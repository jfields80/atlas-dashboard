"""
atlas/repositories/orchestrator_run_repository.py

Run and stage persistence for the AES-006 Atlas Orchestrator.

A parallel schema to ``repositories/run_repository.py`` rather than a
reuse of it: ``pipeline_runs`` carries NOT NULL ``opportunity_id`` /
``portfolio_snapshot_id`` columns specific to the v3 opportunity
pipeline, which do not generalize to arbitrary orchestrator pipelines.
This module keys runs generically by ``pipeline_name`` instead.

Rules (per Atlas architecture contract):
  - Raw SQL only. No ORM, no SQLAlchemy.
  - Zero business logic.
  - Returns plain dicts or None.
  - Schema is additive — never destructively alters existing tables.
"""

from __future__ import annotations

import sqlite3
from typing import Any


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_ORCHESTRATOR_DDL = """
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
"""


def init_orchestrator_schema(conn: sqlite3.Connection) -> None:
    """Idempotent schema application. Safe to call on every startup."""
    conn.executescript(_ORCHESTRATOR_DDL)
    conn.commit()


# ---------------------------------------------------------------------------
# Run CRUD
# ---------------------------------------------------------------------------

def insert_run(conn: sqlite3.Connection, run: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO orchestrator_runs (
            run_id, pipeline_name, pipeline_version, input_hash,
            seed_payload_json, engine_version_set, status, started_at,
            completed_at, failed_at, failure_reason, result_json
        ) VALUES (
            :run_id, :pipeline_name, :pipeline_version, :input_hash,
            :seed_payload_json, :engine_version_set, :status, :started_at,
            :completed_at, :failed_at, :failure_reason, :result_json
        )
        """,
        run,
    )


def get_run_by_id(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM orchestrator_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    return dict(row) if row else None


def get_run_by_input_hash(
    conn: sqlite3.Connection, input_hash: str
) -> dict[str, Any] | None:
    """
    Returns the most recently started run matching ``input_hash``, or
    None. Not constrained to be unique: ``force_rerun`` intentionally
    permits multiple runs sharing the same input_hash, so ties are
    broken by most recent ``started_at``.
    """
    row = conn.execute(
        """
        SELECT * FROM orchestrator_runs
         WHERE input_hash = ?
         ORDER BY started_at DESC
         LIMIT 1
        """,
        (input_hash,),
    ).fetchone()
    return dict(row) if row else None


def complete_run(
    conn: sqlite3.Connection,
    run_id: str,
    completed_at: str,
    result_json: str,
) -> None:
    conn.execute(
        """
        UPDATE orchestrator_runs
           SET status       = 'complete',
               completed_at = :completed_at,
               result_json  = :result_json
         WHERE run_id = :run_id
        """,
        {"run_id": run_id, "completed_at": completed_at, "result_json": result_json},
    )


def fail_run(
    conn: sqlite3.Connection,
    run_id: str,
    failed_at: str,
    failure_reason: str,
) -> None:
    conn.execute(
        """
        UPDATE orchestrator_runs
           SET status         = 'failed',
               failed_at      = :failed_at,
               failure_reason = :failure_reason
         WHERE run_id = :run_id
        """,
        {"run_id": run_id, "failed_at": failed_at, "failure_reason": failure_reason},
    )


def list_runs_for_pipeline(
    conn: sqlite3.Connection, pipeline_name: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM orchestrator_runs
         WHERE pipeline_name = ?
         ORDER BY started_at DESC
        """,
        (pipeline_name,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_incomplete_runs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Returns all runs that never reached 'complete' or 'failed'."""
    rows = conn.execute(
        """
        SELECT * FROM orchestrator_runs
         WHERE status = 'started'
         ORDER BY started_at
        """
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Stage CRUD
# ---------------------------------------------------------------------------

def insert_stage(conn: sqlite3.Connection, stage: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO orchestrator_stages (
            stage_id, run_id, stage_name, status,
            started_at, completed_at, duration_ms, notes
        ) VALUES (
            :stage_id, :run_id, :stage_name, :status,
            :started_at, :completed_at, :duration_ms, :notes
        )
        """,
        stage,
    )


def complete_stage(
    conn: sqlite3.Connection,
    stage_id: str,
    completed_at: str,
    duration_ms: float,
    notes: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE orchestrator_stages
           SET status       = 'complete',
               completed_at = :completed_at,
               duration_ms  = :duration_ms,
               notes        = :notes
         WHERE stage_id = :stage_id
        """,
        {
            "stage_id": stage_id,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "notes": notes,
        },
    )


def fail_stage(
    conn: sqlite3.Connection,
    stage_id: str,
    completed_at: str,
    duration_ms: float,
    notes: str,
) -> None:
    conn.execute(
        """
        UPDATE orchestrator_stages
           SET status       = 'failed',
               completed_at = :completed_at,
               duration_ms  = :duration_ms,
               notes        = :notes
         WHERE stage_id = :stage_id
        """,
        {
            "stage_id": stage_id,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "notes": notes,
        },
    )


def get_stages_for_run(
    conn: sqlite3.Connection, run_id: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM orchestrator_stages
         WHERE run_id = ?
         ORDER BY started_at
        """,
        (run_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Compatibility wrapper
#
# Thin class shim for call sites / tests that expect an
# OrchestratorRunRepository class instance rather than module-level
# functions. Contains zero SQL of its own and zero business logic —
# every method delegates directly to the function of the same name
# above. The functional API remains canonical.
# ---------------------------------------------------------------------------

class OrchestratorRunRepository:
    """
    Compatibility wrapper around the module-level run/stage functions.

    Usage:
        repo = OrchestratorRunRepository()
        repo.insert_run(conn, run_dict)
        record = repo.get_run_by_id(conn, run_id)

    This class holds no state and performs no logic of its own — it
    exists solely so that code written against a class-based
    interface continues to work unchanged.
    """

    def init_schema(self, conn: sqlite3.Connection) -> None:
        return init_orchestrator_schema(conn)

    def insert_run(self, conn: sqlite3.Connection, run: dict[str, Any]) -> None:
        return insert_run(conn, run)

    def get_run_by_id(self, conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
        return get_run_by_id(conn, run_id)

    def get_run_by_input_hash(self, conn: sqlite3.Connection, input_hash: str) -> dict[str, Any] | None:
        return get_run_by_input_hash(conn, input_hash)

    def complete_run(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        completed_at: str,
        result_json: str,
    ) -> None:
        return complete_run(conn, run_id, completed_at, result_json)

    def fail_run(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        failed_at: str,
        failure_reason: str,
    ) -> None:
        return fail_run(conn, run_id, failed_at, failure_reason)

    def list_runs_for_pipeline(self, conn: sqlite3.Connection, pipeline_name: str) -> list[dict[str, Any]]:
        return list_runs_for_pipeline(conn, pipeline_name)

    def list_incomplete_runs(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        return list_incomplete_runs(conn)

    def insert_stage(self, conn: sqlite3.Connection, stage: dict[str, Any]) -> None:
        return insert_stage(conn, stage)

    def complete_stage(
        self,
        conn: sqlite3.Connection,
        stage_id: str,
        completed_at: str,
        duration_ms: float,
        notes: str | None = None,
    ) -> None:
        return complete_stage(conn, stage_id, completed_at, duration_ms, notes)

    def fail_stage(
        self,
        conn: sqlite3.Connection,
        stage_id: str,
        completed_at: str,
        duration_ms: float,
        notes: str,
    ) -> None:
        return fail_stage(conn, stage_id, completed_at, duration_ms, notes)

    def get_stages_for_run(self, conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
        return get_stages_for_run(conn, run_id)
