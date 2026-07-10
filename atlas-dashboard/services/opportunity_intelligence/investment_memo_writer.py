"""
atlas/services/opportunity_intelligence/investment_memo_writer.py

AES-012H — Investment Memo Foundation.

The final stage of the Opportunity Intelligence pipeline: converts the
completed OpportunityAssessment + Recommendation into a concise,
deterministic memo. Consumes only the already-derived MarketProfile
(AES-012B), OpportunityClassification (AES-012C), CompetitionProfile
(AES-012D), RevenueProfile (AES-012E), InvestmentProfile (AES-012F),
and Recommendation (AES-012G) structured outputs — never re-runs any
analyst logic, never re-parses raw opportunity text except to display
the Opportunity's own name/description (already available, not
re-derived). No AI, no LLM calls, no web access, no external APIs, no
persistence, no global state, no randomness, and — critically for
determinism — no timestamps: `InvestmentMemo.generated_at` is left ""
by this writer (a real wall-clock timestamp would make an otherwise
identical input produce a different output on every run, which the
ticket explicitly forbids).

Honesty rule (same convention as every other real stage in this
package, extended to prose): a structured value of "UNKNOWN" is never
printed as literal text ("Category: UNKNOWN") in a summary — it is
simply omitted from that line. A documented, single rule, applied
uniformly by every _format_*_summary helper below: build a list of
only the recognized (non-"UNKNOWN", non-empty) fragments for a
section; if the list ends up empty, the section falls back to one
fixed, honest sentence ("... details are unknown.") rather than
guessing or fabricating anything.

Never displayed, by design (small, auditable, deliberate omissions —
not oversights):
  - CompetitionProfile.competitor_names / competitor_count: no named
    competitors, per the ticket's explicit constraint, even though a
    future/custom competition stage could theoretically populate them.
  - MarketProfile.total_addressable_market_usd,
    RevenueProfile.estimated_monthly_revenue_usd,
    InvestmentProfile.estimated_build_cost_usd/estimated_payback_months:
    no dollar figures or projections of any kind.
  - Recommendation.decision is displayed exactly as the committee
    produced it — this writer summarizes the decision, it never
    reinterprets or overrides it.

key_strengths / key_risks are derived from a small, closed,
alphabetically-sorted, duplicate-free (built via `set`) table of
stable codes — never prose, never invented categories.

Independent package: no Flask, no repositories, no persistence, no
services.opportunity_v2, no orchestrator, no Learning Memory, no
network I/O of any kind.
"""

from __future__ import annotations

from typing import List

from services.opportunity_intelligence.models import (
    CompetitionProfile,
    InvestmentMemo,
    InvestmentProfile,
    MarketProfile,
    Opportunity,
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


def _is_known(value: object) -> bool:
    token = _normalize_key(value)
    return token not in ("", UNKNOWN)


def _is_recognized_confidence(value: object) -> bool:
    return _is_known(value)


def _count_weak_evidence(
    market_profile: MarketProfile,
    classification: OpportunityClassification,
    competition_profile: CompetitionProfile,
    revenue_profile: RevenueProfile,
    investment_profile: InvestmentProfile,
) -> int:
    """
    Counts how many of the 5 upstream confidence signals are
    "UNKNOWN". Purely an observation of already-computed
    data_confidence/confidence fields (the same signals
    InvestmentCommittee already reduces to its own confidence value) —
    not a re-implementation of any analyst's scoring logic.
    """
    signals = (
        market_profile.data_confidence,
        classification.confidence,
        competition_profile.data_confidence,
        revenue_profile.data_confidence,
        investment_profile.data_confidence,
    )
    return sum(1 for signal in signals if not _is_recognized_confidence(signal))


def _join_or_fallback(fragments: List[str], fallback: str) -> str:
    known = [fragment for fragment in fragments if fragment]
    if not known:
        return fallback
    return " ".join(known)


# ---------------------------------------------------------------------------
# Section formatters — each reads only already-derived structured fields
# and applies the single UNKNOWN-omission rule documented above.
# ---------------------------------------------------------------------------


def _format_title(opportunity: Opportunity) -> str:
    name = (opportunity.name or "").strip()
    if not name:
        return "Investment Memo"
    return f"Investment Memo: {name}"


def _format_market_summary(market_profile: MarketProfile) -> str:
    fragments = []
    if _is_known(market_profile.primary_category):
        fragments.append(f"Category: {market_profile.primary_category}.")
    if _is_known(market_profile.primary_geography):
        fragments.append(f"Geography: {market_profile.primary_geography}.")
    if _is_known(market_profile.market_scope):
        fragments.append(f"Market scope: {market_profile.market_scope}.")
    return _join_or_fallback(fragments, "Market details are unknown.")


def _format_competition_summary(competition_profile: CompetitionProfile) -> str:
    fragments = []
    if _is_known(competition_profile.competitor_archetype):
        fragments.append(f"Competitor archetype: {competition_profile.competitor_archetype}.")
    if _is_known(competition_profile.market_fragmentation):
        fragments.append(f"Market fragmentation: {competition_profile.market_fragmentation}.")
    if _is_known(competition_profile.competitive_risk):
        fragments.append(f"Competitive risk: {competition_profile.competitive_risk}.")
    return _join_or_fallback(fragments, "Competition details are unknown.")


def _format_revenue_summary(revenue_profile: RevenueProfile) -> str:
    fragments = []
    if _is_known(revenue_profile.primary_revenue_model):
        fragments.append(f"Primary revenue model: {revenue_profile.primary_revenue_model}.")
    if revenue_profile.secondary_revenue_models:
        fragments.append(f"Secondary models: {', '.join(revenue_profile.secondary_revenue_models)}.")
    if _is_known(revenue_profile.monetization_strength):
        fragments.append(f"Monetization strength: {revenue_profile.monetization_strength}.")
    if _is_known(revenue_profile.revenue_scalability):
        fragments.append(f"Revenue scalability: {revenue_profile.revenue_scalability}.")
    return _join_or_fallback(fragments, "Revenue details are unknown.")


def _format_investment_summary(investment_profile: InvestmentProfile, recommendation: Recommendation) -> str:
    fragments = []
    if investment_profile.investment_score is not None:
        fragments.append(f"Investment score: {investment_profile.investment_score}/100.")
    if _is_known(investment_profile.investment_risk):
        fragments.append(f"Investment risk: {investment_profile.investment_risk}.")
    if _is_known(investment_profile.execution_complexity):
        fragments.append(f"Execution complexity: {investment_profile.execution_complexity}.")
    fragments.append(f"Committee decision: {recommendation.decision}.")
    return _join_or_fallback(fragments, f"Committee decision: {recommendation.decision}.")


def _format_executive_summary(
    opportunity: Opportunity,
    recommendation: Recommendation,
    key_strengths: List[str],
    key_risks: List[str],
) -> str:
    name = (opportunity.name or "this opportunity").strip() or "this opportunity"
    return (
        f"{name}: committee decision is {recommendation.decision} "
        f"(confidence {recommendation.confidence:.2f}). "
        f"{len(key_strengths)} key strength(s) and {len(key_risks)} key risk(s) identified."
    )


# ---------------------------------------------------------------------------
# Strengths / risks — small, closed, stable code tables.
# ---------------------------------------------------------------------------


def _compute_key_strengths(
    classification: OpportunityClassification,
    competition_profile: CompetitionProfile,
    revenue_profile: RevenueProfile,
    investment_profile: InvestmentProfile,
) -> List[str]:
    codes: set = set()

    if revenue_profile.monetization_strength == "STRONG":
        codes.add("STRONG_MONETIZATION")
    if revenue_profile.revenue_scalability == "HIGH":
        codes.add("HIGH_SCALABILITY")
    if competition_profile.competitive_risk == "LOW":
        codes.add("LOW_COMPETITIVE_RISK")
    if competition_profile.market_fragmentation == "HIGH":
        codes.add("FRAGMENTED_MARKET")
    if investment_profile.investment_score is not None and investment_profile.investment_score >= 70:
        codes.add("HIGH_INVESTMENT_SCORE")
    if classification.commercial_intent == "HIGH":
        codes.add("STRONG_COMMERCIAL_INTENT")

    return sorted(codes)


def _compute_key_risks(
    market_profile: MarketProfile,
    competition_profile: CompetitionProfile,
    revenue_profile: RevenueProfile,
    investment_profile: InvestmentProfile,
    weak_evidence_count: int,
) -> List[str]:
    codes: set = set()

    if revenue_profile.monetization_strength == "WEAK":
        codes.add("WEAK_MONETIZATION")
    if competition_profile.competitive_risk == "HIGH":
        codes.add("HIGH_COMPETITIVE_RISK")
    if investment_profile.execution_complexity == "HIGH":
        codes.add("HIGH_EXECUTION_COMPLEXITY")
    if revenue_profile.revenue_scalability == "LOW":
        codes.add("LOW_SCALABILITY")
    if weak_evidence_count >= 3:
        codes.add("LIMITED_EVIDENCE")
    if _normalize_key(market_profile.market_scope) == UNKNOWN:
        codes.add("UNKNOWN_MARKET")

    return sorted(codes)


class InvestmentMemoWriter:
    """
    Pure, deterministic, offline Investment Memo stage. Satisfies
    services.opportunity_intelligence.stages.InvestmentMemoStageProtocol
    structurally (run(Opportunity, OpportunityAssessment, Recommendation)
    -> InvestmentMemo) — no inheritance required. No global state, no
    singletons: every instance is independent and stateless. Never
    mutates its inputs. Never re-runs analyst logic, never reinterprets
    the committee's decision, never fabricates a financial figure.
    """

    def run(
        self,
        opportunity: Opportunity,
        assessment: OpportunityAssessment,
        recommendation: Recommendation,
    ) -> InvestmentMemo:
        market_profile = assessment.market_profile or MarketProfile()
        classification = assessment.classification or OpportunityClassification()
        competition_profile = assessment.competition_profile or CompetitionProfile()
        revenue_profile = assessment.revenue_profile or RevenueProfile()
        investment_profile = assessment.investment_profile or InvestmentProfile()

        weak_evidence_count = _count_weak_evidence(
            market_profile, classification, competition_profile, revenue_profile, investment_profile
        )

        key_strengths = _compute_key_strengths(
            classification, competition_profile, revenue_profile, investment_profile
        )
        key_risks = _compute_key_risks(
            market_profile, competition_profile, revenue_profile, investment_profile, weak_evidence_count
        )

        title = _format_title(opportunity)
        market_summary = _format_market_summary(market_profile)
        competition_summary = _format_competition_summary(competition_profile)
        revenue_summary = _format_revenue_summary(revenue_profile)
        investment_summary = _format_investment_summary(investment_profile, recommendation)
        executive_summary = _format_executive_summary(opportunity, recommendation, key_strengths, key_risks)

        return InvestmentMemo(
            opportunity=opportunity,
            assessment=assessment,
            recommendation=recommendation,
            summary=executive_summary,
            generated_at="",
            title=title,
            market_summary=market_summary,
            competition_summary=competition_summary,
            revenue_summary=revenue_summary,
            investment_summary=investment_summary,
            key_strengths=key_strengths,
            key_risks=key_risks,
        )
