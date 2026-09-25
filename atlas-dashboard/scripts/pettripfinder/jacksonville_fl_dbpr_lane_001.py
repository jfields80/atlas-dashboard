"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phase 9A: the Florida DBPR public-lodging REGISTRY lane.

The state of Florida licenses every public-lodging establishment through the Department of Business and
Professional Regulation. Its active-licence extracts (``hrlodge1.csv`` .. ``hrlodge7.csv``, published
unauthenticated on https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/) name the
licensed PREMISES: business name, location street, city, ZIP, county, rank code and the number of rental units.
That makes the registry the census backbone for Northeast Florida: a licensed HOTEL (rank HOTL) or MOTEL (rank
MOTL) at a street address inside an admitted postal code is a qualifying public-lodging identity candidate on
the state's own record, and every other rank is classified here rather than silently dropped.

THE RANK CODES, AND WHAT THIS ORDER DOES WITH EACH
-------------------------------------------------
  HOTL   hotel                      a census LEAD (tier 2 registry evidence)
  MOTL   motel                      a census LEAD
  TAPT   transient apartment        a census LEAD only when its own name reads as a hotel / suites / inn;
                                    otherwise APARTMENT
  BNB    bed and breakfast          a census LEAD (a B&B operating as an inn is admissible on its own page)
  CNDO   resort condominium unit    VACATION_RENTAL / RESORT_RESIDENCE exclusion, counted per corridor --
                                    every unit is its own licence, never a hotel identity
  DWEL   resort / vacation dwelling VACATION_RENTAL exclusion (whole-home rentals), counted per corridor
  NAPT   non-transient apartment    APARTMENT exclusion, counted per corridor

Northeast Florida's shape on the state's own record is the reason Phase 7's resort / condo safety rule matters
here as much as it did in Palm Beach County. NASSAU COUNTY carries 1,130 resort-condominium licences against 32
hotel-rank ones -- Amelia Island Plantation and the Omni resort villa programmes, individually licensed unit by
unit. ST. JOHNS COUNTY carries 1,472 CNDO and 2,139 DWEL licences (overwhelmingly in the refused St. Augustine
codes). DUVAL itself carries 1,268 vacation dwellings and 834 non-transient apartments against 193 hotel-rank
licences. None of that inventory is a hotel identity and none of it enters the graph.

A licence proposes an identity on the state's record of the premises; it does not decide one. The brand's own
page or the property's own site still binds a route, a brand property code and the policy. AND A LICENSEE NAME
IS NOT A HOTEL NAME -- the West Palm Beach identity correction (PTF-WEST-PALM-BEACH-FL-PREDEPLOY-IDENTITY-
CORRECTION-004) proved that a DBPR record whose Business Name equals its Licensee Name carries a LICENSEE
identity, never a trade name; that rule is applied by the census reconciliation lane, which sees both fields
this lane records.

THE FOUR-COUNTY AUDIT, AND WHY IT IS NOT A SINGLE LINE
------------------------------------------------------
Unlike every prior Florida market, this one has no single home county. Four are evaluated and three of them are
SPLIT, so this lane counts, for every county it touches, how many hotel-rank licences the state records and how
many this market's registry ADMITTED:

  DUVAL       admitted whole (the consolidated city-county).
  CLAY        split -- Orange Park / Fleming Island / Middleburg / Green Cove Springs / Oakleaf admitted;
              Keystone Heights refused by name.
  NASSAU      admitted, split by tier -- Amelia Island / Fernandina Beach at CORRIDOR, mainland at FRINGE.
  ST. JOHNS   split hardest -- Ponte Vedra Beach (32082), Nocatee (32081) and Fruit Cove (32259) admitted;
              EVERY St. Augustine code refused and reserved for a future standalone market.

and, by county, the neighbours it refuses entirely: Baker, Putnam, Flagler, Volusia, Alachua. Georgia's Camden,
Glynn and Chatham counties cannot appear in a Florida extract at all, which is itself the reason the Georgia
line is a state-code refusal rather than a county one.

The audit is also reported CITY BY CITY for the four places the order names individually -- St. Augustine,
St. Augustine Beach, World Golf Village and Palm Coast -- because a county count would hide them.

Reuse: the parser is the shared ``discovery.fl_dbpr_registry`` adapter (PTF-DISCOVERY-P0-001), used unchanged;
this helper adds only the market filter and the rank accounting.

Inputs (downloaded by this order, gitignored, hashed here):
  data/jacksonville_fl/dbpr/hrlodge1.csv .. hrlodge7.csv
Output:
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_dbpr_lane_001.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.discovery import fl_dbpr_registry as DBPR  # noqa: E402
from scripts.pettripfinder import jacksonville_fl_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
SRC_DIR = os.path.join(_DASH, "data", "jacksonville_fl", "dbpr")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "jacksonville_fl_dbpr_lane_001.json")
SOURCE_PAGE = "https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/"
SOURCE_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/hrlodge%d.csv"
RETRIEVED_AT = "2026-09-25T01:02:00Z"
OBSERVED_AT = "2026-09-25"

LEAD_RANKS = ("HOTL", "MOTL", "BNB")
EXCLUSION_RANKS = OrderedDict([
    ("CNDO", "VACATION_RENTAL_OR_RESORT_RESIDENCE -- a resort condominium unit licensed individually"),
    ("DWEL", "VACATION_RENTAL -- a resort / vacation dwelling (whole-home rental) licensed individually"),
    ("NAPT", "APARTMENT -- a non-transient apartment licence"),
])
_TAPT_HOTEL_NAME = re.compile(r"\b(hotel|suites|inn|lodge|motel|resort|studios)\b", re.I)
_TAPT_NOT_HOTEL = re.compile(r"\b(apartment|apartments|apt|apts|homes|living|village|collegiate|condo|rv|marina|"
                             r"fish camp|properties|investments|llc|unit|villa|str #|residences?|"
                             r"stables?|equestrian|farms?)\b", re.I)

#: Counties whose licences this market's registry may admit (each one SPLIT except Duval -- see GEO).
HOME_COUNTIES = OrderedDict([
    ("duval", "ADMITTED WHOLE -- the consolidated city-county"),
    ("clay", "SPLIT -- Orange Park / Fleming Island / Middleburg / Green Cove Springs / Oakleaf admitted, "
             "Keystone Heights refused by name"),
    ("nassau", "ADMITTED, SPLIT BY TIER -- Amelia Island / Fernandina Beach CORRIDOR, mainland FRINGE"),
    ("st. johns", "SPLIT HARDEST -- Ponte Vedra Beach 32082, Nocatee 32081 and Fruit Cove 32259 admitted; every "
                  "St. Augustine code refused and reserved for future st-augustine-fl"),
])

#: Cities named individually in the boundary audit, because a county count would hide them.
_BOUNDARY_CITIES = ("JACKSONVILLE", "JACKSONVILLE BEACH", "JACKSONVILLE BCH", "ATLANTIC BEACH", "NEPTUNE BEACH",
                    "BALDWIN", "PONTE VEDRA BEACH", "SAINT JOHNS", "ST JOHNS",
                    "ORANGE PARK", "FLEMING ISLAND", "MIDDLEBURG", "GREEN COVE SPRINGS", "KEYSTONE HEIGHTS",
                    "FERNANDINA BEACH", "AMELIA ISLAND", "YULEE", "CALLAHAN", "HILLIARD",
                    "SAINT AUGUSTINE", "ST AUGUSTINE", "ST. AUGUSTINE", "ST AUGUSTINE BCH",
                    "SAINT AUGUSTINE BEACH", "ST AUGUSTINE BEACH", "ELKTON", "HASTINGS",
                    "PALM COAST", "FLAGLER BEACH", "FLAGLER BCH", "BUNNELL",
                    "GAINESVILLE", "ALACHUA", "DAYTONA BEACH", "ORMOND BEACH", "DELAND",
                    "PALATKA", "EAST PALATKA", "E PALATKA", "CRESCENT CITY", "MACCLENNY", "GLEN ST MARY")

#: The four places the order asks about by NAME, and the DBPR Location City spellings each one appears under.
NAMED_PLACE_AUDIT = OrderedDict([
    ("ST AUGUSTINE", ("SAINT AUGUSTINE", "ST AUGUSTINE", "ST. AUGUSTINE")),
    ("ST AUGUSTINE BEACH", ("ST AUGUSTINE BCH", "SAINT AUGUSTINE BEACH", "ST AUGUSTINE BEACH",
                            "ST. AUGUSTINE BEACH")),
    ("PALM COAST", ("PALM COAST",)),
    ("GAINESVILLE", ("GAINESVILLE",)),
])
#: World Golf Village has no postal city of its own -- it is Saint Augustine 32092. Audited by postal code.
NAMED_ZIP_AUDIT = OrderedDict([
    ("WORLD GOLF VILLAGE (32092)", ("32092",)),
    ("ST AUGUSTINE BEACH (32080)", ("32080",)),
    ("KEYSTONE HEIGHTS (32656)", ("32656",)),
])


def _clean(v):
    return " ".join((v or "").split())


def observation_zips():
    admitted = {z for c in GEO.CORRIDORS for z in c[5]}
    outside = {z for _m, _s, zs, _w in GEO.OUTSIDE for z in zs}
    return admitted, outside


def build():
    admitted, outside = observation_zips()
    files = []
    leads, tapt_refused = [], []
    exclusion_counts = OrderedDict()
    rank_counts_admitted = Counter()
    rank_counts_outside_named = Counter()
    adapter_checked = 0
    county_audit = OrderedDict()
    named_place = OrderedDict((k, OrderedDict([("discovered_hotel_rank", 0), ("admitted", 0)]))
                              for k in list(NAMED_PLACE_AUDIT) + list(NAMED_ZIP_AUDIT))
    cross_county_admitted = []
    audited_counties = list(HOME_COUNTIES) + list(GEO.OBSERVED_COUNTIES)
    for i in range(1, 8):
        path = os.path.join(SRC_DIR, "hrlodge%d.csv" % i)
        raw = open(path, "rb").read()
        text = raw.decode("latin-1")
        digest = hashlib.sha256(raw).hexdigest()
        files.append(OrderedDict([("file", "hrlodge%d.csv" % i), ("url", SOURCE_URL % i), ("bytes", len(raw)),
                                  ("sha256", digest)]))
        # The shared adapter, unchanged, over the same bytes: its observation for a row is what binds the
        # row's pointer, name, address, ZIP and phone; the raw row adds only rank, units and county.
        obs, _skipped = DBPR.parse_hrlodge_csv(
            text, observed_at=OBSERVED_AT, retrieved_at=RETRIEVED_AT,
            raw_pointer_prefix=SOURCE_URL % i, snapshot_hash="sha256:" + digest)
        obs_by_row = {}
        for o in obs:
            m = re.search(r"#row=(\d+)$", o["provenance"]["raw_pointer"])
            obs_by_row[int(m.group(1))] = o
        reader = csv.DictReader(io.StringIO(text))
        for n, row in enumerate(reader, start=1):
            z = "".join(ch for ch in (row.get(DBPR.COL_LOCATION_ZIP) or "") if ch.isdigit())[:5]
            county = _clean(row.get("Location County")).lower()
            rank0 = _clean(row.get(DBPR.COL_RANK_CODE))
            in_adm, in_out = z in admitted, z in outside
            city = _clean(row.get(DBPR.COL_LOCATION_CITY)).upper()
            # --- the county boundary audit, counted BEFORE any admission decision ---
            if county in audited_counties and rank0 in LEAD_RANKS + ("TAPT",):
                b = county_audit.setdefault(county, OrderedDict([
                    ("role", HOME_COUNTIES.get(county, "OUTSIDE by name")),
                    ("preserved_or_live_market", GEO.OBSERVED_COUNTIES.get(county, "(home county)")),
                    ("hotel_rank_licences", 0), ("by_city", Counter()), ("admitted_here", 0)]))
                b["hotel_rank_licences"] += 1
                b["by_city"][city if city in _BOUNDARY_CITIES else "OTHER"] += 1
                if in_adm:
                    b["admitted_here"] += 1
                    if county not in HOME_COUNTIES:
                        # A licence whose COUNTY no corridor claims but whose own POSTAL CODE this registry
                        # covers. The postal code governs; the row is admitted and named here.
                        cross_county_admitted.append(OrderedDict([
                            ("county", _clean(row.get("Location County"))),
                            ("license_number", _clean(row.get(DBPR.COL_LICENSE_NUMBER))),
                            ("rank_code", rank0),
                            ("name", _clean(row.get(DBPR.COL_BUSINESS_NAME))),
                            ("street", _clean(row.get(DBPR.COL_LOCATION_ADDRESS))),
                            ("city", _clean(row.get(DBPR.COL_LOCATION_CITY))),
                            ("postal_code", z),
                            ("why_admitted",
                             "Its OWN postal code %s is claimed by this market's corridor registry, which covers "
                             "a shared postal code WHOLE. The DBPR 'county' field is the licensing county, not "
                             "the premises' postal geography." % z),
                        ]))
            # --- the named-place audit the order asks for by name ---
            if rank0 in LEAD_RANKS + ("TAPT",):
                for label, spellings in NAMED_PLACE_AUDIT.items():
                    if city in spellings:
                        named_place[label]["discovered_hotel_rank"] += 1
                        if in_adm:
                            named_place[label]["admitted"] += 1
                for label, zips in NAMED_ZIP_AUDIT.items():
                    if z in zips:
                        named_place[label]["discovered_hotel_rank"] += 1
                        if in_adm:
                            named_place[label]["admitted"] += 1
            if not (in_adm or in_out):
                continue
            rank = rank0
            (rank_counts_admitted if in_adm else rank_counts_outside_named)[rank] += 1
            klass, slug, _why = GEO.classify_postal(z, row.get(DBPR.COL_LOCATION_CITY))
            if rank in EXCLUSION_RANKS:
                if in_adm:
                    exclusion_counts.setdefault(slug, Counter())[rank] += 1
                continue
            o = obs_by_row.get(n)
            if o is None:
                continue
            adapter_checked += 1
            units = _clean(row.get("Number of Seats or Rental Units"))
            name = o["name"]
            if rank == "TAPT":
                if not (_TAPT_HOTEL_NAME.search(name) and not _TAPT_NOT_HOTEL.search(name)):
                    tapt_refused.append(OrderedDict([
                        ("name", name), ("street", o.get("address", "")), ("postal_code", z), ("units", units),
                        ("why", "APARTMENT -- a transient-apartment licence whose own name reads as an apartment "
                                "community, RV park, unit or investment entity, not a hotel")]))
                    continue
            elif rank not in LEAD_RANKS:
                continue
            leads.append(OrderedDict([
                ("lane", "REGISTRY_FL_DBPR"),
                ("license_number", _clean(row.get(DBPR.COL_LICENSE_NUMBER))),
                ("property_code", o["property_code"]),
                ("rank_code", rank),
                ("name", name),
                ("business_name", _clean(row.get(DBPR.COL_BUSINESS_NAME))),
                ("licensee_name", _clean(row.get(DBPR.COL_LICENSEE_NAME))),
                ("street", o.get("address", "")),
                ("city", o.get("city", "")),
                ("state", o.get("state", "")),
                ("postal_code", o.get("zip", "")),
                ("phone", o.get("phone", "")),
                ("county", _clean(row.get("Location County"))),
                ("rental_units", int(units) if units.isdigit() else None),
                ("status_codes", "%s/%s" % (_clean(row.get("Primary Status Code")),
                                            _clean(row.get("Secondary Status Code")))),
                ("last_inspection_date", _clean(row.get("Last Inspection Date"))),
                ("admitted_postal_code", in_adm),
                ("geography_class", klass),
                ("corridor_slug", slug),
                ("raw_pointer", o["provenance"]["raw_pointer"]),
                ("snapshot_sha256", digest),
                ("adapter_warnings", [w["code"] for w in o.get("warnings", [])]),
            ]))
    leads.sort(key=lambda r: (r["postal_code"], r["street"], r["name"]))
    by_corridor = Counter(r["corridor_slug"] for r in leads if r["admitted_postal_code"])
    live_market_admissions = sum(v["admitted_here"] for k, v in county_audit.items()
                                 if GEO.OBSERVED_COUNTIES.get(k) in GEO.EXISTING_LIVE_MARKETS)
    refused_county_admissions = sum(v["admitted_here"] for k, v in county_audit.items()
                                    if k not in HOME_COUNTIES)
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "9A -- Florida DBPR public-lodging licence registry, and the Phase 4 / Phase 24 county and "
                  "named-place boundary audit"),
        ("source_page", SOURCE_PAGE),
        ("retrieved_at", RETRIEVED_AT),
        ("terms", "Published unauthenticated on the official state page under 'Public Records'; Florida "
                  "public-lodging licence records are public records (re-verified by PTF-DISCOVERY-P0-001). "
                  "Bulk-file download, no crawl."),
        ("adapter", "scripts/pettripfinder/discovery/fl_dbpr_registry.py (shared, unchanged)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 7),
        ("files", files),
        ("a_licence_is_not_a_policy",
         "A DBPR licence is state identity and eligibility evidence for the licensed premises. It never carries "
         "or implies a pet policy."),
        ("a_licensee_name_is_not_a_hotel_name",
         "Both Business Name and Licensee Name are recorded on every lead so the census lane can apply the West "
         "Palm Beach identity-correction rule: a record whose Business Name EQUALS its Licensee Name carries a "
         "LICENSEE identity, never a hotel trade name, and the longer string never wins on length alone."),
        ("dbpr_does_not_decide_geography",
         "A licence's county and city are the LICENSING record. Admission is decided by the property's own "
         "postal code against the corridor registry, and nothing else. This lane reports both so the two can be "
         "compared, which is exactly how the four-county split is audited."),
        ("rank_rule", OrderedDict([("leads", list(LEAD_RANKS) + ["TAPT (hotel-named only)"]),
                                   ("exclusions", EXCLUSION_RANKS)])),
        ("rank_counts_in_admitted_postal_codes", OrderedDict(sorted(rank_counts_admitted.items()))),
        ("rank_counts_in_named_outside_postal_codes", OrderedDict(sorted(rank_counts_outside_named.items()))),
        ("exclusions_by_corridor", OrderedDict((k, OrderedDict(sorted(v.items())))
                                               for k, v in sorted(exclusion_counts.items()))),
        ("exclusion_totals", OrderedDict((r, sum(v.get(r, 0) for v in exclusion_counts.values()))
                                         for r in EXCLUSION_RANKS)),
        ("tapt_refused_as_apartment", tapt_refused),
        ("home_counties", HOME_COUNTIES),
        ("county_boundary_audit", OrderedDict(
            (k, OrderedDict([("role", v["role"]),
                             ("preserved_or_live_market", v["preserved_or_live_market"]),
                             ("hotel_rank_licences_discovered", v["hotel_rank_licences"]),
                             ("by_city", OrderedDict(sorted(v["by_city"].items()))),
                             ("admitted_into_jacksonville_fl", v["admitted_here"])]))
            for k, v in sorted(county_audit.items()))),
        ("named_place_audit", named_place),
        ("cross_county_admitted_rows", cross_county_admitted),
        ("refused_county_admissions", refused_county_admissions),
        ("no_refused_county_inventory_admitted", refused_county_admissions == 0),
        ("live_market_county_admissions", live_market_admissions),
        ("no_live_market_inventory_admitted", live_market_admissions == 0),
        ("county_boundary_rules", GEO.COUNTY_BOUNDARY_RULES),
        ("lead_count", len(leads)),
        ("lead_count_admitted_postal_codes", sum(1 for r in leads if r["admitted_postal_code"])),
        ("lead_count_named_outside_postal_codes", sum(1 for r in leads if not r["admitted_postal_code"])),
        ("leads_by_rank", OrderedDict(sorted(Counter(r["rank_code"] for r in leads).items()))),
        ("leads_by_corridor", OrderedDict(sorted(by_corridor.items()))),
        ("adapter_rows_bound", adapter_checked),
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
    print("leads:", rep["lead_count"], "admitted:", rep["lead_count_admitted_postal_codes"], "outside-named:",
          rep["lead_count_named_outside_postal_codes"])
    print("by rank:", dict(rep["leads_by_rank"]))
    print("exclusions:", dict(rep["exclusion_totals"]), "tapt refused:", len(rep["tapt_refused_as_apartment"]))
    print("refused-county admissions:", rep["refused_county_admissions"],
          "(must be 0):", rep["no_refused_county_inventory_admitted"])
    for k, v in rep["county_boundary_audit"].items():
        print("  %-12s %5d hotel-rank discovered -> admitted %4d  (%s)" % (
            k, v["hotel_rank_licences_discovered"], v["admitted_into_jacksonville_fl"], v["role"][:46]))
    print("named places:")
    for k, v in rep["named_place_audit"].items():
        print("  %-28s discovered %4d  admitted %d" % (k, v["discovered_hotel_rank"], v["admitted"]))
    print("by corridor:", dict(rep["leads_by_corridor"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
