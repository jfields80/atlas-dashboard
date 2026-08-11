"""PTF-PROD-002 -- production hotel-profile PAGE builder.

The single official hotel-profile markup path for the Columbus site build. It
is the thin production seam that connects:

    real production row + verified facts
        -> hotel_profile.build_vm_from_production / _from_production_unverified
        -> hotel_profile.render_hotel_profile   (the APPROVED renderer)
        -> canonical <link> + breadcrumb/LodgingBusiness JSON-LD injected in <head>

It deliberately adds NO body markup of its own -- the approved renderer owns
every visible element (media, hero, corridor label, six-fact grid, actions,
trust strip, provenance, related). This module only supplies the head metadata
the renderer intentionally leaves to the site layer (canonical + structured
data), reusing the existing structured_data builders and site_enrichment's
inject_head. There is no second hotel renderer here.

Doctrine carried from the renderer/importer chain: facts come only from
repository-authorized verified evidence or the promoted production CSV; an
unverified hotel asserts no policy; structured data never claims more than the
visible page (petsAllowed only when a verified badge is actually shown). No
network. Reads production/verification data, never writes inventory.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from scripts.pettripfinder.approved_hotel_profile import render_approved_hotel_profile
from scripts.pettripfinder.commercial_actions import ACTION_OFFICIAL_WEBSITE, go_route
from scripts.pettripfinder.hotel_profile import (
    STATE_NO_PETS,
    build_vm_from_production,
    build_vm_from_production_unverified,
)
from scripts.pettripfinder.site_enrichment import (
    BASE_URL,
    DEFAULT_ANALYTICS_MARKET,
    build_go_pages_for_listing,
    inject_head,
)
from scripts.pettripfinder.structured_data import (
    breadcrumb_ld,
    lodging_business_ld,
    to_script_tag,
)

CATEGORY_SLUG = "pet-friendly-hotels"
CATEGORY_LABEL = "Pet-Friendly Hotels"
HOTEL_CSS_HREF = "/hotel-profile.css"
# The production Columbus hub is the site root (no /columbus-oh/ page exists in
# the AES-SITE-001 base bundle); the approved renderer defaults to the design
# authority's /columbus-oh/ and we pass the real hub route here.
MARKET_HOME = "/"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def verification_status_for(facts_entry: Optional[Dict]) -> str:
    if not facts_entry:
        return "POLICY_UNVERIFIED"
    if facts_entry["facts"].get("pets_allowed") == "false":
        return "VERIFIED_NO_PETS"
    return "VERIFIED_PET_FRIENDLY"


def _head_metadata(row: Dict[str, str], listing_id: str, facts_entry: Optional[Dict]) -> str:
    """Canonical self-link + breadcrumb and LodgingBusiness JSON-LD, matching
    the base pipeline's self-canonical (origin + route) and the visible page."""
    route = "/%s/%s/" % (CATEGORY_SLUG, listing_id)
    canonical = '<link rel="canonical" href="%s%s">' % (BASE_URL, route)

    pets_allowed: Optional[bool] = None
    amenity_features: Optional[List[str]] = None
    if facts_entry:
        pa = facts_entry["facts"].get("pets_allowed")
        if pa in ("true", "false"):
            pets_allowed = (pa == "true")
        amenity_features = [v for k, v in facts_entry["facts"].items() if k == "species_allowed"] or None

    ld_objects = [
        breadcrumb_ld(BASE_URL, [
            ("PetTripFinder", "/"),
            (CATEGORY_LABEL, "/%s/" % CATEGORY_SLUG),
            (row["name"], route),
        ]),
        lodging_business_ld(
            base_url=BASE_URL, route=route, name=row["name"],
            street=row.get("address", ""), city=row.get("city", ""), state=row.get("state", ""),
            postal_code=row.get("postal_code", ""), official_url=row.get("website_url", ""),
            pets_allowed=pets_allowed, amenity_features=amenity_features,
        ),
    ]
    return canonical + to_script_tag(ld_objects)


# Deterministic temporary-review photo per listing (the five approved review
# JPGs copied to /assets/ by the homepage step). Google Places media is a
# separate later phase; the renderer captions the slot as temporary.
_REVIEW_PHOTOS = 5


def _media_for(listing_id: str) -> str:
    idx = sum(ord(c) for c in listing_id) % _REVIEW_PHOTOS + 1
    return "/assets/hotel%d.jpg" % idx


def _place_desc(row: Dict[str, str]) -> str:
    """One honest descriptive line for a nearby-place card, taken verbatim
    (truncated) from the place's own recorded pet_policy text."""
    text = (row.get("pet_policy") or "").split(";")[0].strip()
    if len(text) > 88:
        text = text[:85].rstrip() + "…"
    return text


def _nearby_from_inventory(
    row: Dict[str, str], park_rows: List[Dict[str, str]],
    restaurant_rows: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Up to three REAL nearby places (same city first, then the Columbus
    core) from the existing verified inventory: two parks and one restaurant.
    No distances -- production carries no coordinates and mileage is never
    fabricated (site_data doctrine)."""
    city = (row.get("city") or "").strip().lower()

    def ranked(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        same = [r for r in rows if (r.get("city") or "").strip().lower() == city]
        rest = [r for r in rows if r not in same]
        key = lambda r: r["name"].lower()
        return sorted(same, key=key) + sorted(rest, key=key)

    out: List[Dict[str, str]] = []
    for park in ranked(park_rows)[:2]:
        pid = _slug(park["name"])
        out.append({
            "kind": "park", "name": park["name"], "desc": _place_desc(park),
            "meta": "%s, %s" % (park.get("city", ""), park.get("state", "")),
            "href": "/go/%s/directions/" % pid, "btn": "Get directions"})
    for rest in ranked(restaurant_rows)[:1]:
        out.append({
            "kind": "restaurant", "name": rest["name"], "desc": _place_desc(rest),
            "meta": "%s, %s" % (rest.get("city", ""), rest.get("state", "")),
            "href": "/pet-friendly-restaurants/%s/" % _slug(rest["name"]),
            "btn": "View details"})
    return out


def render_production_hotel_profile(
    row: Dict[str, str], facts_entry: Optional[Dict], hotel_rows: List[Dict[str, str]],
    facts_map: Dict, *, css_href: str = HOTEL_CSS_HREF, market_home: str = MARKET_HOME,
    park_rows: Optional[List[Dict[str, str]]] = None,
    restaurant_rows: Optional[List[Dict[str, str]]] = None,
    corridor_href: Optional[str] = None,
    market_id: Optional[str] = None,
) -> str:
    """A complete, SEO-integrated hotel-profile page for one production row,
    rendered by the founder-approved profile design
    (approved_hotel_profile.render_approved_hotel_profile). Verified rows
    (rich/sparse) use build_vm_from_production; rows without verified facts
    render the honest POLICY_UNVERIFIED state with their real identity. A
    production no-pets row would be a data error (production carries none) --
    fail closed rather than silently mislabel. ``market_home`` is retained for
    API compatibility (the approved design links the hub explicitly)."""
    if facts_entry and facts_entry["facts"].get("pets_allowed") == "false":
        raise ValueError(
            "unexpected no-pets facts on production hotel row %r; production "
            "inventory contains no no-pets hotels" % row.get("name"))
    if facts_entry:
        vm = build_vm_from_production(row, facts_entry, hotel_rows, facts_map,
                                      market_id=market_id)
    else:
        vm = build_vm_from_production_unverified(row, hotel_rows, facts_map,
                                                 market_id=market_id)
    assert vm.state != STATE_NO_PETS  # guarded above; documents the invariant
    listing_id = _slug(row["name"])
    html_text = render_approved_hotel_profile(
        vm, listing_id=listing_id, css_href=css_href,
        media_src=_media_for(listing_id),
        nearby=_nearby_from_inventory(row, park_rows or [], restaurant_rows or []),
        corridor_href=corridor_href,
        related_thumbs={rel.route: _media_for(rel.route.rstrip("/").rsplit("/", 1)[-1])
                        for rel in vm.related})
    return inject_head(html_text, _head_metadata(row, listing_id, facts_entry))


def build_hotel_go_pages(
    row: Dict[str, str], listing_id: str, corridor: str, facts_entry: Optional[Dict],
    market: str = DEFAULT_ANALYTICS_MARKET,
) -> Dict[str, str]:
    """The /go/ interstitials the approved hotel renderer links to, including
    /go/<id>/booking/ (verified pet-friendly hotels only -- the booking CTA is
    the primary action only in the 'book' state). Reuses the shared, tested
    go-page builder; no new redirect logic here."""
    status = verification_status_for(facts_entry)
    include_booking = status == "VERIFIED_PET_FRIENDLY"
    return build_go_pages_for_listing(
        listing_id=listing_id, name=row["name"], official_url=row.get("website_url", ""),
        phone=row.get("phone", ""), address=row.get("address", ""), city=row.get("city", ""),
        state=row.get("state", ""), category_slug=CATEGORY_SLUG, corridor=corridor,
        verification_status=status, include_booking=include_booking,
        market=market)
