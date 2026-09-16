"""PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 -- Phases 3, 4 and 7: the Tampa Bay travel market.

Built from zero on the current verified-live lineage (Savannah LIVE, 1fa43a48). Tampa V1
(worker/ptf-tampa-fl-market-001) is a historical comparison only; nothing here is read from it.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Tampa Bay traveller lodging market, stated as an explicit CORE / CORRIDOR / FRINGE /
OUTSIDE rule (with FUTURE_STANDALONE markets named inside OUTSIDE) before a single hotel is admitted,
so no property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
-------------------
Membership is decided by the property's OWN postal code, as its own official page (or the Florida DBPR
public-lodging licence, which is the state's own record of the licensed premises) states it, joined to
the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP is
claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's
marketing name ("Tampa Bay Area", "Near the Beaches", "Tampa Airport Hotel") never admits and never
places a property: a hotel whose own address states St. Pete Beach 33706 is a St. Pete Beach / Treasure
Island hotel, not a Tampa hotel.

THE SPLIT TEST (PHASE 4) IS RECORDED IN THE REPORT
---------------------------------------------------
Tampa, St. Petersburg and Clearwater/the Gulf beaches sit inside a single Census-defined
Tampa-St. Petersburg-Clearwater MSA, joined by causeway/interstate connectivity (Howard Frankland,
Courtney Campbell, Gandy, Sunshine Skyway) and a shared "Tampa Bay" travel identity, even where
Visit Tampa Bay and Visit St. Pete-Clearwater run separate CVBs. This order treats them as ONE market
(tampa-fl), with St. Petersburg and Clearwater/the Gulf beaches kept as named CORRIDOR tiers rather than
folded anonymously into generic Tampa corridors -- the separate-CVB / separate-county reality is
preserved as corridor-level distinction, not as three markets. Standalone-market optionality is
preserved for a possible future 'pinellas-beaches-fl' or 'st-petersburg-fl' split; this build does not
force it. Orlando is its own separate, already-built market and is OUTSIDE by name.

WHY SOME NAMED PLACES ARE OVERLAYS, NOT SEPARATE CORRIDORS
------------------------------------------------------------
Rocky Point and Tampa International Airport (TPA) share ZIP 33607 with the general Westshore business
district; Raymond James Stadium sits inside the same 33607 footprint. A postal partition cannot place
them in two corridors without splitting a code other hotels depend on, so Westshore / TPA Airport / Rocky
Point / Raymond James Stadium is ONE corridor, and each named place is reported as a STREET-AND-PIN
OVERLAY on every census row. St. Pete Beach and Treasure Island share ZIP 33706 for the same reason and
are one corridor. Temple Terrace's own postal footprint (33617) is shared with north Tampa / USF, so it
is folded into the Busch Gardens / USF corridor as an overlay. Gulfport shares 33707 with mid-Pinellas
Seminole / Pinellas Park (not with the St. Petersburg corridor's own ZIPs) and is reported there.

VACATION RENTALS, TIMESHARES AND RESORT RESIDENCES
----------------------------------------------------
The rule is stated here once and applied by the census: Florida DBPR licenses every condominium unit
(CNDO) and vacation dwelling (DWEL) as public lodging, and Tampa Bay -- especially the Gulf beaches --
carries thousands of them. None is a hotel identity. A mixed hotel / timeshare / condo campus is
admitted only as the exact hotel premises its own operator sells as a hotel.

Nothing here fetches, spends or deploys. The market document goes to the PROPOSED path (shadow until
registered); the registry's markets/<id>.json is never written.

Outputs:
  scripts/pettripfinder/discovery/config/tampa_fl.json
  launch_packages/pettripfinder/markets/proposed/tampa-fl.json
  launch_packages/pettripfinder/markets/reports/tampa_fl_v2_geography_001.json
  launch_packages/pettripfinder/markets/reports/tampa_fl_v2_corridor_registry_001.json
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

WORK_ORDER = "PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "tampa-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "tampa_fl.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "tampa-fl.json")
REPORT_OUT = os.path.join(REPORTS, "tampa_fl_v2_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "tampa_fl_v2_corridor_registry_001.json")
AS_OF = "2026-09-15"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
#: Every ZIP below was reverse-looked-up against a live ZIP database on AS_OF to confirm its
#: real-world place name before being assigned to a corridor.
CORRIDORS = [
    ("downtown-riverwalk", "Downtown Tampa / Riverwalk / Channelside / Hyde Park", "Downtown Tampa",
     "CORE", "tampa",
     ["33602", "33603", "33606"],
     "Downtown Tampa's Riverwalk, Channelside, the Tampa Convention Center and Amalie Arena, Tampa "
     "Heights, and Hyde Park / Davis Islands / Bayshore Boulevard immediately south and west of downtown."),
    ("ybor-city", "Ybor City", "Ybor City", "CORE", "tampa",
     ["33605"],
     "Ybor City's historic cigar-factory district and 7th Avenue / La Sexta, and the East Tampa blocks "
     "immediately around it."),
    ("westshore-airport-rocky-point", "Westshore / Tampa International Airport (TPA) / Rocky Point / "
     "Raymond James Stadium", "Westshore & TPA Airport", "CORE", "tampa",
     ["33607", "33609", "33614", "33615"],
     "Tampa's largest hotel cluster: Tampa International Airport (TPA), the Westshore business district "
     "and International Plaza on Westshore Boulevard, the Rocky Point peninsula on the Courtney Campbell "
     "Causeway, Raymond James Stadium on North Dale Mabry Highway, and Town 'n' Country to the west. "
     "Rocky Point, TPA and the stadium each share ZIP 33607 with the general Westshore footprint and are "
     "reported as street-and-pin overlays, never separate corridors."),
    ("busch-gardens-usf", "Busch Gardens / USF / Fowler Avenue / Temple Terrace", "Busch Gardens & USF",
     "CORE", "tampa",
     ["33612", "33613", "33617", "33637"],
     "Busch Gardens Tampa Bay and Adventure Island, the University of South Florida (USF) and Fowler "
     "Avenue, and Telecom Park / I-75 at Fowler. The incorporated city of Temple Terrace shares ZIP 33617 "
     "with this footprint and is reported as an overlay, not a separate corridor."),
    ("brandon", "Brandon / Seffner", "Brandon", "CORE", "brandon",
     ["33510", "33511", "33584"],
     "Brandon's US-301 / SR-60 hotel cluster at the Selmon Expressway and I-75, and neighbouring Seffner."),
    ("east-tampa-i75", "East Tampa / Causeway Boulevard / I-75", "East Tampa", "CORE", "tampa",
     ["33610", "33619"],
     "East Tampa's Adamo Drive / US-301 industrial corridor, and Causeway Boulevard / Palm River at the "
     "I-75 / I-4 interchange, both extended-stay and interstate motel clusters."),
    ("st-petersburg-downtown", "Downtown St. Petersburg", "Downtown St. Petersburg", "CORRIDOR",
     "st. petersburg",
     ["33701", "33705"],
     "Downtown St. Petersburg's Beach Drive waterfront, the EDGE District, the St. Pete Pier, Tropicana "
     "Field and the historic Old Northeast, the state's own distinct downtown hotel cluster on the bay."),
    ("st-petersburg", "St. Petersburg", "St. Petersburg", "CORRIDOR", "st. petersburg",
     ["33702", "33703", "33704", "33710", "33712", "33713", "33714", "33716"],
     "St. Petersburg outside its own downtown: the Skyway Marina District, Tyrone, Central Avenue west of "
     "downtown, and the Gandy / Carillon office corridor toward the Howard Frankland and Gandy bridges."),
    ("clearwater-downtown", "Clearwater", "Clearwater", "CORRIDOR", "clearwater",
     ["33755", "33756"],
     "Clearwater's mainland downtown and US-19 corridor, across the Memorial Causeway from Clearwater "
     "Beach."),
    ("clearwater-beach", "Clearwater Beach", "Clearwater Beach", "CORRIDOR", "clearwater",
     ["33767"],
     "Clearwater Beach's barrier-island resort strip on Gulfview Boulevard and Mandalay Avenue, one of the "
     "Gulf coast's largest beach hotel concentrations."),
    ("st-pete-beach-treasure-island", "St. Pete Beach / Treasure Island", "St. Pete Beach", "CORRIDOR",
     "st. pete beach",
     ["33706"],
     "St. Pete Beach and Treasure Island share ZIP 33706 on the same barrier island south of Madeira "
     "Beach; Gulf Boulevard's resort and motel strip runs continuously through both towns."),
    ("madeira-redington-indian-rocks", "Madeira Beach / Redington Beaches / Indian Rocks Beach / "
     "Belleair Beach", "Madeira Beach", "CORRIDOR", "madeira beach",
     ["33708", "33785", "33786"],
     "The barrier-island beach towns between John's Pass and Belleair Beach: Madeira Beach, North and "
     "South Redington Beach, Redington Shores, Indian Rocks Beach and Belleair Beach."),
    ("largo", "Largo", "Largo", "CORRIDOR", "largo",
     ["33770", "33771", "33773", "33774", "33777", "33778", "33779"],
     "Largo, mid-Pinellas County's largest inland city, on US-19 between Clearwater and the beaches."),
    ("wesley-chapel-new-tampa", "Wesley Chapel / New Tampa", "Wesley Chapel", "FRINGE", "wesley chapel",
     ["33647", "33543", "33544", "33545"],
     "New Tampa (Hillsborough County's own 33647) and Wesley Chapel / Zephyrhills just north in Pasco "
     "County, along I-75's Bruce B. Downs corridor; careful evaluation, admitted at FRINGE density."),
    ("south-hillsborough", "Riverview / Apollo Beach / Ruskin / Sun City Center", "South Hillsborough",
     "FRINGE", "riverview",
     ["33569", "33578", "33579", "33570", "33572", "33598"],
     "South Hillsborough County along US-41 and I-75 toward the Sunshine Skyway: Riverview, Apollo Beach, "
     "Ruskin, Sun City Center and Wimauma; careful evaluation, admitted at FRINGE density."),
    ("plant-city", "Plant City", "Plant City", "FRINGE", "plant city",
     ["33563", "33565", "33566", "33567"],
     "Plant City on I-4 at the Hillsborough / Polk county line; careful evaluation, admitted at FRINGE "
     "density."),
    ("tarpon-dunedin", "Tarpon Springs / Dunedin", "Tarpon Springs", "FRINGE", "tarpon springs",
     ["34688", "34689", "34698"],
     "Tarpon Springs' Sponge Docks and Dunedin's Pinellas Trail / downtown, north Pinellas County; careful "
     "evaluation, admitted at FRINGE density."),
    ("mid-pinellas", "Seminole / Pinellas Park / Gulfport", "Mid-Pinellas", "FRINGE", "seminole",
     ["33707", "33772", "33776", "33781", "33782"],
     "Inland mid-Pinellas County between Largo and St. Petersburg: Seminole, Pinellas Park and Gulfport "
     "(which shares ZIP 33707 with this corridor, not with the St. Petersburg corridor's own ZIPs); "
     "careful evaluation, admitted at FRINGE density."),
    ("safety-harbor-oldsmar-palm-harbor", "Safety Harbor / Oldsmar / Palm Harbor", "Safety Harbor",
     "FRINGE", "safety harbor",
     ["34677", "34683", "34695"],
     "Upper Tampa Bay's Safety Harbor, Oldsmar (at the Courtney Campbell / Veterans Expressway "
     "interchange) and Palm Harbor; careful evaluation, admitted at FRINGE density."),
]

MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "saint petersburg": "st. petersburg", "st petersburg": "st. petersburg", "saint pete beach": "st. pete beach",
    "st pete beach": "st. pete beach", "saint pete": "st. petersburg", "st pete": "st. petersburg",
    "temple terrace fl": "tampa", "gulfport fl": "seminole",
}

#: FUTURE standalone markets this order preserves by name.
FUTURE_MARKETS = OrderedDict([
    ("pinellas-beaches-fl", "The Gulf beaches (Clearwater Beach through St. Pete Beach / Treasure Island / "
                            "Madeira Beach) as their own beach-resort market, if traveler behaviour later "
                            "diverges far enough from the Tampa Bay core to justify a split"),
    ("st-petersburg-fl", "St. Petersburg (with its own CVB, Visit St. Pete-Clearwater) as its own standalone "
                         "market, if it later grows enough distinct lodging demand to stand alone"),
    ("sarasota-bradenton-fl", "Sarasota / Bradenton / Siesta Key -- its own Gulf coast resort and arts market "
                              "immediately south of the Sunshine Skyway"),
    ("lakeland-winter-haven-fl", "Lakeland / Winter Haven / Legoland Florida -- Polk County's I-4 midpoint "
                                 "market between Tampa and Orlando (a separate PetTripFinder market order may "
                                 "also reach it from the Orlando side)"),
    ("spring-hill-brooksville-fl", "Spring Hill / Brooksville / Hernando County -- its own small-market "
                                   "lodging area on US-19 north of the Tampa Bay core"),
])

#: Municipalities OUTSIDE the admitted market, each with the reason. A FUTURE_STANDALONE row names its market.
OUTSIDE = [
    ("Sarasota", "FL", ["34236", "34237", "34239", "34242"],
     "Sarasota's downtown and Siesta Key; FUTURE_STANDALONE sarasota-bradenton-fl; refused by name (order)."),
    ("Bradenton", "FL", ["34205", "34208", "34209", "34210"],
     "Bradenton; FUTURE_STANDALONE sarasota-bradenton-fl; refused by name (order)."),
    ("Anna Maria Island (Anna Maria / Bradenton Beach / Longboat Key)", "FL", ["34216", "34217", "34228"],
     "Anna Maria Island's three barrier-island towns, south of the Sunshine Skyway in Manatee County; "
     "FUTURE_STANDALONE sarasota-bradenton-fl; refused by name (order)."),
    ("Lakeland", "FL", ["33801", "33803", "33805", "33809", "33810", "33811", "33812", "33813", "33815"],
     "FUTURE_STANDALONE lakeland-winter-haven-fl; refused by name (order)."),
    ("Spring Hill / Brooksville", "FL", ["34606", "34608", "34609", "34610", "34601", "34602", "34604",
                                         "34613", "34614"],
     "Hernando County; FUTURE_STANDALONE spring-hill-brooksville-fl; refused by name (order)."),
    ("Orlando / Greater Orlando", "FL", [],
     "FUTURE / separate market orlando-fl, already built; refused by name (order). No Orlando-oriented "
     "inventory (theme-park marketing using 'near Orlando' or 'near Tampa' language for the same building) "
     "is admitted here on marketing alone -- the property's own postal code governs."),
    ("Lithia / Fishhawk", "FL", ["33547"],
     "rural southeast Hillsborough County beyond Brandon, weak hotel intent; careful evaluation, refused."),
]

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government).
NONPUBLIC_NAMES = {}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-riverwalk", "Tampa", "Downtown Tampa / Riverwalk / Channelside / Hyde Park", 27.9470, -82.4580, 2500, True),
    ("ybor-city", "Tampa", "Ybor City", 27.9610, -82.4370, 1600, True),
    ("westshore-airport-rocky-point", "Tampa", "Westshore / TPA Airport / Rocky Point / Raymond James Stadium",
     27.9630, -82.5170, 3800, True),
    ("busch-gardens-usf", "Tampa", "Busch Gardens / USF / Temple Terrace", 28.0380, -82.4200, 4200, True),
    ("brandon", "Brandon", "Brandon / Seffner", 27.9380, -82.2860, 4500, True),
    ("east-tampa-i75", "Tampa", "East Tampa / Causeway Blvd / I-75", 27.9550, -82.3500, 3600, True),
    ("st-petersburg-downtown", "St. Petersburg", "Downtown St. Petersburg", 27.7730, -82.6390, 2200, True),
    ("st-petersburg", "St. Petersburg", "St. Petersburg", 27.7900, -82.6650, 4500, True),
    ("clearwater-downtown", "Clearwater", "Clearwater", 27.9660, -82.8000, 2800, True),
    ("clearwater-beach", "Clearwater", "Clearwater Beach", 27.9770, -82.8300, 1800, True),
    ("st-pete-beach-treasure-island", "St. Pete Beach", "St. Pete Beach / Treasure Island", 27.7450, -82.7550, 2800, True),
    ("madeira-redington-indian-rocks", "Madeira Beach", "Madeira Beach / Redington / Indian Rocks Beach",
     27.7970, -82.7900, 3200, True),
    ("largo", "Largo", "Largo", 27.9090, -82.7870, 3000, True),
    ("wesley-chapel-new-tampa", "Wesley Chapel", "Wesley Chapel / New Tampa", 28.1500, -82.3200, 6000, True),
    ("south-hillsborough", "Riverview", "Riverview / Apollo Beach / Ruskin", 27.7900, -82.3400, 6500, True),
    ("plant-city", "Plant City", "Plant City", 28.0200, -82.1100, 4000, True),
    ("tarpon-dunedin", "Tarpon Springs", "Tarpon Springs / Dunedin", 28.0900, -82.7600, 4500, True),
    ("mid-pinellas", "Seminole", "Seminole / Pinellas Park / Gulfport", 27.8500, -82.7500, 4200, True),
    ("safety-harbor-oldsmar-palm-harbor", "Safety Harbor", "Safety Harbor / Oldsmar / Palm Harbor",
     28.0200, -82.6900, 4800, True),
    ("obs-sarasota-bradenton", "Sarasota", "Sarasota / Bradenton -- OBSERVATION ONLY", 27.4200, -82.5500, 9000, False),
    ("obs-anna-maria", "Anna Maria", "Anna Maria Island -- OBSERVATION ONLY", 27.5300, -82.7300, 4500, False),
    ("obs-lakeland", "Lakeland", "Lakeland -- OBSERVATION ONLY", 28.0400, -81.9500, 7000, False),
    ("obs-spring-hill-brooksville", "Spring Hill", "Spring Hill / Brooksville -- OBSERVATION ONLY", 28.4800, -82.5300, 7000, False),
]

BOUNDS = {"min_lat": 27.45, "max_lat": 28.25, "min_lng": -82.85, "max_lng": -81.90}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
#: A row reports under the NEAREST anchor whose radius it falls inside.
COVERAGE_AREAS = [
    ("Downtown Tampa", 27.9475, -82.4584, 2.2),
    ("Channelside", 27.9430, -82.4460, 1.2),
    ("Hyde Park / Davis Islands", 27.9370, -82.4650, 2.0),
    ("Ybor City", 27.9610, -82.4370, 1.5),
    ("Tampa International Airport (TPA)", 27.9755, -82.5332, 2.5),
    ("Westshore", 27.9560, -82.5290, 2.2),
    ("Rocky Point", 27.9720, -82.5480, 1.5),
    ("Raymond James Stadium", 27.9800, -82.5050, 1.5),
    ("Busch Gardens", 28.0378, -82.4197, 1.8),
    ("USF", 28.0600, -82.4140, 2.5),
    ("Temple Terrace", 28.0350, -82.3900, 2.2),
    ("Brandon", 27.9378, -82.2859, 3.0),
    ("Downtown St. Petersburg", 27.7730, -82.6390, 2.0),
    ("Tropicana Field", 27.7683, -82.6534, 1.5),
    ("Clearwater Beach", 27.9775, -82.8288, 1.8),
    ("Clearwater (mainland)", 27.9659, -82.8001, 2.2),
    ("St. Pete Beach", 27.7256, -82.7412, 2.0),
    ("Treasure Island", 27.7676, -82.7659, 1.8),
    ("Madeira Beach", 27.7967, -82.7898, 1.5),
    ("Indian Rocks Beach", 27.8842, -82.8443, 1.8),
    ("Largo", 27.9095, -82.7873, 2.5),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Tampa International Airport (TPA)", re.compile(r"\bairport\b|\bspruce st\b|\bcypress st\b", re.I)),
    ("Rocky Point", re.compile(r"\brocky point\b|\bcourtney campbell\b", re.I)),
    ("Raymond James Stadium", re.compile(r"\braymond james\b|\bn(orth)?\.? dale mabry\b", re.I)),
    ("Westshore", re.compile(r"\bwestshore b(lv)?d\b|\binternational plaza\b|\bboy scout b", re.I)),
    ("Ybor City", re.compile(r"\b7th ave(nue)?\b|\bybor\b|\bla sexta\b", re.I)),
    ("Downtown Tampa", re.compile(r"\briverwalk\b|\bchannelside\b|\bmarion st\b|\bwater st\b|\bashley dr\b", re.I)),
    ("Hyde Park / Davis Islands", re.compile(r"\bbayshore b(lv)?d\b|\bdavis islands?\b|\bhyde park\b", re.I)),
    ("Busch Gardens", re.compile(r"\bbusch b(lv)?d\b|\bmckinley\b|\bbougainvillea\b", re.I)),
    ("USF", re.compile(r"\bfowler ave\b|\busf\b|\b(n(orth)?\.? )?42nd st\b", re.I)),
    ("Downtown St. Petersburg", re.compile(r"\bbeach dr\b|\bcentral ave\b.*\b(1st|2nd|3rd|4th)\b|\b1st ave n\b|\b1st ave s\b", re.I)),
    ("Clearwater Beach", re.compile(r"\bgulfview b(lv)?d\b|\bmandalay ave\b|\bcoronado dr\b", re.I)),
    ("St. Pete Beach", re.compile(r"\bgulf b(lv)?d\b.*\bst\.? pete\b", re.I)),
    ("Treasure Island", re.compile(r"\bgulf b(lv)?d\b.*\btreasure island\b|\b108th ave\b", re.I)),
    ("Madeira Beach", re.compile(r"\bgulf b(lv)?d\b.*\bmadeira\b|\bjohn'?s pass\b", re.I)),
]


def build():
    corridors = []
    seen_zip = {}
    for order, (slug, name, area, klass, _muni, zips, desc) in enumerate(CORRIDORS, start=1):
        for z in zips:
            if z in seen_zip:
                raise SystemExit("postal code %s claimed by both %s and %s -- the corridor registry must be a "
                                 "partition" % (z, seen_zip[z], slug))
            seen_zip[z] = slug
        corridors.append(OrderedDict([
            ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
            ("market_id", MARKET_ID),
            ("name", name),
            ("slug", slug),
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Tampa Bay" % name),
            ("meta_description",
             "Verified pet-friendly hotels in %s, with real pet fees and policies read from each hotel's own "
             "official website." % name),
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
            ("state_code", "FL"),
            ("geography_class", klass),
        ]))
    outside_zips = {z for _m, _s, zs, _w in OUTSIDE for z in zs}
    overlap = outside_zips & set(seen_zip)
    if overlap:
        raise SystemExit("postal codes both admitted and refused: %s" % sorted(overlap))

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius), ("state_code", "FL"),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Tampa – Tampa Bay, Florida multi-core tourism, convention, airport and beach "
                        "lodging market (PetTripFinder discovery scope)"),
        ("state", "FL"),
        ("states", ["FL"]),
        ("country", "US"),
        ("market_center", {"lat": 27.92, "lng": -82.60}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- south "
             "toward Anna Maria Island and the Manatee County line, east toward the Plant City / Lakeland "
             "border, and north toward Wesley Chapel / Pasco County -- so that " + WORK_ORDER + " classifies "
             "those properties on evidence instead of being blind to them. Admission is decided by the "
             "corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Tampa, St. Petersburg and Clearwater/the Gulf beaches are treated as ONE Tampa Bay "
         "market: six CORE Tampa-side corridors, seven CORRIDOR St. Petersburg/Clearwater/Gulf-beach corridors "
         "and six FRINGE corridors. Sarasota/Bradenton, Anna Maria Island, Lakeland and Spring Hill/Brooksville "
         "are OUTSIDE and preserved as future standalone markets; Orlando is its own separate, already-built "
         "market."),
        ("scope_disclosure", "%d bounded cells: %d admitting and %d observation-only." % (
            len(cells), sum(1 for c in cells if c["admitting"]), sum(1 for c in cells if not c["admitting"]))),
        ("explicit_hotel_admissions", OrderedDict([
            ("_what_this_is", "The explicit-hotel mechanism, so a single legitimate fringe property never becomes a "
                              "reason to widen a municipality or a postal code. Empty at authoring time."),
            ("admissions", []),
        ])),
        ("cells", cells),
    ])

    shard = OrderedDict([
        ("schema", "ptf-market/1.1"),
        ("market_id", MARKET_ID),
        ("market_name", "Tampa, Florida"),
        ("market_slug", MARKET_ID),
        ("state_name", "Florida"),
        ("state_code", "FL"),
        ("primary_state_code", "FL"),
        ("states", ["FL"]),
        ("primary_city", "Tampa"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Tampa Bay, Florida | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Tampa Bay -- Downtown Tampa, Ybor City, Westshore / TPA Airport, "
         "Busch Gardens / USF, Brandon, Downtown St. Petersburg, Clearwater Beach and the Gulf beaches -- with "
         "real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Tampa Bay"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its Florida DBPR "
         "public-lodging licence states it, joined to the corridor registry. A multi-core tourism, "
         "convention, airport and beach travel market -- not Tampa's city limits and not all of the Tampa "
         "Bay statistical metro. Nothing else admits a property: not a brand's 'Tampa Bay Area' marketing "
         "name, not a map pin, not a vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Rocky Point, TPA "
         "Airport and Raymond James Stadium share 33607 with the general Westshore footprint; Temple Terrace "
         "shares 33617 with Busch Gardens / USF; St. Pete Beach and Treasure Island share 33706; Gulfport "
         "shares 33707 with mid-Pinellas Seminole / Pinellas Park. Each shared code is one corridor and its "
         "named places are reported as overlays."),
        ("_census_membership_note",
         "Individual condominium units (DBPR CNDO), vacation dwellings (DWEL), vacation homes, whole-home "
         "rental communities, property-management portfolios, Airbnb / Vrbo inventory, ordinary apartments "
         "(DBPR NAPT), individual timeshare units, private resort residences and military-only lodging are "
         "never admitted. A mixed hotel / timeshare / condo campus is admitted only as the exact hotel "
         "premises its operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "3 + 4 + 7 -- Tampa Bay travel-market geography, submarket split test and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/tampa-fl.json; the "
         "registry's markets/<id>.json is never written by this order."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its Florida DBPR public-lodging licence "
         "states it, joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes; future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("submarket_split_test", OrderedDict([
            ("A. Tampa vs. St. Petersburg vs. Clearwater",
             "ONE market (tampa-fl), not three. Single Census MSA, causeway/interstate connectivity (Howard "
             "Frankland, Courtney Campbell, Gandy, Sunshine Skyway) and a shared 'Tampa Bay' travel identity, "
             "even though Visit Tampa Bay and Visit St. Pete-Clearwater run separate CVBs. St. Petersburg and "
             "Clearwater/the Gulf beaches are kept as named CORRIDOR tiers, never folded anonymously into "
             "generic Tampa corridors, so the CVB / county distinction is preserved without a market split. "
             "FUTURE_STANDALONE st-petersburg-fl and pinellas-beaches-fl are named and preserved."),
            ("B. Downtown Tampa",
             "CORE corridor downtown-riverwalk (33602, 33603, 33606): Riverwalk, Channelside, Hyde Park / "
             "Davis Islands. Distinct convention, arena and business demand; too small and too Tampa-bound to "
             "stand as its own market."),
            ("C. Westshore / TPA Airport / Rocky Point / Raymond James Stadium",
             "CORE corridor westshore-airport-rocky-point (33607, 33609, 33614, 33615), Tampa's largest hotel "
             "cluster. Rocky Point and the stadium cannot be separate pages under a postal partition without "
             "splitting 33607 from the airport hotels that depend on it; each is an overlay."),
            ("D. Ybor City",
             "CORE corridor ybor-city (33605). A distinct historic entertainment district with its own hotel "
             "demand, separated from downtown by the postal partition."),
            ("E. Busch Gardens / USF / Temple Terrace",
             "CORE corridor busch-gardens-usf (33612, 33613, 33617, 33637). Temple Terrace's own incorporated "
             "limits share 33617 with north Tampa / USF and cannot be split out; reported as an overlay."),
            ("F. Brandon",
             "CORE corridor brandon (33510, 33511, 33584): the US-301 / SR-60 / I-75 interstate hotel cluster "
             "east of Tampa."),
            ("G. East Tampa / I-75",
             "CORE corridor east-tampa-i75 (33610, 33619): Adamo Drive / US-301 and the Causeway Boulevard "
             "I-75/I-4 interchange."),
            ("H. Downtown St. Petersburg",
             "CORRIDOR corridor st-petersburg-downtown (33701, 33705): Beach Drive, the EDGE District and "
             "Tropicana Field, the state's own distinct downtown hotel cluster."),
            ("I. St. Petersburg (broader)",
             "CORRIDOR corridor st-petersburg (33702, 33703, 33704, 33710, 33712, 33713, 33714, 33716): the "
             "Skyway Marina District, Tyrone and the Gandy corridor."),
            ("J. Clearwater / Clearwater Beach",
             "CORRIDOR clearwater-downtown (33755, 33756) for the mainland, and CORRIDOR clearwater-beach "
             "(33767) for the barrier-island resort strip -- kept separate because the Memorial Causeway "
             "genuinely separates two distinct lodging products (business/medical mainland vs. beach resort)."),
            ("K. St. Pete Beach / Treasure Island",
             "CORRIDOR st-pete-beach-treasure-island (33706): the two towns share one ZIP and one continuous "
             "Gulf Boulevard resort strip; cannot be split by the postal partition."),
            ("L. Madeira Beach / Redington / Indian Rocks Beach",
             "CORRIDOR madeira-redington-indian-rocks (33708, 33785, 33786): the beach towns between John's "
             "Pass and Belleair Beach."),
            ("M. Largo",
             "CORRIDOR largo (33770, 33771, 33773, 33774, 33777, 33778, 33779): mid-Pinellas County's largest "
             "inland city."),
            ("N. Careful-evaluation fringe (Wesley Chapel/New Tampa, South Hillsborough, Plant City, Tarpon "
             "Springs/Dunedin, mid-Pinellas, Safety Harbor/Oldsmar/Palm Harbor)",
             "Six FRINGE corridors, admitted at lower expected density per the mission's explicit 'careful "
             "evaluation' list; a corridor page still requires the same minimum_hotel_count = 5 threshold."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Tampa", "ADMITTED (CORE, six corridors)."),
            ("St. Petersburg", "ADMITTED (CORRIDOR, st-petersburg-downtown / st-petersburg)."),
            ("Clearwater", "ADMITTED (CORRIDOR, clearwater-downtown)."),
            ("Clearwater Beach", "ADMITTED (CORRIDOR, clearwater-beach)."),
            ("St. Pete Beach", "ADMITTED (CORRIDOR, st-pete-beach-treasure-island, 33706)."),
            ("Treasure Island", "ADMITTED (CORRIDOR, st-pete-beach-treasure-island, 33706, shares the ZIP with St. Pete Beach)."),
            ("Madeira Beach", "ADMITTED (CORRIDOR, madeira-redington-indian-rocks)."),
            ("Indian Rocks Beach", "ADMITTED (CORRIDOR, madeira-redington-indian-rocks, 33785)."),
            ("Largo", "ADMITTED (CORRIDOR, largo)."),
            ("Wesley Chapel", "ADMITTED (FRINGE, wesley-chapel-new-tampa) -- careful evaluation."),
            ("New Tampa", "ADMITTED (FRINGE, wesley-chapel-new-tampa, 33647) -- careful evaluation."),
            ("Riverview", "ADMITTED (FRINGE, south-hillsborough) -- careful evaluation."),
            ("Apollo Beach", "ADMITTED (FRINGE, south-hillsborough, 33572) -- careful evaluation."),
            ("Ruskin", "ADMITTED (FRINGE, south-hillsborough, 33570) -- careful evaluation."),
            ("Plant City", "ADMITTED (FRINGE, plant-city) -- careful evaluation."),
            ("Tarpon Springs", "ADMITTED (FRINGE, tarpon-dunedin) -- careful evaluation."),
            ("Dunedin", "ADMITTED (FRINGE, tarpon-dunedin, 34698) -- careful evaluation."),
            ("Seminole", "ADMITTED (FRINGE, mid-pinellas) -- careful evaluation."),
            ("Pinellas Park", "ADMITTED (FRINGE, mid-pinellas, 33781/33782) -- careful evaluation."),
            ("Gulfport", "ADMITTED (FRINGE, mid-pinellas, 33707, shares the ZIP with Seminole/Pinellas Park, not "
                         "with the St. Petersburg corridor) -- careful evaluation."),
            ("Safety Harbor", "ADMITTED (FRINGE, safety-harbor-oldsmar-palm-harbor) -- careful evaluation."),
            ("Oldsmar", "ADMITTED (FRINGE, safety-harbor-oldsmar-palm-harbor, 34677) -- careful evaluation."),
            ("Palm Harbor", "ADMITTED (FRINGE, safety-harbor-oldsmar-palm-harbor, 34683) -- careful evaluation."),
            ("Lithia / Fishhawk", "OUTSIDE -- careful evaluation: rural, weak hotel intent."),
            ("Sarasota", "OUTSIDE by name (order) -- future sarasota-bradenton-fl."),
            ("Bradenton", "OUTSIDE by name (order) -- future sarasota-bradenton-fl."),
            ("Anna Maria Island", "OUTSIDE by name (order) -- future sarasota-bradenton-fl; do not automatically absorb."),
            ("Lakeland", "OUTSIDE by name (order) -- future lakeland-winter-haven-fl; do not automatically absorb."),
            ("Spring Hill / Brooksville", "OUTSIDE by name (order) -- future spring-hill-brooksville-fl; do not automatically absorb."),
            ("Orlando", "OUTSIDE by name (order) -- its own separate, already-built market."),
        ])),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 "
         "verified pet-friendly hotels) is met. No thin corridor page is invented for SEO; every corridor is "
         "show_in_navigation / show_in_sitemap false until a registration order publishes it. Rocky Point, TPA "
         "Airport, Raymond James Stadium, Temple Terrace and Gulfport cannot be separate pages under a "
         "postal-code partition; they are reported as overlays."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, public resorts, qualifying resort towers, qualifying "
         "extended-stay hotels and other public lodging establishments: bookable nightly rooms or suites sold "
         "to the public under one establishment name, with an official property page and an on-site hotel "
         "operation. It NEVER admits: individual condominium units (DBPR rank CNDO) or vacation dwellings "
         "(DBPR rank DWEL); individual vacation homes or villas; whole-home rental communities and "
         "property-management portfolios; Airbnb / Vrbo listings; ordinary apartments (DBPR NAPT); individual "
         "timeshare units, vacation-ownership inventory sold to owners, and private resort residences; and "
         "privately managed units inside resort campuses. A mixed hotel / timeshare / condo campus is admitted "
         "ONLY as the exact hotel premises its operator sells to the public as a hotel, proved on the "
         "operator's own page and the licence's exact premises. Campgrounds, RV parks and dormitory hostels "
         "are NON_LODGING."),
        ("theme_park_campus_rule",
         "Never merged solely by brand, resort family, phone, campus, shared entrance, shared amenities, "
         "shared booking engine or display name. Exact premises identity (its own street address or its own "
         "brand property code on its own page) governs."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


def corridor_municipality():
    return {slug: muni for slug, _n, _a, _k, muni, _z, _d in CORRIDORS}


def corridor_class(slug):
    return {s: k for s, _n, _a, k, _m, _z, _d in CORRIDORS}.get(slug)


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
    """The order's named submarket a census row reports under: its own street first, then its pin, then the
    corridor's own name. Reporting only."""
    for name, rx in STREET_OVERLAYS:
        if rx.search(street or ""):
            return name
    area = coverage_area(lat, lng)
    if area:
        return area
    return {
        "downtown-riverwalk": "Downtown Tampa", "ybor-city": "Ybor City",
        "westshore-airport-rocky-point": "Westshore", "busch-gardens-usf": "Busch Gardens",
        "brandon": "Brandon", "east-tampa-i75": "East Tampa",
        "st-petersburg-downtown": "Downtown St. Petersburg", "st-petersburg": "St. Petersburg",
        "clearwater-downtown": "Clearwater", "clearwater-beach": "Clearwater Beach",
        "st-pete-beach-treasure-island": "St. Pete Beach", "madeira-redington-indian-rocks": "Madeira Beach",
        "largo": "Largo", "wesley-chapel-new-tampa": "Wesley Chapel", "south-hillsborough": "Riverview",
        "plant-city": "Plant City", "tarpon-dunedin": "Tarpon Springs", "mid-pinellas": "Seminole",
        "safety-harbor-oldsmar-palm-harbor": "Safety Harbor",
    }.get(corridor_slug)


def normalise_municipality(city):
    muni = " ".join((city or "").lower().replace(".", " ").split())
    return MUNICIPALITY_SPELLINGS.get(muni, muni)


def future_market_for(postal):
    """The FUTURE_STANDALONE market id a refused postal code is preserved for, or ""."""
    z = (postal or "").strip()[:5]
    for _name, _s, zs, why in OUTSIDE:
        if z in zs:
            for fid in FUTURE_MARKETS:
                if fid in why:
                    return fid
    return ""


def classify_postal(postal, municipality=""):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and municipality. The one
    membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = normalise_municipality(municipality)
    for slug, _name, _area, klass, _m, zips, _desc in CORRIDORS:
        if z in zips:
            for rz, rmuni, why in MUNICIPALITY_REFUSALS:
                if rz == z and rmuni.lower() == muni:
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
                          (REGISTRY_OUT, OrderedDict([("schema", "ptf-corridor-registry/1.0"), ("work_order", WORK_ORDER),
                                                      ("market_id", MARKET_ID), ("corridors", corridors)]))):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, indent=1)
                fh.write("\n")
            print("WROTE", os.path.relpath(path, _DASH))
    print("corridors=%d  admitted_zips=%d  cells=%d (admitting %d, observation %d)" % (
        report["corridor_count"], report["admitted_postal_code_count"], report["cells_total"],
        report["cells_admitting"], report["cells_observation_only"]))
    print("by class:", json.dumps(report["corridor_count_by_class"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
