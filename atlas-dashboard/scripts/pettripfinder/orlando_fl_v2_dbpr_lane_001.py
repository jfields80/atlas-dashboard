"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 9A: the Florida DBPR public-lodging REGISTRY lane.

The state of Florida licenses every public-lodging establishment through the Department of Business and
Professional Regulation. Its active-licence extracts (``hrlodge1.csv`` .. ``hrlodge7.csv``, published
unauthenticated on https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/) name the
licensed PREMISES: business name, location street, city, ZIP, county, rank code and the number of rental
units. That makes the registry the census backbone for Greater Orlando: a licensed HOTEL (rank HOTL) or MOTEL
(rank MOTL) at a street address inside an admitted postal code is a qualifying public-lodging identity
candidate on the state's own record, and every other rank is classified here rather than silently dropped.

THE RANK CODES, AND WHAT THIS ORDER DOES WITH EACH
-------------------------------------------------
  HOTL   hotel                      a census LEAD (tier 2 registry evidence)
  MOTL   motel                      a census LEAD
  TAPT   transient apartment        a census LEAD only when its own name reads as a hotel / suites /
                                    inn; otherwise APARTMENT (ordinary apartment communities, RV parks and
                                    single units dominate this class in Orlando)
  BNB    bed and breakfast          a census LEAD (a B&B operating as an inn is admissible on its own page)
  CNDO   resort condominium unit    VACATION_RENTAL / RESORT_RESIDENCE exclusion, counted per corridor --
                                    every unit is its own licence, never a hotel identity
  DWEL   resort / vacation dwelling VACATION_RENTAL exclusion (whole-home rentals), counted per corridor
  NAPT   non-transient apartment    APARTMENT exclusion, counted per corridor

A licence proposes an identity on the state's record of the premises; it does not decide one. The brand's own
page or the property's own site still binds a route, a brand property code and the policy.

Reuse: the parser is the shared ``discovery.fl_dbpr_registry`` adapter (PTF-DISCOVERY-P0-001), used
unchanged; this helper adds only the market filter and the rank accounting.

Inputs (downloaded by this order, gitignored, hashed here):
  data/orlando_fl_v2/dbpr/hrlodge1.csv .. hrlodge7.csv
Output:
  launch_packages/pettripfinder/markets/reports/orlando_fl_v2_dbpr_lane_001.json
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
from scripts.pettripfinder import orlando_fl_v2_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "orlando-fl"
SRC_DIR = os.path.join(_DASH, "data", "orlando_fl_v2", "dbpr")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports", "orlando_fl_v2_dbpr_lane_001.json")
SOURCE_PAGE = "https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/"
SOURCE_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/hrlodge%d.csv"
RETRIEVED_AT = "2026-09-15T14:12:00Z"

LEAD_RANKS = ("HOTL", "MOTL", "BNB")
EXCLUSION_RANKS = OrderedDict([
    ("CNDO", "VACATION_RENTAL_OR_RESORT_RESIDENCE -- a resort condominium unit licensed individually"),
    ("DWEL", "VACATION_RENTAL -- a resort / vacation dwelling (whole-home rental) licensed individually"),
    ("NAPT", "APARTMENT -- a non-transient apartment licence"),
])
_TAPT_HOTEL_NAME = re.compile(r"\b(hotel|suites|inn|lodge|motel|resort|studios)\b", re.I)
_TAPT_NOT_HOTEL = re.compile(r"\b(apartment|apartments|apt|apts|homes|living|village|collegiate|condo|rv|marina|"
                             r"fish camp|properties|investments|llc|unit|villa|str #|residences?)\b", re.I)

#: Counties the observation box reaches. A row in an admitted ZIP whose county is none of these is a data
#: error in the extract and is reported, never admitted.
OBSERVED_COUNTIES = {"Orange", "Osceola", "Seminole", "Lake", "Polk", "Volusia", "Brevard"}


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _clean(v):
    return " ".join((v or "").split())


#: Refused neighbours this lane OBSERVES row by row (the order's "careful evaluation" towns next to the admitted
#: corridors). The far refused markets -- Tampa, Daytona Beach, the Space Coast, Lakeland / Winter Haven, Ocala,
#: The Villages, Highlands County -- are named and refused by the geography but not enumerated here: their
#: licences are not Orlando leads, and listing them would count another market's inventory as discovered.
OBSERVED_OUTSIDE = ("Poinciana", "Haines City", "Mount Dora", "Groveland", "DeLand", "Kenansville", "Sanford north shore")


def observation_zips():
    admitted = {z for c in GEO.CORRIDORS for z in c[5]}
    outside = {z for m, _s, zs, _w in GEO.OUTSIDE if m.startswith(OBSERVED_OUTSIDE) for z in zs}
    return admitted, outside


def build():
    admitted, outside = observation_zips()
    files = []
    leads, tapt_refused = [], []
    exclusion_counts = OrderedDict()
    rank_counts_admitted = Counter()
    rank_counts_outside_named = Counter()
    adapter_checked = 0
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
            text, observed_at="2026-09-15", retrieved_at=RETRIEVED_AT,
            raw_pointer_prefix=SOURCE_URL % i, snapshot_hash="sha256:" + digest)
        obs_by_row = {}
        for o in obs:
            m = re.search(r"#row=(\d+)$", o["provenance"]["raw_pointer"])
            obs_by_row[int(m.group(1))] = o
        reader = csv.DictReader(io.StringIO(text))
        for n, row in enumerate(reader, start=1):
            z = "".join(ch for ch in (row.get(DBPR.COL_LOCATION_ZIP) or "") if ch.isdigit())[:5]
            in_adm, in_out = z in admitted, z in outside
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
                    tapt_refused.append(OrderedDict([("name", name), ("street", o.get("address", "")), ("postal_code", z),
                                                     ("units", units), ("why", "APARTMENT -- a transient-apartment licence "
                                                      "whose own name reads as an apartment community, RV park, unit or "
                                                      "investment entity, not a hotel")]))
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
                ("status_codes", "%s/%s" % (_clean(row.get("Primary Status Code")), _clean(row.get("Secondary Status Code")))),
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
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "9A -- Florida DBPR public-lodging licence registry"),
        ("source_page", SOURCE_PAGE),
        ("retrieved_at", RETRIEVED_AT),
        ("terms", "Published unauthenticated on the official state page under 'Public Records'; Florida public-lodging "
                  "licence records are public records (re-verified by PTF-DISCOVERY-P0-001). Bulk-file download, no crawl."),
        ("adapter", "scripts/pettripfinder/discovery/fl_dbpr_registry.py (shared, unchanged)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 7),
        ("files", files),
        ("a_licence_is_not_a_policy",
         "A DBPR licence is state identity and eligibility evidence for the licensed premises. It never carries or "
         "implies a pet policy."),
        ("rank_rule", OrderedDict([("leads", list(LEAD_RANKS) + ["TAPT (hotel-named only)"]),
                                   ("exclusions", EXCLUSION_RANKS)])),
        ("rank_counts_in_admitted_postal_codes", OrderedDict(sorted(rank_counts_admitted.items()))),
        ("rank_counts_in_named_outside_postal_codes", OrderedDict(sorted(rank_counts_outside_named.items()))),
        ("exclusions_by_corridor", OrderedDict((k, OrderedDict(sorted(v.items())))
                                               for k, v in sorted(exclusion_counts.items()))),
        ("exclusion_totals", OrderedDict((r, sum(v.get(r, 0) for v in exclusion_counts.values())) for r in EXCLUSION_RANKS)),
        ("tapt_refused_as_apartment", tapt_refused),
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
    print("by corridor:", dict(rep["leads_by_corridor"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
