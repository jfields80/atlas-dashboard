"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phase 12: the OpenStreetMap lane.

Reads the Geofabrik TEXAS extract (ODbL, (c) OpenStreetMap contributors) and keeps every
``tourism=hotel / motel / guest_house / hostel / chalet / apartment`` element -- node, way or multipolygon
relation -- inside this market's OBSERVATION box, which reaches north past Denton, Prosper and Celina, east past
Rockwall and Forney, south past Waxahachie and Cleburne and west past Weatherford, so the boundary audit counts what it
refuses instead of being blind to it.

ONE EXTRACT, OWNED, AND AN OUTER-PLACE MEASUREMENT
-------------------------------------------------
The Texas extract is OWNED: PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001 downloaded the dated Geofabrik extract
``texas-260929.osm.pbf`` (722,556,275 bytes) once, free, on 2026-09-30, and San Antonio reused it. This order
hard-linked those exact bytes into ``data/osm_extracts/texas-latest.osm.pbf`` -- ZERO download requests (owned data
first) -- and re-measures the md5 over the local file every run. A map row is discovery evidence only; a building's
CURRENT operation is decided on its own page, never here.

The order's boundary audit also asks what exists in Sherman / Denison, Gainesville, Greenville, Corsicana and Waco,
outside the observation box. The extract is read ONCE over a wider AUDIT box; the census sees only the observation
box, and the outer places are MEASURED (a count per named region box) and never enter the census.

WHY A TWO-PASS READ, NOT THE AREA-ASSEMBLY INDEX
------------------------------------------------
A lodging census needs a point per building, not a polygon: pass one keeps tagged nodes inside the box and
remembers the node references of tagged ways (and of the outer ways of tagged relations); pass two reads only
those node locations and takes each way's centroid. Minutes, not hours.

A map row is IDENTITY and DISCOVERY evidence, tier 3. It never carries a pet policy, never admits a building and
never proves current operation.

Output:
  launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_osm_lane_001.json
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

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
#: (local file, Geofabrik dated URL, how it came to be on this machine)
PBFS = [
    (os.path.join(_DASH, "data", "osm_extracts", "texas-latest.osm.pbf"),
     "https://download.geofabrik.de/north-america/us/texas-latest.osm.pbf",
     "OWNED: the 2026-09-30 Geofabrik Texas download (texas-260929.osm.pbf, 722,556,275 bytes) made by "
     "PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001 and reused by San Antonio, hard-linked into this worktree by this order "
     "at zero requests; the upstream file may since have been republished, so the md5 is the snapshot's own"),
]
#: Outer-place measurement boxes for the boundary audit (min_lat, max_lat, min_lng, max_lng). Counted, never censused.
STATEWIDE_REGIONS = [
    ("Weatherford / Willow Park / Aledo", (32.68, 32.84, -97.90, -97.62)),
    ("Waxahachie", (32.34, 32.46, -96.90, -96.78)),
    ("Ennis", (32.29, 32.36, -96.68, -96.58)),
    ("Corsicana", (32.04, 32.13, -96.53, -96.42)),
    ("Greenville", (33.08, 33.19, -96.18, -96.04)),
    ("Sherman / Denison", (33.58, 33.80, -96.68, -96.50)),
    ("Gainesville", (33.58, 33.68, -97.20, -97.08)),
    ("Waco / Woodway / Bellmead", (31.47, 31.65, -97.27, -97.04)),
    ("Decatur", (33.20, 33.27, -97.62, -97.55)),
    ("Denton / Corinth", (33.13, 33.28, -97.21, -97.04)),
    ("Rockwall / Royse City", (32.86, 32.99, -96.52, -96.30)),
    ("Granbury / Glen Rose", (32.18, 32.50, -97.85, -97.72)),
]
#: One read covers the observation box AND every outer region (the extract is read once).
AUDIT_BOX = {"min_lat": 31.45, "max_lat": 33.82, "min_lng": -97.95, "max_lng": -96.00}
CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                      "dallas_fort_worth_tx.json")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "dallas_fort_worth_tx_osm_lane_001.json")

#: guest_house, hostel, chalet and apartment are kept too: the Metroplex's serviced apartments, Uptown / Victory Park
#: residence towers, stadium-week rentals and bed-and-breakfasts are often tagged that way, and the census must SEE a
#: rental to refuse it (or an inn to admit it) by decision.
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


def statewide_measurement(audit):
    """Lodging elements per named outer region, from the one audit-box read. Boundary facts only."""
    out = OrderedDict()
    for name, (la0, la1, ln0, ln1) in STATEWIDE_REGIONS:
        inside = [e for e in audit if la0 <= e["lat"] <= la1 and ln0 <= e["lng"] <= ln1]
        out[name] = OrderedDict([
            ("elements", len(inside)),
            ("hotel_motel", sum(1 for e in inside if e["tags"].get("tourism") in ("hotel", "motel"))),
        ])
    return OrderedDict([
        ("what_it_is", "Counts of OSM lodging elements (tourism in hotel, motel, guest_house, hostel, chalet, "
                       "apartment) per named outer region box, read from the same local extract in the same pass. "
                       "Never censused."),
        ("audit_box", AUDIT_BOX),
        ("audit_box_elements_total", len(audit)),
        ("regions", out),
    ])


def build():
    with open(CONFIG, encoding="utf-8") as fh:
        box = json.load(fh)["geographic_bounds"]
    merged = OrderedDict()
    sources = []
    audit = []
    for pbf, url, how in PBFS:
        audit = _read_one(pbf, AUDIT_BOX)
        got = [dict(e) for e in audit if box["min_lat"] <= e["lat"] <= box["max_lat"]
               and box["min_lng"] <= e["lng"] <= box["max_lng"]]
        extract = os.path.basename(url).split("-")[0]
        new = 0
        for e in got:
            key = (e["type"], e["id"])
            if key in merged:
                continue
            e["extract"] = extract
            merged[key] = OrderedDict(e)
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
        ("phase", "12 -- OpenStreetMap / Geofabrik lodging elements inside the observation box (Texas), plus an "
                  "outer-place region count for the boundary audit"),
        ("source", OrderedDict([
            ("extracts", sources),
            ("overpass_attempts", []),
            ("attribution", "(c) OpenStreetMap contributors (ODbL) -- www.openstreetmap.org/copyright"),
            ("bbox", [box["min_lat"], box["min_lng"], box["max_lat"], box["max_lng"]]),
            ("kept", "tourism in (hotel, motel, guest_house, hostel, chalet, apartment)"),
        ])),
        ("paid_provider_calls", 0), ("free_http_requests", 0),  # read from the local extracts; nothing fetched by this run
        ("extract_download_requests", 0),  # OWNED extract hard-linked from another worktree; nothing downloaded
        ("statewide_measurement", statewide_measurement(audit)),
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
