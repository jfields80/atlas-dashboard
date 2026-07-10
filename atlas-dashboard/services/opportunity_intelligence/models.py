"""
atlas/services/opportunity_intelligence/models.py

AES-012A — Opportunity Intelligence Engine v2 Foundation.

Strongly typed domain models for the future Opportunity Intelligence
pipeline. These models carry NO intelligence of their own — no
scoring formulas, no revenue estimation, no AI calls. Every "profile"
model defaults to an honestly-tagged UNKNOWN state (matching Atlas's
honesty-layer convention used elsewhere, e.g.
engines/directory_ingestion's TaggedValue / DataVerificationTag) so a
not-yet-implemented stage's placeholder output never looks like real
data.

Independent package: this module imports nothing beyond pydantic and
the Python standard library. No Flask, no repositories, no
services.opportunity_v2, no orchestrator, no Learning Memory.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

UNKNOWN = "UNKNOWN"


class OpportunitySource(BaseModel):
    """Where an opportunity candidate came from."""

    source_type: str = UNKNOWN
    source_name: str = ""
    discovered_at: str = ""
    notes: str = ""


class Opportunity(BaseModel):
    """The raw candidate idea the pipeline evaluates."""

    opportunity_id: str
    name: str
    niche: str
    description: str = ""
    source: OpportunitySource = Field(default_factory=OpportunitySource)
    geographic_scope: str = "national"
    tags: List[str] = Field(default_factory=list)


class MarketProfile(BaseModel):
    """
    Output contract for the Market Research stage.

    market_name/primary_category/primary_geography/market_scope
    (AES-012B): deterministic facts the Market Research Analyst infers
    directly from the Opportunity's own name/niche text — never from
    external data. All four default to "UNKNOWN", matching every other
    field on this model, so the placeholder stage (AES-012A) and any
    future stage that genuinely cannot infer them are indistinguishable
    from "not yet analyzed."
    """

    total_addressable_market_usd: Optional[float] = None
    market_size_notes: str = ""
    demand_signals: List[str] = Field(default_factory=list)
    data_confidence: str = UNKNOWN
    market_name: str = UNKNOWN
    primary_category: str = UNKNOWN
    primary_geography: str = UNKNOWN
    market_scope: str = UNKNOWN


class OpportunityClassification(BaseModel):
    """
    Output contract for the Opportunity Classification stage
    (AES-012C). Enriches an Opportunity + MarketProfile into a
    structured business profile — industry, audience, business type,
    commercial intent, market vertical, and business model — for
    downstream analysts to consume. Every field defaults to "UNKNOWN";
    nothing here is fabricated when the classifier has no real signal
    to work from.
    """

    industry: str = UNKNOWN
    audience: str = UNKNOWN
    business_type: str = UNKNOWN
    commercial_intent: str = UNKNOWN
    market_vertical: str = UNKNOWN
    business_model: str = UNKNOWN
    confidence: str = UNKNOWN


class CompetitionProfile(BaseModel):
    """
    Output contract for the Competition Analysis stage.

    competitor_archetype/market_fragmentation/likely_competitor_type/
    competitive_risk/competition_scope (AES-012D): deterministic facts
    the Competition Analyst infers from the already-derived
    MarketProfile/OpportunityClassification structured outputs — never
    from external data. All default to "UNKNOWN". The ticket's
    suggested "confidence" field reuses the existing data_confidence
    field below rather than duplicating it.
    """

    competitor_count: Optional[int] = None
    competitor_names: List[str] = Field(default_factory=list)
    competitive_intensity: str = UNKNOWN
    barriers_to_entry: List[str] = Field(default_factory=list)
    data_confidence: str = UNKNOWN
    competitor_archetype: str = UNKNOWN
    market_fragmentation: str = UNKNOWN
    likely_competitor_type: str = UNKNOWN
    competitive_risk: str = UNKNOWN
    competition_scope: str = UNKNOWN


class RevenueProfile(BaseModel):
    """
    Output contract for the Revenue Analysis stage.

    primary_revenue_model/secondary_revenue_models/
    recurring_revenue_potential/transaction_revenue_potential/
    monetization_strength/revenue_scalability (AES-012E): deterministic
    facts the Revenue Analyst infers from the already-derived
    MarketProfile/OpportunityClassification/CompetitionProfile
    structured outputs. These characterize HOW an opportunity could
    monetize (mechanism), never HOW MUCH it could earn — no dollar
    figures, projections, or estimates live on these fields. All
    default to "UNKNOWN" (secondary_revenue_models defaults to an
    empty list). Reuses the existing data_confidence field for
    signal-quality confidence rather than duplicating it.
    """

    estimated_monthly_revenue_usd: Optional[float] = None
    revenue_model_notes: str = ""
    monetization_signals: List[str] = Field(default_factory=list)
    data_confidence: str = UNKNOWN
    primary_revenue_model: str = UNKNOWN
    secondary_revenue_models: List[str] = Field(default_factory=list)
    recurring_revenue_potential: str = UNKNOWN
    transaction_revenue_potential: str = UNKNOWN
    monetization_strength: str = UNKNOWN
    revenue_scalability: str = UNKNOWN


class InvestmentProfile(BaseModel):
    """
    Output contract for the Investment Analysis stage.

    market_attractiveness/revenue_attractiveness/competitive_position/
    execution_complexity/investment_risk/investment_score (AES-012F):
    deterministic facts the Investment Analyst infers from the
    already-derived MarketProfile/OpportunityClassification/
    CompetitionProfile/RevenueProfile structured outputs. These
    characterize investment ATTRACTIVENESS AND RISK STRUCTURE, never a
    final INVEST/REJECT recommendation and never a financial
    projection — no dollar figures live on these fields beyond the
    pre-existing, still-unpopulated estimated_* fields below. All
    string fields default to "UNKNOWN"; investment_score defaults to
    None (unscored) rather than 0 (a real, if minimal, score). Reuses
    the existing data_confidence field for signal-quality confidence
    rather than duplicating it.
    """

    estimated_build_cost_usd: Optional[float] = None
    estimated_payback_months: Optional[float] = None
    risk_notes: List[str] = Field(default_factory=list)
    data_confidence: str = UNKNOWN
    market_attractiveness: str = UNKNOWN
    revenue_attractiveness: str = UNKNOWN
    competitive_position: str = UNKNOWN
    execution_complexity: str = UNKNOWN
    investment_risk: str = UNKNOWN
    investment_score: Optional[int] = None


class OpportunityAssessment(BaseModel):
    """Aggregated output of the Market/Classification/Competition/Revenue/Investment stages."""

    opportunity: Opportunity
    market_profile: Optional[MarketProfile] = None
    classification: Optional[OpportunityClassification] = None
    competition_profile: Optional[CompetitionProfile] = None
    revenue_profile: Optional[RevenueProfile] = None
    investment_profile: Optional[InvestmentProfile] = None


class Recommendation(BaseModel):
    """Output contract for the Committee Recommendation stage."""

    decision: str = "UNASSESSED"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    rationale: str = ""


class InvestmentMemo(BaseModel):
    """Final pipeline output."""

    opportunity: Opportunity
    assessment: OpportunityAssessment
    recommendation: Recommendation
    summary: str = ""
    generated_at: str = ""
