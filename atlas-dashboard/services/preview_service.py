"""Preview Service.

Orchestrates the Phase 4 pipeline:

    ProjectAssembly
        -> StaticSiteGenerator.generate(assembly)   (existing, unmodified)
        -> StaticSiteRepository.write(package, ...)  (via PreviewEngine)
        -> PreviewEngine.build_preview(...)
        -> PreviewBuild

The service never mutates the ProjectAssembly and never mutates the
StaticSitePackage. Given the same assembly and the same preview root, the
resulting build is byte-identical.

No deployment. No hosting. Local preview only.
"""

from __future__ import annotations

from pathlib import Path

from engines.directory_builder.models import ProjectAssembly
from engines.preview.preview_engine import PreviewEngine
from engines.preview.preview_models import PreviewBuild
from engines.website_generator.static_site_generator import StaticSiteGenerator
from repositories.static_site_repository import StaticSiteRepository

DEFAULT_PREVIEW_ROOT = Path("previews")


class PreviewService:
    """Build a browsable local preview from a Directory Builder assembly."""

    def __init__(
        self,
        generator: StaticSiteGenerator | None = None,
        repository: StaticSiteRepository | None = None,
        preview_engine: PreviewEngine | None = None,
        preview_root: Path | str | None = None,
    ) -> None:
        self._generator = generator or StaticSiteGenerator()

        repository = repository or StaticSiteRepository()
        self._preview_engine = preview_engine or PreviewEngine(
            repository=repository
        )

        self._preview_root = (
            Path(preview_root)
            if preview_root is not None
            else DEFAULT_PREVIEW_ROOT
        )

    def build_preview(
        self,
        assembly: ProjectAssembly,
        preview_root: Path | str | None = None,
    ) -> PreviewBuild:
        """Generate the static site for ``assembly`` and write a preview.

        When ``preview_root`` is not given, the preview is written to
        ``<service preview root>/<project_slug>``.
        """
        root = (
            Path(preview_root)
            if preview_root is not None
            else self._preview_root / assembly.project_slug
        )

        package = self._generator.generate(assembly)

        return self._preview_engine.build_preview(package, root)
