"""
prediction_ledger_service.py — thin logic layer for the Prediction Ledger.

Atlas Investment OS, Phase 1. This module contains the (small) amount of
logic needed to turn a freshly-saved DecisionResult into a prediction
snapshot: pulling market_capacity_score out of ctx when it's present, and
choosing the model_version tag. All persistence lives in
prediction_ledger_repository.py; this module owns zero SQL.

Per the existing Atlas layering (Repository -> Service -> Route):
    - Repository: prediction_ledger_repository.py — SQL only.
    - Service:    this module — decides WHAT to persist and WHY.
    - Route:      calls record_prediction() once, after repo.save_decision()
                  has returned a decision_id. No SQL in the route, no
                  logic in the route beyond orchestrating the call.

This module does not change scoring, valuation, or Market Capacity math.
It only reads their already-computed outputs.
"""

from __future__ import annotations

from typing import Optional

from . import prediction_ledger_repository as ledger_repo


def record_prediction(opportunity_id: int,
                        decision_id: int,
                        dna_slug: str,
                        opportunity_name: str,
                        decision_result,          # Pydantic DecisionResult
                        ctx: Optional[dict] = None,
                        db_path=None) -> int:
    """
    Record one immutable prediction snapshot for a saved decision.

    Idempotent: safe to call multiple times for the same decision_id —
    the repository layer guarantees only the first call ever inserts a row.

    ctx: the same context dict passed to BusinessArchitect.generate_decision().
         When Market Capacity has run for this opportunity, ctx carries
         "market_capacity_score" (set by score_opportunity() when a
         MarketCapacityResult was supplied) and that value is snapshotted.
         When Market Capacity has not run, market_capacity_score is stored
         as NULL — never fabricated.

    Returns the prediction_ledger row id (existing or newly created).
    """
    market_capacity_score = (ctx or {}).get("market_capacity_score")

    return ledger_repo.save_prediction_snapshot(
        opportunity_id=opportunity_id,
        decision_id=decision_id,
        dna_slug=dna_slug,
        opportunity_name=opportunity_name,
        decision_result=decision_result,
        market_capacity_score=market_capacity_score,
        model_version=ledger_repo.DEFAULT_MODEL_VERSION,
        db_path=db_path,
    )
