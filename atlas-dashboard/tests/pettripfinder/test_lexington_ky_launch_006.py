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


class TestLexingtonIsLive:

    def test_the_live_release_is_the_lexington_deploy(self):
        live = RI.current_verified_live()
        assert live.deploy_id == DEPLOY_ID
        assert live.bundle_sha256 == CANDIDATE
        assert live.sitemap_sha256 == SITEMAP
        assert (len(live.participating_markets), live.total_profiles,
                live.sitemap_route_count) == (12, 823, 991)
        assert MARKET in live.participating_markets
        assert live.profile_counts[MARKET] == 20
        assert not live.problems

    def test_toledo_and_every_other_market_survived_unchanged(self):
        live = RI.current_verified_live()
        parent = _load(DEPLOY / "deployment_records"
                       / "ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json")
        assert "toledo-oh" in live.participating_markets
        for market, was in parent["profile_counts"].items():
            assert live.profile_counts[market] == was, market
        assert set(live.participating_markets) - set(parent["profile_counts"]) == {MARKET}

    def test_no_unauthorized_market_joined(self):
        live = RI.current_verified_live()
        for market in ("nashville-tn", "chattanooga-tn", "fort-wayne-in",
                       "detroit-ann-arbor-mi"):
            assert market not in live.participating_markets

    def test_participation_records_the_founder_decision(self):
        assert LP.launch_status(MARKET) == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        doc = _load(DEPLOY / "launch_participation.json")
        assert doc["decision"]["work_order"] == \
            "PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
        assert doc["decision"]["supersedes"]["work_order"] == \
            "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"
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

    def test_the_live_pin_agrees_and_the_verifier_is_silent(self):
        live = RI.current_verified_live()
        assert live.rollback_target == PARENT_DEPLOY
        assert live.rollback_record == \
            "ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json"
        assert len(live.rollback_markets) == 11
        # The pin carried the Cincinnati value into this launch. Zero problems
        # is the assertion that it no longer does.
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

    def test_the_opening_is_recorded_as_consumed_by_this_launch(self):
        gate = _load(PKG / "release_production_gate.json")
        fast = _load(PKG / "fast_release_activation.json")
        for doc in (gate, fast):
            assert doc["consumed"]["market_id"] == MARKET
            assert doc["consumed"]["candidate_digest"] == CANDIDATE
            assert doc["consumed"]["host_deployment_id"] == DEPLOY_ID

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
