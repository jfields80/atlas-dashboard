"""
atlas/tests/test_orchestrator_runner.py

Integration tests for services/orchestrator/orchestrator_runner.py —
the AES-006 Atlas Orchestrator's generalized, DB-backed pipeline
execution engine.

Uses trivial dummy stage handlers registered through
services/orchestrator/pipeline_registry.py — zero coupling to any
real Atlas subsystem. No Flask, no UI, no file I/O.
"""

from __future__ import annotations

import sqlite3

import pytest

import repositories.orchestrator_run_repository as orch_run_repo
from core.orchestration.pipeline_spec import PipelineSpec
from core.orchestration.stage_spec import StageSpec
from services.orchestrator import orchestrator_runner, pipeline_registry


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture(autouse=True)
def _clean_registry():
    pipeline_registry.clear_registry()
    yield
    pipeline_registry.clear_registry()


def _double(raw_value: int) -> int:
    return raw_value * 2


def _add_ten(doubled: int) -> int:
    return doubled + 10


def _boom(raw_value: int) -> int:
    raise ValueError("stage_b intentionally failed")


def _register_success_pipeline(name: str = "arithmetic_pipeline") -> PipelineSpec:
    spec = PipelineSpec(
        pipeline_name=name,
        pipeline_version="1.0.0",
        seed_keys=("raw_value",),
        stages=(
            StageSpec(name="double", handler=_double, input_keys=("raw_value",), output_key="doubled"),
            StageSpec(name="add_ten", handler=_add_ten, input_keys=("doubled",), output_key="final"),
        ),
    )
    pipeline_registry.register_pipeline(spec)
    return spec


def _register_failing_pipeline(name: str = "failing_pipeline") -> PipelineSpec:
    spec = PipelineSpec(
        pipeline_name=name,
        pipeline_version="1.0.0",
        seed_keys=("raw_value",),
        stages=(
            StageSpec(name="stage_a", handler=_double, input_keys=("raw_value",), output_key="doubled"),
            StageSpec(name="stage_b", handler=_boom, input_keys=("raw_value",), output_key="never"),
        ),
    )
    pipeline_registry.register_pipeline(spec)
    return spec


def test_run_pipeline_success_wires_stage_outputs_into_later_inputs():
    conn = _make_conn()
    _register_success_pipeline()

    result = orchestrator_runner.run_pipeline("arithmetic_pipeline", {"raw_value": 5}, conn)

    assert result["_cached"] is False
    assert result["context"]["doubled"] == 10
    assert result["context"]["final"] == 20
    assert result["pipeline_name"] == "arithmetic_pipeline"
    assert result["pipeline_version"] == "1.0.0"


def test_run_pipeline_checkpoints_all_stages_as_complete():
    conn = _make_conn()
    _register_success_pipeline("checkpoint_pipeline")

    result = orchestrator_runner.run_pipeline("checkpoint_pipeline", {"raw_value": 3}, conn)

    stages = orch_run_repo.get_stages_for_run(conn, result["run_id"])
    assert [s["stage_name"] for s in stages] == ["double", "add_ten"]
    for stage in stages:
        assert stage["status"] == "complete"
        assert stage["duration_ms"] is not None and stage["duration_ms"] >= 0


def test_run_persisted_with_complete_status():
    conn = _make_conn()
    _register_success_pipeline("persist_pipeline")

    result = orchestrator_runner.run_pipeline("persist_pipeline", {"raw_value": 1}, conn)

    run_record = orch_run_repo.get_run_by_id(conn, result["run_id"])
    assert run_record is not None
    assert run_record["status"] == "complete"
    assert run_record["result_json"] is not None


def test_run_pipeline_failure_marks_run_and_stage_failed_and_raises():
    conn = _make_conn()
    _register_failing_pipeline()

    with pytest.raises(RuntimeError, match="Pipeline failed"):
        orchestrator_runner.run_pipeline("failing_pipeline", {"raw_value": 7}, conn)

    runs = orch_run_repo.list_runs_for_pipeline(conn, "failing_pipeline")
    assert len(runs) == 1
    assert runs[0]["status"] == "failed"
    assert "stage_b intentionally failed" in runs[0]["failure_reason"]

    stages = orch_run_repo.get_stages_for_run(conn, runs[0]["run_id"])
    statuses = {s["stage_name"]: s["status"] for s in stages}
    assert statuses["stage_a"] == "complete"
    assert statuses["stage_b"] == "failed"


def test_run_pipeline_idempotent_on_same_seed_payload():
    conn = _make_conn()
    _register_success_pipeline("idempotent_pipeline")

    result1 = orchestrator_runner.run_pipeline("idempotent_pipeline", {"raw_value": 4}, conn)
    result2 = orchestrator_runner.run_pipeline("idempotent_pipeline", {"raw_value": 4}, conn)

    assert result2["_cached"] is True
    assert result2["run_id"] == result1["run_id"]

    runs = orch_run_repo.list_runs_for_pipeline(conn, "idempotent_pipeline")
    assert len(runs) == 1


def test_run_pipeline_force_rerun_bypasses_cache():
    conn = _make_conn()
    _register_success_pipeline("force_rerun_pipeline")

    result1 = orchestrator_runner.run_pipeline("force_rerun_pipeline", {"raw_value": 2}, conn)
    result2 = orchestrator_runner.run_pipeline(
        "force_rerun_pipeline", {"raw_value": 2}, conn, force_rerun=True
    )

    assert result2["_cached"] is False
    assert result2["run_id"] != result1["run_id"]

    runs = orch_run_repo.list_runs_for_pipeline(conn, "force_rerun_pipeline")
    assert len(runs) == 2


def test_run_pipeline_different_seed_payload_produces_different_run():
    conn = _make_conn()
    _register_success_pipeline("distinct_seed_pipeline")

    result1 = orchestrator_runner.run_pipeline("distinct_seed_pipeline", {"raw_value": 1}, conn)
    result2 = orchestrator_runner.run_pipeline("distinct_seed_pipeline", {"raw_value": 2}, conn)

    assert result1["run_id"] != result2["run_id"]
    assert result1["context"]["final"] != result2["context"]["final"]


def test_run_pipeline_raises_for_unregistered_pipeline():
    conn = _make_conn()
    with pytest.raises(pipeline_registry.PipelineNotFoundError):
        orchestrator_runner.run_pipeline("never_registered", {}, conn)
