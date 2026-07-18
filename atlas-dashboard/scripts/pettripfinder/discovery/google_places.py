"""AES-DATA-004A discovery -- Google Places API (New) discovery adapter
(Task 3).

Endpoint: ``POST https://places.googleapis.com/v1/places:searchText``
(Places API New Text Search), matching the endpoint/auth style already
established in this repo by
``services/opportunity_v2/google_places_business_data_source.py`` and
``services/connectors/google_connector.py``. Auth is header-based
(``X-Goog-Api-Key``) -- the key is never embedded in a URL and never
logged. The key is read from ``GOOGLE_PLACES_API_KEY`` only, at the moment
of the request; nothing in this module prints, hashes, or persists it.

Retries are bounded and transient-only (timeout / connection error / 5xx).
Auth failures (401/403) and invalid requests (400) are never retried.
429 (rate limited) is also never retried in this phase -- treated as a
signal to stop and report, not to hammer through with backoff, since a
public-facing discovery run should never risk compounding a quota problem
(a disclosed, conservative design choice; not a documented API requirement
either way).
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.cache import DiscoveryCache, compute_request_fingerprint
from scripts.pettripfinder.discovery.market_config import GeoBounds
from scripts.pettripfinder.discovery.models import DiscoveryRecord, DiscoverySourceQuery
from scripts.pettripfinder.discovery.query_plan import RequestBudget
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult

_TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})


def api_key_present(env_var: str = C.GOOGLE_PLACES_API_KEY_ENV) -> bool:
    return bool(os.environ.get(env_var, "").strip())


def _sanitized_request(query: DiscoverySourceQuery, page_token: str) -> dict:
    """Everything about the request EXCEPT the key -- this is what gets
    fingerprinted and cached. Never includes headers."""
    return {
        "url": C.GOOGLE_SEARCH_TEXT_URL,
        "textQuery": query.query_text,
        "locationBias": {
            "circle": {
                "center": {"latitude": query.center_lat, "longitude": query.center_lng},
                "radius": query.radius_meters,
            }
        },
        "pageSize": C.GOOGLE_PAGE_SIZE,
        "pageToken": page_token,
        "fieldMask": C.GOOGLE_FIELD_MASK,
    }


def _address_component(components: list, wanted_types: Tuple[str, ...], use_short: bool = False) -> str:
    for comp in components or ():
        types = comp.get("types", ())
        if any(t in wanted_types for t in types):
            return comp.get("shortText" if use_short else "longText", "") or ""
    return ""


def _eligibility_state(name: str, business_status: str, lat: Optional[float],
                        lng: Optional[float], bounds: Optional[GeoBounds]) -> str:
    if business_status == "CLOSED_PERMANENTLY":
        return C.ELIGIBILITY_PERMANENTLY_CLOSED
    if not name:
        return C.ELIGIBILITY_MISSING_IDENTITY
    if bounds is not None and lat is not None and lng is not None and not bounds.contains(lat, lng):
        return C.ELIGIBILITY_OUT_OF_MARKET_BOUNDS
    return C.ELIGIBILITY_ELIGIBLE


def parse_page(payload: dict, query: DiscoverySourceQuery, observed_at: str,
                bounds: Optional[GeoBounds] = None) -> Tuple[Tuple[DiscoveryRecord, ...], Tuple[str, ...]]:
    """Deterministic parse of one Places API (New) searchText response page
    into ``DiscoveryRecord``s. Pure -- no I/O."""
    records = []
    warnings = []
    for place in payload.get("places", ()) or ():
        name = (place.get("displayName") or {}).get("text", "") or ""
        location = place.get("location") or {}
        lat = location.get("latitude")
        lng = location.get("longitude")
        components = place.get("addressComponents") or []
        city = _address_component(components, ("locality", "postal_town"))
        state = _address_component(components, ("administrative_area_level_1",), use_short=True)
        postal_code = _address_component(components, ("postal_code",))
        business_status = place.get("businessStatus", "") or ""
        record_id = place.get("id", "") or ""
        if not record_id:
            warnings.append("missing_place_id")
        types = tuple(place.get("types", ()) or ())
        primary_type = place.get("primaryType", "") or ""
        provider_categories = types if not primary_type or primary_type in types else (primary_type,) + types
        records.append(DiscoveryRecord(
            provider=C.PROVIDER_GOOGLE_PLACES,
            provider_record_id=record_id,
            canonical_category=query.canonical_category,
            provider_categories=provider_categories,
            name=name,
            address_line=place.get("formattedAddress", "") or "",
            city=city, state=state, postal_code=postal_code,
            latitude=float(lat) if isinstance(lat, (int, float)) else None,
            longitude=float(lng) if isinstance(lng, (int, float)) else None,
            phone=place.get("nationalPhoneNumber", "") or "",
            website_url=place.get("websiteUri", "") or "",
            provider_place_url="",   # not requested (googleMapsUri excluded from field mask -- cost)
            business_status=business_status,
            observed_at=observed_at,
            source_query_id=query.query_id,
            provenance=(("market_id", query.market_id), ("cell_id", query.cell_id)),
            eligibility_state=_eligibility_state(name, business_status, lat, lng, bounds),
        ))
    return tuple(records), tuple(warnings)


class GooglePlacesClient:
    """Live adapter. ``session`` is injectable for tests; a real
    ``requests.Session`` is created lazily so importing this module never
    requires the ``requests`` package to be installed for static tests."""

    def __init__(self, session=None, api_key_env: str = C.GOOGLE_PLACES_API_KEY_ENV,
                 sleep_fn=None):
        self._session = session
        self._api_key_env = api_key_env
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

    def _post(self, api_key: str, body: dict) -> Tuple[bool, dict, dict, str]:
        """One HTTP attempt (no retry). Returns
        ``(ok, payload, status_metadata, error_slug)``."""
        import requests
        session = self._get_session()
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": C.GOOGLE_FIELD_MASK,
        }
        request_body = {k: v for k, v in body.items() if k not in ("url", "fieldMask")}
        if not request_body.get("pageToken"):
            request_body.pop("pageToken", None)
        try:
            resp = session.post(
                C.GOOGLE_SEARCH_TEXT_URL, headers=headers, json=request_body,
                timeout=(C.CONNECT_TIMEOUT_SECONDS, C.READ_TIMEOUT_SECONDS),
            )
        except requests.Timeout:
            return (False, {}, {"error": "timeout"}, C.PROVIDER_ERROR_TIMEOUT)
        except requests.RequestException:
            return (False, {}, {"error": "request_exception"}, C.PROVIDER_ERROR_TRANSIENT)

        status = resp.status_code
        status_metadata = {"http_status": status}
        if status in (401, 403):
            return (False, {}, status_metadata, C.PROVIDER_ERROR_AUTH)
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

    def _fetch_page_with_retry(self, api_key: str, body: dict) -> Tuple[bool, dict, dict, str]:
        attempt = 0
        while True:
            ok, payload, status_metadata, error = self._post(api_key, body)
            if ok or error not in (C.PROVIDER_ERROR_TIMEOUT, C.PROVIDER_ERROR_TRANSIENT):
                return (ok, payload, status_metadata, error)
            attempt += 1
            if attempt > C.GOOGLE_MAX_RETRIES:
                return (ok, payload, status_metadata, error)
            self._sleep(C.GOOGLE_RETRY_BACKOFF_SECONDS * attempt)

    def search(self, query: DiscoverySourceQuery, *, cache: DiscoveryCache,
               budget: RequestBudget, observed_at: str,
               bounds: Optional[GeoBounds] = None) -> ProviderQueryResult:
        if not query.enabled:
            return ProviderQueryResult(query_id=query.query_id, provider=C.PROVIDER_GOOGLE_PLACES,
                                       state=C.QUERY_STATE_DISABLED)
        api_key = os.environ.get(self._api_key_env, "").strip()
        if not api_key:
            return ProviderQueryResult(query_id=query.query_id, provider=C.PROVIDER_GOOGLE_PLACES,
                                       state=C.QUERY_STATE_SKIPPED_NO_CREDENTIAL,
                                       error=C.PROVIDER_ERROR_UNAVAILABLE)

        records: List[DiscoveryRecord] = []
        warnings: List[str] = []
        page_token = ""
        pages_fetched = 0
        requests_made = 0
        cache_hits = 0

        for page_num in range(1, max(1, query.max_pages) + 1):
            sanitized_request = _sanitized_request(query, page_token)
            fingerprint = compute_request_fingerprint(sanitized_request)
            cached = cache.get(C.PROVIDER_GOOGLE_PLACES, query.market_id, query.query_id,
                               fingerprint, page_num, as_of=observed_at)
            if cached is not None:
                cache_hits += 1
                payload = cached.payload
            else:
                if not budget.can_spend(1):
                    warnings.append("google_request_budget_exhausted")
                    break
                ok, payload, status_metadata, error = self._fetch_page_with_retry(
                    api_key, sanitized_request)
                budget.spend(1)
                requests_made += 1
                if not ok:
                    return ProviderQueryResult(
                        query_id=query.query_id, provider=C.PROVIDER_GOOGLE_PLACES,
                        state=C.QUERY_STATE_FAILED, error=error,
                        records=tuple(records), requests_made=requests_made,
                        pages_fetched=pages_fetched, cache_hits=cache_hits,
                        warnings=tuple(warnings),
                    )
                cache.put(C.PROVIDER_GOOGLE_PLACES, query.market_id, query.query_id,
                         fingerprint, page_num, sanitized_request=sanitized_request,
                         payload=payload, status_metadata=status_metadata,
                         retrieved_at=observed_at)
            pages_fetched += 1
            page_records, parse_warnings = parse_page(payload, query, observed_at, bounds)
            records.extend(page_records)
            warnings.extend(parse_warnings)
            page_token = payload.get("nextPageToken", "") or ""
            if not page_token:
                break

        # Budget was exhausted before even the first page could be served
        # (from cache or live) -- SKIPPED_CAP_REACHED, not COMPLETED, so
        # yield/coverage reporting doesn't mislabel "nothing happened" as
        # a finished query (bug found and fixed live during Phase 12).
        final_state = (
            C.QUERY_STATE_SKIPPED_CAP_REACHED
            if pages_fetched == 0 and "google_request_budget_exhausted" in warnings
            else C.QUERY_STATE_COMPLETED
        )
        return ProviderQueryResult(
            query_id=query.query_id, provider=C.PROVIDER_GOOGLE_PLACES,
            state=final_state, records=tuple(records),
            requests_made=requests_made, pages_fetched=pages_fetched,
            cache_hits=cache_hits, warnings=tuple(warnings),
        )
