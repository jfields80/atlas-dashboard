"""PTF-OUTER-BANKS-NC-PARALLEL-SOURCE-READY-001 -- Phase 2: the Outer Banks tourism lodging market.

Cloned from the Atlanta GA geography helper (7-tuple corridor registry).

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Outer Banks, North Carolina traveller lodging market -- the
northern beach towns on the NC-12 / US-158 bypass (Kitty Hawk, Kill Devil Hills,
Nags Head), Roanoke Island (Manteo, Wanchese), the northern beaches (Southern
Shores, Duck, Corolla) and the two bridge-foot gateways -- stated as an explicit
four-way rule (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is
discovered, so no property is admitted or refused after the fact to make a
number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

A TOURISM MARKET, NOT ONE TOWN -- AND NOT THE WHOLE BARRIER-ISLAND CHAIN
-----------------------------------------------------------------------
"The Outer Banks" names 200 miles of barrier islands. The lodging a visitor
books when they say "the Outer Banks" is concentrated in one continuous strip:
the beach towns between the Wright Memorial Bridge (US-158 from the Currituck
mainland) and Whalebone Junction (the US-64 causeway to Roanoke Island), plus
Manteo on Roanoke Island and the northern beaches up NC-12. That strip is the
CORE. Hatteras Island and Ocracoke behave as a separate lodging market:

* Hatteras Island (Rodanthe, Waves, Salvo, Avon, Buxton, Frisco, Hatteras
  village) begins south of Oregon Inlet across the Marc Basnight Bridge, after
  some 13 miles of Pea Island National Wildlife Refuge and Cape Hatteras National
  Seashore with no lodging at all. Rodanthe is ~25 miles from Whalebone
  Junction; Buxton ~50; Hatteras village ~60. Its motels and inns serve
  Hatteras-bound anglers, surfers and lighthouse visitors, not northern-beach
  stays, and a visitor to Nags Head does not sleep in Avon by choice.
* Ocracoke is reachable only by ferry (from Hatteras, or from Cedar Island /
  Swan Quarter) and is in Hyde County, not Dare.

Both are therefore OUTSIDE this build and PRESERVED for a future
``hatteras-ocracoke-nc`` submarket: every such property any lane sees is
classified OUTSIDE_MARKET with that reason, not forced into this market and not
silently dropped.

THE CORRIDORS AND WHY
---------------------
The United States Postal Service does not give Southern Shores or Duck ZIPs of
their own: Kitty Hawk, Southern Shores and Duck all share 27949. The corridor
registry is a postal partition, so the three towns are ONE corridor; the
accounting reports each town separately as a municipality overlay on the
property's own stated city (and pin), which decides nothing about membership.

CORE       Kitty Hawk / Southern Shores / Duck (27949); Kill Devil Hills and
           Colington (27948); Nags Head (27959); Manteo / Roanoke Island (27954).
CORRIDOR   Wanchese, south Roanoke Island (27981); Corolla and the Currituck Outer
           Banks, including Carova (27927).
FRINGE     Manns Harbor, the Dare mainland at the foot of the Virginia Dare /
           William B. Umstead bridges (27953); Point Harbor / Powells Point /
           Harbinger, the Currituck mainland at the foot of the Wright Memorial
           Bridge (27964, 27966, 27941). Each is ten minutes from the beach
           towns and each is its own corridor so a fringe property never
           reports as core.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight: Hatteras Island and Ocracoke (future submarket), the
           rest of the Currituck mainland (Grandy, Jarvisburg, Coinjock, Barco,
           Moyock, Currituck), Stumpy Point, East Lake, Columbia, Engelhard,
           Elizabeth City, Edenton and Virginia Beach.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
Outer Banks is built while production deployment is unavailable and four other
markets (Fayetteville, Jacksonville, Greenville, Atlanta) must go live first.
This order writes the market document to the zone's PROPOSED path, never to
the registry's ``markets/<id>.json``.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/outer_banks_nc.json
  launch_packages/pettripfinder/markets/proposed/outer-banks-nc.json
  launch_packages/pettripfinder/markets/reports/outer_banks_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/outer_banks_nc_corridor_registry_001.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-OUTER-BANKS-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "outer-banks-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "outer_banks_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "outer-banks-nc.json")
REPORT_OUT = os.path.join(REPORTS, "outer_banks_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "outer_banks_nc_corridor_registry_001.json")

#: The future submarket every Hatteras Island / Ocracoke property is preserved for.
FUTURE_SUBMARKET = "hatteras-ocracoke-nc"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("kitty-hawk-southern-shores-duck", "Kitty Hawk / Southern Shores / Duck", "Kitty Hawk, Southern Shores & Duck",
     "CORE", "kitty hawk",
     ["27949"],
     "Kitty Hawk at the Wright Memorial Bridge landfall and the US-158 / NC-12 beach road, Southern "
     "Shores, and the Town of Duck on NC-12 north -- one postal code (27949) for all three towns."),
    ("kill-devil-hills", "Kill Devil Hills / Colington", "Kill Devil Hills", "CORE", "kill devil hills",
     ["27948"],
     "Kill Devil Hills -- the Wright Brothers National Memorial, the oceanfront Virginia Dare Trail "
     "and the US-158 bypass -- and Colington Island."),
    ("nags-head", "Nags Head / Whalebone Junction", "Nags Head", "CORE", "nags head",
     ["27959"],
     "Nags Head: Jockey's Ridge, the oceanfront beach road, the US-158 bypass and Whalebone Junction "
     "at the Roanoke Island causeway."),
    ("manteo-roanoke-island", "Manteo / Roanoke Island", "Manteo & Roanoke Island", "CORE", "manteo",
     ["27954"],
     "Manteo's historic waterfront, Roanoke Island Festival Park, Fort Raleigh and the north end of "
     "Roanoke Island."),
    ("wanchese", "Wanchese", "Wanchese", "CORRIDOR", "wanchese",
     ["27981"],
     "Wanchese, the fishing village at the south end of Roanoke Island."),
    ("corolla", "Corolla / Currituck Outer Banks", "Corolla", "CORRIDOR", "corolla",
     ["27927"],
     "Corolla, the Currituck Beach Lighthouse and the four-wheel-drive beaches at Carova, on NC-12 "
     "north of Duck."),
    ("manns-harbor", "Manns Harbor / Dare Mainland", "Manns Harbor", "FRINGE", "manns harbor",
     ["27953"],
     "Manns Harbor on the Dare County mainland at the foot of the Virginia Dare Memorial and William B. "
     "Umstead bridges to Manteo."),
    ("point-harbor", "Point Harbor / Powells Point / Harbinger", "Point Harbor", "FRINGE", "point harbor",
     ["27964", "27966", "27941"],
     "Point Harbor, Powells Point and Harbinger on the Currituck County mainland at the foot of the "
     "Wright Memorial Bridge to Kitty Hawk."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. Empty at authoring time; a later
#: ruling adds a row, never a ZIP.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "kdh": "kill devil hills", "kill devil hill": "kill devil hills",
    "southern shore": "southern shores", "nagshead": "nags head",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
HATTERAS_WHY = ("Hatteras Island, south of Oregon Inlet across the Marc Basnight Bridge and Pea Island: a "
                "separate lodging market; PRESERVED for the future %s submarket, evaluated and refused here."
                % FUTURE_SUBMARKET)
OUTSIDE = [
    ("Rodanthe / Waves / Salvo", "NC", ["27968", "27982", "27972"], HATTERAS_WHY),
    ("Avon", "NC", ["27915"], HATTERAS_WHY),
    ("Buxton", "NC", ["27920"], HATTERAS_WHY),
    ("Frisco", "NC", ["27936"], HATTERAS_WHY),
    ("Hatteras", "NC", ["27943"], HATTERAS_WHY),
    ("Ocracoke", "NC", ["27960"],
     "Ocracoke Island, Hyde County, reachable only by ferry: a separate lodging market; PRESERVED for the "
     "future %s submarket, evaluated and refused here." % FUTURE_SUBMARKET),
    ("Grandy / Jarvisburg / Coinjock / Barco / Aydlett", "NC", ["27939", "27947", "27923", "27917", "27916"],
     "The Currituck mainland on US-158 north of Point Harbor, 15-35 minutes from the beach; roadside and "
     "Intracoastal Waterway lodging, not Outer Banks stays; evaluated and refused."),
    ("Moyock / Currituck / Shawboro / Knotts Island", "NC", ["27958", "27929", "27973", "27950"],
     "Northern Currituck County toward Chesapeake and Virginia Beach; evaluated and refused."),
    ("Stumpy Point / East Lake / Manns Harbor south", "NC", ["27978", "27925"],
     "US-264 on the Dare mainland south of Manns Harbor, and Columbia (Tyrrell County); evaluated and refused."),
    ("Engelhard / Swan Quarter", "NC", ["27824", "27885"],
     "Hyde County mainland; evaluated and refused."),
    ("Elizabeth City", "NC", ["27909", "27906", "27907"],
     "Pasquotank County, 50 miles inland; its own market; refused by name."),
    ("Edenton / Hertford", "NC", ["27932", "27944"],
     "Chowan / Perquimans County on the Albemarle Sound; refused by name."),
    ("Virginia Beach / Chesapeake", "VA", ["23451", "23452", "23454", "23456", "23457", "23320", "23322"],
     "Virginia; another state and its own market; refused by name."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the Hatteras / Ocracoke submarket and the refused mainland so
#: this order classifies those properties on evidence.
CELLS = [
    ("duck", "Duck", "Duck / NC-12 north", 36.170, -75.755, 4000, True),
    ("southern-shores", "Southern Shores", "Southern Shores", 36.125, -75.725, 3000, True),
    ("kitty-hawk", "Kitty Hawk", "Kitty Hawk / US-158 / Wright Memorial Bridge landfall", 36.075, -75.705, 3500, True),
    ("kill-devil-hills-north", "Kill Devil Hills", "Kill Devil Hills north / Wright Brothers Memorial", 36.030, -75.672, 3000, True),
    ("kill-devil-hills-south", "Kill Devil Hills", "Kill Devil Hills south / Colington Road", 36.000, -75.655, 3000, True),
    ("colington", "Kill Devil Hills", "Colington Island", 36.010, -75.705, 3000, True),
    ("nags-head-north", "Nags Head", "Nags Head north / Jockey's Ridge", 35.965, -75.635, 3000, True),
    ("nags-head-south", "Nags Head", "South Nags Head / Whalebone Junction", 35.915, -75.600, 4000, True),
    ("manteo", "Manteo", "Manteo / Roanoke Island north", 35.905, -75.670, 3500, True),
    ("wanchese", "Wanchese", "Wanchese / Roanoke Island south", 35.845, -75.640, 3500, True),
    ("corolla", "Corolla", "Corolla / Currituck Beach Lighthouse", 36.340, -75.815, 6000, True),
    ("manns-harbor", "Manns Harbor", "Manns Harbor / Dare mainland", 35.905, -75.765, 3000, True),
    ("point-harbor", "Point Harbor", "Point Harbor / Powells Point / Harbinger", 36.080, -75.790, 5000, True),
    # observation only -- the Hatteras / Ocracoke submarket and the refused mainland
    ("obs-rodanthe-waves-salvo", "Rodanthe", "Rodanthe / Waves / Salvo -- OBSERVATION ONLY", 35.570, -75.470, 8000, False),
    ("obs-avon", "Avon", "Avon -- OBSERVATION ONLY", 35.350, -75.505, 5000, False),
    ("obs-buxton-frisco", "Buxton", "Buxton / Frisco -- OBSERVATION ONLY", 35.255, -75.580, 7000, False),
    ("obs-hatteras", "Hatteras", "Hatteras village -- OBSERVATION ONLY", 35.215, -75.690, 4000, False),
    ("obs-ocracoke", "Ocracoke", "Ocracoke village -- OBSERVATION ONLY", 35.115, -75.980, 4000, False),
    ("obs-grandy-jarvisburg", "Grandy", "Grandy / Jarvisburg / Coinjock -- OBSERVATION ONLY", 36.250, -75.900, 9000, False),
]

BOUNDS = {
    "min_lat": 35.05,
    "max_lat": 36.56,
    "min_lng": -76.10,
    "max_lng": -75.40,
}

#: Reporting overlay only (never membership): the areas the order names, each an
#: anchor point and a radius. A property is reported in the NEAREST anchor whose
#: radius it falls inside, else "elsewhere". The accounting prefers the
#: property's OWN stated municipality where it names one of these towns.
COVERAGE_AREAS = [
    ("Duck", 36.1700, -75.7550, 4.5),
    ("Southern Shores", 36.1200, -75.7250, 3.5),
    ("Kitty Hawk", 36.0750, -75.7050, 4.0),
    ("Kill Devil Hills", 36.0150, -75.6700, 4.5),
    ("Nags Head", 35.9400, -75.6150, 6.0),
    ("Manteo / Roanoke Island", 35.9050, -75.6700, 4.0),
    ("Wanchese", 35.8450, -75.6400, 3.5),
    ("Corolla", 36.3400, -75.8150, 9.0),
    ("Manns Harbor", 35.9050, -75.7650, 3.0),
    ("Point Harbor / Powells Point", 36.0800, -75.7900, 6.0),
]

#: The order's named towns that SHARE a corridor, keyed on the property's own
#: stated municipality (normalised). Reporting only.
MUNICIPALITY_OVERLAY = OrderedDict([
    ("kitty hawk", "Kitty Hawk"), ("southern shores", "Southern Shores"), ("duck", "Duck"),
    ("kill devil hills", "Kill Devil Hills"), ("colington", "Kill Devil Hills"),
    ("nags head", "Nags Head"), ("manteo", "Manteo / Roanoke Island"), ("wanchese", "Wanchese"),
    ("corolla", "Corolla"), ("carova", "Corolla"), ("manns harbor", "Manns Harbor"),
    ("point harbor", "Point Harbor / Powells Point"), ("powells point", "Point Harbor / Powells Point"),
    ("harbinger", "Point Harbor / Powells Point"),
])


def build():
    corridors = []
    seen_zip = {}
    for order, (slug, name, area, klass, _muni, zips, desc) in enumerate(CORRIDORS, start=1):
        for z in zips:
            if z in seen_zip:
                raise SystemExit("postal code %s claimed by both %s and %s -- the corridor "
                                 "registry must be a partition" % (z, seen_zip[z], slug))
            seen_zip[z] = slug
        corridors.append(OrderedDict([
            ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
            ("market_id", MARKET_ID),
            ("name", name),
            ("slug", slug),
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Outer Banks" % name),
            ("meta_description",
             "Verified pet-friendly hotels in %s, with real pet fees and policies read from "
             "each hotel's own official website." % name),
            ("description", desc),
            ("included_cities", []),
            ("included_postal_codes", list(zips)),
            ("explicit_hotel_ids", []),
            ("excluded_hotel_ids", []),
            ("minimum_hotel_count", 5),
            ("show_in_navigation", False),
            ("show_in_sitemap", False),
            ("allow_multi_corridor", False),
            ("display_order", order),
            ("display_area", area),
            ("state_code", "NC"),
            ("geography_class", klass),
        ]))
    outside_zips = {z for _m, _s, zs, _w in OUTSIDE for z in zs}
    overlap = outside_zips & set(seen_zip)
    if overlap:
        raise SystemExit("postal codes both admitted and refused: %s" % sorted(overlap))

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)),
        ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
        ("state_code", "NC"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Outer Banks, NC tourism lodging market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 35.990, "lng": -75.660}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- south "
             "over Hatteras Island to Ocracoke, and west to the Currituck and Dare mainland -- so that " +
             WORK_ORDER + " classifies those properties on evidence instead of being blind to them. "
             "Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A tourism market: the northern beach towns and Roanoke Island are CORE (Kitty "
         "Hawk / Southern Shores / Duck, Kill Devil Hills, Nags Head, Manteo); Wanchese and Corolla are "
         "CORRIDOR; the two bridge-foot mainland gateways are FRINGE. Hatteras Island and Ocracoke are "
         "OBSERVED and REFUSED, preserved for a future " + FUTURE_SUBMARKET + " submarket; the Currituck "
         "mainland beyond Point Harbor, Elizabeth City and Virginia Beach are named and REFUSED."),
        ("scope_disclosure",
         "%d bounded cells: %d admitting and %d observation-only." % (
             len(cells), sum(1 for c in cells if c["admitting"]),
             sum(1 for c in cells if not c["admitting"]))),
        ("explicit_hotel_admissions", OrderedDict([
            ("_what_this_is",
             "The explicit-hotel mechanism, so a single legitimate fringe property never becomes a reason "
             "to widen a municipality or a postal code. Empty at authoring time."),
            ("admissions", []),
        ])),
        ("cells", cells),
    ])

    shard = OrderedDict([
        ("schema", "ptf-market/1.1"),
        ("market_id", MARKET_ID),
        ("market_name", "Outer Banks, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Kill Devil Hills"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels on the Outer Banks, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels on North Carolina's Outer Banks -- Kitty Hawk, Kill Devil Hills, "
         "Nags Head, Manteo, Duck, Southern Shores and Corolla -- with real pet fees and policies read "
         "from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Outer Banks"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A tourism market -- the northern beach towns, Roanoke Island and the "
         "northern beaches -- not the whole barrier-island chain. Nothing else admits a property: not an "
         "'Outer Banks' marketing name, not a map pin, not a vacation-rental listing, not a competitor "
         "directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor. Kitty Hawk, Southern Shores and Duck "
         "share 27949 and are one corridor."),
        ("_census_membership_note",
         "Hatteras Island (Rodanthe, Waves, Salvo, Avon, Buxton, Frisco, Hatteras) and Ocracoke are a "
         "separate lodging market preserved for a future submarket; the Currituck mainland beyond Point "
         "Harbor, Elizabeth City and Virginia Beach are not absorbed. A property whose own page states "
         "one of their postal codes is OUTSIDE, however it is named. Individual vacation houses, condo "
         "units, rental-management portfolios and timeshare inventory are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Outer Banks tourism-market geography and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-13"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Fayetteville, Jacksonville, Greenville "
         "and Atlanta to go live."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "The Outer Banks lodging a visitor means by 'the Outer Banks': the continuous beach-town strip "
         "between the Wright Memorial Bridge and Whalebone Junction, Roanoke Island and the northern "
         "beaches up NC-12 to Corolla, plus the two bridge-foot mainland gateways as FRINGE."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("hatteras_ocracoke_ruling", OrderedDict([
            ("decision", "OUTSIDE -- PRESERVED_FOR_FUTURE_SUBMARKET"),
            ("future_market_id", FUTURE_SUBMARKET),
            ("why",
             "Hatteras Island begins across Oregon Inlet after ~13 miles of Pea Island refuge and National "
             "Seashore with no lodging; Rodanthe is ~25 road miles from Whalebone Junction and Hatteras "
             "village ~60. Its lodging is a separate cluster serving Hatteras-bound travel. Ocracoke is "
             "ferry-only and in Hyde County. Forcing either into this market would publish hotels an hour "
             "or a ferry ride from the towns the market names."),
            ("how_preserved",
             "Discovery OBSERVES both (five observation cells, brand city pages and sitemaps for Rodanthe, "
             "Avon, Buxton, Frisco, Hatteras and Ocracoke). Every property seen there is carried in the "
             "census's non_admitted rows as OUTSIDE_MARKET with this reason, so the future submarket order "
             "starts from recorded identities rather than from zero."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Kitty Hawk", "ADMITTED (CORE, kitty-hawk-southern-shores-duck, 27949)."),
            ("Kill Devil Hills", "ADMITTED (CORE, kill-devil-hills, 27948) -- includes Colington."),
            ("Nags Head", "ADMITTED (CORE, nags-head, 27959)."),
            ("Manteo / Roanoke Island", "ADMITTED (CORE, manteo-roanoke-island, 27954)."),
            ("Southern Shores", "ADMITTED (CORE) -- shares 27949 with Kitty Hawk; reported separately by municipality."),
            ("Duck", "ADMITTED (CORE) -- shares 27949 with Kitty Hawk; reported separately by municipality."),
            ("Corolla", "ADMITTED (CORRIDOR, corolla, 27927) -- NC-12 north of Duck; never CORE."),
            ("Wanchese", "ADMITTED (CORRIDOR, wanchese, 27981) -- south Roanoke Island; never CORE."),
            ("Manns Harbor", "ADMITTED (FRINGE, manns-harbor, 27953) -- Dare mainland bridge foot."),
            ("Point Harbor / Powells Point / Harbinger", "ADMITTED (FRINGE, point-harbor) -- Currituck mainland bridge foot."),
            ("Rodanthe / Waves / Salvo", "OUTSIDE -- Hatteras Island; future submarket."),
            ("Avon", "OUTSIDE -- Hatteras Island; future submarket."),
            ("Buxton", "OUTSIDE -- Hatteras Island; future submarket."),
            ("Frisco", "OUTSIDE -- Hatteras Island; future submarket."),
            ("Hatteras", "OUTSIDE -- Hatteras Island; future submarket."),
            ("Ocracoke", "OUTSIDE -- ferry-only Hyde County island; future submarket."),
            ("Grandy / Jarvisburg / Coinjock", "OUTSIDE -- Currituck mainland roadside lodging."),
            ("Elizabeth City / Virginia Beach", "OUTSIDE -- their own markets."),
        ])),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]),
            ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = "
         "5 verified pet-friendly hotels) is met. No thin corridor page is invented for SEO; every "
         "corridor is show_in_navigation/show_in_sitemap false until a registration order publishes it."),
        ("coverage_areas_are_a_reporting_overlay",
         "Kitty Hawk, Southern Shores and Duck share 27949. The accounting reports each named town from "
         "the property's own stated municipality (MUNICIPALITY_OVERLAY), falling back to a nearest-anchor "
         "overlay on its pin. The overlay decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Six cells observe Hatteras Island, Ocracoke and the Currituck mainland. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, qualifying resorts and qualifying lodging establishments "
         "operated as lodging businesses: bookable nightly rooms or suites sold to the public under one "
         "establishment name, with an official property page and a front desk / on-site hotel operation. "
         "It NEVER admits: individual vacation houses or cottages; condominium units or condo complexes "
         "rented unit-by-unit through owners or agencies; property-management or realty rental portfolios "
         "(Twiddy, Village Realty, Sun Realty, Outer Banks Blue, Joe Lamb Jr., Brindley Beach, Resort Realty "
         "and the like); Airbnb / Vrbo-style listings; cottage collections that are not operated as one "
         "lodging establishment; and TIMESHARE / vacation-ownership inventory (owner weeks, points and "
         "exchange resorts) unless that property independently qualifies as a hotel -- public nightly "
         "rooms, its own reservation surface and a hotel front desk. Every such row is recorded "
         "NON_LODGING with its reason. A bed and breakfast is admitted only when it operates as an inn "
         "with bookable rooms on its own premises and an official site. Campgrounds and RV parks are "
         "NON_LODGING."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


def corridor_municipality():
    """slug -> the municipality the corridor principally sits in (name attachment only)."""
    return {slug: muni for slug, _n, _a, _k, muni, _z, _d in CORRIDORS}


def coverage_area(lat, lng):
    """The overlay area a coordinate reports under, or None. Reporting only."""
    if lat is None or lng is None:
        return None
    best = None
    for name, la, ln, r in COVERAGE_AREAS:
        dy = (lat - la) * 111.0
        dx = (lng - ln) * 111.0 * math.cos(math.radians(la))
        d = math.hypot(dx, dy)
        if d <= r and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    muni = " ".join((city or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    return MUNICIPALITY_OVERLAY.get(muni)


def is_future_submarket(postal):
    """True when a postal code belongs to the preserved Hatteras / Ocracoke submarket."""
    z = (postal or "").strip()[:5]
    return any(z in zs for name, _s, zs, why in OUTSIDE if FUTURE_SUBMARKET in why)


def classify_postal(postal, municipality):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and
    municipality. The one membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = " ".join((municipality or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    for slug, _name, _area, klass, _m, zips, _desc in CORRIDORS:
        if z in zips:
            for _rz, rmuni, why in MUNICIPALITY_REFUSALS:
                if rmuni.lower() == muni:
                    return "OUTSIDE", None, why
            return klass, slug, "postal code %s -> %s" % (z, slug)
    for name, _s, zs, why in OUTSIDE:
        if z in zs:
            return "OUTSIDE", None, "%s: %s" % (name, why)
    return "OUTSIDE", None, "postal code %r is claimed by no corridor" % z


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    config, shard, report, corridors = build()
    from scripts.pettripfinder.markets.contract import parse_market
    parse_market(json.loads(json.dumps(shard)))
    if args.write:
        for path, doc in ((CONFIG_OUT, config), (SHARD_OUT, shard), (REPORT_OUT, report),
                          (REGISTRY_OUT, OrderedDict([
                              ("schema", "ptf-corridor-registry/1.0"), ("work_order", WORK_ORDER),
                              ("market_id", MARKET_ID), ("corridors", corridors)]))):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, indent=1)
                fh.write("\n")
            print("WROTE", os.path.relpath(path, _DASH))
    print("corridors=%d  admitted_zips=%d  cells=%d (admitting %d, observation %d)" % (
        report["corridor_count"], report["admitted_postal_code_count"],
        report["cells_total"], report["cells_admitting"], report["cells_observation_only"]))
    print("by class:", json.dumps(report["corridor_count_by_class"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
