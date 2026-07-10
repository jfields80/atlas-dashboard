"""
atlas/services/opportunity_intelligence/stages.py

AES-012A — Opportunity Intelligence Engine v2 Foundation.

Defines the pipeline's stage CONTRACTS only — no intelligence, no AI
calls, no web requests, no scoring formulas. Each stage is a
`typing.Protocol` (structural typing: any object with a matching
`run()` method satisfies it, no inheritance required) describing a
typed input -> typed output transformation, plus one placeholder
implementation that returns an honestly-UNKNOWN-tagged default output.

Future AI employees (Market Research Analyst, Competition Analyst,
Revenue Analyst, Investment Analyst, Autonomous Investment Committee,
etc.) plug in by implementing the same Protocol and being passed into
OpportunityPipeline's constructor (services/opportunity_intelligence/
opportunity_pipeline.py) — no change to this module or the pipeline's
orchestration is required to swap a placeholder for a real
implementation.

Independent package: no Flask, no repositories, no
services.opportunity_v2, no orchestrator, no Learning Memory, no AI
SDKs, no scraping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Protocol

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


class StageName(str, Enum):
    SOURCE_COLLECTION = "source_collection"
    MARKET_RESEARCH = "market_research"
    OPPORTUNITY_CLASSIFICATION = "opportunity_classification"
    COMPETITION_ANALYSIS = "competition_analysis"
    REVENUE_ANALYSIS = "revenue_analysis"
    INVESTMENT_ANALYSIS = "investment_analysis"
    COMMITTEE_RECOMMENDATION = "committee_recommendation"
    INVESTMENT_MEMO = "investment_memo"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Stage contracts (Protocols) — structural typing, no base class required.
# ---------------------------------------------------------------------------


class SourceCollectionStageProtocol(Protocol):
    def run(self, opportunity: Opportunity) -> Opportunity: ...


class MarketResearchStageProtocol(Protocol):
    def run(self, opportunity: Opportunity) -> MarketProfile: ...


class OpportunityClassificationStageProtocol(Protocol):
    def run(self, opportunity: Opportunity, market_profile: MarketProfile) -> OpportunityClassification: ...


class CompetitionAnalysisStageProtocol(Protocol):
    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
    ) -> CompetitionProfile: ...


class RevenueAnalysisStageProtocol(Protocol):
    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
        competition_profile: CompetitionProfile,
    ) -> RevenueProfile: ...


class InvestmentAnalysisStageProtocol(Protocol):
    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
        competition_profile: CompetitionProfile,
        revenue_profile: RevenueProfile,
    ) -> InvestmentProfile: ...


class CommitteeRecommendationStageProtocol(Protocol):
    def run(self, assessment: OpportunityAssessment) -> Recommendation: ...


class InvestmentMemoStageProtocol(Protocol):
    def run(
        self,
        opportunity: Opportunity,
        assessment: OpportunityAssessment,
        recommendation: Recommendation,
    ) -> InvestmentMemo: ...


# ---------------------------------------------------------------------------
# Placeholder implementations — no intelligence, honest UNKNOWN outputs.
# ---------------------------------------------------------------------------


class PlaceholderSourceCollectionStage:
    """Passes the Opportunity through unchanged. A future Scout/source
    integration would enrich `opportunity.source` here."""

    name = StageName.SOURCE_COLLECTION

    def run(self, opportunity: Opportunity) -> Opportunity:
        return opportunity


class PlaceholderMarketResearchStage:
    """No market research implemented yet — future Market Research Analyst."""

    name = StageName.MARKET_RESEARCH

    def run(self, opportunity: Opportunity) -> MarketProfile:
        return MarketProfile()


class PlaceholderOpportunityClassificationStage:
    """No classification implemented yet — future Opportunity Classification Engine."""

    name = StageName.OPPORTUNITY_CLASSIFICATION

    def run(self, opportunity: Opportunity, market_profile: MarketProfile) -> OpportunityClassification:
        return OpportunityClassification()


class PlaceholderCompetitionAnalysisStage:
    """No competition analysis implemented yet — future Competition Analyst."""

    name = StageName.COMPETITION_ANALYSIS

    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
    ) -> CompetitionProfile:
        return CompetitionProfile()


class PlaceholderRevenueAnalysisStage:
    """No revenue analysis implemented yet — future Revenue Analyst."""

    name = StageName.REVENUE_ANALYSIS

    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
        competition_profile: CompetitionProfile,
    ) -> RevenueProfile:
        return RevenueProfile()


class PlaceholderInvestmentAnalysisStage:
    """No investment analysis implemented yet — future Investment Analyst."""

    name = StageName.INVESTMENT_ANALYSIS

    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
        competition_profile: CompetitionProfile,
        revenue_profile: RevenueProfile,
    ) -> InvestmentProfile:
        return InvestmentProfile()


class PlaceholderCommitteeRecommendationStage:
    """No committee logic implemented yet — future Autonomous Investment Committee."""

    name = StageName.COMMITTEE_RECOMMENDATION

    def run(self, assessment: OpportunityAssessment) -> Recommendation:
        return Recommendation(
            decision="UNASSESSED",
            confidence=0.0,
            rationale="Placeholder stage — no committee logic implemented yet (AES-012A foundation).",
        )


class PlaceholderInvestmentMemoStage:
    """Assembles the final InvestmentMemo shell — no narrative generation yet."""

    name = StageName.INVESTMENT_MEMO

    def run(
        self,
        opportunity: Opportunity,
        assessment: OpportunityAssessment,
        recommendation: Recommendation,
    ) -> InvestmentMemo:
        return InvestmentMemo(
            opportunity=opportunity,
            assessment=assessment,
            recommendation=recommendation,
            summary="Placeholder memo — AES-012A foundation only, no intelligence implemented.",
            generated_at=_now(),
        )


def ordered_stage_names() -> List[StageName]:
    """The pipeline's authoritative stage order."""
    return [
        StageName.SOURCE_COLLECTION,
        StageName.MARKET_RESEARCH,
        StageName.OPPORTUNITY_CLASSIFICATION,
        StageName.COMPETITION_ANALYSIS,
        StageName.REVENUE_ANALYSIS,
        StageName.INVESTMENT_ANALYSIS,
        StageName.COMMITTEE_RECOMMENDATION,
        StageName.INVESTMENT_MEMO,
    ]
