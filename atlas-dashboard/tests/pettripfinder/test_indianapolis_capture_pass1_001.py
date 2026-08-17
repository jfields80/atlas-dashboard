"""Capture-only gates for PTF-INDIANAPOLIS-CLAUDE-CAPTURE-PASS1-001."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
RAW = (ROOT / "data" / "worker_runs" / "pettripfinder"
       / "indianapolis-claude-capture-pass1-001")


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_capture_covers_the_committed_ten_row_queue_in_order():
    queue = _json(PACKAGE / "indianapolis_capture_queue_pass4.json")
    results = _json(PACKAGE / "indianapolis_capture_pass1_001.json")
    assert results["rows_total"] == results["rows_captured"] == 10
    assert [row["identity_key"] for row in results["results"]] == [
        row["identity_key"] for row in queue["rows"]]
    assert [row["queue_order"] for row in results["results"]] == list(range(1, 11))


def test_every_row_has_exactly_one_terminal_outcome_and_a_bound_artifact():
    results = _json(PACKAGE / "indianapolis_capture_pass1_001.json")
    allowed = {"PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE",
               "POLICY_NOT_FOUND", "ACCESS_BLOCKED", "IDENTITY_UNCERTAIN",
               "CAPTURE_FAILED", "SOURCE_AMBIGUOUS"}
    assert sum(results["outcome_counts"].values()) == 10
    for row in results["results"]:
        assert row["outcome"] in allowed
        assert row["identity_binding"]["bound"] is True
        assert row["identity_binding"]["route_status"] == "ROUTING_CONFIRMED"
        assert row["artifact"]["sha256"].startswith("sha256:")
        assert row["official_property_url"] == row["final_url"]


def test_candidate_quotes_are_contiguous_in_the_hash_bound_raw_artifact():
    results = _json(PACKAGE / "indianapolis_capture_pass1_001.json")
    candidates = [row for row in results["results"]
                  if row["outcome"] in {"PUBLICATION_CANDIDATE",
                                         "VERIFIED_NO_PETS_CANDIDATE"}]
    assert len(candidates) == 5
    for row in candidates:
        artifact = ROOT / row["artifact"]["relative_path"]
        body = artifact.read_text(encoding="utf-8")
        actual = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
        assert actual == row["artifact"]["sha256"]
        for quote in row["exact_quotes"]:
            assert quote in body
        for fact in row["proposed_schema_1_2_facts"]:
            assert fact["quote_contiguous_in_artifact"] is True
            assert fact["quote"] in row["exact_quotes"]


def test_founder_packet_is_review_only_and_authority_is_frozen():
    results = _json(PACKAGE / "indianapolis_capture_pass1_001.json")
    packet = _json(PACKAGE / "indianapolis_capture_pass1_founder_review_packet.json")
    assert packet["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert packet["founder_decisions_applied"] is False
    assert packet["authority_changed"] is False
    assert packet["founder_review_rows"] == 5
    assert results["authority_freeze"] == {
        "published_pet_friendly": 8,
        "verified_no_pets": 4,
        "authority_changed": False,
        "founder_decisions_applied": False,
    }
    assert _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")["published"] is True
    exclusions = _json(PACKAGE / "markets" / "authority" / "indianapolis-in"
                       / "hotel_exclusions.json")["exclusions"]
    assert len(exclusions) == 4
    assert (RAW / "manifest.json").is_file()
    assert (RAW / "artifact_index.json").is_file()
