"""Static Site Repository.

Deterministic filesystem persistence for a Website Generator
StaticSitePackage. This repository is the ONLY Phase 4 component that
touches the filesystem.

Responsibilities:
    * Map site paths ("/", "/about/", "assets/css/site.css") to a
      deterministic on-disk folder structure.
    * Write every page, asset, and system file plus manifest.json.
    * UTF-8 encoding, LF newlines (content is written as raw bytes, so no
      platform newline translation ever occurs — Windows included).
    * Overwrite an existing build safely: the new build is written to a
      staging directory first and only replaces the previous build after
      every file has been written successfully.
    * Never mutate the StaticSitePackage.
    * Verify that manifest hashes match the files actually on disk.

No deployment. No hosting. No network.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath

from engines.website_generator.models import (
    StaticSiteManifest,
    StaticSitePackage,
)

MANIFEST_FILENAME = "manifest.json"

_INDEX_FILENAME = "index.html"
_STAGING_SUFFIX = ".__staging__"
_FORBIDDEN_PART_CHARS = ("\\", ":", "*", "?", '"', "<", ">", "|")


class StaticSiteRepositoryError(ValueError):
    """Raised when a StaticSitePackage cannot be safely written to disk."""


def _dump_model(model: object) -> dict:
    """Dump a Pydantic model to a plain dict under Pydantic v1 or v2.

    Detection is done per-call on the model itself rather than via the
    ConfigDict import gate, because Pydantic 1.10.17+ ships a ConfigDict
    forward-compatibility shim while still lacking ``model_dump``.
    """
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]

    return model.dict()  # type: ignore[attr-defined]


class StaticSiteRepository:
    """Write a StaticSitePackage to disk deterministically."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(
        self,
        package: StaticSitePackage,
        output_root: Path | str,
    ) -> tuple[str, ...]:
        """Write the full static site below ``output_root``.

        Returns the sorted tuple of relative POSIX file paths written.
        Raises StaticSiteRepositoryError on duplicate or unsafe paths.
        """
        root = Path(output_root)
        file_map = self._build_file_map(package)

        root.parent.mkdir(parents=True, exist_ok=True)
        staging = root.parent / f".{root.name}{_STAGING_SUFFIX}"

        if staging.exists():
            shutil.rmtree(staging)

        try:
            for relative_path, content_bytes in file_map.items():
                target = staging.joinpath(*PurePosixPath(relative_path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content_bytes)

            if root.exists():
                shutil.rmtree(root)

            staging.replace(root)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

        return tuple(sorted(file_map))

    def verify(
        self,
        package: StaticSitePackage,
        output_root: Path | str,
    ) -> tuple[str, ...]:
        """Verify the on-disk build against the package manifest.

        Returns a sorted tuple of human-readable issue strings. An empty
        tuple means every manifest entry matched byte-for-byte and the
        serialized manifest.json itself is present and correct.
        """
        issues: list[str] = []
        root = Path(output_root)

        if not root.is_dir():
            return (f"output root does not exist: {root}",)

        manifest_target = root / MANIFEST_FILENAME

        if not manifest_target.is_file():
            issues.append(f"missing file: {MANIFEST_FILENAME}")
        elif manifest_target.read_bytes() != self.serialize_manifest(
            package.manifest
        ):
            issues.append(f"content mismatch: {MANIFEST_FILENAME}")

        for file_hash in sorted(package.manifest.files, key=lambda f: f.path):
            relative_path = self.relative_file_path(file_hash.path)
            target = root.joinpath(*PurePosixPath(relative_path).parts)

            if not target.is_file():
                issues.append(f"missing file: {relative_path}")
                continue

            content_bytes = target.read_bytes()

            if len(content_bytes) != file_hash.size_bytes:
                issues.append(
                    f"size mismatch: {relative_path} "
                    f"(expected {file_hash.size_bytes}, "
                    f"found {len(content_bytes)})"
                )

            actual_sha256 = hashlib.sha256(content_bytes).hexdigest()

            if actual_sha256 != file_hash.sha256:
                issues.append(f"hash mismatch: {relative_path}")

        return tuple(sorted(issues))

    @staticmethod
    def relative_file_path(site_path: str) -> str:
        """Map a package path to a relative POSIX filesystem path.

        Page paths are URL-style and rooted ("/", "/about/",
        "/categories/x/") and map to directory-index files. Asset and
        system-file paths ("assets/css/site.css", "robots.txt") are
        already relative and pass through unchanged.
        """
        stripped = site_path.strip()

        if stripped in ("", "/"):
            return _INDEX_FILENAME

        if stripped.startswith("/"):
            stripped = stripped[1:]

        if stripped.endswith("/"):
            stripped = f"{stripped}{_INDEX_FILENAME}"

        parts = PurePosixPath(stripped).parts

        if not parts:
            raise StaticSiteRepositoryError(
                f"unsafe or empty site path: {site_path!r}"
            )

        for part in parts:
            if part in (".", ".."):
                raise StaticSiteRepositoryError(
                    f"unsafe site path: {site_path!r}"
                )

            if any(char in part for char in _FORBIDDEN_PART_CHARS):
                raise StaticSiteRepositoryError(
                    f"unsafe site path: {site_path!r}"
                )

        return "/".join(parts)

    @staticmethod
    def serialize_manifest(manifest: StaticSiteManifest) -> bytes:
        """Deterministic UTF-8/LF JSON serialization of the manifest."""
        data = _dump_model(manifest)
        text = json.dumps(
            data,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            separators=(",", ": "),
        )
        return f"{text}\n".encode("utf-8")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_file_map(
        self,
        package: StaticSitePackage,
    ) -> dict[str, bytes]:
        """Build the complete relative-path -> bytes map for one build."""
        file_map: dict[str, bytes] = {}

        for page in package.pages:
            self._add_file(file_map, page.path, page.html)

        for asset in package.assets:
            self._add_file(file_map, asset.path, asset.content)

        for system_file in package.system_files:
            self._add_file(file_map, system_file.path, system_file.content)

        if MANIFEST_FILENAME in file_map:
            raise StaticSiteRepositoryError(
                f"package file collides with reserved path: "
                f"{MANIFEST_FILENAME}"
            )

        file_map[MANIFEST_FILENAME] = self.serialize_manifest(package.manifest)

        return file_map

    def _add_file(
        self,
        file_map: dict[str, bytes],
        site_path: str,
        content: str,
    ) -> None:
        relative_path = self.relative_file_path(site_path)

        if relative_path in file_map:
            raise StaticSiteRepositoryError(
                f"duplicate output path: {relative_path} "
                f"(from site path {site_path!r})"
            )

        file_map[relative_path] = content.encode("utf-8")
