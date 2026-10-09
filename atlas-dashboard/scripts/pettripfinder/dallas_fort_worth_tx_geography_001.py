"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5, 6, 7, 8, 9 and 10: the Dallas-Fort Worth
Metroplex market, Texas.

Built from zero on the CURRENT hardened lineage: the Fort Myers-live release 1637778a (live lineage commit 35a04413,
built_from ab616e2e). Current verified live at authoring time = fort-myers-fl deploy 6ac8d0c021f9d04e6aa82455, 46
markets / 4,430 profiles / 4,869 release-index routes / 4,948 served routes, host verified (release_index live-source
--verify-host). No earlier Dallas-Fort Worth build exists. Two Texas markets are live (Austin, San Antonio); neither
admits a 750-762 postal code, and the build refuses to admit any code a registered market already admits.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Dallas-Fort Worth traveller lodging market -- NOT the City of Dallas's municipal boundary, and NOT "North
Texas" -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE markets named inside
OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact to make a number.
The order's "STRONG_CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property card,
or the State's own hotel-tax permit) states it, joined to the corridor registry below. The registry is a POSTAL-CODE
PARTITION: every admitted lodging ZIP is claimed by exactly one corridor, so a property's corridor is a lookup and
never a judgement. A brand's marketing name ("Dallas", "Fort Worth", "Dallas/Fort Worth", "DFW Airport", "Dallas
North", "Dallas Galleria", "Fort Worth Alliance", "Arlington Entertainment District") never admits and never places a
property.

ONE MARKET, FOUR COUNTIES (PHASES 2 AND 3)
-----------------------------------------
The market is the Metroplex's continuous traveller lodging across DALLAS and TARRANT counties (admitted whole) and the
southern tier of COLLIN (Plano, Frisco, Allen, McKinney, Richardson's and Dallas's Collin County land) and DENTON
(Lewisville, The Colony, Flower Mound, Carrollton, Frisco's and Dallas's Denton County land, Roanoke / Trophy Club /
Northlake). Rockwall, Ellis, Johnson, Parker, Wise, Kaufman and every outer county are refused: a premises whose OWN
coordinates fall in a refused county is refused whatever its mailing label (COUNTY_REFUSALS) -- Burleson's Johnson
County land inside 76028, Parker County land inside 76108 / 76020, Mansfield's Johnson / Ellis edge inside 76063.

MUNICIPALITY SAFETY (PHASE 4) -- DECIDED BY THE PREMISES, NOT THE POSTAL CODE
---------------------------------------------------------------------------
The Postal Service names "Dallas" the preferred city of codes that are partly Farmers Branch, Addison, Richardson,
Carrollton, University Park and Highland Park, and "Fort Worth" for codes that are partly White Settlement, Haltom
City, Forest Hill, Saginaw, Lake Worth, Haslet, Keller or Burleson. A row whose coordinates are known publishes the
INCORPORATED PLACE whose Census TIGER/Line boundary contains its premises (dallas_fort_worth_tx_municipal_boundaries
_001); POSTAL_COUNTY below is the fallback for a row without coordinates and the cross-check for every row. A row in a
code that carries more than one municipality and whose premises cannot be placed is HELD, never labelled by its
mailing city. SUBURBAN HOTELS MISLABELED DALLAS = 0 and SUBURBAN HOTELS MISLABELED FORT WORTH = 0 are counts the
census refuses to write otherwise.

DFW AIRPORT (PHASE 5)
---------------------
Dallas/Fort Worth International Airport's land (postal code 75261, "DFW Airport, TX") lies inside the city limits of
Grapevine, Irving, Euless and Coppell. Its on-airport hotels (inside the terminals and on International Parkway) are
the dfw-airport corridor together with CentrePort (76155, City of Fort Worth) south of the airport. Hotels MARKETED
"DFW Airport North / South / West" in Irving (75063 / 75062), Grapevine (76051), Euless (76039 / 76040), Coppell
(75019) or Fort Worth (76155) are placed by their own postal code and publish their own municipality; a property is
ONE row however many of "Dallas", "Fort Worth", "Dallas/Fort Worth", "DFW Airport", "Airport North" and "Airport
South" its marketing carries.

LOVE FIELD (PHASE 6)
--------------------
Dallas Love Field (8008 Herb Kelleher Way, 75235) is a City of Dallas airport. Its hotels are Mockingbird Lane / Cedar
Springs / Lemmon Avenue (75235 / 75209) and the Harry Hines / Walnut Hill / Northwest Highway rows (75220 / 75229);
they are the love-field-medical-market-center corridor with the Medical District (75235 / 75390) and Market Center /
Stemmons (75207 / 75247). A Love Field row and a DFW Airport row never share evidence.

ARLINGTON ENTERTAINMENT DISTRICT (PHASE 7)
-----------------------------------------
AT&T Stadium, Globe Life Field, Choctaw Stadium, Texas Live! and Six Flags Over Texas are in 76011; the I-30 /
Collins / Lamar hotel rows north of the stadiums are 76006. Those two codes are the arlington-entertainment corridor.
Apartment towers, event-only packages and vacation rentals around the stadiums are never hotels.

PLANO / FRISCO (PHASE 8) AND ALLIANCE (PHASE 9)
-----------------------------------------------
Legacy, Legacy West and Granite Park are Plano 75024; The Star, Stonebriar and the Frisco convention district are
Frisco 75034 / 75033. A "Dallas North" or "Dallas Plano" marketing name never makes them Dallas. Alliance / North Fort
Worth (76177 / 76131 / 76137 / 76244) publishes Fort Worth only where the premises are inside the City of Fort Worth;
Roanoke, Trophy Club, Northlake, Westlake, Haslet and Keller keep their own names, and Denton County's far north
(Denton, Corinth, Justin, Argyle) is refused.

DENTON / MCKINNEY SPRAWL (PHASE 10)
-----------------------------------
DENTON (76201-76210, with Corinth, Lake Dallas, Hickory Creek, Argyle and Justin) is a separate university city beyond
Lewisville Lake with its own demand (UNT, TWU): OUTSIDE, FUTURE_STANDALONE denton-tx. MCKINNEY (75069-75072) is
admitted at FRINGE with ALLEN: its hotel clusters at Craig Ranch / SH-121 and US-75 are continuous with Allen, Plano
and Frisco's corporate corridor. Prosper, Celina, Little Elm, Wylie, Rockwall and every outer ring are refused.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/dallas_fort_worth_tx.json
  launch_packages/pettripfinder/markets/proposed/dallas-fort-worth-tx.json
  launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_geography_001.json
  launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_corridor_registry_001.json
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

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "dallas_fort_worth_tx.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "dallas-fort-worth-tx.json")
REPORT_OUT = os.path.join(REPORTS, "dallas_fort_worth_tx_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "dallas_fort_worth_tx_corridor_registry_001.json")
#: Every REGISTERED market's own document: no postal code any of them admits may be admitted here.
REGISTERED_MARKETS_GLOB = os.path.join(PKG, "markets", "*.json")
AS_OF = "2026-10-09"
STATE_CODE = "TX"
STATE_CODES = ("TX",)


def state_for_postal(postal):
    """The state a postal code belongs to: Texas 750-799 and 885. Neighbouring states are named so a stray
    out-of-state row is visible."""
    z = (postal or "").strip()[:3]
    if not z.isdigit():
        return ""
    n = int(z)
    if 750 <= n <= 799 or n == 885:
        return "TX"
    if 730 <= n <= 749:
        return "OK"
    if 716 <= n <= 729:
        return "AR"
    if 700 <= n <= 714:
        return "LA"
    return ""


#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description, state)
CORRIDORS = [
    # ---------------------------------------------------------------- CORE: Dallas
    ("downtown-dallas", "Downtown Dallas, Arts District & Deep Ellum", "Downtown Dallas / Arts District / Main Street "
     "/ Reunion / Kay Bailey Hutchison Convention Center / Deep Ellum / Baylor / Fair Park", "CORE", "dallas",
     ["75201", "75202", "75270", "75226", "75246", "75210", "75215"],
     "The City of Dallas's central business district: the Arts District, Main Street, Reunion and the convention "
     "center (75201 / 75202 / 75270), Deep Ellum (75226), the Baylor medical campus east of downtown (75246), Fair Park "
     "(75210) and South Dallas (75215).", "TX"),
    ("uptown-victory-park", "Uptown, Victory Park & Oak Lawn", "Uptown / McKinney Avenue / State-Thomas / Victory Park "
     "/ American Airlines Center / Oak Lawn / Turtle Creek", "CORE", "dallas", ["75204", "75219"],
     "Uptown, McKinney Avenue and State-Thomas (75204) and Oak Lawn, Turtle Creek, Victory Park and the American "
     "Airlines Center (75219). Victory Park and the AAC sit astride 75219 / 75201 and are overlays, never split codes.",
     "TX"),
    ("love-field-medical-market-center", "Love Field, Medical District & Market Center",
     "Dallas Love Field / Mockingbird Lane / Medical District (Parkland, UT Southwestern) / Market Center / Design "
     "District / Stemmons Freeway / Harry Hines / Walnut Hill / Northwest Highway", "CORE", "dallas",
     ["75207", "75235", "75247", "75209", "75220", "75229", "75212", "75390"],
     "Dallas Love Field and its Mockingbird / Cedar Springs / Lemmon rows (75235 / 75209), the Medical District -- "
     "Parkland, UT Southwestern (75235 / 75390), Market Center, the Design District and the Stemmons Freeway hotel row "
     "(75207 / 75247), the Harry Hines / Walnut Hill / Northwest Highway / Bachman Lake rows north of the airport "
     "(75220 / 75229) and West Dallas (75212). Never DFW Airport.", "TX"),
    ("park-cities-preston-center", "Park Cities, Preston Center & Central Expressway",
     "Highland Park / University Park / SMU / Preston Center / NorthPark / Knox-Henderson / Lower Greenville / "
     "Lakewood / Lake Highlands", "CORE", "dallas",
     ["75205", "75206", "75225", "75275", "75214", "75218", "75238"],
     "The Park Cities (Highland Park and University Park, 75205 / 75225 / 75275 -- their own municipalities, never "
     "Dallas), Preston Center and NorthPark (75225), Knox-Henderson, Lower Greenville and Central Expressway at "
     "Mockingbird (75206), Lakewood and White Rock (75214 / 75218) and Lake Highlands (75238).", "TX"),
    ("north-dallas-galleria", "North Dallas, Galleria & LBJ", "Galleria / LBJ Freeway / Dallas Parkway / Park Central "
     "/ Central Expressway at LBJ / Valley View / Prestonwood / Far North Dallas", "CORE", "dallas",
     ["75240", "75251", "75254", "75230", "75248", "75252", "75287", "75243", "75231"],
     "The Galleria and the LBJ Freeway / Dallas Parkway hotel row (75240 / 75254), Park Central and Central Expressway "
     "at LBJ (75251 / 75243 / 75231), Valley View and Preston Hollow north (75230), Prestonwood (75248) and Far North "
     "Dallas on the Tollway (75252 / 75287). 75254 also carries Addison and 75252 / 75243 Richardson: each row's own "
     "premises decide.", "TX"),
    # ---------------------------------------------------------------- CORE: DFW Airport, Irving, Arlington
    ("dfw-airport", "DFW Airport & CentrePort", "DFW International Airport (terminals, International Parkway) / "
     "CentrePort / Amon Carter Boulevard / SH-360 at the airport's south entrance", "CORE", "dfw airport",
     ["75261", "76155"],
     "Dallas/Fort Worth International Airport's own land (75261, 'DFW Airport, TX' -- inside the city limits of "
     "Grapevine, Irving, Euless and Coppell) and CentrePort south of the airport (76155, City of Fort Worth). A hotel "
     "MARKETED 'DFW Airport' elsewhere is placed by its own code (DFW_AIRPORT_EVALUATION).", "TX"),
    ("irving-las-colinas", "Irving & Las Colinas", "Las Colinas / Urban Center / Irving Convention Center / Toyota "
     "Music Factory / Valley Ranch / SH-114 / SH-183 / DFW Airport North (Irving)", "CORE", "irving",
     ["75038", "75039", "75060", "75061", "75062", "75063", "75014", "75015", "75016", "75017"],
     "The CITY OF IRVING: Las Colinas, the Urban Center, the convention center and the Toyota Music Factory (75038 / "
     "75039), Valley Ranch and the SH-114 / Freeport rows marketed 'DFW Airport North' (75063), the SH-183 / Esters "
     "Road rows marketed 'DFW Airport South' (75062), central and south Irving (75060 / 75061) and the PO codes. Never "
     "Dallas.", "TX"),
    ("arlington-entertainment", "Arlington Entertainment District", "AT&T Stadium / Globe Life Field / Choctaw "
     "Stadium / Texas Live! / Six Flags Over Texas / Hurricane Harbor / I-30 / Collins Street / Lamar Boulevard",
     "CORE", "arlington", ["76011", "76006", "76004", "76005", "76096"],
     "The CITY OF ARLINGTON's stadium district: AT&T Stadium, Globe Life Field, Choctaw Stadium, Texas Live! and Six "
     "Flags (76011) and the I-30 / Collins / Lamar / Brookhollow rows north of the stadiums (76006), with the PO "
     "codes. Apartment towers, event-only packages and vacation rentals are never hotels.", "TX"),
    # ---------------------------------------------------------------- CORE: Fort Worth
    ("downtown-fort-worth", "Downtown Fort Worth, Sundance Square & Near Southside", "Downtown Fort Worth / Sundance "
     "Square / Fort Worth Convention Center / Near Southside / Medical District", "CORE", "fort worth",
     ["76102", "76104", "76101", "76113", "76147", "76161", "76162", "76163", "76185", "76191", "76192", "76193",
      "76195", "76196", "76197", "76198", "76199"],
     "The City of Fort Worth's central business district, Sundance Square and the convention center (76102), the "
     "Near Southside and the Medical District (76104), and the downtown PO and unique codes.", "TX"),
    ("stockyards-north-side", "Fort Worth Stockyards & North Side", "Fort Worth Stockyards / Exchange Avenue / North "
     "Main Street / Meacham Airport / Northside / Riverside", "CORE", "fort worth", ["76164", "76106", "76111"],
     "The Stockyards National Historic District and North Main (76164 / 76106), Meacham Airport, and Riverside (76111 "
     "-- partly Haltom City; each row's own premises decide).", "TX"),
    ("cultural-district-tcu", "Cultural District, West 7th & TCU", "Cultural District / West 7th / Will Rogers "
     "Memorial Center / Dickies Arena / Montgomery Plaza / TCU / University Drive / Berkeley", "CORE", "fort worth",
     ["76107", "76109", "76129", "76110"],
     "The Cultural District, West 7th, Will Rogers and Dickies Arena (76107), TCU and University Drive (76109 / "
     "76129) and Berkeley / Fairmount south (76110).", "TX"),
    ("alliance-north-fort-worth", "Alliance & North Fort Worth", "AllianceTexas / Alliance Town Center / Texas Motor "
     "Speedway (south approach) / I-35W north / Heritage Trace / North Tarrant Parkway / Roanoke / Trophy Club / "
     "Westlake / Keller / Haslet / Saginaw", "CORE", "fort worth",
     ["76131", "76137", "76177", "76244", "76262", "76052", "76179", "76248"],
     "North Fort Worth along I-35W -- Basswood / Western Center (76131 / 76137), AllianceTexas, Alliance Town Center "
     "and Heritage Trace (76177 / 76244) -- and the Alliance-area towns that keep their own names: Roanoke, Trophy "
     "Club, Northlake and Westlake (76262), Haslet (76052), Saginaw (76179) and Keller (76248). Fort Worth is "
     "published only where the premises are inside the City of Fort Worth.", "TX"),
    # ---------------------------------------------------------------- STRONG CORRIDOR: Dallas outer
    ("east-dallas", "East Dallas & I-30 / I-635", "I-30 East / Ferguson Road / Big Town / I-635 at I-30 / Buckner "
     "Boulevard / Pleasant Grove / Kleberg", "CORRIDOR", "dallas", ["75223", "75227", "75228", "75217", "75253"],
     "The City of Dallas's east side: the I-30 East hotel row and East Dallas (75223 / 75227 / 75228), Pleasant Grove "
     "and Buckner Boulevard at I-635 (75217) and Kleberg (75253). Mesquite and Balch Springs land in these codes keeps "
     "its own name.", "TX"),
    ("oak-cliff-south-dallas", "Oak Cliff & South Dallas (I-35E / I-20)", "Bishop Arts / Oak Cliff / Kessler / I-35E "
     "south / I-20 / Red Bird / Camp Wisdom / Mountain Creek / West Dallas (I-30)", "CORRIDOR", "dallas",
     ["75203", "75208", "75211", "75216", "75224", "75232", "75233", "75236", "75237", "75241", "75249"],
     "Oak Cliff and the Bishop Arts District (75203 / 75208), the I-30 west / Cockrell Hill rows (75211), I-35E south "
     "and Ledbetter (75216 / 75224 / 75232), Red Bird and I-20 (75237 / 75236 / 75249) and the I-45 / I-20 rows "
     "(75241). Grand Prairie, Duncanville and Hutchins land in these codes keeps its own name.", "TX"),
    # ---------------------------------------------------------------- STRONG CORRIDOR: Mid-Cities, Arlington, GP
    ("grapevine-coppell", "Grapevine & Coppell", "Grapevine / Gaylord Texan / Grapevine Mills / Historic Main Street "
     "/ SH-114 / SH-121 / DFW Airport North (Grapevine) / Coppell / Cypress Waters edge", "CORRIDOR", "grapevine",
     ["76051", "76099", "75019", "75099"],
     "The CITY OF GRAPEVINE -- the Gaylord Texan, Grapevine Mills, Historic Main Street and the SH-114 / SH-121 rows "
     "at the airport's north entrance (76051 / 76099) -- and the CITY OF COPPELL north of the airport (75019 / 75099). "
     "Never Dallas, never 'DFW Airport'.", "TX"),
    ("mid-cities", "Mid-Cities (Euless, Bedford, Hurst, Colleyville, North Richland Hills)", "Euless / Bedford / Hurst "
     "/ Colleyville / North Richland Hills / Richland Hills / Haltom City / Watauga / SH-183 / SH-121 / Loop 820 / "
     "DFW Airport West (Euless)", "CORRIDOR", "euless",
     ["76039", "76040", "76021", "76022", "76095", "76053", "76054", "76034", "76180", "76182", "76118", "76117",
      "76148"],
     "The HEB Mid-Cities between the two downtowns: Euless (76039 / 76040, marketed 'DFW Airport West'), Bedford "
     "(76021 / 76022 / 76095), Hurst (76053 / 76054), Colleyville (76034), North Richland Hills (76180 / 76182), "
     "Richland Hills (76118), Haltom City (76117) and Watauga (76148). Every row keeps its own municipality.", "TX"),
    ("arlington", "Arlington (UTA, I-20 & Parks Mall)", "UT Arlington / Downtown Arlington / Cooper Street / I-20 / "
     "The Parks Mall / Arlington Highlands / South Arlington / Pantego / Dalworthington Gardens", "CORRIDOR",
     "arlington",
     ["76010", "76012", "76013", "76014", "76015", "76016", "76017", "76018", "76019", "76001", "76002", "76003",
      "76007", "76094"],
     "The rest of the CITY OF ARLINGTON: downtown and UT Arlington (76010 / 76019 / 76013), the Cooper Street and I-20 "
     "rows at The Parks Mall and Arlington Highlands (76015 / 76018 / 76017 / 76014), north and west Arlington (76012 "
     "/ 76016), south Arlington (76001 / 76002) and the PO codes. Pantego and Dalworthington Gardens keep their own "
     "names.", "TX"),
    ("grand-prairie", "Grand Prairie", "Grand Prairie / Lone Star Park / Epic Central / I-30 / SH-360 / I-20 / Great "
     "Southwest", "CORRIDOR", "grand prairie", ["75050", "75051", "75052", "75053", "75054"],
     "The CITY OF GRAND PRAIRIE across the Dallas / Tarrant line: the I-30 / SH-360 / Great Southwest rows and Lone "
     "Star Park (75050), central and south Grand Prairie and I-20 (75051 / 75052 / 75054) and the PO code. Never "
     "Dallas, never Arlington.", "TX"),
    # ---------------------------------------------------------------- STRONG CORRIDOR: Fort Worth outer
    ("fort-worth-west", "West Fort Worth (I-30 / Ridgmar / Las Vegas Trail)", "I-30 West / Ridgmar / Hulen (north) / "
     "Las Vegas Trail / White Settlement / Benbrook / Lake Worth / River Oaks / NAS Fort Worth JRB / Azle", "CORRIDOR",
     "fort worth", ["76116", "76108", "76126", "76135", "76114", "76127", "76020"],
     "West Fort Worth: Ridgmar and I-30 west (76116), Las Vegas Trail and White Settlement (76108), Benbrook (76126), "
     "Lake Worth and the north-west (76135), River Oaks / Westworth Village (76114), Naval Air Station Fort Worth JRB "
     "(76127 -- on-base lodging MILITARY_RESTRICTED) and Azle (76020). Parker County land is refused by county.",
     "TX"),
    ("fort-worth-south", "South Fort Worth (I-35W / I-20 / Hulen)", "Hulen / Cityview / I-20 / I-35W south / Seminary "
     "/ Forest Hill / Everman / Crowley / Kennedale / Burleson edge", "CORRIDOR", "fort worth",
     ["76132", "76133", "76134", "76115", "76119", "76140", "76123", "76036", "76028", "76060"],
     "South Fort Worth: Hulen and Cityview at I-20 (76132 / 76133 / 76123), the I-35W south / Seminary / Alsbury rows "
     "(76134 / 76115 / 76028), Forest Hill and Everman (76119 / 76140), Crowley (76036) and Kennedale (76060). "
     "Burleson's Johnson County land inside 76028 is refused by county.", "TX"),
    ("fort-worth-east", "East Fort Worth (I-30 East / Loop 820)", "I-30 East / Handley / Eastchase / Loop 820 east / "
     "Lake Arlington", "CORRIDOR", "fort worth", ["76103", "76105", "76112", "76120"],
     "East Fort Worth: I-30 East, Handley and Eastchase (76103 / 76112 / 76120) and the Polytechnic / Stop Six area "
     "(76105).", "TX"),
    # ---------------------------------------------------------------- STRONG CORRIDOR: north Dallas corporate
    ("addison", "Addison", "Addison / Addison Circle / Belt Line Road / Dallas Parkway / Addison Airport",
     "CORRIDOR", "addison", ["75001"],
     "The TOWN OF ADDISON (75001): Addison Circle, the Belt Line Road and Dallas Parkway hotel rows. Addison land in "
     "Dallas-preferred 75254 / 75244 is placed by its own premises. Never Dallas.", "TX"),
    ("richardson", "Richardson (Telecom Corridor)", "Richardson / Telecom Corridor / CityLine / UT Dallas / US-75 / "
     "Campbell Road / Galatyn Park", "CORRIDOR", "richardson", ["75080", "75081", "75082", "75083", "75085"],
     "The CITY OF RICHARDSON across the Dallas / Collin line: Galatyn Park and US-75 (75080 / 75081), CityLine, the "
     "Telecom Corridor and UT Dallas (75082 / 75080) and the PO codes. Never Dallas.", "TX"),
    ("plano", "Plano (Legacy, Legacy West & Granite Park)", "Legacy / Legacy West / Granite Park / Dallas North Tollway "
     "(Plano) / Shops at Legacy / US-75 (Plano) / Collin Creek / Plano Parkway / Murphy", "CORRIDOR", "plano",
     ["75024", "75093", "75023", "75025", "75026", "75074", "75075", "75086", "75094"],
     "The CITY OF PLANO: Legacy, Legacy West, Granite Park and the Tollway corporate campuses (75024 / 75093), the US-75 "
     "rows (75074 / 75075 / 75023), north and east Plano (75025 / 75094 -- Murphy and Parker keep their own names) "
     "and the PO codes. PLANO PROFILES LABELED DALLAS = 0.", "TX"),
    ("frisco", "Frisco (The Star, Stonebriar & SH-121)", "The Star / Ford Center / Stonebriar / Frisco convention "
     "district / SH-121 (Sam Rayburn Tollway) / Dallas North Tollway (Frisco) / Toyota Stadium / PGA Frisco",
     "CORRIDOR", "frisco", ["75034", "75033", "75035", "75036"],
     "The CITY OF FRISCO across the Collin / Denton line: The Star, Stonebriar, the convention district and SH-121 "
     "(75034), the Tollway north and PGA Frisco (75033), east Frisco and Toyota Stadium (75035) and west Frisco "
     "(75036). FRISCO PROFILES LABELED DALLAS = 0.", "TX"),
    ("carrollton-farmers-branch", "Carrollton & Farmers Branch", "Carrollton / Farmers Branch / I-35E / LBJ Freeway "
     "west / Valwood / Josey Lane / President George Bush Turnpike / Mercer Crossing", "CORRIDOR", "carrollton",
     ["75006", "75007", "75010", "75011", "75234", "75244", "75381"],
     "The CITY OF CARROLLTON (75006 / 75007 / 75010 / 75011) and the CITY OF FARMERS BRANCH (75234 / 75244 / 75381) "
     "on I-35E, the LBJ Freeway west and Mercer Crossing. 75234 and 75244 are Dallas-preferred postal codes whose "
     "hotels are largely Farmers Branch: each row's own premises decide, never its mailing label.", "TX"),
    ("lewisville-the-colony", "Lewisville, The Colony & Highland Village", "Lewisville / Vista Ridge / I-35E (Lewisville) "
     "/ SH-121 / The Colony / Grandscape / Nebraska Furniture Mart / Highland Village", "CORRIDOR", "lewisville",
     ["75056", "75057", "75067", "75077", "75029"],
     "The CITY OF THE COLONY -- Grandscape and SH-121 (75056) -- and the CITY OF LEWISVILLE -- Vista Ridge, I-35E and "
     "old town (75067 / 75057 / 75077 / 75029), with Highland Village (75077) keeping its own name.", "TX"),
    # ---------------------------------------------------------------- FRINGE (CAREFUL evaluation)
    ("southlake-flower-mound", "Southlake & Flower Mound", "Southlake Town Square / SH-114 / Flower Mound / FM 2499 / "
     "Lakeside / Bartonville", "FRINGE", "southlake", ["76092", "75022", "75028", "75027"],
     "The CITY OF SOUTHLAKE west of the airport (76092) and the TOWN OF FLOWER MOUND north of it (75022 / 75028 / "
     "75027). Admitted at FRINGE after CAREFUL evaluation.", "TX"),
    ("allen-mckinney", "Allen & McKinney", "Allen / Allen Premium Outlets / Credit Union of Texas Event Center / "
     "Watters Creek / McKinney / Craig Ranch / SH-121 / US-75 north / historic downtown McKinney / Fairview", "FRINGE",
     "allen", ["75013", "75002", "75070", "75069", "75071", "75072"],
     "The CITY OF ALLEN (75013 / 75002) and the CITY OF McKINNEY (75070 Craig Ranch / SH-121; 75069 downtown and US-75; "
     "75071 / 75072 north and west), continuous with Plano and Frisco along US-75 and SH-121. Admitted at FRINGE "
     "after CAREFUL evaluation; every row keeps its own municipality (Fairview, Lucas).", "TX"),
    ("garland-mesquite-rowlett", "Garland, Mesquite & Rowlett", "Garland / I-635 (LBJ east) / Mesquite / Town East "
     "/ I-30 / I-20 / Balch Springs / Rowlett / Sachse / Sunnyvale", "FRINGE", "mesquite",
     ["75149", "75150", "75181", "75185", "75187", "75180", "75182", "75040", "75041", "75042", "75043", "75044",
      "75045", "75046", "75047", "75049", "75048", "75088", "75089", "75030"],
     "Dallas County's eastern ring: the CITY OF MESQUITE -- Town East, I-635 and I-30 / I-20 (75149 / 75150 / 75181 / "
     "75185 / 75187) -- Balch Springs (75180), Sunnyvale (75182), the CITY OF GARLAND (75040-75047 / 75049), Sachse "
     "(75048) and Rowlett (75088 / 75089 / 75030). Admitted at FRINGE after CAREFUL evaluation; Rowlett's Rockwall "
     "County land is refused by county.", "TX"),
    ("south-dallas-county", "South Dallas County (I-20 / I-35E / I-45)", "DeSoto / Duncanville / Cedar Hill / "
     "Lancaster / Hutchins / Wilmer / Seagoville / I-20 / I-35E / I-45 / US-67", "FRINGE", "desoto",
     ["75115", "75123", "75116", "75137", "75138", "75104", "75106", "75134", "75146", "75141", "75172", "75159"],
     "Dallas County's southern ring on I-20, I-35E, I-45 and US-67: DeSoto (75115 / 75123), Duncanville (75116 / "
     "75137 / 75138), Cedar Hill (75104 / 75106), Lancaster (75134 / 75146), Hutchins (75141), Wilmer (75172) and "
     "Seagoville (75159). Admitted at FRINGE as Dallas County inner-ring lodging; Ellis County (Red Oak, Midlothian, "
     "Waxahachie) is refused.", "TX"),
    ("mansfield", "Mansfield", "Mansfield / US-287 / SH-360 south", "FRINGE", "mansfield", ["76063"],
     "The CITY OF MANSFIELD south of Arlington (76063). Admitted at FRINGE after CAREFUL evaluation; its Johnson / "
     "Ellis County edge is refused by county.", "TX"),
]

OUTSIDE = [
    ("Denton / Corinth / Lake Dallas / Hickory Creek / Argyle / Justin / Sanger / Krum / Ponder / Aubrey / Pilot Point "
     "-- Denton County north", "TX",
     ["76201", "76202", "76203", "76204", "76205", "76206", "76207", "76208", "76209", "76210", "75065", "76226",
      "76247", "76266", "76249", "76259", "76227", "76258"],
     "DENTON COUNTY beyond Lewisville Lake; FUTURE_STANDALONE denton-tx. Denton is a separate university city (UNT, "
     "TWU) 38 miles from downtown Dallas with its own demand. Refused by postal code after careful evaluation."),
    ("Little Elm / Oak Point / Prosper / Celina -- north of Frisco and The Colony", "TX", ["75068", "75078", "75009"],
     "DENTON / COLLIN COUNTY north of SH-121 and the Hackberry arm of Lewisville Lake. Refused after careful evaluation."),
    ("Wylie / Lavon / Princeton / Farmersville / Anna / Melissa / Nevada / Royse City -- Collin County east and north",
     "TX", ["75098", "75166", "75407", "75442", "75409", "75454", "75173", "75189"],
     "COLLIN COUNTY's outer ring east of Lake Lavon and north of McKinney. Refused after careful evaluation."),
    ("Rockwall / Fate / Heath / McLendon-Chisholm -- Rockwall County", "TX", ["75032", "75087", "75132"],
     "ROCKWALL COUNTY east of Lake Ray Hubbard. Evaluated and refused: a lake-side I-30 exurb in its own county, "
     "25+ miles from downtown Dallas. Refused by postal code and by county."),
    ("Forney / Terrell / Kaufman / Crandall / Scurry / Mabank -- Kaufman County", "TX",
     ["75126", "75160", "75161", "75142", "75114", "75158", "75147"],
     "KAUFMAN COUNTY. Refused by postal code and by county."),
    ("Waxahachie / Ennis / Midlothian / Red Oak / Ferris / Palmer / Maypearl -- Ellis County", "TX",
     ["75165", "75167", "75168", "75119", "75120", "76065", "75154", "75125", "75152", "76064"],
     "ELLIS COUNTY; FUTURE_STANDALONE waxahachie-ennis-tx. Refused by postal code and by county."),
    ("Cleburne / Burleson (Johnson County) / Alvarado / Joshua / Grandview / Keene / Venus / Godley -- Johnson County",
     "TX", ["76031", "76033", "76009", "76058", "76050", "76059", "76084", "76044", "76093", "76097"],
     "JOHNSON COUNTY. Refused by postal code and by county (Burleson's Johnson County land inside 76028 by county)."),
    ("Weatherford / Aledo / Willow Park / Hudson Oaks / Springtown / Millsap / Cresson -- Parker County", "TX",
     ["76085", "76086", "76087", "76088", "76008", "76082", "76066", "76035"],
     "PARKER COUNTY; FUTURE_STANDALONE weatherford-tx. Refused by postal code and by county."),
    ("Decatur / Rhome / Newark / Boyd / Alvord / Paradise / Bridgeport -- Wise County", "TX",
     ["76234", "76078", "76071", "76023", "76225", "76073", "76426"],
     "WISE COUNTY; FUTURE_STANDALONE decatur-tx. Refused by postal code and by county."),
    ("Granbury / Glen Rose / Mineral Wells / Rainbow / Nemo -- Hood, Somervell and Palo Pinto counties", "TX",
     ["76048", "76049", "76043", "76067", "76077", "76070"],
     "Lake / resort towns west and south-west of Fort Worth. Refused by postal code."),
    ("Corsicana / Kerens / Angus -- Navarro County", "TX", ["75109", "75110", "75151", "75144"],
     "NAVARRO COUNTY; FUTURE_STANDALONE corsicana-tx. Refused by postal code."),
    ("Greenville / Commerce -- Hunt County", "TX", ["75401", "75402", "75403", "75404", "75428"],
     "HUNT COUNTY; FUTURE_STANDALONE greenville-tx. Refused by postal code (prefix 754)."),
    ("Sherman / Denison / Pottsboro / Whitesboro / Gordonville -- Grayson County (Texoma)", "TX",
     ["75090", "75091", "75092", "75020", "75021", "75076", "76273", "76245", "75491"],
     "GRAYSON COUNTY; FUTURE_STANDALONE sherman-denison-tx. Refused by postal code."),
    ("Gainesville / Muenster / Valley View -- Cooke County", "TX", ["76240", "76241", "76252", "76272"],
     "COOKE COUNTY; FUTURE_STANDALONE gainesville-tx. Refused by postal code."),
    ("Waco / Woodway / Bellmead / Hewitt -- McLennan County", "TX", [],
     "McLENNAN COUNTY; FUTURE_STANDALONE waco-tx. Refused by PREFIX (766 / 767)."),
    ("Greater Texas and out of state", "--", [],
     "Every other Texas postal code no corridor claims, and every code outside Texas, is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("754", "Northeast Texas (Greenville, Paris, Sulphur Springs, Mount Pleasant)", "greenville-tx"),
    ("755", "Texarkana", ""), ("756", "Longview / Marshall", ""), ("757", "Tyler", ""), ("758", "Palestine", ""),
    ("759", "Lufkin / Nacogdoches", ""), ("763", "Wichita Falls", ""), ("764", "Stephenville / Brownwood", ""),
    ("765", "Temple / Killeen / Belton", ""), ("766", "Waco", "waco-tx"), ("767", "Waco", "waco-tx"),
    ("768", "Abilene / Brownwood", ""), ("769", "San Angelo / Abilene", ""),
    ("786", "Austin (live market austin-tx)", "austin-tx"), ("787", "Austin (live market austin-tx)", "austin-tx"),
    ("782", "San Antonio (live market san-antonio-tx)", "san-antonio-tx"),
    ("770", "Houston", ""), ("772", "Houston", ""), ("773", "Houston north", ""), ("774", "Houston west", ""),
    ("775", "Houston south / Galveston", ""), ("776", "Beaumont", ""), ("777", "Beaumont", ""),
    ("778", "Bryan / College Station", ""), ("779", "Victoria", ""), ("780", "South Texas", ""),
    ("781", "South Texas", ""), ("783", "Corpus Christi", ""), ("784", "Corpus Christi", ""),
    ("785", "Rio Grande Valley", ""), ("788", "Del Rio / Uvalde", ""), ("789", "Hill Country", ""),
    ("790", "Amarillo", ""), ("791", "Amarillo", ""), ("792", "Childress", ""), ("793", "Lubbock", ""),
    ("794", "Lubbock", ""), ("795", "Abilene", ""), ("796", "Abilene", ""), ("797", "Midland / Odessa", ""),
    ("798", "El Paso", ""), ("799", "El Paso", ""),
]

#: The Dallas and Fort Worth sectional centers. A code under one of these that no corridor claims and no OUTSIDE row
#: names is an UNCLAIMED regional code -- refused, and named in the boundary audit so it is visible.
VALLEY_PREFIXES = ("750", "751", "752", "753", "760", "761", "762")

#: The admitted counties. A premises whose OWN coordinates (or the State permit's own county) fall in any other county
#: is refused whatever its postal code's corridor (COUNTY_REFUSALS).
ADMITTED_COUNTY_NAMES = ("Dallas", "Tarrant", "Collin", "Denton")

#: The Texas Comptroller's own county numbering (hdzd-884n ``loc_county``) for the counties this registry names.
COMPTROLLER_COUNTY = {
    "57": "Dallas", "220": "Tarrant", "43": "Collin", "61": "Denton", "199": "Rockwall", "70": "Ellis",
    "126": "Johnson", "184": "Parker", "249": "Wise", "129": "Kaufman", "91": "Grayson", "49": "Cooke",
    "175": "Navarro", "116": "Hunt", "161": "McLennan", "111": "Hood", "213": "Somervell", "182": "Palo Pinto",
    "234": "Van Zandt", "107": "Henderson",
}

#: The county each admitted code is principally in, and the REAL municipalities (or postal localities) its premises
#: can be in -- principal first. The municipality a row PUBLISHES is decided by its premises' coordinates (the Census
#: boundary); this table is the fallback for a row without coordinates and the cross-check for every row. (The
#: inherited consumer name POSTAL_PARISH is kept: every downstream module reads it.)
POSTAL_PARISH = OrderedDict()


def _pp(county, munis, *zips):
    for z in zips:
        POSTAL_PARISH[z] = (county, tuple(munis))


# Dallas core / outer (City of Dallas preferred mailing name)
_pp("Dallas", ("dallas",), "75201", "75202", "75270", "75226", "75246", "75210", "75215", "75204", "75207",
    "75235", "75247", "75212", "75390", "75220", "75206", "75214", "75218", "75230", "75231", "75248", "75251",
    "75223", "75203", "75208", "75216", "75224", "75233")
_pp("Dallas", ("dallas", "highland park"), "75219", "75209")
_pp("Dallas", ("dallas", "farmers branch"), "75229")
_pp("Dallas", ("university park", "highland park", "dallas"), "75205")
_pp("Dallas", ("dallas", "university park"), "75225")
_pp("Dallas", ("university park",), "75275")
_pp("Dallas", ("dallas", "garland"), "75238")
_pp("Dallas", ("dallas", "addison", "farmers branch"), "75240", "75254")
_pp("Dallas", ("dallas", "richardson"), "75243", "75252")
_pp("Dallas", ("dallas", "carrollton", "addison"), "75287")
_pp("Dallas", ("dallas", "mesquite"), "75227", "75228")
_pp("Dallas", ("dallas", "balch springs", "mesquite"), "75217", "75253")
_pp("Dallas", ("dallas", "cockrell hill", "grand prairie"), "75211")
_pp("Dallas", ("dallas", "duncanville", "lancaster"), "75232")
_pp("Dallas", ("dallas", "grand prairie", "duncanville"), "75236", "75249")
_pp("Dallas", ("dallas", "duncanville", "desoto"), "75237")
_pp("Dallas", ("dallas", "hutchins", "lancaster"), "75241")
# DFW Airport and CentrePort
_pp("Tarrant", ("dfw airport", "grapevine", "irving", "euless", "coppell"), "75261")
_pp("Tarrant", ("fort worth", "euless"), "76155")
# Irving
_pp("Dallas", ("irving",), "75038", "75039", "75060", "75061", "75062", "75063", "75014", "75015", "75016", "75017")
# Arlington
_pp("Tarrant", ("arlington",), "76011", "76004", "76005", "76096", "76010", "76012", "76014", "76015", "76017",
    "76019", "76003", "76007", "76094")
_pp("Tarrant", ("arlington", "grand prairie"), "76006", "76018")
_pp("Tarrant", ("arlington", "pantego", "dalworthington gardens"), "76013", "76016")
_pp("Tarrant", ("arlington", "kennedale", "mansfield"), "76001", "76002")
# Fort Worth core
_pp("Tarrant", ("fort worth",), "76102", "76104", "76101", "76113", "76147", "76161", "76162", "76163", "76185",
    "76191", "76192", "76193", "76195", "76196", "76197", "76198", "76199", "76164", "76107", "76109", "76129",
    "76110", "76103", "76105", "76112", "76120", "76132", "76133", "76134", "76115", "76123")
_pp("Tarrant", ("fort worth", "saginaw", "lake worth"), "76106")
_pp("Tarrant", ("fort worth", "haltom city"), "76111")
_pp("Tarrant", ("fort worth", "saginaw"), "76131")
_pp("Tarrant", ("fort worth", "haltom city", "watauga"), "76137")
_pp("Tarrant", ("fort worth", "haslet"), "76177")
_pp("Tarrant", ("fort worth", "keller"), "76244")
_pp("Denton", ("roanoke", "trophy club", "northlake", "westlake", "keller"), "76262")
_pp("Tarrant", ("haslet", "fort worth"), "76052")
_pp("Tarrant", ("saginaw", "fort worth", "blue mound"), "76179")
_pp("Tarrant", ("keller",), "76248")
# Fort Worth outer
_pp("Tarrant", ("fort worth", "benbrook"), "76116")
_pp("Tarrant", ("white settlement", "fort worth"), "76108")
_pp("Tarrant", ("benbrook", "fort worth"), "76126")
_pp("Tarrant", ("fort worth", "lake worth", "sansom park"), "76135")
_pp("Tarrant", ("river oaks", "fort worth", "westworth village", "sansom park"), "76114")
_pp("Tarrant", ("naval air station jrb", "fort worth", "westworth village"), "76127")
_pp("Tarrant", ("azle", "lakeside", "pelican bay"), "76020")
_pp("Tarrant", ("forest hill", "fort worth"), "76119")
_pp("Tarrant", ("fort worth", "forest hill", "everman"), "76140")
_pp("Tarrant", ("crowley", "fort worth"), "76036")
_pp("Tarrant", ("fort worth", "burleson"), "76028")
_pp("Tarrant", ("kennedale", "fort worth", "arlington"), "76060")
# Mid-Cities, Grapevine, Coppell
_pp("Tarrant", ("grapevine",), "76051", "76099")
_pp("Dallas", ("coppell",), "75019", "75099")
_pp("Tarrant", ("euless", "fort worth"), "76039", "76040")
_pp("Tarrant", ("bedford",), "76021", "76022", "76095")
_pp("Tarrant", ("hurst",), "76053", "76054")
_pp("Tarrant", ("colleyville",), "76034")
_pp("Tarrant", ("north richland hills", "haltom city"), "76180")
_pp("Tarrant", ("north richland hills",), "76182")
_pp("Tarrant", ("richland hills", "north richland hills", "fort worth"), "76118")
_pp("Tarrant", ("haltom city", "north richland hills", "fort worth"), "76117")
_pp("Tarrant", ("watauga", "north richland hills", "haltom city"), "76148")
# Grand Prairie
_pp("Dallas", ("grand prairie",), "75050", "75052", "75053", "75054")
_pp("Dallas", ("grand prairie", "dallas", "cedar hill"), "75051")
# North Dallas corporate
_pp("Dallas", ("addison",), "75001")
_pp("Dallas", ("richardson",), "75080", "75081", "75083", "75085")
_pp("Collin", ("richardson",), "75082")
_pp("Collin", ("plano",), "75024", "75093", "75023", "75025", "75026", "75074", "75075", "75086")
_pp("Collin", ("plano", "murphy", "parker"), "75094")
_pp("Collin", ("frisco",), "75034", "75033", "75035")
_pp("Denton", ("frisco", "little elm"), "75036")
_pp("Dallas", ("carrollton", "farmers branch"), "75006")
_pp("Denton", ("carrollton",), "75007", "75010")
_pp("Dallas", ("carrollton",), "75011")
_pp("Dallas", ("farmers branch", "dallas"), "75234", "75244")
_pp("Dallas", ("farmers branch",), "75381")
_pp("Denton", ("the colony",), "75056")
_pp("Denton", ("lewisville",), "75057", "75067", "75029")
_pp("Denton", ("lewisville", "highland village", "double oak"), "75077")
# FRINGE
_pp("Tarrant", ("southlake", "grapevine", "keller"), "76092")
_pp("Denton", ("flower mound", "bartonville"), "75022")
_pp("Denton", ("flower mound",), "75028", "75027")
_pp("Collin", ("allen",), "75013")
_pp("Collin", ("allen", "lucas", "parker"), "75002")
_pp("Collin", ("mckinney",), "75070", "75071")
_pp("Collin", ("mckinney", "fairview", "lowry crossing"), "75069")
_pp("Collin", ("mckinney", "frisco"), "75072")
_pp("Dallas", ("mesquite",), "75149", "75185", "75187")
_pp("Dallas", ("mesquite", "dallas"), "75150")
_pp("Dallas", ("mesquite", "balch springs"), "75181")
_pp("Dallas", ("balch springs",), "75180")
_pp("Dallas", ("sunnyvale",), "75182")
_pp("Dallas", ("garland",), "75040", "75041", "75042", "75045", "75046", "75047", "75049")
_pp("Dallas", ("garland", "rowlett"), "75043")
_pp("Dallas", ("garland", "richardson"), "75044")
_pp("Dallas", ("sachse", "garland"), "75048")
_pp("Dallas", ("rowlett",), "75088", "75089", "75030")
_pp("Dallas", ("desoto",), "75115", "75123")
_pp("Dallas", ("duncanville",), "75116", "75137", "75138")
_pp("Dallas", ("cedar hill",), "75104", "75106")
_pp("Dallas", ("lancaster",), "75134", "75146")
_pp("Dallas", ("hutchins", "wilmer"), "75141")
_pp("Dallas", ("wilmer",), "75172")
_pp("Dallas", ("seagoville", "dallas"), "75159")
_pp("Tarrant", ("mansfield",), "76063")

POSTAL_COUNTY = POSTAL_PARISH

#: Postal localities that are NOT municipalities (a mailing name, never a published city).
NON_MUNICIPAL_LOCALITIES = {"dfw airport": "the airport's own postal locality; the premises are in Grapevine, "
                                           "Irving, Euless or Coppell, decided by the Census boundary",
                            "naval air station jrb": "the base's own postal locality -- MILITARY_RESTRICTED"}

#: How each real municipality is written when it is published.
MUNICIPALITY_DISPLAY = {
    "dallas": "Dallas", "fort worth": "Fort Worth", "irving": "Irving", "grapevine": "Grapevine",
    "euless": "Euless", "coppell": "Coppell", "bedford": "Bedford", "hurst": "Hurst", "arlington": "Arlington",
    "grand prairie": "Grand Prairie", "addison": "Addison", "richardson": "Richardson", "plano": "Plano",
    "frisco": "Frisco", "carrollton": "Carrollton", "farmers branch": "Farmers Branch", "the colony": "The Colony",
    "lewisville": "Lewisville", "allen": "Allen", "mckinney": "McKinney", "flower mound": "Flower Mound",
    "southlake": "Southlake", "roanoke": "Roanoke", "mansfield": "Mansfield", "mesquite": "Mesquite",
    "garland": "Garland", "rowlett": "Rowlett", "sachse": "Sachse", "balch springs": "Balch Springs",
    "sunnyvale": "Sunnyvale", "desoto": "DeSoto", "duncanville": "Duncanville", "cedar hill": "Cedar Hill",
    "lancaster": "Lancaster", "hutchins": "Hutchins", "wilmer": "Wilmer", "seagoville": "Seagoville",
    "highland park": "Highland Park", "university park": "University Park", "cockrell hill": "Cockrell Hill",
    "colleyville": "Colleyville", "north richland hills": "North Richland Hills", "richland hills": "Richland Hills",
    "haltom city": "Haltom City", "watauga": "Watauga", "keller": "Keller", "trophy club": "Trophy Club",
    "northlake": "Northlake", "westlake": "Westlake", "haslet": "Haslet", "saginaw": "Saginaw",
    "blue mound": "Blue Mound", "lake worth": "Lake Worth", "sansom park": "Sansom Park",
    "white settlement": "White Settlement", "benbrook": "Benbrook", "river oaks": "River Oaks",
    "westworth village": "Westworth Village", "azle": "Azle", "lakeside": "Lakeside", "pelican bay": "Pelican Bay",
    "forest hill": "Forest Hill", "everman": "Everman", "crowley": "Crowley", "burleson": "Burleson",
    "kennedale": "Kennedale", "pantego": "Pantego", "dalworthington gardens": "Dalworthington Gardens",
    "murphy": "Murphy", "parker": "Parker", "little elm": "Little Elm", "highland village": "Highland Village",
    "double oak": "Double Oak", "bartonville": "Bartonville", "lucas": "Lucas", "fairview": "Fairview",
    "lowry crossing": "Lowry Crossing", "dfw airport": "DFW Airport",
    "naval air station jrb": "Naval Air Station Fort Worth JRB",
}

ADMITTED_PARISHES = {
    "dallas (admitted whole: dallas, irving, grand prairie's dallas county land, garland, mesquite, richardson, "
    "carrollton, farmers branch, addison, coppell, the park cities, the south and east ring)",
    "tarrant (admitted whole: fort worth, arlington, the mid-cities, grapevine, southlake, mansfield, the fort worth "
    "ring, dfw airport)",
    "collin (south tier: plano, frisco, allen, mckinney, richardson and dallas land)",
    "denton (south tier: lewisville, the colony, flower mound, carrollton, frisco, roanoke / trophy club / northlake)",
}
OBSERVED_PARISHES = OrderedDict([
    ("denton (denton, corinth, lake dallas, argyle, justin, sanger)", "denton-tx"),
    ("collin north / east (prosper, celina, wylie, princeton, anna, melissa)", "(none -- refused after careful evaluation)"),
    ("rockwall (rockwall, fate, heath, royse city)", "(none -- refused after careful evaluation)"),
    ("kaufman (forney, terrell, kaufman)", "(none -- refused)"),
    ("ellis (waxahachie, ennis, midlothian, red oak)", "waxahachie-ennis-tx"),
    ("johnson (cleburne, burleson, alvarado, joshua)", "(none -- refused)"),
    ("parker (weatherford, aledo, willow park)", "weatherford-tx"),
    ("wise (decatur, rhome, bridgeport)", "decatur-tx"),
    ("hood / somervell / palo pinto (granbury, glen rose, mineral wells)", "(none -- refused)"),
    ("navarro (corsicana)", "corsicana-tx"),
    ("hunt (greenville)", "greenville-tx"),
    ("grayson (sherman, denison)", "sherman-denison-tx"),
    ("cooke (gainesville)", "gainesville-tx"),
    ("mclennan (waco)", "waco-tx"),
])
OBSERVED_COUNTIES = OBSERVED_PARISHES
ADMITTED_COUNTIES = ADMITTED_PARISHES

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("dallas", OrderedDict([("ruling", "ADMITTED WHOLE, MUNICIPALITIES PRESERVED. Dallas, Irving, Grand Prairie, "
                                       "Garland, Mesquite, Richardson, Carrollton, Farmers Branch, Addison, Coppell, "
                                       "Highland Park, University Park, Rowlett, Sachse, Balch Springs, Sunnyvale, "
                                       "DeSoto, Duncanville, Cedar Hill, Lancaster, Hutchins, Wilmer and Seagoville "
                                       "each keep their own name.")])),
    ("tarrant", OrderedDict([("ruling", "ADMITTED WHOLE, MUNICIPALITIES PRESERVED. Fort Worth, Arlington, Grapevine, "
                                        "Euless, Bedford, Hurst, Colleyville, Southlake, Keller, North Richland Hills, "
                                        "Richland Hills, Haltom City, Watauga, Saginaw, Haslet, Lake Worth, White "
                                        "Settlement, Benbrook, River Oaks, Forest Hill, Everman, Crowley, Kennedale, "
                                        "Mansfield, Pantego, Dalworthington Gardens and Azle each keep their own "
                                        "name.")])),
    ("collin", OrderedDict([("ruling", "SOUTH TIER ADMITTED: Plano, Frisco (Collin land), Allen, McKinney, Murphy, "
                                       "Parker, Lucas, Fairview and Richardson's / Dallas's Collin land. Prosper, "
                                       "Celina, Wylie, Lavon, Princeton, Anna, Melissa and Farmersville refused.")])),
    ("denton", OrderedDict([("ruling", "SOUTH TIER ADMITTED: Lewisville, The Colony, Highland Village, Flower Mound, "
                                       "Bartonville, Carrollton (Denton land), Frisco (Denton land), Dallas's Denton "
                                       "land and Roanoke / Trophy Club / Northlake / Westlake. Denton, Corinth, Lake "
                                       "Dallas, Hickory Creek, Argyle, Justin, Little Elm, Sanger, Aubrey and Pilot "
                                       "Point refused (FUTURE_STANDALONE denton-tx).")])),
    ("rockwall / kaufman / ellis / johnson / parker / wise", OrderedDict([
        ("ruling", "EVALUATED AND REFUSED. A premises whose own coordinates (or State permit county) are in one of "
                   "these counties is refused whatever its mailing label -- Rowlett's Rockwall land, Mansfield's and "
                   "Burleson's Johnson / Ellis land, Parker County land inside 76108 / 76020.")])),
])

#: A premises whose OWN county (Census boundary or State permit) is one of these is refused whatever its postal code's
#: corridor.
COUNTY_REFUSALS = OrderedDict([
    ("rockwall", "a premises in ROCKWALL COUNTY -- east of Lake Ray Hubbard, refused after careful evaluation"),
    ("kaufman", "a premises in KAUFMAN COUNTY -- refused"),
    ("ellis", "a premises in ELLIS COUNTY -- FUTURE_STANDALONE waxahachie-ennis-tx"),
    ("johnson", "a premises in JOHNSON COUNTY -- refused (Burleson / Cleburne)"),
    ("parker", "a premises in PARKER COUNTY -- FUTURE_STANDALONE weatherford-tx"),
    ("wise", "a premises in WISE COUNTY -- FUTURE_STANDALONE decatur-tx"),
    ("hood", "a premises in HOOD COUNTY -- refused"), ("grayson", "a premises in GRAYSON COUNTY -- refused"),
    ("hunt", "a premises in HUNT COUNTY -- refused"), ("navarro", "a premises in NAVARRO COUNTY -- refused"),
    ("cooke", "a premises in COOKE COUNTY -- refused"), ("mclennan", "a premises in McLENNAN COUNTY -- refused"),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / patient / member
#: only). A normalised-name substring match; the census row keeps its reason.
NONPUBLIC_NAMES = {
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- MILITARY_RESTRICTED",
    "navy lodge": "Navy Lodge on-base lodging -- MILITARY_RESTRICTED",
    "navy gateway inns": "Navy Gateway Inns & Suites on-base lodging (NAS Fort Worth JRB) -- MILITARY_RESTRICTED",
    "gateway inns and suites": "Navy Gateway Inns & Suites on-base lodging (NAS Fort Worth JRB) -- MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "bachelor quarters": "military bachelor quarters -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "hope lodge": "American Cancer Society Hope Lodge -- patient lodging, not public lodging",
    "family housing": "patient-family housing -- not public lodging",
    "patient housing": "patient housing -- not public lodging",
    "rescue mission": "rescue mission shelter -- not public lodging",
    "homeless": "shelter -- not public lodging",
    "salvation army": "Salvation Army shelter -- not public lodging",
    "youth shelter": "youth shelter -- not public lodging",
    "union gospel mission": "Union Gospel Mission shelter -- not public lodging",
    "austin street center": "Austin Street Center shelter -- not public lodging",
    "the bridge homeless": "The Bridge homeless recovery center -- not public lodging",
}

#: Military postal codes inside the admitted partition: Naval Air Station Fort Worth Joint Reserve Base.
MILITARY_POSTAL_CODES = OrderedDict([
    ("76127", "Naval Air Station Fort Worth Joint Reserve Base (on-base Navy Gateway Inns & Suites)"),
])

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-dallas", "Dallas", "Downtown / Arts District / Deep Ellum", 32.7810, -96.7970, 2500, True),
    ("uptown-victory-park", "Dallas", "Uptown / Victory Park / Oak Lawn", 32.8030, -96.8080, 2200, True),
    ("love-field-medical-market-center", "Dallas", "Love Field / Medical District / Market Center / Stemmons",
     32.8250, -96.8530, 5000, True),
    ("park-cities-preston-center", "Dallas", "Park Cities / Preston Center / NorthPark / Knox", 32.8500, -96.7900,
     4500, True),
    ("north-dallas-galleria", "Dallas", "Galleria / LBJ / Park Central / Far North Dallas", 32.9250, -96.8000, 6000,
     True),
    ("dfw-airport", "DFW Airport", "DFW Airport / CentrePort", 32.8800, -97.0400, 6500, True),
    ("irving-las-colinas", "Irving", "Las Colinas / Irving / Valley Ranch", 32.8700, -96.9600, 7000, True),
    ("arlington-entertainment", "Arlington", "AT&T Stadium / Globe Life Field / Six Flags", 32.7550, -97.0850, 3500,
     True),
    ("downtown-fort-worth", "Fort Worth", "Downtown / Sundance Square / Near Southside", 32.7450, -97.3300, 3000, True),
    ("stockyards-north-side", "Fort Worth", "Stockyards / North Side", 32.7900, -97.3450, 3000, True),
    ("cultural-district-tcu", "Fort Worth", "Cultural District / West 7th / TCU", 32.7350, -97.3700, 3500, True),
    ("alliance-north-fort-worth", "Fort Worth", "Alliance / North Fort Worth / Roanoke", 32.9300, -97.2900, 9000,
     True),
    ("east-dallas", "Dallas", "East Dallas / I-30 / I-635", 32.7900, -96.6900, 6000, True),
    ("oak-cliff-south-dallas", "Dallas", "Oak Cliff / I-35E / I-20", 32.6900, -96.8500, 8000, True),
    ("grapevine-coppell", "Grapevine", "Grapevine / Coppell", 32.9400, -97.0600, 6000, True),
    ("mid-cities", "Euless", "Euless / Bedford / Hurst / NRH", 32.8400, -97.1700, 8000, True),
    ("arlington", "Arlington", "Arlington / UTA / I-20", 32.7000, -97.1100, 8000, True),
    ("grand-prairie", "Grand Prairie", "Grand Prairie", 32.7200, -97.0000, 7000, True),
    ("fort-worth-west", "Fort Worth", "West Fort Worth / I-30 / White Settlement", 32.7400, -97.4400, 8000, True),
    ("fort-worth-south", "Fort Worth", "South Fort Worth / I-20 / I-35W", 32.6600, -97.3400, 9000, True),
    ("fort-worth-east", "Fort Worth", "East Fort Worth / I-30 East", 32.7500, -97.2300, 6000, True),
    ("addison", "Addison", "Addison", 32.9600, -96.8300, 2500, True),
    ("richardson", "Richardson", "Richardson / Telecom Corridor", 32.9700, -96.7300, 5000, True),
    ("plano", "Plano", "Plano / Legacy / Granite Park", 33.0500, -96.7700, 9000, True),
    ("frisco", "Frisco", "Frisco / The Star / Stonebriar", 33.1300, -96.8200, 8000, True),
    ("carrollton-farmers-branch", "Carrollton", "Carrollton / Farmers Branch", 32.9500, -96.8900, 6000, True),
    ("lewisville-the-colony", "Lewisville", "Lewisville / The Colony", 33.0600, -96.9500, 7000, True),
    ("southlake-flower-mound", "Southlake", "Southlake / Flower Mound", 33.0000, -97.1200, 8000, True),
    ("allen-mckinney", "Allen", "Allen / McKinney", 33.1500, -96.6600, 10000, True),
    ("garland-mesquite-rowlett", "Mesquite", "Garland / Mesquite / Rowlett", 32.8300, -96.6200, 10000, True),
    ("south-dallas-county", "DeSoto", "DeSoto / Duncanville / Cedar Hill / Lancaster", 32.6100, -96.8300, 10000, True),
    ("mansfield", "Mansfield", "Mansfield", 32.5700, -97.1300, 5000, True),
    ("obs-denton", "Denton", "Denton / Corinth -- OBSERVATION ONLY", 33.2100, -97.1300, 10000, False),
    ("obs-rockwall", "Rockwall", "Rockwall / Royse City -- OBSERVATION ONLY", 32.9100, -96.4500, 9000, False),
    ("obs-weatherford", "Weatherford", "Weatherford / Willow Park -- OBSERVATION ONLY", 32.7600, -97.7700, 9000,
     False),
    ("obs-waxahachie", "Waxahachie", "Waxahachie / Midlothian / Red Oak -- OBSERVATION ONLY", 32.4200, -96.8700,
     12000, False),
    ("obs-burleson-cleburne", "Burleson", "Burleson / Cleburne -- OBSERVATION ONLY", 32.4800, -97.3500, 12000, False),
]

#: The observation box. It reaches north past Denton, Prosper and Celina, east past Rockwall and Forney, south past
#: Waxahachie, Midlothian and Cleburne and west past Weatherford, so the census counts what it refuses. Texas beyond
#: it (Sherman / Denison, Gainesville, Corsicana, Waco, Greenville) is MEASURED by the hotel-tax register for the
#: boundary audit only.
BOUNDS = {"min_lat": 32.25, "max_lat": 33.45, "min_lng": -97.85, "max_lng": -96.25}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
#: The nearest anchor within its radius wins.
COVERAGE_AREAS = [
    ("DFW Airport (on-airport)", 32.8990, -97.0400, 3.2),
    ("Dallas Love Field", 32.8470, -96.8520, 1.4),
    ("AT&T Stadium / Globe Life Field / Texas Live!", 32.7500, -97.0880, 1.6),
    ("Six Flags Over Texas", 32.7560, -97.0700, 1.0),
    ("Fort Worth Stockyards", 32.7890, -97.3470, 1.2),
    ("Sundance Square", 32.7530, -97.3320, 0.9),
    ("Arts District", 32.7890, -96.8000, 0.6),
    ("Deep Ellum", 32.7840, -96.7820, 0.8),
    ("Victory Park", 32.7900, -96.8100, 0.6),
    ("Las Colinas", 32.8780, -96.9450, 3.0),
    ("Legacy West / Legacy", 33.0780, -96.8270, 2.5),
    ("Granite Park", 33.0800, -96.8000, 1.2),
    ("The Star (Frisco)", 33.1100, -96.8290, 1.5),
    ("Stonebriar", 33.1000, -96.8150, 1.5),
    ("Galleria / LBJ", 32.9300, -96.8200, 2.0),
    ("Medical District", 32.8120, -96.8400, 1.4),
    ("Market Center / Design District", 32.7980, -96.8250, 1.5),
    ("Cultural District / West 7th", 32.7510, -97.3600, 1.3),
    ("Alliance", 32.9800, -97.3100, 5.0),
    ("Grapevine Main Street / Gaylord Texan", 32.9400, -97.0750, 2.5),
    ("CentrePort", 32.8350, -97.0650, 2.0),
    ("Addison Circle", 32.9580, -96.8290, 1.5),
    ("Preston Center / NorthPark", 32.8650, -96.7750, 1.8),
    ("Downtown Dallas", 32.7810, -96.7970, 1.8),
    ("Downtown Fort Worth", 32.7500, -97.3300, 1.8),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin). Reporting only.
STREET_OVERLAYS = [
    ("DFW Airport (on-airport)", re.compile(r"\b(international (pkwy|parkway)|terminal d|dfw airport)\b(?=.*\b75261\b)",
                                            re.I)),
    ("Dallas Love Field", re.compile(r"\b(herb kelleher|w(est)? mockingbird (ln|lane)|cedar springs (rd|road)|"
                                     r"lemmon (ave|avenue))\b(?=.*\b752(09|35)\b)", re.I)),
    ("AT&T Stadium / Globe Life Field / Texas Live!", re.compile(r"\b(ballpark (way|dr)|nolan ryan|"
                                                                  r"stadium (dr|drive)|e(ast)? randol mill)\b"
                                                                  r"(?=.*\b7601[1]\b)", re.I)),
    ("Fort Worth Stockyards", re.compile(r"\b(exchange (ave|avenue)|stockyards (blvd|boulevard)|n(orth)? main (st|"
                                         r"street)|rodeo plaza)\b(?=.*\b7616[4]|76106\b)", re.I)),
    ("Legacy West / Legacy", re.compile(r"\b(legacy (dr|drive)|headquarters (dr|drive)|tennyson (pkwy|parkway)|"
                                        r"windrose|bishop (ave|avenue))\b(?=.*\b75024\b)", re.I)),
    ("The Star (Frisco)", re.compile(r"\b(cowboys way|the star)\b(?=.*\b7503[34]\b)", re.I)),
    ("CentrePort", re.compile(r"\b(centreport|amon carter (blvd|boulevard))\b(?=.*\b76155\b)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {c[0]: c[1] for c in CORRIDORS}

#: The order's CORE / STRONG / CAREFUL / KEEP-SEPARATE evaluation list, each classified.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Dallas", "ADMITTED (CORE, downtown-dallas, 75201 / 75202 / 75270)."),
    ("Uptown", "ADMITTED (CORE, uptown-victory-park, 75204 / 75219)."),
    ("Victory Park", "ADMITTED (CORE, uptown-victory-park 75219 / downtown-dallas 75201) -- overlay."),
    ("Arts District", "ADMITTED (CORE, downtown-dallas, 75201) -- overlay."),
    ("Deep Ellum", "ADMITTED (CORE, downtown-dallas, 75226)."),
    ("Design District", "ADMITTED (CORE, love-field-medical-market-center, 75207)."),
    ("Medical District", "ADMITTED (CORE, love-field-medical-market-center, 75235 / 75390)."),
    ("Market Center", "ADMITTED (CORE, love-field-medical-market-center, 75207 / 75247)."),
    ("Love Field", "ADMITTED (CORE, love-field-medical-market-center, 75235 / 75209 / 75220) -- never DFW Airport."),
    ("Park Cities", "ADMITTED (CORE, park-cities-preston-center, 75205 / 75225 / 75275) -- Highland Park and "
                    "University Park keep their own names."),
    ("North Dallas", "ADMITTED (CORE, north-dallas-galleria)."),
    ("Galleria / LBJ", "ADMITTED (CORE, north-dallas-galleria, 75240 / 75254 / 75251)."),
    ("Preston Center", "ADMITTED (CORE, park-cities-preston-center, 75225)."),
    ("Downtown Fort Worth", "ADMITTED (CORE, downtown-fort-worth, 76102)."),
    ("Sundance Square", "ADMITTED (CORE, downtown-fort-worth, 76102) -- overlay."),
    ("Fort Worth Stockyards", "ADMITTED (CORE, stockyards-north-side, 76164 / 76106)."),
    ("Cultural District", "ADMITTED (CORE, cultural-district-tcu, 76107)."),
    ("Near Southside", "ADMITTED (CORE, downtown-fort-worth, 76104)."),
    ("Fort Worth Medical District", "ADMITTED (CORE, downtown-fort-worth, 76104)."),
    ("TCU / University", "ADMITTED (CORE, cultural-district-tcu, 76109 / 76129)."),
    ("Alliance / North Fort Worth", "ADMITTED (CORE, alliance-north-fort-worth, 76177 / 76131 / 76137 / 76244)."),
    ("DFW International Airport", "ADMITTED (CORE, dfw-airport, 75261) -- DFW_AIRPORT_EVALUATION."),
    ("Irving", "ADMITTED (CORE, irving-las-colinas). Municipality IRVING, never Dallas."),
    ("Las Colinas", "ADMITTED (CORE, irving-las-colinas, 75038 / 75039) -- overlay."),
    ("Grapevine", "ADMITTED (STRONG CORRIDOR, grapevine-coppell, 76051)."),
    ("Coppell", "ADMITTED (STRONG CORRIDOR, grapevine-coppell, 75019)."),
    ("Euless", "ADMITTED (STRONG CORRIDOR, mid-cities, 76039 / 76040)."),
    ("Bedford", "ADMITTED (STRONG CORRIDOR, mid-cities, 76021 / 76022)."),
    ("Hurst", "ADMITTED (STRONG CORRIDOR, mid-cities, 76053 / 76054)."),
    ("Arlington", "ADMITTED (CORE arlington-entertainment 76011 / 76006; STRONG CORRIDOR arlington for the rest)."),
    ("Entertainment District / AT&T Stadium / Globe Life Field / Six Flags", "ADMITTED (CORE, arlington-entertainment, "
                                                                              "76011)."),
    ("Grand Prairie", "ADMITTED (STRONG CORRIDOR, grand-prairie, 75050-75054). Never Dallas, never Arlington."),
    ("Addison", "ADMITTED (STRONG CORRIDOR, addison, 75001; Addison land in 75254 / 75244 by premises)."),
    ("Richardson", "ADMITTED (STRONG CORRIDOR, richardson, 75080-75085; Richardson land in 75243 / 75252 by "
                   "premises)."),
    ("Plano", "ADMITTED (STRONG CORRIDOR, plano). PLANO PROFILES LABELED DALLAS = 0."),
    ("Frisco", "ADMITTED (STRONG CORRIDOR, frisco). FRISCO PROFILES LABELED DALLAS = 0."),
    ("Carrollton", "ADMITTED (STRONG CORRIDOR, carrollton-farmers-branch, 75006 / 75007 / 75010)."),
    ("Farmers Branch", "ADMITTED (STRONG CORRIDOR, carrollton-farmers-branch, 75234 / 75244 -- Dallas-preferred codes "
                       "decided by premises)."),
    ("The Colony", "ADMITTED (STRONG CORRIDOR, lewisville-the-colony, 75056)."),
    ("Lewisville", "ADMITTED (STRONG CORRIDOR, lewisville-the-colony, 75057 / 75067 / 75077)."),
    ("Allen", "ADMITTED (FRINGE, allen-mckinney, 75013 / 75002). CAREFUL."),
    ("McKinney", "ADMITTED (FRINGE, allen-mckinney, 75069-75072). CAREFUL: continuous with Allen, Plano and Frisco "
                 "along US-75 and SH-121."),
    ("Flower Mound", "ADMITTED (FRINGE, southlake-flower-mound, 75022 / 75028). CAREFUL."),
    ("Southlake", "ADMITTED (FRINGE, southlake-flower-mound, 76092). CAREFUL."),
    ("Roanoke", "ADMITTED (CORE corridor alliance-north-fort-worth, 76262) -- keeps its own name. CAREFUL."),
    ("Mansfield", "ADMITTED (FRINGE, mansfield, 76063). CAREFUL; Johnson / Ellis edge refused by county."),
    ("Denton", "OUTSIDE -- FUTURE_STANDALONE denton-tx; refused by postal code after careful evaluation."),
    ("Mesquite", "ADMITTED (FRINGE, garland-mesquite-rowlett, 75149 / 75150 / 75181). CAREFUL."),
    ("Garland", "ADMITTED (FRINGE, garland-mesquite-rowlett, 75040-75049). CAREFUL."),
    ("Rockwall", "OUTSIDE -- Rockwall County east of Lake Ray Hubbard; refused by postal code and county after careful "
                 "evaluation."),
    ("Weatherford", "OUTSIDE -- FUTURE_STANDALONE weatherford-tx. KEEP SEPARATE."),
    ("Decatur", "OUTSIDE -- FUTURE_STANDALONE decatur-tx. KEEP SEPARATE."),
    ("Waxahachie", "OUTSIDE -- FUTURE_STANDALONE waxahachie-ennis-tx. KEEP SEPARATE."),
    ("Ennis", "OUTSIDE -- FUTURE_STANDALONE waxahachie-ennis-tx. KEEP SEPARATE."),
    ("Corsicana", "OUTSIDE -- FUTURE_STANDALONE corsicana-tx. KEEP SEPARATE."),
    ("Greenville", "OUTSIDE -- FUTURE_STANDALONE greenville-tx; prefix 754. KEEP SEPARATE."),
    ("Sherman / Denison", "OUTSIDE -- FUTURE_STANDALONE sherman-denison-tx. KEEP SEPARATE."),
    ("Gainesville", "OUTSIDE -- FUTURE_STANDALONE gainesville-tx. KEEP SEPARATE."),
    ("Waco", "OUTSIDE -- FUTURE_STANDALONE waco-tx; prefixes 766 / 767. KEEP SEPARATE."),
])

#: The airport ruling, stated once (Phase 5).
DFW_AIRPORT_EVALUATION = OrderedDict([
    ("airport_land", "Dallas/Fort Worth International Airport's land is postal code 75261 ('DFW Airport, TX'), inside "
                     "the city limits of Grapevine, Irving, Euless and Coppell. Its on-airport hotels -- the Grand "
                     "Hyatt DFW inside Terminal D and the Hyatt Regency DFW on International Parkway -- publish the "
                     "municipality the Census boundary puts their premises in."),
    ("airport_area_rows", "Hotels marketed 'DFW Airport North' (Irving 75063, Grapevine 76051, Coppell 75019), 'DFW "
                          "Airport South' (Irving 75062, Fort Worth CentrePort 76155, Euless 76040) and 'DFW Airport "
                          "West' (Euless 76039, Grapevine) are placed by their own postal code and publish their own "
                          "municipality; CentrePort (76155) joins the airport corridor."),
    ("one_premises_one_row", "A property is ONE row however many of 'Dallas', 'Fort Worth', 'Dallas/Fort Worth', 'DFW "
                             "Airport', 'Airport North' and 'Airport South' its marketing carries; identity is its own "
                             "street address, phone and brand property code."),
    ("never_love_field", "A DFW Airport row never borrows Love Field evidence, and vice versa (LOVE_FIELD_EVALUATION)."),
])
#: Inherited consumer name.
RSW_AIRPORT_EVALUATION = DFW_AIRPORT_EVALUATION

LOVE_FIELD_EVALUATION = OrderedDict([
    ("airport", "Dallas Love Field, 8008 Herb Kelleher Way, Dallas 75235 -- a City of Dallas airport."),
    ("hotel_rows", "Mockingbird Lane / Cedar Springs / Lemmon Avenue (75235 / 75209), Harry Hines Boulevard / Walnut "
                   "Hill / Northwest Highway / Bachman Lake (75220 / 75229); the Medical District (75235 / 75390) and "
                   "Market Center / Stemmons (75207 / 75247) share the corridor."),
    ("separation", "A Love Field row is a different premises from every DFW Airport row; a brand's 'Dallas Airport' "
                   "or 'Dallas Market Center' marketing never moves evidence between them."),
])

ARLINGTON_EVALUATION = OrderedDict([
    ("district", "AT&T Stadium, Globe Life Field, Choctaw Stadium, Texas Live! (with Live! by Loews) and Six Flags "
                 "Over Texas / Hurricane Harbor -- 76011; the I-30 / Collins / Lamar / Brookhollow rows -- 76006."),
    ("protections", "Apartment towers marketed to fans, event-only lodging packages and stadium-week vacation rentals "
                    "are never hotels. A renamed hotel publishes only under its current operator's name on its "
                    "current page; a same-campus pair (Live! by Loews and its neighbours) is two premises."),
])

PLANO_FRISCO_EVALUATION = OrderedDict([
    ("plano", "Legacy, Legacy West and Granite Park are Plano 75024 / 75093; the US-75 rows are Plano 75074 / 75075 / "
              "75023. 'Dallas Plano', 'Dallas North' and 'Dallas Legacy' are marketing."),
    ("frisco", "The Star, Stonebriar, Hall Park and the Frisco convention district are Frisco 75034 / 75033; Toyota "
               "Stadium is Frisco 75035. Frisco's Denton County land (75036 / 75033 / 75034) keeps Frisco."),
    ("rule", "PLANO PROFILES LABELED DALLAS = 0 and FRISCO PROFILES LABELED DALLAS = 0 are counted over the census."),
])

ALLIANCE_EVALUATION = OrderedDict([
    ("alliance", "AllianceTexas, Alliance Town Center and Heritage Trace are inside the City of Fort Worth (76177 / "
                 "76244); Roanoke, Trophy Club, Northlake and Westlake (76262), Haslet (76052) and Keller (76248) "
                 "keep their own names."),
    ("far_north", "Denton County's far north (Denton, Corinth, Justin, Argyle, Ponder) is refused even when a brand "
                  "page markets it 'Fort Worth North' or 'Alliance'."),
])

#: The market ruling.
FORT_MYERS_RULING = OrderedDict([
    ("classification", "The Dallas-Fort Worth market is admitted as Dallas and Tarrant counties whole plus the south "
                       "tiers of Collin and Denton -- 12 CORE corridors (Dallas's downtown, Uptown, Love Field / "
                       "Medical / Market Center, Park Cities, North Dallas / Galleria; DFW Airport; Irving / Las "
                       "Colinas; the Arlington entertainment district; Fort Worth's downtown, Stockyards, Cultural "
                       "District / TCU and Alliance), 15 STRONG CORRIDORS and 5 FRINGE corridors. Denton, Rockwall, "
                       "Weatherford, Decatur, Waxahachie, Ennis, Corsicana, Greenville, Sherman / Denison, Gainesville "
                       "and Waco are OUTSIDE."),
    ("a_marketing_phrase_admits_nothing", "'Dallas', 'Fort Worth', 'Dallas/Fort Worth', 'DFW Airport', 'Dallas North', "
                                          "'Galleria', 'Alliance' and 'Arlington Entertainment District' are "
                                          "marketing. The property's own postal code decides membership; its own "
                                          "premises decide its municipality and county."),
    ("actual_location", "Membership by the property's own postal code; municipality and county by the Census "
                        "boundary that contains its premises; a refused county refuses."),
    ("drive_market_relationship", "Both downtowns, the airports, Las Colinas, the Mid-Cities, Arlington's stadiums and "
                                  "the north Dallas corporate corridors are where Metroplex travellers sleep; Denton, "
                                  "Waco, Sherman and the lake towns are trips of their own."),
    ("traveller_intent", "Conventions (Kay Bailey Hutchison, Irving, Fort Worth, Grapevine's Gaylord Texan, Frisco), "
                         "the airports, stadium and theme-park events, the Medical Districts, corporate travel to "
                         "Legacy, Las Colinas and the Telecom Corridor, the Stockyards and the universities (SMU, TCU, "
                         "UTA, UTD) are this market's intent."),
    ("metro_continuity", "Continuous development runs from Fort Worth through the Mid-Cities and Arlington to Dallas, "
                         "and north along the Tollway, US-75, I-35E and SH-121 to Frisco, McKinney and Lewisville; this "
                         "registry stops at Denton, Prosper, Wylie, Lake Ray Hubbard, the Ellis / Johnson / Parker "
                         "lines and Wise County."),
    ("corridor_support", "Every admitted edge code is in a named corridor so its count is visible and a founder can "
                         "move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE denton-tx, waxahachie-ennis-tx, weatherford-tx, decatur-tx, corsicana-tx, "
                      "greenville-tx, sherman-denison-tx, gainesville-tx and waco-tx."),
])
DALLAS_FORT_WORTH_RULING = FORT_MYERS_RULING

STRUCTURE_TEST = OrderedDict([
    ("A. Is Dallas-Fort Worth one market?",
     "ONE market, dallas-fort-worth-tx: one airport system (DFW, Love Field), one freeway grid, continuous lodging "
     "from Fort Worth to Mesquite and from DeSoto to McKinney."),
    ("B. Municipalities are NOT flattened",
     "Every corridor names its municipality, every admitted code carries its county and real municipalities, and every "
     "row publishes the municipality its premises are in (Census boundary). Irving, Grapevine, Arlington, Plano, "
     "Frisco, Addison, Richardson and every suburb are never written as Dallas or Fort Worth."),
    ("C. DFW Airport", "75261 + CentrePort; 'DFW Airport' hotels elsewhere placed by their own code."),
    ("D. Love Field", "A Dallas airport in its own corridor; never DFW evidence."),
    ("E. Arlington stadiums", "76011 / 76006; hotel premises only."),
    ("F. Plano / Frisco", "Their own corridors; never Dallas."),
    ("G. Alliance", "Fort Worth only inside the City of Fort Worth; Roanoke / Trophy Club / Northlake / Haslet keep "
                    "their own names."),
    ("H. Denton / McKinney", "Denton OUTSIDE (denton-tx); McKinney FRINGE with Allen."),
    ("I. Outer North Texas", "Weatherford, Decatur, Waxahachie, Ennis, Corsicana, Greenville, Sherman / Denison, "
                             "Gainesville and Waco OUTSIDE."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel operation (front desk)."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP). A unit designator ('Ste', "
     "'Unit', '#', 'Apt') in a register address means the record is a UNIT INSIDE a building, which is never a hotel "
     "identity."),
    ("hotel_vs_residence_boundary",
     "A building that holds a hotel and residences or apartments is admitted ONLY as the hotel premises, and a pet "
     "policy binds only to the hotel component. This market's specific exposures: Uptown / Victory Park / Legacy West "
     "/ The Star hotel-and-residence towers, serviced-apartment and 'aparthotel' operators (Sonder, Kasa, Mint House, "
     "Lark, Placemakr, Zeus, Blueground, Barsala, Landing, AKA, stayAPT), corporate-housing portfolios, Arlington "
     "stadium-week rentals and the Airbnb / Vrbo inventory the State's hotel-tax register carries as 531110 / 531311."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort (Marriott Vacation Club, Hilton Grand Vacations, Club Wyndham, "
     "WorldMark, Westgate, Holiday Inn Club Vacations, Bluegreen, Hyatt Vacation Club, Diamond / Hilton Vacation Club, "
     "Shell Vacations, independent ownership resorts) is TIMESHARE and is never admitted to hotel accounting, even "
     "when its brand lists it beside its hotels, even when it sells a nightly rate, and even when a pet-policy page "
     "exists."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared amenities or "
     "shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never published as one. A hotel "
     "and its residences on one campus are distinct premises."),
    ("extended_stay",
     "Extended-stay hotels (Extended Stay America, WoodSpring, HomeTowne Studios, Studio 6, MainStay, TownePlace, "
     "Home2, Residence Inn, Candlewood, Staybridge, InTown, Sonesta Simply Suites, Siegel Select) are hotels and are "
     "admitted on their own pages; an 'apartment hotel' is admitted only as a public hotel operation at an exact "
     "premises, never as a residential building that rents furnished units."),
    ("patient_and_military_lodging",
     "Patient-family housing (Ronald McDonald House, Hope Lodge), charitable family lodging (Fisher House), shelters "
     "and on-base military lodging (NAS Fort Worth JRB) are never public hotels and are never admitted."),
])

#: The operating-status vocabulary every row is classified into (decided per row from the property's OWN current
#: page, never from this module).
OPERATING_STATUS_RULE = OrderedDict([
    ("vocabulary", ["CURRENTLY_OPEN", "REOPENED", "PARTIALLY_OPEN", "TEMPORARILY_CLOSED", "PERMANENTLY_CLOSED",
                    "DEMOLISHED", "REBRANDED", "CONVERTED", "PREOPENING", "UNKNOWN"]),
    ("publishes", "Only a row whose own current first-party page proves an operating public lodging business."),
    ("never_publishes", "TEMPORARILY_CLOSED, PERMANENTLY_CLOSED, DEMOLISHED, CONVERTED, PREOPENING and UNKNOWN. A "
                        "REBRANDED row publishes only under its current operator's name on its current page."),
    ("evidence", "A historic OTA page, an old tourism or competitor listing, a cached brand page, a hotel-tax permit or "
                 "old policy evidence never proves current operation; a permit's out-of-business date is closure "
                 "EVIDENCE for that operator at that premises, never by itself a closure of a hotel whose own page "
                 "still sells rooms."),
])
#: Inherited consumer name (the Fort Myers module's island rule slot).
BEACH_ISLAND_EVALUATION = OrderedDict([
    ("not_applicable", "Dallas-Fort Worth has no beach or island lodging; the slot carries the airport, Love Field, "
                       "Arlington, Plano / Frisco and Alliance rulings instead."),
    ("dfw_airport", DFW_AIRPORT_EVALUATION["airport_land"]),
    ("love_field", LOVE_FIELD_EVALUATION["separation"]),
    ("arlington", ARLINGTON_EVALUATION["protections"]),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("75261", ["DFW Airport (Grapevine / Irving / Euless / Coppell city land)"]),
    ("75234", ["Farmers Branch", "Dallas (Valwood)"]),
    ("75244", ["Farmers Branch", "Dallas", "Addison edge"]),
    ("75254", ["Dallas (Galleria north)", "Addison"]),
    ("75240", ["Dallas (Galleria / LBJ)", "Farmers Branch / Addison edge"]),
    ("75243", ["Dallas (Central at LBJ)", "Richardson"]),
    ("75252", ["Dallas (Far North)", "Richardson"]),
    ("75287", ["Dallas (Far North)", "Carrollton", "Addison"]),
    ("75205", ["University Park", "Highland Park", "Dallas"]),
    ("76108", ["White Settlement", "Fort Worth", "Parker County edge (refused by county)"]),
    ("76028", ["Fort Worth", "Burleson (Johnson County land refused by county)"]),
    ("76262", ["Roanoke", "Trophy Club", "Northlake", "Westlake"]),
    ("76177", ["Fort Worth (Alliance)", "Haslet"]),
    ("76137", ["Fort Worth", "Haltom City", "Watauga"]),
    ("75050", ["Grand Prairie (Dallas County)", "Grand Prairie (Tarrant County)"]),
    ("76063", ["Mansfield (Tarrant)", "Johnson / Ellis County edge (refused by county)"]),
])

FUTURE_MARKETS = OrderedDict([
    ("denton-tx", "Denton, Corinth and the Denton County north -- a university city 38 miles from downtown Dallas."),
    ("waxahachie-ennis-tx", "Waxahachie, Ennis and Midlothian -- Ellis County."),
    ("weatherford-tx", "Weatherford, Aledo and Willow Park -- Parker County."),
    ("decatur-tx", "Decatur and Bridgeport -- Wise County."),
    ("corsicana-tx", "Corsicana -- Navarro County."),
    ("greenville-tx", "Greenville and Commerce -- Hunt County."),
    ("sherman-denison-tx", "Sherman, Denison and Lake Texoma -- Grayson County."),
    ("gainesville-tx", "Gainesville -- Cooke County."),
    ("waco-tx", "Waco -- McLennan County, 90 miles south."),
])

#: Markets that are ALREADY LIVE. Two Texas markets are live; neither shares a 750-762 postal code. Exposures are
#: shared NAMES and chain flags: a bare chain name ("Hampton Inn & Suites") published here would take a live market's
#: identity.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("fort-myers-fl", "Fort Myers / Cape Coral, live as production market #46 (deploy 6ac8d0c021f9d04e6aa82455) -- the "
                      "CURRENT LIVE market at this order's authoring time. No shared state or code."),
    ("austin-tx", "Austin, live -- 190 miles south on I-35; no shared postal code."),
    ("san-antonio-tx", "San Antonio, live -- 270 miles south; no shared postal code."),
])

#: A shared postal code whose OTHER place is refused by municipality name. None: refused county land inside an
#: admitted code is refused by COUNTY (Census boundary or State permit), not by name.
MUNICIPALITY_REFUSALS = [
    ("76262", "justin", "Justin (Denton County north) shares no admitted premises with 76262; a 'Justin' label there "
                        "is refused"),
]
#: Boundary wording on a row's own name or street: a premises an admitted label hides in a refused place.
BOUNDARY_NAME_RX = re.compile(r"\b(denton (ut|unt|university)|texas woman'?s university|lake texoma|"
                              r"glen rose|granbury|mineral wells|weatherford|waxahachie|cleburne|corsicana)\b", re.I)

MUNICIPALITY_SPELLINGS = {
    "dallas,": "dallas", "dallas tx": "dallas", "dallas, tx": "dallas", "fort worth,": "fort worth",
    "ft worth": "fort worth", "ft. worth": "fort worth", "ft worth,": "fort worth", "fort worth tx": "fort worth",
    "fort worth, tx": "fort worth", "dfw": "dfw airport", "dfw airport,": "dfw airport", "d/fw airport": "dfw airport",
    "dallas/fort worth airport": "dfw airport", "dallas fort worth airport": "dfw airport",
    "dfw arpt": "dfw airport", "dfw intl airport": "dfw airport", "irving,": "irving", "irving tx": "irving",
    "las colinas": "irving", "grapevine,": "grapevine", "euless,": "euless", "bedford,": "bedford",
    "hurst,": "hurst", "arlington,": "arlington", "grand prairie,": "grand prairie", "addison,": "addison",
    "richardson,": "richardson", "plano,": "plano", "frisco,": "frisco", "carrollton,": "carrollton",
    "farmers branch,": "farmers branch", "frmrs branch": "farmers branch", "the colony,": "the colony",
    "colony": "the colony", "lewisville,": "lewisville", "allen,": "allen", "mckinney,": "mckinney",
    "mc kinney": "mckinney", "flower mound,": "flower mound", "southlake,": "southlake", "roanoke,": "roanoke",
    "mansfield,": "mansfield", "mesquite,": "mesquite", "garland,": "garland", "de soto": "desoto",
    "desoto,": "desoto", "duncanville,": "duncanville", "cedar hill,": "cedar hill", "lancaster,": "lancaster",
    "n richland hills": "north richland hills", "n. richland hills": "north richland hills",
    "north richland hls": "north richland hills", "nrh": "north richland hills", "haltom": "haltom city",
    "haltom city,": "haltom city", "white settlemnt": "white settlement", "trophy club,": "trophy club",
    "westlake,": "westlake", "northlake,": "northlake", "keller,": "keller", "coppell,": "coppell",
    "university park,": "university park", "highland park,": "highland park", "dalworthington gdns":
    "dalworthington gardens", "balch spgs": "balch springs", "naval air station": "naval air station jrb",
    "nas fort worth jrb": "naval air station jrb", "naval air station fort worth jrb": "naval air station jrb",
    "naval air station jrb,": "naval air station jrb", "ft worth nas jrb": "naval air station jrb",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("75201", "Downtown Dallas / Arts District / Victory Park edge."),
    ("75219", "Oak Lawn / Turtle Creek / Victory Park / American Airlines Center."),
    ("75235", "Love Field / Medical District -- never DFW Airport."),
    ("75261", "DFW Airport -- Grapevine / Irving / Euless / Coppell land, decided by premises."),
    ("75038", "Las Colinas -- Irving, never Dallas."),
    ("76011", "Arlington stadium district."),
    ("75024", "Legacy / Legacy West / Granite Park -- Plano, never Dallas."),
    ("75034", "The Star / Stonebriar -- Frisco, never Dallas."),
    ("75234", "Dallas-preferred, largely Farmers Branch -- decided by premises."),
    ("76102", "Downtown Fort Worth / Sundance Square."),
    ("76164", "Fort Worth Stockyards."),
    ("76177", "Alliance -- Fort Worth or Haslet by premises."),
    ("76201", "Denton -- refused (denton-tx)."),
    ("75087", "Rockwall -- refused."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Dallas-Fort Worth" % name),
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
        raise SystemExit("admitted postal codes outside the Dallas / Fort Worth prefixes: %s" % stray)
    for rz, _m, _w in MUNICIPALITY_REFUSALS:
        if rz not in seen_zip:
            raise SystemExit("municipality refusal on a code no corridor claims: %s" % rz)
    foreign_county = sorted(z for z in seen_zip if POSTAL_PARISH[z][0] not in ADMITTED_COUNTY_NAMES)
    if foreign_county:
        raise SystemExit("admitted postal codes principally outside the four admitted counties: %s" % foreign_county)
    for z, (_c, munis) in POSTAL_PARISH.items():
        for m in munis:
            if m not in MUNICIPALITY_DISPLAY:
                raise SystemExit("postal code %s names municipality %r with no display form" % (z, m))
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
        ("market_name", "Dallas-Fort Worth Metroplex, Texas -- downtown Dallas, Uptown, Love Field, the Park Cities and "
                        "North Dallas; DFW Airport and Las Colinas; Arlington's stadiums; downtown Fort Worth, the "
                        "Stockyards and Alliance; the Mid-Cities; and the Plano / Frisco / Richardson / Addison "
                        "corporate corridors (PetTripFinder discovery scope)"),
        ("state", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("country", "US"),
        ("market_center", {"lat": 32.84, "lng": -97.04}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches north past Denton, Prosper and Celina, east past "
             "Rockwall and Forney, south past Waxahachie and Cleburne and west past Weatherford, so that " + WORK_ORDER
             + " classifies those properties on evidence instead of being blind to them. Admission is decided by the "
             "corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Dallas-Fort Worth is ONE market of Dallas and Tarrant counties and the south tiers of Collin "
         "and Denton, every row keeping its own municipality: 12 CORE corridors, 15 STRONG CORRIDORS and 5 FRINGE "
         "corridors. DENTON, ROCKWALL, WEATHERFORD, DECATUR, WAXAHACHIE, ENNIS, CORSICANA, GREENVILLE, SHERMAN / "
         "DENISON, GAINESVILLE and WACO are refused; Rockwall, Kaufman, Ellis, Johnson, Parker and Wise county "
         "premises are refused whatever their mailing label. Patient, charitable and on-base lodging is never "
         "admitted."),
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
        ("market_name", "Dallas-Fort Worth, Texas"),
        ("market_slug", MARKET_ID),
        ("state_name", "Texas"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("primary_city", "Dallas"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Dallas-Fort Worth, Texas | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across the Dallas-Fort Worth Metroplex -- downtown Dallas, Uptown and Love "
         "Field, DFW Airport, Irving and Las Colinas, Arlington, downtown Fort Worth and the Stockyards, Grapevine and "
         "the Mid-Cities, Plano, Frisco and Richardson -- with real pet fees and policies read from each hotel's own "
         "official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Dallas-Fort Worth"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page, its brand's own property card or the "
         "State's own hotel-tax permit states it, joined to the corridor registry; the property's MUNICIPALITY and "
         "COUNTY are the ones its own premises are in (Census TIGER boundary). A Dallas-Fort Worth Metroplex travel "
         "market -- both downtowns, Love Field and DFW Airport, Las Colinas, Arlington, the Mid-Cities, Alliance and "
         "the north Dallas corporate corridors. Not 'North Texas': Denton, Rockwall, Weatherford, Decatur, Waxahachie, "
         "Ennis, Corsicana, Greenville, Sherman / Denison, Gainesville and Waco are outside. Nothing else admits a "
         "property: not a brand's 'Dallas' or 'Fort Worth' marketing name, not a map pin, not a vacation-rental "
         "listing, not a competitor directory's city label. Patient, charitable and on-base lodging is never "
         "admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Irving, Grapevine, "
         "Arlington, Grand Prairie, Plano, Frisco, Addison, Richardson, Carrollton, Farmers Branch and every other "
         "suburb keep their own municipality and are never written as Dallas or Fort Worth. Dallas-preferred codes "
         "that are partly Farmers Branch, Addison, Richardson or the Park Cities, and Fort Worth-preferred codes that "
         "are partly White Settlement, Haltom City, Forest Hill, Saginaw or Haslet, publish the municipality the "
         "premises are in."),
        ("_census_membership_note",
         "Individual condominium units, private residences, corporate-housing portfolios, serviced-apartment "
         "operators, Airbnb / Vrbo inventory, ordinary apartments, student housing, timeshare and vacation-club "
         "inventory, residential-only towers, member-only club lodging and on-base military / government lodging are "
         "never admitted. A building that holds a hotel and residences is admitted only as the hotel premises. "
         "Extended-stay hotels are hotels."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    counties = ADMITTED_COUNTY_NAMES
    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 + 6 + 7 + 8 + 9 + 10 -- Dallas-Fort Worth travel-market geography, county accounting, "
                  "municipality safety, DFW Airport, Love Field, Arlington, Plano / Frisco, Alliance and the Denton / "
                  "McKinney sprawl rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/dallas-fort-worth-tx.json. This "
         "order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page, its brand's own property card or the State's own "
         "hotel-tax permit states it, joined to the corridor registry. Nothing else admits a property; a premises in "
         "a refused county refuses."),
        ("municipality_rule",
         "Every row with coordinates publishes the incorporated place whose Census TIGER/Line boundary contains its "
         "premises, and the county whose Census boundary contains them; POSTAL_COUNTY is the fallback and cross-check. "
         "A row in a multi-municipality code that cannot be placed is HELD. SUBURBAN HOTELS MISLABELED DALLAS = 0 and "
         "SUBURBAN HOTELS MISLABELED FORT WORTH = 0."),
        ("postal_county", OrderedDict((z, OrderedDict([("county", p), ("municipalities", list(m))]))
                                      for z, (p, m) in POSTAL_PARISH.items())),
        ("classes", OrderedDict((k, "; ".join("%s (%s, %s)" % (c[1], c[7], ", ".join(c[5])) for c in CORRIDORS
                                              if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG_CORRIDOR is registry class CORRIDOR; FUTURE_STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes, by COUNTY (Rockwall, Kaufman, Ellis, "
                          "Johnson, Parker, Wise and the outer counties) and by postal PREFIX for the rest of Texas; "
                          "the future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("dfw_airport_evaluation", DFW_AIRPORT_EVALUATION),
        ("love_field_evaluation", LOVE_FIELD_EVALUATION),
        ("arlington_evaluation", ARLINGTON_EVALUATION),
        ("plano_frisco_evaluation", PLANO_FRISCO_EVALUATION),
        ("alliance_evaluation", ALLIANCE_EVALUATION),
        ("operating_status_rule", OPERATING_STATUS_RULE),
        ("dallas_fort_worth_ruling", FORT_MYERS_RULING),
        ("metro_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("county_refusals", COUNTY_REFUSALS),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("military_lodging_rule", OrderedDict([
            ("rule", "On-base military lodging is MILITARY_RESTRICTED and never admitted: Naval Air Station Fort Worth "
                     "Joint Reserve Base (76127) and its Navy Gateway Inns & Suites."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "Dallas-Fort Worth was selected as a high-value PetTripFinder market for airport, convention, corporate, "
         "stadium and family travel. That lowers NO evidence standard: pet acceptance is never inferred from a "
         "city's reputation. It shapes only the CENSUS: every downtown, airport, suburban, stadium and corporate "
         "lodging cluster is covered by an admitting corridor."),
        ("the_dallas_name_trap",
         "The chains put 'Dallas' on hotels in Irving, Las Colinas, Addison, Farmers Branch, Richardson, Plano, "
         "Frisco, Grand Prairie and Garland, 'Fort Worth' on hotels in Haltom City, Saginaw, Roanoke, Northlake and "
         "Burleson, 'DFW Airport' on hotels in Irving, Grapevine, Euless, Coppell and Fort Worth, and 'Dallas/Fort "
         "Worth' on hotels anywhere between. A property's own postal code, premises, phone and brand property code "
         "decide what and where it is -- and which MUNICIPALITY it is in; none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("DFW International Airport", "dfw-airport (75261), irving-las-colinas, grapevine-coppell, mid-cities."),
            ("Dallas Love Field", "love-field-medical-market-center (75235)."),
            ("Kay Bailey Hutchison Convention Center", "downtown-dallas (75202)."),
            ("American Airlines Center / Victory Park", "uptown-victory-park (75219)."),
            ("AT&T Stadium / Globe Life Field / Six Flags Over Texas", "arlington-entertainment (76011)."),
            ("Fort Worth Stockyards", "stockyards-north-side (76164)."),
            ("Fort Worth Convention Center / Sundance Square", "downtown-fort-worth (76102)."),
            ("Dickies Arena / Will Rogers", "cultural-district-tcu (76107)."),
            ("Gaylord Texan / Grapevine Mills", "grapevine-coppell (76051)."),
            ("Irving Convention Center / Las Colinas", "irving-las-colinas (75039)."),
            ("Legacy West / Toyota North America", "plano (75024)."),
            ("The Star / Ford Center / PGA Frisco", "frisco (75034 / 75033)."),
            ("Texas Motor Speedway (south approach) / AllianceTexas", "alliance-north-fort-worth (76177 / 76262)."),
            ("UT Southwestern / Parkland", "love-field-medical-market-center (75235 / 75390)."),
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
        ("non_municipal_localities", NON_MUNICIPAL_LOCALITIES),
        ("registered_market_postal_codes_checked", len(registered_codes)),
        ("no_live_market_postal_code_admitted", not live_overlap),
        ("third_texas_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("state_code", c["state_code"]), ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, stadium or neighbourhood "
         "keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration order "
         "publishes it."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, bed-and-breakfasts that prove a public lodging operation, public "
         "resorts, qualifying extended-stay hotels and other public lodging establishments: bookable nightly rooms or "
         "suites sold to the public under one establishment name, with an official property page and an on-site "
         "operation. It NEVER admits: individual condominium units; private residences and guest suites; "
         "property-management / corporate-housing / short-term-rental portfolios; serviced-apartment operators; "
         "Airbnb / Vrbo listings; ordinary apartments; student housing; timeshare and vacation-club inventory; "
         "residential-only towers; member-only club lodging; on-base military / government lodging. RV parks and "
         "campgrounds are NON_LODGING."),
        ("shared_campus_rule",
         "Never merged solely by display name, brand, owner, phone, shared address, campus, booking engine, shared "
         "amenities or shared entrance. Exact premises identity (its own street address or its own brand property "
         "code on its own page) governs. A dual-brand building is TWO hotels and is HELD for the split."),
        ("preopening_rule",
         "A preopening hotel ('Opening 2026', 'Coming Soon') never publishes; a closed, converted or demolished hotel "
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
    """The refusal a row's own NAME or STREET carries when it names a refused place an admitted code or label hides.
    Or ""."""
    for text in (name or "", street or ""):
        m = BOUNDARY_NAME_RX.search(text)
        if m:
            return ("refused place named on the row (%r) -- a premises outside the Metroplex boundary, never admitted"
                    % m.group(0))
    return ""


def county_refusal_reason(county):
    """The refusal a premises' own COUNTY carries (Rockwall, Kaufman, Ellis, Johnson, Parker, Wise, outer counties),
    or "". Accepts a county name or a Comptroller county number."""
    c = (county or "").strip()
    if c.isdigit():
        c = COMPTROLLER_COUNTY.get(str(int(c)), c)
    c = " ".join(c.lower().replace("county", "").split())
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
    """The municipality a premises at ``postal`` publishes when its coordinates are NOT known: the stated city when the
    code carries it, else the code's first (principal) municipality. "" for a code outside the admitted partition.
    A row WITH coordinates is placed by ``municipality_for_premises``."""
    entry = POSTAL_PARISH.get((postal or "").strip()[:5])
    if not entry:
        return ""
    stated = normalise_municipality(stated_city)
    if stated in entry[1]:
        return stated
    return entry[1][0]


def municipality_for_premises(postal, stated_city="", lat=None, lng=None):
    """(municipality, county, basis) for a premises. With coordinates: the incorporated place and county whose Census
    boundaries contain the premises (a premises in no incorporated place keeps its stated or postal municipality).
    Without: the postal fallback, flagged so a multi-municipality code can be held."""
    from scripts.pettripfinder import dallas_fort_worth_tx_municipal_boundaries_001 as MB
    entry = POSTAL_PARISH.get((postal or "").strip()[:5])
    if lat is not None and lng is not None:
        try:
            place, klass = MB.place_for_point(float(lat), float(lng))
            county = MB.county_for_point(float(lat), float(lng))
        except (TypeError, ValueError):
            place, klass, county = "", "", ""
        if place:
            return normalise_municipality(place), county, "CENSUS_PLACE_BOUNDARY"
        fallback = municipality_for_postal(postal, stated_city)
        if fallback in NON_MUNICIPAL_LOCALITIES:
            fallback = ""
        return (fallback, county, "UNINCORPORATED_PREMISES_MAILING_MUNICIPALITY" +
                ((" (" + klass + ")") if klass else ""))
    if not entry:
        return "", "", "OUTSIDE_PARTITION"
    m = municipality_for_postal(postal, stated_city)
    basis = "POSTAL_FALLBACK_SINGLE" if len(entry[1]) == 1 else "POSTAL_FALLBACK_MULTI"
    return m, entry[0], basis


def municipality_display(postal, stated_city=""):
    m = municipality_for_postal(postal, stated_city)
    return MUNICIPALITY_DISPLAY.get(m, (stated_city or "").strip())


def municipality_conflict(postal, stated_city):
    """The reason a row's own STATED city is not a municipality its own postal code carries, or "". The guard behind
    SUBURBAN HOTELS MISLABELED DALLAS / FORT WORTH = 0."""
    entry = POSTAL_PARISH.get((postal or "").strip()[:5])
    stated = normalise_municipality(stated_city)
    if not entry or not stated:
        return ""
    if stated in entry[1]:
        return ""
    return ("the row states the city %r beside postal code %s, which is %s County (%s); the premises publish the "
            "municipality their own location is in" % (stated_city, (postal or "")[:5], entry[0],
                                                         " / ".join(entry[1])))


def state_conflict(postal, stated_state):
    """The reason a row's own STATED state contradicts the state its own postal code is in, or ""."""
    s = (stated_state or "").strip().upper()
    s = {"TEXAS": "TX", "OKLAHOMA": "OK", "LOUISIANA": "LA", "ARKANSAS": "AR"}.get(s, s)
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
        return "OUTSIDE", None, "North Texas postal code %r is claimed by no corridor" % z
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
