"""PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 -- Phase 4D: the official destination
lodging roster (cloned from the Boone - Blowing Rock NC Simpleview destination-roster helper).

WHAT THIS IS
------------
Visit Hickory Metro (``visithickorync.com``, the Hickory Metro Convention & Visitors
Bureau and the Hickory-Conover Tourism Development Authority -- Catawba County's
official visitor site) publishes its member lodging in a Simpleview CRM under the
"Places to Stay" category (catid 8), with the bureau's own sub-categories as its
/places-to-stay/ pages declare them (``listingsubcats``): "Hotel" (72), "Extended
Stay" (73), "Bed and Breakfast" (70, the "Historic & Boutique Stays" page) and
"Campgrounds & RV" (71). Its listings span Hickory, Conover, Newton, Claremont,
Catawba and the Hickory Metro counties (Alexander, Burke, Caldwell).

This lane reads the site's OWN listing service -- the same
``plugins_listings_listings/find`` call its category pages make in the browser --
once per lodging sub-category, with the public simple token the site itself issues.
Each response is persisted by its own sha256, and every listing's sub-category is
recorded verbatim so the census can refuse campground listings BY DECISION.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are carried as
``stated_postal_code`` and never key a building on their own; its phone as
``stated_phone``. Nothing the bureau says about pets (its "Pet Friendly" tag
included) is read as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/hickory_nc_destination_roster_001.json
  data/acquisition/hickory_nc_destination_001/<sha256>.bin
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

from scripts.pettripfinder import hickory_nc_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hickory-nc"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "hickory_nc_destination_roster_001.json")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "hickory_nc_destination_001")
SITE = "https://www.visithickorync.com"
TOKEN_URL = SITE + "/plugins/core/get_simple_token/"
FIND_URL = SITE + "/includes/rest_v2/plugins_listings_listings/find/"
CRAWL_DELAY_SECONDS = 2.0

#: The bureau's own "Places to Stay" sub-categories, as its category pages declare them
#: (``listingsubcats`` on /places-to-stay/<page>/), measured 2026-09-14.
SUBCATEGORIES = OrderedDict([
    ("72", "Hotel"),
    ("73", "Extended Stay"),
    ("70", "Bed and Breakfast"),
    ("71", "Campgrounds & RV"),
])
FIELDS = ("recid", "title", "url", "address1", "city", "state", "zip", "phone", "weburl",
          "latitude", "longitude", "primary_category", "categories", "regionname")


def _find(subcatid, token, stats):
    query = {"filter": {"$and": [{"filter_tags": {"$in": ["site_primary_subcatid_%s" % subcatid]}}]},
             "options": {"limit": 1000, "skip": 0, "count": True, "castDocs": False,
                         "fields": {f: 1 for f in FIELDS}}}
    url = "%s?json=%s&token=%s" % (FIND_URL, urllib.parse.quote(json.dumps(query, sort_keys=True)), token)
    row, body = BI.fetch(url, stats, timeout=60)
    row["url"] = "%s [subcatid=%s]" % (FIND_URL, subcatid)
    try:
        docs = json.loads(body.decode("utf-8", "replace"))["docs"]
    except Exception:  # noqa: BLE001
        docs = {"count": None, "docs": []}
    return row, docs


def build():
    stats = BI.Stats()
    tok_row, tok_body = BI.fetch(TOKEN_URL, stats)
    token = tok_body.decode("utf-8", "replace").strip()
    tok_row["sha256"] = None  # a session token is not evidence; never persisted as a document
    by_recid = OrderedDict()
    calls = []
    for subcatid, label in SUBCATEGORIES.items():
        time.sleep(CRAWL_DELAY_SECONDS)
        row, docs = _find(subcatid, token, stats)
        calls.append(OrderedDict([("subcategory_id", subcatid), ("subcategory", label),
                                  ("status", row["status"]), ("document_sha256", row["sha256"]),
                                  ("bytes", row["bytes"]), ("fetched_at", row["fetched_at"]),
                                  ("count", docs.get("count")), ("returned", len(docs.get("docs") or []))]))
        for d in docs.get("docs") or []:
            rec = by_recid.setdefault(d.get("recid"), OrderedDict([("doc", d), ("seen_in", []),
                                                                   ("row", row)]))
            rec["seen_in"].append(label)
    listings = []
    for recid, rec in by_recid.items():
        d = rec["doc"]
        prim = d.get("primary_category") or {}
        link = d.get("url") or ""
        if link and not link.startswith("http"):
            link = SITE + "/" + link.lstrip("/")
        listings.append(OrderedDict([
            ("listing_url", link), ("recid", recid), ("status", rec["row"]["status"]),
            ("document_sha256", rec["row"]["sha256"]), ("document_bytes", rec["row"]["bytes"]),
            ("fetched_at", rec["row"]["fetched_at"]),
            ("bureau_category", prim.get("catname")),
            ("bureau_subcategory", prim.get("subcatname")),
            ("bureau_all_subcategories", sorted({c.get("subcatname") for c in d.get("categories") or []
                                                 if c.get("subcatname")})),
            ("bureau_region", d.get("regionname")),
            ("name", html.unescape(d.get("title") or "").strip()),
            ("street", (d.get("address1") or "").strip()),
            ("city", (d.get("city") or "").strip()),
            ("region", (d.get("state") or "").strip()),
            ("stated_postal_code", (d.get("zip") or "").strip()[:5]),
            ("stated_phone", (d.get("phone") or "").strip()),
            ("lat", d.get("latitude")), ("lng", d.get("longitude")),
            ("website", (d.get("weburl") or "").split("?")[0].strip()),
        ]))
    listings.sort(key=lambda r: (r["name"].lower(), r["recid"] or 0))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "4D -- the official Visit Hickory Metro (Hickory Metro CVB) lodging roster"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "https://www.visithickorync.com -- the site's own listing service, once per 'Places to "
                   "Stay' sub-category (Hickory Metro Convention & Visitors Bureau)"),
        ("service_calls", calls),
        ("crawl_delay_seconds", CRAWL_DELAY_SECONDS),
        ("coverage", "EVERY_PLACES_TO_STAY_SUBCATEGORY"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing the bureau publishes about pets is read; the roster is identity evidence only."),
        ("listing_count", len(listings)),
        ("lodging_by_subcategory", OrderedDict(sorted(Counter(l["bureau_subcategory"] or "" for l in listings).items()))),
        ("non_lodging_listing_pages_by_category", OrderedDict(sorted(Counter(
            l["bureau_category"] or "" for l in listings if l["bureau_category"] != "Places to Stay").items()))),
        ("unreadable_listing_pages", [c for c in calls if c["status"] != 200]),
        ("listings", listings),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", doc["listing_count"], dict(doc["lodging_by_subcategory"]))
    print("calls:", [(c["subcategory"], c["status"], c["count"]) for c in doc["service_calls"]])
    print("requests:", doc["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
