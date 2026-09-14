"""PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 -- Phase 2 + 3: the Richmond travel market and its corridors.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Richmond, Virginia traveller lodging market -- a MULTI-CORE capital,
medical, interstate, airport and suburban-business market, not Richmond's city
limits and not the whole Richmond MSA -- stated as an explicit four-way rule
(CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is admitted, so no
property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page
states it, joined to the corridor registry below. The registry is a POSTAL-CODE
PARTITION: every admitted lodging ZIP is claimed by exactly one corridor, so a
property's corridor is a lookup and never a judgement. A brand's marketing name
("Richmond Airport", "Richmond West/Short Pump", "Richmond South", "Richmond
Innsbrook") never admits and never places a property: a "Richmond Airport" hotel
whose own page states Sandston 23150 is an airport hotel, a "Richmond North" hotel
whose own page states Glen Allen 23059 is an I-95 North hotel, and a "Richmond"
hotel whose own page states Colonial Heights 23834 is OUTSIDE.

HENRICO / CHESTERFIELD MAILING NAMES
------------------------------------
Most of the West End, Short Pump, Innsbrook and the airport sit in Henrico County
and most of Midlothian and the I-95 South corridor sit in Chesterfield County,
and their mail is addressed "Richmond", "Henrico", "Glen Allen", "Sandston" or
"North Chesterfield" interchangeably. The postal code decides; the mailing name is
never read as a municipality boundary.

THE FOUR CLASSES
----------------
CORE       Downtown / Shockoe / Riverfront / VCU Medical Center; VCU Monroe Park /
           The Fan / Museum District; the West End (Willow Lawn, Glenside, Parham,
           Regency, Tuckahoe); Short Pump / Gaskins; Innsbrook / Glen Allen; RIC
           Airport / Sandston / Henrico I-64 East; I-95 North (Chamberlayne, Parham
           Road, Virginia Center); I-95 South (Jefferson Davis Highway, Chippenham,
           Bells Road); Midlothian / Bon Air / Chesterfield.
CORRIDOR   Mechanicsville; Ashland; Chester.
FRINGE     none admitted (see the adjudications below).
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision.

PETERSBURG / COLONIAL HEIGHTS ADJUDICATION
------------------------------------------
Petersburg, Colonial Heights, Hopewell, Prince George and Fort Gregg-Adams form their
own I-95 / I-295 / US-460 "Tri-Cities" lodging cluster twenty to thirty miles south of
downtown, anchored on the army post, Virginia State University and Southpark Mall,
with its own search intent. They are PRESERVED for a future petersburg-tri-cities-va
market and are OUTSIDE here. Chester (23831 / 23836), whose I-95 exit 61 / Route 10
hotels serve the Richmond south side and the Chesterfield industrial corridor, is
admitted as a CORRIDOR.

Outputs:
  scripts/pettripfinder/discovery/config/richmond_va.json
  launch_packages/pettripfinder/markets/proposed/richmond-va.json
  launch_packages/pettripfinder/markets/reports/richmond_va_geography_001.json
  launch_packages/pettripfinder/markets/reports/richmond_va_corridor_registry_001.json
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

WORK_ORDER = "PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "richmond-va"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "richmond_va.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "richmond-va.json")
REPORT_OUT = os.path.join(REPORTS, "richmond_va_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "richmond_va_corridor_registry_001.json")

#: The future standalone market every Petersburg / Colonial Heights / Hopewell property is preserved for.
FUTURE_SUBMARKET = "petersburg-tri-cities-va"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown", "Downtown Richmond / Shockoe / Riverfront / VCU Medical Center", "Downtown & Shockoe",
     "CORE", "richmond",
     ["23219", "23218", "23223", "23298", "23241", "23261"],
     "Downtown Richmond: the Broad Street and Franklin Street hotel core, the Greater Richmond Convention "
     "Center, Capitol Square, Shockoe Slip and Shockoe Bottom, the Canal Walk and Riverfront, VCU Medical "
     "Center (MCV campus) and Church Hill, with the downtown post-office box codes."),
    ("vcu-fan-museum-district", "VCU Monroe Park / The Fan / Museum District", "VCU, The Fan & Museum District",
     "CORE", "richmond",
     ["23220", "23221", "23284"],
     "West of downtown: Jackson Ward and the Arts District, VCU's Monroe Park campus, the Fan, the Museum "
     "District and Carytown."),
    ("west-end", "West End / Willow Lawn / Glenside / Parham / Regency", "West End", "CORE", "richmond",
     ["23226", "23229", "23230", "23294", "23238", "23288", "23173"],
     "Richmond's West End in the city and Henrico County: Scott's Addition and Willow Lawn (23230), the "
     "Glenside and Dickens Road / Emerywood hotel cluster at I-64 exit 183 and West Broad Street (23294), "
     "Parham Road and Regency (23229), Tuckahoe and River Road (23226, 23238) and the University of Richmond."),
    ("short-pump", "Short Pump / Gaskins / West Broad Street", "Short Pump", "CORE", "glen allen",
     ["23233"],
     "Short Pump Town Center and West Broad Village, the West Broad Street and I-64 exit 178 (Gaskins Road / "
     "Broad Street) hotel cluster and the Three Chopt corridor."),
    ("innsbrook-glen-allen", "Innsbrook / Glen Allen", "Innsbrook & Glen Allen", "CORE", "glen allen",
     ["23060", "23058"],
     "The Innsbrook office park (Cox Road, Dominion Boulevard, Innslake Drive), Mayland and Sadler Roads, "
     "Staples Mill north and the Glen Allen business district along I-295 / I-64."),
    ("ric-airport-sandston", "RIC Airport / Sandston / Henrico I-64 East", "RIC Airport & Sandston", "CORE",
     "sandston",
     ["23150", "23250", "23231", "23075"],
     "Richmond International Airport (RIC) and the airport hotel cluster on Williamsburg Road, Airport Drive, "
     "International Center Drive and Laburnum Avenue, Sandston, Highland Springs and eastern Henrico along "
     "I-64 and I-295."),
    ("i-95-north", "I-95 North / Chamberlayne / Parham Road / Virginia Center", "I-95 North", "CORE", "richmond",
     ["23222", "23227", "23228", "23059"],
     "North Richmond and northern Henrico along I-95 and US-1: Chamberlayne Avenue and Brook Road, the I-95 "
     "exit 83 Parham Road cluster, Staples Mill Road and Lakeside, and Virginia Center / Brook Road north "
     "(I-95 exit 84 / 86) in Glen Allen."),
    ("i-95-south", "I-95 South / Richmond South / Jefferson Davis Highway / Chippenham", "I-95 South", "CORE",
     "richmond",
     ["23224", "23225", "23234", "23237"],
     "South Richmond and northern Chesterfield along I-95 and US-1: Manchester, Jefferson Davis Highway, "
     "Bells Road and Commerce Road, the Chippenham Parkway and Willis Road (I-95 exit 64) clusters and "
     "Forest Hill / Westover Hills."),
    ("midlothian-chesterfield", "Midlothian / Bon Air / Chesterfield", "Midlothian & Chesterfield", "CORE",
     "midlothian",
     ["23112", "23113", "23114", "23235", "23236", "23832", "23120"],
     "Chesterfield County west of I-95: Midlothian Turnpike and Chesterfield Towne Center, Bon Air and "
     "Huguenot Road, Robious Road, Hull Street Road and Commonwealth Centre, Brandermill and Moseley."),
    ("mechanicsville", "Mechanicsville / Atlee / US-360", "Mechanicsville", "CORRIDOR", "mechanicsville",
     ["23111", "23116"],
     "Mechanicsville in Hanover County on US-360 and I-295, with Atlee and the Cold Harbor Road corridor."),
    ("ashland", "Ashland / I-95 Exit 92", "Ashland", "CORRIDOR", "ashland",
     ["23005"],
     "The Town of Ashland and the I-95 exit 92 (Route 54) and exit 89 hotel clusters, fifteen miles north "
     "of downtown."),
    ("chester", "Chester / I-95 Exit 61 / Route 10", "Chester", "CORRIDOR", "chester",
     ["23831", "23836"],
     "Chester in Chesterfield County: Route 10 (West Hundred Road), the I-95 exit 61 and I-295 hotel "
     "clusters and the Ruffin Mill / Walthall industrial corridor."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. None in this market.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "richmond va": "richmond", "henrico va": "henrico", "n chesterfield": "north chesterfield",
    "no chesterfield": "north chesterfield", "north chesterfield va": "north chesterfield",
    "glen allen va": "glen allen", "sandston va": "sandston", "midlothian va": "midlothian",
    "chesterfield va": "chesterfield", "chester va": "chester", "ashland va": "ashland",
    "mechanicsville va": "mechanicsville", "colonial hts": "colonial heights", "s chesterfield": "south chesterfield",
    "short pump": "glen allen", "highland spgs": "highland springs",
}

TRI_CITIES_WHY = ("Petersburg / Colonial Heights / Hopewell / Prince George / Fort Gregg-Adams: the Tri-Cities I-95 / "
                  "I-295 / US-460 lodging cluster 20-30 miles south of downtown Richmond, anchored on the army post, "
                  "Virginia State University and Southpark Mall, with its own search intent; PRESERVED for the future "
                  "%s market, evaluated and refused here." % FUTURE_SUBMARKET)

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Petersburg / Colonial Heights / South Chesterfield / Hopewell / Prince George / Fort Gregg-Adams / Ettrick",
     "VA", ["23803", "23804", "23805", "23806", "23834", "23860", "23875", "23801", "23842", "23841"],
     TRI_CITIES_WHY),
    ("Chesterfield south (Matoaca / Winterpock)", "VA", ["23838"],
     "Rural southern Chesterfield County between Chester and Petersburg with no hotel core of its own; "
     "evaluated and refused."),
    ("Powhatan", "VA", ["23139"],
     "Powhatan Courthouse on US-60 / VA-288, 25 miles west: a rural county seat with no hotel core that "
     "Richmond travellers sleep in; evaluated and refused."),
    ("Goochland / Oilville / Rockville / Manakin-Sabot / Maidens / Crozier", "VA",
     ["23063", "23129", "23146", "23103", "23102", "23038"],
     "Goochland County and western Hanover along I-64 west of Short Pump: rural, with no traveller lodging "
     "core; evaluated and refused."),
    ("Hanover Courthouse / Beaverdam / Montpelier / Doswell (Kings Dominion) / Ruther Glen", "VA",
     ["23069", "23015", "23192", "23047", "22546"],
     "Hanover County north of Ashland: Hanover Courthouse and the rural county, and the Doswell / Kings Dominion "
     "theme-park and I-95 exit 98-104 cluster with its own destination intent; evaluated and refused."),
    ("New Kent / Quinton / Providence Forge / West Point", "VA", ["23124", "23140", "23141", "23181", "23089"],
     "New Kent County along I-64 east of Bottoms Bridge toward Williamsburg; evaluated and refused."),
    ("Amelia / Dinwiddie rural / Charles City / Surry", "VA", ["23002", "23030", "23883"],
     "Rural counties beyond the metro edge; evaluated and refused."),
    ("Williamsburg / Jamestown / Yorktown / Toano", "VA", ["23185", "23187", "23188", "23168", "23690", "23692"],
     "The Historic Triangle, its own destination market; refused by name (order: do not absorb Williamsburg)."),
    ("Fredericksburg / Stafford / Spotsylvania", "VA", ["22401", "22405", "22406", "22407", "22408", "22553", "22554"],
     "The Fredericksburg I-95 market; refused by name (order: do not absorb Fredericksburg)."),
    ("Charlottesville / Albemarle", "VA", ["22901", "22902", "22903", "22911"],
     "Charlottesville, its own university and destination market; refused by name (order)."),
    ("Farmville", "VA", ["23901"], "Farmville, its own college-town market; refused by name (order)."),
    ("Tidewater (Newport News / Hampton / Norfolk / Virginia Beach / Chesapeake / Suffolk)", "VA",
     ["23601", "23602", "23606", "23666", "23669", "23502", "23510", "23451", "23452", "23320", "23434"],
     "The Hampton Roads market; refused by name (order: do not absorb far Tidewater inventory)."),
    ("Emporia / South Hill / Stony Creek (far I-95 / I-85)", "VA", ["23847", "23970", "23882"],
     "Far I-95 and I-85 lodging that merely markets 'Richmond'; refused (order)."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover refused neighbours so this order classifies them on evidence.
CELLS = [
    ("downtown", "Richmond", "Downtown / Shockoe / VCU Medical Center", 37.5400, -77.4330, 2200, True),
    ("vcu-fan-museum", "Richmond", "VCU Monroe Park / Fan / Museum District", 37.5500, -77.4700, 2500, True),
    ("west-end-willow-lawn", "Richmond", "Scott's Addition / Willow Lawn", 37.5750, -77.4950, 2500, True),
    ("west-end-glenside", "Henrico", "Glenside / Dickens Rd / West Broad", 37.6100, -77.5400, 3500, True),
    ("west-end-parham", "Henrico", "Parham / Regency / Tuckahoe", 37.5950, -77.5700, 3500, True),
    ("short-pump", "Glen Allen", "Short Pump / Gaskins", 37.6480, -77.6100, 4500, True),
    ("innsbrook", "Glen Allen", "Innsbrook", 37.6550, -77.5750, 3000, True),
    ("ric-airport", "Sandston", "RIC Airport / Sandston", 37.5150, -77.3300, 4500, True),
    ("henrico-i64-east", "Henrico", "Laburnum / Highland Springs", 37.5400, -77.3700, 3500, True),
    ("i-95-north", "Richmond", "Chamberlayne / Parham Road I-95", 37.6200, -77.4500, 4000, True),
    ("virginia-center", "Glen Allen", "Virginia Center / Brook Road", 37.6800, -77.4600, 3500, True),
    ("i-95-south", "North Chesterfield", "Jefferson Davis Hwy / Chippenham", 37.4700, -77.4500, 5000, True),
    ("willis-road", "North Chesterfield", "Willis Road / I-95 exit 64", 37.4150, -77.4350, 3000, True),
    ("midlothian", "Midlothian", "Midlothian Turnpike / Chesterfield Towne Center", 37.5050, -77.6000, 6000, True),
    ("hull-street", "Midlothian", "Hull Street / Commonwealth Centre", 37.4350, -77.6400, 5000, True),
    ("mechanicsville", "Mechanicsville", "Mechanicsville", 37.6100, -77.3600, 5000, True),
    ("ashland", "Ashland", "Ashland / I-95 exit 92", 37.7500, -77.4650, 4000, True),
    ("chester", "Chester", "Chester / I-95 exit 61", 37.3600, -77.4200, 5000, True),
    # observation only -- the preserved Tri-Cities market and refused neighbours
    ("obs-colonial-heights", "Colonial Heights", "Colonial Heights / Southpark -- OBSERVATION ONLY", 37.2600, -77.3950, 5000, False),
    ("obs-petersburg", "Petersburg", "Petersburg -- OBSERVATION ONLY", 37.2150, -77.4000, 6000, False),
    ("obs-hopewell", "Hopewell", "Hopewell / Prince George -- OBSERVATION ONLY", 37.2900, -77.2900, 6000, False),
    ("obs-doswell", "Doswell", "Doswell / Kings Dominion -- OBSERVATION ONLY", 37.8400, -77.4500, 5000, False),
    ("obs-powhatan", "Powhatan", "Powhatan -- OBSERVATION ONLY", 37.5400, -77.9200, 6000, False),
    ("obs-goochland", "Goochland", "Goochland / Oilville -- OBSERVATION ONLY", 37.6800, -77.8000, 8000, False),
    ("obs-new-kent", "Quinton", "New Kent / Bottoms Bridge -- OBSERVATION ONLY", 37.5300, -77.1200, 6000, False),
]

BOUNDS = {
    "min_lat": 37.10,
    "max_lat": 37.92,
    "min_lng": -78.05,
    "max_lng": -77.05,
}

#: Reporting overlay only (never membership): the areas the order names.
COVERAGE_AREAS = [
    ("Downtown Richmond", 37.5410, -77.4360, 1.3),
    ("Shockoe / Riverfront", 37.5320, -77.4250, 1.0),
    ("VCU Medical Center", 37.5400, -77.4300, 0.6),
    ("VCU Monroe Park", 37.5480, -77.4530, 0.9),
    ("Museum District / Fan", 37.5550, -77.4780, 1.8),
    ("Scott's Addition / Willow Lawn", 37.5720, -77.4900, 1.8),
    ("West End", 37.6050, -77.5500, 6.0),
    ("Short Pump", 37.6500, -77.6150, 4.0),
    ("Innsbrook", 37.6550, -77.5750, 2.5),
    ("Glen Allen", 37.6650, -77.5100, 5.0),
    ("RIC Airport", 37.5080, -77.3200, 2.5),
    ("Sandston", 37.5230, -77.3150, 3.5),
    ("Henrico / I-64 East", 37.5450, -77.3750, 4.0),
    ("I-95 North / Chamberlayne", 37.6150, -77.4450, 4.0),
    ("Virginia Center", 37.6850, -77.4550, 2.5),
    ("I-95 South / Richmond South", 37.4600, -77.4500, 5.0),
    ("Chesterfield", 37.4200, -77.5800, 8.0),
    ("Midlothian", 37.5050, -77.6200, 6.0),
    ("Bon Air", 37.5250, -77.5600, 2.5),
    ("Mechanicsville", 37.6100, -77.3550, 6.0),
    ("Ashland", 37.7550, -77.4650, 5.0),
    ("Chester", 37.3550, -77.4200, 6.0),
]


def build():
    corridors = []
    seen_zip = {}
    for order, (slug, name, area, klass, _muni, zips, desc) in enumerate(CORRIDORS, start=1):
        for z in zips:
            if z in seen_zip:
                raise SystemExit("postal code %s claimed by both %s and %s -- the corridor "
                                 "registry must be a partition" % (z, seen_zip[z], slug))
            seen_zip[z] = slug
        corridors.append(OrderedDict([
            ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
            ("market_id", MARKET_ID),
            ("name", name),
            ("slug", slug),
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Richmond" % name),
            ("meta_description",
             "Verified pet-friendly hotels in %s, with real pet fees and policies read from "
             "each hotel's own official website." % name),
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
            ("state_code", "VA"),
            ("geography_class", klass),
        ]))
    outside_zips = {z for _m, _s, zs, _w in OUTSIDE for z in zs}
    overlap = outside_zips & set(seen_zip)
    if overlap:
        raise SystemExit("postal codes both admitted and refused: %s" % sorted(overlap))

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)),
        ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
        ("state_code", "VA"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Richmond, VA multi-core capital, medical, interstate, airport and suburban-business lodging "
                        "market (PetTripFinder discovery scope)"),
        ("state", "VA"),
        ("states", ["VA"]),
        ("country", "US"),
        ("market_center", {"lat": 37.541, "lng": -77.436}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- south over "
             "Colonial Heights, Petersburg and Hopewell, north over Doswell, west over Powhatan and Goochland and east "
             "over New Kent -- so that " + WORK_ORDER + " classifies those properties on evidence instead of being "
             "blind to them. Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A multi-core travel market: nine CORE corridors (Downtown / Shockoe / VCU Medical Center, "
         "VCU Monroe Park / Fan / Museum District, West End, Short Pump, Innsbrook / Glen Allen, RIC Airport / "
         "Sandston / Henrico I-64 East, I-95 North, I-95 South, Midlothian / Chesterfield) and three CORRIDOR "
         "corridors (Mechanicsville, Ashland, Chester). Petersburg, Colonial Heights and Hopewell are OBSERVED and "
         "REFUSED, preserved for a future " + FUTURE_SUBMARKET + " market; Powhatan, Goochland, Hanover Courthouse, "
         "Doswell, New Kent, Williamsburg, Fredericksburg, Charlottesville, Farmville and Tidewater are named and "
         "REFUSED."),
        ("scope_disclosure",
         "%d bounded cells: %d admitting and %d observation-only." % (
             len(cells), sum(1 for c in cells if c["admitting"]),
             sum(1 for c in cells if not c["admitting"]))),
        ("explicit_hotel_admissions", OrderedDict([
            ("_what_this_is",
             "The explicit-hotel mechanism, so a single legitimate fringe property never becomes a reason "
             "to widen a municipality or a postal code. Empty at authoring time."),
            ("admissions", []),
        ])),
        ("cells", cells),
    ])

    shard = OrderedDict([
        ("schema", "ptf-market/1.1"),
        ("market_id", MARKET_ID),
        ("market_name", "Richmond, Virginia"),
        ("market_slug", MARKET_ID),
        ("state_name", "Virginia"),
        ("state_code", "VA"),
        ("primary_state_code", "VA"),
        ("states", ["VA"]),
        ("primary_city", "Richmond"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Richmond, Virginia | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Richmond -- downtown and VCU, the West End, Short Pump and Innsbrook, "
         "the RIC airport, the I-95 corridors, Midlothian and Chesterfield, Mechanicsville, Ashland and Chester -- "
         "with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Richmond"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A multi-core capital, medical, interstate, airport and suburban-business market -- "
         "not Richmond's city limits and not the Richmond MSA. Nothing else admits a property: not a brand's "
         "'Richmond Airport', 'Richmond South' or 'Richmond West' marketing name, not a map pin, not a "
         "short-term-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor. VCU Medical Center shares 23219 with downtown and "
         "Shockoe; Scott's Addition shares 23230 with Willow Lawn in the West End; Bon Air shares 23235 with "
         "Midlothian; Henrico I-64 East is folded into the airport corridor."),
        ("_census_membership_note",
         "Petersburg, Colonial Heights, Hopewell and Prince George are a separate Tri-Cities lodging market preserved "
         "for its own future market; Williamsburg, Fredericksburg, Charlottesville, Farmville and Tidewater are not "
         "absorbed. A property whose own page states one of their postal codes is OUTSIDE, however it is named. "
         "Ordinary apartment communities, corporate-housing portfolios, student housing, individual houses and "
         "apartments and Airbnb / Vrbo inventory are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    adjudications = OrderedDict([
        ("Colonial Heights", OrderedDict([
            ("decision", "C -- OUTSIDE, preserved for the future %s market" % FUTURE_SUBMARKET),
            ("why",
             "Colonial Heights' Southpark Boulevard and I-95 exit 53-54 hotels sit 20 miles south of downtown and "
             "sell Fort Gregg-Adams, Petersburg and Southpark Mall stays under their own search intent. Richmond "
             "traveller behaviour does not clearly support them: Chester's exit 61 cluster, eight miles nearer, "
             "already serves the Richmond south side. Admitting them would fold the Tri-Cities market into Richmond."),
        ])),
        ("Petersburg", OrderedDict([
            ("decision", "C -- OUTSIDE, preserved for the future %s market" % FUTURE_SUBMARKET),
            ("why", "An independent city with its own historic downtown, battlefield, Virginia State University and "
                    "I-95 / I-85 / US-460 lodging; a materially separate I-95 lodging market."),
        ])),
        ("Hopewell", OrderedDict([
            ("decision", "C -- OUTSIDE, preserved for the future %s market" % FUTURE_SUBMARKET),
            ("why", "An independent city on the James and Appomattox serving the Fort Gregg-Adams gate and its own "
                    "industrial base; lodges with Petersburg and Prince George, not Richmond."),
        ])),
        ("Chester", OrderedDict([
            ("decision", "B -- CORRIDOR (chester, 23831 / 23836)"),
            ("why", "Chesterfield County's Route 10 and I-95 exit 61 / I-295 hotels serve the Richmond south side, the "
                    "Chesterfield industrial corridor and Richmond-bound I-95 travellers 15 miles from downtown."),
        ])),
        ("Powhatan", OrderedDict([
            ("decision", "OUTSIDE"),
            ("why", "A rural county seat 25 miles west with no traveller hotel core."),
        ])),
        ("Goochland / Rockville", OrderedDict([
            ("decision", "OUTSIDE"),
            ("why", "Rural I-64 west of Short Pump (Oilville, Rockville, Goochland Courthouse) with no hotel core; a "
                    "single property there would be an explicit-hotel admission, never a widened postal code."),
        ])),
        ("Hanover (county)", OrderedDict([
            ("decision", "SPLIT -- Mechanicsville and Ashland admitted as CORRIDOR; Hanover Courthouse, Doswell and the "
                         "rural county OUTSIDE"),
            ("why", "Mechanicsville (US-360 / I-295) and Ashland (I-95 exit 92) are Richmond's northern interstate "
                    "lodging; Doswell's Kings Dominion cluster has its own theme-park destination intent."),
        ])),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 -- Richmond multi-core travel-market geography, fringe adjudications and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-14"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Richmond's turn in the serialized release "
         "queue against the then-current live parent."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "Richmond's lodging cores (downtown, Shockoe and VCU Medical Center; VCU Monroe Park, the Fan and the "
         "Museum District; the West End; Short Pump; Innsbrook / Glen Allen; the RIC airport and Sandston; the I-95 "
         "North and I-95 South corridors; Midlothian and Chesterfield) and the interstate corridors a Richmond "
         "traveller sleeps in by choice (Mechanicsville, Ashland, Chester)."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("fringe_adjudications", adjudications),
        ("evaluated_inclusions", OrderedDict([
            ("Downtown Richmond", "ADMITTED (CORE, downtown, 23219)."),
            ("Shockoe / Riverfront", "ADMITTED (CORE, downtown, 23219 / 23223) -- reported as an overlay."),
            ("VCU / Medical District", "ADMITTED -- VCU Medical Center (23219 / 23298) is inside downtown and VCU Monroe "
                                       "Park (23220 / 23284) inside vcu-fan-museum-district; reported as overlays."),
            ("Museum District / Fan", "ADMITTED (CORE, vcu-fan-museum-district, 23220 / 23221)."),
            ("Richmond West End", "ADMITTED (CORE, west-end, 23226 / 23229 / 23230 / 23294 / 23238)."),
            ("Short Pump", "ADMITTED (CORE, short-pump, 23233)."),
            ("Innsbrook", "ADMITTED (CORE, innsbrook-glen-allen, 23060)."),
            ("Richmond International Airport / RIC", "ADMITTED (CORE, ric-airport-sandston, 23150 / 23250 / 23231)."),
            ("Sandston", "ADMITTED (CORE, ric-airport-sandston, 23150)."),
            ("Henrico / I-64 East", "ADMITTED (CORE, folded into ric-airport-sandston: 23231 / 23075) -- too few hotels "
                                    "for a corridor of its own; reported as an overlay."),
            ("I-95 North / Chamberlayne", "ADMITTED (CORE, i-95-north, 23222 / 23227 / 23228 / 23059)."),
            ("I-95 South / Richmond South", "ADMITTED (CORE, i-95-south, 23224 / 23225 / 23234 / 23237)."),
            ("Chesterfield", "ADMITTED (CORE, midlothian-chesterfield, 23832 / 23236 / 23235)."),
            ("Midlothian", "ADMITTED (CORE, midlothian-chesterfield, 23112 / 23113 / 23114)."),
            ("Glen Allen", "ADMITTED -- Innsbrook's 23060 in innsbrook-glen-allen; Virginia Center's 23059 in i-95-north."),
            ("Ashland", "ADMITTED (CORRIDOR, ashland, 23005)."),
            ("Mechanicsville", "ADMITTED (CORRIDOR, mechanicsville, 23111 / 23116)."),
            ("Chester", "ADMITTED (CORRIDOR, chester, 23831 / 23836)."),
            ("Bon Air", "ADMITTED (CORE, midlothian-chesterfield, 23235) -- reported as an overlay."),
            ("Colonial Heights", "OUTSIDE -- preserved for the future %s market." % FUTURE_SUBMARKET),
            ("Petersburg", "OUTSIDE -- preserved for the future %s market." % FUTURE_SUBMARKET),
            ("Hopewell", "OUTSIDE -- preserved for the future %s market." % FUTURE_SUBMARKET),
            ("Powhatan", "OUTSIDE -- rural county seat with no hotel core."),
            ("Goochland", "OUTSIDE -- rural I-64 west with no hotel core."),
            ("Hanover", "SPLIT -- Mechanicsville and Ashland admitted; Hanover Courthouse and Doswell OUTSIDE."),
            ("Rockville", "OUTSIDE -- rural I-64 exit 173 with no hotel core."),
            ("Williamsburg / Charlottesville / Fredericksburg / Farmville / Tidewater / far I-95",
             "OUTSIDE -- refused by name (order)."),
        ])),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]),
            ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = "
         "5 verified pet-friendly hotels) is met. No thin corridor page is invented for SEO; every "
         "corridor is show_in_navigation/show_in_sitemap false until a registration order publishes it. "
         "VCU Medical Center shares 23219 with downtown, Scott's Addition shares 23230 with Willow Lawn, Bon Air shares "
         "23235 with Midlothian and Henrico I-64 East is folded into the airport corridor, so they cannot be separate "
         "pages under a postal-code partition; they are reported as overlays."),
        ("coverage_areas_are_a_reporting_overlay",
         "The order's named areas that share a postal code with another area are reported from the "
         "property's own stated street first and a nearest-anchor overlay on its pin second. The overlay "
         "decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("municipality_refusals", []),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Seven cells observe Colonial Heights, Petersburg, Hopewell, Doswell, Powhatan, Goochland and New Kent. "
         "They admit nothing."),
        ("non_hotel_rule",
         "The census admits hotels, motels, inns, boutique and historic hotels, extended-stay hotels and qualifying "
         "public lodging establishments operated as lodging businesses: bookable nightly rooms or suites sold to the "
         "public under one establishment name, with an official property page and an on-site hotel operation. It "
         "NEVER admits: ordinary apartment communities or individual apartments; corporate-housing and furnished-"
         "apartment portfolios; student housing; individual houses, historic homes or carriage houses rented whole; "
         "Airbnb / Vrbo-style listings; app-only apartment-hotel units without a front desk; private residences; "
         "military or university lodging closed to the public; and timeshare inventory unless the property "
         "independently qualifies as a hotel. A historic inn or bed and breakfast is admitted only when it operates "
         "as an inn with bookable rooms on its own premises and an official site. Campgrounds, RV parks and hostels-as-"
         "dormitories are NON_LODGING."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


def corridor_municipality():
    """slug -> the municipality the corridor principally sits in (name attachment only)."""
    return {slug: muni for slug, _n, _a, _k, muni, _z, _d in CORRIDORS}


def coverage_area(lat, lng, names=None):
    """The overlay area a coordinate reports under, or None. Reporting only."""
    if lat is None or lng is None:
        return None
    best = None
    for name, la, ln, r in COVERAGE_AREAS:
        if names is not None and name not in names:
            continue
        dy = (float(lat) - la) * 111.0
        dx = (float(lng) - ln) * 111.0 * math.cos(math.radians(la))
        d = math.hypot(dx, dy)
        if d <= r and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def route_overlay(corridor_slug, street, lat, lng):
    """The order's named area a census row reports under. Reporting only."""
    st = street or ""
    if corridor_slug == "downtown":
        area = coverage_area(lat, lng, ("VCU Medical Center", "Shockoe / Riverfront", "Downtown Richmond"))
        if re.search(r"\b(e|east)\s+(marshall|leigh|clay)\b", st, re.I):
            return "VCU Medical Center"
        return area or "Downtown Richmond"
    if corridor_slug == "vcu-fan-museum-district":
        area = coverage_area(lat, lng, ("VCU Monroe Park", "Museum District / Fan"))
        return area or "Museum District / Fan"
    if corridor_slug == "west-end":
        area = coverage_area(lat, lng, ("Scott's Addition / Willow Lawn",))
        return area or "West End"
    if corridor_slug == "innsbrook-glen-allen":
        area = coverage_area(lat, lng, ("Innsbrook",))
        return area or "Glen Allen"
    if corridor_slug == "ric-airport-sandston":
        area = coverage_area(lat, lng, ("RIC Airport", "Sandston", "Henrico / I-64 East"))
        return area or "RIC Airport / Sandston (other)"
    if corridor_slug == "i-95-north":
        area = coverage_area(lat, lng, ("Virginia Center",))
        return area or "I-95 North / Chamberlayne"
    if corridor_slug == "midlothian-chesterfield":
        area = coverage_area(lat, lng, ("Bon Air", "Midlothian"))
        return area or "Chesterfield"
    return {"short-pump": "Short Pump", "i-95-south": "I-95 South / Richmond South",
            "mechanicsville": "Mechanicsville", "ashland": "Ashland", "chester": "Chester"}.get(corridor_slug)


def normalize_municipality(city):
    muni = " ".join((city or "").lower().replace(".", " ").replace(",", " ").split())
    return MUNICIPALITY_SPELLINGS.get(muni, muni)


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    muni = normalize_municipality(city)
    return {"richmond": "Richmond", "henrico": "Henrico", "glen allen": "Glen Allen", "sandston": "Sandston",
            "midlothian": "Midlothian", "north chesterfield": "North Chesterfield", "chesterfield": "Chesterfield",
            "mechanicsville": "Mechanicsville", "ashland": "Ashland", "chester": "Chester",
            "highland springs": "Highland Springs"}.get(muni)


def is_future_submarket(postal, municipality=None):
    """True when a property belongs to the preserved Petersburg / Tri-Cities market."""
    z = (postal or "").strip()[:5]
    return z in OUTSIDE[0][2]


def classify_postal(postal, municipality):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and
    municipality. The one membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = normalize_municipality(municipality)
    for slug, _name, _area, klass, _m, zips, _desc in CORRIDORS:
        if z in zips:
            for rz, rmuni, why in MUNICIPALITY_REFUSALS:
                if rz == z and rmuni == muni:
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
                          (REGISTRY_OUT, OrderedDict([
                              ("schema", "ptf-corridor-registry/1.0"), ("work_order", WORK_ORDER),
                              ("market_id", MARKET_ID), ("corridors", corridors)]))):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, indent=1)
                fh.write("\n")
            print("WROTE", os.path.relpath(path, _DASH))
    print("corridors=%d  admitted_zips=%d  cells=%d (admitting %d, observation %d)" % (
        report["corridor_count"], report["admitted_postal_code_count"],
        report["cells_total"], report["cells_admitting"], report["cells_observation_only"]))
    print("by class:", json.dumps(report["corridor_count_by_class"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
