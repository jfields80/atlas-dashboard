"""
atlas/services/orchestrator_run_view_service.py

AES-007 — read-only business logic for viewing AES-006 Atlas
Orchestrator run history.

Deliberately kept flat (sibling to services/database.py) rather than
inside services/orchestrator/ — this module is a viewer bolted on top
of the existing, unmodified orchestrator framework, not part of it.

Atlas contract: business logic and shaping only — zero SQL (all
persistence access goes through repositories/orchestrator_run_repository.py),
no Flask, no HTML.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from config import DATABASE
from repositories import orchestrator_run_repository as orch_run_repo


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DATABASE)
    conn.row_factory = sqlite3.Row
    orch_run_repo.init_orchestrator_schema(conn)
    return conn


def _safe_json_loads(raw: str | None) -> Any:
    """Best-effort JSON parse for display; never raises."""
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw


def _format_duration(started_at: str | None, completed_at: str | None) -> str | None:
    """Human-readable duration between two ISO-8601 timestamps, or None."""
    if not started_at or not completed_at:
        return None
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(completed_at)
    except ValueError:
        return None

    seconds = (end - start).total_seconds()
    if seconds < 0:
        return None
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remainder = divmod(int(seconds), 60)
    return f"{minutes}m {remainder:02d}s"


def _shape_run(run: dict[str, Any]) -> dict[str, Any]:
    shaped = dict(run)
    shaped["engine_version_set"] = _safe_json_loads(run.get("engine_version_set"))
    shaped["seed_payload"] = _safe_json_loads(run.get("seed_payload_json"))
    shaped["result"] = _safe_json_loads(run.get("result_json"))
    shaped["duration_display"] = _format_duration(
        run.get("started_at"), run.get("completed_at")
    )
    return shaped


def list_runs(
    pipeline_name: str | None = None,
    limit: int = 200,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Returns recent orchestrator runs, most recent first.

    Scoped to ``pipeline_name`` when given, otherwise across every
    registered pipeline (capped at ``limit``).
    """
    conn = _connect(db_path)
    try:
        if pipeline_name:
            rows = orch_run_repo.list_runs_for_pipeline(conn, pipeline_name)
        else:
            rows = orch_run_repo.list_all_runs(conn, limit)
        return [_shape_run(row) for row in rows]
    finally:
        conn.close()


def get_run_detail(run_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    """
    Returns ``{"run": {...}, "stages": [...]}`` for ``run_id``, or
    None if no such run exists.
    """
    conn = _connect(db_path)
    try:
        run = orch_run_repo.get_run_by_id(conn, run_id)
        if run is None:
            return None

        stages = orch_run_repo.get_stages_for_run(conn, run_id)
        shaped_stages = [
            {
                **stage,
                "duration_display": (
                    f"{stage['duration_ms']:.1f}ms"
                    if stage.get("duration_ms") is not None
                    else None
                ),
            }
            for stage in stages
        ]
        return {"run": _shape_run(run), "stages": shaped_stages}
    finally:
        conn.close()
