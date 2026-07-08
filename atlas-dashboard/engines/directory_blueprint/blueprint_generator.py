"""Blueprint generator — the orchestrating engine for Phase 3.

Pure, deterministic function of a validated ``BlueprintRequest``:
    * No database access
    * No Flask
    * No I/O of any kind
    * Identical input -> byte-identical blueprint (verified by input hash)

The canonical API is the module-level function ``generate_blueprint``.
``BlueprintGenerator`` is a thin compatibility shim only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List

from engines.directory_blueprint.blueprint_models import (
    AIContentTask,
    AIContentTaskPlan,
    BlueprintRequest,
    BusinessProfileSchema,
    CommitteeRecommendation,
    CompetitionLevel,
    ContentItemPlan,
    ContentStrategy,
    DatabaseBlueprint,
    DataVerificationTag,
    DirectoryBlueprint,
    DirectoryType,
    EffortLevel,
    ExpansionClass,
    FieldSpec,
    GeographicScope,
    ProjectProfile,
    ProjectScorecard,
    RepositoryInterfaceSpec,
    SearchExperiencePlan,
    TableSpec,
)
from engines.directory_blueprint.category_planner import (
    infer_directory_type,
    plan_directory_architecture,
    slugify,
)
from engines.directory_blueprint.monetization_planner import plan_monetization
from engines.directory_blueprint.pydantic_compat import model_to_dict
from engines.directory_blueprint.risk_analyzer import analyze_risks
from engines.directory_blueprint.roadmap_planner import plan_roadmap
from engines.directory_blueprint.seo_planner import plan_seo

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

BLUEPRINT_ENGINE_NAME = "directory_blueprint"
BLUEPRINT_ENGINE_VERSION = "1.0.0"

ACTIONABLE_RECOMMENDATIONS = (
    CommitteeRecommendation.BUILD,
    CommitteeRecommendation.TEST,
)

DOMAIN_SUFFIX_TEMPLATES = (
    "{slug}.com",
    "{slug}directory.com",
    "{slug}finder.com",
    "best{slug}.com",
    "{slug}near.me",
)
MAX_SUGGESTED_DOMAINS = 5

COMPETITIVE_POSITION_BY_LEVEL = {
    CompetitionLevel.LOW: "First-mover in an underserved niche; win by coverage depth",
    CompetitionLevel.MEDIUM: "Challenger position; win by data quality and niche-specific filters",
    CompetitionLevel.HIGH: "Contested market; win on long-tail queries and verified data incumbents lack",
}

LAUNCH_COMPLEXITY_BY_SCOPE = {
    GeographicScope.NATIONAL: EffortLevel.HIGH,
    GeographicScope.REGIONAL: EffortLevel.MEDIUM,
    GeographicScope.STATE: EffortLevel.MEDIUM,
    GeographicScope.METRO: EffortLevel.LOW,
    GeographicScope.CITY: EffortLevel.LOW,
}

SCORE_MIN = 1
SCORE_MAX = 10

# Scorecard scoring constants
COMPLEXITY_BY_SCOPE = {
    GeographicScope.NATIONAL: 8,
    GeographicScope.REGIONAL: 6,
    GeographicScope.STATE: 5,
    GeographicScope.METRO: 4,
    GeographicScope.CITY: 3,
}
BUILD_TIME_WEEKS_PER_POINT = 3.0  # effort weeks per scorecard point
CLONE_COMPLEXITY_DISCOUNT = 2  # cloning a proven template reduces complexity/build time
OPERATIONAL_BURDEN_BASE = 4
CONTENT_BURDEN_BASE = 5
MAINTENANCE_BURDEN_BASE = 4
NATIONAL_BURDEN_SURCHARGE = 1
EXPANSION_POTENTIAL_BASE = {
    ExpansionClass.CLONE: 8,
    ExpansionClass.ADJACENT: 7,
    ExpansionClass.NEW_MARKET: 5,
}
SCALABILITY_BASE = 7
AUTOMATION_POTENTIAL_BASE = 8
AI_READINESS_BASE = 8
HIGH_LIQUIDITY_THRESHOLD = 60.0
READINESS_OPPORTUNITY_WEIGHT = 0.05  # opportunity score (0-100) -> 0-5 points
READINESS_BASE = 3
UNVERIFIED_READINESS_PENALTY = 2


def _clamp(value: int) -> int:
    return max(SCORE_MIN, min(SCORE_MAX, value))


def compute_input_hash(request: BlueprintRequest) -> str:
    """Stable SHA-256 over the canonical JSON form of the request.

    Local implementation to keep the subsystem independently runnable;
    can be swapped for ``core.input_hash`` at integration time.
    """
    payload = json.dumps(model_to_dict(request), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Section 1 — Project Profile
# ---------------------------------------------------------------------------


def build_project_profile(request: BlueprintRequest, directory_type: DirectoryType, primary_model) -> ProjectProfile:
    opportunity = request.opportunity
    slug = slugify(opportunity.name)
    compact = slug.replace("-", "")
    domains = [t.format(slug=compact) for t in DOMAIN_SUFFIX_TEMPLATES][:MAX_SUGGESTED_DOMAINS]
    return ProjectProfile(
        project_name=opportunity.name,
        project_slug=slug,
        suggested_domains=domains,
        business_type="Niche directory / lead generation",
        directory_type=directory_type,
        geographic_scope=opportunity.geographic_scope,
        primary_market=opportunity.primary_market,
        target_customer=opportunity.target_customer,
        primary_monetization_model=primary_model,
        competitive_position=COMPETITIVE_POSITION_BY_LEVEL[opportunity.competition_level],
        estimated_launch_complexity=LAUNCH_COMPLEXITY_BY_SCOPE[opportunity.geographic_scope],
    )


# ---------------------------------------------------------------------------
# Section 3 — Database Blueprint (specifications only; no SQL emitted here)
# ---------------------------------------------------------------------------


def _f(name: str, field_type: str, required: bool = False, indexed: bool = False, notes: str = "") -> FieldSpec:
    return FieldSpec(name=name, field_type=field_type, required=required, indexed=indexed, notes=notes)


def build_database_blueprint() -> DatabaseBlueprint:
    tables = [
        TableSpec(
            name="businesses",
            purpose="Core listing entity",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("name", "TEXT", True, True),
                _f("slug", "TEXT", True, True, "unique per city"),
                _f("description", "TEXT"),
                _f("phone", "TEXT"),
                _f("email", "TEXT"),
                _f("website", "TEXT"),
                _f("address", "TEXT"),
                _f("location_id", "INTEGER FK -> locations.id", True, True),
                _f("latitude", "REAL", indexed=True),
                _f("longitude", "REAL", indexed=True),
                _f("hours_json", "TEXT", notes="serialized weekly hours"),
                _f("verified_status", "TEXT", indexed=True, notes="VERIFIED/ESTIMATED/UNKNOWN"),
                _f("premium_status", "INTEGER", indexed=True),
                _f("claim_status", "TEXT", indexed=True),
                _f("created_at", "TEXT", True),
                _f("updated_at", "TEXT", True),
            ],
            relationships=["1:N reviews", "1:N images", "N:M categories", "N:1 locations"],
            indexes=["(location_id, verified_status)", "(latitude, longitude)"],
        ),
        TableSpec(
            name="categories",
            purpose="Category hierarchy (max depth 2)",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("name", "TEXT", True),
                _f("slug", "TEXT", True, True),
                _f("parent_id", "INTEGER FK -> categories.id", indexed=True),
            ],
            relationships=["self-referencing parent/child", "N:M businesses"],
        ),
        TableSpec(
            name="business_categories",
            purpose="Business <-> category join",
            fields=[
                _f("business_id", "INTEGER FK", True, True),
                _f("category_id", "INTEGER FK", True, True),
                _f("is_primary", "INTEGER", True),
            ],
            indexes=["UNIQUE(business_id, category_id)"],
        ),
        TableSpec(
            name="locations",
            purpose="Geographic hierarchy (state/county/city/neighborhood)",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("name", "TEXT", True),
                _f("slug", "TEXT", True, True),
                _f("level", "TEXT", True, True, "STATE/COUNTY/CITY/NEIGHBORHOOD"),
                _f("parent_id", "INTEGER FK -> locations.id", indexed=True),
            ],
            relationships=["self-referencing containment chain"],
        ),
        TableSpec(
            name="reviews",
            purpose="User reviews",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("business_id", "INTEGER FK", True, True),
                _f("rating", "INTEGER", True),
                _f("body", "TEXT"),
                _f("author_name", "TEXT"),
                _f("status", "TEXT", indexed=True, notes="PENDING/APPROVED/REJECTED"),
                _f("created_at", "TEXT", True),
            ],
        ),
        TableSpec(
            name="images",
            purpose="Listing media",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("business_id", "INTEGER FK", True, True),
                _f("url", "TEXT", True),
                _f("alt_text", "TEXT"),
                _f("sort_order", "INTEGER"),
            ],
        ),
        TableSpec(
            name="owners",
            purpose="Business-owner accounts",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("email", "TEXT", True, True),
                _f("name", "TEXT"),
                _f("created_at", "TEXT", True),
            ],
        ),
        TableSpec(
            name="claims",
            purpose="Ownership claims linking owners to businesses",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("business_id", "INTEGER FK", True, True),
                _f("owner_id", "INTEGER FK", True, True),
                _f("status", "TEXT", True, True, "PENDING/VERIFIED/REJECTED"),
                _f("created_at", "TEXT", True),
            ],
        ),
        TableSpec(
            name="subscriptions",
            purpose="Recurring revenue records",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("owner_id", "INTEGER FK", True, True),
                _f("business_id", "INTEGER FK", True, True),
                _f("plan", "TEXT", True),
                _f("status", "TEXT", True, True),
                _f("started_at", "TEXT", True),
                _f("ends_at", "TEXT"),
            ],
        ),
        TableSpec(
            name="premium_listings",
            purpose="Featured/premium placement records",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("business_id", "INTEGER FK", True, True),
                _f("placement", "TEXT", True, notes="HOME/CATEGORY/CITY"),
                _f("starts_at", "TEXT", True),
                _f("ends_at", "TEXT", True),
            ],
        ),
        TableSpec(
            name="events",
            purpose="Business or market events",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("business_id", "INTEGER FK", indexed=True),
                _f("title", "TEXT", True),
                _f("starts_at", "TEXT", True, True),
                _f("location_id", "INTEGER FK", indexed=True),
            ],
        ),
        TableSpec(
            name="coupons",
            purpose="Owner-published offers",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("business_id", "INTEGER FK", True, True),
                _f("title", "TEXT", True),
                _f("terms", "TEXT"),
                _f("expires_at", "TEXT", indexed=True),
            ],
        ),
        TableSpec(
            name="jobs",
            purpose="Job postings by listed businesses",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("business_id", "INTEGER FK", True, True),
                _f("title", "TEXT", True),
                _f("description", "TEXT"),
                _f("posted_at", "TEXT", True),
            ],
        ),
        TableSpec(
            name="articles",
            purpose="Guides, blog posts, cost pages",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("title", "TEXT", True),
                _f("slug", "TEXT", True, True),
                _f("body", "TEXT", True),
                _f("silo", "TEXT", indexed=True, notes="GUIDE/FAQ/COST/BLOG"),
                _f("published_at", "TEXT", indexed=True),
            ],
        ),
        TableSpec(
            name="faqs",
            purpose="FAQ entries, sitewide or per business",
            fields=[
                _f("id", "INTEGER PK", True),
                _f("business_id", "INTEGER FK", indexed=True, notes="NULL = sitewide"),
                _f("question", "TEXT", True),
                _f("answer", "TEXT", True),
            ],
        ),
    ]
    interfaces = [
        RepositoryInterfaceSpec(
            name="BusinessRepository",
            methods=[
                "get_by_id(business_id)",
                "get_by_slug(city_slug, business_slug)",
                "search(filters, sort, limit, offset)",
                "insert(record)",
                "update(business_id, changes)",
                "set_verification(business_id, status)",
            ],
        ),
        RepositoryInterfaceSpec(
            name="CategoryRepository",
            methods=["tree()", "get_by_slug(slug)", "insert(record)"],
        ),
        RepositoryInterfaceSpec(
            name="LocationRepository",
            methods=["children(parent_id)", "get_by_slug(slug, level)", "insert(record)"],
        ),
        RepositoryInterfaceSpec(
            name="ReviewRepository",
            methods=["for_business(business_id)", "insert(record)", "set_status(review_id, status)"],
        ),
        RepositoryInterfaceSpec(
            name="MonetizationRepository",
            methods=[
                "active_subscriptions(owner_id)",
                "active_premium_placements(placement)",
                "insert_subscription(record)",
                "insert_premium(record)",
            ],
        ),
    ]
    return DatabaseBlueprint(
        tables=tables,
        repository_interfaces=interfaces,
        notes=[
            "Specification only — SQL is implemented at build time, per subsystem",
            "All repositories are raw SQL, no ORM, per the Atlas architecture contract",
            "verified_status mirrors the TaggedValue honesty layer at the listing level",
        ],
    )


# ---------------------------------------------------------------------------
# Section 4 — Business Profile Schema
# ---------------------------------------------------------------------------

BUSINESS_PROFILE_FIELDS = (
    ("business_name", "string", True),
    ("address", "string", True),
    ("phone", "string", False),
    ("email", "string", False),
    ("website", "url", False),
    ("description", "text", False),
    ("hours", "weekly-hours object", False),
    ("latitude", "float", False),
    ("longitude", "float", False),
    ("social_media", "map[platform -> url]", False),
    ("amenities", "list[string]", False),
    ("pricing", "price-range enum", False),
    ("services", "list[string]", False),
    ("photos", "list[media]", False),
    ("videos", "list[media]", False),
    ("owner_notes", "text", False),
    ("verified_status", "enum VERIFIED/ESTIMATED/UNKNOWN", True),
    ("premium_status", "bool", True),
    ("claim_status", "enum UNCLAIMED/PENDING/CLAIMED", True),
    ("seo_title", "string", False),
    ("seo_meta_description", "string", False),
)


def build_business_profile_schema() -> BusinessProfileSchema:
    return BusinessProfileSchema(
        fields=[_f(name, ftype, required) for name, ftype, required in BUSINESS_PROFILE_FIELDS]
    )


# ---------------------------------------------------------------------------
# Section 5 — Search Experience
# ---------------------------------------------------------------------------


def build_search_experience() -> SearchExperiencePlan:
    return SearchExperiencePlan(
        filters=["category", "location", "distance", "rating", "amenities", "price-range"],
        sort_options=["relevance", "distance", "rating", "review-count", "recently-added"],
        facets=["categories", "cities", "amenities", "price", "rating-bands"],
        special_toggles=["open-now", "verified-only", "featured", "premium"],
        discovery_modules=["nearby", "recently-added", "popular-this-month", "editor-picks"],
    )


# ---------------------------------------------------------------------------
# Section 8 — Content Strategy
# ---------------------------------------------------------------------------

CONTENT_ITEM_TEMPLATES = (
    ("Category pages", "One per top-level category with intro copy and top listings", 10),
    ("Location pages", "State and city hubs with local stats and top categories", 9),
    ("Buying/choosing guides", "How-to-choose guides per major category", 8),
    ("Cost guides", "Aggregated pricing pages per category", 8),
    ("FAQ hub", "Sitewide and per-category FAQ pages", 7),
    ("Comparison pages", "Top-listing head-to-head comparisons", 6),
    ("Seasonal content", "Season-driven roundups tied to niche demand cycles", 5),
    ("Educational resources", "Evergreen explainers building topical authority", 5),
    ("Resource library", "Downloadables/checklists for email capture", 4),
)


def build_content_strategy() -> ContentStrategy:
    items = [
        ContentItemPlan(content_type=name, description=desc, priority=priority)
        for name, desc, priority in CONTENT_ITEM_TEMPLATES
    ]
    return ContentStrategy(
        items=items,
        publishing_priorities=[
            "1. Structural pages first (categories, locations) — they unlock indexing",
            "2. Guides and cost pages next — they earn links and long-tail traffic",
            "3. Comparison/seasonal content only after listing density supports it",
        ],
    )


# ---------------------------------------------------------------------------
# Section 9 — AI Content Tasks (definitions only, no implementation)
# ---------------------------------------------------------------------------

AI_TASK_TEMPLATES = (
    ("business_research", "Research and normalize raw listing data for a business", ("business name", "city"), ("normalized profile draft",), EffortLevel.MEDIUM),
    ("category_generation", "Propose category/subcategory refinements from listing corpus", ("listing corpus sample",), ("category tree diff",), EffortLevel.LOW),
    ("city_page_copy", "Draft city hub intro copy from local listing stats", ("city stats", "top listings"), ("city page draft",), EffortLevel.LOW),
    ("seo_article", "Draft guide/cost article per keyword cluster brief", ("keyword cluster", "outline"), ("article draft",), EffortLevel.MEDIUM),
    ("faq_generation", "Draft FAQ answers from category knowledge base", ("faq topic list",), ("faq drafts",), EffortLevel.LOW),
    ("business_summary", "Write neutral 2-3 sentence listing summaries", ("business profile",), ("summary text",), EffortLevel.LOW),
    ("metadata_generation", "Generate seo_title and meta descriptions per page", ("page content",), ("metadata pair",), EffortLevel.LOW),
    ("image_collection", "Locate candidate images and licensing status per listing", ("business profile",), ("image candidate list",), EffortLevel.HIGH),
    ("review_moderation", "Classify incoming reviews for policy violations", ("review text",), ("moderation label + reason",), EffortLevel.MEDIUM),
    ("listing_verification", "Cross-check listing facts against sources; assign honesty tag", ("business profile", "source snapshots"), ("VERIFIED/ESTIMATED/UNKNOWN tag + evidence",), EffortLevel.HIGH),
)


def build_ai_content_tasks() -> AIContentTaskPlan:
    tasks = [
        AIContentTask(
            task_id=task_id,
            task_type=task_id.upper(),
            description=description,
            inputs=list(inputs),
            outputs=list(outputs),
            automation_readiness=readiness,
        )
        for task_id, description, inputs, outputs, readiness in AI_TASK_TEMPLATES
    ]
    return AIContentTaskPlan(tasks=tasks)


# ---------------------------------------------------------------------------
# Section 12 — Project Scorecard
# ---------------------------------------------------------------------------


def build_scorecard(request: BlueprintRequest, total_effort_weeks: float) -> ProjectScorecard:
    opportunity = request.opportunity
    capacity = request.market_capacity
    expansion = request.expansion

    explanations: Dict[str, str] = {}

    complexity = COMPLEXITY_BY_SCOPE[opportunity.geographic_scope]
    if expansion.classification == ExpansionClass.CLONE:
        complexity -= CLONE_COMPLEXITY_DISCOUNT
        explanations["complexity"] = "Scope base %d minus clone discount %d" % (
            COMPLEXITY_BY_SCOPE[opportunity.geographic_scope],
            CLONE_COMPLEXITY_DISCOUNT,
        )
    else:
        explanations["complexity"] = "Scope base %d" % complexity
    complexity = _clamp(complexity)

    build_time = _clamp(int(round(total_effort_weeks / BUILD_TIME_WEEKS_PER_POINT)))
    explanations["build_time"] = "%.1f roadmap weeks / %.1f weeks-per-point" % (
        total_effort_weeks,
        BUILD_TIME_WEEKS_PER_POINT,
    )

    surcharge = (
        NATIONAL_BURDEN_SURCHARGE
        if opportunity.geographic_scope == GeographicScope.NATIONAL
        else 0
    )
    operational_burden = _clamp(OPERATIONAL_BURDEN_BASE + surcharge)
    content_burden = _clamp(CONTENT_BURDEN_BASE + surcharge)
    maintenance_burden = _clamp(MAINTENANCE_BURDEN_BASE + surcharge)
    explanations["burdens"] = "Bases %d/%d/%d %s" % (
        OPERATIONAL_BURDEN_BASE,
        CONTENT_BURDEN_BASE,
        MAINTENANCE_BURDEN_BASE,
        "+ national surcharge %d" % surcharge if surcharge else "(no scope surcharge)",
    )

    expansion_potential = _clamp(EXPANSION_POTENTIAL_BASE[expansion.classification])
    explanations["expansion_potential"] = "Base for %s classification" % expansion.classification.value

    scalability = SCALABILITY_BASE
    if capacity.liquidity_score >= HIGH_LIQUIDITY_THRESHOLD:
        scalability += 1
        explanations["scalability"] = "Base %d + 1 high-liquidity bonus" % SCALABILITY_BASE
    else:
        explanations["scalability"] = "Base %d" % SCALABILITY_BASE
    scalability = _clamp(scalability)

    readiness = READINESS_BASE + int(round(opportunity.score * READINESS_OPPORTUNITY_WEIGHT))
    readiness_note = "Base %d + opportunity %.0f x %.2f" % (
        READINESS_BASE,
        opportunity.score,
        READINESS_OPPORTUNITY_WEIGHT,
    )
    if capacity.data_tag != DataVerificationTag.VERIFIED:
        readiness -= UNVERIFIED_READINESS_PENALTY
        readiness_note += " - %d unverified-data penalty (%s)" % (
            UNVERIFIED_READINESS_PENALTY,
            capacity.data_tag.value,
        )
    explanations["overall_build_readiness"] = readiness_note

    return ProjectScorecard(
        complexity=complexity,
        build_time=build_time,
        operational_burden=operational_burden,
        content_burden=content_burden,
        maintenance_burden=maintenance_burden,
        expansion_potential=expansion_potential,
        scalability=scalability,
        automation_potential=_clamp(AUTOMATION_POTENTIAL_BASE),
        ai_readiness=_clamp(AI_READINESS_BASE),
        overall_build_readiness=_clamp(readiness),
        explanations=explanations,
    )


# ---------------------------------------------------------------------------
# Canonical API
# ---------------------------------------------------------------------------


def is_blueprint_eligible(request: BlueprintRequest) -> bool:
    """Blueprints are generated only for BUILD or TEST recommendations."""
    return request.committee.recommendation in ACTIONABLE_RECOMMENDATIONS


def generate_blueprint(request: BlueprintRequest) -> DirectoryBlueprint:
    """Generate a complete directory blueprint.

    Raises ``ValueError`` if the committee recommendation is not BUILD/TEST —
    the eligibility gate is enforced at the engine boundary as well as in the
    service layer, mirroring the Atlas honest-wall philosophy.
    """
    if not is_blueprint_eligible(request):
        raise ValueError(
            "Blueprint generation requires a BUILD or TEST recommendation; got %s"
            % request.committee.recommendation.value
        )

    directory_type = infer_directory_type(request.opportunity)
    architecture = plan_directory_architecture(request.opportunity)
    monetization = plan_monetization(request.opportunity, request.market_capacity, directory_type)
    seo = plan_seo(request.opportunity, architecture)
    roadmap = plan_roadmap(request.opportunity, request.market_capacity)
    risks = analyze_risks(request.opportunity, request.market_capacity)
    scorecard = build_scorecard(request, roadmap.total_estimated_effort_weeks)

    notes: List[str] = []
    if request.market_capacity.data_tag != DataVerificationTag.VERIFIED:
        notes.append(
            "Market capacity inputs are %s — treat monetization values and readiness as estimates"
            % request.market_capacity.data_tag.value
        )
    if request.expansion.classification == ExpansionClass.CLONE and request.expansion.template_asset:
        notes.append("Clone of template asset: %s" % request.expansion.template_asset)
    if request.committee.recommendation == CommitteeRecommendation.TEST:
        notes.append("TEST recommendation: scope Phase 1-3 as a minimum-viable validation build")

    return DirectoryBlueprint(
        engine_version=BLUEPRINT_ENGINE_VERSION,
        input_hash=compute_input_hash(request),
        project_profile=build_project_profile(request, directory_type, monetization.primary_model),
        directory_architecture=architecture,
        database_blueprint=build_database_blueprint(),
        business_profile_schema=build_business_profile_schema(),
        search_experience=build_search_experience(),
        monetization_plan=monetization,
        seo_blueprint=seo,
        content_strategy=build_content_strategy(),
        ai_content_tasks=build_ai_content_tasks(),
        implementation_roadmap=roadmap,
        risk_analysis=risks,
        project_scorecard=scorecard,
        data_confidence_tag=request.market_capacity.data_tag,
        generation_notes=notes,
    )


class BlueprintGenerator:
    """Compatibility shim. The functional API above is canonical."""

    engine_name = BLUEPRINT_ENGINE_NAME
    engine_version = BLUEPRINT_ENGINE_VERSION

    def is_eligible(self, request: BlueprintRequest) -> bool:
        return is_blueprint_eligible(request)

    def generate(self, request: BlueprintRequest) -> DirectoryBlueprint:
        return generate_blueprint(request)
