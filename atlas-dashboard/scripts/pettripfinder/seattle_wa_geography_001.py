"""PTF-SEATTLE-WA-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4 and 5: the Seattle / Bellevue / Puget Sound market.

Built from zero on the CURRENT hardened lineage: the San Antonio-live release 5bd54304 (live lineage commit 60683902,
built_from be83dab2). Current verified live at authoring time = san-antonio-tx deploy 6ac064cd6a4261e60054a2f3, 39
markets / 3,530 profiles / 3,894 release-index routes / 3,966 served routes, host verified (release_index live-source
--fetch --verify-host). No earlier Seattle build exists. It is the FIRST Washington market: no live market admits a
Washington postal code, and the build refuses to admit any code a registered market already admits.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Seattle / Bellevue / Puget Sound traveller lodging market -- not the municipal City of Seattle, and not
"Puget Sound" as a whole -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE
markets named inside OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact
to make a number. The order's "STRONG_CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property card)
states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP
is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing
name never admits and never places a property.

WHY "SEATTLE" DECIDES NOTHING HERE (PHASE 3 -- AIRPORT / EASTSIDE IDENTITY)
--------------------------------------------------------------------------
The chains put "Seattle" on hotels in SeaTac, Tukwila, Renton, Bellevue, Redmond, Bothell, Lynnwood, Everett,
Federal Way, Fife and Tacoma: "Seattle Airport" on International Boulevard hotels in SeaTac 98188 / 98198,
"Seattle/Southcenter" on Tukwila 98188 hotels, "Seattle/Bellevue" and "Seattle Eastside" on Bellevue and Redmond
hotels, "Seattle/Renton" on Renton hotels, "Seattle North" / "Seattle/Lynnwood" / "Seattle-Everett" on Snohomish
County hotels and "Seattle/Tacoma" or "Seattle-Fife" on Pierce County hotels. "Bellevue" on a hotel name never makes
it a Bellevue hotel either. A property's own street and postal code place it; its name never does -- a Fife hotel
titled "Seattle-Tacoma" is a Pierce County hotel and is refused, and a Tukwila hotel titled "Seattle Airport" is an
airport-corridor hotel only because 98188 is.

THE PUGET SOUND BOUNDARY (PHASE 2)
---------------------------------
Seattle does not silently absorb Puget Sound. TACOMA / PIERCE COUNTY (983 / 984: Tacoma, Fife, Lakewood, Puyallup,
Gig Harbor, JBLM), OLYMPIA / THURSTON (985), EVERETT and the rest of SNOHOMISH COUNTY north of Lynnwood / Bothell
(982: Everett, Mukilteo, Mill Creek's north side, Marysville, Lake Stevens, Snohomish, Monroe), BELLINGHAM /
WHATCOM / SKAGIT / WHIDBEY / the SAN JUANS (982), and KITSAP / BREMERTON / BAINBRIDGE ISLAND / the OLYMPIC
PENINSULA (983 and 98110) are refused, each named with its future market. The outer King County ring -- Auburn,
Covington, Maple Valley, Black Diamond, Enumclaw, Sammamish, Snoqualmie, North Bend, Fall City, Carnation, Duvall and
Vashon Island -- is refused by name after careful evaluation. A founder can move any of them on the record; this
order does not.

TRAVELLER-MARKET LOGIC
----------------------
Seattle is a downtown / Pike Place / waterfront tourism, cruise (Pier 66 / Pier 91), convention (the Seattle
Convention Center's Arch and Summit buildings), stadium (Lumen Field / T-Mobile Park / Climate Pledge Arena), tech
and corporate (South Lake Union, Bellevue, Redmond, Kirkland), university (UW), medical (First Hill, UW Medical,
Fred Hutch, Seattle Children's), airport (SEA), extended-stay and Eastside-business lodging market on I-5 / I-405 /
I-90 / SR-520 / SR-99. That lowers NO evidence standard: no destination reputation ("dog-friendly Seattle") is ever
policy evidence. It shapes only the CENSUS: every tourist, cruise, convention, stadium, corporate, university,
medical, airport and extended-stay cluster is covered by an admitting corridor.

RESIDENCE / APARTMENT / VACATION-RENTAL SAFETY (PHASE 4)
-------------------------------------------------------
Qualifying public hotels are admitted on their own pages. Individual condo units, private residences, Airbnb /
Vrbo units, ordinary apartments, corporate-housing and property-management portfolios, serviced-apartment and
aparthotel operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Lark, Barsala, Zeus, Furnished Finder,
Oakwood / corporate housing) and timeshare / vacation-club inventory (WorldMark / Club Wyndham The Camlin, Hilton
Grand Vacations, Marriott Vacation Club, Holiday Inn Club Vacations, Bluegreen) are never admitted, even when they
accept short stays; a mixed property is admitted only as the exact hotel premises its public operator sells. Patient
and charitable housing (Pete Gross House, the Fred Hutch / SCCA House, Ronald McDonald House, Fisher House) is
never public lodging. Phoenix's lesson is carried as a RULE: a vacation-club resort is TIMESHARE even when its brand
lists it beside its hotels and even when a pet-policy page exists.

MILITARY / GOVERNMENT LODGING
-----------------------------
No military installation owns an admitted postal code: Joint Base Lewis-McChord (Pierce County), Naval Station
Everett and Naval Base Kitsap lie in refused regions. The on-base names are still refused wherever they appear
(NONPUBLIC_NAMES).

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/seattle_wa.json
  launch_packages/pettripfinder/markets/proposed/seattle-wa.json
  launch_packages/pettripfinder/markets/reports/seattle_wa_geography_001.json
  launch_packages/pettripfinder/markets/reports/seattle_wa_corridor_registry_001.json
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

WORK_ORDER = "PTF-SEATTLE-WA-HARDENED-SOURCE-READY-001"
MARKET_ID = "seattle-wa"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "seattle_wa.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "seattle-wa.json")
REPORT_OUT = os.path.join(REPORTS, "seattle_wa_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "seattle_wa_corridor_registry_001.json")
#: Every REGISTERED market's own document: no postal code any of them admits may be admitted here.
REGISTERED_MARKETS_GLOB = os.path.join(PKG, "markets", "*.json")
AS_OF = "2026-10-03"
STATE_CODE = "WA"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
#: The order's REQUIRED evaluation areas are CORE, its STRONG evaluation areas are CORRIDOR and its CAREFUL
#: evaluation areas are FRINGE (or covered whole inside a CORE code they share).
CORRIDORS = [
    # ---------------------------------------------------------------- CORE (Seattle)
    ("downtown-waterfront", "Downtown, Pike Place & Waterfront", "Downtown / Pike Place Market / Waterfront / "
     "Belltown / Pioneer Square / Chinatown-International District / Convention Center / Stadiums", "CORE",
     "seattle", ["98101", "98104", "98121", "98134", "98154", "98161", "98164", "98174"],
     "Downtown Seattle's central business district and retail core (98101) -- Pike Place Market, the Seattle "
     "Convention Center's Arch and Summit buildings, Westlake -- with Pioneer Square, the Chinatown-International "
     "District and the south end of First Hill (98104), Belltown, the Edgewater and the Pier 66 cruise terminal on "
     "the waterfront (98121), the stadium district and SoDo (98134: Lumen Field / T-Mobile Park), and the single-"
     "building downtown codes (98154 / 98161 / 98164 / 98174). Pike Place, the Waterfront and the Convention Center "
     "are OVERLAYS, never split codes."),
    ("seattle-center-slu", "Seattle Center, Queen Anne & South Lake Union", "Seattle Center / Space Needle / Lower "
     "Queen Anne / Queen Anne Hill / South Lake Union / Westlake / Interbay / Magnolia / Pier 91", "CORE", "seattle",
     ["98109", "98119", "98199"],
     "Seattle Center, the Space Needle and Climate Pledge Arena, Lower Queen Anne, South Lake Union (Amazon, the "
     "life-science campuses, Fred Hutch) and Westlake / Eastlake's south end -- all one postal code, 98109, never "
     "split -- with Queen Anne Hill and Interbay (98119) and Magnolia and the Smith Cove / Pier 91 cruise terminal "
     "(98199). Seattle Center / Queen Anne and South Lake Union are reported as OVERLAYS of this corridor."),
    ("capitol-hill-central", "Capitol Hill, First Hill & Central Seattle", "Capitol Hill / First Hill / Eastlake / "
     "Madison Park / Central District / Mount Baker / Beacon Hill", "CORE", "seattle",
     ["98102", "98112", "98122", "98144"],
     "Capitol Hill and Eastlake (98102), north Capitol Hill, Madison Park and Montlake (98112), the medical First "
     "Hill / Pill Hill, south Capitol Hill and the Central District (98122: Swedish, Harborview, Virginia Mason, "
     "Seattle University) and Mount Baker / North Beacon Hill (98144)."),
    ("university-district", "University District", "University District / University of Washington / University "
     "Village / Laurelhurst", "CORE", "seattle", ["98105", "98195"],
     "The University District, University Village and Laurelhurst (98105) and the University of Washington campus "
     "and UW Medical Center (98195). University and medical demand."),
    ("ballard-fremont", "Ballard, Fremont & Green Lake", "Ballard / Fremont / Wallingford / Green Lake / Phinney "
     "Ridge / Crown Hill", "CORE", "seattle", ["98103", "98107", "98117"],
     "Fremont, Wallingford, Green Lake, Phinney Ridge and the south end of the Aurora Avenue North motel strip "
     "(98103), Ballard and the Ballard Locks (98107) and north-west Ballard / Crown Hill (98117)."),
    ("north-seattle", "North Seattle, Northgate & Aurora", "Northgate / Lake City / Ravenna / Wedgwood / Aurora "
     "Avenue North / Bitter Lake", "CORE", "seattle", ["98115", "98125", "98133"],
     "Ravenna, Roosevelt, Wedgwood and View Ridge (98115), Northgate and Lake City (98125), and Bitter Lake / Haller "
     "Lake and the Aurora Avenue North (SR-99) motel corridor (98133). 98133 also carries the City of Shoreline's "
     "south side and is covered whole."),
    ("south-west-seattle", "West Seattle, Georgetown & South Seattle", "West Seattle / Alki / Delridge / Georgetown "
     "/ Boeing Field / Columbia City / Rainier Valley / Seward Park", "CORE", "seattle",
     ["98106", "98108", "98116", "98118", "98126", "98136"],
     "West Seattle, Alki and Fauntleroy (98116 / 98126 / 98136), Delridge, Highland Park and South Park (98106), "
     "Georgetown, South Beacon Hill and the King County International Airport / Boeing Field and Museum of Flight "
     "edge (98108; shared with Tukwila's north end and covered whole), and Columbia City, Rainier Beach and the "
     "Rainier Valley (98118). Inside the municipal market; never left unclaimed."),
    # ---------------------------------------------------------------- CORE (airport)
    ("sea-airport", "SEA Airport, SeaTac & Tukwila", "Seattle-Tacoma International Airport / International Blvd / "
     "SeaTac / Tukwila / Southcenter / Des Moines north", "CORE", "seatac",
     ["98158", "98188", "98198", "98168", "98148"],
     "Seattle-Tacoma International Airport's own lodging system: the airport itself (98158), the International "
     "Boulevard (SR-99) hotel row and Cedarbrook in SeaTac and the Southcenter / Tukwila Parkway / Andover Park hotel "
     "cluster in Tukwila (98188 -- one postal code shared by SeaTac and Tukwila, never split), SeaTac's south side "
     "and northern Des Moines (98198), Tukwila International Boulevard and Boulevard Park (98168) and the Burien / "
     "SeaTac / Normandy Park side of the airport (98148). SEA and TUKWILA are reported as OVERLAYS (by the "
     "property's own municipality). A hotel marketed 'Seattle Airport' whose own code is elsewhere is placed by "
     "that code."),
    # ---------------------------------------------------------------- CORE (Eastside, REQUIRED evaluation)
    ("bellevue", "Bellevue", "Downtown Bellevue / Bellevue Square / Wilburton / Crossroads / Eastgate / Factoria / "
     "Bel-Red / Overlake south", "CORE", "bellevue", ["98004", "98005", "98006", "98007", "98008"],
     "Downtown Bellevue, Bellevue Square, Meydenbauer Center and the NE 8th Street / 108th / 112th Avenue NE hotel "
     "cluster (98004), Wilburton and Bel-Red (98005), Factoria, Eastgate and Newport Hills on I-90 (98006), "
     "Crossroads (98007) and Lake Hills / the Overlake side (98008). The Eastside's corporate and convention "
     "centre."),
    ("redmond", "Redmond", "Redmond / Overlake / Microsoft / Redmond Town Center / Marymoor", "CORE", "redmond",
     ["98052", "98053"],
     "The City of Redmond: Overlake and the Microsoft campus, Redmond Town Center, downtown Redmond and Marymoor "
     "Park (98052), and east Redmond / Union Hill (98053). A hotel titled 'Seattle/Redmond' or 'Bellevue/Redmond' is "
     "placed by its own code."),
    ("kirkland", "Kirkland", "Kirkland / Totem Lake / Juanita / Houghton / Carillon Point", "CORE", "kirkland",
     ["98033", "98034"],
     "Downtown Kirkland, the Lake Washington waterfront and Carillon Point (98033), Totem Lake and Juanita on I-405 "
     "(98034)."),
    ("renton", "Renton", "Renton / The Landing / Boeing Renton / Valley Medical / Newcastle / Skyway", "CORE",
     "renton", ["98055", "98056", "98057", "98058", "98059", "98178"],
     "The City of Renton: the Landing and Boeing's Renton plant (98055 / 98056 / 98057), Valley Medical Center and "
     "the Benson Hill / Fairwood side (98055 / 98058), Newcastle and East Renton Highlands (98056 / 98059), and "
     "Skyway / Bryn Mawr and Tukwila's east edge (98178, covered whole). A hotel titled 'Seattle/Renton' is placed by "
     "its own code."),
    # ---------------------------------------------------------------- STRONG CORRIDOR
    ("bothell-kenmore", "Bothell & Kenmore", "Bothell / Canyon Park / North Creek / UW Bothell / Kenmore / Mill "
     "Creek south", "CORRIDOR", "bothell", ["98011", "98012", "98021", "98028"],
     "The City of Bothell on both sides of the King / Snohomish county line -- downtown and UW Bothell (98011), the "
     "Canyon Park / North Creek I-405 business-park hotels (98021 / 98012; 98012 is shared with Mill Creek and "
     "covered whole) -- and Kenmore at the north end of Lake Washington (98028). STRONG."),
    ("lynnwood", "Lynnwood", "Lynnwood / Alderwood / I-5 at 196th St SW / Brier", "CORRIDOR", "lynnwood",
     ["98036", "98037", "98087"],
     "The City of Lynnwood: Alderwood Mall, the Lynnwood Convention Center and the I-5 / 196th Street SW / 44th "
     "Avenue W hotel cluster (98036 / 98037), north Lynnwood (98087) and Brier (98036). A hotel titled 'Seattle "
     "North' is placed by its own code. Everett and Mukilteo beyond it are refused. STRONG."),
    ("issaquah", "Issaquah", "Issaquah / I-90 / Gilman Village / Issaquah Highlands", "CORRIDOR", "issaquah",
     ["98027", "98029"],
     "The City of Issaquah on I-90 at the edge of the Issaquah Alps: downtown, Gilman Village and the I-90 / Front "
     "Street hotel cluster (98027) and the Issaquah Highlands (98029). STRONG. Sammamish, Snoqualmie and North Bend "
     "beyond it are refused."),
    ("kent", "Kent", "Kent / Kent Valley / ShoWare / Kent Station / East Hill / I-5 at S 272nd", "CORRIDOR", "kent",
     ["98030", "98031", "98032"],
     "The City of Kent: the Kent Valley warehouse and business district and accesso ShoWare Center (98032), Kent "
     "Station and East Hill (98030 / 98031) and the West Hill / I-5 side (98032). STRONG. Auburn and Covington beyond "
     "it are refused."),
    ("federal-way", "Federal Way", "Federal Way / The Commons / I-5 at S 320th St / Pacific Hwy S / Wild Waves",
     "CORRIDOR", "federal way", ["98003", "98023"],
     "The City of Federal Way: the S 320th Street / I-5 hotel cluster, The Commons and the Pacific Highway South "
     "row (98003) and west Federal Way / Twin Lakes / Dash Point (98023). STRONG. Milton, Fife and Tacoma beyond it "
     "are refused (Pierce County)."),
    # ---------------------------------------------------------------- FRINGE (CAREFUL evaluation)
    ("mercer-island", "Mercer Island", "Mercer Island / I-90 between Seattle and Bellevue", "FRINGE",
     "mercer island", ["98040"],
     "The City of Mercer Island on I-90 between Seattle and Bellevue (98040). Admitted at FRINGE after CAREFUL "
     "evaluation so its small inventory is ACCOUNTED FOR."),
    ("shoreline-lake-forest-park", "Shoreline & Lake Forest Park", "Shoreline / Aurora Ave N north of N 145th / "
     "Richmond Beach / Lake Forest Park", "FRINGE", "shoreline", ["98155", "98177"],
     "The City of Shoreline north of Seattle on Aurora Avenue North and I-5 (98155 / 98177) and Lake Forest Park "
     "(98155). Shoreline's south side is in 98133 (north-seattle, covered whole). Admitted at FRINGE after CAREFUL "
     "evaluation."),
    ("burien-white-center", "Burien & White Center", "Burien / White Center / Normandy Park / SR-509", "FRINGE",
     "burien", ["98146", "98166"],
     "The City of Burien and unincorporated White Center (98146) and Burien's west side / Normandy Park (98166). The "
     "Burien / SeaTac airport side (98148 / 98168) is in sea-airport. Admitted at FRINGE after CAREFUL evaluation."),
    ("woodinville", "Woodinville", "Woodinville / wine country / Hollywood district / Cottage Lake", "FRINGE",
     "woodinville", ["98072", "98077"],
     "The City of Woodinville and its wine-country tasting-room district (98072) and the Cottage Lake / north "
     "Woodinville side (98077), metro-continuous with Bothell, Kirkland and Redmond. Admitted at FRINGE after CAREFUL "
     "evaluation."),
    ("edmonds-mountlake-terrace", "Mountlake Terrace & Edmonds", "Mountlake Terrace / Edmonds / Highway 99 / "
     "Edmonds ferry terminal", "FRINGE", "mountlake terrace", ["98043", "98020", "98026"],
     "The City of Mountlake Terrace on I-5 (98043) and the City of Edmonds -- the downtown / ferry terminal side "
     "(98020) and the Highway 99 side (98026) -- the metro-continuous band between Shoreline and Lynnwood. Admitted at "
     "FRINGE after CAREFUL evaluation; refusing Edmonds would leave an unclaimed hole between two admitted cities."),
]

OUTSIDE = [
    ("Tacoma / Pierce County -- Tacoma, Fife, Lakewood, University Place, Puyallup, Sumner, Gig Harbor, Milton, "
     "Edgewood, Bonney Lake, Spanaway, DuPont, Joint Base Lewis-McChord", "WA",
     ["98354", "98371", "98372", "98373", "98374", "98375", "98387", "98388", "98390", "98391", "98332", "98335",
      "98327", "98338", "98433", "98439"],
     "PIERCE COUNTY; FUTURE_STANDALONE tacoma-wa. Tacoma's own downtown, Tacoma Dome, port, the Puyallup fair and "
     "JBLM -- its own bureau (Travel Tacoma) and its own market 30 miles south on I-5. Refused by name and by postal "
     "PREFIX (984; Pierce's 983 codes named here). A hotel marketed 'Seattle-Tacoma' or 'Seattle/Fife' at one of these "
     "codes is refused by its own address."),
    ("Olympia / Thurston County -- Olympia, Lacey, Tumwater, Yelm", "WA", [],
     "THURSTON COUNTY; FUTURE_STANDALONE olympia-wa. The state capital, 60 miles south-west on I-5. Refused by postal "
     "PREFIX (985)."),
    ("Everett / north Snohomish County -- Everett, Mukilteo, Marysville, Lake Stevens, Snohomish, Monroe, Arlington, "
     "Stanwood", "WA",
     ["98201", "98203", "98204", "98205", "98206", "98207", "98208", "98275", "98270", "98271", "98258", "98290",
      "98296", "98272", "98223", "98292"],
     "SNOHOMISH COUNTY north of Lynnwood / Bothell / Mill Creek; FUTURE_STANDALONE everett-wa. Paine Field, Boeing "
     "Everett, Naval Station Everett and the Everett waterfront -- 25-30 miles north on I-5. Refused by name and by "
     "postal code. A hotel marketed 'Seattle North' or 'Seattle-Everett' at one of these codes is refused by its own "
     "address."),
    ("Bellingham / Whatcom, Skagit, Island and San Juan counties -- Bellingham, Ferndale, Blaine, Mount Vernon, "
     "Burlington, Anacortes, La Conner, Oak Harbor, Coupeville, Langley, Friday Harbor", "WA",
     ["98225", "98226", "98227", "98228", "98229", "98248", "98230", "98273", "98274", "98233", "98221", "98257",
      "98277", "98278", "98239", "98260", "98249", "98250", "98245", "98261"],
     "FUTURE_STANDALONE bellingham-wa (and the Skagit / Whidbey / San Juan destination inventory). The distant North "
     "Sound, 60-90 miles north. Refused by name and postal code."),
    ("Kitsap / Bremerton / Bainbridge Island / Olympic Peninsula -- Bremerton, Silverdale, Port Orchard, Poulsbo, "
     "Kingston, Bainbridge Island, Port Townsend, Port Angeles, Sequim", "WA",
     ["98110", "98310", "98311", "98312", "98314", "98315", "98337", "98366", "98367", "98370", "98383", "98346",
      "98340", "98342", "98345", "98359", "98364", "98380", "98392", "98368", "98362", "98363", "98382"],
     "KITSAP / JEFFERSON / CLALLAM COUNTY; FUTURE_STANDALONE kitsap-wa. Across Puget Sound by ferry: Bainbridge "
     "Island (98110 -- a 981 code, refused by name), Bremerton and Naval Base Kitsap, Silverdale, Poulsbo, Port "
     "Orchard, Kingston, and the Olympic Peninsula beyond. A ferry crossing is where metro continuity stops."),
    ("Outer King County ring -- Auburn, Algona, Pacific, Covington, Maple Valley, Black Diamond, Enumclaw, "
     "Ravensdale, Hobart", "WA", ["98001", "98002", "98092", "98047", "98042", "98038", "98010", "98022", "98051",
                                  "98025"],
     "SOUTH / SOUTH-EAST KING COUNTY; refused after CAREFUL evaluation. Auburn is its own Green River valley city "
     "south of Kent (98001 is shared with Federal Way's east edge and Algona and refused whole: Federal Way's hotel "
     "row is 98003); Covington, Maple Valley, Black Diamond and Enumclaw are separate towns toward the Cascades and "
     "Mount Rainier. Recorded, never silently absorbed. A founder may move Auburn on the record."),
    ("Outer Eastside -- Sammamish, Snoqualmie, North Bend, Fall City, Preston, Carnation, Duvall, Snoqualmie Pass",
     "WA", ["98074", "98075", "98065", "98045", "98024", "98050", "98014", "98019", "98068"],
     "EAST KING COUNTY; refused after CAREFUL evaluation. Sammamish is a residential plateau with no hotel district; "
     "Snoqualmie (the Salish Lodge and the falls), North Bend, Fall City, Carnation, Duvall and Snoqualmie Pass are "
     "the Cascade-foothill and mountain destination a traveller drives TO."),
    ("Vashon / Maury Island", "WA", ["98070"],
     "KING COUNTY, reached only by ferry; refused -- a ferry crossing is where metro continuity stops."),
    ("Vancouver / Clark County -- the Portland metro", "WA", [],
     "CLARK COUNTY; part of the Portland, Oregon market. Refused by postal PREFIX (986)."),
    ("Central and Eastern Washington, Oregon and out of state", "--", [],
     "Every other Washington postal prefix (988-994: Wenatchee, Leavenworth, Yakima, the Tri-Cities, Spokane ...), "
     "every Oregon code and every non-Washington code is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("982", "Everett / north Snohomish, Skagit, Whatcom (Bellingham), Island and San Juan counties", ""),
    ("983", "Tacoma / Pierce County, Kitsap (Bremerton), the Olympic Peninsula and Mount Rainier", ""),
    ("984", "Tacoma / Pierce County", "tacoma-wa"),
    ("985", "Olympia / Thurston, Lewis, Grays Harbor and Mason counties", "olympia-wa"),
    ("986", "Vancouver / Clark County (Portland metro)", ""),
    ("988", "Wenatchee / Leavenworth / Chelan (north-central Washington)", ""),
    ("989", "Yakima / Ellensburg (central Washington)", ""),
    ("990", "Spokane region", ""), ("991", "Spokane region", ""), ("992", "Spokane", ""),
    ("993", "Tri-Cities / Walla Walla", ""), ("994", "Clarkston / south-east Washington", ""),
    ("970", "Portland, Oregon", ""), ("971", "Portland region, Oregon", ""), ("972", "Portland, Oregon", ""),
    ("973", "Salem, Oregon", ""), ("974", "Eugene, Oregon", ""), ("975", "Medford, Oregon", ""),
    ("976", "Klamath Falls, Oregon", ""), ("977", "Bend, Oregon", ""), ("978", "Pendleton, Oregon", ""),
    ("979", "Ontario, Oregon", ""),
]

#: Seattle's own postal prefixes. A code under one of these that no corridor claims and no OUTSIDE row names is an
#: UNCLAIMED King / south Snohomish code -- refused, and named in the boundary audit so it is visible, never
#: silently dropped.
VALLEY_PREFIXES = ("980", "981")

ADMITTED_COUNTIES = {"king (seattle, the eastside, the airport and the south-county I-5 / valley cities; the outer "
                     "ring refused)",
                     "snohomish (bothell north, mill creek south, lynnwood, brier, mountlake terrace, edmonds; "
                     "everett and the north county refused)"}
OBSERVED_COUNTIES = OrderedDict([
    ("pierce (tacoma, fife, lakewood, puyallup, gig harbor, jblm)", "tacoma-wa"),
    ("thurston (olympia, lacey, tumwater)", "olympia-wa"),
    ("snohomish north (everett, mukilteo, marysville, lake stevens, snohomish, monroe)", "everett-wa"),
    ("whatcom / skagit / island / san juan (bellingham, mount vernon, anacortes, whidbey, friday harbor)",
     "bellingham-wa"),
    ("kitsap / jefferson / clallam (bremerton, silverdale, poulsbo, bainbridge island, port townsend)", "kitsap-wa"),
    ("king outer ring (auburn, covington, maple valley, enumclaw, sammamish, snoqualmie, north bend, vashon)",
     "(none -- refused by name after careful evaluation)"),
])

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("king", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. Seattle, the SEA airport cities (SeaTac, Tukwila, Des Moines' north side, "
                   "Burien), the Eastside (Bellevue, Redmond, Kirkland, Mercer Island, Woodinville, Bothell's King "
                   "side, Kenmore, Issaquah), Renton, Kent, Federal Way and Shoreline / Lake Forest Park are admitted; "
                   "Auburn, Covington, Maple Valley, Black Diamond, Enumclaw, Sammamish, Snoqualmie, North Bend, Fall "
                   "City, Carnation, Duvall and Vashon Island are REFUSED. County inclusion is not traveller-market "
                   "inclusion."),
    ])),
    ("snohomish", OrderedDict([
        ("ruling", "ADMITTED ONLY ON THE SOUTH-COUNTY METRO EDGE. Bothell's Snohomish side and Canyon Park, Mill "
                   "Creek's south side (98012, shared with Bothell), Lynnwood, Brier, Mountlake Terrace and Edmonds "
                   "are admitted; Everett, Mukilteo, Marysville, Lake Stevens, Snohomish, Monroe and the north county "
                   "are refused (FUTURE_STANDALONE everett-wa)."),
    ])),
    ("pierce / thurston", OrderedDict([
        ("ruling", "REFUSED. Tacoma, Fife, Lakewood, Puyallup, Gig Harbor and JBLM are FUTURE_STANDALONE tacoma-wa; "
                   "Olympia, Lacey and Tumwater are FUTURE_STANDALONE olympia-wa. Seattle does not absorb the South "
                   "Sound."),
    ])),
    ("kitsap / jefferson / clallam / whatcom / skagit / island / san juan", OrderedDict([
        ("ruling", "REFUSED. Bremerton, Bainbridge Island and the Olympic Peninsula are across a ferry crossing "
                   "(FUTURE_STANDALONE kitsap-wa); Bellingham, Skagit, Whidbey and the San Juans are the distant North "
                   "Sound (FUTURE_STANDALONE bellingham-wa)."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / patient / member
#: only). A normalised-name substring match; the census row keeps its reason.
NONPUBLIC_NAMES = {
    "navy lodge": "Navy Lodge on-base lodging -- MILITARY_RESTRICTED",
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- restricted to authorised DoD travellers; MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "lewis mcchord": "Joint Base Lewis-McChord lodging -- MILITARY_RESTRICTED",
    "jblm": "Joint Base Lewis-McChord lodging -- MILITARY_RESTRICTED",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "pete gross house": "Fred Hutch / Seattle Cancer Care patient housing -- not public lodging",
    "scca house": "Fred Hutch / Seattle Cancer Care Alliance patient housing -- not public lodging",
    "seattle cancer care alliance house": "Fred Hutch / Seattle Cancer Care Alliance patient housing -- not public "
                                          "lodging",
    "fred hutch house": "Fred Hutch patient housing -- not public lodging",
    "hope lodge": "American Cancer Society Hope Lodge -- patient lodging, not public lodging",
}

#: Military postal codes inside the admitted partition. NONE: JBLM, Naval Station Everett and Naval Base Kitsap all
#: sit in refused regions.
MILITARY_POSTAL_CODES = OrderedDict()

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-waterfront", "Seattle", "Downtown / Pike Place / Waterfront / Belltown / Pioneer Square", 47.6080,
     -122.3380, 2200, True),
    ("seattle-center-slu", "Seattle", "Seattle Center / Queen Anne / South Lake Union", 47.6270, -122.3480, 3000,
     True),
    ("capitol-hill-central", "Seattle", "Capitol Hill / First Hill / Central District", 47.6150, -122.3100, 3000,
     True),
    ("university-district", "Seattle", "University District / UW", 47.6610, -122.3080, 2500, True),
    ("ballard-fremont", "Seattle", "Ballard / Fremont / Green Lake", 47.6700, -122.3650, 3500, True),
    ("north-seattle", "Seattle", "Northgate / Lake City / Aurora north", 47.7150, -122.3200, 5000, True),
    ("south-west-seattle", "Seattle", "West Seattle / Georgetown / Rainier Valley", 47.5450, -122.3300, 7000, True),
    ("sea-airport", "SeaTac", "SEA / SeaTac / Tukwila / Southcenter", 47.4500, -122.2900, 6000, True),
    ("bellevue", "Bellevue", "Downtown Bellevue / Eastgate / Crossroads", 47.6000, -122.1700, 6000, True),
    ("redmond", "Redmond", "Redmond / Overlake", 47.6650, -122.1250, 5000, True),
    ("kirkland", "Kirkland", "Kirkland / Totem Lake", 47.6950, -122.1950, 4000, True),
    ("renton", "Renton", "Renton / Newcastle / Skyway", 47.4850, -122.1900, 6000, True),
    ("bothell-kenmore", "Bothell", "Bothell / Canyon Park / Kenmore", 47.7850, -122.2100, 5000, True),
    ("lynnwood", "Lynnwood", "Lynnwood / Alderwood", 47.8250, -122.2900, 4000, True),
    ("issaquah", "Issaquah", "Issaquah", 47.5400, -122.0300, 4000, True),
    ("kent", "Kent", "Kent / Kent Valley", 47.3900, -122.2300, 6000, True),
    ("federal-way", "Federal Way", "Federal Way", 47.3150, -122.3200, 5000, True),
    ("mercer-island", "Mercer Island", "Mercer Island", 47.5700, -122.2250, 3000, True),
    ("shoreline-lake-forest-park", "Shoreline", "Shoreline / Lake Forest Park", 47.7600, -122.3200, 4000, True),
    ("burien-white-center", "Burien", "Burien / White Center", 47.4800, -122.3450, 4000, True),
    ("woodinville", "Woodinville", "Woodinville", 47.7550, -122.1500, 4000, True),
    ("edmonds-mountlake-terrace", "Mountlake Terrace", "Mountlake Terrace / Edmonds", 47.8000, -122.3400, 4000,
     True),
    ("obs-tacoma", "Tacoma", "Tacoma / Fife / Lakewood / Puyallup -- OBSERVATION ONLY", 47.2300, -122.4500, 18000,
     False),
    ("obs-olympia", "Olympia", "Olympia / Lacey / Tumwater -- OBSERVATION ONLY", 47.0300, -122.8800, 12000, False),
    ("obs-everett", "Everett", "Everett / Mukilteo / Marysville -- OBSERVATION ONLY", 47.9700, -122.2000, 14000,
     False),
    ("obs-bellingham", "Bellingham", "Bellingham / Skagit -- OBSERVATION ONLY", 48.6000, -122.4500, 30000, False),
    ("obs-kitsap", "Bremerton", "Bremerton / Silverdale / Bainbridge Island -- OBSERVATION ONLY", 47.6200,
     -122.6500, 20000, False),
    ("obs-south-king", "Auburn", "Auburn / Covington / Maple Valley / Enumclaw -- OBSERVATION ONLY", 47.3200,
     -122.1000, 15000, False),
    ("obs-east-king", "Snoqualmie", "Sammamish / Snoqualmie / North Bend -- OBSERVATION ONLY", 47.5600, -121.8800,
     15000, False),
]

#: The observation box. It reaches north past Everett to Bellingham, south past Tacoma to Olympia, west across the
#: Sound to Bremerton and the Kitsap Peninsula and east to North Bend, so the census counts what it refuses.
BOUNDS = {"min_lat": 46.95, "max_lat": 48.85, "min_lng": -123.10, "max_lng": -121.65}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Pike Place Market", 47.6097, -122.3422, 0.30),
    ("Seattle Waterfront", 47.6060, -122.3420, 0.55),
    ("Seattle Convention Center", 47.6116, -122.3320, 0.35),
    ("Pioneer Square", 47.6015, -122.3343, 0.45),
    ("Chinatown-International District", 47.5980, -122.3240, 0.50),
    ("Stadiums / SoDo", 47.5920, -122.3320, 0.80),
    ("Belltown", 47.6150, -122.3480, 0.60),
    ("Downtown Seattle CBD", 47.6080, -122.3350, 1.00),
    ("Seattle Center / Queen Anne", 47.6230, -122.3530, 0.80),
    ("South Lake Union", 47.6256, -122.3370, 0.90),
    ("Queen Anne Hill / Interbay / Magnolia", 47.6400, -122.3800, 2.50),
    ("Capitol Hill / First Hill / Central", 47.6150, -122.3150, 2.00),
    ("University District", 47.6610, -122.3130, 1.50),
    ("Ballard / Fremont", 47.6600, -122.3650, 2.20),
    ("North Seattle / Northgate / Aurora", 47.7150, -122.3250, 3.50),
    ("West Seattle / South Seattle", 47.5450, -122.3350, 5.00),
    ("SEA Airport / SeaTac", 47.4450, -122.2970, 2.50),
    ("Tukwila / Southcenter", 47.4590, -122.2580, 2.00),
    ("Downtown Bellevue", 47.6150, -122.2010, 1.30),
    ("Bellevue (Eastgate / Factoria / Crossroads)", 47.5900, -122.1500, 4.00),
    ("Redmond", 47.6700, -122.1200, 4.00),
    ("Kirkland", 47.6950, -122.1950, 3.50),
    ("Renton", 47.4850, -122.2000, 4.00),
    ("Bothell", 47.7850, -122.2050, 4.00),
    ("Lynnwood", 47.8250, -122.2850, 3.50),
    ("Issaquah", 47.5450, -122.0400, 3.50),
    ("Kent", 47.3900, -122.2350, 4.00),
    ("Federal Way", 47.3120, -122.3150, 4.00),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Pike Place Market", re.compile(r"\bpike pl(ace)?\b|\bpost alley\b", re.I)),
    ("Seattle Waterfront", re.compile(r"\balaskan way\b|\bpier (66|69|70|57|91)\b|\bwestern ave\b(?=.*9812?1)",
                                      re.I)),
    ("Seattle Convention Center", re.compile(r"\bconvention pl\b|\bpine st\b(?=.*98101)|\bpike st\b(?=.*98101)",
                                             re.I)),
    ("Pioneer Square", re.compile(r"\bs (jackson|main|washington|king) st\b(?=.*98104)|\boccidental\b", re.I)),
    ("Stadiums / SoDo", re.compile(r"\b(1st|4th) ave s\b(?=.*9813[4])|\bedgar martinez\b|\bs royal brougham\b",
                                   re.I)),
    ("Seattle Center / Queen Anne", re.compile(r"\bqueen anne ave n\b|\b[1-5](st|nd|rd|th) ave n\b(?=.*98109)|"
                                               r"\b(w )?mercer st\b(?=.*98109)|\broy st\b|\bdenny way\b(?=.*98109)|"
                                               r"\belliott ave w\b", re.I)),
    ("South Lake Union", re.compile(r"\bwestlake ave n\b|\bdexter ave n\b|\bfairview ave n\b|\bterry ave n\b|"
                                    r"\bboren ave n\b|\b(8|9)th ave n\b|\bminor ave n\b|\byale ave n\b|\bvalley st\b",
                                    re.I)),
    ("SEA Airport / SeaTac", re.compile(r"\binternational b(lv)?d\b(?=.*981(88|98))|\bpacific hwy s\b(?=.*98188)|"
                                        r"\bs 1[78]\d(th)? st\b(?=.*98188)|\bair cargo rd\b", re.I)),
    ("Tukwila / Southcenter", re.compile(r"\bsouthcenter\b|\bandover park\b|\bstrander b(lv)?d\b|\btukwila pkwy\b|"
                                         r"\bbaker b(lv)?d\b", re.I)),
    ("North Seattle / Northgate / Aurora", re.compile(r"\baurora ave n\b(?=.*981(33|03))|\bnorthgate\b", re.I)),
    ("Downtown Bellevue", re.compile(r"\bbellevue way ne\b|\b1(06|08|10|12)th ave ne\b(?=.*98004)|"
                                     r"\bne (4|6|8|10)th st\b(?=.*98004)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-waterfront": "Downtown Seattle CBD",
    "seattle-center-slu": "Seattle Center / Queen Anne",
    "capitol-hill-central": "Capitol Hill / First Hill / Central",
    "university-district": "University District",
    "ballard-fremont": "Ballard / Fremont",
    "north-seattle": "North Seattle / Northgate / Aurora",
    "south-west-seattle": "West Seattle / South Seattle",
    "sea-airport": "SEA Airport / SeaTac",
    "bellevue": "Bellevue (Eastgate / Factoria / Crossroads)",
    "redmond": "Redmond",
    "kirkland": "Kirkland",
    "renton": "Renton",
    "bothell-kenmore": "Bothell",
    "lynnwood": "Lynnwood",
    "issaquah": "Issaquah",
    "kent": "Kent",
    "federal-way": "Federal Way",
    "mercer-island": "Mercer Island",
    "shoreline-lake-forest-park": "Shoreline",
    "burien-white-center": "Burien",
    "woodinville": "Woodinville",
    "edmonds-mountlake-terrace": "Mountlake Terrace / Edmonds",
}

#: The order's REQUIRED / STRONG / CAREFUL / KEEP-SEPARATE evaluation list, each classified explicitly.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Seattle", "ADMITTED (CORE, downtown-waterfront, 98101 / 98104 / 98121 / 98134 / 98154 / 98161 / 98164 "
                         "/ 98174). REQUIRED."),
    ("Pike Place / Waterfront", "ADMITTED -- OVERLAYS of 98101 / 98121 (downtown-waterfront); a postal code is never "
                                "split. REQUIRED."),
    ("Seattle Center / Queen Anne", "ADMITTED (CORE, seattle-center-slu, 98109 / 98119 / 98199) -- reported as an "
                                    "overlay of the corridor. REQUIRED."),
    ("South Lake Union", "ADMITTED (CORE, seattle-center-slu, 98109 -- the same postal code as Seattle Center, never "
                         "split) -- reported as an overlay of the corridor. REQUIRED."),
    ("Capitol Hill / Central Seattle", "ADMITTED (CORE, capitol-hill-central, 98102 / 98112 / 98122 / 98144). "
                                       "REQUIRED."),
    ("University District", "ADMITTED (CORE, university-district, 98105 / 98195). REQUIRED."),
    ("Ballard / Fremont", "ADMITTED (CORE, ballard-fremont, 98103 / 98107 / 98117). REQUIRED."),
    ("North Seattle / Northgate", "ADMITTED (CORE, north-seattle, 98115 / 98125 / 98133) -- inside the municipal "
                                  "market; never left unclaimed."),
    ("West Seattle / South Seattle", "ADMITTED (CORE, south-west-seattle, 98106 / 98108 / 98116 / 98118 / 98126 / "
                                     "98136) -- inside the municipal market; never left unclaimed."),
    ("SEA / SeaTac Airport", "ADMITTED (CORE, sea-airport, 98158 / 98188 / 98198 / 98168 / 98148). REQUIRED."),
    ("Tukwila", "ADMITTED (CORE, sea-airport: 98188 shared with SeaTac and 98168, both covered whole) -- reported as "
                "an overlay by the property's own municipality. REQUIRED."),
    ("Bellevue", "ADMITTED (CORE, bellevue, 98004 / 98005 / 98006 / 98007 / 98008). REQUIRED."),
    ("Redmond", "ADMITTED (CORE, redmond, 98052 / 98053). REQUIRED."),
    ("Kirkland", "ADMITTED (CORE, kirkland, 98033 / 98034). REQUIRED."),
    ("Renton", "ADMITTED (CORE, renton, 98055 / 98056 / 98057 / 98058 / 98059 / 98178). REQUIRED."),
    ("Bothell", "ADMITTED (STRONG CORRIDOR, bothell-kenmore, 98011 / 98012 / 98021 / 98028). STRONG."),
    ("Lynnwood", "ADMITTED (STRONG CORRIDOR, lynnwood, 98036 / 98037 / 98087). STRONG."),
    ("Issaquah", "ADMITTED (STRONG CORRIDOR, issaquah, 98027 / 98029). STRONG."),
    ("Kent", "ADMITTED (STRONG CORRIDOR, kent, 98030 / 98031 / 98032). STRONG."),
    ("Federal Way", "ADMITTED (STRONG CORRIDOR, federal-way, 98003 / 98023). STRONG."),
    ("Mercer Island", "ADMITTED (FRINGE, mercer-island, 98040) -- on I-90 between Seattle and Bellevue. CAREFUL."),
    ("Shoreline", "ADMITTED (FRINGE, shoreline-lake-forest-park, 98155 / 98177; its south side is in 98133, CORE "
                  "north-seattle, covered whole). CAREFUL."),
    ("Burien", "ADMITTED (FRINGE, burien-white-center, 98146 / 98166; its airport side 98148 / 98168 is in CORE "
               "sea-airport, covered whole). CAREFUL."),
    ("Des Moines", "ADMITTED ONLY THROUGH THE AIRPORT CODES it shares with SeaTac (98198 / 98148, CORE sea-airport, "
                   "covered whole); Des Moines has no code of its own. CAREFUL."),
    ("Woodinville", "ADMITTED (FRINGE, woodinville, 98072 / 98077) -- metro-continuous with Bothell, Kirkland and "
                    "Redmond. CAREFUL."),
    ("Mountlake Terrace", "ADMITTED (FRINGE, edmonds-mountlake-terrace, 98043). CAREFUL."),
    ("Edmonds", "ADMITTED (FRINGE, edmonds-mountlake-terrace, 98020 / 98026) -- not named by the order; evaluated "
                "CAREFULLY because refusing it would leave an unclaimed hole between admitted Shoreline, Mountlake "
                "Terrace and Lynnwood."),
    ("Auburn", "OUTSIDE after CAREFUL evaluation -- its own Green River valley city south of Kent; a founder may "
               "move it on the record."),
    ("Sammamish / Snoqualmie / North Bend", "OUTSIDE after CAREFUL evaluation -- residential plateau and the Cascade-"
                                            "foothill destination."),
    ("Tacoma", "OUTSIDE -- FUTURE_STANDALONE tacoma-wa; refused by prefix 984 and by its Pierce 983 codes. KEEP "
               "SEPARATE."),
    ("Olympia", "OUTSIDE -- FUTURE_STANDALONE olympia-wa; refused by prefix 985. KEEP SEPARATE."),
    ("Everett", "OUTSIDE -- FUTURE_STANDALONE everett-wa; refused by its own codes and prefix 982. KEEP SEPARATE."),
    ("Bellingham", "OUTSIDE -- FUTURE_STANDALONE bellingham-wa; refused by prefix 982. KEEP SEPARATE."),
    ("Kitsap / Bremerton", "OUTSIDE -- FUTURE_STANDALONE kitsap-wa; refused by prefix 983. KEEP SEPARATE."),
    ("Bainbridge Island", "OUTSIDE -- FUTURE_STANDALONE kitsap-wa; 98110 refused by name (a ferry crossing). KEEP "
                          "SEPARATE."),
    ("Distant North Sound inventory", "OUTSIDE -- Skagit, Whidbey, the San Juans and Whatcom (prefix 982). KEEP "
                                      "SEPARATE."),
])

#: The Puget Sound boundary ruling (consumers read it under the inherited name HILL_COUNTRY_RULING).
PUGET_SOUND_RULING = OrderedDict([
    ("classification", "The metro-continuous Seattle / Eastside / airport / I-5 core is admitted -- Seattle, SeaTac, "
                       "Tukwila, Bellevue, Redmond, Kirkland and Renton CORE; Bothell, Lynnwood, Issaquah, Kent and "
                       "Federal Way STRONG CORRIDOR; Mercer Island, Shoreline, Burien, Woodinville, Mountlake Terrace "
                       "and Edmonds FRINGE. Tacoma, Olympia, Everett, Bellingham, Kitsap / Bremerton / Bainbridge and "
                       "the rest of Puget Sound are OUTSIDE."),
    ("a_marketing_phrase_admits_nothing", "'Seattle Airport', 'Seattle/Southcenter', 'Seattle/Bellevue', 'Seattle "
                                          "Eastside', 'Seattle/Renton', 'Seattle North', 'Seattle-Everett', "
                                          "'Seattle-Tacoma' and 'Seattle/Fife' are marketing. The property's own "
                                          "postal code decides."),
    ("actual_location", "Decided by the property's own postal code on its own page."),
    ("drive_market_relationship", "SEA, the Eastside, Renton, the south-county I-5 cities and the south Snohomish "
                                  "edge are where Seattle-bound travellers sleep; Tacoma, Olympia, Everett, "
                                  "Bellingham and the Kitsap / Olympic ferry destinations are markets of their own."),
    ("traveller_intent", "Cruise, convention, stadium, corporate (Amazon, Microsoft, the Bellevue towers), "
                         "university, medical and airport demand is Seattle intent; the Tacoma Dome, JBLM, the state "
                         "capital, Paine Field / Boeing Everett and the San Juan / Olympic destinations are not."),
    ("metro_continuity", "Continuous development runs from Lynnwood and Mountlake Terrace through Seattle to Federal "
                         "Way on I-5, and from Bothell through Kirkland, Bellevue and Renton on I-405, out I-90 to "
                         "Issaquah; it is broken by the Pierce county line at Federal Way / Milton, by the Everett / "
                         "Mukilteo boundary north of Lynnwood, by the Cascade foothills past Issaquah and by every "
                         "ferry crossing."),
    ("corridor_support", "Every admitted edge code is in a named corridor (federal-way, lynnwood, bothell-kenmore, "
                         "issaquah, edmonds-mountlake-terrace, woodinville) so its count is visible and a founder can "
                         "move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE tacoma-wa, olympia-wa, everett-wa, bellingham-wa and kitsap-wa."),
])
HILL_COUNTRY_RULING = PUGET_SOUND_RULING

STRUCTURE_TEST = OrderedDict([
    ("A. Is Seattle one market, or several?",
     "ONE market, seattle-wa, covering the contiguous Seattle / Eastside / SEA / south-county metro -- from Lynnwood "
     "and Bothell to Federal Way, and from Ballard and West Seattle to Issaquah. One commercial airport (SEA), one "
     "I-5 / I-405 / I-90 / SR-520 / SR-99 road system, one Link light-rail spine. The Pierce county line, Everett, "
     "the Cascade foothills and the ferry crossings are where that coherence stops."),
    ("B. The City of Seattle is NOT the market -- and 'Seattle' places nothing",
     "SeaTac, Tukwila, Bellevue, Redmond, Kirkland, Renton, Bothell, Lynnwood, Issaquah, Kent and Federal Way are "
     "admitted by their own codes; the chains' 'Seattle' prefix is on hotels from Everett to Fife and Tacoma."),
    ("C. SEA", "The airport owns its postal code (98158) and its lodging system -- its own CORE corridor with SeaTac's "
               "and Tukwila's shared 98188, 98198, 98168 and 98148."),
    ("D. Pike Place / Waterfront / Convention Center", "NO CORRIDOR of their own -- overlays of downtown (98101 / "
                                                       "98121)."),
    ("E. Seattle Center vs South Lake Union", "ONE postal code (98109), never split: one corridor, two overlays."),
    ("F. Tukwila vs SeaTac", "ONE shared postal code (98188), never split: one corridor, two overlays by the "
                             "property's own municipality."),
    ("G. Bellevue / Redmond / Kirkland / Renton", "Each its own CORE corridor -- the Eastside is not 'Seattle' and "
                                                  "is not one blob."),
    ("H. Tacoma", "OUTSIDE -- FUTURE_STANDALONE tacoma-wa."),
    ("I. Olympia", "OUTSIDE -- FUTURE_STANDALONE olympia-wa."),
    ("J. Everett and the North Sound", "OUTSIDE -- FUTURE_STANDALONE everett-wa / bellingham-wa."),
    ("K. Kitsap / Bremerton / Bainbridge", "OUTSIDE -- FUTURE_STANDALONE kitsap-wa."),
    ("L. Auburn / the outer King ring", "OUTSIDE after careful evaluation."),
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
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. Seattle's "
     "specific exposures: the downtown / Belltown / South Lake Union / Bellevue condo and apartment towers with "
     "furnished short-stay units, the serviced-apartment and aparthotel operators (Sonder, Kasa, Mint House, "
     "Placemakr, Blueground, Lark, Barsala), corporate-housing portfolios, hotel-and-residences towers (the "
     "residences are never the hotel), the WorldMark / Club Wyndham Camlin vacation-ownership building and the "
     "Airbnb / Vrbo inventory."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort (Club Wyndham, WorldMark, Hilton Grand Vacations, Marriott "
     "Vacation Club, Holiday Inn Club Vacations, Bluegreen, Diamond / Hilton Vacation Club, Hyatt Vacation Club) is "
     "TIMESHARE and is never admitted to hotel accounting, even when its brand lists it beside its hotels, even when "
     "it sells a nightly rate, and even when a pet-policy page exists (the Phoenix correction-003 lesson)."),
    ("shared_campus_relation",
     "Never merged by display name, brand, owner, phone, shared address, campus, booking engine, shared "
     "amenities or shared entrance. A dual-brand building is TWO hotels and is HELD for the split, never "
     "published as one. A hotel and its residences on one campus are distinct premises."),
    ("extended_stay",
     "Extended-stay hotels are hotels and are admitted on their own pages; an 'apartment hotel' or 'aparthotel' is "
     "admitted only as a public hotel operation at an exact premises, never as a residential building that rents "
     "furnished units."),
    ("patient_and_military_lodging",
     "Patient housing (Pete Gross House, the SCCA / Fred Hutch House), charitable family lodging (Ronald McDonald "
     "House, Fisher House) and on-base military lodging are never public hotels and are never admitted."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("98101", ["Downtown", "Pike Place Market", "Convention Center"]),
    ("98121", ["Belltown", "Waterfront", "Pier 66"]),
    ("98109", ["Seattle Center", "Lower Queen Anne", "South Lake Union"]),
    ("98188", ["SeaTac", "Tukwila"]),
    ("98198", ["SeaTac", "Des Moines"]),
    ("98168", ["Tukwila", "SeaTac", "Burien", "Boulevard Park"]),
    ("98148", ["Burien", "SeaTac", "Normandy Park", "Des Moines"]),
    ("98108", ["City of Seattle", "Tukwila"]),
    ("98178", ["Renton", "Skyway", "Tukwila", "City of Seattle"]),
    ("98133", ["City of Seattle", "Shoreline"]),
    ("98155", ["Shoreline", "Lake Forest Park", "City of Seattle"]),
    ("98146", ["Burien", "White Center", "City of Seattle"]),
    ("98012", ["Bothell", "Mill Creek"]),
    ("98028", ["Kenmore", "Bothell"]),
    ("98036", ["Lynnwood", "Brier"]),
    ("98026", ["Edmonds", "Lynnwood"]),
    ("98006", ["Bellevue", "Newcastle"]),
    ("98056", ["Renton", "Newcastle"]),
    ("98059", ["Renton", "Newcastle"]),
])

FUTURE_MARKETS = OrderedDict([
    ("tacoma-wa", "Tacoma / Pierce County -- Tacoma, Fife, Lakewood, Puyallup, Gig Harbor and JBLM, 30 miles south "
                  "on I-5."),
    ("olympia-wa", "Olympia / Lacey / Tumwater -- the state capital, 60 miles south-west."),
    ("everett-wa", "Everett / Mukilteo / Marysville -- Paine Field, Boeing Everett and Naval Station Everett, 25 "
                   "miles north."),
    ("bellingham-wa", "Bellingham / Skagit / Whidbey / the San Juans -- the distant North Sound."),
    ("kitsap-wa", "Bremerton / Silverdale / Poulsbo / Bainbridge Island and the Olympic Peninsula -- across Puget "
                  "Sound by ferry."),
])

#: Markets that are ALREADY LIVE. No live market owns a Washington postal code; every live market's exposure is a
#: shared chain NAME only (Kent, OH in cleveland-akron-canton-oh; Lakewood, CO in denver-co; Columbus's
#: University District; Fremont, OH ...).
EXISTING_LIVE_MARKETS = OrderedDict([
    ("san-antonio-tx", "San Antonio / Greater San Antonio, live as production market #39 (deploy "
                       "6ac064cd6a4261e60054a2f3) -- the CURRENT LIVE market at this order's authoring time. No "
                       "shared postal code."),
    ("cleveland-akron-canton-oh", "Cleveland / Akron / Canton, live -- its Kent, Ohio hotels share the bare place "
                                  "name 'Kent' with this market's Kent corridor; identity is decided by premises, "
                                  "never the name."),
    ("denver-co", "Denver, live -- its Lakewood, Colorado hotels share the bare place name 'Lakewood' with "
                  "Lakewood, WA (refused here, Pierce County)."),
])

#: A shared postal code whose OTHER town is refused. 98001 (Auburn / Federal Way / Algona) is refused whole, so a
#: Federal Way-named row at 98001 is refused with it.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "seattle,": "seattle", "seattle wa": "seattle", "seattle, wa": "seattle", "seattle washington": "seattle",
    "sea tac": "seatac", "sea-tac": "seatac", "seatac,": "seatac", "seatac wa": "seatac",
    "tukwila,": "tukwila", "bellevue,": "bellevue", "redmond,": "redmond", "kirkland,": "kirkland",
    "renton,": "renton", "bothell,": "bothell", "kenmore,": "kenmore", "mill creek,": "mill creek",
    "lynnwood,": "lynnwood", "brier,": "brier", "issaquah,": "issaquah", "kent,": "kent",
    "federal way,": "federal way", "fed way": "federal way", "mercer island,": "mercer island",
    "shoreline,": "shoreline", "lake forest park,": "lake forest park", "lk forest park": "lake forest park",
    "burien,": "burien", "white center,": "white center", "des moines,": "des moines",
    "normandy park,": "normandy park", "woodinville,": "woodinville", "mountlake terrace,": "mountlake terrace",
    "mountlake ter": "mountlake terrace", "mt lake terrace": "mountlake terrace", "mlt": "mountlake terrace",
    "edmonds,": "edmonds", "newcastle,": "newcastle",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("98101", "Downtown / Pike Place / Convention Center -- one postal code, never split."),
    ("98121", "Belltown / the Waterfront / Pier 66."),
    ("98109", "Seattle Center and South Lake Union -- one postal code, never split."),
    ("98158", "SEA -- the airport owns its code."),
    ("98188", "SeaTac's International Boulevard and Tukwila's Southcenter -- one postal code, never split."),
    ("98004", "Downtown Bellevue."),
    ("98052", "Redmond / Microsoft."),
    ("98110", "Bainbridge Island -- a 981 code, refused by name (kitsap-wa)."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Seattle" % name),
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
            ("state_code", STATE_CODE),
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
        raise SystemExit("admitted postal codes outside the Seattle prefixes: %s" % stray)
    registered_codes = _registered_market_postal_codes()
    live_overlap = sorted(z for z in seen_zip if z in registered_codes)
    if live_overlap:
        raise SystemExit("admitted postal codes a REGISTERED market already admits: %s" % [
            (z, registered_codes[z]) for z in live_overlap])
    military_unclaimed = [z for z in MILITARY_POSTAL_CODES if z not in seen_zip]
    if military_unclaimed:
        raise SystemExit("military postal codes claimed by no corridor: %s" % military_unclaimed)

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius), ("state_code", STATE_CODE),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Seattle / Bellevue / Puget Sound downtown, waterfront, cruise, convention, stadium, "
                        "corporate, university, medical, airport and Eastside lodging market (PetTripFinder discovery "
                        "scope)"),
        ("state", STATE_CODE),
        ("states", [STATE_CODE]),
        ("country", "US"),
        ("market_center", {"lat": 47.61, "lng": -122.33}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches north past Everett to Bellingham, south "
             "past Tacoma to Olympia, west across the Sound to Bremerton and the Kitsap Peninsula and east to North "
             "Bend, so that " +
             WORK_ORDER + " classifies those properties on evidence instead of being blind to them. Admission is "
             "decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Seattle / Bellevue / Puget Sound is ONE market: twelve CORE corridors (downtown / "
         "Pike Place / waterfront, Seattle Center / Queen Anne / South Lake Union, Capitol Hill / First Hill, the "
         "University District, Ballard / Fremont, North Seattle, West / South Seattle, SEA / SeaTac / Tukwila, "
         "Bellevue, Redmond, Kirkland, Renton), five STRONG CORRIDORS (Bothell / Kenmore, Lynnwood, Issaquah, Kent, "
         "Federal Way) and five FRINGE corridors (Mercer Island, Shoreline / Lake Forest Park, Burien / White Center, "
         "Woodinville, Mountlake Terrace / Edmonds). TACOMA, OLYMPIA, EVERETT, BELLINGHAM and KITSAP / BREMERTON / "
         "BAINBRIDGE are refused as future standalone markets; Auburn and the outer King County ring are refused by "
         "name. Patient, charitable and on-base lodging is never admitted."),
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
        ("market_name", "Seattle, Washington"),
        ("market_slug", MARKET_ID),
        ("state_name", "Washington"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", [STATE_CODE]),
        ("primary_city", "Seattle"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Seattle & Bellevue | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater Seattle -- downtown, Pike Place and the waterfront, Seattle "
         "Center, South Lake Union, Capitol Hill, the University District, SEA airport, Bellevue, Redmond, Kirkland "
         "and Renton -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Seattle"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry. A Seattle / Bellevue / Puget Sound downtown, waterfront, "
         "cruise, convention, stadium, corporate, university, medical, airport and Eastside travel market -- the "
         "contiguous metro from Lynnwood and Bothell to Federal Way, and from Ballard and West Seattle to Issaquah. "
         "Not 'Puget Sound': Tacoma, Olympia, Everett, Bellingham and Kitsap / Bremerton / Bainbridge are future "
         "standalone markets; Auburn and the outer King County ring are refused. Nothing else admits a property: not "
         "a brand's 'Seattle' marketing name, not a map pin, not a vacation-rental listing, not a competitor "
         "directory's city label. Patient, charitable and on-base lodging is never admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). The postal city "
         "'SEATTLE' spans seven corridors and places nothing by itself. Shared codes are covered whole: 98109 by "
         "Seattle Center and South Lake Union; 98188 by SeaTac and Tukwila; 98198 by SeaTac and Des Moines; 98133 by "
         "Seattle and Shoreline; 98012 by Bothell and Mill Creek. Pike Place, the Waterfront, the Convention Center, "
         "Seattle Center, South Lake Union, SEA and Tukwila are overlays."),
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
        ("phase", "2 + 3 + 4 -- Seattle / Bellevue / Puget Sound travel-market geography, the airport / Eastside "
                  "identity trap, the Puget Sound boundary and the residence / apartment / vacation-rental safety "
                  "rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/seattle-wa.json. This "
         "order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its brand's own property card states it, "
         "joined to the corridor registry. Nothing else admits a property."),
        ("classes", OrderedDict((k, "; ".join("%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG_CORRIDOR is registry class CORRIDOR; FUTURE_STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes and by postal PREFIX for the "
                          "refused regions; the future standalone markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("hill_country_ruling", HILL_COUNTRY_RULING),
        ("metro_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("military_lodging_rule", OrderedDict([
            ("rule", "On-base military / government lodging is MILITARY_RESTRICTED and never admitted: restricted "
                     "eligibility (DoD ID or sponsorship), on-base premises behind a gate, ordinary public-hotel "
                     "contract NOT satisfied. No installation owns an admitted Seattle postal code (JBLM, Naval "
                     "Station Everett and Naval Base Kitsap are in refused regions); the on-base names are refused "
                     "wherever they appear."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "Seattle was selected as a high-value PetTripFinder market for its downtown / Pike Place / waterfront "
         "tourism, cruise departures, convention and stadium demand, corporate travel (South Lake Union, Bellevue, "
         "Redmond), university and medical travel, extended-stay demand and SEA airport traffic. That lowers NO "
         "evidence standard: pet acceptance is never inferred from Seattle's reputation. It shapes only the CENSUS: "
         "every tourist, cruise, convention, stadium, corporate, university, medical, airport and extended-stay "
         "lodging cluster is covered by an admitting corridor."),
        ("the_seattle_name_trap",
         "The chains put 'Seattle' on hotels from Everett to Fife and Tacoma: 'Seattle Airport' on SeaTac and Tukwila "
         "hotels, 'Seattle/Southcenter' on Tukwila 98188, 'Seattle/Bellevue' and 'Seattle Eastside' on Bellevue and "
         "Redmond, 'Seattle/Renton', 'Seattle North' on Lynnwood and Everett, 'Seattle-Tacoma' and 'Seattle/Fife' on "
         "Pierce County hotels. A property's own postal code, street and brand property code decide what and where "
         "it is; none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Seattle-Tacoma International Airport (SEA)", "its own corridor sea-airport (98158 / 98188 / 98198 / "
                                                           "98168 / 98148)."),
            ("Pike Place Market / the Waterfront / Pier 66 cruise terminal", "downtown-waterfront (98101 / 98121) -- "
                                                                            "overlays."),
            ("Seattle Convention Center (Arch / Summit)", "downtown-waterfront (98101) -- overlay."),
            ("Lumen Field / T-Mobile Park", "downtown-waterfront (98134 / 98104) -- overlay."),
            ("Seattle Center / Space Needle / Climate Pledge Arena", "seattle-center-slu (98109) -- overlay."),
            ("South Lake Union (Amazon, Fred Hutch, life sciences)", "seattle-center-slu (98109) -- overlay."),
            ("Smith Cove / Pier 91 cruise terminal", "seattle-center-slu (98199)."),
            ("First Hill medical centers", "capitol-hill-central (98104 / 98122)."),
            ("University of Washington / UW Medical Center", "university-district (98105 / 98195)."),
            ("Downtown Bellevue / Meydenbauer Center", "bellevue (98004)."),
            ("Microsoft / Overlake", "redmond (98052)."),
            ("Boeing Renton / The Landing", "renton (98055 / 98057)."),
            ("Westfield Southcenter", "sea-airport (98188) -- Tukwila overlay."),
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
        ("registered_market_postal_codes_checked", len(registered_codes)),
        ("no_live_market_postal_code_admitted", not live_overlap),
        ("first_washington_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, theme-park, convention, "
         "military or stadium keywords; every corridor is show_in_navigation / show_in_sitemap false until a "
         "registration order publishes it."),
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
        return "OUTSIDE", None, "King / south Snohomish postal code %r is claimed by no corridor" % z
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
