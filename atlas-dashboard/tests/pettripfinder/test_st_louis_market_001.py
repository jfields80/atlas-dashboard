"""PTF-ST-LOUIS-MARKET-001 -- the fresh-market gates for St. Louis.

Pinned to the measured run: 565 discovery candidates, 357 census identities,
357 active-eligible, 138 attempted on the free lane, 19 acquired, 17
publication-grade, 17 founder-review candidates, 0 authority.

Everything a founder decision would produce is zero by construction. There is
no code path in this work order that writes an approval, and the tests below
assert that as a property of the artifacts rather than as an intention.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.contracts import census, closure as CL, enums, partition
from scripts.pettripfinder.contracts.identity_key import (
    is_canonical_key, ptf_identity_key,
)
from scripts.pettripfinder.discovery import census_projection as CP
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.markets.assignment import assign_hotels
from scripts.pettripfinder.markets.contract import parse_market

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "st-louis-mo"

EXPECTED = {
    "discovery_candidates": 565,
    "census": 357,
    "active_eligible": 357,
    "attempted": 138,
    "acquired": 19,
    "publication_grade": 17,
    "review_candidates": 17,
    "authority": 0,
    "corridors": 16,
    "postal_codes": 105,
}


def _load(name):
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def contract():
    return parse_market(_load("markets/pending/st-louis-mo.json"),
                        source="pending/st-louis-mo.json")


@pytest.fixture(scope="module")
def census_doc():
    return _load("identity_census/st-louis-mo.json")


@pytest.fixture(scope="module")
def ledger():
    return _load("st_louis_mo_candidate_ledger_001.json")


@pytest.fixture(scope="module")
def partition_doc():
    return _load("st_louis_mo_final_partition_001.json")


@pytest.fixture(scope="module")
def closure_doc():
    return _load("st_louis_mo_closure_ledger_001.json")


@pytest.fixture(scope="module")
def review():
    return _load("st_louis_mo_founder_review_packet_001.json")


@pytest.fixture(scope="module")
def store():
    return _load("st_louis_mo_observation_store_001.json")


@pytest.fixture(scope="module")
def pilot():
    return _load("st_louis_mo_direct_http_pilot_001.json")


class TestMarketConfig:
    def test_the_discovery_config_loads_by_convention(self):
        """No registry edit: the file's existence is its registration."""
        geo = load_market_config(MARKET)
        assert geo.market_id == MARKET
        assert len(geo.cells) == 18
        assert geo.bounds.contains(38.63, -90.19), "downtown St. Louis"
        assert not geo.bounds.contains(38.33, -90.15), "Waterloo IL is outside"

    def test_the_market_contract_is_valid_and_bi_state(self, contract):
        assert contract.states == ("MO", "IL")
        assert contract.primary_state_code == "MO"
        assert len(contract.corridors) == EXPECTED["corridors"]

    def test_every_postal_code_belongs_to_exactly_one_corridor(self, contract):
        codes = [c for corridor in contract.corridors
                 for c in corridor.included_postal_codes]
        assert len(codes) == EXPECTED["postal_codes"]
        assert len(set(codes)) == len(codes), "a ZIP in two corridors is ambiguous"

    def test_the_boundary_decisions_are_written_down(self, contract):
        document = _load("markets/pending/st-louis-mo.json")
        note = document["_boundary_note"]
        for excluded in ("Waterloo", "Pevely", "Festus", "Wright City",
                         "Ste. Genevieve"):
            assert excluded in note, excluded


class TestCensus:
    def test_the_census_is_the_measured_size(self, census_doc):
        assert census_doc["count"] == EXPECTED["census"]
        assert len(census_doc["hotels"]) == EXPECTED["census"]

    def test_no_duplicate_identity(self, census_doc):
        keys = [row["identity_key"] for row in census_doc["hotels"]]
        assert len(set(keys)) == len(keys)

    def test_every_key_is_canonical_and_derives_from_its_own_name(self, census_doc):
        for row in census_doc["hotels"]:
            assert is_canonical_key(row["identity_key"]), row["identity_key"]
            assert ptf_identity_key(row["canonical_name"]) == row["identity_key"]

    def test_every_row_validates_against_the_census_contract(self, census_doc):
        assert census.validate(census_doc) == ()

    def test_every_row_owns_this_market(self, census_doc):
        assert {row["market_id"] for row in census_doc["hotels"]} == {MARKET}

    def test_the_candidate_ledger_sums_to_the_discovered_universe(self, ledger,
                                                                  census_doc):
        assert ledger["count"] == EXPECTED["discovery_candidates"]
        counts = ledger["disposition_counts"]
        assert sum(counts.values()) == ledger["count"]
        assert counts[CP.ADMITTED] == census_doc["count"]

    def test_every_candidate_carries_exactly_one_known_disposition(self, ledger):
        seen = Counter(row["candidate_id"] for row in ledger["candidates"])
        assert max(seen.values()) == 1
        assert set(ledger["disposition_counts"]) <= set(CP.LEDGER_DISPOSITIONS)

    def test_an_identity_key_collision_is_held_with_its_address(self, census_doc):
        """Never collapsed. Bare brand names name several buildings."""
        collisions = census_doc["identity_key_collisions"]
        assert collisions
        for collision in collisions:
            for held in collision["held_for_review"]:
                assert held["address_line"] != collision["kept_address"]

    def test_the_census_is_deterministic(self, census_doc, contract):
        """Rebuild from the same inputs, get the same rows in the same order."""
        candidates = json.loads(
            (REPO_ROOT / "data" / "discovery" / "st_louis_market_001"
             / "candidates" / "st-louis-mo_candidates.json").read_text(encoding="utf-8")
        ) if (REPO_ROOT / "data" / "discovery" / "st_louis_market_001").is_dir() else None
        if candidates is None:
            pytest.skip("the gitignored discovery run is not in this checkout")
        admitted, _ledger = CP.project(candidates, contract,
                                       observed_at="2026-08-23", work_order="T")
        unique, _collisions = CP.resolve_identity_key_collisions(admitted)
        assert sorted(r["identity_key"] for r in unique) == sorted(
            row["identity_key"] for row in census_doc["hotels"])


class TestCorridorAssignment:
    def test_every_assignment_basis_is_provable_against_the_registry(
            self, census_doc, contract):
        """No human judgement may be labelled ``postal_code``: the ZIP that
        fired must actually be in that corridor's registry."""
        by_zip = {code: corridor.corridor_id
                  for corridor in contract.corridors
                  for code in corridor.included_postal_codes}
        for row in census_doc["hotels"]:
            corridor = row["corridor"]
            assert corridor, row["identity_key"]
            assert row["assignment_basis"] == "postal_code"
            assert by_zip[row["assignment_value"]] == corridor

    def test_a_state_the_provider_omitted_is_derived_from_the_registry(
            self, census_doc, contract):
        """A missing state is not a stateless property. Exactly one corridor
        claims a postal code and that corridor declares its own state."""
        corridor_state = {c.corridor_id: c.state_code for c in contract.corridors}
        derived = census_doc["states_derived_from_the_corridor_registry"]
        by_key = {r["identity_key"]: r for r in census_doc["hotels"]}
        for row in derived:
            census_row = by_key[row["identity_key"]]
            assert census_row["state"] == corridor_state[row["corridor"]]
            assert census_row["state_source"] == "corridor_registry"
        for census_row in census_doc["hotels"]:
            assert census_row["city"].strip(), census_row["identity_key"]
            assert census_row["state"].strip(), census_row["identity_key"]

    def test_assignment_is_unambiguous(self, census_doc, contract):
        rows = [{"name": r["canonical_name"], "city": r["city"],
                 "state": r["state"], "postal_code": r["postal_code"]}
                for r in census_doc["hotels"]]
        assignment = assign_hotels(contract, rows, fail_closed=False)
        assert assignment.conflicts == ()


class TestRouting:
    def test_routing_is_derived_from_the_census_and_reconciles(self, census_doc):
        entries, summary = MR.route_census(census_doc["hotels"])
        assert summary["count"] == EXPECTED["census"]
        assert sum(summary["routing_states"].values()) == EXPECTED["census"]
        assert sum(summary["url_shapes"].values()) == EXPECTED["census"]

    def test_no_brand_index_or_third_party_url_is_counted_as_routed(self, census_doc):
        entries, _summary = MR.route_census(census_doc["hotels"])
        for entry in entries:
            if entry["routing_state"] == MR.ROUTED:
                assert entry["url_shape"] in MR.ROUTABLE_SHAPES

    def test_no_new_source_family_was_opened(self, census_doc):
        """Every brand St. Louis exposes was already in the registry."""
        entries, _summary = MR.route_census(census_doc["hotels"])
        unknown = {e["brand"] for e in entries
                   if e["routing_state"] == MR.ROUTED
                   and not e["brand"].startswith("INDEP:")
                   and not e.get("measured_by")}
        assert unknown == set()


class TestAcquisition:
    def test_every_artifact_binds_to_this_market(self, pilot, store,
                                                 closure_doc, partition_doc,
                                                 review, census_doc):
        for document in (pilot, store, closure_doc, partition_doc, review,
                         census_doc):
            assert document["market_id"] == MARKET

    def test_the_pilot_attempted_only_routed_identities(self, pilot, census_doc):
        keys = {row["identity_key"] for row in census_doc["hotels"]}
        assert pilot["attempted"] == EXPECTED["attempted"]
        assert {r["identity_key"] for r in pilot["results"]} <= keys

    def test_zero_cost_recovery_ran_before_any_repeated_acquisition(self):
        """A POLICY_NOT_FOUND that nobody re-read is an assertion nobody can
        check. Every declined document was re-read offline, script bodies
        included, at zero cost."""
        recovery = _load("st_louis_mo_zero_cost_recovery_001.json")
        assert recovery["network_calls"] == 0
        assert recovery["usd_spent"] == 0.0
        assert recovery["examined"] > 0

    def test_the_free_lane_cost_nothing(self, pilot):
        assert pilot["usd_spent"] == 0.0

    def test_the_provider_cost_cap_was_honoured(self):
        benchmark = _load("st_louis_mo_benchmark_001.json")
        spend = benchmark["scorecard"]["provider_spend_usd"]["actual"]
        assert spend <= benchmark["cost"]["cap_usd"]
        assert benchmark["cost"]["provider_calls"]["firecrawl"] == 0
        assert benchmark["cost"]["provider_calls"]["brightdata_browser"] == 0

    def test_an_unrendered_template_is_never_reported_as_silence(self, pilot):
        """Wyndham serves 'Pet Policy {{pets}}'. Reading that as POLICY_NOT_FOUND
        would assert that twenty-six hotels state nothing about pets."""
        wyndham = pilot["outcomes_by_brand"].get("WYNDHAM", {})
        assert wyndham.get("POLICY_NOT_FOUND", 0) == 0
        assert wyndham.get("UNHYDRATED", 0) >= 20

    def test_declined_evidence_was_preserved(self, pilot):
        kept = [r for r in pilot["results"] if r["declined_dir"]]
        assert kept, "a decline that persists nothing is unfalsifiable"


class TestObservationStore:
    def test_the_store_holds_every_acquired_identity(self, store, pilot):
        acquired = [r for r in pilot["results"] if r["outcome"] == "VALID"]
        assert len(acquired) == EXPECTED["acquired"]
        assert store["count"] + len(store["refusals"]) == len(acquired)

    def test_the_store_cost_nothing_and_touched_no_network(self, store):
        assert store["network_calls"] == 0
        assert store["usd_spent"] == 0.0

    def test_every_row_carries_its_full_lineage(self, store):
        for record in store["records"]:
            provenance = record["reader_provenance"]
            assert provenance["module"]
            assert provenance["block_sha256"]
            assert provenance["document_sha256"]
            assert record["observation"]["source_url"]
            assert record["observation"]["snapshot_hash"]
            assert record["review_state"] == "AWAITING_FOUNDER_REVIEW"

    def test_no_reader_epoch_is_mixed(self, store):
        walks = {r["reader_provenance"]["locator_walk"] for r in store["records"]}
        assert len(walks) == 1, walks


class TestClosure:
    def test_the_ledger_sums_exactly_over_the_active_denominator(self, closure_doc):
        assert closure_doc["active_denominator"] == EXPECTED["active_eligible"]
        assert closure_doc["count"] == EXPECTED["active_eligible"]
        assert sum(closure_doc["disposition_counts"].values()) == closure_doc["count"]

    def test_membership_reconciles_by_set_not_by_count(self, closure_doc):
        problems = closure_doc["reconciliation"]
        assert problems["missing"] == []
        assert problems["foreign"] == []
        assert problems["duplicate"] == []

    def test_there_is_no_unnamed_remainder(self, closure_doc, census_doc):
        active = closure_doc["count"]
        not_active = len(closure_doc["not_active"])
        assert active + not_active == census_doc["count"]
        assert sum(closure_doc["eligibility_counts"].values()) == census_doc["count"]

    def test_every_disposition_is_in_the_contract_vocabulary(self, closure_doc):
        assert set(closure_doc["disposition_counts"]) <= set(CL.DISPOSITIONS)

    def test_no_authority_exists_before_a_founder_decision(self, closure_doc):
        for name in CL.AUTHORITY_DISPOSITIONS:
            assert closure_doc["disposition_counts"].get(name, 0) == EXPECTED["authority"]

    def test_policy_not_found_is_only_said_of_a_page_that_served(self, closure_doc):
        """A property nobody fetched has not told us anything. Saying
        POLICY_NOT_FOUND about it is a claim about the hotel made from a fact
        about us."""
        for row in closure_doc["rows"]:
            if row["disposition"] != CL.POLICY_NOT_FOUND:
                continue
            assert row["acquisition_outcome"] == "POLICY_NOT_FOUND", row["identity_key"]

    def test_the_partition_covers_every_census_identity_exactly_once(
            self, partition_doc, census_doc):
        keys = [item["identity_key"] for item in partition_doc["items"]]
        assert sorted(keys) == sorted(r["identity_key"] for r in census_doc["hotels"])
        assert partition.validate(partition_doc) == ()

    def test_the_partition_publishes_nothing(self, partition_doc):
        counts = partition_doc["final_state_counts"]
        assert counts.get(enums.PUBLISHED_PET_FRIENDLY, 0) == 0
        assert counts.get(enums.VERIFIED_NO_PETS, 0) == 0

    def test_a_reviewed_candidate_waits_on_a_person_not_on_the_machine(
            self, partition_doc):
        counts = partition_doc["final_state_counts"]
        assert counts.get(enums.AWAITING_FOUNDER_DECISION, 0) == EXPECTED[
            "publication_grade"]


class TestFounderReview:
    def test_every_candidate_is_publication_grade(self, review, store):
        confirmed = [r for r in store["records"]
                     if r["publication_grade"]["verdict"] == "PUBLICATION_GRADE_CONFIRMED"]
        assert review["count"] == len(confirmed) == EXPECTED["review_candidates"]

    def test_no_candidate_carries_an_approval(self, review):
        for candidate in review["candidates"]:
            assert candidate["review_status"] == enums.MACHINE_REVIEWED_PENDING_OPERATOR
            assert candidate["founder_decision"] == ""
            assert candidate["founder_reviewer_id"] == ""
            assert candidate["founder_reviewed_at"] == ""

    def test_every_candidate_carries_its_hash_material(self, review):
        for candidate in review["candidates"]:
            binding = candidate["semantic_approval"]
            assert binding["binding_contract"] == "semantic-approval/1.0"
            assert binding["semantic_hash"].startswith("sha256:")
            assert binding["projection"]["identity_key"] == candidate["identity_key"]
            assert not binding["unclassified_fields"]

    def test_every_candidate_carries_evidence_and_a_source(self, review):
        for candidate in review["candidates"]:
            assert candidate["source_url"]
            assert candidate["snapshot_hash"]
            assert candidate["lineage"]["block_sha256"]
            assert candidate["evidence"] or candidate["withheld_fields"]

    def test_a_recommendation_is_never_an_authority_word(self, review):
        for candidate in review["candidates"]:
            assert candidate["recommendation"].startswith("RECOMMEND_")


class TestNoPublicationOrLaunch:
    def test_st_louis_publishes_nothing(self, census_doc, closure_doc):
        assert all(row["policy_state"] == enums.POLICY_NOT_VERIFIED
                   for row in census_doc["hotels"])
        assert closure_doc["disposition_counts"].get(
            CL.AUTHORITY_PET_FRIENDLY, 0) == 0

    def test_the_benchmark_reports_its_own_measured_result(self):
        benchmark = _load("st_louis_mo_benchmark_001.json")
        scorecard = benchmark["scorecard"]
        assert scorecard["active_closure_pct"]["actual"] == 100.0
        # The two misses are recorded as misses, not reframed.
        assert scorecard["automatic_routing_pct"]["actual"] < 90
        assert scorecard["observed_acquired_pct"]["actual"] < 85
        assert benchmark["architecture"]["counts"]["market_specific_scripts"] == 0
