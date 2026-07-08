"""Monetization planner.

Deterministic ranking of all thirteen monetization models required by the
Phase 3 spec. Every score is derived from named base constants plus
explainable adjustments driven by the opportunity, market capacity, and
directory type. No randomness; identical inputs always produce identical
rankings (ties broken by the fixed enum declaration order).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from engines.directory_blueprint.blueprint_models import (
    CompetitionLevel,
    DirectoryType,
    EffortLevel,
    MarketCapacityInput,
    MonetizationModel,
    MonetizationOption,
    MonetizationPlan,
    OpportunityInput,
    RiskLevel,
)

# ---------------------------------------------------------------------------
# Named constants — base profiles per monetization model
# (base_value 1-10, complexity, operational burden, risk)
# ---------------------------------------------------------------------------

BASE_PROFILES: Dict[MonetizationModel, Tuple[int, EffortLevel, EffortLevel, RiskLevel]] = {
    MonetizationModel.FEATURED_LISTINGS: (8, EffortLevel.LOW, EffortLevel.LOW, RiskLevel.LOW),
    MonetizationModel.SPONSORED_RESULTS: (7, EffortLevel.MEDIUM, EffortLevel.LOW, RiskLevel.LOW),
    MonetizationModel.LEAD_GENERATION: (9, EffortLevel.MEDIUM, EffortLevel.MEDIUM, RiskLevel.MODERATE),
    MonetizationModel.ADVERTISING: (5, EffortLevel.LOW, EffortLevel.LOW, RiskLevel.MODERATE),
    MonetizationModel.MEMBERSHIP: (6, EffortLevel.MEDIUM, EffortLevel.MEDIUM, RiskLevel.MODERATE),
    MonetizationModel.AFFILIATE: (6, EffortLevel.LOW, EffortLevel.LOW, RiskLevel.MODERATE),
    MonetizationModel.COUPONS: (4, EffortLevel.MEDIUM, EffortLevel.MEDIUM, RiskLevel.MODERATE),
    MonetizationModel.PREMIUM_PROFILES: (7, EffortLevel.LOW, EffortLevel.LOW, RiskLevel.LOW),
    MonetizationModel.EMAIL_SPONSORSHIPS: (5, EffortLevel.LOW, EffortLevel.MEDIUM, RiskLevel.LOW),
    MonetizationModel.EVENTS: (4, EffortLevel.HIGH, EffortLevel.HIGH, RiskLevel.ELEVATED),
    MonetizationModel.MARKETPLACE: (7, EffortLevel.HIGH, EffortLevel.HIGH, RiskLevel.ELEVATED),
    MonetizationModel.BOOKING: (6, EffortLevel.HIGH, EffortLevel.HIGH, RiskLevel.ELEVATED),
    MonetizationModel.DONATIONS: (2, EffortLevel.LOW, EffortLevel.LOW, RiskLevel.LOW),
}

# Directory-type affinity adjustments (+/- applied to base value)
TYPE_AFFINITY: Dict[DirectoryType, Dict[MonetizationModel, int]] = {
    DirectoryType.TRAVEL: {
        MonetizationModel.AFFILIATE: 3,
        MonetizationModel.BOOKING: 2,
        MonetizationModel.ADVERTISING: 1,
    },
    DirectoryType.LOCAL_SERVICES: {
        MonetizationModel.LEAD_GENERATION: 1,
        MonetizationModel.FEATURED_LISTINGS: 1,
    },
    DirectoryType.B2B: {
        MonetizationModel.LEAD_GENERATION: 1,
        MonetizationModel.MEMBERSHIP: 2,
    },
    DirectoryType.EDUCATION: {
        MonetizationModel.LEAD_GENERATION: 1,
        MonetizationModel.PREMIUM_PROFILES: 1,
    },
    DirectoryType.MARKETPLACE: {
        MonetizationModel.MARKETPLACE: 2,
        MonetizationModel.BOOKING: 1,
    },
    DirectoryType.NICHE_INTEREST: {
        MonetizationModel.ADVERTISING: 1,
        MonetizationModel.AFFILIATE: 1,
    },
}

# Liquidity thresholds: thin markets penalize volume-dependent models
LOW_LIQUIDITY_THRESHOLD = 30.0
VOLUME_DEPENDENT_MODELS = (
    MonetizationModel.ADVERTISING,
    MonetizationModel.SPONSORED_RESULTS,
    MonetizationModel.MARKETPLACE,
)
LOW_LIQUIDITY_PENALTY = 2

# High competition boosts differentiated/relationship models
HIGH_COMPETITION_BOOSTED_MODELS = (
    MonetizationModel.LEAD_GENERATION,
    MonetizationModel.PREMIUM_PROFILES,
)
HIGH_COMPETITION_BOOST = 1

VALUE_SCORE_MIN = 1
VALUE_SCORE_MAX = 10

# Deterministic tie-break order = declaration order of the enum
_MODEL_ORDER: List[MonetizationModel] = list(MonetizationModel)


def _clamp(value: int) -> int:
    return max(VALUE_SCORE_MIN, min(VALUE_SCORE_MAX, value))


def score_model(
    model: MonetizationModel,
    directory_type: DirectoryType,
    opportunity: OpportunityInput,
    capacity: MarketCapacityInput,
) -> Tuple[int, List[str]]:
    """Return (value_score, list of applied adjustment explanations)."""
    base_value = BASE_PROFILES[model][0]
    value = base_value
    reasons = ["base value %d" % base_value]

    affinity = TYPE_AFFINITY.get(directory_type, {}).get(model, 0)
    if affinity:
        value += affinity
        reasons.append("%+d directory-type affinity (%s)" % (affinity, directory_type.value))

    if capacity.liquidity_score < LOW_LIQUIDITY_THRESHOLD and model in VOLUME_DEPENDENT_MODELS:
        value -= LOW_LIQUIDITY_PENALTY
        reasons.append("-%d low market liquidity penalty" % LOW_LIQUIDITY_PENALTY)

    if (
        opportunity.competition_level == CompetitionLevel.HIGH
        and model in HIGH_COMPETITION_BOOSTED_MODELS
    ):
        value += HIGH_COMPETITION_BOOST
        reasons.append("+%d high-competition differentiation boost" % HIGH_COMPETITION_BOOST)

    return _clamp(value), reasons


def plan_monetization(
    opportunity: OpportunityInput,
    capacity: MarketCapacityInput,
    directory_type: DirectoryType,
) -> MonetizationPlan:
    scored: List[MonetizationOption] = []
    for model in _MODEL_ORDER:
        value, reasons = score_model(model, directory_type, opportunity, capacity)
        base_value, complexity, burden, risk = BASE_PROFILES[model]
        scored.append(
            MonetizationOption(
                model=model,
                rank=0,  # assigned after sorting
                estimated_value_score=value,
                implementation_complexity=complexity,
                operational_burden=burden,
                risk=risk,
                rationale="; ".join(reasons),
            )
        )

    # Stable sort: highest value first; declaration order breaks ties.
    scored.sort(key=lambda opt: (-opt.estimated_value_score, _MODEL_ORDER.index(opt.model)))
    ranked = [
        MonetizationOption(
            model=opt.model,
            rank=index + 1,
            estimated_value_score=opt.estimated_value_score,
            implementation_complexity=opt.implementation_complexity,
            operational_burden=opt.operational_burden,
            risk=opt.risk,
            rationale=opt.rationale,
        )
        for index, opt in enumerate(scored)
    ]
    return MonetizationPlan(primary_model=ranked[0].model, ranked_options=ranked)
