"""
atlas/tests/test_market_research_analyst.py

Unit tests for services/opportunity_intelligence/market_research_analyst.py
(AES-012B).

Covers the three worked examples from the ticket exactly, plus
additional geography/category cases, UNKNOWN handling, determinism,
and the typed MarketProfile contract.
"""

from __future__ import annotations

from services.opportunity_intelligence.market_research_analyst import (
    MarketResearchAnalyst,
    MarketScope,
)
from services.opportunity_intelligence.models import MarketProfile, Opportunity


def _opportunity(name: str, niche: str = "") -> Opportunity:
    return Opportunity(opportunity_id="opp-1", name=name, niche=niche)


# ---------------------------------------------------------------------------
# The three worked examples from the ticket, verbatim.
# ---------------------------------------------------------------------------


def test_ohio_martial_arts_for_kids():
    profile = MarketResearchAnalyst().run(_opportunity("Ohio Martial Arts for Kids"))

    assert profile.market_name == "Martial Arts"
    assert profile.primary_category == "Martial Arts"
    assert profile.primary_geography == "Ohio"
    assert profile.market_scope == MarketScope.STATE.value


def test_columbus_dog_groomers():
    profile = MarketResearchAnalyst().run(_opportunity("Columbus Dog Groomers"))

    assert profile.market_name == "Dog Grooming"
    assert profile.primary_geography == "Columbus"
    assert profile.market_scope == MarketScope.CITY.value


def test_direct_beef():
    profile = MarketResearchAnalyst().run(_opportunity("Direct Beef"))

    assert profile.market_name == "Beef"
    assert profile.primary_geography == "National"
    assert profile.market_scope == MarketScope.NATIONAL.value


# ---------------------------------------------------------------------------
# Additional geography cases
# ---------------------------------------------------------------------------


def test_geography_prefers_city_over_state_when_both_present():
    profile = MarketResearchAnalyst().run(_opportunity("Columbus Ohio Movers"))

    assert profile.primary_geography == "Columbus"
    assert profile.market_scope == MarketScope.CITY.value


def test_geography_state_only_no_city():
    profile = MarketResearchAnalyst().run(_opportunity("Texas Roofing Company"))

    assert profile.primary_geography == "Texas"
    assert profile.market_scope == MarketScope.STATE.value


def test_geography_no_marker_defaults_to_national():
    profile = MarketResearchAnalyst().run(_opportunity("Premium Auto Repair"))

    assert profile.primary_geography == "National"
    assert profile.market_scope == MarketScope.NATIONAL.value


def test_geography_checks_niche_field_too():
    profile = MarketResearchAnalyst().run(_opportunity("Best Tutors", niche="Seattle tutoring service"))

    assert profile.primary_geography == "Seattle"
    assert profile.market_scope == MarketScope.CITY.value


# ---------------------------------------------------------------------------
# Category extraction
# ---------------------------------------------------------------------------


def test_category_yoga():
    profile = MarketResearchAnalyst().run(_opportunity("Downtown Yoga Studio"))
    assert profile.market_name == "Yoga"


def test_category_hvac():
    profile = MarketResearchAnalyst().run(_opportunity("Reliable HVAC Services"))
    assert profile.market_name == "HVAC"


def test_category_unknown_when_no_keyword_matches():
    profile = MarketResearchAnalyst().run(_opportunity("Pet Trip Finder"))

    assert profile.market_name == "UNKNOWN"
    assert profile.primary_category == "UNKNOWN"


# ---------------------------------------------------------------------------
# UNKNOWN handling never fabricates
# ---------------------------------------------------------------------------


def test_unrecognized_opportunity_still_returns_valid_profile_with_unknown_category():
    profile = MarketResearchAnalyst().run(_opportunity("Xyzzy Quibble Widgets"))

    assert isinstance(profile, MarketProfile)
    assert profile.market_name == "UNKNOWN"
    assert profile.primary_category == "UNKNOWN"
    # Geography still honestly defaults to National rather than guessing a place.
    assert profile.primary_geography == "National"
    assert profile.market_scope == MarketScope.NATIONAL.value


def test_analyst_never_sets_verified_confidence():
    """This analyst infers from text; it never confirms against real
    market data, so its output must never claim VERIFIED confidence."""
    for name in ("Ohio Martial Arts for Kids", "Columbus Dog Groomers", "Direct Beef", "Random Widgets"):
        profile = MarketResearchAnalyst().run(_opportunity(name))
        assert profile.data_confidence != "VERIFIED"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_identical_input_produces_identical_output():
    opportunity = _opportunity("Ohio Martial Arts for Kids")
    analyst = MarketResearchAnalyst()

    profile_a = analyst.run(opportunity)
    profile_b = analyst.run(opportunity)

    assert profile_a == profile_b


def test_different_analyst_instances_produce_identical_output_for_same_input():
    opportunity = _opportunity("Columbus Dog Groomers")

    profile_a = MarketResearchAnalyst().run(opportunity)
    profile_b = MarketResearchAnalyst().run(opportunity)

    assert profile_a == profile_b


# ---------------------------------------------------------------------------
# Typed contract
# ---------------------------------------------------------------------------


def test_run_returns_market_profile_instance():
    result = MarketResearchAnalyst().run(_opportunity("Direct Beef"))
    assert isinstance(result, MarketProfile)


def test_analyst_has_no_mutable_shared_state_between_instances():
    """No global state, no singletons: a fresh instance must not be
    affected by a previous instance's run()."""
    first = MarketResearchAnalyst()
    first.run(_opportunity("Ohio Martial Arts for Kids"))

    second = MarketResearchAnalyst()
    profile = second.run(_opportunity("Direct Beef"))

    assert profile.market_name == "Beef"
    assert profile.primary_geography == "National"
