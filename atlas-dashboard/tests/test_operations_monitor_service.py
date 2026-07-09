"""
atlas/tests/test_operations_monitor_service.py

Unit tests for services/operations_monitor_service.py (AES-011).

Seeds real orchestrator_runs/orchestrator_stages rows via the existing
repository functions (no mocking of persistence), and directly
constructs services.background_job_service.Job instances for full
control over job state without needing real threading timing.
"""

from __future__ import annotations

import sqlite3

import pytest

import services.background_job_service as background_job_service
import services.operations_monitor_service as operations_monitor_service
from repositories import orchestrator_run_repository as orch_run_repo
from services.background_job_service import Job, JobState
from services.orchestrator import pipeline_registry
from services.orchestrator.pipelines.directory_launch import (
    PIPELINE_NAME,
    register_directory_launch_pipeline,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    pipeline_registry.clear_registry()
    yield
    pipeline_registry.clear_registry()


@pytest.fixture
def db_path(tmp_path) -> str:
    path = str(tmp_path / "operations_monitor_test.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    orch_run_repo.init_orchestrator_schema(conn)
    conn.close()
    return path


def _seed_job(job_id: str, **overrides) -> Job:
    job = Job(job_id=job_id, state=JobState.RUNNING)
    for key, value in overrides.items():
        setattr(job, key, value)
    with background_job_service._lock:
        background_job_service._jobs[job_id] = job
    return job


def _seed_run(db_path: str, run_id: str, input_hash: str, status: str = "started") -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    orch_run_repo.insert_run(
        conn,
        {
            "run_id": run_id,
            "pipeline_name": PIPELINE_NAME,
            "pipeline_version": "1.0.0",
            "input_hash": input_hash,
            "seed_payload_json": "{}",
            "engine_version_set": "{}",
            "status": status,
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:10+00:00" if status != "started" else None,
            "failed_at": None,
            "failure_reason": None,
            "result_json": None,
        },
    )
    conn.commit()
    conn.close()


def _seed_stage(db_path: str, run_id: str, stage_name: str, status: str) -> None:
    conn = sqlite3.connect(db_path)
    orch_run_repo.insert_stage(
        conn,
        {
            "stage_id": f"stage-{run_id}-{stage_name}",
            "run_id": run_id,
            "stage_name": stage_name,
            "status": status,
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:05+00:00" if status != "started" else None,
            "duration_ms": 12.5 if status != "started" else None,
            "notes": None,
        },
    )
    conn.commit()
    conn.close()


def test_returns_none_for_unknown_job(db_path):
    assert operations_monitor_service.get_job_monitor_view("does-not-exist", db_path=db_path) is None


def test_job_with_no_correlated_run_yet_has_empty_run_and_stages(db_path):
    _seed_job("job-no-run", state=JobState.QUEUED)

    view = operations_monitor_service.get_job_monitor_view("job-no-run", db_path=db_path)

    assert view["job"].job_id == "job-no-run"
    assert view["run"] is None
    assert view["stages"] == []


def test_running_job_shows_live_mixed_stage_statuses_via_input_hash(db_path):
    register_directory_launch_pipeline()
    _seed_run(db_path, "run-mid", input_hash="hash-mid")
    _seed_stage(db_path, "run-mid", "blueprint", "complete")
    _seed_stage(db_path, "run-mid", "ingestion", "started")
    # launch_kit / build / preview: no rows yet (not reached)

    _seed_job("job-mid", state=JobState.RUNNING, pipeline_input_hash="hash-mid")

    view = operations_monitor_service.get_job_monitor_view("job-mid", db_path=db_path)

    assert view["run"]["run_id"] == "run-mid"
    assert view["run"]["pipeline_name"] == PIPELINE_NAME
    statuses = {s["name"]: s["status"] for s in view["stages"]}
    assert statuses["blueprint"] == "complete"
    assert statuses["ingestion"] == "active"
    assert statuses["launch_kit"] == "pending"
    assert statuses["build"] == "pending"
    assert statuses["preview"] == "pending"
    # Order must match the registered PipelineSpec's stage order.
    assert [s["name"] for s in view["stages"]] == [
        "blueprint", "ingestion", "launch_kit", "build", "preview",
    ]


def test_stage_labels_are_human_readable(db_path):
    register_directory_launch_pipeline()
    _seed_run(db_path, "run-labels", input_hash="hash-labels")
    _seed_job("job-labels", state=JobState.RUNNING, pipeline_input_hash="hash-labels")

    view = operations_monitor_service.get_job_monitor_view("job-labels", db_path=db_path)

    labels = {s["name"]: s["label"] for s in view["stages"]}
    assert labels["build"] == "Directory Builder"
    assert labels["launch_kit"] == "Launch Kit"


def test_terminal_succeeded_job_resolves_run_via_result(db_path):
    register_directory_launch_pipeline()
    _seed_run(db_path, "run-done", input_hash="hash-done", status="complete")
    for stage_name in ("blueprint", "ingestion", "launch_kit", "build", "preview"):
        _seed_stage(db_path, "run-done", stage_name, "complete")

    _seed_job(
        "job-done",
        state=JobState.SUCCEEDED,
        result={"success": True, "run_id": "run-done", "message": "ok"},
    )

    view = operations_monitor_service.get_job_monitor_view("job-done", db_path=db_path)

    assert view["run"]["status"] == "complete"
    assert all(s["status"] == "complete" for s in view["stages"])


def test_terminal_failed_job_shows_failed_stage_and_pending_rest(db_path):
    register_directory_launch_pipeline()
    _seed_run(db_path, "run-failed", input_hash="hash-failed", status="failed")
    _seed_stage(db_path, "run-failed", "blueprint", "complete")
    _seed_stage(db_path, "run-failed", "ingestion", "failed")

    _seed_job(
        "job-failed",
        state=JobState.FAILED,
        result={"success": False, "run_id": "run-failed", "message": "boom"},
        error="boom",
    )

    view = operations_monitor_service.get_job_monitor_view("job-failed", db_path=db_path)

    statuses = {s["name"]: s["status"] for s in view["stages"]}
    assert statuses["blueprint"] == "complete"
    assert statuses["ingestion"] == "failed"
    assert statuses["launch_kit"] == "pending"


def test_falls_back_to_actual_stages_when_pipeline_not_registered(db_path):
    """Pipeline registry cleared (not registered in this process) — must not crash."""
    _seed_run(db_path, "run-unregistered", input_hash="hash-unregistered")
    _seed_stage(db_path, "run-unregistered", "blueprint", "complete")

    _seed_job("job-unregistered", state=JobState.RUNNING, pipeline_input_hash="hash-unregistered")

    view = operations_monitor_service.get_job_monitor_view("job-unregistered", db_path=db_path)

    assert [s["name"] for s in view["stages"]] == ["blueprint"]
