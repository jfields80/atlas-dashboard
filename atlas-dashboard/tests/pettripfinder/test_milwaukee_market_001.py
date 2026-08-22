"""PTF-MILWAUKEE-MARKET-FACTORY-001 -- Greater Milwaukee factory gates.

Pinned to the measured discovery universe: 216 candidates, 147 canonical
identities, 42 boundary exclusions, 13 confirmed duplicates, 7 category
exclusions, 5 ledger-only unresolved identities and 2 source listings already
carried by a held identity.

No policy authority exists for this market, so published=0 and
verified_no_pets=0 by construction and every one of the 147 identities carries
exactly one blocker. The routing shard is empty on purpose: §15 of the work
order admits a routing record only where the property-level route is
confidently bound, and a brand-index binding is not that.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.identity_key import (
    is_canonical_key,
    ptf_identity_key,
)
from scripts.pettripfinder.discovery.source_families import family_of
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "milwaukee-wi"

EXPECTED = {
    "candidates": 216,
    "census": 147,
    "published": 0,
    "no_pets": 0,
    "out_of_category": 0,
    "unresolved": 147,
    "queue": 147,
    "boundary_excluded": 42,
    "duplicates": 13,
    "category_excluded": 7,
    "identity_unresolved_ledger_only": 5,
    "already_accounted_for": 2,
    "corridors": 9,
}

#: What the market's authority holds at the end of the factory work order.
EXPECTED_AUTHORITY = {"routing": 0, "exclusions": 0, "seed": 0}


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def census_doc():
    return _load(PACKAGE / "identity_census" / ("%s.json" % MARKET))


def partition_doc():
    return _load(PACKAGE / "milwaukee_final_partition_001.json")


def ledger_doc():
    return _load(PACKAGE / "milwaukee_candidate_ledger_001.json")


def queue_doc():
    return _load(PACKAGE / "markets" / "reports" / ("%s_founder_review_queue.json" % MARKET))


def sources_doc():
    return _load(PACKAGE / "markets" / "reports" / ("%s_source_registry.json" % MARKET))


def routing_doc():
    return _load(PACKAGE / "markets" / "reports" / ("%s_routing_assessments.json" % MARKET))


def duplicate_ledger_doc():
    return _load(PACKAGE / "markets" / "reports" / ("%s_duplicate_ledger.json" % MARKET))


def completeness_doc():
    return _load(PACKAGE / "markets" / "reports" / ("%s_census_completeness.json" % MARKET))


def coverage_doc():
    return _load(PACKAGE / "markets" / "coverage" / ("%s.json" % MARKET))


class TestMarketConfig:
    def test_market_config_parses_under_the_current_contract(self):
        market = market_by_id(load_markets(), MARKET)
        assert market.market_id == MARKET
        assert market.market_slug == MARKET
        assert market.market_name == "Milwaukee, Wisconsin"
        assert market.primary_city == "Milwaukee"
        assert market.state_code == "WI"
        assert market.primary_state_code == "WI"
        assert list(market.states) == ["WI"]
        assert market.country_code == "US"
        assert market.route_mode == "market_prefixed"
        assert market.minimum_published_hotels == 5

    def test_the_market_is_registered_but_publishes_nothing(self):
        market = market_by_id(load_markets(), MARKET)
        assert market.show_in_navigation is False
        assert market.show_in_sitemap is False
        for corridor in market.corridors:
            assert corridor.show_in_navigation is False
            assert corridor.show_in_sitemap is False

    def test_corridor_count_and_ownership(self):
        market = market_by_id(load_markets(), MARKET)
        assert len(market.corridors) == EXPECTED["corridors"]
        for corridor in market.corridors:
            assert corridor.market_id == MARKET
            assert corridor.corridor_id.startswith("%s__" % MARKET)
            assert corridor.state_code == "WI"

    def test_the_boundary_decision_is_written_down(self):
        raw = _load(PACKAGE / "markets" / ("%s.json" % MARKET))
        note = raw["_boundary_note"]
        # A boundary is only reviewable if the excluded places are named.
        for excluded in ("Delafield", "Oconomowoc", "West Bend", "Grafton",
                         "Racine", "Kenosha", "Lake Geneva", "Kohler"):
            assert excluded in note, excluded
        for included in ("Germantown", "Mequon", "Brookfield", "Waukesha"):
            assert included in note, included


class TestCensus:
    def test_schema_count_and_ownership(self):
        doc = census_doc()
        assert doc["schema"] == enums.CENSUS_SCHEMA
        assert doc["market_id"] == MARKET
        assert doc["identity_key_contract"] == "ptf_identity_key/1.0"
        assert doc["count"] == len(doc["hotels"]) == EXPECTED["census"]
        for row in doc["hotels"]:
            assert row["market_id"] == MARKET
            assert row["state"] == "WI"
            assert is_canonical_key(row["identity_key"])
            assert row["identity_key"] == ptf_identity_key(row["canonical_name"])
            assert row["policy_state"] == enums.POLICY_NOT_VERIFIED

    def test_identities_are_unique(self):
        keys = [r["identity_key"] for r in census_doc()["hotels"]]
        assert len(keys) == len(set(keys))

    def test_validates_against_the_contract(self):
        assert census.validate(census_doc(), market_states=["WI"]) == ()

    def test_no_hotel_claims_a_policy_this_work_order_never_observed(self):
        for row in census_doc()["hotels"]:
            assert row["policy_state"] == enums.POLICY_NOT_VERIFIED, row["canonical_name"]

    def test_every_row_names_a_registered_source(self):
        registered = {s["source_id"] for s in sources_doc()["sources"]}
        for row in census_doc()["hotels"]:
            assert row["source"] in registered, row["canonical_name"]
            for extra in row["corroborating_sources"]:
                assert extra in registered, row["canonical_name"]

    def test_a_shared_address_is_declared_rather_than_implied(self):
        """Six identities sit on three shared sites. Each pair is a dual-brand
        or twin property carrying two distinct property codes on the brand's
        own index, so the shared address is a fact about the site and must be
        visible on the row -- not left implied by a note nobody reads."""
        doc = census_doc()
        by_site = {}
        for row in doc["hotels"]:
            if row["address"]:
                by_site.setdefault(row["street_identity"], []).append(row)
        shared = {k: v for k, v in by_site.items() if len(v) > 1}
        assert len(shared) == 3
        for group in shared.values():
            assert len(group) == 2
            for row in group:
                assert row["collision_state"] == enums.COLLISION_SHARED_ADDRESS
        assert doc["collision_audit"]["open_conflict_count"] == 0
        assert doc["collision_audit"]["duplicate_names_found"] == 0


class TestPartition:
    def test_set_reconciliation(self):
        rec = partition.reconcile(
            census.identity_keys(census_doc()), partition_doc(), market_id=MARKET)
        assert rec.agrees
        assert rec.published == EXPECTED["published"] == 0
        assert rec.verified_no_pets == EXPECTED["no_pets"] == 0
        assert rec.out_of_category == EXPECTED["out_of_category"]
        assert rec.unresolved == EXPECTED["unresolved"]
        assert (rec.published + rec.verified_no_pets + rec.out_of_category
                + rec.unresolved) == rec.census_count
        assert partition.reconciliation_issues(rec) == ()
        assert partition.validate(partition_doc()) == ()

    def test_every_row_carries_exactly_one_next_action(self):
        for item in partition_doc()["items"]:
            assert item["final_state"] not in enums.TERMINAL_STATES
            assert item["resolved"] is False
            assert item["next_action"].strip()
            assert item["next_action_source"].strip()
            # Two work orders have set states in this market: the factory that
            # built it, and the router integration that recovered sixteen
            # routes. A row must name whichever one actually decided it.
            assert item["determined_by"] in (
                "PTF-MILWAUKEE-MARKET-FACTORY-001",
                "PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001")

    def test_no_policy_terminal_state_was_fabricated(self):
        states = {i["final_state"] for i in partition_doc()["items"]}
        assert enums.PUBLISHED_PET_FRIENDLY not in states
        assert enums.VERIFIED_NO_PETS not in states

    def test_every_declared_state_has_a_written_meaning(self):
        doc = partition_doc()
        assert set(doc["final_state_counts"]) == set(doc["final_state_meanings"])
        for state, meaning in doc["final_state_meanings"].items():
            assert meaning == partition.STATE_MEANINGS[state]

    def test_a_row_without_an_official_url_says_so(self):
        by_key = {h["identity_key"]: h for h in census_doc()["hotels"]}
        for item in partition_doc()["items"]:
            row = by_key[item["identity_key"]]
            if item["final_state"] == enums.AWAITING_OFFICIAL_URL:
                assert not row["official_url"], row["canonical_name"]
            if item["final_state"] == enums.AWAITING_POLICY_OBSERVATION:
                assert row["official_url"], row["canonical_name"]


class TestCorridors:
    def test_every_row_has_one_reproducible_corridor(self):
        market = market_by_id(load_markets(), MARKET)
        hotels = census_doc()["hotels"]
        rows = [{"name": r["identity_key"], "city": r["city"],
                 "state": r["state"], "postal_code": r["postal_code"]}
                for r in hotels]
        assignment = assign_hotels(market, rows, fail_closed=True)
        assert assignment.unassigned == ()
        assert assignment.conflicts == ()
        for row in hotels:
            assert row["corridor"], row["canonical_name"]
            assert assignment.corridor_of[row["identity_key"]] == (row["corridor"],)
            basis, value = assignment.basis_of[row["identity_key"]]
            assert row["assignment_basis"] == basis, row["canonical_name"]
            assert row["assignment_value"] == value, row["canonical_name"]

    def test_every_corridor_is_populated(self):
        market = market_by_id(load_markets(), MARKET)
        counts = {}
        for row in census_doc()["hotels"]:
            counts[row["corridor"]] = counts.get(row["corridor"], 0) + 1
        assert set(counts) == {c.corridor_id for c in market.corridors}
        # A corridor exists because inventory clusters there, not because a
        # municipality exists: none may be empty.
        assert min(counts.values()) >= 1

    def test_the_one_explicit_assignment_is_the_documented_one(self):
        """Milwaukee-city rows are placed by ZIP because one city name spans
        four traveler areas. Exactly one identity overrides that, and it is the
        Glendale riverfront hotel whose mailing ZIP is a downtown one."""
        market = market_by_id(load_markets(), MARKET)
        explicit = {corridor.corridor_id: corridor.explicit_hotel_ids
                    for corridor in market.corridors if corridor.explicit_hotel_ids}
        assert explicit == {
            "%s__milwaukee-north-shore" % MARKET: ("holiday inn milwaukee riverfront",)}
        row = next(r for r in census_doc()["hotels"]
                   if r["identity_key"] == "holiday inn milwaukee riverfront")
        assert row["postal_code"] == "53212"
        assert row["assignment_basis"] == "explicit"

    def test_no_city_named_milwaukee_is_registered_to_a_corridor(self):
        """Every Milwaukee-city identity must resolve by ZIP. A bare city entry
        would silently swallow the airport, northwest and north-shore rows."""
        market = market_by_id(load_markets(), MARKET)
        for corridor in market.corridors:
            assert "Milwaukee" not in corridor.included_cities, corridor.corridor_id


class TestCandidateLedger:
    def test_every_candidate_has_exactly_one_disposition_and_a_reason(self):
        doc = ledger_doc()
        assert doc["count"] == len(doc["rows"]) == EXPECTED["candidates"]
        allowed = {"CANONICAL_CENSUS", "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
                   "CONFIRMED_DUPLICATE", "CATEGORY_EXCLUDED", "BOUNDARY_EXCLUDED",
                   "CLOSED_OR_CONVERTED", "IDENTITY_UNRESOLVED"}
        for row in doc["rows"]:
            assert row["disposition"] in allowed, row["candidate_name"]
            assert row["disposition_reason"].strip(), row["candidate_name"]
            assert row["sources"], row["candidate_name"]

    def test_disposition_counts_are_the_measured_universe(self):
        counts = ledger_doc()["disposition_counts"]
        assert counts["CANONICAL_CENSUS"] == EXPECTED["census"]
        assert counts["BOUNDARY_EXCLUDED"] == EXPECTED["boundary_excluded"]
        assert counts["CONFIRMED_DUPLICATE"] == EXPECTED["duplicates"]
        assert counts["CATEGORY_EXCLUDED"] == EXPECTED["category_excluded"]
        assert counts["IDENTITY_UNRESOLVED"] == EXPECTED["identity_unresolved_ledger_only"]
        assert counts["SOURCE_LISTING_ALREADY_ACCOUNTED_FOR"] == EXPECTED["already_accounted_for"]
        assert sum(counts.values()) == EXPECTED["candidates"]

    def test_no_closure_was_recorded_without_convergent_evidence(self):
        """A missing brand route is not closure evidence. Nine Wyndham slugs
        no longer resolve; two were matched to a live property at the same
        address and the rest are UNRESOLVED, never CLOSED_OR_CONVERTED."""
        assert ledger_doc()["disposition_counts"].get("CLOSED_OR_CONVERTED", 0) == 0

    def test_the_canonical_rows_are_exactly_the_census(self):
        canonical = {r["identity_key"] for r in ledger_doc()["rows"]
                     if r["disposition"] == "CANONICAL_CENSUS"}
        assert canonical == census.identity_keys(census_doc())

    def test_every_duplicate_names_the_identity_that_supersedes_it(self):
        keys = census.identity_keys(census_doc())
        for row in ledger_doc()["rows"]:
            if row["disposition"] in ("CONFIRMED_DUPLICATE",
                                      "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR"):
                assert row["duplicate_of"], row["candidate_name"]
                assert ptf_identity_key(row["duplicate_of"]) in keys, row["candidate_name"]

    def test_no_excluded_candidate_leaked_into_the_census(self):
        keys = census.identity_keys(census_doc())
        for row in ledger_doc()["rows"]:
            if row["disposition"] in ("BOUNDARY_EXCLUDED", "CATEGORY_EXCLUDED",
                                      "CONFIRMED_DUPLICATE"):
                assert row["identity_key"] not in keys, row["candidate_name"]

    def test_the_duplicate_ledger_agrees_with_the_candidate_ledger(self):
        counts = duplicate_ledger_doc()["counts"]
        assert counts["canonical"] == EXPECTED["census"]
        assert counts["duplicate"] == EXPECTED["duplicates"]
        assert counts["boundary_excluded"] == EXPECTED["boundary_excluded"]
        assert counts["category_excluded"] == EXPECTED["category_excluded"]
        assert counts["closed"] == 0


class TestSourcesAndCoverage:
    def test_source_registry_covers_every_family_the_census_uses(self):
        overrides = coverage_doc()["source_family_overrides"]
        for source in sources_doc()["sources"]:
            assert family_of(source["source_id"], overrides) == source["family"], \
                source["source_id"]

    def test_the_census_rests_on_more_than_one_source_family(self):
        overrides = coverage_doc()["source_family_overrides"]
        families = set()
        for row in census_doc()["hotels"]:
            for source in [row["source"]] + row["corroborating_sources"]:
                families.add(family_of(source, overrides))
        # CVB, REGISTRY, DIRECTORY and CHAIN all contribute identities: a
        # census built from one voice only ever confirms itself.
        assert {"CVB", "REGISTRY", "DIRECTORY", "CHAIN"} <= families

    def test_a_new_market_declares_its_sources_in_its_own_coverage_config(self):
        """Post-sharding registration pattern: the market's sources belong in
        its own coverage file, not appended to the shared family table."""
        from scripts.pettripfinder.discovery.source_families import CONCRETE_SOURCE_FAMILY
        for source in sources_doc()["sources"]:
            assert source["source_id"] not in CONCRETE_SOURCE_FAMILY or \
                source["source_id"] == "chain_locator", source["source_id"]
        overrides = coverage_doc()["source_family_overrides"]
        assert "visit_milwaukee" in overrides
        assert "travel_wisconsin" in overrides


class TestRoutingAndCaptureReadiness:
    def test_routing_assessments_are_not_routing_authority(self):
        for item in routing_doc()["items"]:
            assert item["assessment_status"] == "ASSESSMENT_ONLY"
            assert item["not_routing_authority"] is True
            assert item["routing_readiness"] in {
                "PROPERTY_LEVEL_ROUTE_CONFIRMED", "ROUTING_RECOVERY_NEEDED",
                "IDENTITY_REVIEW_NEEDED", "SPECIAL_ACCESS", "UNKNOWN"}
            assert item["capture_readiness"] in {
                "EVIDENCE_READY", "FRESH_SESSION_REQUIRED", "ATTENDED_REQUIRED",
                "SPECIAL_SURFACE_REQUIRED", "POLICY_SURFACE_UNKNOWN"}

    def test_assessments_cover_the_census_exactly(self):
        assessed = [i["identity_key"] for i in routing_doc()["items"]]
        assert len(assessed) == len(set(assessed)) == EXPECTED["census"]
        assert set(assessed) == census.identity_keys(census_doc())

    def test_no_route_was_written_to_any_routing_authority(self):
        assert MA.load_market_routes(MARKET) == []
        routes = _load(PACKAGE / "identity_routing.json")["routes"]
        assert [r for r in routes if r.get("market_id") == MARKET] == []

    def test_routing_is_a_subset_of_the_census(self):
        """The frozen invariant, evaluated even though the shard is empty --
        an empty set is a subset, and the gate must be the one that will run
        when it is not."""
        keys = census.identity_keys(census_doc())
        routes = MA.load_market_routes(MARKET)
        assert partition.routing_subset_violations(
            routes, keys, market_id=MARKET) == ()

    def test_no_url_points_at_an_ota_or_a_map_platform(self):
        # Matched on the HOST, not on a substring of the whole URL:
        # "wyndhamhotels.com" ends in "hotels.com" and is a brand site.
        banned = {"booking.com", "expedia.com", "hotels.com", "tripadvisor.com",
                  "maps.google.com", "google.com", "yelp.com", "trip.com",
                  "kayak.com", "agoda.com", "priceline.com"}
        for item in routing_doc()["items"]:
            url = (item["official_url"] or "").lower()
            if not url:
                continue
            host = url.split("//", 1)[-1].split("/", 1)[0]
            host = host[4:] if host.startswith("www.") else host
            assert host not in banned, (item["canonical_name"], host)

    def test_a_brand_index_binding_is_never_page_rendered(self):
        for item in routing_doc()["items"]:
            if item["official_url"]:
                assert item["binding_method"] == enums.BINDING_BRAND_INDEX
            else:
                assert item["binding_method"] == ""



def _assert_every_seed_row_traces_to_an_approved_record():
    """Seed inventory exists only where a founder approved the record.

    NARROWED by PTF-MILWAUKEE-PUBLICATION-037. The market factory left this
    shard empty and the tests above proved it; publication then DERIVED one row
    per founder-approved authority record. "Empty" is no longer the claim --
    "nothing here that a human did not approve" is, and it is the claim that
    protects a reader.
    """
    import json as _json
    rows = MA.load_market_seed_rows(MARKET)
    facts_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
    if not rows:
        return
    assert facts_path.is_file(), "seed inventory with no policy authority"
    doc = _json.loads(facts_path.read_text(encoding="utf-8"))
    approved = {record["name"] for record in doc["hotels"]}
    for row in rows:
        assert row["name"] in approved, row["name"]
        assert row["market_id"] == MARKET
    assert len(rows) == len(approved)

class TestPolicyAuthorityIsEmpty:
    def test_a_policy_fact_file_exists_only_by_founder_decision(self):
        """NARROWED by PTF-MILWAUKEE-FOUNDER-DECISION-036.

        The market factory left Milwaukee's policy authority empty and this
        proved it. The founder has since read the 036 review package and
        approved 96 records explicitly and in writing, so "empty" is no longer
        the claim -- what stays true is that the factory added nothing, that
        the shards are the only place a market writes, and that the generated
        globals are exactly what the shards produce.
        """
        facts = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
        if not facts.is_file():
            return                       # before 036 there was nothing to check
        import json
        doc = json.loads(facts.read_text(encoding="utf-8"))
        assert doc["published"] is False
        ledger = PACKAGE / "milwaukee_founder_decisions_036.json"
        assert ledger.is_file(), "authority exists with no decision ledger"
        approved = {row["identity_key"]
                    for row in json.loads(ledger.read_text(encoding="utf-8"))["decisions"]
                    if row["decision"] == "APPROVE"}
        for record in doc["hotels"]:
            assert record["identity_key"] in approved
            assert record["approval"]["operator"]

    def test_no_release_contract_exists_yet(self):
        from scripts.pettripfinder.release_contracts import available_market_ids
        assert MARKET not in set(available_market_ids())

    def test_the_authority_shards_carry_only_what_a_decision_put_there(self):
        """NARROWED by PTF-MILWAUKEE-FOUNDER-DECISION-036.

        The market factory left Milwaukee's policy authority empty and this
        proved it. The founder has since read the 036 review package and
        approved 96 records explicitly and in writing, so "empty" is no longer
        the claim -- what stays true is that the factory added nothing, that
        the shards are the only place a market writes, and that the generated
        globals are exactly what the shards produce.
        """
        assert MARKET in MA.sharded_market_ids()
        assert len(MA.load_market_routes(MARKET)) == EXPECTED_AUTHORITY["routing"]
        for row in MA.load_market_exclusions(MARKET):
            assert row["exclusion_state"] == "VERIFIED_NO_PETS"
            assert row["reviewer_id"], row["exclusion_id"]
            assert row["evidence_quote"].strip(), row["exclusion_id"]
        _assert_every_seed_row_traces_to_an_approved_record()

    def test_the_market_owns_all_three_shard_files(self):
        for path in (MA.routing_shard_path(MARKET), MA.exclusions_shard_path(MARKET),
                     MA.seed_shard_path(MARKET)):
            assert path.is_file(), path

    def test_no_seed_row_names_this_market_and_every_exclusion_is_signed(self):
        """NARROWED by PTF-MILWAUKEE-FOUNDER-DECISION-036.

        The market factory left Milwaukee's policy authority empty and this
        proved it. The founder has since read the 036 review package and
        approved 96 records explicitly and in writing, so "empty" is no longer
        the claim -- what stays true is that the factory added nothing, that
        the shards are the only place a market writes, and that the generated
        globals are exactly what the shards produce.
        """
        exclusions = _load(PACKAGE / "hotel_exclusions.json")["exclusions"]
        for row in [e for e in exclusions if e.get("market_id") == MARKET]:
            assert row["reviewer_id"], row["exclusion_id"]
            assert row["reviewed_at"], row["exclusion_id"]
        _assert_every_seed_row_traces_to_an_approved_record()

    def test_registering_milwaukee_changed_no_other_market_s_authority(self):
        """The generated globals are what the shards produce, and Milwaukee's
        shards are empty -- so the three compatibility artifacts must still
        carry exactly the record counts they carried before this market
        existed."""
        assert MA.check_generated_artifacts() == []
        assert len(MA.assemble_routing_document()["routes"]) == 277
        # Each global moves only by THIS market's own shard: the pre-Milwaukee
        # totals were 75 exclusions and 296 seed rows, and every row added
        # since belongs to this market.
        registry = MA.assemble_exclusions_document()["exclusions"]
        mine = [row for row in registry if row.get("market_id") == MARKET]
        assert len(registry) - len(mine) == 75
        seeds = MA.assemble_seed_rows()
        my_seeds = [row for row in seeds if row.get("market_id") == MARKET]
        assert len(seeds) - len(my_seeds) == 296


class TestCrossMarketIsolation:
    OTHERS = ("columbus-oh", "cleveland-akron-canton-oh", "dayton-oh",
              "cincinnati-oh", "pittsburgh-pa", "detroit-ann-arbor-mi",
              "indianapolis-in")

    def test_no_identity_key_collides_with_another_market(self):
        mine = census.identity_keys(census_doc())
        for other in self.OTHERS:
            path = PACKAGE / "identity_census" / ("%s.json" % other)
            if not path.is_file():
                continue
            theirs = census.identity_keys(_load(path))
            assert mine.isdisjoint(theirs), sorted(mine & theirs)[:5]

    def test_no_corridor_id_collides_with_another_market(self):
        seen = {}
        for market in load_markets():
            for corridor in market.corridors:
                assert corridor.corridor_id not in seen, corridor.corridor_id
                seen[corridor.corridor_id] = market.market_id

    def test_this_market_holds_no_other_market_s_rows(self):
        for row in census_doc()["hotels"]:
            assert row["market_id"] == MARKET
            assert row["corridor"].startswith("%s__" % MARKET)


class TestQueueAndCompleteness:
    def test_queue_is_exactly_the_unresolved_set(self):
        unresolved = {i["identity_key"] for i in partition_doc()["items"]
                      if not i["resolved"]}
        queued = [q["identity_key"] for q in queue_doc()["items"]]
        assert len(queued) == len(set(queued)) == EXPECTED["queue"]
        assert set(queued) == unresolved
        for item in queue_doc()["items"]:
            assert item["next_action"].strip()
            assert item["review_status"] == "NOT_STARTED"
            assert item["row_sha256"]

    def test_queue_rows_join_to_the_census_and_the_partition(self):
        census_by_key = {r["identity_key"]: r for r in census_doc()["hotels"]}
        partition_by_key = {i["identity_key"]: i for i in partition_doc()["items"]}
        for item in queue_doc()["items"]:
            key = item["identity_key"]
            assert item["hotel_id"] == key
            assert census_by_key[key]["canonical_name"] == item["canonical_name"]
            assert partition_by_key[key]["final_state"] == item["current_classification"]
            assert census_by_key[key]["corridor"] == item["corridor"]

    def test_the_completeness_report_answers_every_closure_question(self):
        doc = completeness_doc()
        assert doc["verdict"] == "CENSUS_COMPLETE"
        assert doc["canonical_census"] == EXPECTED["census"]
        assert len(doc["closure_questions"]) >= 8
        for entry in doc["closure_questions"]:
            assert entry["question"].strip()
            assert entry["answer"].strip()
        assert doc["remaining_blockers"], "a complete census still names its open work"

    def test_the_completeness_corridor_counts_are_the_census_counts(self):
        counts = {}
        for row in census_doc()["hotels"]:
            counts[row["corridor"]] = counts.get(row["corridor"], 0) + 1
        assert completeness_doc()["corridor_counts"] == counts


# --------------------------------------------------------------------------- #
# PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001
#
# The routing prerequisites the router pass depends on, and the freeze that
# pass runs under. Pinned to the measured state after sixteen routes were
# recovered: 133 routed, 8 still without a first-party URL, 6 held for
# identity or category review.
# --------------------------------------------------------------------------- #

ROUTER = {
    "recovered": 16,
    "routed": 133,
    "still_unrouted": 8,
    "identity_held": 6,
    "queue_total": 133,
    "routable": 127,
    "brand_excluded": 6,
}


def recovery_doc():
    return _load(PACKAGE / "markets" / "reports" / ("%s_routing_recovery_001.json" % MARKET))


def identity_review_doc():
    return _load(PACKAGE / "markets" / "reports" / ("%s_identity_review_001.json" % MARKET))


def acquisition_queue_doc():
    return _load(PACKAGE / "markets" / "reports"
                 / ("%s_policy_acquisition_queue_001.json" % MARKET))


class TestRoutingRecovery:
    def test_recovered_routes_are_applied_to_census_and_partition(self):
        doc = recovery_doc()
        assert doc["recovered_count"] == ROUTER["recovered"]
        census_by_key = {r["identity_key"]: r for r in census_doc()["hotels"]}
        partition_by_key = {i["identity_key"]: i for i in partition_doc()["items"]}
        for row in doc["recovered"]:
            key = row["identity_key"]
            assert census_by_key[key]["official_url"] == row["official_url"]
            assert census_by_key[key]["url_shape"] == "property"
            # A recovered route moves the row off "we do not know where its
            # page is" and onto "we have never read its policy" -- and onto
            # nothing else.
            assert partition_by_key[key]["final_state"] == enums.AWAITING_POLICY_OBSERVATION

    def test_every_unrouted_identity_says_why(self):
        """Fourteen identities still have no first-party URL, and the two
        reports have to account for all fourteen between them: eight failed
        routing recovery and are explained there, six are held for identity or
        category review and are explained in that report instead. A row that
        appeared in neither would be an unrouted hotel nobody had to justify."""
        doc = recovery_doc()
        assert doc["still_unrouted_count"] == ROUTER["still_unrouted"]
        explained_by_routing = {r["identity_key"] for r in doc["still_unrouted"]}
        explained_by_identity = {d["identity_key"] for d in identity_review_doc()["items"]}
        actual = {r["identity_key"] for r in census_doc()["hotels"]
                  if not r["official_url"]}
        assert explained_by_routing.isdisjoint(explained_by_identity)
        assert explained_by_routing | explained_by_identity == actual
        for row in doc["still_unrouted"]:
            assert row["reason"].strip()

    def test_no_recovered_route_points_at_an_intermediary(self):
        banned = {"booking.com", "expedia.com", "hotels.com", "tripadvisor.com",
                  "yelp.com", "trip.com", "kayak.com", "google.com",
                  "reservationdesk.com", "hotelplanner.com", "travelweekly.com"}
        for row in recovery_doc()["recovered"]:
            host = row["official_url"].split("//", 1)[-1].split("/", 1)[0]
            host = host[4:] if host.startswith("www.") else host
            assert host not in banned, row["identity_key"]

    def test_routed_and_unrouted_partition_the_census(self):
        rows = census_doc()["hotels"]
        routed = [r for r in rows if r["official_url"]]
        assert len(routed) == ROUTER["routed"]
        assert (len(rows) - len(routed)
                == ROUTER["still_unrouted"] + ROUTER["identity_held"])


class TestIdentityReview:
    def test_every_held_identity_has_a_determination_with_evidence(self):
        doc = identity_review_doc()
        assert doc["count"] == ROUTER["identity_held"]
        held = {i["identity_key"] for i in partition_doc()["items"]
                if i["final_state"] in (enums.AWAITING_CENSUS_REVIEW,
                                        enums.AWAITING_IDENTITY_RESOLUTION)}
        assert {d["identity_key"] for d in doc["items"]} == held
        for d in doc["items"]:
            assert d["determination"].strip()
            assert d["evidence"].strip()
            assert d["source"].strip()
            assert d["recommended_change"].strip()

    def test_the_determinations_are_recorded_and_not_applied(self):
        """SS18 freezes the partition. A determination that would change an
        identity, a name or a count is a decision packet, not a mutation --
        and the artifact has to say so rather than leaving a reader to infer
        it from the absence of a change."""
        doc = identity_review_doc()
        assert doc["applied"] is False
        partition_by_key = {i["identity_key"]: i for i in partition_doc()["items"]}
        for d in doc["items"]:
            assert partition_by_key[d["identity_key"]]["final_state"] == d["held_as"]

    def test_no_held_identity_reached_the_acquisition_queue(self):
        held = {d["identity_key"] for d in identity_review_doc()["items"]}
        queued = {r["identity_key"] for r in acquisition_queue_doc()["items"]}
        assert held.isdisjoint(queued)


class TestAcquisitionQueue:
    def test_queue_is_derived_from_the_partition_not_curated(self):
        doc = acquisition_queue_doc()
        assert doc["queue_total"] == len(doc["items"]) == ROUTER["queue_total"]
        partition_by_key = {i["identity_key"]: i for i in partition_doc()["items"]}
        census_by_key = {r["identity_key"]: r for r in census_doc()["hotels"]}
        for row in doc["items"]:
            key = row["identity_key"]
            assert partition_by_key[key]["final_state"] == enums.AWAITING_POLICY_OBSERVATION
            assert census_by_key[key]["official_url"] == row["official_url"]
            assert row["market_id"] == MARKET

    def test_no_row_is_lost_between_the_census_and_the_queue(self):
        doc = acquisition_queue_doc()
        queued = {r["identity_key"] for r in doc["items"]}
        excluded = set()
        for keys in doc["excluded_identity_keys"].values():
            excluded.update(keys)
        assert queued.isdisjoint(excluded)
        assert queued | excluded == census.identity_keys(census_doc())

    def test_exclusions_are_counted_and_named(self):
        doc = acquisition_queue_doc()
        assert doc["excluded_counts"]["identity_hold"] == ROUTER["identity_held"]
        assert doc["excluded_counts"]["no_route"] == ROUTER["still_unrouted"]
        assert doc["excluded_counts"]["already_resolved"] == 0
        for name, keys in doc["excluded_identity_keys"].items():
            assert len(keys) == doc["excluded_counts"][name]

    def test_every_row_carries_a_resolved_router_lane(self):
        from scripts.pettripfinder.acquisition import providers as PROVIDERS
        from scripts.pettripfinder.acquisition import readers as READERS
        known_providers = set(PROVIDERS.all_ids())
        known_readers = set(READERS.all_ids()) if hasattr(READERS, "all_ids") else None
        for row in acquisition_queue_doc()["items"]:
            assert row["route_provider"] in known_providers, row["identity_key"]
            if known_readers is not None:
                assert row["route_reader"] in known_readers, row["identity_key"]
            assert row["route_resolved_by"].strip()
            assert row["max_attempts_per_provider"] >= 1

    def test_choice_never_routes_to_the_browser_api(self):
        """The measured fact the route table exists to encode: the Browser API
        was refused fourteen times in fifteen on Choice. Fifteen Milwaukee
        properties are Choice, and none of them may be planned onto that lane."""
        rows = [r for r in acquisition_queue_doc()["items"] if r["brand"] == "CHOICE"]
        assert len(rows) == 15
        for row in rows:
            assert row["route_provider"] == "brightdata_web_unlocker"
            assert row["route_reader"] == "choice_static"
            assert "brightdata_browser" not in row["route_fallbacks"]

    def test_excluded_brands_are_flagged_with_their_reason(self):
        doc = acquisition_queue_doc()
        flagged = [r for r in doc["items"] if r["brand_excluded"]]
        assert len(flagged) == ROUTER["brand_excluded"]
        assert {r["brand"] for r in flagged} == {"HYATT", "BEST_WESTERN"}
        for row in flagged:
            assert row["brand_exclusion_reason"].strip()
        assert doc["routable_total"] == ROUTER["routable"]

    def test_the_queue_carries_no_policy_fact_of_any_kind(self):
        """This queue is built before acquisition and must not contain a
        policy fact, a quote or a verdict -- nothing here has read a page."""
        banned = ("pet_", "fee", "policy_text", "quote", "weight", "deposit",
                  "species", "verdict")
        for row in acquisition_queue_doc()["items"]:
            for field in row:
                assert not any(b in field.lower() for b in banned), (
                    field, row["identity_key"])


class TestAuthorityFreeze:
    def test_policy_authority_exists_only_where_a_human_approved_it(self):
        """NARROWED by PTF-MILWAUKEE-FOUNDER-DECISION-036.

        The market factory left Milwaukee's policy authority empty and this
        proved it. The founder has since read the 036 review package and
        approved 96 records explicitly and in writing, so "empty" is no longer
        the claim -- what stays true is that the factory added nothing, that
        the shards are the only place a market writes, and that the generated
        globals are exactly what the shards produce.
        """
        import json
        facts = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
        if facts.is_file():
            assert json.loads(facts.read_text(encoding="utf-8"))["published"] is False
        assert MA.check_generated_artifacts() == []

    def test_no_partition_row_became_terminal(self):
        for item in partition_doc()["items"]:
            assert item["final_state"] not in enums.TERMINAL_STATES
            assert item["resolved"] is False

    def test_the_market_authority_shards_hold_only_signed_rows(self):
        """NARROWED by PTF-MILWAUKEE-FOUNDER-DECISION-036.

        The market factory left Milwaukee's policy authority empty and this
        proved it. The founder has since read the 036 review package and
        approved 96 records explicitly and in writing, so "empty" is no longer
        the claim -- what stays true is that the factory added nothing, that
        the shards are the only place a market writes, and that the generated
        globals are exactly what the shards produce.
        """
        assert len(MA.load_market_routes(MARKET)) == EXPECTED_AUTHORITY["routing"]
        for row in MA.load_market_exclusions(MARKET):
            assert row["reviewer_id"], row["exclusion_id"]
        _assert_every_seed_row_traces_to_an_approved_record()

    def test_the_generated_globals_still_match_the_shards(self):
        assert MA.check_generated_artifacts() == []
