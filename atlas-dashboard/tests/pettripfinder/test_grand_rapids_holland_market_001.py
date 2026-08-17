"""PTF-GRAND-RAPIDS-HOLLAND-MARKET-FACTORY-001 Phase-1 gates."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts import census, partition
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.source_families import family_of
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
MARKET = "grand-rapids-holland-mi"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def census_doc():
    return _load(PACKAGE / "identity_census" / (MARKET + ".json"))


def partition_doc():
    return _load(PACKAGE / "grand_rapids_holland_final_partition_001.json")


def test_candidate_reconciliation_has_no_unexplained_disappearance():
    ledger = _load(PACKAGE / "grand_rapids_holland_candidate_ledger_001.json")
    counts = ledger["counts"]
    assert ledger["raw_listings"] == len(ledger["items"]) == 157
    assert counts == {
        "ADD_TO_CENSUS": 23,
        "BOUNDARY_EXCLUDED": 12,
        "CANONICAL_CENSUS": 96,
        "CATEGORY_EXCLUDED": 5,
        "CLOSED_OR_CONVERTED": 1,
        "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR": 19,
        "SOURCE_LISTING_NOT_LODGING": 1,
    }
    assert sum(counts.values()) == ledger["raw_listings"]
    assert all(item["disposition"] for item in ledger["items"])


def test_census_is_independent_and_contract_valid():
    doc = census_doc()
    assert doc["schema"] == "ptf-market-identity-census/1.1"
    assert doc["market_id"] == MARKET
    assert doc["count"] == len(doc["hotels"]) == 120
    assert census.validate(doc, market_states=["MI"]) == ()
    for row in doc["hotels"]:
        assert row["market_id"] == MARKET
        assert row["identity_key"] == ptf_identity_key(row["canonical_name"])
        assert row["policy_state"] == "POLICY_NOT_VERIFIED"


def test_partition_is_honest_zero_policy_authority():
    doc = partition_doc()
    reconciliation = partition.reconcile(census.identity_keys(census_doc()), doc, market_id=MARKET)
    assert reconciliation.agrees
    assert reconciliation.published == 0
    assert reconciliation.verified_no_pets == 0
    assert reconciliation.out_of_category == 1
    assert reconciliation.unresolved == 119
    assert partition.validate(doc) == ()


def test_corridors_classify_the_existing_census_not_the_reverse():
    market = market_by_id(load_markets(), MARKET)
    rows = [{"name": row["identity_key"], "city": row["city"],
             "state": row["state"], "postal_code": row["postal_code"]}
            for row in census_doc()["hotels"] if row["lodging_state"] == "LODGING_CONFIRMED"]
    assignment = assign_hotels(market, rows, fail_closed=True)
    assert len(assignment.corridor_of) == 119
    assert assignment.unassigned == ()
    assert set(assignment.published) == {
        MARKET + "__downtown-grand-rapids",
        MARKET + "__grr-airport-kentwood",
        MARKET + "__holland-zeeland",
        MARKET + "__walker-northwest-grand-rapids",
        MARKET + "__wyoming-grandville",
        MARKET + "__east-grand-rapids-ada",
    }
    assert assignment.suppressed == ()


def test_sources_and_discovery_cells_are_registered():
    registry = _load(PACKAGE / "markets" / "reports" / (MARKET + "_source_registry.json"))
    assert len(registry["sources"]) == 24
    assert all(source["completeness"] == "PARTIAL" for source in registry["sources"])
    assert all(family_of(source["source_id"]) == source["family"] for source in registry["sources"])
    market = market_by_id(load_markets(), MARKET)
    assert {cell.cell_id for cell in load_market_config(MARKET).cells} == {
        corridor.corridor_id for corridor in market.corridors
    }


def test_boundary_and_routing_reports_are_conservative():
    boundary = _load(PACKAGE / "grand_rapids_holland_boundary_review_001.json")
    assert len(boundary["items"]) == 12
    assert set(boundary["area_findings"]) == {"Grand Haven", "Muskegon", "Saugatuck / Douglas", "South Haven"}
    assert boundary["explicitly_excluded_areas"] == ["Lansing / East Lansing", "Traverse City / Northwest Michigan", "Kalamazoo / Battle Creek"]
    routing = _load(PACKAGE / "markets" / "reports" / (MARKET + "_routing_readiness.json"))
    assert routing["summary"] == {"property_level_urls": 39, "missing_urls": 80, "routing_ready": 39, "evidence_ready_estimate": 0, "manual_or_bot_wall": 0}
    assert all(item["assessment_status"] == "ASSESSMENT_ONLY" for item in routing["items"])
    capture = _load(PACKAGE / "grand_rapids_holland_capture_ready_queue_001.json")
    assert capture["count"] == 39
    assert all(item["routing_ready"] for item in capture["items"])


def test_completeness_pass_is_additive_and_retains_every_new_lead():
    ledger = _load(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_001.json")
    assert ledger["raw_listings"] == len(ledger["items"]) == 45
    assert ledger["counts"] == {
        "ADD_TO_CENSUS": 24,
        "BOUNDARY_EXCLUDED": 2,
        "IDENTITY_UNRESOLVED": 19,
    }
    assert sum(ledger["counts"].values()) == ledger["raw_listings"]


def test_additional_completeness_pass_is_additive_and_fail_closed():
    ledger = _load(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_002.json")
    assert ledger["raw_listings"] == len(ledger["items"]) == 45
    assert ledger["counts"] == {
        "BOUNDARY_EXCLUDED": 2,
        "CANONICAL_CENSUS": 40,
        "CATEGORY_EXCLUDED": 2,
        "SOURCE_LISTING_NOT_LODGING": 1,
    }
    report = _load(PACKAGE / "grand_rapids_holland_census_completeness_002.json")
    assert report["completeness_pass_reconciliation"] == {
        "census_before": 56,
        "new_discovery_candidates": 45,
        "new_valid_lodging_identities": 40,
        "proven_removals": 0,
        "final_census": 96,
        "identity_unresolved_before": 19,
        "identity_unresolved_after": 2,
    }
    assert report["verdict"] == "CENSUS_STILL_INCOMPLETE"
    assert report["policy_capture"] == "NOT_PERFORMED"


def test_final_closure_pass_is_exact_and_reconciles_the_last_leads():
    ledger = _load(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_003.json")
    assert ledger["raw_listings"] == len(ledger["items"]) == 31
    assert ledger["counts"] == {
        "BOUNDARY_EXCLUDED": 3,
        "CANONICAL_CENSUS": 25,
        "CATEGORY_EXCLUDED": 2,
        "CLOSED_OR_CONVERTED": 1,
    }
    assert sum(ledger["counts"].values()) == ledger["raw_listings"]
    report = _load(PACKAGE / "grand_rapids_holland_census_closure_003.json")
    assert report["reconciliation"] == {
        "census_before": 96,
        "new_discovery_candidates": 31,
        "new_valid_lodging_identities": 25,
        "proven_removals": 1,
        "final_census": 120,
        "identity_unresolved_before": 2,
        "identity_unresolved_after": 0,
        "duplicates": 0,
        "closed_or_converted": 1,
    }
    assert report["verdict"] == "CENSUS_COMPLETE"
    assert report["kent_county_reconciliation"]["complete_for_in_scope_lodging_reconciliation"]
    assert report["policy_capture"] == "NOT_PERFORMED"


def test_market_has_no_collision_or_policy_authority():
    ours = census.identity_keys(census_doc())
    for other in ("columbus-oh", "cleveland-akron-canton-oh", "dayton-oh", "cincinnati-oh", "pittsburgh-pa", "detroit-ann-arbor-mi"):
        other_doc = _load(PACKAGE / "identity_census" / (other + ".json"))
        assert ours.isdisjoint(census.identity_keys(other_doc)), other
    assert not (PACKAGE / ("hotel_policy_facts_" + MARKET + ".json")).exists()
    exclusions = _load(PACKAGE / "hotel_exclusions.json")
    assert not [x for x in exclusions["exclusions"] if x.get("market_id") == MARKET]
