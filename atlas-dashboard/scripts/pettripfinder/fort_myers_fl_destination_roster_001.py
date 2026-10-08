"""PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001 -- Phase 13: the official destination-marketing roster.

EVERY BUREAU WAS MEASURED, NOT ASSUMED
--------------------------------------
The standing rule is to MEASURE a convention and visitors bureau before spending anything on it (the San Diego
and Jacksonville finding: never assume Simpleview, never assume a category filter works). The Fort Myers bureau
answered this plain client on 2026-10-08 like this:

  * THE BEACHES OF FORT MYERS & SANIBEL -- the Lee County Visitor & Convention Bureau (visitfortmyers.com) -- is NOT
    Simpleview (its ``/plugins/core/get_simple_token/`` answers 404). It is DRUPAL 10 on Pantheon whose listing pages
    are a React bundle (``leevcb_utilities/category_listing``) that queries the bureau's OWN public search proxy:
    ``POST /api/v1/opensearch/elasticsearch_index_pantheon_prod_leevcb_business/_search`` with an ordinary
    OpenSearch query. MEASURED over the whole index: 762 active business listings; the bureau's own category field
    (``name``) types lodging as "Places to Stay" (187: Hotel 96, Vacation Rental 52, Resort 39, Condo 37, Cottage 19,
    Campgrounds 10, RV Park 8, Motel 6, Bed & Breakfast 4 -- a listing can carry several) and "Meeting Venues &
    Hotels" (42). Both are read. The index carries a title, a pin, a website and the bureau's neighbourhood but NO
    street address, so each lodging listing's OWN bureau page (``/listing/<slug>/<id>``) is read once for its
    structured premises -- ``<p class="address">`` with ``address-line1`` / ``locality`` / ``administrative-area`` /
    ``postal-code`` spans and its ``tel:`` link. The bureau's own footer address (2201 Second Street) is never read
    as a partner's premises: only the FIRST ``p.address`` block is parsed.
  * The bureau's neighbourhood facet is MEASURED (Fort Myers 292, Bonita Springs & Estero 96, Fort Myers Beach 93,
    Cape Coral 89, Sanibel Island 82, Captiva Island 42, Boca Grande & Outer Islands 25, Pine Island 24, North Fort
    Myers 20, Matlacha 16, Alva / Buckingham / Lehigh Acres 11) and never used for membership: the listing's own
    postal code decides.
  * VISIT FLORIDA (visitflorida.com) links to the county bureaus; recorded, not walked. The Fort Myers Beach, Sanibel
    & Captiva and Bonita Springs chambers answered this client with TLS refusals or redirects (measured); the county
    bureau already carries their members.

THE BUREAU'S CATEGORY IS READ, NOT TRUSTED
-----------------------------------------
Only lodging-typed partners are kept, and the census still decides what each row IS (a vacation-home, condo,
rent-by-owner, central-reservations, property-management or campground typing is refused there) and WHERE it is (its
own postal code, which also decides its MUNICIPALITY -- a Bonita Springs-labelled listing in a Naples postal code is OUTSIDE). The
bureaus' "Pet-Friendly" amenity chips, categories and "pet-friendly hotels" pages are NEVER read, stored or published
as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/fort_myers_fl_destination_roster_001.json
  data/acquisition/fort_myers_fl_destination_001/<sha256>.bin   (documents as returned)
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

from scripts.pettripfinder import fort_myers_fl_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "fort-myers-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "fort_myers_fl_destination_roster_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "fort_myers_fl_destination_001")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: The bureau read: its own public OpenSearch proxy, MEASURED on 2026-10-08.
LEE_VCB_HOST = "https://www.visitfortmyers.com"
LEE_VCB_SEARCH = LEE_VCB_HOST + "/api/v1/opensearch/elasticsearch_index_pantheon_prod_leevcb_business/_search"
LEE_VCB_CATEGORIES = ("Places to Stay", "Meeting Venues & Hotels")

#: Bureaus measured and NOT walked, with what answered.
BUREAUS_MEASURED_AND_NOT_WALKED = OrderedDict([
    ("visitflorida.com", "the state tourism office; links to the county bureaus -- recorded, not walked"),
    ("fortmyersbeachchamber.org / capecoral.net / bonitaspringschamber.com",
     "answered this plain client with a TLS refusal (curl exit 35) on 2026-10-08 -- measured, not walked; the "
     "county bureau carries their lodging members"),
    ("sanibel-captiva.org", "the Sanibel & Captiva Islands Chamber; a 301 to its bare host -- measured, not walked"),
    ("visitfortmyers.com /plugins/core/get_simple_token/", "404 -- the bureau is not Simpleview"),
])

LODGING_CATEGORY_WORDS = ("hotel", "motel", "inn", "resort", "lodging", "lodge", "bed and breakfast",
                          "bed & breakfast", "b&b", "accommodation", "stay", "suites", "campground",
                          "rv park", "vacation rental", "short term rental", "condo", "hostel")
NON_CENSUS_CATEGORY_WORDS = ("vacation rental", "short term rental", "condo", "campground", "rv park", "camping",
                             "house rental", "home rental", "cottage rental", "reservation service", "apartment",
                             "condominium", "vacation home", "rent by owner", "central reservations",
                             "booking services", "property management", "long-term rental", "universities")
_TOLL_FREE = re.compile(r"^\(?\+?1?\s*\(?8(00|33|44|55|66|77|88)\)?")
_STATE_NAMES = {"florida": "FL", "fl": "FL"}


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
    """'Cape Coral, Florida 33904' -> ('Cape Coral', 'FL', '33904')."""
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


# --------------------------------------------------------------------------- the Lee County bureau
_ADDR_BLOCK = re.compile(r'<p class="address"[^>]*>(.*?)</p>', re.S)


def _span(block, cls):
    m = re.search(r'<span class="%s">(.*?)</span>' % re.escape(cls), block, re.S)
    return _s(re.sub(r"<[^>]+>", " ", m.group(1))) if m else ""


def parse_listing_page(text):
    """The partner's own premises on its bureau page: the FIRST structured ``p.address`` block (the bureau's footer
    address is a plain ``<address>`` element and is never read) and the first ``a.phone`` tel: link."""
    m = _ADDR_BLOCK.search(text or "")
    if not m:
        return OrderedDict()
    block = m.group(1)
    phone = re.search(r'<a\s+class="phone"\s+href="tel:([^"]+)"', text or "")
    return OrderedDict([
        ("street", _span(block, "address-line1")), ("street2", _span(block, "address-line2")),
        ("city", _span(block, "locality")), ("state", _state(_span(block, "administrative-area"))),
        ("postal_code", "".join(ch for ch in _span(block, "postal-code") if ch.isdigit())[:5]),
        ("phone", _s(phone.group(1)) if phone else ""),
    ])


def lee_vcb_bureau(stats):
    bureau = OrderedDict([("bureau_id", "lee-county-vcb"),
                          ("platform", "Drupal 10 on Pantheon; the bureau's own public OpenSearch proxy, filtered to "
                                       "its own lodging categories (" + " / ".join(LEE_VCB_CATEGORIES) + "), then "
                                       "each lodging listing's own bureau page for its structured premises"),
                          ("entry", None), ("documents", []), ("listings_published", 0), ("listings_read", 0),
                          ("categories_seen", OrderedDict()), ("lodging_partners", 0), ("listing_pages_read", 0),
                          ("listing_pages_without_an_address", [])])
    q = OrderedDict([("from", 0), ("size", 400), ("sort", [OrderedDict([("title.keyword", "asc")])]),
                     ("query", OrderedDict([("bool", OrderedDict([("must", [
                         OrderedDict([("terms", OrderedDict([("status", [True])]))]),
                         OrderedDict([("terms", OrderedDict([("name", list(LEE_VCB_CATEGORIES))]))])])]))]))])
    srow, sbody = fetch(LEE_VCB_SEARCH, stats, headers={"Content-Type": "application/json",
                                                       "Accept": "application/json",
                                                       "Referer": LEE_VCB_HOST + "/stay"},
                        data=json.dumps(q).encode("utf-8"), timeout=60)
    srow["request_body"] = json.dumps(q, separators=(",", ":"))
    bureau["entry"] = srow
    bureau["documents"].append(srow)
    try:
        hits = json.loads(sbody.decode("utf-8", "replace")).get("hits") or {}
    except ValueError:
        hits = {}
    docs = hits.get("hits") or []
    total = (hits.get("total") or {}).get("value", len(docs))
    bureau["listings_published"], bureau["listings_read"] = total, len(docs)
    cats_seen, rows = Counter(), []
    for d in sorted(docs, key=lambda x: str(x.get("_id"))):
        src = d.get("_source") or {}
        categories = sorted({_s(c) for c in (src.get("name") or [])})
        for c in categories:
            cats_seen[c] += 1
        title = _s((src.get("title") or [""])[0])
        path = _s((src.get("url") or [""])[0])
        listing_url = LEE_VCB_HOST + path if path else ""
        website = _s((src.get("website") or [""])[0])
        if website and not re.match(r"^https?://", website, re.I):
            website = "https://" + website.lstrip("/")
        lrow, lbody = fetch(listing_url, stats, timeout=40) if listing_url else ({}, b"")
        if listing_url:
            bureau["listing_pages_read"] += 1
        prem = parse_listing_page(lbody.decode("utf-8", "replace")) if lbody else OrderedDict()
        if not prem.get("postal_code"):
            bureau["listing_pages_without_an_address"].append(OrderedDict([
                ("title", title), ("listing_url", listing_url), ("status", lrow.get("status"))]))
        lat = (src.get("lat") or [None])[0]
        lng = (src.get("lng") or [None])[0]
        rows.append(_row("lee-county-vcb", d.get("_id"), title, prem.get("street"), prem.get("city"),
                         prem.get("state") or "", prem.get("postal_code") or "", prem.get("phone"), website,
                         categories, listing_url, lrow.get("sha256"), lat, lng,
                         extras=[prem.get("street2"), "bureau neighbourhood: " + ", ".join(src.get("nhood") or [])]))
        time.sleep(0.4)
    bureau["categories_seen"] = OrderedDict(cats_seen.most_common())
    bureau["lodging_partners"] = len(rows)
    return bureau, [placed(r) for r in rows]


def build():
    stats = Stats()
    bureaus, rows = OrderedDict(), []
    b, r = lee_vcb_bureau(stats)
    bureaus[b["bureau_id"]] = b
    rows.extend(r)
    admitted = [r for r in rows if r["corridor_slug"]]
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "13 -- the official destination-marketing roster (The Beaches of Fort Myers & Sanibel, the Lee "
                  "County Visitor & Convention Bureau), measured first"),
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
