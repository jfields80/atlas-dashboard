"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phase 11: the official destination-marketing rosters.

EVERY BUREAU WAS MEASURED, NOT ASSUMED
--------------------------------------
The standing rule is to MEASURE a convention and visitors bureau before spending anything on it (the San Diego
and Jacksonville finding: never assume Simpleview, never assume a category filter works). The Salt Lake City / Park
City bureaus answered this plain client on 2026-10-07 like this:

  * VISIT SALT LAKE (visitsaltlake.com) -- **Simpleview**: its own ``/plugins/core/get_simple_token/`` issues a
    session token and its own public listings endpoint (``/includes/rest_v2/plugins_listings_listings/find/``)
    publishes 4,799 partner listings, each with street, city, state, ZIP, telephone, website, pin and the bureau's
    own category. MEASURED over the whole listing set: the bureau types lodging under TWO categories --
    "Accommodations" (catid 595: Hotels 145, Extended Stay 25, Resort Properties 24, Vacation Homes & Condos 16,
    Bed & Breakfasts 6, Campgrounds 3, Hostels & Universities 1) and "Lodging, Hotels & Resorts" (catid 680: Hotels
    66, Resort Lodging 5). Both are read, filtered with the lower-cased ``categories.catid`` field.
  * VISIT PARK CITY (visitparkcity.com, the Park City Chamber / Bureau) -- **Simpleview** as well: 1,357 listings.
    MEASURED: "Places to Stay" (catid 215: Hotels & Lodges 42, Condo & Vacation Home Rentals 26, Rent by Owner 5,
    Central Reservations & Booking Services 4, Camping & RV Resorts 2) and "Meetings" > "Meeting Hotels" (catid
    214). Both are read. Its "Property Management" (1253) and "Housing & Long-Term Rentals" (1240) categories are
    MEASURED, NOT READ: neither is public hotel lodging.
  * VISIT UTAH (visitutah.com, the state office of tourism) -- Craft CMS with no partner listings endpoint; it
    links to the regional bureaus. Recorded, not walked.

THE BUREAU'S CATEGORY IS READ, NOT TRUSTED
-----------------------------------------
Only lodging-typed partners are kept, and the census still decides what each row IS (a vacation-home, condo,
rent-by-owner, central-reservations, property-management or campground typing is refused there) and WHERE it is (its
own postal code, which also decides its MUNICIPALITY -- a Park City bureau listing in Heber City is OUTSIDE). The
bureaus' "Pet-Friendly" amenity chips, categories and "pet-friendly hotels" pages are NEVER read, stored or published
as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_destination_roster_001.json
  data/acquisition/salt_lake_city_ut_destination_001/<sha256>.bin   (documents as returned)
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
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import salt_lake_city_ut_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
MARKET_ID = "salt-lake-city-ut"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "salt_lake_city_ut_destination_roster_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "salt_lake_city_ut_destination_001")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: The Simpleview bureaus read, each with the category ids MEASURED on 2026-10-07 over its whole listing set.
SIMPLEVIEW_BUREAUS = [
    ("visit-salt-lake", "https://www.visitsaltlake.com", (595, 680),
     "Accommodations (595) and Lodging, Hotels & Resorts (680)"),
    ("visit-park-city", "https://www.visitparkcity.com", (215, 214),
     "Places to Stay (215) and Meetings > Meeting Hotels (214)"),
]

#: Bureaus measured and NOT walked, with what answered.
BUREAUS_MEASURED_AND_NOT_WALKED = OrderedDict([
    ("visitutah.com", "the Utah Office of Tourism; Craft CMS with no partner listings endpoint -- measured, not "
                      "walked"),
    ("visitparkcity.com Property Management (1253) / Housing & Long-Term Rentals (1240)",
     "measured; not public hotel lodging -- not read"),
])

LODGING_CATEGORY_WORDS = ("hotel", "motel", "inn", "resort", "lodging", "lodge", "bed and breakfast",
                          "bed & breakfast", "b&b", "accommodation", "stay", "suites", "campground",
                          "rv park", "vacation rental", "short term rental", "condo", "hostel")
NON_CENSUS_CATEGORY_WORDS = ("vacation rental", "short term rental", "condo", "campground", "rv park", "camping",
                             "house rental", "home rental", "cottage rental", "reservation service", "apartment",
                             "condominium", "vacation home", "rent by owner", "central reservations",
                             "booking services", "property management", "long-term rental", "universities")
_TOLL_FREE = re.compile(r"^\(?\+?1?\s*\(?8(00|33|44|55|66|77|88)\)?")
_STATE_NAMES = {"utah": "UT", "ut": "UT"}


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


def _state(v):
    v = _s(v)
    return _STATE_NAMES.get(v.lower().rstrip("."), v.upper()[:2] if v else "")


def split_city_line(line):
    """'Park City, Utah 84060' -> ('Park City', 'UT', '84060')."""
    m = re.match(r"^\s*(.*?),\s*([A-Za-z .]+?)\s+(\d{5})(?:-\d{4})?\s*$", line or "")
    if not m:
        return "", "", ""
    return _s(m.group(1)), _state(m.group(2)), m.group(3)


def _census_eligible(categories):
    for c in categories:
        cl = c.lower()
        if any(w in cl for w in NON_CENSUS_CATEGORY_WORDS):
            continue
        if any(w in cl for w in LODGING_CATEGORY_WORDS):
            return True
    return False


def placed(row):
    klass, slug, why = GEO.classify_postal(row.get("postal_code"), row.get("city"))
    row["geography_class"], row["corridor_slug"], row["membership_reason"] = klass, slug, why
    # the state and municipality guards, recorded on the roster row itself
    row["state_conflict"] = GEO.state_conflict(row.get("postal_code"), row.get("state"))
    row["municipality_conflict"] = GEO.municipality_conflict(row.get("postal_code"), row.get("city"))
    return row


def _row(bureau_id, partner_id, name, street, city, state, postal, phone, website, categories, listing_url,
         listing_sha, lat, lng, extras=()):
    return OrderedDict([
        ("lane", "DESTINATION_ROSTER"), ("bureau_id", bureau_id), ("partner_id", str(partner_id or "")),
        ("name", _s(name)), ("street", _s(street)), ("city", _s(city)), ("state", state),
        ("postal_code", (postal or "")[:5]), ("phone", "" if _TOLL_FREE.match(_s(phone)) else _s(phone)),
        ("official_url", _s(website)), ("bureau_link_refused_as_a_route", ""), ("why_refused", ""),
        ("address_extras", [x for x in extras if x]),
        ("bureau_categories", sorted(set(categories))), ("bureau_schema_types", []),
        ("census_eligible_category", _census_eligible(categories)),
        ("listing_url", listing_url), ("listing_sha256", listing_sha), ("lat", lat), ("lng", lng),
    ])


# --------------------------------------------------------------------------- Simpleview bureaus
SIMPLEVIEW_FIELDS = OrderedDict((k, 1) for k in (
    "recid", "title", "address1", "address2", "city", "state", "zip", "phone", "weburl", "categories",
    "latitude", "longitude", "detailURL", "typeName"))
SIMPLEVIEW_PAGE = 100


def simpleview_bureau(stats, bureau_id, host, catids, cat_note, cap=40):
    bureau = OrderedDict([("bureau_id", bureau_id), ("platform", "Simpleview listings endpoint, filtered to the "
                                                                 "bureau's own lodging categories: " + cat_note),
                          ("entry", None), ("documents", []), ("listings_published", 0), ("listings_read", 0),
                          ("categories_seen", OrderedDict()), ("lodging_partners", 0)])
    trow, tbody = fetch(host + "/plugins/core/get_simple_token/", stats)
    token = tbody.decode("utf-8", "replace").strip()
    bureau["entry"] = trow
    if trow.get("status") != 200 or not re.match(r"^[0-9a-f]{16,64}$", token):
        bureau["disposition"] = "SIMPLEVIEW_TOKEN_NOT_ISSUED__STATUS_%s" % trow.get("status")
        return bureau, []
    docs, skip, total, spent = [], 0, None, 0
    while spent < cap:
        q = json.dumps(OrderedDict([("filter", OrderedDict([("categories.catid", OrderedDict([
            ("$in", list(catids))]))])),
                                ("options", OrderedDict([
            ("limit", SIMPLEVIEW_PAGE), ("skip", skip), ("count", True), ("fields", SIMPLEVIEW_FIELDS),
            ("sort", OrderedDict([("recid", 1)]))]))]), separators=(",", ":"))
        url = host + "/includes/rest_v2/plugins_listings_listings/find/?" + urllib.parse.urlencode(
            [("json", q), ("token", token)])
        prow, pbody = fetch(url, stats, timeout=60)
        spent += 1
        prow["url"] = prow["url"].split("&token=")[0] + "&token=<session>"
        bureau["documents"].append(prow)
        try:
            page = json.loads(pbody.decode("utf-8", "replace")).get("docs") or {}
        except ValueError:
            break
        got = page.get("docs") or []
        total = page.get("count", total)
        docs.extend(got)
        skip += len(got)
        if not got or (total is not None and skip >= total):
            break
    bureau["listings_published"], bureau["listings_read"] = total or 0, len(docs)
    cats_seen, rows, seen = Counter(), [], set()
    for d in sorted(docs, key=lambda x: int(x.get("recid") or 0)):
        rec = d.get("recid")
        if rec in seen:
            continue
        seen.add(rec)
        categories = sorted({"%s / %s" % (c.get("catname") or "", c.get("subcatname") or "")
                             for c in (d.get("categories") or []) if isinstance(c, dict)})
        for c in categories:
            cats_seen[c] += 1
        if not any(any(w in c.lower() for w in LODGING_CATEGORY_WORDS) for c in categories):
            continue
        website = _s(d.get("weburl"))
        if website and not re.match(r"^https?://", website, re.I):
            website = "https://" + website.lstrip("/")
        rows.append(_row(bureau_id, rec, d.get("title"), d.get("address1"), d.get("city"),
                         _state(d.get("state")), "".join(ch for ch in str(d.get("zip") or "") if ch.isdigit()),
                         d.get("phone"), website, categories, host + str(d.get("detailURL") or ""),
                         bureau["documents"][-1]["sha256"] if bureau["documents"] else None, d.get("latitude"),
                         d.get("longitude"), extras=[_s(d.get("address2"))]))
    bureau["categories_seen"] = OrderedDict(cats_seen.most_common())
    bureau["lodging_partners"] = len(rows)
    return bureau, [placed(r) for r in rows]


def build():
    stats = Stats()
    bureaus, rows = OrderedDict(), []
    for bureau_id, host, catids, note in SIMPLEVIEW_BUREAUS:
        b, r = simpleview_bureau(stats, bureau_id, host, catids, note)
        bureaus[b["bureau_id"]] = b
        rows.extend(r)
    admitted = [r for r in rows if r["corridor_slug"]]
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "11 -- the official destination-marketing rosters (Visit Salt Lake, Visit Park City), "
                  "measured first"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("bytes_read", stats.bytes),
        ("the_bureau_was_measured", "Every bureau was probed before it was read; the platform each one runs is "
                                    "recorded, never assumed."),
        ("the_category_filter_is_read_not_trusted", "Only lodging-typed partners are kept; the census decides what "
                                                    "each row is and where it is."),
        ("a_roster_row_is_not_a_policy", "No bureau amenity chip or 'pet-friendly hotels' page is read, stored or "
                                         "published."),
        ("the_bureau_does_not_decide_membership", "The row's own postal code does -- and decides its "
                                                    "municipality."),
        ("bureaus_measured_and_not_walked", BUREAUS_MEASURED_AND_NOT_WALKED),
        ("bureaus", bureaus),
        ("row_count", len(rows)),
        ("rows_in_admitted_postal_codes", len(admitted)),
        ("rows_refused_by_postal_code", sum(1 for r in rows if r["postal_code"] and not r["corridor_slug"])),
        ("rows_without_a_postal_code", sum(1 for r in rows if not r["postal_code"])),
        ("rows_with_an_official_website", sum(1 for r in rows if r["official_url"])),
        ("rows_with_a_phone", sum(1 for r in rows if r["phone"])),
        ("rows_with_a_full_premises", sum(1 for r in rows if r["street"] and r["postal_code"])),
        ("rows_with_a_state_conflict", [r["name"] for r in rows if r["state_conflict"]]),
        ("rows_with_a_municipality_conflict", [OrderedDict([("name", r["name"]), ("city", r["city"]),
                                                            ("postal_code", r["postal_code"]),
                                                            ("why", r["municipality_conflict"])])
                                               for r in rows if r["municipality_conflict"]]),
        ("census_eligible_rows_in_admitted_codes", sum(1 for r in admitted if r["census_eligible_category"])),
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
    print("rows=%d admitted=%d no_zip=%d by_bureau=%s requests=%d state_conflicts=%s" % (
        rep["row_count"], rep["rows_in_admitted_postal_codes"], rep["rows_without_a_postal_code"],
        rep["by_bureau"], rep["free_http_requests"], rep["rows_with_a_state_conflict"]))
    print("by corridor:", rep["by_corridor"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
