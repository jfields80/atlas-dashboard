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
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL
from scripts.pettripfinder.acquisition import retry_policy as RP
from scripts.pettripfinder.acquisition import registry as REGISTRY
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

    def test_a_resume_seeds_the_estimate_with_what_earlier_sessions_spent(
            self, tmp_path, monkeypatch):
        # The defect this pins: a fresh process starts the estimate at zero, so
        # it counts only THIS session. During the vendor's settling lag that is
        # the number the cap binds on, and a cap binding on a session-local
        # figure lets a resumed run spend the whole cap AGAIN on top of what
        # earlier sessions already spent. Both meters must be cumulative or
        # max() is comparing different things.
        meter = self._anchor(tmp_path, {"z1": 100})
        monkeypatch.setattr(meter, "zone_costs", lambda label: {"z1": 341})
        monkeypatch.setattr(PA.PROVIDERS, "all_ids", lambda: ())
        PA.preflight(meter, run_id="r", cap_usd_minor=1000)
        assert meter.estimated_usd_minor == 241.0
        assert meter.seeded_usd_minor == 241.0

        # A fresh estimate would now read 16; the seeded one reads 257, which
        # is what the cap must see.
        class Attempt:
            provider = "brightdata_browser"

        meter.charge([Attempt()])
        view = meter.spend_view("now", refresh=False)
        assert view["estimated_usd_minor"] == 257.0
        assert view["this_session_usd_minor"] == 16.0

    def test_a_first_run_seeds_nothing(self, tmp_path, monkeypatch):
        meter = self._anchor(tmp_path, {"z1": 100})
        monkeypatch.setattr(meter, "zone_costs", lambda label: {"z1": 100})
        monkeypatch.setattr(PA.PROVIDERS, "all_ids", lambda: ())
        PA.preflight(meter, run_id="r", cap_usd_minor=1000)
        assert meter.seeded_usd_minor == 0.0
        assert meter.estimated_usd_minor == 0.0

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


class TestCapReservation:
    """The cap must stop BEFORE it is crossed, at the run's OWN measured rate.

    Both halves were wrong in the first version and the bill proves it: the
    St. Louis paid run stopped at 1055 cents against a 1000-cent cap. It checked
    `binding >= cap` -- a stop-when-exceeded, which `budget.Budget`'s own
    docstring rules out -- and it sized nothing, so with the vendor read every
    fifth property up to five properties could commit unwatched. The registry
    priced the Browser API at 16.0 cents from another market; these pages cost
    20.9.
    """

    def _meter(self, tmp_path, *, measured, seeded, priced, every=5):
        path = tmp_path / "anchor.json"
        path.write_text(json.dumps({"zone_costs_usd_minor": {"z1": 0}}),
                        encoding="utf-8")
        meter = PA.SpendMeter(anchor_path=path, zones=("z1",), meter_every=every)
        meter.last_measured = measured
        meter.seeded_usd_minor = seeded
        meter.priced_properties = priced
        return meter

    def test_the_rate_is_taken_from_the_run_not_from_the_registry(self, tmp_path):
        # 814 cents over 39 properties is 20.9, not the registry's 16.0.
        meter = self._meter(tmp_path, measured=1055, seeded=241, priced=39)
        assert round(meter.calibrated_unit_usd_minor(), 1) == 20.9

    def test_a_rate_from_too_few_properties_is_refused_as_noise(self, tmp_path):
        meter = self._meter(tmp_path, measured=100, seeded=0, priced=2)
        assert meter.calibrated_unit_usd_minor() is None
        # ...and the registry figure is then the honest fallback.
        assert meter.reservation_usd_minor(16.0) == 80.0

    def test_the_reservation_covers_a_whole_metering_interval(self, tmp_path):
        # The blind spot is not one property, it is every property that can run
        # between two vendor readings.
        meter = self._meter(tmp_path, measured=1055, seeded=241, priced=39)
        assert round(meter.reservation_usd_minor(16.0)) == 104   # 20.9 * 5

    def test_the_interval_is_what_scales_the_reservation(self, tmp_path):
        meter = self._meter(tmp_path, measured=1055, seeded=241, priced=39,
                            every=1)
        assert round(meter.reservation_usd_minor(16.0)) == 21

    def test_the_run_that_overshot_would_now_have_stopped_earlier(self, tmp_path):
        # Replay of the real numbers. At the last check before the overshoot the
        # run had spent about 950 cents; 950 >= 1000 was False, so it continued
        # and landed at 1055. With a reservation it stops at 950.
        meter = self._meter(tmp_path, measured=950, seeded=241, priced=34)
        reserve = meter.reservation_usd_minor(16.0)
        assert 950 < 1000                      # the old test passed here
        assert 950 + reserve > 1000            # the new one does not

    def test_a_credit_billed_lane_reserves_no_dollars(self):
        assert PA._fallback_unit({"provider": "firecrawl"}) == 0.0
        assert PA._fallback_unit({"provider": "brightdata_browser"}) == 16.0

    def test_an_unknown_provider_still_reserves_something(self):
        assert PA._fallback_unit({"provider": "nonesuch"}) == 16.0
        assert PA._fallback_unit({}) == 16.0


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


class TestTheReportDescribesTheWorkOrder:
    """A resumed run must report the JOURNAL, never just its own batch.

    This was a silent data-loss bug and it cost a whole closeout. The resumed
    St. Louis run wrote its own 39 rows as the report; the merge then saw 39
    instead of 132, and the founder package fell from 92 candidates to 47. Forty-
    five properties that had been paid for and read vanished from the market's
    current state, and every downstream artifact was quietly consistent with the
    smaller number.
    """

    def _journal(self, tmp_path, keys):
        from scripts.pettripfinder.acquisition import journal as JOURNAL
        j = JOURNAL.Journal(path=tmp_path / "journal.jsonl")
        for key in keys:
            j.append({"identity_key": key, "outcome": O.VALID,
                      "publication_grade": True, "family": "MARRIOTT",
                      "provider": "brightdata_browser", "failure": ""})
        return j

    def test_a_resume_reports_every_journalled_property_not_its_own_batch(
            self, tmp_path):
        journal = self._journal(tmp_path, ["a", "b", "c"])
        report = {"attempted": 1}
        completed = journal.read()
        report["results"] = [completed[k] for k in sorted(completed)]
        report["attempted_this_session"] = report["attempted"]
        report["attempted"] = len(completed)
        assert [r["identity_key"] for r in report["results"]] == ["a", "b", "c"]
        assert report["attempted"] == 3
        assert report["attempted_this_session"] == 1

    def test_the_journal_is_keyed_by_identity_so_a_resume_cannot_duplicate(
            self, tmp_path):
        journal = self._journal(tmp_path, ["a", "b", "a"])
        assert sorted(journal.read()) == ["a", "b"]


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

    # -- PTF-LOUISVILLE-COVERAGE-EXPANSION-003 ------------------------------- #

    def test_an_unfetchable_census_url_is_displaced_by_a_property_page(self, tmp_path):
        """Seven Louisville identities carry one OpenStreetMap tag pointing at a
        Sleep Inn in another city. A URL no lane can fetch is not something the
        overlay has to protect."""
        overlay = tmp_path / "o.json"
        overlay.write_text(json.dumps({"recoveries": [
            {"identity_key": "a",
             "recovered_url": "https://www.hilton.com/en/hotels/sdfshhf-seelbach/",
             "url_shape": "PROPERTY_PAGE", "binding": "PHONE", "evidence": {}}]}),
            encoding="utf-8")
        rows = [{"identity_key": "a", "official_url": "https://seelbachhilton.com"}]
        report = PA.apply_url_overlay(rows, str(overlay))
        assert rows[0]["official_url"].endswith("sdfshhf-seelbach/")
        assert report["applied"] == 1
        assert report["unroutable_census_urls_displaced"] == 1
        assert report["rows"][0]["displaced_census_url"] == "https://seelbachhilton.com"

    def test_a_proposal_no_lane_can_fetch_is_never_applied(self, tmp_path):
        overlay = tmp_path / "o.json"
        overlay.write_text(json.dumps({"recoveries": [
            {"identity_key": "a", "recovered_url":
             "https://www.choicehotels.com/kentucky/shepherdsville/sleep-inn-hotels",
             "url_shape": "PROPERTY_PAGE", "binding": "PHONE", "evidence": {}}]}),
            encoding="utf-8")
        rows = [{"identity_key": "a", "official_url": ""}]
        report = PA.apply_url_overlay(rows, str(overlay))
        # The overlay CLAIMS a property page; the shape is recomputed and the
        # claim is a category listing, so nothing is applied.
        assert rows[0]["official_url"] == "" and report["applied"] == 0


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


# -- PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 ------------------------------- #

class TestCostPlanGate:
    """No paid pass begins without a cost plan that describes THIS cohort."""

    def _plan(self, keys, proof=True):
        from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
        return {"schema": CP.SCHEMA,
                "cohort_keys_sha256": CP.cohort_fingerprint(keys),
                "double_buy_check": {"no_property_is_bought_twice": proof}}

    def test_no_plan_no_pass(self):
        gate = PA.cost_plan_gate(None, [routed("a")])
        assert gate["ok"] is False
        assert gate["checks"][0]["check"] == "cost_plan_present"

    def test_a_plan_over_this_cohort_with_its_proof_opens_the_gate(self):
        gate = PA.cost_plan_gate(self._plan(["a", "b"]), [routed("b"), routed("a")])
        assert gate["ok"] is True

    def test_a_plan_over_a_different_cohort_is_refused(self):
        gate = PA.cost_plan_gate(self._plan(["a"]), [routed("a"), routed("b")])
        assert gate["ok"] is False
        failed = [c["check"] for c in gate["checks"] if not c["ok"]]
        assert failed == ["cost_plan_describes_this_cohort"]

    def test_a_plan_whose_double_buy_proof_failed_is_refused(self):
        gate = PA.cost_plan_gate(self._plan(["a"], proof=False), [routed("a")])
        assert gate["ok"] is False
        failed = [c["check"] for c in gate["checks"] if not c["ok"]]
        assert failed == ["no_property_is_bought_twice"]

    def test_a_document_that_is_not_a_cost_plan_is_refused(self):
        plan = self._plan(["a"])
        plan["schema"] = "ptf-market-paid-acquisition/1.0"
        gate = PA.cost_plan_gate(plan, [routed("a")])
        assert gate["ok"] is False


class TestAlreadySettledRowsAreNeverPurchasedTwice:
    def test_settled_rows_are_outside_the_cohort_and_outside_the_plan(self):
        from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
        entries = [routed("valid"), routed("silent"), routed("wrong"), routed("fresh")]
        prior = {"results": [{"identity_key": "valid", "outcome": O.VALID},
                             {"identity_key": "silent", "outcome": O.POLICY_NOT_FOUND},
                             {"identity_key": "wrong", "outcome": O.IDENTITY_MISMATCH}]}
        cohort, settled, suppressed = PA.plan_cohort(entries, prior)
        assert [r["identity_key"] for r in cohort] == ["fresh"]
        assert {r["identity_key"] for r in settled} == {"valid", "silent", "wrong"}
        assert suppressed == []
        plan = {"market_id": "m", "cohort": cohort,
                "cohort_rule": {"terminal_prior_outcomes": list(PA.DEFAULT_TERMINAL)},
                "preflight": {"checks": []}}
        document = CP.build(plan, prior, authorised_cap_usd=10)
        assert document["double_buy_check"]["no_property_is_bought_twice"] is True
        assert document["double_buy_check"]["already_answered_by_a_prior_pass"] == []


class TestAConstrainedRegistryIsHonouredRatherThanIntended:
    """PTF-CINCINNATI-BRIGHTDATA-PILOT-014 added ``--registry``.

    That order authorised "Bright Data browser only, one attempt per row, no
    Web Unlocker escalation". The committed registry gives both bot-walled
    brands three attempts and a Web Unlocker fallback, so running under it
    would have escalated on the first refusal -- and there were five refusals.
    An authorisation the runner cannot express is an authorisation it cannot
    keep, so the narrower table is loaded through the same strict validator.
    """

    def _narrow(self, tmp_path):
        base = REGISTRY.load()
        doc = json.loads(json.dumps(base))
        doc["properties"] = dict(doc.get("properties") or {})
        doc["properties"]["walled"] = {
            "provider": "brightdata_browser",
            "fallback_providers": [],
            "forbidden_providers": ["brightdata_web_unlocker"],
            "reader": "generic",
            "max_attempts_per_provider": 1,
            "why": "the order authorised one browser attempt and no escalation",
            "measured_by": "PTF-CINCINNATI-BRIGHTDATA-PILOT-014",
        }
        path = tmp_path / "registry.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def test_the_committed_table_would_have_escalated(self):
        """The premise. Without this, the flag is solving nothing."""
        route = REGISTRY.resolve(brand="MARRIOTT",
                                 url="https://www.marriott.com/en-us/hotels/x/overview/",
                                 identity_key="walled")
        assert "brightdata_web_unlocker" in route.ladder
        assert route.max_attempts_per_provider > 1

    def test_the_narrower_table_forbids_the_escalation(self, tmp_path):
        route = REGISTRY.resolve(
            brand="MARRIOTT",
            url="https://www.marriott.com/en-us/hotels/x/overview/",
            identity_key="walled",
            registry=REGISTRY.load(self._narrow(tmp_path)))
        assert route.ladder == ("brightdata_browser",)
        assert route.max_attempts_per_provider == 1

    def test_a_constrained_table_is_still_validated(self, tmp_path):
        """A narrower table naming a provider that does not exist is refused
        HERE, not mid-run after money has moved."""
        doc = json.loads(json.dumps(REGISTRY.load()))
        doc["properties"] = {"walled": {"provider": "a_provider_that_is_not_real",
                                        "reader": "generic", "why": "w",
                                        "measured_by": "m"}}
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(REGISTRY.RegistryError):
            REGISTRY.load(path)

    def test_omitting_the_flag_keeps_the_committed_behaviour(self):
        """The flag is additive: absent it, nothing about routing changes."""
        assert REGISTRY.load() == REGISTRY.load(None)


class TestMaterialChangesAreLoadedThroughAClosedVocabulary:
    """PTF-CINCINNATI-HILTON-CLOSE-AND-MARRIOTT-RETRY-PROBE-015.

    A material change makes an already-paid page payable again. That is the
    one decision that must never be implicit, so the loader refuses an unknown
    kind, a missing reason, and a doubled assertion.
    """

    def _doc(self, tmp_path, changes):
        path = tmp_path / "material.json"
        path.write_text(json.dumps({"changes": changes}), encoding="utf-8")
        return path

    def test_a_reasoned_override_loads(self, tmp_path):
        loaded = PAL.load_material_changes(self._doc(tmp_path, [
            {"identity_key": "a", "kind": "OPERATOR_OVERRIDE",
             "reason": "controlled session retry authorised by the work order"}]))
        assert loaded == {"a": {"OPERATOR_OVERRIDE":
                                "controlled session retry authorised by the "
                                "work order"}}

    def test_an_unknown_kind_is_refused(self, tmp_path):
        with pytest.raises(PAL.PaidLedgerError):
            PAL.load_material_changes(self._doc(tmp_path, [
                {"identity_key": "a", "kind": "BECAUSE_I_SAID_SO",
                 "reason": "no"}]))

    def test_an_unreasoned_override_is_refused(self, tmp_path):
        """An override nobody has to justify is not a control."""
        with pytest.raises(PAL.PaidLedgerError):
            PAL.load_material_changes(self._doc(tmp_path, [
                {"identity_key": "a", "kind": "OPERATOR_OVERRIDE",
                 "reason": "   "}]))

    def test_the_same_kind_asserted_twice_is_refused(self, tmp_path):
        with pytest.raises(PAL.PaidLedgerError):
            PAL.load_material_changes(self._doc(tmp_path, [
                {"identity_key": "a", "kind": "OPERATOR_OVERRIDE", "reason": "x"},
                {"identity_key": "a", "kind": "OPERATOR_OVERRIDE", "reason": "y"}]))

    def test_no_document_means_no_overrides(self):
        assert PAL.load_material_changes("") == {}


class TestRoutingAndAcquisitionShareOneRegistry:
    """The lane the retry policy reasons about must be the lane the run can use.

    Routing through the COMMITTED table while acquiring through a narrower one
    let the retry policy read the wide ladder, see the primary lane was already
    paid for, and start the row on a fallback the narrower table forbids. In
    PILOT-015 that silently routed five Marriott retries to Web Unlocker -- the
    one lane the order excluded -- and only the dry run caught it.
    """

    def _narrow(self, tmp_path):
        doc = json.loads(json.dumps(REGISTRY.load()))
        doc["properties"] = dict(doc.get("properties") or {})
        doc["properties"]["walled"] = {
            "provider": "brightdata_browser",
            "fallback_providers": [],
            "forbidden_providers": ["brightdata_web_unlocker"],
            "reader": "generic",
            "max_attempts_per_provider": 1,
            "why": "one attempt, no escalation",
            "measured_by": "PTF-CINCINNATI-HILTON-CLOSE-AND-MARRIOTT-RETRY-PROBE-015",
        }
        path = tmp_path / "registry.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return REGISTRY.load(path)

    def test_the_wide_ladder_offers_the_forbidden_lane_as_an_alternate(self):
        """The bug's precondition, stated so the fix cannot be misread."""
        entry = {"identity_key": "walled",
                 "ladder": list(REGISTRY.resolve(
                     brand="MARRIOTT",
                     url="https://www.marriott.com/en-us/hotels/x/overview/",
                     identity_key="walled").ladder)}
        assert "brightdata_web_unlocker" in RP.approved_ladder(entry)

    def test_routing_through_the_narrow_table_offers_no_alternate(self, tmp_path):
        narrow = self._narrow(tmp_path)
        entry = {"identity_key": "walled",
                 "ladder": list(REGISTRY.resolve(
                     brand="MARRIOTT",
                     url="https://www.marriott.com/en-us/hotels/x/overview/",
                     identity_key="walled", registry=narrow).ladder)}
        assert RP.approved_ladder(entry) == ("brightdata_browser",)

    def test_route_census_honours_the_registry_it_is_given(self, tmp_path):
        rows = [{"identity_key": "walled", "canonical_name": "Walled",
                 "brand": "MARRIOTT", "corridor": "c",
                 "official_url": "https://www.marriott.com/en-us/hotels/x/overview/"}]
        wide, _ = MR.route_census(rows)
        narrow, _ = MR.route_census(rows, self._narrow(tmp_path))
        assert "brightdata_web_unlocker" in (wide[0].get("fallback_providers") or [])
        assert (narrow[0].get("fallback_providers") or []) == []
