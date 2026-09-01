# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-BACKLOG-COST-PLAN-015 -- pricing the last six profiles.

Nothing here spends. The tests that matter are the ones that stop the forecast
from flattering the purchase it is attached to:

    THE DENOMINATOR IS ATTEMPTS. 012 attempted 50 and 20 became founder-signed
    pet-friendly rows. Quoting the 20/32 valid rate, or the 20/31 publication-
    grade rate, would price the plan on a denominator the buyer never pays.

    NINE-FOR-NINE IS A FLOOR OF 70%, NOT A PROMISE OF 100%. Both plans are
    sized on the Wilson lower bound, and a family nobody has attempted here
    contributes ZERO rather than a borrowed average.

    A CEILING THAT BOUNDS NOTHING IS NOT REPORTED. Zero-for-one gives a
    rule-of-three ceiling of 300%; printing that as a percentage would read
    like evidence. Those come back None.

    THE CHEAP LANE IS UNAVAILABLE, NOT DECLINED. routes.json gives Firecrawl
    CHOICE, IHG and WYNDHAM; the backlog has none of them. Zero credits is a
    fact about the committed registry, and the test pins it to the registry so
    it cannot quietly become a preference.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder.indianapolis_promoted_state import (
    PROMOTED_PET_FRIENDLY, PROMOTED_VERIFIED_NO_PETS, CENSUS)

from scripts.pettripfinder import indianapolis_backlog_cost_plan_015 as M
from scripts.pettripfinder.acquisition import registry as REGISTRY

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plan():
    return _load("indianapolis_in_backlog_cost_plan_015.json")


class TestItSpendsNothingAndAuthorisesNothing:

    def test_no_provider_was_called(self, plan):
        assert plan["provider_calls"] == 0
        assert plan["usd_spent"] == 0

    def test_it_says_plainly_that_it_is_not_an_authorisation(self, plan):
        assert plan["status"] == "PLAN_ONLY_NO_SPEND_AUTHORISED"
        note = plan["nothing_is_authorised_by_this_file"]
        assert "authorises no spend" in note
        assert "a runner may not bill against it" in note.lower()


class TestTheBacklogIsRebuiltExactly:

    def test_all_twenty_four_are_accounted_for_once(self, plan):
        backlog = plan["backlog"]
        assert backlog["original_count"] == 24
        assert len(backlog["rows"]) == 24
        keys = [r["identity_key"] for r in backlog["rows"]]
        assert len(keys) == len(set(keys))

    def test_it_is_the_same_twenty_four_012_recorded(self, plan):
        recorded = {r["identity_key"] for r in
                    _load("indianapolis_in_market_acquisition_012.json")
                    ["authorized_cohort"]["backlog_rows"]}
        assert {r["identity_key"] for r in plan["backlog"]["rows"]} == recorded

    def test_every_row_carries_its_url_lane_and_routing_state(self, plan):
        for row in plan["backlog"]["rows"]:
            if not row["still_genuinely_payable"]:
                continue
            assert row["official_url"].startswith("http"), row["identity_key"]
            assert row["provider_lane"]
            assert row["routing_state"] == "ROUTED"
            assert row["prior_outcome"]
            assert row["cross_run_paid_history_match"]


class TestTheLedgerSuppressedOneAndNothingReplacedIt:

    def test_exactly_one_row_was_suppressed_as_already_paid(self, plan):
        counts = plan["backlog"]["by_decision"]
        assert counts == {"PAYABLE_FIRST_ATTEMPT": 23,
                          "SUPPRESSED_ALREADY_PAID": 1}
        assert plan["backlog"]["payable_after_ledger"] == 23

    def test_the_suppressed_row_names_the_run_that_already_paid(self, plan):
        row, = [r for r in plan["backlog"]["rows"]
                if r["decision"] == "SUPPRESSED_ALREADY_PAID"]
        assert row["identity_key"] == "residence inn by marriott indianapolis northwest"
        assert "indianapolis-in-002-pass1" in row["cross_run_paid_history_match"]
        assert row["still_genuinely_payable"] is False

    def test_the_cohort_shrank_rather_than_being_topped_up(self, plan):
        assert "SHRINKS" in plan["backlog"]["no_substitution"]
        assert len(plan["plan_a"]["identity_keys"]) == 23

    def test_every_payable_row_is_a_genuine_first_attempt(self, plan):
        for row in plan["backlog"]["rows"]:
            if row["still_genuinely_payable"]:
                assert row["prior_outcome"] == "NEVER_ATTEMPTED"
                assert row["prior_terminal_or_reusable_evidence"] == \
                    "none -- never attempted"


class TestTheEsaAirportPairAreTwoDifferentBuildings:
    """The double-buy trap: 012 bought an ESA 'airport' row and the backlog
    holds another. Same brand, same 46241, neither with a street or a phone."""

    def test_they_resolve_to_different_property_slugs(self, plan):
        bought = next(r["source_url"] for r in
                      _load("indianapolis_in_market_acquisition_012.json")["results"]
                      if r["identity_key"] ==
                      "extended stay america indianapolis airport w southern ave")
        backlog = next(r["official_url"] for r in plan["backlog"]["rows"]
                       if r["identity_key"] ==
                       "extended stay america indianapolis airport")
        assert bought != backlog
        assert bought.split("?")[0].endswith("/airport-w-southern-ave")
        assert backlog.split("?")[0].endswith("/airport")


class TestTheCheapLaneIsUnavailableNotDeclined:

    def test_no_row_qualifies_for_firecrawl(self, plan):
        assert plan["lanes"]["firecrawl"] == 0
        assert plan["plan_a"]["cost"]["firecrawl_plan_credits"] == 0
        assert plan["plan_b"]["cost"]["firecrawl_plan_credits"] == 0

    def test_the_registry_is_what_makes_it_unavailable(self, plan):
        """Pinned to routes.json so 'zero credits' can never become a taste."""
        brands = REGISTRY.load()["brands"]
        firecrawl = {b for b, spec in brands.items()
                     if spec.get("provider") == "firecrawl"}
        assert firecrawl == {"CHOICE", "IHG", "WYNDHAM"}
        present = {r["family"] for r in plan["backlog"]["rows"]
                   if r["still_genuinely_payable"]}
        assert present & firecrawl == set()
        assert present == {"HILTON", "INDEPENDENT", "ESA", "RED_ROOF", "SONESTA"}

    def test_every_payable_row_needs_the_browser_lane(self, plan):
        assert plan["lanes"]["brightdata_browser"] == 23
        assert plan["lanes"]["browser_required_rows"] == 23
        for row in plan["backlog"]["rows"]:
            if row["still_genuinely_payable"]:
                assert row["provider_lane"] == "brightdata_browser"
                assert row["fallback_lane"] == ["brightdata_web_unlocker"]


class TestTheRateArithmetic:

    def test_nine_for_nine_floors_at_about_seventy_percent(self):
        assert M.wilson_lower_bound(9, 9) == pytest.approx(0.701, abs=0.005)

    def test_a_floor_is_never_above_the_point_estimate(self):
        for k, n in ((9, 9), (4, 8), (2, 11), (0, 5), (1, 2)):
            assert M.wilson_lower_bound(k, n) <= k / n

    def test_a_smaller_sample_gives_a_lower_floor_at_the_same_rate(self):
        assert M.wilson_lower_bound(2, 2) < M.wilson_lower_bound(9, 9)

    def test_zero_trials_floors_at_zero(self):
        assert M.wilson_lower_bound(0, 0) == 0.0

    def test_a_ceiling_that_bounds_nothing_is_not_reported(self):
        assert M.rule_of_three_upper(1) is None      # would be 300%
        assert M.rule_of_three_upper(2) is None      # would be 150%
        assert M.rule_of_three_upper(5) == pytest.approx(0.6)

    def test_the_uninformative_families_say_so_instead_of_printing_a_number(self, plan):
        history = plan["family_history_indianapolis"]
        for family in ("DRURY", "MOTEL6", "ESA"):
            assert history[family]["ceiling_if_zero_observed"] is None
            assert "nothing is bounded" in history[family]["ceiling_note"]


class TestTheDenominatorIsAttempts:

    def test_the_market_rate_is_twenty_over_fifty(self, plan):
        history = plan["family_history_indianapolis"]
        assert sum(f["attempted"] for f in history.values()) == 50
        assert sum(f["pet_friendly"] for f in history.values()) == 20

    def test_it_is_not_computed_over_valid_or_publication_grade(self, plan):
        """20/32 is 63% and 20/31 is 65%. Either would price the plan on a
        denominator the buyer never pays for."""
        history = plan["family_history_indianapolis"]
        valid = sum(f["valid"] for f in history.values())
        assert valid == 32
        overall = sum(f["pet_friendly"] for f in history.values()) / 50
        assert overall == pytest.approx(0.40)
        assert overall != pytest.approx(20 / valid)

    def test_hilton_went_nine_for_nine_on_attempts(self, plan):
        hilton = plan["family_history_indianapolis"]["HILTON"]
        assert (hilton["attempted"], hilton["valid"], hilton["pet_friendly"]) \
            == (9, 9, 9)


class TestAFamilyWithNoEvidenceContributesZero:

    def test_sonesta_was_never_attempted_here(self, plan):
        assert "SONESTA" not in plan["family_history_indianapolis"]

    def test_it_contributes_zero_to_both_estimates_and_says_why(self, plan):
        row, = [c for c in plan["plan_a"]["yield"]["by_family"]
                if c["family"] == "SONESTA"]
        assert row["rows"] == 1
        assert row["indianapolis_attempts"] == 0
        assert row["expected_point"] == 0.0
        assert row["expected_floor"] == 0.0
        assert "no market average is borrowed" in row["note"]
        assert "no other market is consulted" in row["note"]


class TestSubBrandGrain:

    def test_two_words_keep_hilton_garden_inn_apart_from_hilton(self):
        assert M.sub_brand_key("hilton garden inn indianapolis airport") \
            == "hilton garden"
        assert M.sub_brand_key("hilton indianapolis hotel and suites") \
            == "hilton indianapolis"
        assert M.sub_brand_key("hampton inn indianapolis south") == "hampton inn"

    def test_a_one_word_identity_still_yields_a_key(self):
        assert M.sub_brand_key("tru") == "tru"

    def test_hilton_garden_inn_has_no_indianapolis_precedent(self):
        assert "hilton garden" not in M.sub_brand_history()

    def test_the_sub_brands_that_do_have_one_are_perfect(self):
        history = M.sub_brand_history()
        for key in ("hampton inn", "home2 suites", "homewood suites"):
            assert history[key]["rate"] == 1.0


class TestPlanB:

    def test_it_is_derivable_and_reaches_the_gap_conservatively(self, plan):
        selection = plan["plan_b"]["selection"]
        assert selection["derivable"] is True
        assert selection["need"] == 6
        assert selection["cumulative_conservative_yield"] >= 6

    def test_it_is_the_smallest_such_subset(self, plan):
        """One row fewer must fall short, or it is not a minimum."""
        selection = plan["plan_b"]["selection"]
        floor = plan["family_history_indianapolis"]["HILTON"][
            "pet_friendly_rate_wilson_lower_95"]
        assert (selection["count"] - 1) * floor < 6 <= selection["count"] * floor

    def test_it_never_draws_on_a_family_with_a_zero_floor(self, plan):
        rows = {r["identity_key"]: r for r in plan["backlog"]["rows"]}
        for key in plan["plan_b"]["identity_keys"]:
            family = rows[key]["family"]
            assert plan["family_history_indianapolis"][family][
                "pet_friendly_rate_wilson_lower_95"] > 0

    def test_the_tiebreak_prefers_evidenced_sub_brands_at_equal_price(self, plan):
        """Six of the nine are Hampton (3/3) and Home2 (2/2). Alphabetical
        order would have taken five Hilton Garden Inns instead, for the same
        money and less evidence."""
        precedent = plan["plan_b"]["sub_brand_precedent"]
        assert len(precedent["with_same_sub_brand_precedent"]) == 6
        assert len(precedent["without_any_sub_brand_precedent"]) == 3

    def test_the_weak_rows_are_named_rather_than_buried(self, plan):
        precedent = plan["plan_b"]["sub_brand_precedent"]
        without = {r["identity_key"] for r in
                   precedent["without_any_sub_brand_precedent"]}
        assert all("hilton garden inn" in k for k in without)
        assert "weakest part of the estimate" in precedent["caveat"]

    def test_the_rule_states_that_no_name_is_read(self, plan):
        rule = plan["plan_b"]["selection"]["rule"]
        assert "No hotel name is read for pet-friendliness" in rule


class TestTheSelectionIsDeterministic:

    def test_the_same_input_yields_the_same_cohort(self, plan):
        rows = [r for r in plan["backlog"]["rows"] if r["still_genuinely_payable"]]
        history = plan["family_history_indianapolis"]
        subs = M.sub_brand_history()
        first = M.minimum_cohort(rows, history, 6, subs)["identity_keys"]
        assert first == plan["plan_b"]["identity_keys"]

    def test_shuffling_the_input_does_not_change_the_cohort(self, plan):
        """If input order could change what we buy, the rule is not a rule."""
        rows = [r for r in plan["backlog"]["rows"] if r["still_genuinely_payable"]]
        history = plan["family_history_indianapolis"]
        subs = M.sub_brand_history()
        reversed_ = M.minimum_cohort(list(reversed(rows)), history, 6, subs)
        assert reversed_["identity_keys"] == plan["plan_b"]["identity_keys"]


class TestTheCosts:

    def test_plan_a_prices_twenty_three_dollar_billed_rows(self, plan):
        cost = plan["plan_a"]["cost"]
        assert cost["rows"] == 23 and cost["brightdata_rows"] == 23
        assert cost["projected_usd_minor_at_registry"] == 368.0
        assert cost["worst_case_usd_minor"] == 483.0
        assert cost["safe_cap_usd_minor"] == 500

    def test_plan_b_prices_nine(self, plan):
        cost = plan["plan_b"]["cost"]
        assert cost["rows"] == 9
        assert cost["projected_usd_minor_at_registry"] == 144.0
        assert cost["worst_case_usd_minor"] == 189.0
        assert cost["safe_cap_usd_minor"] == 200

    def test_the_safe_cap_covers_the_worst_case_in_both_plans(self, plan):
        for name in ("plan_a", "plan_b"):
            cost = plan[name]["cost"]
            assert cost["safe_cap_usd_minor"] >= cost["worst_case_usd_minor"]

    def test_the_cheaper_price_is_a_range_end_not_a_settled_rate(self, plan):
        """13.41c is the measured unit the 012 cost plan carried GOING IN. It
        is not what 012 settled at: that run's dollars are not attributable per
        row (its meter was seeded 222c from earlier sessions) and the Bright
        Data zone meter settles upward afterwards. The plan bills at the
        registry's 16c and says which number is which."""
        cost = plan["plan_a"]["cost"]
        assert cost["projected_usd_minor_at_012_plan_measured_unit"] < \
            cost["projected_usd_minor_at_registry"]
        note = cost["what_the_two_prices_are"]
        assert "not a settled rate" in note
        assert "no cap is ever set from it" in note

    def test_every_cap_is_set_from_the_registry_price(self, plan):
        for name in ("plan_a", "plan_b"):
            cost = plan[name]["cost"]
            assert cost["safe_cap_usd_minor"] >= (
                cost["projected_usd_minor_at_registry"]
                + cost["fallback_exposure_usd_minor"])


class TestTheRecommendation:

    def test_plan_a_is_recommended_for_margin_not_for_yield(self, plan):
        recommendation = plan["recommendation"]
        assert recommendation["recommended"] == "PLAN A"
        assert recommendation["difference_usd_minor"] == 294.0
        assert "margin is worth more than the money" in recommendation["why"]

    def test_plan_a_carries_real_margin_over_the_gap(self, plan):
        assert plan["plan_a"]["yield"]["expected_pet_friendly_conservative"] > 6
        assert plan["plan_b"]["yield"]["expected_pet_friendly_conservative"] \
            == pytest.approx(6.31, abs=0.05)

    def test_the_projection_is_labelled_a_forecast(self, plan):
        after = plan["projected_total_after"]
        assert after["plan_a_conservative"] == pytest.approx(53.5, abs=0.1)
        assert after["plan_b_conservative"] == pytest.approx(50.3, abs=0.1)
        assert "FORECASTS" in after["caveat"]
        assert "founder may decline" in after["caveat"]


class TestTheOtherWorkIsKeptSeparate:

    def test_the_esa_hold_is_reported_and_not_costed(self, plan):
        esa = plan["separate_work_not_in_this_plan"]["esa_fee_only_hold"]
        assert esa["cost"].startswith("zero")
        assert "READING question" in esa["why_not_here"]
        assert esa["identity_key"] not in plan["plan_a"]["identity_keys"]

    def test_the_fourteen_mismatches_are_routing_repair_not_acquisition(self, plan):
        rows = plan["separate_work_not_in_this_plan"]["identity_mismatch_rows"]
        assert rows["count"] == 14
        assert rows["state"] == "routing repair, not acquisition"
        assert len(rows["evidence_that_some_are_OUR_defect"]) >= 2
        assert "paid ledger exists to stop" in rows["why_not_here"]

    def test_the_mismatch_count_matches_the_012_run(self):
        run = _load("indianapolis_in_market_acquisition_012.json")
        assert run["outcome_counts"]["IDENTITY_MISMATCH"] == 14


class TestNothingMoved:

    def test_the_package_is_still_twenty_four(self):
        assert len(_load("hotel_policy_facts_indianapolis-in.json")["hotels"]) == PROMOTED_PET_FRIENDLY

    def test_the_exclusion_shard_is_still_twenty_four(self):
        assert _load(
            "markets/authority/indianapolis-in/hotel_exclusions.json")["count"] == PROMOTED_VERIFIED_NO_PETS

    def test_the_census_is_still_257(self):
        assert _load("identity_census/indianapolis-in.json")["count"] == CENSUS  # 257 until PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 promoted the reviewed shadow

    def test_the_current_state_is_the_verified_forty_four(self, plan):
        state = plan["current_state"]
        assert state["promoted_pet_friendly"] == 24
        assert state["signed_pet_friendly_013_014"] == 20
        assert state["projected_total"] == 44
        assert state["gap"] == 6


class TestTheCohortArtifactsAreNotAuthorisations:
    """Three exact-cohort documents ship with this plan. None of them can buy
    anything, and that is enforced by the guard rather than by a comment."""

    @pytest.mark.parametrize("name,count", [
        ("indianapolis_in_backlog_cohort_015.json", 24),
        ("indianapolis_in_backlog_plan_a_cohort_015.json", 23),
        ("indianapolis_in_backlog_plan_b_cohort_015.json", 9),
    ])
    def test_each_names_its_exact_rows(self, name, count):
        doc = _load(name)
        assert doc["schema"] == "ptf-authorized-cohort/1.0"
        assert doc["cohort_count"] == count == len(doc["identity_keys"])
        assert len(set(doc["identity_keys"])) == count

    @pytest.mark.parametrize("name", [
        "indianapolis_in_backlog_cohort_015.json",
        "indianapolis_in_backlog_plan_a_cohort_015.json",
        "indianapolis_in_backlog_plan_b_cohort_015.json",
    ])
    def test_a_runner_pointed_at_one_refuses_to_spend(self, name):
        from scripts.pettripfinder.acquisition import authorized_cohort as AC
        verdict = AC.validate(_load(name), market_id="indianapolis-in",
                              cap_usd_minor=500, plan_credit_cap=0)
        assert verdict["ok"] is False
        refused = [c for c in verdict["checks"] if not c["ok"]]
        assert [c["check"] for c in refused] == [
            "run_cap_within_the_authorised_cap"]
        assert "authorised 0c" in refused[0]["detail"]

    def test_the_zero_cap_is_declared_deliberate(self):
        doc = _load("indianapolis_in_backlog_plan_a_cohort_015.json")
        assert doc["authorization"]["cap_usd_minor"] == 0
        assert "ON PURPOSE" in doc["provenance"]["authorises_nothing"]

    def test_the_plan_a_cohort_matches_what_the_dry_run_derived(self):
        """Same fingerprint the planner computed, so the priced cohort and the
        named cohort cannot drift apart."""
        doc = _load("indianapolis_in_backlog_plan_a_cohort_015.json")
        plan = _load("indianapolis_in_backlog_cost_plan_015.json")
        assert doc["identity_keys"] == sorted(plan["plan_a"]["identity_keys"])

    def test_plan_b_is_a_subset_of_plan_a(self):
        a = set(_load("indianapolis_in_backlog_plan_a_cohort_015.json")["identity_keys"])
        b = set(_load("indianapolis_in_backlog_plan_b_cohort_015.json")["identity_keys"])
        assert b < a

    def test_the_suppressed_row_is_in_the_24_and_in_neither_plan(self):
        full = set(_load("indianapolis_in_backlog_cohort_015.json")["identity_keys"])
        a = set(_load("indianapolis_in_backlog_plan_a_cohort_015.json")["identity_keys"])
        key = "residence inn by marriott indianapolis northwest"
        assert key in full and key not in a
