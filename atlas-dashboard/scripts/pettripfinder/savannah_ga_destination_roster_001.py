"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- Phase 5D/5E: the official destination lodging roster.

WHAT THIS IS
------------
Visit Savannah (``visitsavannah.com``, the Savannah Area Convention & Visitors
Bureau's official destination site) publishes its member lodging as Drupal
``/profile/<slug>/<id>`` pages under its own "Places to Stay" categories:
"Hotels & Motels", "Bed & Breakfasts", "Historic Inns", "Vacation Rentals" and
"Extended Stay". The site refuses a plain HTTPS client (403 on the home page,
robots.txt and sitemap), so the roster was read in the operator's attended
Chrome session (no bot check answered): every category listing page
(``?page=N``) for its profile links, then every profile page for the bureau's
own name, "Located in" area, address line, phone and "Visit Website" link. Each
profile page was hashed in the same browser call (``b`` / ``h``), and the whole
payload's canonical-JSON sha256 was computed in the page and checked equal to the
committed file before it was written (PAYLOAD_DIGEST).

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are carried as
``stated_postal_code`` and never key a building on their own; its phone as
``stated_phone``. Nothing the bureau says about pets is read as a policy. Its
categories are recorded verbatim so the census can refuse vacation-rental,
property-management, campground and venue listings BY DECISION.

Output:
  launch_packages/pettripfinder/markets/reports/savannah_ga_destination_roster_001.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "savannah-ga"
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "savannah-ga",
                   "raw_captures", "cvb_profiles.json")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "savannah_ga_destination_roster_001.json")
SITE = "https://visitsavannah.com"
CAPTURED_AT = "2026-09-14"
#: The canonical-JSON sha256 the browser computed over the same payload.
PAYLOAD_DIGEST = "7d0f028e696d369e11fcf0d8a5d5b9069ad75d84852a1c06a4e2e2a157a8b188"
#: The bureau's own lodging categories, as its category pages are titled.
CATEGORY_PAGES = OrderedDict([
    ("/savannah-hotels-motels", "Hotels & Motels"), ("/bed-breakfasts", "Bed & Breakfasts"),
    ("/historic-inns", "Historic Inns"), ("/vacation-rentals", "Vacation Rentals"),
    ("/extended-stay", "Extended Stay"), ("/places-to-stay", "Places to Stay"),
])

_ADDR = re.compile(r"^(?P<street>.*?),\s*(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<zip>\d{5})\s*$")


def split_address(line):
    m = _ADDR.match((line or "").strip())
    if not m:
        return "", "", "", ""
    street = m.group("street").strip()
    # "Tybee Island, GA 31328" alone (no street) and a PO box are not a street.
    if re.match(r"(?i)^p\.?\s*o\.?\s*box\b", street):
        street = ""
    city = m.group("city").strip()
    if city.lower() in ("pt wentworth", "pt. wentworth"):
        city = "Port Wentworth"
    return street, city, m.group("state"), m.group("zip")


def build():
    rows = json.load(open(RAW, encoding="utf-8"))
    got = hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    if got != PAYLOAD_DIGEST:
        raise SystemExit("payload digest %s != the browser's %s" % (got, PAYLOAD_DIGEST))
    listings = []
    for r in rows:
        street, city, state, z = split_address(r.get("addr"))
        listings.append(OrderedDict([
            ("listing_url", SITE + r["u"]), ("recid", int(r["u"].rstrip("/").rsplit("/", 1)[-1])),
            ("status", r["s"]), ("document_sha256", r.get("h")), ("document_bytes", r.get("b")),
            ("fetched_at", CAPTURED_AT),
            ("bureau_category", "Places to Stay"),
            ("bureau_subcategory", next((c for c in r.get("cats") or [] if c != "Places to Stay"), "Places to Stay")),
            ("bureau_all_subcategories", sorted(set(r.get("cats") or []))),
            ("bureau_region", r.get("area") or ""),
            ("name", (r.get("n") or "").strip()),
            ("street", street), ("city", city), ("region", state),
            ("stated_postal_code", z), ("stated_phone", (r.get("ph") or "").strip()),
            ("lat", None), ("lng", None),
            ("website", (r.get("web") or "").strip()),
        ]))
    listings.sort(key=lambda r: (r["name"].lower(), r["recid"]))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "5D/5E -- the official Visit Savannah (Savannah Area CVB) lodging roster"),
        ("as_of", CAPTURED_AT),
        ("source", "https://visitsavannah.com -- every 'Places to Stay' category listing page and every profile it "
                   "links, read in the operator's attended Chrome session (the site refuses a plain client: 403)"),
        ("category_pages", CATEGORY_PAGES),
        ("payload_digest", PAYLOAD_DIGEST),
        ("committed_payload", os.path.relpath(RAW, _DASH).replace("\\", "/")),
        ("coverage", "EVERY_PLACES_TO_STAY_CATEGORY_PAGE_AND_EVERY_LINKED_PROFILE"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing the bureau publishes about pets is read; the roster is identity evidence only."),
        ("listing_count", len(listings)),
        ("lodging_by_subcategory", OrderedDict(sorted(Counter(l["bureau_subcategory"] for l in listings).items()))),
        ("listings_by_bureau_area", OrderedDict(sorted(Counter(l["bureau_region"] for l in listings).items()))),
        ("unreadable_listing_pages", [l["listing_url"] for l in listings if l["status"] != 200]),
        ("listings", listings),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", doc["listing_count"], dict(doc["lodging_by_subcategory"]))
    print("areas:", dict(doc["listings_by_bureau_area"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
