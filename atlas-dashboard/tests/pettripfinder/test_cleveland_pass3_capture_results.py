"""PTF-CLEVELAND-ATTENDED-PASS-3-001 -- committed-state tests.

These tests validate the COMMITTED outcome of the Pass-3 driveable-queue
session: the queue derivation, the capture-results ledger, and the founder
review packet. They deliberately never read the gitignored worker tree, so
they run in every worktree; the on-disk artifact verification is the
integration script's job and its verdicts are recorded in the committed
ledger. Pass 3 changes NO authority file, and one test pins exactly that.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
QUEUE_PATH = LP / "cleveland_pass3_queue.json"
RESULTS_PATH = LP / "cleveland_pass3_capture_results.json"
PACKET_PATH = LP / "cleveland_pass3_founder_review_packet.json"
FACTS_PATH = LP / "hotel_policy_facts_cleveland-akron-canton-oh.json"
CONTRACT_PATH = (REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / "cleveland-akron-canton-oh.json")

OUTCOMES = {
    "AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_PARTIAL", "NEGATIVE",
    "POLICY_NOT_FOUND", "SOURCE_CONTRADICTORY", "SOURCE_AMBIGUOUS",
    "ACCESS_BLOCKED", "IDENTITY_UNCERTAIN", "CAPTURE_FAILED",
}


@pytest.fixture(scope="module")
def queue():
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger():
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def packet():
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def test_queue_is_the_mechanical_68(queue):
    assert queue["schema"] == "ptf-cleveland-pass3-queue/1.0"
    assert queue["totals"] == {"observation": 30,
                               "marketing_only_artifact": 38,
                               "queue_total": 68}
    rows = queue["rows"]
    assert len(rows) == 68
    assert len({r["identity_key"] for r in rows}) == 68
    assert [r["queue_id"] for r in rows] == \
        ["CLE-P3-%03d" % n for n in range(1, 69)]
    for row in rows:
        assert row["official_url"].strip()
        assert row["group"] in ("OBSERVATION", "MARKETING_ONLY_ARTIFACT")


def test_ledger_covers_every_queue_row_exactly_once(queue, ledger):
    assert ledger["schema"] == "ptf-cleveland-pass3-capture-results/1.0"
    assert ledger["rows_total"] == 68
    ids = [r["queue_id"] for r in ledger["results"]]
    assert ids == [r["queue_id"] for r in queue["rows"]]
    for row in ledger["results"]:
        assert row["outcome"] in OUTCOMES, row["queue_id"]


def test_ledger_counts_are_self_consistent(ledger):
    results = ledger["results"]
    assert ledger["rows_captured"] == sum(
        1 for r in results if r.get("artifact_file"))
    counted = {}
    for row in results:
        counted[row["outcome"]] = counted.get(row["outcome"], 0) + 1
    assert counted == ledger["outcome_counts"]
    # A row without an artifact can only be the blocked kind, and every
    # blocked row is named in rows_not_driven.
    for row in results:
        if not row.get("artifact_file"):
            assert row["outcome"] == "ACCESS_BLOCKED"
            assert row["queue_id"] in ledger["rows_not_driven"]
        else:
            assert row["content_hashes_agree"] is True
            assert row["html_sha256"] and row["captured_at"]


def test_every_captured_row_carries_binding_and_hashes(ledger):
    for row in ledger["results"]:
        if not row.get("artifact_file"):
            continue
        binding = row["identity_binding"]
        assert set(binding) == {"phone", "street_number", "zip", "bound"}
        assert row["artifact_file_sha256"]
        assert row["capture_method"] in ("attended_browser",
                                         "deterministic_fetch")


def test_packet_candidates_mirror_the_ledger(ledger, packet):
    by_id = {r["queue_id"]: r for r in ledger["results"]}
    positives = packet["positive_candidates"]
    negatives = packet["negative_candidates"]
    pos_ids = [c["queue_id"] for c in positives]
    neg_ids = [c["queue_id"] for c in negatives]
    assert len(set(pos_ids)) == len(pos_ids)
    assert len(set(neg_ids)) == len(neg_ids)
    for cand in positives:
        row = by_id[cand["queue_id"]]
        assert row["outcome"] in ("AFFIRMATIVE_STRUCTURED",
                                  "AFFIRMATIVE_PARTIAL")
        assert cand["identity_binding"]["bound"] is True
        assert cand["proposed_facts"], cand["queue_id"]
        for fact in cand["proposed_facts"]:
            assert fact["field"] and fact["quote"]
            assert fact["quote_backed_by"] in ("text", "html")
        for withheld in cand["proposed_withheld"]:
            assert withheld["reason_code"] in (
                "CONTRADICTORY", "SOURCE_AMBIGUOUS",
                "SCHEMA_CANNOT_REPRESENT")
            assert withheld["reason"] and withheld["quote"]
        assert cand["artifact_sha256"].startswith("sha256:")
    for cand in negatives:
        row = by_id[cand["queue_id"]]
        assert row["outcome"] == "NEGATIVE"
        assert cand["proposed_state"] == "VERIFIED_NO_PETS"
        assert cand["refusal_quote"]
        assert cand["identity_binding"]["bound"] is True
    # Every ledger positive/negative made it into the packet -- nothing
    # adjudicated positive is silently dropped.
    ledger_pos = {r["queue_id"] for r in ledger["results"]
                  if r["outcome"] in ("AFFIRMATIVE_STRUCTURED",
                                      "AFFIRMATIVE_PARTIAL")}
    ledger_neg = {r["queue_id"] for r in ledger["results"]
                  if r["outcome"] == "NEGATIVE"}
    assert set(pos_ids) == ledger_pos
    assert set(neg_ids) == ledger_neg


def test_packet_prepares_three_hyatt_manual_instructions(packet):
    hyatt = packet["hyatt_operator_manual_instructions"]
    assert [h["identity_key"] for h in hyatt] == [
        "hyatt regency",
        "hyatt place cleveland lyndhurst legacy village",
        "hyatt place cleveland westlake crocker park",
    ]
    for entry in hyatt:
        assert entry["open_url"].startswith("https://")
        assert entry["targets"] and entry["instructions"]


def test_speed_benchmark_recorded(ledger):
    bench = ledger["speed_benchmark"]
    assert bench["available"] is True
    assert bench["captures"] >= ledger["rows_captured"]
    assert bench["session_elapsed_seconds"] > 0
    assert bench["captures_per_hour"] > 0


def test_founder_decisions_recorded_and_contract_pinned(ledger, packet):
    """The capture pass wrote packets only; the decision application then
    recorded the founder's ruling on every candidate, applied all 44, and
    re-pinned the release contract to the facts package it produced."""
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    actual = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest()
    assert contract["policy_package"]["expected_sha256"] == actual
    assert packet["status"] == "FOUNDER_DECIDED_AND_APPLIED"
    assert packet["decided_by"] == "jfields80"
    assert packet["decided_at"] == "2026-08-16"
    for cand in packet["positive_candidates"]:
        assert cand["founder_decision"] in ("APPROVE", "APPROVE_WITH_CHANGE")
        assert cand["outcome"] == "PUBLISHED"
        assert cand["decision_id"].startswith("D")
    for cand in packet["negative_candidates"]:
        assert cand["founder_decision"] == "APPROVE_VERIFIED_NO_PETS"
        assert cand["outcome"] == "EXCLUDED_VERIFIED_NO_PETS"
    remediation = packet["esa_existing_record_remediation"]
    assert remediation["authorized"] is True and remediation["applied"] is True
    assert remediation["record_hash_before"] != remediation["record_hash_after"]


def test_every_applied_decision_landed_in_the_authorities(packet):
    """Every PUBLISHED candidate is a facts record whose approval cites its
    decision id; every EXCLUDED candidate is a VERIFIED_NO_PETS exclusion."""
    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    by_key = {h["identity_key"]: h for h in facts["hotels"]}
    for cand in packet["positive_candidates"]:
        record = by_key[cand["identity_key"]]
        approval = record["approval"]
        assert approval["operator"] == "jfields80"
        assert approval["approval_date"] == "2026-08-16"
        assert any(cand["decision_id"] + "," in c or
                   cand["decision_id"] + " " in c
                   for c in approval["caveats"]), cand["decision_id"]
        # The record's worker_result_hash names the same artifact the
        # founder was shown.
        assert record["worker_result_hash"] == cand["artifact_sha256"]
    exclusions = json.loads(
        (LP / "hotel_exclusions.json").read_text(encoding="utf-8"))
    by_norm = {e["normalized_name"]: e for e in exclusions["exclusions"]}
    for cand in packet["negative_candidates"]:
        record = by_norm[cand["identity_key"]]
        assert record["exclusion_state"] == "VERIFIED_NO_PETS"
        assert record["source_hash"] == cand["artifact_sha256"]
        assert record["evidence_quote"] == cand["refusal_quote"]
        assert record["reviewer_id"] == "jfields80"
