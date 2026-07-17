"""AES-DATA-002B -- aggregate recommendation semantics: a blocked/unusable
supplemental never poisons an otherwise-valid PRIMARY, the source-count
limit is enforced before any fetch, and every existing single-source
(``run_import``) behavior is provably untouched by this phase. No network."""

from __future__ import annotations

import json

import pytest

from pettripfinder.importer._aggregate_helpers import (
    CONTACT_URL,
    FAQ_URL,
    build_fetcher_extractor,
    contact_facts,
    contact_html,
    default_context,
    faq_facts,
    faq_html,
    make_cas,
)

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import
from scripts.pettripfinder.importer.candidate import (
    candidate_from_dict,
    candidate_to_dict,
    dumps_candidate,
    run_import,
)
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import FetchResult, ImportContext

_FAQ_MARKER = "Beer Garden operations are weather dependent"
_CONTACT_MARKER = "Call the taproom at"


def _run(urls, fetcher, extractor, ctx, tmp_path):
    return run_multi_import(
        urls, ctx, fetcher=fetcher, extractor=extractor, cas=make_cas(tmp_path),
        observed_at="2026-07-17", created_at="1970-01-01T00:00:00")


class TestBlockedSupplemental:
    def test_blocked_supplemental_preserved_primary_fields_populated(self, tmp_path):
        """Scenario 7: a 403-blocked supplemental never poisons an
        otherwise-usable PRIMARY. Recommendation is REVIEW for
        incomplete_source_set, PRIMARY's own fields still populate, and the
        blocked SourceRecord stays fully visible."""
        blocked_url = "https://landgrantbrewing.com/contact/"
        fetcher = StaticPageFetcher()
        fetcher.add_html(FAQ_URL, faq_html())
        fetcher.add_result(blocked_url, FetchResult(
            requested_url=blocked_url, ok=False, http_status=403,
            reason=C.REASON_BLOCKED_SOURCE))
        _, extractor = build_fetcher_extractor([(FAQ_URL, faq_html())], {_FAQ_MARKER: faq_facts()})

        c = _run([FAQ_URL, blocked_url], fetcher, extractor, default_context(), tmp_path)

        assert c.recommendation == C.RECOMMEND_REVIEW
        assert C.REASON_INCOMPLETE_SOURCE_SET in c.recommendation_reasons
        blocked = next(s for s in c.sources if s.final_url == blocked_url)
        assert blocked.usable is False
        assert blocked.fetch_reason == C.REASON_BLOCKED_SOURCE
        facts = dict(c.pet_facts)
        assert facts.get("pets_allowed") == "true"
        assert facts.get("patio_or_outdoor_only") == "true"

    def test_primary_fetch_failure_retains_existing_doctrine(self, tmp_path):
        """PRIMARY-level failure behaves exactly like the single-source
        fetch-failure path -- supplementals never promoted to primary."""
        fetcher = StaticPageFetcher()
        fetcher.add_result(FAQ_URL, FetchResult(
            requested_url=FAQ_URL, ok=False, http_status=500,
            reason=C.REASON_FETCH_FAILED))
        fetcher.add_html(CONTACT_URL, contact_html())
        _, extractor = build_fetcher_extractor(
            [(CONTACT_URL, contact_html())], {_CONTACT_MARKER: contact_facts()})

        c = _run([FAQ_URL, CONTACT_URL], fetcher, extractor, default_context(), tmp_path)
        assert c.recommendation == C.RECOMMEND_REJECT
        assert c.recommendation_reasons == (C.REASON_FETCH_FAILED,)
        assert len(c.sources) == 2
        assert c.sources[0].usable is False
        assert c.sources[0].role == C.SOURCE_ROLE_PRIMARY


class TestMaxSourceLimit:
    def test_five_urls_rejected_before_any_fetch(self):
        """Scenario 18."""
        calls = {"n": 0}

        class CountingFetcher:
            def fetch(self, url):
                calls["n"] += 1
                raise AssertionError("fetcher must never be called")

        ctx = default_context()
        with pytest.raises(ValueError):
            run_multi_import(
                [FAQ_URL] * 5, ctx, fetcher=CountingFetcher(),
                extractor=StaticFactExtractor({"facts": []}), cas=None,
                observed_at="2026-07-17", created_at="t")
        assert calls["n"] == 0

    def test_exactly_four_urls_allowed(self, tmp_path):
        urls = [FAQ_URL, CONTACT_URL,
               "https://landgrantbrewing.com/menu/", "https://landgrantbrewing.com/events/"]
        htmls = [faq_html(), contact_html()] + [
            ('<!doctype html><html><head><meta property="og:title" '
             'content="Land-Grant Brewing Columbus">'
             '<meta property="og:url" content="%s"></head>'
             "<body><h1>Land-Grant Brewing Columbus</h1><p>Info page.</p></body></html>" % u)
            for u in urls[2:]]
        fetcher, extractor = build_fetcher_extractor(
            list(zip(urls, htmls)),
            {_FAQ_MARKER: faq_facts(), _CONTACT_MARKER: contact_facts(),
             "Info page": {"facts": []}})
        c = _run(urls, fetcher, extractor, default_context(), tmp_path)
        assert len(c.sources) == 4

    def test_zero_urls_rejected(self):
        with pytest.raises(ValueError):
            run_multi_import(
                [], default_context(), fetcher=None, extractor=None, cas=None,
                observed_at="2026-07-17", created_at="t")


class TestSingleSourceRegressionUnaffected:
    """Scenario 19: run_import (the pre-existing entry point) must remain
    provably unchanged by this phase's candidate.py/recommend.py edits."""

    def test_run_import_untouched_no_aggregate_fields(self, tmp_path):
        fetcher = StaticPageFetcher()
        fetcher.add_html(FAQ_URL, faq_html())
        extractor = StaticFactExtractor(faq_facts())
        ctx = default_context()
        cas = make_cas(tmp_path)
        c = run_import(FAQ_URL, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                       observed_at="2026-07-17", created_at="1970-01-01T00:00:00")
        assert c.sources == ()
        assert c.aggregation_version == ""
        assert not (set(c.recommendation_reasons) & {
            C.REASON_IDENTITY_CONFLICT, C.REASON_GEOGRAPHY_CONFLICT,
            C.REASON_POLICY_CONFLICT, C.REASON_INCOMPLETE_SOURCE_SET})

    @pytest.mark.parametrize("fixture_stem", [
        "hotel_01_strong", "hotel_03_no_pets", "hotel_04_conflict",
        "park_01_offleash", "park_05_no_pets", "park_08_conflict",
        "restaurant_01_patio", "restaurant_03_no_pets", "restaurant_07_conflict",
    ])
    def test_gold_fixtures_unaffected(self, fixture_stem, tmp_path):
        from pathlib import Path
        from scripts.import_official_url import _build_static

        fixtures_dir = Path(__file__).parent / "fixtures"
        obj = json.loads((fixtures_dir / (fixture_stem + ".json")).read_text(encoding="utf-8"))
        url = obj["url"]
        fetcher, extractor = _build_static(url, str(fixtures_dir / (fixture_stem + ".json")))
        ctx_raw = obj.get("context", {})
        ctx = ImportContext(
            category=ctx_raw.get("category", ""), expected_city=ctx_raw.get("expected_city", ""),
            expected_state=ctx_raw.get("expected_state", ""))
        cas = make_cas(tmp_path)
        c = run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                       observed_at="2026-07-17", created_at="1970-01-01T00:00:00")
        assert c.recommendation == obj["expected_recommendation"]
        assert c.sources == ()
        assert c.aggregation_version == ""


class TestLegacyCandidateLoad:
    """Scenario 20."""

    def test_pre_002_shape_loads_and_approves_normally(self, tmp_path):
        fetcher = StaticPageFetcher()
        fetcher.add_html(FAQ_URL, faq_html())
        extractor = StaticFactExtractor(faq_facts())
        ctx = default_context()
        cas = make_cas(tmp_path)
        c = run_import(FAQ_URL, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                       observed_at="2026-07-17", created_at="1970-01-01T00:00:00")
        old_shape = candidate_to_dict(c)
        assert "sources" not in old_shape
        assert "aggregation_version" not in old_shape
        reloaded = candidate_from_dict(old_shape)
        assert reloaded.sources == ()
        assert reloaded.aggregation_version == ""
        assert reloaded == c

    def test_aggregate_candidate_round_trips(self, tmp_path):
        fetcher, extractor = build_fetcher_extractor(
            [(FAQ_URL, faq_html()), (CONTACT_URL, contact_html())],
            {_FAQ_MARKER: faq_facts(), _CONTACT_MARKER: contact_facts()})
        c = _run([FAQ_URL, CONTACT_URL], fetcher, extractor, default_context(), tmp_path)
        reloaded = candidate_from_dict(json.loads(dumps_candidate(c)))
        assert reloaded == c
        assert reloaded.sources[0].source_id == "S1"
        assert reloaded.sources[1].source_id == "S2"
        assert reloaded.aggregation_version == C.AGGREGATION_VERSION
