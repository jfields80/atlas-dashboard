"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phase 7, the brand CITY-PAGE lane.

A brand's own city page beats its sitemap, and an owned harvest beats both.

This order started Hilton the way Dayton and Cleveland did -- robots.txt to
sitemap index to ~1,185 child sitemaps at polite spacing -- and after roughly
ninety minutes it had produced nothing. One request to Hilton's own Lexington
city page produced twenty property codes, including six properties the census
did not have and the two that prove why a bare chain name can never identify a
hotel: Lexington has TWO Embassy Suites and THREE Homewood Suites.

So the sitemap walk was stopped and this lane replaced it. The city page is
first-party, it is one request per brand, and it is scoped to the market by
the brand itself rather than by a property-code prefix that provably spans
four other destinations.

Every URL here is an identity/ROUTING lead. None of it is policy evidence, and
a brand's decision to list a property under "Lexington" is the brand's
marketing scope, not this market's boundary: admission is still decided on the
address, downstream.
"""
from __future__ import annotations

import argparse
import hashlib
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

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "lexington_ky_city_pages_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
SPACING = 1.5

# Several URL shapes per family: a brand that refuses one often serves another,
# and this order does not want to record a family as walled on one guess.
CITY_PAGES = OrderedDict([
    ("HILTON", [
        "https://www.hilton.com/en/locations/usa/kentucky/lexington/",
    ]),
    ("WYNDHAM", [
        "https://www.wyndhamhotels.com/hotels/lexington-kentucky",
        "https://www.wyndhamhotels.com/hotels/lexington-kentucky/all-hotels",
    ]),
    ("MARRIOTT", [
        "https://www.marriott.com/en-us/search/destination.mi?destinationAddress.city=Lexington"
        "&destinationAddress.stateProvince=KY",
        "https://www.marriott.com/hotels/travel/lexington-kentucky/",
    ]),
    ("IHG", [
        "https://www.ihg.com/destinations/us/en/united-states/kentucky/lexington-hotels",
        "https://www.ihg.com/hotels/us/en/lexington/lexky/hoteldetail",
        "https://www.ihg.com/destinations/us/en/explore?qDest=Lexington,+KY",
    ]),
    ("CHOICE", [
        "https://www.choicehotels.com/kentucky/lexington",
        "https://www.choicehotels.com/kentucky/lexington/hotels",
    ]),
    ("BEST_WESTERN", [
        "https://www.bestwestern.com/en_US/book/hotels-in-lexington.html",
        "https://www.bestwestern.com/en_US/hotels/kentucky/lexington.html",
    ]),
    ("RED_ROOF", [
        "https://www.redroof.com/state/ky/lexington",
        "https://www.redroof.com/location/kentucky/lexington",
    ]),
    ("G6", [
        "https://www.motel6.com/en/kentucky/lexington-hotels.html",
        "https://www.motel6.com/en/motels.ky.lexington.html",
    ]),
    ("ESA", [
        "https://www.extendedstayamerica.com/hotels/ky/lexington",
    ]),
    ("HYATT", [
        "https://www.hyatt.com/explore-hotels/destinations/united-states/kentucky/lexington",
    ]),
    ("SONESTA", [
        "https://www.sonesta.com/destinations/ky/lexington",
    ]),
    ("RADISSON", [
        "https://www.radissonhotels.com/en-us/destination/united-states/kentucky/lexington",
    ]),
])

# What a property URL looks like per family. The captured group carries the
# property code where the family exposes one.
PROPERTY_RE = OrderedDict([
    ("HILTON", r"https://www\.hilton\.com/en/hotels/([a-z0-9]{5,9})-([a-z0-9\-]+)/"),
    ("WYNDHAM", r"(https://www\.wyndhamhotels\.com/[a-z0-9\-]+/[a-z\-]+-kentucky/[a-z0-9\-]+/overview)"),
    ("MARRIOTT", r"https://www\.marriott\.com/(?:[a-z\-]+/)?hotels/([a-z0-9]{5})-([a-z0-9\-]+)/overview"),
    ("IHG", r"(https://www\.ihg\.com/[a-z0-9]+/hotels/us/en/[a-z\-]+/[a-z0-9]{3,7}/hoteldetail)"),
    ("CHOICE", r"(https://www\.choicehotels\.com/kentucky/lexington/[a-z0-9\-]+/[a-z0-9]+)"),
    ("BEST_WESTERN", r"(https://www\.bestwestern\.com/en_US/book/[a-z0-9\-\.]*\d{5,}\.html)"),
    ("RED_ROOF", r"(https://www\.redroof\.com/property/[a-z]{2}/[a-z\-]+/\w+)"),
    ("G6", r"(https://www\.motel6\.com/en/[a-z\-\.]*lexington[a-z0-9\-\.]*\.html)"),
    ("ESA", r"(https://www\.extendedstayamerica\.com/hotels/ky/lexington/[a-z0-9\-]+)"),
    ("HYATT", r"(https://www\.hyatt\.com/[a-z\-]+/en-US/[a-z0-9]+)"),
    ("SONESTA", r"(https://www\.sonesta\.com/[a-z0-9\-]+/ky/lexington/[a-z0-9\-]+)"),
    ("RADISSON", r"(https://www\.radissonhotels\.com/en-us/hotels/[a-z0-9\-]+)"),
])


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def cached_get(url):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    hp, mp = os.path.join(CACHE, key + ".html"), os.path.join(CACHE, key + ".json")
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding="utf-8"))
        return meta, (open(hp, "rb").read() if os.path.exists(hp) else b"")
    time.sleep(SPACING)
    st, final, body = get(url)
    meta = {"url": url, "status": st, "final_url": final, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest() if body else "",
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if body:
        open(hp, "wb").write(body)
    json.dump(meta, open(mp, "w", encoding="utf-8"))
    return meta, body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    families = OrderedDict()
    requests = 0
    for fam, urls in CITY_PAGES.items():
        blk = OrderedDict([("family", fam), ("attempts", []), ("property_urls", []),
                           ("property_codes", [])])
        rx = re.compile(PROPERTY_RE[fam], re.I)
        for u in urls:
            meta, body = cached_get(u)
            requests += 1
            html = body.decode("utf-8", "replace") if body else ""
            hits = rx.findall(html)
            blk["attempts"].append(OrderedDict([
                ("url", u), ("status", meta["status"]), ("bytes", meta["bytes"]),
                ("sha256", meta["sha256"]), ("property_matches", len(hits))]))
            for h in hits:
                if isinstance(h, tuple) and len(h) == 2:
                    code, slug = h
                    blk["property_codes"].append(OrderedDict([("code", code), ("slug", slug)]))
                    if fam == "HILTON":
                        blk["property_urls"].append(
                            "https://www.hilton.com/en/hotels/%s-%s/" % (code, slug))
                    else:
                        blk["property_urls"].append(
                            "https://www.marriott.com/en-us/hotels/%s-%s/overview/" % (code, slug))
                else:
                    blk["property_urls"].append(h if isinstance(h, str) else h[0])
            if hits:
                break
        seen = set()
        uniq = []
        for u in blk["property_urls"]:
            if u in seen:
                continue
            seen.add(u)
            uniq.append(u)
        blk["property_urls"] = sorted(uniq)
        cseen = set()
        cu = []
        for c in blk["property_codes"]:
            if c["code"] in cseen:
                continue
            cseen.add(c["code"])
            cu.append(c)
        blk["property_codes"] = sorted(cu, key=lambda c: c["code"])
        blk["outcome"] = ("ANSWERED_WITH_PROPERTIES" if blk["property_urls"]
                          else "ANSWERED_NO_PROPERTIES"
                          if any(a["status"] == 200 for a in blk["attempts"])
                          else "REFUSED")
        families[fam] = blk
        print(f"{fam:14s} {blk['outcome']:24s} urls={len(blk['property_urls'])}", flush=True)

    counts = Counter(b["outcome"] for b in families.values())
    report = OrderedDict([
        ("schema", "ptf-brand-city-page-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "7 -- brand inventory audit via each brand's OWN city page"),
        ("as_of", args.as_of),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", requests),
        ("why_this_lane_exists",
         "This order began Hilton as a sitemap walk, the way Dayton and Cleveland did: "
         "robots.txt -> sitemap index -> roughly 1,185 child sitemaps at 1.5 s spacing. After "
         "about ninety minutes it had yielded nothing and it was stopped. ONE request to "
         "Hilton's own Lexington city page returned twenty property codes. A brand's own city "
         "page beats its sitemap; an owned harvest beats both. The sitemap walk remains the "
         "right lane for a brand with no city page, and the wrong default for a brand with one."),
        ("scope_caveat",
         "A brand listing a property under 'Lexington' is stating its own marketing scope, not "
         "this market's boundary. Hilton's Lexington page includes a Nicholasville (Jessamine "
         "County) property. These URLs are ROUTING and IDENTITY leads; admission is decided "
         "downstream on the address, by point-in-polygon against the county boundary."),
        ("bare_chain_name_proof",
         "Hilton's own Lexington city page lists TWO Embassy Suites (lexeses UK Coldstream, "
         "lexlges Lexington Green) and THREE Homewood Suites (lexhbhw Hamburg, lexkyhw Fayette "
         "Mall, lexxghw Lexington). The census carries OSM rows named simply 'Embassy Suites' "
         "and 'Homewood Suites'. This is the concrete proof that a bare chain name proposes a "
         "brand and never decides a property."),
        ("totals", OrderedDict([
            ("families_probed", len(families)),
            ("outcomes", OrderedDict(sorted(counts.items()))),
            ("property_urls", sum(len(b["property_urls"]) for b in families.values())),
        ])),
        ("families", families),
    ])
    out = args.out or os.path.join(REPORTS, "lexington_ky_brand_city_page_lane_001.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print(json.dumps(report["totals"], indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
