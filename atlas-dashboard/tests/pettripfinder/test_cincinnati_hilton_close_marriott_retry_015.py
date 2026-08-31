"""PTF-CINCINNATI-HILTON-CLOSE-AND-MARRIOTT-RETRY-PROBE-015.

Nine attempts, $1.26. Hilton finished; Marriott's challenge wall tested once.

The result reads like a triumph -- four of five walls fell, eight of nine rows
publication grade -- and most of these tests exist to stop that reading from
running ahead of the evidence:

* 4/5 and 3/8 have OVERLAPPING Wilson intervals. The retry rate does not, on
  its own, prove retrying helps. What licenses the recommendation is that no
  challenge REPEATED, which is a different and stronger kind of fact.
* the one retry that failed died on a proxy tunnel error at zero bytes. It
  never reached Marriott, so it is neither a repeated challenge nor a reached
  page, and it is counted on its own denominator in both directions.
* every one of the seven Hilton records carries the same "Deposit Yes ...
  Non-refundable Fee" wording. Seven identical labels are ONE template artifact,
  not seven corroborating statements, so the question is more open than before,
  not less.
* Homewood's missing nights 2-4 are still missing, and this order supplies the
  evidence that guessing them would have been wrong.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_hilton_close_marriott_retry_015 as M

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"
REPORT = PKG / "markets" / "reports" / "cincinnati_hilton_close_marriott_retry_015.json"
LEDGER = PKG / "ptf_paid_attempt_ledger_001.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def report():
    return _load(REPORT)


@pytest.fixture(scope="module")
def cincinnati_attempts():
    return [a for a in _load(LEDGER)["attempts"]
            if a.get("market_id") == "cincinnati-oh"]


# ------------------------------------------------------------- the money

def test_the_cap_held_on_every_meter(report):
    spend = report["spend"]
    assert spend["breached"] is False
    for key in ("runner_measured_usd", "runner_estimated_usd",
                "zone_month_to_date_delta_usd", "prepaid_balance_delta_usd"):
        assert spend[key] <= spend["cap_usd"], key


def test_pilot_014s_cost_was_corrected_upward_not_quietly_kept(report):
    """014 reported $1.08 and priced the cohort at $0.09 an attempt.

    The meters settled higher. Leaving the old rate in place would have made
    every future Marriott estimate too cheap by about 44%.
    """
    correction = report["correction_to_pilot_014"]
    assert correction["revised_sizing_rate_usd_per_attempt"] == 0.16
    assert "UNDERSTATED" in correction["why_it_matters"]
    # And the correction does not overclaim: the meters are account-wide.
    assert "cannot be attributed to a single run" in correction["caveat"]


# -------------------------------------------------- the retry measurement

def test_the_retry_was_conditional_and_stayed_conditional(report):
    """Only pilot-014 challenge rows, and all five of them."""
    retry = report["marriott_retry"]
    assert retry["challenged_on_first_attempt"] == 5
    assert retry["retries_attempted"] == 5
    assert retry["challenged_rows_not_retried"] == []
    assert report["authorization"]["new_marriott_identities"] == 0


def test_no_challenge_repeated_which_is_the_actual_finding(report):
    retry = report["marriott_retry"]
    assert retry["repeated_challenges"] == 0
    assert retry["retries_reaching_property_page"] == 4
    assert retry["retries_publication_grade"] == 4


def test_the_tunnel_failure_is_not_counted_as_a_wall(report):
    """ERR_TUNNEL_CONNECTION_FAILED at zero bytes proves nothing either way."""
    retry = report["marriott_retry"]
    assert retry["infrastructure_failures"] == 1
    # Excluded from the connected denominator, so it neither flatters the
    # recovery rate nor is mistaken for a repeated challenge.
    over_attempts = retry["reach_given_challenged_over_attempts"]
    over_connected = retry["reach_given_challenged_over_connected"]
    assert over_attempts["trials"] == 5
    assert over_connected["trials"] == 4
    assert retry["challenge_repeat_rate"]["successes"] == 0


def test_the_overlapping_intervals_are_stated_not_hidden(report):
    """The honest limit of a five-row probe."""
    assert "OVERLAPPING" in report["the_statistical_honesty"]
    first = M.wilson(3, 8)
    retry = report["marriott_retry"]["reach_given_challenged_over_attempts"]
    # The claim in the report is true: the intervals really do overlap.
    assert retry["low"] < first["high"]


def test_the_recommendation_rests_on_the_mechanism_not_the_rates(report):
    rec = report["marriott_recommendation"]
    assert rec["recommendation"] == M.SCALE_WITH_RETRY
    assert "did not repeat" in rec["why"] or "repeated" in rec["why"]
    assert rec["what_would_change_it"]


def test_a_repeated_challenge_would_have_changed_the_answer():
    """The recommendation is not a foregone conclusion of the code path."""
    first = [{"identity_key": "a", "outcome": "ACCESS_DENIED", "body_chars": 250}]
    # Same wall again -> never recommend paying for a second attempt.
    repeated = M.retry_measurement(
        first, [{"identity_key": "a", "outcome": "ACCESS_DENIED",
                 "body_chars": 250}])
    combined = M.combined_access(first, [])
    assert M.recommend(repeated, combined)["recommendation"] == M.STOP_OR_CHANGE


def test_combined_access_counts_properties_not_attempts(report):
    """A row retried once is still one property."""
    combined = report["marriott_combined_two_attempt_access"]
    assert combined["rows"] == 8
    assert combined["reached_within_two_attempts"] == 7
    assert combined["access"]["trials"] == 8


# ---------------------------------------------------------- hilton closed

def test_hilton_is_closed_because_the_population_is_exhausted(report):
    hilton = report["hilton_final"]
    assert hilton["status"] == "CLOSED"
    assert hilton["total_unique_rows"] == 8
    assert hilton["access"] == 8
    assert hilton["publication_grade"] == 7
    assert hilton["policy_not_found"] == 1
    assert "exhausted population" in hilton["why_closed"]


def test_no_routed_hilton_identity_remains_unattempted(cincinnati_attempts):
    """The claim behind CLOSED, checked against authority rather than prose."""
    partition = {i["identity_key"]: i for i in _load(PARTITION)["items"]}
    routes = [r for r in _load(AUTH / "identity_routing.json")["routes"]
              if r["status"] == "ROUTING_CONFIRMED"]
    attempted = {a["identity_key"] for a in cincinnati_attempts}
    left = [r["hotel_ref"]["identity_key"] for r in routes
            if r["brand"] == "HILTON"
            and not partition[r["hotel_ref"]["identity_key"]]["resolved"]
            and r["hotel_ref"]["identity_key"] not in attempted]
    assert left == []


# ------------------------------------------------- the preserved questions

def test_seven_identical_labels_did_not_resolve_the_fee_question(report):
    """Repetition of a template is not corroboration."""
    preserved = report["application_inventory"]["preserved_questions"]
    fee = preserved["fee_or_deposit"]
    assert "template artifact" in fee
    assert "does NOT resolve" in fee
    exceptions = report["application_inventory"]["items"]["FOUNDER_EXCEPTION"]
    assert len(exceptions) == 7
    for item in exceptions:
        assert "FEE_OR_DEPOSIT" in item["questions"]


def test_the_siblings_disagree_so_homewood_stays_unstated(report):
    """Order 015's own evidence shows the inference would have been wrong.

    Four siblings use 1-4/5+, but Sharonville uses 1-3/4-7. There is no single
    ladder to borrow from.
    """
    gap = report["application_inventory"]["preserved_questions"]["homewood_tier_gap"]
    assert "SHARONVILLE" in gap
    assert "1-3nts/4-7nts" in gap
    homewood = next(i for i in report["application_inventory"]["items"]["FOUNDER_EXCEPTION"]
                    if i["identity_key"] == "homewood suites cincinnati midtown")
    assert "TIER_GAP_NIGHTS_2_TO_4" in homewood["questions"]


def test_sharonville_carries_every_one_of_its_problems(report):
    """A species restriction that contradicts its siblings is not a detail."""
    row = next(i for i in report["application_inventory"]["items"]["FOUNDER_EXCEPTION"]
               if i["identity_key"] == "tru by hilton sharonville")
    for question in ("SPECIES_EXCLUDES_CATS", "TIER_BOUNDARIES_DIFFER",
                     "TIER_GAP_ABOVE_7_NIGHTS", "SERVICE_ANIMAL_FEE_EXEMPTION"):
        assert question in row["questions"]
    assert "No Cats" in row["policy_block"]


def test_a_stated_fee_and_an_unstated_one_are_not_the_same_class(report):
    """Absence of a fee sentence is informative here, but it is not $0."""
    clean = report["application_inventory"]["items"]["CLEAN_PET_FRIENDLY"]
    stated = [i for i in clean if i["fee_status"] == "STATED"]
    unstated = [i for i in clean if i["fee_status"] == "NOT_STATED"]
    assert len(stated) == 3 and len(unstated) == 2
    for item in unstated:
        assert "absence is not the same as $0" in item["note"] \
            or "Same reading as Fairfield" in item["note"]


# ------------------------------------------------------- what it did not do

def test_no_authority_was_mutated(report):
    assert report["authority_mutation"] == "NONE"
    counts = _load(PARTITION)["final_state_counts"]
    assert counts["PUBLISHED_PET_FRIENDLY"] == 99
    assert counts["VERIFIED_NO_PETS"] == 49
    assert sum(counts.values()) == 257
    assert _load(AUTH / "identity_routing.json")["count"] == 80


def test_nothing_acquired_was_published(report):
    package = {h["identity_key"] for h in
               _load(PKG / "hotel_policy_facts_cincinnati-oh.json")["hotels"]}
    excluded = {e["normalized_name"]
                for e in _load(AUTH / "hotel_exclusions.json")["exclusions"]}
    for bucket in report["application_inventory"]["items"].values():
        for item in bucket:
            assert item["identity_key"] not in package
            assert item["identity_key"] not in excluded


def test_the_first_attempt_was_preserved_not_overwritten(cincinnati_attempts):
    """A retry that erased its predecessor would destroy the measurement."""
    per_key = {}
    for attempt in cincinnati_attempts:
        per_key.setdefault(attempt["identity_key"], []).append(attempt)
    retried = {k: v for k, v in per_key.items() if len(v) > 1}
    assert len(retried) == 5
    for key, attempts in retried.items():
        outcomes = [a.get("outcome") for a in attempts]
        assert "ACCESS_DENIED" in outcomes, key
    assert len(cincinnati_attempts) == 21
    assert len(per_key) == 16


def test_the_validation_block_records_the_lane_constraints(report):
    v = report["validation"]
    assert v["firecrawl_calls"] == 0
    assert v["places_calls"] == 0
    assert v["web_unlocker_calls"] == 0
    assert v["brightdata_browser_only"] is True
    assert v["one_runner_only"] is True
    assert v["duplicate_unintended_attempts"] == 0
    assert v["hilton_new_rows"] <= 4
    assert v["marriott_retries"] <= 5


# --------------------------------------------------------- the projection

def test_the_scale_up_cap_is_sized_at_two_attempts_for_every_row(report):
    """A cap sized on EXPECTED attempts strands the run halfway."""
    proj = report["remaining_marriott"]["projection"]
    assert proj["rows"] == 34
    assert proj["attempts_hard_ceiling"] == 68
    assert proj["recommended_hard_cap_usd"] == proj["cost_hard_ceiling_usd"]
    assert proj["attempts_expected"] < proj["attempts_worst_case"] \
        <= proj["attempts_hard_ceiling"]
    assert "stops halfway" in proj["why_the_ceiling"]


def test_the_balance_cannot_fund_the_scale_up_and_says_so(report):
    """The finding that decides whether the next order can even run."""
    warning = report["remaining_marriott"]["balance_warning"]
    assert warning["sufficient"] is False
    assert warning["prepaid_balance_usd"] < warning["recommended_hard_cap_usd"]
    assert warning["largest_affordable_batch_rows"] == 17
    assert "stranded" in warning["what_this_means"]


def test_remaining_marriott_was_rebuilt_from_authority(report):
    remaining = report["remaining_marriott"]
    assert remaining["unresolved_routed"] == 42
    assert remaining["already_attempted"] == 8
    assert remaining["never_attempted"] == 34
    assert "rebuilt" in remaining["derivation"]


# ------------------------------------------------------------- the helpers

def test_a_challenge_page_is_not_a_reached_page():
    assert M.reached({"outcome": "VALID", "body_chars": 3000}) is True
    assert M.reached({"outcome": "ACCESS_DENIED", "body_chars": 250}) is False
    assert M.reached({"outcome": "NAVIGATION_FAILED", "body_chars": 0}) is False
    # A "success" carrying no content is not a reached page either.
    assert M.reached({"outcome": "VALID", "body_chars": 10}) is False


def test_recommending_from_no_retries_refuses():
    with pytest.raises(M.PilotError):
        M.recommend(M.retry_measurement([], []), M.combined_access([], []))


def test_two_refusals_share_a_block_digest_so_the_page_digest_binds(report):
    """'Pet Policy Pets Not Allowed' is the same 27 characters at two hotels.

    Hashing the block hashes the SENTENCE, not the property. An approval bound
    to a shared block digest would name evidence that could have come from
    either building -- the Choice collision again, in a different brand.
    """
    binding = report["application_inventory"]["binding_constraint"]
    assert binding["distinct_block_digests"] == 13
    assert binding["distinct_document_digests"] == 14
    assert binding["evidence_rows"] == 14
    assert "never block_sha256 alone" in binding["rule"]

    items = report["application_inventory"]["items"]
    rows = {i["identity_key"]: i for b in items.values() for i in b
            if i.get("document_sha256")}
    a = rows["cincinnati airport marriott"]
    b = rows["towneplace suites cincinnati downtown"]
    assert a["block_sha256"] == b["block_sha256"]
    assert a["document_sha256"] != b["document_sha256"]
    # Every row that carries evidence carries the digest that actually binds.
    assert len(rows) == 14
    assert len({r["document_sha256"] for r in rows.values()}) == 14
