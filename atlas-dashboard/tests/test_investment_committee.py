"""
atlas/tests/test_investment_committee.py

Unit tests for services/opportunity_intelligence/investment_committee.py
(AES-012G).

Covers each decision (INVEST/INVEST_WITH_CAUTION/HOLD/REJECT/UNKNOWN),
rationale-code generation (deterministic ordering, no duplicates),
confidence-as-evidence-quality behavior, unknown-evidence handling,
determinism, input immutability, and the guarantee that this stage
never generates prose or a memo.
"""

from __future__ import annotations

from services.opportunity_intelligence.investment_committee import InvestmentCommittee
from services.opportunity_intelligence.models import (
    CompetitionProfile,
    InvestmentProfile,
    MarketProfile,
    Opportunity,
    OpportunityAssessment,
    OpportunityClassification,
    Recommendation,
    RevenueProfile,
)
from services.opportunity_intelligence.opportunity_pipeline import OpportunityPipeline


def _opportunity() -> Opportunity:
    return Opportunity(opportunity_id="opp-1", name="Pet Trip Finder", niche="pet-friendly-travel")


def _assessment(
    market_profile: MarketProfile = None,
    classification: OpportunityClassification = None,
    competition_profile: CompetitionProfile = None,
    revenue_profile: RevenueProfile = None,
    investment_profile: InvestmentProfile = None,
) -> OpportunityAssessment:
    return OpportunityAssessment(
        opportunity=_opportunity(),
        market_profile=market_profile or MarketProfile(),
        classification=classification or OpportunityClassification(),
        competition_profile=competition_profile or CompetitionProfile(),
        revenue_profile=revenue_profile or RevenueProfile(),
        investment_profile=investment_profile or InvestmentProfile(),
    )


# ---------------------------------------------------------------------------
# Decision: INVEST
# ---------------------------------------------------------------------------


def test_strong_investment_profile_and_strong_monetization_and_low_risk_produces_invest():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED", market_scope="NATIONAL"),
        classification=OpportunityClassification(confidence="ESTIMATED", business_type="Directory"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="LOW"),
        revenue_profile=RevenueProfile(
            data_confidence="HIGH", monetization_strength="STRONG", revenue_scalability="HIGH"
        ),
        investment_profile=InvestmentProfile(data_confidence="HIGH", investment_score=85, investment_risk="LOW"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "INVEST"
    assert result.recommendation_strength == "STRONG"


def test_invest_also_accepted_with_moderate_investment_risk():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="HIGH", monetization_strength="STRONG"),
        investment_profile=InvestmentProfile(data_confidence="HIGH", investment_score=75, investment_risk="MODERATE"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "INVEST"


# ---------------------------------------------------------------------------
# Decision: INVEST_WITH_CAUTION
# ---------------------------------------------------------------------------


def test_moderate_score_and_non_high_risk_produces_invest_with_caution():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="MODERATE", monetization_strength="MODERATE"),
        investment_profile=InvestmentProfile(
            data_confidence="MODERATE", investment_score=60, investment_risk="MODERATE"
        ),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "INVEST_WITH_CAUTION"
    assert result.recommendation_strength == "MODERATE"


# ---------------------------------------------------------------------------
# Decision: HOLD
# ---------------------------------------------------------------------------


def test_missing_investment_score_produces_hold():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="MODERATE", monetization_strength="MODERATE"),
        investment_profile=InvestmentProfile(),  # investment_score is None
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "HOLD"
    assert result.recommendation_strength == "WEAK"


def test_unknown_investment_risk_produces_hold():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="MODERATE", monetization_strength="MODERATE"),
        investment_profile=InvestmentProfile(data_confidence="MODERATE", investment_score=60, investment_risk="UNKNOWN"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "HOLD"


def test_unknown_monetization_strength_produces_hold():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="MODERATE", monetization_strength="UNKNOWN"),
        investment_profile=InvestmentProfile(data_confidence="MODERATE", investment_score=60, investment_risk="MODERATE"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "HOLD"


# ---------------------------------------------------------------------------
# Decision: REJECT
# ---------------------------------------------------------------------------


def test_weak_monetization_and_high_risk_produces_reject():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="HIGH"),
        revenue_profile=RevenueProfile(data_confidence="LOW", monetization_strength="WEAK", revenue_scalability="LOW"),
        investment_profile=InvestmentProfile(data_confidence="MODERATE", investment_score=20, investment_risk="HIGH"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "REJECT"


def test_low_score_catch_all_produces_reject():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="LOW", monetization_strength="MODERATE"),
        investment_profile=InvestmentProfile(data_confidence="LOW", investment_score=20, investment_risk="MODERATE"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "REJECT"
    assert result.recommendation_strength == "WEAK"


def test_weak_monetization_and_high_risk_dominates_even_with_high_score():
    """
    R2 (weak monetization + high risk -> REJECT) runs before R3 (score
    threshold -> INVEST), so a technically-high score cannot override
    a conservative reject signal — no single field dominates.
    """
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="HIGH"),
        revenue_profile=RevenueProfile(data_confidence="LOW", monetization_strength="WEAK"),
        investment_profile=InvestmentProfile(data_confidence="HIGH", investment_score=90, investment_risk="HIGH"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "REJECT"


# ---------------------------------------------------------------------------
# Decision: UNKNOWN
# ---------------------------------------------------------------------------


def test_completely_unknown_evidence_produces_unknown_decision():
    assessment = _assessment()

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "UNKNOWN"
    assert result.recommendation_strength == "UNKNOWN"
    assert result.confidence == 0.0


def test_low_confidence_across_multiple_analysts_produces_unknown_even_with_a_good_score():
    """
    R1 (weak_evidence_count >= 3 -> UNKNOWN) runs first — a
    technically-favorable investment_score cannot override
    insufficient evidence across the majority of upstream analysts.
    """
    assessment = _assessment(
        market_profile=MarketProfile(),  # UNKNOWN
        classification=OpportunityClassification(),  # UNKNOWN
        competition_profile=CompetitionProfile(),  # UNKNOWN
        revenue_profile=RevenueProfile(data_confidence="HIGH", monetization_strength="STRONG"),
        investment_profile=InvestmentProfile(data_confidence="HIGH", investment_score=90, investment_risk="LOW"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "UNKNOWN"


def test_none_profiles_on_assessment_do_not_crash():
    assessment = OpportunityAssessment(opportunity=_opportunity())  # all Optional profiles are None

    result = InvestmentCommittee().run(assessment)

    assert result.decision == "UNKNOWN"


# ---------------------------------------------------------------------------
# Rationale codes: generation, ordering, no duplicates
# ---------------------------------------------------------------------------


def test_rationale_codes_reflect_recognized_signals():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED", market_scope="NATIONAL"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="LOW"),
        revenue_profile=RevenueProfile(
            data_confidence="HIGH", monetization_strength="STRONG", revenue_scalability="HIGH"
        ),
        investment_profile=InvestmentProfile(data_confidence="HIGH", investment_score=85, investment_risk="LOW"),
    )

    result = InvestmentCommittee().run(assessment)

    assert "HIGH_MONETIZATION" in result.rationale_codes
    assert "LOW_COMPETITIVE_RISK" in result.rationale_codes
    assert "HIGH_SCALABILITY" in result.rationale_codes
    assert "UNKNOWN_MARKET" not in result.rationale_codes


def test_rationale_codes_include_unknown_market_when_scope_unrecognized():
    assessment = _assessment(market_profile=MarketProfile(market_scope="UNKNOWN"))

    result = InvestmentCommittee().run(assessment)

    assert "UNKNOWN_MARKET" in result.rationale_codes


def test_rationale_codes_include_limited_evidence_when_evidence_sparse():
    assessment = _assessment()  # every profile default/UNKNOWN

    result = InvestmentCommittee().run(assessment)

    assert "LIMITED_EVIDENCE" in result.rationale_codes


def test_rationale_codes_are_sorted_deterministically():
    assessment = _assessment(
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="HIGH"),
        revenue_profile=RevenueProfile(data_confidence="LOW", monetization_strength="WEAK", revenue_scalability="LOW"),
        investment_profile=InvestmentProfile(data_confidence="LOW", execution_complexity="HIGH"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.rationale_codes == sorted(result.rationale_codes)


def test_rationale_codes_contain_no_duplicates():
    assessment = _assessment(
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="HIGH"),
        revenue_profile=RevenueProfile(data_confidence="LOW", monetization_strength="WEAK", revenue_scalability="LOW"),
        investment_profile=InvestmentProfile(data_confidence="LOW", execution_complexity="HIGH"),
    )

    result = InvestmentCommittee().run(assessment)

    assert len(result.rationale_codes) == len(set(result.rationale_codes))


# ---------------------------------------------------------------------------
# Confidence: evidence quality
# ---------------------------------------------------------------------------


def test_confidence_reflects_fraction_of_recognized_signals():
    fully_recognized = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="HIGH"),
        investment_profile=InvestmentProfile(data_confidence="HIGH"),
    )
    partially_recognized = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
    )

    fully_result = InvestmentCommittee().run(fully_recognized)
    partial_result = InvestmentCommittee().run(partially_recognized)

    assert fully_result.confidence == 1.0
    assert partial_result.confidence < fully_result.confidence


def test_confidence_never_verified():
    assessment = _assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED"),
        revenue_profile=RevenueProfile(data_confidence="HIGH", monetization_strength="STRONG"),
        investment_profile=InvestmentProfile(data_confidence="HIGH", investment_score=90, investment_risk="LOW"),
    )

    result = InvestmentCommittee().run(assessment)

    assert not isinstance(result.confidence, str)
    assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# No prose, no memo
# ---------------------------------------------------------------------------


def test_never_generates_prose_rationale():
    assessment = _assessment(
        revenue_profile=RevenueProfile(monetization_strength="STRONG"),
        investment_profile=InvestmentProfile(investment_score=90, investment_risk="LOW"),
    )

    result = InvestmentCommittee().run(assessment)

    assert result.rationale == ""


# ---------------------------------------------------------------------------
# Determinism, immutability, typed contract
# ---------------------------------------------------------------------------


def test_repeated_calls_with_identical_inputs_return_identical_results():
    assessment = _assessment(
        revenue_profile=RevenueProfile(monetization_strength="STRONG", revenue_scalability="HIGH"),
        investment_profile=InvestmentProfile(investment_score=80, investment_risk="LOW"),
    )
    committee = InvestmentCommittee()

    result_a = committee.run(assessment)
    result_b = committee.run(assessment)

    assert result_a == result_b


def test_input_assessment_is_not_mutated():
    assessment = _assessment(
        revenue_profile=RevenueProfile(monetization_strength="STRONG"),
        investment_profile=InvestmentProfile(investment_score=80, investment_risk="LOW"),
    )
    assessment_copy = assessment.copy(deep=True)

    InvestmentCommittee().run(assessment)

    assert assessment == assessment_copy


def test_run_returns_recommendation_instance():
    result = InvestmentCommittee().run(_assessment())

    assert isinstance(result, Recommendation)


def test_committee_has_no_mutable_shared_state_between_instances():
    first = InvestmentCommittee()
    first.run(_assessment(
        revenue_profile=RevenueProfile(monetization_strength="STRONG"),
        investment_profile=InvestmentProfile(investment_score=90, investment_risk="LOW"),
    ))

    second = InvestmentCommittee()
    result = second.run(_assessment(
        market_profile=MarketProfile(data_confidence="ESTIMATED"),
        classification=OpportunityClassification(confidence="ESTIMATED"),
        competition_profile=CompetitionProfile(data_confidence="ESTIMATED", competitive_risk="HIGH"),
        revenue_profile=RevenueProfile(data_confidence="LOW", monetization_strength="WEAK"),
        investment_profile=InvestmentProfile(data_confidence="LOW", investment_score=10, investment_risk="HIGH"),
    ))

    assert result.decision == "REJECT"


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


def test_pipeline_default_committee_stage_is_the_real_committee():
    pipeline = OpportunityPipeline()
    opportunity = Opportunity(opportunity_id="opp-committee", name="Ohio Martial Arts for Kids", niche="martial arts")

    memo = pipeline.run(opportunity)

    assert memo.recommendation.decision != "UNASSESSED"
    assert memo.recommendation.decision in ("INVEST", "INVEST_WITH_CAUTION", "HOLD", "REJECT", "UNKNOWN")


def test_pipeline_accepts_custom_committee_stage_implementation():
    class _FixedCommitteeRecommendationStage:
        def run(self, assessment):
            return Recommendation(decision="INVEST", confidence=1.0, recommendation_strength="STRONG")

    pipeline = OpportunityPipeline(committee_recommendation_stage=_FixedCommitteeRecommendationStage())

    memo = pipeline.run(_opportunity())

    assert memo.recommendation.decision == "INVEST"


def test_pipeline_stage_order_unchanged_with_real_committee():
    pipeline = OpportunityPipeline()

    memo = pipeline.run(_opportunity())

    assert memo.assessment.investment_profile is not None
    assert memo.recommendation is not None
