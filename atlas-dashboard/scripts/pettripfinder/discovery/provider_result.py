"""AES-DATA-004A discovery -- shared per-query provider execution result.

Returned by every provider client's ``search()`` (Google, Overpass,
Foursquare stub). Kept separate from ``models.py``'s discovery-output
contracts since this describes *execution bookkeeping* (requests made,
cache hits, error slug) rather than discovered business data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from scripts.pettripfinder.discovery.models import DiscoveryRecord


@dataclass(frozen=True)
class ProviderQueryResult:
    query_id: str
    provider: str
    state: str                              # constants.QUERY_STATE_*
    records: Tuple[DiscoveryRecord, ...] = ()
    error: str = ""                          # constants.PROVIDER_ERROR_* or ""
    requests_made: int = 0
    pages_fetched: int = 0
    cache_hits: int = 0
    warnings: Tuple[str, ...] = ()
