"""AES-DATA-004C -- resolution runner orchestration tests."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord
from scripts.pettripfinder.discovery.resolution_fetch_plan import build_fetch_plan
from scripts.pettripfinder.discovery.resolution_runner import (
    combine_lodging_candidate_pools,
    resolve_static,
    resolve_with_fetch,
)
from scripts.pettripfinder.discovery.website_fetcher import ResolutionCache


def _market():
    return load_market_config("columbus-oh")


def _candidate(cid, categories, name="Test", record_id="p1"):
    r = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id=record_id,
                        canonical_category=categories[0], name=name)
    return DiscoveryCandidate(candidate_id=cid, source_records=(r,), name=name,
                              normalized_name=name.lower(), category_candidates=tuple(categories),
                              city="Columbus", state="OH")


def test_cross_category_duplicate_merges_not_double_counted():
    # Same candidate_id found independently in both the hotel and motel
    # pools (real Wave 1 finding: same Google Place ID, "Travel lodge
    # motel", found by both category query sets).
    hotel_version = _candidate("dc_shared", ["hotel"])
    motel_version = _candidate("dc_shared", ["motel"])
    combined = combine_lodging_candidate_pools((hotel_version,), (motel_version,))
    assert len(combined) == 1
    assert combined[0].category_candidates == ("hotel", "motel")


def test_non_overlapping_pools_all_preserved():
    hotel_only = _candidate("dc_h1", ["hotel"])
    motel_only = _candidate("dc_m1", ["motel"])
    combined = combine_lodging_candidate_pools((hotel_only,), (motel_only,))
    assert len(combined) == 2


def test_merged_source_records_union_not_duplicated():
    r1 = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                         canonical_category=C.CATEGORY_HOTEL, name="Test",
                         source_query_id="q_hotel")
    r2 = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                         canonical_category=C.CATEGORY_MOTEL, name="Test",
                         source_query_id="q_motel")
    hotel_version = DiscoveryCandidate(candidate_id="dc_shared", source_records=(r1,), name="Test",
                                       category_candidates=("hotel",))
    motel_version = DiscoveryCandidate(candidate_id="dc_shared", source_records=(r2,), name="Test",
                                       category_candidates=("motel",))
    combined = combine_lodging_candidate_pools((hotel_version,), (motel_version,))
    assert len(combined) == 1
    assert len(combined[0].source_records) == 2


def test_resolve_static_no_double_counted_identity_outcomes_after_combine():
    # Mirrors what deduplicate() actually produces for a genuine same-
    # address conflict pair (review_state=NEEDS_REVIEW) -- b additionally
    # appears cross-category (found live in Wave 1), so the combine step
    # must collapse it to one candidate before identity grouping runs.
    a = DiscoveryCandidate(candidate_id="dc_a", source_records=(), name="Alpha Inn",
                           normalized_name="alpha inn", category_candidates=("hotel",),
                           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215",
                           review_state=C.REVIEW_STATE_NEEDS_REVIEW,
                           conflict_flags=(C.CONFLICT_NAME_MISMATCH,))
    b_hotel = DiscoveryCandidate(candidate_id="dc_b", source_records=(), name="Alpha Suites",
                                 normalized_name="alpha suites", category_candidates=("hotel",),
                                 address_line="1 Main St", city="Columbus", state="OH", postal_code="43215",
                                 review_state=C.REVIEW_STATE_NEEDS_REVIEW,
                                 conflict_flags=(C.CONFLICT_NAME_MISMATCH,))
    b_motel = DiscoveryCandidate(candidate_id="dc_b", source_records=(), name="Alpha Suites",
                                 normalized_name="alpha suites", category_candidates=("motel",),
                                 address_line="1 Main St", city="Columbus", state="OH", postal_code="43215",
                                 review_state=C.REVIEW_STATE_NEEDS_REVIEW,
                                 conflict_flags=(C.CONFLICT_NAME_MISMATCH,))
    combined = combine_lodging_candidate_pools((a, b_hotel), (b_motel,))
    assert len(combined) == 2   # dc_a and merged dc_b, not 3
    m = _market()
    resolved = resolve_static(combined, m)
    identity_outcomes = [r.identity_outcome for r in resolved if r.identity_outcome]
    assert len(identity_outcomes) == 2   # exactly the (a, b) pair, not duplicated


def test_cache_only_miss_never_counted_as_http_request(tmp_path):
    # A --cache-only run against a URL with NO cache entry must report
    # zero HTTP requests -- the fetcher's real .fetch() is never called
    # (bug found and fixed live: cache-only misses were miscounted as
    # actual live requests in the stats).
    class ExplodingFetcher:
        def fetch(self, url):
            raise AssertionError("live fetch attempted during --cache-only run")

    m = _market()
    r = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                        canonical_category=C.CATEGORY_HOTEL, name="Test Hotel",
                        website_url="https://example.com/property")
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(r,), name="Test Hotel",
                                   normalized_name="test hotel", category_candidates=("hotel",),
                                   city="Columbus", state="OH")

    from scripts.pettripfinder.discovery.website_resolution import classify_candidate_urls_statically
    from scripts.pettripfinder.discovery.resolution_runner import build_identity_review_ids

    static_map = {candidate.candidate_id: classify_candidate_urls_statically(candidate)}
    identity_ids = build_identity_review_ids((candidate,))
    fetch_plan = build_fetch_plan((candidate,), static_map, identity_ids, max_total=40)
    assert len(fetch_plan.items) == 1

    cache = ResolutionCache(tmp_path / "cache")
    resolved, stats = resolve_with_fetch(
        (candidate,), m, fetch_plan=fetch_plan, fetcher=ExplodingFetcher(), cache=cache,
        pacer=None, observed_at="2026-07-18", cache_only=True,
    )
    assert stats.http_requests == 0
    assert stats.cache_hits == 0


def test_cache_only_miss_never_downgrades_candidate_to_fetch_blocked(tmp_path):
    # A --cache-only miss (no cache entry, never actually fetched) must
    # leave the candidate exactly as the static pass classified it --
    # never downgrade it to FETCH_BLOCKED/REVIEW_WEBSITE just because the
    # plan included it (bug found and fixed live: this wrongly demoted 30
    # otherwise-fine PROPERTY_OFFICIAL_URL_PROBABLE candidates during Wave
    # 1 cache-only replay).
    class ExplodingFetcher:
        def fetch(self, url):
            raise AssertionError("live fetch attempted during --cache-only run")

    m = _market()
    r = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                        canonical_category=C.CATEGORY_HOTEL, name="Test Hotel",
                        website_url="https://example.com/property")
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(r,), name="Test Hotel",
                                   normalized_name="test hotel", category_candidates=("hotel",),
                                   city="Columbus", state="OH")

    from scripts.pettripfinder.discovery.website_resolution import classify_candidate_urls_statically
    from scripts.pettripfinder.discovery.resolution_runner import build_identity_review_ids

    static_map = {candidate.candidate_id: classify_candidate_urls_statically(candidate)}
    static_state = static_map[candidate.candidate_id][0].resolution_state
    assert static_state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE   # sanity: independent domain

    identity_ids = build_identity_review_ids((candidate,))
    fetch_plan = build_fetch_plan((candidate,), static_map, identity_ids, max_total=40)
    assert len(fetch_plan.items) == 1

    cache = ResolutionCache(tmp_path / "cache")
    resolved, stats = resolve_with_fetch(
        (candidate,), m, fetch_plan=fetch_plan, fetcher=ExplodingFetcher(), cache=cache,
        pacer=None, observed_at="2026-07-18", cache_only=True,
    )
    result = resolved[0]
    assert result.website_resolutions[0].resolution_state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE
    assert result.resolution_outcome != C.RESOLUTION_REVIEW_WEBSITE
