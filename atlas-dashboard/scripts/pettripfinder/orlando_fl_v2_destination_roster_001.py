"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 9D: the destination-organisation roster (Visit Orlando).

Visit Orlando (the official destination marketing organisation for Orlando and Orange County) publishes its
"Places to Stay" member listings through its own Simpleview listing service. Every listing names the property,
its street, city and ZIP as the bureau records them, a phone, a website link and the bureau's own lodging
sub-category. This helper reads that roster with a plain client, one page of 100 listings at a time, through the
same public token the bureau's own page requests.

WHAT A ROSTER ROW IS
--------------------
Tier-2 discovery and identity evidence. A bureau ZIP can be the mailing ZIP; a bureau phone can be a central
reservations line; a bureau website can be a brand home page. None of them keys a building on its own and none
admits one. The roster's own sub-category ("Vacation Homes", "Timeshare", "Hotels & Resorts") is recorded because
the census's vacation-rental rule reads it. The "pet friendly" amenity word a bureau listing may carry is NEVER a
policy and is not read here at all.

Output:
  launch_packages/pettripfinder/markets/reports/orlando_fl_v2_destination_roster_001.json
  data/acquisition/orlando_fl_v2_roster_001/<sha256>.bin
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import direct_http_capture as DHC  # noqa: E402

WORK_ORDER = "PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "orlando-fl"
BASE = "https://www.visitorlando.com"
DOCS = os.path.join(_DASH, "data", "acquisition", "orlando_fl_v2_roster_001")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "orlando_fl_v2_destination_roster_001.json")
FIELDS = {"title": 1, "address1": 1, "address2": 1, "city": 1, "state": 1, "zip": 1, "weburl": 1, "phone": 1,
          "categories": 1, "latitude": 1, "longitude": 1, "recid": 1, "url": 1, "region": 1}
#: The bureau's lodging parent category on this site ("Hotels", catid 167) and any other parent category whose
#: listings the aggregate call reports as lodging.
LODGING_CATIDS = (167,)


def persist(body):
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    p = os.path.join(DOCS, digest + ".bin")
    if not os.path.exists(p):
        open(p, "wb").write(body)
    return digest


def token():
    f = DHC.fetch(BASE + "/plugins/core/get_simple_token/")
    return (f.body or b"").decode().strip()


def page(tok, catid, skip, limit=100):
    q = {"filter": {"filter_tags": {"$in": ["site_primary_catid_%d" % catid]}},
         "options": {"limit": limit, "skip": skip, "count": True, "sort": {"recid": 1}, "fields": FIELDS}}
    url = "%s/includes/rest_v2/plugins_listings_listings/find/?json=%s&token=%s" % (
        BASE, urllib.parse.quote(json.dumps(q, sort_keys=True)), tok)
    f = DHC.fetch(url, timeout=60)
    body = f.body or b""
    return f.status, body, url.split("&token=")[0]


def build():
    tok = token()
    listings, documents = [], []
    for catid in LODGING_CATIDS:
        skip, total = 0, None
        while total is None or skip < total:
            status, body, url = page(tok, catid, skip)
            doc = json.loads(body.decode("utf-8")) if status == 200 else {}
            docs = (doc.get("docs") or {})
            total = docs.get("count", 0) if total is None else total
            rows = docs.get("docs") or []
            documents.append(OrderedDict([("url_without_token", url), ("status", status), ("bytes", len(body)),
                                          ("sha256", persist(body) if body else None), ("listings", len(rows))]))
            for r in rows:
                cats = r.get("categories") or []
                primary = next((c for c in cats if c.get("primary")), cats[0] if cats else {})
                listings.append(OrderedDict([
                    ("recid", r.get("recid")), ("name", (r.get("title") or "").strip()),
                    ("street", " ".join(x for x in ((r.get("address1") or "").strip(), (r.get("address2") or "").strip()) if x)),
                    ("city", (r.get("city") or "").strip()), ("region", (r.get("state") or "FL").strip()),
                    ("stated_postal_code", (r.get("zip") or "").strip()[:5]),
                    ("stated_phone", (r.get("phone") or "").strip()),
                    ("website", (r.get("weburl") or "").strip()),
                    ("bureau_subcategory", primary.get("subcatname")),
                    ("bureau_all_subcategories", sorted({c.get("subcatname") for c in cats if c.get("subcatname")})),
                    ("lat", r.get("latitude")), ("lng", r.get("longitude")),
                    ("listing_url", BASE + (r.get("url") or "")),
                    ("document_sha256", documents[-1]["sha256"]),
                ]))
            if not rows:
                break
            skip += len(rows)
            time.sleep(0.8)
    listings.sort(key=lambda x: x["recid"] or 0)
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9D -- Visit Orlando Places to Stay roster (tier 2 discovery and identity evidence)"),
        ("source", "https://www.visitorlando.com/places-to-stay/ (the bureau's own Simpleview listing service)"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", len(documents) + 1),
        ("a_roster_row_is_not_a_policy",
         "Discovery and identity evidence only. The bureau's amenity words are never read as a pet policy."),
        ("documents", documents), ("listing_count", len(listings)),
        ("by_subcategory", OrderedDict(sorted(Counter(l["bureau_subcategory"] or "" for l in listings).items()))),
        ("listings", listings),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", rep["listing_count"], dict(rep["by_subcategory"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
