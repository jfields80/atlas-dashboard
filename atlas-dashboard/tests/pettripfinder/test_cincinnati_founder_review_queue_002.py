"""PTF-CINCINNATI-HARDENED-SYNC-002 Phase 7 -- the rebuilt founder-review queue.

The committed queue was generated on 2026-08-16 and never regenerated. The day
after, 210 official property URLs were bound and 27 identities were resolved,
so the queue graded 238 of its 250 rows ``MISSING_URL`` -- twenty-one of them
published on the live site -- and marked every row ``NOT_STARTED``.

A worklist that says a routed row has no URL sends someone to re-find a URL the
market already owns. ``test_no_routed_identity_is_reported_as_missing_a_url``
is the assertion that fails if that ever comes back.

The rest of this file pins the distinctions the rebuild is required to keep,
each of which is a state that reads as something worse than it is if it is
flattened: a silent page is not a refusal, a building that has not opened is
not a closure, and a server error is not a pet policy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"
QUEUE = PKG / "markets" / "reports" / "cincinnati-oh_founder_review_queue.json"

REVIEWER = "jfields80"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def queue():
    return _load(QUEUE)


@pytest.fixture(scope="module")
def rows(queue):
    return {r["identity_key"]: r for r in queue["rows"]}


@pytest.fixture(scope="module")
def routed():
    return {r["hotel_ref"]["identity_key"]
            for r in _load(AUTH / "identity_routing.json")["routes"]}


# ------------------------------------------------------------ the whole point

def test_no_routed_identity_is_reported_as_missing_a_url(rows, routed):
    """The defect that made the old queue worse than no queue."""
    liars = sorted(k for k in routed if rows[k]["url_grade"] == "MISSING_URL")
    assert liars == []


def test_every_graded_row_actually_carries_a_url(rows):
    assert [k for k, r in rows.items()
            if r["url_grade"] != "MISSING_URL" and not r["official_url"]] == []


def test_the_queue_covers_the_whole_census(queue, rows):
    census = _load(PKG / "identity_census" / "cincinnati-oh.json")
    assert queue["count"] == len(queue["rows"]) == 256
    assert set(rows) == {h["identity_key"] for h in census["hotels"]}


def test_it_records_what_it_supersedes(queue):
    """A queue that replaces a worklist must say which one, and why.

    Otherwise the next reader has two documents disagreeing about 238 rows and
    no way to tell which is live.
    """
    superseded = queue["supersedes"]
    assert superseded["work_order"] == "PTF-CINCINNATI-CENSUS-RECONCILIATION-001"
    assert superseded["count"] == 250
    assert superseded["why"]


# ------------------------------------------------- decisions are not re-asked

def test_every_resolved_identity_is_marked_decided(queue, rows):
    # 33 -> 96 (004) -> 137 (007) -> 152 (010).
    decided = [r for r in queue["rows"] if r["review_status"] == "DECIDED"]
    assert len(decided) == 152
    by_lane = {}
    for row in decided:
        by_lane.setdefault(row["capture_lane"], []).append(row)
    assert len(by_lane["RESOLVED_PUBLISHED"]) == 99
    assert len(by_lane["RESOLVED_NO_PETS"]) == 47
    assert len(by_lane["RESOLVED_OUT_OF_CATEGORY"]) == 6


def test_every_decided_row_names_the_person_who_decided_it(queue):
    for row in queue["rows"]:
        if row["review_status"] == "DECIDED":
            assert row["reviewer_id"] == REVIEWER, row["identity_key"]
            assert row["reviewed_at"]


def test_the_twenty_seven_capture_pass_one_rulings_survive(queue):
    """21 pet-friendly + 6 verified-no-pets, each still bound to its decision.

    The six OUT_OF_CURRENT_CATEGORY rows are a census disposition, not a Pass 1
    ruling, so they carry a reviewer but no decision_id -- and that difference
    is itself worth pinning.
    """
    ruled = [r for r in queue["rows"] if r.get("decision_id")]
    assert len(ruled) == 27
    lanes = {r["capture_lane"] for r in ruled}
    assert lanes == {"RESOLVED_PUBLISHED", "RESOLVED_NO_PETS"}
    assert all(r["founder_decision"].startswith("APPROVE") for r in ruled)
    # The records APPLICATION-004 and FREE-LANE-APPLICATION-007 added carry
    # their authorization on the policy record's approval block rather than a
    # Pass 1 decision id, so they are decided without being among these 27.
    decided = [r for r in queue["rows"] if r["review_status"] == "DECIDED"]
    assert len(decided) - len(ruled) == 125


def test_published_rows_carry_the_hash_their_approval_binds(rows):
    package = {h["identity_key"]: h
               for h in _load(PKG / "hotel_policy_facts_cincinnati-oh.json")["hotels"]}
    for key, record in package.items():
        assert rows[key]["record_hash"] == record["approval"]["record_hash"]


# ------------------------------------------------ the distinctions that matter

def test_a_silent_page_is_not_a_refusal(rows):
    """POLICY_NOT_FOUND is a fact about a page, never a no-pets answer."""
    silent = [k for k, r in rows.items()
              if r.get("prior_outcome") == "POLICY_NOT_FOUND"]
    assert silent == ["chester inn and suites"]
    row = rows["chester inn and suites"]
    assert row["capture_lane"] == "POLICY_RE_OBSERVATION_REQUIRED"
    assert row["final_state"] != "VERIFIED_NO_PETS"
    assert row["review_status"] == "NOT_STARTED"


def test_a_building_that_has_not_opened_is_held_not_classified(rows):
    """Three Cincinnati identities do not operate yet.

    None may be captured, classified no-pets, or read as closed. There is still
    no canonical AWAITING_PROPERTY_OPENING state, so the queue reports the hold
    and carries the backlog item rather than inventing one.
    """
    held = sorted(k for k, r in rows.items()
                  if r.get("hold_reason") == "PRE_OPENING")
    assert held == ["cincinnati s fidelity hotel",
                    "hyatt house cincinnati north",
                    "marriott cincinnati downtown"]
    for key in held:
        row = rows[key]
        assert row["review_status"] == "HELD"
        assert row["final_state"] != "VERIFIED_NO_PETS"
        assert row["hold_note"]
        assert row["backlog_item"]


def test_an_unreachable_server_says_nothing_about_a_pet_policy(rows):
    row = rows["budget host town center motel"]
    assert row["hold_reason"] == "ACCESS_BLOCKED"
    assert row["review_status"] == "HELD"
    assert row["final_state"] != "VERIFIED_NO_PETS"


def test_an_unadjudicated_census_url_is_its_own_lane(rows):
    """Twelve identities carry a URL the routing pass never ruled on.

    They are neither routed nor URL-less. Grading them BRAND_PROPERTY_PAGE
    would claim a binding nobody verified; grading them MISSING_URL would send
    someone to re-find a URL that is sitting in the census.
    """
    unverified = [k for k, r in rows.items()
                  if r["url_grade"] == "UNVERIFIED_CENSUS_URL"]
    assert len(unverified) == 12
    for key in unverified:
        assert rows[key]["official_url"]
        # Still 12, and still UNVERIFIED, even though Capture Pass 3
        # adjudicated four of them for free and APPLICATION-004 published
        # three. The grade is about ROUTING, not about knowledge: a URL is
        # verified when a routing pass writes the binding into the shard, and
        # publishing an identity actually REMOVES its route, because the seed
        # row becomes the source of truth. Being read is not being routed, and
        # a published row keeps this grade until a routing pass says otherwise.
        assert rows[key]["capture_lane"] in (
            "ROUTING_VERIFICATION_REQUIRED", "IDENTITY_REVIEW",
            "RESOLVED_PUBLISHED", "RESOLVED_NO_PETS")


def test_the_lane_totals_account_for_every_row(queue):
    assert sum(queue["lane_counts"].values()) == queue["count"] == 256
    assert sum(queue["review_status_counts"].values()) == 256
    assert sum(queue["url_grade_counts"].values()) == 256


def test_no_review_outcome_was_inferred_from_the_old_discovery_queue(queue):
    """The 121-row queue could not record an outcome, so none is read from it.

    Every DECIDED row in this queue traces to an artifact that carries a
    decision: the policy package's approval block, the exclusion registry's
    reviewer, or one of the three Pass 1 decision batches.
    """
    for row in queue["rows"]:
        if row["review_status"] == "DECIDED":
            assert (row.get("decision_source") or row.get("exclusion_state")
                    or row.get("record_hash")), row["identity_key"]
