"""AES-DATA-004C Task 5 -- static URL classification tests. No network."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord
from scripts.pettripfinder.discovery.website_resolution import (
    classify_candidate_urls_statically,
    classify_url_statically,
    static_conflicting_urls,
)


def test_independent_official_site_probable():
    state, _ = classify_url_statically("https://www.druryhotels.com/locations/columbus-oh/drury-inn-and-suites-columbus-dublin")
    assert state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE


def test_property_specific_brand_path_probable():
    state, _ = classify_url_statically("https://www.marriott.com/en-us/hotels/cmhtd-towneplace-suites-columbus-dublin/overview/")
    assert state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE


def test_chain_homepage_only():
    state, _ = classify_url_statically("https://www.marriott.com/")
    assert state == C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY


def test_brand_locator_search_page():
    state, _ = classify_url_statically("https://www.hilton.com/en/locations/usa/ohio/dublin/pet-friendly/")
    assert state == C.WEBSITE_RES_BRAND_LOCATION_SEARCH_ONLY


def test_management_company_page_not_reachable_statically():
    # MANAGEMENT_COMPANY_PAGE requires fetch-confirmed identity (Task 8) --
    # static classification alone must never guess it.
    state, _ = classify_url_statically("https://www.somemanagementgroup.com/properties/example-hotel")
    assert state != C.WEBSITE_RES_MANAGEMENT_COMPANY_PAGE
    assert state in C.STATIC_REACHABLE_WEBSITE_STATES


def test_booking_com_third_party():
    state, _ = classify_url_statically("https://www.booking.com/hotel/us/example.html")
    assert state == C.WEBSITE_RES_THIRD_PARTY_BOOKING_URL


def test_expedia_third_party():
    state, _ = classify_url_statically("https://www.expedia.com/Columbus-Hotels-Example.h123.Hotel-Information")
    assert state == C.WEBSITE_RES_THIRD_PARTY_BOOKING_URL


def test_hotels_com_third_party():
    state, _ = classify_url_statically("https://www.hotels.com/ho123456/example-hotel-columbus-united-states/")
    assert state == C.WEBSITE_RES_THIRD_PARTY_BOOKING_URL


def test_facebook_social():
    state, _ = classify_url_statically("https://www.facebook.com/somehotel")
    assert state == C.WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL


def test_yelp_social():
    state, _ = classify_url_statically("https://www.yelp.com/biz/some-hotel-columbus")
    assert state == C.WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL


def test_tripadvisor_social():
    state, _ = classify_url_statically("https://www.tripadvisor.com/Hotel_Review-example.html")
    assert state == C.WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL


def test_malformed_url():
    state, warnings = classify_url_statically("not a url at all")
    assert state == C.WEBSITE_RES_UNRESOLVED
    assert "malformed_url" in warnings


def test_missing_url():
    state, _ = classify_url_statically("")
    assert state == C.WEBSITE_RES_MISSING


def test_url_shortener_unresolved():
    state, warnings = classify_url_statically("https://bit.ly/abc123")
    assert state == C.WEBSITE_RES_UNRESOLVED
    assert "url_shortener_unverified" in warnings


def test_never_confirmed_from_path_syntax_alone():
    # Even an obviously property-shaped path never reaches CONFIRMED
    # without a fetch.
    state, _ = classify_url_statically("https://brand.com/hotel/oh/columbus/property-name")
    assert state != C.WEBSITE_RES_PROPERTY_URL_CONFIRMED


def test_conflicting_domains_detected():
    a = _resolution("https://example-a.com/property")
    b = _resolution("https://example-b.com/property")
    assert static_conflicting_urls((a, b)) is True


def test_non_conflicting_same_domain_not_flagged():
    a = _resolution("https://example-a.com/property")
    b = _resolution("https://example-a.com/property?utm=x")
    assert static_conflicting_urls((a, b)) is False


def _resolution(url):
    from scripts.pettripfinder.discovery.website_resolution import classify_url_statically
    from scripts.pettripfinder.discovery.normalize import normalize_url, registrable_domain
    from scripts.pettripfinder.discovery.models import WebsiteResolution
    state, warnings = classify_url_statically(url)
    normalized = normalize_url(url)
    return WebsiteResolution(candidate_id="dc_1", source_provider=C.PROVIDER_GOOGLE_PLACES,
                             original_url=url, normalized_url=normalized,
                             registrable_domain=registrable_domain(normalized),
                             resolution_state=state, warnings=warnings)


def test_classify_candidate_urls_statically_dedupes_identical_urls():
    r1 = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                         canonical_category=C.CATEGORY_HOTEL, name="Test",
                         website_url="https://example.com/property")
    r2 = DiscoveryRecord(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1",
                         canonical_category=C.CATEGORY_HOTEL, name="Test",
                         website_url="https://example.com/property")
    c = DiscoveryCandidate(candidate_id="dc_1", source_records=(r1, r2), name="Test")
    resolutions = classify_candidate_urls_statically(c)
    assert len(resolutions) == 1


def test_classify_candidate_urls_statically_missing_when_none():
    c = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test")
    resolutions = classify_candidate_urls_statically(c)
    assert len(resolutions) == 1
    assert resolutions[0].resolution_state == C.WEBSITE_RES_MISSING
