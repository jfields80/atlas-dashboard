"""AES-DATA-004C Task 7 -- website identity fetcher.

Reuses ``scripts.pettripfinder.importer.fetch.RequestsPageFetcher`` as-is
(GET only, SSRF-safe host/port/scheme validation, bounded redirects,
bounded response size, HTML-only content types, explicit timeouts --
already proven in the importer) rather than building a second fetcher.
Importer code is not modified.

Adds only what the importer's fetcher doesn't already provide: per-domain
request pacing, and a compact cache of *parsed identity snapshots* (title,
canonical URL, structured-data name/address) rather than raw page bodies,
under ``data/discovery/columbus_wave1_lodging/resolution_cache/`` -- never
committed, never storing unrelated full-page content when a compact
snapshot suffices (Task 7).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from scripts.pettripfinder.importer.fetch import RequestsPageFetcher
from scripts.pettripfinder.importer.models import FetchResult

_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_CANONICAL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE,
)
_LODGING_TYPES = frozenset({"hotel", "lodgingbusiness", "localbusiness"})


@dataclass(frozen=True)
class IdentitySnapshot:
    title: str = ""
    canonical_url: str = ""
    structured_name: str = ""
    structured_address: str = ""


def _flatten_jsonld(data) -> list:
    if isinstance(data, list):
        out = []
        for item in data:
            out.extend(_flatten_jsonld(item))
        return out
    if isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            out = []
            for item in data["@graph"]:
                out.extend(_flatten_jsonld(item))
            return out
        return [data]
    return []


def parse_identity_snapshot(body: bytes) -> IdentitySnapshot:
    """Pure parsing over raw bytes -- no I/O. Deliberately regex-based
    (not BeautifulSoup) to avoid a new hard dependency for identity
    extraction only; tolerant of malformed HTML by design (best-effort,
    never raises)."""
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return IdentitySnapshot()

    title = ""
    m = _TITLE_RE.search(text)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()

    canonical = ""
    m = _CANONICAL_RE.search(text)
    if m:
        canonical = m.group(1).strip()

    structured_name, structured_address = "", ""
    for block in _JSONLD_RE.findall(text):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        for obj in _flatten_jsonld(data):
            obj_type = str(obj.get("@type", "")).lower()
            if obj_type in _LODGING_TYPES:
                structured_name = obj.get("name", "") or structured_name
                addr = obj.get("address")
                if isinstance(addr, dict):
                    parts = [str(v) for k, v in addr.items() if isinstance(v, str) and k != "@type"]
                    structured_address = " ".join(parts)
                elif isinstance(addr, str):
                    structured_address = addr
                if structured_name:
                    break
        if structured_name:
            break

    return IdentitySnapshot(title=title, canonical_url=canonical,
                            structured_name=structured_name, structured_address=structured_address)


class ResolutionCache:
    """One compact JSON snapshot file per fetched URL -- never the raw
    body, never committed (lives under the gitignored ``data/`` root)."""

    def __init__(self, root: Path):
        self._root = Path(root)

    def _path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self._root / ("%s.json" % digest)

    def get(self, url: str) -> Optional[dict]:
        path = self._path(url)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, url: str, *, fetch_result: FetchResult, snapshot: IdentitySnapshot,
            retrieved_at: str) -> str:
        path = self._path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "url": url, "ok": fetch_result.ok, "final_url": fetch_result.final_url,
            "http_status": fetch_result.http_status, "reason": fetch_result.reason,
            "redirect_chain": list(fetch_result.redirect_chain),
            "title": snapshot.title, "canonical_url": snapshot.canonical_url,
            "structured_name": snapshot.structured_name,
            "structured_address": snapshot.structured_address,
            "retrieved_at": retrieved_at,
        }
        path.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        return str(path)


class DomainPacer:
    """Minimum delay between consecutive requests to the same registrable
    domain within one run (Task 7: per-domain pacing)."""

    def __init__(self, min_seconds: float, sleep_fn=None):
        self._min_seconds = min_seconds
        self._sleep_fn = sleep_fn or time.sleep
        self._last_request_at: Dict[str, float] = {}
        self._now_fn = time.monotonic

    def wait(self, domain: str) -> None:
        last = self._last_request_at.get(domain)
        now = self._now_fn()
        if last is not None:
            elapsed = now - last
            if elapsed < self._min_seconds:
                self._sleep_fn(self._min_seconds - elapsed)
        self._last_request_at[domain] = now


def fetch_for_identity(
    url: str, *, fetcher: RequestsPageFetcher, cache: ResolutionCache,
    pacer: Optional[DomainPacer], registrable_domain_value: str, retrieved_at: str,
    cache_only: bool = False,
) -> Dict:
    """Cache-first. Returns a dict with ``fetch_result`` (or None on cache
    hit -- the raw body is never re-materialized from cache), ``snapshot``,
    ``cache_reference``, and ``from_cache`` bool."""
    cached = cache.get(url)
    if cached is not None:
        snapshot = IdentitySnapshot(
            title=cached.get("title", ""), canonical_url=cached.get("canonical_url", ""),
            structured_name=cached.get("structured_name", ""),
            structured_address=cached.get("structured_address", ""),
        )
        return {
            "ok": cached.get("ok", False), "final_url": cached.get("final_url", ""),
            "http_status": cached.get("http_status", 0), "reason": cached.get("reason", ""),
            "snapshot": snapshot, "cache_reference": str(cache._path(url)), "from_cache": True,
        }
    if cache_only:
        return {
            "ok": False, "final_url": "", "http_status": 0, "reason": "cache_only_no_entry",
            "snapshot": IdentitySnapshot(), "cache_reference": "", "from_cache": False,
        }

    if pacer is not None:
        pacer.wait(registrable_domain_value)
    result = fetcher.fetch(url)
    snapshot = parse_identity_snapshot(result.body) if result.ok else IdentitySnapshot()
    cache_reference = cache.put(url, fetch_result=result, snapshot=snapshot, retrieved_at=retrieved_at)
    return {
        "ok": result.ok, "final_url": result.final_url, "http_status": result.http_status,
        "reason": result.reason, "snapshot": snapshot, "cache_reference": cache_reference,
        "from_cache": False,
    }
