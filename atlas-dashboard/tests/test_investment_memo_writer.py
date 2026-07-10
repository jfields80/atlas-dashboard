"""
atlas/tests/test_investment_memo_writer.py

Unit tests for services/opportunity_intelligence/investment_memo_writer.py
(AES-012H).

Covers memo generation for each committee decision, each section
summary (including the UNKNOWN-omission fallback rule), deterministic
strengths/risks (sorted, duplicate-free), the no-named-competitors /
no-dollar-figures / no-timestamp constraints, determinism, input
immutability, and pipeline integration.
"""

from __future__ import annotations

from services.opportunity_intelligence.competition_analyst import CompetitionAnalyst
from services.opportunity_intelligence.investment_analyst import InvestmentAnalyst
from services.opportunity_intelligence.investment_committee import InvestmentCommittee
from services.opportunity_intelligence.investment_memo_writer import InvestmentMemoWriter
from services.opportunity_intelligence.market_research_analyst import MarketResearchAnalyst
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
)
from services.opportunity_intelligence.opportunity_classifier import OpportunityClassifier
from services.opportunity_intelligence.opportunity_pipeline import OpportunityPipeline
from services.opportunity_intelligence.revenue_analyst import RevenueAnalyst


def _opportunity(name: str = "Pet Trip Finder") -> Opportunity:
    return Opportunity(opportunity_id="opp-1", name=name, niche="pet-friendly-travel")


def _assessment(
    opportunity: Opportunity = None,
    market_profile: MarketProfile = None,
    classification: OpportunityClassification = None,
    competition_profile: CompetitionProfile = None,
    revenue_profile: RevenueProfile = None,
    investment_profile: InvestmentProfile = None,
) -> OpportunityAssessment:
    return OpportunityAssessment(
        opportunity=opportunity or _opportunity(),
        market_profile=market_profile or MarketProfile(),
        classification=classification or OpportunityClassification(),
        competition_profile=competition_profile or CompetitionProfile(),
        revenue_profile=revenue_profile or RevenueProfile(),
        investment_profile=investment_profile or InvestmentProfile(),
    )


def _derived_chain(name: str, niche: str = ""):
    """Full real upstream chain through Recommendation."""
    opportunity = Opportunity(opportunity_id="opp-derived", name=name, niche=niche)
    market_profile = MarketResearchAnalyst().run(opportunity)
    classification = OpportunityClassifier().run(opportunity, market_profile)
    competition_profile = CompetitionAnalyst().run(opportunity, market_profile, classification)
    revenue_profile = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)
    investment_profile = InvestmentAnalyst().run(
        opportunity, market_profile, classification, competition_profile, revenue_profile
    )
    assessment = _assessment(
        opportunity, market_profile, classification, competition_profile, revenue_profile, investment_profile
    )
    recommendation = InvestmentCommittee().run(assessment)
    return opportunity, assessment, recommendation


# ---------------------------------------------------------------------------
# One decision per committee value
# ---------------------------------------------------------------------------


def test_invest_memo():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="LOW"),
        revenue_profile=RevenueProfile(
            data_confidence="HIGH", monetization_strength="STRONG", revenue_scalability="HIGH"
        ),
        investment_profile=InvestmentProfile(data_confidence="HIGH", investment_score=85, investment_risk="LOW"),
    )
    recommendation = InvestmentCommittee().run(assessment)

    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, recommendation)

    assert recommendation.decision == "INVEST"
    assert "INVEST" in memo.investment_summary
    assert "Committee decision is INVEST" in memo.summary or "committee decision is INVEST" in memo.summary


def test_invest_with_caution_memo_via_full_derived_chain():
    opportunity, assessment, recommendation = _derived_chain("Ohio Martial Arts for Kids", "martial arts")

    memo = InvestmentMemoWriter().run(opportunity, assessment, recommendation)

    assert recommendation.decision == "INVEST_WITH_CAUTION"
    assert memo.title == "Investment Memo: Ohio Martial Arts for Kids"
    assert "INVEST_WITH_CAUTION" in memo.investment_summary
    assert "FRAGMENTED_MARKET" in memo.key_strengths
    assert "HIGH_INVESTMENT_SCORE" in memo.key_strengths
    assert "STRONG_COMMERCIAL_INTENT" in memo.key_strengths


def test_hold_memo():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="MODERATE", monetization_strength="MODERATE"),
        investment_profile=InvestmentProfile(),  # investment_score None -> HOLD
    )
    recommendation = InvestmentCommittee().run(assessment)

    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, recommendation)

    assert recommendation.decision == "HOLD"
    assert "HOLD" in memo.investment_summary


def test_reject_memo():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="HIGH"),
        revenue_profile=RevenueProfile(data_confidence="LOW", monetization_strength="WEAK", revenue_scalability="LOW"),
        investment_profile=InvestmentProfile(data_confidence="MODERATE", investment_score=20, investment_risk="HIGH"),
    )
    recommendation = InvestmentCommittee().run(assessment)

    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, recommendation)

    assert recommendation.decision == "REJECT"
    assert "REJECT" in memo.investment_summary
    assert "WEAK_MONETIZATION" in memo.key_risks
    assert "HIGH_COMPETITIVE_RISK" in memo.key_risks


def test_unknown_memo():
    assessment = _assessment()  # everything default/UNKNOWN
    recommendation = InvestmentCommittee().run(assessment)

    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, recommendation)

    assert recommendation.decision == "UNKNOWN"
    assert "UNKNOWN" in memo.investment_summary
    assert "LIMITED_EVIDENCE" in memo.key_risks


# ---------------------------------------------------------------------------
# Section summaries
# ---------------------------------------------------------------------------


def test_market_summary_includes_known_fields():
    assessment = _assessment(
        market_profile=MarketProfile(primary_category="HVAC", primary_geography="Ohio", market_scope="STATE")
    )
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert "HVAC" in memo.market_summary
    assert "Ohio" in memo.market_summary
    assert "STATE" in memo.market_summary


def test_market_summary_falls_back_when_fully_unknown():
    assessment = _assessment(market_profile=MarketProfile())
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert memo.market_summary == "Market details are unknown."
    assert "UNKNOWN" not in memo.market_summary


def test_competition_summary_includes_known_fields():
    assessment = _assessment(
        competition_profile=CompetitionProfile(
            competitor_archetype="national_platforms", market_fragmentation="MODERATE", competitive_risk="HIGH"
        )
    )
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert "national_platforms" in memo.competition_summary
    assert "HIGH" in memo.competition_summary


def test_competition_summary_falls_back_when_fully_unknown():
    assessment = _assessment(competition_profile=CompetitionProfile())
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert memo.competition_summary == "Competition details are unknown."


def test_revenue_summary_includes_known_fields():
    assessment = _assessment(
        revenue_profile=RevenueProfile(
            primary_revenue_model="SUBSCRIPTIONS",
            secondary_revenue_models=["LICENSING", "USAGE_FEES"],
            monetization_strength="STRONG",
            revenue_scalability="HIGH",
        )
    )
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert "SUBSCRIPTIONS" in memo.revenue_summary
    assert "LICENSING" in memo.revenue_summary
    assert "STRONG" in memo.revenue_summary


def test_revenue_summary_falls_back_when_fully_unknown():
    assessment = _assessment(revenue_profile=RevenueProfile())
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert memo.revenue_summary == "Revenue details are unknown."


def test_investment_summary_displays_score_and_decision():
    assessment = _assessment(investment_profile=InvestmentProfile(investment_score=77, investment_risk="MODERATE"))
    recommendation = Recommendation(decision="INVEST_WITH_CAUTION")

    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, recommendation)

    assert "77/100" in memo.investment_summary
    assert "INVEST_WITH_CAUTION" in memo.investment_summary


def test_investment_summary_still_shows_decision_when_score_unknown():
    assessment = _assessment(investment_profile=InvestmentProfile())
    recommendation = Recommendation(decision="HOLD")

    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, recommendation)

    assert "HOLD" in memo.investment_summary
    assert "/100" not in memo.investment_summary


# ---------------------------------------------------------------------------
# Strengths / risks: determinism, ordering, no duplicates
# ---------------------------------------------------------------------------


def test_key_strengths_sorted_and_no_duplicates():
    opportunity, assessment, recommendation = _derived_chain("Ohio Martial Arts for Kids", "martial arts")

    memo = InvestmentMemoWriter().run(opportunity, assessment, recommendation)

    assert memo.key_strengths == sorted(memo.key_strengths)
    assert len(memo.key_strengths) == len(set(memo.key_strengths))


def test_key_risks_sorted_and_no_duplicates():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED", market_scope="NATIONAL"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="HIGH"),
        revenue_profile=RevenueProfile(
            data_confidence="LOW", monetization_strength="WEAK", revenue_scalability="LOW"
        ),
        investment_profile=InvestmentProfile(data_confidence="LOW", execution_complexity="HIGH"),
    )
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert memo.key_risks == sorted(memo.key_risks)
    assert len(memo.key_risks) == len(set(memo.key_risks))
    assert memo.key_risks == [
        "HIGH_COMPETITIVE_RISK",
        "HIGH_EXECUTION_COMPLEXITY",
        "LOW_SCALABILITY",
        "WEAK_MONETIZATION",
    ]


def test_key_risks_include_limited_evidence_and_unknown_market_when_sparse():
    assessment = _assessment()  # everything default/UNKNOWN
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert "LIMITED_EVIDENCE" in memo.key_risks
    assert "UNKNOWN_MARKET" in memo.key_risks


# ---------------------------------------------------------------------------
# Honesty / constraints
# ---------------------------------------------------------------------------


def test_unknown_values_are_omitted_not_printed_literally():
    assessment = _assessment(
        market_profile=MarketProfile(primary_category="HVAC"),  # geography/scope stay UNKNOWN
    )
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert "UNKNOWN" not in memo.market_summary
    assert "HVAC" in memo.market_summary


def test_no_named_competitors_in_any_summary():
    assessment = _assessment(
        competition_profile=CompetitionProfile(
            competitor_names=["Rival Co", "Other Rival LLC"], competitor_count=2
        )
    )
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert "Rival Co" not in memo.competition_summary
    assert "Other Rival LLC" not in memo.competition_summary
    assert "Rival Co" not in memo.summary


def test_no_dollar_figures_or_projections_in_any_summary():
    assessment = _assessment(
        market_profile=MarketProfile(total_addressable_market_usd=5_000_000.0),
        revenue_profile=RevenueProfile(estimated_monthly_revenue_usd=10_000.0),
        investment_profile=InvestmentProfile(
            estimated_build_cost_usd=50_000.0, estimated_payback_months=6.0, investment_score=80
        ),
    )
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    all_text = " ".join(
        [memo.summary, memo.market_summary, memo.competition_summary, memo.revenue_summary, memo.investment_summary]
    )
    assert "5000000" not in all_text.replace(",", "").replace(".0", "")
    assert "$" not in all_text
    assert "50000" not in all_text.replace(",", "")


def test_generated_at_is_never_a_timestamp():
    assessment = _assessment()
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert memo.generated_at == ""


def test_decision_displayed_exactly_not_reinterpreted():
    for decision in ("INVEST", "INVEST_WITH_CAUTION", "HOLD", "REJECT", "UNKNOWN"):
        assessment = _assessment()
        recommendation = Recommendation(decision=decision)

        memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, recommendation)

        assert decision in memo.investment_summary
        assert decision in memo.summary


# ---------------------------------------------------------------------------
# Determinism, immutability, defensive normalization
# ---------------------------------------------------------------------------


def test_repeated_calls_with_identical_inputs_return_identical_output():
    opportunity, assessment, recommendation = _derived_chain("Ohio Martial Arts for Kids", "martial arts")
    writer = InvestmentMemoWriter()

    memo_a = writer.run(opportunity, assessment, recommendation)
    memo_b = writer.run(opportunity, assessment, recommendation)

    assert memo_a == memo_b


def test_inputs_are_not_mutated():
    opportunity, assessment, recommendation = _derived_chain("Ohio Martial Arts for Kids", "martial arts")
    assessment_copy = assessment.copy(deep=True)
    recommendation_copy = recommendation.copy(deep=True)

    InvestmentMemoWriter().run(opportunity, assessment, recommendation)

    assert assessment == assessment_copy
    assert recommendation == recommendation_copy


def test_unsupported_future_values_do_not_crash():
    assessment = _assessment(
        market_profile=MarketProfile(market_scope="PLANETARY"),
        competition_profile=CompetitionProfile(competitive_risk="CATASTROPHIC"),
        revenue_profile=RevenueProfile(monetization_strength="ULTRA"),
        investment_profile=InvestmentProfile(execution_complexity="EXTREME"),
    )
    recommendation = Recommendation(decision="SOMETHING_NEW")

    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, recommendation)

    assert isinstance(memo, InvestmentMemo)


def test_run_returns_investment_memo_instance():
    assessment = _assessment()
    memo = InvestmentMemoWriter().run(assessment.opportunity, assessment, Recommendation())

    assert isinstance(memo, InvestmentMemo)


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


def test_pipeline_default_memo_stage_is_the_real_writer():
    pipeline = OpportunityPipeline()
    opportunity = Opportunity(opportunity_id="opp-9", name="Ohio Martial Arts for Kids", niche="martial arts")

    memo = pipeline.run(opportunity)

    assert memo.title == "Investment Memo: Ohio Martial Arts for Kids"
    assert memo.generated_at == ""
    assert "Placeholder" not in memo.summary


def test_pipeline_accepts_custom_memo_stage_implementation():
    class _FixedInvestmentMemoStage:
        def run(self, opportunity, assessment, recommendation):
            return InvestmentMemo(
                opportunity=opportunity, assessment=assessment, recommendation=recommendation, title="Custom"
            )

    pipeline = OpportunityPipeline(investment_memo_stage=_FixedInvestmentMemoStage())

    memo = pipeline.run(_opportunity())

    assert memo.title == "Custom"


def test_pipeline_stage_order_unchanged_through_memo():
    pipeline = OpportunityPipeline()

    memo = pipeline.run(_opportunity())

    assert memo.assessment.market_profile is not None
    assert memo.assessment.investment_profile is not None
    assert memo.recommendation is not None
    assert memo.title != ""
