"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5, 6, 7, 8 and 9: the Salt Lake City / Park City /
Wasatch Front market, Utah.

Built from zero on the CURRENT hardened lineage: the New Orleans-live release a67c8e75 (live lineage commit 90624cd8,
built_from 4c7e7b90). Current verified live at authoring time = new-orleans-la deploy 6ac5ba3bcda3a604f7e467e0, 44
markets / 4,240 profiles / 4,663 release-index routes / 4,740 served routes, host verified (release_index live-source
--fetch --verify-host). No earlier Salt Lake City build exists. It is the FIRST Utah market; the build refuses to admit
any code a registered market already admits.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Salt Lake City / Park City traveller lodging market -- NOT the City of Salt Lake City's municipal
boundary, and NOT "Utah" -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE
markets named inside OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact
to make a number. The order's "STRONG_CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property card)
states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted lodging ZIP
is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A brand's marketing
name never admits and never places a property.

TWO CLUSTERS, ONE MARKET (PHASE 2)
----------------------------------
The market is two traveller clusters joined by I-80 through Parleys Canyon (about 30 miles): the SALT LAKE VALLEY on
the Wasatch Front (downtown Salt Lake City, the airport, the University, Sugar House and the Salt Lake County suburbs
along I-15 / I-215 from North Salt Lake and Bountiful to Draper and Lehi), and PARK CITY on the Wasatch Back (Old
Town / Historic Main Street, Deer Valley, Park Meadows / Prospector, and the Snyderville Basin's Canyons Village and
Kimball Junction). Neither absorbs the other: every row keeps its own municipality.

NEIGHBOURHOODS AND RESORT BASES ARE OVERLAYS, NEVER SPLIT CODES
--------------------------------------------------------------
Temple Square, Central City and the Granary District share 84101 / 84111 / 84150 with the rest of downtown; Deer
Valley's Snow Park and Silver Lake bases share 84060 with Old Town and Historic Main Street; Canyons Village and Kimball
Junction share 84098. The registry partitions CODES, and those named places are REPORTING OVERLAYS decided from the
property's own street and pin -- never a membership decision and never a split code.

SALT LAKE CITY VS PARK CITY IDENTITY (PHASE 3)
----------------------------------------------
Park City is a distinct traveller identity inside this market. A Park City (84060 / 84068) or Snyderville Basin
(84098, mailing name "Park City") premises is a PARK CITY row and is NEVER written as Salt Lake City, whatever "Salt
Lake" its marketing carries; a Salt Lake City row is never written as Park City. Likewise Murray, Midvale, Sandy,
South Jordan, West Jordan, Draper, West Valley City, Cottonwood Heights, Holladay, Millcreek, South Salt Lake,
Taylorsville, Riverton, Lehi, North Salt Lake and Bountiful are their OWN municipalities: an "SLC South" or "Salt Lake
City Airport" hotel in one of them is a hotel of that municipality. The postal code's municipality list is checked
against the row's stated city (municipality_for_postal / municipality_conflict).

SKI RESORTS, LODGES, CONDOS AND CAMPUSES (PHASES 4, 5 AND 6)
-----------------------------------------------------------
Park City carries unusually complex lodging inventory: luxury resort hotels with branded residences (Montage, St.
Regis, Waldorf Astoria, Pendry), condo-hotels with a public front desk (Stein Eriksen Lodge, Grand Summit, Sundial,
Newpark), property-management condo complexes sold nightly (Deer Valley Resort Lodging, Park City Lodging, All Seasons,
Wyndham Vacation Rentals), private chalets and vacation-ownership clubs. A property is admitted ONLY as the exact hotel
/ lodge premises a public operator sells as a hotel, with its own official property page and an on-site operation; a
pet policy binds only to that premises (CONDO_HOTEL_RULE). Resort-wide or management-company policy is never attached
to a building without exact binding.

THE COTTONWOOD CANYONS (PHASE 6)
-------------------------------
Little Cottonwood Canyon (Snowbird, Alta) and Big Cottonwood Canyon (Solitude, Brighton) are ski-destination
inventory -- slope-side lodges, condominium lodges and seasonal mountain operations at the canyon tops, 25-35 miles
from downtown by a canyon road -- not Salt Lake City hotels. They share postal codes with valley suburbs (84092 with
east Sandy; 84121 with Cottonwood Heights), so they are refused by MUNICIPALITY on those codes (MUNICIPALITY_REFUSALS),
preserved for the FUTURE_STANDALONE cottonwood-canyons-ut. Nearness to Salt Lake City admits nothing.

TIMESHARE / VACATION OWNERSHIP (PHASE 7)
----------------------------------------
Club Wyndham, WorldMark, Marriott Vacation Club (MountainSide, Summit Watch), Hilton Grand Vacations (Sunrise Lodge),
Hyatt Vacation Club, Westgate (Park City Resort & Spa), Holiday Inn Club Vacations, Bluegreen and Diamond inventory is
TIMESHARE and never admitted, even when its brand lists it beside its hotels and even when a pet-policy page exists.

PREOPENING / SEASONAL / CLOSED (PHASE 9)
---------------------------------------
A seasonally operating ski hotel is a CURRENT business (held or published on its own policy); a preopening hotel never
publishes; a closed hotel never publishes. Decided per row from the property's own page, never from this module.

MILITARY / GOVERNMENT LODGING
-----------------------------
Hill Air Force Base (Davis County, 84056) is outside the partition; Camp W.G. Williams (Bluffdale, Utah National
Guard) and Fort Douglas's military lodging sell no public rooms -- their names are refused wherever they appear.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/salt_lake_city_ut.json
  launch_packages/pettripfinder/markets/proposed/salt-lake-city-ut.json
  launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_geography_001.json
  launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_corridor_registry_001.json
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

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
MARKET_ID = "salt-lake-city-ut"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "salt_lake_city_ut.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "salt-lake-city-ut.json")
REPORT_OUT = os.path.join(REPORTS, "salt_lake_city_ut_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "salt_lake_city_ut_corridor_registry_001.json")
#: Every REGISTERED market's own document: no postal code any of them admits may be admitted here.
REGISTERED_MARKETS_GLOB = os.path.join(PKG, "markets", "*.json")
AS_OF = "2026-10-07"
STATE_CODE = "UT"
STATE_CODES = ("UT",)


def state_for_postal(postal):
    """The state a postal code belongs to: Utah 840-847. A row's own page still decides; this is the check every
    stated state is held against. Neighbouring states are named so a stray out-of-state row is visible."""
    z = (postal or "").strip()[:3]
    if not z.isdigit():
        return ""
    n = int(z)
    if 840 <= n <= 847:
        return "UT"
    if 832 <= n <= 838:
        return "ID"
    if 820 <= n <= 831:
        return "WY"
    if 889 <= n <= 898:
        return "NV"
    if 800 <= n <= 816:
        return "CO"
    if 850 <= n <= 865:
        return "AZ"
    return ""


#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description, state)
CORRIDORS = [
    # ---------------------------------------------------------------- CORE (City of Salt Lake City)
    ("downtown-salt-lake-city", "Downtown Salt Lake City & Temple Square", "Downtown / Temple Square / City Creek / "
     "Salt Palace Convention Center / Delta Center / Gateway / Central City / Granary District / Capitol Hill / The "
     "Avenues / East Central", "CORE", "salt lake city", ["84101", "84102", "84103", "84111", "84150"],
     "Downtown Salt Lake City: Temple Square and the Church's own headquarters code (84150), the West Temple / South "
     "Temple hotel blocks, City Creek, the Salt Palace and the Delta Center (84101), Main and State Street and Central "
     "City east of State (84111), the Granary District south of 400 South (84101), Capitol Hill and the Avenues (84103) "
     "and East Central / 9th and 9th (84102). Temple Square, Central City and the Granary are reporting OVERLAYS "
     "decided by street and pin, never split codes.", "UT"),
    ("university-foothill", "University of Utah & Foothill", "University of Utah / Research Park / Fort Douglas / "
     "Foothill Drive / University Hospital", "CORE", "salt lake city", ["84108", "84112", "84113", "84132"],
     "The University of Utah campus (84112), Fort Douglas and its guest house (84113), the University Hospital and "
     "Huntsman campus (84132) and Research Park / Foothill Drive (84108).", "UT"),
    ("sugar-house", "Sugar House", "Sugar House / 2100 South / Highland Drive / Westminster / Liberty Wells",
     "CORE", "salt lake city", ["84105", "84106"],
     "Sugar House and Highland Drive (84106) and the Liberty Wells / 1300 East blocks north of it (84105). 84106 also "
     "carries South Salt Lake's and Millcreek's edges; it is covered whole and each row keeps its own municipality.",
     "UT"),
    ("slc-airport-west-side", "SLC Airport & North Temple", "Salt Lake City International Airport (SLC) / North "
     "Temple / Wright Brothers Drive / Admiral Byrd Road / Rose Park / Glendale / Redwood Road (north)", "CORE",
     "salt lake city", ["84116", "84122", "84104"],
     "The airport (84122) and its own hotel row on West North Temple, Wright Brothers Drive, Admiral Byrd Road and "
     "Amelia Earhart Drive (84116), and the west side between the airport and downtown (Rose Park, Glendale, Poplar "
     "Grove, 84116 / 84104). A hotel titled 'Salt Lake City Airport' in West Valley City or Woods Cross is placed by "
     "its own code.", "UT"),
    # ---------------------------------------------------------------- CORE (Park City / Wasatch Back)
    ("park-city", "Park City, Deer Valley & Historic Main Street", "Park City / Old Town / Historic Main Street / "
     "Deer Valley (Snow Park, Silver Lake) / Park Avenue / Prospector / Park Meadows / Bonanza Park", "CORE",
     "park city", ["84060", "84068"],
     "The CITY OF PARK CITY, Summit County: Old Town and Historic Main Street, Park City Mountain's Town Lift and "
     "Resort Center bases, Deer Valley's Snow Park and Silver Lake bases, Prospector, Park Meadows and Bonanza Park "
     "(84060) and the PO code (84068). Deer Valley and Historic Main Street are reporting OVERLAYS. Every row here is "
     "a PARK CITY row, never Salt Lake City. Deer Valley's East Village at Jordanelle lies in Wasatch County and each "
     "premises there is placed by the postal code its OWN page states: the Grand Hyatt Deer Valley and Canopy by "
     "Hilton Deer Valley state Park City, UT 84060 and are Park City rows; an East Village premises stating 84032 "
     "is OUTSIDE (heber-valley-ut).", "UT"),
    ("canyons-kimball-junction", "Canyons Village & Kimball Junction", "Canyons Village / Kimball Junction / "
     "Newpark / Snyderville Basin / Jeremy Ranch / Pinebrook / Summit Park", "CORE", "park city", ["84098"],
     "The Snyderville Basin, unincorporated Summit County, whose mailing name is Park City (84098): Canyons Village "
     "at Park City Mountain's Canyons base, the Kimball Junction / Newpark hotel cluster at I-80 exit 145, Jeremy "
     "Ranch, Pinebrook and Summit Park. Canyons Village and Kimball Junction are reporting OVERLAYS. Every row here "
     "is a PARK CITY row, never Salt Lake City.", "UT"),
    # ---------------------------------------------------------------- STRONG CORRIDOR (Salt Lake County)
    ("south-salt-lake-millcreek", "South Salt Lake & Millcreek", "South Salt Lake / Ballpark / Central Pointe / "
     "Millcreek / East Millcreek / Olympus Cove / 3300 South", "CORRIDOR", "south salt lake", ["84115", "84109"],
     "The CITY OF SOUTH SALT LAKE and Salt Lake City's Ballpark / Central Ninth blocks (84115) and MILLCREEK and Salt "
     "Lake City's east bench (84109). Each row keeps its own municipality. STRONG.", "UT"),
    ("murray", "Murray", "Murray / Fashion Place / Intermountain Medical Center / I-215 & State Street / Murray Park",
     "CORRIDOR", "murray", ["84107", "84123", "84157"],
     "The CITY OF MURRAY: the Fashion Place / Intermountain Medical Center / I-215 hotel row (84107) and Murray's west "
     "side shared with Taylorsville (84123), and the PO code (84157). STRONG.", "UT"),
    ("midvale", "Midvale", "Midvale / Fort Union / 7200 South / I-15 & Jordan River", "CORRIDOR", "midvale",
     ["84047"],
     "The CITY OF MIDVALE: the 7200 South / Fort Union / Union Park Avenue hotel cluster at I-15 and I-215 (84047). "
     "STRONG.", "UT"),
    ("sandy", "Sandy", "Sandy / South Towne / Mountain America Expo Center / America First Field / 10600 South / State "
     "Street", "CORRIDOR", "sandy", ["84070", "84090", "84091", "84092", "84093", "84094"],
     "The CITY OF SANDY: the South Towne / Mountain America Expo Center / 10600 South hotel cluster (84070), America "
     "First Field and east Sandy (84092 / 84093 / 84094) and the PO codes (84090 / 84091). 84092 also carries the "
     "Little Cottonwood Canyon resorts (Snowbird, Alta): those are refused BY MUNICIPALITY (cottonwood-canyons-ut). "
     "STRONG.", "UT"),
    ("south-jordan", "South Jordan", "South Jordan / Daybreak / River Park / 10600 South & Bangerter / Jordan "
     "Landing (east)", "CORRIDOR", "south jordan", ["84095", "84009"],
     "The CITY OF SOUTH JORDAN: the River Park / 10600 South hotel cluster on I-15 (84095) and Daybreak (84009). "
     "STRONG.", "UT"),
    ("west-jordan", "West Jordan", "West Jordan / Jordan Landing / Bangerter Highway / Mountain View Corridor",
     "CORRIDOR", "west jordan", ["84084", "84088", "84081"],
     "The CITY OF WEST JORDAN: Jordan Landing and Bangerter Highway (84084 / 84088) and the Mountain View Corridor "
     "edge (84081). STRONG.", "UT"),
    ("draper", "Draper", "Draper / Point of the Mountain / I-15 & 12300 South / Bangerter Parkway", "CORRIDOR",
     "draper", ["84020"],
     "The CITY OF DRAPER: the 12300 South / Bangerter Parkway / Point of the Mountain hotel cluster on I-15 (84020). "
     "STRONG.", "UT"),
    ("west-valley-city", "West Valley City", "West Valley City / Maverik Center / Valley Fair / 3500 South / 2100 "
     "South & Redwood Road / Bangerter Highway / Magna", "CORRIDOR", "west valley city",
     ["84119", "84120", "84128", "84044"],
     "The CITY OF WEST VALLEY CITY: the Maverik Center / Valley Fair / 3500 South cluster and the 2100 South / Redwood "
     "Road / Bangerter Highway hotels marketed 'Salt Lake City Airport' (84119 / 84120 / 84128), and Magna (84044). "
     "STRONG.", "UT"),
    ("cottonwood-heights-holladay", "Cottonwood Heights & Holladay", "Cottonwood Heights / Fort Union Boulevard / "
     "Holladay / Big Cottonwood Canyon mouth / 6200 South & I-215", "CORRIDOR", "cottonwood heights",
     ["84121", "84117", "84124"],
     "The CITY OF COTTONWOOD HEIGHTS (84121) and the CITY OF HOLLADAY (84117 / 84124). 84121 also carries the Big "
     "Cottonwood Canyon resorts (Solitude, Brighton): those are refused BY MUNICIPALITY (cottonwood-canyons-ut). "
     "STRONG.", "UT"),
    # ---------------------------------------------------------------- FRINGE (CAREFUL evaluation)
    ("taylorsville-kearns", "Taylorsville & Kearns", "Taylorsville / Kearns / Redwood Road (south) / 5400 South",
     "FRINGE", "taylorsville", ["84129", "84118"],
     "The CITY OF TAYLORSVILLE (84129) and Kearns (84118). Admitted at FRINGE after CAREFUL evaluation.", "UT"),
    ("riverton-herriman-bluffdale", "Riverton, Herriman & Bluffdale", "Riverton / Herriman / Bluffdale / Bangerter "
     "Highway (south) / Mountain View Corridor (south)", "FRINGE", "riverton", ["84065", "84096"],
     "The CITY OF RIVERTON and Bluffdale (84065) and HERRIMAN (84096). Camp W.G. Williams's military lodging is "
     "refused by name. Admitted at FRINGE after CAREFUL evaluation.", "UT"),
    ("lehi", "Lehi", "Lehi / Thanksgiving Point / Silicon Slopes / Traverse Mountain / I-15 Point of the Mountain "
     "(south)", "FRINGE", "lehi", ["84043"],
     "The CITY OF LEHI, Utah County: the Thanksgiving Point / Silicon Slopes / Traverse Mountain hotel cluster on "
     "I-15, metro-continuous with Draper across the Point of the Mountain (84043). Admitted at FRINGE after CAREFUL "
     "evaluation; American Fork, Orem, Provo and the rest of Utah County are refused (provo-orem-ut).", "UT"),
    ("north-salt-lake-bountiful", "North Salt Lake & Bountiful", "North Salt Lake / Woods Cross / West Bountiful / "
     "Bountiful / I-15 (Davis County south)", "FRINGE", "bountiful", ["84054", "84010", "84011", "84087"],
     "South Davis County's metro-continuous edge with Salt Lake City: NORTH SALT LAKE (84054), WOODS CROSS and WEST "
     "BOUNTIFUL (84087) and BOUNTIFUL (84010 / 84011). Admitted at FRINGE after CAREFUL evaluation; Centerville, "
     "Farmington, Kaysville, Layton and the rest of Davis County are refused (ogden-ut).", "UT"),
]

OUTSIDE = [
    ("Provo / Orem / American Fork / Pleasant Grove / Lindon / Saratoga Springs / Eagle Mountain / Alpine -- Utah "
     "County beyond Lehi", "UT",
     ["84003", "84004", "84005", "84013", "84042", "84045", "84057", "84058", "84059", "84062", "84097",
      "84601", "84602", "84603", "84604", "84605", "84606"],
     "UTAH COUNTY; FUTURE_STANDALONE provo-orem-ut. Provo / Orem and BYU / UVU are 40-45 miles south on I-15 -- a "
     "trip of their own, never absorbed. Refused by postal code and by PREFIX (846)."),
    ("Ogden / Layton / Kaysville / Farmington / Centerville / Clearfield / Syracuse -- Davis County beyond Bountiful "
     "and Weber County", "UT",
     ["84014", "84015", "84016", "84025", "84037", "84040", "84041", "84056", "84067", "84075", "84089"],
     "DAVIS / WEBER COUNTY; FUTURE_STANDALONE ogden-ut. Centerville, Farmington (Station Park, Lagoon), Kaysville, "
     "Layton and Clearfield north to Ogden. Hill Air Force Base (84056) is military. Refused by postal code and by "
     "PREFIX (844)."),
    ("Heber City / Midway / Jordanelle / Deer Valley East Village -- Wasatch County", "UT",
     ["84032", "84049", "84082"],
     "WASATCH COUNTY; FUTURE_STANDALONE heber-valley-ut. The Heber Valley (Heber City, Midway, Charleston) and the "
     "Jordanelle Reservoir premises that state 84032 are a valley of their own east of the Wasatch Back. A 'Deer "
     "Valley' or 'Park City' marketing NAME admits nothing; only the postal code the premises' own page states does "
     "(Deer Valley East Village hotels whose own pages state Park City, UT 84060 are Park City rows)."),
    ("Kamas / Oakley / Coalville / Wanship / Francis / Woodland -- eastern Summit County", "UT",
     ["84017", "84024", "84033", "84036", "84055", "84061"],
     "EASTERN SUMMIT COUNTY beyond the Snyderville Basin. Refused after careful evaluation (recorded in the boundary "
     "audit)."),
    ("Snowbird / Alta -- Little Cottonwood Canyon", "UT", [],
     "SALT LAKE COUNTY canyon resorts; FUTURE_STANDALONE cottonwood-canyons-ut. Refused BY MUNICIPALITY on 84092 "
     "(MUNICIPALITY_REFUSALS) -- a ski-destination lodging inventory, not a Salt Lake City hotel."),
    ("Solitude / Brighton -- Big Cottonwood Canyon", "UT", [],
     "SALT LAKE COUNTY canyon resorts; FUTURE_STANDALONE cottonwood-canyons-ut. Refused BY MUNICIPALITY on 84121 "
     "(MUNICIPALITY_REFUSALS)."),
    ("Tooele / Grantsville / Stansbury Park / Wendover -- Tooele County", "UT",
     ["84029", "84074", "84083", "84022", "84071", "84080"],
     "TOOELE COUNTY, west across the Oquirrh Mountains. Refused after careful evaluation."),
    ("Logan / Brigham City / Cache Valley / Bear Lake", "UT", ["84321", "84322", "84341", "84302", "84028"],
     "CACHE / BOX ELDER / RICH COUNTY; FUTURE_STANDALONE logan-ut and bear-lake-ut. Refused by PREFIX (843) and by "
     "postal code (Garden City / Bear Lake 84028)."),
    ("Moab / Price / south-east Utah", "UT", ["84532", "84501", "84535"],
     "GRAND / CARBON / SAN JUAN COUNTY; FUTURE_STANDALONE moab-ut. Refused by PREFIX (845)."),
    ("St. George / Cedar City / Springdale (Zion) / Bryce Canyon / Kanab -- southern Utah", "UT",
     ["84770", "84790", "84720", "84767", "84764", "84741", "84759"],
     "WASHINGTON / IRON / KANE / GARFIELD COUNTY; FUTURE_STANDALONE st-george-ut, zion-springdale-ut and "
     "bryce-canyon-ut. Refused by PREFIX (847)."),
    ("Greater Utah and out of state", "--", [],
     "Every other Utah postal code no corridor claims, and every code outside Utah, is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("843", "Logan / Brigham City / Cache Valley", "logan-ut"),
    ("844", "Ogden / Weber County", "ogden-ut"),
    ("845", "Price / Moab / south-east Utah", "moab-ut"),
    ("846", "Provo / Utah County south", "provo-orem-ut"),
    ("847", "St. George / Cedar City / Zion / Bryce / southern Utah", "st-george-ut"),
]

#: The Salt Lake City sectional centers. A code under one of these that no corridor claims and no OUTSIDE row names
#: is an UNCLAIMED regional code -- refused, and named in the boundary audit so it is visible, never silently dropped.
VALLEY_PREFIXES = ("840", "841")

#: The county each admitted code is in, and the REAL municipalities its premises are in. The municipality is what a
#: row publishes; "salt lake city" is the real municipality only where the code carries it, and "park city" only for
#: a Summit County Park City / Snyderville Basin code. Where one code spans more than one municipality the tuple lists
#: every one (principal first), and the row's own stated municipality must be one of them.
#: (The inherited consumer name POSTAL_PARISH is kept: every downstream module reads it.)
POSTAL_PARISH = OrderedDict([
    ("84101", ("Salt Lake", ("salt lake city",))),
    ("84102", ("Salt Lake", ("salt lake city",))),
    ("84103", ("Salt Lake", ("salt lake city",))),
    ("84111", ("Salt Lake", ("salt lake city",))),
    ("84150", ("Salt Lake", ("salt lake city",))),
    ("84108", ("Salt Lake", ("salt lake city",))),
    ("84112", ("Salt Lake", ("salt lake city",))),
    ("84113", ("Salt Lake", ("salt lake city",))),
    ("84132", ("Salt Lake", ("salt lake city",))),
    ("84105", ("Salt Lake", ("salt lake city",))),
    ("84106", ("Salt Lake", ("salt lake city", "south salt lake", "millcreek"))),
    ("84116", ("Salt Lake", ("salt lake city",))),
    ("84122", ("Salt Lake", ("salt lake city",))),
    ("84104", ("Salt Lake", ("salt lake city",))),
    ("84060", ("Summit", ("park city",))),
    ("84068", ("Summit", ("park city",))),
    ("84098", ("Summit", ("park city",))),
    ("84115", ("Salt Lake", ("south salt lake", "salt lake city", "millcreek"))),
    ("84109", ("Salt Lake", ("salt lake city", "millcreek"))),
    ("84107", ("Salt Lake", ("murray", "millcreek"))),
    ("84123", ("Salt Lake", ("murray", "taylorsville"))),
    ("84157", ("Salt Lake", ("murray",))),
    ("84047", ("Salt Lake", ("midvale",))),
    ("84070", ("Salt Lake", ("sandy",))),
    ("84090", ("Salt Lake", ("sandy",))),
    ("84091", ("Salt Lake", ("sandy",))),
    ("84092", ("Salt Lake", ("sandy",))),
    ("84093", ("Salt Lake", ("sandy", "cottonwood heights"))),
    ("84094", ("Salt Lake", ("sandy",))),
    ("84095", ("Salt Lake", ("south jordan",))),
    ("84009", ("Salt Lake", ("south jordan",))),
    ("84084", ("Salt Lake", ("west jordan",))),
    ("84088", ("Salt Lake", ("west jordan",))),
    ("84081", ("Salt Lake", ("west jordan",))),
    ("84020", ("Salt Lake", ("draper",))),
    ("84119", ("Salt Lake", ("west valley city", "taylorsville"))),
    ("84120", ("Salt Lake", ("west valley city",))),
    ("84128", ("Salt Lake", ("west valley city",))),
    ("84044", ("Salt Lake", ("magna",))),
    ("84121", ("Salt Lake", ("cottonwood heights", "holladay", "sandy", "murray"))),
    ("84117", ("Salt Lake", ("holladay", "murray", "cottonwood heights", "millcreek"))),
    ("84124", ("Salt Lake", ("holladay", "millcreek"))),
    ("84129", ("Salt Lake", ("taylorsville",))),
    ("84118", ("Salt Lake", ("kearns", "taylorsville", "west valley city"))),
    ("84065", ("Salt Lake", ("riverton", "bluffdale", "herriman"))),
    ("84096", ("Salt Lake", ("herriman", "riverton", "bluffdale"))),
    ("84043", ("Utah", ("lehi",))),
    ("84054", ("Davis", ("north salt lake",))),
    ("84010", ("Davis", ("bountiful", "west bountiful", "woods cross"))),
    ("84011", ("Davis", ("bountiful",))),
    ("84087", ("Davis", ("woods cross", "west bountiful"))),
])
POSTAL_COUNTY = POSTAL_PARISH

#: How each real municipality is written when it is published.
MUNICIPALITY_DISPLAY = {
    "salt lake city": "Salt Lake City", "park city": "Park City", "south salt lake": "South Salt Lake",
    "millcreek": "Millcreek", "murray": "Murray", "taylorsville": "Taylorsville", "midvale": "Midvale",
    "sandy": "Sandy", "cottonwood heights": "Cottonwood Heights", "south jordan": "South Jordan",
    "west jordan": "West Jordan", "draper": "Draper", "west valley city": "West Valley City", "magna": "Magna",
    "holladay": "Holladay", "kearns": "Kearns", "riverton": "Riverton", "bluffdale": "Bluffdale",
    "herriman": "Herriman", "lehi": "Lehi", "north salt lake": "North Salt Lake", "bountiful": "Bountiful",
    "west bountiful": "West Bountiful", "woods cross": "Woods Cross",
}

ADMITTED_PARISHES = {"salt lake (salt lake city: downtown, temple square, central city, granary, capitol hill, the "
                     "avenues, university, sugar house, the airport and the west side; south salt lake, millcreek, "
                     "murray, midvale, sandy, south jordan, west jordan, draper, west valley city, magna, cottonwood "
                     "heights, holladay, taylorsville, kearns, riverton, herriman, bluffdale; the cottonwood canyon "
                     "resorts refused)",
                     "summit (park city, deer valley, canyons village, kimball junction, the snyderville basin; "
                     "kamas, oakley and coalville refused)",
                     "utah (lehi only; american fork, orem, provo and the rest refused)",
                     "davis (north salt lake, woods cross, west bountiful, bountiful; centerville north refused)"}
OBSERVED_PARISHES = OrderedDict([
    ("utah county beyond lehi (american fork, orem, provo)", "provo-orem-ut"),
    ("davis county beyond bountiful, and weber county (farmington, layton, ogden)", "ogden-ut"),
    ("wasatch county (heber city, midway, jordanelle / deer valley east village)", "heber-valley-ut"),
    ("salt lake county canyon resorts (snowbird, alta, solitude, brighton)", "cottonwood-canyons-ut"),
    ("eastern summit county (kamas, oakley, coalville)", "(none -- refused after careful evaluation)"),
    ("tooele county (tooele, grantsville)", "(none -- refused after careful evaluation)"),
    ("cache / box elder / rich county (logan, brigham city, bear lake)", "logan-ut / bear-lake-ut"),
    ("grand county (moab)", "moab-ut"),
    ("washington / iron / kane / garfield county (st. george, springdale, bryce)",
     "st-george-ut / zion-springdale-ut / bryce-canyon-ut"),
])
#: Inherited consumer name (the cross-county audit slot).
OBSERVED_COUNTIES = OBSERVED_PARISHES
ADMITTED_COUNTIES = ADMITTED_PARISHES

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("salt lake", OrderedDict([
        ("ruling", "ADMITTED, MUNICIPALITIES PRESERVED. Salt Lake City and every valley municipality the order "
                   "evaluates are admitted, each row keeping its own municipality. The Cottonwood Canyon resorts "
                   "(Snowbird, Alta, Solitude, Brighton) are refused by municipality (cottonwood-canyons-ut)."),
    ])),
    ("summit", OrderedDict([
        ("ruling", "ADMITTED AT PARK CITY AND THE SNYDERVILLE BASIN ONLY (84060 / 84068 / 84098). Every row is a PARK "
                   "CITY row. Kamas, Oakley, Coalville and Wanship are refused."),
    ])),
    ("utah", OrderedDict([
        ("ruling", "ADMITTED ONLY AT LEHI (FRINGE). American Fork, Pleasant Grove, Orem, Provo and the rest of Utah "
                   "County are refused (provo-orem-ut)."),
    ])),
    ("davis", OrderedDict([
        ("ruling", "ADMITTED ONLY AT NORTH SALT LAKE / WOODS CROSS / WEST BOUNTIFUL / BOUNTIFUL (FRINGE). "
                   "Centerville, Farmington, Kaysville, Layton, Clearfield and Hill AFB are refused (ogden-ut)."),
    ])),
    ("wasatch", OrderedDict([
        ("ruling", "REFUSED. Heber City, Midway and the Jordanelle premises stating 84032 / 84049 / 84082 are a valley "
                   "of their own (heber-valley-ut); a 'Deer Valley' marketing name admits nothing. A Deer Valley "
                   "East Village hotel whose OWN page states Park City, UT 84060 is placed by that code."),
    ])),
    ("weber / tooele / cache / grand / washington / iron / kane", OrderedDict([
        ("ruling", "REFUSED. Ogden, Tooele, Logan, Moab, St. George, Springdale / Zion and Bryce Canyon are not "
                   "absorbed (FUTURE_STANDALONE ogden-ut, logan-ut, moab-ut, st-george-ut, zion-springdale-ut, "
                   "bryce-canyon-ut)."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / patient / member
#: only). A normalised-name substring match; the census row keeps its reason.
NONPUBLIC_NAMES = {
    "camp williams": "Camp W.G. Williams (Utah National Guard) lodging -- MILITARY_RESTRICTED",
    "camp w g williams": "Camp W.G. Williams (Utah National Guard) lodging -- MILITARY_RESTRICTED",
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- MILITARY_RESTRICTED",
    "navy lodge": "Navy Lodge on-base lodging -- MILITARY_RESTRICTED",
    "navy gateway inns": "Navy Gateway Inns & Suites on-base lodging -- MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "hill afb": "Hill Air Force Base lodging -- MILITARY_RESTRICTED",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "hope lodge": "American Cancer Society Hope Lodge -- patient lodging, not public lodging",
    "family housing": "patient-family housing -- not public lodging",
    "patient housing": "patient housing -- not public lodging",
    "rescue mission": "rescue mission shelter -- not public lodging",
    "homeless": "shelter -- not public lodging",
    "road home": "The Road Home shelter -- not public lodging",
    "youth shelter": "youth shelter -- not public lodging",
    "enlisted quarters": "military enlisted quarters (Camp W.G. Williams) -- MILITARY_RESTRICTED",
    "officers quarters": "military officers quarters -- MILITARY_RESTRICTED",
    "bachelor quarters": "military bachelor quarters -- MILITARY_RESTRICTED",
}

#: Military postal codes inside the admitted partition. None: Hill AFB (84056) is claimed by no corridor.
MILITARY_POSTAL_CODES = OrderedDict()

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-salt-lake-city", "Salt Lake City", "Downtown / Temple Square / Central City / Granary", 40.7620,
     -111.8900, 3000, True),
    ("university-foothill", "Salt Lake City", "University of Utah / Foothill", 40.7600, -111.8400, 2500, True),
    ("sugar-house", "Salt Lake City", "Sugar House", 40.7230, -111.8600, 2500, True),
    ("slc-airport-west-side", "Salt Lake City", "SLC Airport / North Temple / west side", 40.7750, -111.9500, 6000,
     True),
    ("park-city", "Park City", "Park City / Old Town / Main Street / Deer Valley", 40.6450, -111.5000, 4500, True),
    ("canyons-kimball-junction", "Park City", "Canyons Village / Kimball Junction", 40.7000, -111.5500, 5000, True),
    ("south-salt-lake-millcreek", "South Salt Lake", "South Salt Lake / Millcreek", 40.7000, -111.8650, 3500, True),
    ("murray", "Murray", "Murray", 40.6600, -111.8900, 3500, True),
    ("midvale", "Midvale", "Midvale", 40.6150, -111.8900, 2500, True),
    ("sandy", "Sandy", "Sandy / South Towne", 40.5650, -111.8600, 5000, True),
    ("south-jordan", "South Jordan", "South Jordan / Daybreak", 40.5600, -111.9500, 5000, True),
    ("west-jordan", "West Jordan", "West Jordan", 40.6050, -111.9750, 5000, True),
    ("draper", "Draper", "Draper", 40.5250, -111.8700, 4000, True),
    ("west-valley-city", "West Valley City", "West Valley City", 40.6900, -111.9700, 6000, True),
    ("cottonwood-heights-holladay", "Cottonwood Heights", "Cottonwood Heights / Holladay", 40.6350, -111.8250, 4000,
     True),
    ("taylorsville-kearns", "Taylorsville", "Taylorsville / Kearns", 40.6550, -111.9600, 4000, True),
    ("riverton-herriman-bluffdale", "Riverton", "Riverton / Herriman / Bluffdale", 40.5050, -111.9500, 5500, True),
    ("lehi", "Lehi", "Lehi / Thanksgiving Point", 40.4100, -111.8800, 5000, True),
    ("north-salt-lake-bountiful", "Bountiful", "North Salt Lake / Woods Cross / Bountiful", 40.8650, -111.8950,
     5000, True),
    ("obs-provo-orem", "Provo", "Provo / Orem / American Fork -- OBSERVATION ONLY", 40.3000, -111.6900, 18000, False),
    ("obs-davis-ogden", "Ogden", "Farmington / Layton / Ogden -- OBSERVATION ONLY", 41.0800, -111.9600, 20000,
     False),
    ("obs-heber-valley", "Heber City", "Heber City / Midway / Jordanelle -- OBSERVATION ONLY", 40.5300, -111.4300,
     12000, False),
    ("obs-cottonwood-canyons", "Alta", "Snowbird / Alta / Solitude / Brighton -- OBSERVATION ONLY", 40.6000,
     -111.6300, 9000, False),
    ("obs-tooele", "Tooele", "Tooele / Grantsville -- OBSERVATION ONLY", 40.5600, -112.3300, 12000, False),
    ("obs-eastern-summit", "Kamas", "Kamas / Oakley / Coalville -- OBSERVATION ONLY", 40.7800, -111.3500, 15000,
     False),
]

#: The observation box. It reaches south past Provo, north past Ogden, west to Tooele and Grantsville and east across
#: the Wasatch Back to Heber City, Kamas and Coalville, so the census counts what it refuses. Utah beyond it (Logan,
#: Moab, St. George, Springdale, Bryce) is MEASURED statewide by the OpenStreetMap lane for the boundary audit only.
BOUNDS = {"min_lat": 39.95, "max_lat": 41.35, "min_lng": -112.55, "max_lng": -111.15}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
#: Listed most-specific first; the nearest anchor within its radius wins.
COVERAGE_AREAS = [
    ("Temple Square", 40.7705, -111.8920, 0.45),
    ("Historic Main Street", 40.6430, -111.4960, 0.45),
    ("Canyons Village", 40.6850, -111.5560, 1.20),
    ("Kimball Junction", 40.7230, -111.5420, 2.20),
    ("Deer Valley", 40.6270, -111.4880, 2.20),
    ("Granary District", 40.7520, -111.9000, 0.70),
    ("Central City", 40.7560, -111.8770, 0.80),
    ("Downtown Salt Lake City", 40.7630, -111.8930, 1.20),
    ("Capitol Hill / Avenues", 40.7800, -111.8780, 1.10),
    ("University / Foothill", 40.7640, -111.8400, 2.20),
    ("Sugar House", 40.7230, -111.8580, 1.60),
    ("SLC Airport", 40.7750, -111.9550, 3.80),
    ("Park City", 40.6550, -111.5000, 2.80),
    ("South Salt Lake", 40.7120, -111.8900, 1.80),
    ("Millcreek", 40.6880, -111.8450, 2.40),
    ("Murray", 40.6600, -111.8900, 2.40),
    ("Midvale", 40.6120, -111.8900, 2.00),
    ("Cottonwood Heights / Holladay", 40.6350, -111.8250, 3.20),
    ("Sandy", 40.5650, -111.8600, 3.80),
    ("South Jordan", 40.5600, -111.9350, 3.50),
    ("West Jordan", 40.6050, -111.9750, 3.80),
    ("Draper", 40.5250, -111.8700, 3.20),
    ("West Valley City", 40.6900, -111.9700, 4.50),
    ("Taylorsville / Kearns", 40.6550, -111.9600, 2.50),
    ("Riverton / Herriman / Bluffdale", 40.5050, -111.9550, 4.50),
    ("Lehi", 40.4100, -111.8800, 4.50),
    ("North Salt Lake / Bountiful", 40.8650, -111.8950, 4.50),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin). Reporting only.
STREET_OVERLAYS = [
    ("Historic Main Street", re.compile(r"^\s*\d+[a-z]?\s+(main (st|street)|swede alley|heber ave(nue)?)\b"
                                        r"(?=.*\b84060\b)", re.I)),
    ("Deer Valley", re.compile(r"\b(deer valley (dr|drive)|marsac|royal (st|street)|silver lake|sterling (ct|court)|"
                               r"stein way|empire (club )?(dr|drive)|guardsman|deer hollow|white pine canyon)\b"
                               r"(?=.*\b84060\b)", re.I)),
    ("Canyons Village", re.compile(r"\b(canyons resort (dr|drive)|grand summit|sundial (ct|court)|frostwood|"
                                   r"high mountain (rd|road)|lower village (rd|road)|cooper lane|"
                                   r"escala (ct|court))\b(?=.*\b84098\b)", re.I)),
    ("Kimball Junction", re.compile(r"\b(landmark (dr|drive)|newpark|ute (blvd|boulevard)|olympic (pkwy|parkway)|"
                                    r"rasmussen|kimball|old ranch (rd|road)|bitner|cutter lane|"
                                    r"overland (dr|drive))\b(?=.*\b84098\b)", re.I)),
    ("SLC Airport", re.compile(r"\b(n(orth)?\.? temple|wright brothers|terminal (dr|drive)|admiral byrd|"
                               r"amelia earhart|jimmy doolittle|charles lindbergh|john glenn|lindbergh|"
                               r"bangerter)\b(?=.*\b841(16|22)\b)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-salt-lake-city": "Downtown Salt Lake City",
    "university-foothill": "University / Foothill",
    "sugar-house": "Sugar House",
    "slc-airport-west-side": "SLC Airport",
    "park-city": "Park City",
    "canyons-kimball-junction": "Kimball Junction",
    "south-salt-lake-millcreek": "South Salt Lake",
    "murray": "Murray",
    "midvale": "Midvale",
    "sandy": "Sandy",
    "south-jordan": "South Jordan",
    "west-jordan": "West Jordan",
    "draper": "Draper",
    "west-valley-city": "West Valley City",
    "cottonwood-heights-holladay": "Cottonwood Heights / Holladay",
    "taylorsville-kearns": "Taylorsville / Kearns",
    "riverton-herriman-bluffdale": "Riverton / Herriman / Bluffdale",
    "lehi": "Lehi",
    "north-salt-lake-bountiful": "North Salt Lake / Bountiful",
}

#: The order's CORE / STRONG / PARK CITY / CAREFUL / KEEP-SEPARATE evaluation list, each classified.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Salt Lake City", "ADMITTED (CORE, downtown-salt-lake-city, 84101 / 84111 / 84150)."),
    ("Temple Square", "ADMITTED (CORE, downtown-salt-lake-city, 84150 / 84101) -- overlay."),
    ("Central City", "ADMITTED (CORE, downtown-salt-lake-city, 84111) -- overlay."),
    ("Granary / Downtown South", "ADMITTED (CORE, downtown-salt-lake-city, 84101) -- overlay."),
    ("University / Foothill", "ADMITTED (CORE, university-foothill, 84108 / 84112 / 84113 / 84132)."),
    ("Sugar House", "ADMITTED (CORE, sugar-house, 84105 / 84106)."),
    ("Salt Lake City International Airport / SLC", "ADMITTED (CORE, slc-airport-west-side, 84122 / 84116 / 84104). "
                                                   "Municipality SALT LAKE CITY; 'Airport' hotels in West Valley City "
                                                   "or Woods Cross keep their own municipality."),
    ("Murray", "ADMITTED (STRONG CORRIDOR, murray, 84107 / 84123 / 84157)."),
    ("Midvale", "ADMITTED (STRONG CORRIDOR, midvale, 84047)."),
    ("Sandy", "ADMITTED (STRONG CORRIDOR, sandy, 84070 / 84090-84094); Snowbird and Alta refused by municipality."),
    ("South Jordan", "ADMITTED (STRONG CORRIDOR, south-jordan, 84095 / 84009)."),
    ("West Jordan", "ADMITTED (STRONG CORRIDOR, west-jordan, 84084 / 84088 / 84081)."),
    ("Draper", "ADMITTED (STRONG CORRIDOR, draper, 84020)."),
    ("West Valley City", "ADMITTED (STRONG CORRIDOR, west-valley-city, 84119 / 84120 / 84128; Magna 84044)."),
    ("Cottonwood Heights", "ADMITTED (STRONG CORRIDOR, cottonwood-heights-holladay, 84121); Solitude and Brighton "
                           "refused by municipality."),
    ("Holladay", "ADMITTED (STRONG CORRIDOR, cottonwood-heights-holladay, 84117 / 84124)."),
    ("Millcreek", "ADMITTED (STRONG CORRIDOR, south-salt-lake-millcreek, 84109; Millcreek rows in 84106 / 84115 / "
                  "84117 / 84124 keep their municipality)."),
    ("South Salt Lake", "ADMITTED (STRONG CORRIDOR, south-salt-lake-millcreek, 84115)."),
    ("Park City", "ADMITTED (CORE, park-city, 84060 / 84068). Municipality PARK CITY."),
    ("Historic Main Street", "ADMITTED (CORE, park-city, 84060) -- overlay."),
    ("Deer Valley", "ADMITTED (CORE, park-city, 84060) -- overlay; a Deer Valley East Village premises at Jordanelle "
                    "(Wasatch County) is placed by the code its own page states: 84060 admits it as Park City (Grand "
                    "Hyatt Deer Valley, Canopy by Hilton Deer Valley), 84032 refuses it (heber-valley-ut)."),
    ("Canyons Village", "ADMITTED (CORE, canyons-kimball-junction, 84098) -- overlay. Municipality PARK CITY."),
    ("Kimball Junction", "ADMITTED (CORE, canyons-kimball-junction, 84098) -- overlay. Municipality PARK CITY."),
    ("Lehi", "ADMITTED (FRINGE, lehi, 84043). CAREFUL: metro-continuous with Draper across the Point of the Mountain."),
    ("Riverton", "ADMITTED (FRINGE, riverton-herriman-bluffdale, 84065 / 84096). CAREFUL."),
    ("Taylorsville", "ADMITTED (FRINGE, taylorsville-kearns, 84129 / 84118; Taylorsville rows in 84119 / 84123 keep "
                     "their municipality). CAREFUL."),
    ("North Salt Lake", "ADMITTED (FRINGE, north-salt-lake-bountiful, 84054). CAREFUL."),
    ("Bountiful", "ADMITTED (FRINGE, north-salt-lake-bountiful, 84010 / 84011 / 84087). CAREFUL."),
    ("Heber City", "OUTSIDE -- FUTURE_STANDALONE heber-valley-ut (84032). CAREFUL evaluation: the Heber Valley is a "
                   "valley of its own; better standalone."),
    ("Midway", "OUTSIDE -- FUTURE_STANDALONE heber-valley-ut (84049). CAREFUL evaluation: better standalone."),
    ("Little Cottonwood Canyon (Snowbird, Alta)", "OUTSIDE -- FUTURE_STANDALONE cottonwood-canyons-ut; refused by "
                                                  "municipality on 84092."),
    ("Big Cottonwood Canyon (Solitude, Brighton)", "OUTSIDE -- FUTURE_STANDALONE cottonwood-canyons-ut; refused by "
                                                   "municipality on 84121."),
    ("Provo / Orem", "OUTSIDE -- FUTURE_STANDALONE provo-orem-ut; refused by postal code and prefix 846. KEEP "
                     "SEPARATE."),
    ("Ogden", "OUTSIDE -- FUTURE_STANDALONE ogden-ut; refused by prefix 844 and Davis County codes. KEEP SEPARATE."),
    ("Moab", "OUTSIDE -- FUTURE_STANDALONE moab-ut; refused by prefix 845. KEEP SEPARATE."),
    ("St. George", "OUTSIDE -- FUTURE_STANDALONE st-george-ut; refused by prefix 847. KEEP SEPARATE."),
    ("Zion / Springdale", "OUTSIDE -- FUTURE_STANDALONE zion-springdale-ut; refused by prefix 847. KEEP SEPARATE."),
    ("Bryce Canyon", "OUTSIDE -- FUTURE_STANDALONE bryce-canyon-ut; refused by prefix 847. KEEP SEPARATE."),
    ("Logan", "OUTSIDE -- FUTURE_STANDALONE logan-ut; refused by prefix 843. KEEP SEPARATE."),
    ("Bear Lake", "OUTSIDE -- FUTURE_STANDALONE bear-lake-ut; refused by postal code 84028. KEEP SEPARATE."),
])

#: The airport ruling, stated once.
SLC_AIRPORT_EVALUATION = OrderedDict([
    ("airport_terminal", "Salt Lake City International Airport (SLC) is in the CITY OF SALT LAKE CITY, 84122. No hotel "
                         "stands inside the terminal."),
    ("airport_hotel_row", "The airport's own hotel row -- West North Temple, Wright Brothers Drive, Admiral Byrd Road, "
                          "Amelia Earhart Drive, Jimmy Doolittle Road -- is 84116 / 84122: the slc-airport-west-side "
                          "corridor, municipality SALT LAKE CITY."),
    ("airport_marketed_elsewhere", "'Salt Lake City Airport' hotels on 2100 South / Bangerter Highway / 3500 South in "
                                   "West Valley City (84119 / 84120 / 84128) and in Woods Cross / North Salt Lake are "
                                   "placed by their own code and keep their own municipality."),
    ("one_premises_one_row", "A property is one row however many of 'Airport', 'SLC', 'Salt Lake', 'Downtown' and "
                             "'Temple Square' its marketing carries; identity is its own street address, phone and "
                             "brand property code."),
])

#: The Park City / Wasatch Back ruling (Phase 3).
PARK_CITY_EVALUATION = OrderedDict([
    ("park_city_identity", "Park City (84060 / 84068) and the Snyderville Basin (84098, mailing name Park City) are "
                           "PARK CITY rows. A Park City row is NEVER written as Salt Lake City, whatever 'Salt Lake' "
                           "its marketing carries."),
    ("deer_valley", "Deer Valley's Snow Park and Silver Lake bases are in the City of Park City (84060). Deer Valley "
                    "East Village at Jordanelle lies in Wasatch County; its hotels are placed by the code their own "
                    "pages state -- the Grand Hyatt Deer Valley and Canopy by Hilton Deer Valley state Park City, UT "
                    "84060 (Park City rows; the postal-code county field reads Summit for them), and a premises "
                    "stating 84032 is OUTSIDE."),
    ("canyons_village_kimball_junction", "Canyons Village and Kimball Junction are unincorporated Summit County "
                                         "whose mailing name is Park City (84098); they publish as Park City and "
                                         "report under their own overlay."),
    ("resort_campus", "A resort campus (one operator, many buildings, one booking engine) is never one identity: each "
                      "row is the exact hotel / lodge premises the public operator sells as a hotel, and a pet policy "
                      "binds only to that premises (CONDO_HOTEL_RULE)."),
])

#: The market ruling.
SALT_LAKE_CITY_RULING = OrderedDict([
    ("classification", "The Salt Lake City / Park City market is admitted as two clusters joined by I-80 -- Downtown "
                       "and Temple Square, the University and Foothill, Sugar House, the SLC airport and west side, "
                       "Park City (Old Town, Main Street, Deer Valley) and Canyons Village / Kimball Junction CORE; "
                       "South Salt Lake / Millcreek, Murray, Midvale, Sandy, South Jordan, West Jordan, Draper, West "
                       "Valley City and Cottonwood Heights / Holladay STRONG CORRIDOR; Taylorsville / Kearns, "
                       "Riverton / Herriman / Bluffdale, Lehi and North Salt Lake / Bountiful FRINGE. Provo / Orem, "
                       "Ogden and Davis County beyond Bountiful, the Heber Valley, the Cottonwood Canyon resorts, "
                       "Tooele, Logan, Moab, St. George, Springdale / Zion and Bryce Canyon are OUTSIDE."),
    ("a_marketing_phrase_admits_nothing", "'Salt Lake City', 'SLC Airport', 'Downtown', 'Temple Square', 'Park City', "
                                          "'Deer Valley', 'Canyons' and 'Wasatch' are marketing. The property's own "
                                          "postal code decides membership and its municipality."),
    ("actual_location", "Decided by the property's own postal code on its own page; the county and the municipality "
                        "by that code."),
    ("drive_market_relationship", "Downtown, the airport, the University, Sugar House, the I-15 / I-215 suburbs and "
                                  "Park City are where Salt Lake City and Park City travellers sleep; Provo, Ogden, "
                                  "the Heber Valley, the canyon resorts and the national-park gateways are trips of "
                                  "their own."),
    ("traveller_intent", "Leisure (Temple Square, the Wasatch ski resorts reached from the valley and Park City, the "
                         "Sundance Film Festival), convention (the Salt Palace, the Mountain America Expo Center), "
                         "arena and stadium (the Delta Center, America First Field, Rice-Eccles Stadium), medical "
                         "(University of Utah Health, Intermountain Medical Center, Primary Children's), university "
                         "(the University of Utah, Westminster) and SLC airport demand is this market's intent."),
    ("metro_continuity", "Continuous development runs along I-15 from North Salt Lake and Bountiful to Draper and "
                         "across the Point of the Mountain to Lehi, and along I-80 to Park City; this registry stops "
                         "there."),
    ("corridor_support", "Every admitted edge code is in a named corridor so its count is visible and a founder can "
                         "move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE provo-orem-ut, ogden-ut, heber-valley-ut, cottonwood-canyons-ut, logan-ut, "
                      "bear-lake-ut, moab-ut, st-george-ut, zion-springdale-ut and bryce-canyon-ut."),
])

STRUCTURE_TEST = OrderedDict([
    ("A. Is Salt Lake City / Park City one market?",
     "ONE market, salt-lake-city-ut, covering the Salt Lake Valley the order evaluates and Park City / the Snyderville "
     "Basin -- one commercial airport (SLC), one I-15 / I-215 / I-80 road system, two traveller clusters."),
    ("B. Municipalities are NOT flattened",
     "Every corridor names its municipality, every admitted code carries its county and real municipalities, and "
     "every row keeps its own. Park City, Sandy, Murray, Midvale, Draper, West Valley City and the rest are never "
     "written as Salt Lake City."),
    ("C. SLC airport", "The airport and its hotel row are SALT LAKE CITY (84116 / 84122); 'Airport' hotels elsewhere "
                       "are placed by their own code (SLC_AIRPORT_EVALUATION)."),
    ("D. Park City", "Its own identity (PARK_CITY_EVALUATION)."),
    ("E. Temple Square / Central City / Granary / Deer Valley / Canyons Village / Kimball Junction / Main Street",
     "Overlays of their corridor, never split codes."),
    ("F. Provo / Orem", "OUTSIDE -- FUTURE_STANDALONE provo-orem-ut."),
    ("G. Ogden", "OUTSIDE -- FUTURE_STANDALONE ogden-ut."),
    ("H. Heber City / Midway", "OUTSIDE -- FUTURE_STANDALONE heber-valley-ut."),
    ("I. Snowbird / Alta / Solitude / Brighton", "OUTSIDE -- FUTURE_STANDALONE cottonwood-canyons-ut."),
    ("J. Moab / St. George / Zion / Bryce / Logan / Bear Lake", "OUTSIDE -- not absorbed."),
])

CONDO_HOTEL_RULE = OrderedDict([
    ("public_hotel_operator",
     "Required and proved on the operator's own page: an establishment sold nightly to the public under one name, "
     "with an official property page and an on-site hotel / lodge operation (front desk)."),
    ("exact_premises",
     "Required: the row's own street address (house number + canonical street + ZIP). A unit designator ('Ste', "
     "'Unit', '#', 'Apt', 'PH') in a registry address means the record is a UNIT INSIDE a building or campus, which "
     "is never a hotel identity."),
    ("ski_lodge_rule",
     "A ski lodge or mountain inn is admitted however small when its own site proves a PUBLIC LODGING OPERATION "
     "(rooms sold nightly to the public under one establishment name, with its own booking and an on-site "
     "operation), an OFFICIAL PROPERTY IDENTITY and an EXACT PREMISES. A condominium complex whose units are rented "
     "by a property-management company, a private chalet, a 'ski-in ski-out home' or a nightly-rental licence is "
     "never a lodge. Ambiguous qualification is HELD, never admitted to publication."),
    ("hotel_vs_residence_boundary",
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. This market's "
     "specific exposures: Park City's branded residences beside resort hotels (Montage, St. Regis, Waldorf Astoria, "
     "Pendry), the Deer Valley and Canyons Village condominium lodges sold by property managers (Deer Valley Resort "
     "Lodging, Park City Lodging, All Seasons Resort Lodging, Wyndham Vacation Rentals, Vacasa, Evolve), private ski "
     "chalets, downtown Salt Lake City's serviced-apartment operators (Sonder, Kasa, Mint House, Placemakr, Blueground, "
     "Lark, Landing, Zeus, AKA) and corporate-housing portfolios, University of Utah student housing and the Airbnb / "
     "Vrbo inventory."),
    ("timeshare_rule",
     "A vacation-ownership club or timeshare resort (Club Wyndham, WorldMark, Marriott Vacation Club -- MountainSide, "
     "Summit Watch --, Hilton Grand Vacations -- Sunrise Lodge --, Hyatt Vacation Club, Westgate Park City Resort & "
     "Spa, Holiday Inn Club Vacations, Bluegreen, Diamond / Hilton Vacation Club) is TIMESHARE and is never admitted to "
     "hotel accounting, even when its brand lists it beside its hotels, even when it sells a nightly rate, and even "
     "when a pet-policy page exists."),
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
     "shelters and on-base / on-post military lodging are never public hotels and are never admitted."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("84101", ["Downtown (west of Main)", "Temple Square (south side)", "Granary District", "Gateway / Delta Center"]),
    ("84111", ["Downtown (east of Main)", "Central City"]),
    ("84060", ["Old Town / Historic Main Street", "Deer Valley (Snow Park, Silver Lake)", "Prospector",
               "Park Meadows"]),
    ("84098", ["Canyons Village", "Kimball Junction / Newpark", "Jeremy Ranch", "Pinebrook", "Summit Park"]),
    ("84092", ["Sandy (east)", "Snowbird / Alta (refused by municipality)"]),
    ("84121", ["Cottonwood Heights", "Holladay (south)", "Solitude / Brighton (refused by municipality)"]),
    ("84106", ["Sugar House", "South Salt Lake (east)", "Millcreek (north)"]),
    ("84115", ["South Salt Lake", "Salt Lake City (Ballpark)", "Millcreek (west)"]),
    ("84117", ["Holladay", "Murray (east)", "Cottonwood Heights (north)", "Millcreek (south)"]),
    ("84119", ["West Valley City (east)", "Taylorsville (north)"]),
    ("84010", ["Bountiful", "West Bountiful", "Woods Cross"]),
])

FUTURE_MARKETS = OrderedDict([
    ("provo-orem-ut", "Provo / Orem / American Fork -- Utah County, 40-45 miles south on I-15."),
    ("ogden-ut", "Ogden, Layton and Davis County beyond Bountiful -- 35 miles north on I-15."),
    ("heber-valley-ut", "Heber City, Midway and the Jordanelle / Deer Valley East Village premises -- Wasatch County."),
    ("cottonwood-canyons-ut", "Snowbird, Alta, Solitude and Brighton -- the Cottonwood Canyon ski resorts."),
    ("logan-ut", "Logan and the Cache Valley -- 80 miles north."),
    ("bear-lake-ut", "Bear Lake / Garden City -- Rich County."),
    ("moab-ut", "Moab -- Arches and Canyonlands, 230 miles south-east."),
    ("st-george-ut", "St. George and Cedar City -- 300 miles south-west."),
    ("zion-springdale-ut", "Springdale -- Zion National Park's gateway."),
    ("bryce-canyon-ut", "Bryce Canyon City -- Bryce Canyon National Park's gateway."),
])

#: Markets that are ALREADY LIVE. No live market shares Utah; exposures are shared NAMES only: Sandy (Oregon's
#: Portland region), Midvale, Murray (Kentucky), Draper, Holladay, Riverton (Wyoming), Bountiful and Park City (Kansas,
#: Kentucky) appear elsewhere as towns or streets, and "Park City" is a bare name trap in any market.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("new-orleans-la", "New Orleans, live as production market #44 (deploy 6ac5ba3bcda3a604f7e467e0) -- the CURRENT "
                       "LIVE market at this order's authoring time. No shared state, no shared postal code."),
    ("denver-co", "Denver, live -- the nearest live mountain-west market; no shared state or code."),
    ("phoenix-az", "Phoenix, live -- a south-west neighbour with no shared state or code."),
    ("portland-or", "Portland, live -- its region names a Sandy (Oregon); identity is decided by premises and state, "
                    "never a town name."),
])

#: A shared postal code whose OTHER municipality is refused: the Cottonwood Canyon resorts on valley codes.
MUNICIPALITY_REFUSALS = [
    ("84092", "snowbird", "Snowbird (Little Cottonwood Canyon) shares 84092 with east Sandy; a canyon ski resort -- "
                          "FUTURE_STANDALONE cottonwood-canyons-ut"),
    ("84092", "alta", "Alta (Little Cottonwood Canyon) shares 84092 with east Sandy; a canyon ski resort -- "
                      "FUTURE_STANDALONE cottonwood-canyons-ut"),
    ("84121", "solitude", "Solitude (Big Cottonwood Canyon) shares 84121 with Cottonwood Heights; a canyon ski resort "
                          "-- FUTURE_STANDALONE cottonwood-canyons-ut"),
    ("84121", "brighton", "Brighton (Big Cottonwood Canyon) shares 84121 with Cottonwood Heights; a canyon ski resort "
                          "-- FUTURE_STANDALONE cottonwood-canyons-ut"),
]
#: Canyon wording on a row's own name or street: a valley-labelled canyon resort is refused like its municipality.
CANYON_RESORT_RX = re.compile(r"\b(snowbird|alta lodge|alta peruvian|rustler lodge|goldminer'?s daughter|"
                              r"alta'?s|snowpine|cliff lodge|iron blosam|inn at snowbird|lodge at snowbird|"
                              r"solitude|silver fork lodge|brighton (resort|lodge|chalets?)|"
                              r"(little|big) cottonwood canyon (rd|road|hwy)|"
                              r"(sr|state route|hwy|highway|ut)[ -]?(190|210)\b)", re.I)

MUNICIPALITY_SPELLINGS = {
    "salt lake city,": "salt lake city", "salt lake": "salt lake city", "slc": "salt lake city",
    "salt lake city ut": "salt lake city", "salt lake city, ut": "salt lake city", "s salt lake": "south salt lake",
    "so salt lake": "south salt lake", "south salt lake city": "south salt lake", "park city,": "park city",
    "park city ut": "park city", "park city, ut": "park city", "deer valley": "park city",
    "west valley": "west valley city", "w valley city": "west valley city", "west valley city,": "west valley city",
    "w jordan": "west jordan", "s jordan": "south jordan", "n salt lake": "north salt lake",
    "cottonwood hts": "cottonwood heights", "cottonwood heights,": "cottonwood heights", "murray,": "murray",
    "midvale,": "midvale", "sandy,": "sandy", "draper,": "draper", "holladay,": "holladay",
    "millcreek,": "millcreek", "lehi,": "lehi", "bountiful,": "bountiful", "w bountiful": "west bountiful",
    "taylorsville,": "taylorsville", "riverton,": "riverton", "herriman,": "herriman", "bluffdale,": "bluffdale",
    "woods cross,": "woods cross",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("84101", "Downtown west of Main / Temple Square's south side / Granary / Gateway / Delta Center."),
    ("84150", "The Church of Jesus Christ of Latter-day Saints' headquarters code (Temple Square)."),
    ("84111", "Downtown east of Main / Central City."),
    ("84116", "The SLC airport hotel row on North Temple / Wright Brothers Drive -- SALT LAKE CITY."),
    ("84122", "Salt Lake City International Airport itself."),
    ("84060", "Park City -- Old Town, Main Street, Deer Valley -- PARK CITY, never Salt Lake City."),
    ("84098", "Snyderville Basin -- Canyons Village, Kimball Junction -- mailing name Park City."),
    ("84092", "East Sandy -- and Snowbird / Alta, refused by municipality."),
    ("84121", "Cottonwood Heights -- and Solitude / Brighton, refused by municipality."),
    ("84032", "Heber City / Jordanelle / Deer Valley East Village -- refused (heber-valley-ut)."),
    ("84043", "Lehi -- FRINGE."),
    ("84604", "Provo -- refused (provo-orem-ut)."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Salt Lake City" % name),
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
        raise SystemExit("admitted postal codes outside the Salt Lake City prefixes: %s" % stray)
    for rz, _m, _w in MUNICIPALITY_REFUSALS:
        if rz not in seen_zip:
            raise SystemExit("municipality refusal on a code no corridor claims: %s" % rz)
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
        ("market_name", "Salt Lake City / Park City / Wasatch Front, Utah -- downtown and Temple Square, the "
                        "University, Sugar House, the SLC airport, the Salt Lake Valley suburbs from Bountiful to "
                        "Lehi, and Park City, Deer Valley, Canyons Village and Kimball Junction lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("country", "US"),
        ("market_center", {"lat": 40.76, "lng": -111.89}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past Provo, north past Ogden, west to "
             "Tooele and Grantsville and east across the Wasatch Back to Heber City, Kamas and Coalville, so that "
             + WORK_ORDER + " classifies those properties on evidence instead of being blind to them. Admission is "
             "decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Salt Lake City / Park City is ONE market of two clusters across four counties, every row "
         "keeping its own municipality: six CORE corridors (Downtown / Temple Square, University / Foothill, Sugar "
         "House, SLC Airport / North Temple, Park City / Deer Valley / Main Street, Canyons Village / Kimball "
         "Junction), nine STRONG CORRIDORS (South Salt Lake / Millcreek, Murray, Midvale, Sandy, South Jordan, West "
         "Jordan, Draper, West Valley City, Cottonwood Heights / Holladay) and four FRINGE corridors (Taylorsville / "
         "Kearns, Riverton / Herriman / Bluffdale, Lehi, North Salt Lake / Bountiful). PROVO / OREM, OGDEN, the HEBER "
         "VALLEY, the COTTONWOOD CANYON resorts, LOGAN, MOAB, ST. GEORGE, ZION and BRYCE are refused as future "
         "standalone markets. Patient, charitable and on-base lodging is never admitted."),
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
        ("market_name", "Salt Lake City & Park City, Utah"),
        ("market_slug", MARKET_ID),
        ("state_name", "Utah"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", list(STATE_CODES)),
        ("primary_city", "Salt Lake City"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Salt Lake City & Park City, Utah | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Salt Lake City and Park City -- downtown and Temple Square, the "
         "University, Sugar House, the SLC airport, the Salt Lake Valley from Bountiful to Lehi, and Park City, Deer "
         "Valley, Canyons Village and Kimball Junction -- with real pet fees and policies read from each hotel's own "
         "official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Salt Lake City & Park City"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry; the property's MUNICIPALITY is the one its own postal code and "
         "page put it in. A Salt Lake City and Park City travel market -- downtown and Temple Square, convention, "
         "university, medical, Sugar House, SLC airport, the Salt Lake Valley suburbs from Bountiful to Lehi, and "
         "Park City, Deer Valley, Canyons Village and Kimball Junction. Not 'Utah': Provo / Orem, Ogden, the Heber "
         "Valley, the Cottonwood Canyon resorts, Logan, Moab, St. George, Springdale / Zion and Bryce Canyon are "
         "future standalone markets. Nothing else admits a property: not a brand's 'Salt Lake City' or 'Park City' "
         "marketing name, not a map pin, not a vacation-rental listing, not a competitor directory's city label. "
         "Patient, charitable and on-base lodging is never admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Park City rows are "
         "PARK CITY and never Salt Lake City; Sandy, Murray, Midvale, Draper, West Valley City and every other "
         "municipality keep their own. Shared codes are covered whole: 84101 by downtown, Temple Square's south side "
         "and the Granary; 84060 by Old Town, Main Street and Deer Valley; 84098 by Canyons Village and Kimball "
         "Junction; 84092 and 84121 by their valley municipalities, the canyon resorts refused by municipality. "
         "Temple Square, Central City, the Granary, Historic Main Street, Deer Valley, Canyons Village and Kimball "
         "Junction are overlays."),
        ("_census_membership_note",
         "Individual condominium units, private residences, private ski chalets, vacation homes and nightly-rental "
         "condos sold by property managers, corporate-housing portfolios, serviced-apartment operators, Airbnb / Vrbo "
         "inventory, ordinary apartments, student housing, timeshare and vacation-club inventory, residential-only "
         "towers, branded residences beside resort hotels, member-only club lodging and on-base military / "
         "government lodging are never admitted. A ski lodge, mountain inn or bed-and-breakfast is admitted when its "
         "own site proves a public lodging operation at an exact premises. A mixed hotel / condo / residence resort "
         "is admitted only as the exact hotel premises its public operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    counties = ("Salt Lake", "Summit", "Utah", "Davis")
    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 + 6 + 7 + 8 + 9 -- Salt Lake City / Park City travel-market geography, the Salt Lake "
                  "City vs Park City identity rule, the ski-resort / condo / campus rule, the Cottonwood Canyon "
                  "boundary, the timeshare rule, the residence / vacation-rental rule and the seasonal rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/salt-lake-city-ut.json. This "
         "order does not register, authorize or deploy anything."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page or its brand's own property card states it, "
         "joined to the corridor registry. Nothing else admits a property."),
        ("municipality_rule",
         "Every admitted postal code carries its county and its real municipalities (POSTAL_PARISH / POSTAL_COUNTY). "
         "'Salt Lake City' is published only where the code carries it; 'Park City' only for 84060 / 84068 / 84098. "
         "A stated city that is not one of its code's municipalities is a MUNICIPALITY CONFLICT and the row publishes "
         "its code's own municipality, the stated label kept as evidence."),
        ("postal_county", OrderedDict((z, OrderedDict([("county", p), ("municipalities", list(m))]))
                                      for z, (p, m) in POSTAL_PARISH.items())),
        ("classes", OrderedDict((k, "; ".join("%s (%s, %s)" % (c[1], c[7], ", ".join(c[5])) for c in CORRIDORS
                                              if c[3] == k))
                                for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("class_vocabulary",
         "The order's STRONG_CORRIDOR is registry class CORRIDOR; FUTURE_STANDALONE lives inside OUTSIDE with its "
         "future market id."),
        ("outside_class", "Everything else, refused by name with its postal codes, by MUNICIPALITY on a shared code "
                          "(the canyon resorts) and by postal PREFIX for the refused regions; the future standalone "
                          "markets named."),
        ("future_standalone_markets", FUTURE_MARKETS),
        ("existing_live_markets", EXISTING_LIVE_MARKETS),
        ("slc_airport_evaluation", SLC_AIRPORT_EVALUATION),
        ("park_city_evaluation", PARK_CITY_EVALUATION),
        ("salt_lake_city_ruling", SALT_LAKE_CITY_RULING),
        ("metro_structure_test", STRUCTURE_TEST),
        ("county_boundary_rules", COUNTY_BOUNDARY_RULES),
        ("condo_hotel_rule", CONDO_HOTEL_RULE),
        ("cottonwood_canyons_rule", OrderedDict([
            ("ruling", "Snowbird, Alta, Solitude and Brighton are ski-destination inventory and are refused BY "
                       "MUNICIPALITY on the valley codes they share (84092, 84121), and by name / canyon street "
                       "wording (CANYON_RESORT_RX) when a listing labels them with a valley city. FUTURE_STANDALONE "
                       "cottonwood-canyons-ut."),
            ("municipality_refusals", [OrderedDict([("postal_code", z), ("municipality", m), ("why", w)])
                                       for z, m, w in MUNICIPALITY_REFUSALS]),
        ])),
        ("military_lodging_rule", OrderedDict([
            ("rule", "On-base / on-post military lodging is MILITARY_RESTRICTED and never admitted. Hill AFB (84056) "
                     "sits outside the partition; Camp W.G. Williams's and other on-post names are refused wherever "
                     "they appear."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "Salt Lake City and Park City were selected as a high-value PetTripFinder market for ski and outdoor leisure, "
         "convention, university, medical and SLC airport travel. That lowers NO evidence standard: pet acceptance is "
         "never inferred from a resort town's reputation. It shapes only the CENSUS: every downtown, airport, suburban "
         "and resort lodging cluster is covered by an admitting corridor."),
        ("the_salt_lake_name_trap",
         "The chains put 'Salt Lake City' on hotels in West Valley City, Midvale, Murray, Sandy, Draper and Woods "
         "Cross, 'Airport' on hotels three cities away, and 'Park City' or 'Deer Valley' on premises in Heber City and "
         "at Jordanelle. A property's own postal code, street, phone and brand property code decide what and where it "
         "is -- and which MUNICIPALITY it is in; none of those words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Salt Lake City International Airport (SLC)", "slc-airport-west-side (84122 / 84116)."),
            ("Temple Square / City Creek", "downtown-salt-lake-city (84150 / 84101 / 84111)."),
            ("Salt Palace Convention Center / Delta Center", "downtown-salt-lake-city (84101)."),
            ("University of Utah / University Hospital / Rice-Eccles Stadium", "university-foothill (84112 / 84132 / "
                                                                               "84108)."),
            ("Intermountain Medical Center", "murray (84107)."),
            ("Mountain America Expo Center / South Towne", "sandy (84070)."),
            ("America First Field", "sandy (84070 / 84092)."),
            ("Park City Mountain / Deer Valley / Main Street / Sundance Film Festival", "park-city (84060)."),
            ("Canyons Village / Kimball Junction", "canyons-kimball-junction (84098)."),
            ("Silicon Slopes / Thanksgiving Point", "lehi (84043)."),
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
        ("first_utah_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("state_code", c["state_code"]), ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, ski-resort, convention or "
         "neighbourhood keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration "
         "order publishes it."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln), ("radius_km", r)])
                            for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)])
                                       for m, s, zs, w in OUTSIDE]),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, ski lodges and bed-and-breakfasts that prove a public lodging "
         "operation, public resorts, qualifying condo-hotels with a distinct public hotel operation, qualifying "
         "extended-stay hotels and other public lodging establishments: bookable nightly rooms or suites sold to the "
         "public under one establishment name, with an official property page and an on-site operation. It NEVER "
         "admits: individual condominium units; vacation homes, ski chalets and nightly-rental condos sold by owners "
         "or managers; private rooms and guest suites; property-management / corporate-housing / short-term-rental "
         "portfolios; serviced-apartment operators; Airbnb / Vrbo listings; ordinary apartments; student housing; "
         "timeshare and vacation-club inventory; residential-only towers; branded residences; member-only club "
         "lodging; on-base military / government lodging; and privately managed units inside condo-hotels. "
         "Campgrounds and RV parks are NON_LODGING; a hostel is admitted only when it sells private rooms to the "
         "public under its own name at an exact premises."),
        ("shared_campus_rule",
         "Never merged solely by display name, brand, owner, phone, shared address, campus, booking engine, shared "
         "amenities or shared entrance. Exact premises identity (its own street address or its own brand property "
         "code on its own page) governs. A dual-brand building is TWO hotels and is HELD for the split."),
        ("seasonal_rule",
         "A seasonally operating mountain lodge is a CURRENT business: closed-for-season is not closed. A preopening "
         "hotel ('Opening 2026', 'Coming Soon') never publishes; a permanently closed hotel never publishes; a "
         "rebrand is resolved to the operator's current name on its own page."),
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


def canyon_resort_reason(name, street=""):
    """The cottonwood-canyons-ut reason a row's own NAME or STREET carries, or "". A valley-labelled canyon resort
    (a listing that prints 'Sandy' for Snowbird) is refused like its municipality."""
    for text in (name or "", street or ""):
        m = CANYON_RESORT_RX.search(text)
        if m:
            return ("Cottonwood Canyon ski-resort premises (%r) -- FUTURE_STANDALONE cottonwood-canyons-ut"
                    % m.group(0))
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


county_for_postal = parish_for_postal


def municipality_for_postal(postal, stated_city=""):
    """The REAL municipality a premises at ``postal`` publishes: the stated city when the code carries it, else the
    code's first (principal) municipality. ``park city`` is returned only for a Park City / Snyderville Basin code and
    ``salt lake city`` only for a code that carries it. "" for a code outside the admitted partition."""
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
    PARK CITY PROFILES LABELED SALT LAKE CITY = 0: a Park City premises is never written as Salt Lake City, and a
    Sandy, Murray or West Valley City premises is never written as Salt Lake City."""
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
    s = {"UTAH": "UT", "IDAHO": "ID", "WYOMING": "WY", "NEVADA": "NV", "COLORADO": "CO", "ARIZONA": "AZ"}.get(s, s)
    z = state_for_postal(postal)
    if s and z and s != z:
        return ("the row states the state %s beside postal code %s, which is %s; one of the two facts is wrong and the "
                "row is never re-labelled" % (s, (postal or "")[:5], z))
    return ""


def future_market_for(postal, municipality=""):
    """The market id a refused postal code is preserved for (future standalone OR existing live), or ""."""
    z = (postal or "").strip()[:5]
    muni = normalise_municipality(municipality)
    for rz, rmuni, why in MUNICIPALITY_REFUSALS:
        if rz == z and rmuni == muni:
            return "cottonwood-canyons-ut"
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
        return "OUTSIDE", None, "Salt Lake City-region postal code %r is claimed by no corridor" % z
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
