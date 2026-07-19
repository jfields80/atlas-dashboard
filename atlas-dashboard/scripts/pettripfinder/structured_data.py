"""AES-SITE-001 (Task 13) -- JSON-LD structured data.

Every field emitted here must already be visibly rendered as real page
content -- this module reads the SAME approved facts the HTML templates use
(never a richer/different source), so structured data can never claim more
than the visible page (mission doctrine: "Structured data must never be
richer than the visible content"). No ratings, review counts, price ranges,
hours, or ``petsAllowed`` are ever emitted unless that exact fact is visibly
present on the page being described.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

SCHEMA_CONTEXT = "https://schema.org"


def _clean(d: Dict) -> Dict:
    """Drop empty/None values -- schema.org readers treat a present-but-
    empty field as a claim; omission is the honest "not stated" signal."""
    return {k: v for k, v in d.items() if v not in (None, "", [], {}, ())}


def website_ld(base_url: str, name: str) -> Dict:
    return _clean({
        "@context": SCHEMA_CONTEXT, "@type": "WebSite",
        "name": name, "url": base_url,
    })


def organization_ld(base_url: str, name: str) -> Dict:
    return _clean({
        "@context": SCHEMA_CONTEXT, "@type": "Organization",
        "name": name, "url": base_url,
    })


def breadcrumb_ld(base_url: str, crumbs: List[Tuple[str, str]]) -> Dict:
    """``crumbs``: ordered ``(name, route)`` pairs, home first."""
    items = [
        {"@type": "ListItem", "position": i + 1, "name": name,
         "item": base_url.rstrip("/") + route}
        for i, (name, route) in enumerate(crumbs)
    ]
    return _clean({"@context": SCHEMA_CONTEXT, "@type": "BreadcrumbList", "itemListElement": items})


def item_list_ld(base_url: str, name: str, entries: List[Tuple[str, str]]) -> Dict:
    """``entries``: ordered ``(name, route)`` pairs for a category page."""
    items = [
        {"@type": "ListItem", "position": i + 1, "name": n,
         "url": base_url.rstrip("/") + route}
        for i, (n, route) in enumerate(entries)
    ]
    return _clean({"@context": SCHEMA_CONTEXT, "@type": "ItemList", "name": name, "itemListElement": items})


def _address_ld(street: str, city: str, state: str, postal_code: str) -> Optional[Dict]:
    if not (street or city):
        return None
    return _clean({
        "@type": "PostalAddress", "streetAddress": street, "addressLocality": city,
        "addressRegion": state, "postalCode": postal_code, "addressCountry": "US",
    })


def lodging_business_ld(
    *, base_url: str, route: str, name: str, street: str, city: str, state: str,
    postal_code: str, official_url: str, pets_allowed: Optional[bool] = None,
    amenity_features: Optional[List[str]] = None,
) -> Dict:
    """``pets_allowed`` must be passed ONLY when a verified badge is
    actually shown on this exact page -- None means the page shows no
    pets_allowed claim, so this field is correctly omitted (never defaults
    to False, which would itself be an unverified claim)."""
    out: Dict = {
        "@context": SCHEMA_CONTEXT, "@type": "LodgingBusiness",
        "name": name, "url": base_url.rstrip("/") + route,
        "address": _address_ld(street, city, state, postal_code),
    }
    if official_url:
        out["sameAs"] = official_url
    if pets_allowed is not None:
        out["petsAllowed"] = bool(pets_allowed)
    if amenity_features:
        out["amenityFeature"] = [
            {"@type": "LocationFeatureSpecification", "name": f, "value": True}
            for f in amenity_features
        ]
    return _clean(out)


def place_ld(*, base_url: str, route: str, name: str, street: str, city: str,
             state: str, postal_code: str, official_url: str, place_type: str = "Park") -> Dict:
    out = {
        "@context": SCHEMA_CONTEXT, "@type": place_type,
        "name": name, "url": base_url.rstrip("/") + route,
        "address": _address_ld(street, city, state, postal_code),
    }
    if official_url:
        out["sameAs"] = official_url
    return _clean(out)


def restaurant_ld(*, base_url: str, route: str, name: str, street: str, city: str,
                  state: str, postal_code: str, official_url: str) -> Dict:
    return place_ld(base_url=base_url, route=route, name=name, street=street,
                    city=city, state=state, postal_code=postal_code,
                    official_url=official_url, place_type="Restaurant")


def to_script_tag(ld_objects: List[Dict]) -> str:
    """One or more JSON-LD objects, each in its own ``<script>`` tag (the
    standard multi-block form -- easier to validate/debug than an @graph
    array, and matches how most crawlers parse multi-entity pages)."""
    objs = [o for o in ld_objects if o]
    if not objs:
        return ""
    tags = []
    for obj in objs:
        payload = json.dumps(obj, ensure_ascii=False, sort_keys=True)
        # JSON-LD is not HTML -- but a literal "</script" inside a string
        # value would still prematurely close the tag in an HTML parser;
        # escape it defensively (standard JSON-in-HTML practice).
        payload = payload.replace("</", "<\\/")
        tags.append('<script type="application/ld+json">%s</script>' % payload)
    return "".join(tags)
