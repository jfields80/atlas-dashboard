"""AES-DATA-004A discovery -- content-addressed raw provider-response cache
(Task 7).

Separates cached entries by provider / market / query / request fingerprint
/ page, under an isolated operational root (default ``data/discovery/cache``,
gitignored like ``data/import``). Re-running normalization or report
generation against unchanged cached entries makes zero provider calls.

Never receives or persists API keys, authorization headers, or secret-
bearing URLs -- callers must build a ``sanitized_request`` mapping
themselves with all credentials already stripped; this module has no code
path that reads an environment variable or a ``headers`` dict, so there is
nothing here for a key to leak through.

Google Places entries are stamped with an ``expires_at`` derived from
``constants.GOOGLE_CACHE_RETENTION_DAYS`` and refused on read once expired
(doctrine #17) -- OpenStreetMap/Overpass entries (ODbL, freely cacheable
with attribution) never expire.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from scripts.pettripfinder.discovery import constants as C


def compute_request_fingerprint(sanitized_request: dict) -> str:
    """Deterministic id for a request shape -- canonical (sorted-key, no
    whitespace) JSON, sha256, first 16 hex chars. Two calls with the same
    logical request always fingerprint identically regardless of dict
    insertion order (Task 1 "deterministic after raw responses captured")."""
    canonical = json.dumps(sanitized_request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class CacheEntry:
    provider: str
    market_id: str
    query_id: str
    request_fingerprint: str
    page: int
    sanitized_request: dict
    retrieved_at: str
    response_hash: str
    payload: dict
    status_metadata: dict
    expires_at: str = ""     # "" means never expires (e.g. Overpass/OSM)

    def is_expired(self, as_of: str) -> bool:
        if not self.expires_at:
            return False
        return as_of > self.expires_at


class DiscoveryCache:
    """File-backed cache: one JSON file per (provider, market, query,
    fingerprint, page)."""

    def __init__(self, root: Path):
        self._root = Path(root)

    def _path(self, provider: str, market_id: str, query_id: str,
              request_fingerprint: str, page: int) -> Path:
        return (self._root / provider / market_id / query_id
                / request_fingerprint / ("page_%d.json" % page))

    def get(self, provider: str, market_id: str, query_id: str,
            request_fingerprint: str, page: int, *,
            as_of: str = "") -> Optional[CacheEntry]:
        path = self._path(provider, market_id, query_id, request_fingerprint, page)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = CacheEntry(
            provider=data["provider"], market_id=data["market_id"],
            query_id=data["query_id"],
            request_fingerprint=data["request_fingerprint"], page=data["page"],
            sanitized_request=data["sanitized_request"],
            retrieved_at=data["retrieved_at"], response_hash=data["response_hash"],
            payload=data["payload"], status_metadata=data["status_metadata"],
            expires_at=data.get("expires_at", ""),
        )
        if as_of and entry.is_expired(as_of):
            return None
        return entry

    def put(self, provider: str, market_id: str, query_id: str,
            request_fingerprint: str, page: int, *, sanitized_request: dict,
            payload: dict, status_metadata: dict, retrieved_at: str) -> CacheEntry:
        response_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        expires_at = ""
        if provider == C.PROVIDER_GOOGLE_PLACES:
            expires_at = (
                date.fromisoformat(retrieved_at)
                + timedelta(days=C.GOOGLE_CACHE_RETENTION_DAYS)
            ).isoformat()
        entry = CacheEntry(
            provider=provider, market_id=market_id, query_id=query_id,
            request_fingerprint=request_fingerprint, page=page,
            sanitized_request=sanitized_request, retrieved_at=retrieved_at,
            response_hash=response_hash, payload=payload,
            status_metadata=status_metadata, expires_at=expires_at,
        )
        path = self._path(provider, market_id, query_id, request_fingerprint, page)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({
                "provider": entry.provider, "market_id": entry.market_id,
                "query_id": entry.query_id,
                "request_fingerprint": entry.request_fingerprint,
                "page": entry.page, "sanitized_request": entry.sanitized_request,
                "retrieved_at": entry.retrieved_at,
                "response_hash": entry.response_hash, "payload": entry.payload,
                "status_metadata": entry.status_metadata,
                "expires_at": entry.expires_at,
            }, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        return entry
