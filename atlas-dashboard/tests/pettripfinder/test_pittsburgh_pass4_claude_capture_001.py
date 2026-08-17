"""PTF-PITTSBURGH-PASS4-CLAUDE-CAPTURE-001 capture-only gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"
EVIDENCE_ROOT = ROOT / "data" / "operator_evidence" / "pittsburgh-pass4-claude-capture-001"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def results() -> dict:
    return load(REPORTS / "pittsburgh_pass4_claude_capture_results.json")


def test_all_and_only_the_committed_queue_rows_are_processed_once():
    queue = load(REPORTS / "pittsburgh_pass4_claude_capture_queue.json")
    report = results()
    assert queue["count"] == report["queue_count"] == len(report["items"]) == 12
    assert [row["identity_key"] for row in report["items"]] == [row["identity_key"] for row in queue["items"]]
    assert "sunnyledge boutique hotel" not in {row["identity_key"] for row in report["items"]}
    assert {row["outcome"] for row in report["items"]} <= {
        "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "POLICY_NOT_FOUND",
        "ACCESS_BLOCKED", "IDENTITY_UNCERTAIN", "CAPTURE_FAILED", "SOURCE_AMBIGUOUS"}


def test_queue_rows_remain_unresolved_and_authority_is_frozen():
    report = results()
    partition = load(LP / "pittsburgh_final_partition_001.json")
    by_key = {row["identity_key"]: row for row in partition["items"]}
    assert all(not by_key[row["identity_key"]]["resolved"] for row in report["items"])
    frozen = report["authority_before_and_after"]
    assert {key: frozen[key] for key in ("published", "verified_no_pets", "out_of_category", "unresolved")} == {
        "published": 29, "verified_no_pets": 6, "out_of_category": 3, "unresolved": 58}
    assert report["no_authority_applied"] is True


def test_publication_grade_evidence_is_bound_to_hashes_and_contiguous_quotes():
    report = results()
    grade = [row for row in report["items"] if row["publication_grade"]]
    assert len(grade) == 10
    for row in report["items"]:
        artifact = row["artifacts"][0]
        assert artifact["artifact_sha256"].startswith("sha256:")
        assert artifact["source_grade"] == "OFFICIAL_PROPERTY"
        path = ROOT / artifact["artifact_file"]
        if not path.is_file():
            pytest.skip("operator evidence is intentionally gitignored and unavailable in this checkout")
        raw = path.read_bytes()
        assert artifact["artifact_sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8")
        for cited in row["quotes"]:
            assert cited["verification"] == "CONTIGUOUS_IN_DURABLE_ARTIFACT"
            assert cited["quote"] in text


def test_founder_packet_is_review_only_and_matches_the_publication_grade_set():
    report = results()
    packet = load(REPORTS / "pittsburgh_pass4_claude_founder_review_packet.json")
    manifest = load(REPORTS / "pittsburgh_pass4_claude_capture_manifest.json")
    review_keys = {row["identity_key"] for row in packet["entries"]}
    grade_keys = {row["identity_key"] for row in report["items"] if row["publication_grade"]}
    assert packet["status"] == "ALL_FOUNDER_DECISIONS_RECORDED_APPLICATION_PREP_PENDING"
    assert packet["count"] == len(packet["entries"]) == len(grade_keys) == 10
    assert review_keys == grade_keys
    recorded = packet["entries"]
    assert [row["capture_id"] for row in recorded] == [
        "PGH-P4-C001", "PGH-P4-C002", "PGH-P4-C003", "PGH-P4-C004", "PGH-P4-C005",
        "PGH-P4-C006", "PGH-P4-C007", "PGH-P4-C008", "PGH-P4-C009", "PGH-P4-C011"]
    assert [row["founder_decision"] for row in recorded] == [
        "APPROVE_VERIFIED_NO_PETS", "APPROVE_VERIFIED_NO_PETS",
        "APPROVE_PARTIAL_PUBLICATION", "APPROVE_WITH_CHANGE",
        "APPROVE_PUBLISH_STRUCTURED", "APPROVE_PUBLISH_STRUCTURED",
        "APPROVE_WITH_CHANGE", "APPROVE_WITH_CHANGE", "APPROVE_WITH_CHANGE",
        "APPROVE_WITH_CHANGE"]
    assert all(row["authority_application_status"] == "NOT_APPLIED" for row in recorded)
    assert all(row["founder_review_required"] is False for row in recorded)
    assert packet["decisions_recorded"] == 10
    assert packet["decisions_applied"] == 0
    assert manifest["count"] == 12
    assert [row["identity_key"] for row in manifest["artifacts"]] == [row["identity_key"] for row in report["items"]]
