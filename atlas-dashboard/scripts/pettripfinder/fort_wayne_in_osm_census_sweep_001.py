"""PTF-FORT-WAYNE-IN-NEW-MARKET-001 -- Phase 4A/4B (OSM / Overpass lane).

Zero-cost lodging sweep of the Fort Wayne market from OpenStreetMap, through
the public Overpass API.

Why one bbox rather than fifteen cell queries. The committed discovery
configuration declares fifteen cells, and the per-cell path exists so a market
whose geography is large or disjoint can be answered in pieces. Fort Wayne's
whole approved geography is a single 0.34 x 0.45 degree box that Overpass
answers in under three seconds per tag, and fifteen bounded-radius queries over
the same territory would be fifteen times the load on a public server for a
strict subset of the same elements. The cells stay the market's published
taxonomy; this lane answers the whole box once per lodging tag and lets the
membership test place each element.

Politeness: one endpoint, concurrency 1, spacing between queries, and a retry
that BACKS OFF rather than hammers -- the first run of this sweep took a 429 on
its fourth tag, which is the server saying slow down and not an error to paper
over.

OSM is a community map. It is IDENTITY EVIDENCE OF VARYING QUALITY and never
policy evidence: an element's tags may be stale, a hotel may be missing
entirely (the Fort Wayne sweep carries no element for several properties the
brand sitemaps and the CVB both list), and ``addr:*`` may disagree with the
property's own page. Nothing here admits a row on its own.

Output:
  launch_packages/pettripfinder/markets/reports/fort_wayne_in_osm_census_sweep_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.discovery import constants as C  # noqa: E402
from scripts.pettripfinder.discovery.market_config import load_market_config  # noqa: E402

WORK_ORDER = "PTF-FORT-WAYNE-IN-NEW-MARKET-001"
MARKET_ID = "fort-wayne-in"
SCHEMA = "ptf-osm-census-sweep/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")

ENDPOINT = C.OVERPASS_DEFAULT_ENDPOINT
UA = C.OVERPASS_USER_AGENT
ATTRIBUTION = C.OVERPASS_ATTRIBUTION
SPACING_SECONDS = 3.0
BACKOFF_SECONDS = 45.0
MAX_ATTEMPTS = 3

#: The lodging tags this product's census may contain. tourism=apartment and
#: tourism=chalet are deliberately absent: they are short-term-rental shapes,
#: not the hotel category, and admitting them by tag would put OUT_OF_CATEGORY
#: rows into a census that is supposed to be hotels.
TAGS = ("tourism=hotel", "tourism=motel", "tourism=guest_house", "tourism=hostel")


def post(query, timeout=90):
    data = ("data=" + urllib.parse.quote(query)).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, headers={
        "User-Agent": UA, "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))


def build_ql(tag, bbox):
    key, _, value = tag.partition("=")
    filt = "[%s=%s]" % (key, value) if value else "[%s]" % key
    south, west, north, east = bbox
    bbox_str = "%.6f,%.6f,%.6f,%.6f" % (south, west, north, east)
    return ("[out:json][timeout:%d];(node%s(%s);way%s(%s);relation%s(%s););out center;"
            ) % (C.OVERPASS_QL_TIMEOUT_SECONDS, filt, bbox_str, filt, bbox_str,
                 filt, bbox_str)


def sweep(bbox, stats):
    elements = OrderedDict()
    per_tag = []
    for tag in TAGS:
        outcome = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            time.sleep(SPACING_SECONDS)
            t0 = time.time()
            try:
                st, payload = post(build_ql(tag, bbox))
                stats["requests"] += 1
                els = payload.get("elements", [])
                for e in els:
                    elements["%s/%s" % (e.get("type"), e.get("id"))] = e
                outcome = OrderedDict([("tag", tag), ("status", st),
                                       ("elements", len(els)), ("attempts", attempt),
                                       ("seconds", round(time.time() - t0, 1))])
                break
            except urllib.error.HTTPError as exc:
                stats["requests"] += 1
                outcome = OrderedDict([("tag", tag), ("status", exc.code),
                                       ("elements", 0), ("attempts", attempt),
                                       ("seconds", round(time.time() - t0, 1))])
                if exc.code == 429 and attempt < MAX_ATTEMPTS:
                    print("  %s: 429, backing off %.0fs" % (tag, BACKOFF_SECONDS),
                          flush=True)
                    time.sleep(BACKOFF_SECONDS)
                    continue
                break
            except Exception as exc:  # noqa: BLE001
                stats["requests"] += 1
                outcome = OrderedDict([("tag", tag), ("status", "ERR:" + type(exc).__name__),
                                       ("elements", 0), ("attempts", attempt),
                                       ("seconds", round(time.time() - t0, 1))])
                break
        per_tag.append(outcome)
        print(" ", json.dumps(outcome), flush=True)
    return elements, per_tag


def to_row(element):
    t = element.get("tags") or {}
    lat = element.get("lat")
    lng = element.get("lon")
    if lat is None:
        centre = element.get("center") or {}
        lat = centre.get("lat")
        lng = centre.get("lon")
    house = (t.get("addr:housenumber") or "").strip()
    street = (t.get("addr:street") or "").strip()
    return OrderedDict([
        ("osm_id", "%s/%s" % (element.get("type"), element.get("id"))),
        ("name", (t.get("name") or "").strip()),
        ("tourism", (t.get("tourism") or "").strip()),
        ("brand", (t.get("brand") or t.get("operator") or "").strip()),
        ("street", (house + " " + street).strip()),
        ("city", (t.get("addr:city") or "").strip()),
        ("state", (t.get("addr:state") or "").strip()),
        ("postal_code", (t.get("addr:postcode") or "").strip()[:5]),
        ("phone", (t.get("phone") or t.get("contact:phone") or "").strip()),
        ("website", (t.get("website") or t.get("contact:website") or "").strip()),
        ("latitude", lat), ("longitude", lng),
    ])


def build(args):
    market = load_market_config(MARKET_ID)
    b = market.bounds
    bbox = (b.min_lat, b.min_lng, b.max_lat, b.max_lng)
    stats = {"requests": 0}
    print("sweeping", MARKET_ID, bbox, flush=True)
    elements, per_tag = sweep(bbox, stats)
    rows = [to_row(e) for e in elements.values()]
    rows.sort(key=lambda r: (r["city"], r["postal_code"], r["name"]))
    named = [r for r in rows if r["name"]]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4A/4B -- new-market shadow census, OSM/Overpass lane"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "OpenStreetMap via the public Overpass API"),
        ("attribution", ATTRIBUTION),
        ("endpoint", ENDPOINT),
        ("bounds", OrderedDict([("min_lat", b.min_lat), ("min_lng", b.min_lng),
                                ("max_lat", b.max_lat), ("max_lng", b.max_lng)])),
        ("what_this_is",
         "One bounded Overpass sweep per lodging tag over the committed market "
         "geography's whole bounding box. IDENTITY EVIDENCE ONLY, of varying "
         "quality: OSM tags may be stale, absent or in disagreement with the "
         "property's own page, and this lane admits nothing by itself. "
         "tourism=apartment and tourism=chalet are deliberately not swept -- they "
         "are short-term-rental shapes rather than the hotel category."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("tags_swept", per_tag),
        ("counts", OrderedDict([
            ("elements", len(rows)),
            ("named", len(named)),
            ("unnamed", len(rows) - len(named)),
            ("by_tourism", OrderedDict(sorted(Counter(r["tourism"] for r in rows).items()))),
            ("by_city", OrderedDict(sorted(Counter(r["city"] or "(none)" for r in rows).items()))),
            ("by_postal", OrderedDict(sorted(Counter(r["postal_code"] or "(none)" for r in rows).items()))),
            ("with_street", sum(1 for r in rows if r["street"])),
            ("with_phone", sum(1 for r in rows if r["phone"])),
            ("with_website", sum(1 for r in rows if r["website"])),
        ])),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "fort_wayne_in_osm_census_sweep_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
