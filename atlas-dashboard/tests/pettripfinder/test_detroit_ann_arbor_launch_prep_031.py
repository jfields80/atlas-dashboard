# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031 -- the twelfth market, proposed not decided.

WHAT THIS ORDER ACTUALLY DID. Detroit's hardened authority has been complete and
assemblable since PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029; what it lacked was a
participation row. This order re-derived every Detroit number from committed
source, audited the published set for wrong-authority defects, proposed the row,
and reproduced the exact candidate a launch would build. It deployed nothing and
acquired nothing.

THE ROW IS A PROPOSAL AND SAYS SO. The schema has exactly one status that admits
a market, so a candidate that includes Detroit cannot be assembled without
writing FOUNDER_AUTHORIZED_FOR_LAUNCH. The distinction between a proposal and a
decision therefore lives in the decision block, and these tests hold it there:
``decided_by`` must not claim the founder, ``decided_on`` must carry no date, and
the reason must open by saying the row is proposed. If a later edit quietly turns
this into a signed decision, these tests fail -- which is the point.

DETROIT IS THE ONLY THING THAT MOVES. Eleven live markets keep their exact
profile counts, no route is removed, and 4937 of production's 4938 files are
byte-identical in the candidate. The single changed file is sitemap.xml, and its
change is a pure insertion of 133 lines. The two global market-listing pages do
NOT change, because Detroit is navigation-hidden exactly as live Louisville,
Cincinnati and Toledo are.

THE HELD ROWS STAY HELD. Westin Book Cadillac and Roberts Riverwalk publish
nothing, and the Troy EVEN Hotel and Hotel Indigo remain two distinct published
identities on one campus. A launch order is not a licence to revisit rulings, so
these are pinned rather than left to a future reader's judgement.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.site_data import normalize_name
from pettripfinder import epochs

#: The order that turned this order's proposal into a founder decision.
AUTHORIZING_ORDER = (
    "PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032")

PKG = REPO / "launch_packages" / "pettripfinder"
DEPLOY = REPO / "deploy" / "netlify"
MARKET = "detroit-ann-arbor-mi"

CANDIDATE = DEPLOY / "global_deployment_manifest_candidate_031.json"
PARTITION = PKG / "detroit_ann_arbor_final_partition_001.json"
CENSUS = PKG / "identity_census" / ("%s.json" % MARKET)
POLICY = PKG / "hotel_policy_facts_detroit-ann-arbor-mi.json"
SHARD = PKG / "markets" / "authority" / MARKET
PINS = REPO / "tests" / "pettripfinder" / "pins" / "deployment_state.json"

#: The reproduced candidate. Built once before the commit and again from a clean
#: detached worktree at ad3ffb2; both agree byte for byte.
CANDIDATE_BUNDLE = (
    "92b39c81c31988a1d3f778d239ebf5c794cecec4318f524f0d58298aaae8c881")
CANDIDATE_SITEMAP = (
    "ad71bdfaef134ccd35c02b31fb35feb016015fdf85e648f63cd11968af4e4d40")
#: What production serves, and what a pre-flip assembly still reproduces exactly.
LIVE_BUNDLE = (
    "895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0")
LIVE_DEPLOY_ID = "6a9e047690ec8bdaf99bcad2"

CENSUS_COUNT = 247
PUBLISHED = 121
NO_PETS = 81
RESOLVED = 202
UNRESOLVED = 45

LIVE_PROFILE_COUNTS = {
    "cincinnati-oh": 130,
    "cleveland-akron-canton-oh": 120,
    "columbus-oh": 88,
    "dayton-oh": 54,
    "grand-rapids-holland-mi": 43,
    "indianapolis-in": 82,
    "louisville-ky": 53,
    "milwaukee-wi": 73,
    "pittsburgh-pa": 61,
    "st-louis-mo": 82,
    "toledo-oh": 17,
}


@pytest.fixture(scope="module")
def candidate():
    return json.loads(CANDIDATE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def partition():
    return json.loads(PARTITION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def policy():
    return json.loads(POLICY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def participation():
    return LP.load_participation()


class TestTheRowIsAProposalNotADecision:
    """The one place the schema left room to tell them apart.

    This order wrote Detroit's row as a proposal because the assembler admits
    exactly one status and the candidate could not otherwise be composed. The
    four assertions that said "nobody signed this" were true of THIS epoch and
    are false of the record now: PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-
    AUTHORIZATION-032 is the founder authorization instrument that signed it.
    They are superseded BY NAME rather than deleted or quietly inverted, so the
    proposal state this order really did write stays on the record.
    """

    def test_detroit_is_admitted_because_that_is_the_only_admitting_status(
            self, participation):
        assert LP.launch_status(MARKET, participation) == (
            LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)

    @epochs.superseded(
        by=AUTHORIZING_ORDER,
        what="decided_by named this order and disclaimed a founder decision; "
             "the founder has since signed the record")
    def test_decided_by_does_not_claim_the_founder(self, participation):
        decided_by = participation["decision"]["decided_by"]
        assert "NO FOUNDER DECISION RECORDED" in decided_by
        # "founder" alone would read as a signature in the founder's name.
        assert decided_by.strip().lower() != "founder"

    @epochs.superseded(
        by=AUTHORIZING_ORDER,
        what="decided_on read PENDING; the founder decision now carries a date")
    def test_decided_on_carries_no_date(self, participation):
        decided_on = participation["decision"]["decided_on"]
        assert decided_on.startswith("PENDING")
        assert not re.search(r"\d{4}-\d{2}-\d{2}", decided_on)

    @epochs.superseded(
        by=AUTHORIZING_ORDER,
        what="the reason opened with PROPOSED, NOT DECIDED; it now records the "
             "founder decision")
    def test_the_reason_opens_by_saying_it_is_proposed(self, participation):
        assert participation["decision"]["reason"].startswith(
            "PROPOSED, NOT DECIDED.")

    @epochs.superseded(
        by=AUTHORIZING_ORDER,
        what="the row carried proposed_not_decided: true, which the signature "
             "removed because it is no longer true")
    def test_the_row_itself_is_flagged(self, participation):
        row = [r for r in participation["markets"]
               if r["market_id"] == MARKET][0]
        assert row.get("proposed_not_decided") is True

    def test_the_proposal_names_the_order_that_would_decide_it(self, participation):
        """Still asserted, from whichever side of the signature the record is on.

        Before the signature the proposal block named the order that would
        decide it. After it, the signed decision IS that order and names this
        one as the preparer. Either way the chain from preparation to decision
        is on the record, which is what this always checked.
        """
        decision = participation["decision"]
        proposal = decision.get("proposal")
        if proposal is not None:
            assert proposal["is_a_founder_decision"] is False
            assert proposal["authorization_required_from"] == AUTHORIZING_ORDER
            return
        assert decision["work_order"] == AUTHORIZING_ORDER
        assert decision["decided_by"] == "founder"
        assert decision["prepared_by"]["work_order"] == (
            "PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031")

    def test_no_other_market_status_moved(self, participation):
        authorized = set(LP.authorized_market_ids(participation))
        assert authorized == set(LIVE_PROFILE_COUNTS) | {MARKET}

    def test_the_superseded_record_is_the_toledo_one(self, participation):
        superseded = participation["decision"]["supersedes"]
        assert superseded["work_order"] == (
            "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003")
        assert superseded["founder_authorized"] == sorted(LIVE_PROFILE_COUNTS)

    def test_the_lineage_still_walks_back_to_the_first_multimarket_launch(
            self, participation):
        records = participation["decision"]["lineage"]["records"]
        assert records[0]["work_order"] == (
            "PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        assert records[-1]["work_order"] == (
            "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003")


class TestNothingWasAuthorized:
    """A preparation order that wrote an authorization would be a deploy order.

    This order wrote none, and that was the point of it. The founder has since
    authorized and deployed the candidate under
    PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032, so four of
    these assertions describe a window that has closed. They are superseded BY
    NAME rather than deleted: what this order did -- and deliberately did not do
    -- stays on the record.

    The one that survives unchanged is the candidate manifest's own flag. It is
    a statement about the artifact as this order wrote it, not about the world,
    and a later deployment does not make it false.
    """

    def test_the_candidate_records_itself_as_unauthorized(self, candidate):
        assert candidate["deployment_authorized"] is False

    @epochs.superseded(
        by=AUTHORIZING_ORDER,
        what="no authorization existed for the candidate bundle; the founder "
             "has since authorized it as ptf-auth-detroit-032-92b39c81c319")
    def test_no_authorization_exists_for_the_candidate_bundle(self):
        authorizations = sorted(
            (DEPLOY / "deployment_authorizations").glob("*.json"))
        for path in authorizations:
            doc = json.loads(path.read_text(encoding="utf-8"))
            assert CANDIDATE_BUNDLE not in json.dumps(doc), path.name

    @epochs.superseded(
        by=AUTHORIZING_ORDER,
        what="no deployment record existed for the candidate bundle; it has "
             "since been deployed as 6a9eda5a9bf4b1345d8e41dd")
    def test_no_deployment_record_exists_for_the_candidate_bundle(self):
        records = sorted((DEPLOY / "deployment_records").glob("*.json"))
        for path in records:
            doc = json.loads(path.read_text(encoding="utf-8"))
            assert doc.get("bundle_sha256") != CANDIDATE_BUNDLE, path.name

    @epochs.superseded(
        by=AUTHORIZING_ORDER,
        what="the live pin described the Toledo deployment at 803 profiles; it "
             "now describes the Detroit deployment at 924")
    def test_the_live_pin_block_still_describes_the_toledo_deployment(self):
        live = json.loads(PINS.read_text(encoding="utf-8"))["live"]
        assert live["deploy_id"] == LIVE_DEPLOY_ID
        assert live["bundle_sha256"] == LIVE_BUNDLE
        assert live["total_profiles"] == 803
        assert live["sitemap_route_count"] == 966
        assert MARKET not in live["participating_markets"]

    @epochs.superseded(
        by=AUTHORIZING_ORDER,
        what="source ran ahead of production by this order's proposal; the "
             "deployment brought the two back into sync")
    def test_the_source_pin_is_ahead_of_production_by_this_order(self):
        source = json.loads(PINS.read_text(encoding="utf-8"))["source"]
        assert source["ahead_of_production"] is True
        assert source["moved_by"] == "PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031"
        assert source["bundle_sha256"] == CANDIDATE_BUNDLE
        assert source["total_profiles"] == 924

    def test_what_this_order_prepared_is_what_production_now_serves(self):
        """The other side of the four above, and the reason they may be retired.

        Every digest this order prepared reached production unchanged. If a
        launch had deployed something else, retiring the assertions above would
        have hidden it; asserting the equality here means it cannot be.
        """
        live = json.loads(PINS.read_text(encoding="utf-8"))["live"]
        if live["deploy_id"] == LIVE_DEPLOY_ID:
            return  # not yet deployed; the assertions above still stand
        assert live["bundle_sha256"] == CANDIDATE_BUNDLE
        assert live["sitemap_sha256"] == CANDIDATE_SITEMAP
        assert live["total_profiles"] == 924
        assert live["sitemap_route_count"] == 1099
        assert MARKET in live["participating_markets"]
        assert live["profile_counts"][MARKET] == PUBLISHED
        for market_id, count in LIVE_PROFILE_COUNTS.items():
            assert live["profile_counts"][market_id] == count, market_id


class TestDetroitSourceAuthorityAgrees:
    """Every number the proposal cites, re-derived from Detroit's own files."""

    def test_census_and_partition_agree_on_the_identity_universe(self, partition):
        census = json.loads(CENSUS.read_text(encoding="utf-8"))
        assert census["count"] == CENSUS_COUNT
        assert len(census["hotels"]) == CENSUS_COUNT
        assert partition["count"] == CENSUS_COUNT
        assert len(partition["items"]) == CENSUS_COUNT

    def test_the_partition_arithmetic_closes(self, partition):
        states = {}
        for item in partition["items"]:
            states[item["final_state"]] = states.get(item["final_state"], 0) + 1
        assert states == partition["final_state_counts"]
        assert states["PUBLISHED_PET_FRIENDLY"] == PUBLISHED
        assert states["VERIFIED_NO_PETS"] == NO_PETS
        assert PUBLISHED + NO_PETS == RESOLVED
        assert CENSUS_COUNT - RESOLVED == UNRESOLVED

    def test_the_published_set_is_the_policy_package_is_the_seed_shard(
            self, partition, policy):
        published = {i["identity_key"] for i in partition["items"]
                     if i["final_state"] == "PUBLISHED_PET_FRIENDLY"}
        packaged = {h["key"] for h in policy["hotels"]}
        with (SHARD / "seed_businesses.csv").open(
                encoding="utf-8-sig", newline="") as handle:
            seeded = {normalize_name(row["name"])
                      for row in csv.DictReader(handle)}
        assert published == packaged == seeded
        assert len(published) == PUBLISHED

    def test_the_exclusion_shard_is_exactly_the_verified_no_pets_partition(
            self, partition):
        shard = json.loads((SHARD / "hotel_exclusions.json").read_text(
            encoding="utf-8"))
        excluded = {normalize_name(e["canonical_name"])
                    for e in shard["exclusions"]}
        no_pets = {i["identity_key"] for i in partition["items"]
                   if i["final_state"] == "VERIFIED_NO_PETS"}
        assert excluded == no_pets
        assert shard["count"] == NO_PETS == len(excluded)

    def test_no_identity_is_both_pet_friendly_and_verified_no_pets(self, partition):
        published = {i["identity_key"] for i in partition["items"]
                     if i["final_state"] == "PUBLISHED_PET_FRIENDLY"}
        no_pets = {i["identity_key"] for i in partition["items"]
                   if i["final_state"] == "VERIFIED_NO_PETS"}
        assert not published & no_pets

    def test_every_published_record_asserts_pets_allowed(self, policy):
        assert all(h["facts"].get("pets_allowed") is True
                   for h in policy["hotels"])

    def test_the_release_contract_verifies_with_zero_disagreements(self):
        assert RC.verify_contract(MARKET) == []

    def test_every_market_release_contract_verifies(self):
        assert dict(RC.verify_all()) == {
            market_id: [] for market_id in RC.available_market_ids()}


class TestNoWrongAuthorityInThePublishedSet:
    """The narrow safety audit, pinned so a later edit cannot undo it."""

    def test_every_pets_allowed_quote_comes_from_a_first_party_or_brand_page(
            self, policy):
        for hotel in policy["hotels"]:
            for ev in hotel.get("evidence", []):
                if ev.get("field") != "pets_allowed":
                    continue
                assert ev.get("source_grade") in (
                    "PT1_FIRST_PARTY", "PT1_PROPERTY", "PT2_BRAND"), hotel["key"]
                assert ev.get("artifact_class") == (
                    "PUBLICATION_GRADE_EVIDENCE"), hotel["key"]

    def test_no_published_row_rests_on_an_aggregator(self, policy):
        # Every evidence host must be a brand site or the property's own domain.
        forbidden = ("booking.com", "expedia.", "tripadvisor.", "yelp.",
                     "trivago.", "kayak.", "priceline.", "orbitz.", "agoda.",
                     "bringfido.", "petswelcome.")
        for hotel in policy["hotels"]:
            for ev in hotel.get("evidence", []):
                url = (ev.get("source_url") or "").lower()
                assert url, hotel["key"]
                assert not any(bad in url for bad in forbidden), hotel["key"]

    def test_no_policy_source_url_binds_two_published_identities(self, policy):
        # A shared page bound positionally is how one hotel inherits another's
        # policy; every published row must own its evidence page.
        owners = {}
        for hotel in policy["hotels"]:
            for ev in hotel.get("evidence", []):
                url = (ev.get("source_url") or "").rstrip("/").lower()
                owners.setdefault(url, set()).add(hotel["key"])
        shared = {u: k for u, k in owners.items() if len(k) > 1}
        assert shared == {}

    def test_the_only_shared_premise_is_the_troy_campus_ruling(self):
        with (SHARD / "seed_businesses.csv").open(
                encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        def key(row):
            return (re.sub(r"[^a-z0-9]+", " ", row["address"].lower()).strip(),
                    row["city"].lower().strip(),
                    row["postal_code"].strip())

        premises = {}
        for row in rows:
            premises.setdefault(key(row), []).append(row["name"])
        shared = {k: sorted(v) for k, v in premises.items() if len(v) > 1}
        assert shared == {
            ("575 w big beaver", "troy", "48084"): [
                "EVEN Hotel Detroit North Troy",
                "Hotel Indigo Detroit North Troy"]}

    def test_no_published_key_collides_with_another_market(self, policy):
        mine = {h["key"] for h in policy["hotels"]}
        for path in sorted(PKG.glob("hotel_policy_facts_*.json")):
            other_id = path.stem.replace("hotel_policy_facts_", "")
            if other_id == MARKET:
                continue
            other = json.loads(path.read_text(encoding="utf-8"))
            collisions = {h["key"] for h in other.get("hotels", [])} & mine
            assert collisions == set(), other_id

    def test_route_slugs_are_unique_within_the_market(self, partition):
        published = [i for i in partition["items"]
                     if i["final_state"] == "PUBLISHED_PET_FRIENDLY"]
        slugs = [i["slug"] for i in published]
        assert len(set(slugs)) == len(slugs) == PUBLISHED

    def test_no_row_carries_a_bare_service_animal_statement(self, policy):
        # A bare quote string here crashes the renderer; the field is structured.
        for hotel in policy["hotels"]:
            statement = hotel["facts"].get("service_animal_statement")
            assert statement is None or isinstance(statement, dict), hotel["key"]


class TestTheFounderRulingsThisOrderPreserved:
    """A launch order is not a licence to reopen decided work."""

    def _state(self, partition, canonical_name):
        rows = [i for i in partition["items"]
                if i["canonical_name"] == canonical_name]
        assert len(rows) == 1, canonical_name
        return rows[0]["final_state"]

    def test_the_troy_campus_carries_two_distinct_published_identities(
            self, partition):
        assert self._state(partition, "EVEN Hotel Detroit North Troy") == (
            "PUBLISHED_PET_FRIENDLY")
        assert self._state(partition, "Hotel Indigo Detroit North Troy") == (
            "PUBLISHED_PET_FRIENDLY")

    def test_doubletree_ann_arbor_north_stays_published(self, partition):
        assert self._state(partition, "DoubleTree by Hilton Ann Arbor North") == (
            "PUBLISHED_PET_FRIENDLY")

    def test_royal_park_and_the_siren_keep_their_partial_policy_publications(
            self, partition):
        assert self._state(partition, "Royal Park Hotel") == (
            "PUBLISHED_PET_FRIENDLY")
        assert self._state(partition, "The Siren Hotel") == (
            "PUBLISHED_PET_FRIENDLY")

    def test_the_held_rows_are_still_held_and_publish_nothing(
            self, partition, policy):
        packaged = {h["key"] for h in policy["hotels"]}
        for name in ("Westin Book Cadillac Detroit", "Roberts Riverwalk Hotel"):
            assert self._state(partition, name) == "AWAITING_POLICY_OBSERVATION"
            assert normalize_name(name) not in packaged


class TestTheCandidateAddsDetroitAndNothingElse:

    def test_the_candidate_pins_the_reproduced_bundle(self, candidate):
        assert candidate["bundle_sha256"] == CANDIDATE_BUNDLE
        assert candidate["sitemap_sha256"] == CANDIDATE_SITEMAP
        assert candidate["reproduced_from_committed_source"]["byte_identical"] is True

    def test_the_candidate_composes_twelve_markets_and_924_profiles(self, candidate):
        counts = {m["market_id"]: m["published_profiles"]
                  for m in candidate["participating_markets"]}
        assert counts == dict(LIVE_PROFILE_COUNTS, **{MARKET: PUBLISHED})
        assert candidate["total_published_profiles"] == 924
        assert sum(counts.values()) == 924
        assert len(counts) == 12

    def test_every_live_market_keeps_its_exact_profile_count(self, candidate):
        deltas = candidate["baseline_preservation"]["market_profile_deltas_vs_live"]
        for market_id, count in LIVE_PROFILE_COUNTS.items():
            assert deltas[market_id] == 0, market_id

    def test_detroit_is_the_only_non_zero_market_delta(self, candidate):
        deltas = candidate["baseline_preservation"]["market_profile_deltas_vs_live"]
        moved = sorted(k for k, v in deltas.items() if v != 0)
        assert moved == [MARKET]
        assert deltas[MARKET] == PUBLISHED

    def test_no_route_and_no_file_is_removed(self, candidate):
        preservation = candidate["baseline_preservation"]
        assert preservation["files_removed"] == 0
        assert preservation["prior_sitemap_routes_lost"] == 0
        assert preservation["unexpected_prior_market_change"] is False

    def test_the_only_changed_file_is_the_sitemap(self, candidate):
        assert candidate["baseline_preservation"]["changed_files"] == ["sitemap.xml"]
        assert candidate["baseline_preservation"]["files_byte_identical"] == 4937

    def test_the_routes_grow_by_exactly_detroits_own_surface(self, candidate):
        # 121 hotel profiles + 10 published corridors + hub + policy comparison.
        assert candidate["sitemap_route_count"] == 1099
        assert candidate["sitemap_route_count"] - 966 == 133

    def test_every_required_gate_passes(self, candidate):
        assert candidate["all_required_gates_pass"] is True
        failing = sorted(name for name, result in candidate["gates"].items()
                         if result["pass"] is not True)
        assert failing == []

    def test_the_assembly_is_clean(self, candidate):
        gates = candidate["gates"]
        assert gates["content.zero_broken_links"]["pass"] is True
        assert gates["assembly.no_route_collisions"]["pass"] is True
        assert gates["assembly.no_global_shadowing"]["pass"] is True
        assert gates["content.canonical_uniqueness"]["pass"] is True
        assert gates["global.live_routes_preserved"]["pass"] is True

    def test_no_unregistered_market_rides_along(self, candidate):
        composed = {m["market_id"] for m in candidate["participating_markets"]}
        assert "fort-wayne-in" not in composed
        assert "lexington-ky" not in composed
        assert candidate["excluded_markets"] == []

    def test_the_baseline_and_rollback_target_are_the_toledo_deployment(
            self, candidate):
        assert candidate["production_baseline"]["deployment_id"] == LIVE_DEPLOY_ID
        assert candidate["production_baseline"]["bundle_sha256"] == LIVE_BUNDLE
        assert candidate["production_baseline"]["published_profiles"] == 803
        assert candidate["rollback_target"]["deployment_id"] == LIVE_DEPLOY_ID
