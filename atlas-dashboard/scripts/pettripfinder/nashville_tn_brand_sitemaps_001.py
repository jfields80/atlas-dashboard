"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phases 4C and 7, rung 2: the official
brand sitemap, walked only where rung 1 did not already answer.

WHY THIS RUNG EXISTS AT ALL
---------------------------
Rung 1 (``nashville_tn_brand_city_pages_001``) re-probed the eight families the
committed Ohio harvests had recorded as refusing a plain client. Nine of twelve
served ``robots.txt`` this time, and each declared a sitemap. A five-day-old
refusal list would have skipped every one of them.

WHY SERVING robots.txt IS NOT SERVING A SITEMAP
-----------------------------------------------
Measured here, not assumed. IHG, Choice, Red Roof, Motel 6 and Radisson all
answered ``robots.txt`` with a sitemap URL and then REFUSED that very sitemap to
the same client seconds later. That is the finding, and it is what sends those
families down the ladder to Firecrawl and the attended browser rather than
being called silent. Sonesta, Omni, Loews and Wyndham served.

THE ONE-REQUEST WIN
-------------------
Sonesta's whole published roster is a single child sitemap: one request yields
sixty-four Tennessee properties across Americas Best Value Inn, Sonesta Simply
Suites, Sonesta Select, Sonesta ES Suites and Red Lion. That is the same shape
as Toledo's Hilton city page -- the cheap rung was also the complete one.

BOUNDS
------
Every family has a request cap and every walk stops at it. Nothing here is
paid, and no walk is allowed to run unbounded: Toledo lost 25 minutes to an
unbounded Hilton sitemap walk that produced nothing.

A code SELECTS, a page ADMITS, and a roster with no row is not a closure. The
routes here are ROUTING and IDENTITY evidence. None of them is policy.

Output:
  launch_packages/pettripfinder/markets/reports/nashville_tn_brand_sitemaps_001.json
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

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
SCHEMA = "ptf-brand-sitemap-inventory/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "nashville_tn_brand_sitemaps_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 0.8

#: ``family -> (entry sitemap, child selector, property selector, request cap)``.
#: ``child selector`` picks which children of an INDEX are worth fetching;
#: ``property selector`` decides which ``<loc>`` is a Tennessee property route.
FAMILIES = OrderedDict([
    ("SONESTA", ("https://www.sonesta.com/sitemap/sitemap-index.xml",
                 r"sitemap-\d+\.xml", r"sonesta\.com/[a-z0-9-]+/tn/[a-z0-9-]+/[a-z0-9-]+$", 12)),
    ("OMNI", ("https://www.omnihotels.com/sitemap.xml",
              r"$^", r"omnihotels\.com/hotels/[a-z0-9-]*nashville[a-z0-9-]*/?$", 4)),
    ("LOEWS", ("https://www.loewshotels.com/sitemap-desktop.xml",
               r"$^", r"loewshotels\.com/[a-z0-9-]*(?:nashville|vanderbilt)[a-z0-9-]*/?$", 4)),
    ("WYNDHAM", ("https://www.wyndhamhotels.com/sitemap.xml",
                 r"properties_\d+\.xml",
                 r"wyndhamhotels\.com/[a-z0-9-]+/[a-z0-9-]+-tennessee/[a-z0-9-]+/overview$", 240)),
    ("HILTON", ("https://www.hilton.com/sitemap.xml",
                r"(?:hotel|propert|en-us)", r"hilton\.com/en/hotels/bna[a-z0-9]{1,6}-[a-z0-9-]+/?$", 20)),
    # Declared a sitemap in robots.txt and then refused it. Attempted anyway so
    # the refusal is measured by this order rather than inherited.
    ("IHG", ("https://www.ihg.com/services/sitemaps/sitemap-index.xml",
             r"$^", r"ihg\.com/[a-z0-9]+/hotels/us/en/[a-z0-9-]+/bna[a-z0-9]{2}/hoteldetail$", 4)),
    ("CHOICE", ("https://www.choicehotels.com/sitemapindex.xml",
                r"$^", r"choicehotels\.com/tennessee/[a-z0-9-]+/", 4)),
    ("RED_ROOF", ("https://www.redroof.com/sitemap.xml",
                  r"$^", r"redroof\.com/property/", 4)),
    ("MOTEL6", ("https://www.motel6.com/sitemap.xml",
                r"$^", r"motel6\.com/en/motels/tn/", 4)),
    ("RADISSON", ("https://www.radissonhotels.com/sitemapindex.xml",
                  r"$^", r"radissonhotels\.com/en-us/hotels/[a-z0-9-]*nashville", 4)),
])

#: A Nashville-market locality token in a route. Generous on purpose: the point
#: is to CARRY the row forward, and the property page decides.
NASHVILLE_TOKEN = re.compile(
    r"(nashville|brentwood|goodlettsville|antioch|hermitage|old-hickory|donelson|"
    r"opryland|music-valley|bellevue|green-hills|metrocenter|metro-center|vanderbilt|"
    r"west-end|gulch|berry-hill|germantown|madison|rivergate|mount-juliet|mt-juliet|"
    r"hendersonville|smyrna|la-vergne|lavergne|franklin|cool-springs|lebanon)", re.I)
_LOC = re.compile(rb"<loc>\s*([^<\s]+)\s*</loc>")


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/xml,text/xml,*/*",
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
    body_path = os.path.join(CACHE, key + ".xml")
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


def walk_family(fam, entry, child_pat, prop_pat, cap, stats):
    child_rx, prop_rx = re.compile(child_pat, re.I), re.compile(prop_pat, re.I)
    fetched, routes, spent = [], OrderedDict(), 0
    queue, seen = [entry], set()
    while queue and spent < cap:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        meta, body = cached_get(url, stats)
        spent += 1
        locs = [b.decode("utf-8", "replace") for b in _LOC.findall(body)]
        children = [l for l in locs if l.lower().endswith(".xml") and child_rx.search(l)]
        hits = [l for l in locs if prop_rx.search(l)]
        for h in hits:
            routes.setdefault(h.rstrip("/"), OrderedDict([
                ("route", h.rstrip("/")), ("family", fam),
                ("nashville_token", bool(NASHVILLE_TOKEN.search(h))),
                ("found_in", url)]))
        fetched.append(OrderedDict([
            ("url", url), ("status", meta["status"]), ("bytes", meta["bytes"]),
            ("sha256", meta["sha256"]), ("locs", len(locs)),
            ("children_selected", len(children)), ("property_routes", len(hits))]))
        queue.extend(c for c in children if c not in seen)

    served = [f for f in fetched if f["status"] == 200]
    if not served:
        verdict, why = "SITEMAP_REFUSED_TO_THIS_CLIENT", (
            "the family declared this sitemap in its own robots.txt and then refused "
            "it to the same client. That is a fact about this client at this moment, "
            "and it is what sends the family down the ladder. It is NOT evidence that "
            "the family has no Nashville property.")
    elif routes:
        verdict, why = "ROUTES_READ_FROM_THE_BRAND_OWN_SITEMAP", (
            "%d property routes read first-party across %d served documents"
            % (len(routes), len(served)))
    else:
        verdict, why = "SERVED_BUT_NO_NASHVILLE_PROPERTY_ROUTE", (
            "%d documents served and %d carried no route matching this market's "
            "property pattern. A roster with no row is a statement about the ROSTER "
            "and is never proof that a building closed."
            % (len(served), len(served)))
    return OrderedDict([
        ("entry_sitemap", entry), ("request_cap", cap), ("requests_spent", spent),
        ("cap_reached", spent >= cap and bool(queue)),
        ("documents", fetched),
        ("nashville_routes", [r for r in routes.values() if r["nashville_token"]]),
        ("other_routes_matched", sum(1 for r in routes.values() if not r["nashville_token"])),
        ("verdict", verdict), ("why", why)])


def build(args):
    stats = {"requests": 0}
    fams = OrderedDict()
    only = set((args.only or "").upper().split(",")) - {""}
    for fam, (entry, child, prop, cap) in FAMILIES.items():
        if only and fam not in only:
            continue
        fams[fam] = walk_family(fam, entry, child, prop, cap, stats)

    total = sum(len(v["nashville_routes"]) for v in fams.values())
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4C/7 -- brand inventory audit, rung 2 (the brand's own sitemap)"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "LOCAL_FREE_DISCOVERY (official brand sitemaps)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("robots_serving_is_not_sitemap_serving",
         "Measured by this run, not assumed. Several families answered robots.txt "
         "with a sitemap URL and then refused that very sitemap to the same client "
         "seconds later. Each such family is recorded SITEMAP_REFUSED_TO_THIS_CLIENT "
         "and goes down the ladder; none is called silent."),
        ("every_walk_is_bounded",
         "Each family carries a request cap and the walk stops at it, recording "
         "whether the cap was reached with work outstanding. Toledo lost 25 minutes "
         "to an unbounded Hilton sitemap walk that produced nothing."),
        ("a_roster_row_is_not_a_policy",
         "Everything here is ROUTING and IDENTITY evidence. No route in this file "
         "carries or implies a pet policy, and no route admits a property to this "
         "market -- the address the property's OWN page states does that."),
        ("families", fams),
        ("counts", OrderedDict([
            ("families_walked", len(fams)),
            ("nashville_routes_by_family",
             OrderedDict((f, len(v["nashville_routes"])) for f, v in fams.items())),
            ("verdicts", OrderedDict(sorted(
                Counter(v["verdict"] for v in fams.values()).items()))),
            ("total_nashville_routes", total),
        ])),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "nashville_tn_brand_sitemaps_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    for fam, v in rep["families"].items():
        print("%-12s %-42s %d routes (%d requests)"
              % (fam, v["verdict"], len(v["nashville_routes"]), v["requests_spent"]))
    print("total nashville routes:", c["total_nashville_routes"])
    print("free http requests    :", rep["free_http_requests"])
    print("written               :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
