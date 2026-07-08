"""
atlas/tests/test_v3_modules.py

End-to-end test harness for:
  - Portfolio State Service (register, transition, snapshot, reload)
  - Expansion Classifier
  - Market Liquidity Engine

Runs against an in-memory SQLite database — no file I/O, no Flask.
Execute: python -m pytest atlas/tests/test_v3_modules.py -v
   or:   python atlas/tests/test_v3_modules.py  (if run directly)
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.portfolio_service import (
    RevenueTaggedValue,
    init_schema,
    register_asset,
    transition_status,
    update_revenue,
    create_snapshot,
    load_snapshot,
    get_latest_snapshot,
    list_assets,
)
from engines import market_liquidity as liquidity_engine
from engines.market_liquidity import DataSource, estimate_exit_value
from engines.expansion_classifier import classify, ExpansionClass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    init_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# Minimal stub SynergyReport for classifier tests
# (real SynergyReport comes from portfolio_synergy engine)
# ---------------------------------------------------------------------------

from dataclasses import dataclass

@dataclass(frozen=True)
class _StubSynergyReport:
    total_score: float
    portfolio_snapshot_id: str = "stub"


# ---------------------------------------------------------------------------
# Portfolio State Service Tests
# ---------------------------------------------------------------------------

def test_register_asset_defaults():
    conn = _make_conn()
    asset = register_asset(
        conn,
        niche_slug="pet-friendly-travel",
        display_name="PetTripFinder",
        primary_category="pet",
        domain="pettripfinder.com",
        geographic_scope="national",
        initial_status="owned",
    )
    assert asset.asset_id is not None
    assert asset.status == "owned"
    assert asset.revenue.source == "UNKNOWN"   # honesty default
    assert asset.revenue.value == 0.0
    print("  ✓ register_asset: defaults to UNKNOWN revenue when not supplied")


def test_register_asset_with_verified_revenue():
    conn = _make_conn()
    rev = RevenueTaggedValue(
        value=1_200.0,
        source="VERIFIED",
        confidence=0.95,
        provider="stripe",
        rationale="Stripe dashboard, trailing 30 days.",
    )
    asset = register_asset(
        conn,
        niche_slug="pet-friendly-travel",
        display_name="PetTripFinder",
        primary_category="pet",
        revenue=rev,
        initial_status="owned",
    )
    assert asset.revenue.source == "VERIFIED"
    assert asset.revenue.value == 1_200.0
    print("  ✓ register_asset: VERIFIED revenue persists correctly")


def test_valid_status_transitions():
    conn = _make_conn()
    asset = register_asset(
        conn,
        niche_slug="skilled-trade-pathway",
        display_name="SkilledTradePathway",
        primary_category="trades",
    )
    assert asset.status == "candidate"

    asset = transition_status(conn, asset.asset_id, "building", changed_by="test")
    assert asset.status == "building"

    asset = transition_status(conn, asset.asset_id, "owned", changed_by="test")
    assert asset.status == "owned"

    asset = transition_status(conn, asset.asset_id, "exited", changed_by="test")
    assert asset.status == "exited"
    assert asset.exited_at is not None
    print("  ✓ transition_status: candidate→building→owned→exited")


def test_invalid_transition_raises():
    conn = _make_conn()
    asset = register_asset(
        conn,
        niche_slug="direct-beef",
        display_name="DirectBeef",
        primary_category="food",
    )
    try:
        transition_status(conn, asset.asset_id, "owned")   # candidate → owned: invalid
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid transition" in str(e)
    print("  ✓ transition_status: invalid transitions raise ValueError")


def test_terminal_status_cannot_transition():
    conn = _make_conn()
    asset = register_asset(
        conn,
        niche_slug="dead-niche",
        display_name="DeadNiche",
        primary_category="food",
    )
    asset = transition_status(conn, asset.asset_id, "dead")
    try:
        transition_status(conn, asset.asset_id, "candidate")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  ✓ transition_status: terminal states (dead) cannot transition")


def test_revenue_update_honesty():
    conn = _make_conn()
    asset = register_asset(
        conn,
        niche_slug="pet-friendly-travel",
        display_name="PetTripFinder",
        primary_category="pet",
        initial_status="owned",
    )
    assert asset.revenue.source == "UNKNOWN"

    rev = RevenueTaggedValue(
        value=850.0, source="ESTIMATED", confidence=0.60,
        rationale="Projected from comparable site analysis.",
    )
    updated = update_revenue(conn, asset.asset_id, rev)
    assert updated.revenue.value == 850.0
    assert updated.revenue.source == "ESTIMATED"
    print("  ✓ update_revenue: ESTIMATED revenue correctly stored")


def test_snapshot_creation_and_reload():
    conn = _make_conn()

    # Register a mixed portfolio
    pet = register_asset(conn, niche_slug="pet-friendly-travel",
                         display_name="PetTripFinder", primary_category="pet",
                         initial_status="owned")
    trades = register_asset(conn, niche_slug="skilled-trade-pathway",
                            display_name="SkilledTradePathway", primary_category="trades",
                            initial_status="building")
    beef = register_asset(conn, niche_slug="direct-beef",
                          display_name="DirectBeef", primary_category="food",
                          initial_status="candidate")

    snap = create_snapshot(conn)

    assert snap.snapshot_id is not None
    assert len(snap.assets) == 3
    assert len(snap.owned) == 1
    assert len(snap.building) == 1
    assert len(snap.candidates) == 1
    assert snap.owned[0].niche_slug == "pet-friendly-travel"

    # Reload from DB — must be identical
    reloaded = load_snapshot(conn, snap.snapshot_id)
    assert reloaded.snapshot_id == snap.snapshot_id
    assert len(reloaded.assets) == len(snap.assets)
    assert {a.asset_id for a in reloaded.assets} == {a.asset_id for a in snap.assets}

    print("  ✓ create_snapshot + load_snapshot: snapshot round-trips correctly")


def test_snapshot_immutability():
    """Mutating a live asset after snapshot creation does not affect the stored snapshot."""
    conn = _make_conn()
    asset = register_asset(conn, niche_slug="pet-friendly-travel",
                           display_name="PetTripFinder", primary_category="pet",
                           initial_status="owned")

    snap = create_snapshot(conn)
    assert snap.owned[0].revenue.value == 0.0

    # Mutate revenue AFTER snapshot
    update_revenue(conn, asset.asset_id, RevenueTaggedValue(
        value=5_000.0, source="VERIFIED", confidence=0.95
    ))

    # Reload snapshot — should still see original revenue
    reloaded = load_snapshot(conn, snap.snapshot_id)
    assert reloaded.owned[0].revenue.value == 0.0, \
        "Snapshot should capture state at creation time, not current state"

    print("  ✓ snapshot immutability: post-snapshot mutations don't corrupt stored snapshot")


def test_supersede_previous_snapshots():
    conn = _make_conn()
    register_asset(conn, niche_slug="pet-friendly-travel",
                   display_name="PetTripFinder", primary_category="pet",
                   initial_status="owned")

    snap1 = create_snapshot(conn)
    snap2 = create_snapshot(conn)

    # snap1 should be superseded; snap2 should be active
    latest = get_latest_snapshot(conn)
    assert latest.snapshot_id == snap2.snapshot_id
    print("  ✓ create_snapshot: previous snapshots are marked superseded")


# ---------------------------------------------------------------------------
# Expansion Classifier Tests
# ---------------------------------------------------------------------------

def _make_empty_snapshot() -> object:
    """Minimal snapshot stub for classifier tests with no owned assets."""
    @dataclass
    class _S:
        owned: tuple = ()
        building: tuple = ()
        candidates: tuple = ()
        assets: tuple = ()
    return _S()


def _make_snapshot_with_owned(categories: list[str]) -> object:
    @dataclass
    class _Asset:
        primary_category: str
        status: str = "owned"
    @dataclass
    class _S:
        owned: tuple
        building: tuple = ()
        candidates: tuple = ()
        assets: tuple = ()
    owned = tuple(_Asset(c) for c in categories)
    return _S(owned=owned)


def test_classify_expansion():
    snap = _make_snapshot_with_owned(["pet"])
    synergy = _StubSynergyReport(total_score=0.75)
    result = classify(
        market_ceiling_monthly_usd=3_500.0,
        geographic_scope="national",
        conservative_monthly_revenue=400.0,
        synergy_report=synergy,
        portfolio_snapshot=snap,
    )
    assert result.label == "Expansion"
    assert result.synergy_driven is True
    print(f"  ✓ classify: Expansion label (synergy=0.75, owned=pet) → confidence={result.confidence:.3f}")


def test_classify_flagship():
    snap = _make_empty_snapshot()
    synergy = _StubSynergyReport(total_score=0.10)
    result = classify(
        market_ceiling_monthly_usd=15_000.0,
        geographic_scope="national",
        conservative_monthly_revenue=1_200.0,
        synergy_report=synergy,
        portfolio_snapshot=snap,
    )
    assert result.label == "Flagship"
    assert result.synergy_driven is False
    print(f"  ✓ classify: Flagship label (ceiling=$15k, no synergy) → confidence={result.confidence:.3f}")


def test_classify_local():
    snap = _make_empty_snapshot()
    synergy = _StubSynergyReport(total_score=0.20)
    result = classify(
        market_ceiling_monthly_usd=8_000.0,
        geographic_scope="local",
        conservative_monthly_revenue=500.0,
        synergy_report=synergy,
        portfolio_snapshot=snap,
    )
    assert result.label == "Local"
    print(f"  ✓ classify: Local label (scope=local, ceiling=$8k) → confidence={result.confidence:.3f}")


def test_classify_portfolio():
    snap = _make_snapshot_with_owned(["food"])
    synergy = _StubSynergyReport(total_score=0.35)
    result = classify(
        market_ceiling_monthly_usd=4_500.0,
        geographic_scope="national",
        conservative_monthly_revenue=300.0,
        synergy_report=synergy,
        portfolio_snapshot=snap,
    )
    assert result.label == "Portfolio"
    print(f"  ✓ classify: Portfolio label (ceiling=$4.5k, synergy=0.35) → confidence={result.confidence:.3f}")


def test_classify_micro():
    snap = _make_empty_snapshot()
    synergy = _StubSynergyReport(total_score=0.05)
    result = classify(
        market_ceiling_monthly_usd=800.0,
        geographic_scope="national",
        conservative_monthly_revenue=80.0,
        synergy_report=synergy,
        portfolio_snapshot=snap,
    )
    assert result.label == "Micro"
    print(f"  ✓ classify: Micro label (ceiling=$800, low synergy) → confidence={result.confidence:.3f}")


def test_classify_full_explainability():
    """Every classification must return named factors."""
    snap = _make_empty_snapshot()
    synergy = _StubSynergyReport(total_score=0.10)
    result = classify(
        market_ceiling_monthly_usd=12_000.0,
        geographic_scope="national",
        conservative_monthly_revenue=900.0,
        synergy_report=synergy,
        portfolio_snapshot=snap,
    )
    assert len(result.factors) > 0
    for factor in result.factors:
        assert factor.name
        assert factor.observed_value
        assert factor.rationale
    print(f"  ✓ classify: full explainability — {len(result.factors)} named factors returned")


# ---------------------------------------------------------------------------
# Market Liquidity Engine Tests
# ---------------------------------------------------------------------------

def test_liquidity_gather_pet():
    evidence = liquidity_engine.gather("pet", "national")
    assert evidence.category == "pet"
    assert evidence.revenue_multiple_range.source == DataSource.ESTIMATED
    assert evidence.revenue_multiple_range.lo > 0
    assert evidence.revenue_multiple_range.hi > evidence.revenue_multiple_range.lo
    assert evidence.buyer_demand_signal.value > 0
    assert isinstance(evidence.compression_risks.value, list)
    print(f"  ✓ liquidity.gather(pet, national): multiple={evidence.revenue_multiple_range.lo}–{evidence.revenue_multiple_range.hi}×, "
          f"demand={evidence.buyer_demand_signal.value:.2f}, "
          f"risks={len(evidence.compression_risks.value)}")


def test_liquidity_gather_fallback():
    """Unknown category should fall back to default heuristics."""
    evidence = liquidity_engine.gather("obscure-niche-xyz", "national")
    assert evidence.revenue_multiple_range.confidence == 0.30  # default confidence
    assert evidence.revenue_multiple_range.source == DataSource.ESTIMATED
    print(f"  ✓ liquidity.gather(unknown): fallback default heuristics applied, confidence=0.30")


def test_liquidity_all_unknown_source():
    """Source must never be VERIFIED — heuristic tables are ESTIMATED."""
    for category in ["pet", "trades", "food", "travel", "health"]:
        ev = liquidity_engine.gather(category, "national")
        assert ev.revenue_multiple_range.source == DataSource.ESTIMATED, \
            f"{category} returned non-ESTIMATED source"
    print("  ✓ liquidity: all heuristic outputs correctly tagged ESTIMATED")


def test_estimate_exit_value_verified_revenue():
    evidence = liquidity_engine.gather("travel", "national")
    exit_val = estimate_exit_value(evidence, monthly_revenue=2_000.0,
                                   revenue_source=DataSource.VERIFIED)
    # travel: typical=35, so typical exit ≈ $70k
    assert exit_val.value["typical"] == 2_000.0 * evidence.revenue_multiple_range.typical
    assert exit_val.source == DataSource.ESTIMATED   # weakest of VERIFIED + ESTIMATED
    print(f"  ✓ estimate_exit_value(travel, $2k/mo): "
          f"lo=${exit_val.value['lo']:,.0f}, "
          f"typical=${exit_val.value['typical']:,.0f}, "
          f"hi=${exit_val.value['hi']:,.0f}")


def test_estimate_exit_value_zero_revenue():
    evidence = liquidity_engine.gather("pet", "national")
    exit_val = estimate_exit_value(evidence, monthly_revenue=0.0,
                                   revenue_source=DataSource.UNKNOWN)
    assert exit_val.source == DataSource.UNKNOWN
    assert exit_val.value["typical"] == 0.0
    print("  ✓ estimate_exit_value(0 revenue): correctly returns UNKNOWN exit value")


# ---------------------------------------------------------------------------
# Integration: snapshot → classify → liquidity end-to-end
# ---------------------------------------------------------------------------

def test_integration_end_to_end():
    conn = _make_conn()

    # Build a portfolio that mirrors the Atlas real portfolio
    pet = register_asset(conn, niche_slug="pet-friendly-travel",
                         display_name="PetTripFinder", primary_category="pet",
                         domain="pettripfinder.com", initial_status="owned")
    update_revenue(conn, pet.asset_id, RevenueTaggedValue(
        value=0.0, source="ESTIMATED", confidence=0.30,
        rationale="Not yet monetised; estimated $0 pending listing launches."
    ))

    _ = register_asset(conn, niche_slug="skilled-trade-pathway",
                       display_name="SkilledTradePathway", primary_category="trades",
                       initial_status="candidate")
    _ = register_asset(conn, niche_slug="direct-beef",
                       display_name="DirectBeef", primary_category="food",
                       geographic_scope="regional", initial_status="candidate")

    snap = create_snapshot(conn)
    assert len(snap.owned) == 1
    assert len(snap.candidates) == 2

    # Evaluate a new pet-adjacent candidate using the snapshot
    synergy = _StubSynergyReport(
        total_score=0.70,   # strong synergy with PetTripFinder
        portfolio_snapshot_id=snap.snapshot_id
    )

    ec = classify(
        market_ceiling_monthly_usd=4_200.0,
        geographic_scope="national",
        conservative_monthly_revenue=350.0,
        synergy_report=synergy,
        portfolio_snapshot=snap,
    )
    assert ec.label == "Expansion"
    assert ec.synergy_driven is True

    # Gather liquidity evidence for the same candidate
    liq = liquidity_engine.gather("pet", "national")
    exit_val = estimate_exit_value(liq, monthly_revenue=350.0,
                                   revenue_source=DataSource.ESTIMATED)
    assert exit_val.source == DataSource.ESTIMATED

    print(
        f"\n  ✓ Integration E2E:\n"
        f"    Portfolio: {len(snap.owned)} owned, {len(snap.candidates)} candidates\n"
        f"    New candidate: {ec.label} (synergy={synergy.total_score:.2f})\n"
        f"    Exit range: ${exit_val.value['lo']:,.0f} – ${exit_val.value['hi']:,.0f}\n"
        f"    Time to exit: {liq.time_to_exit_months.value[0]}–{liq.time_to_exit_months.value[1]} months"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        # Portfolio Service
        ("Portfolio: register with UNKNOWN revenue default", test_register_asset_defaults),
        ("Portfolio: register with VERIFIED revenue",        test_register_asset_with_verified_revenue),
        ("Portfolio: valid transitions",                      test_valid_status_transitions),
        ("Portfolio: invalid transition raises",              test_invalid_transition_raises),
        ("Portfolio: terminal status locked",                 test_terminal_status_cannot_transition),
        ("Portfolio: revenue update honesty",                 test_revenue_update_honesty),
        ("Portfolio: snapshot creation and reload",           test_snapshot_creation_and_reload),
        ("Portfolio: snapshot immutability",                  test_snapshot_immutability),
        ("Portfolio: snapshot supersedes previous",           test_supersede_previous_snapshots),
        # Expansion Classifier
        ("Classifier: Expansion label",                       test_classify_expansion),
        ("Classifier: Flagship label",                        test_classify_flagship),
        ("Classifier: Local label",                           test_classify_local),
        ("Classifier: Portfolio label",                       test_classify_portfolio),
        ("Classifier: Micro label",                           test_classify_micro),
        ("Classifier: full explainability",                   test_classify_full_explainability),
        # Market Liquidity
        ("Liquidity: gather pet/national",                    test_liquidity_gather_pet),
        ("Liquidity: unknown category fallback",              test_liquidity_gather_fallback),
        ("Liquidity: all outputs ESTIMATED",                  test_liquidity_all_unknown_source),
        ("Liquidity: exit value (verified revenue)",          test_estimate_exit_value_verified_revenue),
        ("Liquidity: exit value (zero revenue)",              test_estimate_exit_value_zero_revenue),
        # Integration
        ("Integration: end-to-end snapshot→classify→liquidity", test_integration_end_to_end),
    ]

    passed = failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            import traceback; traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed:
        sys.exit(1)
