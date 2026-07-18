"""AES-DATA-004C Tasks 7/8 -- website fetcher + post-fetch identity
validation tests. No real network -- a fake fetcher stands in for
``RequestsPageFetcher``."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate
from scripts.pettripfinder.discovery.website_fetcher import (
    DomainPacer,
    IdentitySnapshot,
    ResolutionCache,
    fetch_for_identity,
    parse_identity_snapshot,
)
from scripts.pettripfinder.discovery.website_resolution import validate_fetched_identity
from scripts.pettripfinder.importer.models import FetchResult


class FakeFetcher:
    def __init__(self, results: dict):
        self._results = results
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        return self._results[url]


def _hotel_page(name, street, city, state):
    body = (
        '<title>%s | Example Brand</title>'
        '<script type="application/ld+json">{"@type": "Hotel", "name": "%s", '
        '"address": {"@type": "PostalAddress", "streetAddress": "%s", '
        '"addressLocality": "%s", "addressRegion": "%s"}}</script>'
        % (name, name, street, city, state)
    ).encode("utf-8")
    return body


def test_matching_hotel_jsonld_confirms_identity():
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test Hotel",
                                   normalized_name="test hotel", address_line="1 Main St",
                                   city="Columbus", state="OH")
    body = _hotel_page("Test Hotel", "1 Main St", "Columbus", "OH")
    snap = parse_identity_snapshot(body)
    state, warnings = validate_fetched_identity(
        candidate, page_title=snap.title, structured_name=snap.structured_name,
        structured_address=snap.structured_address, fetch_ok=True, fetch_reason="",
        registrable_domain_value="example.com")
    assert state == C.WEBSITE_RES_PROPERTY_URL_CONFIRMED


def test_matching_address_in_visible_title_only_weaker():
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test Hotel",
                                   normalized_name="test hotel", address_line="1 Main St",
                                   city="Columbus", state="OH")
    state, warnings = validate_fetched_identity(
        candidate, page_title="Test Hotel | Brand", structured_name="", structured_address="",
        fetch_ok=True, fetch_reason="", registrable_domain_value="example.com")
    assert state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE


def test_mismatched_property_never_confirmed():
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test Hotel",
                                   normalized_name="test hotel", address_line="1 Main St",
                                   city="Columbus", state="OH")
    body = _hotel_page("A Totally Different Hotel", "999 Other Ave", "Dublin", "OH")
    snap = parse_identity_snapshot(body)
    state, warnings = validate_fetched_identity(
        candidate, page_title=snap.title, structured_name=snap.structured_name,
        structured_address=snap.structured_address, fetch_ok=True, fetch_reason="",
        registrable_domain_value="example.com")
    assert state != C.WEBSITE_RES_PROPERTY_URL_CONFIRMED
    assert state != C.WEBSITE_RES_PROPERTY_URL_PROBABLE


def test_chain_homepage_with_no_location_identity():
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test Hotel",
                                   normalized_name="test hotel", address_line="1 Main St",
                                   city="Columbus", state="OH")
    state, warnings = validate_fetched_identity(
        candidate, page_title="Marriott Hotels & Resorts", structured_name="",
        structured_address="", fetch_ok=True, fetch_reason="",
        registrable_domain_value="marriott.com")
    assert state == C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY


def test_unrecognized_domain_with_exact_address_still_confirmed():
    # Any independent/unrecognized domain carrying exact property identity
    # is accepted as confirmed.
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test Hotel",
                                   normalized_name="test hotel", address_line="1 Main St",
                                   city="Columbus", state="OH")
    body = _hotel_page("Test Hotel", "1 Main St", "Columbus", "OH")
    snap = parse_identity_snapshot(body)
    state, warnings = validate_fetched_identity(
        candidate, page_title=snap.title, structured_name=snap.structured_name,
        structured_address=snap.structured_address, fetch_ok=True, fetch_reason="",
        registrable_domain_value="somemanagementgroup.com")
    assert state == C.WEBSITE_RES_PROPERTY_URL_CONFIRMED


def test_known_management_company_domain_with_exact_address_gets_management_provenance():
    # A KNOWN property-management platform (e.g. oyorooms.com, found live
    # during Wave 1 resolution) that DOES carry exact property identity is
    # accepted, but tagged MANAGEMENT_COMPANY_PAGE rather than CONFIRMED so
    # the different provenance is never lost (Task 8).
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test Hotel",
                                   normalized_name="test hotel", address_line="1 Main St",
                                   city="Columbus", state="OH")
    body = _hotel_page("Test Hotel", "1 Main St", "Columbus", "OH")
    snap = parse_identity_snapshot(body)
    state, warnings = validate_fetched_identity(
        candidate, page_title=snap.title, structured_name=snap.structured_name,
        structured_address=snap.structured_address, fetch_ok=True, fetch_reason="",
        registrable_domain_value="oyorooms.com")
    assert state == C.WEBSITE_RES_MANAGEMENT_COMPANY_PAGE


def test_blocked_or_timeout_result_fetch_blocked():
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test Hotel")
    state, warnings = validate_fetched_identity(
        candidate, page_title="", structured_name="", structured_address="",
        fetch_ok=False, fetch_reason="fetch_timeout", registrable_domain_value="example.com")
    assert state == C.WEBSITE_RES_FETCH_BLOCKED
    assert "fetch_timeout" in warnings


def test_title_only_weak_match_stays_conservative_not_confirmed():
    candidate = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test Hotel",
                                   normalized_name="test hotel", address_line="1 Main St",
                                   city="Columbus", state="OH")
    # Title matches but no structured address confirmation -- must not
    # jump to CONFIRMED on a title-only weak signal.
    state, warnings = validate_fetched_identity(
        candidate, page_title="Test Hotel", structured_name="", structured_address="",
        fetch_ok=True, fetch_reason="", registrable_domain_value="example.com")
    assert state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE
    assert "weak_identity_signal" in warnings


def test_fetch_for_identity_caches_and_reuses(tmp_path):
    candidate_url = "https://example.com/property"
    body = _hotel_page("Test Hotel", "1 Main St", "Columbus", "OH")
    fetcher = FakeFetcher({candidate_url: FetchResult(
        requested_url=candidate_url, ok=True, final_url=candidate_url, http_status=200,
        content_type="text/html", body=body)})
    cache = ResolutionCache(tmp_path / "cache")
    pacer = DomainPacer(min_seconds=0, sleep_fn=lambda s: None)

    r1 = fetch_for_identity(candidate_url, fetcher=fetcher, cache=cache, pacer=pacer,
                            registrable_domain_value="example.com", retrieved_at="2026-07-18")
    assert r1["ok"] is True
    assert r1["from_cache"] is False
    assert len(fetcher.calls) == 1

    r2 = fetch_for_identity(candidate_url, fetcher=fetcher, cache=cache, pacer=pacer,
                            registrable_domain_value="example.com", retrieved_at="2026-07-18")
    assert r2["from_cache"] is True
    assert len(fetcher.calls) == 1   # no second live call


def test_fetch_for_identity_cache_only_no_entry_returns_blocked(tmp_path):
    fetcher = FakeFetcher({})
    cache = ResolutionCache(tmp_path / "cache")
    result = fetch_for_identity("https://example.com/x", fetcher=fetcher, cache=cache,
                                pacer=None, registrable_domain_value="example.com",
                                retrieved_at="2026-07-18", cache_only=True)
    assert result["ok"] is False
    assert len(fetcher.calls) == 0


def test_domain_pacer_waits_between_same_domain_requests():
    sleeps = []
    pacer = DomainPacer(min_seconds=2.0, sleep_fn=lambda s: sleeps.append(s))
    times = iter([100.0, 100.5])
    pacer._now_fn = lambda: next(times)
    pacer.wait("example.com")
    pacer.wait("example.com")
    assert len(sleeps) == 1
    assert 1.4 < sleeps[0] <= 1.5


def test_domain_pacer_different_domains_no_wait():
    sleeps = []
    pacer = DomainPacer(min_seconds=2.0, sleep_fn=lambda s: sleeps.append(s))
    pacer.wait("example-a.com")
    pacer.wait("example-b.com")
    assert sleeps == []


def test_parse_identity_snapshot_never_raises_on_garbage():
    assert parse_identity_snapshot(b"\xff\xfe not even html") == IdentitySnapshot()
    assert parse_identity_snapshot(b"") == IdentitySnapshot()
