"""PTF-GREENVILLE-NC-PARALLEL-SOURCE-READY-001 -- Phase 4B: the official county
tourism roster.

WHAT THIS IS
------------
The Greenville-Pitt County Convention and Visitors Bureau (``visitgreenvillenc.com``)
publishes one listing page per member business, and every listing page carries a
LocalBusiness JSON-LD block with the name, street, locality, postal code and phone
the business gave the bureau. Its "Hotels & Motels" category renders client-side,
so this lane reads the bureau's own ``sitemap.xml`` (one plain HTTPS GET), keeps
the listing URLs whose slug names a lodging word, reads each of those listing
pages (one plain GET each) and admits a listing to the roster only when the page
itself carries the bureau's hotel facility block ("Total Number of Hotel Rooms").
A slug that names a lodging word but whose page carries no facility block (a
country club, a restaurant called "Japan Inn") is recorded as refused, with why.
Every document is persisted by its own sha256.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are carried as
``stated_postal_code`` and never key a building on their own; its phone as
``stated_phone``. Nothing the bureau says about pets is read as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/greenville_nc_destination_roster_001.json
  data/acquisition/greenville_nc_independent_001/<sha256>.bin
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

from scripts.pettripfinder import greenville_nc_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-GREENVILLE-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "greenville-nc"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "greenville_nc_destination_roster_001.json")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "greenville_nc_independent_001")
SITEMAP = "https://www.visitgreenvillenc.com/sitemap.xml"
#: A listing slug that names a lodging word or a lodging brand. Deliberately wide:
#: the page's own facility block, not the slug, admits a listing to the roster.
_LODGING_SLUG = re.compile(
    r"/listing/[^/]*(inn|hotel|motel|suite|lodge|stay|marriott|hilton|hampton|holiday|residence"
    r"|homewood|courtyard|fairfield|econo|knights|super-8|microtel|days|quality|comfort|red-roof"
    r"|intown|best-western|camelot|country-inn|bed|candlewood|staybridge|baymont|home2|sleep"
    r"|wingate|la-quinta|extended)[^/]*/\d+/$", re.I)
_LODGING_MARKER = re.compile(r"Total Number of Hotel Rooms", re.I)


def _text(body):
    t = body.decode("utf-8", "replace")
    return t, re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ",
                                                      re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t))))


def _local_business(t):
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', t, re.S):
        try:
            j = json.loads(m.group(1))
        except Exception:
            continue
        for x in (j if isinstance(j, list) else j.get("@graph", [j])):
            if isinstance(x, dict) and isinstance(x.get("address"), dict):
                return x
    return None


def build():
    stats = BI.Stats()
    row, body = BI.fetch(SITEMAP, stats)
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body.decode("utf-8", "replace"))
    candidates = sorted({u for u in locs if _LODGING_SLUG.search(u)})
    listings, refused = [], []
    for url in candidates:
        r, b = BI.fetch(url, stats)
        t, txt = _text(b)
        lb = _local_business(t)
        if not lb or not _LODGING_MARKER.search(txt):
            refused.append(OrderedDict([("listing_url", url), ("status", r["status"]),
                                        ("document_sha256", r["sha256"]),
                                        ("why", "the listing page carries no hotel facility block"
                                                if lb else "the listing page carries no LocalBusiness address")]))
            continue
        a = lb.get("address") or {}
        web = re.search(r'href="(https?://(?!www\.visitgreenvillenc\.com)[^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*(?:Visit\s+)?Website',
                        t, re.I)
        listings.append(OrderedDict([
            ("listing_url", url), ("status", r["status"]),
            ("document_sha256", r["sha256"]), ("document_bytes", r["bytes"]),
            ("fetched_at", r["fetched_at"]),
            ("name", html.unescape(lb.get("name") or "").strip()),
            ("street", (a.get("streetAddress") or "").strip()),
            ("city", (a.get("addressLocality") or "").strip()),
            ("stated_postal_code", (a.get("postalCode") or "").strip()[:5]),
            ("stated_phone", (lb.get("telephone") or "").strip()),
            ("website", html.unescape(web.group(1)).split("?")[0] if web else ""),
        ]))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "4B -- the official Greenville-Pitt County CVB lodging roster"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "https://www.visitgreenvillenc.com/sitemap.xml and each lodging listing page it names "
                   "(Greenville-Pitt County Convention and Visitors Bureau)"),
        ("sitemap", OrderedDict([("status", row["status"]), ("document_sha256", row["sha256"]),
                                 ("locs", len(locs)), ("lodging_slug_candidates", len(candidates))])),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing the bureau publishes about pets is read; the roster is identity evidence only."),
        ("listing_count", len(listings)),
        ("listings", listings),
        ("refused_candidates", refused),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for r in doc["listings"]:
        print(r["name"], "|", r["street"], "|", r["city"], r["stated_postal_code"], "|", r["website"][:70])
    print("refused:", [r["listing_url"].split("/listing/")[1] for r in doc["refused_candidates"]])
    print("listings:", doc["listing_count"], "requests:", doc["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
