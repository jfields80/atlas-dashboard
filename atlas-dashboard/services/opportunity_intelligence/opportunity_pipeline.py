"""
atlas/services/opportunity_intelligence/opportunity_pipeline.py

AES-012A — Opportunity Intelligence Engine v2 Foundation.

Defines the execution CONTRACT for the Opportunity Intelligence
pipeline: accept an Opportunity, return an InvestmentMemo. Every
stage defaults to its placeholder implementation
(services/opportunity_intelligence/stages.py) — no intelligence, no
AI, no web requests are implemented here or anywhere in this package.

Each stage is independently constructor-injectable, so a future AI
employee (Market Research Analyst, Competition Analyst, Revenue
Analyst, Investment Analyst, Autonomous Investment Committee, etc.)
plugs in by implementing the matching Protocol from stages.py and
passing an instance into OpportunityPipeline(...) — no change to this
orchestration is required.

Responsibilities (and nothing more):
  - Run the 7 stages in their fixed order.
  - Thread each stage's typed output into the next stage's typed input.
  - Reject any stage output that doesn't match its declared type —
    orchestration/validation, not business logic.
  - Assemble the final OpportunityAssessment and InvestmentMemo.

Independent package: no Flask, no repositories, no
services.opportunity_v2, no orchestrator (core/orchestration,
services/orchestrator), no Learning Memory, no background jobs, no
persistence. Usable entirely from plain Python.
"""

from __future__ import annotations

from services.opportunity_intelligence.models import (
    CompetitionProfile,
    InvestmentMemo,
    InvestmentProfile,
    MarketProfile,
    Opportunity,
    OpportunityAssessment,
    Recommendation,
    RevenueProfile,
)
from services.opportunity_intelligence.stages import (
    CommitteeRecommendationStageProtocol,
    CompetitionAnalysisStageProtocol,
    InvestmentAnalysisStageProtocol,
    InvestmentMemoStageProtocol,
    MarketResearchStageProtocol,
    PlaceholderCommitteeRecommendationStage,
    PlaceholderCompetitionAnalysisStage,
    PlaceholderInvestmentAnalysisStage,
    PlaceholderInvestmentMemoStage,
    PlaceholderMarketResearchStage,
    PlaceholderRevenueAnalysisStage,
    PlaceholderSourceCollectionStage,
    RevenueAnalysisStageProtocol,
    SourceCollectionStageProtocol,
)


class OpportunityPipelineError(ValueError):
    """Raised when a stage returns a value that doesn't match its declared contract."""


def _require_type(value: object, expected_type: type, stage_label: str) -> None:
    if not isinstance(value, expected_type):
        raise OpportunityPipelineError(
            f"{stage_label} must return a {expected_type.__name__}, got {value!r}"
        )


class OpportunityPipeline:
    """
    Deterministic orchestrator for the Opportunity Intelligence
    pipeline. Composes 7 independently swappable stages; owns no
    market/competition/revenue/investment/committee logic of its own.

    All stage arguments default to their placeholder implementation —
    the standard AES-012A foundation usage. Pass real implementations
    (matching the Protocols in stages.py) to progressively replace
    placeholders as future AES tickets implement them.
    """

    def __init__(
        self,
        source_collection_stage: SourceCollectionStageProtocol | None = None,
        market_research_stage: MarketResearchStageProtocol | None = None,
        competition_analysis_stage: CompetitionAnalysisStageProtocol | None = None,
        revenue_analysis_stage: RevenueAnalysisStageProtocol | None = None,
        investment_analysis_stage: InvestmentAnalysisStageProtocol | None = None,
        committee_recommendation_stage: CommitteeRecommendationStageProtocol | None = None,
        investment_memo_stage: InvestmentMemoStageProtocol | None = None,
    ) -> None:
        self._source_collection_stage = source_collection_stage or PlaceholderSourceCollectionStage()
        self._market_research_stage = market_research_stage or PlaceholderMarketResearchStage()
        self._competition_analysis_stage = competition_analysis_stage or PlaceholderCompetitionAnalysisStage()
        self._revenue_analysis_stage = revenue_analysis_stage or PlaceholderRevenueAnalysisStage()
        self._investment_analysis_stage = investment_analysis_stage or PlaceholderInvestmentAnalysisStage()
        self._committee_recommendation_stage = committee_recommendation_stage or PlaceholderCommitteeRecommendationStage()
        self._investment_memo_stage = investment_memo_stage or PlaceholderInvestmentMemoStage()

    def run(self, opportunity: Opportunity) -> InvestmentMemo:
        """
        Executes all 7 stages in order and returns the final
        InvestmentMemo. Raises OpportunityPipelineError if any stage
        returns a value that doesn't match its declared contract.
        """
        if not isinstance(opportunity, Opportunity):
            raise OpportunityPipelineError(
                f"opportunity must be an Opportunity, got {opportunity!r}"
            )

        opportunity = self._source_collection_stage.run(opportunity)
        _require_type(opportunity, Opportunity, "SourceCollectionStage")

        market_profile = self._market_research_stage.run(opportunity)
        _require_type(market_profile, MarketProfile, "MarketResearchStage")

        competition_profile = self._competition_analysis_stage.run(opportunity, market_profile)
        _require_type(competition_profile, CompetitionProfile, "CompetitionAnalysisStage")

        revenue_profile = self._revenue_analysis_stage.run(opportunity, market_profile, competition_profile)
        _require_type(revenue_profile, RevenueProfile, "RevenueAnalysisStage")

        investment_profile = self._investment_analysis_stage.run(
            opportunity, market_profile, competition_profile, revenue_profile
        )
        _require_type(investment_profile, InvestmentProfile, "InvestmentAnalysisStage")

        assessment = OpportunityAssessment(
            opportunity=opportunity,
            market_profile=market_profile,
            competition_profile=competition_profile,
            revenue_profile=revenue_profile,
            investment_profile=investment_profile,
        )

        recommendation = self._committee_recommendation_stage.run(assessment)
        _require_type(recommendation, Recommendation, "CommitteeRecommendationStage")

        memo = self._investment_memo_stage.run(opportunity, assessment, recommendation)
        _require_type(memo, InvestmentMemo, "InvestmentMemoStage")

        return memo
