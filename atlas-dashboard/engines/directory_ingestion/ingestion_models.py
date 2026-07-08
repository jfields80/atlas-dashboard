"""
Atlas Directory Data Ingestion & Seeding Engine — Core Models
=============================================================

Frozen dataclasses shared by every ingestion module.

Architectural contract (Atlas v3):
    * Frozen dataclasses only — no mutation after construction.
    * TaggedValue honesty layer: every derived value carries provenance
      (VERIFIED / ESTIMATED / UNKNOWN).
    * All scoring deterministic and explainable via named constants.
    * No SQL, no Flask, no I/O in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# ---------------------------------------------------------------------------
# Engine identity (registered with the Engine Version Registry)
# ---------------------------------------------------------------------------

ENGINE_NAME = "directory_ingestion"
ENGINE_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Honesty layer
# ---------------------------------------------------------------------------

class Provenance(str, Enum):
    """Provenance tag for the TaggedValue honesty layer."""
    VERIFIED = "VERIFIED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TaggedValue:
    """A value that always carries its provenance."""
    value: Optional[str]
    provenance: Provenance = Provenance.UNKNOWN

    @staticmethod
    def unknown() -> "TaggedValue":
        return TaggedValue(value=None, provenance=Provenance.UNKNOWN)


# ---------------------------------------------------------------------------
# Blueprint contract (input from the completed Blueprint Engine)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CategoryNode:
    """One node of the Blueprint category hierarchy."""
    slug: str
    name: str
    parent_slug: Optional[str] = None
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocationNode:
    """One node of the Blueprint location hierarchy."""
    slug: str
    name: str
    level: str                      # "country" | "state" | "metro" | "city"
    parent_slug: Optional[str] = None
    state_code: Optional[str] = None


@dataclass(frozen=True)
class BlueprintInput:
    """
    The subset of Blueprint Engine output the ingestion engine consumes.

    An adapter in services/ maps the canonical Blueprint payload onto this
    contract when the Blueprint Engine lands in atlas-dashboard.
    """
    directory_slug: str
    directory_name: str
    category_hierarchy: tuple[CategoryNode, ...]
    location_hierarchy: tuple[LocationNode, ...]
    profile_schema_fields: tuple[str, ...]          # Business Profile Schema
    search_keywords: tuple[str, ...] = ()           # Search Blueprint
    monetization_fields: tuple[str, ...] = ()       # Monetization Plan hooks


# ---------------------------------------------------------------------------
# Raw + normalized listings
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    GOOGLE_PLACES = "google_places"
    PUBLIC_DIRECTORY = "public_directory"
    ASSOCIATION_WEBSITE = "association_website"
    GOVERNMENT_OPEN_DATA = "government_open_data"
    CSV_IMPORT = "csv_import"
    USER_SUBMITTED = "user_submitted"
    FUTURE_SCRAPER = "future_scraper"
    FUTURE_API = "future_api"


@dataclass(frozen=True)
class RawListing:
    """An un-normalized listing exactly as it arrived from a source."""
    raw_id: str
    source_type: SourceType
    source_name: str
    source_url: Optional[str]
    payload: tuple[tuple[str, str], ...]    # ordered (field, value) pairs

    def payload_dict(self) -> dict[str, str]:
        return dict(self.payload)


@dataclass(frozen=True)
class NormalizedListing:
    """A listing in canonical Atlas format. All optional fields honest-tagged."""
    listing_id: str
    raw_id: str
    business_name: str
    address: TaggedValue = field(default_factory=TaggedValue.unknown)
    city: TaggedValue = field(default_factory=TaggedValue.unknown)
    state: TaggedValue = field(default_factory=TaggedValue.unknown)
    zip_code: TaggedValue = field(default_factory=TaggedValue.unknown)
    country: TaggedValue = field(default_factory=TaggedValue.unknown)
    phone: TaggedValue = field(default_factory=TaggedValue.unknown)
    website: TaggedValue = field(default_factory=TaggedValue.unknown)
    email: TaggedValue = field(default_factory=TaggedValue.unknown)
    categories: tuple[str, ...] = ()
    subcategories: tuple[str, ...] = ()
    hours: TaggedValue = field(default_factory=TaggedValue.unknown)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amenities: tuple[str, ...] = ()
    services: tuple[str, ...] = ()
    pricing_notes: TaggedValue = field(default_factory=TaggedValue.unknown)
    description: TaggedValue = field(default_factory=TaggedValue.unknown)
    seo_summary: TaggedValue = field(default_factory=TaggedValue.unknown)
    source_type: SourceType = SourceType.CSV_IMPORT
    source_url: Optional[str] = None
    confidence: float = 0.0                 # 0.0 – 1.0
    verified: bool = False


# ---------------------------------------------------------------------------
# Source planning
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceRecommendation:
    source_type: SourceType
    quality_score: int          # 0–100
    coverage_score: int
    freshness_score: int
    difficulty_score: int       # higher = easier
    cost_score: int             # higher = cheaper
    reliability_score: int
    overall_score: int
    rank: int
    rationale: str
    implemented: bool           # False for future scrapers / APIs


@dataclass(frozen=True)
class SourcePlan:
    directory_slug: str
    recommendations: tuple[SourceRecommendation, ...]
    engine_version: str = ENGINE_VERSION


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

class MergeRecommendation(str, Enum):
    AUTO_MERGE = "AUTO_MERGE"
    REVIEW = "REVIEW"
    KEEP_SEPARATE = "KEEP_SEPARATE"


@dataclass(frozen=True)
class DuplicatePair:
    listing_id_a: str
    listing_id_b: str
    similarity: float           # 0.0 – 1.0
    matched_signals: tuple[str, ...]


@dataclass(frozen=True)
class DuplicateCluster:
    cluster_id: str
    listing_ids: tuple[str, ...]
    canonical_listing_id: str
    confidence: float
    merge_recommendation: MergeRecommendation
    pairs: tuple[DuplicatePair, ...]


@dataclass(frozen=True)
class DuplicateReport:
    clusters: tuple[DuplicateCluster, ...]
    total_listings: int
    duplicate_listings: int
    unique_listings: int


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QualityScore:
    listing_id: str
    completeness: int           # each 0–100
    contact_quality: int
    location_accuracy: int
    seo_readiness: int
    monetization_readiness: int
    verification_quality: int
    freshness: int
    overall: int
    explanations: tuple[str, ...]


@dataclass(frozen=True)
class QualityReport:
    scores: tuple[QualityScore, ...]
    average_overall: int
    listings_above_threshold: int
    threshold: int


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

class EnrichmentTaskType(str, Enum):
    FIND_WEBSITE = "find_website"
    FIND_PHONE = "find_phone"
    FIND_EMAIL = "find_email"
    WRITE_DESCRIPTION = "write_description"
    CATEGORIZE_BUSINESS = "categorize_business"
    VERIFY_ADDRESS = "verify_address"
    FIND_PHOTOS = "find_photos"
    FIND_OWNER = "find_owner"
    FIND_SOCIAL_MEDIA = "find_social_media"
    FIND_PREMIUM_CANDIDATE = "find_premium_candidate"


class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class EnrichmentTask:
    task_id: str
    listing_id: str
    task_type: EnrichmentTaskType
    priority: TaskPriority
    rationale: str
    status: str = "pending"     # future AI Employee job status


# ---------------------------------------------------------------------------
# Seed package
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SeedStatistics:
    total_raw: int
    total_normalized: int
    total_canonical: int
    duplicate_clusters: int
    enrichment_tasks: int
    average_quality: int
    verified_count: int


@dataclass(frozen=True)
class SeedPackage:
    package_id: str
    directory_slug: str
    businesses: tuple[NormalizedListing, ...]       # canonical, deduped
    categories: tuple[CategoryNode, ...]
    locations: tuple[LocationNode, ...]
    duplicate_report: DuplicateReport
    quality_report: QualityReport
    enrichment_queue: tuple[EnrichmentTask, ...]
    statistics: SeedStatistics
    engine_name: str = ENGINE_NAME
    engine_version: str = ENGINE_VERSION


# ---------------------------------------------------------------------------
# Import preparation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationIssue:
    listing_id: Optional[str]
    severity: str               # "error" | "warning"
    message: str


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    issues: tuple[ValidationIssue, ...]
    checked_records: int


@dataclass(frozen=True)
class ImportPackage:
    package_id: str
    format: str                 # "json" | "csv" | "sqlite_staging"
    artifact: str               # serialized payload (JSON text, CSV text, SQL)
    validation: ValidationReport
