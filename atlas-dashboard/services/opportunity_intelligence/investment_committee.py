"""
atlas/services/opportunity_intelligence/investment_committee.py

AES-012G — Investment Committee Foundation.

The first stage allowed to answer "should Atlas pursue this
opportunity, and why?" — never with prose, never with a memo (that is
a later stage's job). Consumes the already-derived MarketProfile
(AES-012B), OpportunityClassification (AES-012C), CompetitionProfile
(AES-012D), RevenueProfile (AES-012E), and InvestmentProfile
(AES-012F) structured outputs off the OpportunityAssessment; does not
re-analyze raw opportunity text and does not duplicate any earlier
stage's logic. No AI, no LLM calls, no web access, no external APIs,
no persistence, no global state, no randomness, no timestamps.

Honesty rule (same convention as every other real stage in this
package): a rationale code is only emitted when a real, recognized
structured signal was found upstream. Deterministic classification via
a small, explicit, ordered rule table — no hardcoded nested if/elif
sprawl.

Decision precedence (deterministic, documented, first match wins):
  R1. weak_evidence_count >= 3 (a majority of the 5 upstream
      confidence signals are "UNKNOWN") -> "UNKNOWN". Low confidence
      across multiple analysts means there isn't enough evidence to
      decide at all — this check runs first and short-circuits every
      other rule.
  R2. RevenueProfile.monetization_strength == "WEAK" AND
      InvestmentProfile.investment_risk == "HIGH" -> "REJECT". The
      ticket's own worked example: weak monetization plus high risk is
      conservative grounds to pass regardless of anything else.
  R3. InvestmentProfile.investment_score >= 70 AND
      RevenueProfile.monetization_strength == "STRONG" AND
      InvestmentProfile.investment_risk in ("LOW", "MODERATE") ->
      "INVEST". The ticket's own worked example: a strong investment
      profile plus strong monetization plus moderate-or-low risk.
  R4. InvestmentProfile.investment_score is None, OR
      InvestmentProfile.investment_risk == "UNKNOWN", OR
      RevenueProfile.monetization_strength == "UNKNOWN" -> "HOLD". A
      genuinely missing piece of decision-relevant evidence (but not
      enough missing evidence to trigger R1) means the opportunity is
      not yet resolvable either way — the ticket's own "moderate
      opportunity plus unknown evidence" example.
  R5. InvestmentProfile.investment_score >= 50 AND
      InvestmentProfile.investment_risk != "HIGH" ->
      "INVEST_WITH_CAUTION".
  R6. Otherwise -> "REJECT" (a low score, or a high-risk profile that
      didn't already clear R3's stricter bar).
No single field decides alone: every rule (other than the evidence-
count gate in R1) requires at least two independent signals to agree.

recommendation_strength is a secondary, purely descriptive field
derived only from InvestmentProfile.investment_score's magnitude — it
never influences the decision itself (see _compute_strength).

rationale_codes are a small, closed, alphabetically-sorted,
duplicate-free set of stable string codes describing which structured
signals were present — never prose.

confidence reuses the existing Recommendation.confidence field
(bounded [0.0, 1.0]) — the fraction of the 5 upstream stages that
reported a recognized (non-"UNKNOWN") confidence signal. It reflects
evidence quantity/quality, never how attractive the opportunity looks,
and — being a bounded float rather than a string enum — it can never
render as "VERIFIED": nothing here is confirmed against real external
data.

Independent package: no Flask, no repositories, no persistence, no
services.opportunity_v2, no orchestrator, no Learning Memory, no
network I/O of any kind.
"""

from __future__ import annotations

from typing import List, Optional

from services.opportunity_intelligence.models import (
    CompetitionProfile,
    InvestmentProfile,
    MarketProfile,
    OpportunityAssessment,
    OpportunityClassification,
    Recommendation,
    RevenueProfile,
    UNKNOWN,
)


def _normalize_key(value: object) -> str:
    """Defensive normalization: None-safe, whitespace-trimmed, upper-cased."""
    if value is None:
        return ""
    return str(value).strip().upper()


def _is_recognized_confidence(value: object) -> bool:
    token = _normalize_key(value)
    return token not in ("", UNKNOWN)


def _count_weak_evidence(
    market_profile: MarketProfile,
    classification: OpportunityClassification,
    competition_profile: CompetitionProfile,
    revenue_profile: RevenueProfile,
    investment_profile: InvestmentProfile,
) -> int:
    signals = (
        market_profile.data_confidence,
        classification.confidence,
        competition_profile.data_confidence,
        revenue_profile.data_confidence,
        investment_profile.data_confidence,
    )
    return sum(1 for signal in signals if not _is_recognized_confidence(signal))


def _compute_decision(
    weak_evidence_count: int,
    investment_score: Optional[int],
    investment_risk: str,
    monetization_strength: str,
) -> str:
    if weak_evidence_count >= 3:
        return "UNKNOWN"

    if monetization_strength == "WEAK" and investment_risk == "HIGH":
        return "REJECT"

    if (
        investment_score is not None
        and investment_score >= 70
        and monetization_strength == "STRONG"
        and investment_risk in ("LOW", "MODERATE")
    ):
        return "INVEST"

    if investment_score is None or investment_risk == UNKNOWN or monetization_strength == UNKNOWN:
        return "HOLD"

    if investment_score >= 50 and investment_risk != "HIGH":
        return "INVEST_WITH_CAUTION"

    return "REJECT"


def _compute_strength(decision: str, investment_score: Optional[int]) -> str:
    """
    Purely descriptive: how strongly the numeric investment_score
    supports whatever decision was already made. Never itself an input
    to the decision.
    """
    if decision == "UNKNOWN":
        return UNKNOWN
    if investment_score is None:
        return "WEAK"
    if investment_score >= 80:
        return "STRONG"
    if investment_score >= 50:
        return "MODERATE"
    return "WEAK"


def _compute_confidence(weak_evidence_count: int) -> float:
    recognized_count = 5 - weak_evidence_count
    return round(recognized_count / 5.0, 2)


# ---------------------------------------------------------------------------
# Rationale codes — a small, closed, stable set. Each rule reads only an
# already-derived structured field; no re-parsing, no duplicated logic.
# Collected into a set (so duplicates are structurally impossible) and
# sorted before being returned (so ordering never depends on dict/set
# iteration order).
# ---------------------------------------------------------------------------


def _compute_rationale_codes(
    market_profile: MarketProfile,
    competition_profile: CompetitionProfile,
    revenue_profile: RevenueProfile,
    investment_profile: InvestmentProfile,
    weak_evidence_count: int,
) -> List[str]:
    codes: set = set()

    if revenue_profile.monetization_strength == "STRONG":
        codes.add("HIGH_MONETIZATION")
    elif revenue_profile.monetization_strength == "WEAK":
        codes.add("WEAK_MONETIZATION")

    if competition_profile.competitive_risk == "LOW":
        codes.add("LOW_COMPETITIVE_RISK")
    elif competition_profile.competitive_risk == "HIGH":
        codes.add("HIGH_COMPETITIVE_RISK")

    if investment_profile.execution_complexity == "HIGH":
        codes.add("HIGH_EXECUTION_COMPLEXITY")
    elif investment_profile.execution_complexity == "LOW":
        codes.add("LOW_EXECUTION_COMPLEXITY")

    if revenue_profile.revenue_scalability == "HIGH":
        codes.add("HIGH_SCALABILITY")
    elif revenue_profile.revenue_scalability == "LOW":
        codes.add("LOW_SCALABILITY")

    if _normalize_key(market_profile.market_scope) == UNKNOWN:
        codes.add("UNKNOWN_MARKET")

    if weak_evidence_count >= 3:
        codes.add("LIMITED_EVIDENCE")

    return sorted(codes)


class InvestmentCommittee:
    """
    Pure, deterministic, offline Committee Recommendation stage.
    Satisfies
    services.opportunity_intelligence.stages.CommitteeRecommendationStageProtocol
    structurally (run(OpportunityAssessment) -> Recommendation) — no
    inheritance required. No global state, no singletons: every
    instance is independent and stateless. Never mutates its input.
    Never generates prose or a memo — that is a later stage's job.
    """

    def run(self, assessment: OpportunityAssessment) -> Recommendation:
        market_profile = assessment.market_profile or MarketProfile()
        classification = assessment.classification or OpportunityClassification()
        competition_profile = assessment.competition_profile or CompetitionProfile()
        revenue_profile = assessment.revenue_profile or RevenueProfile()
        investment_profile = assessment.investment_profile or InvestmentProfile()

        weak_evidence_count = _count_weak_evidence(
            market_profile, classification, competition_profile, revenue_profile, investment_profile
        )

        decision = _compute_decision(
            weak_evidence_count=weak_evidence_count,
            investment_score=investment_profile.investment_score,
            investment_risk=_normalize_key(investment_profile.investment_risk),
            monetization_strength=_normalize_key(revenue_profile.monetization_strength),
        )

        strength = _compute_strength(decision, investment_profile.investment_score)

        rationale_codes = _compute_rationale_codes(
            market_profile, competition_profile, revenue_profile, investment_profile, weak_evidence_count
        )

        confidence = _compute_confidence(weak_evidence_count)

        return Recommendation(
            decision=decision,
            confidence=confidence,
            rationale="",
            recommendation_strength=strength,
            rationale_codes=rationale_codes,
        )
