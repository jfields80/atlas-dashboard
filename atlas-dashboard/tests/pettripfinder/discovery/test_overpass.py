"""AES-DATA-004A discovery -- Overpass adapter tests (Task 13). No network."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.cache import DiscoveryCache
from scripts.pettripfinder.discovery.market_config import GeoBounds
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery
from scripts.pettripfinder.discovery.overpass import (
    OverpassClient,
    bbox_from_center_radius,
    build_ql,
    parse_elements,
)
from scripts.pettripfinder.discovery.query_plan import RequestBudget


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def post(self, url, data=None, headers=None, timeout=None):
        idx = len(self.calls)
        self.calls.append({"url": url, "data": data, "headers": headers})
        status, payload = self._responses[idx]
        return FakeResp(status, payload)


def _query(query_text="leisure=dog_park", query_id="q1", category=C.CATEGORY_DOG_PARK):
    return DiscoverySourceQuery(
        query_id=query_id, provider=C.PROVIDER_OPENSTREETMAP, canonical_category=category,
        query_text=query_text, market_id="columbus-oh", cell_id="cell1",
        center_lat=39.96, center_lng=-82.99, radius_meters=6000, max_pages=1,
    )


def test_1_node_element():
    payload = {"elements": [{"type": "node", "id": 1, "lat": 39.96, "lon": -82.99,
                             "tags": {"leisure": "dog_park", "name": "Test Park"}}]}
    records, warnings = parse_elements(payload, _query(), "2026-07-18")
    assert len(records) == 1
    assert records[0].provider_record_id == "node/1"
    assert records[0].latitude == 39.96 and records[0].longitude == -82.99
    assert warnings == ()


def test_2_way_centroid():
    payload = {"elements": [{"type": "way", "id": 2, "center": {"lat": 39.97, "lon": -82.98},
                             "tags": {"leisure": "dog_park", "name": "Way Park"}}]}
    records, _ = parse_elements(payload, _query(), "2026-07-18")
    assert records[0].provider_record_id == "way/2"
    assert records[0].latitude == 39.97 and records[0].longitude == -82.98


def test_3_relation_center():
    payload = {"elements": [{"type": "relation", "id": 3, "center": {"lat": 39.90, "lon": -83.00},
                             "tags": {"leisure": "park", "name": "Relation Park"}}]}
    records, _ = parse_elements(payload, _query(query_text="leisure=park", category=C.CATEGORY_PARK), "2026-07-18")
    assert records[0].provider_record_id == "relation/3"


def test_4_missing_tags_no_name():
    payload = {"elements": [{"type": "node", "id": 4, "lat": 39.96, "lon": -82.99, "tags": {}}]}
    records, _ = parse_elements(payload, _query(), "2026-07-18")
    assert records[0].name == ""
    assert records[0].eligibility_state == C.ELIGIBILITY_MISSING_IDENTITY


def test_5_website_contact_fields():
    payload = {"elements": [{"type": "node", "id": 5, "lat": 39.96, "lon": -82.99,
                             "tags": {"name": "Vet Clinic", "amenity": "veterinary",
                                     "website": "https://vet.example.com",
                                     "phone": "+1 614 555 0100"}}]}
    records, _ = parse_elements(payload, _query(query_text="amenity=veterinary", category=C.CATEGORY_VETERINARY), "2026-07-18")
    assert records[0].website_url == "https://vet.example.com"
    assert records[0].phone == "+1 614 555 0100"


def test_5b_contact_prefixed_fields_used_when_bare_absent():
    payload = {"elements": [{"type": "node", "id": 6, "lat": 39.96, "lon": -82.99,
                             "tags": {"name": "Vet Clinic", "contact:website": "https://vet2.example.com",
                                     "contact:phone": "614-555-0199"}}]}
    records, _ = parse_elements(payload, _query(), "2026-07-18")
    assert records[0].website_url == "https://vet2.example.com"
    assert records[0].phone == "614-555-0199"


def test_6_category_mapping_provider_categories():
    payload = {"elements": [{"type": "node", "id": 7, "lat": 39.96, "lon": -82.99,
                             "tags": {"name": "Test", "amenity": "veterinary", "shop": "pet"}}]}
    records, _ = parse_elements(payload, _query(query_text="amenity=veterinary", category=C.CATEGORY_VETERINARY), "2026-07-18")
    assert "amenity=veterinary" in records[0].provider_categories
    assert "shop=pet" in records[0].provider_categories


def test_7_malformed_element_no_coords_survives():
    payload = {"elements": [{"type": "node", "id": 8, "tags": {"name": "No Coords Park"}}]}
    records, _ = parse_elements(payload, _query(), "2026-07-18")
    assert len(records) == 1
    assert records[0].latitude is None and records[0].longitude is None


def test_7b_element_cap_truncates_with_warning():
    elements = [{"type": "node", "id": i, "lat": 39.96, "lon": -82.99, "tags": {"name": "P%d" % i}}
               for i in range(C.MAX_OVERPASS_ELEMENTS_PER_QUERY + 50)]
    records, warnings = parse_elements({"elements": elements}, _query(), "2026-07-18")
    assert len(records) == C.MAX_OVERPASS_ELEMENTS_PER_QUERY
    assert "overpass_element_cap_truncated" in warnings


def test_8_timeout_then_retry_succeeds(monkeypatch):
    import requests

    class TimeoutThenOkSession:
        def __init__(self):
            self.calls = 0

        def post(self, url, data=None, headers=None, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise requests.Timeout()
            return FakeResp(200, {"elements": []})

    client = OverpassClient(session=TimeoutThenOkSession(), sleep_fn=lambda s: None)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert result.state == C.QUERY_STATE_COMPLETED
    assert result.requests_made == 1


def test_9_retries_exhausted_fails():
    session = FakeSession([(504, {}), (504, {})])
    client = OverpassClient(session=session, sleep_fn=lambda s: None)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert result.state == C.QUERY_STATE_FAILED
    assert result.error == C.PROVIDER_ERROR_TRANSIENT
    assert len(session.calls) == C.OVERPASS_MAX_RETRIES + 1


def test_10_rate_limited_not_retried():
    session = FakeSession([(429, {})])
    client = OverpassClient(session=session, sleep_fn=lambda s: None)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        result = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert result.error == C.PROVIDER_ERROR_RATE_LIMITED
    assert len(session.calls) == 1


def test_11_cache_reuse_avoids_second_network_call(tmp_path):
    session = FakeSession([(200, {"elements": []})])
    client = OverpassClient(session=session)
    cache = DiscoveryCache(tmp_path / "cache")
    r1 = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    r2 = client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert r1.requests_made == 1
    assert r2.requests_made == 0 and r2.cache_hits == 1
    assert len(session.calls) == 1


def test_12_bbox_never_planet_scale():
    south, west, north, east = bbox_from_center_radius(39.96, -82.99, 6000)
    assert (north - south) < 0.3       # a 6km-radius bbox is a fraction of a degree
    assert (east - west) < 0.3


def test_13_ql_uses_bbox_and_tag_and_timeout():
    ql = build_ql("amenity=veterinary", bbox_from_center_radius(39.96, -82.99, 6000))
    assert "amenity=veterinary" in ql
    assert "[timeout:%d]" % C.OVERPASS_QL_TIMEOUT_SECONDS in ql
    assert "out center;" in ql


def test_14_user_agent_sent(tmp_path):
    session = FakeSession([(200, {"elements": []})])
    client = OverpassClient(session=session)
    with tempfile.TemporaryDirectory() as tmp:
        cache = DiscoveryCache(Path(tmp))
        client.search(_query(), cache=cache, budget=RequestBudget(5), observed_at="2026-07-18")
    assert session.calls[0]["headers"]["User-Agent"] == C.OVERPASS_USER_AGENT


def test_15_out_of_market_bounds_eligibility():
    payload = {"elements": [{"type": "node", "id": 1, "lat": 51.5, "lon": -0.12,
                             "tags": {"name": "London Park"}}]}
    bounds = GeoBounds(min_lat=39.8, max_lat=40.2, min_lng=-83.2, max_lng=-82.7)
    records, _ = parse_elements(payload, _query(), "2026-07-18", bounds=bounds)
    assert records[0].eligibility_state == C.ELIGIBILITY_OUT_OF_MARKET_BOUNDS


def test_16_attribution_recorded_in_provenance():
    payload = {"elements": [{"type": "node", "id": 1, "lat": 39.96, "lon": -82.99,
                             "tags": {"name": "Test"}}]}
    records, _ = parse_elements(payload, _query(), "2026-07-18")
    assert dict(records[0].provenance)["attribution"] == C.OVERPASS_ATTRIBUTION


def test_17_no_broad_query_bbox_always_present():
    ql = build_ql("leisure=dog_park", bbox_from_center_radius(39.96, -82.99, 6000))
    # every element clause is bbox-scoped -- never a bare tag filter alone.
    assert ql.count("(") >= 3 and all(
        "," in clause for clause in ql.split(";") if "[leisure=dog_park]" in clause
    )
