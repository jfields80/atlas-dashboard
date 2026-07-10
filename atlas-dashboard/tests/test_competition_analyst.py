"""
atlas/tests/test_competition_analyst.py

Unit tests for services/opportunity_intelligence/competition_analyst.py
(AES-012D).

Covers state/local-market and national-market characterization,
recognized directory-business classification, UNKNOWN handling,
determinism, and the typed CompetitionProfile contract, plus pipeline
integration (default stage, stage ordering, custom-stage injection).
"""

from __future__ import annotations

from services.opportunity_intelligence.competition_analyst import CompetitionAnalyst
from services.opportunity_intelligence.market_research_analyst import MarketResearchAnalyst
from services.opportunity_intelligence.models import CompetitionProfile, MarketProfile, Opportunity, OpportunityClassification
from services.opportunity_intelligence.opportunity_classifier import OpportunityClassifier
from services.opportunity_intelligence.opportunity_pipeline import OpportunityPipeline


def _opportunity(name: str, niche: str = "") -> Opportunity:
    return Opportunity(opportunity_id="opp-1", name=name, niche=niche)


def _market_profile_for(name: str, niche: str = "") -> MarketProfile:
    return MarketResearchAnalyst().run(_opportunity(name, niche))


def _classification_for(name: str, niche: str = "") -> OpportunityClassification:
    opportunity = _opportunity(name, niche)
    market_profile = _market_profile_for(name, niche)
    return OpportunityClassifier().run(opportunity, market_profile)


# ---------------------------------------------------------------------------
# State / local-market characterization
# ---------------------------------------------------------------------------


def test_state_scope_market_characterized_as_fragmented_local():
    opportunity = _opportunity("Ohio Martial Arts for Kids")
    market_profile = _market_profile_for("Ohio Martial Arts for Kids")
    classification = _classification_for("Ohio Martial Arts for Kids")

    result = CompetitionAnalyst().run(opportunity, market_profile, classification)

    assert market_profile.market_scope == "STATE"
    assert result.competitor_archetype == "fragmented_local_providers"
    assert result.market_fragmentation == "HIGH"
    assert result.likely_competitor_type == "local_businesses_and_small_directories"
    assert result.competitive_risk == "MODERATE"
    assert result.competition_scope == "STATE"
    assert result.data_confidence == "ESTIMATED"


# ---------------------------------------------------------------------------
# National-market characterization
# ---------------------------------------------------------------------------


def test_national_scope_market_characterized_as_national_platforms():
    opportunity = _opportunity("Direct Beef")
    market_profile = _market_profile_for("Direct Beef")
    classification = _classification_for("Direct Beef")

    result = CompetitionAnalyst().run(opportunity, market_profile, classification)

    assert market_profile.market_scope == "NATIONAL"
    assert result.competitor_archetype == "national_platforms"
    assert result.market_fragmentation == "MODERATE"
    assert result.likely_competitor_type == "large_directories_and_marketplaces"
    assert result.competitive_risk == "HIGH"
    assert result.competition_scope == "NATIONAL"
    assert result.data_confidence == "ESTIMATED"


# ---------------------------------------------------------------------------
# Recognized directory-business classification required
# ---------------------------------------------------------------------------


def test_recognized_directory_business_type_populates_profile():
    classification = _classification_for("Reliable HVAC Services")
    assert classification.business_type == "Directory"

    market_profile = _market_profile_for("Reliable HVAC Services")
    result = CompetitionAnalyst().run(_opportunity("Reliable HVAC Services"), market_profile, classification)

    assert result.data_confidence == "ESTIMATED"


# ---------------------------------------------------------------------------
# UNKNOWN handling never fabricates
# ---------------------------------------------------------------------------


def test_unrecognized_business_type_stays_entirely_unknown():
    opportunity = _opportunity("Pet Trip Finder")
    market_profile = MarketProfile()  # no category, scope UNKNOWN
    classification = OpportunityClassification()  # business_type UNKNOWN

    result = CompetitionAnalyst().run(opportunity, market_profile, classification)

    assert isinstance(result, CompetitionProfile)
    assert result.competitor_archetype == "UNKNOWN"
    assert result.market_fragmentation == "UNKNOWN"
    assert result.likely_competitor_type == "UNKNOWN"
    assert result.competitive_risk == "UNKNOWN"
    assert result.competition_scope == "UNKNOWN"
    assert result.data_confidence == "UNKNOWN"


def test_unrecognized_market_scope_stays_unknown_even_with_recognized_business_type():
    """
    CITY and REGIONAL are not represented in SCOPE_COMPETITION_PROFILE
    (no worked example evidences a rule for them) — even a recognized
    business_type must not fabricate a competition profile for a scope
    this analyst doesn't have a real signal for.
    """
    opportunity = _opportunity("Columbus Dog Groomers")
    market_profile = _market_profile_for("Columbus Dog Groomers")
    classification = _classification_for("Columbus Dog Groomers")

    assert market_profile.market_scope == "CITY"
    assert classification.business_type == "Directory"

    result = CompetitionAnalyst().run(opportunity, market_profile, classification)

    assert result.competitor_archetype == "UNKNOWN"
    assert result.data_confidence == "UNKNOWN"


def test_never_sets_verified_confidence():
    for name in ("Ohio Martial Arts for Kids", "Direct Beef", "Columbus Dog Groomers", "Xyzzy Widgets"):
        market_profile = _market_profile_for(name)
        classification = _classification_for(name)
        result = CompetitionAnalyst().run(_opportunity(name), market_profile, classification)
        assert result.data_confidence != "VERIFIED"


def test_never_populates_out_of_scope_fields():
    """
    competitor_count, competitor_names, barriers_to_entry, and
    competitive_intensity require real external data or are simply out
    of this ticket's scope — this analyst must never populate them.
    """
    market_profile = _market_profile_for("Ohio Martial Arts for Kids")
    classification = _classification_for("Ohio Martial Arts for Kids")

    result = CompetitionAnalyst().run(_opportunity("Ohio Martial Arts for Kids"), market_profile, classification)

    assert result.competitor_count is None
    assert result.competitor_names == []
    assert result.barriers_to_entry == []
    assert result.competitive_intensity == "UNKNOWN"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_identical_input_produces_identical_output():
    opportunity = _opportunity("Ohio Martial Arts for Kids")
    market_profile = _market_profile_for("Ohio Martial Arts for Kids")
    classification = _classification_for("Ohio Martial Arts for Kids")
    analyst = CompetitionAnalyst()

    result_a = analyst.run(opportunity, market_profile, classification)
    result_b = analyst.run(opportunity, market_profile, classification)

    assert result_a == result_b


def test_different_analyst_instances_produce_identical_output():
    opportunity = _opportunity("Direct Beef")
    market_profile = _market_profile_for("Direct Beef")
    classification = _classification_for("Direct Beef")

    result_a = CompetitionAnalyst().run(opportunity, market_profile, classification)
    result_b = CompetitionAnalyst().run(opportunity, market_profile, classification)

    assert result_a == result_b


# ---------------------------------------------------------------------------
# Typed contract / no shared mutable state
# ---------------------------------------------------------------------------


def test_run_returns_competition_profile_instance():
    market_profile = _market_profile_for("Direct Beef")
    classification = _classification_for("Direct Beef")
    result = CompetitionAnalyst().run(_opportunity("Direct Beef"), market_profile, classification)

    assert isinstance(result, CompetitionProfile)


def test_analyst_has_no_mutable_shared_state_between_instances():
    first = CompetitionAnalyst()
    first.run(
        _opportunity("Ohio Martial Arts for Kids"),
        _market_profile_for("Ohio Martial Arts for Kids"),
        _classification_for("Ohio Martial Arts for Kids"),
    )

    second = CompetitionAnalyst()
    market_profile = _market_profile_for("Direct Beef")
    classification = _classification_for("Direct Beef")
    result = second.run(_opportunity("Direct Beef"), market_profile, classification)

    assert result.competitor_archetype == "national_platforms"


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


def test_pipeline_default_competition_stage_is_the_real_analyst():
    """
    OpportunityPipeline() with no overrides must use the real
    CompetitionAnalyst, not the AES-012A placeholder — proven by a
    fully recognizable opportunity resolving to a real (non-UNKNOWN)
    competition profile.
    """
    pipeline = OpportunityPipeline()
    opportunity = Opportunity(opportunity_id="opp-4", name="Ohio Martial Arts for Kids", niche="martial arts")

    memo = pipeline.run(opportunity)

    assert memo.assessment.competition_profile.competitor_archetype == "fragmented_local_providers"
    assert memo.assessment.competition_profile.competition_scope == "STATE"
    assert memo.assessment.competition_profile.data_confidence == "ESTIMATED"


def test_pipeline_accepts_custom_competition_stage_implementation():
    class _FixedCompetitionAnalysisStage:
        def run(self, opportunity, market_profile, classification):
            return CompetitionProfile(competitor_archetype="fixed", data_confidence="ESTIMATED")

    pipeline = OpportunityPipeline(competition_analysis_stage=_FixedCompetitionAnalysisStage())

    memo = pipeline.run(_opportunity("Pet Trip Finder"))

    assert memo.assessment.competition_profile.competitor_archetype == "fixed"
