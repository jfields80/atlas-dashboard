"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- Phases 4C and 7, rung 1: the
brand's own city page, and the brand inventory audit that rests on it.

WHY A CITY PAGE AND NOT A SITEMAP WALK
--------------------------------------
Toledo killed a Hilton sitemap walk at 25 minutes having produced nothing, then
got every TOL code from ``hilton.com/en/locations/usa/ohio/toledo/`` in ONE
request. Nashville repeated the measurement across sixteen city pages. Rung
order here: owned harvest, brand city page, bounded sitemap, then say you could
not.

A REFUSAL IS A FACT ABOUT A MOMENT
----------------------------------
Every family the committed harvests recorded as refusing a plain client is
RE-PROBED here, against both the ``www.`` and bare hostnames. Those refusals are
days old and are not inherited.

A CODE SELECTS; THE PAGE ADMITS
-------------------------------
Charlotte's Marriott/Hilton prefix is CLT -- an AIRPORT code that serves most of
the western Piedmont. The committed Dayton roster harvest proves it reaches
Shelby (``cltby``), Statesville (``cltfv``), Hickory (``cltht``), Salisbury
(``cltsb``), Mooresville, Monroe and Gastonia. Nothing here admits a property.
Every code found is carried into routing and judged on the postal code its OWN
page states, against the corridor registry in the market contract.

TWO STATES
----------
Charlotte is the first PetTripFinder market whose traveler geography crosses a
state line. Every brand that files rosters by state is therefore asked twice --
North Carolina and South Carolina -- because Fort Mill, Tega Cay and Indian Land
are admitted corridors and Rock Hill is a founder hold that must be MEASURED.

A BRAND ROSTER WITH NO ENTRY IS NOT A CLOSURE
---------------------------------------------
A city with no brand page, or a roster with no row, is a statement about the
ROSTER. It is never proof that a building closed.

No paid provider is called. Output is Charlotte-local.

Output:
  launch_packages/pettripfinder/markets/reports/charlotte_nc_brand_city_pages_001.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
SCHEMA = "ptf-brand-city-page-inventory/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "charlotte_nc_brand_city_pages_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 0.4

#: Hilton names its location pages by state slug and city slug. These are this
#: market's own municipalities plus the held fringe towns, fetched so the hold
#: rests on evidence. A city Hilton does not publish simply 404s: a fact about
#: the roster, not about a building.
HILTON_CITIES = [
    ("north-carolina", "charlotte"),
    ("north-carolina", "pineville"),
    ("north-carolina", "matthews"),
    ("north-carolina", "mint-hill"),
    ("north-carolina", "huntersville"),
    ("north-carolina", "cornelius"),
    ("north-carolina", "davidson"),
    ("north-carolina", "concord"),
    ("north-carolina", "harrisburg"),
    ("north-carolina", "belmont"),
    ("north-carolina", "gastonia"),
    ("north-carolina", "kannapolis"),
    ("north-carolina", "mooresville"),
    ("north-carolina", "monroe"),
    ("north-carolina", "indian-trail"),
    ("north-carolina", "waxhaw"),
    ("south-carolina", "fort-mill"),
    ("south-carolina", "tega-cay"),
    ("south-carolina", "rock-hill"),
    ("south-carolina", "indian-land"),
    ("south-carolina", "lancaster"),
]
HILTON_CITY_URL = "https://www.hilton.com/en/locations/usa/%s/%s/"
HILTON_CODE = re.compile(r"/en/hotels/([a-z0-9]{4,9})-([a-z0-9-]+)/", re.I)
CODE_PREFIX = "clt"

#: Families earlier markets recorded as refusing a plain client. Re-probed
#: against BOTH hostnames; see the module docstring.
REFUSAL_REPROBE = OrderedDict([
    ("IHG", ["https://www.ihg.com/robots.txt", "https://ihg.com/robots.txt"]),
    ("CHOICE", ["https://www.choicehotels.com/robots.txt",
                "https://choicehotels.com/robots.txt"]),
    ("BEST_WESTERN", ["https://www.bestwestern.com/robots.txt",
                      "https://bestwestern.com/robots.txt"]),
    ("ESA", ["https://www.extendedstayamerica.com/robots.txt",
             "https://extendedstayamerica.com/robots.txt"]),
    ("RED_ROOF", ["https://www.redroof.com/robots.txt", "https://redroof.com/robots.txt"]),
    ("MOTEL6", ["https://www.motel6.com/robots.txt", "https://motel6.com/robots.txt"]),
    ("HYATT", ["https://www.hyatt.com/robots.txt", "https://hyatt.com/robots.txt"]),
    ("RADISSON", ["https://www.radissonhotels.com/robots.txt"]),
    ("HILTON", ["https://www.hilton.com/robots.txt"]),
    ("MARRIOTT", ["https://www.marriott.com/robots.txt"]),
    ("WYNDHAM", ["https://www.wyndhamhotels.com/robots.txt"]),
    ("SONESTA", ["https://www.sonesta.com/robots.txt"]),
    ("DRURY", ["https://www.druryhotels.com/robots.txt"]),
    ("WOODSPRING", ["https://www.woodspring.com/robots.txt"]),
    ("OMNI", ["https://www.omnihotels.com/robots.txt"]),
    ("LOEWS", ["https://www.loewshotels.com/robots.txt"]),
    ("KIMPTON", ["https://www.kimptonhotels.com/robots.txt"]),
])

#: City/state roster pages, and the regex that reads a PROPERTY route out of
#: each. Deliberately generous patterns: a page that renders its list
#: client-side yields nothing and is recorded as such, which is itself the
#: finding that sends the family down the ladder.
CITY_PAGES = OrderedDict([
    ("WYNDHAM_NC", ("https://www.wyndhamhotels.com/hotels/charlotte-north-carolina",
                    r'href="(https://www\.wyndhamhotels\.com/[a-z0-9-]+/[a-z0-9-]+-north-carolina/[^"]+/overview)"')),
    ("WYNDHAM_SC", ("https://www.wyndhamhotels.com/hotels/fort-mill-south-carolina",
                    r'href="(https://www\.wyndhamhotels\.com/[a-z0-9-]+/[a-z0-9-]+-south-carolina/[^"]+/overview)"')),
    ("DRURY", ("https://www.druryhotels.com/locations/charlotte-nc",
               r'href="(/locations/[a-z0-9-]+-[ns]c/[^"?#]+)"')),
    ("CHOICE_NC", ("https://www.choicehotels.com/north-carolina/charlotte/hotels",
                   r'href="(/north-carolina/[a-z0-9-]+/[a-z0-9-]+/hotels?/[a-z0-9-]+)"')),
    ("CHOICE_SC", ("https://www.choicehotels.com/south-carolina/fort-mill/hotels",
                   r'href="(/south-carolina/[a-z0-9-]+/[a-z0-9-]+/hotels?/[a-z0-9-]+)"')),
    ("IHG", ("https://www.ihg.com/destinations/us/en/united-states/north-carolina/charlotte-hotels",
             r'href="(https?://www\.ihg\.com/[a-z0-9]+/hotels/us/en/[a-z0-9-]+/[a-z0-9]+/hoteldetail)"')),
    ("BEST_WESTERN", ("https://www.bestwestern.com/en_US/book/hotels-in-charlotte-nc.html",
                      r'href="(https?://www\.bestwestern\.com/en_US/book/[^"]*3[0-9]{4}[^"]*)"')),
    ("ESA", ("https://www.extendedstayamerica.com/hotels/nc/charlotte",
             r'href="(/hotels/[ns]c/[a-z0-9-]+/[a-z0-9-]+)"')),
    ("WOODSPRING", ("https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/charlotte",
                    r'href="(/extended-stay-hotels/locations/(?:north|south)-carolina/[a-z0-9-]+/[a-z0-9-]+)"')),
    ("RED_ROOF_NC", ("https://www.redroof.com/state/nc",
                     r'href="(https?://www\.redroof\.com/property/[a-z0-9-]+/[A-Z0-9]+)"')),
    ("RED_ROOF_SC", ("https://www.redroof.com/state/sc",
                     r'href="(https?://www\.redroof\.com/property/[a-z0-9-]+/[A-Z0-9]+)"')),
    ("MOTEL6", ("https://www.motel6.com/en/motels.nc.charlotte.html",
                r'href="(/en/motels/[ns]c/[a-z0-9-]+/[0-9]+/[^"?#]*)"')),
    ("HYATT", ("https://www.hyatt.com/explore-hotels/destinations/charlotte",
               r'href="(https?://www\.hyatt\.com/[a-z-]+/[a-z]{2}/[a-z0-9-]+/[a-z0-9]+)"')),
    ("SONESTA", ("https://www.sonesta.com/nc/charlotte",
                 r'href="(https?://www\.sonesta\.com/[a-z0-9-]+/[ns]c/[a-z0-9-]+/[a-z0-9-]+)"')),
    ("OMNI", ("https://www.omnihotels.com/hotels/charlotte",
              r'href="(/hotels/charlotte[a-z0-9-]*)"')),
    ("KIMPTON", ("https://www.kimptonhotels.com/destinations/north-carolina/charlotte",
                 r'href="(https?://[a-z0-9.-]*kimpton[a-z0-9.-]*/[^"?#]*)"')),
    ("STAYBRIDGE", ("https://www.ihg.com/destinations/us/en/united-states/south-carolina/fort-mill-hotels",
                    r'href="(https?://www\.ihg\.com/[a-z0-9]+/hotels/us/en/[a-z0-9-]+/[a-z0-9]+/hoteldetail)"')),
])


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Encoding": "gzip", "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                try:
                    data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
                except Exception:  # noqa: BLE001
                    pass
            return r.status, r.geturl(), data
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def cached_get(url, stats):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    meta_path = os.path.join(CACHE, key + ".json")
    body_path = os.path.join(CACHE, key + ".html")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
        body = open(body_path, "rb").read() if os.path.exists(body_path) else b""
        return meta, body
    time.sleep(SPACING)
    st, final, body = get(url)
    stats["requests"] += 1
    meta = {"url": url, "status": st, "final_url": final, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest() if body else "",
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if body:
        open(body_path, "wb").write(body)
    json.dump(meta, open(meta_path, "w", encoding="utf-8"))
    return meta, body


def harvest_hilton(stats):
    cities, codes = OrderedDict(), OrderedDict()
    for state, city in HILTON_CITIES:
        key = "%s/%s" % (state, city)
        url = HILTON_CITY_URL % (state, city)
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        found = OrderedDict()
        for code, slug in HILTON_CODE.findall(html):
            found.setdefault(code.lower(), slug.lower())
        cities[key] = OrderedDict([
            ("url", url), ("status", meta["status"]), ("sha256", meta["sha256"]),
            ("fetched_at", meta["fetched_at"]), ("bytes", meta["bytes"]),
            ("codes_found", len(found)), ("codes", found)])
        for code, slug in found.items():
            if code in codes:
                codes[code]["seen_on_city_pages"].append(key)
                continue
            codes[code] = OrderedDict([
                ("property_code", code), ("slug", slug),
                ("route", "https://www.hilton.com/en/hotels/%s-%s/" % (code, slug)),
                ("code_prefix", code[:3]),
                ("selected_by", "PROPERTY_CODE_PREFIX" if code.startswith(CODE_PREFIX)
                                else "CITY_PAGE_MEMBERSHIP"),
                ("seen_on_city_pages", [key])])
    return cities, codes


def reprobe_refusals(stats):
    out = OrderedDict()
    for fam, urls in REFUSAL_REPROBE.items():
        attempts = []
        for u in urls:
            time.sleep(SPACING)
            st, final, body = get(u)
            stats["requests"] += 1
            sitemaps = []
            if st == 200 and body:
                sitemaps = re.findall(r"(?im)^sitemap:\s*(\S+)",
                                      body.decode("utf-8", "replace"))
            attempts.append(OrderedDict([
                ("url", u), ("status", st), ("bytes", len(body)),
                ("sitemaps_declared", sitemaps),
                ("at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))]))
        served = [a for a in attempts if a["status"] == 200]
        out[fam] = OrderedDict([
            ("attempts", attempts), ("any_host_served", bool(served)),
            ("verdict", "SERVED_ON_AT_LEAST_ONE_HOST" if served
                        else "REFUSED_ON_EVERY_HOST")])
    return out


def harvest_city_pages(stats):
    out = OrderedDict()
    for fam, (url, pattern) in CITY_PAGES.items():
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        links = sorted(set(re.findall(pattern, html)))
        if meta["status"] == 200 and not links:
            verdict = "SERVED_BUT_NO_PROPERTY_ROUTES_TO_A_PLAIN_CLIENT"
            why = ("the page returned %d bytes and declares no property route this "
                   "client can read; the roster is rendered client-side, so the "
                   "family goes down the ladder rather than being called silent"
                   % meta["bytes"])
        elif meta["status"] == 200:
            verdict = "ROUTES_READ_FROM_THE_BRAND_OWN_CITY_PAGE"
            why = "%d property routes read first-party" % len(links)
        else:
            verdict = "REFUSED_OR_ABSENT"
            why = "status %r" % (meta["status"],)
        out[fam] = OrderedDict([
            ("url", url), ("status", meta["status"]), ("final_url", meta.get("final_url")),
            ("sha256", meta["sha256"]), ("bytes", meta["bytes"]),
            ("fetched_at", meta["fetched_at"]),
            ("property_routes", links), ("routes_found", len(links)),
            ("verdict", verdict), ("why", why)])
    return out


def build(args):
    stats = {"requests": 0}
    hilton_cities, hilton_codes = harvest_hilton(stats)
    refusals = reprobe_refusals(stats)
    city_pages = harvest_city_pages(stats)

    clt = [c for c in hilton_codes.values() if c["property_code"].startswith(CODE_PREFIX)]
    other = [c for c in hilton_codes.values() if not c["property_code"].startswith(CODE_PREFIX)]
    served_families = sorted(f for f, v in city_pages.items()
                             if v["verdict"] == "ROUTES_READ_FROM_THE_BRAND_OWN_CITY_PAGE")
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4C/7 -- brand inventory audit, rung 1 (the brand's own city page)"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "LOCAL_FREE_DISCOVERY (official brand city/location pages)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("a_code_selects_it_never_admits",
         "A CLT prefix proposes that a property is in this market. Nothing here admits "
         "it. CLT is the Charlotte Douglas International Airport code and the committed "
         "Dayton roster harvest proves it reaches Shelby (cltby), Statesville (cltfv), "
         "Hickory (cltht), Salisbury (cltsb), Mooresville, Monroe and Gastonia. Every "
         "code below is judged later on the postal code its OWN property page states, "
         "against the corridor registry in the market contract."),
        ("asserts_no_closure",
         "A city with no brand page, or a roster with no entry, is a statement about "
         "the BRAND ROSTER. It is never proof that a building closed."),
        ("two_states_asked_separately",
         "Charlotte is the first PetTripFinder market whose traveler geography crosses "
         "a state line. Every family that files rosters by state is asked twice, "
         "because Fort Mill, Tega Cay and Indian Land are admitted corridors and Rock "
         "Hill is a founder hold that must be MEASURED rather than assumed empty."),
        ("hilton", OrderedDict([
            ("city_pages", hilton_cities),
            ("cities_served", sum(1 for b in hilton_cities.values() if b["status"] == 200)),
            ("cities_404", sorted(c for c, b in hilton_cities.items() if b["status"] == 404)),
            ("distinct_codes", len(hilton_codes)),
            ("clt_prefixed_codes", len(clt)),
            ("other_prefixed_codes", len(other)),
            ("codes", hilton_codes)])),
        ("brand_city_pages", city_pages),
        ("refusal_reprobe", refusals),
        ("counts", OrderedDict([
            ("hilton_cities_fetched", len(hilton_cities)),
            ("hilton_clt_codes", len(clt)),
            ("families_reprobed", len(refusals)),
            ("families_served_on_some_host", sum(1 for v in refusals.values()
                                                 if v["any_host_served"])),
            ("families_refused_everywhere", sorted(f for f, v in refusals.items()
                                                   if not v["any_host_served"])),
            ("city_pages_fetched", len(city_pages)),
            ("families_yielding_routes", served_families),
            ("routes_by_family", OrderedDict(
                (f, v["routes_found"]) for f, v in city_pages.items())),
            ("total_brand_routes", sum(v["routes_found"] for v in city_pages.values())),
        ])),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "charlotte_nc_brand_city_pages_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    print("hilton cities       :", c["hilton_cities_fetched"],
          "served:", rep["hilton"]["cities_served"], "404:", rep["hilton"]["cities_404"])
    print("hilton CLT codes    :", c["hilton_clt_codes"], "of", rep["hilton"]["distinct_codes"])
    print("refusals reprobed   :", c["families_reprobed"],
          "served somewhere:", c["families_served_on_some_host"])
    print("refused everywhere  :", c["families_refused_everywhere"])
    print("brand routes        :", c["total_brand_routes"], c["routes_by_family"])
    print("free http requests  :", rep["free_http_requests"])
    print("written             :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
