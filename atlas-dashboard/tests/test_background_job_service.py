"""
atlas/tests/test_background_job_service.py

Unit tests for services/background_job_service.py (AES-010).

Uses wait_for_job (joins the tracked worker thread) rather than
sleep-polling, for deterministic assertions.
"""

from __future__ import annotations

from services.background_job_service import JobState, get_job, submit_job, wait_for_job


def test_submit_job_with_successful_result_reaches_succeeded():
    job_id = submit_job(lambda: {"success": True, "message": "ok"})
    job = wait_for_job(job_id, timeout=5)

    assert job is not None
    assert job.state == JobState.SUCCEEDED
    assert job.error is None
    assert job.result == {"success": True, "message": "ok"}
    assert job.started_at is not None
    assert job.completed_at is not None


def test_submit_job_with_failure_result_reaches_failed_with_error():
    job_id = submit_job(lambda: {"success": False, "message": "bad input"})
    job = wait_for_job(job_id, timeout=5)

    assert job is not None
    assert job.state == JobState.FAILED
    assert job.error == "bad input"
    assert job.result == {"success": False, "message": "bad input"}


def test_submit_job_with_raising_function_reaches_failed_with_exception_message():
    def _boom():
        raise ValueError("kaboom")

    job_id = submit_job(_boom)
    job = wait_for_job(job_id, timeout=5)

    assert job is not None
    assert job.state == JobState.FAILED
    assert job.error == "kaboom"
    assert job.result is None


def test_submit_job_with_plain_dict_result_reaches_succeeded():
    """A dict with no "success" key at all is treated as a success."""
    job_id = submit_job(lambda: {"anything": "goes"})
    job = wait_for_job(job_id, timeout=5)

    assert job.state == JobState.SUCCEEDED
    assert job.error is None


def test_get_job_returns_none_for_unknown_job_id():
    assert get_job("does-not-exist") is None


def test_submit_job_returns_unique_job_ids():
    job_id_1 = submit_job(lambda: {"success": True})
    job_id_2 = submit_job(lambda: {"success": True})

    assert job_id_1 != job_id_2

    wait_for_job(job_id_1, timeout=5)
    wait_for_job(job_id_2, timeout=5)


def test_get_job_reflects_state_before_and_after_completion():
    job_id = submit_job(lambda: {"success": True})

    # Immediately after submit, the job exists and is not yet unknown.
    job_before = get_job(job_id)
    assert job_before is not None
    assert job_before.state in (JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED)

    job_after = wait_for_job(job_id, timeout=5)
    assert job_after.state == JobState.SUCCEEDED
