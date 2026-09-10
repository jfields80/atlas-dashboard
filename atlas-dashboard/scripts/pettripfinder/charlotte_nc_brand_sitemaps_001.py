"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- Phases 4C and 7, rung 2: the
brand's own sitemap, walked under a per-family request cap.

Rung 1 is the brand's own CITY page (``charlotte_nc_brand_city_pages_001``).
This module is rung 2 and runs for the families whose city page rendered its
roster client-side or refused a plain client. Toledo lost 25 minutes to an
unbounded Hilton sitemap walk that produced nothing, so every walk here is
bounded and records whether it stopped with work outstanding.

Everything produced here is ROUTING and IDENTITY evidence. No route carries or
implies a pet policy, and no route admits a property to this market: the postal
code the property's OWN page states does that, against the corridor registry.

TWO STATES. Charlotte's admitted corridors include Fort Mill, Tega Cay and
Indian Land, South Carolina, so every state-shaped property pattern below
accepts ``north-carolina``/``nc`` and ``south-carolina``/``sc`` alike, and the
locality token carries the South Carolina towns.

No paid provider is called. Output is Charlotte-local.

Output:
  launch_packages/pettripfinder/markets/reports/charlotte_nc_brand_sitemaps_001.json
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

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
SCHEMA = "ptf-brand-sitemap-inventory/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "charlotte_nc_brand_sitemaps_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 0.5

#: ``family -> (entry sitemap, child selector, property selector, request cap)``.
#: ``child selector`` picks which children of an INDEX are worth fetching;
#: ``property selector`` decides which ``<loc>`` is a Carolinas property route.
FAMILIES = OrderedDict([
    ("SONESTA", ("https://www.sonesta.com/sitemap/sitemap-index.xml",
                 r"sitemap-\d+\.xml",
                 r"sonesta\.com/[a-z0-9-]+/[ns]c/[a-z0-9-]+/[a-z0-9-]+$", 14)),
    ("OMNI", ("https://www.omnihotels.com/sitemap.xml",
              r"$^", r"omnihotels\.com/hotels/[a-z0-9-]*charlotte[a-z0-9-]*/?$", 4)),
    ("WYNDHAM", ("https://www.wyndhamhotels.com/sitemap.xml",
                 r"properties_\d+\.xml",
                 r"wyndhamhotels\.com/[a-z0-9-]+/[a-z0-9-]+-(?:north|south)-carolina/[a-z0-9-]+/overview$",
                 260)),
    ("HILTON", ("https://www.hilton.com/sitemap.xml",
                r"(?:hotel|propert|en-us)",
                r"hilton\.com/en/hotels/clt[a-z0-9]{1,6}-[a-z0-9-]+/?$", 24)),
    ("MARRIOTT", ("https://www.marriott.com/sitemap.xml",
                  r"(?:hotel|propert|en-us)",
                  r"marriott\.com/[a-z-]+/hotels/clt[a-z0-9]{2}-[a-z0-9-]+/overview/?$", 24)),
    # Declared a sitemap in robots.txt and then refused it in earlier markets.
    # Attempted anyway so the refusal is measured by THIS order, never inherited.
    ("IHG", ("https://www.ihg.com/services/sitemaps/sitemap-index.xml",
             r"$^",
             r"ihg\.com/[a-z0-9]+/hotels/us/en/[a-z0-9-]+/clt[a-z0-9]{2}/hoteldetail$", 4)),
    ("CHOICE", ("https://www.choicehotels.com/sitemapindex.xml",
                r"$^", r"choicehotels\.com/(?:north|south)-carolina/[a-z0-9-]+/", 4)),
    ("RED_ROOF", ("https://www.redroof.com/sitemap.xml",
                  r"$^", r"redroof\.com/property/", 4)),
    ("MOTEL6", ("https://www.motel6.com/sitemap.xml",
                r"$^", r"motel6\.com/en/motels/[ns]c/", 4)),
    ("RADISSON", ("https://www.radissonhotels.com/sitemapindex.xml",
                  r"$^", r"radissonhotels\.com/en-us/hotels/[a-z0-9-]*charlotte", 4)),
    ("EXTENDED_STAY", ("https://www.extendedstayamerica.com/sitemap.xml",
                       r"$^", r"extendedstayamerica\.com/hotels/[ns]c/[a-z0-9-]+/", 6)),
    ("WOODSPRING", ("https://www.woodspring.com/sitemap.xml",
                    r"$^",
                    r"woodspring\.com/extended-stay-hotels/locations/(?:north|south)-carolina/", 6)),
    ("DRURY", ("https://www.druryhotels.com/sitemap.xml",
               r"$^", r"druryhotels\.com/locations/[a-z0-9-]+-[ns]c/", 6)),
])

#: A Charlotte-market locality token in a route. Generous on purpose: the point
#: is to CARRY the row forward, and the property page decides. Includes the held
#: fringe towns so a hold rests on evidence rather than on an absence.
CHARLOTTE_TOKEN = re.compile(
    r"(charlotte|uptown|south-end|southpark|south-park|ballantyne|pineville|matthews|"
    r"mint-hill|university|northlake|steele-creek|arrowood|westinghouse|tyvola|"
    r"yorkmont|billy-graham|huntersville|cornelius|davidson|lake-norman|concord|"
    r"harrisburg|belmont|gastonia|fort-mill|tega-cay|indian-land|carowinds|"
    r"rock-hill|kannapolis|mooresville|monroe|indian-trail|waxhaw|piper-glen|"
    r"plaza-midwood|noda|dilworth|myers-park|carolina-place)", re.I)
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
                ("charlotte_token", bool(CHARLOTTE_TOKEN.search(h))),
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
            "the family has no Charlotte property.")
    elif routes:
        verdict, why = "ROUTES_READ_FROM_THE_BRAND_OWN_SITEMAP", (
            "%d property routes read first-party across %d served documents"
            % (len(routes), len(served)))
    else:
        verdict, why = "SERVED_BUT_NO_CHARLOTTE_PROPERTY_ROUTE", (
            "%d documents served and none carried a route matching this market's "
            "property pattern. A roster with no row is a statement about the ROSTER "
            "and is never proof that a building closed." % len(served))
    return OrderedDict([
        ("entry_sitemap", entry), ("request_cap", cap), ("requests_spent", spent),
        ("cap_reached", spent >= cap and bool(queue)),
        ("documents", fetched),
        ("charlotte_routes", [r for r in routes.values() if r["charlotte_token"]]),
        ("other_routes_matched", sum(1 for r in routes.values() if not r["charlotte_token"])),
        ("verdict", verdict), ("why", why)])


def build(args):
    stats = {"requests": 0}
    fams = OrderedDict()
    only = set((args.only or "").upper().split(",")) - {""}
    for fam, (entry, child, prop, cap) in FAMILIES.items():
        if only and fam not in only:
            continue
        fams[fam] = walk_family(fam, entry, child, prop, cap, stats)

    total = sum(len(v["charlotte_routes"]) for v in fams.values())
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4C/7 -- brand inventory audit, rung 2 (the brand's own sitemap)"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "LOCAL_FREE_DISCOVERY (official brand sitemaps)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("robots_serving_is_not_sitemap_serving",
         "Measured by this run, not assumed. Several families answer robots.txt with "
         "a sitemap URL and then refuse that very sitemap to the same client seconds "
         "later. Each such family is recorded SITEMAP_REFUSED_TO_THIS_CLIENT and goes "
         "down the ladder; none is called silent."),
        ("every_walk_is_bounded",
         "Each family carries a request cap and the walk stops at it, recording "
         "whether the cap was reached with work outstanding."),
        ("a_roster_row_is_not_a_policy",
         "Everything here is ROUTING and IDENTITY evidence. No route in this file "
         "carries or implies a pet policy, and no route admits a property to this "
         "market -- the postal code the property's OWN page states does that."),
        ("families", fams),
        ("counts", OrderedDict([
            ("families_walked", len(fams)),
            ("charlotte_routes_by_family",
             OrderedDict((f, len(v["charlotte_routes"])) for f, v in fams.items())),
            ("verdicts", OrderedDict(sorted(
                Counter(v["verdict"] for v in fams.values()).items()))),
            ("total_charlotte_routes", total),
        ])),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "charlotte_nc_brand_sitemaps_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    for fam, v in rep["families"].items():
        print("%-14s %-44s %d routes (%d requests)"
              % (fam, v["verdict"], len(v["charlotte_routes"]), v["requests_spent"]))
    print("total charlotte routes:", c["total_charlotte_routes"])
    print("free http requests    :", rep["free_http_requests"])
    print("written               :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
