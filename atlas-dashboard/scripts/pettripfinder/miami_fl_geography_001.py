"""PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4 and 7: the Greater Miami travel market.

Built from zero on the repaired release-factory lineage (0b6ad264; current verified live = Augusta deploy
6aaeb3b7, source 96564199). No earlier Miami build exists; nothing here is read from another market.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Greater Miami / Miami Beach traveller lodging market, stated as an explicit CORE / CORRIDOR /
FRINGE / OUTSIDE rule (with FUTURE_STANDALONE markets named inside OUTSIDE) before a single hotel is admitted,
so no property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
-------------------
Membership is decided by the property's OWN postal code, as its own official page (or the Florida DBPR
public-lodging licence, the state's own record of the licensed premises) states it, joined to the corridor
registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing name ("Miami Airport",
"Miami Beach Area", "Miami North", "Miami Lakes") never admits and never places a property: a hotel whose own
address states Hollywood 33019 is a Broward County hotel, not a Miami hotel, whatever its name says.

THE SPLIT TEST (PHASE 3) IS RECORDED IN THE REPORT
--------------------------------------------------
Miami and Miami Beach are ONE market (miami-fl): one airport (MIA), one CVB (the Greater Miami Convention &
Visitors Bureau markets Miami and the Beaches together), one county (Miami-Dade), causeway-connected (MacArthur,
Venetian, Julia Tuttle, 79th Street, Broad), and the dominant traveller pattern -- fly into MIA, stay on the Beach
or Downtown/Brickell, cruise from PortMiami -- crosses Biscayne Bay constantly. Miami Beach nevertheless keeps a
DISTINCT traveller identity: it is never folded into generic Miami. It is three named CORE corridors (South Beach
33139 / Mid-Beach 33140 / North Beach 33141), exactly along its own postal seams, and every corridor carries its
own display area. Aventura, Sunny Isles Beach and Bal Harbour / Surfside are named CORRIDOR tiers, not Miami Beach.

Downtown Miami and Brickell are ONE corridor. They are distinct neighbourhoods, but ZIP 33131 straddles the Miami
River -- it holds both Brickell Avenue's towers and the north-bank downtown bayfront (Biscayne Boulevard Way,
Chopin Plaza) -- so no postal partition separates them without splitting a code both depend on. Downtown,
Brickell and PortMiami are reported as STREET-AND-PIN OVERLAYS on every census row.

THE CRUISE TEST (PHASE 4)
-------------------------
PortMiami sits on Dodge Island (ZIP 33132), which carries no hotel of its own. Cruise pre/post-stay lodging is
the Downtown / Brickell bayfront hotels already inside downtown-brickell, plus the Beach and the airport. A
"PortMiami" corridor would duplicate downtown-brickell exactly; it is NOT created. PortMiami is an overlay label
only (Biscayne Boulevard / Port Boulevard / Dodge Island street wording, or a pin within 1.6 km of the terminals).

MIA AIRPORT
-----------
The airport's own lodging splits along a real seam: the NW 36th Street / Miami Springs / Virginia Gardens strip on
the north side (33142, 33166) and the Blue Lagoon / NW 7th Street / Airport West office park on the south side
(33126, 33144). Both are CORE. Doral (33122, 33172, 33178) is its own CORE corridor even where its hotels market
themselves as "Miami Airport West": the property's own postal code governs, and Doral is a distinct business /
golf / Trump National Doral lodging cluster.

VACATION RENTALS, CONDO-HOTELS, TIMESHARES AND RESORT RESIDENCES
-----------------------------------------------------------------
Florida DBPR licenses every condominium unit (CNDO) and vacation dwelling (DWEL) as public lodging; Miami-Dade
carries ~9,500 CNDO and ~2,000 DWEL licences. None is a hotel identity and none enters the graph. A mixed hotel /
condo / branded-residence tower (Sunny Isles, Brickell, Miami Beach) is admitted ONLY as the exact hotel premises
its public hotel operator sells as a hotel, proved on the operator's own page and on the licence's exact premises
(a DBPR HOTL licence at that street, not a CNDO rental programme).

Nothing here fetches, spends or deploys. The market document goes to the PROPOSED path (shadow until registered);
the registry's markets/<id>.json is never written.

Outputs:
  scripts/pettripfinder/discovery/config/miami_fl.json
  launch_packages/pettripfinder/markets/proposed/miami-fl.json
  launch_packages/pettripfinder/markets/reports/miami_fl_geography_001.json
  launch_packages/pettripfinder/markets/reports/miami_fl_corridor_registry_001.json
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

WORK_ORDER = "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "miami-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "miami_fl.json")
#: REGISTERED by PTF-MIAMI-FL-REGISTRATION-AND-STAGING-004 against the Augusta-live parent. The source-ready
#: order wrote markets/proposed/miami-fl.json (kept as history).
SHARD_OUT = os.path.join(PKG, "markets", "miami-fl.json")
REPORT_OUT = os.path.join(REPORTS, "miami_fl_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "miami_fl_corridor_registry_001.json")
AS_OF = "2026-09-19"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown-brickell", "Downtown Miami / Brickell / PortMiami", "Downtown Miami & Brickell", "CORE", "miami",
     ["33128", "33129", "33130", "33131", "33132", "33136"],
     "Downtown Miami's Biscayne Boulevard bayfront, Bayside, the Kaseya Center and PortMiami's cruise terminals on "
     "Dodge Island, Brickell's financial district south of the Miami River, Brickell Key, and Overtown / the Health "
     "District. ZIP 33131 straddles the river, so Downtown and Brickell are one corridor; Downtown, Brickell and "
     "PortMiami are reported as overlays."),
    ("south-beach", "South Beach", "South Beach", "CORE", "miami beach",
     ["33139", "33109"],
     "Miami Beach south of roughly Dade Boulevard / 23rd Street: Ocean Drive, Collins Avenue's Art Deco District, "
     "Lincoln Road, South of Fifth and the Venetian Islands, plus Fisher Island (33109)."),
    ("mid-beach", "Mid-Beach", "Mid-Beach", "CORE", "miami beach",
     ["33140"],
     "Miami Beach's Collins Avenue resort row from the Miami Beach Convention Center edge north to about 63rd Street: "
     "the Fontainebleau, Eden Roc, Faena District and Indian Creek."),
    ("north-beach", "North Beach / North Bay Village", "North Beach", "CORE", "miami beach",
     ["33141"],
     "North Beach from 63rd Street to 87th Terrace (Normandy Isles, the North Beach Town Center) and North Bay Village "
     "on the 79th Street Causeway, which shares ZIP 33141."),
    ("mia-airport-miami-springs", "Miami International Airport (MIA) / Miami Springs / Virginia Gardens",
     "MIA Airport", "CORE", "miami",
     ["33142", "33166"],
     "The north side of Miami International Airport: the NW 36th Street / NW 42nd Avenue (Le Jeune Road) hotel strip, "
     "Miami Springs and Virginia Gardens, and the MIA terminal hotel itself."),
    ("airport-west-blue-lagoon", "Airport West / Blue Lagoon / Flagami", "Airport West & Blue Lagoon", "CORE", "miami",
     ["33126", "33144"],
     "The south side of MIA: the Blue Lagoon Drive office lake, NW 7th Street and the Dolphin Expressway / NW 57th "
     "Avenue airport-west hotel park, and West Flagler Street's Flagami motels."),
    ("doral", "Doral", "Doral", "CORE", "doral",
     ["33122", "33172", "33178"],
     "The City of Doral west of MIA -- NW 25th / NW 36th / NW 41st Street business parks, Trump National Doral and "
     "CityPlace Doral -- plus neighbouring Sweetwater and Medley, which share its postal codes."),
    ("coral-gables", "Coral Gables / South Miami", "Coral Gables", "CORE", "coral gables",
     ["33134", "33146", "33143"],
     "The City of Coral Gables (Miracle Mile, Ponce de Leon Boulevard, the Biltmore, the University of Miami) and "
     "adjoining South Miami (33143)."),
    ("coconut-grove", "Coconut Grove", "Coconut Grove", "CORE", "miami",
     ["33133"],
     "Coconut Grove's bayfront village, CocoWalk and South Bayshore Drive."),
    ("midtown-wynwood-edgewater", "Edgewater / Wynwood / Midtown / Design District / MiMo", "Wynwood & Edgewater",
     "CORRIDOR", "miami",
     ["33127", "33137", "33138", "33150"],
     "The neighbourhoods directly north of downtown: Edgewater's Biscayne Boulevard towers, Wynwood, Midtown, the "
     "Design District, the MiMo Biscayne Boulevard historic motels, Little Haiti and Miami Shores / El Portal."),
    ("little-havana", "Little Havana / Coral Way", "Little Havana", "CORRIDOR", "miami",
     ["33125", "33135", "33145"],
     "Calle Ocho / SW 8th Street, the Marlins' loanDepot park and the Coral Way / Shenandoah district west of Brickell."),
    ("key-biscayne", "Key Biscayne", "Key Biscayne", "CORRIDOR", "key biscayne",
     ["33149"],
     "The island village of Key Biscayne across the Rickenbacker Causeway."),
    ("bal-harbour-surfside", "Bal Harbour / Surfside / Bay Harbor Islands", "Bal Harbour & Surfside", "CORRIDOR",
     "bal harbour",
     ["33154"],
     "Surfside, Bal Harbour and Bay Harbor Islands north of Miami Beach's 87th Terrace line; one shared ZIP (33154)."),
    ("sunny-isles-beach", "Sunny Isles Beach", "Sunny Isles Beach", "CORRIDOR", "sunny isles beach",
     ["33160"],
     "Sunny Isles Beach's Collins Avenue oceanfront hotel and condo-hotel towers, plus the Eastern Shores sliver of "
     "North Miami Beach that shares ZIP 33160."),
    ("aventura", "Aventura", "Aventura", "CORRIDOR", "aventura",
     ["33180"],
     "Aventura Mall, Biscayne Boulevard's Aventura hotels and the Turnberry resort district, on the Broward line."),
    ("north-miami", "North Miami / North Miami Beach", "North Miami", "CORRIDOR", "north miami",
     ["33161", "33162", "33167", "33168", "33179", "33181"],
     "North Miami, North Miami Beach and the Biscayne Boulevard / NE 163rd Street motel corridor between Miami "
     "Shores and Aventura, including Keystone Point and FIU's Biscayne Bay campus."),
    ("hialeah-miami-lakes", "Hialeah / Hialeah Gardens / Miami Lakes", "Hialeah", "FRINGE", "hialeah",
     ["33010", "33012", "33013", "33014", "33015", "33016", "33018"],
     "Hialeah's Okeechobee Road and Le Jeune Road lodging immediately north of MIA, Hialeah Gardens, and Miami Lakes "
     "on the Palmetto Expressway; careful evaluation, admitted at FRINGE density."),
    ("miami-gardens-opa-locka", "Miami Gardens / Opa-locka / Liberty City", "Miami Gardens", "FRINGE",
     "miami gardens",
     ["33054", "33055", "33056", "33169", "33147"],
     "Miami Gardens (Hard Rock Stadium), Opa-locka and the NW 27th Avenue / Liberty City blocks; careful evaluation, "
     "admitted at FRINGE density."),
    ("kendall-south-dade", "Kendall / Westchester / Tamiami / Cutler Bay", "Kendall", "FRINGE", "kendall",
     ["33155", "33156", "33157", "33158", "33165", "33170", "33173", "33174", "33175", "33176", "33177", "33182",
      "33183", "33184", "33185", "33186", "33187", "33189", "33190", "33193", "33194", "33196"],
     "Suburban south and west Miami-Dade: Westchester, FIU's Modesto Maidique campus, Tamiami, Kendall, Dadeland, "
     "Pinecrest, Palmetto Bay and Cutler Bay; careful evaluation, admitted at FRINGE density."),
    ("homestead-florida-city", "Homestead / Florida City", "Homestead", "FRINGE", "homestead",
     ["33030", "33031", "33032", "33033", "33034", "33035", "33039"],
     "Homestead and Florida City at the south end of the Turnpike -- the Homestead-Miami Speedway and the Everglades "
     "and Biscayne National Park gateway -- still Miami-Dade County; careful evaluation, admitted at FRINGE density. "
     "Its 'gateway to the Keys' marketing does not make it a Keys property, and it does not pull the Keys in."),
]

MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "miami bch": "miami beach", "mia beach": "miami beach", "miami spgs": "miami springs",
    "sunny isles": "sunny isles beach", "bay harbour island": "bay harbor islands",
    "bay harbour islands": "bay harbor islands", "hilaeah": "hialeah", "n miami": "north miami",
    "n miami beach": "north miami beach", "miami,": "miami",
}

#: FUTURE standalone markets this order preserves by name.
FUTURE_MARKETS = OrderedDict([
    ("fort-lauderdale-fl", "Fort Lauderdale / Hollywood / Hallandale Beach / Dania Beach / Pompano Beach / "
                           "Deerfield Beach -- Broward County, with its own airport (FLL), its own cruise port "
                           "(Port Everglades) and its own CVB (Visit Lauderdale)"),
    ("west-palm-beach-fl", "West Palm Beach / Palm Beach / Boca Raton -- Palm Beach County, with its own airport "
                           "(PBI) and CVB (Discover The Palm Beaches)"),
    ("florida-keys-fl", "The Florida Keys (Key Largo / Islamorada / Marathon / Key West) -- Monroe County, its own "
                        "island resort market (possibly split Upper Keys / Key West when built)"),
])

#: Municipalities OUTSIDE the admitted market, each with the reason. A FUTURE_STANDALONE row names its market.
OUTSIDE = [
    ("Fort Lauderdale", "FL", ["33301", "33304", "33305", "33306", "33308", "33309", "33311", "33312", "33315",
                               "33316", "33317", "33334"],
     "Broward County; FUTURE_STANDALONE fort-lauderdale-fl; refused by name (order)."),
    ("Hollywood", "FL", ["33019", "33020", "33021", "33023", "33024"],
     "Broward County; FUTURE_STANDALONE fort-lauderdale-fl; refused by name (order)."),
    ("Hallandale Beach", "FL", ["33009"],
     "Broward County, immediately north of Aventura / Sunny Isles; FUTURE_STANDALONE fort-lauderdale-fl; refused -- "
     "the county line, not proximity to Aventura, decides."),
    ("Dania Beach", "FL", ["33004"],
     "Broward County (FLL airport south side); FUTURE_STANDALONE fort-lauderdale-fl; refused by name (order)."),
    ("Pompano Beach / Deerfield Beach", "FL", ["33060", "33062", "33064", "33069", "33441", "33442"],
     "Broward County; FUTURE_STANDALONE fort-lauderdale-fl; refused by name (order)."),
    ("Miramar / Pembroke Pines / Davie / Plantation / Sunrise", "FL",
     ["33025", "33027", "33028", "33029", "33314", "33324", "33325", "33326", "33327", "33328", "33330", "33331",
      "33313", "33319", "33321", "33322", "33323", "33351"],
     "Broward County suburbs west of Hollywood / Fort Lauderdale; FUTURE_STANDALONE fort-lauderdale-fl; refused."),
    ("Boca Raton", "FL", ["33431", "33432", "33433", "33434", "33486", "33487", "33496", "33498"],
     "Palm Beach County; FUTURE_STANDALONE west-palm-beach-fl; refused by name (order)."),
    ("West Palm Beach / Palm Beach", "FL", ["33401", "33405", "33406", "33407", "33409", "33411", "33480"],
     "Palm Beach County; FUTURE_STANDALONE west-palm-beach-fl; refused by name (order)."),
    ("Florida Keys (Key Largo / Islamorada / Marathon / Key West)", "FL",
     ["33037", "33036", "33070", "33050", "33042", "33043", "33040", "33041", "33045"],
     "Monroe County; FUTURE_STANDALONE florida-keys-fl; refused by name (order) -- Key Largo and Islamorada are "
     "never absorbed as 'south Miami'."),
]

#: County-level boundary for the registry lane (DBPR states each licence's county). Miami-Dade is the only
#: county the admitted corridors touch; every other county row is OUTSIDE by county before any ZIP lookup.
ADMITTED_COUNTIES = {"dade", "miami-dade"}
OBSERVED_COUNTIES = OrderedDict([
    ("broward", "fort-lauderdale-fl"), ("palm beach", "west-palm-beach-fl"), ("monroe", "florida-keys-fl"),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government).
NONPUBLIC_NAMES = {}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-brickell", "Miami", "Downtown Miami / Brickell / PortMiami", 25.7690, -80.1920, 2600, True),
    ("south-beach", "Miami Beach", "South Beach", 25.7800, -80.1330, 2600, True),
    ("mid-beach", "Miami Beach", "Mid-Beach", 25.8200, -80.1250, 2400, True),
    ("north-beach", "Miami Beach", "North Beach / North Bay Village", 25.8560, -80.1350, 2400, True),
    ("mia-airport-miami-springs", "Miami", "MIA Airport / Miami Springs", 25.8110, -80.2820, 3200, True),
    ("airport-west-blue-lagoon", "Miami", "Airport West / Blue Lagoon", 25.7760, -80.3000, 3000, True),
    ("doral", "Doral", "Doral", 25.8200, -80.3500, 4500, True),
    ("coral-gables", "Coral Gables", "Coral Gables / South Miami", 25.7300, -80.2650, 3500, True),
    ("coconut-grove", "Miami", "Coconut Grove", 25.7280, -80.2400, 1800, True),
    ("midtown-wynwood-edgewater", "Miami", "Edgewater / Wynwood / Design District / MiMo", 25.8150, -80.1930, 3200, True),
    ("little-havana", "Miami", "Little Havana / Coral Way", 25.7650, -80.2250, 2600, True),
    ("key-biscayne", "Key Biscayne", "Key Biscayne", 25.6930, -80.1630, 2500, True),
    ("bal-harbour-surfside", "Bal Harbour", "Bal Harbour / Surfside", 25.8850, -80.1260, 1800, True),
    ("sunny-isles-beach", "Sunny Isles Beach", "Sunny Isles Beach", 25.9430, -80.1230, 2000, True),
    ("aventura", "Aventura", "Aventura", 25.9560, -80.1420, 2000, True),
    ("north-miami", "North Miami", "North Miami / North Miami Beach", 25.9100, -80.1800, 3500, True),
    ("hialeah-miami-lakes", "Hialeah", "Hialeah / Miami Lakes", 25.8700, -80.3000, 5000, True),
    ("miami-gardens-opa-locka", "Miami Gardens", "Miami Gardens / Opa-locka", 25.9300, -80.2500, 4500, True),
    ("kendall-south-dade", "Kendall", "Kendall / Westchester / Cutler Bay", 25.6800, -80.3400, 9000, True),
    ("homestead-florida-city", "Homestead", "Homestead / Florida City", 25.4600, -80.4600, 5000, True),
    ("obs-hallandale-hollywood-dania", "Hollywood", "Hallandale / Hollywood / Dania Beach -- OBSERVATION ONLY",
     26.0200, -80.1400, 6000, False),
    ("obs-fort-lauderdale", "Fort Lauderdale", "Fort Lauderdale -- OBSERVATION ONLY", 26.1200, -80.1400, 6000, False),
    ("obs-upper-keys", "Key Largo", "Key Largo / Upper Keys -- OBSERVATION ONLY", 25.1000, -80.4300, 6000, False),
]

BOUNDS = {"min_lat": 25.05, "max_lat": 26.20, "min_lng": -80.56, "max_lng": -80.05}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Downtown Miami", 25.7760, -80.1900, 1.3),
    ("Brickell", 25.7610, -80.1930, 1.3),
    ("PortMiami", 25.7780, -80.1700, 1.6),
    ("South Beach", 25.7800, -80.1320, 2.0),
    ("Mid-Beach", 25.8200, -80.1230, 2.0),
    ("North Beach", 25.8570, -80.1210, 1.8),
    ("North Bay Village", 25.8470, -80.1520, 1.0),
    ("Miami International Airport (MIA)", 25.7959, -80.2870, 2.2),
    ("Miami Springs", 25.8220, -80.2895, 1.8),
    ("Blue Lagoon", 25.7800, -80.3000, 1.8),
    ("Doral", 25.8195, -80.3553, 4.0),
    ("Coral Gables", 25.7215, -80.2684, 2.5),
    ("Coconut Grove", 25.7280, -80.2430, 1.5),
    ("Wynwood", 25.8010, -80.1990, 1.2),
    ("Edgewater", 25.7960, -80.1880, 1.0),
    ("Design District", 25.8130, -80.1930, 1.0),
    ("Little Havana", 25.7650, -80.2190, 1.5),
    ("Key Biscayne", 25.6930, -80.1628, 2.5),
    ("Bal Harbour", 25.8918, -80.1267, 1.0),
    ("Surfside", 25.8784, -80.1256, 1.0),
    ("Sunny Isles Beach", 25.9429, -80.1234, 1.8),
    ("Aventura", 25.9565, -80.1392, 1.8),
    ("North Miami", 25.8901, -80.1867, 2.5),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("PortMiami", re.compile(r"\bport b(lv)?d\b|\bdodge island\b|\bcruise terminal\b", re.I)),
    ("Brickell", re.compile(r"\bbrickell\b|\bs\.? ?miami ave\b|\bsw \d+(st|nd|rd|th) (st|street|rd|road)\b", re.I)),
    ("Downtown Miami", re.compile(r"\bbiscayne b(lv)?d w(a)?y\b|\bchopin plaza\b|\bbayside\b|\bflagler st\b", re.I)),
    ("Miami International Airport (MIA)", re.compile(r"\bnw 36(th)? st\b|\ble ?jeune\b|\bnw 42(nd)? ave\b|\bairport\b", re.I)),
    ("Blue Lagoon", re.compile(r"\bblue lagoon\b|\bnw 7(th)? st\b", re.I)),
    ("Wynwood", re.compile(r"\bwynwood\b|\bnw 2(nd)? ave\b", re.I)),
    ("Design District", re.compile(r"\bdesign district\b|\bne 39(th)? st\b|\bne 40(th)? st\b", re.I)),
    ("South Beach", re.compile(r"\bocean dr(ive)?\b|\blincoln r(oa)?d\b|\bwashington ave\b|\bcollins ave\b.*\b(1|2)?\d{3}\b.*33139", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-brickell": "Downtown Miami", "south-beach": "South Beach", "mid-beach": "Mid-Beach",
    "north-beach": "North Beach", "mia-airport-miami-springs": "Miami International Airport (MIA)",
    "airport-west-blue-lagoon": "Blue Lagoon", "doral": "Doral", "coral-gables": "Coral Gables",
    "coconut-grove": "Coconut Grove", "midtown-wynwood-edgewater": "Wynwood", "little-havana": "Little Havana",
    "key-biscayne": "Key Biscayne", "bal-harbour-surfside": "Bal Harbour", "sunny-isles-beach": "Sunny Isles Beach",
    "aventura": "Aventura", "north-miami": "North Miami", "hialeah-miami-lakes": "Hialeah",
    "miami-gardens-opa-locka": "Miami Gardens", "kendall-south-dade": "Kendall",
    "homestead-florida-city": "Homestead",
}

SPLIT_TEST = OrderedDict([
    ("A. Downtown Miami / Brickell",
     "CORE, one corridor downtown-brickell (33128, 33129, 33130, 33131, 33132, 33136). Downtown and Brickell are "
     "distinct neighbourhoods but ZIP 33131 straddles the Miami River (Brickell Avenue south, the Biscayne "
     "Boulevard Way / Chopin Plaza bayfront north), so a postal partition cannot separate them; both are overlays."),
    ("B. Miami Beach",
     "Inside miami-fl, NOT folded into generic Miami: three CORE corridors along Miami Beach's own postal seams "
     "(South Beach 33139+33109, Mid-Beach 33140, North Beach 33141). One airport, one CVB, one county and "
     "causeway connectivity make Miami + Miami Beach one travel system; the Beach's distinct identity is carried "
     "at corridor level, never flattened."),
    ("C. South Beach", "CORE corridor south-beach (33139, and Fisher Island 33109). The single densest hotel ZIP "
                       "in the market (213 DBPR hotel/motel/B&B leads)."),
    ("D. Mid-Beach / North Beach",
     "CORE corridors mid-beach (33140) and north-beach (33141, shared with North Bay Village). Separate pages "
     "only where each meets the threshold on its own."),
    ("E. MIA Airport",
     "CORE, two corridors along the airport's real seam: mia-airport-miami-springs (north side, 33142/33166) and "
     "airport-west-blue-lagoon (south side, 33126/33144). 'Miami Airport' marketing names never place a hotel."),
    ("F. Doral", "CORE corridor doral (33122, 33172, 33178), its own business / golf cluster -- not 'MIA' even when a "
                 "Doral hotel's name says 'Miami Airport West'."),
    ("G. Coral Gables / Coconut Grove",
     "CORE corridors coral-gables (33134, 33146, 33143) and coconut-grove (33133): two distinct neighbourhood "
     "hotel clusters with separate ZIPs."),
    ("H. Aventura / Sunny Isles",
     "STRONG CORRIDOR, two corridors: aventura (33180) and sunny-isles-beach (33160). Both are Miami-Dade and "
     "GMCVB 'Beaches' territory; Hallandale Beach (33009) immediately north is Broward and OUTSIDE."),
    ("I. Bal Harbour / Surfside",
     "STRONG CORRIDOR bal-harbour-surfside (33154, with Bay Harbor Islands): one shared ZIP, one corridor."),
])

CRUISE_TEST = OrderedDict([
    ("portmiami_lodging_on_dodge_island", "NONE -- the port island carries terminals, not hotels."),
    ("where_cruise_demand_sleeps",
     "Downtown / Brickell bayfront (inside downtown-brickell), Miami Beach (south-beach / mid-beach) and MIA."),
    ("portmiami_corridor_created", False),
    ("why",
     "A PortMiami corridor would claim exactly the ZIPs downtown-brickell already claims (33132 / 33131) -- a "
     "duplicate page, not a distinct lodging cluster. Cruise intent is an overlay label (PortMiami) on rows whose "
     "own street or pin is at the port, and may inform corridor copy; it never changes premises identity or "
     "membership."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Miami" % name),
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
        ("market_name", "Miami – Miami Beach / Greater Miami, Florida tourism, cruise, convention, airport and beach "
                        "lodging market (PetTripFinder discovery scope)"),
        ("state", "FL"),
        ("states", ["FL"]),
        ("country", "US"),
        ("market_center", {"lat": 25.79, "lng": -80.20}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches north into Broward County (Hallandale, "
             "Hollywood, Dania Beach, Fort Lauderdale) and south to Key Largo so that " + WORK_ORDER + " classifies "
             "those properties on evidence instead of being blind to them. Admission is decided by the corridor "
             "registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Miami and Miami Beach are ONE Greater Miami market inside Miami-Dade County: nine CORE "
         "corridors (Downtown/Brickell, South Beach, Mid-Beach, North Beach, MIA, Airport West, Doral, Coral Gables, "
         "Coconut Grove), seven CORRIDOR tiers and four FRINGE corridors. Broward (Fort Lauderdale, Hollywood, "
         "Hallandale, Dania Beach), Palm Beach County and the Florida Keys are OUTSIDE and preserved as future "
         "standalone markets."),
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
        ("market_name", "Miami, Florida"),
        ("market_slug", MARKET_ID),
        ("state_name", "Florida"),
        ("state_code", "FL"),
        ("primary_state_code", "FL"),
        ("states", ["FL"]),
        ("primary_city", "Miami"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Miami & Miami Beach, Florida | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater Miami -- Downtown & Brickell, South Beach, Mid-Beach, MIA "
         "Airport, Doral, Coral Gables, Coconut Grove, Aventura and Sunny Isles -- with real pet fees and policies "
         "read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Miami"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its Florida DBPR public-lodging "
         "licence states it, joined to the corridor registry. A Miami-Dade tourism, cruise, convention, airport and "
         "beach travel market -- not the City of Miami's limits and not all of South Florida. Nothing else admits a "
         "property: not a brand's 'Miami' marketing name, not a map pin, not a vacation-rental listing, not a "
         "competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Downtown and Brickell "
         "share 33131; PortMiami (33132) has no hotels of its own; North Bay Village shares 33141 with North Beach; "
         "Surfside, Bal Harbour and Bay Harbor Islands share 33154; Sweetwater and Medley share Doral's codes. Each "
         "shared code is one corridor and its named places are reported as overlays."),
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
        ("phase", "2 + 3 + 4 + 7 -- Greater Miami travel-market geography, Miami / Miami Beach split test, "
                  "PortMiami cruise test and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "REGISTERED: the market document is written to the registry's markets/miami-fl.json by "
         "PTF-MIAMI-FL-REGISTRATION-AND-STAGING-004 against the Augusta-live parent. The source-ready order's "
         "markets/proposed/ copy is history."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its Florida DBPR public-lodging licence states "
         "it, joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes (and, for the registry lane, by "
                          "county); future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("miami_miami_beach_split_test", SPLIT_TEST),
        ("portmiami_cruise_test", CRUISE_TEST),
        ("evaluated_inclusions", OrderedDict([
            ("Downtown Miami", "ADMITTED (CORE, downtown-brickell)."),
            ("Brickell", "ADMITTED (CORE, downtown-brickell; shares 33131 with downtown)."),
            ("Miami Beach / South Beach", "ADMITTED (CORE, south-beach)."),
            ("Mid-Beach", "ADMITTED (CORE, mid-beach)."),
            ("North Beach", "ADMITTED (CORE, north-beach)."),
            ("Miami International Airport", "ADMITTED (CORE, mia-airport-miami-springs + airport-west-blue-lagoon)."),
            ("Airport West / Blue Lagoon", "ADMITTED (CORE, airport-west-blue-lagoon)."),
            ("Coral Gables", "ADMITTED (CORE, coral-gables)."),
            ("Coconut Grove", "ADMITTED (CORE, coconut-grove)."),
            ("Doral", "ADMITTED (CORE, doral)."),
            ("Miami Springs", "ADMITTED (CORE, mia-airport-miami-springs, 33166) -- strong evaluation."),
            ("Key Biscayne", "ADMITTED (CORRIDOR, key-biscayne) -- strong evaluation."),
            ("Aventura", "ADMITTED (CORRIDOR, aventura) -- strong evaluation."),
            ("Sunny Isles Beach", "ADMITTED (CORRIDOR, sunny-isles-beach) -- strong evaluation."),
            ("Bal Harbour", "ADMITTED (CORRIDOR, bal-harbour-surfside) -- strong evaluation."),
            ("Surfside", "ADMITTED (CORRIDOR, bal-harbour-surfside) -- strong evaluation."),
            ("North Miami", "ADMITTED (CORRIDOR, north-miami) -- strong evaluation."),
            ("North Miami Beach", "ADMITTED (CORRIDOR, north-miami, 33162/33179) -- strong evaluation."),
            ("Wynwood / Edgewater / Design District / MiMo", "ADMITTED (CORRIDOR, midtown-wynwood-edgewater)."),
            ("Little Havana", "ADMITTED (CORRIDOR, little-havana)."),
            ("Hialeah", "ADMITTED (FRINGE, hialeah-miami-lakes) -- strong evaluation; its lodging on Okeechobee Road "
                        "and Le Jeune Road sits immediately north of MIA."),
            ("Miami Lakes", "ADMITTED (FRINGE, hialeah-miami-lakes) -- careful evaluation."),
            ("Opa-locka", "ADMITTED (FRINGE, miami-gardens-opa-locka) -- careful evaluation."),
            ("Kendall", "ADMITTED (FRINGE, kendall-south-dade) -- careful evaluation."),
            ("South Miami", "ADMITTED (CORE, coral-gables, 33143) -- adjoins Coral Gables; careful evaluation."),
            ("Cutler Bay", "ADMITTED (FRINGE, kendall-south-dade, 33189) -- careful evaluation."),
            ("Homestead", "ADMITTED (FRINGE, homestead-florida-city) -- careful evaluation."),
            ("Florida City", "ADMITTED (FRINGE, homestead-florida-city, 33034) -- careful evaluation."),
            ("Properties using 'Miami' mainly as marketing",
             "Never admitted by name: a 'Miami' / 'Miami North' / 'Miami Airport' name whose own address is in "
             "Broward, Palm Beach or Monroe County is OUTSIDE by its postal code."),
            ("Fort Lauderdale", "OUTSIDE by name (order) -- future fort-lauderdale-fl."),
            ("Hollywood", "OUTSIDE by name (order) -- future fort-lauderdale-fl."),
            ("Hallandale Beach", "OUTSIDE (Broward) -- future fort-lauderdale-fl."),
            ("Dania Beach", "OUTSIDE by name (order) -- future fort-lauderdale-fl."),
            ("Pompano Beach / Deerfield Beach", "OUTSIDE by name (order) -- future fort-lauderdale-fl."),
            ("Boca Raton", "OUTSIDE by name (order) -- future west-palm-beach-fl."),
            ("West Palm Beach / Palm Beach", "OUTSIDE by name (order) -- future west-palm-beach-fl."),
            ("Florida Keys / Key Largo / Islamorada", "OUTSIDE by name (order) -- future florida-keys-fl."),
        ])),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_counties", sorted(ADMITTED_COUNTIES)),
        ("observed_outside_counties", OBSERVED_COUNTIES),
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
         "is show_in_navigation / show_in_sitemap false until a registration order publishes it. Downtown, Brickell, "
         "PortMiami, Miami Springs, North Bay Village, Surfside and Bay Harbor Islands are overlays."),
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
         "a census row."),
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
