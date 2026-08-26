"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- the resilient client: failover, the
cache surviving an endpoint change, no duplicate cell fetch, pacing defaults,
and the all-endpoints-down state. No network."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
import requests

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import overpass as OV
from scripts.pettripfinder.discovery import overpass_endpoints as OE
from scripts.pettripfinder.discovery import pacing as PACING
from scripts.pettripfinder.discovery.cache import DiscoveryCache, compute_request_fingerprint
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery
from scripts.pettripfinder.discovery.query_plan import RequestBudget

A_URL = "https://a.example/api/interpreter"
B_URL = "https://b.example/api/interpreter"


def registry(threshold=2, cooldown=900, spacing=0.0):
    return OE.EndpointRegistry.from_document({
        "schema": OE.REGISTRY_SCHEMA,
        "defaults": {"health_check_path": "/api/status", "timeout_seconds": 5,
                     "connect_timeout_seconds": 2, "min_request_spacing_seconds": spacing,
                     "cooldown_seconds": cooldown, "failure_threshold": threshold,
                     "concurrency": 1},
        "endpoints": [{"endpoint_id": "a.example", "base_url": A_URL, "enabled": True},
                      {"endpoint_id": "b.example", "base_url": B_URL, "enabled": True}],
    })


class Clock:
    def __init__(self):
        self.now = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")

    def json(self):
        return self._payload


class Session:
    """Health probes (GET) and queries (POST), scripted per host."""

    def __init__(self, *, probe=None, post=None):
        self.probe_behaviour = probe or {}
        self.post_behaviour = post or {}
        self.gets = []
        self.posts = []

    def _behave(self, table, url):
        host = url.split("//", 1)[-1].split("/", 1)[0]
        behaviour = table[host]
        if callable(behaviour):
            behaviour = behaviour()
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour

    def get(self, url, headers=None, timeout=None):
        self.gets.append(url)
        return self._behave(self.probe_behaviour, url)

    def post(self, url, data=None, headers=None, timeout=None):
        self.posts.append((url, data["data"]))
        return self._behave(self.post_behaviour, url)


def query(n, category=C.CATEGORY_HOTEL):
    return DiscoverySourceQuery(
        query_id="OPENSTREETMAP__%s__m__cell%02d" % (category, n),
        provider=C.PROVIDER_OPENSTREETMAP, canonical_category=category,
        query_text="tourism=hotel", market_id="m", cell_id="cell%02d" % n,
        center_lat=40.0 + n * 0.01, center_lng=-80.0, radius_meters=3000, max_pages=1)


def elements(*ids):
    return {"elements": [{"type": "node", "id": i, "lat": 40.0, "lon": -80.0,
                          "tags": {"tourism": "hotel", "name": "Hotel %d" % i}}
                         for i in ids]}


def client(session, *, clock=None, ledger=None, reg=None):
    return OV.OverpassClient.from_registry(
        reg or registry(), session=session, sleep_fn=lambda s: None,
        ledger_path=ledger, clock=clock or Clock(),
        pacer=PACING.Pacer(sleep_fn=lambda s: None, rand=lambda: 0.0))


class TestCacheKeyIsTheQuestionNotTheServer:
    def test_the_cache_identity_names_no_endpoint(self):
        identity = OV.cache_identity(query(1))
        assert set(identity) == {"ql", "query_version"}
        assert identity["query_version"] == OV.OVERPASS_QUERY_VERSION

    def test_a_cell_cached_from_a_is_a_hit_when_the_run_moves_to_b(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        session_a = Session(probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
                            post={"a.example": FakeResp(200, elements(1))})
        first = client(session_a)
        first.search(query(1), cache=cache, budget=RequestBudget(5), observed_at="2026-08-25")
        assert session_a.posts[0][0] == A_URL

        session_b = Session(probe={"a.example": requests.ReadTimeout(),
                                   "b.example": FakeResp(200, {})},
                            post={"b.example": FakeResp(200, elements(2))})
        second = client(session_b)
        result = second.search(query(1), cache=cache, budget=RequestBudget(5),
                               observed_at="2026-08-25")
        assert result.cache_hits == 1 and result.requests_made == 0
        assert session_b.posts == []                  # never re-asked
        assert [r.provider_record_id for r in result.records] == ["node/1"]

    def test_a_cell_cached_under_the_legacy_endpoint_key_is_still_found(self, tmp_path):
        # Every pre-resilience run keyed its cache on {endpoint, ql}. Those
        # entries must be hits, not re-fetches.
        cache = DiscoveryCache(tmp_path)
        q = query(3)
        legacy = OV.legacy_cache_identity(q, C.OVERPASS_DEFAULT_ENDPOINT)
        cache.put(C.PROVIDER_OPENSTREETMAP, q.market_id, q.query_id,
                  compute_request_fingerprint(legacy), 1, sanitized_request=legacy,
                  payload=elements(9), status_metadata={"http_status": 200},
                  retrieved_at="2026-08-01")
        session = Session(probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
                          post={"a.example": FakeResp(200, elements(99))})
        result = client(session).search(q, cache=cache, budget=RequestBudget(5),
                                        observed_at="2026-08-25")
        assert result.cache_hits == 1 and session.posts == []
        entry, kind = OV.lookup_cached(cache, q, legacy_endpoint_urls=(C.OVERPASS_DEFAULT_ENDPOINT,))
        assert kind == "legacy"
        provenance = OV.entry_provenance(entry)
        assert provenance["endpoint_id"] == "overpass-api.de"
        assert provenance["key_kind"] == "legacy"

    def test_a_changed_query_version_is_a_different_question(self, tmp_path, monkeypatch):
        cache = DiscoveryCache(tmp_path)
        session = Session(probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
                          post={"a.example": FakeResp(200, elements(1))})
        c = client(session)
        c.search(query(1), cache=cache, budget=RequestBudget(5), observed_at="2026-08-25")
        monkeypatch.setattr(OV, "OVERPASS_QUERY_VERSION", "overpass-ql/2")
        c.search(query(1), cache=cache, budget=RequestBudget(5), observed_at="2026-08-25")
        assert len(session.posts) == 2


class TestProvenance:
    def test_every_cached_response_records_the_endpoint_that_answered(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        clock = Clock()
        session = Session(probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
                          post={"a.example": FakeResp(200, elements(1))})
        client(session, clock=clock).search(query(1), cache=cache, budget=RequestBudget(5),
                                            observed_at="2026-08-25")
        entry, kind = OV.lookup_cached(cache, query(1), legacy_endpoint_urls=())
        assert kind == "current"
        meta = entry.status_metadata
        assert meta["endpoint_id"] == "a.example"
        assert meta["endpoint_url"] == A_URL
        assert meta["requested_at"] == clock.now.isoformat()
        assert meta["http_status"] == 200
        assert meta["query_id"] == query(1).query_id
        assert meta["cell_id"] == "cell01"
        assert meta["query_hash"] == entry.request_fingerprint
        assert meta["query_version"] == OV.OVERPASS_QUERY_VERSION
        assert entry.sanitized_request == OV.cache_identity(query(1))


class TestFailover:
    def test_a_query_that_fails_on_a_completes_on_b_and_later_cells_go_straight_to_b(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        session = Session(
            probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
            post={"a.example": requests.ReadTimeout(),
                  "b.example": lambda: FakeResp(200, elements(len(session.posts)))})
        c = client(session, reg=registry(threshold=2))
        r1 = c.search(query(1), cache=cache, budget=RequestBudget(10), observed_at="2026-08-25")
        assert r1.state == C.QUERY_STATE_COMPLETED
        # a: two attempts (threshold 2) then the circuit opened; b answered.
        a_posts = [u for u, _ in session.posts if u == A_URL]
        assert len(a_posts) == 2
        assert c.selector.circuits["a.example"].state == OE.OPEN
        r2 = c.search(query(2), cache=cache, budget=RequestBudget(10), observed_at="2026-08-25")
        assert r2.state == C.QUERY_STATE_COMPLETED
        assert [u for u, _ in session.posts][-1] == B_URL
        assert len([u for u, _ in session.posts if u == A_URL]) == 2   # a not asked again
        stats = c.run_stats()
        assert stats["endpoint_switches"] == 1
        assert stats["timeouts"] == 2 and stats["successes"] == 2
        assert stats["requests_by_endpoint"] == {"a.example": 2, "b.example": 2}

    def test_a_rate_limited_endpoint_goes_into_cooldown_not_back_into_rotation(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        clock = Clock()
        session = Session(
            probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
            post={"a.example": FakeResp(429, {}), "b.example": FakeResp(200, elements(1))})
        c = client(session, clock=clock)
        c.search(query(1), cache=cache, budget=RequestBudget(10), observed_at="2026-08-25")
        circuit = c.selector.circuits["a.example"]
        assert circuit.state == OE.OPEN and circuit.is_cooling_down(clock())
        assert len([u for u, _ in session.posts if u == A_URL]) == 1
        assert c.run_stats()["rate_limits"] == 1

    def test_a_bad_query_is_not_blamed_on_the_endpoint(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        session = Session(
            probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
            post={"a.example": FakeResp(400, {})})
        c = client(session)
        result = c.search(query(1), cache=cache, budget=RequestBudget(10), observed_at="2026-08-25")
        assert result.error == C.PROVIDER_ERROR_INVALID_REQUEST
        assert c.selector.circuits["a.example"].state == OE.CLOSED
        assert not any(u == B_URL for u, _ in session.posts)

    def test_the_budget_is_spent_once_per_query_not_per_attempt(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        session = Session(
            probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
            post={"a.example": requests.ReadTimeout(), "b.example": FakeResp(200, elements(1))})
        budget = RequestBudget(10)
        client(session).search(query(1), cache=cache, budget=budget, observed_at="2026-08-25")
        assert budget.used == 1


class TestAllEndpointsDown:
    def test_a_run_reports_waiting_and_stops_asking(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        clock = Clock()
        session = Session(probe={"a.example": requests.ReadTimeout(),
                                 "b.example": requests.ConnectionError()},
                          post={})
        c = client(session, clock=clock, reg=registry(threshold=2, cooldown=600),
                   ledger=tmp_path / "health.json")
        results = [c.search(query(n), cache=cache, budget=RequestBudget(30),
                            observed_at="2026-08-25") for n in range(1, 23)]
        assert all(r.state == C.QUERY_STATE_FAILED for r in results)
        assert all(r.error == C.PROVIDER_ERROR_UNAVAILABLE for r in results)
        assert all(OV.WARNING_ALL_ENDPOINTS_UNHEALTHY in r.warnings for r in results)
        assert session.posts == []                            # nothing was queried
        # Two sweeps (threshold 2) opened both circuits; then no more probes.
        assert session.gets.count("https://a.example/api/status") == 2
        assert session.gets.count("https://b.example/api/status") == 2
        stats = c.run_stats()
        assert stats["all_endpoints_unhealthy"] is True
        assert stats["earliest_cooldown_expiry"] == (
            clock.now + timedelta(seconds=600)).isoformat()
        assert stats["endpoint_states"]["a.example"]["availability"] == "COOLING_DOWN"
        assert json.loads((tmp_path / "health.json").read_text(encoding="utf-8"))["circuits"][0]["state"] == OE.OPEN

    def test_cached_cells_are_still_served_while_every_endpoint_is_down(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        q = query(1)
        identity = OV.cache_identity(q)
        cache.put(C.PROVIDER_OPENSTREETMAP, q.market_id, q.query_id,
                  compute_request_fingerprint(identity), 1, sanitized_request=identity,
                  payload=elements(5), status_metadata={"http_status": 200},
                  retrieved_at="2026-08-01")
        session = Session(probe={"a.example": requests.ReadTimeout(),
                                 "b.example": requests.ReadTimeout()}, post={})
        result = client(session).search(q, cache=cache, budget=RequestBudget(5),
                                        observed_at="2026-08-25")
        assert result.state == C.QUERY_STATE_COMPLETED and result.cache_hits == 1
        assert session.gets == []                              # no probe needed


class TestPacingDefaults:
    def test_concurrency_is_one(self):
        assert PACING.DEFAULT_CONCURRENCY == 1
        assert OE.EndpointRegistry.load().concurrency == 1

    def test_spacing_backoff_and_jitter_are_gentle_and_bounded(self):
        assert PACING.DEFAULT_MIN_SPACING_SECONDS >= 1.0
        assert PACING.DEFAULT_BACKOFF_BASE_SECONDS >= 1.0
        assert PACING.DEFAULT_BACKOFF_MAX_SECONDS <= 120
        assert PACING.DEFAULT_MAX_ATTEMPTS_PER_ENDPOINT <= 3
        assert PACING.DEFAULT_JITTER_SECONDS > 0

    def test_backoff_is_exponential_with_jitter_and_capped(self):
        pacer = PACING.Pacer(backoff_base_seconds=2, backoff_max_seconds=10,
                             jitter_seconds=1, rand=lambda: 0.5, sleep_fn=lambda s: None)
        assert pacer.backoff_seconds(1) == 2.5
        assert pacer.backoff_seconds(2) == 4.5
        assert pacer.backoff_seconds(3) == 8.5
        assert pacer.backoff_seconds(4) == 10.5    # capped at 10, plus jitter

    def test_spacing_waits_between_consecutive_requests(self):
        now = [100.0]
        slept = []
        pacer = PACING.Pacer(min_spacing_seconds=2.0, jitter_seconds=0,
                             sleep_fn=slept.append, monotonic=lambda: now[0])
        pacer.before_request()
        now[0] += 0.5
        pacer.before_request()
        assert slept == [1.5]
        assert pacer.stats.requests == 2 and pacer.stats.waited_seconds == 1.5

    def test_attempts_per_endpoint_are_bounded(self):
        pacer = PACING.Pacer(max_attempts_per_endpoint=2)
        assert pacer.may_retry(1) is True and pacer.may_retry(2) is False

    def test_the_default_client_uses_the_registry_spacing(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        slept = []
        session = Session(probe={"a.example": FakeResp(200, {}), "b.example": FakeResp(200, {})},
                          post={"a.example": FakeResp(200, elements(1))})
        now = [0.0]
        c = OV.OverpassClient.from_registry(
            registry(spacing=2.0), session=session, clock=Clock(),
            pacer=PACING.Pacer(sleep_fn=slept.append, monotonic=lambda: now[0],
                               rand=lambda: 0.0))
        c.search(query(1), cache=cache, budget=RequestBudget(5), observed_at="2026-08-25")
        c.search(query(2), cache=cache, budget=RequestBudget(5), observed_at="2026-08-25")
        assert slept == [2.0]


class TestLegacyClientUnchanged:
    def test_the_single_endpoint_form_still_retries_once_and_never_fails_over(self):
        # The original bounded retry, on the one endpoint the caller named.
        calls = []

        class S:
            def post(self, url, data=None, headers=None, timeout=None):
                calls.append(url)
                return FakeResp(504, {})

        c = OV.OverpassClient(session=S(), endpoint=A_URL, sleep_fn=lambda s: None)
        assert c.resilient is False
        result = c.search(query(1), cache=DiscoveryCache(__import__("tempfile").mkdtemp()),
                          budget=RequestBudget(5), observed_at="2026-08-25")
        assert result.state == C.QUERY_STATE_FAILED
        assert calls == [A_URL] * (C.OVERPASS_MAX_RETRIES + 1)
