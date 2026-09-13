"""PTF-JACKSONVILLE-NC-PARALLEL-SOURCE-READY-001 -- Phase 4B: the official county
tourism roster.

WHAT THIS IS
------------
Onslow County's official tourism site (``onlyinonslow.com``, the Jacksonville /
Onslow tourism organisation) publishes a two-page "Onslow County Hotels & Motels"
category, and each listing states a name, a postal address line, a phone and the
website the operator gave the county. One plain HTTPS GET per page; every
document persisted by its own sha256.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are demonstrably loose -- it
prints 28546 for Marine Boulevard buildings whose own pages state 28540, and 28539
for a North Topsail Beach motel -- so the census never keys a building on the
roster's ZIP: the stated ZIP is kept as ``stated_postal_code`` and the row joins
on street and house number instead. Its "Pet Friendly" amenity word is recorded
and NEVER read as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/jacksonville_nc_destination_roster_001.json
  data/acquisition/jacksonville_nc_independent_001/<sha256>.bin
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import jacksonville_nc_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "jacksonville-nc"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "jacksonville_nc_destination_roster_001.json")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "jacksonville_nc_independent_001")
CATEGORY_PAGES = ("https://www.onlyinonslow.com/category/hotels-motels/",
                  "https://www.onlyinonslow.com/category/hotels-motels/page/2/")
#: Site-navigation pages the category template links to; not listings.
_NOT_LISTING = re.compile(
    r"/(about-us|african|beach|birding|boating|category|community|contact|download|event|getting|"
    r"hammocks|historic|history|lejeune-memorial|media|meetings|military|motor-coach|onslow|"
    r"paddling|privacy|things|tourism|trails|where-to-stay)")
_ADDRESS = re.compile(r"([0-9][^:]{3,80}?),\s*([A-Za-z .]+),\s*NC\s*(\d{5})\s*PHONE:\s*(\(?\d{3}\)?[\d -]{7,9})")


def _text(body):
    t = body.decode("utf-8", "replace")
    return t, re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ",
                                                      re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t))))


def build():
    stats = BI.Stats()
    pages, slugs = [], []
    for url in CATEGORY_PAGES:
        row, body = BI.fetch(url, stats)
        t, _txt = _text(body)
        main = t.split("Onslow County Hotels", 1)[-1]
        found = [u for u in re.findall(r'href="(https://www\.onlyinonslow\.com/[a-z0-9-]+/)"', main)
                 if not _NOT_LISTING.search(u)]
        row["listing_links"] = len(found)
        pages.append(row)
        for u in found:
            if u not in slugs:
                slugs.append(u)
    listings = []
    for url in slugs:
        row, body = BI.fetch(url, stats)
        t, txt = _text(body)
        m = _ADDRESS.search(txt)
        if not m:
            continue
        web = re.search(r'href="([^"]+)"[^>]*>\s*WEBSITE', t)
        name = html.unescape((re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1]).split("|")[0].strip()
        website = html.unescape(web.group(1)).split("?")[0] if web else ""
        listings.append(OrderedDict([
            ("listing_url", url), ("status", row["status"]),
            ("document_sha256", row["sha256"]), ("document_bytes", row["bytes"]),
            ("fetched_at", row["fetched_at"]),
            ("name", name), ("street", m.group(1).strip()), ("city", m.group(2).strip()),
            ("stated_postal_code", m.group(3)), ("stated_phone", m.group(4).strip()),
            ("website", website),
            ("amenity_word_pet_friendly", "Pet Friendly" in txt),
        ]))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "4B -- the official Onslow County tourism hotel roster"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "https://www.onlyinonslow.com/category/hotels-motels/ (Onslow County tourism, two pages)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("postal_codes_are_loose",
         "The roster prints 28546 for Marine Boulevard buildings whose own pages state 28540 and 28539 for a "
         "North Topsail Beach motel. The census keeps the roster ZIP as stated_postal_code and never keys on it."),
        ("an_amenity_word_is_not_a_policy",
         "amenity_word_pet_friendly records the roster's own amenity list and is never read as a pet policy."),
        ("category_pages", pages),
        ("listing_count", len(listings)),
        ("listings", listings),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for r in doc["listings"]:
        print(r["name"], "|", r["street"], "|", r["city"], r["stated_postal_code"], "|", r["website"][:70])
    print("listings:", doc["listing_count"], "requests:", doc["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
