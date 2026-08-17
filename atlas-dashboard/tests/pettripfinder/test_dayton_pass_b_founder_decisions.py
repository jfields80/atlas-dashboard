"""PTF-DAYTON-RECERTIFICATION-001 Pass B -- founder decision ledger tests.

Two things must hold, and the second matters more than the first.

A decision must bind the record it was given for. A ruling recorded against a
record that has since moved is a ruling about something the founder never saw,
so every row's hashes are re-checked against the live record here as well as at
recording time.

And recording must not be applying. The whole point of a two-phase flow is that
"the founder decided" and "the authority changed" are separate, auditable
events; a ledger that quietly wrote approvals would collapse them and put a
human's name on a record they had not yet authorised anyone to change.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.dayton_pass_b_founder_decisions import (
    APPROVE, BATCH_A, FOUNDER, HOLD,
)
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / "hotel_policy_facts_dayton-oh.json"
LEDGER_PATH = LP / "dayton_passB_founder_decisions.json"
PACKET_PATH = LP / "dayton_passB_founder_review_packet.json"


@pytest.fixture(scope="module")
def ledger():
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def facts():
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_key(facts):
    return {hotel["identity_key"]: hotel for hotel in facts["hotels"]}


# --------------------------------------------------------------------------- #
# Recording is not applying.
# --------------------------------------------------------------------------- #

def test_no_approval_was_written_to_the_authority(facts):
    """The assertion this file exists for.

    Six APPROVE rulings are on file. Not one of them has been applied, so every
    record -- corrected or not -- is still machine-reviewed and pending, and the
    founder's name appears on no live decision.
    """
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        assert approval["decision"] == enums.MACHINE_REVIEWED_PENDING_OPERATOR
        assert approval["decision"] not in enums.PUBLISHING_DECISIONS
        assert approval["operator"] != FOUNDER
        assert approval["operator"].startswith("claude-")


def test_the_ledger_says_so_in_its_own_fields(ledger):
    assert ledger["status"] == "RECORDED_NOT_APPLIED"
    assert ledger["counts"]["applied"] == 0
    for row in ledger["decisions"]:
        assert row["applied_to_authority"] is False
        assert row["authority_state_now"] == \
            enums.MACHINE_REVIEWED_PENDING_OPERATOR


def test_the_ledger_is_not_the_packet(ledger):
    """A human attestation must not live where a generator can overwrite it."""
    assert LEDGER_PATH != PACKET_PATH
    assert "regeneration can erase" in ledger["why_a_separate_file_from_the_packet"]
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    # The packet remains the machine's question; it carries no ruling.
    for decision in packet["policy_decisions"]:
        assert "founder_decision" not in decision
        assert decision["approval_history"]["bound_by_a_human"] is False


# --------------------------------------------------------------------------- #
# The decisions themselves.
# --------------------------------------------------------------------------- #

def test_batch_a_is_six_approvals_and_no_holds(ledger):
    assert ledger["batch"] == "A"
    assert ledger["counts"] == {"presented": 6, "approved": 6, "held": 0,
                                "applied": 0}
    assert len(ledger["decisions"]) == 6
    assert {r["founder_decision"] for r in ledger["decisions"]} == {APPROVE}
    assert [r["decision_id"] for r in ledger["decisions"]] == \
        ["DAY-B01", "DAY-B02", "DAY-B03", "DAY-B04", "DAY-B05", "DAY-B06"]


def test_every_decision_is_attributed_to_the_founder_who_gave_it(ledger):
    assert ledger["decided_by"] == FOUNDER
    assert "transcription only" in ledger["recorded_by"]
    for row in ledger["decisions"]:
        assert row["decided_by"] == FOUNDER
        assert row["decided_at"] == ledger["decided_at"]


def test_the_declared_decisions_match_the_recorded_ones(ledger):
    """The ledger is a transcription; nothing may appear in it that was not
    given, and nothing given may be dropped."""
    declared = dict(BATCH_A)
    recorded = {r["decision_id"]: r["founder_decision"]
                for r in ledger["decisions"]}
    assert recorded == declared
    assert set(declared.values()) <= {APPROVE, HOLD}


# --------------------------------------------------------------------------- #
# A decision binds the record it was given for.
# --------------------------------------------------------------------------- #

def test_each_decision_still_binds_its_record(ledger, by_key):
    for row in ledger["decisions"]:
        hotel = by_key[row["identity_key"]]
        assert row["bound_record_hash"] == record_hash(hotel), row["decision_id"]
        assert row["bound_evidence_hash"] == evidence_hash(hotel["evidence"]), \
            row["decision_id"]
        # ...and the record's own approval block names the same hashes.
        assert row["bound_record_hash"] == hotel["approval"]["record_hash"]
        assert row["bound_evidence_hash"] == hotel["approval"]["evidence_hash"]
        assert row["hashes_reverified_at_recording"] is True


def test_each_decision_carries_the_change_it_approves(ledger):
    """A ruling with no recorded change would authorise nothing in particular."""
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    presented = {d["decision_id"]: d for d in packet["policy_decisions"]}
    for row in ledger["decisions"]:
        assert row["changes_approved"]
        assert row["changes_approved"] == \
            presented[row["decision_id"]]["changes"]


def test_the_founders_specific_rulings_are_recorded_verbatim(ledger):
    """DAY-B06 came with conditions; an application order must not have to
    infer them."""
    rows = {r["decision_id"]: r for r in ledger["decisions"]}
    notes = rows["DAY-B06"]["decision_notes"]
    assert any("refundable = false" in n for n in notes)
    assert any("tax_relationship = plus_tax" in n for n in notes)
    assert any("Do NOT create $87.94" in n for n in notes)
    assert any("REND-01" in n for n in notes)
    # Every other Batch A row was decided without conditions.
    for decision_id, row in rows.items():
        if decision_id != "DAY-B06":
            assert row["decision_notes"] == []


def test_87_94_was_not_recorded_as_a_charge(ledger, by_key):
    """The founder's condition, checked against the record rather than trusted.

    The approved change adds a tax relationship and a refundability flag to the
    $75 fee. It does not mint the source's arithmetic as a second amount, and
    the record must not contain one.
    """
    courtyard = by_key["courtyard by marriott springfield downtown"]
    fee = courtyard["facts"]["pet_fee"]
    assert fee["amount_cents"] == 7500
    assert fee["tax_relationship"] == enums.TAX_PLUS
    assert fee["refundable"] is False
    assert "8794" not in json.dumps(courtyard["facts"])
    # The sentence containing it survives as evidence, which is where the
    # source's own words belong.
    assert any("87.94" in e["quote"] for e in courtyard["evidence"])


def test_remaining_batches_are_still_outstanding(ledger):
    remaining = ledger["remaining_batches"]
    assert remaining["B_service_animal_and_esa"] == \
        ["DAY-B07", "DAY-B08", "DAY-B09", "DAY-B10", "DAY-B11"]
    assert remaining["C_pointer_repair"] == ["DAY-B12", "DAY-B13"]
    assert remaining["artifact_binding_only_cohort"] == 34
    # 6 decided + 7 outstanding + 34 artifact-only = the whole market.
    assert (len(ledger["decisions"])
            + len(remaining["B_service_animal_and_esa"])
            + len(remaining["C_pointer_repair"])
            + remaining["artifact_binding_only_cohort"]) == 47
