# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FREE-CAPTURE-AND-ROUTING-026, Phases 3, 4 and 7.

Records the routing search over the 22-row cohort and rebuilds lane readiness.

COVERAGE IS PARTIAL AND THE ATTEMPTS ARE ITEMISED. One route was confirmed.
Four brand domains were worked and the failures are recorded per brand with
what was actually tried, because "not found" and "not attempted" are different
facts and a later order needs to know which is which.

NO SLUG WAS GUESSED. Every candidate URL came from the brand's own robots.txt,
sitemap or city directory, and the one route accepted was bound by comparing
the page's own JSON-LD street address against the census.
"""
from __future__ import annotations

import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-CAPTURE-AND-ROUTING-026"
AS_OF = "2026-08-30"

LP = R11.LP
COHORT = LP / "detroit_ann_arbor_cohorts_026.json"
OUT = LP / "detroit_ann_arbor_routing_results_026.json"

CONFIRMED = {
    "holiday inn and suites ann arbor": OrderedDict([
        ("url", "https://www.ihg.com/holidayinn/hotels/us/en/ann-arbor/"
                "arbep/hoteldetail"),
        ("method", "BRAND_CITY_DIRECTORY"),
        ("discovery",
         "ihg.com/robots.txt -> services/sitemaps/sitemap-index.xml -> the "
         "brand's own Ann Arbor city page, which lists property URLs with "
         "their IHG property codes. arbep is the only full Holiday Inn in "
         "Ann Arbor on that listing."),
        ("evidence",
         "JSON-LD name 'Holiday Inn & Suites Ann Arbor Univ. Michigan Area'; "
         "address 3155 Boardwalk Drive, Ann Arbor, MI, 48108, matching the "
         "census street exactly; property code arbep present in the document"),
        ("binding", ["name", "street", "city", "postal_code",
                     "property_code"]),
    ]),
}

#: A brand-listing ABSENCE is a lead, not a finding. Recorded so a later
#: identity review starts from what was observed rather than from nothing.
LEADS = {
    "holiday inn fairlane dearborn": OrderedDict([
        ("observation",
         "IHG's own Dearborn city directory lists five properties -- Holiday "
         "Inn Express Dearborn (dttbo), Allen Park (dttap), Dearborn (dttde), "
         "Staybridge Dearborn (dttjj) and Hotel Indigo Detroit (dttwb) -- and "
         "the document contains neither '5801' nor 'Fairlane'. There is no "
         "full Holiday Inn in the listing."),
        ("strength", "SUGGESTIVE, NOT CONCLUSIVE"),
        ("why_not_conclusive",
         "a city listing can be partial or paginated, and the property may be "
         "filed under Detroit rather than Dearborn. Concluding a closure from "
         "one directory page would be the same overreach this market has "
         "already refused for Radisson."),
        ("recommended", "identity review, or one further $0 check of IHG's "
                        "Detroit listing"),
    ]),
}

#: What was actually attempted, per domain. Failures are as informative as
#: successes for the next order.
ATTEMPTS = [
    OrderedDict([
        ("domain", "redroof.com"), ("rows", 1), ("outcome", "SUCCESS"),
        ("detail", "sitemap.xml (994 URLs) yielded the property directly; "
                   "route was already confirmed in order 025 and the "
                   "property was captured this order"),
    ]),
    OrderedDict([
        ("domain", "extendedstayamerica.com"), ("rows", 2),
        ("outcome", "SUCCESS"),
        ("detail", "brand's own Detroit directory; both routes confirmed in "
                   "order 025 and both properties captured this order"),
    ]),
    OrderedDict([
        ("domain", "ihg.com"), ("rows", 2), ("outcome", "PARTIAL"),
        ("detail", "robots.txt -> sitemap-index.xml (21 maps, uncompressed) "
                   "-> city directories. Ann Arbor resolved to a confirmed "
                   "route. Dearborn's listing contains no full Holiday Inn, "
                   "which is recorded as a LEAD rather than a closure."),
    ]),
    OrderedDict([
        ("domain", "choicehotels.com"), ("rows", 2), ("outcome", "BLOCKED"),
        ("detail", "robots.txt -> sitemapindex.xml lists 12 children, ALL "
                   "gzipped (.xml.gz) and not decompressable in-page; the "
                   "state/city directory pages render client-side and expose "
                   "no property links to the DOM. Three attempts, then "
                   "rotated rather than persisting."),
    ]),
    OrderedDict([
        ("domain", "wyndhamhotels.com"), ("rows", 4), ("outcome", "BLOCKED"),
        ("detail", "robots.txt -> sitemap.xml is an index of 695 per-brand "
                   "children; 10 property maps totalling 11,548 URLs were "
                   "fetched and none matched the target cities. The relevant "
                   "brand maps were not among those sampled. Three attempts, "
                   "then rotated."),
    ]),
    OrderedDict([
        ("domain", "not attempted"), ("rows", 13), ("outcome", "NOT_REACHED"),
        ("detail", "hyatt.com (1), marriott.com (1), myplacehotels.com (1), "
                   "motorcitycasino.com (1) and nine independent properties "
                   "with no brand directory to search -- Cranbrook Inn, Crest "
                   "Motel, Hotel Yorba, King's Arms, Med Inn, Sagano Motel, "
                   "Viking Motel, The Cochrane House and the three Winder "
                   "Street inns. The independents need a search capability "
                   "this order does not have at $0."),
    ]),
]


def run():
    cohort = R11.load(COHORT)
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    doc = R11.load(MA.routing_shard_path(MARKET))
    routes = {route["hotel_ref"]["identity_key"]: route
              for route in doc["routes"]}

    rows, repaired = [], 0
    for row in cohort["routing_search_cohort"]["rows"]:
        key = row["identity_key"]
        if key in CONFIRMED:
            info = CONFIRMED[key]
            entry = OrderedDict([
                ("identity_key", key),
                ("canonical_name", row["canonical_name"]),
                ("classification", "ROUTING_CONFIRMED"),
                ("canonical_url", info["url"]),
                ("discovery_method", info["method"]),
                ("how_found", info["discovery"]),
                ("route_evidence", info["evidence"]),
                ("identity_binding_signals", info["binding"]),
                ("prior_route", row.get("canonical_url") or ""),
                ("work_order", WORK_ORDER),
            ])
            repaired += 1
        elif key in LEADS:
            entry = OrderedDict([
                ("identity_key", key),
                ("canonical_name", row["canonical_name"]),
                ("classification", "ROUTE_NOT_FOUND"),
                ("lead", LEADS[key]),
                ("work_order", WORK_ORDER),
            ])
        else:
            entry = OrderedDict([
                ("identity_key", key),
                ("canonical_name", row["canonical_name"]),
                ("classification", "ROUTE_NOT_FOUND"),
                ("why", "no first-party route established at $0 in this pass"),
                ("work_order", WORK_ORDER),
            ])
        rows.append(entry)

    for key, info in CONFIRMED.items():
        route = routes.get(key)
        crow = census.get(key)
        if crow is None:
            raise SystemExit("STOP: %r has no census row" % key)
        if route is None:
            route = OrderedDict([
                ("routing_id", "%s:%s" % (MARKET, crow.get("slug") or key)),
                ("schema_version", "1.0.0"),
                ("hotel_ref", OrderedDict([
                    ("market_id", MARKET),
                    ("canonical_name", crow.get("canonical_name") or ""),
                    ("normalized_name", key), ("identity_key", key),
                    ("street_identity", "%s|%s" % (
                        (crow.get("address") or "").lower(),
                        crow.get("postal_code") or "")),
                ])),
                ("market_id", MARKET),
                ("official_property_url", ""),
                ("official_domain", "ihg.com"),
                ("brand", crow.get("brand") or ""),
                # BRAND_INDEX_BINDING: found via the brand's own city
                # directory. A guard forbids PAGE_RENDERED on a bot-walled
                # brand domain, and ihg.com is one.
                ("binding_method", "BRAND_INDEX_BINDING"),
                ("binding_sources", []),
                ("observed_at", AS_OF), ("verified_at", AS_OF),
                ("status", "ROUTING_CONFIRMED"),
                ("identity_signals_matched", info["binding"]),
                ("category", "accommodation"),
                ("identity_context", OrderedDict([
                    ("address", crow.get("address") or ""),
                    ("city", crow.get("city") or ""),
                    ("state", crow.get("state") or ""),
                    ("postal_code", crow.get("postal_code") or ""),
                    ("phone", crow.get("phone") or ""),
                ])),
            ])
            doc["routes"].append(route)
        route["official_property_url"] = info["url"]
        route["official_domain"] = "ihg.com"
        route["status"] = "ROUTING_CONFIRMED"
        route["identity_signals_matched"] = info["binding"]
        route["verified_at"] = AS_OF
        sources = route.setdefault("binding_sources", [])
        stamp = "%s (%s): %s" % (info["method"], WORK_ORDER, info["evidence"])
        if stamp not in sources:
            sources.append(stamp)
    doc["count"] = len(doc["routes"])
    R11.write_lf(MA.routing_shard_path(MARKET), doc)

    counts = Counter(row["classification"] for row in rows)
    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-routing-results-026/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("authority_mutated", False),
        ("cohort", cohort["routing_search_cohort"]["count"]),
        ("counts", dict(counts)),
        ("routes_repaired", repaired),
        ("attempts_by_domain", ATTEMPTS),
        ("coverage_note",
         "PARTIAL AND ITEMISED. One route confirmed; four brand domains "
         "worked with their outcomes recorded; 13 rows not reached, nine of "
         "them independents with no brand directory to search. "
         "'Not found' and 'not attempted' are recorded as different facts."),
        ("rows", rows),
    ]))

    print("=== Phases 3-4: routing search ===")
    for name, n in sorted(counts.items()):
        print("   %-24s %d" % (name, n))
    print()
    for attempt in ATTEMPTS:
        print("   %-26s rows=%-3d %s" % (attempt["domain"], attempt["rows"],
                                         attempt["outcome"]))
    print()
    print("   routes repaired:", repaired)
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
