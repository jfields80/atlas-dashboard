"""PTF-NEW-ORLEANS-LA-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5, 6, 8, 9 and 10: the New Orleans / Greater New
Orleans market, Louisiana.

Built from zero on the CURRENT hardened lineage: the Kansas City-live release e42ae364 (live lineage commit 117afe11,
built_from c6609370). Current verified live at authoring time = kansas-city-mo deploy 6ac4dc8a39b0e7274828a32b, 43
markets / 4,136 profiles / 4,552 release-index routes / 4,628 served routes, host verified (release_index live-source
--verify-host). No earlier New Orleans build exists. It is the FIRST Louisiana market; the build refuses to admit any
code a registered market already admits.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical New Orleans traveller lodging market -- NOT merely the City of New Orleans municipal boundary, and NOT
south-east Louisiana -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE markets
named inside OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact to make a
number. The order's "STRONG_CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property card)
states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP
is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing
name never admits and never places a property.

NEIGHBOURHOODS ARE OVERLAYS, NEVER SPLIT CODES
---------------------------------------------
The French Quarter alone spans four postal codes (70112 from Canal to about Conti, 70130 on the river side of Canal
and the upper Quarter, 70116 below about Dumaine/Esplanade, and the single-building code 70140), and 70130 also
carries the Warehouse / Arts District, the Convention Center and the Lower Garden District. The corridor registry
therefore partitions CODES, and the neighbourhoods the order names (French Quarter, CBD / Canal Street, Warehouse /
Arts District, Convention Center, Garden / Lower Garden District, Uptown, Marigny / Bywater, Mid-City, Treme,
University / Audubon) are REPORTING OVERLAYS decided from the property's own street and pin -- never a membership
decision and never a split code.

PARISH / MUNICIPALITY IDENTITY (PHASE 3)
----------------------------------------
Greater New Orleans is four parishes and several municipalities. Orleans Parish IS the City of New Orleans (Algiers and
New Orleans East included). Kenner, Gretna, Westwego and Harahan are incorporated cities of JEFFERSON PARISH; Metairie,
Elmwood, Jefferson, Harvey, Marrero, Terrytown and River Ridge are unincorporated Jefferson Parish communities;
Chalmette and Arabi are St. Bernard Parish; Belle Chasse is Plaquemines Parish. Every admitted row keeps the
municipality its OWN premises are in: an airport hotel on Airline Drive in Kenner is a KENNER hotel whatever its name
says ("New Orleans Airport"), a Veterans Boulevard hotel is a METAIRIE hotel, and a West Bank Expressway hotel is a
GRETNA or HARVEY hotel even when it is marketed "New Orleans Downtown / West Bank". The postal code's parish is checked
against the row's stated city: a Jefferson / St. Bernard / Plaquemines postal code beside the city "New Orleans" is a
MUNICIPALITY CONFLICT and the row's real municipality is the code's own (municipality_for_postal); the stated label is
kept as evidence and never published as the row's city.

MSY (PHASE 4)
-------------
Louis Armstrong New Orleans International Airport is in KENNER (70062), Jefferson Parish, 15 miles west of the French
Quarter. The airport-area hotel row (Airline Drive, Loyola Drive, Williams Boulevard, Veterans Boulevard west of the
Causeway in Kenner) is 70062 / 70065 and is the msy-airport-kenner corridor; Metairie's Veterans Boulevard hotels
marketed "New Orleans Airport" are METAIRIE (70001-70006) and are placed there; St. Rose / Destrehan's "New Orleans
Airport" hotels (St. Charles Parish, 70087 / 70047) are OUTSIDE. One premises is one row however many of "Airport",
"MSY", "Kenner", "Metairie" and "New Orleans" its marketing carries.

HISTORIC INNS / GUESTHOUSES / B&Bs (PHASE 5) AND RESIDENCES / SHORT-TERM RENTALS (PHASE 8)
-----------------------------------------------------------------------------------------
New Orleans has an unusually large inventory of historic inns, guesthouses, bed-and-breakfasts and small boutique
lodging. A legitimate public lodging operation is admitted however small or historic it is; but private-room rentals,
ordinary residences, Airbnb / Vrbo listings, short-term-rental houses, individual condo units, property-management and
corporate-housing portfolios, private guest suites and serviced-apartment operators (Sonder, Kasa, Mint House,
Placemakr, Blueground, Lark, Barsala, Zeus, Stay Alfred, Landing, Vacasa, Evolve, AvantStay, Frontdesk) are never
admitted, even when they accept short stays.

TIMESHARE / VACATION OWNERSHIP (PHASE 9)
----------------------------------------
Club Wyndham (La Belle Maison, Avenue Plaza, the Wyndham Garden-adjacent resorts), WorldMark, Hilton Grand Vacations /
Diamond (Hilton Vacation Club The Quarter / Royal Palm / Avenue Plaza... wherever they appear), Marriott Vacation Club,
Holiday Inn Club Vacations, Bluegreen and Hyatt Vacation Club inventory is TIMESHARE and never admitted, even when its
brand lists it beside its hotels and even when a pet-policy page exists (the Phoenix correction-003 lesson).

MILITARY / GOVERNMENT LODGING
-----------------------------
NAS JRB New Orleans (Belle Chasse, 70143, the Navy Lodge) and Jackson Barracks sell no public lodging; the on-base
names are refused wherever they appear (NONPUBLIC_NAMES), and 70143 is claimed by no corridor.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/new_orleans_la.json
  launch_packages/pettripfinder/markets/proposed/new-orleans-la.json
  launch_packages/pettripfinder/markets/reports/new_orleans_la_geography_001.json
  launch_packages/pettripfinder/markets/reports/new_orleans_la_corridor_registry_001.json
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

WORK_ORDER = "PTF-NEW-ORLEANS-LA-HARDENED-SOURCE-READY-001"
MARKET_ID = "new-orleans-la"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "new_orleans_la.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "new-orleans-la.json")
REPORT_OUT = os.path.join(REPORTS, "new_orleans_la_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "new_orleans_la_corridor_registry_001.json")
#: Every REGISTERED market's own document: no postal code any of them admits may be admitted here.
REGISTERED_MARKETS_GLOB = os.path.join(PKG, "markets", "*.json")
AS_OF = "2026-10-06"
STATE_CODE = "LA"
STATE_CODES = ("LA",)


def state_for_postal(postal):
    """The state a postal code belongs to: Louisiana 700-714 (Mississippi 386-397 is named so the Gulf Coast boundary
    audit can state it). A row's own page still decides; this is the check every stated state is held against."""
    z = (postal or "").strip()[:3]
    if z.isdigit() and 700 <= int(z) <= 714:
        return "LA"
    if z.isdigit() and 386 <= int(z) <= 397:
        return "MS"
    return ""


#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description, state)
CORRIDORS = [
    # ---------------------------------------------------------------- CORE (City of New Orleans / Orleans Parish)
    ("french-quarter-marigny-bywater", "French Quarter, Marigny & Bywater", "French Quarter (Dumaine / Esplanade "
     "side) / Faubourg Marigny / Frenchmen Street / Bywater / Treme (riverside of Rampart) / St. Claude",
     "CORE", "new orleans", ["70116", "70117", "70140"],
     "The French Quarter below about Dumaine and its single-building code (70116 / 70140), the Faubourg Marigny and "
     "Frenchmen Street (70116 / 70117), the Bywater and St. Claude (70117) and Treme's riverside blocks (70116). The "
     "Quarter's Canal-side blocks are 70112 / 70130 and sit in their own corridors; the French Quarter is a reporting "
     "OVERLAY decided by street and pin, never a split code.", "LA"),
    ("cbd-canal-street", "CBD & Canal Street", "Central Business District / Canal Street (lake side) / Poydras / "
     "Superdome / Tulane & LSU medical district / Loyola Avenue / upper French Quarter (Iberville-Conti)", "CORE",
     "new orleans", ["70112", "70113", "70139", "70163", "70170"],
     "The Central Business District: Canal Street's lake side and the Roosevelt / Ritz-Carlton / Saenger blocks and "
     "the upper French Quarter between Iberville and about Conti (70112), Poydras, Loyola Avenue, the Superdome and "
     "the medical district (70112 / 70113), and the CBD office towers' own codes (70139 / 70163 / 70170).", "LA"),
    ("warehouse-district-convention-center", "Warehouse District & Convention Center", "Warehouse / Arts District / "
     "Ernest N. Morial Convention Center / Canal Street (river side) / upper French Quarter / Lower Garden District / "
     "Irish Channel", "CORE", "new orleans", ["70130"],
     "One postal code (70130) with five submarkets, each a REPORTING OVERLAY decided by street and pin: the river "
     "side of Canal Street and the French Quarter's upper blocks (Bourbon, Royal, Chartres, Decatur below Canal), the "
     "Warehouse / Arts District (Julia, Camp, Magazine, Tchoupitoulas), the Convention Center (Convention Center "
     "Boulevard), the Lower Garden District (Prytania, St. Charles, Magazine above the Pontchartrain Expressway) and "
     "the Irish Channel.", "LA"),
    ("garden-district-uptown", "Garden District & Uptown", "Garden District / Uptown / St. Charles Avenue / Magazine "
     "Street / University (Tulane & Loyola) / Audubon / Carrollton / Freret / Broadmoor", "CORE", "new orleans",
     ["70115", "70118", "70125"],
     "The Garden District and Uptown along St. Charles Avenue and Magazine Street (70115), the University district -- "
     "Tulane, Loyola, Audubon Park and Carrollton (70118) -- and Freret / Broadmoor (70125).", "LA"),
    ("mid-city", "Mid-City & Bayou St. John", "Mid-City / Canal Street (upper) / Tulane Avenue / Bayou St. John / "
     "City Park / Fair Grounds / Treme (lake side)", "CORE", "new orleans", ["70119"],
     "Mid-City, upper Canal Street and Tulane Avenue, Bayou St. John, City Park's edge, the Fair Grounds and Treme's "
     "lake-side blocks (70119).", "LA"),
    # ---------------------------------------------------------------- CORE (Jefferson Parish -- airport, Metairie)
    ("msy-airport-kenner", "MSY Airport & Kenner", "Louis Armstrong New Orleans International Airport (MSY) / Airline "
     "Drive / Loyola Drive / Williams Boulevard / Veterans Boulevard (Kenner) / Rivertown / Laketown",
     "CORE", "kenner", ["70062", "70063", "70064", "70065"],
     "The CITY OF KENNER, Jefferson Parish: the airport and its own hotel row on Airline Drive, Loyola Drive and "
     "Williams Boulevard (70062), Kenner's Veterans Boulevard / I-10 side (70065) and the PO codes (70063 / 70064). A "
     "hotel titled 'New Orleans Airport' here is a KENNER hotel.", "LA"),
    ("metairie", "Metairie", "Metairie / Veterans Memorial Boulevard / Causeway Boulevard / Lakeside / Fat City / "
     "Clearview / Old Metairie", "CORE", "metairie", ["70001", "70002", "70003", "70005", "70006"],
     "METAIRIE, unincorporated Jefferson Parish: the Causeway / Veterans Boulevard / Lakeside / Fat City hotel "
     "cluster (70001 / 70002 / 70005 / 70006) and West Metairie / Clearview (70003). A hotel titled 'New Orleans "
     "Metairie' or 'New Orleans Airport' here is a METAIRIE hotel.", "LA"),
    # ---------------------------------------------------------------- STRONG CORRIDOR
    ("elmwood-jefferson-harahan", "Elmwood, Jefferson & Harahan", "Elmwood / Clearview Parkway / Citrus Boulevard / "
     "Jefferson Highway / Ochsner / Old Jefferson / Harahan / River Ridge", "CORRIDOR", "jefferson",
     ["70121", "70123", "70181", "70183"],
     "East Jefferson's river side: Jefferson and Ochsner on Jefferson Highway (70121 / 70181), and Elmwood, Harahan "
     "and River Ridge (70123 / 70183, covered whole). USPS's default mailing name for 70121 and 70123 is 'New "
     "Orleans', but these premises are in JEFFERSON PARISH and keep their own municipality. STRONG.", "LA"),
    ("gretna-west-bank", "Gretna & Terrytown", "Gretna / Terrytown / West Bank Expressway (east) / Belle Chasse "
     "Highway / Oakwood", "CORRIDOR", "gretna", ["70053", "70056"],
     "The CITY OF GRETNA (70053) and Terrytown (70056) on the West Bank Expressway, Jefferson Parish. A hotel titled "
     "'New Orleans West Bank' or 'New Orleans Downtown' here is a GRETNA hotel. STRONG.", "LA"),
    ("harvey-west-bank", "Harvey", "Harvey / West Bank Expressway / Manhattan Boulevard / Lapalco", "CORRIDOR",
     "harvey", ["70058", "70059"],
     "HARVEY, unincorporated Jefferson Parish: the West Bank Expressway / Manhattan Boulevard hotel row (70058) and "
     "the PO code (70059). STRONG.", "LA"),
    ("westwego", "Westwego", "Westwego / Avondale / Bridge City / US-90", "CORRIDOR", "westwego",
     ["70094", "70096"],
     "The CITY OF WESTWEGO and its mailing area (Avondale, Bridge City, Waggaman) on US-90 (70094 / 70096). "
     "STRONG.", "LA"),
    ("algiers", "Algiers", "Algiers / Algiers Point / Lower Coast Algiers / General de Gaulle Drive", "CORRIDOR",
     "new orleans", ["70114", "70131"],
     "Algiers, the West Bank half of the City of New Orleans (Orleans Parish): Algiers Point and the ferry (70114) "
     "and General de Gaulle / Lower Coast Algiers (70131). Inside the city; claimed so no Orleans Parish code is left "
     "unaccounted.", "LA"),
    ("new-orleans-east", "New Orleans East & Gentilly", "New Orleans East / I-10 service road / Read Boulevard / "
     "Chef Menteur Highway / Gentilly / Lakeview / University of New Orleans", "CORRIDOR", "new orleans",
     ["70122", "70124", "70126", "70127", "70128", "70129"],
     "The rest of the City of New Orleans: Gentilly and the University of New Orleans (70122), Lakeview (70124), and "
     "New Orleans East's I-10 / Read Boulevard / Chef Menteur hotel row (70126 / 70127 / 70128 / 70129). Inside the "
     "city; claimed so no Orleans Parish code is left unaccounted.", "LA"),
    # ---------------------------------------------------------------- FRINGE (CAREFUL evaluation)
    ("marrero", "Marrero", "Marrero / Lapalco Boulevard / Barataria Boulevard", "FRINGE", "marrero",
     ["70072", "70073"],
     "MARRERO, unincorporated Jefferson Parish West Bank (70072 / 70073). Admitted at FRINGE after CAREFUL "
     "evaluation.", "LA"),
    ("chalmette-arabi", "Chalmette & Arabi", "Chalmette / Arabi / St. Bernard Highway / Paris Road", "FRINGE",
     "chalmette", ["70032", "70043", "70044"],
     "St. Bernard Parish's metro-continuous edge with the Lower Ninth Ward: Arabi (70032) and Chalmette (70043 / "
     "70044). Admitted at FRINGE after CAREFUL evaluation; Meraux, Violet and St. Bernard beyond are refused.", "LA"),
    ("belle-chasse", "Belle Chasse", "Belle Chasse / LA-23", "FRINGE", "belle chasse", ["70037"],
     "Belle Chasse, Plaquemines Parish, on LA-23 south of the West Bank (70037). Admitted at FRINGE after CAREFUL "
     "evaluation; NAS JRB New Orleans (70143) is a military code claimed by no corridor, and lower Plaquemines is "
     "refused.", "LA"),
]

OUTSIDE = [
    ("Baton Rouge / East Baton Rouge Parish", "LA", [],
     "EAST BATON ROUGE PARISH; FUTURE_STANDALONE baton-rouge-la. The state capital 80 miles north-west on I-10 -- a "
     "trip of its own, never absorbed. Refused by postal PREFIX (707 / 708)."),
    ("Covington / Mandeville / Madisonville / Abita Springs -- the Northshore", "LA",
     ["70433", "70434", "70435", "70447", "70448", "70471", "70420"],
     "ST. TAMMANY PARISH; FUTURE_STANDALONE northshore-la. Across Lake Pontchartrain (the Causeway is 24 miles). "
     "Refused by name, postal code and PREFIX (704)."),
    ("Slidell", "LA", ["70458", "70459", "70460", "70461"],
     "ST. TAMMANY PARISH; FUTURE_STANDALONE northshore-la. 30 miles north-east on I-10. Refused by name and postal "
     "code (and prefix 704)."),
    ("Hammond / Ponchatoula / Tangipahoa Parish", "LA", ["70401", "70402", "70403", "70404", "70454"],
     "TANGIPAHOA PARISH; FUTURE_STANDALONE northshore-la. 55 miles north-west on I-55. Refused by prefix 704."),
    ("Houma / Thibodaux / Terrebonne and Lafourche Parishes", "LA",
     ["70360", "70361", "70363", "70364", "70301", "70302", "70310"],
     "TERREBONNE / LAFOURCHE PARISH; FUTURE_STANDALONE houma-la. 55 miles south-west. Refused by prefix 703."),
    ("St. Charles Parish -- St. Rose, Destrehan, Luling, Hahnville, Boutte, Norco", "LA",
     ["70087", "70047", "70070", "70057", "70039", "70079", "70030"],
     "ST. CHARLES PARISH. Its I-310 / Airline Highway hotels market themselves 'New Orleans Airport' and are placed "
     "by their own code: OUTSIDE. Not in the order's evaluation list; refused after careful evaluation so the market "
     "does not silently absorb the river parishes. Recorded in the boundary audit."),
    ("LaPlace / St. John the Baptist Parish and the river parishes beyond", "LA",
     ["70068", "70069", "70084", "70051", "70049", "70090"],
     "ST. JOHN / ST. JAMES PARISH. 30 miles west on I-10 / I-55. Refused after careful evaluation; recorded in the "
     "boundary audit."),
    ("St. Bernard Parish beyond Chalmette -- Meraux, Violet, St. Bernard, Poydras", "LA",
     ["70075", "70092", "70085", "70082"],
     "ST. BERNARD PARISH beyond the Arabi / Chalmette edge. Refused after careful evaluation."),
    ("Plaquemines Parish beyond Belle Chasse, and NAS JRB New Orleans", "LA",
     ["70143", "70083", "70091", "70040", "70041", "70050", "70081", "70038", "70358"],
     "PLAQUEMINES PARISH beyond Belle Chasse; 70143 is NAS JRB New Orleans (military, Navy Lodge -- "
     "MILITARY_RESTRICTED). Refused."),
    ("Jefferson Parish beyond the evaluated West Bank -- Lafitte, Barataria, Crown Point, Grand Isle", "LA",
     ["70036", "70067", "70358"],
     "Jefferson Parish's southern reaches. Refused after careful evaluation."),
    ("Gulfport / Biloxi / D'Iberville, Mississippi", "MS",
     ["39501", "39503", "39507", "39530", "39531", "39532", "39540"],
     "HARRISON COUNTY MS; FUTURE_STANDALONE mississippi-gulf-coast-ms. 80 miles east on I-10. Refused by postal "
     "PREFIX (395) and state."),
    ("Bay St. Louis / Waveland / Pass Christian / Long Beach / Ocean Springs / Pascagoula, Mississippi", "MS",
     ["39520", "39521", "39525", "39571", "39560", "39564", "39565", "39567", "39581"],
     "HANCOCK / HARRISON / JACKSON COUNTY MS; FUTURE_STANDALONE mississippi-gulf-coast-ms. Refused by PREFIX (395) "
     "and state."),
    ("Greater Louisiana, greater Mississippi and out of state", "--", [],
     "Every other Louisiana postal prefix and every code outside Louisiana is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("703", "Houma / Thibodaux / Bayou Lafourche", "houma-la"),
    ("704", "Hammond / Northshore (Covington, Mandeville, Slidell)", "northshore-la"),
    ("705", "Lafayette / Acadiana", ""),
    ("706", "Lake Charles / south-west Louisiana", ""),
    ("707", "Baton Rouge region", "baton-rouge-la"),
    ("708", "Baton Rouge", "baton-rouge-la"),
    ("710", "Shreveport region", ""),
    ("711", "Shreveport", ""),
    ("712", "Monroe / north-east Louisiana", ""),
    ("713", "Alexandria region", ""),
    ("714", "Alexandria", ""),
    ("395", "Mississippi Gulf Coast (Gulfport / Biloxi / Bay St. Louis)", "mississippi-gulf-coast-ms"),
    ("394", "Hattiesburg / south Mississippi", ""),
    ("396", "McComb / south-west Mississippi", ""),
]

#: Greater New Orleans's own postal prefixes. A code under one of these that no corridor claims and no OUTSIDE row
#: names is an UNCLAIMED metro / regional code -- refused, and named in the boundary audit so it is visible, never
#: silently dropped.
VALLEY_PREFIXES = ("700", "701")

#: The parish each admitted (and each evaluated-but-refused 700/701) code is in, and the REAL municipality its
#: premises are in. The municipality is what a row publishes; "new orleans" is the real municipality ONLY of an
#: Orleans Parish code. Where one code spans more than one municipality the tuple lists every one, and the row's own
#: stated municipality must be one of them.
POSTAL_PARISH = OrderedDict()
for _z in ("70112", "70113", "70114", "70115", "70116", "70117", "70118", "70119", "70122", "70124", "70125",
           "70126", "70127", "70128", "70129", "70130", "70131", "70139", "70140", "70163", "70170"):
    POSTAL_PARISH[_z] = ("Orleans", ("new orleans",))
POSTAL_PARISH.update([
    ("70062", ("Jefferson", ("kenner",))),
    ("70063", ("Jefferson", ("kenner",))),
    ("70064", ("Jefferson", ("kenner",))),
    ("70065", ("Jefferson", ("kenner",))),
    ("70001", ("Jefferson", ("metairie",))),
    ("70002", ("Jefferson", ("metairie",))),
    ("70003", ("Jefferson", ("metairie", "kenner"))),
    ("70005", ("Jefferson", ("metairie",))),
    ("70006", ("Jefferson", ("metairie",))),
    ("70121", ("Jefferson", ("jefferson", "elmwood", "harahan"))),
    ("70181", ("Jefferson", ("jefferson",))),
    ("70123", ("Jefferson", ("elmwood", "harahan", "river ridge", "jefferson"))),
    ("70183", ("Jefferson", ("harahan", "elmwood"))),
    ("70053", ("Jefferson", ("gretna",))),
    ("70056", ("Jefferson", ("gretna", "terrytown"))),
    ("70058", ("Jefferson", ("harvey",))),
    ("70059", ("Jefferson", ("harvey",))),
    ("70072", ("Jefferson", ("marrero",))),
    ("70073", ("Jefferson", ("marrero",))),
    ("70094", ("Jefferson", ("westwego", "avondale", "bridge city", "waggaman"))),
    ("70096", ("Jefferson", ("westwego",))),
    ("70032", ("St. Bernard", ("arabi",))),
    ("70043", ("St. Bernard", ("chalmette",))),
    ("70044", ("St. Bernard", ("chalmette",))),
    ("70037", ("Plaquemines", ("belle chasse",))),
])

#: How each real municipality is written when it is published.
MUNICIPALITY_DISPLAY = {
    "new orleans": "New Orleans", "kenner": "Kenner", "metairie": "Metairie", "jefferson": "Jefferson",
    "elmwood": "Elmwood", "harahan": "Harahan", "river ridge": "River Ridge", "gretna": "Gretna",
    "terrytown": "Terrytown", "harvey": "Harvey", "marrero": "Marrero", "westwego": "Westwego",
    "avondale": "Avondale", "bridge city": "Bridge City", "waggaman": "Waggaman", "arabi": "Arabi",
    "chalmette": "Chalmette", "belle chasse": "Belle Chasse",
}

ADMITTED_PARISHES = {"orleans (the city of new orleans: french quarter, cbd, warehouse district, garden district, "
                     "uptown, marigny, bywater, mid-city, algiers, new orleans east, gentilly, lakeview)",
                     "jefferson (kenner / msy, metairie, elmwood, jefferson, harahan, river ridge, gretna, "
                     "terrytown, harvey, westwego, marrero; lafitte, barataria and grand isle refused)",
                     "st. bernard (arabi, chalmette; meraux, violet and st. bernard refused)",
                     "plaquemines (belle chasse; nas jrb and lower plaquemines refused)"}
OBSERVED_PARISHES = OrderedDict([
    ("east baton rouge (baton rouge)", "baton-rouge-la"),
    ("st. tammany (covington, mandeville, slidell)", "northshore-la"),
    ("tangipahoa (hammond, ponchatoula)", "northshore-la"),
    ("terrebonne / lafourche (houma, thibodaux)", "houma-la"),
    ("st. charles (st. rose, destrehan, luling)", "(none -- refused after careful evaluation)"),
    ("st. john the baptist / st. james (laplace)", "(none -- refused after careful evaluation)"),
    ("harrison / hancock / jackson ms (gulfport, biloxi, bay st. louis)", "mississippi-gulf-coast-ms"),
])
#: Inherited consumer name (the cross-county audit slot).
OBSERVED_COUNTIES = OBSERVED_PARISHES
ADMITTED_COUNTIES = ADMITTED_PARISHES

#: The parish-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("orleans", OrderedDict([
        ("ruling", "ADMITTED WHOLE. Orleans Parish is the City of New Orleans; every Orleans Parish lodging code is "
                   "claimed by a corridor, Algiers and New Orleans East included."),
    ])),
    ("jefferson", OrderedDict([
        ("ruling", "ADMITTED, SPLIT, MUNICIPALITIES PRESERVED. Kenner (MSY), Metairie, Elmwood / Jefferson / Harahan / "
                   "River Ridge, Gretna / Terrytown, Harvey, Westwego and Marrero are admitted, each row keeping its own "
                   "municipality -- never flattened into New Orleans. Lafitte, Barataria and Grand Isle are refused."),
    ])),
    ("st. bernard", OrderedDict([
        ("ruling", "ADMITTED ONLY AT ARABI / CHALMETTE (FRINGE). Meraux, Violet and St. Bernard are refused."),
    ])),
    ("plaquemines", OrderedDict([
        ("ruling", "ADMITTED ONLY AT BELLE CHASSE (FRINGE). NAS JRB New Orleans and lower Plaquemines are refused."),
    ])),
    ("st. charles / st. john", OrderedDict([
        ("ruling", "REFUSED. St. Rose / Destrehan 'New Orleans Airport' hotels and LaPlace are placed by their own "
                   "code: OUTSIDE."),
    ])),
    ("st. tammany / tangipahoa / east baton rouge / terrebonne; mississippi gulf coast", OrderedDict([
        ("ruling", "REFUSED. The Northshore (Covington, Mandeville, Slidell), Hammond, Baton Rouge, Houma and the "
                   "Mississippi Gulf Coast are not absorbed (FUTURE_STANDALONE northshore-la, baton-rouge-la, "
                   "houma-la, mississippi-gulf-coast-ms)."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / patient / member
#: only). A normalised-name substring match; the census row keeps its reason.
NONPUBLIC_NAMES = {
    "navy lodge": "Navy Lodge on-base lodging (NAS JRB New Orleans) -- MILITARY_RESTRICTED",
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- MILITARY_RESTRICTED",
    "jackson barracks": "Jackson Barracks (Louisiana National Guard) lodging -- MILITARY_RESTRICTED",
    "nas jrb": "NAS JRB New Orleans base lodging -- MILITARY_RESTRICTED",
    "navy gateway inns": "Navy Gateway Inns & Suites on-base lodging -- MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "hope lodge": "American Cancer Society Hope Lodge -- patient lodging, not public lodging",
    "family housing": "patient-family housing -- not public lodging",
    "seamen s church": "seafarers' mission lodging -- not public lodging",
    "seafarers": "seafarers' mission lodging -- not public lodging",
    "rescue mission": "rescue mission shelter -- not public lodging",
    "covenant house": "youth shelter -- not public lodging",
}

#: Military postal codes inside the admitted partition. None: NAS JRB New Orleans (70143) is claimed by no corridor.
MILITARY_POSTAL_CODES = OrderedDict()

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("french-quarter-marigny-bywater", "New Orleans", "French Quarter / Marigny / Bywater", 29.9620, -90.0520, 2600,
     True),
    ("cbd-canal-street", "New Orleans", "CBD / Canal Street / Superdome", 29.9530, -90.0760, 1800, True),
    ("warehouse-district-convention-center", "New Orleans", "Warehouse District / Convention Center / Lower Garden "
     "District", 29.9420, -90.0680, 2000, True),
    ("garden-district-uptown", "New Orleans", "Garden District / Uptown / University", 29.9270, -90.1050, 4500,
     True),
    ("mid-city", "New Orleans", "Mid-City / Bayou St. John", 29.9750, -90.0950, 2800, True),
    ("msy-airport-kenner", "Kenner", "MSY / Kenner", 29.9980, -90.2450, 5000, True),
    ("metairie", "Metairie", "Metairie", 30.0000, -90.1800, 6000, True),
    ("elmwood-jefferson-harahan", "Jefferson", "Elmwood / Jefferson / Harahan / River Ridge", 29.9550, -90.1800,
     4500, True),
    ("gretna-west-bank", "Gretna", "Gretna / Terrytown", 29.9100, -90.0450, 3500, True),
    ("harvey-west-bank", "Harvey", "Harvey", 29.8950, -90.0800, 3500, True),
    ("westwego", "Westwego", "Westwego / Avondale", 29.9060, -90.1600, 4500, True),
    ("algiers", "New Orleans", "Algiers", 29.9300, -90.0100, 5000, True),
    ("new-orleans-east", "New Orleans", "New Orleans East / Gentilly / Lakeview", 30.0300, -89.9800, 12000, True),
    ("marrero", "Marrero", "Marrero", 29.8900, -90.1100, 3500, True),
    ("chalmette-arabi", "Chalmette", "Chalmette / Arabi", 29.9450, -89.9800, 4500, True),
    ("belle-chasse", "Belle Chasse", "Belle Chasse", 29.8500, -89.9900, 4000, True),
    ("obs-baton-rouge", "Baton Rouge", "Baton Rouge -- OBSERVATION ONLY", 30.4400, -91.1300, 20000, False),
    ("obs-northshore", "Covington", "Covington / Mandeville -- OBSERVATION ONLY", 30.4200, -90.0900, 15000, False),
    ("obs-slidell", "Slidell", "Slidell -- OBSERVATION ONLY", 30.2800, -89.7800, 10000, False),
    ("obs-hammond", "Hammond", "Hammond / Ponchatoula -- OBSERVATION ONLY", 30.4900, -90.4600, 12000, False),
    ("obs-houma", "Houma", "Houma / Thibodaux -- OBSERVATION ONLY", 29.6500, -90.7500, 20000, False),
    ("obs-river-parishes", "LaPlace", "St. Charles / St. John (St. Rose, Destrehan, LaPlace) -- OBSERVATION ONLY",
     30.0000, -90.4000, 15000, False),
    ("obs-gulf-coast", "Gulfport", "Gulfport / Biloxi / Bay St. Louis, Mississippi -- OBSERVATION ONLY", 30.3700,
     -89.1000, 35000, False),
]

#: The observation box. It reaches north-west past Baton Rouge, north across the lake to Hammond and the Northshore,
#: south-west to Houma and east along the Mississippi Gulf Coast to Biloxi, so the census counts what it refuses.
BOUNDS = {"min_lat": 29.15, "max_lat": 30.75, "min_lng": -91.35, "max_lng": -88.70}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
#: Listed most-specific first; the nearest anchor within its radius wins.
COVERAGE_AREAS = [
    ("French Quarter", 29.9585, -90.0645, 0.75),
    ("Canal Street", 29.9530, -90.0700, 0.30),
    ("Convention Center", 29.9410, -90.0630, 0.55),
    ("Warehouse / Arts District", 29.9450, -90.0690, 0.55),
    ("CBD", 29.9505, -90.0735, 0.75),
    ("Marigny", 29.9645, -90.0560, 0.65),
    ("Bywater", 29.9630, -90.0390, 0.90),
    ("Treme", 29.9655, -90.0700, 0.60),
    ("Lower Garden District", 29.9355, -90.0725, 0.65),
    ("Garden District", 29.9280, -90.0850, 0.80),
    ("University / Audubon", 29.9350, -90.1220, 1.20),
    ("Uptown", 29.9230, -90.1050, 2.20),
    ("Mid-City", 29.9720, -90.0950, 1.80),
    ("MSY / Kenner", 29.9950, -90.2450, 4.50),
    ("Metairie", 30.0000, -90.1750, 5.50),
    ("Elmwood / Jefferson", 29.9580, -90.1750, 3.50),
    ("Gretna", 29.9120, -90.0520, 2.50),
    ("Harvey / West Bank", 29.8950, -90.0850, 3.50),
    ("Algiers", 29.9350, -90.0200, 3.50),
    ("New Orleans East", 30.0300, -89.9700, 8.00),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin). Reporting only.
_FQ_STREETS = (r"bourbon|royal|chartres|decatur|dauphine|burgundy|n\.? rampart|toulouse|st\.? louis|st\.? peter|"
               r"st\.? ann|dumaine|st\.? philip|ursulines|gov(ernor)?\.? nicholls|barracks|esplanade|conti|bienville|"
               r"iberville|orleans ave|wilkinson|exchange (pl|alley)|french market|n\.? peters|toulouse")
STREET_OVERLAYS = [
    ("Convention Center", re.compile(r"\bconvention center (blvd|boulevard)\b", re.I)),
    ("Canal Street", re.compile(r"^\s*\d+[a-z]?\s+canal (st|street)\b", re.I)),
    ("French Quarter", re.compile(r"^\s*\d+[a-z]?\s+(%s)\b(?=.*\b70(116|130|112|140)\b)" % _FQ_STREETS, re.I)),
    ("MSY / Kenner", re.compile(r"\bairline (dr|drive|hwy|highway)\b(?=.*\b7006[25]\b)|\bloyola (dr|drive)\b(?=.*"
                                r"\b7006[25]\b)|\bterminal (dr|drive)\b(?=.*\b7006[25]\b)", re.I)),
    ("Warehouse / Arts District", re.compile(r"\b(julia|girod|lafayette|poydras|tchoupitoulas|s\.? peters|"
                                             r"fulton|magazine|camp|o'?keefe|andrew higgins|baronne)\b(?=.*\b70130\b)",
                                             re.I)),
    ("Marigny", re.compile(r"\bfrenchmen\b|\bdecatur\b(?=.*\b70116\b)(?!.*\besplanade\b)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "french-quarter-marigny-bywater": "Marigny",
    "cbd-canal-street": "CBD",
    "warehouse-district-convention-center": "Warehouse / Arts District",
    "garden-district-uptown": "Uptown",
    "mid-city": "Mid-City",
    "msy-airport-kenner": "MSY / Kenner",
    "metairie": "Metairie",
    "elmwood-jefferson-harahan": "Elmwood / Jefferson",
    "gretna-west-bank": "Gretna",
    "harvey-west-bank": "Harvey / West Bank",
    "westwego": "Harvey / West Bank",
    "algiers": "Algiers",
    "new-orleans-east": "New Orleans East",
    "marrero": "Harvey / West Bank",
    "chalmette-arabi": "Chalmette / Arabi",
    "belle-chasse": "Belle Chasse",
}

#: The order's CORE / AIRPORT-JEFFERSON / WEST BANK / CAREFUL / KEEP-SEPARATE evaluation list, each classified.
EVALUATED_INCLUSIONS = OrderedDict([
    ("French Quarter", "ADMITTED (CORE). Spans 70116 / 70140 (french-quarter-marigny-bywater), 70112 (cbd-canal-street) "
                       "and 70130 (warehouse-district-convention-center); reported as an OVERLAY by street and pin."),
    ("Central Business District / CBD", "ADMITTED (CORE, cbd-canal-street, 70112 / 70113 / 70139 / 70163 / 70170)."),
    ("Canal Street", "ADMITTED (CORE). The lake side is 70112 (cbd-canal-street), the river side 70130 "
                     "(warehouse-district-convention-center); reported as an OVERLAY."),
    ("Warehouse / Arts District", "ADMITTED (CORE, warehouse-district-convention-center, 70130) -- overlay."),
    ("Convention Center", "ADMITTED (CORE, warehouse-district-convention-center, 70130) -- overlay."),
    ("Garden District", "ADMITTED (CORE, garden-district-uptown 70115; its Lower Garden District blocks are 70130)."),
    ("Lower Garden District", "ADMITTED (CORE, warehouse-district-convention-center, 70130) -- overlay."),
    ("Uptown", "ADMITTED (CORE, garden-district-uptown, 70115 / 70118 / 70125)."),
    ("Marigny", "ADMITTED (CORE, french-quarter-marigny-bywater, 70116 / 70117)."),
    ("Bywater", "ADMITTED (CORE, french-quarter-marigny-bywater, 70117)."),
    ("Mid-City", "ADMITTED (CORE, mid-city, 70119)."),
    ("Treme", "ADMITTED (CORE; 70116 riverside in french-quarter-marigny-bywater, 70119 lake side in mid-city) -- "
              "overlay."),
    ("University / Audubon", "ADMITTED (CORE, garden-district-uptown, 70118) -- overlay."),
    ("Louis Armstrong New Orleans International Airport / MSY", "ADMITTED (CORE, msy-airport-kenner, 70062). KENNER."),
    ("Kenner", "ADMITTED (CORE, msy-airport-kenner, 70062 / 70063 / 70064 / 70065). Municipality KENNER."),
    ("Metairie", "ADMITTED (CORE, metairie, 70001 / 70002 / 70003 / 70005 / 70006). Municipality METAIRIE."),
    ("Elmwood", "ADMITTED (STRONG CORRIDOR, elmwood-jefferson-harahan, 70123). Municipality ELMWOOD (Jefferson "
                "Parish)."),
    ("Jefferson", "ADMITTED (STRONG CORRIDOR, elmwood-jefferson-harahan, 70121 / 70181). Municipality JEFFERSON."),
    ("Gretna", "ADMITTED (STRONG CORRIDOR, gretna-west-bank, 70053 / 70056)."),
    ("Harvey", "ADMITTED (STRONG CORRIDOR, harvey-west-bank, 70058 / 70059)."),
    ("Westwego", "ADMITTED (STRONG CORRIDOR, westwego, 70094 / 70096)."),
    ("Marrero", "ADMITTED (FRINGE, marrero, 70072 / 70073). CAREFUL."),
    ("Chalmette", "ADMITTED (FRINGE, chalmette-arabi, 70043 / 70044). CAREFUL."),
    ("Arabi", "ADMITTED (FRINGE, chalmette-arabi, 70032). CAREFUL."),
    ("Belle Chasse", "ADMITTED (FRINGE, belle-chasse, 70037). CAREFUL; NAS JRB (70143) refused."),
    ("River Ridge", "ADMITTED (STRONG CORRIDOR, elmwood-jefferson-harahan, 70123 covered whole). CAREFUL."),
    ("Harahan", "ADMITTED (STRONG CORRIDOR, elmwood-jefferson-harahan, 70123 / 70183 covered whole). CAREFUL."),
    ("Algiers", "ADMITTED (CORRIDOR, algiers, 70114 / 70131) -- the City of New Orleans's West Bank."),
    ("New Orleans East / Gentilly / Lakeview", "ADMITTED (CORRIDOR, new-orleans-east, 70122 / 70124 / 70126-70129) -- "
                                               "inside the city."),
    ("Baton Rouge", "OUTSIDE -- FUTURE_STANDALONE baton-rouge-la; refused by prefix 707 / 708. KEEP SEPARATE."),
    ("Covington", "OUTSIDE -- FUTURE_STANDALONE northshore-la; refused by postal code and prefix 704. KEEP SEPARATE."),
    ("Mandeville", "OUTSIDE -- FUTURE_STANDALONE northshore-la; refused by postal code and prefix 704. KEEP SEPARATE."),
    ("Slidell", "OUTSIDE -- FUTURE_STANDALONE northshore-la; refused by postal code and prefix 704. KEEP SEPARATE."),
    ("Hammond", "OUTSIDE -- FUTURE_STANDALONE northshore-la; refused by prefix 704. KEEP SEPARATE."),
    ("Houma", "OUTSIDE -- FUTURE_STANDALONE houma-la; refused by prefix 703. KEEP SEPARATE."),
    ("Gulfport / Biloxi", "OUTSIDE -- FUTURE_STANDALONE mississippi-gulf-coast-ms; refused by prefix 395 and state. "
                          "KEEP SEPARATE."),
    ("Bay St. Louis", "OUTSIDE -- FUTURE_STANDALONE mississippi-gulf-coast-ms; refused by prefix 395 and state. "
                      "KEEP SEPARATE."),
    ("St. Rose / Destrehan / LaPlace (river parishes)", "OUTSIDE -- refused after careful evaluation by postal code; "
                                                        "recorded in the boundary audit."),
])

#: The MSY ruling (Phase 4), stated once.
MSY_AIRPORT_EVALUATION = OrderedDict([
    ("airport_terminal", "Louis Armstrong New Orleans International Airport (1 Terminal Drive) is in the CITY OF "
                         "KENNER, Jefferson Parish, 70062. No hotel stands inside the terminal."),
    ("kenner_airport_hotels", "The airport's own hotel row -- Airline Drive, Loyola Drive, Williams Boulevard and "
                              "Kenner's Veterans Boulevard -- is 70062 / 70065: the msy-airport-kenner corridor, "
                              "municipality KENNER, whatever 'New Orleans Airport' the name carries."),
    ("veterans_blvd", "Veterans Memorial Boulevard runs through BOTH Kenner (70062 / 70065) and Metairie (70001-70006); "
                      "a Veterans Boulevard hotel is placed by its own code, never by the road."),
    ("metairie_airport_marketed", "A Metairie hotel marketed 'New Orleans Airport' is a METAIRIE hotel (metairie "
                                  "corridor)."),
    ("st_charles_airport_marketed", "St. Rose / Destrehan 'New Orleans Airport' hotels (St. Charles Parish, 70087 / "
                                    "70047) are OUTSIDE."),
    ("one_premises_one_row", "A property is one row however many of 'Airport', 'MSY', 'Kenner', 'Metairie' and 'New "
                             "Orleans' its marketing carries; identity is its own street address, phone and brand "
                             "property code."),
])

#: The Jefferson Parish / West Bank ruling (Phase 3).
JEFFERSON_PARISH_EVALUATION = OrderedDict([
    ("municipalities_never_flattened", "Kenner, Metairie, Elmwood, Jefferson, Harahan, River Ridge, Gretna, Terrytown, "
                                       "Harvey, Westwego and Marrero each keep their own municipality; none is written "
                                       "as New Orleans."),
    ("new_orleans_mailing_name", "USPS's default mailing name for 70121 and 70123 is 'New Orleans' and some operators "
                                 "print it; those premises are in JEFFERSON PARISH and the row publishes the "
                                 "municipality its own code puts it in (municipality_for_postal)."),
    ("west_bank_marketing", "'New Orleans West Bank', 'New Orleans Downtown West Bank' and 'New Orleans Gretna' are "
                            "marketing; the property's own postal code decides Gretna, Terrytown, Harvey, Westwego or "
                            "Marrero, and Algiers (70114 / 70131) is the City of New Orleans."),
    ("shared_codes", "70003 (Metairie / Kenner), 70056 (Gretna / Terrytown), 70094 (Westwego / Avondale / Bridge "
                     "City / Waggaman), 70121 (Jefferson / Elmwood / Harahan) and 70123 (Elmwood / Harahan / River "
                     "Ridge) are covered whole by one corridor each; the row keeps the municipality its own page "
                     "states when that municipality is one the code carries."),
])

#: The market ruling (consumers read it under the inherited name HILL_COUNTRY_RULING).
NEW_ORLEANS_RULING = OrderedDict([
    ("classification", "The metro-continuous New Orleans core is admitted across four parishes -- the French Quarter, "
                       "Marigny and Bywater, the CBD and Canal Street, the Warehouse District / Convention Center / "
                       "Lower Garden District, the Garden District and Uptown, Mid-City, MSY / Kenner and Metairie "
                       "CORE; Elmwood / Jefferson / Harahan, Gretna / Terrytown, Harvey, Westwego, Algiers and New "
                       "Orleans East / Gentilly STRONG CORRIDOR; Marrero, Chalmette / Arabi and Belle Chasse FRINGE. "
                       "Baton Rouge, the Northshore (Covington, Mandeville, Slidell, Hammond), Houma, the river "
                       "parishes (St. Rose, Destrehan, LaPlace) and the Mississippi Gulf Coast are OUTSIDE."),
    ("a_marketing_phrase_admits_nothing", "'New Orleans Airport', 'MSY', 'New Orleans Metairie', 'New Orleans West "
                                          "Bank', 'New Orleans Downtown', 'French Quarter' and 'Near the Quarter' are "
                                          "marketing. The property's own postal code decides membership and its "
                                          "municipality."),
    ("actual_location", "Decided by the property's own postal code on its own page; the parish and the municipality "
                        "by that code."),
    ("drive_market_relationship", "The French Quarter, the CBD, the Warehouse District, the Garden District, Uptown, "
                                  "Mid-City, MSY / Kenner, Metairie and the West Bank are where New Orleans travellers "
                                  "sleep; Baton Rouge, the Northshore, Houma and the Gulf Coast are trips of their "
                                  "own."),
    ("traveller_intent", "Leisure (the French Quarter, Mardi Gras, Jazz Fest, the Fair Grounds, Frenchmen Street), "
                         "convention (the Ernest N. Morial Convention Center), arena and stadium (the Caesars "
                         "Superdome, the Smoothie King Center), medical (the Tulane / LSU / University Medical Center "
                         "district, Ochsner), university (Tulane, Loyola, UNO, Xavier), cruise (the Port of New "
                         "Orleans terminals) and MSY airport demand is New Orleans intent."),
    ("metro_continuity", "Continuous development runs along I-10 from Kenner to New Orleans East, across the "
                         "Crescent City Connection to the West Bank and down LA-23 to Belle Chasse; this registry stops "
                         "there."),
    ("corridor_support", "Every admitted edge code is in a named corridor so its count is visible and a founder can "
                         "move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE baton-rouge-la, northshore-la, houma-la and mississippi-gulf-coast-ms."),
])
HILL_COUNTRY_RULING = NEW_ORLEANS_RULING
TWIN_CITIES_RULING = NEW_ORLEANS_RULING
KANSAS_CITY_RULING = NEW_ORLEANS_RULING
#: Inherited consumer names (the cross-border evaluation slots): New Orleans's equivalents are the MSY and
#: Jefferson Parish evaluations.
VANCOUVER_EVALUATION = MSY_AIRPORT_EVALUATION
MSP_BLOOMINGTON_EVALUATION = MSY_AIRPORT_EVALUATION
MCI_NORTHLAND_EVALUATION = MSY_AIRPORT_EVALUATION
JOHNSON_COUNTY_EVALUATION = JEFFERSON_PARISH_EVALUATION

STRUCTURE_TEST = OrderedDict([
    ("A. Is New Orleans one market?",
     "ONE market, new-orleans-la, covering the City of New Orleans and the metro-continuous Jefferson, St. Bernard and "
     "Plaquemines edges the order evaluates -- one commercial airport (MSY), one I-10 / I-610 / US-90 / Crescent City "
     "Connection road system."),
    ("B. Municipalities are NOT flattened",
     "Every corridor names its municipality, every admitted code carries its parish and real municipality, and every "
     "row keeps its own. Kenner, Metairie, Gretna, Harvey and Westwego are never written as New Orleans."),
    ("C. MSY", "The airport and its hotel row are KENNER (70062 / 70065); 'Airport' hotels elsewhere are placed by "
               "their own code (MSY_AIRPORT_EVALUATION)."),
    ("D. Jefferson Parish", "Each municipality is its own (JEFFERSON_PARISH_EVALUATION)."),
    ("E. French Quarter / CBD / Canal / Warehouse / Convention Center / Garden District", "Overlays of their corridor, "
                                                                                          "never split codes."),
    ("F. Baton Rouge", "OUTSIDE -- FUTURE_STANDALONE baton-rouge-la."),
    ("G. The Northshore (Covington, Mandeville, Slidell, Hammond)", "OUTSIDE -- FUTURE_STANDALONE northshore-la."),
    ("H. Houma", "OUTSIDE -- FUTURE_STANDALONE houma-la."),
    ("I. Gulfport / Biloxi / Bay St. Louis", "OUTSIDE -- FUTURE_STANDALONE mississippi-gulf-coast-ms."),
    ("J. St. Rose / Destrehan / LaPlace", "OUTSIDE -- not absorbed."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel / inn operation."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP). A unit designator ('Ste', "
     "'Unit', '#', 'Apt', 'PH') in a registry address means the record is a UNIT INSIDE a building or campus, which "
     "is never a hotel identity."),
    ("historic_inn_rule",
     "A historic inn, guesthouse or bed-and-breakfast is admitted however small when its own site proves a PUBLIC "
     "LODGING OPERATION (rooms sold nightly to the public under one establishment name, with its own booking), an "
     "OFFICIAL PROPERTY IDENTITY, a PUBLIC BOOKING PRESENCE and an EXACT PREMISES. A private room, a whole-house "
     "rental, a 'guest suite' in a residence, a property-management listing or a short-term-rental permit is never "
     "an inn. Ambiguous qualification is HELD, never admitted to publication."),
    ("hotel_vs_residence_boundary",
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. New Orleans's "
     "specific exposures: CBD and Warehouse District condo towers with furnished short-stay units, French Quarter "
     "and Marigny short-term-rental houses and 'guest suites', the serviced-apartment and aparthotel operators "
     "(Sonder, Kasa, Mint House, Placemakr, Blueground, Lark, Barsala, Stay Alfred, Landing, Frontdesk), "
     "corporate-housing portfolios, Tulane / Loyola / UNO student housing, Club Wyndham / WorldMark / Hilton Vacation "
     "Club vacation-ownership inventory and the Airbnb / Vrbo inventory."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort (Club Wyndham, WorldMark, Hilton Grand Vacations, Hilton Vacation "
     "Club / Diamond, Marriott Vacation Club, Holiday Inn Club Vacations, Bluegreen, Hyatt Vacation Club) is TIMESHARE "
     "and is never admitted to hotel accounting, even when its brand lists it beside its hotels, even when it sells a "
     "nightly rate, and even when a pet-policy page exists (the Phoenix correction-003 lesson)."),
    ("casino_rule",
     "A casino name never proves a hotel. Harrah's / Caesars New Orleans's hotel tower is admitted only as the hotel "
     "its operator sells, with a hotel policy bound to the hotel's own premises; a casino-wide policy is never "
     "attached to a hotel without exact binding. Boomtown (Harvey) and Treasure Chest (Kenner) are casinos without "
     "public hotel rooms unless their own page proves one."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared "
     "amenities or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never "
     "published as one. A hotel and its residences on one campus are distinct premises. Adjoining French Quarter "
     "buildings sold under different names are different hotels; one inn sold across several buildings under one "
     "name is one premises at its own front-desk address."),
    ("extended_stay",
     "Extended-stay hotels are hotels and are admitted on their own pages; an 'apartment hotel' or 'aparthotel' is "
     "admitted only as a public hotel operation at an exact premises, never as a residential building that rents "
     "furnished units."),
    ("patient_and_military_lodging",
     "Patient-family housing (the Ronald McDonald House, Hope Lodge), charitable family lodging (Fisher House), "
     "shelters and seafarers' missions and on-base military lodging are never public hotels and are never admitted."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("70112", ["CBD", "Canal Street (lake side)", "French Quarter (Iberville-Conti)", "Superdome", "medical district"]),
    ("70130", ["French Quarter (upper, river side of Canal)", "Canal Street (river side)", "Warehouse / Arts District",
               "Convention Center", "Lower Garden District", "Irish Channel"]),
    ("70116", ["French Quarter (lower)", "Faubourg Marigny", "Treme (riverside)"]),
    ("70117", ["Faubourg Marigny (lower)", "Bywater", "St. Claude", "Holy Cross"]),
    ("70119", ["Mid-City", "Treme (lake side)", "Bayou St. John"]),
    ("70003", ["Metairie (west)", "Kenner (east edge)"]),
    ("70056", ["Gretna", "Terrytown"]),
    ("70094", ["Westwego", "Avondale", "Bridge City", "Waggaman"]),
    ("70121", ["Jefferson", "Elmwood", "Harahan (east)"]),
    ("70123", ["Elmwood", "Harahan", "River Ridge"]),
])

FUTURE_MARKETS = OrderedDict([
    ("baton-rouge-la", "Baton Rouge -- 80 miles north-west on I-10."),
    ("northshore-la", "The Northshore -- Covington, Mandeville, Slidell and Hammond, across Lake Pontchartrain."),
    ("houma-la", "Houma / Thibodaux -- 55 miles south-west."),
    ("mississippi-gulf-coast-ms", "The Mississippi Gulf Coast -- Bay St. Louis, Gulfport and Biloxi, 60-90 miles east "
                                  "on I-10."),
])

#: Markets that are ALREADY LIVE. No live market shares Louisiana; exposures are shared NAMES only: Jefferson (the
#: Jacksonville / Atlanta / Columbus regions' Jefferson streets and counties), Kenner and Gretna are names only here,
#: Metairie is unique, and "Harvey" / "Marrero" are surnames as well as places.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("kansas-city-mo", "Kansas City, live as production market #43 (deploy 6ac4dc8a39b0e7274828a32b) -- the CURRENT "
                       "LIVE market at this order's authoring time. No shared state, no shared postal code."),
    ("san-antonio-tx", "San Antonio, live -- a Gulf-region neighbour with no shared state or code."),
    ("jacksonville-fl", "Jacksonville, live -- its region names a Jefferson Street; identity is decided by premises "
                        "and state, never a street or town name."),
])

#: A shared postal code whose OTHER town is refused. None at authoring time.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "new orleans,": "new orleans", "nola": "new orleans", "n orleans": "new orleans", "new orleans la": "new orleans",
    "new orleans, la": "new orleans", "nouvelle-orléans": "new orleans", "algiers": "new orleans",
    "kenner,": "kenner", "metairie,": "metairie", "old metairie": "metairie", "jefferson,": "jefferson",
    "elmwood,": "elmwood", "harahan,": "harahan", "river ridge,": "river ridge", "gretna,": "gretna",
    "terrytown,": "terrytown", "harvey,": "harvey", "marrero,": "marrero", "westwego,": "westwego",
    "avondale,": "avondale", "bridge city,": "bridge city", "waggaman,": "waggaman", "arabi,": "arabi",
    "chalmette,": "chalmette", "belle chasse,": "belle chasse", "belle chase": "belle chasse",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("70112", "CBD / lake side of Canal / the French Quarter's Iberville-Conti blocks."),
    ("70130", "Upper French Quarter, river side of Canal, Warehouse District, Convention Center, Lower Garden "
              "District -- five overlays, one code."),
    ("70116", "Lower French Quarter / Marigny / Treme."),
    ("70140", "The Omni Royal Orleans building's own code (French Quarter)."),
    ("70062", "MSY and the Kenner airport hotel row -- KENNER, never New Orleans."),
    ("70001", "Metairie's Causeway / Veterans / Lakeside cluster -- METAIRIE."),
    ("70123", "Elmwood / Harahan / River Ridge -- Jefferson Parish, USPS default mailing name 'New Orleans'."),
    ("70056", "Terrytown / Gretna -- West Bank."),
    ("70087", "St. Rose (St. Charles Parish) 'New Orleans Airport' hotels -- refused."),
    ("70458", "Slidell -- refused (northshore-la)."),
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
                raise SystemExit("admitted postal code %s carries no parish / municipality" % z)
            seen_zip[z] = slug
        corridors.append(OrderedDict([
            ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
            ("market_id", MARKET_ID),
            ("name", name),
            ("slug", slug),
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder New Orleans" % name),
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
        raise SystemExit("admitted postal codes outside the New Orleans prefixes: %s" % stray)
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
        _state = "MS" if suffix == "obs-gulf-coast" else "LA"
        cells.append(OrderedDict([
            ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
            ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
            ("state_code", _state),
            ("admitting", admitting),
        ]))
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "New Orleans / Greater New Orleans, Louisiana -- French Quarter, CBD, convention, Garden "
                        "District and Uptown, Mid-City, MSY airport / Kenner, Metairie and West Bank lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("country", "US"),
        ("market_center", {"lat": 29.95, "lng": -90.07}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches north-west past Baton Rouge, north across the "
             "lake to Hammond and the Northshore, south-west to Houma and east along the Mississippi Gulf Coast to "
             "Biloxi, so that " + WORK_ORDER + " classifies those properties on evidence instead of being blind to "
             "them. Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". New Orleans / Greater New Orleans is ONE market across four parishes, every row keeping its "
         "own municipality: seven CORE corridors (French Quarter / Marigny / Bywater, CBD / Canal Street, Warehouse "
         "District / Convention Center, Garden District / Uptown, Mid-City, MSY / Kenner, Metairie), six STRONG "
         "CORRIDORS (Elmwood / Jefferson / Harahan, Gretna / Terrytown, Harvey, Westwego, Algiers, New Orleans East / "
         "Gentilly) and three FRINGE corridors (Marrero, Chalmette / Arabi, Belle Chasse). BATON ROUGE, the "
         "NORTHSHORE (Covington, Mandeville, Slidell, Hammond), HOUMA and the MISSISSIPPI GULF COAST are refused as "
         "future standalone markets; St. Rose, Destrehan and LaPlace are refused by code. Patient, charitable and "
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
        ("market_name", "New Orleans, Louisiana"),
        ("market_slug", MARKET_ID),
        ("state_name", "Louisiana"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("primary_city", "New Orleans"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in New Orleans, Louisiana | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater New Orleans -- the French Quarter, the CBD and Canal Street, the "
         "Warehouse District and Convention Center, the Garden District and Uptown, Mid-City, MSY airport and Kenner, "
         "Metairie and the West Bank -- with real pet fees and policies read from each hotel's own official "
         "website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "New Orleans"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry; the property's MUNICIPALITY is the one its own postal code and "
         "page put it in. A Greater New Orleans French Quarter, CBD, convention, Garden District, Uptown, Mid-City, "
         "medical, university, cruise, MSY airport, Kenner, Metairie and West Bank travel market -- the City of New "
         "Orleans and the metro-continuous Jefferson, St. Bernard and Plaquemines edges. Not 'Louisiana' and not "
         "'south-east Louisiana': Baton Rouge, the Northshore, Houma and the Mississippi Gulf Coast are future "
         "standalone markets; St. Rose, Destrehan and LaPlace are refused. Nothing else admits a property: not a "
         "brand's 'New Orleans' marketing name, not a map pin, not a vacation-rental listing, not a competitor "
         "directory's city label. Patient, charitable and on-base lodging is never admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Kenner, Metairie, "
         "Gretna, Harvey and Westwego keep their own municipality and are never written as New Orleans. Shared codes "
         "are covered whole: 70130 by the upper French Quarter, Canal Street's river side, the Warehouse District, "
         "the Convention Center and the Lower Garden District; 70112 by the CBD, Canal Street's lake side and the "
         "Quarter's Iberville-Conti blocks; 70116 by the lower Quarter, the Marigny and Treme; 70123 by Elmwood, "
         "Harahan and River Ridge. The French Quarter, Canal Street, the Warehouse District, the Convention Center "
         "and the Garden District are overlays."),
        ("_census_membership_note",
         "Individual condominium units, private residences, vacation homes, short-term-rental houses and private "
         "guest suites, property-management and corporate-housing portfolios, serviced-apartment operators, Airbnb / "
         "Vrbo inventory, ordinary apartments, student housing, timeshare and vacation-club inventory, "
         "residential-only towers, privately managed residences inside hotel towers, member-only club lodging and "
         "on-base military / government lodging are never admitted. A historic inn, guesthouse or bed-and-breakfast "
         "is admitted when its own site proves a public lodging operation at an exact premises. A mixed hotel / "
         "condo / residence / casino property is admitted only as the exact hotel premises its public operator sells "
         "as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 + 6 + 8 + 9 -- New Orleans / Greater New Orleans travel-market geography, the parish "
                  "/ municipality identity rule, the MSY / Kenner boundary, the historic-inn rule, the French Quarter "
                  "overlay rule, the residence / apartment / vacation-rental rule and the timeshare rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/new-orleans-la.json. This "
         "order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its brand's own property card states it, "
         "joined to the corridor registry. Nothing else admits a property."),
        ("municipality_rule",
         "Every admitted postal code carries its parish and its real municipality (POSTAL_PARISH). 'New Orleans' is "
         "the real municipality of an Orleans Parish code only; a Jefferson, St. Bernard or Plaquemines code beside "
         "the city 'New Orleans' is a MUNICIPALITY CONFLICT and the row publishes its code's own municipality, the "
         "stated label kept as evidence. Kenner, Metairie, Gretna, Harvey and Westwego are never flattened into New "
         "Orleans."),
        ("postal_parish", OrderedDict((z, OrderedDict([("parish", p), ("municipalities", list(m))]))
                                      for z, (p, m) in POSTAL_PARISH.items())),
        ("classes", OrderedDict((k, "; ".join("%s (%s, %s)" % (c[1], c[7], ", ".join(c[5])) for c in CORRIDORS
                                              if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG_CORRIDOR is registry class CORRIDOR; FUTURE_STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes and by postal PREFIX for the "
                          "refused regions; the future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("msy_airport_evaluation", MSY_AIRPORT_EVALUATION),
        ("jefferson_parish_evaluation", JEFFERSON_PARISH_EVALUATION),
        ("new_orleans_ruling", NEW_ORLEANS_RULING),
        ("metro_structure_test", STRUCTURE_TEST),
        ("parish_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("military_lodging_rule", OrderedDict([
            ("rule", "On-base military / government lodging is MILITARY_RESTRICTED and never admitted: restricted "
                     "eligibility (DoD ID or sponsorship), on-base premises behind a gate, ordinary public-hotel "
                     "contract NOT satisfied. NAS JRB New Orleans (70143) sits outside the partition; the on-base "
                     "names are refused wherever they appear."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "New Orleans was selected as a high-value PetTripFinder market for its French Quarter leisure demand, "
         "convention and event travel, medical and university travel, cruise departures and MSY airport traffic. That "
         "lowers NO evidence standard: pet acceptance is never inferred from a city's reputation. It shapes only the "
         "CENSUS: every tourist, convention, stadium, medical, cruise, airport and extended-stay lodging cluster is "
         "covered by an admitting corridor."),
        ("the_new_orleans_name_trap",
         "The chains put 'New Orleans' on hotels in Kenner, Metairie, Elmwood, Harahan, Gretna, Harvey, St. Rose and "
         "Slidell, and 'French Quarter' on hotels in the CBD and the Marigny. A property's own postal code, street, "
         "phone and brand property code decide what and where it is -- and which MUNICIPALITY it is in; none of "
         "those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Louis Armstrong New Orleans International Airport (MSY)", "msy-airport-kenner (70062)."),
            ("French Quarter / Bourbon Street / Jackson Square", "french-quarter-marigny-bywater (70116), "
                                                                 "warehouse-district-convention-center (70130), "
                                                                 "cbd-canal-street (70112)."),
            ("Ernest N. Morial Convention Center", "warehouse-district-convention-center (70130)."),
            ("Caesars Superdome / Smoothie King Center", "cbd-canal-street (70112 / 70113)."),
            ("Tulane / LSU / University Medical Center district", "cbd-canal-street (70112) and mid-city (70119)."),
            ("Tulane / Loyola / Audubon", "garden-district-uptown (70118)."),
            ("Port of New Orleans cruise terminals", "warehouse-district-convention-center (70130)."),
            ("Ochsner Medical Center", "elmwood-jefferson-harahan (70121)."),
            ("Fair Grounds / Jazz Fest / City Park", "mid-city (70119)."),
        ])),
        ("evaluated_inclusions", EVALUATED_INCLUSIONS),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_postal_codes_by_parish", OrderedDict(
            (p, sorted(z for z in seen_zip if POSTAL_PARISH[z][0] == p))
            for p in ("Orleans", "Jefferson", "St. Bernard", "Plaquemines"))),
        ("corridor_count_by_parish", OrderedDict(
            (p, sum(1 for c in corridors if POSTAL_PARISH[c["included_postal_codes"][0]][0] == p))
            for p in ("Orleans", "Jefferson", "St. Bernard", "Plaquemines"))),
        ("admitted_parishes", sorted(ADMITTED_PARISHES)),
        ("observed_outside_parishes", OBSERVED_PARISHES),
        ("outside_prefixes", [OrderedDict([("prefix", p), ("area", n), ("future_market", f)])
                              for p, n, f in OUTSIDE_PREFIXES]),
        ("shared_postal_codes", SHARED_POSTAL_CODES),
        ("registered_market_postal_codes_checked", len(registered_codes)),
        ("no_live_market_postal_code_admitted", not live_overlap),
        ("first_louisiana_market", True),
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
         "neighbourhood keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration "
         "order publishes it."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, guesthouses and bed-and-breakfasts that prove a public lodging "
         "operation, public resorts, qualifying condo-hotels with a distinct public hotel operation, qualifying "
         "extended-stay hotels and other public lodging establishments: bookable nightly rooms or suites sold to the "
         "public under one establishment name, with an official property page and an on-site operation. It NEVER "
         "admits: individual condominium units; vacation homes and short-term-rental houses sold by owners or "
         "managers; private rooms and guest suites; property-management / corporate-housing / short-term-rental "
         "portfolios; serviced-apartment operators; Airbnb / Vrbo listings; ordinary apartments; student housing; "
         "timeshare and vacation-club inventory; residential-only towers; privately managed residences; member-only "
         "club lodging; on-base military / government lodging; and privately managed units inside hotel-condo "
         "towers. Campgrounds and RV parks are NON_LODGING; a hostel is admitted only when it sells private rooms "
         "to the public under its own name at an exact premises."),
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


def parish_for_postal(postal):
    entry = POSTAL_PARISH.get((postal or "").strip()[:5])
    return entry[0] if entry else ""


def municipality_for_postal(postal, stated_city=""):
    """The REAL municipality a premises at ``postal`` publishes: the stated city when the code carries it, else the
    code's first (principal) municipality. ``new orleans`` is returned only for an Orleans Parish code. "" for a code
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
    NEW ORLEANS WRONG-CITY IDENTITIES = 0: a Kenner, Metairie, Gretna, Harvey or Westwego premises is never written
    as New Orleans."""
    entry = POSTAL_PARISH.get((postal or "").strip()[:5])
    stated = normalise_municipality(stated_city)
    if not entry or not stated:
        return ""
    if stated in entry[1]:
        return ""
    return ("the row states the city %r beside postal code %s, which is %s Parish (%s); the premises publish as %s"
            % (stated_city, (postal or "")[:5], entry[0], " / ".join(entry[1]),
               MUNICIPALITY_DISPLAY.get(entry[1][0], entry[1][0])))


def state_conflict(postal, stated_state):
    """The reason a row's own STATED state contradicts the state its own postal code is in, or ""."""
    s = (stated_state or "").strip().upper()
    s = {"LOUISIANA": "LA", "MISSISSIPPI": "MS"}.get(s, s)
    z = state_for_postal(postal)
    if s and z and s != z:
        return ("the row states the state %s beside postal code %s, which is %s; one of the two facts is wrong and the "
                "row is never re-labelled" % (s, (postal or "")[:5], z))
    return ""


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
        return "OUTSIDE", None, "New Orleans-region postal code %r is claimed by no corridor" % z
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
    print("by class:", json.dumps(report["corridor_count_by_class"]), "by parish:",
          json.dumps(report["corridor_count_by_parish"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
