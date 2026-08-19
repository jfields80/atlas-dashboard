"""PTF-IHG-FIRECRAWL-DECISION-009 -- the IHG decision, and the applied route.

IHG is the third brand onto Firecrawl and the first where the provider was
never the binding constraint. Its incumbent lane fetched 4/5 at 62% recall --
the weakest in the table -- because IHG states no ``petsAllowed`` in JSON-LD
and the reader has to work from prose. Firecrawl fixed the fetching. It did not
fix the reading, and these tests exist mostly to stop that distinction being
lost.

The one that matters most is the tiered fee. Staybridge Milwaukee Airport South
states 50 USD for stays of 1 to 6 nights and 150 USD for stays over 7. The
extraction carries 5000. A record like that is publication-grade, internally
consistent, and would underprice a week by 100 USD -- so the audit that catches
it is asserted here, on the live artifact, not merely written.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

from scripts.pettripfinder.acquisition import failures as F
from scripts.pettripfinder.acquisition import firecrawl_capture as FC
from scripts.pettripfinder.acquisition import ihg_firecrawl_decision_009 as IHG
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.acquisition import router as ROUTER
from scripts.pettripfinder.acquisition import wyndham_firecrawl_decision_008 as WY
from scripts.pettripfinder.brightdata import browser_capture as BC
from scripts.pettripfinder.brightdata import outcomes as O

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
DECISION = REPORTS / "ptf_ihg_firecrawl_decision_009.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")

IHG_URL = "https://www.ihg.com/holidayinn/hotels/us/en/milwaukee/mkehi/hoteldetail"


# --------------------------------------------------------------------------- #
# 1. IHG resolves to Firecrawl first
# --------------------------------------------------------------------------- #

class TestTheAppliedIhgRoute:
    def _route(self):
        return REGISTRY.resolve(brand="IHG", url=IHG_URL)

    def test_the_primary_is_firecrawl(self):
        assert self._route().provider == PROVIDERS.FIRECRAWL

    def test_the_fallback_is_the_web_unlocker(self):
        assert self._route().ladder == (PROVIDERS.FIRECRAWL,
                                        PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)

    def test_the_attempt_budget_is_three(self):
        assert self._route().max_attempts_per_provider == 3

    def test_the_reader_survived_the_change_of_provider(self):
        assert self._route().reader == "ihg"

    def test_it_cites_its_own_decision_test(self):
        route = self._route()
        assert "PTF-IHG-FIRECRAWL-DECISION-009" in route.measured_by
        assert route.why.strip()

    def test_the_route_records_that_the_reader_is_the_real_constraint(self):
        """Firecrawl fixed the fetching on this lane and did not fix the
        reading. A route row that claimed otherwise would set up the next
        person to blame the wrong layer."""
        row = REGISTRY.load()["brands"]["IHG"]
        assert "READER" in row["known_reader_limitation"]
        assert "provider-independent" in row["known_reader_limitation"]
        assert "HELD from publication" in row["known_reader_limitation"]

    def test_the_previous_lane_is_described_accurately(self):
        """Unlike Choice and Wyndham, this demotion replaced a lane that was
        underperforming. The record should say so rather than reuse the
        'it worked, we demoted it on cost' wording."""
        prev = REGISTRY.load()["brands"]["IHG"]["previous"]
        assert prev["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
        assert "62% recall" in prev["note"]


# --------------------------------------------------------------------------- #
# 4. brightdata_browser cannot be invoked
# --------------------------------------------------------------------------- #

class TestTheBrowserApiCannotBeReached:
    def test_it_is_forbidden_and_absent_from_the_ladder(self):
        route = REGISTRY.resolve(brand="IHG", url=IHG_URL)
        assert PROVIDERS.BRIGHTDATA_BROWSER in route.forbidden_providers
        assert PROVIDERS.BRIGHTDATA_BROWSER not in route.ladder


# --------------------------------------------------------------------------- #
# 2 & 3. Escalation through the real router
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


def _route_ihg_with_stubbed_primary(outcome: str, tmp_path: Path):
    row = WY.subjects("IHG")[0]
    record, target = WY._record_for(row, "IHG")
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


class TestEscalationOnTheIhgLane:
    def test_a_technical_failure_reaches_the_web_unlocker(self, tmp_path):
        result, primary, fallback = _route_ihg_with_stubbed_primary(
            O.ACCESS_DENIED, tmp_path)
        assert list(result.providers_tried) == [
            PROVIDERS.FIRECRAWL, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER]
        assert primary.calls == 3
        assert fallback.calls > 0
        assert result.cost.fallback_invoked is True

    @pytest.mark.parametrize("outcome,expected", [
        (O.IDENTITY_MISMATCH, F.IDENTITY_MISMATCH),
        (O.POLICY_NOT_FOUND, F.POLICY_NOT_FOUND),
    ])
    def test_a_terminal_failure_does_not_fall_through(self, outcome, expected,
                                                      tmp_path):
        result, _p, fallback = _route_ihg_with_stubbed_primary(outcome, tmp_path)
        assert list(result.providers_tried) == [PROVIDERS.FIRECRAWL]
        assert fallback.calls == 0
        assert result.failure == expected
        assert result.cost.fallback_invoked is False

    def test_the_browser_api_is_never_called(self, tmp_path):
        result, _p, _f = _route_ihg_with_stubbed_primary(O.ACCESS_DENIED,
                                                         tmp_path)
        assert not [a for a in result.attempts
                    if a.provider == PROVIDERS.BRIGHTDATA_BROWSER]


# --------------------------------------------------------------------------- #
# 5, 6, 7, 8. Nothing else changed
# --------------------------------------------------------------------------- #

class TestNoCrossBrandChange:
    def test_choice_and_wyndham_are_unchanged(self):
        choice = REGISTRY.resolve(
            brand="CHOICE",
            url="https://www.choicehotels.com/wisconsin/milwaukee/x/wi1")
        wyndham = REGISTRY.resolve(brand="WYNDHAM",
                                   url="https://www.wyndhamhotels.com/x")
        assert (choice.provider, choice.reader) == (PROVIDERS.FIRECRAWL,
                                                    "choice_static")
        assert (wyndham.provider, wyndham.reader) == (PROVIDERS.FIRECRAWL,
                                                      "wyndham")

    @pytest.mark.parametrize("brand,provider,reader", [
        ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER, "marriott"),
        ("HILTON", PROVIDERS.BRIGHTDATA_BROWSER, "hilton_competing"),
        ("MOTEL6", PROVIDERS.BRIGHTDATA_BROWSER, "generic"),
        ("RED_ROOF", PROVIDERS.BRIGHTDATA_BROWSER, "generic"),
        ("ESA", PROVIDERS.BRIGHTDATA_BROWSER, "generic"),
        ("DRURY", PROVIDERS.BRIGHTDATA_BROWSER, "generic"),
        ("SONESTA", PROVIDERS.BRIGHTDATA_BROWSER, "generic"),
    ])
    def test_untested_brands_stayed_where_they_were(self, brand, provider,
                                                    reader):
        route = REGISTRY.resolve(brand=brand, url="https://example.test/x")
        assert route.provider == provider
        assert route.reader == reader

    def test_the_default_is_untouched(self):
        route = REGISTRY.resolve(brand="NOBODY", url="https://example.test/x")
        assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
        assert route.reader == "generic"

    def test_no_domain_row_changed_and_none_was_added_for_ihg(self):
        domains = REGISTRY.load()["domains"]
        assert set(domains) == {"www.choicehotels.com"}
        assert domains["www.choicehotels.com"]["provider"] == PROVIDERS.FIRECRAWL

    def test_failure_classifications_are_untouched(self):
        """A route change must not quietly move the escalation boundary."""
        assert F.may_escalate(F.ACCESS_DENIED)
        assert not F.may_escalate(F.POLICY_NOT_FOUND)
        assert not F.may_escalate(F.POLICY_SURFACE_INCOMPLETE)
        assert not F.may_escalate(F.SOURCE_CONTRADICTORY)
        assert F.ESCALATING | F.TERMINAL == set(F.FAILURES)

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
# The decision test
# --------------------------------------------------------------------------- #

class TestTheDecisionTestMeasuredFirecrawlAlone:
    def test_it_reuses_the_wyndham_construction_rather_than_copying_it(self):
        """A third decision test written from scratch could quietly be a
        gentler test than the two before it."""
        assert IHG.WY.test_registry is WY.test_registry
        assert IHG.WY._observe is WY._observe

    def test_the_override_has_no_fallback_and_forbids_both_bright_data_lanes(self):
        row = WY.test_registry("IHG", "ihg")["brands"]["IHG"]
        assert row["provider"] == PROVIDERS.FIRECRAWL
        assert row["fallback_providers"] == []
        assert PROVIDERS.BRIGHTDATA_BROWSER in row["forbidden_providers"]
        assert PROVIDERS.BRIGHTDATA_WEB_UNLOCKER in row["forbidden_providers"]

    def test_it_used_the_real_ihg_reader(self):
        assert WY.test_registry("IHG", "ihg")["brands"]["IHG"]["reader"] == "ihg"

    def test_the_cohort_size_is_asserted_not_assumed(self):
        """A short cohort would make a rate out of fewer properties than the
        bar was set for."""
        assert IHG.EXPECTED_COHORT == 5
        assert len(WY.subjects("IHG")) == IHG.EXPECTED_COHORT


class TestTheTieredFeeAudit:
    def test_a_tiered_source_with_a_published_amount_is_flagged(self):
        out = IHG.tiered_fee_audit([{
            "identity_key": "x",
            "policy_surface_result": {"excerpt":
                "50 USD nonrefundable fee for stays 1 to 6 nights, 150 USD "
                "for stays over 7 nights."},
            "extraction": {"pet_fee": 5000}}])
        assert out["verdict"] == "TIERED_FEE_FLATTENED"
        assert out["fee_flattened_to_one_tier"][0]["published_amount_minor"] == 5000

    def test_a_tiered_source_with_the_fee_withheld_is_not_a_finding(self):
        """That is the schema working. Counting it as a defect would push
        toward publishing the number instead."""
        out = IHG.tiered_fee_audit([{
            "identity_key": "x",
            "policy_surface_result": {"excerpt":
                "non refundable fee of 50.00 for a 1 to 2 night stay. For 3 to "
                "5 nights the fee is 100.00"},
            "extraction": {"pets_allowed": True}}])
        assert out["verdict"] == "NO_TIERED_FEE_PUBLISHED"
        assert out["fee_correctly_withheld"]

    def test_a_flat_fee_is_not_flagged(self):
        out = IHG.tiered_fee_audit([{
            "identity_key": "x",
            "policy_surface_result": {"excerpt": "Pet fee 30 USD per night."},
            "extraction": {"pet_fee": 3000, "fee_basis": "per_night"}}])
        assert out["properties_with_tiered_fee_language"] == 0

    def test_it_is_recorded_as_provider_independent(self):
        out = IHG.tiered_fee_audit([])
        assert "READER behaviour" in out["provider_independent"]


class TestTheCommittedDecision:
    def _doc(self):
        if not DECISION.is_file():
            pytest.skip("decision test not run in this worktree")
        return json.loads(DECISION.read_text(encoding="utf-8-sig"))

    def test_the_decision_follows_mechanically_from_the_bar(self):
        doc = self._doc()
        rate = doc["totals"]["publication_grade_rate"]
        systemic = doc["defect_audit"]["systemic_defects"]
        if doc["decision"] == "APPROVE":
            assert rate >= IHG.APPROVE_MIN_PUBLICATION_GRADE_RATE
            assert not systemic
        elif doc["decision"] == "APPROVE_WITH_LIMITATION":
            assert rate >= IHG.LIMITATION_MIN_PUBLICATION_GRADE_RATE
        else:
            assert (rate < IHG.LIMITATION_MIN_PUBLICATION_GRADE_RATE
                    or systemic)

    def test_the_bar_required_more_than_a_pass_rate(self):
        t = self._doc()["thresholds_fixed_before_the_run"]
        assert t["approve_min_publication_grade_rate"] == 0.80
        assert "no systemic" in t["approve_also_requires"]
        assert t["cohort"] == 5

    def test_no_bright_data_provider_appears_in_any_attempt(self):
        for prop in self._doc()["properties"]:
            for provider in prop["providers_tried"]:
                assert not provider.startswith("brightdata"), prop["identity_key"]
        assert self._doc()["cost"]["bright_data_attempts"] == 0

    def test_the_defect_audit_ran_every_check_the_phase_named(self):
        audit = self._doc()["defect_audit"]
        for key in ("properties_with_brand_generic_text",
                    "properties_landing_off_the_property_page",
                    "properties_with_incomplete_fact_pairs",
                    "properties_sharing_identical_policy_text",
                    "distinct_extractions", "systemic_defects"):
            assert key in audit, key

    def test_no_capture_landed_off_the_property_page(self):
        """The IHG hazard that would matter most: a global chain policy page
        published as a hotel's own."""
        assert self._doc()["defect_audit"][
            "properties_landing_off_the_property_page"] == 0

    def test_the_tiered_fee_finding_is_carried_not_buried(self):
        """One of these five would underprice a week by 100 USD. An APPROVE
        that did not surface it would be the dangerous kind of pass."""
        audit = self._doc()["tiered_fee_audit"]
        assert audit["verdict"] == "TIERED_FEE_FLATTENED"
        assert audit["fee_flattened_to_one_tier"]
        assert "HELD from publication" in audit["consequence"]

    def test_the_decision_test_changed_nothing(self):
        doc = self._doc()
        assert doc["routes_changed"] is False
        assert doc["authority_written"] is False
        assert doc["policies_published"] is False
