"""PTF-DAYTON-RECERTIFICATION-001 Pass B -- committed-state tests.

Pass B removed monetary prose that defeated a withholding, recorded five
service-animal statements the pages state, aligned four ESA records to the
CEILING != PRICE interpretation, and repaired two fee-scope pointers. These
tests pin what it produced and, just as importantly, what it did not touch.

The assertion this file exists for is the negative one: a correction pass gets
its authority from being narrow, so "the other thirty-four records did not move"
is the claim that has to hold, and it is checked against hashes rather than
against intent.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as evidence_contract
from scripts.pettripfinder.contracts import policy_schema
from scripts.pettripfinder.dayton_pass_b_policy_corrections import (
    AGENT_IDENTITY, CORRECTIONS,
)
from scripts.pettripfinder.policy_migration import (
    evidence_hash, evidence_ref_for, record_hash,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / "hotel_policy_facts_dayton-oh.json"
PACKET_PATH = LP / "dayton_passB_founder_review_packet.json"
PASS_A_PACKET = LP / "dayton_passA_reauth_packet.json"
CENSUS_PATH = LP / "identity_census" / "dayton-oh.json"
CONTRACT_PATH = (REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / "dayton-oh.json")

CORRECTED = set(CORRECTIONS)
ESA = {
    "extended stay america suites dayton fairborn",
    "extended stay america suites dayton south",
    "extended stay america suites dayton north",
    "extended stay america select suites dayton miamisburg",
}
LA_QUINTA = {
    "la quinta inn and suites by wyndham fairborn wright patterson",
    "la quinta inn and suites by wyndham miamisburg dayton south",
}


@pytest.fixture(scope="module")
def facts():
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_key(facts):
    return {hotel["identity_key"]: hotel for hotel in facts["hotels"]}


@pytest.fixture(scope="module")
def packet():
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Scope: exactly thirteen records, and no others.
# --------------------------------------------------------------------------- #

def test_exactly_thirteen_records_were_corrected(packet):
    assert len(CORRECTED) == 13
    assert packet["reconciliation"] == {
        "published_records": 47,
        "policy_decisions_required": 13,
        "artifact_binding_only_reattestations": 34,
        "total_founder_actions": 47,
    }


def test_the_other_thirty_four_records_did_not_move(facts, packet):
    """Checked against the hashes Pass A left, not against intent."""
    pass_a = {row["identity_key"]: row for row in
              json.loads(PASS_A_PACKET.read_text(encoding="utf-8"))["records"]}
    cohort = {row["identity_key"] for row in
              packet["artifact_binding_only_reattestation"]["records"]}
    assert len(cohort) == 34
    assert cohort & CORRECTED == set()
    for hotel in facts["hotels"]:
        key = hotel["identity_key"]
        if key in CORRECTED:
            continue
        assert hotel["approval"]["record_hash"] == \
            pass_a[key]["record_hash_to_attest"], key
        assert hotel["approval"]["evidence_hash"] == \
            pass_a[key]["evidence_hash_unchanged"], key


def test_no_record_lost_its_publication_grade(facts):
    for hotel in facts["hotels"]:
        assert not evidence_contract.validate(hotel)
        assert not evidence_contract.publication_blockers(hotel)
        assert not policy_schema.validate_record(hotel)
        for entry in hotel["evidence"]:
            assert entry["artifact_class"] == enums.PUBLICATION_GRADE_EVIDENCE
            assert entry["evidence_ref"] == evidence_ref_for(entry)


# --------------------------------------------------------------------------- #
# Group A + B: the monetary leak is gone, the facts inside it are not.
# --------------------------------------------------------------------------- #

def test_no_published_restriction_field_carries_money(facts):
    """The rule Group A enforces, asserted over the WHOLE market.

    Not just the six records the audit named: a leak anywhere in Dayton would
    defeat a withholding just as effectively, and pinning only the known six
    would let the seventh through.
    """
    for hotel in facts["hotels"]:
        for field in ("general_restrictions", "breed_restrictions",
                      "unattended_policy", "reservation_requirement"):
            stated = hotel["facts"].get(field)
            if not stated:
                continue
            assert "$" not in stated, (hotel["identity_key"], field)
            assert "USD" not in stated, (hotel["identity_key"], field)


def test_group_a_kept_genuine_restrictions_and_dropped_the_rest(by_key):
    assert by_key["springhill suites troy dayton"]["facts"][
        "general_restrictions"] == "Dogs only, no cats."
    assert by_key["hilton garden inn dayton beavercreek"]["facts"][
        "general_restrictions"] == "dogs & cats only. Two pets max per room."
    # Wholly monetary, or wholly a truncation the record already withholds:
    # nothing survives trimming, so the field goes.
    for key in ("towneplace suites by marriott dayton beavercreek",
                "home2 suites by hilton dayton beavercreek",
                "staybridge suites miamisburg",
                "courtyard by marriott springfield downtown"):
        assert "general_restrictions" not in by_key[key]["facts"], key


def test_the_withheld_amounts_are_no_longer_published_anywhere(by_key):
    """The specific numbers each record decided it could not publish."""
    leaked = {
        "springhill suites troy dayton": ("75", "150", "250"),
        "towneplace suites by marriott dayton beavercreek": ("100", "20"),
        "hilton garden inn dayton beavercreek": ("75",),
        "home2 suites by hilton dayton beavercreek": ("125",),
    }
    for key, amounts in leaked.items():
        published = json.dumps(by_key[key]["facts"])
        for amount in amounts:
            assert "$%s" % amount not in published, (key, amount)


def test_group_b_moved_stated_facts_into_canonical_fields(by_key):
    """Deleting prose must never delete a fact the prose carried."""
    staybridge = by_key["staybridge suites miamisburg"]["facts"]
    assert staybridge["pet_fee"]["refundable"] is False
    assert len(staybridge["fee_tiers"]) == 2          # ladder untouched

    courtyard = by_key["courtyard by marriott springfield downtown"]["facts"]
    assert courtyard["pet_fee"]["amount_cents"] == 7500
    assert courtyard["pet_fee"]["basis"] == enums.BASIS_PER_STAY
    assert courtyard["pet_fee"]["tax_relationship"] == enums.TAX_PLUS
    assert courtyard["pet_fee"]["refundable"] is False
    # The source's own arithmetic never becomes a second charge.
    assert "8794" not in json.dumps(courtyard)


# --------------------------------------------------------------------------- #
# Group C: service-animal statements.
# --------------------------------------------------------------------------- #

def test_five_service_animal_statements_were_added(by_key):
    added = {"days inn by wyndham sidney"} | ESA
    for key in added:
        record = by_key[key]
        statement = record["service_animal_statement"]
        assert statement == {"stated": True, "charges_stated": "no_charge"}
        # A legal access category never enters the pet-policy facts block.
        assert "service_animal_statement" not in record["facts"]
        quoted = [e for e in record["evidence"]
                  if e["field"] == "service_animal_exception"]
        assert len(quoted) == 1, key
        assert quoted[0]["artifact_class"] == enums.PUBLICATION_GRADE_EVIDENCE
    assert by_key["days inn by wyndham sidney"]["evidence"][-1]["quote"] == \
        ("Service Animals - ADA-defined service animals are welcome free of "
         "charge.")


def test_nothing_broader_than_the_source_was_claimed(by_key):
    """"Exempt from this charge" addresses the pet charge and nothing else."""
    for key in ESA:
        statement = by_key[key]["service_animal_statement"]
        assert statement["charges_stated"] == enums.SERVICE_ANIMAL_NO_CHARGE
        assert set(statement) == {"stated", "charges_stated"}


# --------------------------------------------------------------------------- #
# ESA ceiling: CEILING != PRICE, on Cleveland's interpretation.
# --------------------------------------------------------------------------- #

def test_esa_publishes_no_price_and_says_why(by_key):
    for key in ESA:
        record = by_key[key]
        assert "pet_fee" not in record["facts"], key
        assert "fee_tiers" not in record["facts"], key
        withheld = record["withheld_fields"]
        for field in ("pet_fee", "cleaning_fee"):
            assert withheld[field]["reason_code"] == \
                enums.SCHEMA_CANNOT_REPRESENT, (key, field)
            assert "CEILING != PRICE" in withheld["pet_fee"]["reason"]
        # No ceiling figure reaches the published facts.
        published = json.dumps(record["facts"])
        assert "2500" not in published and "1500" not in published


def test_esa_retains_both_exact_ceiling_sentences(by_key):
    """Cleveland's rule: the exact sentence is retained in the evidence array.

    Dayton retained neither, so a charge the page states appeared nowhere in
    the record at all.
    """
    for key in ESA:
        quotes = {e["quote"] for e in by_key[key]["evidence"]
                  if e["field"] == "cleaning_fee"}
        assert quotes == {
            "Pet fees: Not to exceed a $25.00 per day cleaning fee plus tax, "
            "for the first six (6) nights, per pet.",
            "Each day thereafter there is a pet cleaning fee not to exceed a "
            "$15.00 per day plus tax, per pet.",
        }, key


# --------------------------------------------------------------------------- #
# Group D: pointer repairs change a pointer and nothing else.
# --------------------------------------------------------------------------- #

def test_la_quinta_gained_a_pointer_and_no_fact_moved(by_key):
    for key in LA_QUINTA:
        record = by_key[key]
        fee = record["facts"]["pet_fee"]
        assert fee["scope"] == enums.SCOPE_PER_ROOM
        assert fee["scope_pet_allowance"] == 2
        assert fee["amount_cents"] == 2500
        pointer = [e for e in record["evidence"] if e["field"] == "fee_scope"]
        assert len(pointer) == 1, key
        # The pointer cites the property's own sentence, already in the record.
        assert pointer[0]["quote"] == (
            "Fees - Non-refundable 25 USD nightly for up to 2 pets. "
            "Max 75 USD per stay.")
        assert pointer[0]["quote"] in {e["quote"] for e in record["evidence"]
                                       if e["field"] == "pet_fee"}


# --------------------------------------------------------------------------- #
# Doctrine: silence is absence.
# --------------------------------------------------------------------------- #

def test_no_withholding_was_invented_for_a_silent_source(facts):
    for hotel in facts["hotels"]:
        for field, decision in (hotel.get("withheld_fields") or {}).items():
            assert decision["reason_code"] in enums.WITHHELD_FIELD_REASONS
            assert decision["reason_code"] != enums.SOURCE_SILENT
            assert decision["reason"].strip()
            assert decision["evidence_refs"]
            # A withheld field is never also published.
            assert field not in hotel["facts"], (hotel["identity_key"], field)


# --------------------------------------------------------------------------- #
# Governance.
# --------------------------------------------------------------------------- #

def test_no_approval_was_written_without_a_recorded_decision(facts):
    """Pass B wrote no approval; Pass C wrote 47, each from a recorded ruling.

    The claim that survives both is the one worth testing: a live founder
    approval exists only where the founder actually decided, and it binds the
    record it signs.
    """
    ledger = json.loads(
        (LP / "dayton_passB_founder_decisions.json").read_text(encoding="utf-8"))
    decided = {r["identity_key"] for r in ledger["decisions"]}
    decided |= {r["identity_key"] for r in
                ledger["artifact_only_cohort_decision"]["records"]}
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        assert approval["record_hash"] == record_hash(hotel)
        assert approval["evidence_hash"] == evidence_hash(hotel["evidence"])
        if approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW:
            assert approval["operator"] == "jfields80"
            assert hotel["identity_key"] in decided, hotel["identity_key"]
        else:
            assert approval["operator"] != "jfields80"


def test_the_founder_stayed_the_preserved_prior(by_key):
    """No machine approval was ever nested into a supersedes chain.

    Pass B superseded Pass A's machine block and Pass C superseded Pass B's, and
    at no point did either become the "prior" -- which would put an agent's name
    exactly where a reader looks for the last human decision.
    """
    for key in CORRECTED:
        approval = by_key[key]["approval"]
        prior = approval["supersedes"]
        assert prior["operator"] == "jfields80"
        assert prior["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert prior["record_hash"] != approval["record_hash"]
        assert "claude" not in json.dumps(prior).lower()


def test_packet_binds_decisions_to_final_hashes(facts, packet, by_key):
    decisions = packet["policy_decisions"]
    assert len(decisions) == 13
    assert {d["identity_key"] for d in decisions} == CORRECTED
    for decision in decisions:
        hotel = by_key[decision["identity_key"]]
        assert decision["final_record_hash"] == hotel["approval"]["record_hash"]
        assert decision["final_evidence_hash"] == \
            hotel["approval"]["evidence_hash"]
        assert decision["recommendation"] in ("APPROVE_CORRECTED_RECORD", "HOLD")
        assert decision["approval_history"]["bound_by_a_human"] is False
        assert decision["changes"]
        assert decision["rationale"].strip()


def test_batches_cover_every_decision_exactly_once(packet):
    batches = packet["batches"]
    seen = [d for batch in batches.values() for d in batch]
    assert sorted(seen) == sorted(
        d["decision_id"] for d in packet["policy_decisions"])
    assert len(seen) == len(set(seen)) == 13
    assert len(batches["A_monetary"]) == 6
    assert len(batches["B_service_animal_and_esa"]) == 5
    assert len(batches["C_pointer_repair"]) == 2


# --------------------------------------------------------------------------- #
# Census hygiene stays out of the policy lane.
# --------------------------------------------------------------------------- #

def test_census_was_not_touched_by_a_policy_pass(packet):
    section = packet["census_hygiene_tracked_separately"]
    assert section["status"] == "PROPOSED_NOT_APPLIED"
    assert section["is_a_policy_decision"] is False
    assert section["founder_action_required"] is False
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    by_row = {row["identity_key"]: row for row in census["hotels"]}
    assert by_row["best western celina"]["policy_state"] == "POLICY_NOT_VERIFIED"
    assert census["no_pets_count"] == 7


# --------------------------------------------------------------------------- #
# Release contract.
# --------------------------------------------------------------------------- #

def test_release_contract_pins_the_current_package(packet):
    """The pin always names the CURRENT bytes; each pass re-pins what it left.

    Pass B's sha became history when Pass C applied the founder's approvals, so
    an assertion still pointed at it would have stopped checking the live pin.
    """
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    actual = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest()
    assert contract["policy_package"]["expected_sha256"] == actual
    assert packet["facts_sha256_before"] != actual
    assert packet["facts_sha256_after"] != actual   # superseded by Pass C
    raw = FACTS_PATH.read_bytes()
    assert b"\r\n" not in raw and raw.endswith(b"\n")
