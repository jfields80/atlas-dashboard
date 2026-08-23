"""PTF-ST-LOUIS-MARKET-001 -- route a whole market's census, once, generically.

Between a census and an acquisition run sits a question every market has had to
answer by hand: for each identity, what is its source URL really, which brand
owns it, which lane does the registry give it, and is the URL good enough to
carry a policy fact at all? Four markets answered it in four scripts.

This module answers it in one pass over a census document and returns a report.
It fetches nothing and it writes nothing; the caller decides what to persist.

THE URL SHAPE IS THE INTERESTING PART
-------------------------------------
A discovery provider's ``websiteUri`` is not a policy source. It comes in four
shapes and only one of them can back a fact:

    PROPERTY_PAGE      a page about exactly this hotel
    BRAND_REDIRECT     the brand's own click-tracker, carrying a property code
                       (``ihg.com/redirect?...&hotelCode=ALNAT&cm_mmc=...``).
                       Property-specific, but the tracking parameters are not:
                       they name the referrer, not the hotel, and two records
                       for one property differ only in them. Normalised.
    BRAND_INDEX        a brand home page, a city search, a locator. Property-
                       specific for nobody -- the partition has a state for
                       exactly this (``AWAITING_PROPERTY_LEVEL_URL``).
    THIRD_PARTY        an OTA, a social page, an aggregator. Never first-party.

Nothing here upgrades a shape. A BRAND_INDEX stays a BRAND_INDEX; saying so is
the point, because a market that counts brand-index URLs as routed reports 97%
routing coverage and then acquires nothing.
"""

from __future__ import annotations

import re
from collections import Counter, OrderedDict
from typing import Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.brightdata.corpus import (
    BRAND_HOSTS, INDEPENDENT_PREFIX, brand_of,
)

CONTRACT = "ptf-market-routing/1.0"

# URL shapes.
PROPERTY_PAGE = "PROPERTY_PAGE"
BRAND_REDIRECT = "BRAND_REDIRECT"
BRAND_INDEX = "BRAND_INDEX"
THIRD_PARTY = "THIRD_PARTY"
NO_URL = "NO_URL"

URL_SHAPES: Tuple[str, ...] = (PROPERTY_PAGE, BRAND_REDIRECT, BRAND_INDEX,
                               THIRD_PARTY, NO_URL)

#: Shapes a policy fact may be read from. A brand index may not.
ROUTABLE_SHAPES = frozenset({PROPERTY_PAGE, BRAND_REDIRECT})

# Routing states.
ROUTED = "ROUTED"
ROUTE_BRAND_EXCLUDED = "ROUTE_BRAND_EXCLUDED"
ROUTE_NEEDS_PROPERTY_URL = "ROUTE_NEEDS_PROPERTY_URL"
ROUTE_NEEDS_OFFICIAL_URL = "ROUTE_NEEDS_OFFICIAL_URL"
ROUTE_NEEDS_FIRST_PARTY_URL = "ROUTE_NEEDS_FIRST_PARTY_URL"

ROUTING_STATES: Tuple[str, ...] = (
    ROUTED, ROUTE_BRAND_EXCLUDED, ROUTE_NEEDS_PROPERTY_URL,
    ROUTE_NEEDS_OFFICIAL_URL, ROUTE_NEEDS_FIRST_PARTY_URL,
)

#: Query parameters that name the REFERRER rather than the property. Dropped so
#: two sightings of one hotel normalise to one URL. Everything not on this list
#: is kept -- a hotel code often lives in a query parameter, and guessing which
#: ones are safe to drop is how a route stops pointing at a property.
TRACKING_PARAMS = frozenset({
    "cm_mmc", "cm_sp", "gclid", "fbclid", "msclkid", "utm_source", "utm_medium",
    "utm_campaign", "utm_term", "utm_content", "yext", "y_source", "scmisc",
    "srp_id", "gmb", "wt.mc_id", "wt_mc_id", "ref", "referrer",
})

#: Hosts that are somebody else's inventory, never the property's own page.
THIRD_PARTY_HOSTS: Tuple[str, ...] = (
    "booking.com", "expedia.com", "hotels.com", "tripadvisor.com", "agoda.com",
    "airbnb.com", "vrbo.com", "trivago.com", "kayak.com", "priceline.com",
    "orbitz.com", "travelocity.com", "hotwire.com", "facebook.com",
    "instagram.com", "google.com", "yelp.com", "linktr.ee", "wixsite.com",
    "business.site", "sites.google.com",
)

#: Path shapes on a brand host that are an index, a locator or a search rather
#: than one hotel. Checked as whole path segments.
BRAND_INDEX_SEGMENTS = frozenset({
    "", "hotels", "hotel", "locations", "find-hotels", "search", "destinations",
    "our-hotels", "hotel-search", "explore", "offers", "deals", "home",
})


def normalize_source_url(url: str) -> str:
    """Drop referrer-tracking parameters and the fragment; keep everything else.

    Not a canonicaliser: scheme, host case and trailing slashes are left alone
    so a normalised URL still fetches exactly what the record said.
    """
    url = (url or "").strip()
    if not url:
        return ""
    parts = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(kept), ""))


def _host(url: str) -> str:
    return (urlsplit(url or "").hostname or "").lower()


def classify_url_shape(url: str) -> str:
    """What KIND of page this URL is, before anyone tries to fetch it."""
    if not (url or "").strip():
        return NO_URL
    host = _host(url)
    if not host:
        return NO_URL
    for third_party in THIRD_PARTY_HOSTS:
        if host == third_party or host.endswith("." + third_party):
            return THIRD_PARTY
    brand = brand_of(url)
    if brand.startswith(INDEPENDENT_PREFIX):
        # An independent's own domain. Any path is its own page; the source
        # discovery layer is what decides whether it is the POLICY page.
        return PROPERTY_PAGE
    parts = urlsplit(url)
    if "redirect" in parts.path.lower() or "redirect" in parts.query.lower():
        return BRAND_REDIRECT
    segments = [s for s in parts.path.split("/") if s]
    if not segments:
        return BRAND_INDEX
    # A brand property page always carries a property-identifying segment: a
    # hotel code, a slug with more than one word, or a numeric id. A path made
    # only of index words is a locator.
    meaningful = [s for s in segments if s.lower() not in BRAND_INDEX_SEGMENTS
                  and not re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", s.lower())]
    if not meaningful:
        return BRAND_INDEX
    return PROPERTY_PAGE


def route_row(row: Mapping, registry_doc: Optional[Mapping] = None) -> "OrderedDict":
    """One census row -> its brand, normalised URL, shape, route and state."""
    raw = (row.get("official_url") or "").strip()
    url = normalize_source_url(raw)
    shape = classify_url_shape(url)
    brand = brand_of(url) if url else "NO_URL"
    excluded = REGISTRY.excluded_brands(registry_doc)

    entry = OrderedDict((
        ("identity_key", row.get("identity_key", "")),
        ("canonical_name", row.get("canonical_name", "")),
        ("corridor", row.get("corridor", "")),
        ("discovered_url", raw),
        ("source_url", url),
        ("url_shape", shape),
        ("brand", brand),
    ))

    if shape == NO_URL:
        entry["routing_state"] = ROUTE_NEEDS_OFFICIAL_URL
        entry["why"] = "no official URL is known for this identity"
        return entry
    if shape == THIRD_PARTY:
        entry["routing_state"] = ROUTE_NEEDS_FIRST_PARTY_URL
        entry["why"] = ("the only URL on record is a third-party listing (%s); "
                        "a policy fact may only be read from the property's own "
                        "surface" % _host(url))
        return entry
    if brand in excluded:
        entry["routing_state"] = ROUTE_BRAND_EXCLUDED
        entry["why"] = "brand %s is excluded by the routing registry: %s" % (
            brand, excluded[brand])
        return entry
    if shape == BRAND_INDEX:
        entry["routing_state"] = ROUTE_NEEDS_PROPERTY_URL
        entry["why"] = ("the URL on record is a brand index, locator or search "
                        "page; it is property-specific for nobody")
        return entry

    route = REGISTRY.resolve(brand=brand, url=url,
                             identity_key=row.get("identity_key", ""),
                             registry=registry_doc)
    entry["routing_state"] = ROUTED
    entry["provider"] = route.provider
    entry["fallback_providers"] = list(route.fallback_providers)
    entry["ladder"] = list(route.ladder)
    entry["reader"] = route.reader
    entry["max_attempts_per_provider"] = route.max_attempts_per_provider
    entry["resolved_by"] = route.resolved_by
    entry["measured_by"] = route.measured_by
    entry["why"] = route.why
    return entry


def route_census(rows: Sequence[Mapping],
                 registry_doc: Optional[Mapping] = None) -> Tuple[List[Dict], "OrderedDict"]:
    """``(entries, summary)`` over every row handed in."""
    entries = [route_row(row, registry_doc) for row in rows]
    entries.sort(key=lambda e: e["identity_key"])
    shapes = Counter(e["url_shape"] for e in entries)
    states = Counter(e["routing_state"] for e in entries)
    brands = Counter(e["brand"] if not e["brand"].startswith(INDEPENDENT_PREFIX)
                     else "INDEPENDENT" for e in entries)
    providers = Counter(e.get("provider", "") for e in entries if e.get("provider"))
    summary = OrderedDict((
        ("contract", CONTRACT),
        ("count", len(entries)),
        ("url_shapes", OrderedDict(sorted(shapes.items()))),
        ("routing_states", OrderedDict(sorted(states.items()))),
        ("brands", OrderedDict(sorted(brands.items()))),
        ("providers", OrderedDict(sorted(providers.items()))),
        ("automatically_routed", states.get(ROUTED, 0)),
        ("automatically_routed_pct",
         round(100.0 * states.get(ROUTED, 0) / len(entries), 1) if entries else 0.0),
    ))
    return (entries, summary)


def known_brands() -> Tuple[str, ...]:
    return tuple(sorted({brand for _host, brand in BRAND_HOSTS}))
