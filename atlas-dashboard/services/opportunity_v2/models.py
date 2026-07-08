"""
models.py — DecisionResult: the Business Architect's structured output.

Pydantic model for the decision layer. Does not replace OpportunityDNA.

Backward compatibility: all new fields carry defaults so existing
result_json rows in the database validate without error.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DecisionResult(BaseModel):
    # ── Core verdict ───────────────────────────────────────────────────────────
    recommendation: Literal["BUILD", "TEST", "DEFER", "REJECT"]
    confidence_score: float = Field(
        ..., ge=0, le=100,
        description=(
            "Revenue-confidence estimate. Heuristic mode is capped at 45% "
            "because no live market data has been verified yet."))
    conviction_thesis: str
    data_quality: Literal["heuristic", "verified", "mixed"]
    reasoning: List[str]

    # ── Founder unit economics ─────────────────────────────────────────────────
    startup_cost: float
    maintenance_cost: float
    estimated_revenue_low: float    # conservative monthly
    estimated_revenue_high: float   # aggressive monthly
    automation_percentage: float
    time_to_first_revenue_days: int

    # ── Revenue scenarios (named) ──────────────────────────────────────────────
    conservative_monthly_revenue: float = 0.0
    likely_monthly_revenue: float = 0.0
    aggressive_monthly_revenue: float = 0.0

    # Backward-compat aliases
    revenue_midpoint: float = 0.0
    revenue_likely: float = 0.0

    # ── Venture projections ────────────────────────────────────────────────────
    five_year_revenue_potential: float = 0.0
    estimated_exit_value: float = 0.0

    # ── Scoring ───────────────────────────────────────────────────────────────
    roi_months: float = 0.0
    build_score: float = 0.0
    risk_score: float = 0.0
    investment_grade: str = ""
    monetization_diversity_score: float = 0.0

    # ── Strategic vectors ─────────────────────────────────────────────────────
    business_model: str
    moat: str
    portfolio_fit: str
    why_this_market: str
    why_now: str

    # ── Tactical execution ────────────────────────────────────────────────────
    what_to_build_first: List[str]
    what_to_ignore: List[str]
    next_steps: List[str]

    # ── Roadmap ───────────────────────────────────────────────────────────────
    roadmap_30: str
    roadmap_90: str
    roadmap_365: str

    # ── Audit / under-the-hood ────────────────────────────────────────────────
    internal_affinity_score: float
    market_gravity_intensity: str
    commercial_intent_level: str
    core_pages_to_launch_count: int
    related_opportunities: List[Dict[str, str]]
    warnings: List[str]

    # ── Per-stream breakdown ───────────────────────────────────────────────────
    revenue_streams: Optional[List[Dict]] = None

    # ── Explainable valuation audit trail ─────────────────────────────────────
    # Stored as a plain dict so it serializes cleanly to JSON in result_json.
    # The template can render any subset of this without touching routes.
    # None if the valuation engine did not produce an explanation
    # (e.g. legacy records stored before this field existed).
    valuation_explanation: Optional[Dict[str, Any]] = None
