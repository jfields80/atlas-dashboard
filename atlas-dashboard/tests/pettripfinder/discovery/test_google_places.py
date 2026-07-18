"""AES-DATA-004A discovery -- Google Places (New) adapter tests (Task 13).
No network. A ``FakeSession`` stands in for ``requests.Session``."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.cache import DiscoveryCache
from scripts.pettripfinder.discovery.google_places import GooglePlacesClient, parse_page
from scripts.pettripfinder.discovery.market_config import GeoBounds
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery
from scripts.pettripfinder.discovery.query_plan import RequestBudget

_FAKE_KEY = "TEST-ONLY-FAKE-KEY-NEVER-REAL-abc123"


@pytest.fixture(autouse=True)
def _set_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", _FAKE_KEY)


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        """``responses``: list of (status, payload) tuples returned in order,
        or a callable ``fn(call_index, headers, body) -> (status, payload)``."""
        self._responses = responses
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        idx = len(self.calls)
        self.calls.append({"url": url, "headers": headers, "json": json})
        if callable(self._responses):
            status, payload = self._responses(idx, headers, json)
        else:
            status, payload = self._responses[idx]
        return FakeResp(status, payload)


def _query(max_pages=1, query_id="q1", category=C.CATEGORY_VETERINARY):
    return DiscoverySourceQuery(
        query_id=query_id, provider=C.PROVIDER_GOOGLE_PLACES, canonical_category=category,
        query_text="veterinarian in Columbus, OH", market_id="columbus-oh", cell_id="cell1",
        center_lat=39.96, center_lng=-82.99, radius_meters=6000, max_pages=max_pages,
    )


def _place(place_id="p1", name="Test Vet Clinic", lat=39.96, lng=-82.99,
           website="https://testvet.example.com", phone="(614) 555-0100",
           status="OPERATIONAL", city="Columbus", state="OH"):
    components = []
    if city:
        components.append({"longText": city, "types": ["locality"]})
    if state:
        components.append({"shortText": state, "types": ["administrative_area_level_1"]})
    return {
        "id": place_id, "displayName": {"text": name},
        "formattedAddress": "123 Main St, %s, %s 43215" % (city, state),
        "addressComponents": components,
        "location": {"latitude": lat, "longitude": lng},
        "primaryType": "veterinary_care", "types": ["veterinary_care", "point_of_interest"],
        "nationalPhoneNumber": phone, "websiteUri": website, "businessStatus": status,
    }


def _page(places):
    return {"places": places}


def test_1_successful_one_page_response(tmp_path):
    session = FakeSession([(200, _page([_place()]))])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(2), observed_at="2026-07-18")
    assert result.state == C.QUERY_STATE_COMPLETED
    assert result.requests_made == 1
    assert len(result.records) == 1
    assert result.records[0].provider_record_id == "p1"


def test_2_pagination_token_handling(tmp_path):
    page1 = _page([_place("p1")])
    page1["nextPageToken"] = "TOKEN123"
    page2 = _page([_place("p2")])
    session = FakeSession([(200, page1), (200, page2)])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(max_pages=2), cache=cache, budget=RequestBudget(5),
                               observed_at="2026-07-18")
    assert result.requests_made == 2
    assert result.pages_fetched == 2
    assert {r.provider_record_id for r in result.records} == {"p1", "p2"}
    # second request must carry the pageToken from page 1
    assert session.calls[1]["json"]["pageToken"] == "TOKEN123"


def test_3_page_cap_enforced_despite_more_available(tmp_path):
    page1 = _page([_place("p1")])
    page1["nextPageToken"] = "TOKEN123"     # more pages exist...
    session = FakeSession([(200, page1)])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(max_pages=1), cache=cache, budget=RequestBudget(5),
                               observed_at="2026-07-18")
    assert result.requests_made == 1        # ...but max_pages=1 stops here
    assert len(session.calls) == 1


def test_4_field_parsing(tmp_path):
    session = FakeSession([(200, _page([_place(website="https://x.example.com", phone="614-555-0199")]))])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(2), observed_at="2026-07-18")
    rec = result.records[0]
    assert rec.name == "Test Vet Clinic"
    assert rec.city == "Columbus" and rec.state == "OH"
    assert rec.website_url == "https://x.example.com"
    assert rec.phone == "614-555-0199"
    assert rec.canonical_category == C.CATEGORY_VETERINARY


def test_5_missing_website(tmp_path):
    session = FakeSession([(200, _page([_place(website="")]))])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(2), observed_at="2026-07-18")
    assert result.records[0].website_url == ""


def test_6_closed_status_eligibility(tmp_path):
    session = FakeSession([(200, _page([_place(status="CLOSED_PERMANENTLY")]))])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(2), observed_at="2026-07-18")
    assert result.records[0].eligibility_state == C.ELIGIBILITY_PERMANENTLY_CLOSED


def test_7_invalid_coordinates_out_of_market_bounds(tmp_path):
    # A real-valued but wildly out-of-market coordinate -- the client's own
    # parse never fabricates a rejection; eligibility reflects bounds only
    # when bounds are supplied.
    session = FakeSession([(200, _page([_place(lat=51.5, lng=-0.12)]))])   # London, not Columbus
    client = GooglePlacesClient(session=session)
    bounds = GeoBounds(min_lat=39.8, max_lat=40.2, min_lng=-83.2, max_lng=-82.7)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(2),
                               observed_at="2026-07-18", bounds=bounds)
    assert result.records[0].eligibility_state == C.ELIGIBILITY_OUT_OF_MARKET_BOUNDS


def test_8_auth_failure_sanitized_no_retry(tmp_path):
    session = FakeSession([(401, {})])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert result.state == C.QUERY_STATE_FAILED
    assert result.error == C.PROVIDER_ERROR_AUTH
    assert len(session.calls) == 1     # never retried
    assert _FAKE_KEY not in repr(result)
    assert _FAKE_KEY not in str(result.error)


def test_9_quota_rate_limit_error_not_retried(tmp_path):
    session = FakeSession([(429, {})])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert result.error == C.PROVIDER_ERROR_RATE_LIMITED
    assert len(session.calls) == 1


def test_10_transient_error_retried_then_succeeds(tmp_path):
    session = FakeSession([(503, {}), (200, _page([_place()]))])
    client = GooglePlacesClient(session=session, sleep_fn=lambda s: None)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert result.state == C.QUERY_STATE_COMPLETED
    assert len(session.calls) == 2
    assert result.requests_made == 1     # one logical page, one retry-succeeded request


def test_11_transient_error_exhausts_retries_and_fails(tmp_path):
    session = FakeSession([(503, {}), (503, {}), (503, {})])
    client = GooglePlacesClient(session=session, sleep_fn=lambda s: None)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert result.state == C.QUERY_STATE_FAILED
    assert result.error == C.PROVIDER_ERROR_TRANSIENT
    assert len(session.calls) == C.GOOGLE_MAX_RETRIES + 1


def test_12_no_secret_leakage_in_cache_file(tmp_path):
    session = FakeSession([(200, _page([_place()]))])
    client = GooglePlacesClient(session=session)
    cache_dir = tmp_path / "cache"
    cache = DiscoveryCache(cache_dir)
    client.search(_query(), cache=cache, budget=RequestBudget(2), observed_at="2026-07-18")
    for path in cache_dir.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert _FAKE_KEY not in text
        assert "X-Goog-Api-Key" not in text
        assert "Authorization" not in text


def test_13_header_auth_key_never_in_url(tmp_path):
    session = FakeSession([(200, _page([_place()]))])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        client.search(_query(), cache=cache, budget=RequestBudget(2), observed_at="2026-07-18")
    call = session.calls[0]
    assert _FAKE_KEY not in call["url"]
    assert call["headers"]["X-Goog-Api-Key"] == _FAKE_KEY


def test_14_cache_reuse_avoids_second_network_call(tmp_path):
    session = FakeSession([(200, _page([_place()]))])
    client = GooglePlacesClient(session=session)
    cache = DiscoveryCache(tmp_path / "cache")
    r1 = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    r2 = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert r1.requests_made == 1
    assert r2.requests_made == 0
    assert r2.cache_hits == 1
    assert len(session.calls) == 1


def test_15_missing_credential_skips_without_network(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    session = FakeSession([(200, _page([_place()]))])
    client = GooglePlacesClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert result.state == C.QUERY_STATE_SKIPPED_NO_CREDENTIAL
    assert len(session.calls) == 0


def test_16_budget_exhausted_stops_without_extra_calls(tmp_path):
    page1 = _page([_place("p1")])
    page1["nextPageToken"] = "TOKEN"
    session = FakeSession([(200, page1)])
    client = GooglePlacesClient(session=session)
    budget = RequestBudget(max_requests=1)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(max_pages=3), cache=cache, budget=budget, observed_at="2026-07-18")
    assert budget.used == 1
    assert len(session.calls) == 1
    assert "google_request_budget_exhausted" in result.warnings


def test_17_parse_page_pure_no_network():
    payload = _page([_place("p1"), _place("p2")])
    records, warnings = parse_page(payload, _query(), "2026-07-18")
    assert len(records) == 2
    assert warnings == ()
