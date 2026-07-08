"""
scout_service.py — persistence hook for Scout runs.

Atlas Investment OS. This module runs Scout and persists its evidence.

Layering:
- Repository: SQL only (unchanged)
- Service: Scout execution + persistence + post-processing (THIS FILE)
- Route: calls run_and_persist_scout()

This module does NOT modify scoring, valuation, or Market Capacity logic.
"""

from __future__ import annotations

from typing import Optional

from . import opportunity_records_repository as repo
from .dna.schema import OpportunityDNA
from .scout import Scout, ScoutResult, run_scout, scout_result_to_dict

# NEW: Scout Health Engine (non-breaking add-on layer)
from .scout_health_engine import ScoutHealthEngine


# ---------------------------------------------------------------------------
# MAIN SCOUT PIPELINE (PERSISTED)
# ---------------------------------------------------------------------------
def run_and_persist_scout(
    opportunity_id: int,
    niche_name: str,
    dna: OpportunityDNA,
    ctx: dict,
    scout: Optional[Scout] = None,
    db_path=None
) -> tuple[int, ScoutResult]:

    scout_run_id = repo.create_scout_run(opportunity_id, db_path=db_path)

    try:
        result = run_scout(niche_name, dna, ctx, scout=scout)

    except Exception as e:
        repo.finish_scout_run(
            scout_run_id,
            status="failed",
            error=str(e),
            db_path=db_path
        )
        raise

    # -----------------------------------------------------------------------
    # ORIGINAL PERSISTENCE LOGIC (UNCHANGED)
    # -----------------------------------------------------------------------

    verified_business_count = (
        int(result.business.business_count.value)
        if result.business.business_count.is_verified else None
    )

    repo.finish_scout_run(
        scout_run_id,
        status="complete",
        verified_business_count=verified_business_count,
        verified_competitor_count=None,
        findings=scout_result_to_dict(result),
        db_path=db_path
    )

    # -----------------------------------------------------------------------
    # NEW: SCOUT HEALTH ENGINE (SAFE ADD-ON LAYER)
    # -----------------------------------------------------------------------

    try:
        health_engine = ScoutHealthEngine()

        scout_health = health_engine.compute(
            result,
            opportunity_id=opportunity_id
        )

        # Attach metadata (DO NOT BREAK existing schema)
        result.health_score = scout_health.health_score
        result.health_breakdown = {
            "total_fields": scout_health.total_fields,
            "verified_fields": scout_health.verified_fields,
            "estimated_fields": scout_health.estimated_fields,
            "unknown_fields": scout_health.unknown_fields,
            "provider_verified_ratio": scout_health.provider_verified_ratio,
            "completeness_ratio": scout_health.completeness_ratio,
        }

    except Exception:
        # NEVER break Scout if health layer fails
        result.health_score = None
        result.health_breakdown = None

    return scout_run_id, result


# ---------------------------------------------------------------------------
# BACKWARD COMPATIBLE WRAPPER (UNCHANGED BEHAVIOR)
# ---------------------------------------------------------------------------
def get_scout_evidence_for_market_capacity(
    niche_name: str,
    dna: OpportunityDNA,
    ctx: dict,
    scout: Optional[Scout] = None
):
    result = run_scout(niche_name, dna, ctx, scout=scout)
    return result.to_market_capacity_overlay()