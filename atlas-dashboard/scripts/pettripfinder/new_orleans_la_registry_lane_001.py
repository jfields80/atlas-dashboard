"""PTF-NEW-ORLEANS-LA-HARDENED-SOURCE-READY-001 -- Phase 12: the Louisiana / New Orleans lodging-register lane, MEASURED.

WHAT WAS LOOKED FOR
-------------------
The order's census asks for "Louisiana/local lodging inventories" and "New Orleans public lodging/hotel inventories".
This lane measures whether Greater New Orleans has a PROPERTY-LEVEL public register -- a row per lodging premises
with its own street address -- in each parish, and reads the one that exists.

WHAT WAS MEASURED (2026-10-06, free, read-only)
-----------------------------------------------
  * CITY OF NEW ORLEANS (Orleans Parish) -- data.nola.gov iqay-p646, "Active Occupational Licenses" (the Bureau of
    Revenue's occupational licences, refreshed daily; Socrata). Each row is a licensed business premises with its
    trade name (``businessname``), the licensee (``ownername``), street, ZIP, telephone, NAICS business type, start
    date and a point. A REAL property-level register. The four LODGING types are read once in full (one request) --
    "Hotels(except Casino Hotels) & Motels" (294), "Bed & Breakfast Inns" (112), "Casino Hotels" (2) and "Traveler
    Accommodation, All Other" (3) -- and persisted by sha256 under data/new_orleans_la/registry/. "Rooming & Boarding
    Houses" (12) and "Short Term Rentals/Residential Properties" (5) are MEASURED, NOT READ: neither is public hotel
    lodging.
  * data.nola.gov ns2v-hzec "Hotels Motels BBs" (391 rows, last updated 2024-07-16) -- an older extract of the same
    licences; measured, superseded by the current licence list.
  * data.nola.gov ufdg-ajws "Active Short-Term Rental Licenses" (4,320 rows: commercial / non-commercial STR owners and
    operators, and "Lodging Exempt from STR Regulation") -- persisted as EXCLUSION EVIDENCE ONLY: an address that
    holds a short-term-rental licence and no lodging occupational licence is a short-term rental, never an inn. It is
    never a lead.
  * JEFFERSON / ST. BERNARD / PLAQUEMINES PARISH -- no open property-level lodging register: the Socrata catalog
    carries no dataset for any of them, and the Louisiana Department of Health publishes no bulk lodging list. Those
    parishes are built from the independent lanes (OpenStreetMap, the brands' own inventories, the bureaus, Places,
    the property pages and the competitor challenge).

A REGISTER ROW IS A LEAD, NOT A HOTEL
-------------------------------------
Tier 3 identity evidence. Its trade name is the licensee's filing (sometimes a DBA, sometimes an LLC), its
telephone is carried as metadata and NEVER as a merge key (a management company's office number can cover many
properties), and it never carries a pet policy. A licence row decides no membership: the census decides by postal
code, and the property's own page outranks it. A licence row whose trade name is empty carries the licensee name and
says so.

Output:
  launch_packages/pettripfinder/markets/reports/new_orleans_la_registry_lane_001.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import new_orleans_la_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-NEW-ORLEANS-LA-HARDENED-SOURCE-READY-001"
MARKET_ID = "new-orleans-la"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "new_orleans_la_registry_lane_001.json")
SNAPSHOT = os.path.join(_DASH, "data", "new_orleans_la", "registry", "nola_lodging_licenses_iqay-p646.json")
STR_SNAPSHOT = os.path.join(_DASH, "data", "new_orleans_la", "registry", "nola_str_licenses_ufdg-ajws.json")
SOURCE_URL = ("https://data.nola.gov/resource/iqay-p646.json?$limit=5000&$where=businesstype in('Hotels(except "
              "Casino Hotels) & Motels','Bed & Breakfast Inns','Casino Hotels','Traveler Accommodation, All Other')"
              "&$order=businesslicensenumber")
STR_SOURCE_URL = "https://data.nola.gov/resource/ufdg-ajws.json?$limit=10000&$order=license_number"
DATASET_PAGE = "https://data.nola.gov/d/iqay-p646"
LEAD_PREFIXES = ("700", "701")

#: (portal, query or dataset, what answered, verdict)
MEASUREMENTS = [
    ("data.nola.gov (Socrata) iqay-p646", "Active Occupational Licenses, lodging business types",
     "411 rows: 294 hotels & motels, 112 bed & breakfast inns, 2 casino hotels, 3 other traveler accommodation; "
     "trade name, licensee, street, ZIP, phone, NAICS type, start date, point",
     "READ -- a property-level register for Orleans Parish; every row is a lead"),
    ("data.nola.gov (Socrata) iqay-p646", "business types Rooming & Boarding Houses (12), Short Term "
     "Rentals/Residential Properties (5), RV Parks & Campgrounds (8)", "counted",
     "MEASURED, NOT READ -- not public hotel lodging"),
    ("data.nola.gov (Socrata) ns2v-hzec", "Hotels Motels BBs", "391 rows, last updated 2024-07-16",
     "MEASURED, NOT READ -- an older extract of the same licences"),
    ("data.nola.gov (Socrata) ufdg-ajws", "Active Short-Term Rental Licenses, $limit=10000",
     "4,320 rows: STR operators / commercial owners / non-commercial and 'Lodging Exempt from STR Regulation'",
     "READ AS EXCLUSION EVIDENCE ONLY -- an STR licence marks a short-term rental, never an inn; never a lead"),
    ("Socrata catalog (all domains)", "q=occupational license / lodging / hotel, Jefferson / St. Bernard / "
     "Plaquemines", "no parish dataset", "NO OPEN JEFFERSON / ST. BERNARD / PLAQUEMINES REGISTER"),
    ("data.louisiana.gov", "domain lookup", "'Domain not found'",
     "no statewide Louisiana open-data register; the LDH publishes no bulk lodging list"),
]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _street(r):
    """The licence's own premises street. ``businessaddress`` is the licence's full street as filed (the parsed
    streetname / streetsuffix columns drop words: '2031 ST. CHARLES' parses to '2031 ST.', '10100 I 10 SERVICE RD' to
    '10100 10 SERVICE RD'); a trailing unit or building letter ('830 CONTI ST B', '3819 PATTERSON ST BLDG C') is a
    designator inside the premises and is dropped; a post-office box is no premises at all."""
    import re
    addr = " ".join((r.get("businessaddress") or "").split())
    if re.match(r"^p\.?\s*o\.?\s*box\b", addr, re.I):
        return ""
    addr = re.sub(r"\s+(?:bldg|building|ste|suite|unit|apt)\s*#?\s*[a-z0-9-]+$", "", addr, flags=re.I)
    addr = re.sub(r"\b(st|ave|rd|blvd|dr|pl|pkwy|hwy|ct|ln|way)\s+[a-z]$", r"\1", addr, flags=re.I)
    return addr


def str_licence_addresses():
    """Normalised (house number, street name, ZIP5) of every active short-term-rental licence: exclusion evidence."""
    import re
    with open(STR_SNAPSHOT, encoding="utf-8") as fh:
        rows = json.load(fh)
    out = {}
    for r in rows:
        addr = " ".join((r.get("address") or "").lower().replace(".", " ").replace(",", " ").split())
        m = re.match(r"^(\d+)[a-z]?\s+(.*)$", addr)
        if not m:
            continue
        out.setdefault((m.group(1), m.group(2)), []).append(OrderedDict([
            ("license_number", r.get("license_number")), ("license_type", r.get("license_type")),
            ("residential_subtype", r.get("residential_subtype")), ("address", r.get("address")),
        ]))
    return out


def build():
    with open(SNAPSHOT, encoding="utf-8") as fh:
        rows = json.load(fh)
    sha = _sha256(SNAPSHOT)
    leads, by_corridor, refused_future, by_type = [], Counter(), Counter(), Counter()
    in_admitted = refused = 0
    for r in rows:
        z = (r.get("zip") or "").strip()[:5]
        by_type[r.get("businesstype")] += 1
        if not z.startswith(LEAD_PREFIXES):
            refused += 1
            refused_future[GEO.future_market_for(z) or "(none)"] += 1
            continue
        _klass, slug, _why = GEO.classify_postal(z, r.get("city") or "")
        if slug:
            in_admitted += 1
            by_corridor[slug] += 1
        else:
            refused += 1
            refused_future[GEO.future_market_for(z) or "(none)"] += 1
        trade = (r.get("businessname") or "").strip()
        geom = (r.get("the_geom") or {}).get("coordinates") or [None, None]
        leads.append(OrderedDict([
            ("business_name", trade or (r.get("ownername") or "").strip()),
            ("name_is_licensee", not bool(trade)),
            ("licensee_name", (r.get("ownername") or "").strip()),
            ("street", _street(r)),
            ("city", (r.get("city") or "").strip()),
            ("state", (r.get("state") or "").strip()),
            ("postal_code", z),
            ("phone", (r.get("businessphone") or "").strip()),
            ("lat", geom[1]), ("lng", geom[0]),
            ("county_code", "Orleans"),
            ("license_number", r.get("businesslicensenumber")),
            ("rank_code", r.get("businesstype")),
            ("business_start_date", (r.get("businessstartdate") or "")[:10]),
            ("raw_pointer", "%s#license=%s" % (DATASET_PAGE, r.get("businesslicensenumber"))),
            ("snapshot_sha256", sha),
            ("corridor", slug or ""),
        ]))
    with open(STR_SNAPSHOT, encoding="utf-8") as fh:
        str_rows = json.load(fh)
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "12 -- the Louisiana / New Orleans lodging-register lane: MEASURED; Orleans Parish READ, Jefferson "
                  "/ St. Bernard / Plaquemines NONE OPEN"),
        ("register_exists", True),
        ("register_exists_by_parish", OrderedDict([("Orleans", True), ("Jefferson", False), ("St. Bernard", False),
                                                   ("Plaquemines", False)])),
        ("measured_on", "2026-10-06"),
        ("measurements", [OrderedDict([("portal", p), ("query", q), ("answered", a), ("verdict", w)])
                          for p, q, a, w in MEASUREMENTS]),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 14),
        ("snapshot", OrderedDict([
            ("source_url", SOURCE_URL), ("dataset_page", DATASET_PAGE),
            ("local_file", os.path.relpath(SNAPSHOT, _DASH).replace(os.sep, "/")), ("sha256", sha),
            ("rows_read", len(rows)),
            ("rows_by_business_type", OrderedDict(sorted((str(k), v) for k, v in by_type.items()))),
            ("an_occupational_licence_is_not_an_operating_proof",
             "a licence row says a business holds a licence at a premises; the property's own page decides whether "
             "it operates as public lodging today"),
        ])),
        ("str_exclusion_snapshot", OrderedDict([
            ("source_url", STR_SOURCE_URL),
            ("local_file", os.path.relpath(STR_SNAPSHOT, _DASH).replace(os.sep, "/")),
            ("sha256", _sha256(STR_SNAPSHOT)), ("rows", len(str_rows)),
            ("rows_by_license_type", OrderedDict(sorted(Counter(str(r.get("license_type"))
                                                                for r in str_rows).items()))),
            ("use", "EXCLUSION EVIDENCE ONLY: never a lead, never a policy"),
        ])),
        ("a_register_row_is_a_lead", "Tier 3 identity evidence: never a policy, never membership; its telephone is "
                                     "metadata, never a merge key."),
        ("lead_prefixes", list(LEAD_PREFIXES)),
        ("accommodation_rows", len(rows)),
        ("lead_rows", len(leads)),
        ("leads_in_admitted_postal_codes", in_admitted),
        ("leads_by_corridor", OrderedDict(sorted(by_corridor.items()))),
        ("leads_refused_by_their_own_postal_code", refused),
        ("leads_refused_by_future_market", OrderedDict(sorted(refused_future.items()))),
        ("leads", leads),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("register_exists=%s leads=%d in_admitted=%d refused=%d" % (
        dict(rep["register_exists_by_parish"]), rep["lead_rows"], rep["leads_in_admitted_postal_codes"],
        rep["leads_refused_by_their_own_postal_code"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
