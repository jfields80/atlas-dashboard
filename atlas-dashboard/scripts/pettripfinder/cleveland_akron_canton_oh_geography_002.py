"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phase 2.

Mechanical reconstruction of the Cleveland-Akron-Canton market geography as
the committed authority states it: the 14 ptf-market/1.1 corridors and their
postal codes, the 24 discovery cells that mirror them, and where every one
of the 188 registered identities sits against both. Reports interior gaps,
fringe rows the census already holds outside every corridor, and the explicit
exclusions. Documents; never widens. Offline.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-market-geography-reconstruction/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DISCOVERY_CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "cleveland_akron_canton_oh.json")

# The intended coverage the order names, mapped onto the committed corridors.
DOCTRINE = OrderedDict([
    ("CLEVELAND", OrderedDict([
        ("downtown / core", ["cleveland-akron-canton-oh__downtown-cleveland"]),
        ("airport / west side", ["cleveland-akron-canton-oh__cleveland-airport-west"]),
        ("east-side suburbs", ["cleveland-akron-canton-oh__cleveland-east-beachwood", "cleveland-akron-canton-oh__mentor-lake-county"]),
        ("I-480 / I-71 corridors", ["cleveland-akron-canton-oh__independence-rockside", "cleveland-akron-canton-oh__cleveland-airport-west"]),
        ("I-271 / SR-8 southeast", ["cleveland-akron-canton-oh__macedonia-twinsburg-northfield", "cleveland-akron-canton-oh__streetsboro-hudson-aurora"]),
        ("I-77 south", ["cleveland-akron-canton-oh__richfield-brecksville"]),
    ])),
    ("AKRON / SUMMIT", OrderedDict([
        ("Akron", ["cleveland-akron-canton-oh__akron-downtown-east"]),
        ("Fairlawn", ["cleveland-akron-canton-oh__fairlawn-montrose-copley"]),
        ("Cuyahoga Falls / Stow", ["cleveland-akron-canton-oh__cuyahoga-falls-stow"]),
        ("Hudson", ["cleveland-akron-canton-oh__streetsboro-hudson-aurora"]),
        ("I-77 south / Green / CAK approach", ["cleveland-akron-canton-oh__akron-south-green"]),
    ])),
    ("CANTON / STARK", OrderedDict([
        ("Canton / North Canton / Belden Village / CAK", ["cleveland-akron-canton-oh__canton-north-canton-cak"]),
        ("Massillon / Alliance / other Stark", ["cleveland-akron-canton-oh__massillon-alliance-stark"]),
    ])),
])


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build() -> OrderedDict:
    market = read_json(os.path.join(PKG, "markets", f"{MARKET_ID}.json"))
    census = read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]
    cells = read_json(DISCOVERY_CONFIG)
    corridors = OrderedDict()
    postal_to_corridor = {}
    for c in market["corridors"]:
        cid = c["corridor_id"]
        corridors[cid] = OrderedDict([
            ("name", c.get("name") or c.get("title")), ("postal_codes", list(c.get("included_postal_codes") or [])),
            ("cities", list(c.get("included_cities") or [])), ("explicit_hotel_ids", len(c.get("explicit_hotel_ids") or [])),
            ("excluded_hotel_ids", list(c.get("excluded_hotel_ids") or [])), ("census_rows", 0), ("census_postals", Counter()),
        ])
        for pc in c.get("included_postal_codes") or []:
            postal_to_corridor[pc] = cid
    fringe = []
    for r in census:
        cid = r.get("corridor")
        if cid and cid in corridors:
            corridors[cid]["census_rows"] += 1
            corridors[cid]["census_postals"][r.get("postal_code")] += 1
        else:
            fringe.append(OrderedDict([("identity_key", r["identity_key"]), ("city", r.get("city")), ("postal_code", r.get("postal_code")),
                                       ("address", r.get("address")), ("policy_state_live", None)]))
    for cid in corridors:
        corridors[cid]["census_postals"] = OrderedDict(sorted(corridors[cid]["census_postals"].items(), key=lambda kv: -kv[1]))
    # Interior gaps: corridor postal codes with zero census rows.
    interior_gaps = []
    for cid, c in corridors.items():
        for pc in c["postal_codes"]:
            if pc not in c["census_postals"]:
                interior_gaps.append(OrderedDict([("corridor", cid), ("postal_code", pc)]))
    # Census postal codes not declared by any corridor (rows are assigned by city fallback or unassigned).
    undeclared_postals = Counter(r.get("postal_code") for r in census if r.get("postal_code") not in postal_to_corridor)
    cell_rows = [OrderedDict([("cell_id", c["cell_id"]), ("municipality", c["municipality"]), ("label", c["label"]), ("radius_m", c["radius_meters"])]) for c in cells["cells"]]
    doctrine = OrderedDict()
    for core, areas in DOCTRINE.items():
        doctrine[core] = OrderedDict()
        for area, cids in areas.items():
            doctrine[core][area] = OrderedDict([("corridors", cids), ("census_rows", sum(corridors[c]["census_rows"] for c in cids if c in corridors))])
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("phase", "2 -- reconstruct market geography"), ("market_id", MARKET_ID), ("as_of", "2026-09-01"),
        ("what_this_is", "The committed geography restated: corridors with their postal codes and census occupancy, the discovery cells seeded from them, the doctrine areas the order names mapped onto corridors, interior postal gaps, and the fringe rows the census already holds outside every corridor. Nothing here widens the market; fringe rows keep their registration and receive no discovery cell."),
        ("core_metros", market.get("core_metros")), ("region_type", market.get("region_type")), ("route_mode", market.get("route_mode")),
        ("doctrine_coverage", doctrine),
        ("corridors", corridors),
        ("discovery_cells", cell_rows), ("discovery_bounds", cells["geographic_bounds"]),
        ("interior_postal_gaps", interior_gaps),
        ("census_postals_not_declared_by_any_corridor", OrderedDict(sorted(undeclared_postals.items(), key=lambda kv: (-kv[1], str(kv[0]))))),
        ("fringe_rows_outside_every_corridor", fringe),
        ("explicit_exclusions", OrderedDict((cid, c["excluded_hotel_ids"]) for cid, c in corridors.items() if c["excluded_hotel_ids"])),
        ("accidental_omission_review", [
            "Strongsville (44136) and Brunswick (44212): I-71 south lodging cluster between the airport corridor and Medina; one Brunswick row is already a fringe registration. Not a corridor; flagged for founder geography ruling, not widened here.",
            "Avon / Avon Lake (44011 / 44012): two Avon rows are registered fringe (Cambria->Wyndham Avon; Residence Inn Avon is LIVE); the I-90 west cluster has no corridor.",
            "Mayfield / Highland Heights (44143) and Wickliffe (44092): inside the east-side doctrine, partially declared (44143 present, 44092 absent).",
            "Elyria / Lorain / Oberlin (44035 / 44052 / 44074): Lorain County rows registered as fringe; outside the three stated cores.",
            "Geneva-on-the-Lake (44041): Ashtabula County resort rows registered as fringe; outside the CSA doctrine.",
        ]),
        ("summary", OrderedDict([("corridors", len(corridors)), ("cells", len(cell_rows)), ("census_rows_in_corridors", sum(c["census_rows"] for c in corridors.values())),
                                 ("fringe_rows", len(fringe)), ("interior_postal_gaps", len(interior_gaps))])),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_geography_002.json"))
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["summary"]))
    print("fringe:", [(f["city"], f["postal_code"]) for f in rep["fringe_rows_outside_every_corridor"]])
    print("interior gaps:", [(g["corridor"].split("__")[1], g["postal_code"]) for g in rep["interior_postal_gaps"]])
    print("undeclared postals:", dict(rep["census_postals_not_declared_by_any_corridor"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
