"""PTF-PITTSBURGH-MARKET-REVALIDATION-001 -- Pittsburgh factory gates.

Pinned to the measured first-pass universe from PTF-PITTSBURGH-MARKET-BUILD-001.
policy_state is POLICY_NOT_VERIFIED on every row. No hotel-policy authority
is published.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.assemble_production_site import market_eligibility
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.identity_key import (
    is_canonical_key,
    ptf_identity_key,
)
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.source_families import family_of
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id
from scripts.pettripfinder.release_contracts import available_market_ids

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "pittsburgh-pa"

EXPECTED = {
    "census": 96,
    "published": 0,
    "no_pets": 0,
    "out_of_category": 3,
    "unresolved": 93,
    "queue": 93,
}


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def census_doc():
    return _load(PACKAGE / "identity_census" / ("%s.json" % MARKET))


def partition_doc():
    return _load(PACKAGE / "pittsburgh_final_partition_001.json")


def queue_doc():
    return _load(PACKAGE / "markets" / "reports" / "pittsburgh-pa_founder_review_queue.json")


def sources_doc():
    return _load(PACKAGE / "markets" / "reports" / "pittsburgh-pa_source_registry.json")


def utilities_doc():
    return _load(PACKAGE / "markets" / "reports" / "pittsburgh-pa_utility_inventory.json")


def routing_doc():
    return _load(PACKAGE / "markets" / "reports" / "pittsburgh-pa_routing_assessments.json")


class TestCensus:
    def test_schema_count_and_ownership(self):
        doc = census_doc()
        assert doc["schema"] == enums.CENSUS_SCHEMA
        assert doc["market_id"] == MARKET
        assert doc["count"] == len(doc["hotels"]) == EXPECTED["census"]
        for row in doc["hotels"]:
            assert row["market_id"] == MARKET
            assert row["state"] == "PA"
            assert is_canonical_key(row["identity_key"])
            assert row["identity_key"] == ptf_identity_key(row["canonical_name"])
            assert row["policy_state"] == enums.POLICY_NOT_VERIFIED

    def test_identities_are_unique(self):
        keys = [r["identity_key"] for r in census_doc()["hotels"]]
        assert len(keys) == len(set(keys))

    def test_validates_against_the_contract(self):
        assert census.validate(census_doc(), market_states=["PA"]) == ()


class TestPartition:
    def test_set_reconciliation(self):
        rec = partition.reconcile(
            census.identity_keys(census_doc()), partition_doc(), market_id=MARKET)
        assert rec.agrees
        assert rec.published == EXPECTED["published"]
        assert rec.verified_no_pets == EXPECTED["no_pets"]
        assert rec.out_of_category == EXPECTED["out_of_category"]
        assert rec.unresolved == EXPECTED["unresolved"]
        assert rec.published + rec.verified_no_pets + rec.out_of_category + rec.unresolved == rec.census_count
        assert partition.reconciliation_issues(rec) == ()
        assert partition.validate(partition_doc()) == ()

    def test_unresolved_rows_have_one_next_action(self):
        for item in partition_doc()["items"]:
            if item["final_state"] in enums.TERMINAL_STATES:
                assert item["resolved"] is True
                assert item["next_action"] == ""
            else:
                assert item["resolved"] is False
                assert item["next_action"].strip()


class TestCorridors:
    def test_every_canonical_row_has_one_reproducible_corridor(self):
        market = market_by_id(load_markets(), MARKET)
        hotels = census_doc()["hotels"]
        rows = [{"name": r["identity_key"], "city": r["city"],
                 "state": r["state"], "postal_code": r["postal_code"]}
                for r in hotels]
        assignment = assign_hotels(market, rows, fail_closed=True)
        for row in hotels:
            assert row["corridor"], row["canonical_name"]
            assigned = assignment.corridor_of[row["identity_key"]]
            assert assigned == (row["corridor"],)
            basis, value = assignment.basis_of[row["identity_key"]]
            assert row["assignment_basis"] == basis
            assert row["assignment_value"] == value


class TestQueueAndSources:
    def test_queue_is_the_unresolved_set(self):
        unresolved = {i["identity_key"] for i in partition_doc()["items"]
                      if not i["resolved"]}
        queued = [q["identity_key"] for q in queue_doc()["items"]]
        assert len(queued) == EXPECTED["queue"] == len(unresolved)
        assert set(queued) == unresolved
        assert len(queued) == len(set(queued))
        for item in queue_doc()["items"]:
            assert item["next_action"].strip()
            assert item["review_status"] == "NOT_STARTED"

    def test_queue_identity_keys_match_census_and_partition(self):
        census_by_key = {r["identity_key"]: r for r in census_doc()["hotels"]}
        partition_by_key = {i["identity_key"]: i for i in partition_doc()["items"]}
        unresolved = {key for key, item in partition_by_key.items()
                      if not item["resolved"]}
        queued = [q["identity_key"] for q in queue_doc()["items"]]
        assert len(queued) == EXPECTED["queue"]
        assert len(queued) == len(set(queued))
        assert set(queued) == unresolved
        assert len(unresolved - set(queued)) == 0
        assert len(set(queued) - unresolved) == 0
        for item in queue_doc()["items"]:
            key = item["identity_key"]
            assert key
            assert key == census_by_key[key]["identity_key"]
            assert key == partition_by_key[key]["identity_key"]
            if "hotel_id" in item:
                assert item["hotel_id"] == key
            assert item.get("row_sha256")

    def test_source_registry_covers_census_sources(self):
        registered = {s["source_id"] for s in sources_doc()["sources"]}
        used = {r["source"] for r in census_doc()["hotels"]}
        assert used <= registered
        for source in sources_doc()["sources"]:
            assert family_of(source["source_id"]) == source["family"]


class TestRoutingAndAuthorityIsolation:
    def test_routing_assessments_are_not_confirmed_authority(self):
        for item in routing_doc()["items"]:
            assert item["assessment_status"] == "ASSESSMENT_ONLY"
            assert item["not_routing_authority"] is True
        routing = _load(PACKAGE / "identity_routing.json")
        assert not any(r.get("market_id") == MARKET for r in routing.get("routes") or [])

    def test_no_pittsburgh_policy_authority_or_release_contract(self):
        assert not (PACKAGE / "hotel_policy_facts_pittsburgh-pa.json").exists()
        assert MARKET not in set(available_market_ids())
        configured = {m.market_id for m in load_markets()}
        assert MARKET in configured
        ohio = {"columbus-oh", "cleveland-akron-canton-oh", "dayton-oh", "cincinnati-oh"}
        pitt_keys = census.identity_keys(census_doc())
        for other in ohio:
            other_doc = PACKAGE / "identity_census" / ("%s.json" % other)
            if other_doc.is_file():
                assert pitt_keys.isdisjoint(census.identity_keys(_load(other_doc)))


class TestUtilities:
    def test_every_utility_has_provenance_and_24_7_is_quoted(self):
        doc = utilities_doc()
        assert doc["as_of"] == "2026-08-15"
        assert doc["count"] == len(doc["items"])
        confirmed_24_7 = 0
        for item in doc["items"]:
            assert item["evidence_url"]
            assert item["evidence_quote"]
            assert item.get("as_of") == doc["as_of"]
            assert item.get("needs_reverification") is False
            if item.get("is_24_7"):
                confirmed_24_7 += 1
                quote = item["evidence_quote"].lower()
                assert "24" in quote
                assert item["official_url"]
            assert item.get("revalidation_due") == "2027-02-11"
        assert confirmed_24_7 == 2


class TestRevalidation:
    def test_base_commit_is_canonical_fea73de(self):
        assert census_doc()["base_commit"] == (
            "fea73de1ec699289cf04b88fd7069cf23fa4d735")

    def test_assembler_eligibility_is_honest_zero(self):
        market = market_by_id(load_markets(), MARKET)
        row = market_eligibility(market)
        assert row["published_count"] == 0
        assert row["assemblable"] is False
        assert market.show_in_navigation is False
        assert market.show_in_sitemap is False
        for corridor in market.corridors:
            assert corridor.show_in_navigation is False
            assert corridor.show_in_sitemap is False

    def test_discovery_cells_match_committed_corridors(self):
        market = market_by_id(load_markets(), MARKET)
        cells = {cell.cell_id for cell in load_market_config(MARKET).cells}
        corridors = {corridor.corridor_id for corridor in market.corridors}
        assert cells == corridors

    def test_market_identity_matches_current_contract(self):
        market = market_by_id(load_markets(), MARKET)
        assert market.market_id == MARKET
        assert market.market_slug == MARKET
        assert market.market_name == "Pittsburgh, Pennsylvania"
        assert market.primary_city == "Pittsburgh"
        assert market.state_code == "PA"
        assert market.primary_state_code == "PA"
        assert list(market.states) == ["PA"]
        assert market.country_code == "US"
        assert market.route_mode == "market_prefixed"
        assert market.minimum_published_hotels == 5
