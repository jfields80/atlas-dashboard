# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-BROADER-RECOVERY-010 -- the remaining 118, and what they bought.

Two artifacts are pinned here: the discovery run itself, and the offline routing
analysis that says what the recovered URLs are worth. Neither will be re-run --
the discovery ledger now suppresses all 143 rows of the unroutable universe --
so these tests are the durable record.

The number worth arguing with is the shortfall. The qualification sample
projected 44.4% and the cohort delivered 28.8%, and the reason is in the
stratification: the 18-row name-and-postal sample seated every one of eleven
families before any family got a second row, which over-weighted the small easy
families and under-weighted Choice, Hilton and IHG -- 60 of the 118. A sample
built to prove a rule is safe is not automatically a sample that predicts a
rate, and this file records that both numbers were real.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.discovery import constants as C

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def run():
    return _load("indianapolis_in_places_broader_010.json")


@pytest.fixture(scope="module")
def gain():
    return _load("indianapolis_in_routing_gain_010.json")


@pytest.fixture(scope="module")
def ledger():
    return DAL.load(PACKAGE_DIR / "ptf_discovery_attempt_ledger_001.json")


class TestThePreflightAndTheCap:

    def test_the_cohort_is_derived_by_subtraction(self, run):
        pre = run["preflight"]
        assert pre["universe"] == 143
        assert pre["already_attempted"] == 25
        assert pre["remaining"] == 118

    def test_the_ledger_split_was_a_partition_before_any_spend(self, run):
        pre = run["preflight"]
        assert pre["partition_holds"] is True
        assert pre["payable"] + pre["suppressed_before_run"] == pre["remaining"]

    def test_none_of_the_prior_25_entered_this_cohort(self, run):
        sampled = {r["identity_key"] for r in
                   _load("indianapolis_in_discovery_replay_007.json")
                   ["qualification_sample"]["rows"]}
        ran = {r["identity_key"] for r in run["rows"] if r.get("requests_made")}
        assert sampled & ran == set()

    def test_exactly_118_requests_were_made(self, run):
        assert run["requests_made"] == 118
        assert run["authorised_request_cap"] == 118
        assert run["cap_held"] is True

    def test_the_run_used_the_009_binding_rule(self, run):
        assert run["preflight"]["presentation_variants"] is True

    def test_it_was_not_aborted(self, run):
        assert run["aborted"] == ""


class TestTheSafetyWallsHeld:

    def test_the_brand_tripwire_never_fired(self, run):
        """A bound row whose opening brand word disagrees with the census is
        how a rule that has started matching on locality alone announces
        itself. None did."""
        assert run["brand_disagreements"] == []

    def test_no_two_identities_bound_to_one_place(self, run):
        assert run["place_id_collisions"] == {}

    def test_every_bound_row_carries_a_routable_url(self, run):
        for row in run["rows"]:
            if not row.get("bound"):
                continue
            shape = MR.classify_url_shape(
                MR.normalize_source_url(row["website_uri"]))
            assert shape in MR.ROUTABLE_SHAPES, row["identity_key"]
            assert row["place_id"] and row["routing_state"] == "ROUTABLE"

    def test_every_refusal_states_a_reason(self, run):
        for row in run["rows"]:
            if row.get("requests_made") and not row.get("bound"):
                assert row["refusal_reason"], row["identity_key"]

    def test_only_the_name_and_postal_key_bound_anything(self, run):
        """No phone-bearing row was left in this cohort; the sample took all
        five."""
        assert dict(run["totals"]["by_bind_method"]) == {
            "NAME_AND_POSTAL_CODE": 34}


class TestTheMeasuredResult:

    def test_thirty_four_of_118(self, run):
        assert run["totals"]["executed"] == 118
        assert run["totals"]["bound"] == 34
        assert run["totals"]["bind_rate"] == pytest.approx(0.2881, abs=1e-4)

    def test_every_unbound_row_still_got_an_answer_from_the_provider(self, run):
        """The provider found something for all 118; the binder refused 84."""
        unbound = [r for r in run["rows"]
                   if r.get("requests_made") and not r["bound"]]
        assert len(unbound) == 84
        assert all(r["places_returned"] > 0 for r in unbound
                   if r["bind_state"] != DAL.BIND_NO_RESULT)

    def test_the_ledger_recorded_all_118(self, run, ledger):
        assert run["ledger_rows_written"] == 118
        assert len(ledger["attempts"]) == 143
        assert sum(a["paid_requests"] for a in ledger["attempts"]) == 143


class TestTheWholeUniverseIsNowProtected:

    def test_no_row_of_the_143_can_be_bought_again(self, ledger):
        rows = [{"identity_key": r["identity_key"],
                 "canonical_name": r["canonical_name"], "street": r["street"],
                 "city": r["city"], "state": "IN",
                 "postal_code": r["postal_code"], "telephone": r["telephone"]}
                for r in _load("indianapolis_in_url_recovery_report_006.json")
                ["phase_1_unroutable_inventory"]["rows"]]
        payable, suppressed = DAL.suppress(
            rows, ledger, provider="GOOGLE_PLACES", method="searchText",
            field_mask=tuple(C.GOOGLE_FIELD_MASK.split(",")))
        assert payable == []
        assert len(suppressed) == 143

    def test_failures_are_remembered_as_findings(self, ledger):
        failed = [a for a in ledger["attempts"]
                  if a["bind_state"] in DAL.ANSWERED_NEGATIVE_STATES]
        assert len(failed) == 100


class TestTheRoutingGain:

    def test_forty_seven_identities_became_routable(self, gain):
        routing = gain["routing"]
        assert routing["routing_before"] == 114
        assert routing["newly_routed"] == 47
        assert routing["routing_after"] == 161

    def test_the_url_less_count_fell_from_143_to_96(self, gain):
        routing = gain["routing"]
        assert routing["url_less_before"] == 143
        assert routing["url_less_after"] == 96

    def test_the_recovered_set_is_the_two_runs_under_the_current_rule(self, gain):
        """Thirteen from the sample -- nine bound then, four more once the
        binder compared identity instead of presentation -- plus 34."""
        assert gain["routing"]["newly_routed"] == 13 + 34

    def test_the_lane_split_comes_from_the_committed_registry(self, gain):
        split = gain["newly_routed_lane_split"]
        assert split["firecrawl"] == 17
        assert split["brightdata_browser"] == 29
        assert split["brightdata_web_unlocker"] == 0
        assert "registry's own answer" in \
            gain["minimum_next_acquisition_cohort"]["cheapest_valid_lane_note"]

    def test_the_paid_ledger_caught_one_across_the_two_ledgers(self, gain):
        """Discovery found a URL for a page policy acquisition had already
        bought. Both ledgers had to agree for that to be visible."""
        evidence = gain["policy_evidence"]
        assert evidence["suppressed_by_paid_history"] == 1
        assert evidence["genuinely_need_acquisition"] == 46

    def test_no_policy_acquisition_ran(self, gain):
        assert gain["no_policy_acquisition_ran"] is True
        assert gain["provider_calls"] == 0 and gain["usd_spent"] == 0.0


class TestTheGapToFifty:

    def test_the_rate_is_this_market_s_own_record(self, gain):
        target = gain["target_50"]
        assert target["observed_pet_friendly_rate"] == pytest.approx(0.3038,
                                                                     abs=1e-4)
        assert "79 identities attempted" in target["rate_basis"]

    def test_routing_46_is_worth_about_14_profiles(self, gain):
        target = gain["target_50"]
        assert target["current_promoted_pet_friendly"] == 24
        assert target["acquirable_cohort"] == 46
        assert target["expected_new_pet_friendly"] == 14
        assert target["expected_total"] == 38

    def test_fifty_is_still_not_reached(self, gain):
        target = gain["target_50"]
        assert target["reaches_50"] is False
        assert target["remaining_gap_after"] == 12


class TestTheMinimumNextCohort:

    def test_it_authorises_nothing(self, gain):
        plan = gain["minimum_next_acquisition_cohort"]
        assert plan["this_is_not_an_authorization"] is True

    def test_firecrawl_is_preferred_wherever_the_registry_allows_it(self, gain):
        plan = gain["minimum_next_acquisition_cohort"]
        assert plan["firecrawl_properties"] == 17
        assert plan["firecrawl_credits"] == 17.0
        assert plan["credit_billed_properties"] == 17

    def test_the_dollar_exposure_is_small_and_bounded(self, gain):
        plan = gain["minimum_next_acquisition_cohort"]
        assert plan["cohort_size"] == 46
        assert plan["dollar_billed_properties"] == 29
        assert plan["projection"]["worst_case_usd_minor"] == 609.0
        assert plan["safe_cap_usd_minor"] == 624
