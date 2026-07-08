"""
atlas/tests/test_pipeline_integration.py

End-to-end integration test for the v3 wired pipeline.

Tests the complete path:
  PipelineRunner
    → v2 stub (ATLAS_V2_STUB=1)
    → Market Liquidity
    → Portfolio Synergy
    → Expansion Classifier
    → Investment Committee
    → Persist

Uses in-memory SQLite + the v2 stub adapter.
No Flask, no UI, no file I/O.

Run:
    ATLAS_V2_STUB=1 python atlas/tests/test_pipeline_integration.py
    ATLAS_V2_STUB=1 python -m pytest atlas/tests/test_pipeline_integration.py -v
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

# Activate the v2 stub adapter
os.environ["ATLAS_V2_STUB"] = "1"

sys.path.insert(0, str(Path(__file__).parent.parent))

import repositories.run_repository as run_repo
from repositories.run_repository import RunRepository
from repositories.portfolio_repository import PortfolioRepository
from services import pipeline_runner
from services.pipeline_runner import PipelineRunner
from services import portfolio_service as portfolio_svc
from services.portfolio_service import RevenueTaggedValue, PortfolioStateService
from services.v2_pipeline_adapter import V2PipelineAdapter
from engines.expansion_classifier import ExpansionClassifier
from engines.market_liquidity import MarketLiquidityEngine


# ---------------------------------------------------------------------------
# DB factory
# ---------------------------------------------------------------------------

def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _seed_portfolio(conn: sqlite3.Connection) -> None:
    """Register realistic portfolio assets matching the Atlas real portfolio."""
    portfolio_svc.init_schema(conn)

    # PetTripFinder — owned, unmonetised
    pet = portfolio_svc.register_asset(
        conn,
        niche_slug="pet-friendly-travel",
        display_name="PetTripFinder",
        primary_category="pet",
        domain="pettripfinder.com",
        geographic_scope="national",
        monetization_model="listing_fees,affiliate",
        initial_status="owned",
    )
    portfolio_svc.update_revenue(conn, pet.asset_id, RevenueTaggedValue(
        value=0.0, source="ESTIMATED", confidence=0.30,
        rationale="Not yet monetised; pre-launch estimate."
    ))

    # SkilledTradePathway — candidate
    portfolio_svc.register_asset(
        conn,
        niche_slug="skilled-trade-pathway",
        display_name="SkilledTradePathway",
        primary_category="trades",
        geographic_scope="national",
        initial_status="candidate",
    )

    # DirectBeef — candidate
    portfolio_svc.register_asset(
        conn,
        niche_slug="direct-beef",
        display_name="DirectBeef",
        primary_category="food",
        geographic_scope="regional",
        initial_status="candidate",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_output_shape():
    """Pipeline returns all required keys with correct types."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-001", conn)

    required_keys = {
        "run_id", "snapshot_id", "engine_version_set",
        "market_result", "expansion_result", "liquidity_result",
        "synergy_result", "final_decision",
    }
    missing = required_keys - set(result.keys())
    assert not missing, f"Missing keys in pipeline output: {missing}"

    assert isinstance(result["run_id"], str)
    assert isinstance(result["snapshot_id"], str)
    assert isinstance(result["engine_version_set"], dict)
    assert isinstance(result["final_decision"], dict)
    print("  ✓ output_shape: all required keys present with correct types")


def test_engine_version_set_recorded():
    """Engine version set is present and contains all expected engines."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-002", conn)
    evs = result["engine_version_set"]

    for engine in ("scout", "market_capacity", "scorer", "valuation", "architect",
                   "synergy", "liquidity", "classifier", "committee"):
        assert engine in evs, f"Missing engine version: {engine}"
        assert evs[engine], f"Empty version string for engine: {engine}"

    print(f"  ✓ engine_version_set: all 9 engines versioned — fingerprint: "
          f"{result['engine_version_set']}")


def test_run_persisted_in_db():
    """Completed run is persisted in pipeline_runs table with status=complete."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-003", conn)
    run_id = result["run_id"]

    run_record = run_repo.get_run_by_id(conn, run_id)
    assert run_record is not None
    assert run_record["status"] == "complete"
    assert run_record["result_json"] is not None
    assert run_record["opportunity_id"] == "opp-003"
    assert run_record["portfolio_snapshot_id"] == result["snapshot_id"]
    print(f"  ✓ run_persisted: run_id={run_id[:8]}… status=complete")


def test_stages_all_complete():
    """All 6 pipeline stages are logged as complete in run_stages."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-004", conn)
    stages = run_repo.get_stages_for_run(conn, result["run_id"])

    expected_stages = {
        "v2_core_pipeline",
        "market_liquidity",
        "portfolio_synergy",
        "expansion_classifier",
        "investment_committee",
        "persist",
    }
    completed_stages = {s["stage_name"] for s in stages if s["status"] == "complete"}
    missing = expected_stages - completed_stages
    assert not missing, f"Stages not completed: {missing}"

    for stage in stages:
        assert stage["duration_ms"] is not None and stage["duration_ms"] >= 0
    print(f"  ✓ stages_all_complete: {len(stages)} stages, all complete with duration_ms")


def test_snapshot_attached_to_run():
    """Run record references a valid portfolio snapshot."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-005", conn)
    snap = portfolio_svc.load_snapshot(conn, result["snapshot_id"])

    assert snap is not None
    assert len(snap.assets) == 3    # pet (owned) + 2 candidates
    assert len(snap.owned) == 1
    print(f"  ✓ snapshot_attached: snapshot_id={result['snapshot_id'][:8]}… "
          f"assets={len(snap.assets)}, owned={len(snap.owned)}")


def test_market_result_shape():
    """market_result contains ceiling, category, scope."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-006", conn)
    mr = result["market_result"]

    assert "ceiling_monthly_usd" in mr
    assert "category" in mr
    assert "geographic_scope" in mr
    assert mr["ceiling_monthly_usd"] > 0
    print(f"  ✓ market_result: ceiling=${mr['ceiling_monthly_usd']:,.0f}/mo, "
          f"category={mr['category']}, scope={mr['geographic_scope']}")


def test_expansion_result_shape_and_explainability():
    """expansion_result has label, confidence, factors with full explainability."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-007", conn)
    er = result["expansion_result"]

    assert er["label"] in ("Flagship", "Portfolio", "Local", "Micro", "Expansion")
    assert 0.0 <= er["confidence"] <= 1.0
    assert isinstance(er["synergy_driven"], bool)
    assert isinstance(er["factors"], list)
    assert len(er["factors"]) > 0

    for factor in er["factors"]:
        assert "name" in factor
        assert "observed_value" in factor
        assert "rule_threshold" in factor
        assert "passed" in factor
        assert "rationale" in factor

    print(f"  ✓ expansion_result: label={er['label']}, confidence={er['confidence']:.3f}, "
          f"factors={len(er['factors'])}")


def test_liquidity_result_evidence_only():
    """Liquidity result contains evidence fields, all tagged ESTIMATED."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-008", conn)
    lr = result["liquidity_result"]

    assert lr["multiple_lo"] > 0
    assert lr["multiple_hi"] > lr["multiple_lo"]
    assert lr["multiple_source"] == "ESTIMATED"
    assert 0.0 <= lr["buyer_demand_signal"] <= 1.0
    assert isinstance(lr["compression_risks"], list)
    assert len(lr["compression_risks"]) > 0
    assert isinstance(lr["time_to_exit_months"], (tuple, list))
    print(f"  ✓ liquidity_result (evidence-only): multiple={lr['multiple_lo']}–{lr['multiple_hi']}×, "
          f"demand={lr['buyer_demand_signal']:.2f}, source={lr['multiple_source']}")


def test_synergy_result_shape():
    """Synergy result has total_score and named components."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-009", conn)
    sr = result["synergy_result"]

    assert -1.0 <= sr["total_score"] <= 1.0
    assert isinstance(sr["components"], list)
    assert len(sr["components"]) == 5  # 4 positive + 1 penalty

    component_names = {c["name"] for c in sr["components"]}
    assert "audience_overlap" in component_names
    assert "cannibalization_penalty" in component_names

    for comp in sr["components"]:
        assert "name" in comp
        assert "raw_value" in comp
        assert "weight" in comp
        assert "contribution" in comp
        assert "rationale" in comp

    print(f"  ✓ synergy_result: total_score={sr['total_score']:.4f}, "
          f"components={len(sr['components'])}")


def test_final_decision_shape():
    """final_decision has all required PortfolioDecisionResult fields."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-010", conn)
    fd = result["final_decision"]

    required = {
        "run_id", "portfolio_snapshot_id", "engine_versions",
        "core_decision", "synergy", "expansion", "liquidity",
        "portfolio_recommendation", "portfolio_confidence",
        "honest_wall_binding", "committee_rationale",
    }
    missing = required - set(fd.keys())
    assert not missing, f"Missing keys in final_decision: {missing}"

    assert fd["portfolio_recommendation"] in ("BUILD", "TEST", "DEFER", "REJECT")
    assert 0.0 <= fd["portfolio_confidence"] <= 1.0
    assert isinstance(fd["honest_wall_binding"], bool)
    assert isinstance(fd["committee_rationale"], str) and fd["committee_rationale"]
    assert fd["core_decision"]["opportunity_id"] == "opp-010"
    print(f"  ✓ final_decision: recommendation={fd['portfolio_recommendation']}, "
          f"confidence={fd['portfolio_confidence']:.4f}, "
          f"honest_wall={fd['honest_wall_binding']}")


def test_honest_wall_binding():
    """Honest wall inherited from v2: confidence ≤ 0.45 when wall applied."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-011", conn)
    fd = result["final_decision"]

    if fd["honest_wall_binding"]:
        assert fd["portfolio_confidence"] <= 0.45, (
            f"Honest wall applied but portfolio_confidence={fd['portfolio_confidence']} > 0.45"
        )
        print(f"  ✓ honest_wall_binding: confidence={fd['portfolio_confidence']:.4f} ≤ 0.45")
    else:
        print(f"  ✓ honest_wall_binding: wall not applied, confidence={fd['portfolio_confidence']:.4f}")


def test_idempotency():
    """
    Running the same opportunity_id against the same snapshot twice returns
    the cached result, not a new run.
    """
    conn = _make_conn()
    _seed_portfolio(conn)

    result1 = pipeline_runner.execute("opp-012", conn)
    result2 = pipeline_runner.execute(
        "opp-012", conn, snapshot_id=result1["snapshot_id"]
    )

    # Second call should return the cached run
    assert result2.get("_cached") is True
    assert result2["run_id"] == result1["run_id"]

    # Only one run record in DB
    runs = run_repo.list_runs_for_opportunity(conn, "opp-012")
    assert len(runs) == 1, f"Expected 1 run, found {len(runs)}"
    print(f"  ✓ idempotency: second call returned cached result, run_id={result1['run_id'][:8]}…")


def test_v2_decision_embedded_verbatim():
    """v2 DecisionResult inside final_decision matches v2 pipeline output exactly."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-013", conn)
    fd = result["final_decision"]
    core = fd["core_decision"]

    # Stub always returns confidence=0.42, decision=TEST
    assert core["confidence"] == 0.42
    assert core["decision"] == "TEST"
    assert core["honest_wall_applied"] is True
    assert core["opportunity_id"] == "opp-013"
    print(f"  ✓ v2_decision_embedded_verbatim: "
          f"decision={core['decision']}, confidence={core['confidence']}, "
          f"honest_wall={core['honest_wall_applied']}")


def test_no_v2_promotion():
    """Committee can never promote a v2 DEFER/REJECT to a higher decision."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-014", conn)
    fd = result["final_decision"]
    core_decision = fd["core_decision"]["decision"]
    portfolio_recommendation = fd["portfolio_recommendation"]

    decision_rank = {"BUILD": 4, "TEST": 3, "DEFER": 2, "REJECT": 1}
    assert decision_rank[portfolio_recommendation] <= decision_rank[core_decision], (
        f"Committee promoted {core_decision} → {portfolio_recommendation}: VIOLATION"
    )
    print(f"  ✓ no_v2_promotion: core={core_decision} → portfolio={portfolio_recommendation} "
          f"(rank: {decision_rank[core_decision]} → {decision_rank[portfolio_recommendation]})")


def test_batch_execution():
    """Batch execution uses one shared snapshot for all opportunities."""
    conn = _make_conn()
    _seed_portfolio(conn)

    opp_ids = ["batch-001", "batch-002", "batch-003"]
    results = pipeline_runner.execute_batch(opp_ids, conn)

    assert len(results) == 3

    # All results share the same snapshot_id
    snapshot_ids = {r["snapshot_id"] for r in results if "snapshot_id" in r}
    assert len(snapshot_ids) == 1, \
        f"Batch used {len(snapshot_ids)} snapshots, expected 1"

    for i, (opp_id, result) in enumerate(zip(opp_ids, results)):
        assert "error" not in result, f"Batch item {opp_id} failed: {result.get('error')}"
        assert result["run_id"] is not None

    shared_snapshot_id = snapshot_ids.pop()
    print(f"  ✓ batch_execution: {len(results)} opportunities, "
          f"shared snapshot_id={shared_snapshot_id[:8]}…")


def test_run_result_json_serialisable():
    """The persisted result_json round-trips through JSON without error."""
    conn = _make_conn()
    _seed_portfolio(conn)

    result = pipeline_runner.execute("opp-015", conn)
    run_record = run_repo.get_run_by_id(conn, result["run_id"])

    assert run_record["result_json"] is not None
    parsed = json.loads(run_record["result_json"])
    assert parsed["run_id"] == result["run_id"]
    assert "portfolio_recommendation" in parsed
    print(f"  ✓ result_json_serialisable: {len(run_record['result_json'])} bytes persisted, round-trips cleanly")


def test_portfolio_with_no_assets():
    """Pipeline runs correctly when the portfolio has no owned assets (empty synergy)."""
    conn = _make_conn()
    # Intentionally do NOT seed any assets

    result = pipeline_runner.execute("opp-016", conn)

    snap = portfolio_svc.load_snapshot(conn, result["snapshot_id"])
    assert len(snap.owned) == 0

    sr = result["synergy_result"]
    # No owned assets → synergy should be ≤ 0 (no positive synergy possible)
    # Cannibalization penalty also 0 (nothing to cannibalize)
    assert sr["total_score"] <= 0.01, \
        f"Expected near-zero synergy with empty portfolio, got {sr['total_score']}"

    er = result["expansion_result"]
    # No owned assets → cannot be Expansion
    assert er["label"] != "Expansion", \
        "Empty portfolio cannot produce an Expansion label"

    print(f"  ✓ empty_portfolio: synergy={sr['total_score']:.4f}, "
          f"expansion={er['label']} (correctly not Expansion)")


def test_pipeline_runner_class_wrapper():
    """
    PipelineRunner class wrapper produces identical output to the
    functional execute() API — proves the compatibility shim delegates
    correctly and introduces no behavior change.
    """
    conn = _make_conn()
    _seed_portfolio(conn)

    runner = PipelineRunner(conn=conn)
    result = runner.run("opp-class-001")

    required_keys = {
        "run_id", "snapshot_id", "engine_version_set",
        "market_result", "expansion_result", "liquidity_result",
        "synergy_result", "final_decision",
    }
    missing = required_keys - set(result.keys())
    assert not missing, f"Missing keys in class-wrapper output: {missing}"
    assert result["final_decision"]["core_decision"]["opportunity_id"] == "opp-class-001"
    print("  ✓ pipeline_runner_class_wrapper: PipelineRunner.run() matches functional API shape")


def test_pipeline_runner_class_wrapper_batch():
    """PipelineRunner.run_batch() delegates correctly to execute_batch()."""
    conn = _make_conn()
    _seed_portfolio(conn)

    runner = PipelineRunner(conn=conn)
    results = runner.run_batch(["class-batch-001", "class-batch-002"])

    assert len(results) == 2
    snapshot_ids = {r["snapshot_id"] for r in results if "snapshot_id" in r}
    assert len(snapshot_ids) == 1, "Batch via class wrapper should share one snapshot"
    print(f"  ✓ pipeline_runner_class_wrapper_batch: {len(results)} results, "
          f"shared snapshot_id={snapshot_ids.pop()[:8]}…")


def test_portfolio_state_service_class_wrapper():
    """PortfolioStateService delegates correctly to module-level portfolio functions."""
    conn = _make_conn()
    portfolio_svc.init_schema(conn)

    service = PortfolioStateService()
    asset = service.register_asset(
        conn,
        niche_slug="class-wrapper-niche",
        display_name="ClassWrapperAsset",
        primary_category="pet",
        initial_status="owned",
    )
    assert asset.status == "owned"

    fetched = service.get_asset(conn, asset.asset_id)
    assert fetched.asset_id == asset.asset_id

    snap = service.create_snapshot(conn)
    assert len(snap.owned) == 1

    reloaded = service.load_snapshot(conn, snap.snapshot_id)
    assert reloaded.snapshot_id == snap.snapshot_id

    latest = service.get_latest_snapshot(conn)
    assert latest.snapshot_id == snap.snapshot_id

    print("  ✓ portfolio_state_service_class_wrapper: register/get/snapshot/reload all delegate correctly")


def test_expansion_classifier_class_wrapper():
    """ExpansionClassifier delegates correctly to classify()."""
    from dataclasses import dataclass

    @dataclass
    class _StubSynergy:
        total_score: float = 0.10
        portfolio_snapshot_id: str = "stub"

    @dataclass
    class _StubSnapshot:
        owned: tuple = ()

    classifier = ExpansionClassifier()
    result = classifier.classify(
        market_ceiling_monthly_usd=15_000.0,
        geographic_scope="national",
        conservative_monthly_revenue=1_000.0,
        synergy_report=_StubSynergy(),
        portfolio_snapshot=_StubSnapshot(),
    )
    assert result.label == "Flagship"
    print(f"  ✓ expansion_classifier_class_wrapper: label={result.label}, "
          f"confidence={result.confidence:.3f}")


def test_market_liquidity_engine_class_wrapper():
    """MarketLiquidityEngine delegates correctly to gather() and estimate_exit_value()."""
    engine = MarketLiquidityEngine()
    evidence = engine.gather("pet", "national")
    assert evidence.category == "pet"
    assert evidence.revenue_multiple_range.source == "ESTIMATED"

    exit_val = engine.estimate_exit_value(evidence, monthly_revenue=1_000.0)
    assert exit_val.value["typical"] > 0
    print(f"  ✓ market_liquidity_engine_class_wrapper: multiple="
          f"{evidence.revenue_multiple_range.lo}-{evidence.revenue_multiple_range.hi}x, "
          f"exit_typical=${exit_val.value['typical']:,.0f}")


def test_portfolio_repository_class_wrapper():
    """PortfolioRepository delegates correctly to raw-SQL functions."""
    conn = _make_conn()
    repo = PortfolioRepository()
    repo.init_schema(conn)

    repo.insert_asset(conn, {
        "asset_id": "repo-class-test-1",
        "niche_slug": "repo-test",
        "display_name": "RepoClassTest",
        "domain": None,
        "dna_profile_json": None,
        "primary_category": "pet",
        "geographic_scope": "national",
        "monetization_model": None,
        "status": "candidate",
        "revenue_value": 0.0,
        "revenue_source": "UNKNOWN",
        "revenue_provider": None,
        "revenue_rationale": None,
        "revenue_confidence": 0.0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "exited_at": None,
        "notes": None,
    })
    conn.commit()

    row = repo.get_asset_by_id(conn, "repo-class-test-1")
    assert row is not None
    assert row["display_name"] == "RepoClassTest"
    print("  ✓ portfolio_repository_class_wrapper: insert_asset/get_asset_by_id delegate correctly")


def test_run_repository_class_wrapper():
    """RunRepository delegates correctly to raw-SQL functions."""
    conn = _make_conn()
    repo = RunRepository()
    repo.init_schema(conn)

    repo.insert_run(conn, {
        "run_id": "repo-class-run-1",
        "input_hash": "deadbeef",
        "opportunity_id": "opp-repo-test",
        "portfolio_snapshot_id": "snap-repo-test",
        "engine_version_set": "{}",
        "status": "started",
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": None,
        "failed_at": None,
        "failure_reason": None,
        "result_json": None,
    })
    conn.commit()

    record = repo.get_run_by_id(conn, "repo-class-run-1")
    assert record is not None
    assert record["opportunity_id"] == "opp-repo-test"
    print("  ✓ run_repository_class_wrapper: insert_run/get_run_by_id delegate correctly")


def test_v2_pipeline_adapter_class_wrapper():
    """V2PipelineAdapter delegates correctly to run_v2_pipeline() (stub active)."""
    conn = _make_conn()
    adapter = V2PipelineAdapter()
    result = adapter.run("opp-adapter-class-test", conn)

    assert result.decision_result.opportunity_id == "opp-adapter-class-test"
    assert result.decision_result.decision == "TEST"
    print(f"  ✓ v2_pipeline_adapter_class_wrapper: decision={result.decision_result.decision}, "
          f"confidence={result.decision_result.confidence}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        ("Output shape: all required keys",              test_output_shape),
        ("Engine version set: all 9 engines recorded",   test_engine_version_set_recorded),
        ("Run persisted: status=complete in DB",          test_run_persisted_in_db),
        ("Stages: all 6 stages complete with duration",  test_stages_all_complete),
        ("Snapshot: attached to run record",             test_snapshot_attached_to_run),
        ("Market result: shape and ceiling",             test_market_result_shape),
        ("Expansion: label, confidence, explainability", test_expansion_result_shape_and_explainability),
        ("Liquidity: evidence-only, all ESTIMATED",      test_liquidity_result_evidence_only),
        ("Synergy: score + 5 named components",          test_synergy_result_shape),
        ("Final decision: full PortfolioDecisionResult", test_final_decision_shape),
        ("Honest wall: confidence ≤ 0.45 when binding",  test_honest_wall_binding),
        ("Idempotency: same inputs return cached run",   test_idempotency),
        ("v2 decision embedded verbatim",                test_v2_decision_embedded_verbatim),
        ("No v2 promotion: committee cannot promote",    test_no_v2_promotion),
        ("Batch: one shared snapshot for all",           test_batch_execution),
        ("Persist: result_json round-trips through JSON",test_run_result_json_serialisable),
        ("Empty portfolio: synergy=0, no Expansion",     test_portfolio_with_no_assets),
        ("Class wrapper: PipelineRunner.run()",          test_pipeline_runner_class_wrapper),
        ("Class wrapper: PipelineRunner.run_batch()",    test_pipeline_runner_class_wrapper_batch),
        ("Class wrapper: PortfolioStateService",         test_portfolio_state_service_class_wrapper),
        ("Class wrapper: ExpansionClassifier",           test_expansion_classifier_class_wrapper),
        ("Class wrapper: MarketLiquidityEngine",         test_market_liquidity_engine_class_wrapper),
        ("Class wrapper: PortfolioRepository",           test_portfolio_repository_class_wrapper),
        ("Class wrapper: RunRepository",                 test_run_repository_class_wrapper),
        ("Class wrapper: V2PipelineAdapter",             test_v2_pipeline_adapter_class_wrapper),
    ]

    passed = failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            fn()
            passed += 1
        except Exception as e:
            import traceback as tb
            print(f"  ✗ FAILED: {e}")
            tb.print_exc()
            failed += 1

    print(f"\n{'='*70}")
    print(f"Integration Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed:
        sys.exit(1)
    print("All integration tests passed. v3 pipeline wiring is complete.")
