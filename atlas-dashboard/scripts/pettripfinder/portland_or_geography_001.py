"""PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5 and 6: the Portland / Greater Portland market.

Built from zero on the CURRENT hardened lineage: the Seattle-live release 0e2e8bb8 (live lineage commit f0003e78,
built_from 438348c7). Current verified live at authoring time = seattle-wa deploy 6ac169ef7c75c383eb79f824, 40
markets / 3,669 profiles / 4,044 release-index routes / 4,117 served routes, host verified (release_index live-source
--fetch --verify-host). No earlier Portland build exists. It is the FIRST Oregon market: no live market admits an
Oregon postal code, and the build refuses to admit any code a registered market already admits (seattle-wa's 980 /
981 codes among them).

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Portland / Greater Portland traveller lodging market -- not the municipal City of Portland, and not
"Northwest Oregon" or "Southwest Washington" -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with
FUTURE_STANDALONE markets named inside OUTSIDE) before a single hotel is admitted, so no property is admitted or
refused after the fact to make a number. The order's "STRONG_CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property card)
states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP
is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing
name never admits and never places a property.

THE OREGON-SIDE TEST: THE METRO URBAN GROWTH BOUNDARY
----------------------------------------------------
Oregon draws one regional urban growth boundary around the Portland metro (Metro's UGB, ORS 268 / 197). Inside it:
Portland, Beaverton, Hillsboro, Tigard, Lake Oswego, Gresham, Tualatin, Wilsonville, Happy Valley, Troutdale,
Fairview, Wood Village, Milwaukie, Gladstone, Oregon City, West Linn, Sherwood, Forest Grove, Cornelius, King City
and Durham. Outside it: Canby, Sandy, Estacada, Newberg and the Yamhill wine towns, Scappoose and St Helens, and
everything beyond. The UGB is the mechanical, published line where metro continuity stops on the Oregon side, so it
is the line this registry uses: every UGB city is claimed by a corridor (CORE, CORRIDOR or FRINGE by the order's own
evaluation tiers) and no non-UGB town is.

WHY "PORTLAND" DECIDES NOTHING HERE (PHASE 5 -- AIRPORT / SUBURBAN IDENTITY)
---------------------------------------------------------------------------
The chains put "Portland" on hotels in Beaverton, Hillsboro, Tigard, Lake Oswego, Clackamas, Gresham, Troutdale,
Wilsonville, Vancouver (Washington) and even Hood River: "Portland Airport" on NE Airport Way / Cascade Station
hotels, "Portland/Beaverton", "Portland/Hillsboro", "Portland/Tigard", "Portland Lake Oswego", "Portland/Clackamas",
"Portland East/Troutdale", "Portland/Gresham", "Portland/Vancouver" and "Portland North". A property's own street and
postal code place it; its name never does -- a Troutdale hotel titled "Portland East" is a Troutdale hotel, and a
Vancouver hotel titled "Portland/Vancouver" is a WASHINGTON hotel placed by its own Washington code and stated as
Vancouver, WA.

THE VANCOUVER, WASHINGTON BOUNDARY (PHASE 3)
-------------------------------------------
Vancouver is evaluated, not assumed. See VANCOUVER_EVALUATION below for the eight-factor test the order names. The
ruling: the City of Vancouver and its contiguous urban unincorporated area (Hazel Dell, Orchards, Salmon Creek,
Cascade Park) is an IN-MARKET CORRIDOR (registry class CORRIDOR) whose rows KEEP their Washington identity -- city
"Vancouver", state "WA", their own 986 postal code. Camas, Washougal, Battle Ground, Ridgefield, La Center, Woodland
and the rest of Clark / Cowlitz / Skamania counties are OUTSIDE. No Vancouver row is ever rewritten as a Portland,
Oregon hotel; the census states the state the property's own page states.

THE COLUMBIA GORGE / MOUNT HOOD BOUNDARY (PHASE 4)
-------------------------------------------------
Troutdale and Fairview (the Gorge's western threshold, metro-continuous on I-84 inside the UGB) are admitted as a
STRONG corridor. Corbett / Multnomah Falls, Cascade Locks, Hood River, The Dalles, Stevenson (Skamania Lodge), White
Salmon and Washougal-east are the COLUMBIA GORGE destination market; Sandy, Welches, Rhododendron, Zigzag, Government
Camp and Timberline are the MOUNT HOOD resort market. Both are refused by name and postal code and preserved as
future standalone markets. A hotel marketed "Portland East", "Gateway to the Gorge" or "Gateway to Mount Hood" is
placed by its own code.

RESIDENCE / APARTMENT / VACATION-RENTAL SAFETY (PHASE 6)
-------------------------------------------------------
Qualifying public hotels are admitted on their own pages. Individual condo units, private residences, Airbnb /
Vrbo units, ordinary apartments, corporate-housing and property-management portfolios, serviced-apartment and
aparthotel operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Lark, Barsala, Zeus, Furnished Finder,
Oakwood / corporate housing, Society, Stay Alfred) and timeshare / vacation-club inventory (WorldMark, Club Wyndham,
Hilton Grand Vacations, Marriott Vacation Club, Holiday Inn Club Vacations, Bluegreen, Shell Vacations) are never
admitted, even when they accept short stays; a mixed property is admitted only as the exact hotel premises its
public operator sells. Patient and charitable housing (Ronald McDonald House, the OHSU / Doernbecher family housing,
Fisher House, Hope Lodge) is never public lodging. Phoenix's lesson is carried as a RULE: a vacation-club resort is
TIMESHARE even when its brand lists it beside its hotels and even when a pet-policy page exists.

MILITARY / GOVERNMENT LODGING
-----------------------------
No military installation owns an admitted postal code (the Portland Air National Guard Base at PDX sells no public
lodging and owns no lodging code). The on-base names are still refused wherever they appear (NONPUBLIC_NAMES).

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/portland_or.json
  launch_packages/pettripfinder/markets/proposed/portland-or.json
  launch_packages/pettripfinder/markets/reports/portland_or_geography_001.json
  launch_packages/pettripfinder/markets/reports/portland_or_corridor_registry_001.json
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

WORK_ORDER = "PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001"
MARKET_ID = "portland-or"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "portland_or.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "portland-or.json")
REPORT_OUT = os.path.join(REPORTS, "portland_or_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "portland_or_corridor_registry_001.json")
#: Every REGISTERED market's own document: no postal code any of them admits may be admitted here.
REGISTERED_MARKETS_GLOB = os.path.join(PKG, "markets", "*.json")
AS_OF = "2026-10-03"
#: The PRIMARY state. The market spans two (Vancouver is Washington); every row keeps its own state.
STATE_CODE = "OR"
STATE_CODES = ("OR", "WA")


def state_for_postal(postal):
    """The state a postal code belongs to: Oregon 970-979, Washington 980-994. A row's own page still decides;
    this is the fallback when a lane states no state of its own."""
    z = (postal or "").strip()[:3]
    if z.startswith("97"):
        return "OR"
    if z.startswith(("98", "99")):
        return "WA"
    return ""


#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description, state)
#: The order's REQUIRED evaluation areas are CORE, its STRONG evaluation areas are CORRIDOR and its CAREFUL
#: evaluation areas are FRINGE (or covered whole inside a CORE code they share).
CORRIDORS = [
    # ---------------------------------------------------------------- CORE (City of Portland)
    ("downtown-portland", "Downtown Portland", "Downtown / Portland State University / Goose Hollow / Cultural "
     "District / RiverPlace / Pioneer Courthouse Square", "CORE", "portland", ["97201", "97204", "97205", "97258"],
     "Downtown Portland's central business district and retail core (97204: Pioneer Courthouse Square, the "
     "transit mall, the downtown hotel row on SW Broadway / SW 6th / SW Morrison), the west side of downtown, the "
     "Cultural District and Goose Hollow / Providence Park (97205), Portland State University, the South "
     "Auditorium district and RiverPlace on the Willamette (97201), and the single-building downtown code 97258. "
     "Pioneer Courthouse Square, Providence Park and RiverPlace are OVERLAYS, never split codes.", "OR"),
    ("pearl-old-town-northwest", "Pearl District, Old Town & Northwest", "Pearl District / Old Town / Chinatown / "
     "Union Station / Nob Hill / Northwest 23rd / Slabtown / Forest Park", "CORE", "portland",
     ["97209", "97210", "97231"],
     "The Pearl District, Old Town / Chinatown, Union Station and the north end of downtown -- all one postal code, "
     "97209, never split -- with Northwest Portland, Nob Hill, NW 21st / 23rd, Slabtown and Forest Park (97210) and "
     "Linnton / Sauvie Island (97231). Pearl and Old Town / Chinatown are reported as OVERLAYS of this corridor.",
     "OR"),
    ("south-waterfront-southwest", "South Waterfront & Southwest Portland", "South Waterfront / OHSU / Lair Hill / "
     "Corbett / Hillsdale / Multnomah Village / Burlingame / Sylvan", "CORE", "portland",
     ["97239", "97219", "97221"],
     "South Waterfront, the OHSU campus and aerial tram, Lair Hill and Corbett (97239) -- medical and university "
     "demand -- with Hillsdale, Multnomah Village, Burlingame and the I-5 / Barbur Boulevard side of Southwest "
     "Portland (97219) and Sylvan / the West Hills on US-26 (97221).", "OR"),
    ("lloyd-convention-center", "Lloyd District & Convention Center", "Lloyd District / Oregon Convention Center / "
     "Moda Center / Rose Quarter / Lloyd Center / Eliot / Holladay Park", "CORE", "portland", ["97232", "97227"],
     "The Oregon Convention Center (777 NE Martin Luther King Jr Blvd), the Lloyd District hotel cluster and Lloyd "
     "Center (97232), and the Rose Quarter, Moda Center, Veterans Memorial Coliseum and Eliot / lower Albina "
     "(97227). The Convention Center and the Rose Quarter are OVERLAYS.", "OR"),
    ("central-eastside", "Central Eastside, Hawthorne & Sellwood", "Central Eastside Industrial District / Buckman / "
     "Hawthorne / Belmont / Division / Mount Tabor / Brooklyn / Sellwood-Moreland / Woodstock", "CORE", "portland",
     ["97214", "97202", "97215"],
     "The Central Eastside across the Willamette from downtown -- the inner-east boutique-hotel district, Buckman, "
     "Hawthorne, Belmont and Division (97214) -- with Brooklyn, Sellwood-Moreland, Eastmoreland, Woodstock and Reed "
     "(97202) and Mount Tabor / Sunnyside (97215).", "OR"),
    ("pdx-airport", "PDX Airport & Cascade Station", "Portland International Airport / NE Airport Way / Cascade "
     "Station / NE 82nd Ave / Columbia Blvd / Parkrose", "CORE", "portland", ["97220", "97218", "97230"],
     "Portland International Airport's own lodging system: the NE Airport Way / NE 82nd Avenue hotel row and "
     "Cascade Station beside the terminal (97220), Columbia Boulevard and Cully west of the airport (97218), and "
     "Parkrose / the NE Airport Way east side toward I-205 and 122nd Avenue (97230). PDX and Cascade Station are "
     "reported as OVERLAYS. A hotel marketed 'Portland Airport' whose own code is elsewhere (Vancouver, Gresham) is "
     "placed by that code.", "OR"),
    ("northeast-north-portland", "Northeast & North Portland", "Alberta / Irvington / Hollywood / Interstate Ave / "
     "Kenton / Delta Park / Hayden Island / Jantzen Beach / St Johns", "CORE", "portland",
     ["97211", "97212", "97213", "97217", "97203"],
     "Northeast Portland -- Alberta / King / Woodlawn (97211), Irvington / Alameda / Grant Park (97212) and "
     "Hollywood / Rose City Park (97213) -- with North Portland's Interstate Avenue motel corridor, Kenton, Delta "
     "Park, the Portland Expo Center and Hayden Island / Jantzen Beach at the I-5 bridge (97217), and St Johns / the "
     "University of Portland (97203).", "OR"),
    ("southeast-east-portland", "Southeast & East Portland", "Foster-Powell / Lents / SE 82nd Ave / Gateway / Mall "
     "205 / Montavilla / Powell Butte", "CORE", "portland", ["97206", "97216", "97266", "97236"],
     "Southeast and East Portland: Foster-Powell and Woodstock east (97206), Gateway, Mall 205 and the I-84 / "
     "I-205 interchange (97216), Lents and the SE 82nd Avenue motel corridor (97266) and Powell Butte / Pleasant "
     "Valley (97236). Inside the municipal market; never left unclaimed.", "OR"),
    # ---------------------------------------------------------------- CORE (Washington County / suburbs, REQUIRED)
    ("beaverton", "Beaverton", "Beaverton / Nike WHQ / Cedar Hills / Raleigh Hills / Aloha / Murray Hill / Cedar "
     "Mill / Bethany / Tanasbourne south", "CORE", "beaverton",
     ["97005", "97006", "97007", "97008", "97003", "97078", "97225", "97229"],
     "The City of Beaverton -- downtown, Cedar Hills Crossing and the Canyon Road / Beaverton-Hillsdale Highway "
     "hotel row (97005), the Nike World Headquarters and Murray Hill side (97005 / 97008), south Beaverton and "
     "Progress (97007 / 97008) -- with the unincorporated Washington County urban area its postal codes carry: "
     "Aloha (97003 / 97006 / 97078), the Tanasbourne / Amberglen south side and the Sunset Corridor (97006, whose "
     "USPS preferred city is Beaverton, covered whole), Raleigh Hills / West Slope (97225) and Cedar Mill / "
     "Bethany (97229). A hotel titled 'Portland/Beaverton' or 'Hillsboro' at one of these codes is placed by its "
     "own code.", "OR"),
    ("hillsboro", "Hillsboro", "Hillsboro / Tanasbourne / Orenco / Intel Ronler Acres / Hillsboro Airport / "
     "downtown Hillsboro", "CORE", "hillsboro", ["97123", "97124"],
     "The City of Hillsboro: downtown, the Washington County Fair Complex and the TV Highway side (97123), and "
     "Tanasbourne, Orenco Station, Intel's Ronler Acres / Hawthorn Farm campuses, the Hillsboro Airport and the "
     "NE Shute Road / Evergreen Parkway hotel cluster (97124). A hotel titled 'Portland/Hillsboro' is placed by its "
     "own code.", "OR"),
    ("tigard", "Tigard & Washington Square", "Tigard / Washington Square / Lincoln Center / Kruse Way west / King "
     "City / Durham / Metzger / Garden Home", "CORE", "tigard", ["97223", "97224"],
     "The City of Tigard: Washington Square, Lincoln Center, the Highway 217 / SW 72nd Avenue hotel row and "
     "Metzger / Garden Home (97223), and south Tigard, King City and Durham (97224).", "OR"),
    ("lake-oswego", "Lake Oswego", "Lake Oswego / Kruse Way / downtown Lake Oswego / Lake Grove", "CORE",
     "lake oswego", ["97034", "97035"],
     "The City of Lake Oswego: downtown and the lake (97034) and Kruse Way's office-park hotels and Lake Grove on "
     "I-5 (97035). A hotel titled 'Portland Lake Oswego' is placed by its own code.", "OR"),
    ("gresham", "Gresham", "Gresham / downtown Gresham / Rockwood / Gresham Station / Mount Hood Community College",
     "CORE", "gresham", ["97030", "97080", "97233"],
     "The City of Gresham: downtown, Gresham Station and the Burnside / Division corridor (97030), south Gresham "
     "(97080) and Rockwood on the Portland / Gresham line (97233, covered whole). A hotel titled 'Portland/Gresham' "
     "or 'Gateway to Mount Hood' is placed by its own code.", "OR"),
    # ---------------------------------------------------------------- STRONG CORRIDOR
    ("tualatin-wilsonville", "Tualatin & Wilsonville", "Tualatin / Bridgeport Village / I-5 at Nyberg Road / "
     "Wilsonville / Town Center Loop / I-5 at Wilsonville Road", "CORRIDOR", "tualatin", ["97062", "97070"],
     "The City of Tualatin -- Bridgeport Village and the I-5 / Nyberg Road hotel cluster (97062) -- and the City of "
     "Wilsonville at the south end of the Metro urban growth boundary on I-5 (97070). STRONG.", "OR"),
    ("clackamas-happy-valley", "Clackamas & Happy Valley", "Clackamas Town Center / I-205 at Sunnyside Road / "
     "Happy Valley / Sunnyside / Damascus", "CORRIDOR", "clackamas", ["97015", "97086", "97089"],
     "Clackamas Town Center and the I-205 / Sunnyside Road / SE 82nd Avenue hotel cluster (97015), the City of "
     "Happy Valley (97086) and Damascus (97089). STRONG.", "OR"),
    ("troutdale-fairview", "Troutdale & Fairview", "Troutdale / Columbia Gorge Outlets / I-84 exit 16-17 / Wood "
     "Village / Fairview", "CORRIDOR", "troutdale", ["97060", "97024"],
     "The City of Troutdale, Wood Village and the I-84 exit-16 / exit-17 hotel cluster at the Gorge's western "
     "threshold (97060), and Fairview (97024) -- metro-continuous on I-84 inside the urban growth boundary. "
     "STRONG. Corbett, Multnomah Falls and the Gorge beyond are refused; a hotel marketed 'Portland East' or "
     "'Gateway to the Gorge' here is a Troutdale hotel.", "OR"),
    ("vancouver-wa", "Vancouver, Washington", "Downtown Vancouver / Vancouver Waterfront / Esther Short Park / "
     "Hazel Dell / Orchards / Vancouver Mall / Cascade Park / Salmon Creek / SR-14", "CORRIDOR", "vancouver",
     ["98660", "98661", "98662", "98663", "98664", "98665", "98682", "98683", "98684", "98685", "98686"],
     "The City of Vancouver, WASHINGTON and its contiguous urban unincorporated area across the I-5 Interstate "
     "Bridge and the I-205 Glenn Jackson Bridge: downtown Vancouver, the Waterfront and Esther Short Park (98660), "
     "the Vancouver Mall / Andresen / Fourth Plain hotels (98661 / 98662), the Uptown / Hough side (98663), the "
     "SR-14 / Columbia Shores / Fort Vancouver side (98664), Hazel Dell (98665), Orchards (98682), Cascade Park / "
     "the I-205 / SR-14 hotel cluster (98683 / 98684) and Salmon Creek (98685 / 98686). IN-MARKET CORRIDOR after "
     "the eight-factor evaluation in VANCOUVER_EVALUATION. Every row keeps its own WASHINGTON identity (city "
     "Vancouver, state WA, its own 986 code); none is ever stated as Portland, Oregon.", "WA"),
    # ---------------------------------------------------------------- FRINGE (CAREFUL evaluation)
    ("milwaukie", "Milwaukie", "Milwaukie / Oak Grove / McLoughlin Blvd / Highway 224", "FRINGE", "milwaukie",
     ["97222", "97267"],
     "The City of Milwaukie and Oak Grove on McLoughlin Boulevard (97222 / 97267), metro-continuous with Sellwood "
     "and Clackamas inside the urban growth boundary. Admitted at FRINGE after CAREFUL evaluation so its small "
     "inventory is ACCOUNTED FOR.", "OR"),
    ("oregon-city-west-linn", "Oregon City, West Linn & Gladstone", "Oregon City / End of the Oregon Trail / I-205 "
     "at Highway 213 / West Linn / Gladstone", "FRINGE", "oregon city", ["97045", "97068", "97027"],
     "The City of Oregon City (97045), West Linn across the Willamette (97068) and Gladstone (97027) on I-205 at "
     "the south-east edge of the urban growth boundary. Admitted at FRINGE after CAREFUL evaluation.", "OR"),
    ("sherwood", "Sherwood", "Sherwood / Highway 99W", "FRINGE", "sherwood", ["97140"],
     "The City of Sherwood on Highway 99W at the south-west edge of the urban growth boundary (97140). Admitted at "
     "FRINGE after CAREFUL evaluation. Newberg and the Yamhill wine towns beyond it on 99W are refused.", "OR"),
    ("forest-grove-cornelius", "Forest Grove & Cornelius", "Forest Grove / Pacific University / Cornelius / TV "
     "Highway west", "FRINGE", "forest grove", ["97116", "97113"],
     "The City of Forest Grove -- Pacific University and the McMenamins Grand Lodge -- and Cornelius (97116 / "
     "97113), the western end of the urban growth boundary on TV Highway past Hillsboro. Admitted at FRINGE after "
     "CAREFUL evaluation; Gaston, Banks and the Coast Range beyond are refused.", "OR"),
]

OUTSIDE = [
    ("Salem / Keizer / Woodburn / the mid-Willamette Valley", "OR",
     ["97071", "97002", "97032", "97026", "97137", "97362"],
     "MARION / POLK COUNTY; FUTURE_STANDALONE salem-or. The state capital 45 miles south on I-5, its own bureau "
     "(Travel Salem). Refused by name and by postal PREFIX (973); Woodburn (the outlet mall, 97071), Aurora, "
     "Hubbard, Gervais, St Paul and Mount Angel named here."),
    ("Eugene / Springfield", "OR", [],
     "LANE COUNTY; FUTURE_STANDALONE eugene-or. 110 miles south. Refused by postal PREFIX (974)."),
    ("Columbia River Gorge -- Corbett / Multnomah Falls, Cascade Locks, Hood River, Mosier, The Dalles, and the "
     "Washington shore: Stevenson / Skamania Lodge, Carson, North Bonneville, White Salmon, Bingen, Washougal", "--",
     ["97019", "97014", "97031", "97040", "97058", "98648", "98610", "98639", "98672", "98605", "98671"],
     "FUTURE_STANDALONE columbia-gorge. The Gorge National Scenic Area is a destination a Portland traveller drives "
     "TO (Multnomah Falls, Hood River's wind-sport and orchard tourism, Skamania Lodge). Refused by name and postal "
     "code on both shores. Washougal (98671) is the Washington Gorge portal on SR-14. A hotel marketed 'Gateway to "
     "the Gorge' or 'Hood River / Portland' at one of these codes is refused by its own address."),
    ("Mount Hood -- Sandy, Boring, Brightwood, Welches, Zigzag, Rhododendron, Government Camp, Timberline, "
     "Parkdale", "OR", ["97055", "97009", "97011", "97067", "97049", "97028", "97041"],
     "CLACKAMAS COUNTY (east) / HOOD RIVER COUNTY; FUTURE_STANDALONE mount-hood. The Mount Hood resort and ski "
     "inventory (Timberline Lodge, Mt. Hood Oregon Resort, the Government Camp lodges) on US-26 beyond the urban "
     "growth boundary. Sandy is outside the UGB and is the mountain gateway. Refused by name and postal code."),
    ("Oregon Coast -- Astoria, Warrenton, Hammond, Gearhart, Seaside, Cannon Beach, Arch Cape, Manzanita, "
     "Nehalem, Wheeler, Rockaway Beach, Garibaldi, Tillamook, Oceanside, Pacific City, Neskowin, Lincoln City, "
     "Depoe Bay, Newport, Yachats", "OR",
     ["97103", "97146", "97121", "97138", "97110", "97102", "97130", "97131", "97147", "97136", "97118", "97141",
      "97134", "97135", "97149", "97107", "97112", "97143", "97367", "97341", "97388", "97365", "97366", "97498",
      "97368", "97364"],
     "CLATSOP / TILLAMOOK / LINCOLN COUNTY; FUTURE_STANDALONE oregon-coast. The coast is its own destination 75-90 "
     "miles west over the Coast Range. Refused by name and postal code (and by prefix 973 / 974 for the central "
     "and south coast)."),
    ("Bend / Central Oregon", "OR", [],
     "DESCHUTES COUNTY; FUTURE_STANDALONE bend-or. Refused by postal PREFIX (977)."),
    ("Yamhill County wine country -- Newberg, Dundee, Dayton, Lafayette, Carlton, Yamhill, McMinnville, Amity, "
     "Sheridan, Willamina, Grand Ronde", "OR",
     ["97132", "97115", "97114", "97127", "97111", "97148", "97128", "97101", "97378", "97396", "97347"],
     "YAMHILL / POLK COUNTY; refused after CAREFUL evaluation (outside the Metro UGB). The Willamette Valley wine "
     "destination on Highway 99W / 18 (and Spirit Mountain at Grand Ronde) -- a market a traveller drives TO, "
     "preserved for a future willamette-valley market."),
    ("Outer Clackamas County -- Canby, Estacada, Molalla, Mulino, Beavercreek, Eagle Creek, Colton, Barlow, "
     "Marquam", "OR", ["97013", "97023", "97038", "97042", "97004", "97022", "97017"],
     "CLACKAMAS COUNTY outside the urban growth boundary; refused after CAREFUL evaluation."),
    ("Outer Washington County -- North Plains, Banks, Gaston, Manning, Timber, Gales Creek, Buxton", "OR",
     ["97133", "97106", "97119", "97125", "97144", "97109"],
     "WASHINGTON COUNTY outside the urban growth boundary (the Coast Range and US-26 west); refused after "
     "CAREFUL evaluation."),
    ("Columbia County -- Scappoose, St Helens, Warren, Columbia City, Rainier, Clatskanie, Vernonia", "OR",
     ["97056", "97051", "97053", "97018", "97048", "97016", "97064"],
     "COLUMBIA COUNTY on US-30, outside the urban growth boundary; refused after CAREFUL evaluation."),
    ("Outer Clark County, Washington -- Camas, Battle Ground, Brush Prairie, Ridgefield, La Center, Yacolt, Amboy, "
     "Woodland", "WA", ["98607", "98604", "98606", "98642", "98629", "98675", "98601", "98674"],
     "CLARK / COWLITZ COUNTY outside the Vancouver urban area; refused after CAREFUL evaluation. Camas is its own "
     "SR-14 mill town at the Gorge approach (Washougal beyond it is the Gorge portal); Battle Ground, Ridgefield "
     "(the ilani casino resort at La Center) and Woodland are north-county towns. Recorded, never silently "
     "absorbed. A founder may move Camas on the record."),
    ("Longview / Kelso / Kalama / Castle Rock", "WA", ["98632", "98626", "98625", "98611"],
     "COWLITZ COUNTY; FUTURE_STANDALONE longview-kelso. 45 miles north on I-5."),
    ("Olympia / Thurston County", "WA", [],
     "FUTURE_STANDALONE olympia-wa. Refused by postal PREFIX (985)."),
    ("Tacoma / Pierce County", "WA", [],
     "FUTURE_STANDALONE tacoma-wa. Refused by postal PREFIX (984)."),
    ("Seattle / King and south Snohomish counties -- the LIVE seattle-wa market", "WA", [],
     "EXISTING LIVE seattle-wa. Refused by postal PREFIX (980 / 981); a registered market already owns those codes."),
    ("Central / Eastern / Southern Oregon, the rest of Washington and out of state", "--", [],
     "Every other Oregon postal prefix (975 Medford, 976 Klamath Falls, 978 Pendleton, 979 Ontario), every other "
     "Washington prefix (982 / 983 / 988-994) and every non-Pacific-Northwest code is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("973", "Salem / mid-Willamette Valley / central Oregon Coast", "salem-or"),
    ("974", "Eugene / Springfield / south Willamette Valley / south-central coast", "eugene-or"),
    ("975", "Medford / Rogue Valley / south coast", ""),
    ("976", "Klamath Falls / south-central Oregon", ""),
    ("977", "Bend / Central Oregon", "bend-or"),
    ("978", "Pendleton / north-east Oregon", ""),
    ("979", "Ontario / eastern Oregon", ""),
    ("980", "Seattle / King and south Snohomish (LIVE seattle-wa)", "seattle-wa"),
    ("981", "Seattle (LIVE seattle-wa)", "seattle-wa"),
    ("982", "Everett / north Snohomish, Skagit, Whatcom, Island and San Juan counties", ""),
    ("983", "Pierce / Kitsap / the Olympic Peninsula", ""),
    ("984", "Tacoma / Pierce County", "tacoma-wa"),
    ("985", "Olympia / Thurston, Lewis, Grays Harbor and Mason counties", "olympia-wa"),
    ("988", "Wenatchee / north-central Washington", ""),
    ("989", "Yakima / central Washington", ""),
    ("990", "Spokane region", ""), ("991", "Spokane region", ""), ("992", "Spokane", ""),
    ("993", "Tri-Cities / Walla Walla", ""), ("994", "Clarkston / south-east Washington", ""),
]

#: Portland's own postal prefixes (and Vancouver's). A code under one of these that no corridor claims and no OUTSIDE
#: row names is an UNCLAIMED north-west Oregon / south-west Washington code -- refused, and named in the boundary
#: audit so it is visible, never silently dropped.
VALLEY_PREFIXES = ("970", "971", "972", "986")

ADMITTED_COUNTIES = {"multnomah (portland, gresham, troutdale, fairview, wood village)",
                     "washington (beaverton, hillsboro, tigard, tualatin north, sherwood, forest grove, cornelius, "
                     "the unincorporated urban area; the area outside the UGB refused)",
                     "clackamas (lake oswego, milwaukie, oak grove, clackamas, happy valley, damascus, gladstone, "
                     "oregon city, west linn, wilsonville; the area outside the UGB and mount hood refused)",
                     "clark, washington (the city of vancouver and its contiguous urban unincorporated area; camas, "
                     "washougal, battle ground, ridgefield, la center refused)"}
OBSERVED_COUNTIES = OrderedDict([
    ("marion / polk (salem, keizer, woodburn)", "salem-or"),
    ("lane (eugene, springfield)", "eugene-or"),
    ("hood river / wasco / skamania / klickitat (the columbia gorge)", "columbia-gorge"),
    ("clackamas east / hood river south (sandy, welches, government camp, timberline)", "mount-hood"),
    ("clatsop / tillamook / lincoln (the oregon coast)", "oregon-coast"),
    ("deschutes (bend)", "bend-or"),
    ("yamhill (newberg, dundee, mcminnville)", "(none -- refused after careful evaluation)"),
    ("columbia (scappoose, st helens)", "(none -- refused after careful evaluation)"),
    ("clark outer / cowlitz (camas, battle ground, ridgefield, woodland, longview, kelso)",
     "longview-kelso (cowlitz); clark outer refused after careful evaluation"),
    ("thurston (olympia)", "olympia-wa"),
    ("pierce (tacoma)", "tacoma-wa"),
    ("king / snohomish (seattle)", "seattle-wa (LIVE)"),
])

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("multnomah", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. The City of Portland, Gresham, Troutdale, Fairview and Wood Village are "
                   "admitted; Corbett / Multnomah Falls, Bridal Veil and the Gorge east of Troutdale are REFUSED "
                   "(FUTURE_STANDALONE columbia-gorge). County inclusion is not traveller-market inclusion."),
    ])),
    ("washington", OrderedDict([
        ("ruling", "ADMITTED INSIDE THE URBAN GROWTH BOUNDARY. Beaverton, Hillsboro, Tigard, Tualatin's north side, "
                   "King City, Durham, Sherwood, Forest Grove, Cornelius and the unincorporated urban area (Aloha, "
                   "Cedar Mill, Bethany, Raleigh Hills, Metzger) are admitted; North Plains, Banks, Gaston and the "
                   "Coast Range are refused."),
    ])),
    ("clackamas", OrderedDict([
        ("ruling", "ADMITTED INSIDE THE URBAN GROWTH BOUNDARY. Lake Oswego, Milwaukie, Oak Grove, Clackamas, Happy "
                   "Valley, Damascus, Gladstone, Oregon City, West Linn and Wilsonville are admitted; Canby, Sandy, "
                   "Estacada, Molalla and the Mount Hood corridor are refused (FUTURE_STANDALONE mount-hood)."),
    ])),
    ("clark (washington)", OrderedDict([
        ("ruling", "ADMITTED ONLY AS THE VANCOUVER URBAN CORRIDOR, WITH ITS WASHINGTON IDENTITY. The City of Vancouver "
                   "and its contiguous unincorporated urban area (Hazel Dell, Orchards, Salmon Creek, Cascade Park) "
                   "are admitted as the vancouver-wa corridor; every row is stated as Vancouver, WA. Camas, "
                   "Washougal, Battle Ground, Ridgefield, La Center and the north county are refused."),
    ])),
    ("yamhill / columbia / marion / polk", OrderedDict([
        ("ruling", "REFUSED. Newberg and the wine towns, Scappoose and St Helens, Woodburn and Salem are outside "
                   "the urban growth boundary. Portland does not absorb north-west Oregon."),
    ])),
    ("hood river / wasco / skamania / clatsop / tillamook / lincoln / deschutes", OrderedDict([
        ("ruling", "REFUSED. The Columbia Gorge, Mount Hood, the Oregon Coast and Bend are destination markets of "
                   "their own (FUTURE_STANDALONE columbia-gorge, mount-hood, oregon-coast, bend-or)."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / patient / member
#: only). A normalised-name substring match; the census row keeps its reason.
NONPUBLIC_NAMES = {
    "navy lodge": "Navy Lodge on-base lodging -- MILITARY_RESTRICTED",
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- restricted to authorised DoD travellers; MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "air national guard": "Air National Guard base lodging -- MILITARY_RESTRICTED",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "hope lodge": "American Cancer Society Hope Lodge -- patient lodging, not public lodging",
    "doernbecher family": "OHSU Doernbecher family housing -- patient-family lodging, not public lodging",
    "ohsu family housing": "OHSU patient-family housing -- not public lodging",
    "rosewood guest house": "patient-family guest housing -- not public lodging",
}

#: Military postal codes inside the admitted partition. NONE: no installation sells lodging in an admitted code.
MILITARY_POSTAL_CODES = OrderedDict()

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-portland", "Portland", "Downtown / PSU / Goose Hollow / RiverPlace", 45.5180, -122.6800, 1800, True),
    ("pearl-old-town-northwest", "Portland", "Pearl / Old Town / Chinatown / Northwest", 45.5300, -122.6900, 2500,
     True),
    ("south-waterfront-southwest", "Portland", "South Waterfront / OHSU / SW Portland", 45.4850, -122.6900, 4000,
     True),
    ("lloyd-convention-center", "Portland", "Lloyd District / Convention Center / Rose Quarter", 45.5320,
     -122.6580, 1800, True),
    ("central-eastside", "Portland", "Central Eastside / Hawthorne / Sellwood", 45.4950, -122.6450, 3500, True),
    ("pdx-airport", "Portland", "PDX / NE Airport Way / Cascade Station / Parkrose", 45.5650, -122.5700, 5000, True),
    ("northeast-north-portland", "Portland", "NE Portland / Interstate Ave / Hayden Island / St Johns", 45.5750,
     -122.6700, 5500, True),
    ("southeast-east-portland", "Portland", "SE / East Portland / Gateway / Lents", 45.4900, -122.5650, 5000, True),
    ("beaverton", "Beaverton", "Beaverton / Aloha / Cedar Mill / Bethany", 45.5000, -122.8200, 7000, True),
    ("hillsboro", "Hillsboro", "Hillsboro / Tanasbourne / Orenco", 45.5300, -122.9300, 6000, True),
    ("tigard", "Tigard", "Tigard / Washington Square / King City", 45.4250, -122.7700, 4500, True),
    ("lake-oswego", "Lake Oswego", "Lake Oswego / Kruse Way", 45.4150, -122.7000, 4000, True),
    ("gresham", "Gresham", "Gresham / Rockwood", 45.5000, -122.4400, 5500, True),
    ("tualatin-wilsonville", "Tualatin", "Tualatin / Wilsonville", 45.3400, -122.7600, 7000, True),
    ("clackamas-happy-valley", "Clackamas", "Clackamas / Happy Valley / Damascus", 45.4300, -122.5300, 6000, True),
    ("troutdale-fairview", "Troutdale", "Troutdale / Wood Village / Fairview", 45.5380, -122.4000, 3500, True),
    ("vancouver-wa", "Vancouver", "Vancouver, WA / Hazel Dell / Orchards / Cascade Park / Salmon Creek", 45.6600,
     -122.5800, 9000, True),
    ("milwaukie", "Milwaukie", "Milwaukie / Oak Grove", 45.4300, -122.6250, 3500, True),
    ("oregon-city-west-linn", "Oregon City", "Oregon City / West Linn / Gladstone", 45.3600, -122.6200, 5000, True),
    ("sherwood", "Sherwood", "Sherwood", 45.3550, -122.8400, 3000, True),
    ("forest-grove-cornelius", "Forest Grove", "Forest Grove / Cornelius", 45.5200, -123.0900, 4500, True),
    ("obs-salem", "Salem", "Salem / Keizer / Woodburn -- OBSERVATION ONLY", 45.0500, -122.9500, 22000, False),
    ("obs-gorge", "Hood River", "Columbia Gorge: Corbett / Cascade Locks / Hood River / Stevenson -- OBSERVATION "
     "ONLY", 45.6500, -121.8000, 30000, False),
    ("obs-mount-hood", "Government Camp", "Sandy / Welches / Government Camp -- OBSERVATION ONLY", 45.3300,
     -121.9500, 20000, False),
    ("obs-coast", "Seaside", "Astoria / Seaside / Cannon Beach / Tillamook -- OBSERVATION ONLY", 45.7500,
     -123.8500, 35000, False),
    ("obs-yamhill", "Newberg", "Newberg / Dundee / McMinnville -- OBSERVATION ONLY", 45.2600, -123.0700, 15000,
     False),
    ("obs-clark-outer", "Camas", "Camas / Washougal / Battle Ground / Ridgefield / La Center -- OBSERVATION ONLY",
     45.7600, -122.5300, 15000, False),
    ("obs-longview", "Longview", "Longview / Kelso / Kalama / Woodland -- OBSERVATION ONLY", 46.1300, -122.9300,
     15000, False),
    ("obs-columbia-county", "St Helens", "Scappoose / St Helens -- OBSERVATION ONLY", 45.8300, -122.8600, 10000,
     False),
]

#: The observation box. It reaches south past Salem, east through the Gorge to The Dalles and up Mount Hood, west
#: to the Oregon Coast and north past Longview / Kelso, so the census counts what it refuses.
BOUNDS = {"min_lat": 44.85, "max_lat": 46.25, "min_lng": -124.05, "max_lng": -121.10}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Pioneer Courthouse Square / Downtown core", 45.5190, -122.6790, 0.55),
    ("Portland State University / South Auditorium", 45.5110, -122.6840, 0.55),
    ("RiverPlace", 45.5080, -122.6735, 0.35),
    ("Goose Hollow / Providence Park", 45.5200, -122.6920, 0.55),
    ("Downtown Portland", 45.5170, -122.6800, 1.10),
    ("Pearl District", 45.5290, -122.6830, 0.60),
    ("Old Town / Chinatown", 45.5250, -122.6730, 0.45),
    ("Northwest Portland / Nob Hill", 45.5300, -122.6990, 1.20),
    ("South Waterfront / OHSU", 45.4990, -122.6720, 0.90),
    ("Southwest Portland", 45.4700, -122.7000, 3.00),
    ("Lloyd District / Convention Center", 45.5300, -122.6600, 0.90),
    ("Rose Quarter / Moda Center", 45.5320, -122.6670, 0.45),
    ("Central Eastside", 45.5150, -122.6580, 1.20),
    ("Hawthorne / Division / Belmont", 45.5100, -122.6300, 1.60),
    ("Sellwood / Brooklyn / Woodstock", 45.4750, -122.6400, 2.20),
    ("PDX Airport / Cascade Station", 45.5800, -122.5800, 2.60),
    ("Parkrose / NE Airport Way east", 45.5600, -122.5400, 2.00),
    ("Northeast Portland", 45.5550, -122.6400, 2.80),
    ("North Portland / Interstate Ave", 45.5700, -122.6800, 2.20),
    ("Hayden Island / Jantzen Beach", 45.6120, -122.6800, 1.40),
    ("Gateway / Mall 205", 45.5300, -122.5650, 1.60),
    ("Southeast / East Portland", 45.4850, -122.5800, 3.50),
    ("Beaverton", 45.4900, -122.8050, 3.50),
    ("Cedar Mill / Bethany", 45.5300, -122.8100, 3.00),
    ("Hillsboro (Tanasbourne / Orenco)", 45.5370, -122.8750, 2.50),
    ("Hillsboro (downtown / airport)", 45.5250, -122.9650, 3.00),
    ("Tigard / Washington Square", 45.4300, -122.7650, 3.00),
    ("Lake Oswego / Kruse Way", 45.4150, -122.7100, 3.00),
    ("Gresham", 45.5000, -122.4300, 4.00),
    ("Tualatin", 45.3850, -122.7600, 3.00),
    ("Wilsonville", 45.3000, -122.7700, 3.00),
    ("Clackamas / Happy Valley", 45.4300, -122.5500, 3.50),
    ("Troutdale / Fairview", 45.5350, -122.4000, 3.00),
    ("Downtown Vancouver, WA / Waterfront", 45.6280, -122.6720, 1.50),
    ("Vancouver, WA (east / Cascade Park / Mall)", 45.6300, -122.5300, 6.00),
    ("Vancouver, WA (Hazel Dell / Salmon Creek)", 45.7000, -122.6600, 5.00),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("PDX Airport / Cascade Station", re.compile(r"\bne airport way\b|\bcascades? pkwy\b|\bne mt\.? hood ave\b|"
                                                 r"\bne 82nd ave\b(?=.*97220)|\bne columbia blvd\b(?=.*972(18|20))",
                                                 re.I)),
    ("Lloyd District / Convention Center", re.compile(r"\bne multnomah st\b|\bne holladay st\b|\bne lloyd blvd\b|"
                                                      r"\bne (grand|mlk|martin luther king)\b.*97232|"
                                                      r"\bne (oregon|pacific|irving) st\b(?=.*97232)", re.I)),
    ("Hayden Island / Jantzen Beach", re.compile(r"\bhayden is(land)?\b|\bjantzen\b|\bn tomahawk\b", re.I)),
    ("North Portland / Interstate Ave", re.compile(r"\bn interstate ave\b|\bn denver ave\b", re.I)),
    ("Pearl District", re.compile(r"\bnw (9th|10th|11th|12th|13th|14th) ave\b(?=.*97209)|\bnw (glisan|hoyt|irving|"
                                  r"johnson|kearney|lovejoy|marshall|northrup) st\b(?=.*97209)", re.I)),
    ("Old Town / Chinatown", re.compile(r"\bnw (couch|davis|everett|flanders) st\b(?=.*97209)|\bnw (3rd|4th|5th|6th|"
                                        r"broadway)\b.*97209|\bsw (1st|2nd) ave\b(?=.*97204)|\bsw naito\b", re.I)),
    ("RiverPlace", re.compile(r"\bsw harbor way\b|\bsw montgomery st\b(?=.*97201)", re.I)),
    ("South Waterfront / OHSU", re.compile(r"\bsw (bond|moody|macadam|river) (ave|pkwy|pky)\b|\bsw gaines st\b|"
                                           r"\bsw lowell st\b", re.I)),
    ("Downtown Vancouver, WA / Waterfront", re.compile(r"\bwaterfront way\b|\besther st\b|\bcolumbia way\b|"
                                                       r"\b(c|w 6th|w 8th|w 9th) st\b(?=.*98660)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-portland": "Downtown Portland",
    "pearl-old-town-northwest": "Northwest Portland / Nob Hill",
    "south-waterfront-southwest": "Southwest Portland",
    "lloyd-convention-center": "Lloyd District / Convention Center",
    "central-eastside": "Central Eastside",
    "pdx-airport": "PDX Airport / Cascade Station",
    "northeast-north-portland": "Northeast Portland",
    "southeast-east-portland": "Southeast / East Portland",
    "beaverton": "Beaverton",
    "hillsboro": "Hillsboro (Tanasbourne / Orenco)",
    "tigard": "Tigard / Washington Square",
    "lake-oswego": "Lake Oswego / Kruse Way",
    "gresham": "Gresham",
    "tualatin-wilsonville": "Tualatin",
    "clackamas-happy-valley": "Clackamas / Happy Valley",
    "troutdale-fairview": "Troutdale / Fairview",
    "vancouver-wa": "Vancouver, WA (east / Cascade Park / Mall)",
    "milwaukie": "Milwaukie / Oak Grove",
    "oregon-city-west-linn": "Oregon City / West Linn",
    "sherwood": "Sherwood",
    "forest-grove-cornelius": "Forest Grove / Cornelius",
}

#: The order's REQUIRED / STRONG / CAREFUL / CROSS-RIVER / KEEP-SEPARATE evaluation list, each classified explicitly.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Portland", "ADMITTED (CORE, downtown-portland, 97201 / 97204 / 97205 / 97258). REQUIRED."),
    ("Pearl District", "ADMITTED (CORE, pearl-old-town-northwest, 97209 -- shared with Old Town / Chinatown, never "
                       "split) -- reported as an overlay. REQUIRED."),
    ("Old Town / Chinatown", "ADMITTED (CORE, pearl-old-town-northwest, 97209; its SW 1st / Naito edge is 97204, "
                             "downtown-portland) -- reported as an overlay. REQUIRED."),
    ("Northwest Portland", "ADMITTED (CORE, pearl-old-town-northwest, 97210 / 97231). REQUIRED."),
    ("Lloyd District / Convention Center", "ADMITTED (CORE, lloyd-convention-center, 97232 / 97227). REQUIRED."),
    ("Central Eastside", "ADMITTED (CORE, central-eastside, 97214 / 97202 / 97215). REQUIRED."),
    ("South Waterfront", "ADMITTED (CORE, south-waterfront-southwest, 97239; RiverPlace's 97201 side is "
                         "downtown-portland) -- reported as an overlay. REQUIRED."),
    ("PDX Airport", "ADMITTED (CORE, pdx-airport, 97220 / 97218 / 97230). REQUIRED."),
    ("Northeast Portland", "ADMITTED (CORE, northeast-north-portland, 97211 / 97212 / 97213 / 97217 / 97203). "
                           "REQUIRED."),
    ("Southeast Portland", "ADMITTED (CORE, central-eastside for the inner east 97214 / 97202 / 97215; "
                           "southeast-east-portland for 97206 / 97216 / 97266 / 97236). REQUIRED."),
    ("Beaverton", "ADMITTED (CORE, beaverton, 97005 / 97006 / 97007 / 97008 / 97003 / 97078 / 97225 / 97229). "
                  "REQUIRED."),
    ("Hillsboro", "ADMITTED (CORE, hillsboro, 97123 / 97124; the Tanasbourne south side in 97006 is in beaverton, "
                  "covered whole by its USPS preferred city). REQUIRED."),
    ("Tigard", "ADMITTED (CORE, tigard, 97223 / 97224). REQUIRED."),
    ("Lake Oswego", "ADMITTED (CORE, lake-oswego, 97034 / 97035). REQUIRED."),
    ("Gresham", "ADMITTED (CORE, gresham, 97030 / 97080 / 97233). REQUIRED."),
    ("Tualatin", "ADMITTED (STRONG CORRIDOR, tualatin-wilsonville, 97062). STRONG."),
    ("Wilsonville", "ADMITTED (STRONG CORRIDOR, tualatin-wilsonville, 97070). STRONG."),
    ("Clackamas", "ADMITTED (STRONG CORRIDOR, clackamas-happy-valley, 97015). STRONG."),
    ("Happy Valley", "ADMITTED (STRONG CORRIDOR, clackamas-happy-valley, 97086 / 97089). STRONG."),
    ("Troutdale", "ADMITTED (STRONG CORRIDOR, troutdale-fairview, 97060 / 97024) -- the Gorge's western threshold "
                  "inside the urban growth boundary. STRONG."),
    ("Oregon City", "ADMITTED (FRINGE, oregon-city-west-linn, 97045). CAREFUL."),
    ("Milwaukie", "ADMITTED (FRINGE, milwaukie, 97222 / 97267). CAREFUL."),
    ("Sherwood", "ADMITTED (FRINGE, sherwood, 97140). CAREFUL."),
    ("West Linn", "ADMITTED (FRINGE, oregon-city-west-linn, 97068). CAREFUL."),
    ("Forest Grove", "ADMITTED (FRINGE, forest-grove-cornelius, 97116) -- inside the urban growth boundary. "
                     "CAREFUL."),
    ("Cornelius", "ADMITTED (FRINGE, forest-grove-cornelius, 97113) -- inside the urban growth boundary. CAREFUL."),
    ("Gladstone", "ADMITTED (FRINGE, oregon-city-west-linn, 97027) -- not named by the order; inside the urban "
                  "growth boundary between Milwaukie and Oregon City, evaluated CAREFULLY so no hole is left."),
    ("Vancouver, Washington", "ADMITTED AS AN IN-MARKET CORRIDOR (registry class CORRIDOR, vancouver-wa, 98660 / "
                              "98661 / 98662 / 98663 / 98664 / 98665 / 98682 / 98683 / 98684 / 98685 / 98686) after "
                              "the eight-factor evaluation (VANCOUVER_EVALUATION). Every row keeps its WASHINGTON "
                              "identity. CROSS-RIVER BOUNDARY / CAREFUL."),
    ("Camas / Washougal", "OUTSIDE after CAREFUL evaluation -- Camas is its own SR-14 town at the Gorge approach; "
                          "Washougal is the Washington Gorge portal (columbia-gorge)."),
    ("Salem", "OUTSIDE -- FUTURE_STANDALONE salem-or; refused by prefix 973 and Woodburn by name. KEEP SEPARATE."),
    ("Eugene", "OUTSIDE -- FUTURE_STANDALONE eugene-or; refused by prefix 974. KEEP SEPARATE."),
    ("Hood River / Columbia River Gorge", "OUTSIDE -- FUTURE_STANDALONE columbia-gorge; refused by name and postal "
                                          "code on both shores. KEEP SEPARATE."),
    ("Oregon Coast", "OUTSIDE -- FUTURE_STANDALONE oregon-coast; refused by name and postal code. KEEP SEPARATE."),
    ("Bend", "OUTSIDE -- FUTURE_STANDALONE bend-or; refused by prefix 977. KEEP SEPARATE."),
    ("Longview / Kelso", "OUTSIDE -- FUTURE_STANDALONE longview-kelso; refused by postal code. KEEP SEPARATE."),
    ("Olympia", "OUTSIDE -- FUTURE_STANDALONE olympia-wa; refused by prefix 985. KEEP SEPARATE."),
    ("Tacoma", "OUTSIDE -- FUTURE_STANDALONE tacoma-wa; refused by prefix 984. KEEP SEPARATE."),
    ("Mount Hood resort inventory", "OUTSIDE -- FUTURE_STANDALONE mount-hood; refused by name and postal code. KEEP "
                                    "SEPARATE."),
    ("Newberg / Yamhill wine country", "OUTSIDE after CAREFUL evaluation -- outside the urban growth boundary."),
])

#: PHASE 3 -- the eight factors the order names for Vancouver, each measured or stated from a public fact.
VANCOUVER_EVALUATION = OrderedDict([
    ("traveller_intent",
     "Portland-bound. Vancouver's hotels sell Portland's attractions, the Moda Center, the Convention Center and PDX; "
     "Washington has no sales tax, so Portland shoppers and visitors deliberately stay north of the river. A traveller "
     "searching pet-friendly hotels 'in Portland' is shown Vancouver by every brand engine within 10 miles."),
    ("hotel_clustering",
     "Two real clusters: the downtown Vancouver waterfront (Hilton Vancouver Washington, the Heathman Lodge's "
     "east-side twin cluster aside, the waterfront AC / Indigo / Residence Inn-class towers) 3 miles from Hayden "
     "Island, and the SR-14 / I-205 Cascade Park and Vancouver Mall clusters 5-7 miles from the PDX terminal. The "
     "census measures the count (boundary accounting)."),
    ("drive_continuity",
     "Continuous: the I-5 Interstate Bridge joins downtown Vancouver to Hayden Island / North Portland (97217) in "
     "under 2 miles, and the I-205 Glenn Jackson Bridge joins Cascade Park to the PDX / Parkrose corridor (97220 / "
     "97230). Downtown Vancouver is closer to downtown Portland (8 miles) than Hillsboro (16) or Wilsonville (18)."),
    ("airport_relationship",
     "PDX is Vancouver's only commercial airport and sits 6-9 miles from every Vancouver cluster; the I-205 Cascade "
     "Park hotels are, by drive time, PDX airport hotels. No other airport serves Clark County."),
    ("cross_river_business_travel",
     "One labour market: the Portland-Vancouver-Hillsboro MSA (OMB) is a single metro, with C-TRAN express buses "
     "into downtown Portland and the commuter flows on I-5 / I-205 that define it."),
    ("hotel_marketing",
     "The brands themselves pair the two names (Marriott, Hilton and IHG property names of the form "
     "'Portland/Vancouver' or 'Vancouver-Portland'); the census measures that count. Marketing alone admits nothing "
     "-- it is one factor of eight, and each row is still placed only by its own Washington postal code."),
    ("corridor_strength",
     "Comparable to a CORE suburban corridor (Beaverton / Hillsboro scale), not a thin edge; the corridor accounting "
     "reports its census and publishes only if it clears the 5-profile threshold on its own evidence."),
    ("future_standalone_value",
     "LOW as a market of its own. Vancouver is not a destination a traveller drives TO -- it is where Portland "
     "visitors sleep. The Columbia Gorge (Stevenson, White Salmon) and Longview / Kelso, which ARE separate trips, "
     "are refused and preserved. Refusing Vancouver would leave the PDX-adjacent Washington inventory unaccounted "
     "for, not preserved for anything."),
    ("ruling",
     "IN-MARKET CORRIDOR (vancouver-wa, registry class CORRIDOR) for the City of Vancouver and its contiguous urban "
     "unincorporated area; OUTSIDE for Camas, Washougal (columbia-gorge), Battle Ground, Ridgefield, La Center and "
     "Woodland; FUTURE_STANDALONE longview-kelso for Cowlitz County. Washington state identity is retained on every "
     "row: city Vancouver, state WA, the property's own 986 postal code, never 'Portland, OR'."),
    ("precedent",
     "Charlotte (charlotte-nc) admits Fort Mill / Carowinds, SOUTH CAROLINA as a corridor of a North Carolina market "
     "with every row's own state retained; the live seattle-wa geography already names Clark County 'part of the "
     "Portland, Oregon market' when refusing it from Seattle."),
])

#: The Columbia Gorge / Mount Hood ruling (consumers read it under the inherited name HILL_COUNTRY_RULING).
GORGE_AND_MOUNTAIN_RULING = OrderedDict([
    ("classification", "The metro-continuous Portland / Washington County / Clackamas / Vancouver core inside the "
                       "urban growth boundary is admitted -- the eight City of Portland corridors, Beaverton, "
                       "Hillsboro, Tigard, Lake Oswego and Gresham CORE; Tualatin / Wilsonville, Clackamas / Happy "
                       "Valley, Troutdale / Fairview and Vancouver WA STRONG CORRIDOR; Milwaukie, Oregon City / West "
                       "Linn / Gladstone, Sherwood and Forest Grove / Cornelius FRINGE. Salem, Eugene, the Columbia "
                       "Gorge, Mount Hood, the Oregon Coast, Bend, Longview / Kelso, Olympia and Tacoma are OUTSIDE."),
    ("a_marketing_phrase_admits_nothing", "'Portland Airport', 'Portland East', 'Portland/Beaverton', "
                                          "'Portland/Hillsboro', 'Portland Lake Oswego', 'Portland/Vancouver', "
                                          "'Portland North', 'Gateway to the Gorge', 'Gateway to Mount Hood' and "
                                          "'Hood River / Portland' are marketing. The property's own postal code "
                                          "decides."),
    ("actual_location", "Decided by the property's own postal code on its own page."),
    ("drive_market_relationship", "PDX, the Washington County tech corridor, the Clackamas / I-205 ring, Troutdale and "
                                  "Vancouver are where Portland-bound travellers sleep; the Gorge, Mount Hood, the "
                                  "coast, the wine country, Salem and Eugene are trips of their own."),
    ("traveller_intent", "Convention (the Oregon Convention Center), arena (Moda Center / Providence Park), "
                         "medical (OHSU, Providence, Legacy, Kaiser), university (PSU, OHSU, University of Portland, "
                         "Reed, Pacific), corporate (Nike, Intel, Columbia Sportswear, Daimler Trucks) and PDX demand "
                         "is Portland intent; Multnomah Falls, Timberline, Cannon Beach and the Dundee Hills are not."),
    ("metro_continuity", "Continuous development runs inside the Metro urban growth boundary from Forest Grove to "
                         "Troutdale and from Vancouver to Wilsonville; it is broken by the UGB line itself at Sandy, "
                         "Canby, Newberg and North Plains, by the Gorge Scenic Area east of Troutdale and by the "
                         "Vancouver urban-area line at Camas and Battle Ground."),
    ("corridor_support", "Every admitted edge code is in a named corridor (troutdale-fairview, tualatin-wilsonville, "
                         "clackamas-happy-valley, sherwood, forest-grove-cornelius, oregon-city-west-linn, "
                         "vancouver-wa) so its count is visible and a founder can move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE salem-or, eugene-or, columbia-gorge, mount-hood, oregon-coast, bend-or, "
                      "longview-kelso, olympia-wa and tacoma-wa."),
])
HILL_COUNTRY_RULING = GORGE_AND_MOUNTAIN_RULING

STRUCTURE_TEST = OrderedDict([
    ("A. Is Portland one market, or several?",
     "ONE market, portland-or, covering the contiguous Portland metro inside Oregon's Metro urban growth boundary "
     "plus the Vancouver urban area across the Columbia -- one commercial airport (PDX), one I-5 / I-84 / I-205 / "
     "I-405 / US-26 / OR-217 road system, one MAX light-rail network. The UGB line, the Gorge Scenic Area and the "
     "Vancouver urban-area line are where that coherence stops."),
    ("B. The City of Portland is NOT the market -- and 'Portland' places nothing",
     "Beaverton, Hillsboro, Tigard, Lake Oswego, Gresham, Tualatin, Wilsonville, Clackamas, Troutdale and Vancouver "
     "are admitted by their own codes; the chains' 'Portland' prefix is on hotels from Hood River to Vancouver."),
    ("C. PDX", "The airport's lodging system (NE Airport Way / Cascade Station / NE 82nd) is its own CORE corridor, "
               "97220 / 97218 / 97230."),
    ("D. Pearl / Old Town / Chinatown", "NO CORRIDOR of their own -- overlays of 97209, never split."),
    ("E. Lloyd / Convention Center", "Its own CORE corridor (97232 / 97227)."),
    ("F. Hillsboro vs Beaverton at Tanasbourne", "97006 is ONE postal code whose USPS preferred city is Beaverton: "
                                                 "covered whole by beaverton; Hillsboro proper is 97123 / 97124."),
    ("G. Vancouver, Washington", "IN-MARKET CORRIDOR with Washington identity retained (VANCOUVER_EVALUATION)."),
    ("H. Salem", "OUTSIDE -- FUTURE_STANDALONE salem-or."),
    ("I. Eugene", "OUTSIDE -- FUTURE_STANDALONE eugene-or."),
    ("J. Columbia Gorge / Hood River", "OUTSIDE -- FUTURE_STANDALONE columbia-gorge."),
    ("K. Mount Hood", "OUTSIDE -- FUTURE_STANDALONE mount-hood."),
    ("L. Oregon Coast", "OUTSIDE -- FUTURE_STANDALONE oregon-coast."),
    ("M. Newberg / Canby / Sandy / Scappoose", "OUTSIDE -- outside the urban growth boundary."),
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
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. Portland's "
     "specific exposures: the Pearl District / South Waterfront / Lloyd condo and apartment towers with furnished "
     "short-stay units, the serviced-apartment and aparthotel operators (Sonder, Kasa, Mint House, Placemakr, "
     "Blueground, Lark, Barsala, Society), corporate-housing portfolios, hotel-and-residences towers (the residences "
     "are never the hotel), WorldMark / Club Wyndham vacation-ownership inventory and the Airbnb / Vrbo inventory."),
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
     "Patient-family housing (the Ronald McDonald Houses, OHSU / Doernbecher family housing, Hope Lodge), charitable "
     "family lodging (Fisher House) and on-base military lodging are never public hotels and are never admitted."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("97209", ["Pearl District", "Old Town / Chinatown", "Union Station"]),
    ("97201", ["Downtown / PSU", "RiverPlace", "South Waterfront (north)"]),
    ("97232", ["Lloyd District", "Oregon Convention Center"]),
    ("97220", ["PDX", "Cascade Station", "Gateway north"]),
    ("97217", ["North Portland", "Hayden Island / Jantzen Beach"]),
    ("97006", ["Beaverton", "Aloha", "Hillsboro (Tanasbourne south)"]),
    ("97003", ["Beaverton", "Aloha", "Hillsboro"]),
    ("97225", ["Portland (mailing)", "Raleigh Hills / West Slope", "Beaverton"]),
    ("97229", ["Portland (mailing)", "Cedar Mill / Bethany"]),
    ("97223", ["Tigard", "Metzger", "Garden Home"]),
    ("97224", ["Tigard", "King City", "Durham"]),
    ("97233", ["Portland (Rockwood)", "Gresham"]),
    ("97060", ["Troutdale", "Wood Village"]),
    ("97015", ["Clackamas", "Happy Valley"]),
    ("97222", ["Milwaukie", "Oak Grove"]),
    ("97062", ["Tualatin", "Durham"]),
    ("98664", ["Vancouver", "Fort Vancouver"]),
    ("98665", ["Vancouver", "Hazel Dell"]),
    ("98682", ["Vancouver", "Orchards"]),
])

FUTURE_MARKETS = OrderedDict([
    ("salem-or", "Salem / Keizer / Woodburn -- the state capital, 45 miles south on I-5."),
    ("eugene-or", "Eugene / Springfield -- 110 miles south."),
    ("columbia-gorge", "The Columbia River Gorge -- Multnomah Falls, Cascade Locks, Hood River, The Dalles, Stevenson "
                       "(Skamania Lodge), White Salmon."),
    ("mount-hood", "Mount Hood -- Sandy, Welches, Government Camp, Timberline."),
    ("oregon-coast", "The Oregon Coast -- Astoria, Seaside, Cannon Beach, Tillamook, Lincoln City, Newport."),
    ("bend-or", "Bend / Central Oregon."),
    ("longview-kelso", "Longview / Kelso / Kalama -- Cowlitz County, 45 miles north on I-5."),
    ("olympia-wa", "Olympia / Lacey / Tumwater -- the Washington state capital, 100 miles north."),
    ("tacoma-wa", "Tacoma / Pierce County -- 140 miles north."),
])

#: Markets that are ALREADY LIVE. Exactly one live market shares a state with this one (seattle-wa, Washington); it
#: owns the 980 / 981 codes and none of Vancouver's 986 codes. Every other exposure is a shared NAME only (Portland,
#: MAINE is not a market; Vancouver, BC is not in the United States; Beaverton, Hillsboro, Gresham and Troutdale
#: are not place names any live market prints; Milwaukie is not Milwaukee).
EXISTING_LIVE_MARKETS = OrderedDict([
    ("seattle-wa", "Seattle / Bellevue / Puget Sound, live as production market #40 (deploy "
                   "6ac169ef7c75c383eb79f824) -- the CURRENT LIVE market at this order's authoring time and the only "
                   "other Pacific Northwest market. It owns 980 / 981; no shared postal code. Its own geography refuses "
                   "Clark County as 'part of the Portland, Oregon market'."),
    ("milwaukee-wi", "Milwaukee, live -- 'Milwaukee' and this market's 'Milwaukie' differ by one letter; identity is "
                     "decided by premises, never the name."),
])

#: A shared postal code whose OTHER town is refused. None at authoring time.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "portland,": "portland", "portland or": "portland", "portland, or": "portland", "portland oregon": "portland",
    "pdx": "portland", "beaverton,": "beaverton", "aloha,": "aloha", "hillsboro,": "hillsboro",
    "tigard,": "tigard", "king city,": "king city", "durham,": "durham", "lake oswego,": "lake oswego",
    "lk oswego": "lake oswego", "gresham,": "gresham", "tualatin,": "tualatin", "wilsonville,": "wilsonville",
    "clackamas,": "clackamas", "happy valley,": "happy valley", "damascus,": "damascus", "troutdale,": "troutdale",
    "wood village,": "wood village", "fairview,": "fairview", "milwaukie,": "milwaukie", "oak grove,": "oak grove",
    "oregon city,": "oregon city", "west linn,": "west linn", "gladstone,": "gladstone", "sherwood,": "sherwood",
    "forest grove,": "forest grove", "cornelius,": "cornelius", "vancouver,": "vancouver", "vancouver wa": "vancouver",
    "vancouver, wa": "vancouver", "vancouver washington": "vancouver", "hazel dell,": "hazel dell",
    "salmon creek,": "salmon creek", "orchards,": "orchards",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("97204", "Downtown core -- Pioneer Courthouse Square, the downtown hotel row."),
    ("97209", "Pearl District and Old Town / Chinatown -- one postal code, never split."),
    ("97232", "Lloyd District / Oregon Convention Center."),
    ("97220", "PDX -- NE Airport Way and Cascade Station."),
    ("97217", "North Portland and Hayden Island / Jantzen Beach at the I-5 bridge."),
    ("97006", "Beaverton / Aloha / Tanasbourne south -- USPS preferred city Beaverton, covered whole."),
    ("98660", "Downtown Vancouver, WASHINGTON -- state identity retained."),
    ("97031", "Hood River -- refused (columbia-gorge)."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Portland" % name),
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
        raise SystemExit("admitted postal codes outside the Portland / Vancouver prefixes: %s" % stray)
    registered_codes = _registered_market_postal_codes()
    live_overlap = sorted(z for z in seen_zip if z in registered_codes)
    if live_overlap:
        raise SystemExit("admitted postal codes a REGISTERED market already admits: %s" % [
            (z, registered_codes[z]) for z in live_overlap])
    military_unclaimed = [z for z in MILITARY_POSTAL_CODES if z not in seen_zip]
    if military_unclaimed:
        raise SystemExit("military postal codes claimed by no corridor: %s" % military_unclaimed)

    cell_state = {slug: state for slug, _n, _a, _k, _m, _z, _d, state in CORRIDORS}
    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
        ("state_code", cell_state.get(suffix) or ("WA" if suffix in ("obs-clark-outer", "obs-longview") else "OR")),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Portland / Greater Portland downtown, Pearl, convention, arena, medical, university, "
                        "corporate, airport, Washington County, Clackamas, Gresham / Troutdale and Vancouver WA "
                        "lodging market (PetTripFinder discovery scope)"),
        ("state", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("country", "US"),
        ("market_center", {"lat": 45.52, "lng": -122.68}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past Salem, east through the Columbia "
             "Gorge to The Dalles and up Mount Hood, west to the Oregon Coast and north past Longview / Kelso, so "
             "that " + WORK_ORDER + " classifies those properties on evidence instead of being blind to them. "
             "Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Portland / Greater Portland is ONE market: thirteen CORE corridors (downtown, Pearl / Old "
         "Town / Northwest, South Waterfront / Southwest, Lloyd / Convention Center, the Central Eastside, PDX, "
         "Northeast / North Portland, Southeast / East Portland, Beaverton, Hillsboro, Tigard, Lake Oswego, "
         "Gresham), four STRONG CORRIDORS (Tualatin / Wilsonville, Clackamas / Happy Valley, Troutdale / Fairview, "
         "Vancouver WA -- its rows keep their Washington identity) and four FRINGE corridors (Milwaukie, Oregon City "
         "/ West Linn / Gladstone, Sherwood, Forest Grove / Cornelius). SALEM, EUGENE, the COLUMBIA GORGE, MOUNT "
         "HOOD, the OREGON COAST, BEND, LONGVIEW / KELSO, OLYMPIA and TACOMA are refused as future standalone "
         "markets; every town outside Oregon's Metro urban growth boundary and the Vancouver urban area is refused "
         "by name. Patient, charitable and on-base lodging is never admitted."),
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
        ("market_name", "Portland, Oregon"),
        ("market_slug", MARKET_ID),
        ("state_name", "Oregon"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("primary_city", "Portland"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Portland, Oregon | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater Portland -- downtown, the Pearl District, the Lloyd District "
         "and Convention Center, PDX airport, Beaverton, Hillsboro, Tigard, Lake Oswego, Gresham and Vancouver, WA "
         "-- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Portland"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry. A Portland / Greater Portland downtown, Pearl, convention, "
         "arena, medical, university, corporate, airport and suburban travel market -- the contiguous metro inside "
         "Oregon's Metro urban growth boundary from Forest Grove to Troutdale and Wilsonville, plus the Vancouver, "
         "WASHINGTON urban area across the Columbia (every Vancouver row keeps its own Washington city, state and "
         "postal code). Not 'Northwest Oregon': Salem, Eugene, the Columbia Gorge / Hood River, Mount Hood, the "
         "Oregon Coast and Bend are future standalone markets; Newberg, Canby, Sandy, Scappoose, Camas, Battle "
         "Ground and Longview / Kelso are refused. Nothing else admits a property: not a brand's 'Portland' "
         "marketing name, not a map pin, not a vacation-rental listing, not a competitor directory's city label. "
         "Patient, charitable and on-base lodging is never admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). The postal city "
         "'PORTLAND' spans nine corridors (including Cedar Mill / Bethany and Raleigh Hills in Washington County) "
         "and places nothing by itself. Shared codes are covered whole: 97209 by the Pearl District and Old Town / "
         "Chinatown; 97006 by Beaverton, Aloha and Tanasbourne south; 97233 by Portland and Gresham; 97015 by "
         "Clackamas and Happy Valley. Pioneer Courthouse Square, the Pearl, Old Town / Chinatown, RiverPlace, South "
         "Waterfront, the Convention Center, the Rose Quarter, PDX / Cascade Station and Hayden Island are "
         "overlays. The vancouver-wa corridor is the only Washington corridor; its state_code is WA."),
        ("_census_membership_note",
         "Individual condominium units, private residences, vacation homes, property-management and corporate-housing "
         "portfolios, serviced-apartment operators, Airbnb / Vrbo inventory, ordinary apartments, timeshare and "
         "vacation-club inventory, residential-only towers, privately managed residences inside hotel towers, "
         "member-only club lodging and on-base military / government lodging are never admitted. A mixed hotel / "
         "condo / residence property is admitted only as the exact hotel premises its public operator sells as a "
         "hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 + 6 -- Portland / Greater Portland travel-market geography, the Vancouver WA "
                  "cross-river boundary, the Columbia Gorge / Mount Hood boundary, the airport / suburban identity "
                  "trap and the residence / apartment / vacation-rental safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/portland-or.json. This "
         "order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its brand's own property card states it, "
         "joined to the corridor registry. Nothing else admits a property."),
        ("oregon_side_test",
         "Oregon's Metro urban growth boundary: every UGB city is claimed by a corridor and no non-UGB town is."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG_CORRIDOR is registry class CORRIDOR; FUTURE_STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes and by postal PREFIX for the "
                          "refused regions; the future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("vancouver_wa_evaluation", VANCOUVER_EVALUATION),
        ("hill_country_ruling", HILL_COUNTRY_RULING),
        ("metro_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("military_lodging_rule", OrderedDict([
            ("rule", "On-base military / government lodging is MILITARY_RESTRICTED and never admitted: restricted "
                     "eligibility (DoD ID or sponsorship), on-base premises behind a gate, ordinary public-hotel "
                     "contract NOT satisfied. No installation owns an admitted Portland postal code; the on-base "
                     "names are refused wherever they appear."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "Portland was selected as a high-value PetTripFinder market for its downtown / Pearl tourism, convention "
         "and arena demand, medical and university travel (OHSU), corporate travel (Nike, Intel), extended-stay "
         "demand and PDX airport traffic. That lowers NO evidence standard: pet acceptance is never inferred from "
         "Portland's reputation as a dog-friendly city. It shapes only the CENSUS: every tourist, convention, "
         "arena, medical, university, corporate, airport and extended-stay lodging cluster is covered by an "
         "admitting corridor."),
        ("the_portland_name_trap",
         "The chains put 'Portland' on hotels from Hood River to Vancouver: 'Portland Airport' on NE Airport Way and "
         "Cascade Station hotels (and on Vancouver and Gresham hotels), 'Portland/Beaverton', 'Portland/Hillsboro', "
         "'Portland/Tigard', 'Portland Lake Oswego', 'Portland/Clackamas', 'Portland East' on Troutdale hotels, "
         "'Portland/Vancouver' on Washington hotels. A property's own postal code, street and brand property code "
         "decide what and where it is; none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Portland International Airport (PDX)", "its own corridor pdx-airport (97220 / 97218 / 97230)."),
            ("Oregon Convention Center", "lloyd-convention-center (97232) -- overlay."),
            ("Moda Center / Rose Quarter", "lloyd-convention-center (97227) -- overlay."),
            ("Providence Park", "downtown-portland (97205) -- overlay."),
            ("Pearl District / Old Town / Chinatown / Union Station", "pearl-old-town-northwest (97209) -- overlays."),
            ("OHSU / South Waterfront / the aerial tram", "south-waterfront-southwest (97239)."),
            ("Portland State University", "downtown-portland (97201)."),
            ("Nike World Headquarters", "beaverton (97005)."),
            ("Intel Ronler Acres / Hawthorn Farm", "hillsboro (97124)."),
            ("Washington Square", "tigard (97223)."),
            ("Clackamas Town Center", "clackamas-happy-valley (97015)."),
            ("Columbia Gorge Outlets (gateway)", "troutdale-fairview (97060)."),
            ("Portland Expo Center / Delta Park", "northeast-north-portland (97217)."),
            ("Vancouver Waterfront", "vancouver-wa (98660) -- Washington."),
        ])),
        ("evaluated_inclusions", EVALUATED_INCLUSIONS),
        ("nonpublic_names", NONPUBLIC_NAMES),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("admitted_postal_codes_by_state", OrderedDict(
            (s, sorted(z for z in seen_zip if state_for_postal(z) == s)) for s in STATE_CODES)),
        ("admitted_counties", sorted(ADMITTED_COUNTIES)),
        ("observed_outside_counties", OBSERVED_COUNTIES),
        ("outside_prefixes", [OrderedDict([("prefix", p), ("area", n), ("future_market", f)])
                              for p, n, f in OUTSIDE_PREFIXES]),
        ("shared_postal_codes", SHARED_POSTAL_CODES),
        ("registered_market_postal_codes_checked", len(registered_codes)),
        ("no_live_market_postal_code_admitted", not live_overlap),
        ("first_oregon_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("state_code", c["state_code"]), ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, convention, arena or "
         "outlet-mall keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration "
         "order publishes it."),
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
         "/ Vrbo listings; ordinary apartments; timeshare and vacation-club inventory; residential-only towers; "
         "privately managed residences; member-only club lodging; on-base military / government lodging; and "
         "privately managed units inside hotel-condo towers. Campgrounds, RV parks and hostels are NON_LODGING."),
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
        return "OUTSIDE", None, "north-west Oregon / south-west Washington postal code %r is claimed by no corridor" % z
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
