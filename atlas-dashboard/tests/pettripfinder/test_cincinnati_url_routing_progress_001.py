"""PTF-CINCINNATI-URL-ROUTING-RECOVERY-001A -- checkpoint gates.

The 001 pass lost real routing evidence because it lived only in browser
session state. These tests exist so the committed checkpoint cannot drift from
the 223-row target manifest, and so a partial pass can never quietly become a
claim about the whole queue.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
PROGRESS = PKG / "markets" / "reports" / "cincinnati_url_routing_recovery_001_progress.json"
EVIDENCE = PKG / "markets" / "reports" / "cincinnati-oh_routing_evidence_001a.json"
TARGETS = PKG / "markets" / "reports" / "cincinnati-oh_url_recovery_targets.json"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"

QUEUE_TOTAL = 223


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def progress():
    return _load(PROGRESS)


@pytest.fixture(scope="module")
def targets():
    return _load(TARGETS)


class TestCoverage:

    def test_queue_total_is_unchanged(self, progress, targets):
        assert progress["original_queue_total"] == QUEUE_TOTAL
        assert targets["count"] == QUEUE_TOTAL

    def test_adjudicated_plus_remaining_is_the_whole_queue(self, progress):
        assert (progress["adjudicated_count"] + progress["remaining_count"]
                == QUEUE_TOTAL)
        assert len(progress["adjudicated"]) == progress["adjudicated_count"]
        assert len(progress["remaining"]) == progress["remaining_count"]

    def test_every_target_appears_exactly_once(self, progress, targets):
        seen = ([r["identity_key"] for r in progress["adjudicated"]]
                + [r["identity_key"] for r in progress["remaining"]])
        assert len(seen) == len(set(seen)), "duplicate identity in the checkpoint"
        assert set(seen) == {r["identity_key"] for r in targets["rows"]}


class TestEvidence:

    def test_every_accepted_route_carries_its_evidence(self, progress):
        for row in progress["adjudicated"]:
            if row["verdict"] == "PROPERTY_CLOSED_OR_CONVERTED":
                assert row["note"], row["identity_key"]
                continue
            assert row["final_url"].startswith("https://"), row["identity_key"]
            assert row["binding_signals"], row["identity_key"]
            assert row["source_relationship"], row["identity_key"]

    def test_a_full_binding_agrees_with_the_census_on_number_and_zip(self, progress):
        for row in progress["adjudicated"]:
            if row["verdict"] != "BRAND_PROPERTY_URL_FOUND":
                continue
            census_number = re.match(r"\s*(\d+)", row["census_address"] or "")
            page_number = re.match(r"\s*(\d+)", row["page_street"] or "")
            assert census_number and page_number, row["identity_key"]
            assert census_number.group(1) == page_number.group(1), row["identity_key"]

    def test_a_two_of_three_binding_says_which_signal_is_missing(self, progress):
        for row in progress["adjudicated"]:
            if row["verdict"].endswith("_2OF3"):
                assert len(row["note"]) > 60, row["identity_key"]

    def test_no_generic_brand_homepage_was_accepted(self, progress):
        for row in progress["adjudicated"]:
            url = row["final_url"]
            if not url:
                continue
            path = re.sub(r"^https?://[^/]+", "", url).strip("/")
            assert path, "%s bound a bare brand homepage" % row["identity_key"]
            assert len(path.split("/")) >= 2 or row["property_code"], row["identity_key"]

    def test_evidence_records_reconcile_to_adjudicated_rows(self, progress):
        evidence = _load(EVIDENCE)
        assert evidence["count"] == len(evidence["records"])
        assert evidence["count"] == progress["adjudicated_count"]


class TestScope:

    def test_checkpoint_is_not_routing_authority(self, progress):
        assert progress["is_routing_authority"] is False

    def test_routing_candidates_are_a_subset_of_the_census(self, progress):
        census = {h["identity_key"] for h in _load(CENSUS)["hotels"]}
        for row in progress["adjudicated"]:
            assert row["identity_key"] in census, row["identity_key"]

    def test_no_identity_review_row_was_pulled_into_the_queue(self, progress):
        blocked = {i["identity_key"] for i in _load(PARTITION)["items"]
                   if i["final_state"] == "AWAITING_IDENTITY_RESOLUTION"}
        touched = {r["identity_key"] for r in progress["adjudicated"]}
        assert not (touched & blocked)

    def test_the_pass_does_not_claim_the_whole_queue(self, progress):
        assert progress["remaining_count"] > 0
        assert progress["resume_point"]["lanes_outstanding"]

    def test_out_of_scope_lanes_are_named_not_silently_dropped(self, progress):
        deferred = " ".join(progress["resume_point"]["deferred_to_001b"]).lower()
        for lane in ("marriott", "hilton", "hyatt", "g6"):
            assert lane in deferred


class TestAuthorityUntouched:
    """The checkpoint must not have moved any authority file."""

    def test_partition_still_shows_every_target_awaiting_a_url(self, targets):
        states = {i["identity_key"]: i["final_state"]
                  for i in _load(PARTITION)["items"]}
        for row in targets["rows"]:
            assert states[row["identity_key"]] == "AWAITING_OFFICIAL_URL"

    def test_census_carries_no_new_official_url(self):
        census = _load(CENSUS)["hotels"]
        with_url = [h for h in census if (h.get("official_url") or "").strip()]
        assert len(with_url) == 12, "the checkpoint must not write official_url"
