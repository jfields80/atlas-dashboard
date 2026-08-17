"""PTF-DETROIT-ANN-ARBOR-CAPTURE-PASS2-001 -- committed-state tests.

Validates the real Claude attended-browser capture of the 3 routing-repaired
DTW-area properties: exact 3-row batch completeness, artifact hash binding,
quote contiguity, identity binding, and that this capture-only pass left
every authority file untouched. It deliberately never reads the gitignored
worker tree -- artifact bytes are hashed once at capture time and the
committed sha256 is what these tests check against.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
RESULTS_PATH = LP / "detroit_ann_arbor_capture_pass2_001.json"
PACKET_PATH = LP / "detroit_ann_arbor_capture_pass2_founder_review_packet.json"
FACTS_PATH = LP / "hotel_policy_facts_detroit-ann-arbor-mi.json"
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
CENSUS_PATH = LP / "identity_census" / "detroit-ann-arbor-mi.json"
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
RAW_DIR = (REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-capture-pass2-001" / "raw")

MARKET = "detroit-ann-arbor-mi"
EXPECTED_IDS = ["DTW-P2-01", "DTW-P2-02", "DTW-P2-03"]
EXPECTED_KEYS = {
    "DTW-P2-01": "courtyard detroit pontiac bloomfield",
    "DTW-P2-02": "doubletree by hilton detroit novi",
    "DTW-P2-03": "hotel indigo detroit downtown",
}
OUTCOMES = {
    "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "POLICY_NOT_FOUND",
    "IDENTITY_UNCERTAIN", "ACCESS_BLOCKED", "CAPTURE_FAILED", "SOURCE_AMBIGUOUS",
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def results():
    return _load(RESULTS_PATH)


@pytest.fixture(scope="module")
def packet():
    return _load(PACKET_PATH)


class TestBatchCompleteness:
    def test_exactly_three_rows_in_results(self, results):
        assert results["count"] == 3
        rows = results["results"]
        assert len(rows) == 3
        assert [r["queue_id"] for r in rows] == EXPECTED_IDS
        assert len({r["identity_key"] for r in rows}) == 3

    def test_exactly_three_rows_in_packet(self, packet):
        assert packet["count"] == 3
        candidates = packet["candidates"]
        assert len(candidates) == 3
        assert [c["decision_id"] for c in candidates] == EXPECTED_IDS

    def test_no_founder_decision_recorded_yet(self, packet):
        for c in packet["candidates"]:
            assert "founder_decision" not in c

    def test_identity_keys_match_the_repaired_routing_batch(self, packet):
        for c in packet["candidates"]:
            assert c["identity_key"] == EXPECTED_KEYS[c["decision_id"]]

    def test_every_row_has_exactly_one_valid_outcome(self, packet, results):
        for c in packet["candidates"]:
            assert c["outcome"] in OUTCOMES
        for r in results["results"]:
            assert r["outcome"] in OUTCOMES


class TestArtifactBinding:
    def test_screenshot_sha256_matches_the_file_on_disk(self, packet):
        for c in packet["candidates"]:
            path = RAW_DIR / results_screenshot_file(c["decision_id"])
            assert path.is_file(), path
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            assert actual == c["artifact_sha256_screenshot"]

    def test_results_and_packet_agree_on_the_hash(self, results, packet):
        by_id_r = {r["queue_id"]: r for r in results["results"]}
        for c in packet["candidates"]:
            assert by_id_r[c["decision_id"]]["artifact_sha256_screenshot"] == \
                c["artifact_sha256_screenshot"]


def results_screenshot_file(decision_id):
    return {
        "DTW-P2-01": "P2-01-courtyard-pontiac.jpg",
        "DTW-P2-02": "P2-02-doubletree-novi.jpg",
        "DTW-P2-03": "P2-03-hotel-indigo-downtown.jpg",
    }[decision_id]


class TestQuoteContiguity:
    def test_every_row_has_a_nonempty_exact_quote(self, packet):
        for c in packet["candidates"]:
            assert c["exact_quote"].strip()
            assert "..." not in c["exact_quote"]
            assert "[TRUNCATED]" not in c["exact_quote"]

    def test_publication_candidate_facts_and_withholds_quote_the_source(self, packet):
        row = next(c for c in packet["candidates"] if c["decision_id"] == "DTW-P2-03")
        for fact in row["proposed_schema_1_2_facts"]:
            assert fact["quote"].strip()
            assert fact["quote"] in row["exact_quote"]
        for w in row["withheld_fields"]:
            assert w["reason_code"] in ("SOURCE_CONTRADICTORY", "SOURCE_AMBIGUOUS",
                                        "SCHEMA_CANNOT_REPRESENT")
            for q in w["quotes"]:
                assert q in row["exact_quote"]

    def test_no_pets_rows_have_no_proposed_facts_or_withholds(self, packet):
        for did in ("DTW-P2-01", "DTW-P2-02"):
            row = next(c for c in packet["candidates"] if c["decision_id"] == did)
            assert row["outcome"] == "VERIFIED_NO_PETS_CANDIDATE"
            assert row["proposed_schema_1_2_facts"] == []
            assert row["withheld_fields"] == []


class TestIdentityBinding:
    def test_every_row_is_fully_bound(self, packet):
        for c in packet["candidates"]:
            binding = c["identity_binding"]
            assert binding["bound"] is True
            assert binding["name"] is True

    def test_bound_route_matches_the_committed_census_official_url(self, packet):
        census = {r["identity_key"]: r for r in _load(CENSUS_PATH)["hotels"]}
        for c in packet["candidates"]:
            assert census[c["identity_key"]]["official_url"] == c["final_url"]
            assert census[c["identity_key"]]["url_shape"] == "property"


class TestFeeContradictionHandled:
    def test_hotel_indigo_fee_withheld_not_guessed(self, packet):
        row = next(c for c in packet["candidates"] if c["decision_id"] == "DTW-P2-03")
        withheld_fields = {w["field"] for w in row["withheld_fields"]}
        assert "pet_fee" in withheld_fields
        proposed_fields = {f["field"] for f in row["proposed_schema_1_2_facts"]}
        assert "pet_fee" not in proposed_fields


class TestAuthorityUnchanged:
    def test_no_policy_authority_or_exclusion_gained_a_new_detroit_row(self):
        facts = _load(FACTS_PATH)
        assert len(facts["hotels"]) == 6
        exclusions = _load(EXCLUSIONS_PATH)
        rows = [e for e in exclusions["exclusions"] if e.get("market_id") == MARKET]
        assert len(rows) == 5

    def test_census_and_partition_counts_unchanged_by_capture(self):
        census = _load(CENSUS_PATH)
        assert census["count"] == 142
        partition = _load(PARTITION_PATH)
        counts = partition["final_state_counts"]
        assert counts["PUBLISHED_PET_FRIENDLY"] == 6
        assert counts["VERIFIED_NO_PETS"] == 5

    def test_the_three_captured_rows_are_still_awaiting_policy_observation(self):
        partition = {i["identity_key"]: i for i in _load(PARTITION_PATH)["items"]}
        for key in EXPECTED_KEYS.values():
            assert partition[key]["final_state"] == "AWAITING_POLICY_OBSERVATION"
