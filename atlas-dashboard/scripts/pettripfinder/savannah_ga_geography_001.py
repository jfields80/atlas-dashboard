"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- Phase 2 + 3: the Savannah travel market and its corridors.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Savannah, Georgia traveler lodging market -- a MULTI-CORE tourism,
airport and interstate market, not a city and not the whole coast -- stated as an
explicit four-way rule (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single
hotel is admitted, so no property is admitted or refused after the fact to make
a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. A brand's
marketing name ("Savannah Airport", "Savannah I-95 North", "Savannah South")
never admits and never places a property: a "Savannah Airport" hotel whose own
page states Pooler 31322 is a Pooler hotel.

A TRAVEL MARKET, NOT CITY LIMITS, AND NOT THE COAST
--------------------------------------------------
Savannah's hotel demand sits in separate lodging cores: the Landmark Historic
District (the squares, Broughton Street, the convention and cruise-port
visitors), the riverfront (River Street, Factors Walk, Plant Riverside and the
Eastern Wharf), Hutchinson Island (the Savannah Convention Center and the
Westin), Midtown (Victory Drive to DeRenne, Abercorn / White Bluff and the
Chatham Parkway hotel strip at I-16), the Southside (Abercorn Extension,
Oglethorpe Mall, the hospitals), the Savannah / Hilton Head International
Airport and Garden City beside it, Pooler (I-95 exits 102 / 104, Tanger
Outlets) and the Gateway interchange at I-95 exit 94. Around them sit the
interstate towns where a Savannah traveller sleeps by choice -- Port Wentworth
and the Crossroads business park (I-95 exits 106 / 109) -- and a FRINGE of
Richmond Hill (I-95 exits 87 / 90, whose own brands file it under Savannah) and
the eastern islands on the road to Tybee (Wilmington Island, Whitemarsh,
Skidaway). FRINGE is admitted, each its own corridor, never reported as core.

RIVER STREET, EASTERN WHARF AND THE HISTORIC DISTRICT SHARE ONE POSTAL CODE
--------------------------------------------------------------------------
31401 carries the Historic District, River Street, Plant Riverside and the
Eastern Wharf alike. A postal-code partition cannot place them in two corridors
without splitting a ZIP other hotels depend on, so they are ONE corridor, and
River Street / Eastern Wharf is reported as a STREET-AND-PIN OVERLAY on each
row (the property's own stated street first: River Street, Bay Street, Factors
Walk, Eastern Wharf; then a pin within 250 m of the river). The overlay decides
nothing about membership or corridor. The same applies to Georgetown and the
Gateway interchange inside 31419 and to Thunderbolt inside 31404.

THE FOUR CLASSES
----------------
CORE       Historic District / Downtown / River Street / Eastern Wharf (31401);
           Hutchinson Island (31421); Midtown / Chatham Parkway / Thunderbolt
           (31404, 31405); Southside (31406); SAV Airport / Garden City / West
           Savannah (31408, 31415); Pooler (31322); Gateway / I-95 exit 94 /
           Georgetown (31419).
CORRIDOR   Port Wentworth / Crossroads / I-95 exits 106-109 (31407).
FRINGE     Richmond Hill (31324); Wilmington Island / Whitemarsh / Skidaway
           (31410, 31411).
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision --
           Tybee Island (PRESERVED for a future standalone beach market),
           Hilton Head Island, Bluffton, Hardeeville, Ridgeland and Beaufort SC,
           Rincon / Springfield / Guyton (Effingham County), Bloomingdale,
           Hinesville / Midway / Fort Stewart, Statesboro, Brunswick, St. Simons
           Island, Pembroke / Ellabell, and Hunter Army Airfield (military,
           non-public lodging).

THE "EVALUATE" SET
------------------
Garden City   ADMITTED CORE with the airport (31408): the airport sits in it,
              and its US-80 / GA-21 motels sell to airport and port traffic.
Port Wentworth ADMITTED CORRIDOR (31407): I-95 exits 106 / 109 and the
              Crossroads Parkway hotels branded "Savannah Airport".
Georgetown    ADMITTED CORE inside the Gateway corridor (31419).
Richmond Hill ADMITTED FRINGE (31324): the I-95 exit 87 / 90 cluster 15 miles
              south of downtown; Marriott files its Richmond Hill hotels under
              the SAV market code and they sell Savannah-bound interstate stays.
              Midway / Hinesville beyond it are OUTSIDE.
Tybee Island  OUTSIDE -- PRESERVED_FOR_FUTURE_MARKET tybee-island-ga. An
              18-mile barrier-island beach town on US-80 whose lodging is a
              beach-resort and vacation-rental market with its own search
              intent ("Tybee Island hotels"), its own motels and oceanfront
              resorts, and a lodging stock dominated by rental cottages and
              condos. A Savannah visitor day-trips Tybee; a Tybee visitor books
              Tybee. Forcing it in would publish beach resorts under a city
              page 30 minutes away and bury a market that can stand alone.
Thunderbolt   ADMITTED CORE inside Midtown's 31404 (reported as its own overlay).
Wilmington Island / Skidaway  ADMITTED FRINGE (31410 / 31411): the residential
              islands on US-80 and Diamond Causeway; any hotel there sells to
              Savannah visitors on the Tybee road. The Landings club is private.
Hilton Head / Bluffton / Beaufort / Hardeeville  OUTSIDE (South Carolina; the
              order refuses Hilton Head, Bluffton and Beaufort by name, and
              Hardeeville's I-95 exit 5 cluster is another state's interchange).
Statesboro / Brunswick / St. Simons  OUTSIDE by name (the order).

A future standalone market stays possible wherever traveller intent is
materially distinct: every OUTSIDE town is named with its postal codes and
nothing here claims it.

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the admitted ZIPs -- Tybee Island, Hardeeville,
Bluffton, Rincon, Midway -- so this order classifies those properties on
evidence rather than being blind to them.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
Savannah is built while Jacksonville is the current live release and other
markets stand ahead of it in the serialized release queue. The market document
goes to the zone's PROPOSED path, never to the registry's markets/<id>.json.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/savannah_ga.json
  launch_packages/pettripfinder/markets/proposed/savannah-ga.json
  launch_packages/pettripfinder/markets/reports/savannah_ga_geography_001.json
  launch_packages/pettripfinder/markets/reports/savannah_ga_corridor_registry_001.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "savannah-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "savannah_ga.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "savannah-ga.json")
REPORT_OUT = os.path.join(REPORTS, "savannah_ga_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "savannah_ga_corridor_registry_001.json")

#: The future standalone market every Tybee Island property is preserved for.
FUTURE_SUBMARKET = "tybee-island-ga"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("historic-district", "Historic District / Downtown / River Street", "Historic District & River Street",
     "CORE", "savannah",
     ["31401", "31402", "31412"],
     "Savannah's Landmark Historic District and downtown: the squares, Broughton and Bay Streets, the "
     "riverfront (River Street, Factors Walk, Plant Riverside District) and the Eastern Wharf, plus the "
     "downtown post-office box codes."),
    ("hutchinson-island", "Hutchinson Island / Savannah Convention Center", "Hutchinson Island", "CORE",
     "savannah",
     ["31421"],
     "Hutchinson Island across the Savannah River from River Street: the Savannah Convention Center, "
     "the Westin Savannah Harbor resort and the water-ferry landing."),
    ("midtown", "Midtown / Chatham Parkway / Thunderbolt", "Midtown", "CORE", "savannah",
     ["31404", "31405"],
     "Midtown Savannah from Victory Drive to DeRenne Avenue -- Abercorn Street, White Bluff Road, "
     "Starland and Daffin Park -- the Chatham Parkway / I-16 hotel strip, the east side and the town of "
     "Thunderbolt."),
    ("southside", "Southside / Abercorn Extension / Oglethorpe Mall", "Southside", "CORE", "savannah",
     ["31406"],
     "The Southside: Abercorn Extension, Oglethorpe Mall, Memorial and St. Joseph's hospitals, Hodgson "
     "Memorial Drive, Skidaway Road and Isle of Hope."),
    ("sav-airport", "Savannah / Hilton Head International Airport / Garden City", "SAV Airport",
     "CORE", "savannah",
     ["31408", "31415"],
     "Savannah / Hilton Head International Airport (SAV) and Garden City around it -- Airways Avenue, "
     "Dean Forest Road, US-80 / GA-21 and the port -- with West Savannah between Garden City and "
     "downtown."),
    ("pooler", "Pooler / I-95 Exits 102-104 / Tanger Outlets", "Pooler", "CORE", "pooler",
     ["31322"],
     "The City of Pooler at I-95 exits 102 (US-80) and 104 (Pooler Parkway): the airport-side hotel "
     "cluster, Tanger Outlets and the Mighty Eighth Air Force Museum."),
    ("gateway-i95", "Gateway / I-95 Exit 94 / Georgetown", "Gateway / I-95", "CORE", "savannah",
     ["31419"],
     "The Savannah Gateway interchange at I-95 exit 94 (GA-204 / Abercorn Street), Gateway Boulevard, "
     "Georgetown, Southbridge and Abercorn Street south toward Georgia Southern's Armstrong campus."),
    ("port-wentworth", "Port Wentworth / Crossroads / I-95 Exits 106-109", "Port Wentworth", "CORRIDOR",
     "port wentworth",
     ["31407"],
     "Port Wentworth and the Crossroads business park at I-95 exits 106 (Jimmy DeLoach Parkway) and 109 "
     "(GA-21), north of the airport."),
    ("richmond-hill", "Richmond Hill / I-95 Exits 87-90", "Richmond Hill", "FRINGE", "richmond hill",
     ["31324"],
     "Richmond Hill in Bryan County at I-95 exits 87 (US-17) and 90 (GA-144), fifteen miles south of "
     "downtown Savannah."),
    ("eastern-islands", "Wilmington Island / Whitemarsh / Skidaway Island", "Wilmington & Skidaway Islands",
     "FRINGE", "savannah",
     ["31410", "31411"],
     "The residential islands east and south of the city: Whitemarsh and Wilmington Island on US-80 "
     "toward Tybee, and Skidaway Island on Diamond Causeway."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. Empty at authoring time; a later
#: ruling adds a row, never a ZIP.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "savannah ga": "savannah", "port wentworth ga": "port wentworth", "richmond hill ga": "richmond hill",
    "pooler ga": "pooler", "garden city ga": "garden city", "tybee": "tybee island",
    "savannah beach": "tybee island",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
TYBEE_WHY = ("Tybee Island: an 18-mile barrier-island beach town at the end of US-80 whose lodging is a "
             "beach-resort, motel and vacation-rental market with its own search intent; PRESERVED for the "
             "future %s standalone market, evaluated and refused here." % FUTURE_SUBMARKET)
OUTSIDE = [
    ("Tybee Island", "GA", ["31328"], TYBEE_WHY),
    ("Hunter Army Airfield", "GA", ["31409"],
     "MILITARY_GOVERNMENT_NONPUBLIC -- Hunter Army Airfield's installation lodging is not public lodging; "
     "evaluated and refused."),
    ("Bloomingdale", "GA", ["31302"],
     "Bloomingdale west of Pooler on US-80: residential, no lodging core of its own; evaluated and refused."),
    ("Rincon / Springfield / Guyton / Clyo (Effingham County)", "GA", ["31326", "31329", "31312", "31307"],
     "Effingham County on GA-21 / GA-17, its own small lodging cluster north of Port Wentworth; "
     "evaluated and refused."),
    ("Hinesville / Midway / Fort Stewart / Riceboro", "GA", ["31313", "31314", "31315", "31320", "31323"],
     "Liberty County and the Fort Stewart market on I-95 exit 76 and US-84; its own market; refused."),
    ("Pembroke / Ellabell / Bryan County north", "GA", ["31321", "31308"],
     "Bryan County on I-16 west, a separate interchange cluster; evaluated and refused."),
    ("Statesboro", "GA", ["30458", "30459", "30460", "30461"],
     "Georgia Southern's university town on I-16, its own market; refused by name (order)."),
    ("Brunswick / St. Simons Island / Jekyll Island", "GA", ["31520", "31523", "31525", "31522", "31527"],
     "The Golden Isles, 75 miles south, their own coastal market; refused by name (order)."),
    ("Darien / Eulonia / Townsend", "GA", ["31305", "31331", "31319"],
     "McIntosh County on I-95 south; far coastal Georgia; refused by name (order)."),
    ("Hardeeville / Ridgeland", "SC", ["29927", "29936"],
     "South Carolina's I-95 exits 5 / 21 across the river: another state's interchange cluster; refused."),
    ("Bluffton / Okatie", "SC", ["29909", "29910"],
     "South Carolina Lowcountry; refused by name (order: do not absorb Bluffton)."),
    ("Hilton Head Island", "SC", ["29926", "29928", "29925", "29938"],
     "South Carolina resort island; refused by name (order: do not absorb Hilton Head Island)."),
    ("Beaufort / Port Royal / Lady's Island", "SC", ["29902", "29906", "29907", "29935"],
     "South Carolina; refused by name (order: do not absorb Beaufort)."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover refused neighbours so this order classifies them on evidence.
CELLS = [
    ("historic-district", "Savannah", "Historic District / Downtown", 32.0760, -81.0930, 1800, True),
    ("river-street", "Savannah", "River Street / Plant Riverside / Eastern Wharf", 32.0810, -81.0900, 1500, True),
    ("hutchinson-island", "Savannah", "Hutchinson Island / Convention Center", 32.0880, -81.0950, 1800, True),
    ("midtown", "Savannah", "Midtown / Victory Drive / Abercorn", 32.0450, -81.0950, 3000, True),
    ("chatham-parkway", "Savannah", "Chatham Parkway / I-16", 32.0550, -81.1650, 3000, True),
    ("thunderbolt", "Thunderbolt", "Thunderbolt / east side", 32.0350, -81.0500, 2500, True),
    ("southside", "Savannah", "Southside / Abercorn Extension / Oglethorpe Mall", 31.9950, -81.1150, 4500, True),
    ("sav-airport", "Savannah", "SAV Airport / Garden City", 32.1250, -81.2000, 4500, True),
    ("pooler", "Pooler", "Pooler / I-95 exits 102-104", 32.1100, -81.2500, 4500, True),
    ("gateway-i95", "Savannah", "Gateway / I-95 exit 94 / Georgetown", 31.9700, -81.2300, 5000, True),
    ("port-wentworth", "Port Wentworth", "Port Wentworth / Crossroads", 32.1650, -81.1900, 5000, True),
    ("richmond-hill", "Richmond Hill", "Richmond Hill / I-95 exits 87-90", 31.9100, -81.3200, 6000, True),
    ("eastern-islands", "Savannah", "Wilmington Island / Whitemarsh / Skidaway", 32.0000, -81.0000, 7000, True),
    # observation only -- the preserved Tybee market and refused neighbours
    ("obs-tybee-island", "Tybee Island", "Tybee Island -- OBSERVATION ONLY", 32.0100, -80.8500, 4000, False),
    ("obs-hardeeville", "Hardeeville", "Hardeeville SC -- OBSERVATION ONLY", 32.2900, -81.0800, 6000, False),
    ("obs-bluffton", "Bluffton", "Bluffton SC -- OBSERVATION ONLY", 32.2300, -80.8700, 6000, False),
    ("obs-rincon", "Rincon", "Rincon / Effingham -- OBSERVATION ONLY", 32.2950, -81.2350, 6000, False),
    ("obs-midway", "Midway", "Midway / Hinesville -- OBSERVATION ONLY", 31.8100, -81.4300, 6000, False),
]

BOUNDS = {
    "min_lat": 31.78,
    "max_lat": 32.40,
    "min_lng": -81.50,
    "max_lng": -80.82,
}

#: Reporting overlay only (never membership): the areas the order names, each an
#: anchor point and a radius. A property is reported in the NEAREST anchor whose
#: radius it falls inside, else "elsewhere".
COVERAGE_AREAS = [
    ("Historic District / Downtown", 32.0760, -81.0930, 1.6),
    ("River Street / Eastern Wharf", 32.0810, -81.0880, 0.35),
    ("Hutchinson Island", 32.0890, -81.0970, 2.0),
    ("Midtown", 32.0450, -81.0950, 3.0),
    ("Chatham Parkway / I-16", 32.0550, -81.1650, 3.0),
    ("Thunderbolt", 32.0350, -81.0500, 2.0),
    ("Southside", 31.9950, -81.1150, 5.0),
    ("SAV Airport", 32.1280, -81.2020, 3.0),
    ("Garden City", 32.1000, -81.1600, 3.5),
    ("Pooler", 32.1100, -81.2500, 5.0),
    ("Gateway / I-95 exit 94", 31.9650, -81.2400, 4.0),
    ("Georgetown", 31.9800, -81.2000, 3.0),
    ("Port Wentworth / Crossroads", 32.1650, -81.1900, 5.0),
    ("Richmond Hill", 31.9100, -81.3200, 7.0),
    ("Wilmington Island", 32.0100, -80.9700, 5.0),
    ("Skidaway Island", 31.9400, -81.0500, 5.0),
]

#: Street wording on the property's OWN address that names the riverfront.
RIVERFRONT_STREETS = re.compile(
    r"\briver st|\bfactors walk|\beastern wharf|\bwharf\b|\bbay st(reet)?\b|\briverside\b", re.I)


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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Savannah" % name),
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
            ("state_code", "GA"),
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
        ("state_code", "GA" if muni not in ("Hardeeville", "Bluffton") else "SC"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Savannah, GA multi-core tourism, airport and interstate lodging market (PetTripFinder discovery scope)"),
        ("state", "GA"),
        ("states", ["GA"]),
        ("country", "US"),
        ("market_center", {"lat": 32.080, "lng": -81.095}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- east over "
             "Tybee Island and Bluffton SC, north over Hardeeville SC and Rincon, south past Richmond Hill to "
             "Midway -- so that " + WORK_ORDER + " classifies those properties on evidence instead of being "
             "blind to them. Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A multi-core travel market: seven CORE corridors (Historic District / River Street, "
         "Hutchinson Island, Midtown, Southside, SAV Airport / Garden City, Pooler, Gateway / I-95), one "
         "interstate CORRIDOR (Port Wentworth) and two FRINGE corridors (Richmond Hill; Wilmington / Skidaway "
         "Islands). Tybee Island is OBSERVED and REFUSED, preserved for a future " + FUTURE_SUBMARKET +
         " market; Hilton Head, Bluffton, Beaufort, Hardeeville, Rincon, Hinesville, Statesboro and Brunswick "
         "are named and REFUSED."),
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
        ("market_name", "Savannah, Georgia"),
        ("market_slug", MARKET_ID),
        ("state_name", "Georgia"),
        ("state_code", "GA"),
        ("primary_state_code", "GA"),
        ("states", ["GA"]),
        ("primary_city", "Savannah"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Savannah, Georgia | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Savannah -- the Historic District and River Street, Hutchinson "
         "Island, Midtown, the Southside, the Savannah / Hilton Head airport, Pooler, the I-95 Gateway and "
         "Richmond Hill -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Savannah"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A multi-core tourism, airport and interstate market -- not Savannah's city "
         "limits and not the coast. Nothing else admits a property: not a brand's 'Savannah Airport' or "
         "'Savannah I-95' marketing name, not a map pin, not a vacation-rental listing, not a competitor "
         "directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor. The Historic District, River Street and "
         "the Eastern Wharf share 31401 and are one corridor."),
        ("_census_membership_note",
         "Tybee Island is a separate beach-lodging market preserved for its own future market; Hilton Head "
         "Island, Bluffton, Beaufort, Hardeeville, Rincon, Hinesville, Statesboro, Brunswick and St. Simons "
         "Island are not absorbed. A property whose own page states one of their postal codes is OUTSIDE, "
         "however it is named. Individual vacation houses, condo units, rental-management portfolios, "
         "apartment rentals and timeshare inventory are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 -- Savannah multi-core travel-market geography and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-14"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Savannah's turn in the serialized release "
         "queue against the then-current live parent."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "Savannah's lodging cores (the Historic District and riverfront, Hutchinson Island, Midtown, the "
         "Southside, the SAV airport district, Pooler and the I-95 Gateway interchange) plus the Port "
         "Wentworth interstate corridor a Savannah traveller sleeps in by choice, and Richmond Hill and the "
         "eastern islands as FRINGE."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("tybee_island_ruling", OrderedDict([
            ("decision", "OUTSIDE -- PRESERVED_FOR_FUTURE_MARKET"),
            ("future_market_id", FUTURE_SUBMARKET),
            ("why",
             "Tybee Island is 18 miles and ~30 minutes from the Historic District at the end of US-80, a "
             "barrier-island beach town with its own municipality, its own 31328 postal code, its own beach "
             "motels and oceanfront resorts, and a lodging stock dominated by rental cottages and condos. "
             "Its visitors search and book 'Tybee Island' for the beach, not 'Savannah'. Forcing it in would "
             "publish beach resorts on a Savannah city page and bury a market that can stand on its own."),
            ("how_preserved",
             "Discovery OBSERVES it (an observation cell, the Georgia OSM extract and the brand city pages for "
             "Tybee Island). Every property seen there is carried in the census's non_admitted rows as "
             "OUTSIDE_MARKET with this reason, so the future market order starts from recorded identities "
             "rather than from zero."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Historic District / Downtown Savannah", "ADMITTED (CORE, historic-district, 31401)."),
            ("River Street / Eastern Wharf", "ADMITTED (CORE, historic-district, 31401) -- same postal code as the "
                                             "Historic District; reported as the River Street / Eastern Wharf overlay."),
            ("Midtown Savannah", "ADMITTED (CORE, midtown, 31405 / 31404)."),
            ("Southside Savannah", "ADMITTED (CORE, southside, 31406)."),
            ("Savannah / Hilton Head International Airport (SAV)", "ADMITTED (CORE, sav-airport, 31408); an 'airport' "
                                                                  "hotel whose own page states Pooler 31322 or Port "
                                                                  "Wentworth 31407 is filed there."),
            ("Pooler", "ADMITTED (CORE, pooler, 31322)."),
            ("I-95 / Gateway corridor", "ADMITTED (CORE, gateway-i95, 31419) -- exit 94; the exit 102-109 hotels sit "
                                        "in Pooler and Port Wentworth, exit 87-90 in Richmond Hill."),
            ("Hutchinson Island", "ADMITTED (CORE, hutchinson-island, 31421)."),
            ("Garden City", "ADMITTED (CORE, sav-airport, 31408) -- the airport sits inside it."),
            ("Port Wentworth", "ADMITTED (CORRIDOR, port-wentworth, 31407)."),
            ("Georgetown", "ADMITTED (CORE, gateway-i95, 31419)."),
            ("Richmond Hill", "ADMITTED (FRINGE, richmond-hill, 31324) -- Savannah-oriented I-95 lodging; Midway and "
                              "Hinesville beyond it are OUTSIDE."),
            ("Tybee Island", "OUTSIDE -- preserved for the future tybee-island-ga market."),
            ("Thunderbolt", "ADMITTED (CORE, midtown, 31404)."),
            ("Wilmington Island", "ADMITTED (FRINGE, eastern-islands, 31410)."),
            ("Skidaway Island", "ADMITTED (FRINGE, eastern-islands, 31411)."),
            ("Hilton Head Island / Bluffton / Beaufort", "OUTSIDE -- refused by name (order)."),
            ("Hardeeville / Ridgeland SC", "OUTSIDE -- South Carolina's own interchange cluster."),
            ("Statesboro / Brunswick / St. Simons Island", "OUTSIDE -- refused by name (order)."),
            ("Rincon / Effingham County", "OUTSIDE -- its own small cluster north of Port Wentworth."),
            ("Hinesville / Midway", "OUTSIDE -- the Fort Stewart market."),
            ("Hunter Army Airfield", "OUTSIDE -- military, non-public lodging."),
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
         "corridor is show_in_navigation/show_in_sitemap false until a registration order publishes it. "
         "River Street / Eastern Wharf, Georgetown and Thunderbolt cannot be separate pages under a "
         "postal-code partition; they are reported as overlays."),
        ("coverage_areas_are_a_reporting_overlay",
         "The order's named areas that share a postal code with another area (River Street / Eastern Wharf "
         "inside the Historic District's 31401; Georgetown inside the Gateway's 31419; Thunderbolt inside "
         "Midtown's 31404; Garden City beside the airport in 31408) are reported from the property's own "
         "stated street first and a nearest-anchor overlay on its pin second. The overlay decides nothing "
         "about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Five cells observe Tybee Island, Hardeeville, Bluffton, Rincon and Midway. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, boutique hotels, qualifying resorts and qualifying lodging "
         "establishments operated as lodging businesses: bookable nightly rooms or suites sold to the public "
         "under one establishment name, with an official property page and a front desk / on-site hotel "
         "operation. It NEVER admits: individual vacation houses, historic homes or carriage houses rented "
         "whole; condominium units or condo complexes rented unit-by-unit; property-management or realty "
         "rental portfolios (Savannah and Tybee vacation-rental companies and the like); Airbnb / Vrbo-style "
         "listings; app-only apartment-hotel units without a front desk; ordinary apartment communities "
         "(including brand-affiliated apartment inventory such as 'Apartments by Marriott Bonvoy' that is "
         "not operated as a hotel); private residences; and TIMESHARE / vacation-ownership inventory unless "
         "that property independently qualifies as a hotel. A historic inn or bed and breakfast is admitted "
         "only when it operates as an inn with bookable rooms on its own premises and an official site. "
         "Campgrounds, RV parks, hostels-as-dormitories and university housing are NON_LODGING."),
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
        dy = (float(lat) - la) * 111.0
        dx = (float(lng) - ln) * 111.0 * math.cos(math.radians(la))
        d = math.hypot(dx, dy)
        if d <= r and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def route_overlay(corridor_slug, street, lat, lng):
    """The order's named area a census row reports under. Reporting only.

    Historic District rows report as River Street / Eastern Wharf when their OWN
    stated street is a riverfront street, else as the Historic District. Midtown
    rows on Chatham Parkway and in Thunderbolt, Gateway rows in Georgetown and
    airport rows in Garden City report under those names. Other corridors report
    as themselves."""
    st = street or ""
    if corridor_slug == "historic-district":
        if RIVERFRONT_STREETS.search(st):
            return "River Street / Eastern Wharf"
        return "Historic District / Downtown"
    if corridor_slug == "midtown":
        if re.search(r"chatham p(ar)?kwy|chatham parkway|\bi-?16\b|mall p(ar)?kwy|stiles", st, re.I):
            return "Chatham Parkway / I-16"
        area = coverage_area(lat, lng)
        if area == "Thunderbolt":
            return "Thunderbolt"
        return "Midtown"
    if corridor_slug == "gateway-i95":
        if re.search(r"gateway|\bga-?204\b|highway 204|hwy 204", st, re.I):
            return "Gateway / I-95 exit 94"
        area = coverage_area(lat, lng)
        return area if area in ("Georgetown", "Gateway / I-95 exit 94") else "Gateway / I-95 exit 94"
    if corridor_slug == "sav-airport":
        area = coverage_area(lat, lng)
        return "Garden City" if area == "Garden City" else "SAV Airport"
    return {"hutchinson-island": "Hutchinson Island", "southside": "Southside", "pooler": "Pooler",
            "port-wentworth": "Port Wentworth / Crossroads", "richmond-hill": "Richmond Hill",
            "eastern-islands": "Wilmington / Skidaway Islands"}.get(corridor_slug)


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    muni = " ".join((city or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    return {"savannah": "Savannah", "pooler": "Pooler", "garden city": "Garden City",
            "port wentworth": "Port Wentworth", "richmond hill": "Richmond Hill",
            "thunderbolt": "Thunderbolt"}.get(muni)


def is_future_submarket(postal):
    """True when a postal code belongs to the preserved Tybee Island market."""
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
