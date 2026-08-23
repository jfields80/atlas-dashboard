"""PTF-ST-LOUIS-FOUNDER-SIGNATURE-005 -- a signature, and what it must refuse.

Two properties carry this work order and neither is about hotels.

THE SIGNATURE IS SCOPED. It covers a named population and refuses to widen to
whatever else happens to be reviewable, because a scoped approval that quietly
becomes a blanket one is indistinguishable from the blanket one afterwards.

THE DECIDER AND THE TRANSCRIBER ARE DIFFERENT FIELDS. PTF-POLICY-SCHEMA-
MIGRATION-001 Phase F wrote twenty-six approvals under a founder's name for
records the founder had never seen; every fact was source-backed and every hash
verified, and the defect was purely the signature. No technical gate catches
that, because no gate checks who a name belongs to. These tests are the closest
thing to one.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder import market_founder_signature_cli as SIG
from scripts.pettripfinder import market_proposed_authority_cli as AUTH
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import founder_approval as FA

PKG = "launch_packages/pettripfinder/"


def _load(name):
    with open(PKG + name, encoding="utf-8") as handle:
        return json.load(handle)


def candidate(key, **over):
    base = {"identity_key": key, "canonical_name": key.title(), "brand": "CHOICE",
            "corridor": "c", "source_url": "https://x/y", "snapshot_hash": "s",
            "founder_decision": "", "founder_reviewer_id": "",
            "founder_reviewed_at": "",
            "semantic_approval": {"semantic_hash": "sha256:" + key}}
    base.update(over)
    return base


def reviewed(key, disposition, **over):
    base = {"identity_key": key, "proposed_disposition": disposition,
            "next_action": "", "required_changes": []}
    base.update(over)
    return base


def run(candidates, rows, **over):
    kwargs = {"decided_by": "founder-id", "decided_at": "2026-08-23",
              "authorization": "the founder's words",
              "work_order": "WO", "recorded_by": "agent, transcription only"}
    kwargs.update(over)
    return SIG.sign({"candidates": candidates, "market_id": "m"},
                    {"rows": rows}, **kwargs)


class TestScope:
    def test_only_the_authorised_dispositions_are_signed(self):
        ledger = run(
            [candidate("a"), candidate("b"), candidate("c"), candidate("d")],
            [reviewed("a", "APPROVE_PET_FRIENDLY"),
             reviewed("b", "APPROVE_VERIFIED_NO_PETS"),
             reviewed("c", "APPROVE_WITH_CHANGE"),
             reviewed("d", "HOLD")])
        assert ledger["signed_count"] == 2
        assert ledger["withheld_count"] == 2
        assert {r["identity_key"] for r in ledger["signed"]} == {"a", "b"}

    def test_a_held_row_is_never_signed(self):
        ledger = run([candidate("a")], [reviewed("a", "HOLD")])
        assert ledger["signed"] == []

    def test_a_row_needing_a_change_is_never_signed(self):
        ledger = run([candidate("a")], [reviewed("a", "APPROVE_WITH_CHANGE")])
        assert ledger["signed"] == []

    def test_every_withheld_row_says_what_it_is_waiting_on(self):
        ledger = run([candidate("a")],
                     [reviewed("a", "HOLD", next_action="do the thing")])
        assert ledger["withheld"][0]["outstanding"] == "do the thing"

    def test_the_scope_can_be_narrowed_but_is_never_inferred(self):
        ledger = run([candidate("a"), candidate("b")],
                     [reviewed("a", "APPROVE_PET_FRIENDLY"),
                      reviewed("b", "APPROVE_VERIFIED_NO_PETS")],
                     signable=("APPROVE_PET_FRIENDLY",))
        assert ledger["signed_count"] == 1
        assert ledger["authorised_scope"] == ["APPROVE_PET_FRIENDLY"]


class TestTheAttestationIsNotInvented:
    @pytest.mark.parametrize("field", ["decided_by", "decided_at",
                                       "authorization"])
    def test_a_missing_attestation_field_stops_the_run(self, field):
        with pytest.raises(SIG.SignatureError):
            run([candidate("a")], [reviewed("a", "APPROVE_PET_FRIENDLY")],
                **{field: ""})

    def test_the_decider_and_the_transcriber_are_separate_fields(self):
        ledger = run([candidate("a")], [reviewed("a", "APPROVE_PET_FRIENDLY")],
                     decided_by="the-founder", recorded_by="the-agent")
        assert ledger["decided_by"] == "the-founder"
        assert ledger["recorded_by"] == "the-agent"
        assert ledger["signed"][0]["founder_reviewer_id"] == "the-founder"

    def test_the_authorisation_is_recorded_verbatim(self):
        ledger = run([candidate("a")], [reviewed("a", "APPROVE_PET_FRIENDLY")],
                     authorization="sign the 114 clean rows only")
        assert ledger["authorization"] == "sign the 114 clean rows only"

    def test_an_already_signed_row_is_never_re_signed(self):
        with pytest.raises(SIG.SignatureError):
            run([candidate("a", founder_decision="APPROVED_AFTER_CURRENT_REVIEW")],
                [reviewed("a", "APPROVE_PET_FRIENDLY")])

    def test_an_unreviewed_candidate_stops_the_whole_run(self):
        with pytest.raises(SIG.SignatureError):
            run([candidate("a"), candidate("b")],
                [reviewed("a", "APPROVE_PET_FRIENDLY")])

    def test_the_decision_uses_the_repositorys_canonical_word(self):
        ledger = run([candidate("a")], [reviewed("a", "APPROVE_PET_FRIENDLY")])
        decision = ledger["signed"][0]["founder_decision"]
        assert decision == FA.CANONICAL_APPROVED == "APPROVED_AFTER_CURRENT_REVIEW"
        assert FA.is_publishable(decision)


class TestBinding:
    def test_a_signature_is_bound_to_what_the_founder_was_shown(self):
        ledger = run([candidate("a")], [reviewed("a", "APPROVE_PET_FRIENDLY")])
        row = ledger["signed"][0]
        assert row["bound_semantic_hash"] == "sha256:a"
        assert row["bound_snapshot_hash"] == "s"

    def test_authority_refuses_a_record_that_changed_after_signing(self):
        decisions = {"market_id": "m", "signed": [{
            "identity_key": "a", "canonical_name": "A", "corridor": "c",
            "founder_decision": FA.CANONICAL_APPROVED,
            "founder_reviewer_id": "f", "founder_reviewed_at": "d",
            "proposes_authority": enums.PUBLISHED_PET_FRIENDLY,
            "bound_semantic_hash": "sha256:a", "bound_snapshot_hash": "OLD"}]}
        store = {"records": [{"identity_key": "a", "observation": {
            "snapshot_hash": "NEW", "evidence": []}}]}
        built = AUTH.build(decisions, store, {"hotels": []})
        assert built["authority_total"] == 0
        assert "changed after it was signed" in built["unresolved"][0]["why"]

    def test_an_unsigned_row_can_never_become_authority(self):
        decisions = {"market_id": "m", "signed": []}
        store = {"records": [{"identity_key": "a", "observation": {}}]}
        assert AUTH.build(decisions, store, {"hotels": []})["authority_total"] == 0

    def test_a_non_publishing_decision_never_becomes_authority(self):
        decisions = {"market_id": "m", "signed": [{
            "identity_key": "a", "canonical_name": "A", "corridor": "c",
            "founder_decision": enums.HELD_FOR_REVIEW,
            "founder_reviewer_id": "f", "founder_reviewed_at": "d",
            "proposes_authority": enums.PUBLISHED_PET_FRIENDLY,
            "bound_snapshot_hash": "", "bound_semantic_hash": ""}]}
        store = {"records": [{"identity_key": "a", "observation": {}}]}
        built = AUTH.build(decisions, store, {"hotels": []})
        assert built["authority_total"] == 0
        assert "does not publish" in built["unresolved"][0]["why"]


class TestTheCommittedSignature:
    def test_exactly_114_rows_are_signed(self):
        ledger = _load("st_louis_mo_founder_decisions_005.json")
        assert ledger["signed_count"] == 114
        assert ledger["withheld_count"] == 8
        assert ledger["candidates_reviewed"] == 122
        assert len({r["identity_key"] for r in ledger["signed"]}) == 114

    def test_the_split_is_76_pet_friendly_and_38_no_pets(self):
        ledger = _load("st_louis_mo_founder_decisions_005.json")
        assert ledger["signed_by_authority"] == {
            enums.PUBLISHED_PET_FRIENDLY: 76, enums.VERIFIED_NO_PETS: 38}

    def test_the_signature_names_the_founder_and_the_transcriber_apart(self):
        ledger = _load("st_louis_mo_founder_decisions_005.json")
        assert ledger["decided_by"] == "jfields80"
        assert "transcription only" in ledger["recorded_by"]
        assert "claude" in ledger["recorded_by"].lower()
        assert ledger["authorization"]

    def test_the_review_packet_itself_is_still_unsigned(self):
        # The packet is regenerated by an idempotent builder; an attestation
        # living there is one rebuild away from being erased.
        packet = _load("st_louis_mo_founder_review_packet_004.json")
        for row in packet["candidates"]:
            assert row["founder_decision"] == ""
            assert row["founder_reviewer_id"] == ""
            assert row["founder_reviewed_at"] == ""

    def test_the_authority_is_exactly_the_signed_set(self):
        ledger = _load("st_louis_mo_founder_decisions_005.json")
        authority = _load("st_louis_mo_proposed_authority_005.json")
        signed = {r["identity_key"] for r in ledger["signed"]}
        built = ({r["normalized_name"] for r in authority["pet_friendly"]}
                 | {r["normalized_name"] for r in authority["verified_no_pets"]})
        assert built == signed
        assert authority["authority_total"] == 114
        assert authority["unresolved"] == []

    def test_every_authority_row_keeps_its_citations_and_provenance(self):
        authority = _load("st_louis_mo_proposed_authority_005.json")
        for row in authority["pet_friendly"] + authority["verified_no_pets"]:
            assert row["evidence"], row["normalized_name"]
            assert row["snapshot_hash"], row["normalized_name"]
            assert row["source_url"], row["normalized_name"]
            assert row["reader_provenance"], row["normalized_name"]
            assert row["publication_grade"] == "PUBLICATION_GRADE_CONFIRMED"
            assert row["membrane_verdict"] == "VALID"

    def test_withheld_fields_are_carried_forward_never_dropped(self):
        # "Not stated" is a fact about the source. An authority row that loses
        # it is how a blank becomes an implied zero.
        store = _load("st_louis_mo_observation_store_004.json")
        withheld = {r["identity_key"]: r["withheld_fields"]
                    for r in store["records"] if r["withheld_fields"]}
        authority = _load("st_louis_mo_proposed_authority_005.json")
        carried = {r["normalized_name"]: r["withheld_fields"]
                   for r in authority["pet_friendly"] + authority["verified_no_pets"]}
        checked = 0
        for key, fields in withheld.items():
            if key in carried:
                assert carried[key] == fields, key
                checked += 1
        assert checked > 0

    def test_the_market_is_not_registered_by_this_pass(self):
        authority = _load("st_louis_mo_proposed_authority_005.json")
        assert authority["registered"] is False
        assert authority["published"] is False
        assert authority["deployed"] is False

    def test_no_authority_shard_directory_was_created(self):
        # market_authority lists that directory to decide which markets exist
        # and RAISES on a shard whose market has no contract. Creating one
        # would break the global build the deployment manifest pins.
        from pathlib import Path
        shard = Path(PKG) / "markets" / "authority" / "st-louis-mo"
        assert not shard.exists()

    def test_the_eight_unsigned_rows_are_named_with_their_reason(self):
        ledger = _load("st_louis_mo_founder_decisions_005.json")
        assert len(ledger["withheld"]) == 8
        for row in ledger["withheld"]:
            assert row["reviewed_disposition"] in ("HOLD", "APPROVE_WITH_CHANGE")
            assert row["outstanding"]

    def test_everything_still_reconciles_to_357(self):
        closure = _load("st_louis_mo_closure_ledger_004.json")
        ledger = _load("st_louis_mo_founder_decisions_005.json")
        assert closure["count"] == closure["active_denominator"] == 357
        assert closure["reconciliation"]["missing"] == []
        assert closure["reconciliation"]["foreign"] == []
        assert closure["reconciliation"]["duplicate"] == []
        held = closure["disposition_counts"]["HELD_REVIEW"]
        assert held == ledger["signed_count"] + ledger["withheld_count"] == 122
