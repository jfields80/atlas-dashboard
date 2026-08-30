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
RESULTS = PKG / "markets" / "reports" / "cincinnati_url_routing_recovery_001_results.json"

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

    #: Verdicts that legitimately carry no live URL -- the property is closed,
    #: converted, or (Marriott Cincinnati Downtown at 444 Plum St) has not
    #: opened yet. Each must still explain itself in the note.
    NO_URL_VERDICTS = ("PROPERTY_CLOSED_OR_CONVERTED", "ROUTING_UNRESOLVED")

    def test_every_accepted_route_carries_its_evidence(self, progress):
        for row in progress["adjudicated"]:
            if row["verdict"] in self.NO_URL_VERDICTS:
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
            if row["source_relationship"] == "EXACT_PROPERTY_FIRST_PARTY":
                # A dedicated single-property domain has no multi-property
                # homepage to be mistaken for -- the whole domain is the
                # binding, so the shallow-path heuristic does not apply.
                continue
            path = re.sub(r"^https?://[^/]+", "", url).strip("/")
            assert path, "%s bound a bare brand homepage" % row["identity_key"]
            assert len(path.split("/")) >= 2 or row["property_code"], row["identity_key"]

    def test_evidence_records_reconcile_to_adjudicated_rows(self, progress):
        evidence = _load(EVIDENCE)
        assert evidence["count"] == len(evidence["records"])
        assert evidence["count"] == progress["adjudicated_count"]


def _census_keys_with_history():
    """Census keys plus the keys they SUPERSEDED.

    A rename moves an identity key, and a historical report necessarily names
    the identity as it stood when the report was written. Resolving through
    ``prior_identity_key`` is what lets an old checkpoint keep validating
    without either rewriting history or losing the row. PTF-CINCINNATI-FOUNDER-
    REVIEW-AND-APPLICATION-004 renamed Extended Stay America Cincinnati
    Fairfield to Studio 6 Extended Stay Fairfield on the founder's ruling.
    """
    out = {}
    for h in _load(CENSUS)["hotels"]:
        out[h["identity_key"]] = h["identity_key"]
        prior = h.get("prior_identity_key")
        if prior:
            out[prior] = h["identity_key"]
    return out


class TestScope:

    def test_checkpoint_is_not_routing_authority(self, progress):
        assert progress["is_routing_authority"] is False

    def test_routing_candidates_are_a_subset_of_the_census(self, progress):
        census = _census_keys_with_history()
        for row in progress["adjudicated"]:
            assert row["identity_key"] in census, row["identity_key"]

    def test_no_identity_review_row_was_knowingly_pulled_into_the_queue(
            self, progress):
        """A row blocked on identity must not be worked for URLs.

        This asserted the two sets never overlap, which held until
        PTF-CINCINNATI-MAINSTAY-IDENTITY-012 found that a row this pass had
        already adjudicated denotes TWO hotels. A row can be routed and only
        LATER be found to be an identity conflation, so the invariant is not
        "no overlap" -- it is that every overlapping row was blocked by a
        later order than this pass, never worked while known to be blocked.
        """
        items = {i["identity_key"]: i for i in _load(PARTITION)["items"]}
        blocked = {k for k, i in items.items()
                   if i["final_state"] == "AWAITING_IDENTITY_RESOLUTION"}
        touched = {r["identity_key"] for r in progress["adjudicated"]}
        for key in touched & blocked:
            determined = items[key]["determined_by"]
            assert determined, key
            assert "URL-ROUTING-RECOVERY-001" not in determined, key
            assert "IDENTITY" in determined or "APPLICATION" in determined, key

    def test_the_pass_does_not_misstate_its_own_completeness(self, progress):
        # A partial pass must own up to what is still outstanding; a
        # genuinely complete pass (all 223 adjudicated) must not claim
        # phantom remaining work either -- both are the same "don't lie
        # about scope" invariant, just at opposite ends of the queue.
        if progress["remaining_count"] > 0:
            assert progress["resume_point"]["lanes_outstanding"]
        else:
            assert progress["adjudicated_count"] == progress["original_queue_total"]
            assert not progress["resume_point"]["lanes_outstanding"]

    def test_out_of_scope_lanes_are_named_not_silently_dropped(self, progress):
        if progress["remaining_count"] == 0:
            pytest.skip("all lanes complete -- nothing is out of scope to name")
        deferred = " ".join(progress["resume_point"]["deferred_to_001b"]).lower()
        for lane in ("marriott", "hilton", "hyatt", "g6"):
            assert lane in deferred


class TestAuthorityUntouched:
    """The CHECKPOINT (this module) must never move authority itself -- that
    stays true at every remaining_count. Once PTF-CINCINNATI-URL-ROUTING-
    RECOVERY-001C's separate finalize step has legitimately run (the
    explicitly-authorized "REBUILD ROUTING/PARTITION" step, once and only
    once remaining_count == 0), the partition is EXPECTED to have moved --
    that is finalization doing its job, not the checkpoint leaking into
    authority. Same distinction as TestScope.test_the_pass_does_not_misstate_
    its_own_completeness."""

    def test_partition_state_matches_finalization_status(self, targets, progress):
        states = {i["identity_key"]: i["final_state"]
                  for i in _load(PARTITION)["items"]}
        if progress["remaining_count"] > 0:
            for row in targets["rows"]:
                assert states[row["identity_key"]] == "AWAITING_OFFICIAL_URL"
            return
        # Finalized: every routed identity moved to AWAITING_POLICY_OBSERVATION
        # (or further, to PUBLISHED_PET_FRIENDLY/VERIFIED_NO_PETS once
        # PTF-CINCINNATI-PASS1-AUTHORITY-APPLICATION-001 resolved 26 of them);
        # every ROUTING_UNRESOLVED/no-URL identity stays AWAITING_OFFICIAL_URL.
        routed = {r["identity_key"] for r in _load(RESULTS)["rows"]
                 if r["included_in_routing_authority"]}
        # AWAITING_OFFICIAL_URL joins the onward states because a route can be
        # RETIRED after the fact: APPLICATION-004 retired three whose URL had
        # stopped resolving to the hotel (two domains resold to unrelated
        # sites, one property page that became a brand search page), which
        # correctly returns those identities to URL recovery.
        # AWAITING_IDENTITY_RESOLUTION joins them for the same kind of reason:
        # PTF-CINCINNATI-MAINSTAY-IDENTITY-012 found that a routed row denotes
        # TWO Choice properties in two buildings at one street number, so the
        # route is real and points at one of them while the identity behind it
        # is not settled. Being routed was never a promise that the identity
        # would hold.
        routed_onward_states = {"AWAITING_POLICY_OBSERVATION",
                                "PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
                                "AWAITING_OFFICIAL_URL",
                                "AWAITING_IDENTITY_RESOLUTION"}
        current = _census_keys_with_history()
        for row in targets["rows"]:
            key = current.get(row["identity_key"], row["identity_key"])
            if row["identity_key"] in routed:
                assert states[key] in routed_onward_states, key
            else:
                assert states[key] == "AWAITING_OFFICIAL_URL", key

    def test_census_carries_no_new_official_url(self):
        # Routing authority is a SEPARATE file from the census; finalization
        # writes identity_routing.json, never identity_census/cincinnati-oh.json's
        # own official_url field. That stays true regardless of completion.
        census = _load(CENSUS)["hotels"]
        with_url = [h for h in census if (h.get("official_url") or "").strip()]
        assert len(with_url) == 12, "routing authority must not write the census's official_url"
