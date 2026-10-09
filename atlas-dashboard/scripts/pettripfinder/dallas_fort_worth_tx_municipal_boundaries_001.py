"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phases 3, 4, 5, 8 and 9: MUNICIPALITY AND COUNTY BY PREMISES.

WHY A POSTAL CODE IS NOT ENOUGH IN THIS MARKET
---------------------------------------------
Every earlier market published the municipality its postal code carries. In the Metroplex that is not safe: the
Postal Service names "Dallas" as the preferred city for codes whose land is partly Farmers Branch (75234, 75244),
Addison (75254), Richardson (75243, 75252), Carrollton (75287) or University Park (75205), and "Fort Worth" for codes
that are partly White Settlement (76108), Haltom City (76111, 76117), Forest Hill (76119, 76140), Saginaw / Lake
Worth (76135, 76179), Haslet (76177) or Burleson (76028). A hotel at "XXXX LBJ Freeway, Dallas, TX 75234" can stand
inside the City of Farmers Branch. A mailing label proves nothing about the municipality the premises are in.

THE RULE
--------
A row whose coordinates are known publishes the INCORPORATED PLACE whose Census TIGER/Line 2024 boundary contains
its premises (``place_for_point``); its county is the county whose Census cartographic boundary contains them
(``county_for_point``). A premises inside no incorporated place (unincorporated county land, or a Census-designated
place) keeps its own mailing municipality, and its county is still decided by the polygon. The stated city on a
brand page is evidence, kept on the row, never the decision.

The boundaries are the U.S. Census Bureau's own public files, downloaded once, free, unauthenticated:
  https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_48_place.zip     (Texas places, TIGER/Line 2024)
  https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip  (U.S. counties, 1:500k, 2023)
They are read here with a small pure-Python shapefile reader (polygon records, dBASE attributes) and kept under the
git-ignored ``data/dallas_fort_worth_tx/tiger/``; their SHA-256 is recorded in the report.

A boundary file is IDENTITY GEOGRAPHY, never membership: the corridor registry over the property's own postal code
decides membership (dallas_fort_worth_tx_geography_001). This module decides only which municipality and county an
admitted row publishes, and powers the SUBURBAN HOTELS MISLABELED DALLAS / FORT WORTH = 0 checks.

Output:
  launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_municipal_boundaries_001.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import struct
import sys
import zipfile
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
TIGER_DIR = os.path.join(_DASH, "data", "dallas_fort_worth_tx", "tiger")
PLACE_ZIP = os.path.join(TIGER_DIR, "tl_2024_48_place.zip")
COUNTY_ZIP = os.path.join(TIGER_DIR, "cb_2023_us_county_500k.zip")
REPORT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                      "dallas_fort_worth_tx_municipal_boundaries_001.json")
PLACE_URL = "https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_48_place.zip"
COUNTY_URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
TEXAS_FIPS = "48"
#: The observation window the boundaries are kept for (the Metroplex and its refused ring, generously).
WINDOW = {"min_lat": 31.40, "max_lat": 34.00, "min_lng": -98.40, "max_lng": -95.70}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_dbf(data):
    """dBASE III records as dicts of stripped strings."""
    n_rec, hdr_len, rec_len = struct.unpack("<IHH", data[4:12])
    fields, pos = [], 32
    while data[pos] != 0x0D:
        name = data[pos:pos + 11].split(b"\x00", 1)[0].decode("ascii")
        flen = data[pos + 16]
        fields.append((name, flen))
        pos += 32
    out = []
    for i in range(n_rec):
        base = hdr_len + i * rec_len + 1
        rec, off = {}, base
        for name, flen in fields:
            rec[name] = data[off:off + flen].decode("latin-1").strip()
            off += flen
        out.append(rec)
    return out


def _read_shp(data):
    """Polygon records: list of (bbox, [ring, ...]) with ring = [(lng, lat), ...]."""
    pos, out = 100, []
    while pos < len(data):
        _num, clen = struct.unpack(">II", data[pos:pos + 8])
        rec = data[pos + 8:pos + 8 + clen * 2]
        pos += 8 + clen * 2
        stype = struct.unpack("<i", rec[0:4])[0]
        if stype == 0:
            out.append(None)
            continue
        xmin, ymin, xmax, ymax = struct.unpack("<4d", rec[4:36])
        nparts, npoints = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack("<%di" % nparts, rec[44:44 + 4 * nparts]))
        pts_off = 44 + 4 * nparts
        pts = struct.unpack("<%dd" % (2 * npoints), rec[pts_off:pts_off + 16 * npoints])
        rings = []
        for k in range(nparts):
            a = parts[k]
            b = parts[k + 1] if k + 1 < nparts else npoints
            rings.append([(pts[2 * j], pts[2 * j + 1]) for j in range(a, b)])
        out.append(((xmin, ymin, xmax, ymax), rings))
    return out


def _load_layer(zpath, stem_suffix):
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        shp = next(n for n in names if n.endswith(stem_suffix + ".shp"))
        dbf = shp[:-4] + ".dbf"
        return _read_shp(zf.read(shp)), _read_dbf(zf.read(dbf))


def _in_window(bbox):
    xmin, ymin, xmax, ymax = bbox
    w = WINDOW
    return not (xmax < w["min_lng"] or xmin > w["max_lng"] or ymax < w["min_lat"] or ymin > w["max_lat"])


def _point_in_rings(lng, lat, rings):
    inside = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > lat) != (yj > lat):
                x_cross = xi + (lat - yi) * (xj - xi) / (yj - yi)
                if lng < x_cross:
                    inside = not inside
            j = i
    return inside


class Boundaries:
    """Texas places and the window's counties, loaded once."""

    def __init__(self):
        shapes, attrs = _load_layer(PLACE_ZIP, "_place")
        self.places = []
        for shp, a in zip(shapes, attrs):
            if shp and _in_window(shp[0]):
                self.places.append((shp[0], shp[1], a))
        shapes, attrs = _load_layer(COUNTY_ZIP, "_county_500k")
        self.counties = []
        for shp, a in zip(shapes, attrs):
            if shp and a.get("STATEFP") == TEXAS_FIPS and _in_window(shp[0]):
                self.counties.append((shp[0], shp[1], a))

    @staticmethod
    def _hit(rows, lat, lng):
        hits = []
        for bbox, rings, a in rows:
            if bbox[0] <= lng <= bbox[2] and bbox[1] <= lat <= bbox[3] and _point_in_rings(lng, lat, rings):
                hits.append(a)
        return hits

    def place_for_point(self, lat, lng):
        """(incorporated place name, LSAD class) or ("", "") when the premises are in no incorporated place. A
        Census-designated place (CLASSFP U1 / U2) is not a municipality and is returned as ("", "CDP:<name>")."""
        if lat is None or lng is None:
            return "", ""
        hits = self._hit(self.places, float(lat), float(lng))
        inc = [a for a in hits if not a.get("CLASSFP", "").startswith("U")]
        if inc:
            return inc[0]["NAME"], inc[0].get("CLASSFP", "")
        cdp = [a for a in hits if a.get("CLASSFP", "").startswith("U")]
        if cdp:
            return "", "CDP:" + cdp[0]["NAME"]
        return "", ""

    def county_for_point(self, lat, lng):
        if lat is None or lng is None:
            return ""
        hits = self._hit(self.counties, float(lat), float(lng))
        return hits[0]["NAME"] if hits else ""


_BOUNDARIES = None


def boundaries():
    global _BOUNDARIES
    if _BOUNDARIES is None:
        _BOUNDARIES = Boundaries()
    return _BOUNDARIES


def place_for_point(lat, lng):
    return boundaries().place_for_point(lat, lng)


def county_for_point(lat, lng):
    return boundaries().county_for_point(lat, lng)


#: Fixed probes: landmarks whose municipality and county are public record. The module refuses to report if any
#: probe is answered wrongly, so a broken reader can never label a suburb.
PROBES = [
    ("Reunion Tower (Dallas)", 32.7755, -96.8089, "Dallas", "Dallas"),
    ("Sundance Square (Fort Worth)", 32.7530, -97.3320, "Fort Worth", "Tarrant"),
    ("AT&T Stadium (Arlington)", 32.7473, -97.0945, "Arlington", "Tarrant"),
    ("Gaylord Texan (Grapevine)", 32.9440, -97.0700, "Grapevine", "Tarrant"),
    ("Legacy West (Plano)", 33.0780, -96.8270, "Plano", "Collin"),
    ("The Star (Frisco)", 33.1100, -96.8290, "Frisco", "Collin"),
    ("Las Colinas Urban Center (Irving)", 32.8770, -96.9440, "Irving", "Dallas"),
    ("Addison Circle (Addison)", 32.9580, -96.8290, "Addison", "Dallas"),
    ("Fort Worth Stockyards (Fort Worth)", 32.7890, -97.3470, "Fort Worth", "Tarrant"),
    ("Dallas Love Field terminal (Dallas)", 32.8460, -96.8510, "Dallas", "Dallas"),
]


def build():
    b = boundaries()
    probes, failures = [], []
    for name, lat, lng, want_place, want_county in PROBES:
        got_place, klass = b.place_for_point(lat, lng)
        got_county = b.county_for_point(lat, lng)
        ok = got_place == want_place and got_county == want_county
        probes.append(OrderedDict([("probe", name), ("lat", lat), ("lng", lng), ("place", got_place),
                                   ("class", klass), ("county", got_county), ("expected_place", want_place),
                                   ("expected_county", want_county), ("ok", ok)]))
        if not ok:
            failures.append(name)
    if failures:
        raise SystemExit("municipal boundary probes failed: %s" % failures)
    return OrderedDict([
        ("schema", "ptf-municipal-boundaries/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "3 + 4 + 5 + 8 + 9 -- municipality and county decided by the premises' coordinates"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 2),
        ("sources", [
            OrderedDict([("layer", "Texas places (TIGER/Line 2024)"), ("url", PLACE_URL),
                         ("sha256", _sha256(PLACE_ZIP)), ("bytes", os.path.getsize(PLACE_ZIP)),
                         ("places_in_window", len(b.places))]),
            OrderedDict([("layer", "U.S. counties (cartographic boundary 1:500k, 2023)"), ("url", COUNTY_URL),
                         ("sha256", _sha256(COUNTY_ZIP)), ("bytes", os.path.getsize(COUNTY_ZIP)),
                         ("texas_counties_in_window", len(b.counties))]),
        ]),
        ("rule", "A row with coordinates publishes the incorporated place whose boundary contains its premises and the "
                 "county whose boundary contains them; a premises in no incorporated place keeps its own mailing "
                 "municipality. A brand's or a register's stated city is evidence, never the decision."),
        ("probes", probes),
        ("probes_passed", len(probes) - len(failures)),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    rep = build()
    for p in rep["probes"]:
        print("%-38s %-14s %-10s %s" % (p["probe"], p["place"], p["county"], "OK" if p["ok"] else "FAIL"))
    if args.write:
        with open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rep, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("WROTE", os.path.relpath(REPORT, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
