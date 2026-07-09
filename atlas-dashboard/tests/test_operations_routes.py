"""
atlas/tests/test_operations_routes.py

Flask route tests for routes/operations.py (AES-009A).

Uses the isolated test-Flask-app pattern established in AES-007's
tests/test_orchestrator_runs_routes.py: registers only operations_bp
against a Flask app pointed at the real templates/ directory, rather
than importing the real app.py (avoiding coupling to the full startup
sequence for what is otherwise a self-contained route test).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask

import repositories.run_repository as run_repo
import services.database as database_module
import services.pipeline_execution_service as pipeline_execution_service
from routes.operations import operations_bp
from services.orchestrator import pipeline_registry
from services.investment_committee import (
    ExpansionClassModel,
    LiquidityEvidenceModel,
    PortfolioDecisionResult,
    SynergyReportModel,
)
from services.v2_types import DecisionResult, ScoreBreakdown

TEMPLATES_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _clean_registry():
    pipeline_registry.clear_registry()
    yield
    pipeline_registry.clear_registry()


def _portfolio_decision_result() -> PortfolioDecisionResult:
    core = DecisionResult(
        opportunity_id="opp-route-1",
        niche_slug="pet-friendly-travel",
        decision="BUILD",
        confidence=0.7,
        honest_wall_applied=False,
        rationale="test decision",
        score_breakdown=ScoreBreakdown(total_score=72.5),
        geographic_scope="national",
    )
    return PortfolioDecisionResult(
        run_id="run-route-1",
        portfolio_snapshot_id="snap-route-1",
        engine_versions={},
        core_decision=core,
        synergy=SynergyReportModel(
            total_score=0.1, portfolio_snapshot_id="snap-route-1", category="pet", geographic_scope="national"
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
        portfolio_recommendation="BUILD",
        portfolio_confidence=0.7,
        honest_wall_binding=False,
        committee_rationale="Test rationale for route test.",
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "operations_routes_test.db")
    monkeypatch.setattr(database_module, "DATABASE", db_path)
    monkeypatch.setattr(pipeline_execution_service, "DATABASE", db_path)

    conn = sqlite3.connect(db_path)
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
    conn.execute(
        """
        INSERT INTO businesses
            (id, project_id, business_name, category, city, state, phone, website, status)
        VALUES (1, 1, 'The Barkley Hotel', 'Hotels', 'Columbus', 'OH', '614-555-0100', 'https://example.com', 'active')
        """
    )
    conn.commit()
    conn.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    run_repo.init_run_schema(conn)
    run_repo.insert_run(
        conn,
        {
            "run_id": "run-route-1",
            "input_hash": "hash-run-route-1",
            "opportunity_id": "opp-route-1",
            "portfolio_snapshot_id": "snap-route-1",
            "engine_version_set": "{}",
            "status": "complete",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:10+00:00",
            "failed_at": None,
            "failure_reason": None,
            "result_json": _portfolio_decision_result().json(),
        },
    )
    conn.commit()
    conn.close()

    test_app = Flask(__name__, template_folder=TEMPLATES_DIR)
    test_app.config["TESTING"] = True
    test_app.register_blueprint(operations_bp)

    with test_app.test_client() as test_client:
        yield test_client


def test_operations_center_returns_200_and_shows_directory_launch(client):
    response = client.get("/operations")
    assert response.status_code == 200
    assert b"Directory Launch" in response.data


def test_operations_center_renders_card_from_descriptor_icon_and_route(client):
    """
    AES-009B regression guard: the card's icon and "Configure & Run"
    link come from OperationDescriptor.icon/.route, not template-
    hardcoded values.
    """
    from services.operations_registry import list_operations

    [operation] = list_operations()

    response = client.get("/operations")
    html = response.data.decode("utf-8")

    assert operation.icon in html
    assert f'href="{operation.route}"' in html


def test_post_with_valid_data_returns_200_and_success_message(client):
    response = client.post(
        "/operations/directory-launch/run",
        data={
            "committee_run_id": "run-route-1",
            "project_slug": "pet-friendly-travel",
            "description": "A pet-friendly travel directory.",
            "target_customer": "Pet owners planning trips",
            "competition_level": "medium",
            "monetization_signals": "affiliate_booking, featured_listings",
        },
    )

    assert response.status_code == 200
    assert b"Directory Launch pipeline completed successfully" in response.data


def test_post_with_missing_fields_returns_200_and_failure_message(client):
    response = client.post(
        "/operations/directory-launch/run",
        data={
            "committee_run_id": "",
            "project_slug": "",
            "description": "",
            "target_customer": "",
            "competition_level": "",
            "monetization_signals": "",
        },
    )

    assert response.status_code == 200
    assert b"Missing required field" in response.data
