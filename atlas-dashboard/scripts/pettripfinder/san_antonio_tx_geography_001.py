"""PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001 -- Phases 2, 3, 4, 5 and 6: the San Antonio / Greater San Antonio
market.

Built from zero on the CURRENT hardened lineage: the Austin-live release 3afa9b17 (live lineage commit f0ddbcde,
built_from ef28f7b4). Current verified live at authoring time = austin-tx deploy 6abf3e749cc359701298718d, 38 markets
/ 3,386 profiles / 3,737 release-index routes / 3,808 served routes, host verified (release_index live-source
--fetch --verify-host). No earlier San Antonio build exists. It is the SECOND Texas market: Austin (live) owns the
786 / 787 postal codes this market refuses, and this market admits no postal code Austin's partition carries.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical San Antonio / Greater San Antonio traveller lodging market -- not the municipal City of San Antonio,
and not "South Texas" -- stated as an explicit CORE / CORRIDOR / FRINGE / OUTSIDE rule (with FUTURE_STANDALONE
markets named inside OUTSIDE) before a single hotel is admitted, so no property is admitted or refused after the
fact to make a number. The order's "STRONG CORRIDOR" class is registry class CORRIDOR.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page (or its brand's own property
card) states it, joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted
lodging ZIP is claimed by exactly one corridor, so a property's corridor is a lookup and never a judgement. A
brand's marketing name never admits and never places a property: a hotel titled "San Antonio North" whose own
address states Selma 78154 is a Selma / Schertz hotel, a hotel titled "San Antonio Airport" whose own address states
78217 is still an airport-corridor hotel only because 78217 is, and a resort titled "Hill Country" whose own address
states 78251 is a SeaWorld / Westover Hills hotel.

WHY "SAN ANTONIO" DECIDES NOTHING HERE (PHASE 4)
------------------------------------------------
The chains put "San Antonio" on hotels in Selma, Schertz, Live Oak, Universal City, Converse, Leon Valley, Boerne,
New Braunfels and even Seguin, "San Antonio North" on I-35 hotels in 78154 / 78233, and "San Antonio Hill Country" /
"Texas Hill Country" on resorts in 78251 (Westover Hills), 78261 (Cibolo Canyons), 78256 (La Cantera), Boerne and
New Braunfels. "Riverwalk" is on hotel names three postal codes apart (78204 / 78205 / 78215). A property's own
postal code places it; its name never does.

THE NEW BRAUNFELS / HILL COUNTRY BOUNDARY (PHASE 4)
--------------------------------------------------
New Braunfels, Gruene, Canyon Lake and Seguin (781 30-33 / 55-56, 78070) are refused as the FUTURE_STANDALONE
san-marcos-new-braunfels-tx market -- the I-35 river-tubing and Schlitterbahn destination the live Austin geography
already preserves under that id. Fredericksburg, Kerrville, Comfort, Bandera, Pipe Creek, Bergheim, Spring Branch and
BOERNE / FAIR OAKS RANCH (78006 / 78015) are refused as the FUTURE_STANDALONE texas-hill-country market -- the live
Austin geography names Boerne in that market's inventory, and one premises can belong to one market only. The
metro-continuous US-281 north spine (Stone Oak, Timberwood Park, BULVERDE 78163) is admitted, Bulverde at FRINGE;
Castroville (78009), 15 miles past Loop 1604 across a rural US-90 gap in Medina County, is refused after careful
evaluation. A founder can move Boerne or Castroville on the record; this order does not.

MILITARY / GOVERNMENT LODGING (PHASE 5)
--------------------------------------
Joint Base San Antonio owns three postal codes inside the admitted partition: JBSA-Lackland (78236), JBSA-Fort Sam
Houston (78234) and JBSA-Randolph (78150). Their on-base lodging -- the Lackland Gateway Inn, the Fort Sam Houston and
Randolph inns, the IHG Army Hotels on post, Air Force Inns, Navy Lodges -- is restricted to DoD-ID holders and their
sponsored guests and is NEVER admitted as an ordinary public hotel (MILITARY_RESTRICTED, NONPUBLIC_NAMES below). A
public commercial hotel OUTSIDE the gate (the Military Drive / US-90 / Valley Hi hotel rows) is an ordinary hotel and
is admitted on its own page like any other.

TRAVELLER-MARKET LOGIC (PHASE 3)
--------------------------------
San Antonio is a River Walk / Alamo tourism, convention (Henry B. Gonzalez Convention Center), military-family
(basic-training graduations at Lackland, Brooke Army Medical Center, Fort Sam Houston), business / medical (the South
Texas Medical Center), theme-park (SeaWorld, Six Flags Fiesta Texas), resort (La Cantera, the Hyatt Hill Country, the
JW Marriott TPC), extended-stay, airport (SAT) and Hill Country gateway market on I-10 / I-35 / I-37 / US-281 / US-90.
That lowers NO evidence standard: no destination reputation ("dog-friendly River Walk", a hotel's marketing) is ever
policy evidence. It shapes only the CENSUS: every tourist, convention, military, medical, theme-park, resort,
extended-stay, airport and road-trip cluster is covered by an admitting corridor.

RESORT / CONDO / VACATION-OWNERSHIP SAFETY (PHASE 6)
---------------------------------------------------
Qualifying public hotels and resorts are admitted on their own pages. Individual condo units, private residences,
Airbnb / Vrbo units, ordinary apartments, corporate-housing and property-management portfolios, serviced-apartment
operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Lark) and timeshare / vacation-club inventory (Club
Wyndham, WorldMark, Hilton Grand Vacations, Marriott Vacation Club, Holiday Inn Club Vacations, Bluegreen, Diamond /
Hilton Vacation Club, Hyatt Vacation Club, the Villas at the Hill Country resorts) are never admitted; a mixed
property is admitted only as the exact hotel premises its public operator sells. Phoenix's lesson is carried as a
RULE: a vacation-club resort is TIMESHARE even when its brand lists it beside its hotels and even when a pet-policy
page exists.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/san_antonio_tx.json
  launch_packages/pettripfinder/markets/proposed/san-antonio-tx.json
  launch_packages/pettripfinder/markets/reports/san_antonio_tx_geography_001.json
  launch_packages/pettripfinder/markets/reports/san_antonio_tx_corridor_registry_001.json
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

WORK_ORDER = "PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-antonio-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "san_antonio_tx.json")
#: NOT registered by this order. A source-ready market's document lives under markets/proposed/ until a
#: registration order moves it to the registry's markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "san-antonio-tx.json")
REPORT_OUT = os.path.join(REPORTS, "san_antonio_tx_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "san_antonio_tx_corridor_registry_001.json")
#: The live Austin market's own registered document: no postal code it admits may be admitted here.
LIVE_AUSTIN_MARKET = os.path.join(PKG, "markets", "austin-tx.json")
AS_OF = "2026-10-02"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    # ---------------------------------------------------------------- CORE
    ("downtown-river-walk", "Downtown & River Walk", "Downtown / River Walk / The Alamo / Convention Center / "
     "Hemisfair / Market Square", "CORE", "san antonio", ["78205", "78207"],
     "Downtown San Antonio's central business district (78205): the River Walk's downtown loop, the Alamo and Alamo "
     "Plaza, the Henry B. Gonzalez Convention Center, Hemisfair and La Villita, the Tower of the Americas and the "
     "Rivercenter -- and Market Square, UTSA's downtown campus and the near West Side across I-35 / I-10 (78207). "
     "The River Walk, the Alamo and the Convention Center are OVERLAYS of 78205, never a split code."),
    ("pearl-broadway", "Pearl & Broadway", "The Pearl / River North / Broadway / Tobin Hill / Monte Vista / "
     "Brackenridge Park", "CORE", "san antonio", ["78215", "78212"],
     "The Pearl brewery district and River North on the Museum Reach of the River Walk (78215), and Broadway, Tobin "
     "Hill, Monte Vista, Olmos Park, Brackenridge Park, the San Antonio Zoo and Trinity University north of it "
     "(78212). A boutique-hotel, dining and museum district."),
    ("southtown", "Southtown & King William", "Southtown / King William / Lavaca / Blue Star / Durango Blvd",
     "CORE", "san antonio", ["78204", "78210"],
     "Southtown and the King William historic district on the River Walk's Mission Reach (78204) -- the Blue Star "
     "arts complex, the Durango Boulevard edge of downtown and the Lone Star brewery redevelopment -- and the Lavaca, "
     "Roosevelt / Mission Road and S St Mary's side to the south-east (78210)."),
    ("sat-airport", "San Antonio Airport (SAT)", "SAT / Airport Blvd / NE & NW Loop 410 at US-281 / North Star / "
     "Broadway north", "CORE", "san antonio", ["78216", "78217"],
     "San Antonio International Airport's own lodging system: the airport campus and Airport Boulevard, the Loop 410 "
     "/ US-281 interchange hotel rows, North Star Mall and San Pedro Avenue (78216), and the Broadway / Wurzbach "
     "Parkway / Perrin Beitel / NE Loop 410 side east of the runways (78217). SAT owns 78216, so the AIRPORT test "
     "answers YES. A hotel marketed 'San Antonio Airport' whose own code is elsewhere is placed by that code."),
    ("medical-center", "Medical Center", "South Texas Medical Center / Fredericksburg Rd / Wurzbach / Babcock / "
     "USAA / Balcones Heights", "CORE", "san antonio", ["78229", "78240", "78230", "78201"],
     "The South Texas Medical Center (78229) -- University Hospital, UT Health San Antonio, Methodist and Christus -- "
     "with the Wurzbach / Babcock / Fredericksburg Road hotel rows (78229 / 78240), USAA and the I-10 / Wurzbach / "
     "Huebner side to the north (78230), and Balcones Heights / the Fredericksburg Road approach at Loop 410 (78201). "
     "Medical, business and extended-stay demand."),
    ("north-central", "North Central", "Alamo Heights / The Quarry / Castle Hills / Blanco Rd / US-281 north / "
     "Shavano Park / Hollywood Park", "CORE", "san antonio", ["78209", "78213", "78231", "78232", "78248"],
     "North-central San Antonio between Loop 410 and Loop 1604: the City of Alamo Heights, Terrell Hills and the "
     "Quarry Market (78209), Castle Hills and Blanco Road (78213), Shavano Park (78231), Hollywood Park and the US-281 "
     "/ Bitters / Thousand Oaks corridor (78232) and the Huebner / Blanco north side (78248). Alamo Heights is an "
     "enclave of the city, admitted with it."),
    ("stone-oak", "Stone Oak & Far North", "Stone Oak / US-281 north of Loop 1604 / Sonterra / Timberwood Park / "
     "TPC / Cibolo Canyons", "CORE", "san antonio", ["78258", "78259", "78260", "78261"],
     "Stone Oak and the US-281 north corridor beyond Loop 1604 (78258 / 78259), Timberwood Park (78260) and the TPC "
     "San Antonio / Cibolo Canyons resort district (78261). The JW Marriott San Antonio Hill Country Resort stands in "
     "78261: its 'Hill Country' name places nothing, its own postal code does."),
    ("northwest-la-cantera", "Northwest & La Cantera", "UTSA / I-10 at De Zavala & Huebner / Loop 1604 / La "
     "Cantera / The Shops at La Cantera", "CORE", "san antonio", ["78249", "78256"],
     "UTSA's main campus and the I-10 / De Zavala / Huebner / Loop 1604 hotel rows (78249), and La Cantera -- the La "
     "Cantera Resort & Spa and The Shops at La Cantera (78256)."),
    ("six-flags-rim", "Six Flags & The Rim", "Six Flags Fiesta Texas / The Rim / I-10 at Loop 1604 / Leon Springs / "
     "The Dominion", "CORE", "san antonio", ["78257", "78255"],
     "Six Flags Fiesta Texas and The Rim shopping district on I-10 at Loop 1604 (78257), and the Dominion / Leon "
     "Springs / Camp Bullis edge of I-10 north-west (78255). Fair Oaks Ranch and Boerne beyond it are refused "
     "(FUTURE_STANDALONE texas-hill-country)."),
    ("seaworld-westover-hills", "SeaWorld & Westover Hills", "SeaWorld San Antonio / Westover Hills / SH-151 / "
     "Loop 1604 west / Potranco / Alamo Ranch / Culebra", "CORE", "san antonio",
     ["78245", "78251", "78253", "78254"],
     "SeaWorld San Antonio and Aquatica (78245), the Westover Hills business park and the Hyatt Regency Hill Country "
     "Resort on SH-151 (78251), Alamo Ranch and the Loop 1604 / Potranco / Culebra far-west edge (78253 / 78254). "
     "The Hyatt's 'Hill Country' name places nothing."),
    ("lackland-west", "Lackland & West San Antonio", "JBSA-Lackland gate / Military Dr W / US-90 W / Port San "
     "Antonio / Kelly / Culebra / Ingram west", "CORE", "san antonio",
     ["78227", "78236", "78242", "78226", "78237", "78228"],
     "The Military Drive / US-90 West / Valley Hi hotel rows outside JBSA-Lackland's gates (78227 / 78242) -- the "
     "basic-training graduation lodging market -- the base itself (78236; its on-base lodging is MILITARY_RESTRICTED "
     "and never admitted), Port San Antonio / the former Kelly AFB (78226) and the West Side's Commerce / Culebra / "
     "Callaghan corridors (78237 / 78228)."),
    ("east-side", "East Side & Fort Sam Houston", "JBSA-Fort Sam Houston / Brooke Army Medical Center / Frost Bank "
     "Center / I-10 East / I-35 at Walters / Harry Wurzbach", "CORE", "san antonio",
     ["78202", "78203", "78208", "78219", "78220", "78222", "78234"],
     "The East Side: JBSA-Fort Sam Houston and Brooke Army Medical Center (78234; on-post lodging MILITARY_RESTRICTED), "
     "the Fort Sam / I-35 Walters / New Braunfels Avenue approach (78208), the Frost Bank Center, Freeman Coliseum and "
     "the San Antonio Stock Show grounds (78219 / 78220), the I-10 East / WW White / Foster Road rows (78219 / 78220 / "
     "78222) and the near-east neighbourhoods (78202 / 78203)."),
    ("south-side", "South Side, Missions & Brooks", "Missions National Historical Park / I-35 South / I-37 South / "
     "SE & SW Military Dr / Brooks / Mission Rd", "CORE", "san antonio",
     ["78211", "78214", "78221", "78223", "78224", "78225", "78235", "78263", "78264"],
     "The South Side: the San Antonio Missions (Mission San Jose, Concepcion, San Juan, Espada; 78210 / 78214 / "
     "78221), the I-35 South and SW Military Drive hotel rows (78211 / 78224 / 78225), the I-37 South and SE Military "
     "Drive / Brooks City Base rows (78223 / 78235) and the rural south-east Bexar I-37 / US-181 edge (78263 / "
     "78264)."),
    ("northeast", "Northeast & Windcrest", "Windcrest / Walzem / Rittiman / NE Loop 410 / I-35 north to Loop 1604 / "
     "Thousand Oaks / O'Connor", "CORE", "san antonio", ["78218", "78239", "78244", "78247"],
     "Northeast San Antonio between Loop 410 and Loop 1604: the NE Loop 410 / Walzem / Rittiman / I-35 hotel rows "
     "(78218), the City of Windcrest (78239), the Converse-edge north-east (78244) and Thousand Oaks / O'Connor / "
     "Nacogdoches (78247). Windcrest is an enclave of the city, admitted with it."),
    # ---------------------------------------------------------------- STRONG CORRIDOR
    ("live-oak-universal-city", "Live Oak & Universal City", "Live Oak / The Forum / Universal City / Randolph / "
     "I-35 & Loop 1604", "CORRIDOR", "live oak", ["78233", "78148", "78150"],
     "The City of Live Oak and the Forum at Olympia Parkway on I-35 at Loop 1604 (78233), the City of Universal City "
     "on Pat Booker Road (78148) and JBSA-Randolph (78150; its on-base lodging is MILITARY_RESTRICTED). 78233 also "
     "carries part of the City of San Antonio and is covered whole. STRONG."),
    ("selma-schertz", "Selma, Schertz & Cibolo", "Selma / Schertz / Cibolo / I-35 north / FM-3009 / Garden Ridge",
     "CORRIDOR", "schertz", ["78154", "78108", "78266"],
     "The Cities of Selma and Schertz on I-35 north (78154) -- the Retama Park / FM-3009 / I-35 hotel cluster -- and "
     "Cibolo / east Schertz (78108) and Garden Ridge / far north-east San Antonio (78266). Metro-continuous with Live "
     "Oak along I-35; NEW BRAUNFELS (781 30-32) beyond it is refused. Cibolo is admitted through 78108, which it "
     "shares with Schertz and which is covered whole. STRONG."),
    ("leon-valley-helotes", "Leon Valley & Helotes", "Leon Valley / Ingram Park / NW Loop 410 at Bandera Rd / "
     "Tezel / Helotes", "CORRIDOR", "leon valley", ["78238", "78250", "78023"],
     "The City of Leon Valley and the Ingram Park / NW Loop 410 / Bandera Road hotel cluster (78238), the Bandera Road "
     "/ Tezel side of north-west San Antonio (78250) and the City of Helotes (78023). STRONG."),
    # ---------------------------------------------------------------- FRINGE
    ("converse", "Converse", "Converse / FM-78 / Loop 1604 east", "FRINGE", "converse", ["78109"],
     "The City of Converse (78109) on FM-78 and Loop 1604 east, contiguous with north-east San Antonio and Live Oak. "
     "Admitted at FRINGE after CAREFUL evaluation so its small hotel inventory is ACCOUNTED FOR."),
    ("bulverde", "Bulverde & US-281 North", "Bulverde / US-281 north of Timberwood Park", "FRINGE", "bulverde",
     ["78163"],
     "The City of Bulverde (78163) on US-281 north of Timberwood Park -- Comal County, inside the San Antonio MSA and "
     "metro-continuous along US-281 from Stone Oak. Admitted at FRINGE after CAREFUL evaluation. Spring Branch, "
     "Canyon Lake and the Guadalupe River destinations beyond it are refused."),
]

OUTSIDE = [
    ("Austin / Central Texas -- LIVE austin-tx (Austin, Round Rock, Pflugerville, Cedar Park, Georgetown, Lakeway, "
     "Buda, Kyle, Dripping Springs ...)", "TX", [],
     "TRAVIS / WILLIAMSON / HAYS COUNTY; the LIVE austin-tx market, 80 miles north-east on I-35. Refused by postal "
     "PREFIX (786 / 787); no postal code Austin's own partition admits is admitted here."),
    ("New Braunfels / Gruene / Canyon Lake / Seguin / McQueeney / Spring Branch", "TX",
     ["78130", "78131", "78132", "78133", "78135", "78155", "78156", "78123", "78070"],
     "COMAL / GUADALUPE COUNTY; FUTURE_STANDALONE san-marcos-new-braunfels-tx (the id the live Austin geography "
     "preserves). The Schlitterbahn / Gruene / Guadalupe and Comal river-tubing destination 30 miles north-east on "
     "I-35, Canyon Lake, and Seguin on I-10 east -- its own bureau, its own river-and-lake destination demand. A "
     "property marketed 'San Antonio / New Braunfels' at one of these codes is refused by its own address. Seguin is "
     "refused: no traveller-market evidence strongly supports inclusion."),
    ("San Marcos / Martindale / Maxwell", "TX", ["78666", "78667", "78655", "78656"],
     "HAYS / CALDWELL COUNTY; FUTURE_STANDALONE san-marcos-new-braunfels-tx. Texas State University and the Premium "
     "Outlets, 50 miles north-east on I-35."),
    ("Texas Hill Country destination inventory -- Boerne, Fair Oaks Ranch, Bergheim, Comfort, Kerrville, Ingram, "
     "Center Point, Bandera, Pipe Creek, Medina, Fredericksburg, Johnson City, Blanco, Wimberley, Sisterdale", "TX",
     ["78006", "78015", "78004", "78013", "78028", "78029", "78024", "78010", "78003", "78063", "78055", "78624",
      "78631", "78636", "78606", "78676", "78027", "78074"],
     "KENDALL / KERR / BANDERA / GILLESPIE / BLANCO COUNTY; FUTURE_STANDALONE texas-hill-country. The destination "
     "Hill Country a traveller drives TO: Boerne's Main Street and its Hill Country resorts and B&Bs (the live Austin "
     "geography names Boerne in that market's inventory -- one premises, one market), Comfort, Kerrville, Bandera "
     "('the Cowboy Capital'), Fredericksburg and the wine road. A property marketed 'San Antonio Hill Country' at one "
     "of these codes is refused by its own address. A founder may move Boerne on the record."),
    ("Castroville / La Coste / Rio Medina / Mico / Hondo", "TX", ["78009", "78039", "78066", "78056"],
     "MEDINA COUNTY; refused after CAREFUL evaluation. Castroville ('the Little Alsace of Texas') is its own town 15 "
     "miles past Loop 1604 across a rural US-90 gap, with its own small destination inventory. Hondo (78861) and the "
     "788 prefix beyond are refused by prefix."),
    ("Rural outer Bexar and the south / east ring -- Von Ormy, Atascosa, Somerset, Lytle, Elmendorf, Adkins, St "
     "Hedwig, Marion, La Vernia, Floresville, Pleasanton, Poteet, Jourdanton, Devine, Natalia", "TX",
     ["78073", "78002", "78069", "78052", "78112", "78101", "78152", "78124", "78121", "78114", "78064", "78065",
      "78026", "78016", "78059"],
     "BEXAR (rural edge) / WILSON / ATASCOSA / MEDINA / GUADALUPE COUNTY; refused by name and postal code. Separate "
     "towns and rural highway stops (I-35 South past Loop 1604, I-37 / US-181 south, I-10 East past Loop 1604) across "
     "a rural gap -- the metro-continuity test fails. Recorded, never silently absorbed."),
    ("Corpus Christi / the Coastal Bend", "TX", [],
     "NUECES / SAN PATRICIO COUNTY; FUTURE_STANDALONE corpus-christi-tx. Refused by postal PREFIX (783 / 784). 140 miles "
     "south-east on I-37."),
    ("Other Texas and out of state", "--", [],
     "Every other Texas postal prefix (750-799 outside this market's codes) and every non-Texas code is refused."),
]

#: Postal PREFIXES refused as a class, so an unlisted code in a refused region is refused by its prefix and never
#: falls through to "claimed by no corridor". (prefix, name, future market)
OUTSIDE_PREFIXES = [
    ("786", "Austin region / north Hill Country (Travis / Williamson / Hays / Blanco / Gillespie / Burnet)", "austin-tx"),
    ("787", "Austin (LIVE)", "austin-tx"),
    ("765", "Killeen / Temple / Belton (Bell County)", "killeen-temple-tx"),
    ("766", "Waco region (McLennan County)", "waco-tx"),
    ("767", "Waco", "waco-tx"),
    ("778", "Bryan / College Station / Brenham", "college-station-tx"),
    ("789", "La Grange / Giddings / Columbus / Gonzales (Fayette / Lee / Colorado / Gonzales County)", ""),
    ("788", "Uvalde / Del Rio / Hondo / south-west Texas", ""),
    ("779", "Victoria / the Coastal Bend", ""),
    ("783", "Corpus Christi", "corpus-christi-tx"), ("784", "Corpus Christi", "corpus-christi-tx"),
    ("785", "the Rio Grande Valley", ""),
    ("750", "Dallas region", ""), ("751", "Dallas region", ""), ("752", "Dallas", ""), ("753", "Dallas", ""),
    ("760", "Fort Worth region", ""), ("761", "Fort Worth", ""), ("762", "Denton region", ""),
    ("763", "Wichita Falls", ""), ("764", "Stephenville / Brownwood", ""), ("768", "Abilene / Brownwood", ""),
    ("769", "San Angelo", ""), ("770", "Houston", ""), ("772", "Houston", ""), ("773", "Houston region", ""),
    ("774", "Houston region", ""), ("775", "Houston region", ""), ("776", "Beaumont", ""), ("777", "Beaumont", ""),
    ("790", "Amarillo", ""), ("791", "Amarillo", ""), ("793", "Lubbock", ""), ("794", "Lubbock", ""),
    ("795", "Abilene", ""), ("796", "Abilene", ""), ("797", "Midland / Odessa", ""), ("798", "El Paso", ""),
    ("799", "El Paso", ""),
]

#: San Antonio's own postal prefixes. A code under one of these that no corridor claims and no OUTSIDE row names is
#: an UNCLAIMED South Texas code -- refused, and named in the boundary audit so it is visible, never silently
#: dropped.
VALLEY_PREFIXES = ("780", "781", "782")

ADMITTED_COUNTIES = {"bexar (city of san antonio and its enclaves and inner suburbs; rural edge refused)",
                     "guadalupe (schertz / cibolo / selma edge)",
                     "comal (bulverde, garden ridge; new braunfels / canyon lake / spring branch refused)"}
OBSERVED_COUNTIES = OrderedDict([
    ("travis / williamson / hays (austin)", "austin-tx (LIVE)"),
    ("comal / guadalupe (new braunfels, gruene, canyon lake, seguin)", "san-marcos-new-braunfels-tx"),
    ("hays south (san marcos)", "san-marcos-new-braunfels-tx"),
    ("kendall / kerr / bandera / gillespie / blanco (boerne, comfort, kerrville, bandera, fredericksburg)",
     "texas-hill-country"),
    ("medina (castroville, hondo)", "(none -- refused by name after careful evaluation)"),
    ("wilson / atascosa / rural bexar (floresville, pleasanton, von ormy, elmendorf)", "(none -- refused by name)"),
    ("nueces (corpus christi)", "corpus-christi-tx"),
])

#: The county-line rulings the order's boundary clauses demand.
COUNTY_BOUNDARY_RULES = OrderedDict([
    ("bexar", OrderedDict([
        ("ruling", "ADMITTED, SPLIT. The City of San Antonio with its enclaves (Alamo Heights, Terrell Hills, Olmos "
                   "Park, Castle Hills, Balcones Heights, Windcrest, Kirby, Shavano Park, Hollywood Park) and its "
                   "inner suburbs (Leon Valley, Helotes, Live Oak, Universal City, Converse, Selma) are admitted; the "
                   "rural edge past Loop 1604 (Von Ormy, Atascosa, Somerset, Elmendorf, Adkins, St Hedwig) is "
                   "REFUSED. County inclusion is not traveller-market inclusion."),
    ])),
    ("guadalupe", OrderedDict([
        ("ruling", "ADMITTED ONLY ON THE I-35 / FM-3009 / FM-78 METRO EDGE. Schertz, Cibolo and Selma's Guadalupe side "
                   "are admitted; Seguin, Marion and McQueeney are refused."),
    ])),
    ("comal", OrderedDict([
        ("ruling", "ADMITTED ONLY ON THE US-281 / I-35 METRO EDGE. Bulverde (US-281, FRINGE) and Garden Ridge "
                   "(78266) are admitted; New Braunfels, Gruene, Canyon Lake and Spring Branch are refused "
                   "(FUTURE_STANDALONE san-marcos-new-braunfels-tx)."),
    ])),
    ("kendall / kerr / bandera / medina", OrderedDict([
        ("ruling", "REFUSED. Boerne / Fair Oaks Ranch, Comfort, Kerrville, Bandera and Pipe Creek are the destination "
                   "Hill Country (FUTURE_STANDALONE texas-hill-country); Castroville and Hondo are refused after careful "
                   "evaluation. San Antonio does not absorb the Hill Country."),
    ])),
    ("wilson / atascosa / nueces / travis / williamson / hays", OrderedDict([
        ("ruling", "REFUSED. Floresville, Pleasanton and the south ring are separate towns; Corpus Christi and Austin "
                   "(LIVE) are separate traveller markets. San Antonio does not absorb South / Central Texas."),
    ])),
])

#: Names refused as NON-PUBLIC lodging inside an admitted postal code (military / government / member only). A
#: normalised-name substring match; the census row keeps its reason. Public commercial hotels near a base are NOT
#: here -- they are ordinary hotels.
NONPUBLIC_NAMES = {
    "gateway inn": "JBSA-Lackland on-base lodging (Air Force Inns) -- restricted to DoD-ID holders and sponsored "
                   "guests; MILITARY_RESTRICTED",
    "lackland gateway": "JBSA-Lackland on-base lodging -- MILITARY_RESTRICTED",
    "air force inn": "Air Force Inns on-base lodging -- MILITARY_RESTRICTED",
    "randolph inn": "JBSA-Randolph on-base lodging -- MILITARY_RESTRICTED",
    "fort sam houston inn": "JBSA-Fort Sam Houston on-post lodging -- MILITARY_RESTRICTED",
    "army hotel": "IHG Army Hotels on-post lodging -- restricted to authorised DoD travellers; MILITARY_RESTRICTED",
    "army lodging": "on-post Army lodging -- MILITARY_RESTRICTED",
    "navy lodge": "Navy Lodge on-base lodging -- MILITARY_RESTRICTED",
    "fisher house": "Fisher House -- charitable lodging for military and veteran families; not public lodging",
    "temporary lodging facility": "military temporary lodging facility (TLF) -- MILITARY_RESTRICTED",
    "visiting quarters": "military visiting quarters -- MILITARY_RESTRICTED",
    "ronald mcdonald house": "charitable family lodging -- not public lodging",
}

#: Military postal codes: a lodging row whose own code is one of these is ON-BASE unless its own page proves a
#: public commercial hotel outside the gate. Held MILITARY_RESTRICTED on the code when its name does not decide.
MILITARY_POSTAL_CODES = OrderedDict([
    ("78236", "JBSA-Lackland"),
    ("78234", "JBSA-Fort Sam Houston"),
    ("78150", "JBSA-Randolph"),
])

#: Bounded observation cells. ADMITTING cells sit on admitted corridors; OBSERVATION cells cover refused
#: neighbours so the census classifies them on evidence rather than being blind to them.
CELLS = [
    ("downtown-river-walk", "San Antonio", "Downtown / River Walk / Alamo / Convention Center", 29.4241, -98.4936,
     2200, True),
    ("pearl-broadway", "San Antonio", "Pearl / Broadway / Tobin Hill", 29.4550, -98.4780, 3000, True),
    ("southtown", "San Antonio", "Southtown / King William", 29.4050, -98.4900, 3000, True),
    ("sat-airport", "San Antonio", "SAT / Loop 410 / US-281", 29.5300, -98.4700, 5000, True),
    ("medical-center", "San Antonio", "Medical Center / Wurzbach / Fredericksburg Rd", 29.5080, -98.5700, 5000, True),
    ("north-central", "San Antonio", "Alamo Heights / Castle Hills / US-281 north", 29.5400, -98.5000, 7000, True),
    ("stone-oak", "San Antonio", "Stone Oak / TPC / Cibolo Canyons", 29.6400, -98.4600, 8000, True),
    ("northwest-la-cantera", "San Antonio", "UTSA / La Cantera", 29.5900, -98.6100, 5000, True),
    ("six-flags-rim", "San Antonio", "Six Flags / The Rim / Leon Springs", 29.6200, -98.6300, 6000, True),
    ("seaworld-westover-hills", "San Antonio", "SeaWorld / Westover Hills / Alamo Ranch", 29.4700, -98.7000, 8000,
     True),
    ("lackland-west", "San Antonio", "Lackland / West Side / Port San Antonio", 29.4100, -98.5900, 8000, True),
    ("east-side", "San Antonio", "East Side / Fort Sam / Frost Bank Center", 29.4400, -98.4300, 7000, True),
    ("south-side", "San Antonio", "South Side / Missions / Brooks", 29.3400, -98.4800, 10000, True),
    ("northeast", "San Antonio", "Northeast / Windcrest", 29.5300, -98.3800, 6000, True),
    ("live-oak-universal-city", "Live Oak", "Live Oak / Universal City / Randolph", 29.5600, -98.3100, 5000, True),
    ("selma-schertz", "Schertz", "Selma / Schertz / Cibolo", 29.5900, -98.2700, 7000, True),
    ("leon-valley-helotes", "Leon Valley", "Leon Valley / Bandera Rd / Helotes", 29.5300, -98.6400, 7000, True),
    ("converse", "Converse", "Converse", 29.5200, -98.3100, 4000, True),
    ("bulverde", "Bulverde", "Bulverde / US-281 north", 29.7400, -98.4500, 6000, True),
    ("obs-new-braunfels", "New Braunfels", "New Braunfels / Gruene / Canyon Lake -- OBSERVATION ONLY", 29.7000,
     -98.1200, 15000, False),
    ("obs-seguin", "Seguin", "Seguin -- OBSERVATION ONLY", 29.5700, -97.9600, 8000, False),
    ("obs-san-marcos", "San Marcos", "San Marcos -- OBSERVATION ONLY", 29.8800, -97.9400, 8000, False),
    ("obs-boerne", "Boerne", "Boerne / Fair Oaks Ranch -- OBSERVATION ONLY", 29.7900, -98.7300, 10000, False),
    ("obs-hill-country", "Kerrville", "Kerrville / Comfort / Bandera / Fredericksburg -- OBSERVATION ONLY", 30.0000,
     -99.0500, 30000, False),
    ("obs-castroville", "Castroville", "Castroville / Hondo -- OBSERVATION ONLY", 29.3600, -98.9000, 12000, False),
    ("obs-south-ring", "Floresville", "Floresville / Pleasanton / Von Ormy / Elmendorf -- OBSERVATION ONLY", 29.2000,
     -98.3500, 25000, False),
]

#: The observation box. It reaches north past New Braunfels and San Marcos, west past Kerrville, Bandera and
#: Castroville, south past Pleasanton and east past Seguin, so the census counts what it refuses.
BOUNDS = {"min_lat": 28.90, "max_lat": 30.30, "min_lng": -99.40, "max_lng": -97.80}

#: Reporting overlay only (never membership): the areas the order names, each an anchor point and a radius in km.
COVERAGE_AREAS = [
    ("The Alamo / Alamo Plaza", 29.4260, -98.4861, 0.35),
    ("Henry B. Gonzalez Convention Center / Hemisfair", 29.4194, -98.4836, 0.45),
    ("River Walk (downtown loop)", 29.4232, -98.4893, 0.70),
    ("Market Square / UTSA Downtown", 29.4256, -98.4995, 0.60),
    ("Downtown San Antonio CBD", 29.4241, -98.4936, 1.20),
    ("The Pearl / River North", 29.4425, -98.4800, 0.80),
    ("Broadway / Tobin Hill / Brackenridge Park", 29.4600, -98.4720, 1.40),
    ("Southtown / King William / Blue Star", 29.4110, -98.4950, 1.00),
    ("SAT terminal / Airport Blvd", 29.5337, -98.4698, 1.60),
    ("Loop 410 / US-281 / North Star", 29.5180, -98.4930, 1.60),
    ("Alamo Heights / The Quarry", 29.4900, -98.4650, 1.40),
    ("South Texas Medical Center", 29.5080, -98.5750, 2.00),
    ("Fredericksburg Rd / Balcones Heights", 29.4900, -98.5500, 1.40),
    ("Stone Oak / US-281 north", 29.6400, -98.4800, 3.00),
    ("TPC San Antonio / Cibolo Canyons", 29.6600, -98.4150, 2.50),
    ("UTSA / I-10 at De Zavala", 29.5830, -98.6190, 1.80),
    ("La Cantera", 29.5950, -98.6230, 1.20),
    ("Six Flags Fiesta Texas / The Rim", 29.6040, -98.6040, 1.20),
    ("SeaWorld San Antonio / Westover Hills", 29.4582, -98.6996, 3.00),
    ("JBSA-Lackland gate / Military Dr W", 29.3900, -98.6200, 3.00),
    ("Port San Antonio / Kelly", 29.3800, -98.5800, 2.00),
    ("JBSA-Fort Sam Houston / BAMC", 29.4580, -98.4400, 2.00),
    ("Frost Bank Center / Freeman Coliseum", 29.4270, -98.4375, 1.50),
    ("Brooks / SE Military Dr", 29.3400, -98.4400, 2.50),
    ("San Antonio Missions", 29.3620, -98.4800, 2.00),
    ("Ingram Park / Leon Valley", 29.4800, -98.6000, 2.00),
    ("Helotes", 29.5780, -98.6900, 3.00),
    ("Live Oak / The Forum", 29.5600, -98.3300, 2.50),
    ("Universal City / Randolph", 29.5480, -98.2950, 2.50),
    ("Selma / Schertz I-35", 29.5850, -98.2900, 3.00),
    ("Converse", 29.5180, -98.3160, 2.50),
    ("Windcrest / Walzem", 29.5150, -98.3800, 1.60),
]

#: Street wording on a property's OWN address that names a submarket (checked before the pin).
STREET_OVERLAYS = [
    ("The Alamo / Alamo Plaza", re.compile(r"\balamo plaza\b|\bbonham st\b|\blosoya st\b|\be crockett st\b"
                                           r"(?=.*78205)", re.I)),
    ("Henry B. Gonzalez Convention Center / Hemisfair", re.compile(r"\be market st\b(?=.*78205)|\bhemisfair\b|"
                                                                   r"\bs alamo st\b(?=.*78205)|\bbowie st\b", re.I)),
    ("Market Square / UTSA Downtown", re.compile(r"\bdolorosa\b|\bmarket sq|\bw commerce st\b(?=.*78207)", re.I)),
    ("The Pearl / River North", re.compile(r"\be grayson st\b|\bpearl pkwy\b|\bkarnes st\b|\bavenue a\b|"
                                           r"\bbroadway\b(?=.*78215)", re.I)),
    ("SAT terminal / Airport Blvd", re.compile(r"\bairport b(lv)?d\b|\bhalm b(lv)?d\b|\bjones maltsberger\b|"
                                               r"\bne loop 410\b(?=.*78216)", re.I)),
    ("South Texas Medical Center", re.compile(r"\bmedical dr\b|\bfloyd curl\b|\bmerton minter\b|"
                                              r"\bwurzbach rd\b(?=.*782(29|40))|\bbabcock rd\b(?=.*78229)|"
                                              r"\bfredericksburg rd\b(?=.*782(29|40))", re.I)),
    ("La Cantera", re.compile(r"\bla cantera\b", re.I)),
    ("Six Flags Fiesta Texas / The Rim", re.compile(r"\bthe rim\b|\brim pass\b|\bfiesta texas\b", re.I)),
    ("SeaWorld San Antonio / Westover Hills", re.compile(r"\bseaworld\b|\bwestover hills\b|\bhyatt resort dr\b", re.I)),
    ("TPC San Antonio / Cibolo Canyons", re.compile(r"\bresort pkwy\b(?=.*78261)|\bcibolo canyons\b", re.I)),
    ("Stone Oak / US-281 north", re.compile(r"\bstone oak\b|\bsonterra\b", re.I)),
    ("JBSA-Lackland gate / Military Dr W", re.compile(r"\bmilitary dr(ive)? w\b|\bw military dr\b|\bvalley hi\b",
                                                      re.I)),
    ("Ingram Park / Leon Valley", re.compile(r"\bbandera rd\b(?=.*78238)|\bingram\b(?=.*78238)", re.I)),
]

#: Coarse corridor default display names (when no street or pin overlay applies).
CORRIDOR_DEFAULT_OVERLAY = {
    "downtown-river-walk": "Downtown San Antonio",
    "pearl-broadway": "Pearl / Broadway",
    "southtown": "Southtown",
    "sat-airport": "San Antonio Airport",
    "medical-center": "Medical Center",
    "north-central": "North Central San Antonio",
    "stone-oak": "Stone Oak",
    "northwest-la-cantera": "Northwest San Antonio",
    "six-flags-rim": "Six Flags / The Rim",
    "seaworld-westover-hills": "SeaWorld / Westover Hills",
    "lackland-west": "West San Antonio",
    "east-side": "East San Antonio",
    "south-side": "South San Antonio",
    "northeast": "Northeast San Antonio",
    "live-oak-universal-city": "Live Oak / Universal City",
    "selma-schertz": "Selma / Schertz",
    "leon-valley-helotes": "Leon Valley / Helotes",
    "converse": "Converse",
    "bulverde": "Bulverde",
}

#: The order's PRIMARY / STRONG / CAREFUL / KEEP-OUTSIDE evaluation list, each classified explicitly.
EVALUATED_INCLUSIONS = OrderedDict([
    ("Downtown San Antonio", "ADMITTED (CORE, downtown-river-walk, 78205 / 78207). PRIMARY."),
    ("River Walk", "ADMITTED -- an OVERLAY: the downtown loop is 78205 (downtown-river-walk), the Museum Reach 78215 "
                   "(pearl-broadway), the Mission Reach 78204 / 78210 (southtown). A 'Riverwalk' name places "
                   "nothing. PRIMARY."),
    ("Alamo / Convention Center", "ADMITTED -- an OVERLAY of 78205 (downtown-river-walk); a postal code is never "
                                  "split, so it is reported as an overlay, not a corridor. PRIMARY."),
    ("Pearl / Broadway", "ADMITTED (CORE, pearl-broadway, 78215 / 78212). PRIMARY."),
    ("Southtown", "ADMITTED (CORE, southtown, 78204 / 78210). PRIMARY."),
    ("San Antonio International Airport / SAT", "ADMITTED (CORE, sat-airport, 78216 / 78217). PRIMARY."),
    ("Medical Center", "ADMITTED (CORE, medical-center, 78229 / 78240 / 78230 / 78201). PRIMARY."),
    ("North Central", "ADMITTED (CORE, north-central, 78209 / 78213 / 78231 / 78232 / 78248). PRIMARY."),
    ("Stone Oak", "ADMITTED (CORE, stone-oak, 78258 / 78259 / 78260 / 78261). PRIMARY."),
    ("Northwest San Antonio", "ADMITTED (CORE, northwest-la-cantera 78249 / 78256 and leon-valley-helotes 78250). "
                              "PRIMARY."),
    ("La Cantera", "ADMITTED (CORE, northwest-la-cantera, 78256). PRIMARY."),
    ("Six Flags / I-10 corridor", "ADMITTED (CORE, six-flags-rim, 78257 / 78255). PRIMARY."),
    ("SeaWorld / Westover Hills", "ADMITTED (CORE, seaworld-westover-hills, 78245 / 78251 / 78253 / 78254). "
                                  "PRIMARY."),
    ("Lackland / West San Antonio", "ADMITTED (CORE, lackland-west, 78227 / 78242 / 78226 / 78237 / 78228; on-base "
                                    "78236 lodging MILITARY_RESTRICTED). PRIMARY."),
    ("East Side / Fort Sam Houston", "ADMITTED (CORE, east-side, 78202 / 78203 / 78208 / 78219 / 78220 / 78222; on-post "
                                     "78234 lodging MILITARY_RESTRICTED) -- the city's own East Side, not named by "
                                     "the order but inside the municipal market; never left unclaimed."),
    ("South Side / Missions / Brooks", "ADMITTED (CORE, south-side, 78211 / 78214 / 78221 / 78223 / 78224 / 78225 / "
                                       "78235 / 78263 / 78264) -- inside the municipal market; never left "
                                       "unclaimed."),
    ("Northeast / Windcrest", "ADMITTED (CORE, northeast, 78218 / 78239 / 78244 / 78247). Windcrest is an enclave "
                              "of the city. CAREFUL -> admitted."),
    ("Alamo Heights", "ADMITTED (CORE, north-central, 78209) -- an enclave of the city. CAREFUL -> admitted."),
    ("Live Oak", "ADMITTED (STRONG CORRIDOR, live-oak-universal-city, 78233). STRONG."),
    ("Universal City", "ADMITTED (STRONG CORRIDOR, live-oak-universal-city, 78148). STRONG."),
    ("Selma", "ADMITTED (STRONG CORRIDOR, selma-schertz, 78154). STRONG."),
    ("Schertz", "ADMITTED (STRONG CORRIDOR, selma-schertz, 78154 / 78108 / 78266). STRONG."),
    ("Leon Valley", "ADMITTED (STRONG CORRIDOR, leon-valley-helotes, 78238). STRONG."),
    ("Helotes", "ADMITTED (STRONG CORRIDOR, leon-valley-helotes, 78023). STRONG."),
    ("Converse", "ADMITTED (FRINGE, converse, 78109) -- contiguous with north-east San Antonio and Live Oak. "
                 "CAREFUL."),
    ("Cibolo", "ADMITTED (STRONG CORRIDOR, selma-schertz, through 78108 which it shares with Schertz, covered whole). "
               "CAREFUL."),
    ("Bulverde", "ADMITTED (FRINGE, bulverde, 78163) -- San Antonio MSA, metro-continuous on US-281 from Stone Oak and "
                 "Timberwood Park; Spring Branch / Canyon Lake beyond refused. CAREFUL."),
    ("Boerne", "OUTSIDE after CAREFUL evaluation -- FUTURE_STANDALONE texas-hill-country. The live Austin geography "
               "already names Boerne in that market's inventory, and a premises belongs to one market; Boerne is a "
               "Hill Country destination town (Main Street, B&Bs, Hill Country resorts) beyond Fair Oaks Ranch. A "
               "founder may move it on the record."),
    ("Castroville", "OUTSIDE after CAREFUL evaluation -- its own town 15 miles past Loop 1604 across a rural US-90 gap "
                    "in Medina County."),
    ("Austin", "OUTSIDE -- LIVE austin-tx; refused by postal prefix 786 / 787."),
    ("New Braunfels", "OUTSIDE -- FUTURE_STANDALONE san-marcos-new-braunfels-tx."),
    ("Fredericksburg", "OUTSIDE -- FUTURE_STANDALONE texas-hill-country."),
    ("Broader Texas Hill Country destination inventory", "OUTSIDE -- FUTURE_STANDALONE texas-hill-country (Boerne, "
                                                         "Comfort, Kerrville, Bandera, Pipe Creek, Fredericksburg)."),
    ("Corpus Christi", "OUTSIDE -- FUTURE_STANDALONE corpus-christi-tx; refused by prefix 783 / 784."),
    ("Seguin", "OUTSIDE -- no traveller-market evidence strongly supports inclusion; preserved with "
               "san-marcos-new-braunfels-tx."),
    ("Kerrville", "OUTSIDE -- FUTURE_STANDALONE texas-hill-country."),
    ("Bandera", "OUTSIDE -- FUTURE_STANDALONE texas-hill-country."),
    ("San Marcos", "OUTSIDE -- FUTURE_STANDALONE san-marcos-new-braunfels-tx."),
])

HILL_COUNTRY_RULING = OrderedDict([
    ("classification", "The metro-continuous north / north-west edge -- La Cantera, Six Flags / The Rim / Leon Springs "
                       "(78256 / 78257 / 78255), Stone Oak and Cibolo Canyons (78258-78261) and Bulverde on US-281 "
                       "(78163, FRINGE) -- is admitted; Boerne / Fair Oaks Ranch and the destination Hill Country "
                       "(Comfort, Kerrville, Bandera, Fredericksburg) are OUTSIDE; New Braunfels / Gruene / Canyon Lake "
                       "are OUTSIDE."),
    ("a_marketing_phrase_admits_nothing", "'San Antonio Hill Country', 'Texas Hill Country', 'North San Antonio', "
                                          "'Greater San Antonio', 'New Braunfels / San Antonio', 'Boerne / San "
                                          "Antonio' and 'La Cantera / Hill Country' are marketing. The property's own "
                                          "postal code decides."),
    ("actual_location", "Decided by the property's own postal code on its own page."),
    ("drive_market_relationship", "La Cantera, The Rim, Stone Oak and Bulverde are San Antonio suburbs whose visitors "
                                  "are San Antonio-bound; Boerne, Comfort, Kerrville, Bandera, Fredericksburg, Gruene "
                                  "and Canyon Lake are destinations a traveller drives TO."),
    ("traveller_intent", "Theme parks, golf resorts, the Shops at La Cantera and the Medical Center are San Antonio "
                         "intent; Main Street Boerne, the Guadalupe and Comal rivers, Schlitterbahn and the wine road "
                         "are Hill Country / New Braunfels intent."),
    ("metro_continuity", "Continuous suburban development runs out I-10 to Leon Springs and the Dominion, up US-281 "
                         "through Stone Oak and Timberwood Park into Bulverde, and up I-35 through Live Oak, Selma and "
                         "Schertz; it thins past Fair Oaks Ranch on I-10, past Bulverde on US-281, at the Comal county "
                         "line on I-35 and past Loop 1604 to the south and west."),
    ("corridor_support", "Every admitted edge code is in a named corridor (six-flags-rim, stone-oak, bulverde, "
                         "selma-schertz) so its count is visible and a founder can move it on the record."),
    ("preserved_for", "FUTURE_STANDALONE texas-hill-country (Boerne, Fair Oaks Ranch, Comfort, Kerrville, Bandera, "
                      "Fredericksburg) and san-marcos-new-braunfels-tx (New Braunfels, Gruene, Canyon Lake, Seguin, San "
                      "Marcos)."),
])

STRUCTURE_TEST = OrderedDict([
    ("A. Is San Antonio one market, or several?",
     "ONE market, san-antonio-tx, covering the contiguous San Antonio metro inside and along Loop 1604 -- from Helotes "
     "and Six Flags to Converse and Schertz, and from Bulverde and Stone Oak to Brooks and the Missions. One "
     "commercial airport (SAT), one I-10 / I-35 / I-37 / I-410 / Loop 1604 / US-281 / US-90 road system, one VIA. The "
     "rural gaps toward New Braunfels, Seguin, Boerne, Castroville and Floresville are where that coherence stops."),
    ("B. The City of San Antonio is NOT the market -- and 'San Antonio' places nothing",
     "Live Oak, Universal City, Selma, Schertz, Cibolo, Converse, Leon Valley, Helotes and Bulverde are admitted by "
     "their own codes; the chains' 'San Antonio' prefix is on hotels from Seguin to Boerne."),
    ("C. SAT", "The airport owns its postal code (78216) and its lodging system -- its own CORE corridor with the "
               "Broadway / NE Loop 410 side (78217)."),
    ("D. River Walk / Alamo / Convention Center", "NO CORRIDOR of their own -- 78205, overlays of downtown. The River "
                                                  "Walk's reaches run through three corridors."),
    ("E. Medical Center", "Its own CORE corridor (78229 / 78240 / 78230 / 78201)."),
    ("F. La Cantera vs Six Flags", "Two corridors: La Cantera / UTSA (78256 / 78249) and Six Flags / The Rim / Leon "
                                   "Springs (78257 / 78255)."),
    ("G. Lackland / Fort Sam / Randolph", "The bases' own codes (78236 / 78234 / 78150) are covered by their "
                                          "corridors, but on-base lodging is MILITARY_RESTRICTED and never admitted."),
    ("H. Austin", "OUTSIDE -- LIVE austin-tx (786 / 787)."),
    ("I. New Braunfels / San Marcos / Seguin", "OUTSIDE -- FUTURE_STANDALONE san-marcos-new-braunfels-tx."),
    ("J. Hill Country (incl. Boerne)", "OUTSIDE -- FUTURE_STANDALONE texas-hill-country."),
    ("K. Corpus Christi", "OUTSIDE -- FUTURE_STANDALONE corpus-christi-tx."),
    ("L. Castroville / the rural ring", "OUTSIDE after careful evaluation."),
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
     "A property that sells both hotel rooms and residences is admitted ONLY as the hotel premises. San Antonio's "
     "specific exposures: the downtown River Walk condo towers and short-term lofts, the serviced-apartment and "
     "short-stay operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Lark, Wanderjaunt), the timeshare / "
     "vacation-club resorts and villas (Hill Country Villas, the Wyndham / WorldMark / Holiday Inn Club Vacations / "
     "Hilton Grand Vacations / Diamond inventory, the Villas at the Hill Country resorts) and the Airbnb / Vrbo "
     "inventory."),
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
    ("military_lodging",
     "On-base lodging (Air Force Inns, IHG Army Hotels on post, Navy Lodges, TLFs, visiting quarters, Fisher "
     "Houses) is MILITARY_RESTRICTED: restricted eligibility, on-base, the ordinary public-hotel contract not "
     "satisfied. Never admitted. A public commercial hotel outside the gate is an ordinary hotel."),
])

SHARED_POSTAL_CODES = OrderedDict([
    ("78205", ["Downtown", "River Walk", "The Alamo", "Convention Center", "Hemisfair"]),
    ("78209", ["City of San Antonio", "Alamo Heights", "Terrell Hills"]),
    ("78239", ["City of San Antonio", "Windcrest"]),
    ("78233", ["Live Oak", "City of San Antonio"]),
    ("78154", ["Selma", "Schertz", "City of San Antonio"]),
    ("78108", ["Cibolo", "Schertz"]),
    ("78238", ["Leon Valley", "City of San Antonio"]),
    ("78201", ["City of San Antonio", "Balcones Heights"]),
    ("78213", ["City of San Antonio", "Castle Hills"]),
    ("78232", ["City of San Antonio", "Hollywood Park"]),
    ("78231", ["City of San Antonio", "Shavano Park"]),
    ("78219", ["City of San Antonio", "Kirby"]),
])

FUTURE_MARKETS = OrderedDict([
    ("san-marcos-new-braunfels-tx", "San Marcos / New Braunfels / Gruene / Canyon Lake / Seguin -- the I-35 "
                                    "river-tubing, outlet and university destination between San Antonio and Austin."),
    ("texas-hill-country", "Boerne / Comfort / Kerrville / Bandera / Fredericksburg / Wimberley / Johnson City -- the "
                           "destination Hill Country a traveller drives TO."),
    ("corpus-christi-tx", "Corpus Christi / the Coastal Bend -- 140 miles south-east on I-37."),
    ("killeen-temple-tx", "Killeen / Temple / Belton -- north of Austin."),
    ("waco-tx", "Waco -- north of Austin."),
    ("college-station-tx", "Bryan / College Station -- Texas A&M's own market."),
])

#: Markets that are ALREADY LIVE. Austin owns the Texas postal codes north-east of this market; every other live
#: market's exposure is a shared chain NAME only.
EXISTING_LIVE_MARKETS = OrderedDict([
    ("austin-tx", "Austin / Central Texas, live as production market #38 (deploy 6abf3e749cc359701298718d) -- the "
                  "CURRENT LIVE market at this order's authoring time, and the only live market that owns Texas "
                  "postal codes (786 / 787, 67 admitted codes). No code it admits is admitted here; the boundary "
                  "audit counts every Austin node this market's lanes see."),
    ("phoenix-az", "Phoenix, live -- shares chain names but no postal code."),
])

#: A shared postal code whose OTHER town is refused. None in this market at authoring time: every admitted code's
#: towns are admitted together.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "san antonio,": "san antonio", "san antonio tx": "san antonio", "san antonio, tx": "san antonio",
    "sa": "san antonio", "s antonio": "san antonio", "san antonio texas": "san antonio",
    "live oak,": "live oak", "universal city,": "universal city", "universal cty": "universal city",
    "selma,": "selma", "schertz,": "schertz", "cibolo,": "cibolo", "converse,": "converse",
    "leon valley,": "leon valley", "helotes,": "helotes", "bulverde,": "bulverde", "windcrest,": "windcrest",
    "alamo heights,": "alamo heights", "castle hills,": "castle hills", "balcones heights,": "balcones heights",
    "balcones hts": "balcones heights", "shavano park,": "shavano park", "hollywood park,": "hollywood park",
    "kirby,": "kirby", "terrell hills,": "terrell hills", "olmos park,": "olmos park", "garden ridge,": "garden ridge",
    "jbsa lackland": "jbsa-lackland", "lackland afb": "jbsa-lackland", "fort sam houston": "jbsa-fort sam houston",
    "ft sam houston": "jbsa-fort sam houston", "randolph afb": "jbsa-randolph", "jbsa randolph": "jbsa-randolph",
}

STRUCTURE_NOTE_ZIPS = OrderedDict([
    ("78205", "Downtown / River Walk / Alamo / Convention Center -- one postal code, never split."),
    ("78215", "The Pearl / River North -- the Museum Reach of the River Walk."),
    ("78216", "SAT -- the airport owns its code."),
    ("78229", "The South Texas Medical Center."),
    ("78256", "La Cantera."),
    ("78257", "Six Flags Fiesta Texas / The Rim."),
    ("78245", "SeaWorld San Antonio."),
    ("78236", "JBSA-Lackland -- on-base lodging is MILITARY_RESTRICTED."),
])


def _live_austin_postal_codes():
    """Every postal code the LIVE Austin market's own registered document admits (read only)."""
    if not os.path.exists(LIVE_AUSTIN_MARKET):
        return set()
    with open(LIVE_AUSTIN_MARKET, encoding="utf-8") as fh:
        doc = json.load(fh)
    return {z for c in doc.get("corridors", []) for z in c.get("included_postal_codes", [])}


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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder San Antonio" % name),
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
        raise SystemExit("admitted postal codes outside the San Antonio prefixes: %s" % stray)
    austin_codes = _live_austin_postal_codes()
    live_overlap = sorted(austin_codes & set(seen_zip))
    if live_overlap:
        raise SystemExit("admitted postal codes the LIVE austin-tx market already admits: %s" % live_overlap)
    military_unclaimed = [z for z in MILITARY_POSTAL_CODES if z not in seen_zip]
    if military_unclaimed:
        raise SystemExit("military postal codes claimed by no corridor: %s" % military_unclaimed)

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)), ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius), ("state_code", "TX"),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "San Antonio / Greater San Antonio River Walk, convention, military, medical, theme-park, "
                        "resort, airport and Hill Country gateway lodging market (PetTripFinder discovery scope)"),
        ("state", "TX"),
        ("states", ["TX"]),
        ("country", "US"),
        ("market_center", {"lat": 29.42, "lng": -98.49}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches north past New Braunfels and San Marcos, west "
             "past Kerrville, Bandera and Castroville, south past Pleasanton and east past Seguin, so that " +
             WORK_ORDER + " classifies those properties on evidence instead of being blind to them. Admission is "
             "decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership is decided by "
         "the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". San Antonio / Greater San Antonio is ONE market: fourteen CORE corridors (downtown / River "
         "Walk, Pearl / Broadway, Southtown, SAT, the Medical Center, North Central, Stone Oak, Northwest / La "
         "Cantera, Six Flags / The Rim, SeaWorld / Westover Hills, Lackland / West, the East Side, the South Side and "
         "the Northeast), three STRONG CORRIDORS (Live Oak / Universal City, Selma / Schertz / Cibolo, Leon Valley / "
         "Helotes) and two FRINGE corridors (Converse, Bulverde). AUSTIN is live; NEW BRAUNFELS / SAN MARCOS / "
         "SEGUIN, the destination HILL COUNTRY (incl. Boerne) and CORPUS CHRISTI are refused as future standalone "
         "markets; Castroville and the rural ring are refused by name. On-base military lodging is never admitted."),
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
        ("market_name", "San Antonio, Texas"),
        ("market_slug", MARKET_ID),
        ("state_name", "Texas"),
        ("state_code", "TX"),
        ("primary_state_code", "TX"),
        ("states", ["TX"]),
        ("primary_city", "San Antonio"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in San Antonio & the River Walk | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater San Antonio -- downtown and the River Walk, the Pearl, "
         "Southtown, the airport, the Medical Center, Stone Oak, La Cantera, Six Flags, SeaWorld, Lackland, Live Oak, "
         "Schertz and Leon Valley -- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "San Antonio"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page or its brand's own property card "
         "states it, joined to the corridor registry. A San Antonio / Greater San Antonio River Walk, convention, "
         "military, medical, theme-park, resort, airport and Hill Country gateway travel market -- the contiguous "
         "metro from Helotes and Six Flags to Converse and Schertz, and from Bulverde and Stone Oak to Brooks and the "
         "Missions. Not 'South Texas': Austin is its own live market; New Braunfels / San Marcos / Seguin, the "
         "destination Hill Country (Boerne, Kerrville, Bandera, Fredericksburg) and Corpus Christi are future "
         "standalone markets; Castroville and the rural ring are refused. Nothing else admits a property: not a "
         "brand's 'San Antonio' or 'Hill Country' marketing name, not a map pin, not a vacation-rental listing, not a "
         "competitor directory's city label. On-base military lodging is never admitted."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). The postal city 'SAN "
         "ANTONIO' spans fourteen corridors and places nothing by itself. Shared codes are covered whole: 78205 by "
         "downtown, the River Walk, the Alamo and the Convention Center; 78233 by Live Oak and San Antonio; 78154 by "
         "Selma, Schertz and San Antonio; 78108 by Cibolo and Schertz; 78238 by Leon Valley and San Antonio. The River "
         "Walk, the Alamo, the Convention Center, La Cantera, The Rim, SeaWorld and the Lackland gate are overlays."),
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
        ("phase", "2 + 3 + 4 + 5 + 6 -- San Antonio / Greater San Antonio travel-market geography, traveller-market "
                  "logic, the New Braunfels / Hill Country boundary, the military-lodging boundary and the resort / "
                  "condo / vacation-ownership safety rule"),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED. The market document is written to markets/proposed/san-antonio-tx.json. This "
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
                     "contract NOT satisfied. A public commercial hotel outside the gate is an ordinary hotel."),
            ("military_postal_codes", MILITARY_POSTAL_CODES),
            ("nonpublic_names", NONPUBLIC_NAMES),
        ])),
        ("pet_travel_relevance",
         "San Antonio was selected as a high-value PetTripFinder market for its River Walk / Alamo tourism, regional "
         "road trips, military-family travel, business and convention demand, extended-stay demand, theme-park "
         "travel, resort demand, airport traffic and Hill Country gateway traffic. That lowers NO evidence standard: "
         "pet acceptance is never inferred from San Antonio's reputation. It shapes only the CENSUS: every tourist, "
         "convention, military, medical, theme-park, resort, extended-stay, airport and road-trip lodging cluster is "
         "covered by an admitting corridor."),
        ("the_san_antonio_name_trap",
         "The chains put 'San Antonio' on hotels from Seguin to Boerne and New Braunfels, 'San Antonio Hill Country' on "
         "resorts in 78251, 78256, 78261 and Boerne, and 'Riverwalk' on hotels in 78204, 78205 and 78215. A "
         "property's own postal code, street and brand property code decide what and where it is; none of those "
         "words decides anything."),
        ("notable_postal_codes", STRUCTURE_NOTE_ZIPS),
        ("demand_drivers", OrderedDict([
            ("_rule", "A demand driver informs a corridor's description and its publication priority. It NEVER "
                      "alters an exact premises identity and never admits a property."),
            ("San Antonio International Airport (SAT)", "its own corridor sat-airport (78216 / 78217)."),
            ("River Walk / The Alamo / Convention Center / Hemisfair", "downtown-river-walk (78205) -- overlays."),
            ("The Pearl / Museum Reach", "pearl-broadway (78215) -- overlay."),
            ("South Texas Medical Center / UT Health", "medical-center (78229 / 78240)."),
            ("JBSA-Lackland (basic-training graduations)", "lackland-west (78227 / 78242 / 78236) -- public hotels "
                                                            "outside the gate only."),
            ("JBSA-Fort Sam Houston / BAMC", "east-side (78208 / 78234) -- public hotels outside the gate only."),
            ("JBSA-Randolph", "live-oak-universal-city (78148 / 78150) -- public hotels outside the gate only."),
            ("SeaWorld San Antonio / Aquatica", "seaworld-westover-hills (78245) -- overlay."),
            ("Six Flags Fiesta Texas / The Rim", "six-flags-rim (78257) -- overlay."),
            ("La Cantera / UTSA", "northwest-la-cantera (78256 / 78249) -- overlays."),
            ("Frost Bank Center / Freeman Coliseum / Stock Show", "east-side (78219) -- overlay."),
            ("San Antonio Missions (UNESCO)", "south-side / southtown -- overlay."),
            ("TPC San Antonio / JW Marriott Hill Country", "stone-oak (78261) -- overlay."),
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
        ("live_austin_postal_codes_checked", len(austin_codes)),
        ("no_live_market_postal_code_admitted", not live_overlap),
        ("first_texas_market", False),
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
        return "OUTSIDE", None, "South Texas postal code %r is claimed by no corridor" % z
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
