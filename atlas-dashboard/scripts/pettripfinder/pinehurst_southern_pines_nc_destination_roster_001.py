"""PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001 -- Phase 4B: the official destination
lodging roster (cloned from the Boone - Blowing Rock NC destination-roster helper).

WHAT THIS IS
------------
The Pinehurst, Southern Pines, Aberdeen Area Convention & Visitors Bureau
(``homeofgolf.com``, Moore County's official destination site) publishes its member
lodging on ``/lodging/`` from its own partner directory, under the bureau's own
categories: "Lodging", "Lodging » Hotels / Inns", "Lodging » Resorts", "Lodging »
B&Bs", "Lodging » Condos / Villas", "Lodging » RV/Campground" and "Lodging » Unique
Venue".

The page renders the list in the browser from the bureau's public search index: its
``data-info`` block names the application, the search-only key and the index
(``prod-visit-pinehurst-nc-listings``), and its ``data-config`` names the exact filter
the page applies. This lane reads that page, takes the index, key and filter FROM
THE PAGE (never typed), and sends the same query the page sends -- once, all
categories, one request. The page and the query response are each persisted by their
own sha256, and every listing's categories are recorded verbatim so the census can
refuse condo / villa, campground and venue listings BY DECISION. robots.txt
disallows only ``/cpresources/``, ``/vendor/`` and ``/directories/``; the lodging page
and the bureau's ``/directory/<slug>/`` pages are allowed.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are carried as
``stated_postal_code`` and never key a building on their own; its phone as
``stated_phone``. Nothing the bureau says about pets is read as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/pinehurst_southern_pines_nc_destination_roster_001.json
  data/acquisition/pinehurst_southern_pines_nc_destination_001/<sha256>.bin
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import pinehurst_southern_pines_nc_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "pinehurst-southern-pines-nc"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "pinehurst_southern_pines_nc_destination_roster_001.json")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "pinehurst_southern_pines_nc_destination_001")
SITE = "https://homeofgolf.com"
LODGING_PAGE = SITE + "/lodging/"

#: The bureau's hotel-type categories (the census reads every category a listing carries).
_ZIP = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


def _page_config(text):
    """The index, key and filter the bureau's own lodging page declares."""
    m_info = re.search(r'data-info="([^"]*)"', text)
    m_conf = re.search(r'data-config="([^"]*)"', text)
    if not (m_info and m_conf):
        raise SystemExit("the lodging page no longer declares its listing index")
    return json.loads(html.unescape(m_info.group(1))), json.loads(html.unescape(m_conf.group(1)))


def _query(info, conf, stats):
    url = "https://%s-dsn.algolia.net/1/indexes/%s/query" % (info["appId"], info["index"])
    body = json.dumps({"filters": conf["filters"], "hitsPerPage": 1000, "page": 0}, sort_keys=True).encode()
    req = urllib.request.Request(url, data=body, headers={
        "X-Algolia-Application-Id": info["appId"], "X-Algolia-API-Key": info["apiKey"],
        "Content-Type": "application/json", "Referer": LODGING_PAGE, "Origin": SITE, "User-Agent": BI.UA})
    stats.requests += 1
    row = OrderedDict([("url", url + " [the lodging page's own filter]"), ("status", None), ("bytes", 0),
                       ("sha256", None), ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))])
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        row["status"] = resp.getcode()
    row["bytes"] = len(raw)
    row["sha256"] = BI.persist(raw)
    return row, json.loads(raw.decode("utf-8"))


def _address(lines):
    """(street, city, stated ZIP) from the bureau's address lines, as printed."""
    lines = [html.unescape(x or "").strip() for x in (lines or []) if (x or "").strip()]
    if not lines:
        return "", "", ""
    street = lines[0]
    tail = lines[-1] if len(lines) > 1 else ""
    # A house number is not a ZIP: "12615 US Hwy 15-501" with no postal line states no postal code.
    z = None
    for ln in lines:
        for m in _ZIP.finditer(re.sub(r"^\s*\d+\s", " ", ln)):
            # The bureau prints "Aberdeen, NC 12615" for 12615 US Hwy 15-501: a North Carolina
            # postal code starts 27 or 28, and a house number copied into the ZIP field is none.
            if m.group(1)[:2] in ("27", "28"):
                z = m
    city = ""
    m = re.match(r"\s*([A-Za-z .'-]+?),\s*(?:NC|North Carolina)\b", tail)
    if m:
        city = m.group(1).strip()
    # "805 SW Service Road" / "US Hwy 1, NC 28387": the second line is a street continuation, not a town.
    if city and re.search(r"\b(hwy|highway|us|rd|road|st|street|ave|blvd|suite|ste)\b", city, re.I):
        street = "%s, %s" % (street, city)
        city = ""
    return street, city, z.group(1) if z else ""


def build():
    stats = BI.Stats()
    prow, page = BI.fetch(LODGING_PAGE, stats, timeout=60)
    info, conf = _page_config(page.decode("utf-8", "replace"))
    qrow, doc = _query(info, conf, stats)
    listings = []
    for d in doc.get("hits", []):
        street, city, z = _address(d.get("address"))
        cats = sorted(d.get("partnerCategories") or [])
        lodging = sorted(c for c in cats if c.startswith("Lodging"))
        geo = d.get("_geoloc") or {}
        listings.append(OrderedDict([
            ("listing_url", SITE + (d.get("uri") or "")), ("object_id", d.get("objectID")),
            ("status", qrow["status"]), ("document_sha256", qrow["sha256"]), ("document_bytes", qrow["bytes"]),
            ("fetched_at", qrow["fetched_at"]),
            ("bureau_category", "Lodging" if lodging else (cats[0] if cats else "")),
            ("bureau_subcategory", next((c.split("»", 1)[1].strip() for c in lodging if "»" in c), "")),
            ("bureau_all_subcategories", sorted({c.split("»", 1)[1].strip() for c in cats if "»" in c})),
            ("bureau_all_categories", cats),
            ("name", html.unescape(d.get("title") or "").strip()),
            ("address_lines", d.get("address") or []),
            ("street", street), ("city", city), ("region", "NC"),
            ("stated_postal_code", z),
            ("stated_phone", (d.get("phone") or "").strip()),
            ("lat", geo.get("lat")), ("lng", geo.get("lng")),
            ("website", (d.get("website") or "").split("?")[0].strip()),
        ]))
    listings.sort(key=lambda r: (r["name"].lower(), str(r["object_id"])))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "4B -- the official Pinehurst, Southern Pines, Aberdeen Area CVB lodging roster"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "https://homeofgolf.com/lodging/ -- the page's own partner-listing index and filter "
                   "(Pinehurst, Southern Pines, Aberdeen Area Convention & Visitors Bureau)"),
        ("lodging_page", OrderedDict([("url", LODGING_PAGE), ("status", prow["status"]),
                                      ("sha256", prow["sha256"]), ("bytes", prow["bytes"]),
                                      ("fetched_at", prow["fetched_at"])])),
        ("page_declared_index", info.get("index")),
        ("page_declared_filter", conf.get("filters")),
        ("service_calls", [qrow]),
        ("coverage", "EVERY_LODGING_CATEGORY_THE_BUREAU_PAGE_FILTERS"),
        ("index_hit_count", doc.get("nbHits")),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing the bureau publishes about pets is read; the roster is identity evidence only."),
        ("listing_count", len(listings)),
        ("lodging_by_subcategory", OrderedDict(sorted(Counter(
            s for l in listings for s in (l["bureau_all_subcategories"] or [""])).items()))),
        ("listings", listings),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", doc["listing_count"], "index hits:", doc["index_hit_count"], dict(doc["lodging_by_subcategory"]))
    print("requests:", doc["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
