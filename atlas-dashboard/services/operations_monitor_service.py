"""
atlas/services/operations_monitor_service.py

AES-011 — Live Operations Monitor: read-side view combining a
background job's state (services/background_job_service.py) with its
correlated orchestrator run's live stage progress (repositories/
orchestrator_run_repository.py + services/orchestrator/pipeline_registry.py),
without introducing any second progress-tracking system.

A job's underlying orchestrator run is resolved two ways depending on
whether the job has finished yet:
  - Terminal jobs: `job.result["run_id"]` (already returned by
    services/pipeline_execution_service.py).
  - Still-running jobs: `job.pipeline_input_hash` (reported early via
    background_job_service.set_pipeline_input_hash — see
    pipeline_execution_service.start_directory_launch_run's
    on_input_hash_known callback) resolved through the existing
    orchestrator_run_repository.get_run_by_input_hash.

Once a run_id is known, the stage checklist is built by walking the
*registered* PipelineSpec's stages (the authoritative, ordered list of
what a pipeline run will do) and overlaying each stage's real DB
status from get_stages_for_run — a stage with no DB row yet is
"pending" (not yet reached), never fabricated as complete.

Atlas contract: business logic and orchestration only — zero SQL of
its own (all persistence access delegates to existing repository
functions), no Flask, no HTML.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from config import DATABASE
from repositories import orchestrator_run_repository
from services.background_job_service import Job, get_job
from services.orchestrator import pipeline_registry

_STAGE_LABELS = {
    "blueprint": "Blueprint",
    "ingestion": "Ingestion",
    "launch_kit": "Launch Kit",
    "build": "Directory Builder",
    "preview": "Preview",
}


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DATABASE)
    conn.row_factory = sqlite3.Row
    orchestrator_run_repository.init_orchestrator_schema(conn)
    return conn


def _resolve_run_id(job: Job, conn: sqlite3.Connection) -> str | None:
    if job.result and job.result.get("run_id"):
        return job.result["run_id"]

    if job.pipeline_input_hash:
        run = orchestrator_run_repository.get_run_by_input_hash(conn, job.pipeline_input_hash)
        if run:
            return run["run_id"]

    return None


def _build_stage_checklist(conn: sqlite3.Connection, run: dict[str, Any]) -> list[dict[str, str]]:
    actual_by_name = {
        stage["stage_name"]: stage
        for stage in orchestrator_run_repository.get_stages_for_run(conn, run["run_id"])
    }

    try:
        spec = pipeline_registry.get_pipeline(run["pipeline_name"])
        expected_names = [stage.name for stage in spec.stages]
    except pipeline_registry.PipelineNotFoundError:
        # Pipeline not registered in this process (should not normally
        # happen — registration happens synchronously before a job is
        # submitted) — fall back to whatever stages have actually run
        # rather than guessing at an expected order.
        expected_names = list(actual_by_name.keys())

    checklist: list[dict[str, str]] = []
    for name in expected_names:
        actual = actual_by_name.get(name)
        if actual is None:
            status = "pending"
        elif actual["status"] == "complete":
            status = "complete"
        elif actual["status"] == "failed":
            status = "failed"
        else:
            status = "active"

        checklist.append(
            {
                "name": name,
                "label": _STAGE_LABELS.get(name, name.replace("_", " ").title()),
                "status": status,
            }
        )

    return checklist


def get_job_monitor_view(job_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    """
    Returns {"job": Job, "run": {...} | None, "stages": [...]} for
    job_id, or None if no such job exists. "run" and "stages" are
    empty/None whenever the job has no correlated orchestrator run yet
    (or ever, for a future non-pipeline-backed operation) — the
    monitor page renders cleanly either way.
    """
    job = get_job(job_id)
    if job is None:
        return None

    conn = _connect(db_path)
    try:
        run_id = _resolve_run_id(job, conn)
        if run_id is None:
            return {"job": job, "run": None, "stages": []}

        run = orchestrator_run_repository.get_run_by_id(conn, run_id)
        if run is None:
            return {"job": job, "run": None, "stages": []}

        run_summary = {
            "run_id": run["run_id"],
            "pipeline_name": run["pipeline_name"],
            "status": run["status"],
        }
        stages = _build_stage_checklist(conn, run)

        return {"job": job, "run": run_summary, "stages": stages}
    finally:
        conn.close()
