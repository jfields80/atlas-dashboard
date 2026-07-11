"""Website Generation Engine (AES-WEB-001 Phase 1).

Public surface per AES-WEB-001 §3.4: the pipeline, the Phase 1 engine
classes, the artifact models and enums from ``contracts/``, and the
typed exception hierarchy. Internal helpers (state-machine internals,
canonicalization internals) are not exported here and may be refactored
freely provided public behavior and artifacts are unchanged.

This package is independent of the legacy ``engines/website_generator``
and ``engines/website_intelligence`` packages, which remain untouched.
"""

from engines.website_generation.contracts.artifacts import (
    ArtifactHeader,
    BrandPackage,
    BuildManifest,
    BusinessSpec,
    ComponentInstance,
    ComponentManifest,
    ContentBlock,
    ContentCandidate,
    ContentPackage,
    GateResult,
    LaunchCertificateBody,
    LayoutPlan,
    LayoutRegion,
    PageComponents,
    PageLayout,
    PagePlan,
    QualityReport,
    RenderedPage,
    RenderedPageSet,
    SEOEntry,
    SEOPackage,
    SiteArchitecture,
    SiteBundle,
    SpecCompilerInput,
    StageRecord,
    TransitionRecord,
    artifact_sha256,
    canonical_artifact_json,
    canonical_json,
    sha256_of_text,
)
from engines.website_generation.contracts.enums import (
    ArtifactKind,
    ArtifactLifecycleState,
    BuildState,
    GateSeverity,
    StageExecutionStatus,
    StageOutcome,
)
from engines.website_generation.contracts.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactValidationError,
    IllegalTransitionError,
    RepositoryCorruptionError,
    SchemaRegistrationError,
    SpecCompilationError,
    UnsupportedSchemaVersionError,
    WebsiteGenerationError,
)
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
    registered_artifact_model,
    registered_schema_versions,
)
from engines.website_generation.pipeline.website_generation_pipeline import (
    WebsiteGenerationBuildResult,
    WebsiteGenerationPipeline,
)
from engines.website_generation.speccompiler.business_spec_compiler import (
    BusinessSpecCompiler,
)

__all__ = [
    # pipeline + engines
    "WebsiteGenerationPipeline",
    "WebsiteGenerationBuildResult",
    "BusinessSpecCompiler",
    # artifact models
    "ArtifactHeader",
    "BrandPackage",
    "BuildManifest",
    "BusinessSpec",
    "ComponentInstance",
    "ComponentManifest",
    "ContentBlock",
    "ContentCandidate",
    "ContentPackage",
    "GateResult",
    "LaunchCertificateBody",
    "LayoutPlan",
    "LayoutRegion",
    "PageComponents",
    "PageLayout",
    "PagePlan",
    "QualityReport",
    "RenderedPage",
    "RenderedPageSet",
    "SEOEntry",
    "SEOPackage",
    "SiteArchitecture",
    "SiteBundle",
    "SpecCompilerInput",
    "StageRecord",
    "TransitionRecord",
    # serialization / identity helpers
    "artifact_sha256",
    "canonical_artifact_json",
    "canonical_json",
    "sha256_of_text",
    # enums
    "ArtifactKind",
    "ArtifactLifecycleState",
    "BuildState",
    "GateSeverity",
    "StageExecutionStatus",
    "StageOutcome",
    # errors
    "ArtifactIntegrityError",
    "ArtifactNotFoundError",
    "ArtifactValidationError",
    "IllegalTransitionError",
    "RepositoryCorruptionError",
    "SchemaRegistrationError",
    "SpecCompilationError",
    "UnsupportedSchemaVersionError",
    "WebsiteGenerationError",
    # registries
    "ENGINE_VERSIONS",
    "SCHEMA_VERSIONS",
    "registered_artifact_model",
    "registered_schema_versions",
]
