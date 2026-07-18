"""AES-DATA-004A discovery -- Foursquare reserved-seam tests (Task 5)."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.foursquare import (
    FoursquareClient,
    ProviderUnavailable,
    api_key_present,
)
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery


def _query(enabled=False):
    return DiscoverySourceQuery(query_id="q1", provider=C.PROVIDER_FOURSQUARE,
                                canonical_category=C.CATEGORY_VETERINARY, enabled=enabled)


def test_key_absence_reported_without_failing(monkeypatch):
    monkeypatch.delenv(C.FOURSQUARE_API_KEY_ENV, raising=False)
    assert api_key_present() is False


def test_disabled_query_returns_disabled_state():
    client = FoursquareClient()
    result = client.search(_query(enabled=False))
    assert result.state == C.QUERY_STATE_DISABLED


def test_missing_credential_never_raises(monkeypatch):
    monkeypatch.delenv(C.FOURSQUARE_API_KEY_ENV, raising=False)
    client = FoursquareClient()
    result = client.search(_query(enabled=True))
    assert result.state == C.QUERY_STATE_SKIPPED_NO_CREDENTIAL
    assert result.error == C.PROVIDER_ERROR_UNAVAILABLE


def test_credential_present_still_refuses_no_fake_data(monkeypatch):
    monkeypatch.setenv(C.FOURSQUARE_API_KEY_ENV, "fake-key")
    client = FoursquareClient()
    result = client.search(_query(enabled=True))
    assert result.state == C.QUERY_STATE_SKIPPED_NO_CREDENTIAL
    assert result.records == ()


def test_require_available_raises_explicit_error():
    client = FoursquareClient()
    with pytest.raises(ProviderUnavailable):
        client.require_available()


def test_absence_never_blocks_other_providers_at_query_plan_level():
    from scripts.pettripfinder.discovery.market_config import load_market_config
    from scripts.pettripfinder.discovery.query_plan import plan_queries
    m = load_market_config("columbus-oh")
    queries = plan_queries(m, [C.PROVIDER_GOOGLE_PLACES, C.PROVIDER_FOURSQUARE], [C.CATEGORY_VETERINARY])
    google_queries = [q for q in queries if q.provider == C.PROVIDER_GOOGLE_PLACES]
    assert all(q.enabled for q in google_queries)
