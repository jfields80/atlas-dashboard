"""PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5, 6, 7 and 8: the Kansas City / Greater Kansas City
market, Missouri AND Kansas.

Built from zero on the CURRENT hardened lineage: the Minneapolis-live release e74dee3b (live lineage commit d5762303,
built_from 239c2836). Current verified live at authoring time = minneapolis-mn deploy 6ac3bfda7b585d009f007620, 42
markets / 3,975 profiles / 4,377 release-index routes / 4,452 served routes, host verified (release_index live-source
--fetch --verify-host). No earlier Kansas City build exists. It is the SECOND Missouri market (st-louis-mo is live and
owns the 630-633 codes) and the FIRST Kansas market; the build refuses to admit any code a registered market already
admits.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Kansas City traveller lodging market -- ONE CROSS-STATE market across the state line, never two markets
merely because State Line Road divides it -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with
FUTURE_STANDALONE markets named inside OUTSIDE) before a single hotel is admitted, so no property is admitted or
refused after the fact to make a number. The order's "STRONG_CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property card)
states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP
is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing
name never admits and never places a property.

MISSOURI AND KANSAS ARE DECIDED BY THE POSTAL CODE, NEVER BY "KANSAS CITY" (PHASE 3)
-----------------------------------------------------------------------------------
Kansas City, MISSOURI and Kansas City, KANSAS are two different cities in two different states, and the chains put
"Kansas City" on hotels in Overland Park, Lenexa, Olathe, Shawnee, Merriam, Leawood, Independence, Lee's Summit,
Liberty, Gladstone, Riverside and Grandview ("Kansas City Overland Park", "Kansas City Airport", "Kansas City North",
"Kansas City-Lenexa", "Kansas City Olathe", "Kansas City Independence"). A Missouri ZIP is 640-658 and a Kansas ZIP is
660-679: every corridor below states its state, every admitted postal code is checked against it at build time, and
a row whose own page states a state its own postal code contradicts is HELD, never re-labelled. Every row keeps its
OWN city, state, ZIP and street: no Kansas hotel is ever written as Missouri and no Missouri hotel as Kansas.
Measured on the map before a single row was admitted: "Sonesta Select Kansas City South Overland Park" stands at
64131, Kansas City, MISSOURI -- the name's "Overland Park" decides nothing.

MCI / NORTHLAND (PHASE 4)
-------------------------
Kansas City International Airport sits 15 miles north-west of downtown in Platte County. The airport-area hotel row
(Tiffany Springs Parkway, NW Prairie View Road, NW 112th Street) is 64153 and is the mci-airport corridor; Zona Rosa
and Barry Road are 64154 / 64151 (northland-north-kansas-city); North Kansas City and Briarcliff are 64116; Platte
City's "KCI Airport North" motels (64079) are OUTSIDE. One premises is one row however many of "Airport", "KCI",
"Northland", "North" and "Kansas City" its marketing carries.

JOHNSON COUNTY (PHASE 5)
------------------------
Overland Park, Lenexa, Olathe, Shawnee, Merriam, Mission, Prairie Village and Leawood are each a city of their own;
none is flattened into Kansas City, Kansas or Kansas City, Missouri. The USPS mailing name "Shawnee Mission" covers
most of north Johnson County's 662xx codes and is a MAILING name, not a city: it decides nothing.

RESIDENCE / APARTMENT / VACATION-RENTAL SAFETY (PHASE 6) AND TIMESHARE (PHASE 7)
-------------------------------------------------------------------------------
Qualifying public hotels are admitted on their own pages. Individual condo units, private residences, Airbnb /
Vrbo units, ordinary apartments, corporate-housing and property-management portfolios, serviced-apartment and
aparthotel operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Lark, Barsala, Zeus, Furnished Finder,
Oakwood / corporate housing, Stay Alfred, Landing), student housing and timeshare / vacation-club inventory (WorldMark,
Club Wyndham, Hilton Grand Vacations, Marriott Vacation Club, Holiday Inn Club Vacations, Bluegreen, Shell Vacations)
are never admitted, even when they accept short stays; a mixed property is admitted only as the exact hotel premises
its public operator sells. Patient and charitable housing (Ronald McDonald House, Hope Lodge, Fisher House) is never
public lodging. Phoenix's lesson is carried as a RULE: a vacation-club resort is TIMESHARE even when its brand lists
it beside its hotels and even when a pet-policy page exists.

MILITARY / GOVERNMENT LODGING
-----------------------------
Fort Leavenworth (66027, IHG Army Hotels' Hoge Hall) and Whiteman AFB (Knob Noster) sell no public lodging and are
OUTSIDE the market anyway; the on-base names are refused wherever they appear (NONPUBLIC_NAMES).

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/kansas_city_mo.json
  launch_packages/pettripfinder/markets/proposed/kansas-city-mo.json
  launch_packages/pettripfinder/markets/reports/kansas_city_mo_geography_001.json
  launch_packages/pettripfinder/markets/reports/kansas_city_mo_corridor_registry_001.json
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

WORK_ORDER = "PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001"
MARKET_ID = "kansas-city-mo"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "kansas_city_mo.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "kansas-city-mo.json")
REPORT_OUT = os.path.join(REPORTS, "kansas_city_mo_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "kansas_city_mo_corridor_registry_001.json")
#: Every REGISTERED market's own document: no postal code any of them admits may be admitted here.
REGISTERED_MARKETS_GLOB = os.path.join(PKG, "markets", "*.json")
AS_OF = "2026-10-05"
#: The PRIMARY state (title generation, the contract's state_code alias). Kansas is a full member state.
STATE_CODE = "MO"
STATE_CODES = ("MO", "KS")


def state_for_postal(postal):
    """The state a postal code belongs to: Missouri 630-658, Kansas 660-679. A row's own page still decides; this is
    the check every stated state is held against, and the fallback when a lane states no state of its own."""
    z = (postal or "").strip()[:3]
    if z.isdigit() and 630 <= int(z) <= 658:
        return "MO"
    if z.isdigit() and 660 <= int(z) <= 679:
        return "KS"
    return ""


#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description, state)
#: The order's MISSOURI / KANSAS CORE areas are CORE, its STRONG CORRIDORS are CORRIDOR and its CAREFUL evaluation
#: areas are FRINGE.
CORRIDORS = [
    # ---------------------------------------------------------------- CORE (Kansas City, Missouri)
    ("downtown-kansas-city", "Downtown Kansas City", "Downtown loop / Power & Light District / River Market / "
     "Library District / Financial District / West Bottoms", "CORE", "kansas city",
     ["64101", "64102", "64105", "64106"],
     "Downtown Kansas City, Missouri: the downtown loop, the Power & Light District and T-Mobile Center, the Library "
     "and Financial districts and the Baltimore / 12th Street hotel row (64105 / 64106), the River Market and "
     "Columbus Park (64106), and the West Bottoms (64101 / 64102). Power & Light and the River Market are OVERLAYS "
     "reported by street, never split codes.", "MO"),
    ("crossroads-crown-center", "Crossroads & Crown Center", "Crossroads Arts District / Crown Center / Union "
     "Station / Kansas City Convention Center south / 18th & Vine / Beacon Hill / Union Hill", "CORE", "kansas city",
     ["64108"],
     "The Crossroads Arts District, Crown Center and its connected hotels, Union Station, the WWI Museum and Memorial "
     "and the 18th & Vine Jazz District edge -- one postal code (64108), reported by street.", "MO"),
    ("plaza-westport", "Country Club Plaza & Westport", "Country Club Plaza / Westport / Southmoreland / Brookside / "
     "Midtown Main Street", "CORE", "kansas city", ["64111", "64112", "64113"],
     "Westport and Midtown's Main Street hotel row (64111), the Country Club Plaza and its Ward Parkway / J.C. Nichols "
     "Parkway hotels (64112) and Brookside (64113). Plaza and Westport are OVERLAYS reported by street.", "MO"),
    ("midtown-east-kansas-city", "Midtown & East Kansas City", "Midtown / Hospital Hill / UMKC / Troost / Northeast / "
     "East Bottoms / Swope Park", "CORE", "kansas city",
     ["64109", "64110", "64120", "64123", "64124", "64125", "64126", "64127", "64128", "64130", "64132"],
     "Midtown east of Main and Hospital Hill (64109 / 64108 edge), UMKC and Rockhill (64110), the Historic Northeast "
     "and the East Bottoms (64120 / 64123 / 64124 / 64125), and the city's east side (64126 / 64127 / 64128 / 64130 / "
     "64132). Inside the city; claimed so no Kansas City, Missouri code is left unaccounted.", "MO"),
    ("mci-airport", "Kansas City International Airport (MCI)", "MCI / KCI Airport / Tiffany Springs / NW Prairie "
     "View Road / NW 112th Street", "CORE", "kansas city", ["64153", "64163", "64164", "64195"],
     "The airport and its own hotel row in Platte County: Tiffany Springs Parkway, NW Prairie View Road and NW 112th "
     "Street (64153), and the airport's surrounding codes (64163 / 64164 / 64195). A hotel MARKETED 'Kansas City "
     "Airport' or 'KCI' whose own code is Platte City (64079) is OUTSIDE.", "MO"),
    ("northland-north-kansas-city", "Northland & North Kansas City", "North Kansas City / Briarcliff / Zona Rosa / "
     "Barry Road / I-29 & I-435 / Antioch / Shoal Creek / Worlds of Fun", "CORE", "kansas city",
     ["64116", "64117", "64151", "64154", "64155", "64156", "64157", "64161", "64165", "64166", "64167"],
     "North Kansas City and Briarcliff (64116), the Worlds of Fun / I-435 & Parvin Road side (64117 / 64161), Zona "
     "Rosa and Barry Road on the I-29 corridor (64154 / 64151), and the Northland's Shoal Creek and Staley codes "
     "(64155 / 64156 / 64157 / 64165 / 64166 / 64167).", "MO"),
    ("independence", "Independence", "Independence / I-70 & Little Blue Parkway / Bass Pro / Truman Home / "
     "Cable Dahmer Arena", "CORE", "independence",
     ["64050", "64051", "64052", "64053", "64054", "64055", "64056", "64057", "64058"],
     "The City of Independence: the I-70 / Little Blue Parkway / Bass Pro hotel cluster (64055 / 64057) and the "
     "historic square and the rest of the city (64050-64058). A hotel titled 'Kansas City Independence' is an "
     "Independence hotel.", "MO"),
    ("lees-summit", "Lee's Summit", "Lee's Summit / US-50 & MO-291 / I-470 / Summit Fair / Unity Village",
     "CORE", "lee's summit", ["64063", "64064", "64065", "64081", "64082", "64086"],
     "The City of Lee's Summit: downtown (64063), the I-470 / US-50 / MO-291 hotel cluster (64064 / 64081 / 64086), "
     "Unity Village (64065) and the south side (64082).", "MO"),
    # ---------------------------------------------------------------- STRONG CORRIDOR (Missouri)
    ("liberty-gladstone", "Liberty & Gladstone", "Liberty / I-35 & MO-152 / Gladstone / North Oak Trafficway",
     "CORRIDOR", "liberty", ["64068", "64069", "64118", "64119", "64158"],
     "The City of Liberty on I-35 (64068 / 64069), the Kansas City-Liberty I-35 & 152 hotel row (64158) and "
     "Gladstone (64118 / 64119, shared with Kansas City and covered whole). STRONG.", "MO"),
    ("blue-springs", "Blue Springs", "Blue Springs / I-70 & MO-7 / Adams Dairy Parkway", "CORRIDOR", "blue springs",
     ["64013", "64014", "64015"],
     "The City of Blue Springs on I-70 (64014 / 64015 and the PO code 64013). STRONG.", "MO"),
    ("raytown-sports-complex", "Raytown & Truman Sports Complex", "Truman Sports Complex / Arrowhead / Kauffman "
     "Stadium / Blue Ridge Cutoff / Raytown", "CORRIDOR", "raytown", ["64129", "64133", "64138"],
     "The Truman Sports Complex hotels on Blue Ridge Cutoff and I-70 (64129 / 64133, Kansas City addresses) and "
     "Raytown (64133 / 64138). STRONG.", "MO"),
    ("south-kansas-city-grandview", "South Kansas City & Grandview", "Ward Parkway south / Bannister / I-435 & "
     "US-71 / Hickman Mills / Red Bridge / Martin City / Grandview", "CORRIDOR", "kansas city",
     ["64114", "64131", "64134", "64136", "64137", "64139", "64145", "64146", "64147", "64149", "64030"],
     "South Kansas City, Missouri -- the State Line / Ward Parkway south side (64114), the Bannister / I-435 & US-71 "
     "hotels (64131 / 64134 / 64137), Red Bridge and Martin City (64145 / 64146 / 64147 / 64149) -- and the City of "
     "Grandview (64030). A hotel titled 'Kansas City South Overland Park' here is a MISSOURI hotel. STRONG.", "MO"),
    # ---------------------------------------------------------------- FRINGE (Missouri, CAREFUL evaluation)
    ("riverside-parkville", "Riverside & Parkville", "Riverside / Argosy / Horizons Parkway / Parkville / Park "
     "University", "FRINGE", "riverside", ["64150", "64152"],
     "The City of Riverside on the Missouri River and I-635 (64150) and Parkville (64152, shared with Kansas City's "
     "Platte Woods side and covered whole). Admitted at FRINGE after CAREFUL evaluation.", "MO"),
    ("grain-valley", "Grain Valley", "Grain Valley / I-70 & Buckner Tarsney Road", "FRINGE", "grain valley",
     ["64029"],
     "The City of Grain Valley on I-70 east of Blue Springs (64029). Admitted at FRINGE after CAREFUL evaluation; "
     "Oak Grove beyond it is refused.", "MO"),
    ("belton-raymore", "Belton & Raymore", "Belton / I-49 & MO-58 / Raymore", "FRINGE", "belton",
     ["64012", "64083"],
     "The City of Belton on I-49 (64012) and Raymore (64083). Admitted at FRINGE after CAREFUL evaluation; "
     "Peculiar and Harrisonville beyond are refused.", "MO"),
    # ---------------------------------------------------------------- CORE (Kansas)
    ("kansas-city-kansas", "Kansas City, Kansas", "Downtown KCK / KU Medical Center / Rosedale / Fairfax / "
     "Argentine / Turner / I-70 & I-635", "CORE", "kansas city",
     ["66101", "66102", "66103", "66104", "66105", "66106", "66112", "66115", "66118", "66160"],
     "Kansas City, KANSAS (Wyandotte County / the Unified Government) east of I-435: downtown KCK and Strawberry Hill "
     "(66101 / 66102), the University of Kansas Medical Center and Rosedale (66103 / 66160), the north and west side "
     "(66104 / 66112), Argentine and Turner (66105 / 66106), Fairfax (66115) and the Kansas River bottoms (66118). "
     "Every row is stated as KANSAS.", "KS"),
    ("village-west-legends", "Village West & The Legends", "Village West / Legends Outlets / Kansas Speedway / "
     "Children's Mercy Park / Hollywood Casino / I-435 & I-70 west", "CORE", "kansas city",
     ["66109", "66111"],
     "Kansas City, KANSAS west of I-435: the Village West / Legends / Kansas Speedway hotel cluster (66111, shared with "
     "Edwardsville and covered whole) and the Parkwood / Piper side (66109). Reported as a Kansas City, Kansas area; "
     "every row is stated as KANSAS.", "KS"),
    ("overland-park", "Overland Park", "Overland Park / College Boulevard / Corporate Woods / Overland Park "
     "Convention Center / Metcalf / Oak Park Mall / 135th Street", "CORE", "overland park",
     ["66204", "66210", "66211", "66212", "66213", "66214", "66221", "66223"],
     "The City of Overland Park: the College Boulevard / Corporate Woods / Overland Park Convention Center hotel "
     "cluster (66210 / 66211, shared with Lenexa and Leawood and covered whole), Metcalf and Oak Park Mall (66212 / "
     "66214 / 66204), and the 119th / 135th Street south side (66213 / 66221 / 66223). A hotel titled 'Kansas City "
     "Overland Park' here is an Overland Park, KANSAS hotel.", "KS"),
    ("lenexa", "Lenexa", "Lenexa / Lenexa City Center / I-435 & 95th / I-35 & 95th / Renner Boulevard",
     "CORE", "lenexa", ["66215", "66219", "66220", "66227"],
     "The City of Lenexa: the I-35 / 95th Street hotel row (66215, shared with Overland Park and covered whole), "
     "Lenexa City Center and the I-435 / Renner Boulevard side (66219 / 66220 / 66227).", "KS"),
    ("olathe", "Olathe", "Olathe / I-35 & 119th / I-35 & Santa Fe / Olathe Medical Center / Great Mall",
     "CORE", "olathe", ["66061", "66062", "66063"],
     "The City of Olathe on I-35: the 119th Street / Strang Line Road hotel cluster (66061 / 66062), Santa Fe Street "
     "and the medical center (66061 / 66062) and the PO code 66063.", "KS"),
    ("shawnee", "Shawnee", "Shawnee / I-435 & Shawnee Mission Parkway / Midland Drive / K-7", "CORE", "shawnee",
     ["66216", "66217", "66218", "66226"],
     "The City of Shawnee: the I-435 / Midland Drive hotel cluster (66217), central Shawnee (66216 / 66218) and the "
     "K-7 west side (66226).", "KS"),
    # ---------------------------------------------------------------- STRONG CORRIDOR (Kansas)
    ("merriam-mission", "Merriam & Mission", "Merriam / I-35 & Shawnee Mission Parkway / Mission / Roeland Park / "
     "Fairway / Westwood", "CORRIDOR", "merriam", ["66202", "66203", "66205"],
     "Merriam's I-35 / Shawnee Mission Parkway hotel cluster (66202 / 66203, the latter shared with Shawnee and "
     "covered whole), Mission, Roeland Park, Fairway and Westwood (66202 / 66205). STRONG.", "KS"),
    ("prairie-village-leawood", "Prairie Village & Leawood", "Prairie Village / Leawood / Town Center Plaza / "
     "Park Place / Mission Farms / I-435 & Nall / Mission Hills", "CORRIDOR", "leawood",
     ["66206", "66207", "66208", "66209", "66224"],
     "Prairie Village and Mission Hills (66207 / 66208), and Leawood -- Town Center Plaza, Park Place and the I-435 "
     "/ Nall / Roe hotel side (66206 / 66209 / 66224; 66209 shared with Overland Park and covered whole). STRONG.",
     "KS"),
    # ---------------------------------------------------------------- FRINGE (Kansas, CAREFUL evaluation)
    ("gardner", "Gardner", "Gardner / I-35 & US-56 / New Century", "FRINGE", "gardner", ["66030"],
     "The City of Gardner on I-35 south-west of Olathe (66030). Admitted at FRINGE after CAREFUL evaluation; Edgerton, "
     "Spring Hill, De Soto and Paola beyond are refused.", "KS"),
    ("bonner-springs-edwardsville", "Bonner Springs & Edwardsville", "Bonner Springs / Azura Amphitheater / "
     "Edwardsville / K-7 & I-70", "FRINGE", "bonner springs", ["66012", "66113"],
     "The City of Bonner Springs (66012) and Edwardsville's own PO code (66113; its 66111 addresses are in "
     "village-west-legends). Admitted at FRINGE after CAREFUL evaluation; Basehor and Tonganoxie beyond are "
     "refused.", "KS"),
]

OUTSIDE = [
    ("Lawrence / University of Kansas / Douglas County", "KS", ["66044", "66045", "66046", "66047", "66049"],
     "DOUGLAS COUNTY; FUTURE_STANDALONE lawrence-ks. The University of Kansas town 40 miles west on I-70 -- a trip of "
     "its own, never absorbed. Refused by name and postal code. A hotel marketed 'Kansas City / Lawrence' is placed "
     "by its code."),
    ("Topeka / Shawnee County, Kansas", "KS", [],
     "SHAWNEE COUNTY KS; FUTURE_STANDALONE topeka-ks. The state capital 60 miles west on I-70. Refused by postal "
     "PREFIX (666, and the 664 region). 'Shawnee' the Johnson County city is NOT Shawnee County."),
    ("St. Joseph, Missouri", "MO", ["64501", "64503", "64504", "64505", "64506", "64507"],
     "BUCHANAN COUNTY; FUTURE_STANDALONE st-joseph-mo. 55 miles north on I-29. Refused by name and postal PREFIX "
     "(645)."),
    ("Columbia / University of Missouri / Boone County", "MO", [],
     "BOONE COUNTY MO; FUTURE_STANDALONE columbia-mo. 125 miles east on I-70. Refused by postal PREFIX (652)."),
    ("Manhattan / Kansas State / Fort Riley / Junction City", "KS", [],
     "RILEY / GEARY COUNTY; FUTURE_STANDALONE manhattan-ks. 120 miles west on I-70. Refused by postal PREFIX (665)."),
    ("Lake of the Ozarks -- Osage Beach, Lake Ozark, Camdenton, Sunrise Beach, Linn Creek", "MO",
     ["65049", "65065", "65020", "65079", "65052", "65072", "65787", "65324", "65326"],
     "CAMDEN / MILLER / MORGAN COUNTY; FUTURE_STANDALONE lake-of-the-ozarks-mo. A resort lake 160 miles south-east. "
     "Refused by name and postal code (and prefix 650)."),
    ("Wichita, Kansas", "KS", [],
     "SEDGWICK COUNTY; FUTURE_STANDALONE wichita-ks. 200 miles south-west. Refused by postal PREFIX (670-672)."),
    ("Springfield / Branson, Missouri", "MO", [],
     "GREENE / TANEY COUNTY; FUTURE_STANDALONE springfield-mo. 160 miles south. Refused by postal PREFIX (656-658)."),
    ("Leavenworth / Lansing / Fort Leavenworth", "KS", ["66048", "66043", "66027"],
     "LEAVENWORTH COUNTY; Fort Leavenworth (66027) is an Army post whose IHG Army Hotels lodging is MILITARY_RESTRICTED. "
     "Not in the order's evaluation list; refused after careful evaluation so the market does not silently absorb "
     "eastern Kansas. Recorded in the boundary audit."),
    ("North / north-east metro beyond the evaluated suburbs -- Platte City (KCI Airport North), Kearney, Smithville, "
     "Excelsior Springs, Weston, Lathrop", "MO", ["64079", "64060", "64089", "64024", "64098", "64492", "64048"],
     "PLATTE / CLAY / CLINTON COUNTY beyond Liberty and the airport. Platte City's motels market themselves 'KCI "
     "Airport North' and are placed by their own code: OUTSIDE. Recorded, never silently absorbed. A founder may move "
     "Platte City on the record."),
    ("East / south metro beyond the evaluated suburbs -- Oak Grove, Odessa, Bates City, Harrisonville, Peculiar, "
     "Pleasant Hill, Greenwood, Warrensburg, Richmond", "MO",
     ["64075", "64076", "64011", "64701", "64078", "64080", "64034", "64093", "64085"],
     "JACKSON COUNTY east / CASS / JOHNSON / RAY COUNTY beyond Blue Springs, Grain Valley, Lee's Summit and Belton. "
     "Refused after careful evaluation; recorded in the boundary audit."),
    ("Johnson / Wyandotte / Miami County, Kansas beyond the evaluated suburbs -- De Soto, Spring Hill, Edgerton, "
     "Basehor, Tonganoxie, Paola, Louisburg, Ottawa, Atchison", "KS",
     ["66018", "66083", "66021", "66007", "66086", "66071", "66053", "66067", "66002", "66064"],
     "Beyond Olathe, Gardner, Bonner Springs and Edwardsville. Refused after careful evaluation; recorded in the "
     "boundary audit, never silently absorbed."),
    ("St. Louis, Missouri (the live st-louis-mo market)", "MO", [],
     "Owned by the live st-louis-mo market. Refused by postal PREFIX (630-633) -- this market never admits a code a "
     "registered market owns."),
    ("Greater Missouri, greater Kansas and out of state", "--", [],
     "Every other Missouri and Kansas postal prefix and every code outside Missouri and Kansas is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("630", "St. Louis region (live st-louis-mo)", "st-louis-mo"),
    ("631", "St. Louis (live st-louis-mo)", "st-louis-mo"),
    ("633", "St. Charles / St. Louis region (live st-louis-mo)", "st-louis-mo"),
    ("634", "Hannibal / north-east Missouri", ""),
    ("635", "Kirksville / north-east Missouri", ""),
    ("636", "Flat River / east-central Missouri", ""),
    ("637", "Cape Girardeau / south-east Missouri", ""),
    ("638", "Sikeston / south-east Missouri", ""),
    ("639", "Poplar Bluff / south-east Missouri", ""),
    ("644", "St. Joseph region / north-west Missouri", "st-joseph-mo"),
    ("645", "St. Joseph", "st-joseph-mo"),
    ("646", "Chillicothe / north-central Missouri", ""),
    ("647", "Harrisonville / west-central Missouri", ""),
    ("648", "Joplin / south-west Missouri", ""),
    ("650", "Jefferson City region / Lake of the Ozarks", "lake-of-the-ozarks-mo"),
    ("651", "Jefferson City", ""),
    ("652", "Columbia / mid-Missouri", "columbia-mo"),
    ("653", "Sedalia / west-central Missouri", ""),
    ("654", "Rolla / south-central Missouri", ""),
    ("655", "Rolla / south-central Missouri", ""),
    ("656", "Springfield region", "springfield-mo"),
    ("657", "Springfield region", "springfield-mo"),
    ("658", "Springfield", "springfield-mo"),
    ("664", "Topeka region / north-east Kansas", "topeka-ks"),
    ("665", "Manhattan / Junction City / north-central Kansas", "manhattan-ks"),
    ("666", "Topeka", "topeka-ks"),
    ("667", "Fort Scott / south-east Kansas", ""),
    ("668", "Emporia / east-central Kansas", ""),
    ("669", "Concordia / north-central Kansas", ""),
    ("670", "Wichita region", "wichita-ks"),
    ("671", "Wichita region", "wichita-ks"),
    ("672", "Wichita", "wichita-ks"),
    ("673", "Independence KS / south-east Kansas", ""),
    ("674", "Salina / central Kansas", ""),
    ("675", "Hutchinson / central Kansas", ""),
    ("676", "Hays / west-central Kansas", ""),
    ("677", "Colby / north-west Kansas", ""),
    ("678", "Dodge City / south-west Kansas", ""),
    ("679", "Liberal / south-west Kansas", ""),
]

#: Greater Kansas City's own postal prefixes. A code under one of these that no corridor claims and no OUTSIDE row
#: names is an UNCLAIMED metro / regional code -- refused, and named in the boundary audit so it is visible, never
#: silently dropped.
VALLEY_PREFIXES = ("640", "641", "660", "661", "662")

ADMITTED_COUNTIES = {"jackson mo (kansas city, independence, lee's summit, blue springs, raytown, grandview, grain "
                     "valley; oak grove refused)",
                     "clay mo (kansas city north, north kansas city, gladstone, liberty; kearney, smithville and "
                     "excelsior springs refused)",
                     "platte mo (mci airport, kansas city's platte county codes, riverside, parkville; platte city and "
                     "weston refused)",
                     "cass mo (belton, raymore; peculiar and harrisonville refused)",
                     "wyandotte ks (kansas city ks, village west / the legends, bonner springs, edwardsville)",
                     "johnson ks (overland park, lenexa, olathe, shawnee, merriam, mission, prairie village, leawood, "
                     "gardner; de soto, spring hill and edgerton refused)"}
OBSERVED_COUNTIES = OrderedDict([
    ("douglas ks (lawrence)", "lawrence-ks"),
    ("shawnee ks (topeka)", "topeka-ks"),
    ("buchanan mo (st. joseph)", "st-joseph-mo"),
    ("boone mo (columbia)", "columbia-mo"),
    ("riley / geary ks (manhattan, junction city, fort riley)", "manhattan-ks"),
    ("camden / miller / morgan mo (lake of the ozarks)", "lake-of-the-ozarks-mo"),
    ("sedgwick ks (wichita)", "wichita-ks"),
    ("greene / taney mo (springfield, branson)", "springfield-mo"),
    ("leavenworth ks (leavenworth, lansing, fort leavenworth)", "(none -- refused after careful evaluation)"),
    ("platte / clay / clinton mo beyond the airport and liberty", "(none -- refused after careful evaluation)"),
    ("jackson east / cass south / johnson mo / ray mo", "(none -- refused after careful evaluation)"),
    ("miami / franklin / atchison ks", "(none -- refused, keep separate)"),
])

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("state_line", OrderedDict([
        ("ruling", "ONE MARKET ACROSS THE STATE LINE, TWO STATES PRESERVED. Kansas City, Missouri and Kansas City, "
                   "Kansas are both admitted, as are the Johnson County cities; every row keeps the state its own "
                   "postal code and its own page state. A row whose page states a state its postal code contradicts "
                   "is HELD."),
    ])),
    ("jackson mo", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. Kansas City, Independence, Lee's Summit, Blue Springs, Raytown, Grandview and "
                   "Grain Valley are admitted; Oak Grove and the east county are refused."),
    ])),
    ("clay / platte mo", OrderedDict([
        ("ruling", "ADMITTED INSIDE THE NORTHLAND. Kansas City north of the river, North Kansas City, Gladstone, "
                   "Liberty, the airport, Riverside and Parkville are admitted; Platte City, Weston, Kearney, "
                   "Smithville and Excelsior Springs are refused."),
    ])),
    ("cass mo", OrderedDict([
        ("ruling", "ADMITTED ONLY AT BELTON / RAYMORE. Peculiar, Harrisonville and Pleasant Hill are refused."),
    ])),
    ("wyandotte ks", OrderedDict([
        ("ruling", "ADMITTED. Kansas City, Kansas (east and Village West), Bonner Springs and Edwardsville."),
    ])),
    ("johnson ks", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. Overland Park, Lenexa, Olathe, Shawnee, Merriam, Mission, Roeland Park, "
                   "Fairway, Westwood, Prairie Village, Mission Hills, Leawood and Gardner are admitted; De Soto, "
                   "Spring Hill and Edgerton are refused."),
    ])),
    ("douglas / shawnee / leavenworth ks; buchanan / boone mo", OrderedDict([
        ("ruling", "REFUSED. Lawrence, Topeka, Leavenworth, St. Joseph and Columbia are not absorbed (FUTURE_STANDALONE "
                   "lawrence-ks, topeka-ks, st-joseph-mo, columbia-mo)."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / patient / member
#: only). A normalised-name substring match; the census row keeps its reason.
NONPUBLIC_NAMES = {
    "navy lodge": "Navy Lodge on-base lodging -- MILITARY_RESTRICTED",
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- restricted to authorised DoD travellers; MILITARY_RESTRICTED",
    "hoge hall": "Fort Leavenworth's IHG Army Hotels Hoge Hall -- MILITARY_RESTRICTED",
    "fort leavenworth": "Fort Leavenworth on-post lodging -- MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "air national guard": "Air National Guard base lodging -- MILITARY_RESTRICTED",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "hope lodge": "American Cancer Society Hope Lodge -- patient lodging, not public lodging",
    "family housing": "patient-family housing -- not public lodging",
}

#: Military postal codes inside the admitted partition. None: Fort Leavenworth (66027) and Whiteman AFB (65305) are
#: outside it, and no admitted code is an installation's own.
MILITARY_POSTAL_CODES = OrderedDict()

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-kansas-city", "Kansas City", "Downtown / Power & Light / River Market", 39.1000, -94.5830, 1800, True),
    ("crossroads-crown-center", "Kansas City", "Crossroads / Crown Center / Union Station", 39.0850, -94.5800, 1500,
     True),
    ("plaza-westport", "Kansas City", "Country Club Plaza / Westport / Brookside", 39.0400, -94.5900, 2800, True),
    ("midtown-east-kansas-city", "Kansas City", "Midtown / UMKC / Northeast / East side", 39.0600, -94.5400, 6000,
     True),
    ("mci-airport", "Kansas City", "MCI / KCI Airport / Tiffany Springs", 39.2900, -94.7000, 5000, True),
    ("northland-north-kansas-city", "Kansas City", "North Kansas City / Zona Rosa / Northland", 39.2100, -94.5900,
     9000, True),
    ("independence", "Independence", "Independence", 39.0700, -94.3900, 7000, True),
    ("lees-summit", "Lee's Summit", "Lee's Summit", 38.9200, -94.3800, 7000, True),
    ("liberty-gladstone", "Liberty", "Liberty / Gladstone", 39.2200, -94.4800, 6500, True),
    ("blue-springs", "Blue Springs", "Blue Springs", 39.0200, -94.2700, 5000, True),
    ("raytown-sports-complex", "Raytown", "Truman Sports Complex / Raytown", 39.0300, -94.4800, 4000, True),
    ("south-kansas-city-grandview", "Kansas City", "South Kansas City / Grandview", 38.9200, -94.5400, 7500, True),
    ("riverside-parkville", "Riverside", "Riverside / Parkville", 39.1700, -94.6600, 4500, True),
    ("grain-valley", "Grain Valley", "Grain Valley", 39.0150, -94.2000, 3000, True),
    ("belton-raymore", "Belton", "Belton / Raymore", 38.8100, -94.5200, 5000, True),
    ("kansas-city-kansas", "Kansas City", "Kansas City, Kansas / KU Medical Center", 39.1050, -94.6800, 7000, True),
    ("village-west-legends", "Kansas City", "Village West / The Legends / Kansas Speedway", 39.1200, -94.8200, 4000,
     True),
    ("overland-park", "Overland Park", "Overland Park / College Blvd / Corporate Woods", 38.9300, -94.6800, 7500,
     True),
    ("lenexa", "Lenexa", "Lenexa", 38.9600, -94.7600, 5000, True),
    ("olathe", "Olathe", "Olathe", 38.8800, -94.8000, 7000, True),
    ("shawnee", "Shawnee", "Shawnee", 39.0100, -94.7600, 5000, True),
    ("merriam-mission", "Merriam", "Merriam / Mission / Roeland Park", 39.0200, -94.6800, 3500, True),
    ("prairie-village-leawood", "Leawood", "Prairie Village / Leawood", 38.9300, -94.6200, 5500, True),
    ("gardner", "Gardner", "Gardner", 38.8100, -94.9300, 3000, True),
    ("bonner-springs-edwardsville", "Bonner Springs", "Bonner Springs / Edwardsville", 39.0800, -94.9000, 4000, True),
    ("obs-lawrence", "Lawrence", "Lawrence, Kansas -- OBSERVATION ONLY", 38.9600, -95.2400, 12000, False),
    ("obs-topeka", "Topeka", "Topeka, Kansas -- OBSERVATION ONLY", 39.0500, -95.6900, 15000, False),
    ("obs-st-joseph", "St. Joseph", "St. Joseph, Missouri -- OBSERVATION ONLY", 39.7700, -94.8500, 12000, False),
    ("obs-columbia", "Columbia", "Columbia, Missouri -- OBSERVATION ONLY", 38.9500, -92.3300, 12000, False),
    ("obs-manhattan", "Manhattan", "Manhattan / Junction City, Kansas -- OBSERVATION ONLY", 39.1100, -96.7000, 20000,
     False),
    ("obs-lake-ozarks", "Osage Beach", "Lake of the Ozarks -- OBSERVATION ONLY", 38.1500, -92.7000, 25000, False),
    ("obs-wichita", "Wichita", "Wichita, Kansas -- OBSERVATION ONLY", 37.6900, -97.3400, 20000, False),
    ("obs-springfield", "Springfield", "Springfield / Branson, Missouri -- OBSERVATION ONLY", 37.1000, -93.2900,
     25000, False),
    ("obs-leavenworth", "Leavenworth", "Leavenworth / Lansing -- OBSERVATION ONLY", 39.3100, -94.9200, 8000, False),
    ("obs-north-metro", "Platte City", "Platte City / Kearney / Excelsior Springs -- OBSERVATION ONLY", 39.3500,
     -94.5000, 20000, False),
    ("obs-east-south-metro", "Harrisonville", "Oak Grove / Harrisonville / Pleasant Hill -- OBSERVATION ONLY",
     38.8500, -94.2000, 20000, False),
]

#: The observation box. It reaches west past Lawrence, Topeka and Manhattan, north to St. Joseph, east to Columbia
#: and the Lake of the Ozarks and south to Wichita and Springfield, so the census counts what it refuses.
BOUNDS = {"min_lat": 37.00, "max_lat": 40.20, "min_lng": -97.60, "max_lng": -92.10}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Power & Light District", 39.0975, -94.5820, 0.45),
    ("River Market", 39.1100, -94.5830, 0.60),
    ("Downtown Kansas City", 39.1000, -94.5830, 1.40),
    ("Crossroads Arts District", 39.0900, -94.5800, 0.70),
    ("Crown Center / Union Station", 39.0820, -94.5820, 0.70),
    ("Westport", 39.0530, -94.5920, 0.70),
    ("Country Club Plaza", 39.0410, -94.5930, 0.80),
    ("Midtown", 39.0620, -94.5800, 1.60),
    ("Kansas City International Airport (MCI)", 39.2950, -94.7100, 4.00),
    ("Zona Rosa / Barry Road", 39.2430, -94.6600, 2.00),
    ("North Kansas City / Briarcliff", 39.1420, -94.5750, 2.20),
    ("Northland", 39.2200, -94.5800, 6.00),
    ("Kansas City, Kansas / KU Medical Center", 39.0900, -94.6600, 5.00),
    ("Village West / The Legends", 39.1220, -94.8250, 2.50),
    ("College Boulevard / Corporate Woods", 38.9270, -94.6750, 2.50),
    ("Overland Park", 38.9300, -94.6800, 5.00),
    ("Lenexa", 38.9600, -94.7700, 4.00),
    ("Olathe", 38.8800, -94.8000, 5.00),
    ("Shawnee", 39.0100, -94.7700, 4.00),
    ("Merriam / Mission", 39.0200, -94.6750, 2.50),
    ("Prairie Village / Leawood", 38.9300, -94.6200, 4.00),
    ("Independence", 39.0700, -94.3900, 5.50),
    ("Lee's Summit", 38.9200, -94.3800, 5.50),
    ("Liberty / Gladstone", 39.2200, -94.4800, 5.00),
    ("Blue Springs", 39.0200, -94.2700, 4.00),
    ("Truman Sports Complex / Raytown", 39.0350, -94.4850, 3.00),
    ("South Kansas City / Grandview", 38.9200, -94.5400, 6.00),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Kansas City International Airport (MCI)", re.compile(r"\btiffany springs\b|\bnw prairie view\b|"
                                                           r"\bnw 112th\b|\binternational cir", re.I)),
    ("Crown Center / Union Station", re.compile(r"\b(e|w) pershing\b|\bpershing (rd|road)\b|\bmcgee st\b(?=.*64108)|"
                                                r"\bgrand (blvd|boulevard)\b(?=.*64108)", re.I)),
    ("Country Club Plaza", re.compile(r"\bward (pkwy|parkway)\b(?=.*6411[12])|\bj ?c nichols\b|\bnichols (pkwy|"
                                      r"parkway)\b|\bw 4[6-8]th\b(?=.*6411[12])", re.I)),
    ("Westport", re.compile(r"\bwestport (rd|road)\b|\bpennsylvania ave\b(?=.*64111)|\bbroadway\b(?=.*64111)", re.I)),
    ("River Market", re.compile(r"\b(e|w) (2nd|3rd|4th|5th) st\b(?=.*6410[56])|\bdelaware st\b(?=.*64105)", re.I)),
    ("Zona Rosa / Barry Road", re.compile(r"\bn dixson\b|\bnw barry (rd|road)\b|\bzona rosa\b", re.I)),
    ("Village West / The Legends", re.compile(r"\bvillage west\b|\bcabela\b|\bspeedway\b|\blegends\b(?=.*66111)",
                                              re.I)),
    ("College Boulevard / Corporate Woods", re.compile(r"\bcollege (blvd|boulevard)\b(?=.*662(10|11|15))|"
                                                       r"\bcorporate woods\b", re.I)),
    ("Truman Sports Complex / Raytown", re.compile(r"\bblue ridge cut ?off\b|\bstadium dr\b", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-kansas-city": "Downtown Kansas City",
    "crossroads-crown-center": "Crossroads Arts District",
    "plaza-westport": "Country Club Plaza",
    "midtown-east-kansas-city": "Midtown",
    "mci-airport": "Kansas City International Airport (MCI)",
    "northland-north-kansas-city": "Northland",
    "independence": "Independence",
    "lees-summit": "Lee's Summit",
    "liberty-gladstone": "Liberty / Gladstone",
    "blue-springs": "Blue Springs",
    "raytown-sports-complex": "Truman Sports Complex / Raytown",
    "south-kansas-city-grandview": "South Kansas City / Grandview",
    "riverside-parkville": "Northland",
    "grain-valley": "Blue Springs",
    "belton-raymore": "South Kansas City / Grandview",
    "kansas-city-kansas": "Kansas City, Kansas / KU Medical Center",
    "village-west-legends": "Village West / The Legends",
    "overland-park": "Overland Park",
    "lenexa": "Lenexa",
    "olathe": "Olathe",
    "shawnee": "Shawnee",
    "merriam-mission": "Merriam / Mission",
    "prairie-village-leawood": "Prairie Village / Leawood",
    "gardner": "Olathe",
    "bonner-springs-edwardsville": "Village West / The Legends",
}

#: The order's MISSOURI CORE / KANSAS CORE / STRONG / CAREFUL / KEEP-SEPARATE evaluation list, each classified.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Kansas City MO", "ADMITTED (CORE, downtown-kansas-city, 64101 / 64102 / 64105 / 64106). MISSOURI CORE."),
    ("Power & Light", "ADMITTED (CORE, downtown-kansas-city, 64105 / 64106) -- reported as an overlay. MISSOURI CORE."),
    ("Crossroads", "ADMITTED (CORE, crossroads-crown-center, 64108) -- reported as an overlay. MISSOURI CORE."),
    ("Crown Center", "ADMITTED (CORE, crossroads-crown-center, 64108) -- reported as an overlay. MISSOURI CORE."),
    ("Country Club Plaza", "ADMITTED (CORE, plaza-westport, 64112 / 64111) -- reported as an overlay. MISSOURI CORE."),
    ("Westport", "ADMITTED (CORE, plaza-westport, 64111) -- reported as an overlay. MISSOURI CORE."),
    ("Midtown", "ADMITTED (CORE, midtown-east-kansas-city, 64109 / 64110 and the east-side codes; Midtown's Main "
                "Street hotel row is 64111 in plaza-westport). MISSOURI CORE."),
    ("Kansas City International Airport / MCI", "ADMITTED (CORE, mci-airport, 64153 / 64163 / 64164 / 64195). "
                                                "MISSOURI CORE."),
    ("Northland", "ADMITTED (CORE, northland-north-kansas-city, 64151 / 64154-64157 / 64161 / 64165-64167). "
                  "MISSOURI CORE."),
    ("North Kansas City", "ADMITTED (CORE, northland-north-kansas-city, 64116). MISSOURI CORE."),
    ("Independence", "ADMITTED (CORE, independence, 64050-64058). MISSOURI CORE."),
    ("Lee's Summit", "ADMITTED (CORE, lees-summit, 64063 / 64064 / 64065 / 64081 / 64082 / 64086). MISSOURI CORE."),
    ("Kansas City KS", "ADMITTED (CORE, kansas-city-kansas 66101-66106 / 66112 / 66115 / 66118 / 66160, and "
                       "village-west-legends 66109 / 66111). KANSAS CORE."),
    ("Overland Park", "ADMITTED (CORE, overland-park, 66204 / 66210-66214 / 66221 / 66223). KANSAS CORE."),
    ("Lenexa", "ADMITTED (CORE, lenexa, 66215 / 66219 / 66220 / 66227). KANSAS CORE."),
    ("Olathe", "ADMITTED (CORE, olathe, 66061 / 66062 / 66063). KANSAS CORE."),
    ("Shawnee", "ADMITTED (CORE, shawnee, 66216 / 66217 / 66218 / 66226). KANSAS CORE."),
    ("Liberty", "ADMITTED (STRONG CORRIDOR, liberty-gladstone, 64068 / 64069 / 64158). MISSOURI STRONG."),
    ("Gladstone", "ADMITTED (STRONG CORRIDOR, liberty-gladstone, 64118 / 64119). MISSOURI STRONG."),
    ("Blue Springs", "ADMITTED (STRONG CORRIDOR, blue-springs, 64013 / 64014 / 64015). MISSOURI STRONG."),
    ("Raytown", "ADMITTED (STRONG CORRIDOR, raytown-sports-complex, 64133 / 64138; the sports complex 64129). "
                "MISSOURI STRONG."),
    ("Grandview", "ADMITTED (STRONG CORRIDOR, south-kansas-city-grandview, 64030). MISSOURI STRONG."),
    ("Merriam", "ADMITTED (STRONG CORRIDOR, merriam-mission, 66202 / 66203). KANSAS STRONG."),
    ("Mission", "ADMITTED (STRONG CORRIDOR, merriam-mission, 66202 / 66205). KANSAS STRONG."),
    ("Prairie Village", "ADMITTED (STRONG CORRIDOR, prairie-village-leawood, 66207 / 66208). KANSAS STRONG."),
    ("Leawood", "ADMITTED (STRONG CORRIDOR, prairie-village-leawood, 66206 / 66209 / 66224; its 66211 College "
                "Boulevard hotels sit in overland-park's shared code, covered whole). KANSAS STRONG."),
    ("Parkville MO", "ADMITTED (FRINGE, riverside-parkville, 64152). CAREFUL."),
    ("Riverside MO", "ADMITTED (FRINGE, riverside-parkville, 64150). CAREFUL."),
    ("Grain Valley MO", "ADMITTED (FRINGE, grain-valley, 64029). CAREFUL."),
    ("Belton MO", "ADMITTED (FRINGE, belton-raymore, 64012). CAREFUL."),
    ("Raymore MO", "ADMITTED (FRINGE, belton-raymore, 64083). CAREFUL."),
    ("Gardner KS", "ADMITTED (FRINGE, gardner, 66030). CAREFUL."),
    ("Bonner Springs KS", "ADMITTED (FRINGE, bonner-springs-edwardsville, 66012). CAREFUL."),
    ("Edwardsville KS", "ADMITTED (FRINGE, bonner-springs-edwardsville, 66113; its 66111 addresses sit in "
                        "village-west-legends, covered whole). CAREFUL."),
    ("Lawrence KS", "OUTSIDE -- FUTURE_STANDALONE lawrence-ks; refused by name and postal code. KEEP SEPARATE."),
    ("Topeka KS", "OUTSIDE -- FUTURE_STANDALONE topeka-ks; refused by prefix 664 / 666. KEEP SEPARATE."),
    ("St. Joseph MO", "OUTSIDE -- FUTURE_STANDALONE st-joseph-mo; refused by prefix 644 / 645. KEEP SEPARATE."),
    ("Columbia MO", "OUTSIDE -- FUTURE_STANDALONE columbia-mo; refused by prefix 652. KEEP SEPARATE."),
    ("Manhattan KS", "OUTSIDE -- FUTURE_STANDALONE manhattan-ks; refused by prefix 665. KEEP SEPARATE."),
    ("Lake of the Ozarks", "OUTSIDE -- FUTURE_STANDALONE lake-of-the-ozarks-mo; refused by name, postal code and "
                           "prefix 650. KEEP SEPARATE."),
    ("Wichita", "OUTSIDE -- FUTURE_STANDALONE wichita-ks; refused by prefix 670-672. KEEP SEPARATE."),
    ("Springfield MO", "OUTSIDE -- FUTURE_STANDALONE springfield-mo; refused by prefix 656-658. KEEP SEPARATE."),
    ("Platte City / Kearney / Leavenworth / Oak Grove / Harrisonville / De Soto / Spring Hill",
     "OUTSIDE -- refused after careful evaluation by name and postal code, recorded in the boundary audit."),
])

#: The MCI / Northland ruling (Phase 4), stated once.
MCI_NORTHLAND_EVALUATION = OrderedDict([
    ("mci_airport", "The airport's own hotel row (Tiffany Springs Parkway, NW Prairie View Road, NW 112th Street) is "
                    "64153, the mci-airport corridor. A hotel marketed 'Kansas City Airport' or 'KCI' is placed by its "
                    "own code: Platte City (64079) is OUTSIDE; Riverside (64150) and Zona Rosa (64154) are where their "
                    "codes put them."),
    ("northland", "North of the Missouri River inside Kansas City and North Kansas City: Briarcliff and North Kansas "
                  "City (64116), Worlds of Fun / Parvin Road (64117 / 64161), Zona Rosa and Barry Road (64154 / "
                  "64151) -- the northland-north-kansas-city corridor."),
    ("liberty_gladstone", "Liberty (64068) and Gladstone (64118 / 64119), and the Kansas City-Liberty I-35 & 152 row "
                          "(64158), are a STRONG corridor of their own."),
    ("one_premises_one_row", "A property is one row however many of 'Airport', 'KCI', 'Northland', 'North' and 'Kansas "
                             "City' its marketing carries; identity is its own street address and brand property "
                             "code."),
])

#: The Johnson County ruling (Phase 5).
JOHNSON_COUNTY_EVALUATION = OrderedDict([
    ("cities_never_flattened", "Overland Park, Lenexa, Olathe, Shawnee, Merriam, Mission, Prairie Village and Leawood "
                               "each keep their own municipality; none is written as Kansas City, Kansas or Kansas "
                               "City, Missouri."),
    ("shawnee_mission", "'Shawnee Mission' is a USPS mailing name covering most of north Johnson County. It is never "
                        "a municipality and never decides a corridor; the postal code does."),
    ("shared_codes", "66210 (Overland Park / Lenexa), 66211 (Overland Park / Leawood), 66215 (Lenexa / Overland "
                     "Park), 66209 (Leawood / Overland Park) and 66203 (Merriam / Shawnee) are covered whole by one "
                     "corridor each; the row keeps the city its own page states."),
    ("missouri_overland_park_trap", "A hotel marketed 'Kansas City South Overland Park' or 'Overland Park' whose own "
                                    "code is 64131 / 64114 is a Kansas City, MISSOURI hotel, placed by its code."),
])

#: The cross-state ruling (consumers read it under the inherited name HILL_COUNTRY_RULING).
KANSAS_CITY_RULING = OrderedDict([
    ("classification", "The metro-continuous Kansas City core is admitted on both sides of the state line -- downtown, "
                       "Crossroads / Crown Center, Plaza / Westport, Midtown / east Kansas City, MCI, the Northland, "
                       "Independence and Lee's Summit in Missouri, Kansas City Kansas, Village West, Overland Park, "
                       "Lenexa, Olathe and Shawnee in Kansas CORE; Liberty / Gladstone, Blue Springs, Raytown, south "
                       "Kansas City / Grandview, Merriam / Mission and Prairie Village / Leawood STRONG CORRIDOR; "
                       "Riverside / Parkville, Grain Valley, Belton / Raymore, Gardner and Bonner Springs / "
                       "Edwardsville FRINGE. Lawrence, Topeka, St. Joseph, Columbia, Manhattan, the Lake of the Ozarks, "
                       "Wichita and Springfield are OUTSIDE, and so are Platte City, Kearney, Leavenworth, Oak Grove "
                       "and Harrisonville."),
    ("a_marketing_phrase_admits_nothing", "'Kansas City Airport', 'KCI', 'Kansas City North', 'Kansas City South', "
                                          "'Kansas City Overland Park', 'Kansas City-Lenexa', 'Kansas City Olathe', "
                                          "'Kansas City Independence', 'Kansas City Plaza' and 'Kansas City "
                                          "Downtown' are marketing. The property's own postal code decides."),
    ("actual_location", "Decided by the property's own postal code on its own page; the state by that code."),
    ("drive_market_relationship", "MCI, the downtown loop, Crown Center, the Plaza, the Northland, Johnson County's "
                                  "College Boulevard and the Legends are where Kansas City travellers sleep; "
                                  "Lawrence, Topeka, St. Joseph and the Lake of the Ozarks are trips of their own."),
    ("traveller_intent", "Convention (Kansas City Convention Center, Overland Park Convention Center), arena and "
                         "stadium (T-Mobile Center, Arrowhead, Kauffman, Children's Mercy Park, Kansas Speedway), "
                         "medical (KU Medical Center, Saint Luke's, Children's Mercy, Truman Medical), university "
                         "(UMKC, KU Med), corporate (Cerner / Oracle Health, Garmin, Hallmark, H&R Block, T-Mobile, "
                         "Burns & McDonnell), the Plaza, Crown Center, Union Station, the Legends and MCI demand is "
                         "Kansas City intent; the University of Kansas, the state capitals and the Ozarks are not."),
    ("metro_continuity", "Continuous development runs inside the I-435 loop and along I-29, I-35, I-49, I-70 and "
                         "US-50 to the suburbs the order names; this registry stops there."),
    ("corridor_support", "Every admitted edge code is in a named corridor so its count is visible and a founder can "
                         "move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE lawrence-ks, topeka-ks, st-joseph-mo, columbia-mo, manhattan-ks, "
                      "lake-of-the-ozarks-mo, wichita-ks and springfield-mo."),
])
HILL_COUNTRY_RULING = KANSAS_CITY_RULING
TWIN_CITIES_RULING = KANSAS_CITY_RULING
#: Inherited consumer names (the Portland / Minneapolis helpers' cross-border evaluation slots): Kansas City's
#: equivalent is the MCI / Northland evaluation.
VANCOUVER_EVALUATION = MCI_NORTHLAND_EVALUATION
MSP_BLOOMINGTON_EVALUATION = MCI_NORTHLAND_EVALUATION

STRUCTURE_TEST = OrderedDict([
    ("A. Is Kansas City one market, or two?",
     "ONE market, kansas-city-mo, covering both Kansas Cities and the contiguous suburbs the order evaluates on both "
     "sides of the state line -- one commercial airport (MCI), one I-35 / I-70 / I-435 / I-29 / I-49 road system."),
    ("B. Missouri and Kansas are NOT flattened",
     "Every corridor states its state, every admitted code is checked against the state's postal prefixes, and every "
     "row keeps its own city and state. Kansas City, Kansas is never written as Kansas City, Missouri, and the "
     "reverse."),
    ("C. MCI", "Only the airport's own codes (64153 / 64163 / 64164 / 64195) are mci-airport; 'Airport' hotels "
               "elsewhere are placed by their own code (MCI_NORTHLAND_EVALUATION)."),
    ("D. Johnson County", "Each city is its own municipality (JOHNSON_COUNTY_EVALUATION)."),
    ("E. Power & Light / River Market / Crossroads / Crown Center / Plaza / Westport", "Overlays of their corridor, "
                                                                                       "never split codes."),
    ("F. Lawrence", "OUTSIDE -- FUTURE_STANDALONE lawrence-ks."),
    ("G. Topeka", "OUTSIDE -- FUTURE_STANDALONE topeka-ks."),
    ("H. St. Joseph", "OUTSIDE -- FUTURE_STANDALONE st-joseph-mo."),
    ("I. Columbia", "OUTSIDE -- FUTURE_STANDALONE columbia-mo."),
    ("J. Manhattan", "OUTSIDE -- FUTURE_STANDALONE manhattan-ks."),
    ("K. Lake of the Ozarks / Wichita / Springfield", "OUTSIDE -- FUTURE_STANDALONE each."),
    ("L. Platte City / Kearney / Leavenworth / Oak Grove / Harrisonville", "OUTSIDE -- not absorbed."),
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
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. Kansas City's "
     "specific exposures: the downtown loop, Crossroads and Plaza apartment towers with furnished short-stay units, "
     "the serviced-apartment and aparthotel operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Landing), "
     "corporate-housing portfolios, UMKC and KU Med student housing, Club Wyndham / WorldMark vacation-ownership "
     "inventory and the Airbnb / Vrbo inventory."),
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
     "Patient-family housing (the Ronald McDonald Houses, Hope Lodge), charitable family lodging (Fisher House) and "
     "on-base military lodging are never public hotels and are never admitted."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("64105", ["Downtown loop", "Power & Light District", "Library District", "River Market (west)"]),
    ("64106", ["Power & Light District (east)", "River Market", "Columbus Park", "East Village"]),
    ("64108", ["Crossroads Arts District", "Crown Center", "Union Station", "18th & Vine (west)", "Union Hill"]),
    ("64111", ["Westport", "Midtown Main Street"]),
    ("64112", ["Country Club Plaza"]),
    ("64119", ["Gladstone", "Kansas City (Antioch)"]),
    ("64133", ["Raytown", "Kansas City (Truman Sports Complex)"]),
    ("64152", ["Parkville", "Kansas City (Platte Woods)"]),
    ("66111", ["Kansas City KS (Village West)", "Edwardsville"]),
    ("66203", ["Merriam", "Shawnee"]),
    ("66209", ["Leawood", "Overland Park"]),
    ("66210", ["Overland Park", "Lenexa"]),
    ("66211", ["Overland Park", "Leawood"]),
    ("66215", ["Lenexa", "Overland Park"]),
    ("66202", ["Merriam", "Mission", "Overland Park (north)"]),
])

FUTURE_MARKETS = OrderedDict([
    ("lawrence-ks", "Lawrence / the University of Kansas -- 40 miles west on I-70."),
    ("topeka-ks", "Topeka -- 60 miles west on I-70."),
    ("st-joseph-mo", "St. Joseph -- 55 miles north on I-29."),
    ("columbia-mo", "Columbia / the University of Missouri -- 125 miles east on I-70."),
    ("manhattan-ks", "Manhattan / Kansas State / Fort Riley -- 120 miles west on I-70."),
    ("lake-of-the-ozarks-mo", "The Lake of the Ozarks -- 160 miles south-east."),
    ("wichita-ks", "Wichita -- 200 miles south-west on I-35."),
    ("springfield-mo", "Springfield / Branson -- 160 miles south."),
])

#: Markets that are ALREADY LIVE. st-louis-mo shares the STATE of Missouri (never a postal code: it owns 630-633,
#: refused here by prefix). Exposures are otherwise shared NAMES only: Independence, OHIO (cleveland-akron-canton-oh's
#: region); Liberty Township, OHIO (the Cincinnati / Dayton regions); Riverside, Shawnee and Mission are names other
#: states carry; Bloomington, Minnesota and Indiana are not Kansas City places at all.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("minneapolis-mn", "Minneapolis / St. Paul, live as production market #42 (deploy 6ac3bfda7b585d009f007620) -- "
                       "the CURRENT LIVE market at this order's authoring time. No shared state, no shared postal "
                       "code."),
    ("st-louis-mo", "St. Louis, live -- the only other MISSOURI market. It owns the 630-633 codes; every one is "
                    "refused here by prefix, and identity is decided by premises and postal code, never the state."),
    ("cleveland-akron-canton-oh", "Cleveland / Akron / Canton, live -- its region contains an Independence, OHIO; "
                                  "identity is decided by premises and state, never the town name."),
    ("cincinnati-oh", "Cincinnati, live -- its region contains Liberty Township, OHIO; identity is decided by premises "
                      "and state, never the town name."),
])

#: A shared postal code whose OTHER town is refused. None at authoring time.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "kansas city,": "kansas city", "kansas city mo": "kansas city", "kansas city, mo": "kansas city",
    "kansas city ks": "kansas city", "kansas city, ks": "kansas city", "kcmo": "kansas city", "kck": "kansas city",
    "kc": "kansas city", "kansas city missouri": "kansas city", "kansas city kansas": "kansas city",
    "north kansas city,": "north kansas city", "n kansas city": "north kansas city", "nkc": "north kansas city",
    "lee's summit": "lees summit", "lee’s summit": "lees summit", "lees summit,": "lees summit",
    "lee's summit,": "lees summit", "independence,": "independence", "liberty,": "liberty",
    "gladstone,": "gladstone", "blue springs,": "blue springs", "raytown,": "raytown", "grandview,": "grandview",
    "riverside,": "riverside", "parkville,": "parkville", "grain valley,": "grain valley", "belton,": "belton",
    "raymore,": "raymore", "overland park,": "overland park", "lenexa,": "lenexa", "olathe,": "olathe",
    "shawnee,": "shawnee", "merriam,": "merriam", "mission,": "mission", "prairie village,": "prairie village",
    "leawood,": "leawood", "gardner,": "gardner", "bonner springs,": "bonner springs",
    "edwardsville,": "edwardsville", "shawnee mission,": "shawnee mission", "roeland park,": "roeland park",
    "mission hills,": "mission hills", "fairway,": "fairway", "westwood,": "westwood",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("64105", "Downtown loop / Power & Light / Library District."),
    ("64106", "River Market / Power & Light east -- overlays of downtown, never split."),
    ("64108", "Crossroads / Crown Center / Union Station."),
    ("64111", "Westport / Midtown Main Street."),
    ("64112", "Country Club Plaza."),
    ("64153", "MCI airport hotel row -- the only airport-property code with hotels."),
    ("64131", "Kansas City, MISSOURI's Bannister / I-435 side -- 'Overland Park' in a name here decides nothing."),
    ("66111", "Village West / The Legends -- Kansas City, KANSAS."),
    ("66210", "College Boulevard / Corporate Woods -- Overland Park and Lenexa."),
    ("66211", "Overland Park Convention Center / Leawood -- Overland Park and Leawood."),
    ("66044", "Lawrence -- refused (lawrence-ks)."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Kansas City" % name),
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
        raise SystemExit("admitted postal codes outside the Kansas City prefixes: %s" % stray)
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
        _state = next((c[7] for c in CORRIDORS if c[0] == suffix), "")
        if not _state:
            _state = ("KS" if suffix in ("obs-lawrence", "obs-topeka", "obs-manhattan", "obs-wichita",
                                         "obs-leavenworth") else "MO")
        cells.append(OrderedDict([
            ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
            ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
            ("state_code", _state),
            ("admitting", admitting),
        ]))
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Kansas City / Greater Kansas City, Missouri & Kansas -- downtown, convention, Crown Center, "
                        "Plaza, stadium, medical, corporate, MCI airport, Northland and Johnson County suburban "
                        "lodging market (PetTripFinder discovery scope)"),
        ("state", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("country", "US"),
        ("market_center", {"lat": 39.10, "lng": -94.58}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches west past Lawrence, Topeka and Manhattan, north "
             "to St. Joseph, east to Columbia and the Lake of the Ozarks and south to Wichita and Springfield, so "
             "that " + WORK_ORDER + " classifies those properties on evidence instead of being blind to them. "
             "Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Kansas City / Greater Kansas City is ONE cross-state market, Missouri AND Kansas, every row "
         "keeping its own state: thirteen CORE corridors (downtown Kansas City, Crossroads / Crown Center, Plaza / "
         "Westport, Midtown / east Kansas City, MCI, the Northland / North Kansas City, Independence, Lee's Summit, "
         "Kansas City Kansas, Village West / the Legends, Overland Park, Lenexa, Olathe, Shawnee), six STRONG "
         "CORRIDORS (Liberty / Gladstone, Blue Springs, Raytown / the sports complex, south Kansas City / Grandview, "
         "Merriam / Mission, Prairie Village / Leawood) and five FRINGE corridors (Riverside / Parkville, Grain "
         "Valley, Belton / Raymore, Gardner, Bonner Springs / Edwardsville). LAWRENCE, TOPEKA, ST. JOSEPH, COLUMBIA, "
         "MANHATTAN, the LAKE OF THE OZARKS, WICHITA and SPRINGFIELD are refused as future standalone markets; Platte "
         "City, Kearney, Leavenworth, Oak Grove and Harrisonville are refused by name. Patient, charitable and "
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
        ("market_name", "Kansas City, Missouri & Kansas"),
        ("market_slug", MARKET_ID),
        ("state_name", "Missouri"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("primary_city", "Kansas City"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Kansas City, Missouri & Kansas | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater Kansas City -- downtown, the Crossroads and Crown Center, the "
         "Plaza and Westport, MCI airport, the Northland, Independence, Lee's Summit, Kansas City Kansas, Overland "
         "Park, Lenexa, Olathe and Shawnee -- with real pet fees and policies read from each hotel's own official "
         "website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Kansas City"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry; the property's STATE is the one its own postal code and page "
         "state. A Kansas City / Greater Kansas City cross-state downtown, convention, Crown Center, Plaza, stadium, "
         "medical, corporate, MCI airport, Northland and Johnson County suburban travel market -- Kansas City, "
         "Missouri and Kansas City, Kansas and the contiguous suburbs the order evaluates on both sides of the state "
         "line. Not 'Missouri' and not 'Kansas': Lawrence, Topeka, St. Joseph, Columbia, Manhattan, the Lake of the "
         "Ozarks, Wichita and Springfield are future standalone markets; Platte City, Kearney, Leavenworth, Oak Grove "
         "and Harrisonville are refused. Nothing else admits a property: not a brand's 'Kansas City' marketing name, "
         "not a map pin, not a vacation-rental listing, not a competitor directory's city label. Patient, charitable "
         "and on-base lodging is never admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY); each corridor states "
         "its own state. The postal city 'KANSAS CITY' exists in BOTH states and places nothing by itself; "
         "'SHAWNEE MISSION' is a Johnson County mailing name, never a city. Shared codes are covered whole: 64105 / "
         "64106 by the downtown loop, Power & Light and the River Market; 64108 by the Crossroads and Crown Center; "
         "66111 by Village West and Edwardsville; 66210 / 66211 / 66215 / 66209 by Overland Park, Lenexa and "
         "Leawood; 66203 by Merriam and Shawnee. Power & Light, the River Market, the Crossroads, Crown Center, the "
         "Plaza, Westport, Zona Rosa, the Legends and College Boulevard are overlays."),
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
        ("phase", "2 + 3 + 4 + 5 + 6 + 7 -- Kansas City / Greater Kansas City cross-state travel-market geography, the "
                  "Kansas City, Missouri / Kansas City, Kansas identity trap, the MCI / Northland boundary, the "
                  "Johnson County cities, the residence / apartment / vacation-rental rule and the timeshare rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/kansas-city-mo.json. This "
         "order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its brand's own property card states it, "
         "joined to the corridor registry. Nothing else admits a property."),
        ("cross_state_rule",
         "Missouri (630-658) and Kansas (660-679) are decided by the postal code. Every corridor states its state; "
         "every row keeps its own city, state, ZIP and street; a page whose stated state contradicts its own postal "
         "code is HELD, never re-labelled. 'Kansas City' in a name or a city field places nothing."),
        ("two_city_rule",
         "Kansas City, Missouri and Kansas City, Kansas are both central cities with their own corridors; neither is "
         "flattened into the other, and every row states the city and state its own premises are in."),
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
        ("mci_northland_evaluation", MCI_NORTHLAND_EVALUATION),
        ("johnson_county_evaluation", JOHNSON_COUNTY_EVALUATION),
        ("kansas_city_ruling", KANSAS_CITY_RULING),
        ("metro_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("military_lodging_rule", OrderedDict([
            ("rule", "On-base military / government lodging is MILITARY_RESTRICTED and never admitted: restricted "
                     "eligibility (DoD ID or sponsorship), on-base premises behind a gate, ordinary public-hotel "
                     "contract NOT satisfied. Fort Leavenworth and Whiteman AFB sit outside the partition; the "
                     "on-base names are refused wherever they appear."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "Kansas City was selected as a high-value PetTripFinder market for its downtown and Crown Center, convention "
         "and stadium demand, medical and corporate travel, the Plaza, the Legends, extended-stay demand and MCI "
         "airport traffic, on both sides of the state line. That lowers NO evidence standard: pet acceptance is "
         "never inferred from a city's reputation. It shapes only the CENSUS: every tourist, convention, stadium, "
         "medical, corporate, airport and extended-stay lodging cluster is covered by an admitting corridor."),
        ("the_kansas_city_name_trap",
         "The chains put 'Kansas City' on hotels in Overland Park, Lenexa, Olathe, Shawnee, Merriam, Leawood, "
         "Independence, Lee's Summit, Liberty, Gladstone, Riverside, Grandview and Platte City, and 'Overland Park' "
         "on a Kansas City, Missouri hotel. A property's own postal code, street and brand property code decide what "
         "and where it is -- and which STATE it is in; none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Kansas City International Airport (MCI)", "mci-airport (64153)."),
            ("Kansas City Convention Center / T-Mobile Center / Power & Light", "downtown-kansas-city (64105 / 64106)."),
            ("Crown Center / Union Station / WWI Museum", "crossroads-crown-center (64108)."),
            ("Country Club Plaza / Westport", "plaza-westport (64112 / 64111)."),
            ("Truman Sports Complex (Arrowhead / Kauffman)", "raytown-sports-complex (64129 / 64133)."),
            ("Worlds of Fun", "northland-north-kansas-city (64161 / 64117)."),
            ("KU Medical Center", "kansas-city-kansas (66103 / 66160)."),
            ("Kansas Speedway / Legends / Children's Mercy Park", "village-west-legends (66111)."),
            ("Overland Park Convention Center / College Boulevard", "overland-park (66211 / 66210)."),
            ("Bass Pro / Cable Dahmer Arena", "independence (64055 / 64057)."),
        ])),
        ("evaluated_inclusions", EVALUATED_INCLUSIONS),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_postal_codes_by_state", OrderedDict(
            (s, sorted(z for z in seen_zip if state_for_postal(z) == s)) for s in STATE_CODES)),
        ("corridor_count_by_state", OrderedDict(
            (s, sum(1 for c in corridors if c["state_code"] == s)) for s in STATE_CODES)),
        ("admitted_counties", sorted(ADMITTED_COUNTIES)),
        ("observed_outside_counties", OBSERVED_COUNTIES),
        ("outside_prefixes", [OrderedDict([("prefix", p), ("area", n), ("future_market", f)])
                              for p, n, f in OUTSIDE_PREFIXES]),
        ("shared_postal_codes", SHARED_POSTAL_CODES),
        ("registered_market_postal_codes_checked", len(registered_codes)),
        ("no_live_market_postal_code_admitted", not live_overlap),
        ("first_kansas_market", True),
        ("second_missouri_market", "st-louis-mo is live and owns 630-633; none of its codes is admitted here."),
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


def state_conflict(postal, stated_state):
    """The reason a row's own STATED state contradicts the state its own postal code is in, or "". The cross-state
    guard: a Kansas hotel is never written as Missouri and a Missouri hotel never as Kansas."""
    s = (stated_state or "").strip().upper()
    s = {"MISSOURI": "MO", "KANSAS": "KS"}.get(s, s)
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
        return "OUTSIDE", None, "Kansas City-region postal code %r is claimed by no corridor" % z
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
    print("by class:", json.dumps(report["corridor_count_by_class"]), "by state:",
          json.dumps(report["corridor_count_by_state"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
