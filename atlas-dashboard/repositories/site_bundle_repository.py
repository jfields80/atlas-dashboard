"""Site Bundle Repository (AES-WEB-001 §9.3; AES-WEB-002J.12).

Deterministic filesystem materialization of an in-memory ``SiteBundle``
(schema 1.1.0, ``engines/website_generation/contracts/artifacts.py``) to a
real directory tree, for preview/inspection. This is the WGE's only
directory-tree writer for rendered sites -- the twin of
``artifact_store_repository`` (§9.1, content-addressable JSON) and
``build_state_repository`` (§9.2, SQLite audit trail).

Scope (this delivery). Directory materialization, integrity verification,
and a ``bundle_manifest.json`` sidecar only. The deployment ZIP and
``LaunchCertificate`` embedding (§12.1) are explicitly deferred -- no
``LaunchCertificate`` is issued by the Quality Gate Engine yet (§5.10,
AES-WEB-002J.11), so packaging it would be premature.

Sequence, per §9.3 ("verifies every file's hash after write") and the
established staging discipline (mirrors ``artifact_store_repository``'s
atomic writes and the legacy ``static_site_repository``'s stage-then-replace
pattern):

1. Validate the ``SiteBundle`` shape in memory (no I/O): no duplicate or
   case-colliding paths, ``file_map`` keys exactly equal ``BundleFile``
   paths, every content hash matches ``file_map``, ``bundle_hash`` matches
   the canonical ``file_map``, every path is syntactically safe, no
   file/directory collisions. Fails fast, in this fixed order, before a
   single byte is written; each failing stage batch-reports every violation
   it found (never first-failure-only).
2. Validate the destination: not a symlink, no symlinked ancestor, absent or
   empty.
3. Materialize into a deterministically-named adjacent staging directory
   (``.<destination-name>.__staging__`` -- never a random/UUID/timestamp
   name), writing exact UTF-8 bytes (``content.encode("utf-8")``, no
   newline translation) in sorted path order, refusing to write through any
   symlink encountered at any directory level.
4. Emit ``bundle_manifest.json`` (deterministic JSON: UTF-8, sorted keys,
   ``ensure_ascii=False``, 2-space indent, trailing newline -- the same
   format the legacy ``static_site_repository`` uses).
5. Read every written file and the manifest back and re-verify bytes and
   hashes. A mismatch is never silently repaired -- it raises.
6. Atomically replace the destination with the fully-verified staging tree
   (a single ``os.replace``; the destination is either fully populated or
   left exactly as found -- never partially visible). The staging directory
   is removed on any failure at any stage.

Import boundary (§3.2): ``contracts/`` and standard-library storage drivers
only (``json, os, shutil, pathlib``, plus the ``dataclasses`` stdlib module
for the local result type) -- no engine, pipeline, service, or sibling
repository (``artifact_store_repository``) import. No network, AI, clock,
UUID, randomness, or environment-variable access.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from engines.website_generation.contracts.artifacts import (
    BundleFile,
    SiteBundle,
    canonical_json,
    sha256_of_text,
)
from engines.website_generation.contracts.errors import SiteBundleRepositoryError

MANIFEST_FILENAME = "bundle_manifest.json"

_STAGING_SUFFIX = ".__staging__"

# Characters forbidden anywhere in a single path segment (superset of the
# NTFS-reserved set; ":" alone also rejects drive-letter and stream-suffix
# forms, "\\" alone also rejects backslash-separated segments).
_FORBIDDEN_SEGMENT_CHARS: Tuple[str, ...] = ("\\", ":", "*", "?", '"', "<", ">", "|")

# Windows reserved device names (case-insensitive; the restriction applies
# to the segment's base name before its first "." -- e.g. "con.txt" too).
_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)


@dataclass(frozen=True)
class SiteBundleMaterialization:
    """Result of a successful ``SiteBundleRepository.materialize()`` call.

    Repository-local return type -- not a WGE artifact: no
    ``schema_version``/``artifact_kind``/``source_hashes``, not registered in
    ``contracts/versions.py``, not exported from the Website Generation
    Engine's public surface (``engines/website_generation/__init__.py``).
    """

    destination: str
    written_paths: Tuple[str, ...]
    bundle_hash: str
    manifest_path: str


def _is_symlink_or_reparse_point(path: Path) -> bool:
    """True if ``path`` is a POSIX/Windows symlink, or -- on Windows -- any
    other filesystem reparse point, most notably an NTFS junction.

    ``Path.is_symlink()`` alone does **not** detect junctions (confirmed
    empirically: ``mklink /J`` succeeds with no special privilege, yet
    ``is_symlink()`` reports ``False`` for the result), even though a
    junction redirects a write just as a symlink would. The symlink policy
    is fail-closed, so every symlink check in this module goes through this
    helper rather than ``Path.is_symlink()`` directly. Fails closed (treats
    an unreadable path as unsafe) on any stat error other than "does not
    exist".
    """
    if path.is_symlink():
        return True
    if sys.platform == "win32":
        try:
            attrs = os.stat(path, follow_symlinks=False).st_file_attributes
        except FileNotFoundError:
            return False
        except OSError:
            return True
        return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return False


def _validate_path_syntax(path: str) -> bool:
    """True if ``path`` is a safe, bundle-root-relative POSIX path.

    Defense-in-depth: :class:`BundleFile` documents ``path`` as always
    forward-slash, relative, and ``..``-free, but this repository never
    trusts that invariant from the outside -- every path is re-validated
    here before it is ever joined onto a filesystem location.
    """
    if not path or path.startswith("/"):
        return False  # empty, absolute, or protocol-relative/UNC-shaped
    if "\\" in path:
        return False
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in path):
        return False
    for segment in path.split("/"):
        if segment in ("", ".", ".."):
            return False
        if any(ch in _FORBIDDEN_SEGMENT_CHARS for ch in segment):
            return False
        if segment.split(".", 1)[0].upper() in _RESERVED_NAMES:
            return False
        if segment != segment.rstrip(" ."):
            return False  # trailing space or trailing dot
    return True


def _detect_duplicate_paths(files: Tuple[BundleFile, ...]) -> Tuple[str, ...]:
    seen: set = set()
    dupes: set = set()
    for bf in files:
        if bf.path in seen:
            dupes.add(bf.path)
        seen.add(bf.path)
    return tuple(sorted(dupes))


def _detect_case_collisions(files: Tuple[BundleFile, ...]) -> Tuple[str, ...]:
    by_lower: Dict[str, set] = {}
    for bf in files:
        by_lower.setdefault(bf.path.lower(), set()).add(bf.path)
    collisions: set = set()
    for distinct_paths in by_lower.values():
        if len(distinct_paths) > 1:
            collisions |= distinct_paths
    return tuple(sorted(collisions))


def _detect_mapping_mismatch(bundle: SiteBundle) -> Tuple[str, ...]:
    file_paths = {bf.path for bf in bundle.files}
    map_paths = set(bundle.file_map.keys())
    issues: List[str] = []
    for path in sorted(map_paths - file_paths):
        issues.append(f"file_map entry has no matching BundleFile: {path!r}")
    for path in sorted(file_paths - map_paths):
        issues.append(f"BundleFile has no file_map entry: {path!r}")
    return tuple(issues)


def _detect_hash_mismatches(bundle: SiteBundle) -> Tuple[str, ...]:
    issues: List[str] = []
    for bf in sorted(bundle.files, key=lambda f: f.path):
        expected = bundle.file_map.get(bf.path)
        actual = sha256_of_text(bf.content)
        if actual != expected:
            issues.append(f"{bf.path}: expected {expected}, actual {actual}")
    return tuple(issues)


def _bundle_hash_matches(bundle: SiteBundle) -> bool:
    expected = sha256_of_text(canonical_json(dict(bundle.file_map)))
    return expected == bundle.bundle_hash


def _detect_file_directory_collisions(files: Tuple[BundleFile, ...]) -> Tuple[str, ...]:
    """A path collides with another when it (or a case-insensitive match of
    it -- Windows NTFS and default macOS are case-insensitive, so ``Assets``
    and ``assets/logo.svg`` collide there exactly as ``assets`` and
    ``assets/logo.svg`` would) is a directory-prefix implied by another
    path."""
    file_paths = {bf.path for bf in files}
    lower_to_original: Dict[str, List[str]] = {}
    for path in file_paths:
        lower_to_original.setdefault(path.lower(), []).append(path)
    issues: set = set()
    for path in file_paths:
        parts = path.split("/")
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i])
            for original in lower_to_original.get(prefix.lower(), ()):
                issues.add(f"{original!r} is both a file and a directory prefix of {path!r}")
    return tuple(sorted(issues))


class SiteBundleRepository:
    """Materialize a ``SiteBundle`` to disk, deterministically (§9.3)."""

    def materialize(
        self,
        bundle: SiteBundle,
        output_root: Union[str, Path],
        build_id: Optional[str] = None,
    ) -> SiteBundleMaterialization:
        """Write every ``bundle.files`` entry plus ``bundle_manifest.json``
        below ``output_root``. Raises :class:`SiteBundleRepositoryError`
        (never returns a partial result) if the bundle is malformed, the
        destination is unsafe or non-empty, or any write/verification step
        fails. Never mutates ``bundle``."""
        self._validate_bundle_shape(bundle)
        destination = Path(output_root)
        self._validate_destination(destination)

        staging = self._staging_path(destination)
        self._prepare_staging(staging)

        try:
            written = self._write_files(bundle, staging)
            manifest_bytes = self._manifest_bytes(bundle, build_id)
            (staging / MANIFEST_FILENAME).write_bytes(manifest_bytes)
            self._verify_written(bundle, staging, manifest_bytes)
        except SiteBundleRepositoryError:
            self._cleanup_staging(staging)
            raise
        except OSError as exc:
            self._cleanup_staging(staging)
            raise SiteBundleRepositoryError(
                "filesystem write failed while materializing the site bundle",
                category="write_failure",
                diagnostics={"error": repr(exc)},
            ) from exc

        self._finalize(staging, destination)

        return SiteBundleMaterialization(
            destination=str(destination),
            written_paths=written,
            bundle_hash=bundle.bundle_hash,
            manifest_path=MANIFEST_FILENAME,
        )

    # -- pre-write validation (no I/O) --------------------------------------

    @staticmethod
    def _validate_bundle_shape(bundle: SiteBundle) -> None:
        """Deterministic fail-fast stage order; every violation within a
        stage is batch-reported at once (never first-failure-only)."""
        dupes = _detect_duplicate_paths(bundle.files)
        if dupes:
            raise SiteBundleRepositoryError(
                "duplicate BundleFile path(s)",
                category="duplicate_path",
                diagnostics={"paths": list(dupes)},
            )

        collisions = _detect_case_collisions(bundle.files)
        if collisions:
            raise SiteBundleRepositoryError(
                "case-only path collision(s)",
                category="case_collision",
                diagnostics={"paths": list(collisions)},
            )

        mapping_issues = _detect_mapping_mismatch(bundle)
        if mapping_issues:
            raise SiteBundleRepositoryError(
                "file_map does not exactly match BundleFile paths",
                category="mapping_mismatch",
                diagnostics={"issues": list(mapping_issues)},
            )

        hash_issues = _detect_hash_mismatches(bundle)
        if hash_issues:
            raise SiteBundleRepositoryError(
                "BundleFile content hash does not match file_map",
                category="content_hash_mismatch",
                diagnostics={"issues": list(hash_issues)},
            )

        if not _bundle_hash_matches(bundle):
            raise SiteBundleRepositoryError(
                "bundle_hash does not match the canonical file_map",
                category="bundle_hash_mismatch",
                diagnostics={"declared_bundle_hash": bundle.bundle_hash},
            )

        unsafe = tuple(
            sorted({bf.path for bf in bundle.files if not _validate_path_syntax(bf.path)})
        )
        if unsafe:
            raise SiteBundleRepositoryError(
                "unsafe bundle file path(s)",
                category="unsafe_path",
                diagnostics={"paths": list(unsafe)},
            )

        dir_collisions = _detect_file_directory_collisions(bundle.files)
        if dir_collisions:
            raise SiteBundleRepositoryError(
                "file/directory path collision(s)",
                category="file_directory_collision",
                diagnostics={"issues": list(dir_collisions)},
            )

    # -- destination + staging -----------------------------------------------

    @staticmethod
    def _validate_destination(destination: Path) -> None:
        for ancestor in destination.parents:
            if _is_symlink_or_reparse_point(ancestor):
                raise SiteBundleRepositoryError(
                    "an intermediate destination directory is a symlink",
                    category="symlink_detected",
                )
        if _is_symlink_or_reparse_point(destination):
            raise SiteBundleRepositoryError(
                "destination root is a symlink",
                category="symlink_detected",
            )
        if destination.exists():
            if not destination.is_dir():
                raise SiteBundleRepositoryError(
                    "destination exists and is not a directory",
                    category="invalid_destination",
                )
            if any(destination.iterdir()):
                raise SiteBundleRepositoryError(
                    "destination is not empty",
                    category="destination_not_empty",
                )

    @staticmethod
    def _staging_path(destination: Path) -> Path:
        return destination.parent / f".{destination.name}{_STAGING_SUFFIX}"

    @staticmethod
    def _prepare_staging(staging: Path) -> None:
        if _is_symlink_or_reparse_point(staging):
            raise SiteBundleRepositoryError(
                "the repository-owned staging path is a symlink",
                category="symlink_detected",
            )
        if staging.exists():
            if not staging.is_dir():
                raise SiteBundleRepositoryError(
                    "the repository-owned staging path exists and is not a directory",
                    category="staging_failure",
                    diagnostics={"staging_path": str(staging)},
                )
            # A stale leftover at our exact, deterministically-named,
            # repository-owned staging path (never a symlink, verified
            # above) from a prior interrupted run -- safe to remove.
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)

    # -- write ----------------------------------------------------------------

    def _write_files(self, bundle: SiteBundle, staging: Path) -> Tuple[str, ...]:
        written: List[str] = []
        for bf in sorted(bundle.files, key=lambda f: f.path):
            target = staging.joinpath(*bf.path.split("/"))
            self._assert_contained(target, staging)
            self._mkdir_checked(target.parent, staging)
            if _is_symlink_or_reparse_point(target):
                raise SiteBundleRepositoryError(
                    f"refusing to write through an existing symlink: {bf.path}",
                    category="symlink_detected",
                )
            target.write_bytes(bf.content.encode("utf-8"))
            written.append(bf.path)
        return tuple(sorted(written))

    @staticmethod
    def _assert_contained(target: Path, staging: Path) -> None:
        resolved_staging = staging.resolve(strict=False)
        resolved_target = target.resolve(strict=False)
        try:
            resolved_target.relative_to(resolved_staging)
        except ValueError:
            raise SiteBundleRepositoryError(
                "bundle file path escapes the destination root",
                category="unsafe_path",
                diagnostics={"target": str(target)},
            )

    @staticmethod
    def _mkdir_checked(directory: Path, staging: Path) -> None:
        relative = directory.relative_to(staging)
        current = staging
        for part in relative.parts:
            current = current / part
            if _is_symlink_or_reparse_point(current):
                raise SiteBundleRepositoryError(
                    "refusing to create a directory through a symlink",
                    category="symlink_detected",
                    diagnostics={"path": str(current)},
                )
            if current.exists():
                if not current.is_dir():
                    raise SiteBundleRepositoryError(
                        "a bundle file path segment collides with a directory",
                        category="file_directory_collision",
                        diagnostics={"path": str(current)},
                    )
            else:
                current.mkdir()

    @staticmethod
    def _manifest_bytes(bundle: SiteBundle, build_id: Optional[str]) -> bytes:
        payload: Dict[str, object] = {
            "file_map": dict(bundle.file_map),
            "bundle_hash": bundle.bundle_hash,
        }
        if build_id is not None:
            payload["build_id"] = build_id
        text = json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            separators=(",", ": "),
        )
        return f"{text}\n".encode("utf-8")

    # -- post-write verification ----------------------------------------------

    @staticmethod
    def _verify_written(bundle: SiteBundle, staging: Path, manifest_bytes: bytes) -> None:
        issues: List[str] = []
        for bf in sorted(bundle.files, key=lambda f: f.path):
            target = staging.joinpath(*bf.path.split("/"))
            try:
                actual_bytes = target.read_bytes()
            except OSError as exc:
                issues.append(f"{bf.path}: unreadable after write ({exc!r})")
                continue
            expected_bytes = bf.content.encode("utf-8")
            if actual_bytes != expected_bytes:
                issues.append(f"{bf.path}: byte mismatch after write")
                continue
            if sha256_of_text(bf.content) != bundle.file_map.get(bf.path):
                issues.append(f"{bf.path}: hash mismatch after write")

        manifest_target = staging / MANIFEST_FILENAME
        try:
            actual_manifest = manifest_target.read_bytes()
        except OSError as exc:
            issues.append(f"{MANIFEST_FILENAME}: unreadable after write ({exc!r})")
        else:
            if actual_manifest != manifest_bytes:
                issues.append(f"{MANIFEST_FILENAME}: content mismatch after write")

        if issues:
            raise SiteBundleRepositoryError(
                "post-write verification failed",
                category="post_write_verification_failure",
                diagnostics={"issues": issues},
            )

    # -- finalize / cleanup -----------------------------------------------------

    def _finalize(self, staging: Path, destination: Path) -> None:
        try:
            if destination.exists():
                destination.rmdir()  # only succeeds if still empty
            staging.replace(destination)
        except OSError as exc:
            self._cleanup_staging(staging)
            raise SiteBundleRepositoryError(
                "failed to atomically finalize the site bundle destination",
                category="staging_failure",
                diagnostics={"error": repr(exc)},
            ) from exc

    @staticmethod
    def _cleanup_staging(staging: Path) -> None:
        if not staging.exists() or _is_symlink_or_reparse_point(staging):
            return
        try:
            shutil.rmtree(staging)
        except OSError as exc:
            raise SiteBundleRepositoryError(
                "failed to clean up the staging directory after a prior failure",
                category="cleanup_failure",
                diagnostics={"staging_path": str(staging)},
            ) from exc
