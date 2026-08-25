"""PTF-MILWAUKEE-RESUME-007 -- resuming Milwaukee without choosing lanes.

The risk in a resume run is not that it fails; it is that it quietly does
something other than what it reports.

  * It could pick providers itself. Everything here goes through
    ``router.route_property``, so the route table chooses and this module only
    chooses the WORK.
  * It could report properties it never attempted as failures, making the
    primary provider look worse than the evidence supports. The fifty-six
    properties whose configured primary is the forbidden provider are counted
    as BLOCKED and are excluded from every rate.
  * It could project a 0% escalation rate off four observations. Zero events
    bounds a rate, it does not fix one, and the difference compounds at fifty
    markets.
  * It could quietly spend past a hard cap. The cap is cumulative for the
    MARKET and its anchor outlives the process, or ten runs of ten properties
    could each spend the whole cap and each report itself inside it.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import failures as F
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder import milwaukee_resume_007 as RESUME

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT = (REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
          / "reports" / "ptf_milwaukee_provider_utilization_007.json")


class TestTheRunnerChoosesWorkNotLanes:
    def test_it_acquires_only_through_the_router(self):
        source = inspect.getsource(RESUME)
        assert "ROUTER.route_property" in source
        # No direct provider call anywhere: that would bypass the ladder, the
        # attempt budget and the escalation rule all at once.
        assert "PROVIDERS.get(" not in source
        assert "capture_property" not in source

    def test_eligibility_is_read_from_the_live_registry(self):
        """Not from a list in this file, which could drift from the route
        table and send a property down a lane nobody configured."""
        source = inspect.getsource(RESUME.partition_remaining)
        assert "REGISTRY.resolve" in source

    def test_it_never_names_the_forbidden_provider_as_a_target(self):
        assert RESUME.FORBIDDEN == PROVIDERS.BRIGHTDATA_BROWSER
        assert RESUME.FIRECRAWL == PROVIDERS.FIRECRAWL

    def test_the_remaining_set_is_derived_from_the_queue_minus_the_journal(self):
        split = RESUME.partition_remaining()
        assert split["eligible"] or split["blocked"]
        for row in split["eligible"]:
            assert row["route_primary"] == PROVIDERS.FIRECRAWL
        for row in split["blocked"]:
            assert row["route_primary"] != PROVIDERS.FIRECRAWL
            assert row["blocked_reason"]


class TestTheSpendCapSurvivesTheProcess:
    def test_the_market_anchor_is_not_reset_by_this_run(self):
        """The cap is $15 for the MARKET. Re-anchoring here would zero the
        cumulative figure and let this run spend the whole cap again."""
        source = inspect.getsource(RESUME.run)
        assert "anchor_zone_costs() is None" in source
        assert "refusing to spend" in source

    def test_the_cap_is_checked_before_each_property_not_after(self):
        source = inspect.getsource(RESUME.run)
        before = source.index("spent = meter.spent_usd_minor()")
        acquire = source.index("ROUTER.route_property")
        assert before < acquire

    def test_unreadable_telemetry_stops_the_run_rather_than_reading_as_zero(self):
        source = inspect.getsource(RESUME.run)
        assert "spent is None" in source
        assert "spending blind" in source

    def test_the_cap_is_the_market_cap_unchanged(self):
        assert RESUME.HARD_CAP_USD_MINOR == 1500


class TestTheCommittedUtilizationReport:
    def _doc(self):
        if not REPORT.is_file():
            pytest.skip("resume not run in this worktree")
        return json.loads(REPORT.read_text(encoding="utf-8-sig"))

    def test_blocked_properties_are_not_counted_as_failures(self):
        """Counting fifty-six untried properties as failures would understate
        the primary provider on lanes it was never given."""
        doc = self._doc()
        e, t = doc["eligibility"], doc["totals"]
        assert e["eligible_firecrawl_first"] + e["blocked"] == e["remaining_in_queue"]
        assert t["total_properties_processed"] <= e["eligible_firecrawl_first"]
        assert t["unresolved_manual_review"] + t["acquired"] == \
            t["total_properties_processed"]

    def test_the_rates_are_computed_over_processed_properties_only(self):
        t = self._doc()["totals"]
        assert t["firecrawl_success_rate_pct"] == round(
            100.0 * t["firecrawl_only_successes"] / t["total_properties_processed"], 1)

    def test_no_forbidden_provider_call_was_made(self):
        doc = self._doc()
        assert doc["attempts"]["bright_data_browser_calls"] == 0
        for row in doc["per_property"]:
            assert PROVIDERS.BRIGHTDATA_BROWSER not in row["providers_tried"]

    def test_every_property_records_which_provider_served_it(self):
        for row in self._doc()["per_property"]:
            assert "provider_used" in row
            assert "firecrawl_attempts" in row
            assert "bright_data_attempts" in row

    def test_attempts_never_exceed_the_routes_budget(self):
        for row in self._doc()["per_property"]:
            assert row["firecrawl_attempts"] <= 3, row["identity_key"]

    def test_fallback_reasons_are_classified_by_failure_family(self):
        reasons = self._doc()["fallback_reasons"]
        assert "by_failure" in reasons and "by_failure_class" in reasons
        for failure in reasons["by_failure"]:
            assert F.may_escalate(failure), (
                "%s stops the ladder and can never have caused a fallback"
                % failure)

    def test_currencies_are_reported_separately(self):
        cost = self._doc()["cost"]
        assert cost["firecrawl_credits"] is not None
        assert "currencies_are_not_combined" in cost
        assert "bright_data_spent_usd_minor_month_to_date" in cost

    def test_the_measured_credits_survived_a_report_rebuild(self):
        """A rebuild has nothing left to measure and must not overwrite the
        measurement with a zero."""
        assert self._doc()["cost"]["firecrawl_credits"] > 0

    def test_nothing_was_published_and_no_route_moved(self):
        doc = self._doc()
        assert doc["routes_changed"] is False
        assert doc["authority_written"] is False
        assert doc["policies_published"] is False


class TestTheProjectionDoesNotOverclaim:
    def _doc(self):
        if not REPORT.is_file():
            pytest.skip("resume not run in this worktree")
        return json.loads(REPORT.read_text(encoding="utf-8-sig"))

    def test_it_is_not_based_on_this_run_alone(self):
        """Four observations is not a rate. The basis is every natural Choice
        acquisition made under the applied three-attempt route."""
        p = self._doc()["projection"]
        assert RESUME.CHOICE_NATURAL_ACQUISITIONS > 4
        assert str(RESUME.CHOICE_NATURAL_ACQUISITIONS) in p["basis"]

    def test_zero_events_is_reported_as_a_bound_not_as_zero(self):
        p = self._doc()["projection"]
        assert p["choice_escalations_observed"] == 0
        assert p["choice_escalation_rate"] == 0.0
        bound = p["choice_escalation_rate_upper_bound_95pct"]
        assert bound is not None and bound > 0
        assert p["why_a_bound_and_not_a_rate"]

    def test_every_horizon_carries_both_the_estimate_and_the_bound(self):
        for name, row in self._doc()["projection"]["per_market"].items():
            assert row["choice_bright_data_escalations_upper_bound_95pct"] >= \
                row["choice_bright_data_escalations_expected"], name
            assert row["total_bright_data_usd_upper_bound_95pct"] >= \
                row["total_bright_data_usd_expected"], name

    def test_the_non_choice_majority_is_not_hidden(self):
        """Choice is 15 of 127. A projection that reported only the Choice lane
        would imply a market costs almost nothing."""
        p = self._doc()["projection"]
        assert p["assumptions"]["non_choice_per_market"] > \
            p["assumptions"]["choice_per_market"]
        for row in p["per_market"].values():
            assert row["non_choice_properties_still_on_bright_data"] > 0
            assert row["non_choice_bright_data_usd_expected"] > 0
        assert "measured nothing about them" in p["the_number_that_actually_matters"]

    def test_it_scales_linearly_and_says_it_is_a_planning_figure(self):
        """Each row is rounded independently, so scaling a rounded one-market
        figure cannot match the fifty-market row to the cent. The claim worth
        holding is that the underlying model is linear, within that rounding."""
        per = self._doc()["projection"]["per_market"]
        one = per["1_comparable_markets"]["non_choice_bright_data_usd_expected"]
        fifty = per["50_comparable_markets"]["non_choice_bright_data_usd_expected"]
        assert abs(fifty - one * 50) <= 50 * 0.005 + 0.01
        assert "not a quote" in \
            self._doc()["projection"]["assumptions"]["comparable_market"]
