"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- Phase 9, free routing.

For every confirmed Charlotte identity, the cheapest route that a FIRST-PARTY
source states. Nothing here guesses a URL from a name.

Route sources, in ladder order:

  1. ROUTED_OFFICIAL_DESTINATION -- the route an official Charlotte-area
     destination organisation links from a partner page. Toledo's CVB partner
     roster was the single most valuable rung in that market. Five of the seven
     organisations this order probed served a plain client, so this rung is live
     here; whatever it yields is recorded, and the two refusals are recorded as
     refusals rather than as absence.
  2. ROUTED_OFFICIAL_SITEMAP -- a Marriott route from the committed Dayton
     harvest (OWNED, zero requests), a Hilton route from Hilton's own Carolinas
     city pages, or a Wyndham, Sonesta, Omni or Drury route from the brand's own
     sitemap or city page.
  3. ROUTED_FREE_STATIC -- an independent property's own domain.

A ROUTE IS A PROPOSAL
---------------------
Every route here is bound to an identity and must still be CONFIRMED by the
page's own address, phone or property code when it is read. This is not
pedantry. Toledo's destination roster linked ``redroofinns.com`` from its
Baymont partner page -- a different chain entirely -- and only reading the page
caught it. The same guard runs here: a route whose HOST serves a different
chain than the hotel's NAME is rejected as ROUTE_BRAND_MISMATCH before it is
ever captured.

A CODE SELECTS, THE PAGE ADMITS
-------------------------------
Charlotte's CLT property-code prefix reaches Shelby, Statesville, Hickory,
Salisbury, Mooresville, Monroe and Gastonia. Rows
the census could not place are routed anyway, as IDENTITY_FILL, precisely so
the capture lane can read the address the property's OWN page states.

Nothing here fetches. Output is Charlotte-local.

Output:
  launch_packages/pettripfinder/markets/reports/charlotte_nc_routing_001.json
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

from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
SCHEMA = "ptf-market-routing/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
def _first_existing(*paths):
    """The registered path if this market has been promoted, else the proposed one."""
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[-1]

REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census", "charlotte-nc.json")
LEADS = os.path.join(REPORTS, "charlotte_nc_lead_sources_001.json")

OWNED_ROUTE_REUSED = "OWNED_ROUTE_REUSED"
ROUTED_OFFICIAL_DESTINATION = "ROUTED_OFFICIAL_DESTINATION"
ROUTED_OFFICIAL_SITEMAP = "ROUTED_OFFICIAL_SITEMAP"
ROUTED_FREE_STATIC = "ROUTED_FREE_STATIC"
FREE_LANE_EXHAUSTED = "FREE_LANE_EXHAUSTED"
INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
ROUTED_FOR_IDENTITY_FILL = "ROUTED_FOR_IDENTITY_FILL"
ROUTE_BRAND_MISMATCH = "ROUTE_BRAND_MISMATCH"

#: Which chain a hotel name belongs to, and which host serves that chain. A
#: route whose host serves a DIFFERENT chain than the name is not this hotel's
#: page. Measured in Toledo: that market's destination roster linked
#: redroofinns.com from its Baymont partner page.
_NAME_FAMILY = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel"
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

#: Hosts that are not a property's own page even when a directory links them.
_NOT_A_PROPERTY_ROUTE = re.compile(
    r"(google\.com|facebook\.com|instagram\.com|tripadvisor|booking\.com|expedia|yelp\.com)", re.I)

#: A brand LOCATOR INDEX, not a property page. The map source states
#: ``choicehotels.com/tennessee/white-house/quality-inn-hotels`` for a hotel in
#: CHARLOTTE: it is the brand's town index, it names the wrong town, and
#: capturing it would read a list as a policy. A directory URL is never a route.
_BRAND_LOCATOR_INDEX = re.compile(
    r"(/hotels/?$|-hotels/?$|/locations/?$|/find-hotels|/hotel-search|/destinations?/?$"
    r"|/city/?$|/state/?$|/search)", re.I)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


#: Marriott's LEGACY route shape. Directories still link hotels as
#: ``marriott.com/hotels/travel/<code>-<slug>``; Marriott's own current sitemap
#: publishes them as ``marriott.com/en-us/hotels/<code>-<slug>/overview/``. The
#: legacy shape still resolves, but the property-code parser does not read a
#: code from it, so every one of those rows was reported
#: PROPERTY_CODE_UNPARSEABLE_ROUTING_REPAIR_REQUIRED -- the Detroit PASS-008
#: failure class, which lost 49 of 65 attempts to exactly this. Repairing the
#: shape is free and is done from the brand's OWN published inventory.
_MARRIOTT_LEGACY = re.compile(
    r"^https?://(?:www\.)?marriott\.com/hotels/travel/([a-z0-9]{5,7})-([a-z0-9-]+)/?$", re.I)
#: Two more shapes the map source states for the same property: a FACT SHEET
#: path, and a bare property code with no slug at all. Both resolve, and
#: neither parses as a property code where the route table looks for one.
_MARRIOTT_FACTSHEET = re.compile(
    r"^https?://(?:www\.)?marriott\.com/hotels/fact-sheet/travel/([a-z0-9]{5,7})-([a-z0-9-]+)/?$",
    re.I)
_MARRIOTT_BARE_CODE = re.compile(
    r"^https?://(?:www\.)?marriott\.com/([a-z0-9]{5,7})/?$", re.I)


def clean_url(url: str) -> str:
    """A directory can print a route with a space or an HTML entity in it."""
    u = (url or "").strip().replace("&#038;", "&").replace("&amp;", "&")
    u = re.sub(r"^(https?://)\s+", r"\1", u)
    return u.rstrip()


def repair_route(url: str, slug_hint: str = ""):
    """The brand's own current canonical shape, and what was repaired."""
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


def cvb_routes():
    """Property routes the official destination organisation states.

    Five of the seven Charlotte-area destination organisations this order probed
    served a plain client, so this rung is LIVE here -- unlike Nashville, where
    every one refused. A link an organisation publishes is still a PROPOSAL: it
    is bound to an identity by name and confirmed by the page's own address when
    it is read, and the brand-mismatch guard runs on it exactly as on every
    other rung. Toledo's destination roster linked a different chain entirely
    from one partner page, which is why no rung is trusted for being official.
    """
    doc = _load(LEADS, {}) or {}
    out = {}
    for _org, block in (doc.get("destination_organisations") or {}).items():
        if not block.get("any_url_served"):
            continue
        for url in block.get("lodging_links") or []:
            url = clean_url(url)
            if not url or _NOT_A_PROPERTY_ROUTE.search(url):
                continue
            nm = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
            out[normalize_name(nm)] = OrderedDict([
                ("url", url), ("stated_by", block.get("attempts", [{}])[0].get("url", "")),
                ("street", ""), ("postal_code", ""), ("telephone", "")])
    return out


def brand_sitemap_routes():
    """``identity key -> route`` from the brand's own sitemap walk.

    Rung 2 alongside the owned Marriott harvest and Hilton's city pages. Keyed
    on the normalised name the route slug proposes, which is how the census
    already recorded the same observation, so the two meet on one key.
    """
    doc = _load(os.path.join(REPORTS, "charlotte_nc_brand_sitemaps_001.json"), {}) or {}
    out = {}
    for fam, block in (doc.get("families") or {}).items():
        for r in block.get("charlotte_routes") or []:
            url = clean_url(r.get("route") or "")
            if not url or _NOT_A_PROPERTY_ROUTE.search(url):
                continue
            tail = url.rstrip("/").rsplit("/", 1)[-1]
            if tail in ("overview", "hoteldetail"):
                tail = url.rstrip("/").split("/")[-2]
            nm = normalize_name(tail.replace("-", " "))
            if nm:
                out.setdefault(nm, OrderedDict([
                    ("url", url), ("stated_by", r.get("found_in", "")), ("family", fam)]))
    return out


def route_from_map_source(row):
    """A first-party website URL the MAP SOURCE states for this building.

    A large share of OpenStreetMap candidates carry a ``website_url``, and for
    several families -- IHG and Choice above all -- it is the only free route
    this order ever found: both refused this client on their city page AND on
    the sitemap their own robots.txt declares, measured by this run.

    It is a PROPOSAL like every other route. Two guards run before it is kept:
    a brand LOCATOR INDEX is rejected outright (the map source states
    a brand town index rather than a property page -- a list, and often the
    wrong town), and the shared
    name-family / host-family guard rejects a route on another chain's host.
    """
    for obs in row.get("evidence", []):
        if obs.get("lane") != "OSM_OVERPASS":
            continue
        url = clean_url(obs.get("website_url") or "")
        if not url or not url.startswith("http"):
            continue
        if _NOT_A_PROPERTY_ROUTE.search(url) or _BRAND_LOCATOR_INDEX.search(url):
            continue
        return url, obs.get("source_url") or "OpenStreetMap"
    return "", ""


def route_from_evidence(row):
    """A route the census row already carries, and where it came from."""
    for obs in row.get("evidence", []):
        if obs.get("lane") in ("BRAND_INVENTORY_OWNED", "BRAND_INVENTORY_CITY_PAGE") \
                and obs.get("route"):
            return obs["route"], obs["lane"], obs
    return "", "", None


def build():
    census = _load(CENSUS, {}) or {}
    cvb = cvb_routes()
    sitemap = brand_sitemap_routes()
    rows = []
    for h in census.get("hotels", []):
        key = h["identity_key"]
        name = h["canonical_name"]
        cand = []
        # 1. The official destination partner roster, matched on the CVB's own
        #    name for the property as it appears in this row's evidence.
        cvb_names = [normalize_name(o.get("name") or "") for o in h.get("evidence", [])
                     if o.get("lane") == "CVB_PARTNER"]
        for n in cvb_names:
            if n in cvb:
                cand.append((ROUTED_OFFICIAL_DESTINATION, cvb[n]["url"], cvb[n]["stated_by"]))
                break
        # 2. The brand's own published inventory: the route the census row
        #    already carries, then the brand sitemap walk, matched on any name
        #    this identity is known by.
        url, lane, obs = route_from_evidence(h)
        if url:
            cand.append((ROUTED_OFFICIAL_SITEMAP, url, obs.get("source_url") or url))
        for alias in [key] + list(h.get("identity_key_aliases") or []):
            hit = sitemap.get(alias)
            if hit and hit["url"] not in [c[1] for c in cand]:
                cand.append((ROUTED_OFFICIAL_SITEMAP, hit["url"], hit["stated_by"]))
                break
        # 3. The website the MAP SOURCE states for this building, last because
        #    it is the least authoritative of the three and the most likely to
        #    be a locator index.
        murl, mby = route_from_map_source(h)
        if murl and murl not in [c[1] for c in cand]:
            cand.append((ROUTED_FREE_STATIC, murl, mby))
        # A route whose host serves a different chain than the hotel's name is
        # not this hotel's page. Reject it here rather than capturing it and
        # publishing another chain's policy.
        mismatch = None
        keep = []
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
            chosen = (ROUTED_FREE_STATIC, chosen[1], chosen[2])
        rec = OrderedDict([
            ("identity_key", key), ("canonical_name", name),
            ("street", h["street"]), ("city", h["city"]), ("postal_code", h["postal_code"]),
            ("phone", h["phone"]), ("brand", h["brand"]), ("property_code", h["property_code"]),
            ("corridor", h["corridor"]),
        ])
        if chosen:
            repaired, repair = repair_route(chosen[1], normalize_name(name).replace(" ", "-"))
            rec["routing_state"] = chosen[0]
            rec["url"] = repaired
            if repair:
                rec["route_repair"] = OrderedDict([
                    ("as_stated_by_source", chosen[1]), ("repaired_to", repaired),
                    ("repair", repair),
                    ("why", "the brand's own published inventory uses this shape, and the "
                            "property-code parser reads a code only from it")])
            rec["route_stated_by"] = chosen[2]
            rec["route_class"] = route_class(chosen[1])
            rec["alternate_routes"] = [c[1] for c in cand[1:]]
            rec["binding_caveat"] = (
                "This route is bound to this identity by the source that stated it. It is NOT "
                "confirmed until the page's own address, phone or property code agrees. "
                "Toledo's destination roster linked redroofinns.com from a Baymont partner "
                "page, a different chain, and only reading the page caught that.")
        else:
            rec["routing_state"] = (ROUTE_BRAND_MISMATCH if mismatch
                                    else INDEPENDENT_REVIEW if not h["brand"]
                                    else FREE_LANE_EXHAUSTED)
            rec["url"] = ""
            rec["why_no_route"] = (
                "no first-party source in this order stated a route for this identity: the "
                "destination roster does not carry it and its brand's published inventory was "
                "either not owned or not readable free")
        if mismatch:
            rec["rejected_route"] = mismatch
        rows.append(rec)

    # Brand roster rows this order found but could not yet place: the brand's
    # own published inventory states the property exists and gives its canonical
    # route, but no source gave it an address, so market membership is undecided.
    # Routing them is what lets the capture lane read the address off the
    # property's OWN page -- a code SELECTS, the page ADMITS.
    fill = []
    recon = _load(os.path.join(REPORTS, "charlotte_nc_census_reconciliation_001.json"), {}) or {}
    placed = {r["identity_key"] for r in rows}
    for x in recon.get("rows", []):
        if x["classification"] != "NAME_ONLY_UNRESOLVED" or not x.get("official_url"):
            continue
        if x["identity_key"] in placed:
            continue
        url = clean_url(x["official_url"])
        if url.rstrip("/").endswith("/hotels"):
            continue        # a brand locator index, not a property page
        fill.append(OrderedDict([
            ("identity_key", x["identity_key"]), ("canonical_name", x["canonical_name"]),
            ("brand", x["brand"]), ("property_code", x["property_code"]),
            ("routing_state", ROUTED_FOR_IDENTITY_FILL),
            ("url", url), ("route_stated_by", x["lanes"]),
            ("route_class", route_class(url)),
            ("why", "the brand's own published inventory names this property and gives this "
                    "route; no source in this order gave it an address, so it is captured to "
                    "read the address the property's own page states. It is NOT in the census "
                    "and it publishes nothing until that read admits it."),
        ]))

    counts = Counter(r["routing_state"] for r in rows)
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9 -- free routing"),
        ("lane", "LOCAL_FREE_DISCOVERY / OWNED_EVIDENCE"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("http_requests", 0),
        ("a_route_is_a_proposal",
         "Every route here is bound to the identity the stating source named, and is confirmed "
         "only when the page's own address, phone or property code agrees. Toledo's destination "
         "roster linked redroofinns.com from a Baymont partner page; a routing lane that did not "
         "carry the identity forward would have captured a Red Roof page as a Baymont policy. "
         "Charlotte adds its own reason: the CLT property-code prefix reaches Shelby, "
         "Statesville, Hickory, Salisbury, Mooresville and Monroe, so a route selected by code "
         "is a proposal until the page states an address."),
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
    ap.add_argument("--out", default=os.path.join(REPORTS, "charlotte_nc_routing_001.json"))
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
    print("written      :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
