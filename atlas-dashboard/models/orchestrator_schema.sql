-- atlas/models/orchestrator_schema.sql
--
-- Reference schema for the AES-006 Atlas Orchestrator.
--
-- This is the documented source-of-truth copy of the DDL. The
-- canonical, executed copy lives inline in
-- repositories/orchestrator_run_repository.py (as _ORCHESTRATOR_DDL),
-- following the same convention as repositories/run_repository.py's
-- _RUNS_DDL. Keep this file in sync if the inline DDL changes.

CREATE TABLE IF NOT EXISTS orchestrator_runs (
    run_id              TEXT PRIMARY KEY,
    pipeline_name        TEXT NOT NULL,
    pipeline_version     TEXT NOT NULL,
    input_hash           TEXT NOT NULL,
    seed_payload_json    TEXT NOT NULL,
    engine_version_set   TEXT NOT NULL,      -- JSON
    status               TEXT NOT NULL DEFAULT 'started',
                                             -- started | complete | failed
    started_at           TEXT NOT NULL,
    completed_at          TEXT,
    failed_at            TEXT,
    failure_reason       TEXT,
    result_json          TEXT               -- serialised final context on success
);

CREATE INDEX IF NOT EXISTS idx_orch_runs_input_hash
    ON orchestrator_runs(input_hash);
-- Intentionally not UNIQUE: force_rerun permits multiple runs with the
-- same input_hash; get_run_by_input_hash returns the most recent one.

CREATE INDEX IF NOT EXISTS idx_orch_runs_pipeline
    ON orchestrator_runs(pipeline_name);

CREATE INDEX IF NOT EXISTS idx_orch_runs_status
    ON orchestrator_runs(status);

CREATE TABLE IF NOT EXISTS orchestrator_stages (
    stage_id        TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES orchestrator_runs(run_id),
    stage_name      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'started',  -- started | complete | failed
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    duration_ms     REAL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_orch_stages_run
    ON orchestrator_stages(run_id);
