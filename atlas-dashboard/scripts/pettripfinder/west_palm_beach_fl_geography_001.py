"""PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 -- Phases 3, 4 and 5: The Palm Beaches market.

Built from zero on the CURRENT repaired lineage (participation-guard repair, supersessions-lineage repair and
deployment work_order semantics, on top of the live Fort Lauderdale release). Current verified live at authoring
time = fort-lauderdale-fl deploy 6ab1a035c7ef3b14a23a4ec6, source e82120cc, 32 markets / 2,375 profiles /
2,646 release-index routes / 2,711 served routes. No earlier West Palm Beach build exists. Miami's and Fort
Lauderdale's builds are read for DISCOVERY INTELLIGENCE only (Phase 2); no census row, policy fact or evidence
row is imported from either as authority.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical West Palm Beach / Palm Beach County ("The Palm Beaches") traveller lodging market, stated as an
explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE and EXISTING_LIVE markets named inside
OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact to make a
number.

THE GOVERNING RULE
-------------------
Membership is decided by the property's OWN postal code, as its own official page (or the Florida DBPR
public-lodging licence, the state's own record of the licensed premises) states it, joined to the corridor
registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing name never admits and
never places a property: a hotel whose own address states Riviera Beach 33404 is a Riviera Beach hotel however
loudly it calls itself "Palm Beach", and a hotel whose own address states Deerfield Beach 33441 is a Broward
property belonging to the LIVE fort-lauderdale-fl market, not to this one.

WHY "WEST PALM BEACH" AND "PALM BEACH" ARE TWO DIFFERENT PLACES
---------------------------------------------------------------
This market's single most dangerous identity trap. The Town of Palm Beach (33480 -- Worth Avenue, The Breakers,
the Four Seasons, the Colony) is an island municipality across the Intracoastal from the City of West Palm Beach
(33401 -- Clematis Street, Rosemary Square, the Convention Center). They are separate municipalities, separate
postal codes and separate travel products, and the state's own registry keeps them apart: 33480 carries 12
hotel-rank licences against 33401's 18. A great many properties in both places carry "Palm Beach" in their names.
The postal code decides; the name never does. The same trap runs the length of the county -- Palm Beach Gardens
(33410/33418), North Palm Beach (33408), Royal Palm Beach (33411), Palm Beach Shores (33404) and Palm Springs
(33406/33461) are five further municipalities whose names all contain "Palm".

WHERE PALM BEACH COUNTY'S POSTAL CODES STRADDLE MUNICIPALITIES
---------------------------------------------------------------
As in Broward, the county's postal codes cross municipal lines, and the state's own registry shows the seams:
33404 carries Riviera Beach AND Palm Beach Shores AND Singer Island AND West Palm Beach; 33408 carries North
Palm Beach AND Juno Beach AND Palm Beach Gardens; 33403 carries Lake Park AND West Palm Beach AND Palm Beach
Gardens; 33406 carries West Palm Beach AND Lake Clarke Shores AND Palm Springs; 33460/33461/33463/33467 carry
Lake Worth Beach AND Palm Springs AND Greenacres; 33462 carries Lantana AND Manalapan AND Hypoluxo; 33487
carries Boca Raton AND Highland Beach; 33435 carries Boynton Beach AND Ocean Ridge; 33469 carries Tequesta AND
Jupiter. A corridor therefore covers a shared postal code AS A WHOLE and reports its named places as
street-and-pin overlays. It never splits a ZIP, because a split ZIP is a judgement applied per property --
exactly what this registry exists to forbid.

THE COUNTY-LINE TEST (PHASE 22), IN BOTH DIRECTIONS
-----------------------------------------------------
SOUTH: Deerfield Beach 33441 / 33442 is Broward County and is ALREADY OWNED by the LIVE fort-lauderdale-fl
market (its 'deerfield-beach' corridor). Boca Raton adjoins it across the line. The line decides, not the
distance, and no Broward postal code is admitted here -- a double admission would publish one hotel in two
markets.

NORTH: postal code 33469 is a Palm Beach County code (Tequesta, 45 lodging licences) that SPILLS ACROSS THE
MARTIN COUNTY LINE (6 lodging licences, 2 of them hotel-rank, on the SE Federal Highway / US-1 approach that
is addressed Tequesta FL 33469). This is the "exact border evidence" case the order names. The registry covers
33469 WHOLE, because the governing rule is the property's own postal code and a split ZIP is exactly the
per-property judgement this market forbids; those rows are admitted by the same rule that admits everything
else, and are reported explicitly in the county boundary audit. Every other Martin County postal code (Hobe
Sound 33455 and the 349xx Stuart / Jensen Beach / Palm City codes) is refused by name.

THE STRUCTURE TEST (PHASE 4) IS RECORDED IN THE REPORT
-------------------------------------------------------
The Palm Beaches are ONE market (west-palm-beach-fl): one county (Palm Beach), one commercial airport (PBI),
one CVB (Discover The Palm Beaches, which markets all 39 Palm Beach County municipalities together under that
name). Boca Raton, Delray Beach and the Town of Palm Beach are INSIDE it -- they are Palm Beach County, they are
Discover The Palm Beaches territory, and their traveller flow is the PBI / I-95 / Brightline flow -- but each
keeps a DISTINCT traveller identity and is never folded into generic West Palm Beach. The order's instruction is
explicit: do not force Boca, Delray or Palm Beach into separate markets merely because they are large; first
determine whether the county-wide travel market remains coherent. It does, and they are corridors.

NO AIRPORT CORRIDOR, FOR THE SAME REASON AS FLL
------------------------------------------------
Palm Beach International (PBI) sits at Belvedere Road and Australian Avenue. Its hotel district is not one
postal code -- it spreads over 33406 (Belvedere Road), 33409 (Palm Beach Lakes Boulevard / Village Boulevard)
and 33415. Those three, with 33405 and 33417, form one contiguous inland corridor around the airport and the
Southern Boulevard / Okeechobee Boulevard approaches; "PBI Airport" itself is a street-and-pin overlay inside
it, never a corridor, because it owns no postal code of its own. This is the same finding FLL produced in
PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001.

NO CRUISE CORRIDOR: THE PORT OF PALM BEACH FAILS THE PORT EVERGLADES TEST
--------------------------------------------------------------------------
The Port of Palm Beach sits in Riviera Beach 33404. Unlike Port Everglades -- which sits inside 33316, a postal
code full of hotels, and therefore earned its own corridor -- and like PortMiami, the Port of Palm Beach carries
no hotel inventory that the Riviera Beach / Singer Island corridor does not already claim. Creating a cruise
corridor here would duplicate riviera-beach-singer-island's own postal code. The port is therefore an OVERLAY
inside that corridor, never a corridor. See the memory rule the two prior markets settled: a port corridor is
decided by the POSTAL CODE.

LUXURY RESORTS, CONDO-HOTELS, TIMESHARES AND RESORT RESIDENCES
---------------------------------------------------------------
Florida DBPR licenses every condominium unit (CNDO) and vacation dwelling (DWEL) as public lodging; Palm Beach
County carries 856 CNDO and 1,843 DWEL licences, plus 1,110 non-transient apartments, against just 194 hotel /
motel / B&B licences. None is a hotel identity and none enters the graph. Palm Beach County's particular risk is
the country-club and oceanfront-residence stock -- The Breakers' and Eau Palm Beach's residence inventory, the
Boca Raton Resort & Club's towers, Wellington's equestrian-season rentals, the Singer Island and Highland Beach
condo-hotel towers, and PGA National's villa programme. A mixed property is admitted ONLY as the exact hotel
premises its public hotel operator sells as a hotel, proved on the operator's own page and on the licence's exact
premises (a DBPR HOTL licence at that street, not a CNDO rental programme).

Nothing here fetches, spends or deploys. The market document goes to the registry's markets/<id>.json, as
every REGISTERED market's does.

Outputs:
  scripts/pettripfinder/discovery/config/west_palm_beach_fl.json
  launch_packages/pettripfinder/markets/west-palm-beach-fl.json
  launch_packages/pettripfinder/markets/reports/west_palm_beach_fl_geography_001.json
  launch_packages/pettripfinder/markets/reports/west_palm_beach_fl_corridor_registry_001.json
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

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "west-palm-beach-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "west_palm_beach_fl.json")
#: REGISTERED by PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002: the market document is written to the
#: registry's markets/<id>.json. The source-ready order's markets/proposed/ copy is history.
SHARD_OUT = os.path.join(PKG, "markets", "west-palm-beach-fl.json")
REPORT_OUT = os.path.join(REPORTS, "west_palm_beach_fl_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "west_palm_beach_fl_corridor_registry_001.json")
AS_OF = "2026-09-22"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown-west-palm-beach", "Downtown West Palm Beach", "Downtown West Palm Beach", "CORE", "west palm beach",
     ["33401", "33402"],
     "Downtown West Palm Beach: Clematis Street and the waterfront, Rosemary Square (formerly CityPlace), the "
     "Palm Beach County Convention Center, the Kravis Center, the Norton Museum of Art, the Brightline West Palm "
     "Beach station, Flagler Drive along the Intracoastal and the Okeechobee Boulevard hotel blocks. The Town of "
     "Palm Beach is across the Royal Park and Flagler Memorial bridges and is its own corridor."),
    ("palm-beach-worth-avenue", "Palm Beach / Worth Avenue", "Palm Beach & Worth Avenue", "CORE", "palm beach",
     ["33480"],
     "The Town of Palm Beach: Worth Avenue, South and North County Road, South Ocean Boulevard (A1A), The "
     "Breakers, the Four Seasons, the Colony and the Royal Poinciana Way blocks -- the island municipality "
     "between the Intracoastal and the Atlantic, entirely separate from the City of West Palm Beach."),
    ("northwood-metrocentre", "Northwood / Metrocentre / 45th Street", "Northwood & Metrocentre", "CORE",
     "west palm beach",
     ["33407"],
     "North West Palm Beach: the Metrocentre Boulevard and Northpoint Parkway hotel cluster at Interstate 95 and "
     "45th Street, the Northwood Village arts district, the Broadway / US-1 motor-court row, Currie Park and the "
     "Mangonia Park and southern Riviera Beach edges that share this postal code."),
    ("riviera-beach-singer-island", "Riviera Beach / Singer Island / Lake Park",
     "Riviera Beach & Singer Island", "CORE", "riviera beach",
     ["33403", "33404"],
     "The northern barrier island and its mainland: Singer Island's Ocean Drive and Blue Heron Boulevard "
     "oceanfront, Palm Beach Shores at the Palm Beach Inlet, Peanut Island, the Port of Palm Beach, Riviera "
     "Beach's Broadway corridor, and Lake Park's Northlake Boulevard and marina district."),
    ("palm-beach-gardens", "Palm Beach Gardens", "Palm Beach Gardens", "CORE", "palm beach gardens",
     ["33410", "33418"],
     "Palm Beach Gardens: the PGA Boulevard corridor, PGA National Resort, the Gardens Mall, Downtown Palm Beach "
     "Gardens, Alton and the Interstate 95 / Florida's Turnpike interchanges, north to the Donald Ross Road "
     "line with Jupiter."),
    ("jupiter-tequesta", "Jupiter / Tequesta / Jupiter Island approach", "Jupiter & Tequesta", "CORE", "jupiter",
     ["33458", "33469", "33477", "33478"],
     "The county's northern coast: Jupiter Beach and the Jupiter Inlet Lighthouse, Indiantown Road, Abacoa and "
     "Roger Dean Stadium, the Loxahatchee River, Tequesta's US-1 village, and the Jupiter Farms acreage west of "
     "the Turnpike. Postal code 33469 crosses the Martin County line on its US-1 approach and is covered whole."),
    ("palm-beach-international-airport", "Palm Beach International Airport / Southern & Okeechobee",
     "PBI Airport & Southern Boulevard", "CORE", "west palm beach",
     ["33405", "33406", "33409", "33415", "33417"],
     "The inland West Palm Beach hotel belt around Palm Beach International Airport: Belvedere Road, Palm Beach "
     "Lakes Boulevard and Village Boulevard, the Southern Boulevard and Okeechobee Boulevard approaches, the "
     "Palm Beach Outlets, Military Trail, and the South Dixie Highway / El Cid and Lake Clarke Shores blocks. "
     "The airport owns no postal code and is reported as an overlay across the corridor."),
    ("lake-worth-beach", "Lake Worth Beach / Greenacres", "Lake Worth Beach", "CORE", "lake worth beach",
     ["33460", "33461", "33463", "33467"],
     "Lake Worth Beach: the downtown Lake and Lucerne Avenue district, the Lake Worth Beach casino building and "
     "municipal pier, the dense South Dixie Highway and Federal Highway motor-court row -- the single largest "
     "concentration of licensed motels in Palm Beach County -- and the Palm Springs, Greenacres and Lake Worth "
     "Road corridors inland."),
    ("delray-beach", "Delray Beach", "Delray Beach", "CORE", "delray beach",
     ["33444", "33445", "33446", "33482", "33483", "33484"],
     "Delray Beach: Atlantic Avenue from Swinton to the sea, the municipal beach and A1A oceanfront, Pineapple "
     "Grove, the Federal Highway and Congress Avenue corridors, and the western Atlantic Avenue communities "
     "toward Military Trail."),
    ("boca-raton", "Boca Raton / Highland Beach", "Boca Raton", "CORE", "boca raton",
     ["33427", "33428", "33429", "33431", "33432", "33433", "33434", "33486", "33487", "33488", "33496", "33498"],
     "Boca Raton: the downtown Mizner Park and Federal Highway district, the Boca Raton Resort and the Boca Inlet, "
     "South Ocean Boulevard, the Glades Road and Town Center corridor, the northern Congress Avenue / NW 53rd "
     "Street and Park at Broken Sound hotel cluster, Florida Atlantic University, west Boca, and Highland Beach's "
     "oceanfront which shares postal code 33487."),
    ("boynton-beach", "Boynton Beach / Ocean Ridge", "Boynton Beach", "CORE", "boynton beach",
     ["33424", "33425", "33426", "33435", "33436", "33437", "33472", "33473", "33474"],
     "Boynton Beach: the Federal Highway and Ocean Avenue downtown, the Boynton Beach Inlet and Ocean Ridge "
     "oceanfront, Gateway Boulevard and the Interstate 95 corridor, Congress Avenue, and the western "
     "Boynton Beach Boulevard communities."),

    ("lantana-manalapan-hypoluxo", "Lantana / Manalapan / Hypoluxo", "Lantana & Manalapan", "CORRIDOR", "lantana",
     ["33462"],
     "The narrow coastal strip between Lake Worth Beach and Boynton Beach on one shared postal code: Lantana's "
     "Ocean Avenue and municipal beach, Manalapan's South Ocean Boulevard resort frontage (Eau Palm Beach), "
     "Hypoluxo Island, and the Lantana Road / Dixie Highway approach. Lantana, Manalapan and Hypoluxo all use "
     "33462; each is reported as an overlay."),
    ("north-palm-beach-juno-beach", "North Palm Beach / Juno Beach", "North Palm Beach & Juno Beach", "CORRIDOR",
     "north palm beach",
     ["33408"],
     "The shared postal code north of the Earman River: North Palm Beach's US-1 and Northlake Boulevard village, "
     "Juno Beach's Ocean Drive oceanfront and the Loggerhead Marinelife Center, and the southern Palm Beach "
     "Gardens blocks that also use 33408. Each is reported as an overlay."),

    ("western-communities", "Wellington / Royal Palm Beach / Loxahatchee", "Wellington & Royal Palm Beach",
     "FRINGE", "wellington",
     ["33411", "33412", "33413", "33414", "33449", "33470"],
     "The western communities: Wellington's equestrian district and the Winter Equestrian Festival showgrounds, "
     "the Village of Royal Palm Beach, Greenacres and Haverhill, Westlake and the Seminole Pratt Whitney corridor, "
     "Loxahatchee Groves and The Acreage, and the Ibis and Northlake Boulevard west blocks; careful evaluation, "
     "admitted at FRINGE density."),
    ("the-glades", "Belle Glade / Pahokee / South Bay", "The Glades", "FRINGE", "belle glade",
     ["33430", "33438", "33476", "33493"],
     "The Glades: Belle Glade, South Bay, Pahokee and Canal Point on the southeastern shore of Lake Okeechobee, "
     "forty miles inland from the coast across the Everglades Agricultural Area. Palm Beach County and Discover "
     "The Palm Beaches territory, admitted at FRINGE density so the county's own inventory is accounted for "
     "rather than silently dropped; far below any publication threshold."),
]

#: Municipalities OUTSIDE the admitted market, each with the reason. A row names the market it is preserved for.
OUTSIDE = [
    ("Deerfield Beach / Pompano Beach / Fort Lauderdale / all Broward County", "FL",
     ["33004", "33009", "33019", "33020", "33021", "33023", "33024", "33025", "33026", "33027", "33028", "33029",
      "33060", "33062", "33063", "33064", "33065", "33066", "33067", "33068", "33069", "33071", "33073", "33076",
      "33301", "33304", "33305", "33306", "33308", "33309", "33311", "33312", "33313", "33314", "33315", "33316",
      "33317", "33319", "33321", "33322", "33323", "33324", "33325", "33326", "33327", "33328", "33330", "33331",
      "33332", "33334", "33351", "33441", "33442"],
     "Broward County; EXISTING_LIVE_MARKET fort-lauderdale-fl (live as market #32, deploy "
     "6ab1a035c7ef3b14a23a4ec6). Deerfield Beach 33441 / 33442 adjoins Boca Raton directly across the county "
     "line and is ALREADY PUBLISHED by that market's 'deerfield-beach' corridor; admitting it here would publish "
     "one hotel in two markets. Refused by the line, not by distance."),
    ("Miami / Miami Beach / Greater Miami-Dade", "FL",
     ["33101", "33109", "33122", "33125", "33126", "33127", "33128", "33129", "33130", "33131", "33132", "33133",
      "33134", "33135", "33136", "33137", "33138", "33139", "33140", "33141", "33142", "33143", "33144", "33145",
      "33146", "33147", "33149", "33150", "33154", "33155", "33156", "33157", "33158", "33160", "33161", "33162",
      "33165", "33166", "33167", "33168", "33169", "33170", "33172", "33173", "33174", "33175", "33176", "33177",
      "33178", "33179", "33180", "33181", "33182", "33183", "33184", "33185", "33186", "33187", "33189", "33190",
      "33193", "33194", "33196", "33010", "33012", "33013", "33014", "33015", "33016", "33018", "33030", "33031",
      "33032", "33033", "33034", "33035", "33039", "33054", "33055", "33056"],
     "Miami-Dade County; EXISTING_LIVE_MARKET miami-fl (live as market #31). Two counties away from this "
     "market's southern boundary."),
    ("Stuart / Hobe Sound / Jensen Beach / Palm City -- Martin County", "FL",
     ["33455", "34956", "34957", "34990", "34991", "34992", "34994", "34995", "34996", "34997"],
     "Martin County; FUTURE_STANDALONE treasure-coast-fl, a separate CVB (Discover Martin County) and a "
     "separate travel market. Refused by name. The ONE border case that required review is postal code 33469 "
     "(Tequesta), a PALM BEACH COUNTY code whose US-1 approach spills across the line; it is admitted WHOLE by "
     "this registry -- see the county boundary audit -- and no 349xx or 33455 code is admitted."),
    ("Port St. Lucie / Fort Pierce -- St. Lucie County", "FL",
     ["34945", "34946", "34947", "34949", "34950", "34951", "34952", "34953", "34981", "34982", "34983", "34984",
      "34986", "34987", "34988"],
     "St. Lucie County; FUTURE_STANDALONE treasure-coast-fl; refused by name."),
    ("Florida Keys (Key Largo / Islamorada / Marathon / Key West)", "FL",
     ["33036", "33037", "33040", "33041", "33042", "33043", "33044", "33045", "33050", "33051", "33052", "33070"],
     "Monroe County; FUTURE_STANDALONE florida-keys-fl; refused by name."),
]

#: County-level boundary for the registry lane (DBPR states each licence's county). Palm Beach is the county the
#: admitted corridors sit in; every other county row is OUTSIDE by county before any ZIP lookup, EXCEPT where a
#: Palm Beach postal code the registry covers whole reaches across a line (33469) -- see MARTIN_BORDER_RULE.
ADMITTED_COUNTIES = {"palm beach"}
OBSERVED_COUNTIES = OrderedDict([
    ("broward", "fort-lauderdale-fl"), ("dade", "miami-fl"), ("miami-dade", "miami-fl"),
    ("martin", "treasure-coast-fl"), ("st. lucie", "treasure-coast-fl"), ("monroe", "florida-keys-fl"),
])

#: The one border case the order's "Martin County unless exact border evidence requires review" clause names.
MARTIN_BORDER_RULE = OrderedDict([
    ("postal_code", "33469"),
    ("postal_code_county", "Palm Beach (Tequesta) -- 45 of its 51 lodging licences are Palm Beach County"),
    ("spills_into", "Martin County -- 6 lodging licences, 2 of them hotel-rank, on the SE Federal Highway / US-1 "
                    "approach north of the county line, every one of them addressed 'TEQUESTA FL 33469'"),
    ("ruling", "ADMITTED WHOLE. The governing rule of this market is the property's OWN postal code; the DBPR "
               "'county' field is the LICENSING county, not the premises' postal geography. Splitting 33469 "
               "would be a per-property judgement, which is exactly what the corridor registry exists to "
               "forbid, and would contradict the shared-postal-code rule applied to every other corridor."),
    ("reported_as", "MARTIN COUNTY ADMITTED in the Phase 22 county boundary audit, with each row named."),
    ("every_other_martin_code", "REFUSED by name: 33455 (Hobe Sound) and the 349xx Stuart / Jensen Beach / Palm "
                                "City / Indiantown codes."),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / club-member only).
NONPUBLIC_NAMES = {}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-west-palm-beach", "West Palm Beach", "Downtown West Palm Beach", 26.7100, -80.0550, 3000, True),
    ("palm-beach-worth-avenue", "Palm Beach", "Palm Beach / Worth Avenue", 26.7050, -80.0360, 3000, True),
    ("northwood-metrocentre", "West Palm Beach", "Northwood / Metrocentre / 45th Street",
     26.7600, -80.0700, 3600, True),
    ("riviera-beach-singer-island", "Riviera Beach", "Riviera Beach / Singer Island / Lake Park",
     26.7850, -80.0550, 4200, True),
    ("palm-beach-gardens", "Palm Beach Gardens", "Palm Beach Gardens", 26.8400, -80.1100, 6000, True),
    ("jupiter-tequesta", "Jupiter", "Jupiter / Tequesta", 26.9350, -80.1000, 7000, True),
    ("palm-beach-international-airport", "West Palm Beach", "PBI Airport / Southern & Okeechobee",
     26.6800, -80.0950, 5500, True),
    ("lake-worth-beach", "Lake Worth Beach", "Lake Worth Beach / Greenacres", 26.6150, -80.0800, 5000, True),
    ("delray-beach", "Delray Beach", "Delray Beach", 26.4600, -80.0800, 5000, True),
    ("boca-raton", "Boca Raton", "Boca Raton / Highland Beach", 26.3650, -80.1000, 7000, True),
    ("boynton-beach", "Boynton Beach", "Boynton Beach / Ocean Ridge", 26.5300, -80.0800, 5000, True),
    ("lantana-manalapan-hypoluxo", "Lantana", "Lantana / Manalapan / Hypoluxo", 26.5850, -80.0500, 3000, True),
    ("north-palm-beach-juno-beach", "North Palm Beach", "North Palm Beach / Juno Beach",
     26.8250, -80.0600, 3400, True),
    ("western-communities", "Wellington", "Wellington / Royal Palm Beach / Loxahatchee",
     26.6550, -80.2400, 9000, True),
    ("the-glades", "Belle Glade", "Belle Glade / Pahokee / South Bay", 26.6900, -80.6700, 12000, True),
    ("obs-deerfield-boca-line", "Deerfield Beach", "Deerfield Beach -- OBSERVATION ONLY (Broward, LIVE market)",
     26.3180, -80.0950, 4000, False),
    ("obs-hobe-sound-stuart", "Hobe Sound", "Hobe Sound / Stuart -- OBSERVATION ONLY (Martin County)",
     27.0600, -80.1400, 9000, False),
]

BOUNDS = {"min_lat": 26.28, "max_lat": 27.10, "min_lng": -80.80, "max_lng": -80.02}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Downtown West Palm Beach", 26.7120, -80.0530, 1.6),
    ("Clematis Street", 26.7130, -80.0510, 0.8),
    ("Rosemary Square", 26.7020, -80.0560, 0.9),
    ("Palm Beach County Convention Center", 26.6980, -80.0570, 0.8),
    ("Brightline West Palm Beach", 26.7100, -80.0580, 0.7),
    ("Flagler Drive / Intracoastal", 26.7060, -80.0480, 1.6),
    ("Norton Museum of Art", 26.6900, -80.0520, 0.8),
    ("Worth Avenue", 26.7000, -80.0390, 1.0),
    ("The Breakers", 26.7150, -80.0350, 1.0),
    ("South Ocean Boulevard, Palm Beach", 26.6700, -80.0370, 3.0),
    ("Royal Poinciana Way", 26.7180, -80.0420, 0.8),
    ("Metrocentre / Northpoint Parkway", 26.7570, -80.0740, 1.2),
    ("Northwood Village", 26.7420, -80.0560, 1.0),
    ("Broadway / US-1 West Palm Beach", 26.7600, -80.0620, 2.0),
    ("Singer Island", 26.7900, -80.0350, 2.6),
    ("Palm Beach Shores", 26.7760, -80.0350, 1.2),
    ("Port of Palm Beach", 26.7700, -80.0530, 1.2),
    ("Blue Heron Boulevard", 26.7830, -80.0600, 2.0),
    ("Lake Park / Northlake Boulevard", 26.8000, -80.0700, 2.2),
    ("PGA Boulevard", 26.8420, -80.0880, 3.0),
    ("PGA National Resort", 26.8360, -80.1440, 1.6),
    ("Gardens Mall", 26.8420, -80.0880, 1.0),
    ("Jupiter Beach", 26.9340, -80.0740, 2.4),
    ("Jupiter Inlet Lighthouse", 26.9480, -80.0820, 1.2),
    ("Abacoa / Roger Dean Stadium", 26.9130, -80.1150, 1.6),
    ("Indiantown Road", 26.9340, -80.1300, 3.0),
    ("Tequesta", 26.9640, -80.0880, 2.0),
    ("Palm Beach International Airport (PBI)", 26.6832, -80.0956, 3.0),
    ("Belvedere Road", 26.6850, -80.1100, 3.0),
    ("Palm Beach Lakes Boulevard", 26.7180, -80.0900, 2.6),
    ("Southern Boulevard", 26.6720, -80.1100, 3.0),
    ("Okeechobee Boulevard", 26.7050, -80.1100, 3.0),
    ("Palm Beach Outlets", 26.7160, -80.0840, 1.0),
    ("Lake Clarke Shores", 26.6480, -80.0760, 1.6),
    ("Lake Worth Beach", 26.6170, -80.0560, 2.0),
    ("Lake Worth Beach Casino & Pier", 26.6130, -80.0340, 1.0),
    ("Lake Avenue / Lucerne Avenue", 26.6170, -80.0570, 1.0),
    ("Dixie Highway, Lake Worth", 26.6100, -80.0620, 2.4),
    ("Palm Springs", 26.6360, -80.0960, 2.0),
    ("Greenacres", 26.6250, -80.1250, 2.6),
    ("Lantana", 26.5870, -80.0520, 1.8),
    ("Manalapan", 26.5720, -80.0400, 1.6),
    ("Hypoluxo", 26.5620, -80.0520, 1.2),
    ("Boynton Beach", 26.5250, -80.0660, 3.0),
    ("Ocean Ridge", 26.5250, -80.0450, 1.6),
    ("Atlantic Avenue, Delray Beach", 26.4620, -80.0730, 2.4),
    ("Delray Beach oceanfront", 26.4620, -80.0620, 1.6),
    ("Pineapple Grove", 26.4680, -80.0720, 0.8),
    ("Mizner Park", 26.3540, -80.0840, 1.0),
    ("Boca Raton Resort", 26.3420, -80.0780, 1.2),
    ("Glades Road / Town Center", 26.3680, -80.1250, 3.0),
    ("Park at Broken Sound", 26.4030, -80.1000, 2.0),
    ("Florida Atlantic University", 26.3720, -80.1020, 1.6),
    ("Highland Beach", 26.4000, -80.0650, 2.4),
    ("Wellington", 26.6580, -80.2410, 4.5),
    ("Winter Equestrian Festival showgrounds", 26.6620, -80.2620, 1.6),
    ("Royal Palm Beach", 26.7060, -80.2300, 3.5),
    ("Westlake", 26.7650, -80.2600, 3.0),
    ("Loxahatchee / The Acreage", 26.7500, -80.2900, 5.0),
    ("Belle Glade", 26.6840, -80.6680, 4.0),
    ("Pahokee", 26.8200, -80.6650, 3.0),
    ("South Bay", 26.6690, -80.7160, 2.5),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Worth Avenue", re.compile(r"\bworth ave(nue)?\b", re.I)),
    ("The Breakers", re.compile(r"\bbreakers row\b|\bcounty rd\b(?=.*breakers)", re.I)),
    ("Royal Poinciana Way", re.compile(r"\broyal poinciana\b", re.I)),
    ("South Ocean Boulevard, Palm Beach", re.compile(r"\bs(outh)? ocean b(lv)?d\b", re.I)),
    ("Clematis Street", re.compile(r"\bclematis st\b", re.I)),
    ("Rosemary Square", re.compile(r"\brosemary ave\b|\bcityplace\b|\brosemary square\b", re.I)),
    ("Flagler Drive / Intracoastal", re.compile(r"\b(n|s|north|south)? ?flagler dr\b", re.I)),
    ("Okeechobee Boulevard", re.compile(r"\bokeechobee b(lv)?d\b", re.I)),
    ("Metrocentre / Northpoint Parkway", re.compile(r"\bmetrocentre\b|\bnorthpoint p(k|ar)kwy\b|\bnorthpoint pkwy\b", re.I)),
    ("Broadway / US-1 West Palm Beach", re.compile(r"\bbroadway\b", re.I)),
    ("Northwood Village", re.compile(r"\bnorthwood rd\b", re.I)),
    ("Singer Island", re.compile(r"\bsinger island\b|\bocean ave\b(?=.*singer)", re.I)),
    ("Blue Heron Boulevard", re.compile(r"\bblue heron\b", re.I)),
    ("Port of Palm Beach", re.compile(r"\bport of palm beach\b|\beast port rd\b", re.I)),
    ("Lake Park / Northlake Boulevard", re.compile(r"\bnorthlake b(lv)?d\b", re.I)),
    ("PGA Boulevard", re.compile(r"\bpga b(lv)?d\b|\bpga national\b|\bavenue of the champions\b", re.I)),
    ("Indiantown Road", re.compile(r"\bindiantown rd\b", re.I)),
    ("Abacoa / Roger Dean Stadium", re.compile(r"\bmain st\b(?=.*jupiter)|\buniversity b(lv)?d\b", re.I)),
    ("Palm Beach International Airport (PBI)", re.compile(
        r"\bbelvedere rd\b|\bturnage b(lv)?d\b|\bpbi\b|\bpalm beach int(ernational)?\b|\baustralian ave\b", re.I)),
    ("Palm Beach Lakes Boulevard", re.compile(r"\bpalm beach lakes\b|\bvillage b(lv)?d\b", re.I)),
    ("Southern Boulevard", re.compile(r"\bsouthern b(lv)?d\b", re.I)),
    ("Lake Avenue / Lucerne Avenue", re.compile(r"\blake ave\b|\blucerne ave\b", re.I)),
    ("Dixie Highway, Lake Worth", re.compile(r"\b(s|n|south|north)? ?dixie hwy\b", re.I)),
    ("Atlantic Avenue, Delray Beach", re.compile(r"\b(e|w|east|west)? ?atlantic ave\b", re.I)),
    ("Pineapple Grove", re.compile(r"\bpineapple grove\b|\bne 2 ave\b", re.I)),
    ("Mizner Park", re.compile(r"\bmizner\b|\bplaza real\b", re.I)),
    ("Glades Road / Town Center", re.compile(r"\bglades rd\b", re.I)),
    ("Park at Broken Sound", re.compile(r"\bnw 53 st\b|\bnw 77 st\b|\bbroken sound\b|\bcongress ave\b", re.I)),
    ("Winter Equestrian Festival showgrounds", re.compile(r"\bpierson rd\b|\bsouth shore b(lv)?d\b", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-west-palm-beach": "Downtown West Palm Beach",
    "palm-beach-worth-avenue": "Worth Avenue",
    "northwood-metrocentre": "Metrocentre / Northpoint Parkway",
    "riviera-beach-singer-island": "Singer Island",
    "palm-beach-gardens": "PGA Boulevard",
    "jupiter-tequesta": "Jupiter Beach",
    "palm-beach-international-airport": "Palm Beach International Airport (PBI)",
    "lake-worth-beach": "Lake Worth Beach",
    "delray-beach": "Atlantic Avenue, Delray Beach",
    "boca-raton": "Mizner Park",
    "boynton-beach": "Boynton Beach",
    "lantana-manalapan-hypoluxo": "Lantana",
    "north-palm-beach-juno-beach": "North Palm Beach / Juno Beach",
    "western-communities": "Wellington",
    "the-glades": "Belle Glade",
}

STRUCTURE_TEST = OrderedDict([
    ("A. Is The Palm Beaches one market, or several?",
     "ONE market, west-palm-beach-fl, covering Palm Beach County. One county, one commercial airport (PBI), one "
     "CVB -- Discover The Palm Beaches markets all 39 county municipalities together under that single brand -- "
     "one Brightline spine and one contiguous I-95 / US-1 / A1A coastal system. The order's instruction is "
     "followed literally: the county-wide travel market was tested for coherence FIRST, and Boca Raton, Delray "
     "Beach and the Town of Palm Beach are corridors inside it, not separate markets, however large they are."),
    ("B. West Palm Beach vs Palm Beach",
     "TWO CORE corridors, and this is the market's defining identity rule. downtown-west-palm-beach (33401, "
     "33402) is the mainland city: Clematis Street, Rosemary Square, the Convention Center, Brightline. "
     "palm-beach-worth-avenue (33480) is the island Town of Palm Beach: Worth Avenue, The Breakers, the Four "
     "Seasons, the Colony. They are separate municipalities on separate postal codes with separate travel "
     "products. A property's own postal code decides which it is; the words 'Palm Beach' in a hotel's name "
     "decide nothing."),
    ("C. Palm Beach International Airport (PBI)",
     "NO CORRIDOR OF ITS OWN -- the airport owns no postal code, exactly as FLL owned none in Broward. Its hotel "
     "district spreads across Belvedere Road (33406), Palm Beach Lakes Boulevard and Village Boulevard (33409) "
     "and 33415. Those, with 33405 and 33417, form the single inland corridor "
     "palm-beach-international-airport, and 'PBI' is a street-and-pin overlay inside it."),
    ("D. The Port of Palm Beach / cruise lodging",
     "NO CORRIDOR -- and for the PortMiami reason, not the Port Everglades one. The port sits in Riviera Beach "
     "33404 and carries no hotel inventory that riviera-beach-singer-island does not already claim, so a cruise "
     "corridor would duplicate that corridor's own postal code. The port is an OVERLAY. The corridor registry "
     "is a partition, and a port earns a corridor only where it owns hotel-bearing postal codes no other "
     "corridor claims."),
    ("E. Riviera Beach / Singer Island",
     "CORE, one corridor riviera-beach-singer-island (33403, 33404). The barrier island (Singer Island, Palm "
     "Beach Shores) and its mainland (Riviera Beach, Lake Park) share 33404 and 33403 and are covered whole, "
     "with Singer Island, Palm Beach Shores and the Port of Palm Beach reported as overlays. Palm Beach Shores "
     "is a distinct municipality whose name contains 'Palm Beach' and which is NOT the Town of Palm Beach."),
    ("F. Palm Beach Gardens",
     "CORE, one corridor palm-beach-gardens (33410, 33418). The PGA Boulevard corridor, PGA National Resort and "
     "the Gardens Mall are a genuine, self-contained lodging and golf destination with its own inventory. "
     "33418's 315 lodging licences are overwhelmingly PGA National's villa and condominium programme, which "
     "never enters the graph."),
    ("G. Jupiter / Tequesta",
     "CORE, one corridor jupiter-tequesta (33458, 33469, 33477, 33478). Jupiter Beach, the Inlet lighthouse, "
     "Abacoa and Indiantown Road are the county's northern coastal anchor. 33469 (Tequesta) crosses the Martin "
     "County line and is covered whole -- the one border case the order's Martin clause names."),
    ("H. Lake Worth Beach",
     "CORE, one corridor lake-worth-beach (33460, 33461, 33463, 33467). 33460 alone carries 20 hotel-rank "
     "licences, 18 of them MOTELS -- the densest motel row in Palm Beach County, along South Dixie and Federal "
     "Highway. Palm Springs and Greenacres share 33461 / 33463 / 33467 and are overlays. Lake Worth Beach "
     "renamed itself from 'Lake Worth' in 2019 and the registry still carries both spellings."),
    ("I. Lantana / Manalapan",
     "CORRIDOR, one corridor lantana-manalapan-hypoluxo (33462). A narrow coastal strip carrying 7 hotel-rank "
     "licences including Manalapan's oceanfront resort frontage (Eau Palm Beach). Too thin to be CORE, too "
     "distinct -- and too valuable -- to fold into Lake Worth Beach or Boynton Beach."),
    ("J. Boynton Beach",
     "CORE, one corridor boynton-beach. Its own downtown, inlet and oceanfront at Ocean Ridge, which shares "
     "33435 and is an overlay. A distinct municipality between Lantana and Delray Beach."),
    ("K. Delray Beach",
     "CORE, one corridor delray-beach. Atlantic Avenue is one of the strongest walkable traveller streets in "
     "South Florida and 33483 carries 13 hotel-rank licences on its own. Never folded into Boca Raton or "
     "Boynton Beach; each is its own municipality and its own corridor."),
    ("L. Boca Raton",
     "CORE, one corridor boca-raton, covering all twelve Boca postal codes plus Highland Beach's shared 33487. "
     "25 hotel-rank licences, the county's second-largest concentration, in three distinct clusters: downtown / "
     "Mizner Park and the Boca Raton Resort (33432), the Glades Road / Town Center belt (33431, 33433, 33434, "
     "33486) and the northern Congress Avenue / Park at Broken Sound hotel cluster (33487). It is INSIDE this "
     "market: Palm Beach County, Discover The Palm Beaches territory, PBI's own catchment. It is never folded "
     "into generic West Palm Beach and it never reaches south over the Broward line."),
    ("M. North Palm Beach / Juno Beach",
     "CORRIDOR, one corridor north-palm-beach-juno-beach (33408). Two municipalities plus part of a third "
     "(Palm Beach Gardens) on one shared postal code, carrying 4 hotel-rank licences. Careful evaluation; "
     "admitted at CORRIDOR tier and covered whole."),
    ("N. Wellington / Royal Palm Beach / the western communities",
     "FRINGE, one corridor western-communities (33411, 33412, 33413, 33414, 33449, 33470). Wellington's "
     "Winter Equestrian Festival is a real seasonal demand generator, but its lodging is overwhelmingly "
     "seasonal equestrian rental stock (33414 carries 230 lodging licences and just 2 hotel-rank), so the area "
     "is admitted at FRINGE density on one corridor. Westlake, Greenacres, Haverhill, Loxahatchee Groves and "
     "The Acreage sit here too."),
    ("O. The Glades (Belle Glade / Pahokee / South Bay / Canal Point)",
     "FRINGE, one corridor the-glades. Forty miles inland on Lake Okeechobee, agricultural rather than "
     "coastal-traveller -- but Palm Beach County and Discover The Palm Beaches territory, carrying 4 hotel-rank "
     "licences. Admitted at FRINGE so the home county's own inventory is ACCOUNTED FOR rather than silently "
     "dropped, and far below any publication threshold; it will never produce a page."),
    ("P. Deerfield Beach and the Broward line",
     "OUTSIDE, and this is a hard constraint rather than a judgement: Deerfield Beach 33441 / 33442 is Broward "
     "County and is ALREADY PUBLISHED by the LIVE fort-lauderdale-fl market. Boca Raton adjoins it directly. "
     "Admitting it would publish the same hotel in two markets. The county line decides."),
])

#: The cruise test the two prior South Florida markets established, applied here and FAILED (deliberately).
CRUISE_TEST = OrderedDict([
    ("port_of_palm_beach_lodging_in_its_own_postal_code",
     "NO. The Port of Palm Beach sits at the east end of Riviera Beach in postal code 33404, which is already "
     "claimed in full by riviera-beach-singer-island. 33404's 13 hotel-rank licences are Singer Island's "
     "oceanfront, Palm Beach Shores at the inlet and Riviera Beach's Broadway blocks -- the corridor's own "
     "inventory, not a separate port hotel district."),
    ("would_a_port_corridor_duplicate_inventory", True),
    ("port_corridor_created", False),
    ("why",
     "The corridor registry is a postal-code partition, so a 'Port of Palm Beach' corridor could only be built "
     "by SPLITTING 33404 -- a per-property judgement the registry forbids -- or by duplicating it, which the "
     "partition forbids outright. This is the PortMiami finding (Dodge Island: terminals, no separable hotel "
     "inventory), not the Port Everglades finding (33316: a postal code full of hotels claimed by nothing "
     "else). A port earns a corridor only when it owns hotel-bearing postal codes no other corridor claims. "
     "The Port of Palm Beach is reported as a street-and-pin OVERLAY inside riviera-beach-singer-island, and "
     "cruise relevance never altered one premises identity."),
    ("pbi_airport_corridor_created", False),
    ("pbi_why", "The same rule: PBI owns no postal code. Its hotels are on Belvedere Road (33406), Palm Beach "
                "Lakes / Village Boulevard (33409) and 33415, all inside the single "
                "palm-beach-international-airport corridor, where 'PBI' is an overlay."),
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
     "the pool, the golf course and the booking engine. Palm Beach County's specific exposures: The Breakers' "
     "and Eau Palm Beach's residence inventory, the Boca Raton Resort's towers, PGA National's villa programme, "
     "Singer Island's and Highland Beach's condo-hotel towers, and Wellington's equestrian-season rentals."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared "
     "amenities or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never "
     "published as one."),
    ("country_club_lodging",
     "Member-only or guest-of-member club lodging (Palm Beach County carries a great deal of it) is NOT public "
     "lodging and is refused unless the operator's own page sells rooms nightly to the general public."),
])

#: The shared postal codes the corridor registry deliberately covers whole, with the municipalities that share
#: each one on the state's own record. Reporting only -- a shared code is still exactly one corridor.
SHARED_POSTAL_CODES = OrderedDict([
    ("33403", ["Lake Park", "West Palm Beach", "Palm Beach Gardens"]),
    ("33404", ["Riviera Beach", "Palm Beach Shores", "Singer Island", "West Palm Beach"]),
    ("33406", ["West Palm Beach", "Lake Clarke Shores", "Palm Springs"]),
    ("33407", ["West Palm Beach", "Mangonia Park", "Riviera Beach"]),
    ("33408", ["North Palm Beach", "Juno Beach", "Palm Beach Gardens"]),
    ("33409", ["West Palm Beach", "Haverhill"]),
    ("33411", ["West Palm Beach", "Royal Palm Beach"]),
    ("33413", ["West Palm Beach", "Greenacres"]),
    ("33414", ["Wellington", "Royal Palm Beach"]),
    ("33415", ["West Palm Beach", "Haverhill", "Lake Worth"]),
    ("33426", ["Boynton Beach"]),
    ("33435", ["Boynton Beach", "Ocean Ridge"]),
    ("33460", ["Lake Worth Beach", "Lake Worth"]),
    ("33461", ["Lake Worth", "Palm Springs"]),
    ("33462", ["Lantana", "Manalapan", "Hypoluxo"]),
    ("33463", ["Lake Worth", "Greenacres"]),
    ("33469", ["Tequesta", "Jupiter", "(spills into Martin County -- covered whole)"]),
    ("33470", ["Loxahatchee", "The Acreage", "Wellington"]),
    ("33480", ["Palm Beach", "Town of Palm Beach"]),
    ("33483", ["Delray Beach"]),
    ("33487", ["Boca Raton", "Highland Beach"]),
])

#: FUTURE standalone markets this order preserves by name.
FUTURE_MARKETS = OrderedDict([
    ("treasure-coast-fl", "Stuart / Hobe Sound / Jensen Beach / Port St. Lucie / Fort Pierce -- Martin and "
                          "St. Lucie Counties, their own CVBs and their own travel market"),
    ("florida-keys-fl", "The Florida Keys (Key Largo / Islamorada / Marathon / Key West) -- Monroe County, its "
                        "own island resort market"),
])

#: Markets that are ALREADY LIVE and own the inventory this market refuses. Never 'future'.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("fort-lauderdale-fl", "Fort Lauderdale / Greater Broward County, live as market #32 (deploy "
                           "6ab1a035c7ef3b14a23a4ec6). Owns every Broward postal code, including Deerfield "
                           "Beach 33441 / 33442 immediately south of Boca Raton across the county line."),
    ("miami-fl", "Miami - Miami Beach / Greater Miami-Dade, live as market #31 (deploy "
                 "6ab071a5b7561c33aff6c17b). Owns every Miami-Dade postal code."),
])

MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "wpb": "west palm beach", "w palm beach": "west palm beach", "westpalm beach": "west palm beach",
    "west palm": "west palm beach", "west": "west palm beach", "w. palm beach": "west palm beach",
    "west plam beach": "west palm beach", "west palm beach,": "west palm beach",
    "town of palm beach": "palm beach", "palm beach,": "palm beach",
    "palm beach garden": "palm beach gardens", "palms beach garden": "palm beach gardens",
    "palm beach gardens,": "palm beach gardens", "pbg": "palm beach gardens",
    "n palm beach": "north palm beach", "no palm beach": "north palm beach",
    "royal plm beach": "royal palm beach", "royal palm bch": "royal palm beach",
    "lake worth": "lake worth beach", "lakek worth": "lake worth beach", "lakeworth": "lake worth beach",
    "lake worth bch": "lake worth beach",
    "boyton beach": "boynton beach", "boynton bch": "boynton beach", "boynton blvd": "boynton beach",
    "del ray beach": "delray beach", "delray": "delray beach", "delray bch": "delray beach",
    "boca": "boca raton", "bo": "boca raton", "boca raton, florida": "boca raton", "boca rator": "boca raton",
    "green acres city": "greenacres", "green acres": "greenacres",
    "village of wellingto": "wellington", "village of wellington": "wellington", "wellington,": "wellington",
    "singer island": "riviera beach", "palm beach shores": "palm beach shores",
    "jupiter,": "jupiter", "jupiter farms": "jupiter", "tequesta,": "tequesta",
    "juno bch": "juno beach", "highland bch": "highland beach",
    "belle glade,": "belle glade", "canal point,": "canal point",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("33401", "West Palm Beach downtown -- 18 hotel-rank licences, the market's largest single code."),
    ("33460", "Lake Worth Beach -- 20 hotel-rank licences, 18 of them motels; the densest motel row in the county."),
    ("33480", "Town of Palm Beach -- 12 hotel-rank licences on 83 lodging licences total; the luxury anchor."),
    ("33407", "North West Palm Beach -- 13, split between the Metrocentre chain cluster and the Broadway motor courts."),
    ("33404", "Riviera Beach / Singer Island / Palm Beach Shores -- 13."),
    ("33483", "Delray Beach oceanfront and Atlantic Avenue -- 13."),
    ("33487", "North Boca Raton / Highland Beach -- 8."),
    ("33410", "Palm Beach Gardens PGA Boulevard -- 8."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder West Palm Beach" % name),
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
        ("market_name", "West Palm Beach / The Palm Beaches, Florida beach, resort, equestrian and convention "
                        "lodging market (PetTripFinder discovery scope)"),
        ("state", "FL"),
        ("states", ["FL"]),
        ("country", "US"),
        ("market_center", {"lat": 26.71, "lng": -80.06}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past the Broward County line "
             "(Deerfield Beach) and north past the Martin County line (Hobe Sound) so that " + WORK_ORDER +
             " classifies those properties on evidence instead of being blind to them. Admission is decided by "
             "the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". The Palm Beaches are ONE Palm Beach County market: eleven CORE corridors (Downtown West "
         "Palm Beach, Palm Beach/Worth Avenue, Northwood/Metrocentre, Riviera Beach/Singer Island, Palm Beach "
         "Gardens, Jupiter/Tequesta, PBI Airport, Lake Worth Beach, Delray Beach, Boca Raton, Boynton Beach), "
         "two CORRIDOR tiers and two FRINGE corridors. Broward County belongs to the LIVE fort-lauderdale-fl "
         "market and Miami-Dade to the LIVE miami-fl market; Martin / St. Lucie and the Florida Keys are "
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
        ("market_name", "West Palm Beach, Florida"),
        ("market_slug", MARKET_ID),
        ("state_name", "Florida"),
        ("state_code", "FL"),
        ("primary_state_code", "FL"),
        ("states", ["FL"]),
        ("primary_city", "West Palm Beach"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in West Palm Beach & The Palm Beaches, Florida | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across The Palm Beaches -- downtown West Palm Beach, Palm Beach and Worth "
         "Avenue, Palm Beach Gardens, Singer Island, Jupiter, Lake Worth Beach, Delray Beach, Boynton Beach and "
         "Boca Raton -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "West Palm Beach"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its Florida DBPR "
         "public-lodging licence states it, joined to the corridor registry. A Palm Beach County beach, resort, "
         "equestrian and convention travel market -- not the City of West Palm Beach's limits and not all of "
         "South Florida. Nothing else admits a property: not a brand's 'Palm Beach' marketing name, not a map "
         "pin, not a vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Palm Beach County's "
         "postal codes straddle municipalities: 33404 is shared by Riviera Beach, Palm Beach Shores, Singer "
         "Island and West Palm Beach; 33408 by North Palm Beach, Juno Beach and Palm Beach Gardens; 33403 by "
         "Lake Park, West Palm Beach and Palm Beach Gardens; 33406 by West Palm Beach, Lake Clarke Shores and "
         "Palm Springs; 33462 by Lantana, Manalapan and Hypoluxo; 33487 by Boca Raton and Highland Beach; 33435 "
         "by Boynton Beach and Ocean Ridge; 33469 by Tequesta and Jupiter. Each shared code is one corridor and "
         "its named places are reported as overlays. Worth Avenue, The Breakers, PBI, the Port of Palm Beach, "
         "Singer Island, PGA Boulevard, Mizner Park, Atlantic Avenue and the Winter Equestrian Festival "
         "showgrounds are overlays, never corridors of their own."),
        ("_census_membership_note",
         "Individual condominium units (DBPR CNDO), vacation dwellings (DWEL), vacation homes, property-management "
         "portfolios, Airbnb / Vrbo inventory, ordinary apartments (DBPR NAPT), individual timeshare units, private "
         "resort / branded residences, equestrian-season rentals and member-only club lodging are never admitted. "
         "A mixed hotel / condo / residence property is admitted only as the exact hotel premises its public "
         "operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "3 + 4 + 5 -- West Palm Beach / Palm Beach County ('The Palm Beaches') travel-market geography, "
                  "the county-coherence structure test, the Port of Palm Beach cruise test and the luxury-resort "
                  "/ condo-hotel / country-club safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "REGISTERED: the market document is written to the registry's markets/west-palm-beach-fl.json by "
         "PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002. The source-ready order's markets/proposed/ copy is history."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its Florida DBPR public-lodging licence states "
         "it, joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes (and, for the registry lane, by "
                          "county); the existing live markets and future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("palm_beaches_structure_test", STRUCTURE_TEST),
        ("port_of_palm_beach_cruise_test", CRUISE_TEST),
        ("martin_county_border_rule", MARTIN_BORDER_RULE),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("west_palm_beach_vs_palm_beach",
         "THE market's identity trap, stated before any hotel is admitted. Seven Palm Beach County municipalities "
         "carry 'Palm' in their names -- West Palm Beach (33401/33402/33405/33406/33407/33409/33411/33412/33413/"
         "33415/33417), the Town of Palm Beach (33480), Palm Beach Gardens (33410/33418), North Palm Beach "
         "(33408), Royal Palm Beach (33411/33414), Palm Beach Shores (33404) and Palm Springs (33406/33461). "
         "A hotel's own postal code decides which one it is in. Its name decides nothing, and no later phase may "
         "place a property by name."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("evaluated_inclusions", OrderedDict([
            ("West Palm Beach", "ADMITTED (CORE) -- downtown-west-palm-beach (33401/33402), "
                                "northwood-metrocentre (33407) and palm-beach-international-airport "
                                "(33405/33406/33409/33415/33417). Primary coverage."),
            ("Palm Beach (Town of)", "ADMITTED (CORE, palm-beach-worth-avenue, 33480), separate from the City of "
                                     "West Palm Beach. Primary coverage."),
            ("Palm Beach Gardens", "ADMITTED (CORE, palm-beach-gardens, 33410/33418; also 33403 in "
                                   "riviera-beach-singer-island and 33408 in north-palm-beach-juno-beach as "
                                   "overlays). Primary coverage."),
            ("Riviera Beach / Singer Island", "ADMITTED (CORE, riviera-beach-singer-island, 33403/33404). "
                                              "Primary coverage."),
            ("Palm Beach Shores", "ADMITTED (CORE, riviera-beach-singer-island, 33404) as an overlay on a shared "
                                  "postal code; a distinct municipality, NOT the Town of Palm Beach."),
            ("Jupiter", "ADMITTED (CORE, jupiter-tequesta, 33458/33477/33478). Primary coverage."),
            ("Boca Raton", "ADMITTED (CORE, boca-raton) -- strong evaluation. Inside this market, not a separate "
                           "one and never folded into Broward."),
            ("Delray Beach", "ADMITTED (CORE, delray-beach) -- strong evaluation."),
            ("Boynton Beach", "ADMITTED (CORE, boynton-beach) -- strong evaluation."),
            ("Lake Worth Beach", "ADMITTED (CORE, lake-worth-beach, 33460/33461/33463/33467) -- strong "
                                 "evaluation. Both the 'Lake Worth' and 'Lake Worth Beach' spellings are "
                                 "normalised to one municipality."),
            ("Wellington", "ADMITTED (FRINGE, western-communities, 33414/33449) -- strong evaluation; its "
                           "lodging is overwhelmingly equestrian-season rental stock."),
            ("Royal Palm Beach", "ADMITTED (FRINGE, western-communities, 33411/33414) -- strong evaluation."),
            ("North Palm Beach", "ADMITTED (CORRIDOR, north-palm-beach-juno-beach, 33408) -- careful evaluation."),
            ("Juno Beach", "ADMITTED (CORRIDOR, north-palm-beach-juno-beach, 33408) -- careful evaluation; an "
                           "overlay on a shared postal code."),
            ("Tequesta", "ADMITTED (CORE, jupiter-tequesta, 33469) -- careful evaluation; 33469 crosses the "
                         "Martin County line and is covered whole."),
            ("Lantana", "ADMITTED (CORRIDOR, lantana-manalapan-hypoluxo, 33462) -- careful evaluation."),
            ("Manalapan", "ADMITTED (CORRIDOR, lantana-manalapan-hypoluxo, 33462) -- careful evaluation; an "
                          "overlay on a shared postal code, carrying the Eau Palm Beach oceanfront."),
            ("Hypoluxo", "ADMITTED (CORRIDOR, lantana-manalapan-hypoluxo, 33462) -- careful evaluation."),
            ("Greenacres", "ADMITTED (CORE lake-worth-beach 33463/33467 and FRINGE western-communities 33413) -- "
                           "careful evaluation; an overlay on shared postal codes."),
            ("Westlake", "ADMITTED (FRINGE, western-communities, 33470) -- careful evaluation; Palm Beach "
                         "County's newest municipality."),
            ("Palm Springs", "ADMITTED (CORE palm-beach-international-airport 33406 and CORE lake-worth-beach "
                             "33461) -- careful evaluation; an overlay on shared postal codes. NOT Palm Springs, "
                             "California."),
            ("Lake Clarke Shores", "ADMITTED (CORE, palm-beach-international-airport, 33406) -- careful "
                                   "evaluation; an overlay on a shared postal code."),
            ("Ocean Ridge", "ADMITTED (CORE, boynton-beach, 33435) -- an overlay on a shared postal code."),
            ("Highland Beach", "ADMITTED (CORE, boca-raton, 33487) -- an overlay on a shared postal code."),
            ("Lake Park", "ADMITTED (CORE, riviera-beach-singer-island, 33403)."),
            ("Mangonia Park", "ADMITTED (CORE, northwood-metrocentre, 33407) -- an overlay."),
            ("Haverhill", "ADMITTED (CORE, palm-beach-international-airport, 33409/33415) -- an overlay."),
            ("Loxahatchee / The Acreage", "ADMITTED (FRINGE, western-communities, 33470)."),
            ("Belle Glade / Pahokee / South Bay / Canal Point",
             "ADMITTED (FRINGE, the-glades) -- Palm Beach County and Discover The Palm Beaches territory. "
             "Admitted so the home county's inventory is accounted for, not because it is a coastal traveller "
             "market; 4 hotel-rank licences, far below any publication threshold."),
            ("Port of Palm Beach", "ADMITTED as an OVERLAY on riviera-beach-singer-island (33404). Never a "
                                   "corridor -- see the cruise test."),
            ("Palm Beach International Airport (PBI)",
             "ADMITTED as an OVERLAY on palm-beach-international-airport (33406/33409/33415). The airport owns "
             "no postal code, so it is never a corridor."),
            ("Properties using 'Palm Beach' mainly as marketing",
             "Never admitted or placed by name: a 'Palm Beach' / 'Palm Beach Airport' / 'West Palm Beach North' "
             "name is placed by its OWN postal code, which may be Riviera Beach, Palm Beach Gardens, Lake Park, "
             "Boynton Beach or Broward County. A 'Boca Raton' name whose own address is Deerfield Beach 33441 is "
             "a Broward property and belongs to the LIVE fort-lauderdale-fl market."),
            ("Deerfield Beach", "OUTSIDE (Broward County) -- the EXISTING LIVE market fort-lauderdale-fl, "
                                "corridor 'deerfield-beach' (33441/33442). Admitting it would publish one hotel "
                                "in two markets."),
            ("Pompano Beach", "OUTSIDE (Broward County) -- fort-lauderdale-fl corridor 'pompano-beach', live."),
            ("Fort Lauderdale", "OUTSIDE (Broward County) -- fort-lauderdale-fl, live as market #32."),
            ("All Broward County inventory", "OUTSIDE -- fort-lauderdale-fl is live and owns it."),
            ("Miami / Miami Beach / all Miami-Dade inventory",
             "OUTSIDE -- miami-fl is live as market #31 and owns it."),
            ("Martin County / Stuart / Hobe Sound",
             "OUTSIDE by name -- future treasure-coast-fl. ONE border case required review and is recorded: "
             "postal code 33469 (Tequesta) crosses the line and is covered WHOLE, so a small number of "
             "Martin-county-licensed premises addressed 'Tequesta FL 33469' are admitted. No 349xx or 33455 "
             "code is admitted."),
            ("Port St. Lucie / Fort Pierce", "OUTSIDE by name -- St. Lucie County, future treasure-coast-fl."),
            ("Florida Keys", "OUTSIDE by name -- Monroe County, future florida-keys-fl."),
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
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, cruise or equestrian keywords; "
         "every corridor is show_in_navigation / show_in_sitemap false until a registration order publishes it. "
         "Worth Avenue, The Breakers, PBI, the Port of Palm Beach, Singer Island, Palm Beach Shores, PGA "
         "Boulevard, Mizner Park, Atlantic Avenue, Highland Beach, Ocean Ridge, Manalapan, Juno Beach, Palm "
         "Springs, Lake Clarke Shores, Greenacres, Westlake and the Winter Equestrian Festival showgrounds are "
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
         "branded residences; equestrian-season rentals; member-only country-club lodging; and privately managed "
         "units inside hotel-condo towers. A mixed hotel / condo / residence property is admitted ONLY as the exact "
         "hotel premises its public operator sells as a hotel, proved on the operator's own page and the licence's "
         "exact premises. Campgrounds, RV parks and hostels are NON_LODGING."),
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
