"""PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001 -- Phase 9: the Minnesota / Twin Cities lodging-register lane, MEASURED.

WHAT WAS LOOKED FOR
-------------------
The order's census asks for "Minnesota/local lodging inventories". Seattle had one (the City of Seattle's active
business-licence certificates on data.seattle.gov, with NAICS codes and street addresses). This lane measures whether
the Twin Cities has an equivalent PROPERTY-LEVEL public register -- a row per lodging premises with its own street
address -- and records the answer.

WHAT WAS MEASURED (2026-10-04, free, read-only)
-----------------------------------------------
  * opendata.minneapolismn.gov (ArcGIS Hub search API, queries "hotel", "lodging", "food license", "business
    license", "license"): no lodging dataset. The licence datasets are On_Sale_Liquor, Off_Sale_Liquor, trade
    licences and Active_Rental_Licenses (RESIDENTIAL rental licences -- never a hotel register).
  * information.stpaul.gov (ArcGIS Hub search API, queries "license", "hotel", "lodging"): Liquor Licenses, building
    and demolition permits, vacant buildings and housing production. No lodging dataset; the domain is not a Socrata
    domain (the Socrata catalog answers "Domain not found").
  * Socrata catalog (all domains, "minnesota lodging license"): no Minnesota register.
  * ArcGIS Hub global search ("minneapolis business licenses"): no Twin Cities lodging register (other cities only).
  * Minnesota Department of Health, Food, Pools, and Lodging Services licensing page: informational, with no bulk
    list or open dataset. Lodging licensing in Minneapolis, St. Paul and Bloomington is delegated to the city health
    agencies, none of which publishes an open register.

THE ANSWER
----------
NO PROPERTY-LEVEL PUBLIC LODGING REGISTER EXISTS for this market. A liquor licence is not a lodging register (it
names restaurants and bars, and a hotel's licence is often held by its restaurant operator under another name), so
it is not read as one. The census is built from the independent lanes that do exist -- OpenStreetMap (the Minnesota
extract), the committed national brand inventory, the brands' own city pages and sitemaps, the destination
organisations (Meet Minneapolis, Visit Saint Paul, Bloomington / Mall of America and the suburban bureaus), Google
Places identity verification, the property pages themselves and the competitor gap challenge -- so no single
inventory carries it. The census reader finds this report with ZERO leads and adds no REGISTRY_LICENCE observation.

Output:
  launch_packages/pettripfinder/markets/reports/minneapolis_mn_registry_lane_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001"
MARKET_ID = "minneapolis-mn"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "minneapolis_mn_registry_lane_001.json")

#: (portal, query or dataset, what answered, why it is not a property register)
MEASUREMENTS = [
    ("opendata.minneapolismn.gov (ArcGIS Hub search API)", "q=hotel / q=lodging", "no dataset", "nothing to read"),
    ("opendata.minneapolismn.gov (ArcGIS Hub search API)", "q=license / q=business license / q=food license",
     "On_Sale_Liquor, Off_Sale_Liquor, trade licences, Active_Rental_Licenses, Public_311_*",
     "liquor and trade licences are not lodging registers; Active_Rental_Licenses are RESIDENTIAL rental licences"),
    ("information.stpaul.gov (ArcGIS Hub search API)", "q=license / q=hotel / q=lodging", "Liquor Licenses, "
     "building / demolition permits, vacant buildings, housing production", "no lodging dataset"),
    ("Socrata catalog (all domains)", "q=minnesota lodging license", "no dataset", "no Minnesota register"),
    ("hub.arcgis.com global search", "q=minneapolis business licenses", "other cities' licence layers only",
     "no Twin Cities lodging register"),
    ("health.state.mn.us Food, Pools, and Lodging Services licensing page", "GET (plain client)", "HTTP 200, an "
     "informational page", "no bulk list or open dataset; lodging licensing in Minneapolis, St. Paul and Bloomington "
     "is delegated to the city health agencies"),
]


def build():
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9 -- the Minnesota / Twin Cities lodging-register lane: MEASURED, NONE EXISTS"),
        ("register_exists", False),
        ("measured_on", "2026-10-04"),
        ("measurements", [OrderedDict([("portal", p), ("query", q), ("answered", a), ("why_not_a_register", w)])
                          for p, q, a, w in MEASUREMENTS]),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 14),
        ("what_replaces_it",
         "OpenStreetMap (the Minnesota extract), the committed national brand inventory, the brands' own city "
         "pages and sitemaps, the destination organisations, Google Places identity verification inside the free "
         "allowance, the property pages themselves and the competitor gap challenge."),
        ("accommodation_rows", 0),
        ("lead_rows", 0),
        ("leads_in_admitted_postal_codes", 0),
        ("leads_by_corridor", OrderedDict()),
        ("leads_refused_by_their_own_postal_code", 0),
        ("leads_refused_by_future_market", OrderedDict()),
        ("leads_without_trade_name", 0),
        ("short_term_rental_and_other_rows_counted_not_leads", 0),
        ("pages", []),
        ("leads", []),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("register_exists=%s measurements=%d leads=%d" % (rep["register_exists"], len(rep["measurements"]),
                                                          rep["lead_rows"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
