"""PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 -- Phase 5D-5H: the official destination lodging roster
(cloned from the Boone - Blowing Rock NC destination-roster helper).

WHAT THIS IS
------------
Richmond Region Tourism (``visitrichmondva.com``, the official Visit Richmond VA
destination site) publishes its member lodging in a Simpleview CRM under listing
category 9, whose sub-categories its own "Hotels" pages declare (``listingsubcats``
in the page's listings widget, measured 2026-09-14). Its listings span the City of
Richmond and the Henrico, Chesterfield and Hanover counties, with the bureau's own
Downtown / North / South / West / East-Airport hotel pages.

This lane reads the site's OWN listing service -- the same
``plugins_listings_listings/find`` call its hotel pages make in the browser -- once
for every listing whose filter tags carry category 9, with the public simple token
the site itself issues. The robots ``Crawl-delay: 2`` is honoured between calls. The
response is persisted by its own sha256, and every listing's sub-categories are
recorded verbatim so the census can refuse apartment, corporate-housing and
vacation-rental listings BY DECISION.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are carried as
``stated_postal_code`` and never key a building on their own; its phone as
``stated_phone``. Nothing the bureau says about pets (its "Pet-Friendly Hotels"
page included) is read as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/richmond_va_destination_roster_001.json
  data/acquisition/richmond_va_destination_001/<sha256>.bin
"""
from __future__ import annotations

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

from scripts.pettripfinder import richmond_va_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "richmond-va"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "richmond_va_destination_roster_001.json")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "richmond_va_destination_001")
SITE = "https://www.visitrichmondva.com"
TOKEN_URL = SITE + "/plugins/core/get_simple_token/"
FIND_URL = SITE + "/includes/rest_v2/plugins_listings_listings/find/"
CRAWL_DELAY_SECONDS = 2.0
#: The bureau's own lodging category, as its /hotels/ page's listings widget declares it.
LODGING_CATEGORY_TAG = "catid_9"
FIELDS = ("recid", "title", "url", "address1", "city", "state", "zip", "phone", "weburl",
          "latitude", "longitude", "loc", "primary_category", "categories", "regionname", "region")


def _find(token, stats):
    query = {"filter": {"$and": [{"filter_tags": {"$in": [LODGING_CATEGORY_TAG]}}]},
             "options": {"limit": 1000, "skip": 0, "count": True, "castDocs": False,
                         "fields": {f: 1 for f in FIELDS}}}
    url = "%s?json=%s&token=%s" % (FIND_URL, urllib.parse.quote(json.dumps(query, sort_keys=True)), token)
    row, body = BI.fetch(url, stats, timeout=60)
    row["url"] = "%s [filter_tags=%s]" % (FIND_URL, LODGING_CATEGORY_TAG)
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


def build():
    stats = BI.Stats()
    tok_row, tok_body = BI.fetch(TOKEN_URL, stats)
    token = tok_body.decode("utf-8", "replace").strip()
    tok_row["sha256"] = None  # a session token is not evidence; never persisted as a document
    time.sleep(CRAWL_DELAY_SECONDS)
    row, docs = _find(token, stats)
    calls = [OrderedDict([("filter_tag", LODGING_CATEGORY_TAG), ("status", row["status"]),
                          ("document_sha256", row["sha256"]), ("bytes", row["bytes"]),
                          ("fetched_at", row["fetched_at"]), ("count", docs.get("count")),
                          ("returned", len(docs.get("docs") or []))])]
    listings = []
    for d in docs.get("docs") or []:
        prim = d.get("primary_category") or {}
        link = d.get("url") or ""
        if link and not link.startswith("http"):
            link = SITE + "/" + link.lstrip("/")
        subs = sorted({c.get("subcatname") for c in d.get("categories") or []
                       if c.get("subcatname") and str(c.get("catid")) == "9"})
        listings.append(OrderedDict([
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
            ("stated_postal_code", (d.get("zip") or "").strip()[:5]),
            ("stated_phone", (d.get("phone") or "").strip()),
            ("lat", _coord(d, "latitude")), ("lng", _coord(d, "longitude")),
            ("website", (d.get("weburl") or "").split("?")[0].strip()),
        ]))
    listings.sort(key=lambda r: (r["name"].lower(), r["recid"] or 0))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "5D-5H -- the official Visit Richmond VA (Richmond Region Tourism) lodging roster"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "https://www.visitrichmondva.com -- the site's own listing service, every listing tagged with the "
                   "bureau's lodging category (Richmond Region Tourism)"),
        ("service_calls", calls),
        ("crawl_delay_seconds", CRAWL_DELAY_SECONDS),
        ("coverage", "EVERY_LISTING_IN_THE_BUREAU_LODGING_CATEGORY"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing the bureau publishes about pets is read; the roster is identity evidence only."),
        ("listing_count", len(listings)),
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
    print("listings:", doc["listing_count"], dict(doc["lodging_by_subcategory"]))
    print("municipalities:", dict(doc["listings_by_municipality"]))
    print("calls:", [(c["filter_tag"], c["status"], c["count"]) for c in doc["service_calls"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
