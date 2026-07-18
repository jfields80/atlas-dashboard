"""AES-DATA-004A discovery -- raw response cache tests (Task 7)."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.cache import DiscoveryCache, compute_request_fingerprint


def test_fingerprint_deterministic_regardless_of_key_order():
    a = compute_request_fingerprint({"b": 2, "a": 1})
    b = compute_request_fingerprint({"a": 1, "b": 2})
    assert a == b


def test_put_then_get_round_trips(tmp_path):
    cache = DiscoveryCache(tmp_path)
    entry = cache.put(C.PROVIDER_OPENSTREETMAP, "columbus-oh", "q1", "fp1", 1,
                      sanitized_request={"ql": "x"}, payload={"elements": []},
                      status_metadata={"http_status": 200}, retrieved_at="2026-07-18")
    got = cache.get(C.PROVIDER_OPENSTREETMAP, "columbus-oh", "q1", "fp1", 1)
    assert got is not None
    assert got.payload == {"elements": []}
    assert got.expires_at == ""   # OSM never expires


def test_google_entries_expire_after_retention_window(tmp_path):
    cache = DiscoveryCache(tmp_path)
    cache.put(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "q1", "fp1", 1,
             sanitized_request={"textQuery": "x"}, payload={"places": []},
             status_metadata={"http_status": 200}, retrieved_at="2026-01-01")
    # Within retention window.
    assert cache.get(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "q1", "fp1", 1,
                     as_of="2026-01-15") is not None
    # Past the retention window -- refused, forcing a fresh live call.
    assert cache.get(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "q1", "fp1", 1,
                     as_of="2026-03-01") is None


def test_miss_returns_none(tmp_path):
    cache = DiscoveryCache(tmp_path)
    assert cache.get(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "nope", "fp", 1) is None


def test_separate_paths_by_provider_market_query_fingerprint_page(tmp_path):
    cache = DiscoveryCache(tmp_path)
    cache.put(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "q1", "fpA", 1,
             sanitized_request={}, payload={"places": [1]},
             status_metadata={}, retrieved_at="2026-07-18")
    cache.put(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "q1", "fpB", 1,
             sanitized_request={}, payload={"places": [2]},
             status_metadata={}, retrieved_at="2026-07-18")
    a = cache.get(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "q1", "fpA", 1)
    b = cache.get(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "q1", "fpB", 1)
    assert a.payload != b.payload


def test_never_persists_secret_looking_keys(tmp_path):
    cache = DiscoveryCache(tmp_path)
    cache.put(C.PROVIDER_GOOGLE_PLACES, "columbus-oh", "q1", "fp1", 1,
             sanitized_request={"textQuery": "vet"}, payload={"places": []},
             status_metadata={"http_status": 200}, retrieved_at="2026-07-18")
    for path in tmp_path.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "X-Goog-Api-Key" not in text
        assert "Authorization" not in text
        assert "api_key" not in text.lower()
