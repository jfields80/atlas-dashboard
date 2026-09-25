"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phases 3, 4, 5 and 6: the Jacksonville / Northeast Florida market.

Built from zero on the CURRENT hardened lineage (lineage-test-047 semantics repair bf7a54c3 on top of the live
West Palm Beach release e3efa221). Current verified live at authoring time = west-palm-beach-fl deploy
6ab599163f833ab7f48b395d, 33 markets / 2,424 profiles / 2,701 release-index routes / 2,767 served routes. No
earlier Jacksonville FLORIDA build exists. The LIVE market `jacksonville-nc` is a DIFFERENT PLACE (Onslow County,
North Carolina, ZIPs 285xx) and is named here so no later phase confuses the two.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Jacksonville / Northeast Florida traveller lodging market, stated as an explicit
CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE and EXISTING_LIVE markets named inside OUTSIDE)
before a single hotel is admitted, so no property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or the Florida DBPR
public-lodging licence, the state's own record of the licensed premises) states it, joined to the corridor
registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing name never admits and
never places a property: a hotel whose own address states Saint Augustine 32084 is a St. Augustine hotel however
loudly it calls itself "Jacksonville South", and a hotel whose own address states Jacksonville NC 28546 is not
in this market at all.

WHY "JACKSONVILLE" IS THIS MARKET'S DEFINING IDENTITY TRAP, TWICE OVER
----------------------------------------------------------------------
FIRST, ACROSS STATES. `jacksonville-nc` is LIVE as production market #22 -- Jacksonville, Onslow County, North
Carolina (Camp Lejeune; ZIPs 28540 / 28543 / 28544 / 28545 / 28546 / 28547). Every chain that operates in both
cities publishes two hotels with almost the same trade name: "Hampton Inn Jacksonville", "Home2 Suites by Hilton
Jacksonville", "Holiday Inn Express Jacksonville", "Sleep Inn Jacksonville", "Super 8 Jacksonville". A NAME
PROPOSES AN IDENTITY AND NEVER DECIDES ONE: these are separated by state code, postal code, street and brand
property code, never by the word "Jacksonville". No generic chain-name flag raised in the North Carolina market
may hold a Florida row, and no Florida row may hold a North Carolina one.

SECOND, INSIDE FLORIDA. Duval County is a CONSOLIDATED city-county: the City of Jacksonville is the county, so
the postal city "JACKSONVILLE" spans 25 lodging-bearing postal codes from the Georgia line to the St. Johns
County line and from the Atlantic to Baldwin -- 39 miles across. "Jacksonville" as a city name therefore places
nothing at all inside this market either. Only the postal code does. The four beach municipalities (Jacksonville
Beach, Neptune Beach, Atlantic Beach, Baldwin) are separate municipalities INSIDE Duval County, and Mayport
Village and Naval Station Mayport share Atlantic Beach's 32233.

WHERE NORTHEAST FLORIDA'S POSTAL CODES STRADDLE MUNICIPALITIES AND COUNTIES
---------------------------------------------------------------------------
32233 carries Atlantic Beach AND Mayport Village AND Jacksonville; 32250 carries Jacksonville Beach AND
Jacksonville; 32034 carries Fernandina Beach AND Amelia Island; 32259 is a ST. JOHNS COUNTY code whose Fruit
Cove / Julington Creek lodging faces Duval's Mandarin across Julington Creek; 32073 and 32065 carry Orange Park
AND unincorporated Clay County AND Oakleaf, whose Duval half is 32222. A corridor therefore covers a shared
postal code AS A WHOLE and reports its named places as street-and-pin overlays. It never splits a ZIP, because a
split ZIP is a judgement applied per property -- exactly what this registry exists to forbid.

THE STRUCTURE TEST (PHASE 4): COUNTY INCLUSION IS NOT TRAVELLER-MARKET INCLUSION
--------------------------------------------------------------------------------
Four counties were evaluated separately and they did NOT all answer the same way. Duval is the market. Clay
(Orange Park / Fleming Island) is a Jacksonville commuter suburb on Blanding Boulevard and US-17 and is admitted
at CORRIDOR tier, but its inland lake country (Keystone Heights 32656) is refused by name. Nassau splits: Amelia
Island / Fernandina Beach is admitted at CORRIDOR tier and the rural Callahan / Hilliard / Yulee interchange row
at FRINGE. St. Johns splits HARDEST of all: Ponte Vedra Beach (32082) is admitted because it is the next beach
south of Jacksonville Beach on A1A and its resorts fly guests into JAX, while ST. AUGUSTINE IS REFUSED ENTIRELY
and reserved as a future standalone market. The state's own register settles that: 32084 alone carries 78
hotel-rank lodging licences and 32080 (St. Augustine Beach) another 29 -- 116 across the St. Augustine codes,
which is a larger hotel-rank inventory than most PetTripFinder markets publish in total. Absorbing it would
destroy a market, not extend one.

NO AIRPORT CORRIDOR OF ITS OWN NAME -- BUT JAX IS THIS MARKET'S LARGEST CLUSTER
-------------------------------------------------------------------------------
Jacksonville International (JAX) sits at Airport Center Drive and Duval Road inside postal code 32218, and 32218
carries 29 hotel-rank lodging licences -- the single largest concentration in the market. Unlike PBI and FLL,
which owned no postal code, JAX's hotel district IS a postal code, so the corridor exists; it is named
`jax-airport-northside` rather than "airport" because 32218 also carries Dunn Avenue, River City Marketplace and
the I-95 / I-295 north interchange, and because 32208, 32209, 32219 and 32226 (Oceanway, Dames Point, JAXPORT
Blount Island) belong to the same northern travel system. This is the POSTAL-CODE test the three prior Florida
markets settled, answered YES here for the first time.

NO CRUISE CORRIDOR: JAXPORT FAILS THE PORT EVERGLADES TEST
----------------------------------------------------------
JAXPORT's cruise terminal is at Dames Point in postal code 32226, which carries ONE hotel-rank lodging licence
and is already claimed in full by `jax-airport-northside`. Like PortMiami and the Port of Palm Beach, and unlike
Port Everglades (33316, a postal code full of hotels claimed by nothing else), a cruise corridor here could only
be built by splitting or duplicating a code the registry already covers. Cruise passengers stay in the airport /
Northside cluster or downtown. JAXPORT is a street-and-pin OVERLAY.

NO MAYPORT CORRIDOR, AND THE STATE'S REGISTER PROVES IT
-------------------------------------------------------
The order requires Mayport to be evaluated explicitly. It was, mechanically: postal codes 32227 (Naval Station
Mayport) and 32228 (Mayport) carry ZERO public-lodging licences of any rank on the state's own record. Naval
Station Mayport is a military installation whose billeting is not public lodging, and Mayport Village's
commercial inventory is addressed ATLANTIC BEACH 32233. Mayport is therefore an OVERLAY inside
`atlantic-neptune-beach-mayport`, never a corridor -- a measurement, not a preference. The same measurement
refuses an NAS Jacksonville corridor: 32212 carries zero lodging licences.

NO MEDICAL CORRIDOR, EITHER
---------------------------
Mayo Clinic Jacksonville sits on San Pablo Road in 32224, which carries 6 hotel-rank licences and is claimed in
full by `deerwood-park-mayo-unf` alongside the University of North Florida and Tinseltown. Medical demand is a
DEMAND DRIVER, which informs a corridor's description and never alters a premises identity.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/jacksonville_fl.json
  launch_packages/pettripfinder/markets/proposed/jacksonville-fl.json
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_geography_001.json
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_corridor_registry_001.json
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

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "jacksonville_fl.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "jacksonville-fl.json")
REPORT_OUT = os.path.join(REPORTS, "jacksonville_fl_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "jacksonville_fl_corridor_registry_001.json")
AS_OF = "2026-09-25"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown-jacksonville", "Downtown Jacksonville", "Downtown Jacksonville", "CORE", "jacksonville",
     ["32202", "32206"],
     "The Northbank: Laura Street and the Jacksonville Landing site, the Hyatt Regency and Omni riverfront "
     "blocks, the Prime F. Osborn III Convention Center, VyStar Veterans Memorial Arena, EverBank Stadium and "
     "the sports complex, the Northbank Riverwalk, the Main Street and Acosta bridges, the Springfield historic "
     "district and the Eastside. The Southbank is across the river and is its own corridor."),
    ("southbank-san-marco", "Southbank / San Marco", "Southbank & San Marco", "CORE", "jacksonville",
     ["32207"],
     "The Southbank and San Marco: the Southbank Riverwalk and Friendship Fountain, the Museum of Science and "
     "History, the riverfront hotel blocks on Riverplace Boulevard and Prudential Drive, San Marco Square and "
     "Hendricks Avenue, Baptist Medical Center Jacksonville and Wolfson Children's Hospital, and the St. Nicholas "
     "and Philips Highway approaches. Thirteen hotel-rank lodging licences on one postal code."),
    ("riverside-avondale-brooklyn", "Riverside / Avondale / Brooklyn", "Riverside & Avondale", "CORE",
     "jacksonville",
     ["32204", "32205"],
     "Riverside, Avondale, Brooklyn and Murray Hill: Five Points, the King Street and Park Street districts, "
     "Riverside Avenue and Unity Plaza, the Cummer Museum, Memorial Park, the Shoppes of Avondale and Ascension "
     "St. Vincent's Riverside. Jacksonville's historic walkable west-of-downtown quarter."),
    ("jax-airport-northside", "Jacksonville International Airport / Northside",
     "JAX Airport & the Northside", "CORE", "jacksonville",
     ["32208", "32209", "32218", "32219", "32226"],
     "The market's largest lodging cluster: Jacksonville International Airport (JAX) on Airport Center Drive and "
     "Duval Road, the Airport Road and Dunn Avenue hotel rows, River City Marketplace at I-95 and Airport Road, "
     "the I-95 / I-295 north interchange, Oceanway, Dames Point and the JAXPORT Blount Island and Dames Point "
     "cruise and container terminals, Busch Gardens-bound US-17 traffic, and the Norwood, Golfair, Moncrief and "
     "Dinsmore blocks of north and northwest Jacksonville. 32218 alone carries 29 hotel-rank lodging licences."),
    ("westside-i10-i295", "Westside / I-10 & I-295", "The Westside", "CORE", "jacksonville",
     ["32210", "32212", "32220", "32221", "32222", "32234", "32244", "32254"],
     "West and southwest Jacksonville: the I-10 Cassat Avenue, Lane Avenue and Chaffee Road interchanges, the "
     "Commonwealth Avenue and Normandy Boulevard motel rows, 103rd Street and Jacksonville Heights, Ortega and "
     "the Roosevelt Boulevard approach, Argyle and the Duval half of Oakleaf, NAS Jacksonville (32212, which "
     "carries no public-lodging licence and is an overlay), Cecil Commerce Center and the town of Baldwin on "
     "US-301 at I-10."),
    ("arlington-intracoastal-west", "Arlington / Intracoastal West", "Arlington & Intracoastal West", "CORE",
     "jacksonville",
     ["32211", "32225", "32277"],
     "East of the river and north of the Arlington Expressway: Arlington Road and University Boulevard North, "
     "Regency Square, Fort Caroline and the Timucuan Preserve, Girvin Road, Monument Road and the Intracoastal "
     "West blocks on Atlantic Boulevard, the Wonderwood Connector and the Mathews and Hart bridges."),
    ("southside-university-boulevard", "Southside / University Boulevard", "Southside", "CORE", "jacksonville",
     ["32216"],
     "The inner Southside: the University Boulevard and Bowden Road hotel rows, the Philips Highway motel strip, "
     "Spring Park, Lakewood, the Beach Boulevard and Southside Boulevard junctions and the Tinseltown-bound "
     "approaches. Eighteen hotel-rank lodging licences on one postal code -- the market's oldest motor-court row."),
    ("st-johns-town-center-gate-parkway", "St. Johns Town Center / Gate Parkway",
     "St. Johns Town Center", "CORE", "jacksonville",
     ["32246"],
     "St. Johns Town Center and the Gate Parkway retail and hotel district: Town Center Parkway, Big Island "
     "Drive, the Beach Boulevard and Southside Boulevard retail spine, Tinseltown, and the J. Turner Butler "
     "Boulevard (SR-202) interchange traffic between downtown and the beaches."),
    ("deerwood-baymeadows", "Deerwood / Baymeadows", "Deerwood & Baymeadows", "CORE", "jacksonville",
     ["32217", "32256"],
     "The Baymeadows and Deerwood business district: Baymeadows Road and the Baymeadows Way hotel row, the "
     "Philips Highway and I-95 Southside interchanges, Gate Parkway West, Deerwood Park's office campuses, "
     "Southpoint and the Butler Boulevard corporate corridor, and Lakewood south to the Bowden line. "
     "Twenty-six hotel-rank lodging licences -- the market's second-largest corridor."),
    ("deerwood-park-mayo-unf", "Deerwood Park / Mayo Clinic / UNF", "Mayo Clinic & UNF", "CORE", "jacksonville",
     ["32224"],
     "East Southside: Mayo Clinic Jacksonville on San Pablo Road, the University of North Florida, Deerwood Park "
     "North and the Town Center's eastern approaches, Kernan Boulevard, the Butler Boulevard run to the beaches "
     "and the Intracoastal crossing. Mayo Clinic's patient-and-family demand is a DEMAND DRIVER reported here; "
     "it never alters a premises identity."),
    ("mandarin-bartram-julington-creek", "Mandarin / Bartram Park / Julington Creek",
     "Mandarin & Bartram Park", "CORE", "jacksonville",
     ["32223", "32257", "32258", "32259"],
     "South Jacksonville along the St. Johns River: Mandarin's San Jose Boulevard (SR-13) and Old St. Augustine "
     "Road, Bartram Park and the I-95 Race Track Road interchange, and -- across Julington Creek in ST. JOHNS "
     "COUNTY -- Fruit Cove, Julington Creek Plantation and the SR-13 river road. 32259 is a St. Johns County "
     "postal code admitted here because its lodging faces Mandarin, not St. Augustine; it is named in the "
     "county boundary audit."),
    ("jacksonville-beach", "Jacksonville Beach", "Jacksonville Beach", "CORE", "jacksonville beach",
     ["32250"],
     "The City of Jacksonville Beach: the Jacksonville Beach Pier, Beach Boulevard and 3rd Street (A1A), the "
     "oceanfront hotel blocks, Beaches Town Center at the Neptune Beach line, Latham Plaza and the Butler "
     "Boulevard beach approach. Sixteen hotel-rank lodging licences -- a separate municipality inside Duval "
     "County, never generic 'Jacksonville'."),
    ("atlantic-neptune-beach-mayport", "Atlantic Beach / Neptune Beach / Mayport",
     "Atlantic & Neptune Beach", "CORE", "atlantic beach",
     ["32227", "32228", "32233", "32266"],
     "The two northern beach municipalities and the river mouth: Atlantic Beach's Atlantic Boulevard and Mayport "
     "Road, Neptune Beach and the Beaches Town Center, Hanna Park, Mayport Village and the St. Johns River "
     "Ferry, and Naval Station Mayport. 32227 and 32228 carry ZERO public-lodging licences, so Mayport is an "
     "overlay on 32233 and never a corridor."),
    ("ponte-vedra-beach-sawgrass", "Ponte Vedra Beach / Sawgrass", "Ponte Vedra Beach", "CORRIDOR",
     "ponte vedra beach",
     ["32081", "32082"],
     "The next beach south of Jacksonville Beach on A1A, in ST. JOHNS COUNTY: Ponte Vedra Beach's oceanfront "
     "resorts, the Ponte Vedra Inn & Club and the Lodge & Club, Sawgrass and TPC Sawgrass (THE PLAYERS "
     "Championship), the Sawgrass Village and A1A / Solana Road blocks, and Nocatee. Admitted at CORRIDOR tier "
     "because it is contiguous with Jacksonville Beach and its resorts route through JAX -- not because it is "
     "St. Johns County, whose St. Augustine codes are refused entirely."),
    ("orange-park-fleming-island", "Orange Park / Fleming Island", "Orange Park & Fleming Island", "CORRIDOR",
     "orange park",
     ["32003", "32043", "32065", "32068", "32073"],
     "CLAY COUNTY's Jacksonville commuter suburbs: Orange Park's Blanding Boulevard and Wells Road hotel row, "
     "Park Avenue and US-17, Fleming Island and the Eagle Harbour and Town Center blocks, the Clay half of "
     "Oakleaf, Middleburg on SR-21, Green Cove Springs and the Shands Bridge approach, and Naval Air Station "
     "Jacksonville's southern gate traffic."),
    ("amelia-island-fernandina-beach", "Amelia Island / Fernandina Beach", "Amelia Island", "CORRIDOR",
     "fernandina beach",
     ["32034", "32035"],
     "NASSAU COUNTY's barrier island: Fernandina Beach's Centre Street historic district and the downtown "
     "waterfront, South Fletcher Avenue (A1A) oceanfront, the Ritz-Carlton Amelia Island and Omni Amelia Island "
     "Resort campuses, Amelia Island Plantation, Fort Clinch and the Georgia line at the St. Marys River. "
     "Thirty-two hotel-rank lodging licences against 1,130 Nassau County resort-condominium licences: the "
     "island's rental stock is overwhelmingly condominium inventory that never enters this census."),
    ("yulee-nassau-i95", "Yulee / Callahan / Hilliard", "Yulee & rural Nassau", "FRINGE", "yulee",
     ["32011", "32046", "32097"],
     "Mainland NASSAU COUNTY: Yulee at the I-95 exit 373 / SR-200 Amelia Island gateway and Wildlight, Callahan "
     "at US-1 and US-301, and Hilliard on US-1 at the Georgia line. Ten hotel-rank lodging licences across an "
     "interchange-and-rural row, admitted at FRINGE so Nassau County's mainland inventory is ACCOUNTED FOR "
     "rather than silently dropped, and far below any publication threshold."),
]

OUTSIDE = [
    ("St. Augustine / St. Augustine Beach / World Golf Village / Hastings -- St. Johns County", "FL",
     ["32033", "32080", "32084", "32085", "32086", "32092", "32095", "32145"],
     "St. Johns County's historic-coast codes; FUTURE_STANDALONE st-augustine-fl. REFUSED ENTIRELY and by name. "
     "The state's own register makes this a market-scale refusal rather than a judgement call: 32084 carries 78 "
     "hotel-rank lodging licences, 32080 (St. Augustine Beach) 29 and 32092 (World Golf Village) 9 -- 116 in "
     "total, a larger hotel-rank inventory than most PetTripFinder markets publish. St. Augustine is the "
     "nation's oldest city, has its own CVB (Florida's Historic Coast), its own 1.5-million-visitor historic "
     "district and its own resort golf destination at World Golf Village. Absorbing it would destroy a future "
     "market rather than extend this one. Ponte Vedra Beach 32082 is the ONE St. Johns County coastal code "
     "admitted here, and 32259 the one inland code, each for its own stated reason."),
    ("Palm Coast / Flagler Beach / Bunnell -- Flagler County", "FL",
     ["32110", "32135", "32136", "32137", "32142", "32143", "32164"],
     "Flagler County; FUTURE_STANDALONE palm-coast-flagler-fl (or a future Daytona market's northern corridor). "
     "Refused by name. Sixty miles south of downtown Jacksonville and closer to Daytona Beach than to JAX; 26 "
     "hotel-rank lodging licences of its own, and a lodging register dominated by 676 resort-condominium and "
     "775 vacation-dwelling licences."),
    ("Daytona Beach / Ormond Beach / DeLand -- Volusia County", "FL",
     ["32114", "32117", "32118", "32119", "32124", "32127", "32128", "32129", "32130", "32132", "32168", "32169",
      "32174", "32176", "32180", "32190", "32198", "32720", "32724", "32725", "32738", "32744", "32746", "32763",
      "32764"],
     "Volusia County; FUTURE_STANDALONE daytona-beach-fl. Refused by name; a separate Atlantic beach market with "
     "its own CVB, its own speedway demand and 236 hotel-rank lodging licences."),
    ("Gainesville / Alachua County", "FL",
     ["32601", "32603", "32605", "32606", "32607", "32608", "32609", "32610", "32612", "32615", "32618", "32631",
      "32640", "32641", "32643", "32653", "32667", "32669", "32694"],
     "Alachua County; FUTURE_STANDALONE gainesville-fl. Refused by name; a separate university market 70 miles "
     "southwest on I-75, with 69 hotel-rank lodging licences of its own."),
    ("Palatka / Crescent City / East Palatka -- Putnam County", "FL",
     ["32112", "32131", "32139", "32140", "32148", "32177", "32178", "32181", "32187", "32189", "32193"],
     "Putnam County; OUTSIDE by name. A rural St. Johns River county on SR-100 between Gainesville and St. "
     "Augustine, with 19 hotel-rank lodging licences, no Jacksonville traveller system and no CVB of its own."),
    ("Macclenny / Glen St. Mary -- Baker County", "FL",
     ["32063", "32040", "32087"],
     "Baker County; OUTSIDE by name. A rural I-10 county west of Baldwin with 5 hotel-rank lodging licences on "
     "the interstate. The market's western line is Duval's own 32234 (Baldwin); Baker's interchange motels are "
     "refused by the line, not by distance."),
    ("Keystone Heights / inland Clay County lake country", "FL",
     ["32656", "32640"],
     "Clay County lake country; OUTSIDE by name, and the market's own proof that COUNTY INCLUSION IS NOT "
     "TRAVELLER-MARKET INCLUSION. Keystone Heights is 45 miles southwest of downtown Jacksonville on SR-21 in "
     "the Trail Ridge lake district, oriented to Gainesville, and carries 1 hotel-rank lodging licence. Clay "
     "County's Jacksonville-facing codes (Orange Park, Fleming Island, Middleburg, Green Cove Springs, Oakleaf) "
     "ARE admitted; this one is not."),
    ("Kingsland / St. Marys / Camden County, Georgia", "GA",
     ["31548", "31558", "31565", "31569"],
     "GEORGIA, Camden County; OUTSIDE by name and by state. Kingsland's I-95 exit 3 and exit 6 interchange "
     "motels are 20 minutes from Yulee and market to Cumberland Island and Naval Submarine Base Kings Bay, not "
     "to Jacksonville. Florida DBPR does not license them and no corridor admits them. A future "
     "golden-isles-ga / coastal-georgia market's territory."),
    ("Brunswick / St. Simons Island / Jekyll Island / Golden Isles, Georgia", "GA",
     ["31520", "31521", "31522", "31523", "31525", "31527", "31561"],
     "GEORGIA, Glynn County; FUTURE_STANDALONE golden-isles-ga. Refused by name and by state; its own island "
     "resort market with its own CVB."),
    ("Savannah / Chatham County, Georgia", "GA",
     ["31401", "31404", "31405", "31406", "31407", "31408", "31409", "31410", "31411", "31415", "31419", "31421",
      "31322", "31324", "31326", "31328"],
     "GEORGIA, Chatham County; EXISTING_LIVE_MARKET savannah-ga (live as production market #27). Owns every "
     "Chatham County postal code. Admitting any of them would publish one hotel in two markets."),
    ("Orlando / Central Florida", "FL",
     ["32801", "32803", "32804", "32805", "32806", "32807", "32808", "32809", "32810", "32811", "32812", "32814",
      "32817", "32818", "32819", "32821", "32822", "32824", "32825", "32826", "32827", "32828", "32829", "32830",
      "32831", "32832", "32835", "32836", "32837", "32839", "32789", "32792", "32751", "32746", "32771", "32773",
      "34741", "34743", "34744", "34746", "34747", "34787"],
     "EXISTING_LIVE_MARKET orlando-fl (live as production market #28). Central Florida is 140 miles south on "
     "I-95 / I-4 and is already published. Refused by name."),
    ("Jacksonville, NORTH CAROLINA -- Onslow County", "NC",
     ["28540", "28541", "28543", "28544", "28545", "28546", "28547"],
     "A DIFFERENT PLACE AND A DIFFERENT STATE. EXISTING_LIVE_MARKET jacksonville-nc (live as production market "
     "#22): Jacksonville, Onslow County, North Carolina -- Camp Lejeune, Marine Corps Air Station New River, "
     "Western Boulevard. Named here because every national chain publishes near-identically named hotels in both "
     "cities, and because a generic chain-name flag raised in EITHER market must never hold a row in the other. "
     "Separation is by state code, postal code, street and brand property code; never by the word "
     "'Jacksonville'."),
]

#: County-level boundary for the registry lane (DBPR states each licence's county). Four Florida counties carry
#: admitted corridors; every other county row is OUTSIDE by county before any ZIP lookup.
ADMITTED_COUNTIES = {"duval", "clay", "nassau", "st. johns", "st johns"}
OBSERVED_COUNTIES = OrderedDict([
    ("baker", "(none -- rural I-10, refused by name)"),
    ("putnam", "(none -- rural St. Johns River, refused by name)"),
    ("flagler", "palm-coast-flagler-fl"),
    ("volusia", "daytona-beach-fl"),
    ("alachua", "gainesville-fl"),
    ("chatham", "savannah-ga"),
    ("glynn", "golden-isles-ga"),
    ("camden", "golden-isles-ga"),
])

#: The county-line rulings the order's Phase 4 clause demands, each answered on the state's own register.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("duval", OrderedDict([
        ("ruling", "ADMITTED WHOLE -- every Duval County postal code that carries a lodging licence is claimed by "
                   "exactly one corridor. Duval is a CONSOLIDATED city-county, so 'JACKSONVILLE' is the postal "
                   "city for 25 lodging-bearing codes across 39 miles and places nothing by itself."),
        ("corridors", "downtown-jacksonville, southbank-san-marco, riverside-avondale-brooklyn, "
                      "jax-airport-northside, westside-i10-i295, arlington-intracoastal-west, "
                      "southside-university-boulevard, st-johns-town-center-gate-parkway, deerwood-baymeadows, "
                      "deerwood-park-mayo-unf, mandarin-bartram-julington-creek (Duval part), "
                      "jacksonville-beach, atlantic-neptune-beach-mayport"),
        ("separate_municipalities_inside_duval",
         "Jacksonville Beach, Neptune Beach, Atlantic Beach and Baldwin are separate municipalities INSIDE Duval "
         "County with their own postal codes; each is placed by its own code, never by 'Jacksonville'."),
    ])),
    ("st. johns", OrderedDict([
        ("ruling", "SPLIT, and this is the market's hardest boundary call. TWO codes admitted (32082 Ponte Vedra "
                   "Beach and 32081 Nocatee at CORRIDOR tier; 32259 Fruit Cove / Julington Creek inside the "
                   "Mandarin corridor). EVERY St. Augustine code REFUSED by name."),
        ("why_ponte_vedra_is_admitted",
         "Ponte Vedra Beach is the next beach south of Jacksonville Beach on A1A with no gap between them; its "
         "resorts (Ponte Vedra Inn & Club, the Lodge & Club, Sawgrass Marriott, TPC Sawgrass) route their guests "
         "through JAX, 25 miles north, and their traveller flow is the Butler Boulevard / A1A beaches flow. It "
         "carries 6 hotel-rank lodging licences."),
        ("why_julington_creek_is_admitted",
         "32259's Fruit Cove / Julington Creek lodging faces Duval's Mandarin across Julington Creek on SR-13 and "
         "Race Track Road, 20 miles from downtown St. Augustine and 15 from downtown Jacksonville. It carries "
         "ZERO hotel-rank lodging licences on the state's own record, so it is admitted for completeness of the "
         "Mandarin corridor and contributes no census row."),
        ("why_st_augustine_is_refused",
         "116 hotel-rank lodging licences across 32084 (78), 32080 (29) and 32092 (9); its own CVB (Florida's "
         "Historic Coast); its own historic-district and World Golf Village travel products. FUTURE_STANDALONE "
         "st-augustine-fl. County inclusion is not traveller-market inclusion, and the order forbids absorbing "
         "it automatically."),
        ("cvb_fact_recorded_against_the_traveller_fact",
         "Florida's Historic Coast markets Ponte Vedra together with St. Augustine, so the CVB test and the "
         "traveller test DISAGREE for 32082. The traveller test governs and the disagreement is recorded rather "
         "than hidden: Ponte Vedra Beach is contiguous with Jacksonville Beach and shares its airport, while "
         "St. Augustine is 40 miles further south with an inventory large enough to be its own market."),
    ])),
    ("clay", OrderedDict([
        ("ruling", "SPLIT. The Jacksonville-facing codes (32073 Orange Park, 32003 Fleming Island, 32065 Oakleaf, "
                   "32068 Middleburg, 32043 Green Cove Springs) ADMITTED at CORRIDOR tier -- 17 hotel-rank "
                   "lodging licences. The inland lake country (32656 Keystone Heights, 1 licence) REFUSED by "
                   "name."),
        ("why", "Orange Park is a Blanding Boulevard / US-17 commuter suburb continuous with Duval's westside and "
                "its hotels serve NAS Jacksonville and Jacksonville business travel. Keystone Heights is 45 miles "
                "southwest in the Trail Ridge lake district and is oriented to Gainesville. This split is the "
                "market's own demonstration that a county is not a travel market."),
    ])),
    ("nassau", OrderedDict([
        ("ruling", "ADMITTED, SPLIT BY TIER. Amelia Island / Fernandina Beach (32034, 32035) at CORRIDOR tier -- "
                   "32 hotel-rank lodging licences. The mainland row (32097 Yulee, 32011 Callahan, 32046 "
                   "Hilliard) at FRINGE -- 10 licences."),
        ("amelia_island_classification", "CORRIDOR -- not FRINGE and not FUTURE_STANDALONE. The order requires an "
                                         "explicit choice among those three and this is it."),
        ("why_corridor",
         "Nassau County is inside the Jacksonville metropolitan statistical area; JAX is Amelia Island's airport "
         "(30 miles, no closer commercial field); the A1A / I-95 exit 373 approach is a Jacksonville traveller "
         "flow; and 32 hotel-rank licences is real, coherent inventory that no other market publishes. Admitting "
         "it at CORRIDOR tier ACCOUNTS FOR that inventory instead of silently dropping it."),
        ("future_optionality_preserved_explicitly",
         "Amelia Island is this market's NAMED first candidate for a future standalone market: it has its own "
         "CVB (the Amelia Island Convention & Visitors Bureau), its own county, its own island resort identity "
         "and two flagship resort campuses. The classification is recorded here so a founder can promote it "
         "later on the record rather than discovering the question after publication. It is admitted at CORRIDOR "
         "tier, not CORE, for exactly that reason."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / club-member only).
NONPUBLIC_NAMES = {
    "navy lodge": "US Navy billeting -- not public lodging",
    "navy gateway inns": "US Navy billeting -- not public lodging",
    "navy gateway inns & suites": "US Navy billeting -- not public lodging",
    "navy gateway inns and suites": "US Navy billeting -- not public lodging",
    "nas jacksonville navy lodge": "US Navy billeting -- not public lodging",
    "naval station mayport navy lodge": "US Navy billeting -- not public lodging",
}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-jacksonville", "Jacksonville", "Downtown Jacksonville", 30.3270, -81.6560, 3000, True),
    ("southbank-san-marco", "Jacksonville", "Southbank / San Marco", 30.3150, -81.6540, 3400, True),
    ("riverside-avondale-brooklyn", "Jacksonville", "Riverside / Avondale / Brooklyn",
     30.3080, -81.6900, 3800, True),
    ("jax-airport-northside", "Jacksonville", "JAX Airport / Northside", 30.4500, -81.6550, 11000, True),
    ("westside-i10-i295", "Jacksonville", "Westside / I-10 & I-295", 30.2850, -81.7800, 11000, True),
    ("arlington-intracoastal-west", "Jacksonville", "Arlington / Intracoastal West",
     30.3400, -81.5550, 7000, True),
    ("southside-university-boulevard", "Jacksonville", "Southside / University Boulevard",
     30.2880, -81.6000, 3800, True),
    ("st-johns-town-center-gate-parkway", "Jacksonville", "St. Johns Town Center / Gate Parkway",
     30.2580, -81.5280, 4200, True),
    ("deerwood-baymeadows", "Jacksonville", "Deerwood / Baymeadows", 30.2250, -81.5700, 5200, True),
    ("deerwood-park-mayo-unf", "Jacksonville", "Deerwood Park / Mayo Clinic / UNF",
     30.2620, -81.4620, 4800, True),
    ("mandarin-bartram-julington-creek", "Jacksonville", "Mandarin / Bartram Park / Julington Creek",
     30.1550, -81.6150, 8000, True),
    ("jacksonville-beach", "Jacksonville Beach", "Jacksonville Beach", 30.2880, -81.3950, 3200, True),
    ("atlantic-neptune-beach-mayport", "Atlantic Beach", "Atlantic Beach / Neptune Beach / Mayport",
     30.3420, -81.4000, 5000, True),
    ("ponte-vedra-beach-sawgrass", "Ponte Vedra Beach", "Ponte Vedra Beach / Sawgrass",
     30.2250, -81.3800, 6500, True),
    ("orange-park-fleming-island", "Orange Park", "Orange Park / Fleming Island", 30.1400, -81.7300, 11000, True),
    ("amelia-island-fernandina-beach", "Fernandina Beach", "Amelia Island / Fernandina Beach",
     30.6450, -81.4550, 9000, True),
    ("yulee-nassau-i95", "Yulee", "Yulee / Callahan / Hilliard", 30.6300, -81.6800, 14000, True),
    ("obs-st-augustine-line", "Saint Augustine",
     "St. Augustine / St. Augustine Beach / World Golf Village -- OBSERVATION ONLY (future standalone)",
     29.9000, -81.3300, 14000, False),
    ("obs-palm-coast", "Palm Coast", "Palm Coast / Flagler Beach -- OBSERVATION ONLY (Flagler County)",
     29.5700, -81.2200, 12000, False),
    ("obs-macclenny-baker", "Macclenny", "Macclenny / Baker County -- OBSERVATION ONLY (rural I-10)",
     30.2800, -82.1200, 9000, False),
    ("obs-kingsland-ga", "Kingsland", "Kingsland / St. Marys, GEORGIA -- OBSERVATION ONLY (out of state)",
     30.8000, -81.6900, 10000, False),
    ("obs-palatka-putnam", "Palatka", "Palatka / Putnam County -- OBSERVATION ONLY (rural)",
     29.6500, -81.6400, 9000, False),
]

BOUNDS = {"min_lat": 29.52, "max_lat": 30.92, "min_lng": -82.28, "max_lng": -81.18}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Downtown Jacksonville", 30.3270, -81.6560, 1.8),
    ("Northbank Riverwalk", 30.3230, -81.6600, 1.2),
    ("Prime Osborn Convention Center", 30.3230, -81.6780, 0.9),
    ("EverBank Stadium / sports complex", 30.3240, -81.6370, 1.2),
    ("VyStar Veterans Memorial Arena", 30.3250, -81.6400, 0.8),
    ("Springfield historic district", 30.3450, -81.6540, 1.4),
    ("Southbank", 30.3200, -81.6570, 1.2),
    ("San Marco Square", 30.3060, -81.6480, 1.2),
    ("Baptist Medical Center Jacksonville", 30.3150, -81.6620, 0.9),
    ("Riverside / Five Points", 30.3180, -81.6820, 1.4),
    ("Avondale / Shoppes of Avondale", 30.3010, -81.7000, 1.4),
    ("Brooklyn / Unity Plaza", 30.3180, -81.6720, 0.9),
    ("Murray Hill", 30.3060, -81.7180, 1.4),
    ("Jacksonville International Airport (JAX)", 30.4941, -81.6879, 3.5),
    ("Airport Center Drive / Duval Road", 30.4800, -81.6600, 2.2),
    ("River City Marketplace", 30.4650, -81.6320, 1.6),
    ("Dunn Avenue", 30.4180, -81.6720, 2.6),
    ("Oceanway", 30.4600, -81.6100, 3.0),
    ("Dames Point / JAXPORT cruise terminal", 30.3900, -81.5600, 3.0),
    ("Blount Island / JAXPORT", 30.4080, -81.5300, 3.0),
    ("Norwood / Golfair", 30.3700, -81.6700, 2.4),
    ("Moncrief / New Town", 30.3600, -81.7000, 2.4),
    ("Dinsmore / Whitehouse", 30.4200, -81.7600, 4.0),
    ("Arlington / Regency Square", 30.3260, -81.5800, 2.6),
    ("Fort Caroline / Timucuan Preserve", 30.3850, -81.5000, 3.0),
    ("Intracoastal West / Girvin Road", 30.3200, -81.4800, 3.0),
    ("University Boulevard, Southside", 30.2900, -81.6000, 2.4),
    ("Philips Highway", 30.2600, -81.5900, 4.0),
    ("Bowden Road / Spring Park", 30.2820, -81.6100, 2.0),
    ("St. Johns Town Center", 30.2580, -81.5230, 1.8),
    ("Big Island Drive / Town Center Parkway", 30.2570, -81.5280, 1.2),
    ("Tinseltown", 30.2400, -81.5470, 1.4),
    ("Beach Boulevard / Southside Boulevard", 30.2870, -81.5480, 2.4),
    ("Baymeadows Road", 30.2200, -81.5900, 2.6),
    ("Deerwood Park / Southpoint", 30.2380, -81.5580, 2.4),
    ("J. Turner Butler Boulevard corridor", 30.2470, -81.5100, 4.0),
    ("Gate Parkway", 30.2480, -81.5380, 2.0),
    ("Mayo Clinic Jacksonville", 30.2660, -81.4400, 1.6),
    ("University of North Florida", 30.2700, -81.5100, 1.8),
    ("Kernan Boulevard", 30.2800, -81.4900, 2.4),
    ("Mandarin / San Jose Boulevard", 30.1650, -81.6300, 3.4),
    ("Old St. Augustine Road", 30.1900, -81.5900, 3.0),
    ("Bartram Park", 30.1350, -81.5650, 2.6),
    ("Julington Creek / Fruit Cove", 30.1100, -81.6200, 4.0),
    ("Jacksonville Beach Pier", 30.2870, -81.3930, 1.2),
    ("3rd Street / A1A, Jacksonville Beach", 30.2850, -81.4000, 2.6),
    ("Beaches Town Center", 30.3130, -81.3960, 1.0),
    ("Atlantic Beach", 30.3340, -81.3980, 2.0),
    ("Neptune Beach", 30.3140, -81.3980, 1.4),
    ("Mayport Road", 30.3600, -81.4200, 2.6),
    ("Mayport Village / St. Johns River Ferry", 30.3930, -81.4300, 1.6),
    ("Naval Station Mayport", 30.3900, -81.4250, 2.6),
    ("Hanna Park", 30.3600, -81.4000, 1.6),
    ("Ponte Vedra Beach", 30.2400, -81.3860, 3.0),
    ("TPC Sawgrass / Sawgrass Village", 30.1980, -81.3950, 2.2),
    ("A1A / Solana Road", 30.2300, -81.3880, 2.0),
    ("Nocatee", 30.1150, -81.4100, 4.0),
    ("Orange Park / Blanding Boulevard", 30.1660, -81.7060, 3.4),
    ("Wells Road", 30.1730, -81.7070, 1.2),
    ("Fleming Island", 30.0930, -81.7130, 3.4),
    ("Oakleaf", 30.1750, -81.8000, 3.4),
    ("Middleburg", 30.0660, -81.8600, 3.4),
    ("Green Cove Springs", 29.9920, -81.6780, 3.4),
    ("NAS Jacksonville", 30.2350, -81.6800, 3.0),
    ("Cecil Commerce Center", 30.2200, -81.8700, 4.0),
    ("Cassat Avenue / I-10", 30.3000, -81.7300, 2.2),
    ("Lane Avenue / I-10", 30.3050, -81.7600, 2.2),
    ("Commonwealth Avenue", 30.3200, -81.7500, 3.0),
    ("Normandy Boulevard", 30.2900, -81.8000, 4.0),
    ("103rd Street / Jacksonville Heights", 30.2500, -81.7800, 4.0),
    ("Ortega / Roosevelt Boulevard", 30.2600, -81.7200, 3.0),
    ("Baldwin / US-301 at I-10", 30.3030, -81.9750, 3.4),
    ("Centre Street, Fernandina Beach", 30.6700, -81.4640, 1.2),
    ("South Fletcher Avenue / A1A, Amelia Island", 30.6100, -81.4400, 4.0),
    ("Omni Amelia Island Resort", 30.5750, -81.4450, 2.2),
    ("Ritz-Carlton Amelia Island", 30.5900, -81.4430, 1.4),
    ("Amelia Island Plantation", 30.5750, -81.4470, 2.2),
    ("Fort Clinch", 30.7000, -81.4550, 1.6),
    ("Yulee / SR-200 at I-95", 30.6330, -81.6060, 3.4),
    ("Wildlight", 30.6600, -81.5700, 2.6),
    ("Callahan", 30.5620, -81.8300, 3.0),
    ("Hilliard", 30.6900, -81.9200, 3.0),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Jacksonville International Airport (JAX)", re.compile(
        r"\bairport (center|rd|road|entrance)\b|\bduval rd\b|\bdixie clipper\b|\bpecan park rd\b", re.I)),
    ("River City Marketplace", re.compile(r"\briver city\b|\bmax leggett\b", re.I)),
    ("Dunn Avenue", re.compile(r"\bdunn ave\b", re.I)),
    ("Northbank Riverwalk", re.compile(r"\bindependent dr\b|\bcoastline dr\b|\bwater st\b", re.I)),
    ("Prime Osborn Convention Center", re.compile(r"\bw bay st\b|\bwest bay st\b|\bjohnson st\b", re.I)),
    ("Southbank", re.compile(r"\briverplace b(lv)?d\b|\bprudential dr\b|\bflagler ave\b", re.I)),
    ("San Marco Square", re.compile(r"\bsan marco b(lv)?d\b|\bhendricks ave\b|\blasalle st\b", re.I)),
    ("Riverside / Five Points", re.compile(r"\briverside ave\b|\bpark st\b|\bmargaret st\b|\bking st\b", re.I)),
    ("Brooklyn / Unity Plaza", re.compile(r"\bmay st\b|\bjackson st\b|\bforest st\b", re.I)),
    ("Avondale / Shoppes of Avondale", re.compile(r"\bst johns ave\b|\bsaint johns ave\b", re.I)),
    ("Arlington / Regency Square", re.compile(r"\barlington expy\b|\buniversity b(lv)?d n\b|\bregency\b", re.I)),
    ("Intracoastal West / Girvin Road", re.compile(r"\bgirvin rd\b|\bmonument rd\b|\bwonderwood\b", re.I)),
    ("University Boulevard, Southside", re.compile(r"\buniversity b(lv)?d w\b|\buniversity blvd\b", re.I)),
    ("Philips Highway", re.compile(r"\bphilips hwy\b|\bphillips hwy\b", re.I)),
    ("Bowden Road / Spring Park", re.compile(r"\bbowden rd\b|\bspring park rd\b|\bsalisbury rd\b", re.I)),
    ("St. Johns Town Center", re.compile(r"\btown center pkwy\b|\bbig island dr\b|\bmidtown pkwy\b", re.I)),
    ("Beach Boulevard / Southside Boulevard", re.compile(r"\bbeach b(lv)?d\b|\bsouthside b(lv)?d\b", re.I)),
    ("Baymeadows Road", re.compile(r"\bbaymeadows (rd|way|cir)\b", re.I)),
    ("Deerwood Park / Southpoint", re.compile(r"\bsouthpoint\b|\bdeerwood park\b|\bcorporate sq\b", re.I)),
    ("J. Turner Butler Boulevard corridor", re.compile(r"\bbutler b(lv)?d\b|\bj turner butler\b", re.I)),
    ("Gate Parkway", re.compile(r"\bgate p(k|ar)kwy\b|\bgate pkwy\b", re.I)),
    ("Mayo Clinic Jacksonville", re.compile(r"\bsan pablo rd\b|\bmayo clinic\b", re.I)),
    ("University of North Florida", re.compile(r"\bkernan b(lv)?d\b|\bunf dr\b", re.I)),
    ("Mandarin / San Jose Boulevard", re.compile(r"\bsan jose b(lv)?d\b", re.I)),
    ("Old St. Augustine Road", re.compile(r"\bold st(\.)? augustine rd\b|\bold saint augustine rd\b", re.I)),
    ("Bartram Park", re.compile(r"\bbartram\b|\brace track rd\b", re.I)),
    ("3rd Street / A1A, Jacksonville Beach", re.compile(r"\b(n|s|north|south)? ?3rd st\b|\bfirst st\b|\b1st st\b", re.I)),
    ("Beaches Town Center", re.compile(r"\batlantic b(lv)?d\b(?=.*beach)|\bahern st\b", re.I)),
    ("Mayport Road", re.compile(r"\bmayport rd\b", re.I)),
    ("Mayport Village / St. Johns River Ferry", re.compile(r"\bocean st\b|\bmayport village\b", re.I)),
    ("Ponte Vedra Beach", re.compile(r"\bponte vedra b(lv)?d\b|\bsolana rd\b", re.I)),
    ("TPC Sawgrass / Sawgrass Village", re.compile(r"\bsawgrass\b|\btpc b(lv)?d\b", re.I)),
    ("Orange Park / Blanding Boulevard", re.compile(r"\bblanding b(lv)?d\b|\bwells rd\b|\bpark ave\b", re.I)),
    ("Fleming Island", re.compile(r"\bfleming island\b|\beagle harbo(u)?r\b", re.I)),
    ("Cassat Avenue / I-10", re.compile(r"\bcassat ave\b", re.I)),
    ("Lane Avenue / I-10", re.compile(r"\blane ave\b", re.I)),
    ("Commonwealth Avenue", re.compile(r"\bcommonwealth ave\b", re.I)),
    ("Normandy Boulevard", re.compile(r"\bnormandy b(lv)?d\b", re.I)),
    ("103rd Street / Jacksonville Heights", re.compile(r"\b103(rd)? st\b", re.I)),
    ("Ortega / Roosevelt Boulevard", re.compile(r"\broosevelt b(lv)?d\b", re.I)),
    ("Centre Street, Fernandina Beach", re.compile(r"\bcentre st\b|\bs 8th st\b|\bash st\b", re.I)),
    ("South Fletcher Avenue / A1A, Amelia Island", re.compile(r"\bfletcher ave\b|\bamelia island p(k|ar)kwy\b", re.I)),
    ("Omni Amelia Island Resort", re.compile(r"\bamelia island plantation\b|\bfirst coast hwy\b", re.I)),
    ("Ritz-Carlton Amelia Island", re.compile(r"\britz carlton dr\b|\britz-carlton dr\b", re.I)),
    ("Yulee / SR-200 at I-95", re.compile(r"\bsr ?200\b|\ba1a\b(?=.*yulee)|\bharts rd\b", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-jacksonville": "Downtown Jacksonville",
    "southbank-san-marco": "Southbank / San Marco",
    "riverside-avondale-brooklyn": "Riverside / Avondale",
    "jax-airport-northside": "Jacksonville International Airport (JAX)",
    "westside-i10-i295": "Westside / I-10 & I-295",
    "arlington-intracoastal-west": "Arlington / Intracoastal West",
    "southside-university-boulevard": "Southside / University Boulevard",
    "st-johns-town-center-gate-parkway": "St. Johns Town Center",
    "deerwood-baymeadows": "Baymeadows Road",
    "deerwood-park-mayo-unf": "Deerwood Park / Mayo Clinic",
    "mandarin-bartram-julington-creek": "Mandarin",
    "jacksonville-beach": "Jacksonville Beach",
    "atlantic-neptune-beach-mayport": "Atlantic Beach / Neptune Beach",
    "ponte-vedra-beach-sawgrass": "Ponte Vedra Beach",
    "orange-park-fleming-island": "Orange Park",
    "amelia-island-fernandina-beach": "Amelia Island",
    "yulee-nassau-i95": "Yulee",
}

STRUCTURE_TEST = OrderedDict([
    ("A. Is Jacksonville / Northeast Florida one market, or several?",
     "ONE market, jacksonville-fl, covering Duval County whole plus the Jacksonville-facing codes of Clay and "
     "Nassau and two codes of St. Johns. One consolidated city-county at its centre, one commercial airport "
     "(JAX) serving all four counties, one CVB for the core (Visit Jacksonville, which covers Duval including "
     "the beaches), one I-95 / I-10 / I-295 / SR-202 road system and one contiguous Atlantic beach chain from "
     "Amelia Island to Ponte Vedra Beach. St. Augustine is the boundary where that coherence STOPS, and it is "
     "refused."),
    ("B. Downtown Jacksonville is NOT the market",
     "The order's first instruction. Downtown (32202 + 32206) carries just 5 hotel-rank lodging licences of the "
     "market's 258 -- under 2 %. The market's real weight is suburban and airport: 32218 (JAX / Northside) 29, "
     "32256 (Deerwood / Baymeadows) 26, 32216 (Southside) 18, 32250 (Jacksonville Beach) 16, 32073 (Orange "
     "Park) 14, 32207 (Southbank / San Marco) 13, 32246 (Town Center) 12, 32034 (Amelia Island) 32. Modelling "
     "this market as downtown Jacksonville would discard 98 % of it."),
    ("C. Jacksonville International Airport (JAX)",
     "A CORRIDOR OF ITS OWN POSTAL CODE -- the first Florida market where the airport test answers YES. JAX's "
     "hotel district is 32218 (Airport Center Drive, Duval Road, Airport Road, River City Marketplace), which "
     "carries 29 hotel-rank lodging licences, the market's largest single code. PBI and FLL owned no postal "
     "code and got no corridor; JAX owns one. The corridor is named jax-airport-northside because the same "
     "postal system carries Dunn Avenue, Oceanway, Dames Point and the northwest Duval blocks."),
    ("D. JAXPORT / cruise lodging",
     "NO CORRIDOR -- the PortMiami and Port of Palm Beach finding, not the Port Everglades one. The cruise "
     "terminal is at Dames Point in 32226, which carries ONE hotel-rank lodging licence and is already claimed "
     "in full by jax-airport-northside. A cruise corridor could only split or duplicate a covered code. "
     "JAXPORT and Blount Island are street-and-pin OVERLAYS."),
    ("E. Naval Station Mayport and NAS Jacksonville",
     "NO CORRIDOR FOR EITHER, proved on the state's own register: 32227 and 32228 (Mayport) and 32212 (NAS "
     "Jacksonville) carry ZERO public-lodging licences of any rank. Military billeting is not public lodging "
     "and is refused by name (NONPUBLIC_NAMES). Mayport Village's commercial inventory is addressed ATLANTIC "
     "BEACH 32233 and sits inside atlantic-neptune-beach-mayport. Both bases are overlays, and both are real "
     "demand drivers for the corridors around them."),
    ("F. Mayo Clinic Jacksonville",
     "NO MEDICAL CORRIDOR. Mayo sits on San Pablo Road in 32224 (6 hotel-rank licences), claimed in full by "
     "deerwood-park-mayo-unf alongside UNF and Tinseltown. Medical demand informs a corridor's description and "
     "never alters a premises identity."),
    ("G. The four beach municipalities",
     "THREE CORRIDORS, not one generic beach strip, and the order forbids flattening them. jacksonville-beach "
     "(32250, 16 licences) is the City of Jacksonville Beach: the pier, 3rd Street and the oceanfront blocks. "
     "atlantic-neptune-beach-mayport (32233 / 32266 / 32227 / 32228, 9 licences) is two smaller municipalities "
     "plus the river mouth, whose traveller product is Beaches Town Center and Hanna Park rather than the pier. "
     "ponte-vedra-beach-sawgrass (32082 / 32081, 6 licences) is St. Johns County resort-and-golf. Each has a "
     "distinct traveller intent; each publishes only if it meets the threshold on its own."),
    ("H. Southside is FOUR corridors, because the order names four things",
     "The order requires Southside, St. Johns Town Center, Deerwood and Baymeadows to be evaluated. Duval's "
     "postal codes separate them cleanly and the registry follows: southside-university-boulevard (32216, the "
     "old University Boulevard / Philips Highway motor-court row, 18), "
     "st-johns-town-center-gate-parkway (32246, the Town Center retail district, 12), deerwood-baymeadows "
     "(32217 + 32256, the Baymeadows and Southpoint business corridor, 26) and deerwood-park-mayo-unf (32224, "
     "Mayo and UNF, 6). Four codes, four travel products, four corridors."),
    ("I. Riverside / Avondale and San Marco",
     "TWO CORE corridors, never folded into downtown. riverside-avondale-brooklyn (32204 + 32205) is the "
     "historic walkable west quarter; southbank-san-marco (32207) is the Southbank plus San Marco Square plus "
     "the Baptist Health campus and carries 13 licences, more than twice downtown's own 5."),
    ("J. Orange Park / Fleming Island",
     "CORRIDOR, one corridor over five CLAY COUNTY codes (17 licences). A Blanding Boulevard / US-17 commuter "
     "suburb continuous with Duval's westside, serving NAS Jacksonville and Jacksonville business travel. Clay "
     "County's inland lake country (Keystone Heights 32656) is REFUSED, which is this market's own proof that "
     "county inclusion is not traveller-market inclusion."),
    ("K. Amelia Island / Fernandina Beach",
     "CORRIDOR (32034 + 32035, 32 licences). The order requires an explicit choice among CORRIDOR, FRINGE and "
     "FUTURE STANDALONE; CORRIDOR is chosen because Nassau County is in the Jacksonville MSA, JAX is the "
     "island's airport with no closer commercial field, and 32 hotel-rank licences is real inventory no other "
     "market publishes. It is admitted at CORRIDOR tier rather than CORE precisely because it is this market's "
     "NAMED first future-standalone candidate: its own CVB, its own county, two flagship resort campuses."),
    ("L. Ponte Vedra Beach",
     "CORRIDOR (32082 + 32081, 6 licences), and the one place where the CVB test and the traveller test "
     "disagree. Florida's Historic Coast markets Ponte Vedra with St. Augustine; the traveller reality is that "
     "Ponte Vedra Beach is the next beach south of Jacksonville Beach on A1A with no gap, and its resorts route "
     "guests through JAX 25 miles north. The traveller test governs and the disagreement is recorded."),
    ("M. St. Augustine / St. Augustine Beach / World Golf Village",
     "OUTSIDE, refused ENTIRELY and by name, reserved as FUTURE_STANDALONE st-augustine-fl. 116 hotel-rank "
     "lodging licences across 32084 (78), 32080 (29) and 32092 (9) -- larger than most PetTripFinder markets "
     "publish in total -- its own CVB, the nation's oldest city, and a separate resort golf destination at "
     "World Golf Village. The order forbids automatic absorption and the register makes absorption indefensible."),
    ("N. Palm Coast",
     "OUTSIDE, refused by name, FUTURE_STANDALONE. Flagler County, 60 miles south of downtown Jacksonville and "
     "closer to Daytona Beach; 26 hotel-rank licences and a register dominated by 676 resort-condominium and "
     "775 vacation-dwelling licences."),
    ("O. Gainesville, Daytona Beach, Savannah and the Golden Isles",
     "ALL OUTSIDE. Gainesville (Alachua, 69 licences) and Daytona Beach (Volusia, 236) are future standalone "
     "markets. Savannah is the EXISTING LIVE market savannah-ga and owns every Chatham County code -- admitting "
     "one would publish a hotel twice. Brunswick / St. Simons / Jekyll (Glynn County, Georgia) and Kingsland / "
     "St. Marys (Camden County, Georgia) are out of state, unlicensed by Florida DBPR, and belong to a future "
     "golden-isles-ga market."),
    ("P. Jacksonville, NORTH CAROLINA",
     "A DIFFERENT PLACE. jacksonville-nc is LIVE as production market #22 (Onslow County, ZIPs 285xx). It is "
     "named in the OUTSIDE table so that no later phase, and no cross-market chain-name flag, can confuse a "
     "Duval County hotel with a Camp Lejeune one. Separation is by state code, postal code, street and brand "
     "property code. The word 'Jacksonville' separates nothing."),
])

CRUISE_TEST = OrderedDict([
    ("jaxport_lodging_in_its_own_postal_code",
     "NO. JAXPORT's cruise terminal sits at Dames Point in postal code 32226, which carries ONE hotel-rank "
     "lodging licence on the state's own record and is already claimed in full by jax-airport-northside. Blount "
     "Island (container) is in the same code. Cruise passengers stay in the JAX airport / Northside cluster or "
     "downtown, both of which are already corridors."),
    ("would_a_port_corridor_duplicate_inventory", True),
    ("port_corridor_created", False),
    ("why",
     "The corridor registry is a postal-code partition, so a 'JAXPORT' corridor could only be built by SPLITTING "
     "32226 -- a per-property judgement the registry forbids -- or by duplicating it, which a partition forbids "
     "outright. This is the PortMiami / Port of Palm Beach finding, not the Port Everglades finding (33316: a "
     "postal code full of hotels claimed by nothing else). A port earns a corridor only when it owns "
     "hotel-bearing postal codes no other corridor claims. JAXPORT is a street-and-pin OVERLAY."),
    ("jax_airport_corridor_created", True),
    ("jax_why",
     "AND THIS IS THE DIFFERENCE FROM PBI AND FLL. Both of those airports owned no postal code, so neither "
     "earned a corridor. JAX's hotel district IS postal code 32218 -- Airport Center Drive, Duval Road, Airport "
     "Road, River City Marketplace -- which carries 29 hotel-rank lodging licences, the largest single code in "
     "this market. The same postal-code test therefore answers YES here. The corridor is named "
     "jax-airport-northside, not 'airport', because 32218 also carries Dunn Avenue and the I-95 / I-295 north "
     "interchange and because 32208 / 32209 / 32219 / 32226 belong to the same northern travel system."),
    ("mayport_corridor_created", False),
    ("mayport_why",
     "Postal codes 32227 (Naval Station Mayport) and 32228 (Mayport) carry ZERO public-lodging licences of any "
     "rank. Mayport Village's commercial inventory is addressed ATLANTIC BEACH 32233. Mayport is an OVERLAY "
     "inside atlantic-neptune-beach-mayport. A measurement, not a preference."),
    ("nas_jacksonville_corridor_created", False),
    ("nas_why", "32212 carries zero public-lodging licences; Navy billeting is not public lodging and is refused "
                "by name. NAS Jacksonville is an overlay inside westside-i10-i295 and a demand driver for "
                "orange-park-fleming-island."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel operation."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP), matched to a DBPR HOTL / "
     "MOTL / BNB licence at that premises. A unit designator ('Ste', 'Unit', '#', 'Apt', 'PH', 'Villa') in the "
     "licensed address means the licence is a UNIT INSIDE a building, which is never a hotel identity."),
    ("hotel_vs_residence_boundary",
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. The "
     "residences are refused as RESORT_RESIDENCE even where they share the address, the brand, the entrance, "
     "the pool, the golf course and the booking engine. Northeast Florida's specific exposures: Amelia Island "
     "Plantation's and the Omni Amelia Island Resort's villa and condominium programme (Nassau County carries "
     "1,130 resort-condominium licences against 32 hotel-rank ones), the Ritz-Carlton Amelia Island's "
     "residences, Sawgrass and TPC Sawgrass villas, Ponte Vedra Inn & Club's cottages, Jacksonville Beach's "
     "oceanfront condominium towers, and St. Johns County's 1,472 resort-condominium and 2,139 vacation-dwelling "
     "licences (overwhelmingly in the refused St. Augustine codes)."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared "
     "amenities or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never "
     "published as one."),
    ("golf_resort_lodging",
     "Golf-resort lodging (TPC Sawgrass, Sawgrass Marriott, Ponte Vedra Inn & Club, Amelia Island Plantation, "
     "the Omni Amelia Island Resort) is admitted only as the hotel premises the operator sells nightly to the "
     "general public. Member-only or guest-of-member club lodging is NOT public lodging and is refused."),
    ("military_lodging",
     "Navy Lodge and Navy Gateway Inns & Suites operations at NAS Jacksonville and Naval Station Mayport are "
     "government billeting, not public lodging, and are refused by name."),
])

#: The shared postal codes the corridor registry deliberately covers whole, with the municipalities that share
#: each one on the state's own record. Reporting only -- a shared code is still exactly one corridor.
SHARED_POSTAL_CODES = OrderedDict([
    ("32003", ["Fleming Island", "Orange Park", "(Clay County)"]),
    ("32034", ["Fernandina Beach", "Amelia Island", "(Nassau County)"]),
    ("32065", ["Orange Park", "Oakleaf", "(Clay County -- the Duval half of Oakleaf is 32222)"]),
    ("32073", ["Orange Park", "unincorporated Clay County"]),
    ("32082", ["Ponte Vedra Beach", "Ponte Vedra", "(St. Johns County)"]),
    ("32097", ["Yulee", "(Nassau County)"]),
    ("32218", ["Jacksonville", "(JAX airport, Dunn Avenue, River City Marketplace)"]),
    ("32226", ["Jacksonville", "Oceanway", "Dames Point", "(JAXPORT)"]),
    ("32233", ["Atlantic Beach", "Mayport Village", "Jacksonville"]),
    ("32250", ["Jacksonville Beach", "Jacksonville"]),
    ("32256", ["Jacksonville", "(Deerwood, Baymeadows East, Southpoint)"]),
    ("32259", ["Saint Johns", "Fruit Cove", "Julington Creek", "(ST. JOHNS COUNTY -- covered inside the "
                                                               "Mandarin corridor)"]),
    ("32266", ["Neptune Beach"]),
])

#: FUTURE standalone markets this order preserves by name.
FUTURE_MARKETS = OrderedDict([
    ("st-augustine-fl", "St. Augustine / St. Augustine Beach / World Golf Village -- St. Johns County's historic "
                        "coast, its own CVB (Florida's Historic Coast) and 116 hotel-rank lodging licences. The "
                        "single most important market this order refuses."),
    ("amelia-island-fl", "NAMED OPTIONALITY, not a refusal. Amelia Island / Fernandina Beach is ADMITTED here at "
                         "CORRIDOR tier, and is recorded as this market's first candidate for promotion to a "
                         "standalone market: its own CVB, its own county and two flagship resort campuses. A "
                         "founder can promote it later on this record."),
    ("palm-coast-flagler-fl", "Palm Coast / Flagler Beach -- Flagler County, 60 miles south and oriented to "
                              "Daytona Beach."),
    ("daytona-beach-fl", "Daytona Beach / Ormond Beach -- Volusia County, its own Atlantic beach and speedway "
                         "market."),
    ("gainesville-fl", "Gainesville -- Alachua County, a separate university market on I-75."),
    ("golden-isles-ga", "Brunswick / St. Simons Island / Jekyll Island and Kingsland / St. Marys -- coastal "
                        "GEORGIA, out of state and unlicensed by Florida DBPR."),
])

#: Markets that are ALREADY LIVE and own the inventory this market refuses. Never 'future'.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("jacksonville-nc", "Jacksonville, Onslow County, NORTH CAROLINA (Camp Lejeune), live as production market "
                        "#22. A DIFFERENT PLACE THAT SHARES THIS MARKET'S NAME. Owns ZIPs 28540 / 28543 / 28544 "
                        "/ 28545 / 28546 / 28547. Named first because the name collision, not the geography, is "
                        "the hazard."),
    ("savannah-ga", "Savannah / Chatham County, GEORGIA, live as production market #27. Owns every Chatham "
                    "County postal code, 120 miles north on I-95."),
    ("orlando-fl", "Orlando / Central Florida, live as production market #28. Owns the Orange / Osceola / "
                   "Seminole codes, 140 miles south."),
    ("tampa-fl", "Tampa / Hillsborough and Pinellas, live. Owns the Gulf-coast codes, 200 miles southwest."),
    ("west-palm-beach-fl", "West Palm Beach / The Palm Beaches, live as production market #33 (deploy "
                           "6ab599163f833ab7f48b395d) -- the CURRENT LIVE market at this order's authoring time."),
    ("miami-fl", "Miami / Miami-Dade, live as production market #31."),
    ("fort-lauderdale-fl", "Fort Lauderdale / Broward, live as production market #32."),
])

MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "jacksonvill": "jacksonville", "jacksonvile": "jacksonville", "jax": "jacksonville",
    "jacksonville,": "jacksonville", "jacksonville fl": "jacksonville", "jacksonville, fl": "jacksonville",
    "jacksonville bch": "jacksonville beach", "jax beach": "jacksonville beach",
    "jacksonville beach,": "jacksonville beach", "jacksonvillle beach": "jacksonville beach",
    "jacksonville beach fl": "jacksonville beach", "jax bch": "jacksonville beach",
    "atlantic bch": "atlantic beach", "atlantic beach,": "atlantic beach",
    "neptune bch": "neptune beach", "neptune beach,": "neptune beach",
    "ponte vedra": "ponte vedra beach", "ponte vedra bch": "ponte vedra beach",
    "ponte verda beach": "ponte vedra beach", "pv beach": "ponte vedra beach",
    "fernandina": "fernandina beach", "fernandina bch": "fernandina beach",
    "fernadina beach": "fernandina beach", "amelia island": "fernandina beach",
    "orange pk": "orange park", "orange park,": "orange park",
    "green cove spgs": "green cove springs", "green cove": "green cove springs",
    "saint johns": "st. johns", "st johns": "st. johns", "st. johns,": "st. johns",
    "fruit cove": "st. johns", "julington creek": "st. johns",
    "saint augustine": "st. augustine", "st augustine": "st. augustine",
    "st augustine bch": "st. augustine beach", "saint augustine beach": "st. augustine beach",
    "mayport": "atlantic beach", "mayport naval station": "atlantic beach",
    "baldwin,": "baldwin", "yulee,": "yulee", "middleburg,": "middleburg",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("32218", "JAX airport / Dunn Avenue / River City Marketplace -- 29 hotel-rank lodging licences, the "
              "market's largest single code, and the reason this market HAS an airport corridor where PBI and "
              "FLL did not."),
    ("32034", "Amelia Island / Fernandina Beach -- 32, against Nassau County's 1,130 resort-condominium "
              "licences; the island's rental stock is condominium inventory that never enters the census."),
    ("32256", "Deerwood / Baymeadows / Southpoint -- 26, the market's second-largest code."),
    ("32216", "Southside / University Boulevard / Philips Highway -- 18, the market's oldest motor-court row."),
    ("32250", "Jacksonville Beach -- 16, a separate municipality inside Duval County."),
    ("32073", "Orange Park, CLAY COUNTY -- 14 on Blanding Boulevard and Wells Road."),
    ("32207", "Southbank / San Marco -- 13, more than twice downtown's own 5."),
    ("32246", "St. Johns Town Center / Gate Parkway -- 12."),
    ("32244", "Westside / 103rd Street -- 10."),
    ("32202", "DOWNTOWN JACKSONVILLE -- just 3, and 5 with Springfield's 32206. Downtown is under 2 % of the "
              "market, which is why the order's 'do not model this as Downtown Jacksonville' instruction is the "
              "single most important geographic fact here."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Jacksonville" % name),
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
        ("market_name", "Jacksonville / Northeast Florida beach, airport, resort and business lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", "FL"),
        ("states", ["FL"]),
        ("country", "US"),
        ("market_center", {"lat": 30.33, "lng": -81.66}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past the St. Johns County line (St. "
             "Augustine, St. Augustine Beach, World Golf Village) and into Flagler and Putnam, west past Baldwin "
             "into Baker County, and north across the GEORGIA state line (Kingsland / St. Marys), so that " +
             WORK_ORDER + " classifies those properties on evidence instead of being blind to them. Admission is "
             "decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Jacksonville / Northeast Florida is ONE market: thirteen CORE corridors over Duval "
         "County (a consolidated city-county) plus the Duval half of the Mandarin corridor, three CORRIDOR tiers "
         "(Ponte Vedra Beach / Sawgrass in St. Johns County, Orange Park / Fleming Island in Clay County, Amelia "
         "Island / Fernandina Beach in Nassau County) and one FRINGE corridor (mainland Nassau). ST. AUGUSTINE "
         "IS REFUSED ENTIRELY and reserved as future st-augustine-fl; Palm Coast, Gainesville and Daytona Beach "
         "are refused as future standalone markets; savannah-ga, orlando-fl and jacksonville-nc are LIVE markets "
         "whose inventory is never admitted here."),
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
        ("market_name", "Jacksonville, Florida"),
        ("market_slug", MARKET_ID),
        ("state_name", "Florida"),
        ("state_code", "FL"),
        ("primary_state_code", "FL"),
        ("states", ["FL"]),
        ("primary_city", "Jacksonville"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Jacksonville & Northeast Florida | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Jacksonville and Northeast Florida -- downtown and the Southbank, "
         "the JAX airport and Northside cluster, Southside and St. Johns Town Center, Baymeadows and Deerwood, "
         "Jacksonville Beach, Atlantic and Neptune Beach, Ponte Vedra Beach, Orange Park and Amelia Island -- "
         "with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Jacksonville"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its Florida DBPR "
         "public-lodging licence states it, joined to the corridor registry. A Northeast Florida beach, airport, "
         "resort and business travel market -- Duval County whole plus the Jacksonville-facing codes of Clay and "
         "Nassau and two codes of St. Johns. Not 'all of Northeast Florida': St. Augustine, Palm Coast, "
         "Gainesville and Daytona Beach are refused. Nothing else admits a property: not a brand's "
         "'Jacksonville' marketing name, not a map pin, not a vacation-rental listing, not a competitor "
         "directory's city label. And the LIVE market jacksonville-nc is a different city in a different state."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Duval County is a "
         "CONSOLIDATED city-county, so the postal city 'JACKSONVILLE' spans 25 lodging-bearing codes across 39 "
         "miles and places nothing by itself. Shared codes are covered whole: 32233 by Atlantic Beach, Mayport "
         "Village and Jacksonville; 32250 by Jacksonville Beach and Jacksonville; 32034 by Fernandina Beach and "
         "Amelia Island; 32073 / 32065 / 32003 by Orange Park, Oakleaf and unincorporated Clay County; 32259 by "
         "Saint Johns, Fruit Cove and Julington Creek in ST. JOHNS COUNTY. JAX Airport is a corridor because it "
         "owns 32218; JAXPORT, Naval Station Mayport, NAS Jacksonville, Mayo Clinic, UNF, TPC Sawgrass, the "
         "Beaches Town Center, Centre Street and Fort Clinch are overlays, never corridors of their own."),
        ("_census_membership_note",
         "Individual condominium units (DBPR CNDO), vacation dwellings (DWEL), vacation homes, property-management "
         "portfolios, Airbnb / Vrbo inventory, ordinary apartments (DBPR NAPT), individual timeshare units, private "
         "resort / branded residences, golf-villa programmes, member-only club lodging and government military "
         "billeting are never admitted. A mixed hotel / condo / residence property is admitted only as the exact "
         "hotel premises its public operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "3 + 4 + 5 + 6 -- Jacksonville / Northeast Florida travel-market geography, the four-county "
                  "boundary test, the coastal / beach structure test, the JAXPORT cruise test, the JAX airport "
                  "test, the business / medical / port / military demand-driver test and the resort / condo / "
                  "vacation-rental safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/jacksonville-fl.json. "
         "This order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its Florida DBPR public-lodging licence states "
         "it, joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes (and, for the registry lane, by "
                          "county); the existing live markets and future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("northeast_florida_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("jaxport_cruise_and_airport_test", CRUISE_TEST),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("the_jacksonville_name_trap",
         "THE market's identity trap, stated before any hotel is admitted, and it runs in two directions. "
         "ACROSS STATES: jacksonville-nc is LIVE (Onslow County, North Carolina, ZIPs 285xx) and every national "
         "chain publishes near-identically named hotels in both cities -- Hampton Inn Jacksonville, Home2 Suites "
         "Jacksonville, Holiday Inn Express Jacksonville, Sleep Inn Jacksonville, Super 8 Jacksonville. INSIDE "
         "FLORIDA: Duval County is a consolidated city-county, so the postal city 'JACKSONVILLE' covers 25 "
         "lodging-bearing postal codes across 39 miles, from the Georgia line to the St. Johns County line and "
         "from the Atlantic to Baldwin. A property's own postal code, street and brand property code decide what "
         "and where it is. The word 'Jacksonville' decides nothing, in either direction, and no later phase may "
         "place or hold a property by it."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Jacksonville International Airport (JAX)",
             "jax-airport-northside (32218) -- and here uniquely the driver IS a postal code, so it is a "
             "corridor."),
            ("Downtown / Southbank convention, arena and stadium demand",
             "downtown-jacksonville (32202/32206) and southbank-san-marco (32207) -- overlays: the Prime Osborn "
             "Convention Center, VyStar Veterans Memorial Arena, EverBank Stadium."),
            ("St. Johns Town Center retail demand", "st-johns-town-center-gate-parkway (32246) -- overlay."),
            ("Southside / Deerwood / Southpoint corporate demand",
             "deerwood-baymeadows (32217/32256) and southside-university-boulevard (32216) -- overlays."),
            ("Baymeadows", "deerwood-baymeadows -- an overlay on 32256/32217, not a corridor of its own."),
            ("Mayo Clinic Jacksonville", "deerwood-park-mayo-unf (32224) -- overlay. No medical corridor."),
            ("JAXPORT / cruise demand", "jax-airport-northside (32226) -- overlay. No cruise corridor."),
            ("Naval Station Mayport", "atlantic-neptune-beach-mayport (32227/32228 carry zero lodging licences) "
                                      "-- overlay. Billeting is not public lodging."),
            ("NAS Jacksonville", "westside-i10-i295 (32212 carries zero lodging licences) -- overlay, and a "
                                 "driver for orange-park-fleming-island."),
            ("University of North Florida", "deerwood-park-mayo-unf (32224) -- overlay."),
            ("TPC Sawgrass / THE PLAYERS Championship", "ponte-vedra-beach-sawgrass (32082) -- overlay."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Downtown Jacksonville", "ADMITTED (CORE, downtown-jacksonville, 32202/32206). PRIMARY evaluation. "
                                      "5 hotel-rank licences -- under 2 % of the market."),
            ("Southbank", "ADMITTED (CORE, southbank-san-marco, 32207). PRIMARY evaluation."),
            ("San Marco", "ADMITTED (CORE, southbank-san-marco, 32207) -- shares the Southbank's postal code and "
                          "is reported as an overlay. PRIMARY evaluation."),
            ("Riverside / Avondale", "ADMITTED (CORE, riverside-avondale-brooklyn, 32204/32205). PRIMARY "
                                     "evaluation. Brooklyn and Murray Hill are overlays on the same codes."),
            ("Jacksonville International Airport / JAX",
             "ADMITTED (CORE, jax-airport-northside, 32218) -- PRIMARY evaluation, and the market's largest "
             "cluster at 29 hotel-rank licences. A corridor because it owns a postal code."),
            ("Northside", "ADMITTED (CORE, jax-airport-northside, 32208/32209/32218/32219/32226). PRIMARY "
                          "evaluation."),
            ("Southside", "ADMITTED (CORE, southside-university-boulevard, 32216). PRIMARY evaluation."),
            ("Deerwood", "ADMITTED (CORE) across deerwood-baymeadows (32256, Deerwood Park south / Southpoint) "
                         "and deerwood-park-mayo-unf (32224, Deerwood Park north). PRIMARY evaluation."),
            ("Baymeadows", "ADMITTED (CORE, deerwood-baymeadows, 32217/32256). PRIMARY evaluation."),
            ("St. Johns Town Center", "ADMITTED (CORE, st-johns-town-center-gate-parkway, 32246). PRIMARY "
                                      "evaluation."),
            ("Arlington", "ADMITTED (CORE, arlington-intracoastal-west, 32211/32225/32277). PRIMARY evaluation."),
            ("Mandarin", "ADMITTED (CORE, mandarin-bartram-julington-creek, 32223/32257/32258 + St. Johns "
                         "County's 32259). PRIMARY evaluation."),
            ("Jacksonville Beach", "ADMITTED (CORE, jacksonville-beach, 32250). PRIMARY evaluation. A separate "
                                   "municipality inside Duval County; 16 hotel-rank licences."),
            ("Neptune Beach", "ADMITTED (CORE, atlantic-neptune-beach-mayport, 32266). PRIMARY evaluation."),
            ("Atlantic Beach", "ADMITTED (CORE, atlantic-neptune-beach-mayport, 32233). PRIMARY evaluation."),
            ("Mayport", "ADMITTED as an OVERLAY on atlantic-neptune-beach-mayport. PRIMARY evaluation, answered "
                        "mechanically: 32227 and 32228 carry ZERO public-lodging licences of any rank and "
                        "Mayport Village's inventory is addressed ATLANTIC BEACH 32233. Never a corridor."),
            ("Ponte Vedra Beach", "ADMITTED (CORRIDOR, ponte-vedra-beach-sawgrass, 32082). STRONG evaluation. "
                                  "ST. JOHNS COUNTY; admitted on the traveller test against the CVB test, which "
                                  "is recorded."),
            ("Sawgrass", "ADMITTED (CORRIDOR, ponte-vedra-beach-sawgrass, 32082) as an overlay. STRONG "
                         "evaluation."),
            ("Orange Park", "ADMITTED (CORRIDOR, orange-park-fleming-island, 32073). STRONG evaluation. CLAY "
                            "COUNTY; 14 hotel-rank licences."),
            ("Fleming Island", "ADMITTED (CORRIDOR, orange-park-fleming-island, 32003). STRONG evaluation."),
            ("St. Johns", "ADMITTED (CORE, mandarin-bartram-julington-creek, 32259). STRONG evaluation. ST. "
                          "JOHNS COUNTY; ZERO hotel-rank licences of its own, admitted for completeness of the "
                          "Mandarin corridor it faces across Julington Creek."),
            ("Julington Creek", "ADMITTED (CORE, mandarin-bartram-julington-creek, 32259) as an overlay. STRONG "
                                "evaluation."),
            ("Yulee", "ADMITTED (FRINGE, yulee-nassau-i95, 32097). STRONG evaluation. NASSAU COUNTY; the I-95 "
                      "exit 373 / SR-200 gateway to Amelia Island, 6 hotel-rank licences."),
            ("Amelia Island", "ADMITTED (CORRIDOR, amelia-island-fernandina-beach, 32034/32035). STRONG "
                              "evaluation, explicit classification required by the order and given: CORRIDOR, "
                              "not FRINGE and not FUTURE STANDALONE. 32 hotel-rank licences. Recorded as the "
                              "market's NAMED first future-standalone candidate."),
            ("Fernandina Beach", "ADMITTED (CORRIDOR, amelia-island-fernandina-beach, 32034). STRONG "
                                 "evaluation; shares 32034 with Amelia Island."),
            ("Callahan / Hilliard", "ADMITTED (FRINGE, yulee-nassau-i95, 32011/32046). Rural mainland Nassau on "
                                    "US-1 / US-301; 4 hotel-rank licences, far below any publication threshold. "
                                    "Admitted so Nassau County's inventory is ACCOUNTED FOR."),
            ("Baldwin", "ADMITTED (CORE, westside-i10-i295, 32234). A separate municipality inside Duval County "
                        "on US-301 at I-10; the market's western line."),
            ("Oakleaf", "ADMITTED on BOTH sides of the county line by its own codes: the Duval half (32222) in "
                        "westside-i10-i295 and the Clay half (32065) in orange-park-fleming-island."),
            ("Middleburg / Green Cove Springs", "ADMITTED (CORRIDOR, orange-park-fleming-island, 32068/32043). "
                                                "CLAY COUNTY."),
            ("Nocatee", "ADMITTED (CORRIDOR, ponte-vedra-beach-sawgrass, 32081). ST. JOHNS COUNTY; no hotel-rank "
                        "licence of its own."),
            ("JAXPORT / Blount Island / Dames Point",
             "ADMITTED as an OVERLAY on jax-airport-northside (32226). Never a corridor -- see the cruise test."),
            ("Naval Station Mayport / NAS Jacksonville",
             "ADMITTED as OVERLAYS (32227/32228 and 32212, all three carrying zero lodging licences). Navy "
             "Lodge and Navy Gateway Inns & Suites billeting is refused by name as NON-PUBLIC lodging."),
            ("Mayo Clinic Jacksonville / UNF",
             "ADMITTED as OVERLAYS on deerwood-park-mayo-unf (32224). No medical corridor."),
            ("St. Augustine", "OUTSIDE -- REFUSED ENTIRELY and by name (32084/32085/32095/32086/32033/32145). "
                              "FUTURE_STANDALONE st-augustine-fl. CAREFUL evaluation, and the order's explicit "
                              "instruction not to absorb it. 78 hotel-rank licences in 32084 alone."),
            ("St. Augustine Beach", "OUTSIDE -- refused by name (32080). 29 hotel-rank licences. "
                                    "FUTURE_STANDALONE st-augustine-fl."),
            ("World Golf Village", "OUTSIDE -- refused by name (32092). 9 hotel-rank licences. CAREFUL "
                                   "evaluation; a St. Augustine resort-golf product, reserved for "
                                   "st-augustine-fl."),
            ("Palm Coast", "OUTSIDE -- refused by name (32137/32164/32135/32110/32136). CAREFUL evaluation. "
                           "Flagler County, 60 miles south and oriented to Daytona Beach. FUTURE_STANDALONE."),
            ("Keystone Heights", "OUTSIDE -- refused by name (32656) although it is CLAY COUNTY. The market's "
                                 "own proof that county inclusion is not traveller-market inclusion."),
            ("Gainesville", "OUTSIDE -- refused by name. Alachua County, FUTURE_STANDALONE gainesville-fl."),
            ("Daytona Beach", "OUTSIDE -- refused by name. Volusia County, FUTURE_STANDALONE daytona-beach-fl."),
            ("Palatka / Putnam County", "OUTSIDE -- refused by name. Rural, no Jacksonville traveller system."),
            ("Macclenny / Baker County", "OUTSIDE -- refused by name. Rural I-10 west of Baldwin."),
            ("Savannah", "OUTSIDE -- EXISTING LIVE MARKET savannah-ga (production #27) owns every Chatham County "
                         "code. Admitting one would publish a hotel in two markets."),
            ("Brunswick / Golden Isles / St. Simons / Jekyll",
             "OUTSIDE -- GEORGIA, Glynn County, FUTURE_STANDALONE golden-isles-ga."),
            ("Kingsland / St. Marys, Georgia", "OUTSIDE -- GEORGIA, Camden County. Twenty minutes from Yulee, "
                                               "and refused by the state line rather than by distance; Florida "
                                               "DBPR does not license it."),
            ("Central Florida inventory", "OUTSIDE -- EXISTING LIVE MARKET orlando-fl (production #28)."),
            ("Jacksonville, NORTH CAROLINA", "OUTSIDE -- a DIFFERENT PLACE. EXISTING LIVE MARKET "
                                             "jacksonville-nc (production #22), Onslow County, ZIPs 285xx."),
            ("Properties using 'Jacksonville' mainly as marketing",
             "Never admitted or placed by name. A 'Jacksonville' / 'Jacksonville South' / 'Jacksonville Airport' "
             "name is placed by its OWN postal code, which may be Orange Park, Yulee, St. Augustine or Onslow "
             "County, North Carolina. A 'Jacksonville Beach' name whose own address states 32233 is an Atlantic "
             "Beach property."),
        ])),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_counties", sorted(ADMITTED_COUNTIES)),
        ("observed_outside_counties", OBSERVED_COUNTIES),
        ("shared_postal_codes", SHARED_POSTAL_CODES),
        ("no_live_market_postal_code_admitted", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, cruise, airport, medical or golf "
         "keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration order "
         "publishes it. JAXPORT, Naval Station Mayport, NAS Jacksonville, Mayo Clinic, UNF, TPC Sawgrass, the "
         "Beaches Town Center, Mayport Village, River City Marketplace, Centre Street, Fort Clinch, Nocatee and "
         "Oakleaf are overlays."),
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
         "branded residences; golf-villa programmes; member-only club lodging; government military billeting; and "
         "privately managed units inside hotel-condo towers. A mixed hotel / condo / residence property is admitted "
         "ONLY as the exact hotel premises its public operator sells as a hotel, proved on the operator's own page "
         "and the licence's exact premises. Campgrounds, RV parks and hostels are NON_LODGING."),
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
    key = muni
    if key in MUNICIPALITY_SPELLINGS:
        return MUNICIPALITY_SPELLINGS[key]
    key2 = muni.rstrip(",")
    if key2 in MUNICIPALITY_SPELLINGS:
        return MUNICIPALITY_SPELLINGS[key2]
    #: "st johns" arrives here with the period already stripped; re-spell the canonical forms.
    return {"st johns": "st. johns", "st augustine": "st. augustine",
            "st augustine beach": "st. augustine beach"}.get(key2, key2)


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
