"""PTF-LEXINGTON-KY-FRESH-PACKAGE-REAUTHORIZATION-PREP-005 -- the fresh packet.

The 004 launch halted because a sealed package digest could not be reproduced.
This order replaces it with one that can, and these tests hold the replacement
to the two things that make it worth having:

    1  the fresh package really is reproducible -- proved by re-deriving it,
       not by a field that says so
    2  the dead 004 digest is retired, not aliased

Plus the standing invariant: nothing is authorized, activated or deployed.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

import pytest

from pettripfinder import epochs

from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import market_package_writer as W
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
DEPLOY = REPO_ROOT / "deploy" / "netlify"
MARKET_ID = "lexington-ky"

FRESH_PACKAGE_DIGEST = \
    "sha256:a29e4a966e1b68b918c1b0f34db21ff5525691fc5e7581fb58190cc1031310b0"
SUPERSEDED_DIGEST = \
    "sha256:e5d26fd63bb2d2e2d3d632134cc40cd832d1a4d4c5e1b82f003aa58dc52c5380"
CANDIDATE_DIGEST = "67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78"
SITEMAP_DIGEST = "dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611"
PARENT_DEPLOY = "6a9e047690ec8bdaf99bcad2"
PARENT_DIGEST = "895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _inputs_pinned_to(package, lane):
    """Package inputs for a re-derivation, pinned to the commit the package names."""
    live = RI.live_index()
    inputs = W.inputs_from_committed_market(
        MARKET_ID, execution_zone=SMP.ZONE_REGISTERED_LIVE,
        intended_delta=OrderedDict((("market_id", MARKET_ID),)),
        parent_live_state=lane.parent_from_live(live),
        source_sha=package["created_from_source_sha"])
    inputs.intended_delta = lane.joining_delta(inputs)
    return inputs


@pytest.fixture(scope="module")
def packet():
    return _load(REPORTS / "lexington_deployment_authorization_006_PROPOSED.json")


@pytest.fixture(scope="module")
def package():
    return SMP.read_sealed(SMP.list_packages(MARKET_ID)[-1])


class TestTheFreshPackageIsReproducible:

    def test_the_committed_package_is_the_fresh_digest(self, package):
        assert package["package_digest"] == FRESH_PACKAGE_DIGEST
        assert package["package_digest"] != SUPERSEDED_DIGEST

    def test_the_seal_recomputes_over_its_own_committed_body(self, package):
        body = OrderedDict((k, v) for k, v in package.items() if k not in SMP.SEAL_FIELDS)
        assert SMP.sha256_text(SMP.canonical_json(body)) == package["package_digest"]
        assert SMP.validate(package) == ()

    def test_re_derivation_is_epoch_bound_and_the_seal_is_not(self, package):
        """The distinction the 004 halt was really about, now demonstrated.

        When this package was sealed, re-deriving it from the committed tree --
        pinned to the commit ``created_from_source_sha`` names -- reproduced the
        digest exactly with a byte-identical body. That was true while the
        Toledo release was still live.

        PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 shipped
        this package, so live moved. A sealed package embeds
        ``parent_live_state``, and a re-derivation today reads the NEW parent, so
        the bodies no longer match. Re-derivation is therefore EPOCH-BOUND: it
        holds only while the parent the package names is still live.

        The seal is not. It recomputes over the package's OWN committed body
        forever, which is precisely why committing the package was the right
        answer to the halt and re-deriving it was not. This test asserts both
        halves rather than skipping, because the contrast IS the lesson.
        """
        import scripts.pettripfinder.lexington_ky_release_lane_003 as L

        # Permanent: the seal recomputes over its own body.
        body = OrderedDict((k, v) for k, v in package.items() if k not in SMP.SEAL_FIELDS)
        assert SMP.sha256_text(SMP.canonical_json(body)) == package["package_digest"]

        # Epoch-bound: the package names the parent it was sealed against, and
        # that parent is no longer live.
        live = RI.current_verified_live()
        sealed_parent = package["parent_live_state"]["live_deploy_id"]
        assert sealed_parent == PARENT_DEPLOY
        assert live.deploy_id != sealed_parent, (
            "while the sealed parent is still live, re-derivation must still reproduce "
            "the digest; this assertion is the trigger to restore the full re-derivation "
            "check rather than to weaken it")

        # And the re-derivation now differs for exactly that reason: the parent.
        rebuilt = W.build_sealed_package(
            _inputs_pinned_to(package, L), sealed_at=L.SEALED_AT)
        assert rebuilt["package_digest"] != package["package_digest"]
        assert rebuilt["parent_live_state"]["live_deploy_id"] == live.deploy_id
        without_parent = lambda d: OrderedDict(  # noqa: E731
            (k, v) for k, v in d.items()
            if k not in SMP.SEAL_FIELDS and k != "parent_live_state")
        assert SMP.canonical_json(without_parent(rebuilt)) ==             SMP.canonical_json(without_parent(package)),             "only the parent may differ; anything else means the MARKET moved"

    def test_the_package_describes_the_committed_authority(self, package):
        policy = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET_ID))
        exclusions = _load(PKG / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json")
        census = _load(PKG / "identity_census" / ("%s.json" % MARKET_ID))
        assert len(package["pet_friendly_records"]) == len(policy["hotels"]) == 20
        assert len(package["verified_no_pets_records"]) == len(exclusions["exclusions"]) == 10
        assert package["census"]["count"] == census["count"] == 57
        assert package["parent_live_state"]["live_deploy_id"] == PARENT_DEPLOY


class TestTheDeadDigestIsRetiredNotAliased:

    def test_the_packet_names_the_old_digest_only_as_superseded(self, packet):
        assert packet["supersedes"]["sealed_package_digest"] == SUPERSEDED_DIGEST
        assert packet["supersedes"]["valid_for_the_fresh_package"] is False
        bound = packet["the_digests_this_authorization_binds"]
        assert bound["sealed_package_digest"] == FRESH_PACKAGE_DIGEST
        assert SUPERSEDED_DIGEST not in bound.values()

    def test_the_old_proposal_is_not_presented_as_current(self):
        old = _load(REPORTS / "lexington_deployment_authorization_004_PROPOSED.json")
        assert old["the_four_digests_this_authorization_binds"]["sealed_package_digest"] == \
            SUPERSEDED_DIGEST
        halt = _load(REPORTS / "lexington_reauthorization_005_REQUIRED.json")
        assert halt["status"] == "HALTED_AWAITING_FRESH_FOUNDER_AUTHORIZATION"


class TestTheFreshPacket:

    def test_it_binds_every_digest_the_order_asked_for(self, packet, package):
        bound = packet["the_digests_this_authorization_binds"]
        assert bound["parent_release_digest"] == PARENT_DIGEST
        assert bound["sealed_package_digest"] == package["package_digest"]
        assert bound["final_candidate_digest"] == CANDIDATE_DIGEST
        assert bound["deployment_artifact_digest"] == CANDIDATE_DIGEST
        assert bound["candidate_sitemap_digest"] == SITEMAP_DIGEST
        for key in ("build_input_key", "intended_delta_digest", "fast_lane_receipt_digest"):
            assert bound[key].startswith("sha256:") and len(bound[key]) == 71, key

    def test_the_delta_is_exactly_one_market_twenty_profiles_twenty_five_routes(self, packet):
        d = packet["release_delta"]
        assert (d["parent_market_count"], d["parent_profile_count"],
                d["parent_route_count"]) == (11, 803, 966)
        assert (d["candidate_market_count"], d["candidate_profile_count"],
                d["candidate_route_count"]) == (12, 823, 991)
        assert d["profile_delta"] == 20 and d["route_delta"] == 25
        assert d["markets_added"] == [MARKET_ID]
        assert d["markets_updated"] == [] and d["markets_removed"] == []
        assert d["unexpected_market_changes"] == 0
        assert d["unexpected_profile_changes"] == 0
        assert d["unexpected_route_changes"] == 0
        assert d["forbidden_markets_present"] == []

    def test_the_validation_was_narrow_and_says_why(self, packet):
        v = packet["validation"]
        assert v["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES
        assert all(status == FL.PASS for status in v["rules"].values())
        assert len(v["rules"]) == 15
        assert v["unknown_rules"] == [] and v["failed_rules"] == []
        assert v["FULL_REGRESSION_REQUIRED"] == "NO"
        assert v["REMOTE_BROAD_JOBS_REQUIRED"] == 0
        assert v["broad_run_reran"] is False
        assert v["integration_audit"]["TRUE_NEW_FAILURE_AFTER_CLOSURE"] == 0
        assert v["integration_audit"]["rerun_by_this_order"] is False
        # The reason a broad run was not rerun is recorded, not implied.
        assert "reverse-import scan" in v["why_no_broad_run"]

    def test_the_packet_does_not_claim_to_be_byte_stable(self, packet):
        """It records the moment it was written, and says so.

        Three fields move on every regeneration -- the assembly commit, git HEAD
        and the uncommitted list. What it BINDS does not move, and that is the
        property an authorization needs. Saying this out loud is what stops a
        later reader from mistaking a changed report for a changed candidate.
        """
        note = packet["git"]["note"]
        assert "not byte-stable" in note
        assert isinstance(packet["git"]["uncommitted_at_generation"], list)

    def test_the_candidate_is_reproducible_and_the_packet_says_how_often(self, packet):
        r = packet["candidate_reproducibility"]
        # Bumped to 5 when PTF-LEXINGTON-KY-FRESH-PACKAGE-REAUTHORIZATION-PREP-005
        # was re-issued and the candidate was assembled once more, at 6b5fa73.
        # The count is a parameter of the writer now, so it cannot drift from
        # what actually ran.
        assert r["independent_assemblies"] == 5
        assert r["all_byte_identical"] is True
        assert r["digest"] == CANDIDATE_DIGEST

    def test_the_holds_are_carried_forward_untouched(self, packet):
        holds = _load(PKG / "lexington_ky_identity_holds_003.json")
        assert packet["lexington"]["held_rows"] == holds["count"] == 15
        assert len(packet["held_rows"]) == 15
        assert dict(packet["lexington"]["held_by_class"]) == {
            "CROSS_MARKET_IDENTITY_COLLISION": 1,
            "IDENTITY_HOLD": 3,
            "MODERN_EVIDENCE_GATE_HOLD": 5,
            "PAID_PROVENANCE_HOLD": 6,
        }

    def test_the_rollback_target_is_the_current_parent_not_the_one_it_replaced(self, packet):
        r = packet["rollback"]
        assert r["target_deployment_id"] == PARENT_DEPLOY
        assert r["target_release_digest"] == PARENT_DIGEST
        assert r["target_is_current_verified_parent"] is True
        assert r["never_roll_back_to"] != PARENT_DEPLOY

    def test_every_deployment_ready_gate_derives_true(self, packet):
        assert packet["DEPLOYMENT_READY"] == "YES"
        assert all(packet["deployment_ready_gates"].values())


class TestNothingIsAuthorizedActivatedOrDeployed:

    def test_the_packet_is_unsigned(self, packet):
        assert packet["status"] == "AWAITING_FOUNDER_AUTHORIZATION"
        assert packet["authorized_by"] is None and packet["authorized_at"] is None
        assert packet["nothing_authorized"] is True
        assert packet["nothing_activated"] is True
        assert packet["nothing_deployed"] is True

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='the re-authorization prep created no authorization. The launch that consumed its packet created ptf-auth-lexington-006-67fe8617b79f.')
    def test_no_authorization_file_exists_for_lexington(self):
        for path in (DEPLOY / "deployment_authorizations").glob("*.json"):
            assert MARKET_ID not in path.name
            assert MARKET_ID not in _load(path).get("participating_markets", [])

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='the prep left participation withheld. The launch flipped it.')
    def test_participation_is_still_withheld(self):
        assert LP.launch_status(MARKET_ID) == \
            "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"
        doc = _load(DEPLOY / "launch_participation.json")
        assert doc["decision"]["work_order"] == \
            "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"
        authorized = [m["market_id"] for m in doc["markets"]
                      if m["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"]
        assert MARKET_ID not in authorized and len(authorized) == 11

    def test_both_production_gates_are_still_closed(self):
        fast = _load(PKG / "fast_release_activation.json")
        gate = _load(PKG / "release_production_gate.json")
        assert fast["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"
        assert fast["PRODUCTION_RELEASE_CONSUMPTION"] == "DISABLED"
        assert fast["pilot_allowlist"] == []
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] == "NO"
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] == []

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='the prep left production on the Toledo release at 11 / 803 / 966. The launch moved it to 12 / 823 / 991.')
    def test_live_production_is_unchanged(self):
        live = RI.current_verified_live()
        assert live.deploy_id == PARENT_DEPLOY
        assert live.bundle_sha256 == PARENT_DIGEST
        assert (len(live.participating_markets), live.total_profiles,
                live.sitemap_route_count) == (11, 803, 966)
        assert "toledo-oh" in live.participating_markets
        assert MARKET_ID not in live.participating_markets
