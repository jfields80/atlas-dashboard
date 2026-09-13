"""PTF-OUTER-BANKS-NC-PARALLEL-SOURCE-READY-001 -- Phase 4B: the official destination
lodging roster (cloned from the Greenville NC destination-roster helper).

WHAT THIS IS
------------
The Outer Banks Visitors Bureau (``outerbanks.org``, Dare County's official
destination organisation) publishes one listing page per member business. Every
listing page carries a Hotel / LodgingBusiness JSON-LD block (name, street,
locality, postal code, phone, pin) and the bureau's own CRM record for the
listing, whose ``primaryCategory`` states the bureau's category ("Lodging") and
sub-category ("Hotels & Motels", "Bed & Breakfasts", "Condos/Townhouses",
"Vacation Rentals", "Campgrounds", ...).

This lane reads the bureau's own ``sitemap.xml`` (one plain HTTPS GET), then
EVERY ``/listing/`` page the sitemap names -- not a slug-filtered subset, because
an Outer Banks hotel slug need not contain a lodging word -- one plain GET each,
sequentially, honouring the site's ``robots.txt`` ``Crawl-delay: 2``. A listing
enters the roster when its CRM ``catname`` is "Lodging"; its sub-category is
recorded verbatim so the census can refuse vacation-rental, condo, realty and
campground listings BY DECISION. Every document is persisted by its own sha256.

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are carried as
``stated_postal_code`` and never key a building on their own; its phone as
``stated_phone``. Nothing the bureau says about pets is read as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/outer_banks_nc_destination_roster_001.json
  data/acquisition/outer_banks_nc_destination_001/<sha256>.bin
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import outer_banks_nc_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-OUTER-BANKS-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "outer-banks-nc"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "outer_banks_nc_destination_roster_001.json")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "outer_banks_nc_destination_001")
SITEMAP = "https://www.outerbanks.org/sitemap.xml"
CRAWL_DELAY_SECONDS = 2.0


def _local_business(t):
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', t, re.S):
        try:
            j = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        for x in (j if isinstance(j, list) else j.get("@graph", [j])):
            if isinstance(x, dict) and isinstance(x.get("address"), dict):
                return x
    return None


def _crm(t):
    """The bureau's own CRM record fields for the listing (``var data = {...}``)."""
    i = t.find("var data = {")
    if i < 0:
        return {}
    seg = t[i + 11:i + 60000]
    out = {}
    m = re.search(r'"primaryCategory":(\{[^{}]*\})', seg)
    if m:
        try:
            out["primary_category"] = json.loads(m.group(1))
        except ValueError:
            pass
    for key in ("weburl", "city", "address1", "phone", "zip", "state"):
        m = re.search(r'"%s":"((?:[^"\\]|\\.)*)"' % key, seg)
        if m:
            out[key] = json.loads('"%s"' % m.group(1))
    return out


#: A listing slug that names a lodging word. ORDER ONLY: these pages are read first so the
#: census can start early; every other /listing/ page is still read afterwards.
_LODGING_FIRST = re.compile(
    r"inn|hotel|motel|suite|lodge|resort|marriott|hilton|hampton|holiday|comfort|quality|days|"
    r"best-western|ramada|travelodge|towneplace|sanderling|shutters|tranquil|surf-side|colony|oasis|"
    r"sea-ranch|motor|cottage|b-b|bed|breakfast|guest|villa|court|condo|rental|realty|camp|rv|"
    r"stay|oceanfront|beach|house|club|harbor|marina|island|sound", re.I)
URL_INDEX = os.path.join(BI.DOCS, "_url_index.json")


def _listing_url_of(text):
    lb = _local_business(text) or {}
    u = lb.get("url") or ""
    if not u:
        m = re.search(r'<meta property="og:url" content="([^"]+)"', text)
        u = m.group(1) if m else ""
    return u if "/listing/" in u else ""


def url_index():
    """``listing url -> persisted document`` for every page already on disk.

    A listing page states its own canonical URL in its JSON-LD, so a document persisted by
    an interrupted run is re-used by what it SAYS it is, never re-requested.
    """
    idx = {}
    if os.path.exists(URL_INDEX):
        with open(URL_INDEX, encoding="utf-8") as fh:
            idx = json.load(fh)
    known = {v["sha256"] for v in idx.values()}
    for name in sorted(os.listdir(BI.DOCS)) if os.path.isdir(BI.DOCS) else ():
        if not name.endswith(".bin") or name[:-4] in known:
            continue
        with open(os.path.join(BI.DOCS, name), "rb") as fh:
            body = fh.read()
        u = _listing_url_of(body.decode("utf-8", "replace"))
        if u:
            idx.setdefault(u, {"status": 200, "sha256": name[:-4], "bytes": len(body),
                               "fetched_at": None, "error": None, "reused_from_disk": True})
    return idx


def _save_index(idx):
    with open(URL_INDEX, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(idx, fh, indent=0, sort_keys=True)


def build(priority_only=False):
    stats = BI.Stats()
    row, body = BI.fetch(SITEMAP, stats)
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body.decode("utf-8", "replace"))
    candidates = sorted({u for u in locs if "/listing/" in u})
    order = sorted(candidates, key=lambda u: (0 if _LODGING_FIRST.search(u.split("/listing/")[1]) else 1, u))
    idx = url_index()
    listings, other = [], Counter()
    unreadable = []
    if priority_only:
        order = [u for u in order if _LODGING_FIRST.search(u.split("/listing/")[1])]
    for n, url in enumerate(order):
        hit = idx.get(url)
        if hit and hit.get("sha256"):
            with open(os.path.join(BI.DOCS, hit["sha256"] + ".bin"), "rb") as fh:
                b = fh.read()
            r = OrderedDict([("status", hit["status"]), ("sha256", hit["sha256"]), ("bytes", hit["bytes"]),
                             ("fetched_at", hit.get("fetched_at")), ("error", None)])
        else:
            time.sleep(CRAWL_DELAY_SECONDS)
            r, b = BI.fetch(url, stats, timeout=40)
            idx[url] = {"status": r["status"], "sha256": r["sha256"], "bytes": r["bytes"],
                        "fetched_at": r["fetched_at"], "error": r["error"]}
            if n % 20 == 0:
                _save_index(idx)
        t = b.decode("utf-8", "replace")
        crm = _crm(t)
        cat = (crm.get("primary_category") or {})
        if r["status"] != 200 or not cat:
            unreadable.append(OrderedDict([("listing_url", url), ("status", r["status"]),
                                           ("error", r["error"]), ("document_sha256", r["sha256"])]))
            continue
        if cat.get("catname") != "Lodging":
            other[cat.get("catname") or ""] += 1
            continue
        lb = _local_business(t) or {}
        a = lb.get("address") or {}
        geo = lb.get("geo") or {}
        listings.append(OrderedDict([
            ("listing_url", url), ("status", r["status"]),
            ("document_sha256", r["sha256"]), ("document_bytes", r["bytes"]),
            ("fetched_at", r["fetched_at"]),
            ("bureau_category", cat.get("catname")),
            ("bureau_subcategory", cat.get("subcatname")),
            ("jsonld_type", lb.get("@type")),
            ("name", html.unescape(lb.get("name") or "").strip()),
            ("street", (a.get("streetAddress") or crm.get("address1") or "").strip()),
            ("city", (a.get("addressLocality") or crm.get("city") or "").strip()),
            ("region", (a.get("addressRegion") or "").strip()),
            ("stated_postal_code", (a.get("postalCode") or "").strip()[:5]),
            ("stated_phone", (lb.get("telephone") or crm.get("phone") or "").strip()),
            ("lat", geo.get("latitude")), ("lng", geo.get("longitude")),
            ("website", (crm.get("weburl") or "").split("?")[0].strip()),
        ]))
    _save_index(idx)
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "4B -- the official Outer Banks Visitors Bureau lodging roster"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "https://www.outerbanks.org/sitemap.xml and every /listing/ page it names "
                   "(Outer Banks Visitors Bureau, Dare County's destination organisation)"),
        ("sitemap", OrderedDict([("status", row["status"]), ("document_sha256", row["sha256"]),
                                 ("locs", len(locs)), ("listing_pages", len(candidates))])),
        ("crawl_delay_seconds", CRAWL_DELAY_SECONDS),
        ("coverage", "PRIORITY_SLUGS_ONLY (interim)" if priority_only else "EVERY_LISTING_PAGE_IN_THE_SITEMAP"),
        ("listing_pages_read", len(order)),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing the bureau publishes about pets is read; the roster is identity evidence only."),
        ("listing_count", len(listings)),
        ("lodging_by_subcategory", OrderedDict(sorted(Counter(l["bureau_subcategory"] for l in listings).items()))),
        ("non_lodging_listing_pages_by_category", OrderedDict(sorted(other.items()))),
        ("unreadable_listing_pages", unreadable),
        ("listings", listings),
    ])


def main():
    doc = build(priority_only="--priority-only" in sys.argv)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", doc["listing_count"], dict(doc["lodging_by_subcategory"]))
    print("other:", dict(doc["non_lodging_listing_pages_by_category"]))
    print("unreadable:", len(doc["unreadable_listing_pages"]), "requests:", doc["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
