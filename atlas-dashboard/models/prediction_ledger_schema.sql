-- Prediction Ledger schema — Atlas Investment OS, Phase 1.
--
-- Purpose: every DecisionResult Atlas produces gets a permanent, immutable
-- prediction snapshot. This is the sole prerequisite for the future
-- Learning Loop (Scout verification -> build decision -> actual project
-- performance -> model calibration). No calibration logic exists yet —
-- this schema only captures what the model believed and why, at the
-- moment it believed it.
--
-- Idempotent: safe to run repeatedly alongside existing Atlas tables.
-- One row per decision_id, enforced by the UNIQUE constraint below.
--
-- This file is additive only. It does not alter opportunity_records_schema.sql
-- or any existing table.

CREATE TABLE IF NOT EXISTS prediction_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity — links this snapshot back to the opportunity and the
    -- exact decision it was produced from.
    opportunity_id INTEGER NOT NULL,
    decision_id INTEGER NOT NULL,
    dna_slug TEXT NOT NULL,
    opportunity_name TEXT NOT NULL,

    -- Evidence quality at prediction time — the honest wall, snapshotted.
    data_quality TEXT NOT NULL,                 -- heuristic | verified | mixed

    -- Core verdict
    recommendation TEXT NOT NULL,               -- BUILD | TEST | DEFER | REJECT
    confidence_score REAL NOT NULL,

    -- Revenue scenarios
    estimated_revenue_low REAL,
    likely_monthly_revenue REAL,
    estimated_revenue_high REAL,

    -- Economics
    startup_cost REAL,
    maintenance_cost REAL,

    -- Scoring
    build_score REAL,
    risk_score REAL,
    investment_grade TEXT,

    -- Venture projections
    estimated_exit_value REAL,
    five_year_revenue_potential REAL,

    -- Investment OS field — optional because Market Capacity may not have
    -- run for every decision yet (older heuristic-only pipeline runs).
    market_capacity_score REAL,

    -- Full audit trail, snapshotted verbatim so it can be replayed even if
    -- valuation_engine.py's formulas change later.
    valuation_explanation_json TEXT,

    -- Which model/weights produced this prediction. A static tag today;
    -- becomes meaningful the moment weights are ever revised, since the
    -- Learning Loop needs to know which model version made which call.
    model_version TEXT NOT NULL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (decision_id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunity_records(id),
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);

CREATE INDEX IF NOT EXISTS idx_prediction_ledger_opp
    ON prediction_ledger(opportunity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prediction_ledger_dna
    ON prediction_ledger(dna_slug);
CREATE INDEX IF NOT EXISTS idx_prediction_ledger_recommendation
    ON prediction_ledger(recommendation);
CREATE INDEX IF NOT EXISTS idx_prediction_ledger_model_version
    ON prediction_ledger(model_version);
