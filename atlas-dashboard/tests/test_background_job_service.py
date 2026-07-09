"""
atlas/tests/test_background_job_service.py

Unit tests for services/background_job_service.py (AES-010, extended
by AES-011's job_id-aware submit_job + pipeline_input_hash
correlation).

Uses wait_for_job (joins the tracked worker thread) rather than
sleep-polling, for deterministic assertions.
"""

from __future__ import annotations

from services.background_job_service import (
    JobState,
    get_job,
    set_pipeline_input_hash,
    submit_job,
    wait_for_job,
)


def test_submit_job_with_successful_result_reaches_succeeded():
    job_id = submit_job(lambda job_id: {"success": True, "message": "ok"})
    job = wait_for_job(job_id, timeout=5)

    assert job is not None
    assert job.state == JobState.SUCCEEDED
    assert job.error is None
    assert job.result == {"success": True, "message": "ok"}
    assert job.started_at is not None
    assert job.completed_at is not None


def test_submit_job_with_failure_result_reaches_failed_with_error():
    job_id = submit_job(lambda job_id: {"success": False, "message": "bad input"})
    job = wait_for_job(job_id, timeout=5)

    assert job is not None
    assert job.state == JobState.FAILED
    assert job.error == "bad input"
    assert job.result == {"success": False, "message": "bad input"}


def test_submit_job_with_raising_function_reaches_failed_with_exception_message():
    def _boom(job_id):
        raise ValueError("kaboom")

    job_id = submit_job(_boom)
    job = wait_for_job(job_id, timeout=5)

    assert job is not None
    assert job.state == JobState.FAILED
    assert job.error == "kaboom"
    assert job.result is None


def test_submit_job_with_plain_dict_result_reaches_succeeded():
    """A dict with no "success" key at all is treated as a success."""
    job_id = submit_job(lambda job_id: {"anything": "goes"})
    job = wait_for_job(job_id, timeout=5)

    assert job.state == JobState.SUCCEEDED
    assert job.error is None


def test_get_job_returns_none_for_unknown_job_id():
    assert get_job("does-not-exist") is None


def test_submit_job_returns_unique_job_ids():
    job_id_1 = submit_job(lambda job_id: {"success": True})
    job_id_2 = submit_job(lambda job_id: {"success": True})

    assert job_id_1 != job_id_2

    wait_for_job(job_id_1, timeout=5)
    wait_for_job(job_id_2, timeout=5)


def test_get_job_reflects_state_before_and_after_completion():
    job_id = submit_job(lambda job_id: {"success": True})

    # Immediately after submit, the job exists and is not yet unknown.
    job_before = get_job(job_id)
    assert job_before is not None
    assert job_before.state in (JobState.QUEUED, JobState.RUNNING, JobState.SUCCEEDED)

    job_after = wait_for_job(job_id, timeout=5)
    assert job_after.state == JobState.SUCCEEDED


def test_submit_job_passes_job_id_to_callable():
    seen_job_ids = []

    def _record(job_id):
        seen_job_ids.append(job_id)
        return {"success": True}

    job_id = submit_job(_record)
    wait_for_job(job_id, timeout=5)

    assert seen_job_ids == [job_id]


def test_set_pipeline_input_hash_records_hash_on_job():
    job_id = submit_job(lambda job_id: {"success": True})
    wait_for_job(job_id, timeout=5)

    set_pipeline_input_hash(job_id, "hash-abc-123")

    assert get_job(job_id).pipeline_input_hash == "hash-abc-123"


def test_set_pipeline_input_hash_is_a_safe_no_op_for_unknown_job_id():
    set_pipeline_input_hash("does-not-exist", "hash-abc-123")  # must not raise


def test_job_reports_its_own_pipeline_input_hash_while_running():
    def _job(job_id):
        set_pipeline_input_hash(job_id, "hash-from-worker")
        return {"success": True}

    job_id = submit_job(_job)
    job = wait_for_job(job_id, timeout=5)

    assert job.pipeline_input_hash == "hash-from-worker"
