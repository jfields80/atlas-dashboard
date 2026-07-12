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
    ContrastEvidence,
    GateResult,
    InternalLinkIntent,
    LaunchCertificateBody,
    LayoutPlan,
    LayoutRegion,
    PageComponents,
    PageHierarchyEntry,
    PageLayout,
    PagePlan,
    QualityReport,
    RenderedPage,
    RenderedPageSet,
    SEOEntry,
    SEOPackage,
    SelectionCandidate,
    SelectionScoreComponent,
    SelectionTrace,
    SiteArchitecture,
    SiteBundle,
    SlotSelectionTrace,
    SpecCompilerInput,
    StageRecord,
    TransitionRecord,
    artifact_sha256,
    canonical_artifact_json,
    canonical_json,
    sha256_of_text,
)
from engines.website_generation.contracts.components import (
    AccessibilityContract,
    AnalyticsContract,
    ComponentDefinition,
    ConversionContract,
    DeprecationInfo,
    DirectoryContract,
    MonetizationContract,
    PropSpec,
    RenderingContract,
    ResponsiveContract,
    SEOContract,
    SlotSpec,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    ArtifactKind,
    ArtifactLifecycleState,
    AssetRole,
    BuildState,
    CommercialPurpose,
    ComponentFamily,
    ConversionGoal,
    GateSeverity,
    LifecycleStatus,
    ListingKind,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
    StageExecutionStatus,
    StageOutcome,
)
from engines.website_generation.contracts.errors import (
    ArchitecturePlanningError,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactValidationError,
    ComponentNotFoundError,
    ComponentSystemError,
    ConflictingComponentError,
    ContentValidationError,
    DuplicateComponentError,
    IllegalTransitionError,
    InvalidCompatibilityDeclarationError,
    InvalidComponentDefinitionError,
    RepositoryCorruptionError,
    SchemaRegistrationError,
    SpecCompilationError,
    UnsupportedComponentVersionError,
    UnsupportedSchemaVersionError,
    WebsiteGenerationError,
)
from engines.website_generation.contracts.interfaces import (
    ComponentRegistryView,
)
from engines.website_generation.contracts.versions import (
    COMPONENT_CONTRACT_SCHEMA_VERSION,
    COMPONENT_SYSTEM_VERSIONS,
    ENGINE_VERSIONS,
    REGISTRY_FINGERPRINT_VERSION,
    REGISTRY_VERSION,
    SCHEMA_VERSIONS,
    registered_artifact_model,
    registered_schema_versions,
)
from engines.website_generation.components import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    RegistryInventoryEntry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)
from engines.website_generation.brand import BrandEngine
from engines.website_generation.ia import InformationArchitectureEngine
from engines.website_generation.content import ContentEngine
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
    # Brand Engine (AES-WEB-001 §5.2 / Part 2 / Part 13 Phase 2;
    # AES-WEB-002J.2). Not wired into pipeline execution.
    "BrandEngine",
    # Information Architecture Engine (AES-WEB-001 §5.3 / Part 2 / Part 13
    # Phase 2; AES-WEB-002J.3). Not wired into pipeline execution.
    "InformationArchitectureEngine",
    # Content Engine (AES-WEB-001 §5.4 / Part 2; AES-WEB-002J.4). Not wired
    # into pipeline execution.
    "ContentEngine",
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
    "ContrastEvidence",
    "GateResult",
    "InternalLinkIntent",
    "LaunchCertificateBody",
    "LayoutPlan",
    "LayoutRegion",
    "PageComponents",
    "PageHierarchyEntry",
    "PageLayout",
    "PagePlan",
    "QualityReport",
    "RenderedPage",
    "RenderedPageSet",
    "SEOEntry",
    "SEOPackage",
    "SelectionCandidate",
    "SelectionScoreComponent",
    "SelectionTrace",
    "SiteArchitecture",
    "SiteBundle",
    "SlotSelectionTrace",
    "SpecCompilerInput",
    "StageRecord",
    "TransitionRecord",
    # component contracts (AES-WEB-002A)
    "AccessibilityContract",
    "AnalyticsContract",
    "ComponentDefinition",
    "ConversionContract",
    "DeprecationInfo",
    "DirectoryContract",
    "MonetizationContract",
    "PropSpec",
    "RenderingContract",
    "ResponsiveContract",
    "SEOContract",
    "SlotSpec",
    "VariantSpec",
    # component registry (AES-WEB-002A)
    "ComponentRegistry",
    "ComponentRegistryView",
    "RegistryInventoryEntry",
    "REGISTERED_COMPONENTS",
    "build_default_registry",
    "definition_fingerprint",
    "validate_definition",
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
    # component enums (AES-WEB-002A)
    "AssetRole",
    "CommercialPurpose",
    "ComponentFamily",
    "ConversionGoal",
    "LifecycleStatus",
    "ListingKind",
    "PageRole",
    "PropType",
    "RegionKind",
    "SemanticElement",
    "SlotCardinality",
    # errors
    "ArchitecturePlanningError",
    "ArtifactIntegrityError",
    "ArtifactNotFoundError",
    "ArtifactValidationError",
    "ContentValidationError",
    "IllegalTransitionError",
    "RepositoryCorruptionError",
    "SchemaRegistrationError",
    "SpecCompilationError",
    "UnsupportedSchemaVersionError",
    "WebsiteGenerationError",
    # component errors (AES-WEB-002A)
    "ComponentNotFoundError",
    "ComponentSystemError",
    "ConflictingComponentError",
    "DuplicateComponentError",
    "InvalidCompatibilityDeclarationError",
    "InvalidComponentDefinitionError",
    "UnsupportedComponentVersionError",
    # registries
    "ENGINE_VERSIONS",
    "SCHEMA_VERSIONS",
    "registered_artifact_model",
    "registered_schema_versions",
    # component-system versions (AES-WEB-002A)
    "COMPONENT_CONTRACT_SCHEMA_VERSION",
    "COMPONENT_SYSTEM_VERSIONS",
    "REGISTRY_FINGERPRINT_VERSION",
    "REGISTRY_VERSION",
]
