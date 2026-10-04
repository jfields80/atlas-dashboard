"""PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5 and 6: the Minneapolis / St. Paul / Twin Cities
market.

Built from zero on the CURRENT hardened lineage: the Portland-live release e494698f (live lineage commit aeb57df1,
built_from 22ff1c94). Current verified live at authoring time = portland-or deploy 6ac264b79e70ce6a7db4baaf, 41
markets / 3,819 profiles / 4,206 release-index routes / 4,280 served routes, host verified (release_index live-source
--fetch --verify-host). No earlier Minneapolis build exists. It is the FIRST Minnesota market: no live market admits a
Minnesota postal code, and the build refuses to admit any code a registered market already admits.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Twin Cities traveller lodging market -- a TWO-CITY market, Minneapolis AND St. Paul, never St. Paul
flattened into Minneapolis -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE
markets named inside OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact
to make a number. The order's "STRONG_CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property card)
states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP
is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing
name never admits and never places a property.

WHY "MINNEAPOLIS" AND "ST. PAUL" DECIDE NOTHING HERE (PHASES 3 AND 4)
--------------------------------------------------------------------
The chains put "Minneapolis" on hotels in Bloomington, Eagan, Edina, Eden Prairie, Plymouth, Maple Grove, Brooklyn
Park and Burnsville ("Minneapolis Airport", "Minneapolis/Bloomington", "Minneapolis-Mall of America", "Minneapolis
West", "Minneapolis North", "Minneapolis South") and "St. Paul" on hotels in Roseville, Maplewood, Woodbury, Oakdale,
Shoreview, Mendota Heights and Eagan ("St. Paul North", "St. Paul East", "St. Paul-Woodbury", "Minneapolis-St. Paul
Airport"). A property's own street and postal code place it; its name never does. The MSP / Bloomington cluster is
the trap the order singles out: a hotel at the Mall of America is a BLOOMINGTON hotel (55425), a hotel on American
Blvd East is a Bloomington hotel marketed as "Airport", and the one hotel physically inside the airport
(Fort Snelling, 55111) is the msp-airport corridor. One premises is one row however many of "airport", "Mall of
America", "Bloomington" and "Minneapolis" its marketing carries.

DOWNTOWN OVERLAYS, NEVER SPLIT CODES
-----------------------------------
North Loop, the Warehouse District and the Mill District share 55401 / 55415 with the downtown core; Lowertown,
Rice Park, Cathedral Hill and West 7th share 55101 / 55102 with downtown St. Paul. They are OVERLAYS of their
corridor, reported by the property's own street, never split postal codes.

RESIDENCE / APARTMENT / VACATION-RENTAL SAFETY (PHASE 5) AND TIMESHARE (PHASE 6)
-------------------------------------------------------------------------------
Qualifying public hotels are admitted on their own pages. Individual condo units, private residences, Airbnb /
Vrbo units, ordinary apartments, corporate-housing and property-management portfolios, serviced-apartment and
aparthotel operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Lark, Barsala, Zeus, Furnished Finder,
Oakwood / corporate housing, Stay Alfred), student housing and timeshare / vacation-club inventory (WorldMark, Club
Wyndham, Hilton Grand Vacations, Marriott Vacation Club, Holiday Inn Club Vacations, Bluegreen, Shell Vacations) are
never admitted, even when they accept short stays; a mixed property is admitted only as the exact hotel premises its
public operator sells. Patient and charitable housing (Ronald McDonald House, Hope Lodge, Fisher House, the Mayo /
University of Minnesota / Children's family housing) is never public lodging. Phoenix's lesson is carried as a RULE:
a vacation-club resort is TIMESHARE even when its brand lists it beside its hotels and even when a pet-policy page
exists.

MILITARY / GOVERNMENT LODGING
-----------------------------
The Minneapolis-St. Paul Joint Air Reserve Station and the 133rd Airlift Wing (Minnesota Air National Guard) sit at
MSP inside 55450 / 55111; their on-base lodging is never public. Fort Snelling's historic district sells no
on-base public lodging. The on-base names are refused wherever they appear (NONPUBLIC_NAMES).

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/minneapolis_mn.json
  launch_packages/pettripfinder/markets/proposed/minneapolis-mn.json
  launch_packages/pettripfinder/markets/reports/minneapolis_mn_geography_001.json
  launch_packages/pettripfinder/markets/reports/minneapolis_mn_corridor_registry_001.json
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001"
MARKET_ID = "minneapolis-mn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "minneapolis_mn.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "minneapolis-mn.json")
REPORT_OUT = os.path.join(REPORTS, "minneapolis_mn_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "minneapolis_mn_corridor_registry_001.json")
#: Every REGISTERED market's own document: no postal code any of them admits may be admitted here.
REGISTERED_MARKETS_GLOB = os.path.join(PKG, "markets", "*.json")
AS_OF = "2026-10-04"
STATE_CODE = "MN"
STATE_CODES = ("MN",)


def state_for_postal(postal):
    """The state a postal code belongs to: Minnesota 550-567, Wisconsin 530-549. A row's own page still decides;
    this is the fallback when a lane states no state of its own."""
    z = (postal or "").strip()[:3]
    if z.isdigit() and 550 <= int(z) <= 567:
        return "MN"
    if z.isdigit() and 530 <= int(z) <= 549:
        return "WI"
    return ""


#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description, state)
#: The order's PRIMARY / REQUIRED evaluation areas are CORE, its STRONG CORRIDORS are CORRIDOR and its CAREFUL
#: evaluation areas are FRINGE (or covered whole inside a code they share).
CORRIDORS = [
    # ---------------------------------------------------------------- CORE (City of Minneapolis)
    ("downtown-minneapolis", "Downtown Minneapolis", "Downtown core / Nicollet Mall / North Loop / Warehouse District "
     "/ Mill District / Downtown East / Loring Park / Elliot Park / Convention Center", "CORE", "minneapolis",
     ["55401", "55402", "55403", "55404", "55415"],
     "Downtown Minneapolis: the Nicollet Mall core and skyway hotel row (55402), the North Loop, Warehouse District, "
     "Gateway and the west Mill District along the river (55401), Loring Park, the Minneapolis Convention Center and "
     "the 11th / 12th Street hotel row (55403), Elliot Park and the Hennepin County Medical Center side (55404), and "
     "Downtown East / U.S. Bank Stadium / the east Mill District (55415). North Loop and the Mill District are "
     "OVERLAYS reported by street, never split codes.", "MN"),
    ("university-dinkytown", "University of Minnesota & Dinkytown", "Dinkytown / Marcy-Holmes / Stadium Village / "
     "Prospect Park / East Bank / West Bank / Cedar-Riverside", "CORE", "minneapolis", ["55414", "55454", "55455"],
     "The University of Minnesota's East Bank, Dinkytown, Marcy-Holmes, Stadium Village and Prospect Park (55414), "
     "the West Bank and Cedar-Riverside (55454) and the campus code (55455) -- university, Huntington Bank Stadium and "
     "the M Health Fairview medical demand.", "MN"),
    ("uptown-south-minneapolis", "Uptown & South Minneapolis", "Uptown / Lyn-Lake / Bde Maka Ska / Lake Harriet / "
     "Linden Hills / Powderhorn / Longfellow / Minnehaha / Nokomis / Bryn Mawr", "CORE", "minneapolis",
     ["55405", "55406", "55407", "55408", "55409", "55410", "55417", "55419"],
     "Uptown, Lyn-Lake and the chain of lakes (55408 / 55405 / 55410), Powderhorn and Phillips south (55407), "
     "Longfellow and Minnehaha Falls (55406 / 55417), and the southwest and Tangletown neighbourhoods (55409 / "
     "55419). Inside the city; never left unclaimed.", "MN"),
    ("northeast-minneapolis", "Northeast Minneapolis", "Northeast / Nicollet Island east / St. Anthony Main / Arts "
     "District / Central Ave / Columbia Park", "CORE", "minneapolis", ["55413", "55418"],
     "Northeast Minneapolis: St. Anthony Main and the Northeast Arts District (55413) and Northeast north to "
     "Columbia Heights' line (55418).", "MN"),
    ("north-minneapolis", "North Minneapolis", "North Minneapolis / Near North / Camden / Victory", "CORE",
     "minneapolis", ["55411", "55412"],
     "North Minneapolis (55411 / 55412). Inside the city; not named by the order, claimed so no city code is left "
     "unaccounted.", "MN"),
    # ---------------------------------------------------------------- CORE (City of St. Paul)
    ("downtown-st-paul", "Downtown St. Paul", "Downtown St. Paul / Lowertown / Rice Park / Xcel Energy Center / "
     "RiverCentre / Cathedral Hill / West 7th / Capitol", "CORE", "st paul", ["55101", "55102", "55155"],
     "Downtown St. Paul: Lowertown, the Union Depot, CHS Field and the east downtown hotel row (55101), Rice Park, the "
     "Xcel Energy Center, RiverCentre, Cathedral Hill and West 7th (55102) and the Capitol complex (55155). "
     "Lowertown, Rice Park, Cathedral Hill and West 7th are OVERLAYS reported by street, never split codes.", "MN"),
    ("st-paul-midway", "St. Paul Midway & University Avenue", "Midway / University Avenue / Allianz Field / "
     "Frogtown / Merriam Park / St. Anthony Park / Como / State Fairgrounds / Falcon Heights", "CORE", "st paul",
     ["55103", "55104", "55108", "55114"],
     "The University Avenue / Green Line corridor between the two downtowns: Frogtown and the Capitol north (55103), "
     "the Midway, Allianz Field and Merriam Park (55104), the Raymond / Midway west industrial side (55114) and St. "
     "Anthony Park, Como, the University of Minnesota St. Paul campus, the State Fairgrounds and Falcon Heights "
     "(55108).", "MN"),
    ("st-paul-neighborhoods", "St. Paul Neighborhoods", "Highland Park / Mac-Groveland / West Side / Dayton's Bluff / "
     "East Side / North End", "CORE", "st paul", ["55105", "55106", "55107", "55116", "55117", "55130"],
     "St. Paul's residential neighbourhoods: Mac-Groveland and Summit Avenue (55105), Highland Park and the West 7th "
     "south end (55116), the West Side (55107), Dayton's Bluff and the East Side (55106 / 55130) and the North End "
     "/ Rice Street (55117, shared with Little Canada and western Maplewood, covered whole).", "MN"),
    # ---------------------------------------------------------------- CORE (MSP / Bloomington)
    ("msp-airport", "MSP Airport", "Minneapolis-St. Paul International Airport / Terminal 1 / Terminal 2 / Fort "
     "Snelling", "CORE", "fort snelling", ["55111", "55450"],
     "The airport itself: the unorganised Fort Snelling territory (55111) and the airport's own code (55450). Only a "
     "hotel physically on airport property is placed here. A hotel MARKETED 'Minneapolis Airport' or 'MSP Airport' "
     "whose own code is Bloomington, Eagan, Mendota Heights or Richfield is placed by that code.", "MN"),
    ("bloomington-mall-of-america", "Bloomington & Mall of America", "Mall of America / South Loop / American Blvd "
     "East / Bloomington East (airport-adjacent) / Normandale Lake / Bloomington West / I-494 strip", "CORE",
     "bloomington",
     ["55420", "55425", "55431", "55437", "55438", "55439"],
     "The City of Bloomington: the South Loop district -- the Mall of America and its connected hotels, and the "
     "airport-adjacent American Blvd East / 24th / 34th Avenue South hotel row (55425) -- the I-494 / American Blvd "
     "central strip (55420 / 55431), and Bloomington West's Normandale Lake office-park hotels (55437 / 55438 / "
     "55439, the last shared with Edina and covered whole). Mall of America, Bloomington East and Bloomington West are "
     "OVERLAYS reported by street.", "MN"),
    # ---------------------------------------------------------------- STRONG CORRIDOR
    ("eagan", "Eagan", "Eagan / Yankee Doodle Road / Pilot Knob / I-494 & I-35E / Viking Lakes / Twin Cities Premium "
     "Outlets", "CORRIDOR", "eagan", ["55121", "55122", "55123"],
     "The City of Eagan: the I-494 / Lone Oak / Pilot Knob airport-adjacent hotel cluster (55121 / 55122) and "
     "south Eagan, the outlets and Viking Lakes (55123). A hotel titled 'Minneapolis Airport' or 'St. Paul' here is "
     "an Eagan hotel. STRONG.", "MN"),
    ("richfield", "Richfield", "Richfield / I-494 & Cedar / 66th Street / Best Buy HQ", "CORRIDOR", "richfield",
     ["55423"],
     "The City of Richfield between Minneapolis and Bloomington (55423). STRONG.", "MN"),
    ("edina", "Edina", "Edina / Southdale / 50th & France / Galleria / Centennial Lakes / France Ave & I-494",
     "CORRIDOR", "edina", ["55424", "55435", "55436"],
     "The City of Edina: Southdale, Galleria, Centennial Lakes and the France Avenue / I-494 hotel cluster (55435), "
     "50th & France (55424) and west Edina (55436). A hotel titled 'Minneapolis-Edina' is placed by its code. "
     "STRONG.", "MN"),
    ("eden-prairie", "Eden Prairie", "Eden Prairie / Eden Prairie Center / I-494 & US-212 / Flying Cloud",
     "CORRIDOR", "eden prairie", ["55344", "55346", "55347"],
     "The City of Eden Prairie: the Eden Prairie Center / I-494 / US-212 office-park hotel cluster (55344) and the "
     "residential south and west (55346 / 55347). STRONG.", "MN"),
    ("minnetonka-hopkins", "Minnetonka, Hopkins & Wayzata", "Minnetonka / Ridgedale / Opus / Hopkins / I-394 / "
     "Wayzata", "CORRIDOR", "minnetonka", ["55305", "55343", "55345", "55391"],
     "The City of Minnetonka -- Ridgedale and the I-394 hotel row (55305), Opus and Hopkins (55343), central "
     "Minnetonka (55345) -- and Wayzata / north Minnetonka on Lake Minnetonka (55391, covered whole). STRONG.", "MN"),
    ("plymouth", "Plymouth", "Plymouth / I-494 & MN-55 / Carlson Parkway / Vicksburg Lane", "CORRIDOR", "plymouth",
     ["55441", "55442", "55446", "55447"],
     "The City of Plymouth: the I-494 / Highway 55 / Carlson Parkway corporate-park hotels (55441 / 55447) and north "
     "Plymouth (55442 / 55446). A hotel titled 'Minneapolis West' or 'Minneapolis-Plymouth' is placed by its code. "
     "STRONG.", "MN"),
    ("roseville", "Roseville & North St. Paul suburbs", "Roseville / Rosedale Center / I-35W & MN-36 / Arden Hills / "
     "New Brighton / Shoreview", "CORRIDOR", "roseville", ["55113", "55112", "55126"],
     "The City of Roseville -- Rosedale Center and the I-35W / Highway 36 hotel cluster (55113) -- with Arden Hills / "
     "New Brighton (55112) and Shoreview (55126) on the I-35W / I-694 ring, where the chains say 'St. Paul North'. "
     "STRONG.", "MN"),
    ("maplewood-oakdale", "Maplewood & Oakdale", "Maplewood / Maplewood Mall / White Bear Ave / I-694 / I-94 & "
     "McKnight / Oakdale", "CORRIDOR", "maplewood", ["55109", "55119", "55128"],
     "The City of Maplewood -- Maplewood Mall and the I-694 / White Bear Avenue hotels (55109), the I-94 / McKnight "
     "Road side shared with St. Paul's Battle Creek (55119, covered whole) -- and Oakdale (55128). A hotel titled "
     "'St. Paul East' is placed by its code. STRONG.", "MN"),
    ("woodbury", "Woodbury", "Woodbury / I-94 & I-494 / Radio Drive / Tamarack / Woodbury Lakes / City Place",
     "CORRIDOR", "woodbury", ["55125", "55129"],
     "The City of Woodbury: the I-94 / I-494 / Radio Drive hotel cluster (55125) and south Woodbury (55129). A hotel "
     "titled 'St. Paul-Woodbury' is a Woodbury hotel. STRONG.", "MN"),
    # ---------------------------------------------------------------- FRINGE (CAREFUL evaluation)
    ("brooklyn-center-brooklyn-park", "Brooklyn Center & Brooklyn Park", "Brooklyn Center / Shingle Creek / I-694 "
     "& MN-100 / Brooklyn Park / I-94 & Boone / Crystal / New Hope", "FRINGE", "brooklyn center",
     ["55430", "55429", "55443", "55444", "55445", "55428"],
     "Brooklyn Center on the I-694 / Highway 100 / Shingle Creek Parkway hotel cluster (55430 / 55429) and Brooklyn "
     "Park (55443 / 55444 / 55445 / 55428, the last shared with Crystal and New Hope). Admitted at FRINGE after "
     "CAREFUL evaluation; metro-continuous inside the I-694 / I-94 ring.", "MN"),
    ("maple-grove", "Maple Grove", "Maple Grove / Arbor Lakes / I-94 & I-494 / Osseo", "FRINGE", "maple grove",
     ["55311", "55369"],
     "The City of Maple Grove -- Arbor Lakes and the I-94 / I-494 / Highway 610 hotel cluster (55311 / 55369, the "
     "latter shared with Osseo). Admitted at FRINGE after CAREFUL evaluation. Rogers, Dayton, Elk River and the "
     "north-west exurbs beyond are refused.", "MN"),
    ("burnsville-shakopee", "Burnsville, Savage & Shakopee", "Burnsville / Burnsville Center / I-35W & County Road "
     "42 / Savage / Shakopee / Canterbury Park / Valleyfair", "FRINGE", "burnsville",
     ["55306", "55337", "55378", "55379"],
     "The City of Burnsville -- Burnsville Center and the I-35W / I-35E / County Road 42 hotel cluster (55337) and "
     "south Burnsville (55306) -- with Savage (55378) and Shakopee, Canterbury Park and Valleyfair (55379), "
     "continuous along the Minnesota River on Highway 13 / 101. Admitted at FRINGE after CAREFUL evaluation. Prior "
     "Lake (Mystic Lake), Apple Valley, Lakeville and Jordan are refused.", "MN"),
    ("mendota-heights-inver-grove", "Mendota Heights, West St. Paul & Inver Grove Heights", "Mendota Heights / "
     "Lilydale / West St. Paul / South St. Paul / Inver Grove Heights / US-52 & I-494", "FRINGE", "mendota heights",
     ["55118", "55120", "55075", "55076", "55077"],
     "Mendota Heights and Lilydale on the I-494 / Highway 13 / 55 side of the airport (55120, shared with north-east "
     "Eagan and covered whole), West St. Paul (55118), South St. Paul (55075) and Inver Grove Heights on US-52 / "
     "I-494 (55076 / 55077). Admitted at FRINGE after CAREFUL evaluation.", "MN"),
    ("golden-valley-st-louis-park", "Golden Valley & St. Louis Park", "St. Louis Park / West End / Excelsior & "
     "Grand / I-394 & MN-100 / Golden Valley / Crystal / Robbinsdale", "FRINGE", "st louis park",
     ["55416", "55426", "55422", "55427"],
     "St. Louis Park -- the West End and the I-394 / Highway 100 hotel row (55416 / 55426) -- and Golden Valley "
     "(55422 / 55427, shared with Robbinsdale, Crystal and New Hope, covered whole). Admitted at FRINGE after CAREFUL "
     "evaluation; first-ring suburbs continuous with Minneapolis.", "MN"),
]

OUTSIDE = [
    ("Rochester / Mayo Clinic / Olmsted County", "MN", ["55901", "55902", "55903", "55904", "55905", "55906"],
     "OLMSTED COUNTY; FUTURE_STANDALONE rochester-mn. Mayo Clinic's medical-travel market 80 miles south-east on "
     "US-52. Refused by name and postal PREFIX (559). A hotel marketed 'Mayo / Minneapolis' is placed by its code."),
    ("Duluth / Lake Superior North Shore / Two Harbors / Cloquet", "MN", [],
     "ST. LOUIS / LAKE COUNTY; FUTURE_STANDALONE duluth-mn. 150 miles north on I-35. Refused by postal PREFIX (556 "
     "/ 557 / 558)."),
    ("St. Cloud / Sauk Rapids / Waite Park", "MN", [],
     "STEARNS / BENTON COUNTY; FUTURE_STANDALONE st-cloud-mn. 65 miles north-west on I-94. Refused by postal PREFIX "
     "(563)."),
    ("Mankato / North Mankato / St. Peter", "MN", ["56001", "56002", "56003", "56082"],
     "BLUE EARTH / NICOLLET COUNTY; FUTURE_STANDALONE mankato-mn. 80 miles south-west on US-169. Refused by name and "
     "postal PREFIX (560)."),
    ("Stillwater / St. Croix Valley -- Stillwater, Oak Park Heights, Bayport, Lake Elmo, Lakeland, Afton, Marine on "
     "St. Croix, Hastings", "MN", ["55082", "55003", "55042", "55043", "55001", "55047", "55033", "55090"],
     "WASHINGTON COUNTY east / DAKOTA COUNTY south-east; FUTURE_STANDALONE stillwater-st-croix. Stillwater's "
     "historic river-town inns and B&Bs are a destination a Twin Cities traveller drives TO, better standalone than "
     "absorbed. Hastings is the Mississippi / St. Croix confluence town on US-61. Refused by name and postal code."),
    ("North metro beyond the I-694 ring -- Columbia Heights, Fridley, Spring Lake Park, Blaine (National Sports "
     "Center), Coon Rapids, Anoka, Ramsey, Andover, Ham Lake, Lino Lakes, White Bear Lake, Vadnais Heights, Hugo, "
     "Forest Lake", "MN",
     ["55421", "55432", "55434", "55449", "55433", "55448", "55303", "55304", "55110", "55127", "55014", "55038",
      "55025", "55011", "55070", "55092"],
     "ANOKA COUNTY / north RAMSEY / north WASHINGTON COUNTY. Not in the order's evaluation list. Refused after "
     "CAREFUL evaluation so the Twin Cities market does not silently absorb the north metro; recorded in the "
     "boundary audit, never silently dropped. A founder may move Blaine / Coon Rapids on the record."),
    ("South metro beyond Burnsville / Eagan -- Apple Valley, Lakeville, Rosemount, Farmington, Cottage Grove, Prior "
     "Lake (Mystic Lake Casino Hotel), Jordan, Belle Plaine, Northfield, Red Wing (Treasure Island)", "MN",
     ["55124", "55044", "55068", "55024", "55016", "55372", "55352", "56011", "55057", "55066", "55089", "55065"],
     "DAKOTA / SCOTT / WASHINGTON / GOODHUE / RICE COUNTY outside the evaluated suburbs; refused after CAREFUL "
     "evaluation. Mystic Lake (Prior Lake) and Treasure Island (Red Wing / Welch) are tribal casino resorts a "
     "traveller drives TO. Recorded, never silently absorbed."),
    ("Western / north-western exurbs -- Chanhassen, Chaska, Victoria, Excelsior, Mound, Long Lake, Orono, Medina, "
     "Hamel, Rogers, Dayton, Champlin, Elk River, Otsego, Albertville, St. Michael, Monticello, Buffalo, Delano",
     "MN",
     ["55317", "55318", "55386", "55331", "55364", "55356", "55340", "55374", "55327", "55316", "55330", "55301",
      "55376", "55362", "55313", "55328", "55357", "55359", "55384", "55387"],
     "CARVER / western HENNEPIN / WRIGHT / SHERBURNE COUNTY. The order's 'farther western / northern exurbs' -- "
     "KEEP SEPARATE. Refused by name and postal code."),
    ("Wisconsin -- Hudson, River Falls, Prescott, Somerset (St. Croix / Pierce counties) and the rest of Wisconsin",
     "WI", ["54016", "54022", "54021", "54025", "54082"],
     "Across the St. Croix in WISCONSIN. The Twin Cities market is a Minnesota market; Hudson is refused by its own "
     "state and code (and the live milwaukee-wi market owns its own Wisconsin codes). Refused by PREFIX (530-549)."),
    ("Greater Minnesota and out of state", "--", [],
     "Every other Minnesota postal prefix (556-567: Duluth, Rochester, Mankato, Willmar, St. Cloud, Brainerd, "
     "Detroit Lakes, Bemidji, Thief River Falls) and every non-Minnesota code is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("556", "Duluth region / north-east Minnesota (Arrowhead)", "duluth-mn"),
    ("557", "Duluth region / Iron Range", "duluth-mn"),
    ("558", "Duluth", "duluth-mn"),
    ("559", "Rochester / south-east Minnesota", "rochester-mn"),
    ("560", "Mankato / south-central Minnesota", "mankato-mn"),
    ("561", "Windom / south-west Minnesota", ""),
    ("562", "Willmar / west-central Minnesota", ""),
    ("563", "St. Cloud / central Minnesota", "st-cloud-mn"),
    ("564", "Brainerd / north-central Minnesota", ""),
    ("565", "Detroit Lakes / north-west Minnesota", ""),
    ("566", "Bemidji / north Minnesota", ""),
    ("567", "Thief River Falls / north-west Minnesota", ""),
] + [("%03d" % p, "Wisconsin", "") for p in range(530, 550)]

#: The Twin Cities' own postal prefixes. A code under one of these that no corridor claims and no OUTSIDE row names
#: is an UNCLAIMED metro / east-central Minnesota code -- refused, and named in the boundary audit so it is visible,
#: never silently dropped.
VALLEY_PREFIXES = ("550", "551", "553", "554", "555")

ADMITTED_COUNTIES = {"hennepin (minneapolis, bloomington, richfield, edina, eden prairie, minnetonka, hopkins, "
                     "wayzata, plymouth, st. louis park, golden valley, brooklyn center, brooklyn park, maple grove; "
                     "the western exurbs refused)",
                     "ramsey (st. paul, roseville, maplewood, arden hills, new brighton, shoreview, falcon heights; "
                     "white bear lake and vadnais heights refused)",
                     "dakota (eagan, mendota heights, west st. paul, south st. paul, inver grove heights, burnsville; "
                     "apple valley, lakeville, rosemount, hastings refused)",
                     "washington (woodbury, oakdale; stillwater and the st. croix valley refused)",
                     "scott (savage, shakopee; prior lake / mystic lake and jordan refused)",
                     "fort snelling unorganized territory (msp airport)"}
OBSERVED_COUNTIES = OrderedDict([
    ("olmsted (rochester)", "rochester-mn"),
    ("st. louis / lake (duluth)", "duluth-mn"),
    ("stearns / benton (st. cloud)", "st-cloud-mn"),
    ("blue earth / nicollet (mankato)", "mankato-mn"),
    ("washington east (stillwater)", "stillwater-st-croix"),
    ("anoka (blaine, coon rapids, fridley, anoka)", "(none -- refused after careful evaluation)"),
    ("carver / wright / sherburne (western exurbs)", "(none -- refused, keep separate)"),
    ("st. croix / pierce, wisconsin (hudson, river falls)", "(none -- another state)"),
])

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("hennepin", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. Minneapolis, Bloomington, Richfield, Edina, Eden Prairie, Minnetonka, Hopkins, "
                   "Wayzata, Plymouth, St. Louis Park, Golden Valley, Brooklyn Center, Brooklyn Park and Maple Grove "
                   "are admitted; Rogers, Dayton, Champlin, Medina, Orono, Mound and the western lake towns are "
                   "refused. County inclusion is not traveller-market inclusion."),
    ])),
    ("ramsey", OrderedDict([
        ("ruling", "ADMITTED INSIDE THE I-694 RING. St. Paul, Roseville, Maplewood, Falcon Heights, Arden Hills, New "
                   "Brighton and Shoreview are admitted; White Bear Lake and Vadnais Heights are refused."),
    ])),
    ("dakota", OrderedDict([
        ("ruling", "ADMITTED NORTH OF COUNTY ROAD 42. Eagan, Mendota Heights, West St. Paul, South St. Paul, Inver "
                   "Grove Heights and Burnsville are admitted; Apple Valley, Lakeville, Rosemount, Farmington and "
                   "Hastings are refused."),
    ])),
    ("washington", OrderedDict([
        ("ruling", "ADMITTED ONLY AT WOODBURY / OAKDALE. Stillwater, Oak Park Heights, Bayport, Lake Elmo and the St. "
                   "Croix Valley are refused (FUTURE_STANDALONE stillwater-st-croix); Cottage Grove and Forest Lake "
                   "are refused."),
    ])),
    ("scott", OrderedDict([
        ("ruling", "ADMITTED ONLY AT SAVAGE / SHAKOPEE. Prior Lake (Mystic Lake), Jordan and Belle Plaine are "
                   "refused."),
    ])),
    ("anoka / carver / wright / sherburne", OrderedDict([
        ("ruling", "REFUSED. The north metro beyond I-694 and the western / north-western exurbs are not absorbed."),
    ])),
    ("olmsted / st. louis / stearns / blue earth", OrderedDict([
        ("ruling", "REFUSED. Rochester, Duluth, St. Cloud and Mankato are standalone markets (FUTURE_STANDALONE "
                   "rochester-mn, duluth-mn, st-cloud-mn, mankato-mn)."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / patient / member
#: only). A normalised-name substring match; the census row keeps its reason.
NONPUBLIC_NAMES = {
    "navy lodge": "Navy Lodge on-base lodging -- MILITARY_RESTRICTED",
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- restricted to authorised DoD travellers; MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "air reserve station": "Minneapolis-St. Paul Joint Air Reserve Station lodging -- MILITARY_RESTRICTED",
    "air national guard": "Air National Guard base lodging -- MILITARY_RESTRICTED",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "hope lodge": "American Cancer Society Hope Lodge -- patient lodging, not public lodging",
    "family housing": "patient-family housing -- not public lodging",
    "gift of life": "transplant-patient family housing -- not public lodging",
}

#: Military postal codes inside the admitted partition. The Joint Air Reserve Station / 133rd Airlift Wing sit on
#: MSP inside 55450; neither sells public lodging, and no public hotel is refused for its code -- the NAMES are.
MILITARY_POSTAL_CODES = OrderedDict()

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-minneapolis", "Minneapolis", "Downtown / North Loop / Mill District / Loring Park", 44.9760, -93.2700,
     2200, True),
    ("university-dinkytown", "Minneapolis", "University / Dinkytown / Cedar-Riverside", 44.9760, -93.2300, 2200,
     True),
    ("uptown-south-minneapolis", "Minneapolis", "Uptown / South Minneapolis / Longfellow / Nokomis", 44.9300,
     -93.2600, 6000, True),
    ("northeast-minneapolis", "Minneapolis", "Northeast Minneapolis", 45.0050, -93.2450, 3000, True),
    ("north-minneapolis", "Minneapolis", "North Minneapolis", 45.0100, -93.3000, 3000, True),
    ("downtown-st-paul", "St. Paul", "Downtown St. Paul / Lowertown / Rice Park / Cathedral Hill / West 7th",
     44.9480, -93.0950, 2200, True),
    ("st-paul-midway", "St. Paul", "Midway / University Ave / Como / St. Anthony Park", 44.9650, -93.1650, 4000, True),
    ("st-paul-neighborhoods", "St. Paul", "Highland / Mac-Groveland / West Side / East Side / North End", 44.9350,
     -93.1200, 6500, True),
    ("msp-airport", "Fort Snelling", "MSP Airport / Fort Snelling", 44.8850, -93.2150, 3000, True),
    ("bloomington-mall-of-america", "Bloomington", "Bloomington / Mall of America / American Blvd / Normandale",
     44.8500, -93.3000, 7500, True),
    ("eagan", "Eagan", "Eagan / Pilot Knob / Yankee Doodle", 44.8250, -93.1700, 5500, True),
    ("richfield", "Richfield", "Richfield", 44.8800, -93.2800, 2500, True),
    ("edina", "Edina", "Edina / Southdale / Galleria / France Ave", 44.8950, -93.3500, 4000, True),
    ("eden-prairie", "Eden Prairie", "Eden Prairie", 44.8550, -93.4700, 5500, True),
    ("minnetonka-hopkins", "Minnetonka", "Minnetonka / Hopkins / Ridgedale / Wayzata", 44.9400, -93.4600, 6500, True),
    ("plymouth", "Plymouth", "Plymouth", 45.0100, -93.4600, 5500, True),
    ("roseville", "Roseville", "Roseville / Arden Hills / New Brighton / Shoreview", 45.0400, -93.1600, 5500, True),
    ("maplewood-oakdale", "Maplewood", "Maplewood / Oakdale", 45.0000, -93.0100, 5500, True),
    ("woodbury", "Woodbury", "Woodbury", 44.9200, -92.9400, 5000, True),
    ("brooklyn-center-brooklyn-park", "Brooklyn Center", "Brooklyn Center / Brooklyn Park / Crystal", 45.0850,
     -93.3400, 6500, True),
    ("maple-grove", "Maple Grove", "Maple Grove / Osseo", 45.0950, -93.4500, 5000, True),
    ("burnsville-shakopee", "Burnsville", "Burnsville / Savage / Shakopee", 44.7800, -93.3800, 9000, True),
    ("mendota-heights-inver-grove", "Mendota Heights", "Mendota Heights / West St. Paul / South St. Paul / Inver "
     "Grove Heights", 44.8700, -93.0800, 6000, True),
    ("golden-valley-st-louis-park", "St. Louis Park", "St. Louis Park / Golden Valley / Crystal", 44.9750, -93.3500,
     5000, True),
    ("obs-rochester", "Rochester", "Rochester / Mayo Clinic -- OBSERVATION ONLY", 44.0200, -92.4700, 15000, False),
    ("obs-duluth", "Duluth", "Duluth / North Shore -- OBSERVATION ONLY", 46.7900, -92.1000, 15000, False),
    ("obs-st-cloud", "St. Cloud", "St. Cloud / Waite Park -- OBSERVATION ONLY", 45.5600, -94.1700, 12000, False),
    ("obs-mankato", "Mankato", "Mankato / North Mankato -- OBSERVATION ONLY", 44.1650, -94.0000, 10000, False),
    ("obs-stillwater", "Stillwater", "Stillwater / Oak Park Heights / Lake Elmo / Hastings -- OBSERVATION ONLY",
     44.9500, -92.8300, 15000, False),
    ("obs-north-metro", "Blaine", "Blaine / Coon Rapids / Fridley / Anoka / White Bear Lake -- OBSERVATION ONLY",
     45.1500, -93.2300, 15000, False),
    ("obs-south-metro", "Lakeville", "Apple Valley / Lakeville / Prior Lake / Rosemount -- OBSERVATION ONLY",
     44.7000, -93.2500, 15000, False),
    ("obs-west-exurbs", "Chanhassen", "Chanhassen / Chaska / Rogers / Elk River / Monticello -- OBSERVATION ONLY",
     45.0000, -93.6500, 25000, False),
]

#: The observation box. It reaches south past Rochester and Mankato, north to Duluth and west past St. Cloud, so the
#: census counts what it refuses.
BOUNDS = {"min_lat": 43.90, "max_lat": 46.90, "min_lng": -94.45, "max_lng": -91.95}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("North Loop / Warehouse District", 44.9870, -93.2760, 0.80),
    ("Mill District / Downtown East", 44.9780, -93.2560, 0.65),
    ("Downtown Minneapolis core / Nicollet Mall", 44.9760, -93.2720, 0.80),
    ("Loring Park / Convention Center", 44.9690, -93.2810, 0.60),
    ("Downtown Minneapolis", 44.9760, -93.2700, 1.50),
    ("University / Dinkytown", 44.9800, -93.2350, 1.30),
    ("Uptown / Lyn-Lake", 44.9480, -93.2960, 1.40),
    ("South Minneapolis / Longfellow / Nokomis", 44.9200, -93.2300, 4.00),
    ("Northeast Minneapolis", 45.0050, -93.2470, 2.20),
    ("Lowertown", 44.9490, -93.0860, 0.55),
    ("Rice Park / Xcel Energy Center", 44.9440, -93.1000, 0.55),
    ("Cathedral Hill / West 7th", 44.9400, -93.1150, 1.10),
    ("Downtown St. Paul", 44.9480, -93.0930, 1.20),
    ("St. Paul Midway / University Ave", 44.9560, -93.1670, 2.40),
    ("MSP Airport terminals", 44.8830, -93.2120, 2.00),
    ("Mall of America", 44.8550, -93.2420, 0.80),
    ("Bloomington East (airport-adjacent)", 44.8580, -93.2250, 2.20),
    ("Bloomington West / Normandale", 44.8560, -93.3500, 3.00),
    ("Bloomington central / I-494", 44.8600, -93.2900, 2.50),
    ("Eagan", 44.8250, -93.1650, 4.00),
    ("Richfield", 44.8800, -93.2800, 2.00),
    ("Edina / Southdale / Galleria", 44.8800, -93.3250, 2.50),
    ("Eden Prairie", 44.8550, -93.4500, 4.00),
    ("Minnetonka / Hopkins / Ridgedale", 44.9500, -93.4400, 4.00),
    ("Plymouth", 45.0100, -93.4600, 4.00),
    ("Roseville / Rosedale", 45.0150, -93.1650, 3.00),
    ("Maplewood / Oakdale", 45.0050, -93.0050, 4.00),
    ("Woodbury", 44.9300, -92.9400, 4.00),
    ("Brooklyn Center / Brooklyn Park", 45.0800, -93.3400, 4.50),
    ("Maple Grove", 45.0950, -93.4400, 3.50),
    ("Burnsville / Savage / Shakopee", 44.7800, -93.3500, 8.00),
    ("Mendota Heights / Inver Grove Heights", 44.8700, -93.1000, 5.00),
    ("St. Louis Park / Golden Valley", 44.9700, -93.3500, 3.50),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("MSP Airport terminals", re.compile(r"\bglumack\b|\b5005 glumack\b|\bairport (dr|drive)\b(?=.*551(11|450))|"
                                         r"\b(55111|55450)\b", re.I)),
    ("Mall of America", re.compile(r"\blindau (ln|lane)\b|\bkillebrew (dr|drive)\b|\bmall of america\b|"
                                   r"\b(24th|22nd) ave(nue)? s(outh)?\b(?=.*55425)", re.I)),
    ("Bloomington East (airport-adjacent)", re.compile(r"\bamerican (blvd|boulevard) e(ast)?\b|"
                                                       r"\b(34th|28th|30th) ave(nue)? s(outh)?\b(?=.*55425)|"
                                                       r"\be (78th|79th|80th|81st) st\b(?=.*554(20|25))", re.I)),
    ("Bloomington West / Normandale", re.compile(r"\bnormandale (blvd|boulevard|lake)\b|\bamerican (blvd|boulevard) "
                                                 r"w(est)?\b|\b(55437|55438|55439)\b", re.I)),
    ("North Loop / Warehouse District", re.compile(r"\b(washington|1st|2nd|3rd|4th|5th) (ave|avenue|st|street) "
                                                   r"n(orth)?\b(?=.*55401)|\bn (washington|1st|2nd|3rd|4th|5th) "
                                                   r"(ave|st)\b(?=.*55401)|\bhennepin (ave|avenue)\b(?=.*55401)", re.I)),
    ("Mill District / Downtown East", re.compile(r"\b(washington|2nd|3rd|4th) (ave|avenue|st|street) s(outh)?\b"
                                                 r"(?=.*554(01|15))|\bs (washington|2nd|3rd) (ave|st)\b"
                                                 r"(?=.*554(01|15))|\bportland ave\b(?=.*55415)|\bchicago ave\b"
                                                 r"(?=.*55415)|\b(5th|6th|7th|8th|9th|10th|11th) ave s\b(?=.*55415)",
                                                 re.I)),
    ("Loring Park / Convention Center", re.compile(r"\b(11th|12th|13th|grant) st(reet)?\b(?=.*55403)|"
                                                   r"\bnicollet (mall|ave)\b(?=.*55403)|\bharmon pl\b|\bwillow st\b",
                                                   re.I)),
    ("Lowertown", re.compile(r"\b(e|east) (4th|5th|6th|7th|kellogg) (st|street|blvd)\b(?=.*55101)|\bsibley\b|"
                             r"\bbroadway st\b(?=.*55101)|\bwacouta\b|\bjackson st\b(?=.*55101)", re.I)),
    ("Rice Park / Xcel Energy Center", re.compile(r"\bmarket st\b(?=.*55102)|\bkellogg (blvd|boulevard) w(est)?\b|"
                                                  r"\bw(est)? kellogg\b|\bwashington st\b(?=.*55102)|"
                                                  r"\bst peter st\b(?=.*55102)", re.I)),
    ("Cathedral Hill / West 7th", re.compile(r"\bw(est)? 7th st\b|\bwest seventh\b|\bselby ave\b|\bsummit ave\b|"
                                             r"\bkellogg blvd\b(?=.*55102)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-minneapolis": "Downtown Minneapolis",
    "university-dinkytown": "University / Dinkytown",
    "uptown-south-minneapolis": "South Minneapolis / Longfellow / Nokomis",
    "northeast-minneapolis": "Northeast Minneapolis",
    "north-minneapolis": "North Minneapolis",
    "downtown-st-paul": "Downtown St. Paul",
    "st-paul-midway": "St. Paul Midway / University Ave",
    "st-paul-neighborhoods": "St. Paul neighborhoods",
    "msp-airport": "MSP Airport terminals",
    "bloomington-mall-of-america": "Bloomington central / I-494",
    "eagan": "Eagan",
    "richfield": "Richfield",
    "edina": "Edina / Southdale / Galleria",
    "eden-prairie": "Eden Prairie",
    "minnetonka-hopkins": "Minnetonka / Hopkins / Ridgedale",
    "plymouth": "Plymouth",
    "roseville": "Roseville / Rosedale",
    "maplewood-oakdale": "Maplewood / Oakdale",
    "woodbury": "Woodbury",
    "brooklyn-center-brooklyn-park": "Brooklyn Center / Brooklyn Park",
    "maple-grove": "Maple Grove",
    "burnsville-shakopee": "Burnsville / Savage / Shakopee",
    "mendota-heights-inver-grove": "Mendota Heights / Inver Grove Heights",
    "golden-valley-st-louis-park": "St. Louis Park / Golden Valley",
}

#: The order's PRIMARY / STRONG / CAREFUL / KEEP-SEPARATE evaluation list, each classified explicitly.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Minneapolis", "ADMITTED (CORE, downtown-minneapolis, 55401 / 55402 / 55403 / 55404 / 55415). "
                             "PRIMARY."),
    ("North Loop", "ADMITTED (CORE, downtown-minneapolis, 55401 -- shared with the Warehouse District and the core, "
                   "never split) -- reported as an overlay. PRIMARY."),
    ("Mill District", "ADMITTED (CORE, downtown-minneapolis, 55401 / 55415) -- reported as an overlay. PRIMARY."),
    ("University / Dinkytown", "ADMITTED (CORE, university-dinkytown, 55414 / 55454 / 55455). PRIMARY."),
    ("Uptown / South Minneapolis", "ADMITTED (CORE, uptown-south-minneapolis, 55405 / 55406 / 55407 / 55408 / 55409 "
                                   "/ 55410 / 55417 / 55419). PRIMARY."),
    ("Northeast Minneapolis", "ADMITTED (CORE, northeast-minneapolis, 55413 / 55418). PRIMARY."),
    ("Downtown St. Paul", "ADMITTED (CORE, downtown-st-paul, 55101 / 55102 / 55155). PRIMARY."),
    ("Cathedral Hill", "ADMITTED (CORE, downtown-st-paul, 55102) -- reported as an overlay. PRIMARY."),
    ("West 7th", "ADMITTED (CORE, downtown-st-paul, 55102; its south end 55116 is st-paul-neighborhoods) -- reported "
                 "as an overlay. PRIMARY."),
    ("Lowertown", "ADMITTED (CORE, downtown-st-paul, 55101) -- reported as an overlay. PRIMARY."),
    ("University / Midway", "ADMITTED (CORE, st-paul-midway, 55103 / 55104 / 55108 / 55114). PRIMARY."),
    ("MSP Airport", "ADMITTED (CORE, msp-airport, 55111 / 55450) -- only hotels physically on airport property. "
                    "PRIMARY."),
    ("Bloomington", "ADMITTED (CORE, bloomington-mall-of-america, 55420 / 55425 / 55431 / 55437 / 55438 / 55439). "
                    "PRIMARY."),
    ("Mall of America", "ADMITTED (CORE, bloomington-mall-of-america, 55425) -- reported as an overlay. PRIMARY."),
    ("Eagan", "ADMITTED (STRONG CORRIDOR, eagan, 55121 / 55122 / 55123). STRONG."),
    ("Richfield", "ADMITTED (STRONG CORRIDOR, richfield, 55423). STRONG."),
    ("Edina", "ADMITTED (STRONG CORRIDOR, edina, 55424 / 55435 / 55436). STRONG."),
    ("Eden Prairie", "ADMITTED (STRONG CORRIDOR, eden-prairie, 55344 / 55346 / 55347). STRONG."),
    ("Minnetonka", "ADMITTED (STRONG CORRIDOR, minnetonka-hopkins, 55305 / 55343 / 55345 / 55391). STRONG."),
    ("Plymouth", "ADMITTED (STRONG CORRIDOR, plymouth, 55441 / 55442 / 55446 / 55447). STRONG."),
    ("Roseville", "ADMITTED (STRONG CORRIDOR, roseville, 55113 / 55112 / 55126). STRONG."),
    ("Maplewood", "ADMITTED (STRONG CORRIDOR, maplewood-oakdale, 55109 / 55119 / 55128). STRONG."),
    ("Woodbury", "ADMITTED (STRONG CORRIDOR, woodbury, 55125 / 55129). STRONG."),
    ("Brooklyn Center", "ADMITTED (FRINGE, brooklyn-center-brooklyn-park, 55430 / 55429). CAREFUL."),
    ("Brooklyn Park", "ADMITTED (FRINGE, brooklyn-center-brooklyn-park, 55443 / 55444 / 55445 / 55428). CAREFUL."),
    ("Maple Grove", "ADMITTED (FRINGE, maple-grove, 55311 / 55369). CAREFUL."),
    ("Burnsville", "ADMITTED (FRINGE, burnsville-shakopee, 55306 / 55337). CAREFUL."),
    ("Shakopee", "ADMITTED (FRINGE, burnsville-shakopee, 55379; Savage 55378 between them). CAREFUL."),
    ("Mendota Heights", "ADMITTED (FRINGE, mendota-heights-inver-grove, 55120 / 55118). CAREFUL."),
    ("Inver Grove Heights", "ADMITTED (FRINGE, mendota-heights-inver-grove, 55076 / 55077; South St. Paul 55075). "
                            "CAREFUL."),
    ("Golden Valley", "ADMITTED (FRINGE, golden-valley-st-louis-park, 55422 / 55427). CAREFUL."),
    ("St. Louis Park", "ADMITTED (FRINGE, golden-valley-st-louis-park, 55416 / 55426). CAREFUL."),
    ("Rochester", "OUTSIDE -- FUTURE_STANDALONE rochester-mn; refused by prefix 559. KEEP SEPARATE."),
    ("Duluth", "OUTSIDE -- FUTURE_STANDALONE duluth-mn; refused by prefix 556 / 557 / 558. KEEP SEPARATE."),
    ("St. Cloud", "OUTSIDE -- FUTURE_STANDALONE st-cloud-mn; refused by prefix 563. KEEP SEPARATE."),
    ("Mankato", "OUTSIDE -- FUTURE_STANDALONE mankato-mn; refused by prefix 560. KEEP SEPARATE."),
    ("Stillwater", "OUTSIDE -- FUTURE_STANDALONE stillwater-st-croix; the river-town inns are better standalone. "
                   "KEEP SEPARATE."),
    ("Farther western / northern exurbs", "OUTSIDE -- Chanhassen, Chaska, Rogers, Elk River, Monticello, Blaine, Coon "
                                          "Rapids, Anoka and beyond; refused by name and postal code. KEEP SEPARATE."),
    ("Hudson, Wisconsin", "OUTSIDE -- another state; refused by its Wisconsin code."),
])

#: The MSP / Bloomington ruling (Phase 4), stated once.
MSP_BLOOMINGTON_EVALUATION = OrderedDict([
    ("msp_airport", "Only a hotel physically on airport property (Fort Snelling 55111 / airport 55450) is the "
                    "msp-airport corridor. Every other hotel marketed 'MSP Airport', 'Minneapolis Airport' or "
                    "'Minneapolis-St. Paul Airport' is placed by its own code: Bloomington (55425 / 55420), Eagan "
                    "(55121 / 55122), Mendota Heights (55120) or Richfield (55423)."),
    ("mall_of_america", "The Mall of America is 55425, Bloomington. Its connected hotels and the hotels marketed "
                        "'Mall of America' are Bloomington hotels and report under the Mall of America overlay by "
                        "their own street (Lindau Lane, Killebrew Drive, 24th Avenue South)."),
    ("bloomington_east", "The airport-adjacent American Blvd East / 34th Avenue South / East 78th-81st Street hotel "
                         "row (55425 / 55420) reports as the Bloomington East overlay."),
    ("bloomington_west", "Normandale Lake / American Blvd West (55437 / 55438 / 55439) reports as the Bloomington "
                         "West overlay."),
    ("one_premises_one_row", "A property is one row however many of 'airport', 'Mall of America', 'Bloomington' and "
                             "'Minneapolis' its marketing carries; identity is its own street address and brand "
                             "property code."),
])

#: The out-state / exurb ruling (consumers read it under the inherited name HILL_COUNTRY_RULING).
TWIN_CITIES_RULING = OrderedDict([
    ("classification", "The metro-continuous Twin Cities core is admitted -- the five Minneapolis and three St. Paul "
                       "corridors, MSP Airport and Bloomington / Mall of America CORE; Eagan, Richfield, Edina, Eden "
                       "Prairie, Minnetonka / Hopkins / Wayzata, Plymouth, Roseville, Maplewood / Oakdale and "
                       "Woodbury STRONG CORRIDOR; Brooklyn Center / Brooklyn Park, Maple Grove, Burnsville / Savage "
                       "/ Shakopee, Mendota Heights / West St. Paul / Inver Grove Heights and Golden Valley / St. "
                       "Louis Park FRINGE. Rochester, Duluth, St. Cloud, Mankato and Stillwater are OUTSIDE, and so "
                       "are the north metro beyond I-694, the outer south metro and the western exurbs."),
    ("a_marketing_phrase_admits_nothing", "'Minneapolis Airport', 'MSP Airport', 'Mall of America', 'Minneapolis "
                                          "West', 'Minneapolis North', 'Minneapolis South', 'St. Paul North', 'St. "
                                          "Paul East', 'St. Paul-Woodbury' and 'Minneapolis-St. Paul' are marketing. "
                                          "The property's own postal code decides."),
    ("actual_location", "Decided by the property's own postal code on its own page."),
    ("drive_market_relationship", "MSP, Bloomington / the Mall of America, the I-494 / I-694 ring suburbs and the "
                                  "two downtowns are where Twin Cities travellers sleep; Rochester (Mayo), Duluth, "
                                  "St. Cloud, Mankato and the St. Croix river towns are trips of their own."),
    ("traveller_intent", "Convention (Minneapolis Convention Center, RiverCentre), arena and stadium (Target Center, "
                         "U.S. Bank Stadium, Target Field, Xcel Energy Center, Allianz Field, Huntington Bank "
                         "Stadium), medical (Hennepin Healthcare, M Health Fairview, Regions, Children's), "
                         "university (University of Minnesota, St. Thomas, Macalester, Hamline), corporate (Target, "
                         "Best Buy, UnitedHealth, 3M, Ecolab, General Mills, Medtronic), Mall of America and MSP "
                         "demand is Twin Cities intent; Mayo Clinic, the North Shore and the St. Croix are not."),
    ("metro_continuity", "Continuous development runs inside the I-494 / I-694 ring and along its suburban "
                         "interchanges; this registry stops at the ring's outer suburbs named by the order."),
    ("corridor_support", "Every admitted edge code is in a named corridor so its count is visible and a founder can "
                         "move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE rochester-mn, duluth-mn, st-cloud-mn, mankato-mn and stillwater-st-croix."),
])
HILL_COUNTRY_RULING = TWIN_CITIES_RULING
#: Inherited consumer name (the Portland helper's cross-border evaluation slot): the Twin Cities' equivalent is the
#: MSP / Bloomington evaluation.
VANCOUVER_EVALUATION = MSP_BLOOMINGTON_EVALUATION

STRUCTURE_TEST = OrderedDict([
    ("A. Is the Twin Cities one market, or several?",
     "ONE market, minneapolis-mn, covering both central cities and the contiguous suburbs the order evaluates -- one "
     "commercial airport (MSP), one I-94 / I-35W / I-35E / I-494 / I-694 road system, one Metro Transit light-rail "
     "network (Blue and Green Lines)."),
    ("B. St. Paul is NOT flattened into Minneapolis",
     "Downtown St. Paul, the Midway and the St. Paul neighbourhoods are their own corridors with their own city; a "
     "St. Paul hotel is never stated as Minneapolis, and the reverse."),
    ("C. MSP", "Only the airport's own codes (55111 / 55450) are msp-airport; 'Airport' hotels elsewhere are placed "
               "by their own code (MSP_BLOOMINGTON_EVALUATION)."),
    ("D. Mall of America", "An overlay of bloomington-mall-of-america (55425)."),
    ("E. North Loop / Mill District / Lowertown / Cathedral Hill / West 7th", "Overlays of their downtown corridor, "
                                                                            "never split codes."),
    ("F. Rochester", "OUTSIDE -- FUTURE_STANDALONE rochester-mn."),
    ("G. Duluth", "OUTSIDE -- FUTURE_STANDALONE duluth-mn."),
    ("H. St. Cloud", "OUTSIDE -- FUTURE_STANDALONE st-cloud-mn."),
    ("I. Mankato", "OUTSIDE -- FUTURE_STANDALONE mankato-mn."),
    ("J. Stillwater", "OUTSIDE -- FUTURE_STANDALONE stillwater-st-croix."),
    ("K. North metro / western exurbs", "OUTSIDE -- not absorbed."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel operation."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP). A unit designator ('Ste', "
     "'Unit', '#', 'Apt', 'PH') in a registry address means the record is a UNIT INSIDE a building or campus, which "
     "is never a hotel identity."),
    ("hotel_vs_residence_boundary",
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. The Twin Cities' "
     "specific exposures: the North Loop / Mill District / Uptown apartment towers with furnished short-stay units, "
     "the serviced-apartment and aparthotel operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Lark, "
     "Barsala), corporate-housing portfolios, the University of Minnesota student housing, hotel-and-residences "
     "towers (the residences are never the hotel), Club Wyndham / WorldMark vacation-ownership inventory and the "
     "Airbnb / Vrbo inventory."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort (Club Wyndham, WorldMark, Hilton Grand Vacations, Marriott "
     "Vacation Club, Holiday Inn Club Vacations, Bluegreen, Diamond / Hilton Vacation Club, Hyatt Vacation Club, Shell "
     "Vacations) is TIMESHARE and is never admitted to hotel accounting, even when its brand lists it beside its "
     "hotels, even when it sells a nightly rate, and even when a pet-policy page exists (the Phoenix correction-003 "
     "lesson)."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared "
     "amenities or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never "
     "published as one. A hotel and its residences on one campus are distinct premises."),
    ("extended_stay",
     "Extended-stay hotels are hotels and are admitted on their own pages; an 'apartment hotel' or 'aparthotel' is "
     "admitted only as a public hotel operation at an exact premises, never as a residential building that rents "
     "furnished units."),
    ("patient_and_military_lodging",
     "Patient-family housing (the Ronald McDonald Houses, Hope Lodge, Gift of Life), charitable family lodging "
     "(Fisher House) and on-base military lodging are never public hotels and are never admitted."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("55401", ["North Loop", "Warehouse District", "Mill District (west)", "Downtown core (Hennepin)"]),
    ("55415", ["Downtown East", "Mill District (east)", "U.S. Bank Stadium"]),
    ("55403", ["Loring Park", "Convention Center", "Downtown core (south)"]),
    ("55101", ["Lowertown", "Downtown St. Paul (east)"]),
    ("55102", ["Rice Park", "Downtown St. Paul (west)", "Cathedral Hill", "West 7th"]),
    ("55425", ["Mall of America", "Bloomington East (airport-adjacent)", "South Loop"]),
    ("55439", ["Bloomington West", "Edina (south-west)"]),
    ("55120", ["Mendota Heights", "Eagan (north-east)", "Lilydale"]),
    ("55117", ["St. Paul North End", "Little Canada", "Maplewood (west)"]),
    ("55119", ["St. Paul Battle Creek", "Maplewood (south)"]),
    ("55416", ["St. Louis Park", "Golden Valley", "Minneapolis (Bryn Mawr edge)"]),
    ("55422", ["Golden Valley", "Robbinsdale", "Crystal"]),
    ("55427", ["Golden Valley", "Crystal", "New Hope"]),
    ("55428", ["Brooklyn Park", "Crystal", "New Hope"]),
    ("55369", ["Maple Grove", "Osseo"]),
    ("55343", ["Hopkins", "Minnetonka", "Edina (west)"]),
    ("55391", ["Wayzata", "Minnetonka (north)", "Orono"]),
    ("55108", ["St. Anthony Park", "Como", "Falcon Heights", "Lauderdale"]),
])

FUTURE_MARKETS = OrderedDict([
    ("rochester-mn", "Rochester / Mayo Clinic -- 80 miles south-east on US-52."),
    ("duluth-mn", "Duluth / the North Shore -- 150 miles north on I-35."),
    ("st-cloud-mn", "St. Cloud -- 65 miles north-west on I-94."),
    ("mankato-mn", "Mankato / North Mankato -- 80 miles south-west on US-169."),
    ("stillwater-st-croix", "Stillwater and the St. Croix Valley river towns -- 25 miles east."),
])

#: Markets that are ALREADY LIVE. None shares a state with this one. Exposures are shared NAMES only: Bloomington,
#: Indiana (indianapolis-in's region) is not Bloomington, MN; Richfield, Ohio sits in cleveland-akron-canton-oh's
#: region; Plymouth, Maple Grove, Woodbury and Eagan are names other states carry; Hudson, Wisconsin is outside.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("portland-or", "Portland / Greater Portland, live as production market #41 (deploy 6ac264b79e70ce6a7db4baaf) -- "
                    "the CURRENT LIVE market at this order's authoring time. No shared state, no shared postal code."),
    ("milwaukee-wi", "Milwaukee, live -- the nearest live market and the only Upper-Midwest one. It owns its own "
                     "Wisconsin 53xxx codes; every Wisconsin code is refused here by prefix."),
    ("cleveland-akron-canton-oh", "Cleveland / Akron / Canton, live -- its region contains a Richfield, OHIO; "
                                  "identity is decided by premises and state, never the town name."),
    ("indianapolis-in", "Indianapolis, live -- Bloomington, INDIANA is a different city; identity is decided by "
                        "premises and state, never the town name."),
])

#: A shared postal code whose OTHER town is refused. None at authoring time.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "minneapolis,": "minneapolis", "minneapolis mn": "minneapolis", "minneapolis, mn": "minneapolis", "mpls": "minneapolis",
    "saint paul": "st paul", "saint paul,": "st paul", "st paul,": "st paul", "st. paul": "st paul",
    "st paul mn": "st paul", "saint paul mn": "st paul", "st paul, mn": "st paul", "saint paul, mn": "st paul",
    "bloomington,": "bloomington", "eagan,": "eagan", "richfield,": "richfield", "edina,": "edina",
    "eden prairie,": "eden prairie", "minnetonka,": "minnetonka", "hopkins,": "hopkins", "wayzata,": "wayzata",
    "plymouth,": "plymouth", "roseville,": "roseville", "maplewood,": "maplewood", "oakdale,": "oakdale",
    "woodbury,": "woodbury", "brooklyn center,": "brooklyn center", "brooklyn park,": "brooklyn park",
    "maple grove,": "maple grove", "osseo,": "osseo", "burnsville,": "burnsville", "savage,": "savage",
    "shakopee,": "shakopee", "mendota heights,": "mendota heights", "west saint paul": "west st paul",
    "west st. paul": "west st paul", "south saint paul": "south st paul", "south st. paul": "south st paul",
    "inver grove heights,": "inver grove heights", "inver grove hts": "inver grove heights",
    "golden valley,": "golden valley", "saint louis park": "st louis park", "st. louis park": "st louis park",
    "st louis park,": "st louis park", "arden hills,": "arden hills", "new brighton,": "new brighton",
    "shoreview,": "shoreview", "fort snelling,": "fort snelling", "falcon heights,": "falcon heights",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("55402", "Downtown Minneapolis core -- Nicollet Mall and the skyway hotel row."),
    ("55401", "North Loop / Warehouse District / Mill District -- overlays of downtown, never split."),
    ("55403", "Loring Park and the Minneapolis Convention Center."),
    ("55101", "Lowertown -- downtown St. Paul east."),
    ("55102", "Rice Park / Xcel Energy Center / Cathedral Hill / West 7th -- downtown St. Paul west."),
    ("55425", "Mall of America and the airport-adjacent Bloomington East hotel row."),
    ("55111", "MSP Airport / Fort Snelling -- the only airport-property code."),
    ("55901", "Rochester -- refused (rochester-mn)."),
])


def _registered_market_postal_codes():
    """Every postal code a REGISTERED market's own document admits (read only), keyed by code."""
    codes = {}
    for path in sorted(glob.glob(REGISTERED_MARKETS_GLOB)):
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        for c in doc.get("corridors", []) or []:
            for z in c.get("included_postal_codes", []) or []:
                codes[z] = doc.get("market_id") or os.path.basename(path)[:-5]
    return codes


def build():
    corridors = []
    seen_zip = {}
    for order, (slug, name, area, klass, _muni, zips, desc, state) in enumerate(CORRIDORS, start=1):
        for z in zips:
            if z in seen_zip:
                raise SystemExit("postal code %s claimed by both %s and %s -- the corridor registry must be a "
                                 "partition" % (z, seen_zip[z], slug))
            if state_for_postal(z) != state:
                raise SystemExit("postal code %s (%s) sits in corridor %s stated as %s" % (
                    z, state_for_postal(z), slug, state))
            seen_zip[z] = slug
        corridors.append(OrderedDict([
            ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
            ("market_id", MARKET_ID),
            ("name", name),
            ("slug", slug),
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Twin Cities" % name),
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
            ("state_code", state),
            ("geography_class", klass),
        ]))
    outside_zips = {z for _m, _s, zs, _w in OUTSIDE for z in zs}
    overlap = outside_zips & set(seen_zip)
    if overlap:
        raise SystemExit("postal codes both admitted and refused: %s" % sorted(overlap))
    prefix_overlap = [z for z in seen_zip if any(z.startswith(p) for p, _n, _f in OUTSIDE_PREFIXES)]
    if prefix_overlap:
        raise SystemExit("admitted postal codes under a refused prefix: %s" % sorted(prefix_overlap))
    stray = [z for z in seen_zip if not z.startswith(VALLEY_PREFIXES)]
    if stray:
        raise SystemExit("admitted postal codes outside the Twin Cities prefixes: %s" % stray)
    registered_codes = _registered_market_postal_codes()
    live_overlap = sorted(z for z in seen_zip if z in registered_codes)
    if live_overlap:
        raise SystemExit("admitted postal codes a REGISTERED market already admits: %s" % [
            (z, registered_codes[z]) for z in live_overlap])
    military_unclaimed = [z for z in MILITARY_POSTAL_CODES if z not in seen_zip]
    if military_unclaimed:
        raise SystemExit("military postal codes claimed by no corridor: %s" % military_unclaimed)

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
        ("state_code", STATE_CODE),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Minneapolis / St. Paul / Twin Cities downtown, convention, stadium, medical, university, "
                        "corporate, MSP airport, Mall of America and I-494 / I-694 suburban lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("country", "US"),
        ("market_center", {"lat": 44.96, "lng": -93.20}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past Rochester and Mankato, north to "
             "Duluth and west past St. Cloud, so that " + WORK_ORDER + " classifies those properties on evidence "
             "instead of being blind to them. Admission is decided by the corridor registry over the property's "
             "OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Minneapolis / St. Paul / Twin Cities is ONE two-city market: ten CORE corridors (downtown "
         "Minneapolis, University / Dinkytown, Uptown / South Minneapolis, Northeast, North Minneapolis, downtown St. "
         "Paul, the Midway, the St. Paul neighbourhoods, MSP Airport, Bloomington / Mall of America), nine STRONG "
         "CORRIDORS (Eagan, Richfield, Edina, Eden Prairie, Minnetonka / Hopkins / Wayzata, Plymouth, Roseville, "
         "Maplewood / Oakdale, Woodbury) and five FRINGE corridors (Brooklyn Center / Brooklyn Park, Maple Grove, "
         "Burnsville / Savage / Shakopee, Mendota Heights / West St. Paul / Inver Grove Heights, Golden Valley / St. "
         "Louis Park). ROCHESTER, DULUTH, ST. CLOUD, MANKATO and STILLWATER are refused as future standalone markets; "
         "the north metro beyond I-694, the outer south metro, the western exurbs and Wisconsin are refused by name. "
         "Patient, charitable and on-base lodging is never admitted."),
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
        ("market_name", "Minneapolis / St. Paul, Minnesota"),
        ("market_slug", MARKET_ID),
        ("state_name", "Minnesota"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("primary_city", "Minneapolis"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Minneapolis / St. Paul, Minnesota | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across the Twin Cities -- downtown Minneapolis, downtown St. Paul, the "
         "University, MSP airport, Bloomington and the Mall of America, Eagan, Edina, Eden Prairie, Plymouth, "
         "Roseville and Woodbury -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Minneapolis / St. Paul"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry. A Minneapolis / St. Paul two-city downtown, convention, "
         "stadium, medical, university, corporate, MSP airport, Mall of America and suburban travel market -- both "
         "central cities and the contiguous I-494 / I-694 suburbs the order evaluates. Not 'Minnesota': Rochester, "
         "Duluth, St. Cloud, Mankato and Stillwater are future standalone markets; the north metro beyond I-694, the "
         "outer south metro, the western exurbs and Wisconsin are refused. Nothing else admits a property: not a "
         "brand's 'Minneapolis' or 'St. Paul' marketing name, not a map pin, not a vacation-rental listing, not a "
         "competitor directory's city label. Patient, charitable and on-base lodging is never admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). The postal city "
         "'MINNEAPOLIS' also covers Bloomington, Richfield, Edina and Golden Valley codes and places nothing by "
         "itself; 'ST PAUL' covers Roseville, Maplewood, Woodbury and Eagan codes. Shared codes are covered whole: "
         "55401 by the North Loop, Warehouse District and Mill District; 55102 by Rice Park, Cathedral Hill and West "
         "7th; 55425 by the Mall of America and Bloomington East; 55439 by Bloomington West and south-west Edina; "
         "55120 by Mendota Heights and north-east Eagan. North Loop, Mill District, Lowertown, Rice Park, Cathedral "
         "Hill, West 7th, Mall of America, Bloomington East and Bloomington West are overlays."),
        ("_census_membership_note",
         "Individual condominium units, private residences, vacation homes, property-management and corporate-housing "
         "portfolios, serviced-apartment operators, Airbnb / Vrbo inventory, ordinary apartments, student housing, "
         "timeshare and vacation-club inventory, residential-only towers, privately managed residences inside hotel "
         "towers, member-only club lodging and on-base military / government lodging are never admitted. A mixed "
         "hotel / condo / residence property is admitted only as the exact hotel premises its public operator sells "
         "as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 + 6 -- Minneapolis / St. Paul / Twin Cities two-city travel-market geography, the "
                  "Minneapolis / St. Paul identity trap, the MSP / Bloomington / Mall of America boundary, the "
                  "residence / apartment / vacation-rental rule and the timeshare rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/minneapolis-mn.json. This "
         "order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its brand's own property card states it, "
         "joined to the corridor registry. Nothing else admits a property."),
        ("two_city_rule",
         "Minneapolis and St. Paul are both central cities with their own corridors; neither is flattened into the "
         "other, and every row states the city its own premises are in."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG_CORRIDOR is registry class CORRIDOR; FUTURE_STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes and by postal PREFIX for the "
                          "refused regions; the future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("msp_bloomington_evaluation", MSP_BLOOMINGTON_EVALUATION),
        ("twin_cities_ruling", TWIN_CITIES_RULING),
        ("metro_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("military_lodging_rule", OrderedDict([
            ("rule", "On-base military / government lodging is MILITARY_RESTRICTED and never admitted: restricted "
                     "eligibility (DoD ID or sponsorship), on-base premises behind a gate, ordinary public-hotel "
                     "contract NOT satisfied. The Joint Air Reserve Station / 133rd Airlift Wing at MSP sell no "
                     "public lodging; the on-base names are refused wherever they appear."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "The Twin Cities was selected as a high-value PetTripFinder market for its two downtowns, convention and "
         "stadium demand, medical and university travel, corporate travel, the Mall of America, extended-stay demand "
         "and MSP airport traffic. That lowers NO evidence standard: pet acceptance is never inferred from a city's "
         "reputation. It shapes only the CENSUS: every tourist, convention, stadium, medical, university, corporate, "
         "airport and extended-stay lodging cluster is covered by an admitting corridor."),
        ("the_minneapolis_st_paul_name_trap",
         "The chains put 'Minneapolis' on hotels in Bloomington, Eagan, Edina, Eden Prairie, Plymouth, Maple Grove, "
         "Brooklyn Park and Burnsville, and 'St. Paul' on hotels in Roseville, Maplewood, Woodbury, Oakdale, "
         "Shoreview, Mendota Heights and Eagan. A property's own postal code, street and brand property code decide "
         "what and where it is; none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Minneapolis-St. Paul International Airport (MSP)", "msp-airport (55111 / 55450); airport-marketed "
                                                                 "hotels placed by their own codes."),
            ("Mall of America", "bloomington-mall-of-america (55425) -- overlay."),
            ("Minneapolis Convention Center", "downtown-minneapolis (55403) -- overlay."),
            ("U.S. Bank Stadium / Target Field / Target Center", "downtown-minneapolis (55415 / 55403 / 55401)."),
            ("University of Minnesota", "university-dinkytown (55414 / 55454 / 55455)."),
            ("Xcel Energy Center / RiverCentre", "downtown-st-paul (55102) -- overlay."),
            ("Allianz Field", "st-paul-midway (55104)."),
            ("Minnesota State Fairgrounds", "st-paul-midway (55108)."),
            ("Southdale / Galleria", "edina (55435)."),
            ("Rosedale Center", "roseville (55113)."),
            ("Canterbury Park / Valleyfair", "burnsville-shakopee (55379)."),
        ])),
        ("evaluated_inclusions", EVALUATED_INCLUSIONS),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_postal_codes_by_state", OrderedDict(
            (s, sorted(z for z in seen_zip if state_for_postal(z) == s)) for s in STATE_CODES)),
        ("admitted_counties", sorted(ADMITTED_COUNTIES)),
        ("observed_outside_counties", OBSERVED_COUNTIES),
        ("outside_prefixes", [OrderedDict([("prefix", p), ("area", n), ("future_market", f)])
                              for p, n, f in OUTSIDE_PREFIXES]),
        ("shared_postal_codes", SHARED_POSTAL_CODES),
        ("registered_market_postal_codes_checked", len(registered_codes)),
        ("no_live_market_postal_code_admitted", not live_overlap),
        ("first_minnesota_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("state_code", c["state_code"]), ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, stadium, convention or "
         "mall keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration order "
         "publishes it."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, public resorts, qualifying condo-hotels with a distinct public hotel "
         "operation, qualifying extended-stay hotels and other public lodging establishments: bookable nightly rooms or "
         "suites sold to the public under one establishment name, with an official property page and an on-site hotel "
         "operation. It NEVER admits: individual condominium units; vacation homes sold by owners or managers; "
         "property-management / corporate-housing / short-term-rental portfolios; serviced-apartment operators; Airbnb "
         "/ Vrbo listings; ordinary apartments; student housing; timeshare and vacation-club inventory; "
         "residential-only towers; privately managed residences; member-only club lodging; on-base military / "
         "government lodging; and privately managed units inside hotel-condo towers. Campgrounds, RV parks and hostels "
         "are NON_LODGING."),
        ("shared_campus_rule",
         "Never merged solely by display name, brand, owner, phone, shared address, campus, booking engine, shared "
         "amenities or shared entrance. Exact premises identity (its own street address or its own brand property "
         "code on its own page) governs. A dual-brand building is TWO hotels and is HELD for the split."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


def military_postal(postal):
    """The base a postal code belongs to, or ""."""
    return MILITARY_POSTAL_CODES.get((postal or "").strip()[:5], "")


def nonpublic_reason(name):
    """The MILITARY_RESTRICTED / charitable reason a lodging NAME carries, or ""."""
    n = " ".join(re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split())
    for key, why in NONPUBLIC_NAMES.items():
        if key in n:
            return why
    return ""


def corridor_municipality():
    return {c[0]: c[4] for c in CORRIDORS}


def corridor_class(slug):
    return {c[0]: c[3] for c in CORRIDORS}.get(slug)


def corridor_state(slug):
    return {c[0]: c[7] for c in CORRIDORS}.get(slug)


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


def route_overlay(corridor_slug, street, lat, lng, postal=""):
    """The order's named submarket a census row reports under: its own street first, then its pin, then the
    corridor's own name. Reporting only."""
    text = "%s %s" % (street or "", postal or "")
    for name, rx in STREET_OVERLAYS:
        if rx.search(text):
            return name
    area = coverage_area(lat, lng)
    if area:
        return area
    return CORRIDOR_DEFAULT_OVERLAY.get(corridor_slug)


def normalise_municipality(city):
    muni = " ".join((city or "").lower().replace(".", " ").split())
    muni = muni.replace(" ,", ",")
    if muni in MUNICIPALITY_SPELLINGS:
        return MUNICIPALITY_SPELLINGS[muni]
    key2 = muni.rstrip(",")
    return MUNICIPALITY_SPELLINGS.get(key2, key2)


def future_market_for(postal):
    """The market id a refused postal code is preserved for (future standalone OR existing live), or ""."""
    z = (postal or "").strip()[:5]
    for _name, _s, zs, why in OUTSIDE:
        if z in zs:
            for fid in list(EXISTING_LIVE_MARKETS) + list(FUTURE_MARKETS):
                if fid in why:
                    return fid
    for prefix, _n, fid in OUTSIDE_PREFIXES:
        if z.startswith(prefix):
            return fid
    return ""


def classify_postal(postal, municipality=""):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and municipality. The one
    membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = normalise_municipality(municipality)
    for slug, _name, _area, klass, _m, zips, _desc, _state in CORRIDORS:
        if z in zips:
            for rz, rmuni, why in MUNICIPALITY_REFUSALS:
                if rz == z and rmuni.lower() == muni:
                    return "OUTSIDE", None, why
            return klass, slug, "postal code %s -> %s" % (z, slug)
    for name, _s, zs, why in OUTSIDE:
        if z in zs:
            return "OUTSIDE", None, "%s: %s" % (name, why)
    for prefix, name, fid in OUTSIDE_PREFIXES:
        if z.startswith(prefix):
            return "OUTSIDE", None, "postal prefix %s is %s%s" % (
                prefix, name, (" (FUTURE_STANDALONE %s)" % fid) if fid else "")
    if z.startswith(VALLEY_PREFIXES):
        return "OUTSIDE", None, "Twin Cities-region postal code %r is claimed by no corridor" % z
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
                          (REGISTRY_OUT, OrderedDict([("schema", "ptf-corridor-registry/1.0"),
                                                      ("work_order", WORK_ORDER),
                                                      ("market_id", MARKET_ID), ("corridors", corridors)]))):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, indent=1, ensure_ascii=False)
                fh.write("\n")
            print("WROTE", os.path.relpath(path, _DASH))
    print("corridors=%d  admitted_zips=%d  cells=%d (admitting %d, observation %d)" % (
        report["corridor_count"], report["admitted_postal_code_count"], report["cells_total"],
        report["cells_admitting"], report["cells_observation_only"]))
    print("by class:", json.dumps(report["corridor_count_by_class"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
