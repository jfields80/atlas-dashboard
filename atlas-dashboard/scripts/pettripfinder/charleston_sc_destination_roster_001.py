"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- Phase 6D-6I: the official destination lodging roster.

WHAT THIS IS
------------
The Charleston Area Convention & Visitors Bureau (``charlestoncvb.com``, the
official Explore Charleston destination site, Simpleview CMS) publishes its member
lodging under "Plan Your Trip > Lodging" in its own categories: Hotels, Bed &
Breakfasts, Cottages, Vacation Rentals, Extended Stay, Historic Inns and Beach
Resorts. Unlike Visit Savannah, the site answers a PLAIN HTTPS client, so this
lane reads every category page, every listing URL the bureau's own listings
sitemap names under Lodging, and every listing page, from a plain client.

Each listing page carries the bureau's own schema.org Hotel JSON-LD (name, street,
municipality, state, telephone, pin) and a "View Website" link. It carries NO
postal code. Every document is persisted as returned, addressed by sha256, under
``data/acquisition/charleston_sc_cvb_001/``.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its phone is carried as ``stated_phone``; it
states no postal code, so ``stated_postal_code`` is empty and membership is never
decided on a roster row alone. Nothing the bureau says about pets is read. Its
categories are recorded verbatim so the census can refuse vacation-rental and
cottage listings BY DECISION.

Output:
  launch_packages/pettripfinder/markets/reports/charleston_sc_destination_roster_001.json
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import charleston_sc_brand_inventory_001 as B  # noqa: E402

WORK_ORDER = "PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "charleston-sc"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "charleston_sc_destination_roster_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "charleston_sc_cvb_001")
SITE = "https://www.charlestoncvb.com"
#: The bureau's own lodging categories, as its category pages are titled.
CATEGORY_PAGES = OrderedDict([
    ("/plan-your-trip/lodging~123/hotels~847/", "Hotels"),
    ("/plan-your-trip/lodging~123/bed-breakfasts~615/", "Bed & Breakfasts"),
    ("/plan-your-trip/lodging~123/historic-inns~614/", "Historic Inns"),
    ("/plan-your-trip/lodging~123/extended-stay~1079/", "Extended Stay"),
    ("/plan-your-trip/lodging~123/beach-resorts~622/", "Beach Resorts"),
    ("/plan-your-trip/lodging~123/cottages~1080/", "Cottages"),
    ("/plan-your-trip/lodging~123/vacation-rentals~846/", "Vacation Rentals"),
    ("/plan-your-trip/lodging~123/", "Lodging"),
])
LISTINGS_SITEMAP = SITE + "/cvb-plan-visit/ajax.php?method=sitemap_listings&domain=visitors"
_LISTING = re.compile(r"(/plan-your-trip/lodging~123/([a-z0-9-]+)~(\d+)/[a-z0-9-]+~(\d+)\.html)")
_SLUG_CAT = {path.split("/")[3].split("~")[0]: label for path, label in CATEGORY_PAGES.items()
             if path.count("/") > 3}


def _jsonld_lodging(text):
    for m in re.finditer(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", text, re.S | re.I):
        try:
            j = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        for x in (j if isinstance(j, list) else [j]):
            if isinstance(x, dict) and isinstance(x.get("address"), dict):
                return x
    return {}


def read_listing(path):
    st = B.Stats()
    row, body = B.fetch(SITE + path, st, timeout=40)
    text = body.decode("utf-8", "replace")
    ld = _jsonld_lodging(text)
    a = ld.get("address") or {}
    g = ld.get("geo") or {}
    web = re.search(r"trackEvent\('Interact With Businesses','Visit Website'[^)]*\)\"[^>]*href=\"(https?://[^\"]+)\"", text)

    def f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    return OrderedDict([
        ("path", path), ("status", row["status"]), ("sha256", row["sha256"]), ("bytes", row["bytes"]),
        ("fetched_at", row["fetched_at"]),
        ("name", html.unescape(ld.get("name") or "").strip()),
        ("street", html.unescape(a.get("streetAddress") or "").strip()),
        ("city", html.unescape(a.get("addressLocality") or "").strip()),
        ("region", (a.get("addressRegion") or "").strip()),
        ("phone", (ld.get("telephone") or "").strip()),
        ("lat", f(g.get("latitude"))), ("lng", f(g.get("longitude"))),
        ("website", html.unescape(web.group(1)).split("?")[0] if web else ""),
        ("schema_type", ld.get("@type")),
    ])


def build():
    t0 = time.time()
    B.DOCS = DOCS
    stats = B.Stats()
    cats = OrderedDict()
    pages = OrderedDict()
    for path, label in CATEGORY_PAGES.items():
        row, body = B.fetch(SITE + path, stats, timeout=40)
        found = sorted({m[0] for m in _LISTING.findall(body.decode("utf-8", "replace"))})
        row["listings_found"] = len(found)
        pages[path] = row
        for p in found:
            cats.setdefault(p, set()).add(label)
    row, body = B.fetch(LISTINGS_SITEMAP, stats, timeout=40)
    sm = sorted({m[0] for m in _LISTING.findall(body.decode("utf-8", "replace"))})
    row["lodging_listings_found"] = len(sm)
    pages["listings_sitemap"] = row
    for p in sm:
        cats.setdefault(p, set())
    # the category a listing's own URL is filed under is the bureau's own typing too
    for p in list(cats):
        slug = _LISTING.search(p).group(2)
        if slug in _SLUG_CAT:
            cats[p].add(_SLUG_CAT[slug])
    paths = sorted(cats)
    with ThreadPoolExecutor(max_workers=6) as ex:
        reads = list(ex.map(read_listing, paths))
    # one listing per bureau record id (a listing filed under two categories has two URLs)
    by_id = OrderedDict()
    for r in reads:
        rid = int(_LISTING.search(r["path"]).group(4))
        prev = by_id.get(rid)
        if prev is None:
            by_id[rid] = (r, set(cats[r["path"]]))
        else:
            prev[1].update(cats[r["path"]])
    listings = []
    for rid, (r, labels) in by_id.items():
        subs = sorted(labels - {"Lodging"}) or ["Lodging"]
        listings.append(OrderedDict([
            ("listing_url", SITE + r["path"]), ("recid", rid), ("status", r["status"]),
            ("document_sha256", r["sha256"]), ("document_bytes", r["bytes"]), ("fetched_at", r["fetched_at"]),
            ("bureau_category", "Lodging"),
            ("bureau_subcategory", subs[0]),
            ("bureau_all_subcategories", subs),
            ("bureau_region", ""),
            ("name", r["name"]), ("street", r["street"]), ("city", r["city"]), ("region", r["region"]),
            ("stated_postal_code", ""), ("stated_phone", r["phone"]),
            ("lat", r["lat"]), ("lng", r["lng"]), ("website", r["website"]),
            ("schema_type", r["schema_type"]),
        ]))
    listings.sort(key=lambda r: (r["name"].lower(), r["recid"]))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "6D-6I -- the official Charleston Area CVB (Explore Charleston) lodging roster"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", SITE + " -- every Lodging category page, the bureau's own listings sitemap and every lodging "
                          "listing page, read from a plain HTTPS client"),
        ("category_pages", CATEGORY_PAGES),
        ("category_page_reads", pages),
        ("coverage", "EVERY_LODGING_CATEGORY_PAGE_AND_SITEMAP_LISTING"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats.requests + len(paths)),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing the bureau publishes about pets is read; the roster is identity evidence only."),
        ("no_postal_code",
         "The bureau's listing JSON-LD states street, municipality, state, phone and pin but no postal code; "
         "a roster row never decides membership on its own."),
        ("documents_persisted_at", os.path.relpath(DOCS, _DASH).replace("\\", "/")),
        ("seconds", round(time.time() - t0, 1)),
        ("listing_count", len(listings)),
        ("lodging_by_subcategory", OrderedDict(sorted(Counter(l["bureau_subcategory"] for l in listings).items()))),
        ("listings_by_municipality", OrderedDict(sorted(Counter(l["city"] for l in listings).items()))),
        ("unreadable_listing_pages", [l["listing_url"] for l in listings if l["status"] != 200]),
        ("listings", listings),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", doc["listing_count"], dict(doc["lodging_by_subcategory"]))
    print("municipalities:", dict(doc["listings_by_municipality"]))
    print("unreadable:", len(doc["unreadable_listing_pages"]), "seconds", doc["seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
