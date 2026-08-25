"""PTF-LOUISVILLE-COVERAGE-EXPANSION-003 -- what a cohort costs before it runs.

The plan's job is to be wrong in public rather than in private: it states the
projection in both currencies, names the balance that will actually bind, and
proves the cohort buys nothing a previous pass already answered. These tests are
mostly about the distinction that check turns on -- a property that was ATTEMPTED
and a property that was ANSWERED are not the same property, and treating them the
same either fails the check on every legitimate retry or lets a paid answer be
bought twice.
"""

from __future__ import annotations

import json

from scripts.pettripfinder.acquisition import cohort_cost_plan as CP


def plan(*cohort, overlay_keys=(), terminal=("VALID", "POLICY_NOT_FOUND",
                                             "IDENTITY_MISMATCH")):
    return {
        "market_id": "louisville-ky",
        "work_order": "PTF-LOUISVILLE-COVERAGE-EXPANSION-003",
        "run_id": "louisville-expansion-003",
        "cohort_rule": {"terminal_prior_outcomes": list(terminal)},
        "url_overlay": {"rows": [{"identity_key": k} for k in overlay_keys]},
        "preflight": {"checks": [
            {"check": "balance_covers_the_remaining_cap", "ok": False,
             "detail": "balance 494 cents against a 1000 cent cap"}]},
        "cohort": list(cohort),
    }


def row(key, provider="brightdata_browser", family="HILTON"):
    return {"identity_key": key, "provider": provider, "family": family,
            "canonical_name": key.title()}


class TestProjection:
    def test_a_credit_billed_lane_draws_nothing_from_the_dollar_cap(self):
        document = CP.build(plan(row("a", provider="firecrawl", family="CHOICE")),
                            {"results": []}, authorised_cap_usd=10)
        lane = document["lanes"][0]
        assert lane["billing"] == CP.CREDIT_BILLED
        assert document["projection"]["at_registry_rates_usd_minor"] == 0
        assert document["credit_billed_properties"] == 1

    def test_the_measured_unit_comes_from_the_previous_pass_arithmetic(self):
        previous = {"spend": {"binding_usd_minor": 881}, "attempted": 58,
                    "results": [], "deferred": []}
        assert CP.measured_unit_usd_minor(previous) == 15.19

    def test_a_pass_that_attempted_nothing_measures_nothing(self):
        assert CP.measured_unit_usd_minor(
            {"spend": {"binding_usd_minor": 0}, "attempted": 0}) is None

    def test_the_worst_case_includes_a_fallback_attempt_on_every_property(self):
        document = CP.build(plan(row("a"), row("b")), {"results": []},
                            authorised_cap_usd=10)
        projection = document["projection"]
        assert projection["unlocker_fallback_exposure_usd_minor"] > 0
        assert (projection["worst_case_usd_minor"]
                > projection["at_registry_rates_usd_minor"])


class TestRecommendedCap:
    def test_a_cap_above_the_vendor_balance_is_lowered_to_the_balance(self):
        document = CP.build(plan(row("a")), {"results": []},
                            authorised_cap_usd=10)
        assert document["vendor_balance_usd_minor"] == 494
        assert document["recommended_cap_usd_minor"] == 444
        assert "below the authorised ceiling" in document["recommended_cap_why"]

    def test_a_balance_that_covers_the_ceiling_leaves_the_ceiling_alone(self):
        document = CP.build(plan(row("a")), {"results": []},
                            authorised_cap_usd=4)
        assert document["recommended_cap_usd_minor"] == 400


class TestDoubleBuy:
    def test_a_property_a_prior_pass_answered_is_a_defect(self):
        document = CP.build(plan(row("a")),
                            {"results": [{"identity_key": "a",
                                          "outcome": "VALID"}]},
                            authorised_cap_usd=10)
        check = document["double_buy_check"]
        assert check["no_property_is_bought_twice"] is False
        assert check["already_answered_by_a_prior_pass"] == ["a"]

    def test_a_property_that_was_attempted_and_answered_nothing_is_a_retry(self):
        document = CP.build(plan(row("a")),
                            {"results": [{"identity_key": "a",
                                          "outcome": "ACCESS_DENIED"}]},
                            authorised_cap_usd=10)
        check = document["double_buy_check"]
        assert check["no_property_is_bought_twice"] is True
        assert check["retries_of_attempts_that_answered_nothing"] == {
            "a": "ACCESS_DENIED"}

    def test_a_property_already_in_the_journal_is_a_defect(self, tmp_path):
        journal = tmp_path / "journal.jsonl"
        journal.write_text(json.dumps({"identity_key": "a", "outcome": "VALID"})
                           + "\n", encoding="utf-8")
        document = CP.build(plan(row("a")), {"results": []},
                            authorised_cap_usd=10, journal_path=journal)
        check = document["double_buy_check"]
        assert check["already_journalled_in_this_run_dir"] == ["a"]
        assert check["no_property_is_bought_twice"] is False


class TestProvenance:
    def test_the_cohort_is_split_by_where_each_property_came_from(self):
        previous = {"results": [{"identity_key": "retried",
                                 "outcome": "UNEXPECTED_PAGE"}],
                    "deferred": ["deferred"], "spend": {}, "attempted": 0}
        document = CP.build(
            plan(row("recovered"), row("deferred"), row("retried")),
            {"results": []}, previous=previous, authorised_cap_usd=10)
        counts = document["cohort_provenance"]["counts"]
        assert counts["newly_routed_by_url_recovery"] == 0
        assert counts["previously_deferred_by_the_cap"] == 1
        assert counts["retried_after_an_attempt_that_answered_nothing"] == 1
        assert counts["routed_before_and_never_attempted"] == 1

    def test_a_deferred_entry_may_be_a_bare_key_or_a_row(self):
        for deferred in (["deferred"], [{"identity_key": "deferred"}]):
            document = CP.build(plan(row("deferred")), {"results": []},
                                previous={"deferred": deferred, "results": []},
                                authorised_cap_usd=10)
            assert document["cohort_provenance"]["counts"][
                "previously_deferred_by_the_cap"] == 1

    def test_a_url_recovery_that_routed_a_row_is_named_as_its_source(self):
        document = CP.build(plan(row("recovered"), overlay_keys=("recovered",)),
                            {"results": []},
                            previous={"results": [], "deferred": []},
                            authorised_cap_usd=10)
        assert document["cohort_provenance"]["newly_routed_by_url_recovery"] == [
            "recovered"]
