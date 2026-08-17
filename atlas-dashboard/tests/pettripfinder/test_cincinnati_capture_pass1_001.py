"""PTF-CINCINNATI-CAPTURE-PASS1-001 -- committed-state tests.

Capture-only pass: 30 EVIDENCE_READY rows, terminally classified. These
tests validate the committed prepared queue, results ledger and founder
review packet, and pin that no policy authority moved -- this pass is
research, not publication.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
PREPARED_PATH = LP / "markets" / "reports" / "cincinnati_capture_pass1_001_prepared.json"
RESULTS_PATH = LP / "markets" / "reports" / "cincinnati_capture_pass1_001_results.json"
PACKET_PATH = LP / "markets" / "reports" / "cincinnati_capture_pass1_founder_review_packet.json"
PARTITION_PATH = LP / "cincinnati_final_partition_001.json"
ROUTING_PATH = LP / "identity_routing.json"

OUTCOMES = {
    "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "POLICY_NOT_FOUND",
    "IDENTITY_UNCERTAIN", "ACCESS_BLOCKED", "CAPTURE_FAILED", "SOURCE_AMBIGUOUS",
}
CANDIDATE_OUTCOMES = {"PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE"}
FORBIDDEN_LANES = {"choice", "marriott", "hyatt", "ihg"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def prepared():
    return _load(PREPARED_PATH)


@pytest.fixture(scope="module")
def results():
    return _load(RESULTS_PATH)


@pytest.fixture(scope="module")
def packet():
    return _load(PACKET_PATH)


class TestCompleteness:

    def test_exactly_thirty_rows(self, results):
        assert results["batch_total"] == 30
        assert results["attempted"] == 30
        assert len(results["rows"]) == 30

    def test_every_row_terminally_classified(self, results):
        for row in results["rows"]:
            assert row["outcome"] in OUTCOMES, row["identity_key"]
            assert row["outcome"] != "NOT_STARTED"

    def test_results_match_prepared_queue_exactly(self, prepared, results):
        prepared_keys = {r["identity_key"] for r in prepared["rows"]}
        result_keys = {r["identity_key"] for r in results["rows"]}
        assert prepared_keys == result_keys
        assert len(result_keys) == 30

    def test_no_duplicate_candidate(self, results):
        keys = [r["identity_key"] for r in results["rows"]]
        assert len(keys) == len(set(keys))

    def test_prepared_queue_status_reflects_outcome(self, prepared, results):
        outcome_by_key = {r["identity_key"]: r["outcome"] for r in results["rows"]}
        for row in prepared["rows"]:
            assert row["status"] == outcome_by_key[row["identity_key"]]
            assert row["status"] != "NOT_STARTED"


class TestScope:

    def test_no_attended_required_brand_was_processed(self, results):
        for row in results["rows"]:
            assert row["brand_lane"] not in FORBIDDEN_LANES, row["identity_key"]

    def test_brand_distribution_matches_the_prepared_mix(self, prepared, results):
        assert prepared["brand_distribution"] == {
            "bestwestern": 5, "esa": 3, "g6": 3, "hilton": 2, "independent": 5,
            "redroof": 5, "sonesta": 2, "wyndham": 5,
        }
        from collections import Counter
        assert dict(Counter(r["brand_lane"] for r in results["rows"])) == \
            prepared["brand_distribution"]

    def test_hilton_did_not_expand_beyond_two(self, results):
        hilton_rows = [r for r in results["rows"] if r["brand_lane"] == "hilton"]
        assert len(hilton_rows) == 2


class TestEvidenceQuality:

    def test_every_candidate_carries_an_exact_quote(self, results):
        for row in results["rows"]:
            if row["outcome"] in CANDIDATE_OUTCOMES:
                artifact = row.get("artifact")
                assert artifact is not None, row["identity_key"]
                assert artifact["exact_quote"].strip(), row["identity_key"]

    def test_sha256_when_present_is_well_formed(self, results):
        for row in results["rows"]:
            artifact = row.get("artifact")
            if artifact and artifact.get("artifact_sha256"):
                sha = artifact["artifact_sha256"]
                assert len(sha) == 64, row["identity_key"]
                assert all(c in "0123456789abcdef" for c in sha), row["identity_key"]

    def test_every_row_carries_identity_binding(self, results):
        for row in results["rows"]:
            binding = row["identity_binding"]
            assert binding["city"] and binding["state"] and binding["postal_code"], \
                row["identity_key"]

    def test_no_general_deposit_became_a_pet_fact(self, results):
        """Property-wide incidental/authorization holds must never surface as a
        pet-specific fee or deposit in the proposed facts. Every row whose
        capture notes call out a general/incidental hold amount must not
        carry that same dollar figure as a pet fee or deposit fact."""
        import re
        for row in results["rows"]:
            note = row["notes"]
            m = re.search(r"\$(\d+)[^.]*(incidental|general)", note, re.I) or \
                re.search(r"(incidental|general)[^.]*\$(\d+)", note, re.I)
            if not m:
                continue
            general_amount = int(next(g for g in m.groups() if g and g.isdigit()))
            facts = row["proposed_facts_schema_1_2"]
            for key in ("fee_amount", "deposit"):
                if key in facts:
                    assert facts[key] != general_amount, (
                        "%s: %s=%s matches the general/incidental hold called out in its "
                        "own notes -- looks like it leaked into the pet fact"
                        % (row["identity_key"], key, facts[key]))

    def test_access_blocked_and_policy_not_found_carry_no_fabricated_facts(self, results):
        for row in results["rows"]:
            if row["outcome"] in ("ACCESS_BLOCKED", "POLICY_NOT_FOUND"):
                assert row["proposed_facts_schema_1_2"] == {}, row["identity_key"]


class TestFounderPacket:

    def test_packet_covers_exactly_the_candidate_outcomes(self, results, packet):
        candidate_keys = {r["identity_key"] for r in results["rows"]
                          if r["outcome"] in CANDIDATE_OUTCOMES}
        packet_keys = {r["identity_key"] for r in packet["rows"]}
        assert candidate_keys == packet_keys
        assert packet["count"] == len(candidate_keys) == 27

    def test_packet_rows_have_unique_decision_ids(self, packet):
        ids = [r["decision_id"] for r in packet["rows"]]
        assert len(ids) == len(set(ids))

    def test_packet_recommends_no_founder_approval(self, packet):
        assert "founder_decision" not in packet
        assert "approved_by" not in packet
        for row in packet["rows"]:
            assert row["recommended_founder_decision"] in (
                "APPROVE_PUBLICATION", "APPROVE_NO_PETS")


class TestAuthorityFreeze:

    def test_partition_has_no_published_or_no_pets_state(self):
        partition = _load(PARTITION_PATH)
        states = set(partition["final_state_counts"])
        assert not any("PUBLISHED" in s or "NO_PETS" in s for s in states)

    def test_partition_still_totals_256(self):
        partition = _load(PARTITION_PATH)
        assert sum(partition["final_state_counts"].values()) == 256

    def test_routing_authority_untouched_by_this_pass(self):
        # Same total as PTF-CINCINNATI-ROUTING-INTEGRATION-001 left it --
        # capture is research, not a routing action.
        routing = _load(ROUTING_PATH)
        assert routing["count"] == len(routing["routes"]) == 300

    def test_no_hotel_policy_facts_file_exists_for_cincinnati(self):
        facts_path = LP / "hotel_policy_facts_cincinnati-oh.json"
        assert not facts_path.exists(), (
            "a policy-facts file for Cincinnati exists -- this capture pass must never "
            "write publication authority")
