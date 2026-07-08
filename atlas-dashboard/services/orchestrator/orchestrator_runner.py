"""
atlas/services/orchestrator/orchestrator_runner.py

AES-006 Atlas Orchestrator — generalized, framework-agnostic pipeline
runner.

Generalizes the checkpointing/idempotency pattern proven out by
``services/pipeline_runner.py`` (the v3 opportunity-evaluation
orchestrator) for arbitrary pipelines registered via
``services/orchestrator/pipeline_registry.py``. Unlike
``pipeline_runner.py``, this module hardcodes no knowledge of any
specific subsystem — it only knows how to walk a ``PipelineSpec``'s
stages, resolve each stage's inputs from a running context dict, and
checkpoint progress.

Responsibilities:
  1. Run identity: run_id, input_hash, idempotency check.
  2. Stage checkpointing: orchestrator_stages table.
  3. Sequential stage execution, wiring stage outputs into later
     stages' inputs via a shared context dict.
  4. Result persistence: orchestrator_runs record.

Architecture rules:
  - Zero SQL outside repositories.
  - Zero Flask imports.
  - Zero UI code.
  - Deterministic: same pipeline_name, seed_payload, engine
    version_set → same output (assuming stage handlers are
    themselves deterministic).
"""

from __future__ import annotations

import json
import sqlite3
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Generator

from core.engine_versions import CURRENT_VERSION_SET, EngineVersionSet
from core.input_hash import compute_pipeline_input_hash
from core.orchestration.pipeline_spec import PipelineSpec

from repositories import orchestrator_run_repository as orch_run_repo
from services.orchestrator import pipeline_registry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _json_default(obj: Any) -> Any:
    """Best-effort fallback for serializing arbitrary stage outputs."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "_asdict"):
        return obj._asdict()
    if hasattr(obj, "__dict__"):
        return vars(obj)
    return str(obj)


@contextmanager
def _stage(
    conn: sqlite3.Connection,
    run_id: str,
    stage_name: str,
) -> Generator[None, None, None]:
    stage_id = _new_id()
    started_at = _now()
    t0 = monotonic()

    orch_run_repo.insert_stage(
        conn,
        {
            "stage_id": stage_id,
            "run_id": run_id,
            "stage_name": stage_name,
            "status": "started",
            "started_at": started_at,
            "completed_at": None,
            "duration_ms": None,
            "notes": None,
        },
    )
    conn.commit()

    try:
        yield
        duration_ms = (monotonic() - t0) * 1000
        orch_run_repo.complete_stage(conn, stage_id, _now(), round(duration_ms, 2))
        conn.commit()
    except Exception as exc:
        duration_ms = (monotonic() - t0) * 1000
        orch_run_repo.fail_stage(
            conn,
            stage_id,
            _now(),
            round(duration_ms, 2),
            notes=f"{type(exc).__name__}: {exc}",
        )
        conn.commit()
        raise


def run_pipeline(
    pipeline_name: str,
    seed_payload: dict[str, Any],
    conn: sqlite3.Connection,
    *,
    version_set: EngineVersionSet = CURRENT_VERSION_SET,
    force_rerun: bool = False,
) -> dict[str, Any]:
    """
    Executes the pipeline registered under ``pipeline_name`` against
    ``seed_payload``.

    Behaviour:
      - Looks up the ``PipelineSpec`` via
        ``pipeline_registry.get_pipeline`` (raises
        ``PipelineNotFoundError`` if unregistered).
      - Computes an idempotency hash from
        (pipeline_name, pipeline_version, seed_payload, version_set).
        Unless ``force_rerun``, a prior completed run with the same
        hash is returned directly (``_cached: True``), never re-run.
      - Seeds a running context dict with ``seed_payload``, then walks
        ``spec.stages`` in order. Each stage's inputs are resolved
        from ``stage.input_keys`` against the current context; each
        stage's result is stored at ``context[stage.output_key]`` for
        later stages to consume.
      - Each stage is checkpointed into ``orchestrator_stages`` via
        ``_stage()`` — started/complete/failed with duration_ms.
      - On any stage exception, the run is marked failed and the
        exception is re-raised wrapped in a ``RuntimeError`` (same
        failure contract as ``services/pipeline_runner.py``).

    Returns a dict with keys: ``run_id``, ``pipeline_name``,
    ``pipeline_version``, ``engine_version_set``, ``context``
    (JSON-safe dict of every stage's output_key), ``_cached``.
    """
    orch_run_repo.init_orchestrator_schema(conn)

    spec: PipelineSpec = pipeline_registry.get_pipeline(pipeline_name)

    input_hash = compute_pipeline_input_hash(
        pipeline_name=pipeline_name,
        pipeline_version=spec.pipeline_version,
        seed_payload=seed_payload,
        version_set=version_set,
    )

    if not force_rerun:
        existing_run = orch_run_repo.get_run_by_input_hash(conn, input_hash)
        if existing_run and existing_run["status"] == "complete" and existing_run["result_json"]:
            context = json.loads(existing_run["result_json"])
            return {
                "run_id": existing_run["run_id"],
                "pipeline_name": pipeline_name,
                "pipeline_version": spec.pipeline_version,
                "engine_version_set": version_set.as_dict(),
                "context": context,
                "_cached": True,
            }

    run_id = _new_id()

    orch_run_repo.insert_run(
        conn,
        {
            "run_id": run_id,
            "pipeline_name": pipeline_name,
            "pipeline_version": spec.pipeline_version,
            "input_hash": input_hash,
            "seed_payload_json": json.dumps(seed_payload, default=_json_default, sort_keys=True),
            "engine_version_set": version_set.as_json(),
            "status": "started",
            "started_at": _now(),
            "completed_at": None,
            "failed_at": None,
            "failure_reason": None,
            "result_json": None,
        },
    )
    conn.commit()

    try:
        return _run_stages(
            conn=conn,
            run_id=run_id,
            pipeline_name=pipeline_name,
            spec=spec,
            seed_payload=seed_payload,
            version_set=version_set,
        )
    except Exception as exc:
        orch_run_repo.fail_run(
            conn,
            run_id,
            _now(),
            failure_reason=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        conn.commit()
        raise RuntimeError(
            f"Pipeline failed for pipeline_name={pipeline_name!r} "
            f"(run_id={run_id}): {exc}"
        ) from exc


def _run_stages(
    conn: sqlite3.Connection,
    run_id: str,
    pipeline_name: str,
    spec: PipelineSpec,
    seed_payload: dict[str, Any],
    version_set: EngineVersionSet,
) -> dict[str, Any]:
    context: dict[str, Any] = dict(seed_payload)

    for stage in spec.stages:
        with _stage(conn, run_id, stage.name):
            inputs = {key: context[key] for key in stage.input_keys}
            result = stage.handler(**inputs)
            if stage.output_key:
                context[stage.output_key] = result

    result_json = json.dumps(context, default=_json_default, sort_keys=True)

    orch_run_repo.complete_run(conn, run_id, _now(), result_json)
    conn.commit()

    return {
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "pipeline_version": spec.pipeline_version,
        "engine_version_set": version_set.as_dict(),
        "context": json.loads(result_json),
        "_cached": False,
    }
