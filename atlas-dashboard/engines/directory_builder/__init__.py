"""Directory Builder Engine — pure deterministic computation layer.

No Flask. No SQL. No I/O. Engines consume validated Pydantic models and
return validated Pydantic models. All versions are declared here so the
(frozen) Engine Version Registry can register this subsystem without
modification to registry code — see integration_changes/README.md.
"""

from engines.directory_builder.constants import ENGINE_NAME, ENGINE_VERSION
from engines.directory_builder.structure_engine import ProjectStructureEngine
from engines.directory_builder.import_package_engine import ImportPackageEngine
from engines.directory_builder.seo_build_engine import SeoBuildEngine
from engines.directory_builder.content_build_engine import ContentBuildEngine
from engines.directory_builder.image_package_engine import ImagePackageEngine
from engines.directory_builder.validation_engine import ImportValidationEngine
from engines.directory_builder.status_engine import ProjectStatusEngine
from engines.directory_builder.ai_queue_engine import AiBuildQueueEngine
from engines.directory_builder.quality_engine import QualityReportEngine
from engines.directory_builder.manifest_engine import BuildManifestEngine

ENGINE_VERSIONS = {
    "directory_builder": ENGINE_VERSION,
    "directory_builder.structure": ProjectStructureEngine.VERSION,
    "directory_builder.import_package": ImportPackageEngine.VERSION,
    "directory_builder.seo_build": SeoBuildEngine.VERSION,
    "directory_builder.content_build": ContentBuildEngine.VERSION,
    "directory_builder.image_package": ImagePackageEngine.VERSION,
    "directory_builder.validation": ImportValidationEngine.VERSION,
    "directory_builder.status": ProjectStatusEngine.VERSION,
    "directory_builder.ai_queue": AiBuildQueueEngine.VERSION,
    "directory_builder.quality": QualityReportEngine.VERSION,
    "directory_builder.manifest": BuildManifestEngine.VERSION,
}

__all__ = [
    "ENGINE_NAME",
    "ENGINE_VERSION",
    "ENGINE_VERSIONS",
    "ProjectStructureEngine",
    "ImportPackageEngine",
    "SeoBuildEngine",
    "ContentBuildEngine",
    "ImagePackageEngine",
    "ImportValidationEngine",
    "ProjectStatusEngine",
    "AiBuildQueueEngine",
    "QualityReportEngine",
    "BuildManifestEngine",
]
