"""PTF-ST-LOUIS-PRODUCTION-DEPLOY-012 -- the six-market bundle is LIVE.

St. Louis joined production. 333 profiles became 415, five live markets became
six, and the deployment consumed the authorization PTF-ST-LOUIS-REGISTER-PUBLISH-011
prepared and did not reuse an older one.

What these assert is the DURABLE shape of that, not the run:

  * the authorization is consumed -- DEPLOYED, and refused for any further
    deploy -- and the record names it;
  * the record describes an addition, not a replacement: 509 files added, none
    removed, one changed, and that one is the sitemap;
  * every earlier authorization stays DEPLOYED history, unreopened and unreused;
  * the live verification actually covered the whole public surface rather than
    a sample, and the four Milwaukee service-animal corrections survived.

No network here. The live checks happened once, against production, and their
outcome is recorded; a test that re-fetched the internet would be testing the
internet.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import launch_participation as LP

AUTH_ID = "ptf-auth-011-2077ad2895c9"
RECORD_ID = "ptf-deploy-011-6a8cab48ead9d4293f477472"
DEPLOY_ID = "6a8cab48ead9d4293f477472"
BUNDLE = "2077ad2895c9273ddc9deed62295058f88915e20cb6fcd4072433d1c17dff741"
#: The deploy this one replaced, and the rollback target if it must be undone.
PREVIOUS_DEPLOY = "6a8c6de6fa99ff1f7bd5c7f5"
PREVIOUS_BUNDLE = "70747f09fdfe18ccc18e13a3155cc6287404e3ddfe5bb5784d0f03cc30348967"

SIX = ["cleveland-akron-canton-oh", "columbus-oh", "dayton-oh", "milwaukee-wi",
       "pittsburgh-pa", "st-louis-mo"]
PROFILES = {"cleveland-akron-canton-oh": 99, "columbus-oh": 88, "dayton-oh": 47,
            "milwaukee-wi": 73, "pittsburgh-pa": 26, "st-louis-mo": 82}


@pytest.fixture()
def auth():
    return DA.load_authorization(AUTH_ID)


@pytest.fixture()
def record():
    return json.loads(
        (REPO / "deploy" / "netlify" / "deployment_records"
         / ("%s.json" % RECORD_ID)).read_text(encoding="utf-8"))


@pytest.fixture()
def manifest():
    return GD.load_manifest()


# --------------------------------------------------------------------------- #
# The authorization was used, once.
# --------------------------------------------------------------------------- #

class TestTheAuthorizationIsConsumed:
    def test_it_is_deployed_and_may_never_deploy_again(self, auth):
        assert auth["authorization_status"] == DA.DEPLOYED
        assert DA.deployability_problems(auth), \
            "a consumed authorization must never be deployable again"

    def test_its_state_history_is_the_whole_path(self, auth):
        statuses = [entry["status"] for entry in auth["status_history"]]
        assert statuses == [DA.PREPARED, DA.AUTHORIZED, DA.DEPLOYED]
        final = auth["status_history"][-1]
        assert final["deployment_id"] == DEPLOY_ID
        assert final["deployment_record_id"] == RECORD_ID

    def test_it_still_binds_the_artifact_that_went_live(self, auth):
        assert DA.verify_authorization(auth) == []
        assert auth["bundle_sha256"] == BUNDLE
        assert auth["total_profiles"] == 415
        assert auth["sitemap_route_count"] == 515
        assert auth["participating_markets"] == SIX
        assert auth["profile_counts"] == PROFILES

    def test_no_earlier_authorization_was_reopened_or_reused(self):
        by_id = {a["authorization_id"]: a for a in DA.list_authorizations()}
        assert set(by_id) == {AUTH_ID, "ptf-auth-012-70747f09fdfe",
                              "ptf-auth-047-a324b1bf5023"}
        for a in by_id.values():
            assert a["authorization_status"] == DA.DEPLOYED
            assert DA.deployability_problems(a)

    def test_no_credential_is_recorded(self, auth, record):
        for doc in (auth, record):
            blob = json.dumps(doc).lower()
            for needle in ("nfp_", "netlify_auth_token", "bearer ",
                           "ecf6b5ee-45cb-4ead-a242-3f0f9096de15"):
                assert needle not in blob


# --------------------------------------------------------------------------- #
# The record.
# --------------------------------------------------------------------------- #

class TestTheDeploymentRecord:
    def test_it_verifies_against_the_authorization_it_consumed(self, record, auth):
        assert DA.verify_record(record, auth) == []
        assert record["authorization_id"] == AUTH_ID
        assert record["final_status"] == DA.DEPLOYED
        assert record["exit_status"] == 0
        assert record["rollback_used"] is False

    def test_it_names_the_deploy_and_what_it_replaced(self, record, auth):
        assert record["deployment_id"] == DEPLOY_ID
        assert record["previous_deployment_id"] == PREVIOUS_DEPLOY
        # The rollback target is the deploy this one replaced, so undoing it is
        # a restore of a known-good artifact rather than a rebuild.
        assert record["rollback_target"] == PREVIOUS_DEPLOY == auth["rollback_target"]
        assert record["target_site"] == "pettripfinder-prod"
        assert record["production_url"] == "https://pettripfinder.com"

    def test_it_records_a_six_market_415_profile_release(self, record):
        assert record["participating_markets"] == SIX
        assert record["profile_counts"] == PROFILES
        assert sum(PROFILES.values()) == record["total_profiles"] == 415
        assert record["sitemap_route_count"] == 515
        assert record["global_gate_results"] == {"required": 27, "passed": 27,
                                                 "failed": []}

    def test_measurement_and_affiliates_were_not_switched_on(self, record):
        assert record["measurement"] == {"enabled": False, "provider_kind": "none"}
        assert record["affiliate"] == {"providers_enrolled": 0,
                                       "destinations_active": 0}


# --------------------------------------------------------------------------- #
# What the live verification found.
# --------------------------------------------------------------------------- #

class TestLiveVerification:
    def test_it_passed(self, record):
        assert record["live_verification_results"]["overall_pass"] is True

    def test_every_st_louis_route_served_the_deployed_bytes(self, record):
        stl = record["live_verification_results"]["st_louis_routes"]
        assert stl["hotel_profiles"] == 82
        assert stl["checked"] == stl["http_200"] == 83   # 82 profiles + the hub
        assert stl["bytes_match_deployed_bundle"] == 83
        assert stl["failed_or_missing"] == []

    def test_the_whole_public_surface_was_checked_not_a_sample(self, record):
        """515 routes fetched and byte-compared. A spot check can only say a
        deploy is not obviously broken; this says what it actually serves."""
        every = record["live_verification_results"]["every_sitemap_route"]
        assert every["checked"] == every["http_200"] == 515
        assert every["bytes_match_deployed_bundle"] == 515
        assert every["failures"] == []

    def test_the_go_interstitials_are_live_and_noindex(self, record):
        """They carry no sitemap entry by design, so the 515-route sweep cannot
        see them and they are verified on their own."""
        go = record["live_verification_results"]["st_louis_go_interstitials"]
        assert go["checked"] == go["http_200"] == 82
        assert go["bytes_match_deployed_bundle"] == 82
        assert go["all_noindex"] is True

    def test_the_milwaukee_correction_survived_this_deploy(self, record):
        mke = record["live_verification_results"][
            "milwaukee_service_animal_correction"]
        assert mke["checked"] == mke["http_200"] == 4
        assert mke["carry_the_corrected_sentence"] == 4
        assert mke["still_carry_the_false_sentence"] == 0
        assert mke["bytes_match_deployed_bundle"] == 4

    def test_it_was_an_addition_and_not_a_replacement(self, record):
        """The claim the founder authorized: St. Louis is added and nothing
        existing moves. 509 files added, none removed, and the one pre-existing
        file that changed is the sitemap -- which cannot not change when a
        market joins."""
        diff = record["live_verification_results"][
            "public_differential_vs_previous_deploy"]
        assert diff["previous_deployment_id"] == PREVIOUS_DEPLOY
        assert diff["added"] == 509
        assert diff["removed"] == 0
        assert diff["changed"] == 1
        assert diff["changed_files"] == ["sitemap.xml"]
        assert diff["added_outside_st_louis_namespace"] == 0

    def test_held_and_superseded_identities_have_no_live_route(self, record):
        """404 is the assertion. A held property that merely renders as hidden
        is one template change away from being published."""
        absent = record["live_verification_results"]["absent_by_design"]
        assert absent["held_days_inn_and_suites_pontoon_beach"] == 404
        assert absent["superseded_wingate_at_wyndham"] == 404
        assert absent["superseded_doubletree"] == 404
        # A registered market the founder withheld is equally absent.
        assert absent["withheld_market_indianapolis_hub"] == 404

    def test_the_live_sitemap_is_the_one_the_manifest_pins(self, record, auth):
        sm = record["live_verification_results"]["sitemap"]
        assert sm["status"] == 200
        assert sm["loc_count"] == sm["unique_locs"] == 515
        assert sm["sha256"] == auth["sitemap_sha256"]
        assert sm["matches_manifest_pin"] and sm["matches_deployed_bundle"]
        assert sm["go_entries"] == 0
        assert sm["indianapolis_entries"] == 0
        assert sm["st_louis_routes"] == 99   # 82 profiles + 15 corridors + hub + comparison

    def test_every_market_serves_the_profiles_its_contract_promises(self, record):
        by_market = record["live_verification_results"][
            "live_profile_routes_by_market"]
        assert {k: v for k, v in by_market.items() if k != "total"} == PROFILES
        assert by_market["total"] == 415


# --------------------------------------------------------------------------- #
# The repository agrees with what is live.
# --------------------------------------------------------------------------- #

class TestTheRepositoryMatchesProduction:
    def test_the_manifest_verifies_and_mirrors_the_consumed_authorization(self, manifest):
        assert GD.verify_manifest() == []
        assert manifest["deployment_authorized"] is True
        assert manifest["deployment_authorization"]["authorization_id"] == AUTH_ID
        assert manifest["bundle_sha256"] == BUNDLE

    def test_the_founder_authorized_set_is_the_six_that_are_live(self):
        assert LP.authorized_market_ids() == sorted(SIX)

    def test_no_seventh_market_was_admitted(self):
        assert (LP.launch_status("indianapolis-in")
                == LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH)
        for market_id in ("cincinnati-oh", "detroit-ann-arbor-mi"):
            assert LP.launch_status(market_id) == LP.NOT_SOURCE_READY

    def test_the_deploy_lineage_reads_back_in_order(self):
        """Three production deploys, each consuming its own authorization and
        naming the one before it as its rollback target."""
        records = {r["deployment_record_id"]: r for r in DA.list_records()}
        chain = [
            ("ptf-deploy-047-6a8a2dada6e73cb0d819c9d0", "6a78dc1cdad05ac32bc58cec"),
            ("ptf-deploy-012-6a8c6de6fa99ff1f7bd5c7f5", "6a8a2dada6e73cb0d819c9d0"),
            (RECORD_ID, PREVIOUS_DEPLOY),
        ]
        assert set(records) == {rid for rid, _ in chain}
        for record_id, rollback in chain:
            assert records[record_id]["rollback_target"] == rollback
        assert records[RECORD_ID]["bundle_sha256"] == BUNDLE
        assert (records["ptf-deploy-012-6a8c6de6fa99ff1f7bd5c7f5"]["bundle_sha256"]
                == PREVIOUS_BUNDLE)
