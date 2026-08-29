"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- is free discovery finished, waiting, or runnable?

``ptf-discovery-state/1.0`` answers, for one market and offline:

    OVERPASS_CELLS_TOTAL          every Overpass query the plan calls for
    OVERPASS_CELLS_CACHED         those already answered, under the current
                                  cache key OR a legacy endpoint-bearing one
    OVERPASS_CELLS_REMAINING      total minus cached
    OVERPASS_ENDPOINTS_AVAILABLE  approved endpoints that are enabled and not
                                  cooling down
    OVERPASS_FREE_DISCOVERY_EXHAUSTED   remaining == 0

and one state:

    OVERPASS_FREE_DISCOVERY_EXHAUSTED   nothing left to ask
    FREE_DISCOVERY_RUNNABLE             cells remain and an approved endpoint
                                        is available; the factory owes a run
    WAITING_FOR_FREE_DISCOVERY          cells remain and every approved
                                        endpoint is disabled or cooling down;
                                        carries the health states and the
                                        earliest cooldown expiry

Free discovery is never called exhausted while a healthy approved endpoint
exists and uncached cells remain, and a partial census is never built and
called complete: the market-factory census phase reads this document first.

Pittsburgh's shape, as a worked example: 15 cells x 2 lodging categories = 30
queries; 8 cached from endpoint A; A in cooldown, B available -> RUNNABLE with
22 remaining. A and B both in cooldown -> WAITING, 8 cached, 22 remaining.
"""

from __future__ import annotations

import json
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import overpass as OV
from scripts.pettripfinder.discovery import overpass_endpoints as OE
from scripts.pettripfinder.discovery import paid_discovery_fallback as PAID
from scripts.pettripfinder.discovery import progress_gate as PG
from scripts.pettripfinder.discovery.cache import DiscoveryCache
from scripts.pettripfinder.discovery.market_config import MarketConfig, load_market_config
from scripts.pettripfinder.discovery.query_plan import plan_queries

SCHEMA = "ptf-discovery-state/1.0"

EXHAUSTED = "OVERPASS_FREE_DISCOVERY_EXHAUSTED"
RUNNABLE = "FREE_DISCOVERY_RUNNABLE"
WAITING = "WAITING_FOR_FREE_DISCOVERY"
STATES = (EXHAUSTED, RUNNABLE, WAITING)

#: The categories a lodging census asks Overpass for.
LODGING_CATEGORIES = (C.CATEGORY_HOTEL, C.CATEGORY_MOTEL)


def build(market_id: str, *, cache_root: Path,
          registry: Optional[OE.EndpointRegistry] = None,
          health_ledger_path: Optional[Path] = None,
          categories: Sequence[str] = LODGING_CATEGORIES,
          market: Optional[MarketConfig] = None,
          clock: Optional[Callable[[], datetime]] = None,
          google_key_present: bool = False,
          paid_authorization: Optional[Mapping] = None,
          as_of: str = "",
          progress_path: Optional[Path] = None,
          stall_cycles: int = PG.DEFAULT_STALL_CYCLES) -> Dict:
    market = market or load_market_config(market_id)
    registry = registry or OE.EndpointRegistry.load()
    if progress_path is None and health_ledger_path is not None:
        progress_path = Path(health_ledger_path).parent / PG.FILENAME
    selector_kwargs = dict(registry=registry, ledger_path=health_ledger_path)
    if clock is not None:
        selector_kwargs["clock"] = clock
    selector = OE.EndpointSelector(**selector_kwargs)
    cache = DiscoveryCache(Path(cache_root))

    queries = [q for q in plan_queries(market, (C.PROVIDER_OPENSTREETMAP,), tuple(categories))
               if q.provider == C.PROVIDER_OPENSTREETMAP]
    legacy_urls = (C.OVERPASS_DEFAULT_ENDPOINT,) + registry.base_urls()
    cached: List[Dict] = []
    remaining: List[Dict] = []
    for query in queries:
        entry, kind = OV.lookup_cached(cache, query, legacy_endpoint_urls=legacy_urls,
                                       as_of=as_of)
        row = OrderedDict((("query_id", query.query_id), ("cell_id", query.cell_id),
                           ("category", query.canonical_category)))
        if entry is None:
            remaining.append(row)
            continue
        row["cache_key_kind"] = kind
        row["provenance"] = OV.entry_provenance(entry)
        cached.append(row)

    available = selector.available_endpoints()
    domains = selector.available_failure_domains()
    states = selector.states()
    progress = PG.summary(PG.load(progress_path), stall_cycles)
    stalled = progress["status"] == PG.STALLED
    total, n_cached = len(queries), len(cached)
    n_remaining = total - n_cached
    waiting_reason = ""
    if n_remaining == 0:
        state = EXHAUSTED
    elif stalled:
        # Endpoints may look available; the last N attempting cycles say
        # otherwise. Retrying is not progress.
        state = WAITING
        waiting_reason = ("forward progress stalled: %d consecutive resume cycles "
                          "completed no cell (gate closes at %d); a human overrides "
                          "one run with --override-progress-gate"
                          % (progress["consecutive_zero_progress_cycles"],
                             progress["stall_cycles"]))
    elif available:
        state = RUNNABLE
    else:
        state = WAITING
        waiting_reason = "every approved endpoint is disabled or cooling down"

    paid = PAID.availability(google_key_present=google_key_present,
                             remaining_cells=n_remaining)
    authorised: Dict = OrderedDict((("authorised", False), ("error", "")))
    if paid_authorization is not None:
        try:
            authorised = OrderedDict((("authorised", True),
                                      ("authorization", PAID.validate(
                                          paid_authorization, market_id=market_id))))
        except PAID.PaidFallbackError as exc:
            authorised = OrderedDict((("authorised", False), ("error", str(exc))))

    by_endpoint = Counter(r["provenance"]["endpoint_id"] for r in cached)
    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Whether a market's free (Overpass) discovery is exhausted, runnable "
         "or waiting on endpoint health -- derived offline from the plan, the "
         "cache and the approved-endpoint health ledger. Free discovery is "
         "never called exhausted while a healthy approved endpoint exists and "
         "uncached cells remain."),
        ("market_id", market_id),
        ("categories", list(categories)),
        ("state", state),
        ("OVERPASS_ENDPOINTS_TOTAL", len(registry.endpoints)),
        ("OVERPASS_ENDPOINTS_ENABLED", len(registry.enabled_endpoints())),
        ("OVERPASS_ENDPOINTS_AVAILABLE", len(available)),
        ("OVERPASS_FAILURE_DOMAINS_ENABLED", len(registry.enabled_failure_domains())),
        ("OVERPASS_FAILURE_DOMAINS_AVAILABLE", len(domains)),
        ("OVERPASS_CELLS_TOTAL", total),
        ("OVERPASS_CELLS_CACHED", n_cached),
        ("OVERPASS_CELLS_REMAINING", n_remaining),
        ("OVERPASS_FREE_DISCOVERY_EXHAUSTED", n_remaining == 0),
        ("WAITING_FOR_FREE_DISCOVERY", state == WAITING),
        ("FORWARD_PROGRESS_STALLED", stalled),
        ("RESUME_CYCLES_WITHOUT_PROGRESS", progress["consecutive_zero_progress_cycles"]),
        ("waiting_reason", waiting_reason),
        ("forward_progress", progress),
        ("earliest_cooldown_expiry", selector.earliest_cooldown_expiry()),
        ("available_endpoint_ids", [e.endpoint_id for e in available]),
        ("available_failure_domains", list(domains)),
        ("endpoint_health_states", states),
        ("cached_cells_by_endpoint", OrderedDict(sorted(by_endpoint.items()))),
        ("cached_cells", cached),
        ("remaining_cells", remaining),
        ("paid_discovery_fallback", paid),
        ("paid_discovery_authorization", authorised),
        ("health_ledger", Path(health_ledger_path).as_posix() if health_ledger_path else ""),
        ("progress_ledger", Path(progress_path).as_posix() if progress_path else ""),
        ("registry", registry.source),
    ))


def write(document: Mapping, path: Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")
    return path.as_posix()


__all__ = ["SCHEMA", "EXHAUSTED", "RUNNABLE", "WAITING", "STATES",
           "LODGING_CATEGORIES", "build", "write"]
