"""PTF-SPIDER-BENCHMARK-001 -- the Spider lane and its benchmark.

Two things are being protected here. First, that the lane borrows the measured
pipeline instead of bringing its own, because a benchmark whose two arms differ
in more than the vendor is not a benchmark. Second, that measuring a provider
did not quietly promote it: the route table is proven, and a benchmark does not
get to edit it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.acquisition import spider_benchmark_001 as BENCH
from scripts.pettripfinder.acquisition import spider_capture as SPIDER
from scripts.pettripfinder.brightdata import unlocker_capture as UC

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT = (REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
          / "ptf_spider_benchmark_001.json")


class TestMeasuringAProviderDidNotPromoteIt:
    def test_spider_is_still_not_a_routable_provider(self):
        """It is implemented and it is deliberately not registered. Promotion
        is a decision with a measurement behind it, not a side effect of
        having written an adapter."""
        assert "spider" not in PROVIDERS.all_ids()
        assert "spider" not in PROVIDERS.implemented()
        assert "spider" in PROVIDERS.KNOWN_FUTURE_PROVIDERS

    def test_the_route_table_still_names_only_the_measured_lanes(self):
        registry = REGISTRY.load()
        providers = {registry["default"]["provider"]}
        for entry in registry["brands"].values():
            providers.add(entry["provider"])
            providers.update(entry.get("fallback_providers") or ())
        for entry in registry["domains"].values():
            providers.add(entry["provider"])
            providers.update(entry.get("fallback_providers") or ())
        assert "spider" not in providers

    def test_choice_still_forbids_the_browser_api(self):
        """The benchmark must not have disturbed the one route rule that was
        bought with fifteen failed attempts."""
        route = REGISTRY.resolve(
            brand="CHOICE",
            url="https://www.choicehotels.com/wisconsin/milwaukee/cambria-hotels/wi297")
        assert route.provider == "brightdata_web_unlocker"
        assert "brightdata_browser" in route.forbidden_providers


class TestTheLaneBorrowsTheMeasuredPipeline:
    def test_it_reuses_the_unlocker_gates_rather_than_reimplementing_them(self):
        """Same text extraction, same denial markers, same policy locator,
        same persistence. If these ever fork, the benchmark stops comparing
        vendors and starts comparing pipelines."""
        import inspect
        source = inspect.getsource(SPIDER)
        for borrowed in ("UC.html_to_text", "UC.DENIAL_MARKERS",
                         "UC.locate_policy_in_html", "UC._persist"):
            assert borrowed in source, borrowed

    def test_it_uses_the_same_page_health_and_identity_gates(self):
        import inspect
        source = inspect.getsource(SPIDER)
        assert "PS.page_health" in source
        assert "PS.read_identity" in source
        assert "PS.assess_identity" in source
        assert "PR.parse" in source

    def test_the_retry_rule_is_the_unlockers(self):
        """A page that ANSWERED is not re-fetched. Retrying an identity
        mismatch buys the same answer at full price."""
        import inspect
        source = inspect.getsource(SPIDER.capture_property)
        assert "worth_retrying" in source

    def test_the_request_profile_is_the_anti_bot_one(self):
        """The fair comparison against an unlocker, which is an anti-bot
        product -- not a bare fetch that would lose on a technicality."""
        profile = SPIDER.DEFAULT_REQUEST
        assert profile["request"] == "chrome"
        assert profile["proxy_enabled"] is True
        assert profile["stealth"] is True


class TestTheKeyNeverLeaks:
    def test_the_key_is_redacted_from_any_text(self, monkeypatch):
        monkeypatch.setenv(SPIDER.KEY_ENV, "sk-secret-value-123")
        assert "sk-secret-value-123" not in SPIDER.redact(
            "failed with key sk-secret-value-123")
        assert "<redacted:spider-key>" in SPIDER.redact("key sk-secret-value-123")

    def test_redaction_is_safe_when_no_key_is_set(self, monkeypatch):
        monkeypatch.delenv(SPIDER.KEY_ENV, raising=False)
        assert SPIDER.redact("nothing to hide") == "nothing to hide"
        assert SPIDER.credential_present() is False

    def test_a_fetch_without_a_key_fails_closed(self, monkeypatch):
        monkeypatch.delenv(SPIDER.KEY_ENV, raising=False)
        with pytest.raises(SPIDER.SpiderError):
            SPIDER.fetch("https://example.com/")


class TestTheComparisonVocabulary:
    def test_identical_extractions_are_all_match(self):
        base = {"pets_allowed": True, "pet_count_limit": 2}
        assert BENCH.compare(base, dict(base))["counts"] == {"MATCH": 2}

    def test_a_field_only_the_baseline_had_is_missing(self):
        result = BENCH.compare({"pets_allowed": True, "pet_fee": {"amount": 50}},
                               {"pets_allowed": True})
        assert result["per_field"]["pet_fee"] == "MISSING"

    def test_a_field_only_spider_had_is_extra(self):
        result = BENCH.compare({"pets_allowed": True},
                               {"pets_allowed": True, "pet_count_limit": 2})
        assert result["per_field"]["pet_count_limit"] == "EXTRA"

    def test_disagreement_is_a_mismatch_and_is_never_folded_into_missing(self):
        """The distinction the whole benchmark turns on. A missing field costs
        coverage; a disagreeing field would publish a wrong fact to a guest."""
        result = BENCH.compare({"pet_fee": {"amount": 50, "basis": "per_night"}},
                               {"pet_fee": {"amount": 75, "basis": "per_night"}})
        assert result["per_field"]["pet_fee"] == "MISMATCH"
        assert result["counts"]["MISMATCH"] == 1
        assert result["mismatches"]["pet_fee"]["bright_data"]["amount"] == 50
        assert result["mismatches"]["pet_fee"]["spider"]["amount"] == 75

    def test_mismatches_are_reported_with_both_sides(self):
        result = BENCH.compare({"pet_count_limit": 2}, {"pet_count_limit": 3})
        assert set(result["mismatches"]["pet_count_limit"]) == {"bright_data", "spider"}


class TestTheBaselineIsRealNotSynthetic:
    def test_the_baseline_is_the_committed_publication_grade_captures(self):
        rows = BENCH.baseline_rows()
        if not rows:
            pytest.skip("no journal in this worktree")
        for row in rows:
            assert row["final_state"] == "ACQUIRED_PUBLICATION_GRADE"
            assert row["official_url"].startswith("http")

    def test_the_reachable_lane_list_is_recorded_as_measured(self):
        assert set(BENCH.REACHABLE_READERS) == {"ihg", "wyndham", "generic"}


class TestTheCommittedBenchmark:
    def _doc(self):
        if not REPORT.is_file():
            pytest.skip("benchmark not run in this worktree")
        return json.loads(REPORT.read_text(encoding="utf-8-sig"))

    def test_the_benchmark_wrote_no_authority_and_changed_no_routes(self):
        doc = self._doc()
        assert doc["authority_written"] is False
        assert doc["routes_changed"] is False

    def test_cost_is_the_vendors_own_figure_not_an_inference(self):
        doc = self._doc()
        assert "reports its own per-request cost" in doc["cost"]["basis"]
        assert doc["cost"]["spider_reported_usd"] >= 0

    def test_every_sampled_property_has_an_outcome(self):
        doc = self._doc()
        assert len(doc["items"]) == doc["sample_size"]
        for row in doc["items"]:
            assert row["spider_outcome"]
            assert "spider_state" in row

    def test_any_mismatch_is_surfaced_with_both_values(self):
        doc = self._doc()
        detail = doc["field_comparison"]["mismatch_detail"]
        assert len(detail) == doc["field_comparison"]["properties_with_a_mismatch"]
        for row in detail:
            for field, sides in row["mismatches"].items():
                assert set(sides) == {"bright_data", "spider"}

# --------------------------------------------------------------------------- #
# PTF-FIRECRAWL-BENCHMARK-002
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.acquisition import firecrawl_benchmark_002 as FCB
from scripts.pettripfinder.acquisition import firecrawl_capture as FIRECRAWL

FC_REPORT = (REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
             / "reports" / "ptf_firecrawl_benchmark_002.json")


class TestFirecrawlIsAlsoNotPromoted:
    def test_firecrawl_is_not_a_routable_provider(self):
        assert "firecrawl" not in PROVIDERS.all_ids()
        assert "firecrawl" in PROVIDERS.KNOWN_FUTURE_PROVIDERS

    def test_the_route_table_is_still_untouched(self):
        registry = REGISTRY.load()
        names = {registry["default"]["provider"]}
        for entry in list(registry["brands"].values()) + list(registry["domains"].values()):
            names.add(entry["provider"])
            names.update(entry.get("fallback_providers") or ())
        assert "firecrawl" not in names and "spider" not in names


class TestTheFirecrawlLaneBorrowsTheSamePipeline:
    def test_it_reuses_the_unlocker_gates(self):
        import inspect
        source = inspect.getsource(FIRECRAWL)
        for borrowed in ("UC.html_to_text", "UC.DENIAL_MARKERS",
                         "UC.locate_policy_in_html", "UC._persist",
                         "PS.page_health", "PS.assess_identity", "PR.parse"):
            assert borrowed in source, borrowed

    def test_it_asks_for_raw_html_not_markdown(self):
        """Every downstream gate reads HTML. A markdown conversion would drop
        the class names the brand locators key on."""
        assert FIRECRAWL.DEFAULT_PROFILE["formats"] == ["rawHtml"]

    def test_it_waits_for_the_page_to_paint(self):
        """The entire reason this vendor was worth testing: Spider failed by
        returning the shell."""
        assert FIRECRAWL.DEFAULT_PROFILE["waitFor"] >= 3000

    def test_the_two_benchmarks_share_one_comparison_vocabulary(self):
        """Two definitions of MISMATCH would make the vendors incomparable,
        which is the only thing running a second vendor is for."""
        from scripts.pettripfinder.acquisition import spider_benchmark_001 as SB
        assert FCB.compare is SB.compare
        assert FCB.baseline_rows is SB.baseline_rows


class TestARateLimitIsNotACapabilityFailure:
    def test_rate_limiting_has_its_own_error_class(self):
        assert issubclass(FIRECRAWL.FirecrawlRateLimited, FIRECRAWL.FirecrawlError)

    def test_a_rate_limit_is_reported_as_a_quota_result(self):
        """Ten properties first came back NAVIGATION_FAILED on HTTP 429 and
        every one of them acquired cleanly when paced. Folding a quota result
        into a capability failure would have reported 60% for a lane that
        reaches 100%."""
        import inspect
        source = inspect.getsource(FIRECRAWL.run_attempt)
        assert "RATE_LIMITED" in source
        assert "says nothing about" in source


class TestMismatchClassification:
    def test_a_numeric_disagreement_is_structured(self):
        out = FCB.classify_mismatches(
            {"pet_fee": {"bright_data": 5000, "firecrawl": 3000}})
        assert "pet_fee" in out["structured_disagreements"]
        assert out["text_excerpt_variants"] == {}

    def test_two_quotes_of_the_same_prose_are_a_text_variant(self):
        out = FCB.classify_mismatches({"service_animal_exception": {
            "bright_data": "Pet & Service Animal Policy",
            "firecrawl": "Service Animals - ADA-defined service animals welcome."}})
        assert "service_animal_exception" in out["text_excerpt_variants"]
        assert out["structured_disagreements"] == {}

    def test_a_dict_valued_disagreement_is_structured(self):
        out = FCB.classify_mismatches({"weight_limit": {
            "bright_data": {"value": 25.0, "unit": "lb"},
            "firecrawl": {"value": 50.0, "unit": "lb"}}})
        assert "weight_limit" in out["structured_disagreements"]


class TestTheCommittedFirecrawlBenchmark:
    def _doc(self):
        if not FC_REPORT.is_file():
            pytest.skip("firecrawl benchmark not run in this worktree")
        return json.loads(FC_REPORT.read_text(encoding="utf-8-sig"))

    def test_it_wrote_no_authority_and_changed_no_routes(self):
        doc = self._doc()
        assert doc["authority_written"] is False
        assert doc["routes_changed"] is False

    def test_no_structured_disagreement_survived(self):
        """The disqualifying number. Different excerpts of prose are tolerable;
        a different fee or weight limit is not."""
        doc = self._doc()
        assert doc["agreement"]["properties_with_a_STRUCTURED_disagreement"] == 0
        assert doc["agreement"]["structured_disagreement_detail"] == []

    def test_cost_is_reported_in_credits_and_says_so(self):
        doc = self._doc()
        assert "credits" in doc["cost"]["basis"]
        assert "not a dollar figure" in doc["cost"]["basis"]

    def test_completeness_is_reported_in_both_directions(self):
        """A vendor that gains fields somewhere and loses them elsewhere must
        show both, or the report is an advertisement."""
        comp = self._doc()["completeness"]
        assert "fields_gained_over_baseline" in comp
        assert "fields_lost_versus_baseline" in comp
        assert comp["properties_where_baseline_extracted_more"] >= 0
