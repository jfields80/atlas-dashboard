"""PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001 -- Phase 10: the official destination-marketing rosters.

EVERY BUREAU WAS MEASURED, NOT ASSUMED
--------------------------------------
The standing rule is to MEASURE a convention and visitors bureau before spending anything on it (the San Diego
and Jacksonville finding: never assume Simpleview, never assume a category filter works). The Kansas City bureaus,
on both sides of the state line, answered this plain client on 2026-10-05 like this:

  * VISIT KC (visitkc.com) -- WordPress, NOT Simpleview (``/plugins/core/get_simple_token/`` answers 404). Its own
    REST endpoint ``/wp-json/wp/v2/listing`` publishes all 885 partner listings with the bureau's own typing in
    ``class_list`` (``listing_category-accommodations``, ``-all-hotels``, ``-extended-stay-lodging``,
    ``-short-term-rentals``, ``-rv-parks-camping``). The index is read in nine paged requests; then each listing the
    bureau types ``accommodations`` (79) is read ONCE for the partner's own CRM record the page embeds
    (``crm_street``, ``crm_city``, ``crm_state``, ``crm_postal_code``, ``crm_phone``, ``crm_website``, pin) -- the
    same fields its own address card renders.
  * VISIT KANSAS CITY KANSAS (visitkansascityks.com) -- **Simpleview**: its own public listings endpoint
    (``/includes/rest_v2/plugins_listings_listings/find/`` with the site's own ``get_simple_token``) returns every
    partner with street, city, state, ZIP, telephone, website and the bureau's own category -- the Denver reader's
    call, unchanged.
  * VISIT OVERLAND PARK (visitoverlandpark.com) -- Craft CMS searching a partner index (application ``EYQHJ2IY2M``,
    index ``prod-visit-overland-park``) with the SEARCH-ONLY key the bureau embeds in its own pages, exactly as its
    own "Hotels" page does. Each ``Local Business`` record states the partner's own address lines, telephone, website
    and the bureau's own ``partnerCategories`` ("Accommodations >> Hotels" / "Accommodations >> Extended Stay").
  * VISIT INDEPENDENCE (visitindependence.com) -- the same Craft platform, but its index answers only a SECURED
    search key whose application is not published in the page; not worked around. Independence's hotels reach the
    census through the Missouri lodging register, the map and the brands.
  * VISIT SHAWNEE (visitshawneeks.com) -- WordPress with a small "stay" category; Shawnee's hotels reach the census
    through the map, the brands and Places. Measured, not walked.
  * olatheks.org and leawood.org -- HTTP 403 to this client; visitlenexa.com, northkansascity.org and
    visitbluesprings.com -- no answer; visitleessummit.com and visitliberty.com -- PARKED domains (a JavaScript
    redirect to "/lander"). Recorded, not worked around.

THE BUREAU'S CATEGORY IS READ, NOT TRUSTED
-----------------------------------------
Only lodging-typed partners are kept, and the census still decides what each row IS (a short-term-rental or RV
category is refused there) and WHERE it is (its own postal code, which also decides its STATE). The bureaus'
"Pet-Friendly" amenity chips and "pet-friendly hotels" pages are NEVER read, stored or published as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/kansas_city_mo_destination_roster_001.json
  data/acquisition/kansas_city_mo_destination_001/<sha256>.bin   (documents as returned)
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

from scripts.pettripfinder import kansas_city_mo_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001"
MARKET_ID = "kansas-city-mo"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "kansas_city_mo_destination_roster_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "kansas_city_mo_destination_001")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

VKC_HOST = "https://www.visitkc.com"
VKC_INDEX = VKC_HOST + "/wp-json/wp/v2/listing?per_page=100&page=%d&_fields=id,slug,link,title,class_list"
#: Visit KC's own lodging typings (class_list) -> the bureau category recorded on the row.
VKC_LODGING_CLASSES = OrderedDict([
    ("listing_category-all-hotels", "Accommodations / All Hotels"),
    ("listing_category-extended-stay-lodging", "Accommodations / Extended Stay Lodging"),
    ("listing_category-short-term-rentals", "Accommodations / Short Term Rentals"),
    ("listing_category-rv-parks-camping", "Accommodations / RV Parks Camping"),
    ("listing_category-accommodations", "Accommodations / Accommodations (parent category only)"),
])
KCK_HOST = "https://www.visitkansascityks.com"
OP_ALGOLIA_APP = "EYQHJ2IY2M"
#: The SEARCH-ONLY key Visit Overland Park embeds in its own pages' markup -- read-only.
OP_ALGOLIA_KEY = "c6d5977cb5cd80c09abfd2a7e5d9e88b"
OP_INDEX = "prod-visit-overland-park"
OP_HOTELS_PAGE = "https://www.visitoverlandpark.com/hotels/"

#: Bureaus measured and NOT walked, with what answered.
BUREAUS_MEASURED_AND_NOT_WALKED = OrderedDict([
    ("visitindependence.com", "Craft CMS; its partner index answers only a SECURED search key whose application id "
                              "the page does not publish -- not worked around"),
    ("visitshawneeks.com", "WordPress with a small '/listing-category/stay/' page; measured, not walked"),
    ("olatheks.org", "HTTP 403 to this plain client; recorded, not worked around"),
    ("leawood.org", "HTTP 403 to this plain client; recorded, not worked around"),
    ("visitlenexa.com", "no answer (connection failed)"),
    ("northkansascity.org", "no answer (connection failed)"),
    ("visitbluesprings.com", "no answer (connection failed)"),
    ("visitleessummit.com", "a parked domain (JavaScript redirect to /lander) -- not a bureau"),
    ("visitliberty.com", "a parked domain (JavaScript redirect to /lander) -- not a bureau"),
])

LODGING_CATEGORY_WORDS = ("hotel", "motel", "inn", "resort", "lodging", "lodge", "bed and breakfast",
                          "bed & breakfast", "b&b", "accommodation", "stay", "suites", "campground",
                          "rv park", "vacation rental", "short term rental", "condo", "hostel")
NON_CENSUS_CATEGORY_WORDS = ("vacation rental", "short term rental", "condo", "campground", "rv park", "camping",
                             "house rental", "home rental", "cottage rental")
_TOLL_FREE = re.compile(r"^\(?\+?1?\s*\(?8(00|33|44|55|66|77|88)\)?")
_STATE_NAMES = {"missouri": "MO", "mo": "MO", "kansas": "KS", "ks": "KS"}


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
    """'Overland Park, Kansas 66210' -> ('Overland Park', 'KS', '66210')."""
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
    # the cross-state guard, recorded on the roster row itself: the census holds a contradiction, never fixes it
    row["state_conflict"] = GEO.state_conflict(row.get("postal_code"), row.get("state"))
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


# --------------------------------------------------------------------------- Visit KC (WordPress)
_CRM = re.compile(r'"crm_(street|suite|city|state|postal_code|phone|website|coordinates_lat|coordinates_lng)"'
                  r':"((?:[^"\\]|\\.)*)"')


def _crm_fields(text):
    out = {}
    for k, v in _CRM.findall(text):
        if k not in out:
            try:
                out[k] = json.loads('"%s"' % v)
            except ValueError:
                out[k] = v
    return out


def visit_kc(stats):
    bureau = OrderedDict([("bureau_id", "visit-kc"), ("platform", "WordPress (REST listing index + listing pages)"),
                          ("index_documents", []), ("listing_documents", []), ("listings_in_index", 0),
                          ("lodging_typed_listings", 0)])
    listings, page = [], 1
    while page <= 20:
        doc, body = fetch(VKC_INDEX % page, stats, timeout=60)
        bureau["index_documents"].append(doc)
        if not body:
            break
        try:
            got = json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            break
        if not isinstance(got, list) or not got:
            break
        listings.extend(got)
        if len(got) < 100:
            break
        page += 1
    bureau["listings_in_index"] = len(listings)
    rows = []
    for li in sorted(listings, key=lambda x: int(x.get("id") or 0)):
        classes = li.get("class_list") or []
        cats = [label for cls, label in VKC_LODGING_CLASSES.items() if cls in classes]
        if not cats:
            continue
        # the parent category is recorded only when the bureau gives the listing no sub-category of its own
        if len(cats) > 1:
            cats = [c for c in cats if not c.endswith("(parent category only)")]
        bureau["lodging_typed_listings"] += 1
        d, b = fetch(li["link"], stats)
        bureau["listing_documents"].append(d)
        time.sleep(0.4)
        crm = _crm_fields(b.decode("utf-8", "replace"))
        rows.append(_row("visit-kc", li.get("id"), (li.get("title") or {}).get("rendered"), crm.get("street"),
                         crm.get("city"), _state(crm.get("state")), crm.get("postal_code"), crm.get("phone"),
                         crm.get("website"), cats, li["link"], d["sha256"], crm.get("coordinates_lat"),
                         crm.get("coordinates_lng"), extras=[_s(crm.get("suite"))]))
    return bureau, [placed(r) for r in rows]


# --------------------------------------------------------------------------- Visit KCK (Simpleview)
SIMPLEVIEW_FIELDS = OrderedDict((k, 1) for k in (
    "recid", "title", "address1", "address2", "city", "state", "zip", "phone", "weburl", "categories",
    "latitude", "longitude", "detailURL", "typeName"))
SIMPLEVIEW_PAGE = 100


def visit_kck(stats, cap=40):
    bureau = OrderedDict([("bureau_id", "visit-kansas-city-kansas"), ("platform", "Simpleview listings endpoint"),
                          ("entry", None), ("documents", []), ("listings_published", 0), ("listings_read", 0),
                          ("categories_seen", OrderedDict()), ("lodging_partners", 0)])
    trow, tbody = fetch(KCK_HOST + "/plugins/core/get_simple_token/", stats)
    token = tbody.decode("utf-8", "replace").strip()
    bureau["entry"] = trow
    if trow.get("status") != 200 or not re.match(r"^[0-9a-f]{16,64}$", token):
        bureau["disposition"] = "SIMPLEVIEW_TOKEN_NOT_ISSUED__STATUS_%s" % trow.get("status")
        return bureau, []
    docs, skip, total, spent = [], 0, None, 0
    while spent < cap:
        q = json.dumps(OrderedDict([("filter", OrderedDict()), ("options", OrderedDict([
            ("limit", SIMPLEVIEW_PAGE), ("skip", skip), ("count", True), ("fields", SIMPLEVIEW_FIELDS),
            ("sort", OrderedDict([("recid", 1)]))]))]), separators=(",", ":"))
        url = KCK_HOST + "/includes/rest_v2/plugins_listings_listings/find/?" + urllib.parse.urlencode(
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
        rows.append(_row("visit-kansas-city-kansas", rec, d.get("title"), d.get("address1"), d.get("city"),
                         _state(d.get("state")), "".join(ch for ch in str(d.get("zip") or "") if ch.isdigit()),
                         d.get("phone"), website, categories, KCK_HOST + str(d.get("detailURL") or ""),
                         bureau["documents"][-1]["sha256"] if bureau["documents"] else None, d.get("latitude"),
                         d.get("longitude"), extras=[_s(d.get("address2"))]))
    bureau["categories_seen"] = OrderedDict(cats_seen.most_common())
    bureau["lodging_partners"] = len(rows)
    return bureau, [placed(r) for r in rows]


# --------------------------------------------------------------------------- Visit Overland Park (partner index)
def visit_overland_park(stats):
    bureau = OrderedDict([("bureau_id", "visit-overland-park"), ("platform", "Craft CMS + partner search index"),
                          ("index", OP_INDEX), ("documents", []), ("lodging_typed_records", 0)])
    filt = ('sectionName:"Local Business" AND (partnerCategories:"Accommodations » Hotels" OR '
            'partnerCategories:"Accommodations » Extended Stay")')
    hits, page = [], 0
    while page <= 10:
        params = "query=&hitsPerPage=1000&page=%d&filters=%s" % (page, urllib.parse.quote(filt))
        url = "https://%s-dsn.algolia.net/1/indexes/%s?%s" % (OP_ALGOLIA_APP, OP_INDEX, params)
        doc, body = fetch(url, stats, headers={"X-Algolia-API-Key": OP_ALGOLIA_KEY,
                                               "X-Algolia-Application-Id": OP_ALGOLIA_APP,
                                               "Referer": OP_HOTELS_PAGE,
                                               "Origin": "https://www.visitoverlandpark.com"})
        bureau["documents"].append(doc)
        if not body:
            break
        data = json.loads(body.decode("utf-8", "replace"))
        hits.extend(data.get("hits") or [])
        page += 1
        if page >= int(data.get("nbPages") or 0):
            break
    rows, seen = [], set()
    for h in hits:
        pid = _s(h.get("id"))
        if pid in seen:
            continue
        seen.add(pid)
        cats = [c.replace(" » ", " / ") for c in (h.get("partnerCategories") or [])
                if str(c).startswith("Accommodations")]
        addr = [a for a in (h.get("address") or []) if _s(a)]
        street = _s(addr[0]) if addr else ""
        city, state, postal = split_city_line(addr[-1]) if len(addr) >= 2 else ("", "", "")
        geo = h.get("_geoloc") or {}
        rows.append(_row("visit-overland-park", pid, h.get("title"), street, city, state, postal, h.get("phone"),
                         h.get("website"), cats, "https://www.visitoverlandpark.com" + _s(h.get("uri")),
                         bureau["documents"][-1]["sha256"] if bureau["documents"] else None, geo.get("lat"),
                         geo.get("lng"), extras=[_s(a) for a in addr[1:-1]]))
    bureau["lodging_typed_records"] = len(rows)
    return bureau, [placed(r) for r in rows]


def build():
    stats = Stats()
    bureaus, rows = OrderedDict(), []
    for fn in (visit_kc, visit_kck, visit_overland_park):
        b, r = fn(stats)
        bureaus[b["bureau_id"]] = b
        rows.extend(r)
    admitted = [r for r in rows if r["corridor_slug"]]
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "10 -- the official destination-marketing rosters (Visit KC, Visit Kansas City Kansas, Visit "
                  "Overland Park), measured first"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("bytes_read", stats.bytes),
        ("the_bureau_was_measured", "Every bureau was probed before it was read; the platform each one runs is "
                                    "recorded, never assumed."),
        ("the_category_filter_is_read_not_trusted", "Only lodging-typed partners are kept; the census decides what "
                                                    "each row is and where it is."),
        ("a_roster_row_is_not_a_policy", "No bureau amenity chip or 'pet-friendly hotels' page is read, stored or "
                                         "published."),
        ("the_bureau_does_not_decide_membership", "The row's own postal code does -- and decides its state."),
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
