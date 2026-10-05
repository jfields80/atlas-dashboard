"""PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001 -- Phase 10: the OpenStreetMap lane.

Reads the Geofabrik MISSOURI and KANSAS extracts (ODbL, (c) OpenStreetMap contributors) and keeps every
``tourism=hotel / motel / guest_house / hostel / chalet / apartment`` element -- node, way or multipolygon
relation -- inside this market's OBSERVATION box, which reaches west past Lawrence, Topeka and Manhattan, north to
St. Joseph, east to Columbia and the Lake of the Ozarks and south to Wichita and Springfield, so the boundary audit
counts what it refuses instead of being blind to it.

TWO EXTRACTS, ONE STATE EACH
---------------------------
The market is a CROSS-STATE market, so both states are read, each from its own extract, and every element records
the extract it came from (the two-state rule: one read per extract, never one cache shared by both). No Missouri or
Kansas extract was owned by any worktree on this machine; this order downloaded Geofabrik's dated
``missouri-261004.osm.pbf`` (197,739,412 bytes, md5 480390032f35089a04388416ff0187e4) and ``kansas-261004.osm.pbf``
(116,470,419 bytes, md5 9a45643ebfba4acb2558a099f8ae98b2), each matching Geofabrik's published .md5, ONCE, free, on
2026-10-05, to ``data/osm_extracts/<state>-latest.osm.pbf``. Every run reads those bytes at zero requests and
re-measures each md5 over the local file. An element both extracts carry (a border building) is kept once, from the
first extract that read it.

WHY A TWO-PASS READ, NOT THE AREA-ASSEMBLY INDEX
------------------------------------------------
A lodging census needs a point per building, not a polygon: pass one keeps tagged nodes inside the box and
remembers the node references of tagged ways (and of the outer ways of tagged relations); pass two reads only
those node locations and takes each way's centroid. Minutes, not hours.

A map row is IDENTITY and DISCOVERY evidence, tier 3. It never carries a pet policy and never admits a
building: the postal code the property's own page states does that.

Output:
  launch_packages/pettripfinder/markets/reports/kansas_city_mo_osm_lane_001.json
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

WORK_ORDER = "PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001"
MARKET_ID = "kansas-city-mo"
#: (local file, Geofabrik dated URL, how it came to be on this machine)
PBFS = [
    (os.path.join(_DASH, "data", "osm_extracts", "missouri-latest.osm.pbf"),
     "https://download.geofabrik.de/north-america/us/missouri-261004.osm.pbf",
     "Downloaded once on 2026-10-05 by this order (Geofabrik missouri-261004, 197,739,412 bytes, md5 matching "
     "Geofabrik's published .md5; no Missouri extract was owned)"),
    (os.path.join(_DASH, "data", "osm_extracts", "kansas-latest.osm.pbf"),
     "https://download.geofabrik.de/north-america/us/kansas-261004.osm.pbf",
     "Downloaded once on 2026-10-05 by this order (Geofabrik kansas-261004, 116,470,419 bytes, md5 matching "
     "Geofabrik's published .md5; no Kansas extract was owned)"),
]
CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                      "kansas_city_mo.json")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "kansas_city_mo_osm_lane_001.json")

#: guest_house, hostel, chalet and apartment are kept too: Kansas City's furnished condo units, serviced apartments
#: and aparthotels, and the lake cabins in the observation box, are often tagged that way, and the census must SEE a
#: rental to refuse it by decision.
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
        ("phase", "10 -- OpenStreetMap / Geofabrik lodging elements inside the observation box (Missouri and Kansas)"),
        ("source", OrderedDict([
            ("extracts", sources),
            ("overpass_attempts", []),
            ("attribution", "(c) OpenStreetMap contributors (ODbL) -- www.openstreetmap.org/copyright"),
            ("bbox", [box["min_lat"], box["min_lng"], box["max_lat"], box["max_lng"]]),
            ("kept", "tourism in (hotel, motel, guest_house, hostel, chalet, apartment)"),
        ])),
        ("paid_provider_calls", 0), ("free_http_requests", 0),  # read from the local extracts; nothing fetched by this run
        ("extract_download_requests", 6),  # per state: the HEAD, .md5 and .pbf, once, free, before the first run
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
