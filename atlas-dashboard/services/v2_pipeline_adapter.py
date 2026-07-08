"""
atlas/services/v2_pipeline_adapter.py

Adapter facade between the v3 Pipeline Runner and the frozen v2 engine chain.

Purpose:
  The v3 Pipeline Runner calls `run_v2_pipeline()` as a single unit.
  This file is the ONLY place that knows about v2 engine internals.
  Everything outside this file treats v2 as a black box that accepts
  an opportunity_id + db connection and returns a V2PipelineResult.

Integration contract:
  - Input:  opportunity_id (str), conn (sqlite3.Connection)
  - Output: V2PipelineResult
  - The v2 engines are NEVER modified. Only import paths change.
  - If the v2 engines are not present (e.g. during isolated v3 testing),
    this adapter raises ImportError with a clear message pointing to
    the v2 codebase.

Shim behaviour:
  In the current repository, the real v2 engine chain (Scout,
  MarketCapacity, OpportunityScorer, ValuationEngine, BusinessArchitect)
  lives under a separate module tree. This adapter imports them by their
  actual paths. If those paths change, update the imports below — do NOT
  change anything else in this file or anywhere in the v3 codebase.

  For testing without a live v2 codebase, set the environment variable
  ATLAS_V2_STUB=1 to activate the deterministic test stub at the bottom
  of this file.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from services.v2_types import (
    DecisionResult,
    V2PipelineResult,
    ValuationSummary,
    ScoreBreakdown,
)


def run_v2_pipeline(
    opportunity_id: str,
    conn: sqlite3.Connection,
) -> V2PipelineResult:
    """
    Execute the frozen v2 pipeline for the given opportunity.

    Returns a V2PipelineResult containing the DecisionResult and
    intermediate stage outputs needed by v3 engines.

    Raises:
        ValueError: if opportunity_id is not found in the database.
        RuntimeError: if the v2 pipeline fails for any reason.
    """
    if os.environ.get("ATLAS_V2_STUB") == "1":
        return _stub_v2_pipeline(opportunity_id, conn)

    return _real_v2_pipeline(opportunity_id, conn)


# ---------------------------------------------------------------------------
# Real v2 integration
# ---------------------------------------------------------------------------

def _real_v2_pipeline(
    opportunity_id: str,
    conn: sqlite3.Connection,
) -> V2PipelineResult:
    """
    Calls the actual frozen v2 engine chain.

    Import paths reference the v2 module structure.  Update these paths
    if the v2 package layout changes — change nothing else.
    """
    try:
        # These imports will resolve when this adapter runs inside the full
        # Atlas codebase that includes the v2 engine tree.
        from opportunity_records_repository import get_opportunity_by_id  # type: ignore[import]
        from scout_service import run_scout                                # type: ignore[import]
        from market_capacity_engine import run_market_capacity             # type: ignore[import]
        from opportunity_scorer import score_opportunity                   # type: ignore[import]
        from valuation_engine import run_valuation                         # type: ignore[import]
        from business_architect import make_decision                       # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "v2 engine modules not found on the import path. "
            "Run with ATLAS_V2_STUB=1 for isolated v3 testing, or ensure the "
            "v2 module tree is importable. "
            f"Original error: {exc}"
        ) from exc

    opp = get_opportunity_by_id(conn, opportunity_id)
    if opp is None:
        raise ValueError(f"Opportunity not found: {opportunity_id!r}")

    scout_result     = run_scout(opp, conn)
    capacity_result  = run_market_capacity(opp, scout_result)
    score_result     = score_opportunity(opp, scout_result, capacity_result)
    valuation_result = run_valuation(opp, score_result, capacity_result)
    decision         = make_decision(opp, valuation_result, score_result)

    core = DecisionResult(
        opportunity_id=opportunity_id,
        niche_slug=opp.get("niche_slug", ""),
        decision=decision.recommendation,
        confidence=decision.confidence,
        honest_wall_applied=decision.honest_wall_applied,
        rationale=decision.rationale,
        valuation=ValuationSummary(
            conservative_monthly_revenue=valuation_result.conservative_monthly,
            likely_monthly_revenue=valuation_result.likely_monthly,
            aggressive_monthly_revenue=valuation_result.aggressive_monthly,
            five_year_potential_usd=valuation_result.five_year_potential,
            exit_value_usd=valuation_result.exit_value,
            build_score=valuation_result.build_score,
            risk_score=valuation_result.risk_score,
            investment_grade=valuation_result.investment_grade,
            explanation=valuation_result.explanation or {},
        ),
        score_breakdown=ScoreBreakdown(
            total_score=score_result.total_score,
            components=score_result.components or {},
            market_capacity_score=score_result.market_capacity_score,
        ),
        primary_category=opp.get("primary_category", "unknown"),
        geographic_scope=opp.get("geographic_scope", "national"),
        market_ceiling_monthly_usd=capacity_result.ceiling_monthly_usd,
        scout_evidence_summary=scout_result.summary or {},
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return V2PipelineResult(
        decision_result=core,
        market_capacity_result={
            "ceiling_monthly_usd": capacity_result.ceiling_monthly_usd,
            "confidence": capacity_result.confidence,
        },
        scorer_result={
            "total_score": score_result.total_score,
            "components": score_result.components or {},
        },
        raw_scout_evidence=scout_result.raw_evidence or {},
    )


# ---------------------------------------------------------------------------
# Deterministic test stub
# ---------------------------------------------------------------------------

def _stub_v2_pipeline(
    opportunity_id: str,
    conn: sqlite3.Connection,
) -> V2PipelineResult:
    """
    Deterministic stub for isolated v3 testing.
    Active when ATLAS_V2_STUB=1.

    Returns a realistic V2PipelineResult without calling any v2 engines.
    All values are fixed — same input always produces same output.
    """
    # Pull category + scope from DB if opportunity row exists; otherwise use defaults.
    row = None
    try:
        cursor = conn.execute(
            "SELECT primary_category, geographic_scope, niche_slug "
            "FROM opportunity_records WHERE id = ?",
            (opportunity_id,),
        )
        row = cursor.fetchone()
    except Exception:
        pass  # table may not exist in isolated test DB

    category = dict(row)["primary_category"] if row else "pet"
    scope    = dict(row)["geographic_scope"]  if row else "national"
    slug     = dict(row)["niche_slug"]        if row else opportunity_id

    # Deterministic stub values
    ceiling = 4_200.0
    total_score = 0.62
    conservative = 350.0
    likely = 650.0
    aggressive = 1_100.0

    core = DecisionResult(
        opportunity_id=opportunity_id,
        niche_slug=slug,
        decision="TEST",
        confidence=0.42,            # below honest wall cap — ESTIMATED data
        honest_wall_applied=True,
        rationale=(
            "Stub: estimated-data honest wall applied. "
            "Market shows viable signal; verification required for BUILD."
        ),
        valuation=ValuationSummary(
            conservative_monthly_revenue=conservative,
            likely_monthly_revenue=likely,
            aggressive_monthly_revenue=aggressive,
            five_year_potential_usd=likely * 12 * 3.5,
            exit_value_usd=likely * 32,
            build_score=0.64,
            risk_score=0.38,
            investment_grade="B",
            explanation={
                "conservative_basis": "Low-end organic traffic scenario",
                "likely_basis": "Moderate listing + affiliate mix",
                "aggressive_basis": "Full monetization at category ceiling",
            },
        ),
        score_breakdown=ScoreBreakdown(
            total_score=total_score,
            components={
                "demand_score":      {"raw": 0.65, "weight": 0.20, "contribution": 0.13},
                "competition_score": {"raw": 0.58, "weight": 0.15, "contribution": 0.087},
                "monetization_score":{"raw": 0.70, "weight": 0.15, "contribution": 0.105},
                "market_capacity":   {"raw": 0.55, "weight": 0.40, "contribution": 0.22},
                "execution_score":   {"raw": 0.50, "weight": 0.10, "contribution": 0.05},
            },
            market_capacity_score=0.55,
        ),
        primary_category=category,
        geographic_scope=scope,
        market_ceiling_monthly_usd=ceiling,
        scout_evidence_summary={
            "business_intel": "ESTIMATED",
            "competition_intel": "ESTIMATED",
            "monetization_intel": "ESTIMATED",
        },
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return V2PipelineResult(
        decision_result=core,
        market_capacity_result={
            "ceiling_monthly_usd": ceiling,
            "confidence": 0.45,
        },
        scorer_result={
            "total_score": total_score,
            "components": core.score_breakdown.components,
        },
        raw_scout_evidence=core.scout_evidence_summary,
    )


# ---------------------------------------------------------------------------
# Compatibility wrapper
#
# Thin class shim for older call sites / tests that expect a
# V2PipelineAdapter class instance rather than the module-level
# run_v2_pipeline() function. Contains zero business logic and does
# NOT touch the real v2 engine chain — it delegates directly to
# run_v2_pipeline() above, which is itself only a pass-through to
# the frozen v2 engines (or the deterministic stub under
# ATLAS_V2_STUB=1). The functional API remains canonical.
# ---------------------------------------------------------------------------

class V2PipelineAdapter:
    """
    Compatibility wrapper around the module-level run_v2_pipeline() function.

    Usage:
        adapter = V2PipelineAdapter()
        result = adapter.run(opportunity_id, conn)

    This class holds no state and performs no logic of its own —
    it exists solely so that code written against a class-based
    interface continues to work unchanged. It never modifies the v2
    engine chain; that logic lives entirely in the frozen v2 modules
    imported by run_v2_pipeline() / _real_v2_pipeline() above.
    """

    def run(
        self,
        opportunity_id: str,
        conn: sqlite3.Connection,
    ) -> V2PipelineResult:
        return run_v2_pipeline(opportunity_id, conn)
