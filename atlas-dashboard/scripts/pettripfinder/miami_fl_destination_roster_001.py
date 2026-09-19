"""PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 -- Phase 9D: the destination-organisation roster (Greater Miami
Convention & Visitors Bureau, miamiandbeaches.com).

The GMCVB is the official destination marketing organisation for Miami-Dade County -- Miami AND the Beaches. Its
own public sitemap (``/sitemap.xml``, allowed to every user agent by its robots.txt) lists every hotel member
listing at ``/l/hotels/<slug>/<id>``. Each listing page carries the bureau's own schema.org ``Hotel`` JSON-LD
(name, street, city, ZIP, phone, coordinates) and the bureau's "Visit Website" link. This helper reads the
sitemap once and every hotel listing once, with a plain client and a polite delay.

The City of Miami Beach's own visitor sites (experiencemiamibeach.com, miamibeachvca.com) are Webflow marketing
sites with no lodging roster; they are probed once and recorded, not silently skipped.

WHAT A ROSTER ROW IS
--------------------
Tier-2 discovery and identity evidence. A bureau ZIP can be the mailing ZIP; a bureau phone can be a central
reservations line; a bureau website can be a brand home page. None of them keys a building on its own and none
admits one. The bureau's "pet friendly" amenity words, if any, are NEVER a policy and are not read here at all.

Output:
  launch_packages/pettripfinder/markets/reports/miami_fl_destination_roster_001.json
  data/acquisition/miami_fl_roster_001/<sha256>.bin
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import direct_http_capture as DHC  # noqa: E402

WORK_ORDER = "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "miami-fl"
DOCS = os.path.join(_DASH, "data", "acquisition", "miami_fl_roster_001")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "miami_fl_destination_roster_001.json")
GMCVB = "https://www.miamiandbeaches.com"
SITEMAP = GMCVB + "/sitemap.xml"
_HOTEL_LISTING = re.compile(r"^https://www\.miamiandbeaches\.com/l/hotels/([a-z0-9-]+)/(\d+)$")
_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_LDJSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
_WEBSITE = re.compile(r'<a href="([^"]+)"[^>]*aria-label="Visit Website', re.I)
PROBED_ONLY = [
    ("Miami Beach Visitor & Convention Authority", "https://www.miamibeachvca.com/"),
    ("Experience Miami Beach", "https://www.experiencemiamibeach.com/"),
]


def persist(body):
    if not body:
        return None
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    p = os.path.join(DOCS, digest + ".bin")
    if not os.path.exists(p):
        with open(p, "wb") as fh:
            fh.write(body)
    return digest


def parse_listing(text):
    hotel = None
    for m in _LDJSON.finditer(text):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for item in (data if isinstance(data, list) else [data]):
            if isinstance(item, dict) and item.get("@type") in ("Hotel", "LodgingBusiness", "Resort", "Motel",
                                                                  "BedAndBreakfast"):
                hotel = item
                break
        if hotel:
            break
    if not hotel:
        return None
    addr = hotel.get("address") or {}
    geo = hotel.get("geo") or {}
    web = _WEBSITE.search(text)
    return OrderedDict([
        ("name", html.unescape((hotel.get("name") or "").strip())),
        ("schema_type", hotel.get("@type")),
        ("street", html.unescape((addr.get("streetAddress") or "").strip())),
        ("city", (addr.get("addressLocality") or "").strip()),
        ("region", (addr.get("addressRegion") or "FL").strip()),
        ("stated_postal_code", (addr.get("postalCode") or "").strip()[:5]),
        ("stated_phone", (hotel.get("telephone") or "").strip()),
        ("website", html.unescape(web.group(1)) if web else ""),
        ("lat", geo.get("latitude")), ("lng", geo.get("longitude")),
    ])


def build(delay=0.6):
    requests = 0
    sm = DHC.fetch(SITEMAP, timeout=60)
    requests += 1
    sm_body = sm.body or b""
    sm_sha = persist(sm_body)
    urls = sorted({u for u in _LOC.findall(sm_body.decode("utf-8", "replace")) if _HOTEL_LISTING.match(u)},
                  key=lambda u: int(_HOTEL_LISTING.match(u).group(2)))
    documents, listings, failures = [], [], []
    for n, url in enumerate(urls, start=1):
        f = DHC.fetch(url, timeout=45)
        requests += 1
        body = f.body or b""
        sha = persist(body) if f.status == 200 else None
        documents.append(OrderedDict([("url", url), ("status", f.status), ("bytes", len(body)), ("sha256", sha)]))
        row = parse_listing(body.decode("utf-8", "replace")) if f.status == 200 else None
        if not row:
            failures.append(OrderedDict([("url", url), ("status", f.status),
                                         ("why", "NO_HOTEL_JSON_LD" if f.status == 200 else "HTTP_%s" % f.status)]))
        else:
            m = _HOTEL_LISTING.match(url)
            row["recid"] = int(m.group(2))
            row["bureau_subcategory"] = "Hotels"
            row["bureau_all_subcategories"] = ["Hotels"]
            row["listing_url"] = url
            row["document_sha256"] = sha
            listings.append(row)
        if n % 50 == 0:
            print("  gmcvb %d/%d" % (n, len(urls)), flush=True)
        time.sleep(delay)
    listings.sort(key=lambda x: x["recid"])
    bureaus = OrderedDict()
    bureaus["Greater Miami Convention & Visitors Bureau"] = OrderedDict([
        ("bureau", "Greater Miami Convention & Visitors Bureau"), ("base_url", GMCVB),
        ("sitemap", OrderedDict([("url", SITEMAP), ("status", sm.status), ("bytes", len(sm_body)), ("sha256", sm_sha),
                                 ("hotel_listing_urls", len(urls))])),
        ("disposition", "ANSWERED_THIS_CLIENT" if listings else "ANSWERED_BUT_NO_LISTINGS"),
        ("documents", documents), ("parse_failures", failures),
        ("listing_count", len(listings)),
        ("by_city", OrderedDict(sorted(Counter(l["city"] for l in listings).items()))),
        ("listings", listings),
    ])
    for name, url in PROBED_ONLY:
        f = DHC.fetch(url, timeout=30)
        requests += 1
        text = (f.body or b"").decode("utf-8", "replace")
        bureaus[name] = OrderedDict([
            ("bureau", name), ("base_url", url), ("status", f.status),
            ("disposition", "NO_LODGING_ROSTER__MARKETING_SITE" if f.status == 200 else "STATUS_%s" % f.status),
            ("webflow_site", "Webflow" in text[:600]),
            ("documents", []), ("listing_count", 0), ("listings", []),
        ])
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9D -- Greater Miami destination-organisation roster (tier 2 discovery and identity evidence)"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", requests),
        ("a_roster_row_is_not_a_policy",
         "Discovery and identity evidence only. The bureau's amenity words are never read as a pet policy."),
        ("bureaus", bureaus),
        ("listing_count_total", sum(b["listing_count"] for b in bureaus.values())),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("total listings:", rep["listing_count_total"], "requests:", rep["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
