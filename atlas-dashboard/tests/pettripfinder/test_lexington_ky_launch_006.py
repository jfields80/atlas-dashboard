"""PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 -- the launch.

LEXINGTON IS LIVE AT 20, deploy 6aa172121d37bb4013eb44a4, twelve markets / 823
profiles / 991 routes.

This launch is the only one in the repository that follows a founder HALT, so
these tests hold two things a normal launch suite would not:

    1  the authorization binds the FRESH package, and the retired 004 digest
       appears nowhere in it -- asserted absent, not merely unused
    2  the rollback target is the Toledo release, NOT the Cincinnati deploy
       Toledo replaced. The live pin still named the Cincinnati one when this
       launch began; the release-index verifier caught it and it was corrected.
       A test that only checked "a rollback target exists" would have passed
       over exactly that.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder import epochs
from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_coordinator as RC
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
DEPLOY = REPO_ROOT / "deploy" / "netlify"
MARKET = "lexington-ky"

DEPLOY_ID = "6aa172121d37bb4013eb44a4"
PARENT_DEPLOY = "6a9e047690ec8bdaf99bcad2"
PARENT_DIGEST = "895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0"
CANDIDATE = "67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78"
SITEMAP = "dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611"
FRESH_PACKAGE = "sha256:a29e4a966e1b68b918c1b0f34db21ff5525691fc5e7581fb58190cc1031310b0"
RETIRED_PACKAGE = "sha256:e5d26fd63bb2d2e2d3d632134cc40cd832d1a4d4c5e1b82f003aa58dc52c5380"
#: The deploy Toledo replaced. Rolling back to this would un-deploy Toledo.
NEVER_ROLL_BACK_TO = "6a9d33f5dc8c3d1cf9464376"
AUTH_ID = "ptf-auth-lexington-006-67fe8617b79f"
RECORD_ID = "ptf-deploy-lexington-006-6aa172121d37bb4013eb44a4"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def auth():
    return DA.load_authorization(AUTH_ID)


@pytest.fixture(scope="module")
def record():
    return _load(DEPLOY / "deployment_records" / ("%s.json" % RECORD_ID))


class TestLexingtonWentLiveAndStayed:
    """Lexington was the live release until PTF-NASHVILLE-TN-FOUNDER-
    AUTHORIZATION-AND-LIVE-LAUNCH-005 shipped the thirteenth market.

    What this launch did is a fact about a past deploy, so it is read from that
    deploy's OWN record. Asking ``current_verified_live`` would make these tests
    describe whichever release is newest, which is a different claim and one
    that every later launch falsifies again.
    """

    def test_the_release_it_shipped_is_recorded_as_it_shipped(self, record):
        assert record["deployment_id"] == DEPLOY_ID
        assert record["bundle_sha256"] == CANDIDATE
        assert record["sitemap_sha256"] == SITEMAP
        assert (len(record["participating_markets"]), record["total_profiles"],
                record["sitemap_route_count"]) == (12, 823, 991)
        assert MARKET in record["participating_markets"]
        assert record["profile_counts"][MARKET] == 20
        assert record["final_status"] == DA.DEPLOYED

    def test_it_is_the_parent_the_next_launch_built_on(self):
        """The chain, asserted from the successor rather than from a pin."""
        live = RI.current_verified_live()
        assert live.rollback_target == DEPLOY_ID
        assert live.deploy_id != DEPLOY_ID, "a successor should have replaced it"
        assert MARKET in live.participating_markets
        assert live.profile_counts[MARKET] == 20
        assert not live.problems

    def test_toledo_and_every_other_market_survived_unchanged(self, record):
        parent = _load(DEPLOY / "deployment_records"
                       / "ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json")
        assert "toledo-oh" in record["participating_markets"]
        for market, was in parent["profile_counts"].items():
            assert record["profile_counts"][market] == was, market
        assert set(record["participating_markets"]) - set(parent["profile_counts"]) \
            == {MARKET}

    def test_no_unauthorized_market_joined_at_this_launch(self, record):
        """Nashville joined LATER, on its own founder decision.

        It is named here deliberately: this launch must be provable not to have
        let it in, and that has to stay provable after a different launch did.
        """
        for market in ("nashville-tn", "chattanooga-tn", "fort-wayne-in",
                       "detroit-ann-arbor-mi"):
            assert market not in record["participating_markets"]
        assert "nashville-tn" in RI.current_verified_live().participating_markets

    def test_participation_still_carries_the_founder_decision(self):
        assert LP.launch_status(MARKET) == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        # The CURRENT decision block is the Charlotte registration, and the
        # Nashville launch before it. What THIS launch decided is an ancestor
        # now, and the chain is where an ancestor lives -- which is the whole
        # point of keeping one: the record moves on, the decision does not.
        # Read by work order rather than by position, so the next reissue moves
        # nothing here.
        chain = epochs.participation_decision_chain()
        mine = next(r for r in chain["records"]
                    if r["work_order"] ==
                    "PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006")
        assert MARKET in mine["founder_authorized"]
        # And it is still an ancestor of the record that stands today.
        assert mine["sha256"] != LP.participation_sha256()
        assert LP.launch_status("detroit-ann-arbor-mi") != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH


class TestTheAuthorizationBindsTheFreshPackage:

    def test_it_is_consumed_and_binds_the_candidate(self, auth):
        assert auth["authorization_status"] == DA.DEPLOYED
        assert auth["bundle_sha256"] == CANDIDATE
        assert auth["sitemap_sha256"] == SITEMAP
        assert auth["rollback_target"] == PARENT_DEPLOY

    def test_the_retired_004_digest_appears_nowhere_in_the_authorization(self, auth):
        """Asserted ABSENT, not merely unused.

        The 004 launch was halted over that digest. The cheapest way to undo a
        halt by accident is to copy a value forward from the packet that caused
        it, so the whole serialized authorization is searched.
        """
        assert RETIRED_PACKAGE not in json.dumps(auth)
        assert RETIRED_PACKAGE.split(":", 1)[1] not in json.dumps(auth)

    def test_the_committed_package_is_the_one_that_was_authorized(self):
        package = SMP.read_sealed(SMP.list_packages(MARKET)[-1])
        assert package["package_digest"] == FRESH_PACKAGE
        assert SMP.validate(package) == ()

    def test_the_packet_that_proposed_this_launch_bound_the_same_digests(self):
        packet = _load(PKG / "markets" / "reports"
                       / "lexington_deployment_authorization_006_PROPOSED.json")
        bound = packet["the_digests_this_authorization_binds"]
        assert bound["sealed_package_digest"] == FRESH_PACKAGE
        assert bound["final_candidate_digest"] == CANDIDATE
        assert bound["parent_release_digest"] == PARENT_DIGEST


class TestTheRollbackTargetIsTheToledoRelease:
    """The trap this launch actually walked into, caught by the verifier."""

    def test_the_record_rolls_back_to_toledo_not_to_cincinnati(self, record):
        assert record["rollback_target"] == PARENT_DEPLOY
        assert record["rollback_target"] != NEVER_ROLL_BACK_TO
        assert record["previous_deployment_id"] == PARENT_DEPLOY

    def test_the_record_chain_agrees_and_the_verifier_is_silent(self, record):
        """Read from the chain of records, not from the live pin.

        The live pin moved on to the Nashville release. What this launch has to
        keep proving is that ITS rollback target was the Toledo deploy -- the
        pin carried the Cincinnati value into this launch and the verifier
        caught it -- and that the chain onward from here is still unbroken.
        """
        assert record["rollback_target"] == PARENT_DEPLOY
        assert record["rollback_target"] != NEVER_ROLL_BACK_TO
        parent = _load(DEPLOY / "deployment_records"
                       / "ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json")
        assert parent["deployment_id"] == PARENT_DEPLOY
        assert len(parent["participating_markets"]) == 11
        live = RI.current_verified_live()
        assert live.rollback_record == ("ptf-deploy-lexington-006-%s.json" % DEPLOY_ID)
        assert list(live.problems) == []


class TestTheLiveVerificationIsRecorded:

    def test_every_critical_check_passed(self, record):
        lv = record["live_verification_results"]
        assert lv["ALL_CRITICAL_CHECKS_PASS"] is True
        assert lv["failed_critical_checks"] == []
        assert all(lv["critical_checks"].values())

    def test_the_live_bytes_are_the_authorized_bytes(self, record):
        lv = record["live_verification_results"]
        assert lv["sitemap_exact_match_to_authorized"] is True
        assert lv["route_sets_identical_to_authorized"] is True
        assert lv["authorized_route_count"] == 991
        assert lv["routes_http_200"] == 991
        assert lv["routes_byte_identical_to_authorized_bundle"] == 991
        assert lv["routes_non_200"] == [] and lv["routes_mismatched"] == []

    def test_nothing_was_removed_and_the_check_read_the_previous_deploy(self, record):
        lv = record["live_verification_results"]
        assert lv["previous_deploy_sitemap_read_from_its_own_address"] is True
        assert lv["previous_deploy_route_count"] == 966
        assert lv["routes_added_vs_previous_deploy"] == 25
        assert lv["routes_removed_vs_previous_deploy"] == 0
        assert lv["removed_routes"] == [] and lv["profiles_removed"] == 0
        assert lv["unrelated_routes_lost"] == [] and lv["unrelated_routes_gained"] == []

    def test_lexington_surfaces_and_the_held_rows_do_not(self, record):
        lv = record["live_verification_results"]
        assert lv["lexington_hub_200"] is True
        assert lv["lexington_comparison_200"] is True
        assert lv["lexington_routes_authorized"] == 25
        assert lv["lexington_routes_live_and_identical"] == 25
        assert len(lv["lexington_corridor_routes"]) == 3
        assert all(c["byte_identical"] for c in lv["lexington_corridor_routes"].values())
        # Three held rows share a NAME with a published one, so the probe is the
        # street address. A name probe would have found the published row and
        # called the leak a pass.
        assert lv["held_identities_surfaced_on"] == {}
        assert lv["forbidden_market_routes_live"] == []


class TestTheGateWasOpenedNarrowlyAndClosed:

    def test_both_gates_are_closed_again(self):
        fast = _load(PKG / "fast_release_activation.json")
        gate = _load(PKG / "release_production_gate.json")
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] == "NO"
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] == []
        assert fast["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"
        assert fast["pilot_allowlist"] == []

    def test_the_coordinator_refuses_every_market_again(self):
        for market in (MARKET, "toledo-oh", "nashville-tn", "cincinnati-oh"):
            allowed, _why = RC.production_activation_allowed(market)
            assert allowed is False, market

    def test_the_opening_is_still_recorded_as_consumed_by_this_launch(self):
        """The FAST-lane flag still names this launch. The coordinator gate has
        since been opened and closed again for Nashville, and names this launch
        as the opening it superseded -- the same fact from the other side.
        """
        fast = _load(PKG / "fast_release_activation.json")
        assert fast["consumed"]["market_id"] == MARKET
        assert fast["consumed"]["candidate_digest"] == CANDIDATE
        assert fast["consumed"]["host_deployment_id"] == DEPLOY_ID
        gate = _load(PKG / "release_production_gate.json")
        assert gate["consumed"]["market_id"] == "nashville-tn"
        assert gate["consumed"]["supersedes"] == \
            "PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"

    def test_the_factory_itself_was_not_disabled(self):
        """Closing a launch permission is not the same as switching the lane off."""
        fast = _load(PKG / "fast_release_activation.json")
        assert fast["FAST_PATH_IMPLEMENTED"] == "YES"
        assert fast["FAST_PATH_VALIDATED"] == "YES"

    def test_the_cache_consumption_flag_was_never_opened(self):
        fast = _load(PKG / "fast_release_activation.json")
        assert fast["PRODUCTION_RELEASE_CONSUMPTION"] == "DISABLED"


class TestTheHeldRowsAreUntouched:

    def test_fifteen_rows_are_still_held_in_four_classes(self):
        holds = _load(PKG / "lexington_ky_identity_holds_003.json")
        assert holds["count"] == 15
        assert dict(holds["counts_by_class"]) == {
            "CROSS_MARKET_IDENTITY_COLLISION": 1,
            "IDENTITY_HOLD": 3,
            "MODERN_EVIDENCE_GATE_HOLD": 5,
            "PAID_PROVENANCE_HOLD": 6,
        }
        assert all(h["published_anything"] is False for h in holds["holds"])

    def test_the_launch_published_twenty_not_the_shadows_twenty_eight(self):
        policy = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET))
        exclusions = _load(PKG / "markets" / "authority" / MARKET / "hotel_exclusions.json")
        assert len(policy["hotels"]) == 20
        assert len(exclusions["exclusions"]) == 10
