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


_LEDGER_FILENAME = "query_ledger.json"


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
    overpass_client = overpass_client or OverpassClient()
    foursquare_client = foursquare_client or FoursquareClient()
    if config.cache_only:
        google_client = _CacheOnlyClient(google_client)
        overpass_client = _CacheOnlyClient(overpass_client)

    google_budget = RequestBudget(max_requests=config.max_google_requests)
    overpass_budget = RequestBudget(max_requests=config.max_overpass_requests)
    ledger = _load_ledger(config.output_root) if config.resume else {}

    results: List[ProviderQueryResult] = []
    for query in queries:
        if not query.enabled:
            results.append(ProviderQueryResult(query_id=query.query_id, provider=query.provider,
                                               state=C.QUERY_STATE_DISABLED))
            continue
        if config.resume and ledger.get(query.query_id) == C.QUERY_STATE_COMPLETED:
            # Already completed in a prior run against this output_root --
            # skip without even touching the cache (that is the point of
            # --resume: avoid redoing known-finished work).
            results.append(ProviderQueryResult(query_id=query.query_id, provider=query.provider,
                                               state=C.QUERY_STATE_COMPLETED,
                                               warnings=("resumed_from_ledger",)))
            continue
        if query.provider == C.PROVIDER_GOOGLE_PLACES:
            if not google_budget.can_spend(1):
                results.append(ProviderQueryResult(query_id=query.query_id, provider=query.provider,
                                                   state=C.QUERY_STATE_SKIPPED_CAP_REACHED))
                continue
            results.append(google_client.search(query, cache=cache, budget=google_budget,
                                                 observed_at=config.observed_at, bounds=market.bounds))
        elif query.provider == C.PROVIDER_OPENSTREETMAP:
            if not overpass_budget.can_spend(1):
                results.append(ProviderQueryResult(query_id=query.query_id, provider=query.provider,
                                                   state=C.QUERY_STATE_SKIPPED_CAP_REACHED))
                continue
            results.append(overpass_client.search(query, cache=cache, budget=overpass_budget,
                                                   observed_at=config.observed_at, bounds=market.bounds))
        elif query.provider == C.PROVIDER_FOURSQUARE:
            results.append(foursquare_client.search(query, cache=cache, budget=None,
                                                     observed_at=config.observed_at))
        else:
            raise ValueError("unknown provider: %r" % query.provider)

    ledger.update({r.query_id: r.state for r in results})
    _save_ledger(config.output_root, ledger)

    all_records = [r for res in results for r in res.records]
    normalized = normalize_records(tuple(all_records))
    candidates = deduplicate(normalized, market_id=market.market_id)
    return market, queries, results, candidates
