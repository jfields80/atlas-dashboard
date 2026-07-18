"""AES-WORK-001A/B -- batch import queue: contracts, manifest parsing,
fail-closed validation, stable batch identity, deterministic per-job
fingerprints (001A), and the sequential execution runner, atomic state
persistence, and resume doctrine (001B).

001B routes every job through the EXISTING importer entry points -- never a
second extraction system:

  1 URL     -> import_url(...)   (scripts/import_official_url.py)
  2-4 URLs  -> import_urls(...)  (scripts/import_official_urls.py)

Candidate JSON and per-candidate HTML reports remain authoritative at their
existing ``<output_root>/candidates|reports/`` paths; batch state stores
only pointers, status, fingerprints, and execution metadata --
``<output_root>/batches/<batch_id>/{manifest,state,summary}.json``.

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
import os
import re
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.candidate import _registrable, load_candidate
from scripts.pettripfinder.importer.domain_packs.registry import default_registry
from scripts.pettripfinder.importer.models import CandidateListing, ImportContext

# Reuse the existing per-URL-count importer entry points and their static-
# fixture builders verbatim -- batch.py is an orchestrator, never a second
# extraction system. Neither CLI imports anything from this module, so this
# is a one-directional dependency (no cycle).
from scripts.import_official_url import _build_static, import_url
from scripts.import_official_urls import _build_static_multi, import_urls

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
    runtime, random values, or output_root.

    AES-DATA-003A: also folds in the resolved domain pack's ``pack_id`` and
    ``pack_version`` for the job's category, so pack provenance participates
    in reuse semantics -- changing ONE pack's version invalidates only the
    fingerprints of jobs in that pack's categories (proven in
    test_domain_packs.py), never a different category's jobs, and never
    batch_id/manifest_hash (both are computed independently of any pack).
    An unresolvable category fails clearly (UnknownCategoryError) rather
    than silently fingerprinting without pack provenance -- by the time a
    real run reaches this function the category has already passed
    validate_manifest, so this only fires for a caller that bypasses it."""
    pack = default_registry.for_category(job.category)
    normalized_urls = [N.normalize_url(u) or u for u in job.urls]
    payload = {field: getattr(job, field) for field in _FINGERPRINT_JOB_FIELDS}
    payload["urls"] = normalized_urls
    payload["extractor"] = extractor
    payload["model"] = model
    payload["observed_at"] = observed_at
    payload["importer_version"] = C.IMPORTER_VERSION
    payload["aggregation_version"] = C.AGGREGATION_VERSION
    payload["pack_id"] = pack.pack_id
    payload["pack_version"] = pack.pack_version

    if extractor == "static":
        repo_root = Path(repo_root).resolve()
        fixture_hashes = []
        for fixture in job.static_fixtures:
            fixture_bytes = (repo_root / fixture).resolve().read_bytes()
            fixture_hashes.append(hashlib.sha256(fixture_bytes).hexdigest())
        payload["fixture_hashes"] = fixture_hashes

    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# =========================================================================== #
# AES-WORK-001B -- execution: state contracts, atomic persistence, routing,
# and the sequential resumable runner.
# =========================================================================== #

def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_clock() -> str:
    """UTC timestamp string for run_id/created_at provenance. Never
    participates in batch_id/manifest_hash/job_fingerprint or any other
    deterministic candidate output -- tests inject a fixed ``clock``
    callable instead of calling this."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BatchStateError(ValueError):
    """Persisted batch state that is malformed or incompatible with the
    current run: bad JSON, missing/mistyped keys, an unrecognized
    execution_state, a batch_state_version mismatch, or a batch_id mismatch.
    Distinct from ``BatchRunError`` -- this is purely about the STORED
    document's shape; ``BatchRunError`` is the batch-level precondition
    failure raised once that document (or its absence) has been reconciled
    against the current invocation."""


class BatchRunError(ValueError):
    """A batch-level precondition failure detected before/during a real
    execution attempt that must map to CLI exit code 2: existing state
    without --resume/--force, incompatible persisted state, or an unknown
    --job-id selection. Raised before any job executes."""


# --------------------------------------------------------------------------- #
# Job execution-state vocabulary (Task 1). Plain string constants, matching
# the established importer convention (RECOMMEND_READY, SUPPORT_SUPPORTED,
# ...) rather than introducing enum.Enum for the first time in this package.
# --------------------------------------------------------------------------- #

JOB_PENDING = "PENDING"
JOB_RUNNING = "RUNNING"
JOB_DONE = "DONE"
JOB_FAILED = "FAILED"
JOB_SKIPPED = "SKIPPED"
JOB_EXEC_STATES = frozenset({JOB_PENDING, JOB_RUNNING, JOB_DONE, JOB_FAILED, JOB_SKIPPED})


# --------------------------------------------------------------------------- #
# State contracts (Task 1).
#
# Durable-state-versus-current-run-action doctrine: ``execution_state`` is
# the permanent ledger truth and is machine-checked against JOB_EXEC_STATES.
# SKIPPED is reserved EXCLUSIVELY for a job that has never produced (and
# under this invocation will not produce) a candidate -- i.e. a disabled
# job. A completed job that is merely being reused this run, or was simply
# not selected this run, keeps its durable DONE (or PENDING) state exactly
# as it was; ``last_action`` records what THIS invocation did with it
# ("ran" | "reused" | "skipped_disabled" | "skipped_not_selected" |
# "failed" | "" for an untouched PENDING job). This is why the summary
# reports a "disabled" total rather than a generic "skipped" total: durable
# SKIPPED means only "disabled" (Task 9).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class JobState:
    job_id: str
    fingerprint: str
    execution_state: str
    last_action: str = ""
    recommendation: str = ""
    recommendation_reasons: Tuple[str, ...] = ()
    candidate_id: str = ""
    candidate_path: str = ""
    report_path: str = ""
    run_id: str = ""
    skip_reason: str = ""
    error_type: str = ""
    error_message: str = ""
    # (source_id, role, status_label) triples; empty for a single-source job
    # (sources == () on the candidate itself, same AES-DATA-001 shape).
    source_outcomes: Tuple[Tuple[str, str, str], ...] = ()
    snapshot_hashes: Tuple[str, ...] = ()
    provider: str = ""
    model: str = ""
    prompt_version: str = ""
    # AES-WORK-001C (additive; legacy WORK-001B state.json loads these as
    # their defaults below). Real provider usage only -- never inferred.
    # USD estimation is deferred this phase (Task 9): estimated_cost_usd/
    # pricing_version are carried as schema fields but never populated.
    provider_request_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: str = ""
    pricing_version: str = ""


@dataclass(frozen=True)
class BatchState:
    batch_state_version: str
    batch_id: str
    manifest_hash: str
    manifest_schema_version: str
    extractor: str
    model: str
    observed_at: str
    jobs: Tuple[JobState, ...]   # manifest order, always -- never completion order


# --------------------------------------------------------------------------- #
# State serialization (Task 2). Sorted-key JSON, UTF-8, LF; tuples round-trip
# through lists; missing optional keys default; malformed/incompatible state
# is rejected with a clear ``BatchStateError`` -- never arbitrary object
# decoding (plain ``json.loads`` and explicit field access only).
# --------------------------------------------------------------------------- #

def _job_state_to_dict(js: JobState) -> dict:
    return {
        "job_id": js.job_id,
        "fingerprint": js.fingerprint,
        "execution_state": js.execution_state,
        "last_action": js.last_action,
        "recommendation": js.recommendation,
        "recommendation_reasons": list(js.recommendation_reasons),
        "candidate_id": js.candidate_id,
        "candidate_path": js.candidate_path,
        "report_path": js.report_path,
        "run_id": js.run_id,
        "skip_reason": js.skip_reason,
        "error_type": js.error_type,
        "error_message": js.error_message,
        "source_outcomes": [list(t) for t in js.source_outcomes],
        "snapshot_hashes": list(js.snapshot_hashes),
        "provider": js.provider,
        "model": js.model,
        "prompt_version": js.prompt_version,
        "provider_request_count": js.provider_request_count,
        "input_tokens": js.input_tokens,
        "output_tokens": js.output_tokens,
        "estimated_cost_usd": js.estimated_cost_usd,
        "pricing_version": js.pricing_version,
    }


def _job_state_from_dict(d: dict) -> JobState:
    if not isinstance(d, dict):
        raise BatchStateError("a job state entry must be a JSON object")
    try:
        job_id = d["job_id"]
        fingerprint = d["fingerprint"]
        execution_state = d["execution_state"]
    except KeyError as exc:
        raise BatchStateError("job state entry missing required key: %s" % exc) from exc
    if execution_state not in JOB_EXEC_STATES:
        raise BatchStateError("job %r has an unrecognized execution_state: %r"
                              % (job_id, execution_state))
    return JobState(
        job_id=job_id, fingerprint=fingerprint, execution_state=execution_state,
        last_action=d.get("last_action", ""),
        recommendation=d.get("recommendation", ""),
        recommendation_reasons=tuple(d.get("recommendation_reasons", ())),
        candidate_id=d.get("candidate_id", ""),
        candidate_path=d.get("candidate_path", ""),
        report_path=d.get("report_path", ""),
        run_id=d.get("run_id", ""),
        skip_reason=d.get("skip_reason", ""),
        error_type=d.get("error_type", ""),
        error_message=d.get("error_message", ""),
        source_outcomes=tuple(tuple(t) for t in d.get("source_outcomes", ())),
        snapshot_hashes=tuple(d.get("snapshot_hashes", ())),
        provider=d.get("provider", ""),
        model=d.get("model", ""),
        prompt_version=d.get("prompt_version", ""),
        provider_request_count=d.get("provider_request_count", 0),
        input_tokens=d.get("input_tokens", 0),
        output_tokens=d.get("output_tokens", 0),
        estimated_cost_usd=d.get("estimated_cost_usd", ""),
        pricing_version=d.get("pricing_version", ""),
    )


def batch_state_to_dict(state: BatchState) -> dict:
    return {
        "batch_state_version": state.batch_state_version,
        "batch_id": state.batch_id,
        "manifest_hash": state.manifest_hash,
        "manifest_schema_version": state.manifest_schema_version,
        "extractor": state.extractor,
        "model": state.model,
        "observed_at": state.observed_at,
        "jobs": [_job_state_to_dict(j) for j in state.jobs],
    }


def batch_state_from_dict(d: dict) -> BatchState:
    if not isinstance(d, dict):
        raise BatchStateError("batch state must be a JSON object")
    required = ("batch_state_version", "batch_id", "manifest_hash",
               "manifest_schema_version", "extractor", "model", "observed_at", "jobs")
    missing = [k for k in required if k not in d]
    if missing:
        raise BatchStateError("batch state missing required key(s): %s" % ", ".join(missing))
    if not isinstance(d["jobs"], list):
        raise BatchStateError("batch state 'jobs' must be a list")
    jobs = tuple(_job_state_from_dict(j) for j in d["jobs"])
    return BatchState(
        batch_state_version=d["batch_state_version"],
        batch_id=d["batch_id"],
        manifest_hash=d["manifest_hash"],
        manifest_schema_version=d["manifest_schema_version"],
        extractor=d["extractor"],
        model=d["model"],
        observed_at=d["observed_at"],
        jobs=jobs,
    )


def dump_batch_state(state: BatchState) -> str:
    return json.dumps(batch_state_to_dict(state), sort_keys=True, ensure_ascii=False, indent=2)


def load_batch_state(path) -> BatchState:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except ValueError as exc:
        raise BatchStateError("state.json is not valid JSON: %s" % exc) from exc
    return batch_state_from_dict(raw)


# --------------------------------------------------------------------------- #
# Atomic JSON writer (Task 3). An independent implementation of the
# repository's established same-directory-tempfile + os.replace idiom
# (mirrors, but never imports, ArtifactStoreRepository's private method).
# --------------------------------------------------------------------------- #

def _atomic_write_json(path, payload: dict) -> None:
    """Write ``payload`` to ``path`` atomically: serialize, write to a
    same-directory temp file, flush, best-effort fsync, then ``os.replace``.
    The parent directory is created here (callers only ever reach this
    function during real execution, never dry-run). On any failure before
    ``os.replace`` the prior file (if any) is left completely intact and
    the abandoned temp file is removed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(blob)
            handle.write("\n")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass   # best-effort: not every filesystem/mount supports fsync
        os.replace(tmp_name, str(path))
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _manifest_snapshot_dict(manifest: BatchManifest) -> dict:
    """The frozen, defaults-resolved manifest as persisted to manifest.json
    -- the current audit copy, always kept up to date (Task 4)."""
    return {
        "manifest_schema_version": manifest.manifest_schema_version,
        "batch_id": manifest.batch_id,
        "batch_name": manifest.batch_name,
        "manifest_hash": compute_manifest_hash(manifest),
        "jobs": [_job_to_ordered_dict(j) for j in manifest.jobs],
    }


def write_manifest_snapshot(manifest: BatchManifest, batch_dir) -> Path:
    path = Path(batch_dir) / "manifest.json"
    _atomic_write_json(path, _manifest_snapshot_dict(manifest))
    return path


def write_batch_state(state: BatchState, batch_dir) -> Path:
    path = Path(batch_dir) / "state.json"
    _atomic_write_json(path, batch_state_to_dict(state))
    return path


def write_batch_summary(summary: dict, batch_dir) -> Path:
    path = Path(batch_dir) / "summary.json"
    _atomic_write_json(path, summary)
    return path


# --------------------------------------------------------------------------- #
# Execution routing (Task 5): one URL -> import_url; two-to-four -> import_urls.
# Never a second extraction system.
# --------------------------------------------------------------------------- #

def _build_fetcher_extractor_for_job(
    job: BatchJob, *, extractor_mode: str, model: str, repo_root: Path,
    fetcher_factory: Optional[Callable] = None,
    extractor_factory: Optional[Callable] = None,
):
    """Real construction mirrors the existing CLIs' own static/anthropic
    branches exactly (their private fixture builders are reused verbatim,
    never re-implemented). Tests may inject ``fetcher_factory``/
    ``extractor_factory`` (each called as ``factory(job)``) to bypass real
    fixture-file/network construction entirely; both or neither must be
    supplied."""
    if (fetcher_factory is None) != (extractor_factory is None):
        raise ValueError("fetcher_factory and extractor_factory must be supplied together")
    if fetcher_factory is not None and extractor_factory is not None:
        return (fetcher_factory(job), extractor_factory(job))

    if extractor_mode == "static":
        if len(job.urls) == 1:
            fixture_path = str((repo_root / job.static_fixtures[0]).resolve())
            return _build_static(job.urls[0], fixture_path)
        fixture_paths = [str((repo_root / f).resolve()) for f in job.static_fixtures]
        return _build_static_multi(list(job.urls), fixture_paths)

    # anthropic: live provider, never called in tests.
    from scripts.pettripfinder.importer.fetch import RequestsPageFetcher
    from scripts.pettripfinder.importer.extraction_anthropic import AnthropicFactExtractor
    return (RequestsPageFetcher(), AnthropicFactExtractor(model=model))


def run_job(
    job: BatchJob, *, extractor_mode: str, model: str, observed_at: str,
    created_at: str, output_root: str, repo_root: Path,
    fetcher_factory: Optional[Callable] = None,
    extractor_factory: Optional[Callable] = None,
) -> Tuple[CandidateListing, Path, Path]:
    """Execute ONE job through the existing single-source or multi-source
    importer entry point, chosen strictly by URL count. Builds the
    ``ImportContext`` from the resolved ``BatchJob``; extractor/model/
    observed_at/created_at/output_root come from the batch-level caller."""
    context = ImportContext(
        category=job.category, candidate_name=job.candidate_name,
        expected_city=job.expected_city, expected_state=job.expected_state,
        source_relationship_hint=job.source_relationship_hint,
        source_type_hint=job.source_type_hint)
    fetcher, extractor = _build_fetcher_extractor_for_job(
        job, extractor_mode=extractor_mode, model=model, repo_root=repo_root,
        fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
    if len(job.urls) == 1:
        return import_url(
            job.urls[0], context, fetcher=fetcher, extractor=extractor,
            output_root=output_root, observed_at=observed_at, created_at=created_at)
    return import_urls(
        list(job.urls), context, fetcher=fetcher, extractor=extractor,
        output_root=output_root, observed_at=observed_at, created_at=created_at)


def _source_status_label(source_record) -> str:
    if source_record.excluded_reason:
        return "excluded:%s" % source_record.excluded_reason
    if not source_record.usable:
        return "unusable:%s" % source_record.fetch_reason
    return "included"


# --------------------------------------------------------------------------- #
# AES-WORK-001C Task 2 -- per-registrable-domain lock keys. Pure, no I/O: no
# DNS, no fetch, derived only from the requested URL strings (which
# validate_manifest has already confirmed are non-empty; a malformed URL
# manifest fails validation long before this is ever called). This is a
# politeness key for serializing concurrent network/provider work against
# the same site, not a security boundary -- final-redirect domains remain
# governed entirely by the existing importer's own fetch-safety checks.
# --------------------------------------------------------------------------- #

def _job_domain_keys(job: BatchJob) -> Tuple[str, ...]:
    """The distinct registrable domains this job's requested URLs resolve
    to, normalized and sorted -- reuses the exact same ``_registrable``
    helper ``aggregate.py`` already relies on for its own same-domain gate,
    never a second domain-parsing implementation. Deduplicated: a
    multi-source job whose URLs share one domain yields exactly ONE key, so
    a single (non-reentrant) lock is acquired once, not twice."""
    domains = set()
    for url in job.urls:
        host = (urlsplit(url).hostname or "").lower()
        domains.add(_registrable(host))
    return tuple(sorted(domains))


# --------------------------------------------------------------------------- #
# Consolidated summary (Task 9). Pure function of durable state + manifest;
# no elapsed-time/wall-clock field anywhere.
# --------------------------------------------------------------------------- #

def build_batch_summary(state: BatchState, manifest: BatchManifest) -> dict:
    totals = {
        "jobs": len(state.jobs), "done": 0, "failed": 0, "pending": 0,
        "running": 0, "disabled": 0, "ready": 0, "review": 0, "reject": 0,
    }
    usage_totals = {"provider_request_count": 0, "input_tokens": 0, "output_tokens": 0}
    by_id = {js.job_id: js for js in state.jobs}
    jobs_out = []
    for job in manifest.jobs:   # manifest order, always
        js = by_id.get(job.job_id)
        if js is None:
            continue
        if js.execution_state == JOB_DONE:
            totals["done"] += 1
        elif js.execution_state == JOB_FAILED:
            totals["failed"] += 1
        elif js.execution_state == JOB_PENDING:
            totals["pending"] += 1
        elif js.execution_state == JOB_RUNNING:
            totals["running"] += 1
        elif js.execution_state == JOB_SKIPPED:
            totals["disabled"] += 1
        if js.recommendation == C.RECOMMEND_READY:
            totals["ready"] += 1
        elif js.recommendation == C.RECOMMEND_REVIEW:
            totals["review"] += 1
        elif js.recommendation == C.RECOMMEND_REJECT:
            totals["reject"] += 1
        usage_totals["provider_request_count"] += js.provider_request_count
        usage_totals["input_tokens"] += js.input_tokens
        usage_totals["output_tokens"] += js.output_tokens
        jobs_out.append({
            "job_id": js.job_id,
            "candidate_name": job.candidate_name,
            "execution_state": js.execution_state,
            "last_action": js.last_action,
            "recommendation": js.recommendation,
            "reasons": list(js.recommendation_reasons),
            "candidate_path": js.candidate_path,
            "report_path": js.report_path,
            "fingerprint": js.fingerprint,
            "run_id": js.run_id,
            "skip_reason": js.skip_reason,
            "error_type": js.error_type,
            "error_message": js.error_message,
            "source_outcomes": [list(t) for t in js.source_outcomes],
            "snapshot_hashes": list(js.snapshot_hashes),
            "usage": {
                "provider_request_count": js.provider_request_count,
                "input_tokens": js.input_tokens,
                "output_tokens": js.output_tokens,
                "estimated_cost_usd": js.estimated_cost_usd,
                "pricing_version": js.pricing_version,
            },
        })
    # USD estimation is deferred this phase (Task 9) -- estimated_cost_usd
    # is never populated on any JobState, so it never appears at the batch
    # level either. This key is added only once a real pricing table
    # produces a known cost for every contributing job.
    return {
        "batch_state_version": state.batch_state_version,
        "batch_id": state.batch_id,
        "batch_name": manifest.batch_name,
        "manifest_hash": state.manifest_hash,
        "manifest_schema_version": state.manifest_schema_version,
        "extractor": state.extractor,
        "model": state.model,
        "observed_at": state.observed_at,
        "importer_version": C.IMPORTER_VERSION,
        "aggregation_version": C.AGGREGATION_VERSION,
        "totals": totals,
        "usage": usage_totals,
        "jobs": jobs_out,
    }


# --------------------------------------------------------------------------- #
# Resume-reuse eligibility (Task 6 doctrine, factored out so the sequential
# and concurrent runners share IDENTICAL reuse semantics). Pure/read-only:
# no lock, no persist, no mutation -- safe to call from any thread.
# --------------------------------------------------------------------------- #

def _is_reusable(prior: JobState, fingerprint: str) -> bool:
    if prior.execution_state != JOB_DONE or prior.fingerprint != fingerprint:
        return False
    if not prior.candidate_path or not Path(prior.candidate_path).exists():
        return False
    if not prior.report_path or not Path(prior.report_path).exists():
        return False
    try:
        load_candidate(prior.candidate_path)
    except Exception:
        return False
    return True


# --------------------------------------------------------------------------- #
# The sequential runner (Task 6). Manifest order throughout; state+summary
# persisted atomically after every transition (initial snapshot, RUNNING,
# and every terminal outcome) -- never only at batch completion.
# --------------------------------------------------------------------------- #

def run_batch(
    manifest: BatchManifest,
    *,
    extractor_mode: str,
    model: str,
    output_root,
    observed_at: str,
    resume: bool = False,
    force: bool = False,
    selected_job_ids: Tuple[str, ...] = (),
    repo_root=None,
    fetcher_factory: Optional[Callable] = None,
    extractor_factory: Optional[Callable] = None,
    clock: Optional[Callable[[], str]] = None,
    max_workers: int = 1,
) -> BatchState:
    """Execute a manifest. ``max_workers=1`` (the default) runs the EXACT
    WORK-001B sequential algorithm, byte-for-byte unchanged below. Every
    precondition (unknown selected job id, malformed/incompatible prior
    state, existing state without resume/force, out-of-range max_workers)
    is checked and raised as ``BatchRunError``/``BatchStateError`` BEFORE
    any directory is created or any file is written -- a rejected run
    touches nothing. One job's exception is isolated (FAILED, batch
    continues); KeyboardInterrupt converts any currently-RUNNING job to
    FAILED before re-raising, so resume never treats an interrupted job as
    reusable.

    ``max_workers>1`` (AES-WORK-001C) additionally bounds concurrency via
    ``ThreadPoolExecutor`` and serializes jobs that share a registrable
    domain -- see ``_job_domain_keys``/Task 2. Concurrency is job-level
    only: sources within one multi-source job stay sequential through the
    existing ``import_urls`` path, exactly as in WORK-001B."""
    if not (1 <= max_workers <= C.MAX_BATCH_WORKERS):
        raise BatchRunError(
            "max_workers must be between 1 and %d (got %d)"
            % (C.MAX_BATCH_WORKERS, max_workers))
    repo_root = Path(repo_root).resolve() if repo_root is not None else _default_repo_root()
    output_root = Path(output_root)
    clock = clock or _default_clock
    # Deferred import: batch_report.py imports contract types FROM this
    # module, so importing it back at module level here would be a cycle.
    from scripts.pettripfinder.importer.batch_report import (
        build_batch_report_html,
        write_batch_report,
    )

    batch_id = get_batch_id(manifest)
    manifest_hash = compute_manifest_hash(manifest)
    batch_dir = output_root / C.BATCHES_SUBDIR / batch_id
    state_path = batch_dir / "state.json"

    all_job_ids = [job.job_id for job in manifest.jobs]
    selected = set(selected_job_ids) if selected_job_ids else set(all_job_ids)
    unknown = selected - set(all_job_ids)
    if unknown:
        raise BatchRunError("unknown selected job id(s): %s" % ", ".join(sorted(unknown)))

    prior_state: Optional[BatchState] = None
    if state_path.exists():
        try:
            prior_state = load_batch_state(state_path)
        except BatchStateError as exc:
            raise BatchRunError("existing batch state is malformed: %s" % exc) from exc
        if prior_state.batch_state_version != C.BATCH_STATE_VERSION:
            raise BatchRunError(
                "existing batch state version %r is incompatible with %r"
                % (prior_state.batch_state_version, C.BATCH_STATE_VERSION))
        if prior_state.batch_id != batch_id:
            raise BatchRunError(
                "existing batch state batch_id %r does not match manifest batch_id %r"
                % (prior_state.batch_id, batch_id))
        if not resume and not force:
            raise BatchRunError(
                "batch state already exists at %s -- pass resume=True or force=True"
                % state_path)

    fingerprints = {
        job.job_id: compute_job_fingerprint(
            job, extractor=extractor_mode, model=model, observed_at=observed_at,
            repo_root=repo_root)
        for job in manifest.jobs
    }

    # Every precondition has passed -- only now does execution touch disk.
    batch_dir.mkdir(parents=True, exist_ok=True)
    write_manifest_snapshot(manifest, batch_dir)

    prior_by_id = {js.job_id: js for js in (prior_state.jobs if prior_state else ())}
    job_states: Dict[str, JobState] = {}
    for job in manifest.jobs:
        prior = prior_by_id.get(job.job_id)
        job_states[job.job_id] = prior if prior is not None else JobState(
            job_id=job.job_id, fingerprint=fingerprints[job.job_id],
            execution_state=JOB_PENDING)

    def _current_state() -> BatchState:
        return BatchState(
            batch_state_version=C.BATCH_STATE_VERSION, batch_id=batch_id,
            manifest_hash=manifest_hash,
            manifest_schema_version=manifest.manifest_schema_version,
            extractor=extractor_mode, model=model, observed_at=observed_at,
            jobs=tuple(job_states[j.job_id] for j in manifest.jobs))

    def _persist_unlocked() -> BatchState:
        """Compute + write state/summary/report from the CURRENT job_states.
        Callers are responsible for any locking; the sequential path below
        is single-threaded and calls this directly via ``_persist()``."""
        state = _current_state()
        write_batch_state(state, batch_dir)
        write_batch_summary(build_batch_summary(state, manifest), batch_dir)
        write_batch_report(build_batch_report_html(state, manifest, batch_dir), batch_dir)
        return state

    def _persist() -> BatchState:
        return _persist_unlocked()

    _persist()   # initial snapshot: every job visible before any execution

    if max_workers <= 1:
        # --- WORK-001B sequential algorithm, byte-for-byte unchanged. -------
        try:
            for job in manifest.jobs:
                fingerprint = fingerprints[job.job_id]
                prior = job_states[job.job_id]

                if not job.enabled:
                    job_states[job.job_id] = replace(
                        prior, fingerprint=fingerprint, execution_state=JOB_SKIPPED,
                        last_action="skipped_disabled", skip_reason="disabled")
                    _persist()
                    continue

                if job.job_id not in selected:
                    # Durable state (execution_state and everything else)
                    # untouched -- only the per-run action is stamped.
                    job_states[job.job_id] = replace(prior, last_action="skipped_not_selected")
                    _persist()
                    continue

                if not force and resume and _is_reusable(prior, fingerprint):
                    job_states[job.job_id] = replace(
                        prior, fingerprint=fingerprint, last_action="reused")
                    _persist()
                    continue

                run_id = clock()
                job_states[job.job_id] = JobState(
                    job_id=job.job_id, fingerprint=fingerprint,
                    execution_state=JOB_RUNNING, last_action="ran", run_id=run_id)
                _persist()

                try:
                    candidate, json_path, report_path = run_job(
                        job, extractor_mode=extractor_mode, model=model,
                        observed_at=observed_at, created_at=run_id,
                        output_root=str(output_root), repo_root=repo_root,
                        fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
                except Exception as exc:
                    job_states[job.job_id] = JobState(
                        job_id=job.job_id, fingerprint=fingerprint,
                        execution_state=JOB_FAILED, last_action="failed", run_id=run_id,
                        error_type=type(exc).__name__, error_message=str(exc)[:500])
                    _persist()
                    continue

                source_outcomes = tuple(
                    (s.source_id, s.role, _source_status_label(s)) for s in candidate.sources)
                snapshot_hashes = (
                    tuple(s.snapshot.raw_content_hash for s in candidate.sources if s.snapshot)
                    if candidate.sources else (candidate.snapshot.raw_content_hash,))

                job_states[job.job_id] = JobState(
                    job_id=job.job_id, fingerprint=fingerprint,
                    execution_state=JOB_DONE, last_action="ran", run_id=run_id,
                    recommendation=candidate.recommendation,
                    recommendation_reasons=candidate.recommendation_reasons,
                    candidate_id=candidate.candidate_id, candidate_path=str(json_path),
                    report_path=str(report_path), source_outcomes=source_outcomes,
                    snapshot_hashes=snapshot_hashes,
                    provider=candidate.extraction_provider, model=candidate.extraction_model,
                    prompt_version=candidate.prompt_version,
                    provider_request_count=candidate.provider_request_count,
                    input_tokens=candidate.input_tokens, output_tokens=candidate.output_tokens)
                _persist()
        except KeyboardInterrupt:
            # A currently-RUNNING job must never look DONE: convert it to
            # FAILED atomically before re-raising, so resume reruns it rather
            # than (incorrectly) treating it as reusable. Ctrl+C is never
            # swallowed -- it always propagates to the caller.
            interrupted = False
            for jid, js in list(job_states.items()):
                if js.execution_state == JOB_RUNNING:
                    job_states[jid] = replace(
                        js, execution_state=JOB_FAILED, last_action="failed",
                        error_type="KeyboardInterrupt", error_message="interrupted")
                    interrupted = True
            if interrupted:
                _persist()
            raise

    else:
        # --- AES-WORK-001C concurrent path (Tasks 1-4, 11) -------------------
        # ONE coordinator lock around every job_states mutation + write, so a
        # persisted snapshot never straddles two threads' updates (Task 3).
        coordinator_lock = threading.Lock()

        def _apply(job_id: str, new_job_state: JobState) -> BatchState:
            with coordinator_lock:
                job_states[job_id] = new_job_state
                return _persist_unlocked()

        # Pre-pass: classify every job in manifest order. Disabled/not-
        # selected/reused jobs never touch a thread -- identical semantics
        # to the sequential branch above, via the SAME _is_reusable helper.
        to_execute: List[Tuple[BatchJob, str]] = []
        for job in manifest.jobs:
            fingerprint = fingerprints[job.job_id]
            prior = job_states[job.job_id]

            if not job.enabled:
                _apply(job.job_id, replace(
                    prior, fingerprint=fingerprint, execution_state=JOB_SKIPPED,
                    last_action="skipped_disabled", skip_reason="disabled"))
                continue
            if job.job_id not in selected:
                _apply(job.job_id, replace(prior, last_action="skipped_not_selected"))
                continue
            if not force and resume and _is_reusable(prior, fingerprint):
                _apply(job.job_id, replace(
                    prior, fingerprint=fingerprint, last_action="reused"))
                continue
            to_execute.append((job, fingerprint))

        if not to_execute:
            return _current_state()

        # Per-registrable-domain lock registry (Task 2) -- local to THIS
        # run_batch call only, never a process-wide/global registry.
        # Pre-created (not lazily created inside a worker) so no thread ever
        # races another to create-or-fetch the SAME domain's lock object.
        domain_locks: Dict[str, threading.Lock] = {}
        for job, _fp in to_execute:
            for d in _job_domain_keys(job):
                domain_locks.setdefault(d, threading.Lock())

        def _worker(job: BatchJob, fingerprint: str):
            """Acquire this job's domain locks in sorted order, run it
            through the existing single/multi-source entry point, and
            RETURN an immutable outcome for the coordinator to apply
            (Task 3.C) -- the only direct (lock-protected) mutation a
            worker performs itself is the initial RUNNING mark, so
            operators watching state.json see progress in real time even
            while a job is still queued behind a same-domain lock."""
            run_id = clock()
            _apply(job.job_id, JobState(
                job_id=job.job_id, fingerprint=fingerprint,
                execution_state=JOB_RUNNING, last_action="ran", run_id=run_id))

            domains = _job_domain_keys(job)
            for d in domains:                      # sorted already
                domain_locks[d].acquire()
            try:
                try:
                    candidate, json_path, report_path = run_job(
                        job, extractor_mode=extractor_mode, model=model,
                        observed_at=observed_at, created_at=run_id,
                        output_root=str(output_root), repo_root=repo_root,
                        fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
                except Exception as exc:
                    # Isolated to this job (Task 11): never escapes _worker,
                    # so a future's .result() never raises for this reason.
                    return (job.job_id, JobState(
                        job_id=job.job_id, fingerprint=fingerprint,
                        execution_state=JOB_FAILED, last_action="failed", run_id=run_id,
                        error_type=type(exc).__name__, error_message=str(exc)[:500]))

                source_outcomes = tuple(
                    (s.source_id, s.role, _source_status_label(s)) for s in candidate.sources)
                snapshot_hashes = (
                    tuple(s.snapshot.raw_content_hash for s in candidate.sources if s.snapshot)
                    if candidate.sources else (candidate.snapshot.raw_content_hash,))
                return (job.job_id, JobState(
                    job_id=job.job_id, fingerprint=fingerprint,
                    execution_state=JOB_DONE, last_action="ran", run_id=run_id,
                    recommendation=candidate.recommendation,
                    recommendation_reasons=candidate.recommendation_reasons,
                    candidate_id=candidate.candidate_id, candidate_path=str(json_path),
                    report_path=str(report_path), source_outcomes=source_outcomes,
                    snapshot_hashes=snapshot_hashes,
                    provider=candidate.extraction_provider, model=candidate.extraction_model,
                    prompt_version=candidate.prompt_version,
                    provider_request_count=candidate.provider_request_count,
                    input_tokens=candidate.input_tokens, output_tokens=candidate.output_tokens))
            finally:
                # Domain lock is ALWAYS released (Task 11), even on a job
                # exception or an (in practice signal-delivery-impossible,
                # but test-injectable) BaseException from run_job.
                for d in reversed(domains):
                    domain_locks[d].release()

        executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            futures = {executor.submit(_worker, job, fp): job.job_id
                      for job, fp in to_execute}
            try:
                for future in as_completed(futures):
                    job_id, outcome_state = future.result()
                    _apply(job_id, outcome_state)
            except KeyboardInterrupt:
                # Stop submitting new work (everything eligible was already
                # handed to the pool above -- there is nothing left to hold
                # back) and cancel whatever has not started yet. NOTE: an
                # ALREADY-RUNNING worker's blocking network/provider call
                # cannot be forcibly interrupted -- Python's ThreadPoolExecutor
                # has no thread-kill primitive, and (per the ``signal`` module)
                # a real KeyboardInterrupt is only ever delivered to the MAIN
                # thread in the first place, so it always surfaces here, at
                # this ``as_completed`` wait, never inside a worker. Such a
                # thread is left to finish in the background (never joined
                # here -- see the ``finally`` below); its job's durable state
                # is still correctly converted to FAILED without waiting for it.
                already_done = [f for f in futures if f.done()]
                for f in futures:
                    if not f.done():
                        f.cancel()   # succeeds only for not-yet-started futures
                with coordinator_lock:
                    # Drain any future that genuinely finished (successfully
                    # or via its own isolated job failure) before the
                    # interrupt landed -- it must never be mis-reported as
                    # interrupted just because we had not gotten to it yet.
                    for f in already_done:
                        job_id = futures[f]
                        try:
                            _, outcome_state = f.result()
                            job_states[job_id] = outcome_state
                        except BaseException:
                            pass   # this future's own exception is exactly
                                   # what triggered this handler; its job is
                                   # decided by the RUNNING sweep below.
                    for jid, js in list(job_states.items()):
                        if js.execution_state == JOB_RUNNING:
                            job_states[jid] = replace(
                                js, execution_state=JOB_FAILED, last_action="failed",
                                error_type="KeyboardInterrupt", error_message="interrupted")
                    _persist_unlocked()
                raise
        finally:
            # Never blocks (Task 4: "do not wait indefinitely"): on the
            # normal-completion path every future is already done, so this
            # is a fast no-op; on the interrupt path it never joins a
            # still-running worker thread.
            executor.shutdown(wait=False, cancel_futures=True)

    return _current_state()
