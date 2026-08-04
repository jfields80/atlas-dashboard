"""PTF-MACHINE-REVIEW storage -- where each part of a machine review lives.

The governing rule is one line: **track what cannot be recomputed, ignore what
can.**

  * A PENDING_REVIEW record is reproducible. Same evidence plus the same
    committed code yields a byte-identical ``record_hash`` -- ``created_at`` is
    excluded from the hash precisely so a rebuild is not mistaken for a change.
    Reproducible artifacts stay in the gitignored ``data/`` tree.

  * A human DECISION is not reproducible. Nobody can recompute a reviewer's
    judgement from the evidence, so if it lives only under ``data/`` then one
    ``git clean -fdx`` or one disk failure destroys it. Decisions are tracked in
    git, append-only, with history for free.

  * Raw evidence -- captures, screenshots, view metadata -- never enters git.
    Captured pages are verbatim third-party HTML; a scan of this corpus found 67
    Google API keys embedded by the brands in their own markup. Committing them
    would write real third-party credentials into permanent history. Evidence
    stays in ``data/``, is backed up by the runbook, and is referenced here only
    by repo-relative path and SHA-256.

  * A tracked INDEX carries git-safe metadata only, mirroring the existing
    ``atlas-attestation-index/1.0``: hashes and outcomes, never excerpts, never
    absolute paths, and a URL only when it passes a safety check.

Nothing here touches operator-attestation storage. Separate files, separate
index, separate decisions record.
"""

from __future__ import annotations

import hashlib
import json
import os as _os
import pathlib
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from services.research_workers.machine_capture_review import (
    DECISION_APPROVED, DECISION_REJECTED, MachineReviewError,
    OVERLAP_COMPARE_ONLY, STATUS_PENDING_REVIEW,
)

EVIDENCE_MANIFEST_SCHEMA = "ptf-machine-review-evidence-manifest/1.0"
DECISIONS_SCHEMA = "ptf-machine-review-decisions/1.0"
INDEX_SCHEMA = "atlas-machine-review-index/1.0"

EVIDENCE_MANIFEST_NAME = "evidence_manifest.json"
EVIDENCE_MANIFEST_HASH_NAME = "evidence_manifest.sha256"

#: Tracked locations. Relative to the repository root, always posix.
DECISIONS_PATH = "launch_packages/pettripfinder/machine_review_decisions.json"
DECISION_SCHEMA_PATH = "launch_packages/pettripfinder/machine_review_decision.schema.json"
INDEX_PATH = "docs/pettripfinder/artifact_indexes/machine_review_index.json"

#: Gitignored location for regenerable records.
RECORDS_ROOT = "data/worker_runs/pettripfinder/machine_review"

#: Directory names that never belong in an evidence manifest. ``.chrome-profile``
#: is the capture runner's browser scratch: it holds Cookies, Login Data and
#: Trust Tokens, and nothing in it is evidence.
EXCLUDED_DIR_PARTS = ("site", ".chrome-profile")

#: Fields a tracked file may never carry, whatever else it says.
FORBIDDEN_TRACKED_KEYS = (
    "cookie", "cookies", "header", "headers", "token", "tokens", "secret",
    "password", "authorization", "html", "screenshot_bytes", "policy_excerpt",
    "text", "payload",
)

#: An absolute path in any form -- Windows drive, UNC, or posix root.
_ABSOLUTE_PATH_RE = re.compile(r"(?:^|[\"'\s=:])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|Users|mnt|var|etc)/)")

#: Credential shapes, matching the backup tool's redaction vocabulary.
_CREDENTIAL_RE = re.compile(
    r"AIza[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9_\-]{20,}|nfp_[A-Za-z0-9]{10,}"
    r"|AKIA[0-9A-Z]{16}|(?i:bearer\s+[A-Za-z0-9._\-]{20,})"
    r"|(?i:(api[_-]?key|token|secret|password)\s*[:=]\s*\S{8,})")

#: Query keys that carry campaign or session identifiers. A URL bearing one is
#: recorded without its query rather than omitted: the path still identifies the
#: property, and the tracking parameter is what must not be republished.
_TRACKING_QUERY_KEYS = ("cid", "seo_id", "iata", "gclid", "fbclid", "utm_source",
                        "utm_medium", "utm_campaign", "utm_term", "utm_content",
                        "sid", "sessionid", "token", "key")


class StorageError(MachineReviewError):
    """Refusal to write, read or validate machine-review storage."""


# --------------------------------------------------------------------------- #
# Shared helpers.
# --------------------------------------------------------------------------- #

def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _sha256_file(path: pathlib.Path) -> Tuple[str, int]:
    h, size = hashlib.sha256(), 0
    with open(_long(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def _long(path) -> str:
    """Windows extended-length form. Capture filenames are URL-derived and long."""
    import os
    p = str(path)
    if os.name != "nt":
        return p
    resolved = os.path.abspath(p)
    if resolved.startswith("\\\\?\\"):
        return resolved
    if resolved.startswith("\\\\"):
        return "\\\\?\\UNC" + resolved[1:]
    return "\\\\?\\" + resolved


def repo_relative(path, repo_root) -> str:
    """Posix path relative to the repository, so records travel between roots."""
    p, root = pathlib.Path(path), pathlib.Path(repo_root)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise StorageError("path_outside_repository:%s" % p) from exc


def artifact_class(relative_posix: str) -> str:
    """Classify by directory role, matching the backup tool's vocabulary."""
    parts = relative_posix.split("/")
    if "cas" in parts and "objects" in parts:
        return "cas_object"
    for part in parts:
        if part == "attestations":
            return "attestation"
        if part == "captures":
            return "capture"
        if part in ("retrieval", "rendered_retrieval"):
            return "retrieval"
        if part == "records":
            return "machine_review_record"
    return "report"


# --------------------------------------------------------------------------- #
# A. Evidence manifests -- immutable once written.
# --------------------------------------------------------------------------- #

def build_evidence_manifest(batch_dir, repo_root, *, captured_at: str = "") -> dict:
    """Metadata for every evidence file in one capture batch. Content-free."""
    batch = pathlib.Path(batch_dir)
    if not batch.is_dir():
        raise StorageError("missing_batch_directory:%s" % batch)
    entries: List[dict] = []
    for path in sorted(batch.rglob("*")):
        if not path.is_file():
            continue
        rel_in_batch = path.relative_to(batch).as_posix()
        if any(part in EXCLUDED_DIR_PARTS for part in rel_in_batch.split("/")[:-1]):
            continue
        if path.name in (EVIDENCE_MANIFEST_NAME, EVIDENCE_MANIFEST_HASH_NAME):
            continue
        rel = repo_relative(path, repo_root)
        digest, size = _sha256_file(path)
        entries.append({
            "relative_path": rel,
            "byte_size": size,
            "sha256": digest,
            "artifact_class": artifact_class(rel),
            "captured_at": captured_at,
        })
    return {
        "schema": EVIDENCE_MANIFEST_SCHEMA,
        "batch_id": batch.name,
        "file_count": len(entries),
        "total_bytes": sum(e["byte_size"] for e in entries),
        "files": entries,
    }


def write_evidence_manifest(manifest: Mapping, batch_dir) -> Tuple[pathlib.Path, str]:
    """Write the manifest and its hash. Refuse to overwrite differing content.

    A manifest is a statement about what the evidence WAS. Rewriting one in place
    would let evidence change while its record of itself silently followed along,
    which is the failure this exists to make impossible.
    """
    batch = pathlib.Path(batch_dir)
    body = json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    target = batch / EVIDENCE_MANIFEST_NAME
    hash_target = batch / EVIDENCE_MANIFEST_HASH_NAME
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if existing != body:
            raise StorageError(
                "evidence_manifest_is_immutable:%s differs from the completed manifest"
                % target.name)
        return (target, digest)
    target.write_text(body, encoding="utf-8")
    hash_target.write_text("%s  %s\n" % (digest, EVIDENCE_MANIFEST_NAME),
                           encoding="utf-8")
    return (target, digest)


def verify_evidence_manifest(batch_dir, repo_root) -> List[str]:
    """Problems, or an empty list. Missing evidence is a problem, not a warning."""
    batch = pathlib.Path(batch_dir)
    target = batch / EVIDENCE_MANIFEST_NAME
    if not target.exists():
        return ["missing_evidence_manifest"]
    manifest = json.loads(target.read_text(encoding="utf-8"))
    problems = []
    stored = (batch / EVIDENCE_MANIFEST_HASH_NAME).read_text(encoding="utf-8").split()[0] \
        if (batch / EVIDENCE_MANIFEST_HASH_NAME).exists() else ""
    if stored != hashlib.sha256(target.read_text(encoding="utf-8").encode("utf-8")).hexdigest():
        problems.append("manifest_hash_mismatch")
    root = pathlib.Path(repo_root)
    for entry in manifest.get("files", []):
        path = root / entry["relative_path"]
        if not _os.path.exists(_long(path)):
            problems.append("missing_evidence:%s" % entry["relative_path"])
            continue
        digest, size = _sha256_file(path)
        if digest != entry["sha256"] or size != entry["byte_size"]:
            problems.append("changed_evidence:%s" % entry["relative_path"])
    return problems


# --------------------------------------------------------------------------- #
# B. PENDING_REVIEW records -- regenerable, gitignored.
# --------------------------------------------------------------------------- #

def records_dir(batch_id: str, repo_root) -> pathlib.Path:
    return pathlib.Path(repo_root) / RECORDS_ROOT / batch_id / "records"


def write_pending_records(records: Sequence, batch_id: str, repo_root) -> List[pathlib.Path]:
    """One file per hotel_id. A rerun over identical evidence rewrites identical
    bytes rather than adding a second record."""
    import os
    out = records_dir(batch_id, repo_root)
    os.makedirs(_long(out), exist_ok=True)
    written = []
    for record in records:
        if record.status != STATUS_PENDING_REVIEW:
            raise StorageError("only_pending_review_records_are_stored_here:%s"
                               % record.status)
        path = out / ("%s.json" % record.hotel_id)
        # Extended-length throughout: a hotel_id is long, and under a deeply
        # nested checkout the record path passes MAX_PATH, where a plain
        # ``exists()`` answers False and the record reads as missing rather
        # than as unreachable. A restored review must not depend on where the
        # repository happens to sit.
        with open(_long(path), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), indent=1, sort_keys=True,
                                ensure_ascii=False))
        written.append(path)
    return written


def load_pending_record(hotel_id: str, batch_id: str, repo_root) -> dict:
    import os
    path = records_dir(batch_id, repo_root) / ("%s.json" % hotel_id)
    if not os.path.exists(_long(path)):
        raise StorageError("missing_machine_review_record:%s" % hotel_id)
    with open(_long(path), "r", encoding="utf-8") as fh:
        return json.loads(fh.read())


def rederive_record_hash(record: Mapping) -> str:
    """The hash implied by the record's own content, ignoring what is stored."""
    rebuilt = {k: v for k, v in dict(record).items()
               if k not in ("created_at", "record_hash")}
    return "sha256:" + hashlib.sha256(_canonical(rebuilt).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# C. Durable decisions -- tracked, append-only.
# --------------------------------------------------------------------------- #

def empty_decisions() -> dict:
    return {"schema": DECISIONS_SCHEMA,
            "note": ("Append-only. A reversal or correction is a NEW entry; an "
                     "existing entry is never edited or removed. Carries no "
                     "screenshot, HTML, policy excerpt, absolute path or secret."),
            "decisions": []}


def load_decisions(repo_root) -> dict:
    path = pathlib.Path(repo_root) / DECISIONS_PATH
    if not path.exists():
        return empty_decisions()
    return json.loads(path.read_text(encoding="utf-8"))


def append_decision(store: Mapping, *, listing_key: str, hotel_id: str,
                    decision) -> dict:
    """Return a NEW store with one more entry. Never mutates an existing entry."""
    entry = {
        "listing_key": listing_key,
        "hotel_id": hotel_id,
        "reviewer_id": decision["reviewer_id"],
        "reviewed_at": decision["reviewed_at"],
        "decision": decision["decision"],
        "field_decisions": dict(decision.get("field_decisions") or {}),
        "overlap_approved": bool(decision.get("overlap_approved")),
        "notes": decision.get("notes", ""),
        "source_record_hash": decision["source_record_hash"],
        "approval_hash": decision["approval_hash"],
    }
    if entry["decision"] not in (DECISION_APPROVED, DECISION_REJECTED):
        raise StorageError("decision_must_be_approved_or_rejected:%s" % entry["decision"])
    existing = list(store.get("decisions") or [])
    if any(e["approval_hash"] == entry["approval_hash"] for e in existing):
        return dict(store, decisions=existing)          # idempotent re-append
    return dict(store, schema=store.get("schema", DECISIONS_SCHEMA),
                note=store.get("note", empty_decisions()["note"]),
                decisions=existing + [entry])


def latest_decision(store: Mapping, listing_key: str) -> Optional[dict]:
    """The most recent entry for a listing. Order is append order, not time:
    a reversal is appended after the decision it reverses."""
    found = [e for e in (store.get("decisions") or [])
             if e.get("listing_key") == listing_key]
    return found[-1] if found else None


def write_decisions(store: Mapping, repo_root) -> pathlib.Path:
    path = pathlib.Path(repo_root) / DECISIONS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=1, sort_keys=True, ensure_ascii=False)
                    + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# D. The git-safe index.
# --------------------------------------------------------------------------- #

def safe_url(url: str) -> Tuple[str, str]:
    """``(url_or_empty, omission_reason)``.

    A URL with a tracking or credential-shaped query is recorded WITHOUT its
    query rather than dropped: the path identifies the property and is the part
    a reader needs; the parameters are the part that must not be republished.
    """
    from urllib.parse import urlsplit, parse_qsl, urlunsplit
    if not url:
        return ("", "missing_url")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return ("", "non_web_scheme")
    if "@" in (parts.netloc or ""):
        return ("", "embedded_userinfo")
    host = (parts.hostname or "").lower()
    if not host or host in ("localhost",) or host.endswith(".local") \
            or host.startswith(("127.", "10.", "192.168.")):
        return ("", "private_or_local_host")
    if _CREDENTIAL_RE.search(url):
        return ("", "credential_shaped_value")
    keys = {k.lower() for k, _v in parse_qsl(parts.query, keep_blank_values=True)}
    if keys & set(_TRACKING_QUERY_KEYS):
        return (urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")),
                "tracking_query_stripped")
    return (urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, "")), "")


def build_index(records: Iterable[Mapping]) -> dict:
    """Git-safe metadata only. No excerpt, no path, no HTML, no screenshot."""
    rows = []
    stripped = 0
    for record in records:
        url, reason = safe_url(record.get("normalized_url", ""))
        row = {
            "hotel_id": record["hotel_id"],
            "listing_key": record["listing_key"],
            "record_hash": record["record_hash"],
            "extraction_result_hash": record["extraction_result_hash"],
            "capture_sha256": record["capture_sha256"],
            "screenshot_sha256": record["screenshot_sha256"],
            "identity_outcome": record["identity_outcome"],
            "published_overlap": record["published_overlap"],
            "status": record["status"],
            "capture_commit": record["capture_commit"],
        }
        if url:
            row["normalized_url"] = url
        if reason:
            row["normalized_url_note"] = reason
            stripped += 1
        rows.append(row)
    rows.sort(key=lambda r: r["hotel_id"])
    return {
        "schema": INDEX_SCHEMA,
        "description": ("Git-safe metadata about machine-verified capture reviews. "
                        "Contains no page HTML, no screenshots, no policy excerpts, "
                        "no headers, no cookies, no tokens and no absolute paths. "
                        "The evidence itself lives outside git -- see "
                        "docs/pettripfinder/ARTIFACT_BACKUP_RUNBOOK.md."),
        "totals": {"records": len(rows), "publishable": 0,
                   "normalized_url_adjusted": stripped},
        "records": rows,
    }


def write_index(index: Mapping, repo_root) -> pathlib.Path:
    path = pathlib.Path(repo_root) / INDEX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=1, sort_keys=True, ensure_ascii=False)
                    + "\n", encoding="utf-8")
    return path


def tracked_file_problems(path) -> List[str]:
    """Credential, absolute-path and forbidden-field scan for a tracked file."""
    body = pathlib.Path(path).read_text(encoding="utf-8")
    problems = []
    if _ABSOLUTE_PATH_RE.search(body):
        problems.append("absolute_path_present")
    if _CREDENTIAL_RE.search(body):
        problems.append("credential_shaped_value_present")

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key.lower() in FORBIDDEN_TRACKED_KEYS:
                    problems.append("forbidden_field:%s" % key)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(json.loads(body))
    return sorted(set(problems))


# --------------------------------------------------------------------------- #
# E. Promotion lookup.
# --------------------------------------------------------------------------- #

def promotion_lookup(listing_key: str, *, batch_id: str, repo_root,
                     decisions: Optional[Mapping] = None) -> dict:
    """The facts promotion may use for one listing, or a refusal.

    Deliberately separate from operator-attestation promotion: it reads a
    different decisions file, a different record store, and never consults an
    attestation.
    """
    store = decisions if decisions is not None else load_decisions(repo_root)
    decision = latest_decision(store, listing_key)
    if decision is None:
        raise StorageError("promotion_refused:no_decision_for:%s" % listing_key)
    if decision["decision"] != DECISION_APPROVED:
        raise StorageError("promotion_refused:decision=%s" % decision["decision"])

    record = load_pending_record(decision["hotel_id"], batch_id, repo_root)
    if record.get("status") != STATUS_PENDING_REVIEW:
        raise StorageError("promotion_refused:unexpected_record_status:%s"
                           % record.get("status"))

    rebuilt = rederive_record_hash(record)
    if rebuilt != decision["source_record_hash"]:
        raise StorageError("promotion_refused:stale_or_mismatched_source_hash")

    root = pathlib.Path(repo_root)
    for path_field, hash_field in (("capture_path", "capture_sha256"),
                                   ("screenshot_path", "screenshot_sha256"),
                                   ("view_path", "view_sha256")):
        path = root / record[path_field]
        if not _os.path.exists(_long(path)):
            raise StorageError("promotion_refused:missing_evidence:%s"
                               % record[path_field])
        digest, _size = _sha256_file(path)
        if digest != record[hash_field]:
            raise StorageError("promotion_refused:changed_evidence:%s"
                               % record[path_field])

    with open(_long(root / record["capture_path"]), "r", encoding="utf-8") as fh:
        capture = json.loads(fh.read())
    for field, recorded in (("text", record["rendered_text_sha256"]),
                            ("html", record["html_sha256"])):
        digest = hashlib.sha256((capture.get(field) or "").encode("utf-8")).hexdigest()
        if digest != recorded or digest != capture.get("%s_sha256" % field):
            raise StorageError("promotion_refused:changed_evidence:capture.%s" % field)

    if record.get("published_overlap") == OVERLAP_COMPARE_ONLY \
            and not decision.get("overlap_approved"):
        raise StorageError(
            "promotion_refused:published_overlap_not_specifically_approved")

    rejected = {k for k, v in (decision.get("field_decisions") or {}).items()
                if v == DECISION_REJECTED}
    return {
        "hotel_id": record["hotel_id"],
        "listing_key": record["listing_key"],
        "normalized_url": record["normalized_url"],
        "facts": {k: v for k, v in (record.get("facts") or {}).items()
                  if k not in rejected},
        "withheld_fields": sorted(rejected),
        "source_record_hash": rebuilt,
        "approval_hash": decision["approval_hash"],
        "published_overlap": record.get("published_overlap"),
    }
