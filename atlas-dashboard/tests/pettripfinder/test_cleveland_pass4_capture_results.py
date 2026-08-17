"""PTF-CLEVELAND-ATTENDED-PASS-4-001 -- committed-state tests.

These validate the COMMITTED outcome of the Pass-4 capture session: the
ledger covers the routing-repair queue exactly once, every candidate is
identity-bound and quote-backed, the conversion rows are held back from
publication, and -- the invariant this work order exists under -- Pass 4
changed NO policy authority. They never read the gitignored worker tree, so
they run in every worktree; the on-disk artifact verification is the
integration script's job and its verdicts are recorded in the ledger.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
QUEUE_PATH = LP / "cleveland_routing_repair_001_capture_ready_queue.json"
RESULTS_PATH = LP / "cleveland_pass4_capture_results.json"
PACKET_PATH = LP / "cleveland_pass4_founder_review_packet.json"
FACTS_PATH = LP / "hotel_policy_facts_cleveland-akron-canton-oh.json"
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
PARTITION_PATH = LP / "cleveland_final_partition_002.json"
CONTRACT_PATH = (REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / "cleveland-akron-canton-oh.json")

OUTCOMES = {
    "AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_PARTIAL", "NEGATIVE",
    "POLICY_NOT_FOUND", "POLICY_CAPTURED_PENDING_IDENTITY_RENAME",
    "IDENTITY_UNCERTAIN", "ROUTING_PROBLEM", "ACCESS_BLOCKED",
    "CAPTURE_FAILED",
}
WITHHOLDING_REASONS = {"SOURCE_SILENT", "SOURCE_AMBIGUOUS",
                       "SOURCE_CONTRADICTORY", "SCHEMA_CANNOT_REPRESENT",
                       "ARTIFACT_INSUFFICIENT", "IDENTITY_NOT_CONFIRMED"}


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def queue():
    return _json(QUEUE_PATH)


@pytest.fixture(scope="module")
def ledger():
    return _json(RESULTS_PATH)


@pytest.fixture(scope="module")
def packet():
    return _json(PACKET_PATH)


def test_ledger_covers_the_queue_exactly_once(queue, ledger):
    assert ledger["schema"] == "ptf-cleveland-pass4-capture-results/1.0"
    assert ledger["rows_total"] == 30 == ledger["rows_captured"]
    ids = [r["queue_id"] for r in ledger["results"]]
    assert sorted(ids) == sorted(r["queue_id"] for r in queue["rows"])
    assert len(set(ids)) == 30
    for row in ledger["results"]:
        assert row["outcome"] in OUTCOMES, row["queue_id"]


def test_every_row_carries_a_verified_artifact(ledger):
    """Pass 4 drove a routing-repaired queue, so every row has a page: there
    is no ACCESS_BLOCKED or CAPTURE_FAILED row to excuse a missing one."""
    for row in ledger["results"]:
        assert row["artifact_file"], row["queue_id"]
        assert row["content_hashes_agree"] is True, row["queue_id"]
        assert row["html_sha256"] and row["captured_at"]
        assert row["capture_method"] in ("attended_browser",
                                         "deterministic_fetch")
        binding = row["identity_binding"]
        assert set(binding) == {"phone", "street_number", "zip", "bound"}


def test_counts_are_self_consistent(ledger):
    counted = {}
    for row in ledger["results"]:
        counted[row["outcome"]] = counted.get(row["outcome"], 0) + 1
    assert counted == ledger["outcome_counts"]
    assert sum(counted.values()) == 30


def test_candidates_mirror_the_ledger_and_are_quote_backed(ledger, packet):
    by_id = {r["queue_id"]: r for r in ledger["results"]}
    positives = packet["positive_candidates"]
    renames = packet["rename_candidates"]
    negatives = packet["negative_candidates"]
    assert packet["decision_totals"] == {
        "positive_candidates": len(positives),
        "rename_candidates": len(renames),
        "negative_candidates": len(negatives),
        "total_founder_decisions":
            len(positives) + len(renames) + len(negatives),
    }
    for cand in positives + renames:
        row = by_id[cand["queue_id"]]
        assert row["outcome"] == cand["outcome"]
        assert cand["identity_binding"]["bound"] is True, cand["queue_id"]
        assert cand["proposed_facts"], cand["queue_id"]
        for fact in cand["proposed_facts"]:
            assert fact["field"] and fact["quote"]
            assert fact["quote_backed_by"] in ("text", "html")
        for withheld in cand["proposed_withheld"]:
            assert withheld["reason_code"] in WITHHOLDING_REASONS
            assert withheld["reason"] and withheld["quote"]
        assert cand["artifact_sha256"].startswith("sha256:")
    for cand in negatives:
        assert by_id[cand["queue_id"]]["outcome"] == "NEGATIVE"
        assert cand["proposed_state"] == "VERIFIED_NO_PETS"
        assert cand["refusal_quote"]
        assert cand["identity_binding"]["bound"] is True
    # Nothing adjudicated positive or negative is silently dropped.
    assert {c["queue_id"] for c in positives} == {
        r["queue_id"] for r in ledger["results"]
        if r["outcome"] in ("AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_PARTIAL")}
    assert {c["queue_id"] for c in renames} == {
        r["queue_id"] for r in ledger["results"]
        if r["outcome"] == "POLICY_CAPTURED_PENDING_IDENTITY_RENAME"}
    assert {c["queue_id"] for c in negatives} == {
        r["queue_id"] for r in ledger["results"]
        if r["outcome"] == "NEGATIVE"}


def test_conversion_rows_are_held_back_from_publication(packet):
    """A captured policy whose census identity still names the prior brand
    may not publish against that name; the rename is decided first."""
    for cand in packet["rename_candidates"]:
        conversion = cand["conversion_note"]
        assert conversion["census_name"] != conversion["observed_name"]
        assert conversion["note"]
        assert cand["current_canonical_name"] == conversion["census_name"]
        assert cand["recommended_founder_decision"] == \
            "APPROVE_RENAME_THEN_PUBLISH"


def test_hilton_rate_limit_rule_is_recorded(ledger):
    """P3-049 first, Embassy after a cool-down, nothing else on hilton.com."""
    rule = ledger["hilton_rate_limit_rule"]
    assert "CLE-RR-030" in rule and "FIRST navigation" in rule
    hilton = [r for r in ledger["results"]
              if "hilton.com" in (r.get("final_url") or "")]
    assert {r["queue_id"] for r in hilton} == {"CLE-RR-030", "CLE-RR-011"}
    for row in hilton:
        assert row["outcome"] == "AFFIRMATIVE_STRUCTURED"


def test_hyatt_stays_operator_manual(packet, ledger):
    hyatt = packet["hyatt_operator_manual_instructions"]
    assert len(hyatt) == 3
    assert not any("hyatt" in r["identity_key"] for r in ledger["results"])
    for entry in hyatt:
        assert entry["open_url"].startswith("https://")
        assert entry["targets"] and entry["instructions"]


def test_speed_benchmark_recorded(ledger):
    bench = ledger["speed_benchmark"]
    assert bench["available"] is True
    assert bench["captures"] >= ledger["rows_captured"]
    assert bench["session_elapsed_seconds"] > 0
    assert bench["captures_per_hour"] > 0


def test_pass4_changed_no_authority(packet):
    """The invariant this work order runs under: a capture pass writes
    packets, never authority. The facts package still matches the release
    contract pin, Cleveland's published and excluded counts are untouched,
    and no approval or founder attribution exists in the packet."""
    contract = _json(CONTRACT_PATH)
    actual = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest()
    assert contract["policy_package"]["expected_sha256"] == actual
    facts = _json(FACTS_PATH)
    assert len(facts["hotels"]) == 81
    cle_no_pets = [e for e in _json(EXCLUSIONS_PATH)["exclusions"]
                   if e.get("market_id") == "cleveland-akron-canton-oh"
                   and e["exclusion_state"] == "VERIFIED_NO_PETS"]
    assert len(cle_no_pets) == 35
    rec = _json(PARTITION_PATH)["reconciliation"]
    assert (rec["published_pet_friendly"], rec["verified_no_pets"],
            rec["unresolved"]) == (81, 35, 72)
    assert packet["status"] == "AWAITING_FOUNDER_DECISION"
    blob = json.dumps(packet)
    assert "jfields80" not in blob
    for cand in (packet["positive_candidates"] + packet["rename_candidates"]
                 + packet["negative_candidates"]):
        assert "approval" not in cand
