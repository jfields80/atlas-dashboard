"""PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5, 6, 7, 8, 9, 10 and 11: the Fort Myers / Cape Coral
/ Southwest Florida market, Florida.

Built from zero on the CURRENT hardened lineage: the Salt Lake City-live release 21dacb1c (live lineage commit 3d812f28,
built_from 6959e985). Current verified live at authoring time = salt-lake-city-ut deploy 6ac6f3d213d002249f9c3e67, 45
markets / 4,373 profiles / 4,807 release-index routes / 4,885 served routes, host verified (release_index live-source
--fetch --verify-host). No earlier Fort Myers build exists. Six Florida markets are live (Jacksonville, Orlando, Tampa,
West Palm Beach, Fort Lauderdale, Miami); none admits a Lee, Collier or Charlotte County code, and the build refuses to
admit any code a registered market already admits.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Fort Myers / Cape Coral traveller lodging market -- NOT the City of Fort Myers's municipal boundary, and
NOT "Southwest Florida" -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE markets
named inside OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact to make a
number. The order's "STRONG_CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property card)
states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP
is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing
name ("Fort Myers", "Fort Myers Area", "Beaches of Fort Myers & Sanibel", "RSW Airport", "Naples-Fort Myers", "Naples
North") never admits and never places a property.

ONE MARKET, LEE COUNTY ONLY (PHASE 2)
------------------------------------
The market is Lee County's traveller lodging: the City of Fort Myers (downtown and the River District, Colonial
Boulevard and Cleveland Avenue / US-41, Daniels Parkway and Six Mile Cypress), the I-75 interchanges and Southwest
Florida International Airport (RSW) at Gateway, the City of Cape Coral across the Caloosahatchee, the Town of Fort Myers
Beach on Estero Island, the City of Sanibel, the Village of Estero and the City of Bonita Springs, with North Fort
Myers, Lehigh Acres / Alva and Captiva admitted at FRINGE after careful evaluation. Every row keeps its own
municipality; nothing is flattened into "Fort Myers".

NEIGHBOURHOODS AND DESTINATIONS ARE OVERLAYS, NEVER SPLIT CODES
--------------------------------------------------------------
The River District shares 33901 with the rest of downtown; Gateway, Treeline Avenue, Gulf Coast Town Center, Miromar
Lakes and the airport itself share 33913; Coconut Point shares 33928 with the rest of Estero. The postal code 33931 is
the Town of Fort Myers Beach on ESTERO ISLAND **and** the mainland approach (San Carlos Island, Summerlin Square, Iona)
whose mailing name is also Fort Myers Beach: the code is covered whole, every row publishes Fort Myers Beach (its own
mailing municipality), and the island / mainland split is a REPORTING OVERLAY decided from the row's own street and pin
(BEACH_ISLAND_EVALUATION). The registry partitions CODES, and those named places are overlays -- never a membership
decision and never a split code.

MUNICIPALITY SAFETY (PHASE 3)
-----------------------------
Cape Coral, Fort Myers Beach, Sanibel, Captiva, Bonita Springs, Estero, North Fort Myers, Lehigh Acres and Alva are
their OWN municipalities (or their own unincorporated postal places). A "Fort Myers" label on a Cape Coral, Estero or
Bonita Springs premises is a marketing label: the postal code's municipality list is checked against the row's stated
city (municipality_for_postal / municipality_conflict) and the code's own municipality publishes. North Fort Myers
(33903 / 33917 / 33918) lies north of the Caloosahatchee outside the City of Fort Myers: a "Fort Myers" label there
publishes North Fort Myers.

NAPLES / BONITA SPRINGS (PHASE 4)
---------------------------------
Bonita Springs (Lee County, 34133-34136) is admitted. NAPLES, North Naples, Marco Island, Everglades City, Immokalee
and the rest of Collier County are refused (FUTURE_STANDALONE naples-fl / marco-island-fl / everglades-city-fl). A
"Naples North" or "Naples-Fort Myers" marketing name admits nothing and refuses nothing: the premises' own postal code
decides. Collier County reaches north of Bonita Beach Road into postal code 34134; a premises the State licenses in
COLLIER County is refused there whatever its Bonita Springs mailing label (COUNTY_REFUSALS), so NAPLES / COLLIER
PROFILES ADMITTED = 0.

POST-HURRICANE STATUS, BEACH AND ISLAND SAFETY (PHASES 5-7)
-----------------------------------------------------------
Hurricane Ian (28 September 2022) destroyed or closed much of the Fort Myers Beach, Sanibel and Captiva lodging stock;
Hurricanes Helene and Milton (2024) struck again. Historical existence proves nothing: every beach / island row is
admitted to PUBLICATION only on current first-party evidence of an operating public lodging business (its own live
booking or policy page). The census decides membership by code; the operating status is decided per row from the
property's own current page and never from this module (OPERATING_STATUS_RULE).

CONDOS, VACATION RENTALS AND TIMESHARE (PHASES 8-9)
--------------------------------------------------
Southwest Florida's resort-condominium (DBPR CNDO) and vacation-dwelling (DWEL) inventory dwarfs its hotels -- Fort
Myers Beach alone carries ~1,400 of them against ~20 hotel-rank licences. None of it is a hotel identity. Vacation-
ownership resorts (Marriott Vacation Club, Hilton Grand Vacations, Club Wyndham, WorldMark, Westgate, Holiday Inn Club
Vacations, Bluegreen, Diamond / Hilton Vacation Club, Shell Vacations, independent timeshare resorts) are TIMESHARE and
never admitted.

RSW AIRPORT (PHASE 10)
----------------------
Southwest Florida International Airport is 11000 Terminal Access Road, Fort Myers, 33913 (Gateway / unincorporated
Lee County). Its hotels are the Daniels Parkway, Chamberlin Parkway, Treeline Avenue and Gulf Coast Town Center rows
in 33913 and the Daniels Parkway / Market Place Road rows west of I-75 in 33912. A property is one row however many of
"RSW", "Airport", "Gateway", "FGCU", "Estero" and "Fort Myers" its marketing carries.

MILITARY / GOVERNMENT LODGING
-----------------------------
Lee County has no military installation with transient lodging; the military / charitable / patient name list is kept
so a stray record is refused wherever it appears.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/fort_myers_fl.json
  launch_packages/pettripfinder/markets/proposed/fort-myers-fl.json
  launch_packages/pettripfinder/markets/reports/fort_myers_fl_geography_001.json
  launch_packages/pettripfinder/markets/reports/fort_myers_fl_corridor_registry_001.json
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

WORK_ORDER = "PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "fort-myers-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "fort_myers_fl.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "fort-myers-fl.json")
REPORT_OUT = os.path.join(REPORTS, "fort_myers_fl_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "fort_myers_fl_corridor_registry_001.json")
#: Every REGISTERED market's own document: no postal code any of them admits may be admitted here.
REGISTERED_MARKETS_GLOB = os.path.join(PKG, "markets", "*.json")
AS_OF = "2026-10-08"
STATE_CODE = "FL"
STATE_CODES = ("FL",)


def state_for_postal(postal):
    """The state a postal code belongs to: Florida 320-349. A row's own page still decides; this is the check every
    stated state is held against. Neighbouring states are named so a stray out-of-state row is visible."""
    z = (postal or "").strip()[:3]
    if not z.isdigit():
        return ""
    n = int(z)
    if 320 <= n <= 349:
        return "FL"
    if 300 <= n <= 319 or 398 <= n <= 399:
        return "GA"
    if 350 <= n <= 369:
        return "AL"
    return ""


#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description, state)
CORRIDORS = [
    # ---------------------------------------------------------------- CORE (City of Fort Myers, I-75, RSW)
    ("downtown-fort-myers", "Downtown Fort Myers & River District", "Downtown / River District / Edison & Ford "
     "Winter Estates / McGregor Boulevard (north) / Cleveland Avenue (north of Colonial)", "CORE", "fort myers",
     ["33901", "33902"],
     "Downtown Fort Myers and the River District on the Caloosahatchee, the Edison and Ford Winter Estates and "
     "McGregor Boulevard's north end, and Cleveland Avenue (US-41) from the river south toward Colonial Boulevard "
     "(33901), with the downtown PO code (33902). The River District is a reporting OVERLAY decided by street and pin, "
     "never a split code.", "FL"),
    ("colonial-cleveland", "Colonial Boulevard & Cleveland Avenue (US-41)", "Colonial Boulevard / Cleveland Avenue "
     "(US-41) / Metro Parkway / Edison Mall / Bell Tower / College Parkway / Whiskey Creek", "CORE", "fort myers",
     ["33907", "33916", "33919", "33906", "33911"],
     "Midtown Fort Myers: the Colonial Boulevard hotel row, Cleveland Avenue (US-41) from Colonial south to Bell Tower "
     "and University Drive, Edison Mall (33907); the Metro Parkway / Ford Street / Executive Circle cluster at "
     "Colonial and the Dunbar and Palm Beach Boulevard blocks east of downtown (33916); College Parkway, Whiskey "
     "Creek and Cypress Lake (33919); and the PO codes (33906 / 33911). STRONG CORE.", "FL"),
    ("daniels-six-mile", "Daniels Parkway & Six Mile Cypress", "Daniels Parkway (west of I-75) / Market Place Road / "
     "Six Mile Cypress Parkway / Colonial Boulevard (east) / Metro Parkway (south) / San Carlos Park", "CORE",
     "fort myers", ["33912", "33966", "33967"],
     "The Daniels Parkway hotel row west of I-75 -- Market Place Road, Indian Paint Lane, Hilsman Lane -- marketed "
     "'Fort Myers Airport' (33912); Six Mile Cypress Parkway, Colonial Boulevard east of Metro and Metro Parkway "
     "south (33966); San Carlos Park / Three Oaks south toward Estero (33967).", "FL"),
    ("rsw-airport-gateway", "RSW Airport, Gateway & Treeline", "Southwest Florida International Airport (RSW) / "
     "Gateway / Treeline Avenue / Daniels Parkway (east of I-75) / Gulf Coast Town Center / Alico Road / Miromar "
     "Lakes / FGCU", "CORE", "fort myers", ["33913", "33965"],
     "RSW itself (11000 Terminal Access Road, 33913) and its hotel rows east of I-75: Daniels Parkway, Chamberlin "
     "Parkway / Airkraft Court, Interstate Commerce Drive and Gulf Center Drive at Gulf Coast Town Center, Treeline "
     "Avenue, Global Parkway, Corporate Commerce Way, Gateway and Miromar Lakes (33913); and Florida Gulf Coast "
     "University's own code (33965). RSW, Gateway, Treeline and Gulf Coast Town Center are reporting OVERLAYS.",
     "FL"),
    ("east-fort-myers-i75", "East Fort Myers & I-75 (Forum / Palm Beach Boulevard)", "The Forum / Colonial & I-75 / "
     "Palm Beach Boulevard (SR-80) / Tice / Orange River / Fort Myers Shores / Buckingham", "CORE", "fort myers",
     ["33905"],
     "The I-75 interchanges at Colonial Boulevard (the Forum, Champion Ring Road) and Palm Beach Boulevard / SR-80 "
     "(Boatways Road, Old Luckett Road, Orange River Boulevard), and Palm Beach Boulevard's motel row through Tice, "
     "Fort Myers Shores and Buckingham (33905). Buckingham is evaluated here: one code, covered whole.", "FL"),
    # ---------------------------------------------------------------- STRONG CORRIDOR
    ("cape-coral", "Cape Coral", "Cape Coral / Cape Coral Parkway / Del Prado Boulevard / Tarpon Point / Pine Island "
     "Road / Matlacha", "CORRIDOR", "cape coral",
     ["33904", "33909", "33910", "33914", "33915", "33990", "33991", "33993"],
     "The CITY OF CAPE CORAL across the Caloosahatchee: the Cape Coral Parkway / Del Prado / SE 47th Terrace hotel "
     "core (33904), north Cape and Pine Island Road (33909 / 33993), Tarpon Point and the Westin (33914), central Cape "
     "(33990 / 33991) and the PO codes (33910 / 33915). 33993 also carries Matlacha (unincorporated, on Pine Island "
     "Road): covered whole, the Matlacha row keeps its own municipality. A 'Fort Myers' label never makes a Cape "
     "Coral premises a Fort Myers row.", "FL"),
    ("fort-myers-beach", "Fort Myers Beach", "Fort Myers Beach (Estero Island) / Times Square / Estero Boulevard / San "
     "Carlos Island / Summerlin Square (mainland)", "CORRIDOR", "fort myers beach", ["33931", "33932"],
     "The TOWN OF FORT MYERS BEACH on Estero Island (Times Square, the Estero Boulevard resort row) and the mainland "
     "approach whose mailing name is also Fort Myers Beach -- San Carlos Island and Summerlin Square (33931), and the "
     "PO code (33932). Estero Island vs mainland is a reporting OVERLAY (BEACH_ISLAND_EVALUATION). Every beach row is "
     "published only on current first-party proof of operation.", "FL"),
    ("summerlin-iona", "South Fort Myers, Iona & Sanibel Causeway", "Summerlin Road / Iona / McGregor Boulevard "
     "(south) / Punta Rassa / Sanibel Causeway approach / San Carlos Boulevard (north)", "CORRIDOR", "fort myers",
     ["33908"],
     "South Fort Myers between the city and the islands (mailing name Fort Myers): Summerlin Road, Iona, McGregor "
     "Boulevard's south end, Punta Rassa at the Sanibel Causeway, and US-41 south toward San Carlos (33908).", "FL"),
    ("sanibel", "Sanibel Island", "Sanibel / Periwinkle Way / East Gulf Drive / West Gulf Drive / Middle Gulf Drive",
     "CORRIDOR", "sanibel", ["33957"],
     "The CITY OF SANIBEL (33957). Sanibel is its own municipality and never Fort Myers, and never Captiva. Every "
     "island row is published only on current first-party proof of operation.", "FL"),
    ("estero", "Estero & Coconut Point", "Estero / Coconut Point / Corkscrew Road / Hertz Arena / Miromar Outlets / "
     "US-41 (Estero)", "CORRIDOR", "estero", ["33928", "33929"],
     "The VILLAGE OF ESTERO: Coconut Point, Corkscrew Commons and Corkscrew Road at I-75, Hertz Arena and Miromar "
     "Outlets (33928) and the PO code (33929). A 'Fort Myers / Estero' marketing name keeps the Estero municipality.",
     "FL"),
    ("bonita-springs", "Bonita Springs", "Bonita Springs / Bonita Beach Road / Old US-41 / Coconut Road / Bonita Bay "
     "/ I-75 (Bonita Beach Road)", "CORRIDOR", "bonita springs", ["34133", "34134", "34135", "34136"],
     "The CITY OF BONITA SPRINGS, Lee County: Bonita Beach and Hickory Boulevard, Bonita Bay and Coconut Road "
     "(34134), Old US-41, Crown Lake and the I-75 / Bonita Beach Road interchange (34135), and the PO codes (34133 / "
     "34136). Collier County (Naples) begins at Bonita Beach Road: a premises the State licenses in Collier County "
     "with a Bonita Springs mailing label is refused (COUNTY_REFUSALS). 'Naples North' marketing admits nothing and "
     "refuses nothing.", "FL"),
    # ---------------------------------------------------------------- FRINGE (CAREFUL evaluation)
    ("north-fort-myers", "North Fort Myers", "North Fort Myers / North Tamiami Trail (US-41) / North Cleveland Avenue "
     "/ Marinatown / Pine Island Road (east)", "FRINGE", "north fort myers", ["33903", "33917", "33918"],
     "NORTH FORT MYERS, unincorporated Lee County north of the Caloosahatchee: the North Tamiami Trail / North "
     "Cleveland Avenue motel and hotel row and Marinatown at the bridges (33903), the north end (33917) and the PO "
     "code (33918). Admitted at FRINGE after CAREFUL evaluation; never written as Fort Myers.", "FL"),
    ("lehigh-acres-alva", "Lehigh Acres & Alva", "Lehigh Acres / Lee Boulevard / Alva / SR-80 (east)", "FRINGE",
     "lehigh acres", ["33936", "33970", "33971", "33972", "33973", "33974", "33976", "33920"],
     "LEHIGH ACRES, unincorporated east Lee County (33936 / 33970-33976), and ALVA on the Caloosahatchee (33920). "
     "Admitted at FRINGE after CAREFUL evaluation; each row keeps its own municipality.", "FL"),
    ("captiva", "Captiva Island", "Captiva / South Seas / Captiva Drive / Andy Rosse Lane", "FRINGE", "captiva",
     ["33924"],
     "CAPTIVA ISLAND, unincorporated Lee County, reached through Sanibel (33924). Admitted at FRINGE after CAREFUL "
     "evaluation; Captiva is never Sanibel. The boat-access islands sharing 33924 -- Useppa, North (Upper) Captiva, "
     "Safety Harbor -- are refused by name (BOUNDARY_NAME_RX). Every island row is published only on current "
     "first-party proof of operation.", "FL"),
]

OUTSIDE = [
    ("Naples / North Naples / Golden Gate / East Naples -- Collier County", "FL",
     ["34101", "34102", "34103", "34104", "34105", "34106", "34107", "34108", "34109", "34110", "34112", "34113",
      "34114", "34116", "34117", "34119", "34120"],
     "COLLIER COUNTY; FUTURE_STANDALONE naples-fl. Naples, North Naples (Vanderbilt Beach, Pelican Bay), Golden Gate "
     "and East Naples are their own traveller market 20-35 miles south. Refused by postal code."),
    ("Marco Island / Goodland -- Collier County", "FL", ["34145", "34146", "34140"],
     "COLLIER COUNTY; FUTURE_STANDALONE marco-island-fl. Refused by postal code."),
    ("Everglades City / Chokoloskee / Ochopee -- Collier County", "FL", ["34139", "34138", "34141"],
     "COLLIER COUNTY; FUTURE_STANDALONE everglades-city-fl. Refused by postal code."),
    ("Immokalee / Ave Maria -- Collier County interior", "FL", ["34142", "34143"],
     "COLLIER COUNTY interior. Refused after careful evaluation."),
    ("Punta Gorda / Babcock Ranch / Harbour Heights -- Charlotte County", "FL",
     ["33950", "33951", "33955", "33982", "33983"],
     "CHARLOTTE COUNTY; FUTURE_STANDALONE punta-gorda-port-charlotte-fl. Punta Gorda is 25 miles north on I-75 with "
     "its own airport (PGD). Refused by postal code."),
    ("Port Charlotte -- Charlotte County", "FL", ["33948", "33949", "33952", "33953", "33954", "33980", "33981"],
     "CHARLOTTE COUNTY; FUTURE_STANDALONE punta-gorda-port-charlotte-fl. Refused by postal code."),
    ("Englewood / Placida / Rotonda / Boca Grande -- Charlotte County and Gasparilla Island", "FL",
     ["34223", "34224", "33946", "33947", "33921"],
     "CHARLOTTE / SARASOTA COUNTY and GASPARILLA ISLAND; FUTURE_STANDALONE englewood-boca-grande-fl. Boca Grande "
     "(33921) is in Lee County but reached only through Charlotte County across the Gasparilla causeway -- a "
     "destination of its own. Refused by postal code."),
    ("Pine Island (Bokeelia / St. James City / Pineland) and Cabbage Key -- Lee County", "FL",
     ["33922", "33956", "33945"],
     "LEE COUNTY's Pine Island fishing villages and the boat-access Cabbage Key (licensed at 33945). Refused after "
     "careful evaluation: an island trip of its own, 25 miles from downtown, with almost no public hotel lodging."),
    ("LaBelle / Clewiston / Felda / Moore Haven -- Hendry and Glades County", "FL",
     ["33935", "33440", "33930", "33471"],
     "HENDRY / GLADES COUNTY, east of Lee on SR-80. Refused after careful evaluation."),
    ("Sarasota / Bradenton / Venice / North Port / Arcadia", "FL", [],
     "SARASOTA / MANATEE / DESOTO COUNTY; FUTURE_STANDALONE sarasota-fl, bradenton-fl and venice-fl. Refused by PREFIX "
     "(342)."),
    ("Greater Florida and out of state", "--", [],
     "Every other Florida postal code no corridor claims, and every code outside Florida, is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("342", "Sarasota / Bradenton / Venice / North Port / Arcadia", "sarasota-fl"),
]

#: The Fort Myers and Naples sectional centers. A code under one of these that no corridor claims and no OUTSIDE row
#: names is an UNCLAIMED regional code -- refused, and named in the boundary audit so it is visible.
VALLEY_PREFIXES = ("339", "341")

#: The county each admitted code is in, and the REAL municipalities (or unincorporated postal places) its premises are
#: in. The municipality is what a row publishes; "fort myers" is the real municipality only where the code carries it.
#: Where one code spans more than one place the tuple lists every one (principal first), and the row's own stated
#: municipality must be one of them. (The inherited consumer name POSTAL_PARISH is kept: every downstream module reads
#: it.)
POSTAL_PARISH = OrderedDict([
    ("33901", ("Lee", ("fort myers",))),
    ("33902", ("Lee", ("fort myers",))),
    ("33907", ("Lee", ("fort myers",))),
    ("33916", ("Lee", ("fort myers",))),
    ("33919", ("Lee", ("fort myers",))),
    ("33906", ("Lee", ("fort myers",))),
    ("33911", ("Lee", ("fort myers",))),
    ("33912", ("Lee", ("fort myers",))),
    ("33966", ("Lee", ("fort myers",))),
    ("33967", ("Lee", ("fort myers", "san carlos park"))),
    ("33913", ("Lee", ("fort myers", "gateway", "miromar lakes"))),
    ("33965", ("Lee", ("fort myers",))),
    ("33905", ("Lee", ("fort myers", "buckingham", "tice", "fort myers shores", "olga"))),
    ("33904", ("Lee", ("cape coral",))),
    ("33909", ("Lee", ("cape coral",))),
    ("33910", ("Lee", ("cape coral",))),
    ("33914", ("Lee", ("cape coral",))),
    ("33915", ("Lee", ("cape coral",))),
    ("33990", ("Lee", ("cape coral",))),
    ("33991", ("Lee", ("cape coral",))),
    ("33993", ("Lee", ("cape coral", "matlacha"))),
    ("33931", ("Lee", ("fort myers beach",))),
    ("33932", ("Lee", ("fort myers beach",))),
    ("33908", ("Lee", ("fort myers",))),
    ("33957", ("Lee", ("sanibel",))),
    ("33928", ("Lee", ("estero",))),
    ("33929", ("Lee", ("estero",))),
    ("34133", ("Lee", ("bonita springs",))),
    ("34134", ("Lee", ("bonita springs",))),
    ("34135", ("Lee", ("bonita springs",))),
    ("34136", ("Lee", ("bonita springs",))),
    ("33903", ("Lee", ("north fort myers",))),
    ("33917", ("Lee", ("north fort myers",))),
    ("33918", ("Lee", ("north fort myers",))),
    ("33936", ("Lee", ("lehigh acres",))),
    ("33970", ("Lee", ("lehigh acres",))),
    ("33971", ("Lee", ("lehigh acres",))),
    ("33972", ("Lee", ("lehigh acres",))),
    ("33973", ("Lee", ("lehigh acres",))),
    ("33974", ("Lee", ("lehigh acres",))),
    ("33976", ("Lee", ("lehigh acres",))),
    ("33920", ("Lee", ("alva",))),
    ("33924", ("Lee", ("captiva",))),
])
POSTAL_COUNTY = POSTAL_PARISH

#: How each real municipality is written when it is published.
MUNICIPALITY_DISPLAY = {
    "fort myers": "Fort Myers", "san carlos park": "San Carlos Park", "gateway": "Gateway",
    "miromar lakes": "Miromar Lakes", "buckingham": "Buckingham", "tice": "Tice",
    "fort myers shores": "Fort Myers Shores", "olga": "Olga", "cape coral": "Cape Coral", "matlacha": "Matlacha",
    "fort myers beach": "Fort Myers Beach", "sanibel": "Sanibel", "estero": "Estero",
    "bonita springs": "Bonita Springs", "north fort myers": "North Fort Myers", "lehigh acres": "Lehigh Acres",
    "alva": "Alva", "captiva": "Captiva",
}

ADMITTED_PARISHES = {"lee (fort myers: downtown, the river district, colonial boulevard, cleveland avenue, daniels "
                     "parkway, six mile cypress, the forum and palm beach boulevard; rsw and gateway; cape coral; "
                     "fort myers beach; south fort myers / iona; sanibel; estero; bonita springs; north fort myers; "
                     "lehigh acres and alva; captiva -- pine island, cabbage key, useppa and boca grande refused)"}
OBSERVED_PARISHES = OrderedDict([
    ("collier (naples, north naples, golden gate, east naples)", "naples-fl"),
    ("collier (marco island, goodland)", "marco-island-fl"),
    ("collier (everglades city, chokoloskee, immokalee, ave maria)", "everglades-city-fl"),
    ("charlotte (punta gorda, port charlotte, babcock ranch)", "punta-gorda-port-charlotte-fl"),
    ("charlotte / gasparilla island (englewood, placida, rotonda, boca grande)", "englewood-boca-grande-fl"),
    ("lee (pine island: bokeelia, st. james city, pineland; cabbage key)", "(none -- refused after careful evaluation)"),
    ("hendry / glades (labelle, clewiston, moore haven)", "(none -- refused after careful evaluation)"),
    ("sarasota / manatee / desoto (sarasota, bradenton, venice, north port, arcadia)",
     "sarasota-fl / bradenton-fl / venice-fl"),
])
#: Inherited consumer name (the cross-county audit slot).
OBSERVED_COUNTIES = OBSERVED_PARISHES
ADMITTED_COUNTIES = ADMITTED_PARISHES

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("lee", OrderedDict([
        ("ruling", "ADMITTED, MUNICIPALITIES PRESERVED. Fort Myers, Cape Coral, Fort Myers Beach, Sanibel, Estero and "
                   "Bonita Springs are admitted with Gateway / RSW, South Fort Myers / Iona and East Fort Myers; North "
                   "Fort Myers, Lehigh Acres / Alva and Captiva at FRINGE. Pine Island (Bokeelia, St. James City, "
                   "Pineland), Cabbage Key, Useppa, North Captiva and Boca Grande (Gasparilla Island) are refused."),
    ])),
    ("collier", OrderedDict([
        ("ruling", "REFUSED WHOLE. Naples, North Naples, Marco Island, Everglades City, Immokalee and Ave Maria are "
                   "future standalone markets. A premises the State licenses in Collier County is refused even where "
                   "its mailing label reads Bonita Springs (34134 north of the county line) -- COUNTY_REFUSALS."),
    ])),
    ("charlotte", OrderedDict([
        ("ruling", "REFUSED WHOLE. Punta Gorda, Port Charlotte, Englewood, Placida and Rotonda are future standalone "
                   "markets; Boca Grande (Lee County, Gasparilla Island) is refused with them."),
    ])),
    ("hendry / glades / sarasota / manatee / desoto", OrderedDict([
        ("ruling", "REFUSED. LaBelle, Clewiston, Sarasota, Bradenton, Venice, North Port and Arcadia are not absorbed."),
    ])),
])

#: A premises whose STATE LICENCE names one of these counties is refused whatever its postal code's corridor: the
#: Collier County land north of Bonita Beach Road shares 34134 with the City of Bonita Springs.
COUNTY_REFUSALS = OrderedDict([
    ("collier", "a premises the State of Florida licenses in COLLIER COUNTY (Naples) -- FUTURE_STANDALONE naples-fl; "
                "a Bonita Springs mailing label does not move the county line"),
    ("charlotte", "a premises the State of Florida licenses in CHARLOTTE COUNTY -- FUTURE_STANDALONE "
                  "punta-gorda-port-charlotte-fl"),
    ("hendry", "a premises the State of Florida licenses in HENDRY COUNTY -- refused"),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / patient / member
#: only). A normalised-name substring match; the census row keeps its reason.
NONPUBLIC_NAMES = {
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- MILITARY_RESTRICTED",
    "navy lodge": "Navy Lodge on-base lodging -- MILITARY_RESTRICTED",
    "navy gateway inns": "Navy Gateway Inns & Suites on-base lodging -- MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "hope lodge": "American Cancer Society Hope Lodge -- patient lodging, not public lodging",
    "hope hospice": "hospice -- not public lodging",
    "family housing": "patient-family housing -- not public lodging",
    "patient housing": "patient housing -- not public lodging",
    "rescue mission": "rescue mission shelter -- not public lodging",
    "homeless": "shelter -- not public lodging",
    "salvation army": "Salvation Army shelter -- not public lodging",
    "youth shelter": "youth shelter -- not public lodging",
    "bachelor quarters": "military bachelor quarters -- MILITARY_RESTRICTED",
}

#: Military postal codes inside the admitted partition. None in Lee County.
MILITARY_POSTAL_CODES = OrderedDict()

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-fort-myers", "Fort Myers", "Downtown / River District", 26.6420, -81.8650, 2500, True),
    ("colonial-cleveland", "Fort Myers", "Colonial Boulevard / Cleveland Avenue / Metro Parkway", 26.5900, -81.8650,
     5000, True),
    ("daniels-six-mile", "Fort Myers", "Daniels Parkway / Six Mile Cypress / San Carlos Park", 26.5450, -81.8300,
     6000, True),
    ("rsw-airport-gateway", "Fort Myers", "RSW / Gateway / Treeline / Gulf Coast Town Center", 26.5350, -81.7600,
     7000, True),
    ("east-fort-myers-i75", "Fort Myers", "Forum / Palm Beach Boulevard / Tice / Buckingham", 26.6500, -81.7800,
     7000, True),
    ("cape-coral", "Cape Coral", "Cape Coral", 26.6100, -81.9600, 10000, True),
    ("fort-myers-beach", "Fort Myers Beach", "Fort Myers Beach / Estero Island / San Carlos Island", 26.4400,
     -81.9300, 6000, True),
    ("summerlin-iona", "Fort Myers", "Summerlin / Iona / Punta Rassa", 26.5000, -81.9300, 5000, True),
    ("sanibel", "Sanibel", "Sanibel Island", 26.4400, -82.0700, 9000, True),
    ("estero", "Estero", "Estero / Coconut Point", 26.4300, -81.8000, 5000, True),
    ("bonita-springs", "Bonita Springs", "Bonita Springs / Bonita Beach", 26.3500, -81.8000, 7000, True),
    ("north-fort-myers", "North Fort Myers", "North Fort Myers", 26.6900, -81.8800, 6000, True),
    ("lehigh-acres-alva", "Lehigh Acres", "Lehigh Acres / Alva", 26.6200, -81.6400, 9000, True),
    ("captiva", "Captiva", "Captiva Island", 26.5250, -82.1850, 4000, True),
    ("obs-naples", "Naples", "Naples / North Naples -- OBSERVATION ONLY", 26.2000, -81.7900, 15000, False),
    ("obs-marco-island", "Marco Island", "Marco Island / Goodland -- OBSERVATION ONLY", 25.9400, -81.7100, 9000,
     False),
    ("obs-punta-gorda", "Punta Gorda", "Punta Gorda / Port Charlotte -- OBSERVATION ONLY", 26.9600, -82.0700, 15000,
     False),
    ("obs-pine-island", "Bokeelia", "Pine Island / Cabbage Key / Useppa -- OBSERVATION ONLY", 26.6200, -82.1300,
     12000, False),
    ("obs-boca-grande", "Boca Grande", "Boca Grande / Placida / Englewood -- OBSERVATION ONLY", 26.8200, -82.2800,
     12000, False),
]

#: The observation box. It reaches south past Naples to Marco Island and Everglades City, north past Punta Gorda and
#: Port Charlotte, west over Boca Grande, Pine Island and Captiva and east to LaBelle, so the census counts what it
#: refuses. Florida beyond it (Sarasota, Bradenton, Venice, the Keys) is MEASURED by the OpenStreetMap lane over the
#: whole Florida extract for the boundary audit only.
BOUNDS = {"min_lat": 25.80, "max_lat": 27.10, "min_lng": -82.40, "max_lng": -81.35}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
#: Listed most-specific first; the nearest anchor within its radius wins.
COVERAGE_AREAS = [
    ("RSW Airport", 26.5362, -81.7552, 1.6),
    ("River District", 26.6440, -81.8690, 0.8),
    ("Times Square (Fort Myers Beach)", 26.4520, -81.9500, 0.6),
    ("Gulf Coast Town Center", 26.4880, -81.7860, 1.2),
    ("Coconut Point", 26.4050, -81.8080, 1.5),
    ("Bell Tower", 26.5520, -81.8710, 1.0),
    ("Treeline / Gateway", 26.5550, -81.7800, 3.0),
    ("Downtown Fort Myers", 26.6400, -81.8650, 1.6),
    ("Colonial Boulevard", 26.5980, -81.8500, 3.0),
    ("Daniels Parkway", 26.5480, -81.8300, 3.0),
    ("Estero Island (Fort Myers Beach)", 26.4300, -81.9150, 5.5),
    ("San Carlos Island / Summerlin Square", 26.4800, -81.9550, 2.2),
    ("Iona / Punta Rassa", 26.5050, -81.9600, 3.5),
    ("Sanibel", 26.4400, -82.0700, 8.0),
    ("Captiva", 26.5250, -82.1850, 3.5),
    ("Cape Coral", 26.6100, -81.9600, 9.0),
    ("Estero", 26.4300, -81.8000, 4.5),
    ("Bonita Springs", 26.3500, -81.8000, 6.0),
    ("North Fort Myers", 26.6900, -81.8800, 5.5),
    ("East Fort Myers / Forum", 26.6400, -81.7900, 6.0),
    ("Lehigh Acres", 26.6200, -81.6400, 9.0),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin). Reporting only.
STREET_OVERLAYS = [
    ("Estero Island (Fort Myers Beach)", re.compile(
        r"\b(estero (blvd|boulevard)|crescent (st|street)|old san carlos (blvd|boulevard)|times square|"
        r"(first|1st|third|3rd|fifth|5th) (st|street)|mango (st|street)|virginia (ave|avenue)|"
        r"lenell|connecticut (st|street)|bay (rd|road))\b(?=.*\b3393[12]\b)", re.I)),
    ("San Carlos Island / Summerlin Square", re.compile(
        r"\b(summerlin square|summerlin (dr|drive|rd|road)|san carlos (blvd|boulevard)|main (st|street))\b"
        r"(?=.*\b33931\b)", re.I)),
    ("RSW Airport", re.compile(r"\b(terminal access (rd|road)|airkraft|chamberlin (pkwy|parkway)|"
                               r"interstate commerce|intercom (dr|drive))\b(?=.*\b33913\b)", re.I)),
    ("Gulf Coast Town Center", re.compile(r"\b(gulf center (dr|drive)|university plaza (dr|drive))\b"
                                          r"(?=.*\b33913\b)", re.I)),
    ("Treeline / Gateway", re.compile(r"\b(treeline (ave|avenue)|global (pkwy|parkway)|corporate commerce|"
                                      r"gateway (blvd|boulevard)|colonial (ct|court))\b(?=.*\b33913\b)", re.I)),
    ("Coconut Point", re.compile(r"\b(via villagio|via coconut point|coconut (rd|road)|coconut point)\b", re.I)),
    ("Bell Tower", re.compile(r"\b(bell tower (dr|drive))\b", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-fort-myers": "Downtown Fort Myers",
    "colonial-cleveland": "Colonial Boulevard",
    "daniels-six-mile": "Daniels Parkway",
    "rsw-airport-gateway": "Treeline / Gateway",
    "east-fort-myers-i75": "East Fort Myers / Forum",
    "cape-coral": "Cape Coral",
    "fort-myers-beach": "Estero Island (Fort Myers Beach)",
    "summerlin-iona": "Iona / Punta Rassa",
    "sanibel": "Sanibel",
    "estero": "Estero",
    "bonita-springs": "Bonita Springs",
    "north-fort-myers": "North Fort Myers",
    "lehigh-acres-alva": "Lehigh Acres",
    "captiva": "Captiva",
}

#: The order's CORE / STRONG / CAREFUL / KEEP-SEPARATE evaluation list, each classified.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Fort Myers", "ADMITTED (CORE, downtown-fort-myers, 33901 / 33902)."),
    ("River District", "ADMITTED (CORE, downtown-fort-myers, 33901) -- overlay."),
    ("Colonial Boulevard", "ADMITTED (CORE, colonial-cleveland 33907 / 33916; daniels-six-mile 33966 for the "
                           "Colonial rows east of Metro Parkway)."),
    ("Cleveland Avenue / US-41", "ADMITTED (CORE, colonial-cleveland 33907; downtown-fort-myers 33901 north of "
                                 "Colonial)."),
    ("Daniels Parkway", "ADMITTED (CORE, daniels-six-mile 33912 west of I-75; rsw-airport-gateway 33913 east of "
                        "I-75)."),
    ("Six Mile Cypress", "ADMITTED (CORE, daniels-six-mile 33966 / 33912)."),
    ("I-75 Fort Myers corridors", "ADMITTED (CORE, east-fort-myers-i75 33905 at Colonial / the Forum and SR-80; "
                                  "daniels-six-mile and rsw-airport-gateway at Daniels and Alico)."),
    ("Gateway", "ADMITTED (CORE, rsw-airport-gateway, 33913) -- overlay; municipality Fort Myers / Gateway."),
    ("RSW / Southwest Florida International Airport", "ADMITTED (CORE, rsw-airport-gateway, 33913) -- overlay; "
                                                       "RSW_AIRPORT_EVALUATION."),
    ("Cape Coral", "ADMITTED (STRONG CORRIDOR, cape-coral, 33904 / 33909 / 33910 / 33914 / 33915 / 33990 / 33991 / "
                   "33993). Municipality CAPE CORAL, never Fort Myers."),
    ("Fort Myers Beach", "ADMITTED (STRONG CORRIDOR, fort-myers-beach, 33931 / 33932). Municipality FORT MYERS BEACH; "
                         "Estero Island and the mainland approach reported separately; current operation required."),
    ("Estero", "ADMITTED (STRONG CORRIDOR, estero, 33928 / 33929). Municipality ESTERO."),
    ("Bonita Springs", "ADMITTED (STRONG CORRIDOR, bonita-springs, 34133-34136). Municipality BONITA SPRINGS; "
                       "Collier-licensed premises refused."),
    ("Sanibel", "ADMITTED (STRONG CORRIDOR, sanibel, 33957). Municipality SANIBEL; current operation required."),
    ("South Fort Myers / Iona / Summerlin", "ADMITTED (STRONG CORRIDOR, summerlin-iona, 33908). Municipality Fort "
                                            "Myers (mailing)."),
    ("North Fort Myers", "ADMITTED (FRINGE, north-fort-myers, 33903 / 33917 / 33918). CAREFUL: north of the river, "
                         "never written as Fort Myers."),
    ("Lehigh Acres", "ADMITTED (FRINGE, lehigh-acres-alva, 33936 / 33970-33976). CAREFUL."),
    ("Captiva", "ADMITTED (FRINGE, captiva, 33924). CAREFUL: never Sanibel; the boat-access islands refused by name; "
                "current operation required."),
    ("Miromar Lakes", "ADMITTED (CORE, rsw-airport-gateway, 33913) -- overlay; Miromar Outlets is Estero 33928."),
    ("Alva", "ADMITTED (FRINGE, lehigh-acres-alva, 33920). CAREFUL: no hotel-rank licence at authoring time."),
    ("Buckingham", "ADMITTED (CORE, east-fort-myers-i75, 33905 -- covered whole). CAREFUL."),
    ("Naples", "OUTSIDE -- FUTURE_STANDALONE naples-fl; refused by postal code and by Collier County licence. KEEP "
               "SEPARATE."),
    ("Marco Island", "OUTSIDE -- FUTURE_STANDALONE marco-island-fl; refused by postal code. KEEP SEPARATE."),
    ("Punta Gorda", "OUTSIDE -- FUTURE_STANDALONE punta-gorda-port-charlotte-fl; refused by postal code. KEEP "
                    "SEPARATE."),
    ("Port Charlotte", "OUTSIDE -- FUTURE_STANDALONE punta-gorda-port-charlotte-fl; refused by postal code. KEEP "
                       "SEPARATE."),
    ("Sarasota", "OUTSIDE -- FUTURE_STANDALONE sarasota-fl; refused by prefix 342. KEEP SEPARATE."),
    ("Bradenton", "OUTSIDE -- FUTURE_STANDALONE bradenton-fl; refused by prefix 342. KEEP SEPARATE."),
    ("Venice", "OUTSIDE -- FUTURE_STANDALONE venice-fl; refused by prefix 342. KEEP SEPARATE."),
    ("Everglades City", "OUTSIDE -- FUTURE_STANDALONE everglades-city-fl; refused by postal code. KEEP SEPARATE."),
    ("Pine Island / Matlacha", "Pine Island (Bokeelia 33922, St. James City 33956, Pineland 33945) OUTSIDE after "
                               "careful evaluation; Matlacha shares 33993 with Cape Coral and is covered whole, keeping "
                               "its own municipality."),
    ("Boca Grande", "OUTSIDE -- Gasparilla Island, reached through Charlotte County (englewood-boca-grande-fl)."),
])

#: The airport ruling, stated once (Phase 10).
RSW_AIRPORT_EVALUATION = OrderedDict([
    ("airport_terminal", "Southwest Florida International Airport (RSW) is 11000 Terminal Access Road, Fort Myers, "
                         "FL 33913 -- unincorporated Lee County at Gateway. No hotel stands inside the terminal."),
    ("airport_hotel_rows", "RSW's hotels are the Daniels Parkway / Chamberlin Parkway / Airkraft Court, Interstate "
                           "Commerce Drive, Gulf Center Drive, Treeline Avenue, Global Parkway and Corporate Commerce "
                           "Way rows east of I-75 (33913, rsw-airport-gateway) and the Daniels Parkway / Market Place "
                           "Road rows west of I-75 (33912, daniels-six-mile)."),
    ("airport_marketed_elsewhere", "'Fort Myers Airport' or 'RSW' hotels in Estero (33928) or on Colonial Boulevard "
                                   "are placed by their own code and keep their own municipality."),
    ("one_premises_one_row", "A property is one row however many of 'RSW', 'Airport', 'Gateway', 'FGCU', 'Estero' "
                             "and 'Fort Myers' its marketing carries; identity is its own street address, phone and "
                             "brand property code."),
])

#: The beach / island ruling (Phases 5-7).
BEACH_ISLAND_EVALUATION = OrderedDict([
    ("fort_myers_beach", "The Town of Fort Myers Beach is Estero Island (33931). The mainland approach -- San Carlos "
                         "Island, Summerlin Square -- shares 33931 and the mailing name Fort Myers Beach; its rows "
                         "publish as Fort Myers Beach and report under the 'San Carlos Island / Summerlin Square' "
                         "overlay, never as island beach resorts."),
    ("sanibel", "The City of Sanibel (33957) is its own municipality: never Fort Myers, never Captiva."),
    ("captiva", "Captiva (33924) is its own unincorporated island: never Sanibel. Useppa, North / Upper Captiva and "
                "Safety Harbor share 33924 and are boat-access islands of private clubs and vacation homes, refused "
                "by name."),
    ("current_operation", "Hurricane Ian (2022), Helene and Milton (2024) destroyed or closed much of the beach and "
                          "island lodging. A beach / island row publishes only on its own CURRENT first-party page "
                          "proving an operating public lodging business; a historic OTA page, an old tourism or "
                          "competitor listing, a cached brand page, a pre-hurricane identity or old policy evidence "
                          "never publishes one."),
    ("resort_campus", "A resort campus (one operator, many buildings, one booking engine) is never one identity: each "
                      "row is the exact hotel premises the public operator sells as a hotel, and a pet policy binds "
                      "only to that premises (CONDO_HOTEL_RULE)."),
])

#: The market ruling.
FORT_MYERS_RULING = OrderedDict([
    ("classification", "The Fort Myers / Cape Coral market is admitted as Lee County's traveller lodging -- Downtown / "
                       "River District, Colonial Boulevard & Cleveland Avenue, Daniels Parkway & Six Mile Cypress, RSW / "
                       "Gateway and East Fort Myers / I-75 CORE; Cape Coral, Fort Myers Beach, South Fort Myers / Iona, "
                       "Sanibel, Estero and Bonita Springs STRONG CORRIDOR; North Fort Myers, Lehigh Acres / Alva and "
                       "Captiva FRINGE. Naples, Marco Island, Everglades City, Punta Gorda, Port Charlotte, Englewood / "
                       "Boca Grande, Pine Island, LaBelle, Sarasota, Bradenton and Venice are OUTSIDE."),
    ("a_marketing_phrase_admits_nothing", "'Fort Myers', 'Fort Myers Area', 'Southwest Florida', 'Beaches of Fort "
                                          "Myers & Sanibel', 'RSW Airport', 'Naples-Fort Myers' and 'Naples North' are "
                                          "marketing. The property's own postal code decides membership and its "
                                          "municipality."),
    ("actual_location", "Decided by the property's own postal code on its own page; the county and the municipality "
                        "by that code; a State licence naming Collier, Charlotte or Hendry County refuses."),
    ("drive_market_relationship", "Downtown, the US-41 / Colonial / Daniels hotel rows, the airport, Cape Coral, the "
                                  "beach and the islands, Estero and Bonita Springs are where Fort Myers travellers "
                                  "sleep; Naples, Marco Island, Punta Gorda and Sarasota are trips of their own."),
    ("traveller_intent", "Leisure (Fort Myers Beach, Sanibel and Captiva, the Edison and Ford Winter Estates), spring "
                         "training (JetBlue Park, Hammond Stadium), RSW airport, Florida Gulf Coast University, medical "
                         "(Lee Health, Gulf Coast Medical Center, Golisano Children's), Hertz Arena and Coconut Point "
                         "demand is this market's intent."),
    ("metro_continuity", "Continuous development runs along US-41 and I-75 from North Fort Myers through Fort Myers, "
                         "Estero and Bonita Springs to the Collier County line at Bonita Beach Road; this registry "
                         "stops there."),
    ("corridor_support", "Every admitted edge code is in a named corridor so its count is visible and a founder can "
                         "move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE naples-fl, marco-island-fl, everglades-city-fl, "
                      "punta-gorda-port-charlotte-fl, englewood-boca-grande-fl, sarasota-fl, bradenton-fl and "
                      "venice-fl."),
])

STRUCTURE_TEST = OrderedDict([
    ("A. Is Fort Myers / Cape Coral one market?",
     "ONE market, fort-myers-fl, covering Lee County's traveller lodging from North Fort Myers to Bonita Springs and "
     "from Lehigh Acres to Sanibel and Captiva -- one commercial airport (RSW), one US-41 / I-75 road system."),
    ("B. Municipalities are NOT flattened",
     "Every corridor names its municipality, every admitted code carries its county and real municipalities, and "
     "every row keeps its own. Cape Coral, Fort Myers Beach, Sanibel, Captiva, Estero, Bonita Springs, North Fort "
     "Myers and Lehigh Acres are never written as Fort Myers."),
    ("C. RSW airport", "Fort Myers / Gateway (33913); 'Airport' hotels elsewhere are placed by their own code "
                       "(RSW_AIRPORT_EVALUATION)."),
    ("D. Beaches and islands", "Their own identities, current operation required (BEACH_ISLAND_EVALUATION)."),
    ("E. River District / Gateway / Treeline / Gulf Coast Town Center / Coconut Point / Times Square",
     "Overlays of their corridor, never split codes."),
    ("F. Naples / North Naples / Marco Island", "OUTSIDE -- FUTURE_STANDALONE naples-fl / marco-island-fl."),
    ("G. Punta Gorda / Port Charlotte", "OUTSIDE -- FUTURE_STANDALONE punta-gorda-port-charlotte-fl."),
    ("H. Sarasota / Bradenton / Venice", "OUTSIDE -- FUTURE_STANDALONE sarasota-fl / bradenton-fl / venice-fl."),
    ("I. Pine Island / Boca Grande / Cabbage Key / Useppa", "OUTSIDE -- not absorbed."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel / inn / lodge operation (front desk)."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP). A unit designator ('Ste', "
     "'Unit', '#', 'Apt', 'PH') in a registry address means the record is a UNIT INSIDE a building or campus, which "
     "is never a hotel identity."),
    ("beach_inn_rule",
     "A beach inn, island cottage court or historic inn is admitted however small when its own site proves a PUBLIC "
     "LODGING OPERATION (rooms sold nightly to the public under one establishment name, with its own booking and an "
     "on-site operation), an OFFICIAL PROPERTY IDENTITY and an EXACT PREMISES. A condominium complex whose units are "
     "rented by a property-management company, a private cottage, a beach house or a vacation-dwelling licence is "
     "never an inn. Ambiguous qualification is HELD, never admitted to publication."),
    ("hotel_vs_residence_boundary",
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. This market's "
     "specific exposures: Fort Myers Beach's and Sanibel's condominium resorts sold by rental programmes (DBPR CNDO), "
     "Bonita Beach and Estero Boulevard condo towers, island vacation-rental managers (Royal Shell, Sanibel & Captiva "
     "Island Vacation Rentals, VIP, Vacasa, Evolve), Cape Coral's canal-home vacation rentals (~2,600 DWEL "
     "licences), serviced-apartment and corporate-housing operators, FGCU student housing and the Airbnb / Vrbo "
     "inventory."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort (Marriott Vacation Club, Hilton Grand Vacations, Club Wyndham, "
     "WorldMark, Westgate, Holiday Inn Club Vacations, Bluegreen, Diamond / Hilton Vacation Club, Shell Vacations, "
     "Lehigh Resort Club, independent ownership resorts) is TIMESHARE and is never admitted to hotel accounting, even "
     "when its brand lists it beside its hotels, even when it sells a nightly rate, and even when a pet-policy page "
     "exists."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared amenities or "
     "shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never published as one. A hotel "
     "and its residences on one campus are distinct premises. A resort-wide or management-company policy never binds "
     "to a building without exact binding."),
    ("extended_stay",
     "Extended-stay hotels are hotels and are admitted on their own pages; an 'apartment hotel' or 'aparthotel' is "
     "admitted only as a public hotel operation at an exact premises, never as a residential building that rents "
     "furnished units."),
    ("patient_and_military_lodging",
     "Patient-family housing (the Ronald McDonald House, Hope Lodge), charitable family lodging (Fisher House), "
     "shelters and on-base military lodging are never public hotels and are never admitted."),
])

#: Phase 5 -- the operating-status vocabulary every beach / island row is classified into (decided per row from the
#: property's OWN current page, never from this module).
OPERATING_STATUS_RULE = OrderedDict([
    ("vocabulary", ["CURRENTLY_OPEN", "REOPENED", "PARTIALLY_OPEN", "SEASONAL", "TEMPORARILY_CLOSED",
                    "CLOSED_FOR_REBUILD", "PERMANENTLY_CLOSED", "DEMOLISHED", "REBRANDED", "PREOPENING", "UNKNOWN"]),
    ("publishes", "Only a row whose own current first-party page proves an operating public lodging business "
                  "(CURRENTLY_OPEN, REOPENED, PARTIALLY_OPEN for the open premises, SEASONAL in season or out)."),
    ("never_publishes", "TEMPORARILY_CLOSED, CLOSED_FOR_REBUILD, PERMANENTLY_CLOSED, DEMOLISHED, PREOPENING and "
                        "UNKNOWN. A REBRANDED row publishes only under its current operator's name on its current page."),
    ("evidence", "A historic OTA page, an old tourism or competitor listing, a cached brand page, a pre-hurricane "
                 "identity, a DBPR licence or old policy evidence never proves current operation."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("33901", ["Downtown Fort Myers", "River District", "McGregor Boulevard (north)", "Cleveland Avenue (north)"]),
    ("33913", ["RSW Airport", "Gateway", "Treeline Avenue", "Gulf Coast Town Center", "Miromar Lakes"]),
    ("33931", ["Estero Island (Town of Fort Myers Beach)", "San Carlos Island", "Summerlin Square (mainland)"]),
    ("33905", ["The Forum", "Palm Beach Boulevard", "Tice", "Fort Myers Shores", "Buckingham"]),
    ("33993", ["Cape Coral (north-west)", "Matlacha"]),
    ("33924", ["Captiva", "Useppa / North Captiva / Safety Harbor (refused by name)"]),
    ("34134", ["Bonita Springs (Lee County)", "Collier County north of the county line (refused by licence county)"]),
])

FUTURE_MARKETS = OrderedDict([
    ("naples-fl", "Naples, North Naples, Golden Gate and East Naples -- Collier County, 20-35 miles south."),
    ("marco-island-fl", "Marco Island and Goodland -- Collier County."),
    ("everglades-city-fl", "Everglades City, Chokoloskee and Ochopee -- the Everglades' Gulf gateway."),
    ("punta-gorda-port-charlotte-fl", "Punta Gorda and Port Charlotte -- Charlotte County, 25 miles north on I-75."),
    ("englewood-boca-grande-fl", "Englewood, Placida, Rotonda and Boca Grande on Gasparilla Island."),
    ("sarasota-fl", "Sarasota, Siesta Key and Longboat Key -- 75 miles north."),
    ("bradenton-fl", "Bradenton and Anna Maria Island -- 90 miles north."),
    ("venice-fl", "Venice and North Port -- 55 miles north."),
])

#: Markets that are ALREADY LIVE. Six Florida markets are live; none shares a Lee / Collier / Charlotte postal code.
#: Exposures are shared NAMES and chain flags: a bare chain name ("Hampton Inn & Suites") published here would take a
#: live Florida market's identity, and Orlando, Tampa and Miami each publish Fort Myers-adjacent brand names.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("salt-lake-city-ut", "Salt Lake City, live as production market #45 (deploy 6ac6f3d213d002249f9c3e67) -- the "
                          "CURRENT LIVE market at this order's authoring time. No shared state or code."),
    ("tampa-fl", "Tampa Bay, live -- the nearest live Florida market (Sarasota and Bradenton are outside both). No "
                 "shared postal code."),
    ("orlando-fl", "Orlando, live -- no shared postal code."),
    ("miami-fl", "Miami, live -- across the Everglades on I-75 (Alligator Alley); no shared postal code."),
    ("fort-lauderdale-fl", "Fort Lauderdale, live -- no shared postal code."),
    ("west-palm-beach-fl", "West Palm Beach, live -- no shared postal code."),
    ("jacksonville-fl", "Jacksonville, live -- no shared postal code."),
])

#: A shared postal code whose OTHER place is refused. None by municipality name: the boat-access islands that share
#: Captiva's 33924 are refused by name (BOUNDARY_NAME_RX), and Collier County land in 34134 by licence county.
MUNICIPALITY_REFUSALS = [
    ("33924", "useppa", "Useppa Island shares 33924 with Captiva; a boat-access private-club island -- refused"),
    ("33924", "north captiva", "North (Upper) Captiva shares 33924 with Captiva; a boat-access island of vacation "
                               "homes -- refused"),
    ("33924", "upper captiva", "Upper (North) Captiva shares 33924 with Captiva; a boat-access island of vacation "
                               "homes -- refused"),
]
#: Boundary wording on a row's own name or street: a Captiva-labelled boat-access island, or a premises on Pine
#: Island / Gasparilla Island that a listing labels with an admitted city, is refused like its place.
BOUNDARY_NAME_RX = re.compile(r"\b(useppa|cabbage key|north captiva|upper captiva|safety harbor club|"
                              r"pine island (rd|road) (nw|w)|stringfellow (rd|road)|bokeelia|st\.? james city|"
                              r"pineland|gasparilla inn|boca grande)\b", re.I)

MUNICIPALITY_SPELLINGS = {
    "fort myers,": "fort myers", "ft myers": "fort myers", "ft. myers": "fort myers", "ft myers,": "fort myers",
    "fort meyers": "fort myers", "ft meyers": "fort myers", "fort myers fl": "fort myers",
    "fort myers, fl": "fort myers", "fort myers beach,": "fort myers beach", "ft myers beach": "fort myers beach",
    "ft myers bch": "fort myers beach", "ft. myers beach": "fort myers beach", "fort myers bch": "fort myers beach",
    "ft mye beach": "fort myers beach", "fmb": "fort myers beach", "cape coral,": "cape coral",
    "cape coral fl": "cape coral", "cape coral, fl": "cape coral", "n fort myers": "north fort myers",
    "n ft myers": "north fort myers", "n. fort myers": "north fort myers", "n. ft. myers": "north fort myers",
    "n ft. myers": "north fort myers", "north ft myers": "north fort myers", "north ft. myers": "north fort myers",
    "north fort myers,": "north fort myers", "sanibel island": "sanibel", "sanibel,": "sanibel",
    "captiva island": "captiva", "captiva isl": "captiva", "captiva,": "captiva", "estero,": "estero",
    "bonita spgs": "bonita springs", "bonita springs,": "bonita springs", "bonita beach": "bonita springs",
    "bonita": "bonita springs", "lehigh": "lehigh acres", "lehigh acres,": "lehigh acres", "alva,": "alva",
    "miromar lakes,": "miromar lakes", "gateway,": "gateway", "matlacha,": "matlacha",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("33901", "Downtown Fort Myers / River District."),
    ("33907", "Cleveland Avenue (US-41) / Colonial Boulevard / Bell Tower -- the midtown hotel row."),
    ("33912", "Daniels Parkway west of I-75 -- the 'Fort Myers Airport' row on Market Place Road."),
    ("33913", "RSW itself, Gateway, Treeline Avenue, Gulf Coast Town Center and Miromar Lakes."),
    ("33903", "North Fort Myers -- never Fort Myers."),
    ("33931", "Fort Myers Beach: Estero Island and the mainland approach (San Carlos Island, Summerlin Square)."),
    ("33957", "Sanibel -- never Fort Myers, never Captiva."),
    ("33924", "Captiva -- and Useppa / North Captiva, refused by name."),
    ("33928", "Estero / Coconut Point -- never Fort Myers."),
    ("34134", "Bonita Springs -- and Collier County north of Bonita Beach Road, refused by licence county."),
    ("34108", "North Naples -- refused (naples-fl)."),
    ("33950", "Punta Gorda -- refused (punta-gorda-port-charlotte-fl)."),
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
            if z not in POSTAL_PARISH:
                raise SystemExit("admitted postal code %s carries no county / municipality" % z)
            seen_zip[z] = slug
        corridors.append(OrderedDict([
            ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
            ("market_id", MARKET_ID),
            ("name", name),
            ("slug", slug),
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Fort Myers" % name),
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
    unused_county = sorted(set(POSTAL_PARISH) - set(seen_zip))
    if unused_county:
        raise SystemExit("county table names codes no corridor claims: %s" % unused_county)
    outside_zips = {z for _m, _s, zs, _w in OUTSIDE for z in zs}
    overlap = outside_zips & set(seen_zip)
    if overlap:
        raise SystemExit("postal codes both admitted and refused: %s" % sorted(overlap))
    prefix_overlap = [z for z in seen_zip if any(z.startswith(p) for p, _n, _f in OUTSIDE_PREFIXES)]
    if prefix_overlap:
        raise SystemExit("admitted postal codes under a refused prefix: %s" % sorted(prefix_overlap))
    stray = [z for z in seen_zip if not z.startswith(VALLEY_PREFIXES)]
    if stray:
        raise SystemExit("admitted postal codes outside the Fort Myers / Naples prefixes: %s" % stray)
    for rz, _m, _w in MUNICIPALITY_REFUSALS:
        if rz not in seen_zip:
            raise SystemExit("municipality refusal on a code no corridor claims: %s" % rz)
    non_lee = sorted(z for z in seen_zip if POSTAL_PARISH[z][0] != "Lee")
    if non_lee:
        raise SystemExit("admitted postal codes outside Lee County: %s" % non_lee)
    registered_codes = _registered_market_postal_codes()
    live_overlap = sorted(z for z in seen_zip if z in registered_codes)
    if live_overlap:
        raise SystemExit("admitted postal codes a REGISTERED market already admits: %s" % [
            (z, registered_codes[z]) for z in live_overlap])
    military_unclaimed = [z for z in MILITARY_POSTAL_CODES if z not in seen_zip]
    if military_unclaimed:
        raise SystemExit("military postal codes claimed by no corridor: %s" % military_unclaimed)

    cells = []
    for suffix, muni, label, lat, lng, radius, admitting in CELLS:
        cells.append(OrderedDict([
            ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
            ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
            ("state_code", STATE_CODE),
            ("admitting", admitting),
        ]))
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Fort Myers / Cape Coral / Southwest Florida, Florida -- downtown and the River District, "
                        "Colonial Boulevard and Cleveland Avenue, Daniels Parkway, RSW and Gateway, Cape Coral, Fort "
                        "Myers Beach, Sanibel and Captiva, Estero and Bonita Springs lodging market (PetTripFinder "
                        "discovery scope)"),
        ("state", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("country", "US"),
        ("market_center", {"lat": 26.61, "lng": -81.85}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past Naples to Marco Island and Everglades "
             "City, north past Punta Gorda and Port Charlotte, west over Boca Grande, Pine Island and Captiva and "
             "east to LaBelle, so that " + WORK_ORDER + " classifies those properties on evidence instead of being "
             "blind to them. Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Fort Myers / Cape Coral is ONE market of Lee County, every row keeping its own municipality: "
         "five CORE corridors (Downtown / River District, Colonial Boulevard & Cleveland Avenue, Daniels Parkway & Six "
         "Mile Cypress, RSW Airport / Gateway / Treeline, East Fort Myers / I-75), six STRONG CORRIDORS (Cape Coral, "
         "Fort Myers Beach, South Fort Myers / Iona, Sanibel, Estero, Bonita Springs) and three FRINGE corridors "
         "(North Fort Myers, Lehigh Acres / Alva, Captiva). NAPLES, MARCO ISLAND, EVERGLADES CITY, PUNTA GORDA, PORT "
         "CHARLOTTE, ENGLEWOOD / BOCA GRANDE, PINE ISLAND, SARASOTA, BRADENTON and VENICE are refused; Collier, "
         "Charlotte and Hendry County licences are refused whatever their mailing label. Patient, charitable and "
         "on-base lodging is never admitted."),
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
        ("market_name", "Fort Myers, Cape Coral & Sanibel, Florida"),
        ("market_slug", MARKET_ID),
        ("state_name", "Florida"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("primary_city", "Fort Myers"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Fort Myers, Cape Coral & Sanibel, Florida | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Fort Myers and Southwest Florida -- downtown and the River District, "
         "Colonial Boulevard and Daniels Parkway, RSW airport, Cape Coral, Fort Myers Beach, Sanibel and Captiva, "
         "Estero and Bonita Springs -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Fort Myers & Cape Coral"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry; the property's MUNICIPALITY is the one its own postal code and "
         "page put it in. A Fort Myers and Cape Coral travel market -- downtown and the River District, the US-41 / "
         "Colonial / Daniels hotel rows, RSW airport and Gateway, Cape Coral, Fort Myers Beach, Sanibel and Captiva, "
         "Estero and Bonita Springs. Not 'Southwest Florida': Naples, Marco Island, Everglades City, Punta Gorda, "
         "Port Charlotte, Englewood / Boca Grande, Sarasota, Bradenton and Venice are future standalone markets. "
         "Nothing else admits a property: not a brand's 'Fort Myers' or 'Naples' marketing name, not a map pin, not "
         "a vacation-rental listing, not a competitor directory's city label. Patient, charitable and on-base "
         "lodging is never admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Cape Coral, Fort Myers "
         "Beach, Sanibel, Captiva, Estero, Bonita Springs, North Fort Myers and Lehigh Acres rows keep their own "
         "municipality and are never written as Fort Myers. Shared codes are covered whole: 33901 by downtown and the "
         "River District; 33913 by RSW, Gateway, Treeline and Gulf Coast Town Center; 33931 by Estero Island and the "
         "mainland approach; 33993 by Cape Coral and Matlacha; 34134 by Bonita Springs, Collier-licensed premises "
         "refused. The River District, RSW, Gateway, Treeline, Gulf Coast Town Center, Coconut Point and Times "
         "Square are overlays."),
        ("_census_membership_note",
         "Individual condominium units, private residences, beach houses and canal homes, vacation homes and "
         "nightly-rental condos sold by property managers, corporate-housing portfolios, serviced-apartment "
         "operators, Airbnb / Vrbo inventory, ordinary apartments, student housing, timeshare and vacation-club "
         "inventory, residential-only towers, member-only club lodging and on-base military / government lodging are "
         "never admitted. A beach inn, island cottage court or bed-and-breakfast is admitted when its own site proves "
         "a public lodging operation at an exact premises. A mixed hotel / condo / residence resort is admitted only "
         "as the exact hotel premises its public operator sells as a hotel. A beach or island property publishes "
         "only on current first-party proof of operation."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    counties = ("Lee",)
    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 + 6 + 7 + 8 + 9 + 10 + 11 -- Fort Myers / Cape Coral travel-market geography, the "
                  "municipality rule, the Naples / Bonita Springs boundary, the post-hurricane operating-status rule, "
                  "the beach / island rule, the condo / vacation-rental rule, the timeshare rule, the RSW airport "
                  "rule and the Estero / Bonita / I-75 corridor rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/fort-myers-fl.json. This "
         "order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its brand's own property card states it, "
         "joined to the corridor registry. Nothing else admits a property; a State licence naming Collier, "
         "Charlotte or Hendry County refuses one."),
        ("municipality_rule",
         "Every admitted postal code carries its county and its real municipalities (POSTAL_PARISH / POSTAL_COUNTY). "
         "'Fort Myers' is published only where the code carries it. A stated city that is not one of its code's "
         "municipalities is a MUNICIPALITY CONFLICT and the row publishes its code's own municipality, the stated "
         "label kept as evidence (WRONG-CITY FORT MYERS IDENTITIES = 0)."),
        ("postal_county", OrderedDict((z, OrderedDict([("county", p), ("municipalities", list(m))]))
                                      for z, (p, m) in POSTAL_PARISH.items())),
        ("classes", OrderedDict((k, "; ".join("%s (%s, %s)" % (c[1], c[7], ", ".join(c[5])) for c in CORRIDORS
                                              if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG_CORRIDOR is registry class CORRIDOR; FUTURE_STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes, by licence COUNTY (Collier, "
                          "Charlotte, Hendry), by name on Captiva's shared code (the boat-access islands) and by "
                          "postal PREFIX for Sarasota / Bradenton / Venice; the future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("rsw_airport_evaluation", RSW_AIRPORT_EVALUATION),
        ("beach_island_evaluation", BEACH_ISLAND_EVALUATION),
        ("operating_status_rule", OPERATING_STATUS_RULE),
        ("fort_myers_ruling", FORT_MYERS_RULING),
        ("metro_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("county_refusals", COUNTY_REFUSALS),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("boat_access_islands_rule", OrderedDict([
            ("ruling", "Useppa, North / Upper Captiva and Safety Harbor share Captiva's 33924 and Cabbage Key is "
                       "licensed at Pineland's 33945: boat-access islands of private clubs and vacation homes, refused "
                       "BY NAME (BOUNDARY_NAME_RX) and by municipality on 33924. Pine Island (Bokeelia, St. James "
                       "City, Pineland) and Boca Grande are refused by postal code."),
            ("municipality_refusals", [OrderedDict([("postal_code", z), ("municipality", m), ("why", w)])
                                       for z, m, w in MUNICIPALITY_REFUSALS]),
        ])),
        ("military_lodging_rule", OrderedDict([
            ("rule", "On-base military lodging is MILITARY_RESTRICTED and never admitted. Lee County has no "
                     "installation with transient lodging; the names are refused wherever they appear."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "Fort Myers, Cape Coral and the beaches and islands were selected as a high-value PetTripFinder market for "
         "beach and island leisure, spring training, RSW airport, university and medical travel. That lowers NO "
         "evidence standard: pet acceptance is never inferred from a beach town's reputation. It shapes only the "
         "CENSUS: every downtown, airport, suburban, beach and island lodging cluster is covered by an admitting "
         "corridor."),
        ("the_fort_myers_name_trap",
         "The chains put 'Fort Myers' on hotels in Estero, Gateway, Cape Coral and North Fort Myers, 'Airport' on "
         "hotels on Colonial Boulevard and in Estero, 'Fort Myers Beach' on mainland hotels at Summerlin Square, "
         "'Sanibel' on hotels in Iona, and 'Naples North' on hotels in Bonita Springs. A property's own postal code, "
         "street, phone and brand property code decide what and where it is -- and which MUNICIPALITY it is in; "
         "none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Southwest Florida International Airport (RSW)", "rsw-airport-gateway (33913)."),
            ("River District / Edison & Ford Winter Estates", "downtown-fort-myers (33901)."),
            ("JetBlue Park (Boston Red Sox spring training)", "rsw-airport-gateway (33913)."),
            ("Hammond Stadium (Minnesota Twins spring training)", "daniels-six-mile (33912)."),
            ("Florida Gulf Coast University", "rsw-airport-gateway (33965)."),
            ("Gulf Coast Medical Center / HealthPark", "daniels-six-mile (33912) / summerlin-iona (33908)."),
            ("Hertz Arena / Coconut Point / Miromar Outlets", "estero (33928)."),
            ("Fort Myers Beach / Times Square", "fort-myers-beach (33931)."),
            ("Sanibel Lighthouse / J.N. 'Ding' Darling NWR", "sanibel (33957)."),
        ])),
        ("evaluated_inclusions", EVALUATED_INCLUSIONS),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_postal_codes_by_county", OrderedDict(
            (p, sorted(z for z in seen_zip if POSTAL_PARISH[z][0] == p)) for p in counties)),
        ("corridor_count_by_county", OrderedDict(
            (p, sum(1 for c in corridors if POSTAL_PARISH[c["included_postal_codes"][0]][0] == p))
            for p in counties)),
        ("admitted_counties", sorted(ADMITTED_PARISHES)),
        ("observed_outside_counties", OBSERVED_PARISHES),
        ("outside_prefixes", [OrderedDict([("prefix", p), ("area", n), ("future_market", f)])
                              for p, n, f in OUTSIDE_PREFIXES]),
        ("shared_postal_codes", SHARED_POSTAL_CODES),
        ("registered_market_postal_codes_checked", len(registered_codes)),
        ("no_live_market_postal_code_admitted", not live_overlap),
        ("seventh_florida_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("state_code", c["state_code"]), ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, beach, island, spring-"
         "training or neighbourhood keywords; every corridor is show_in_navigation / show_in_sitemap false until a "
         "registration order publishes it."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, beach inns, island cottage courts and bed-and-breakfasts that prove "
         "a public lodging operation, public resorts, qualifying condo-hotels with a distinct public hotel operation, "
         "qualifying extended-stay hotels and other public lodging establishments: bookable nightly rooms or suites "
         "sold to the public under one establishment name, with an official property page and an on-site operation. "
         "It NEVER admits: individual condominium units; vacation homes, beach houses, canal homes and nightly-rental "
         "condos sold by owners or managers; private rooms and guest suites; property-management / corporate-housing "
         "/ short-term-rental portfolios; serviced-apartment operators; Airbnb / Vrbo listings; ordinary apartments; "
         "student housing; timeshare and vacation-club inventory; residential-only towers; member-only club lodging; "
         "on-base military / government lodging; and privately managed units inside condo-hotels. Campgrounds, RV "
         "parks and marinas are NON_LODGING."),
        ("shared_campus_rule",
         "Never merged solely by display name, brand, owner, phone, shared address, campus, booking engine, shared "
         "amenities or shared entrance. Exact premises identity (its own street address or its own brand property "
         "code on its own page) governs. A dual-brand building is TWO hotels and is HELD for the split."),
        ("seasonal_rule",
         "A seasonally operating beach or island inn is a CURRENT business: closed-for-season is not closed. A "
         "preopening hotel ('Opening 2026', 'Coming Soon') never publishes; a closed, rebuilding or demolished hotel "
         "never publishes; a rebrand is resolved to the operator's current name on its own page."),
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


def boundary_name_reason(name, street=""):
    """The refusal a row's own NAME or STREET carries when it names a refused place an admitted code or label hides:
    a Captiva-labelled boat-access island (Useppa, North Captiva, Cabbage Key) or a Pine Island / Gasparilla Island
    premises. Or ""."""
    for text in (name or "", street or ""):
        m = BOUNDARY_NAME_RX.search(text)
        if m:
            return ("refused place named on the row (%r) -- boat-access island, Pine Island or Gasparilla Island "
                    "premises, never admitted" % m.group(0))
    return ""


def county_refusal_reason(county):
    """The refusal a State licence's COUNTY carries (Collier, Charlotte, Hendry), or ""."""
    c = " ".join((county or "").lower().replace("county", "").split())
    return COUNTY_REFUSALS.get(c, "")


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


def parish_for_postal(postal):
    entry = POSTAL_PARISH.get((postal or "").strip()[:5])
    return entry[0] if entry else ""


county_for_postal = parish_for_postal


def municipality_for_postal(postal, stated_city=""):
    """The REAL municipality a premises at ``postal`` publishes: the stated city when the code carries it, else the
    code's first (principal) municipality. ``fort myers`` is returned only for a code that carries it. "" for a code
    outside the admitted partition."""
    entry = POSTAL_PARISH.get((postal or "").strip()[:5])
    if not entry:
        return ""
    stated = normalise_municipality(stated_city)
    if stated in entry[1]:
        return stated
    return entry[1][0]


def municipality_display(postal, stated_city=""):
    m = municipality_for_postal(postal, stated_city)
    return MUNICIPALITY_DISPLAY.get(m, (stated_city or "").strip())


def municipality_conflict(postal, stated_city):
    """The reason a row's own STATED city is not a municipality its own postal code carries, or "". The guard behind
    WRONG-CITY FORT MYERS IDENTITIES = 0: a Cape Coral, Estero, Bonita Springs, Fort Myers Beach, Sanibel or North
    Fort Myers premises is never written as Fort Myers."""
    entry = POSTAL_PARISH.get((postal or "").strip()[:5])
    stated = normalise_municipality(stated_city)
    if not entry or not stated:
        return ""
    if stated in entry[1]:
        return ""
    return ("the row states the city %r beside postal code %s, which is %s County (%s); the premises publish as %s"
            % (stated_city, (postal or "")[:5], entry[0], " / ".join(entry[1]),
               MUNICIPALITY_DISPLAY.get(entry[1][0], entry[1][0])))


def state_conflict(postal, stated_state):
    """The reason a row's own STATED state contradicts the state its own postal code is in, or ""."""
    s = (stated_state or "").strip().upper()
    s = {"FLORIDA": "FL", "GEORGIA": "GA", "ALABAMA": "AL"}.get(s, s)
    z = state_for_postal(postal)
    if s and z and s != z:
        return ("the row states the state %s beside postal code %s, which is %s; one of the two facts is wrong and the "
                "row is never re-labelled" % (s, (postal or "")[:5], z))
    return ""


def future_market_for(postal, municipality=""):
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
                if rz == z and rmuni == muni:
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
        return "OUTSIDE", None, "Southwest Florida postal code %r is claimed by no corridor" % z
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
    print("by class:", json.dumps(report["corridor_count_by_class"]), "by county:",
          json.dumps(report["corridor_count_by_county"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
