"""DirectoryBuilderService — business orchestration for the Directory Builder.

Service layer only: wires repositories and engines together in a fixed,
replayable order. No computation lives here (engines) and no
serialization lives here (repositories). No Flask objects.

Pipeline:
    Launch Package (files)
        -> LaunchPackageRepository.load
        -> ProjectStructureEngine
        -> ImportPackageEngine
        -> SeoBuildEngine
        -> ImagePackageEngine
        -> ContentBuildEngine
        -> ImportValidationEngine
        -> AiBuildQueueEngine
        -> QualityReportEngine
        -> ProjectStatusEngine
        -> ProjectAssemblyRepository.write_assembly
        -> BuildManifestEngine
        -> ProjectAssemblyRepository.write_manifest
        -> BuildResult

Replayability: pass a fixed `built_at` (ISO-8601 string) to reproduce a
byte-identical build for identical inputs. When omitted, the current UTC
time is used. build_id is clock-independent either way.
"""

from __future__ import annotations

from datetime import datetime, timezone

from engines.directory_builder.models import BuildResult, ProjectAssembly
from engines.directory_builder.ai_queue_engine import AiBuildQueueEngine
from engines.directory_builder.content_build_engine import ContentBuildEngine
from engines.directory_builder.image_package_engine import ImagePackageEngine
from engines.directory_builder.import_package_engine import ImportPackageEngine
from engines.directory_builder.manifest_engine import BuildManifestEngine
from engines.directory_builder.quality_engine import QualityReportEngine
from engines.directory_builder.seo_build_engine import SeoBuildEngine
from engines.directory_builder.status_engine import ProjectStatusEngine
from engines.directory_builder.structure_engine import ProjectStructureEngine
from engines.directory_builder.validation_engine import ImportValidationEngine
from repositories.directory_builder.launch_package_repository import LaunchPackageRepository
from repositories.directory_builder.project_assembly_repository import ProjectAssemblyRepository


class DirectoryBuilderService:
    def __init__(
        self,
        launch_package_repository: LaunchPackageRepository,
        assembly_repository: ProjectAssemblyRepository,
    ) -> None:
        self._launch_packages = launch_package_repository
        self._assemblies = assembly_repository

    def build_project(self, package_dir: str, built_at: str | None = None) -> BuildResult:
        package = self._launch_packages.load(package_dir)
        project_slug = package.blueprint.project_slug

        structure = ProjectStructureEngine.build(project_slug)
        imports = ImportPackageEngine.build(package)
        seo = SeoBuildEngine.build(package, imports)
        images = ImagePackageEngine.build(package, imports)
        content = ContentBuildEngine.build(package, imports, seo, images)
        validation = ImportValidationEngine.build(imports, seo)
        queue = AiBuildQueueEngine.build(package, imports, content, images)
        quality = QualityReportEngine.build(package, imports, seo, content, images, validation)
        status = ProjectStatusEngine.build(project_slug, quality, validation, queue)

        assembly = ProjectAssembly(
            project_slug=project_slug,
            structure=structure,
            import_package=imports,
            seo_package=seo,
            content_package=content,
            image_package=images,
            validation_report=validation,
            status=status,
            ai_queue=queue,
            quality=quality,
        )

        files = self._assemblies.write_assembly(assembly)
        timestamp = built_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest = BuildManifestEngine.build(package, project_slug, timestamp, files)
        manifest_files = self._assemblies.write_manifest(assembly, manifest)

        return BuildResult(
            project_slug=project_slug,
            project_path=str(self._assemblies.project_path(project_slug)),
            assembly=assembly,
            manifest=manifest,
            files_written=tuple(sorted([f.path for f in files]) + list(manifest_files)),
        )
