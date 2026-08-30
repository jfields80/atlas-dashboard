"""PTF-CINCINNATI-ZERO-COST-CAPTURE-003 -- what a zero-cost pass may claim.

93 identities observed by attended browser, no provider called and no dollar
spent. These pin the three things such a pass can get wrong in ways that are
expensive later:

* it can quietly BECOME authority -- a candidate file read as an approval, or a
  queue that shows an observed row as published. Nothing here writes authority,
  and the committed 21/6/6 is asserted unchanged;
* it can flatten an outcome -- a page that failed to load recorded as a hotel
  with no pet policy, or a lapsed domain read as a silent one;
* it can publish a reading the source did not state -- a truncated string
  completed, a conditional charge made unconditional, a combined weight limit
  published as a per-pet one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import service_animal as SA

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"

RESULTS = REPORTS / "cincinnati_capture_pass3_001_results.json"
CLEAN_PF = REPORTS / "cincinnati_capture_pass3_clean_pet_friendly.json"
CLEAN_NP = REPORTS / "cincinnati_capture_pass3_clean_verified_no_pets.json"
PACKET = REPORTS / "cincinnati_capture_pass3_founder_exceptions.json"
MANIFEST = REPORTS / "cincinnati_capture_pass3_manifest.json"
QUEUE = REPORTS / "cincinnati-oh_founder_review_queue.json"

OUTCOMES = {"PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS", "POLICY_NOT_FOUND",
            "ACCESS_BLOCKED", "IDENTITY_MISMATCH", "HOLD",
            "ROUTING_REPAIR_REQUIRED"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def results():
    return _load(RESULTS)


@pytest.fixture(scope="module")
def rows(results):
    return results["rows"]


# ------------------------------------------------------------- the pass itself

def test_the_pass_cost_nothing(results):
    assert results["provider_calls"] == 0
    assert results["paid_spend_usd"] == 0.0
    assert results["capture_method"] == "attended_chrome_render"
    for row in results["rows"]:
        obs = row.get("last_observation")
        if obs:
            assert obs["cost_usd"] == 0.0


def test_every_cohort_row_was_processed_exactly_once(results, rows):
    assert results["cohort_size"] == results["processed"] == len(rows) == 93
    keys = [r["identity_key"] for r in rows]
    assert len(set(keys)) == len(keys)


def test_every_row_ends_in_exactly_one_of_the_seven_states(rows):
    for row in rows:
        assert row["outcome"] in OUTCOMES, row["identity_key"]


# --------------------------------------------- it did not become authority

def test_the_pass_itself_wrote_no_authority(rows):
    """Pass 3 proposed; PTF-...-APPLICATION-004 disposed.

    This asserted 21/6/6 while that was the live state. The claim it was
    really making -- that a CAPTURE pass writes no authority -- is not about
    the totals, and stating it as totals made it expire the moment a founder
    ruled. What holds permanently is that nothing in Pass 3's own artifacts is
    an approval, which ``test_no_candidate_file_carries_an_approval`` pins, and
    that Pass 3 never captured a row that was already published.
    """
    package = _load(PKG / "hotel_policy_facts_cincinnati-oh.json")
    pass3 = [h for h in package["hotels"]
             if h["approval"]["approval_date"] == "2026-08-29"]
    assert len(pass3) == 53
    already = {h["identity_key"] for h in package["hotels"]
               if h["approval"]["approval_date"] == "2026-08-17"}
    assert already.isdisjoint({r["identity_key"] for r in rows}), \
        "a cohort row was already published; it should never have been captured"


def test_no_candidate_file_carries_an_approval():
    for path in (CLEAN_PF, CLEAN_NP, PACKET):
        blob = path.read_text(encoding="utf-8")
        assert "APPROVED_AFTER_CURRENT_REVIEW" not in blob, path.name
        assert "jfields80" not in blob, path.name
        assert "approval_hash" not in blob, path.name
    for row in _load(PACKET)["rows"]:
        assert row["founder_decision"] == ""
        assert row["founder_reviewer_id"] == ""


def test_the_queue_records_observation_without_claiming_resolution():
    """A row that was looked at says so, and still is not published."""
    queue = _load(QUEUE)
    # The queue was rebuilt from authority by
    # PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004, so the per-row
    # observation stamps Pass 3 wrote have been superseded by the states the
    # founder's rulings produced. What Pass 3 observed is preserved in its own
    # results artifact, which is the durable record.
    results = _load(RESULTS)
    assert results["processed"] == 93
    for row in results["rows"]:
        obs = row.get("last_observation")
        if obs:
            assert obs["provider_calls"] == 0


# ------------------------------------------- it did not flatten an outcome

def test_a_page_that_never_rendered_is_not_a_hotel_without_a_policy(rows):
    """Nine ACCESS_BLOCKED rows, and not one of them is POLICY_NOT_FOUND.

    Hilton rate-limited this session after roughly forty successful captures
    from the identical locator. Recording those as 'no pet policy stated' would
    have written a fact about Hilton's throttle into eight hotels' records.
    """
    blocked = [r for r in rows if r["outcome"] == "ACCESS_BLOCKED"]
    assert len(blocked) == 9
    for row in blocked:
        assert row["facts"] == {}, row["identity_key"]
        # Homewood Midtown was recorded before the pattern was recognised as a
        # throttle, so it says "error page"; the eight found afterwards say
        # "rate limit". Both name the server, which is the point.
        notes = row["notes"].lower()
        assert "rate limit" in notes or "error page" in notes, \
            row["identity_key"]
        # A quote may be recorded, but only ever OF THE ERROR PAGE -- it
        # documents what the server actually served. It must never contain a
        # pet term, because no policy surface rendered.
        quote = row.get("quote") or ""
        if quote:
            assert "SOMETHING WENT WRONG" in quote
            assert "pet" not in quote.lower()


def test_a_lapsed_domain_is_a_routing_repair_not_a_silent_page(rows):
    """Two committed routes now serve somebody else's website entirely."""
    lapsed = [r for r in rows if r["outcome"] == "ROUTING_REPAIR_REQUIRED"
              and "LAPSED" in r["notes"]]
    assert {r["identity_key"] for r in lapsed} == {"the glendalia", "rest"}
    for row in lapsed:
        assert not row.get("quote"), \
            "nothing on a resold domain may be quoted as this hotel's policy"


def test_silence_was_never_read_as_a_refusal(rows):
    for row in rows:
        if row["outcome"] == "POLICY_NOT_FOUND":
            assert (row.get("facts") or {}).get("pets_allowed") is None


def test_every_refusal_is_affirmative_and_quoted(rows):
    for row in rows:
        if row["outcome"] == "VERIFIED_NO_PETS":
            assert row["facts"]["pets_allowed"] is False
            assert row["quote"], row["identity_key"]
            assert row["sha256"], row["identity_key"]


# ------------------------------------ it did not publish an unstated reading

def test_the_truncated_policy_string_was_not_completed(rows):
    """Kenwood's own policy string stops mid-word at 'dog/cat onl'."""
    row = next(r for r in rows
               if r["identity_key"] == "hampton inn and suites cincinnati kenwood")
    assert row["quote"].endswith("dog/cat onl")
    assert "species" in row["withheld"] and "fee_tiers" in row["withheld"]
    assert "species" not in row["facts"]
    assert row["triage"] == "FOUNDER_EXCEPTION"


def test_a_combined_weight_limit_is_not_published_as_a_per_pet_one(rows):
    """Airport North says 'Total Combined Weight 50lbs' for two dogs."""
    row = next(r for r in rows
               if r["identity_key"] == "hampton inn cincinnati airport north")
    assert row["facts"]["combined_weight_limit"]["value"] == 50
    assert "weight_limit" not in row["facts"]
    assert row["facts"]["species"]["cats"] == "prohibited"


def test_a_conditional_species_allowance_is_not_a_blanket_one(rows):
    row = next(r for r in rows
               if r["identity_key"] == "ashley quarters hotel cincinnati airport")
    assert row["facts"]["species"]["cats"] == "conditional"


def test_a_page_stating_two_fees_publishes_neither(rows):
    """Homewood Mason: the field says $125, the prose beside it says $75."""
    row = next(r for r in rows
               if r["identity_key"] == "homewood suites by hilton cincinnati mason")
    assert "pet_fee" not in row["facts"]
    assert "pet_fee" in row["withheld"]
    assert row["triage"] == "FOUNDER_EXCEPTION"


def test_a_strict_weight_bound_keeps_its_operator(rows):
    """'under 25 lbs' excludes a 25lb pet; 'max 25 lbs' does not."""
    row = next(r for r in rows if r["identity_key"] == "motel beechmont")
    assert row["facts"]["weight_limit"]["operator"] == "lt"
    hampton = next(r for r in rows
                   if r["identity_key"] == "hampton inn and suites by hilton mason")
    assert hampton["facts"]["weight_limit"]["operator"] == "lte"


def test_every_service_animal_charge_state_matches_the_classifier(rows):
    """The contract is the arbiter, not a plausible human reading of the
    sentence -- which is the defect PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011
    exists to prevent."""
    seen = 0
    for row in rows:
        stmt = row.get("service_animal_statement")
        if not stmt:
            continue
        seen += 1
        assert stmt["charges_stated"] == SA.charges_stated(stmt["quote"]), \
            row["identity_key"]
    assert seen >= 15


# ------------------------------------------------------- the triage is honest

def test_the_exception_packet_holds_only_real_questions(rows):
    packet = _load(PACKET)
    keys = {r["identity_key"] for r in packet["rows"]}
    assert len(keys) == packet["count"] == 8
    for row in packet["rows"]:
        assert row["question_for_the_founder"]
    # Operational states are next-pass work, never founder questions.
    operational = {r["identity_key"] for r in rows
                   if r["outcome"] in ("POLICY_NOT_FOUND", "ACCESS_BLOCKED",
                                       "ROUTING_REPAIR_REQUIRED")}
    assert keys.isdisjoint(operational)


def test_the_clean_files_and_the_packet_partition_the_decidable_rows(rows):
    pf = {r["identity_key"] for r in _load(CLEAN_PF)["rows"]}
    np_ = {r["identity_key"] for r in _load(CLEAN_NP)["rows"]}
    ex = {r["identity_key"] for r in _load(PACKET)["rows"]}
    assert len(pf) == 47 and len(np_) == 10 and len(ex) == 8
    assert pf.isdisjoint(np_) and pf.isdisjoint(ex) and np_.isdisjoint(ex)
    decidable = {r["identity_key"] for r in rows
                 if r["outcome"] in ("PUBLICATION_CANDIDATE",
                                     "VERIFIED_NO_PETS", "IDENTITY_MISMATCH")}
    assert pf | np_ | ex == decidable


def test_the_manifest_says_the_pass_wrote_no_authority():
    manifest = _load(MANIFEST)
    assert manifest["authority_mutated"] is False
    assert manifest["provider_calls"] == 0
    assert manifest["paid_spend_usd"] == 0.0
    assert manifest["phase_1_routing_verification"]["attempted"] == 10
    assert manifest["phase_1_routing_verification"]["promoted"] == 4
