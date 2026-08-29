"""AES-DATA-004A discovery -- orchestration (Task 12 support).

Ties market config + query planning + provider clients + cache +
normalization + deduplication + coverage reporting together. The CLI is a
thin argument-parsing shell around this module; every function here is
independently testable without a shell.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import progress_gate as PG
from scripts.pettripfinder.discovery.cache import DiscoveryCache
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.foursquare import FoursquareClient
from scripts.pettripfinder.discovery.google_places import GooglePlacesClient, api_key_present as google_key_present
from scripts.pettripfinder.discovery.market_config import MarketConfig, load_market_config
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoverySourceQuery
from scripts.pettripfinder.discovery.normalize import normalize_records
from scripts.pettripfinder.discovery.overpass import OverpassClient
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult
from scripts.pettripfinder.discovery.query_plan import (
    RequestBudget,
    build_planner_report,
    plan_queries,
)


@dataclass
class RunConfig:
    market_id: str
    providers: Tuple[str, ...]
    categories: Tuple[str, ...]
    output_root: str
    observed_at: str
    max_pages_per_query: int = C.DEFAULT_MAX_PAGES_PER_QUERY
    max_google_requests: int = C.DEFAULT_MAX_GOOGLE_REQUESTS
    max_overpass_requests: int = C.DEFAULT_MAX_OVERPASS_REQUESTS
    cache_only: bool = False
    resume: bool = False
    # PTF-DISCOVERY-OVERPASS-RESILIENCE-001. An approved-endpoint registry
    # other than the committed default, and a local OSM extract index that
    # answers Overpass cells without a public server at all.
    overpass_registry_path: str = ""
    osm_extract_index: str = ""
    #: PTF-INDIANAPOLIS-HARDENED-RECENSUS-002. One named mirror, recorded, with
    #: no fallback -- for the case that order was written against: the default
    #: public endpoint went dark while other mirrors answered in a second, and
    #: an operator needs to say WHICH one this run may ask. It is checked before
    #: the registry so naming a mirror means exactly that; leaving it empty is
    #: how a run gets the resilient registry instead.
    overpass_endpoint: str = ""
    # PTF-PITTSBURGH-HARDENED-RECENSUS-001. After ``progress_stall_cycles``
    # consecutive resume cycles that completed no cell, live free discovery
    # is refused until a human overrides ONE run.
    override_progress_gate: bool = False
    progress_stall_cycles: int = PG.DEFAULT_STALL_CYCLES


_LEDGER_FILENAME = "query_ledger.json"
OVERPASS_RUN_STATS_FILENAME = "overpass_run_stats.json"


def default_overpass_source(config: "RunConfig"):
    """The OSM source a run uses when the caller injects none.

    A local extract index, when configured, answers every cell for free and
    touches no shared server. Otherwise the resilient client: the approved
    registry, health-checked selection, a circuit per endpoint persisted in the
    run's own health ledger, and gentle pacing. Never one hard-coded endpoint.
    """
    from scripts.pettripfinder.discovery import overpass_endpoints as OE
    if config.overpass_endpoint:
        # An operator naming ONE mirror is a deliberate act and outranks the
        # registry, which is exactly the point of the flag: no hidden fallback
        # to a second server.
        return OverpassClient(endpoint=config.overpass_endpoint)
    if config.osm_extract_index:
        from scripts.pettripfinder.discovery.osm_extract import ExtractIndex, LocalOsmExtractSource
        return LocalOsmExtractSource(ExtractIndex.load(Path(config.osm_extract_index)))
    registry = (OE.EndpointRegistry.load(Path(config.overpass_registry_path))
                if config.overpass_registry_path else OE.EndpointRegistry.load())
    return OverpassClient.from_registry(
        registry, ledger_path=Path(config.output_root) / OE.HEALTH_LEDGER_FILENAME)


def _save_overpass_stats(output_root: str, source) -> Optional[str]:
    """What the OSM source did this run -- requests, failures, switches,
    waits -- beside the query ledger. Only sources that keep stats write one."""
    stats_fn = getattr(source, "run_stats", None)
    if stats_fn is None:
        return None
    import json
    path = Path(output_root) / OVERPASS_RUN_STATS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats_fn(), indent=1) + "\n", encoding="utf-8")
    return path.as_posix()


def _load_ledger(output_root: str) -> dict:
    import json
    path = Path(output_root) / _LEDGER_FILENAME
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_ledger(output_root: str, ledger: dict) -> None:
    import json
    path = Path(output_root) / _LEDGER_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, sort_keys=True, indent=2), encoding="utf-8")


class _ProgressGatedSource:
    """An OSM source behind a closed forward-progress gate: cached cells are
    still served; an uncached cell is reported FAILED with the gate's warning
    and no request is made. Wraps any source with the ``search`` shape."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def search(self, query, *, cache, budget, observed_at, bounds=None):
        result = self._inner.search(query, cache=cache, budget=RequestBudget(max_requests=0),
                                    observed_at=observed_at, bounds=bounds)
        if result.state != C.QUERY_STATE_SKIPPED_CAP_REACHED:
            return result
        return ProviderQueryResult(
            query_id=result.query_id, provider=result.provider,
            state=C.QUERY_STATE_FAILED, error=C.PROVIDER_ERROR_UNAVAILABLE,
            requests_made=0, warnings=(PG.WARNING_PROGRESS_GATE,))


def _overpass_cycle_outcome(results: Sequence[ProviderQueryResult]) -> Tuple[bool, int, int, int]:
    """(attempted live discovery, newly completed cells, requests made,
    cells still not completed) for the Overpass results of one run."""
    osm = [r for r in results if r.provider == C.PROVIDER_OPENSTREETMAP
           and r.state != C.QUERY_STATE_DISABLED]
    uncached = [r for r in osm if r.cache_hits == 0]
    attempted = any(r.requests_made > 0 for r in uncached)
    newly = sum(1 for r in uncached if r.state == C.QUERY_STATE_COMPLETED)
    requests_made = sum(r.requests_made for r in osm)
    remaining = sum(1 for r in osm if r.state != C.QUERY_STATE_COMPLETED)
    return attempted, newly, requests_made, remaining


def build_plan(config: RunConfig, market: Optional[MarketConfig] = None):
    market = market or load_market_config(config.market_id)
    return market, plan_queries(
        market, config.providers, config.categories,
        max_pages_per_query=config.max_pages_per_query)


def dry_run_report(config: RunConfig):
    """Pure planning -- makes no network calls (mission Task 6/12)."""
    market, queries = build_plan(config)
    report = build_planner_report(
        queries, market_id=market.market_id,
        google_key_present=google_key_present(),
        foursquare_key_present=bool(os.environ.get(C.FOURSQUARE_API_KEY_ENV, "").strip()),
        market=market, categories=config.categories,
    )
    return market, queries, report


class _CacheOnlyClient:
    """Wraps a real client (Google or Overpass -- both share the same
    ``search`` shape) but refuses to spend budget, used for
    ``--cache-only`` so a cache miss is a clean skip, never a live call."""

    def __init__(self, inner):
        self._inner = inner

    def search(self, query, *, cache, budget, observed_at, bounds=None):
        frozen_budget = RequestBudget(max_requests=0)
        return self._inner.search(query, cache=cache, budget=frozen_budget,
                                  observed_at=observed_at, bounds=bounds)


def execute_run(
    config: RunConfig,
    *,
    google_client: Optional[GooglePlacesClient] = None,
    overpass_client: Optional[OverpassClient] = None,
    foursquare_client: Optional[FoursquareClient] = None,
    cache: Optional[DiscoveryCache] = None,
) -> Tuple[MarketConfig, Tuple[DiscoverySourceQuery, ...], List[ProviderQueryResult],
          Tuple[DiscoveryCandidate, ...]]:
    market, queries = build_plan(config)
    cache = cache or DiscoveryCache(Path(config.output_root) / C.CACHE_SUBDIR)
    google_client = google_client or GooglePlacesClient()
    overpass_client = overpass_client or default_overpass_source(config)
    foursquare_client = foursquare_client or FoursquareClient()
    if config.cache_only:
        google_client = _CacheOnlyClient(google_client)
        overpass_client = _CacheOnlyClient(overpass_client)

    # The forward-progress gate: N attempting resume cycles that completed no
    # cell close it, and this run makes no live Overpass request unless a
    # human overrides it. Cache-only runs and local-extract runs never ask a
    # public server, so the gate does not apply to them.
    progress_path = Path(config.output_root) / PG.FILENAME
    gate_applies = (C.PROVIDER_OPENSTREETMAP in config.providers
                    and not config.cache_only and not config.osm_extract_index)
    gated = (gate_applies and not config.override_progress_gate
             and PG.is_stalled(PG.load(progress_path), config.progress_stall_cycles))
    if gated:
        overpass_client = _ProgressGatedSource(overpass_client)
        PG.record_gated_run(progress_path)

    google_budget = RequestBudget(max_requests=config.max_google_requests)
    overpass_budget = RequestBudget(max_requests=config.max_overpass_requests)
    # NOTE (bug found and fixed live during AES-DATA-004B Phase 12): resume
    # must NEVER skip a query via the ledger alone -- doing so discarded
    # that query's already-collected records entirely (the ledger only
    # stores a state string, never the records), silently losing real data
    # on every resumed run. The ledger is bookkeeping/reporting only now;
    # every query -- resumed or not -- always goes through the client's own
    # cache-first search() path below, which already returns cached
    # records with zero new live requests when a cache entry exists (proven
    # in AES-DATA-004A's cache-reuse tests). This is the ONLY resume
    # mechanism; there is no separate ledger-skip fast path.
    ledger = _load_ledger(config.output_root) if config.resume else {}

    results: List[ProviderQueryResult] = []
    for query in queries:
        if not query.enabled:
            results.append(ProviderQueryResult(query_id=query.query_id, provider=query.provider,
                                               state=C.QUERY_STATE_DISABLED))
            continue
        if query.provider == C.PROVIDER_GOOGLE_PLACES:
            # No budget pre-check here (bug found and fixed live during
            # Phase 12): GooglePlacesClient.search() already checks cache
            # BEFORE consulting the budget, per query/page -- a redundant
            # cache-blind pre-check at this level would skip a fully-cached
            # query just because the budget happens to be 0, discarding
            # data that costs nothing to reuse. Let the client decide.
            results.append(google_client.search(query, cache=cache, budget=google_budget,
                                                 observed_at=config.observed_at, bounds=market.bounds))
        elif query.provider == C.PROVIDER_OPENSTREETMAP:
            results.append(overpass_client.search(query, cache=cache, budget=overpass_budget,
                                                   observed_at=config.observed_at, bounds=market.bounds))
        elif query.provider == C.PROVIDER_FOURSQUARE:
            results.append(foursquare_client.search(query, cache=cache, budget=None,
                                                     observed_at=config.observed_at))
        else:
            raise ValueError("unknown provider: %r" % query.provider)

    ledger.update({r.query_id: r.state for r in results})
    _save_ledger(config.output_root, ledger)
    inner = getattr(overpass_client, "_inner", overpass_client)
    _save_overpass_stats(config.output_root, inner)
    if gate_applies and not gated:
        attempted, newly, requests_made, remaining = _overpass_cycle_outcome(results)
        if attempted or remaining:
            # A cycle that had cells to ask for counts, whether or not a
            # request got out: an outage that refuses every probe is still
            # a cycle without progress.
            PG.record_cycle(progress_path, newly_completed=newly,
                            requests_made=requests_made, remaining_after=remaining,
                            override=config.override_progress_gate)

    all_records = [r for res in results for r in res.records]
    normalized = normalize_records(tuple(all_records))
    candidates = deduplicate(normalized, market_id=market.market_id)
    return market, queries, results, candidates
