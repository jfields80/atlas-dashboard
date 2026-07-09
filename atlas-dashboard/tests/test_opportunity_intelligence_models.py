"""
atlas/tests/test_opportunity_intelligence_models.py

Unit tests for services/opportunity_intelligence/models.py (AES-012A).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.opportunity_intelligence.models import (
    CompetitionProfile,
    InvestmentMemo,
    InvestmentProfile,
    MarketProfile,
    Opportunity,
    OpportunityAssessment,
    OpportunitySource,
    Recommendation,
    RevenueProfile,
)


def _opportunity(**overrides) -> Opportunity:
    defaults = dict(opportunity_id="opp-1", name="Pet Trip Finder", niche="pet-friendly-travel")
    defaults.update(overrides)
    return Opportunity(**defaults)


def test_opportunity_requires_id_name_and_niche():
    with pytest.raises(ValidationError):
        Opportunity()


def test_opportunity_source_defaults_to_unknown():
    source = OpportunitySource()
    assert source.source_type == "UNKNOWN"
    assert source.source_name == ""


def test_opportunity_defaults_have_unknown_source_and_national_scope():
    opportunity = _opportunity()
    assert opportunity.source.source_type == "UNKNOWN"
    assert opportunity.geographic_scope == "national"
    assert opportunity.tags == []


def test_opportunity_accepts_explicit_source():
    opportunity = _opportunity(source=OpportunitySource(source_type="scout", source_name="Google Places"))
    assert opportunity.source.source_type == "scout"


def test_market_profile_defaults_to_unknown_confidence():
    profile = MarketProfile()
    assert profile.data_confidence == "UNKNOWN"
    assert profile.total_addressable_market_usd is None
    assert profile.demand_signals == []


def test_competition_profile_defaults_to_unknown_confidence():
    profile = CompetitionProfile()
    assert profile.data_confidence == "UNKNOWN"
    assert profile.competitor_count is None


def test_revenue_profile_defaults_to_unknown_confidence():
    profile = RevenueProfile()
    assert profile.data_confidence == "UNKNOWN"
    assert profile.estimated_monthly_revenue_usd is None


def test_investment_profile_defaults_to_unknown_confidence():
    profile = InvestmentProfile()
    assert profile.data_confidence == "UNKNOWN"
    assert profile.risk_notes == []


def test_recommendation_defaults_to_unassessed():
    recommendation = Recommendation()
    assert recommendation.decision == "UNASSESSED"
    assert recommendation.confidence == 0.0


def test_recommendation_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        Recommendation(confidence=1.5)

    with pytest.raises(ValidationError):
        Recommendation(confidence=-0.1)


def test_opportunity_assessment_requires_opportunity():
    with pytest.raises(ValidationError):
        OpportunityAssessment()


def test_opportunity_assessment_profiles_default_to_none():
    assessment = OpportunityAssessment(opportunity=_opportunity())
    assert assessment.market_profile is None
    assert assessment.competition_profile is None
    assert assessment.revenue_profile is None
    assert assessment.investment_profile is None


def test_investment_memo_requires_opportunity_assessment_and_recommendation():
    with pytest.raises(ValidationError):
        InvestmentMemo()


def test_investment_memo_constructs_with_full_assessment():
    opportunity = _opportunity()
    assessment = OpportunityAssessment(
        opportunity=opportunity,
        market_profile=MarketProfile(),
        competition_profile=CompetitionProfile(),
        revenue_profile=RevenueProfile(),
        investment_profile=InvestmentProfile(),
    )
    recommendation = Recommendation()

    memo = InvestmentMemo(opportunity=opportunity, assessment=assessment, recommendation=recommendation)

    assert memo.opportunity.opportunity_id == "opp-1"
    assert memo.assessment.market_profile is not None
    assert memo.recommendation.decision == "UNASSESSED"
