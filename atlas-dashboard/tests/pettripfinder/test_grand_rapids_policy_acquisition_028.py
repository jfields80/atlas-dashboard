# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-POLICY-ACQUISITION-028 -- fetching the twenty pages already paid to find.

THE HEADLINE IS A NEGATIVE ONE AND THE TESTS PIN IT. Seven new pet-friendly
candidates take this market to 42 against a target of 43. It is short by one,
and a later pass that quietly reports 43 would be reading something this
evidence does not say.

WHAT THE MONEY BOUGHT. 20 of 20 payable, 20 attempted, 13 publication-grade,
170 cents measured against a $6.50 authorisation. The cap tests are here
because the operating cap was deliberately set BELOW the authorisation -- the
runner refuses to arm a cap the vendor balance cannot cover -- and a reader
should be able to see that was a choice rather than a mistake.

THE FINDING WORTH MORE THAN THE SEVEN. All six IDENTITY_MISMATCH rows came back
from a page that names this property and were declined on a street SUFFIX:
"4155 28th St., S.E." against "4155 28th Street". Their rendered HTML is on
disk. That is a zero-cost reading, and it is deliberately NOT taken here -- a
rule widened during the run whose count it would raise is a rule nothing has
qualified. The tests assert both halves: that the evidence was recorded, and
that no rule moved.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_policy_acquisition_028 as ACQ  # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
PREFLIGHT = LP / "grand_rapids_holland_mi_acquisition_preflight_028.json"
RESULT = LP / "grand_rapids_holland_mi_policy_acquisition_028.json"
RUN_REPORT = LP / "grand_rapids_holland_mi_market_acquisition_028.json"
STORE = LP / "grand_rapids_holland_mi_observation_store_028.json"
COHORT = LP / "grand_rapids_holland_mi_authorized_cohort_028.json"
OVERLAY = LP / "grand_rapids_holland_mi_recovered_url_overlay_028.json"


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def preflight():
    return _load(PREFLIGHT)


@pytest.fixture(scope="module")
def result():
    return _load(RESULT)


@pytest.fixture(scope="module")
def run():
    return _load(RUN_REPORT)


# --------------------------------------------------------------------------- #
# Pre-flight
# --------------------------------------------------------------------------- #

def test_twenty_unique_identities_and_twenty_unique_pages(preflight):
    checks = preflight["preflight"]
    assert checks["cohort_size_before_suppression"] == 20
    assert checks["unique_identities"] == 20
    assert checks["unique_canonical_urls"] == 20
    assert checks["payable_size"] == 20
    assert checks["withheld"] == 0
    assert dict(checks["by_verdict"]) == {ACQ.PAYABLE: 20}


def test_every_identity_still_binds(preflight):
    """The Places bind is re-run from saved evidence, so a URL that only bound
    under a rule this branch has since changed is caught before the money."""
    assert preflight["preflight"]["every_identity_still_binds"] is True
    for row in preflight["preflight"]["rows"]:
        assert row["binding_still_holds"] is True
        assert row["binding"] in ("PHONE", "NAME_AND_POSTAL_CODE")
        assert "binds" in row["binding_check"]


def test_nothing_already_paid_and_no_duplicate_page(preflight):
    verdicts = {row["verdict"] for row in preflight["preflight"]["rows"]}
    assert ACQ.ALREADY_PAID not in verdicts
    assert ACQ.DUPLICATE_PAGE not in verdicts
    assert ACQ.REUSABLE not in verdicts
    assert ACQ.BINDING_LAPSED not in verdicts


def test_the_runner_reached_the_same_verdict_independently(run):
    """This module's pre-flight and the runner's own authorised-cohort gate are
    two different readings of the same ledger. They agree."""
    gate = run["authorized_cohort"]
    assert gate["authorised"] == 20
    assert gate["payable"] == 20
    assert gate["suppressed_by_paid_history"] == 0
    assert gate["authorised_but_not_eligible"] == []
    assert gate["validation"]["ok"] is True


def test_the_census_was_not_edited(run):
    overlay = run["url_overlay"]
    assert overlay["offered"] == 20 and overlay["applied"] == 20
    assert overlay["unroutable_census_urls_displaced"] == 0
    assert "census file is unchanged" in overlay["note"]


# --------------------------------------------------------------------------- #
# The lane plan
# --------------------------------------------------------------------------- #

def test_the_lane_split_is_derived_and_both_derivations_agree(preflight, run):
    lanes = preflight["lane_plan"]
    assert lanes["firecrawl_rows"] == 11
    assert lanes["brightdata_browser_rows"] == 9
    assert lanes["brightdata_web_unlocker_rows"] == 0
    assert lanes["other_rows"] == 0
    assert run["cohort_by_provider"] == {"brightdata_browser": 9,
                                         "firecrawl": 11}


def test_firecrawl_took_only_families_the_registry_has_qualified(preflight):
    """The condition the order attaches to using it."""
    lanes = preflight["lane_plan"]
    assert lanes["firecrawl_families_are_all_qualified"] is True
    qualified = set(lanes["qualified_pairs"])
    for assignment in lanes["assignments"]:
        if assignment["primary_lane"] == "firecrawl":
            assert "firecrawl/%s" % assignment["family"] in qualified


def test_the_worst_case_fits_under_the_authorised_cap(preflight):
    lanes = preflight["lane_plan"]
    assert lanes["authorised_cap_usd_minor"] == ACQ.CAP_USD_MINOR == 650
    assert lanes["worst_case_usd_minor"] <= lanes["authorised_cap_usd_minor"]
    assert lanes["worst_case_fits_under_the_cap"] is True
    assert lanes["projected_usd_minor"] <= lanes["fallback_usd_minor"]
    assert lanes["fallback_usd_minor"] <= lanes["worst_case_usd_minor"]


# --------------------------------------------------------------------------- #
# The spend
# --------------------------------------------------------------------------- #

def test_the_cap_held_and_the_spend_is_measured(result):
    spend = result["spend"]
    assert spend["measured_usd_minor"] == 170
    assert spend["plan_credits"] == 11.0
    assert spend["cap_held"] is True
    assert spend["under_the_founder_cap"] is True
    assert spend["measured_usd_minor"] <= spend["operating_cap_usd_minor"]
    assert spend["operating_cap_usd_minor"] <= spend["founder_cap_usd_minor"]


def test_the_operating_cap_was_lower_on_purpose(result):
    """The runner refuses to arm a cap the vendor balance cannot cover, and the
    balance read 641 cents against the authorised 650. A cap is a maximum."""
    why = result["spend"]["why_the_operating_cap_is_lower"]
    assert "641" in why and "650" in why
    assert "spending under it needs no permission" in why.lower()


def test_the_binding_meter_is_the_larger_of_the_two(result):
    """The vendor's zone meter settles minutes after a session, so until it
    does the estimate is the only number that exists and the cap binds on the
    larger. Pittsburgh learned this when the meter rose after the run."""
    spend = result["spend"]
    assert spend["binding_usd_minor"] >= spend["estimated_usd_minor"]
    assert "settles" in spend["lag_note"]


# --------------------------------------------------------------------------- #
# The classification
# --------------------------------------------------------------------------- #

def test_thirteen_rows_were_acquired_at_publication_grade(result):
    cohort = result["cohort"]
    assert cohort["attempted"] == 20
    assert cohort["publication_grade"] == 13
    assert dict(cohort["outcome_counts"]) == {"VALID": 13,
                                              "IDENTITY_MISMATCH": 6,
                                              "UNEXPECTED_PAGE": 1}


def test_the_classification_is_seven_and_six_with_nothing_left_over(result):
    klass = result["classification"]
    assert klass["pet_friendly"] == 7
    assert klass["verified_no_pets"] == 6
    assert klass["policy_not_found"] == 0
    assert klass["holds"] == 0
    assert klass["pet_friendly"] + klass["verified_no_pets"] == 13
    assert klass["identity_or_routing_issues"] == 7


def test_a_class_needs_the_state_and_the_fact_to_agree():
    """020 published a VERIFIED_NO_PETS off a store its ruling had not edited.
    The guard is that neither the readiness state nor the fact is believed
    alone."""
    assert ACQ.classify({"readiness": {"state": "POLICY_CONFIRMED"},
                         "observation": {"extraction": {"pets_allowed": True}}
                         })[0] == ACQ.PET_FRIENDLY
    assert ACQ.classify({"readiness": {"state": "POLICY_NEGATIVE_CONFIRMED"},
                         "observation": {"extraction": {"pets_allowed": False}}
                         })[0] == ACQ.VERIFIED_NO_PETS
    # A state that says one thing and a fact that says nothing is a HOLD, not
    # a guess in either direction.
    assert ACQ.classify({"readiness": {"state": "POLICY_CONFIRMED"},
                         "observation": {"extraction": {"pets_allowed": None}}
                         })[0] == ACQ.HOLD
    assert ACQ.classify({"readiness": {"state": "POLICY_NEGATIVE_CONFIRMED"},
                         "observation": {"extraction": {"pets_allowed": True}}
                         })[0] == ACQ.HOLD


def test_every_acquired_row_is_publication_grade_and_membrane_valid(result):
    for row in result["classification"]["rows"]:
        assert row["publication_grade"] == "PUBLICATION_GRADE_CONFIRMED"
        assert row["membrane"] == "VALID"


def test_the_review_is_exception_only_and_publishes_nothing(result):
    review = result["founder_review"]
    assert review["shape"] == "exception-only"
    # Six confirmed and six negative-confirmed route themselves; the one
    # POLICY_CONFIRMED_WITH_AMBIGUITY needs a person.
    assert review["clean_rows_that_route_themselves"] == 12
    assert len(review["exceptions_needing_a_reading"]) == 1
    assert review["exceptions_needing_a_reading"][0]["readiness"] == \
        "POLICY_CONFIRMED_WITH_AMBIGUITY"
    assert review["founder_decision"] == ""
    assert review["founder_reviewer_id"] == ""
    assert review["review_status"] == "MACHINE_REVIEWED_PENDING_OPERATOR"
    assert "a FACT ruling is not a RECORD approval" in review["nothing_was_published"]


# --------------------------------------------------------------------------- #
# Target 43 -- and the one it falls short by
# --------------------------------------------------------------------------- #

def test_the_market_lands_at_42_which_is_one_short(result):
    """The headline, and a negative one. A later pass that reports 43 without
    new evidence is reading something this run does not say."""
    target = result["target_43"]
    assert target["published_today"] == 35
    assert target["target"] == 43
    assert target["new_pet_friendly_candidates"] == 7
    assert target["projected_final_pet_friendly"] == 42
    assert target["target_reached"] is False
    assert target["short_by"] == 1


# --------------------------------------------------------------------------- #
# The unresolved seven
# --------------------------------------------------------------------------- #

def test_every_refused_row_returned_a_page_naming_this_property(result):
    unresolved = result["unresolved_rows"]
    assert unresolved["count"] == 7
    mismatches = [r for r in unresolved["rows"]
                  if r["outcome"] == "IDENTITY_MISMATCH"]
    assert len(mismatches) == 6
    for row in mismatches:
        assert row["name_on_page"], "the page named a property"
        assert row["address_on_page"], "and stated an address"
        assert "does not agree with expected" in row["why"]


def test_the_bytes_are_on_disk_so_the_reading_would_cost_nothing(result):
    """The difference between a finding worth acting on for free and one that
    costs money. Read from disk, not assumed: this project has both cases."""
    unresolved = result["unresolved_rows"]
    assert unresolved["bytes_on_disk"] == 6
    on_disk = [r for r in unresolved["rows"] if r["bytes_are_on_disk"]]
    assert len(on_disk) == 6
    for row in on_disk:
        assert row["declined_directory"]
        assert (REPO_ROOT / row["declined_directory"] / "rendered.html").is_file()


def test_no_rule_was_widened_to_collect_them(result):
    finding = result["unresolved_rows"]["finding"]
    assert "NO RULE IS WIDENED HERE" in finding
    assert "a rule nothing has qualified" in finding


def test_the_two_index_pages_are_called_out_as_a_weaker_case(result):
    """The Extended Stay America pages are titled "Explore Our Nationwide Hotel
    Locations". A policy read off an index that lists many properties could
    belong to any of them, and lumping them with the four single-property
    pages would overstate what a re-read can settle."""
    note = result["unresolved_rows"]["two_are_not_the_same_case"]
    assert "Explore Our Nationwide Hotel Locations" in note
    esa = [r for r in result["unresolved_rows"]["rows"] if r["brand"] == "ESA"]
    assert len(esa) == 2
    for row in esa:
        assert "Nationwide Hotel Locations" in row["page_title"]


# --------------------------------------------------------------------------- #
# Nothing else moved
# --------------------------------------------------------------------------- #

def test_no_places_request_was_made(result):
    joined = " ".join(result["nothing_else_was_run"])
    assert "no Google Places request" in joined
    ledger = _load(LP / "ptf_discovery_attempt_ledger_001.json")
    ours = [a for a in ledger["attempts"]
            if a["market_id"] == "grand-rapids-holland-mi"]
    assert len(ours) == 40, "still the 40 bought by 026 and 027, and no more"


def test_no_authority_was_written():
    import subprocess
    result_ = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/identity_census",
         "launch_packages/pettripfinder/hotel_policy_facts_grand-rapids-holland-mi.json",
         "deploy/netlify"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result_.returncode == 0, result_.stderr
    assert result_.stdout.strip() == "", (
        "an acquisition writes no authority: %r" % result_.stdout)


def test_the_published_count_did_not_move():
    package = _load(LP / "hotel_policy_facts_grand-rapids-holland-mi.json")
    assert package["count"] == 35
