"""PTF-CINCINNATI-MARRIOTT-SCALE-BATCH-016 -- fourteen for $1.38, all of them.

Every admitted property finished publication grade. A clean sweep is exactly
when a measurement most needs guarding, so these tests mostly pin the places
where this batch could be over-read:

* it is FOURTEEN rows, not the authorised seventeen. Seventeen at two attempts
  and the settled rate is a worst case of exactly the cap, which would have
  left the account at $0.21;
* first-attempt access was 10/14 against pilot 014's 3/8, and those intervals
  OVERLAP. The wall did not demonstrably get easier; access is variable, which
  is the argument for keeping the retry rather than dropping it;
* the repeat-challenge rate rests on TWO retried challenge rows. Its upper
  bound is 0.66. Pooled with Order 015 it is 0 of 7, upper bound 0.35 -- good
  evidence, not proof, and the recommendation says what would retire it;
* fourteen rows produced only ten distinct block digests. Binding on a block
  digest would name evidence that could have come from another hotel.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_marriott_scale_batch_016 as M

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"
REPORTS = PKG / "markets" / "reports"
REPORT = REPORTS / "cincinnati_marriott_scale_batch_016.json"
INVENTORY = REPORTS / "cincinnati_application_inventory_016.json"
LEDGER = PKG / "ptf_paid_attempt_ledger_001.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def report():
    return _load(REPORT)


@pytest.fixture(scope="module")
def inventory():
    return _load(INVENTORY)


@pytest.fixture(scope="module")
def cincinnati_attempts():
    return [a for a in _load(LEDGER)["attempts"]
            if a.get("market_id") == "cincinnati-oh"]


# ------------------------------------------------------- the batch was reduced

def test_fourteen_admitted_not_seventeen_and_the_reason_is_arithmetic(report):
    auth = report["authorization"]
    assert auth["properties_max"] == 17
    assert auth["properties_admitted"] == 14
    assert auth["effective_cap_usd"] < auth["cap_usd"]
    assert "$0.21" in auth["why_fewer_than_authorised"]


def test_the_two_attempt_ceiling_held_for_every_property(cincinnati_attempts):
    """Checked against the ledger, not against the report's own prose."""
    per_key = {}
    for attempt in cincinnati_attempts:
        per_key.setdefault(attempt["identity_key"], []).append(attempt)
    assert max(len(v) for v in per_key.values()) == M.MAX_ATTEMPTS_PER_PROPERTY


def test_the_stratification_that_was_impossible_is_named_as_such(report):
    """All 34 pool rows share one template and one code shape."""
    strat = report["authorization"]["stratification"]
    assert "could NOT be stratified" in strat
    assert "13 Marriott sub-brands" in strat


# ------------------------------------------------------------- the measurement

def test_the_first_pass_took_exactly_one_attempt_each(report):
    first = report["first_attempt_pass"]
    assert first["attempts"] == 14
    assert first["reached"] == first["publication_grade"] == 10
    assert first["challenge_failures"] == 2
    assert first["transport_failures"] == 2
    assert first["policy_silence"] == 0
    assert first["identity_failures"] == 0


def test_the_retry_recovered_everything_it_touched(report):
    retry = report["retry_pass"]
    assert retry["eligible"] == retry["attempted"] == 4
    assert retry["recovered_access"] == 4
    assert retry["recovered_publication_grade"] == 4
    assert retry["repeated_challenges"] == 0
    assert retry["repeated_transport_failures"] == 0


def test_the_repeat_rate_is_computed_over_challenge_rows_only(report):
    """Two of the four retries were transport failures.

    Pooling them into the denominator would dilute the one number the policy
    depends on -- a tunnel that never reached Marriott cannot testify about a
    bot wall.
    """
    retry = report["retry_pass"]
    assert retry["challenge_rows_retried"] == 2
    assert retry["repeat_challenge_rate"]["trials"] == 2
    assert retry["recovery_over_attempts"]["trials"] == 4


def test_the_batch_cleared_every_identity(report):
    combined = report["combined"]
    assert combined["unique_identities"] == 14
    assert combined["publication_grade"] == 14
    assert combined["failures"] == 0
    assert combined["two_attempt_access"]["point"] == 1.0


# ------------------------------------------------- the comparisons stay honest

def test_the_access_improvement_is_not_claimed_as_established(report):
    """10/14 against 3/8 looks decisive and is not."""
    comparison = report["comparison"]
    assert "NOT established" in comparison["do_these_differ"]
    assert "VARIABLE" in comparison["do_these_differ"]
    low_016 = M.wilson(10, 14)["low"]
    high_014 = M.wilson(3, 8)["high"]
    assert low_016 < high_014          # the intervals really do overlap


def test_two_challenge_rows_are_reported_as_weak_on_their_own(report):
    comparison = report["comparison"]
    pooled = comparison["pooled_repeat_challenge_rate"]
    assert pooled["successes"] == 0
    assert pooled["trials"] == 7           # 2 here + 5 from Order 015
    assert pooled["high"] > 0.3            # still a wide interval
    assert "not proof" in comparison["pooled_caveat"]


def test_the_recommendation_names_what_would_retire_it(report):
    rec = report["marriott_recommendation"]
    assert rec["recommendation"] == M.CONTINUE
    assert "measured again" in rec["what_would_retire_it"]


def test_a_material_repeat_rate_would_change_the_lane():
    """The recommendation is not a foregone conclusion of the code path."""
    first = [{"identity_key": "a", "outcome": "ACCESS_DENIED", "body_chars": 250},
             {"identity_key": "b", "outcome": "ACCESS_DENIED", "body_chars": 250}]
    retries = [{"identity_key": "a", "outcome": "ACCESS_DENIED", "body_chars": 250},
               {"identity_key": "b", "outcome": "VALID", "body_chars": 4000,
                "publication_grade": True}]
    measured = M.retry_pass(first, retries)
    assert measured["repeat_challenge_rate"]["point"] == 0.5
    combined = M.combined(first, retries)
    assert M.recommend(measured, combined)["recommendation"] == M.CHANGE_LANE


def test_a_batch_that_retried_no_challenge_row_may_not_issue_a_policy():
    """Transport-only retries cannot speak to the wall."""
    first = [{"identity_key": "a", "outcome": "NAVIGATION_FAILED", "body_chars": 0}]
    retries = [{"identity_key": "a", "outcome": "VALID", "body_chars": 4000,
                "publication_grade": True}]
    with pytest.raises(M.ScaleBatchError):
        M.recommend(M.retry_pass(first, retries), M.combined(first, retries))


# ------------------------------------------------------------ evidence binding

def test_block_digests_collide_again_so_document_digests_bind(report):
    binding = report["evidence_binding"]
    assert binding["evidence_rows"] == 14
    assert binding["distinct_block_digests"] == 10
    assert binding["distinct_document_digests"] == 14
    assert binding["all_rows_have_document_hash"] is True
    assert "never block_sha256 alone" in binding["rule"]


def test_every_publication_grade_row_carries_its_document_hash(report):
    rows = [r for bucket in report["batch_inventory"]["items"].values()
            for r in bucket]
    assert len(rows) == 14
    assert all(r["document_sha256"] for r in rows)
    assert len({r["document_sha256"] for r in rows}) == 14


# ------------------------------------------------------------ classification

def test_a_stated_zero_is_not_the_same_as_a_missing_fee(report):
    """Aloft says pets stay free. The Westin simply does not mention a fee."""
    clean = report["batch_inventory"]["items"]["CLEAN_PET_FRIENDLY"]
    by_key = {r["identity_key"]: r for r in clean}
    assert by_key["aloft newport on the levee"]["fee_status"] == "free"
    assert by_key["the westin cincinnati"]["fee_status"] == "not_stated"
    assert "not $0" in by_key["the westin cincinnati"]["note"]


def test_a_penalty_is_not_a_pet_fee(report):
    """SpringHill refuses pets AND names $250 for an undisclosed one."""
    no_pets = report["batch_inventory"]["items"]["CLEAN_VERIFIED_NO_PETS"]
    row = next(r for r in no_pets
               if r["identity_key"] == "springhill suites cincinnati airport south")
    assert "PENALTY" in row["caution"]
    assert "never be encoded as a fee tier" in row["caution"]


def test_service_animals_only_is_a_refusal_not_an_allowance(report):
    no_pets = report["batch_inventory"]["items"]["CLEAN_VERIFIED_NO_PETS"]
    row = next(r for r in no_pets
               if r["identity_key"] == "ac hotel cincinnati at liberty center")
    assert "service animal is not a pet" in row["note"]
    assert row["classification"] == "CLEAN_VERIFIED_NO_PETS"


def test_every_admitted_identity_got_exactly_one_terminal_state(report):
    items = report["batch_inventory"]["items"]
    keys = [r["identity_key"] for bucket in items.values() for r in bucket]
    assert len(keys) == len(set(keys)) == 14


# --------------------------------------------------------------------- cost

def test_reserved_spend_is_not_reported_as_actual_spend(report):
    """Using the ledger's ceiling as the bill would overstate cost ~50%."""
    cost = report["cost"]
    assert cost["actual_spend_usd"] == 1.38
    assert cost["ledger_reserved_usd"] > cost["actual_spend_usd"]
    assert cost["breached"] is False
    assert cost["actual_spend_usd"] <= cost["cap_usd"]
    assert cost["starting_balance_usd"] - cost["ending_balance_usd"] == \
        pytest.approx(cost["actual_spend_usd"], abs=0.01)


def test_the_planning_rate_is_the_more_expensive_meter(report):
    """The two meters disagree by ~60%; planning on the cheap one strands runs."""
    rate = report["settled_rate"]
    assert rate["recommended_planning_rate"] >= rate["zone_derived_usd_per_attempt"]
    assert rate["zone_derived_usd_per_attempt"] > \
        rate["balance_derived_usd_per_attempt"]


# ---------------------------------------------------------------- what remains

def test_the_remaining_pool_was_rebuilt_and_is_not_fully_fundable(report):
    remaining = report["remaining_marriott"]
    assert remaining["never_attempted"] == 20
    projection = remaining["projection"]
    assert projection["attempts_hard_ceiling"] == 40
    assert projection["balance_sufficient_for_all"] is False
    assert projection["rows_the_balance_can_fund"] == 9
    assert "rebuilt" in remaining["derivation"]


def test_the_remaining_pool_matches_authority(cincinnati_attempts):
    partition = {i["identity_key"]: i for i in _load(PARTITION)["items"]}
    routes = [r for r in _load(AUTH / "identity_routing.json")["routes"]
              if r["status"] == "ROUTING_CONFIRMED"]
    attempted = {a["identity_key"] for a in cincinnati_attempts}
    left = [r for r in routes if r["brand"] == "MARRIOTT"
            and not partition[r["hotel_ref"]["identity_key"]]["resolved"]
            and r["hotel_ref"]["identity_key"] not in attempted]
    assert len(left) == 20


# ----------------------------------------------------- the merged inventory

def test_the_inventory_balances_against_the_ledger(inventory):
    """Every identity Cincinnati has paid for appears exactly once."""
    rec = inventory["reconciliation"]
    assert rec["balanced"] is True
    assert rec["paid_but_missing_here"] == []
    assert rec["here_but_never_paid"] == []
    assert rec["paid_identities_in_ledger"] == rec["identities_in_this_inventory"] == 30


def test_the_consolidated_counts(inventory):
    assert inventory["counts"] == {
        "CLEAN_PET_FRIENDLY": 11, "CLEAN_VERIFIED_NO_PETS": 10,
        "FOUNDER_EXCEPTION": 7, "NO_AUTHORITY_ACTION": 2}
    assert inventory["total_identities"] == 30


def test_no_identity_is_claimed_by_two_orders(inventory):
    keys = [r["identity_key"] for bucket in inventory["items"].values()
            for r in bucket]
    assert len(keys) == len(set(keys)) == 30


def test_every_open_question_survived_consolidation(inventory):
    """Merging three reports is exactly where a caveat gets lost."""
    questions = inventory["open_questions"]
    for key in ("fee_or_deposit", "homewood_tier_gap", "sharonville_species",
                "monroe_taxable", "fee_not_stated", "springhill_penalty"):
        assert questions[key]
    # And the two that Order 015 raised are still stated in full.
    assert "two different charges" in questions["fee_or_deposit"]
    assert "1-3/4-7" in questions["homewood_tier_gap"]


def test_nothing_was_applied(report, inventory):
    assert report["authority_mutation"] == "NONE"
    assert inventory["applied"] == "NOTHING"
    counts = _load(PARTITION)["final_state_counts"]
    assert counts["PUBLISHED_PET_FRIENDLY"] == 99
    assert counts["VERIFIED_NO_PETS"] == 49
    assert sum(counts.values()) == 257
    assert _load(AUTH / "identity_routing.json")["count"] == 80

    package = {h["identity_key"] for h in
               _load(PKG / "hotel_policy_facts_cincinnati-oh.json")["hotels"]}
    excluded = {e["normalized_name"]
                for e in _load(AUTH / "hotel_exclusions.json")["exclusions"]}
    for bucket in inventory["items"].values():
        for row in bucket:
            assert row["identity_key"] not in package
            assert row["identity_key"] not in excluded


def test_the_lane_constraints_held(report):
    v = report["validation"]
    assert v["web_unlocker_calls"] == 0
    assert v["firecrawl_calls"] == 0
    assert v["places_calls"] == 0
    assert v["brightdata_browser_only"] is True
    assert v["one_runner_only"] is True
    assert v["unintended_duplicate_attempts"] == 0
    assert v["unique_properties"] <= 17
    assert v["max_attempts_per_property"] <= 2


# --------------------------------------------------------------- the helpers

def test_retry_eligibility_excludes_rows_that_answered():
    assert M.retry_eligible({"outcome": "ACCESS_DENIED"}) is True
    assert M.retry_eligible({"outcome": "NAVIGATION_FAILED"}) is True
    assert M.retry_eligible({"outcome": "VALID"}) is False
    assert M.retry_eligible({"outcome": "POLICY_NOT_FOUND"}) is False
    assert M.retry_eligible({"outcome": "IDENTITY_MISMATCH"}) is False
    # Publication grade closes a row whatever its outcome says.
    assert M.retry_eligible({"outcome": "ACCESS_DENIED",
                             "publication_grade": True}) is False


def test_the_affordable_batch_keeps_an_operational_floor():
    """An account drained to nothing cannot run the diagnostic a surprise needs."""
    assert M.affordable_rows(4.27, 0.165) == 9
    assert M.affordable_rows(1.00, 0.165) == 0
    assert M.affordable_rows(0.50, 0.165) == 0
    # Without the floor the same balance would look like it funds more.
    assert M.affordable_rows(4.27, 0.165, floor_usd=0.0) > \
        M.affordable_rows(4.27, 0.165)
