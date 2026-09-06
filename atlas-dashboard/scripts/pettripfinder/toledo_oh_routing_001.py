"""PTF-TOLEDO-OH-NEW-MARKET-001 -- Phase 9, free routing.

For every confirmed Toledo identity, the cheapest route that a FIRST-PARTY
source states. Nothing here guesses a URL from a name.

Route sources, in ladder order:

  1. ROUTED_OFFICIAL_DESTINATION -- the route Destination Toledo's own partner
     page links from its Website button. This turned out to be the single most
     valuable rung in the market: it supplies canonical IHG, Choice, Red Roof
     and Extended Stay America property routes -- ``.../maumee/toltd/hoteldetail``,
     ``choicehotels.com/ohio/oregon/comfort-inn-hotels/oh073``,
     ``redroof.com/property/oh/maumee/RRI046`` -- for four brands whose own
     sites refuse this client outright.
  2. ROUTED_OFFICIAL_SITEMAP -- a Marriott or Wyndham property URL from the
     committed Dayton/Cleveland harvests, or a Hilton route from Hilton's own
     Toledo city page.
  3. ROUTED_FREE_STATIC -- an independent property's own domain, as the CVB
     states it.

A ROUTE IS A PROPOSAL
---------------------
Every route here is bound to an identity and must still be CONFIRMED by the
page's own address, phone or property code when it is read. This is not
pedantry: Destination Toledo's Baymont Holland/Toledo partner page links
``redroofinns.com``, a different chain entirely. The capture lane is what
catches that, and it can only catch it because the route carries the identity
it claims to serve.

Nothing here fetches. Output is Toledo-local.

Output:
  launch_packages/pettripfinder/markets/reports/toledo_oh_routing_001.json
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

WORK_ORDER = "PTF-TOLEDO-OH-NEW-MARKET-001"
MARKET_ID = "toledo-oh"
SCHEMA = "ptf-market-routing/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "toledo-oh.json")
LEADS = os.path.join(REPORTS, "toledo_oh_lead_sources_001.json")

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
#: page: Destination Toledo's Baymont Holland/Toledo partner page links
#: redroofinns.com.
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


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


#: Marriott's LEGACY route shape. Destination Toledo links ten Toledo hotels as
#: ``marriott.com/hotels/travel/<code>-<slug>``; Marriott's own current sitemap
#: publishes them as ``marriott.com/en-us/hotels/<code>-<slug>/overview/``. The
#: legacy shape still resolves, but the property-code parser does not read a
#: code from it, so every one of those rows was reported
#: PROPERTY_CODE_UNPARSEABLE_ROUTING_REPAIR_REQUIRED -- the Detroit PASS-008
#: failure class, which lost 49 of 65 attempts to exactly this. Repairing the
#: shape is free and is done from the brand's OWN published inventory.
_MARRIOTT_LEGACY = re.compile(
    r"^https?://(?:www\.)?marriott\.com/hotels/travel/([a-z0-9]{5,7})-([a-z0-9-]+)/?$", re.I)


def clean_url(url: str) -> str:
    """Destination Toledo prints at least one route with a space in it."""
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
    return (url, "")


def route_class(url: str) -> str:
    h = (re.match(r"https?://([^/]+)", url or "") or [None, ""])[1].lower()
    if re.search(r"(marriott|hilton|ihg|holidayinn|choicehotels|wyndhamhotels|redroof|"
                 r"extendedstayamerica|bestwestern|hyatt|sonesta|motel6|radissonhotels|"
                 r"countryinns|drury)\.", h):
        return "BRAND_FIRST_PARTY"
    if h.endswith(".hgi.com") or h.endswith(".hilton.com"):
        return "BRAND_FIRST_PARTY"
    return "INDEPENDENT_FIRST_PARTY"


def cvb_routes():
    doc = _load(LEADS, {}) or {}
    out = {}
    for r in ((doc.get("official_destination_partner_roster") or {}).get("rows") or []):
        url = clean_url(r.get("official_url") or "")
        if not url or _NOT_A_PROPERTY_ROUTE.search(url):
            continue
        nm = (r.get("name") or "").replace("&#038;", "&").replace("&amp;", "&")
        out[normalize_name(nm)] = OrderedDict([
            ("url", url), ("stated_by", r["url"]),
            ("street", r.get("street", "")), ("postal_code", r.get("postal_code", "")),
            ("telephone", r.get("telephone", "")),
        ])
    return out


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
        # 2. The brand's own published inventory.
        url, lane, obs = route_from_evidence(h)
        if url:
            cand.append((ROUTED_OFFICIAL_SITEMAP, url, obs.get("source_url") or url))
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
            rec["route_class"] = route_class(chosen[1])
            rec["alternate_routes"] = [c[1] for c in cand[1:]]
            rec["binding_caveat"] = (
                "This route is bound to this identity by the source that stated it. It is NOT "
                "confirmed until the page's own address, phone or property code agrees: "
                "Destination Toledo's Baymont Holland/Toledo partner page links redroofinns.com, "
                "a different chain, and only reading the page catches that.")
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
    recon = _load(os.path.join(REPORTS, "toledo_oh_census_reconciliation_001.json"), {}) or {}
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
         "only when the page's own address, phone or property code agrees. Destination Toledo's "
         "Baymont Holland/Toledo partner page links redroofinns.com; a routing lane that did not "
         "carry the identity forward would have captured a Red Roof page as a Baymont policy."),
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
    ap.add_argument("--out", default=os.path.join(REPORTS, "toledo_oh_routing_001.json"))
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
