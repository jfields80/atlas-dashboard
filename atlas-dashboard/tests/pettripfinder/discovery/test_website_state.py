"""AES-DATA-004A discovery -- website readiness classification tests (Task 10)."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.website_state import classify_candidate_website


def rec(website_url=""):
    return DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                           canonical_category=C.CATEGORY_VETERINARY, name="Test",
                           website_url=website_url)


def test_missing_when_no_url_at_all():
    state, url = classify_candidate_website((rec(website_url=""),))
    assert state == C.WEBSITE_STATE_MISSING and url == ""


def test_official_present_single_valid_url():
    state, url = classify_candidate_website((rec(website_url="https://example-vet.com"),))
    assert state == C.WEBSITE_STATE_OFFICIAL_PRESENT
    assert url == "https://example-vet.com"


def test_provider_url_only_social_domain():
    state, url = classify_candidate_website((rec(website_url="https://www.facebook.com/examplevet"),))
    assert state == C.WEBSITE_STATE_PROVIDER_URL_ONLY
    assert "facebook.com" in url


def test_conflicting_websites_different_domains():
    a = rec(website_url="https://example-vet.com")
    b = rec(website_url="https://different-domain.com")
    state, url = classify_candidate_website((a, b))
    assert state == C.WEBSITE_STATE_CONFLICTING
    assert url == ""


def test_same_domain_multiple_providers_still_official_present():
    a = rec(website_url="https://example-vet.com/")
    b = rec(website_url="https://example-vet.com/home")
    state, url = classify_candidate_website((a, b))
    assert state == C.WEBSITE_STATE_OFFICIAL_PRESENT


def test_ambiguous_when_supplied_but_unparseable():
    state, url = classify_candidate_website((rec(website_url="not a real url"),))
    assert state == C.WEBSITE_STATE_AMBIGUOUS
    assert url == ""


def test_empty_records_tuple_is_missing():
    state, url = classify_candidate_website(())
    assert state == C.WEBSITE_STATE_MISSING
