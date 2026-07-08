"""
Atlas Directory Data Ingestion & Seeding Engine (Phase 3B).

Public API surface. Downstream code should import from this package rather
than from individual modules.
"""

from engines.directory_ingestion.ingestion_models import (
    ENGINE_NAME,
    ENGINE_VERSION,
    BlueprintInput,
    CategoryNode,
    DuplicateCluster,
    DuplicateReport,
    EnrichmentTask,
    EnrichmentTaskType,
    ImportPackage,
    LocationNode,
    MergeRecommendation,
    NormalizedListing,
    Provenance,
    QualityReport,
    QualityScore,
    RawListing,
    SeedPackage,
    SeedStatistics,
    SourcePlan,
    SourceRecommendation,
    SourceType,
    TaggedValue,
    TaskPriority,
    ValidationIssue,
    ValidationReport,
)
from engines.directory_ingestion.source_planner import SourcePlanner
from engines.directory_ingestion.listing_normalizer import (
    DEFAULT_MAPPING_PROFILE,
    FieldMapping,
    ListingNormalizer,
)
from engines.directory_ingestion.duplicate_detector import (
    AUTO_MERGE_THRESHOLD,
    DUPLICATE_THRESHOLD,
    DuplicateDetector,
)
from engines.directory_ingestion.quality_engine import QUALITY_THRESHOLD, QualityEngine
from engines.directory_ingestion.enrichment_generator import EnrichmentTaskGenerator
from engines.directory_ingestion.seed_package_builder import SeedPackageBuilder
from engines.directory_ingestion.import_preparer import ImportPreparer

__all__ = [
    "ENGINE_NAME",
    "ENGINE_VERSION",
    "BlueprintInput",
    "CategoryNode",
    "LocationNode",
    "RawListing",
    "NormalizedListing",
    "TaggedValue",
    "Provenance",
    "SourceType",
    "SourcePlan",
    "SourceRecommendation",
    "SourcePlanner",
    "FieldMapping",
    "DEFAULT_MAPPING_PROFILE",
    "ListingNormalizer",
    "DuplicateDetector",
    "DuplicateCluster",
    "DuplicateReport",
    "MergeRecommendation",
    "DUPLICATE_THRESHOLD",
    "AUTO_MERGE_THRESHOLD",
    "QualityEngine",
    "QualityScore",
    "QualityReport",
    "QUALITY_THRESHOLD",
    "EnrichmentTaskGenerator",
    "EnrichmentTask",
    "EnrichmentTaskType",
    "TaskPriority",
    "SeedPackageBuilder",
    "SeedPackage",
    "SeedStatistics",
    "ImportPreparer",
    "ImportPackage",
    "ValidationReport",
    "ValidationIssue",
]
