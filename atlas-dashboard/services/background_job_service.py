"""
atlas/services/background_job_service.py

AES-010 — Background Job Queue Foundation.

A minimal, in-memory, thread-per-job registry. This is explicitly a
foundation: no distributed workers, no Celery, no Redis, no external
queue, no retries, no scheduling, no parallel-execution guarantees.
A later AES ticket will replace the in-memory registry with durable
persistence.

This module knows nothing about Directory Launch, pipelines, or the
orchestrator — it accepts any callable (given its own job_id) returning
a dict and tracks its execution. Callers (routes) compose the deferred
call (e.g. `lambda job_id: start_directory_launch_run(**form_values)`)
so pipeline logic is never duplicated here.

AES-011 note: `pipeline_input_hash` is an optional, generic
correlation field a wrapped callable may report back (via
`set_pipeline_input_hash`) as soon as it's known — before the job
finishes — so a live monitor can resolve "what orchestrator run does
this job correspond to" without this module knowing anything about
orchestrator runs itself. A future non-pipeline job simply never sets
it.

Atlas contract: business logic and orchestration only — no SQL, no
Flask, no HTML.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class JobState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class Job:
    job_id: str
    state: JobState = JobState.QUEUED
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    pipeline_input_hash: str | None = None


_jobs: dict[str, Job] = {}
_threads: dict[str, threading.Thread] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_job(job_id: str, fn: Callable[[str], dict[str, Any]]) -> None:
    with _lock:
        job = _jobs[job_id]
        job.state = JobState.RUNNING
        job.started_at = _now()

    try:
        result = fn(job_id)
    except Exception as exc:
        with _lock:
            job.error = str(exc)
            job.completed_at = _now()
            job.state = JobState.FAILED
        return

    with _lock:
        job.result = result
        job.completed_at = _now()
        if isinstance(result, dict) and result.get("success") is False:
            job.state = JobState.FAILED
            job.error = result.get("message")
        else:
            job.state = JobState.SUCCEEDED


def submit_job(fn: Callable[[str], dict[str, Any]]) -> str:
    """
    Starts `fn` on a background thread and returns immediately with a
    new job_id. `fn` is called with that same job_id (so it can report
    correlation data back via `set_pipeline_input_hash` while it's
    still running) and must return a dict; if that dict contains
    `"success": False`, the job is recorded as FAILED with `error` set
    from its `"message"`. An uncaught exception from `fn` is also
    recorded as FAILED, with `error` set from the exception's string
    form. Any other return value marks the job SUCCEEDED.
    """
    job_id = str(uuid.uuid4())
    job = Job(job_id=job_id, state=JobState.QUEUED)

    with _lock:
        _jobs[job_id] = job

    thread = threading.Thread(target=_run_job, args=(job_id, fn), daemon=True)

    with _lock:
        _threads[job_id] = thread

    thread.start()
    return job_id


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def set_pipeline_input_hash(job_id: str, input_hash: str) -> None:
    """
    Records a correlation hash on a running job so a live monitor can
    resolve which orchestrator run it corresponds to before the job
    finishes. Tolerant no-op for an unknown job_id (the job may have
    already been evicted by a future persistence layer, or the caller
    made a mistake — either way this must never raise from a worker
    thread).
    """
    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            job.pipeline_input_hash = input_hash


def wait_for_job(job_id: str, timeout: float | None = None) -> Job | None:
    """
    Blocks until the job's worker thread finishes (or `timeout`
    elapses), then returns the job's current snapshot. Primarily a
    test utility for deterministic assertions without sleep-polling;
    harmless to call from production code too.
    """
    with _lock:
        thread = _threads.get(job_id)

    if thread is not None:
        thread.join(timeout=timeout)

    return get_job(job_id)
