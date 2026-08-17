"""PTF-DAYTON-RECERTIFICATION-001 -- the artifact-only cohort, verified.

Thirty-four records go to the founder as ONE block decision. The risk of any
block decision is that something real hides inside it, so these tests check the
claim rather than the summary: the committed report must say all 34 are
artifact-only, and the records themselves must independently agree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.dayton_artifact_cohort_verification import (
    ARTIFACT_BINDING_KEYS, verify_record,
)
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / "hotel_policy_facts_dayton-oh.json"
REPORT_PATH = LP / "dayton_artifact_cohort_verification.json"
PACKET_PATH = LP / "dayton_passB_founder_review_packet.json"
LEDGER_PATH = LP / "dayton_passB_founder_decisions.json"

COHORT_SIZE = 34
DECIDED = 13


@pytest.fixture(scope="module")
def report():
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_key():
    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    return {h["identity_key"]: h for h in facts["hotels"]}


def test_the_whole_cohort_is_artifact_only(report):
    assert report["cohort_size"] == COHORT_SIZE
    assert report["verdicts"] == {"ARTIFACT_BINDING_ONLY": COHORT_SIZE,
                                  "NOT_ARTIFACT_ONLY": 0}
    assert report["policy_corrections_hidden_in_the_cohort"] == 0
    for row in report["records"]:
        assert row["verdict"] == "ARTIFACT_BINDING_ONLY"
        assert row["failures"] == []


def test_each_of_the_founders_five_conditions_holds_on_all(report):
    """Named one by one, because a single aggregate boolean is easy to satisfy
    accidentally and hard to read as a promise."""
    assert report["facts_unchanged_on_all"] is True
    assert report["quotes_unchanged_on_all"] is True
    assert report["withholding_unchanged_on_all"] is True
    assert report["evidence_hash_unchanged_on_all"] is True
    assert report["record_hash_moved_on_all"] is True


def test_it_was_checked_against_the_pre_work_order_baseline(report):
    """A diff against what the pass intended proves nothing; this is a diff
    against what was committed before the pass ran."""
    assert report["baseline_ref"] == "d14cdc4"
    assert "before this work order touched anything" in report["method"]


def test_every_final_target_hash_is_enumerated(report, by_key):
    """The founder attests hashes, so every one must be listed AND live."""
    assert len(report["records"]) == COHORT_SIZE
    for row in report["records"]:
        record = by_key[row["identity_key"]]
        assert row["final_record_hash_to_attest"] == record_hash(record)
        assert row["final_record_hash_to_attest"] == \
            record["approval"]["record_hash"]
        assert row["evidence_hash"] == evidence_hash(record["evidence"])
        assert row["evidence_hash"] == record["approval"]["evidence_hash"]
        # The hash the founder's own earlier approval bound, and the new one.
        assert row["record_hash_before_work_order"] == \
            row["founder_prior_approval"]["record_hash"]
        assert row["record_hash_before_work_order"] != \
            row["final_record_hash_to_attest"]


def test_the_cohort_and_the_decisions_partition_the_market(report):
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    cohort = {r["identity_key"] for r in report["records"]}
    decided = {r["identity_key"] for r in ledger["decisions"]}
    assert len(cohort) == COHORT_SIZE
    assert len(decided) == DECIDED
    assert cohort & decided == set()
    assert len(cohort | decided) == 47
    assert cohort == {r["identity_key"] for r in
                      packet["artifact_binding_only_reattestation"]["records"]}


def test_every_cohort_record_is_now_founder_bound(by_key, report):
    """Pass C applied the block decision; the cohort is attested, and the
    approval it replaced is still the founder's own earlier one."""
    for row in report["records"]:
        approval = by_key[row["identity_key"]]["approval"]
        assert approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert approval["operator"] == "jfields80"
        assert approval["decision_source"]["kind"] == \
            "ARTIFACT_BINDING_ONLY_REATTESTATION"
        assert approval["supersedes"]["operator"] == "jfields80"
        assert approval["supersedes"]["record_hash"] == \
            row["record_hash_before_work_order"]


def test_the_verifier_catches_a_hidden_policy_change(by_key, report):
    """The check that makes the other checks worth anything.

    A verifier that only ever returns PASS is indistinguishable from no
    verifier, so each class of change the founder asked about is injected and
    must be caught.
    """
    import copy
    sample = by_key[report["records"][0]["identity_key"]]
    baseline = copy.deepcopy(sample)
    for entry in baseline["evidence"]:
        for key in ARTIFACT_BINDING_KEYS:
            entry.pop(key, None)
        entry["artifact_class"] = enums.POINTER_TO_EVIDENCE
    baseline["approval"] = copy.deepcopy(sample["approval"]["supersedes"])

    assert verify_record(baseline, sample)["verdict"] == "ARTIFACT_BINDING_ONLY"

    mutations = {
        "fact": lambda r: r["facts"].__setitem__("pet_count_limit", 9),
        "quote": lambda r: r["evidence"][0].__setitem__("quote", "TAMPERED"),
        "withholding": lambda r: r.__setitem__(
            "withheld_fields", {"pet_fee": {"reason_code": "SOURCE_AMBIGUOUS",
                                            "reason": "x",
                                            "evidence_refs": []}}),
        "service_animal": lambda r: r.__setitem__(
            "service_animal_statement", {"stated": True,
                                         "charges_stated": "no_charge"}),
        "dropped_evidence": lambda r: r["evidence"].pop(),
    }
    for label, mutate in mutations.items():
        tampered = copy.deepcopy(sample)
        mutate(tampered)
        result = verify_record(baseline, tampered)
        assert result["verdict"] == "NOT_ARTIFACT_ONLY", label
        assert result["failures"], label
