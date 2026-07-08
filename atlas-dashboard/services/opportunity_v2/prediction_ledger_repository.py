"""
prediction_ledger_repository.py — persistence for the Prediction Ledger.

Atlas Investment OS, Phase 1 (Prediction Ledger only — no calibration
logic, no ML, no weight adjustment). Every DecisionResult Atlas produces
gets one immutable prediction snapshot, recorded here, for future
calibration once enough live outcomes exist.

Design rules for this module (identical to opportunity_records_repository.py):
    - ZERO scoring logic. Reads / writes only.
    - ZERO Flask coupling. Plain arguments in, plain dicts out.
    - Idempotent: one snapshot per decision_id, enforced at the database
      level via a UNIQUE constraint and defended in code with an
      INSERT OR IGNORE + lookup pattern, so calling save_prediction_snapshot
      twice for the same decision_id is always a no-op on the second call.

This module does NOT modify opportunity_records_repository.py. It imports
its connection helper and serializer to guarantee identical connection
handling (PRAGMA foreign_keys, row_factory, commit-on-success) without
duplicating that logic or touching the existing, working file.

Public API:
    init_schema(db_path=None)
    save_prediction_snapshot(opportunity_id, decision_id, dna_slug,
                              opportunity_name, decision_result,
                              market_capacity_score=None,
                              model_version=DEFAULT_MODEL_VERSION,
                              db_path=None) -> int
    get_prediction_snapshot(decision_id, db_path=None) -> dict | None
    list_prediction_snapshots(opportunity_id, db_path=None) -> list[dict]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .opportunity_records_repository import get_connection, _serialize, _row

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "models" / "prediction_ledger_schema.sql"

# Static model version tag for this phase. No calibration or weight
# adjustment exists yet — this constant exists solely so every snapshot
# records which model/weight generation produced it, which is the
# prerequisite for comparing predictions across future model revisions.
DEFAULT_MODEL_VERSION = "atlas-investment-os-v1"


def init_schema(db_path=None):
    """Create the prediction_ledger table if it doesn't exist. Safe to
    call repeatedly; matches the init_schema pattern used elsewhere."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())


# ---------------------------------------------------------------------------
# Snapshot lifecycle
# ---------------------------------------------------------------------------

def save_prediction_snapshot(opportunity_id: int,
                               decision_id: int,
                               dna_slug: str,
                               opportunity_name: str,
                               decision_result,             # Pydantic DecisionResult
                               market_capacity_score: Optional[float] = None,
                               model_version: str = DEFAULT_MODEL_VERSION,
                               db_path=None) -> int:
    """
    Record an immutable prediction snapshot for a decision.

    Idempotent: if a snapshot already exists for this decision_id, no
    new row is written and the existing snapshot's id is returned
    unchanged. This makes it safe to call from a route hook even if a
    decision is somehow saved more than once, or if this function is
    invoked more than once for the same decision_id.

    decision_result must expose (all already present on DecisionResult,
    all with safe defaults so older/partial results don't raise):
        data_quality, recommendation, confidence_score,
        estimated_revenue_low, likely_monthly_revenue, estimated_revenue_high,
        startup_cost, maintenance_cost, build_score, risk_score,
        investment_grade, estimated_exit_value, five_year_revenue_potential,
        valuation_explanation (dict | None)

    market_capacity_score: optional — pass ctx.get("market_capacity_score")
    when the caller has run Market Capacity for this opportunity; None
    when it hasn't (older heuristic-only pipeline runs, or Market Capacity
    not yet wired into this call site). Stored as NULL, not fabricated.
    """
    explanation = getattr(decision_result, "valuation_explanation", None)
    explanation_json = _serialize(explanation) if explanation is not None else None

    with get_connection(db_path) as conn:
        # Idempotency guard: check for an existing snapshot first so the
        # function is a safe no-op on repeat calls for the same decision.
        existing = conn.execute(
            "SELECT id FROM prediction_ledger WHERE decision_id=?",
            (decision_id,)).fetchone()
        if existing:
            return existing["id"]

        cur = conn.execute(
            """INSERT OR IGNORE INTO prediction_ledger
               (opportunity_id, decision_id, dna_slug, opportunity_name,
                data_quality, recommendation, confidence_score,
                estimated_revenue_low, likely_monthly_revenue,
                estimated_revenue_high, startup_cost, maintenance_cost,
                build_score, risk_score, investment_grade,
                estimated_exit_value, five_year_revenue_potential,
                market_capacity_score, valuation_explanation_json,
                model_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (opportunity_id, decision_id, dna_slug, opportunity_name,
             decision_result.data_quality,
             decision_result.recommendation,
             decision_result.confidence_score,
             getattr(decision_result, "estimated_revenue_low", None),
             getattr(decision_result, "likely_monthly_revenue", None),
             getattr(decision_result, "estimated_revenue_high", None),
             getattr(decision_result, "startup_cost", None),
             getattr(decision_result, "maintenance_cost", None),
             getattr(decision_result, "build_score", None),
             getattr(decision_result, "risk_score", None),
             getattr(decision_result, "investment_grade", None),
             getattr(decision_result, "estimated_exit_value", None),
             getattr(decision_result, "five_year_revenue_potential", None),
             market_capacity_score,
             explanation_json,
             model_version))

        if cur.lastrowid:
            return cur.lastrowid

        # INSERT OR IGNORE silently no-opped (a concurrent writer won the
        # UNIQUE constraint race between our existence check and our
        # insert) — look the row up rather than raising.
        row = conn.execute(
            "SELECT id FROM prediction_ledger WHERE decision_id=?",
            (decision_id,)).fetchone()
        return row["id"] if row else None


def get_prediction_snapshot(decision_id: int, db_path=None) -> dict | None:
    """Return the prediction snapshot for a decision_id, or None if no
    snapshot has been recorded yet (e.g. decisions saved before Phase 1
    shipped — this is expected and not an error)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM prediction_ledger WHERE decision_id=?",
            (decision_id,)).fetchone()
        return _row(row)


def list_prediction_snapshots(opportunity_id: int, db_path=None) -> list[dict]:
    """All prediction snapshots for an opportunity, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM prediction_ledger
               WHERE opportunity_id=?
               ORDER BY created_at DESC""",
            (opportunity_id,)).fetchall()
        return [_row(r) for r in rows]
