"""Data-driven corridor navigation and sitemap entries (Part E).

Everything here derives from the market config + the shared assignment
result: only PUBLISHED corridors (>= their configured minimum) that opt in
via ``show_in_navigation`` / ``show_in_sitemap`` ever produce a link, so a
suppressed corridor can never create a broken navigation or breadcrumb
link. Ordering is the configured ``display_order`` -- deterministic, never
insertion or dict order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from scripts.pettripfinder.markets.assignment import CorridorAssignment
from scripts.pettripfinder.markets.contract import MarketConfig
from scripts.pettripfinder.markets.routes import corridor_route
from scripts.pettripfinder.site_data import normalize_name


@dataclass(frozen=True)
class NavEntry:
    label: str
    route: str
    corridor_id: str


def _ordered_published(assignment: CorridorAssignment):
    return sorted(assignment.published_corridors(),
                  key=lambda c: (c.display_order, c.slug))


def corridor_navigation(market: MarketConfig,
                        assignment: CorridorAssignment) -> Tuple[NavEntry, ...]:
    """Ordered navigation entries for the market's published, nav-visible
    corridors. Empty when the market itself is nav-hidden or below its
    published-hotel minimum."""
    if not market.show_in_navigation:
        return ()
    # The market gates on its total published-hotel inventory: every row the
    # assignment saw is a published hotel (assigned or reported-unassigned).
    total_hotels = len(assignment.corridor_of) + len(assignment.unassigned)
    if total_hotels < market.minimum_published_hotels:
        return ()
    return tuple(
        NavEntry(label=corridor.name,
                 route=corridor_route(market, corridor),
                 corridor_id=corridor.corridor_id)
        for corridor in _ordered_published(assignment)
        if corridor.show_in_navigation)


def sitemap_corridor_routes(market: MarketConfig,
                            assignment: CorridorAssignment) -> Tuple[str, ...]:
    """Sitemap routes for published, sitemap-visible corridors, in display
    order. A market with show_in_sitemap=False contributes nothing."""
    if not market.show_in_sitemap:
        return ()
    return tuple(corridor_route(market, corridor)
                 for corridor in _ordered_published(assignment)
                 if corridor.show_in_sitemap)


def corridor_href_for(market: MarketConfig, assignment: CorridorAssignment,
                      hotel_name: str) -> Optional[str]:
    """The breadcrumb/see-all link for one hotel: the route of its first
    (display-ordered) PUBLISHED corridor, or None -- a suppressed corridor
    must never become a broken link."""
    key = normalize_name(hotel_name)
    corridor_ids = assignment.corridor_of.get(key, ())
    if not corridor_ids:
        return None
    published = set(assignment.published)
    candidates = [market.corridor_by_id(cid) for cid in corridor_ids if cid in published]
    if not candidates:
        return None
    corridor = min(candidates, key=lambda c: (c.display_order, c.slug))
    return corridor_route(market, corridor)
