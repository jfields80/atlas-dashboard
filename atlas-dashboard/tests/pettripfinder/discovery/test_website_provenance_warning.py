"""AES-DATA-004B Phase 5 -- website readiness review: ``location_page_unverified``
disclosure. Syntax/domain classification only; no live fetch anywhere.
"""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_records


def rec(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="id1",
               canonical_category=C.CATEGORY_HOTEL, name="Test Hotel")
    base.update(kw)
    return DiscoveryRecord(**base)


def test_official_website_present_gets_unverified_warning():
    a = rec(website_url="https://www.hyatt.com/hyatt-regency/columbus")
    cands = deduplicate(normalize_records((a,)), market_id="columbus-oh")
    assert cands[0].website_state == C.WEBSITE_STATE_OFFICIAL_PRESENT
    assert C.WARNING_LOCATION_PAGE_UNVERIFIED in cands[0].warnings


def test_missing_website_never_discards_the_candidate():
    a = rec(name="No Website Roadside Motel", website_url="")
    cands = deduplicate(normalize_records((a,)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].website_state == C.WEBSITE_STATE_MISSING
    assert cands[0].warnings == ()


def test_provider_url_only_does_not_get_unverified_warning():
    # Not a resolved official website at all -- a different, already-honest
    # state; the "unverified LOCATION page" warning is specific to the
    # OFFICIAL_WEBSITE_PRESENT case, not restated redundantly here.
    a = rec(name="Directory Listed Motel", website_url="https://www.facebook.com/somemotel")
    cands = deduplicate(normalize_records((a,)), market_id="columbus-oh")
    assert cands[0].website_state == C.WEBSITE_STATE_PROVIDER_URL_ONLY
    assert cands[0].warnings == ()


def test_conflicting_websites_does_not_get_unverified_warning():
    # Same address triggers the merge (SAME_ADDRESS); the two providers then
    # disagree on domain, producing CONFLICTING_WEBSITES on the ONE merged
    # candidate.
    a = rec(provider_record_id="a1", website_url="https://example-a.com",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1",
           website_url="https://example-b.com",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].website_state == C.WEBSITE_STATE_CONFLICTING
    assert cands[0].warnings == ()


def test_warning_applies_regardless_of_category_not_lodging_only():
    a = rec(canonical_category=C.CATEGORY_VETERINARY, website_url="https://example-vet.com")
    cands = deduplicate(normalize_records((a,)), market_id="columbus-oh")
    assert C.WARNING_LOCATION_PAGE_UNVERIFIED in cands[0].warnings
