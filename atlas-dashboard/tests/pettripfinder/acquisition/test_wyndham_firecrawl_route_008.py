"""PTF-WYNDHAM-FIRECRAWL-DECISION-008 -- the decision, and the applied route.

Wyndham is the second brand to move onto Firecrawl, and the second move is
where a pattern can turn into a habit. So these tests hold the thing that made
the first move defensible: a brand moves when it is measured, on its own
evidence, and only onto the lane that evidence covers.

The decision test itself is held to two standards beyond its result:

  * it must have measured FIRECRAWL, not a ladder. Its registry override
    carries no fallback and forbids both Bright Data lanes, so a success
    cannot have been the incumbent's.
  * it must not have measured a constant. Three La Quinta properties returned
    byte-identical policy text, which is the shape of the brand-boilerplate
    defect that put two wrong Columbus exclusions into this corpus. The report
    has to show the corpus answers varying, or the result means nothing.

One thing this change does that the CHOICE change did not: it demotes a lane
that WORKED. The Browser API was 5/5 at 100% recall on Wyndham. That is a cost
decision, it is recorded as one, and the fallback is what bounds it.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

from scripts.pettripfinder.acquisition import failures as F
from scripts.pettripfinder.acquisition import firecrawl_capture as FC
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.acquisition import router as ROUTER
from scripts.pettripfinder.acquisition import wyndham_firecrawl_decision_008 as WY
from scripts.pettripfinder.brightdata import browser_capture as BC
from scripts.pettripfinder.brightdata import outcomes as O

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
DECISION = REPORTS / "ptf_wyndham_firecrawl_decision_008.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")

WYNDHAM_URL = ("https://www.wyndhamhotels.com/super-8/milwaukee-wisconsin/"
               "super-8-milwaukee-airport/overview")


# --------------------------------------------------------------------------- #
# 1. WYNDHAM resolves to Firecrawl first
# --------------------------------------------------------------------------- #

class TestTheAppliedWyndhamRoute:
    def _route(self):
        return REGISTRY.resolve(brand="WYNDHAM", url=WYNDHAM_URL)

    def test_the_primary_is_firecrawl(self):
        assert self._route().provider == PROVIDERS.FIRECRAWL

    def test_the_fallback_is_the_web_unlocker(self):
        route = self._route()
        assert route.ladder == (PROVIDERS.FIRECRAWL,
                                PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)

    def test_the_attempt_budget_is_three(self):
        assert self._route().max_attempts_per_provider == 3

    def test_the_reader_survived_the_change_of_provider(self):
        """A provider change must not become a reader change; the wyndham
        reader is what PTF-ACQUISITION-BRAND-REPAIR-003 measured."""
        assert self._route().reader == "wyndham"

    def test_it_cites_its_own_decision_test(self):
        route = self._route()
        assert "PTF-WYNDHAM-FIRECRAWL-DECISION-008" in route.measured_by
        assert route.why.strip()

    def test_the_demotion_of_a_working_lane_is_recorded_as_such(self):
        """The Browser API was 5/5 at 100% recall here. Demoting a lane that
        worked is a cost decision and the record must say so rather than imply
        the old lane failed."""
        row = REGISTRY.load()["brands"]["WYNDHAM"]
        assert row["previous"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
        assert "not being retired for failing" in row["previous"]["note"]
        assert "reversible" in row["previous"]["note"]


# --------------------------------------------------------------------------- #
# 4. brightdata_browser cannot be invoked by the WYNDHAM route
# --------------------------------------------------------------------------- #

class TestTheBrowserApiCannotBeReached:
    def test_it_is_forbidden_and_absent_from_the_ladder(self):
        route = REGISTRY.resolve(brand="WYNDHAM", url=WYNDHAM_URL)
        assert PROVIDERS.BRIGHTDATA_BROWSER in route.forbidden_providers
        assert PROVIDERS.BRIGHTDATA_BROWSER not in route.ladder

    def test_a_forbidden_provider_is_removed_even_if_listed_as_a_fallback(self):
        """Belt and braces: the ladder property strips it, so no caller can
        escalate into it by constructing the route differently."""
        route = REGISTRY.Route(
            provider=PROVIDERS.FIRECRAWL,
            fallback_providers=(PROVIDERS.BRIGHTDATA_BROWSER,
                                PROVIDERS.BRIGHTDATA_WEB_UNLOCKER),
            reader="wyndham", max_attempts_per_provider=3,
            resolved_by="test", why="test", measured_by="test",
            forbidden_providers=(PROVIDERS.BRIGHTDATA_BROWSER,))
        assert PROVIDERS.BRIGHTDATA_BROWSER not in route.ladder
        assert route.ladder == (PROVIDERS.FIRECRAWL,
                                PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)


# --------------------------------------------------------------------------- #
# 2 & 3. Escalation, through the real router with stub lanes
# --------------------------------------------------------------------------- #

class _StubModule:
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
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
        return records, None


def _route_wyndham_with_stubbed_primary(outcome: str, tmp_path: Path):
    row = WY.subjects()[0]
    record, target = WY._record_for(row)
    primary = PROVIDERS.get(PROVIDERS.FIRECRAWL)
    fallback = PROVIDERS.get(PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    p_stub, f_stub = _StubModule(outcome), _StubModule(O.ACCESS_DENIED)
    healthy = lambda: PROVIDERS.ProviderHealth(True, "stubbed")   # noqa: E731

    saved = (primary.module, fallback.module, primary.health, fallback.health)
    object.__setattr__(primary, "module", p_stub)
    object.__setattr__(fallback, "module", f_stub)
    object.__setattr__(primary, "health", healthy)
    object.__setattr__(fallback, "health", healthy)
    try:
        result = asyncio.run(ROUTER.route_property(
            record, target, run_dir=tmp_path, run_id="test"))
    finally:
        object.__setattr__(primary, "module", saved[0])
        object.__setattr__(fallback, "module", saved[1])
        object.__setattr__(primary, "health", saved[2])
        object.__setattr__(fallback, "health", saved[3])
    return result, p_stub, f_stub


class TestEscalationOnTheWyndhamLane:
    def test_a_technical_failure_reaches_the_web_unlocker(self, tmp_path):
        result, primary, fallback = _route_wyndham_with_stubbed_primary(
            O.ACCESS_DENIED, tmp_path)
        assert list(result.providers_tried) == [
            PROVIDERS.FIRECRAWL, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER]
        assert primary.calls == 3, "the primary gets its full measured budget"
        assert fallback.calls > 0
        assert result.cost.fallback_invoked is True

    @pytest.mark.parametrize("outcome,expected", [
        (O.IDENTITY_MISMATCH, F.IDENTITY_MISMATCH),
        (O.POLICY_NOT_FOUND, F.POLICY_NOT_FOUND),
    ])
    def test_a_terminal_failure_does_not_fall_through(self, outcome, expected,
                                                      tmp_path):
        """A second provider would receive the same answer at full price."""
        result, _p, fallback = _route_wyndham_with_stubbed_primary(
            outcome, tmp_path)
        assert list(result.providers_tried) == [PROVIDERS.FIRECRAWL]
        assert fallback.calls == 0
        assert result.failure == expected
        assert result.cost.fallback_invoked is False

    def test_the_browser_api_is_never_called(self, tmp_path):
        result, _p, _f = _route_wyndham_with_stubbed_primary(
            O.ACCESS_DENIED, tmp_path)
        assert not [a for a in result.attempts
                    if a.provider == PROVIDERS.BRIGHTDATA_BROWSER]

    @pytest.mark.parametrize("failure", [
        F.SOURCE_CONTRADICTORY, F.SOURCE_AMBIGUOUS, F.POLICY_NOT_FOUND,
        F.IDENTITY_MISMATCH,
    ])
    def test_source_level_answers_are_terminal_by_rule(self, failure):
        assert not F.may_escalate(failure)


# --------------------------------------------------------------------------- #
# 5 & 6. Nothing else moved; the profile is still shared
# --------------------------------------------------------------------------- #

class TestNothingElseMoved:
    @pytest.mark.parametrize("brand,provider,reader", [
        ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER, "marriott"),
        ("HILTON", PROVIDERS.BRIGHTDATA_BROWSER, "hilton_competing"),
        ("IHG", PROVIDERS.BRIGHTDATA_BROWSER, "ihg"),
        ("MOTEL6", PROVIDERS.BRIGHTDATA_BROWSER, "generic"),
        ("RED_ROOF", PROVIDERS.BRIGHTDATA_BROWSER, "generic"),
    ])
    def test_unmeasured_brands_stayed_where_they_were(self, brand, provider,
                                                      reader):
        route = REGISTRY.resolve(brand=brand, url="https://example.test/x")
        assert route.provider == provider
        assert route.reader == reader

    def test_the_default_is_untouched(self):
        route = REGISTRY.resolve(brand="NOBODY", url="https://example.test/x")
        assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
        assert route.reader == "generic"

    def test_choice_is_untouched(self):
        route = REGISTRY.resolve(
            brand="CHOICE",
            url="https://www.choicehotels.com/wisconsin/milwaukee/x/wi1")
        assert route.provider == PROVIDERS.FIRECRAWL
        assert route.reader == "choice_static"

    def test_no_domain_row_was_added_for_wyndham(self):
        """Choice got a domain mirror because unknown-brand Choice properties
        exist in the queue. Nothing measured here justifies one for Wyndham."""
        assert "www.wyndhamhotels.com" not in REGISTRY.load()["domains"]

    def test_the_shared_routed_profile_is_still_canonical(self):
        provider = PROVIDERS.get(PROVIDERS.FIRECRAWL)
        assert provider.capture_kwargs["profile"] is FC.ROUTED_PROFILE
        assert FC.ROUTED_PROFILE["formats"] == ["rawHtml"]
        assert FC.ROUTED_PROFILE["location"] == {"country": "US"}

    def test_no_credential_reached_the_route_table(self):
        text = ROUTES_PATH.read_text(encoding="utf-8").lower()
        for token in ("fc-", "brd-customer", "api_key", "password", "token"):
            assert token not in text, token


# --------------------------------------------------------------------------- #
# The decision test itself
# --------------------------------------------------------------------------- #

class TestTheDecisionTestMeasuredFirecrawlAlone:
    def test_the_override_has_no_fallback_and_forbids_bright_data(self):
        row = WY.test_registry()["brands"]["WYNDHAM"]
        assert row["provider"] == PROVIDERS.FIRECRAWL
        assert row["fallback_providers"] == []
        assert PROVIDERS.BRIGHTDATA_BROWSER in row["forbidden_providers"]
        assert PROVIDERS.BRIGHTDATA_WEB_UNLOCKER in row["forbidden_providers"]

    def test_the_override_left_every_other_brand_alone(self):
        override = WY.test_registry()
        live = REGISTRY.load()
        for brand in live["brands"]:
            if brand == "WYNDHAM":
                continue
            assert override["brands"][brand] == live["brands"][brand], brand

    def test_it_used_the_real_reader_not_a_weakened_one(self):
        assert WY.test_registry()["brands"]["WYNDHAM"]["reader"] == "wyndham"

    def test_the_thresholds_were_fixed_before_the_run(self):
        """A bar that moves to fit the result is not a bar."""
        assert WY.APPROVE_MIN_PUBLICATION_GRADE_RATE > \
            WY.LIMITATION_MIN_PUBLICATION_GRADE_RATE
        assert 0 < WY.LIMITATION_MIN_PUBLICATION_GRADE_RATE < 1


class TestTheCommittedDecision:
    def _doc(self):
        if not DECISION.is_file():
            pytest.skip("decision test not run in this worktree")
        return json.loads(DECISION.read_text(encoding="utf-8-sig"))

    def test_the_decision_follows_mechanically_from_the_measurement(self):
        doc = self._doc()
        rate = doc["totals"]["publication_grade_rate"]
        if doc["decision"] == "APPROVE":
            assert rate >= WY.APPROVE_MIN_PUBLICATION_GRADE_RATE
        elif doc["decision"] == "APPROVE_WITH_LIMITATION":
            assert rate >= WY.LIMITATION_MIN_PUBLICATION_GRADE_RATE
        else:
            assert rate < WY.LIMITATION_MIN_PUBLICATION_GRADE_RATE

    def test_no_bright_data_provider_appears_in_any_attempt(self):
        for prop in self._doc()["properties"]:
            for provider in prop["providers_tried"]:
                assert not provider.startswith("brightdata"), prop["identity_key"]
        assert self._doc()["cost"]["bright_data_attempts"] == 0

    def test_every_property_carries_the_evidence_the_phase_required(self):
        for prop in self._doc()["properties"]:
            for key in ("identity_key", "property_name", "url_attempted",
                        "firecrawl_attempt_count", "acquisition_result",
                        "identity_result", "policy_surface_result",
                        "publication_grade_result", "failure_classification",
                        "eligible_for_escalation"):
                assert key in prop, key

    def test_attempts_never_exceeded_the_proposed_budget(self):
        for prop in self._doc()["properties"]:
            assert prop["firecrawl_attempt_count"] <= WY.PROPOSED_ATTEMPTS

    def test_identical_policy_text_was_investigated_not_assumed(self):
        """Three La Quintas returned the same policy. That is the shape of the
        brand-boilerplate defect that produced two wrong Columbus exclusions,
        so the report must show the corpus answers varying."""
        check = self._doc()["boilerplate_check"]
        assert check["verdict"] == "BRAND_STANDARD_NOT_BOILERPLATE"
        assert check["distinct_extractions"] > 1
        assert set(check["pets_allowed_values_observed"]) == {"true", "false"}

    def test_the_decision_test_changed_nothing(self):
        doc = self._doc()
        assert doc["routes_changed"] is False
        assert doc["authority_written"] is False
        assert doc["policies_published"] is False
