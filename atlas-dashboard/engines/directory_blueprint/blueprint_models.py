"""Data contracts for the Directory Blueprint Engine.

Every input the engine consumes and every artifact it emits is defined here.
Models are Pydantic (v1/v2 compatible via ``pydantic_compat``) so blueprints
are validated, serializable, and safe to persist through the repository layer.

Input models are deliberately self-contained: they do NOT import from
``services.v2_types`` or any other Atlas subsystem. Upstream callers (or a
thin adapter) map committee / capacity / classification outputs onto these
contracts. This keeps the subsystem independently runnable, per the Phase 3
success criteria.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from engines.directory_blueprint.pydantic_compat import BaseModel, Field

# ---------------------------------------------------------------------------
# Enumerations (string enums serialize identically under Pydantic v1 and v2)
# ---------------------------------------------------------------------------


class CommitteeRecommendation(str, Enum):
    BUILD = "BUILD"
    TEST = "TEST"
    WATCH = "WATCH"
    PASS = "PASS"


class GeographicScope(str, Enum):
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"
    STATE = "STATE"
    METRO = "METRO"
    CITY = "CITY"


class CompetitionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DataVerificationTag(str, Enum):
    """Mirrors the Atlas TaggedValue honesty layer."""

    VERIFIED = "VERIFIED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class ExpansionClass(str, Enum):
    NEW_MARKET = "NEW_MARKET"
    ADJACENT = "ADJACENT"
    CLONE = "CLONE"


class DirectoryType(str, Enum):
    LOCAL_SERVICES = "LOCAL_SERVICES"
    TRAVEL = "TRAVEL"
    B2B = "B2B"
    EDUCATION = "EDUCATION"
    MARKETPLACE = "MARKETPLACE"
    NICHE_INTEREST = "NICHE_INTEREST"


class MonetizationModel(str, Enum):
    FEATURED_LISTINGS = "FEATURED_LISTINGS"
    SPONSORED_RESULTS = "SPONSORED_RESULTS"
    LEAD_GENERATION = "LEAD_GENERATION"
    ADVERTISING = "ADVERTISING"
    MEMBERSHIP = "MEMBERSHIP"
    AFFILIATE = "AFFILIATE"
    COUPONS = "COUPONS"
    PREMIUM_PROFILES = "PREMIUM_PROFILES"
    EMAIL_SPONSORSHIPS = "EMAIL_SPONSORSHIPS"
    EVENTS = "EVENTS"
    MARKETPLACE = "MARKETPLACE"
    BOOKING = "BOOKING"
    DONATIONS = "DONATIONS"


class EffortLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"


# ---------------------------------------------------------------------------
# Input contracts
# ---------------------------------------------------------------------------


class OpportunityInput(BaseModel):
    """Distilled Opportunity Intelligence Engine v2 evaluation."""

    name: str
    niche: str
    description: str = ""
    score: float = Field(0.0, ge=0.0, le=100.0)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    geographic_scope: GeographicScope = GeographicScope.NATIONAL
    primary_market: str = "United States"
    target_customer: str = "Consumers searching for local providers"
    competition_level: CompetitionLevel = CompetitionLevel.MEDIUM
    monetization_signals: List[str] = Field(default_factory=list)


class MarketCapacityInput(BaseModel):
    """Distilled Market Capacity / Market Liquidity Engine output."""

    total_addressable_listings: int = Field(0, ge=0)
    liquidity_score: float = Field(0.0, ge=0.0, le=100.0)
    saturation_level: CompetitionLevel = CompetitionLevel.MEDIUM
    data_tag: DataVerificationTag = DataVerificationTag.ESTIMATED


class PortfolioAssetRef(BaseModel):
    name: str
    niche: str
    status: str = "LIVE"


class PortfolioContextInput(BaseModel):
    """Distilled Portfolio State Service / Synergy Engine output."""

    existing_assets: List[PortfolioAssetRef] = Field(default_factory=list)
    synergy_score: float = Field(0.0, ge=0.0, le=100.0)


class ExpansionClassificationInput(BaseModel):
    """Distilled Expansion Classifier output."""

    classification: ExpansionClass = ExpansionClass.NEW_MARKET
    template_asset: Optional[str] = None


class CommitteeInput(BaseModel):
    """Distilled Investment Committee recommendation."""

    recommendation: CommitteeRecommendation
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    rationale: str = ""


class BlueprintRequest(BaseModel):
    """The complete, validated input bundle for blueprint generation."""

    opportunity: OpportunityInput
    market_capacity: MarketCapacityInput = Field(default_factory=MarketCapacityInput)
    portfolio_context: PortfolioContextInput = Field(default_factory=PortfolioContextInput)
    expansion: ExpansionClassificationInput = Field(
        default_factory=ExpansionClassificationInput
    )
    committee: CommitteeInput


# ---------------------------------------------------------------------------
# Section 1 — Project Profile
# ---------------------------------------------------------------------------


class ProjectProfile(BaseModel):
    project_name: str
    project_slug: str
    suggested_domains: List[str]
    business_type: str
    directory_type: DirectoryType
    geographic_scope: GeographicScope
    primary_market: str
    target_customer: str
    primary_monetization_model: MonetizationModel
    competitive_position: str
    estimated_launch_complexity: EffortLevel


# ---------------------------------------------------------------------------
# Section 2 — Directory Architecture
# ---------------------------------------------------------------------------


class CategoryNode(BaseModel):
    name: str
    slug: str
    subcategories: List["CategoryNode"] = Field(default_factory=list)


class LocationHierarchy(BaseModel):
    levels: List[str]
    example_paths: List[str]


class NavigationNode(BaseModel):
    label: str
    url_pattern: str
    children: List["NavigationNode"] = Field(default_factory=list)


class DirectoryArchitecture(BaseModel):
    category_tree: List[CategoryNode]
    location_hierarchy: LocationHierarchy
    tags: List[str]
    amenities: List[str]
    attributes: List[str]
    relationship_diagram: str
    parent_child_rules: List[str]
    navigation_tree: List[NavigationNode]
    url_hierarchy: List[str]
    canonical_strategy: List[str]


# ---------------------------------------------------------------------------
# Section 3 — Database Blueprint
# ---------------------------------------------------------------------------


class FieldSpec(BaseModel):
    name: str
    field_type: str
    required: bool = False
    indexed: bool = False
    notes: str = ""


class TableSpec(BaseModel):
    name: str
    purpose: str
    fields: List[FieldSpec]
    relationships: List[str] = Field(default_factory=list)
    indexes: List[str] = Field(default_factory=list)


class RepositoryInterfaceSpec(BaseModel):
    name: str
    methods: List[str]


class DatabaseBlueprint(BaseModel):
    tables: List[TableSpec]
    repository_interfaces: List[RepositoryInterfaceSpec]
    notes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Section 4 — Business Profile Schema
# ---------------------------------------------------------------------------


class BusinessProfileSchema(BaseModel):
    fields: List[FieldSpec]


# ---------------------------------------------------------------------------
# Section 5 — Search Experience
# ---------------------------------------------------------------------------


class SearchExperiencePlan(BaseModel):
    filters: List[str]
    sort_options: List[str]
    facets: List[str]
    special_toggles: List[str]
    discovery_modules: List[str]


# ---------------------------------------------------------------------------
# Section 6 — Monetization Plan
# ---------------------------------------------------------------------------


class MonetizationOption(BaseModel):
    model: MonetizationModel
    rank: int
    estimated_value_score: int = Field(..., ge=1, le=10)
    implementation_complexity: EffortLevel
    operational_burden: EffortLevel
    risk: RiskLevel
    rationale: str


class MonetizationPlan(BaseModel):
    primary_model: MonetizationModel
    ranked_options: List[MonetizationOption]


# ---------------------------------------------------------------------------
# Section 7 — SEO Blueprint
# ---------------------------------------------------------------------------


class KeywordCluster(BaseModel):
    theme: str
    example_keywords: List[str]
    target_page_type: str


class SEOBlueprint(BaseModel):
    url_structure: List[str]
    content_silos: List[str]
    landing_pages: List[str]
    category_pages: List[str]
    location_pages: List[str]
    faq_topics: List[str]
    blog_opportunities: List[str]
    schema_markup: List[str]
    internal_linking_strategy: List[str]
    keyword_clusters: List[KeywordCluster]
    programmatic_seo_opportunities: List[str]


# ---------------------------------------------------------------------------
# Section 8 — Content Strategy
# ---------------------------------------------------------------------------


class ContentItemPlan(BaseModel):
    content_type: str
    description: str
    priority: int = Field(..., ge=1, le=10)


class ContentStrategy(BaseModel):
    items: List[ContentItemPlan]
    publishing_priorities: List[str]


# ---------------------------------------------------------------------------
# Section 9 — AI Content Tasks
# ---------------------------------------------------------------------------


class AIContentTask(BaseModel):
    task_id: str
    task_type: str
    description: str
    inputs: List[str]
    outputs: List[str]
    automation_readiness: EffortLevel


class AIContentTaskPlan(BaseModel):
    tasks: List[AIContentTask]


# ---------------------------------------------------------------------------
# Section 10 — Implementation Roadmap
# ---------------------------------------------------------------------------


class RoadmapPhase(BaseModel):
    phase_number: int
    name: str
    objectives: List[str]
    dependencies: List[str]
    complexity: EffortLevel
    estimated_effort_weeks: float
    risks: List[str]


class ImplementationRoadmap(BaseModel):
    phases: List[RoadmapPhase]
    total_estimated_effort_weeks: float


# ---------------------------------------------------------------------------
# Section 11 — Risk Analysis
# ---------------------------------------------------------------------------


class RiskAssessment(BaseModel):
    category: str
    level: RiskLevel
    score: int = Field(..., ge=1, le=10)
    drivers: List[str]
    mitigations: List[str]


class RiskAnalysis(BaseModel):
    assessments: List[RiskAssessment]
    overall_risk_level: RiskLevel
    overall_risk_score: int = Field(..., ge=1, le=10)


# ---------------------------------------------------------------------------
# Section 12 — Project Scorecard
# ---------------------------------------------------------------------------


class ProjectScorecard(BaseModel):
    complexity: int = Field(..., ge=1, le=10)
    build_time: int = Field(..., ge=1, le=10)
    operational_burden: int = Field(..., ge=1, le=10)
    content_burden: int = Field(..., ge=1, le=10)
    maintenance_burden: int = Field(..., ge=1, le=10)
    expansion_potential: int = Field(..., ge=1, le=10)
    scalability: int = Field(..., ge=1, le=10)
    automation_potential: int = Field(..., ge=1, le=10)
    ai_readiness: int = Field(..., ge=1, le=10)
    overall_build_readiness: int = Field(..., ge=1, le=10)
    explanations: Dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level blueprint
# ---------------------------------------------------------------------------


class DirectoryBlueprint(BaseModel):
    engine_version: str
    input_hash: str
    project_profile: ProjectProfile
    directory_architecture: DirectoryArchitecture
    database_blueprint: DatabaseBlueprint
    business_profile_schema: BusinessProfileSchema
    search_experience: SearchExperiencePlan
    monetization_plan: MonetizationPlan
    seo_blueprint: SEOBlueprint
    content_strategy: ContentStrategy
    ai_content_tasks: AIContentTaskPlan
    implementation_roadmap: ImplementationRoadmap
    risk_analysis: RiskAnalysis
    project_scorecard: ProjectScorecard
    data_confidence_tag: DataVerificationTag
    generation_notes: List[str] = Field(default_factory=list)


# Forward-reference resolution (works on both Pydantic majors).
try:  # Pydantic v2
    CategoryNode.model_rebuild()
    NavigationNode.model_rebuild()
except AttributeError:  # Pydantic v1
    CategoryNode.update_forward_refs()
    NavigationNode.update_forward_refs()
