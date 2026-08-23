"""PTF-ST-LOUIS-PAID-ACQUISITION-002 -- the paid cohort, the cap, the breaker.

Three claims carry the money, and each has a way of being wrong that no earlier
test caught:

* the COHORT is the routed population minus the properties whose question is
  already answered -- and it must partition that population exactly, or the
  report undercounts what was never tried;
* the CAP binds on the larger of a measured figure and an estimate, because the
  vendor's meter settles minutes after a session and a cap on a lagging meter
  overshoots;
* the BREAKER stops a family only when the family is a WALL, never when it is
  merely having a bad run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import market_paid_acquisition as PA
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.brightdata import outcomes as O


def routed(identity_key, brand="MARRIOTT", provider="brightdata_browser"):
    return {"identity_key": identity_key, "canonical_name": identity_key.title(),
            "brand": brand, "corridor": "c", "source_url": "https://x/%s" % identity_key,
            "routing_state": MR.ROUTED, "provider": provider, "reader": "generic"}


class TestCohort:
    def test_cohort_and_settled_partition_the_routed_population(self):
        entries = [routed("a"), routed("b"), routed("c"),
                   dict(routed("d"), routing_state=MR.ROUTE_NEEDS_OFFICIAL_URL)]
        prior = {"results": [{"identity_key": "a", "outcome": O.VALID}]}
        cohort, settled = PA.derive_cohort(entries, prior)
        assert len(cohort) + len(settled) == 3
        assert {r["identity_key"] for r in cohort} == {"b", "c"}
        assert {r["identity_key"] for r in settled} == {"a"}

    @pytest.mark.parametrize("outcome", [O.VALID, O.POLICY_NOT_FOUND,
                                         O.IDENTITY_MISMATCH])
    def test_an_answered_question_is_not_bought_a_second_time(self, outcome):
        prior = {"results": [{"identity_key": "a", "outcome": outcome}]}
        cohort, settled = PA.derive_cohort([routed("a")], prior)
        assert cohort == []
        assert settled[0]["prior_outcome"] == outcome

    @pytest.mark.parametrize("outcome", [O.UNHYDRATED, O.ACCESS_DENIED,
                                         O.NAVIGATION_FAILED, O.UNEXPECTED_PAGE])
    def test_a_failure_to_reach_the_page_is_exactly_what_a_paid_lane_is_for(
            self, outcome):
        prior = {"results": [{"identity_key": "a", "outcome": outcome}]}
        cohort, settled = PA.derive_cohort([routed("a")], prior)
        assert [r["identity_key"] for r in cohort] == ["a"]
        assert settled == []

    def test_a_property_no_prior_pass_touched_is_in_the_cohort(self):
        cohort, _settled = PA.derive_cohort([routed("a")], {"results": []})
        assert cohort[0]["prior_outcome"] == "NEVER_ATTEMPTED"

    def test_the_terminal_set_is_named_rather_than_inferred(self):
        prior = {"results": [{"identity_key": "a", "outcome": O.UNHYDRATED}]}
        cohort, settled = PA.derive_cohort([routed("a")], prior,
                                           terminal=[O.UNHYDRATED])
        assert cohort == [] and len(settled) == 1


class TestQueueOrder:
    def _cohort(self, *entries):
        cohort, _settled = PA.derive_cohort(entries, {"results": []})
        return cohort

    def test_a_credit_billed_lane_runs_before_any_dollar_lane(self):
        cohort = self._cohort(
            routed("z", brand="MARRIOTT", provider="brightdata_browser"),
            routed("a", brand="CHOICE", provider="firecrawl"))
        order = [r["identity_key"] for r in PA.order_queue(cohort, ["MARRIOTT"])]
        assert order == ["a", "z"]

    def test_within_the_dollar_lanes_the_named_priority_decides(self):
        cohort = self._cohort(routed("b", brand="INDEP:x.com"),
                              routed("a", brand="MARRIOTT"))
        order = [r["family"] for r in PA.order_queue(cohort,
                                                     ["MARRIOTT", "INDEPENDENT"])]
        assert order == ["MARRIOTT", "INDEPENDENT"]

    def test_every_independent_is_one_family_not_one_family_each(self):
        assert PA.family_of("INDEP:a.com") == PA.family_of("INDEP:b.com")
        assert PA.family_of("MARRIOTT") == "MARRIOTT"


class TestSpendMeter:
    def _anchor(self, tmp_path, costs):
        path = tmp_path / "anchor.json"
        path.write_text(json.dumps({"zone_costs_usd_minor": costs}),
                        encoding="utf-8")
        return PA.SpendMeter(anchor_path=path, zones=tuple(costs))

    def test_the_anchor_stores_per_zone_costs_under_the_key_it_reads_back(
            self, tmp_path, monkeypatch):
        # The defect this pins: an anchor written from UsageSnapshot.to_dict
        # carries one zone's cost under a different key, so anchor_zone_costs
        # reads back None and measured spend is unknown for the whole run --
        # which, under a hard cap, must never be mistaken for zero.
        meter = PA.SpendMeter(anchor_path=tmp_path / "a.json", zones=("z1",))
        monkeypatch.setattr(meter, "zone_costs", lambda label: {"z1": 100})
        meter.anchor("label")
        stored = json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))
        assert stored["zone_costs_usd_minor"] == {"z1": 100}
        assert meter.measured_usd_minor("later") is not None

    def test_measured_spend_is_growth_summed_over_every_billable_zone(
            self, tmp_path, monkeypatch):
        meter = self._anchor(tmp_path, {"z1": 100, "z2": 10})
        monkeypatch.setattr(meter, "zone_costs",
                            lambda label: {"z1": 130, "z2": 12})
        assert meter.measured_usd_minor("now") == 32

    def test_a_zone_that_cannot_be_read_makes_spend_unknown_never_zero(
            self, tmp_path, monkeypatch):
        meter = self._anchor(tmp_path, {"z1": 100, "z2": 10})
        monkeypatch.setattr(meter, "zone_costs",
                            lambda label: {"z1": 130, "z2": None})
        assert meter.measured_usd_minor("now") is None

    def test_a_zone_that_went_down_cannot_credit_another_zones_growth(
            self, tmp_path, monkeypatch):
        meter = self._anchor(tmp_path, {"z1": 100, "z2": 50})
        monkeypatch.setattr(meter, "zone_costs",
                            lambda label: {"z1": 120, "z2": 10})
        assert meter.measured_usd_minor("now") == 20

    def test_the_cap_binds_on_the_estimate_while_the_vendor_still_reads_zero(
            self, tmp_path, monkeypatch):
        meter = self._anchor(tmp_path, {"z1": 100})
        monkeypatch.setattr(meter, "zone_costs", lambda label: {"z1": 100})
        meter.estimated_usd_minor = 640.0
        view = meter.spend_view("now")
        assert view["measured_usd_minor"] == 0
        assert view["binding_usd_minor"] == 640.0
        assert view["binding_source"] == "estimated"

    def test_once_billing_settles_the_vendors_larger_figure_binds(
            self, tmp_path, monkeypatch):
        meter = self._anchor(tmp_path, {"z1": 100})
        monkeypatch.setattr(meter, "zone_costs", lambda label: {"z1": 900})
        meter.estimated_usd_minor = 640.0
        view = meter.spend_view("now")
        assert view["binding_usd_minor"] == 800
        assert view["binding_source"] == "measured"

    def test_a_property_is_charged_once_per_provider_not_once_per_attempt(
            self, tmp_path):
        # The unit is "zone delta / properties attempted", an average that
        # already includes the retries inside a property. Charging every
        # attempt would bill a three-attempt property triple, and the cap
        # would bind at roughly a third of the money actually spent.
        class Attempt:
            def __init__(self, provider):
                self.provider = provider

        meter = PA.SpendMeter(anchor_path=tmp_path / "a.json")
        meter.charge([Attempt("brightdata_browser")] * 3)
        assert meter.estimated_usd_minor == 16.0
        meter.charge([Attempt("brightdata_browser"),
                      Attempt("brightdata_web_unlocker")])
        assert meter.estimated_usd_minor == 37.0

    def test_credits_and_dollars_are_never_added_together(self, tmp_path):
        class Attempt:
            def __init__(self, provider):
                self.provider = provider

        meter = PA.SpendMeter(anchor_path=tmp_path / "a.json")
        meter.charge([Attempt("firecrawl")])
        assert meter.estimated_usd_minor == 0.0
        assert meter.estimated_credits == 1.0

    def test_reusing_the_last_reading_still_recomputes_the_estimate(
            self, tmp_path, monkeypatch):
        meter = self._anchor(tmp_path, {"z1": 100})
        calls = []

        def zone_costs(label):
            calls.append(label)
            return {"z1": 100}

        monkeypatch.setattr(meter, "zone_costs", zone_costs)
        meter.spend_view("first")
        meter.estimated_usd_minor = 500.0
        view = meter.spend_view("second", refresh=False)
        assert len(calls) == 1                     # the vendor was not re-asked
        assert view["binding_usd_minor"] == 500.0  # the cap still saw the truth


class TestFamilyBreaker:
    def test_a_family_failing_identically_across_the_window_is_a_wall(self):
        breaker = PA.FamilyBreaker(window=3)
        for _ in range(3):
            breaker.record("CHOICE", acquired=False, failure="ACCESS_DENIED")
        assert breaker.is_open("CHOICE")
        assert breaker.tripped["CHOICE"]["failure"] == "ACCESS_DENIED"

    def test_one_success_anywhere_in_the_window_means_it_is_not_a_wall(self):
        breaker = PA.FamilyBreaker(window=3)
        breaker.record("CHOICE", acquired=False, failure="ACCESS_DENIED")
        breaker.record("CHOICE", acquired=True, failure="")
        breaker.record("CHOICE", acquired=False, failure="ACCESS_DENIED")
        assert not breaker.is_open("CHOICE")

    def test_failing_variously_is_a_bad_run_not_a_capability_wall(self):
        breaker = PA.FamilyBreaker(window=3)
        for failure in ("ACCESS_DENIED", "POLICY_NOT_FOUND", "TIMEOUT"):
            breaker.record("HILTON", acquired=False, failure=failure)
        assert not breaker.is_open("HILTON")

    def test_one_family_tripping_never_stops_another(self):
        breaker = PA.FamilyBreaker(window=2)
        for _ in range(2):
            breaker.record("CHOICE", acquired=False, failure="ACCESS_DENIED")
        assert breaker.is_open("CHOICE")
        assert not breaker.is_open("MARRIOTT")


class TestUrlOverlay:
    def test_an_overlay_fills_only_rows_that_have_no_url(self, tmp_path):
        overlay = tmp_path / "o.json"
        overlay.write_text(json.dumps({"recoveries": [
            {"identity_key": "a", "recovered_url": "https://new/a",
             "binding": "PHONE", "evidence": {}},
            {"identity_key": "b", "recovered_url": "https://new/b",
             "binding": "PHONE", "evidence": {}}]}), encoding="utf-8")
        rows = [{"identity_key": "a", "official_url": ""},
                {"identity_key": "b", "official_url": "https://discovered/b"}]
        report = PA.apply_url_overlay(rows, str(overlay))
        assert rows[0]["official_url"] == "https://new/a"
        assert rows[1]["official_url"] == "https://discovered/b"
        assert report["applied"] == 1 and report["offered"] == 2

    def test_no_overlay_changes_nothing(self):
        rows = [{"identity_key": "a", "official_url": ""}]
        report = PA.apply_url_overlay(rows, "")
        assert rows[0]["official_url"] == ""
        assert report["applied"] == 0


class TestTarget:
    def test_an_independents_routing_label_is_never_used_as_an_identity_signal(self):
        record = PA.record_for(
            {"identity_key": "k", "canonical_name": "The Inn",
             "market_id": "m", "address": "1 Road", "postal_code": "63101",
             "phone": "3145551212", "city": "St. Louis", "state": "MO"},
            {"brand": "INDEP:theinn.com", "source_url": "https://theinn.com"})
        target = PA.target_for(record)
        assert target.identity_brand == ""
        assert target.expected_phone == "3145551212"

    def test_a_chain_keeps_its_brand_as_an_identity_signal(self):
        record = PA.record_for(
            {"identity_key": "k", "canonical_name": "AC Hotel",
             "market_id": "m", "address": "", "postal_code": "", "phone": "",
             "city": "", "state": ""},
            {"brand": "MARRIOTT", "source_url": "https://marriott.com/x"})
        assert PA.target_for(record).identity_brand == "MARRIOTT"

    def test_a_capture_target_carries_no_field_a_policy_value_could_sit_in(self):
        record = PA.record_for(
            {"identity_key": "k", "canonical_name": "X", "market_id": "m",
             "address": "", "postal_code": "", "phone": "", "city": "",
             "state": ""},
            {"brand": "MARRIOTT", "source_url": "https://marriott.com/x"})
        assert record.facts == {} and record.quotes == ()
        assert record.pets_allowed is None
