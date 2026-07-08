"""Preview Engine.

Turns an in-memory StaticSitePackage into a fully browsable local website
and reports the result as an immutable PreviewBuild.

All filesystem writes are delegated to the Static Site Repository — the
engine itself only orchestrates the write and performs the Phase 4
quality checks:

    * homepage exists
    * manifest exists
    * robots exists
    * sitemap exists
    * all pages written
    * all assets written
    * manifest hashes verify
    * no duplicate paths

Given the same StaticSitePackage and the same preview root, the engine
produces byte-identical output and an identical PreviewBuild.

No deployment. No hosting. No server. The preview is plain files that a
browser can open directly.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from engines.preview.preview_models import PreviewBuild
from engines.website_generator.models import StaticSitePackage
from repositories.static_site_repository import (
    MANIFEST_FILENAME,
    StaticSiteRepository,
    StaticSiteRepositoryError,
)

_HOMEPAGE_RELATIVE_PATH = "index.html"
_ROBOTS_RELATIVE_PATH = "robots.txt"
_SITEMAP_RELATIVE_PATH = "sitemap.xml"


class PreviewEngine:
    """Generate and validate a local preview build."""

    def __init__(self, repository: StaticSiteRepository | None = None) -> None:
        self._repository = repository or StaticSiteRepository()

    def build_preview(
        self,
        package: StaticSitePackage,
        preview_root: Path | str,
    ) -> PreviewBuild:
        """Write ``package`` below ``preview_root`` and validate it."""
        root = Path(preview_root)

        try:
            written = self._repository.write(package, root)
        except StaticSiteRepositoryError as error:
            return PreviewBuild(
                preview_path=str(root),
                page_count=len(package.pages),
                asset_count=len(package.assets) + len(package.system_files),
                manifest_path=str(root / MANIFEST_FILENAME),
                homepage_path=str(root / _HOMEPAGE_RELATIVE_PATH),
                preview_ready=False,
                issues=(f"write failed: {error}",),
            )

        issues = self._quality_checks(package, root, written)

        return PreviewBuild(
            preview_path=str(root),
            page_count=len(package.pages),
            asset_count=len(package.assets) + len(package.system_files),
            manifest_path=str(root / MANIFEST_FILENAME),
            homepage_path=str(root / _HOMEPAGE_RELATIVE_PATH),
            preview_ready=not issues,
            issues=issues,
        )

    # ------------------------------------------------------------------
    # Quality checks
    # ------------------------------------------------------------------

    def _quality_checks(
        self,
        package: StaticSitePackage,
        root: Path,
        written: tuple[str, ...],
    ) -> tuple[str, ...]:
        issues: list[str] = []

        issues.extend(self._required_file_checks(root))
        issues.extend(self._page_checks(package, root))
        issues.extend(self._asset_checks(package, root))
        issues.extend(self._duplicate_checks(written))
        issues.extend(self._manifest_hash_checks(package, root))

        return tuple(sorted(set(issues)))

    def _required_file_checks(self, root: Path) -> list[str]:
        issues: list[str] = []

        required = (
            ("homepage", _HOMEPAGE_RELATIVE_PATH),
            ("manifest", MANIFEST_FILENAME),
            ("robots", _ROBOTS_RELATIVE_PATH),
            ("sitemap", _SITEMAP_RELATIVE_PATH),
        )

        for label, relative_path in required:
            if not self._resolve(root, relative_path).is_file():
                issues.append(f"{label} missing: {relative_path}")

        return issues

    def _page_checks(
        self,
        package: StaticSitePackage,
        root: Path,
    ) -> list[str]:
        issues: list[str] = []

        for page in package.pages:
            relative_path = self._repository.relative_file_path(page.path)

            if not self._resolve(root, relative_path).is_file():
                issues.append(f"page not written: {relative_path}")

        return issues

    def _asset_checks(
        self,
        package: StaticSitePackage,
        root: Path,
    ) -> list[str]:
        issues: list[str] = []

        for asset in package.assets + package.system_files:
            relative_path = self._repository.relative_file_path(asset.path)

            if not self._resolve(root, relative_path).is_file():
                issues.append(f"asset not written: {relative_path}")

        return issues

    @staticmethod
    def _duplicate_checks(written: tuple[str, ...]) -> list[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()

        for relative_path in written:
            if relative_path in seen:
                duplicates.add(relative_path)

            seen.add(relative_path)

        return [f"duplicate output path: {path}" for path in sorted(duplicates)]

    def _manifest_hash_checks(
        self,
        package: StaticSitePackage,
        root: Path,
    ) -> list[str]:
        return [
            f"manifest verification failed: {issue}"
            for issue in self._repository.verify(package, root)
        ]

    @staticmethod
    def _resolve(root: Path, relative_path: str) -> Path:
        return root.joinpath(*PurePosixPath(relative_path).parts)
