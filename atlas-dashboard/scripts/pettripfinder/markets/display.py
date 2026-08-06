"""Unified corridor display labels (Part D).

The ONE source of the "<Area> corridor · <City>, <ST>" label the approved
hotel-profile design shows -- replacing the second, address-token taxonomy
that previously lived in ``hotel_profile.py``. Labels derive from the SAME
assignment used for routes/sitemap/navigation:

- an assigned hotel shows its corridor's ``display_area`` (short label,
  defaulting to the corridor name), even when the corridor is suppressed
  from publication (a label is a fact about location; a route is not);
- an unassigned hotel falls back to its own CITY when that differs from the
  market's primary city (a suburb is an honest area on its own), otherwise
  to the primary city -- never to an area inferred from address text or a
  marketing name.

The metro anchor is the market's primary city + state code, never a
hard-coded string.
"""

from __future__ import annotations

from typing import Optional

from scripts.pettripfinder.markets.assignment import CorridorAssignment
from scripts.pettripfinder.markets.contract import MarketConfig
from scripts.pettripfinder.site_data import normalize_name


def corridor_display_area(market: MarketConfig, assignment: Optional[CorridorAssignment],
                          hotel_name: str, city: str) -> str:
    """Short area label for one hotel ("Downtown", "Dublin", "Grove City")."""
    if assignment is not None:
        corridor_ids = assignment.corridor_of.get(normalize_name(hotel_name), ())
        if corridor_ids:
            corridors = [market.corridor_by_id(cid) for cid in corridor_ids]
            first = min(corridors, key=lambda c: (c.display_order, c.slug))
            return first.display_area
    c = (city or "").strip()
    if c and c.lower() != market.primary_city.lower():
        return c
    return market.primary_city


def corridor_display_label(market: MarketConfig, assignment: Optional[CorridorAssignment],
                           hotel_name: str, city: str) -> str:
    """The full profile chip label: "<Area> corridor · <PrimaryCity>, <ST>"."""
    area = corridor_display_area(market, assignment, hotel_name, city)
    return "%s corridor · %s, %s" % (area, market.primary_city, market.state_code)
