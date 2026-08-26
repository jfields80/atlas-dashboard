"""PTF-PITTSBURGH-HARDENED-RECENSUS-001 -- the minimum-forward-progress gate:
N resume cycles that complete no cell stop live free discovery until a human
overrides one run. No network."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import discovery_state as DS
from scripts.pettripfinder.discovery import overpass as OV
from scripts.pettripfinder.discovery import overpass_endpoints as OE
from scripts.pettripfinder.discovery import pacing as PACING
from scripts.pettripfinder.discovery import progress_gate as PG
from scripts.pettripfinder.discovery import runner as RUNNER
from scripts.pettripfinder.discovery.cache import DiscoveryCache
from scripts.pettripfinder.discovery.market_config import GeoBounds, MarketCell, MarketConfig

NOW = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
A_URL = "https://a.example/api/interpreter"
B_URL = "https://b.example/api/interpreter"


def market(cells=2):
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
                     "cooldown_seconds": 900, "failure_threshold": 1, "concurrency": 1},
        "endpoints": [{"endpoint_id": "a.example", "base_url": A_URL},
                      {"endpoint_id": "b.example", "base_url": B_URL}],
    })


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")

    def json(self):
        return self._payload


class Session:
    def __init__(self, *, probe_status=200, post_status=200):
        self.probe_status, self.post_status = probe_status, post_status
        self.gets, self.posts = [], []

    def get(self, url, headers=None, timeout=None):
        self.gets.append(url)
        return FakeResp(self.probe_status, {})

    def post(self, url, data=None, headers=None, timeout=None):
        self.posts.append(url)
        n = len(self.posts)
        return FakeResp(self.post_status, {"elements": [
            {"type": "node", "id": n, "lat": 40.0, "lon": -80.0,
             "tags": {"tourism": "hotel", "name": "Hotel %d" % n}}]})


def client(session):
    return OV.OverpassClient.from_registry(
        registry(), session=session, sleep_fn=lambda s: None, clock=lambda: NOW,
        pacer=PACING.Pacer(sleep_fn=lambda s: None, rand=lambda: 0.0))


def config(root, **overrides):
    values = dict(market_id="testville-xx", providers=(C.PROVIDER_OPENSTREETMAP,),
                  categories=(C.CATEGORY_HOTEL,), output_root=str(root),
                  observed_at="2026-08-26", max_overpass_requests=10, resume=True)
    values.update(overrides)
    return RUNNER.RunConfig(**values)


@pytest.fixture
def tiny_market(monkeypatch):
    monkeypatch.setattr(RUNNER, "load_market_config", lambda market_id: market(2))


class TestTheLedger:
    def test_zero_progress_cycles_accumulate_and_one_completed_cell_clears_them(self, tmp_path):
        path = tmp_path / PG.FILENAME
        for n in range(1, 3):
            doc = PG.record_cycle(path, newly_completed=0, requests_made=2, remaining_after=18,
                                  clock=lambda: NOW)
            assert doc["consecutive_zero_progress_cycles"] == n
            assert PG.status(doc) == PG.PROGRESSING
        doc = PG.record_cycle(path, newly_completed=0, requests_made=0, remaining_after=18,
                              clock=lambda: NOW)
        assert PG.is_stalled(doc) and PG.status(doc) == PG.STALLED
        doc = PG.record_cycle(path, newly_completed=1, requests_made=2, remaining_after=17,
                              override=True, clock=lambda: NOW)
        assert doc["consecutive_zero_progress_cycles"] == 0
        assert doc["attempting_cycles"] == 4 and doc["last_progress_at"] == NOW.isoformat()
        assert doc["cycles"][-1]["override"] is True
        assert PG.status(doc) == PG.PROGRESSING

    def test_a_missing_or_foreign_ledger_reads_as_no_cycles(self, tmp_path):
        assert PG.status(PG.load(tmp_path / "absent.json")) == PG.NO_CYCLES
        (tmp_path / "foreign.json").write_text('{"schema": "other"}', encoding="utf-8")
        assert PG.load(tmp_path / "foreign.json")["attempting_cycles"] == 0

    def test_history_is_bounded_but_the_counters_are_not(self, tmp_path):
        path = tmp_path / PG.FILENAME
        for _ in range(PG.HISTORY_LIMIT + 7):
            doc = PG.record_cycle(path, newly_completed=0, requests_made=0, remaining_after=1,
                                  clock=lambda: NOW)
        assert len(doc["cycles"]) == PG.HISTORY_LIMIT
        assert doc["consecutive_zero_progress_cycles"] == PG.HISTORY_LIMIT + 7

    def test_a_gated_run_is_counted_apart_from_attempting_cycles(self, tmp_path):
        path = tmp_path / PG.FILENAME
        doc = PG.record_gated_run(path, clock=lambda: NOW)
        assert doc["gated_runs"] == 1 and doc["attempting_cycles"] == 0


class TestTheRunnerHonoursTheGate:
    def _cycles_of_outage(self, root, n):
        for _ in range(n):
            session = Session(probe_status=503)
            RUNNER.execute_run(config(root), overpass_client=client(session),
                               cache=DiscoveryCache(root / C.CACHE_SUBDIR))
            assert session.posts == []

    def test_cycles_that_complete_nothing_close_the_gate_and_the_next_run_asks_nothing(
            self, tmp_path, tiny_market):
        root = tmp_path / "run"
        self._cycles_of_outage(root, PG.DEFAULT_STALL_CYCLES)
        progress = PG.load(root / PG.FILENAME)
        assert progress["attempting_cycles"] == PG.DEFAULT_STALL_CYCLES
        assert PG.is_stalled(progress)

        # Now the endpoints are healthy -- and the gate still holds: no probe,
        # no request, every uncached cell FAILED with the gate's warning.
        session = Session()
        _market, _queries, results, _cands = RUNNER.execute_run(
            config(root), overpass_client=client(session),
            cache=DiscoveryCache(root / C.CACHE_SUBDIR))
        assert session.gets == [] and session.posts == []
        assert all(r.state == C.QUERY_STATE_FAILED for r in results)
        assert all(PG.WARNING_PROGRESS_GATE in r.warnings for r in results)
        after = PG.load(root / PG.FILENAME)
        assert after["gated_runs"] == 1
        assert after["attempting_cycles"] == PG.DEFAULT_STALL_CYCLES    # a gated run is not a cycle
        ledger = json.loads((root / "query_ledger.json").read_text(encoding="utf-8"))
        assert set(ledger.values()) == {C.QUERY_STATE_FAILED}

    def test_the_state_document_reads_waiting_while_the_gate_is_closed(self, tmp_path, tiny_market):
        root = tmp_path / "run"
        self._cycles_of_outage(root, PG.DEFAULT_STALL_CYCLES)
        document = DS.build("testville-xx", cache_root=root / C.CACHE_SUBDIR, registry=registry(),
                            health_ledger_path=root / OE.HEALTH_LEDGER_FILENAME,
                            categories=(C.CATEGORY_HOTEL,), market=market(2),
                            clock=lambda: NOW + timedelta(hours=2))
        assert document["state"] == DS.WAITING
        assert document["FORWARD_PROGRESS_STALLED"] is True
        assert document["OVERPASS_ENDPOINTS_AVAILABLE"] == 2     # cooldowns long expired
        assert document["OVERPASS_CELLS_REMAINING"] == 2

    def test_a_human_override_runs_once_and_progress_clears_the_gate(self, tmp_path, tiny_market):
        root = tmp_path / "run"
        self._cycles_of_outage(root, PG.DEFAULT_STALL_CYCLES)
        session = Session()
        _m, _q, results, candidates = RUNNER.execute_run(
            config(root, override_progress_gate=True), overpass_client=client(session),
            cache=DiscoveryCache(root / C.CACHE_SUBDIR))
        assert len(session.posts) == 2
        assert all(r.state == C.QUERY_STATE_COMPLETED for r in results)
        assert len(candidates) == 2
        progress = PG.load(root / PG.FILENAME)
        assert progress["consecutive_zero_progress_cycles"] == 0
        assert progress["cycles"][-1] == {"at": progress["last_cycle_at"],
                                          "newly_completed_cells": 2, "requests_made": 2,
                                          "remaining_after": 0, "override": True}
        # The gate is open again; a plain run makes live requests.
        session = Session()
        RUNNER.execute_run(config(root), overpass_client=client(session),
                           cache=DiscoveryCache(root / C.CACHE_SUBDIR))
        assert session.posts == []                 # every cell is cached now...
        assert PG.load(root / PG.FILENAME)["attempting_cycles"] == 4   # ...and that is no cycle

    def test_cached_cells_are_still_served_behind_a_closed_gate(self, tmp_path, tiny_market):
        root = tmp_path / "run"
        cache = DiscoveryCache(root / C.CACHE_SUBDIR)
        session = Session()
        RUNNER.execute_run(config(root), overpass_client=client(session), cache=cache)
        assert len(session.posts) == 2
        for _ in range(PG.DEFAULT_STALL_CYCLES):
            PG.record_cycle(root / PG.FILENAME, newly_completed=0, requests_made=0,
                            remaining_after=0, clock=lambda: NOW)
        session = Session()
        _m, _q, results, _c = RUNNER.execute_run(
            config(root), overpass_client=client(session), cache=cache)
        assert session.posts == [] and session.gets == []
        assert all(r.state == C.QUERY_STATE_COMPLETED and r.cache_hits == 1 for r in results)

    def test_cache_only_and_local_extract_runs_never_touch_the_gate(self, tmp_path, tiny_market):
        root = tmp_path / "run"
        for _ in range(PG.DEFAULT_STALL_CYCLES):
            PG.record_cycle(root / PG.FILENAME, newly_completed=0, requests_made=0,
                            remaining_after=2, clock=lambda: NOW)
        session = Session()
        RUNNER.execute_run(config(root, cache_only=True), overpass_client=client(session),
                           cache=DiscoveryCache(root / C.CACHE_SUBDIR))
        assert PG.load(root / PG.FILENAME)["gated_runs"] == 0
        assert RUNNER.RunConfig.__dataclass_fields__["override_progress_gate"].default is False
