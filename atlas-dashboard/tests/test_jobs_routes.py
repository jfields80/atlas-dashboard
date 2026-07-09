"""
atlas/tests/test_jobs_routes.py

Flask route tests for routes/jobs.py (AES-010, extended by AES-011's
Live Operations Monitor: stage checklist + /status.json polling
endpoint).

Isolated test-Flask-app pattern established in AES-007/009: registers
only jobs_bp against a Flask app pointed at the real templates/
directory.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask

import services.operations_monitor_service as operations_monitor_service
from repositories import orchestrator_run_repository as orch_run_repo
from routes.jobs import jobs_bp
from services.background_job_service import Job, JobState, submit_job, wait_for_job
import services.background_job_service as background_job_service
from services.orchestrator import pipeline_registry
from services.orchestrator.pipelines.directory_launch import (
    PIPELINE_NAME,
    register_directory_launch_pipeline,
)

TEMPLATES_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _clean_registry():
    pipeline_registry.clear_registry()
    yield
    pipeline_registry.clear_registry()


@pytest.fixture
def client():
    test_app = Flask(__name__, template_folder=TEMPLATES_DIR)
    test_app.config["TESTING"] = True
    test_app.register_blueprint(jobs_bp)

    with test_app.test_client() as test_client:
        yield test_client


def test_job_status_returns_404_for_unknown_job(client):
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 404


def test_job_status_shows_succeeded_state(client):
    job_id = submit_job(lambda job_id: {"success": True, "message": "All good.", "run_id": "run-abc-123"})
    wait_for_job(job_id, timeout=5)

    response = client.get(f"/jobs/{job_id}")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "SUCCEEDED" in html
    assert "run-abc-123" in html
    assert "View Run Details" in html
    assert "/orchestrator/runs/run-abc-123" in html


def test_job_status_shows_failed_state_with_error_and_no_traceback(client):
    job_id = submit_job(lambda job_id: {"success": False, "message": "Something went wrong."})
    wait_for_job(job_id, timeout=5)

    response = client.get(f"/jobs/{job_id}")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "FAILED" in html
    assert "Something went wrong." in html
    assert "Traceback" not in html


def test_job_status_shows_timestamps(client):
    job_id = submit_job(lambda job_id: {"success": True, "message": "ok"})
    job = wait_for_job(job_id, timeout=5)

    response = client.get(f"/jobs/{job_id}")
    html = response.data.decode("utf-8")

    assert job.started_at in html
    assert job.completed_at in html


def test_job_status_page_renders_stage_checklist_for_correlated_run(client, tmp_path, monkeypatch):
    db_path = str(tmp_path / "jobs_routes_monitor_test.db")
    monkeypatch.setattr(operations_monitor_service, "DATABASE", db_path)

    register_directory_launch_pipeline()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    orch_run_repo.init_orchestrator_schema(conn)
    orch_run_repo.insert_run(
        conn,
        {
            "run_id": "run-monitor-1",
            "pipeline_name": PIPELINE_NAME,
            "pipeline_version": "1.0.0",
            "input_hash": "hash-monitor-1",
            "seed_payload_json": "{}",
            "engine_version_set": "{}",
            "status": "started",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": None,
            "failed_at": None,
            "failure_reason": None,
            "result_json": None,
        },
    )
    orch_run_repo.insert_stage(
        conn,
        {
            "stage_id": "stage-monitor-1-blueprint",
            "run_id": "run-monitor-1",
            "stage_name": "blueprint",
            "status": "complete",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:02+00:00",
            "duration_ms": 12.5,
            "notes": None,
        },
    )
    conn.commit()
    conn.close()

    job = Job(job_id="job-monitor-1", state=JobState.RUNNING, pipeline_input_hash="hash-monitor-1")
    with background_job_service._lock:
        background_job_service._jobs["job-monitor-1"] = job

    response = client.get("/jobs/job-monitor-1")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Blueprint" in html
    assert "Directory Builder" in html
    assert "Preview" in html
    assert 'data-stage-name="blueprint"' in html
    assert "job-status-stage-complete" in html
    assert "job-status-stage-pending" in html


def test_job_status_returns_404_for_unknown_job_json(client):
    response = client.get("/jobs/does-not-exist/status.json")
    assert response.status_code == 404


def test_job_status_json_returns_expected_shape(client):
    job_id = submit_job(lambda job_id: {"success": True, "message": "All good.", "run_id": "run-json-1"})
    wait_for_job(job_id, timeout=5)

    response = client.get(f"/jobs/{job_id}/status.json")
    data = response.get_json()

    assert response.status_code == 200
    assert data["job_id"] == job_id
    assert data["state"] == "SUCCEEDED"
    assert data["result"]["run_id"] == "run-json-1"
    assert data["error"] is None
    assert data["stages"] == []


def test_job_status_json_reports_no_error_field_leak_for_success(client):
    job_id = submit_job(lambda job_id: {"success": True, "message": "ok"})
    wait_for_job(job_id, timeout=5)

    response = client.get(f"/jobs/{job_id}/status.json")
    data = response.get_json()

    assert data["error"] is None
