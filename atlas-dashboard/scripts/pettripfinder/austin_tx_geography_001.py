"""PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4 and 5: the Austin / Central Texas market.

Built from zero on the CURRENT hardened lineage: the Phoenix-live release 0e309868 (live source e2d45272, built_from
63e410ff). Current verified live at authoring time = phoenix-az deploy 6abc8387e81507b25eb94a0a, 37 markets / 3,210
profiles / 3,549 release-index routes / 3,619 served routes, host verified (release_index live-source --verify-host).
No earlier Austin build exists, and this is the FIRST Texas market: no live market owns a single Texas postal code.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Austin / Central Texas traveller lodging market -- not the municipal City of Austin, and not "Central
Texas" -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE markets named inside
OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the fact to make a number.
The order's "STRONG CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property
card) states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted
lodging ZIP is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A
brand's marketing name never admits and never places a property: a hotel titled "Austin North" whose own address
states Round Rock 78681 is a Round Rock hotel, a hotel titled "Austin Airport" whose own address states 78744 is a
South Austin hotel, and a resort titled "Austin Hill Country" whose own address states Spicewood 78669 is refused.

WHY "AUSTIN" DECIDES NOTHING HERE (PHASE 10)
--------------------------------------------
The chains put "Austin" on hotels in Round Rock, Pflugerville, Cedar Park, Lakeway, Buda, Kyle and Bastrop, and
"Austin Hill Country" / "Lake Travis" on resorts from Lakeway to Spicewood and Marble Falls. "Austin Airport" hotels
stand in 78719 (the airport itself), 78741 / 78742 (the SH-71 / Riverside row) and 78744 / 78617. "The Domain"
hotels are 78758. Several postal codes carry two municipalities (78681 Round Rock / Austin, 78660 Pflugerville /
Austin, 78613 Cedar Park / Austin, 78746 West Lake Hills / Rollingwood / Austin, 78738 Bee Cave / Lakeway): each is
covered WHOLE by one corridor, and the row's own municipality is recorded, never used to split a code.

THE HILL COUNTRY BOUNDARY (PHASE 4)
-----------------------------------
"Austin Hill Country", "Texas Hill Country" and "Lake Travis" are marketing phrases and admit nothing. The
metro-continuous Lake Travis SOUTH shore (Lakeway, Bee Cave, Hudson Bend, Steiner Ranch: 78734 / 78738 / 78732) is
a STRONG CORRIDOR on the SH-71 / RM-620 suburban spine. Dripping Springs (78620) and the US-290 Belterra corridor
(78737) are admitted at FRINGE: Hays County, inside the Austin MSA, metro-continuous along US-290 from Oak Hill, and
the drive market is Austin's. Everything past them -- Spicewood / Briarcliff (78669), the Lake Travis NORTH shore
(Lago Vista / Jonestown, 78645), Marble Falls and the Highland Lakes, Johnson City, Wimberley, Driftwood (78619),
Fredericksburg and the Pedernales wine country -- is OUTSIDE, preserved for a FUTURE_STANDALONE texas-hill-country
market. A resort's own address decides; its "Austin" tagline never does.

TRAVELLER-MARKET LOGIC (PHASE 3)
--------------------------------
Austin is a road-trip, event (SXSW, ACL, F1 at the Circuit of the Americas, UT football), business, outdoor
(Lady Bird Lake, Barton Springs, the Greenbelt, Lake Travis), long-stay / extended-stay and airport market, with
Round Rock / North Austin corporate demand and a Hill Country gateway role. That lowers NO evidence standard: no
destination reputation ("dog-friendly Austin", the trails, a hotel's marketing) is ever policy evidence. It shapes
only the CENSUS: every event, trail, extended-stay, airport and I-35 / US-183 / SH-130 / SH-71 / US-290 road-trip
cluster is covered by an admitting corridor.

RESORT / CONDO / VACATION-OWNERSHIP SAFETY (PHASE 5)
----------------------------------------------------
Qualifying public hotels and resorts are admitted on their own pages. Individual condo units, private residences,
Airbnb / Vrbo units, ordinary apartments, corporate-housing and property-management portfolios, serviced-apartment
operators (Sonder, Kasa, Mint House, Placemakr, Blueground) and timeshare / vacation-club inventory (Club Wyndham,
WorldMark, Hilton Grand Vacations, Marriott Vacation Club, Holiday Inn Club Vacations, Bluegreen, Diamond / Hilton
Vacation Club) are never admitted; a mixed property is admitted only as the exact hotel premises its public operator
sells. Phoenix's lesson is carried as a RULE: a vacation-club resort is TIMESHARE even when its brand lists it beside
its hotels and even when a pet-policy page exists.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/austin_tx.json
  launch_packages/pettripfinder/markets/proposed/austin-tx.json
  launch_packages/pettripfinder/markets/reports/austin_tx_geography_001.json
  launch_packages/pettripfinder/markets/reports/austin_tx_corridor_registry_001.json
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

WORK_ORDER = "PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "austin-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "austin_tx.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "austin-tx.json")
REPORT_OUT = os.path.join(REPORTS, "austin_tx_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "austin_tx_corridor_registry_001.json")
AS_OF = "2026-09-30"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    # ---------------------------------------------------------------- CORE
    ("downtown-austin", "Downtown Austin", "Downtown / Congress Ave / Rainey / Warehouse District / West End", "CORE",
     "austin", ["78701", "78703"],
     "Downtown Austin's central business district (78701): Congress Avenue and the Texas State Capitol, the Austin "
     "Convention Center, the Rainey Street and Warehouse / 2nd Street districts, Sixth Street, the Moody Center's "
     "south approach, Lady Bird Lake's north shore and the Seaholm / West End -- and Clarksville, Old West Austin and "
     "Tarrytown to its west (78703). The Convention Center, Capitol and Sixth Street are OVERLAYS, never a split code."),
    ("south-congress", "South Congress & Zilker", "South Congress (SoCo) / Travis Heights / Bouldin / Zilker / Barton "
     "Springs / South Lamar", "CORE", "austin", ["78704"],
     "South Congress Avenue (SoCo) and the neighbourhoods of 78704: Travis Heights, Bouldin Creek, South Lamar, "
     "Zilker Park (Austin City Limits), Barton Springs Pool and the Barton Creek Greenbelt trailheads, and Lady Bird "
     "Lake's south shore. One postal code, covered whole: the SoCo boutique hotels and the South Lamar / Riverside "
     "chain hotels are one corridor."),
    ("east-austin", "East Austin & Mueller", "East Austin / East 6th / East Cesar Chavez / Mueller / Windsor Park",
     "CORE", "austin", ["78702", "78721", "78722", "78723", "78724", "78725"],
     "East Austin (78702) -- East Sixth, East Cesar Chavez, Holly and the East 11th / 12th corridors -- with "
     "Cherrywood (78722), MLK / Springdale (78721), Mueller and Windsor Park (78723) and the far-east Loyola / "
     "Hornsby Bend edge toward SH-130 (78724 / 78725). A boutique-hotel, dining and music district."),
    ("ut-central", "UT & Central Austin", "University of Texas / West Campus / Hyde Park / Rosedale / Crestview",
     "CORE", "austin", ["78705", "78712", "78751", "78756", "78757"],
     "The University of Texas at Austin (78712) with West Campus and North University (78705) -- the AT&T Hotel & "
     "Conference Center, Darrell K Royal stadium, the Dell Medical district -- and central Austin north of campus: "
     "Hyde Park and North Loop (78751), Rosedale and Brentwood (78756) and Crestview / Allandale (78757)."),
    ("domain-north-austin", "The Domain & North Austin", "The Domain / North Burnet / Gateway / I-35 North / "
     "Wells Branch / Parmer", "CORE", "austin", ["78752", "78753", "78754", "78758", "78727", "78728"],
     "North Austin's hotel spine: The Domain and North Burnet / Gateway (78758) -- Austin's 'second downtown' and the "
     "Q2 Stadium -- the I-35 North hotel rows at US-290 / St Johns / Rundberg / Braker / Parmer (78752 / 78753), "
     "Scofield and the Parmer / MoPac tech campuses (78727), Wells Branch on I-35 (78728) and Harris Branch / Dessau "
     "(78754). Corporate, extended-stay and drive-market demand."),
    ("arboretum-northwest", "Arboretum & Northwest Austin", "Arboretum / Great Hills / Northwest Hills / Jollyville / "
     "Anderson Mill / Four Points / Avery Ranch", "CORE", "austin",
     ["78759", "78731", "78729", "78750", "78726", "78730", "78717"],
     "The Arboretum / Great Hills / Balcones district on US-183 and Capital of Texas Highway (78759), Northwest Hills "
     "(78731), the US-183 Jollyville / Anderson Mill hotel rows (78729 / 78750), Four Points and River Place on RM-620 "
     "and Loop 360 (78726 / 78730) and Avery Ranch / Brushy Creek on Austin's north-west edge (78717)."),
    ("south-austin", "South Austin", "South Austin / I-35 South / Ben White / Sunset Valley / Southwest Parkway / "
     "Oak Hill / Circle C / Slaughter", "CORE", "austin",
     ["78745", "78744", "78748", "78749", "78735", "78736", "78739", "78747", "78652"],
     "South Austin below Ben White Boulevard: the I-35 South / Stassney / William Cannon hotel rows (78744 / 78745), "
     "the City of Sunset Valley and the South MoPac / Brodie side (78745 / 78749), Southwest Parkway and Barton "
     "Creek (78735), Oak Hill on US-290 / SH-71 west (78736), Circle C and the Lady Bird Johnson Wildflower Center "
     "(78739), Slaughter / Shady Hollow (78748), Onion Creek / far south-east (78747) and Manchaca (78652). The "
     "Sunset Valley municipality sits inside 78745 and is covered whole."),
    ("aus-airport", "Austin-Bergstrom Airport (AUS)", "AUS / Presidential Blvd / SH-71 / East Riverside / Montopolis / "
     "Del Valle / Circuit of the Americas", "CORE", "austin", ["78719", "78741", "78742", "78617"],
     "Austin-Bergstrom International Airport's own lodging system: the airport campus hotels (78719), the SH-71 / "
     "East Ben White / East Riverside hotel row between I-35 and the airport (78741), Montopolis at the US-183 / "
     "SH-71 interchange (78742) and Del Valle east and south of the runways -- including the Circuit of the Americas "
     "(78617). AUS owns its codes, so the AIRPORT test answers YES. A hotel marketed 'Austin Airport' whose own code "
     "is 78744 is a South Austin hotel."),
    # ---------------------------------------------------------------- STRONG CORRIDOR
    ("round-rock", "Round Rock", "Round Rock / Dell Diamond / Kalahari / La Frontera / I-35 & SH-45", "CORRIDOR",
     "round rock", ["78664", "78665", "78681", "78680", "78682", "78683"],
     "The City of Round Rock on I-35 north: the La Frontera / SH-45 / University Boulevard hotel rows (78681 / 78664), "
     "the Dell Diamond, the Kalahari resort and the Old Settlers Park sports complex (78665), downtown Round Rock "
     "(78664) and the Round Rock Premium Outlets. 78681 also carries the City of Austin's Brushy Creek edge and is "
     "covered whole. A corporate (Dell) and youth-sports market -- PRIMARY."),
    ("pflugerville", "Pflugerville", "Pflugerville / SH-130 / SH-45 / Stone Hill", "CORRIDOR", "pflugerville",
     ["78660", "78691"],
     "The City of Pflugerville (78660) on SH-130, SH-45 and FM-685 between North Austin and Round Rock -- the Stone "
     "Hill Town Center and the SH-45 / I-35 hotel rows that Austin and Round Rock hotels share. 78660 also carries "
     "parts of Austin and Round Rock and is covered whole. PRIMARY."),
    ("cedar-park", "Cedar Park", "Cedar Park / US-183 / 183A / H-E-B Center / Lakeline", "CORRIDOR", "cedar park",
     ["78613", "78630"],
     "The City of Cedar Park (78613) on US-183 and the 183A toll road: the H-E-B Center, Lakeline and the 1890 Ranch / "
     "Cedar Park Town Center hotel cluster. 78613 also carries parts of Austin and Leander and is covered whole. "
     "PRIMARY."),
    ("georgetown", "Georgetown", "Georgetown / Downtown Square / Southwestern University / Sun City / I-35 north",
     "CORRIDOR", "georgetown", ["78626", "78627", "78628", "78633"],
     "The City of Georgetown on I-35 north of Round Rock: the historic courthouse square and Southwestern University "
     "(78626), the I-35 / Williams Drive / University Boulevard hotel rows (78626 / 78628), Lake Georgetown and the "
     "San Gabriel River trail, and Sun City Texas (78633). PRIMARY."),
    ("lakeway-bee-cave", "Lakeway, Bee Cave & Lake Travis", "Lakeway / Bee Cave / Hudson Bend / Steiner Ranch / Lake "
     "Travis south shore", "CORRIDOR", "lakeway", ["78734", "78738", "78732"],
     "The metro-continuous Lake Travis SOUTH shore on the SH-71 / RM-620 suburban spine: the City of Lakeway and "
     "Hudson Bend (78734), the City of Bee Cave and the Hill Country Galleria (78738) and Steiner Ranch / the Lake "
     "Austin shore (78732). STRONG. The Lake Travis NORTH shore (Lago Vista / Jonestown, 78645) and Spicewood / "
     "Briarcliff (78669) are Hill Country destination inventory and are refused (FUTURE_STANDALONE "
     "texas-hill-country)."),
    ("westlake-west-lake-hills", "West Lake Hills & Westlake", "West Lake Hills / Rollingwood / Westlake / Bee Caves "
     "Road / Loop 360", "CORRIDOR", "west lake hills", ["78746", "78733"],
     "The City of West Lake Hills and Rollingwood (78746) across Lady Bird Lake from downtown, and the Westlake / "
     "Davenport Ranch / Bee Caves Road side on Loop 360 (78733). Contiguous with downtown and South Austin. STRONG."),
    ("buda", "Buda", "Buda / I-35 south / Cabela's", "CORRIDOR", "buda", ["78610"],
     "The City of Buda (78610) on I-35 south of Austin: the Cabela's / Main Street / FM-1626 hotel cluster. "
     "Metro-continuous with South Austin along I-35. STRONG."),
    ("kyle", "Kyle", "Kyle / I-35 south / Plum Creek", "CORRIDOR", "kyle", ["78640"],
     "The City of Kyle (78640) on I-35 between Buda and San Marcos: the Kyle Parkway / Center Street hotel cluster. "
     "Metro-continuous with Buda along I-35; SAN MARCOS (78666), its southern neighbour, is refused. STRONG."),
    # ---------------------------------------------------------------- FRINGE
    ("leander", "Leander", "Leander / 183A / US-183 north", "FRINGE", "leander", ["78641", "78646"],
     "The City of Leander (78641) at the north end of the 183A toll road and MetroRail's Red Line terminus, "
     "contiguous with Cedar Park. Admitted at FRINGE so its small hotel inventory is ACCOUNTED FOR. 78641 also "
     "carries parts of Cedar Park and the Volente lakeshore and is covered whole."),
    ("hutto", "Hutto", "Hutto / US-79 / SH-130", "FRINGE", "hutto", ["78634"],
     "The City of Hutto (78634) on US-79 and SH-130, contiguous with Round Rock and Pflugerville. Admitted at FRINGE. "
     "Taylor (76574) beyond it is refused."),
    ("manor", "Manor", "Manor / US-290 east / SH-130", "FRINGE", "manor", ["78653"],
     "The City of Manor (78653) on US-290 east at SH-130, contiguous with east Austin. Admitted at FRINGE. Elgin "
     "(78621) beyond it is refused."),
    ("dripping-springs", "Dripping Springs & US-290 West", "Dripping Springs / Belterra / US-290 west", "FRINGE",
     "dripping springs", ["78620", "78737"],
     "The City of Dripping Springs (78620) and the US-290 Belterra corridor (78737) west of Oak Hill -- the "
     "'Gateway to the Hill Country', inside the Austin MSA and metro-continuous along US-290. Admitted at FRINGE with "
     "its reason recorded. Driftwood (78619), Wimberley, Johnson City and Fredericksburg beyond it are Hill Country "
     "destination inventory and are refused (FUTURE_STANDALONE texas-hill-country)."),
]

OUTSIDE = [
    ("San Antonio metro -- San Antonio, Alamo Heights, Live Oak, Universal City, Schertz, Selma, Converse", "TX",
     [],
     "BEXAR / GUADALUPE / COMAL COUNTY; FUTURE_STANDALONE san-antonio-tx. Refused by name and by postal PREFIX (780 / "
     "782). 80 miles south-west on I-35 with its own airport (SAT), the River Walk, the Alamo and its own convention "
     "market."),
    ("New Braunfels / Seguin / Canyon Lake / Gruene", "TX",
     ["78130", "78131", "78132", "78133", "78135", "78155", "78156", "78070"],
     "COMAL / GUADALUPE COUNTY; FUTURE_STANDALONE san-marcos-new-braunfels-tx. The Schlitterbahn / Gruene / Guadalupe "
     "and Comal river-tubing destination 45 miles south-west on I-35. Refused by name and postal code (781 prefix)."),
    ("San Marcos / Martindale / Maxwell", "TX", ["78666", "78667", "78655", "78656"],
     "HAYS / CALDWELL COUNTY; FUTURE_STANDALONE san-marcos-new-braunfels-tx. Texas State University, the San Marcos "
     "River and the Premium Outlets -- its own university and outlet travel market 30 miles south on I-35. The order "
     "keeps it OUTSIDE unless traveller-market evidence strongly supports inclusion; none does: San Marcos has its "
     "own bureau, its own university demand and sits past Kyle's contiguous edge."),
    ("Texas Hill Country destination inventory -- Fredericksburg, Johnson City, Stonewall, Wimberley, Driftwood, "
     "Blanco, Spicewood, Briarcliff, Marble Falls, Horseshoe Bay, Kingsland, Burnet, Llano, Round Mountain, Lago "
     "Vista, Jonestown, Boerne, Kerrville, Comfort", "TX",
     ["78624", "78631", "78671", "78636", "78676", "78619", "78623", "78606", "78669", "78654", "78657", "78639",
      "78611", "78643", "78663", "78645", "78605", "78672", "78006", "78028", "78013", "78004"],
     "BLANCO / GILLESPIE / HAYS (west) / BURNET / LLANO / TRAVIS (west) / KENDALL / KERR COUNTY; FUTURE_STANDALONE "
     "texas-hill-country. The wine-country, river, lake and ranch-resort destinations a traveller drives TO, not "
     "through: Fredericksburg (78624) and the Pedernales wine road, Wimberley, Johnson City, Driftwood's venues, "
     "Spicewood / Briarcliff and the Lake Travis NORTH shore (78669 / 78645), Marble Falls and the Highland Lakes. "
     "A property marketed 'Austin Hill Country' or 'Lake Travis' at one of these codes is refused by its own address."),
    ("Bastrop / Cedar Creek / Smithville / Lost Pines", "TX", ["78602", "78612", "78957", "78659", "78650"],
     "BASTROP COUNTY; refused by name and postal code after CAREFUL evaluation. Bastrop is its own county seat and "
     "destination 30 miles east on SH-71 with its own bureau (Visit Bastrop); the Lost Pines resort (Cedar Creek "
     "78612) is a destination resort marketed with 'Austin'. The SH-71 corridor between Del Valle and Bastrop is "
     "rural, so the metro-continuity test fails. Recorded, never silently absorbed."),
    ("Elgin / McDade / Paige", "TX", ["78621", "78650", "78953"],
     "BASTROP COUNTY; refused after CAREFUL evaluation: Elgin is a separate town 25 miles east on US-290 past Manor, "
     "with a rural gap. Its few lodging rows are counted, never admitted."),
    ("Liberty Hill / Bertram / Florence / Jarrell / Weir / Walburg", "TX", ["78642", "76527", "76537", "78674",
                                                                           "78673"],
     "WILLIAMSON COUNTY (north / west); refused after CAREFUL evaluation. Liberty Hill sits 12 miles past Leander on "
     "SH-29 toward Burnet with no contiguous hotel corridor; Jarrell and Florence are the rural I-35 / SH-195 north "
     "edge. County inclusion is not traveller-market inclusion."),
    ("Taylor / Coupland / Granger / Thrall", "TX", ["76574", "78615", "76530", "76578"],
     "WILLIAMSON COUNTY (east); refused by name. Taylor is a separate town on US-79 past Hutto."),
    ("Lockhart / Luling / Dale / Uhland", "TX", ["78644", "78648", "78616"],
     "CALDWELL COUNTY; refused by name. Lockhart's barbecue-town day trips are Austin excursions, not Austin lodging."),
    ("Killeen / Temple / Belton / Harker Heights / Fort Cavazos / Salado", "TX", [],
     "BELL COUNTY; FUTURE_STANDALONE killeen-temple-tx. Refused by postal PREFIX (765). 60-70 miles north on I-35 "
     "with its own airport (GRK), Fort Cavazos and Baylor Scott & White."),
    ("Waco / Hewitt / Woodway / Bellmead", "TX", [],
     "McLENNAN COUNTY; FUTURE_STANDALONE waco-tx. Refused by postal PREFIX (766 / 767). 100 miles north on I-35 with "
     "its own airport (ACT), Baylor University and Magnolia Market."),
    ("Bryan / College Station", "TX", [],
     "BRAZOS COUNTY; FUTURE_STANDALONE college-station-tx. Refused by postal PREFIX (778). Texas A&M University's own "
     "market 100 miles east."),
    ("La Grange / Giddings / Columbus / Brenham -- the SH-71 / US-290 east corridor", "TX", [],
     "FAYETTE / LEE / WASHINGTON COUNTY; refused by postal PREFIX (789 / 778)."),
    ("Other Texas and out of state", "--", [],
     "Every other Texas postal prefix (750-799 outside this market's codes) and every non-Texas code is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("780", "San Antonio region (Bexar / Atascosa / Wilson)", "san-antonio-tx"),
    ("782", "San Antonio", "san-antonio-tx"),
    ("781", "New Braunfels / Seguin / Comal / Guadalupe", "san-marcos-new-braunfels-tx"),
    ("765", "Killeen / Temple / Belton (Bell County)", "killeen-temple-tx"),
    ("766", "Waco region (McLennan County)", "waco-tx"),
    ("767", "Waco", "waco-tx"),
    ("778", "Bryan / College Station / Brenham", "college-station-tx"),
    ("789", "La Grange / Giddings / Columbus (Fayette / Lee / Colorado County)", ""),
    ("788", "Uvalde / Del Rio / south-west Texas", ""),
    ("779", "Victoria / the Coastal Bend", ""),
    ("783", "Corpus Christi", ""), ("784", "Corpus Christi", ""), ("785", "the Rio Grande Valley", ""),
    ("750", "Dallas region", ""), ("751", "Dallas region", ""), ("752", "Dallas", ""), ("753", "Dallas", ""),
    ("760", "Fort Worth region", ""), ("761", "Fort Worth", ""), ("762", "Denton region", ""),
    ("763", "Wichita Falls", ""), ("764", "Stephenville / Brownwood", ""), ("768", "Abilene / Brownwood", ""),
    ("769", "San Angelo", ""), ("770", "Houston", ""), ("772", "Houston", ""), ("773", "Houston region", ""),
    ("774", "Houston region", ""), ("775", "Houston region", ""), ("776", "Beaumont", ""), ("777", "Beaumont", ""),
    ("790", "Amarillo", ""), ("791", "Amarillo", ""), ("793", "Lubbock", ""), ("794", "Lubbock", ""),
    ("795", "Abilene", ""), ("796", "Abilene", ""), ("797", "Midland / Odessa", ""), ("798", "El Paso", ""),
    ("799", "El Paso", ""),
]

#: Austin's own postal prefixes. A code under one of these that no corridor claims is an UNCLAIMED Central Texas
#: code -- refused, and named in the boundary audit so it is visible, never silently dropped.
VALLEY_PREFIXES = ("786", "787")

ADMITTED_COUNTIES = {"travis", "williamson (round rock / cedar park / georgetown / pflugerville edge / leander / "
                               "hutto)", "hays (buda / kyle / dripping springs / us-290 belterra)"}
OBSERVED_COUNTIES = OrderedDict([
    ("bexar (san antonio)", "san-antonio-tx"),
    ("comal / guadalupe (new braunfels, seguin)", "san-marcos-new-braunfels-tx"),
    ("hays south (san marcos)", "san-marcos-new-braunfels-tx"),
    ("gillespie / blanco / burnet / llano / kendall / kerr (hill country)", "texas-hill-country"),
    ("bastrop (bastrop, cedar creek, elgin, smithville)", "(none -- refused by name after careful evaluation)"),
    ("bell (killeen, temple, belton)", "killeen-temple-tx"),
    ("mclennan (waco)", "waco-tx"),
    ("brazos (bryan, college station)", "college-station-tx"),
    ("caldwell (lockhart)", "(none -- refused by name)"),
])

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("travis", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. The City of Austin and its enclaves and suburbs -- West Lake Hills, "
                   "Rollingwood, Sunset Valley, Lakeway, Bee Cave, Manor, Pflugerville's Travis side, Del Valle and "
                   "the airport -- are admitted; Spicewood / Briarcliff and the Lake Travis NORTH shore (Lago Vista, "
                   "Jonestown) are REFUSED as Hill Country destination inventory. County inclusion is not "
                   "traveller-market inclusion."),
    ])),
    ("williamson", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. Round Rock, Cedar Park, Georgetown, Pflugerville's Williamson side, Leander and "
                   "Hutto are admitted; Liberty Hill, Jarrell, Florence, Weir, Taylor and Coupland are refused."),
    ])),
    ("hays", OrderedDict([
        ("ruling", "ADMITTED ONLY IN THE I-35 / US-290 METRO BAND. Buda and Kyle (I-35) and Dripping Springs with the "
                   "US-290 Belterra corridor are admitted; San Marcos, Wimberley and Driftwood are refused."),
    ])),
    ("bastrop / caldwell", OrderedDict([
        ("ruling", "REFUSED after careful evaluation: Bastrop, Cedar Creek (the Lost Pines resort), Elgin, Smithville "
                   "and Lockhart are separate towns across a rural gap."),
    ])),
    ("bexar / comal / guadalupe / bell / mclennan / brazos / gillespie / blanco / burnet / llano", OrderedDict([
        ("ruling", "REFUSED. San Antonio, New Braunfels, San Marcos, Killeen / Temple, Waco, College Station and the "
                   "destination Hill Country are separate traveller markets, named FUTURE_STANDALONE. Austin does not "
                   "absorb Central Texas."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / member only).
NONPUBLIC_NAMES = {
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
    "ronald mcdonald house of central texas": "charitable family lodging -- not public lodging",
    "ronald mcdonald house charities of central texas": "charitable family lodging -- not public lodging",
    "camp mabry lodging": "Texas Military Department billeting -- not public lodging",
}

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-austin", "Austin", "Downtown Austin / Capitol / Rainey", 30.2672, -97.7431, 2600, True),
    ("south-congress", "Austin", "South Congress / Zilker / South Lamar", 30.2480, -97.7580, 3500, True),
    ("east-austin", "Austin", "East Austin / Mueller", 30.2800, -97.7000, 5000, True),
    ("ut-central", "Austin", "UT / Hyde Park / Rosedale / Crestview", 30.3100, -97.7400, 4000, True),
    ("domain-north-austin", "Austin", "The Domain / North Austin / I-35 North", 30.3900, -97.7000, 7000, True),
    ("arboretum-northwest", "Austin", "Arboretum / Jollyville / Four Points", 30.4200, -97.7800, 8000, True),
    ("south-austin", "Austin", "South Austin / Sunset Valley / Oak Hill", 30.2000, -97.8000, 9000, True),
    ("aus-airport", "Austin", "AUS / SH-71 / Del Valle / COTA", 30.2000, -97.6700, 7000, True),
    ("round-rock", "Round Rock", "Round Rock", 30.5100, -97.6800, 8000, True),
    ("pflugerville", "Pflugerville", "Pflugerville", 30.4400, -97.6200, 6000, True),
    ("cedar-park", "Cedar Park", "Cedar Park / Lakeline", 30.5050, -97.8200, 6000, True),
    ("georgetown", "Georgetown", "Georgetown / Sun City", 30.6300, -97.6800, 9000, True),
    ("lakeway-bee-cave", "Lakeway", "Lakeway / Bee Cave / Lake Travis south shore", 30.3500, -97.9700, 8000, True),
    ("westlake-west-lake-hills", "West Lake Hills", "West Lake Hills / Westlake", 30.2900, -97.8000, 4000, True),
    ("buda", "Buda", "Buda", 30.0850, -97.8400, 5000, True),
    ("kyle", "Kyle", "Kyle", 29.9900, -97.8800, 6000, True),
    ("leander", "Leander", "Leander", 30.5800, -97.8500, 6000, True),
    ("hutto", "Hutto", "Hutto", 30.5400, -97.5500, 5000, True),
    ("manor", "Manor", "Manor", 30.3400, -97.5600, 5000, True),
    ("dripping-springs", "Dripping Springs", "Dripping Springs / Belterra", 30.2100, -98.0000, 9000, True),
    ("obs-san-antonio", "San Antonio", "San Antonio metro -- OBSERVATION ONLY", 29.4500, -98.5000, 25000, False),
    ("obs-new-braunfels", "New Braunfels", "New Braunfels / Seguin -- OBSERVATION ONLY", 29.7000, -98.1200, 12000,
     False),
    ("obs-san-marcos", "San Marcos", "San Marcos -- OBSERVATION ONLY", 29.8800, -97.9400, 8000, False),
    ("obs-hill-country", "Fredericksburg", "Fredericksburg / Hill Country -- OBSERVATION ONLY", 30.2750, -98.8700,
     25000, False),
    ("obs-marble-falls", "Marble Falls", "Marble Falls / Highland Lakes / Spicewood -- OBSERVATION ONLY", 30.5700,
     -98.2700, 20000, False),
    ("obs-bastrop", "Bastrop", "Bastrop / Lost Pines / Elgin -- OBSERVATION ONLY", 30.1100, -97.3200, 15000, False),
    ("obs-killeen-temple", "Killeen", "Killeen / Temple / Belton -- OBSERVATION ONLY", 31.1000, -97.5800, 25000, False),
    ("obs-waco", "Waco", "Waco -- OBSERVATION ONLY", 31.5500, -97.1500, 15000, False),
    ("obs-college-station", "College Station", "Bryan / College Station -- OBSERVATION ONLY", 30.6200, -96.3300,
     15000, False),
]

#: The Overpass / observation box. It reaches south past downtown San Antonio, north past Waco, west past
#: Fredericksburg and east past College Station, so the census counts what it refuses.
BOUNDS = {"min_lat": 29.30, "max_lat": 31.70, "min_lng": -99.10, "max_lng": -96.20}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("Texas State Capitol / Congress Ave", 30.2747, -97.7404, 0.7),
    ("Austin Convention Center / Rainey Street", 30.2630, -97.7400, 0.7),
    ("Sixth Street / Warehouse District", 30.2670, -97.7440, 0.6),
    ("Seaholm / West End", 30.2680, -97.7530, 0.6),
    ("Downtown Austin CBD", 30.2672, -97.7431, 1.2),
    ("Clarksville / Tarrytown", 30.2860, -97.7640, 1.4),
    ("South Congress (SoCo)", 30.2500, -97.7490, 0.9),
    ("Zilker / Barton Springs", 30.2640, -97.7700, 1.0),
    ("South Lamar", 30.2500, -97.7650, 1.0),
    ("East Riverside / Lady Bird Lake south", 30.2450, -97.7300, 1.2),
    ("East Sixth / East Cesar Chavez", 30.2620, -97.7250, 1.2),
    ("Mueller", 30.2980, -97.7050, 1.4),
    ("University of Texas / West Campus", 30.2860, -97.7390, 1.2),
    ("Hyde Park / North Loop", 30.3100, -97.7300, 1.2),
    ("The Domain / North Burnet", 30.4020, -97.7250, 1.4),
    ("I-35 North / US-290 / St Johns", 30.3350, -97.7000, 1.6),
    ("I-35 North / Rundberg / Braker / Parmer", 30.3800, -97.6750, 2.4),
    ("Arboretum / Great Hills", 30.3930, -97.7470, 1.4),
    ("US-183 Jollyville / Anderson Mill", 30.4400, -97.7800, 2.4),
    ("Four Points / RM-620", 30.4000, -97.8500, 2.4),
    ("South Austin I-35 / Ben White / Stassney", 30.2100, -97.7700, 2.4),
    ("Sunset Valley", 30.2270, -97.8150, 1.2),
    ("Southwest Parkway / Barton Creek", 30.2500, -97.8400, 2.4),
    ("Oak Hill (US-290 / SH-71 west)", 30.2330, -97.8750, 2.0),
    ("AUS terminal / Presidential Blvd", 30.1975, -97.6664, 2.4),
    ("SH-71 / East Ben White hotel row", 30.2200, -97.6950, 2.0),
    ("Circuit of the Americas", 30.1328, -97.6411, 3.0),
    ("Round Rock La Frontera / SH-45 / University Blvd", 30.4900, -97.6800, 2.4),
    ("Dell Diamond / Kalahari / Old Settlers Park", 30.5300, -97.6300, 2.4),
    ("Downtown Round Rock", 30.5080, -97.6780, 1.2),
    ("Pflugerville / Stone Hill", 30.4600, -97.6000, 3.0),
    ("Cedar Park / Lakeline / 1890 Ranch", 30.4900, -97.8100, 2.4),
    ("Georgetown Square / Southwestern", 30.6380, -97.6780, 1.4),
    ("Georgetown I-35", 30.6200, -97.6800, 2.4),
    ("Sun City Texas", 30.6900, -97.7400, 3.0),
    ("Lakeway / Lake Travis south shore", 30.3630, -97.9800, 3.0),
    ("Bee Cave / Hill Country Galleria", 30.3080, -97.9400, 2.0),
    ("West Lake Hills / Westlake", 30.2950, -97.8000, 2.0),
    ("Buda", 30.0850, -97.8400, 3.0),
    ("Kyle", 29.9900, -97.8800, 3.0),
    ("Leander", 30.5800, -97.8500, 3.0),
    ("Hutto", 30.5400, -97.5500, 3.0),
    ("Manor", 30.3400, -97.5600, 3.0),
    ("Dripping Springs", 30.1900, -98.0870, 4.0),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("Austin Convention Center / Rainey Street", re.compile(r"\brainey st\b|\bred river st\b(?=.*78701)|"
                                                            r"\be (2nd|3rd|4th) st\b(?=.*78701)|\btrinity st\b"
                                                            r"(?=.*78701)", re.I)),
    ("Texas State Capitol / Congress Ave", re.compile(r"\bcongress ave\b(?=.*78701)|\blavaca st\b|\bcolorado st\b"
                                                      r"(?=.*78701)|\bbrazos st\b", re.I)),
    ("South Congress (SoCo)", re.compile(r"\bs(outh)? congress ave\b(?=.*78704)", re.I)),
    ("The Domain / North Burnet", re.compile(r"\bthe domain\b|\bdomain dr\b|\bpalm way\b|\bkramer ln\b|"
                                             r"\bn burnet rd\b(?=.*78758)|\balterra pkwy\b|\bbraker ln\b(?=.*78758)",
                                             re.I)),
    ("Arboretum / Great Hills", re.compile(r"\barboretum\b|\bgreat hills\b|\bresearch b(lv)?d\b(?=.*78759)|"
                                           r"\bcapital of texas hwy\b(?=.*78759)", re.I)),
    ("AUS terminal / Presidential Blvd", re.compile(r"\bpresidential b(lv)?d\b|\bhotel dr\b(?=.*78719)|"
                                                    r"\bspirit of texas\b|\bgovernment center\b", re.I)),
    ("SH-71 / East Ben White hotel row", re.compile(r"\be ben white b(lv)?d\b(?=.*7874[12])|\bsh-?71\b(?=.*78741)|"
                                                    r"\bhwy 71\b(?=.*78741)", re.I)),
    ("Circuit of the Americas", re.compile(r"\bcircuit of the americas\b|\belroy rd\b", re.I)),
    ("Round Rock La Frontera / SH-45 / University Blvd", re.compile(r"\bla frontera\b|\bchisholm trl\b(?=.*78681)|"
                                                                     r"\bhesters crossing\b", re.I)),
    ("Dell Diamond / Kalahari / Old Settlers Park", re.compile(r"\bkalahari\b|\bold settlers\b|\bdell diamond\b",
                                                               re.I)),
    ("Georgetown Square / Southwestern", re.compile(r"\bs austin ave\b(?=.*78626)|\bmain st\b(?=.*78626)", re.I)),
    ("Lakeway / Lake Travis south shore", re.compile(r"\blakeway dr\b|\bflintrock\b|\branch rd 620\b(?=.*78734)",
                                                     re.I)),
    ("Bee Cave / Hill Country Galleria", re.compile(r"\bgalleria\b(?=.*78738)|\bhwy 71\b(?=.*78738)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-austin": "Downtown Austin",
    "south-congress": "South Congress / Zilker",
    "east-austin": "East Austin",
    "ut-central": "UT / Central Austin",
    "domain-north-austin": "North Austin",
    "arboretum-northwest": "Northwest Austin",
    "south-austin": "South Austin",
    "aus-airport": "Austin Airport",
    "round-rock": "Round Rock",
    "pflugerville": "Pflugerville",
    "cedar-park": "Cedar Park",
    "georgetown": "Georgetown",
    "lakeway-bee-cave": "Lakeway / Bee Cave",
    "westlake-west-lake-hills": "West Lake Hills",
    "buda": "Buda",
    "kyle": "Kyle",
    "leander": "Leander",
    "hutto": "Hutto",
    "manor": "Manor",
    "dripping-springs": "Dripping Springs",
}

#: The order's PRIMARY / STRONG / CAREFUL / FUTURE evaluation list, each classified explicitly.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown Austin", "ADMITTED (CORE, downtown-austin, 78701 / 78703). PRIMARY."),
    ("South Congress / SoCo", "ADMITTED (CORE, south-congress, 78704). PRIMARY."),
    ("East Austin", "ADMITTED (CORE, east-austin, 78702 / 78721-78725). PRIMARY."),
    ("University / UT / Central Austin", "ADMITTED (CORE, ut-central, 78705 / 78712 / 78751 / 78756 / 78757). "
                                         "PRIMARY."),
    ("The Domain / North Austin", "ADMITTED (CORE, domain-north-austin, 78752 / 78753 / 78754 / 78758 / 78727 / "
                                  "78728). PRIMARY."),
    ("Arboretum", "ADMITTED (CORE, arboretum-northwest, 78759). PRIMARY."),
    ("Northwest Austin", "ADMITTED (CORE, arboretum-northwest, 78731 / 78729 / 78750 / 78726 / 78730 / 78717). "
                         "PRIMARY."),
    ("South Austin", "ADMITTED (CORE, south-austin, 78745 / 78744 / 78748 / 78749 / 78735 / 78736 / 78739 / 78747 / "
                     "78652). PRIMARY."),
    ("Austin-Bergstrom International Airport / AUS", "ADMITTED (CORE, aus-airport, 78719 / 78741 / 78742 / 78617). "
                                                     "PRIMARY."),
    ("Round Rock", "ADMITTED (STRONG CORRIDOR, round-rock, 78664 / 78665 / 78681). PRIMARY."),
    ("Pflugerville", "ADMITTED (STRONG CORRIDOR, pflugerville, 78660). PRIMARY."),
    ("Cedar Park", "ADMITTED (STRONG CORRIDOR, cedar-park, 78613). PRIMARY."),
    ("Georgetown", "ADMITTED (STRONG CORRIDOR, georgetown, 78626 / 78628 / 78633). PRIMARY."),
    ("Lakeway", "ADMITTED (STRONG CORRIDOR, lakeway-bee-cave, 78734). STRONG."),
    ("Bee Cave", "ADMITTED (STRONG CORRIDOR, lakeway-bee-cave, 78738). STRONG."),
    ("West Lake Hills", "ADMITTED (STRONG CORRIDOR, westlake-west-lake-hills, 78746 / 78733). STRONG."),
    ("Sunset Valley", "ADMITTED (CORE, south-austin, 78745) -- the City of Sunset Valley sits inside 78745, covered "
                      "whole. STRONG."),
    ("Buda", "ADMITTED (STRONG CORRIDOR, buda, 78610). STRONG."),
    ("Kyle", "ADMITTED (STRONG CORRIDOR, kyle, 78640). STRONG."),
    ("Dripping Springs", "ADMITTED (FRINGE, dripping-springs, 78620 with the US-290 Belterra code 78737) -- Austin MSA, "
                         "metro-continuous on US-290; Driftwood (78619) refused. CAREFUL."),
    ("Leander", "ADMITTED (FRINGE, leander, 78641) -- contiguous with Cedar Park on 183A. CAREFUL."),
    ("Hutto", "ADMITTED (FRINGE, hutto, 78634) -- contiguous with Round Rock / Pflugerville. CAREFUL."),
    ("Manor", "ADMITTED (FRINGE, manor, 78653) -- contiguous with east Austin on US-290. CAREFUL."),
    ("Bastrop", "OUTSIDE after CAREFUL evaluation -- its own county seat and destination 30 miles east across a rural "
                "SH-71 gap; the Lost Pines resort (Cedar Creek 78612) is refused by its own address."),
    ("Elgin", "OUTSIDE after CAREFUL evaluation -- a separate town past Manor across a rural gap."),
    ("Liberty Hill", "OUTSIDE after CAREFUL evaluation -- 12 miles past Leander on SH-29 with no contiguous hotel "
                     "corridor."),
    ("San Antonio", "OUTSIDE -- FUTURE_STANDALONE san-antonio-tx."),
    ("Waco", "OUTSIDE -- FUTURE_STANDALONE waco-tx."),
    ("Fredericksburg", "OUTSIDE -- FUTURE_STANDALONE texas-hill-country."),
    ("Broader Hill Country destination inventory", "OUTSIDE -- FUTURE_STANDALONE texas-hill-country (Wimberley, Johnson "
                                                   "City, Driftwood, Spicewood, Marble Falls, Lago Vista)."),
    ("New Braunfels", "OUTSIDE -- FUTURE_STANDALONE san-marcos-new-braunfels-tx."),
    ("San Marcos", "OUTSIDE -- FUTURE_STANDALONE san-marcos-new-braunfels-tx; no traveller-market evidence strongly "
                   "supports inclusion."),
    ("Killeen / Temple", "OUTSIDE -- FUTURE_STANDALONE killeen-temple-tx."),
    ("College Station", "OUTSIDE -- FUTURE_STANDALONE college-station-tx."),
])

HILL_COUNTRY_RULING = OrderedDict([
    ("classification", "The metro-continuous Lake Travis SOUTH shore (Lakeway / Bee Cave / Hudson Bend / Steiner "
                       "Ranch, 78734 / 78738 / 78732) is a STRONG CORRIDOR; Dripping Springs and the US-290 Belterra "
                       "corridor (78620 / 78737) are FRINGE; the destination Hill Country is OUTSIDE."),
    ("a_marketing_phrase_admits_nothing", "'Austin Hill Country', 'Texas Hill Country', 'Lake Travis' and 'Austin' in "
                                          "a resort's name are marketing. The property's own postal code decides."),
    ("actual_location", "Decided by the property's own postal code on its own page."),
    ("drive_market_relationship", "Lakeway / Bee Cave / Dripping Springs are commuter suburbs whose visitors are "
                                  "Austin-bound; Fredericksburg, Wimberley, Johnson City and Marble Falls are "
                                  "destinations a traveller drives TO."),
    ("traveller_intent", "Wine country, river tubing, lake houses and ranch resorts are Hill Country intent; the "
                         "Galleria, Lakeway's marina hotels and the US-290 venues sit inside Austin's suburban band."),
    ("metro_continuity", "Continuous suburban development runs from Oak Hill to Dripping Springs on US-290 and from "
                         "West Lake Hills to Lakeway on SH-71 / RM-620; it stops at Spicewood, Driftwood and Lago "
                         "Vista."),
    ("corridor_support", "Every admitted Hill Country edge code is its own corridor (lakeway-bee-cave, "
                         "dripping-springs) so its count is visible and a founder can move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE texas-hill-country (Fredericksburg, Wimberley, Johnson City, Driftwood, "
                      "Spicewood, Marble Falls / Highland Lakes, Lago Vista, Boerne, Kerrville)."),
])

STRUCTURE_TEST = OrderedDict([
    ("A. Is Austin one market, or several?",
     "ONE market, austin-tx, covering the contiguous Austin metro from Georgetown and Hutto to Kyle and from Manor and "
     "the airport to Lakeway and Dripping Springs. One commercial airport (AUS), one I-35 / MoPac / US-183 / SH-130 / "
     "SH-45 / SH-71 / US-290 road system, one CapMetro. The rural gaps toward San Marcos, Bastrop, Taylor, Liberty "
     "Hill and the Hill Country are where that coherence stops."),
    ("B. The City of Austin is NOT the market -- and 'Austin' places nothing",
     "Round Rock, Pflugerville, Cedar Park, Georgetown, Leander, Hutto, Manor, Buda, Kyle, Lakeway, Bee Cave, West "
     "Lake Hills, Sunset Valley and Dripping Springs are admitted by their own codes; the chains' 'Austin' prefix is on "
     "hotels from Georgetown to Bastrop."),
    ("C. AUS", "The airport owns its postal code (78719) and its lodging system -- its own CORE corridor with the "
               "SH-71 / Riverside row (78741 / 78742) and Del Valle / COTA (78617)."),
    ("D. The Domain", "Inside domain-north-austin (78758) -- an overlay, not a corridor of its own."),
    ("E. Convention Center / Capitol / Sixth Street", "NO CORRIDOR of their own -- 78701, overlays of downtown."),
    ("F. Circuit of the Americas", "An overlay of aus-airport (78617)."),
    ("G. Round Rock vs Austin", "78681 and 78660 carry both municipalities and are covered whole by round-rock / "
                                "pflugerville; the row's own stated city is recorded, never used to split a code."),
    ("H. San Antonio", "OUTSIDE -- FUTURE_STANDALONE san-antonio-tx."),
    ("I. San Marcos / New Braunfels", "OUTSIDE -- FUTURE_STANDALONE san-marcos-new-braunfels-tx."),
    ("J. Hill Country", "OUTSIDE beyond Lakeway / Bee Cave / Dripping Springs -- FUTURE_STANDALONE texas-hill-country."),
    ("K. Waco / Killeen-Temple / College Station", "OUTSIDE -- FUTURE_STANDALONE waco-tx / killeen-temple-tx / "
                                                   "college-station-tx."),
    ("L. Bastrop / Elgin / Liberty Hill", "OUTSIDE after careful evaluation."),
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
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. Austin's specific "
     "exposures: the downtown hotel-and-residence towers (the Four Seasons Residences, The Austonian, the W "
     "Residences, the Fairmont / Waterline / Six Pines towers), the Lake Travis and Lakeway condo and villa rental "
     "pools, the serviced-apartment operators in downtown, East Austin and the Domain (Sonder, Kasa, Mint House, "
     "Placemakr, Blueground, Lyric, Wanderjaunt) and the Airbnb / Vrbo inventory."),
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
     "Extended-stay hotels are hotels and are admitted on their own pages; an 'apartment hotel' is admitted only "
     "as a public hotel operation at an exact premises."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("78701", ["Downtown Austin", "Convention Center", "Capitol", "Rainey Street", "Sixth Street"]),
    ("78681", ["Round Rock", "City of Austin (Brushy Creek edge)"]),
    ("78660", ["Pflugerville", "City of Austin", "Round Rock"]),
    ("78613", ["Cedar Park", "City of Austin", "Leander"]),
    ("78641", ["Leander", "Cedar Park", "Volente"]),
    ("78746", ["West Lake Hills", "Rollingwood", "City of Austin"]),
    ("78738", ["Bee Cave", "Lakeway", "City of Austin"]),
    ("78745", ["City of Austin", "Sunset Valley"]),
    ("78617", ["Del Valle", "City of Austin", "Circuit of the Americas"]),
])

FUTURE_MARKETS = OrderedDict([
    ("san-antonio-tx", "San Antonio -- 80 miles south-west, its own airport (SAT), River Walk and convention market."),
    ("san-marcos-new-braunfels-tx", "San Marcos / New Braunfels -- the I-35 river-tubing, outlet and university "
                                    "destination between Austin and San Antonio."),
    ("texas-hill-country", "Fredericksburg / Wimberley / Johnson City / Driftwood / Spicewood / Marble Falls -- the "
                           "destination Hill Country a traveller drives TO."),
    ("waco-tx", "Waco -- 100 miles north, Baylor University and Magnolia Market."),
    ("killeen-temple-tx", "Killeen / Temple / Belton -- 60-70 miles north, Fort Cavazos and its own airport."),
    ("college-station-tx", "Bryan / College Station -- Texas A&M's own market."),
])

#: Markets that are ALREADY LIVE. None of them owns a Texas postal code; named so the collision guards know the only
#: exposure is NAME, never premises.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("phoenix-az", "Phoenix / Scottsdale / Valley of the Sun, live as production market #37 (deploy "
                   "6abc8387e81507b25eb94a0a) -- the CURRENT LIVE market at this order's authoring time. No live "
                   "market owns a Texas postal code; the only cross-market exposure is a shared chain NAME, which "
                   "rule G and the bare-chain test guard."),
    ("denver-co", "Denver, live (deploy 6aba7587ddcc33a192bdf694) -- shares chain names but no postal code."),
])

#: A shared postal code whose OTHER town is refused. None in this market at authoring time: every admitted code's
#: towns are admitted together (78641's Volente shoreline is a Travis County village inside Leander's code).
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "austin,": "austin", "austin tx": "austin", "austin, tx": "austin", "atx": "austin",
    "round rock,": "round rock", "pflugerville,": "pflugerville", "cedar park,": "cedar park",
    "georgetown,": "georgetown", "lakeway,": "lakeway", "bee cave,": "bee cave", "bee caves": "bee cave",
    "west lake hills,": "west lake hills", "westlake hills": "west lake hills", "west lake hls": "west lake hills",
    "sunset valley,": "sunset valley", "buda,": "buda", "kyle,": "kyle", "leander,": "leander", "hutto,": "hutto",
    "manor,": "manor", "dripping springs,": "dripping springs", "dripping spgs": "dripping springs",
    "del valle,": "del valle", "rollingwood,": "rollingwood", "manchaca,": "manchaca",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("78701", "Downtown / Convention Center / Capitol / Rainey -- one postal code, never split."),
    ("78704", "South Congress, Zilker, Barton Springs and South Lamar share one code."),
    ("78719", "AUS -- the airport owns its code."),
    ("78758", "The Domain / North Burnet -- Austin's 'second downtown'."),
    ("78681", "Round Rock -- including the City of Austin's Brushy Creek edge; covered whole."),
    ("78745", "South Austin -- including the City of Sunset Valley; covered whole."),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Austin" % name),
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
            ("state_code", "TX"),
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
        raise SystemExit("admitted postal codes outside the Austin prefixes: %s" % stray)

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius), ("state_code", "TX"),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Austin / Central Texas city, airport, event, university, corporate and Hill Country gateway "
                        "lodging market (PetTripFinder discovery scope)"),
        ("state", "TX"),
        ("states", ["TX"]),
        ("country", "US"),
        ("market_center", {"lat": 30.27, "lng": -97.74}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches south past downtown San Antonio, north past "
             "Waco, west past Fredericksburg and east past College Station, so that " + WORK_ORDER + " classifies "
             "those properties on evidence instead of being blind to them. Admission is decided by the corridor "
             "registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". Austin / Central Texas is ONE market: eight CORE corridors (downtown, South Congress, East "
         "Austin, UT / Central, the Domain / North Austin, Arboretum / Northwest, South Austin, AUS), eight STRONG "
         "CORRIDORS (Round Rock, Pflugerville, Cedar Park, Georgetown, Lakeway / Bee Cave, West Lake Hills, Buda, Kyle) "
         "and four FRINGE corridors (Leander, Hutto, Manor, Dripping Springs). SAN ANTONIO, SAN MARCOS / NEW "
         "BRAUNFELS, the destination HILL COUNTRY, WACO, KILLEEN / TEMPLE and COLLEGE STATION are refused as future "
         "standalone markets; Bastrop, Elgin, Liberty Hill, Taylor and Lockhart are refused by name."),
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
        ("market_name", "Austin, Texas"),
        ("market_slug", MARKET_ID),
        ("state_name", "Texas"),
        ("state_code", "TX"),
        ("primary_state_code", "TX"),
        ("states", ["TX"]),
        ("primary_city", "Austin"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Austin, Round Rock & Central Texas | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Austin and Central Texas -- downtown, South Congress, East Austin, UT, "
         "the Domain, the Arboretum, the airport, Round Rock, Pflugerville, Cedar Park, Georgetown, Lakeway, Buda and "
         "Kyle -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Austin"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry. An Austin / Central Texas city, airport, event, university, "
         "corporate and Hill Country gateway travel market -- the contiguous metro from Georgetown and Hutto to Kyle "
         "and from Manor and the airport to Lakeway and Dripping Springs. Not 'Central Texas': San Antonio, San "
         "Marcos / New Braunfels, the destination Hill Country, Waco, Killeen / Temple and College Station are future "
         "standalone markets; Bastrop, Elgin and Liberty Hill are refused. Nothing else admits a property: not a "
         "brand's 'Austin' or 'Hill Country' marketing name, not a map pin, not a vacation-rental listing, not a "
         "competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). The postal city "
         "'AUSTIN' spans eight corridors and places nothing by itself. Shared codes are covered whole: 78701 by "
         "downtown, the Convention Center and the Capitol; 78681 by Round Rock and Austin's Brushy Creek edge; 78660 "
         "by Pflugerville; 78613 by Cedar Park; 78745 by South Austin and Sunset Valley. The Convention Center, Sixth "
         "Street, the Domain, the Arboretum, the Circuit of the Americas and the Dell Diamond are overlays."),
        ("_census_membership_note",
         "Individual condominium units, private residences, vacation homes, property-management and corporate-housing "
         "portfolios, serviced-apartment operators, Airbnb / Vrbo inventory, ordinary apartments, timeshare and "
         "vacation-club inventory, residential-only towers, privately managed residences inside hotel towers, "
         "member-only club lodging and government billeting are never admitted. A mixed hotel / condo / residence "
         "property is admitted only as the exact hotel premises its public operator sells as a hotel."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class") for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 + 5 -- Austin / Central Texas travel-market geography, traveller-market logic, the Hill "
                  "Country boundary and the resort / condo / vacation-ownership safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/austin-tx.json. This order "
         "does not register, authorize or deploy anything."),
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
        ("pet_travel_relevance",
         "Austin was selected as a high-value PetTripFinder market for its regional road-trip traffic, large events, "
         "business travel, outdoor recreation, parks and trails, long-stay and extended-stay demand, pet-friendly "
         "neighbourhoods, airport traffic, Round Rock / North Austin corporate demand and Hill Country gateway role. "
         "That lowers NO evidence standard: pet acceptance is never inferred from Austin's reputation. It shapes only "
         "the CENSUS: every event, trail, extended-stay, airport and road-trip lodging cluster the traveller geography "
         "names is covered by an admitting corridor."),
        ("the_austin_name_trap",
         "The chains put 'Austin' on hotels from Georgetown to Bastrop and 'Austin Hill Country' / 'Lake Travis' on "
         "resorts from Lakeway to Marble Falls; 'Austin Airport' spans 78719, 78741, 78742, 78744 and 78617. A "
         "property's own postal code, street and brand property code decide what and where it is; none of those words "
         "decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("Austin-Bergstrom International Airport (AUS)", "its own corridor aus-airport (78719 / 78741 / 78742 / "
                                                             "78617)."),
            ("Austin Convention Center / Capitol / Sixth Street / Rainey", "downtown-austin (78701) -- overlays."),
            ("University of Texas / DKR stadium / Moody Center", "ut-central (78705 / 78712) and downtown -- overlays."),
            ("Zilker Park (ACL) / Barton Springs / South Congress", "south-congress (78704) -- overlays."),
            ("The Domain / Q2 Stadium", "domain-north-austin (78758) -- overlay."),
            ("Circuit of the Americas (F1, MotoGP)", "aus-airport (78617) -- overlay."),
            ("Dell / Round Rock corporate campuses / Dell Diamond / Kalahari", "round-rock -- overlays."),
            ("Apple / Samsung / Tesla campuses", "arboretum-northwest (78729 / 78750), domain-north-austin, "
                                                 "aus-airport (Tesla Giga Texas, 78725 / 78617) -- overlays."),
            ("Lady Bird Lake / the Greenbelt / Lake Travis", "south-congress, downtown-austin, lakeway-bee-cave -- "
                                                              "overlays."),
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
        ("first_texas_market", True),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]), ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = 5 verified "
         "pet-friendly hotels) is met. No thin corridor page is invented for SEO, airport, event, university or "
         "stadium keywords; every corridor is show_in_navigation / show_in_sitemap false until a registration "
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
         "privately managed residences; member-only club lodging; government billeting; and privately managed units "
         "inside hotel-condo towers. Campgrounds, RV parks and hostels are NON_LODGING."),
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
        return "OUTSIDE", None, "Central Texas postal code %r is claimed by no corridor" % z
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
