"""PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001 -- Phase 1 factory gates.

Pinned to the measured independent-discovery universe: 152 candidates, 9
boundary exclusions, 0 duplicates. As of
PTF-DETROIT-ANN-ARBOR-PASS1-DECISION-APPLICATION-001, the DTW/Romulus pilot
capture pass recorded real founder decisions: 6 PUBLISHED_PET_FRIENDLY, 5
VERIFIED_NO_PETS, 1 OUT_OF_CURRENT_CATEGORY. As of
PTF-DETROIT-ANN-ARBOR-IDENTITY-REPAIR-PASS2-001, two more founder identity/
census decisions landed: Delta Hotels by Marriott Detroit Metro Airport was
renamed in place to Skyline Hotel Detroit Airport, SureStay Collection by BW
(same address+phone, new brand flag) and moved to
AWAITING_POLICY_OBSERVATION; Hawthorn Suites by Wyndham Southfield Detroit
was retired from the active census via the 'closed' disposition (never a
VERIFIED_NO_PETS exclusion), dropping the canonical census from 143 to 142.
As of PTF-DETROIT-ANN-ARBOR-PASS2-DECISION-APPLICATION-001, the 3
routing-repaired DTW-area properties captured in Pass 2 were founder-decided:
Hotel Indigo Detroit Downtown published (pet_fee and weight_limit withheld),
Courtyard Detroit Pontiac Bloomfield and DoubleTree by Hilton Detroit Novi
both VERIFIED_NO_PETS. As of
PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-002, an additive completeness
audit found 19 real, distinct hotels materially missing from the census
(Dearborn +6, Livonia +4, Ann Arbor +3, Royal Oak +2, Southfield +2,
DTW/Romulus +1, Troy +1), raising the census from 142 to 161; 2 more
(Commerce Township, Ferndale) are flagged boundary-review rather than
silently added (their cities aren't in any corridor's included_cities);
1 more (Hawthorn Suites by Wyndham Troy) was found already closed and
retired straight to the ledger. As of
PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-003, a brand-by-brand sweep
(Hilton/IHG/Choice/Wyndham own location pages, WebSearch exhausted) closed
all 5 remaining blockers: 22 more real hotels added (161 -> 183), 6 more
boundary-review flags (Commerce Township, Clawson, Canton, Madison
Heights, Allen Park, Rochester Hills), and 2 existing rows corrected on
convergent first-party re-verification -- "Best Western Premier Detroit
Southfield Hotel" renamed in place to "Radisson Hotel Southfield-Detroit"
(same address/phone, converted brand, former_name preserved) and
"Staybridge Suites Detroit North - Royal Oak"'s address fixed to match
its own IHG property page. 168 identities remain unresolved.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.identity_key import (
    is_canonical_key,
    ptf_identity_key,
)
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.source_families import family_of
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "detroit-ann-arbor-mi"

EXPECTED = {
    "candidates": 152,
    "census": 183,
    "published": 7,
    "no_pets": 7,
    "out_of_category": 1,
    "unresolved": 168,
    "queue": 168,
    "boundary_excluded": 17,
    "duplicates": 0,
}


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def census_doc():
    return _load(PACKAGE / "identity_census" / ("%s.json" % MARKET))


def partition_doc():
    return _load(PACKAGE / "detroit_ann_arbor_final_partition_001.json")


def queue_doc():
    return _load(PACKAGE / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json")


def sources_doc():
    return _load(PACKAGE / "markets" / "reports" / "detroit-ann-arbor-mi_source_registry.json")


def routing_doc():
    return _load(PACKAGE / "markets" / "reports" / "detroit-ann-arbor-mi_routing_assessments.json")


def duplicate_ledger_doc():
    return _load(PACKAGE / "markets" / "reports" / "detroit-ann-arbor-mi_duplicate_ledger.json")


class TestCensus:
    def test_schema_count_and_ownership(self):
        doc = census_doc()
        assert doc["schema"] == enums.CENSUS_SCHEMA
        assert doc["market_id"] == MARKET
        assert doc["count"] == len(doc["hotels"]) == EXPECTED["census"]
        for row in doc["hotels"]:
            assert row["market_id"] == MARKET
            assert row["state"] == "MI"
            assert is_canonical_key(row["identity_key"])
            assert row["identity_key"] == ptf_identity_key(row["canonical_name"])
            assert row["policy_state"] == enums.POLICY_NOT_VERIFIED

    def test_identities_are_unique(self):
        keys = [r["identity_key"] for r in census_doc()["hotels"]]
        assert len(keys) == len(set(keys))

    def test_validates_against_the_contract(self):
        assert census.validate(census_doc(), market_states=["MI"]) == ()

    def test_no_hotel_is_published_or_verified_no_pets_by_default(self):
        # This is a brand-new market with no committed policy authority:
        # nothing in the census may claim otherwise.
        for row in census_doc()["hotels"]:
            assert row["policy_state"] in (enums.POLICY_NOT_VERIFIED,)


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

    def test_ann_arbor_core_and_south_were_not_fabricated_apart(self):
        # The work order named "Ann Arbor core" and "Ann Arbor east/south" as
        # separate hypotheses. No source gave ZIP-level data precise enough
        # to split individual hotels between them, so they are honestly one
        # corridor rather than a fabricated split.
        market = market_by_id(load_markets(), MARKET)
        corridor_ids = {c.corridor_id for c in market.corridors}
        assert "detroit-ann-arbor-mi__ann-arbor" in corridor_ids
        assert not any("ann-arbor-south" in c or "ann-arbor-downtown" in c
                       for c in corridor_ids)


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


class TestRoutingAndDuplicateLedger:
    def test_routing_assessments_are_not_confirmed_authority(self):
        # The informal pre-routing assessments file stays an assessment, even
        # after PTF-DETROIT-ANN-ARBOR-ROUTING-EXPANSION-004 gave the market
        # its first real routing authority: the two are different files with
        # different jobs, and the assessment file must never claim to BE
        # confirmed authority just because real authority now also exists.
        for item in routing_doc()["items"]:
            assert item["assessment_status"] == "ASSESSMENT_ONLY"
            assert item["not_routing_authority"] is True

    def test_market_has_real_routing_authority_and_it_is_well_formed(self):
        # PTF-DETROIT-ANN-ARBOR-ROUTING-EXPANSION-004: the market's FIRST real
        # routing authority, written to its shard only. Every record must
        # validate under the shared contract and reference an identity this
        # market's own census actually contains.
        from scripts.pettripfinder import identity_routing as IR
        from scripts.pettripfinder import market_authority as MA
        routes = MA.load_market_routes(MARKET)
        assert routes
        for r in routes:
            assert r["market_id"] == MARKET
            assert r["status"] == IR.ROUTING_CONFIRMED
        keys = {r["identity_key"] for r in census_doc()["hotels"]}
        for r in routes:
            ref_key = r["hotel_ref"].get("identity_key")
            assert ref_key and ref_key in keys
        # The global assembled file carries the same records for this market.
        routing = _load(PACKAGE / "identity_routing.json")
        global_for_market = [r for r in routing.get("routes") or []
                             if r.get("market_id") == MARKET]
        assert len(global_for_market) == len(routes)

    def test_pass1_policy_authority_exists_and_no_release_contract_yet(self):
        # PASS1-DECISION-APPLICATION-001 created real Schema 1.2 authority
        # for the DTW/Romulus pilot (6 published + 5 excluded), but the
        # market has not been assembled/deployed, so no release contract
        # exists for it yet.
        facts_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
        assert facts_path.is_file()
        facts = _load(facts_path)
        assert len(facts["hotels"]) == EXPECTED["published"]
        for hotel in facts["hotels"]:
            assert hotel["market_id"] == MARKET
            assert hotel["approval"]["operator"] == "jfields80"
        exclusions = _load(PACKAGE / "hotel_exclusions.json")
        rows = [e for e in exclusions["exclusions"] if e.get("market_id") == MARKET]
        assert len(rows) == EXPECTED["no_pets"]
        for row in rows:
            assert row["reviewer_id"] == "jfields80"
        from scripts.pettripfinder.release_contracts import available_market_ids
        assert MARKET not in set(available_market_ids())

    def test_duplicate_ledger_matches_boundary_exclusion_count(self):
        doc = duplicate_ledger_doc()
        assert doc["counts"]["boundary_excluded"] == EXPECTED["boundary_excluded"]
        assert doc["counts"]["duplicate"] == EXPECTED["duplicates"]
        boundary_rows = [x for x in doc["items"] if x["disposition"] == "boundary_excluded"]
        assert len(boundary_rows) == EXPECTED["boundary_excluded"]

    def test_market_isolation_from_other_markets(self):
        configured = {m.market_id for m in load_markets()}
        assert MARKET in configured
        others = {"columbus-oh", "cleveland-akron-canton-oh", "dayton-oh",
                  "cincinnati-oh", "pittsburgh-pa"}
        det_keys = census.identity_keys(census_doc())
        for other in others:
            other_doc = PACKAGE / "identity_census" / ("%s.json" % other)
            if other_doc.is_file():
                assert det_keys.isdisjoint(census.identity_keys(_load(other_doc)))


class TestMarketRegistration:
    def test_discovery_cells_match_committed_corridors(self):
        market = market_by_id(load_markets(), MARKET)
        cells = {cell.cell_id for cell in load_market_config(MARKET).cells}
        corridors = {corridor.corridor_id for corridor in market.corridors}
        assert cells == corridors

    def test_market_identity_matches_current_contract(self):
        market = market_by_id(load_markets(), MARKET)
        assert market.market_id == MARKET
        assert market.market_slug == MARKET
        assert market.market_name == "Detroit–Ann Arbor, Michigan"
        assert market.primary_city == "Detroit"
        assert market.state_code == "MI"
        assert market.primary_state_code == "MI"
        assert list(market.states) == ["MI"]
        assert market.country_code == "US"
        assert market.route_mode == "market_prefixed"
        assert market.minimum_published_hotels == 5
        assert market.show_in_navigation is False
        assert market.show_in_sitemap is False
        for corridor in market.corridors:
            assert corridor.show_in_navigation is False
            assert corridor.show_in_sitemap is False
