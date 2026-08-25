"""PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 -- no same-lane retry waste.

Louisville paid for eight properties a prior pass had already paid for and
failed to read; all eight failed again on the same lanes for $1.20 and no fact.
These tests pin the rule that keeps that from happening by default, and the
four doors that let a retry through on purpose.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.acquisition import market_paid_acquisition as PA
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.acquisition import retry_policy as RP
from scripts.pettripfinder.brightdata import outcomes as O


def routed(key, provider="brightdata_browser", fallbacks=("brightdata_web_unlocker",),
           reader="generic", url=None):
    return {"identity_key": key, "canonical_name": key.title(), "brand": "HILTON",
            "corridor": "c", "source_url": url or "https://x/%s" % key,
            "routing_state": MR.ROUTED, "provider": provider, "reader": reader,
            "fallback_providers": list(fallbacks),
            "ladder": [provider] + list(fallbacks)}


def prior(key, outcome, *, tried=("brightdata_browser", "brightdata_web_unlocker"),
          provider=None, reader="generic", url=None, failure=None):
    return {"identity_key": key, "outcome": outcome,
            "providers_tried": list(tried),
            "provider": provider or (tried[-1] if tried else ""),
            "reader": reader, "source_url": url or "https://x/%s" % key,
            "failure": failure or outcome}


class TestSuppression:
    @pytest.mark.parametrize("outcome", [O.ACCESS_DENIED, O.NAVIGATION_FAILED,
                                         O.UNHYDRATED, O.UNEXPECTED_PAGE,
                                         O.BLANK_PAGE, O.CAPTURE_FAILED])
    def test_a_failure_on_every_approved_lane_is_not_bought_again(self, outcome):
        verdict = RP.classify(routed("a"), prior("a", outcome))
        assert verdict["classification"] == RP.RETRY_REQUIRES_ALTERNATE_LANE
        assert verdict["suppressed_because"] == RP.WHY_EVERY_LANE_TRIED

    def test_a_suppressed_row_is_never_marked_settled(self):
        cohort, settled, suppressed = PA.plan_cohort(
            [routed("a")], {"results": [prior("a", O.ACCESS_DENIED)]})
        assert cohort == [] and settled == []
        assert [r["identity_key"] for r in suppressed] == ["a"]
        assert suppressed[0]["retry_classification"] == RP.RETRY_REQUIRES_ALTERNATE_LANE

    def test_the_three_lists_partition_the_routed_population(self):
        entries = [routed("valid"), routed("blocked"), routed("fresh"),
                   dict(routed("unrouted"), routing_state=MR.ROUTE_NEEDS_OFFICIAL_URL)]
        results = {"results": [prior("valid", O.VALID),
                               prior("blocked", O.ACCESS_DENIED)]}
        cohort, settled, suppressed = PA.plan_cohort(entries, results)
        keys = sorted(r["identity_key"] for r in cohort + settled + suppressed)
        assert keys == ["blocked", "fresh", "valid"]
        assert [r["identity_key"] for r in cohort] == ["fresh"]
        assert [r["identity_key"] for r in settled] == ["valid"]
        assert [r["identity_key"] for r in suppressed] == ["blocked"]

    def test_an_unrecorded_prior_lane_is_suppressed_not_assumed_different(self):
        row = {"identity_key": "a", "outcome": O.ACCESS_DENIED,
               "source_url": "https://x/a"}
        verdict = RP.classify(routed("a"), row)
        assert verdict["classification"] == RP.RETRY_REQUIRES_ALTERNATE_LANE
        assert verdict["suppressed_because"] == RP.WHY_PRIOR_LANE_UNRECORDED

    def test_the_free_pilots_document_level_lane_counts_as_recorded(self):
        # The direct_http pilot names its lane once, at document level.
        document = {"provider": "direct_http",
                    "results": [{"identity_key": "a", "outcome": O.ACCESS_DENIED,
                                 "source_url": "https://x/a"}]}
        verdict = RP.classify(routed("a"), document["results"][0],
                              prior_document=document)
        # direct_http was tried; the paid ladder is untried -> allowed.
        assert verdict["classification"] == RP.RETRY_ALLOWED_ALTERNATE_LANE
        assert verdict["lanes_tried"] == ["direct_http"]
        assert verdict["lane_override"]["provider"] == "brightdata_browser"

    def test_a_merged_view_names_no_single_lane_at_document_level(self):
        assert RP.lanes_tried({"identity_key": "a"},
                              {"provider": "firecrawl, brightdata_browser"}) == ()


class TestTheFourDoors:
    def test_an_untried_approved_lane_lets_the_retry_through_on_that_lane(self):
        verdict = RP.classify(routed("a"),
                              prior("a", O.ACCESS_DENIED, tried=("brightdata_browser",)))
        assert verdict["classification"] == RP.RETRY_ALLOWED_ALTERNATE_LANE
        assert verdict["alternate_lanes"] == ["brightdata_web_unlocker"]
        assert verdict["lane_override"] == {"provider": "brightdata_web_unlocker",
                                            "fallback_providers": []}

    def test_a_changed_source_url_lets_the_retry_through(self):
        verdict = RP.classify(routed("a", url="https://hilton.com/new"),
                              prior("a", O.UNEXPECTED_PAGE, url="https://old/a"))
        assert verdict["classification"] == RP.RETRY_ALLOWED_URL_CHANGED

    def test_a_tracking_parameter_is_not_a_changed_url(self):
        verdict = RP.classify(routed("a", url="https://x/a?cm_mmc=ref"),
                              prior("a", O.UNEXPECTED_PAGE, url="https://x/a"))
        assert verdict["classification"] == RP.RETRY_REQUIRES_ALTERNATE_LANE

    def test_a_reader_change_lets_a_reader_addressable_failure_through(self):
        verdict = RP.classify(
            routed("a", reader="hilton_competing"),
            prior("a", "IDENTITY_UNCERTAIN", reader="generic",
                  failure="IDENTITY_UNCERTAIN"))
        assert verdict["classification"] == RP.RETRY_ALLOWED_READER_CHANGED

    def test_a_reader_change_does_not_address_a_channel_refusal(self):
        # A new reader reads the same 403.
        verdict = RP.classify(routed("a", reader="hilton_competing"),
                              prior("a", O.ACCESS_DENIED, reader="generic"))
        assert verdict["classification"] == RP.RETRY_REQUIRES_ALTERNATE_LANE

    def test_an_operator_override_lets_the_retry_through_and_names_who(self, tmp_path):
        path = tmp_path / "overrides.json"
        path.write_text(json.dumps({"overrides": [
            {"identity_key": "a", "authorised_by": "jfields80",
             "why": "the vendor confirmed the block was lifted"}]}),
            encoding="utf-8")
        overrides = RP.load_overrides(path)
        verdict = RP.classify(routed("a"), prior("a", O.ACCESS_DENIED),
                              overrides=overrides)
        assert verdict["classification"] == RP.RETRY_ALLOWED_OPERATOR_OVERRIDE
        assert "jfields80" in verdict["why"]

    @pytest.mark.parametrize("row", [
        {"identity_key": "a", "why": "reason"},
        {"identity_key": "a", "authorised_by": "someone"},
        {"authorised_by": "someone", "why": "reason"},
    ])
    def test_an_override_without_an_author_or_a_reason_is_refused(self, tmp_path, row):
        path = tmp_path / "overrides.json"
        path.write_text(json.dumps({"overrides": [row]}), encoding="utf-8")
        with pytest.raises(RP.RetryPolicyError):
            RP.load_overrides(path)


class TestNeverAttemptedAndSettled:
    def test_a_property_no_pass_touched_is_a_first_attempt(self):
        verdict = RP.classify(routed("a"), None)
        assert verdict["classification"] == RP.FIRST_ATTEMPT

    @pytest.mark.parametrize("outcome", [O.VALID, O.POLICY_NOT_FOUND,
                                         O.IDENTITY_MISMATCH])
    def test_a_settled_row_is_answered_consistently_not_refused(self, outcome):
        verdict = RP.classify(routed("a"), prior("a", outcome))
        assert verdict["classification"] == "SETTLED_BY_PRIOR_OUTCOME"


class TestApplyAndOverrides:
    def test_apply_moves_an_alternate_lane_row_onto_its_untried_lane(self):
        cohort, _settled = PA.derive_cohort(
            [routed("a")],
            {"results": [prior("a", O.ACCESS_DENIED, tried=("brightdata_browser",))]})
        eligible, suppressed = RP.apply(cohort, {"results": [
            prior("a", O.ACCESS_DENIED, tried=("brightdata_browser",))]})
        assert suppressed == []
        assert eligible[0]["provider"] == "brightdata_web_unlocker"
        assert eligible[0]["routed_provider"] == "brightdata_browser"

    def test_the_registry_overlay_starts_the_row_on_the_untried_lane(self):
        from scripts.pettripfinder.acquisition import registry as REGISTRY
        eligible = [dict(routed("a"), provider="brightdata_web_unlocker",
                         lane_override={"provider": "brightdata_web_unlocker",
                                        "fallback_providers": []},
                         lanes_tried=["brightdata_browser"])]
        overlay = RP.lane_overrides_registry(eligible, work_order="WO",
                                             base=REGISTRY.load())
        route = REGISTRY.resolve(brand="HILTON", url="https://www.hilton.com/x",
                                 identity_key="a", registry=overlay)
        assert route.provider == "brightdata_web_unlocker"
        assert route.resolved_by == "property:a"
        assert route.measured_by == "WO"

    def test_no_alternate_rows_means_no_overlay(self):
        assert RP.lane_overrides_registry([routed("a")], work_order="WO") is None

    def test_a_forbidden_lane_cannot_be_reentered_through_the_overlay(self):
        # Choice forbids the Browser API; the ladder never contains it, so no
        # alternate can name it.
        entry = routed("a", provider="firecrawl", fallbacks=("brightdata_web_unlocker",))
        verdict = RP.classify(entry, prior("a", O.ACCESS_DENIED,
                                           tried=("firecrawl", "brightdata_web_unlocker")))
        assert verdict["classification"] == RP.RETRY_REQUIRES_ALTERNATE_LANE
        assert "brightdata_browser" not in verdict["approved_ladder"]


class TestLouisvilleReplay:
    """The eight retries Louisville paid for are suppressed by the policy over
    the committed artifacts, and every other cohort row passes through."""

    def test_the_eight_same_lane_retries_are_suppressed(self):
        from pathlib import Path
        base = Path("launch_packages/pettripfinder")
        plan = json.loads((base / "louisville_ky_cost_plan_003.json")
                          .read_text(encoding="utf-8"))
        merged = json.loads((base / "louisville_ky_acquisition_merged_003.json")
                            .read_text(encoding="utf-8"))
        retried = set(json.loads(
            (base / "louisville_ky_cohort_cost_plan_003.json")
            .read_text(encoding="utf-8"))["cohort_provenance"][
                "retried_after_an_attempt_that_answered_nothing"])
        eligible, suppressed = RP.apply(plan["cohort"], merged)
        assert {r["identity_key"] for r in suppressed} == retried
        assert len(eligible) == plan["cohort_size"] - len(retried)
        assert all(r["suppressed_because"] == RP.WHY_EVERY_LANE_TRIED
                   for r in suppressed)
