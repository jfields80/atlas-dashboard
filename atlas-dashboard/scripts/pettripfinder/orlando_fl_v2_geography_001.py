"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phases 3, 4 and 7: the Greater Orlando travel market.

Built from zero on the current verified-live lineage (Savannah LIVE, 1fa43a48). Orlando V1
(worker/ptf-orlando-fl-market-001) is a historical comparison only; nothing here is read from it.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Greater Orlando / Central Florida traveller lodging market, stated as an explicit
CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE markets named inside OUTSIDE)
before a single hotel is admitted, so no property is admitted or refused after the fact to make a
number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or the Florida
DBPR public-lodging licence, which is the state's own record of the licensed premises) states it,
joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted
lodging ZIP is claimed by exactly one corridor, so a property's corridor is a lookup and never a
judgement. A brand's marketing name ("Orlando Disney Area", "Orlando Maingate", "Near Universal",
"Orlando Airport") never admits and never places a property: a "Maingate" hotel whose own address
states Kissimmee 34746 is a Kissimmee US-192 hotel.

WHY THE THEME-PARK SUBMARKETS ARE OVERLAYS, NOT SEPARATE PAGES
--------------------------------------------------------------
Universal Orlando, the Orange County Convention Center, the northern International Drive strip and
Sand Lake / Dr. Phillips share 32819. SeaWorld, southern International Drive and Vineland share 32821.
Disney Springs' Hotel Plaza Boulevard hotels share 32830 with Walt Disney World's own resorts.
Celebration shares 34747 with the West US-192 resorts. A postal partition cannot place them in two
corridors without splitting a postal code other hotels depend on, so each is ONE corridor, and the
named submarket is reported as a STREET-AND-PIN OVERLAY on every census row (the property's own
street first -- Universal Boulevard, Hotel Plaza Boulevard, Sea Harbor Drive, Celebration Place --
then a pin within the anchor's radius). The overlay decides nothing about membership or corridor. The
contract's explicit_hotel_ids mechanism remains available to a later order that wants a Universal or
Disney Springs page and can meet the publication threshold with named properties.

THE SPLIT TEST (PHASE 4) IS RECORDED IN THE REPORT
--------------------------------------------------
Each of the order's twelve submarkets (A-L) is classified with the reason, and the future-standalone
optionality that each preserves is named. Nothing is forced into one undifferentiated market: Space
Coast, Daytona Beach, Tampa, Lakeland / Winter Haven, Ocala and The Villages / Lake County north are
OUTSIDE and named, with their postal codes, so a future market order starts from recorded identities.

VACATION RENTALS, TIMESHARES AND RESORT RESIDENCES
--------------------------------------------------
The rule is stated here once and applied by the census: Florida DBPR licenses every condominium unit
(CNDO) and vacation dwelling (DWEL) as public lodging, and Greater Orlando carries tens of thousands of
them (34747 alone: 5,158 CNDO + 7,156 DWEL licences). None is a hotel identity. A mixed hotel /
timeshare / condo campus is admitted only as the exact hotel premises its own operator sells as a hotel.

Nothing here fetches, spends or deploys. The market document goes to the PROPOSED path (shadow until
registered); the registry's markets/<id>.json is never written.

Outputs:
  scripts/pettripfinder/discovery/config/orlando_fl.json
  launch_packages/pettripfinder/markets/proposed/orlando-fl.json
  launch_packages/pettripfinder/markets/reports/orlando_fl_v2_geography_001.json
  launch_packages/pettripfinder/markets/reports/orlando_fl_v2_corridor_registry_001.json
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

WORK_ORDER = "PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "orlando-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "orlando_fl.json")
#: REGISTERED by PTF-ORLANDO-FL-V2-REGISTRATION-AND-FOUNDER-PACKET-003 against the Savannah-live parent. The source-ready
#: order wrote markets/proposed/orlando-fl.json (kept as history).
SHARD_OUT = os.path.join(PKG, "markets", "orlando-fl.json")
REPORT_OUT = os.path.join(REPORTS, "orlando_fl_v2_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "orlando_fl_v2_corridor_registry_001.json")
AS_OF = "2026-09-15"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown-orlando", "Downtown Orlando / Lake Eola / SoDo", "Downtown Orlando", "CORE", "orlando",
     ["32801", "32803", "32804", "32805", "32806"],
     "Downtown Orlando and the neighbourhoods around it: Lake Eola, Church Street, the Kia Center and Camping "
     "World Stadium, Dr. Phillips Center, College Park, Loch Haven / Mills 50 and SoDo with the Orlando Health "
     "and AdventHealth downtown campuses."),
    ("mco-airport", "Orlando International Airport (MCO) / Lake Nona", "MCO Airport", "CORE", "orlando",
     ["32812", "32822", "32824", "32827", "32832"],
     "Orlando International Airport (MCO) and its hotel districts: the in-terminal hotel, the Semoran and "
     "Hoffner / Conway strips north of the airport, the Landstar / Boggy Creek area to the west and Lake Nona "
     "Medical City to the south."),
    ("international-drive-universal", "International Drive / Convention Center / Universal / Sand Lake",
     "I-Drive, Convention Center & Universal", "CORE", "orlando",
     ["32819"],
     "The northern International Drive resort strip (ICON Park, Pointe Orlando), the Orange County "
     "Convention Center, Universal Orlando Resort and its on-site hotels, and Sand Lake Road / Dr. Phillips "
     "Restaurant Row. One postal code, so Universal, the Convention Center and I-Drive are overlays."),
    ("seaworld-idrive-south", "SeaWorld / International Drive South / Vineland", "SeaWorld & I-Drive South",
     "CORE", "orlando",
     ["32821"],
     "SeaWorld Orlando, Aquatica and Discovery Cove, southern International Drive, Lake Bryan, Vineland Road "
     "and the Orlando Vineland Premium Outlets."),
    ("lake-buena-vista", "Lake Buena Vista / Palm Parkway / SR-535", "Lake Buena Vista", "CORE", "orlando",
     ["32836"],
     "The Lake Buena Vista gateway outside Walt Disney World's gates: Palm Parkway, Apopka-Vineland Road "
     "(SR-535), Lake Buena Vista Drive and Bay Hill."),
    ("walt-disney-world", "Walt Disney World Resort / Disney Springs", "Walt Disney World & Disney Springs",
     "CORE", "lake buena vista",
     ["32830"],
     "Walt Disney World Resort inside Reedy Creek / Bay Lake: Disney's own resort hotels, the Walt Disney "
     "World Swan and Dolphin, Four Seasons Orlando and the Disney Springs Resort Area hotels on Hotel Plaza "
     "Boulevard. Military-only Shades of Green is non-public lodging."),
    ("flamingo-crossings-winter-garden", "Flamingo Crossings / Winter Garden / Windermere / Ocoee",
     "Flamingo Crossings & West Orange", "CORRIDOR", "winter garden",
     ["34787", "34786", "34761"],
     "Walt Disney World's western gateway at Flamingo Crossings Town Center (SR-429 / Western Way), with "
     "Winter Garden, Horizon West, Windermere and Ocoee along SR-429 and the Turnpike."),
    ("kissimmee-us192-maingate", "Kissimmee US-192 / Maingate / Old Town", "Kissimmee US-192 Maingate",
     "CORE", "kissimmee",
     ["34746"],
     "West Irlo Bronson Memorial Highway (US-192) east of I-4 -- Maingate, Old Town, Fun Spot and the "
     "Vineland Road / Poinciana Boulevard hotel strip -- the densest Disney-gateway motel and resort corridor."),
    ("celebration-west-192", "Celebration / West US-192 / Reunion", "Celebration & West 192", "CORE",
     "celebration",
     ["34747"],
     "The town of Celebration and West US-192 beyond I-4: Formosa Gardens, Reunion, Margaritaville and the "
     "large resort campuses on World Drive and Sherberth Road."),
    ("kissimmee-east", "Kissimmee / East US-192 / Buenaventura Lakes", "Kissimmee East", "CORRIDOR",
     "kissimmee",
     ["34741", "34743", "34744"],
     "Downtown Kissimmee, the Lakefront Park, East Irlo Bronson Memorial Highway (US-192) and John Young "
     "Parkway to the Osceola Heritage Park and Buenaventura Lakes."),
    ("four-corners-davenport", "Four Corners / ChampionsGate / Davenport", "Four Corners & Davenport",
     "CORRIDOR", "davenport",
     ["33896", "33897", "33837"],
     "Polk County's I-4 / US-27 interchange where Orange, Osceola, Lake and Polk meet: ChampionsGate, Four "
     "Corners, Posner Park and Davenport -- Disney-gateway lodging on the Orlando side of I-4."),
    ("south-orlando", "South Orlando / Florida Mall / Hunter's Creek / Orange Blossom Trail",
     "South Orlando & Florida Mall", "CORRIDOR", "orlando",
     ["32809", "32811", "32835", "32837", "32839"],
     "The Florida Mall and Sand Lake Road at Orange Blossom Trail, Kirkman / MetroWest, Americana and Oak "
     "Ridge, and Hunter's Creek / Southchase on John Young Parkway and the Turnpike."),
    ("east-orlando-ucf", "East Orlando / UCF / Research Park / Oviedo", "East Orlando & UCF", "CORRIDOR",
     "orlando",
     ["32807", "32817", "32825", "32826", "32828", "32829", "32765", "32708"],
     "East Colonial Drive and University Boulevard: the University of Central Florida, Central Florida "
     "Research Park, Waterford Lakes, Avalon Park, Oviedo and Winter Springs."),
    ("north-orlando-lee-road", "North Orlando / Lee Road / I-4 North", "North Orlando", "CORRIDOR", "orlando",
     ["32808", "32810", "32818"],
     "The I-4 north interchanges at Lee Road and Maitland Boulevard and West Colonial Drive through Pine "
     "Hills."),
    ("winter-park-maitland", "Winter Park / Maitland / Baldwin Park", "Winter Park & Maitland", "CORRIDOR",
     "winter park",
     ["32789", "32792", "32751", "32814"],
     "Winter Park's Park Avenue and Rollins College, Maitland Center and Baldwin Park."),
    ("altamonte-springs-longwood", "Altamonte Springs / Longwood / Casselberry", "Altamonte Springs",
     "CORRIDOR", "altamonte springs",
     ["32701", "32714", "32750", "32779", "32707", "32730"],
     "Altamonte Springs at I-4 / SR-436 (Cranes Roost, Altamonte Mall), Longwood, Casselberry and Fern Park."),
    ("lake-mary-sanford", "Lake Mary / Heathrow / Sanford / SFB Airport", "Lake Mary & Sanford", "CORRIDOR",
     "lake mary",
     ["32746", "32771", "32773"],
     "The Lake Mary / Heathrow office corridor at I-4 and Rinehart Road, and Sanford with Orlando Sanford "
     "International Airport (SFB) and the historic downtown riverfront."),
    ("clermont", "Clermont / US-27 / Minneola", "Clermont", "FRINGE", "clermont",
     ["34711", "34714", "34715"],
     "Clermont and Minneola on SR-50 and US-27 in south Lake County, including the US-27 resort communities "
     "north of Four Corners."),
    ("st-cloud", "St. Cloud / East Osceola", "St. Cloud", "FRINGE", "st cloud",
     ["34769", "34771", "34772"],
     "St. Cloud on East US-192, ten miles east of downtown Kissimmee."),
    ("apopka", "Apopka / Northwest Orange", "Apopka", "FRINGE", "apopka",
     ["32703", "32712"],
     "Apopka on US-441 / SR-414 in northwest Orange County."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the property's OWN stated
#: municipality. (postal, municipality, why)
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "orlando fl": "orlando", "saint cloud": "st cloud", "st. cloud": "st cloud", "lake buena vista fl": "lake buena vista",
    "bay lake": "lake buena vista", "altamonte": "altamonte springs", "champions gate": "championsgate",
    "kissimmee fl": "kissimmee", "celebration fl": "celebration", "mt dora": "mount dora", "mt. dora": "mount dora",
}

#: FUTURE standalone markets this order preserves by name.
FUTURE_MARKETS = OrderedDict([
    ("space-coast-fl", "Space Coast: Titusville / Kennedy Space Center / Cocoa / Cocoa Beach / Port Canaveral / "
                       "Melbourne -- its own cruise-port, beach and launch-viewing lodging market 45-70 miles east"),
    ("daytona-beach-fl", "Daytona Beach / New Smyrna Beach / Ormond Beach -- an oceanfront resort and motorsport "
                         "market 55 miles north-east"),
    ("tampa-fl", "Tampa Bay -- its own major market (a separate PetTripFinder market order exists)"),
    ("lakeland-winter-haven-fl", "Lakeland / Winter Haven / Legoland Florida -- Polk County's I-4 west and Legoland "
                                 "market, whose lodging sells to Legoland and Tampa-Orlando midpoint stays"),
    ("ocala-fl", "Ocala / Marion County -- its own horse-country market 80 miles north-west"),
    ("the-villages-lake-county-fl", "The Villages / Leesburg / Mount Dora / Tavares / Eustis -- north Lake and Sumter "
                                    "County retirement and small-town lodging with weak Orlando lodging intent"),
])

#: Municipalities OUTSIDE the admitted market, each with the reason. A FUTURE_STANDALONE row names its market.
OUTSIDE = [
    ("Poinciana", "FL", ["34758", "34759"],
     "Poinciana: a residential and vacation-home community south of Kissimmee with almost no hotel stock and weak "
     "hotel intent; careful evaluation, refused (its vacation homes are refused by the rental rule anyway)."),
    ("Haines City / Lake Hamilton / Dundee", "FL", ["33844", "33845", "33851", "33838"],
     "Haines City and the US-27 towns south of Davenport: Polk County ridge lodging sold as 'near Orlando' marketing "
     "only; careful evaluation, refused."),
    ("Mount Dora / Tavares / Eustis / Umatilla / Howey-in-the-Hills", "FL",
     ["32757", "32778", "32726", "32727", "32736", "32784", "34737"],
     "north Lake County's small towns, 30-40 miles from Orlando's lodging cores; FUTURE_STANDALONE "
     "the-villages-lake-county-fl; refused."),
    ("Leesburg / The Villages / Wildwood / Fruitland Park", "FL",
     ["34748", "34749", "34788", "34789", "32159", "32162", "32163", "34762", "34785", "34731"],
     "The Villages and Leesburg; FUTURE_STANDALONE the-villages-lake-county-fl; refused by the order's weak-intent rule."),
    ("Groveland / Mascotte / Montverde", "FL", ["34736", "34753", "34756"],
     "west Lake County beyond Clermont with no Orlando lodging core; refused."),
    ("DeLand / Orange City / DeBary / Deltona / Lake Helen / Cassadaga", "FL",
     ["32720", "32721", "32723", "32724", "32763", "32713", "32725", "32738", "32744", "32706"],
     "west Volusia County; DeLand is named by the order for careful evaluation: Stetson University and "
     "DeLand-bound stays, 35+ miles north of downtown Orlando; refused."),
    ("Daytona Beach / Ormond Beach / New Smyrna Beach / Port Orange", "FL",
     ["32114", "32117", "32118", "32119", "32124", "32127", "32129", "32168", "32169", "32174", "32176"],
     "FUTURE_STANDALONE daytona-beach-fl; refused by name (order)."),
    ("Titusville / Mims / Scottsmoor", "FL", ["32780", "32796", "32754", "32775"],
     "the northern Space Coast; FUTURE_STANDALONE space-coast-fl; refused by name (order)."),
    ("Cocoa / Cocoa Beach / Cape Canaveral / Merritt Island / Rockledge", "FL",
     ["32922", "32926", "32927", "32931", "32920", "32952", "32953", "32955"],
     "FUTURE_STANDALONE space-coast-fl; refused by name (order)."),
    ("Melbourne / Palm Bay / Viera", "FL", ["32901", "32903", "32904", "32934", "32935", "32940", "32905", "32907"],
     "FUTURE_STANDALONE space-coast-fl; refused."),
    ("Lakeland / Auburndale / Polk City", "FL",
     ["33801", "33803", "33805", "33809", "33810", "33811", "33812", "33813", "33815", "33823", "33868"],
     "FUTURE_STANDALONE lakeland-winter-haven-fl; refused by name (order)."),
    ("Winter Haven / Lake Alfred / Lake Wales / Bartow", "FL",
     ["33880", "33881", "33884", "33850", "33853", "33859", "33898", "33830"],
     "FUTURE_STANDALONE lakeland-winter-haven-fl (Legoland Florida); refused."),
    ("Tampa Bay", "FL", ["33601", "33602", "33605", "33606", "33607", "33609", "33610", "33612", "33614", "33619",
                         "33634", "33635", "33637", "33647", "33584", "33566", "33567", "33563"],
     "FUTURE / separate market tampa-fl; refused by name (order)."),
    ("Ocala", "FL", ["34470", "34471", "34472", "34474", "34475", "34476", "34480", "34482"],
     "FUTURE_STANDALONE ocala-fl; refused by name (order)."),
    ("Kenansville / Yeehaw Junction / Holopaw", "FL", ["34739", "34972"],
     "the Turnpike's rural south Osceola service plazas and motels, 30+ miles from Kissimmee; refused."),
    ("Sebring / Avon Park / Lake Placid", "FL", ["33870", "33872", "33875", "33825", "33852"],
     "Highlands County; refused."),
    ("Sanford north shore / Lake Monroe / Geneva / Chuluota", "FL", ["32732", "32766", "32747"],
     "rural east Seminole with no lodging core; refused."),
]

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government).
NONPUBLIC_NAMES = {
    "shades of green": "Shades of Green on Walt Disney World Resort is an Armed Forces Recreation Center open only "
                       "to eligible military patrons and their guests; non-public lodging, refused.",
}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-orlando", "Orlando", "Downtown Orlando", 28.5410, -81.3790, 4000, True),
    ("mco-airport", "Orlando", "MCO Airport / Lake Nona", 28.4200, -81.2900, 9000, True),
    ("idrive-universal", "Orlando", "International Drive / Universal / OCCC", 28.4550, -81.4700, 5000, True),
    ("seaworld", "Orlando", "SeaWorld / I-Drive South", 28.3950, -81.4750, 4500, True),
    ("lake-buena-vista", "Orlando", "Lake Buena Vista / Palm Parkway", 28.3950, -81.5100, 4000, True),
    ("walt-disney-world", "Lake Buena Vista", "Walt Disney World Resort", 28.3800, -81.5600, 8000, True),
    ("flamingo-crossings", "Winter Garden", "Flamingo Crossings / Winter Garden", 28.4500, -81.5900, 12000, True),
    ("kissimmee-maingate", "Kissimmee", "US-192 Maingate / Old Town", 28.3350, -81.5000, 6000, True),
    ("celebration", "Celebration", "Celebration / West 192 / Reunion", 28.3000, -81.5700, 8000, True),
    ("kissimmee-east", "Kissimmee", "Downtown Kissimmee / East 192", 28.3000, -81.3900, 9000, True),
    ("four-corners", "Davenport", "Four Corners / ChampionsGate / Davenport", 28.2400, -81.6300, 12000, True),
    ("south-orlando", "Orlando", "Florida Mall / Hunter's Creek", 28.4300, -81.4000, 9000, True),
    ("east-orlando", "Orlando", "UCF / Research Park / Oviedo", 28.5800, -81.2200, 11000, True),
    ("north-orlando", "Orlando", "Lee Road / Pine Hills", 28.6000, -81.4200, 6000, True),
    ("winter-park", "Winter Park", "Winter Park / Maitland", 28.6100, -81.3600, 5000, True),
    ("altamonte", "Altamonte Springs", "Altamonte Springs / Longwood", 28.6700, -81.3700, 7000, True),
    ("lake-mary-sanford", "Lake Mary", "Lake Mary / Sanford", 28.7700, -81.3200, 10000, True),
    ("clermont", "Clermont", "Clermont / US-27", 28.5000, -81.7300, 12000, True),
    ("st-cloud", "St. Cloud", "St. Cloud", 28.2500, -81.2800, 7000, True),
    ("apopka", "Apopka", "Apopka", 28.6800, -81.5100, 7000, True),
    ("obs-poinciana", "Poinciana", "Poinciana -- OBSERVATION ONLY", 28.1400, -81.4600, 9000, False),
    ("obs-haines-city", "Haines City", "Haines City -- OBSERVATION ONLY", 28.1100, -81.6200, 8000, False),
    ("obs-mount-dora", "Mount Dora", "Mount Dora / Tavares / Eustis -- OBSERVATION ONLY", 28.8100, -81.6800, 12000, False),
    ("obs-deland", "DeLand", "DeLand / Orange City -- OBSERVATION ONLY", 28.9500, -81.2800, 12000, False),
]

BOUNDS = {"min_lat": 28.00, "max_lat": 29.08, "min_lng": -81.95, "max_lng": -81.00}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a
#: radius in km. A row reports under the NEAREST anchor whose radius it falls inside.
COVERAGE_AREAS = [
    ("Downtown Orlando", 28.5410, -81.3790, 2.2),
    ("MCO Airport", 28.4312, -81.3081, 4.5),
    ("Lake Nona", 28.3700, -81.2500, 4.0),
    ("Universal Orlando", 28.4740, -81.4670, 1.6),
    ("Convention Center", 28.4250, -81.4700, 1.3),
    ("International Drive", 28.4436, -81.4690, 2.2),
    ("Sand Lake / Dr. Phillips", 28.4500, -81.4930, 2.0),
    ("SeaWorld", 28.4115, -81.4617, 1.8),
    ("I-Drive South / Vineland", 28.3880, -81.4880, 2.2),
    ("Lake Buena Vista", 28.3900, -81.5080, 2.4),
    ("Disney Springs", 28.3720, -81.5160, 1.2),
    ("Walt Disney World", 28.3850, -81.5640, 6.0),
    ("Flamingo Crossings", 28.3790, -81.6150, 2.0),
    ("Kissimmee US-192 Maingate", 28.3330, -81.5050, 4.5),
    ("Celebration", 28.3190, -81.5440, 2.8),
    ("Reunion / West 192", 28.2700, -81.5900, 4.0),
    ("ChampionsGate", 28.2600, -81.6250, 2.5),
    ("Four Corners", 28.3050, -81.6450, 3.5),
    ("Davenport", 28.1900, -81.6300, 5.0),
    ("Downtown Kissimmee / East 192", 28.2950, -81.4050, 6.0),
    ("Florida Mall", 28.4460, -81.3960, 3.0),
    ("Hunter's Creek", 28.3600, -81.4200, 3.5),
    ("UCF / Research Park", 28.6000, -81.2000, 5.0),
    ("Winter Park", 28.6000, -81.3500, 3.0),
    ("Maitland", 28.6300, -81.3700, 3.0),
    ("Altamonte Springs", 28.6650, -81.3950, 4.0),
    ("Lake Mary", 28.7550, -81.3500, 4.0),
    ("Sanford", 28.8000, -81.2750, 5.0),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Universal Orlando", re.compile(r"\buniversal b(lv)?d|\bhollywood way\b|\badventure way\b|\bkirkman\b", re.I)),
    ("Convention Center", re.compile(r"\b(9[0-9]{3}|8[0-9]{3}|10[0-9]{3}) international d|\bconvention way\b|\bdestination parkway\b|\bwestwood b", re.I)),
    ("International Drive", re.compile(r"\binternational d(r|rive)\b|\bi-?drive\b", re.I)),
    ("SeaWorld", re.compile(r"\bsea harbor\b|\bsea ?world\b|\bcentral florida p(ar)?kwy\b", re.I)),
    ("Disney Springs", re.compile(r"\bhotel plaza b", re.I)),
    ("Lake Buena Vista", re.compile(r"\bpalm p(ar)?kwy\b|\blake buena vista d|\bapopka[- ]vineland\b|\bcrossroads\b", re.I)),
    ("Kissimmee US-192 Maingate", re.compile(r"\b(w(est)?\.? )?irlo bronson\b|\bus[- ]?192\b|\bhwy 192\b|\bhighway 192\b|\bold vineland\b", re.I)),
    ("Celebration", re.compile(r"\bcelebration (pl|place|ave|avenue|b)|\bfront street\b", re.I)),
    ("Flamingo Crossings", re.compile(r"\bflamingo crossings\b|\bwestern way\b|\bcommon (way|ground)\b", re.I)),
    ("Sand Lake / Dr. Phillips", re.compile(r"\bsand lake\b|\bdr\.? phillips\b|\bvineland (rd|road)\b", re.I)),
]


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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Orlando" % name),
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
        ("market_name", "Greater Orlando / Central Florida theme-park, convention and airport lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", "FL"),
        ("states", ["FL"]),
        ("country", "US"),
        ("market_center", {"lat": 28.45, "lng": -81.45}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- north over "
             "Mount Dora and DeLand, south over Poinciana and Haines City -- so that " + WORK_ORDER + " classifies "
             "those properties on evidence instead of being blind to them. Admission is decided by the corridor "
             "registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A multi-core theme-park, convention and airport market: eight CORE corridors, nine CORRIDOR "
         "and three FRINGE. Space Coast, Daytona Beach, Tampa, Lakeland / Winter Haven, Ocala and The Villages / north "
         "Lake County are OUTSIDE and preserved as future standalone markets."),
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
        ("market_name", "Orlando, Florida"),
        ("market_slug", MARKET_ID),
        ("state_name", "Florida"),
        ("state_code", "FL"),
        ("primary_state_code", "FL"),
        ("states", ["FL"]),
        ("primary_city", "Orlando"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Orlando, Florida | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater Orlando -- Downtown, MCO airport, International Drive and the "
         "Convention Center, Universal, SeaWorld, Lake Buena Vista and Walt Disney World, Kissimmee and Celebration, "
         "Winter Park and Lake Mary -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Orlando"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its Florida DBPR public-lodging "
         "licence states it, joined to the corridor registry. A multi-core theme-park, convention and airport travel "
         "market -- not Orlando's city limits and not all of Central Florida. Nothing else admits a property: not a "
         "brand's 'Orlando', 'Disney Area' or 'Maingate' marketing name, not a map pin, not a vacation-rental listing, "
         "not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Universal, the Convention "
         "Center and International Drive share 32819; SeaWorld and I-Drive South share 32821; Disney Springs shares "
         "32830 with Walt Disney World; Celebration shares 34747 with West US-192. Each shared code is one corridor and "
         "its named submarkets are reported as overlays."),
        ("_census_membership_note",
         "Individual condominium units (DBPR CNDO), vacation dwellings (DWEL), vacation homes, whole-home rental "
         "communities, property-management portfolios, Airbnb / Vrbo inventory, ordinary apartments, individual "
         "timeshare units, private resort residences and military-only lodging are never admitted. A mixed hotel / "
         "timeshare / condo campus is admitted only as the exact hotel premises its operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "3 + 4 + 7 -- Greater Orlando travel-market geography, submarket split test and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/orlando-fl.json; the registry's "
         "markets/<id>.json is never written by this order."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its Florida DBPR public-lodging licence states "
         "it, joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes; future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("submarket_split_test", OrderedDict([
            ("A. Downtown / business Orlando",
             "CORE corridor downtown-orlando (32801-32806). Distinct business, arena and medical demand; enough "
             "licensed hotels to stand as its own corridor page. Not a standalone market: its visitors are Orlando visitors."),
            ("B. MCO airport",
             "CORE corridor mco-airport (32812, 32822, 32824, 32827, 32832). Airport and Lake Nona demand, its own corridor."),
            ("C. International Drive / Convention Center",
             "CORE corridor international-drive-universal (32819) plus seaworld-idrive-south (32821). The Convention "
             "Center and northern I-Drive are an overlay inside 32819; they cannot be a separate page under a postal "
             "partition without splitting Universal and Sand Lake from them."),
            ("D. Universal",
             "OVERLAY inside CORE 32819. Universal's on-site hotels and Universal Boulevard share 32819 with I-Drive and "
             "Sand Lake. A Universal page is possible later through explicit_hotel_ids only if its named properties "
             "meet the publication threshold on their own."),
            ("E. SeaWorld",
             "CORE corridor seaworld-idrive-south (32821): SeaWorld, southern I-Drive and Vineland share one code, so "
             "SeaWorld is the corridor's anchor and I-Drive South an overlay."),
            ("F. Lake Buena Vista",
             "CORE corridor lake-buena-vista (32836) for the gateway outside Disney's gates; the Hotel Plaza Boulevard "
             "'Disney Springs Resort Area' hotels are 32830 and sit with Walt Disney World."),
            ("G. Disney gateway",
             "CORE corridor walt-disney-world (32830) for the resort itself; the gateway is spread across 32836 (LBV), "
             "34746 (Maingate), 34747 (Celebration / West 192), 34787 (Flamingo Crossings) and 33896/33897 (Four "
             "Corners) -- each its own corridor, so 'Disney area' marketing never merges them. Disney/Kissimmee resort "
             "inventory is the market's largest block and a candidate for a FUTURE split into its own market; that "
             "optionality is preserved because each gateway corridor is separable by postal code."),
            ("H. Kissimmee / US-192",
             "CORE corridor kissimmee-us192-maingate (34746) for West 192 / Maingate / Old Town; CORRIDOR "
             "kissimmee-east (34741, 34743, 34744) for downtown Kissimmee and East 192."),
            ("I. Celebration",
             "CORE corridor celebration-west-192 (34747). Celebration shares 34747 with the West 192 resort campuses, "
             "so it is the corridor's anchor with West 192 / Reunion as overlays."),
            ("J. Four Corners / Davenport / ChampionsGate",
             "CORRIDOR four-corners-davenport (33896, 33897, 33837): Polk County lodging whose demand is Disney-gateway "
             "demand across I-4. Haines City beyond it is OUTSIDE."),
            ("K. Winter Park / Maitland",
             "CORRIDOR winter-park-maitland (32789, 32792, 32751, 32814): a distinct upscale suburban corridor, too small "
             "for a standalone market."),
            ("L. Lake Mary / Sanford",
             "CORRIDOR lake-mary-sanford (32746, 32771, 32773): Heathrow office demand and Sanford airport (SFB) demand; "
             "Seminole County, Orlando-bound. Not a standalone market."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Winter Park", "ADMITTED (CORRIDOR, winter-park-maitland)."),
            ("Maitland", "ADMITTED (CORRIDOR, winter-park-maitland, 32751)."),
            ("Altamonte Springs", "ADMITTED (CORRIDOR, altamonte-springs-longwood)."),
            ("Lake Mary", "ADMITTED (CORRIDOR, lake-mary-sanford, 32746)."),
            ("Sanford", "ADMITTED (CORRIDOR, lake-mary-sanford, 32771 / 32773)."),
            ("Ocoee", "ADMITTED (CORRIDOR, flamingo-crossings-winter-garden, 34761)."),
            ("Winter Garden", "ADMITTED (CORRIDOR, flamingo-crossings-winter-garden, 34787) -- Flamingo Crossings is Disney's western gateway."),
            ("Clermont", "ADMITTED (FRINGE, clermont)."),
            ("Four Corners", "ADMITTED (CORRIDOR, four-corners-davenport)."),
            ("Davenport", "ADMITTED (CORRIDOR, four-corners-davenport, 33837 / 33897)."),
            ("ChampionsGate", "ADMITTED (CORRIDOR, four-corners-davenport, 33896)."),
            ("Reunion", "ADMITTED (CORE, celebration-west-192, 34747) as an overlay."),
            ("St. Cloud", "ADMITTED (FRINGE, st-cloud)."),
            ("Apopka", "ADMITTED (FRINGE, apopka) -- careful evaluation: US-441 / SR-414 lodging with Orlando-bound demand."),
            ("Poinciana", "OUTSIDE -- careful evaluation: residential / vacation-home community with no hotel core."),
            ("Haines City", "OUTSIDE -- careful evaluation: 'near Orlando' marketing only."),
            ("Mount Dora", "OUTSIDE -- careful evaluation: north Lake County small-town lodging (future the-villages-lake-county-fl)."),
            ("DeLand", "OUTSIDE -- careful evaluation: west Volusia / Stetson; 35+ miles north."),
            ("Tampa", "OUTSIDE by name (order)."),
            ("Daytona Beach", "OUTSIDE by name (order) -- future daytona-beach-fl."),
            ("Cocoa Beach / Space Coast", "OUTSIDE by name (order) -- future space-coast-fl."),
            ("Lakeland", "OUTSIDE by name (order) -- future lakeland-winter-haven-fl."),
            ("Ocala", "OUTSIDE by name (order) -- future ocala-fl."),
        ])),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO; every corridor is "
         "show_in_navigation / show_in_sitemap false until a registration order publishes it. Universal, the "
         "Convention Center, International Drive, Disney Springs, Reunion and ChampionsGate cannot be separate pages "
         "under a postal-code partition; they are reported as overlays."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, public resorts, qualifying resort towers, qualifying extended-stay "
         "hotels and other public lodging establishments: bookable nightly rooms or suites sold to the public under one "
         "establishment name, with an official property page and an on-site hotel operation. It NEVER admits: "
         "individual condominium units (DBPR rank CNDO) or vacation dwellings (DBPR rank DWEL); individual vacation homes "
         "or villas; whole-home rental communities and property-management portfolios; Airbnb / Vrbo listings; ordinary "
         "apartments (DBPR NAPT); individual timeshare units, vacation-ownership inventory sold to owners, and private "
         "resort residences; and privately managed units inside resort campuses. A mixed hotel / timeshare / condo campus "
         "is admitted ONLY as the exact hotel premises its operator sells to the public as a hotel, proved on the "
         "operator's own page and the licence's exact premises. Campgrounds, RV parks and dormitory hostels are NON_LODGING."),
        ("theme_park_campus_rule",
         "Never merged solely by brand, resort family, phone, campus, shared entrance, shared amenities, shared booking "
         "engine or display name. Exact premises identity (its own street address or its own brand property code on its "
         "own page) governs. Disney's resorts are separate hotels; Universal's Loews-operated hotels are separate hotels; "
         "a Marriott or Hilton vacation-club campus beside a hotel is not the hotel."),
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
    return {
        "downtown-orlando": "Downtown Orlando", "mco-airport": "MCO Airport",
        "international-drive-universal": "International Drive", "seaworld-idrive-south": "SeaWorld",
        "lake-buena-vista": "Lake Buena Vista", "walt-disney-world": "Walt Disney World",
        "flamingo-crossings-winter-garden": "Flamingo Crossings", "kissimmee-us192-maingate": "Kissimmee US-192 Maingate",
        "celebration-west-192": "Celebration", "kissimmee-east": "Downtown Kissimmee / East 192",
        "four-corners-davenport": "Four Corners", "south-orlando": "Florida Mall", "east-orlando-ucf": "UCF / Research Park",
        "north-orlando-lee-road": "North Orlando", "winter-park-maitland": "Winter Park",
        "altamonte-springs-longwood": "Altamonte Springs", "lake-mary-sanford": "Lake Mary",
        "clermont": "Clermont", "st-cloud": "St. Cloud", "apopka": "Apopka",
    }.get(corridor_slug)


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
                json.dump(doc, fh, indent=1)
                fh.write("\n")
            print("WROTE", os.path.relpath(path, _DASH))
    print("corridors=%d  admitted_zips=%d  cells=%d (admitting %d, observation %d)" % (
        report["corridor_count"], report["admitted_postal_code_count"], report["cells_total"],
        report["cells_admitting"], report["cells_observation_only"]))
    print("by class:", json.dumps(report["corridor_count_by_class"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
