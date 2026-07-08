"""
atlas/tests/test_directory_launch_adapters.py

Unit tests for services/orchestrator/adapters/directory_launch_adapters.py
(AES-006 Phase 2). Exercises each adapter in isolation against the
real, unmodified services it wires together — no mocking of Atlas
subsystems, only fixture data for the seed payload.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engines.directory_blueprint.blueprint_models import CategoryNode as BlueprintCategoryNode
from engines.preview.preview_models import PreviewBuild
from engines.directory_builder.models import BuildResult
from services.directory_ingestion_service import IngestionResult
from services.investment_committee import (
    ExpansionClassModel,
    LiquidityEvidenceModel,
    PortfolioDecisionResult,
    SynergyReportModel,
)
from services.v2_types import DecisionResult, ScoreBreakdown
from services.orchestrator.adapters import directory_launch_adapters as adapters


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _committee_decision(
    recommendation: str = "BUILD", geographic_scope: str = "national"
) -> PortfolioDecisionResult:
    core = DecisionResult(
        opportunity_id="opp-dl-1",
        niche_slug="pet-friendly-travel",
        decision=recommendation,
        confidence=0.7,
        honest_wall_applied=False,
        rationale="test decision",
        score_breakdown=ScoreBreakdown(total_score=72.5),
        geographic_scope=geographic_scope,
    )
    return PortfolioDecisionResult(
        run_id="run-dl-1",
        portfolio_snapshot_id="snap-dl-1",
        engine_versions={},
        core_decision=core,
        synergy=SynergyReportModel(
            total_score=0.1,
            portfolio_snapshot_id="snap-dl-1",
            category="pet",
            geographic_scope=geographic_scope,
        ),
        expansion=ExpansionClassModel(
            label="Portfolio",
            confidence=0.6,
            plain_english="Adds diversification.",
            synergy_driven=False,
        ),
        liquidity=LiquidityEvidenceModel(
            category="pet",
            geographic_scope=geographic_scope,
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
        committee_rationale="Test rationale for directory launch pipeline.",
    )


def _opportunity_extra() -> dict:
    return {
        "description": "A pet-friendly travel directory.",
        "target_customer": "Pet owners planning trips",
        "competition_level": "medium",
        "monetization_signals": ["affiliate_booking", "featured_listings"],
    }


def _raw_listing_rows() -> list[dict]:
    return [
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
    ]


# ---------------------------------------------------------------------------
# blueprint_stage
# ---------------------------------------------------------------------------

def test_blueprint_stage_generates_blueprint_for_build_recommendation():
    conn = _make_conn()
    blueprint = adapters.blueprint_stage(conn, _committee_decision("BUILD"), _opportunity_extra())

    assert blueprint.project_profile.project_slug
    assert blueprint.data_confidence_tag is not None


def test_blueprint_stage_raises_when_opportunity_extra_missing_keys():
    conn = _make_conn()
    incomplete_extra = {"description": "Missing the rest."}

    with pytest.raises(adapters.DirectoryLaunchAdapterError, match="missing required keys"):
        adapters.blueprint_stage(conn, _committee_decision("BUILD"), incomplete_extra)


def test_blueprint_stage_raises_when_decision_not_eligible():
    conn = _make_conn()
    with pytest.raises(adapters.DirectoryLaunchAdapterError, match="halted at blueprint stage"):
        adapters.blueprint_stage(conn, _committee_decision("DEFER"), _opportunity_extra())


def test_blueprint_stage_reject_also_not_eligible():
    conn = _make_conn()
    with pytest.raises(adapters.DirectoryLaunchAdapterError, match="halted at blueprint stage"):
        adapters.blueprint_stage(conn, _committee_decision("REJECT"), _opportunity_extra())


# ---------------------------------------------------------------------------
# category tree flattening (ingestion_stage helper)
# ---------------------------------------------------------------------------

def test_flatten_category_tree_sets_parent_slug_across_two_levels():
    tree = [
        BlueprintCategoryNode(
            name="Hotels",
            slug="hotels",
            subcategories=[
                BlueprintCategoryNode(name="Pet-Friendly Hotels", slug="pet-friendly-hotels", subcategories=[]),
            ],
        ),
        BlueprintCategoryNode(name="Campgrounds", slug="campgrounds", subcategories=[]),
    ]

    flat = adapters._flatten_category_tree(tree)

    by_slug = {node.slug: node for node in flat}
    assert by_slug["hotels"].parent_slug is None
    assert by_slug["pet-friendly-hotels"].parent_slug == "hotels"
    assert by_slug["campgrounds"].parent_slug is None
    assert len(flat) == 3


# ---------------------------------------------------------------------------
# ingestion_stage
# ---------------------------------------------------------------------------

def test_ingestion_stage_produces_seed_package_from_raw_listings():
    conn = _make_conn()
    blueprint = adapters.blueprint_stage(conn, _committee_decision("BUILD"), _opportunity_extra())

    result = adapters.ingestion_stage(conn, blueprint, _raw_listing_rows())

    assert isinstance(result, IngestionResult)
    assert len(result.package.businesses) == 2


# ---------------------------------------------------------------------------
# launch_kit_stage
# ---------------------------------------------------------------------------

def test_launch_kit_stage_writes_package_under_given_output_root(tmp_path):
    conn = _make_conn()
    blueprint = adapters.blueprint_stage(conn, _committee_decision("BUILD"), _opportunity_extra())
    ingestion_result = adapters.ingestion_stage(conn, blueprint, _raw_listing_rows())

    output_root = tmp_path / "launch_packages"
    launch_kit_result = adapters.launch_kit_stage(
        blueprint, ingestion_result, blueprint.project_profile.project_slug, str(output_root)
    )

    package_dir = launch_kit_result["package_dir"]
    assert isinstance(package_dir, Path)
    assert package_dir.exists()
    assert output_root in package_dir.parents
    assert launch_kit_result["warnings"] == []


def test_launch_kit_stage_writes_url_map_with_path_column(tmp_path):
    """
    Regression test for the Launch Kit <-> Directory Builder url_map
    shape mismatch: the engine always writes a "url" CSV column, but
    Directory Builder's UrlMapEntry model requires "path". Confirms
    _patch_url_map_csv_column actually rewrites the header.
    """
    conn = _make_conn()
    blueprint = adapters.blueprint_stage(conn, _committee_decision("BUILD"), _opportunity_extra())
    ingestion_result = adapters.ingestion_stage(conn, blueprint, _raw_listing_rows())

    launch_kit_result = adapters.launch_kit_stage(
        blueprint, ingestion_result, blueprint.project_profile.project_slug, str(tmp_path / "launch_packages")
    )

    url_map_path = launch_kit_result["package_dir"] / "url_map.csv"
    header = url_map_path.read_text(encoding="utf-8").splitlines()[0]
    assert "path" in header.split(",")
    assert "url" not in header.split(",")


def test_launch_kit_stage_writes_locations_with_city_key(tmp_path):
    """
    Regression test for the Launch Kit locations.json shape mismatch:
    the engine's own derivation writes a "name" key, but Directory
    Builder's LocationDef model requires "city". Confirms the adapter's
    explicit, city-keyed locations avoid that path entirely.
    """
    conn = _make_conn()
    blueprint = adapters.blueprint_stage(conn, _committee_decision("BUILD"), _opportunity_extra())
    ingestion_result = adapters.ingestion_stage(conn, blueprint, _raw_listing_rows())

    launch_kit_result = adapters.launch_kit_stage(
        blueprint, ingestion_result, blueprint.project_profile.project_slug, str(tmp_path / "launch_packages")
    )

    locations_path = launch_kit_result["package_dir"] / "locations.json"
    import json

    locations = json.loads(locations_path.read_text(encoding="utf-8"))
    assert len(locations) >= 1
    assert all("city" in entry for entry in locations)


def test_launch_kit_stage_skips_listing_with_no_categories_and_warns(tmp_path):
    conn = _make_conn()
    blueprint = adapters.blueprint_stage(conn, _committee_decision("BUILD"), _opportunity_extra())

    rows = _raw_listing_rows()
    del rows[0]["category"]  # normalizer will produce zero categories for this listing
    ingestion_result = adapters.ingestion_stage(conn, blueprint, rows)

    launch_kit_result = adapters.launch_kit_stage(
        blueprint,
        ingestion_result,
        blueprint.project_profile.project_slug,
        str(tmp_path / "launch_packages"),
    )

    assert any("no categories" in warning for warning in launch_kit_result["warnings"])


# ---------------------------------------------------------------------------
# build_stage
# ---------------------------------------------------------------------------

def test_build_stage_produces_assembly_for_expected_project_slug(tmp_path):
    conn = _make_conn()
    blueprint = adapters.blueprint_stage(conn, _committee_decision("BUILD"), _opportunity_extra())
    ingestion_result = adapters.ingestion_stage(conn, blueprint, _raw_listing_rows())
    launch_kit_result = adapters.launch_kit_stage(
        blueprint, ingestion_result, blueprint.project_profile.project_slug, str(tmp_path / "launch_packages")
    )

    build_result = adapters.build_stage(launch_kit_result, str(tmp_path / "projects"))

    assert isinstance(build_result, BuildResult)
    assert build_result.assembly.project_slug == blueprint.project_profile.project_slug


# ---------------------------------------------------------------------------
# preview_stage
# ---------------------------------------------------------------------------

def test_preview_stage_produces_preview_build(tmp_path):
    conn = _make_conn()
    blueprint = adapters.blueprint_stage(conn, _committee_decision("BUILD"), _opportunity_extra())
    ingestion_result = adapters.ingestion_stage(conn, blueprint, _raw_listing_rows())
    launch_kit_result = adapters.launch_kit_stage(
        blueprint, ingestion_result, blueprint.project_profile.project_slug, str(tmp_path / "launch_packages")
    )
    build_result = adapters.build_stage(launch_kit_result, str(tmp_path / "projects"))

    preview = adapters.preview_stage(build_result, str(tmp_path / "previews"))

    assert isinstance(preview, PreviewBuild)
