"""
atlas/services/pipeline_execution_service.py

AES-009A — business logic for triggering the AES-006 Directory Launch
pipeline from the Operations Center UI.

Deliberately kept flat (sibling to services/database.py,
services/orchestrator_run_view_service.py) rather than inside
services/orchestrator/ — this module is UI-facing plumbing on top of
the existing, unmodified orchestrator framework, not part of it.

Atlas contract: business logic and orchestration only — zero SQL (all
persistence access goes through repositories/run_repository.py and
repositories/orchestrator_run_repository.py, both untouched by this
module), no Flask, no HTML.

AES-009B note: this module owns only "how Directory Launch executes."
"What operations exist" (the descriptor list previously exposed here
as describe_available_pipelines()) moved to
services/operations_registry.py, so future non-pipeline operations
don't have to be described from inside a pipeline-specific module.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from config import DATABASE
from core.engine_versions import CURRENT_VERSION_SET
from core.input_hash import compute_pipeline_input_hash
from repositories import orchestrator_run_repository, run_repository
from services.database import Database
from services.investment_committee import PortfolioDecisionResult
from services.orchestrator import orchestrator_runner, pipeline_registry
from services.orchestrator.pipelines.directory_launch import (
    PIPELINE_NAME,
    register_directory_launch_pipeline,
)

_REQUIRED_FORM_FIELDS = (
    "committee_run_id",
    "project_slug",
    "description",
    "target_customer",
    "competition_level",
    "monetization_signals",
)


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DATABASE)
    conn.row_factory = sqlite3.Row
    run_repository.init_run_schema(conn)
    return conn


def _derive_output_roots(db_path: str | None = None) -> dict[str, str]:
    """
    Derives the three Directory Launch filesystem roots from the
    database file's directory, under a `generated/` subfolder — no new
    config constant, not user-editable via the form.
    """
    base = os.path.dirname(os.path.abspath(db_path or DATABASE))
    generated_root = os.path.join(base, "generated")
    return {
        "launch_kit_output_root": os.path.join(generated_root, "launch_packages"),
        "projects_root": os.path.join(generated_root, "projects"),
        "preview_root": os.path.join(generated_root, "previews"),
    }


def _ensure_pipeline_registered() -> None:
    try:
        register_directory_launch_pipeline()
    except pipeline_registry.PipelineAlreadyRegisteredError:
        pass


def _lookup_failed_run_id(conn: sqlite3.Connection, seed_payload: dict[str, Any]) -> str | None:
    """
    Recovers the orchestrator run_id for a stage failure, so the
    Operations Center failure banner can link to its full stage-by-
    stage detail (repositories/orchestrator_run_repository.py already
    persists it — the run is created before the failing stage runs).

    Recomputes the same input_hash orchestrator_runner.run_pipeline
    used internally, from the identical pipeline_name/pipeline_version/
    seed_payload/version_set — no orchestrator/pipeline code changes,
    just reuse of already-public functions.
    """
    spec = pipeline_registry.get_pipeline(PIPELINE_NAME)
    input_hash = compute_pipeline_input_hash(
        pipeline_name=PIPELINE_NAME,
        pipeline_version=spec.pipeline_version,
        seed_payload=seed_payload,
        version_set=CURRENT_VERSION_SET,
    )
    run = orchestrator_run_repository.get_run_by_input_hash(conn, input_hash)
    return run["run_id"] if run else None


def _clean_failure_message(exc: Exception) -> str:
    """
    orchestrator_runner wraps stage failures as:
        "Pipeline failed for pipeline_name='...' (run_id=...): <cause>"
    Strips the technical pipeline_name/run_id prefix for the UI (the
    run_id is surfaced separately as a clickable link instead) while
    never showing a raw traceback. Falls back to the full text if the
    expected shape isn't found.
    """
    text = str(exc)
    marker = "): "
    idx = text.rfind(marker)
    cause = text[idx + len(marker):] if idx != -1 else text
    return f"Directory Launch pipeline failed: {cause}"


def _missing_fields(form: dict[str, Any]) -> list[str]:
    return [
        field
        for field in _REQUIRED_FORM_FIELDS
        if not str(form.get(field, "")).strip()
    ]


def start_directory_launch_run(
    *,
    committee_run_id: str,
    project_slug: str,
    description: str,
    target_customer: str,
    competition_level: str,
    monetization_signals: str,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Triggers one Directory Launch pipeline run from Operations Center
    form input. Never raises — every failure mode (missing fields,
    unknown/incomplete committee run, pipeline stage failure) is
    converted into a {"success": False, "message": ...} result so the
    route can render it directly.
    """
    form = {
        "committee_run_id": committee_run_id,
        "project_slug": project_slug,
        "description": description,
        "target_customer": target_customer,
        "competition_level": competition_level,
        "monetization_signals": monetization_signals,
    }
    missing = _missing_fields(form)
    if missing:
        return {
            "success": False,
            "run_id": None,
            "message": f"Missing required field(s): {', '.join(missing)}.",
        }

    conn = _connect(db_path)
    try:
        committee_run = run_repository.get_run_by_id(conn, committee_run_id)
        if committee_run is None:
            return {
                "success": False,
                "run_id": None,
                "message": f"No investment committee run found with run_id {committee_run_id!r}.",
            }

        if not committee_run.get("result_json"):
            return {
                "success": False,
                "run_id": None,
                "message": (
                    f"Committee run {committee_run_id!r} has not completed yet "
                    f"(status={committee_run.get('status')!r}) and has no result to use."
                ),
            }

        try:
            committee_decision = PortfolioDecisionResult(
                **json.loads(committee_run["result_json"])
            )
        except Exception as exc:
            return {
                "success": False,
                "run_id": None,
                "message": f"Could not load committee decision for run_id {committee_run_id!r}: {exc}",
            }

        _ensure_pipeline_registered()

        raw_listings = Database().get_businesses_detailed()

        monetization_signal_list = [
            signal.strip()
            for signal in monetization_signals.split(",")
            if signal.strip()
        ]

        seed_payload = {
            "conn": conn,
            "committee_decision": committee_decision,
            "opportunity_extra": {
                "description": description,
                "target_customer": target_customer,
                "competition_level": competition_level,
                "monetization_signals": monetization_signal_list,
            },
            "raw_listings": raw_listings,
            "project_slug": project_slug,
            **_derive_output_roots(db_path),
        }

        try:
            result = orchestrator_runner.run_pipeline(PIPELINE_NAME, seed_payload, conn)
        except RuntimeError as exc:
            return {
                "success": False,
                "run_id": _lookup_failed_run_id(conn, seed_payload),
                "message": _clean_failure_message(exc),
            }

        return {
            "success": True,
            "run_id": result["run_id"],
            "cached": result["_cached"],
            "message": (
                "Directory Launch pipeline run already existed (cached result)."
                if result["_cached"]
                else "Directory Launch pipeline completed successfully."
            ),
        }
    finally:
        conn.close()
