"""Section 1 — Project Structure Engine.

Pure computation of the project directory plan. Persistence happens in
ProjectAssemblyRepository, never here.
"""

from __future__ import annotations

from engines.directory_builder.models import ProjectStructurePlan
from engines.directory_builder.constants import PROJECT_DIRECTORIES

ENGINE_VERSION = "1.0.0"


class ProjectStructureEngine:
    """Computes the canonical, ordered directory layout for a project."""

    VERSION = ENGINE_VERSION

    @staticmethod
    def build(project_slug: str) -> ProjectStructurePlan:
        return ProjectStructurePlan(
            project_slug=project_slug,
            directories=tuple(PROJECT_DIRECTORIES),
        )
