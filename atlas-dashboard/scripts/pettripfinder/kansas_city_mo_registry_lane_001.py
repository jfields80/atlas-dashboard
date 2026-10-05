"""PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001 -- Phase 10: the Missouri / Kansas lodging-register lane, MEASURED.

WHAT WAS LOOKED FOR
-------------------
The order's census asks for "Missouri/local lodging inventories" and "Kansas/local lodging inventories". Seattle had
one (the City's business-licence certificates with NAICS codes); the Twin Cities had none. This lane measures whether
Kansas City has a PROPERTY-LEVEL public register -- a row per lodging premises with its own street address -- on each
side of the state line, and reads the one that exists.

WHAT WAS MEASURED (2026-10-05, free, read-only)
-----------------------------------------------
  * MISSOURI -- data.mo.gov dataset 7ac3-k2di, "Missouri Licensed Lodging Establishment List" (the Department of
    Health and Senior Services' lodging licensing; Socrata, 1,470 rows statewide): establishment name, street, city,
    ZIP, telephone, county and an approval code. A REAL property-level register. Read once in full (one request),
    persisted by sha256 under data/kansas_city_mo/registry/. 185 rows sit in this market's admitted Missouri codes.
    The approval code is an inspection status, not an operating status (operating chain hotels carry NA and blank
    codes), so every row is a LEAD whatever its code, and the code is carried for the record.
  * KANSAS CITY, MISSOURI -- data.kcmo.org pnm4-68wg, "Business License Holders": 31 rows typed "Hotels (except Casino
    Hotels) and Motels" / "All Other Traveler Accommodation" -- a licence-holder list (often the operating company),
    fully overlapped by the state register. Measured, not read as a lane.
  * KANSAS -- the Kansas Department of Agriculture licenses lodging establishments (K.S.A. 36-502) but publishes no
    open register: its lodging licence page answered this plain client 403, and the Socrata catalog carries no
    Kansas lodging dataset. NO PROPERTY-LEVEL KANSAS REGISTER is read; the Kansas side is built from the
    independent lanes (OpenStreetMap's Kansas extract, the brands' own inventories, the bureaus, Places, the
    property pages and the competitor challenge).

A REGISTER ROW IS A LEAD, NOT A HOTEL
-------------------------------------
Tier 3 identity evidence. Its name is the licensee's filing (sometimes a DBA, an LLC or a winery), its telephone is
carried as metadata and NEVER as a merge key (a management company's office number can cover many properties), and
it never carries a pet policy. A licence row decides no membership: the census decides by postal code, and the
property's own page outranks it.

SCOPE OF THE LEADS
------------------
Every Missouri row under the prefixes 640-658 -- the Kansas City region and the refused Missouri neighbours inside
the observation box (St. Joseph, Columbia, the Lake of the Ozarks, Springfield) -- so the boundary audit counts them.
The St. Louis prefixes (630-633, the live st-louis-mo market) and south-east / north-east Missouri are not leads.

Output:
  launch_packages/pettripfinder/markets/reports/kansas_city_mo_registry_lane_001.json
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

from scripts.pettripfinder import kansas_city_mo_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001"
MARKET_ID = "kansas-city-mo"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "kansas_city_mo_registry_lane_001.json")
SNAPSHOT = os.path.join(_DASH, "data", "kansas_city_mo", "registry", "mo_lodging_7ac3-k2di.json")
SOURCE_URL = "https://data.mo.gov/resource/7ac3-k2di.json?$limit=5000"
DATASET_PAGE = "https://data.mo.gov/d/7ac3-k2di"
LEAD_PREFIXES = tuple("%03d" % p for p in range(640, 659))

#: (portal, query or dataset, what answered, verdict)
MEASUREMENTS = [
    ("data.mo.gov (Socrata) 7ac3-k2di", "Missouri Licensed Lodging Establishment List, $limit=5000",
     "1,470 rows statewide: name, street, city, ZIP, telephone, county, approval code",
     "READ -- a property-level register; Missouri rows under 640-658 are leads"),
    ("data.kcmo.org (Socrata) pnm4-68wg", "Business License Holders, business_type like hotel / lodging / "
     "accommodation", "31 rows (18 'Hotels (except Casino Hotels) and Motels', 13 'All Other Traveler Accommodation')",
     "MEASURED, NOT READ -- a licence-holder list overlapped by the state register"),
    ("agriculture.ks.gov Food Safety & Lodging, lodging licence information page", "GET (plain client)", "HTTP 403",
     "NO OPEN KANSAS REGISTER -- the KDA licenses lodging establishments but publishes no bulk list"),
    ("Socrata catalog (all domains)", "q=lodging kansas", "no Kansas lodging dataset", "no Kansas register"),
]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    with open(SNAPSHOT, encoding="utf-8") as fh:
        rows = json.load(fh)
    sha = _sha256(SNAPSHOT)
    leads, by_corridor, refused_future = [], Counter(), Counter()
    in_admitted = refused = 0
    for i, r in enumerate(rows):
        z = (r.get("establishment_zip_code") or "").strip()[:5]
        if not z.startswith(LEAD_PREFIXES):
            continue
        klass, slug, _why = GEO.classify_postal(z, r.get("establishment_city") or "")
        if slug:
            in_admitted += 1
            by_corridor[slug] += 1
        else:
            refused += 1
            refused_future[GEO.future_market_for(z) or "(none)"] += 1
        leads.append(OrderedDict([
            ("business_name", (r.get("establishment_name") or "").strip()),
            ("street", (r.get("establishment_address_2") or "").strip()),
            ("city", (r.get("establishment_city") or "").strip()),
            ("state", (r.get("establishment_state") or "").strip()),
            ("postal_code", z),
            ("phone", (r.get("telephone_number") or "").strip()),
            ("county_code", r.get("county")),
            ("license_number", None),
            ("rank_code", r.get("application_approval_code")),
            ("raw_pointer", "%s#row=%d" % (DATASET_PAGE, i)),
            ("snapshot_sha256", sha),
            ("corridor", slug or ""),
        ]))
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "10 -- the Missouri / Kansas lodging-register lane: MEASURED; Missouri READ, Kansas NONE OPEN"),
        ("register_exists", True),
        ("register_exists_by_state", OrderedDict([("MO", True), ("KS", False)])),
        ("measured_on", "2026-10-05"),
        ("measurements", [OrderedDict([("portal", p), ("query", q), ("answered", a), ("verdict", w)])
                          for p, q, a, w in MEASUREMENTS]),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 9),
        ("snapshot", OrderedDict([
            ("source_url", SOURCE_URL), ("dataset_page", DATASET_PAGE),
            ("local_file", os.path.relpath(SNAPSHOT, _DASH).replace(os.sep, "/")), ("sha256", sha),
            ("rows_statewide", len(rows)),
            ("rows_by_approval_code", OrderedDict(sorted(Counter(str(r.get("application_approval_code"))
                                                                for r in rows).items()))),
            ("approval_code_is_not_an_operating_status",
             "operating chain hotels carry NA and blank codes alike; the code is carried, never read as closure"),
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
        rep["register_exists_by_state"], rep["lead_rows"], rep["leads_in_admitted_postal_codes"],
        rep["leads_refused_by_their_own_postal_code"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
