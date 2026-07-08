"""
atlas/core/v2_types.py

Canonical type definitions for v2 pipeline outputs.

These types are FROZEN — they represent the v2 contract.
Do not add scoring logic here.  Do not modify existing fields.
New v3 fields belong in PortfolioDecisionResult (investment_committee.py).

DecisionResult is the output of the v2 BusinessArchitect.
It is embedded verbatim inside PortfolioDecisionResult — never mutated.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# v2 DecisionResult — the authoritative v2 output object
# ---------------------------------------------------------------------------

class ValuationSummary(BaseModel):
    conservative_monthly_revenue: float = 0.0
    likely_monthly_revenue: float = 0.0
    aggressive_monthly_revenue: float = 0.0
    five_year_potential_usd: float = 0.0
    exit_value_usd: float = 0.0
    build_score: float = 0.0
    risk_score: float = 0.0
    investment_grade: str = "UNKNOWN"
    explanation: dict[str, Any] = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    total_score: float = 0.0
    components: dict[str, Any] = Field(default_factory=dict)
    market_capacity_score: float | None = None


class DecisionResult(BaseModel):
    """
    Output of the v2 Business Architect.
    Embedded verbatim in PortfolioDecisionResult — never mutated by v3.
    """
    opportunity_id: str
    niche_slug: str
    decision: str                   # BUILD | TEST | DEFER | REJECT
    confidence: float               # 0.0–1.0
    honest_wall_applied: bool       # True when ESTIMATED data capped confidence
    rationale: str
    valuation: ValuationSummary = Field(default_factory=ValuationSummary)
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    primary_category: str = "unknown"
    geographic_scope: str = "national"
    market_ceiling_monthly_usd: float = 0.0
    scout_evidence_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


# ---------------------------------------------------------------------------
# Minimal v2 pipeline result container (what PipelineRunner gets back
# from the v2 execution path before v3 layers are applied)
# ---------------------------------------------------------------------------

class V2PipelineResult(BaseModel):
    """
    The complete output of the frozen v2 pipeline execution.
    Carries both the final decision and intermediate stage outputs
    for attachment to the v3 run context.
    """
    decision_result: DecisionResult
    market_capacity_result: dict[str, Any] = Field(default_factory=dict)
    scorer_result: dict[str, Any] = Field(default_factory=dict)
    raw_scout_evidence: dict[str, Any] = Field(default_factory=dict)
