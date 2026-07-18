"""AES-DATA-004A discovery -- coverage report tests (Task 11)."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.coverage import (
    build_coverage_summary,
    render_coverage_html,
    render_coverage_json,
)
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.models import DiscoveryRecord, DiscoverySourceQuery
from scripts.pettripfinder.discovery.normalize import normalize_records
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult


def _market():
    return load_market_config("columbus-oh")


def rec(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="id1",
               canonical_category=C.CATEGORY_VETERINARY, name="Test",
               provenance=(("market_id", "columbus-oh"), ("cell_id", "columbus-oh__columbus-downtown")))
    base.update(kw)
    return DiscoveryRecord(**base)


def _query(qid, provider, category="veterinary"):
    m = _market()
    cell = m.cells[0]
    return DiscoverySourceQuery(query_id=qid, provider=provider, canonical_category=category,
                                query_text="x", market_id=m.market_id, cell_id=cell.cell_id,
                                center_lat=cell.center_lat, center_lng=cell.center_lng,
                                radius_meters=cell.radius_meters, max_pages=1)


def test_overlap_and_provider_only_counts():
    m = _market()
    g = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="g1", name="Shared Vet",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    o = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1", name="Shared Vet",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    solo = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="g2", name="Google Only Vet")
    records = normalize_records((g, o, solo))
    candidates = deduplicate(records, market_id=m.market_id)

    q1 = _query("q1", C.PROVIDER_GOOGLE_PLACES)
    q2 = _query("q2", C.PROVIDER_OPENSTREETMAP)
    results = [
        ProviderQueryResult(query_id="q1", provider=C.PROVIDER_GOOGLE_PLACES,
                            state=C.QUERY_STATE_COMPLETED, records=(g, solo), requests_made=1,
                            pages_fetched=1),
        ProviderQueryResult(query_id="q2", provider=C.PROVIDER_OPENSTREETMAP,
                            state=C.QUERY_STATE_COMPLETED, records=(o,), requests_made=1,
                            pages_fetched=1),
    ]
    summary = build_coverage_summary(
        market=m, observed_at="2026-07-18", providers_enabled=(C.PROVIDER_GOOGLE_PLACES, C.PROVIDER_OPENSTREETMAP),
        google_key_present=True, foursquare_key_present=False,
        planned_queries=[q1, q2], query_results=results, candidates=candidates,
    )
    assert dict(summary.overlap_by_provider_pair) == {
        "%s+%s" % (C.PROVIDER_GOOGLE_PLACES, C.PROVIDER_OPENSTREETMAP): 1
    }
    assert dict(summary.provider_only_candidates) == {C.PROVIDER_GOOGLE_PLACES: 1}
    assert summary.unique_candidates == 2
    assert summary.duplicates_merged == 1


def test_category_totals():
    m = _market()
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="a1", canonical_category=C.CATEGORY_VETERINARY)
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="b1", canonical_category=C.CATEGORY_BOARDING,
           name="Different Business")
    candidates = deduplicate(normalize_records((a, b)), market_id=m.market_id)
    q1 = _query("q1", C.PROVIDER_GOOGLE_PLACES)
    results = [ProviderQueryResult(query_id="q1", provider=C.PROVIDER_GOOGLE_PLACES,
                                   state=C.QUERY_STATE_COMPLETED, records=(a, b), requests_made=1,
                                   pages_fetched=1)]
    summary = build_coverage_summary(
        market=m, observed_at="2026-07-18", providers_enabled=(C.PROVIDER_GOOGLE_PLACES,),
        google_key_present=True, foursquare_key_present=False,
        planned_queries=[q1], query_results=results, candidates=candidates,
    )
    assert dict(summary.counts_by_category) == {C.CATEGORY_VETERINARY: 1, C.CATEGORY_BOARDING: 1}


def test_zero_division_safety_empty_run():
    m = _market()
    summary = build_coverage_summary(
        market=m, observed_at="2026-07-18", providers_enabled=(),
        google_key_present=False, foursquare_key_present=False,
        planned_queries=[], query_results=[], candidates=(),
    )
    html_out = render_coverage_html(summary)   # must not raise ZeroDivisionError
    assert "0/0" in html_out
    assert summary.unique_candidates == 0


def test_missing_optional_provider_foursquare_shows_unavailable():
    m = _market()
    summary = build_coverage_summary(
        market=m, observed_at="2026-07-18", providers_enabled=(C.PROVIDER_GOOGLE_PLACES,),
        google_key_present=True, foursquare_key_present=False,
        planned_queries=[], query_results=[], candidates=(),
    )
    assert dict(summary.credentials_available)[C.PROVIDER_FOURSQUARE] is False
    html_out = render_coverage_html(summary)
    assert "FOURSQUARE" in html_out


def test_html_escaping_of_hostile_candidate_name():
    m = _market()
    hostile = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="x1",
                  name="<script>alert(1)</script>")
    candidates = deduplicate(normalize_records((hostile,)), market_id=m.market_id)
    summary = build_coverage_summary(
        market=m, observed_at="2026-07-18", providers_enabled=(C.PROVIDER_GOOGLE_PLACES,),
        google_key_present=True, foursquare_key_present=False,
        planned_queries=[], query_results=[], candidates=candidates,
    )
    # category/municipality names come from controlled vocab, not raw
    # candidate names, but exercise the render path end-to-end regardless.
    html_out = render_coverage_html(summary)
    assert "<script>alert(1)</script>" not in html_out


def test_json_render_is_valid_and_sorted():
    import json
    m = _market()
    summary = build_coverage_summary(
        market=m, observed_at="2026-07-18", providers_enabled=(C.PROVIDER_GOOGLE_PLACES,),
        google_key_present=True, foursquare_key_present=False,
        planned_queries=[], query_results=[], candidates=(),
    )
    text = render_coverage_json(summary)
    data = json.loads(text)
    assert data["market_id"] == "columbus-oh"
    assert "disclosure" in data
    assert "%" not in data["disclosure"] or "No completeness percentage" in data["disclosure"]


def test_query_completion_reflects_disabled_and_skipped():
    m = _market()
    q1 = _query("q1", C.PROVIDER_GOOGLE_PLACES)
    q_disabled = DiscoverySourceQuery(query_id="qf", provider=C.PROVIDER_FOURSQUARE,
                                      canonical_category="veterinary", enabled=False,
                                      market_id=m.market_id)
    results = [ProviderQueryResult(query_id="q1", provider=C.PROVIDER_GOOGLE_PLACES,
                                   state=C.QUERY_STATE_COMPLETED, requests_made=1, pages_fetched=1)]
    summary = build_coverage_summary(
        market=m, observed_at="2026-07-18", providers_enabled=(C.PROVIDER_GOOGLE_PLACES,),
        google_key_present=True, foursquare_key_present=False,
        planned_queries=[q1, q_disabled], query_results=results, candidates=(),
    )
    completion = dict(summary.query_completion)
    assert completion["q1"] == C.QUERY_STATE_COMPLETED
    assert completion["qf"] == C.QUERY_STATE_DISABLED
