"""Risk analyzer.

Deterministic engine producing Section 11. Seven risk categories are scored
1-10 (10 = worst) from named base scores plus explainable adjustments tied to
competition, market liquidity, data verification status, and scope.
"""

from __future__ import annotations

from typing import List, Tuple

from engines.directory_blueprint.blueprint_models import (
    CompetitionLevel,
    DataVerificationTag,
    GeographicScope,
    MarketCapacityInput,
    OpportunityInput,
    RiskAnalysis,
    RiskAssessment,
    RiskLevel,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

RISK_SCORE_MIN = 1
RISK_SCORE_MAX = 10

# (category, base score, drivers, mitigations)
RISK_TEMPLATES: Tuple[Tuple[str, int, Tuple[str, ...], Tuple[str, ...]], ...] = (
    (
        "SEO risk",
        5,
        ("New domain with zero authority", "Directory SERPs dominated by aggregators"),
        ("Programmatic pages gated on listing density", "Unique data per page (hours, pricing, reviews)"),
    ),
    (
        "Competition risk",
        4,
        ("Incumbent horizontal directories (Yelp/Google) capture head terms",),
        ("Own the long tail with niche-specific attributes incumbents lack",),
    ),
    (
        "Operational risk",
        3,
        ("Solo-operator bandwidth across a multi-asset portfolio",),
        ("Automation-first pipeline; weekly not daily maintenance cadence",),
    ),
    (
        "Data acquisition risk",
        5,
        ("Seed data licensing, freshness, and coverage gaps",),
        ("Multiple provider sources; TaggedValue honesty layer downgrades stale data",),
    ),
    (
        "Monetization risk",
        5,
        ("Revenue unverified until owners actually pay",),
        ("Launch with lowest-friction model first; treat projections as ESTIMATED",),
    ),
    (
        "Scaling risk",
        4,
        ("Template debt if first build hard-codes niche assumptions",),
        ("Blueprint-driven build keeps structure declarative and cloneable",),
    ),
    (
        "AI content risk",
        5,
        ("Thin or duplicative generated pages risk quality filters",),
        ("Human review gate; publish only pages backed by structured listing data",),
    ),
)

HIGH_COMPETITION_ADJUSTMENT = 2
LOW_COMPETITION_ADJUSTMENT = -1
COMPETITION_AFFECTED = ("SEO risk", "Competition risk")

LOW_LIQUIDITY_THRESHOLD = 30.0
LOW_LIQUIDITY_ADJUSTMENT = 2
LIQUIDITY_AFFECTED = ("Monetization risk", "Data acquisition risk")

UNVERIFIED_DATA_ADJUSTMENT = 2
UNVERIFIED_AFFECTED = ("Data acquisition risk", "Monetization risk")

NATIONAL_SCOPE_ADJUSTMENT = 1
SCOPE_AFFECTED = ("Operational risk", "Scaling risk")

# Risk level bands (inclusive upper bounds)
LEVEL_BANDS: Tuple[Tuple[int, RiskLevel], ...] = (
    (3, RiskLevel.LOW),
    (5, RiskLevel.MODERATE),
    (7, RiskLevel.ELEVATED),
    (RISK_SCORE_MAX, RiskLevel.HIGH),
)


def _clamp(score: int) -> int:
    return max(RISK_SCORE_MIN, min(RISK_SCORE_MAX, score))


def score_to_level(score: int) -> RiskLevel:
    for upper_bound, level in LEVEL_BANDS:
        if score <= upper_bound:
            return level
    return RiskLevel.HIGH  # pragma: no cover - unreachable given bands


def analyze_risks(
    opportunity: OpportunityInput, capacity: MarketCapacityInput
) -> RiskAnalysis:
    assessments: List[RiskAssessment] = []

    for category, base_score, drivers, mitigations in RISK_TEMPLATES:
        score = base_score
        applied_drivers = list(drivers)

        if category in COMPETITION_AFFECTED:
            if opportunity.competition_level == CompetitionLevel.HIGH:
                score += HIGH_COMPETITION_ADJUSTMENT
                applied_drivers.append("High competition level (+%d)" % HIGH_COMPETITION_ADJUSTMENT)
            elif opportunity.competition_level == CompetitionLevel.LOW:
                score += LOW_COMPETITION_ADJUSTMENT
                applied_drivers.append("Low competition level (%d)" % LOW_COMPETITION_ADJUSTMENT)

        if category in LIQUIDITY_AFFECTED and capacity.liquidity_score < LOW_LIQUIDITY_THRESHOLD:
            score += LOW_LIQUIDITY_ADJUSTMENT
            applied_drivers.append("Low market liquidity (+%d)" % LOW_LIQUIDITY_ADJUSTMENT)

        if (
            category in UNVERIFIED_AFFECTED
            and capacity.data_tag != DataVerificationTag.VERIFIED
        ):
            score += UNVERIFIED_DATA_ADJUSTMENT
            applied_drivers.append(
                "Market data is %s, not VERIFIED (+%d)"
                % (capacity.data_tag.value, UNVERIFIED_DATA_ADJUSTMENT)
            )

        if (
            category in SCOPE_AFFECTED
            and opportunity.geographic_scope == GeographicScope.NATIONAL
        ):
            score += NATIONAL_SCOPE_ADJUSTMENT
            applied_drivers.append("National scope (+%d)" % NATIONAL_SCOPE_ADJUSTMENT)

        score = _clamp(score)
        assessments.append(
            RiskAssessment(
                category=category,
                level=score_to_level(score),
                score=score,
                drivers=applied_drivers,
                mitigations=list(mitigations),
            )
        )

    # Overall = ceiling-free integer average, rounded half up deterministically.
    total = sum(a.score for a in assessments)
    overall_score = _clamp(int(round(total / float(len(assessments)))))
    return RiskAnalysis(
        assessments=assessments,
        overall_risk_level=score_to_level(overall_score),
        overall_risk_score=overall_score,
    )
