"""PTF-CINCINNATI-BRIGHTDATA-PILOT-014 -- Cincinnati's first paid measurement.

Twelve properties, $1.08, one Bright Data browser attempt each. The pressure in
a pilot like this runs toward a single headline number -- "6 of 12, 50%" -- and
these tests exist because that number would have been useless.

Marriott and Hilton both returned three publication-grade records, and the
resemblance is a coincidence. Marriott's five misses are a ~250 character
challenge page: the lane never reached the property, and no reader could have
helped. Hilton's one miss is a complete 6,032 character page that does not
publish a pet policy: the lane worked perfectly and the hotel is silent. A
blended rate prices a bot wall and a silent hotel identically, and only one of
them can be bought around.

So the assertions here are mostly about refusing to merge things: access from
extraction, a measured rate from a hypothesis about retries, and a cap from
three vendor meters that disagree with each other.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_brightdata_pilot_014 as M

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"
REPORT = PKG / "markets" / "reports" / "cincinnati_brightdata_pilot_014.json"
OBSERVATIONS = (PKG / "markets" / "reports"
                / "cincinnati_brightdata_pilot_014_observations.json")
LEDGER = PKG / "ptf_paid_attempt_ledger_001.json"

CAP_USD = 3.00
ATTEMPTS = 12


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def report():
    return _load(REPORT)


@pytest.fixture(scope="module")
def observations():
    return _load(OBSERVATIONS)


# --------------------------------------------------------------- the spending

def test_the_cap_was_not_breached(report):
    """Every meter, not the friendliest one."""
    cap = report["cap_invariant"]
    assert cap["breached"] is False
    assert cap["cap_usd"] == CAP_USD
    spend = report["spend"]
    assert spend["prepaid_balance_delta_usd"] <= CAP_USD
    assert spend["runner_measured_usd"] <= CAP_USD
    assert cap["largest_meter_usd"] <= CAP_USD


def test_the_three_meters_disagree_and_all_three_are_reported(report):
    """A single figure here would be a choice about which vendor lie to tell."""
    spend = report["spend"]
    assert spend["prepaid_balance_delta_usd"] == 0.78
    assert spend["runner_measured_usd"] == 1.08
    # Sizing uses the LARGER, so a cohort priced from this pilot cannot
    # overrun when the cheaper meter turns out to be the lagging one.
    assert spend["sizing_rate_usd_per_attempt"] == \
        spend["usd_per_attempt_by_runner"]
    assert spend["sizing_rate_usd_per_attempt"] >= \
        spend["usd_per_attempt_by_balance"]


def test_exactly_twelve_attempts_and_no_more(report):
    assert report["authorization"]["properties_attempted"] == ATTEMPTS
    assert report["authorization"]["properties_max"] == ATTEMPTS
    assert report["authorization"]["attempts_per_row"] == 1
    assert sum(report["outcome_counts"].values()) == ATTEMPTS


def test_escalation_was_forbidden_not_merely_unused(report):
    """The committed registry offers Web Unlocker; the order forbade it.

    Relying on "it did not happen to escalate" would have left the constraint
    to luck on the first refusal, and there were five refusals.
    """
    assert "FORBIDDEN" in report["authorization"]["escalation"]
    assert report["authorization"]["lane"] == M.LANE


# ------------------------------------------------- access is not extraction

def test_the_two_brands_failed_for_unrelated_reasons(report):
    """The whole point of measuring them apart."""
    marriott = report["measurement_by_brand"]["MARRIOTT"]
    hilton = report["measurement_by_brand"]["HILTON"]

    # Same headline, opposite meaning.
    assert marriott["publication_grade"] == hilton["publication_grade"] == 3

    # Marriott: the lane could not reach five properties at all.
    assert marriott["access_failed"] == 5
    assert marriott["source_silent"] == 0
    # Every page it DID reach converted. The reader is not the bottleneck.
    assert marriott["extraction_per_page_reached"]["point"] == 1.0

    # Hilton: the lane reached everything; one hotel publishes nothing.
    assert hilton["access_failed"] == 0
    assert hilton["source_silent"] == 1
    assert hilton["access_per_attempt"]["point"] == 1.0


def test_a_silent_page_is_never_counted_as_a_lane_failure(observations):
    """The Cincinnatian returned a full page. That is the hotel's answer."""
    row = next(o for o in observations["observations"]
               if o["identity_key"] == "the cincinnatian hotel")
    assert row["classification"] == "SOURCE_SILENT"
    assert row["outcome"] == "POLICY_NOT_FOUND"
    # A challenge page is a few hundred characters; this is a real page.
    assert row["body_chars"] > M.WALL_CHARS
    assert row["publication_grade"] is False


def test_the_denied_rows_really_were_walls(observations):
    """Corroborated by size, so ACCESS_FAILED is not just a label."""
    denied = [o for o in observations["observations"]
              if o["classification"] == "ACCESS_FAILED"]
    assert len(denied) == 5
    for row in denied:
        assert row["brand"] == "MARRIOTT"
        assert row["body_chars"] < M.WALL_CHARS
        assert row["policy_block"] == ""


# ------------------------------------------- a hypothesis stays a hypothesis

def test_the_retry_hypothesis_is_not_reported_as_a_measurement(report):
    """It would raise Marriott from 37.5% to ~76%, and it is untested.

    The order authorised exactly one attempt per row. That makes the retry
    question unanswerable here, and an unanswerable question must not be
    answered in the recommendation.
    """
    pattern = report["marriott_access_pattern"]
    assert pattern["hypothesis"] == "INDEPENDENT_PER_SESSION_CHALLENGE"
    assert pattern["not_tested"]
    assert "HYPOTHESIS" in pattern["why_it_matters"]
    assert report["recommendations"]["MARRIOTT"]["recommendation"] == \
        "RETRY_PROBE_BEFORE_SCALE"


def test_the_throttling_explanation_was_ruled_out_on_evidence(report):
    """Not merely asserted: the first two attempts failed.

    Cumulative rate limiting cannot explain a failure that happens before any
    volume has accumulated.
    """
    evidence = " ".join(report["marriott_access_pattern"]["evidence"])
    assert "FIRST TWO" in evidence
    assert "throttling" in evidence


def test_sizing_uses_the_lower_bound_not_the_point_estimate(report):
    """Twelve trials do not license a point rate."""
    for brand, band in report["reprice"].items():
        stats = report["measurement_by_brand"][brand]["yield_per_attempt"]
        assert band["expected_records_low"] <= band["expected_records_point"]
        assert stats["low"] < stats["point"] < stats["high"]


def test_the_recommendations_differ_because_the_findings_do(report):
    """Buying four cheap certain rows and thirty-four uncertain ones are not
    the same decision, and one recommendation for both would hide that."""
    hilton = report["recommendations"]["HILTON"]
    marriott = report["recommendations"]["MARRIOTT"]
    assert hilton["recommendation"] == "BUY_THE_REMAINDER"
    assert hilton["rows"] == 4
    assert marriott["recommendation"] != hilton["recommendation"]
    assert marriott["do_not"]


# ------------------------------------------------------- what it did not do

def test_no_cincinnati_authority_was_mutated(report):
    """Phase 10 forbade it, and the pilot's own artifact says so."""
    assert report["authority_mutation"].startswith("NONE")


def test_the_market_totals_are_untouched_by_this_order():
    """99 published / 49 no-pets / 154 resolved, exactly as SPLIT-013 left it."""
    counts = _load(PKG / "cincinnati_final_partition_001.json")["final_state_counts"]
    assert counts["PUBLISHED_PET_FRIENDLY"] == 99
    assert counts["VERIFIED_NO_PETS"] == 49
    assert counts["OUT_OF_CURRENT_CATEGORY"] == 6
    assert sum(counts.values()) == 257
    assert _load(AUTH / "identity_routing.json")["count"] == 80


def test_nothing_bought_was_published(observations):
    """Six publication-grade blocks were acquired and none was applied.

    They are worth about a dollar and they are NOT authority until a founder
    rules on them.
    """
    package = {h["identity_key"]
               for h in _load(PKG / "hotel_policy_facts_cincinnati-oh.json")["hotels"]}
    excluded = {e["normalized_name"]
                for e in _load(AUTH / "hotel_exclusions.json")["exclusions"]}
    for row in observations["observations"]:
        assert row["identity_key"] not in package, row["identity_key"]
        assert row["identity_key"] not in excluded, row["identity_key"]
    assert observations["applied"].startswith("NOTHING")


# ------------------------------------------------------ the money is recorded

def test_every_paid_attempt_is_in_the_cross_run_ledger():
    """Cincinnati had zero paid attempts before this order and has twelve now.

    An unrecorded paid attempt is money a later run spends again.
    """
    attempts = _load(LEDGER)["attempts"]
    cincinnati = [a for a in attempts if a.get("market_id") == "cincinnati-oh"]
    assert len(cincinnati) == ATTEMPTS
    assert len({a["identity_key"] for a in cincinnati}) == ATTEMPTS


def test_the_evidence_was_kept_but_the_captures_were_not(observations):
    """Six blocks with digests, so the next order need not re-buy them."""
    assert observations["with_policy_block"] == 6
    kept = [o for o in observations["observations"] if o["policy_block"]]
    assert len({o["block_sha256"] for o in kept}) == 6
    for row in kept:
        assert row["document_sha256"]
        assert row["locator_strategy"]
    # The rendered HTML and screenshots are deliberately absent.
    assert "NOT committed" in observations["what_this_is"]


def test_the_unresolved_questions_were_handed_on_not_guessed(observations):
    """A deposit and a non-refundable fee are two charges; the label names both.

    Resolving that here would be inventing a founder ruling out of a parse.
    """
    questions = " ".join(observations["open_questions_for_the_application_order"])
    assert "deposit and a non-refundable fee are two different charges" in questions
    assert "2-4 unstated" in questions or "nights 2-4" in questions


# ---------------------------------------------------------------- the maths

def test_wilson_is_an_interval_not_a_point():
    band = M.wilson(3, 8)
    assert band["point"] == 0.375
    assert band["low"] < band["point"] < band["high"]
    # Small samples must produce wide intervals; a narrow one here would mean
    # the arithmetic is wrong.
    assert band["high"] - band["low"] > 0.5


def test_wilson_on_no_trials_claims_nothing():
    band = M.wilson(0, 0)
    assert band["point"] is None
    assert (band["low"], band["high"]) == (0.0, 1.0)


def test_repricing_a_brand_this_pilot_never_measured_refuses():
    """Quoting one brand's luck at another is how a cohort gets mispriced."""
    measured = M.measure([
        {"brand": "HILTON", "outcome": "VALID", "publication_grade": True},
    ])
    with pytest.raises(M.PilotError):
        M.reprice({"HYATT": 4}, measured, 0.09)


def test_classification_separates_the_three_states():
    assert M.classify({"outcome": "ACCESS_DENIED"}) == "ACCESS_FAILED"
    assert M.classify({"outcome": "POLICY_NOT_FOUND"}) == "SOURCE_SILENT"
    assert M.classify({"outcome": "VALID",
                       "publication_grade": True}) == "PUBLICATION_GRADE"
    # A VALID page that did not reach publication grade is none of the three.
    assert M.classify({"outcome": "VALID",
                       "publication_grade": False}) == "OTHER"


def test_the_remaining_cohort_was_rebuilt_not_quoted_forward(report):
    """Three orders in this lineage have slipped by quoting a stale subtotal."""
    remaining = report["remaining_cohort"]
    assert remaining["marriott"] + remaining["hilton"] == remaining["total"] == 38
    assert "rebuilt" in remaining["derivation"]
    routes = [r for r in _load(AUTH / "identity_routing.json")["routes"]
              if r["status"] == "ROUTING_CONFIRMED"]
    partition = {i["identity_key"]: i for i in
                 _load(PKG / "cincinnati_final_partition_001.json")["items"]}
    live = [r for r in routes
            if not partition[r["hotel_ref"]["identity_key"]]["resolved"]
            and r["brand"] in ("MARRIOTT", "HILTON")]
    assert len(live) == 50          # 38 remaining + the 12 this pilot bought
