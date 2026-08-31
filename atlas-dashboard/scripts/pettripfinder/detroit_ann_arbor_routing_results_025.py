# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-025, Phases 4 to 8.

Records the routing determinations reached at $0 and writes the repaired
routes into the Detroit routing shard.

ROUTING ONLY. No policy is captured, no authority record is written, no
exclusion is touched. Several of these pages were open in front of me with
their pet policies on them and none of that was read: the whole point of
separating routing from acquisition is that the next acquisition cohort is
mechanically clean, and a route confirmed while quietly harvesting policy
would defeat it.

EVERY CONFIRMED ROUTE IS BOUND BY ADDRESS, NOT BY NAME. A URL containing a
hotel's name proves nothing -- this market has already been burned by a routed
domain that resolved to an online-gambling site. Each route below was opened
and its own structured data compared against the census street address, and in
most cases the phone as well.
"""
from __future__ import annotations

import json
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
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-025"
AS_OF = "2026-08-30"

LP = R11.LP
COHORT = LP / "detroit_ann_arbor_routing_cohort_025.json"
SCREEN = LP / "detroit_ann_arbor_routing_identity_screen_025.json"
OUT = LP / "detroit_ann_arbor_routing_results_025.json"

#: Verified at $0 this pass. Each was opened; the page's own JSON-LD street
#: address was compared against the census row before it was accepted.
CONFIRMED = {
    "courtyard detroit metro airport romulus": OrderedDict([
        ("url", "https://www.marriott.com/en-us/hotels/"
                "dtwca-courtyard-detroit-metro-airport-romulus/overview/"),
        ("prior_url", "https://www.marriott.com/hotels/travel/"
                      "dtwca-courtyard-detroit-metro-airport-romulus"),
        ("method", "DETERMINISTIC_BRAND_TEMPLATE"),
        ("evidence", "JSON-LD name 'Courtyard by Marriott Detroit Metro "
                     "Airport Romulus'; address 30653 Flynn Drive, Romulus, "
                     "Michigan, 48174; phone +17347213200; property code "
                     "dtwca present in the document"),
        ("binding", ["name", "street", "city", "postal_code", "phone",
                     "property_code"]),
    ]),
    "the henry autograph collection": OrderedDict([
        ("url", "https://www.marriott.com/en-us/hotels/"
                "dtwak-the-henry-autograph-collection/overview/"),
        ("prior_url", "https://www.marriott.com/hotels/travel/"
                      "dtwak-the-henry-autograph-collection/"),
        ("method", "DETERMINISTIC_BRAND_TEMPLATE"),
        ("evidence", "JSON-LD name 'The Henry, Autograph Collection'; address "
                     "Fairlane Plaza, 300 Town Center Drive, Dearborn, "
                     "Michigan, 48126; phone +13134412000; property code "
                     "dtwak present"),
        ("binding", ["name", "street", "city", "postal_code", "phone",
                     "property_code"]),
    ]),
    "towneplace suites detroit commerce": OrderedDict([
        ("url", "https://www.marriott.com/en-us/hotels/"
                "dtwtc-towneplace-suites-detroit-commerce/overview/"),
        ("prior_url", "https://www.marriott.com/hotels/travel/"
                      "dtwtc-towneplace-suites-detroit-commerce"),
        ("method", "DETERMINISTIC_BRAND_TEMPLATE"),
        ("evidence", "JSON-LD name 'TownePlace Suites by Marriott Detroit "
                     "Commerce'; address 199 Loop Road, Commerce Township, "
                     "Michigan, 48390; phone +12486693200; property code "
                     "dtwtc present"),
        ("binding", ["name", "street", "city", "postal_code", "phone",
                     "property_code"]),
    ]),
    "extended stay america detroit madison heights": OrderedDict([
        ("url", "https://www.extendedstayamerica.com/hotels/mi/detroit/"
                "madison-heights"),
        ("prior_url", ""),
        ("method", "BRAND_DIRECTORY"),
        ("evidence", "listed in Extended Stay America's own Detroit "
                     "directory; JSON-LD name 'Extended Stay America - "
                     "Detroit - Madison Heights'; address 32690 Stephenson "
                     "Hwy., Madison Heights, MI, 48071"),
        ("binding", ["name", "street", "city", "postal_code"]),
    ]),
    "extended stay america detroit novi orchard hill place": OrderedDict([
        ("url", "https://www.extendedstayamerica.com/hotels/mi/detroit/"
                "novi-orchard-hill-place"),
        ("prior_url", ""),
        ("method", "BRAND_DIRECTORY"),
        ("evidence", "listed in Extended Stay America's own Detroit "
                     "directory; JSON-LD name 'Extended Stay America - "
                     "Detroit - Novi - Orchard Hill Place'; address 39640 "
                     "Orchard Hill Pl., Novi, MI, 48375"),
        ("binding", ["name", "street", "city", "postal_code"]),
    ]),
    "red roof inn detroit troy": OrderedDict([
        ("url", "https://www.redroof.com/property/mi/troy/rri021"),
        ("prior_url", ""),
        ("method", "BRAND_SITEMAP"),
        ("evidence", "found in Red Roof's own sitemap.xml (994 URLs) as the "
                     "single Michigan Troy property; JSON-LD address 2350 "
                     "Rochester Ct, Troy, MI; property code rri021"),
        ("binding", ["street", "city", "property_code"]),
    ]),
}

#: Determinations that are NOT route repairs. Recorded for founder/identity
#: review rather than resolved here.
DETERMINATIONS = {
    "drury inn and suites": OrderedDict([
        ("classification", "PROPERTY_CLOSED_OR_CONVERTED"),
        ("evidence",
         "Drury's own complete US locations directory (215 property links, "
         "all states) lists exactly TWO Michigan properties -- Frankenmuth "
         "and Grand Rapids. There is no Troy or Detroit Drury in the brand's "
         "own directory. The committed legacy route "
         "wwws.druryhotels.com/PropertyHotelServices.aspx?Property=0029 "
         "returns no hotel content."),
        ("route_action", "the dead legacy route is PRESERVED as historical "
                         "evidence and must not be used for acquisition"),
        ("why_not_a_route_repair",
         "there is no current Drury route to repair TO. The brand does not "
         "list this building. Whether it closed, rebranded or converted is an "
         "identity question and is not decided here."),
        ("needs", "founder / identity review"),
    ]),
    "radisson hotel detroit farmington hills": OrderedDict([
        ("classification", "IDENTITY_REVIEW_FIRST"),
        ("evidence",
         "verified first-hand this pass: the committed route "
         "radissonhotels.com/en-us/hotels/radisson-farmington-hills 302s to "
         "/en-us/brand/radisson, a brand index whose document names neither "
         "'Farmington Hills' nor '12 Mile'. No property page for this "
         "building exists on the brand domain."),
        ("route_action", "the collapsing route is PRESERVED as evidence; it "
                         "is not a property route and must not be treated as "
                         "one"),
        ("why_not_a_route_repair",
         "the order is explicit: do not force a Radisson route if the "
         "building is no longer a Radisson. The brand no longer publishes a "
         "page for it, and renaming the identity on that basis alone would be "
         "exactly the silent rebrand the order forbids."),
        ("needs", "founder / identity review"),
    ]),
    "roberts riverwalk hotel": OrderedDict([
        ("classification", "ROUTING_UNRESOLVED"),
        ("evidence",
         "detroitriverwalkhotel.com lapsed and was re-registered; it 301s to "
         "an online-gambling site. The hijacked page was NOT opened again "
         "this pass and is not treated as first-party evidence of anything."),
        ("route_action", "the hijacked route is PRESERVED as historical "
                         "evidence, flagged as hijacked, and must never be "
                         "used for acquisition or published to a guest"),
        ("why_unresolved",
         "no current first-party property or operator page for 1000 River "
         "Place Drive was found at zero cost. Guessing a successor domain is "
         "precisely how a hijacked route gets adopted as a real one, so "
         "nothing was accepted."),
        ("needs", "zero-cost operator discovery in a follow-up, or founder "
                  "identity review"),
    ]),
}


def run():
    cohort = R11.load(COHORT)
    screen = R11.load(SCREEN)
    routing_doc = R11.load(MA.routing_shard_path(MARKET))
    routes = {route["hotel_ref"]["identity_key"]: route
              for route in routing_doc["routes"]}
    flagged = {row["identity_key"] for row in screen["flagged"]}

    results, repaired = [], 0
    for row in cohort["rows"]:
        key = row["identity_key"]
        if key in CONFIRMED:
            info = CONFIRMED[key]
            entry = OrderedDict([
                ("identity_key", key),
                ("canonical_name", row["canonical_name"]),
                ("classification", "ROUTING_CONFIRMED"),
                ("canonical_url", info["url"]),
                ("first_party_domain",
                 info["url"].split("/")[2].replace("www.", "")),
                ("discovery_method", info["method"]),
                ("route_evidence", info["evidence"]),
                ("identity_binding_signals", info["binding"]),
                ("prior_route", info["prior_url"]),
                ("replacement_reason",
                 "the committed route was a brand-index/legacy template that "
                 "names no building" if info["prior_url"] else
                 "the identity carried no route at all"),
                ("work_order", WORK_ORDER),
                ("policy_captured", False),
            ])
            repaired += 1
        elif key in DETERMINATIONS:
            info = DETERMINATIONS[key]
            entry = OrderedDict([("identity_key", key),
                                 ("canonical_name", row["canonical_name"])])
            entry.update(info)
            entry["work_order"] = WORK_ORDER
            entry["policy_captured"] = False
        elif key in flagged:
            entry = OrderedDict([
                ("identity_key", key),
                ("canonical_name", row["canonical_name"]),
                ("classification", "IDENTITY_REVIEW_FIRST"),
                ("why", "flagged by the identity screen as a probable "
                        "duplicate of an already-resolved identity, or as not "
                        "obviously a lodging business"),
                ("needs", "identity review before any route is discovered"),
                ("work_order", WORK_ORDER),
                ("policy_captured", False),
            ])
        else:
            entry = OrderedDict([
                ("identity_key", key),
                ("canonical_name", row["canonical_name"]),
                ("classification", "ROUTE_NOT_FOUND"),
                ("why", "not reached in this pass -- see coverage below"),
                ("work_order", WORK_ORDER),
                ("policy_captured", False),
            ])
        results.append(entry)

    # ---- write the repaired routes into the shard ---------------------- #
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    for key, info in CONFIRMED.items():
        route = routes.get(key)
        if route is None:
            # A row that never had a route needs one CREATED, in the same
            # shape as every other route in the shard. It is only created
            # because the page was opened and its own address matched the
            # census -- a route is a binding, not a URL.
            crow = census.get(key)
            if crow is None:
                raise SystemExit("STOP: %r has no census row; refusing to "
                                 "create a route it cannot bind" % key)
            route = OrderedDict([
                ("routing_id", "%s:%s" % (MARKET, crow.get("slug") or key)),
                ("schema_version", "1.0.0"),
                ("hotel_ref", OrderedDict([
                    ("market_id", MARKET),
                    ("canonical_name", crow.get("canonical_name") or ""),
                    ("normalized_name", key),
                    ("identity_key", key),
                    ("street_identity", "%s|%s" % (
                        (crow.get("address") or "").lower(),
                        crow.get("postal_code") or "")),
                ])),
                ("market_id", MARKET),
                ("official_property_url", ""),
                ("official_domain",
                 info["url"].split("/")[2].replace("www.", "")),
                ("brand", crow.get("brand") or ""),
                # BRAND_INDEX_BINDING, not PAGE_RENDERED. These routes were
                # established from the BRAND's own directory or sitemap, and a
                # committed guard forbids a rendered-page binding on a
                # bot-walled brand domain -- for good reason, since claiming to
                # have rendered a page on a domain that blocks anonymous
                # fetches is exactly the false provenance it exists to catch.
                # The property page WAS opened in attended Chrome to confirm
                # the address; that corroboration is recorded in
                # binding_sources and identity_signals_matched, which is where
                # it belongs.
                ("binding_method", "BRAND_INDEX_BINDING"),
                ("binding_sources",
                 ["%s (%s)" % (info["method"], WORK_ORDER)]),
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
            routing_doc["routes"].append(route)
            routes[key] = route
        route["official_property_url"] = info["url"]
        route["official_domain"] = info["url"].split("/")[2].replace("www.", "")
        route["identity_signals_matched"] = info["binding"]
        route["verified_at"] = AS_OF
        route["status"] = "ROUTING_CONFIRMED"
        # The routing contract is additionalProperties:false, so route history
        # does NOT go in the shard -- it is carried in this order's report,
        # which records prior_route, replacement_reason and the binding
        # evidence for every repair. Inventing a field the contract does not
        # define is how a shard stops validating for everyone.
        sources = route.setdefault("binding_sources", [])
        stamp = "%s (%s)" % (info["method"], WORK_ORDER)
        if stamp not in sources:
            sources.append(stamp)
    routing_doc["count"] = len(routing_doc["routes"])
    A = R11.write_lf
    A(MA.routing_shard_path(MARKET), routing_doc)

    counts = Counter(row.get("classification") for row in results)
    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-routing-results/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("policy_acquired", False),
        ("authority_mutated", False),
        ("cohort", cohort["admitted"]),
        ("counts", dict(counts)),
        ("routes_repaired", repaired),
        ("coverage", OrderedDict([
            ("rows_determined", repaired + len(DETERMINATIONS)
             + len(flagged)),
            ("rows_not_reached", counts.get("ROUTE_NOT_FOUND", 0)),
            ("note",
             "PARTIAL AND SAID SO. Six routes were repaired and verified by "
             "address, three named cases were determined, and three rows were "
             "flagged as identity rather than routing problems. The remaining "
             "rows are independents and brands whose directories were not "
             "swept in this pass; they are reported as ROUTE_NOT_FOUND rather "
             "than counted as failures or quietly dropped."),
        ])),
        ("rows", results),
    ]))

    print("=== Phases 4-8: routing determinations ===")
    for name, n in sorted(counts.items()):
        print("   %-30s %d" % (name, n))
    print()
    print("   routes repaired and written to the shard:", repaired)
    for key, info in CONFIRMED.items():
        print("      %-46s %s" % (key[:46], info["method"]))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
