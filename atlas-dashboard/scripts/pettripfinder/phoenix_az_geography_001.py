"""PTF-PHOENIX-AZ-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4 and 5: the Phoenix / Scottsdale / Valley of the Sun market.

Built from zero on the CURRENT hardened lineage: the Denver-live release 630d1198 (live source edf11b7a, built_from
5bc62502). Current verified live at authoring time = denver-co deploy 6aba7587ddcc33a192bdf694, 36 markets / 2,954
profiles / 3,274 release-index routes / 3,343 served routes, host verified. No earlier Phoenix build exists, and this
is the FIRST Arizona market: no live market owns a single Arizona postal code.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Phoenix / Scottsdale / Valley of the Sun traveller lodging market -- not the City of Phoenix, and not
"Arizona" -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE markets named
inside OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact to make a
number. The order's "STRONG CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property
card) states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted
lodging ZIP is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A
brand's marketing name never admits and never places a property: a hotel titled "Phoenix Airport" whose own address
states Tempe 85281 is a Tempe hotel, and a hotel titled "Scottsdale" whose own address states Phoenix 85054 is a
Desert Ridge hotel.

WHY "PHOENIX" AND "SCOTTSDALE" DECIDE NOTHING HERE
--------------------------------------------------
The chains put "Phoenix" in the name of hotels in Tempe, Mesa, Chandler, Glendale, Peoria, Goodyear, Avondale and
Buckeye, and "Scottsdale" on hotels in Paradise Valley (85253), in the City of Phoenix's Kierland / Desert Ridge
districts (85254 / 85054) and on the Salt River Pima-Maricopa Indian Community (85256). "Phoenix Airport" hotels
stand in Phoenix 85034 / 85008 / 85040 and in Tempe 85281 / 85282. "Chandler" resorts at Wild Horse Pass stand on
the Gila River Indian Community (Chandler postal city 85226). Each is placed by its own postal code.

THE SCOTTSDALE RULING (PHASE 3): FIVE CORRIDORS INSIDE phoenix-az, NEVER FLATTENED INTO GENERIC PHOENIX
------------------------------------------------------------------------------------------------------
Scottsdale is a traveller identity of its own inside the Valley, so it is NOT one line in a Phoenix list and it is
NOT a separate market in this order. It is five corridors, each placed by its own postal codes:
  * OLD TOWN SCOTTSDALE (85251 / 85257) -- CORE. The walkable arts / dining / nightlife district, Fashion Square
    and the Scottsdale Road / Camelback resort row;
  * CENTRAL SCOTTSDALE (85250 / 85258 / 85259 / 85256) -- CORE. McCormick Ranch, Gainey Ranch, Scottsdale Ranch and
    the Talking Stick / Salt River Fields / Pima Road hotels on the Salt River Pima-Maricopa Indian Community;
  * PARADISE VALLEY (85253) -- CORE. The Town of Paradise Valley's luxury-resort cluster on Lincoln Drive and
    Scottsdale Road, most of which carry a SCOTTSDALE postal city; the resort-residence exposure is highest here;
  * SCOTTSDALE AIRPARK / KIERLAND (85260 / 85254) -- STRONG CORRIDOR. The Airpark / Perimeter Center business and
    extended-stay cluster and Kierland Commons / Scottsdale Quarter. 85254 is mostly the CITY OF PHOENIX under a
    Scottsdale name; it is covered whole, never split;
  * NORTH SCOTTSDALE (85255 / 85262 / 85266) -- STRONG CORRIDOR. The Princess / TPC, DC Ranch, Troon North and
    Pinnacle Peak golf-resort cluster.
Scottsdale is recorded as this market's NAMED first candidate for promotion to a standalone market
(scottsdale-az) -- it is not created here.

PET-TRAVEL / DRIVE-MARKET RELEVANCE (PHASE 4)
---------------------------------------------
Phoenix / Scottsdale is a road-trip, snowbird / long-stay, hiking and resort market. That lowers NO evidence
standard: no destination reputation ("dog-friendly Scottsdale", the desert trails, the resorts' marketing) is ever
policy evidence. It shapes only the CENSUS: every trail-access (Camelback, Piestewa, South Mountain, the McDowell
Sonoran Preserve, the Superstitions, Lake Pleasant), extended-stay, spring-training, airport-arrival and I-10 / I-17
road-trip cluster is covered by an admitting cell and an overlay.

RESORT / CASITA / CONDO / VACATION-RENTAL SAFETY (PHASE 5)
----------------------------------------------------------
Qualifying public hotels and resorts (including resort casitas the public operator sells nightly) are admitted on
their own pages. Individual condo units, private villas, Airbnb / Vrbo units, ordinary apartments, individual
timeshare units, residential-only towers, privately managed resort residences and property-management portfolios
are never admitted; a mixed property is admitted only as the exact hotel premises its public operator sells.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/phoenix_az.json
  launch_packages/pettripfinder/markets/proposed/phoenix-az.json
  launch_packages/pettripfinder/markets/reports/phoenix_az_geography_001.json
  launch_packages/pettripfinder/markets/reports/phoenix_az_corridor_registry_001.json
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

WORK_ORDER = "PTF-PHOENIX-AZ-HARDENED-SOURCE-READY-001"
MARKET_ID = "phoenix-az"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "phoenix_az.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "phoenix-az.json")
REPORT_OUT = os.path.join(REPORTS, "phoenix_az_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "phoenix_az_corridor_registry_001.json")
AS_OF = "2026-09-29"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    # ---------------------------------------------------------------- CORE
    ("downtown-phoenix", "Downtown Phoenix", "Downtown / Convention Center / Roosevelt Row / Capitol", "CORE",
     "phoenix", ["85003", "85004", "85007"],
     "Downtown Phoenix's central business district: the Phoenix Convention Center, Chase Field and the Footprint "
     "Center, the Roosevelt Row arts district, ASU's downtown campus, the Arizona State Capitol and the Warehouse "
     "District (85003 / 85004 / 85007). The Convention Center and the stadiums are OVERLAYS, never a split code."),
    ("midtown-central-phoenix", "Midtown & Central Phoenix", "Midtown / Central Avenue / Uptown / Melrose", "CORE",
     "phoenix", ["85006", "85012", "85013", "85014", "85015"],
     "The Central Avenue light-rail spine north of downtown -- Midtown and Park Central (85012 / 85013), Uptown and "
     "Camelback & Central (85013 / 85014), the Heard Museum and Encanto Park, the Melrose district (85015) and the "
     "Coronado / Garfield / Miracle Mile side east of 7th Street (85006)."),
    ("biltmore-camelback-arcadia", "Biltmore, Camelback & Arcadia", "Biltmore / Camelback Corridor / Arcadia", "CORE",
     "phoenix", ["85016", "85018"],
     "The Camelback Corridor and the Biltmore district (85016) -- the Arizona Biltmore, Biltmore Fashion Park and "
     "the 24th Street / Camelback office-and-hotel row -- and Arcadia at the foot of Camelback Mountain (85018): "
     "Royal Palms, the Camelback trailheads and Arcadia's resort edge."),
    ("phx-sky-harbor", "Phoenix Sky Harbor Airport (PHX)", "PHX / Sky Harbor Circle / 44th Street / Papago",
     "CORE", "phoenix", ["85034", "85008", "85040"],
     "Phoenix Sky Harbor International Airport's own lodging system: the airport and the Sky Harbor Circle / 24th "
     "Street / Buckeye Road hotels (85034), the 44th Street / Van Buren / Papago Park cluster north of the "
     "runways (85008) and the University Drive / Broadway / 48th Street hotels south of them (85040). PHX owns its "
     "codes, so the AIRPORT test answers YES. The Tempe hotels marketed as 'Phoenix Airport' (85281 / 85282) are an "
     "OVERLAY of the tempe corridor: Tempe's codes are Tempe's and are never split."),
    ("tempe", "Tempe", "Tempe / ASU / Mill Avenue / Tempe Town Lake", "CORE", "tempe",
     ["85281", "85282", "85283", "85284", "85285", "85287", "85288", "85280"],
     "The City of Tempe: Arizona State University's main campus (85287), Mill Avenue and Tempe Town Lake (85281), "
     "the University Drive / Priest / Broadway 'Phoenix Airport' hotels (85281 / 85282), Tempe Marketplace, the "
     "I-10 / US-60 / Loop 101 interchanges and the Discovery / Elliot business campuses in south Tempe (85283 / "
     "85284). Its own city with its own university, event and airport-overflow demand. 85288 (the Rio Salado / "
     "Tempe Marketplace side, stated as the premises code by two independent bureau listings) and 85280 are Tempe "
     "codes too."),
    ("old-town-scottsdale", "Old Town Scottsdale", "Old Town / Fashion Square / Scottsdale Waterfront / South "
     "Scottsdale", "CORE", "scottsdale", ["85251", "85257"],
     "Old Town Scottsdale (85251): the walkable arts, dining and nightlife district, the Scottsdale Waterfront, "
     "Scottsdale Fashion Square and the Scottsdale Road / Camelback resort row -- and south Scottsdale on McDowell "
     "Road and Papago Park's east edge (85257). Scottsdale's own traveller identity, never flattened into generic "
     "Phoenix; see scottsdale_ruling."),
    ("central-scottsdale", "Central Scottsdale & Talking Stick", "McCormick Ranch / Gainey Ranch / Scottsdale Ranch / "
     "Talking Stick", "CORE", "scottsdale", ["85250", "85256", "85258", "85259"],
     "Central Scottsdale: the Indian Bend / Scottsdale Road residential-resort band (85250), McCormick Ranch and "
     "Gainey Ranch (85258), Scottsdale Ranch and the east side to the McDowell Mountains (85259), and the Talking "
     "Stick / Salt River Fields / Pima Road hotels on the Salt River Pima-Maricopa Indian Community whose postal "
     "city is SCOTTSDALE (85256). A resort-and-spring-training cluster between Old Town and the Airpark."),
    ("paradise-valley", "Paradise Valley", "Paradise Valley resorts / Lincoln Drive / Mummy Mountain", "CORE",
     "paradise valley", ["85253"],
     "The Town of Paradise Valley (85253) between Camelback and Mummy Mountains: the Valley's densest luxury-resort "
     "cluster (Lincoln Drive, Scottsdale Road and Camelback's north face), most of it under a SCOTTSDALE postal "
     "city. The resort-residence and private-villa exposure is highest here: only the exact hotel premises a public "
     "operator sells nightly is admitted."),
    ("mesa", "Mesa", "Mesa / Riverview / Superstition Springs / Mesa Gateway (AZA)", "CORE", "mesa",
     ["85201", "85202", "85203", "85204", "85205", "85206", "85207", "85208", "85209", "85210", "85212", "85213",
      "85215"],
     "The City of Mesa: downtown Mesa, Riverview / Mesa Riverview and Sloan Park (the Cubs' spring training, "
     "85201), the Fiesta / Dobson / US-60 hotel rows (85202 / 85210), Superstition Springs and east Mesa (85206 / "
     "85208 / 85209), the Red Mountain / Usery Pass side to the Salt River recreation area (85207 / 85215) and the "
     "Phoenix-Mesa Gateway Airport (AZA) hotels (85212). The Valley's second city with its own airport."),
    ("chandler", "Chandler & Wild Horse Pass", "Chandler / Price Corridor / Downtown Chandler / Wild Horse Pass",
     "CORE", "chandler", ["85224", "85225", "85226", "85248", "85249", "85286"],
     "The City of Chandler: the Price Road / Loop 101 business corridor and Chandler Fashion Center (85226 / 85286), "
     "downtown Chandler (85225), the I-10 / Ray Road hotels (85224 / 85226), Ocotillo and Sun Lakes (85248 / 85249) "
     "-- and the Wild Horse Pass resort and casino hotels on the Gila River Indian Community whose postal city is "
     "CHANDLER (85226)."),
    ("glendale", "Glendale & Westgate", "Glendale / Westgate / State Farm Stadium / Arrowhead", "CORE", "glendale",
     ["85301", "85302", "85303", "85304", "85305", "85306", "85307", "85308", "85310"],
     "The City of Glendale: the Westgate Entertainment District, State Farm Stadium and Desert Diamond Arena "
     "(85305), downtown Glendale (85301), the Loop 101 / Northern Avenue hotels (85303 / 85307), Arrowhead Towne "
     "Center (85308) and the north side (85310). The West Valley's event and stadium lodging core."),
    # ---------------------------------------------------------------- STRONG CORRIDOR
    ("scottsdale-airpark-kierland", "Scottsdale Airpark & Kierland", "Scottsdale Airpark / Perimeter Center / "
     "Kierland Commons / Scottsdale Quarter", "CORRIDOR", "scottsdale", ["85254", "85260"],
     "The Scottsdale Airpark / Perimeter Center / Frank Lloyd Wright Boulevard business-and-extended-stay cluster "
     "(85260) and Kierland Commons / Scottsdale Quarter with the Greenway Parkway resort (85254). 85254 is mostly the "
     "CITY OF PHOENIX under a Scottsdale name and reaches west to Paradise Valley Village; it is covered whole, never "
     "split. A STRONG CORRIDOR of Scottsdale's own."),
    ("north-scottsdale", "North Scottsdale", "Princess / TPC / DC Ranch / Troon North / Pinnacle Peak", "CORRIDOR",
     "scottsdale", ["85255", "85262", "85266"],
     "North Scottsdale's golf-resort and desert-trail cluster: the Princess / TPC Scottsdale, DC Ranch and Grayhawk "
     "(85255), Troon North, Pinnacle Peak and the McDowell Sonoran Preserve trailheads (85262 / 85266). A STRONG "
     "CORRIDOR of Scottsdale's own."),
    ("desert-ridge-mayo", "Desert Ridge & Mayo Clinic", "Desert Ridge / Mayo Clinic Hospital / Loop 101 & Tatum",
     "CORRIDOR", "phoenix", ["85050", "85054"],
     "North-east Phoenix on the Loop 101: the Desert Ridge resort and marketplace (85054 / 85050) and the Mayo Clinic "
     "Hospital campus (85054). Hotels here are marketed as 'Scottsdale'; their own codes place them in the City of "
     "Phoenix's Desert Ridge. Medical, resort and business demand."),
    ("north-phoenix-deer-valley", "North Phoenix & Deer Valley", "North Phoenix / Deer Valley / I-17 / Norterra / "
     "Anthem", "CORRIDOR", "phoenix",
     ["85020", "85021", "85022", "85023", "85024", "85027", "85028", "85029", "85032", "85051", "85053", "85083",
      "85085", "85086", "85087"],
     "North Phoenix along I-17 and the Piestewa / SR-51: the Squaw Peak / Tapatio Cliffs resort pair and the "
     "Phoenix Mountains Preserve (85020 / 85022), Metrocenter and the I-17 / Dunlap / Peoria hotel rows (85021 / "
     "85029 / 85051), Deer Valley and its airport (85027), Paradise Valley Village and Moon Valley (85028 / 85032 / "
     "85023), Norterra / Happy Valley (85083 / 85085) and Anthem / New River on the I-17 road to the high country "
     "(85086 / 85087)."),
    ("west-phoenix", "West Phoenix & Tolleson", "West Phoenix / I-10 West / Desert Sky / Tolleson", "CORRIDOR",
     "phoenix", ["85009", "85017", "85019", "85031", "85033", "85035", "85037", "85039", "85043", "85353"],
     "The west side on I-10 and Grand Avenue: the I-10 / 51st Avenue and 27th-35th Avenue hotel rows (85009 / "
     "85043), Maryvale and Desert Sky (85031 / 85033 / 85035 / 85037), west-central Phoenix (85017 / 85019) and "
     "Tolleson's I-10 / 99th Avenue exit (85353). Drive-market and budget lodging."),
    ("ahwatukee-south-mountain", "Ahwatukee & South Mountain", "Ahwatukee Foothills / South Mountain / Laveen",
     "CORRIDOR", "phoenix", ["85041", "85042", "85044", "85045", "85048", "85339"],
     "The Ahwatukee Foothills on I-10 at Baseline, Elliot, Ray and Chandler Boulevard (85044 / 85045 / 85048), the "
     "resort at South Mountain's east end, South Phoenix and South Mountain Park -- the largest municipal park in "
     "the country (85041 / 85042) -- and Laveen (85339). Trail access and I-10 drive lodging."),
    ("gilbert", "Gilbert", "Gilbert / Heritage District / San Tan Village", "CORRIDOR", "gilbert",
     ["85233", "85234", "85295", "85296", "85297", "85298"],
     "The Town of Gilbert: the Heritage District (85233 / 85234), the Loop 202 / San Tan Village hotel row (85295 / "
     "85297 / 85298) and the Val Vista / Higley side (85296). A suburban drive market with a growing hotel "
     "inventory."),
    ("peoria", "Peoria", "Peoria / P83 / Peoria Sports Complex / Lake Pleasant", "CORRIDOR", "peoria",
     ["85345", "85381", "85382", "85383"],
     "The City of Peoria: the P83 entertainment district and the Peoria Sports Complex (Padres and Mariners spring "
     "training, 85382), old-town Peoria on Grand Avenue (85345), and north Peoria on the Lake Pleasant Parkway to "
     "Lake Pleasant Regional Park (85383)."),
    ("goodyear-avondale-litchfield", "Goodyear, Avondale & Litchfield Park", "Goodyear / Avondale / Litchfield Park / "
     "Phoenix Raceway", "CORRIDOR", "goodyear", ["85323", "85338", "85340", "85392", "85395"],
     "The south-west Valley on I-10: the Goodyear Ballpark and the I-10 / Litchfield Road / Estrella hotels (85338 / "
     "85395), Avondale and Phoenix Raceway's approach (85323 / 85392) and the City of Litchfield Park with its "
     "historic resort (85340). The three share the I-10 exits and are one corridor, never a split code."),
    ("surprise-sun-city", "Surprise & Sun City", "Surprise / Surprise Stadium / Sun City / Sun City West / El "
     "Mirage", "CORRIDOR", "surprise", ["85335", "85351", "85363", "85373", "85374", "85375", "85378", "85379",
                                        "85387", "85388"],
     "The north-west Valley on Grand Avenue and Bell Road: Surprise and the Surprise Stadium spring-training "
     "complex (85374 / 85378 / 85379 / 85387 / 85388), El Mirage (85335), the Town of Youngtown (85363, an "
     "enclave on Grand Avenue between Sun City and El Mirage -- measured: a Quality Inn states it) and the Sun City "
     "retirement communities (85351 / 85373 / 85375). Snowbird and spring-training lodging; Sun City is an overlay "
     "of this corridor."),
    ("fountain-hills-fort-mcdowell", "Fountain Hills & Fort McDowell", "Fountain Hills / Fort McDowell / Verde River",
     "CORRIDOR", "fountain hills", ["85264", "85268"],
     "The Town of Fountain Hills (85268) and the Fort McDowell Yavapai Nation's resort and casino (85264) on the "
     "Beeline Highway, the gateway to the Verde River and the McDowell Mountain Regional Park."),
    # ---------------------------------------------------------------- FRINGE
    ("queen-creek", "Queen Creek", "Queen Creek / San Tan Mountains", "FRINGE", "queen creek", ["85142", "85242"],
     "The Town of Queen Creek (85142, and its former code 85242, which a hotel's own page still states -- measured: "
     "Hampton Inn Queen Creek) at the south-east edge of the Valley. Admitted at FRINGE so its small hotel "
     "inventory is ACCOUNTED FOR; San Tan Valley's Pinal County codes (85140 / 85143) are refused."),
    ("apache-junction-gold-canyon", "Apache Junction & Gold Canyon", "Apache Junction / Gold Canyon / Superstition "
     "Mountains", "FRINGE", "apache junction", ["85118", "85119", "85120"],
     "The City of Apache Junction (85119 / 85120) and Gold Canyon (85118) at the foot of the Superstition "
     "Mountains, contiguous with east Mesa: the Lost Dutchman State Park and Apache Trail gateway. Admitted at "
     "FRINGE -- the Valley's urban edge and a trail-access cluster -- and placed by its own codes."),
    ("buckeye", "Buckeye", "Buckeye / Verrado / I-10 west", "FRINGE", "buckeye", ["85326", "85396"],
     "The City of Buckeye (85326 / 85396) on I-10 west of Goodyear, the Valley's last exits toward California. "
     "Admitted at FRINGE so the inventory is accounted for; Tonopah and Gila Bend are refused."),
    ("cave-creek-carefree", "Cave Creek & Carefree", "Cave Creek / Carefree / Tonto National Forest edge", "FRINGE",
     "cave creek", ["85331", "85377"],
     "The Towns of Cave Creek (85331) and Carefree (85377), north of Scottsdale and Phoenix at the Tonto National "
     "Forest edge: a desert-resort and trail-town pair. Admitted at FRINGE."),
]

OUTSIDE = [
    ("Sedona / Verde Valley -- Sedona, Oak Creek, Cottonwood, Clarkdale, Jerome, Camp Verde", "AZ",
     ["86336", "86351", "86339", "86324", "86326", "86322", "86325", "86335", "86331"],
     "YAVAPAI / COCONINO COUNTY; FUTURE_STANDALONE sedona-az. Refused by name and postal code (863 prefix). 115 "
     "miles north of Phoenix on I-17 with its own red-rock resort, spa and vacation-rental product."),
    ("Flagstaff / northern Arizona high country", "AZ",
     ["86001", "86004", "86005", "86011", "86015", "86017", "86018"],
     "COCONINO COUNTY; FUTURE_STANDALONE flagstaff-az. Refused by name and postal prefix (860). 145 miles north at "
     "7,000 feet with its own airport (FLG), NAU, Route 66 and I-40 / I-17 junction demand."),
    ("Grand Canyon lodging -- Grand Canyon Village, Tusayan, Williams, Valle", "AZ",
     ["86023", "86046", "86052"],
     "COCONINO COUNTY; FUTURE_STANDALONE grand-canyon-az. The national-park gateway lodging markets, refused by name "
     "and prefix (860)."),
    ("Prescott / Prescott Valley / Chino Valley", "AZ",
     ["86301", "86303", "86305", "86313", "86314", "86315", "86323", "86327"],
     "YAVAPAI COUNTY; FUTURE_STANDALONE prescott-az. Refused by name and prefix (863). 100 miles north-west, a "
     "mountain-town and lake market of its own."),
    ("Tucson metro -- Tucson, Oro Valley, Marana, Sahuarita, Green Valley", "AZ",
     ["85701", "85704", "85705", "85706", "85710", "85711", "85712", "85713", "85714", "85715", "85716", "85718",
      "85719", "85737", "85741", "85742", "85743", "85745", "85746", "85747", "85748", "85749", "85750", "85756",
      "85757", "85614", "85629", "85653", "85658"],
     "PIMA COUNTY; FUTURE_STANDALONE tucson-az. Refused by name and postal prefix (856 / 857). 115 miles south-east "
     "on I-10 with its own airport (TUS), the University of Arizona and its own resort market."),
    ("Payson / Rim Country", "AZ",
     ["85541", "85544", "85547", "85553", "85554"],
     "GILA COUNTY; refused by name and prefix (855). The Mogollon Rim cabin-and-lake country 90 miles north-east."),
    ("Pinal County outside the contiguous East Valley -- Casa Grande, Maricopa, Florence, Eloy, Coolidge, San Tan "
     "Valley, Superior, Arizona City", "AZ",
     ["85122", "85123", "85128", "85131", "85132", "85138", "85139", "85140", "85143", "85144", "85145", "85172",
      "85173", "85193", "85194"],
     "PINAL COUNTY; refused by name. The I-10 / I-8 towns south of the Gila River Indian Community (Casa Grande, the "
     "City of Maricopa and its Ak-Chin casino hotel, Eloy), Florence and Coolidge, San Tan Valley's Pinal codes and "
     "Superior on US-60. Apache Junction / Gold Canyon and Queen Creek -- contiguous with Mesa -- are the Pinal "
     "edge this market admits."),
    ("North-west and west Maricopa County -- Wickenburg, Morristown, Wittmann, Tonopah, Gila Bend, Arlington", "AZ",
     ["85390", "85342", "85361", "85354", "85337", "85322", "85343"],
     "MARICOPA COUNTY outside the metro; refused by name. Wickenburg's dude-ranch town 55 miles north-west, and the "
     "I-10 / I-8 desert exits at Tonopah and Gila Bend. County inclusion is not traveller-market inclusion."),
    ("Yuma / western Arizona river towns -- Yuma, Parker, Quartzsite", "AZ",
     ["85364", "85365", "85367", "85344", "85346", "85348"],
     "YUMA / LA PAZ COUNTY; refused by name (these share the 853 prefix with the West Valley and are listed so none "
     "falls through)."),
    ("Lake Havasu / Kingman / Bullhead City -- Mohave County river and Route 66 markets", "AZ",
     ["86401", "86403", "86404", "86406", "86409", "86429", "86430", "86440", "86442"],
     "MOHAVE COUNTY; OTHER ARIZONA RESORT MARKETS. Refused by name and prefix (864)."),
    ("Page / Lake Powell / Navajo Nation / White Mountains / Globe / Safford", "AZ",
     ["86040", "85501", "85539", "85546", "85901", "85935", "85929"],
     "OTHER ARIZONA MARKETS; refused by name and prefix (855 / 859 / 860 / 865)."),
    ("Nevada / California / Utah / New Mexico / Sonora", "--",
     [],
     "OUT OF STATE. Las Vegas, Southern California, St George, Albuquerque and every non-Arizona postal code are "
     "refused by prefix."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("855", "Gila / Graham / Greenlee County (Payson, Globe, Safford)", ""),
    ("856", "southern Arizona (Tucson region, Nogales, Sierra Vista)", "tucson-az"),
    ("857", "Tucson", "tucson-az"),
    ("859", "White Mountains (Show Low, Pinetop)", ""),
    ("860", "northern Arizona (Flagstaff, Grand Canyon, Williams, Page)", "flagstaff-az"),
    ("863", "Yavapai County (Prescott, Sedona, Verde Valley)", "sedona-az / prescott-az"),
    ("864", "Mohave County (Kingman, Lake Havasu, Bullhead City)", ""),
    ("865", "Navajo / Apache County (Holbrook, Winslow)", ""),
    ("889", "Nevada", ""), ("890", "Nevada", ""), ("891", "Nevada (Las Vegas)", ""),
    ("922", "California (Imperial / Riverside desert)", ""), ("923", "California", ""),
    ("840", "Utah", ""), ("847", "Utah", ""), ("870", "New Mexico", ""), ("873", "New Mexico", ""),
]

#: The Valley's own postal prefixes. A code under one of these that no corridor claims is an UNCLAIMED Valley
#: code -- refused, and named in the boundary audit so it is visible, never silently dropped.
VALLEY_PREFIXES = ("850", "851", "852", "853")

ADMITTED_COUNTIES = {"maricopa", "pinal (apache junction / gold canyon / queen creek edge only)"}
OBSERVED_COUNTIES = OrderedDict([
    ("yavapai / coconino (sedona, verde valley)", "sedona-az"),
    ("coconino (flagstaff)", "flagstaff-az"),
    ("coconino (grand canyon, tusayan, williams)", "grand-canyon-az"),
    ("yavapai (prescott)", "prescott-az"),
    ("pima", "tucson-az"),
    ("gila (payson)", "(none -- refused by name and prefix)"),
    ("pinal (casa grande, maricopa, florence, san tan valley)", "(none -- refused by name)"),
    ("mohave (lake havasu, kingman, bullhead)", "(none -- other Arizona resort markets, refused by prefix)"),
])

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("maricopa", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. The contiguous Valley -- Phoenix, Scottsdale, Paradise Valley, Tempe, Mesa, "
                   "Chandler, Gilbert, Glendale, Peoria, Surprise, Goodyear, Avondale, Litchfield Park, Buckeye, "
                   "Tolleson, Fountain Hills, Cave Creek, Carefree, Queen Creek and the Salt River / Fort McDowell / "
                   "Gila River resort lands inside the metro -- is admitted; Wickenburg, Gila Bend, Tonopah and the "
                   "western desert are REFUSED by name. County inclusion is not traveller-market inclusion."),
    ])),
    ("pinal", OrderedDict([
        ("ruling", "ADMITTED ONLY AT THE EAST VALLEY EDGE. Apache Junction / Gold Canyon and Queen Creek's Pinal "
                   "side are contiguous with Mesa and admitted at FRINGE; Casa Grande, the City of Maricopa, "
                   "Florence, Eloy, Coolidge, San Tan Valley and Superior are refused."),
    ])),
    ("yavapai / coconino / pima / gila / mohave", OrderedDict([
        ("ruling", "REFUSED. Sedona, Flagstaff, the Grand Canyon, Prescott and Tucson are separate markets, named "
                   "FUTURE_STANDALONE; Payson, Lake Havasu, Kingman and Bullhead City are refused by name and "
                   "prefix. Phoenix does not absorb Arizona."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / member only).
NONPUBLIC_NAMES = {
    "luke air force base lodging": "US Air Force billeting -- not public lodging",
    "luke lodge": "US Air Force billeting -- not public lodging",
    "fisher house phoenix": "VA / military family lodging -- not public lodging",
    "fisher house": "VA / military family lodging -- not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "ronald mcdonald house of central and northern arizona": "charitable family lodging -- not public lodging",
    "ronald mcdonald house phoenix": "charitable family lodging -- not public lodging",
}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-phoenix", "Phoenix", "Downtown Phoenix / Convention Center", 33.4500, -112.0740, 2600, True),
    ("midtown-central-phoenix", "Phoenix", "Midtown / Central Ave / Uptown", 33.4850, -112.0700, 3500, True),
    ("biltmore-camelback-arcadia", "Phoenix", "Biltmore / Camelback / Arcadia", 33.5000, -112.0000, 4500, True),
    ("phx-sky-harbor", "Phoenix", "PHX / Sky Harbor / 44th St", 33.4300, -112.0000, 5000, True),
    ("tempe", "Tempe", "Tempe / ASU / airport hotels", 33.3900, -111.9300, 9000, True),
    ("old-town-scottsdale", "Scottsdale", "Old Town Scottsdale", 33.4900, -111.9250, 3500, True),
    ("central-scottsdale", "Scottsdale", "McCormick / Gainey / Talking Stick", 33.5600, -111.8900, 6000, True),
    ("paradise-valley", "Paradise Valley", "Paradise Valley resorts", 33.5400, -111.9600, 4500, True),
    ("mesa", "Mesa", "Mesa / AZA", 33.4000, -111.7300, 14000, True),
    ("chandler", "Chandler", "Chandler / Price corridor / Wild Horse Pass", 33.2900, -111.8800, 10000, True),
    ("glendale", "Glendale", "Glendale / Westgate / Arrowhead", 33.5700, -112.2000, 10000, True),
    ("scottsdale-airpark-kierland", "Scottsdale", "Airpark / Kierland", 33.6200, -111.9300, 4500, True),
    ("north-scottsdale", "Scottsdale", "North Scottsdale / Troon / Pinnacle Peak", 33.7000, -111.8600, 12000, True),
    ("desert-ridge-mayo", "Phoenix", "Desert Ridge / Mayo Clinic", 33.6800, -111.9700, 4000, True),
    ("north-phoenix-deer-valley", "Phoenix", "North Phoenix / Deer Valley / Norterra", 33.6700, -112.0900, 14000,
     True),
    ("west-phoenix", "Phoenix", "West Phoenix / Tolleson", 33.4700, -112.1900, 10000, True),
    ("ahwatukee-south-mountain", "Phoenix", "Ahwatukee / South Mountain", 33.3500, -112.0200, 9000, True),
    ("gilbert", "Gilbert", "Gilbert", 33.3200, -111.7500, 9000, True),
    ("peoria", "Peoria", "Peoria / P83 / Lake Pleasant", 33.6500, -112.2600, 10000, True),
    ("goodyear-avondale-litchfield", "Goodyear", "Goodyear / Avondale / Litchfield Park", 33.4400, -112.3600, 9000,
     True),
    ("surprise-sun-city", "Surprise", "Surprise / Sun City", 33.6300, -112.3300, 10000, True),
    ("fountain-hills-fort-mcdowell", "Fountain Hills", "Fountain Hills / Fort McDowell", 33.6200, -111.7100, 6000,
     True),
    ("queen-creek", "Queen Creek", "Queen Creek", 33.2500, -111.6400, 6000, True),
    ("apache-junction-gold-canyon", "Apache Junction", "Apache Junction / Gold Canyon", 33.3900, -111.5000, 9000,
     True),
    ("buckeye", "Buckeye", "Buckeye", 33.4000, -112.5800, 9000, True),
    ("cave-creek-carefree", "Cave Creek", "Cave Creek / Carefree", 33.8300, -111.9300, 6000, True),
    ("obs-sedona", "Sedona", "Sedona / Verde Valley -- OBSERVATION ONLY", 34.8200, -111.8500, 20000, False),
    ("obs-flagstaff", "Flagstaff", "Flagstaff -- OBSERVATION ONLY", 35.1983, -111.6513, 12000, False),
    ("obs-prescott", "Prescott", "Prescott / Prescott Valley -- OBSERVATION ONLY", 34.5700, -112.4000, 15000, False),
    ("obs-tucson", "Tucson", "Tucson metro -- OBSERVATION ONLY", 32.2500, -110.9700, 25000, False),
    ("obs-payson", "Payson", "Payson -- OBSERVATION ONLY", 34.2309, -111.3251, 8000, False),
    ("obs-casa-grande", "Casa Grande", "Casa Grande / Maricopa -- OBSERVATION ONLY (Pinal County)", 32.9500,
     -111.9000, 20000, False),
    ("obs-wickenburg", "Wickenburg", "Wickenburg -- OBSERVATION ONLY", 33.9686, -112.7296, 8000, False),
]

#: The Overpass / observation box. It reaches north past Sedona, Prescott and Flagstaff and south-east past
#: Tucson, so the census counts what it refuses. The Grand Canyon (36.05), Page, Lake Havasu and Yuma lie outside
#: the box and are audited from the brand lanes instead.
BOUNDS = {"min_lat": 31.95, "max_lat": 35.40, "min_lng": -113.00, "max_lng": -110.70}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Phoenix Convention Center", 33.4430, -112.0700, 0.6),
    ("Chase Field / Footprint Center", 33.4455, -112.0667, 0.5),
    ("Roosevelt Row", 33.4586, -112.0668, 0.7),
    ("Arizona State Capitol", 33.4481, -112.0970, 0.9),
    ("Downtown Phoenix CBD", 33.4500, -112.0740, 1.2),
    ("Midtown / Park Central", 33.4870, -112.0740, 1.2),
    ("Uptown / Camelback & Central", 33.5093, -112.0740, 1.2),
    ("Biltmore / 24th St & Camelback", 33.5095, -112.0290, 1.6),
    ("Arcadia / Camelback Mountain", 33.4960, -111.9800, 1.8),
    ("PHX terminals / Sky Harbor Circle", 33.4342, -112.0116, 2.4),
    ("44th St / Papago", 33.4500, -111.9860, 1.6),
    ("Tempe 'Phoenix Airport' hotels (University / Priest)", 33.4210, -111.9700, 1.8),
    ("ASU / Mill Ave / Tempe Town Lake", 33.4255, -111.9400, 1.4),
    ("Tempe Marketplace", 33.4300, -111.9000, 1.2),
    ("South Tempe / Discovery / I-10 & Elliot", 33.3500, -111.9600, 2.4),
    ("Old Town Scottsdale", 33.4942, -111.9261, 1.2),
    ("Scottsdale Fashion Square / Camelback resorts", 33.5020, -111.9290, 0.9),
    ("Talking Stick / Salt River Fields", 33.5440, -111.8840, 1.6),
    ("McCormick Ranch / Gainey Ranch", 33.5700, -111.9000, 2.0),
    ("Paradise Valley resorts (Lincoln Dr)", 33.5310, -111.9500, 2.4),
    ("Scottsdale Airpark / Perimeter Center", 33.6200, -111.9100, 1.8),
    ("Kierland / Scottsdale Quarter", 33.6260, -111.9280, 1.0),
    ("Princess / TPC Scottsdale", 33.6400, -111.9050, 1.4),
    ("Troon North / Pinnacle Peak", 33.7300, -111.8600, 4.0),
    ("Desert Ridge / Mayo Clinic Hospital", 33.6750, -111.9720, 2.0),
    ("Squaw Peak / Tapatio Cliffs / Phoenix Mountains", 33.5600, -112.0500, 2.4),
    ("Deer Valley / I-17 & Bell", 33.6400, -112.1150, 2.4),
    ("Norterra / Happy Valley", 33.7100, -112.1100, 2.4),
    ("Anthem", 33.8600, -112.1400, 3.0),
    ("West Phoenix I-10 & 51st Ave", 33.4600, -112.1680, 2.4),
    ("Desert Sky / I-10 & 75th-99th Ave", 33.4600, -112.2300, 3.0),
    ("Ahwatukee / I-10 & Elliot-Ray", 33.3350, -111.9750, 2.4),
    ("South Mountain Park", 33.3450, -112.0700, 3.0),
    ("Downtown Mesa / Riverview / Sloan Park", 33.4250, -111.8310, 2.4),
    ("Mesa Fiesta / Dobson / US-60", 33.3900, -111.8700, 2.0),
    ("Superstition Springs (Mesa)", 33.3850, -111.6900, 2.4),
    ("Phoenix-Mesa Gateway Airport (AZA)", 33.3080, -111.6700, 3.0),
    ("Chandler Price corridor / Chandler Fashion", 33.3040, -111.8960, 2.0),
    ("Downtown Chandler", 33.3030, -111.8410, 1.2),
    ("Wild Horse Pass", 33.2700, -111.9950, 3.0),
    ("Gilbert Heritage District", 33.3510, -111.7890, 1.4),
    ("San Tan Village (Gilbert)", 33.3000, -111.7440, 2.0),
    ("Westgate / State Farm Stadium", 33.5320, -112.2610, 1.6),
    ("Downtown Glendale", 33.5387, -112.1860, 1.4),
    ("Arrowhead", 33.6440, -112.2250, 1.8),
    ("P83 / Peoria Sports Complex", 33.6380, -112.2350, 1.4),
    ("Lake Pleasant", 33.8500, -112.2700, 6.0),
    ("Goodyear I-10 / Litchfield Rd", 33.4600, -112.3600, 2.4),
    ("Phoenix Raceway (Avondale)", 33.3750, -112.3110, 2.4),
    ("Surprise Stadium", 33.6280, -112.3790, 2.0),
    ("Sun City", 33.6000, -112.2800, 3.0),
    ("Fountain Hills", 33.6100, -111.7200, 3.0),
    ("Fort McDowell / We-Ko-Pa", 33.6500, -111.6750, 3.0),
    ("Queen Creek", 33.2480, -111.6340, 3.0),
    ("Apache Junction / Superstition Mountains", 33.4150, -111.5500, 3.0),
    ("Gold Canyon", 33.3700, -111.4400, 3.0),
    ("Buckeye", 33.3700, -112.5800, 4.0),
    ("Cave Creek / Carefree", 33.8300, -111.9350, 3.0),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Phoenix Convention Center", re.compile(r"\bn 3rd st\b(?=.*85004)|\bw monroe st\b(?=.*85004)|"
                                             r"\bn 2nd st\b(?=.*85004)", re.I)),
    ("PHX terminals / Sky Harbor Circle", re.compile(r"\bsky harbor\b|\bbuckeye r(oa)?d\b(?=.*85034)|"
                                                     r"\bn 24th st\b(?=.*85034)", re.I)),
    ("44th St / Papago", re.compile(r"\bn 44th st\b(?=.*8500[8])|\bpapago\b|\be van buren\b(?=.*85008)", re.I)),
    ("Tempe 'Phoenix Airport' hotels (University / Priest)", re.compile(
        r"\bw university dr\b(?=.*8528[12])|\bs priest dr\b|\bs 5[2-6]th st\b(?=.*8528[12])", re.I)),
    ("ASU / Mill Ave / Tempe Town Lake", re.compile(r"\bmill ave\b|\brio salado\b|\bw 6th st\b(?=.*85281)|"
                                                    r"\bfarmer ave\b", re.I)),
    ("Old Town Scottsdale", re.compile(r"\bn scottsdale r(oa)?d\b(?=.*85251)|\bmarshall way\b|\bwinfield scott\b|"
                                       r"\be indian school r(oa)?d\b(?=.*85251)|\bsaddlebag trl\b", re.I)),
    ("Talking Stick / Salt River Fields", re.compile(r"\btalking stick\b|\bvia de ventura\b|\bpima r(oa)?d\b"
                                                     r"(?=.*85256)|\bthe pavilions\b", re.I)),
    ("Paradise Valley resorts (Lincoln Dr)", re.compile(r"\be lincoln dr\b|\bmockingbird ln\b|\bpalo cristi\b|"
                                                        r"\bjackrabbit\b(?=.*85253)", re.I)),
    ("Scottsdale Airpark / Perimeter Center", re.compile(r"\bperimeter\b|\bfrank lloyd wright\b|\bn 7[3-9]th "
                                                         r"(st|pl|way)\b(?=.*85260)|\bredfield\b|\bgreenway-hayden\b",
                                                         re.I)),
    ("Kierland / Scottsdale Quarter", re.compile(r"\bkierland\b|\be greenway pkwy\b(?=.*85254)|\bn scottsdale "
                                                 r"r(oa)?d\b(?=.*85254)", re.I)),
    ("Princess / TPC Scottsdale", re.compile(r"\bprincess dr\b|\be princess\b", re.I)),
    ("Desert Ridge / Mayo Clinic Hospital", re.compile(r"\bmarriott dr\b|\bdesert ridge\b|\bmayo b(lv)?d\b|"
                                                       r"\bn 56th st\b(?=.*85054)", re.I)),
    ("Westgate / State Farm Stadium", re.compile(r"\bw coyotes b(lv)?d\b|\bwestgate\b|\bn 9[1-5]th ave\b(?=.*85305)",
                                                 re.I)),
    ("Chandler Price corridor / Chandler Fashion", re.compile(r"\bs price r(oa)?d\b|\bw chandler b(lv)?d\b(?=.*85226)|"
                                                              r"\bchandler village dr\b", re.I)),
    ("Wild Horse Pass", re.compile(r"\bwild horse pass\b", re.I)),
    ("Phoenix-Mesa Gateway Airport (AZA)", re.compile(r"\bs ellsworth r(oa)?d\b(?=.*85212)|\bgateway\b(?=.*85212)|"
                                                      r"\bs sossaman\b", re.I)),
    ("Downtown Mesa / Riverview / Sloan Park", re.compile(r"\briverview\b|\bn dobson r(oa)?d\b(?=.*85201)|"
                                                          r"\bw rio salado pkwy\b(?=.*85201)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-phoenix": "Downtown Phoenix",
    "midtown-central-phoenix": "Midtown Phoenix",
    "biltmore-camelback-arcadia": "Biltmore / Camelback",
    "phx-sky-harbor": "PHX Airport",
    "tempe": "Tempe",
    "old-town-scottsdale": "Old Town Scottsdale",
    "central-scottsdale": "Central Scottsdale",
    "paradise-valley": "Paradise Valley",
    "mesa": "Mesa",
    "chandler": "Chandler",
    "glendale": "Glendale",
    "scottsdale-airpark-kierland": "Scottsdale Airpark / Kierland",
    "north-scottsdale": "North Scottsdale",
    "desert-ridge-mayo": "Desert Ridge",
    "north-phoenix-deer-valley": "North Phoenix",
    "west-phoenix": "West Phoenix",
    "ahwatukee-south-mountain": "Ahwatukee",
    "gilbert": "Gilbert",
    "peoria": "Peoria",
    "goodyear-avondale-litchfield": "Goodyear / Avondale",
    "surprise-sun-city": "Surprise",
    "fountain-hills-fort-mcdowell": "Fountain Hills",
    "queen-creek": "Queen Creek",
    "apache-junction-gold-canyon": "Apache Junction",
    "buckeye": "Buckeye",
    "cave-creek-carefree": "Cave Creek / Carefree",
}

#: The order's PRIMARY / STRONG / CAREFUL / FUTURE evaluation list, each classified explicitly.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Phoenix", "ADMITTED (CORE, downtown-phoenix, 85003 / 85004 / 85007). PRIMARY."),
    ("Midtown / Central Phoenix", "ADMITTED (CORE, midtown-central-phoenix, 85006 / 85012-85015). PRIMARY."),
    ("Biltmore / Camelback", "ADMITTED (CORE, biltmore-camelback-arcadia, 85016). PRIMARY."),
    ("Phoenix Sky Harbor / PHX", "ADMITTED (CORE, phx-sky-harbor, 85034 / 85008 / 85040); Tempe's 'Phoenix Airport' "
                                 "hotels (85281 / 85282) are an overlay of tempe. PRIMARY."),
    ("Tempe", "ADMITTED (CORE, tempe, 85280-85285 / 85287 / 85288). PRIMARY."),
    ("Old Town Scottsdale", "ADMITTED (CORE, old-town-scottsdale, 85251 / 85257). PRIMARY -- see scottsdale_ruling."),
    ("Central Scottsdale", "ADMITTED (CORE, central-scottsdale, 85250 / 85256 / 85258 / 85259). PRIMARY."),
    ("North Scottsdale", "ADMITTED (STRONG CORRIDOR, north-scottsdale, 85255 / 85262 / 85266). PRIMARY."),
    ("Paradise Valley", "ADMITTED (CORE, paradise-valley, 85253). PRIMARY."),
    ("Mesa", "ADMITTED (CORE, mesa, 85201-85210 / 85212 / 85213 / 85215). PRIMARY."),
    ("Chandler", "ADMITTED (CORE, chandler, 85224-85226 / 85248 / 85249 / 85286). PRIMARY."),
    ("Gilbert", "ADMITTED (STRONG CORRIDOR, gilbert, 85233 / 85234 / 85295-85298). PRIMARY."),
    ("Glendale", "ADMITTED (CORE, glendale, 85301-85308 / 85310). PRIMARY."),
    ("Peoria", "ADMITTED (STRONG CORRIDOR, peoria, 85345 / 85381-85383). PRIMARY."),
    ("Scottsdale Airpark", "ADMITTED (STRONG CORRIDOR, scottsdale-airpark-kierland, 85260). STRONG."),
    ("Kierland / Scottsdale Quarter", "ADMITTED (STRONG CORRIDOR, scottsdale-airpark-kierland, 85254) -- 85254 is "
                                      "mostly the City of Phoenix under a Scottsdale name, covered whole. STRONG."),
    ("Arcadia", "ADMITTED (CORE, biltmore-camelback-arcadia, 85018). STRONG."),
    ("Ahwatukee", "ADMITTED (STRONG CORRIDOR, ahwatukee-south-mountain, 85044 / 85045 / 85048). STRONG."),
    ("Deer Valley", "ADMITTED (STRONG CORRIDOR, north-phoenix-deer-valley, 85027). STRONG."),
    ("North Phoenix", "ADMITTED (STRONG CORRIDOR, north-phoenix-deer-valley) and Desert Ridge / Mayo (STRONG "
                      "CORRIDOR, desert-ridge-mayo, 85050 / 85054). STRONG."),
    ("West Phoenix", "ADMITTED (STRONG CORRIDOR, west-phoenix, with Tolleson 85353). STRONG."),
    ("Goodyear", "ADMITTED (STRONG CORRIDOR, goodyear-avondale-litchfield, 85338 / 85395). STRONG."),
    ("Avondale", "ADMITTED (STRONG CORRIDOR, goodyear-avondale-litchfield, 85323 / 85392). STRONG."),
    ("Surprise", "ADMITTED (STRONG CORRIDOR, surprise-sun-city, 85374 / 85378 / 85379 / 85387 / 85388). STRONG."),
    ("Fountain Hills", "ADMITTED (STRONG CORRIDOR, fountain-hills-fort-mcdowell, 85268; Fort McDowell 85264). "
                       "STRONG."),
    ("Queen Creek", "ADMITTED (FRINGE, queen-creek, 85142); San Tan Valley's Pinal codes refused. CAREFUL."),
    ("Buckeye", "ADMITTED (FRINGE, buckeye, 85326 / 85396). CAREFUL."),
    ("Litchfield Park", "ADMITTED (STRONG CORRIDOR, goodyear-avondale-litchfield, 85340) -- it shares the I-10 exits "
                        "with Goodyear and Avondale. CAREFUL."),
    ("Sun City", "ADMITTED (STRONG CORRIDOR, surprise-sun-city, 85351 / 85373 / 85375) as an overlay of Surprise. "
                 "CAREFUL."),
    ("Cave Creek", "ADMITTED (FRINGE, cave-creek-carefree, 85331). CAREFUL."),
    ("Carefree", "ADMITTED (FRINGE, cave-creek-carefree, 85377). CAREFUL."),
    ("Apache Junction", "ADMITTED (FRINGE, apache-junction-gold-canyon, 85119 / 85120; Gold Canyon 85118) -- "
                        "contiguous with east Mesa, the Superstition trail gateway. CAREFUL."),
    ("Sedona", "OUTSIDE -- FUTURE_STANDALONE sedona-az."),
    ("Flagstaff", "OUTSIDE -- FUTURE_STANDALONE flagstaff-az."),
    ("Prescott", "OUTSIDE -- FUTURE_STANDALONE prescott-az."),
    ("Tucson", "OUTSIDE -- FUTURE_STANDALONE tucson-az."),
    ("Payson", "OUTSIDE by name and prefix (855)."),
    ("Lake Havasu", "OUTSIDE by name and prefix (864) -- another Arizona resort market."),
    ("Grand Canyon lodging markets", "OUTSIDE -- FUTURE_STANDALONE grand-canyon-az."),
    ("Casa Grande / Maricopa / Florence / San Tan Valley", "OUTSIDE by name (Pinal County outside the East Valley "
                                                           "edge)."),
    ("Wickenburg / Gila Bend / Tonopah", "OUTSIDE by name (Maricopa County outside the metro)."),
])

SCOTTSDALE_RULING = OrderedDict([
    ("classification", "Inside phoenix-az, split into FIVE corridors by its own postal codes: old-town-scottsdale "
                       "(CORE), central-scottsdale (CORE), paradise-valley (CORE), scottsdale-airpark-kierland "
                       "(STRONG CORRIDOR) and north-scottsdale (STRONG CORRIDOR)."),
    ("not_flattened_because", "Scottsdale is a traveller identity of its own -- Old Town's arts, dining and "
                              "nightlife, the resort and spa cluster, spring training, golf and the McDowell Sonoran "
                              "Preserve -- distinct from downtown Phoenix's convention, sports and government "
                              "demand. Each of its districts keeps its own corridor page."),
    ("not_a_separate_market_because", "One airport (PHX) serves both cities, and Scottsdale's hotel geography does "
                                      "not stop at the city line: 'Scottsdale' is the postal city of Paradise "
                                      "Valley's resorts, of the Salt River community's Talking Stick hotels and the "
                                      "marketed name of the City of Phoenix's Kierland and Desert Ridge. A separate "
                                      "market would have to split one postal code (85254) and one resort cluster. "
                                      "The order also forbids creating it here."),
    ("old_town", "CORE -- 85251 / 85257."),
    ("central_scottsdale", "CORE -- 85250 / 85256 / 85258 / 85259 (McCormick Ranch, Gainey Ranch, Talking Stick)."),
    ("paradise_valley_resort_cluster", "CORE -- 85253, its own town; the highest resort-residence exposure, so only "
                                       "exact public hotel premises are admitted."),
    ("kierland_and_airpark", "STRONG CORRIDOR -- 85254 / 85260; 85254 is mostly the City of Phoenix and is covered "
                             "whole."),
    ("north_scottsdale", "STRONG CORRIDOR -- 85255 / 85262 / 85266."),
    ("fringe", "None of Scottsdale is FRINGE. Cave Creek / Carefree to its north are a FRINGE corridor of their own."),
    ("named_optionality", "Recorded as this market's first candidate for promotion to a standalone scottsdale-az "
                          "market, which a founder can split on the record."),
])

STRUCTURE_TEST = OrderedDict([
    ("A. Is the Valley one market, or several?",
     "ONE market, phoenix-az, covering the contiguous Valley of the Sun from Buckeye to Apache Junction and from "
     "Anthem, Cave Creek and Fountain Hills to Queen Creek and Wild Horse Pass. One commercial airport (PHX) serving "
     "the whole Valley (AZA is a secondary airport inside Mesa), one I-10 / I-17 / Loop 101 / Loop 202 / Loop 303 / "
     "US-60 / SR-51 road system, one Valley Metro. The desert, the Gila River and the Mogollon Rim are where that "
     "coherence stops."),
    ("B. The City of Phoenix is NOT the market -- and 'Phoenix' places nothing",
     "Twenty-odd municipalities and three tribal communities are admitted by their own codes; the chains' 'Phoenix' "
     "prefix is on hotels from Buckeye to Mesa."),
    ("C. PHX", "The airport owns its postal code (85034) and its lodging system -- its own CORE corridor, with "
               "Tempe's 'Phoenix Airport' hotels an overlay of tempe."),
    ("D. Scottsdale", "Five corridors of its own inside phoenix-az; see scottsdale_ruling."),
    ("E. Convention Center / stadiums", "NO CORRIDOR of their own -- 85004 / 85003, overlays of downtown."),
    ("F. Westgate / State Farm Stadium", "An overlay of glendale (85305)."),
    ("G. Spring training", "Overlays of the corridors that hold the ballparks (Mesa, Scottsdale, Talking Stick, "
                           "Tempe, Glendale, Peoria, Surprise, Goodyear)."),
    ("H. Sedona", "OUTSIDE -- FUTURE_STANDALONE sedona-az."),
    ("I. Flagstaff / Grand Canyon", "OUTSIDE -- FUTURE_STANDALONE flagstaff-az / grand-canyon-az."),
    ("J. Prescott", "OUTSIDE -- FUTURE_STANDALONE prescott-az."),
    ("K. Tucson", "OUTSIDE -- FUTURE_STANDALONE tucson-az."),
    ("L. Pinal County", "Only Apache Junction / Gold Canyon and Queen Creek (contiguous with Mesa) are admitted, at "
                        "FRINGE."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel operation."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP). A unit designator ('Ste', "
     "'Unit', '#', 'Apt', 'PH', 'Villa', 'Casita') in a registry address means the record is a UNIT INSIDE a "
     "building or campus, which is never a hotel identity."),
    ("hotel_vs_residence_boundary",
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. Phoenix's "
     "specific exposures: the Paradise Valley and North Scottsdale resort residences and private villas (Sanctuary, "
     "Mountain Shadows, Montelucia, Four Seasons Troon North, Ritz-Carlton Paradise Valley), the golf-course "
     "condominium rental pools, Old Town Scottsdale's apartment-hotel and short-term-rental operators (Sonder, Mint "
     "House, Kasa, Placemakr-style portfolios) and the Airbnb / Vrbo casita inventory."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort (Marriott Vacation Club, Hilton Grand Vacations, Club Wyndham, "
     "Diamond / Hilton Vacation Club, Holiday Inn Club Vacations, WorldMark, Westgate) is admitted ONLY if the "
     "operator's own page sells nightly public stays at that premises under a public hotel name. Owner-only / "
     "member-only / points-only resorts and individual timeshare units are TIMESHARE and are never admitted."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared "
     "amenities or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never "
     "published as one. A resort and its residences or villas on one campus are distinct premises."),
    ("extended_stay",
     "Extended-stay hotels are hotels and are admitted on their own pages; an 'apartment hotel' is admitted only "
     "as a public hotel operation at an exact premises."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("85004", ["Downtown Phoenix", "Convention Center", "Roosevelt Row", "Footprint Center"]),
    ("85034", ["PHX Sky Harbor", "Sky Harbor Circle", "Buckeye Road"]),
    ("85281", ["Tempe (Mill Ave / ASU)", "Tempe 'Phoenix Airport' hotels (University / Priest)"]),
    ("85254", ["City of Phoenix (Kierland, Paradise Valley Village)", "Scottsdale (postal city / marketing name)",
               "Paradise Valley edge"]),
    ("85253", ["Paradise Valley", "(postal city Scottsdale for most resorts)"]),
    ("85256", ["Salt River Pima-Maricopa Indian Community", "(postal city Scottsdale)", "Talking Stick"]),
    ("85226", ["Chandler", "Gila River Indian Community (Wild Horse Pass)"]),
    ("85054", ["City of Phoenix (Desert Ridge, Mayo)", "(marketed as Scottsdale)"]),
    ("85340", ["Litchfield Park", "Goodyear edge"]),
])

FUTURE_MARKETS = OrderedDict([
    ("sedona-az", "Sedona / Verde Valley -- 115 miles north, a red-rock resort, spa and vacation-rental market."),
    ("flagstaff-az", "Flagstaff -- 145 miles north at 7,000 feet, its own airport, NAU and Route 66 / I-40 demand."),
    ("grand-canyon-az", "Grand Canyon Village / Tusayan / Williams -- the national-park gateway lodging markets."),
    ("prescott-az", "Prescott / Prescott Valley -- a mountain-town and lake market 100 miles north-west."),
    ("tucson-az", "Tucson -- 115 miles south-east, its own airport, university and resort market."),
    ("scottsdale-az", "NAMED OPTIONALITY, not a refusal. Scottsdale is ADMITTED here as five corridors and recorded as "
                      "this market's first candidate for promotion to a standalone market."),
])

#: Markets that are ALREADY LIVE. None of them owns an Arizona postal code; named so the collision guards know the
#: only exposure is NAME, never premises.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("denver-co", "Denver / Boulder / Front Range, live as production market #36 (deploy 6aba7587ddcc33a192bdf694) "
                  "-- the CURRENT LIVE market at this order's authoring time. No live market owns an Arizona "
                  "postal code; the only cross-market exposure is a shared chain or resort NAME, which rule G and "
                  "the bare-chain test guard."),
    ("san-diego-ca", "San Diego, live (deploy 6ab859787d349f8397e1450a) -- the nearest live market; shares chain "
                     "names ('Desert', 'Camelback', 'Mission Palms'-style resort names) but no postal code."),
])

#: A shared postal code whose OTHER town is refused. None in this market at authoring time: every admitted code's
#: towns are admitted together.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "phoenix,": "phoenix", "phoenix az": "phoenix", "phoenix, az": "phoenix", "phx": "phoenix",
    "scottsdale,": "scottsdale", "tempe,": "tempe", "mesa,": "mesa", "chandler,": "chandler",
    "gilbert,": "gilbert", "glendale,": "glendale", "peoria,": "peoria", "goodyear,": "goodyear",
    "avondale,": "avondale", "surprise,": "surprise", "paradise vly": "paradise valley",
    "paradise valley,": "paradise valley", "fountain hls": "fountain hills", "fountain hills,": "fountain hills",
    "litchfield pk": "litchfield park", "litchfield park,": "litchfield park", "apache jct": "apache junction",
    "apache junction,": "apache junction", "queen creek,": "queen creek", "cave creek,": "cave creek",
    "carefree,": "carefree", "buckeye,": "buckeye", "tolleson,": "tolleson", "fort mcdowell,": "fort mcdowell",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("85004", "Downtown / Convention Center / stadiums -- one postal code, never split."),
    ("85034", "PHX -- the airport owns its code; Sky Harbor Circle and Buckeye Road."),
    ("85281", "Tempe -- Mill Avenue, ASU and the University Drive 'Phoenix Airport' hotels share one code; Tempe's."),
    ("85254", "Kierland / Scottsdale Quarter -- mostly the City of Phoenix under a Scottsdale name; covered whole."),
    ("85253", "Paradise Valley -- the resort cluster, mostly under a Scottsdale postal city."),
    ("85226", "Chandler -- including Wild Horse Pass on the Gila River Indian Community."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Phoenix" % name),
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
            ("state_code", "AZ"),
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
        raise SystemExit("admitted postal codes outside the Valley prefixes: %s" % stray)

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius), ("state_code", "AZ"),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Phoenix / Scottsdale / Valley of the Sun city, airport, resort, spring-training and business "
                        "lodging market (PetTripFinder discovery scope)"),
        ("state", "AZ"),
        ("states", ["AZ"]),
        ("country", "US"),
        ("market_center", {"lat": 33.45, "lng": -112.07}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches north past Sedona, Prescott and Flagstaff and "
             "south-east past Tucson, so that " + WORK_ORDER + " classifies those properties on evidence instead of "
             "being blind to them. Admission is decided by the corridor registry over the property's OWN postal "
             "code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Phoenix / Scottsdale / the Valley of the Sun is ONE market: eleven CORE corridors (downtown, "
         "Midtown, Biltmore / Arcadia, PHX, Tempe, Old Town and Central Scottsdale, Paradise Valley, Mesa, Chandler, "
         "Glendale), eleven STRONG CORRIDORS (Scottsdale Airpark / Kierland, North Scottsdale, Desert Ridge, North "
         "Phoenix, West Phoenix, Ahwatukee, Gilbert, Peoria, Goodyear / Avondale, Surprise / Sun City, Fountain "
         "Hills) and four FRINGE corridors (Queen Creek, Apache Junction, Buckeye, Cave Creek / Carefree). SEDONA, "
         "FLAGSTAFF, the GRAND CANYON, PRESCOTT and TUCSON are refused as future standalone markets; Payson, Lake "
         "Havasu, Casa Grande, Wickenburg and the rest of Arizona are refused by name."),
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
        ("market_name", "Phoenix, Arizona"),
        ("market_slug", MARKET_ID),
        ("state_name", "Arizona"),
        ("state_code", "AZ"),
        ("primary_state_code", "AZ"),
        ("states", ["AZ"]),
        ("primary_city", "Phoenix"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Phoenix, Scottsdale & the Valley | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Phoenix, Scottsdale and the Valley of the Sun -- downtown Phoenix, "
         "Midtown, the Biltmore, Sky Harbor airport, Tempe, Old Town Scottsdale, Paradise Valley, Mesa, Chandler, "
         "Gilbert, Glendale and Peoria -- with real pet fees and policies read from each hotel's own official "
         "website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Phoenix"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry. A Phoenix / Scottsdale / Valley of the Sun city, airport, resort, "
         "spring-training and business travel market -- the contiguous Valley from Buckeye to Apache Junction and "
         "from Anthem and Cave Creek to Queen Creek. Not 'Arizona': Sedona, Flagstaff, the Grand Canyon, Prescott and "
         "Tucson are future standalone markets; Payson, Lake Havasu, Casa Grande and Wickenburg are refused. Nothing "
         "else admits a property: not a brand's 'Phoenix' or 'Scottsdale' marketing name, not a map pin, not a "
         "vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). The postal cities "
         "'PHOENIX' and 'SCOTTSDALE' each span several municipalities and place nothing by themselves. Shared codes "
         "are covered whole: 85004 by downtown, the Convention Center and the stadiums; 85281 by Tempe and its "
         "'Phoenix Airport' hotels; 85254 by Kierland and the City of Phoenix; 85253 by Paradise Valley's resorts "
         "under a Scottsdale postal city. The Convention Center, Westgate, Talking Stick, Kierland, Mayo Clinic and "
         "the spring-training ballparks are overlays."),
        ("_census_membership_note",
         "Individual condominium units, private villas and casitas sold by owners, vacation homes, property-management "
         "portfolios, Airbnb / Vrbo inventory, ordinary apartments, individual timeshare units, owner-only "
         "vacation-ownership resorts, residential-only towers, privately managed resort residences, member-only club "
         "lodging and government billeting are never admitted. A mixed hotel / condo / residence property is admitted "
         "only as the exact hotel premises its public operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 -- Phoenix / Scottsdale / Valley of the Sun travel-market geography, the Scottsdale "
                  "ruling, pet-travel / drive-market relevance and the resort / casita / condo / vacation-rental "
                  "safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/phoenix-az.json. This order "
         "does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its brand's own property card states it, "
         "joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG CORRIDOR is registry class CORRIDOR; FUTURE_STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes and by postal PREFIX for the "
                          "refused regions; the future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("scottsdale_ruling", SCOTTSDALE_RULING),
        ("valley_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("pet_travel_relevance",
         "Phoenix / Scottsdale was selected as a high-value pet-travel, road-trip and snowbird market. That lowers NO "
         "evidence standard: no destination reputation ('dog-friendly Scottsdale', the desert trails, a resort's "
         "marketing) is ever policy evidence. It shapes only the CENSUS: every trail-access (Camelback, Piestewa, "
         "South Mountain, the McDowell Sonoran Preserve, the Superstitions, Lake Pleasant), long-stay / extended-stay "
         "/ snowbird, resort, spring-training, airport-arrival and road-trip (I-10, I-17, US-60, Loop 101 / 202 / 303 "
         "exits) lodging cluster the traveller geography names is covered by an admitting cell and an overlay."),
        ("the_phoenix_name_trap",
         "The chains put 'Phoenix' on hotels from Buckeye to Mesa and 'Scottsdale' on hotels in Paradise Valley, "
         "Phoenix's Kierland and Desert Ridge and the Salt River community; 'Phoenix Airport' spans Phoenix 85034 / "
         "85008 / 85040 and Tempe 85281 / 85282; 'Chandler' resorts stand on the Gila River Indian Community. A "
         "property's own postal code, street and brand property code decide what and where it is; none of those "
         "words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Phoenix Sky Harbor International Airport (PHX)",
             "its own corridor phx-sky-harbor (85034 / 85008 / 85040); overlay on tempe's University / Priest rows."),
            ("Phoenix-Mesa Gateway Airport (AZA)", "mesa (85212) -- overlay."),
            ("Phoenix Convention Center / Chase Field / Footprint Center", "downtown-phoenix (85004 / 85003) -- "
                                                                          "overlays."),
            ("Arizona State University", "tempe (85287 / 85281) -- overlay."),
            ("State Farm Stadium / Westgate / Desert Diamond Arena", "glendale (85305) -- overlay."),
            ("Mayo Clinic Hospital", "desert-ridge-mayo (85054) -- overlay."),
            ("Spring training (Cactus League)", "overlays of mesa, old-town-scottsdale, central-scottsdale, tempe, "
                                                "glendale, peoria, surprise-sun-city and goodyear-avondale-litchfield."),
            ("TPC Scottsdale / the Phoenix Open", "north-scottsdale (85255) -- overlay."),
            ("Phoenix Raceway", "goodyear-avondale-litchfield (85323 / 85392) -- overlay."),
            ("Camelback / Piestewa / South Mountain / McDowell Sonoran / Superstition trailheads",
             "biltmore-camelback-arcadia, north-phoenix-deer-valley, ahwatukee-south-mountain, north-scottsdale and "
             "apache-junction-gold-canyon -- overlays."),
        ])),
        ("evaluated_inclusions", EVALUATED_INCLUSIONS),
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
        ("first_arizona_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, resort, spring-training or "
         "stadium keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration "
         "order publishes it."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, public resorts (including resort casitas the public operator sells "
         "nightly), qualifying condo-hotels with a distinct public hotel operation, qualifying extended-stay hotels "
         "and other public lodging establishments: bookable nightly rooms or suites sold to the public under one "
         "establishment name, with an official property page and an on-site hotel operation. It NEVER admits: "
         "individual condominium units; vacation homes, casitas or villas sold by owners or managers; "
         "property-management / short-term-rental portfolios; Airbnb / Vrbo listings; ordinary apartments; individual "
         "timeshare units or owner-only vacation-ownership resorts; residential-only towers; privately managed resort "
         "residences; member-only club lodging; government billeting; and privately managed units inside hotel-condo "
         "towers. Campgrounds, RV parks and hostels are NON_LODGING."),
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
    if z.startswith(VALLEY_PREFIXES):
        return "OUTSIDE", None, "Valley postal code %r is claimed by no corridor" % z
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
