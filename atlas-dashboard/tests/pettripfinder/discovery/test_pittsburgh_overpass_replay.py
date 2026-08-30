"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- the Pittsburgh replay, as a FIXTURE.

Pittsburgh's known state: 15 discovery cells x 2 lodging categories = 30
Overpass queries; 8 safely cached from the primary endpoint (under the old,
endpoint-bearing cache key); the primary began timing out at the TCP layer;
22 remained. This test replays that shape against fakes -- no live Pittsburgh
provider call is made, and nothing under the Pittsburgh market authority is
read or written.

Asserts: only the 22 are requested, the 8 are untouched, no duplicate candidate
is introduced, the merged output covers all 30, and provenance names both
endpoints.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import discovery_state as DS
from scripts.pettripfinder.discovery import overpass as OV
from scripts.pettripfinder.discovery import overpass_endpoints as OE
from scripts.pettripfinder.discovery import pacing as PACING
from scripts.pettripfinder.discovery.cache import DiscoveryCache, compute_request_fingerprint
from scripts.pettripfinder.discovery.runner import RunConfig, build_plan, execute_run

PRIMARY = "overpass-api.de"
SECONDARY = "overpass.kumi.systems"
PRIMARY_URL = "https://overpass-api.de/api/interpreter"
SECONDARY_URL = "https://overpass.kumi.systems/api/interpreter"


def registry():
    return OE.EndpointRegistry.from_document({
        "schema": OE.REGISTRY_SCHEMA,
        "defaults": {"health_check_path": "/api/status", "timeout_seconds": 5,
                     "connect_timeout_seconds": 2, "min_request_spacing_seconds": 2.0,
                     "cooldown_seconds": 900, "failure_threshold": 3, "concurrency": 1},
        "endpoints": [{"endpoint_id": PRIMARY, "base_url": PRIMARY_URL, "enabled": True},
                      {"endpoint_id": SECONDARY, "base_url": SECONDARY_URL, "enabled": True}],
    })


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")

    def json(self):
        return self._payload


class Session:
    """The primary times out at the TCP layer; the secondary answers every
    cell with elements unique to that cell."""

    def __init__(self):
        self.gets = []
        self.posts = []

    def get(self, url, headers=None, timeout=None):
        self.gets.append(url)
        if url.startswith("https://overpass-api.de/"):
            raise requests.ConnectTimeout()
        return FakeResp(200, {})

    def post(self, url, data=None, headers=None, timeout=None):
        self.posts.append((url, data["data"]))
        if url == PRIMARY_URL:
            raise requests.ConnectTimeout()
        seed = int(hashlib.sha256(data["data"].encode("utf-8")).hexdigest()[:6], 16)
        return FakeResp(200, {"elements": [
            {"type": "node", "id": 100000 + seed, "lat": 40.44, "lon": -79.99,
             "tags": {"tourism": "hotel", "name": "Live Hotel %d" % seed}}]})


def _config(root):
    return RunConfig(market_id="pittsburgh-pa", providers=(C.PROVIDER_OPENSTREETMAP,),
                     categories=(C.CATEGORY_HOTEL, C.CATEGORY_MOTEL), output_root=str(root),
                     observed_at="2026-08-25", max_overpass_requests=30)


def _seed_eight_cached_from_primary(cache, queries):
    """Eight cells cached the way the ORIGINAL client cached them: keyed on
    {endpoint, ql}, with distinct elements per cell."""
    seeded = []
    for n, q in enumerate(queries[:8], 1):
        identity = OV.legacy_cache_identity(q, PRIMARY_URL)
        entry = cache.put(C.PROVIDER_OPENSTREETMAP, q.market_id, q.query_id,
                          compute_request_fingerprint(identity), 1,
                          sanitized_request=identity,
                          payload={"elements": [{"type": "node", "id": n, "lat": 40.44,
                                                 "lon": -79.99,
                                                 "tags": {"tourism": "hotel",
                                                          "name": "Cached Hotel %d" % n}}]},
                          status_metadata={"http_status": 200}, retrieved_at="2026-08-20")
        seeded.append((q, entry))
    return seeded


def test_pittsburgh_8_of_30_cached_primary_dead_secondary_healthy(tmp_path):
    root = tmp_path / "pittsburgh_replay"
    cache_root = root / C.CACHE_SUBDIR
    cache = DiscoveryCache(cache_root)
    market, queries = build_plan(_config(root))
    assert len(market.cells) == 15 and len(queries) == 30

    seeded = _seed_eight_cached_from_primary(cache, queries)
    cached_files = {p: p.read_bytes() for p in cache_root.rglob("page_1.json")}
    assert len(cached_files) == 8

    # The state BEFORE the run: 8/30 cached, primary unhealthy in the ledger.
    ledger = root / OE.HEALTH_LEDGER_FILENAME
    before = DS.build("pittsburgh-pa", cache_root=cache_root, registry=registry(),
                      health_ledger_path=ledger, market=market,
                      clock=lambda: datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc))
    assert (before["OVERPASS_CELLS_TOTAL"], before["OVERPASS_CELLS_CACHED"],
            before["OVERPASS_CELLS_REMAINING"]) == (30, 8, 22)
    assert before["state"] == DS.RUNNABLE

    session = Session()
    client = OV.OverpassClient.from_registry(
        registry(), session=session, sleep_fn=lambda s: None, ledger_path=ledger,
        clock=lambda: datetime(2026, 8, 25, 12, 30, tzinfo=timezone.utc),
        pacer=PACING.Pacer(sleep_fn=lambda s: None, rand=lambda: 0.0))
    market, queries, results, candidates = execute_run(
        _config(root), overpass_client=client, cache=cache)

    # Only the 22 remaining cells were requested, all of them on the secondary.
    assert len(session.posts) == 22
    assert {url for url, _ in session.posts} == {SECONDARY_URL}
    asked = {ql for _, ql in session.posts}
    assert asked == {OV.query_ql(q) for q in queries[8:]}
    assert not any(OV.query_ql(q) in asked for q, _ in seeded)

    # The 8 cached cells are byte-for-byte untouched and were served as hits.
    for path, content in cached_files.items():
        assert path.read_bytes() == content
    by_id = {r.query_id: r for r in results}
    for q, _ in seeded:
        assert by_id[q.query_id].cache_hits == 1 and by_id[q.query_id].requests_made == 0

    # Every one of the 30 cells completed; the merged output covers all of them.
    assert all(r.state == C.QUERY_STATE_COMPLETED for r in results)
    assert len(results) == 30
    ledger_doc = json.loads((root / "query_ledger.json").read_text(encoding="utf-8"))
    assert len(ledger_doc) == 30 and set(ledger_doc.values()) == {C.QUERY_STATE_COMPLETED}

    # No duplicate candidate input: 8 cached + 22 live elements, all distinct.
    record_ids = [r.provider_record_id for res in results for r in res.records]
    assert len(record_ids) == len(set(record_ids)) == 30
    assert len(candidates) == 30

    # Provenance names both endpoints: the 8 from the primary (legacy key),
    # the 22 from the secondary (current key).
    after = DS.build("pittsburgh-pa", cache_root=cache_root, registry=registry(),
                     health_ledger_path=ledger, market=market,
                     clock=lambda: datetime(2026, 8, 25, 13, 0, tzinfo=timezone.utc))
    assert after["state"] == DS.EXHAUSTED
    assert after["cached_cells_by_endpoint"] == {PRIMARY: 8, SECONDARY: 22}
    kinds = {c["cache_key_kind"] for c in after["cached_cells"]}
    assert kinds == {"legacy", "current"}
    for cell in after["cached_cells"]:
        assert cell["provenance"]["endpoint_url"] in (PRIMARY_URL, SECONDARY_URL)
        assert cell["provenance"]["requested_at"]

    # The primary was probed, never queried; the run switched once.
    assert session.gets.count("https://overpass-api.de/api/status") >= 1
    assert not any(url == PRIMARY_URL for url, _ in session.posts)
    stats = json.loads((root / "overpass_run_stats.json").read_text(encoding="utf-8"))
    assert stats["requests_by_endpoint"] == {SECONDARY: 22}
    assert stats["cache_hits"] == 8 and stats["successes"] == 22
    assert stats["current_endpoint_id"] == SECONDARY
    assert stats["all_endpoints_unhealthy"] is False


#: The paths the replay must never write to.
_AUTHORITY_PATHS = (
    "launch_packages/pettripfinder/markets/authority/pittsburgh-pa",
    "launch_packages/pettripfinder/identity_census/pittsburgh-pa.json",
    "launch_packages/pettripfinder/markets/pittsburgh-pa.json",
    "deploy/netlify",
)


def _authority_status():
    import subprocess
    out = subprocess.run(["git", "status", "--porcelain", "--", *_AUTHORITY_PATHS],
                         capture_output=True, text=True, check=False).stdout
    return {line[3:].strip() for line in out.splitlines() if line.strip()}


def test_pittsburgh_replay_touches_no_market_authority(tmp_path):
    """The replay runs under tmp_path and writes no committed authority.

    Asserted as a DELTA, not as a clean working tree. An equality-to-empty
    check conflates "the replay wrote to authority" -- the thing this guard
    exists to catch -- with "this checkout has uncommitted work", which is the
    normal state of the market order that is running the suite, and which no
    amount of correctness in the replay can fix (PTF-INDIANAPOLIS-FOUNDER-
    PROMOTION-004 lost time to exactly that conflation).
    """
    before = _authority_status()
    root = tmp_path / "replay"
    market, _queries = build_plan(_config(root))
    DS.build("pittsburgh-pa", cache_root=root / C.CACHE_SUBDIR,
             registry=registry(), health_ledger_path=root / "ledger.json",
             market=market,
             clock=lambda: datetime(2026, 8, 25, 13, 0, tzinfo=timezone.utc))
    assert _authority_status() - before == set()
