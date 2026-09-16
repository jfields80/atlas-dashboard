"""PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 12F: Extended Stay America, the plain-client lane.

Extended Stay America's own Tampa city page (https://www.extendedstayamerica.com/hotels/fl/tampa) answers a
plain HTTPS client and lists every nearby property route. Each property page answers too, and carries, in its
own Hotel JSON-LD, the property's address and telephone, and in its own FAQPage JSON-LD the property-specific
answer to "Is <property> pet friendly?". That answer is the operative statement this lane reads. The brand's
fee schedule in the page's terms is a ceiling in the terms of use, not the property's stated fee, and is never
published as one. The ``petsAllowed`` JSON-LD boolean and the "Pet-friendly rooms" amenity feature are never
read as policy.

Routes: in-market towns only (the city page can also list nearby out-of-market Florida towns). Documents
persisted by sha256 under data/acquisition/tampa_fl_v2_esa_001/.

Also reads the St. Petersburg city page directly, since ESA operates properties across both sides of the bay
and a single Tampa city-page walk may not surface every Pinellas-side property.

Outputs:
  launch_packages/pettripfinder/markets/staging/tampa-fl/raw_captures/esa_rows.json
  launch_packages/pettripfinder/markets/reports/tampa_fl_v2_esa_lane_001.json
"""
from __future__ import annotations

import hashlib
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

from scripts.pettripfinder import tampa_fl_v2_brand_inventory_001 as B  # noqa: E402

WORK_ORDER = "PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001"
B.DOCS = os.path.join(_DASH, "data", "acquisition", "tampa_fl_v2_esa_001")
CITY_PAGES = [
    "https://www.extendedstayamerica.com/hotels/fl/tampa",
    "https://www.extendedstayamerica.com/hotels/fl/st-petersburg",
    "https://www.extendedstayamerica.com/hotels/fl/clearwater",
]
RAW_OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "tampa-fl", "raw_captures", "esa_rows.json")
REPORT_OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports", "tampa_fl_v2_esa_lane_001.json")
OUT_OF_MARKET_TOWNS = ("orlando", "kissimmee", "lakeland", "winter-haven", "sarasota", "bradenton",
                       "ocala", "gainesville", "daytona-beach", "melbourne")


def _jsonld_hotel(text):
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', text, re.S | re.I):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict) and node.get("@type") in ("Hotel", "LodgingBusiness") and node.get("address"):
                return node
    return None


def main():
    st = B.Stats()
    city_rows = []
    all_routes = set()
    for city_url in CITY_PAGES:
        row, body = B.fetch(city_url, st, timeout=40)
        city_rows.append(row)
        text = body.decode("utf-8", "replace")
        routes = {"https://www." + u for u in re.findall(r"extendedstayamerica\.com/hotels/fl/[a-z-]+/[a-z0-9-]+", text)}
        all_routes |= routes
    routes = sorted(u for u in all_routes if u.split("/hotels/fl/")[1].split("/")[0] not in OUT_OF_MARKET_TOWNS)
    rows = []
    for u in routes:
        time.sleep(1.0)
        prow, pbody = B.fetch(u, st, timeout=40)
        t = pbody.decode("utf-8", "replace")
        rec = OrderedDict([("u", u), ("s", prow["status"]), ("final_url", prow["final_url"]), ("h", prow["sha256"]), ("b", prow["bytes"])])
        hotel = _jsonld_hotel(t) or {}
        addr = hotel.get("address") or {}
        rec.update(OrderedDict([("n", hotel.get("name")), ("st", addr.get("streetAddress")), ("ci", addr.get("addressLocality")),
                                ("rg", addr.get("addressRegion")), ("z", (addr.get("postalCode") or "")[:5]),
                                ("ph", hotel.get("telephone"))]))
        m = re.search(r'"name":"(Is [^"]{3,120}? pet friendly\?)","acceptedAnswer":\{"@type":"Answer","text":"([^"]{1,400})"', t)
        rec["q"] = html.unescape(m.group(1)) if m else ""
        rec["p"] = html.unescape(m.group(2)) if m else ""
        cnt = re.search(r"A maximum of (two|one|three|\d) pets are allowed in each suite", t)
        rec["count_sentence"] = cnt.group(0) if cnt else ""
        rows.append(rec)
        print(u, rec["s"], rec["n"], rec["z"], rec["p"][:60], flush=True)
    os.makedirs(os.path.dirname(RAW_OUT), exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("city_pages", city_rows), ("rows", rows)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(REPORT_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([
            ("schema", "ptf-brand-first-party-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", "tampa-fl"),
            ("lane", "DIRECT_STATIC_FETCH (the brand's own city pages + property pages, plain client)"),
            ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", st.requests),
            ("city_pages_read", CITY_PAGES),
            ("routes_selected", len(routes)), ("pages_served", sum(1 for r in rows if r["s"] == 200)),
            ("with_faq_pet_answer", sum(1 for r in rows if r["p"])),
            ("never_read_as_policy", "the petsAllowed JSON-LD boolean, the 'Pet-friendly rooms' feature and the terms-of-use fee ceilings"),
            ("raw_captures", os.path.relpath(RAW_OUT, _DASH).replace("\\", "/")),
        ]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
