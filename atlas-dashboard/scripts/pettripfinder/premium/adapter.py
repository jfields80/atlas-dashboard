"""PETTRIPFINDER-DESIGN-002 -- data adapters between the site pipeline and the
premium renderers. Pure functions: turn a production seed row + its committed
facts entry into the small dicts the premium page renderers consume, and build
the JSON-LD head blocks for premium pages. No new facts are introduced -- every
value is copied through from the committed package / seed data, or omitted.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from scripts.pettripfinder.hotel_profile import _corridor_area, _friendly_date, _initials
from scripts.pettripfinder.structured_data import (
    breadcrumb_ld, place_ld, restaurant_ld, to_script_tag,
)

BASE_URL = "https://pettripfinder.com"
_CAT_LABEL = {
    "pet-friendly-parks": "Pet-friendly parks",
    "pet-friendly-restaurants": "Pet-friendly restaurants",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def hotel_card_dict(row: Dict, facts_entry: Optional[Dict]) -> Dict:
    """Card data for the premium hotel_card. ``facts`` are passed through
    verbatim from the committed package; the renderer decides honest chips."""
    name = row["name"]
    f = (facts_entry or {}).get("facts", {}) if facts_entry else {}
    return dict(
        name=name,
        area=_corridor_area(row.get("city", ""), row.get("address", ""), name),
        route="/pet-friendly-hotels/%s/" % _slug(name),
        verified_at=_friendly_date((facts_entry or {}).get("verified_at", "")) if facts_entry else "",
        facts=f,
        initials=_initials(name),
    )


def featured_order(cards: List[Dict]) -> List[Dict]:
    """Deterministic 'featured' ordering: hotels with the richest quoted facts
    first (fee stated, then species/limits), then the rest alphabetically -- so
    the homepage's featured cards look substantive without inventing anything."""
    def richness(c: Dict) -> Tuple:
        f = c["facts"]
        return (
            -1 if f.get("pet_fee") else 0,
            -sum(1 for k in ("species_allowed", "pet_count_limit", "weight_limit") if f.get(k)),
            c["name"].lower(),
        )
    return sorted(cards, key=richness)


def comparison_row(row: Dict, facts_entry: Optional[Dict]) -> Dict:
    f = (facts_entry or {}).get("facts", {}) if facts_entry else {}
    return dict(
        name=row["name"],
        route="/pet-friendly-hotels/%s/" % _slug(row["name"]),
        area="%s, %s" % (row.get("city", ""), row.get("state", "")),
        species=f.get("species_allowed", ""),
        fee=f.get("pet_fee", ""),
        fee_basis=f.get("fee_basis", ""),
        count=f.get("pet_count_limit", ""),
        weight=f.get("weight_limit", ""),
        verified_at=_friendly_date((facts_entry or {}).get("verified_at", "")) if facts_entry else "",
    )


def place_profile_head(row: Dict, category_slug: str, place_type: str) -> str:
    """Breadcrumb + Park/Restaurant JSON-LD for a premium place profile (exactly
    one place-type entry, matching the visible page)."""
    route = "/%s/%s/" % (category_slug, _slug(row["name"]))
    builder = place_ld if place_type == "Park" else restaurant_ld
    lds = [
        breadcrumb_ld(BASE_URL, [("PetTripFinder", "/"),
                                 (_CAT_LABEL[category_slug], "/%s/" % category_slug),
                                 (row["name"], route)]),
        builder(base_url=BASE_URL, route=route, name=row["name"],
                street=row.get("address", ""), city=row.get("city", ""),
                state=row.get("state", ""), postal_code=row.get("postal_code", ""),
                official_url=row.get("website_url", "")),
    ]
    return to_script_tag(lds)


def listing_head(category_slug: str, rows: List[Dict], label: str) -> str:
    """Breadcrumb + ItemList JSON-LD for a premium listing page."""
    from scripts.pettripfinder.structured_data import item_list_ld
    route = "/%s/" % category_slug
    entries = [(r["name"], "%s%s/" % (route, _slug(r["name"]))) for r in rows]
    lds = [
        breadcrumb_ld(BASE_URL, [("PetTripFinder", "/"), (label, route)]),
        item_list_ld(BASE_URL, label, entries),
    ]
    return to_script_tag(lds)
