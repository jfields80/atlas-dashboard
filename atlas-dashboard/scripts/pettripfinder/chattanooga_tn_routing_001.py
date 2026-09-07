"""PTF-CHATTANOOGA-TN-NEW-MARKET-001 -- Phase 10, free routing.

For every confirmed Chattanooga identity, the cheapest route a FIRST-PARTY
source states. Nothing here guesses a URL from a name and nothing here fetches.

Route sources, in ladder order:

  1. OWNED_ROUTE_REUSED -- a Marriott property route already committed to this
     repository in ``dayton_oh_brand_directory_harvest_001.json``. Zero requests
     and zero risk of a new refusal.
  2. ROUTED_OFFICIAL_SITEMAP -- a route from a brand's OWN published inventory
     read this run: Hilton's Chattanooga city page, Wyndham's per-brand property
     sitemaps, and the Drury, Sonesta and WoodSpring city pages.
  3. ROUTED_FREE_STATIC -- a property's own domain, from a first-party capture
     or from OpenStreetMap's ``website`` tag. The map tag sits at the BOTTOM of
     the ladder because volunteered data is weaker than a brand's own published
     inventory, but it is the only free lane that reaches an INDEPENDENT hotel's
     own site, which no brand inventory can.

WHY THERE IS NO DESTINATION-BUREAU ROUTING RUNG HERE
----------------------------------------------------
Toledo's best routing lane was the destination bureau's Website button, which
carried canonical IHG, Choice and Red Roof property routes. The Chattanooga
Tourism Co. serves that button through a click-counting redirect under
``/plugins/crm/count/``, and its own robots.txt disallows that path. This order
does not fetch it. The bureau is therefore an IDENTITY lane in this market and
not a routing lane, which is exactly why IHG, Choice, Red Roof, Best Western and
Extended Stay America stay unrouted after the free lanes and become the measured
Firecrawl and attended cohort.

A ROUTE IS A PROPOSAL
---------------------
Every route is bound to the identity the stating source named and is CONFIRMED
only when the page's own address, phone or property code agrees. A route whose
host serves a different chain than the hotel's name is rejected here rather than
captured, because capturing it would read another chain's page and publish it.

Output:
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_routing_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.site_data import normalize_name  # noqa: E402,F401

WORK_ORDER = "PTF-CHATTANOOGA-TN-NEW-MARKET-001"
MARKET_ID = "chattanooga-tn"
SCHEMA = "ptf-market-routing/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")


def _first_existing(*paths):
    """The registered path if this market has been promoted, else the proposed one."""
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[-1]


REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = _first_existing(os.path.join(PKG, "identity_census", "chattanooga-tn.json"),
                         os.path.join(PKG, "identity_census_proposed", "chattanooga-tn.json"))
RECON = os.path.join(REPORTS, "chattanooga_tn_census_reconciliation_001.json")

OWNED_ROUTE_REUSED = "OWNED_ROUTE_REUSED"
ROUTED_OFFICIAL_SITEMAP = "ROUTED_OFFICIAL_SITEMAP"
ROUTED_FREE_STATIC = "ROUTED_FREE_STATIC"
FREE_LANE_EXHAUSTED = "FREE_LANE_EXHAUSTED"
INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
ROUTED_FOR_IDENTITY_FILL = "ROUTED_FOR_IDENTITY_FILL"
ROUTE_BRAND_MISMATCH = "ROUTE_BRAND_MISMATCH"

_NAME_FAMILY = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel"
                 r"|aloft|westin|sheraton|moxy|element|renaissance|delta hotels|autograph"
                 r"|tribute|kinley|edwin|dwell"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tru |tapestry"
               r"|canopy|spark by|hgi|garden inn"),
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
    ("HYATT", r"hyatt|caption by"),
    ("INTOWN", r"intown suites"),
]
_HOST_FAMILY = [
    ("MARRIOTT", r"marriott\.com"),
    ("HILTON", r"hilton\.com|\.hgi\.com"),
    ("IHG", r"ihg\.com|holidayinn\.com|staybridge"),
    ("CHOICE", r"choicehotels\.com|woodspring\.com"),
    ("WYNDHAM", r"wyndhamhotels\.com"),
    ("ESA", r"extendedstayamerica\.com"),
    ("BEST_WESTERN", r"bestwestern\.com"),
    ("MOTEL6", r"motel6\.com|g6hospitality\.com"),
    ("RED_ROOF", r"redroof\.com|redroofinns\.com"),
    ("SONESTA", r"sonesta\.com"),
    ("RADISSON", r"radissonhotels\.com|countryinns\.com"),
    ("DRURY", r"druryhotels\.com"),
    ("HYATT", r"hyatt\.com"),
    ("INTOWN", r"intownsuites\.com"),
]

_NOT_A_PROPERTY_ROUTE = re.compile(
    r"(google\.com|facebook\.com|instagram\.com|tripadvisor|booking\.com|expedia|yelp\.com"
    r"|visitchattanooga\.com)", re.I)

#: A brand LOCATOR index, not a property page. Routing one of these would send
#: the capture lane to a LIST of hotels and let it read whichever policy the
#: list happens to print -- which is exactly what this run's first pass did:
#: OpenStreetMap's website tag for the WoodSpring Suites node is the brand's
#: Chattanooga CITY page, and the capture lane read a clean "no pets" off it and
#: offered it as this property's policy. A directory URL is never a route.
_LOCATOR_INDEX = re.compile(
    r"/(hotels|locations|find-hotels|hotel-search|search|destinations)/?$", re.I)


def is_locator_for_city(url: str, city: str) -> bool:
    """True when the URL's last segment is just the TOWN, not this property.

    ``woodspring.com/extended-stay-hotels/locations/tennessee/chattanooga/`` names
    a city, not a building. A property route's own last segment names the
    property.
    """
    last = (url or "").rstrip("/").rsplit("/", 1)[-1].lower()
    town = re.sub(r"[^a-z0-9]+", "-", (city or "").strip().lower()).strip("-")
    return bool(town) and last == town


def family_of_name(name: str) -> str:
    n = (name or "").lower()
    for fam, rx in _NAME_FAMILY:
        if re.search(rx, n):
            return fam
    return ""


def family_of_host(url: str) -> str:
    h = (re.match(r"https?://([^/]+)", url or "") or [None, ""])[1].lower()
    for fam, rx in _HOST_FAMILY:
        if re.search(rx, h):
            return fam
    return ""


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


#: Marriott's LEGACY route shape. The current sitemap shape is the only one the
#: property-code parser reads a code from; the legacy shape produced the Detroit
#: PASS-008 failure class (49 of 65 attempts lost to an unparseable code).
_MARRIOTT_LEGACY = re.compile(
    r"^https?://(?:www\.)?marriott\.com/hotels/travel/([a-z0-9]{5,7})-([a-z0-9-]+)/?$", re.I)
#: A non-en-us locale is NORMALISED, never dropped: some Marriott properties are
#: published only under /en-gb/, and dropping the row loses a real hotel.
_MARRIOTT_LOCALE = re.compile(r"^(https?://(?:www\.)?marriott\.com)/en-(?!us)[a-z]{2}/(.*)$", re.I)


def clean_url(url: str) -> str:
    u = (url or "").strip().replace("&#038;", "&").replace("&amp;", "&")
    u = re.sub(r"^(https?://)\s+", r"\1", u)
    return u.rstrip()


def repair_route(url: str):
    """The brand's own current canonical shape, and what was repaired."""
    m = _MARRIOTT_LEGACY.match(url or "")
    if m:
        return ("https://www.marriott.com/en-us/hotels/%s-%s/overview/"
                % (m.group(1).lower(), m.group(2).lower()),
                "MARRIOTT_LEGACY_TRAVEL_PATH_TO_CURRENT_OVERVIEW_PATH")
    m = _MARRIOTT_LOCALE.match(url or "")
    if m:
        return ("%s/en-us/%s" % (m.group(1), m.group(2)),
                "MARRIOTT_NON_EN_US_LOCALE_NORMALISED_TO_EN_US")
    return (url, "")


def route_class(url: str) -> str:
    h = (re.match(r"https?://([^/]+)", url or "") or [None, ""])[1].lower()
    if re.search(r"(marriott|hilton|ihg|holidayinn|choicehotels|wyndhamhotels|redroof|"
                 r"extendedstayamerica|bestwestern|hyatt|sonesta|motel6|g6hospitality|"
                 r"radissonhotels|countryinns|drury|woodspring|intownsuites)\.", h):
        return "BRAND_FIRST_PARTY"
    if h.endswith(".hgi.com") or h.endswith(".hilton.com"):
        return "BRAND_FIRST_PARTY"
    return "INDEPENDENT_FIRST_PARTY"


#: Which lane a route came from, and therefore which routing state it earns.
_OWNED_LANES = {"BRAND_INVENTORY_OWNED"}
_SITEMAP_LANES = {"BRAND_INVENTORY_CITY_PAGE", "BRAND_INVENTORY_SITEMAP"}
#: OpenStreetMap's ``website`` tag. It is the ONLY free lane that supplies an
#: independent hotel's own domain, which no brand inventory can, so it is kept --
#: at the BOTTOM of the ladder, because a map tag is volunteered data and a
#: brand's own published inventory is not. The capture lane confirms it on the
#: page's own address like every other route.
_MAP_LANES = {"OSM_LOCAL_EXTRACT"}


def routes_from_evidence(row):
    """Every first-party route this census row already carries, cheapest first."""
    owned, sitemap, page, mapped = [], [], [], []
    for obs in row.get("evidence", []):
        url = clean_url(obs.get("route") or "")
        if not url or _NOT_A_PROPERTY_ROUTE.search(url) or _LOCATOR_INDEX.search(url):
            continue
        if is_locator_for_city(url, row.get("city") or ""):
            continue
        lane = obs.get("lane") or ""
        if lane in _OWNED_LANES:
            owned.append((OWNED_ROUTE_REUSED, url, obs.get("source_url") or url, lane))
        elif lane in _SITEMAP_LANES:
            sitemap.append((ROUTED_OFFICIAL_SITEMAP, url, obs.get("source_url") or url, lane))
        elif lane.startswith("PROPERTY_PAGE"):
            page.append((ROUTED_FREE_STATIC, url, obs.get("source_url") or url, lane))
        elif lane in _MAP_LANES:
            mapped.append((ROUTED_FREE_STATIC, url, obs.get("source_url") or url, lane))
    return owned + sitemap + page + mapped


def build():
    census = _load(CENSUS, {}) or {}
    rows = []
    for h in census.get("hotels", []):
        name = h["canonical_name"]
        cand = routes_from_evidence(h)
        mismatch, keep = None, []
        for c in cand:
            nf, hf = family_of_name(name), family_of_host(c[1])
            if nf and hf and nf != hf:
                mismatch = OrderedDict([
                    ("rejected_url", c[1]), ("stated_by", c[2]),
                    ("name_family", nf), ("host_family", hf),
                    ("why", "the source states a route on a host that serves %s while this hotel "
                            "is a %s property; capturing it would read another chain's page"
                            % (hf, nf))])
                continue
            keep.append(c)
        cand = keep
        chosen = cand[0] if cand else None
        if chosen and route_class(chosen[1]) == "INDEPENDENT_FIRST_PARTY":
            chosen = (ROUTED_FREE_STATIC, chosen[1], chosen[2], chosen[3])
        rec = OrderedDict([
            ("identity_key", h["identity_key"]), ("canonical_name", name),
            ("street", h["street"]), ("city", h["city"]), ("postal_code", h["postal_code"]),
            ("phone", h["phone"]), ("brand", h["brand"]),
            ("property_code", h["property_code"]), ("corridor", h["corridor"]),
        ])
        if chosen:
            repaired, repair = repair_route(chosen[1])
            rec["routing_state"] = chosen[0]
            rec["url"] = repaired
            if repair:
                rec["route_repair"] = OrderedDict([
                    ("as_stated_by_source", chosen[1]), ("repaired_to", repaired),
                    ("repair", repair),
                    ("why", "the brand's own published inventory uses this shape, and the "
                            "property-code parser reads a code only from it")])
            rec["route_stated_by"] = chosen[2]
            rec["route_lane"] = chosen[3]
            rec["route_class"] = route_class(repaired)
            rec["alternate_routes"] = [c[1] for c in cand[1:]]
            rec["binding_caveat"] = (
                "This route is bound to this identity by the source that stated it. It is NOT "
                "confirmed until the page's own address, phone or property code agrees.")
        else:
            # A row whose NAME belongs to a chain is a brand row even when no
            # lane set its brand field: the free lanes simply never reached it.
            # Calling that INDEPENDENT_REVIEW would hide a whole refused family.
            rec["routing_state"] = (ROUTE_BRAND_MISMATCH if mismatch
                                    else FREE_LANE_EXHAUSTED
                                    if (h["brand"] or family_of_name(name))
                                    else INDEPENDENT_REVIEW)
            rec["url"] = ""
            rec["why_no_route"] = (
                "no first-party source in this order stated a route for this identity. The "
                "destination bureau's Website button is robots-disallowed here, so a brand whose "
                "own site refuses a plain client (IHG, Choice, Red Roof, Best Western, Extended "
                "Stay America) has no free routing rung left and becomes Firecrawl or attended "
                "cohort.")
        if mismatch:
            rec["rejected_route"] = mismatch
        rows.append(rec)

    # Brand roster rows this order found but could not yet place. The brand's own
    # inventory states the property exists and gives its canonical route, but no
    # source gave it an address, so membership is undecided. Routing them lets
    # the capture lane read the address off the property's OWN page: a code
    # SELECTS, the page ADMITS.
    fill = []
    recon = _load(RECON, {}) or {}
    placed = {r["identity_key"] for r in rows}
    non_admitted = (_load(CENSUS, {}) or {}).get("non_admitted") or []
    for x in non_admitted:
        if x["classification"] != "NAME_ONLY_UNRESOLVED" or not x.get("official_url"):
            continue
        if x["identity_key"] in placed:
            continue
        url = clean_url(x["official_url"])
        if _LOCATOR_INDEX.search(url) or _NOT_A_PROPERTY_ROUTE.search(url):
            continue
        if is_locator_for_city(url, x.get("city") or ""):
            continue
        repaired, repair = repair_route(url)
        fill.append(OrderedDict([
            ("identity_key", x["identity_key"]), ("canonical_name", x["canonical_name"]),
            ("brand", x["brand"]), ("property_code", x["property_code"]),
            ("routing_state", ROUTED_FOR_IDENTITY_FILL),
            ("url", repaired), ("route_repair", repair),
            ("route_stated_by", x["lanes"]), ("route_class", route_class(repaired)),
            ("why", "the brand's own published inventory names this property and gives this "
                    "route; no source in this order gave it an address, so it is captured to "
                    "read the address the property's own page states. It is NOT in the census "
                    "and it publishes nothing until that read admits it."),
        ]))

    counts = Counter(r["routing_state"] for r in rows)
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "10 -- free routing"),
        ("lane", "OWNED_EVIDENCE / LOCAL_FREE_DISCOVERY"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("http_requests", 0),
        ("a_route_is_a_proposal",
         "Every route here is bound to the identity the stating source named, and is confirmed "
         "only when the page's own address, phone or property code agrees."),
        ("no_destination_bureau_routing_rung",
         "The Chattanooga Tourism Co. serves its Website button through a /plugins/crm/count/ "
         "click redirect that its own robots.txt disallows, so unlike Toledo this market has no "
         "free bureau routing rung. That is the measured reason IHG, Choice, Red Roof, Best "
         "Western and Extended Stay America stay unrouted after the free lanes."),
        ("counts", OrderedDict([
            ("confirmed_identities", len(rows)),
            ("by_routing_state", OrderedDict(sorted(counts.items()))),
            ("by_route_class", OrderedDict(sorted(
                Counter(r.get("route_class", "NONE") for r in rows).items()))),
            ("routed", sum(1 for r in rows if r.get("url"))),
            ("unrouted", sum(1 for r in rows if not r.get("url"))),
            ("identity_fill_routes", len(fill)),
        ])),
        ("routes", rows),
        ("identity_fill_routes", fill),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "chattanooga_tn_routing_001.json"))
    args = ap.parse_args(argv)
    rep = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    print("identities   :", c["confirmed_identities"])
    print("routed       :", c["routed"], "unrouted:", c["unrouted"])
    print("by state     :", dict(c["by_routing_state"]))
    print("by class     :", dict(c["by_route_class"]))
    print("fill routes  :", c["identity_fill_routes"])
    print("written      :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
