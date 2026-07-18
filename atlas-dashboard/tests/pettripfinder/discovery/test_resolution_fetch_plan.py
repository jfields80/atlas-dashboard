"""AES-DATA-004C Task 6 -- fetch plan tests. Pure, no network."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, WebsiteResolution
from scripts.pettripfinder.discovery.resolution_fetch_plan import (
    PRIORITY_CONFLICTING_WEBSITE,
    PRIORITY_IDENTITY_REVIEW,
    PRIORITY_PROBABLE_OR_CHAIN_HOMEPAGE,
    build_fetch_plan,
)


def _cand(cid, name="Test"):
    return DiscoveryCandidate(candidate_id=cid, source_records=(), name=name)


def _res(cid, state, url="https://example.com/x", domain="example.com"):
    return WebsiteResolution(candidate_id=cid, source_provider=C.PROVIDER_GOOGLE_PLACES,
                             original_url=url, normalized_url=url, registrable_domain=domain,
                             resolution_state=state)


def test_identity_review_gets_highest_priority():
    candidates = [_cand("dc_1")]
    static_map = {"dc_1": (_res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE),)}
    plan = build_fetch_plan(candidates, static_map, ["dc_1"])
    assert len(plan.items) == 1
    assert plan.items[0].priority == PRIORITY_IDENTITY_REVIEW


def test_conflicting_website_priority_when_not_identity_review():
    candidates = [_cand("dc_1")]
    static_map = {"dc_1": (
        _res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://a.com", "a.com"),
        _res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://b.com", "b.com"),
    )}
    plan = build_fetch_plan(candidates, static_map, [])
    assert all(item.priority == PRIORITY_CONFLICTING_WEBSITE for item in plan.items)


def test_probable_only_lowest_of_the_three_active_priorities():
    candidates = [_cand("dc_1")]
    static_map = {"dc_1": (_res("dc_1", C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY),)}
    plan = build_fetch_plan(candidates, static_map, [])
    assert plan.items[0].priority == PRIORITY_PROBABLE_OR_CHAIN_HOMEPAGE


def test_third_party_and_social_never_fetched():
    candidates = [_cand("dc_1")]
    static_map = {"dc_1": (
        _res("dc_1", C.WEBSITE_RES_THIRD_PARTY_BOOKING_URL, "https://booking.com/x", "booking.com"),
        _res("dc_1", C.WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL, "https://facebook.com/x", "facebook.com"),
    )}
    plan = build_fetch_plan(candidates, static_map, [])
    assert plan.items == ()
    assert len(plan.blocked_third_party_urls) == 2


def test_missing_and_unresolved_never_fetched():
    candidates = [_cand("dc_1")]
    static_map = {"dc_1": (_res("dc_1", C.WEBSITE_RES_MISSING, url=""),)}
    plan = build_fetch_plan(candidates, static_map, [])
    assert plan.items == ()


def test_global_cap_enforced():
    candidates = [_cand("dc_%d" % i) for i in range(10)]
    static_map = {
        "dc_%d" % i: (_res("dc_%d" % i, C.WEBSITE_RES_PROPERTY_URL_PROBABLE,
                          "https://example-%d.com" % i, "example-%d.com" % i),)
        for i in range(10)
    }
    plan = build_fetch_plan(candidates, static_map, [], max_total=3)
    assert len(plan.items) == 3
    assert plan.excluded_by_cap_count == 7


def test_per_candidate_cap_enforced():
    candidates = [_cand("dc_1")]
    static_map = {"dc_1": (
        _res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://a.com", "a.com"),
        _res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://b.com", "b.com"),
        _res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://c.com", "c.com"),
    )}
    plan = build_fetch_plan(candidates, static_map, [], max_per_candidate=2)
    assert len(plan.items) == 2


def test_per_domain_cap_enforced():
    candidates = [_cand("dc_%d" % i) for i in range(5)]
    static_map = {
        "dc_%d" % i: (_res("dc_%d" % i, C.WEBSITE_RES_PROPERTY_URL_PROBABLE,
                          "https://shared.com/%d" % i, "shared.com"),)
        for i in range(5)
    }
    plan = build_fetch_plan(candidates, static_map, [], max_per_domain=2)
    assert len(plan.items) == 2
    assert dict(plan.per_domain_counts) == {"shared.com": 2}


def test_no_duplicate_url_double_counted():
    candidates = [_cand("dc_1")]
    static_map = {"dc_1": (
        _res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://a.com", "a.com"),
        _res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://a.com", "a.com"),
    )}
    plan = build_fetch_plan(candidates, static_map, [])
    assert len(plan.items) == 1


def test_static_only_count_reflects_candidates_needing_no_fetch():
    candidates = [_cand("dc_1"), _cand("dc_2")]
    static_map = {
        "dc_1": (_res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE),),
        "dc_2": (_res("dc_2", C.WEBSITE_RES_MISSING, url=""),),
    }
    plan = build_fetch_plan(candidates, static_map, [])
    assert plan.total_candidates == 2
    assert plan.static_only_count == 1
    assert plan.fetch_required_count == 1


def test_deterministic_ordering_regardless_of_input_order():
    candidates_a = [_cand("dc_2"), _cand("dc_1")]
    candidates_b = [_cand("dc_1"), _cand("dc_2")]
    static_map = {
        "dc_1": (_res("dc_1", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://a.com", "a.com"),),
        "dc_2": (_res("dc_2", C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "https://b.com", "b.com"),),
    }
    plan_a = build_fetch_plan(candidates_a, static_map, [])
    plan_b = build_fetch_plan(candidates_b, static_map, [])
    assert plan_a.items == plan_b.items
