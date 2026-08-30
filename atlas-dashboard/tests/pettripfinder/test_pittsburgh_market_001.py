"""PTF-PITTSBURGH-MARKET-REVALIDATION-001 -- Pittsburgh factory gates.

Pinned to the measured first-pass universe from PTF-PITTSBURGH-MARKET-BUILD-001,
updated by PTF-PITTSBURGH-PASS1-DECISION-APPLICATION-001 (17 published, 2
VERIFIED_NO_PETS, the D003 Distrikt -> Joinery identity rename) and then
PTF-PITTSBURGH-PASS2-DECISION-APPLICATION-001 (9 more publications, 2 more
VERIFIED_NO_PETS, and two AWAITING_CENSUS_REVIEW workflow findings for
Courtyard Pittsburgh Shadyside and Shadyside Inn Suites -- findings, never
policy or closure decisions), then PTF-PITTSBURGH-PASS3-DECISION-APPLICATION-001A
(3 more publications and 2 more VERIFIED_NO_PETS), then
PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001 (8 more publications and 2
more VERIFIED_NO_PETS). The census policy_state column stays
legacy-frozen at POLICY_NOT_VERIFIED (the Cleveland precedent); the partition
and the policy/exclusion authorities are the publication truth.
"""

from __future__ import annotations

import json
from collections import Counter
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

#: The census size is read from the RELEASE CONTRACT, which is the artifact
#: that actually pins it (identity_census.expected_count). That is the
#: invariant worth testing -- "the census is exactly what this market's
#: contract binds it to" -- and it stays true across a legitimate promotion,
#: where a bare literal would only record that somebody edited two files.
#:
#: 96 through PTF-PITTSBURGH-HARDENED-SYNC-004, which refused to promote the
#: 115-row shadow recensus; 102 after PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005
#: added six identities that each carried a founder signature the sync could not
#: apply while the identity did not exist. ADD-ONLY: all 96 preserved.
def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _census_size():
    contract = _load(REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                     / ("%s.json" % MARKET))
    return contract["identity_census"]["expected_count"]


CENSUS_SIZE = _census_size()


def _expected():
    """The counts these gates protect, DERIVED from the primary authorities.

    Written this way deliberately (PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 14).
    These tests exist to prove that the partition, the founder review queue and
    the assembler all AGREE with the policy package and the exclusion registry
    -- not to remember a number. Restating a literal every time authority moves
    tests the transcription instead of the invariant, and a stale literal has
    to be edited by whoever changed the thing it was meant to police.

    So published comes from the policy package and the two closure counts from
    the exclusion REGISTRY (the no-pets authority, never a census annotation),
    and everything downstream is asserted against them.
    """
    package = _load(PACKAGE / ("hotel_policy_facts_%s.json" % MARKET))
    exclusions = _load(PACKAGE / "markets" / "authority" / MARKET
                       / "hotel_exclusions.json")["exclusions"]
    states = Counter(row["exclusion_state"] for row in exclusions)
    published = len(package["hotels"])
    no_pets = states["VERIFIED_NO_PETS"]
    out_of_category = states["OUT_OF_CURRENT_CATEGORY"]
    unresolved = CENSUS_SIZE - (published + no_pets + out_of_category)
    return {
        "census": CENSUS_SIZE,
        "published": published,
        "no_pets": no_pets,
        "out_of_category": out_of_category,
        "unresolved": unresolved,
        "queue": unresolved,
    }


EXPECTED = _expected()


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


def pass4_report_doc():
    return _load(PACKAGE / "markets" / "reports" / "pittsburgh_pass4_routing_recap_prep_001.json")


def pass4_capture_queue_doc():
    return _load(PACKAGE / "markets" / "reports" / "pittsburgh_pass4_claude_capture_queue.json")


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
        # The GLOBAL routing file is generated from the market shards, so the
        # two must agree exactly; a global that has drifted from its shard is
        # the failure this catches, not any particular route count.
        routing = _load(PACKAGE / "identity_routing.json")
        pittsburgh_routes = [r for r in routing.get("routes") or []
                            if r.get("market_id") == MARKET]
        shard = _load(PACKAGE / "markets" / "authority" / MARKET
                      / "identity_routing.json")
        assert len(pittsburgh_routes) == shard["count"] == len(shard["routes"])
        assert ({r["hotel_ref"]["identity_key"] for r in pittsburgh_routes}
                == {r["hotel_ref"]["identity_key"] for r in shard["routes"]})

        # A route is a standing instruction to GO AND FIND this property's
        # policy, so no route may survive beside an answer. Defect D2 of the
        # PTF-PITTSBURGH-HARDENED-SYNC-004 readiness audit was exactly this:
        # six identities held authority and kept their routes anyway. Asserting
        # the invariant rather than a count means the gate keeps working as the
        # market resolves, instead of needing a new literal each time.
        answered = {h["identity_key"] for h in
                    _load(PACKAGE / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
        answered |= {e["normalized_name"] for e in
                     _load(PACKAGE / "markets" / "authority" / MARKET
                           / "hotel_exclusions.json")["exclusions"]}
        assert not (answered & {r["hotel_ref"]["identity_key"]
                                for r in pittsburgh_routes})

        # Routing bindings are conservative endpoint recoveries, never policy
        # authority: they retain no page bytes and record no policy content.
        for route in pittsburgh_routes:
            assert route["binding_method"] == "BRAND_INDEX_BINDING"
            assert route["status"] == "ROUTING_CONFIRMED"


    def test_policy_authority_is_founder_bound_and_no_release_contract(self):
        from scripts.pettripfinder.policy_migration import (
            evidence_hash, record_hash)
        facts = _load(PACKAGE / "hotel_policy_facts_pittsburgh-pa.json")
        assert facts["market_id"] == MARKET
        assert len(facts["hotels"]) == EXPECTED["published"]
        keys = census.identity_keys(census_doc())
        for hotel in facts["hotels"]:
            assert hotel["identity_key"] in keys
            approval = hotel["approval"]
            assert approval["decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
            assert approval["operator"] == "jfields80"
            assert approval["record_hash"] == record_hash(hotel)
            assert approval["evidence_hash"] == evidence_hash(hotel["evidence"])
            for entry in hotel["evidence"]:
                assert entry["artifact_class"] == "PUBLICATION_GRADE_EVIDENCE"
                assert entry["artifact_sha256"].startswith("sha256:")
        # The release contract exists because the market now has verified
        # inventory (the registry invariant) -- and it grants NO deployment.
        assert MARKET in set(available_market_ids())
        from scripts.pettripfinder.release_contracts import (
            load_contract, verify_contract)
        contract = load_contract(MARKET)
        assert contract["deployment_authorization"]["grants_deployment"] is False
        assert verify_contract(MARKET) == []

    def test_verified_no_pets_lives_in_the_exclusion_registry(self):
        doc = _load(PACKAGE / "hotel_exclusions.json")
        rows = [e for e in doc["exclusions"] if e.get("market_id") == MARKET]
        no_pets = [e for e in rows
                   if e["exclusion_state"] == "VERIFIED_NO_PETS"]
        category = [e for e in rows
                    if e["exclusion_state"] == "OUT_OF_CURRENT_CATEGORY"]
        assert len(no_pets) == EXPECTED["no_pets"]
        assert len(category) == EXPECTED["out_of_category"]
        assert len(rows) == len(no_pets) + len(category)
        # The eight refusals committed before PTF-PITTSBURGH-HARDENED-SYNC-004
        # are asserted as a SUBSET, not as the whole set: this gate protects
        # against a refusal being silently EVICTED, which is the direction that
        # loses founder work. Growth is what an application order is for, and
        # the total is checked against derived authority above.
        assert {e["normalized_name"] for e in no_pets} >= {
            "cambria hotel pittsburgh downtown",
            "courtyard by marriott pittsburgh airport",
            "courtyard by marriott pittsburgh airport settlers ridge",
            "courtyard by marriott pittsburgh downtown",
            "doubletree by hilton pittsburgh airport",
            "fairfield inn and suites pittsburgh neville island",
            "springhill suites pittsburgh bakery square",
            "springhill suites pittsburgh north shore"}
        # No identity may be both published and refused.
        published_keys = {h["identity_key"] for h in
                          _load(PACKAGE / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
        assert not (published_keys & {e["normalized_name"] for e in rows})
        assert {e["normalized_name"] for e in category} == {
            "inn on negley", "choderwood", "the maverick by kasa"}
        for entry in rows:
            assert entry["evidence_quote"].strip()
            assert entry["source_hash"].startswith("sha256:")
            assert entry["reviewer_id"] == "jfields80"

    def test_joinery_rename_applied_and_published_with_fee_withheld(self):
        rows = {r["identity_key"]: r for r in census_doc()["hotels"]}
        assert "distrikt hotel pittsburgh" not in rows
        joinery = rows["joinery hotel pittsburgh"]
        assert joinery["former_name"] == "Distrikt Hotel Pittsburgh"
        assert joinery["address"] == "453 Boulevard of the Allies"
        assert joinery["phone"] == "412-339-1870"
        assert joinery["official_url"] == "https://www.joineryhotel.com"
        item = {i["identity_key"]: i for i in partition_doc()["items"]}[
            "joinery hotel pittsburgh"]
        assert item["final_state"] == "PUBLISHED_PET_FRIENDLY"
        assert item["resolved"] is True

    def test_pass2_census_review_findings_carry_no_policy_authority(self):
        # PGH-P2-D... census-review findings: workflow projections, never
        # policy or closure decisions. Neither identity may appear in the
        # published facts package or the exclusion registry.
        facts = _load(PACKAGE / "hotel_policy_facts_pittsburgh-pa.json")
        published_keys = {h["identity_key"] for h in facts["hotels"]}
        exclusions = _load(PACKAGE / "hotel_exclusions.json")
        excluded_norms = {e["normalized_name"] for e in exclusions["exclusions"]
                          if e.get("market_id") == MARKET}
        items = {i["identity_key"]: i for i in partition_doc()["items"]}
        for key in ("courtyard by marriott pittsburgh shadyside",
                    "shadyside inn suites"):
            assert key not in published_keys
            assert key not in excluded_norms
            assert items[key]["final_state"] == "AWAITING_CENSUS_REVIEW"
            assert items[key]["resolved"] is False

    def test_mansions_on_fifth_remains_unresolved_no_authority(self):
        # Founder: policy-silent first-party site, no founder decision.
        # Silence is never a refusal.
        key = "mansions on fifth"
        facts = _load(PACKAGE / "hotel_policy_facts_pittsburgh-pa.json")
        assert key not in {h["identity_key"] for h in facts["hotels"]}
        exclusions = _load(PACKAGE / "hotel_exclusions.json")
        assert key not in {e["normalized_name"] for e in exclusions["exclusions"]}
        item = {i["identity_key"]: i for i in partition_doc()["items"]}[key]
        assert item["final_state"] == "AWAITING_POLICY_OBSERVATION"
        assert item["resolved"] is False

    def test_market_isolation_from_ohio(self):
        configured = {m.market_id for m in load_markets()}
        assert MARKET in configured
        ohio = {"columbus-oh", "cleveland-akron-canton-oh", "dayton-oh", "cincinnati-oh"}
        pitt_keys = census.identity_keys(census_doc())
        for other in ohio:
            other_doc = PACKAGE / "identity_census" / ("%s.json" % other)
            if other_doc.is_file():
                assert pitt_keys.isdisjoint(census.identity_keys(_load(other_doc)))


class TestPass4RoutingAndRecapturePreparation:
    def test_authority_is_frozen_and_sunnyledge_is_not_policy_authority(self):
        report = pass4_report_doc()
        assert report["authority_freeze"] == {
            "published": 29, "verified_no_pets": 6, "out_of_category": 3}
        assert report["unresolved_before"] == 58
        assert report["sunnyledge_recapture"]["outcome"] == "SOURCE_AMBIGUOUS"
        assert report["sunnyledge_recapture"]["publication_grade"] is False
        assert report["sunnyledge_recapture"]["next_action"] == "RECAPTURE_REQUIRED"
        assert report["sunnyledge_recapture"]["artifact_sha256"].startswith("sha256:")

    def test_safe_capture_queue_remains_a_historical_capture_cohort(self):
        report = pass4_report_doc()
        queue = pass4_capture_queue_doc()
        queued = [item["identity_key"] for item in queue["items"]]
        assert queue["count"] == len(queued) == 12
        assert len(queued) == len(set(queued))
        assert "sunnyledge boutique hotel" not in queued
        assert set(report["routing_confirmed"]) <= set(queued)
        assert report["capture_readiness_counts"] == {
            "FRESH_SESSION_REQUIRED": 6,
            "SPECIAL_SURFACE_REQUIRED": 4,
            "ATTENDED_REQUIRED": 2,
        }


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

    def test_assembler_eligibility_is_honest_and_hidden(self):
        market = market_by_id(load_markets(), MARKET)
        row = market_eligibility(market)
        assert row["published_count"] == EXPECTED["published"]
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
