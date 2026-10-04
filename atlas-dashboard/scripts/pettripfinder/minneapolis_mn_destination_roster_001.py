"""PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001 -- Phase 9: the official destination-marketing rosters.

EVERY BUREAU WAS MEASURED, NOT ASSUMED
--------------------------------------
The standing rule is to MEASURE a convention and visitors bureau before spending anything on it (the San Diego
and Jacksonville finding: never assume Simpleview, never assume a category filter works). The Twin Cities bureaus
answered this plain client on 2026-10-04 like this:

  * MEET MINNEAPOLIS (minneapolis.org) -- Craft CMS, NOT Simpleview (``/plugins/core/get_simple_token/`` answers
    404). Its partner directory (``/directory/<slug>/``) is listed in its own sitemap and searched by its own pages
    through an Algolia index (application ``EYQHJ2IY2M``, index ``prod-meet-minneapolis-listings``) with the
    SEARCH-ONLY key the bureau embeds in every page's markup. This lane reads that index exactly as the bureau's own
    "Hotels" page does -- one read-only search query per page of results, nothing bypassed. Each Partner record
    carries the partner's OWN address lines, telephone and website, and the bureau's own categories
    (``partnerCategories``, ``partnerVenueTypes``, ``partnerGuestRooms``).
      THE BUREAU'S OWN JSON-LD IS A TRAP: every directory page's schema.org PostalAddress is the BUREAU'S office
      (801 Marquette Ave S, Suite 100, 55402), not the partner's. It is never read.
  * VISIT SAINT PAUL (visitsaintpaul.com) -- the same Craft platform. Its "Where to Stay" page server-renders its
    lodging partners' directory links; each directory page embeds a booking widget's accommodation record with the
    property's own street (``line_1``), city, pin and type ("Hotel"). It states NO postal code, and its only
    telephone fields are the bureau's reservation line and the property's toll-free number -- neither binds a
    building. A Visit Saint Paul row is therefore a STREET-WITHOUT-ZIP row: it joins the one building that states
    the same house number and street, or it stays an unplaced lead.
  * BLOOMINGTON CVB (bloomingtonmn.org) -- HTTP 403 to this client on the home page and every probe; recorded, not
    worked around. Bloomington's hotels reach the census through the brands, the map, Meet Minneapolis's "South
    Metro includes Airport/MOA too" region and the competitor gap challenge.
  * EXPLORE MINNESOTA (exploreminnesota.com) -- HTTP 403 to this client; recorded, not worked around.
  * visiteagan.com and visitwoodbury.com -- PARKED domains (a JavaScript redirect to "/lander"); not bureaus.
  * VISIT ROSEVILLE (visitroseville.com) -- answers 200 with a "/hotels/" page; its listing is measured below and
    read when it states a property's own street.

THE BUREAU'S CATEGORY IS READ, NOT TRUSTED
-----------------------------------------
Only lodging-typed partners are kept: a Meet Minneapolis Partner whose own categories include "Hotels/Lodging",
whose venue type is "Hotel" or which states guest rooms; a Visit Saint Paul listing the bureau itself places under
"Where to Stay". The census still decides what each row IS (a serviced-apartment operator such as Roami is refused
as VACATION_RENTAL there) and WHERE it is (its own postal code). The bureau's "Pets Allowed" amenity chip is NEVER
read, stored or published as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/minneapolis_mn_destination_roster_001.json
  data/acquisition/minneapolis_mn_destination_001/<sha256>.bin   (documents as returned)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import minneapolis_mn_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001"
MARKET_ID = "minneapolis-mn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "minneapolis_mn_destination_roster_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "minneapolis_mn_destination_001")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

MM_ALGOLIA_APP = "EYQHJ2IY2M"
#: The SEARCH-ONLY key Meet Minneapolis embeds in its own pages' markup (data-algolia config) -- read-only.
MM_ALGOLIA_KEY = "c6d5977cb5cd80c09abfd2a7e5d9e88b"
MM_INDEX = "prod-meet-minneapolis-listings"
MM_HOTELS_PAGE = "https://www.minneapolis.org/hotels/"
VSP_WHERE_TO_STAY = "https://www.visitsaintpaul.com/where-to-stay/"
ROSEVILLE_HOTELS = "https://visitroseville.com/hotels/"

#: Bureaus measured and NOT walked, with what answered.
BUREAUS_MEASURED_AND_NOT_WALKED = OrderedDict([
    ("bloomingtonmn.org", "HTTP 403 to this plain client (home page and /plugins/core/get_simple_token/); recorded, "
                          "not worked around"),
    ("exploreminnesota.com", "HTTP 403 to this plain client; recorded, not worked around"),
    ("visiteagan.com", "a parked domain (JavaScript redirect to /lander) -- not a bureau"),
    ("visitwoodbury.com", "a parked domain (JavaScript redirect to /lander) -- not a bureau"),
])

#: Meet Minneapolis partner typings that make a partner a LODGING row of the bureau.
MM_LODGING_CATEGORIES = {"Hotels/Lodging"}
MM_LODGING_VENUE_TYPES = {"Hotel"}
_TOLL_FREE = re.compile(r"^\(?8(00|33|44|55|66|77|88)\)?")
_STATE_NAMES = {"minnesota": "MN", "mn": "MN", "wisconsin": "WI", "wi": "WI"}


class Stats(object):
    def __init__(self):
        self.requests = 0
        self.bytes = 0


def persist(body):
    if not body:
        return None
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, digest + ".bin")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(body)
    return digest


def fetch(url, stats, headers=None, data=None, timeout=40):
    row = OrderedDict([("url", url), ("status", None), ("final_url", None), ("bytes", 0), ("sha256", None),
                       ("error", None)])
    h = {"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
         "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data)
    stats.requests += 1
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if (resp.headers.get("Content-Encoding") or "").lower() == "gzip" or body[:2] == b"\x1f\x8b":
                try:
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                except OSError:
                    pass
            row.update(status=resp.getcode(), final_url=resp.geturl(), bytes=len(body), sha256=persist(body))
            stats.bytes += len(body)
            return row, body
    except urllib.error.HTTPError as exc:
        row["status"], row["final_url"] = exc.code, url
        return row, b""
    except Exception as exc:  # network failure is recorded, never raised
        row["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])
        return row, b""


def _s(v):
    return " ".join(html.unescape(str(v or "")).split())


def split_city_line(line):
    """'Minneapolis, Minnesota 55404' -> ('Minneapolis', 'MN', '55404')."""
    m = re.match(r"^\s*(.*?),\s*([A-Za-z .]+?)\s+(\d{5})(?:-\d{4})?\s*$", line or "")
    if not m:
        return "", "", ""
    return _s(m.group(1)), _STATE_NAMES.get(m.group(2).strip().lower().rstrip("."), m.group(2).strip().upper()), \
        m.group(3)


def placed(row):
    klass, slug, why = GEO.classify_postal(row.get("postal_code"), row.get("city"))
    row["geography_class"], row["corridor_slug"], row["membership_reason"] = klass, slug, why
    return row


# --------------------------------------------------------------------------- Meet Minneapolis (Algolia index)
def meet_minneapolis(stats):
    bureau = OrderedDict([("bureau_id", "meet-minneapolis"), ("platform", "Craft CMS + Algolia partner index"),
                          ("index", MM_INDEX), ("documents", []), ("lodging_typed_partner_records_in_index", 0),
                          ("lodging_partners", 0)])
    rows, hits_all, seen_obj = OrderedDict(), [], set()
    # Two read-only queries (Algolia does not mix a numeric filter into a facet OR): the bureau's own lodging
    # typings, then any partner stating guest rooms. Records are unioned by objectID.
    for filt in ('sectionName:"Partners" AND (partnerCategories:"Hotels/Lodging" OR partnerVenueTypes:"Hotel")',
                 'sectionName:"Partners" AND partnerGuestRooms > 0'):
        page = 0
        while True:
            params = "query=&hitsPerPage=1000&page=%d&filters=%s" % (page, urllib.request.quote(filt))
            url = "https://%s-dsn.algolia.net/1/indexes/%s?%s" % (MM_ALGOLIA_APP, MM_INDEX, params)
            doc, body = fetch(url, stats, headers={"X-Algolia-API-Key": MM_ALGOLIA_KEY,
                                                   "X-Algolia-Application-Id": MM_ALGOLIA_APP,
                                                   "Referer": MM_HOTELS_PAGE,
                                                   "Origin": "https://www.minneapolis.org"})
            bureau["documents"].append(doc)
            if not body:
                break
            data = json.loads(body.decode("utf-8", "replace"))
            for h in data.get("hits") or []:
                if h.get("objectID") not in seen_obj:
                    seen_obj.add(h.get("objectID"))
                    hits_all.append(h)
            page += 1
            if page >= int(data.get("nbPages") or 0) or page > 10:
                break
    bureau["lodging_typed_partner_records_in_index"] = len(hits_all)
    for h in hits_all:
        cats = set(h.get("partnerCategories") or [])
        venues = set(h.get("partnerVenueTypes") or [])
        rooms = int(h.get("partnerGuestRooms") or 0)
        if not (cats & MM_LODGING_CATEGORIES or venues & MM_LODGING_VENUE_TYPES or rooms > 0):
            continue
        pid = _s(h.get("distinctField") or h.get("id"))
        addr = [a for a in (h.get("address") or []) if _s(a)]
        street = _s(addr[0]) if addr else ""
        city, state, postal = split_city_line(addr[-1]) if len(addr) >= 2 else ("", "", "")
        typing = sorted({"Partner / %s" % c for c in cats} | {"Venue / %s" % v for v in venues}
                        | ({"Partner / Guest Rooms"} if rooms > 0 else set()))
        if pid in rows:
            r = rows[pid]
            r["bureau_categories"] = sorted(set(r["bureau_categories"]) | set(typing))
            r["listing_urls"] = sorted(set(r["listing_urls"]) | {"https://www.minneapolis.org" + _s(h.get("uri"))})
            continue
        geo = h.get("_geoloc") or {}
        phone = _s(h.get("phone"))
        rows[pid] = OrderedDict([
            ("lane", "DESTINATION_ROSTER"), ("bureau_id", "meet-minneapolis"), ("partner_id", pid),
            ("name", _s(h.get("title"))), ("street", street), ("city", city), ("state", state),
            ("postal_code", postal), ("phone", "" if _TOLL_FREE.match(phone) else phone),
            ("official_url", _s(h.get("website"))), ("bureau_link_refused_as_a_route", ""), ("why_refused", ""),
            ("address_extras", [_s(a) for a in addr[1:-1]]),
            ("bureau_categories", typing), ("bureau_schema_types", []),
            ("census_eligible_category", True), ("bureau_subtype", "hotel"),
            ("guest_rooms", rooms), ("bureau_region", sorted(h.get("partnerRegions") or [])),
            ("listing_url", "https://www.minneapolis.org" + _s(h.get("uri"))),
            ("listing_urls", ["https://www.minneapolis.org" + _s(h.get("uri"))]),
            ("listing_sha256", bureau["documents"][-1]["sha256"] if bureau["documents"] else None),
            ("lat", geo.get("lat")), ("lng", geo.get("lng")),
        ])
    bureau["lodging_partners"] = len(rows)
    return bureau, [placed(r) for r in rows.values()]


# --------------------------------------------------------------------------- Visit Saint Paul (where-to-stay)
def _vsp_record(text):
    """The accommodation record a Visit Saint Paul directory page embeds (escaped JSON inside a script)."""
    t = text.replace('\\"', '"').replace("\\u002D", "-").replace("\\/", "/")
    name = ""
    m = re.search(r'<meta property="og:title" content="([^"]+)"', text)
    if m:
        name = _s(m.group(1))
    m = re.search(r'"addresses":\[\{"id":\d+,"line_1":"([^"]*)"(?:,"line_2":"([^"]*)")?,"city":"([^"]*)"'
                  r'(?:,"geolocation":\{"id":\d+,"latitude":"([-0-9.]+)","longitude":"([-0-9.]+)"\})?', t)
    street = city = lat = lng = ""
    if m:
        street, city, lat, lng = _s(m.group(1)), _s(m.group(3)), m.group(4) or "", m.group(5) or ""
    m = re.search(r'"telephones":\[\{"type":"main","number":"([^"]+)"\}', t)
    phone = _s(m.group(1)) if m else ""
    m = re.search(r'"type":\{"id":\d+,"name":"([^"]+)"', t)
    typ = _s(m.group(1)) if m else ""
    return name, street, city, lat, lng, phone, typ


def visit_saint_paul(stats):
    bureau = OrderedDict([("bureau_id", "visit-saint-paul"), ("platform", "Craft CMS + embedded booking widget"),
                          ("entry", VSP_WHERE_TO_STAY), ("documents", []), ("listing_links", 0)])
    doc, body = fetch(VSP_WHERE_TO_STAY, stats)
    bureau["documents"].append(doc)
    links = sorted(set(re.findall(r'href="(https://www\.visitsaintpaul\.com/directory/[a-z0-9-]+/)"',
                                  body.decode("utf-8", "replace"))))
    bureau["listing_links"] = len(links)
    rows = []
    for link in links:
        d, b = fetch(link, stats)
        tries = 1
        while d["status"] and d["status"] >= 500 and tries < 3:
            # the bureau's server answers 500 intermittently; a paced retry, never a workaround
            time.sleep(4.0)
            d, b = fetch(link, stats)
            tries += 1
        d["attempts"] = tries
        time.sleep(0.6)
        bureau["documents"].append(d)
        name, street, city, lat, lng, phone, typ = _vsp_record(b.decode("utf-8", "replace"))
        if not name:
            continue
        rows.append(OrderedDict([
            ("lane", "DESTINATION_ROSTER"), ("bureau_id", "visit-saint-paul"),
            ("partner_id", link.rstrip("/").rsplit("/", 1)[-1]), ("name", name), ("street", street),
            ("city", city), ("state", "MN" if street else ""), ("postal_code", ""),
            ("phone", "" if _TOLL_FREE.match(phone) else phone), ("official_url", ""),
            ("bureau_link_refused_as_a_route", ""), ("why_refused", ""), ("address_extras", []),
            ("bureau_categories", ["Where to Stay / %s" % (typ or "Lodging")]), ("bureau_schema_types", []),
            ("census_eligible_category", True), ("bureau_subtype", (typ or "lodging").lower()),
            ("listing_url", link), ("listing_sha256", d["sha256"]), ("lat", lat), ("lng", lng),
            ("no_postal_code_stated",
             "the bureau's record states a street and city but no postal code; the row joins only the one building "
             "that states the same house number and street"),
        ]))
    return bureau, [placed(r) for r in rows]


# --------------------------------------------------------------------------- Visit Roseville
def visit_roseville(stats):
    bureau = OrderedDict([("bureau_id", "visit-roseville"), ("entry", ROSEVILLE_HOTELS), ("documents", []),
                          ("rows_with_a_street", 0)])
    doc, body = fetch(ROSEVILLE_HOTELS, stats)
    bureau["documents"].append(doc)
    text = body.decode("utf-8", "replace")
    rows = []
    # The page's own schema.org ItemList of @type Hotel: each item states its OWN street, locality, postal code,
    # telephone and official route (sameAs). The bureau's own Organization address is a different block and is
    # never read.
    for blob in re.findall(r'(?s)<script type="application/ld\+json">(.*?)</script>', text):
        try:
            doc_ld = json.loads(blob, strict=False)  # the page's JSON-LD carries a raw control character
        except ValueError:
            continue
        if not isinstance(doc_ld, dict) or doc_ld.get("@type") != "ItemList":
            continue
        for item in doc_ld.get("itemListElement") or []:
            if not isinstance(item, dict) or item.get("@type") != "Hotel":
                continue
            ad = item.get("address") or {}
            name = _s(item.get("name"))
            same = [u for u in (item.get("sameAs") or []) if isinstance(u, str)]
            rows.append(OrderedDict([
                ("lane", "DESTINATION_ROSTER"), ("bureau_id", "visit-roseville"),
                ("partner_id", _s(item.get("url")).rstrip("/").rsplit("/", 1)[-1]), ("name", name),
                ("street", _s(ad.get("streetAddress"))), ("city", _s(ad.get("addressLocality"))),
                ("state", _STATE_NAMES.get(_s(ad.get("addressRegion")).lower(), _s(ad.get("addressRegion")))),
                ("postal_code", _s(ad.get("postalCode"))[:5]), ("phone", _s(item.get("telephone"))),
                ("official_url", same[0] if same else ""), ("bureau_link_refused_as_a_route", ""),
                ("why_refused", ""), ("address_extras", []),
                ("bureau_categories", ["Hotels / Hotels"]), ("bureau_schema_types", ["Hotel"]),
                ("census_eligible_category", True), ("bureau_subtype", "hotel"),
                ("listing_url", _s(item.get("url")) or ROSEVILLE_HOTELS), ("listing_sha256", doc["sha256"]),
                ("lat", ""), ("lng", ""),
            ]))
    bureau["rows_with_a_street"] = len(rows)
    return bureau, [placed(r) for r in rows]


def build():
    stats = Stats()
    bureaus, rows = OrderedDict(), []
    for fn in (meet_minneapolis, visit_saint_paul, visit_roseville):
        b, r = fn(stats)
        bureaus[b["bureau_id"]] = b
        rows.extend(r)
    admitted = [r for r in rows if r["corridor_slug"]]
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9 -- the official destination-marketing rosters (Meet Minneapolis, Visit Saint Paul, Visit "
                  "Roseville), measured first"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("bytes_read", stats.bytes),
        ("the_bureau_was_measured", "Every bureau was probed before it was read; the platform each one runs is "
                                    "recorded, never assumed."),
        ("the_category_filter_is_read_not_trusted", "Only lodging-typed partners are kept; the census decides what "
                                                    "each row is and where it is."),
        ("a_roster_row_is_not_a_policy", "No bureau amenity chip -- including Meet Minneapolis's 'Pets Allowed' -- is "
                                         "read, stored or published."),
        ("the_bureau_does_not_decide_membership", "The row's own postal code does. Meet Minneapolis's directory "
                                                  "JSON-LD address is the bureau's own office and is never read."),
        ("bureaus_measured_and_not_walked", BUREAUS_MEASURED_AND_NOT_WALKED),
        ("bureaus", bureaus),
        ("row_count", len(rows)),
        ("rows_in_admitted_postal_codes", len(admitted)),
        ("rows_refused_by_postal_code", sum(1 for r in rows if r["postal_code"] and not r["corridor_slug"])),
        ("rows_without_a_postal_code", sum(1 for r in rows if not r["postal_code"])),
        ("rows_with_an_official_website", sum(1 for r in rows if r["official_url"])),
        ("rows_with_a_phone", sum(1 for r in rows if r["phone"])),
        ("rows_with_a_full_premises", sum(1 for r in rows if r["street"] and r["postal_code"])),
        ("census_eligible_rows_in_admitted_codes", len(admitted)),
        ("by_corridor", dict(Counter(r["corridor_slug"] for r in admitted))),
        ("by_bureau", dict(Counter(r["bureau_id"] for r in rows))),
        ("rows", rows),
        ("documents_persisted_at", os.path.relpath(DOCS, _DASH).replace("\\", "/")),
        ("bureau_links_refused_as_a_route", []),
        ("bureau_links_refused_as_a_route_count", 0),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("rows=%d admitted=%d no_zip=%d by_bureau=%s requests=%d" % (
        rep["row_count"], rep["rows_in_admitted_postal_codes"], rep["rows_without_a_postal_code"],
        rep["by_bureau"], rep["free_http_requests"]))
    print("by corridor:", rep["by_corridor"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
