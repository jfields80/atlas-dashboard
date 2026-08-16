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
    """The Pass-1 report described the 21 records published at the time; the
    Pass-2 founder decisions added twenty more, each carried instead by
    cleveland_pass2_capture_results.json."""
    assert report["schema"] == "ptf-cleveland-artifact-verification/1.0"
    assert report["records_checked"] == 21
    assert len(facts["hotels"]) == 81
    assert report["classification_counts"] == {
        "ARTIFACT_VERIFIED_COMPLETE": 19,
        "ARTIFACT_PARTIAL": 2,
    }
    published = {h["identity_key"] for h in facts["hotels"]}
    by_key = {row["identity_key"]: row for row in report["records"]}
    assert set(by_key) <= published
    for key in DRURY_KEYS:
        assert by_key[key]["classification"] == "ARTIFACT_PARTIAL"


def test_verified_records_are_publication_grade(facts):
    for hotel in facts["hotels"]:
        entries = hotel["evidence"]
        drury = hotel["identity_key"] in DRURY_KEYS
        for entry in entries:
            assert entry["artifact_class"] == enums.PUBLICATION_GRADE_EVIDENCE
            assert entry["artifact_kind"] == enums.ARTIFACT_RENDERED_HTML
            assert entry["artifact_sha256"].startswith("sha256:")
            assert entry["captured_at"]
            if drury:
                # Pass 2 recaptured the page with the attended browser and
                # retained the bytes; worker_result_hash keeps naming the
                # 2026-08-11 deterministic fetch as historical provenance.
                assert entry["capture_method"] == "attended_browser"
                assert entry["artifact_sha256"] != hotel["worker_result_hash"]
            else:
                # Pass-1-era records were browser_assisted captures; the
                # Pass-2 founder-approved records are attended captures.
                # Either way the binding names the page the result hash names.
                assert entry["capture_method"] in ("browser_assisted",
                                                   "attended_browser")
                assert entry["artifact_sha256"] == hotel["worker_result_hash"]
            assert entry["source_grade"] == enums.GRADE_PT1_FIRST_PARTY
        assert not evidence_contract.validate(hotel)


def test_upgrade_did_not_touch_quotes_or_evidence_set(facts):
    """Refs derive from field+quote+url, so identical refs prove the upgrade
    changed bindings only -- never the words a fact rests on."""
    for hotel in facts["hotels"]:
        hay = " ".join(hotel["evidence_quote"].split())
        for entry in hotel["evidence"]:
            assert entry["evidence_ref"] == evidence_ref_for(entry)
            assert " ".join(entry["quote"].split()) in hay


def test_approvals_founder_bound_after_closeout(facts):
    """Pass 1 downgraded the 19 upgraded records to pending-operator rather
    than re-signing them; the governance closeout then recorded the founder's
    re-attestation against the FINAL hashes. What must remain true forever:
    every approval binds the record it signs, the founder's name sits only on
    decisions the founder gave, and the prior approval each one replaced is
    preserved verbatim -- unbound, never rewritten."""
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        assert approval["record_hash"] == record_hash(hotel)
        assert approval["evidence_hash"] == evidence_hash(hotel["evidence"])
        assert approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert approval["operator"] == "jfields80"
        # 2026-08-15: Pass-1 closeout + Pass-2 decisions; 2026-08-16:
        # Pass-3 decisions and the ESA ceiling!=price remediation.
        assert approval["approval_date"] in ("2026-08-15", "2026-08-16")
        if hotel["identity_key"] in DRURY_KEYS:
            # Re-attested by PTF-CLEVELAND-PASS2-FOUNDER-DECISIONS-001 against
            # the verified current hash; the 2026-08-11 approval is preserved
            # verbatim and provably unbound.
            prior = approval["supersedes"]
            assert prior["operator"] == "jfields80"
            assert prior["approval_date"] == "2026-08-11"
            assert prior["record_hash"] != approval["record_hash"]
            assert prior["evidence_hash"] == approval["evidence_hash"]
            continue
        prior = approval.get("supersedes")
        if prior is None:
            # First publication (Pass-2/Pass-3 founder decision): nothing
            # replaced.
            assert any("Founder decision" in c for c in approval["caveats"])
            continue
        # A superseding approval is either the Pass-1 governance closeout
        # re-attestation or the founder's Pass-3 ESA remediation.
        assert any("governance closeout" in c or "Founder remediation" in c
                   for c in approval["caveats"])
        assert prior["operator"] == "jfields80"
        assert prior["decision"] in (enums.APPROVED_AFTER_CURRENT_REVIEW,
                                     "APPROVED")
        # The replaced approval stays verbatim and provably unbound.
        if prior.get("record_hash"):
            assert prior["record_hash"] != approval["record_hash"]


def test_closeout_applied_exactly_the_two_approved_additions(facts):
    additions = {
        "the westin": "Leashed or caged in public areas, fee applies",
        "hotel indigo cleveland beachwood":
            "Required vaccination records showing up to date rabies, "
            "distemper, parvovirus and bordetella",
    }
    # The equality check is scoped to the 21 Pass-1-era records: the Pass-2
    # publications carry their own founder-approved general_restrictions.
    pass1_era = {row["identity_key"] for row in json.loads(
        REPORT_PATH.read_text(encoding="utf-8"))["records"]}
    for hotel in facts["hotels"]:
        if hotel["identity_key"] not in pass1_era:
            continue
        stated = hotel["facts"].get("general_restrictions")
        expected = additions.get(hotel["identity_key"])
        assert stated == expected, hotel["identity_key"]
        if not expected:
            continue
        entry = [e for e in hotel["evidence"]
                 if e["field"] == "general_restrictions"]
        assert len(entry) == 1 and entry[0]["quote"] == expected
        assert entry[0]["artifact_class"] == enums.PUBLICATION_GRADE_EVIDENCE
        assert entry[0]["artifact_sha256"] == hotel["worker_result_hash"]
    # KEEP_AS_IS x5: Key Tower gained no service_animal_statement, and the
    # four convention-scoped weight limits are still per_pet, unrestructured.
    by_key = {h["identity_key"]: h for h in facts["hotels"]}
    assert "service_animal_statement" not in \
        by_key["cleveland marriott downtown at key tower"]
    for key in ("comfort inn mayfield heights cleveland east",
                "holiday inn express and suites",
                "home2 suites by hilton cleveland beachwood",
                "hotel indigo cleveland downtown"):
        weight = by_key[key]["facts"]["weight_limit"]
        assert weight["scope"] == "per_pet"
        assert "combined_weight_limit" not in by_key[key]["facts"]


def test_release_contract_pins_the_upgraded_package(report):
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    actual = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest()
    assert contract["policy_package"]["expected_sha256"] == actual
    # Earlier shas are history; the latest pass stamps the pin it leaves.
    assert report["facts_sha256_after_pass3_decisions"] == actual
    assert report["facts_sha256_after_pass2_decisions"] != actual
    assert report["facts_sha256_after_pass2"] != actual
    assert report["facts_sha256_after_closeout"] != actual
    assert report["facts_sha256_after_apply"] != actual
