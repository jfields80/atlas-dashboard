"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- free-discovery exhaustion semantics
and the paid-fallback authorisation contract. Offline."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import discovery_state as DS
from scripts.pettripfinder.discovery import overpass as OV
from scripts.pettripfinder.discovery import overpass_endpoints as OE
from scripts.pettripfinder.discovery import paid_discovery_fallback as PAID
from scripts.pettripfinder.discovery.cache import DiscoveryCache, compute_request_fingerprint
from scripts.pettripfinder.discovery.market_config import GeoBounds, MarketCell, MarketConfig
from scripts.pettripfinder.discovery.query_plan import plan_queries


def market(cells=3):
    return MarketConfig(
        market_id="testville-xx", market_name="Testville", state="XX", country="US",
        center_lat=40.0, center_lng=-80.0,
        bounds=GeoBounds(min_lat=39.0, max_lat=41.0, min_lng=-81.0, max_lng=-79.0),
        included_municipalities=("Testville",),
        cells=tuple(MarketCell(cell_id="testville-xx__c%d" % i, municipality="Testville",
                               label="c%d" % i, center_lat=40.0 + i * 0.05,
                               center_lng=-80.0, radius_meters=3000)
                    for i in range(cells)))


def registry():
    return OE.EndpointRegistry.from_document({
        "schema": OE.REGISTRY_SCHEMA,
        "defaults": {"health_check_path": "/api/status", "timeout_seconds": 5,
                     "connect_timeout_seconds": 2, "min_request_spacing_seconds": 0,
                     "cooldown_seconds": 600, "failure_threshold": 1, "concurrency": 1},
        "endpoints": [{"endpoint_id": "a.example", "base_url": "https://a.example/api/interpreter"},
                      {"endpoint_id": "b.example", "base_url": "https://b.example/api/interpreter"}],
    })


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def cache_cells(cache, queries, *, endpoint_id, legacy_url=None):
    for q in queries:
        if legacy_url:
            identity = OV.legacy_cache_identity(q, legacy_url)
            meta = {"http_status": 200}
        else:
            identity = OV.cache_identity(q)
            meta = {"http_status": 200, "endpoint_id": endpoint_id,
                    "endpoint_url": "https://%s/api/interpreter" % endpoint_id,
                    "query_version": OV.OVERPASS_QUERY_VERSION}
        cache.put(C.PROVIDER_OPENSTREETMAP, q.market_id, q.query_id,
                  compute_request_fingerprint(identity), 1, sanitized_request=identity,
                  payload={"elements": []}, status_metadata=meta, retrieved_at="2026-08-01")


def health_ledger(path, circuits):
    path.write_text(json.dumps({"schema": OE.HEALTH_LEDGER_SCHEMA,
                                "circuits": [c.to_dict() for c in circuits]}),
                    encoding="utf-8")


class TestExhaustion:
    def test_nothing_cached_and_an_endpoint_available_is_runnable(self, tmp_path):
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            market=market(3), clock=lambda: NOW)
        assert document["state"] == DS.RUNNABLE
        assert document["OVERPASS_CELLS_TOTAL"] == 6          # 3 cells x hotel+motel
        assert document["OVERPASS_CELLS_CACHED"] == 0
        assert document["OVERPASS_CELLS_REMAINING"] == 6
        assert document["OVERPASS_FREE_DISCOVERY_EXHAUSTED"] is False
        assert document["OVERPASS_ENDPOINTS_AVAILABLE"] == 2

    def test_every_cell_cached_is_exhausted_whatever_the_endpoints_are_doing(self, tmp_path):
        cache = DiscoveryCache(tmp_path / "cache")
        queries = plan_queries(market(3), (C.PROVIDER_OPENSTREETMAP,), DS.LODGING_CATEGORIES)
        cache_cells(cache, queries, endpoint_id="a.example")
        ledger = tmp_path / "health.json"
        circuit = OE.EndpointCircuit(endpoint_id="a.example", state=OE.OPEN,
                                     cooldown_until=(NOW + timedelta(hours=1)).isoformat())
        health_ledger(ledger, [circuit, OE.EndpointCircuit(endpoint_id="b.example", state=OE.OPEN,
                                                           cooldown_until=(NOW + timedelta(hours=1)).isoformat())])
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            health_ledger_path=ledger, market=market(3), clock=lambda: NOW)
        assert document["state"] == DS.EXHAUSTED
        assert document["OVERPASS_FREE_DISCOVERY_EXHAUSTED"] is True
        assert document["OVERPASS_ENDPOINTS_AVAILABLE"] == 0
        assert document["cached_cells_by_endpoint"] == {"a.example": 6}

    def test_cells_remaining_with_a_healthy_endpoint_is_never_exhausted(self, tmp_path):
        cache = DiscoveryCache(tmp_path / "cache")
        queries = plan_queries(market(3), (C.PROVIDER_OPENSTREETMAP,), DS.LODGING_CATEGORIES)
        cache_cells(cache, queries[:4], endpoint_id="a.example")
        ledger = tmp_path / "health.json"
        health_ledger(ledger, [OE.EndpointCircuit(endpoint_id="a.example", state=OE.OPEN,
                                                  cooldown_until=(NOW + timedelta(hours=1)).isoformat())])
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            health_ledger_path=ledger, market=market(3), clock=lambda: NOW)
        assert document["state"] == DS.RUNNABLE
        assert document["OVERPASS_CELLS_CACHED"] == 4
        assert document["OVERPASS_CELLS_REMAINING"] == 2
        assert document["available_endpoint_ids"] == ["b.example"]
        assert document["OVERPASS_FREE_DISCOVERY_EXHAUSTED"] is False

    def test_all_endpoints_cooling_down_with_cells_remaining_is_waiting(self, tmp_path):
        cache = DiscoveryCache(tmp_path / "cache")
        queries = plan_queries(market(3), (C.PROVIDER_OPENSTREETMAP,), DS.LODGING_CATEGORIES)
        cache_cells(cache, queries[:2], endpoint_id="a.example")
        ledger = tmp_path / "health.json"
        soon = (NOW + timedelta(minutes=5)).isoformat()
        later = (NOW + timedelta(minutes=50)).isoformat()
        health_ledger(ledger, [OE.EndpointCircuit(endpoint_id="a.example", state=OE.OPEN, cooldown_until=later),
                               OE.EndpointCircuit(endpoint_id="b.example", state=OE.OPEN, cooldown_until=soon)])
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            health_ledger_path=ledger, market=market(3), clock=lambda: NOW)
        assert document["state"] == DS.WAITING
        assert document["WAITING_FOR_FREE_DISCOVERY"] is True
        assert document["OVERPASS_CELLS_CACHED"] == 2
        assert document["OVERPASS_CELLS_REMAINING"] == 4
        assert document["earliest_cooldown_expiry"] == soon
        assert set(document["endpoint_health_states"]) == {"a.example", "b.example"}
        assert document["endpoint_health_states"]["b.example"]["availability"] == "COOLING_DOWN"

    def test_a_cooldown_that_has_expired_makes_the_endpoint_available_again(self, tmp_path):
        ledger = tmp_path / "health.json"
        health_ledger(ledger, [OE.EndpointCircuit(endpoint_id="a.example", state=OE.OPEN,
                                                  cooldown_until=(NOW - timedelta(minutes=1)).isoformat()),
                               OE.EndpointCircuit(endpoint_id="b.example", state=OE.OPEN,
                                                  cooldown_until=(NOW + timedelta(hours=1)).isoformat())])
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            health_ledger_path=ledger, market=market(2), clock=lambda: NOW)
        assert document["state"] == DS.RUNNABLE
        assert document["available_endpoint_ids"] == ["a.example"]

    def test_an_expired_cooldown_is_reported_half_open_not_available(self, tmp_path):
        ledger = tmp_path / "health.json"
        health_ledger(ledger, [OE.EndpointCircuit(endpoint_id="a.example", state=OE.OPEN,
                                                  cooldown_until=(NOW - timedelta(minutes=1)).isoformat())])
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            health_ledger_path=ledger, market=market(2), clock=lambda: NOW)
        assert document["endpoint_health_states"]["a.example"]["availability"] == OE.HALF_OPEN
        assert "a.example" in document["available_endpoint_ids"]   # one trial is owed

    def test_stalled_forward_progress_is_waiting_even_with_an_endpoint_available(self, tmp_path):
        # PTF-PITTSBURGH-HARDENED-RECENSUS-001 Q7: endpoints that look
        # available but have answered nothing for N cycles are not runnable.
        from scripts.pettripfinder.discovery import progress_gate as PG
        progress = tmp_path / PG.FILENAME
        for _ in range(PG.DEFAULT_STALL_CYCLES):
            PG.record_cycle(progress, newly_completed=0, requests_made=0, remaining_after=6,
                            clock=lambda: NOW)
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            health_ledger_path=tmp_path / "health.json", market=market(3),
                            clock=lambda: NOW)
        assert document["OVERPASS_ENDPOINTS_AVAILABLE"] == 2
        assert document["state"] == DS.WAITING
        assert document["FORWARD_PROGRESS_STALLED"] is True
        assert document["RESUME_CYCLES_WITHOUT_PROGRESS"] == PG.DEFAULT_STALL_CYCLES
        assert "override-progress-gate" in document["waiting_reason"]
        assert document["forward_progress"]["status"] == PG.STALLED
        assert document["progress_ledger"] == progress.as_posix()

    def test_failure_domains_are_counted_beside_endpoints(self, tmp_path):
        doc = {
            "schema": OE.REGISTRY_SCHEMA,
            "defaults": {"health_check_path": "/api/status", "timeout_seconds": 5,
                         "connect_timeout_seconds": 2, "min_request_spacing_seconds": 0,
                         "cooldown_seconds": 600, "failure_threshold": 1, "concurrency": 1},
            "endpoints": [{"endpoint_id": "a.example", "base_url": "https://a.example/api/interpreter"},
                          {"endpoint_id": "b.example", "base_url": "https://b.example/api/interpreter",
                           "failure_domain": "shared"},
                          {"endpoint_id": "c.example", "base_url": "https://c.example/api/interpreter",
                           "failure_domain": "shared"}],
        }
        reg = OE.EndpointRegistry.from_document(doc)
        ledger = tmp_path / "health.json"
        health_ledger(ledger, [OE.EndpointCircuit(endpoint_id="b.example", state=OE.OPEN,
                                                  cooldown_until=(NOW + timedelta(hours=1)).isoformat())])
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=reg,
                            health_ledger_path=ledger, market=market(2), clock=lambda: NOW)
        assert document["OVERPASS_ENDPOINTS_ENABLED"] == 3
        assert document["OVERPASS_FAILURE_DOMAINS_ENABLED"] == 2
        # c shares b's backend: suppressed with it, so one endpoint and one domain remain.
        assert document["available_endpoint_ids"] == ["a.example"]
        assert document["OVERPASS_FAILURE_DOMAINS_AVAILABLE"] == 1
        assert document["endpoint_health_states"]["c.example"]["availability"] == "COOLING_DOWN_SIBLING"

    def test_legacy_cached_cells_count_and_carry_their_endpoint(self, tmp_path):
        cache = DiscoveryCache(tmp_path / "cache")
        queries = plan_queries(market(2), (C.PROVIDER_OPENSTREETMAP,), DS.LODGING_CATEGORIES)
        cache_cells(cache, queries, endpoint_id="", legacy_url=C.OVERPASS_DEFAULT_ENDPOINT)
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            market=market(2), clock=lambda: NOW)
        assert document["state"] == DS.EXHAUSTED
        assert document["cached_cells_by_endpoint"] == {"overpass-api.de": 4}
        assert all(c["cache_key_kind"] == "legacy" for c in document["cached_cells"])


class TestPaidFallback:
    def test_availability_is_reported_never_acted_on(self, tmp_path):
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            market=market(2), clock=lambda: NOW, google_key_present=True)
        assert document["paid_discovery_fallback"]["state"] == PAID.PAID_DISCOVERY_FALLBACK_AVAILABLE
        assert document["paid_discovery_authorization"]["authorised"] is False

    def test_no_key_means_no_fallback_to_report(self, tmp_path):
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            market=market(2), clock=lambda: NOW, google_key_present=False)
        assert document["paid_discovery_fallback"]["state"] == PAID.PAID_DISCOVERY_FALLBACK_UNAVAILABLE

    def test_an_authorisation_must_name_who_why_how_much_and_the_market(self):
        good = {"schema": PAID.SCHEMA, "market_id": "testville-xx",
                "authorised_by": "jfields80", "why": "Overpass outage exceeded 24h",
                "cost_plan": "launch_packages/pettripfinder/testville_xx_discovery_cost_plan_001.json",
                "max_google_requests": 40}
        assert PAID.validate(good, market_id="testville-xx")["max_google_requests"] == 40
        with pytest.raises(PAID.PaidFallbackError):
            PAID.validate(None, market_id="testville-xx")
        for broken in (dict(good, market_id="other-yy"), dict(good, authorised_by=""),
                       dict(good, why=""), dict(good, cost_plan=""),
                       dict(good, max_google_requests=0), dict(good, schema="x")):
            with pytest.raises(PAID.PaidFallbackError):
                PAID.validate(broken, market_id="testville-xx")

    def test_a_valid_authorisation_is_carried_in_the_state_document(self, tmp_path):
        good = {"schema": PAID.SCHEMA, "market_id": "testville-xx",
                "authorised_by": "jfields80", "why": "outage", "cost_plan": "plan.json",
                "max_google_requests": 10}
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            market=market(2), clock=lambda: NOW, google_key_present=True,
                            paid_authorization=good)
        assert document["paid_discovery_authorization"]["authorised"] is True

    def test_an_invalid_authorisation_is_refused_and_the_reason_recorded(self, tmp_path):
        document = DS.build("testville-xx", cache_root=tmp_path / "cache", registry=registry(),
                            market=market(2), clock=lambda: NOW, google_key_present=True,
                            paid_authorization={"schema": PAID.SCHEMA, "market_id": "testville-xx"})
        assert document["paid_discovery_authorization"]["authorised"] is False
        assert "authorised_by" in document["paid_discovery_authorization"]["error"]

    def test_the_runner_has_no_path_from_overpass_down_to_google(self):
        from pathlib import Path
        from scripts.pettripfinder.discovery import runner
        source = Path(runner.__file__).read_text(encoding="utf-8")
        assert "PAID_DISCOVERY" not in source
        assert "google_budget = RequestBudget(max_requests=config.max_google_requests)" in source
