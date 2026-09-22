"""PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 -- Phase 7A: the Florida DBPR public-lodging REGISTRY lane.

The state of Florida licenses every public-lodging establishment through the Department of Business and
Professional Regulation. Its active-licence extracts (``hrlodge1.csv`` .. ``hrlodge7.csv``, published
unauthenticated on https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/) name the
licensed PREMISES: business name, location street, city, ZIP, county, rank code and the number of rental units.
That makes the registry the census backbone for The Palm Beaches: a licensed HOTEL (rank HOTL) or MOTEL (rank
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

Palm Beach County's shape on the state's own record: 856 CNDO and 1,843 DWEL licences and 1,110 non-transient
apartments against just 194 hotel / motel / B&B licences. The county's lodging register is dominated by
individually licensed condominium and vacation-rental units -- PGA National's villas (33418 carries 315 lodging
licences and 2 hotel-rank), Wellington's equestrian-season rentals (33414: 230 and 2), Singer Island's and
Highland Beach's towers -- none of which is a hotel identity.

A licence proposes an identity on the state's record of the premises; it does not decide one. The brand's own
page or the property's own site still binds a route, a brand property code and the policy.

THE COUNTY LINES, COUNTED IN BOTH DIRECTIONS
---------------------------------------------
This lane is also the Phase 22 boundary audit. It counts, by county and city, every hotel-rank licence in the
counties this market borders -- Broward (the LIVE fort-lauderdale-fl market), Miami-Dade (the LIVE miami-fl
market), Martin and St. Lucie (future treasure-coast-fl) and Monroe (future florida-keys-fl) -- and reports how
many of each were ADMITTED here. Broward and Miami-Dade must be zero: those markets are live and already
publish that inventory. Martin is the one county where a non-zero count is expected and explained, because
postal code 33469 (Tequesta) crosses the line and this market's registry covers a shared postal code whole.

Reuse: the parser is the shared ``discovery.fl_dbpr_registry`` adapter (PTF-DISCOVERY-P0-001), used unchanged;
this helper adds only the market filter and the rank accounting.

Inputs (downloaded by this order, gitignored, hashed here):
  data/west_palm_beach_fl/dbpr/hrlodge1.csv .. hrlodge7.csv
Output:
  launch_packages/pettripfinder/markets/reports/west_palm_beach_fl_dbpr_lane_001.json
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
from scripts.pettripfinder import west_palm_beach_fl_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "west-palm-beach-fl"
SRC_DIR = os.path.join(_DASH, "data", "west_palm_beach_fl", "dbpr")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "west_palm_beach_fl_dbpr_lane_001.json")
SOURCE_PAGE = "https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/"
SOURCE_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/hrlodge%d.csv"
RETRIEVED_AT = "2026-09-22T14:22:00Z"
OBSERVED_AT = "2026-09-22"

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

#: Cities named individually in the county boundary audit; everything else in an observed county is "OTHER".
_BOUNDARY_CITIES = ("DEERFIELD BEACH", "POMPANO BEACH", "FORT LAUDERDALE", "HOLLYWOOD", "HALLANDALE BEACH",
                    "CORAL SPRINGS", "MIAMI", "MIAMI BEACH", "AVENTURA", "SUNNY ISLES BEACH", "HIALEAH",
                    "STUART", "HOBE SOUND", "JENSEN BEACH", "PALM CITY", "INDIANTOWN", "TEQUESTA", "JUPITER",
                    "PORT ST LUCIE", "PORT SAINT LUCIE", "FORT PIERCE",
                    "KEY LARGO", "ISLAMORADA", "KEY WEST", "MARATHON")


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
    boundary = OrderedDict()
    cross_county_admitted = []
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
            # --- the Phase 22 county boundary audit, counted before any admission decision ---
            if county in GEO.OBSERVED_COUNTIES and rank0 in LEAD_RANKS + ("TAPT",):
                b = boundary.setdefault(county, OrderedDict([
                    ("preserved_or_live_market", GEO.OBSERVED_COUNTIES[county]),
                    ("hotel_rank_licences", 0), ("by_city", Counter()), ("admitted_here", 0)]))
                b["hotel_rank_licences"] += 1
                city = _clean(row.get(DBPR.COL_LOCATION_CITY)).upper()
                b["by_city"][city if city in _BOUNDARY_CITIES else "OTHER"] += 1
                if in_adm:
                    # A licence whose COUNTY is not Palm Beach but whose own POSTAL CODE this registry claims.
                    # The postal code governs (see GEO.MARTIN_BORDER_RULE); the row is admitted and named here.
                    b["admitted_here"] += 1
                    cross_county_admitted.append(OrderedDict([
                        ("county", _clean(row.get("Location County"))),
                        ("license_number", _clean(row.get(DBPR.COL_LICENSE_NUMBER))),
                        ("rank_code", rank0),
                        ("name", _clean(row.get(DBPR.COL_BUSINESS_NAME))),
                        ("street", _clean(row.get(DBPR.COL_LOCATION_ADDRESS))),
                        ("city", _clean(row.get(DBPR.COL_LOCATION_CITY))),
                        ("postal_code", z),
                        ("why_admitted",
                         "Its OWN postal code %s is claimed by this market's corridor registry, which covers a "
                         "shared postal code WHOLE. The DBPR 'county' field is the licensing county, not the "
                         "premises' postal geography." % z),
                    ]))
            if county in GEO.OBSERVED_COUNTIES and not in_adm and z not in outside:
                continue
            if not (in_adm or in_out):
                continue
            rank = _clean(row.get(DBPR.COL_RANK_CODE))
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
                                "community, RV park, unit, stable or investment entity, not a hotel")]))
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
    live_market_admissions = sum(v["admitted_here"] for k, v in boundary.items()
                                 if GEO.OBSERVED_COUNTIES.get(k) in GEO.EXISTING_LIVE_MARKETS)
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "7A -- Florida DBPR public-lodging licence registry, and the Phase 22 county boundary audit"),
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
        ("rank_rule", OrderedDict([("leads", list(LEAD_RANKS) + ["TAPT (hotel-named only)"]),
                                   ("exclusions", EXCLUSION_RANKS)])),
        ("rank_counts_in_admitted_postal_codes", OrderedDict(sorted(rank_counts_admitted.items()))),
        ("rank_counts_in_named_outside_postal_codes", OrderedDict(sorted(rank_counts_outside_named.items()))),
        ("exclusions_by_corridor", OrderedDict((k, OrderedDict(sorted(v.items())))
                                               for k, v in sorted(exclusion_counts.items()))),
        ("exclusion_totals", OrderedDict((r, sum(v.get(r, 0) for v in exclusion_counts.values()))
                                         for r in EXCLUSION_RANKS)),
        ("tapt_refused_as_apartment", tapt_refused),
        ("county_boundary_audit", OrderedDict(
            (k, OrderedDict([("preserved_or_live_market", v["preserved_or_live_market"]),
                             ("hotel_rank_licences", v["hotel_rank_licences"]),
                             ("by_city", OrderedDict(sorted(v["by_city"].items()))),
                             ("admitted_into_west_palm_beach", v["admitted_here"])]))
            for k, v in sorted(boundary.items()))),
        ("cross_county_admitted_rows", cross_county_admitted),
        ("live_market_county_admissions", live_market_admissions),
        ("no_live_market_inventory_admitted", live_market_admissions == 0),
        ("martin_county_border_rule", GEO.MARTIN_BORDER_RULE),
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
    print("LIVE-market county admissions:", rep["live_market_county_admissions"],
          "(must be 0):", rep["no_live_market_inventory_admitted"])
    for k, v in rep["county_boundary_audit"].items():
        print("  %-12s %4d hotel-rank -> admitted here %d  (%s)" % (
            k, v["hotel_rank_licences"], v["admitted_into_west_palm_beach"], v["preserved_or_live_market"]))
    print("by corridor:", dict(rep["leads_by_corridor"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
