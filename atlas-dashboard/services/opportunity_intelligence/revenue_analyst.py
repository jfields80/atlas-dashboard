"""
atlas/services/opportunity_intelligence/revenue_analyst.py

AES-012E — Deterministic Revenue Analyst Foundation.

Characterizes HOW an opportunity could monetize — never HOW MUCH it
could earn. Consumes the already-derived MarketProfile (AES-012B),
OpportunityClassification (AES-012C), and CompetitionProfile
(AES-012D) structured outputs; does not re-parse raw opportunity text
and does not duplicate the responsibilities of Market Research,
Classification, or Competition Analysis. No AI, no LLM calls, no web
access, no external APIs, no persistence, no global state, no
randomness, no timestamps.

This stage answers "how could this type of opportunity generate
revenue?" — never "how much revenue will this opportunity generate?".
It never fabricates revenue amounts, monthly/annual revenue, average
order value, conversion rates, customer lifetime value, prices,
margins, market size, transaction volume, advertising rates,
subscriber counts, lead values, or growth rates.

Honesty rule (same convention as market_research_analyst.py,
opportunity_classifier.py, and competition_analyst.py): a field is
only set to something other than "UNKNOWN" when a real, recognized
structured signal was found upstream. Deterministic classification via
a small, explicit, configurable lookup table
(BUSINESS_TYPE_REVENUE_PROFILE) — no hardcoded if/elif chains.

Rule precedence (deterministic, documented):
  1. A recognized OpportunityClassification.business_model (a string
     that already names one of this module's known revenue
     mechanisms) takes precedence as the primary revenue model.
  2. Otherwise, a recognized OpportunityClassification.business_type
     (a key in BUSINESS_TYPE_REVENUE_PROFILE) supplies the primary
     revenue model and its baseline characteristics.
  3. market_vertical is accepted as an input but has no dedicated rule
     in this foundation ticket — no worked example ties a specific
     vertical to a monetization mechanism beyond what business_type
     already encodes, so inventing one would be fabrication.
  4. CompetitionProfile.competitor_archetype may add secondary revenue
     models (never overrides the primary, never invents a dollar
     figure).
  5. A separate market_scope-based refinement is intentionally not
     implemented: CompetitionProfile.competitor_archetype/
     competition_scope already reflect MarketProfile.market_scope
     (derived by CompetitionAnalyst), so adding a second rule keyed on
     market_scope directly would duplicate that stage's
     responsibility.
  6. Otherwise, every field stays "UNKNOWN".
  When a recognized business_model names a different mechanism than
  business_type's own primary model, the business_type's primary
  model is demoted to a secondary model (never silently dropped) and
  the mismatch is treated as a conflict that reduces confidence one
  level — never a fabricated MIXED result invented to paper over the
  disagreement, since the business_model signal is by definition more
  specific than the broader business_type bucket.

Independent package: no Flask, no repositories, no persistence, no
services.opportunity_v2, no orchestrator, no Learning Memory, no
network I/O of any kind.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Tuple

from services.opportunity_intelligence.models import (
    CompetitionProfile,
    MarketProfile,
    Opportunity,
    OpportunityClassification,
    RevenueProfile,
)


class PrimaryRevenueModel(str, Enum):
    ADVERTISING = "ADVERTISING"
    FEATURED_LISTINGS = "FEATURED_LISTINGS"
    LEAD_GENERATION = "LEAD_GENERATION"
    TRANSACTION_FEES = "TRANSACTION_FEES"
    SUBSCRIPTIONS = "SUBSCRIPTIONS"
    DIRECT_SERVICES = "DIRECT_SERVICES"
    PRODUCT_SALES = "PRODUCT_SALES"
    AFFILIATE_REVENUE = "AFFILIATE_REVENUE"
    SPONSORSHIPS = "SPONSORSHIPS"
    LICENSING = "LICENSING"
    MEMBERSHIP = "MEMBERSHIP"
    USAGE_FEES = "USAGE_FEES"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class RevenuePotential(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class MonetizationStrength(str, Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Reference data — a small, static, explicitly configurable lookup
# table keyed by a normalized (stripped, lower-cased)
# OpportunityClassification.business_type. Adjust/extend this table to
# change monetization-characterization behavior; no logic branches
# need to change. Only business types with a worked-example basis
# (AES-012E ticket) are represented here.
# ---------------------------------------------------------------------------

BUSINESS_TYPE_REVENUE_PROFILE: Dict[str, dict] = {
    "directory": {
        "primary_revenue_model": PrimaryRevenueModel.FEATURED_LISTINGS,
        "secondary_revenue_models": (
            PrimaryRevenueModel.ADVERTISING,
            PrimaryRevenueModel.LEAD_GENERATION,
            PrimaryRevenueModel.MEMBERSHIP,
            PrimaryRevenueModel.SPONSORSHIPS,
        ),
        "recurring_revenue_potential": RevenuePotential.MODERATE,
        "transaction_revenue_potential": RevenuePotential.LOW,
        "revenue_scalability": RevenuePotential.HIGH,
        "monetization_strength": MonetizationStrength.MODERATE,
    },
    "marketplace": {
        "primary_revenue_model": PrimaryRevenueModel.TRANSACTION_FEES,
        "secondary_revenue_models": (
            PrimaryRevenueModel.ADVERTISING,
            PrimaryRevenueModel.FEATURED_LISTINGS,
            PrimaryRevenueModel.SUBSCRIPTIONS,
        ),
        "recurring_revenue_potential": RevenuePotential.MODERATE,
        "transaction_revenue_potential": RevenuePotential.HIGH,
        "revenue_scalability": RevenuePotential.HIGH,
        "monetization_strength": MonetizationStrength.STRONG,
    },
    "saas": {
        "primary_revenue_model": PrimaryRevenueModel.SUBSCRIPTIONS,
        "secondary_revenue_models": (
            PrimaryRevenueModel.LICENSING,
            PrimaryRevenueModel.USAGE_FEES,
        ),
        "recurring_revenue_potential": RevenuePotential.HIGH,
        "transaction_revenue_potential": RevenuePotential.MODERATE,
        "revenue_scalability": RevenuePotential.HIGH,
        "monetization_strength": MonetizationStrength.STRONG,
    },
    "service provider": {
        "primary_revenue_model": PrimaryRevenueModel.DIRECT_SERVICES,
        "secondary_revenue_models": (
            PrimaryRevenueModel.MEMBERSHIP,
            PrimaryRevenueModel.SUBSCRIPTIONS,
        ),
        "recurring_revenue_potential": RevenuePotential.MODERATE,
        "transaction_revenue_potential": RevenuePotential.MODERATE,
        "revenue_scalability": RevenuePotential.LOW,
        "monetization_strength": MonetizationStrength.WEAK,
    },
    "ecommerce": {
        "primary_revenue_model": PrimaryRevenueModel.PRODUCT_SALES,
        "secondary_revenue_models": (
            PrimaryRevenueModel.AFFILIATE_REVENUE,
            PrimaryRevenueModel.SUBSCRIPTIONS,
        ),
        "recurring_revenue_potential": RevenuePotential.LOW,
        "transaction_revenue_potential": RevenuePotential.HIGH,
        "revenue_scalability": RevenuePotential.MODERATE,
        "monetization_strength": MonetizationStrength.MODERATE,
    },
    "content publisher": {
        "primary_revenue_model": PrimaryRevenueModel.ADVERTISING,
        "secondary_revenue_models": (
            PrimaryRevenueModel.AFFILIATE_REVENUE,
            PrimaryRevenueModel.MEMBERSHIP,
            PrimaryRevenueModel.SPONSORSHIPS,
        ),
        "recurring_revenue_potential": RevenuePotential.MODERATE,
        "transaction_revenue_potential": RevenuePotential.LOW,
        "revenue_scalability": RevenuePotential.HIGH,
        "monetization_strength": MonetizationStrength.MODERATE,
    },
}

# Competitor archetype (services.opportunity_intelligence.competition_analyst
# .SCOPE_COMPETITION_PROFILE's own vocabulary) -> secondary revenue models it
# conservatively suggests. Never overrides the primary model, never invents
# a dollar figure.
COMPETITION_ARCHETYPE_SECONDARY_MODELS: Dict[str, Tuple[PrimaryRevenueModel, ...]] = {
    "fragmented_local_providers": (
        PrimaryRevenueModel.FEATURED_LISTINGS,
        PrimaryRevenueModel.LEAD_GENERATION,
    ),
    "national_platforms": (
        PrimaryRevenueModel.SUBSCRIPTIONS,
        PrimaryRevenueModel.TRANSACTION_FEES,
    ),
}

_CONFIDENCE_ORDER: Tuple[str, ...] = ("UNKNOWN", "LOW", "MODERATE", "HIGH")


def _normalize_key(value: object) -> str:
    """Defensive normalization: None-safe, whitespace-trimmed, lower-cased."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _normalize_revenue_model(value: object) -> Optional[PrimaryRevenueModel]:
    """
    Accepts an enum member or a string (any case/spacing), returns the
    matching PrimaryRevenueModel if OpportunityClassification.business_model
    already names one of this module's known revenue mechanisms —
    otherwise None. Never raises on an unrecognized/future value.
    """
    if value is None:
        return None
    token = str(value).strip().upper().replace(" ", "_").replace("-", "_")
    if not token or token in (PrimaryRevenueModel.UNKNOWN.value, PrimaryRevenueModel.MIXED.value):
        return None
    try:
        return PrimaryRevenueModel(token)
    except ValueError:
        return None


def _is_market_scope_known(market_profile: MarketProfile) -> bool:
    return _normalize_key(market_profile.market_scope) not in ("", "unknown")


def _is_competition_usable(competition_profile: CompetitionProfile) -> bool:
    return _normalize_key(competition_profile.data_confidence) == "estimated"


def _compute_confidence(
    business_type_recognized: bool,
    business_model_recognized: bool,
    competition_usable: bool,
    market_scope_known: bool,
    conflict: bool,
) -> str:
    if not business_type_recognized and not business_model_recognized:
        return "UNKNOWN"

    recognized_count = int(business_type_recognized) + int(business_model_recognized)
    level = "HIGH" if recognized_count >= 2 else "MODERATE"

    if level == "MODERATE" and competition_usable and market_scope_known:
        level = "HIGH"

    if conflict:
        idx = _CONFIDENCE_ORDER.index(level)
        level = _CONFIDENCE_ORDER[max(idx - 1, 0)]

    return level


class RevenueAnalyst:
    """
    Pure, deterministic, offline Revenue Analysis stage. Satisfies
    services.opportunity_intelligence.stages.RevenueAnalysisStageProtocol
    structurally (run(Opportunity, MarketProfile, OpportunityClassification,
    CompetitionProfile) -> RevenueProfile) — no inheritance required. No
    global state, no singletons: every instance is independent and
    stateless. Never mutates its inputs.
    """

    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
        competition_profile: CompetitionProfile,
    ) -> RevenueProfile:
        business_type_key = _normalize_key(classification.business_type)
        type_profile = BUSINESS_TYPE_REVENUE_PROFILE.get(business_type_key)
        business_type_recognized = type_profile is not None

        business_model_signal = _normalize_revenue_model(classification.business_model)
        business_model_recognized = business_model_signal is not None

        if not business_type_recognized and not business_model_recognized:
            return RevenueProfile()

        secondary_models: set = set()
        conflict = False

        if business_model_recognized:
            primary = business_model_signal
            if business_type_recognized:
                type_primary = type_profile["primary_revenue_model"]
                if type_primary != primary:
                    conflict = True
                    secondary_models.add(type_primary.value)
                secondary_models.update(m.value for m in type_profile["secondary_revenue_models"])
        else:
            primary = type_profile["primary_revenue_model"]
            secondary_models.update(m.value for m in type_profile["secondary_revenue_models"])

        if business_type_recognized:
            recurring = type_profile["recurring_revenue_potential"].value
            transaction = type_profile["transaction_revenue_potential"].value
            scalability = type_profile["revenue_scalability"].value
            strength = type_profile["monetization_strength"].value
        else:
            recurring = transaction = scalability = strength = "UNKNOWN"

        archetype_key = _normalize_key(competition_profile.competitor_archetype)
        for model in COMPETITION_ARCHETYPE_SECONDARY_MODELS.get(archetype_key, ()):
            secondary_models.add(model.value)

        secondary_models.discard(primary.value)

        confidence = _compute_confidence(
            business_type_recognized=business_type_recognized,
            business_model_recognized=business_model_recognized,
            competition_usable=_is_competition_usable(competition_profile),
            market_scope_known=_is_market_scope_known(market_profile),
            conflict=conflict,
        )

        return RevenueProfile(
            primary_revenue_model=primary.value,
            secondary_revenue_models=sorted(secondary_models),
            recurring_revenue_potential=recurring,
            transaction_revenue_potential=transaction,
            monetization_strength=strength,
            revenue_scalability=scalability,
            data_confidence=confidence,
        )
