"""PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001 -- Phase 11A: one first-party route per census identity.

The router needs a URL before it can choose a lane. This helper states, for every census identity the proposed
census ADMITTED, the first-party route it will be read at and which source stated it, in this order:

  1. the route the brand's own published inventory carries for the row (owned Marriott harvest, Marriott's California
     sitemap page, Hilton's city-page card, the brand sitemaps that answered);
  2. the website a destination bureau (Visit Carlsbad, Visit Oceanside) links for the listing joined to this
     building -- the partner's OWN outbound website, which is a first-party route and not a directory page;
  3. the website the map source (OSM) tags on the building.

Guards: a directory, social or OTA host is never a route; a brand LOCATOR INDEX is never a route; a route on a
host that serves a different chain than the hotel's own name is REJECTED; Marriott legacy / fact-sheet shapes
are repaired to the brand's current overview shape.

A route is bound to an identity by the source that stated it and is NOT confirmed until the page's own address,
phone or property code agrees -- that is the capture lane's job.

IDENTITY FILL: brand-roster rows the census could not place (a route and a name, no address) are routed too, so
the capture lane can read the address the property's OWN page states. A code selects; the page admits.

Nothing here fetches. Output:
  launch_packages/pettripfinder/markets/reports/san_diego_ca_routing_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-diego-ca"
SCHEMA = "ptf-market-routing/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "san-diego-ca.json")
OUT = os.path.join(REPORTS, "san_diego_ca_routing_001.json")

_NAME_FAMILY = [
    ("MARRIOTT", r"marriott|courtyard by marriott|courtyard marriott|courtyard san diego"
                 r"|courtyard by|residence inn|springhill|fairfield|towneplace|ac hotel|studiores|city express"
                 r"|aloft|westin|sheraton|moxy|element|renaissance|delta hotels|autograph"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tru |tapestry"
               r"|canopy|spark by|hgi"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental"
            r"|kimpton|hotel indigo"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay"
               r"|suburban|econo lodge|rodeway|woodspring|ascend"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel"
                r"|howard johnson|hawthorn|americinn|wingate|trademark"),
    ("ESA", r"extended stay america"),
    ("BEST_WESTERN", r"best western|surestay"),
    ("MOTEL6", r"motel 6|studio 6"),
    ("RED_ROOF", r"red roof|hometowne studios"),
    ("SONESTA", r"sonesta|americas best value|red lion|signature inn"),
    ("RADISSON", r"radisson|country inn"),
    ("DRURY", r"drury"),
    ("OMNI", r"\bomni\b"),
    ("LOEWS", r"\bloews\b"),
    ("HYATT", r"hyatt|thompson |andaz|caption by"),
]
_HOST_FAMILY = [
    ("MARRIOTT", r"marriott\.com"),
    ("HILTON", r"hilton\.com|\.hgi\.com|\.hilton\.com"),
    ("IHG", r"ihg\.com|holidayinn\.com|staybridge"),
    ("CHOICE", r"choicehotels\.com|woodspring\.com"),
    ("WYNDHAM", r"wyndhamhotels\.com"),
    ("ESA", r"extendedstayamerica\.com"),
    ("BEST_WESTERN", r"bestwestern\.com"),
    ("MOTEL6", r"motel6\.com"),
    ("RED_ROOF", r"redroof\.com|redroofinns\.com"),
    ("SONESTA", r"sonesta\.com"),
    ("RADISSON", r"radissonhotels\.com|countryinns\.com|countyinns\.com"),
    ("DRURY", r"druryhotels\.com"),
    ("OMNI", r"omnihotels\.com"),
    ("LOEWS", r"loewshotels\.com"),
    ("HYATT", r"hyatt\.com|thompsonhotels\.com"),
]


def _chain_of_name(name: str) -> str:
    n = (name or "").lower()
    for fam, rx in _NAME_FAMILY:
        if re.search(rx, n):
            return fam
    return ""


def _chain_of_host(url: str) -> str:
    h = (re.match(r"https?://([^/]+)", url or "") or [None, ""])[1].lower()
    for fam, rx in _HOST_FAMILY:
        if re.search(rx, h):
            return fam
    return ""


_NOT_A_PROPERTY_ROUTE = re.compile(
    r"(google\.com|facebook\.com|instagram\.com|tripadvisor|booking\.com|expedia|yelp\.com)", re.I)

_BRAND_LOCATOR_INDEX = re.compile(
    r"(/hotels/?$|-hotels/?$|/locations/?$|/find-hotels|/hotel-search|/destinations?/?$"
    r"|/city/?$|/state/?$|/search)", re.I)

_MARRIOTT_LEGACY = re.compile(
    r"^https?://(?:www\.)?marriott\.com/hotels/travel/([a-z0-9]{5,7})-([a-z0-9-]+)/?$", re.I)
_MARRIOTT_FACTSHEET = re.compile(
    r"^https?://(?:www\.)?marriott\.com/hotels/fact-sheet/travel/([a-z0-9]{5,7})-([a-z0-9-]+)/?$",
    re.I)
_MARRIOTT_BARE_CODE = re.compile(
    r"^https?://(?:www\.)?marriott\.com/([a-z0-9]{5,7})/?$", re.I)


def clean_url(url: str) -> str:
    u = (url or "").strip().replace("&#038;", "&").replace("&amp;", "&")
    u = re.sub(r"^(https?://)\s+", r"\1", u)
    return u.rstrip()


def repair_route(url: str, slug_hint: str = ""):
    m = _MARRIOTT_LEGACY.match(url or "")
    if m:
        return ("https://www.marriott.com/en-us/hotels/%s-%s/overview/"
                % (m.group(1).lower(), m.group(2).lower()),
                "MARRIOTT_LEGACY_TRAVEL_PATH_TO_CURRENT_OVERVIEW_PATH")
    m = _MARRIOTT_FACTSHEET.match(url or "")
    if m:
        return ("https://www.marriott.com/en-us/hotels/%s-%s/overview/"
                % (m.group(1).lower(), m.group(2).lower()),
                "MARRIOTT_FACT_SHEET_PATH_TO_CURRENT_OVERVIEW_PATH")
    m = _MARRIOTT_BARE_CODE.match(url or "")
    if m and slug_hint:
        return ("https://www.marriott.com/en-us/hotels/%s-%s/overview/"
                % (m.group(1).lower(), slug_hint),
                "MARRIOTT_BARE_PROPERTY_CODE_TO_CURRENT_OVERVIEW_PATH")
    return (url, "")


def route_class(url: str) -> str:
    h = (re.match(r"https?://([^/]+)", url or "") or [None, ""])[1].lower()
    if re.search(r"(marriott|hilton|ihg|holidayinn|choicehotels|wyndhamhotels|redroof|"
                 r"extendedstayamerica|bestwestern|hyatt|sonesta|motel6|radissonhotels|"
                 r"countryinns|drury|omnihotels|loewshotels|woodspring)\.", h):
        return "BRAND_FIRST_PARTY"
    if h.endswith(".hgi.com") or h.endswith(".hilton.com"):
        return "BRAND_FIRST_PARTY"
    return "INDEPENDENT_FIRST_PARTY"


ROUTED_OFFICIAL_INVENTORY = "ROUTED_OFFICIAL_INVENTORY"
ROUTED_OFFICIAL_DESTINATION = "ROUTED_OFFICIAL_DESTINATION"
ROUTED_MAP_WEBSITE = "ROUTED_MAP_WEBSITE"
FREE_LANE_EXHAUSTED = "FREE_LANE_EXHAUSTED"
INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
ROUTE_BRAND_MISMATCH = "ROUTE_BRAND_MISMATCH"
ROUTED_FOR_IDENTITY_FILL = "ROUTED_FOR_IDENTITY_FILL"

#: HOTELS.COM IS ANCHORED TO ITS OWN HOST LABEL. Unanchored, ``hotels\.com`` also matches choiceHOTELS.COM and
#: wyndhamHOTELS.COM, so every Choice and Wyndham brand-inventory route was refused as an OTA link and 12 branded
#: rows fell to FREE_LANE_EXHAUSTED (measured here; the Jacksonville module this was cloned from carries the same
#: pattern -- recorded as a finding, not touched by this order).
_NOT_A_PROPERTY_ROUTE = re.compile(
    r"(google\.|facebook\.com|instagram\.com|tripadvisor|booking\.com|expedia|yelp\.com|(?<![a-z0-9-])hotels\.com|kayak\.|"
    r"sandiego\.org|visitcarlsbad\.com|visitoceanside\.org|coronadovisitorcenter\.com|oyorooms\.com|bringfido|airbnb|vrbo|priceline|agoda|trivago|orbitz)", re.I)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _usable(url):
    url = clean_url(url or "")
    if not url.startswith("http") or _NOT_A_PROPERTY_ROUTE.search(url) or _BRAND_LOCATOR_INDEX.search(url):
        return ""
    return url


def candidates(h):
    cand = []
    for obs in h.get("evidence", []):
        if str(obs.get("lane", "")).startswith("BRAND_INVENTORY") and obs.get("route"):
            u = _usable(obs["route"])
            if u:
                cand.append((ROUTED_OFFICIAL_INVENTORY, u, obs.get("lane")))
    for obs in h.get("evidence", []):
        if obs.get("lane") == "DESTINATION_ORGANIZATION":
            # The bureau's OWN outbound link to the partner's site. Palm Beach's bureau published none, so the
            # prior helper only looked at `website_url`; all three bureaus here publish one, and the census
            # records it as the observation's `route`. Both spellings are read, and the field a bureau
            # actually used is recorded on the route.
            u = _usable(obs.get("website_url")) or _usable(obs.get("route"))
            if u:
                cand.append((ROUTED_OFFICIAL_DESTINATION, u, obs.get("source_url")))
    for obs in h.get("evidence", []):
        if obs.get("lane") == "OSM_OVERPASS":
            u = _usable(obs.get("website_url"))
            if u:
                cand.append((ROUTED_MAP_WEBSITE, u, obs.get("source_url")))
    # MIAMI: a competitor-gap identity verified by Places carries the website its own map card names.
    for obs in h.get("evidence", []):
        if obs.get("lane") == "IDENTITY_VERIFIED_PLACES":
            u = _usable(obs.get("website_url"))
            if u:
                cand.append((ROUTED_MAP_WEBSITE, u, obs.get("source_url")))
    seen, out = set(), []
    for c in cand:
        k = c[1].rstrip("/").lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out


def family_of_name(name):
    return _chain_of_name(name)


def family_of_host(url):
    return _chain_of_host(url)


def route_row(h, *, identity_fill=False):
    name = h["canonical_name"]
    cand, mismatch = [], None
    for c in candidates(h):
        nf, hf = family_of_name(name), family_of_host(c[1])
        if nf and hf and nf != hf:
            mismatch = OrderedDict([("rejected_url", c[1]), ("stated_by", c[2]), ("name_family", nf),
                                    ("host_family", hf),
                                    ("why", "a route on a %s host for a %s-named hotel would read another chain's page" % (hf, nf))])
            continue
        cand.append(c)
    rec = OrderedDict([
        ("identity_key", h["identity_key"]), ("canonical_name", name), ("classification", h.get("classification")),
        ("street", h.get("street", "")), ("city", h.get("city", "")), ("postal_code", h.get("postal_code", "")),
        ("phone", h.get("phone", "")), ("brand", h.get("brand", "")), ("brand_family", family_of_name(name)),
        ("property_code", h.get("property_code", "")), ("corridor", h.get("corridor", "")),
    ])
    if cand:
        state, url, by = cand[0]
        repaired, repair = repair_route(url, normalize_name(name).replace(" ", "-"))
        rec["routing_state"] = ROUTED_FOR_IDENTITY_FILL if identity_fill else state
        rec["url"] = repaired
        if repair:
            rec["route_repair"] = OrderedDict([("as_stated_by_source", url), ("repaired_to", repaired), ("repair", repair)])
        rec["route_stated_by"] = by
        rec["route_class"] = route_class(repaired)
        rec["alternate_routes"] = [c[1] for c in cand[1:]]
    else:
        rec["routing_state"] = (ROUTE_BRAND_MISMATCH if mismatch else
                                INDEPENDENT_REVIEW if not family_of_name(name) else FREE_LANE_EXHAUSTED)
        rec["url"] = ""
        rec["why_no_route"] = ("no first-party source in this order stated a usable route: no brand inventory row joined "
                               "the building, and neither the bureau nor the map source links the property's own page")
    if mismatch:
        rec["rejected_route"] = mismatch
    return rec


def build():
    census = _load(CENSUS, {}) or {}
    routes = [route_row(h) for h in census.get("hotels", [])]
    fill = []
    for h in census.get("non_admitted", []):
        if h.get("classification") not in ("NAME_ONLY_UNRESOLVED", "IDENTITY_REVIEW_REQUIRED"):
            continue
        if any(str(o.get("lane", "")).startswith("BRAND_INVENTORY") for o in h.get("evidence", [])):
            r = route_row(h, identity_fill=True)
        elif h.get("classification") == "IDENTITY_REVIEW_REQUIRED" and h.get("street"):
            r = route_row(h, identity_fill=True)
        else:
            continue
        if r.get("url"):
            fill.append(r)
    doc = OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "12A -- first-party route per census identity (router input)"),
        ("census_admitted", len(routes)),
        ("counts", OrderedDict([
            ("by_routing_state", OrderedDict(sorted(Counter(r["routing_state"] for r in routes).items()))),
            ("by_brand_family", OrderedDict(sorted(Counter(r["brand_family"] or "INDEPENDENT" for r in routes).items()))),
            ("identity_fill_routes", len(fill)),
            ("identity_fill_by_family", OrderedDict(sorted(Counter(r["brand_family"] or "INDEPENDENT" for r in fill).items()))),
        ])),
        ("routes", routes),
        ("identity_fill_routes", fill),
    ])
    return doc


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(doc["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
