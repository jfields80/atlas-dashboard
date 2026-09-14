"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- Phase 2 + 3 + 4: the Charleston travel market,
its beach / resort decisions and its corridors.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Charleston, South Carolina traveller lodging market -- a MULTI-CORE
historic, airport, interstate and coastal market, not Charleston's city limits and
not the whole Lowcountry -- stated as an explicit four-way rule (CORE / CORRIDOR /
FRINGE / OUTSIDE) before a single hotel is admitted, so no property is admitted or
refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page
states it, joined to the corridor registry below. The registry is a POSTAL-CODE
PARTITION: every admitted lodging ZIP is claimed by exactly one corridor, so a
property's corridor is a lookup and never a judgement. A brand's marketing name
("Charleston Airport", "Charleston / Mt. Pleasant", "Charleston North") never
admits and never places a property: a "Charleston Airport" hotel whose own page
states North Charleston 29418 is an airport / convention hotel, and a
"Charleston / Mt. Pleasant" hotel whose own page states 29464 is a Mount Pleasant
hotel.

A MUNICIPALITY REFUSAL INSIDE ONE ADMITTED ZIP
----------------------------------------------
Kiawah Island and Seabrook Island share 29455 with Johns Island. The ZIP stays
admitted for Johns Island, and a property whose OWN stated municipality is Kiawah
Island or Seabrook Island is refused inside it (MUNICIPALITY_REFUSALS) and
preserved for the future kiawah-seabrook-sc resort-island market.

THE FOUR CLASSES
----------------
CORE       Historic District / Downtown (29401 + downtown PO / campus codes);
           Upper Peninsula / Meeting Street / King Street north (29403, 29409);
           West Ashley (29407, 29414); North Charleston (29405, 29406, 29410
           Hanahan, 29420, PO codes); CHS Airport / Convention Center / Coliseum /
           Tanger (29418); Mount Pleasant / Patriots Point (29464, 29466, PO);
           Daniel Island / Cainhoy (29492).
CORRIDOR   James Island (29412); Summerville (29483, 29485, 29486, PO); Goose
           Creek (29445); Ladson / I-26 exit 203 (29456).
FRINGE     Folly Beach (29439); Isle of Palms / Sullivan's Island (29451, 29482);
           Johns Island (29455, Kiawah / Seabrook refused by municipality).
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision.

Outputs:
  scripts/pettripfinder/discovery/config/charleston_sc.json
  launch_packages/pettripfinder/markets/proposed/charleston-sc.json
  launch_packages/pettripfinder/markets/reports/charleston_sc_geography_001.json
  launch_packages/pettripfinder/markets/reports/charleston_sc_corridor_registry_001.json
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

WORK_ORDER = "PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "charleston-sc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "charleston_sc.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "charleston-sc.json")
REPORT_OUT = os.path.join(REPORTS, "charleston_sc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "charleston_sc_corridor_registry_001.json")

#: The future standalone market every Kiawah Island / Seabrook Island property is preserved for.
FUTURE_SUBMARKET = "kiawah-seabrook-sc"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("historic-district", "Historic District / Downtown Charleston", "Historic District & Downtown",
     "CORE", "charleston",
     ["29401", "29402", "29413", "29424", "29425"],
     "Charleston's lower peninsula: the Historic District, the French Quarter, King Street and Market "
     "Street, the Battery, the Waterfront, the College of Charleston and MUSC, and the downtown "
     "post-office box codes."),
    ("upper-peninsula", "Upper Peninsula / Meeting Street / Upper King", "Upper Peninsula", "CORE",
     "charleston",
     ["29403", "29409"],
     "The upper peninsula north of Calhoun Street: upper King and Meeting Streets, the Morrison Drive "
     "and Romney Street hotel corridor, Hampton Park, Wagener Terrace and The Citadel."),
    ("west-ashley", "West Ashley / Savannah Highway / I-526", "West Ashley", "CORE", "charleston",
     ["29407", "29414", "29416", "29417"],
     "West Ashley across the Ashley River: Savannah Highway (US-17), Sam Rittenberg Boulevard, the "
     "I-526 / Citadel Mall interchange, Ashley River Road and Bees Ferry."),
    ("north-charleston", "North Charleston / Rivers Avenue / Hanahan", "North Charleston", "CORE",
     "north charleston",
     ["29405", "29406", "29410", "29415", "29419", "29420", "29423"],
     "North Charleston outside the airport and Coliseum district: Rivers Avenue, Northwoods Mall and "
     "University Boulevard, Park Circle, Dorchester Road and the I-26 / I-526 interchanges, with the "
     "City of Hanahan beside it."),
    ("chs-airport-convention", "CHS Airport / Convention Center / Coliseum / Tanger Outlets",
     "Airport & Convention Center", "CORE", "north charleston",
     ["29418"],
     "Charleston International Airport (CHS) and the North Charleston Coliseum and Performing Arts "
     "Center / Charleston Area Convention Center district beside it: International Boulevard, "
     "Tanger Outlet Boulevard, Centre Pointe Drive, Montague Avenue and Ashley Phosphate Road."),
    ("mount-pleasant", "Mount Pleasant / Patriots Point", "Mount Pleasant", "CORE", "mount pleasant",
     ["29464", "29465", "29466"],
     "The Town of Mount Pleasant across the Ravenel Bridge: Patriots Point and the USS Yorktown, "
     "Shem Creek, Coleman Boulevard, Johnnie Dodds Boulevard (US-17), Towne Centre and north Mount "
     "Pleasant toward Isle of Palms."),
    ("daniel-island", "Daniel Island / Cainhoy", "Daniel Island", "CORE", "charleston",
     ["29492"],
     "Daniel Island between the Wando and Cooper Rivers (the Credit One Stadium and the I-526 "
     "business district) with Cainhoy and Clements Ferry Road."),
    ("james-island", "James Island / Folly Road", "James Island", "CORRIDOR", "charleston",
     ["29412", "29422"],
     "James Island on Folly Road and Maybank Highway between downtown and Folly Beach."),
    ("summerville", "Summerville / I-26 Exits 199", "Summerville", "CORRIDOR", "summerville",
     ["29483", "29484", "29485", "29486"],
     "The Town of Summerville on I-26 exit 199 (Main Street / US-17A), Ladson Road and Dorchester "
     "Road: the upper metro's hotel cluster twenty-five miles from downtown."),
    ("goose-creek", "Goose Creek / US-52", "Goose Creek", "CORRIDOR", "goose creek",
     ["29445"],
     "The City of Goose Creek on US-52 and US-176 beside Naval Weapons Station / Joint Base "
     "Charleston."),
    ("ladson", "Ladson / I-26 Exit 203", "Ladson", "CORRIDOR", "ladson",
     ["29456"],
     "Ladson at I-26 exit 203 (College Park Road) and the Exchange Park fairgrounds between North "
     "Charleston and Summerville."),
    ("folly-beach", "Folly Beach", "Folly Beach", "FRINGE", "folly beach",
     ["29439"],
     "The City of Folly Beach, Charleston's own beach at the end of Folly Road, twenty minutes from "
     "downtown."),
    ("isle-of-palms", "Isle of Palms / Sullivan's Island", "Isle of Palms", "FRINGE", "isle of palms",
     ["29451", "29482"],
     "Isle of Palms (including the Wild Dunes resort's hotels) and Sullivan's Island, the barrier "
     "islands beyond Mount Pleasant."),
    ("johns-island", "Johns Island / Maybank Highway", "Johns Island", "FRINGE", "johns island",
     ["29455", "29457"],
     "Johns Island on Maybank Highway, River Road and Bohicket Road. Kiawah Island and Seabrook "
     "Island share this postal code and are refused inside it by their own stated municipality."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. (postal code, municipality, why)
KIAWAH_WHY = ("Kiawah Island / Seabrook Island: gated resort barrier islands 45 minutes from downtown whose "
              "public lodging is one resort's hotel plus resort villa, cottage and private-club rental "
              "inventory, with its own 'Kiawah' search intent; PRESERVED for the future %s resort-island "
              "market, evaluated and refused here." % FUTURE_SUBMARKET)
MUNICIPALITY_REFUSALS = [
    ("29455", "kiawah island", KIAWAH_WHY),
    ("29455", "seabrook island", KIAWAH_WHY),
    ("29455", "kiawah", KIAWAH_WHY),
    ("29455", "seabrook", KIAWAH_WHY),
]
MUNICIPALITY_SPELLINGS = {
    "charleston sc": "charleston", "n charleston": "north charleston", "north charleston sc": "north charleston",
    "no charleston": "north charleston", "mt pleasant": "mount pleasant", "mt  pleasant": "mount pleasant",
    "mount pleasant sc": "mount pleasant", "isle of palms sc": "isle of palms", "iop": "isle of palms",
    "sullivans island": "sullivan's island", "folly beach sc": "folly beach", "summerville sc": "summerville",
    "goose creek sc": "goose creek", "ladson sc": "ladson", "johns island sc": "johns island",
    "john's island": "johns island", "kiawah island sc": "kiawah island", "seabrook island sc": "seabrook island",
    "daniel island": "charleston", "james island": "charleston", "west ashley": "charleston",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Kiawah Island / Seabrook Island (by municipality inside 29455)", "SC", [], KIAWAH_WHY),
    ("Joint Base Charleston (military)", "SC", ["29404"],
     "MILITARY_GOVERNMENT_NONPUBLIC -- installation lodging on Joint Base Charleston is not public "
     "lodging; evaluated and refused."),
    ("Moncks Corner / Bonneau / Pinopolis (Berkeley County north)", "SC", ["29461", "29431", "29468", "29479"],
     "Moncks Corner and Lake Moultrie, 30 miles north on US-52: its own small county-seat and lake lodging "
     "cluster; evaluated and refused."),
    ("Awendaw / McClellanville", "SC", ["29429", "29458"],
     "Rural US-17 north through the Francis Marion National Forest; no traveller lodging core of its own; "
     "evaluated and refused."),
    ("Ravenel / Hollywood / Meggett / Adams Run", "SC", ["29470", "29449", "29426"],
     "Rural US-17 south and SC-162; no hotel core; evaluated and refused."),
    ("Wadmalaw Island", "SC", ["29487"], "Rural sea island with no public hotel core; evaluated and refused."),
    ("Huger / Wando / Cordesville", "SC", ["29450", "29434"],
     "Rural Berkeley County north of Cainhoy; evaluated and refused."),
    ("Edisto Island / Edisto Beach", "SC", ["29438"],
     "Edisto Beach, its own beach and vacation-rental market; refused by name (order)."),
    ("Walterboro / Colleton County", "SC", ["29488"],
     "Walterboro's I-95 exit 53-57 cluster, its own interstate market; refused by name (order)."),
    ("St. George / Harleyville / Ridgeville / Dorchester (I-95 / I-26 upper Dorchester County)", "SC",
     ["29477", "29448", "29472", "29437"],
     "Upper Dorchester County and the I-95 / I-26 crossroads, a separate interstate cluster; evaluated and "
     "refused."),
    ("Beaufort / Port Royal / Lady's Island / Yemassee", "SC", ["29902", "29906", "29907", "29935", "29945"],
     "The Beaufort market; refused by name (order: do not absorb Beaufort)."),
    ("Hilton Head Island", "SC", ["29926", "29928", "29925", "29938"],
     "South Carolina resort island; refused by name (order: do not absorb Hilton Head Island)."),
    ("Bluffton / Okatie / Hardeeville / Ridgeland", "SC", ["29909", "29910", "29927", "29936"],
     "The southern Lowcountry; refused by name (order: do not absorb Bluffton)."),
    ("Georgetown / Pawleys Island", "SC", ["29440", "29442", "29585"],
     "Georgetown and the Waccamaw Neck, their own coastal market; refused by name (order)."),
    ("Myrtle Beach / Grand Strand", "SC", ["29572", "29575", "29577", "29579", "29582", "29588", "29576"],
     "The Grand Strand, its own beach market; refused by name (order)."),
    ("Santee / Orangeburg / Columbia", "SC", ["29142", "29115", "29118"],
     "The I-95 / I-26 inland markets; refused."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover refused neighbours so this order classifies them on evidence.
CELLS = [
    ("historic-district", "Charleston", "Historic District / Downtown", 32.7800, -79.9330, 1800, True),
    ("upper-peninsula", "Charleston", "Upper Peninsula / Meeting Street", 32.8040, -79.9430, 2200, True),
    ("west-ashley", "Charleston", "West Ashley / Savannah Highway", 32.8000, -80.0300, 5000, True),
    ("north-charleston-neck", "North Charleston", "North Charleston / Park Circle", 32.8600, -79.9800, 3500, True),
    ("north-charleston-rivers", "North Charleston", "Rivers Avenue / Northwoods / Hanahan", 32.9300, -80.0300, 5000, True),
    ("north-charleston-dorchester", "North Charleston", "Dorchester Road / I-26", 32.9300, -80.1000, 4500, True),
    ("chs-airport", "North Charleston", "CHS Airport", 32.8990, -80.0400, 3000, True),
    ("convention-tanger", "North Charleston", "Convention Center / Coliseum / Tanger", 32.8700, -80.0200, 2500, True),
    ("mount-pleasant", "Mount Pleasant", "Mount Pleasant / Patriots Point", 32.8300, -79.8500, 6000, True),
    ("daniel-island", "Charleston", "Daniel Island", 32.8650, -79.9100, 3500, True),
    ("james-island", "Charleston", "James Island", 32.7250, -79.9550, 4000, True),
    ("summerville", "Summerville", "Summerville", 33.0000, -80.1800, 7000, True),
    ("goose-creek", "Goose Creek", "Goose Creek", 32.9900, -80.0300, 5000, True),
    ("ladson", "Ladson", "Ladson / I-26 exit 203", 32.9850, -80.1050, 3500, True),
    ("folly-beach", "Folly Beach", "Folly Beach", 32.6600, -79.9400, 4000, True),
    ("isle-of-palms", "Isle of Palms", "Isle of Palms / Sullivan's Island", 32.7900, -79.7900, 6000, True),
    ("johns-island", "Johns Island", "Johns Island", 32.7100, -80.0700, 7000, True),
    # observation only -- the preserved resort islands and refused neighbours
    ("obs-kiawah-seabrook", "Kiawah Island", "Kiawah / Seabrook -- OBSERVATION ONLY", 32.6000, -80.1200, 8000, False),
    ("obs-moncks-corner", "Moncks Corner", "Moncks Corner -- OBSERVATION ONLY", 33.1950, -80.0100, 7000, False),
    ("obs-awendaw", "Awendaw", "Awendaw -- OBSERVATION ONLY", 32.9900, -79.6500, 8000, False),
    ("obs-ravenel", "Ravenel", "Ravenel / Hollywood -- OBSERVATION ONLY", 32.7700, -80.2400, 7000, False),
    ("obs-edisto", "Edisto Island", "Edisto -- OBSERVATION ONLY", 32.5300, -80.3000, 9000, False),
]

BOUNDS = {
    "min_lat": 32.45,
    "max_lat": 33.30,
    "min_lng": -80.45,
    "max_lng": -79.55,
}

#: Reporting overlay only (never membership): the areas the order names.
COVERAGE_AREAS = [
    ("Historic District / Downtown", 32.7800, -79.9330, 1.6),
    ("Upper Peninsula / Meeting Street", 32.8040, -79.9430, 2.0),
    ("West Ashley", 32.8000, -80.0300, 5.0),
    ("North Charleston", 32.8900, -80.0100, 7.0),
    ("CHS Airport", 32.8986, -80.0405, 1.9),
    ("Convention Center / Coliseum / Tanger", 32.8700, -80.0200, 1.8),
    ("Mount Pleasant", 32.8320, -79.8280, 7.0),
    ("Patriots Point", 32.7900, -79.9050, 1.3),
    ("Daniel Island", 32.8650, -79.9100, 3.0),
    ("Isle of Palms", 32.7950, -79.7700, 5.0),
    ("Sullivan's Island", 32.7630, -79.8370, 2.0),
    ("Folly Beach", 32.6550, -79.9400, 4.0),
    ("James Island", 32.7250, -79.9550, 4.0),
    ("Johns Island", 32.7100, -80.0700, 7.0),
    ("Kiawah / Seabrook", 32.6000, -80.1200, 9.0),
    ("Goose Creek", 32.9900, -80.0300, 5.0),
    ("Summerville", 33.0100, -80.1800, 7.0),
    ("Ladson", 32.9850, -80.1050, 3.0),
    ("Hanahan", 32.9200, -80.0200, 3.0),
]


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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Charleston" % name),
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
            ("state_code", "SC"),
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
        ("state_code", "SC"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Charleston, SC multi-core historic, airport, interstate and coastal lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", "SC"),
        ("states", ["SC"]),
        ("country", "US"),
        ("market_center", {"lat": 32.780, "lng": -79.933}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- south over "
             "Kiawah and Seabrook Islands toward Edisto, north over Moncks Corner, east over Awendaw and west "
             "over Ravenel -- so that " + WORK_ORDER + " classifies those properties on evidence instead of being "
             "blind to them. Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A multi-core travel market: seven CORE corridors (Historic District, Upper Peninsula, "
         "West Ashley, North Charleston, CHS Airport / Convention Center, Mount Pleasant, Daniel Island), four "
         "CORRIDOR corridors (James Island, Summerville, Goose Creek, Ladson) and three FRINGE corridors (Folly "
         "Beach, Isle of Palms / Sullivan's Island, Johns Island). Kiawah and Seabrook Islands are OBSERVED and "
         "REFUSED, preserved for a future " + FUTURE_SUBMARKET + " market; Moncks Corner, Awendaw, Ravenel, "
         "Edisto, Walterboro, Beaufort, Hilton Head, Bluffton, Georgetown and Myrtle Beach are named and REFUSED."),
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
        ("market_name", "Charleston, South Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "South Carolina"),
        ("state_code", "SC"),
        ("primary_state_code", "SC"),
        ("states", ["SC"]),
        ("primary_city", "Charleston"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Charleston, South Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Charleston -- the Historic District and upper peninsula, West "
         "Ashley, North Charleston and the CHS airport, Mount Pleasant, Daniel Island, Summerville and the "
         "beaches -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Charleston"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A multi-core historic, airport, interstate and coastal market -- not "
         "Charleston's city limits and not the Lowcountry. Nothing else admits a property: not a brand's "
         "'Charleston Airport' or 'Charleston / Mt. Pleasant' marketing name, not a map pin, not a "
         "vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor. The CHS airport and the Convention Center "
         "/ Coliseum / Tanger district share 29418 and are one corridor; Patriots Point shares 29464 with "
         "Mount Pleasant."),
        ("_census_membership_note",
         "Kiawah Island and Seabrook Island are a separate resort-island lodging market preserved for its "
         "own future market; Beaufort, Hilton Head Island, Bluffton, Georgetown, Myrtle Beach, Edisto and "
         "Walterboro are not absorbed. A property whose own page states one of their postal codes or "
         "municipalities is OUTSIDE, however it is named. Individual vacation houses, condo units, "
         "rental-management portfolios, resort villa programmes, apartment rentals and timeshare inventory "
         "are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    beach = OrderedDict([
        ("Isle of Palms", OrderedDict([
            ("decision", "B -- FRINGE inventory, admitted as its own corridor (isle-of-palms, 29451)"),
            ("why",
             "Isle of Palms is reached from Mount Pleasant in minutes over the Connector, is part of the "
             "Charleston metro and the Charleston visitor bureau's own lodging inventory, and its hotels (the "
             "Wild Dunes resort's Sweetgrass Inn and Boardwalk Inn, and the island's small oceanfront hotels) "
             "sell Charleston-area beach stays. Its hotel count is small and its vacation-rental stock is large "
             "and refused, so it cannot stand alone as a hotel market: FRINGE, never core."),
        ])),
        ("Sullivan's Island", OrderedDict([
            ("decision", "B -- FRINGE, folded into the isle-of-palms corridor (29482)"),
            ("why", "A residential island with essentially no public hotel stock; admitted only so a qualifying "
                    "inn there is classified rather than invisible."),
        ])),
        ("Folly Beach", OrderedDict([
            ("decision", "B -- FRINGE inventory, admitted as its own corridor (folly-beach, 29439)"),
            ("why",
             "Folly Beach is 'Charleston's beach': twenty minutes down Folly Road from downtown through James "
             "Island, with a handful of oceanfront hotels and inns that Charleston visitors book for a beach "
             "night. The town's lodging is dominated by rental houses, which are refused, and its hotel count "
             "cannot carry a standalone market."),
        ])),
        ("Kiawah Island", OrderedDict([
            ("decision", "C -- FUTURE standalone / submarket opportunity (%s); OUTSIDE here" % FUTURE_SUBMARKET),
            ("why",
             "A gated resort island 45 minutes from downtown. Its public lodging is one resort's hotel (The "
             "Sanctuary) plus resort villa, cottage and home rental programmes; its search intent is "
             "'Kiawah Island resort' and golf, not 'Charleston hotels'. Admitting it would publish a gated "
             "destination resort on a Charleston page and fold its villa programme into a hotel census."),
        ])),
        ("Seabrook Island", OrderedDict([
            ("decision", "C -- FUTURE submarket with Kiawah (%s); OUTSIDE here" % FUTURE_SUBMARKET),
            ("why",
             "A private, gated club community whose lodging is member / guest villa and home rentals; no "
             "public hotel identity."),
        ])),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 -- Charleston multi-core travel-market geography, beach / resort decisions and "
                  "corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-14"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Charleston's turn in the serialized release "
         "queue against the then-current live parent."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry, with Kiawah Island / Seabrook Island refused by their own stated municipality inside "
         "29455. Nothing else admits a property."),
        ("travel_market",
         "Charleston's lodging cores (the Historic District, the upper peninsula, West Ashley, North "
         "Charleston, the CHS airport and Convention Center district, Mount Pleasant and Daniel Island), "
         "the interstate and suburban corridors a Charleston traveller sleeps in by choice (James Island, "
         "Summerville, Goose Creek, Ladson), and Charleston's own beaches as FRINGE (Folly Beach, Isle of "
         "Palms / Sullivan's Island) with Johns Island."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("beach_resort_decisions", beach),
        ("evaluated_inclusions", OrderedDict([
            ("Charleston Historic District / Downtown", "ADMITTED (CORE, historic-district, 29401)."),
            ("Upper Peninsula / Meeting Street corridor", "ADMITTED (CORE, upper-peninsula, 29403)."),
            ("West Ashley", "ADMITTED (CORE, west-ashley, 29407 / 29414)."),
            ("North Charleston", "ADMITTED (CORE, north-charleston, 29405 / 29406 / 29420)."),
            ("Charleston International Airport / CHS", "ADMITTED (CORE, chs-airport-convention, 29418) -- shares "
                                                       "29418 with the Convention Center district; reported "
                                                       "as an overlay."),
            ("Tanger / Convention Center / Coliseum", "ADMITTED (CORE, chs-airport-convention, 29418)."),
            ("Mount Pleasant", "ADMITTED (CORE, mount-pleasant, 29464 / 29466)."),
            ("Patriots Point", "ADMITTED (CORE, mount-pleasant, 29464) -- reported as an overlay."),
            ("Daniel Island", "ADMITTED (CORE, daniel-island, 29492)."),
            ("Isle of Palms", "ADMITTED (FRINGE, isle-of-palms, 29451)."),
            ("Sullivan's Island", "ADMITTED (FRINGE, isle-of-palms, 29482)."),
            ("Folly Beach", "ADMITTED (FRINGE, folly-beach, 29439)."),
            ("James Island", "ADMITTED (CORRIDOR, james-island, 29412)."),
            ("Johns Island", "ADMITTED (FRINGE, johns-island, 29455) -- Kiawah / Seabrook refused inside it."),
            ("Kiawah / Seabrook resort lodging", "OUTSIDE -- preserved for the future %s market." % FUTURE_SUBMARKET),
            ("Goose Creek", "ADMITTED (CORRIDOR, goose-creek, 29445)."),
            ("Summerville", "ADMITTED (CORRIDOR, summerville, 29483 / 29485 / 29486)."),
            ("Ladson", "ADMITTED (CORRIDOR, ladson, 29456) -- the I-26 exit 203 cluster between North "
                       "Charleston and Summerville."),
            ("Hanahan", "ADMITTED (CORE, north-charleston, 29410) -- contiguous with North Charleston; too small "
                        "for its own corridor."),
            ("Moncks Corner", "OUTSIDE -- 30 miles north, its own lake / county-seat cluster."),
            ("Awendaw", "OUTSIDE -- rural national-forest US-17 with no lodging core."),
            ("Ravenel", "OUTSIDE -- rural US-17 south with no hotel core."),
            ("Beaufort / Hilton Head Island / Bluffton / Georgetown / Myrtle Beach / Edisto / Walterboro",
             "OUTSIDE -- refused by name (order)."),
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
         "The CHS airport and the Convention Center / Tanger district share 29418, and Patriots Point shares "
         "29464 with Mount Pleasant, so they cannot be separate pages under a postal-code partition; they are "
         "reported as overlays."),
        ("coverage_areas_are_a_reporting_overlay",
         "The order's named areas that share a postal code with another area are reported from the "
         "property's own stated street first and a nearest-anchor overlay on its pin second. The overlay "
         "decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("municipality_refusals", [OrderedDict([("postal_code", z), ("municipality", m), ("why", w)])
                                   for z, m, w in MUNICIPALITY_REFUSALS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Five cells observe Kiawah / Seabrook, Moncks Corner, Awendaw, Ravenel and Edisto. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, boutique hotels, qualifying resorts and qualifying lodging "
         "establishments operated as lodging businesses: bookable nightly rooms or suites sold to the public "
         "under one establishment name, with an official property page and a front desk / on-site hotel "
         "operation. It NEVER admits: individual vacation houses, historic homes, carriage houses or "
         "single-house rentals rented whole; condominium units or condo complexes rented unit-by-unit; "
         "property-management or realty rental portfolios (Isle of Palms, Folly Beach, Kiawah and downtown "
         "vacation-rental companies and the like); resort villa rental programmes; Airbnb / Vrbo-style "
         "listings; app-only apartment-hotel units without a front desk; ordinary apartment communities; "
         "private residences; and TIMESHARE / vacation-ownership inventory unless that property independently "
         "qualifies as a hotel. A historic inn or bed and breakfast is admitted only when it operates as an "
         "inn with bookable rooms on its own premises and an official site. Campgrounds, RV parks, "
         "hostels-as-dormitories and university housing are NON_LODGING."),
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


def coverage_area(lat, lng, names=None):
    """The overlay area a coordinate reports under, or None. Reporting only."""
    if lat is None or lng is None:
        return None
    best = None
    for name, la, ln, r in COVERAGE_AREAS:
        if names is not None and name not in names:
            continue
        dy = (float(lat) - la) * 111.0
        dx = (float(lng) - ln) * 111.0 * math.cos(math.radians(la))
        d = math.hypot(dx, dy)
        if d <= r and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def route_overlay(corridor_slug, street, lat, lng):
    """The order's named area a census row reports under. Reporting only."""
    st = street or ""
    if corridor_slug == "chs-airport-convention":
        if re.search(r"tanger|coliseum|centre pointe|center pointe|mall dr|convention", st, re.I):
            return "Convention Center / Coliseum / Tanger"
        if re.search(r"international blvd|aviation|airport|arco", st, re.I):
            area = coverage_area(lat, lng, ("CHS Airport", "Convention Center / Coliseum / Tanger"))
            return area or "CHS Airport"
        area = coverage_area(lat, lng, ("CHS Airport", "Convention Center / Coliseum / Tanger"))
        return area or "CHS Airport / Convention (other)"
    if corridor_slug == "mount-pleasant":
        if re.search(r"patriots point", st, re.I):
            return "Patriots Point"
        area = coverage_area(lat, lng, ("Patriots Point",))
        return area or "Mount Pleasant"
    if corridor_slug == "upper-peninsula":
        if re.search(r"\bmeeting st", st, re.I):
            return "Upper Peninsula / Meeting Street"
        return "Upper Peninsula"
    if corridor_slug == "north-charleston":
        area = coverage_area(lat, lng, ("Hanahan",))
        return "Hanahan" if area else "North Charleston"
    if corridor_slug == "isle-of-palms":
        area = coverage_area(lat, lng, ("Sullivan's Island",))
        return "Sullivan's Island" if area else "Isle of Palms"
    return {"historic-district": "Historic District / Downtown", "west-ashley": "West Ashley",
            "daniel-island": "Daniel Island", "james-island": "James Island", "summerville": "Summerville",
            "goose-creek": "Goose Creek", "ladson": "Ladson", "folly-beach": "Folly Beach",
            "johns-island": "Johns Island"}.get(corridor_slug)


def normalize_municipality(city):
    muni = " ".join((city or "").lower().replace(".", " ").replace(",", " ").split())
    return MUNICIPALITY_SPELLINGS.get(muni, muni)


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    muni = normalize_municipality(city)
    return {"charleston": "Charleston", "north charleston": "North Charleston",
            "mount pleasant": "Mount Pleasant", "summerville": "Summerville", "goose creek": "Goose Creek",
            "ladson": "Ladson", "hanahan": "Hanahan", "folly beach": "Folly Beach",
            "isle of palms": "Isle of Palms", "sullivan's island": "Sullivan's Island",
            "johns island": "Johns Island"}.get(muni)


def is_future_submarket(postal, municipality=None):
    """True when a property belongs to the preserved Kiawah / Seabrook market."""
    z = (postal or "").strip()[:5]
    muni = normalize_municipality(municipality)
    return any(z == rz and muni == rm for rz, rm, _w in MUNICIPALITY_REFUSALS)


def classify_postal(postal, municipality):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and
    municipality. The one membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = normalize_municipality(municipality)
    for slug, _name, _area, klass, _m, zips, _desc in CORRIDORS:
        if z in zips:
            for rz, rmuni, why in MUNICIPALITY_REFUSALS:
                if rz == z and rmuni == muni:
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
