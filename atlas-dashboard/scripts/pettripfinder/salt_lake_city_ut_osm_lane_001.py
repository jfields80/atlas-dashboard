"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phase 11: the OpenStreetMap lane.

Reads the Geofabrik UTAH extract (ODbL, (c) OpenStreetMap contributors) and keeps every
``tourism=hotel / motel / guest_house / hostel / chalet / apartment`` element -- node, way or multipolygon
relation -- inside this market's OBSERVATION box, which reaches south past Provo, north past Ogden, west to Tooele and
Grantsville and east across the Wasatch Back to Heber City, Kamas and Coalville, so the boundary audit counts what it
refuses instead of being blind to it.

ONE EXTRACT, AND A STATEWIDE MEASUREMENT
---------------------------------------
The market is a single-state market whose neighbours are all Utah, so one extract is read. No Utah extract was owned
by any worktree on this machine; this order downloaded Geofabrik's dated ``utah-261006.osm.pbf`` (169,707,025 bytes,
md5 dce6fbd13a42a44d005214c864f90e1f, matching Geofabrik's published .md5) ONCE, free, on 2026-10-07, to
``data/osm_extracts/utah-latest.osm.pbf``. Every run reads those bytes at zero requests and re-measures the md5 over
the local file.

The order's boundary audit also asks what exists in Moab, St. George, Springdale / Zion, Bryce Canyon, Logan and Bear
Lake, far outside the observation box. Those are MEASURED here statewide (a count per named region box) and never
enter the census: a far-away count is a boundary fact, not a lead.

WHY A TWO-PASS READ, NOT THE AREA-ASSEMBLY INDEX
------------------------------------------------
A lodging census needs a point per building, not a polygon: pass one keeps tagged nodes inside the box and
remembers the node references of tagged ways (and of the outer ways of tagged relations); pass two reads only
those node locations and takes each way's centroid. Minutes, not hours.

A map row is IDENTITY and DISCOVERY evidence, tier 3. It never carries a pet policy and never admits a
building: the postal code the property's own page states does that.

Output:
  launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_osm_lane_001.json
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

import osmium  # noqa: E402

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
MARKET_ID = "salt-lake-city-ut"
#: (local file, Geofabrik dated URL, how it came to be on this machine)
PBFS = [
    (os.path.join(_DASH, "data", "osm_extracts", "utah-latest.osm.pbf"),
     "https://download.geofabrik.de/north-america/us/utah-261006.osm.pbf",
     "Downloaded once on 2026-10-07 by this order (Geofabrik utah-261006, 169,707,025 bytes, md5 matching "
     "Geofabrik's published .md5; no Utah extract was owned)"),
]
#: Statewide measurement boxes for the boundary audit (min_lat, max_lat, min_lng, max_lng). Counted, never censused.
STATEWIDE_REGIONS = [
    ("Moab", (38.45, 38.70, -109.70, -109.40)),
    ("St. George / Washington / Hurricane", (36.95, 37.25, -113.75, -113.25)),
    ("Springdale / Zion", (37.10, 37.30, -113.05, -112.90)),
    ("Bryce Canyon / Tropic", (37.55, 37.75, -112.30, -112.05)),
    ("Cedar City", (37.60, 37.75, -113.15, -113.00)),
    ("Kanab", (37.00, 37.10, -112.60, -112.45)),
    ("Logan / Cache Valley", (41.55, 41.95, -112.00, -111.70)),
    ("Bear Lake / Garden City", (41.85, 42.00, -111.45, -111.30)),
    ("Ogden (city)", (41.15, 41.30, -112.05, -111.90)),
    ("Provo / Orem (cities)", (40.18, 40.34, -111.75, -111.62)),
    ("Heber City / Midway", (40.45, 40.56, -111.52, -111.38)),
]
UTAH_BOX = {"min_lat": 36.99, "max_lat": 42.01, "min_lng": -114.06, "max_lng": -109.04}
CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                      "salt_lake_city_ut.json")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "salt_lake_city_ut_osm_lane_001.json")

#: guest_house, hostel, chalet and apartment are kept too: Park City's condominium lodges and ski chalets, downtown
#: Salt Lake City's serviced apartments and the bed-and-breakfasts in the observation box are often tagged that way,
#: and the census must SEE a rental to refuse it (or a lodge to admit it) by decision.
LODGING = {"hotel", "motel", "guest_house", "hostel", "chalet", "apartment"}
KEEP_TAGS = ("name", "brand", "brand:wikidata", "operator", "tourism", "addr:housenumber",
             "addr:street", "addr:city", "addr:state", "addr:postcode", "addr:country", "phone",
             "contact:phone", "website", "contact:website", "building", "disused:tourism")


def _tags(obj):
    return OrderedDict((k, obj.tags[k]) for k in KEEP_TAGS if k in obj.tags)


class PassOne(osmium.SimpleHandler):
    def __init__(self, box):
        super().__init__()
        self.box = box
        self.nodes = []
        self.ways = {}
        self.relations = {}

    def _inside(self, lat, lng):
        b = self.box
        return b["min_lat"] <= lat <= b["max_lat"] and b["min_lng"] <= lng <= b["max_lng"]

    def node(self, n):
        if n.tags.get("tourism") in LODGING and n.location.valid() and \
                self._inside(n.location.lat, n.location.lon):
            self.nodes.append(OrderedDict([("type", "node"), ("id", n.id),
                                           ("lat", round(n.location.lat, 6)),
                                           ("lng", round(n.location.lon, 6)),
                                           ("tags", _tags(n))]))

    def way(self, w):
        if w.tags.get("tourism") in LODGING:
            self.ways[w.id] = (_tags(w), [r.ref for r in w.nodes])

    def relation(self, r):
        if r.tags.get("tourism") in LODGING:
            self.relations[r.id] = (_tags(r), [m.ref for m in r.members if m.type == "w"])


class WayRefs(osmium.SimpleHandler):
    def __init__(self, wanted):
        super().__init__()
        self.wanted = wanted
        self.refs = {}

    def way(self, w):
        if w.id in self.wanted:
            self.refs[w.id] = [r.ref for r in w.nodes]


class NodeLocations(osmium.SimpleHandler):
    def __init__(self, wanted):
        super().__init__()
        self.wanted = wanted
        self.loc = {}

    def node(self, n):
        if n.id in self.wanted and n.location.valid():
            self.loc[n.id] = (n.location.lat, n.location.lon)


def _read_one(pbf, box):
    one = PassOne(box)
    one.apply_file(pbf, locations=False)
    # relation outer ways need their own node refs
    rel_way_ids = {wid for _t, wids in one.relations.values() for wid in wids}
    way_refs = {}
    if rel_way_ids:
        wr = WayRefs(rel_way_ids)
        wr.apply_file(pbf, locations=False)
        way_refs = wr.refs
    wanted = {ref for _t, refs in one.ways.values() for ref in refs}
    wanted |= {ref for refs in way_refs.values() for ref in refs}
    locs = NodeLocations(wanted)
    locs.apply_file(pbf, locations=False)

    def centroid(refs):
        pts = [locs.loc[r] for r in refs if r in locs.loc]
        if not pts:
            return None
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    elements = list(one.nodes)
    for wid, (tags, refs) in one.ways.items():
        c = centroid(refs)
        if c and one._inside(*c):
            elements.append(OrderedDict([("type", "way"), ("id", wid), ("lat", round(c[0], 6)),
                                         ("lng", round(c[1], 6)), ("tags", tags)]))
    for rid, (tags, wids) in one.relations.items():
        c = centroid([ref for wid in wids for ref in way_refs.get(wid, [])])
        if c and one._inside(*c):
            elements.append(OrderedDict([("type", "relation"), ("id", rid),
                                         ("lat", round(c[0], 6)), ("lng", round(c[1], 6)),
                                         ("tags", tags)]))
    return elements


def _md5(path):
    md5 = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            md5.update(chunk)
    return md5.hexdigest()


def statewide_measurement():
    """Lodging elements per named far-away region, from the whole-state read. Boundary facts only."""
    pbf = PBFS[0][0]
    got = _read_one(pbf, UTAH_BOX)
    out = OrderedDict()
    for name, (la0, la1, ln0, ln1) in STATEWIDE_REGIONS:
        inside = [e for e in got if la0 <= e["lat"] <= la1 and ln0 <= e["lng"] <= ln1]
        out[name] = OrderedDict([
            ("elements", len(inside)),
            ("hotel_motel", sum(1 for e in inside if e["tags"].get("tourism") in ("hotel", "motel"))),
        ])
    return OrderedDict([
        ("what_it_is", "Counts of OSM lodging elements (tourism in hotel, motel, guest_house, hostel, chalet, "
                       "apartment) per named region box, read from the same local extract. Never censused."),
        ("utah_elements_total", len(got)),
        ("regions", out),
    ])


def build():
    with open(CONFIG, encoding="utf-8") as fh:
        box = json.load(fh)["geographic_bounds"]
    merged = OrderedDict()
    sources = []
    for pbf, url, how in PBFS:
        got = _read_one(pbf, box)
        extract = os.path.basename(url).split("-")[0]
        new = 0
        for e in got:
            key = (e["type"], e["id"])
            if key in merged:
                continue
            e["extract"] = extract
            merged[key] = e
            new += 1
        sources.append(OrderedDict([
            ("pbf", os.path.relpath(pbf, _DASH).replace(os.sep, "/")), ("url", url), ("pbf_md5", _md5(pbf)),
            ("pbf_bytes", os.path.getsize(pbf)),
            ("pbf_snapshot", how + " -- the md5 above is re-measured over the local file by this run"),
            ("elements_inside_box", len(got)), ("elements_kept_not_already_seen", new),
        ]))
    elements = sorted(merged.values(), key=lambda e: (e["type"], e["id"]))
    for e in elements:
        e["osm_url"] = "https://www.openstreetmap.org/%s/%d" % (e["type"], e["id"])
    return OrderedDict([
        ("schema", "ptf-osm-lodging-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "11 -- OpenStreetMap / Geofabrik lodging elements inside the observation box (Utah), plus a "
                  "statewide region count for the boundary audit"),
        ("source", OrderedDict([
            ("extracts", sources),
            ("overpass_attempts", []),
            ("attribution", "(c) OpenStreetMap contributors (ODbL) -- www.openstreetmap.org/copyright"),
            ("bbox", [box["min_lat"], box["min_lng"], box["max_lat"], box["max_lng"]]),
            ("kept", "tourism in (hotel, motel, guest_house, hostel, chalet, apartment)"),
        ])),
        ("paid_provider_calls", 0), ("free_http_requests", 0),  # read from the local extracts; nothing fetched by this run
        ("extract_download_requests", 4),  # the HEAD, the index, the .md5 and the .pbf, once, free, before the first run
        ("statewide_measurement", statewide_measurement()),
        ("element_count", len(elements)),
        ("by_extract", dict(Counter(e["extract"] for e in elements))),
        ("by_type", dict(Counter(e["type"] for e in elements))),
        ("by_tourism", dict(Counter(e["tags"].get("tourism") for e in elements))),
        ("with_postcode", sum(1 for e in elements if e["tags"].get("addr:postcode"))),
        ("with_street", sum(1 for e in elements if e["tags"].get("addr:street"))),
        ("a_map_row_is_not_a_policy",
         "Tier-3 identity and discovery evidence only; it never admits a building and never "
         "carries a pet policy."),
        ("elements", elements),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("elements:", doc["element_count"], doc["by_extract"], doc["by_type"], doc["by_tourism"],
          "postcode:", doc["with_postcode"], "street:", doc["with_street"])
    # no wall-clock is written or printed: the report must be byte-identical across reproductions
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
