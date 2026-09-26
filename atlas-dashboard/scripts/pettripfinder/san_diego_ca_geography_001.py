"""PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4 and 5: the San Diego / Coastal San Diego County market.

Built from zero on the CURRENT hardened lineage: the Jacksonville-live release c6d9f5bd (live source e9a059e5,
built_from e7e02d43). Current verified live at authoring time = jacksonville-fl deploy 6ab6c8798bd9daf5038ae3e5,
34 markets / 2,519 profiles / 2,807 release-index routes / 2,874 served routes, host verified. No earlier San
Diego build exists, and this is the FIRST California market: no live market owns a single California postal code.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical San Diego traveller lodging market, stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule
(with FUTURE_STANDALONE markets named inside OUTSIDE) before a single hotel is admitted, so no property is admitted
or refused after the fact to make a number. The order's "STRONG CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or the City of San Diego's
business-tax certificate for the premises, the city's own record of the business location) states it, joined to
the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by
exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing name never
admits and never places a property: a hotel whose own address states Temecula 92590 is a Riverside County hotel
however loudly it calls itself "North San Diego", and a hotel named "Del Mar" whose own address states San Diego
92130 is placed by 92130.

WHY "SAN DIEGO" AND "LA JOLLA" DECIDE NOTHING HERE
-------------------------------------------------
The postal city "SAN DIEGO" is the postal city of the whole City of San Diego -- 342 square miles from San Ysidro
on the Mexican border to Rancho Bernardo, 30 miles north -- so it places nothing. "La Jolla" is worse: it is a
community of the City of San Diego whose name the chains borrow for the University City / Golden Triangle
business district (La Jolla Village Drive, Executive Drive, Genesee Avenue), whose own postal code is 92122 and
whose own postal city is SAN DIEGO. A hotel on La Jolla Village Drive may carry 92037 or 92122 depending on which
side of the street it stands; each is placed by its own code. "Del Mar" is the same trap in the north: Carmel
Valley (92130, City of San Diego) carries "Del Mar" in half its hotel names.

THE COASTAL STRUCTURE TEST (PHASE 3): TWELVE TRAVELLER SUBMARKETS, NOT ONE "SAN DIEGO BEACHES" PAGE
-------------------------------------------------------------------------------------------------
Downtown / Gaslamp, the Embarcadero waterfront, Little Italy and Harbor Island share ONE postal code (92101) and
are therefore ONE corridor with named overlays -- the registry never splits a code. The beach communities do NOT
share codes and each keeps its own corridor because the traveller intent differs: Ocean Beach (92107) is the
dog-beach bohemian village, Mission / Pacific Beach (92109) the boardwalk and bay-resort strip, La Jolla (92037)
the cove-and-village luxury coast, Coronado (92118) the island resort city, Del Mar / Solana Beach the racetrack
and fairground coast, Encinitas the surf-town coast, Carlsbad the resort-and-Legoland city and Oceanside the
harbour-and-pier city. Each publishes only when it meets the threshold on its own.

THE AIRPORT TEST: SAN OWNS NO POSTAL CODE -- THE PBI / FLL FINDING, NOT THE JAX ONE
---------------------------------------------------------------------------------
San Diego International (SAN) sits on North Harbor Drive inside 92101, the downtown code. Its hotel district is
split three ways: Harbor Island (92101), North Harbor Drive / Shelter Island / Rosecrans (92106) and Pacific
Highway / Old Town / Midway (92110). An "airport" corridor could only be built by splitting 92101 and 92110,
which the partition forbids. The airport is an OVERLAY reported across three corridors; the corridor carrying
its name is point-loma-shelter-island-airport, whose own code 92106 carries the North Harbor Drive airport
hotels. A measurement, not a preference.

NO CRUISE, MILITARY OR CONVENTION CORRIDOR
------------------------------------------
The B Street and Broadway cruise terminals and the San Diego Convention Center are all in 92101 (downtown) -- the
PortMiami finding. Naval Base San Diego (92136), NAS North Island (92135), Naval Amphibious Base Coronado
(92155), MCRD (92140), MCAS Miramar (92145), Naval Base Point Loma (92106 / 92147) and Camp Pendleton (92055)
are military; their Navy Lodge / Navy Gateway Inns billeting is NOT public lodging and is refused by name. The
military-only postal codes are OUTSIDE.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/san_diego_ca.json
  launch_packages/pettripfinder/markets/proposed/san-diego-ca.json
  launch_packages/pettripfinder/markets/reports/san_diego_ca_geography_001.json
  launch_packages/pettripfinder/markets/reports/san_diego_ca_corridor_registry_001.json
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

WORK_ORDER = "PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-diego-ca"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "san_diego_ca.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "san-diego-ca.json")
REPORT_OUT = os.path.join(REPORTS, "san_diego_ca_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "san_diego_ca_corridor_registry_001.json")
AS_OF = "2026-09-25"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown-gaslamp-waterfront", "Downtown San Diego, Gaslamp & the Waterfront",
     "Downtown / Gaslamp / Embarcadero / Little Italy", "CORE", "san diego",
     ["92101"],
     "One postal code carrying six traveller districts, reported as overlays and never split: the Gaslamp Quarter "
     "(Fifth Avenue, Petco Park, the convention center's back door), East Village, the Marina district and "
     "Seaport Village, the Embarcadero / North Harbor Drive waterfront with the B Street and Broadway cruise "
     "terminals and the USS Midway, Little Italy (India Street, Kettner Boulevard), Cortez Hill and Columbia, and "
     "HARBOR ISLAND -- the airport-hotel peninsula on SAN's south side. San Diego International itself sits in "
     "this code."),
    ("point-loma-shelter-island-airport", "Point Loma, Shelter Island & the Airport",
     "Point Loma / Shelter Island / SAN", "CORE", "san diego",
     ["92106"],
     "Point Loma's bay side: Shelter Island's marina hotels, the North Harbor Drive airport-hotel strip on SAN's "
     "west end, Liberty Station, Rosecrans Street and Cabrillo National Monument. The corridor that carries the "
     "airport's name, because its code carries the North Harbor Drive airport hotels; Harbor Island (92101) and "
     "Pacific Highway (92110) carry the rest and report the airport as an overlay."),
    ("old-town-midway", "Old Town & Midway", "Old Town / Midway / Pacific Highway", "CORE", "san diego",
     ["92110"],
     "Old Town San Diego State Historic Park and San Diego Avenue, the Pacific Highway and Rosecrans motor-inn "
     "row on SAN's east side, the Midway / Sports Arena district (Pechanga Arena) and Morena. Old Town is its own "
     "postal code and its own traveller product -- the historic park and the trolley hub -- so it is its own "
     "corridor rather than an overlay of downtown."),
    ("mission-valley-hotel-circle", "Mission Valley & Hotel Circle", "Mission Valley / Hotel Circle", "CORE",
     "san diego", ["92108"],
     "Hotel Circle North and South along I-8, Camino del Rio, Rio San Diego Drive, Fashion Valley and Mission "
     "Valley's malls, and Snapdragon Stadium. The market's densest mid-price drive-in and convention-overflow "
     "cluster, one postal code."),
    ("ocean-beach", "Ocean Beach", "Ocean Beach", "CORE", "san diego",
     ["92107"],
     "Newport Avenue, the OB Pier, Sunset Cliffs and the Ocean Beach Dog Beach at the San Diego River mouth. A "
     "distinct beach village with its own traveller intent -- not folded into a generic beaches corridor."),
    ("mission-pacific-beach", "Mission Beach & Pacific Beach", "Mission Beach / Pacific Beach / Mission Bay",
     "CORE", "san diego", ["92109"],
     "Mission Beach's boardwalk and Belmont Park, Pacific Beach's Garnet Avenue and Crystal Pier, and the Mission "
     "Bay resort islands -- Paradise Point, Bahia, Catamaran, the Hyatt Regency Mission Bay and the Mission Bay "
     "Drive / Mission Bay Park motel row. One postal code carries all three, reported as overlays."),
    ("la-jolla", "La Jolla", "La Jolla", "CORE", "la jolla",
     ["92037", "92093"],
     "The La Jolla village (Prospect Street, the Cove, Girard Avenue), La Jolla Shores, Torrey Pines and the "
     "Scripps / UCSD coast, whose own postal code is 92037 (92093 is the UC San Diego campus). NOT the "
     "University City / Golden Triangle business district that the chains market as 'La Jolla' -- that is 92122, "
     "postal city San Diego, and its own corridor."),
    ("utc-golden-triangle-sorrento", "UTC, Golden Triangle & Sorrento Valley",
     "UTC / Golden Triangle / Sorrento Valley", "CORE", "san diego",
     ["92121", "92122"],
     "University City (La Jolla Village Drive, Executive Drive, Genesee Avenue, Westfield UTC) and the Sorrento "
     "Valley / Sorrento Mesa biotech district. The corporate and research lodging cluster the chains call 'La "
     "Jolla' and 'UTC'; placed by its own codes, 92122 and 92121."),
    ("uptown-hillcrest-north-park", "Uptown, Hillcrest & North Park", "Hillcrest / North Park / Balboa Park",
     "CORE", "san diego", ["92102", "92103", "92104", "92116"],
     "Hillcrest, Bankers Hill, Mission Hills and Balboa Park's west and north rims (92103), North Park and South "
     "Park (92104), Golden Hill (92102) and Normal Heights / University Heights (92116). Walkable urban "
     "neighbourhoods with the historic inns and boutique hotels nearest the San Diego Zoo."),
    ("kearny-mesa-clairemont", "Kearny Mesa & Clairemont", "Kearny Mesa / Clairemont / Serra Mesa", "CORE",
     "san diego", ["92111", "92117", "92123", "92124"],
     "Kearny Mesa's Clairemont Mesa Boulevard and Aero Drive business hotels (92111 / 92123), Clairemont and Bay "
     "Park (92117), Serra Mesa and Tierrasanta (92124): the I-805 / I-15 / SR-163 business-and-drive cluster "
     "between Mission Valley and Miramar."),
    ("college-area-mission-gorge", "College Area & Mission Gorge", "SDSU / College Area / Mission Gorge", "CORE",
     "san diego", ["92105", "92115", "92119", "92120"],
     "San Diego State University and the College Area / El Cajon Boulevard motor-court row (92115), City Heights "
     "(92105), San Carlos (92119) and Allied Gardens / Grantville on Mission Gorge Road (92120) -- Mission "
     "Valley's east end."),
    ("coronado", "Coronado", "Coronado", "CORRIDOR", "coronado",
     ["92118"],
     "The City of Coronado: the Hotel del Coronado, Orange Avenue, the Coronado Ferry Landing, Glorietta Bay and "
     "the Silver Strand, whose own postal code is 92118. A STRONG CORRIDOR -- a separate city and a resort "
     "destination in its own right across the bridge from downtown, but one whose airport, trolley-less transit, "
     "cruise and convention demand are downtown San Diego's. NAS North Island (92135) and Naval Amphibious Base "
     "Coronado (92155) are military codes and are OUTSIDE."),
    ("del-mar-solana-beach", "Del Mar, Solana Beach & Carmel Valley",
     "Del Mar / Solana Beach / Carmel Valley / Rancho Santa Fe", "CORRIDOR", "del mar",
     ["92014", "92075", "92130", "92067", "92091"],
     "The City of Del Mar (the Del Mar Fairgrounds and racetrack, Camino del Mar), the City of Solana Beach, "
     "Carmel Valley (92130, City of San Diego -- the Del Mar Heights / El Camino Real hotels that carry 'Del Mar' "
     "in their names) and Rancho Santa Fe's resort inns (92067 / 92091). One traveller product: the fairground, "
     "racetrack and North County coast immediately north of Torrey Pines. Carmel Valley is here and not with UTC "
     "because its hotels face the fairground and the I-5 / SR-56 Del Mar interchange, and the choice is "
     "recorded."),
    ("encinitas-cardiff", "Encinitas & Cardiff-by-the-Sea", "Encinitas / Leucadia / Cardiff", "CORRIDOR",
     "encinitas", ["92024", "92007"],
     "The City of Encinitas -- Leucadia, Old Encinitas and Moonlight Beach (92024) and Cardiff-by-the-Sea "
     "(92007). A surf-town coast with its own traveller intent, admitted at CORRIDOR tier."),
    ("carlsbad", "Carlsbad", "Carlsbad", "CORRIDOR", "carlsbad",
     ["92008", "92009", "92010", "92011"],
     "The City of Carlsbad: Carlsbad Village and the beach (92008), La Costa and Aviara (92009 / 92011), "
     "Legoland, the Palomar Airport Road business park and the Flower Fields (92010 / 92011). A STRONG CORRIDOR "
     "with its own CVB (Visit Carlsbad) and several resort campuses; recorded as this market's NAMED first "
     "candidate for promotion to a standalone 'North County coast' market."),
    ("oceanside", "Oceanside", "Oceanside", "CORRIDOR", "oceanside",
     ["92054", "92056", "92057", "92058"],
     "The City of Oceanside: the harbour, the pier and the Coast Highway (92054), and the SR-76 / College "
     "Boulevard inland codes (92056 / 92057 / 92058). The northern end of the San Diego coast, 35 miles from "
     "downtown, admitted at CORRIDOR tier with its own CVB (Visit Oceanside). Camp Pendleton (92055) is a "
     "military code and is OUTSIDE."),
    ("south-bay-chula-vista", "South Bay: Chula Vista, National City & Imperial Beach",
     "Chula Vista / National City / Imperial Beach / San Ysidro", "CORRIDOR", "chula vista",
     ["91902", "91910", "91911", "91913", "91914", "91915", "91932", "91950", "92113", "92114", "92139", "92154",
      "92173"],
     "The South Bay: Chula Vista's bayfront (the Gaylord Pacific resort) and its I-5 / I-805 / Otay Ranch "
     "inventory, National City's Mile of Cars and bay, Bonita, Imperial Beach's pier and beach, and the City of "
     "San Diego's southern codes -- Barrio Logan (92113), Encanto (92114), Paradise Hills (92139), Otay Mesa "
     "(92154) and the San Ysidro border crossing (92173). Imperial Beach is a real beach town but carries too "
     "little inventory for a corridor of its own; it is an overlay here and the choice is recorded. Tijuana, "
     "across the border, is MEXICO and OUTSIDE."),
    ("rancho-bernardo-poway-i15", "Rancho Bernardo, Poway & the I-15 Corridor",
     "Rancho Bernardo / Poway / Mira Mesa / Scripps Ranch", "CORRIDOR", "san diego",
     ["92064", "92126", "92127", "92128", "92129", "92131"],
     "The I-15 inland corridor inside and beside the City of San Diego: Mira Mesa (92126), Scripps Ranch "
     "(92131), Rancho Peñasquitos (92129), Rancho Bernardo and 4S Ranch (92127 / 92128) and the City of Poway "
     "(92064). Business, golf-resort and drive-market lodging."),
    ("east-county-i8", "East County: La Mesa, El Cajon & Santee", "La Mesa / El Cajon / Santee / Lakeside",
     "FRINGE", "la mesa",
     ["91941", "91942", "91945", "91977", "91978", "92019", "92020", "92021", "92040", "92071"],
     "The I-8 / SR-125 / SR-52 East County: La Mesa (91941 / 91942), Lemon Grove (91945), Spring Valley (91977 / "
     "91978), El Cajon (92019 / 92020 / 92021), Lakeside (92040) and Santee (92071). Drive-market and budget "
     "lodging plus two tribal casino resorts (Sycuan in 92019, Barona in 92040). Admitted at FRINGE so the inland "
     "inventory is ACCOUNTED FOR rather than silently dropped."),
    ("escondido-san-marcos-vista", "Escondido, San Marcos & Vista", "Escondido / San Marcos / Vista", "FRINGE",
     "escondido",
     ["92025", "92026", "92027", "92029", "92069", "92078", "92081", "92083", "92084"],
     "Inland North County on I-15 and SR-78: Escondido (the Safari Park, Stone Brewing), San Marcos (Cal State "
     "San Marcos) and Vista. Admitted at FRINGE -- a metro drive market 30 miles from downtown, oriented to the "
     "North County coast and the I-15 corridor."),
]

OUTSIDE = [
    ("Temecula / Murrieta / Temecula Valley wine country -- RIVERSIDE COUNTY", "CA",
     ["92589", "92590", "92591", "92592", "92593", "92562", "92563", "92564", "92595", "92596", "92584", "92585",
      "92586", "92587", "92530", "92532"],
     "RIVERSIDE COUNTY; FUTURE_STANDALONE temecula-valley-ca. Refused by name and by county. Temecula is 60 "
     "miles north of downtown on I-15, in another county, with its own wine-country resort product, its own CVB "
     "(Visit Temecula Valley) and its own casino resort (Pechanga). Its marketing reaches for 'San Diego' and "
     "its own postal code refuses it."),
    ("Palm Springs / Coachella Valley -- RIVERSIDE COUNTY desert", "CA",
     ["92262", "92263", "92264", "92270", "92276", "92234", "92240", "92241", "92253", "92260", "92201", "92203",
      "92210", "92211", "92236", "92282"],
     "RIVERSIDE COUNTY desert; FUTURE_STANDALONE palm-springs-ca. Refused by name: 140 miles by road, its own "
     "airport (PSP), its own resort market."),
    ("Orange County -- San Clemente / Dana Point / San Juan Capistrano / Laguna / Irvine / Anaheim", "CA",
     ["92672", "92673", "92674", "92629", "92624", "92675", "92677", "92651", "92656", "92691", "92692", "92694",
      "92612", "92614", "92618", "92620", "92626", "92660", "92663", "92648", "92649", "92802", "92801", "92805",
      "92806", "92868", "92840"],
     "ORANGE COUNTY; FUTURE_STANDALONE orange-county-ca. Refused by name and by county. San Clemente is the first "
     "town north of Camp Pendleton and the county line; nothing north of the line is San Diego. The 926xx-928xx "
     "prefixes are Orange County and are refused by prefix as well."),
    ("Los Angeles County and the rest of Southern California", "CA",
     ["90001", "90012", "90045", "90401", "91101", "91502", "91601", "91765", "91766"],
     "OUTSIDE by name. Los Angeles is 120 miles north; every 900xx-918xx code is refused by prefix."),
    ("Fallbrook / Bonsall / Valley Center / Pala / Pauma -- rural inland North County", "CA",
     ["92028", "92003", "92082", "92059", "92061", "92088"],
     "San Diego County's rural inland north: Fallbrook and Bonsall's avocado country and the SR-76 tribal casino "
     "resorts (Harrah's Resort Southern California in Valley Center, Pala Casino Spa Resort, Pauma). A "
     "destination-casino and rural product, oriented to Temecula as much as to San Diego. OUTSIDE by name; the "
     "casino resorts are recorded, not absorbed."),
    ("Ramona / Julian / Santa Ysabel / Warner Springs -- the backcountry mountains", "CA",
     ["92065", "92036", "92070", "92086", "92066"],
     "San Diego County's mountain backcountry: Ramona, the Julian apple-and-gold-rush town and the Warner "
     "Springs ranch country, 45-60 miles from downtown. A separate mountain-weekend product. OUTSIDE by name."),
    ("Borrego Springs / Anza-Borrego Desert", "CA",
     ["92004"],
     "San Diego County's desert: Borrego Springs inside Anza-Borrego Desert State Park, 90 miles from downtown "
     "over the mountains. A separate desert-resort product. OUTSIDE by name."),
    ("Alpine / Jamul / Descanso / Pine Valley / Campo / Mount Laguna -- the I-8 backcountry", "CA",
     ["91901", "91935", "91916", "91962", "91906", "91905", "91934", "91948", "91931", "91917", "91963", "91980"],
     "San Diego County's I-8 and SR-94 backcountry east of El Cajon, including the Viejas (Alpine) and Jamul "
     "casino resorts. Rural and mountain lodging, oriented to the Cleveland National Forest. OUTSIDE by name; "
     "the admitted East County stops at El Cajon, Santee and Lakeside."),
    ("Military installations -- Navy / Marine Corps postal codes", "CA",
     ["92055", "92135", "92136", "92140", "92145", "92147", "92155", "92134"],
     "Camp Pendleton (92055), NAS North Island (92135), Naval Base San Diego (92136), MCRD San Diego (92140), "
     "MCAS Miramar (92145), Naval Base Point Loma (92147), Naval Amphibious Base Coronado (92155) and Naval "
     "Medical Center San Diego (92134). Military billeting (Navy Lodge, Navy Gateway Inns & Suites, Inns of the "
     "Corps) is NOT public lodging. OUTSIDE."),
    ("Tijuana / Rosarito / Ensenada -- MEXICO", "BC",
     [],
     "MEXICO (Baja California). OUTSIDE by COUNTRY: no US postal code, no US premises, never a PetTripFinder "
     "admission. Recorded because Tijuana hotels market to San Diego travellers and because the San Ysidro "
     "border crossing sits inside the admitted South Bay corridor."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused county is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, reason)
OUTSIDE_PREFIXES = [
    ("925", "Riverside County (Temecula / Murrieta / Inland Empire)", "temecula-valley-ca"),
    ("922", "Riverside / Imperial County desert (Palm Springs / Coachella Valley / El Centro)", "palm-springs-ca"),
    ("926", "Orange County", "orange-county-ca"),
    ("927", "Orange County", "orange-county-ca"),
    ("928", "Orange County", "orange-county-ca"),
    ("923", "San Bernardino / Riverside County (Inland Empire)", ""),
    ("924", "San Bernardino County (Inland Empire)", ""),
    ("900", "Los Angeles County", ""), ("901", "Los Angeles County", ""), ("902", "Los Angeles County", ""),
    ("903", "Los Angeles County", ""), ("904", "Los Angeles County", ""), ("905", "Los Angeles County", ""),
    ("906", "Los Angeles County", ""), ("907", "Los Angeles County", ""), ("908", "Los Angeles County", ""),
    ("910", "Los Angeles County", ""), ("911", "Los Angeles County", ""), ("912", "Los Angeles County", ""),
    ("913", "Los Angeles / Ventura County", ""), ("914", "Los Angeles County", ""), ("915", "Los Angeles County", ""),
    ("916", "Los Angeles County", ""), ("917", "Los Angeles / San Bernardino County", ""),
    ("918", "Los Angeles County", ""),
]

#: San Diego County's own postal prefixes. A code under one of these that no corridor claims is an UNCLAIMED San
#: Diego County code -- refused, and named in the boundary audit so it is visible, never silently dropped.
SAN_DIEGO_COUNTY_PREFIXES = ("919", "920", "921")

ADMITTED_COUNTIES = {"san diego"}
OBSERVED_COUNTIES = OrderedDict([
    ("riverside", "temecula-valley-ca / palm-springs-ca"),
    ("orange", "orange-county-ca"),
    ("imperial", "(none -- desert, refused by name)"),
    ("los angeles", "(none -- refused by name)"),
])

#: The county-line rulings the order's Phase 2 / 23 clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("san diego", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. The coast from Imperial Beach to Oceanside and the metro from the border to "
                   "Rancho Bernardo and El Cajon are admitted; the rural inland north (Fallbrook, Valley Center, "
                   "Pala, Pauma), the mountain backcountry (Ramona, Julian, Warner Springs), the I-8 backcountry "
                   "(Alpine, Jamul, Pine Valley) and the desert (Borrego Springs) are REFUSED by name. County "
                   "inclusion is not traveller-market inclusion."),
        ("military", "Camp Pendleton, NAS North Island, Naval Base San Diego, MCRD, MCAS Miramar, Naval Base Point "
                     "Loma and NAB Coronado are military codes; billeting is refused by name."),
    ])),
    ("riverside", OrderedDict([
        ("ruling", "REFUSED. Temecula / Murrieta (FUTURE_STANDALONE temecula-valley-ca) and the Coachella Valley "
                   "(FUTURE_STANDALONE palm-springs-ca) are separate markets in another county."),
    ])),
    ("orange", OrderedDict([
        ("ruling", "REFUSED. San Clemente, Dana Point and everything north of the county line is Orange County "
                   "(FUTURE_STANDALONE orange-county-ca)."),
    ])),
    ("mexico", OrderedDict([
        ("ruling", "REFUSED BY COUNTRY. Tijuana, Rosarito and Ensenada are Baja California, Mexico."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / member only).
NONPUBLIC_NAMES = {
    "navy lodge": "US Navy billeting -- not public lodging",
    "navy lodge san diego": "US Navy billeting -- not public lodging",
    "navy lodge north island": "US Navy billeting -- not public lodging",
    "navy gateway inns": "US Navy billeting -- not public lodging",
    "navy gateway inns & suites": "US Navy billeting -- not public lodging",
    "navy gateway inns and suites": "US Navy billeting -- not public lodging",
    "inns of the corps": "US Marine Corps billeting -- not public lodging",
    "the inn at mcrd": "US Marine Corps billeting -- not public lodging",
    "admiral kidd catering and conference center": "US Navy facility -- not public lodging",
}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-gaslamp-waterfront", "San Diego", "Downtown / Gaslamp / Embarcadero / Little Italy",
     32.7140, -117.1600, 2800, True),
    ("point-loma-shelter-island-airport", "San Diego", "Point Loma / Shelter Island / SAN", 32.7250, -117.2200,
     4500, True),
    ("old-town-midway", "San Diego", "Old Town / Midway", 32.7520, -117.2000, 3200, True),
    ("mission-valley-hotel-circle", "San Diego", "Mission Valley / Hotel Circle", 32.7650, -117.1650, 3800, True),
    ("ocean-beach", "San Diego", "Ocean Beach", 32.7470, -117.2450, 2200, True),
    ("mission-pacific-beach", "San Diego", "Mission Beach / Pacific Beach / Mission Bay", 32.7900, -117.2350,
     4200, True),
    ("la-jolla", "La Jolla", "La Jolla", 32.8420, -117.2600, 4800, True),
    ("utc-golden-triangle-sorrento", "San Diego", "UTC / Golden Triangle / Sorrento Valley", 32.8850, -117.2150,
     5500, True),
    ("uptown-hillcrest-north-park", "San Diego", "Hillcrest / North Park / Balboa Park", 32.7450, -117.1400,
     4200, True),
    ("kearny-mesa-clairemont", "San Diego", "Kearny Mesa / Clairemont", 32.8150, -117.1600, 6000, True),
    ("college-area-mission-gorge", "San Diego", "SDSU / College Area / Mission Gorge", 32.7700, -117.0800, 6000,
     True),
    ("coronado", "Coronado", "Coronado", 32.6850, -117.1750, 5000, True),
    ("del-mar-solana-beach", "Del Mar", "Del Mar / Solana Beach / Carmel Valley", 32.9600, -117.2300, 7000, True),
    ("encinitas-cardiff", "Encinitas", "Encinitas / Cardiff", 33.0400, -117.2850, 5000, True),
    ("carlsbad", "Carlsbad", "Carlsbad", 33.1250, -117.2850, 8000, True),
    ("oceanside", "Oceanside", "Oceanside", 33.2100, -117.3300, 8000, True),
    ("south-bay-chula-vista", "Chula Vista", "South Bay", 32.6150, -117.0700, 12000, True),
    ("rancho-bernardo-poway-i15", "San Diego", "I-15 / Rancho Bernardo / Poway", 32.9600, -117.0850, 11000, True),
    ("east-county-i8", "El Cajon", "East County", 32.7900, -116.9900, 11000, True),
    ("escondido-san-marcos-vista", "Escondido", "Escondido / San Marcos / Vista", 33.1300, -117.1500, 13000,
     True),
    ("obs-temecula", "Temecula", "Temecula / Murrieta -- OBSERVATION ONLY (Riverside County)", 33.5000, -117.1500,
     12000, False),
    ("obs-san-clemente", "San Clemente", "San Clemente / Dana Point -- OBSERVATION ONLY (Orange County)",
     33.4400, -117.6200, 9000, False),
    ("obs-fallbrook-pala", "Fallbrook", "Fallbrook / Valley Center / Pala -- OBSERVATION ONLY", 33.3200, -117.1000,
     15000, False),
    ("obs-julian-ramona", "Julian", "Ramona / Julian -- OBSERVATION ONLY (backcountry)", 33.0500, -116.7300, 18000,
     False),
    ("obs-borrego", "Borrego Springs", "Borrego Springs -- OBSERVATION ONLY (desert)", 33.2560, -116.3750, 10000,
     False),
    ("obs-tijuana", "Tijuana", "Tijuana, MEXICO -- OBSERVATION ONLY (out of country)", 32.5100, -117.0300, 9000,
     False),
]

#: The Overpass / observation box. It reaches north past the Orange and Riverside County lines (San Clemente,
#: Temecula), east over the mountains to Borrego Springs and south across the border into Tijuana, so the census
#: counts what it refuses. Palm Springs lies outside it (lat 33.83) and is audited from the brand lanes instead.
BOUNDS = {"min_lat": 32.45, "max_lat": 33.56, "min_lng": -117.66, "max_lng": -116.08}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Gaslamp Quarter", 32.7115, -117.1600, 0.6),
    ("San Diego Convention Center", 32.7065, -117.1620, 0.5),
    ("East Village / Petco Park", 32.7100, -117.1530, 0.7),
    ("Marina District / Seaport Village", 32.7090, -117.1700, 0.6),
    ("Embarcadero / Waterfront", 32.7180, -117.1730, 0.9),
    ("Little Italy", 32.7240, -117.1690, 0.6),
    ("Cortez Hill / Columbia", 32.7200, -117.1600, 0.6),
    ("Harbor Island", 32.7250, -117.1920, 1.2),
    ("San Diego International Airport (SAN)", 32.7338, -117.1933, 1.6),
    ("Shelter Island", 32.7170, -117.2280, 1.0),
    ("North Harbor Drive / Point Loma airport strip", 32.7280, -117.2120, 0.9),
    ("Liberty Station", 32.7390, -117.2150, 0.9),
    ("Point Loma / Rosecrans", 32.7330, -117.2300, 1.8),
    ("Old Town San Diego", 32.7540, -117.1970, 0.9),
    ("Pacific Highway / Old Town motor inns", 32.7500, -117.2000, 0.9),
    ("Midway / Sports Arena", 32.7550, -117.2120, 1.2),
    ("Hotel Circle", 32.7600, -117.1800, 1.2),
    ("Mission Valley / Fashion Valley", 32.7680, -117.1600, 1.6),
    ("Rio San Diego / Snapdragon Stadium", 32.7780, -117.1270, 1.6),
    ("Ocean Beach / Newport Avenue", 32.7480, -117.2490, 1.0),
    ("Ocean Beach Dog Beach", 32.7530, -117.2510, 0.5),
    ("Mission Beach / Belmont Park", 32.7710, -117.2520, 1.0),
    ("Pacific Beach / Crystal Pier", 32.7970, -117.2560, 1.2),
    ("Mission Bay resort islands", 32.7800, -117.2300, 1.8),
    ("Mission Bay Drive / Mission Bay Park", 32.7950, -117.2150, 1.2),
    ("La Jolla Village / the Cove", 32.8470, -117.2740, 1.0),
    ("La Jolla Shores", 32.8580, -117.2560, 1.0),
    ("Torrey Pines / UCSD", 32.8900, -117.2450, 2.0),
    ("University City / UTC", 32.8710, -117.2110, 1.6),
    ("Golden Triangle / Executive Drive", 32.8760, -117.2220, 1.2),
    ("Sorrento Valley / Sorrento Mesa", 32.9000, -117.2000, 2.4),
    ("Hillcrest", 32.7480, -117.1640, 1.0),
    ("Bankers Hill / Balboa Park west", 32.7310, -117.1600, 0.9),
    ("Balboa Park / San Diego Zoo", 32.7340, -117.1470, 1.2),
    ("North Park", 32.7470, -117.1300, 1.2),
    ("Kearny Mesa / Clairemont Mesa Boulevard", 32.8330, -117.1400, 2.0),
    ("Clairemont / Bay Park", 32.8150, -117.1970, 2.0),
    ("SDSU / College Area", 32.7730, -117.0710, 1.8),
    ("Mission Gorge / Grantville", 32.7900, -117.1000, 1.8),
    ("Hotel del Coronado", 32.6810, -117.1780, 0.7),
    ("Coronado Orange Avenue / Ferry Landing", 32.6950, -117.1700, 1.2),
    ("Silver Strand", 32.6400, -117.1400, 2.5),
    ("Del Mar Fairgrounds / racetrack", 32.9760, -117.2600, 1.2),
    ("Del Mar village / Camino del Mar", 32.9600, -117.2650, 1.0),
    ("Solana Beach", 32.9920, -117.2700, 1.2),
    ("Carmel Valley / Del Mar Heights", 32.9450, -117.2250, 2.0),
    ("Rancho Santa Fe", 33.0200, -117.2020, 2.5),
    ("Encinitas / Moonlight Beach", 33.0480, -117.2930, 1.4),
    ("Leucadia", 33.0700, -117.3050, 1.2),
    ("Cardiff-by-the-Sea", 33.0200, -117.2800, 1.2),
    ("Carlsbad Village", 33.1590, -117.3490, 1.2),
    ("Legoland / Palomar Airport Road", 33.1270, -117.3100, 2.0),
    ("La Costa / Aviara", 33.0950, -117.2650, 2.4),
    ("Oceanside Harbor / Pier", 33.1950, -117.3830, 1.6),
    ("Oceanside Mission Avenue / SR-76", 33.2100, -117.3300, 3.0),
    ("Chula Vista Bayfront", 32.6250, -117.1000, 1.6),
    ("Chula Vista / I-805 / Otay Ranch", 32.6300, -117.0100, 4.0),
    ("National City", 32.6780, -117.1000, 2.0),
    ("Imperial Beach pier", 32.5790, -117.1320, 1.4),
    ("San Ysidro border crossing", 32.5430, -117.0290, 1.6),
    ("Otay Mesa", 32.5650, -116.9700, 3.0),
    ("Rancho Bernardo", 33.0200, -117.0800, 3.0),
    ("Poway", 32.9620, -117.0360, 3.0),
    ("Mira Mesa / Scripps Ranch", 32.9100, -117.1300, 3.0),
    ("La Mesa", 32.7680, -117.0230, 2.4),
    ("El Cajon", 32.7950, -116.9620, 3.0),
    ("Santee", 32.8380, -116.9730, 2.4),
    ("Escondido", 33.1200, -117.0860, 3.4),
    ("San Marcos", 33.1400, -117.1660, 3.0),
    ("Vista", 33.2000, -117.2420, 3.0),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Harbor Island", re.compile(r"\bharbor island dr\b", re.I)),
    ("Shelter Island", re.compile(r"\bshelter island dr\b|\bscott st\b", re.I)),
    ("North Harbor Drive / Point Loma airport strip", re.compile(r"\bn(orth)? harbor dr\b(?=.*9210[16])", re.I)),
    ("Hotel Circle", re.compile(r"\bhotel cir(cle)?\b", re.I)),
    ("Mission Valley / Fashion Valley", re.compile(r"\bcamino del rio\b|\bfriars rd\b|\bfashion valley\b", re.I)),
    ("Rio San Diego / Snapdragon Stadium", re.compile(r"\brio san diego\b", re.I)),
    ("Pacific Highway / Old Town motor inns", re.compile(r"\bpacific h(igh)?wy\b", re.I)),
    ("Old Town San Diego", re.compile(r"\bsan diego ave\b|\bold town ave\b|\bjuan st\b|\btaylor st\b", re.I)),
    ("Midway / Sports Arena", re.compile(r"\bsports arena b(lv)?d\b|\bmidway dr\b|\brosecrans st\b(?=.*92110)",
                                         re.I)),
    ("Mission Bay resort islands", re.compile(r"\bvacation rd\b|\bw(est)? mission bay dr\b|\bgleason rd\b",
                                              re.I)),
    ("Mission Bay Drive / Mission Bay Park", re.compile(r"\bmission bay dr\b|\bgrand ave\b(?=.*92109)", re.I)),
    ("Mission Beach / Belmont Park", re.compile(r"\bmission b(lv)?d\b(?=.*92109)|\bocean front walk\b", re.I)),
    ("Pacific Beach / Crystal Pier", re.compile(r"\bgarnet ave\b|\bmission blvd\b|\bocean b(lv)?d\b(?=.*92109)",
                                                re.I)),
    ("Ocean Beach / Newport Avenue", re.compile(r"\bnewport ave\b|\babbott st\b|\bsunset cliffs\b", re.I)),
    ("La Jolla Village / the Cove", re.compile(r"\bprospect st\b|\bgirard ave\b|\bcoast b(lv)?d\b|\bpearl st\b",
                                               re.I)),
    ("La Jolla Shores", re.compile(r"\bla jolla shores dr\b|\bspindrift dr\b|\bcamino del oro\b", re.I)),
    ("Torrey Pines / UCSD", re.compile(r"\bn(orth)? torrey pines rd\b|\bgilman dr\b", re.I)),
    ("Golden Triangle / Executive Drive", re.compile(r"\bexecutive (dr|way|sq)\b|\bla jolla village dr\b", re.I)),
    ("University City / UTC", re.compile(r"\bgenesee ave\b|\bnobel dr\b|\bregents rd\b", re.I)),
    ("Sorrento Valley / Sorrento Mesa", re.compile(r"\bsorrento\b|\bmira mesa b(lv)?d\b(?=.*92121)|\bscranton rd\b",
                                                   re.I)),
    ("Hotel del Coronado", re.compile(r"\borange ave\b(?=.*1500)|\bglorietta\b", re.I)),
    ("Silver Strand", re.compile(r"\bsilver strand\b", re.I)),
    ("Del Mar village / Camino del Mar", re.compile(r"\bcamino del mar\b|\bjimmy durante\b", re.I)),
    ("Carmel Valley / Del Mar Heights", re.compile(r"\bel camino real\b(?=.*92130)|\bcarmel (creek|mountain|valley)\b|"
                                                   r"\bgrand del mar\b", re.I)),
    ("Legoland / Palomar Airport Road", re.compile(r"\blegoland\b|\bpalomar airport rd\b|\bsea gate rd\b|"
                                                   r"\bcar country dr\b", re.I)),
    ("La Costa / Aviara", re.compile(r"\bla costa\b|\baviara\b|\bcosta del mar\b", re.I)),
    ("Carlsbad Village", re.compile(r"\bcarlsbad b(lv)?d\b|\bcarlsbad village dr\b|\bstate st\b(?=.*9200)",
                                    re.I)),
    ("Oceanside Harbor / Pier", re.compile(r"\bharbor dr s\b|\bn(orth)? pacific st\b|\bmission ave\b(?=.*92054)|"
                                           r"\bcoast h(igh)?wy\b(?=.*92054)", re.I)),
    ("Chula Vista Bayfront", re.compile(r"\bmarina pkwy\b|\bgaylord\b|\bbayfront\b", re.I)),
    ("National City", re.compile(r"\bmile of cars\b|\bplaza b(lv)?d\b(?=.*91950)", re.I)),
    ("San Ysidro border crossing", re.compile(r"\bsan ysidro b(lv)?d\b|\bcamino de la plaza\b", re.I)),
    ("Imperial Beach pier", re.compile(r"\bseacoast dr\b|\bold palm ave\b", re.I)),
    ("Rancho Bernardo", re.compile(r"\brancho bernardo\b|\bbernardo (center|heights)\b|\bw bernardo dr\b", re.I)),
    ("Kearny Mesa / Clairemont Mesa Boulevard", re.compile(r"\bclairemont mesa b(lv)?d\b|\baero dr\b|"
                                                           r"\bkearny villa\b", re.I)),
    ("SDSU / College Area", re.compile(r"\bel cajon b(lv)?d\b(?=.*9211[56])|\bcollege ave\b", re.I)),
    ("Mission Gorge / Grantville", re.compile(r"\bmission gorge\b", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-gaslamp-waterfront": "Downtown San Diego",
    "point-loma-shelter-island-airport": "Point Loma",
    "old-town-midway": "Old Town San Diego",
    "mission-valley-hotel-circle": "Mission Valley",
    "ocean-beach": "Ocean Beach",
    "mission-pacific-beach": "Pacific Beach",
    "la-jolla": "La Jolla",
    "utc-golden-triangle-sorrento": "University City / UTC",
    "uptown-hillcrest-north-park": "Hillcrest",
    "kearny-mesa-clairemont": "Kearny Mesa",
    "college-area-mission-gorge": "College Area",
    "coronado": "Coronado",
    "del-mar-solana-beach": "Del Mar",
    "encinitas-cardiff": "Encinitas",
    "carlsbad": "Carlsbad",
    "oceanside": "Oceanside",
    "south-bay-chula-vista": "Chula Vista",
    "rancho-bernardo-poway-i15": "Rancho Bernardo",
    "east-county-i8": "El Cajon",
    "escondido-san-marcos-vista": "Escondido",
}

#: PHASE 3 -- the order's twelve coastal traveller submarkets, each classified explicitly.
COASTAL_STRUCTURE = OrderedDict([
    ("A. Downtown / Gaslamp", OrderedDict([
        ("class", "CORE"), ("corridor", "downtown-gaslamp-waterfront"), ("postal_codes", ["92101"]),
        ("ruling", "CORE. The Gaslamp Quarter, East Village, the Marina district and the convention center share "
                   "92101 with the waterfront, Little Italy and Harbor Island; one corridor, named overlays.")])),
    ("B. Waterfront / Embarcadero", OrderedDict([
        ("class", "CORE (overlay of downtown-gaslamp-waterfront)"), ("corridor", "downtown-gaslamp-waterfront"),
        ("postal_codes", ["92101"]),
        ("ruling", "CORE, as an OVERLAY. The Embarcadero, Seaport Village, the cruise terminals and the bayfront "
                   "towers are 92101 -- the same code as the Gaslamp. A separate corridor could only be built by "
                   "SPLITTING 92101, which the partition forbids (the PortMiami / JAXPORT finding). The overlay is "
                   "reported on every row it covers.")])),
    ("C. Airport / Point Loma", OrderedDict([
        ("class", "CORE"), ("corridor", "point-loma-shelter-island-airport"), ("postal_codes", ["92106"]),
        ("ruling", "CORE. SAN owns no postal code (it sits in 92101), so there is no corridor named only for the "
                   "airport -- the PBI / FLL finding, not JAX's. Point Loma's own code 92106 carries Shelter "
                   "Island, Liberty Station and the North Harbor Drive airport strip and is its own corridor; "
                   "Harbor Island (92101) and Pacific Highway (92110) report SAN as an overlay.")])),
    ("D. Mission Valley / Hotel Circle", OrderedDict([
        ("class", "CORE"), ("corridor", "mission-valley-hotel-circle"), ("postal_codes", ["92108"]),
        ("ruling", "CORE. Hotel Circle and Mission Valley are one postal code and the market's densest drive-in "
                   "cluster.")])),
    ("E. Ocean Beach", OrderedDict([
        ("class", "CORE"), ("corridor", "ocean-beach"), ("postal_codes", ["92107"]),
        ("ruling", "CORE, its own corridor. OB is a beach village with its own traveller intent (the Dog Beach, "
                   "Newport Avenue, Sunset Cliffs) and its own postal code; it is not flattened into Mission / "
                   "Pacific Beach.")])),
    ("F. Mission / Pacific Beach", OrderedDict([
        ("class", "CORE"), ("corridor", "mission-pacific-beach"), ("postal_codes", ["92109"]),
        ("ruling", "CORE. Mission Beach, Pacific Beach and the Mission Bay resort islands share 92109; one "
                   "corridor with three overlays.")])),
    ("G. La Jolla", OrderedDict([
        ("class", "CORE"), ("corridor", "la-jolla"), ("postal_codes", ["92037", "92093"]),
        ("ruling", "CORE, and bounded by its OWN code. The chains' 'La Jolla' Golden Triangle hotels (92122, "
                   "postal city San Diego) are a separate corridor, utc-golden-triangle-sorrento.")])),
    ("H. Coronado", OrderedDict([
        ("class", "STRONG CORRIDOR"), ("corridor", "coronado"), ("postal_codes", ["92118"]),
        ("ruling", "STRONG CORRIDOR (registry class CORRIDOR). A separate city and a resort destination of its "
                   "own, but its airport, cruise and convention demand are downtown's and the bridge makes it a "
                   "ten-minute drive. Not CORE because it is a separate municipality with its own traveller "
                   "product; not FUTURE_STANDALONE because it is inseparable from the San Diego visit.")])),
    ("I. Del Mar", OrderedDict([
        ("class", "STRONG CORRIDOR"), ("corridor", "del-mar-solana-beach"),
        ("postal_codes", ["92014", "92075", "92130", "92067", "92091"]),
        ("ruling", "STRONG CORRIDOR. Del Mar, Solana Beach, Carmel Valley and Rancho Santa Fe are one fairground-"
                   "racetrack-and-coast product 20 minutes north of downtown. Carmel Valley (92130) is City of San "
                   "Diego and is placed here on the traveller test; its hotels carry 'Del Mar' in their names, and "
                   "92130 -- not the name -- is what places them.")])),
    ("J. Encinitas", OrderedDict([
        ("class", "STRONG CORRIDOR"), ("corridor", "encinitas-cardiff"), ("postal_codes", ["92024", "92007"]),
        ("ruling", "STRONG CORRIDOR. A surf-town coast with its own intent; small inventory, its own corridor "
                   "because it is its own place, publishing only if it meets the threshold.")])),
    ("K. Carlsbad", OrderedDict([
        ("class", "STRONG CORRIDOR"), ("corridor", "carlsbad"), ("postal_codes", ["92008", "92009", "92010",
                                                                                   "92011"]),
        ("ruling", "STRONG CORRIDOR, with NAMED future optionality. Carlsbad has its own CVB, Legoland and "
                   "several resort campuses, and is the market's first candidate for a standalone 'North County "
                   "coast' market. It is admitted here because SAN is its airport and I-5 makes it a San Diego "
                   "visit; the optionality is recorded so a founder can promote it on the record.")])),
    ("L. Oceanside", OrderedDict([
        ("class", "STRONG CORRIDOR"), ("corridor", "oceanside"), ("postal_codes", ["92054", "92056", "92057",
                                                                                    "92058"]),
        ("ruling", "STRONG CORRIDOR. The northern end of the county's coast, 35 miles from downtown, its own CVB "
                   "and harbour. Admitted at CORRIDOR (not FRINGE) because its beach-and-pier traveller intent is "
                   "coastal San Diego's; not FUTURE_STANDALONE because Camp Pendleton, not Oceanside, is where "
                   "the San Diego coast stops.")])),
])

STRUCTURE_TEST = OrderedDict([
    ("A. Is San Diego one market, or several?",
     "ONE market, san-diego-ca, covering the coast from Imperial Beach to Oceanside and the metro from the "
     "border to Rancho Bernardo and El Cajon. One commercial airport (SAN) serving the whole county, one "
     "tourism authority for the core (the San Diego Tourism Authority), one I-5 / I-8 / I-15 / I-805 road "
     "system. Camp Pendleton and the county line are where that coherence STOPS in the north; the mountains "
     "in the east; the international border in the south."),
    ("B. The City of San Diego is NOT the market -- and 'San Diego' places nothing",
     "The postal city SAN DIEGO covers 342 square miles and 40-odd postal codes. The market is modelled on "
     "traveller districts joined to postal codes, and eight separate cities (Coronado, Del Mar, Solana Beach, "
     "Encinitas, Carlsbad, Oceanside, Chula Vista, National City, Imperial Beach, La Mesa, El Cajon, Santee, "
     "Poway, Escondido, San Marcos, Vista) are admitted by their own codes."),
    ("C. San Diego International (SAN)", COASTAL_STRUCTURE["C. Airport / Point Loma"]["ruling"]),
    ("D. Cruise terminals and the convention center",
     "NO CORRIDOR -- both are in 92101 (downtown). The PortMiami finding: a port or convention corridor could only "
     "split a covered code. Overlays of downtown-gaslamp-waterfront."),
    ("E. Military installations",
     "NO CORRIDOR. The military-only postal codes (92055, 92135, 92136, 92140, 92145, 92147, 92155, 92134) are "
     "OUTSIDE and billeting is refused by name. Naval Base San Diego and NAS North Island are demand drivers for "
     "the South Bay and Coronado corridors, never premises facts."),
    ("F. La Jolla vs San Diego naming",
     COASTAL_STRUCTURE["G. La Jolla"]["ruling"]),
    ("G. The beaches are FIVE corridors, not one 'San Diego beaches' page",
     "Ocean Beach (92107), Mission / Pacific Beach (92109), La Jolla (92037), Coronado (92118) and the North "
     "County coast (Del Mar, Encinitas, Carlsbad, Oceanside -- four corridors) each keep their own traveller "
     "intent. Imperial Beach is the one beach town too small for its own corridor; it is an overlay of the "
     "South Bay and the choice is recorded."),
    ("H. North County inland",
     "Rancho Bernardo / Poway / Mira Mesa is a CORRIDOR on I-15 inside and beside the City of San Diego; "
     "Escondido / San Marcos / Vista is FRINGE; Fallbrook, Valley Center, Pala and Pauma are OUTSIDE (rural and "
     "destination-casino, oriented to Temecula as much as San Diego)."),
    ("I. East County",
     "La Mesa, El Cajon, Santee, Lakeside, Lemon Grove and Spring Valley are ONE FRINGE corridor on I-8 / SR-125; "
     "Alpine, Jamul and the I-8 backcountry are OUTSIDE."),
    ("J. Temecula", "OUTSIDE -- RIVERSIDE COUNTY, FUTURE_STANDALONE temecula-valley-ca. Refused by name, county "
                    "and postal prefix."),
    ("K. Orange County", "OUTSIDE -- FUTURE_STANDALONE orange-county-ca. Refused by county and by postal prefix "
                         "926-928."),
    ("L. Palm Springs / Coachella Valley", "OUTSIDE -- FUTURE_STANDALONE palm-springs-ca. Refused by name and "
                                           "by postal prefix 922."),
    ("M. Tijuana / Mexico", "OUTSIDE by COUNTRY. Never admitted."),
    ("N. Los Angeles", "OUTSIDE. Refused by postal prefix 900-918."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel operation."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP). A unit designator ('Ste', "
     "'Unit', '#', 'Apt', 'PH', 'Villa') in a registry address means the record is a UNIT INSIDE a building, "
     "which is never a hotel identity."),
    ("hotel_vs_residence_boundary",
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. The "
     "residences are refused as RESORT_RESIDENCE even where they share the address, the brand, the entrance, "
     "the pool and the booking engine. San Diego's specific exposures: the downtown and Little Italy condo-hotel "
     "towers and serviced-apartment operators, the Mission Beach / Pacific Beach vacation-rental cottages and "
     "beach rentals, La Jolla's and Coronado's resort residences and beach cottages, the Carlsbad and Oceanside "
     "resort timeshare programmes (Marriott Vacation Club, Hilton Vacation Club / Grand Pacific, Wyndham Destinations, "
     "WorldMark, Welk, Grand Pacific Palisades, Hyatt Vacation Club, Carlsbad Seapointe), and property-management "
     "portfolios presented under a hotel-like name."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort is admitted ONLY if the operator's own page sells nightly "
     "public stays at that premises under a public hotel name. Owner-only / member-only / points-only resorts and "
     "individual timeshare units are TIMESHARE and are never admitted."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared "
     "amenities or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never "
     "published as one."),
    ("military_lodging",
     "Navy Lodge, Navy Gateway Inns & Suites and Inns of the Corps are government billeting, not public lodging, "
     "and are refused by name."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("92101", ["Downtown", "Gaslamp Quarter", "East Village", "Little Italy", "Marina", "Embarcadero",
               "Harbor Island", "Cortez Hill", "(SAN airport)"]),
    ("92106", ["Point Loma", "Shelter Island", "Liberty Station", "(North Harbor Drive airport strip)"]),
    ("92109", ["Pacific Beach", "Mission Beach", "Mission Bay"]),
    ("92110", ["Old Town", "Midway", "Morena", "Bay Park"]),
    ("92037", ["La Jolla", "La Jolla Shores", "Torrey Pines"]),
    ("92122", ["San Diego", "University City", "(marketed as 'La Jolla')"]),
    ("92130", ["San Diego", "Carmel Valley", "(marketed as 'Del Mar')"]),
    ("92024", ["Encinitas", "Leucadia", "Olivenhain"]),
    ("92118", ["Coronado"]),
    ("91910", ["Chula Vista"]),
])

FUTURE_MARKETS = OrderedDict([
    ("temecula-valley-ca", "Temecula / Murrieta -- Riverside County wine country and Pechanga, 60 miles north on "
                           "I-15. The single most important refusal in this order: it markets itself to San Diego "
                           "travellers and its own postal code refuses it."),
    ("orange-county-ca", "Orange County -- San Clemente, Dana Point, Laguna, Irvine, Anaheim; everything north of "
                         "the county line."),
    ("palm-springs-ca", "Palm Springs / the Coachella Valley -- Riverside County desert resorts."),
    ("north-county-coast-ca", "NAMED OPTIONALITY, not a refusal. Carlsbad (with Oceanside and Encinitas) is "
                              "ADMITTED here at CORRIDOR tier and recorded as this market's first candidate for "
                              "promotion to a standalone North County coast market."),
])

#: Markets that are ALREADY LIVE. None of them owns a California postal code; named so the collision guards know
#: the only exposure is NAME, never premises.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("jacksonville-fl", "Jacksonville / Northeast Florida, live as production market #34 (deploy "
                        "6ab6c8798bd9daf5038ae3e5) -- the CURRENT LIVE market at this order's authoring time. No "
                        "live market owns a California postal code; the only cross-market exposure is a shared "
                        "chain NAME, which rule G and the bare-chain test guard."),
])

MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "san diego,": "san diego", "san diego ca": "san diego", "sandiego": "san diego", "sd": "san diego",
    "san deigo": "san diego", "san diego, ca": "san diego",
    "lajolla": "la jolla", "la jolla,": "la jolla", "la jolla ca": "la jolla",
    "coronado,": "coronado", "coronado island": "coronado",
    "del mar,": "del mar", "delmar": "del mar",
    "solana bch": "solana beach", "solana beach,": "solana beach",
    "cardiff": "encinitas", "cardiff by the sea": "encinitas", "cardiff-by-the-sea": "encinitas",
    "leucadia": "encinitas", "olivenhain": "encinitas",
    "carlsbad,": "carlsbad", "la costa": "carlsbad",
    "oceanside,": "oceanside",
    "chula vista,": "chula vista", "national city,": "national city", "imperial bch": "imperial beach",
    "san ysidro": "san diego", "otay mesa": "san diego", "pacific beach": "san diego", "mission beach": "san diego",
    "ocean beach": "san diego", "point loma": "san diego", "mission valley": "san diego",
    "rancho bernardo": "san diego", "carmel valley": "san diego", "sorrento valley": "san diego",
    "rancho santa fe": "rancho santa fe", "rsf": "rancho santa fe",
    "la mesa,": "la mesa", "el cajon,": "el cajon", "santee,": "santee",
    "escondido,": "escondido", "san marcos,": "san marcos", "vista,": "vista", "poway,": "poway",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("92101", "Downtown / Gaslamp / Embarcadero / Little Italy / Harbor Island -- the convention, cruise and "
              "airport heart, one postal code, never split."),
    ("92108", "Mission Valley / Hotel Circle -- the densest drive-in cluster."),
    ("92109", "Mission Beach / Pacific Beach / Mission Bay -- the beach-resort and vacation-rental core; the "
              "City's own register carries more short-term-rental certificates here than anywhere else."),
    ("92106", "Point Loma / Shelter Island -- the corridor that carries the airport's name."),
    ("92037", "La Jolla -- bounded by its own code; 92122 is the Golden Triangle."),
    ("92118", "Coronado -- a separate city."),
    ("92130", "Carmel Valley -- City of San Diego, marketed as 'Del Mar', placed in the Del Mar corridor by the "
              "traveller test."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder San Diego" % name),
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
            ("state_code", "CA"),
            ("geography_class", klass),
        ]))
    outside_zips = {z for _m, _s, zs, _w in OUTSIDE for z in zs}
    overlap = outside_zips & set(seen_zip)
    if overlap:
        raise SystemExit("postal codes both admitted and refused: %s" % sorted(overlap))
    prefix_overlap = [z for z in seen_zip if any(z.startswith(p) for p, _n, _f in OUTSIDE_PREFIXES)]
    if prefix_overlap:
        raise SystemExit("admitted postal codes under a refused prefix: %s" % sorted(prefix_overlap))
    stray = [z for z in seen_zip if not z.startswith(SAN_DIEGO_COUNTY_PREFIXES)]
    if stray:
        raise SystemExit("admitted postal codes outside San Diego County's prefixes: %s" % stray)

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius), ("state_code", "CA"),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "San Diego / Coastal San Diego County beach, resort, airport and business lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", "CA"),
        ("states", ["CA"]),
        ("country", "US"),
        ("market_center", {"lat": 32.72, "lng": -117.16}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches north past the Orange and Riverside County "
             "lines (San Clemente, Temecula), east over the mountains to Borrego Springs and south across the "
             "border into Tijuana, so that " + WORK_ORDER + " classifies those properties on evidence instead of "
             "being blind to them. Admission is decided by the corridor registry over the property's OWN postal "
             "code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". San Diego / Coastal San Diego County is ONE market: eleven CORE corridors over the City of "
         "San Diego's traveller districts, seven CORRIDOR tiers (Coronado, Del Mar / Solana Beach / Carmel Valley, "
         "Encinitas, Carlsbad, Oceanside, the South Bay, the I-15 corridor) and two FRINGE corridors (East County, "
         "inland North County). TEMECULA, ORANGE COUNTY and PALM SPRINGS are refused as future standalone "
         "markets; the rural inland north, the mountain and I-8 backcountry and the desert are refused by name; "
         "Tijuana is refused by country."),
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
        ("market_name", "San Diego, California"),
        ("market_slug", MARKET_ID),
        ("state_name", "California"),
        ("state_code", "CA"),
        ("primary_state_code", "CA"),
        ("states", ["CA"]),
        ("primary_city", "San Diego"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in San Diego & Coastal San Diego County | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across San Diego and the coast -- downtown and the Gaslamp, the waterfront "
         "and Little Italy, Point Loma and the airport, Old Town, Mission Valley, Ocean Beach, Mission and Pacific "
         "Beach, La Jolla, Coronado, Del Mar, Encinitas, Carlsbad and Oceanside -- with real pet fees and policies "
         "read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "San Diego"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or the City of San Diego's "
         "business-tax record of the premises states it, joined to the corridor registry. A San Diego beach, "
         "resort, airport and business travel market -- the coast from Imperial Beach to Oceanside and the metro "
         "from the border to Rancho Bernardo and El Cajon. Not 'all of San Diego County': the rural inland north, "
         "the backcountry and the desert are refused; Temecula, Orange County and Palm Springs are future "
         "standalone markets; Tijuana is Mexico. Nothing else admits a property: not a brand's 'San Diego' or "
         "'La Jolla' or 'Del Mar' marketing name, not a map pin, not a vacation-rental listing, not a competitor "
         "directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). The postal city "
         "'SAN DIEGO' spans 40-odd codes and places nothing by itself. Shared codes are covered whole: 92101 by "
         "Downtown, the Gaslamp, East Village, Little Italy, the Embarcadero and Harbor Island; 92109 by Mission "
         "Beach, Pacific Beach and Mission Bay; 92106 by Point Loma and Shelter Island; 92110 by Old Town and "
         "Midway. SAN airport, the cruise terminals, the convention center, Balboa Park, the Hotel del Coronado, "
         "the Del Mar Fairgrounds, Legoland, Imperial Beach and San Ysidro are overlays, never corridors of their "
         "own."),
        ("_census_membership_note",
         "Individual condominium units, vacation homes, beach cottages rented unit by unit, property-management "
         "portfolios, Airbnb / Vrbo inventory, short-term residential occupancy licences, ordinary apartments, "
         "individual timeshare units, owner-only vacation-ownership resorts, private resort / branded residences, "
         "member-only club lodging and government military billeting are never admitted. A mixed hotel / condo / "
         "residence property is admitted only as the exact hotel premises its public operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 -- San Diego / Coastal San Diego County travel-market geography, the coastal "
                  "structure test, the airport / cruise / military test, the county and border boundary test and "
                  "the resort / condo / timeshare / vacation-rental safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/san-diego-ca.json. "
         "This order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or the City of San Diego business-tax record "
         "of the premises states it, joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG CORRIDOR is registry class CORRIDOR; FUTURE STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes and by postal PREFIX for the "
                          "refused counties; the future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("coastal_structure_test", COASTAL_STRUCTURE),
        ("san_diego_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("dog_travel_relevance",
         "San Diego was selected as a high-value pet-travel market. That lowers NO evidence standard: no "
         "destination reputation ('dog-friendly city', Dog Beach, Fiesta Island) is ever policy evidence. It "
         "shapes only the CENSUS: every beach, bay-resort, outdoor, extended-stay and airport / drive-market "
         "cluster the traveller geography names is covered by an admitting cell and an overlay, so no lodging "
         "cluster near the dog beaches (Ocean Beach, Coronado's Dog Beach, Del Mar's North Beach) is missed."),
        ("the_san_diego_name_trap",
         "The postal city 'SAN DIEGO' covers the whole 342-square-mile City of San Diego. 'LA JOLLA' is borrowed "
         "by the Golden Triangle (92122). 'DEL MAR' is borrowed by Carmel Valley (92130). 'NORTH SAN DIEGO' is "
         "borrowed by Temecula and Escondido. A property's own postal code, street and brand property code decide "
         "what and where it is; none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("San Diego International Airport (SAN)",
             "overlay across downtown-gaslamp-waterfront (Harbor Island), point-loma-shelter-island-airport "
             "(North Harbor Drive) and old-town-midway (Pacific Highway). No corridor of its own: it owns no code."),
            ("San Diego Convention Center / Petco Park", "downtown-gaslamp-waterfront (92101) -- overlay."),
            ("Cruise terminals", "downtown-gaslamp-waterfront (92101) -- overlay."),
            ("Balboa Park / San Diego Zoo", "uptown-hillcrest-north-park and downtown -- overlay."),
            ("SeaWorld / Mission Bay", "mission-pacific-beach (92109) -- overlay."),
            ("UC San Diego / Scripps / biotech", "la-jolla and utc-golden-triangle-sorrento -- overlays."),
            ("Del Mar Fairgrounds / racetrack", "del-mar-solana-beach -- overlay."),
            ("Legoland California", "carlsbad -- overlay."),
            ("San Diego Zoo Safari Park", "escondido-san-marcos-vista -- overlay."),
            ("Naval Base San Diego / NAS North Island / Camp Pendleton",
             "military codes OUTSIDE; drivers for south-bay-chula-vista, coronado and oceanside."),
            ("San Ysidro border crossing", "south-bay-chula-vista (92173) -- overlay."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Downtown San Diego", "ADMITTED (CORE, downtown-gaslamp-waterfront, 92101). PRIMARY evaluation."),
            ("Gaslamp Quarter", "ADMITTED (CORE, downtown-gaslamp-waterfront, 92101) as an overlay. PRIMARY."),
            ("San Diego Bay / Waterfront", "ADMITTED (CORE, downtown-gaslamp-waterfront, 92101) as an overlay -- "
                                           "92101 is never split. PRIMARY."),
            ("Little Italy", "ADMITTED (CORE, downtown-gaslamp-waterfront, 92101) as an overlay. PRIMARY."),
            ("San Diego International Airport / SAN",
             "ADMITTED as an OVERLAY across 92101 / 92106 / 92110; the corridor carrying its name is "
             "point-loma-shelter-island-airport (92106). PRIMARY."),
            ("Mission Valley", "ADMITTED (CORE, mission-valley-hotel-circle, 92108). PRIMARY."),
            ("Hotel Circle", "ADMITTED (CORE, mission-valley-hotel-circle, 92108) as an overlay. PRIMARY."),
            ("Old Town", "ADMITTED (CORE, old-town-midway, 92110). PRIMARY."),
            ("Point Loma", "ADMITTED (CORE, point-loma-shelter-island-airport, 92106). PRIMARY."),
            ("Ocean Beach", "ADMITTED (CORE, ocean-beach, 92107). PRIMARY."),
            ("Mission Beach", "ADMITTED (CORE, mission-pacific-beach, 92109). PRIMARY."),
            ("Pacific Beach", "ADMITTED (CORE, mission-pacific-beach, 92109). PRIMARY."),
            ("La Jolla", "ADMITTED (CORE, la-jolla, 92037 / 92093). PRIMARY. The Golden Triangle (92122) is its own "
                         "corridor."),
            ("Coronado", "ADMITTED (STRONG CORRIDOR, coronado, 92118). STRONG."),
            ("Del Mar", "ADMITTED (STRONG CORRIDOR, del-mar-solana-beach, 92014). STRONG."),
            ("Solana Beach", "ADMITTED (STRONG CORRIDOR, del-mar-solana-beach, 92075). STRONG."),
            ("Encinitas", "ADMITTED (STRONG CORRIDOR, encinitas-cardiff, 92024 / 92007). STRONG."),
            ("Carlsbad", "ADMITTED (STRONG CORRIDOR, carlsbad, 92008-92011). STRONG; named future optionality."),
            ("Chula Vista", "ADMITTED (CORRIDOR, south-bay-chula-vista). ADDITIONAL."),
            ("National City", "ADMITTED (CORRIDOR, south-bay-chula-vista, 91950). ADDITIONAL."),
            ("Imperial Beach", "ADMITTED (CORRIDOR, south-bay-chula-vista, 91932) as an overlay -- too small for "
                               "a corridor of its own. ADDITIONAL."),
            ("La Mesa", "ADMITTED (FRINGE, east-county-i8, 91941 / 91942). ADDITIONAL."),
            ("El Cajon", "ADMITTED (FRINGE, east-county-i8, 92019-92021). ADDITIONAL."),
            ("Santee", "ADMITTED (FRINGE, east-county-i8, 92071). ADDITIONAL."),
            ("Poway", "ADMITTED (CORRIDOR, rancho-bernardo-poway-i15, 92064). ADDITIONAL."),
            ("Rancho Bernardo", "ADMITTED (CORRIDOR, rancho-bernardo-poway-i15, 92127 / 92128). ADDITIONAL."),
            ("Escondido", "ADMITTED (FRINGE, escondido-san-marcos-vista). ADDITIONAL."),
            ("San Marcos", "ADMITTED (FRINGE, escondido-san-marcos-vista, 92069 / 92078). ADDITIONAL."),
            ("Vista", "ADMITTED (FRINGE, escondido-san-marcos-vista, 92081 / 92083 / 92084). ADDITIONAL."),
            ("Oceanside", "ADMITTED (STRONG CORRIDOR, oceanside, 92054-92058). ADDITIONAL."),
            ("Temecula", "OUTSIDE -- Riverside County, FUTURE_STANDALONE temecula-valley-ca. CAREFUL."),
            ("Orange County", "OUTSIDE -- FUTURE_STANDALONE orange-county-ca. CAREFUL."),
            ("Palm Springs / Coachella Valley", "OUTSIDE -- FUTURE_STANDALONE palm-springs-ca. CAREFUL."),
            ("Tijuana / Mexico", "OUTSIDE by country."),
            ("Riverside", "OUTSIDE by county and prefix."),
            ("Los Angeles", "OUTSIDE by prefix."),
            ("Fallbrook / Valley Center / Pala / Pauma", "OUTSIDE by name (rural / destination casino)."),
            ("Ramona / Julian / Borrego Springs / Alpine", "OUTSIDE by name (backcountry and desert)."),
            ("Military installations", "OUTSIDE (military-only codes); billeting refused by name."),
        ])),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_counties", sorted(ADMITTED_COUNTIES)),
        ("observed_outside_counties", OBSERVED_COUNTIES),
        ("outside_prefixes", [OrderedDict([("prefix", p), ("area", n), ("future_market", f)])
                              for p, n, f in OUTSIDE_PREFIXES]),
        ("shared_postal_codes", SHARED_POSTAL_CODES),
        ("no_live_market_postal_code_admitted", True),
        ("first_california_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, cruise, beach, zoo or "
         "Legoland keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration "
         "order publishes it."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, public resorts, qualifying condo-hotels with a distinct public hotel "
         "operation, qualifying extended-stay hotels and other public lodging establishments: bookable nightly rooms "
         "or suites sold to the public under one establishment name, with an official property page and an on-site "
         "hotel operation. It NEVER admits: individual condominium units; vacation homes, beach cottages or villas; "
         "property-management / short-term-rental portfolios; Airbnb / Vrbo listings; City of San Diego "
         "short-term residential occupancy (STRO) licences; ordinary apartments; individual timeshare units or "
         "owner-only vacation-ownership resorts; private resort or branded residences; member-only club lodging; "
         "government military billeting; and privately managed units inside hotel-condo towers. Campgrounds, RV "
         "parks and hostels are NON_LODGING."),
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
    for slug, _name, _area, klass, _m, zips, _desc in CORRIDORS:
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
    if z.startswith(SAN_DIEGO_COUNTY_PREFIXES):
        return "OUTSIDE", None, "San Diego County postal code %r is claimed by no corridor" % z
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
