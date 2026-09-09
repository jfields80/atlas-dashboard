"""PTF-LEXINGTON-KY-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-004 -- the halt.

A founder authorized a launch and named seven digests. Six verified exactly and
one did not, and the founder ruled STOP rather than proceed on six of seven.
These tests hold the two halves of that outcome:

    1  nothing was authorized, activated or deployed
    2  the reason the seventh digest failed is recorded truthfully -- it is a
       property of the machine that sealed the package, not of the market, and
       the market's own content is proved unmoved rather than asserted

The second half matters more than it looks. "The content did not change" is the
kind of claim that is easy to make and hard to check, so it is checked here
against the committed authority rather than against a report that says so.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder import epochs

from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
DEPLOY = REPO_ROOT / "deploy" / "netlify"
MARKET_ID = "lexington-ky"

#: The digest the founder named in 004. It is kept here BY NAME so a later order
#: cannot quietly decide the halt never happened.
AUTHORIZED_004_PACKAGE_DIGEST = \
    "sha256:e5d26fd63bb2d2e2d3d632134cc40cd832d1a4d4c5e1b82f003aa58dc52c5380"
AUTHORIZED_004_CANDIDATE_DIGEST = \
    "67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78"
PARENT_DEPLOY = "6a9e047690ec8bdaf99bcad2"
PARENT_DIGEST = "895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def report():
    return _load(REPORTS / "lexington_reauthorization_005_REQUIRED.json")


@pytest.fixture(scope="module")
def package():
    paths = SMP.list_packages(MARKET_ID)
    assert paths, "this order commits Lexington's sealed package under its market"
    return SMP.read_sealed(paths[-1])


class TestNothingHappened:
    """The whole point of a halt."""

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='the HALT left no Lexington authorization. The later launch created one against the FRESH reproducible package, which is exactly the remedy the halt demanded.')
    def test_no_deployment_authorization_exists_for_lexington(self):
        for path in (DEPLOY / "deployment_authorizations").glob("*.json"):
            assert MARKET_ID not in path.name
            assert MARKET_ID not in _load(path).get("participating_markets", [])

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='the HALT left participation withheld. The later launch flipped it on a fresh founder decision bound to the reproducible package.')
    def test_lexington_participation_is_still_withheld(self):
        assert LP.launch_status(MARKET_ID) == \
            "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='the HALT left the Toledo decision standing. The later launch replaced it and carries Toledo in the lineage.')
    def test_the_founder_decision_block_still_names_toledo(self):
        doc = _load(DEPLOY / "launch_participation.json")
        assert doc["decision"]["work_order"] == \
            "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"
        authorized = [m["market_id"] for m in doc["markets"]
                      if m["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"]
        assert MARKET_ID not in authorized
        assert len(authorized) == 11

    def test_the_production_activation_flags_are_untouched(self):
        fast = _load(PKG / "fast_release_activation.json")
        gate = _load(PKG / "release_production_gate.json")
        assert fast["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"
        assert fast["PRODUCTION_RELEASE_CONSUMPTION"] == "DISABLED"
        assert fast["pilot_allowlist"] == []
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] == "NO"
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] == []

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='the HALT deployed nothing. The later launch deployed 6aa172121d37bb4013eb44a4 and wrote its record.')
    def test_no_deployment_record_names_lexington(self):
        for path in (DEPLOY / "deployment_records").glob("*.json"):
            record = _load(path)
            assert MARKET_ID not in record.get("participating_markets", []), path.name

    @epochs.superseded(by='PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006',
                       what='the HALT left production on the Toledo release. The later launch published Lexington as the twelfth market; the Toledo release is now the ROLLBACK TARGET, which is the fact this assertion becomes.')
    def test_live_production_is_still_the_toledo_release(self):
        live = RI.current_verified_live()
        assert live.deploy_id == PARENT_DEPLOY
        assert live.bundle_sha256 == PARENT_DIGEST
        assert len(live.participating_markets) == 11
        assert live.total_profiles == 803
        assert live.sitemap_route_count == 966
        assert "toledo-oh" in live.participating_markets
        assert MARKET_ID not in live.participating_markets

    def test_the_report_says_halted_and_names_no_authorizer(self, report):
        assert report["status"] == "HALTED_AWAITING_FRESH_FOUNDER_AUTHORIZATION"
        assert report["authorized_by"] is None
        assert report["authorized_at"] is None
        assert report["nothing_authorized"] is True
        assert report["nothing_activated"] is True
        assert report["nothing_deployed"] is True


class TestTheHaltIsRecordedTruthfully:

    def test_exactly_one_authorized_value_failed_and_it_is_named(self, report):
        assert report["verification_failed_on"] == ["sealed_package_digest"]
        checks = report["verification_of_those_values"]
        assert checks["sealed_package_digest"] is False
        # Everything else the founder named held, and each is asserted, not summarised.
        for key in ("parent_deployment", "parent_release_digest", "parent_counts_11_803_966",
                    "toledo_present", "final_candidate_digest", "deployment_artifact_digest",
                    "candidate_sitemap_digest", "intended_delta_digest"):
            assert checks[key] is True, key

    def test_the_committed_package_is_not_the_digest_that_was_authorized(self, package):
        assert package["package_digest"] != AUTHORIZED_004_PACKAGE_DIGEST

    def test_the_committed_package_seal_re_validates_against_its_own_body(self, package):
        """The reason a committed package removes the drift: it is READ."""
        path = SMP.list_packages(MARKET_ID)[-1]
        assert path.name == "%s.json" % package["package_id"]
        again = SMP.read_sealed(path)
        assert again["package_digest"] == package["package_digest"]
        assert SMP.validate(again) == ()

    def test_the_content_the_digest_describes_did_not_move(self, package):
        """Checked against the committed authority, not against a claim."""
        policy = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET_ID))
        exclusions = _load(PKG / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json")
        census = _load(PKG / "identity_census" / ("%s.json" % MARKET_ID))
        assert len(package["pet_friendly_records"]) == len(policy["hotels"]) == 20
        assert len(package["verified_no_pets_records"]) == len(exclusions["exclusions"]) == 10
        assert package["census"]["count"] == census["count"] == 57
        assert [r["identity_key"] for r in package["pet_friendly_records"]] == \
            [h["key"] for h in policy["hotels"]]

    def test_the_intended_delta_digest_is_the_one_the_founder_authorized(self, report):
        fresh = report["the_fresh_values_to_authorize"]["intended_delta_digest"]
        assert fresh == report["what_the_founder_authorized_in_004"]["intended_delta_digest"]

    def test_the_candidate_digest_is_stable_across_three_assemblies(self, report):
        stability = report["candidate_digest_stability"]
        assert stability["independent_assemblies"] == 3
        assert stability["all_byte_identical"] is True
        assert stability["digest"] == AUTHORIZED_004_CANDIDATE_DIGEST

    def test_both_causes_are_named_and_neither_is_about_lexington(self, report):
        why = report["why_the_sealed_package_digest_did_not_reproduce"]
        assert why["cause_1_created_from_source_sha"]["sealed_at_commit"].startswith("fa08b22")
        assert "seed_businesses.csv" in why["cause_2_raw_byte_dependency_digests"]["file"]
        proof = why["proof_the_content_did_not_move"]
        assert proof["reproducing_both_conditions_recovers_the_authorized_digest"] is True
        assert proof["authority_documents_reproduce_byte_for_byte"] == 6
        assert (proof["census"], proof["published_pet_friendly"],
                proof["verified_no_pets"], proof["held_rows"]) == (57, 20, 10, 15)

    def test_the_writer_defect_is_left_for_a_later_order(self, report):
        why = report["why_the_sealed_package_digest_did_not_reproduce"]
        assert "NOT done here" in why["remedy_for_a_later_order"]
        # And it really was left: the writer still hashes raw bytes.
        from scripts.pettripfinder import market_package_writer as W
        source = Path(W.__file__).read_text(encoding="utf-8")
        collapsed = " ".join(source.split())
        assert "digests = OrderedDict((k, SMP.sha256_bytes(p.read_bytes()))" in collapsed


class TestTheValidationCarriedForward:

    @pytest.fixture(scope="class")
    def receipt(self):
        package = SMP.read_sealed(SMP.list_packages(MARKET_ID)[-1])
        paths = FL.eligible_receipts(MARKET_ID, package["package_digest"])
        assert paths, "a receipt is committed for the exact committed package"
        return _load(paths[-1])

    def test_the_receipt_is_for_the_committed_package_and_passes_every_rule(self, receipt,
                                                                           package):
        assert receipt["PACKAGE_DIGEST"] == package["package_digest"]
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES
        assert receipt["UNKNOWN_RULES"] == [] and receipt["FAILED_RULES"] == []
        assert set(receipt["RESULTS"]) == set("ABCDEFGHIJKLMNO")
        assert all(r["status"] == FL.PASS for r in receipt["RESULTS"].values())
        assert receipt["DETERMINISM_RESULT"] == "BYTE_IDENTICAL"

    def test_the_receipt_still_refuses_production_activation(self, receipt):
        assert receipt["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"
        assert receipt["PRODUCTION_ACTIVATION_ALLOWED"] == FL.NO

    def test_the_receipt_names_the_current_live_parent(self, receipt):
        assert receipt["PARENT_RELEASE"]["live_deploy_id"] == PARENT_DEPLOY

    def test_the_holds_are_untouched_and_none_was_promoted(self, report):
        holds = _load(PKG / "lexington_ky_identity_holds_003.json")
        assert holds["count"] == 15
        assert report["holds_untouched"]["count"] == 15
        assert report["holds_untouched"]["any_promoted"] is False
        assert dict(holds["counts_by_class"]) == {
            "CROSS_MARKET_IDENTITY_COLLISION": 1,
            "IDENTITY_HOLD": 3,
            "MODERN_EVIDENCE_GATE_HOLD": 5,
            "PAID_PROVENANCE_HOLD": 6,
        }
