"""PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001 -- Phase 8: the Texas lodging register lane (Hotel Tax Permits).

WHAT THIS IS
------------
The Texas Comptroller of Public Accounts publishes every HOTEL OCCUPANCY TAX PERMIT location on the state's open
data portal (data.texas.gov dataset ``hdzd-884n``, "Hotel Tax Permits", refreshed 2026-09-26): the taxpayer number,
the location number, the location NAME, its street number and street, city, ZIP, county, NAICS code, the date the
responsibility began and -- when it closed -- the OUT-OF-BUSINESS date. Every Texas lodging establishment that
collects state hotel tax holds one, so it is the independent statewide register the order's "Texas lodging /
business data" lane asks for -- the Texas equivalent of Florida's DBPR lodging licence file.

WHAT IT IS USED FOR, AND WHAT IT NEVER DECIDES
----------------------------------------------
Tier-3 IDENTITY and CLOSURE evidence:
  * an ACTIVE permit (no out-of-business date) under a hotel NAICS (721110 hotels and motels, 721120 casino hotels,
    721000 the Comptroller's generic accommodation code, 721191 bed-and-breakfast inns) at an admitted postal code is
    a census LEAD with a full premises;
  * a permit with an OUT-OF-BUSINESS date is CLOSURE evidence for that location name at that premises (a closed or
    re-flagged operator), recorded -- a hotel whose own page still sells rooms is never closed on it;
  * every other NAICS (531110 / 531311 residential rental and property managers, 721199 other traveller
    accommodation, 721211 RV parks, 721310 rooming houses, and the rest) is short-term-rental, RV or rooming-house
    inventory and is COUNTED, never a hotel lead.
A permit carries no pet policy, admits nothing by itself (the corridor registry over its postal code does that) and
never outranks the property's own page. Its location name is often a store number ("LA QUINTA INN- SAN ANTONIO # 907"); the census strips the store number for naming and keeps the raw name on the observation.

A register lane is free and read-only: the Socrata API is paged 5,000 rows at a time over the South Texas postal
prefixes (780 / 781 / 782) for full rows, and the refused neighbours' active hotel permits (786 / 787 Austin, 783 /
784 Corpus Christi, 788 / 789 / 779) are read for the boundary audit only.

Output:
  launch_packages/pettripfinder/markets/reports/san_antonio_tx_registry_lane_001.json
  data/acquisition/san_antonio_tx_registry_001/<sha256>.json   (every page as returned)
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

from scripts.pettripfinder import san_antonio_tx_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-antonio-tx"
DATASET = "hdzd-884n"
ENDPOINT = "https://data.texas.gov/resource/%s.json" % DATASET
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "san_antonio_tx_registry_001")
OUT = os.path.join(REPORTS, "san_antonio_tx_registry_lane_001.json")
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
CORE_PREFIXES = ("780", "781", "782")
BOUNDARY_PREFIXES = ("786", "787", "783", "784", "788", "789", "779")
_STORE_NUMBER = re.compile(r"\s*(?:#|no\.?|num\.?)\s*\d+\s*$", re.I)


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
        with urllib.request.urlopen(req, timeout=120) as resp:
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


def lead(r, snapshot):
    naics = _s(r.get("naics"))
    name = _s(r.get("loc_name"))
    z = _s(r.get("loc_zip"))[:5]
    city = _s(r.get("loc_city")).title()
    klass, slug, why = GEO.classify_postal(z, city)
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
        ("county_code", _s(r.get("loc_county"))),
        ("geography_class", klass), ("corridor_slug", slug), ("membership_reason", why),
        ("snapshot_sha256", snapshot),
        ("raw_pointer", "https://data.texas.gov/resource/%s.json?tp_number=%s&loc_number=%s"
         % (DATASET, _s(r.get("tp_number")), _s(r.get("loc_number")))),
    ])


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
    admitted_hotel = [r for r in hotel_active if r["corridor_slug"]]
    closed_hotel_admitted = [r for r in closed if r["naics_code"] in HOTEL_NAICS and r["corridor_slug"]]
    bnd = Counter()
    for r in boundary:
        z = _s(r.get("loc_zip"))[:5]
        fid = GEO.future_market_for(z) or "other"
        bnd[fid] += 1
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "8 -- the Texas lodging register (Comptroller Hotel Tax Permits, data.texas.gov hdzd-884n)"),
        ("source", OrderedDict([
            ("dataset", "Hotel Tax Permits (Texas Comptroller of Public Accounts)"),
            ("endpoint", ENDPOINT), ("portal_refreshed", "2026-09-26"),
            ("licence", "Texas Open Data Portal -- public domain / open"),
        ])),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats["requests"]),
        ("a_register_row_is_not_a_policy",
         "Tier-3 IDENTITY and CLOSURE evidence. A permit carries no pet policy, admits nothing by itself and never "
         "outranks the property's own page."),
        ("hotel_naics", sorted(HOTEL_NAICS)),
        ("core_rows", len(all_rows)),
        ("core_active", len(active)),
        ("core_closed", len(closed)),
        ("core_active_by_naics", OrderedDict(Counter(r["naics_code"] for r in active).most_common())),
        ("core_closed_by_naics", OrderedDict(Counter(r["naics_code"] for r in closed).most_common())),
        ("hotel_active_rows", len(hotel_active)),
        ("hotel_active_in_admitted_postal_codes", len(admitted_hotel)),
        ("hotel_active_by_corridor", OrderedDict(sorted(Counter(r["corridor_slug"] for r in admitted_hotel).items()))),
        ("closed_hotel_rows_in_admitted_postal_codes", len(closed_hotel_admitted)),
        ("boundary_active_hotel_permits_by_future_market", OrderedDict(sorted(bnd.items()))),
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
              "closed_hotel_rows_in_admitted_postal_codes", "free_http_requests"):
        print("%-44s %s" % (k, rep[k]))
    print("active by naics:", dict(rep["core_active_by_naics"]))
    print("by corridor:", dict(rep["hotel_active_by_corridor"]))
    print("boundary:", dict(rep["boundary_active_hotel_permits_by_future_market"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
