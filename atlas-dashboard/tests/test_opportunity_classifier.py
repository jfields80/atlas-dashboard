"""
atlas/tests/test_opportunity_classifier.py

Unit tests for services/opportunity_intelligence/opportunity_classifier.py
(AES-012C).

Covers the ticket's worked example exactly, plus industry/audience/
business-type/commercial-intent classification, UNKNOWN handling,
determinism, and the typed OpportunityClassification contract.
"""

from __future__ import annotations

from services.opportunity_intelligence.market_research_analyst import MarketResearchAnalyst
from services.opportunity_intelligence.models import MarketProfile, Opportunity, OpportunityClassification
from services.opportunity_intelligence.opportunity_classifier import OpportunityClassifier


def _opportunity(name: str, niche: str = "") -> Opportunity:
    return Opportunity(opportunity_id="opp-1", name=name, niche=niche)


def _market_profile_for(name: str, niche: str = "") -> MarketProfile:
    return MarketResearchAnalyst().run(_opportunity(name, niche))


# ---------------------------------------------------------------------------
# The ticket's worked example, verbatim.
# ---------------------------------------------------------------------------


def test_ohio_martial_arts_for_kids_full_example():
    opportunity = _opportunity("Ohio Martial Arts for Kids")
    market_profile = _market_profile_for("Ohio Martial Arts for Kids")

    classification = OpportunityClassifier().run(opportunity, market_profile)

    assert classification.industry == "Sports & Recreation"
    assert classification.audience == "Children"
    assert classification.business_type == "Directory"
    assert classification.commercial_intent == "HIGH"
    assert classification.confidence == "ESTIMATED"
    # Market/Geographic Scope live on MarketProfile (AES-012B), not here.
    assert market_profile.market_name == "Martial Arts"
    assert market_profile.market_scope == "STATE"


# ---------------------------------------------------------------------------
# Industry classification
# ---------------------------------------------------------------------------


def test_industry_pet_services():
    market_profile = _market_profile_for("Columbus Dog Groomers")
    classification = OpportunityClassifier().run(_opportunity("Columbus Dog Groomers"), market_profile)

    assert classification.industry == "Pet Services"


def test_industry_food_and_agriculture():
    market_profile = _market_profile_for("Direct Beef")
    classification = OpportunityClassifier().run(_opportunity("Direct Beef"), market_profile)

    assert classification.industry == "Food & Agriculture"


def test_industry_unknown_when_category_unrecognized():
    market_profile = MarketProfile()  # no category recognized
    classification = OpportunityClassifier().run(_opportunity("Pet Trip Finder"), market_profile)

    assert classification.industry == "UNKNOWN"


# ---------------------------------------------------------------------------
# Audience classification
# ---------------------------------------------------------------------------


def test_audience_seniors():
    market_profile = _market_profile_for("Senior Yoga Classes")
    classification = OpportunityClassifier().run(_opportunity("Senior Yoga Classes"), market_profile)

    assert classification.audience == "Seniors"


def test_audience_pet_owners():
    market_profile = _market_profile_for("Columbus Dog Groomers")
    classification = OpportunityClassifier().run(_opportunity("Columbus Dog Groomers"), market_profile)

    assert classification.audience == "Pet Owners"


def test_audience_unknown_when_no_marker_present():
    market_profile = _market_profile_for("Direct Beef")
    classification = OpportunityClassifier().run(_opportunity("Direct Beef"), market_profile)

    assert classification.audience == "UNKNOWN"


def test_audience_checks_niche_field_too():
    market_profile = _market_profile_for("Best Tutors", niche="tutoring for children")
    classification = OpportunityClassifier().run(
        _opportunity("Best Tutors", niche="tutoring for children"), market_profile
    )

    assert classification.audience == "Children"


# ---------------------------------------------------------------------------
# Business type / business model
# ---------------------------------------------------------------------------


def test_business_type_directory_when_category_recognized():
    market_profile = _market_profile_for("Reliable HVAC Services")
    classification = OpportunityClassifier().run(_opportunity("Reliable HVAC Services"), market_profile)

    assert classification.business_type == "Directory"


def test_business_type_unknown_when_category_unrecognized():
    market_profile = MarketProfile()
    classification = OpportunityClassifier().run(_opportunity("Pet Trip Finder"), market_profile)

    assert classification.business_type == "UNKNOWN"


def test_business_model_stays_unknown_with_no_monetization_signal():
    """
    No monetization signal is available to this stage yet — must not
    fabricate a business_model.
    """
    market_profile = _market_profile_for("Ohio Martial Arts for Kids")
    classification = OpportunityClassifier().run(_opportunity("Ohio Martial Arts for Kids"), market_profile)

    assert classification.business_model == "UNKNOWN"


def test_market_vertical_echoes_market_profile_primary_category():
    market_profile = _market_profile_for("Reliable HVAC Services")
    classification = OpportunityClassifier().run(_opportunity("Reliable HVAC Services"), market_profile)

    assert classification.market_vertical == "HVAC"


# ---------------------------------------------------------------------------
# Commercial intent
# ---------------------------------------------------------------------------


def test_commercial_intent_high_for_home_services():
    market_profile = _market_profile_for("Reliable HVAC Services")
    classification = OpportunityClassifier().run(_opportunity("Reliable HVAC Services"), market_profile)

    assert classification.commercial_intent == "HIGH"


def test_commercial_intent_low_for_food_and_agriculture():
    market_profile = _market_profile_for("Direct Beef")
    classification = OpportunityClassifier().run(_opportunity("Direct Beef"), market_profile)

    assert classification.commercial_intent == "LOW"


def test_commercial_intent_unknown_when_industry_unrecognized():
    market_profile = MarketProfile()
    classification = OpportunityClassifier().run(_opportunity("Pet Trip Finder"), market_profile)

    assert classification.commercial_intent == "UNKNOWN"


# ---------------------------------------------------------------------------
# UNKNOWN handling never fabricates
# ---------------------------------------------------------------------------


def test_fully_unrecognized_opportunity_stays_entirely_unknown():
    market_profile = MarketProfile()
    classification = OpportunityClassifier().run(_opportunity("Xyzzy Quibble Widgets"), market_profile)

    assert classification.industry == "UNKNOWN"
    assert classification.audience == "UNKNOWN"
    assert classification.business_type == "UNKNOWN"
    assert classification.commercial_intent == "UNKNOWN"
    assert classification.confidence == "UNKNOWN"


def test_never_sets_verified_confidence():
    for name in ("Ohio Martial Arts for Kids", "Columbus Dog Groomers", "Direct Beef", "Xyzzy Widgets"):
        market_profile = _market_profile_for(name)
        classification = OpportunityClassifier().run(_opportunity(name), market_profile)
        assert classification.confidence != "VERIFIED"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_identical_input_produces_identical_output():
    opportunity = _opportunity("Ohio Martial Arts for Kids")
    market_profile = _market_profile_for("Ohio Martial Arts for Kids")
    classifier = OpportunityClassifier()

    result_a = classifier.run(opportunity, market_profile)
    result_b = classifier.run(opportunity, market_profile)

    assert result_a == result_b


def test_different_classifier_instances_produce_identical_output():
    opportunity = _opportunity("Columbus Dog Groomers")
    market_profile = _market_profile_for("Columbus Dog Groomers")

    result_a = OpportunityClassifier().run(opportunity, market_profile)
    result_b = OpportunityClassifier().run(opportunity, market_profile)

    assert result_a == result_b


# ---------------------------------------------------------------------------
# Typed contract
# ---------------------------------------------------------------------------


def test_run_returns_opportunity_classification_instance():
    market_profile = _market_profile_for("Direct Beef")
    result = OpportunityClassifier().run(_opportunity("Direct Beef"), market_profile)

    assert isinstance(result, OpportunityClassification)


def test_classifier_has_no_mutable_shared_state_between_instances():
    first = OpportunityClassifier()
    first.run(_opportunity("Ohio Martial Arts for Kids"), _market_profile_for("Ohio Martial Arts for Kids"))

    second = OpportunityClassifier()
    market_profile = _market_profile_for("Direct Beef")
    result = second.run(_opportunity("Direct Beef"), market_profile)

    assert result.industry == "Food & Agriculture"
