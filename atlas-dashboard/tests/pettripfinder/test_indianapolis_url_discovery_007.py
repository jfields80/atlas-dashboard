# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PAID-OFFICIAL-URL-DISCOVERY-007.

The plan half of these tests exists to keep two refusals from eroding. This
work order was asked for a unit cost and an expected yield, and the honest
answer to both is "not known here":

  * no USD rate for Google Places is recorded anywhere in this repo -- it
    budgets Places in REQUESTS -- so the plan is denominated in requests and
    the dollar line stays null until someone reads the billing console;
  * no market has ever run a TARGETED per-identity Places lookup, so the
    expected yield is UNKNOWN. The one historical datum (St. Louis, 5 of 60)
    came from mining a cache built for a different purpose, and all five of
    those bound on a telephone that 138 of these 143 rows do not have.

A later run that quietly fills either number in with an estimate is the failure
these tests are here to catch.

The exception half pins the direction of the answer: resolving the nine makes
Indianapolis LESS routed, not more, because four of them are wrong routes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plan():
    return _load("indianapolis_in_url_discovery_plan_007.json")


@pytest.fixture(scope="module")
def rulings():
    return _load("indianapolis_in_exception_resolution_007.json")


class TestNothingWasBoughtOrAuthorised:

    def test_the_plan_spends_nothing_and_authorises_nothing(self, plan):
        assert plan["nothing_was_fetched"] is True
        assert plan["usd_spent"] == 0.0
        assert plan["provider_calls"] == 0
        assert plan["this_is_not_an_authorization"] is True

    def test_the_rulings_decide_nothing(self, rulings):
        assert rulings["usd_spent"] == 0.0
        assert "PROPOSED" in rulings["nothing_is_decided_by_this_file"]


class TestTheMethod:

    def test_the_only_provider_that_can_find_a_url_is_places(self, plan):
        assert plan["method"]["provider"] == "GOOGLE_PLACES"
        assert plan["method"]["field_that_answers_this"] == "places.websiteUri"
        assert "websiteUri" in " ".join(plan["method"]["field_mask"])

    def test_the_acquisition_providers_cannot_do_this_job(self, plan):
        why = plan["method"]["why_this_one"]
        assert "brightdata_browser" in why and "firecrawl" in why
        assert "none of them can find one" in why

    def test_ota_and_directory_pages_are_refused_by_name(self, plan):
        rejected = plan["method"]["rejected_url_shapes"]
        assert "booking.com" in rejected["third_party_booking"]
        assert "tripadvisor.com" in rejected["social_or_directory"]


class TestTheTwoRefusals:
    """The heart of this work order."""

    def test_no_usd_unit_cost_is_invented(self, plan):
        cost = plan["unit_cost"]
        assert cost["usd_per_request"] is None
        assert cost["recorded_in_this_repo"] is False
        assert cost["denominated_in"] == "provider requests"

    def test_no_yield_is_invented(self, plan):
        y = plan["expected_yield"]
        assert y["targeted_lookup_hit_rate"] == "UNKNOWN"
        assert y["targeted_lookup_bind_rate"] == "UNKNOWN"

    def test_the_one_historical_datum_is_reported_and_disclaimed(self, plan):
        datum = plan["expected_yield"]["the_one_historical_datum"]
        assert datum["market"] == "st-louis-mo"
        assert datum["url_less_rows"] == 60 and datum["recovered"] == 5
        assert datum["binding_counts"] == {"PHONE": 5}
        assert "does not carry across" in datum["why_it_does_not_transfer"]

    def test_option_b_refuses_to_be_sized_without_a_measurement(self, plan):
        option = plan["options"]["B_enough_to_unlock_about_30_candidates"]
        assert option["identities"] is None
        assert option["provider_requests"] is None
        assert "fabricated yield" in option["why_it_cannot_be_sized_yet"]


class TestTheCohortAndItsRisk:

    def test_the_whole_cohort_is_new_spend(self, plan):
        guard = plan["repeat_spend_guard"]
        assert plan["url_less_identities"] == 143
        assert guard["already_paid_reusable_discovery_lookups"] == 0
        assert guard["true_new_paid_lookup_cohort"] == 143

    def test_the_paid_ledger_does_not_cover_discovery(self, plan):
        """The gap that must be closed before any money moves."""
        guard = plan["repeat_spend_guard"]
        assert guard["ledger_covers_discovery_lookups"] is False
        assert set(guard["paid_attempt_ledger_lanes"]) == {
            "brightdata_browser", "brightdata_web_unlocker", "firecrawl"}
        assert "BEFORE authorising any spend" in guard["THE GAP"]

    def test_the_binding_key_that_worked_before_is_almost_absent_here(self, plan):
        binding = plan["binding_readiness"]
        assert binding["can_bind_on_telephone"] == 5
        assert binding["must_bind_on_name_and_postal"] == 138
        assert binding["identities"] == 143

    def test_the_options_are_a_sample_an_unknown_and_the_full_cohort(self, plan):
        options = plan["options"]
        assert options["A_qualification_sample"]["identities"] == 25
        assert options["A_qualification_sample"]["provider_requests"] == 25
        assert options["C_full_cohort"]["identities"] == 143
        assert options["C_full_cohort"]["provider_requests"] == 143

    def test_the_sample_is_stratified_and_prefers_rows_with_a_telephone(self, plan):
        option = plan["options"]["A_qualification_sample"]
        assert len(option["stratified_by_family"]) >= 5
        assert option["carries_a_telephone"] >= 1

    def test_the_worst_case_is_stated_as_zero_usable_urls(self, plan):
        worst = plan["worst_case"]
        assert worst["full_cohort_requests"] == 143
        assert "0 usable URLs" in worst["worst_case_outcome"]


class TestTheNineExceptions:

    def test_all_nine_are_ruled_on(self, rulings):
        assert rulings["exceptions"] == 9
        assert len(rulings["rulings"]) == 9

    def test_eight_need_no_spend_and_one_needs_new_evidence(self, rulings):
        assert rulings["resolvable_without_spend"] == 8
        assert rulings["need_new_evidence"] == 1
        bare = [r for r in rulings["rulings"] if not r["resolvable_without_spend"]]
        assert bare[0]["identity_key"] == "towneplace suites"

    def test_four_are_decidable_on_a_sanctioned_key(self, rulings):
        by = rulings["by_decidability"]
        assert by["MACHINE_DECIDABLE_ON_A_SANCTIONED_KEY"] == 4
        assert by["NEEDS_A_FOUNDER_RULING"] == 4
        assert by["NEEDS_NEW_EVIDENCE"] == 1

    def test_the_residence_inn_dispute_is_really_a_duplicate(self, rulings):
        """It was carried as 5224-versus-5228. Two sanctioned keys say one
        building: a shared telephone and a shared Marriott property code."""
        r = [x for x in rulings["rulings"]
             if x["identity_key"] == "residence inn indianapolis airport"][0]
        assert r["kind"] == "DUPLICATE_IDENTITY"
        assert r["decidable"] == "MACHINE_DECIDABLE_ON_A_SANCTIONED_KEY"
        assert "3172441500" in r["identity_evidence"]
        assert "indap" in r["identity_evidence"]

    def test_the_hampton_duplicate_dissolves_on_a_shared_telephone(self, rulings):
        r = [x for x in rulings["rulings"]
             if x["identity_key"] == "hampton inn indianapolis southwest plainfield"][0]
        assert r["decidable"] == "MACHINE_DECIDABLE_ON_A_SANCTIONED_KEY"
        assert "3178399993" in r["identity_evidence"]

    def test_the_dual_brand_building_is_left_to_the_founder(self, rulings):
        r = [x for x in rulings["rulings"]
             if x["identity_key"] == "hyatt house indianapolis downtown"][0]
        assert r["decidable"] == "NEEDS_A_FOUNDER_RULING"
        assert r["creates_a_newly_routable_property"] is True

    def test_resolving_them_makes_the_market_less_routed_not_more(self, rulings):
        pool = rulings["effect_on_the_unroutable_pool"]
        assert pool["before"] == 143
        assert pool["rows_whose_wrong_url_is_cleared"] == 4
        assert pool["rows_merged_away"] == 1
        assert pool["after"] == 146

    def test_no_exception_produces_a_pet_friendly_candidate(self, rulings):
        assert rulings["new_pet_friendly_candidates"] == 0

    def test_only_the_hyatt_ruling_moves_the_payable_count(self, rulings):
        effect = rulings["payable_effect"]
        assert effect["before"] == 33
        assert effect["after_if_every_proposal_is_accepted"] == 34
        assert "Hyatt" in effect["what_changes"]
