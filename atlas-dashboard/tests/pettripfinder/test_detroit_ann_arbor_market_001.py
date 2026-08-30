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
its own IHG property page. 168 identities remain unresolved. As of
PTF-DETROIT-ANN-ARBOR-ROUTING-EXPANSION-004's founder identity follow-up
(D001/D002), two more decisions landed: "Homewood Suites by Hilton Novi
Detroit" was retired as a confirmed duplicate of "Homewood Suites by
Hilton Novi" (identical hilton.com URL and address/phone, added under a
second name by a later pass), dropping the census from 183 to 182 and
raising the duplicate-ledger count to 1; "Best Western Greenfield Inn"'s
city was corrected Dearborn -> Allen Park (address/ZIP/phone/URL/corridor
all unchanged, via a one-hotel explicit corridor override -- Allen Park
is still not in any corridor's included_cities). 167 identities remain
unresolved.
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

# PTF-DETROIT-ANN-ARBOR-EVIDENCE-VOCABULARY-AND-PROMOTION-004. Founder decision
# B-003-1 registered the text_extract artifact kind, which unblocked the 28-row
# Pass 3 packet: 7 -> 17 published and 7 -> 25 verified-no-pets. Founder ruling
# DTW-ID-003-NOVI-11-MILE superseded the stale Courtyard Detroit Novi identity
# with its Sonesta Select successor at one address, so the census is 181 and the
# duplicate ledger carries a second entry. out_of_category went 1 -> 0: this
# market's one non-lodging identity claimed a TERMINAL category exit that the
# exclusion REGISTRY never carried -- it has no official_url and no artifact, so
# it cannot take an exclusion record at all -- and an unbacked terminal
# disposition was downgraded to AWAITING_CENSUS_REVIEW rather than invented or
# deleted. It is unresolved now, which is what it honestly is.
# PTF-DETROIT-ANN-ARBOR-FOUNDER-RULINGS-AND-SHADOW-PROMOTION-006 promoted the local-OSM shadow recensus after the founder settled the ten-municipality boundary packet (7 ADMIT, 1 ALIAS, 1 HELD, Plymouth Township ADMIT) and retired the Motel 6 identity at 3764 S State St as closed or converted.
# The boundary rulings admitted 8 municipalities and aliased one spelling, so
# candidates that had been held MARKET_MEMBERSHIP_UNRESOLVED became admissible;
# only Canton's 5 remain held, by founder judgement. The duplicate ledger gains
# no new `duplicate` row -- the Motel 6 retirement is a CLOSURE, recorded under
# `closed`, because the evidence shows that hotel is gone and NOT that it and
# the Residence Inn at the same address are one record.
# Updated by PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011, which
# applied the founder's approval of the Firecrawl 008/009/010 candidates:
# 16 more published and 35 more verified-no-pets, so 51 identities left the
# unresolved set. The census is unchanged -- nothing was discovered here, only
# decided. Two further candidates were withheld because the census carries no
# street address for them, and a hotel the market cannot place can neither
# render nor form an exclusion record.
# PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011 applied the founder's
# approval of the Firecrawl 008/009/010 candidates: +16 published and +35
# verified-no-pets, so 51 identities left the unresolved set. The census is
# unchanged -- nothing was discovered, only decided. Three further candidates
# were withheld: two the census cannot place (no street address) and one
# sharing an address with a second brand, pending a reviewed same-campus
# resolution.
# ... then PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019 applied
# the 58 clean Bright Data candidates acquired across orders 013-018: +49
# published and +9 verified-no-pets, then a founder ruling approved one more
# (TownePlace Dearborn) and HELD another (Embassy Suites Livonia Novi) for
# re-capture. The census is unchanged -- these rows were decided, not
# discovered.
EXPECTED = {
    "candidates": 152,
    "census": 247,
    "published": 112,
    "no_pets": 79,
    "out_of_category": 0,
    "unresolved": 56,
    "queue": 56,
    "boundary_excluded": 17,
    "duplicates": 2,
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
        # PTF-DETROIT-ANN-ARBOR-FOUNDER-RULINGS-AND-SHADOW-PROMOTION-006 retired ONE record: the founder
        # ruled the Motel 6 identity closed, and ROUTING_RETIRED is precisely a
        # route to an identity this market's census no longer contains. It is
        # kept rather than deleted, so how the URL was bound stays on file --
        # which is why the census-membership assertion below deliberately
        # exempts retired records instead of the record being removed.
        # PTF-DETROIT-ANN-ARBOR-FREE-CAPTURE-AND-ROUTING-026 gave this market
        # its first HELD record. Roberts Riverwalk's domain lapsed and now
        # redirects to an online-gambling site, and the record was still sitting
        # at ROUTING_CONFIRMED -- the only status a capture queue may act on, so
        # every cohort builder keying on it would send someone to open that
        # page. HELD is the right status and not RETIRED: the binding was
        # correct when it was made, its identity is still in the census, and
        # keeping the URL on file is how the hijack stays documented.
        for r in routes:
            assert r["market_id"] == MARKET
            assert r["status"] in (IR.ROUTING_CONFIRMED, IR.ROUTING_HELD,
                                   IR.ROUTING_RETIRED)
        assert sum(1 for r in routes if r["status"] == IR.ROUTING_RETIRED) == 1
        assert {r["hotel_ref"]["identity_key"] for r in routes
                if r["status"] == IR.ROUTING_HELD} == {"roberts riverwalk hotel"}
        keys = {r["identity_key"] for r in census_doc()["hotels"]}
        for r in routes:
            ref_key = r["hotel_ref"].get("identity_key")
            assert ref_key
            if r["status"] == IR.ROUTING_RETIRED:
                # A retired route is retired BECAUSE its identity left the
                # census. Requiring it to still be there would make the record
                # impossible to keep, and keeping it is the point.
                assert ref_key not in keys
                continue
            assert ref_key in keys
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
        # PTF-DETROIT-ANN-ARBOR-DISPLAY-INVENTORY-AND-RELEASE-CONTRACT-005
        # seeded this market's display inventory, which is what makes a release
        # contract both possible and required of it. It carries one now -- and
        # that contract grants NO deployment, which is the property worth
        # asserting here in place of its former absence.
        from scripts.pettripfinder.release_contracts import (
            available_market_ids, load_contract)
        assert MARKET in set(available_market_ids())
        contract = load_contract(MARKET)
        assert contract["deployment_authorization"]["grants_deployment"] is False
        assert contract["deployment_authorization"]["asserts_market_complete"] is False
        assert contract["market_visibility"]["launch_participation"] is False

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
