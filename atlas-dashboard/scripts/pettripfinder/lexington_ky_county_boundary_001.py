"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phase 2, the county boundary as EVIDENCE.

Lexington's discovery box is deliberately wider than the market: it covers the
three fringe county seats (Georgetown/Scott, Nicholasville/Jessamine,
Versailles/Woodford) so this order can MEASURE them instead of assuming them.

That width has a sharp edge. `lodging_scope.classify_scope_fields` admits a
candidate whose coordinates fall inside the market bounds when the candidate
states no municipality at all -- so a Georgetown hotel with a blank OSM
`addr:city` would be admitted into Lexington by the box alone. Seven of the
ninety-one candidates in the free census state no city, and four of those sit
in Scott County.

So the boundary is not guessed and not approximated by a rectangle: it is read
out of the same Geofabrik Kentucky extract the census came from, as the OSM
administrative-boundary relations for the counties involved, and written out as
committed polygons. `admin_level=6` is the county level in the United States;
Lexington-Fayette is a merged city-county, so its city boundary and its county
boundary are the same ring.

Output: launch_packages/pettripfinder/markets/reports/lexington_ky_county_boundaries_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict

import osmium

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
PBF = os.path.join(_DASH, "data", "osm_extracts", "kentucky-latest.osm.pbf")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "lexington_ky_county_boundaries_001.json")

WANTED = {
    "Fayette County": "CORE",
    "Scott County": "FRINGE",
    "Jessamine County": "FRINGE",
    "Woodford County": "FRINGE",
    "Clark County": "NEAR_MISS",
    "Madison County": "NEAR_MISS",
    "Bourbon County": "NEAR_MISS",
    "Franklin County": "NEAR_MISS",
}


class CountyHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.found = {}
        self.factory = osmium.geom.GeoJSONFactory()

    def area(self, a):
        t = a.tags
        if t.get("boundary") != "administrative":
            return
        if t.get("admin_level") != "6":
            return
        name = t.get("name") or ""
        if name not in WANTED:
            return
        if t.get("state") and t.get("state") != "Kentucky":
            return
        try:
            geo = json.loads(self.factory.create_multipolygon(a))
        except Exception:  # noqa: BLE001
            return
        rings = []
        if geo.get("type") == "MultiPolygon":
            for poly in geo["coordinates"]:
                rings.append(poly[0])
        elif geo.get("type") == "Polygon":
            rings.append(geo["coordinates"][0])
        if not rings:
            return
        prev = self.found.get(name)
        total = sum(len(r) for r in rings)
        if prev is None or total > prev["vertex_count"]:
            self.found[name] = OrderedDict([
                ("name", name),
                ("band", WANTED[name]),
                ("osm_area_id", a.id),
                ("wikidata", t.get("wikidata") or ""),
                ("admin_level", "6"),
                ("ring_count", len(rings)),
                ("vertex_count", total),
                ("rings", [[[round(x, 6), round(y, 6)] for x, y in r] for r in rings]),
            ])


def bbox(rings):
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return [round(min(ys), 6), round(min(xs), 6), round(max(ys), 6), round(max(xs), 6)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pbf", default=PBF)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    h = CountyHandler()
    h.apply_file(args.pbf, locations=True, idx="flex_mem")

    counties = OrderedDict()
    for name in WANTED:
        rec = h.found.get(name)
        if rec is None:
            continue
        rec["bbox_lat_lng"] = bbox(rec["rings"])
        counties[name] = rec

    report = OrderedDict([
        ("schema", "ptf-county-boundaries/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", "lexington-ky"),
        ("what_this_is",
         "OSM administrative boundaries (admin_level=6, the US county level) for the counties "
         "the Lexington discovery box touches, read out of the same Geofabrik Kentucky extract "
         "that produced the free census. Rings are [lng, lat] pairs. Fayette is the CORE: "
         "Lexington-Fayette is a merged city-county, so the city and the county are one ring. "
         "The FRINGE counties are the three the order named for evaluation. The NEAR_MISS "
         "counties are carried so a candidate that lands in one can be named rather than just "
         "called 'outside'."),
        ("why_this_exists",
         "lodging_scope.classify_scope_fields admits a candidate whose coordinates are inside "
         "the market bounds when the candidate states NO municipality. The Lexington box is "
         "deliberately wider than the market, so that rule alone would admit a blank-city "
         "Georgetown hotel. A point-in-polygon test against the real county boundary settles "
         "those on evidence instead of on the width of a rectangle."),
        ("source", OrderedDict([
            ("pbf", os.path.basename(args.pbf)),
            ("url", "https://download.geofabrik.de/north-america/us/kentucky-latest.osm.pbf"),
            ("license", "ODbL 1.0"),
            ("attribution", "(c) OpenStreetMap contributors (ODbL) -- www.openstreetmap.org/copyright"),
        ])),
        ("counties_found", list(counties.keys())),
        ("counties_missing", [n for n in WANTED if n not in counties]),
        ("counties", counties),
    ])
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    for n, c in counties.items():
        print(f"{n:20s} band={c['band']:9s} rings={c['ring_count']} vertices={c['vertex_count']} bbox={c['bbox_lat_lng']}")
    print("missing:", report["counties_missing"])
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
