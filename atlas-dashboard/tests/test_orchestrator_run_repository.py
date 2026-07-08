"""
atlas/tests/test_orchestrator_run_repository.py

Unit tests for repositories/orchestrator_run_repository.py — the
AES-006 Atlas Orchestrator's persistence layer.

Mirrors the assertions services/pipeline_runner.py's tests make
against repositories/run_repository.py, adapted to the generalized
orchestrator_runs / orchestrator_stages schema.
"""

from __future__ import annotations

import sqlite3

import repositories.orchestrator_run_repository as orch_run_repo
from repositories.orchestrator_run_repository import OrchestratorRunRepository


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _run_row(run_id: str, pipeline_name: str = "sample_pipeline", input_hash: str = "hash-1") -> dict:
    return {
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "pipeline_version": "1.0.0",
        "input_hash": input_hash,
        "seed_payload_json": "{}",
        "engine_version_set": "{}",
        "status": "started",
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": None,
        "failed_at": None,
        "failure_reason": None,
        "result_json": None,
    }


def test_init_schema_is_idempotent():
    conn = _make_conn()
    orch_run_repo.init_orchestrator_schema(conn)
    orch_run_repo.init_orchestrator_schema(conn)  # must not raise


def test_insert_and_get_run_by_id():
    conn = _make_conn()
    orch_run_repo.init_orchestrator_schema(conn)

    orch_run_repo.insert_run(conn, _run_row("run-1"))
    conn.commit()

    record = orch_run_repo.get_run_by_id(conn, "run-1")
    assert record is not None
    assert record["pipeline_name"] == "sample_pipeline"
    assert record["status"] == "started"


def test_get_run_by_input_hash():
    conn = _make_conn()
    orch_run_repo.init_orchestrator_schema(conn)

    orch_run_repo.insert_run(conn, _run_row("run-2", input_hash="unique-hash"))
    conn.commit()

    record = orch_run_repo.get_run_by_input_hash(conn, "unique-hash")
    assert record is not None
    assert record["run_id"] == "run-2"

    assert orch_run_repo.get_run_by_input_hash(conn, "does-not-exist") is None


def test_complete_run_updates_status_and_result():
    conn = _make_conn()
    orch_run_repo.init_orchestrator_schema(conn)

    orch_run_repo.insert_run(conn, _run_row("run-3"))
    conn.commit()

    orch_run_repo.complete_run(conn, "run-3", "2026-01-01T00:05:00+00:00", '{"ok": true}')
    conn.commit()

    record = orch_run_repo.get_run_by_id(conn, "run-3")
    assert record["status"] == "complete"
    assert record["result_json"] == '{"ok": true}'


def test_fail_run_updates_status_and_reason():
    conn = _make_conn()
    orch_run_repo.init_orchestrator_schema(conn)

    orch_run_repo.insert_run(conn, _run_row("run-4"))
    conn.commit()

    orch_run_repo.fail_run(conn, "run-4", "2026-01-01T00:05:00+00:00", "ValueError: boom")
    conn.commit()

    record = orch_run_repo.get_run_by_id(conn, "run-4")
    assert record["status"] == "failed"
    assert record["failure_reason"] == "ValueError: boom"


def test_list_runs_for_pipeline_orders_most_recent_first():
    conn = _make_conn()
    orch_run_repo.init_orchestrator_schema(conn)

    row_a = _run_row("run-a", input_hash="hash-a")
    row_a["started_at"] = "2026-01-01T00:00:00+00:00"
    row_b = _run_row("run-b", input_hash="hash-b")
    row_b["started_at"] = "2026-01-02T00:00:00+00:00"

    orch_run_repo.insert_run(conn, row_a)
    orch_run_repo.insert_run(conn, row_b)
    conn.commit()

    runs = orch_run_repo.list_runs_for_pipeline(conn, "sample_pipeline")
    assert [r["run_id"] for r in runs] == ["run-b", "run-a"]


def test_list_incomplete_runs_only_returns_started():
    conn = _make_conn()
    orch_run_repo.init_orchestrator_schema(conn)

    orch_run_repo.insert_run(conn, _run_row("run-started", input_hash="hash-started"))
    orch_run_repo.insert_run(conn, _run_row("run-done", input_hash="hash-done"))
    conn.commit()
    orch_run_repo.complete_run(conn, "run-done", "2026-01-01T00:05:00+00:00", "{}")
    conn.commit()

    incomplete = orch_run_repo.list_incomplete_runs(conn)
    assert {r["run_id"] for r in incomplete} == {"run-started"}


def test_stage_insert_complete_fail_and_get_stages_for_run():
    conn = _make_conn()
    orch_run_repo.init_orchestrator_schema(conn)

    orch_run_repo.insert_run(conn, _run_row("run-stages"))
    conn.commit()

    orch_run_repo.insert_stage(conn, {
        "stage_id": "stage-1",
        "run_id": "run-stages",
        "stage_name": "first",
        "status": "started",
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": None,
        "duration_ms": None,
        "notes": None,
    })
    orch_run_repo.insert_stage(conn, {
        "stage_id": "stage-2",
        "run_id": "run-stages",
        "stage_name": "second",
        "status": "started",
        "started_at": "2026-01-01T00:00:01+00:00",
        "completed_at": None,
        "duration_ms": None,
        "notes": None,
    })
    conn.commit()

    orch_run_repo.complete_stage(conn, "stage-1", "2026-01-01T00:00:02+00:00", 12.5)
    orch_run_repo.fail_stage(conn, "stage-2", "2026-01-01T00:00:03+00:00", 5.0, "RuntimeError: boom")
    conn.commit()

    stages = orch_run_repo.get_stages_for_run(conn, "run-stages")
    assert [s["stage_name"] for s in stages] == ["first", "second"]
    assert stages[0]["status"] == "complete"
    assert stages[0]["duration_ms"] == 12.5
    assert stages[1]["status"] == "failed"
    assert stages[1]["notes"] == "RuntimeError: boom"


def test_orchestrator_run_repository_class_wrapper_delegates():
    conn = _make_conn()
    repo = OrchestratorRunRepository()
    repo.init_schema(conn)

    repo.insert_run(conn, _run_row("run-class"))
    conn.commit()

    record = repo.get_run_by_id(conn, "run-class")
    assert record is not None
    assert record["pipeline_name"] == "sample_pipeline"
