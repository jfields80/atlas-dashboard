"""PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001 -- Phase 10: the Oregon / Washington lodging-register lane, MEASURED.

WHAT WAS LOOKED FOR
-------------------
The order's census asks for "Oregon/local lodging inventories" and "Washington sources where evaluating Vancouver".
Seattle had one (the City of Seattle's active business-licence certificates on data.seattle.gov, with NAICS codes and
street addresses). This lane measures whether Portland has an equivalent PROPERTY-LEVEL public register -- a row per
lodging premises with its own street address -- and records the answer.

WHAT WAS MEASURED (2026-10-03, free, read-only)
-----------------------------------------------
  * data.oregon.gov (Socrata catalog, queries "lodging", "hotel"): the only lodging datasets are the Oregon
    Department of Revenue's STATE TRANSIENT LODGING TAX RETURN STATISTICS (``8prr-d4xq`` by accommodation type,
    ``mf7n-egve`` by region) -- AGGREGATE tax statistics with no premises, no name and no address. Not a register.
  * data.orcities.org ``xvs2-d76x`` "Transient Lodging Tax Revenues" -- city-level revenue totals. Not a register.
  * Socrata-wide catalog ("transient lodging portland", "traveler's accommodation"): no Oregon or Clark County
    property register on any portal.
  * Oregon traveller-accommodation licensing is delegated to the counties (OAR 333-029); Multnomah County's
    inspection portal (inspections.myhealthdepartment.com/multnomah) answered a plain client 403 Forbidden. It is an
    interactive search behind an access control, not an open register, and this order does not work around access
    controls.
  * Washington: the Department of Health "Transient Accommodations" listing (data.wa.gov ``9vm5-7kxk``) was measured
    by the Seattle order as last updated 2018-03-12 and non-tabular; the City of Vancouver publishes no business
    licence register on an open portal.

THE ANSWER
----------
NO PROPERTY-LEVEL PUBLIC LODGING REGISTER EXISTS for this market. The census is built from the independent lanes that
do exist -- OpenStreetMap (both state extracts), the committed national brand inventory, the brands' own city pages
and sitemaps, the destination organisations (Travel Portland, Explore Washington County, Visit Vancouver USA and the
county bureaus), Google Places identity verification, the property pages themselves and the competitor gap
challenge -- so no single inventory carries it. The census reader finds this report with ZERO leads and adds no
REGISTRY_LICENCE observation.

Output:
  launch_packages/pettripfinder/markets/reports/portland_or_registry_lane_001.json
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

WORK_ORDER = "PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001"
MARKET_ID = "portland-or"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "portland_or_registry_lane_001.json")

#: (portal, query or dataset, what answered, why it is not a property register)
MEASUREMENTS = [
    ("data.oregon.gov catalog", "q=lodging", "8prr-d4xq State Transient Lodging Tax Return Statistics by "
     "Accommodation Type; mf7n-egve ... by Region", "aggregate tax statistics -- no premises, name or address"),
    ("data.oregon.gov catalog", "q=hotel", "no dataset", "nothing to read"),
    ("Socrata catalog (all domains)", "q=transient lodging portland", "data.orcities.org xvs2-d76x Transient Lodging "
     "Tax Revenues", "city-level revenue totals -- no premises"),
    ("Socrata catalog (all domains)", "q=traveler's accommodation", "Nova Scotia / New Brunswick datasets only",
     "no Oregon or Washington register"),
    ("inspections.myhealthdepartment.com/multnomah", "GET (plain client)", "HTTP 403 Forbidden",
     "interactive county inspection search behind an access control; not an open register and not worked around"),
    ("data.wa.gov 9vm5-7kxk (measured by PTF-SEATTLE-WA-HARDENED-SOURCE-READY-001)", "Transient Accommodations "
     "(Lodging)", "updated 2018-03-12, non-tabular", "stale and not a tabular register"),
]


def build():
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "10 -- the Oregon / Washington lodging-register lane: MEASURED, NONE EXISTS"),
        ("register_exists", False),
        ("measured_on", "2026-10-03"),
        ("measurements", [OrderedDict([("portal", p), ("query", q), ("answered", a), ("why_not_a_register", w)])
                          for p, q, a, w in MEASUREMENTS]),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 6),
        ("what_replaces_it",
         "OpenStreetMap (Oregon + Washington extracts), the committed national brand inventory, the brands' own city "
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
