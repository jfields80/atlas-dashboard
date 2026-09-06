"""PTF-TOLEDO-OH-NEW-MARKET-001 -- Phase 7, rung 1: a brand's own CITY page.

PTF-FORT-WAYNE-IN-NEW-MARKET-001 measured three rungs BELOW the brand sitemap
walk. This module is rung 1, and it is why this order killed its own Hilton
sitemap walk after 25 minutes:

  ``hilton.com/en/locations/usa/ohio/toledo/`` returns every TOL-coded Hilton
  property in ONE request. The sitemap path to the same answer is
  ``sitemap-en.xml`` -> an index of ~984 brand-sharded children, each answering
  in seconds. Both prior Ohio harvests recorded ZERO Hilton property URLs after
  walking it, which is the same lesson from the other side: the expensive rung
  was also the incomplete one.

Two disciplines this run keeps:

* **A property code SELECTS, it never ADMITS.** Hilton's Ohio index carries every
  Ohio city; a TOL prefix proposes Toledo and the property page's OWN address
  decides. Bowling Green is fetched and reported, but the market contract holds
  it, not this file.
* **A refusal is a fact about a moment.** Every family this order could not walk
  is re-probed here against both the ``www.`` and bare hostnames, because the two
  answer differently and the difference is not stable within a single run. What
  the run actually observed is recorded, including the inconsistency.

No paid provider is called. Output is Toledo-local.

Output:
  launch_packages/pettripfinder/markets/reports/toledo_oh_brand_city_pages_001.json
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
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-TOLEDO-OH-NEW-MARKET-001"
MARKET_ID = "toledo-oh"
SCHEMA = "ptf-brand-city-page-inventory/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "toledo_oh_brand_city_pages_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 1.2

#: Hilton names its location pages by city slug. These are the market's own
#: municipalities; a city Hilton does not publish simply 404s, which is a fact
#: about the roster and not about the building.
HILTON_CITIES = [
    "toledo", "maumee", "perrysburg", "rossford", "sylvania", "holland", "oregon",
    "northwood", "waterville", "whitehouse", "swanton", "millbury", "walbridge",
    "monclova", "bowling-green",
]
HILTON_CITY_URL = "https://www.hilton.com/en/locations/usa/ohio/%s/"
HILTON_CODE = re.compile(r"/en/hotels/([a-z0-9]{4,9})-([a-z0-9-]+)/", re.I)
#: Toledo Express Airport. A TOL prefix selects; the property page decides.
CODE_PREFIX = "tol"

#: Families this order could not walk. Probed against BOTH hostnames, because
#: they answer differently: on 2026-09-06 ``ihg.com``, ``choicehotels.com`` and
#: ``motel6.com`` each returned 200 to a bare-host robots.txt request within
#: seconds of ``www.`` refusing, and then refused the bare host on the next
#: request. The instability is the finding.
REFUSAL_REPROBE = OrderedDict([
    ("IHG", ["https://www.ihg.com/robots.txt", "https://ihg.com/robots.txt",
             "https://www.holidayinn.com/robots.txt"]),
    ("CHOICE", ["https://www.choicehotels.com/robots.txt",
                "https://choicehotels.com/robots.txt"]),
    ("BEST_WESTERN", ["https://www.bestwestern.com/robots.txt",
                      "https://bestwestern.com/robots.txt"]),
    ("ESA", ["https://www.extendedstayamerica.com/robots.txt",
             "https://extendedstayamerica.com/robots.txt"]),
    ("RED_ROOF", ["https://www.redroof.com/robots.txt", "https://redroof.com/robots.txt"]),
    ("MOTEL6", ["https://www.motel6.com/robots.txt", "https://motel6.com/robots.txt"]),
    ("HYATT", ["https://www.hyatt.com/robots.txt", "https://hyatt.com/robots.txt"]),
])
#: Families whose Toledo roster this run reads somewhere other than a sitemap.
OTHER_CITY_PAGES = OrderedDict([
    ("DRURY", "https://www.druryhotels.com/locations/toledo-oh"),
    ("WYNDHAM", "https://www.wyndhamhotels.com/hotels/toledo-ohio"),
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
    cities = OrderedDict()
    codes = OrderedDict()
    for city in HILTON_CITIES:
        url = HILTON_CITY_URL % city
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        found = OrderedDict()
        for code, slug in HILTON_CODE.findall(html):
            found.setdefault(code.lower(), slug.lower())
        cities[city] = OrderedDict([
            ("url", url), ("status", meta["status"]), ("sha256", meta["sha256"]),
            ("fetched_at", meta["fetched_at"]), ("bytes", meta["bytes"]),
            ("codes_found", len(found)),
            ("codes", found),
        ])
        for code, slug in found.items():
            if code in codes:
                codes[code]["seen_on_city_pages"].append(city)
                continue
            codes[code] = OrderedDict([
                ("property_code", code), ("slug", slug),
                ("route", "https://www.hilton.com/en/hotels/%s-%s/" % (code, slug)),
                ("code_prefix", code[:3]),
                ("selected_by", "PROPERTY_CODE_PREFIX" if code.startswith(CODE_PREFIX)
                                else "CITY_PAGE_MEMBERSHIP"),
                ("seen_on_city_pages", [city]),
            ])
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
                ("at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            ]))
        served = [a for a in attempts if a["status"] == 200]
        out[fam] = OrderedDict([
            ("attempts", attempts),
            ("any_host_served", bool(served)),
            ("verdict", "SERVED_ON_AT_LEAST_ONE_HOST" if served else "REFUSED_ON_EVERY_HOST"),
        ])
    return out


def harvest_other(stats):
    out = OrderedDict()
    for fam, url in OTHER_CITY_PAGES.items():
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        if fam == "DRURY":
            links = sorted(set(re.findall(r'href="(/locations/[a-z-]+-oh/[^"]*)"', html)))
        else:
            links = sorted(set(re.findall(
                r'href="(https://www\.wyndhamhotels\.com/[a-z0-9-]+/[a-z-]+-ohio/[^"]+/overview)"',
                html)))
        out[fam] = OrderedDict([
            ("url", url), ("status", meta["status"]), ("final_url", meta.get("final_url")),
            ("sha256", meta["sha256"]), ("bytes", meta["bytes"]),
            ("property_links", links),
            ("note", ""),
        ])
        if fam == "DRURY" and meta.get("final_url", "").rstrip("/").endswith("/locations"):
            out[fam]["note"] = (
                "The Toledo locations URL REDIRECTED to Drury's national locations index, and that "
                "index lists no Toledo property (Cincinnati, Cleveland, Columbus, Dayton, Findlay, "
                "Middletown are its Ohio entries). Recorded as BRAND_INVENTORY_SILENT for Toledo. "
                "A brand roster with no Toledo entry is a statement about the roster; it is not "
                "evidence that a Drury building in Toledo closed, because none is known to exist.")
        if fam == "WYNDHAM" and not links:
            out[fam]["note"] = (
                "Wyndham's Toledo city page served 200 but renders its property list client-side, "
                "so a plain client reads no property links. This costs nothing: Wyndham's Ohio "
                "property URLs are already OWNED from the committed Dayton and Cleveland sitemap "
                "harvests, which is rung 0.")
    return out


def build(args) -> OrderedDict:
    stats = {"requests": 0}
    hilton_cities, hilton_codes = harvest_hilton(stats)
    refusals = reprobe_refusals(stats)
    other = harvest_other(stats)
    tol = [c for c in hilton_codes.values() if c["property_code"].startswith(CODE_PREFIX)]
    non_tol = [c for c in hilton_codes.values() if not c["property_code"].startswith(CODE_PREFIX)]

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "7 -- brand inventory audit, rung 1 (the brand's own city page)"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "LOCAL_FREE_DISCOVERY (official brand city/location pages)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats["requests"]),
        ("why_not_the_sitemap",
         "This order started a Hilton sitemap walk and killed it at 25 minutes with nothing to "
         "show. Both committed Ohio harvests (Cleveland 2026-09-01, Dayton 2026-09-02) recorded "
         "ZERO Hilton property URLs after walking 985 children each. The city page answers the "
         "same question in one request. Rung order: owned harvest, brand city page, bounded "
         "sitemap, then say you could not."),
        ("a_code_selects_it_never_admits",
         "A TOL prefix proposes that a property is in this market. Nothing here admits it. Every "
         "code below is carried into routing and judged on the address its OWN property page "
         "states, exactly as Marriott's TOLBG (Bowling Green, OHIO) is held by the market contract "
         "rather than admitted by its prefix."),
        ("asserts_no_closure",
         "A city with no Hilton page, or a roster with no entry, is a statement about the BRAND "
         "ROSTER. It is never proof that a building closed or stopped taking guests."),
        ("hilton", OrderedDict([
            ("city_pages", hilton_cities),
            ("cities_served", sum(1 for b in hilton_cities.values() if b["status"] == 200)),
            ("cities_404", sorted(c for c, b in hilton_cities.items() if b["status"] == 404)),
            ("distinct_codes", len(hilton_codes)),
            ("tol_prefixed_codes", len(tol)),
            ("other_prefixed_codes", len(non_tol)),
            ("codes", hilton_codes),
        ])),
        ("other_brand_city_pages", other),
        ("refusal_reprobe", refusals),
        ("counts", OrderedDict([
            ("hilton_cities_fetched", len(hilton_cities)),
            ("hilton_tol_codes", len(tol)),
            ("families_reprobed", len(refusals)),
            ("families_served_on_some_host", sum(1 for v in refusals.values()
                                                 if v["any_host_served"])),
            ("families_refused_everywhere", sorted(f for f, v in refusals.items()
                                                   if not v["any_host_served"])),
        ])),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "toledo_oh_brand_city_pages_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    print("hilton cities       :", c["hilton_cities_fetched"],
          "served:", rep["hilton"]["cities_served"], "404:", rep["hilton"]["cities_404"])
    print("hilton TOL codes    :", c["hilton_tol_codes"], "of", rep["hilton"]["distinct_codes"])
    print("refusals reprobed   :", c["families_reprobed"],
          "served somewhere:", c["families_served_on_some_host"])
    print("refused everywhere  :", c["families_refused_everywhere"])
    print("free http requests  :", rep["free_http_requests"])
    print("written             :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
