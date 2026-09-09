# -*- coding: utf-8 -*-
"""ATLAS-THROUGHPUT-003 -- the sealed market package contract, the typed
writer, the first-party evidence gate, the whole-release index, the intended
delta guard, the determinism gate, the validation receipt, the Regression V2
extension and the production-activation boundary.

Every adversarial case below mutates the REAL Dayton authority (this tree,
read only) exactly as the pilot sealed it, or a real live-release index, so a
FAIL is the gate catching a concrete defect fixture and never a synthetic
shape the gate was written to recognise. Nothing here edits committed
authority, promotes a market, deploys, or makes a paid provider call.

Case numbers follow the order's Phase 14 matrix (1-25).
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from collections import OrderedDict
from pathlib import Path

import pytest

from pettripfinder import market_state as MS
from scripts.pettripfinder import atlas_throughput_003_pilot as PILOT
from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import first_party_binding as FPB
from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import market_local_ownership as OWN
from scripts.pettripfinder import market_package_writer as W
from scripts.pettripfinder import package_staging as STAGING
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP
from scripts.pettripfinder.acquisition.paid_attempt_ledger import attempt_id as paid_attempt_id

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "reports"
SEALED_AT = "2026-09-08T00:00:00Z"
VALIDATED_AT = FPB.parse_timestamp("2026-09-08T12:00:00Z")


def _clone(inputs: W.PackageInputs) -> W.PackageInputs:
    return copy.deepcopy(inputs)


def _writer_codes(inputs: W.PackageInputs):
    try:
        W.build_sealed_package(inputs, sealed_at=SEALED_AT)
    except W.PackageWriteError as exc:
        return exc.codes()
    return ()


@pytest.fixture(scope="module")
def live():
    return RI.live_index()


@pytest.fixture(scope="module")
def dayton_inputs(live):
    return PILOT.frozen_inputs("dayton-oh", live)


@pytest.fixture(scope="module")
def dayton_package(dayton_inputs):
    return W.build_sealed_package(dayton_inputs, sealed_at=SEALED_AT)


@pytest.fixture(scope="module")
def corrected_inputs(live):
    return PILOT.withdrawal_inputs(live)


@pytest.fixture(scope="module")
def corrected_package(corrected_inputs):
    return W.build_sealed_package(corrected_inputs, sealed_at=SEALED_AT)


def _lane(package, live, tmp, **kw):
    kw.setdefault("build", False)
    kw.setdefault("determinism", False)
    kw.setdefault("now", VALIDATED_AT)
    return FL.run_fast_lane(package, work_dir=tmp, live=live, **kw)


# --------------------------------------------------------------------------- #
# The sealed package contract.
# --------------------------------------------------------------------------- #

class TestSealedPackageContract:
    def test_the_package_carries_every_field_the_order_names(self, dayton_package):
        for field in SMP.BODY_FIELDS + SMP.SEAL_FIELDS:
            assert field in dayton_package, field
        assert dayton_package["schema"] == SMP.SCHEMA
        assert dayton_package["validation_state"] == SMP.VALIDATION_STATE_SEALED
        assert not SMP.validate(dayton_package)

    def test_the_digest_re_derives_and_the_id_derives_from_the_digest(self, dayton_package):
        assert SMP.digest_of(dayton_package) == dayton_package["package_digest"]
        assert dayton_package["package_id"] == SMP.package_id_for("dayton-oh", dayton_package["package_digest"])

    def test_the_writer_is_deterministic_and_the_seal_time_is_outside_the_digest(self, dayton_inputs):
        a = W.build_sealed_package(dayton_inputs, sealed_at="2026-09-08T00:00:00Z")
        b = W.build_sealed_package(dayton_inputs, sealed_at="2026-09-09T00:00:00Z")
        assert a["package_digest"] == b["package_digest"] and a["package_id"] == b["package_id"]
        assert a["sealed_at"] != b["sealed_at"]

    def test_a_sealed_package_is_never_rewritten_in_place(self, dayton_package, tmp_path):
        path = SMP.write_sealed(dayton_package, tmp_path)
        assert path.name == dayton_package["package_id"] + ".json"
        assert SMP.write_sealed(dayton_package, tmp_path) == path        # byte-identical re-write is a no-op
        tampered = copy.deepcopy(dayton_package)
        tampered["sealed_at"] = "2026-09-09T00:00:00Z"                  # same id, different bytes
        with pytest.raises(SMP.PackageContractError, match="never rewritten"):
            SMP.write_sealed(tampered, tmp_path)
        assert SMP.read_sealed(path)["package_digest"] == dayton_package["package_digest"]

    def test_case_18_a_malformed_or_tampered_digest_fails(self, dayton_package, live, tmp_path):
        bad = copy.deepcopy(dayton_package)
        bad["package_digest"] = "sha256:" + "0" * 64
        issues = SMP.validate(bad)
        assert any(i.code == "DIGEST_MISMATCH" for i in issues)
        edited = copy.deepcopy(dayton_package)
        edited["pet_friendly_records"][0]["name"] += " (edited after sealing)"
        assert any(i.code == "DIGEST_MISMATCH" for i in SMP.validate(edited))
        receipt = _lane(edited, live, tmp_path)
        assert receipt["RESULTS"]["A"]["status"] == FL.FAIL
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO
        path = tmp_path / "dayton-oh" / (dayton_package["package_id"] + ".json")
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(SMP.PackageContractError):
            SMP.read_sealed(path)

    def test_a_correction_is_a_new_package_identity(self, dayton_package, corrected_package):
        assert corrected_package["package_id"] != dayton_package["package_id"]
        assert corrected_package["package_digest"] != dayton_package["package_digest"]
        assert len(corrected_package["pet_friendly_records"]) == len(dayton_package["pet_friendly_records"]) - 4

    def test_a_removal_without_a_ruling_cannot_even_seal(self, live):
        inputs = PILOT.withdrawal_inputs(live, ruling_ref="", reason="")
        with pytest.raises(W.PackageWriteError) as excinfo:
            W.build_sealed_package(inputs, sealed_at=SEALED_AT)
        assert any(i.path == "intended_delta.removal_authority" for i in excinfo.value.issues)


# --------------------------------------------------------------------------- #
# The typed writer rejects before serialization.
# --------------------------------------------------------------------------- #

class TestTypedWriter:
    def test_case_6_invalid_fee_basis_enum_and_currency(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["pet_fee"]["basis"] = "per_week"
        assert "POLICY_BAD_ENUM" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["pet_fee"].pop("currency")
        assert "POLICY_MISSING_CURRENCY" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["pet_fee"]["amount_cents"] = 50.0
        assert "POLICY_NOT_INT_CENTS" in _writer_codes(inputs)

    def test_invalid_pet_count_and_weight_structures(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["pet_count_limit"] = "two"
        assert "POLICY_BAD_COUNT" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["weight_limit"] = {"value": "25 lbs"}
        codes = _writer_codes(inputs)
        assert any(c.startswith("POLICY_") for c in codes), codes

    def test_fee_deposit_conflation(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["pet_fee"]["refundable"] = True
        assert "FEE_DEPOSIT_CONFLATION" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["pet_deposit"] = 15000
        assert "FEE_DEPOSIT_CONFLATION" in _writer_codes(inputs)

    def test_missing_identity_and_invalid_policy_status(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["identity_key"] = "a hotel the census never admitted"
        assert "MISSING_IDENTITY" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["verification_state"] = "HOLD_POLICY_NOT_VERIFIED"
        assert "INVALID_POLICY_STATUS" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["pets_allowed"] = False
        assert "INVALID_POLICY_STATUS" in _writer_codes(inputs)

    def test_case_19_evidence_hash_mismatch_and_missing_binding(self, dayton_inputs, dayton_package, live, tmp_path):
        # Against the capture manifest (the reference table the run produced),
        # a record whose hash names no captured page is unbound.
        inputs = _clone(dayton_inputs)
        inputs.evidence_references = copy.deepcopy(dayton_package["evidence_references"])
        inputs.pet_friendly_records[0]["evidence"][0]["artifact_sha256"] = "sha256:" + "a" * 64
        assert "MISSING_EVIDENCE_BINDING" in _writer_codes(inputs)
        assert dayton_package["coverage_scorecard"]["evidence_references_source"] == "derived_from_records"
        # An artifact the package says is available must hash to its reference.
        package = copy.deepcopy(dayton_package)
        ref = package["evidence_references"][0]
        artifact = tmp_path / "artifact.html"
        artifact.write_text("<html>not the captured page</html>", encoding="utf-8")
        ref["artifact_available"] = True
        ref["artifact_path"] = str(artifact)
        package = SMP.seal(SMP.body_of(package), sealed_at=SEALED_AT)
        receipt = _lane(package, live, tmp_path / "lane")
        assert receipt["RESULTS"]["L"]["status"] == FL.FAIL
        assert any("bytes hash to" in p for p in receipt["RESULTS"]["L"]["problems"])

    def test_policy_evidence_identity_mismatch(self, dayton_inputs, dayton_package):
        # One captured page is one property's page: two identities citing one
        # artifact is a wrong-property binding, with or without a manifest.
        inputs = _clone(dayton_inputs)
        a, b = inputs.pet_friendly_records[0], inputs.pet_friendly_records[1]
        a["evidence"][0]["artifact_sha256"] = b["evidence"][0]["artifact_sha256"]
        a["evidence"][0]["source_url"] = b["evidence"][0]["source_url"]
        assert "POLICY_EVIDENCE_IDENTITY_MISMATCH" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.evidence_references = copy.deepcopy(dayton_package["evidence_references"])
        a, b = inputs.pet_friendly_records[0], inputs.pet_friendly_records[1]
        a["evidence"][0]["artifact_sha256"] = b["evidence"][0]["artifact_sha256"]
        a["evidence"][0]["source_url"] = b["evidence"][0]["source_url"]
        assert "POLICY_EVIDENCE_IDENTITY_MISMATCH" in _writer_codes(inputs)

    def test_case_14_invalid_market_assignment_and_wrong_market_route(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["market_id"] = "indianapolis-in"
        assert "INVALID_MARKET_ASSIGNMENT" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["corridor"] = "indianapolis-in__downtown"
        assert "INVALID_MARKET_ASSIGNMENT" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["source_url"] = "https://www.booking.com/hotel/us/ac-hotel-dayton.html"
        assert "INVALID_ROUTE" in _writer_codes(inputs)

    def test_case_7_orphaned_partition(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        partition = json.loads(json.dumps(inputs.partition))
        partition["items"] = partition["items"][1:]
        inputs.partition = partition
        assert "ORPHAN_PARTITION" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        partition = json.loads(json.dumps(inputs.partition))
        partition["items"].append(dict(partition["items"][0], identity_key="a hotel that is not in the census",
                                       canonical_name="A hotel that is not in the census"))
        inputs.partition = partition
        assert "ORPHAN_PARTITION" in _writer_codes(inputs)

    def test_case_20_an_unresolved_row_promoted_clean(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        partition = json.loads(json.dumps(inputs.partition))
        key = inputs.pet_friendly_records[0]["identity_key"]
        for item in partition["items"]:
            if item["identity_key"] == key:
                item.update({"final_state": "AWAITING_POLICY_ARTIFACT", "resolved": False,
                             "next_action": "capture", "next_action_source": "test", "determined_by": "test"})
        inputs.partition = partition
        assert "UNRESOLVED_PROMOTED_CLEAN" in _writer_codes(inputs)

    def test_case_8_duplicate_identity(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records.append(copy.deepcopy(inputs.pet_friendly_records[0]))
        assert "DUPLICATE_IDENTITY" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        census = json.loads(json.dumps(inputs.census))
        census["hotels"].append(copy.deepcopy(census["hotels"][0]))
        census["count"] = len(census["hotels"])
        inputs.census = census
        assert "DUPLICATE_IDENTITY" in _writer_codes(inputs)

    def test_unsupported_enums_and_sentinels(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        inputs.verified_no_pets_records[0]["exclusion_state"] = "PETS_MAYBE"
        inputs.verified_no_pets_records[0]["record_hash"] = HE.record_hash(inputs.verified_no_pets_records[0])
        inputs.verified_no_pets_records[0]["approval_hash"] = HE.approval_hash(inputs.verified_no_pets_records[0])
        assert "EXCLUSION_CONTRACT" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["facts"]["breed_restrictions"] = "N/A"
        assert "POLICY_SENTINEL_FOR_SILENCE" in _writer_codes(inputs)
        inputs = _clone(dayton_inputs)
        census = json.loads(json.dumps(inputs.census))
        census["hotels"][0]["address"] = "unknown"
        inputs.census = census
        assert "SENTINEL_VALUE" in _writer_codes(inputs)

    def test_the_writer_seals_the_committed_dayton_authority_as_is(self, dayton_package):
        card = dayton_package["coverage_scorecard"]
        assert (card["census_count"], card["published_pet_friendly"], card["verified_no_pets"]) == (129, 54, 24)
        assert card["evidence_references"] == 78 and card["paid_evidence_references"] == 0

    def test_the_writer_reports_which_live_markets_do_not_satisfy_the_contracts(self, live):
        """Legacy facts, not failures of the writer: recorded for the report."""
        verdicts = {}
        for market_id in ("cleveland-akron-canton-oh", "pittsburgh-pa", "grand-rapids-holland-mi"):
            inputs = PILOT.frozen_inputs(market_id, live)
            verdicts[market_id] = _writer_codes(inputs)
        # ATLAS-THROUGHPUT-004 corrected 003's over-reading of Cleveland's four
        # ROUTING_RETIRED rows (acquisition history, not dangling references)
        # and accepted the dash-spelled artifact hashes: Cleveland now seals.
        assert verdicts["cleveland-akron-canton-oh"] == ()
        # An ACTIVE route outside the census is still a dangling reference.
        assert "ROUTE_IDENTITY_NOT_IN_CENSUS" in verdicts["grand-rapids-holland-mi"]
        assert "PUBLICATION_BLOCKED" in verdicts["pittsburgh-pa"]


# --------------------------------------------------------------------------- #
# The first-party evidence gate.
# --------------------------------------------------------------------------- #

class TestFirstPartyGate:
    def _record(self, package, index=0):
        record = copy.deepcopy(package["pet_friendly_records"][index])
        identity = next(r for r in package["identity_records"] if r["identity_key"] == record["identity_key"])
        refs = {(r["identity_key"], r["artifact_sha256"]): r for r in package["evidence_references"]}
        return record, identity, refs

    def test_case_2_wrong_hotel_page_bound_to_the_right_record(self, dayton_package):
        record, identity, refs = self._record(dayton_package)
        assert record["source_url"].startswith("https://www.marriott.com/")
        wrong = "https://www.marriott.com/en-us/hotels/cmhac-ac-hotel-columbus-downtown/overview/"
        for entry in record["evidence"]:
            entry["source_url"] = wrong
        verdict = FPB.evaluate_policy_record(record, identity, refs)
        assert not verdict["eligible"] and verdict["classification"] == FPB.CLASS_WRONG_PROPERTY

    def test_same_brand_wrong_property(self, dayton_package):
        record, identity, refs = self._record(dayton_package)
        identity = dict(identity, property_code="dayac")
        record["evidence"][0]["source_url"] = "https://www.marriott.com/en-us/hotels/dayfn-fairfield-dayton-north/overview/"
        verdict = FPB.evaluate_policy_record(record, identity, refs)
        assert verdict["classification"] == FPB.CLASS_WRONG_PROPERTY

    def test_case_3_competitor_only_evidence_is_lead_only(self, dayton_package, dayton_inputs):
        record, identity, refs = self._record(dayton_package)
        for entry in record["evidence"]:
            entry["source_grade"] = "PT3_THIRD_PARTY"
        verdict = FPB.evaluate_policy_record(record, identity, refs)
        assert not verdict["eligible"] and verdict["classification"] == FPB.CLASS_LEAD_ONLY
        inputs = _clone(dayton_inputs)
        for entry in inputs.pet_friendly_records[0]["evidence"]:
            entry["source_grade"] = "PT3_THIRD_PARTY"
        codes = _writer_codes(inputs)
        assert "PUBLICATION_BLOCKED" in codes and "EVIDENCE_NOT_FIRST_PARTY" in codes

    def test_case_4_fee_present_acceptance_absent(self):
        assert FPB.classify_quote("$50 pet fee per night", kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.CLASS_FEE_ONLY
        assert FPB.classify_quote("Maximum 2 pets, 50 lbs each", kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.CLASS_FEE_ONLY

    def test_case_5_service_animals_only(self):
        assert FPB.classify_quote("Service animals welcome", kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.CLASS_SERVICE_ANIMAL_ONLY
        assert FPB.classify_quote("ADA-defined service animals are welcome free of charge.",
                                  kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.CLASS_SERVICE_ANIMAL_ONLY

    def test_amenity_chip_only(self):
        assert FPB.classify_quote("Pets Allowed Coin Laundry", kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.CLASS_AMENITY_CHIP_ONLY
        assert FPB.classify_quote("Pet friendly", kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.CLASS_AMENITY_CHIP_ONLY
        # The same label beside the page's fee sentence IS a policy block.
        cls, _why = FPB.classify_quote("Pets Welcome", kind=FPB.KIND_PET_FRIENDLY,
                                       context="Non-Refundable Pet Fee Per Night: $50.00 Maximum Pet Weight: 25.0lbs")
        assert cls == FPB.ELIGIBLE

    def test_structured_no_pets_with_insufficient_context(self):
        assert FPB.classify_quote('"petsAllowed": false', kind=FPB.KIND_NO_PETS)[0] == FPB.CLASS_STRUCTURED_NO_PETS_INSUFFICIENT
        assert FPB.classify_quote("pets_allowed=false", kind=FPB.KIND_NO_PETS)[0] == FPB.CLASS_STRUCTURED_NO_PETS_INSUFFICIENT

    def test_valid_operative_policy_and_valid_explicit_refusal(self):
        assert FPB.classify_quote("Pets allowed, $125.00 non-refundable fee", kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.ELIGIBLE
        assert FPB.classify_quote("Dogs and cats accepted.", kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.ELIGIBLE
        assert FPB.classify_quote("Pet Policy Pets Not Allowed", kind=FPB.KIND_NO_PETS)[0] == FPB.ELIGIBLE
        assert FPB.classify_quote("Sorry, no pets allowed.", kind=FPB.KIND_NO_PETS)[0] == FPB.ELIGIBLE

    def test_the_gate_refuses_five_live_dayton_records_and_says_why(self, dayton_package):
        report = FPB.evaluate_package(dayton_package)
        assert report["records_evaluated"] == 78 and report["ineligible"] == 5
        assert set(report["classes"]) == {FPB.CLASS_QUOTE_NOT_OPERATIVE, FPB.CLASS_AMENITY_CHIP_ONLY,
                                          FPB.CLASS_STRUCTURED_NO_PETS_INSUFFICIENT}
        assert {f["identity_key"] for f in report["failures"]} == \
            set(PILOT.DAYTON_WITHDRAW_PET_FRIENDLY) | set(PILOT.DAYTON_WITHDRAW_NO_PETS)

    def test_the_eight_checks_are_all_present_on_every_verdict(self, dayton_package):
        record, identity, refs = self._record(dayton_package)
        verdict = FPB.evaluate_policy_record(record, identity, refs)
        assert tuple(verdict["checks"]) == FPB.CHECKS
        assert verdict["eligible"]

    def test_an_unreviewed_record_has_no_authority_status(self, dayton_package):
        record, identity, refs = self._record(dayton_package)
        record.pop("approval", None)
        record.pop("reviewer_id", None)
        verdict = FPB.evaluate_policy_record(record, identity, refs)
        assert "AUTHORITY_STATUS" in verdict["failed_checks"]


# --------------------------------------------------------------------------- #
# Same-premises safety.
# --------------------------------------------------------------------------- #

class TestSamePremises:
    def _identity(self, key, name, street, postal, url, relation=None):
        rec = OrderedDict((("identity_key", key), ("canonical_name", name), ("slug", key.replace(" ", "-")),
                           ("street", street), ("city", "Indianapolis"), ("state", "IN"), ("postal_code", postal),
                           ("phone", ""), ("brand_family", ""), ("property_code", ""), ("official_url", url),
                           ("corridor", ""), ("aliases", []), ("collision_state", "NONE")))
        if relation:
            rec["relation"] = relation
        return rec

    def test_case_9_legitimate_same_campus_distinct_hotels_pass(self):
        a = self._identity("residence inn indianapolis southwest", "Residence Inn Indianapolis Southwest",
                           "5155 W Bradbury Ave", "46241",
                           "https://www.marriott.com/en-us/hotels/indsw-residence-inn-indianapolis-airport/overview/")
        b = self._identity("hotel indigo indianapolis southwest", "Hotel Indigo Indianapolis Southwest",
                           "5155 W Bradbury Ave", "46241",
                           "https://www.ihg.com/hotelindigo/hotels/us/en/indianapolis/indsw/hoteldetail")
        assert W._same_premises_issues([a, b]) == []

    def test_a_declared_relation_admits_a_pair_the_mechanical_rule_cannot_prove(self):
        a = self._identity("the galt house hotel", "The Galt House Hotel", "140 N 4th St", "40202",
                           "https://www.galthouse.com/")
        b = self._identity("rivue tower", "Rivue Tower", "140 N 4th St", "40202", "")
        assert [i.code for i in W._same_premises_issues([a, b])] == ["SAME_PREMISES_UNPROVEN"]
        b["relation"] = OrderedDict((("type", SMP.RELATION_CO_LOCATED_DISTINCT),
                                     ("related_identity_key", "the galt house hotel"),
                                     ("ruling_ref", "PTF-LOUISVILLE-FOUNDER-REVIEW-004")))
        assert W._same_premises_issues([a, b]) == []

    def test_an_accidental_duplicate_on_one_premises_fails(self):
        a = self._identity("tru by hilton st louis downtown", "Tru by Hilton St Louis Downtown", "1221 Locust St", "63103",
                           "https://www.hilton.com/en/hotels/stlocru-tru-st-louis-downtown/")
        b = self._identity("tru", "Tru", "1221 Locust St", "63103",
                           "https://www.hilton.com/en/hotels/stlocru-tru-st-louis-downtown/")
        assert [i.code for i in W._same_premises_issues([a, b])] == ["SAME_PREMISES_DUPLICATE"]

    def test_an_address_less_identity_is_not_a_collision(self):
        a = self._identity("a", "A Hotel", "", "45506", "")
        b = self._identity("b", "B Hotel", "", "45506", "")
        assert W._same_premises_issues([a, b]) == []


# --------------------------------------------------------------------------- #
# The whole-release index, preservation and the intended delta guard.
# --------------------------------------------------------------------------- #

class TestReleaseIndex:
    def test_current_verified_live_agrees_across_record_manifest_and_pin(self, live):
        """DEPLOYMENT_EPOCH_INVARIANT, and it moves when production moves.

        This assertion was written at the Cincinnati epoch -- deploy 6a9d33f5,
        786 profiles, ten markets -- and read three sources that had to AGREE.
        PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003 integrated this
        engineering onto the Toledo-live lineage, where production is deploy
        6a9e0476 at 803 profiles over eleven markets. The literal is therefore
        read from the committed pin rather than restated: what the test is
        actually about is the AGREEMENT of the record, the manifest and the pin,
        and that is exactly what still runs. Pinning a number the pin file
        already states would only mean editing it twice.
        """
        idx, state, problems = live
        assert problems == []
        pinned = MS.live()
        assert state.deploy_id == pinned.deploy_id
        assert state.total_profiles == pinned.total_profiles
        assert idx.total_profiles == pinned.total_profiles
        assert len(idx.participating) == len(pinned.participating_markets)
        assert state.rollback_target == state.previous_deploy_id and state.rollback_record
        assert len(state.rollback_markets) == len(pinned.participating_markets) - 1

    def test_a_zero_delta_package_compares_clean(self, live, dayton_package):
        idx = live[0]
        package_index = RI.index_from_package(dayton_package, participating=True)
        proposed = RI.compose(idx, package_index, participates=True)
        report = RI.compare(idx, proposed, package_market="dayton-oh", intended_delta=dayton_package["intended_delta"])
        assert report["passed"], report["finding_counts"]

    def test_case_10_cross_market_canonical_identity_collision(self, live, dayton_package):
        idx = live[0]
        package_index = RI.index_from_package(dayton_package, participating=True)
        foreign_key, foreign = next(iter(idx.markets["indianapolis-in"].profiles.items()))
        package_index.profiles[foreign_key] = RI.ProfileEntry(**{**foreign.__dict__, "market_id": "dayton-oh",
                                                                 "route": "/pet-friendly-hotels/dayton-oh/borrowed/"})
        proposed = RI.compose(idx, package_index, participates=True)
        report = RI.compare(idx, proposed, package_market="dayton-oh", intended_delta=dayton_package["intended_delta"])
        codes = set(report["finding_counts"])
        assert RI.CROSS_MARKET_IDENTITY_COLLISION in codes and RI.OWNERSHIP_MOVEMENT in codes

    def test_case_14_a_route_claimed_by_two_markets_is_a_duplicate(self, live, dayton_package):
        idx = live[0]
        package_index = RI.index_from_package(dayton_package, participating=True)
        key, entry = next(iter(package_index.profiles.items()))
        foreign_route = next(iter(idx.markets["indianapolis-in"].profiles.values())).route
        package_index.profiles[key] = RI.ProfileEntry(**{**entry.__dict__, "route": foreign_route})
        proposed = RI.compose(idx, package_index, participates=True)
        report = RI.compare(idx, proposed, package_market="dayton-oh", intended_delta=dayton_package["intended_delta"])
        assert RI.DUPLICATE_ROUTE in report["finding_counts"]

    def test_case_11_an_unrelated_live_market_cannot_disappear(self, live, dayton_package):
        idx = live[0]
        package_index = RI.index_from_package(dayton_package, participating=True)
        proposed = RI.compose(idx, package_index, participates=True)
        del proposed.markets["indianapolis-in"]
        report = RI.compare(idx, proposed, package_market="dayton-oh", intended_delta=dayton_package["intended_delta"])
        assert report["finding_counts"][RI.MISSING_LIVE_MARKET] == 1
        assert RI.DELTA_MISMATCH in report["finding_counts"]          # the market count moved, undeclared
        # ... nor lose a profile or a route.
        proposed = RI.compose(idx, package_index, participates=True)
        indy = proposed.markets["indianapolis-in"]
        trimmed = RI.MarketIndex(**{**indy.__dict__, "profiles": OrderedDict(list(indy.profiles.items())[1:])})
        proposed.markets["indianapolis-in"] = trimmed
        report = RI.compare(idx, proposed, package_market="dayton-oh", intended_delta=dayton_package["intended_delta"])
        assert RI.MISSING_UNRELATED_PROFILE in report["finding_counts"]
        assert RI.MISSING_UNRELATED_ROUTE in report["finding_counts"]

    def test_case_17_the_stale_pittsburgh_like_package_cannot_remove_newer_indianapolis_like_state(
            self, live, dayton_package, tmp_path):
        """The historic incident class: a package built from an older source
        whose view of the live release predates another market's growth.
        It fails on rule N (stale parent) without rebuilding Indianapolis,
        and rule H proves the CURRENT live members are what the proposed
        release carries -- never the package's stale view."""
        idx, state, _ = live
        stale = copy.deepcopy(dayton_package)
        parent = stale["parent_live_state"]
        parent["live_deploy_id"] = state.previous_deploy_id                  # one deploy behind
        parent["profile_counts"] = OrderedDict(parent["profile_counts"], **{"indianapolis-in": 67})
        parent["total_profiles"] = state.total_profiles - 15
        parent["live_index_digest"] = "sha256:" + "1" * 64
        stale = SMP.seal(SMP.body_of(stale), sealed_at=SEALED_AT)
        receipt = _lane(stale, live, tmp_path)
        assert receipt["RESULTS"]["N"]["status"] == FL.FAIL
        assert any("indianapolis" in p or "profile_counts" in p or "live_deploy_id" in p
                   for p in receipt["RESULTS"]["N"]["problems"])
        assert receipt["RESULTS"]["H"]["status"] == FL.PASS          # Indianapolis (82) preserved from CURRENT live
        # The proposed release is CURRENT live with the stale package's market
        # replaced; its total is therefore live's, whatever epoch live is at.
        # 786 when this was written at the Cincinnati epoch, 803 since
        # PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003 integrated
        # this engineering onto the Toledo-live lineage. The point of the case
        # is unchanged and still checked above: a package one deploy behind
        # cannot remove newer state.
        assert (receipt["RESULTS"]["G"]["detail"]["proposed_total_profiles"]
                == MS.live().total_profiles)
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO
        assert receipt["RESULTS"]["J"]["status"] == FL.UNKNOWN            # nothing was rebuilt to find out

    def test_case_12_and_13_removals_and_route_loss_must_be_declared(self, live, corrected_package, tmp_path):
        receipt = _lane(corrected_package, live, tmp_path / "declared")
        assert receipt["RESULTS"]["I"]["status"] == FL.PASS
        assert receipt["RESULTS"]["I"]["detail"]["actual_delta"]["profile_delta"] == -4
        # The same withdrawal without the corridor-route consequence declared.
        undeclared = PILOT.withdrawal_inputs(live, declare_corridor_routes=False)
        package = W.build_sealed_package(undeclared, sealed_at=SEALED_AT)
        receipt = _lane(package, live, tmp_path / "undeclared")
        assert receipt["RESULTS"]["I"]["status"] == FL.FAIL
        assert any("route" in p and "without declared intent" in p for p in receipt["RESULTS"]["I"]["problems"])
        # And a removal nobody declared at all.
        silent = PILOT.frozen_inputs("dayton-oh", live)
        silent.pet_friendly_records = silent.pet_friendly_records[1:]
        partition = json.loads(json.dumps(silent.partition))
        partition["items"] = [i for i in partition["items"]
                              if i["identity_key"] != "ac hotel dayton"] + [OrderedDict((
                                  ("identity_key", "ac hotel dayton"), ("canonical_name", "AC Hotel Dayton"),
                                  ("final_state", "AWAITING_POLICY_ARTIFACT"), ("resolved", False),
                                  ("next_action", "x"), ("next_action_source", "x"), ("determined_by", "x")))]
        silent.partition = partition
        package = W.build_sealed_package(silent, sealed_at=SEALED_AT)
        receipt = _lane(package, live, tmp_path / "silent")
        assert receipt["RESULTS"]["I"]["status"] == FL.FAIL
        assert any(p.startswith("profile 'ac hotel dayton' removed") for p in receipt["RESULTS"]["I"]["problems"])

    def test_the_index_is_o_data_and_fast_at_a_hundred_markets(self, live, corrected_package):
        package_index = RI.index_from_package(corrected_package, participating=True)
        rows = RI.benchmark(live[0], package_index, corrected_package["intended_delta"], sizes=(11, 100))
        assert rows[-1]["markets"] == 100 and rows[-1]["profiles"] > 7000
        assert rows[-1]["total_seconds"] < 30, rows

    def test_the_rollback_chain_is_checked_generically(self, tmp_path):
        """H12: a rollback target must be the previous DEPLOYED record with
        its own market set; a chain that skips a deploy is a problem."""
        deploy = tmp_path / "deploy"
        (deploy / "deployment_records").mkdir(parents=True)
        (deploy / "deployment_authorizations").mkdir()
        older = OrderedDict((("deployment_id", "a" * 24), ("previous_deployment_id", "0" * 24),
                             ("rollback_target", "0" * 24), ("deployed_at", "2026-09-01T00:00:00+00:00"),
                             ("final_status", "DEPLOYED"), ("bundle_sha256", "b" * 64), ("sitemap_sha256", "c" * 64),
                             ("participating_markets", ["columbus-oh"]), ("profile_counts", {"columbus-oh": 88}),
                             ("total_profiles", 88), ("sitemap_route_count", 100), ("authorization_id", "auth-a")))
        newest = OrderedDict(older, deployment_id="d" * 24, previous_deployment_id="e" * 24,
                             rollback_target="e" * 24, deployed_at="2026-09-02T00:00:00+00:00", authorization_id="auth-d")
        for doc in (older, newest):
            (deploy / "deployment_records" / ("%s.json" % doc["deployment_id"])).write_text(json.dumps(doc), encoding="utf-8")
        state = RI.current_verified_live(deploy_dir=deploy, pins_dir=tmp_path / "nopins")
        assert any("previous DEPLOYED record" in p for p in state.problems)
        assert any("no DEPLOYED record of its own" in p for p in state.problems)


# --------------------------------------------------------------------------- #
# The lane, the receipt, determinism, freshness, paid provenance.
# --------------------------------------------------------------------------- #

class TestFastLane:
    def test_case_1_the_corrected_dayton_package_passes_every_non_build_rule(self, live, corrected_package, tmp_path):
        receipt = _lane(corrected_package, live, tmp_path)
        for rule in "ABCDEFGHILMNO":
            assert receipt["RESULTS"][rule]["status"] == FL.PASS, (rule, receipt["RESULTS"][rule]["problems"])
        assert receipt["UNKNOWN_RULES"] == ["J", "K"]
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO       # UNKNOWN => NOT ELIGIBLE
        assert receipt["LEGACY_EXCEPTIONS"] == []

    def test_the_frozen_live_copy_fails_the_first_party_gate_and_nothing_else(self, live, dayton_package, tmp_path):
        receipt = _lane(dayton_package, live, tmp_path)
        assert receipt["FAILED_RULES"] == ["C"]
        assert receipt["RESULTS"]["C"]["detail"]["ineligible"] == 5

    def test_the_receipt_carries_every_field_the_order_names(self, live, corrected_package, tmp_path):
        receipt = _lane(corrected_package, live, tmp_path)
        for field in ("PACKAGE_ID", "PACKAGE_DIGEST", "PARENT_RELEASE", "CHANGE_CLASS", "DEPENDENCY_DIGEST",
                      "VALIDATION_POLICY_VERSION", "RULES_EXECUTED", "RESULTS", "TIMESTAMPS", "ARTIFACT_DIGESTS",
                      "GLOBAL_INDEX_DIGEST", "INTENDED_DELTA_DIGEST", "DETERMINISM_RESULT",
                      "FIRST_PARTY_BINDING_RESULT", "COLLISION_RESULT", "REMOVAL_RESULT", "LEGACY_EXCEPTIONS",
                      "ENVIRONMENT", "EXPIRY_REVOCATION_CONDITIONS", "FAST_DATA_ONLY_RELEASE_ELIGIBLE",
                      "FAST_PATH_PRODUCTION_ACTIVATION", "RECEIPT_DIGEST"):
            assert field in receipt, field
        assert [r["rule"] for r in receipt["RULES_EXECUTED"]] == list(FL.RULES)
        assert receipt["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"
        assert receipt["PRODUCTION_ACTIVATION_ALLOWED"] == FL.NO

    @pytest.mark.slow
    def test_case_15_identical_changed_market_builds_are_deterministic_and_cold(self, live, corrected_package, tmp_path):
        receipt = FL.run_fast_lane(corrected_package, work_dir=tmp_path, live=live, build=True, determinism=True,
                                   now=VALIDATED_AT)
        k = receipt["RESULTS"]["K"]
        assert receipt["RESULTS"]["J"]["status"] == FL.PASS, receipt["RESULTS"]["J"]["problems"]
        assert k["status"] == FL.PASS, k["problems"]
        assert k["detail"]["result"] == "BYTE_IDENTICAL"
        assert k["detail"]["output_digest_a"] == k["detail"]["output_digest_b"]
        assert k["detail"]["cold_builds_executed"] >= 2 and k["detail"]["reuse_hits"] == 0
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES
        assert receipt["PERFORMANCE"]["total_seconds"] < 15 * 60
        assert subprocess.run(["git", "status", "--porcelain", "--", "launch_packages/pettripfinder/markets/authority",
                               "launch_packages/pettripfinder/identity_census", "deploy/netlify"],
                              cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip() == ""

    def test_case_16_a_nondeterministic_build_fails_the_gate(self, live, corrected_package, tmp_path, monkeypatch):
        calls = []

        def fake_build(package, stage_root, output_root, *, context="production", cold=True, repo_root=None):
            calls.append(cold)
            digest = "a" * 64 if len(calls) == 1 else "b" * 64
            return OrderedDict((("market_id", package["market_id"]), ("package_id", package["package_id"]),
                                ("context", context), ("cold", cold), ("staged_files", {}),
                                ("staged_input_digest", "sha256:" + "5" * 64), ("contract_sha256", "sha256:" + "6" * 64),
                                ("bundle_sha256", digest), ("file_count", 1), ("html_count", 1), ("release_name", "x"),
                                ("gates_failing", []),
                                ("cache_events", [OrderedDict((("verdict", "BUILD_EXECUTED"), ("assembly_kind", "market_bundle"),
                                                               ("input_key", "k"), ("seconds", 1.0)))]),
                                ("seconds", 1.0)))
        monkeypatch.setattr(STAGING, "build_changed_market", fake_build)
        receipt = _lane(corrected_package, live, tmp_path, build=True, determinism=True)
        assert calls == [True, True]
        assert receipt["RESULTS"]["K"]["status"] == FL.FAIL
        assert receipt["DETERMINISM_RESULT"] == "DIFFERENT"
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO

    def test_two_cache_hits_can_never_pass_the_determinism_gate(self, live, corrected_package, tmp_path, monkeypatch):
        def warm_build(package, stage_root, output_root, *, context="production", cold=True, repo_root=None):
            return OrderedDict((("market_id", package["market_id"]), ("package_id", package["package_id"]),
                                ("context", context), ("cold", cold), ("staged_files", {}),
                                ("staged_input_digest", "sha256:" + "5" * 64), ("contract_sha256", "sha256:" + "6" * 64),
                                ("bundle_sha256", "a" * 64), ("file_count", 1), ("html_count", 1), ("release_name", "x"),
                                ("gates_failing", []),
                                ("cache_events", [OrderedDict((("verdict", "REUSE_HIT"), ("assembly_kind", "market_bundle"),
                                                               ("input_key", "k"), ("seconds", 0.1)))]),
                                ("seconds", 0.1)))
        monkeypatch.setattr(STAGING, "build_changed_market", warm_build)
        receipt = _lane(corrected_package, live, tmp_path, build=True, determinism=True)
        assert receipt["RESULTS"]["J"]["status"] == FL.FAIL and receipt["RESULTS"]["K"]["status"] == FL.FAIL

    def test_freshness_and_revocation(self, live, corrected_package, tmp_path):
        old = FPB.parse_timestamp("2028-01-01T00:00:00Z")
        receipt = _lane(corrected_package, live, tmp_path / "old", now=old)
        assert receipt["RESULTS"]["M"]["status"] == FL.FAIL
        assert any("older than" in p for p in receipt["RESULTS"]["M"]["problems"])
        revoked = {corrected_package["evidence_references"][0]["artifact_sha256"]: {"reason": "wrong property"}}
        receipt = _lane(corrected_package, live, tmp_path / "revoked", revocations=revoked)
        assert receipt["RESULTS"]["M"]["status"] == FL.FAIL
        assert any("REVOKED" in p for p in receipt["RESULTS"]["M"]["problems"])

    def _with_paid_reference(self, package, reservation):
        package = copy.deepcopy(package)
        ref = package["evidence_references"][0]
        ref["capture_lane"] = "firecrawl_rendered_fetch"
        if reservation is not None:
            ref["paid_reservation"] = reservation
        return SMP.seal(SMP.body_of(package), sealed_at=SEALED_AT)

    def test_case_21_paid_evidence_without_reservation_provenance_fails(self, live, corrected_package, tmp_path):
        package = self._with_paid_reference(corrected_package, None)
        receipt = _lane(package, live, tmp_path)
        assert receipt["RESULTS"]["O"]["status"] == FL.FAIL
        assert receipt["RESULTS"]["O"]["detail"]["paid_references"] == 1

    def test_case_22_a_correctly_reserved_paid_capture_passes_without_a_provider_call(self, live, corrected_package, tmp_path):
        ref = corrected_package["evidence_references"][0]
        reservation = OrderedDict((("provider", "Firecrawl"), ("lane", "firecrawl"), ("run_id", "dayton_oh_firecrawl_001"),
                                   ("attempt_id", paid_attempt_id("dayton-oh", "dayton_oh_firecrawl_001",
                                                                  ref["identity_key"], "firecrawl")),
                                   ("request_envelope_sha256", "sha256:" + "7" * 64)))
        package = self._with_paid_reference(corrected_package, reservation)
        receipt = _lane(package, live, tmp_path / "ok", ledger_lookup=lambda r: True)
        assert receipt["RESULTS"]["O"]["status"] == FL.PASS
        assert receipt["RESULTS"]["O"]["detail"]["ledger_cross_checked"] == 1
        wrong = OrderedDict(reservation, attempt_id="0" * 16)
        receipt = _lane(self._with_paid_reference(corrected_package, wrong), live, tmp_path / "wrong")
        assert receipt["RESULTS"]["O"]["status"] == FL.FAIL
        receipt = _lane(package, live, tmp_path / "unknown", ledger_lookup=lambda r: None)
        assert receipt["RESULTS"]["O"]["status"] == FL.UNKNOWN
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO

    def test_the_writer_makes_a_paid_dependency_visible(self, dayton_inputs):
        inputs = _clone(dayton_inputs)
        inputs.pet_friendly_records[0]["evidence"][0]["capture_method"] = "brightdata_browser"
        package = W.build_sealed_package(inputs, sealed_at=SEALED_AT)
        paid = [r for r in package["evidence_references"] if W.is_paid_lane(r["capture_lane"])]
        assert paid and "paid_reservation" not in paid[0]
        assert package["coverage_scorecard"]["paid_evidence_references"] == 0

    def test_the_lane_never_builds_an_unchanged_market(self, live, corrected_package, tmp_path, monkeypatch):
        seen = []
        real = STAGING.build_changed_market

        def spy(package, *a, **kw):
            seen.append(package["market_id"])
            raise RuntimeError("stop before the real build")
        monkeypatch.setattr(STAGING, "build_changed_market", spy)
        _lane(corrected_package, live, tmp_path, build=True)
        assert seen == ["dayton-oh"]
        assert real is not spy


# --------------------------------------------------------------------------- #
# Staging: committed authority is never touched.
# --------------------------------------------------------------------------- #

class TestStaging:
    def test_a_staged_build_leaves_no_build_state_behind(self, corrected_package, tmp_path, monkeypatch):
        """The 003 migration audit's one TRUE_NEW class: a staged Dayton build
        left the /go/ route prefix set for whatever ran next in the process."""
        from scripts.pettripfinder import commercial_actions as CA
        from scripts.pettripfinder.approved_hotel_profile import set_market_labels

        assert CA.go_market_prefix() == ""
        with STAGING.overlay(tmp_path / "stage_state"):
            CA.set_go_market_prefix("dayton-oh")
            set_market_labels(label="Dayton", state="Ohio", metro_default="Dayton, OH")
        assert CA.go_market_prefix() == ""
        assert CA.go_route("drury-inn-suites-columbus-grove-city", CA.ACTION_OFFICIAL_WEBSITE) == \
            "/go/drury-inn-suites-columbus-grove-city/official-website/"
        for module_name, attribute in STAGING.BUILD_STATE_ATTRIBUTES:
            assert hasattr(__import__(module_name, fromlist=[attribute]), attribute), (module_name, attribute)

    def test_staging_writes_only_into_the_stage_and_restores_every_constant(self, corrected_package, tmp_path):
        from scripts.pettripfinder import site_data
        from scripts.pettripfinder.markets import contract as MC
        before = (site_data.PRODUCTION_CSV, MC.MARKETS_DIR)
        written = STAGING.stage_package(corrected_package, tmp_path / "stage")
        assert "launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json" in written
        assert "launch_packages/pettripfinder/markets/authority/dayton-oh/hotel_exclusions.json" in written
        assert all((tmp_path / "stage" / p).is_file() for p in written)
        with STAGING.overlay(tmp_path / "stage"):
            assert site_data.PRODUCTION_CSV != before[0] and MC.MARKETS_DIR != before[1]
            contract = STAGING.derive_staged_contract(corrected_package, tmp_path / "stage")
            assert contract["policy_package"]["expected_record_count"] == 50
            assert contract["reconciliation"]["verified_no_pets"] == 23
        assert (site_data.PRODUCTION_CSV, MC.MARKETS_DIR) == before
        status = subprocess.run(["git", "status", "--porcelain", "--", "launch_packages/pettripfinder/markets/authority",
                                 "launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json", "deploy/netlify"],
                                cwd=str(REPO_ROOT), capture_output=True, text=True).stdout
        assert status.strip() == ""


# --------------------------------------------------------------------------- #
# Regression V2: classes, surfaces, the data-only refinement, the boundary.
# --------------------------------------------------------------------------- #

class TestRegressionV2Extension:
    def test_the_new_classes_have_rows_and_the_mandatory_set_is_unchanged(self):
        assert RD.MARKET_DATA_PACKAGE in RD.SAFE_NARROW_CLASSES
        assert RD.MARKET_AUTHORITY_DATA_ONLY not in RD.MANDATORY_FULL_REGRESSION
        assert RD.MARKET_AUTHORITY_DATA_ONLY not in RD.SAFE_NARROW_CLASSES
        assert RD.VALIDATION_MATRIX[RD.MARKET_AUTHORITY_DATA_ONLY]["full_regression"] == RD.CONDITIONAL
        assert RD.VALIDATION_MATRIX[RD.MARKET_AUTHORITY_DATA_ONLY]["assembly"] == RD.REQUIRED
        assert set(RD.MANDATORY_FULL_REGRESSION) == {RD.AUTHORITY_CHANGE, RD.GENERIC_RUNTIME_CHANGE, RD.SCHEMA_CHANGE,
                                                     RD.ROUTING_SEMANTIC_CHANGE, RD.DEPLOYMENT_CHANGE, RD.UNCLASSIFIED}

    def test_packages_staging_and_receipts_are_market_data_and_market_owned(self):
        for rel in ("launch_packages/pettripfinder/markets/packages/nashville-tn/pkg-nashville-tn-0123456789abcdef.json",
                    "launch_packages/pettripfinder/markets/staging/nashville-tn/launch_packages/pettripfinder/x.json",
                    "launch_packages/pettripfinder/markets/receipts/nashville-tn/pkg-x-y.json"):
            assert RD.classify_path(rel)[0] == (RD.MARKET_DATA_PACKAGE,), rel
            zone, _why = OWN.owner_of(rel)
            assert zone is not None and zone.market_id == "nashville-tn", rel
        assert RD.classify_path("launch_packages/pettripfinder/fast_release_activation.json")[0] == (RD.DEPLOYMENT_CHANGE,)
        assert RD.is_narrowing_blocker("launch_packages/pettripfinder/fast_release_activation.json")
        assert RD.classify_path("launch_packages/pettripfinder/evidence_revocations.json")[0] == (RD.AUTHORITY_CHANGE,)
        for module in ("sealed_market_package", "market_package_writer", "package_staging", "release_index",
                       "first_party_binding", "fast_release_lane"):
            assert RD.is_narrowing_blocker("scripts/pettripfinder/%s.py" % module), module

    def _row(self, path, classes):
        return {"path": path, "status": "M", "classes": list(classes), "rule": "r", "why": "",
                "shared_test_state": False, "markets": [], "market_local_proof": None, "renamed_from": None}

    def test_a_one_market_data_only_change_set_is_recognised(self):
        rows = [self._row("launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json", (RD.AUTHORITY_CHANGE,)),
                self._row("launch_packages/pettripfinder/markets/authority/dayton-oh/hotel_exclusions.json", (RD.AUTHORITY_CHANGE,)),
                self._row("launch_packages/pettripfinder/identity_census/dayton-oh.json", (RD.AUTHORITY_CHANGE, RD.ROUTING_SEMANTIC_CHANGE)),
                self._row("launch_packages/pettripfinder/dayton_final_partition_002.json", (RD.AUTHORITY_CHANGE,)),
                self._row("deploy/netlify/release_contracts/dayton-oh.json", (RD.AUTHORITY_CHANGE,)),
                self._row("launch_packages/pettripfinder/markets/reports/dayton_oh_x.json", (RD.GENERATED_REPORT_ONLY,))]
        market, why = RD._market_authority_data_only(rows, "HEAD", RD.WORKTREE, [])
        assert market == "dayton-oh", why

    def test_case_23_an_unknown_dependency_is_not_data_only(self):
        rows = [self._row("launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json", (RD.AUTHORITY_CHANGE,)),
                self._row("some/directory/nobody/taught/us/about.bin", (RD.UNCLASSIFIED,))]
        assert RD._market_authority_data_only(rows, "HEAD", RD.WORKTREE, [])[0] is None
        assert RD.release_surface_of(rows[1]) == RD.SURFACE_UNKNOWN_MIXED

    def test_case_24_a_shared_runtime_change_is_not_data_only(self):
        rows = [self._row("launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json", (RD.AUTHORITY_CHANGE,)),
                self._row("scripts/pettripfinder/site_data.py", (RD.GENERIC_RUNTIME_CHANGE,))]
        assert RD._market_authority_data_only(rows, "HEAD", RD.WORKTREE, [])[0] is None
        assert RD.release_surface_of(rows[1]) == RD.SURFACE_SHARED_RUNTIME_CHANGE
        schema = self._row("scripts/pettripfinder/contracts/policy_schema.py", (RD.GENERIC_RUNTIME_CHANGE, RD.SCHEMA_CHANGE))
        assert RD.release_surface_of(schema) == RD.SURFACE_SHARED_SCHEMA_CHANGE

    def test_case_25_a_shared_assembler_change_is_not_data_only(self):
        rows = [self._row("launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json", (RD.AUTHORITY_CHANGE,)),
                self._row("scripts/pettripfinder/assemble_netlify_bundle.py", (RD.GENERIC_RUNTIME_CHANGE, RD.DEPLOYMENT_CHANGE))]
        assert RD._market_authority_data_only(rows, "HEAD", RD.WORKTREE, [])[0] is None
        assert RD.release_surface_of(rows[1]) == RD.SURFACE_ASSEMBLER_CHANGE
        assert RD.release_surface_of(self._row("scripts/pettripfinder/regression_delta.py", (RD.GENERIC_RUNTIME_CHANGE,))) \
            == RD.SURFACE_CLASSIFIER_TEST_INFRA_CHANGE

    def test_two_markets_or_a_blocker_are_not_data_only(self):
        rows = [self._row("launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json", (RD.AUTHORITY_CHANGE,)),
                self._row("launch_packages/pettripfinder/hotel_policy_facts_pittsburgh-pa.json", (RD.AUTHORITY_CHANGE,))]
        assert RD._market_authority_data_only(rows, "HEAD", RD.WORKTREE, [])[0] is None
        assert RD._market_authority_data_only(rows[:1], "HEAD", RD.WORKTREE, ["conftest.py"])[0] is None
        assert RD._market_authority_data_only(
            [self._row("launch_packages/pettripfinder/launch_participation.json", (RD.AUTHORITY_CHANGE,))],
            "HEAD", RD.WORKTREE, [])[0] is None

    def test_the_fast_requirement_fails_closed_without_a_package_receipt_or_activation(self, dayton_package, live, tmp_path, monkeypatch):
        rows = [self._row("launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json", (RD.AUTHORITY_CHANGE,))]
        monkeypatch.setattr(SMP, "PACKAGES_DIR", tmp_path / "packages")
        monkeypatch.setattr(SMP, "RECEIPTS_DIR", tmp_path / "receipts")
        block = RD.fast_data_only_release("dayton-oh", rows, RD.WORKTREE)
        assert block["FAST_DATA_ONLY_RELEASE_REQUIRED"] == "YES" and block["FULL_REGRESSION_REQUIRED"] == "YES"
        assert "no sealed package" in block["why"]
        # A sealed package covering the committed bytes, no receipt yet.
        SMP.write_sealed(dayton_package, tmp_path / "packages")
        block = RD.fast_data_only_release("dayton-oh", rows, RD.WORKTREE)
        assert block["package_id"] == dayton_package["package_id"] and block["FULL_REGRESSION_REQUIRED"] == "YES"
        assert "no committed receipt" in block["why"]
        # A receipt that is NOT eligible does not count.
        receipt = _lane(dayton_package, live, tmp_path / "lane")
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO
        FL.write_receipt(receipt, tmp_path / "receipts")
        block = RD.fast_data_only_release("dayton-oh", rows, RD.WORKTREE)
        assert block["FULL_REGRESSION_REQUIRED"] == "YES"
        # An ELIGIBLE receipt (fixture) still cannot lift the requirement while activation is DISABLED.
        eligible = copy.deepcopy(receipt)
        eligible["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] = FL.YES
        eligible["UNKNOWN_RULES"] = []
        eligible["FAILED_RULES"] = []
        eligible["RECEIPT_DIGEST"] = "sha256:" + "9" * 64
        FL.write_receipt(eligible, tmp_path / "receipts")
        block = RD.fast_data_only_release("dayton-oh", rows, RD.WORKTREE)
        assert block["receipt_eligible"] and block["FULL_REGRESSION_REQUIRED"] == "YES"
        assert "DISABLED" in block["why"]
        # Only the activation file, ENABLED with the market allow-listed, lifts it.
        monkeypatch.setattr(FL, "load_activation", lambda path=None: OrderedDict((
            ("FAST_PATH_PRODUCTION_ACTIVATION", "ENABLED"), ("pilot_allowlist", ["dayton-oh"]))))
        block = RD.fast_data_only_release("dayton-oh", rows, RD.WORKTREE)
        assert block["FULL_REGRESSION_REQUIRED"] == "NO"
        classification = {"changed_files": [dict(rows[0], classes=[RD.MARKET_AUTHORITY_DATA_ONLY], markets=["dayton-oh"])],
                          "fast_data_only_release": block, "release_surfaces": [RD.SURFACE_MARKET_AUTHORITY_DATA_ONLY]}
        plan = RD.plan_for(classification)
        assert plan["FAST_DATA_ONLY_RELEASE_REQUIRED"] == "YES" and not plan["full_regression_required"]
        assert plan["assembly_required"]

    def test_the_committed_activation_is_disabled_with_an_empty_allowlist(self):
        doc = FL.load_activation()
        assert doc["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED" and doc["pilot_allowlist"] == []
        assert doc["FAST_PATH_IMPLEMENTED"] == "YES" and doc["FAST_PATH_VALIDATED"] == "YES"
        assert not FL.production_activation_allowed("dayton-oh")

    def test_this_work_orders_own_change_set_is_broad(self):
        classification = RD.classify_change("e982aad")
        assert classification["market_authority_data_only"]["market_id"] is None
        plan = RD.plan_for(classification)
        assert plan["full_regression_required"] and plan["FAST_DATA_ONLY_RELEASE_REQUIRED"] == "NO"
        assert RD.SURFACE_CLASSIFIER_TEST_INFRA_CHANGE in classification["release_surfaces"]

    def test_the_committed_matrix_carries_the_release_surfaces(self):
        doc = json.loads(RD.MATRIX_PATH.read_text(encoding="utf-8-sig"))
        assert doc["release_surfaces"] == list(RD.RELEASE_SURFACES)
        rows = {r["release_surface"]: r for r in doc["release_surface_matrix"]}
        assert rows[RD.SURFACE_MARKET_AUTHORITY_DATA_ONLY]["FAST_DATA_ONLY_RELEASE_REQUIRED"] == "YES"
        for surface in (RD.SURFACE_SHARED_SCHEMA_CHANGE, RD.SURFACE_SHARED_RUNTIME_CHANGE, RD.SURFACE_ASSEMBLER_CHANGE,
                        RD.SURFACE_DEPLOYMENT_CHANGE, RD.SURFACE_CLASSIFIER_TEST_INFRA_CHANGE, RD.SURFACE_UNKNOWN_MIXED):
            assert rows[surface]["FULL_REGRESSION_REQUIRED"] == "YES", surface


# --------------------------------------------------------------------------- #
# The committed pilot artifacts.
# --------------------------------------------------------------------------- #

class TestCommittedPilot:
    def test_the_pilot_package_and_receipt_are_committed_under_the_market_and_agree(self):
        packages = SMP.list_packages("dayton-oh")
        assert packages, "the pilot package is committed under markets/packages/dayton-oh/"
        package = SMP.read_sealed(packages[-1])
        receipts = FL.eligible_receipts("dayton-oh", package["package_digest"])
        assert receipts, "the pilot receipt says ELIGIBLE = YES for the committed package"
        receipt = json.loads(receipts[-1].read_text(encoding="utf-8-sig"))
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES and receipt["UNKNOWN_RULES"] == []
        assert all(res["status"] == FL.PASS for res in receipt["RESULTS"].values())
        assert receipt["DETERMINISM_RESULT"] == "BYTE_IDENTICAL"
        assert receipt["PERFORMANCE"]["total_seconds"] < 15 * 60
        assert receipt["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"

    def test_the_committed_report_records_the_measurements(self):
        doc = json.loads((REPORTS / "atlas_throughput_003_fast_lane_report.json").read_text(encoding="utf-8-sig"))
        p2 = doc["packages"]["P2_dayton_withdrawal"]
        assert p2["receipt"]["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES
        assert p2["receipt"]["total_seconds"] < 15 * 60
        assert doc["packages"]["P1_dayton_frozen_zero_delta"]["receipt"]["failed_rules"] == ["C"]
        assert doc["index_benchmark"][-1]["markets"] >= 100
