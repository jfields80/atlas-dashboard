"""PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 -- the live correction itself.

``test_service_animal.py`` holds the rule. This holds what the rule did to the
committed markets: which records moved, that nothing else did, and that no
live profile anywhere still says a charge applies to a service animal when its
own source says the opposite.
"""

from __future__ import annotations

import copy

import pytest

from scripts.pettripfinder import service_animal_correction_011 as C
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import policy_schema as SCHEMA
from scripts.pettripfinder.contracts import service_animal as SA

#: The four Milwaukee profiles that published the false statement.
DEFECTIVE_IDENTITIES = (
    "avid hotels oak creek",
    "extended stay america milwaukee waukesha",
    "extended stay america milwaukee wauwatosa",
    "the pfister hotel",
)


@pytest.fixture(scope="module")
def rows():
    return C.findings()


# --------------------------------------------------------------------------- #
# The committed state, after the correction.
# --------------------------------------------------------------------------- #

def test_no_committed_record_still_disagrees_with_its_own_source(rows):
    """The correction is complete: re-deriving today changes nothing."""
    assert [r["identity_key"] for r in rows if r["verdict"] == C.CORRECTED] == []


def test_the_four_defective_profiles_now_state_no_charge():
    package = C.load_package("milwaukee-wi")
    found = {r["identity_key"]: r for r in package["hotels"]}
    for identity in DEFECTIVE_IDENTITIES:
        statement = found[identity]["service_animal_statement"]
        assert statement["charges_stated"] == enums.SERVICE_ANIMAL_NO_CHARGE
        assert SA.classify(statement["quote"]).interpretation == \
            SA.EXEMPT_FROM_PET_CHARGE


def test_no_live_record_in_any_market_claims_a_charge_on_a_quote(rows):
    """No published statement says "a charge applies" over exemption words."""
    claiming = [r for r in rows
                if r["published_charges_stated"]
                == enums.SERVICE_ANIMAL_CHARGE_STATED]
    assert claiming == [], claiming


def test_the_corrected_profiles_render_the_corrected_sentence():
    package = C.load_package("milwaukee-wi")
    found = {r["identity_key"]: r for r in package["hotels"]}
    for identity in DEFECTIVE_IDENTITIES:
        record = found[identity]
        copy_now = C.rendered_copy(
            record, record["service_animal_statement"]["charges_stated"])
        assert copy_now == ("The property states that service animals are "
                            "welcome at no charge.")
        assert "charge applies" not in copy_now


#: Records that already failed schema validation before this work order ran,
#: all in the market the founder withdrew from launch. Pinned by name so the
#: assertion below is "nothing NEW broke" and not "nothing is broken".
PREEXISTING_SCHEMA_FAILURES = {
    ("indianapolis-in", "le meridien indianapolis"),
    ("indianapolis-in", "residence inn by marriott indianapolis airport"),
    ("indianapolis-in", "hampton inn and suites indianapolis keystone"),
    ("indianapolis-in", "hampton inn and suites indianapolis west speedway"),
    ("indianapolis-in", "hilton garden inn indianapolis airport"),
}


def test_no_committed_record_newly_fails_schema_validation():
    failing = set()
    for market_id in C.market_ids():
        if not C.package_path(market_id).is_file():
            continue
        for record in C.load_package(market_id)["hotels"]:
            if list(SCHEMA.validate_record(record)):
                failing.add((market_id, record["identity_key"]))
    assert failing == PREEXISTING_SCHEMA_FAILURES


def test_every_corrected_record_validates():
    package = C.load_package("milwaukee-wi")
    found = {r["identity_key"]: r for r in package["hotels"]}
    for identity in DEFECTIVE_IDENTITIES:
        assert list(SCHEMA.validate_record(found[identity])) == []


# --------------------------------------------------------------------------- #
# What the correction refused to touch.
# --------------------------------------------------------------------------- #

def test_a_statement_with_no_quote_is_never_reclassified(rows):
    """A founder decision is not overwritten by a reading of the empty string."""
    untouched = [r for r in rows if r["verdict"] == C.NO_QUOTE]
    assert untouched, "the corpus must still exercise this branch"
    for row in untouched:
        assert row["published_charges_stated"] in enums.SERVICE_ANIMAL_CHARGE_STATES
        assert "derived_charges_stated" not in row


def test_correct_record_refuses_to_move_anything_else():
    record = {
        "identity_key": "probe",
        "facts": {"pets_allowed": True, "pet_fee": {"amount_cents": 5000,
                                                    "currency": "USD"}},
        "service_animal_statement": {
            "stated": True,
            "charges_stated": enums.SERVICE_ANIMAL_CHARGE_STATED,
            "quote": "Service animals will be exempt from this charge."},
        "approval": {"decision": "APPROVED_AFTER_CURRENT_REVIEW",
                     "operator": "jfields80",
                     "record_hash": "sha256:stale",
                     "conversion_notes": []},
    }
    before = copy.deepcopy(record)
    C.correct_record(record, enums.SERVICE_ANIMAL_NO_CHARGE)

    assert record["facts"] == before["facts"]
    assert record["service_animal_statement"]["quote"] == \
        before["service_animal_statement"]["quote"]
    assert record["service_animal_statement"]["stated"] is True
    assert record["service_animal_statement"]["charges_stated"] == \
        enums.SERVICE_ANIMAL_NO_CHARGE


def test_the_founder_decision_fields_are_never_rewritten():
    record = {
        "identity_key": "probe",
        "facts": {"pets_allowed": True},
        "service_animal_statement": {
            "stated": True,
            "charges_stated": enums.SERVICE_ANIMAL_CHARGE_STATED,
            "quote": "Service animals are permitted, without charge."},
        "approval": {"decision": "APPROVED_AFTER_CURRENT_REVIEW",
                     "operator": "jfields80",
                     "approval_date": "2026-08-21",
                     "decision_source": {"kind": "FOUNDER_DECISION"},
                     "evidence_hash": "sha256:e",
                     "reviewed_record_hash": "sha256:r",
                     "reviewed_evidence_hash": "sha256:re",
                     "record_hash": "sha256:stale",
                     "conversion_notes": []},
    }
    before = copy.deepcopy(record["approval"])
    C.correct_record(record, enums.SERVICE_ANIMAL_NO_CHARGE)

    for field in C.FROZEN_APPROVAL_FIELDS:
        assert record["approval"].get(field) == before.get(field), field
    # The checksum of the record IS recomputed -- a stored hash that no longer
    # describes its record is a silent integrity break -- and says so.
    assert record["approval"]["record_hash"] != before["record_hash"]
    note = record["approval"]["conversion_notes"][-1]
    assert C.WORK_ORDER in note
    assert "GOV-01" in note
    assert "sha256:stale" in note


def test_a_corrected_record_carries_exactly_one_new_note():
    package = C.load_package("milwaukee-wi")
    found = {r["identity_key"]: r for r in package["hotels"]}
    for identity in DEFECTIVE_IDENTITIES:
        notes = found[identity]["approval"]["conversion_notes"]
        stamped = [n for n in notes if C.WORK_ORDER in n]
        assert len(stamped) == 1, identity
        assert "charge_stated" in stamped[0] and "no_charge" in stamped[0]


def test_the_published_flag_and_publication_block_are_untouched():
    """A correction must never publish or unpublish a market as a side effect."""
    package = C.load_package("milwaukee-wi")
    assert package["published"] is True
    assert package["publication"]["work_order"] == "PTF-MILWAUKEE-PUBLICATION-042"
    assert package["publication"]["deployed"] is False
    assert package["schema_version"] == "1.2"
    assert len(package["hotels"]) == 73


def test_re_running_the_correction_writes_nothing():
    """Idempotent by derivation, so a rebuild cannot drift the package hash."""
    for market_id in C.market_ids():
        if not C.package_path(market_id).is_file():
            continue
        result = C.apply_market(market_id, apply=False)
        assert result["sha256_before"] == result["sha256_after"], market_id
        assert result["corrected"] == 0, market_id


# --------------------------------------------------------------------------- #
# The correction is the canonical pipeline's own answer.
# --------------------------------------------------------------------------- #

def test_the_store_and_the_published_quote_agree_through_036():
    agreement = C.milwaukee_pipeline_agreement()
    if not agreement.get("available"):                # pragma: no cover
        pytest.skip("the acquisition store is not present in this checkout")
    assert agreement["records_checked"] > 0
    assert agreement["disagreements"] == []
