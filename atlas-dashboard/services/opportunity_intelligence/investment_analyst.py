"""
atlas/services/opportunity_intelligence/investment_analyst.py

AES-012F — Investment Analyst Foundation.

Characterizes investment ATTRACTIVENESS AND RISK STRUCTURE — never a
final INVEST/REJECT recommendation (that is the Autonomous Investment
Committee's job, a later stage) and never a financial projection.
Consumes the already-derived MarketProfile (AES-012B),
OpportunityClassification (AES-012C), CompetitionProfile (AES-012D),
and RevenueProfile (AES-012E) structured outputs; does not re-parse
raw opportunity text and does not duplicate the responsibilities of
any earlier stage. No AI, no LLM calls, no web access, no external
APIs, no persistence, no global state, no randomness, no timestamps.

Honesty rule (same convention as every other real analyst in this
package): a field is only set to something other than "UNKNOWN" when a
real, recognized structured signal was found upstream. An unknown
upstream signal is excluded from scoring entirely — it is never
treated as negative evidence (never silently scored as LOW/0).
Deterministic classification via small, explicit, configurable lookup
tables — no hardcoded if/elif chains.

Dimensions produced:
  - market_attractiveness: from MarketProfile.market_scope (a broader
    addressable geography is more attractive) via
    MARKET_SCOPE_ATTRACTIVENESS.
  - revenue_attractiveness: from RevenueProfile.monetization_strength
    and RevenueProfile.revenue_scalability (strong monetization + high
    scalability improve attractiveness) via _combine_levels.
  - competitive_position: the inverse of
    CompetitionProfile.competitive_risk, refined upward one level when
    CompetitionProfile.market_fragmentation is "HIGH" (a fragmented
    market is more accessible to a new entrant).
  - execution_complexity: from OpportunityClassification.business_type
    via EXECUTION_COMPLEXITY_BY_BUSINESS_TYPE (marketplaces and
    service businesses are harder to execute; directories and content
    publishers are comparatively simple).
  - investment_risk: a summary combination of
    CompetitionProfile.competitive_risk and execution_complexity via
    _combine_levels — deliberately NOT one of investment_score's own
    inputs (it is built from signals the score already counts, so
    including it too would double-count the same evidence).
  - investment_score: a bounded 0-100 point total from
    market_attractiveness, revenue_attractiveness, competitive_position,
    and execution_complexity (see INVESTMENT_SCORE_POINTS for the
    documented point rules). An unrecognized/UNKNOWN input contributes
    zero points, never a negative penalty. None (not 0) when nothing
    was recognized — 0 would misrepresent "actively bad" rather than
    "no evidence".

Confidence (reuses the existing data_confidence field) reflects how
many of the four dimension signals were actually recognized upstream
— evidence quality, never attractiveness. Never "VERIFIED": nothing
here is confirmed against real external data.

Independent package: no Flask, no repositories, no persistence, no
services.opportunity_v2, no orchestrator, no Learning Memory, no
network I/O of any kind.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Tuple

from services.opportunity_intelligence.models import (
    CompetitionProfile,
    InvestmentProfile,
    MarketProfile,
    Opportunity,
    OpportunityClassification,
    RevenueProfile,
)


class Level(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Reference data — small, static, explicitly configurable lookup tables.
# Adjust/extend these tables to change investment-characterization
# behavior; no logic branches need to change.
# ---------------------------------------------------------------------------

# MarketProfile.market_scope -> market_attractiveness. Only the scopes
# MarketResearchAnalyst actually produces (CITY/STATE/NATIONAL) are
# represented; REGIONAL/UNKNOWN honestly fall through to UNKNOWN.
MARKET_SCOPE_ATTRACTIVENESS: Dict[str, Level] = {
    "NATIONAL": Level.HIGH,
    "STATE": Level.MODERATE,
    "CITY": Level.LOW,
}

# Normalized (stripped, lower-cased) OpportunityClassification.business_type
# -> execution_complexity. Marketplaces and service businesses require more
# operational/trust-and-payments machinery; directories and content
# publishers are comparatively simple to execute.
EXECUTION_COMPLEXITY_BY_BUSINESS_TYPE: Dict[str, Level] = {
    "directory": Level.LOW,
    "content publisher": Level.LOW,
    "ecommerce": Level.MODERATE,
    "saas": Level.MODERATE,
    "service provider": Level.HIGH,
    "marketplace": Level.HIGH,
}

# MonetizationStrength (revenue_analyst.py vocabulary) -> this module's
# LOW/MODERATE/HIGH scale, so it can be combined with revenue_scalability
# (already LOW/MODERATE/HIGH) on a common footing.
MONETIZATION_STRENGTH_TO_LEVEL: Dict[str, Level] = {
    "STRONG": Level.HIGH,
    "MODERATE": Level.MODERATE,
    "WEAK": Level.LOW,
}

# Point rules for investment_score (documented, bounded 0-100 total).
# An unrecognized/UNKNOWN dimension contributes zero points — never a
# negative penalty. investment_risk is intentionally NOT a scoring
# input: it is itself built from competitive_risk + execution_complexity,
# both of which already contribute via competitive_position and
# execution_complexity, so including it too would double-count evidence.
INVESTMENT_SCORE_POINTS: Dict[str, Dict[str, int]] = {
    "market_attractiveness": {"HIGH": 25, "MODERATE": 12, "LOW": 0, "UNKNOWN": 0},
    "revenue_attractiveness": {"HIGH": 30, "MODERATE": 15, "LOW": 0, "UNKNOWN": 0},
    "competitive_position": {"HIGH": 25, "MODERATE": 12, "LOW": 0, "UNKNOWN": 0},
    # execution_complexity is inverted: LOW complexity is favorable.
    "execution_complexity": {"LOW": 20, "MODERATE": 10, "HIGH": 0, "UNKNOWN": 0},
}

_LEVEL_POINTS: Dict[str, int] = {"LOW": 0, "MODERATE": 1, "HIGH": 2}
_RISK_SCALE: Tuple[str, ...] = (Level.LOW.value, Level.MODERATE.value, Level.HIGH.value)
_CONFIDENCE_ORDER: Tuple[str, ...] = ("UNKNOWN", "LOW", "MODERATE", "HIGH")


def _normalize_key(value: object) -> str:
    """Defensive normalization: None-safe, whitespace-trimmed, lower-cased."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _normalize_level(value: object) -> str:
    """
    Accepts an enum member or a string (any case/spacing) and returns a
    canonical "LOW"/"MODERATE"/"HIGH"/"UNKNOWN" — or "UNKNOWN" for
    None, blank, or any unrecognized/future value. Never raises.
    """
    token = _normalize_key(value).upper()
    if token in (Level.LOW.value, Level.MODERATE.value, Level.HIGH.value):
        return token
    return Level.UNKNOWN.value


def _combine_levels(*levels: str) -> str:
    """
    Averages the point value of every recognized (non-UNKNOWN) level
    and maps the average back onto LOW/MODERATE/HIGH. Unknown levels
    are excluded from the average entirely — never treated as
    negative evidence. Returns "UNKNOWN" only when nothing was
    recognized at all.
    """
    known_points = [_LEVEL_POINTS[level] for level in levels if level in _LEVEL_POINTS]
    if not known_points:
        return Level.UNKNOWN.value

    average = sum(known_points) / len(known_points)
    if average >= 1.5:
        return Level.HIGH.value
    if average >= 0.5:
        return Level.MODERATE.value
    return Level.LOW.value


def _bump_one_level(level: str) -> str:
    """Moves a recognized LOW/MODERATE/HIGH level up one step, capped at HIGH."""
    if level not in _RISK_SCALE:
        return level
    idx = _RISK_SCALE.index(level)
    return _RISK_SCALE[min(idx + 1, len(_RISK_SCALE) - 1)]


def _compute_market_attractiveness(market_profile: MarketProfile) -> str:
    scope = _normalize_key(market_profile.market_scope).upper()
    return MARKET_SCOPE_ATTRACTIVENESS.get(scope, Level.UNKNOWN).value


def _compute_revenue_attractiveness(revenue_profile: RevenueProfile) -> str:
    strength_key = _normalize_key(revenue_profile.monetization_strength).upper()
    strength_level = MONETIZATION_STRENGTH_TO_LEVEL.get(strength_key, Level.UNKNOWN).value
    scalability_level = _normalize_level(revenue_profile.revenue_scalability)
    return _combine_levels(strength_level, scalability_level)


def _compute_competitive_position(competition_profile: CompetitionProfile) -> str:
    risk_level = _normalize_level(competition_profile.competitive_risk)
    if risk_level == Level.UNKNOWN.value:
        return Level.UNKNOWN.value

    # Position is the inverse of risk: high risk -> low position.
    position = _RISK_SCALE[len(_RISK_SCALE) - 1 - _RISK_SCALE.index(risk_level)]

    if _normalize_key(competition_profile.market_fragmentation).upper() == Level.HIGH.value:
        position = _bump_one_level(position)

    return position


def _compute_execution_complexity(classification: OpportunityClassification) -> str:
    business_type_key = _normalize_key(classification.business_type)
    return EXECUTION_COMPLEXITY_BY_BUSINESS_TYPE.get(business_type_key, Level.UNKNOWN).value


def _compute_investment_score(
    market_attractiveness: str,
    revenue_attractiveness: str,
    competitive_position: str,
    execution_complexity: str,
) -> Optional[int]:
    dimensions = {
        "market_attractiveness": market_attractiveness,
        "revenue_attractiveness": revenue_attractiveness,
        "competitive_position": competitive_position,
        "execution_complexity": execution_complexity,
    }
    if all(level == Level.UNKNOWN.value for level in dimensions.values()):
        return None

    return sum(INVESTMENT_SCORE_POINTS[name][level] for name, level in dimensions.items())


def _compute_confidence(recognized_flags: Tuple[bool, ...]) -> str:
    recognized_count = sum(1 for flag in recognized_flags if flag)
    if recognized_count == 0:
        return "UNKNOWN"
    if recognized_count == 1:
        return "LOW"
    if recognized_count == 2:
        return "MODERATE"
    return "HIGH"


class InvestmentAnalyst:
    """
    Pure, deterministic, offline Investment Analysis stage. Satisfies
    services.opportunity_intelligence.stages.InvestmentAnalysisStageProtocol
    structurally (run(Opportunity, MarketProfile, OpportunityClassification,
    CompetitionProfile, RevenueProfile) -> InvestmentProfile) — no
    inheritance required. No global state, no singletons: every
    instance is independent and stateless. Never mutates its inputs.
    Never emits a final INVEST/REJECT recommendation — that is the
    Committee Recommendation stage's job.
    """

    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
        competition_profile: CompetitionProfile,
        revenue_profile: RevenueProfile,
    ) -> InvestmentProfile:
        market_attractiveness = _compute_market_attractiveness(market_profile)
        revenue_attractiveness = _compute_revenue_attractiveness(revenue_profile)
        competitive_position = _compute_competitive_position(competition_profile)
        execution_complexity = _compute_execution_complexity(classification)

        investment_risk = _combine_levels(
            _normalize_level(competition_profile.competitive_risk),
            execution_complexity,
        )

        investment_score = _compute_investment_score(
            market_attractiveness,
            revenue_attractiveness,
            competitive_position,
            execution_complexity,
        )

        confidence = _compute_confidence(
            (
                market_attractiveness != Level.UNKNOWN.value,
                revenue_attractiveness != Level.UNKNOWN.value,
                competitive_position != Level.UNKNOWN.value,
                execution_complexity != Level.UNKNOWN.value,
            )
        )

        return InvestmentProfile(
            market_attractiveness=market_attractiveness,
            revenue_attractiveness=revenue_attractiveness,
            competitive_position=competitive_position,
            execution_complexity=execution_complexity,
            investment_risk=investment_risk,
            investment_score=investment_score,
            data_confidence=confidence,
        )
