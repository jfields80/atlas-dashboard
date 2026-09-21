"""PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001 -- Phases 3, 4, 5 and 6: the Greater Fort Lauderdale market.

Built from zero on the repaired release-factory lineage (0b6ad264; current verified live = Miami deploy
6ab071a5b7561c33aff6c17b, source fbaf6f73, 31 markets / 2290 profiles / 2614 routes). No earlier Fort Lauderdale
build exists. Miami's build is read for DISCOVERY INTELLIGENCE only (Phase 2); no Miami census row, policy fact or
evidence row is imported as authority.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Greater Fort Lauderdale / Broward County traveller lodging market, stated as an explicit
CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE and EXISTING_LIVE markets named inside OUTSIDE)
before a single hotel is admitted, so no property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
-------------------
Membership is decided by the property's OWN postal code, as its own official page (or the Florida DBPR
public-lodging licence, the state's own record of the licensed premises) states it, joined to the corridor
registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing name never admits and
never places a property: a hotel whose own address states Dania Beach 33004 is a Dania Beach hotel however loudly
it calls itself "Fort Lauderdale Airport", and a hotel whose own address states Aventura 33180 is a Miami-Dade
hotel that belongs to the LIVE miami-fl market, not to this one.

WHY BROWARD'S ZIP CODES STRADDLE MUNICIPALITIES, AND WHAT THAT MEANS
--------------------------------------------------------------------
Broward County is unusually fragmented: 31 municipalities share postal codes freely. The Florida DBPR registry
(the state's own record, read in fort_lauderdale_fl_dbpr_lane_001) shows the seams directly --
33308 carries Fort Lauderdale's Galt Ocean Mile AND Lauderdale-by-the-Sea AND Sea Ranch Lakes; 33305 / 33311 /
33334 each carry Fort Lauderdale AND Wilton Manors; 33306 / 33309 / 33334 each carry Oakland Park; 33064 carries
Lighthouse Point AND Pompano Beach AND Deerfield Beach; 33312 carries Fort Lauderdale AND Dania Beach.
A corridor therefore covers a SHARED postal code as a whole and reports its named places as STREET-AND-PIN
OVERLAYS. It never splits a ZIP, because a split ZIP is a judgement call applied per property, which is exactly
what this registry exists to forbid.

THE STRUCTURE TEST (PHASE 4) IS RECORDED IN THE REPORT
-------------------------------------------------------
Greater Fort Lauderdale is ONE market (fort-lauderdale-fl): one county (Broward), one airport (FLL), one cruise
port (Port Everglades), one CVB (Visit Lauderdale, which markets all 31 Broward municipalities together).
Hollywood, Hollywood Beach and Hallandale Beach are INSIDE it -- they are Broward, they are Visit Lauderdale
territory, and their traveller flow is the FLL / Port Everglades flow -- but they keep DISTINCT traveller
identities and are never folded into generic Fort Lauderdale. Hollywood Beach (33019) is the single densest
lodging postal code in the county and is its own CORE corridor.

THE CRUISE TEST (PHASE 5)
-------------------------
Unlike PortMiami (Dodge Island, which carries terminals and no hotels), PORT EVERGLADES SITS INSIDE A POSTAL CODE
THAT IS FULL OF HOTELS. ZIP 33316 carries the port's own gates, the 17th Street Causeway hotel wall (Embassy
Suites, Hilton Fort Lauderdale Marina, Pier Sixty-Six, Omni, Hyatt Place Cruise Port, Holiday Inn Express Cruise
Port), the Broward County Convention Center, Harbor Beach (Marriott Harbor Beach, Lago Mar) and the Bahia Mar /
Seabreeze Boulevard south beach strip. That is a coherent cruise + convention + marina traveller system on its
OWN postal code, claimed by no other corridor, so a dedicated corridor IS created -- not as an SEO split and not
as a duplicate of downtown or the beach, but because the postal partition hands it its own inventory. It is named
for what it is (Port Everglades / 17th Street / Harbor Beach), and cruise relevance never altered one premises
identity.

FLL AIRPORT SPLITS ON A REAL SEAM
----------------------------------
The FLL hotel district is not one postal code. Its south side -- Stirling Road, SW 18th Avenue / SW 19th Court,
North Compass Way, Griffin Road east -- is Dania Beach 33004; its north and west side -- State Road 84 / Marina
Mile, Maritime Boulevard, Griffin Road west, Anglers Avenue -- is 33312 / 33315. Two corridors on that real seam,
with "Fort Lauderdale-Hollywood International Airport (FLL)" reported as a street-and-pin overlay across both.
No corridor is created for "FLL Airport" as such, because it owns no postal code of its own.

VACATION RENTALS, CONDO-HOTELS, TIMESHARES AND RESORT RESIDENCES
-----------------------------------------------------------------
Florida DBPR licenses every condominium unit (CNDO) and vacation dwelling (DWEL) as public lodging; Broward
carries 4,569 CNDO and 6,234 DWEL licences against just 427 hotel / motel / B&B licences. None is a hotel identity
and none enters the graph. A mixed hotel / condo / branded-residence tower (Hollywood Beach's S Ocean Drive,
Fort Lauderdale Beach Boulevard, Galt Ocean Mile) is admitted ONLY as the exact hotel premises its public hotel
operator sells as a hotel, proved on the operator's own page and on the licence's exact premises (a DBPR HOTL
licence at that street, not a CNDO rental programme).

Nothing here fetches, spends or deploys. The market document goes to the registry's markets/<id>.json, as every
registered market's does.

Outputs:
  scripts/pettripfinder/discovery/config/fort_lauderdale_fl.json
  launch_packages/pettripfinder/markets/fort-lauderdale-fl.json
  launch_packages/pettripfinder/markets/reports/fort_lauderdale_fl_geography_001.json
  launch_packages/pettripfinder/markets/reports/fort_lauderdale_fl_corridor_registry_001.json
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

WORK_ORDER = "PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "fort-lauderdale-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "fort_lauderdale_fl.json")
#: REGISTERED by PTF-FORT-LAUDERDALE-FL-REGISTRATION-AND-STAGING-002: the market document is written to the
#: registry's markets/<id>.json. The source-ready order's markets/proposed/ copy is history.
SHARD_OUT = os.path.join(PKG, "markets", "fort-lauderdale-fl.json")
REPORT_OUT = os.path.join(REPORTS, "fort_lauderdale_fl_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "fort_lauderdale_fl_corridor_registry_001.json")
AS_OF = "2026-09-20"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown-las-olas", "Downtown Fort Lauderdale / Las Olas", "Downtown & Las Olas", "CORE", "fort lauderdale",
     ["33301"],
     "Downtown Fort Lauderdale: Las Olas Boulevard from Andrews Avenue to the Intracoastal, the Riverwalk and New "
     "River, Flagler Village, the Broward Center for the Performing Arts and the Federal Highway / Andrews Avenue "
     "hotel blocks. Las Olas runs east from here to the beach, but the beach end is its own postal code."),
    ("fort-lauderdale-beach", "Fort Lauderdale Beach", "Fort Lauderdale Beach", "CORE", "fort lauderdale",
     ["33304"],
     "The Fort Lauderdale beachfront: North Fort Lauderdale Beach Boulevard (A1A) from Las Olas north past Sunrise "
     "Boulevard to Hugh Taylor Birch State Park, the North Birch Road / Breakers Avenue / Bayshore Drive guesthouse "
     "district, and Sunrise Boulevard's Galleria blocks. Victoria Park, inland on the same postal code, is reported "
     "as an overlay."),
    ("port-everglades-17th-street", "Port Everglades / 17th Street Causeway / Harbor Beach",
     "Port Everglades & 17th Street", "CORE", "fort lauderdale",
     ["33316"],
     "The cruise, convention and marina system on its own postal code: Port Everglades' terminals, the Southeast "
     "17th Street Causeway hotel wall, the Broward County Convention Center, Harbor Beach and Holiday Drive, the "
     "Bahia Mar / Seabreeze Boulevard south beach strip, Lauderdale Harbours and Rio Vista."),
    ("fll-airport-sr84", "Fort Lauderdale-Hollywood International Airport (FLL) north / State Road 84",
     "FLL Airport & SR-84", "CORE", "fort lauderdale",
     ["33312", "33315"],
     "The north and west sides of Fort Lauderdale-Hollywood International Airport: the State Road 84 / Marina Mile "
     "hotel strip, Maritime Boulevard, the western Griffin Road and Anglers Avenue blocks, Riverland and the "
     "Southwest 12th Avenue cruise-port approach. The airport's south-side hotel cluster is Dania Beach 33004."),
    ("dania-beach", "Dania Beach", "Dania Beach", "CORE", "dania beach",
     ["33004"],
     "Dania Beach: the Fort Lauderdale-Hollywood International Airport south-side hotel cluster on Stirling Road, "
     "Southwest 18th Avenue / 19th Court, North Compass Way and eastern Griffin Road; Dania Beach's own Federal "
     "Highway motel row, its antique-district downtown, Dania Beach Boulevard and the Dania Beach pier."),
    ("hollywood-beach", "Hollywood Beach", "Hollywood Beach", "CORE", "hollywood",
     ["33019"],
     "Hollywood Beach: the Broadwalk, North and South Ocean Drive, Surf Road and the lettered / presidential beach "
     "streets, north to Hollywood North Beach Park and south past the Diplomat and Hollywood's South Ocean Drive "
     "resort towers. The densest lodging postal code in Broward County."),
    ("hollywood", "Hollywood", "Hollywood", "CORE", "hollywood",
     ["33020", "33021", "33024"],
     "Hollywood off the beach: downtown Hollywood and ArtsPark at Young Circle, Hollywood Boulevard, the Federal "
     "Highway and Dixie Highway corridors, Hollywood Hills, Emerald Hills and the Sheridan Street / Interstate 95 "
     "blocks, and Hollywood's western neighbourhoods toward Pembroke Road."),
    ("plantation-davie", "Plantation / Davie / Cooper City", "Plantation & Davie", "CORE", "plantation",
     ["33314", "33317", "33324", "33325", "33328"],
     "The western business and university corridor: Plantation's Broward Boulevard and Pine Island Road office "
     "parks and Plantation Midtown, Davie's Nova Southeastern University and the South Florida Education Center, "
     "Griffin Road west, Cooper City and the Interstate 595 / Fort Lauderdale Executive corridor."),
    ("hallandale-beach", "Hallandale Beach", "Hallandale Beach", "CORE", "hallandale beach",
     ["33009"],
     "Hallandale Beach: Gulfstream Park, the Village at Gulfstream, Hallandale Beach Boulevard, South Ocean Drive's "
     "oceanfront towers and the Diplomat Golf district -- Broward County's southernmost municipality, immediately "
     "north of the Miami-Dade line at Aventura."),

    ("galt-ocean-lauderdale-by-the-sea", "Galt Ocean Mile / Lauderdale-by-the-Sea",
     "Galt Ocean Mile & Lauderdale-by-the-Sea", "CORRIDOR", "fort lauderdale",
     ["33308"],
     "The beach strip north of Birch State Park on one shared postal code: Fort Lauderdale's Galt Ocean Mile and "
     "North Ocean Boulevard, Lauderdale-by-the-Sea's El Mar Drive / Commercial Boulevard pier village, Sea Ranch "
     "Lakes, Coral Ridge and the Intracoastal blocks along Northeast 32nd Avenue. Fort Lauderdale, "
     "Lauderdale-by-the-Sea and Sea Ranch Lakes all use 33308; each is reported as an overlay."),
    ("oakland-park-wilton-manors", "Oakland Park / Wilton Manors / Coral Ridge", "Oakland Park & Wilton Manors",
     "CORRIDOR", "oakland park",
     ["33305", "33306", "33334"],
     "The near-north neighbourhoods between downtown and the Galt: Wilton Manors and Wilton Drive, Oakland Park's "
     "Dixie Highway arts district and Oakland Park Boulevard, Coral Ridge, Bayview and Middle River Terrace. Fort "
     "Lauderdale, Wilton Manors and Oakland Park share all three of these postal codes; each is an overlay."),
    ("cypress-creek", "Cypress Creek / Northwest Fort Lauderdale", "Cypress Creek", "CORRIDOR", "fort lauderdale",
     ["33309", "33311"],
     "The Cypress Creek Road office and hotel corridor at Interstate 95 and Executive Airport, Commercial Boulevard "
     "west, Powerline Road, and northwest Fort Lauderdale's Sistrunk Boulevard and Lauderdale Lakes edges. Oakland "
     "Park, Lauderdale Lakes and Wilton Manors share these postal codes with Fort Lauderdale."),
    ("pompano-beach", "Pompano Beach / Lighthouse Point / Hillsboro Beach", "Pompano Beach", "CORRIDOR",
     "pompano beach",
     ["33060", "33062", "33064", "33069"],
     "Pompano Beach: the Pompano Beach Pier and its A1A / North and South Ocean Boulevard hotel row, Atlantic "
     "Boulevard, Briny Avenue, the Hillsboro Mile north to Hillsboro Inlet, Lighthouse Point, and the Powerline "
     "Road / Copans Road commercial blocks west of Interstate 95."),
    ("deerfield-beach", "Deerfield Beach", "Deerfield Beach", "CORRIDOR", "deerfield beach",
     ["33441", "33442"],
     "Deerfield Beach: the Deerfield Beach International Fishing Pier, Northeast 21st Avenue and the A1A oceanfront, "
     "Hillsboro Boulevard, the Cove, and the Interstate 95 / Southwest 10th Street commercial corridor at Broward "
     "County's northern boundary with Palm Beach County."),

    ("sunrise-tamarac-lauderhill", "Sunrise / Tamarac / Lauderhill", "Sunrise & Tamarac", "FRINGE", "sunrise",
     ["33313", "33319", "33321", "33322", "33323", "33351"],
     "Sunrise's Sawgrass Mills and the Amerant Bank Arena, the Sawgrass Corporate Park and Sunrise Boulevard west, "
     "Tamarac, Lauderhill, Lauderdale Lakes and North Lauderdale's eastern edge; careful evaluation, admitted at "
     "FRINGE density."),
    ("weston-southwest-ranches", "Weston / Southwest Ranches", "Weston", "FRINGE", "weston",
     ["33326", "33327", "33330", "33331", "33332"],
     "Weston's Indian Trace and Bonaventure, the Arvida Parkway Center, and Southwest Ranches' equestrian "
     "acreage west of Interstate 75 -- the western edge of developed Broward against the Everglades Water "
     "Conservation Areas; careful evaluation, admitted at FRINGE density. Weston's postal codes are still "
     "addressed 'Fort Lauderdale' by USPS, which never places a property on its own."),
    ("pembroke-pines-miramar", "Pembroke Pines / Miramar / West Park", "Pembroke Pines & Miramar", "FRINGE",
     "pembroke pines",
     ["33023", "33025", "33026", "33027", "33028", "33029"],
     "South-central Broward: Pembroke Pines along Pines Boulevard and the Shops at Pembroke Gardens, Miramar's "
     "Red Road, Miramar Parkway and the Miramar Town Center, and West Park; careful evaluation, admitted at FRINGE "
     "density."),
    ("coral-springs-coconut-creek", "Coral Springs / Coconut Creek / Margate / Parkland",
     "Coral Springs & Coconut Creek", "FRINGE", "coral springs",
     ["33063", "33065", "33066", "33067", "33068", "33071", "33073", "33076"],
     "Northwest Broward: Coral Springs along University Drive and Sample Road, Coconut Creek's Promenade and the "
     "Seminole Casino Coconut Creek, Margate, North Lauderdale and Parkland; careful evaluation, admitted at "
     "FRINGE density."),
]

#: Municipalities OUTSIDE the admitted market, each with the reason. A row names the market it is preserved for.
OUTSIDE = [
    ("Miami / Miami Beach / Greater Miami-Dade", "FL",
     ["33101", "33109", "33122", "33125", "33126", "33127", "33128", "33129", "33130", "33131", "33132", "33133",
      "33134", "33135", "33136", "33137", "33138", "33139", "33140", "33141", "33142", "33143", "33144", "33145",
      "33146", "33147", "33149", "33150", "33154", "33155", "33156", "33157", "33158", "33160", "33161", "33162",
      "33165", "33166", "33167", "33168", "33169", "33170", "33172", "33173", "33174", "33175", "33176", "33177",
      "33178", "33179", "33180", "33181", "33182", "33183", "33184", "33185", "33186", "33187", "33189", "33190",
      "33193", "33194", "33196", "33010", "33012", "33013", "33014", "33015", "33016", "33018", "33030", "33031",
      "33032", "33033", "33034", "33035", "33039", "33054", "33055", "33056"],
     "Miami-Dade County; EXISTING_LIVE_MARKET miami-fl (live as market #31). Aventura, Sunny Isles Beach, North "
     "Miami Beach and Golden Beach sit directly against Hallandale Beach at the county line and are refused by "
     "that line, not by distance."),
    ("Boca Raton", "FL", ["33427", "33428", "33429", "33431", "33432", "33433", "33434", "33486", "33487", "33488",
                          "33496", "33498"],
     "Palm Beach County; FUTURE_STANDALONE west-palm-beach-fl; refused by name (order). Boca Raton adjoins "
     "Deerfield Beach across the county line and is refused by that line."),
    ("Delray Beach", "FL", ["33444", "33445", "33446", "33482", "33483", "33484"],
     "Palm Beach County; FUTURE_STANDALONE west-palm-beach-fl; refused by name (order)."),
    ("Boynton Beach", "FL", ["33424", "33425", "33426", "33435", "33436", "33437", "33472", "33473", "33474"],
     "Palm Beach County; FUTURE_STANDALONE west-palm-beach-fl; refused by name (order)."),
    ("West Palm Beach / Palm Beach / Palm Beach Gardens / Jupiter", "FL",
     ["33401", "33402", "33403", "33404", "33405", "33406", "33407", "33408", "33409", "33410", "33411", "33412",
      "33413", "33414", "33415", "33417", "33418", "33419", "33420", "33421", "33458", "33460", "33461", "33462",
      "33463", "33465", "33467", "33469", "33477", "33478", "33480"],
     "Palm Beach County; FUTURE_STANDALONE west-palm-beach-fl; refused by name (order)."),
    ("Florida Keys (Key Largo / Islamorada / Marathon / Key West)", "FL",
     ["33036", "33037", "33040", "33041", "33042", "33043", "33044", "33045", "33050", "33051", "33052", "33070"],
     "Monroe County; FUTURE_STANDALONE florida-keys-fl; refused by name (order)."),
]

#: County-level boundary for the registry lane (DBPR states each licence's county). Broward is the only county
#: the admitted corridors touch; every other county row is OUTSIDE by county before any ZIP lookup.
ADMITTED_COUNTIES = {"broward"}
OBSERVED_COUNTIES = OrderedDict([
    ("dade", "miami-fl"), ("miami-dade", "miami-fl"), ("palm beach", "west-palm-beach-fl"),
    ("monroe", "florida-keys-fl"),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government).
NONPUBLIC_NAMES = {}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-las-olas", "Fort Lauderdale", "Downtown Fort Lauderdale / Las Olas", 26.1200, -80.1420, 2200, True),
    ("fort-lauderdale-beach", "Fort Lauderdale", "Fort Lauderdale Beach", 26.1310, -80.1050, 2600, True),
    ("port-everglades-17th-street", "Fort Lauderdale", "Port Everglades / 17th Street / Harbor Beach",
     26.0980, -80.1180, 2800, True),
    ("fll-airport-sr84", "Fort Lauderdale", "FLL Airport north / State Road 84", 26.0900, -80.1650, 4000, True),
    ("dania-beach", "Dania Beach", "Dania Beach / FLL south side", 26.0550, -80.1500, 3400, True),
    ("hollywood-beach", "Hollywood", "Hollywood Beach", 26.0170, -80.1170, 3600, True),
    ("hollywood", "Hollywood", "Hollywood", 26.0180, -80.1650, 4500, True),
    ("plantation-davie", "Plantation", "Plantation / Davie / Cooper City", 26.0800, -80.2400, 6500, True),
    ("hallandale-beach", "Hallandale Beach", "Hallandale Beach", 25.9850, -80.1330, 2600, True),
    ("galt-ocean-lauderdale-by-the-sea", "Fort Lauderdale", "Galt Ocean Mile / Lauderdale-by-the-Sea",
     26.1700, -80.0980, 3200, True),
    ("oakland-park-wilton-manors", "Oakland Park", "Oakland Park / Wilton Manors / Coral Ridge",
     26.1660, -80.1330, 3400, True),
    ("cypress-creek", "Fort Lauderdale", "Cypress Creek / Northwest Fort Lauderdale", 26.1900, -80.1750, 4200, True),
    ("pompano-beach", "Pompano Beach", "Pompano Beach / Lighthouse Point", 26.2400, -80.1000, 5000, True),
    ("deerfield-beach", "Deerfield Beach", "Deerfield Beach", 26.3180, -80.0950, 4000, True),
    ("sunrise-tamarac-lauderhill", "Sunrise", "Sunrise / Tamarac / Lauderhill", 26.1700, -80.2700, 7000, True),
    ("weston-southwest-ranches", "Weston", "Weston / Southwest Ranches", 26.1000, -80.3800, 6500, True),
    ("pembroke-pines-miramar", "Pembroke Pines", "Pembroke Pines / Miramar", 25.9900, -80.2700, 7500, True),
    ("coral-springs-coconut-creek", "Coral Springs", "Coral Springs / Coconut Creek / Margate",
     26.2700, -80.2400, 7000, True),
    ("obs-aventura-sunny-isles", "Aventura", "Aventura / Sunny Isles Beach -- OBSERVATION ONLY",
     25.9500, -80.1300, 5000, False),
    ("obs-boca-raton", "Boca Raton", "Boca Raton -- OBSERVATION ONLY", 26.3600, -80.0900, 6000, False),
]

BOUNDS = {"min_lat": 25.90, "max_lat": 26.45, "min_lng": -80.50, "max_lng": -80.05}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Downtown Fort Lauderdale", 26.1220, -80.1430, 1.4),
    ("Las Olas Boulevard", 26.1190, -80.1310, 1.6),
    ("Fort Lauderdale Beach", 26.1290, -80.1050, 2.0),
    ("Hugh Taylor Birch State Park", 26.1440, -80.1050, 1.2),
    ("Victoria Park", 26.1310, -80.1310, 1.0),
    ("Port Everglades", 26.0930, -80.1170, 2.0),
    ("17th Street Causeway", 26.1020, -80.1240, 1.6),
    ("Broward County Convention Center", 26.0970, -80.1230, 1.0),
    ("Harbor Beach", 26.0990, -80.1080, 1.2),
    ("Bahia Mar / Seabreeze Boulevard", 26.1090, -80.1080, 1.2),
    ("Fort Lauderdale-Hollywood International Airport (FLL)", 26.0726, -80.1527, 3.0),
    ("State Road 84 / Marina Mile", 26.0910, -80.1750, 3.0),
    ("Dania Beach", 26.0540, -80.1440, 2.6),
    ("Hollywood Beach Broadwalk", 26.0170, -80.1160, 2.2),
    ("Downtown Hollywood / Young Circle", 26.0110, -80.1470, 1.4),
    ("Hallandale Beach", 25.9850, -80.1340, 2.2),
    ("Gulfstream Park", 25.9790, -80.1420, 1.2),
    ("Galt Ocean Mile", 26.1620, -80.0990, 1.4),
    ("Lauderdale-by-the-Sea", 26.1930, -80.0970, 1.6),
    ("Sea Ranch Lakes", 26.1830, -80.0970, 0.8),
    ("Wilton Manors", 26.1600, -80.1400, 1.6),
    ("Oakland Park", 26.1720, -80.1320, 2.0),
    ("Coral Ridge", 26.1560, -80.1130, 1.6),
    ("Cypress Creek", 26.1930, -80.1600, 2.4),
    ("Pompano Beach Pier", 26.2340, -80.0900, 1.8),
    ("Hillsboro Beach", 26.2800, -80.0800, 2.0),
    ("Lighthouse Point", 26.2760, -80.0880, 1.6),
    ("Deerfield Beach Pier", 26.3180, -80.0760, 1.8),
    ("Plantation", 26.1230, -80.2330, 3.0),
    ("Davie", 26.0760, -80.2520, 3.5),
    ("Nova Southeastern University", 26.0800, -80.2410, 1.5),
    ("Cooper City", 26.0570, -80.2870, 2.5),
    ("Sawgrass Mills", 26.1500, -80.3020, 2.0),
    ("Sunrise", 26.1500, -80.2960, 3.5),
    ("Tamarac", 26.2100, -80.2500, 3.0),
    ("Lauderhill", 26.1470, -80.2130, 2.5),
    ("Weston", 26.1000, -80.3990, 4.0),
    ("Pembroke Pines", 26.0080, -80.3200, 4.5),
    ("Miramar", 25.9770, -80.3350, 4.5),
    ("Coral Springs", 26.2710, -80.2710, 4.0),
    ("Coconut Creek", 26.2510, -80.1790, 3.0),
    ("Margate", 26.2450, -80.2060, 2.5),
    ("Parkland", 26.3100, -80.2370, 3.0),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Port Everglades", re.compile(r"\beller dr(ive)?\b|\bmcintosh rd\b|\bport everglades\b|\bcruise terminal\b", re.I)),
    ("17th Street Causeway", re.compile(r"\b(se|s\.?e\.?|southeast) ?17(th)? ?(st|street)\b|\b17(th)? st(reet)? c(au)?sw?(a)?y\b", re.I)),
    ("Harbor Beach", re.compile(r"\bholiday dr(ive)?\b|\bharbor dr(ive)?\b|\bs(outh)? ocean ln\b|\bocean lane\b", re.I)),
    ("Bahia Mar / Seabreeze Boulevard", re.compile(r"\bseabreeze b(lv)?d\b|\bbahia mar\b", re.I)),
    ("Fort Lauderdale Beach", re.compile(r"\b(n|s|north|south)? ?(ft|fort) ?lauderdale beach b(lv)?d\b|\bbirch rd\b|"
                                         r"\bbreakers ave\b|\borton ave\b|\bbayshore dr\b", re.I)),
    ("Las Olas Boulevard", re.compile(r"\blas olas\b", re.I)),
    ("Galt Ocean Mile", re.compile(r"\bgalt ocean\b", re.I)),
    ("Lauderdale-by-the-Sea", re.compile(r"\bel mar dr\b|\bbougainvilla dr\b|\bpoinciana st\b", re.I)),
    ("State Road 84 / Marina Mile", re.compile(r"\b(s\.?r\.?|state (rd|road)) ?84\b|\bmarina mile\b|"
                                               r"\bmaritime b(lv)?d\b|\banglers ave\b", re.I)),
    ("Fort Lauderdale-Hollywood International Airport (FLL)", re.compile(
        r"\bgriffin rd\b|\bstirling rd\b|\bn(orth)? compass way\b|\bsw 18(th)? ave\b|\bsw 19(th)? ct\b|"
        r"\bgulf stream way\b|\bterminal dr\b", re.I)),
    ("Hollywood Beach Broadwalk", re.compile(r"\bbroadwalk\b|\bsurf rd\b", re.I)),
    ("Gulfstream Park", re.compile(r"\bgulfstream way\b|\bvillage at gulfstream\b", re.I)),
    ("Sawgrass Mills", re.compile(r"\bsawgrass mills\b|\bsawgrass corporate\b|\bnw 136(th)? ave\b", re.I)),
    ("Nova Southeastern University", re.compile(r"\bnova dr(ive)?\b|\bsw 30(th)? st\b", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-las-olas": "Downtown Fort Lauderdale", "fort-lauderdale-beach": "Fort Lauderdale Beach",
    "port-everglades-17th-street": "Port Everglades", "fll-airport-sr84":
        "Fort Lauderdale-Hollywood International Airport (FLL)", "dania-beach": "Dania Beach",
    "hollywood-beach": "Hollywood Beach Broadwalk", "hollywood": "Downtown Hollywood / Young Circle",
    "plantation-davie": "Plantation", "hallandale-beach": "Hallandale Beach",
    "galt-ocean-lauderdale-by-the-sea": "Galt Ocean Mile", "oakland-park-wilton-manors": "Oakland Park",
    "cypress-creek": "Cypress Creek", "pompano-beach": "Pompano Beach Pier", "deerfield-beach":
        "Deerfield Beach Pier", "sunrise-tamarac-lauderhill": "Sunrise", "weston-southwest-ranches": "Weston",
    "pembroke-pines-miramar": "Pembroke Pines", "coral-springs-coconut-creek": "Coral Springs",
}

STRUCTURE_TEST = OrderedDict([
    ("A. Downtown Fort Lauderdale / Las Olas",
     "CORE, one corridor downtown-las-olas (33301). Las Olas Boulevard is the market's spine but it crosses three "
     "postal codes on its way to the sand; the downtown end (Andrews Avenue to the Intracoastal, Riverwalk, "
     "Flagler Village) is 33301 and is its own corridor. Las Olas is reported as a street overlay wherever it "
     "appears."),
    ("B. Fort Lauderdale Beach",
     "CORE, one corridor fort-lauderdale-beach (33304). The A1A beachfront wall (Ritz-Carlton, W, Conrad, Four "
     "Seasons, Westin, Sonesta, Hilton Beach Resort) plus the North Birch Road / Breakers Avenue guesthouse "
     "district. Victoria Park shares 33304 inland and is an overlay, never a second corridor."),
    ("C. FLL Airport",
     "NO CORRIDOR OF ITS OWN -- the airport owns no postal code. Its hotel district splits on a real seam: the "
     "south side (Stirling Road, SW 18th Avenue / 19th Court, North Compass Way, eastern Griffin Road) is Dania "
     "Beach 33004; the north and west side (State Road 84 / Marina Mile, Maritime Boulevard, Anglers Avenue) is "
     "33312 / 33315. 'FLL Airport' is a street-and-pin overlay across both corridors."),
    ("D. Port Everglades / cruise lodging",
     "CORE, one corridor port-everglades-17th-street (33316) -- see the cruise test. Unlike PortMiami, the port "
     "shares its postal code with the 17th Street Causeway hotel wall, the Convention Center, Harbor Beach and "
     "the Bahia Mar south beach strip, so the corridor carries real inventory no other corridor claims."),
    ("E. Dania Beach",
     "CORE, one corridor dania-beach (33004). It is a distinct municipality with its own downtown, its own beach "
     "and pier, its own Federal Highway motel row -- and it happens to hold FLL's south-side hotel cluster. A "
     "'Fort Lauderdale Airport' name on a Dania Beach licence never moves the property."),
    ("F. Hollywood",
     "CORE, one corridor hollywood (33020, 33021, 33024). Inside fort-lauderdale-fl: Broward County, Visit "
     "Lauderdale territory, FLL's own catchment. Never folded into generic Fort Lauderdale -- it is its own "
     "named corridor with its own display area."),
    ("G. Hollywood Beach",
     "CORE, one corridor hollywood-beach (33019), SEPARATE from inland Hollywood. It is the densest lodging "
     "postal code in Broward County (2,041 DBPR lodging licences of all ranks, 65 hotel / motel / B&B) and a "
     "distinct beach travel system -- the Broadwalk, Ocean Drive, Surf Road and the South Ocean Drive resort "
     "towers. Distinct beach systems are never merged merely because they share a county."),
    ("H. Hallandale Beach",
     "CORE, one corridor hallandale-beach (33009). Broward's southernmost municipality. Gulfstream Park and the "
     "South Ocean Drive towers face Aventura and Sunny Isles across the county line; the LINE decides, not the "
     "distance, and everything south of it belongs to the LIVE miami-fl market."),
    ("I. Plantation / Davie",
     "CORE, one corridor plantation-davie (33314, 33317, 33324, 33325, 33328). Plantation's Broward Boulevard and "
     "Pine Island Road office parks, Davie's Nova Southeastern University and the South Florida Education Center, "
     "and Cooper City. Plantation, Davie and Fort Lauderdale share every one of these postal codes; a 'Fort "
     "Lauderdale' name on a Plantation address never moves the property."),
    ("J. Sunrise",
     "FRINGE, inside sunrise-tamarac-lauderhill (33313, 33319, 33321, 33322, 33323, 33351). Sawgrass Mills and "
     "the Amerant Bank Arena are real demand generators, but the lodging is thin and its postal codes are shared "
     "with Plantation, Tamarac, Lauderhill and Lauderdale Lakes; admitted at FRINGE density, on one corridor."),
    ("K. Pompano Beach",
     "CORRIDOR, one corridor pompano-beach (33060, 33062, 33064, 33069). A distinct beach town with its own pier, "
     "its own A1A hotel row and its own Atlantic Boulevard downtown. Hillsboro Beach and Lighthouse Point share "
     "33062 / 33064 and are overlays. A 'Fort Lauderdale / Pompano Beach' brand name never moves a property into "
     "the Fort Lauderdale beach corridor."),
    ("L. Deerfield Beach",
     "CORRIDOR, one corridor deerfield-beach (33441, 33442). Broward's northern boundary town, with its own pier "
     "and oceanfront. It adjoins Boca Raton across the Palm Beach County line, which is refused."),
])

CRUISE_TEST = OrderedDict([
    ("port_everglades_lodging_in_its_own_postal_code",
     "YES -- ZIP 33316 carries 32 DBPR hotel / motel / B&B licences (734 lodging licences of all ranks), including "
     "the 17th Street Causeway wall (Embassy Suites, Hilton Fort Lauderdale Marina, Pier Sixty-Six, Omni, Hyatt "
     "Place Cruise Port, Holiday Inn Express Cruise Port, Crowne Plaza Airport/Cruise, Four Points Airport & "
     "Cruise), Harbor Beach (Marriott Harbor Beach at 3030 Holiday Drive, Lago Mar) and Bahia Mar."),
    ("17th_street_causeway", "INSIDE the corridor -- it is the corridor's own hotel spine, not a separate one."),
    ("convention_center", "INSIDE the corridor -- the Broward County Convention Center sits at 1950 Eisenhower "
                          "Boulevard inside the port's own postal code."),
    ("fll_to_port_hotel_cluster",
     "SPLIT ON A REAL SEAM, and reported as such: the hotels that sell themselves as 'Airport & Cruise Port' are "
     "physically on State Road 84 (33315), in Dania Beach (33004), or on 17th Street (33316). Each sits in the "
     "corridor its own postal code names; the dual 'airport/cruise' marketing is an overlay label."),
    ("downtown_pre_post_cruise_lodging",
     "Downtown Fort Lauderdale (33301) carries genuine pre/post-cruise demand but is a separate postal code with "
     "its own Las Olas / Riverwalk identity; it is NOT absorbed into a cruise corridor."),
    ("dania_beach_cruise_hotels", "Inside dania-beach (33004) -- Dania Beach is its own municipality and corridor."),
    ("port_everglades_corridor_created", True),
    ("why",
     "The corridor passes every test the order sets: density (32 hotel-rank licences on its own postal code), "
     "coherent traveller intent (cruise + convention + marina + Harbor Beach, one contiguous system around the "
     "17th Street Causeway), and NOT duplicate inventory -- the corridor registry is a postal-code partition, so "
     "33316 is claimed by this corridor and by nothing else. This is the exact opposite of the PortMiami finding "
     "in PTF-MIAMI-FL-HARDENED-SOURCE-READY-001, where Dodge Island carried terminals and no hotels and a port "
     "corridor would have duplicated downtown-brickell's postal codes. Cruise relevance informed the corridor's "
     "NAME only; it never altered one premises identity."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel operation."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP), matched to a DBPR HOTL / "
     "MOTL / BNB licence at that premises. A unit designator ('Ste', 'Unit', '#', 'Apt', 'PH') in the licensed "
     "address means the licence is a UNIT INSIDE a building, which is never a hotel identity."),
    ("hotel_vs_residence_boundary",
     "A tower that sells both hotel rooms and condominium residences is admitted ONLY as the hotel premises. The "
     "residences are refused as RESORT_RESIDENCE even where they share the address, the brand, the entrance, the "
     "pool and the booking engine."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared amenities "
     "or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never published as one."),
])


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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Fort Lauderdale" % name),
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
        ("market_name", "Fort Lauderdale / Greater Broward County, Florida beach, cruise, airport and convention "
                        "lodging market (PetTripFinder discovery scope)"),
        ("state", "FL"),
        ("states", ["FL"]),
        ("country", "US"),
        ("market_center", {"lat": 26.12, "lng": -80.15}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past the Miami-Dade line (Aventura, "
             "Sunny Isles Beach) and north past the Palm Beach County line (Boca Raton) so that " + WORK_ORDER +
             " classifies those properties on evidence instead of being blind to them. Admission is decided by "
             "the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Greater Fort Lauderdale is ONE Broward County market: nine CORE corridors (Downtown/Las "
         "Olas, Fort Lauderdale Beach, Port Everglades/17th Street, FLL/SR-84, Dania Beach, Hollywood Beach, "
         "Hollywood, Plantation/Davie, Hallandale Beach), five CORRIDOR tiers and four FRINGE corridors. "
         "Miami-Dade County belongs to the LIVE miami-fl market; Palm Beach County and the Florida Keys are "
         "OUTSIDE and preserved as future standalone markets."),
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
        ("market_name", "Fort Lauderdale, Florida"),
        ("market_slug", MARKET_ID),
        ("state_name", "Florida"),
        ("state_code", "FL"),
        ("primary_state_code", "FL"),
        ("states", ["FL"]),
        ("primary_city", "Fort Lauderdale"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Fort Lauderdale & Broward County, Florida | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater Fort Lauderdale -- Las Olas & downtown, Fort Lauderdale "
         "Beach, Port Everglades & 17th Street, FLL Airport, Dania Beach, Hollywood Beach, Hallandale Beach, "
         "Pompano Beach and Deerfield Beach -- with real pet fees and policies read from each hotel's own "
         "official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Fort Lauderdale"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its Florida DBPR public-lodging "
         "licence states it, joined to the corridor registry. A Broward County beach, cruise, airport and "
         "convention travel market -- not the City of Fort Lauderdale's limits and not all of South Florida. "
         "Nothing else admits a property: not a brand's 'Fort Lauderdale' marketing name, not a map pin, not a "
         "vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Broward's postal "
         "codes straddle municipalities freely: 33308 is shared by Fort Lauderdale, Lauderdale-by-the-Sea and Sea "
         "Ranch Lakes; 33305 / 33311 / 33334 by Fort Lauderdale and Wilton Manors; 33306 / 33309 / 33334 by "
         "Oakland Park; 33064 by Lighthouse Point, Pompano Beach and Deerfield Beach; 33312 by Fort Lauderdale "
         "and Dania Beach; 33322 / 33323 / 33325 by Sunrise, Plantation and Davie. Each shared code is one "
         "corridor and its named places are reported as overlays. Las Olas, Port Everglades, the 17th Street "
         "Causeway, Harbor Beach, FLL, Victoria Park, the Galt Ocean Mile and the Hollywood Broadwalk are "
         "overlays, never corridors of their own."),
        ("_census_membership_note",
         "Individual condominium units (DBPR CNDO), vacation dwellings (DWEL), vacation homes, property-management "
         "portfolios, Airbnb / Vrbo inventory, ordinary apartments (DBPR NAPT), individual timeshare units, private "
         "resort / branded residences and military-only lodging are never admitted. A mixed hotel / condo / "
         "residence tower is admitted only as the exact hotel premises its public operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "3 + 4 + 5 + 6 -- Greater Fort Lauderdale / Broward County travel-market geography, the "
                  "Fort Lauderdale / Hollywood / Pompano structure test, the Port Everglades cruise test and the "
                  "beach / resort / condo-hotel safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "REGISTERED: the market document is written to the registry's markets/fort-lauderdale-fl.json by "
         "PTF-FORT-LAUDERDALE-FL-REGISTRATION-AND-STAGING-002. The source-ready order's markets/proposed/ "
         "copy is history."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its Florida DBPR public-lodging licence states "
         "it, joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes (and, for the registry lane, by "
                          "county); the existing live market and future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("fort_lauderdale_structure_test", STRUCTURE_TEST),
        ("port_everglades_cruise_test", CRUISE_TEST),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("evaluated_inclusions", OrderedDict([
            ("Downtown Fort Lauderdale", "ADMITTED (CORE, downtown-las-olas)."),
            ("Las Olas", "ADMITTED as an OVERLAY on downtown-las-olas, fort-lauderdale-beach and "
                         "port-everglades-17th-street -- Las Olas Boulevard crosses three postal codes."),
            ("Fort Lauderdale Beach", "ADMITTED (CORE, fort-lauderdale-beach)."),
            ("Fort Lauderdale-Hollywood International Airport / FLL",
             "ADMITTED as an OVERLAY across fll-airport-sr84 (33312, 33315) and dania-beach (33004). The airport "
             "owns no postal code, so it is never a corridor."),
            ("Port Everglades", "ADMITTED (CORE, port-everglades-17th-street) -- see the cruise test."),
            ("Dania Beach", "ADMITTED (CORE, dania-beach)."),
            ("Hollywood", "ADMITTED (CORE, hollywood)."),
            ("Hollywood Beach", "ADMITTED (CORE, hollywood-beach), separate from inland Hollywood."),
            ("Hallandale Beach", "ADMITTED (CORE, hallandale-beach)."),
            ("Plantation", "ADMITTED (CORE, plantation-davie)."),
            ("Davie", "ADMITTED (CORE, plantation-davie)."),
            ("Sunrise", "ADMITTED (FRINGE, sunrise-tamarac-lauderhill) -- strong evaluation."),
            ("Lauderhill", "ADMITTED (FRINGE, sunrise-tamarac-lauderhill, 33313/33319/33351) -- strong evaluation."),
            ("Tamarac", "ADMITTED (FRINGE, sunrise-tamarac-lauderhill, 33319/33321/33351) -- strong evaluation."),
            ("Lauderdale-by-the-Sea",
             "ADMITTED (CORRIDOR, galt-ocean-lauderdale-by-the-sea, 33308) -- strong evaluation. It shares 33308 "
             "with Fort Lauderdale's Galt Ocean Mile and is reported as an overlay, never a corridor of its own."),
            ("Oakland Park", "ADMITTED (CORRIDOR, oakland-park-wilton-manors, 33306/33334; also 33309 in "
                             "cypress-creek) -- strong evaluation."),
            ("Wilton Manors", "ADMITTED (CORRIDOR, oakland-park-wilton-manors, 33305/33334; also 33311 in "
                              "cypress-creek) -- strong evaluation."),
            ("Pompano Beach", "ADMITTED (CORRIDOR, pompano-beach) -- strong evaluation."),
            ("Deerfield Beach", "ADMITTED (CORRIDOR, deerfield-beach) -- strong evaluation."),
            ("Coconut Creek", "ADMITTED (FRINGE, coral-springs-coconut-creek, 33063/33066/33073) -- strong "
                              "evaluation."),
            ("Coral Springs", "ADMITTED (FRINGE, coral-springs-coconut-creek, 33065/33067/33071/33076) -- strong "
                              "evaluation."),
            ("Margate", "ADMITTED (FRINGE, coral-springs-coconut-creek, 33063/33068/33073) -- strong evaluation."),
            ("Pembroke Pines", "ADMITTED (FRINGE, pembroke-pines-miramar) -- strong evaluation."),
            ("Miramar", "ADMITTED (FRINGE, pembroke-pines-miramar) -- strong evaluation."),
            ("Weston", "ADMITTED (FRINGE, weston-southwest-ranches) -- strong evaluation. USPS still addresses "
                       "33326 / 33327 as 'Fort Lauderdale'; the postal code, not the city string, places it."),
            ("Cooper City", "ADMITTED (CORE, plantation-davie, 33328/33330) -- strong evaluation."),
            ("Southwest Ranches", "ADMITTED (FRINGE, weston-southwest-ranches, 33330/33331/33332) -- careful "
                                  "evaluation."),
            ("Parkland", "ADMITTED (FRINGE, coral-springs-coconut-creek, 33067/33076) -- careful evaluation."),
            ("Hillsboro Beach", "ADMITTED (CORRIDOR, pompano-beach, 33062) -- careful evaluation; shares 33062 "
                                "with Pompano Beach and is an overlay."),
            ("Lighthouse Point", "ADMITTED (CORRIDOR, pompano-beach, 33064) -- careful evaluation; shares 33064 "
                                 "with Pompano Beach and Deerfield Beach and is an overlay."),
            ("Sea Ranch Lakes", "ADMITTED (CORRIDOR, galt-ocean-lauderdale-by-the-sea, 33308) -- careful "
                                "evaluation; an overlay on a shared postal code."),
            ("North Lauderdale", "ADMITTED (FRINGE, coral-springs-coconut-creek, 33068) -- careful evaluation."),
            ("West Park", "ADMITTED (FRINGE, pembroke-pines-miramar, 33023) -- careful evaluation."),
            ("Lauderdale Lakes", "ADMITTED (CORRIDOR cypress-creek 33309/33311 and FRINGE "
                                 "sunrise-tamarac-lauderhill 33313/33319) -- careful evaluation; an overlay on "
                                 "shared postal codes."),
            ("Properties using 'Fort Lauderdale' mainly as marketing",
             "Never admitted or placed by name: a 'Fort Lauderdale Airport' / 'Fort Lauderdale Pompano Beach' / "
             "'Fort Lauderdale North' name is placed by its OWN postal code, which may be Dania Beach, Pompano "
             "Beach, Plantation or Weston. A 'Miami' name whose own address is Hallandale Beach 33009 is a Broward "
             "property and belongs to this market."),
            ("Miami / Miami Beach", "OUTSIDE (Miami-Dade County) -- the EXISTING LIVE market miami-fl."),
            ("Aventura", "OUTSIDE (Miami-Dade County) -- miami-fl corridor 'aventura', live."),
            ("Sunny Isles Beach", "OUTSIDE (Miami-Dade County) -- miami-fl corridor 'sunny-isles-beach', live."),
            ("All Miami-Dade inventory", "OUTSIDE -- miami-fl is live as market #31 and owns it."),
            ("Boca Raton", "OUTSIDE by name (order) -- Palm Beach County, future west-palm-beach-fl."),
            ("Delray Beach", "OUTSIDE by name (order) -- Palm Beach County, future west-palm-beach-fl."),
            ("Boynton Beach", "OUTSIDE by name (order) -- Palm Beach County, future west-palm-beach-fl."),
            ("West Palm Beach / Palm Beach", "OUTSIDE by name (order) -- future west-palm-beach-fl."),
            ("All Palm Beach County inventory", "OUTSIDE by name (order); no border case was found that required "
                                                "review -- Deerfield Beach 33441/33442 stops at the county line."),
            ("Florida Keys", "OUTSIDE by name (order) -- Monroe County, future florida-keys-fl."),
        ])),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_counties", sorted(ADMITTED_COUNTIES)),
        ("observed_outside_counties", OBSERVED_COUNTIES),
        ("shared_postal_codes", SHARED_POSTAL_CODES),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO or cruise keywords; every corridor "
         "is show_in_navigation / show_in_sitemap false until a registration order publishes it. Las Olas, "
         "Victoria Park, Port Everglades, the 17th Street Causeway, Harbor Beach, FLL, the Galt Ocean Mile, "
         "Lauderdale-by-the-Sea, Sea Ranch Lakes, Hillsboro Beach, Lighthouse Point, Wilton Manors, Oakland Park, "
         "Lauderdale Lakes, Cooper City, Southwest Ranches, Parkland, West Park and the Hollywood Broadwalk are "
         "overlays."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, public resorts, qualifying condo-hotels with a distinct public hotel "
         "operation, qualifying extended-stay hotels and other public lodging establishments: bookable nightly rooms "
         "or suites sold to the public under one establishment name, with an official property page and an on-site "
         "hotel operation. It NEVER admits: individual condominium units (DBPR rank CNDO) or vacation dwellings (DBPR "
         "rank DWEL); individual vacation homes or villas; property-management / short-term-rental portfolios; "
         "Airbnb / Vrbo listings; ordinary apartments (DBPR NAPT); individual timeshare units; private resort or "
         "branded residences; and privately managed units inside hotel-condo towers. A mixed hotel / condo / "
         "residence tower is admitted ONLY as the exact hotel premises its public operator sells as a hotel, proved "
         "on the operator's own page and the licence's exact premises. Campgrounds, RV parks and hostels are "
         "NON_LODGING."),
        ("shared_campus_rule",
         "Never merged solely by display name, brand, owner, phone, shared address, campus, booking engine, shared "
         "amenities or shared entrance. Exact premises identity (its own street address or its own brand property "
         "code on its own page) governs; a hotel and the residences above it are two things, and only the hotel is "
         "a census row. A dual-brand building is TWO hotels and is HELD for the split."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "ft lauderdale": "fort lauderdale", "ft. lauderdale": "fort lauderdale",
    "fortlauderdale": "fort lauderdale", "fort lauderdade": "fort lauderdale",
    "fort lauderdale,": "fort lauderdale", "lauderdale": "fort lauderdale",
    "lauderdale-by-the-se": "lauderdale-by-the-sea", "lauderdale by the se": "lauderdale-by-the-sea",
    "lauderdale bythe sea": "lauderdale-by-the-sea", "lauderdale by the sea": "lauderdale-by-the-sea",
    "lauderdale-by-the sea": "lauderdale-by-the-sea", "lbts": "lauderdale-by-the-sea",
    "dania": "dania beach", "hallandale": "hallandale beach", "hallendale beach": "hallandale beach",
    "hollywood beach": "hollywood", "holyywood": "hollywood", "hollwood": "hollywood",
    "holliwood": "hollywood", "hollywood,": "hollywood",
    "pompano": "pompano beach", "lighthouse pt": "lighthouse point",
    "deerfield": "deerfield beach", "deerfield bch": "deerfield beach",
    "deerfiled beach": "deerfield beach", "luaderhill": "lauderhill",
    "sw ranches": "southwest ranches", "sunrise, fl": "sunrise", "sunrise fl": "sunrise",
    "plantation,": "plantation", "plantation gardens": "plantation", "westone": "weston",
    "n lauderdale": "north lauderdale", "oakland pk": "oakland park",
}

#: The shared postal codes the corridor registry deliberately covers whole, with the municipalities that share
#: each one on the state's own record. Reporting only -- a shared code is still exactly one corridor.
SHARED_POSTAL_CODES = OrderedDict([
    ("33004", ["Dania Beach", "Dania", "Hollywood"]),
    ("33009", ["Hallandale Beach", "Hallandale", "Hollywood"]),
    ("33019", ["Hollywood", "Hollywood Beach", "Hallandale"]),
    ("33023", ["Miramar", "Hollywood", "Pembroke Pines", "West Park"]),
    ("33024", ["Hollywood", "Pembroke Pines", "Davie", "Cooper City"]),
    ("33062", ["Pompano Beach", "Hillsboro Beach", "Lauderdale-by-the-Sea"]),
    ("33063", ["Margate", "Coconut Creek"]),
    ("33064", ["Lighthouse Point", "Pompano Beach", "Deerfield Beach"]),
    ("33067", ["Parkland", "Coral Springs"]),
    ("33068", ["North Lauderdale", "Margate", "Tamarac"]),
    ("33073", ["Coconut Creek", "Margate", "Pompano Beach"]),
    ("33305", ["Fort Lauderdale", "Wilton Manors"]),
    ("33306", ["Fort Lauderdale", "Oakland Park", "Wilton Manors"]),
    ("33308", ["Fort Lauderdale", "Lauderdale-by-the-Sea", "Sea Ranch Lakes"]),
    ("33309", ["Oakland Park", "Fort Lauderdale", "Lauderdale Lakes"]),
    ("33311", ["Fort Lauderdale", "Wilton Manors", "Lauderdale Lakes"]),
    ("33312", ["Fort Lauderdale", "Dania Beach"]),
    ("33313", ["Sunrise", "Lauderhill", "Plantation", "Lauderdale Lakes"]),
    ("33314", ["Davie", "Dania Beach", "Fort Lauderdale"]),
    ("33317", ["Plantation", "Fort Lauderdale", "Davie"]),
    ("33319", ["Tamarac", "Lauderdale Lakes", "Lauderhill"]),
    ("33322", ["Plantation", "Sunrise"]),
    ("33323", ["Plantation", "Sunrise"]),
    ("33324", ["Plantation", "Davie"]),
    ("33325", ["Plantation", "Davie", "Sunrise"]),
    ("33326", ["Weston", "Fort Lauderdale (USPS name)"]),
    ("33328", ["Cooper City", "Davie"]),
    ("33330", ["Davie", "Southwest Ranches", "Cooper City"]),
    ("33331", ["Southwest Ranches", "Weston", "Davie"]),
    ("33334", ["Oakland Park", "Fort Lauderdale", "Wilton Manors"]),
    ("33351", ["Sunrise", "Lauderhill", "Tamarac"]),
])

#: FUTURE standalone markets this order preserves by name.
FUTURE_MARKETS = OrderedDict([
    ("west-palm-beach-fl", "West Palm Beach / Palm Beach / Boca Raton / Delray Beach / Boynton Beach -- Palm Beach "
                           "County, with its own airport (PBI) and CVB (Discover The Palm Beaches)"),
    ("florida-keys-fl", "The Florida Keys (Key Largo / Islamorada / Marathon / Key West) -- Monroe County, its own "
                        "island resort market (possibly split Upper Keys / Key West when built)"),
])

#: Markets that are ALREADY LIVE and own the inventory this market refuses. Never 'future'.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("miami-fl", "Miami - Miami Beach / Greater Miami-Dade, live as market #31 (deploy 6ab071a5b7561c33aff6c17b). "
                 "Owns every Miami-Dade postal code, including Aventura 33180 and Sunny Isles Beach 33160 "
                 "immediately south of Hallandale Beach."),
])


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
    return CORRIDOR_DEFAULT_OVERLAY.get(corridor_slug)


def normalise_municipality(city):
    muni = " ".join((city or "").lower().replace(".", " ").split())
    muni = muni.replace(" ,", ",")
    return MUNICIPALITY_SPELLINGS.get(muni, MUNICIPALITY_SPELLINGS.get(muni.rstrip(","), muni))


def future_market_for(postal):
    """The market id a refused postal code is preserved for (future standalone OR existing live), or ""."""
    z = (postal or "").strip()[:5]
    for _name, _s, zs, why in OUTSIDE:
        if z in zs:
            for fid in list(EXISTING_LIVE_MARKETS) + list(FUTURE_MARKETS):
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
