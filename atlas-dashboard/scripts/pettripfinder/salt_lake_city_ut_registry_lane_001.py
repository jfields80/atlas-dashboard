"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phase 11: the Utah / Salt Lake City lodging-register lane, MEASURED.

WHAT WAS LOOKED FOR
-------------------
The order's census asks for "Utah/local lodging inventories". This lane measures whether the Salt Lake City / Park
City market has a PROPERTY-LEVEL public register -- a row per lodging premises with its own street address -- and
records what answered.

WHAT WAS MEASURED (2026-10-07, free, read-only)
-----------------------------------------------
  * opendata.utah.gov -- no longer a Socrata domain: the Socrata catalog answers "Domain not found:
    opendata.utah.gov" and the host itself answers HTTP 400. The State publishes no lodging licence list.
  * ArcGIS Hub (the platform Salt Lake City, Salt Lake County and UGRC publish on) -- searched for Salt Lake City and
    Park City business licences and Utah hotels: no business-licence or lodging register is published. The only
    lodging layer is UGRC's "Utah Open Source Places", which is DERIVED FROM OpenStreetMap -- not an independent
    lane, and already read first-hand by salt_lake_city_ut_osm_lane_001.
  * Utah's transient-room-tax and sales-tax licences (Utah State Tax Commission), the Salt Lake County Health
    Department's lodging inspections and Summit County / Park City nightly-rental licences publish no open bulk
    list.

So this market has NO open property-level lodging register. The census is built from the independent lanes
(OpenStreetMap, the brands' own inventories, Visit Salt Lake and Visit Park City, Places, the property pages and the
competitor challenge). The lane is kept, with zero leads, so the census reader and the source accounting state the
measurement instead of omitting it.

Output:
  launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_registry_lane_001.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
MARKET_ID = "salt-lake-city-ut"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "salt_lake_city_ut_registry_lane_001.json")

MEASURED = [
    OrderedDict([("surface", "https://api.us.socrata.com/api/catalog/v1?domains=opendata.utah.gov"),
                 ("answered", "HTTP 200 {\"error\":\"Domain not found: opendata.utah.gov\"}"),
                 ("verdict", "NO_SOCRATA_CATALOG")]),
    OrderedDict([("surface", "https://opendata.utah.gov/"), ("answered", "HTTP 400"),
                 ("verdict", "NO_OPEN_DATA_PORTAL_ANSWERING")]),
    OrderedDict([("surface", "https://hub.arcgis.com/api/search/v1/collections/dataset/items?q=salt lake city "
                             "business licenses / park city business license / utah hotels / salt lake county "
                             "business"),
                 ("answered", "no Utah business-licence or lodging register; UGRC 'Utah Open Source Places' "
                              "(services1.arcgis.com/99lidPhWCzftIe9K/.../OpenSourcePlaces) is an OpenStreetMap "
                              "derivative"),
                 ("verdict", "NO_INDEPENDENT_REGISTER")]),
    OrderedDict([("surface", "Utah State Tax Commission transient-room-tax licences; Salt Lake County Health "
                             "Department lodging inspections; Summit County / Park City nightly-rental licences"),
                 ("answered", "no open bulk list published"),
                 ("verdict", "NOT_PUBLISHED")]),
]


def build():
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "11 -- the Utah / Salt Lake City lodging-register lane, measured"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 7),
        ("property_level_register_exists", False),
        ("measured", MEASURED),
        ("consequence", "No register row exists to read. The census is built from the independent lanes; no "
                        "row is admitted or refused on a register's evidence in this market."),
        ("leads", []),
        ("lead_count", 0),
    ])


def main(argv=None):
    rep = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("register exists:", rep["property_level_register_exists"], "leads:", rep["lead_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
