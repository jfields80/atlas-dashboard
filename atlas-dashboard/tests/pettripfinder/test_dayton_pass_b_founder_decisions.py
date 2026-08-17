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
    APPROVE, DECISIONS, FOLLOW_UPS, FOUNDER, HOLD, PACKET_BATCH_KEYS,
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

def test_recording_and_applying_stayed_separate_events(facts, ledger):
    """The assertion this file exists for.

    The ledger records decisions; it never writes approvals. It still says
    ``applied_to_authority: false`` on every row, because THAT was true of the
    recording -- Pass C applied them afterwards as its own auditable event. A
    ledger that had written the approvals itself would have collapsed the two.
    """
    assert ledger["status"] == "RECORDED_NOT_APPLIED"
    assert ledger["counts"]["applied"] == 0
    for row in ledger["decisions"]:
        assert row["applied_to_authority"] is False
    # ...and every live approval traces to a decision this ledger recorded.
    decided = {r["identity_key"] for r in ledger["decisions"]}
    decided |= {r["identity_key"] for r in
                ledger["artifact_only_cohort_decision"]["records"]}
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        if approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW:
            assert approval["operator"] == FOUNDER
            assert hotel["identity_key"] in decided


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

def test_all_thirteen_policy_decisions_are_recorded_and_approved(ledger):
    assert ledger["batches_recorded"] == ["A", "B", "C"]
    assert ledger["counts"] == {"presented": 13, "approved": 13, "held": 0,
                                "applied": 0}
    assert len(ledger["decisions"]) == 13
    assert {r["founder_decision"] for r in ledger["decisions"]} == {APPROVE}
    assert [r["decision_id"] for r in ledger["decisions"]] == [
        "DAY-B01", "DAY-B02", "DAY-B03", "DAY-B04", "DAY-B05", "DAY-B06",
        "DAY-B07", "DAY-B08", "DAY-B09", "DAY-B10", "DAY-B11",
        "DAY-B12", "DAY-B13"]
    assert ledger["counts_by_batch"]["A"]["approved"] == 6
    assert ledger["counts_by_batch"]["B"]["approved"] == 5
    assert ledger["counts_by_batch"]["C"]["approved"] == 2


def test_a_batch_is_recorded_whole_or_not_at_all(ledger):
    """A partial batch would leave records looking undecided when they had
    simply been dropped from the transcription."""
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    for batch, given in DECISIONS.items():
        asked = set(packet["batches"][PACKET_BATCH_KEYS[batch]])
        answered = {decision_id for decision_id, _ in given}
        assert answered == asked, batch
        recorded = {r["decision_id"] for r in ledger["decisions"]
                    if r["batch"] == batch}
        assert recorded == asked, batch


def test_a_later_batch_never_disturbed_an_earlier_one(ledger):
    """The ledger is rebuilt whole on every run, so an earlier batch must
    survive a later one -- which it can only do while its records have not
    moved."""
    for batch, size in (("A", 6), ("B", 5), ("C", 2)):
        rows = [r for r in ledger["decisions"] if r["batch"] == batch]
        assert len(rows) == size, batch
        for row in rows:
            assert row["founder_decision"] == APPROVE
            assert row["decided_at"] == ledger["decided_at"]
            assert row["applied_to_authority"] is False
    notes = {r["decision_id"]: r["decision_notes"] for r in ledger["decisions"]}
    assert any("Do NOT create $87.94" in n for n in notes["DAY-B06"])


def test_every_decision_is_attributed_to_the_founder_who_gave_it(ledger):
    assert ledger["decided_by"] == FOUNDER
    assert "transcription only" in ledger["recorded_by"]
    for row in ledger["decisions"]:
        assert row["decided_by"] == FOUNDER
        assert row["decided_at"] == ledger["decided_at"]


def test_the_declared_decisions_match_the_recorded_ones(ledger):
    """The ledger is a transcription; nothing may appear in it that was not
    given, and nothing given may be dropped."""
    declared = {decision_id: ruling
                for given in DECISIONS.values()
                for decision_id, ruling in given}
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
    # Batch B came with conditions on every row, and they are recorded too.
    assert any("free of charge" in n for n in rows["DAY-B07"]["decision_notes"])
    assert any("Do not broaden this" in n
               for n in rows["DAY-B07"]["decision_notes"])
    for decision_id in ("DAY-B08", "DAY-B09", "DAY-B10", "DAY-B11"):
        notes = " ".join(rows[decision_id]["decision_notes"])
        assert "SCHEMA_CANNOT_REPRESENT" in notes or "DAY-B08" in notes
        assert "CEILING != PRICE" in notes or "exact" in notes.lower()
    # The rest of Batch A was decided without conditions; recording a note
    # nobody gave would be inventing a ruling.
    for decision_id in ("DAY-B01", "DAY-B02", "DAY-B03", "DAY-B04", "DAY-B05"):
        assert rows[decision_id]["decision_notes"] == []


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


def test_nothing_is_outstanding_and_the_market_reconciles(ledger):
    """Every published record now has a founder decision recorded against it.

    The cohort left ``still_outstanding`` when the founder ruled on it, which
    is the point: the field lists what is un-decided, so an empty one is the
    claim that nothing is.
    """
    assert ledger["still_outstanding"] == {}
    cohort = ledger["artifact_only_cohort_decision"]
    assert cohort["decision"] == "APPROVE_ARTIFACT_BINDING_ONLY_REATTESTATION"
    assert cohort["cohort_size"] == 34
    # 13 policy decisions + 34 artifact-only = the whole market.
    assert len(ledger["decisions"]) + cohort["cohort_size"] == 47
    assert cohort["applied_to_authority"] is False
    assert all(r["applied_to_authority"] is False for r in cohort["records"])


def test_the_cohort_decision_records_the_grounds_it_rests_on(ledger):
    """The founder made the BLOCK form conditional on the verifier's proof, so
    the grounds are part of the decision rather than context around it."""
    cohort = ledger["artifact_only_cohort_decision"]
    grounds = cohort["approved_on_the_basis_that_the_verifier_proves"]
    for required in ("facts unchanged", "quotes unchanged",
                     "evidence_hash unchanged", "withheld_fields unchanged",
                     "service_animal_statement unchanged",
                     "evidence set unchanged"):
        assert any(required in g for g in grounds), required
    assert any("no policy correction hidden" in g for g in grounds)
    governance = " ".join(cohort["governance"])
    assert "GOV-01 applies" in governance
    assert "NOT permission to use block approval for mixed" in governance
    assert "STOP for that record" in governance
    assert cohort["policy_corrections_hidden_in_the_cohort"] == 0
    assert cohort["verifier_baseline_ref"] == "d14cdc4"


def test_no_cohort_record_is_also_a_policy_decision(ledger):
    """Zero overlap and zero omission, exactly as the founder scoped it."""
    cohort = {r["identity_key"] for r in
              ledger["artifact_only_cohort_decision"]["records"]}
    policy = {r["identity_key"] for r in ledger["decisions"]}
    assert len(cohort) == 34 and len(policy) == 13
    assert cohort & policy == set()
    assert len(cohort | policy) == 47


def test_the_governance_ruling_was_recorded(ledger):
    """A principle given in passing during a batch review is exactly what
    evaporates when the conversation ends, and this one governs every market
    that follows."""
    rulings = {g["id"]: g for g in ledger["governance_rulings"]}
    assert set(rulings) == {"GOV-01"}
    gov = rulings["GOV-01"]
    assert gov["ruled_by"] == FOUNDER
    assert "re-attestation" in gov["rule"]
    assert "evidentiary basis" in gov["reason"]
    assert "future markets" in gov["scope"]
    assert gov["first_applied_to"] == ["DAY-B12", "DAY-B13"]


def test_the_governance_ruling_reached_the_contract_it_names():
    """The founder scoped GOV-01 to the evidence contract, so the contract is
    where the next market has to be able to find it."""
    source = (REPO_ROOT / "scripts" / "pettripfinder" / "contracts"
              / "evidence.py").read_text(encoding="utf-8")
    assert "GOV-01" in source
    assert "citation-only" in source
    assert "evidence-pointer repair DOES require founder" in source


def test_batch_c_changed_a_pointer_and_nothing_else(ledger, by_key):
    """The decisions that prompted GOV-01: no fact moved, only the citation."""
    rows = {r["decision_id"]: r for r in ledger["decisions"]}
    for decision_id in ("DAY-B12", "DAY-B13"):
        row = rows[decision_id]
        assert all(c["kind"] == "EVIDENCE_ADDED" for c in row["changes_approved"])
        assert [c["field"] for c in row["changes_approved"]] == ["fee_scope"]
        record = by_key[row["identity_key"]]
        fee = record["facts"]["pet_fee"]
        assert fee["scope"] == enums.SCOPE_PER_ROOM
        assert fee["scope_pet_allowance"] == 2
        assert fee["amount_cents"] == 2500
        assert record["facts"]["fee_cap"]["amount_cents"] == 7500
        assert record["facts"]["fee_cap"]["qualifier_stated"] is True
        pointer = [e for e in record["evidence"] if e["field"] == "fee_scope"]
        assert len(pointer) == 1


# --------------------------------------------------------------------------- #
# Batch B specifics.
# --------------------------------------------------------------------------- #

ESA_DECISIONS = ("DAY-B08", "DAY-B09", "DAY-B10", "DAY-B11")


def test_the_esa_ceiling_ruling_is_recorded_on_every_esa_record(ledger, by_key):
    """CEILING != PRICE, checked against the records and not just the notes."""
    rows = {r["decision_id"]: r for r in ledger["decisions"]}
    for decision_id in ESA_DECISIONS:
        record = by_key[rows[decision_id]["identity_key"]]
        withheld = record["withheld_fields"]
        assert withheld["pet_fee"]["reason_code"] == \
            enums.SCHEMA_CANNOT_REPRESENT
        assert withheld["cleaning_fee"]["reason_code"] == \
            enums.SCHEMA_CANNOT_REPRESENT
        # No ceiling figure became a published price.
        published = json.dumps(record["facts"])
        assert "2500" not in published and "1500" not in published
        assert "pet_fee" not in record["facts"]
        # Both exact sentences are retained where source wording belongs.
        ceilings = {e["quote"] for e in record["evidence"]
                    if e["field"] == "cleaning_fee"}
        assert len(ceilings) == 2


def test_the_service_animal_mapping_was_not_broadened(ledger, by_key):
    rows = {r["decision_id"]: r for r in ledger["decisions"]}
    for decision_id in ("DAY-B07",) + ESA_DECISIONS:
        record = by_key[rows[decision_id]["identity_key"]]
        statement = record["service_animal_statement"]
        assert statement == {"stated": True, "charges_stated": "no_charge"}
        assert set(statement) == {"stated", "charges_stated"}
        # A legal access category never enters the pet-policy facts block.
        assert "service_animal_statement" not in record["facts"]


def test_the_cleveland_asymmetry_was_recorded_not_acted_on(ledger):
    """A recommendation given during a decision must not evaporate -- and must
    not turn into an edit nobody authorised."""
    follow_ups = {f["id"]: f for f in ledger["follow_ups"]}
    assert len(FOLLOW_UPS) == len(follow_ups) == 1
    entry = follow_ups["FU-01"]
    assert entry["cleveland_touched_by_this_order"] is False
    assert "not block" in entry["founder_ruling"].lower()
    assert len(entry["records"]) == 2
    assert all(r.startswith("cleveland-akron-canton-oh /")
               for r in entry["records"])


def test_this_order_changed_no_cleveland_record():
    """Asserted against Cleveland's own package, not against intent."""
    cleveland = json.loads(
        (LP / "hotel_policy_facts_cleveland-akron-canton-oh.json")
        .read_text(encoding="utf-8"))
    esa = [h for h in cleveland["hotels"]
           if "extended stay" in h["identity_key"]]
    assert len(esa) == 2
    for record in esa:
        # Still exactly as the follow-up describes: no statement, no quote.
        assert record.get("service_animal_statement") is None
        assert not any("service animal" in e["quote"].lower()
                       for e in record["evidence"])
