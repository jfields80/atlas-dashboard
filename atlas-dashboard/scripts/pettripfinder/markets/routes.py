"""Market-aware route construction (PTF-CORRIDORS-002 Part A).

Target national architecture:

    /pet-friendly-hotels/{market_slug}/
    /pet-friendly-hotels/{market_slug}/{corridor_slug}/
    /pet-friendly-hotels/{market_slug}/{hotel_slug}/

A market in ``legacy_unprefixed`` route mode (Columbus, until its URL
migration is explicitly approved) keeps today's unprefixed routes:

    /pet-friendly-hotels/
    /pet-friendly-hotels/{corridor_slug}/
    /pet-friendly-hotels/{hotel_slug}/

Duplicate FINAL routes always fail closed -- including the legacy-mode
hazard of a corridor slug colliding with a hotel slug in the shared
unprefixed namespace.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, Sequence, Tuple

from scripts.pettripfinder.markets.assignment import CorridorAssignment
from scripts.pettripfinder.markets.contract import (
    ROUTE_MODE_LEGACY_UNPREFIXED,
    CorridorConfig,
    MarketConfig,
    slugify,
)

CATEGORY_ROOT = "/pet-friendly-hotels/"


class MarketRouteError(ValueError):
    """A route collision or malformed route (fail closed)."""


def market_route(market: MarketConfig) -> str:
    if market.route_mode == ROUTE_MODE_LEGACY_UNPREFIXED:
        return CATEGORY_ROOT
    return "%s%s/" % (CATEGORY_ROOT, market.market_slug)


def corridor_route(market: MarketConfig, corridor: CorridorConfig) -> str:
    if market.route_mode == ROUTE_MODE_LEGACY_UNPREFIXED:
        return "%s%s/" % (CATEGORY_ROOT, corridor.slug)
    return "%s%s/%s/" % (CATEGORY_ROOT, market.market_slug, corridor.slug)


def hotel_route(market: MarketConfig, hotel_name: str) -> str:
    slug = slugify(hotel_name)
    if not slug:
        raise MarketRouteError("hotel name %r produces an empty route slug" % hotel_name)
    if market.route_mode == ROUTE_MODE_LEGACY_UNPREFIXED:
        return "%s%s/" % (CATEGORY_ROOT, slug)
    return "%s%s/%s/" % (CATEGORY_ROOT, market.market_slug, slug)


def build_route_table(
    entries: Iterable[Tuple[str, Dict]],
) -> "OrderedDict[str, Dict]":
    """Collect (route, descriptor) pairs into a table; ANY duplicate final
    route fails closed with both claimants named."""
    table: "OrderedDict[str, Dict]" = OrderedDict()
    for route, descriptor in entries:
        if not route.startswith("/") or not route.endswith("/"):
            raise MarketRouteError("malformed route %r (must start and end with '/')" % route)
        if route in table:
            raise MarketRouteError(
                "duplicate route %r claimed by %r and %r (fail closed)"
                % (route, table[route], descriptor))
        table[route] = descriptor
    return table


def market_route_table(
    market: MarketConfig,
    assignment: CorridorAssignment,
    hotel_names: Sequence[str],
) -> "OrderedDict[str, Dict]":
    """The full public route set one market claims: its market page, every
    PUBLISHED corridor page, and every hotel page. Suppressed corridors
    claim no route. Raises ``MarketRouteError`` on any collision (e.g. a
    legacy-mode hotel slug equal to a corridor slug)."""
    entries = [(market_route(market),
                {"kind": "market", "market_id": market.market_id})]
    for corridor in assignment.published_corridors():
        entries.append((corridor_route(market, corridor),
                        {"kind": "corridor", "market_id": market.market_id,
                         "corridor_id": corridor.corridor_id}))
    for name in hotel_names:
        entries.append((hotel_route(market, name),
                        {"kind": "hotel", "market_id": market.market_id,
                         "hotel": name}))
    return build_route_table(entries)
