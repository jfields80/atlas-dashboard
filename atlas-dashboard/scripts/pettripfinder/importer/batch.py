"""AES-WORK-001A -- batch import queue: contracts, manifest parsing,
fail-closed validation, stable batch identity, and deterministic per-job
fingerprints.

Scope is deliberately narrow: this module has NO execution path. It never
fetches, extracts, calls a provider, or persists a candidate/batch-state --
those are later AES-WORK-001 phases, built on top of the existing
``run_import``/``run_multi_import`` entry points (never a second extraction
system).

Three separate identity concepts (binding architectural amendment):

  batch_id       operator-controlled, stable, a safe path component. Never
                 derived from content. Survives job edits unchanged --
                 future per-job resume needs a STABLE state directory.
  manifest_hash  sha256 of the complete defaults-resolved manifest content.
                 Audit metadata only; changes whenever any material content
                 changes. Never used as a directory name.
  job_fingerprint  sha256 of one resolved job plus execution context
                 (extractor/model/observed_at) and code versions
                 (IMPORTER_VERSION/AGGREGATION_VERSION). Controls future
                 per-job reuse; editing one job changes only that job's
                 fingerprint.

Pure and deterministic: no network, no clock (observed_at is supplied by
the caller, never read from the system clock here), no randomness.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N

# job_id and batch_id share one safe-path-component grammar: lowercase
# alnum start, then lowercase alnum/underscore/hyphen, max 64 chars total.
_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# Keys a job entry may carry; a subset (the "defaultable" keys) may also
# appear under the manifest's top-level "defaults" and are shallow-merged
# into each job (explicit job value always wins). job_id/urls/static_fixtures
# are inherently per-job and are never default-able.
_JOB_KEYS = frozenset({
    "job_id", "candidate_name", "category", "expected_city", "expected_state",
    "urls", "source_relationship_hint", "source_type_hint", "static_fixtures",
    "enabled",
})
_DEFAULTABLE_JOB_KEYS = frozenset({
    "candidate_name", "category", "expected_city", "expected_state",
    "source_relationship_hint", "source_type_hint", "enabled",
})
_TOP_LEVEL_KEYS = frozenset({
    "manifest_schema_version", "batch_id", "batch_name", "defaults", "jobs",
})

# The exact ordered field set hashed into a job fingerprint (Task 6). job_id
# is deliberately excluded: a fingerprint answers "would this configuration
# produce the same result," which does not depend on the operator's label
# for the job.
_FINGERPRINT_JOB_FIELDS = (
    "candidate_name", "category", "expected_city", "expected_state",
    "source_relationship_hint", "source_type_hint", "enabled",
)


class BatchManifestError(ValueError):
    """A manifest that could not even be parsed into contracts: malformed
    JSON, wrong top-level shape, or an unknown/mistyped key. Distinct from
    ``validate_manifest``'s business-rule errors (which are returned as
    strings, never raised) -- this is the fail-closed structural gate."""


# --------------------------------------------------------------------------- #
# Contracts.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class BatchJob:
    job_id: str
    candidate_name: str
    category: str
    expected_city: str
    expected_state: str
    urls: Tuple[str, ...]
    source_relationship_hint: str = ""
    source_type_hint: str = ""
    static_fixtures: Tuple[str, ...] = ()
    enabled: bool = True


@dataclass(frozen=True)
class BatchManifest:
    manifest_schema_version: str
    batch_id: str
    batch_name: str
    defaults: Dict[str, str]
    jobs: Tuple[BatchJob, ...]


# --------------------------------------------------------------------------- #
# Manifest parsing (Task 3). Fail-closed on structural/shape problems;
# semantic/business-rule problems are left to validate_manifest.
# --------------------------------------------------------------------------- #

def _require_str(value, field: str) -> str:
    if not isinstance(value, str):
        raise BatchManifestError("%s must be a string" % field)
    return value


def _require_bool(value, field: str) -> bool:
    if not isinstance(value, bool):
        raise BatchManifestError("%s must be a boolean" % field)
    return value


def _require_str_list(value, field: str) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise BatchManifestError("%s must be a list" % field)
    out = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise BatchManifestError("%s[%d] must be a string" % (field, i))
        out.append(item)
    return tuple(out)


def _parse_job(raw: dict, defaults: Dict[str, str]) -> BatchJob:
    if not isinstance(raw, dict):
        raise BatchManifestError("each job must be a JSON object")
    unknown = set(raw) - _JOB_KEYS
    if unknown:
        raise BatchManifestError("unknown job key(s): %s" % ", ".join(sorted(unknown)))
    if "job_id" not in raw:
        raise BatchManifestError("job is missing required key: job_id")
    if "urls" not in raw:
        raise BatchManifestError("job is missing required key: urls")

    def _field(key: str) -> str:
        # Explicit job value wins; otherwise inherit the resolved default;
        # otherwise "" -- never inferred, never guessed (Task 3).
        if key in raw:
            return _require_str(raw[key], key)
        return defaults.get(key, "")

    enabled = raw["enabled"] if "enabled" in raw else defaults.get("enabled", True)
    if not isinstance(enabled, bool):
        raise BatchManifestError("enabled must be a boolean")

    return BatchJob(
        job_id=_require_str(raw["job_id"], "job_id"),
        candidate_name=_field("candidate_name"),
        category=_field("category"),
        expected_city=_field("expected_city"),
        expected_state=_field("expected_state"),
        urls=_require_str_list(raw["urls"], "urls"),
        source_relationship_hint=_field("source_relationship_hint"),
        source_type_hint=_field("source_type_hint"),
        static_fixtures=_require_str_list(raw.get("static_fixtures", []), "static_fixtures"),
        enabled=enabled,
    )


def load_manifest(path) -> BatchManifest:
    """Parse one JSON document into a ``BatchManifest``. Unknown top-level,
    ``defaults``, or job keys are rejected (fail-closed); ``defaults`` is
    shallow-merged into each job with the job's own value always winning;
    the parsed input is never mutated in place; job order is preserved
    exactly as written. Raises ``BatchManifestError`` on any structural
    problem -- semantic/business-rule problems are validate_manifest's job."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except ValueError as exc:
        raise BatchManifestError("manifest is not valid JSON: %s" % exc) from exc

    if not isinstance(raw, dict):
        raise BatchManifestError("manifest must be a JSON object")
    unknown = set(raw) - _TOP_LEVEL_KEYS
    if unknown:
        raise BatchManifestError("unknown top-level key(s): %s" % ", ".join(sorted(unknown)))
    for required in ("manifest_schema_version", "batch_id", "batch_name", "jobs"):
        if required not in raw:
            raise BatchManifestError("manifest is missing required key: %s" % required)

    raw_defaults = raw.get("defaults", {})
    if not isinstance(raw_defaults, dict):
        raise BatchManifestError("defaults must be a JSON object")
    unknown_defaults = set(raw_defaults) - _DEFAULTABLE_JOB_KEYS
    if unknown_defaults:
        raise BatchManifestError(
            "unknown defaults key(s): %s" % ", ".join(sorted(unknown_defaults)))
    defaults: Dict[str, str] = {}
    for key, value in raw_defaults.items():
        if key == "enabled":
            defaults[key] = _require_bool(value, "defaults.enabled")
        else:
            defaults[key] = _require_str(value, "defaults.%s" % key)

    raw_jobs = raw["jobs"]
    if not isinstance(raw_jobs, list):
        raise BatchManifestError("jobs must be a list")
    jobs = tuple(_parse_job(j, defaults) for j in raw_jobs)

    return BatchManifest(
        manifest_schema_version=_require_str(
            raw["manifest_schema_version"], "manifest_schema_version"),
        batch_id=_require_str(raw["batch_id"], "batch_id"),
        batch_name=_require_str(raw["batch_name"], "batch_name"),
        defaults=defaults,
        jobs=jobs,
    )


# --------------------------------------------------------------------------- #
# Validation (Task 4). Pure; returns deterministic, stable-order error
# strings (manifest order, then within-job in the order checked below).
# Never validates network reachability.
# --------------------------------------------------------------------------- #

def _validate_fixture_path(fixture: str, repo_root: Path) -> str:
    """Returns an error message, or "" when the fixture path is safe and
    resolves to an existing regular file beneath ``repo_root``."""
    if not fixture:
        return "fixture path must be a non-empty string"
    p = Path(fixture)
    if p.is_absolute():
        return "fixture path must not be absolute: %s" % fixture
    resolved = (repo_root / p).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return "fixture path escapes the repository root: %s" % fixture
    if not resolved.exists() or not resolved.is_file():
        return "fixture path does not exist or is not a regular file: %s" % fixture
    return ""


def validate_manifest(
    manifest: BatchManifest, *, extractor: str, repo_root,
) -> Tuple[str, ...]:
    """Business-rule validation over an already-parsed manifest. Every
    check here must be satisfiable without any fetch/provider/network call.
    Duplicate job ids reject the entire manifest, same as every other
    structural failure -- nothing here is a per-job partial pass."""
    errors = []
    repo_root = Path(repo_root).resolve()

    if manifest.manifest_schema_version != C.BATCH_MANIFEST_SCHEMA_VERSION:
        errors.append(
            "unsupported manifest_schema_version: %r (expected %r)"
            % (manifest.manifest_schema_version, C.BATCH_MANIFEST_SCHEMA_VERSION))
    if not _SAFE_ID_RE.match(manifest.batch_id or ""):
        errors.append("invalid batch_id: %r" % manifest.batch_id)
    if not manifest.jobs:
        errors.append("manifest has no jobs")

    seen_ids = set()
    for job in manifest.jobs:
        prefix = "job %r: " % job.job_id

        if not _SAFE_ID_RE.match(job.job_id or ""):
            errors.append(prefix + "invalid job_id")
        elif job.job_id in seen_ids:
            errors.append("duplicate job_id: %s" % job.job_id)
        else:
            seen_ids.add(job.job_id)

        if not job.candidate_name.strip():
            errors.append(prefix + "candidate_name is required")
        if job.category not in C.IMPORTER_CATEGORIES:
            errors.append(
                prefix + "category must be one of %s (got %r)"
                % (C.IMPORTER_CATEGORIES, job.category))
        if not job.expected_city.strip():
            errors.append(prefix + "expected_city is required")
        if not job.expected_state.strip():
            errors.append(prefix + "expected_state is required")

        if not (1 <= len(job.urls) <= C.MAX_AGGREGATE_SOURCES):
            errors.append(
                prefix + "urls must contain 1 to %d entries (got %d)"
                % (C.MAX_AGGREGATE_SOURCES, len(job.urls)))
        for i, u in enumerate(job.urls):
            if not u.strip():
                errors.append(prefix + "urls[%d] must be a non-empty string" % i)

        if extractor == "static":
            if len(job.static_fixtures) != len(job.urls):
                errors.append(
                    prefix + "static mode requires exactly one static_fixtures "
                    "entry per url (got %d fixtures for %d urls)"
                    % (len(job.static_fixtures), len(job.urls)))
            for i, fixture in enumerate(job.static_fixtures):
                err = _validate_fixture_path(fixture, repo_root)
                if err:
                    errors.append(prefix + "static_fixtures[%d]: %s" % (i, err))
        elif extractor == "anthropic":
            if job.static_fixtures:
                errors.append(prefix + "anthropic mode does not accept static_fixtures")

    return tuple(errors)


# --------------------------------------------------------------------------- #
# Stable batch identity (Task 5).
# --------------------------------------------------------------------------- #

def get_batch_id(manifest: BatchManifest) -> str:
    """Return the validated, explicit, operator-controlled batch_id. Never
    derived from content, never appended to -- this IS the future state
    directory name (``data/import/batches/<batch_id>/``)."""
    if not _SAFE_ID_RE.match(manifest.batch_id or ""):
        raise ValueError("invalid batch_id: %r" % manifest.batch_id)
    return manifest.batch_id


def _job_to_ordered_dict(job: BatchJob) -> dict:
    return {
        "job_id": job.job_id,
        "candidate_name": job.candidate_name,
        "category": job.category,
        "expected_city": job.expected_city,
        "expected_state": job.expected_state,
        "urls": list(job.urls),
        "source_relationship_hint": job.source_relationship_hint,
        "source_type_hint": job.source_type_hint,
        "static_fixtures": list(job.static_fixtures),
        "enabled": job.enabled,
    }


def compute_manifest_hash(manifest: BatchManifest) -> str:
    """Deterministic sha256 of the complete defaults-resolved manifest:
    schema version, batch_id, batch_name, and every job's full resolved
    field set, in manifest order. Audit metadata only -- never used as a
    directory name and never gates job reuse (that is job_fingerprint's
    job). No timestamps, no wall-clock, no randomness."""
    payload = {
        "manifest_schema_version": manifest.manifest_schema_version,
        "batch_id": manifest.batch_id,
        "batch_name": manifest.batch_name,
        "jobs": [_job_to_ordered_dict(j) for j in manifest.jobs],
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Deterministic per-job fingerprints (Task 6).
# --------------------------------------------------------------------------- #

def compute_job_fingerprint(
    job: BatchJob, *, extractor: str, model: str, observed_at: str, repo_root,
) -> str:
    """Deterministic sha256 of ONE resolved job plus execution context and
    code versions. Editing one job changes only that job's fingerprint;
    changing extractor/model/observed_at/IMPORTER_VERSION/AGGREGATION_VERSION
    changes every job's fingerprint (they are threaded in as shared inputs
    by the caller). Never includes batch_name, other jobs, wall-clock
    runtime, random values, or output_root."""
    normalized_urls = [N.normalize_url(u) or u for u in job.urls]
    payload = {field: getattr(job, field) for field in _FINGERPRINT_JOB_FIELDS}
    payload["urls"] = normalized_urls
    payload["extractor"] = extractor
    payload["model"] = model
    payload["observed_at"] = observed_at
    payload["importer_version"] = C.IMPORTER_VERSION
    payload["aggregation_version"] = C.AGGREGATION_VERSION

    if extractor == "static":
        repo_root = Path(repo_root).resolve()
        fixture_hashes = []
        for fixture in job.static_fixtures:
            fixture_bytes = (repo_root / fixture).resolve().read_bytes()
            fixture_hashes.append(hashlib.sha256(fixture_bytes).hexdigest())
        payload["fixture_hashes"] = fixture_hashes

    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
