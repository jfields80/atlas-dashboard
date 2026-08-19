"""PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006 -- the applied Choice route.

This is the first work order in the series that CHANGES production routing
rather than proposing it, so the tests are shaped around what could go wrong
when a route moves:

  * the change spreads. Firecrawl earned one brand on one measurement, and
    Marriott, Hilton, IHG, Wyndham and the default must be exactly where they
    were. Asserted individually, not as "nothing else changed".
  * a hard-won exclusion gets swept away with the row it lives on. The Browser
    API stays forbidden on Choice; that rule cost fourteen refusals in fifteen
    attempts and this measurement did not revisit it.
  * escalation semantics loosen. A second provider may retry a CHANNEL failure
    and must never re-interpret a SOURCE answer. Both directions are asserted
    through the real router with stub providers, not by reading the rule back.

The escalation tests use stub providers deliberately: the question "does the
ladder move" is a property of the routing rule, not of any page, and buying the
answer with live fetches would make it slower and less certain, not more.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

from scripts.pettripfinder.acquisition import envelope as ENV
from scripts.pettripfinder.acquisition import failures as F
from scripts.pettripfinder.acquisition import firecrawl_capture as FC
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.acquisition import router as ROUTER
from scripts.pettripfinder.acquisition import choice_route_proof_006 as PROOF
from scripts.pettripfinder.acquisition import firecrawl_hard_lanes_003 as HARD
from scripts.pettripfinder.brightdata import browser_capture as BC
from scripts.pettripfinder.brightdata import corpus as CORPUS
from scripts.pettripfinder.brightdata import outcomes as O

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
PROOF_REPORT = REPORTS / "ptf_choice_route_proof_006.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")

CHOICE_URL = ("https://www.choicehotels.com/wisconsin/milwaukee/"
              "econo-lodge-hotels/wi423")


# --------------------------------------------------------------------------- #
# The applied route
# --------------------------------------------------------------------------- #

class TestTheChoiceRouteIsApplied:
    def _route(self):
        return REGISTRY.resolve(brand="CHOICE", url=CHOICE_URL)

    def test_the_primary_is_firecrawl(self):
        assert self._route().provider == PROVIDERS.FIRECRAWL

    def test_the_fallback_is_the_web_unlocker(self):
        route = self._route()
        assert PROVIDERS.BRIGHTDATA_WEB_UNLOCKER in route.fallback_providers
        assert route.ladder == (PROVIDERS.FIRECRAWL,
                                PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)

    def test_the_attempt_budget_is_three(self):
        """Measured, not chosen: Sleep Inn succeeded on attempt 3."""
        assert self._route().max_attempts_per_provider == 3

    def test_the_browser_api_is_still_forbidden(self):
        """Fourteen refusals in fifteen attempts bought that rule, and this
        measurement did not revisit it. A route change is not an occasion to
        quietly drop an exclusion that travels on the same row."""
        route = self._route()
        assert PROVIDERS.BRIGHTDATA_BROWSER in route.forbidden_providers
        assert PROVIDERS.BRIGHTDATA_BROWSER not in route.ladder

    def test_the_reader_did_not_change(self):
        assert self._route().reader == "choice_static"

    def test_a_choice_property_with_an_unknown_brand_takes_the_same_lane(self):
        route = REGISTRY.resolve(brand="SOMETHING_ELSE", url=CHOICE_URL)
        assert route.provider == PROVIDERS.FIRECRAWL
        assert PROVIDERS.BRIGHTDATA_BROWSER in route.forbidden_providers

    def test_the_route_cites_the_measurements_that_justify_it(self):
        route = self._route()
        assert "PTF-FIRECRAWL-CHOICE-VALIDATION-004" in route.measured_by
        assert "PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005" in route.measured_by
        assert route.why.strip()

    def test_no_credential_is_stored_in_the_route_table(self):
        text = ROUTES_PATH.read_text(encoding="utf-8").lower()
        for token in ("fc-", "brd-customer", "api_key", "apikey", "password",
                      "authorization", "token"):
            assert token not in text, token


class TestNoOtherRouteMoved:
    @pytest.mark.parametrize("brand,provider,reader", [
        ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER, "marriott"),
        ("HILTON", PROVIDERS.BRIGHTDATA_BROWSER, "hilton_competing"),
    ])
    def test_the_hard_lanes_are_untouched(self, brand, provider, reader):
        """Firecrawl measured 1/4 on Marriott and 0/3 on Hilton. Earning one
        brand is not evidence about any other.

        WYNDHAM was in this list when 006 shipped and is not any more: it got
        its OWN decision test in PTF-WYNDHAM-FIRECRAWL-DECISION-008 and passed
        it 7/7. That is the rule working, not an exception to it -- a brand
        moves when it is measured, and only then."""
        route = REGISTRY.resolve(brand=brand, url="https://example.test/x")
        assert route.provider == provider
        assert route.reader == reader

    def test_the_default_is_untouched(self):
        route = REGISTRY.resolve(brand="NOBODY", url="https://example.test/x")
        assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
        assert route.reader == "generic"

    def test_firecrawl_reaches_only_brands_that_earned_it(self):
        """Every brand on this lane must name the decision test that put it
        there, and the default must never be Firecrawl -- a default carries
        brands nobody measured."""
        registry = REGISTRY.load()
        brands = {b: row for b, row in registry["brands"].items()
                  if row.get("provider") == PROVIDERS.FIRECRAWL}
        assert set(brands) == {"CHOICE", "WYNDHAM", "IHG"}
        assert "VALIDATION-004" in brands["CHOICE"]["measured_by"]
        assert "WYNDHAM-FIRECRAWL-DECISION-008" in brands["WYNDHAM"]["measured_by"]
        assert "IHG-FIRECRAWL-DECISION-009" in brands["IHG"]["measured_by"]
        domains = [d for d, row in registry["domains"].items()
                   if row.get("provider") == PROVIDERS.FIRECRAWL]
        assert domains == ["www.choicehotels.com"]
        assert registry["default"]["provider"] != PROVIDERS.FIRECRAWL


# --------------------------------------------------------------------------- #
# The provider
# --------------------------------------------------------------------------- #

class TestFirecrawlIsRegisteredHonestly:
    def test_it_is_implemented_and_no_longer_a_future_provider(self):
        assert PROVIDERS.FIRECRAWL in PROVIDERS.implemented()
        assert "firecrawl" not in PROVIDERS.KNOWN_FUTURE_PROVIDERS

    def test_spider_stays_a_future_provider_because_it_failed(self):
        """Being benchmarked is what earns a route. It is not the same as
        passing one: Spider reached 7 of 25."""
        assert "spider" in PROVIDERS.KNOWN_FUTURE_PROVIDERS
        assert "spider" not in PROVIDERS.all_ids()

    def test_its_capabilities_are_the_measured_ones_only(self):
        provider = PROVIDERS.get(PROVIDERS.FIRECRAWL)
        assert PROVIDERS.RUNS_JAVASCRIPT in provider.capabilities
        assert PROVIDERS.GEO_PINNABLE in provider.capabilities
        # The routed lane runs a plain scrape. The deterministic interaction
        # pass belongs to the benchmarks and is not claimed here.
        assert PROVIDERS.CAN_INTERACT not in provider.capabilities
        assert PROVIDERS.TAKES_SCREENSHOTS not in provider.capabilities

    def test_it_uses_the_profile_the_decision_was_measured_with(self):
        """One definition, not a copy: a second profile could drift away from
        the lane the decision was actually made about."""
        provider = PROVIDERS.get(PROVIDERS.FIRECRAWL)
        assert provider.capture_kwargs["profile"] is FC.ROUTED_PROFILE
        assert HARD.SCRAPE_PROFILE is FC.ROUTED_PROFILE
        assert FC.ROUTED_PROFILE["formats"] == ["rawHtml"]
        assert FC.ROUTED_PROFILE["waitFor"] >= 6000
        assert FC.ROUTED_PROFILE["location"] == {"country": "US"}

    def test_its_credential_is_environment_only(self):
        """Nothing about the key may live in the route table or the adapter."""
        assert FC.KEY_ENV == "FIRECRAWL_API_KEY"
        source = Path(FC.__file__).read_text(encoding="utf-8")
        assert "fc-" not in source
        assert "os.environ.get(KEY_ENV)" in source


class TestCostCurrenciesAreNotCombined:
    def test_firecrawl_bills_credits_and_asserts_no_dollar_figure(self):
        cost = PROVIDERS.get(PROVIDERS.FIRECRAWL).cost_metadata()
        assert cost.usd_minor_per_property is None
        assert cost.credits_per_property is not None
        assert cost.currency == "plan_credits"

    def test_bright_data_bills_dollars_and_asserts_no_credits(self):
        for pid in (PROVIDERS.BRIGHTDATA_BROWSER, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER):
            cost = PROVIDERS.get(pid).cost_metadata()
            assert cost.usd_minor_per_property is not None
            assert cost.credits_per_property is None
            assert cost.currency == "usd_minor"

    def test_the_cost_record_keeps_them_in_separate_fields(self):
        cost = ENV.AcquisitionCost(reported_credits=3.0,
                                   estimated_usd_minor=42.0).to_dict()
        assert cost["reported_credits"] == 3.0
        assert cost["estimated_usd_minor"] == 42.0
        assert "currencies_are_not_combined" in cost
        assert not any(k for k in cost
                       if "total" in k and "cost" in k)

    def test_the_record_can_carry_per_provider_latency_and_a_fallback_flag(self):
        """A ladder that fell through spent time in two lanes, and one total
        hides which one was slow."""
        cost = ENV.AcquisitionCost(
            seconds_by_provider={"firecrawl": 1.0, "brightdata_web_unlocker": 88.0},
            fallback_invoked=True).to_dict()
        assert cost["seconds_by_provider"]["brightdata_web_unlocker"] == 88.0
        assert cost["fallback_invoked"] is True


# --------------------------------------------------------------------------- #
# Escalation, through the real router, with stub lanes
# --------------------------------------------------------------------------- #

class _StubModule:
    """A capture module that returns one outcome and makes no request."""

    def __init__(self, outcome: str, payload=None) -> None:
        self.outcome = outcome
        self.payload = payload
        self.calls = 0

    async def capture_property(self, target, *, run_dir: Path, brand: str,
                               max_attempts: int = 3, profile=None
                               ) -> Tuple[List, Optional[Dict]]:
        records = []
        for attempt in range(1, max_attempts + 1):
            self.calls += 1
            records.append(BC.AttemptRecord(
                attempt=attempt, outcome=self.outcome, started_at="",
                ended_at="", elapsed_seconds=0.0,
                requested_url=target.requested_url,
                final_url=target.requested_url, title="", body_chars=0,
                detail="stubbed by the test"))
            if self.outcome != O.ACCESS_DENIED:
                break
        return records, self.payload


def _run_with_stubbed_primary(outcome: str, tmp_path: Path):
    """Route one Choice property with the primary lane stubbed to ``outcome``."""
    record, target, _entry = PROOF._record_for(PROOF.CONTROL_KEY)
    primary = PROVIDERS.get(PROVIDERS.FIRECRAWL)
    fallback = PROVIDERS.get(PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    primary_stub = _StubModule(outcome)
    fallback_stub = _StubModule(O.ACCESS_DENIED)

    original_primary, original_fallback = primary.module, fallback.module
    original_health_p, original_health_f = primary.health, fallback.health
    healthy = lambda: PROVIDERS.ProviderHealth(True, "stubbed")   # noqa: E731
    object.__setattr__(primary, "module", primary_stub)
    object.__setattr__(fallback, "module", fallback_stub)
    object.__setattr__(primary, "health", healthy)
    object.__setattr__(fallback, "health", healthy)
    try:
        result = asyncio.run(ROUTER.route_property(
            record, target, run_dir=tmp_path, run_id="test"))
    finally:
        object.__setattr__(primary, "module", original_primary)
        object.__setattr__(fallback, "module", original_fallback)
        object.__setattr__(primary, "health", original_health_p)
        object.__setattr__(fallback, "health", original_health_f)
    return result, primary_stub, fallback_stub


class TestATechnicalFailureFallsThrough:
    def test_access_denied_reaches_the_web_unlocker(self, tmp_path):
        result, primary, fallback = _run_with_stubbed_primary(
            O.ACCESS_DENIED, tmp_path)
        assert list(result.providers_tried) == [
            PROVIDERS.FIRECRAWL, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER]
        assert fallback.calls > 0
        assert result.cost.fallback_invoked is True

    def test_the_primary_is_given_its_full_measured_budget_first(self, tmp_path):
        """Three attempts, because SCRAPE_ALL_ENGINES_FAILED is intermittent
        on this origin and two was demonstrably too few."""
        _result, primary, _fallback = _run_with_stubbed_primary(
            O.ACCESS_DENIED, tmp_path)
        assert primary.calls == 3

    def test_the_browser_api_is_never_called_on_choice(self, tmp_path):
        result, _p, _f = _run_with_stubbed_primary(O.ACCESS_DENIED, tmp_path)
        assert PROVIDERS.BRIGHTDATA_BROWSER not in result.providers_tried
        assert not [a for a in result.attempts
                    if a.provider == PROVIDERS.BRIGHTDATA_BROWSER]


class TestASourceLevelAnswerNeverFallsThrough:
    @pytest.mark.parametrize("outcome,expected_failure", [
        (O.IDENTITY_MISMATCH, F.IDENTITY_MISMATCH),
        (O.POLICY_NOT_FOUND, F.POLICY_NOT_FOUND),
    ])
    def test_the_ladder_stops_at_the_first_provider(self, outcome,
                                                    expected_failure, tmp_path):
        """A second provider would receive the same answer, at full price."""
        result, _p, fallback = _run_with_stubbed_primary(outcome, tmp_path)
        assert list(result.providers_tried) == [PROVIDERS.FIRECRAWL]
        assert fallback.calls == 0
        assert result.failure == expected_failure
        assert "terminal" in result.escalation_stopped_because
        assert result.cost.fallback_invoked is False

    @pytest.mark.parametrize("failure", [
        F.SOURCE_CONTRADICTORY, F.SOURCE_AMBIGUOUS, F.POLICY_NOT_FOUND,
        F.IDENTITY_MISMATCH,
    ])
    def test_these_failures_are_terminal_by_rule(self, failure):
        assert not F.may_escalate(failure)
        assert failure in F.TERMINAL

    def test_a_contradictory_source_is_a_source_state_not_a_fetch_state(self):
        """PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005 produced a real one. It must
        never become a reason to spend a second provider."""
        assert F.from_withholding("SOURCE_CONTRADICTORY") == F.SOURCE_CONTRADICTORY
        assert not F.may_escalate(F.SOURCE_CONTRADICTORY)
        assert ROUTER._final_state(document=None,
                                   failure=F.SOURCE_CONTRADICTORY) == \
            ENV.SOURCE_CONTRADICTORY


# --------------------------------------------------------------------------- #
# The live proof
# --------------------------------------------------------------------------- #

class TestTheLiveProof:
    def _doc(self):
        if not PROOF_REPORT.is_file():
            pytest.skip("route proof not run in this worktree")
        return json.loads(PROOF_REPORT.read_text(encoding="utf-8-sig"))

    def test_it_passed(self):
        assert self._doc()["status"] == "PASS"

    def test_normal_traffic_stays_on_firecrawl_and_never_touches_the_fallback(self):
        control = self._doc()["normal_control"]
        assert control["acquired_by"] == "firecrawl"
        assert control["providers_tried"] == ["firecrawl"]
        assert control["fallback_invoked"] is False
        assert control["publication_grade"] is True
        assert len(control["outcomes_by_provider"]["firecrawl"]) <= 3

    def test_the_fallback_fired_end_to_end_for_the_first_time(self):
        """Every earlier work order could only say this path was untested."""
        fb = self._doc()["forced_fallback"]
        assert fb["providers_tried"] == ["firecrawl", "brightdata_web_unlocker"]
        assert fb["fallback_invoked"] is True
        assert fb["acquired_by"] == "brightdata_web_unlocker"

    def test_the_fallback_leg_met_the_same_standard_as_the_primary(self):
        """A fallback that acquires at a lower standard is not a fallback."""
        fb = self._doc()["forced_fallback"]
        assert fb["publication_grade"] is True
        assert fb["identity_confirmed"] is True
        assert fb["reader"] == "choice_static"
        assert fb["state"] == "ACQUIRED_PUBLICATION_GRADE"
        assert fb["extraction"]

    def test_the_forced_failure_was_a_channel_failure_not_a_source_answer(self):
        fb = self._doc()["forced_fallback"]
        assert fb["outcomes_by_provider"]["firecrawl"] == ["ACCESS_DENIED"] * 3
        assert fb["failure_class"] == "TECHNICAL"

    def test_no_browser_api_call_was_made_in_either_proof(self):
        doc = self._doc()
        for name in ("normal_control", "forced_fallback"):
            assert doc[name]["brightdata_browser_calls"] == 0

    def test_credits_and_dollars_are_reported_separately(self):
        doc = self._doc()
        control_cost = doc["normal_control"]["cost"]
        assert control_cost["reported_credits"] == 1.0
        fb_cost = doc["forced_fallback"]["cost"]
        # No successful Firecrawl attempt on the fallback leg, so no credit.
        assert fb_cost["reported_credits"] == 0.0
        assert fb_cost["seconds_by_provider"]["brightdata_web_unlocker"] > 0

    def test_the_proof_wrote_no_authority_and_published_nothing(self):
        doc = self._doc()
        assert doc["authority_written"] is False
        assert doc["policies_published"] is False

    def test_the_other_brands_were_checked_during_the_proof_too(self):
        others = self._doc()["other_brand_primaries"]
        assert set(others.values()) == {"brightdata_browser"}

    def test_a_successful_fallback_still_reports_why_it_fired(self):
        """The router keeps the primary's failure on a result it ultimately
        acquired. That is deliberate -- it is the only record of WHY the
        fallback ran -- so ``state`` is the authoritative field and consumers
        must not read success off an empty ``failure``."""
        fb = self._doc()["forced_fallback"]
        assert fb["state"] == "ACQUIRED_PUBLICATION_GRADE"
        assert fb["failure"] == "ACCESS_DENIED"


class TestTheApplicationRecord:
    """The proposal and the application are two artifacts on purpose: one says
    what should happen, the other says what did. Collapsing them loses the
    ability to check the second against the first."""

    APPLIED = REPORTS / "ptf_choice_route_applied_006.json"

    def _doc(self):
        if not self.APPLIED.is_file():
            pytest.skip("no application record in this worktree")
        return json.loads(self.APPLIED.read_text(encoding="utf-8-sig"))

    def test_it_is_marked_applied_and_names_its_authorization(self):
        doc = self._doc()
        assert doc["status"] == "APPLIED"
        assert doc["authorized_by"]
        assert doc["applies"] == "ptf_choice_route_change_005.json"

    def test_every_freeze_is_recorded_as_unchanged(self):
        freezes = self._doc()["freezes"]
        for key in ("POLICY_AUTHORITY_CHANGED", "EXCLUSIONS_CHANGED",
                    "SEEDS_CHANGED", "APPROVALS_CHANGED", "PARTITION_CHANGED",
                    "POLICIES_PUBLISHED", "DEPLOYED"):
            assert freezes[key] == "NO", key

    def test_nothing_cross_brand_shipped_in_this_commit(self):
        """An earlier draft moved POLICY_SURFACE_INCOMPLETE into ESCALATING,
        which would have split the POLICY family and changed EVERY brand's
        ladder. It was restored before commit on founder instruction, and the
        record must show the scope is Choice-only rather than quietly carrying
        a cross-brand change under a Choice heading."""
        doc = self._doc()
        assert "failures.py" not in doc["what_changed"]
        assert "Choice lane" in doc["scope_note"]
        note = doc["failure_semantics_preserved"]["POLICY_SURFACE_INCOMPLETE_note"]
        assert "RESTORED" in note
        assert not F.may_escalate(F.POLICY_SURFACE_INCOMPLETE)

    def test_it_does_not_overclaim_the_control_latency(self):
        """1.9s is faster than the profile's own 6s wait. Reporting it as a
        cold-fetch time would flatter the lane."""
        control = self._doc()["proofs"]["normal_control"]
        assert "cache" in control["note_on_speed"]

    def test_it_carries_the_reader_backlog_item_forward_untouched(self):
        backlog = self._doc()["reader_backlog_unchanged"]
        assert backlog
        assert backlog[0]["touched_by_this_work_order"] is False

    def test_it_names_the_newly_reachable_router_behaviour(self):
        known = self._doc()["known_behaviour_worth_naming"]
        assert "failure" in known["item"]
        assert "state is the authoritative field" in known["consequence"]

    def test_the_semantics_it_claims_match_the_live_rule(self):
        """The record must not describe escalation semantics the code does not
        actually implement."""
        semantics = self._doc()["failure_semantics_preserved"]
        for name in semantics["never_falls_through"]:
            assert not F.may_escalate(name), name
        for entry in semantics["falls_through"]:
            name = entry.split(" (")[0]
            assert F.may_escalate(name), name
