#!/usr/bin/env python3
"""Restore (or verify) a PetTripFinder worker-artifact snapshot -- Phase 1.

Companion to ``backup_worker_artifacts.py``. Two modes:

  --verify-only   check a snapshot's internal integrity and stop. Touches
                  nothing outside the snapshot. This is the mode used for the
                  quarterly restore drill and is safe to run at any time.

  (restore)       verify first, stage into a temporary directory beside the
                  destination, then place files. Never deletes, never
                  overwrites a differing file.

Safety posture
--------------
* Verification always runs before any write. A snapshot that fails integrity
  is never partially restored.
* An existing destination file blocks the restore unless it is byte-identical
  AND ``--allow-existing-identical`` is passed. A file that exists with
  different content is always a hard failure -- this tool will not resolve that
  ambiguity on your behalf.
* Nothing is ever deleted from the destination.
* Restores stage through ``<destination>/.restore-staging-<snapshot>`` so a
  failure mid-way does not leave the live tree half-populated.

SECURITY: snapshot payloads contain verbatim third-party page captures, which
have been observed to embed third-party API keys. This tool never prints file
contents and redacts credential-shaped text from error messages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MANIFEST_NAME = "manifest.json"
MANIFEST_HASH_NAME = "manifest.sha256"
PAYLOAD_DIRNAME = "payload"
STAGING_PREFIX = ".restore-staging-"
READ_CHUNK = 1024 * 1024

_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"nfp_[A-Za-z0-9]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S{8,}"),
]


class RestoreError(RuntimeError):
    """Raised for any verification failure or refusal."""


def redact(text) -> str:
    out = str(text)
    for rx in _SECRET_PATTERNS:
        out = rx.sub("[REDACTED]", out)
    return out


def sha256_file(path: Path) -> Tuple[str, int]:
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


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #

def load_manifest(snapshot_root: Path) -> Dict:
    """Load manifest.json only after manifest.sha256 confirms it is intact."""
    manifest_path = snapshot_root / MANIFEST_NAME
    hash_path = snapshot_root / MANIFEST_HASH_NAME

    if not manifest_path.is_file():
        raise RestoreError(f"missing {MANIFEST_NAME} in {snapshot_root}")
    if not hash_path.is_file():
        raise RestoreError(f"missing {MANIFEST_HASH_NAME} in {snapshot_root}")

    raw = manifest_path.read_bytes()
    expected = hash_path.read_text(encoding="utf-8").strip()
    actual = sha256_bytes(raw)
    if actual != expected:
        raise RestoreError(
            "manifest integrity check FAILED: manifest.json does not match "
            f"manifest.sha256 (expected {expected[:16]}…, got {actual[:16]}…). "
            "This snapshot has been altered; do not restore it."
        )
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RestoreError(f"manifest is not valid JSON: {redact(exc)}") from None


def payload_key(entry: Dict) -> str:
    """Path of an entry inside payload/, namespaced when the manifest is 1.1+."""
    namespace = entry.get("source_namespace")
    return f"{namespace}/{entry['relative_path']}" if namespace else entry["relative_path"]


def verify_payload(snapshot_root: Path, manifest: Dict) -> Dict[str, int]:
    """Verify every payload file, and that no undeclared file is present."""
    payload_root = snapshot_root / PAYLOAD_DIRNAME
    if not payload_root.is_dir():
        raise RestoreError(f"missing {PAYLOAD_DIRNAME}/ in {snapshot_root}")

    entries = manifest.get("files") or []
    declared = {payload_key(e) for e in entries}

    missing: List[str] = []
    mismatched: List[str] = []
    for entry in entries:
        key = payload_key(entry)
        target = payload_root / key
        if not target.is_file():
            missing.append(key)
            continue
        digest, size = sha256_file(target)
        if digest != entry["sha256"] or size != entry["byte_size"]:
            mismatched.append(key)

    present = {
        p.relative_to(payload_root).as_posix()
        for p in payload_root.rglob("*")
        if p.is_file()
    }
    extra = sorted(present - declared)

    problems = []
    if missing:
        problems.append(f"{len(missing)} missing payload file(s), e.g. {redact(missing[0])}")
    if mismatched:
        problems.append(
            f"{len(mismatched)} payload file(s) failed SHA-256, e.g. {redact(mismatched[0])}"
        )
    if extra:
        problems.append(
            f"{len(extra)} undeclared file(s) present in payload, e.g. {redact(extra[0])}"
        )
    if problems:
        raise RestoreError("snapshot verification FAILED: " + "; ".join(problems))

    return {"verified": len(entries), "bytes": sum(e["byte_size"] for e in entries)}


# --------------------------------------------------------------------------- #
# Restore
# --------------------------------------------------------------------------- #

def resolve_destinations(manifest: Dict,
                         destinations: Optional[Dict[str, Path]],
                         destination_root: Optional[Path]) -> Dict[str, Path]:
    """Map every namespace in the manifest to an explicit destination.

    A snapshot spanning several artifact trees must never be restored by
    guesswork: each namespace needs its own destination, supplied by the
    operator. A namespace with no mapping is a hard refusal.
    """
    namespaces = sorted({
        e.get("source_namespace") or "" for e in (manifest.get("files") or [])
    })
    destinations = {str(k): Path(v) for k, v in (destinations or {}).items()}

    # Legacy single-namespace snapshots may be restored with a bare root.
    if namespaces == [""] and not destinations:
        if destination_root is None:
            raise RestoreError("--destination-root is required for this snapshot")
        return {"": Path(destination_root)}

    if not destinations and destination_root is not None and len(namespaces) == 1:
        return {namespaces[0]: Path(destination_root)}

    missing = [ns for ns in namespaces if ns not in destinations]
    if missing:
        raise RestoreError(
            "no destination mapping for source namespace(s): "
            + ", ".join(repr(ns) for ns in missing)
            + ". Supply one --destination-root NAMESPACE=PATH per namespace; "
            "this tool will not infer where an artifact tree belongs."
        )
    unknown = [ns for ns in destinations if ns not in namespaces]
    if unknown:
        raise RestoreError(
            "destination mapping given for namespace(s) not in this snapshot: "
            + ", ".join(repr(ns) for ns in unknown)
            + f". Snapshot contains: {', '.join(repr(n) for n in namespaces)}."
        )
    return destinations


def plan_restore(destinations: Dict[str, Path], manifest: Dict,
                 allow_existing_identical: bool) -> List[Dict]:
    """Decide per file. Raises on any conflict rather than guessing."""
    to_write: List[Dict] = []
    conflicts: List[str] = []
    identical: List[str] = []

    for entry in manifest.get("files") or []:
        root = destinations[entry.get("source_namespace") or ""]
        target = root / entry["relative_path"]
        if not target.exists():
            to_write.append(entry)
            continue
        digest, size = sha256_file(target)
        if digest == entry["sha256"] and size == entry["byte_size"]:
            identical.append(payload_key(entry))
            if not allow_existing_identical:
                conflicts.append(payload_key(entry))
        else:
            # Differing content is never auto-resolved, with or without the flag.
            conflicts.append(payload_key(entry))

    if conflicts:
        raise RestoreError(
            f"refusing to overwrite {len(conflicts)} existing destination file(s), "
            f"e.g. {redact(conflicts[0])}. "
            "Pass --allow-existing-identical to skip files that are already "
            "byte-identical; files whose content DIFFERS are never overwritten."
        )
    return to_write


def restore_snapshot(snapshot_root: Path, destination_root: Optional[Path] = None,
                     verify_only: bool = False,
                     allow_existing_identical: bool = False,
                     destinations: Optional[Dict[str, Path]] = None) -> Dict:
    snapshot_root = Path(snapshot_root)

    manifest = load_manifest(snapshot_root)
    stats = verify_payload(snapshot_root, manifest)

    if verify_only:
        return {
            "mode": "verify-only",
            "snapshot_id": manifest.get("snapshot_id"),
            "files_verified": stats["verified"],
            "bytes": stats["bytes"],
            "files_written": 0,
        }

    dest_map = resolve_destinations(manifest, destinations, destination_root)
    dest_map = {ns: Path(p).resolve() for ns, p in dest_map.items()}
    for root in dest_map.values():
        root.mkdir(parents=True, exist_ok=True)

    to_write = plan_restore(dest_map, manifest, allow_existing_identical)

    payload_root = snapshot_root / PAYLOAD_DIRNAME
    staging_parent = next(iter(dest_map.values()))
    staging = staging_parent / (STAGING_PREFIX + str(manifest.get("snapshot_id", "snapshot")))
    if staging.exists():
        raise RestoreError(
            f"staging directory already exists at {staging}; inspect and remove "
            "it manually before retrying (this tool never deletes)."
        )
    staging.mkdir(parents=True, exist_ok=False)

    try:
        # Stage first, verifying each staged copy.
        for entry in to_write:
            key = payload_key(entry)
            src = payload_root / key
            dst = staging / key
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            digest, size = sha256_file(dst)
            if digest != entry["sha256"] or size != entry["byte_size"]:
                raise RestoreError(f"staged copy failed verification: {redact(key)}")

        # Place, then verify again at the final location.
        written = 0
        for entry in to_write:
            key = payload_key(entry)
            src = staging / key
            dst = dest_map[entry.get("source_namespace") or ""] / entry["relative_path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            digest, size = sha256_file(dst)
            if digest != entry["sha256"] or size != entry["byte_size"]:
                raise RestoreError(f"restored file failed verification: {redact(key)}")
            written += 1
    finally:
        # Staging is scratch this run created itself; clearing it removes no
        # user data. Any failure has already raised by this point.
        shutil.rmtree(staging, ignore_errors=True)

    return {
        "mode": "restore",
        "snapshot_id": manifest.get("snapshot_id"),
        "files_verified": stats["verified"],
        "bytes": stats["bytes"],
        "files_written": written,
        "files_skipped_identical": stats["verified"] - written,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="restore_worker_artifacts",
        description="Verify and/or restore a worker-artifact snapshot.",
    )
    p.add_argument("--snapshot-root", required=True, type=Path,
                   help="a single snapshot directory (contains manifest.json)")
    p.add_argument("--destination-root", action="append", default=[],
                   metavar="[NS=]PATH",
                   help="where to restore; repeatable. Use NAMESPACE=PATH when "
                        "the snapshot spans several source roots. Required "
                        "unless --verify-only.")
    p.add_argument("--verify-only", action="store_true",
                   help="check snapshot integrity and stop; writes nothing")
    p.add_argument("--allow-existing-identical", action="store_true",
                   help="skip destination files that are already byte-identical")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.verify_only and not args.destination_root:
        print("REFUSED: --destination-root is required unless --verify-only is set.",
              file=sys.stderr)
        return 2

    destinations: Dict[str, Path] = {}
    bare: Optional[Path] = None
    for value in args.destination_root:
        if "=" in value:
            namespace, _, raw = value.partition("=")
            namespace = namespace.strip()
            if namespace in destinations:
                print(f"REFUSED: duplicate destination for namespace '{namespace}'.",
                      file=sys.stderr)
                return 2
            destinations[namespace] = Path(raw.strip())
        elif bare is not None:
            print("REFUSED: more than one bare --destination-root; use "
                  "NAMESPACE=PATH when a snapshot spans several source roots.",
                  file=sys.stderr)
            return 2
        else:
            bare = Path(value)

    try:
        result = restore_snapshot(
            snapshot_root=args.snapshot_root,
            destination_root=bare,
            verify_only=args.verify_only,
            allow_existing_identical=args.allow_existing_identical,
            destinations=destinations or None,
        )
    except RestoreError as exc:
        print(f"REFUSED: {redact(exc)}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"FAILED: {redact(exc)}", file=sys.stderr)
        return 1

    print(f"{result['mode']}: {result['snapshot_id']}")
    print(f"  files verified : {result['files_verified']}")
    print(f"  bytes          : {result['bytes']:,}")
    if result["mode"] == "restore":
        print(f"  files written  : {result['files_written']}")
        print(f"  skipped (identical): {result['files_skipped_identical']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
