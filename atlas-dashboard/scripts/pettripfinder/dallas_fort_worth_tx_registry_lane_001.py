"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phase 12: the Texas lodging register lane (Hotel Tax Permits).

Cloned from the San Antonio register lane (PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001), with the Dallas / Fort Worth
sectional centers, the State permit's own COUNTY as a refusal signal, and a boundary audit by named outer place.

WHAT THIS IS
------------
The Texas Comptroller of Public Accounts publishes every HOTEL OCCUPANCY TAX PERMIT location on the state's open
data portal (data.texas.gov dataset ``hdzd-884n``, "Hotel Tax Permits"): the taxpayer number, the location number,
the location NAME, its street number and street, city, ZIP, county, NAICS code, the date the responsibility began and
-- when it closed -- the OUT-OF-BUSINESS date. Every Texas lodging establishment that collects state hotel tax holds
one, so it is the independent statewide register of the Metroplex's lodging premises.

WHAT IT IS USED FOR, AND WHAT IT NEVER DECIDES
----------------------------------------------
Tier-3 IDENTITY and CLOSURE evidence:
  * an ACTIVE permit (no out-of-business date) under a hotel NAICS (721110 hotels and motels, 721120 casino hotels,
    721000 the Comptroller's generic accommodation code, 721191 bed-and-breakfast inns) at an admitted postal code is
    a census LEAD with a full premises;
  * a permit whose own COUNTY is a refused county (Rockwall, Kaufman, Ellis, Johnson, Parker, Wise ...) is recorded
    ``county_refused`` -- the census refuses that building whatever other lane reaches it (the Burleson / Mansfield /
    Rowlett / White Settlement edges of admitted codes);
  * a permit with an OUT-OF-BUSINESS date is CLOSURE evidence for that location name at that premises (a closed or
    re-flagged operator), recorded -- a hotel whose own page still sells rooms is never closed on it;
  * every other NAICS (531110 / 531311 residential rental and property managers, 721199 other traveller
    accommodation, 721211 RV parks, 721310 rooming houses, and the rest) is short-term-rental, RV or rooming-house
    inventory and is COUNTED, never a hotel lead.
A permit carries no pet policy, admits nothing by itself (the corridor registry over its postal code does that) and
never outranks the property's own page. Its location name is often a store number ("LA QUINTA INN- DALLAS # 907");
the census strips the store number for naming and keeps the raw name on the observation. Its CITY is the taxpayer's
mailing city and never decides a municipality (dallas_fort_worth_tx_municipal_boundaries_001 does).

A register lane is free and read-only: the Socrata API is paged 5,000 rows at a time over the Dallas / Fort Worth
sectional centers (750-753, 760-762) for full rows, and the refused outer places' active hotel permits (754 Greenville
/ Northeast Texas, 763 Wichita Falls, 765 Temple, 766 / 767 Waco) are read for the boundary audit only.

Output:
  launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_registry_lane_001.json
  data/acquisition/dallas_fort_worth_tx_registry_001/<sha256>.json   (every page as returned)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import dallas_fort_worth_tx_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
DATASET = "hdzd-884n"
ENDPOINT = "https://data.texas.gov/resource/%s.json" % DATASET
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "dallas_fort_worth_tx_registry_001")
OUT = os.path.join(REPORTS, "dallas_fort_worth_tx_registry_lane_001.json")
PAGE = 5000
UA = "PetTripFinder census lane (read-only; data.texas.gov open data)"

HOTEL_NAICS = {"721110", "721120", "721000", "721191"}
NAICS_LABEL = {
    "721110": "Hotels (except casino hotels) and motels", "721120": "Casino hotels",
    "721000": "Accommodation (Comptroller generic)", "721191": "Bed-and-breakfast inns",
    "721199": "All other traveler accommodation", "721211": "RV parks and campgrounds",
    "721214": "Recreational and vacation camps", "721310": "Rooming and boarding houses",
    "531110": "Lessors of residential buildings (short-term rental)",
    "531311": "Residential property managers (short-term rental)",
}
CORE_PREFIXES = ("750", "751", "752", "753", "760", "761", "762")
BOUNDARY_PREFIXES = ("754", "763", "765", "766", "767")
_STORE_NUMBER = re.compile(r"\s*(?:#|no\.?|num\.?)\s*\d+\s*$", re.I)

#: The outer places the order asks to see by name (boundary audit), by the permit's own city or postal code.
NAMED_OUTSIDE_PLACES = OrderedDict([
    ("WEATHERFORD", {"cities": {"weatherford", "willow park", "hudson oaks", "aledo"}, "zips": set()}),
    ("WAXAHACHIE", {"cities": {"waxahachie"}, "zips": set()}),
    ("ENNIS", {"cities": {"ennis"}, "zips": set()}),
    ("CORSICANA", {"cities": {"corsicana", "angus"}, "zips": set()}),
    ("GREENVILLE", {"cities": {"greenville"}, "zips": {"75401", "75402", "75403", "75404"}}),
    ("SHERMAN / DENISON", {"cities": {"sherman", "denison", "pottsboro"}, "zips": set()}),
    ("GAINESVILLE", {"cities": {"gainesville", "gainsville"}, "zips": set()}),
    ("WACO", {"cities": {"waco", "woodway", "bellmead", "hewitt", "lacy lakeview", "robinson"}, "zips": set()}),
    ("DECATUR", {"cities": {"decatur"}, "zips": set()}),
    ("DENTON", {"cities": {"denton", "corinth", "shady shores"}, "zips": set()}),
    ("ROCKWALL", {"cities": {"rockwall", "fate", "heath", "mclendon chisholm", "royse city"}, "zips": set()}),
])


def persist(body):
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, digest + ".json")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(body)
    return digest


def fetch_rows(where, stats):
    rows, offset, pages = [], 0, []
    while True:
        q = urllib.parse.urlencode([("$where", where), ("$limit", PAGE), ("$offset", offset),
                                    ("$order", "tp_number,loc_number")])
        url = ENDPOINT + "?" + q
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        stats["requests"] += 1
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read()
        got = json.loads(body.decode("utf-8"))
        pages.append(OrderedDict([("url", url), ("rows", len(got)), ("sha256", persist(body)),
                                  ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))]))
        rows.extend(got)
        if len(got) < PAGE:
            break
        offset += PAGE
        time.sleep(1.0)
    return rows, pages


def _s(v):
    return " ".join(str(v or "").split())


def county_name(code):
    c = _s(code)
    return GEO.COMPTROLLER_COUNTY.get(str(int(c)) if c.isdigit() else c, "county %s" % c if c else "")


def lead(r, snapshot):
    naics = _s(r.get("naics"))
    name = _s(r.get("loc_name"))
    z = _s(r.get("loc_zip"))[:5]
    city = _s(r.get("loc_city")).title()
    klass, slug, why = GEO.classify_postal(z, city)
    county = county_name(r.get("loc_county"))
    refusal = GEO.county_refusal_reason(county) if slug else ""
    return OrderedDict([
        ("lane", "REGISTRY_LICENCE"),
        ("business_name", _STORE_NUMBER.sub("", name).strip(" -#") or name),
        ("registered_location_name", name),
        ("street", _s("%s %s" % (_s(r.get("address_number")), _s(r.get("address_text"))))),
        ("city", city), ("state", _s(r.get("loc_state")) or "TX"), ("postal_code", z),
        ("license_number", "%s-%s" % (_s(r.get("tp_number")), _s(r.get("loc_number")))),
        ("taxpayer_number", _s(r.get("tp_number"))),
        ("rank_code", naics), ("naics_code", naics), ("naics_label", NAICS_LABEL.get(naics, "")),
        ("responsibility_begin_date", _s(r.get("resp_begin_date"))[:10]),
        ("out_of_business_date", _s(r.get("out_of_business_date"))[:10]),
        ("county_code", _s(r.get("loc_county"))), ("county", county),
        ("county_refused", bool(refusal)), ("county_refusal_reason", refusal),
        ("geography_class", klass), ("corridor_slug", slug), ("membership_reason", why),
        ("snapshot_sha256", snapshot),
        ("raw_pointer", "https://data.texas.gov/resource/%s.json?tp_number=%s&loc_number=%s"
         % (DATASET, _s(r.get("tp_number")), _s(r.get("loc_number")))),
    ])


def named_place(row):
    city = _s(row.get("loc_city") or row.get("city")).lower()
    z = _s(row.get("loc_zip") or row.get("postal_code"))[:5]
    for place, spec in NAMED_OUTSIDE_PLACES.items():
        if city in spec["cities"] or z in spec["zips"]:
            return place
    return ""


def build():
    stats = {"requests": 0}
    core_where = " OR ".join("starts_with(loc_zip,'%s')" % p for p in CORE_PREFIXES)
    core, core_pages = fetch_rows("(%s)" % core_where, stats)
    bnd_where = "(%s) AND out_of_business_date IS NULL AND naics IN ('721110','721120','721000','721191')" % (
        " OR ".join("starts_with(loc_zip,'%s')" % p for p in BOUNDARY_PREFIXES))
    boundary, boundary_pages = fetch_rows(bnd_where, stats)
    snap = core_pages[0]["sha256"] if core_pages else ""
    all_rows = [lead(r, snap) for r in core]
    active = [r for r in all_rows if not r["out_of_business_date"]]
    closed = [r for r in all_rows if r["out_of_business_date"]]
    hotel_active = [r for r in active if r["naics_code"] in HOTEL_NAICS]
    admitted_hotel = [r for r in hotel_active if r["corridor_slug"] and not r["county_refused"]]
    county_refused = [r for r in hotel_active if r["corridor_slug"] and r["county_refused"]]
    closed_hotel_admitted = [r for r in closed if r["naics_code"] in HOTEL_NAICS and r["corridor_slug"]]
    bnd = Counter()
    for r in boundary:
        z = _s(r.get("loc_zip"))[:5]
        fid = GEO.future_market_for(z) or "other"
        bnd[fid] += 1
    named = OrderedDict((p, OrderedDict([("discovered_active_hotel_permits", 0), ("admitted", 0)]))
                        for p in NAMED_OUTSIDE_PLACES)
    for r in hotel_active:
        p = named_place({"city": r["city"], "postal_code": r["postal_code"]})
        if p:
            named[p]["discovered_active_hotel_permits"] += 1
            if r["corridor_slug"] and not r["county_refused"]:
                named[p]["admitted"] += 1
    for r in boundary:
        p = named_place(r)
        if p:
            named[p]["discovered_active_hotel_permits"] += 1
    by_county = Counter(r["county"] for r in admitted_hotel)
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "12 -- the Texas lodging register (Comptroller Hotel Tax Permits, data.texas.gov hdzd-884n)"),
        ("source", OrderedDict([
            ("dataset", "Hotel Tax Permits (Texas Comptroller of Public Accounts)"),
            ("endpoint", ENDPOINT),
            ("licence", "Texas Open Data Portal -- public domain / open"),
        ])),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats["requests"]),
        ("a_register_row_is_not_a_policy",
         "Tier-3 IDENTITY and CLOSURE evidence. A permit carries no pet policy, admits nothing by itself and never "
         "outranks the property's own page. Its city is a mailing city, never a municipality decision."),
        ("hotel_naics", sorted(HOTEL_NAICS)),
        ("core_prefixes", list(CORE_PREFIXES)), ("boundary_prefixes", list(BOUNDARY_PREFIXES)),
        ("core_rows", len(all_rows)),
        ("core_active", len(active)),
        ("core_closed", len(closed)),
        ("core_active_by_naics", OrderedDict(Counter(r["naics_code"] for r in active).most_common())),
        ("core_closed_by_naics", OrderedDict(Counter(r["naics_code"] for r in closed).most_common())),
        ("hotel_active_rows", len(hotel_active)),
        ("hotel_active_in_admitted_postal_codes", len(admitted_hotel)),
        ("hotel_active_in_admitted_postal_codes_by_county", OrderedDict(by_county.most_common())),
        ("hotel_active_county_refused_in_admitted_postal_codes", len(county_refused)),
        ("county_refused_permits", [OrderedDict([("business_name", r["business_name"]), ("street", r["street"]),
                                                 ("city", r["city"]), ("postal_code", r["postal_code"]),
                                                 ("county", r["county"]), ("why", r["county_refusal_reason"])])
                                    for r in county_refused]),
        ("hotel_active_by_corridor", OrderedDict(sorted(Counter(r["corridor_slug"] for r in admitted_hotel).items()))),
        ("closed_hotel_rows_in_admitted_postal_codes", len(closed_hotel_admitted)),
        ("boundary_active_hotel_permits_by_future_market", OrderedDict(sorted(bnd.items()))),
        ("named_outside_places", named),
        ("pages", core_pages + boundary_pages),
        ("leads", hotel_active),
        ("closed_hotel_permits", [r for r in closed if r["naics_code"] in HOTEL_NAICS]),
        ("non_hotel_active_counted", OrderedDict(Counter(r["naics_code"] for r in active
                                                         if r["naics_code"] not in HOTEL_NAICS).most_common())),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for k in ("core_rows", "core_active", "core_closed", "hotel_active_rows", "hotel_active_in_admitted_postal_codes",
              "hotel_active_county_refused_in_admitted_postal_codes", "closed_hotel_rows_in_admitted_postal_codes",
              "free_http_requests"):
        print("%-52s %s" % (k, rep[k]))
    print("by county:", dict(rep["hotel_active_in_admitted_postal_codes_by_county"]))
    print("by corridor:", dict(rep["hotel_active_by_corridor"]))
    print("named outside:", {k: (v["discovered_active_hotel_permits"], v["admitted"])
                             for k, v in rep["named_outside_places"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
