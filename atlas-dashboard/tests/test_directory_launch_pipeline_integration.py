"""
atlas/tests/test_directory_launch_pipeline_integration.py

End-to-end integration test for the "directory_launch_v1" pipeline
(AES-006 Phase 2): Investment Committee Decision -> Blueprint ->
Ingestion -> Launch Kit -> Directory Builder -> Preview, run through
the generalized orchestrator framework built in Phase 1.

Uses an in-memory SQLite connection + tmp_path filesystem roots.
No Flask, no UI, no writes outside tmp_path.
"""

from __future__ import annotations

import sqlite3

import pytest

from engines.preview.preview_models import PreviewBuild
from repositories import orchestrator_run_repository as orch_run_repo
from services.investment_committee import (
    ExpansionClassModel,
    LiquidityEvidenceModel,
    PortfolioDecisionResult,
    SynergyReportModel,
)
from services.orchestrator import orchestrator_runner, pipeline_registry
from services.orchestrator.pipelines.directory_launch import (
    PIPELINE_NAME,
    register_directory_launch_pipeline,
)
from services.v2_types import DecisionResult, ScoreBreakdown


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture(autouse=True)
def _clean_registry():
    pipeline_registry.clear_registry()
    yield
    pipeline_registry.clear_registry()


def _committee_decision(recommendation: str = "BUILD") -> PortfolioDecisionResult:
    core = DecisionResult(
        opportunity_id="opp-dl-int-1",
        niche_slug="pet-friendly-travel",
        decision=recommendation,
        confidence=0.7,
        honest_wall_applied=False,
        rationale="test decision",
        score_breakdown=ScoreBreakdown(total_score=72.5),
        geographic_scope="national",
    )
    return PortfolioDecisionResult(
        run_id="run-dl-int-1",
        portfolio_snapshot_id="snap-dl-int-1",
        engine_versions={},
        core_decision=core,
        synergy=SynergyReportModel(
            total_score=0.1, portfolio_snapshot_id="snap-dl-int-1", category="pet", geographic_scope="national"
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
        committee_rationale="Integration test rationale.",
    )


def _seed_payload(conn: sqlite3.Connection, tmp_path, recommendation: str = "BUILD") -> dict:
    return {
        "conn": conn,
        "committee_decision": _committee_decision(recommendation),
        "opportunity_extra": {
            "description": "A pet-friendly travel directory.",
            "target_customer": "Pet owners planning trips",
            "competition_level": "medium",
            "monetization_signals": ["affiliate_booking", "featured_listings"],
        },
        "raw_listings": [
            {
                "id": 1,
                "project_id": 1,
                "business_name": "The Barkley Hotel",
                "category": "Hotels",
                "city": "Columbus",
                "state": "OH",
                "phone": "614-555-0100",
                "website": "https://example.com/barkley",
                "email": None,
                "facebook_url": None,
                "instagram_url": None,
                "tiktok_url": None,
                "linkedin_url": None,
                "youtube_url": None,
                "contact_page_url": None,
                "contact_form_detected": 0,
                "last_enriched_at": None,
                "status": "active",
            },
            {
                "id": 2,
                "project_id": 1,
                "business_name": "Paws Inn",
                "category": "Hotels",
                "city": "Dublin",
                "state": "OH",
                "phone": None,
                "website": None,
                "email": "info@pawsinn.com",
                "facebook_url": None,
                "instagram_url": None,
                "tiktok_url": None,
                "linkedin_url": None,
                "youtube_url": None,
                "contact_page_url": None,
                "contact_form_detected": 0,
                "last_enriched_at": None,
                "status": "active",
            },
        ],
        "project_slug": "pet-friendly-travel",
        "launch_kit_output_root": str(tmp_path / "launch_packages"),
        "projects_root": str(tmp_path / "projects"),
        "preview_root": str(tmp_path / "previews"),
    }


def test_directory_launch_pipeline_runs_all_stages_to_completion(tmp_path):
    conn = _make_conn()
    register_directory_launch_pipeline()

    result = orchestrator_runner.run_pipeline(PIPELINE_NAME, _seed_payload(conn, tmp_path), conn)

    assert result["_cached"] is False

    stages = orch_run_repo.get_stages_for_run(conn, result["run_id"])
    stage_statuses = {s["stage_name"]: s["status"] for s in stages}
    assert stage_statuses == {
        "blueprint": "complete",
        "ingestion": "complete",
        "launch_kit": "complete",
        "build": "complete",
        "preview": "complete",
    }


def test_directory_launch_pipeline_produces_preview_build(tmp_path):
    conn = _make_conn()
    register_directory_launch_pipeline()

    result = orchestrator_runner.run_pipeline(PIPELINE_NAME, _seed_payload(conn, tmp_path), conn)

    # context is JSON-round-tripped for cached replay, so assert on the
    # serialized shape (a PreviewBuild.model_dump()-equivalent dict)
    # rather than an isinstance check.
    preview_result = result["context"]["preview_result"]
    assert isinstance(preview_result, dict)
    assert preview_result["page_count"] >= 1
    assert preview_result["homepage_path"]


def test_directory_launch_pipeline_is_idempotent_on_identical_seed_payload(tmp_path):
    conn = _make_conn()
    register_directory_launch_pipeline()

    payload = _seed_payload(conn, tmp_path)
    result1 = orchestrator_runner.run_pipeline(PIPELINE_NAME, payload, conn)
    result2 = orchestrator_runner.run_pipeline(PIPELINE_NAME, payload, conn)

    assert result2["_cached"] is True
    assert result2["run_id"] == result1["run_id"]

    runs = orch_run_repo.list_runs_for_pipeline(conn, PIPELINE_NAME)
    assert len(runs) == 1


def test_directory_launch_pipeline_halts_on_ineligible_committee_decision(tmp_path):
    conn = _make_conn()
    register_directory_launch_pipeline()

    payload = _seed_payload(conn, tmp_path, recommendation="DEFER")

    with pytest.raises(RuntimeError, match="Pipeline failed"):
        orchestrator_runner.run_pipeline(PIPELINE_NAME, payload, conn)

    runs = orch_run_repo.list_runs_for_pipeline(conn, PIPELINE_NAME)
    assert len(runs) == 1
    assert runs[0]["status"] == "failed"

    stages = orch_run_repo.get_stages_for_run(conn, runs[0]["run_id"])
    stage_statuses = {s["stage_name"]: s["status"] for s in stages}
    assert stage_statuses == {"blueprint": "failed"}
