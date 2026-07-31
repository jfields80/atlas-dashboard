#!/usr/bin/env python3
"""Full-snapshot backup for PetTripFinder worker artifacts (Phase 1).

The worker-run tree under ``data/worker_runs/pettripfinder`` is gitignored and
untracked. It holds the only copies of operator attestations, the browser
captures behind them, and the content-addressed objects those attestations
cite. Several source sites now block automated retrieval, so a lost capture
cannot be re-fetched -- it can only be re-earned by a human opening the page
again. This tool exists so that never becomes necessary.

Phase 1 scope
-------------
Full snapshots only. No incremental mode, no pruning, no deletion, no upload.
At ~28 MB a full snapshot takes seconds and has no dependency chain that can be
reasoned about incorrectly during a recovery.

SECURITY -- read before changing this file
------------------------------------------
Captured pages are verbatim copies of third-party HTML. They have been observed
to contain third-party Google Maps API keys embedded in the publisher's own
markup. Those keys are not ours, but they are real. Therefore:

  * capture bodies, screenshots and CAS objects MUST NOT be committed to git;
  * snapshots MUST NOT be uploaded anywhere unencrypted;
  * this tool never prints file contents, and redacts anything resembling a
    credential before writing an error message.

The manifest carries metadata only: relative path, byte size, SHA-256,
artifact class, and the snapshot timestamp.

This module is deliberately self-contained (it re-implements a few small
helpers rather than importing them). A disaster-recovery tool should keep
working when the surrounding package does not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

SCHEMA = "atlas-worker-backup/1.1"
NAMESPACE_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
EXCLUDED_DIR_PART = "site"  # every **/site/** rendered-preview tree
MANIFEST_NAME = "manifest.json"
MANIFEST_HASH_NAME = "manifest.sha256"
PAYLOAD_DIRNAME = "payload"
PARTIAL_SUFFIX = "-partial"
READ_CHUNK = 1024 * 1024

# Patterns redacted from any message that could reach a console or a log.
_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"nfp_[A-Za-z0-9]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S{8,}"),
]


class BackupError(RuntimeError):
    """Raised for any refusal or verification failure."""


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def redact(text: str) -> str:
    """Mask anything that looks like a credential before it is displayed."""
    out = str(text)
    for rx in _SECRET_PATTERNS:
        out = rx.sub("[REDACTED]", out)
    return out


def sha256_file(path: Path) -> Tuple[str, int]:
    """Return (hex digest, byte size). Streams; never holds the file in memory."""
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(READ_CHUNK)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_stamp(now: Optional[datetime] = None) -> str:
    """Snapshot id: compact UTC, filesystem-safe on Windows (no colons)."""
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H%M%SZ")


def artifact_class(relative_posix: str) -> str:
    """Classify by directory role. Drives retention reasoning, not behaviour."""
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
        if part == "model_results":
            return "model_result"
        if part == "assignments":
            return "assignment"
        if part == "validated_results":
            return "validated_result"
        if part == "routing_envelopes":
            return "routing_envelope"
        if part == EXCLUDED_DIR_PART:
            return "derived_preview"
    return "report"


def is_excluded(relative_posix: str) -> bool:
    """True for every path under a ``site/`` directory at any depth."""
    return EXCLUDED_DIR_PART in relative_posix.split("/")[:-1]


def find_repo_root(start: Path) -> Optional[Path]:
    """Nearest ancestor containing a .git entry, or None. No subprocess.

    The path MUST be resolved first. A relative path such as
    ``data/worker_runs/pettripfinder`` has parents ``data/worker_runs``,
    ``data`` and ``.`` -- none of which contain ``.git`` when the repository
    root is two levels above the working directory. Walking it unresolved
    silently returns None and disables the in-repository refusal entirely.
    """
    try:
        start = Path(start).resolve()
    except OSError:
        return None
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def is_within(child: Path, parent: Path) -> bool:
    """True when child == parent or child is nested under parent."""
    try:
        child = child.resolve()
        parent = parent.resolve()
    except OSError:
        return False
    return child == parent or parent in child.parents


# --------------------------------------------------------------------------- #
# Source namespaces
# --------------------------------------------------------------------------- #
# A snapshot may cover more than one artifact tree. Each tree is stored under a
# distinct namespace directory inside payload/, so two roots can contain files
# with identical relative paths without colliding. Namespaces are always
# explicit at restore time -- the tool will not guess where a tree belongs.

def parse_source_arg(value: str) -> Tuple[str, Path]:
    """Parse ``NAMESPACE=PATH`` or bare ``PATH`` (namespace = directory name).

    A Windows drive letter is not a namespace separator: ``C:\\x`` splits on
    the first ``=`` only, so bare absolute paths remain unambiguous.
    """
    if "=" in value:
        namespace, _, raw = value.partition("=")
        namespace = namespace.strip()
        path = Path(raw.strip())
        if not namespace:
            raise BackupError(f"empty namespace in --source-root '{value}'")
    else:
        path = Path(value)
        namespace = path.resolve().name
    if not NAMESPACE_RX.match(namespace):
        raise BackupError(
            f"invalid namespace '{namespace}': use letters, digits, dot, dash "
            "or underscore (no path separators), 1-64 characters"
        )
    return namespace, path


def normalize_source_roots(
    source_root: Optional[Path] = None,
    source_roots: Optional[Dict[str, Path]] = None,
) -> "Dict[str, Path]":
    """Accept either the single-root form or an explicit namespace map."""
    if source_roots and source_root is not None:
        raise BackupError("pass source_root or source_roots, not both")
    if source_roots:
        result = {}
        for namespace, path in source_roots.items():
            if not NAMESPACE_RX.match(str(namespace)):
                raise BackupError(f"invalid namespace '{namespace}'")
            result[str(namespace)] = Path(path)
        return result
    if source_root is None:
        raise BackupError("no source root supplied")
    path = Path(source_root)
    return {path.resolve().name: path}


def collect_source_roots(values: Iterable[str]) -> "Dict[str, Path]":
    """Build the namespace map from repeated CLI arguments, refusing dupes."""
    roots: Dict[str, Path] = {}
    seen_paths: Dict[str, str] = {}
    for value in values:
        namespace, path = parse_source_arg(value)
        if namespace in roots:
            raise BackupError(
                f"duplicate source namespace '{namespace}'. Two roots cannot "
                "share a namespace; give one an explicit NAME=PATH."
            )
        resolved = str(path.resolve()).lower()
        if resolved in seen_paths:
            raise BackupError(
                f"source root '{path}' supplied twice (as '{seen_paths[resolved]}' "
                f"and '{namespace}')"
            )
        roots[namespace] = path
        seen_paths[resolved] = namespace
    if not roots:
        raise BackupError("at least one --source-root is required")
    return roots


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #

def validate_roots(source_root: Path, backup_root: Path) -> None:
    """Refuse any configuration that could damage or self-nest the source.

    Both roots are resolved to absolute paths up front. Every refusal below
    depends on ancestry comparison, and ancestry is meaningless for a relative
    path.
    """
    if not source_root.exists() or not source_root.is_dir():
        raise BackupError(
            f"source root does not exist or is not a directory: {source_root}"
        )

    if is_within(backup_root, source_root):
        raise BackupError(
            "backup root resolves inside the source root; a snapshot must never "
            f"be written into the tree it is copying ({backup_root})"
        )

    if is_within(source_root, backup_root):
        raise BackupError(
            "source root resolves inside the backup root; refusing to snapshot a "
            f"tree that contains its own destination ({source_root})"
        )

    repo_root = find_repo_root(source_root)
    if repo_root is not None and is_within(backup_root, repo_root):
        raise BackupError(
            "backup root resolves inside the git repository "
            f"({repo_root}). Snapshots contain third-party page captures and "
            "must live outside the repo so no git operation can reach them."
        )


# --------------------------------------------------------------------------- #
# Scan + manifest
# --------------------------------------------------------------------------- #

def scan_source(source_root: Path) -> List[Path]:
    """Every included file, sorted for deterministic manifests."""
    found: List[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source_root).as_posix()
        if is_excluded(rel):
            continue
        found.append(path)
    return sorted(found, key=lambda p: p.relative_to(source_root).as_posix())


def build_entries(source_root: Path, files: Iterable[Path], stamp: str,
                  namespace: str) -> List[Dict]:
    entries: List[Dict] = []
    for path in files:
        rel = path.relative_to(source_root).as_posix()
        digest, size = sha256_file(path)
        entries.append(
            {
                "source_namespace": namespace,
                "relative_path": rel,
                "byte_size": size,
                "sha256": digest,
                "artifact_class": artifact_class(rel),
                "snapshot_timestamp_utc": stamp,
            }
        )
    return entries


def build_manifest(entries: List[Dict], stamp: str, snapshot_name: str,
                   namespaces: Iterable[str]) -> Dict:
    payload_digest = sha256_bytes(
        "\n".join(
            f"{e['source_namespace']}/{e['relative_path']}  {e['sha256']}"
            for e in entries
        ).encode("utf-8")
    )
    by_class: Dict[str, int] = {}
    sources: Dict[str, Dict[str, int]] = {ns: {"files": 0, "bytes": 0} for ns in namespaces}
    for entry in entries:
        by_class[entry["artifact_class"]] = by_class.get(entry["artifact_class"], 0) + 1
        bucket = sources.setdefault(entry["source_namespace"], {"files": 0, "bytes": 0})
        bucket["files"] += 1
        bucket["bytes"] += entry["byte_size"]
    return {
        "schema": SCHEMA,
        "snapshot_id": snapshot_name,
        "created_at_utc": stamp,
        "exclusions": ["**/site/**"],
        "sources": dict(sorted(sources.items())),
        "totals": {
            "files": len(entries),
            "bytes": sum(e["byte_size"] for e in entries),
            "by_class": dict(sorted(by_class.items())),
        },
        "payload_digest": payload_digest,
        "files": entries,
    }


# --------------------------------------------------------------------------- #
# Snapshot
# --------------------------------------------------------------------------- #

def copy_and_verify(roots: Dict[str, Path], payload_root: Path,
                    entries: List[Dict]) -> None:
    """Copy each file, then re-hash the destination. Abort on first mismatch."""
    for entry in entries:
        namespace = entry["source_namespace"]
        rel = entry["relative_path"]
        src = roots[namespace] / rel
        dst = payload_root / namespace / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        digest, size = sha256_file(dst)
        if digest != entry["sha256"] or size != entry["byte_size"]:
            raise BackupError(
                "destination verification failed after copy for "
                f"{redact(namespace + '/' + rel)} (expected {entry['sha256'][:16]}…/"
                f"{entry['byte_size']}B, got {digest[:16]}…/{size}B)"
            )


def create_snapshot(source_root: Optional[Path] = None,
                    backup_root: Optional[Path] = None,
                    snapshot_name: Optional[str] = None,
                    dry_run: bool = False,
                    now: Optional[datetime] = None,
                    source_roots: Optional[Dict[str, Path]] = None) -> Dict:
    """Create one verified full snapshot across one or more source roots."""
    if backup_root is None:
        raise BackupError("backup_root is required")
    roots = normalize_source_roots(source_root, source_roots)

    # Resolve before any ancestry check. See validate_roots / find_repo_root.
    backup_root = Path(backup_root).resolve()
    resolved: Dict[str, Path] = {}
    for namespace, path in roots.items():
        path = Path(path).resolve()
        validate_roots(path, backup_root)
        resolved[namespace] = path

    # Two namespaces must never resolve to the same tree.
    seen: Dict[Path, str] = {}
    for namespace, path in resolved.items():
        if path in seen:
            raise BackupError(
                f"namespaces '{seen[path]}' and '{namespace}' resolve to the "
                f"same source root ({path})"
            )
        seen[path] = namespace

    stamp = utc_stamp(now)
    name = snapshot_name or stamp

    snapshots_root = backup_root / "snapshots"
    final_dir = snapshots_root / name
    partial_dir = snapshots_root / (name + PARTIAL_SUFFIX)

    if final_dir.exists():
        raise BackupError(
            f"snapshot '{name}' already exists at {final_dir}; refusing to "
            "overwrite. Phase 1 never deletes or replaces a snapshot."
        )

    entries: List[Dict] = []
    for namespace, path in resolved.items():
        entries.extend(build_entries(path, scan_source(path), stamp, namespace))
    manifest = build_manifest(entries, stamp, name, resolved.keys())

    if dry_run:
        manifest["dry_run"] = True
        return manifest

    if partial_dir.exists():
        raise BackupError(
            f"a partial snapshot already exists at {partial_dir}; inspect and "
            "remove it manually before retrying (this tool never deletes)."
        )

    payload_root = partial_dir / PAYLOAD_DIRNAME
    payload_root.mkdir(parents=True, exist_ok=False)

    # Any failure below leaves the -partial directory in place, untouched, for
    # inspection. It is never promoted, so a half-written snapshot can never be
    # mistaken for a complete one.
    copy_and_verify(resolved, payload_root, entries)

    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=False).encode("utf-8")
    (partial_dir / MANIFEST_NAME).write_bytes(manifest_bytes)
    (partial_dir / MANIFEST_HASH_NAME).write_text(
        sha256_bytes(manifest_bytes) + "\n", encoding="utf-8"
    )

    os.rename(partial_dir, final_dir)  # atomic promotion
    return manifest


# --------------------------------------------------------------------------- #
# Attestation index (git-safe metadata)
# --------------------------------------------------------------------------- #
# The payload of an attestation must never enter git. Its *existence* and its
# hashes safely can, and that is worth a great deal: if a snapshot is ever lost,
# this index still says exactly what evidence existed and what it hashed to, so
# any recovered file can be proven authentic.
#
# Only these fields are emitted. Nothing else from the attestation is read out.

INDEX_SCHEMA = "atlas-attestation-index/1.0"

_UNSAFE_QUERY_KEYS = {
    "token", "access_token", "id_token", "auth", "authorization", "key",
    "apikey", "api_key", "sig", "signature", "session", "sessionid", "sid",
    "password", "secret", "credential", "x-amz-signature", "x-goog-signature",
}
_PRIVATE_HOSTS = re.compile(
    r"^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", re.I
)


def source_url_safety(url: str) -> Tuple[bool, str]:
    """Decide whether a source URL is safe to record in git-tracked metadata.

    Returns (is_safe, reason_when_unsafe).
    """
    from urllib.parse import urlsplit, parse_qsl

    if not url or not isinstance(url, str):
        return False, "missing_or_non_string"
    try:
        parts = urlsplit(url)
    except ValueError:
        return False, "unparseable_url"

    if parts.scheme not in ("http", "https"):
        return False, f"non_web_scheme:{parts.scheme or 'none'}"
    if "@" in parts.netloc:
        return False, "embedded_userinfo"
    host = parts.hostname or ""
    if not host or _PRIVATE_HOSTS.match(host):
        return False, "private_or_local_host"
    for pattern in _SECRET_PATTERNS:
        if pattern.search(url):
            return False, "credential_pattern_in_url"
    for key, _value in parse_qsl(parts.query, keep_blank_values=True):
        if key.strip().lower() in _UNSAFE_QUERY_KEYS:
            return False, f"credentialed_query_parameter:{key.strip().lower()}"
    return True, ""


def _index_entry(record: Dict) -> Dict:
    ingestion = record.get("ingestion") or {}
    affirmation = record.get("affirmation") or {}
    approval = record.get("approval") or {}
    screenshots = record.get("screenshots") or []
    capture_sha = ""
    if screenshots and isinstance(screenshots[0], dict):
        capture_sha = str(screenshots[0].get("sha256", ""))

    entry = {
        "listing_key": record.get("listing_key") or ingestion.get("listing_key", ""),
        "attestation_id": record.get("attestation_id", ""),
        "attestation_hash": record.get("attestation_hash", ""),
        "observed_at": record.get("observed_at", ""),
        "operator_id": affirmation.get("operator_id") or approval.get("approver_id", ""),
        "capture_sha256": capture_sha,
        "publishable": bool(record.get("publishable", False)),
    }

    url = record.get("official_url") or ingestion.get("canonical_url") or ""
    safe, reason = source_url_safety(url)
    if safe:
        entry["source_url"] = url
    else:
        entry["source_url_omitted"] = True
        entry["source_url_omission_reason"] = reason
    return entry


def build_attestation_index(source_root: Path) -> Dict:
    """Scan attestation records and emit git-safe metadata only."""
    source_root = Path(source_root)
    entries: List[Dict] = []
    for path in sorted(source_root.rglob("*.json")):
        parts = path.relative_to(source_root).as_posix().split("/")
        if "attestations" not in parts[:-1]:
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict) or not record.get("attestation_id"):
            continue
        entries.append(_index_entry(record))

    entries.sort(key=lambda e: (e["listing_key"], e["attestation_id"]))
    omitted = sum(1 for e in entries if e.get("source_url_omitted"))
    return {
        "schema": INDEX_SCHEMA,
        "description": (
            "Git-safe metadata about operator attestations. Contains no page "
            "HTML, no screenshots, no headers, no cookies, no tokens and no "
            "absolute paths. The evidence itself lives outside git and outside "
            "this repository -- see docs/pettripfinder/ARTIFACT_BACKUP_RUNBOOK.md."
        ),
        "totals": {
            "attestations": len(entries),
            "publishable": sum(1 for e in entries if e["publishable"]),
            "source_url_omitted": omitted,
        },
        "attestations": entries,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="backup_worker_artifacts",
        description="Create a verified full snapshot of PetTripFinder worker artifacts.",
    )
    # Both roots are REQUIRED and have no defaults, so no snapshot can ever be
    # written to an unreviewed location inside the repository.
    p.add_argument("--source-root", action="append", default=[], metavar="[NS=]PATH",
                   help="artifact root to snapshot; repeatable. Use NAME=PATH to "
                        "set an explicit namespace (default: directory name). "
                        "Each root is stored under payload/<namespace>/.")
    p.add_argument("--backup-root", type=Path, default=None,
                   help="destination root; must be OUTSIDE the git repository")
    p.add_argument("--snapshot-name", default=None,
                   help="optional snapshot id (default: UTC timestamp)")
    p.add_argument("--dry-run", action="store_true",
                   help="scan and report only; write nothing")
    p.add_argument("--emit-attestation-index", type=Path, default=None,
                   help="write the git-safe attestation index to this path and exit")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.emit_attestation_index is not None:
        try:
            roots = collect_source_roots(args.source_root)
            if len(roots) != 1:
                raise BackupError(
                    "--emit-attestation-index takes exactly one --source-root"
                )
            index = build_attestation_index(next(iter(roots.values())))
        except BackupError as exc:
            print(f"REFUSED: {redact(exc)}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"FAILED: {redact(exc)}", file=sys.stderr)
            return 1
        out = Path(args.emit_attestation_index)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        totals = index["totals"]
        print(f"attestation index written: {out}")
        print(f"  attestations       : {totals['attestations']}")
        print(f"  publishable        : {totals['publishable']}")
        print(f"  source_url omitted : {totals['source_url_omitted']}")
        return 0

    if args.backup_root is None:
        print("REFUSED: --backup-root is required (no default; it must be a "
              "reviewed location outside the git repository).", file=sys.stderr)
        return 2

    try:
        manifest = create_snapshot(
            source_roots=collect_source_roots(args.source_root),
            backup_root=args.backup_root,
            snapshot_name=args.snapshot_name,
            dry_run=args.dry_run,
        )
    except BackupError as exc:
        print(f"REFUSED: {redact(exc)}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"FAILED: {redact(exc)}", file=sys.stderr)
        return 1

    totals = manifest["totals"]
    mode = "DRY RUN (nothing written)" if manifest.get("dry_run") else "snapshot complete"
    print(f"{mode}: {manifest['snapshot_id']}")
    print(f"  files : {totals['files']}")
    print(f"  bytes : {totals['bytes']:,}")
    print("  sources:")
    for namespace, stats in manifest["sources"].items():
        print(f"    {namespace:<34} {stats['files']:>5} files  {stats['bytes']:>12,} B")
    print("  classes:")
    for cls, count in totals["by_class"].items():
        print(f"    {cls:<18} {count}")
    if not manifest.get("dry_run"):
        print(f"  written to: {Path(args.backup_root) / 'snapshots' / manifest['snapshot_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
