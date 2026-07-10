"""
atlas/tests/test_revenue_analyst.py

Unit tests for services/opportunity_intelligence/revenue_analyst.py
(AES-012E).

Covers monetization-mechanism characterization for each supported
business_type, business_model precedence over business_type,
secondary-model determinism, competition-profile refinement, UNKNOWN
handling, determinism, and the typed RevenueProfile contract. Verifies
no financial amounts/projections are ever fabricated.
"""

from __future__ import annotations

from services.opportunity_intelligence.competition_analyst import CompetitionAnalyst
from services.opportunity_intelligence.market_research_analyst import MarketResearchAnalyst
from services.opportunity_intelligence.models import (
    CompetitionProfile,
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
    """Full real upstream chain: MarketProfile -> Classification -> CompetitionProfile."""
    opportunity = _opportunity(name, niche)
    market_profile = MarketResearchAnalyst().run(opportunity)
    classification = OpportunityClassifier().run(opportunity, market_profile)
    competition_profile = CompetitionAnalyst().run(opportunity, market_profile, classification)
    return opportunity, market_profile, classification, competition_profile


# ---------------------------------------------------------------------------
# Per-business-type monetization characterization
# ---------------------------------------------------------------------------


def test_directory_classification_produces_valid_directory_monetization_profile():
    opportunity, market_profile, classification, competition_profile = _derived("Reliable HVAC Services")
    assert classification.business_type == "Directory"

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "FEATURED_LISTINGS"
    assert result.recurring_revenue_potential == "MODERATE"
    assert result.transaction_revenue_potential == "LOW"
    assert result.revenue_scalability == "HIGH"
    assert result.monetization_strength == "MODERATE"
    assert "ADVERTISING" in result.secondary_revenue_models


def test_marketplace_classification_produces_transaction_fee_monetization():
    opportunity = _opportunity("Widget Marketplace")
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Marketplace")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "TRANSACTION_FEES"
    assert result.transaction_revenue_potential == "HIGH"
    assert result.revenue_scalability == "HIGH"


def test_saas_classification_produces_subscription_monetization():
    opportunity = _opportunity("Acme SaaS")
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="SaaS")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "SUBSCRIPTIONS"
    assert result.recurring_revenue_potential == "HIGH"


def test_service_provider_classification_produces_direct_service_monetization():
    opportunity = _opportunity("Local Handyman")
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Service Provider")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "DIRECT_SERVICES"
    assert result.revenue_scalability == "LOW"


def test_ecommerce_classification_produces_product_sales_monetization():
    opportunity = _opportunity("Direct Beef Shop")
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Ecommerce")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "PRODUCT_SALES"
    assert result.transaction_revenue_potential == "HIGH"


def test_content_publisher_classification_produces_advertising_monetization():
    opportunity = _opportunity("Pet Blog")
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Content Publisher")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "ADVERTISING"
    assert "AFFILIATE_REVENUE" in result.secondary_revenue_models


def test_business_type_lookup_is_case_and_whitespace_insensitive():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="  directory  ")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "FEATURED_LISTINGS"


# ---------------------------------------------------------------------------
# Secondary revenue models: determinism, no duplicates, ordering
# ---------------------------------------------------------------------------


def test_secondary_revenue_models_are_deterministic():
    opportunity, market_profile, classification, competition_profile = _derived("Reliable HVAC Services")

    result_a = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)
    result_b = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result_a.secondary_revenue_models == result_b.secondary_revenue_models


def test_secondary_revenue_models_contain_no_duplicates():
    opportunity, market_profile, classification, competition_profile = _derived("Reliable HVAC Services")

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert len(result.secondary_revenue_models) == len(set(result.secondary_revenue_models))


def test_secondary_revenue_models_have_deterministic_sorted_ordering():
    opportunity, market_profile, classification, competition_profile = _derived("Reliable HVAC Services")

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.secondary_revenue_models == sorted(result.secondary_revenue_models)


def test_primary_model_never_appears_in_secondary_models():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Directory", business_model="advertising")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model not in result.secondary_revenue_models


# ---------------------------------------------------------------------------
# business_model precedence over business_type
# ---------------------------------------------------------------------------


def test_recognized_business_model_takes_precedence_over_business_type():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Marketplace", business_model="subscriptions")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "SUBSCRIPTIONS"
    # the business_type's own primary model is demoted to secondary, not dropped
    assert "TRANSACTION_FEES" in result.secondary_revenue_models


def test_conflicting_business_model_and_business_type_reduce_confidence():
    opportunity = _opportunity()
    market_profile = MarketProfile(market_scope="NATIONAL")
    classification_conflict = OpportunityClassification(business_type="Directory", business_model="subscriptions")
    classification_agree = OpportunityClassification(business_type="Directory", business_model="featured_listings")
    competition_profile = CompetitionProfile(data_confidence="ESTIMATED")

    result_conflict = RevenueAnalyst().run(opportunity, market_profile, classification_conflict, competition_profile)
    result_agree = RevenueAnalyst().run(opportunity, market_profile, classification_agree, competition_profile)

    confidence_order = ("UNKNOWN", "LOW", "MODERATE", "HIGH")
    assert confidence_order.index(result_conflict.data_confidence) < confidence_order.index(result_agree.data_confidence)


# ---------------------------------------------------------------------------
# Competition-profile refinement
# ---------------------------------------------------------------------------


def test_competition_data_can_refine_a_recognized_profile():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="SaaS")
    competition_profile = CompetitionProfile(competitor_archetype="fragmented_local_providers")

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "SUBSCRIPTIONS"
    assert "LEAD_GENERATION" in result.secondary_revenue_models
    assert "FEATURED_LISTINGS" in result.secondary_revenue_models


def test_unknown_competition_data_does_not_erase_recognized_classification_result():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Directory")
    competition_profile = CompetitionProfile()  # entirely UNKNOWN

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "FEATURED_LISTINGS"
    assert result.data_confidence != "UNKNOWN"


# ---------------------------------------------------------------------------
# UNKNOWN handling never fabricates
# ---------------------------------------------------------------------------


def test_missing_classification_returns_valid_unknown_profile():
    result = RevenueAnalyst().run(_opportunity(), MarketProfile(), OpportunityClassification(), CompetitionProfile())

    assert isinstance(result, RevenueProfile)
    assert result.primary_revenue_model == "UNKNOWN"
    assert result.secondary_revenue_models == []
    assert result.recurring_revenue_potential == "UNKNOWN"
    assert result.transaction_revenue_potential == "UNKNOWN"
    assert result.monetization_strength == "UNKNOWN"
    assert result.revenue_scalability == "UNKNOWN"
    assert result.data_confidence == "UNKNOWN"


def test_completely_unknown_inputs_return_valid_mostly_unknown_profile():
    opportunity = _opportunity("Xyzzy Quibble Widgets")
    market_profile = MarketProfile()
    classification = OpportunityClassification()
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "UNKNOWN"
    assert result.data_confidence == "UNKNOWN"


def test_unsupported_future_business_type_does_not_crash():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Some Future Vertical")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert isinstance(result, RevenueProfile)
    assert result.primary_revenue_model == "UNKNOWN"


def test_unsupported_future_business_model_does_not_crash():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Directory", business_model="some-future-mechanism")
    competition_profile = CompetitionProfile()

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "FEATURED_LISTINGS"


def test_unsupported_competitor_archetype_does_not_crash():
    opportunity = _opportunity()
    market_profile = MarketProfile()
    classification = OpportunityClassification(business_type="Directory")
    competition_profile = CompetitionProfile(competitor_archetype="some_future_archetype")

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.primary_revenue_model == "FEATURED_LISTINGS"


# ---------------------------------------------------------------------------
# Confidence behavior
# ---------------------------------------------------------------------------


def test_confidence_increases_with_additional_consistent_signals():
    opportunity = _opportunity()
    classification = OpportunityClassification(business_type="Directory")

    bare_result = RevenueAnalyst().run(opportunity, MarketProfile(), classification, CompetitionProfile())
    enriched_result = RevenueAnalyst().run(
        opportunity,
        MarketProfile(market_scope="NATIONAL"),
        classification,
        CompetitionProfile(data_confidence="ESTIMATED"),
    )

    confidence_order = ("UNKNOWN", "LOW", "MODERATE", "HIGH")
    assert confidence_order.index(enriched_result.data_confidence) > confidence_order.index(bare_result.data_confidence)


def test_confidence_never_verified():
    inputs = [
        ("Reliable HVAC Services",),
        ("Direct Beef",),
        ("Columbus Dog Groomers",),
        ("Xyzzy Widgets",),
    ]
    for (name,) in inputs:
        opportunity, market_profile, classification, competition_profile = _derived(name)
        result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)
        assert result.data_confidence != "VERIFIED"


# ---------------------------------------------------------------------------
# No mutation, determinism, typed contract
# ---------------------------------------------------------------------------


def test_inputs_are_not_mutated():
    opportunity = _opportunity()
    market_profile = MarketProfile(market_scope="NATIONAL")
    classification = OpportunityClassification(business_type="Directory")
    competition_profile = CompetitionProfile(competitor_archetype="national_platforms")

    market_profile_copy = market_profile.copy(deep=True)
    classification_copy = classification.copy(deep=True)
    competition_profile_copy = competition_profile.copy(deep=True)

    RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert market_profile == market_profile_copy
    assert classification == classification_copy
    assert competition_profile == competition_profile_copy


def test_repeated_calls_with_identical_inputs_return_identical_results():
    opportunity, market_profile, classification, competition_profile = _derived("Reliable HVAC Services")
    analyst = RevenueAnalyst()

    result_a = analyst.run(opportunity, market_profile, classification, competition_profile)
    result_b = analyst.run(opportunity, market_profile, classification, competition_profile)

    assert result_a == result_b


def test_run_returns_revenue_profile_instance():
    result = RevenueAnalyst().run(_opportunity(), MarketProfile(), OpportunityClassification(), CompetitionProfile())

    assert isinstance(result, RevenueProfile)


def test_analyst_has_no_mutable_shared_state_between_instances():
    first = RevenueAnalyst()
    opportunity1, market_profile1, classification1, competition_profile1 = _derived("Reliable HVAC Services")
    first.run(opportunity1, market_profile1, classification1, competition_profile1)

    second = RevenueAnalyst()
    opportunity2 = _opportunity("Widget Shop")
    classification2 = OpportunityClassification(business_type="Ecommerce")
    result = second.run(opportunity2, MarketProfile(), classification2, CompetitionProfile())

    assert result.primary_revenue_model == "PRODUCT_SALES"


# ---------------------------------------------------------------------------
# Never fabricates financial data
# ---------------------------------------------------------------------------


def test_never_populates_financial_amounts():
    opportunity, market_profile, classification, competition_profile = _derived("Reliable HVAC Services")

    result = RevenueAnalyst().run(opportunity, market_profile, classification, competition_profile)

    assert result.estimated_monthly_revenue_usd is None
    assert result.revenue_model_notes == ""
    assert result.monetization_signals == []
