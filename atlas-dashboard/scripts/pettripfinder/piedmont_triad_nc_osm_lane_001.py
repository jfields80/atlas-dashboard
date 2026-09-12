"""PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001 -- Phase 4A: the OpenStreetMap lane.

Reads the local Geofabrik North Carolina extract (ODbL, (c) OpenStreetMap
contributors) and keeps every ``tourism=hotel`` / ``tourism=motel`` element --
node, way or multipolygon relation -- inside this market's OBSERVATION box.

WHY A TWO-PASS READ, NOT THE AREA-ASSEMBLY INDEX
------------------------------------------------
Raleigh's run measured the shared index builder's pyosmium area-assembly pass
at over an hour on this 428 MB extract before it died without writing an index.
A lodging census needs a point per building, not a polygon: pass one keeps
tagged nodes inside the box and remembers the node references of tagged ways
(and of the outer ways of tagged relations); pass two reads only those node
locations and takes each way's centroid. Minutes, not hours.

A map row is IDENTITY and DISCOVERY evidence, tier 3. It never carries a pet
policy and never admits a building: the postal code the property's own page
states does that.

Output:
  launch_packages/pettripfinder/markets/reports/piedmont_triad_nc_osm_lane_001.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

import osmium  # noqa: E402

WORK_ORDER = "PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "piedmont-triad-nc"
PBF = os.path.join(_DASH, "data", "osm_extracts", "north-carolina-latest.osm.pbf")
CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                      "piedmont_triad_nc.json")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "piedmont_triad_nc_osm_lane_001.json")

LODGING = {"hotel", "motel"}
KEEP_TAGS = ("name", "brand", "brand:wikidata", "operator", "tourism", "addr:housenumber",
             "addr:street", "addr:city", "addr:state", "addr:postcode", "phone",
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


def build():
    started = time.time()
    with open(CONFIG, encoding="utf-8") as fh:
        box = json.load(fh)["geographic_bounds"]
    one = PassOne(box)
    one.apply_file(PBF, locations=False)
    # relation outer ways need their own node refs
    rel_way_ids = {wid for _t, wids in one.relations.values() for wid in wids}
    way_refs = {}
    if rel_way_ids:
        wr = WayRefs(rel_way_ids)
        wr.apply_file(PBF, locations=False)
        way_refs = wr.refs
    wanted = {ref for _t, refs in one.ways.values() for ref in refs}
    wanted |= {ref for refs in way_refs.values() for ref in refs}
    locs = NodeLocations(wanted)
    locs.apply_file(PBF, locations=False)

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
    elements.sort(key=lambda e: (e["type"], e["id"]))
    for e in elements:
        e["osm_url"] = "https://www.openstreetmap.org/%s/%d" % (e["type"], e["id"])

    md5 = hashlib.md5()
    with open(PBF, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            md5.update(chunk)
    return OrderedDict([
        ("schema", "ptf-osm-lodging-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "4A -- OpenStreetMap / Geofabrik lodging elements inside the observation box"),
        ("source", OrderedDict([
            ("pbf", "data/osm_extracts/north-carolina-latest.osm.pbf"),
            ("url", "https://download.geofabrik.de/north-america/us/north-carolina-latest.osm.pbf"),
            ("pbf_md5", md5.hexdigest()),
            ("pbf_bytes", os.path.getsize(PBF)),
            ("pbf_snapshot",
             "the 2026-09-10 Geofabrik download, reused from the Charlotte run's local copy; the "
             "upstream file has since been republished, so this md5 is the snapshot's own"),
            ("attribution", "(c) OpenStreetMap contributors (ODbL) -- www.openstreetmap.org/copyright"),
            ("bbox", [box["min_lat"], box["min_lng"], box["max_lat"], box["max_lng"]]),
            ("kept", "tourism in (hotel, motel)"),
        ])),
        ("paid_provider_calls", 0), ("free_http_requests", 0),
        ("seconds", round(time.time() - started, 1)),
        ("element_count", len(elements)),
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
    print("elements:", doc["element_count"], doc["by_type"], doc["by_tourism"],
          "postcode:", doc["with_postcode"], "street:", doc["with_street"],
          "seconds:", doc["seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
