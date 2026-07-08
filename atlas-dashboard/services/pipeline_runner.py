"""
services/pipeline_runner.py

v3 Pipeline Runner — framework-agnostic orchestrator.

This is the ONLY entry point for executing a full pipeline evaluation.
It is the sole writer to the database during a run.

Responsibilities:
  1. Run identity: run_id, input_hash, idempotency check
  2. Stage checkpointing: run_stages table
  3. Portfolio snapshot acquisition: latest or new
  4. v2 pipeline execution via v2_pipeline_adapter
  5. v3 layer execution:
       Market Liquidity → Portfolio Synergy → Expansion Classifier → Investment Committee
  6. Result persistence: run record + committee result JSON
  7. Structured output assembly

Architecture rules:
  - Zero SQL outside repositories.
  - Zero Flask imports.
  - Zero UI code.
  - Deterministic: same opportunity_id, snapshot_id, version_set → same output.
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
from core.input_hash import compute_input_hash
from services.v2_types import V2PipelineResult

from engines import expansion_classifier as classifier_engine
from engines import market_liquidity as liquidity_engine
from engines import portfolio_synergy as synergy_engine

from repositories import run_repository as run_repo
from services import investment_committee as committee_svc
from services import portfolio_service as portfolio_svc
from services.portfolio_service import PortfolioSnapshot
from services.v2_pipeline_adapter import run_v2_pipeline


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _to_json(model: Any) -> str:
    """
    Pydantic v1/v2 compatible JSON serialization.
    """
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json()
    if hasattr(model, "json"):
        return model.json()
    return json.dumps(model)


@contextmanager
def _stage(
    conn: sqlite3.Connection,
    run_id: str,
    stage_name: str,
) -> Generator[None, None, None]:
    stage_id = _new_id()
    started_at = _now()
    t0 = monotonic()

    run_repo.insert_stage(
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
        run_repo.complete_stage(conn, stage_id, _now(), round(duration_ms, 2))
        conn.commit()
    except Exception as exc:
        duration_ms = (monotonic() - t0) * 1000
        run_repo.fail_stage(
            conn,
            stage_id,
            _now(),
            round(duration_ms, 2),
            notes=f"{type(exc).__name__}: {exc}",
        )
        conn.commit()
        raise


def execute(
    opportunity_id: str,
    conn: sqlite3.Connection,
    *,
    version_set: EngineVersionSet = CURRENT_VERSION_SET,
    force_new_snapshot: bool = False,
    snapshot_id: str | None = None,
) -> dict[str, Any]:
    portfolio_svc.init_schema(conn)
    run_repo.init_run_schema(conn)

    snapshot: PortfolioSnapshot

    if snapshot_id:
        loaded = portfolio_svc.load_snapshot(conn, snapshot_id)
        if loaded is None:
            raise ValueError(f"Portfolio snapshot not found: {snapshot_id!r}")
        snapshot = loaded
    elif force_new_snapshot:
        snapshot = portfolio_svc.create_snapshot(conn)
    else:
        existing = portfolio_svc.get_latest_snapshot(conn)
        snapshot = existing if existing is not None else portfolio_svc.create_snapshot(conn)

    input_hash = compute_input_hash(
        opportunity_id=opportunity_id,
        portfolio_snapshot_id=snapshot.snapshot_id,
        version_set=version_set,
    )

    existing_run = run_repo.get_run_by_input_hash(conn, input_hash)
    if existing_run and existing_run["status"] == "complete" and existing_run["result_json"]:
        result_data = json.loads(existing_run["result_json"])
        result_data["_cached"] = True
        result_data["run_id"] = existing_run["run_id"]
        return result_data

    run_id = _new_id()

    run_repo.insert_run(
        conn,
        {
            "run_id": run_id,
            "input_hash": input_hash,
            "opportunity_id": opportunity_id,
            "portfolio_snapshot_id": snapshot.snapshot_id,
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
        return _run_pipeline(
            conn=conn,
            run_id=run_id,
            opportunity_id=opportunity_id,
            snapshot=snapshot,
            version_set=version_set,
        )
    except Exception as exc:
        run_repo.fail_run(
            conn,
            run_id,
            _now(),
            failure_reason=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        conn.commit()
        raise RuntimeError(
            f"Pipeline failed for opportunity {opportunity_id!r} "
            f"(run_id={run_id}): {exc}"
        ) from exc


def execute_batch(
    opportunity_ids: list[str],
    conn: sqlite3.Connection,
    *,
    version_set: EngineVersionSet = CURRENT_VERSION_SET,
    force_new_snapshot: bool = True,
) -> list[dict[str, Any]]:
    portfolio_svc.init_schema(conn)
    run_repo.init_run_schema(conn)

    if force_new_snapshot:
        snapshot = portfolio_svc.create_snapshot(conn)
    else:
        snapshot = portfolio_svc.get_latest_snapshot(conn) or portfolio_svc.create_snapshot(conn)

    results: list[dict[str, Any]] = []

    for opp_id in opportunity_ids:
        try:
            result = execute(
                opp_id,
                conn,
                version_set=version_set,
                snapshot_id=snapshot.snapshot_id,
            )
        except Exception as exc:
            result = {
                "run_id": None,
                "snapshot_id": snapshot.snapshot_id,
                "opportunity_id": opp_id,
                "error": str(exc),
                "_batch_failure": True,
            }

        results.append(result)

    return results


def _run_pipeline(
    conn: sqlite3.Connection,
    run_id: str,
    opportunity_id: str,
    snapshot: PortfolioSnapshot,
    version_set: EngineVersionSet,
) -> dict[str, Any]:
    v2_result: V2PipelineResult

    with _stage(conn, run_id, "v2_core_pipeline"):
        v2_result = run_v2_pipeline(opportunity_id, conn)

    decision = v2_result.decision_result
    category = decision.primary_category
    scope = decision.geographic_scope
    ceiling = decision.market_ceiling_monthly_usd
    conservative_revenue = decision.valuation.conservative_monthly_revenue

    with _stage(conn, run_id, "market_liquidity"):
        liquidity_evidence = liquidity_engine.gather(
            category=category,
            geographic_scope=scope,
        )

    with _stage(conn, run_id, "portfolio_synergy"):
        synergy_report = synergy_engine.score(
            candidate_category=category,
            candidate_geographic_scope=scope,
            candidate_monetization_model=None,
            portfolio_snapshot=snapshot,
        )

    with _stage(conn, run_id, "expansion_classifier"):
        expansion_class = classifier_engine.classify(
            market_ceiling_monthly_usd=ceiling,
            geographic_scope=scope,
            conservative_monthly_revenue=conservative_revenue,
            synergy_report=synergy_report,
            portfolio_snapshot=snapshot,
        )

    with _stage(conn, run_id, "investment_committee"):
        portfolio_decision = committee_svc.decide(
            v2_result=decision,
            synergy_report=synergy_report,
            expansion_class=expansion_class,
            liquidity_evidence=liquidity_evidence,
            version_set=version_set,
            run_id=run_id,
            portfolio_snapshot_id=snapshot.snapshot_id,
        )

    result_json = _to_json(portfolio_decision)

    with _stage(conn, run_id, "persist"):
        run_repo.complete_run(conn, run_id, _now(), result_json)
        conn.commit()

    output: dict[str, Any] = {
        "run_id": run_id,
        "snapshot_id": snapshot.snapshot_id,
        "engine_version_set": version_set.as_dict(),
        "market_result": {
            **v2_result.market_capacity_result,
            "category": category,
            "geographic_scope": scope,
            "ceiling_monthly_usd": ceiling,
        },
        "expansion_result": {
            "label": expansion_class.label,
            "confidence": expansion_class.confidence,
            "synergy_driven": expansion_class.synergy_driven,
            "plain_english": expansion_class.plain_english,
            "factors": [
                {
                    "name": f.name,
                    "observed_value": f.observed_value,
                    "rule_threshold": f.rule_threshold,
                    "passed": f.passed,
                    "rationale": f.rationale,
                }
                for f in expansion_class.factors
            ],
        },
        "liquidity_result": {
            "category": liquidity_evidence.category,
            "geographic_scope": liquidity_evidence.geographic_scope,
            "multiple_lo": liquidity_evidence.revenue_multiple_range.lo,
            "multiple_hi": liquidity_evidence.revenue_multiple_range.hi,
            "multiple_typical": liquidity_evidence.revenue_multiple_range.typical,
            "multiple_source": liquidity_evidence.revenue_multiple_range.source,
            "buyer_demand_signal": liquidity_evidence.buyer_demand_signal.value,
            "time_to_exit_months": liquidity_evidence.time_to_exit_months.value,
            "buyer_depth_estimate": liquidity_evidence.buyer_depth_estimate.value,
            "compression_risks": list(liquidity_evidence.compression_risks.value),
        },
        "synergy_result": {
            "total_score": synergy_report.total_score,
            "portfolio_snapshot_id": synergy_report.portfolio_snapshot_id,
            "components": [
                {
                    "name": c.name,
                    "raw_value": c.raw_value,
                    "weight": c.weight,
                    "contribution": c.contribution,
                    "rationale": c.rationale,
                }
                for c in synergy_report.components
            ],
        },
        "final_decision": json.loads(result_json),
    }

    return output


class PipelineRunner:
    """
    Compatibility wrapper for older Atlas tests/call sites.
    """

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        version_set: EngineVersionSet = CURRENT_VERSION_SET,
    ) -> None:
        self._conn = conn
        self._version_set = version_set

    def run(
        self,
        opportunity_id: str,
        conn: sqlite3.Connection | None = None,
        *,
        version_set: EngineVersionSet | None = None,
        force_new_snapshot: bool = False,
        snapshot_id: str | None = None,
    ) -> dict[str, Any]:
        active_conn = conn or self._conn

        if active_conn is None:
            raise ValueError(
                "PipelineRunner.run() requires a connection. "
                "Pass conn= or construct PipelineRunner(conn=...)."
            )

        return execute(
            opportunity_id,
            active_conn,
            version_set=version_set or self._version_set,
            force_new_snapshot=force_new_snapshot,
            snapshot_id=snapshot_id,
        )

    def run_batch(
        self,
        opportunity_ids: list[str],
        conn: sqlite3.Connection | None = None,
        *,
        version_set: EngineVersionSet | None = None,
        force_new_snapshot: bool = True,
    ) -> list[dict[str, Any]]:
        active_conn = conn or self._conn

        if active_conn is None:
            raise ValueError(
                "PipelineRunner.run_batch() requires a connection. "
                "Pass conn= or construct PipelineRunner(conn=...)."
            )

        return execute_batch(
            opportunity_ids,
            active_conn,
            version_set=version_set or self._version_set,
            force_new_snapshot=force_new_snapshot,
        )