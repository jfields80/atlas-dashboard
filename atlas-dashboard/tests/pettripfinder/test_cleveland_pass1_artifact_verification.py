"""PTF-CLEVELAND-LIGHT-RECERTIFICATION-001 Pass 1 -- committed-state tests.

These tests validate the COMMITTED outcome of the artifact-verification pass:
the upgraded facts package, the verification report, and the release-contract
pin. They deliberately do not read the gitignored worker tree, so they run in
every worktree; the on-disk hash verification itself is the script's job and
its verdicts are recorded in the committed report.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as evidence_contract
from scripts.pettripfinder.policy_migration import (
    evidence_hash, evidence_ref_for, record_hash,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / "hotel_policy_facts_cleveland-akron-canton-oh.json"
REPORT_PATH = LP / "cleveland_artifact_verification_001.json"
CONTRACT_PATH = (REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / "cleveland-akron-canton-oh.json")

DRURY_KEYS = {"drury inn and suites beachwood", "drury plaza hotel"}


@pytest.fixture(scope="module")
def facts():
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report():
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_report_covers_all_published_records(facts, report):
    assert report["schema"] == "ptf-cleveland-artifact-verification/1.0"
    assert report["records_checked"] == len(facts["hotels"]) == 21
    assert report["classification_counts"] == {
        "ARTIFACT_VERIFIED_COMPLETE": 19,
        "ARTIFACT_PARTIAL": 2,
    }
    by_key = {row["identity_key"]: row for row in report["records"]}
    assert set(by_key) == {h["identity_key"] for h in facts["hotels"]}
    for key in DRURY_KEYS:
        assert by_key[key]["classification"] == "ARTIFACT_PARTIAL"


def test_verified_records_are_publication_grade(facts):
    for hotel in facts["hotels"]:
        entries = hotel["evidence"]
        if hotel["identity_key"] in DRURY_KEYS:
            assert all(e["artifact_class"] == enums.POINTER_TO_EVIDENCE
                       for e in entries)
            continue
        for entry in entries:
            assert entry["artifact_class"] == enums.PUBLICATION_GRADE_EVIDENCE
            assert entry["artifact_kind"] == enums.ARTIFACT_RENDERED_HTML
            assert entry["artifact_sha256"].startswith("sha256:")
            assert entry["captured_at"]
            assert entry["capture_method"] == "browser_assisted"
            assert entry["source_grade"] == enums.GRADE_PT1_FIRST_PARTY
            # The binding names the SAME page the record's result hash names.
            assert entry["artifact_sha256"] == hotel["worker_result_hash"]
        assert not evidence_contract.validate(hotel)


def test_upgrade_did_not_touch_quotes_or_evidence_set(facts):
    """Refs derive from field+quote+url, so identical refs prove the upgrade
    changed bindings only -- never the words a fact rests on."""
    for hotel in facts["hotels"]:
        hay = " ".join(hotel["evidence_quote"].split())
        for entry in hotel["evidence"]:
            assert entry["evidence_ref"] == evidence_ref_for(entry)
            assert " ".join(entry["quote"].split()) in hay


def test_approvals_downgraded_never_resigned(facts):
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        assert approval["record_hash"] == record_hash(hotel)
        assert approval["evidence_hash"] == evidence_hash(hotel["evidence"])
        if hotel["identity_key"] in DRURY_KEYS:
            # Untouched records keep their operator approval untouched.
            assert approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
            assert approval["operator"] == "jfields80"
            continue
        assert approval["decision"] == enums.MACHINE_REVIEWED_PENDING_OPERATOR
        assert "jfields80" not in approval["operator"]
        prior = approval["supersedes"]
        assert prior["operator"] == "jfields80"
        assert prior["decision"] in (enums.APPROVED_AFTER_CURRENT_REVIEW,
                                     "APPROVED")
        # The evidence SET did not move; only the record (bindings) did.
        if prior.get("evidence_hash"):
            assert prior["evidence_hash"] == approval["evidence_hash"]
        if prior.get("record_hash"):
            assert prior["record_hash"] != approval["record_hash"]
        assert any("re-attestation" in c.lower()
                   for c in approval.get("caveats", []))


def test_release_contract_pins_the_upgraded_package(report):
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    actual = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest()
    assert contract["policy_package"]["expected_sha256"] == actual
    assert report["facts_sha256_after_apply"] == actual
