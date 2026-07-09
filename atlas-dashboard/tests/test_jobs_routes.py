"""
atlas/tests/test_jobs_routes.py

Flask route tests for routes/jobs.py (AES-010).

Isolated test-Flask-app pattern established in AES-007/009: registers
only jobs_bp against a Flask app pointed at the real templates/
directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from routes.jobs import jobs_bp
from services.background_job_service import submit_job, wait_for_job

TEMPLATES_DIR = str(Path(__file__).resolve().parent.parent / "templates")


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
    job_id = submit_job(lambda: {"success": True, "message": "All good.", "run_id": "run-abc-123"})
    wait_for_job(job_id, timeout=5)

    response = client.get(f"/jobs/{job_id}")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "SUCCEEDED" in html
    assert "run-abc-123" in html
    assert "View Run Details" in html
    assert "/orchestrator/runs/run-abc-123" in html


def test_job_status_shows_failed_state_with_error_and_no_traceback(client):
    job_id = submit_job(lambda: {"success": False, "message": "Something went wrong."})
    wait_for_job(job_id, timeout=5)

    response = client.get(f"/jobs/{job_id}")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "FAILED" in html
    assert "Something went wrong." in html
    assert "Traceback" not in html


def test_job_status_shows_timestamps(client):
    job_id = submit_job(lambda: {"success": True, "message": "ok"})
    job = wait_for_job(job_id, timeout=5)

    response = client.get(f"/jobs/{job_id}")
    html = response.data.decode("utf-8")

    assert job.started_at in html
    assert job.completed_at in html
