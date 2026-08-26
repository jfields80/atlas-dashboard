"""PTF-PITTSBURGH-HARDENED-RECENSUS-001 -- the extract reducer against a real
(tiny) .osm.pbf: a node, a closed way and a multipolygon relation, each tagged
tourism=hotel, must all reach the index the way Overpass's ``out center``
returns them. Skipped when pyosmium is not installed; never touches a server."""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.discovery import osm_extract as OX
from scripts.pettripfinder.discovery import overpass as OV

osmium = pytest.importorskip("osmium")


def _write_tiny_pbf(path):
    """One hotel node, one hotel closed way, one hotel multipolygon relation
    (two rings), and a highway way that no index should keep."""
    writer = osmium.SimpleWriter(str(path))
    try:
        mutable = osmium.osm.mutable
        nodes = {
            1: (40.4400, -80.0000, {"tourism": "hotel", "name": "Node Hotel"}),
            # closed way ring
            11: (40.4500, -80.0100, {}), 12: (40.4500, -80.0090, {}),
            13: (40.4510, -80.0090, {}), 14: (40.4510, -80.0100, {}),
            # relation outer ring
            21: (40.4600, -80.0200, {}), 22: (40.4600, -80.0190, {}),
            23: (40.4610, -80.0190, {}), 24: (40.4610, -80.0200, {}),
            # relation inner ring (a courtyard)
            31: (40.4603, -80.0197, {}), 32: (40.4603, -80.0193, {}),
            33: (40.4607, -80.0193, {}), 34: (40.4607, -80.0197, {}),
            # a road
            41: (40.4700, -80.0300, {}), 42: (40.4700, -80.0290, {}),
        }
        for nid, (lat, lon, tags) in nodes.items():
            writer.add_node(mutable.Node(id=nid, location=(lon, lat), tags=tags, version=1))
        writer.add_way(mutable.Way(id=101, nodes=[11, 12, 13, 14, 11],
                                   tags={"tourism": "hotel", "name": "Way Hotel"}, version=1))
        writer.add_way(mutable.Way(id=102, nodes=[21, 22, 23, 24, 21], tags={}, version=1))
        writer.add_way(mutable.Way(id=103, nodes=[31, 32, 33, 34, 31], tags={}, version=1))
        writer.add_way(mutable.Way(id=104, nodes=[41, 42],
                                   tags={"highway": "residential"}, version=1))
        writer.add_relation(mutable.Relation(
            id=201, members=[("w", 102, "outer"), ("w", 103, "inner")],
            tags={"type": "multipolygon", "tourism": "hotel", "name": "Relation Hotel"},
            version=1))
    finally:
        writer.close()


def test_nodes_closed_ways_and_multipolygon_relations_all_reach_the_index(tmp_path):
    pbf = tmp_path / "tiny.osm.pbf"
    _write_tiny_pbf(pbf)
    out = tmp_path / "tiny.index.json"
    OX.build_index_from_pbf(pbf, extract_id="tiny", out=out,
                            keep_tag_keys=OX.DEFAULT_INDEX_TAG_KEYS)
    index = OX.ExtractIndex.load(out)
    by_type = {(e["type"], e["id"]): e for e in index.elements}
    assert set(by_type) == {("node", 1), ("way", 101), ("relation", 201)}
    relation = by_type[("relation", 201)]
    assert relation["tags"]["name"] == "Relation Hotel"
    assert abs(relation["center"]["lat"] - 40.4605) < 1e-3
    assert abs(relation["center"]["lon"] - (-80.0195)) < 1e-3
    # Each answers a cell exactly as an Overpass `out center` element does.
    bbox = OV.bbox_from_center_radius(40.45, -80.01, 3000)
    answered = index.query("tourism=hotel", bbox)["elements"]
    assert {(e["type"], e["id"]) for e in answered} == {("node", 1), ("way", 101), ("relation", 201)}
    source = json.loads(out.read_text(encoding="utf-8"))["source"]
    assert source["kept_tag_keys"] == list(OX.DEFAULT_INDEX_TAG_KEYS)


def test_the_bbox_keeps_only_what_lies_inside_it(tmp_path):
    pbf = tmp_path / "tiny.osm.pbf"
    _write_tiny_pbf(pbf)
    out = tmp_path / "tiny.index.json"
    OX.build_index_from_pbf(pbf, extract_id="tiny", out=out,
                            keep_tag_keys=OX.DEFAULT_INDEX_TAG_KEYS,
                            bbox=(40.455, -80.03, 40.47, -80.00))   # relation only
    index = OX.ExtractIndex.load(out)
    assert [(e["type"], e["id"]) for e in index.elements] == [("relation", 201)]
    assert json.loads(out.read_text(encoding="utf-8"))["source"]["bbox"] == [40.455, -80.03, 40.47, -80.0]
