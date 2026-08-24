"""PTF-MILWAUKEE-SERVICE-ANIMAL-REAUTHORIZE-012 -- the founder's signature.

011 corrected four live profiles and stopped, because GOV-01 says a repair
that moves a record's final ``record_hash`` needs founder re-attestation. This
asserts what the re-attestation actually did: four records signed, none other,
the 036 approval preserved rather than overwritten, and the publication
binding still holding for all seventy-three.
"""

from __future__ import annotations

import copy
import json

import pytest

from scripts.pettripfinder import service_animal_correction_011 as C11
from scripts.pettripfinder import service_animal_reattestation_012 as R12
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import founder_approval as FA
from scripts.pettripfinder.contracts import policy_schema as SCHEMA
from scripts.pettripfinder.contracts import service_animal as SA
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash

FOUR = R12.SIGNED_IDENTITIES


@pytest.fixture(scope="module")
def package():
    return C11.load_package("milwaukee-wi")


@pytest.fixture(scope="module")
def signed(package):
    return {r["identity_key"]: r for r in package["hotels"]
            if r["identity_key"] in FOUR}


@pytest.fixture(scope="module")
def ledger():
    return R12.load_ledger()


# --------------------------------------------------------------------------- #
# Scope: four, and only four.
# --------------------------------------------------------------------------- #

def test_exactly_four_records_carry_this_attestation_in_the_whole_repository():
    carrying = []
    for market_id in C11.market_ids():
        if not C11.package_path(market_id).is_file():
            continue
        for record in C11.load_package(market_id)["hotels"]:
            source = (record.get("approval") or {}).get("decision_source") or {}
            if source.get("work_order") == R12.WORK_ORDER:
                carrying.append((market_id, record["identity_key"]))
    assert carrying == [("milwaukee-wi", key) for key in sorted(FOUR)] or \
        sorted(carrying) == sorted(("milwaukee-wi", k) for k in FOUR)
    assert len(carrying) == 4


def test_the_signed_set_is_the_set_whose_substance_moved():
    report = R12.verify()
    assert report["scope_is_exactly_the_four"]
    assert report["records_outside_the_signed_four_that_moved"] == []
    assert report["records_whose_substance_moved"] == sorted(FOUR)


def test_every_verification_check_still_passes_except_the_replay_guard():
    """Now that the four are signed, exactly one check must fail on each: the
    guard that refuses to sign a record twice. Everything the founder relied
    on -- unchanged evidence, unchanged facts, one moved field, a source that
    states an exemption -- still holds and is re-derived here."""
    report = R12.verify()
    for row in report["rows"]:
        failed = [name for name, ok in row["checks"].items() if not ok]
        assert failed == ["not_already_reattested"], (row["identity_key"], failed)


def test_the_other_sixty_nine_milwaukee_approvals_were_not_touched(package):
    for record in package["hotels"]:
        if record["identity_key"] in FOUR:
            continue
        approval = record["approval"]
        assert "supersedes" not in approval, record["identity_key"]
        assert approval["approval_date"] != R12.DECIDED_AT, record["identity_key"]


# --------------------------------------------------------------------------- #
# What each signature says.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("identity", FOUR)
def test_the_signature_is_canonical_and_the_founders(signed, identity):
    approval = signed[identity]["approval"]
    assert approval["decision"] == FA.CANONICAL_APPROVED
    assert approval["decision"] in FA.WRITABLE
    assert approval["operator"] == R12.FOUNDER == "jfields80"
    assert approval["approval_date"] == R12.DECIDED_AT
    source = approval["decision_source"]
    assert source["work_order"] == R12.WORK_ORDER
    assert source["decided_by"] == R12.FOUNDER
    assert source["ledger"] == "milwaukee_service_animal_reattestation_012.json"


@pytest.mark.parametrize("identity", FOUR)
def test_the_earlier_approval_is_preserved_not_overwritten(signed, identity):
    approval = signed[identity]["approval"]
    prior = approval["supersedes"]
    assert prior["decision"] == FA.CANONICAL_APPROVED
    assert prior["operator"] == "jfields80"
    assert prior["approval_date"] == "2026-08-21"
    assert prior["decision_source"]["work_order"] == \
        "PTF-MILWAUKEE-FOUNDER-DECISION-036"
    # The superseded hash is the one the 036 approval actually described --
    # read from the pre-correction commit, not from the block 011 recomputed.
    assert prior["record_hash"] != approval["record_hash"]
    assert prior["evidence_hash"] == approval["evidence_hash"]


@pytest.mark.parametrize("identity", FOUR)
def test_the_signature_binds_the_corrected_record(signed, identity):
    record = signed[identity]
    approval = record["approval"]
    assert approval["record_hash"] == record_hash(record)
    assert approval["evidence_hash"] == evidence_hash(record["evidence"])
    assert list(SCHEMA.validate_record(record)) == []


@pytest.mark.parametrize("identity", FOUR)
def test_the_signed_record_states_the_corrected_interpretation(signed, identity):
    statement = signed[identity]["service_animal_statement"]
    assert statement["charges_stated"] == enums.SERVICE_ANIMAL_NO_CHARGE
    assert SA.classify(statement["quote"]).interpretation == \
        SA.EXEMPT_FROM_PET_CHARGE
    assert C11.rendered_copy(signed[identity], statement["charges_stated"]) == \
        "The property states that service animals are welcome at no charge."


@pytest.mark.parametrize("identity", FOUR)
def test_the_attestation_terms_are_on_the_record(signed, identity):
    caveats = signed[identity]["approval"]["caveats"]
    for term in R12.ATTESTATION_TERMS:
        assert term in caveats, term
    assert any("GOV-01" in c for c in caveats)
    assert any("supersedes" in c for c in caveats)


@pytest.mark.parametrize("identity", FOUR)
def test_the_original_store_binding_is_kept(signed, identity):
    """publication_042 binds a 036-era approval through these two fields."""
    approval = signed[identity]["approval"]
    assert approval["reviewed_record_hash"].startswith("sha256:")
    assert approval["reviewed_evidence_hash"].startswith("sha256:")


# --------------------------------------------------------------------------- #
# The ledger.
# --------------------------------------------------------------------------- #

def test_the_ledger_records_four_decisions_by_the_founder(ledger):
    assert ledger["decided_by"] == "jfields80"
    assert ledger["decided_at"] == R12.DECIDED_AT
    assert ledger["work_order"] == R12.WORK_ORDER
    assert ledger["applied_to_authority"] is True
    assert len(ledger["decisions"]) == 4
    assert [d["identity_key"] for d in ledger["decisions"]] == list(FOUR)
    assert {d["decision"] for d in ledger["decisions"]} == {R12.LEDGER_DECISION}


def test_the_ledger_quotes_the_authorization_rather_than_summarising_it(ledger):
    source = ledger["authorization_source"]
    assert R12.WORK_ORDER in source
    assert "Sign ONLY" in source
    for identity in FOUR:
        assert identity in source
    assert "No other record may receive a new attestation" in source
    assert "transcription and verification only" in ledger["recorded_by"]


def test_the_ledger_states_every_term_the_founder_attested_to(ledger):
    assert list(ledger["attestation_terms"]) == list(R12.ATTESTATION_TERMS)
    assert any("GOV-01 applies" in line for line in ledger["governance"])


def test_the_ledger_still_describes_the_live_records(ledger, signed):
    for row in ledger["decisions"]:
        record = signed[row["identity_key"]]
        assert row["target_record_hash"] == record_hash(record)
        assert row["target_record_hash"] == record["approval"]["record_hash"]
        assert row["prior_record_hash"] == record["approval"]["supersedes"]["record_hash"]
        assert row["source_quote"] == record["service_animal_statement"]["quote"]
        assert row["prior_value"] == enums.SERVICE_ANIMAL_CHARGE_STATED
        assert row["approved_value"] == enums.SERVICE_ANIMAL_NO_CHARGE
        assert "charge applies" in row["rendered_before"]
        assert "at no charge" in row["rendered_after"]


# --------------------------------------------------------------------------- #
# Refusals.
# --------------------------------------------------------------------------- #

def test_re_running_the_application_is_refused_now_that_it_is_done():
    """A second signature over an already-signed record is not idempotent, it
    is a second attestation, and the verifier refuses rather than writing one."""
    with pytest.raises(R12.ReattestationError):
        R12.assert_verified()


def test_a_record_whose_facts_also_moved_cannot_be_signed():
    before = {"identity_key": "probe", "name": "Probe",
              "facts": {"pets_allowed": True,
                        "pet_fee": {"amount_cents": 5000, "currency": "USD"}},
              "evidence": [],
              "service_animal_statement": {
                  "stated": True,
                  "charges_stated": enums.SERVICE_ANIMAL_CHARGE_STATED,
                  "quote": "Service animals will be exempt from this charge."},
              "approval": {"decision": FA.CANONICAL_APPROVED,
                           "operator": "jfields80"}}
    after = copy.deepcopy(before)
    after["service_animal_statement"]["charges_stated"] = \
        enums.SERVICE_ANIMAL_NO_CHARGE
    after["facts"]["pet_fee"]["amount_cents"] = 7500      # a fee moved too
    row = R12.verify_one("probe", before, after)
    assert row["checks"]["everything_but_the_statement_is_identical"] is False
    assert row["all_checks_pass"] is False


def test_a_record_outside_the_four_cannot_be_signed():
    before = {"identity_key": "somewhere else",
              "service_animal_statement": {
                  "stated": True,
                  "charges_stated": enums.SERVICE_ANIMAL_CHARGE_STATED,
                  "quote": "Service animals are exempt."},
              "approval": {"decision": FA.CANONICAL_APPROVED,
                           "operator": "jfields80"}}
    after = copy.deepcopy(before)
    after["service_animal_statement"]["charges_stated"] = \
        enums.SERVICE_ANIMAL_NO_CHARGE
    row = R12.verify_one("somewhere else", before, after)
    assert row["checks"]["record_is_one_of_the_four"] is False
    assert row["all_checks_pass"] is False


def test_the_publication_gate_still_binds_every_milwaukee_record():
    """Keeping reviewed_record_hash is what makes this true, and it matters:
    042 binds a 036-era approval through that field and nothing else."""
    from scripts.pettripfinder.acquisition import publication_042 as P42
    valid, rejected = P42.validate_pet_friendly()
    assert rejected == []
    assert len(valid) == 73


def test_the_signed_package_still_carries_the_market_unchanged(package):
    assert package["published"] is True
    assert package["publication"]["work_order"] == "PTF-MILWAUKEE-PUBLICATION-042"
    assert package["schema_version"] == "1.2"
    assert len(package["hotels"]) == 73
