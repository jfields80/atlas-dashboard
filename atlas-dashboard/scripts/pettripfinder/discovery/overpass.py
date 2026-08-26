"""AES-DATA-004A discovery -- OpenStreetMap/Overpass discovery adapter
(Task 4).

No credential required. Queries are single-tag, single-bbox, single-request
(Overpass has no page-token pagination the way Places API New does) --
capped by ``constants.MAX_OVERPASS_ELEMENTS_PER_QUERY`` and a server-side
``[timeout:N]`` QL directive well under the platform default, per the public
instance's documented fair-use guidance
(https://dev.overpass-api.de/overpass-doc/en/preface/commons.html: "less
than 10,000 queries per day and ... less than 1 GB data per day"). A unique
``User-Agent`` is sent on every request, as that guidance requires.

Attribution: "© OpenStreetMap contributors (ODbL)" is required wherever
discovered OSM data is displayed (``constants.OVERPASS_ATTRIBUTION``).

PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- TWO WAYS TO CONSTRUCT THE CLIENT
-------------------------------------------------------------------------
``OverpassClient(endpoint=...)`` is the original single-endpoint form and it
still behaves exactly as it did: one endpoint, the original bounded retry, no
health probe, no spacing. It exists for callers that deliberately name one
endpoint and for the tests that pin that behaviour.

``OverpassClient.from_registry(...)`` is what discovery runs use by default.
It selects an approved endpoint through ``overpass_endpoints.EndpointSelector``
(health check, circuit breaker, cooldown), paces every request through
``pacing.Pacer`` (concurrency 1, spacing, jittered exponential backoff), and
FAILS OVER to the next healthy approved endpoint when the current one's circuit
opens -- without ever re-asking a cell the cache already holds.

THE CACHE KEY NAMES THE QUESTION, NOT THE SERVER
------------------------------------------------
The original fingerprint was ``{endpoint, ql}``. That made a cached cell from
endpoint A a MISS the moment the run moved to endpoint B, which is precisely
the re-query the work order forbids. The key is now ``{ql, query_version}`` --
the geometry and semantics of the question -- and the endpoint that answered
it is recorded in the entry's ``status_metadata`` as provenance. Cells cached
under the old key are still found: ``_lookup`` falls back to the legacy
fingerprint for every approved endpoint URL, so no market re-buys a cell it
already holds.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import overpass_endpoints as OE
from scripts.pettripfinder.discovery import pacing as PACING
from scripts.pettripfinder.discovery.cache import CacheEntry, DiscoveryCache, compute_request_fingerprint
from scripts.pettripfinder.discovery.market_config import GeoBounds
from scripts.pettripfinder.discovery.models import DiscoveryRecord, DiscoverySourceQuery
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult
from scripts.pettripfinder.discovery.query_plan import RequestBudget

_TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})
_METERS_PER_DEGREE_LAT = 111_320.0

#: Bumped only when the QL a cell is asked with changes MEANING. Part of the
#: cache key, so a semantics change re-asks every cell and a server change asks
#: none of them.
OVERPASS_QUERY_VERSION = "overpass-ql/1"

#: Warning emitted on a query the run could not attempt because every approved
#: endpoint was unhealthy. The discovery-state module turns it into
#: WAITING_FOR_FREE_DISCOVERY.
WARNING_ALL_ENDPOINTS_UNHEALTHY = "all_overpass_endpoints_unhealthy"


def bbox_from_center_radius(lat: float, lng: float, radius_meters: float) -> Tuple[float, float, float, float]:
    """(south, west, north, east) -- a simple equirectangular approximation,
    adequate for a several-km discovery radius (not survey-grade)."""
    dlat = radius_meters / _METERS_PER_DEGREE_LAT
    meters_per_lng_degree = _METERS_PER_DEGREE_LAT * max(0.01, math.cos(math.radians(lat)))
    dlng = radius_meters / meters_per_lng_degree
    return (lat - dlat, lng - dlng, lat + dlat, lng + dlng)


def build_ql(tag_expr: str, bbox: Tuple[float, float, float, float],
             timeout_seconds: int = C.OVERPASS_QL_TIMEOUT_SECONDS) -> str:
    key, _, value = tag_expr.partition("=")
    south, west, north, east = bbox
    bbox_str = "%.6f,%.6f,%.6f,%.6f" % (south, west, north, east)
    filt = "[%s=%s]" % (key, value) if value else "[%s]" % key
    return (
        "[out:json][timeout:%d];"
        "(node%s(%s);way%s(%s);relation%s(%s););"
        "out center;"
    ) % (timeout_seconds, filt, bbox_str, filt, bbox_str, filt, bbox_str)


def query_ql(query: DiscoverySourceQuery) -> str:
    bbox = bbox_from_center_radius(query.center_lat, query.center_lng, query.radius_meters)
    return build_ql(query.query_text, bbox)


def cache_identity(query: DiscoverySourceQuery) -> dict:
    """What the cache key is computed from: the question, never the server.

    market, category and cell are in the QL's bbox and tag and in the query id
    the cache path already carries; ``query_version`` names the semantics.
    """
    return {"ql": query_ql(query), "query_version": OVERPASS_QUERY_VERSION}


def legacy_cache_identity(query: DiscoverySourceQuery, endpoint_url: str) -> dict:
    """The fingerprint material every pre-resilience run wrote: it named the
    endpoint. Kept only so those entries are still FOUND."""
    return {"endpoint": endpoint_url, "ql": query_ql(query)}


def _sanitized_request(query: DiscoverySourceQuery, endpoint: str) -> dict:
    """Backward-compatible name; returns the LEGACY shape (endpoint-bearing)."""
    return legacy_cache_identity(query, endpoint)


def _tag_value(tags: dict, *keys: str) -> str:
    for key in keys:
        val = tags.get(key)
        if val:
            return val
    return ""


def _eligibility_state(name: str, lat: Optional[float], lng: Optional[float],
                        bounds: Optional[GeoBounds]) -> str:
    if not name:
        return C.ELIGIBILITY_MISSING_IDENTITY
    if bounds is not None and lat is not None and lng is not None and not bounds.contains(lat, lng):
        return C.ELIGIBILITY_OUT_OF_MARKET_BOUNDS
    return C.ELIGIBILITY_ELIGIBLE


def parse_elements(payload: dict, query: DiscoverySourceQuery, observed_at: str,
                    bounds: Optional[GeoBounds] = None) -> Tuple[Tuple[DiscoveryRecord, ...], Tuple[str, ...]]:
    """Deterministic parse of an Overpass ``out center`` response into
    ``DiscoveryRecord``s. Pure -- no I/O. Large geometry is never copied
    into the record -- only the element's own coordinate/centroid."""
    elements = payload.get("elements", ()) or ()
    warnings: List[str] = []
    if len(elements) > C.MAX_OVERPASS_ELEMENTS_PER_QUERY:
        warnings.append("overpass_element_cap_truncated")
        elements = elements[:C.MAX_OVERPASS_ELEMENTS_PER_QUERY]

    records = []
    for el in elements:
        el_type = el.get("type", "")
        el_id = el.get("id", "")
        tags = el.get("tags", {}) or {}
        name = tags.get("name", "") or ""
        if el_type == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lng = center.get("lat"), center.get("lon")
        housenumber = tags.get("addr:housenumber", "")
        street = tags.get("addr:street", "")
        address_line = (housenumber + " " + street).strip() if (housenumber or street) else ""
        provider_categories = tuple(
            "%s=%s" % (k, v) for k, v in sorted(tags.items())
            if k in ("amenity", "shop", "tourism", "leisure", "highway")
        )
        records.append(DiscoveryRecord(
            provider=C.PROVIDER_OPENSTREETMAP,
            provider_record_id="%s/%s" % (el_type, el_id),
            canonical_category=query.canonical_category,
            provider_categories=provider_categories or (query.query_text,),
            name=name,
            address_line=address_line,
            city=tags.get("addr:city", "") or "",
            state=tags.get("addr:state", "") or "",
            postal_code=tags.get("addr:postcode", "") or "",
            latitude=float(lat) if isinstance(lat, (int, float)) else None,
            longitude=float(lng) if isinstance(lng, (int, float)) else None,
            phone=_tag_value(tags, "phone", "contact:phone"),
            website_url=_tag_value(tags, "website", "contact:website"),
            provider_place_url="https://www.openstreetmap.org/%s/%s" % (el_type, el_id) if el_id else "",
            business_status="",
            observed_at=observed_at,
            source_query_id=query.query_id,
            provenance=(
                ("market_id", query.market_id), ("cell_id", query.cell_id),
                ("osm_element_type", el_type), ("osm_element_id", str(el_id)),
                ("attribution", C.OVERPASS_ATTRIBUTION),
            ),
            eligibility_state=_eligibility_state(name, lat, lng, bounds),
        ))
    return tuple(records), tuple(warnings)


# --------------------------------------------------------------------------- #
# Cache lookup that survives an endpoint change
# --------------------------------------------------------------------------- #

def lookup_cached(cache: DiscoveryCache, query: DiscoverySourceQuery, *,
                  legacy_endpoint_urls: Sequence[str], as_of: str = ""
                  ) -> Tuple[Optional[CacheEntry], str]:
    """``(entry, key_kind)`` -- the endpoint-free key first, then every legacy
    endpoint-bearing key. ``key_kind`` is ``"current"``, ``"legacy"`` or ``""``."""
    fingerprint = compute_request_fingerprint(cache_identity(query))
    entry = cache.get(C.PROVIDER_OPENSTREETMAP, query.market_id, query.query_id,
                      fingerprint, 1, as_of=as_of)
    if entry is not None:
        return (entry, "current")
    seen = set()
    for url in legacy_endpoint_urls:
        if not url or url in seen:
            continue
        seen.add(url)
        legacy = compute_request_fingerprint(legacy_cache_identity(query, url))
        entry = cache.get(C.PROVIDER_OPENSTREETMAP, query.market_id, query.query_id,
                          legacy, 1, as_of=as_of)
        if entry is not None:
            return (entry, "legacy")
    return (None, "")


def entry_provenance(entry: CacheEntry) -> Dict:
    """Which endpoint produced a cached cell, for old and new entries alike."""
    meta = entry.status_metadata or {}
    endpoint_url = str(meta.get("endpoint_url") or entry.sanitized_request.get("endpoint") or "")
    endpoint_id = str(meta.get("endpoint_id") or
                      (endpoint_url.split("//", 1)[-1].split("/", 1)[0] if endpoint_url else ""))
    return OrderedDict((
        ("endpoint_id", endpoint_id),
        ("endpoint_url", endpoint_url),
        ("requested_at", str(meta.get("requested_at") or entry.retrieved_at)),
        ("http_status", meta.get("http_status")),
        ("query_id", entry.query_id),
        ("cell_id", str(meta.get("cell_id") or "")),
        ("query_hash", entry.request_fingerprint),
        ("query_version", str(meta.get("query_version") or "legacy")),
        ("key_kind", "current" if meta.get("query_version") else "legacy"),
    ))


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #

class OverpassClient:
    def __init__(self, session=None, endpoint: str = C.OVERPASS_DEFAULT_ENDPOINT,
                 sleep_fn=None, *, selector: Optional[OE.EndpointSelector] = None,
                 pacer: Optional[PACING.Pacer] = None,
                 clock: Optional[Callable[[], datetime]] = None):
        self._session = session
        self._endpoint = endpoint
        self._sleep_fn = sleep_fn
        self._selector = selector
        self._pacer = pacer
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._exhausted = False
        self._exhausted_states: Dict = {}
        self._earliest_cooldown = ""
        self.stats = pacer.stats if pacer is not None else PACING.PacingStats()

    @classmethod
    def from_registry(cls, registry: Optional[OE.EndpointRegistry] = None, *,
                      session=None, sleep_fn=None,
                      ledger_path: Optional[Path] = None,
                      probe=None, clock: Optional[Callable[[], datetime]] = None,
                      pacer: Optional[PACING.Pacer] = None) -> "OverpassClient":
        """The resilient client: approved registry, health-checked selection,
        circuit breaker, cooldown, pacing, failover."""
        registry = registry or OE.EndpointRegistry.load()
        selector_kwargs = dict(registry=registry, ledger_path=ledger_path)
        if probe is not None:
            selector_kwargs["probe"] = probe
        elif session is not None:
            selector_kwargs["probe"] = lambda endpoint: OE.probe_with_requests(endpoint, session)
        if clock is not None:
            selector_kwargs["clock"] = clock
        selector = OE.EndpointSelector(**selector_kwargs)
        pacer = pacer or PACING.Pacer(sleep_fn=sleep_fn)
        return cls(session=session, sleep_fn=sleep_fn, selector=selector,
                   pacer=pacer, clock=clock)

    # -- properties -------------------------------------------------------- #

    @property
    def resilient(self) -> bool:
        return self._selector is not None

    @property
    def selector(self) -> Optional[OE.EndpointSelector]:
        return self._selector

    @property
    def legacy_endpoint_urls(self) -> Tuple[str, ...]:
        urls: List[str] = [C.OVERPASS_DEFAULT_ENDPOINT, self._endpoint]
        if self._selector is not None:
            urls.extend(self._selector.registry.base_urls())
        out: List[str] = []
        for url in urls:
            if url and url not in out:
                out.append(url)
        return tuple(out)

    def run_stats(self) -> Dict:
        document = self.stats.to_dict()
        if self._selector is not None:
            document["endpoint_switches"] = self._selector.switches
            document["current_endpoint_id"] = self._selector.current_id
            document["endpoint_states"] = self._selector.states()
        document["all_endpoints_unhealthy"] = self._exhausted
        document["earliest_cooldown_expiry"] = self._earliest_cooldown
        return document

    # -- plumbing ---------------------------------------------------------- #

    def _get_session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def _sleep(self, seconds: float) -> None:
        if self._sleep_fn is not None:
            self._sleep_fn(seconds)
        else:
            import time
            time.sleep(seconds)

    def _post(self, ql: str, *, endpoint_url: Optional[str] = None,
              timeout: Optional[Tuple[float, float]] = None) -> Tuple[bool, dict, dict, str]:
        import requests
        session = self._get_session()
        url = endpoint_url or self._endpoint
        try:
            resp = session.post(
                url, data={"data": ql},
                headers={"User-Agent": C.OVERPASS_USER_AGENT},
                timeout=timeout or (C.CONNECT_TIMEOUT_SECONDS, C.OVERPASS_CLIENT_TIMEOUT_SECONDS),
            )
        except requests.Timeout:
            return (False, {}, {"error": "timeout"}, C.PROVIDER_ERROR_TIMEOUT)
        except requests.RequestException:
            return (False, {}, {"error": "request_exception"}, C.PROVIDER_ERROR_TRANSIENT)

        status = resp.status_code
        status_metadata = {"http_status": status}
        if status == 429:
            return (False, {}, status_metadata, C.PROVIDER_ERROR_RATE_LIMITED)
        if status == 400:
            return (False, {}, status_metadata, C.PROVIDER_ERROR_INVALID_REQUEST)
        if status in _TRANSIENT_STATUSES:
            return (False, {}, status_metadata, C.PROVIDER_ERROR_TRANSIENT)
        if status < 200 or status >= 300:
            return (False, {}, status_metadata, C.PROVIDER_ERROR_TRANSIENT)
        if len(resp.content) > C.MAX_RESPONSE_BYTES:
            return (False, {}, status_metadata, C.PROVIDER_ERROR_OVERSIZED_RESPONSE)
        try:
            payload = resp.json()
        except ValueError:
            return (False, {}, status_metadata, C.PROVIDER_ERROR_TRANSIENT)
        return (True, payload, status_metadata, "")

    def _post_with_retry(self, ql: str) -> Tuple[bool, dict, dict, str]:
        """The original single-endpoint retry: bounded, transient-only."""
        attempt = 0
        while True:
            ok, payload, status_metadata, error = self._post(ql)
            if ok or error not in (C.PROVIDER_ERROR_TIMEOUT, C.PROVIDER_ERROR_TRANSIENT):
                return (ok, payload, status_metadata, error)
            attempt += 1
            if attempt > C.OVERPASS_MAX_RETRIES:
                return (ok, payload, status_metadata, error)
            self._sleep(C.OVERPASS_RETRY_BACKOFF_SECONDS * attempt)

    def _count(self, error: str, status_metadata: dict) -> None:
        if not error:
            self.stats.successes += 1
        elif error == C.PROVIDER_ERROR_TIMEOUT:
            self.stats.timeouts += 1
        elif error == C.PROVIDER_ERROR_RATE_LIMITED:
            self.stats.rate_limits += 1
        elif (status_metadata.get("http_status") or 0) >= 500:
            self.stats.server_errors += 1
        else:
            self.stats.other_failures += 1

    def _post_resilient(self, ql: str) -> Tuple[bool, dict, dict, str, Optional[OE.EndpointRecord]]:
        """One query through the selector: paced, bounded per endpoint, and
        moved to the next healthy approved endpoint when a circuit opens.

        Returns ``(ok, payload, status_metadata, error, endpoint)``; the
        endpoint is ``None`` only when no approved endpoint was available.
        """
        selector, pacer = self._selector, self._pacer
        endpoints_tried: List[str] = []
        last: Tuple[bool, dict, dict, str] = (False, {}, {"error": "no_endpoint"},
                                             C.PROVIDER_ERROR_UNAVAILABLE)
        # A sweep that finds every endpoint unhealthy is one failure per
        # endpoint. Sweeps are repeated -- with backoff, and bounded by the
        # registry's failure threshold -- so that a real outage OPENS every
        # circuit and leaves a cooldown on disk, rather than a run stopping on
        # one bad probe and the next run rediscovering the same outage.
        sweeps = 0
        max_sweeps = max(e.failure_threshold for e in selector.registry.endpoints)
        while True:
            try:
                endpoint = selector.select()
            except OE.NoHealthyEndpoint as exc:
                sweeps += 1
                if sweeps < max_sweeps and selector.available_endpoints():
                    pacer.backoff(sweeps, why="every approved endpoint unhealthy; re-probing")
                    continue
                self._exhausted = True
                self._exhausted_states = exc.states
                self._earliest_cooldown = exc.earliest_cooldown_expiry
                return (False, {}, {"error": "all_endpoints_unhealthy",
                                    "earliest_cooldown_expiry": exc.earliest_cooldown_expiry},
                        C.PROVIDER_ERROR_UNAVAILABLE, None)
            if endpoint.endpoint_id in endpoints_tried:
                # The selector handed back an endpoint this query already
                # exhausted its attempts on: nothing new to try.
                return last + (endpoint,)
            endpoints_tried.append(endpoint.endpoint_id)
            attempt = 0
            while True:
                attempt += 1
                pacer.before_request(min_spacing_seconds=endpoint.min_request_spacing_seconds)
                self.stats.requests_by_endpoint[endpoint.endpoint_id] = (
                    self.stats.requests_by_endpoint.get(endpoint.endpoint_id, 0) + 1)
                ok, payload, status_metadata, error = self._post(
                    ql, endpoint_url=endpoint.base_url,
                    timeout=(endpoint.connect_timeout_seconds, endpoint.timeout_seconds))
                self._count(error, status_metadata)
                last = (ok, payload, status_metadata, error)
                if ok:
                    selector.record_request_success(endpoint)
                    return (ok, payload, status_metadata, error, endpoint)
                if error in (C.PROVIDER_ERROR_INVALID_REQUEST,
                             C.PROVIDER_ERROR_OVERSIZED_RESPONSE):
                    # The QUERY is wrong, not the server; no endpoint fixes it.
                    return (ok, payload, status_metadata, error, endpoint)
                classification = OE.classify_request_error(
                    error, http_status=status_metadata.get("http_status"))
                opened = selector.record_request_failure(endpoint, classification)
                if opened:
                    self.stats.endpoint_switches = selector.switches + 1
                    break                          # select() again -> next endpoint
                if not pacer.may_retry(attempt):
                    break                          # bounded; move on
                pacer.backoff(attempt, why="retry on %s after %s"
                              % (endpoint.endpoint_id, classification))
            # Fell out of the attempt loop without success: try to select a
            # different endpoint. If the same one comes back (still closed,
            # still healthy on probe) the guard at the top returns.

    # -- search ------------------------------------------------------------ #

    def search(self, query: DiscoverySourceQuery, *, cache: DiscoveryCache,
               budget: RequestBudget, observed_at: str,
               bounds: Optional[GeoBounds] = None) -> ProviderQueryResult:
        if not query.enabled:
            return ProviderQueryResult(query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                                       state=C.QUERY_STATE_DISABLED)

        cached, _kind = lookup_cached(cache, query, as_of=observed_at,
                                      legacy_endpoint_urls=self.legacy_endpoint_urls)
        if cached is not None:
            self.stats.cache_hits += 1
            records, warnings = parse_elements(cached.payload, query, observed_at, bounds)
            return ProviderQueryResult(
                query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                state=C.QUERY_STATE_COMPLETED, records=records, requests_made=0,
                pages_fetched=1, cache_hits=1, warnings=warnings,
            )

        if not budget.can_spend(1):
            return ProviderQueryResult(
                query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                state=C.QUERY_STATE_SKIPPED_CAP_REACHED,
                warnings=("overpass_request_budget_exhausted",),
            )

        if self._selector is not None and self._exhausted:
            # Every approved endpoint was found unhealthy earlier in this run.
            # Asking again for each remaining cell is the loop this module
            # exists to end; the cell is reported, not re-attempted.
            return ProviderQueryResult(
                query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                state=C.QUERY_STATE_FAILED, error=C.PROVIDER_ERROR_UNAVAILABLE,
                requests_made=0, warnings=(WARNING_ALL_ENDPOINTS_UNHEALTHY,),
            )

        ql = query_ql(query)
        identity = cache_identity(query)
        fingerprint = compute_request_fingerprint(identity)
        if self._selector is None:
            ok, payload, status_metadata, error = self._post_with_retry(ql)
            endpoint_id = self._endpoint.split("//", 1)[-1].split("/", 1)[0]
            endpoint_url = self._endpoint
            attempted = True
        else:
            ok, payload, status_metadata, error, endpoint = self._post_resilient(ql)
            attempted = endpoint is not None
            endpoint_id = endpoint.endpoint_id if endpoint else ""
            endpoint_url = endpoint.base_url if endpoint else ""
        if attempted:
            budget.spend(1)
        if not ok:
            warnings = ((WARNING_ALL_ENDPOINTS_UNHEALTHY,)
                        if error == C.PROVIDER_ERROR_UNAVAILABLE and not attempted else ())
            return ProviderQueryResult(
                query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                state=C.QUERY_STATE_FAILED, error=error,
                requests_made=1 if attempted else 0, warnings=warnings,
            )
        provenance = OrderedDict(status_metadata)
        provenance.update(OrderedDict((
            ("endpoint_id", endpoint_id),
            ("endpoint_url", endpoint_url),
            ("requested_at", self._clock().isoformat()),
            ("query_id", query.query_id),
            ("cell_id", query.cell_id),
            ("query_hash", fingerprint),
            ("query_version", OVERPASS_QUERY_VERSION),
        )))
        cache.put(C.PROVIDER_OPENSTREETMAP, query.market_id, query.query_id, fingerprint,
                  1, sanitized_request=identity, payload=payload,
                  status_metadata=dict(provenance), retrieved_at=observed_at)
        records, warnings = parse_elements(payload, query, observed_at, bounds)
        return ProviderQueryResult(
            query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
            state=C.QUERY_STATE_COMPLETED, records=records, requests_made=1,
            pages_fetched=1, cache_hits=0, warnings=warnings,
        )
