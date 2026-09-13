"""PTF-ATLANTA-GA-PARALLEL-SOURCE-READY-001 -- Phase 2 + 3: the Atlanta travel market and its corridors.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Atlanta, Georgia traveler lodging market -- a MULTI-CORE market,
not a city and not a statistical area -- stated as an explicit four-way rule
(CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is admitted, so no
property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. A brand's
marketing name ("Atlanta Airport", "Atlanta Perimeter", "Atlanta North") never
admits and never places a property.

A TRAVEL MARKET, NOT CITY LIMITS, AND NOT THE MSA
------------------------------------------------
Atlanta's hotel demand sits in separate lodging cores: the Downtown convention
district (GWCC, State Farm Arena, Mercedes-Benz Stadium, Centennial Olympic
Park), Midtown and Georgia Tech, Buckhead / Lenox, Hartsfield-Jackson (the
world's busiest airport, whose hotels sit in College Park, Hapeville and East
Point), Perimeter Center (Sandy Springs / Dunwoody), Cumberland / Galleria /
Truist Park (Vinings, Smyrna) and Decatur / Emory (Emory University Hospital and
the CDC). Around them the interstate business corridors -- I-75 north
(Marietta, Kennesaw), GA-400 north (Roswell, Alpharetta), I-85 north
(Chamblee, Doraville, Norcross, Peachtree Corners, Duluth, Johns Creek,
Suwanee), US-78 / I-285 east (Tucker, Northlake, Stone Mountain) and I-75 / I-85
south of the airport (Riverdale, Forest Park) -- are where an Atlanta traveller
sleeps by choice. The FRINGE is the ring of I-20 / I-75 interchange towns whose
lodging still sells to Atlanta interstate traffic (Morrow, Stockbridge, Lithonia /
Stonecrest, Douglasville): admitted, each its own corridor, never reported as
core.

THE FOUR CLASSES
----------------
CORE       Downtown; Midtown / West Midtown / Georgia Tech; Buckhead / Lenox /
           Brookhaven; ATL Airport (College Park, Hapeville, East Point, Camp
           Creek); Perimeter / Sandy Springs / Dunwoody; Cumberland / Galleria /
           Vinings; Smyrna; Decatur / Emory; Southside Atlanta (inside the city).
CORRIDOR   Airport South (College Park south, Riverdale, Forest Park); Chamblee /
           Doraville; Marietta; Alpharetta / Roswell (North Fulton); Norcross /
           Peachtree Corners; Duluth / Johns Creek; Tucker / Northlake / Stone
           Mountain; Kennesaw; Suwanee.
FRINGE     Morrow; Stockbridge; Lithonia / Stonecrest; Douglasville.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision --
           Acworth, Lawrenceville, Buford / Mall of Georgia, Snellville, Union
           City, Fairburn, Austell / Six Flags, Lithia Springs, Mableton,
           Jonesboro, Conley / Ellenwood, McDonough, Conyers, Covington,
           Cumming, Woodstock, Canton, Cartersville, Newnan, Peachtree City,
           Fayetteville, Gainesville, Athens and beyond.

THE "EVALUATE CAREFULLY" SET
----------------------------
Kennesaw     ADMITTED CORRIDOR -- contiguous with Marietta on I-75 (Town Center,
             Kennesaw State); its own brands sell it as an Atlanta-north stop.
Johns Creek  ADMITTED CORRIDOR -- its hotels share Duluth's 30097 and
             Alpharetta's 30022; the Medlock Bridge / State Bridge business strip.
Suwanee      ADMITTED CORRIDOR -- I-85 exit 111, contiguous with Duluth.
Morrow       ADMITTED FRINGE -- I-75 south (Southlake, Clayton State), ten miles
             past the airport.
Forest Park  ADMITTED CORRIDOR (Airport South) -- the I-75 / I-285 interchange
             five miles from the airport.
Stockbridge  ADMITTED FRINGE -- the I-75 / I-675 interchange; interstate lodging
             that sells to Atlanta traffic. McDonough beyond it is OUTSIDE.
Lithonia     ADMITTED FRINGE -- I-20 east at Stonecrest.
Douglasville ADMITTED FRINGE -- I-20 west at Arbor Place.
Acworth      OUTSIDE -- Lake Allatoona and the I-75 run toward Cartersville; its
             lodging serves the lake and the Cartersville corridor.
Lawrenceville OUTSIDE -- the Gwinnett county seat on GA-316 toward Athens; a
             plausible future east-Gwinnett market, not an Atlanta traveller's stay.

A future standalone market stays possible wherever traveller intent is
materially distinct: every OUTSIDE town is named with its postal codes and
nothing here claims it.

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the admitted ZIPs -- out to Acworth,
Lawrenceville, Buford, Conyers, McDonough and Fairburn -- so this order
classifies those properties on evidence rather than being blind to them.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
Atlanta is built while production deployment is blocked and three markets
(Fayetteville, Jacksonville, Greenville) must go live first. The market document
goes to the zone's PROPOSED path, never to the registry's markets/<id>.json.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/atlanta_ga.json
  launch_packages/pettripfinder/markets/proposed/atlanta-ga.json
  launch_packages/pettripfinder/markets/reports/atlanta_ga_geography_001.json
  launch_packages/pettripfinder/markets/reports/atlanta_ga_corridor_registry_001.json
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

WORK_ORDER = "PTF-ATLANTA-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "atlanta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "atlanta_ga.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "atlanta-ga.json")
REPORT_OUT = os.path.join(REPORTS, "atlanta_ga_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "atlanta_ga_corridor_registry_001.json")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown", "Downtown / Centennial Olympic Park / GWCC", "Downtown", "CORE", "atlanta",
     ["30303", "30313", "30312", "30314", "30334", "30335"],
     "Downtown Atlanta: Peachtree Center, the Georgia World Congress Center, State Farm Arena, "
     "Mercedes-Benz Stadium, Centennial Olympic Park, Castleberry Hill and the Old Fourth Ward south."),
    ("midtown", "Midtown / West Midtown / Georgia Tech", "Midtown", "CORE", "atlanta",
     ["30308", "30309", "30363", "30318", "30306", "30307", "30332", "30361"],
     "Midtown Atlanta and Atlantic Station, Georgia Tech, West Midtown / Westside, Ponce City "
     "Market and the intown east neighbourhoods (Virginia-Highland, Poncey-Highland, Inman Park)."),
    ("buckhead", "Buckhead / Lenox / Lindbergh / Brookhaven", "Buckhead", "CORE", "atlanta",
     ["30305", "30326", "30327", "30324", "30319"],
     "Buckhead Village, Lenox Square and Phipps Plaza, Peachtree Road, Lindbergh / Piedmont Road "
     "and Brookhaven."),
    ("atl-airport", "Hartsfield-Jackson ATL Airport / College Park / Hapeville / East Point",
     "ATL Airport", "CORE", "college park",
     ["30337", "30354", "30320", "30344", "30331"],
     "Hartsfield-Jackson Atlanta International Airport and its hotel district: College Park and "
     "the Georgia International Convention Center, Hapeville, East Point, Virginia Avenue and "
     "Camp Creek Parkway."),
    ("perimeter", "Perimeter Center / Sandy Springs / Dunwoody", "Perimeter", "CORE", "sandy springs",
     ["30328", "30338", "30346", "30350", "30342"],
     "Perimeter Center (Perimeter Mall, the Central Perimeter office market), Sandy Springs, "
     "Dunwoody and the medical centre at I-285 / GA-400."),
    ("cumberland-galleria", "Cumberland / Galleria / Vinings / Truist Park", "Cumberland / Galleria",
     "CORE", "atlanta",
     ["30339"],
     "Cumberland Mall, the Cobb Galleria Centre, Truist Park / The Battery Atlanta and Vinings."),
    ("smyrna", "Smyrna", "Smyrna", "CORE", "smyrna",
     ["30080", "30082"],
     "Smyrna on I-285 / South Cobb Drive and the Cumberland edge."),
    ("decatur-emory", "Decatur / Emory / Druid Hills / Executive Park", "Decatur / Emory", "CORE", "decatur",
     ["30030", "30031", "30032", "30033", "30034", "30035", "30002", "30079", "30322", "30329",
      "30316", "30317"],
     "Downtown Decatur, Emory University and Emory University Hospital, the CDC, Druid Hills, North "
     "Druid Hills / Executive Park, Avondale Estates and the east-side city neighbourhoods."),
    ("southside-atlanta", "West End / Southside Atlanta / Fulton Industrial", "Southside Atlanta",
     "CORE", "atlanta",
     ["30310", "30311", "30315", "30336"],
     "The City of Atlanta south and west of downtown: West End, Cascade, Lakewood, the I-75 / I-85 "
     "south connector and Fulton Industrial Boulevard."),
    ("airport-south", "Airport South / Riverdale / Forest Park", "Airport South", "CORRIDOR", "college park",
     ["30349", "30296", "30274", "30297"],
     "South of the airport: College Park south on Old National Highway, Riverdale and Forest "
     "Park at the I-75 / I-285 interchange."),
    ("chamblee-doraville", "Chamblee / Doraville / Peachtree Industrial", "Chamblee / Doraville",
     "CORRIDOR", "chamblee",
     ["30341", "30340", "30360", "30366"],
     "Chamblee, Doraville and Peachtree Industrial Boulevard inside and at I-285, on I-85 north."),
    ("marietta", "Marietta / Windy Hill / Delk Road", "Marietta", "CORRIDOR", "marietta",
     ["30060", "30062", "30064", "30066", "30067", "30068", "30008", "30061", "30065", "30069"],
     "Marietta and the I-75 business strip at Delk Road, Windy Hill and Powers Ferry."),
    ("north-fulton", "Alpharetta / Roswell / North Fulton", "Alpharetta / Roswell", "CORRIDOR", "alpharetta",
     ["30004", "30005", "30009", "30022", "30023", "30075", "30076", "30077"],
     "GA-400 north: Roswell, Alpharetta, North Point, Windward Parkway, Avalon and Milton."),
    ("norcross-peachtree-corners", "Norcross / Peachtree Corners", "Norcross / Peachtree Corners",
     "CORRIDOR", "norcross",
     ["30071", "30092", "30093", "30091", "30010", "30003"],
     "I-85 north at Jimmy Carter Boulevard: Norcross, Peachtree Corners and Technology Park."),
    ("duluth-johns-creek", "Duluth / Johns Creek / Gwinnett Place", "Duluth / Johns Creek", "CORRIDOR",
     "duluth",
     ["30096", "30097", "30095", "30098", "30099"],
     "Duluth, Gwinnett Place, Gas South District and Johns Creek's Medlock Bridge / State Bridge corridor."),
    ("tucker-stone-mountain", "Tucker / Northlake / Stone Mountain", "Tucker / Stone Mountain", "CORRIDOR",
     "tucker",
     ["30084", "30085", "30345", "30083", "30087", "30088", "30086"],
     "Tucker and Northlake at I-285, and Stone Mountain on US-78 (Stone Mountain Park)."),
    ("kennesaw", "Kennesaw / Town Center / Kennesaw State", "Kennesaw", "CORRIDOR", "kennesaw",
     ["30144", "30152", "30156", "30160"],
     "Kennesaw on I-75 north at Town Center and Kennesaw State University, contiguous with Marietta."),
    ("suwanee", "Suwanee / I-85 North", "Suwanee", "CORRIDOR", "suwanee",
     ["30024"],
     "Suwanee at I-85 exit 111, contiguous with Duluth."),
    ("morrow", "Morrow / Southlake", "Morrow", "FRINGE", "morrow",
     ["30260"],
     "Morrow on I-75 south at Southlake and Clayton State University."),
    ("stockbridge", "Stockbridge / I-75 South", "Stockbridge", "FRINGE", "stockbridge",
     ["30281"],
     "Stockbridge at the I-75 / I-675 interchange."),
    ("lithonia-stonecrest", "Lithonia / Stonecrest", "Lithonia / Stonecrest", "FRINGE", "lithonia",
     ["30038", "30058"],
     "Lithonia and Stonecrest on I-20 east."),
    ("douglasville", "Douglasville / I-20 West", "Douglasville", "FRINGE", "douglasville",
     ["30134", "30135"],
     "Douglasville on I-20 west at Arbor Place."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. Empty at authoring time; a later
#: ruling adds a row, never a ZIP.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {}

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Acworth", "GA", ["30101", "30102"],
     "Lake Allatoona and the I-75 run toward Cartersville; its lodging serves the lake and that corridor; evaluated and refused."),
    ("Lawrenceville", "GA", ["30043", "30044", "30045", "30046", "30042"],
     "Gwinnett county seat on GA-316 toward Athens; a plausible future east-Gwinnett market; evaluated and refused."),
    ("Buford / Mall of Georgia / Sugar Hill", "GA", ["30518", "30519"],
     "I-85 / I-985 toward Lake Lanier and Gainesville; evaluated and refused."),
    ("Snellville / Grayson / Loganville / Lilburn / Dacula", "GA", ["30039", "30078", "30017", "30052", "30047", "30048", "30019"],
     "US-78 / GA-124 east Gwinnett suburbs; evaluated and refused."),
    ("Union City / Fairburn / Palmetto", "GA", ["30291", "30213", "30268"],
     "I-85 south Fulton toward Newnan; evaluated and refused."),
    ("Austell / Six Flags / Lithia Springs / Mableton / Powder Springs", "GA", ["30168", "30106", "30122", "30126", "30127"],
     "South Cobb / I-20 west leisure and suburban lodging; evaluated and refused."),
    ("Jonesboro / Rex / Hampton", "GA", ["30236", "30238", "30273", "30228"],
     "Clayton / Henry County south of Morrow; evaluated and refused."),
    ("Conley / Ellenwood", "GA", ["30288", "30294"],
     "I-675 / I-285 south-east industrial fringe; evaluated and refused."),
    ("McDonough / Locust Grove", "GA", ["30252", "30253", "30248"],
     "I-75 south beyond Stockbridge; its own interstate cluster; refused by name (order: do not absorb McDonough)."),
    ("Conyers / Covington", "GA", ["30012", "30013", "30094", "30014", "30016"],
     "I-20 east beyond Stonecrest; refused by name (order: do not absorb Covington)."),
    ("Cumming / Woodstock / Canton", "GA", ["30040", "30041", "30028", "30188", "30189", "30114", "30115"],
     "Forsyth and Cherokee County exurbs; evaluated and refused."),
    ("Cartersville", "GA", ["30120", "30121"],
     "Bartow County on I-75, its own market; refused by name (order)."),
    ("Newnan", "GA", ["30263", "30265"],
     "Coweta County on I-85, its own market; refused by name (order)."),
    ("Peachtree City / Fayetteville / Tyrone", "GA", ["30269", "30214", "30215", "30290"],
     "Fayette County; refused by name (order)."),
    ("Gainesville", "GA", ["30501", "30504", "30506", "30507"],
     "Hall County on Lake Lanier, its own market; refused by name (order)."),
    ("Athens", "GA", ["30601", "30605", "30606", "30607"],
     "The University of Georgia, its own market; refused by name (order)."),
    ("Hiram / Dallas / Villa Rica / Braselton", "GA", ["30141", "30157", "30180", "30517"],
     "Far exurban Georgia; refused by name."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover refused neighbours so this order classifies them on evidence.
CELLS = [
    ("downtown", "Atlanta", "Downtown / GWCC / Centennial Olympic Park", 33.759, -84.392, 2500, True),
    ("midtown", "Atlanta", "Midtown / Georgia Tech / Atlantic Station", 33.783, -84.387, 3000, True),
    ("west-midtown", "Atlanta", "West Midtown / Westside", 33.785, -84.415, 3000, True),
    ("buckhead", "Atlanta", "Buckhead / Lenox / Lindbergh", 33.845, -84.370, 4000, True),
    ("brookhaven", "Brookhaven", "Brookhaven", 33.870, -84.335, 3000, True),
    ("atl-airport", "College Park", "ATL Airport / College Park / Hapeville", 33.650, -84.440, 5000, True),
    ("east-point-camp-creek", "East Point", "East Point / Camp Creek", 33.665, -84.500, 4000, True),
    ("perimeter", "Sandy Springs", "Perimeter / Sandy Springs / Dunwoody", 33.925, -84.350, 5000, True),
    ("cumberland", "Atlanta", "Cumberland / Galleria / Vinings", 33.880, -84.465, 4000, True),
    ("smyrna", "Smyrna", "Smyrna", 33.870, -84.515, 4000, True),
    ("decatur-emory", "Decatur", "Decatur / Emory / Executive Park", 33.790, -84.300, 5000, True),
    ("southside", "Atlanta", "West End / Southside / Fulton Industrial", 33.720, -84.430, 6000, True),
    ("airport-south", "Riverdale", "Airport South / Riverdale / Forest Park", 33.600, -84.400, 6000, True),
    ("chamblee-doraville", "Chamblee", "Chamblee / Doraville", 33.890, -84.290, 4000, True),
    ("marietta", "Marietta", "Marietta / Delk Road / Windy Hill", 33.940, -84.520, 7000, True),
    ("north-fulton", "Alpharetta", "Alpharetta / Roswell", 34.040, -84.320, 9000, True),
    ("norcross", "Norcross", "Norcross / Peachtree Corners", 33.930, -84.210, 5000, True),
    ("duluth", "Duluth", "Duluth / Johns Creek", 34.000, -84.150, 6000, True),
    ("tucker-stone-mountain", "Tucker", "Tucker / Northlake / Stone Mountain", 33.830, -84.200, 7000, True),
    ("kennesaw", "Kennesaw", "Kennesaw / Town Center", 34.020, -84.610, 5000, True),
    ("suwanee", "Suwanee", "Suwanee", 34.050, -84.070, 4000, True),
    ("morrow", "Morrow", "Morrow / Southlake", 33.580, -84.340, 4000, True),
    ("stockbridge", "Stockbridge", "Stockbridge", 33.530, -84.240, 5000, True),
    ("lithonia", "Lithonia", "Lithonia / Stonecrest", 33.700, -84.110, 6000, True),
    ("douglasville", "Douglasville", "Douglasville", 33.730, -84.740, 6000, True),
    ("obs-acworth", "Acworth", "Acworth -- OBSERVATION ONLY", 34.060, -84.680, 5000, False),
    ("obs-lawrenceville", "Lawrenceville", "Lawrenceville -- OBSERVATION ONLY", 33.960, -83.990, 6000, False),
    ("obs-buford", "Buford", "Buford / Mall of Georgia -- OBSERVATION ONLY", 34.080, -83.990, 5000, False),
    ("obs-union-city", "Union City", "Union City / Fairburn -- OBSERVATION ONLY", 33.580, -84.560, 6000, False),
    ("obs-mcdonough", "McDonough", "McDonough -- OBSERVATION ONLY", 33.450, -84.160, 5000, False),
    ("obs-conyers", "Conyers", "Conyers -- OBSERVATION ONLY", 33.670, -84.010, 5000, False),
]

BOUNDS = {
    "min_lat": 33.40,
    "max_lat": 34.17,
    "min_lng": -84.85,
    "max_lng": -83.94,
}

#: Reporting overlay only (never membership): the areas the order names, each an
#: anchor point and a radius. A property is reported in the NEAREST anchor whose
#: radius it falls inside, else "elsewhere".
COVERAGE_AREAS = [
    ("Downtown Atlanta", 33.7590, -84.3900, 1.8),
    ("Midtown Atlanta", 33.7810, -84.3850, 2.0),
    ("Buckhead", 33.8450, -84.3680, 3.0),
    ("Hartsfield-Jackson ATL Airport", 33.6400, -84.4280, 3.5),
    ("College Park", 33.6530, -84.4490, 2.5),
    ("Hapeville", 33.6600, -84.4100, 1.8),
    ("East Point", 33.6800, -84.4700, 2.5),
    ("Sandy Springs", 33.9300, -84.3730, 3.0),
    ("Dunwoody / Perimeter Center", 33.9260, -84.3400, 2.5),
    ("Cumberland / Galleria", 33.8800, -84.4650, 2.5),
    ("Vinings", 33.8650, -84.4700, 1.5),
    ("Smyrna", 33.8840, -84.5140, 3.0),
    ("Decatur / Emory", 33.7850, -84.3050, 3.5),
    ("Marietta", 33.9530, -84.5280, 5.0),
    ("Roswell", 34.0230, -84.3620, 4.0),
    ("Alpharetta", 34.0750, -84.2940, 5.0),
    ("Norcross", 33.9300, -84.2130, 3.0),
    ("Peachtree Corners", 33.9700, -84.2200, 3.0),
    ("Duluth", 33.9900, -84.1450, 4.0),
    ("Tucker", 33.8550, -84.2170, 3.0),
    ("Stone Mountain", 33.8080, -84.1700, 4.0),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Atlanta" % name),
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
        ("state_code", "GA"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Atlanta, GA multi-core traveler lodging market (PetTripFinder discovery scope)"),
        ("state", "GA"),
        ("states", ["GA"]),
        ("country", "US"),
        ("market_center", {"lat": 33.755, "lng": -84.390}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- "
             "to Acworth, Lawrenceville, Buford, Conyers, McDonough and Fairburn -- so that " +
             WORK_ORDER + " classifies those properties on evidence instead of being blind to them. "
             "Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A multi-core travel market: nine CORE corridors (Downtown, Midtown, Buckhead, "
         "ATL Airport, Perimeter, Cumberland / Galleria, Smyrna, Decatur / Emory, Southside Atlanta), "
         "nine interstate CORRIDORS and four FRINGE interchange towns. Acworth, Lawrenceville, Buford, "
         "Union City, McDonough, Conyers and the far exurbs are OBSERVED or named, and REFUSED."),
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
        ("market_name", "Atlanta, Georgia"),
        ("market_slug", MARKET_ID),
        ("state_name", "Georgia"),
        ("state_code", "GA"),
        ("primary_state_code", "GA"),
        ("states", ["GA"]),
        ("primary_city", "Atlanta"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Atlanta, Georgia | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across metro Atlanta -- Downtown, Midtown, Buckhead, the "
         "Hartsfield-Jackson airport district, Perimeter Center, Cumberland / Galleria, Decatur / "
         "Emory, Marietta, Alpharetta and more -- with real pet fees and policies read from each "
         "hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Atlanta"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A multi-core travel market -- not Atlanta's city limits and not the "
         "statistical MSA. Nothing else admits a property: not a brand's 'Atlanta Airport' or 'Atlanta "
         "North' marketing name, not a map pin, not a vacation-rental listing, not a competitor "
         "directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor."),
        ("_census_membership_note",
         "Acworth, Lawrenceville, Buford, Snellville, Union City, Fairburn, Austell, Mableton, "
         "Jonesboro, McDonough, Conyers, Covington, Cumming, Woodstock, Cartersville, Newnan, "
         "Peachtree City, Gainesville and Athens are not absorbed. A property whose own page states one "
         "of their postal codes is OUTSIDE, however it is named."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 -- Atlanta multi-core travel-market geography and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-13"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Fayetteville, Jacksonville and "
         "Greenville to go live."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "Atlanta's lodging cores (Downtown convention district, Midtown / Georgia Tech, Buckhead, the "
         "Hartsfield-Jackson airport district, Perimeter Center, Cumberland / Galleria, Decatur / "
         "Emory) plus the interstate business corridors a traveller to Atlanta sleeps in by choice, and "
         "four I-20 / I-75 interchange towns as FRINGE."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("evaluated_inclusions", OrderedDict([
            ("Downtown Atlanta", "ADMITTED (CORE, downtown)."),
            ("Midtown Atlanta", "ADMITTED (CORE, midtown)."),
            ("Buckhead", "ADMITTED (CORE, buckhead)."),
            ("Hartsfield-Jackson ATL Airport", "ADMITTED (CORE, atl-airport) -- 30320 plus the hotel ZIPs 30337 / 30354 / 30344."),
            ("College Park", "ADMITTED -- 30337 CORE (atl-airport); 30349 south of the airport is CORRIDOR (airport-south)."),
            ("Hapeville", "ADMITTED (CORE, atl-airport, 30354)."),
            ("East Point", "ADMITTED (CORE, atl-airport, 30344; Camp Creek 30331)."),
            ("Sandy Springs", "ADMITTED (CORE, perimeter)."),
            ("Dunwoody / Perimeter Center", "ADMITTED (CORE, perimeter)."),
            ("Cumberland / Galleria", "ADMITTED (CORE, cumberland-galleria, 30339)."),
            ("Vinings", "ADMITTED (CORE, cumberland-galleria, 30339)."),
            ("Smyrna", "ADMITTED (CORE, smyrna)."),
            ("Decatur / Emory", "ADMITTED (CORE, decatur-emory)."),
            ("Marietta", "ADMITTED (CORRIDOR, marietta)."),
            ("Roswell", "ADMITTED (CORRIDOR, north-fulton)."),
            ("Alpharetta", "ADMITTED (CORRIDOR, north-fulton)."),
            ("Norcross", "ADMITTED (CORRIDOR, norcross-peachtree-corners)."),
            ("Peachtree Corners", "ADMITTED (CORRIDOR, norcross-peachtree-corners)."),
            ("Duluth", "ADMITTED (CORRIDOR, duluth-johns-creek)."),
            ("Tucker", "ADMITTED (CORRIDOR, tucker-stone-mountain)."),
            ("Stone Mountain", "ADMITTED (CORRIDOR, tucker-stone-mountain)."),
            ("Chamblee / Doraville / Brookhaven", "ADMITTED -- inside I-285 on I-85 north (Chamblee / Doraville CORRIDOR; Brookhaven CORE with Buckhead)."),
            ("Kennesaw", "ADMITTED (CORRIDOR, kennesaw) -- contiguous with Marietta on I-75."),
            ("Johns Creek", "ADMITTED (CORRIDOR) -- its hotels carry Duluth's 30097 or Alpharetta's 30022."),
            ("Suwanee", "ADMITTED (CORRIDOR, suwanee) -- I-85 exit 111, contiguous with Duluth."),
            ("Forest Park", "ADMITTED (CORRIDOR, airport-south) -- I-75 / I-285, five miles from ATL."),
            ("Morrow", "ADMITTED (FRINGE, morrow)."),
            ("Stockbridge", "ADMITTED (FRINGE, stockbridge) -- interstate lodging at I-75 / I-675."),
            ("Lithonia / Stonecrest", "ADMITTED (FRINGE, lithonia-stonecrest)."),
            ("Douglasville", "ADMITTED (FRINGE, douglasville)."),
            ("Acworth", "OUTSIDE -- Lake Allatoona / the Cartersville run of I-75."),
            ("Lawrenceville", "OUTSIDE -- Gwinnett county seat on GA-316 toward Athens."),
            ("McDonough", "OUTSIDE -- beyond Stockbridge (order: not absorbed beyond clearly Atlanta-oriented behavior)."),
            ("Athens / Gainesville / Newnan / Peachtree City / Cartersville / Covington", "OUTSIDE -- refused by name (order)."),
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
         "The order's named areas that share a postal code with another area (College Park / Hapeville / "
         "ATL; Sandy Springs / Dunwoody; Cumberland / Vinings) are reported as a NEAREST-ANCHOR overlay on "
         "each property's coordinates. The overlay decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Six cells observe Acworth, Lawrenceville, Buford, Union City, McDonough and Conyers. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotel / motel / inn / resort establishments operated as lodging businesses. "
         "Individual apartments and condos, short-term-rental portfolios (Airbnb / Vrbo-style units, "
         "Sonder-style app-only apartments without a hotel front desk), ordinary apartment communities, "
         "non-hotel corporate housing, vacation-rental listings, student housing, RV parks and "
         "hostels-as-dormitories are NON_HOTEL exclusions, never admitted. An apartment-hotel or "
         "extended-stay hotel is admitted only when it is operated as a hotel (bookable nightly rooms "
         "under one name, an official property page, and a front desk or brand hotel operation)."),
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
