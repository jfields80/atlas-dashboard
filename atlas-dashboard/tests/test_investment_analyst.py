"""
atlas/tests/test_investment_analyst.py

Unit tests for services/opportunity_intelligence/investment_analyst.py
(AES-012F).

Covers market/revenue/competitive/execution characterization,
investment_score bounds and point rules, confidence-as-evidence-
quality behavior, determinism, input immutability, defensive
normalization of unsupported future values, and the guarantee that no
final INVEST/REJECT recommendation or financial projection is ever
emitted by this stage.
"""

from __future__ import annotations

from services.opportunity_intelligence.competition_analyst import CompetitionAnalyst
from services.opportunity_intelligence.investment_analyst import InvestmentAnalyst
from services.opportunity_intelligence.market_research_analyst import MarketResearchAnalyst
from services.opportunity_intelligence.models import (
    CompetitionProfile,
    InvestmentProfile,
    MarketProfile,
    Opportunity,
    OpportunityClassification,
    RevenueProfile,
)
from services.opportunity_intelligence.opportunity_classifier import OpportunityClassifier
from services.opportunity_intelligence.revenue_analyst import RevenueAnalyst


def _opportunity(name: str = "Pet Trip Finder", niche: str = "") -> Opportunity:
    return Opportunity(opportunity_id="opp-1", name=name, niche=niche)


def _derived(name: str, niche: str = ""):
    """Full real upstream chain through RevenueProfile."""
    opportunity = _opportunity(name, niche)
    market_profile = MarketResearchAnalyst().run(opportunity)
    classification = OpportunityClassifier().run(opportunity, market_profile)
    competition_profile = CompetitionAnalyst().run(opportunity, market_profile, classification)
    revenue_profile = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)
    return opportunity, market_profile, classification, competition_profile, revenue_profile


# ---------------------------------------------------------------------------
# Full derived worked example
# ---------------------------------------------------------------------------


def test_ohio_martial_arts_for_kids_full_derived_example():
    opportunity, market_profile, classification, competition_profile, revenue_profile = _derived(
        "Ohio Martial Arts for Kids"
    )
    assert market_profile.market_scope == "STATE"
    assert classification.business_type == "Directory"
    assert competition_profile.competitive_risk == "MODERATE"
    assert competition_profile.market_fragmentation == "HIGH"

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.market_attractiveness == "MODERATE"
    assert result.revenue_attractiveness == "HIGH"
    assert result.competitive_position == "HIGH"  # MODERATE risk inverted, bumped by fragmentation
    assert result.execution_complexity == "LOW"
    assert result.investment_risk == "MODERATE"
    assert result.investment_score == 87
    assert result.data_confidence == "HIGH"


# ---------------------------------------------------------------------------
# Strong revenue profile / weak monetization
# ---------------------------------------------------------------------------


def test_strong_revenue_profile_improves_revenue_attractiveness():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile(monetization_strength="STRONG", revenue_scalability="HIGH")

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.revenue_attractiveness == "HIGH"


def test_weak_monetization_produces_low_revenue_attractiveness():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile(monetization_strength="WEAK", revenue_scalability="LOW")

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.revenue_attractiveness == "LOW"


# ---------------------------------------------------------------------------
# Competitive risk / fragmentation
# ---------------------------------------------------------------------------


def test_high_competitive_risk_weakens_competitive_position():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile(competitive_risk="HIGH")
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.competitive_position == "LOW"


def test_fragmented_competition_improves_accessibility():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    revenue_profile = RevenueProfile()

    fragmented = CompetitionProfile(competitive_risk="HIGH", market_fragmentation="HIGH")
    not_fragmented = CompetitionProfile(competitive_risk="HIGH", market_fragmentation="MODERATE")

    fragmented_result = InvestmentAnalyst().run(opportunity, market_profile, classification, fragmented, revenue_profile)
    baseline_result = InvestmentAnalyst().run(opportunity, market_profile, classification, not_fragmented, revenue_profile)

    assert fragmented_result.competitive_position == "MODERATE"
    assert baseline_result.competitive_position == "LOW"


def test_competitive_position_never_bumped_past_high():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile(competitive_risk="LOW", market_fragmentation="HIGH")
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.competitive_position == "HIGH"


# ---------------------------------------------------------------------------
# Scalability impact
# ---------------------------------------------------------------------------


def test_scalability_alone_influences_revenue_attractiveness():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile()

    high_scale = RevenueProfile(revenue_scalability="HIGH")
    low_scale = RevenueProfile(revenue_scalability="LOW")

    high_result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, high_scale)
    low_result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, low_scale)

    order = ("UNKNOWN", "LOW", "MODERATE", "HIGH")
    assert order.index(high_result.revenue_attractiveness) > order.index(low_result.revenue_attractiveness)


# ---------------------------------------------------------------------------
# Execution complexity by business type
# ---------------------------------------------------------------------------


def test_marketplace_has_high_execution_complexity():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Marketplace")
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.execution_complexity == "HIGH"


def test_directory_has_low_execution_complexity():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Directory")
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.execution_complexity == "LOW"


def test_saas_has_moderate_execution_complexity():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="SaaS")
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.execution_complexity == "MODERATE"


def test_service_provider_has_higher_operational_complexity():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Service Provider")
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.execution_complexity == "HIGH"


def test_execution_complexity_lookup_is_case_and_whitespace_insensitive():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="  directory  ")
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.execution_complexity == "LOW"


# ---------------------------------------------------------------------------
# UNKNOWN handling never fabricates / never treats UNKNOWN as negative
# ---------------------------------------------------------------------------


def test_completely_unknown_inputs_return_valid_all_unknown_profile():
    result = InvestmentAnalyst().run(
        _opportunity(), MarketProfile(), OpportunityClassification(), CompetitionProfile(), RevenueProfile()
    )

    assert isinstance(result, InvestmentProfile)
    assert result.market_attractiveness == "UNKNOWN"
    assert result.revenue_attractiveness == "UNKNOWN"
    assert result.competitive_position == "UNKNOWN"
    assert result.execution_complexity == "UNKNOWN"
    assert result.investment_risk == "UNKNOWN"
    assert result.investment_score is None
    assert result.data_confidence == "UNKNOWN"


def test_unknown_signal_does_not_lower_a_known_sibling_signal():
    """
    revenue_attractiveness combines monetization_strength and
    revenue_scalability — an UNKNOWN monetization_strength must not
    drag a real HIGH revenue_scalability down toward LOW.
    """
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile(monetization_strength="UNKNOWN", revenue_scalability="HIGH")

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.revenue_attractiveness == "HIGH"


def test_unsupported_future_business_type_does_not_crash():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Some Future Vertical")
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert isinstance(result, InvestmentProfile)
    assert result.execution_complexity == "UNKNOWN"


def test_unsupported_future_market_scope_does_not_crash():
    opportunity = _opportunity()
    market_profile = MarketProfile(market_scope="PLANETARY")
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile()
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.market_attractiveness == "UNKNOWN"


def test_unsupported_future_competitive_risk_value_does_not_crash():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile(competitive_risk="CATASTROPHIC")
    revenue_profile = RevenueProfile()

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.competitive_position == "UNKNOWN"


# ---------------------------------------------------------------------------
# Bounded investment_score
# ---------------------------------------------------------------------------


def test_investment_score_is_bounded_between_zero_and_hundred():
    for name in ("Ohio Martial Arts for Kids", "Direct Beef", "Columbus Dog Groomers", "Reliable HVAC Services"):
        opportunity, market_profile, classification, competition_profile, revenue_profile = _derived(name)
        result = InvestmentAnalyst().run(
            opportunity, market_profile, classification, competition_profile, revenue_profile
        )
        if result.investment_score is not None:
            assert 0 <= result.investment_score <= 100


def test_investment_score_is_maximal_for_all_high_signals():
    opportunity = _opportunity()
    market_profile = MarketProfile(market_scope="NATIONAL")
    classification = OpportunityClassification(business_type="Directory")
    competition_profile = CompetitionProfile(competitive_risk="LOW")
    revenue_profile = RevenueProfile(monetization_strength="STRONG", revenue_scalability="HIGH")

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    # market=HIGH(25) + revenue=HIGH(30) + competitive_position=HIGH(25) + execution=LOW(20) = 100
    assert result.investment_score == 100


def test_investment_score_none_when_nothing_recognized():
    result = InvestmentAnalyst().run(
        _opportunity(), MarketProfile(), OpportunityClassification(), CompetitionProfile(), RevenueProfile()
    )

    assert result.investment_score is None


# ---------------------------------------------------------------------------
# Confidence reflects evidence quality, not attractiveness
# ---------------------------------------------------------------------------


def test_confidence_increases_with_additional_recognized_signals():
    opportunity = _opportunity()
    revenue_profile = RevenueProfile()

    one_signal = InvestmentAnalyst().run(
        opportunity, MarketProfile(market_scope="NATIONAL"), OpportunityClassification(), CompetitionProfile(), revenue_profile
    )
    two_signals = InvestmentAnalyst().run(
        opportunity,
        MarketProfile(market_scope="NATIONAL"),
        OpportunityClassification(business_type="Directory"),
        CompetitionProfile(),
        revenue_profile,
    )

    order = ("UNKNOWN", "LOW", "MODERATE", "HIGH")
    assert order.index(two_signals.data_confidence) > order.index(one_signal.data_confidence)


def test_confidence_reflects_evidence_not_attractiveness():
    """
    A fully-recognized but unattractive profile (LOW everywhere) must
    report the same HIGH confidence as a fully-recognized attractive
    one — confidence is about how much evidence exists, not how good
    it looks.
    """
    opportunity = _opportunity()
    unattractive = InvestmentAnalyst().run(
        opportunity,
        MarketProfile(market_scope="CITY"),
        OpportunityClassification(business_type="Service Provider"),
        CompetitionProfile(competitive_risk="HIGH"),
        RevenueProfile(monetization_strength="WEAK", revenue_scalability="LOW"),
    )
    attractive = InvestmentAnalyst().run(
        opportunity,
        MarketProfile(market_scope="NATIONAL"),
        OpportunityClassification(business_type="Directory"),
        CompetitionProfile(competitive_risk="LOW"),
        RevenueProfile(monetization_strength="STRONG", revenue_scalability="HIGH"),
    )

    assert unattractive.data_confidence == attractive.data_confidence == "HIGH"


def test_confidence_never_verified():
    for name in ("Ohio Martial Arts for Kids", "Direct Beef", "Columbus Dog Groomers", "Xyzzy Widgets"):
        opportunity, market_profile, classification, competition_profile, revenue_profile = _derived(name)
        result = InvestmentAnalyst().run(
            opportunity, market_profile, classification, competition_profile, revenue_profile
        )
        assert result.data_confidence != "VERIFIED"


# ---------------------------------------------------------------------------
# No mutation, determinism, typed contract
# ---------------------------------------------------------------------------


def test_inputs_are_not_mutated():
    opportunity = _opportunity()
    market_profile = MarketProfile(market_scope="NATIONAL")
    classification = OpportunityClassification(business_type="Directory")
    competition_profile = CompetitionProfile(competitive_risk="HIGH")
    revenue_profile = RevenueProfile(monetization_strength="STRONG")

    market_profile_copy = market_profile.copy(deep=True)
    classification_copy = classification.copy(deep=True)
    competition_profile_copy = competition_profile.copy(deep=True)
    revenue_profile_copy = revenue_profile.copy(deep=True)

    InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert market_profile == market_profile_copy
    assert classification == classification_copy
    assert competition_profile == competition_profile_copy
    assert revenue_profile == revenue_profile_copy


def test_repeated_calls_with_identical_inputs_return_identical_results():
    opportunity, market_profile, classification, competition_profile, revenue_profile = _derived(
        "Ohio Martial Arts for Kids"
    )
    analyst = InvestmentAnalyst()

    result_a = analyst.run(opportunity, market_profile, classification, competition_profile, revenue_profile)
    result_b = analyst.run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result_a == result_b


def test_run_returns_investment_profile_instance():
    result = InvestmentAnalyst().run(
        _opportunity(), MarketProfile(), OpportunityClassification(), CompetitionProfile(), RevenueProfile()
    )

    assert isinstance(result, InvestmentProfile)


def test_analyst_has_no_mutable_shared_state_between_instances():
    first = InvestmentAnalyst()
    o1, mp1, c1, cp1, rp1 = _derived("Ohio Martial Arts for Kids")
    first.run(o1, mp1, c1, cp1, rp1)

    second = InvestmentAnalyst()
    result = second.run(
        _opportunity("Widget Shop"),
        MarketProfile(),
        OpportunityClassification(business_type="Marketplace"),
        CompetitionProfile(),
        RevenueProfile(),
    )

    assert result.execution_complexity == "HIGH"


# ---------------------------------------------------------------------------
# No committee recommendation, no financial projections
# ---------------------------------------------------------------------------


def test_no_committee_recommendation_emitted():
    opportunity, market_profile, classification, competition_profile, revenue_profile = _derived(
        "Ohio Martial Arts for Kids"
    )

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert not hasattr(result, "decision")
    assert not hasattr(result, "recommendation")


def test_never_populates_financial_projections():
    opportunity, market_profile, classification, competition_profile, revenue_profile = _derived(
        "Ohio Martial Arts for Kids"
    )

    result = InvestmentAnalyst().run(opportunity, market_profile, classification, competition_profile, revenue_profile)

    assert result.estimated_build_cost_usd is None
    assert result.estimated_payback_months is None
    assert result.risk_notes == []
