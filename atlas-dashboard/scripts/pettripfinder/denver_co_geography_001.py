"""PTF-DENVER-CO-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5 and 6: the Denver / Boulder / Front Range market.

Built from zero on the CURRENT hardened lineage: the San Diego-live release 1724e822 (live source f01587ba,
built_from 34d523d9). Current verified live at authoring time = san-diego-ca deploy 6ab859787d349f8397e1450a,
35 markets / 2,666 profiles / 2,969 release-index routes / 3,037 served routes, host verified (the live
sitemap.xml hashes to 4f648fff...). No earlier Denver build exists, and this is the FIRST Colorado market: no live
market owns a single Colorado postal code.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Denver traveller lodging market -- not the City and County of Denver, and not "the Front Range" --
stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE markets named inside
OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact to make a number.
The order's "STRONG CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property
card) states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted
lodging ZIP is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A
brand's marketing name never admits and never places a property: a hotel titled "Denver North" whose own address
states Loveland 80538 is a Larimer County hotel, and a hotel titled "Boulder / Longmont" is placed by its own code.

WHY "DENVER" DECIDES NOTHING HERE
---------------------------------
The chains put "Denver" in the name of hotels in Aurora, Lakewood, Golden, Westminster, Thornton, Lone Tree,
Englewood, Littleton, Brighton, Parker and Castle Rock -- and the postal city "DENVER" itself spills over the
city line into Glendale (80246), unincorporated Arapahoe and Adams County (80221, 80229, 80231) and Lakewood
(80226, 80227, 80232, 80235). "Denver Tech Center" is a business district split across Denver (80237), Greenwood
Village (80111) and Centennial / Englewood (80112). "Denver Airport" hotels stand in Denver 80249 and 80239 and
in Aurora 80011 and 80019. Each is placed by its own postal code.

THE BOULDER RULING (PHASE 3): STRONG CORRIDOR, ITS OWN CORRIDOR, NEVER FLATTENED INTO DENVER
-------------------------------------------------------------------------------------------
Boulder (80301-80305, 80310) is admitted as a STRONG CORRIDOR (registry class CORRIDOR) with its own corridor,
boulder, and Louisville / Superior / Lafayette keep a SEPARATE corridor so Boulder's own page is Boulder's.
  * hotel inventory -- a real city inventory (CU's hotels, the downtown Pearl Street boutiques, the Baseline /
    28th Street / Diagonal chains), large enough to publish on its own, small enough that a separate market
    would be a thin one today;
  * traveller intent -- the University of Colorado, the Flatirons, Chautauqua and the Boulder Creek path: an
    outdoor-and-university destination distinct from downtown Denver's convention / sports / business demand;
  * drive pattern -- 25 miles on US-36 (with the Flatiron Flyer BRT), inside the metro commute shed;
  * airport relation -- Boulder has NO commercial airport; its travellers arrive through DEN, which is the
    decisive test that keeps it inside the Denver traveller market rather than FUTURE_STANDALONE;
  * outdoor / pet-travel relevance -- the highest in the metro (open-space trails, Boulder Canyon), which is why
    it keeps its own page instead of being a line in a generic "Denver suburbs" list;
  * corridor coherence -- one city, one set of postal codes, no code shared with Denver.
Boulder is also recorded as this market's NAMED first candidate for promotion to a standalone market, so a founder
can split it on the record.

MOUNTAIN ACCESS (PHASE 4)
-------------------------
Golden (the Coors / Colorado School of Mines town at the mouth of Clear Creek Canyon and I-70's climb), Morrison
(Red Rocks, 80465) and the C-470 / I-70 west side (Lakewood's Denver West, Wheat Ridge's Kipling exit) are the
metro's mountain gateway and are ADMITTED. The mountain towns themselves -- Evergreen, Idaho Springs, Georgetown,
Black Hawk / Central City, Nederland, Lyons, Estes Park -- and every ski-resort market (Summit County, Vail /
Beaver Creek, Aspen / Snowmass, Winter Park / Fraser, Steamboat) are OUTSIDE, named as FUTURE_STANDALONE where
they are markets of their own. Denver's outdoor reputation lowers NO evidence standard: it shapes the census only
(every gateway / trail / long-stay / airport cluster is covered by an admitting cell), never a policy fact.

AIRPORT, BUSINESS, MEDICAL, EVENT DEMAND (PHASE 5)
--------------------------------------------------
DEN is 25 miles from downtown on Pena Boulevard and has its OWN lodging system: the Westin on the terminal, the
Tower Road / Pena Boulevard hotels (Denver 80249), the 40th Avenue / Chambers Road cluster (Montbello, Denver
80239) and the Gaylord Rockies at E-470 (Aurora 80019). Those three codes are the den-airport corridor -- the
first market since Jacksonville where the AIRPORT test answers YES. Aurora's Gateway Park hotels (E 40th Circle,
Aurora 80011) are marketed as "Denver Airport" but share 80011 with the Anschutz Medical Campus / Fitzsimons
hotels and East Colfax; a shared code is covered whole and never split, so 80011 is Aurora's and DEN is an
OVERLAY on those rows. The Colorado Convention Center and Union Station are downtown (80202); Anschutz (80045)
is Aurora; the DTC is its own corridor; Cherry Creek and Glendale share a corridor.

RESORT / CONDO / EXTENDED-STAY (PHASE 6)
----------------------------------------
Extended-stay hotels (Residence Inn, Homewood, Home2, Staybridge, Candlewood, Hyatt House, TownePlace, Element,
ESA, WoodSpring, Sonesta ES, InTown) are hotels and are admitted on their own pages. Apartment hotels and serviced
apartments are admitted only as a public hotel operation at an exact premises. Ordinary apartments, condo units,
Airbnb / Vrbo, private residences, property-management portfolios, the City and County of Denver's short-term
rental licences and individual timeshare units are never admitted.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/denver_co.json
  launch_packages/pettripfinder/markets/proposed/denver-co.json
  launch_packages/pettripfinder/markets/reports/denver_co_geography_001.json
  launch_packages/pettripfinder/markets/reports/denver_co_corridor_registry_001.json
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

WORK_ORDER = "PTF-DENVER-CO-HARDENED-SOURCE-READY-001"
MARKET_ID = "denver-co"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "denver_co.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "denver-co.json")
REPORT_OUT = os.path.join(REPORTS, "denver_co_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "denver_co_corridor_registry_001.json")
AS_OF = "2026-09-27"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown-lodo-union-station", "Downtown Denver, LoDo & Union Station",
     "Downtown / LoDo / Union Station / Auraria", "CORE", "denver",
     ["80202", "80204", "80264", "80265", "80290", "80293", "80294"],
     "Downtown Denver's central business district, Lower Downtown (LoDo) and Union Station, Larimer Square, the "
     "16th Street Mall, the Colorado Convention Center (700 14th St), the Denver Performing Arts Complex, Coors "
     "Field's edge, and -- across Speer Boulevard in 80204 -- the Auraria campus, Ball Arena, Empower Field at Mile "
     "High and Lincoln Park / La Alma. LoDo and Union Station share 80202 with the CBD and are OVERLAYS, never a "
     "split code. The single-building downtown codes (80264, 80265, 80290, 80293, 80294) are downtown's too."),
    ("capitol-hill-uptown", "Capitol Hill & Uptown", "Capitol Hill / Uptown / Cheesman Park", "CORE", "denver",
     ["80203", "80218"],
     "The State Capitol and Civic Center's east side, Capitol Hill, Governor's Park, Uptown / City Park West, "
     "Cheesman Park and the Colfax Avenue strip (80203 / 80218). Walkable historic neighbourhoods with Denver's "
     "boutique and historic inns, one mile from the convention center."),
    ("highlands-rino-north-denver", "Highlands, RiNo & North Denver", "Highlands / RiNo / Five Points / Globeville",
     "CORE", "denver", ["80205", "80211", "80212", "80216"],
     "The River North Art District and Five Points (80205 / 80216), Globeville and Elyria-Swansea with the "
     "National Western Center and the I-70 / I-25 interchange (80216), and the Highlands, Sunnyside, Berkeley "
     "and Sloan's Lake (80211 / 80212) across I-25 from LoDo."),
    ("cherry-creek-glendale", "Cherry Creek & Glendale", "Cherry Creek / Glendale / Washington Park", "CORE",
     "denver", ["80206", "80209", "80246"],
     "Cherry Creek North and the Cherry Creek Shopping Center (80206), Washington Park / Belcaro / Country Club "
     "(80209) and the City of Glendale -- an enclave whose postal city is DENVER -- with its Colorado Boulevard "
     "hotel row (80246). Denver's luxury shopping-and-dining district and the market's upscale boutique cluster."),
    ("central-park-lowry-i70", "Central Park, Lowry & the I-70 East Corridor",
     "Central Park (Stapleton) / Lowry / Park Hill / Quebec Street", "CORE", "denver",
     ["80207", "80220", "80230", "80238"],
     "The former Stapleton airport -- now Central Park -- and its I-70 / Quebec Street hotel cluster (80207 / "
     "80238), Park Hill, Montclair and Hale (80220) and Lowry (80230). A dense mid-price cluster between downtown "
     "and DEN that serves both."),
    ("south-denver-university", "South Denver, DU & Colorado Boulevard",
     "University of Denver / Colorado Blvd / Hampden / Federal Blvd", "CORE", "denver",
     ["80210", "80219", "80222", "80223", "80224", "80231", "80236"],
     "The University of Denver and Platt Park (80210), the I-25 / Colorado Boulevard / Evans hotel row (80222), "
     "Goldsmith and the Hampden / I-225 / Parker Road interchange (80224 / 80231), and the city's west and "
     "southwest side on Federal Boulevard, Alameda and Hampden (80219 / 80223 / 80236)."),
    ("denver-tech-center", "Denver Tech Center, Greenwood Village & Park Meadows",
     "DTC / Greenwood Village / Centennial / Lone Tree / Park Meadows", "CORE", "englewood",
     ["80237", "80111", "80112", "80124"],
     "The Denver Technological Center astride I-25 -- split across Denver (80237), Greenwood Village (80111) and "
     "Centennial / unincorporated Arapahoe County with an ENGLEWOOD postal city (80112: Inverness, Meridian, "
     "Arapahoe Road) -- and Lone Tree / Park Meadows (80124) at the C-470 interchange. The market's corporate "
     "lodging district; 'DTC' in a hotel's name places nothing, its code does."),
    ("den-airport", "Denver International Airport (DEN)", "DEN / Pena Boulevard / Tower Road / Gaylord Rockies",
     "CORE", "denver", ["80249", "80239", "80019"],
     "Denver International Airport's own lodging system: the Westin on the terminal and the Pena Boulevard / Tower "
     "Road / 68th Avenue hotels (Denver 80249), the 40th Avenue / Chambers Road / Peoria cluster in Montbello "
     "(Denver 80239) and the Gaylord Rockies resort and the E-470 / 64th Avenue hotels (Aurora 80019). DEN owns "
     "its postal code, so -- unlike San Diego, Palm Beach or Fort Lauderdale -- the AIRPORT test answers YES. "
     "Aurora's Gateway Park hotels (80011) are an overlay of the aurora corridor: 80011 is shared with Anschutz "
     "and East Colfax and is never split."),
    ("aurora", "Aurora, Anschutz & Gateway Park", "Aurora / Anschutz Medical Campus / Gateway Park / I-225",
     "CORE", "aurora",
     ["80010", "80011", "80012", "80013", "80014", "80015", "80016", "80017", "80018", "80045", "80247"],
     "The City of Aurora: the Anschutz Medical Campus and Fitzsimons (80045 and its 80010 / 80011 edges), East "
     "Colfax, the Gateway Park 'Denver Airport' hotels on E 40th Circle (80011), the I-225 / Aurora Mall / "
     "Havana corridor (80012 / 80014 / 80247), Southlands and the E-470 south side (80015 / 80016). Its own city "
     "with its own convention demand; DEN is an overlay on its Gateway Park rows."),
    ("lakewood-wheat-ridge", "Lakewood, Wheat Ridge & Denver West", "Lakewood / Belmar / Wheat Ridge / Federal Center",
     "CORE", "lakewood",
     ["80214", "80215", "80226", "80227", "80228", "80232", "80235", "80033", "80034"],
     "The City of Lakewood -- Belmar, the Denver Federal Center and Union Boulevard (80226 / 80228), Wadsworth "
     "(80214 / 80215 / 80232), Bear Creek and Bear Valley (80227 / 80235) -- and Wheat Ridge's I-70 / Kipling "
     "hotel exit (80033). The west side's business-and-drive cluster on the way to the mountains."),
    ("golden-red-rocks", "Golden, Morrison & Red Rocks", "Golden / Morrison / Red Rocks / Denver West", "CORRIDOR",
     "golden", ["80401", "80403", "80419", "80465"],
     "The City of Golden -- downtown Golden, the Colorado School of Mines, Coors, Clear Creek and the Denver West "
     "office park whose hotels carry a GOLDEN postal city (80401 / 80403) -- and Morrison with Red Rocks Park and "
     "Amphitheatre (80465). The metro's mountain gateway: US-6 into Clear Creek Canyon and I-70's climb begin "
     "here. A STRONG CORRIDOR with the highest outdoor-access relevance after Boulder."),
    ("arvada", "Arvada", "Arvada / Olde Town / Ralston Road", "CORRIDOR", "arvada",
     ["80002", "80003", "80004", "80005", "80007"],
     "The City of Arvada: Olde Town Arvada on the G-Line, Ralston Road, Wadsworth and the I-70 / Ward Road edge. A "
     "suburban drive market with a small hotel inventory, admitted so it is ACCOUNTED FOR; it publishes only if it "
     "meets the threshold on its own."),
    ("westminster-broomfield", "Westminster, Broomfield & Interlocken", "Westminster / Broomfield / Interlocken / US-36",
     "CORRIDOR", "westminster",
     ["80020", "80021", "80023", "80030", "80031", "80038", "80234"],
     "The US-36 corridor between Denver and Boulder: Westminster (Westminster Boulevard, Church Ranch, the "
     "Orchard and the I-25 / 120th / 136th Avenue hotels) and the City and County of Broomfield (the Interlocken "
     "business park and Flatiron Crossing). The two cities SHARE 80020 and 80021, so they are one corridor, never "
     "a split code; each is reported as its own overlay."),
    ("thornton-northglenn-north-i25", "Thornton, Northglenn & North I-25", "Thornton / Northglenn / Federal Heights / Commerce City",
     "CORRIDOR", "thornton",
     ["80221", "80229", "80233", "80241", "80260", "80602", "80022", "80640"],
     "The north I-25 / I-76 / I-270 side: Thornton, Northglenn and Federal Heights (80221 / 80229 / 80233 / 80241 "
     "/ 80260 / 80602), and Commerce City / Henderson (80022 / 80640) with Dick's Sporting Goods Park and the "
     "Rocky Mountain Arsenal refuge. Drive-market and budget lodging."),
    ("littleton-englewood", "Littleton, Englewood & Highlands Ranch", "Littleton / Englewood / Highlands Ranch / Ken Caryl",
     "CORRIDOR", "littleton",
     ["80110", "80113", "80120", "80121", "80122", "80123", "80125", "80126", "80127", "80128", "80129", "80130"],
     "The south-west metro on Santa Fe Drive, C-470 and Wadsworth: the City of Englewood (80110 / 80113), the City "
     "of Littleton and its unincorporated edges (80120-80123, 80125, 80127, 80128), Highlands Ranch (80126 / "
     "80129 / 80130) and Centennial's west side. The C-470 trailheads to Waterton Canyon and Chatfield."),
    ("boulder", "Boulder", "Boulder / Pearl Street / CU Boulder / Flatirons", "CORRIDOR", "boulder",
     ["80301", "80302", "80303", "80304", "80305", "80310"],
     "The City of Boulder: Pearl Street and downtown, the University of Colorado (80310), the Hill, Chautauqua and "
     "the Flatirons, and the Baseline / 28th Street / Diagonal hotel rows. A STRONG CORRIDOR kept as its own "
     "page (never flattened into generic Denver), and recorded as this market's named first candidate for "
     "promotion to a standalone market. DEN is its airport."),
    ("louisville-superior-lafayette", "Louisville, Superior & Lafayette", "Louisville / Superior / Lafayette",
     "CORRIDOR", "louisville", ["80026", "80027"],
     "East Boulder County on US-36 and South Boulder Road: Louisville and Superior (80027) and Lafayette (80026). "
     "Kept apart from Boulder so Boulder's page stays Boulder's; a small inventory that publishes only on its own "
     "threshold."),
    ("longmont-erie", "Longmont & Erie", "Longmont / Erie / Niwot", "FRINGE", "longmont",
     ["80501", "80503", "80504", "80516"],
     "Longmont (80501 / 80503 / 80504) and Erie (80516), north-east Boulder County on the Diagonal and I-25. The "
     "chains market Longmont as 'Boulder / Longmont'; admitted at FRINGE so the inventory is ACCOUNTED FOR rather "
     "than silently dropped, and placed by its own codes."),
    ("parker-southeast", "Parker & the Southeast Metro", "Parker / E-470 south", "FRINGE", "parker",
     ["80134", "80138"],
     "The Town of Parker (80134 / 80138) on Parker Road and E-470, contiguous with Aurora's south side. Admitted "
     "at FRINGE; Castle Rock, further south on I-25, is refused."),
    ("brighton-northeast", "Brighton & the Northeast Metro", "Brighton / US-85 / I-76", "FRINGE", "brighton",
     ["80601", "80603"],
     "The City of Brighton (80601 / 80603) on US-85 and I-76, marketed by the chains as 'Denver Northeast'. "
     "Admitted at FRINGE so the inventory is accounted for."),
]

OUTSIDE = [
    ("Colorado Springs / Pikes Peak region -- El Paso and Teller County", "CO",
     ["80132", "80133", "80829", "80863", "80809", "80817", "80831", "80840", "80841", "80901", "80902", "80903",
      "80904", "80905", "80906", "80907", "80909", "80910", "80911", "80915", "80916", "80917", "80918", "80919",
      "80920", "80921", "80922", "80923", "80924", "80925", "80927", "80938", "80939", "80951"],
     "EL PASO COUNTY; FUTURE_STANDALONE colorado-springs-co. Refused by name, county and postal prefix (808 / 809). "
     "Seventy miles south on I-25 with its own airport (COS), its own military demand (Fort Carson, Peterson, the "
     "Air Force Academy) and its own resort product (the Broadmoor, Garden of the Gods, Manitou Springs)."),
    ("Castle Rock / Douglas County south of the metro", "CO",
     ["80104", "80108", "80109", "80116", "80118", "80135"],
     "DOUGLAS COUNTY south of Lone Tree and Parker; refused by name. Castle Rock is 30 miles south on I-25, a "
     "separate town between the Denver and Colorado Springs markets (the outlets, the Rock); its hotels market "
     "themselves as 'Denver South' and their own postal code refuses them. Recorded as a possible later FRINGE "
     "extension, never absorbed here."),
    ("Fort Collins / Loveland / Windsor -- Larimer County and northern Weld", "CO",
     ["80521", "80524", "80525", "80526", "80528", "80537", "80538", "80539", "80534", "80550", "80513", "80547"],
     "LARIMER COUNTY; FUTURE_STANDALONE fort-collins-loveland-co. Refused by name and county. Sixty miles north on "
     "I-25, with Colorado State University and its own regional airport; the chains' 'Denver North' Loveland hotels "
     "are refused by their own postal code."),
    ("Greeley / Weld County plains", "CO",
     ["80631", "80634", "80620", "80615", "80642", "80643", "80651", "80530", "80520", "80504x"],
     "WELD COUNTY; refused by name. Greeley and the I-25 / US-85 plains towns are their own oil, university and "
     "agriculture market."),
    ("Estes Park / Rocky Mountain National Park", "CO",
     ["80517", "80511"],
     "LARIMER COUNTY mountain resort; FUTURE_STANDALONE estes-park-co. The gateway to Rocky Mountain National Park, "
     "70 miles from downtown -- a separate mountain-vacation market with a heavy cabin / vacation-rental share."),
    ("Mountain resort and ski markets -- Summit County, Vail Valley, Aspen, Winter Park, Steamboat", "CO",
     ["80424", "80435", "80443", "80498", "80497", "80482", "80442", "80446", "80447", "80487", "80488", "80461",
      "81620", "81657", "81658", "81611", "81612", "81615", "81601", "81632", "81631", "81637"],
     "FUTURE_STANDALONE colorado-ski-resorts (one or several markets). Breckenridge, Frisco, Silverthorne, Dillon, "
     "Keystone, Copper Mountain, Vail, Avon / Beaver Creek, Aspen / Snowmass, Winter Park / Fraser, Grand Lake, "
     "Steamboat Springs, Leadville and Glenwood Springs. Resort-and-condo markets 70-200 miles from downtown whose "
     "inventory is dominated by condo and vacation-ownership units. Refused by name; the 816 prefix by prefix."),
    ("I-70 mountain corridor and foothills towns -- Evergreen, Idaho Springs, Georgetown, Black Hawk, Central City, "
     "Nederland, Lyons", "CO",
     ["80439", "80433", "80452", "80444", "80422", "80427", "80466", "80540", "80453", "80454", "80457", "80470",
      "80421", "80438", "80476"],
     "The foothills and mountain towns west of the metro: Evergreen and Conifer, Idaho Springs and Georgetown on "
     "I-70, the Black Hawk / Central City casino towns, Nederland in Boulder Canyon and Lyons at the mouth of the "
     "St. Vrain. Mountain-weekend and casino products 20-45 minutes past the metro's edge, refused by name; "
     "Golden, Morrison and Boulder are where this market's mountain gateway stops."),
    ("Pueblo and southern Colorado", "CO",
     ["81001", "81003", "81004", "81005", "81006", "81007", "81008"],
     "PUEBLO COUNTY; refused by name and by postal prefix (810 / 811)."),
    ("Eastern plains -- Bennett, Watkins, Byers, Strasburg, Kiowa, Elizabeth", "CO",
     ["80102", "80137", "80103", "80136", "80117", "80107"],
     "The Adams, Arapahoe and Elbert County plains east of E-470. Rural highway lodging outside the metro. OUTSIDE "
     "by name."),
    ("Wyoming / Nebraska / Kansas / New Mexico / Utah", "--",
     [],
     "OUT OF STATE. Cheyenne, Laramie and every non-Colorado postal code are refused by prefix."),
]
# The 80504x placeholder above is a deliberate non-code (Longmont's 80504 is ADMITTED); strip it at load.
OUTSIDE = [(m, s, [z for z in zs if re.match(r"^\d{5}$", z)], w) for m, s, zs, w in OUTSIDE]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("808", "El Paso / Teller / Elbert County (Colorado Springs region)", "colorado-springs-co"),
    ("809", "Colorado Springs", "colorado-springs-co"),
    ("810", "Pueblo County", ""),
    ("811", "southern Colorado (Trinidad / Walsenburg / San Luis Valley)", ""),
    ("812", "southern Colorado (Canon City / Salida)", ""),
    ("813", "south-western Colorado (Durango / Cortez)", ""),
    ("814", "western Colorado (Montrose / Delta / Gunnison)", ""),
    ("815", "western Colorado (Grand Junction)", ""),
    ("816", "western Colorado mountain resorts (Glenwood / Vail / Aspen / Steamboat)", "colorado-ski-resorts"),
    ("807", "north-eastern Colorado plains (Sterling / Fort Morgan)", ""),
    ("820", "Wyoming", ""), ("821", "Wyoming", ""), ("822", "Wyoming", ""), ("823", "Wyoming", ""),
    ("824", "Wyoming", ""), ("825", "Wyoming", ""), ("826", "Wyoming", ""), ("827", "Wyoming", ""),
    ("828", "Wyoming", ""), ("829", "Wyoming", ""), ("830", "Wyoming", ""), ("831", "Wyoming", ""),
    ("690", "Nebraska", ""), ("691", "Nebraska", ""), ("693", "Nebraska", ""),
    ("677", "Kansas", ""), ("878", "New Mexico", ""), ("840", "Utah", ""),
]

#: The Front Range's own postal prefixes. A code under one of these that no corridor claims is an UNCLAIMED
#: Colorado code -- refused, and named in the boundary audit so it is visible, never silently dropped.
FRONT_RANGE_PREFIXES = ("800", "801", "802", "803", "804", "805", "806")

ADMITTED_COUNTIES = {"denver", "arapahoe", "adams", "jefferson", "douglas", "boulder", "broomfield"}
OBSERVED_COUNTIES = OrderedDict([
    ("el paso", "colorado-springs-co"),
    ("larimer", "fort-collins-loveland-co / estes-park-co"),
    ("weld", "(none -- Greeley, refused by name; Erie's Weld side is admitted with Longmont / Erie)"),
    ("summit / eagle / pitkin / grand / routt / garfield", "colorado-ski-resorts"),
    ("clear creek / gilpin", "(none -- I-70 mountain towns and Black Hawk casinos, refused by name)"),
    ("pueblo", "(none -- refused by prefix)"),
])

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("denver", OrderedDict([
        ("ruling", "ADMITTED WHOLE. The City and County of Denver's every lodging code is claimed; the airport "
                   "(80249) is its own corridor."),
    ])),
    ("arapahoe / adams / jefferson", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. The contiguous metro (Aurora, Englewood, Greenwood Village, Centennial, "
                   "Littleton, Lakewood, Wheat Ridge, Golden, Arvada, Westminster, Thornton, Northglenn, Commerce "
                   "City, Brighton) is admitted; the eastern plains (Bennett, Watkins, Byers, Strasburg) and the "
                   "Jefferson County foothills and mountains (Evergreen, Conifer, Idledale, Indian Hills) are "
                   "REFUSED by name. County inclusion is not traveller-market inclusion."),
    ])),
    ("douglas", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. Lone Tree / Park Meadows (DTC corridor), Highlands Ranch (Littleton corridor) "
                   "and Parker (FRINGE) are admitted; Castle Rock, Franktown, Larkspur and Sedalia are refused."),
    ])),
    ("boulder / broomfield", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. Boulder, Louisville, Superior, Lafayette, Broomfield, Longmont and Erie are "
                   "admitted; Nederland, Lyons and the Boulder Canyon / Peak-to-Peak mountain towns are refused."),
    ])),
    ("el paso / larimer / weld / mountain counties", OrderedDict([
        ("ruling", "REFUSED. Colorado Springs, Fort Collins / Loveland, Estes Park, Greeley and every ski-resort "
                   "county are separate markets, the first three named FUTURE_STANDALONE."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / member only).
NONPUBLIC_NAMES = {
    "buckley space force base lodging": "US Space Force billeting -- not public lodging",
    "buckley lodge": "US Space Force billeting -- not public lodging",
    "sbirs lodge": "US Space Force billeting -- not public lodging",
    "fisher house denver": "VA / military family lodging -- not public lodging",
    "fisher house": "VA / military family lodging -- not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "ronald mcdonald house of denver": "charitable family lodging -- not public lodging",
}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-lodo-union-station", "Denver", "Downtown / LoDo / Union Station", 39.7490, -104.9960, 2600, True),
    ("capitol-hill-uptown", "Denver", "Capitol Hill / Uptown", 39.7360, -104.9750, 2200, True),
    ("highlands-rino-north-denver", "Denver", "Highlands / RiNo / Globeville", 39.7700, -104.9900, 4200, True),
    ("cherry-creek-glendale", "Denver", "Cherry Creek / Glendale", 39.7120, -104.9450, 3200, True),
    ("central-park-lowry-i70", "Denver", "Central Park / Lowry / Quebec St", 39.7560, -104.9000, 4500, True),
    ("south-denver-university", "Denver", "DU / Colorado Blvd / Hampden", 39.6750, -104.9500, 7000, True),
    ("denver-tech-center", "Greenwood Village", "DTC / Park Meadows", 39.5950, -104.8850, 7000, True),
    ("den-airport", "Denver", "DEN / Tower Rd / Gaylord Rockies", 39.8250, -104.7350, 12000, True),
    ("aurora", "Aurora", "Aurora / Anschutz / Gateway Park", 39.7200, -104.8000, 12000, True),
    ("lakewood-wheat-ridge", "Lakewood", "Lakewood / Wheat Ridge", 39.7050, -105.0900, 8000, True),
    ("golden-red-rocks", "Golden", "Golden / Morrison / Red Rocks", 39.7250, -105.1950, 8000, True),
    ("arvada", "Arvada", "Arvada", 39.8150, -105.1000, 7000, True),
    ("westminster-broomfield", "Westminster", "Westminster / Broomfield / Interlocken", 39.9050, -105.0650, 9000,
     True),
    ("thornton-northglenn-north-i25", "Thornton", "Thornton / Northglenn / Commerce City", 39.8850, -104.9500,
     10000, True),
    ("littleton-englewood", "Littleton", "Littleton / Englewood / Highlands Ranch", 39.6000, -105.0200, 10000,
     True),
    ("boulder", "Boulder", "Boulder", 40.0150, -105.2600, 7000, True),
    ("louisville-superior-lafayette", "Louisville", "Louisville / Superior / Lafayette", 39.9750, -105.1250, 6000,
     True),
    ("longmont-erie", "Longmont", "Longmont / Erie", 40.1300, -105.0800, 10000, True),
    ("parker-southeast", "Parker", "Parker", 39.5200, -104.7700, 7000, True),
    ("brighton-northeast", "Brighton", "Brighton", 39.9850, -104.8150, 6000, True),
    ("obs-colorado-springs", "Colorado Springs", "Colorado Springs -- OBSERVATION ONLY (El Paso County)", 38.8600,
     -104.8000, 20000, False),
    ("obs-castle-rock", "Castle Rock", "Castle Rock -- OBSERVATION ONLY (Douglas County south)", 39.3700,
     -104.8600, 9000, False),
    ("obs-fort-collins-loveland", "Fort Collins", "Fort Collins / Loveland -- OBSERVATION ONLY (Larimer County)",
     40.4800, -105.0500, 20000, False),
    ("obs-estes-park", "Estes Park", "Estes Park -- OBSERVATION ONLY (mountain resort)", 40.3770, -105.5250, 8000,
     False),
    ("obs-i70-mountain-towns", "Idaho Springs", "Evergreen / Idaho Springs / Black Hawk -- OBSERVATION ONLY",
     39.7300, -105.4500, 20000, False),
    ("obs-summit-county", "Breckenridge", "Summit County ski resorts -- OBSERVATION ONLY", 39.5500, -106.0500,
     25000, False),
    ("obs-vail-valley", "Vail", "Vail / Beaver Creek -- OBSERVATION ONLY", 39.6300, -106.4500, 20000, False),
    ("obs-aspen", "Aspen", "Aspen / Snowmass -- OBSERVATION ONLY", 39.2000, -106.8700, 15000, False),
    ("obs-winter-park", "Winter Park", "Winter Park / Fraser -- OBSERVATION ONLY", 39.9000, -105.7800, 12000,
     False),
    ("obs-greeley", "Greeley", "Greeley -- OBSERVATION ONLY (Weld County)", 40.4200, -104.7200, 12000, False),
]

#: The Overpass / observation box. It reaches south past Colorado Springs, north past Fort Collins, west over the
#: Divide to Aspen and Vail, so the census counts what it refuses. Pueblo (38.27) and Steamboat (40.48, -106.83
#: is inside, Steamboat is not) lie at or outside the edge and are audited from the brand lanes instead.
BOUNDS = {"min_lat": 38.60, "max_lat": 40.70, "min_lng": -106.95, "max_lng": -104.40}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("LoDo / Union Station", 39.7530, -105.0000, 0.7),
    ("Colorado Convention Center", 39.7430, -104.9950, 0.5),
    ("16th Street Mall / CBD", 39.7470, -104.9920, 0.8),
    ("Auraria / Ball Arena / Empower Field", 39.7440, -105.0110, 1.4),
    ("Capitol Hill", 39.7360, -104.9790, 1.0),
    ("Uptown / City Park", 39.7440, -104.9650, 1.2),
    ("RiNo / Five Points", 39.7640, -104.9800, 1.2),
    ("Highlands", 39.7610, -105.0150, 1.6),
    ("Globeville / National Western / I-70", 39.7850, -104.9800, 1.6),
    ("Cherry Creek North", 39.7190, -104.9530, 0.8),
    ("Glendale / Colorado Blvd", 39.7050, -104.9330, 1.0),
    ("Washington Park", 39.7000, -104.9700, 1.0),
    ("Central Park / Quebec St / I-70", 39.7740, -104.9030, 1.8),
    ("Lowry", 39.7200, -104.8950, 1.4),
    ("University of Denver", 39.6780, -104.9620, 1.0),
    ("Colorado Blvd / Evans / I-25", 39.6780, -104.9400, 1.2),
    ("Hampden / I-225", 39.6530, -104.9000, 1.8),
    ("Denver Tech Center", 39.6150, -104.8930, 2.4),
    ("Greenwood Village", 39.6170, -104.9500, 2.0),
    ("Inverness / Meridian", 39.5700, -104.8600, 2.4),
    ("Park Meadows / Lone Tree", 39.5620, -104.8760, 2.0),
    ("DEN terminal / Pena Blvd", 39.8490, -104.6740, 3.0),
    ("Tower Road / DEN hotels", 39.8100, -104.7700, 2.4),
    ("40th Ave / Chambers / Montbello", 39.7780, -104.8100, 2.0),
    ("Gaylord Rockies / E-470", 39.8120, -104.7070, 2.4),
    ("Gateway Park (Aurora)", 39.7720, -104.7760, 1.6),
    ("Anschutz Medical Campus / Fitzsimons", 39.7460, -104.8380, 1.6),
    ("East Colfax (Aurora)", 39.7400, -104.8600, 2.4),
    ("Aurora Mall / I-225 / Havana", 39.7050, -104.8350, 2.4),
    ("Southlands / E-470 south", 39.6000, -104.7100, 3.0),
    ("Belmar / Lakewood", 39.7110, -105.0810, 1.4),
    ("Denver Federal Center / Union Blvd", 39.7150, -105.1250, 1.6),
    ("Denver West / Colorado Mills", 39.7370, -105.1600, 1.6),
    ("Wheat Ridge / I-70 Kipling", 39.7780, -105.1100, 1.8),
    ("Downtown Golden / Colorado School of Mines", 39.7550, -105.2210, 1.4),
    ("Red Rocks / Morrison", 39.6650, -105.2050, 2.4),
    ("Olde Town Arvada", 39.7990, -105.0800, 1.2),
    ("Westminster Blvd / the Orchard", 39.9000, -105.0600, 2.4),
    ("Interlocken / Flatiron Crossing", 39.9300, -105.1300, 2.0),
    ("Thornton / I-25 & 120th", 39.9140, -104.9850, 2.4),
    ("Northglenn / Federal Heights", 39.8900, -105.0100, 2.0),
    ("Commerce City", 39.8200, -104.9100, 3.0),
    ("Englewood / Santa Fe", 39.6500, -104.9950, 2.0),
    ("Littleton / Southwest Plaza", 39.6000, -105.0500, 3.0),
    ("Highlands Ranch", 39.5500, -104.9800, 3.0),
    ("Pearl Street / downtown Boulder", 40.0180, -105.2790, 1.0),
    ("CU Boulder / the Hill", 40.0070, -105.2700, 1.2),
    ("Boulder 28th St / Diagonal", 40.0300, -105.2550, 1.8),
    ("Chautauqua / Flatirons", 39.9990, -105.2830, 1.2),
    ("Louisville / Superior", 39.9600, -105.1500, 2.4),
    ("Lafayette", 39.9950, -105.1000, 2.0),
    ("Longmont", 40.1670, -105.1020, 4.0),
    ("Erie", 40.0500, -105.0500, 3.0),
    ("Parker", 39.5180, -104.7610, 3.0),
    ("Brighton", 39.9850, -104.8200, 3.0),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("LoDo / Union Station", re.compile(r"\b(wynkoop|wazee|blake|market|larimer|chestnut) st\b|\bunion station\b|"
                                        r"\b1[5-9]th st\b(?=.*80202)", re.I)),
    ("Colorado Convention Center", re.compile(r"\b(14th|welton|california|stout) st\b(?=.*80202)", re.I)),
    ("Auraria / Ball Arena / Empower Field", re.compile(r"\bchopper cir\b|\bauraria\b|\bmile high stadium\b", re.I)),
    ("Cherry Creek North", re.compile(r"\bclayton (ln|st)\b|\bcolumbine st\b(?=.*80206)|\bjosephine st\b(?=.*80206)|"
                                      r"\bfillmore st\b(?=.*80206)|\be (1st|2nd|3rd) ave\b(?=.*80206)", re.I)),
    ("Glendale / Colorado Blvd", re.compile(r"\bcolorado b(lv)?d\b(?=.*80246)|\bleetsdale\b|\bvirginia ave\b(?=.*80246)",
                                            re.I)),
    ("Colorado Blvd / Evans / I-25", re.compile(r"\bcolorado b(lv)?d\b(?=.*8022[24])|\bevans ave\b", re.I)),
    ("Central Park / Quebec St / I-70", re.compile(r"\bquebec st\b|\bcentral park b(lv)?d\b|\bnorthfield\b", re.I)),
    ("Tower Road / DEN hotels", re.compile(r"\btower r(oa)?d\b|\bpena b(lv)?d\b|\be 6[48]th ave\b|\byampa st\b", re.I)),
    ("40th Ave / Chambers / Montbello", re.compile(r"\bchambers r(oa)?d\b(?=.*80239)|\be 40th ave\b(?=.*80239)|"
                                                   r"\bpeoria st\b(?=.*80239)", re.I)),
    ("Gaylord Rockies / E-470", re.compile(r"\bgaylord rockies\b", re.I)),
    ("Gateway Park (Aurora)", re.compile(r"\be 40th (cir|circle|ave)\b(?=.*80011)|\bgateway park\b|\bairport b(lv)?d\b"
                                         r"(?=.*80011)", re.I)),
    ("Anschutz Medical Campus / Fitzsimons", re.compile(r"\bfitzsimons\b|\bwheeling st\b|\bmontview b(lv)?d\b(?=.*800(10|11|45))|"
                                                        r"\be 1[4-9]th (ave|pl)\b(?=.*80011)", re.I)),
    ("Denver Tech Center", re.compile(r"\btech center\b|\bdtc\b|\bs syracuse way\b|\be orchard r(oa)?d\b|"
                                      r"\bs yosemite st\b|\be belleview\b", re.I)),
    ("Inverness / Meridian", re.compile(r"\binverness\b|\bmeridian\b", re.I)),
    ("Park Meadows / Lone Tree", re.compile(r"\bpark meadows\b|\blone tree\b|\bcommons st\b|\byosemite st\b(?=.*80124)",
                                            re.I)),
    ("Belmar / Lakewood", re.compile(r"\bbelmar\b|\bw alameda ave\b(?=.*80226)", re.I)),
    ("Denver Federal Center / Union Blvd", re.compile(r"\bunion b(lv)?d\b|\bvan gordon\b", re.I)),
    ("Denver West / Colorado Mills", re.compile(r"\bdenver west\b|\bcolorado mills\b|\bindiana st\b(?=.*80401)", re.I)),
    ("Wheat Ridge / I-70 Kipling", re.compile(r"\bkipling st\b(?=.*80033)|\byoungfield\b", re.I)),
    ("Downtown Golden / Colorado School of Mines", re.compile(r"\bwashington ave\b(?=.*80401)|\b1[0-9]th st\b(?=.*80401)|"
                                                              r"\bgolden\b(?=.*80401)", re.I)),
    ("Westminster Blvd / the Orchard", re.compile(r"\bwestminster b(lv)?d\b|\bchurch ranch\b|\borchard pkwy\b", re.I)),
    ("Interlocken / Flatiron Crossing", re.compile(r"\binterlocken\b|\bflatiron\b|\barista pl\b", re.I)),
    ("Pearl Street / downtown Boulder", re.compile(r"\bpearl st\b|\bcanyon b(lv)?d\b|\bspruce st\b(?=.*8030[24])|"
                                                   r"\bwalnut st\b(?=.*80302)", re.I)),
    ("CU Boulder / the Hill", re.compile(r"\bbroadway\b(?=.*8030[25])|\bbaseline r(oa)?d\b|\bcollege ave\b(?=.*80302)",
                                         re.I)),
    ("Boulder 28th St / Diagonal", re.compile(r"\b28th st\b|\b30th st\b(?=.*8030[13])|\bdiagonal h(igh)?wy\b|"
                                              r"\bfoothills pkwy\b", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-lodo-union-station": "Downtown Denver",
    "capitol-hill-uptown": "Capitol Hill",
    "highlands-rino-north-denver": "North Denver",
    "cherry-creek-glendale": "Cherry Creek",
    "central-park-lowry-i70": "Central Park",
    "south-denver-university": "South Denver",
    "denver-tech-center": "Denver Tech Center",
    "den-airport": "DEN Airport",
    "aurora": "Aurora",
    "lakewood-wheat-ridge": "Lakewood",
    "golden-red-rocks": "Golden",
    "arvada": "Arvada",
    "westminster-broomfield": "Westminster",
    "thornton-northglenn-north-i25": "Thornton",
    "littleton-englewood": "Littleton",
    "boulder": "Boulder",
    "louisville-superior-lafayette": "Louisville",
    "longmont-erie": "Longmont",
    "parker-southeast": "Parker",
    "brighton-northeast": "Brighton",
}

#: The order's REQUIRED / STRONG evaluation list, each classified explicitly.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Denver", "ADMITTED (CORE, downtown-lodo-union-station, 80202 / 80204 and the building codes). PRIMARY."),
    ("LoDo / Union Station", "ADMITTED (CORE, downtown-lodo-union-station, 80202) as an OVERLAY -- 80202 is never "
                             "split. PRIMARY."),
    ("Capitol Hill", "ADMITTED (CORE, capitol-hill-uptown, 80203 / 80218). PRIMARY."),
    ("Cherry Creek", "ADMITTED (CORE, cherry-creek-glendale, 80206 / 80209 / 80246). PRIMARY."),
    ("Denver Tech Center / DTC", "ADMITTED (CORE, denver-tech-center, 80237 / 80111 / 80112 / 80124). PRIMARY."),
    ("Denver International Airport / DEN", "ADMITTED (CORE, den-airport, 80249 / 80239 / 80019); Gateway Park "
                                           "(Aurora 80011) is an overlay of aurora. PRIMARY."),
    ("Aurora", "ADMITTED (CORE, aurora, 80010-80018 / 80045 / 80247). PRIMARY."),
    ("Lakewood", "ADMITTED (CORE, lakewood-wheat-ridge). PRIMARY."),
    ("Golden", "ADMITTED (STRONG CORRIDOR, golden-red-rocks, 80401 / 80403 / 80419 / 80465). PRIMARY."),
    ("Arvada", "ADMITTED (CORRIDOR, arvada, 80002-80007). PRIMARY."),
    ("Westminster", "ADMITTED (CORRIDOR, westminster-broomfield) -- shares 80020 / 80021 with Broomfield. PRIMARY."),
    ("Littleton", "ADMITTED (CORRIDOR, littleton-englewood). PRIMARY."),
    ("Englewood", "ADMITTED (CORRIDOR, littleton-englewood, 80110 / 80113); the DTC's 80112 'Englewood' is the "
                  "denver-tech-center corridor. PRIMARY."),
    ("Boulder", "ADMITTED (STRONG CORRIDOR, boulder, 80301-80305 / 80310), its own corridor. PRIMARY -- see "
                "boulder_ruling."),
    ("Broomfield", "ADMITTED (CORRIDOR, westminster-broomfield, 80020 / 80021 / 80023 / 80038). STRONG."),
    ("Louisville", "ADMITTED (CORRIDOR, louisville-superior-lafayette, 80027). STRONG."),
    ("Superior", "ADMITTED (CORRIDOR, louisville-superior-lafayette, 80027). STRONG."),
    ("Lafayette", "ADMITTED (CORRIDOR, louisville-superior-lafayette, 80026). STRONG."),
    ("Centennial", "ADMITTED -- split by its own codes: 80112 (DTC), 80121 / 80122 (littleton-englewood), 80015 / "
                   "80016 (aurora). STRONG."),
    ("Greenwood Village", "ADMITTED (CORE, denver-tech-center, 80111). STRONG."),
    ("Wheat Ridge", "ADMITTED (CORE, lakewood-wheat-ridge, 80033 / 80034). STRONG."),
    ("Thornton", "ADMITTED (CORRIDOR, thornton-northglenn-north-i25). STRONG."),
    ("Northglenn", "ADMITTED (CORRIDOR, thornton-northglenn-north-i25, 80233 / 80260). STRONG."),
    ("Longmont / Erie", "ADMITTED (FRINGE, longmont-erie). Not on the order's list; admitted so the chains' "
                        "'Boulder / Longmont' inventory is accounted for, not silently dropped."),
    ("Parker", "ADMITTED (FRINGE, parker-southeast). Not on the order's list; contiguous with Aurora."),
    ("Brighton", "ADMITTED (FRINGE, brighton-northeast). Not on the order's list; marketed as 'Denver Northeast'."),
    ("Castle Rock", "OUTSIDE -- Douglas County south of the metro, between two markets. CAREFUL."),
    ("Fort Collins", "OUTSIDE -- FUTURE_STANDALONE fort-collins-loveland-co. CAREFUL."),
    ("Loveland", "OUTSIDE -- FUTURE_STANDALONE fort-collins-loveland-co."),
    ("Colorado Springs", "OUTSIDE -- FUTURE_STANDALONE colorado-springs-co. CAREFUL."),
    ("Estes Park", "OUTSIDE -- FUTURE_STANDALONE estes-park-co. CAREFUL."),
    ("Breckenridge", "OUTSIDE -- FUTURE_STANDALONE colorado-ski-resorts. CAREFUL."),
    ("Vail", "OUTSIDE -- FUTURE_STANDALONE colorado-ski-resorts. CAREFUL."),
    ("Aspen", "OUTSIDE -- FUTURE_STANDALONE colorado-ski-resorts. CAREFUL."),
    ("Winter Park", "OUTSIDE -- FUTURE_STANDALONE colorado-ski-resorts. CAREFUL."),
    ("Pueblo", "OUTSIDE by name and prefix."),
    ("Evergreen / Idaho Springs / Black Hawk / Nederland / Lyons", "OUTSIDE by name (mountain towns / casinos)."),
    ("Greeley", "OUTSIDE by name."),
])

BOULDER_RULING = OrderedDict([
    ("classification", "STRONG CORRIDOR (registry class CORRIDOR), its own corridor 'boulder'"),
    ("hotel_inventory", "A city inventory of its own -- CU's conference hotels, downtown's Pearl Street boutiques "
                        "and the Baseline / 28th Street / Diagonal chains -- enough to publish a page on its own, not "
                        "enough to make a standalone market anything but thin today."),
    ("traveller_intent", "University (CU Boulder), the Flatirons, Chautauqua, Boulder Creek and the open-space "
                         "trail system: an outdoor-and-university intent distinct from downtown Denver's "
                         "convention, sports and business demand -- which is why it is NOT flattened into Denver."),
    ("drive_pattern", "25 miles on US-36 (Flatiron Flyer BRT), inside the metro commute shed; Interlocken and "
                      "Louisville between the two are continuous development."),
    ("airport_relation", "No commercial airport. Every flying visitor arrives through DEN -- the decisive reason it "
                         "is inside the Denver traveller market rather than FUTURE_STANDALONE."),
    ("outdoor_pet_travel_relevance", "The highest in the metro. It shapes the CENSUS (Boulder keeps its own cell and "
                                     "corridor) and never an evidence standard."),
    ("corridor_coherence", "One city with its own postal codes (80301-80305, 80310), none shared with Denver or "
                           "with Louisville / Superior / Lafayette, which keep their own corridor."),
    ("not_core_because", "A separate city 25 miles from downtown with its own traveller product."),
    ("not_fringe_because", "Its intent is a destination in its own right, not overflow."),
    ("not_future_standalone_because", "DEN is its airport and its inventory is a page, not yet a market."),
    ("named_optionality", "Recorded as this market's first candidate for promotion to a standalone boulder-co market."),
])

STRUCTURE_TEST = OrderedDict([
    ("A. Is Denver one market, or several?",
     "ONE market, denver-co, covering the contiguous Denver metro from Brighton to Parker and Highlands Ranch, and "
     "from DEN to Golden, plus Boulder County's US-36 cities. One commercial airport (DEN) serving the whole Front "
     "Range metro, one I-25 / I-70 / I-225 / I-270 / C-470 / E-470 / US-36 road system, one RTD transit system. "
     "Castle Rock and the Palmer Divide are where that coherence stops in the south; Fort Collins / Loveland in the "
     "north; the foothills in the west; E-470 and the plains in the east."),
    ("B. The City of Denver is NOT the market -- and 'Denver' places nothing",
     "Twenty-odd municipalities are admitted by their own codes; the chains' 'Denver' prefix is on hotels from "
     "Loveland to Castle Rock."),
    ("C. DEN", "The airport owns its postal code (80249) and has its own lodging system -- its own CORE corridor."),
    ("D. Convention Center / Union Station", "NO CORRIDOR of their own -- both are 80202, overlays of downtown."),
    ("E. Anschutz Medical Campus", "An overlay of aurora (80045 and its 80010 / 80011 edges)."),
    ("F. Boulder", "STRONG CORRIDOR, its own corridor; see boulder_ruling."),
    ("G. Mountain gateway", "Golden and Morrison / Red Rocks are ADMITTED (golden-red-rocks); the mountain towns and "
                            "resorts are OUTSIDE."),
    ("H. Colorado Springs", "OUTSIDE -- FUTURE_STANDALONE colorado-springs-co."),
    ("I. Fort Collins / Loveland", "OUTSIDE -- FUTURE_STANDALONE fort-collins-loveland-co."),
    ("J. Estes Park", "OUTSIDE -- FUTURE_STANDALONE estes-park-co."),
    ("K. Ski resorts", "OUTSIDE -- FUTURE_STANDALONE colorado-ski-resorts."),
    ("L. Castle Rock", "OUTSIDE by name; a possible later FRINGE extension recorded."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel operation."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP). A unit designator ('Ste', "
     "'Unit', '#', 'Apt', 'PH') in a registry address means the record is a UNIT INSIDE a building, which is never "
     "a hotel identity."),
    ("hotel_vs_residence_boundary",
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. Denver's "
     "specific exposures: the downtown and Union Station apartment-hotel and serviced-apartment operators "
     "(Sonder, Mint House, Kasa, Stay Alfred-style portfolios), the Four Seasons / Ritz-Carlton / Halcyon "
     "private residences, Boulder's university-area short-term rentals, and the mountain-access condo inventory "
     "west of the metro (which is OUTSIDE by geography anyway)."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort is admitted ONLY if the operator's own page sells nightly "
     "public stays at that premises under a public hotel name. Owner-only / member-only / points-only resorts and "
     "individual timeshare units are TIMESHARE and are never admitted."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared "
     "amenities or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never "
     "published as one."),
    ("extended_stay",
     "Extended-stay hotels are hotels and are admitted on their own pages; an 'apartment hotel' is admitted only "
     "as a public hotel operation at an exact premises."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("80202", ["Downtown", "LoDo", "Union Station", "Convention Center", "16th Street Mall"]),
    ("80204", ["Auraria", "Ball Arena", "Empower Field", "Lincoln Park", "West Colfax"]),
    ("80011", ["Aurora", "Gateway Park ('Denver Airport')", "Anschutz / Fitzsimons edge", "East Colfax"]),
    ("80112", ["Englewood (postal city)", "Centennial", "DTC south / Inverness / Meridian"]),
    ("80020", ["Broomfield", "Westminster"]),
    ("80021", ["Broomfield (Interlocken)", "Westminster (Church Ranch)"]),
    ("80027", ["Louisville", "Superior"]),
    ("80246", ["Glendale", "(postal city Denver)"]),
    ("80401", ["Golden", "Denver West (Lakewood side, postal city Golden)"]),
])

FUTURE_MARKETS = OrderedDict([
    ("colorado-springs-co", "Colorado Springs / Pikes Peak -- 70 miles south, its own airport, military and resort "
                            "demand."),
    ("fort-collins-loveland-co", "Fort Collins / Loveland -- 60 miles north, CSU, its own regional airport."),
    ("estes-park-co", "Estes Park / Rocky Mountain National Park -- the park gateway."),
    ("colorado-ski-resorts", "Summit County, Vail Valley, Aspen / Snowmass, Winter Park, Steamboat -- one or several "
                             "resort markets dominated by condo and vacation-ownership inventory."),
    ("boulder-co", "NAMED OPTIONALITY, not a refusal. Boulder is ADMITTED here at CORRIDOR tier and recorded as this "
                   "market's first candidate for promotion to a standalone market."),
])

#: Markets that are ALREADY LIVE. None of them owns a Colorado postal code; named so the collision guards know the
#: only exposure is NAME, never premises.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("san-diego-ca", "San Diego / Coastal San Diego County, live as production market #35 (deploy "
                     "6ab859787d349f8397e1450a) -- the CURRENT LIVE market at this order's authoring time. No live "
                     "market owns a Colorado postal code; the only cross-market exposure is a shared chain NAME, "
                     "which rule G and the bare-chain test guard."),
])

#: A shared postal code whose OTHER town is refused: 80504 is Longmont's east side AND the Weld County towns of
#: Firestone, Frederick and Dacono (the Carbon Valley), which are refused with Greeley's plains. The property's own
#: stated town decides inside that code.
MUNICIPALITY_REFUSALS = [
    ("80504", "firestone", "Firestone (Weld County, Carbon Valley) shares Longmont's 80504 and is refused by name"),
    ("80504", "frederick", "Frederick (Weld County, Carbon Valley) shares Longmont's 80504 and is refused by name"),
    ("80504", "dacono", "Dacono (Weld County, Carbon Valley) shares Longmont's 80504 and is refused by name"),
]
MUNICIPALITY_SPELLINGS = {
    "denver,": "denver", "denver co": "denver", "denver, co": "denver", "dnv": "denver",
    "glendale,": "glendale", "aurora,": "aurora", "lakewood,": "lakewood", "golden,": "golden",
    "arvada,": "arvada", "westminster,": "westminster", "broomfield,": "broomfield", "thornton,": "thornton",
    "northglenn,": "northglenn", "federal hts": "federal heights", "commerce cty": "commerce city",
    "littleton,": "littleton", "englewood,": "englewood", "centennial,": "centennial",
    "greenwood vlg": "greenwood village", "greenwood village,": "greenwood village",
    "lone tree,": "lone tree", "highlands ranch,": "highlands ranch", "wheat ridge,": "wheat ridge",
    "wheatridge": "wheat ridge", "boulder,": "boulder", "louisville,": "louisville", "superior,": "superior",
    "lafayette,": "lafayette", "longmont,": "longmont", "erie,": "erie", "parker,": "parker",
    "brighton,": "brighton", "morrison,": "morrison",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("80202", "Downtown / LoDo / Union Station / Convention Center -- one postal code, never split."),
    ("80249", "DEN -- the airport owns its code; Tower Road and Pena Boulevard."),
    ("80011", "Aurora -- Gateway Park ('Denver Airport') and the Anschutz edge share one code; Aurora's."),
    ("80237", "Denver's share of the DTC; 80111 Greenwood Village and 80112 Centennial / Englewood are the rest."),
    ("80401", "Golden -- including the Denver West hotels whose postal city is Golden."),
    ("80301", "Boulder -- the 28th Street / Diagonal chains; 80302 is downtown and Pearl Street."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Denver" % name),
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
            ("state_code", "CO"),
            ("geography_class", klass),
        ]))
    outside_zips = {z for _m, _s, zs, _w in OUTSIDE for z in zs}
    overlap = outside_zips & set(seen_zip)
    if overlap:
        raise SystemExit("postal codes both admitted and refused: %s" % sorted(overlap))
    prefix_overlap = [z for z in seen_zip if any(z.startswith(p) for p, _n, _f in OUTSIDE_PREFIXES)]
    if prefix_overlap:
        raise SystemExit("admitted postal codes under a refused prefix: %s" % sorted(prefix_overlap))
    stray = [z for z in seen_zip if not z.startswith(FRONT_RANGE_PREFIXES)]
    if stray:
        raise SystemExit("admitted postal codes outside the Front Range prefixes: %s" % stray)

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius), ("state_code", "CO"),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Denver / Boulder / Front Range city, airport, mountain-gateway and business lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", "CO"),
        ("states", ["CO"]),
        ("country", "US"),
        ("market_center", {"lat": 39.74, "lng": -104.99}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past Colorado Springs, north past Fort "
             "Collins and west over the Continental Divide to Vail and Aspen, so that " + WORK_ORDER + " classifies "
             "those properties on evidence instead of being blind to them. Admission is decided by the corridor "
             "registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Denver / Boulder / Front Range is ONE market: ten CORE corridors over Denver's traveller "
         "districts, DEN, Aurora, the DTC and Lakewood; seven CORRIDOR tiers (Golden / Red Rocks, Arvada, "
         "Westminster / Broomfield, Thornton / North I-25, Littleton / Englewood, Boulder, Louisville / Superior / "
         "Lafayette) and three FRINGE corridors (Longmont / Erie, Parker, Brighton). COLORADO SPRINGS, FORT "
         "COLLINS / LOVELAND, ESTES PARK and the SKI RESORTS are refused as future standalone markets; Castle Rock, "
         "the mountain towns, Greeley, Pueblo and the plains are refused by name."),
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
        ("market_name", "Denver, Colorado"),
        ("market_slug", MARKET_ID),
        ("state_name", "Colorado"),
        ("state_code", "CO"),
        ("primary_state_code", "CO"),
        ("states", ["CO"]),
        ("primary_city", "Denver"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Denver, Boulder & the Front Range | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Denver, Boulder and the Front Range -- downtown and LoDo, Capitol "
         "Hill, Cherry Creek, DEN airport, Aurora, the Denver Tech Center, Lakewood, Golden and Red Rocks, "
         "Westminster, Broomfield and Boulder -- with real pet fees and policies read from each hotel's own "
         "official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Denver"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry. A Denver city, airport, mountain-gateway and business travel "
         "market -- the contiguous metro from Brighton to Parker and from DEN to Golden, plus Boulder County's US-36 "
         "cities. Not 'the Front Range': Colorado Springs, Fort Collins / Loveland, Estes Park and the ski resorts "
         "are future standalone markets; Castle Rock, the mountain towns and the plains are refused. Nothing else "
         "admits a property: not a brand's 'Denver' marketing name, not a map pin, not a vacation-rental listing, "
         "not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). The postal city "
         "'DENVER' spans the city and several neighbours and places nothing by itself. Shared codes are covered "
         "whole: 80202 by Downtown, LoDo, Union Station and the Convention Center; 80011 by Aurora, Gateway Park and "
         "the Anschutz edge; 80020 / 80021 by Westminster and Broomfield; 80027 by Louisville and Superior. Union "
         "Station, the Convention Center, Anschutz, Red Rocks, Park Meadows and Interlocken are overlays."),
        ("_census_membership_note",
         "Individual condominium units, vacation homes, property-management portfolios, Airbnb / Vrbo inventory, "
         "Denver short-term-rental licences, ordinary apartments, individual timeshare units, owner-only "
         "vacation-ownership resorts, private residences, member-only club lodging and government billeting are "
         "never admitted. A mixed hotel / condo / residence property is admitted only as the exact hotel premises "
         "its public operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 + 6 -- Denver / Boulder / Front Range travel-market geography, the Boulder ruling, "
                  "mountain access, the airport / business / medical / event test and the resort / condo / "
                  "extended-stay safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/denver-co.json. This order "
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
        ("boulder_ruling", BOULDER_RULING),
        ("denver_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("pet_travel_relevance",
         "Denver was selected as a high-value pet-travel and road-trip market. That lowers NO evidence standard: no "
         "destination reputation ('dog-friendly city', Colorado's outdoor culture, the dog parks, the trails) is "
         "ever policy evidence. It shapes only the CENSUS: every mountain-gateway (Golden, Morrison, Boulder), "
         "trail-access (C-470, Chatfield, Boulder open space), long-stay / extended-stay, airport-arrival and "
         "road-trip (I-70, I-25, I-76 and E-470 exits) lodging cluster the traveller geography names is covered by "
         "an admitting cell and an overlay."),
        ("the_denver_name_trap",
         "The chains put 'Denver' on hotels from Loveland to Castle Rock and 'Boulder' on hotels in Longmont and "
         "Broomfield; 'Denver Tech Center' spans three cities; 'Denver Airport' spans Denver 80249 / 80239 and "
         "Aurora 80011 / 80019. A property's own postal code, street and brand property code decide what and where "
         "it is; none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Denver International Airport (DEN)",
             "its own corridor den-airport (80249 / 80239 / 80019); overlay on aurora's Gateway Park rows (80011)."),
            ("Colorado Convention Center", "downtown-lodo-union-station (80202) -- overlay."),
            ("Union Station / LoDo", "downtown-lodo-union-station (80202) -- overlay."),
            ("Coors Field / Ball Arena / Empower Field", "downtown-lodo-union-station (80202 / 80204) -- overlays."),
            ("Denver Tech Center", "denver-tech-center -- its own corridor."),
            ("Anschutz Medical Campus / Children's Hospital Colorado / UCHealth", "aurora (80045 / 80010 / 80011) -- "
                                                                                  "overlay."),
            ("Cherry Creek", "cherry-creek-glendale -- its own corridor."),
            ("Golden / Red Rocks / I-70 mountain gateway", "golden-red-rocks -- its own corridor."),
            ("University of Colorado Boulder", "boulder (80310) -- overlay."),
            ("University of Denver", "south-denver-university (80210) -- overlay."),
            ("Gaylord Rockies convention resort", "den-airport (80019) -- overlay."),
            ("Park Meadows / Lone Tree", "denver-tech-center (80124) -- overlay."),
            ("Interlocken / Flatiron Crossing", "westminster-broomfield (80021) -- overlay."),
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
        ("first_colorado_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, mountain, ski or "
         "stadium keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration "
         "order publishes it."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, public resorts, qualifying condo-hotels with a distinct public hotel "
         "operation, qualifying extended-stay hotels and other public lodging establishments: bookable nightly rooms "
         "or suites sold to the public under one establishment name, with an official property page and an on-site "
         "hotel operation. It NEVER admits: individual condominium units; vacation homes, cabins or villas; "
         "property-management / short-term-rental portfolios; Airbnb / Vrbo listings; Denver short-term-rental "
         "licences; ordinary apartments; individual timeshare units or owner-only vacation-ownership resorts; "
         "private residences; member-only club lodging; government billeting; and privately managed units inside "
         "hotel-condo towers. Campgrounds, RV parks and hostels are NON_LODGING."),
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
    if z.startswith(FRONT_RANGE_PREFIXES):
        return "OUTSIDE", None, "Front Range postal code %r is claimed by no corridor" % z
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
