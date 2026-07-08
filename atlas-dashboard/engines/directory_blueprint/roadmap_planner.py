"""Implementation roadmap planner.

Deterministic engine producing Section 10. The eight canonical phases are
fixed by the Phase 3 spec; per-phase effort scales by named multipliers
derived from geographic scope and market size.
"""

from __future__ import annotations

from typing import List, Tuple

from engines.directory_blueprint.blueprint_models import (
    EffortLevel,
    GeographicScope,
    ImplementationRoadmap,
    MarketCapacityInput,
    OpportunityInput,
    RoadmapPhase,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

# (phase name, base effort weeks, complexity, objectives, risks)
PHASE_TEMPLATES: Tuple[Tuple[str, float, EffortLevel, Tuple[str, ...], Tuple[str, ...]], ...] = (
    (
        "Foundation",
        2.0,
        EffortLevel.MEDIUM,
        (
            "Domain, hosting, and analytics provisioned",
            "Core schema deployed (businesses, categories, locations)",
            "Repository + service skeleton in place",
        ),
        ("Over-engineering before data validates the market",),
    ),
    (
        "Data",
        3.0,
        EffortLevel.HIGH,
        (
            "Seed listing dataset acquired and normalized",
            "Category and location hierarchies populated",
            "Verification pipeline tagging VERIFIED/ESTIMATED/UNKNOWN",
        ),
        ("Source data quality below threshold", "Licensing/scraping constraints"),
    ),
    (
        "Search",
        2.0,
        EffortLevel.MEDIUM,
        (
            "Faceted search with category, location, and rating filters",
            "Distance sort and geo queries",
            "Zero-result handling and suggestions",
        ),
        ("Poor relevance on thin data",),
    ),
    (
        "Content",
        2.5,
        EffortLevel.MEDIUM,
        (
            "Guides, FAQ hub, and cost pages published",
            "AI content task pipeline producing drafts for human review",
        ),
        ("Thin/duplicative AI content", "Review bottleneck"),
    ),
    (
        "SEO",
        2.0,
        EffortLevel.MEDIUM,
        (
            "Schema markup live on all page types",
            "Internal linking rules enforced in templates",
            "Sitemaps and canonical policy verified in Search Console",
        ),
        ("Index bloat from facet pages", "Slow crawl on new domain"),
    ),
    (
        "Monetization",
        1.5,
        EffortLevel.MEDIUM,
        (
            "Primary monetization model live (per Monetization Plan rank 1)",
            "Claim flow and payment processing tested end to end",
        ),
        ("Premature paywalls suppressing listing growth",),
    ),
    (
        "Launch",
        1.0,
        EffortLevel.LOW,
        (
            "Public launch checklist complete",
            "Uptime, error, and conversion monitoring active",
        ),
        ("Launching before minimum viable listing density",),
    ),
    (
        "Growth",
        4.0,
        EffortLevel.HIGH,
        (
            "Programmatic SEO expansion per keyword clusters",
            "Owner outreach loop for claims and upgrades",
            "Expansion candidates fed back into Atlas pipeline",
        ),
        ("Scaling content faster than quality controls", "Algorithm updates"),
    ),
)

# Dependencies expressed as phase-name references (empty = none)
PHASE_DEPENDENCIES: Tuple[Tuple[str, ...], ...] = (
    (),
    ("Foundation",),
    ("Data",),
    ("Data",),
    ("Content", "Search"),
    ("Search", "Data"),
    ("SEO", "Monetization"),
    ("Launch",),
)

# Effort multipliers by geographic scope
SCOPE_EFFORT_MULTIPLIER = {
    GeographicScope.NATIONAL: 1.5,
    GeographicScope.REGIONAL: 1.25,
    GeographicScope.STATE: 1.0,
    GeographicScope.METRO: 0.75,
    GeographicScope.CITY: 0.6,
}

# Market-size effort multiplier thresholds (total addressable listings)
LARGE_MARKET_LISTING_THRESHOLD = 5000
LARGE_MARKET_MULTIPLIER = 1.2
SMALL_MARKET_LISTING_THRESHOLD = 500
SMALL_MARKET_MULTIPLIER = 0.9
DEFAULT_MARKET_MULTIPLIER = 1.0

EFFORT_ROUNDING_DIGITS = 1


def _market_multiplier(capacity: MarketCapacityInput) -> float:
    if capacity.total_addressable_listings >= LARGE_MARKET_LISTING_THRESHOLD:
        return LARGE_MARKET_MULTIPLIER
    if capacity.total_addressable_listings <= SMALL_MARKET_LISTING_THRESHOLD:
        return SMALL_MARKET_MULTIPLIER
    return DEFAULT_MARKET_MULTIPLIER


def plan_roadmap(
    opportunity: OpportunityInput, capacity: MarketCapacityInput
) -> ImplementationRoadmap:
    scope_multiplier = SCOPE_EFFORT_MULTIPLIER[opportunity.geographic_scope]
    market_multiplier = _market_multiplier(capacity)

    phases: List[RoadmapPhase] = []
    total = 0.0
    for index, (name, base_weeks, complexity, objectives, risks) in enumerate(PHASE_TEMPLATES):
        weeks = round(base_weeks * scope_multiplier * market_multiplier, EFFORT_ROUNDING_DIGITS)
        total += weeks
        phases.append(
            RoadmapPhase(
                phase_number=index + 1,
                name=name,
                objectives=list(objectives),
                dependencies=list(PHASE_DEPENDENCIES[index]),
                complexity=complexity,
                estimated_effort_weeks=weeks,
                risks=list(risks),
            )
        )

    return ImplementationRoadmap(
        phases=phases,
        total_estimated_effort_weeks=round(total, EFFORT_ROUNDING_DIGITS),
    )
