"""
atlas/tests/test_opportunity_intelligence_stages.py

Unit tests for services/opportunity_intelligence/stages.py (AES-012A).

Verifies each placeholder stage's typed input/output contract and
that placeholder outputs are honestly tagged UNKNOWN rather than
fabricating data.
"""

from __future__ import annotations

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
from services.opportunity_intelligence.stages import (
    PlaceholderCommitteeRecommendationStage,
    PlaceholderCompetitionAnalysisStage,
    PlaceholderInvestmentAnalysisStage,
    PlaceholderInvestmentMemoStage,
    PlaceholderMarketResearchStage,
    PlaceholderOpportunityClassificationStage,
    PlaceholderRevenueAnalysisStage,
    PlaceholderSourceCollectionStage,
    StageName,
    ordered_stage_names,
)


def _opportunity() -> Opportunity:
    return Opportunity(opportunity_id="opp-1", name="Pet Trip Finder", niche="pet-friendly-travel")


def test_ordered_stage_names_returns_all_eight_in_pipeline_order():
    assert ordered_stage_names() == [
        StageName.SOURCE_COLLECTION,
        StageName.MARKET_RESEARCH,
        StageName.OPPORTUNITY_CLASSIFICATION,
        StageName.COMPETITION_ANALYSIS,
        StageName.REVENUE_ANALYSIS,
        StageName.INVESTMENT_ANALYSIS,
        StageName.COMMITTEE_RECOMMENDATION,
        StageName.INVESTMENT_MEMO,
    ]


def test_source_collection_stage_passes_opportunity_through_unchanged():
    opportunity = _opportunity()
    stage = PlaceholderSourceCollectionStage()

    result = stage.run(opportunity)

    assert result is opportunity
    assert stage.name == StageName.SOURCE_COLLECTION


def test_market_research_stage_returns_unknown_market_profile():
    stage = PlaceholderMarketResearchStage()

    result = stage.run(_opportunity())

    assert isinstance(result, MarketProfile)
    assert result.data_confidence == "UNKNOWN"
    assert result.total_addressable_market_usd is None


def test_opportunity_classification_stage_returns_unknown_classification():
    stage = PlaceholderOpportunityClassificationStage()

    result = stage.run(_opportunity(), MarketProfile())

    assert isinstance(result, OpportunityClassification)
    assert result.industry == "UNKNOWN"
    assert result.confidence == "UNKNOWN"
    assert stage.name == StageName.OPPORTUNITY_CLASSIFICATION


def test_competition_analysis_stage_returns_unknown_competition_profile():
    stage = PlaceholderCompetitionAnalysisStage()

    result = stage.run(_opportunity(), MarketProfile())

    assert isinstance(result, CompetitionProfile)
    assert result.data_confidence == "UNKNOWN"


def test_revenue_analysis_stage_returns_unknown_revenue_profile():
    stage = PlaceholderRevenueAnalysisStage()

    result = stage.run(_opportunity(), MarketProfile(), CompetitionProfile())

    assert isinstance(result, RevenueProfile)
    assert result.data_confidence == "UNKNOWN"


def test_investment_analysis_stage_returns_unknown_investment_profile():
    stage = PlaceholderInvestmentAnalysisStage()

    result = stage.run(_opportunity(), MarketProfile(), CompetitionProfile(), RevenueProfile())

    assert isinstance(result, InvestmentProfile)
    assert result.data_confidence == "UNKNOWN"


def test_committee_recommendation_stage_returns_unassessed_recommendation():
    stage = PlaceholderCommitteeRecommendationStage()
    assessment = OpportunityAssessment(opportunity=_opportunity())

    result = stage.run(assessment)

    assert isinstance(result, Recommendation)
    assert result.decision == "UNASSESSED"
    assert result.confidence == 0.0
    assert "Placeholder" in result.rationale


def test_investment_memo_stage_assembles_memo_from_inputs():
    opportunity = _opportunity()
    assessment = OpportunityAssessment(opportunity=opportunity)
    recommendation = Recommendation()
    stage = PlaceholderInvestmentMemoStage()

    result = stage.run(opportunity, assessment, recommendation)

    assert isinstance(result, InvestmentMemo)
    # pydantic copies nested submodels on construction rather than
    # preserving identity, so compare by value, not `is`.
    assert result.opportunity == opportunity
    assert result.assessment == assessment
    assert result.recommendation == recommendation
    assert result.generated_at != ""
