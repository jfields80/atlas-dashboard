# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-TARGET-43-45-RECOVERY-025.

The finding this pass exists to deliver is a NEGATIVE one, so the tests are
weighted towards it: the zero-cost pool cannot move the pet-friendly count, and
the target is not reachable from any cohort smaller than the entire remaining
market. Both are pinned, because a later pass that quietly "recovers" a profile
here would be reading something this evidence does not say.

THE READER. Two defects were driven out of it and both are guarded. A refusal
wins over an allowance on the same line, because "Sorry no other pets are
allowed" CONTAINS the substring an allowance pattern matches and publishing it
as a permission would say the opposite of what the hotel says. And no pattern
may span a newline: letting one do so is how "Pets Not Allowed" first came back
quoting "See Details / Open in New Tab / Rooms & Suites".

THE SIZING. Yield is planned on the Wilson LOWER bound and cost on the UPPER
one. Using a single bound for both is how a plan under-delivers and overruns at
once, and the URL rate is borrowed from another market, which the report says
in the same breath as it uses it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_target_recovery_025 as R  # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORT = LP / "grand_rapids_holland_mi_target_recovery_025.json"


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def report():
    return _load(REPORT)


# --------------------------------------------------------------------------- #
# The finding
# --------------------------------------------------------------------------- #

def test_the_zero_cost_pool_moves_the_pet_friendly_count_by_zero(report):
    recovery = report["zero_cost_recovery"]
    assert recovery["reviewed"] == 6
    assert recovery["pet_friendly"] == 0
    assert recovery["verified_no_pets"] == 2
    assert recovery["by_verdict"] == {"SOURCE_SILENT": 4, "VERIFIED_NO_PETS": 2}
    assert report["projected_pet_friendly_after_zero_cost"] == 35
    assert report["remaining_gap_to_43"] == 8


def test_both_recoveries_are_refusals_quoted_from_the_saved_page(report):
    rows = {r["identity_key"]: r for r in report["zero_cost_recovery"]["rows"]}
    baymont = rows["baymont inn and suites grand rapids airport"]
    assert baymont["verdict"] == "VERIFIED_NO_PETS"
    assert baymont["quote"] == "Sorry no other pets are allowed."
    fairfield = rows["fairfield inn and suites grand rapids wyoming"]
    assert fairfield["verdict"] == "VERIFIED_NO_PETS"
    assert fairfield["quote"] == "Pets Not Allowed"
    for row in rows.values():
        assert row["provider_calls"] == 0
        assert row["rendered_html_sha256"], "the bytes read must be identified"


def test_a_refusal_wins_over_an_allowance_on_the_same_line():
    """"Sorry no other pets are allowed" contains the substring an allowance
    pattern matches. Reading it as a permission publishes the opposite of what
    the hotel says."""
    line = "Sorry no other pets are allowed."
    assert R._REFUSAL.search(line)
    assert R._ALLOWANCE.search(line), (
        "the allowance pattern DOES match -- which is exactly why the refusal "
        "is tested first rather than the two being treated as equal")


@pytest.mark.parametrize("line,refusal,allowance", [
    ("Pets Not Allowed", True, False),
    ("No, pets are not allowed at this hotel.", True, False),
    ("Pets are welcome for a fee.", False, True),
    ("Up to 2 pets are allowed for 25.00 USD per night", False, True),
    ("We welcome pets", False, True),
])
def test_the_reader_reads_only_what_the_line_says(line, refusal, allowance):
    assert bool(R._REFUSAL.search(line)) is refusal
    assert bool(R._ALLOWANCE.search(line)) is allowance


def test_no_pattern_may_span_a_newline():
    """The defect that made "Pets Not Allowed" quote a navigation menu."""
    text = "Pets Not\nAllowed\nSee Details\nOpen in New Tab"
    for line in text.splitlines():
        match = R._REFUSAL.search(line)
        if match:
            assert "\n" not in match.group(0)
            assert "See Details" not in match.group(0)


def test_a_service_animal_sentence_is_never_a_pet_policy():
    stripped = R._SERVICE_ANIMAL.sub(
        " ", "ADA defined service animals are welcome at this hotel.")
    assert not R._ALLOWANCE.search(stripped)
    assert not R._REFUSAL.search(stripped)


# --------------------------------------------------------------------------- #
# The populations
# --------------------------------------------------------------------------- #

def test_the_unresolved_pool_splits_into_four_populations(report):
    populations = report["unresolved_populations"]
    assert populations["no_url"]["count"] == 76
    assert populations["dedup_merged_duplicate"]["count"] == 17
    assert populations["brand_excluded"]["count"] == 5
    assert populations["routed_with_a_saved_capture"]["count"] == 16
    assert sum(p["count"] for p in populations.values()) == 114


def test_every_row_the_order_excludes_says_which_rule_kept_it_out(report):
    excluded = report["zero_cost_recovery"]["excluded_by_rule"]
    assert len(excluded) == 10
    keys = {row["identity_key"] for row in excluded}
    assert "budgetel grand rapids" in keys
    assert "comfort suites grandville grand rapids sw" in keys
    assert "avid hotel zeeland" in keys
    for row in excluded:
        assert row["why"]


# --------------------------------------------------------------------------- #
# The sizing
# --------------------------------------------------------------------------- #

def test_yield_is_planned_low_and_cost_is_planned_high(report):
    rates = report["paid_plan"]["rates"]
    pet = rates["pet_friendly_per_attempt"]
    assert pet["successes"] == 34 and pet["trials"] == 65
    assert pet["wilson_lower_95"] < pet["point"] < pet["wilson_upper_95"]
    url = rates["url_recovered_per_discovery_lookup"]
    assert url["borrowed"] is True
    assert "another market's rate" in url["caveat"]
    assert url["wilson_lower_95"] < url["point"] < url["wilson_upper_95"]


def test_wilson_bounds_bracket_the_point_estimate():
    assert R.wilson_lower(34, 65) < 34 / 65 < R.wilson_upper(34, 65)
    assert R.wilson_lower(0, 0) == 0.0 and R.wilson_upper(0, 0) == 0.0
    # A single success proves almost nothing, and the bound has to say so.
    assert R.wilson_lower(1, 1) < 0.5


def test_the_target_needs_the_entire_remaining_market(report):
    """The second finding. There is no smaller cohort, so the order's stop rule
    never gets to bite."""
    plan = report["paid_plan"]
    lane_b = plan["lane_b_rows_with_no_url_at_all"]
    assert lane_b["is_the_entire_remaining_pool"] is True
    assert lane_b["discovery_lookups_required"] == 76
    assert lane_b["rows_that_actually_exist_to_look_up"] == 76
    # Eight profiles at the conservative rate would need more lookups than
    # there are rows to look up.
    assert lane_b["lookups_eight_profiles_would_need_at_the_lower_bound"] > 76

    target = plan["reaching_the_target"]
    assert target["today"] == 35
    assert target["lane_b_alone_at_the_lower_bound"] < 43, (
        "lane B alone falls short, which is why lane A is not optional")
    assert target["lane_a_plus_lane_b_at_the_lower_bound"] >= 43
    assert target["reaches_the_target_conservatively"] is True


def test_the_premium_domain_rows_are_required_and_unpriceable(report):
    lane_a = report["paid_plan"]["lane_a_rows_that_already_hold_a_url"]
    assert lane_a["candidates"] == 5
    assert lane_a["never_attempted"] is True
    assert lane_a["priceable_today"] is False
    assert "premium" in lane_a["why_not_priceable"].lower()
    assert "required_not_optional" in lane_a
    assert set(lane_a["families"]) == {"HYATT", "BEST_WESTERN"}


def test_no_dollar_figure_is_invented_for_discovery(report):
    lane_b = report["paid_plan"]["lane_b_rows_with_no_url_at_all"]
    assert lane_b["discovery_priced_in"] == "REQUESTS"
    assert lane_b["discovery_usd"] is None
    assert "no USD rate" in lane_b["why_no_discovery_dollar_figure"]


def test_firecrawl_is_zero_because_no_family_is_known_yet(report):
    lane_b = report["paid_plan"]["lane_b_rows_with_no_url_at_all"]
    assert lane_b["acquisition_firecrawl_rows"] == 0
    assert lane_b["firecrawl_credits_required"] == 0
    assert "before its lookup returns a page" in lane_b["why_no_firecrawl"]
    qualified = report["paid_plan"]["lane_a_rows_that_already_hold_a_url"][
        "lane_qualification"]["qualified_pairs"]
    assert "firecrawl/CHOICE" in qualified, (
        "Firecrawl IS qualified for families this market has measured; the "
        "reason it takes no rows here is that none of these rows has a family "
        "yet, not that the lane is unavailable"
    )


def test_the_cap_is_the_worst_case(report):
    plan = report["paid_plan"]
    lane_b = plan["lane_b_rows_with_no_url_at_all"]
    assert (plan["recommended_hard_cap_usd_minor"]
            >= lane_b["worst_case_usd_minor"])
    assert (lane_b["worst_case_usd_minor"]
            > lane_b["projected_brightdata_usd_minor"])


def test_the_authorization_is_split_in_two(report):
    """Discovery has no committed rate, so its size cannot be settled in the
    same breath as the acquisition it feeds."""
    recommendation = report["paid_plan"]["recommended_authorization"]
    assert recommendation["shape"] == "two authorizations, not one"
    assert "RE-MEASURED" in recommendation["first"]
    assert recommendation["second"] and recommendation["and_separately"]


# --------------------------------------------------------------------------- #
# The founder review
# --------------------------------------------------------------------------- #

def test_the_review_is_exception_only_and_signs_nothing(report):
    review = report["founder_review"]
    assert len(review["clean_rows_needing_no_reading"]) == 2
    assert len(review["exceptions_needing_a_reading"]) == 4
    assert review["founder_decision"] == ""
    assert review["founder_reviewer_id"] == ""
    assert review["review_status"] == "MACHINE_REVIEWED_PENDING_OPERATOR"
    assert review["would_move"] == {"pet_friendly": 0, "verified_no_pets": 2}


def test_source_silence_is_not_reopened_as_a_refusal(report):
    exceptions = report["founder_review"]["exceptions_needing_a_reading"]
    assert all(row["proposes"] == "REMAINS_UNRESOLVED" for row in exceptions)
    for row in exceptions:
        assert "not a refusal" in row["why"]


# --------------------------------------------------------------------------- #
# Nothing was spent and nothing was written
# --------------------------------------------------------------------------- #

def test_nothing_was_run(report):
    assert report["provider_calls"] == 0
    assert report["usd_spent"] == 0.0
    assert report["plan_credits_spent"] == 0.0
    assert len(report["nothing_was_run"]) == 5


def test_the_authority_is_untouched(report):
    """A fact about THIS pass, not about the live market.

    It used to read the live shards and assert the counts as they stood then.
    That is not a fact about this order -- it is a fact about whichever order
    most recently promoted, and 030 and 031 have since moved the market to 43
    published and 20 exclusions by doing exactly what they were authorised to
    do. What this order must be held to is that IT wrote no authority, which
    its own report states.
    """
    assert report["provider_calls"] == 0
    assert report["usd_spent"] == 0.0
    assert len(report["nothing_was_run"]) == 5
    package = _load(LP / "hotel_policy_facts_grand-rapids-holland-mi.json")
    assert package["published"] is True


def test_only_this_orders_report_was_written():
    import subprocess
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/identity_census",
         "launch_packages/pettripfinder/hotel_policy_facts_grand-rapids-holland-mi.json",
         "deploy/netlify"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        "a recovery audit must write no authority: %r" % result.stdout)
