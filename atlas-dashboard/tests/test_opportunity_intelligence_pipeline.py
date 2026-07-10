"""
atlas/tests/test_opportunity_intelligence_pipeline.py

Unit tests for services/opportunity_intelligence/opportunity_pipeline.py
(AES-012A).

Covers: pipeline construction with default (placeholder) stages,
stage ordering, a full run producing an InvestmentMemo, custom-stage
injection (the mechanism future AI employees plug into), and
rejection of a misbehaving stage's wrongly-typed output.
"""

from __future__ import annotations

import pytest

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
from services.opportunity_intelligence.opportunity_pipeline import (
    OpportunityPipeline,
    OpportunityPipelineError,
)


def _opportunity() -> Opportunity:
    return Opportunity(opportunity_id="opp-1", name="Pet Trip Finder", niche="pet-friendly-travel")


def test_pipeline_constructs_with_all_default_placeholder_stages():
    pipeline = OpportunityPipeline()
    memo = pipeline.run(_opportunity())

    assert isinstance(memo, InvestmentMemo)


def test_pipeline_rejects_non_opportunity_input():
    pipeline = OpportunityPipeline()

    with pytest.raises(OpportunityPipelineError):
        pipeline.run("not an opportunity")  # type: ignore[arg-type]


def test_pipeline_run_produces_fully_populated_assessment():
    pipeline = OpportunityPipeline()

    memo = pipeline.run(_opportunity())

    assert memo.assessment.market_profile is not None
    assert memo.assessment.classification is not None
    assert memo.assessment.competition_profile is not None
    assert memo.assessment.revenue_profile is not None
    assert memo.assessment.investment_profile is not None
    assert memo.recommendation.decision == "UNASSESSED"


def test_pipeline_default_classification_stage_is_the_real_classifier():
    """
    AES-012C: OpportunityPipeline() with no overrides must use the real
    OpportunityClassifier, not the AES-012A-style placeholder — proven
    by a fully recognizable opportunity resolving to real (non-UNKNOWN)
    classification facts.
    """
    pipeline = OpportunityPipeline()
    opportunity = Opportunity(opportunity_id="opp-3", name="Ohio Martial Arts for Kids", niche="martial arts")

    memo = pipeline.run(opportunity)

    assert memo.assessment.classification.industry == "Sports & Recreation"
    assert memo.assessment.classification.audience == "Children"
    assert memo.assessment.classification.business_type == "Directory"
    assert memo.assessment.classification.commercial_intent == "HIGH"


def test_pipeline_default_market_research_stage_is_the_real_analyst():
    """
    AES-012B: OpportunityPipeline() with no overrides must use the real
    MarketResearchAnalyst, not the AES-012A placeholder — proven by a
    geography-bearing opportunity name resolving to real (non-UNKNOWN)
    facts, matching the ticket's own worked examples.
    """
    pipeline = OpportunityPipeline()
    opportunity = Opportunity(opportunity_id="opp-2", name="Ohio Martial Arts for Kids", niche="martial arts")

    memo = pipeline.run(opportunity)

    assert memo.assessment.market_profile.market_name == "Martial Arts"
    assert memo.assessment.market_profile.primary_geography == "Ohio"
    assert memo.assessment.market_profile.market_scope == "STATE"


def test_pipeline_calls_stages_in_correct_order():
    """
    A stage-ordering regression guard: instrumented fake stages record
    the order they were invoked in, proving the pipeline calls
    Source Collection -> Market Research -> Opportunity Classification
    -> Competition Analysis -> Revenue Analysis -> Investment Analysis
    -> Committee Recommendation -> Investment Memo, in that fixed
    sequence.
    """
    call_order: list[str] = []

    class _RecordingSourceCollectionStage:
        def run(self, opportunity):
            call_order.append("source_collection")
            return opportunity

    class _RecordingMarketResearchStage:
        def run(self, opportunity):
            call_order.append("market_research")
            return MarketProfile()

    class _RecordingOpportunityClassificationStage:
        def run(self, opportunity, market_profile):
            call_order.append("opportunity_classification")
            return OpportunityClassification()

    class _RecordingCompetitionAnalysisStage:
        def run(self, opportunity, market_profile, classification):
            call_order.append("competition_analysis")
            return CompetitionProfile()

    class _RecordingRevenueAnalysisStage:
        def run(self, opportunity, market_profile, competition_profile):
            call_order.append("revenue_analysis")
            return RevenueProfile()

    class _RecordingInvestmentAnalysisStage:
        def run(self, opportunity, market_profile, competition_profile, revenue_profile):
            call_order.append("investment_analysis")
            return InvestmentProfile()

    class _RecordingCommitteeRecommendationStage:
        def run(self, assessment):
            call_order.append("committee_recommendation")
            return Recommendation()

    class _RecordingInvestmentMemoStage:
        def run(self, opportunity, assessment, recommendation):
            call_order.append("investment_memo")
            return InvestmentMemo(opportunity=opportunity, assessment=assessment, recommendation=recommendation)

    pipeline = OpportunityPipeline(
        source_collection_stage=_RecordingSourceCollectionStage(),
        market_research_stage=_RecordingMarketResearchStage(),
        classification_stage=_RecordingOpportunityClassificationStage(),
        competition_analysis_stage=_RecordingCompetitionAnalysisStage(),
        revenue_analysis_stage=_RecordingRevenueAnalysisStage(),
        investment_analysis_stage=_RecordingInvestmentAnalysisStage(),
        committee_recommendation_stage=_RecordingCommitteeRecommendationStage(),
        investment_memo_stage=_RecordingInvestmentMemoStage(),
    )

    pipeline.run(_opportunity())

    assert call_order == [
        "source_collection",
        "market_research",
        "opportunity_classification",
        "competition_analysis",
        "revenue_analysis",
        "investment_analysis",
        "committee_recommendation",
        "investment_memo",
    ]


def test_pipeline_accepts_custom_stage_implementations():
    """
    Proves the future-compatibility mechanism: a "real" stage
    implementation (standing in for a future AI employee) can be
    injected without any change to OpportunityPipeline itself.
    """

    class _FixedMarketResearchStage:
        def run(self, opportunity):
            return MarketProfile(
                total_addressable_market_usd=1_000_000.0,
                data_confidence="ESTIMATED",
            )

    pipeline = OpportunityPipeline(market_research_stage=_FixedMarketResearchStage())

    memo = pipeline.run(_opportunity())

    assert memo.assessment.market_profile.total_addressable_market_usd == 1_000_000.0
    assert memo.assessment.market_profile.data_confidence == "ESTIMATED"


def test_pipeline_raises_when_a_stage_returns_wrong_type():
    class _BrokenMarketResearchStage:
        def run(self, opportunity):
            return "not a MarketProfile"

    pipeline = OpportunityPipeline(market_research_stage=_BrokenMarketResearchStage())

    with pytest.raises(OpportunityPipelineError, match="MarketResearchStage"):
        pipeline.run(_opportunity())


def test_pipeline_raises_when_source_collection_returns_wrong_type():
    class _BrokenSourceCollectionStage:
        def run(self, opportunity):
            return {"not": "an opportunity"}

    pipeline = OpportunityPipeline(source_collection_stage=_BrokenSourceCollectionStage())

    with pytest.raises(OpportunityPipelineError, match="SourceCollectionStage"):
        pipeline.run(_opportunity())


def test_pipeline_raises_when_investment_memo_stage_returns_wrong_type():
    class _BrokenInvestmentMemoStage:
        def run(self, opportunity, assessment, recommendation):
            return None

    pipeline = OpportunityPipeline(investment_memo_stage=_BrokenInvestmentMemoStage())

    with pytest.raises(OpportunityPipelineError, match="InvestmentMemoStage"):
        pipeline.run(_opportunity())


def test_pipeline_run_is_deterministic_for_placeholder_stages():
    """
    Two placeholder runs on equivalent input should be structurally
    identical apart from the generated_at timestamp — no randomness,
    no hidden state carried between runs.
    """
    pipeline = OpportunityPipeline()

    memo_a = pipeline.run(_opportunity())
    memo_b = pipeline.run(_opportunity())

    assert memo_a.recommendation == memo_b.recommendation
    assert memo_a.assessment.market_profile == memo_b.assessment.market_profile
