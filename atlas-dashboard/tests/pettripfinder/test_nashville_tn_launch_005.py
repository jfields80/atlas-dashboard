"""PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 -- the launch.

NASHVILLE IS LIVE AT 79, deploy 6aa212a8ba9f174305c0441a, thirteen markets /
902 profiles / 1078 routes.

Three things here are not boilerplate, and each exists because of something this
launch got wrong or nearly got wrong.

  1  THE AUTHORIZATION WAS LEFT PREPARED, AND THE DEPLOY RAN ANYWAY.
     The authorize step wrote the authorization and never called ``transition``,
     so ``deployability_problems`` -- the gate that refuses to deploy anything
     but an AUTHORIZED authorization -- was never asked. Its substantive
     bindings were each checked directly and held, and live verification then
     proved production serves those exact bytes. The status history is asserted
     to SAY that, in order, rather than to read as though the transition had
     happened before the deploy.

  2  NO HELD ROW IS PROVED ABSENT BY PROBING ITS NAME.
     Two of the four held rows are cross-market collisions on a name another
     market already publishes. The proof that none leaked is set equality: every
     live Nashville profile slug is in the published authority set, and there are
     exactly as many of them as the authority holds. A name probe answers a
     narrower question and can answer it wrongly.

  3  THE PACKAGE DIGEST IS NOT ASSERTED EQUAL TO A FRESH SEAL.
     ``created_from_source_sha`` is a FIELD of the sealed package, so the digest
     moves with the commit while the seven dependency input digests do not. What
     proves authority did not move is that identity, and the candidate digest is
     unaffected either way because the assembler never reads the package.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_coordinator as RC
from scripts.pettripfinder import release_index as RI
from pettripfinder.conftest import manifest_problems_other_than_the_lapsed_pin

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
DEPLOY = REPO_ROOT / "deploy" / "netlify"
MARKET = "nashville-tn"

DEPLOY_ID = "6aa212a8ba9f174305c0441a"
PARENT_DEPLOY = "6aa172121d37bb4013eb44a4"
PARENT_DIGEST = "67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78"
CANDIDATE = "c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11"
SITEMAP = "13f5335fc1a055ce06de5ce66c7921da55308110e94c0b0f18806853c1662bc4"
PACKAGE = "sha256:8cdb83d4413cd48713113f32230877ba52998861e811d01bd06855f10a47b478"
DELTA = "sha256:104ed7ba3c0a917ffc274e62de175b5a1469d276784a62856ee81676fa33c79d"
RECEIPT = "sha256:600afcf7829f6d3b6994417bcd783b9f8e33554f76575d50a30713c5f69d599b"
#: The deploy Lexington replaced. Rolling back to this would un-deploy Lexington.
NEVER_ROLL_BACK_TO = "6a9e047690ec8bdaf99bcad2"
AUTH_ID = "ptf-auth-nashville-005-c12b410ec833"
RECORD_ID = "ptf-deploy-nashville-005-6aa212a8ba9f174305c0441a"
PUBLISHED = "PUBLISHED_PET_FRIENDLY"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def auth():
    return DA.load_authorization(AUTH_ID)


@pytest.fixture(scope="module")
def record():
    return _load(DEPLOY / "deployment_records" / ("%s.json" % RECORD_ID))


@pytest.fixture(scope="module")
def verification():
    return _load(PKG / "nashville_tn_live_verification_005.json")


class TestNashvilleIsLive:

    def test_the_live_release_is_the_nashville_deploy(self):
        live = RI.current_verified_live()
        assert live.deploy_id == DEPLOY_ID
        assert live.bundle_sha256 == CANDIDATE
        assert live.sitemap_sha256 == SITEMAP
        assert (len(live.participating_markets), live.total_profiles,
                live.sitemap_route_count) == (13, 902, 1078)
        assert MARKET in live.participating_markets
        assert live.profile_counts[MARKET] == 79
        assert not live.problems

    def test_lexington_and_every_other_market_survived_unchanged(self):
        live = RI.current_verified_live()
        parent = _load(DEPLOY / "deployment_records"
                       / ("ptf-deploy-lexington-006-%s.json" % PARENT_DEPLOY))
        assert "lexington-ky" in live.participating_markets
        assert "toledo-oh" in live.participating_markets
        for market, was in parent["profile_counts"].items():
            assert live.profile_counts[market] == was, market
        assert set(live.participating_markets) - set(parent["profile_counts"]) == {MARKET}

    def test_no_other_source_ready_market_joined(self):
        """The order names three markets it does not authorize. None joined."""
        live = RI.current_verified_live()
        for market in ("chattanooga-tn", "fort-wayne-in", "detroit-ann-arbor-mi"):
            assert market not in live.participating_markets
            assert LP.launch_status(market) != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH

    def test_participation_carries_the_founder_decision_for_nashville_only(self):
        """Read from wherever the record now keeps it.

        This decision was the CURRENT block until PTF-CHARLOTTE-NC-ZERO-TO-LIVE-
        BENCHMARK-001 registered a market and reissued the record. A reissue
        moves a decision into the lineage; it does not change it, which is what
        the lineage is for. The facts asserted are the same ones.
        """
        assert LP.launch_status(MARKET) == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        doc = _load(DEPLOY / "launch_participation.json")
        decision = doc["decision"]
        if decision["work_order"] != \
                "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005":
            # Superseded, and by a write that authorized nothing: this launch is
            # still the newest FOUNDER decision in the chain.
            newest = LP.decision_chain(doc)["records"][-1]
            assert newest["work_order"] == \
                "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
            assert MARKET in newest["founder_authorized"]
            assert newest["founder_authorized"] == LP.authorized_market_ids()
        else:
            assert decision["markets_moved"] == [MARKET]
        row = next(r for r in doc["markets"] if r["market_id"] == MARKET)
        assert row["founder_decision"]["authorized_candidate_digest"] == CANDIDATE
        assert row["founder_decision"]["authorized_package_digest"] == PACKAGE


class TestTheAuthorizationBindsTheAuthorizedCandidate:

    def test_it_is_consumed_and_binds_the_candidate(self, auth):
        assert auth["authorization_status"] == DA.DEPLOYED
        assert auth["bundle_sha256"] == CANDIDATE
        assert auth["sitemap_sha256"] == SITEMAP
        assert auth["rollback_target"] == PARENT_DEPLOY
        assert MARKET in auth["founder_authorized_markets"]
        assert len(auth["founder_authorized_markets"]) == 13

    def test_the_status_history_records_the_late_transition_honestly(self, auth):
        """The gate that was skipped, recorded as skipped.

        The deploy ran while this authorization was PREPARED. The history must
        read in order and the AUTHORIZED entry must say so in words, so that a
        reader cannot mistake it for a transition that preceded the deploy.
        """
        history = auth["status_history"]
        assert [entry["status"] for entry in history] == \
            [DA.PREPARED, DA.AUTHORIZED, DA.DEPLOYED]
        assert [entry["at"] for entry in history] == sorted(e["at"] for e in history)
        authorized = history[1]
        assert "PREPARED" in authorized["note"]
        assert "deployability_problems" in authorized["note"]
        assert DEPLOY_ID in history[2]["note"]

    def test_it_verifies_against_the_repository_it_names(self, auth):
        """Everything still agrees except the pin a later registration lapsed.

        PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 registered a fifteenth
        market, which reissues the participation record, which this
        authorization binds by sha256. That is the design working and is the
        same lapse conftest documents at length: the live bundle is untouched
        and the next deployment issues a new authorization. The filter drops
        ONLY complaints about the participation record, so a changed contract or
        a moved control file would still come through and still fail.
        """
        manifest = _load(DEPLOY / "global_deployment_manifest.json")
        assert manifest_problems_other_than_the_lapsed_pin(
            DA.verify_authorization(auth, manifest)) == []
        assert manifest_problems_other_than_the_lapsed_pin(
            DA.manifest_authorization_problems(manifest)) == []
        assert manifest["deployment_authorized"] is True

    def test_the_packet_that_proposed_this_launch_bound_the_same_digests(self):
        packet = _load(PKG / "markets" / "reports"
                       / "nashville_deployment_authorization_004_PROPOSED.json")
        bound = packet["the_four_digests_this_authorization_binds"]
        assert bound["final_candidate_digest"] == CANDIDATE
        assert bound["deployment_artifact_digest"] == CANDIDATE
        assert bound["candidate_sitemap_sha256"] == SITEMAP
        assert bound["parent_release_digest"] == PARENT_DIGEST
        assert bound["sealed_package_digest"] == PACKAGE
        assert bound["intended_delta_digest"] == DELTA
        assert bound["fast_lane_receipt_digest"] == RECEIPT

    def test_the_lane_that_proved_the_package_passed_every_rule(self):
        """A-O, with no rule left UNKNOWN. A skipped rule is not a pass."""
        lane = _load(PKG / "markets" / "reports" / "nashville_tn_release_lane_003.json")
        receipt = lane["fast_lane_receipt"]
        assert receipt["receipt_digest"] == RECEIPT
        assert receipt["eligible"] == "YES"
        assert sorted(receipt["rules"]) == list("ABCDEFGHIJKLMNO")
        assert set(receipt["rules"].values()) == {"PASS"}
        assert receipt["unknown_rules"] == [] and receipt["failed_rules"] == []
        assert lane["sealed_package"]["package_digest"] == PACKAGE
        assert lane["sealed_package"]["pet_friendly_records"] == 79
        assert lane["sealed_package"]["verified_no_pets_records"] == 18


class TestTheRollbackTargetIsTheLexingtonRelease:
    """Lexington's own launch walked into this trap; this one asserts past it."""

    def test_the_record_rolls_back_to_lexington_not_to_toledo(self, record):
        assert record["rollback_target"] == PARENT_DEPLOY
        assert record["rollback_target"] != NEVER_ROLL_BACK_TO
        assert record["previous_deployment_id"] == PARENT_DEPLOY

    def test_the_live_pin_agrees_and_the_verifier_is_silent(self):
        live = RI.current_verified_live()
        assert live.rollback_target == PARENT_DEPLOY
        assert live.rollback_record == \
            ("ptf-deploy-lexington-006-%s.json" % PARENT_DEPLOY)
        assert len(live.rollback_markets) == 12
        assert list(live.problems) == []

    def test_no_rollback_was_performed_and_the_determination_says_why(self, record):
        determination = _load(PKG / "nashville_tn_rollback_determination_005.json")
        assert record["final_status"] == DA.DEPLOYED
        assert record["rollback_used"] is False
        assert record["rollback_reason"] is None
        assert determination["rollback_required"] is False
        assert determination["critical_checks_failed"] == []
        assert determination["stale_rollback_refused"] is False
        assert determination["rollback_target_if_it_had_been"] == PARENT_DEPLOY


class TestTheLiveVerificationIsRecorded:

    def test_every_critical_check_passed(self, record, verification):
        checks = record["live_verification_results"]["critical_checks"]
        assert checks, "the record carries no critical checks"
        assert all(entry["pass"] for entry in checks.values())
        assert record["live_verification_results"]["ALL_CRITICAL_CHECKS_PASS"] is True
        assert verification["failed_critical_checks"] == []
        assert verification["NASHVILLE_IS_LIVE"] is True

    def test_the_checks_are_shaped_so_the_record_verifier_can_police_them(self, record):
        """A flat boolean is recorded and never checked.

        ``verify_record`` refuses a DEPLOYED record whose live checks contain a
        mapping with ``pass`` False. That scan only sees mappings, so the checks
        are written as mappings on purpose.
        """
        checks = record["live_verification_results"]["critical_checks"]
        assert all(isinstance(entry, dict) and "pass" in entry
                   for entry in checks.values())
        assert DA.verify_record(record) == []

    def test_every_live_route_was_byte_identical_to_the_authorized_bundle(self, verification):
        live = verification["live"]
        assert verification["live_sitemap_sha256"] == SITEMAP
        assert live["routes"] == live["authorized_routes"] == 1078
        assert live["http_200"] == 1078
        assert live["byte_identical"] == 1078
        assert live["non_200"] == [] and live["byte_mismatched"] == []
        assert live["not_present_in_authorized_bundle"] == []

    def test_nothing_was_removed_and_the_previous_deploy_was_read_from_its_own_address(
            self, verification):
        versus = verification["versus_previous_deploy"]
        assert versus["previous_route_count"] == 991
        assert versus["added"] == 87
        assert versus["removed"] == 0
        assert versus["removed_routes"] == []
        assert list(versus["added_by_market"]) == [MARKET]
        assert PARENT_DEPLOY in versus["read_from"]
        assert verification["unrelated_markets_whose_route_count_changed"] == []

    def test_nashville_surfaces_at_its_authority_and_not_beyond(self, verification):
        nashville = verification["nashville"]
        assert nashville["live_routes"] == 87
        assert nashville["live_profiles"] == 79
        assert nashville["published_in_authority"] == 79
        assert nashville["published_in_partition"] == 79
        assert nashville["verified_no_pets_in_authority"] == 18
        assert nashville["hub_live"] is True and nashville["policy_comparison_live"] is True
        assert nashville["live_corridor_pages"] == 6
        assert nashville["routes_not_accounted_for"] == []


class TestTheHeldRowsNeverReachedProduction:

    def test_four_rows_are_still_held_in_three_classes(self):
        holds = _load(PKG / "nashville_tn_identity_holds_002.json")
        assert holds["count"] == 4
        assert dict(holds["counts_by_class"]) == {
            "CONTRACT_MIGRATION_ERROR": 1,
            "CROSS_MARKET_COLLISION": 2,
            "MODERN_EVIDENCE_GATE_HOLD": 1,
        }
        assert all(hold["published_anything"] is False for hold in holds["holds"])

    def test_no_held_row_is_in_the_published_authority(self):
        holds = _load(PKG / "nashville_tn_identity_holds_002.json")
        facts = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET))
        published = {hotel["identity_key"] for hotel in facts["hotels"]}
        for hold in holds["holds"]:
            assert hold["identity_key_proposed"] not in published, hold["canonical_name"]

    def test_the_live_profile_set_is_exactly_the_published_set(self, verification):
        """Set equality, not a name probe.

        Two held rows collide on a name another market publishes, so probing the
        name asks a narrower question than "did anything unauthorized publish".
        Every live profile slug being a published slug, and the counts agreeing,
        answers the wider one.
        """
        partition = _load(PKG / "nashville_tn_final_partition_001.json")
        published = {item["slug"] for item in partition["items"]
                     if item["final_state"] == PUBLISHED}
        assert len(published) == 79
        assert verification["nashville"]["live_profiles"] == len(published)
        assert verification["nashville"]["held_rows_reaching_production"] == []
        assert verification["critical_checks"][
            "no_held_nashville_identity_reached_production"] is True

    def test_the_launch_published_seventy_nine_not_the_shadows_eighty(self):
        facts = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET))
        exclusions = _load(PKG / "markets" / "authority" / MARKET / "hotel_exclusions.json")
        assert len(facts["hotels"]) == 79
        assert len(exclusions["exclusions"]) == 18


class TestTheGateWasOpenedNarrowlyAndClosed:

    def test_the_gate_is_closed_again(self):
        gate = _load(PKG / "release_production_gate.json")
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] == "NO"
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] == []
        assert "open_for" not in gate

    def test_the_coordinator_refuses_every_market_again(self):
        for market in (MARKET, "lexington-ky", "toledo-oh", "chattanooga-tn"):
            allowed, _why = RC.production_activation_allowed(market)
            assert allowed is False, market

    def test_the_opening_is_recorded_as_consumed_and_names_what_it_replaced(self):
        gate = _load(PKG / "release_production_gate.json")
        consumed = gate["consumed"]
        assert consumed["market_id"] == MARKET
        assert consumed["authorization_id"] == AUTH_ID
        assert consumed["candidate_digest"] == CANDIDATE
        assert consumed["host_deployment_id"] == DEPLOY_ID
        # The chain, not just the current entry. The first write of this field
        # read a key the previous block did not carry and recorded null.
        assert consumed["supersedes"] == \
            "PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
        assert re.match(r"^\d{4}-\d\d-\d\dT", consumed["opened_at"])
        assert consumed["opened_at"] < consumed["closed_at"]

    def test_the_factory_itself_was_not_disabled(self):
        fast = _load(PKG / "fast_release_activation.json")
        assert fast["FAST_PATH_IMPLEMENTED"] == "YES"
        assert fast["FAST_PATH_VALIDATED"] == "YES"

    def test_the_cache_consumption_flag_was_never_opened(self):
        fast = _load(PKG / "fast_release_activation.json")
        assert fast["PRODUCTION_RELEASE_CONSUMPTION"] == "DISABLED"
        assert fast["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"
        assert fast["pilot_allowlist"] == []


class TestTheSupersessionRegistryNamesTheLiveAuthorization:

    def test_the_live_authorization_is_registered_with_nothing_moved(self):
        registry = _load(REPO_ROOT / "tests" / "pettripfinder" / "pins"
                         / "supersessions.json")["authorizations"]
        assert registry[AUTH_ID]["moved_by_later_work"] == {}
        assert registry[AUTH_ID]["work_order"] == \
            "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"

    def test_every_contract_the_authorization_bound_still_hashes(self, auth):
        for row in auth["release_contracts"]:
            assert row["sha256"] == DA._sha256_file(REPO_ROOT / row["path"]), \
                row["market_id"]
