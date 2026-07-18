"""AES-DATA-004C Task 1 -- deterministic lodging-scope classification.

Classifies a discovery candidate as IN_SCOPE / BORDERLINE_SCOPE /
OUT_OF_SCOPE / UNKNOWN_SCOPE against the committed Columbus market
configuration, using municipality + coordinates + city/state -- never
provider location bias alone, and never silently excluding a candidate
that simply has missing geography.
"""

from __future__ import annotations

from typing import Optional

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.market_config import GeoBounds, MarketConfig
from scripts.pettripfinder.discovery.models import DiscoveryCandidate
from scripts.pettripfinder.discovery.normalize import normalize_business_name


def _expanded_bounds(bounds: GeoBounds, fraction: float) -> GeoBounds:
    lat_buffer = (bounds.max_lat - bounds.min_lat) * fraction
    lng_buffer = (bounds.max_lng - bounds.min_lng) * fraction
    return GeoBounds(
        min_lat=bounds.min_lat - lat_buffer, max_lat=bounds.max_lat + lat_buffer,
        min_lng=bounds.min_lng - lng_buffer, max_lng=bounds.max_lng + lng_buffer,
    )


def classify_lodging_scope(candidate: DiscoveryCandidate, market: MarketConfig) -> str:
    """Pure, deterministic. Never fetches, never uses provider location
    bias as evidence -- only the candidate's own address/coordinate
    fields against the committed market configuration."""
    city = normalize_business_name(candidate.city) if candidate.city else ""
    state = (candidate.state or "").strip().upper()
    lat, lng = candidate.latitude, candidate.longitude
    has_coords = lat is not None and lng is not None

    included_normalized = {normalize_business_name(m) for m in market.included_municipalities}
    municipality_match: Optional[bool] = (city in included_normalized) if city else None

    coords_in_bounds: Optional[bool] = None
    coords_in_buffer: Optional[bool] = None
    if has_coords:
        coords_in_bounds = market.bounds.contains(lat, lng)
        if not coords_in_bounds:
            buffered = _expanded_bounds(market.bounds, C.SCOPE_BORDERLINE_BUFFER_FRACTION)
            coords_in_buffer = buffered.contains(lat, lng)

    # No geography at all -- never silently excluded.
    if municipality_match is None and not has_coords:
        return C.SCOPE_UNKNOWN

    # Conflicting signals: municipality says in, coordinates say clearly out
    # (beyond even the borderline buffer), or vice versa.
    if municipality_match is True and has_coords and coords_in_bounds is False and coords_in_buffer is False:
        return C.SCOPE_BORDERLINE
    if municipality_match is False and has_coords and coords_in_bounds is True:
        return C.SCOPE_BORDERLINE

    if municipality_match is True:
        return C.SCOPE_IN_SCOPE
    if has_coords and coords_in_bounds:
        return C.SCOPE_IN_SCOPE
    if has_coords and coords_in_buffer:
        return C.SCOPE_BORDERLINE
    if has_coords:
        return C.SCOPE_OUT_OF_SCOPE

    # No coordinates; municipality is known but not in the configured list.
    if municipality_match is False:
        if state and state != market.state:
            return C.SCOPE_OUT_OF_SCOPE
        # Same state, unfamiliar municipality -- could be a real adjacent
        # suburb not yet in the configured list; never guess it's excluded.
        return C.SCOPE_BORDERLINE

    return C.SCOPE_UNKNOWN
