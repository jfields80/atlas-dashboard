"""PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001 -- Phase 13: the OpenStreetMap lane.

Reads the Geofabrik FLORIDA extract (ODbL, (c) OpenStreetMap contributors) and keeps every
``tourism=hotel / motel / guest_house / hostel / chalet / apartment`` element -- node, way or multipolygon
relation -- inside this market's OBSERVATION box, which reaches south past Naples to Marco Island and Everglades City,
north past Punta Gorda and Port Charlotte, west over Boca Grande, Pine Island and Captiva and east to LaBelle, so the
boundary audit counts what it refuses instead of being blind to it.

ONE EXTRACT, OWNED, AND A STATEWIDE MEASUREMENT
-----------------------------------------------
The market is a single-state market, so one extract is read. A Florida extract is ALREADY OWNED on this machine: the
2026-09-15 Geofabrik Florida download made by PTF-TAMPA-FL-HARDENED-V2 and reused by Fort Lauderdale (656,564,714
bytes, md5 63d91c8dcbce4dd2479f727a7ef97074). This order hard-linked those bytes into
``data/osm_extracts/florida-latest.osm.pbf`` -- ZERO download requests (owned data first). Every run reads those
bytes and re-measures the md5 over the local file. The snapshot predates this order by three weeks; a map row is
discovery evidence only, and a building's CURRENT operation is decided on its own page, never here.

The order's boundary audit also asks what exists in Sarasota, Bradenton and Venice, far outside the observation box.
Those are MEASURED here statewide (a count per named region box) and never enter the census: a far-away count is a
boundary fact, not a lead.

WHY A TWO-PASS READ, NOT THE AREA-ASSEMBLY INDEX
------------------------------------------------
A lodging census needs a point per building, not a polygon: pass one keeps tagged nodes inside the box and
remembers the node references of tagged ways (and of the outer ways of tagged relations); pass two reads only
those node locations and takes each way's centroid. Minutes, not hours.

A map row is IDENTITY and DISCOVERY evidence, tier 3. It never carries a pet policy, never admits a building and
never proves current operation: the postal code the property's own page states does the first, and the property's
own current page the last.

Output:
  launch_packages/pettripfinder/markets/reports/fort_myers_fl_osm_lane_001.json
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

WORK_ORDER = "PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "fort-myers-fl"
#: (local file, Geofabrik dated URL, how it came to be on this machine)
PBFS = [
    (os.path.join(_DASH, "data", "osm_extracts", "florida-latest.osm.pbf"),
     "https://download.geofabrik.de/north-america/us/florida-latest.osm.pbf",
     "OWNED: the 2026-09-15 Geofabrik Florida download made by PTF-TAMPA-FL-HARDENED-V2 (656,564,714 bytes), "
     "hard-linked into this worktree by this order at zero requests; the upstream file may since have been "
     "republished, so the md5 is the snapshot's own"),
]
#: Statewide measurement boxes for the boundary audit (min_lat, max_lat, min_lng, max_lng). Counted, never censused.
STATEWIDE_REGIONS = [
    ("Naples (city and North Naples)", (26.08, 26.30, -81.82, -81.72)),
    ("Marco Island", (25.90, 25.98, -81.75, -81.68)),
    ("Punta Gorda / Port Charlotte", (26.88, 27.05, -82.15, -81.95)),
    ("Englewood / Boca Grande", (26.70, 26.98, -82.40, -82.20)),
    ("Sarasota / Siesta Key / Longboat Key", (27.20, 27.45, -82.70, -82.45)),
    ("Bradenton / Anna Maria Island", (27.42, 27.55, -82.75, -82.50)),
    ("Venice / North Port", (27.00, 27.15, -82.48, -82.20)),
    ("Everglades City / Chokoloskee", (25.82, 25.90, -81.42, -81.35)),
]
FLORIDA_BOX = {"min_lat": 24.39, "max_lat": 31.01, "min_lng": -87.64, "max_lng": -79.97}
CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                      "fort_myers_fl.json")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "fort_myers_fl_osm_lane_001.json")

#: guest_house, hostel, chalet and apartment are kept too: Fort Myers Beach's and Sanibel's condominium resorts, the
#: islands' cottage rentals and the bed-and-breakfasts in the observation box are often tagged that way, and the
#: census must SEE a rental to refuse it (or an inn to admit it) by decision.
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
    got = _read_one(pbf, FLORIDA_BOX)
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
        ("florida_elements_total", len(got)),
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
        ("phase", "13 -- OpenStreetMap / Geofabrik lodging elements inside the observation box (Florida), plus a "
                  "statewide region count for the boundary audit"),
        ("source", OrderedDict([
            ("extracts", sources),
            ("overpass_attempts", []),
            ("attribution", "(c) OpenStreetMap contributors (ODbL) -- www.openstreetmap.org/copyright"),
            ("bbox", [box["min_lat"], box["min_lng"], box["max_lat"], box["max_lng"]]),
            ("kept", "tourism in (hotel, motel, guest_house, hostel, chalet, apartment)"),
        ])),
        ("paid_provider_calls", 0), ("free_http_requests", 0),  # read from the local extracts; nothing fetched by this run
        ("extract_download_requests", 0),  # OWNED extract hard-linked from another worktree; nothing downloaded
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
