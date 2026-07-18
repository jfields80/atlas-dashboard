"""AES-DATA-004A discovery -- deterministic category query planning and the
planner/dry-run report (Task 6).

``plan_queries`` is a pure function: market config + provider/category
selection in, an ordered tuple of ``DiscoverySourceQuery`` out. It never
touches the network. ``build_planner_report`` is equally pure and answers
"how many requests would this cost" before anything is executed, which is
what the CLI ``plan``/``--dry-run`` path renders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.market_config import MarketConfig
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery


# --------------------------------------------------------------------------- #
# Request budget -- shared mutable counter threaded through a live run so a
# global cap holds across queries/pages, not just within one query.
# --------------------------------------------------------------------------- #

@dataclass
class RequestBudget:
    max_requests: int
    used: int = 0

    def remaining(self) -> int:
        return max(0, self.max_requests - self.used)

    def can_spend(self, n: int = 1) -> bool:
        return self.used + n <= self.max_requests

    def spend(self, n: int = 1) -> None:
        self.used += n


# --------------------------------------------------------------------------- #
# Provider-specific category query mappings (Task 6). Multiple bounded text
# variants per category for Google (never one keyword per category). Only
# categories with a real, well-known OSM tag get an Overpass mapping --
# everything else is deliberately absent rather than inventing a tag that
# doesn't exist (doctrine #18), and is disclosed via
# ``OVERPASS_UNSUPPORTED_CATEGORIES`` below.
# --------------------------------------------------------------------------- #

GOOGLE_QUERY_TEMPLATES: Dict[str, Tuple[str, ...]] = {
    C.CATEGORY_HOTEL: ("pet friendly hotel",),
    C.CATEGORY_MOTEL: ("pet friendly motel",),
    C.CATEGORY_VETERINARY: ("veterinarian", "animal hospital"),
    C.CATEGORY_EMERGENCY_VETERINARY: ("emergency veterinarian", "24 hour animal hospital"),
    C.CATEGORY_BOARDING: ("pet boarding", "dog boarding kennel"),
    C.CATEGORY_DAYCARE: ("dog daycare",),
    C.CATEGORY_GROOMING: ("pet groomer", "dog grooming"),
    C.CATEGORY_PET_STORE: ("pet store", "pet supplies"),
    C.CATEGORY_DOG_PARK: ("dog park",),
    C.CATEGORY_PARK: ("park",),
    C.CATEGORY_TRAIL: ("hiking trail",),
    C.CATEGORY_RESTAURANT: ("pet friendly restaurant", "dog friendly restaurant patio"),
    C.CATEGORY_ATTRACTION: ("pet friendly attraction",),
}

# OSM tag expression (single `key=value`) per category. Absent category =
# no supported tag; OSM coverage is skipped for it, never approximated.
OVERPASS_TAG_QUERIES: Dict[str, str] = {
    C.CATEGORY_HOTEL: "tourism=hotel",
    C.CATEGORY_MOTEL: "tourism=motel",
    C.CATEGORY_VETERINARY: "amenity=veterinary",
    C.CATEGORY_PET_STORE: "shop=pet",
    C.CATEGORY_DOG_PARK: "leisure=dog_park",
    C.CATEGORY_PARK: "leisure=park",
    # Trail coverage via OSM is real but structurally weak for a single-tag
    # bbox query (trails are usually `route=hiking` relations built from many
    # `highway=path`/`highway=footway` ways) -- disclosed as weak, not
    # invented; `highway=path` is the closest single-tag proxy.
    C.CATEGORY_TRAIL: "highway=path",
}
# Categories with no Overpass mapping at all -- OSM has no standard tag for
# these (emergency-vet triage, boarding, daycare, grooming, dog-friendly
# restaurant patios, dog-friendly attractions are not stable OSM concepts).
OVERPASS_UNSUPPORTED_CATEGORIES = frozenset(
    C.DISCOVERY_CATEGORY_SET - set(OVERPASS_TAG_QUERIES)
)


def _google_query_text(template: str, municipality: str, state: str) -> str:
    return "%s in %s, %s" % (template, municipality, state)


def plan_queries(
    market: MarketConfig,
    providers: Sequence[str],
    categories: Sequence[str],
    *,
    max_pages_per_query: int = C.DEFAULT_MAX_PAGES_PER_QUERY,
) -> Tuple[DiscoverySourceQuery, ...]:
    """Deterministic query enumeration. Never calls a provider. Foursquare
    queries are always emitted with ``enabled=False`` (Task 5 -- the seam
    exists, nothing runs against it)."""
    for category in categories:
        if category not in C.DISCOVERY_CATEGORY_SET:
            raise ValueError("unknown discovery category: %r" % category)
    for provider in providers:
        if provider not in C.DISCOVERY_PROVIDERS:
            raise ValueError("unknown discovery provider: %r" % provider)

    queries = []
    for category in categories:
        for cell in market.cells:
            if C.PROVIDER_GOOGLE_PLACES in providers:
                templates = GOOGLE_QUERY_TEMPLATES.get(
                    category, (category.replace("_", " "),))
                for idx, template in enumerate(templates):
                    query_id = "%s__%s__%s__%d" % (
                        C.PROVIDER_GOOGLE_PLACES, category, cell.cell_id, idx)
                    queries.append(DiscoverySourceQuery(
                        query_id=query_id, provider=C.PROVIDER_GOOGLE_PLACES,
                        canonical_category=category,
                        query_text=_google_query_text(template, cell.municipality, market.state),
                        market_id=market.market_id, cell_id=cell.cell_id,
                        center_lat=cell.center_lat, center_lng=cell.center_lng,
                        radius_meters=cell.radius_meters,
                        max_pages=max_pages_per_query,
                        expected_market=market.market_id, enabled=True,
                    ))
            if C.PROVIDER_OPENSTREETMAP in providers:
                tag = OVERPASS_TAG_QUERIES.get(category)
                if tag is None:
                    continue
                query_id = "%s__%s__%s" % (C.PROVIDER_OPENSTREETMAP, category, cell.cell_id)
                queries.append(DiscoverySourceQuery(
                    query_id=query_id, provider=C.PROVIDER_OPENSTREETMAP,
                    canonical_category=category, query_text=tag,
                    market_id=market.market_id, cell_id=cell.cell_id,
                    center_lat=cell.center_lat, center_lng=cell.center_lng,
                    radius_meters=cell.radius_meters, max_pages=1,
                    expected_market=market.market_id, enabled=True,
                ))
            if C.PROVIDER_FOURSQUARE in providers:
                query_id = "%s__%s__%s" % (C.PROVIDER_FOURSQUARE, category, cell.cell_id)
                queries.append(DiscoverySourceQuery(
                    query_id=query_id, provider=C.PROVIDER_FOURSQUARE,
                    canonical_category=category, query_text=category,
                    market_id=market.market_id, cell_id=cell.cell_id,
                    center_lat=cell.center_lat, center_lng=cell.center_lng,
                    radius_meters=cell.radius_meters, max_pages=1,
                    expected_market=market.market_id, enabled=False,
                ))
    return tuple(queries)


# --------------------------------------------------------------------------- #
# Planner / dry-run report (Task 6).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class PlannerReport:
    market_id: str
    total_planned_queries: int
    queries_by_provider: Tuple[Tuple[str, int], ...]
    queries_by_category: Tuple[Tuple[str, int], ...]
    queries_by_cell: Tuple[Tuple[str, int], ...]
    max_possible_paginated_requests: int
    estimated_upper_bound_google_billable_calls: int
    estimated_upper_bound_overpass_requests: int
    blocked_queries_missing_credential: Tuple[str, ...]
    credentials_available: Tuple[Tuple[str, bool], ...]


def _count_by(queries: Sequence[DiscoverySourceQuery], key) -> Tuple[Tuple[str, int], ...]:
    counts: Dict[str, int] = {}
    for q in queries:
        k = key(q)
        counts[k] = counts.get(k, 0) + 1
    return tuple(sorted(counts.items()))


def build_planner_report(
    queries: Tuple[DiscoverySourceQuery, ...],
    *,
    market_id: str,
    google_key_present: bool,
    foursquare_key_present: bool,
) -> PlannerReport:
    """Pure accounting over an already-built query plan. Makes no network
    calls -- this is exactly what the CLI's ``plan``/``--dry-run`` path
    renders (mission Task 6/12)."""
    enabled = [q for q in queries if q.enabled]
    google_queries = [q for q in enabled if q.provider == C.PROVIDER_GOOGLE_PLACES]
    overpass_queries = [q for q in enabled if q.provider == C.PROVIDER_OPENSTREETMAP]

    blocked = []
    if not google_key_present:
        blocked.extend(q.query_id for q in google_queries)
    # Foursquare queries are always disabled in this phase (Task 5); they are
    # never "blocked" by a missing credential -- they are structurally not run.

    max_possible = sum(q.max_pages for q in google_queries) + len(overpass_queries)
    google_upper_bound = sum(q.max_pages for q in google_queries) if google_key_present else 0
    overpass_upper_bound = len(overpass_queries)

    return PlannerReport(
        market_id=market_id,
        total_planned_queries=len(queries),
        queries_by_provider=_count_by(queries, lambda q: q.provider),
        queries_by_category=_count_by(queries, lambda q: q.canonical_category),
        queries_by_cell=_count_by(queries, lambda q: q.cell_id),
        max_possible_paginated_requests=max_possible,
        estimated_upper_bound_google_billable_calls=google_upper_bound,
        estimated_upper_bound_overpass_requests=overpass_upper_bound,
        blocked_queries_missing_credential=tuple(sorted(blocked)),
        credentials_available=(
            (C.PROVIDER_GOOGLE_PLACES, google_key_present),
            (C.PROVIDER_OPENSTREETMAP, True),
            (C.PROVIDER_FOURSQUARE, foursquare_key_present),
        ),
    )
