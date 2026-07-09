"""
atlas/tests/test_pipeline_execution_service.py

Unit tests for services/pipeline_execution_service.py (AES-009A).

Uses a real temp sqlite file (not :memory:) since both the service and
Database() open their own connections per call. services.database.
DATABASE and services.pipeline_execution_service.DATABASE are both
monkeypatched to the same temp path (Database() has no constructor
override, so this is the only way to isolate it in tests).
"""

from __future__ import annotations

import json
import sqlite3

import pytest

import repositories.run_repository as run_repo
import services.database as database_module
import services.pipeline_execution_service as pipeline_execution_service
from repositories import orchestrator_run_repository as orch_run_repo
from services.investment_committee import (
    ExpansionClassModel,
    LiquidityEvidenceModel,
    PortfolioDecisionResult,
    SynergyReportModel,
)
from services.orchestrator import pipeline_registry
from services.v2_types import DecisionResult, ScoreBreakdown


@pytest.fixture(autouse=True)
def _clean_registry():
    pipeline_registry.clear_registry()
    yield
    pipeline_registry.clear_registry()


@pytest.fixture
def db_path(tmp_path, monkeypatch) -> str:
    path = str(tmp_path / "pipeline_execution_test.db")
    monkeypatch.setattr(database_module, "DATABASE", path)
    monkeypatch.setattr(pipeline_execution_service, "DATABASE", path)

    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE businesses (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            business_name TEXT,
            category TEXT,
            city TEXT,
            state TEXT,
            phone TEXT,
            website TEXT,
            status TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    return path


def _seed_business(db_path: str, **overrides) -> None:
    row = {
        "id": 1,
        "project_id": 1,
        "business_name": "The Barkley Hotel",
        "category": "Hotels",
        "city": "Columbus",
        "state": "OH",
        "phone": "614-555-0100",
        "website": "https://example.com/barkley",
        "status": "active",
    }
    row.update(overrides)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO businesses
            (id, project_id, business_name, category, city, state, phone, website, status)
        VALUES (:id, :project_id, :business_name, :category, :city, :state, :phone, :website, :status)
        """,
        row,
    )
    conn.commit()
    conn.close()


def _portfolio_decision_result(recommendation: str = "BUILD") -> PortfolioDecisionResult:
    core = DecisionResult(
        opportunity_id="opp-pe-1",
        niche_slug="pet-friendly-travel",
        decision=recommendation,
        confidence=0.7,
        honest_wall_applied=False,
        rationale="test decision",
        score_breakdown=ScoreBreakdown(total_score=72.5),
        geographic_scope="national",
    )
    return PortfolioDecisionResult(
        run_id="run-pe-1",
        portfolio_snapshot_id="snap-pe-1",
        engine_versions={},
        core_decision=core,
        synergy=SynergyReportModel(
            total_score=0.1, portfolio_snapshot_id="snap-pe-1", category="pet", geographic_scope="national"
        ),
        expansion=ExpansionClassModel(
            label="Portfolio", confidence=0.6, plain_english="Adds diversification.", synergy_driven=False
        ),
        liquidity=LiquidityEvidenceModel(
            category="pet",
            geographic_scope="national",
            multiple_lo=2.0,
            multiple_hi=4.0,
            multiple_typical=3.0,
            multiple_source="ESTIMATED",
            multiple_confidence=0.5,
            buyer_demand_signal=0.5,
            buyer_demand_source="ESTIMATED",
            time_to_exit_lo_months=6,
            time_to_exit_hi_months=12,
            buyer_depth_estimate=5,
            compression_risks=[],
        ),
        portfolio_recommendation=recommendation,
        portfolio_confidence=0.7,
        honest_wall_binding=False,
        committee_rationale="Test rationale for pipeline execution service.",
    )


def _seed_committee_run(db_path: str, run_id: str, status: str = "complete", recommendation: str = "BUILD") -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    run_repo.init_run_schema(conn)

    result_json = _portfolio_decision_result(recommendation).json() if status == "complete" else None

    run_repo.insert_run(
        conn,
        {
            "run_id": run_id,
            "input_hash": f"hash-{run_id}",
            "opportunity_id": "opp-pe-1",
            "portfolio_snapshot_id": "snap-pe-1",
            "engine_version_set": "{}",
            "status": status,
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:10+00:00" if status == "complete" else None,
            "failed_at": None,
            "failure_reason": None,
            "result_json": result_json,
        },
    )
    conn.commit()
    conn.close()


VALID_FORM = {
    "project_slug": "pet-friendly-travel",
    "description": "A pet-friendly travel directory.",
    "target_customer": "Pet owners planning trips",
    "competition_level": "medium",
    "monetization_signals": "affiliate_booking, featured_listings",
}


def test_missing_fields_returns_failure_without_touching_pipeline(db_path):
    result = pipeline_execution_service.start_directory_launch_run(
        committee_run_id="",
        project_slug="",
        description="",
        target_customer="",
        competition_level="",
        monetization_signals="",
        db_path=db_path,
    )

    assert result["success"] is False
    assert result["run_id"] is None
    assert "Missing required field" in result["message"]


def test_unknown_committee_run_id_returns_failure(db_path):
    result = pipeline_execution_service.start_directory_launch_run(
        committee_run_id="does-not-exist",
        db_path=db_path,
        **VALID_FORM,
    )

    assert result["success"] is False
    assert result["run_id"] is None
    assert "No investment committee run found" in result["message"]


def test_incomplete_committee_run_returns_failure(db_path):
    _seed_committee_run(db_path, "run-started", status="started")

    result = pipeline_execution_service.start_directory_launch_run(
        committee_run_id="run-started",
        db_path=db_path,
        **VALID_FORM,
    )

    assert result["success"] is False
    assert "has not completed yet" in result["message"]


def test_successful_run_creates_orchestrator_run(db_path):
    _seed_committee_run(db_path, "run-complete")
    _seed_business(db_path)

    result = pipeline_execution_service.start_directory_launch_run(
        committee_run_id="run-complete",
        db_path=db_path,
        **VALID_FORM,
    )

    assert result["success"] is True
    assert result["run_id"]
    assert result["cached"] is False

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    orch_run = orch_run_repo.get_run_by_id(conn, result["run_id"])
    conn.close()

    assert orch_run is not None
    assert orch_run["status"] == "complete"
    assert orch_run["pipeline_name"] == "directory_launch_v1"


def test_on_input_hash_known_callback_fires_before_pipeline_completes_and_resolves_to_run(db_path):
    """
    AES-011: on_input_hash_known must be called with a hash that, once
    the pipeline has started, resolves (via the existing
    orchestrator_run_repository.get_run_by_input_hash) to the same
    run_id the call ultimately returns — this is the correlation a
    live monitor depends on to find a job's run before it finishes.
    """
    _seed_committee_run(db_path, "run-hash-callback")
    _seed_business(db_path)

    captured_hashes = []

    result = pipeline_execution_service.start_directory_launch_run(
        committee_run_id="run-hash-callback",
        db_path=db_path,
        on_input_hash_known=captured_hashes.append,
        **VALID_FORM,
    )

    assert len(captured_hashes) == 1
    assert result["success"] is True

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    resolved_run = orch_run_repo.get_run_by_input_hash(conn, captured_hashes[0])
    conn.close()

    assert resolved_run is not None
    assert resolved_run["run_id"] == result["run_id"]


def test_ineligible_committee_decision_returns_failure(db_path):
    """
    A DEFER/REJECT committee decision fails inside the pipeline's
    blueprint stage (not before it starts), so a real orchestrator run
    row exists with the failure recorded — AES-009C: the service must
    recover that run_id and expose it for a "View Run Details" link,
    and the message must not contain a raw traceback.
    """
    _seed_committee_run(db_path, "run-defer", recommendation="DEFER")
    _seed_business(db_path)

    result = pipeline_execution_service.start_directory_launch_run(
        committee_run_id="run-defer",
        db_path=db_path,
        **VALID_FORM,
    )

    assert result["success"] is False
    assert result["run_id"]
    assert "Directory Launch pipeline failed:" in result["message"]
    assert "Traceback" not in result["message"]

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    orch_run = orch_run_repo.get_run_by_id(conn, result["run_id"])
    conn.close()

    assert orch_run is not None
    assert orch_run["status"] == "failed"


def test_second_call_with_identical_inputs_is_cached(db_path):
    _seed_committee_run(db_path, "run-repeat")
    _seed_business(db_path)

    first = pipeline_execution_service.start_directory_launch_run(
        committee_run_id="run-repeat",
        db_path=db_path,
        **VALID_FORM,
    )
    second = pipeline_execution_service.start_directory_launch_run(
        committee_run_id="run-repeat",
        db_path=db_path,
        **VALID_FORM,
    )

    assert first["success"] is True
    assert second["success"] is True
    assert second["cached"] is True
    assert second["run_id"] == first["run_id"]
