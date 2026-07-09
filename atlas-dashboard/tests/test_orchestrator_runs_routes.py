"""
atlas/tests/test_orchestrator_runs_routes.py

Flask route tests for routes/orchestrator_runs.py (AES-007) — the
first Flask test_client() usage in this repo.

Uses an isolated test Flask app that registers ONLY
orchestrator_runs_bp, rather than importing the real app.py. This is
deliberate: app.py currently fails to import at all due to a
pre-existing, unrelated bug (services/opportunity_v2/bootstrap.py
imports `initialize_memory_system`, which does not exist in
services/opportunity_v2/persistence.py — confirmed unrelated to
AES-007 via `git status`, that module is untouched by this feature).
That bug is separate technical debt and out of scope here; building a
minimal, isolated app around the new blueprint tests the real route
and real templates without depending on the broken opportunity_v2
boot sequence.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask

import repositories.orchestrator_run_repository as orch_run_repo
import services.orchestrator_run_view_service as view_service
from routes.orchestrator_runs import orchestrator_runs_bp

TEMPLATES_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "orchestrator_routes_test.db")
    monkeypatch.setattr(view_service, "DATABASE", db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    orch_run_repo.init_orchestrator_schema(conn)

    orch_run_repo.insert_run(
        conn,
        {
            "run_id": "run-route-test-1",
            "pipeline_name": "directory_launch_v1",
            "pipeline_version": "1.0.0",
            "input_hash": "hash-route-test-1",
            "seed_payload_json": "{}",
            "engine_version_set": "{}",
            "status": "complete",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:10+00:00",
            "failed_at": None,
            "failure_reason": None,
            "result_json": "{}",
        },
    )
    orch_run_repo.insert_stage(
        conn,
        {
            "stage_id": "stage-route-test-1",
            "run_id": "run-route-test-1",
            "stage_name": "blueprint",
            "status": "complete",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:05+00:00",
            "duration_ms": 42.0,
            "notes": None,
        },
    )
    conn.commit()
    conn.close()

    test_app = Flask(__name__, template_folder=TEMPLATES_DIR)
    test_app.config["TESTING"] = True
    test_app.register_blueprint(orchestrator_runs_bp)

    with test_app.test_client() as test_client:
        yield test_client


def test_runs_list_returns_200_and_shows_pipeline_name(client):
    response = client.get("/orchestrator/runs")
    assert response.status_code == 200
    assert b"directory_launch_v1" in response.data


def test_run_detail_returns_200_and_shows_stage_name(client):
    response = client.get("/orchestrator/runs/run-route-test-1")
    assert response.status_code == 200
    assert b"blueprint" in response.data


def test_run_detail_404_for_unknown_run(client):
    response = client.get("/orchestrator/runs/does-not-exist")
    assert response.status_code == 404
