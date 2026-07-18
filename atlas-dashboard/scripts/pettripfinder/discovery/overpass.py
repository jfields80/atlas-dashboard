"""AES-DATA-004A discovery -- OpenStreetMap/Overpass discovery adapter
(Task 4).

No credential required. Queries are single-tag, single-bbox, single-request
(Overpass has no page-token pagination the way Places API New does) --
capped by ``constants.MAX_OVERPASS_ELEMENTS_PER_QUERY`` and a server-side
``[timeout:N]`` QL directive well under the platform default, per the public
instance's documented fair-use guidance
(https://dev.overpass-api.de/overpass-doc/en/preface/commons.html: "less
than 10,000 queries per day and ... less than 1 GB data per day"). A unique
``User-Agent`` is sent on every request, as that guidance requires. Endpoint
is configurable via ``endpoint=`` -- never a hidden fallback to a second
mirror; the caller must explicitly choose to point elsewhere.

Attribution: "© OpenStreetMap contributors (ODbL)" is required wherever
discovered OSM data is displayed (``constants.OVERPASS_ATTRIBUTION``).
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.cache import DiscoveryCache, compute_request_fingerprint
from scripts.pettripfinder.discovery.market_config import GeoBounds
from scripts.pettripfinder.discovery.models import DiscoveryRecord, DiscoverySourceQuery
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult
from scripts.pettripfinder.discovery.query_plan import RequestBudget

_TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})
_METERS_PER_DEGREE_LAT = 111_320.0


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


def _sanitized_request(query: DiscoverySourceQuery, endpoint: str) -> dict:
    bbox = bbox_from_center_radius(query.center_lat, query.center_lng, query.radius_meters)
    return {
        "endpoint": endpoint,
        "ql": build_ql(query.query_text, bbox),
    }


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


class OverpassClient:
    def __init__(self, session=None, endpoint: str = C.OVERPASS_DEFAULT_ENDPOINT, sleep_fn=None):
        self._session = session
        self._endpoint = endpoint
        self._sleep_fn = sleep_fn

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

    def _post(self, ql: str) -> Tuple[bool, dict, dict, str]:
        import requests
        session = self._get_session()
        try:
            resp = session.post(
                self._endpoint, data={"data": ql},
                headers={"User-Agent": C.OVERPASS_USER_AGENT},
                timeout=(C.CONNECT_TIMEOUT_SECONDS, C.OVERPASS_CLIENT_TIMEOUT_SECONDS),
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
        attempt = 0
        while True:
            ok, payload, status_metadata, error = self._post(ql)
            if ok or error not in (C.PROVIDER_ERROR_TIMEOUT, C.PROVIDER_ERROR_TRANSIENT):
                return (ok, payload, status_metadata, error)
            attempt += 1
            if attempt > C.OVERPASS_MAX_RETRIES:
                return (ok, payload, status_metadata, error)
            self._sleep(C.OVERPASS_RETRY_BACKOFF_SECONDS * attempt)

    def search(self, query: DiscoverySourceQuery, *, cache: DiscoveryCache,
               budget: RequestBudget, observed_at: str,
               bounds: Optional[GeoBounds] = None) -> ProviderQueryResult:
        if not query.enabled:
            return ProviderQueryResult(query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                                       state=C.QUERY_STATE_DISABLED)

        sanitized_request = _sanitized_request(query, self._endpoint)
        fingerprint = compute_request_fingerprint(sanitized_request)
        cached = cache.get(C.PROVIDER_OPENSTREETMAP, query.market_id, query.query_id,
                           fingerprint, 1, as_of=observed_at)
        if cached is not None:
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

        ok, payload, status_metadata, error = self._post_with_retry(sanitized_request["ql"])
        budget.spend(1)
        if not ok:
            return ProviderQueryResult(
                query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                state=C.QUERY_STATE_FAILED, error=error, requests_made=1,
            )
        cache.put(C.PROVIDER_OPENSTREETMAP, query.market_id, query.query_id, fingerprint,
                  1, sanitized_request=sanitized_request, payload=payload,
                  status_metadata=status_metadata, retrieved_at=observed_at)
        records, warnings = parse_elements(payload, query, observed_at, bounds)
        return ProviderQueryResult(
            query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
            state=C.QUERY_STATE_COMPLETED, records=records, requests_made=1,
            pages_fetched=1, cache_hits=0, warnings=warnings,
        )
