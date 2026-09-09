"""PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003 -- this order's gates.

Lexington is the first market to cross from the pre-redesign market factory
into the redesigned ATLAS-THROUGHPUT release lane. What that crossing must NOT
do is quietly change what Lexington means, and what it must not do EITHER is
lower a modern gate to keep an old count. These tests hold both halves.

The order of the assertions is the order of the argument:

    1  the shadow is reproduced EXACTLY -- 61 / 28 / 14 / 19
    2  the registered market is what remains after named gates, and every
       removal is named
    3  nothing held reaches the published authority
    4  the published authority satisfies the contracts that own it
    5  nothing is live, nothing is activated, nothing is authorized
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder import epochs

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.contracts import census as CENSUS
from scripts.pettripfinder.contracts import policy_schema as POLICY
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.markets import contract as MC

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
DEPLOY = REPO_ROOT / "deploy" / "netlify"
MARKET_ID = "lexington-ky"
ORDER = "PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def shadow():
    return _load(REPORTS / "lexington_ky_shadow_market_002.json")


@pytest.fixture(scope="module")
def clean():
    return _load(REPORTS / "lexington_ky_clean_inventory_002.json")


@pytest.fixture(scope="module")
def census():
    return _load(PKG / "identity_census" / ("%s.json" % MARKET_ID))


@pytest.fixture(scope="module")
def holds():
    return _load(PKG / "lexington_ky_identity_holds_003.json")


@pytest.fixture(scope="module")
def policy():
    return _load(PKG / ("hotel_policy_facts_%s.json" % MARKET_ID))


@pytest.fixture(scope="module")
def exclusions():
    return _load(PKG / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json")


@pytest.fixture(scope="module")
def partition():
    return _load(PKG / "lexington_ky_final_partition_001.json")


class TestTheShadowIsReproducedExactly:
    """The migration is semantic-preserving, and this is what that means."""

    def test_the_governing_shadow_numbers_are_still_the_shadows_own(self, shadow):
        assert shadow["census"]["confirmed_active_identities"] == 61
        assert shadow["policy"]["clean_pet_friendly"] == 28
        assert shadow["policy"]["clean_verified_no_pets"] == 14
        assert shadow["policy"]["unresolved"] == 19

    def test_the_clean_cohort_is_carried_across_row_for_row(self, clean, shadow):
        rows = clean["clean_rows"]
        assert len(rows) == 42
        pf = [r for r in rows if r["policy_class"] == "CLEAN_PET_FRIENDLY"]
        np = [r for r in rows if r["policy_class"] == "CLEAN_VERIFIED_NO_PETS"]
        assert len(pf) == shadow["policy"]["clean_pet_friendly"]
        assert len(np) == shadow["policy"]["clean_verified_no_pets"]

    def test_the_registered_market_plus_its_holds_accounts_for_every_clean_row(
            self, clean, policy, exclusions, holds):
        """42 clean rows in, and every one is either published or named as held.

        This is the assertion that makes a silent drop impossible: a row that
        vanished without a hold record fails here, and so does a hold record
        for a row that is also published.
        """
        published = ({h["key"] for h in policy["hotels"]}
                     | {r["normalized_name"] for r in exclusions["exclusions"]})
        held = {h["identity_key_proposed"] for h in holds["holds"]}
        clean_keys = {ptf_identity_key(r["canonical_name"]) for r in clean["clean_rows"]}
        unaccounted = sorted(clean_keys - published - held)
        assert unaccounted == [], unaccounted
        assert not (published & held)


class TestEveryRemovalIsNamed:

    def test_the_holds_document_names_every_held_row_and_its_class(self, holds):
        assert holds["count"] == len(holds["holds"])
        assert holds["count"] == 15
        assert dict(holds["counts_by_class"]) == {
            "CROSS_MARKET_IDENTITY_COLLISION": 1,
            "IDENTITY_HOLD": 3,
            "MODERN_EVIDENCE_GATE_HOLD": 5,
            "PAID_PROVENANCE_HOLD": 6,
        }
        for record in holds["holds"]:
            assert record["published_anything"] is False
            assert record["why"].strip()
            assert record["next_action"].strip()

    def test_no_hold_is_a_lowered_gate(self, holds):
        """Each class is a refusal by a rule the repository already owns."""
        owners = {
            "IDENTITY_HOLD": "ptf_identity_key/1.0 keys on the canonical name alone",
            "CROSS_MARKET_IDENTITY_COLLISION": "hotel_exclusions.validate refuses a "
                                               "second exclusion under one name",
            "MODERN_EVIDENCE_GATE_HOLD": "first_party_binding",
            "PAID_PROVENANCE_HOLD": "ptf_paid_attempt_ledger_001.json",
        }
        assert set(holds["counts_by_class"]) <= set(owners)

    def test_the_paid_provenance_holds_are_reversible_without_recapture(self, holds):
        paid = [h for h in holds["holds"] if h["classification"] == "PAID_PROVENANCE_HOLD"]
        assert paid
        for record in paid:
            assert record["reversible_without_recapture"] is True
            assert "lexington_ky_firecrawl_002" in record["next_action"]


class TestTheRegisteredMarket:

    def test_the_market_contract_parses_and_states_its_membership_basis(self):
        path = PKG / "markets" / ("%s.json" % MARKET_ID)
        cfg = MC.parse_market(_load(path), source=str(path))
        assert cfg.market_id == MARKET_ID
        assert cfg.route_mode == MC.ROUTE_MODE_MARKET_PREFIXED
        assert len(cfg.corridors) == 7
        # A postal-code partition of these corridors does not exist: 40505 is
        # in two of them and 40509 in two others, and seventeen census rows
        # state no ZIP at all. MARKET_GEOGRAPHY is the contract's own basis for
        # exactly this shape.
        doc = _load(path)
        assert doc["census_membership_basis"] == MC.MEMBERSHIP_MARKET_GEOGRAPHY
        for corridor in doc["corridors"]:
            assert corridor["included_postal_codes"] == []
            assert corridor["explicit_hotel_ids"]

    def test_the_census_validates_and_every_identity_key_is_canonical(self, census):
        assert census["market_id"] == MARKET_ID
        assert census["count"] == 57
        assert census["shadow_confirmed_identities"] == 61
        assert CENSUS.validate(census, market_states=["KY"]) == ()
        keys = [h["identity_key"] for h in census["hotels"]]
        assert len(keys) == len(set(keys))
        for row in census["hotels"]:
            assert row["identity_key"] == ptf_identity_key(row["canonical_name"])

    def test_every_corridor_membership_matches_the_census(self, census):
        path = PKG / "markets" / ("%s.json" % MARKET_ID)
        doc = _load(path)
        declared = {c["corridor_id"]: set(c["explicit_hotel_ids"]) for c in doc["corridors"]}
        for row in census["hotels"]:
            assert row["identity_key"] in declared[row["corridor"]], row["identity_key"]
        assert sum(len(v) for v in declared.values()) == census["count"]

    def test_the_partition_names_every_census_identity_once(self, census, partition):
        keys = [i["identity_key"] for i in partition["items"]]
        assert sorted(keys) == sorted(h["identity_key"] for h in census["hotels"])
        assert partition["count"] == census["count"]
        counts = partition["final_state_counts"]
        assert counts["PUBLISHED_PET_FRIENDLY"] == 20
        assert counts["VERIFIED_NO_PETS"] == 10
        # A row the modern gates held is not "unrouted" and not "unread": it is
        # awaiting a policy ARTIFACT, which is a different and truthful state.
        assert counts["AWAITING_POLICY_ARTIFACT"] == 11


class TestThePublishedAuthority:

    def test_the_policy_package_validates(self, policy):
        assert policy["market_id"] == MARKET_ID
        assert len(policy["hotels"]) == 20
        assert POLICY.validate_package(policy) == ()

    def test_the_exclusion_shard_validates(self, exclusions):
        assert exclusions["market_id"] == MARKET_ID
        assert len(exclusions["exclusions"]) == 10
        HE.validate(exclusions)

    def test_every_published_row_carries_first_party_evidence(self, policy):
        for record in policy["hotels"]:
            assert record["evidence"], record["name"]
            for entry in record["evidence"]:
                assert entry["source_url"].startswith("https://")
                assert entry["quote"].strip()
                assert entry["artifact_sha256"].startswith("sha256:")
                assert len(entry["artifact_sha256"]) == 71
                assert entry["captured_at"]

    def test_every_published_row_carries_the_withholding_forward(self, policy):
        """PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 published acceptance and
        withheld fee, weight and count on purpose. Carrying the withholding
        forward is what stops a blank from reading as a zero."""
        for record in policy["hotels"]:
            assert set(record["facts"]) == {"pets_allowed"}
            assert record["facts"]["pets_allowed"] is True
            assert record["withheld_facts"]

    def test_no_lexington_published_identity_belongs_to_another_market(self, policy,
                                                                       exclusions):
        mine = ({h["key"] for h in policy["hotels"]}
                | {r["normalized_name"] for r in exclusions["exclusions"]})
        others = set()
        for path in sorted(PKG.glob("hotel_policy_facts_*.json")):
            doc = _load(path)
            if doc.get("market_id") == MARKET_ID:
                continue
            others |= {h.get("key") or h.get("identity_key") for h in doc.get("hotels") or ()}
        for path in sorted((PKG / "markets" / "authority").glob("*/hotel_exclusions.json")):
            doc = _load(path)
            if doc.get("market_id") == MARKET_ID:
                continue
            others |= {r["normalized_name"] for r in doc.get("exclusions") or ()}
        assert not (mine & others), sorted(mine & others)

    def test_the_generated_globals_are_in_sync_with_the_shards(self):
        assert MA.check_generated_artifacts() == []

    def test_the_seed_shard_has_one_row_per_published_record(self, policy):
        rows = MA.load_market_seed_rows(MARKET_ID)
        assert len(rows) == len(policy["hotels"])
        names = {h["name"] for h in policy["hotels"]}
        assert {r["name"] for r in rows} == names
        for row in rows:
            for field in ("address", "city", "state", "postal_code", "website_url",
                          "source_url", "observed_at", "pet_policy"):
                assert str(row.get(field) or "").strip(), (row["name"], field)


class TestNothingIsLiveAndNothingIsAuthorized:

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what="Lexington was registered and WITHHELD. The launch flipped participation to FOUNDER_AUTHORIZED_FOR_LAUNCH, which is what launching a registered market means. That it was withheld at registration time is what this order proved, and the withholding is still provable from the participation record's own supersedes block.")
    def test_lexington_is_registered_and_explicitly_withheld_from_launch(self):
        assert LP.launch_status(MARKET_ID) == \
            "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what="the founder decision block named Toledo. The launch is the founder's next decision and names Lexington; the Toledo decision it replaced is carried in the lineage under its own sha256, which is where a superseded decision leaves its history.")
    def test_the_founder_decision_block_still_names_toledo_and_not_lexington(self):
        doc = _load(DEPLOY / "launch_participation.json")
        assert MARKET_ID not in doc["decision"]["reason"]
        authorized = [m["market_id"] for m in doc["markets"]
                      if m["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"]
        assert MARKET_ID not in authorized
        assert "toledo-oh" in authorized

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='no Lexington authorization existed. The launch created ptf-auth-lexington-006-67fe8617b79f, which only a founder decision may do and which this order was careful not to.')
    def test_no_deployment_authorization_exists_for_lexington(self):
        for path in (DEPLOY / "deployment_authorizations").glob("*.json"):
            assert MARKET_ID not in path.name
            assert MARKET_ID not in _load(path).get("participating_markets", [])

    def test_the_release_contract_grants_no_deployment(self):
        contract = _load(DEPLOY / "release_contracts" / ("%s.json" % MARKET_ID))
        assert contract["deployment_authorization"]["grants_deployment"] is False
        assert contract["deployment_authorization"]["asserts_market_complete"] is False
        assert contract["reconciliation"]["published_pet_friendly"] == 20
        assert contract["reconciliation"]["verified_no_pets"] == 10

    def test_the_production_activation_flags_are_untouched(self):
        fast = _load(PKG / "fast_release_activation.json")
        gate = _load(PKG / "release_production_gate.json")
        assert fast["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"
        assert fast["PRODUCTION_RELEASE_CONSUMPTION"] == "DISABLED"
        assert fast["pilot_allowlist"] == []
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] == "NO"
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] == []

    def test_the_enablement_plan_is_a_proposal_and_says_so(self):
        plan = _load(REPORTS / "lexington_ky_production_enablement_plan_003.json")
        assert plan["status"] == "PROPOSED_NOT_APPLIED"
        assert plan["applied"] is False
        assert plan["scope"] == "LEXINGTON_ONLY"
        for change in plan["proposed_changes"]:
            assert change["current"] != change["proposed"]
            assert MARKET_ID in str(change["proposed"]) or change["proposed"] in (
                "ENABLED", "YES", "ENABLED_FOR_PILOT_ALLOWLIST")

    def test_the_authorization_packet_is_unsigned(self):
        packet = _load(REPORTS / "lexington_deployment_authorization_004_PROPOSED.json")
        assert packet["status"] == "AWAITING_FOUNDER_AUTHORIZATION"
        assert packet["authorized_by"] is None
        assert packet["authorized_at"] is None
        assert packet["nothing_deployed"] is True
        assert packet["nothing_activated"] is True

    def test_the_packet_binds_the_parent_that_is_actually_live(self):
        packet = _load(REPORTS / "lexington_deployment_authorization_004_PROPOSED.json")
        live = _load(DEPLOY / "deployment_records"
                     / "ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json")
        parent = packet["parent_release"]
        assert parent["live_deploy_id"] == live["deployment_id"]
        assert parent["bundle_sha256"] == live["bundle_sha256"]
        assert parent["toledo_present"] is True
        # The stale-rollback trap this order had to walk around: the live
        # deploy's OWN rollback_target is the Cincinnati deploy Toledo
        # replaced, and rolling back to it would un-deploy Toledo.
        assert packet["rollback"]["target_deployment_id"] == live["deployment_id"]
        assert packet["rollback"]["never_roll_back_to"] == live["rollback_target"]
        assert packet["rollback"]["target_is_current_verified_parent"] is True


class TestTheModernLaneRanAndSaidSo:

    @pytest.fixture(scope="class")
    def lane(self):
        return _load(REPORTS / "lexington_ky_release_lane_003.json")

    def test_the_fast_lane_passed_every_rule_with_no_unknown(self, lane):
        receipt = lane["fast_lane_receipt"]
        assert receipt["eligible"] == "YES"
        assert receipt["unknown_rules"] == []
        assert receipt["failed_rules"] == []
        assert set(receipt["rules"]) == set("ABCDEFGHIJKLMNO")
        assert all(status == "PASS" for status in receipt["rules"].values())

    def test_the_first_party_gate_is_clean_over_what_remains(self, lane):
        gate = lane["first_party_gate"]
        assert gate["ineligible"] == 0
        assert gate["passed"] is True
        assert gate["records_evaluated"] == 30

    def test_the_release_diff_carries_no_unexpected_finding(self, lane):
        diff = lane["release_diff"]
        assert diff["findings"] == []
        assert diff["live_total_profiles"] == 803
        assert diff["proposed_total_profiles"] == 823
        assert MARKET_ID in diff["proposed_participating"]
        assert MARKET_ID not in diff["live_participating"]

    def test_no_unrelated_market_moved_into_or_out_of_the_candidate(self, lane):
        live = set(lane["release_diff"]["live_participating"])
        proposed = set(lane["release_diff"]["proposed_participating"])
        assert proposed - live == {MARKET_ID}
        assert live - proposed == set()

    def test_no_source_ready_market_auto_participated(self, lane):
        proposed = set(lane["candidate"]["markets"])
        for market_id in ("detroit-ann-arbor-mi", "nashville-tn", "chattanooga-tn",
                          "fort-wayne-in"):
            assert market_id not in proposed

    def test_no_unchanged_market_was_rebuilt(self, lane):
        assert lane["cache_reuse"]["UNCHANGED_MARKETS_REBUILT"] == 0
        assert lane["cache_reuse"]["unchanged_live_markets"]["bundles_rebuilt"] == 0

    def test_the_registration_widens_scope_and_the_report_says_which_paths(self, lane):
        """Registering a market is NOT data-only, and pretending otherwise is
        how a shared change escapes its regression."""
        surface = lane["registration_change_classification"]
        assert surface["FULL_REGRESSION_REQUIRED"] == "YES"
        assert surface["MARKET_AUTHORITY_DATA_ONLY"]["market_id"] is None
        assert "DEPLOYMENT_CHANGE" in surface["change_classes"]
        # The routine release is the other question, and the lane answered it.
        assert lane["fast_lane_receipt"]["change_class"] == "MARKET_AUTHORITY_DATA_ONLY"
        assert lane["fast_lane_receipt"]["full_regression_required_by_lane"] == "NO"
