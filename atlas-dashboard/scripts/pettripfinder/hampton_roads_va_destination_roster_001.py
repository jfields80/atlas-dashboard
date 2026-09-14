"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- Phase 8D-8M: the official destination lodging rosters
(cloned from the Richmond VA destination-roster helper; one bureau per independent city).

WHAT THIS IS
------------
Hampton Roads has no single bureau: each independent city runs its own. This lane reads
every city bureau whose own lodging listings a plain client (or, for a bureau that refuses a
plain client, the attended browser on the bureau's own origin) can read:

  * Simpleview CRM bureaus (Visit Chesapeake, Visit Newport News): the site's OWN listing
    service -- the same ``plugins_listings_listings/find`` call its lodging pages make in the
    browser -- once, for every listing whose categories carry the bureau's lodging category,
    with the public simple token the site itself issues. Crawl-delay honoured between calls.
  * Browser-read rosters (committed under ``markets/staging/hampton-roads-va/raw_captures``
    with the page-computed canonical-JSON sha256 checked here): bureaus whose site refused
    this plain client (403) and served the attended browser.

Every response is persisted by its own sha256, and every listing's sub-categories are
recorded verbatim so the census can refuse vacation-rental, condo, campground and group
listings BY DECISION.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are carried as ``stated_postal_code``
and never key a building on their own; its phone as ``stated_phone``. Nothing a bureau says
about pets (a "Pet Friendly" sub-category included) is read as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/hampton_roads_va_destination_roster_001.json
  data/acquisition/hampton_roads_va_destination_001/<sha256>.bin
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import sys
import time
import urllib.parse
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import hampton_roads_va_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hampton-roads-va"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "hampton_roads_va_destination_roster_001.json")
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "hampton-roads-va", "raw_captures")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "hampton_roads_va_destination_001")
CRAWL_DELAY_SECONDS = 2.0
FIELDS = ("recid", "title", "url", "address1", "city", "state", "zip", "phone", "weburl",
          "latitude", "longitude", "loc", "primary_category", "categories", "regionname", "region")

#: (bureau, site, lodging catid) -- the lodging category each bureau's own listing data carries.
SIMPLEVIEW_BUREAUS = [
    ("Visit Chesapeake", "https://www.visitchesapeake.com", "2"),
    ("Visit Newport News", "https://www.visitnewportnews.com", "1571"),
]

#: Browser-read rosters: (bureau, site, lodging catid, committed payload, its page-computed sha256).
#: Visit Virginia Beach refuses a plain client (403). Its own WordPress listing API (``/wp-json/wp/v2/mdb_listing``,
#: the Simpleview CRM mirror the site renders from) served the attended browser all 1,268 listings; the rows kept are
#: every listing carrying a category in the CRM's own "Accommodations" group (165), as compact rows
#: [recid, title, listing path, street, city, zip, phone, website, lat, lng, [Accommodations sub-categories]].
#: The WordPress taxonomy filter was measured INERT (every category id returned the same 1,268), so the filter was
#: applied to the CRM categories in the page, never to the site's taxonomy.
BROWSER_BUREAUS = [
    ("Visit Virginia Beach", "https://www.visitvirginiabeach.com", "accommodations", "visitvirginiabeach_rows.json",
     "9e3e56d6f45e88ec329b3e36754f23765989c1032463cead63a365fd51c4d435"),
]


def _compact_to_doc(site, r):
    rid, title, path, street, city, zip_, phone, web, lat, lng, subs = r
    cats = [OrderedDict([("catid", "accommodations"), ("catname", "Accommodations"), ("subcatname", s)]) for s in subs]
    return OrderedDict([
        ("recid", rid), ("title", title), ("url", site + path), ("address1", street), ("city", city), ("state", "VA"),
        ("zip", zip_), ("phone", phone), ("weburl", web), ("latitude", lat), ("longitude", lng),
        ("primary_category", OrderedDict([("catname", "Accommodations"), ("subcatname", subs[0] if subs else "")])),
        ("categories", cats)])


def _find(site, catid, token, stats):
    query = {"filter": {"$and": [{"filter_tags": {"$in": ["catid_%s" % catid]}}]},
             "options": {"limit": 1000, "skip": 0, "count": True, "castDocs": False,
                         "fields": {f: 1 for f in FIELDS}}}
    url = "%s/includes/rest_v2/plugins_listings_listings/find/?json=%s&token=%s" % (
        site, urllib.parse.quote(json.dumps(query, sort_keys=True)), token)
    row, body = BI.fetch(url, stats, timeout=60)
    row["url"] = "%s/includes/rest_v2/plugins_listings_listings/find/ [filter_tags=catid_%s]" % (site, catid)
    try:
        docs = json.loads(body.decode("utf-8", "replace"))["docs"]
    except Exception:  # noqa: BLE001
        docs = {"count": None, "docs": []}
    return row, docs


def _coord(d, axis):
    v = d.get(axis)
    if v is None and isinstance(d.get("loc"), dict):
        coords = d["loc"].get("coordinates") or []
        if len(coords) == 2:
            v = coords[1] if axis == "latitude" else coords[0]
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _listings(bureau, site, catid, docs, row):
    out = []
    for d in docs:
        prim = d.get("primary_category") or {}
        link = d.get("url") or ""
        if link and not link.startswith("http"):
            link = site + "/" + link.lstrip("/")
        subs = sorted({c.get("subcatname") for c in d.get("categories") or []
                       if c.get("subcatname") and str(c.get("catid")) == str(catid)})
        out.append(OrderedDict([
            ("bureau", bureau),
            ("listing_url", link), ("recid", d.get("recid")), ("status", row["status"]),
            ("document_sha256", row["sha256"]), ("document_bytes", row["bytes"]),
            ("fetched_at", row["fetched_at"]),
            ("bureau_category", prim.get("catname")),
            ("bureau_subcategory", prim.get("subcatname")),
            ("bureau_all_subcategories", subs or sorted({c.get("subcatname") for c in d.get("categories") or []
                                                         if c.get("subcatname")})),
            ("bureau_region", d.get("regionname") or d.get("region")),
            ("name", html.unescape(d.get("title") or "").strip()),
            ("street", (d.get("address1") or "").strip()),
            ("city", (d.get("city") or "").strip()),
            ("region", (d.get("state") or "").strip()),
            ("stated_postal_code", str(d.get("zip") or "").strip()[:5]),
            ("stated_phone", (d.get("phone") or "").strip()),
            ("lat", _coord(d, "latitude")), ("lng", _coord(d, "longitude")),
            ("website", (d.get("weburl") or "").split("?")[0].strip()),
        ]))
    return out


def build():
    stats = BI.Stats()
    calls, listings = [], []
    for bureau, site, catid in SIMPLEVIEW_BUREAUS:
        tok_row, tok_body = BI.fetch(site + "/plugins/core/get_simple_token/", stats)
        token = tok_body.decode("utf-8", "replace").strip()
        time.sleep(CRAWL_DELAY_SECONDS)
        row, docs = _find(site, catid, token, stats)
        calls.append(OrderedDict([("bureau", bureau), ("filter_tag", "catid_%s" % catid), ("lane", "PLAIN_CLIENT"),
                                  ("status", row["status"]), ("document_sha256", row["sha256"]), ("bytes", row["bytes"]),
                                  ("fetched_at", row["fetched_at"]), ("count", docs.get("count")),
                                  ("returned", len(docs.get("docs") or []))]))
        listings.extend(_listings(bureau, site, catid, docs.get("docs") or [], row))
        time.sleep(CRAWL_DELAY_SECONDS)
    for bureau, site, catid, name, want in BROWSER_BUREAUS:
        raw = json.load(open(os.path.join(RAW, name), encoding="utf-8"))
        got = hashlib.sha256(json.dumps(raw, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        if got != want:
            raise SystemExit("roster payload %s digest %s != the browser's %s" % (name, got, want))
        docs = [_compact_to_doc(site, r) if isinstance(r, list) else r for r in raw]
        row = OrderedDict([("status", 200), ("sha256", got), ("bytes", None), ("fetched_at", "2026-09-14")])
        calls.append(OrderedDict([("bureau", bureau), ("filter_tag", "catid_%s" % catid), ("lane", "ATTENDED_BROWSER"),
                                  ("status", 200), ("document_sha256", got), ("payload", name),
                                  ("returned", len(docs))]))
        listings.extend(_listings(bureau, site, catid, docs, row))
    listings.sort(key=lambda r: (r["name"].lower(), r["bureau"], r["recid"] or 0))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "8D-8M -- the official Hampton Roads city bureaus' lodging rosters"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "each city bureau's own listing service, every listing tagged with the bureau's lodging category"),
        ("service_calls", calls),
        ("crawl_delay_seconds", CRAWL_DELAY_SECONDS),
        ("coverage", "EVERY_LISTING_IN_EACH_READ_BUREAU_LODGING_CATEGORY"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing a bureau publishes about pets is read; the roster is identity evidence only."),
        ("listing_count", len(listings)),
        ("listings_by_bureau", OrderedDict(sorted(Counter(l["bureau"] for l in listings).items()))),
        ("lodging_by_subcategory", OrderedDict(sorted(Counter(l["bureau_subcategory"] or "" for l in listings).items()))),
        ("listings_by_municipality", OrderedDict(sorted(Counter(l["city"] for l in listings).items()))),
        ("unreadable_listing_pages", [c for c in calls if c["status"] != 200]),
        ("listings", listings),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", doc["listing_count"], dict(doc["listings_by_bureau"]))
    print("subcategories:", dict(doc["lodging_by_subcategory"]))
    print("municipalities:", dict(doc["listings_by_municipality"]))
    print("calls:", [(c["bureau"], c["status"], c.get("count"), c["returned"]) for c in doc["service_calls"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
