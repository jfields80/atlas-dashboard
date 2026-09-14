"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- Phase 5F: the Pooler official lodging roster.

WHAT THIS IS
------------
Visit Pooler (``visitpooler.com``, the City of Pooler's official visitor site)
publishes its hotel roster under ``/stay/`` (WordPress), one page per property
stating the name, phone and address the bureau holds and a "Visit Website" link.
The airport-side Pooler cluster is under-represented in Visit Savannah's member
roster, so this second destination lane reads EVERY ``/stay/`` listing (the index
and its ``/stay/page/N/`` pages) from a plain HTTPS client. Each document is
persisted as returned, addressed by sha256.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
Its postal codes are carried as ``stated_postal_code`` and never key a building
on their own; its phone as ``stated_phone``. Nothing it says about pets or
amenities is read.

Output:
  launch_packages/pettripfinder/markets/reports/savannah_ga_pooler_roster_001.json
  data/acquisition/savannah_ga_pooler_roster_001/<sha256>.bin
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

from scripts.pettripfinder import savannah_ga_brand_inventory_001 as BI  # noqa: E402
from scripts.pettripfinder.savannah_ga_destination_roster_001 import split_address  # noqa: E402

WORK_ORDER = "PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "savannah-ga"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports", "savannah_ga_pooler_roster_001.json")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "savannah_ga_pooler_roster_001")
SITE = "https://www.visitpooler.com"
_LISTING = re.compile(r'href="(?:https://www\.visitpooler\.com)?(/stay/(?!page/|feed/)[a-z0-9-]+/)"')
_SOCIAL = re.compile(r"gmpg\.org|x\.com|twitter\.com|instagram\.com|facebook\.com|youtube\.com|google\.com/maps|maps\.app")


def _lines(body):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S | re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    return [x.strip() for x in t.split("\n") if x.strip()]


def build():
    stats = BI.Stats()
    index_rows, slugs = [], []
    for page in range(1, 15):
        url = SITE + ("/stay/" if page == 1 else "/stay/page/%d/" % page)
        row, body = BI.fetch(url, stats)
        text = body.decode("utf-8", "replace")
        found = [s for s in dict.fromkeys(_LISTING.findall(text)) if s not in slugs]
        index_rows.append(OrderedDict([("url", url), ("status", row["status"]), ("sha256", row["sha256"]),
                                       ("new_listings", len(found))]))
        if row["status"] != 200 or not found:
            break
        slugs.extend(found)
    listings = []
    for slug in slugs:
        url = SITE + slug
        row, body = BI.fetch(url, stats)
        text = body.decode("utf-8", "replace")
        lines = _lines(text)
        k = next((i for i, x in enumerate(lines) if re.search(r",\s*(GA|SC)\s+\d{5}\s*$", x)), None)
        name = phone = addr = ""
        if k is not None and k >= 2:
            addr, phone, name = lines[k], lines[k - 1], lines[k - 2]
            if not re.search(r"\d{3}[-.) ]\s*\d{3}-\d{4}", phone):
                name, phone = phone, ""
        street, city, state, z = split_address(addr)
        webs = [u for u in re.findall(r'href="(https?://(?!www\.visitpooler)[^"]+)"', text) if not _SOCIAL.search(u)]
        listings.append(OrderedDict([
            ("listing_url", url), ("recid", slug.strip("/").split("/")[-1]), ("status", row["status"]),
            ("document_sha256", row["sha256"]), ("document_bytes", row["bytes"]), ("fetched_at", row["fetched_at"]),
            ("bureau_category", "Stay"), ("bureau_subcategory", "Hotels"), ("bureau_all_subcategories", ["Hotels"]),
            ("bureau_region", "Pooler"), ("name", name), ("street", street), ("city", city), ("region", state),
            ("stated_postal_code", z), ("stated_phone", phone), ("lat", None), ("lng", None),
            ("website", (webs[0] if webs else "").split("?")[0]),
        ]))
        time.sleep(0.5)
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "5F -- the official Visit Pooler lodging roster"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "https://www.visitpooler.com/stay/ -- every listing on the index and its pages (City of Pooler)"),
        ("index_pages", index_rows), ("coverage", "EVERY_STAY_LISTING"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("listing_count", len(listings)),
        ("unreadable_listing_pages", [l["listing_url"] for l in listings if l["status"] != 200 or not l["name"]]),
        ("documents_persisted_at", os.path.relpath(BI.DOCS, _DASH).replace("\\", "/")),
        ("listings", listings),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", doc["listing_count"], "unreadable:", len(doc["unreadable_listing_pages"]))
    for l in doc["listings"]:
        print(" ", l["name"], "|", l["street"], l["stated_postal_code"], "|", l["website"][:60])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
