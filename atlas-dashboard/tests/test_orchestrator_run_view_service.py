"""
atlas/tests/test_orchestrator_run_view_service.py

Unit tests for services/orchestrator_run_view_service.py (AES-007).

Uses a real temp sqlite file (not :memory:) since the service opens
its own connection per call from a db_path string — an in-memory
database wouldn't persist data across those separate connections.
Seeds data directly via repositories/orchestrator_run_repository.py
(no mocking).
"""

from __future__ import annotations

import sqlite3

import pytest

import repositories.orchestrator_run_repository as orch_run_repo
from services import orchestrator_run_view_service as view_service


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "orchestrator_view_test.db")


def _seed_run(db_path: str, run_id: str, pipeline_name: str, status: str = "complete", **overrides) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    orch_run_repo.init_orchestrator_schema(conn)

    row = {
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "pipeline_version": "1.0.0",
        "input_hash": f"hash-{run_id}",
        "seed_payload_json": '{"raw_value": 1}',
        "engine_version_set": "{}",
        "status": status,
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:00:10+00:00" if status == "complete" else None,
        "failed_at": "2026-01-01T00:00:10+00:00" if status == "failed" else None,
        "failure_reason": "ValueError: boom" if status == "failed" else None,
        "result_json": '{"ok": true}' if status == "complete" else None,
    }
    row.update(overrides)
    orch_run_repo.insert_run(conn, row)
    conn.commit()
    conn.close()


def _seed_stage(db_path: str, run_id: str, stage_name: str, status: str = "complete", notes=None) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    orch_run_repo.insert_stage(
        conn,
        {
            "stage_id": f"stage-{run_id}-{stage_name}",
            "run_id": run_id,
            "stage_name": stage_name,
            "status": status,
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:05+00:00",
            "duration_ms": 12.5,
            "notes": notes,
        },
    )
    conn.commit()
    conn.close()


def test_list_runs_empty_state(db_path):
    assert view_service.list_runs(db_path=db_path) == []


def test_list_runs_all_and_filtered(db_path):
    _seed_run(db_path, "run-a", "pipeline_one")
    _seed_run(db_path, "run-b", "pipeline_two")

    all_runs = view_service.list_runs(db_path=db_path)
    assert {r["run_id"] for r in all_runs} == {"run-a", "run-b"}

    filtered = view_service.list_runs(pipeline_name="pipeline_one", db_path=db_path)
    assert [r["run_id"] for r in filtered] == ["run-a"]


def test_list_runs_shapes_duration_and_parses_json(db_path):
    _seed_run(db_path, "run-a", "pipeline_one")

    [run] = view_service.list_runs(db_path=db_path)
    assert run["duration_display"] == "10.0s"
    assert run["result"] == {"ok": True}
    assert run["seed_payload"] == {"raw_value": 1}


def test_get_run_detail_includes_ordered_stages(db_path):
    _seed_run(db_path, "run-a", "pipeline_one")
    _seed_stage(db_path, "run-a", "first")
    _seed_stage(db_path, "run-a", "second")

    detail = view_service.get_run_detail("run-a", db_path=db_path)
    assert detail["run"]["run_id"] == "run-a"
    assert [s["stage_name"] for s in detail["stages"]] == ["first", "second"]
    assert detail["stages"][0]["duration_display"] == "12.5ms"


def test_get_run_detail_unknown_run_returns_none(db_path):
    assert view_service.get_run_detail("does-not-exist", db_path=db_path) is None


def test_get_run_detail_surfaces_failure_reason_and_stage_notes(db_path):
    _seed_run(db_path, "run-fail", "pipeline_one", status="failed")
    _seed_stage(db_path, "run-fail", "stage_a", status="failed", notes="RuntimeError: kaboom")

    detail = view_service.get_run_detail("run-fail", db_path=db_path)
    assert detail["run"]["failure_reason"] == "ValueError: boom"
    assert detail["stages"][0]["notes"] == "RuntimeError: kaboom"


def test_json_parse_fallback_for_malformed_payload(db_path):
    _seed_run(db_path, "run-bad-json", "pipeline_one", seed_payload_json="{not valid json")

    [run] = view_service.list_runs(db_path=db_path)
    assert run["seed_payload"] == "{not valid json"
