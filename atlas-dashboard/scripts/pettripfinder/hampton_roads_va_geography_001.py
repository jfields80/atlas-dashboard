"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- Phase 2 + 3 + 4: the Hampton Roads travel market, its cities and corridors.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Hampton Roads, Virginia traveller lodging market -- a LARGE MULTI-CORE
region of independent cities (Virginia Beach, Norfolk, Chesapeake, Portsmouth, Hampton,
Newport News, Suffolk) joined by the I-64 / I-264 / I-664 tunnels and bridges, with an
oceanfront resort strip, a downtown convention and cruise core, an airport, a naval
capital and two peninsula business districts. It is NOT one downtown-centred city and
NOT the Virginia Beach-Norfolk-Newport News MSA. The rule is stated as an explicit
four-way class (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is admitted,
so no property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page
states it, joined to the corridor registry below. The registry is a POSTAL-CODE
PARTITION: every admitted lodging ZIP is claimed by exactly one corridor, and every
corridor sits inside ONE independent city (or, for the FRINGE, one county town), so a
property's corridor AND its city are a lookup and never a judgement. A brand's
marketing name ("Norfolk Airport", "Virginia Beach Oceanfront", "Newport News /
Williamsburg", "Chesapeake / Norfolk") never admits and never places a property.

MUNICIPALITY SAFETY (PHASE 12)
------------------------------
Virginia's cities are independent cities: a Norfolk hotel is not in Virginia Beach and
a Hampton hotel is not in Newport News, whatever a brand calls them. The ZIP decides
the corridor, and the municipality the property's OWN page states is then checked
against the cities that corridor's ZIPs are mailed as (CITY_OF_CORRIDOR, applied in the
census helper). A stated municipality that contradicts the ZIP's city is a
GEOGRAPHY_HOLD -- one of the two first-party facts is wrong, and the ZIP alone never
decides which. The market stays one regional market; the city is preserved on every row.

THE FOUR CLASSES
----------------
CORE       Virginia Beach (Oceanfront; Town Center / Pembroke; Central & Bayside),
           Norfolk (Downtown / Waterside / Ghent; ORF Airport / Military Highway /
           Military Circle; Ocean View / Bayfront), Chesapeake (Greenbrier / Battlefield
           Blvd North; Great Bridge / Battlefield South / Deep Creek; Western Branch),
           Portsmouth, Hampton (Coliseum Central / Convention Center; Mercury Blvd East /
           Downtown / Phoebus), Newport News (City Center / Oyster Point / Midtown;
           I-64 / Jefferson Ave / Denbigh / PHF Airport).
CORRIDOR   Suffolk (Downtown / US-58 and Harbour View / North Suffolk).
FRINGE     Smithfield / Carrollton (Isle of Wight); Yorktown US-17 / Tabb / Grafton (York
           County south of the Colonial Parkway).
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision.

WILLIAMSBURG ADJUDICATION
-------------------------
Williamsburg, Jamestown, James City County, Busch Gardens / Kingsmill, Lightfoot and
Toano are the Historic Triangle -- a destination market with its own search intent --
and DEFAULT TO A FUTURE SEPARATE williamsburg-va MARKET. Historic Yorktown (23690: the
Riverwalk and battlefield village on the Colonial Parkway) lodges with that Historic
Triangle, and is preserved for the same future market. The US-17 / Victory Boulevard
hotels of Tabb and Grafton (23692 / 23693) sit on the Newport News / Hampton line and
serve the peninsula's business, NASA Langley and PHF airport travel: admitted as FRINGE.

MILITARY LODGING (PHASE 5)
--------------------------
Installation-only postal codes (Naval Station Norfolk 23511 / 23551, JEB Little Creek
23521, Fort Eustis 23604, Langley 23665, Naval Weapons Station Yorktown 23691, Norfolk
Naval Shipyard 23709) are OUTSIDE with the MILITARY_NONPUBLIC reason: Navy Gateway Inns
& Suites, IHG Army Hotels and Air Force Inns require installation access or military
eligibility and are not public lodging. Commercial hotels outside the fence that serve
military travellers are ordinary hotels and are admitted on their own ZIP. A named
military lodging row inside a mixed ZIP is refused by name in the census helper.

Outputs:
  scripts/pettripfinder/discovery/config/hampton_roads_va.json
  launch_packages/pettripfinder/markets/proposed/hampton-roads-va.json
  launch_packages/pettripfinder/markets/reports/hampton_roads_va_geography_001.json
  launch_packages/pettripfinder/markets/reports/hampton_roads_va_corridor_registry_001.json
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

WORK_ORDER = "PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hampton-roads-va"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "hampton_roads_va.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "hampton-roads-va.json")
REPORT_OUT = os.path.join(REPORTS, "hampton_roads_va_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "hampton_roads_va_corridor_registry_001.json")

#: The future standalone market every Williamsburg / Historic Triangle property is preserved for.
FUTURE_SUBMARKET = "williamsburg-va"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, city, postal codes, description)
CORRIDORS = [
    ("virginia-beach-oceanfront", "Virginia Beach Oceanfront", "Virginia Beach Oceanfront", "CORE", "virginia beach",
     ["23451", "23450"],
     "The Virginia Beach resort strip: Atlantic Avenue and Ocean Front from Rudee Inlet to the North End, the "
     "Boardwalk, the Virginia Beach Convention Center and the Laskin Road / Hilltop east corridor."),
    ("virginia-beach-town-center", "Virginia Beach Town Center / Pembroke / Newtown Road", "Virginia Beach Town Center",
     "CORE", "virginia beach",
     ["23462"],
     "Town Center of Virginia Beach, Pembroke and Independence Boulevard, the I-264 Newtown Road and Witchduck "
     "Road interchanges and the Virginia Beach Boulevard business district."),
    ("virginia-beach-central-bayside", "Virginia Beach Lynnhaven / Shore Drive / Kempsville / Princess Anne",
     "Virginia Beach Central & Bayside", "CORE", "virginia beach",
     ["23452", "23454", "23455", "23453", "23456", "23457", "23459", "23460", "23461", "23464", "23463"],
     "The rest of the city of Virginia Beach: Lynnhaven Mall and Lynnhaven Parkway, Great Neck and First Colonial, "
     "Shore Drive and the Chesapeake Bay beaches, Northampton Boulevard, Kempsville, Princess Anne, Oceana and "
     "Sandbridge."),
    ("norfolk-downtown", "Norfolk Downtown / Waterside / Ghent / ODU", "Norfolk Downtown", "CORE", "norfolk",
     ["23510", "23507", "23517", "23508", "23501", "23504", "23523"],
     "Downtown Norfolk: Waterside and the Elizabeth River waterfront, the cruise terminal, MacArthur Center, "
     "Granby Street and Freemason, Ghent, Old Dominion University and the Eastern Virginia Medical School district."),
    ("norfolk-airport-military-highway", "Norfolk International Airport (ORF) / Military Highway / Military Circle",
     "ORF Airport & Military Highway", "CORE", "norfolk",
     ["23502", "23518", "23513", "23505", "23509"],
     "Norfolk International Airport and the North Military Highway hotel cluster at I-64 / I-264, Military Circle "
     "and Newtown Road, Norview, Wards Corner and Ingleside."),
    ("norfolk-ocean-view", "Norfolk Ocean View / Bayfront", "Norfolk Ocean View", "CORE", "norfolk",
     ["23503"],
     "Norfolk's Chesapeake Bay shore: Ocean View Avenue, Willoughby Spit and the I-64 Hampton Roads Bridge-Tunnel "
     "approach."),
    ("chesapeake-greenbrier", "Chesapeake Greenbrier / Crossways / Battlefield Boulevard North",
     "Chesapeake Greenbrier", "CORE", "chesapeake",
     ["23320", "23325"],
     "Greenbrier Parkway, Crossways Boulevard and Greenbrier Mall at I-64 exit 289, the Battlefield Boulevard North "
     "interchange (exit 290) and Indian River."),
    ("chesapeake-great-bridge-south", "Chesapeake Great Bridge / Battlefield Boulevard South / Deep Creek",
     "Chesapeake Battlefield & Great Bridge", "CORE", "chesapeake",
     ["23322", "23323", "23324"],
     "Great Bridge and Battlefield Boulevard South, the Chesapeake Expressway, Deep Creek and Dominion Boulevard, "
     "South Military Highway and South Norfolk."),
    ("chesapeake-western-branch", "Chesapeake Western Branch / Chesapeake Square / I-664", "Chesapeake Western Branch",
     "CORE", "chesapeake",
     ["23321"],
     "Western Branch: Chesapeake Square, Taylor Road and Portsmouth Boulevard at I-664 / US-17."),
    ("portsmouth", "Portsmouth Downtown / Olde Towne / Churchland", "Portsmouth", "CORE", "portsmouth",
     ["23701", "23702", "23703", "23704", "23705", "23707", "23708"],
     "The city of Portsmouth: the Olde Towne waterfront and Harbor Center, High Street, Naval Medical Center "
     "Portsmouth's neighbourhood, Churchland and the Victory Boulevard / I-264 corridor."),
    ("hampton-coliseum-central", "Hampton Coliseum Central / Convention Center / Hampton Roads Center",
     "Hampton Coliseum & Convention Center", "CORE", "hampton",
     ["23666"],
     "Coliseum Central: the Hampton Coliseum and Hampton Roads Convention Center, Coliseum Drive, Mercury "
     "Boulevard West at I-64 exit 263, Hampton Roads Center Parkway and Big Bethel Road."),
    ("hampton-mercury-downtown", "Hampton Mercury Boulevard East / Downtown / Phoebus / Buckroe",
     "Hampton Downtown & Mercury Blvd East", "CORE", "hampton",
     ["23669", "23661", "23663", "23664", "23651", "23670", "23630"],
     "Downtown Hampton and the Settlers Landing waterfront, East Mercury Boulevard toward Fort Monroe, Phoebus, "
     "Buckroe Beach and the Hampton University district."),
    ("newport-news-city-center", "Newport News City Center / Oyster Point / Midtown", "Newport News City Center",
     "CORE", "newport news",
     ["23606", "23601", "23605", "23607"],
     "City Center at Oyster Point, Thimble Shoals and Canon Boulevard, the Oyster Point business park, "
     "Warwick Boulevard and Hilton Village, Midtown and downtown Newport News."),
    ("newport-news-i-64-denbigh", "Newport News I-64 / Jefferson Avenue / Denbigh / PHF Airport",
     "Newport News I-64 & Airport", "CORE", "newport news",
     ["23602", "23608", "23603"],
     "Jefferson Avenue at I-64 exits 250-256, Newport News / Williamsburg International Airport (PHF), Denbigh, "
     "Lee Hall and Warwick Boulevard north."),
    ("suffolk", "Suffolk Downtown / US-58 / Harbour View", "Suffolk", "CORRIDOR", "suffolk",
     ["23434", "23435", "23436", "23433"],
     "The city of Suffolk's traveller lodging: downtown and the US-58 / US-460 / US-13 bypass corridor, and Harbour "
     "View / North Suffolk at I-664 and the Monitor-Merrimac Bridge-Tunnel."),
    ("smithfield", "Smithfield / Carrollton / Benns Church", "Smithfield", "FRINGE", "smithfield",
     ["23430", "23431", "23314"],
     "The Town of Smithfield and Carrollton in Isle of Wight County, at Benns Church (US-258 / VA-10) and the "
     "James River Bridge approach."),
    ("yorktown-route-17", "Yorktown US-17 / Tabb / Grafton", "Yorktown US-17", "FRINGE", "yorktown",
     ["23692", "23693"],
     "York County's US-17 (George Washington Memorial Highway) and Victory Boulevard corridor at Grafton and Tabb, "
     "on the Newport News and Hampton line."),
]

#: The mailing municipalities each corridor's postal codes are addressed as. A property whose OWN stated
#: municipality is a known city OUTSIDE this set is a GEOGRAPHY_HOLD (read by the census helper).
CITY_OF_CORRIDOR = {
    "virginia-beach-oceanfront": {"virginia beach"},
    "virginia-beach-town-center": {"virginia beach"},
    "virginia-beach-central-bayside": {"virginia beach"},
    "norfolk-downtown": {"norfolk"},
    "norfolk-airport-military-highway": {"norfolk"},
    "norfolk-ocean-view": {"norfolk"},
    "chesapeake-greenbrier": {"chesapeake"},
    "chesapeake-great-bridge-south": {"chesapeake"},
    "chesapeake-western-branch": {"chesapeake"},
    "portsmouth": {"portsmouth"},
    "hampton-coliseum-central": {"hampton"},
    "hampton-mercury-downtown": {"hampton", "fort monroe"},
    "newport-news-city-center": {"newport news"},
    "newport-news-i-64-denbigh": {"newport news"},
    "suffolk": {"suffolk"},
    "smithfield": {"smithfield", "carrollton"},
    "yorktown-route-17": {"yorktown", "grafton", "seaford", "tabb"},
}

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. None in this market.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "virginia beach va": "virginia beach", "va beach": "virginia beach", "virginia bch": "virginia beach",
    "norfolk va": "norfolk", "chesapeake va": "chesapeake", "portsmouth va": "portsmouth", "hampton va": "hampton",
    "newport news va": "newport news", "newport news va.": "newport news", "suffolk va": "suffolk",
    "smithfield va": "smithfield", "yorktown va": "yorktown", "williamsburg va": "williamsburg",
}

HISTORIC_TRIANGLE_WHY = (
    "Williamsburg / Jamestown / James City County / Busch Gardens / Kingsmill / Lightfoot / Toano and historic "
    "Yorktown (23690): the Historic Triangle, a destination lodging market with its own search intent on the "
    "Colonial Parkway; PRESERVED for the future %s market, evaluated and refused here." % FUTURE_SUBMARKET)

MILITARY_WHY = ("MILITARY_NONPUBLIC -- an installation-only postal code: lodging there (Navy Gateway Inns & Suites, "
                "IHG Army Hotels, Air Force Inns, transient quarters) requires installation access or military "
                "eligibility and is not ordinary public lodging; evaluated and refused under the order's military "
                "lodging rule.")

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Williamsburg / James City County / Busch Gardens / Lightfoot / Toano / historic Yorktown", "VA",
     ["23185", "23186", "23187", "23188", "23168", "23081", "23090", "23690"],
     HISTORIC_TRIANGLE_WHY),
    ("Military installations (Naval Station Norfolk, JEB Little Creek, Fort Eustis, Langley, NWS Yorktown, "
     "Norfolk Naval Shipyard)", "VA",
     ["23511", "23551", "23521", "23604", "23665", "23691", "23709", "23681"],
     MILITARY_WHY),
    ("Poquoson", "VA", ["23662"],
     "The city of Poquoson: a residential and waterfront city between Hampton and York County with no hotel core "
     "of its own; evaluated carefully and refused (a single legitimate property there would be an explicit-hotel "
     "admission, never a widened postal code)."),
    ("Western Suffolk (Holland / Whaleyville / Chuckatuck / Driver PO)", "VA", ["23437", "23438", "23432", "23439"],
     "Rural western and southern Suffolk along US-58 and VA-10 beyond the downtown bypass: no traveller lodging core; "
     "refused by name (order: do not absorb far western Suffolk)."),
    ("Isle of Wight rural / Windsor / Surry", "VA", ["23397", "23487", "23883", "23846", "23315"],
     "Isle of Wight County beyond Smithfield and Carrollton, Windsor and Surry: rural, no hotel core; refused."),
    ("Gloucester / Gloucester Point / Mathews / Hayes", "VA", ["23061", "23062", "23072", "23109", "23128"],
     "The Middle Peninsula north of the York River: its own county lodging; refused by name (order)."),
    ("Virginia Eastern Shore (Cape Charles / Cheriton / Exmore / Chincoteague / Onley)", "VA",
     ["23310", "23316", "23350", "23336", "23417", "23413", "23420"],
     "The Eastern Shore across the Chesapeake Bay Bridge-Tunnel; refused by name (order)."),
    ("North Carolina (Moyock / Currituck / Corolla / Outer Banks / Elizabeth City)", "NC",
     ["27958", "27929", "27927", "27909", "27949", "27948", "27959", "27954"],
     "North Carolina's Currituck County, Elizabeth City and the Outer Banks: another state and another market "
     "(outer-banks-nc is its own registered market); refused by name (order)."),
    ("New Kent / Charles City / West Point / Richmond region", "VA", ["23124", "23140", "23030", "23181", "23219"],
     "New Kent County, Charles City and the Richmond region up I-64; refused (richmond-va is its own market)."),
    ("Franklin / Southampton / Courtland / Emporia", "VA", ["23851", "23837", "23847"],
     "Franklin and Southampton County on US-58 west of Suffolk; refused."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover refused neighbours so this order classifies them on evidence.
CELLS = [
    ("vb-oceanfront", "Virginia Beach", "Virginia Beach Oceanfront", 36.8500, -75.9780, 4500, True),
    ("vb-town-center", "Virginia Beach", "Town Center / Pembroke", 36.8450, -76.1400, 3500, True),
    ("vb-lynnhaven", "Virginia Beach", "Lynnhaven / Great Neck / Shore Drive", 36.8750, -76.0700, 5000, True),
    ("vb-kempsville", "Virginia Beach", "Kempsville / Princess Anne / Oceana", 36.8000, -76.1000, 7000, True),
    ("norfolk-downtown", "Norfolk", "Downtown / Waterside / Ghent", 36.8520, -76.2900, 3000, True),
    ("norfolk-airport", "Norfolk", "ORF Airport / Military Highway / Military Circle", 36.8700, -76.2050, 4000, True),
    ("norfolk-ocean-view", "Norfolk", "Ocean View / Wards Corner", 36.9450, -76.2500, 4000, True),
    ("chesapeake-greenbrier", "Chesapeake", "Greenbrier / Crossways / Battlefield North", 36.7700, -76.2400, 4000, True),
    ("chesapeake-great-bridge", "Chesapeake", "Great Bridge / Deep Creek / South Military", 36.7200, -76.2600, 7000, True),
    ("chesapeake-western-branch", "Chesapeake", "Western Branch / Chesapeake Square", 36.8000, -76.4000, 4000, True),
    ("portsmouth", "Portsmouth", "Olde Towne / Churchland / Victory Blvd", 36.8350, -76.3500, 6000, True),
    ("hampton-coliseum", "Hampton", "Coliseum Central / Convention Center", 37.0500, -76.3950, 3500, True),
    ("hampton-downtown", "Hampton", "Downtown / Phoebus / Buckroe", 37.0250, -76.3300, 5000, True),
    ("newport-news-city-center", "Newport News", "City Center / Oyster Point", 37.0850, -76.4700, 4000, True),
    ("newport-news-south", "Newport News", "Hilton Village / Midtown / Downtown", 37.0100, -76.4300, 5000, True),
    ("newport-news-i-64", "Newport News", "Jefferson Ave I-64 / Denbigh / PHF", 37.1300, -76.5100, 6000, True),
    ("suffolk-downtown", "Suffolk", "Downtown / US-58 bypass", 36.7300, -76.5900, 6000, True),
    ("suffolk-harbour-view", "Suffolk", "Harbour View / North Suffolk", 36.8700, -76.4600, 5000, True),
    ("smithfield", "Smithfield", "Smithfield / Carrollton / Benns Church", 36.9500, -76.5900, 7000, True),
    ("yorktown-route-17", "Yorktown", "US-17 / Tabb / Grafton", 37.1400, -76.4500, 6000, True),
    # observation only -- the preserved Historic Triangle and refused neighbours
    ("obs-williamsburg", "Williamsburg", "Williamsburg / Busch Gardens -- OBSERVATION ONLY", 37.2700, -76.7000, 9000, False),
    ("obs-yorktown-historic", "Yorktown", "Historic Yorktown -- OBSERVATION ONLY", 37.2350, -76.5100, 3000, False),
    ("obs-gloucester", "Gloucester Point", "Gloucester Point -- OBSERVATION ONLY", 37.2500, -76.5000, 4000, False),
    ("obs-poquoson", "Poquoson", "Poquoson -- OBSERVATION ONLY", 37.1250, -76.3600, 3000, False),
    ("obs-moyock", "Moyock", "Moyock / Currituck NC -- OBSERVATION ONLY", 36.5200, -76.1800, 8000, False),
    ("obs-western-suffolk", "Holland", "Western Suffolk -- OBSERVATION ONLY", 36.6800, -76.7800, 8000, False),
]

BOUNDS = {
    "min_lat": 36.50,
    "max_lat": 37.42,
    "min_lng": -76.95,
    "max_lng": -75.85,
}

#: Reporting overlay only (never membership): the areas the order names that share a postal code with another.
COVERAGE_AREAS = [
    ("Virginia Beach Oceanfront", 36.8500, -75.9780, 5.0),
    ("Virginia Beach Town Center", 36.8440, -76.1350, 1.6),
    ("Pembroke / Newtown Road", 36.8500, -76.1750, 2.5),
    ("Norfolk Downtown / Waterside", 36.8480, -76.2880, 1.6),
    ("Ghent / ODU", 36.8650, -76.3000, 2.5),
    ("ORF Airport", 36.8850, -76.2050, 2.0),
    ("Military Circle / Military Highway", 36.8520, -76.2080, 2.5),
    ("Norfolk Ocean View", 36.9500, -76.2500, 4.0),
    ("Chesapeake Greenbrier", 36.7720, -76.2330, 2.0),
    ("Chesapeake Battlefield Blvd North", 36.7620, -76.2480, 1.2),
    ("Chesapeake Great Bridge / Battlefield South", 36.7200, -76.2400, 4.0),
    ("Hampton Coliseum / Convention Center", 37.0500, -76.3900, 1.8),
    ("Hampton Roads Center / Mercury Blvd", 37.0450, -76.3700, 3.0),
    ("Newport News City Center", 37.0800, -76.4650, 1.2),
    ("Oyster Point", 37.0950, -76.4800, 2.5),
    ("PHF Airport", 37.1300, -76.4950, 2.5),
    ("Denbigh / Jefferson Ave I-64", 37.1400, -76.5200, 5.0),
]


def build():
    corridors = []
    seen_zip = {}
    for order, (slug, name, area, klass, _city, zips, desc) in enumerate(CORRIDORS, start=1):
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Hampton Roads" % name),
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
    if set(CITY_OF_CORRIDOR) != {c[0] for c in CORRIDORS}:
        raise SystemExit("every corridor needs its mailing cities")

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)),
        ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
        ("state_code", "VA"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Hampton Roads, VA multi-core regional lodging market -- Virginia Beach, Norfolk, Chesapeake, "
                        "Portsmouth, Hampton, Newport News and Suffolk (PetTripFinder discovery scope)"),
        ("state", "VA"),
        ("states", ["VA"]),
        ("country", "US"),
        ("market_center", {"lat": 36.885, "lng": -76.285}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- north over "
             "Williamsburg, Yorktown and Gloucester Point, west over rural Suffolk, Isle of Wight and Surry, south over "
             "Currituck County NC and east over the Chesapeake Bay Bridge-Tunnel -- so that " + WORK_ORDER + " classifies "
             "those properties on evidence instead of being blind to them. Admission is decided by the corridor "
             "registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A multi-core regional market: fourteen CORE corridors across Virginia Beach, Norfolk, "
         "Chesapeake, Portsmouth, Hampton and Newport News, one CORRIDOR (Suffolk) and two FRINGE corridors "
         "(Smithfield, Yorktown US-17). Williamsburg and historic Yorktown are OBSERVED and REFUSED, preserved for a "
         "future " + FUTURE_SUBMARKET + " market; military installations, Poquoson, western Suffolk, Gloucester, the "
         "Eastern Shore and North Carolina are named and REFUSED."),
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
        ("market_name", "Hampton Roads, Virginia"),
        ("market_slug", MARKET_ID),
        ("state_name", "Virginia"),
        ("state_code", "VA"),
        ("primary_state_code", "VA"),
        ("states", ["VA"]),
        ("primary_city", "Virginia Beach"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Hampton Roads, Virginia | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Hampton Roads -- the Virginia Beach Oceanfront and Town Center, downtown "
         "Norfolk and the ORF airport, Chesapeake, Portsmouth, Hampton, Newport News and Suffolk -- with real pet fees "
         "and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Hampton Roads"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A multi-core regional market of independent cities -- not one city and not the "
         "Virginia Beach-Norfolk-Newport News MSA. Every corridor sits inside one city, so a property's city is never "
         "flattened into a generic regional label. Nothing else admits a property: not a brand's 'Norfolk Airport' or "
         "'Newport News / Williamsburg' marketing name, not a map pin, not a short-term-rental listing, not a "
         "competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every admitted lodging "
         "ZIP is claimed by exactly one corridor. The ORF airport shares 23502 / 23518 with Military Highway and "
         "Military Circle; Battlefield Boulevard North shares 23320 with Greenbrier; the Hampton Coliseum shares 23666 "
         "with the Convention Center and Hampton Roads Center; City Center shares 23606 with Oyster Point: each pair "
         "is reported as an overlay, never a separate page."),
        ("_census_membership_note",
         "Williamsburg, Jamestown, Busch Gardens and historic Yorktown are the Historic Triangle, preserved for a "
         "future market; military installation lodging, Poquoson, western Suffolk, Gloucester, the Eastern Shore and "
         "North Carolina are not absorbed. A property whose own page states one of their postal codes is OUTSIDE, "
         "however it is named. Individual condos, vacation-rental units, Airbnb / Vrbo inventory, property-management "
         "portfolios, timeshare units without a public hotel operation, private residences and base lodging closed "
         "to the public are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    adjudications = OrderedDict([
        ("Williamsburg / Jamestown / Busch Gardens", OrderedDict([
            ("decision", "OUTSIDE, preserved for the future %s market (the order's default)" % FUTURE_SUBMARKET),
            ("why",
             "The Historic Triangle's 23185 / 23188 lodging (Colonial Williamsburg, Busch Gardens, Kingsmill, the "
             "Richmond Road and Route 60 motel strip) sells a destination -- theme park, living-history museum, "
             "Jamestown -- to leisure travellers with their own search intent, thirty miles up I-64 from Newport News. "
             "Absorbing it would fold a whole second destination market into Hampton Roads."),
        ])),
        ("Yorktown", OrderedDict([
            ("decision", "SPLIT -- historic Yorktown (23690) OUTSIDE, preserved for %s; the US-17 / Tabb / Grafton "
                         "corridor (23692 / 23693) FRINGE (yorktown-route-17)" % FUTURE_SUBMARKET),
            ("why",
             "The Riverwalk Landing inns and the battlefield village sit on the Colonial Parkway and are sold as the "
             "third point of the Historic Triangle. The US-17 and Victory Boulevard hotels at Grafton and Tabb sit on "
             "the Newport News / Hampton line beside NASA Langley and PHF and are peninsula business lodging."),
        ])),
        ("Poquoson", OrderedDict([
            ("decision", "OUTSIDE -- evaluated carefully"),
            ("why", "A small independent city with marinas and neighbourhoods and no hotel core; its travellers sleep "
                    "in Hampton's Coliseum Central or on US-17."),
        ])),
        ("Suffolk", OrderedDict([
            ("decision", "CORRIDOR (suffolk: 23434 / 23435 / 23436 / 23433); western Suffolk OUTSIDE"),
            ("why", "Downtown Suffolk's US-58 / US-460 bypass hotels and North Suffolk's Harbour View cluster at I-664 "
                    "serve Hampton Roads travellers; Holland, Whaleyville and Chuckatuck are rural and carry no lodging "
                    "core (order: do not absorb far western Suffolk solely because it is in the MSA)."),
        ])),
        ("Smithfield", OrderedDict([
            ("decision", "FRINGE (smithfield: 23430 / 23431 / 23314 Carrollton)"),
            ("why", "The Town of Smithfield and the Benns Church / Carrollton cluster at the James River Bridge sit "
                    "twenty minutes from Newport News and host Smithfield Foods and Isle of Wight business travel; "
                    "admitted as fringe because their lodging is small and town-scale."),
        ])),
        ("Military installations", OrderedDict([
            ("decision", "OUTSIDE on installation-only ZIPs; named military lodging refused by name elsewhere"),
            ("why", MILITARY_WHY),
        ])),
        ("Norfolk / Virginia Beach line (Newtown Road, Military Highway)", OrderedDict([
            ("decision", "ZIP decides the corridor; the property's own stated city must be the ZIP's city"),
            ("why", "Newtown Road is the Norfolk / Virginia Beach line and Military Highway runs from Norfolk into "
                    "Chesapeake. A Norfolk-ZIP hotel whose own page says Virginia Beach (or the reverse) is a "
                    "GEOGRAPHY_HOLD, never silently re-labelled."),
        ])),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 -- Hampton Roads multi-core geography, city model, fringe adjudications and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-14"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Hampton Roads' turn in the serialized release "
         "queue against the then-current live parent."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("city_model",
         "Every corridor sits inside exactly one city (CITY_OF_CORRIDOR), so every admitted hotel carries a city, a "
         "corridor and the metro market. The six cores are Virginia Beach, Norfolk, Chesapeake, Portsmouth, Hampton "
         "and Newport News; Suffolk is a corridor city; Smithfield and Yorktown are fringe towns."),
        ("travel_market",
         "Hampton Roads' lodging cores (the Virginia Beach Oceanfront, Town Center and Lynnhaven / Shore Drive; "
         "downtown Norfolk, the ORF airport and Military Highway, Ocean View; Greenbrier, Great Bridge and Western "
         "Branch in Chesapeake; Portsmouth; Hampton's Coliseum Central and downtown; Newport News City Center / Oyster "
         "Point and I-64 / PHF), Suffolk, and the fringe towns a Hampton Roads traveller sleeps in by choice "
         "(Smithfield, Yorktown US-17)."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("fringe_adjudications", adjudications),
        ("corridor_page_evaluations", OrderedDict([
            ("Virginia Beach Oceanfront", "SEPARATE CORRIDOR (23451 / 23450)."),
            ("Virginia Beach Town Center", "SEPARATE CORRIDOR (23462: Town Center, Pembroke, Newtown Road)."),
            ("Norfolk Downtown", "SEPARATE CORRIDOR (23510 / 23507 / 23517 / 23508 ...)."),
            ("ORF Airport", "OVERLAY inside norfolk-airport-military-highway -- the airport hotels on North Military "
                            "Highway share 23502 with Military Circle."),
            ("Military Highway", "SAME CORRIDOR as the airport (23502 / 23513), reported as an overlay; the Chesapeake "
                                 "stretch of South Military Highway is in Chesapeake's corridors."),
            ("Chesapeake Greenbrier", "SEPARATE CORRIDOR (23320 / 23325)."),
            ("Chesapeake Battlefield", "SPLIT -- Battlefield Boulevard North (I-64 exit 290) shares 23320 with Greenbrier "
                                       "(overlay); Battlefield Boulevard South / Great Bridge is its own corridor."),
            ("Portsmouth", "SEPARATE CORRIDOR (the whole city)."),
            ("Hampton Coliseum", "SEPARATE CORRIDOR (23666), with the Convention Center and Hampton Roads Center as "
                                 "overlays."),
            ("Hampton / Mercury Blvd", "SEPARATE CORRIDOR for Mercury Boulevard East / downtown (23669 / 23661 / 23663); "
                                       "Mercury Boulevard West at I-64 is in 23666 (overlay)."),
            ("Newport News City Center", "SEPARATE CORRIDOR (23606 ...), with Oyster Point as an overlay (shared ZIP)."),
            ("Oyster Point", "OVERLAY inside newport-news-city-center."),
            ("Newport News I-64", "SEPARATE CORRIDOR (23602 / 23608 / 23603)."),
            ("Suffolk", "SEPARATE CORRIDOR (CORRIDOR class)."),
            ("Smithfield", "SEPARATE CORRIDOR (FRINGE class)."),
            ("Yorktown", "SEPARATE CORRIDOR for US-17 (FRINGE class); historic Yorktown OUTSIDE."),
        ])),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]),
            ("geography_class", c["geography_class"]),
            ("city", CITY_OF[c["slug"]]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {k: sum(1 for c in corridors if c["geography_class"] == k)
                                     for k in ("CORE", "CORRIDOR", "FRINGE")}),
        ("corridor_page_rule",
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = "
         "5 verified pet-friendly hotels) is met. No thin corridor page is invented for SEO; every "
         "corridor is show_in_navigation/show_in_sitemap false until a registration order publishes it."),
        ("coverage_areas_are_a_reporting_overlay",
         "The order's named areas that share a postal code with another area are reported from the "
         "property's own stated street first and a nearest-anchor overlay on its pin second. The overlay "
         "decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("municipality_refusals", []),
        ("city_of_corridor", OrderedDict((k, sorted(v)) for k, v in CITY_OF_CORRIDOR.items())),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Six cells observe Williamsburg, historic Yorktown, Gloucester Point, Poquoson, Moyock NC and western "
         "Suffolk. They admit nothing."),
        ("military_lodging_rule", MILITARY_WHY + " Ordinary publicly bookable commercial hotels serving military "
                                                "travellers are admitted on their own postal code."),
        ("beach_resort_rule",
         "Qualifying publicly bookable hotels, motels, resorts, inns and extended-stay hotels enter under the existing "
         "lodging contract. Individual condos, vacation-rental units, Airbnb / Vrbo inventory, property-management "
         "portfolios, timeshare units without normal public hotel operation and private residential inventory are "
         "never admitted. A complex resort is decided on exact premises identity: one hotel identity, several "
         "distinct hotels, condo / timeshare inventory, or non-public lodging."),
        ("non_hotel_rule",
         "The census admits hotels, motels, inns, boutique and historic hotels, extended-stay hotels and qualifying "
         "public lodging establishments operated as lodging businesses: bookable nightly rooms or suites sold to the "
         "public under one establishment name, with an official property page and an on-site hotel operation. It "
         "NEVER admits: ordinary apartment communities or individual apartments; corporate-housing and furnished-"
         "apartment portfolios; student housing; individual houses or cottages rented whole; Airbnb / Vrbo-style "
         "listings; vacation-rental management companies; timeshare inventory unless the property independently "
         "qualifies as a hotel; private residences; and military lodging closed to the public. Campgrounds, RV parks "
         "and hostels-as-dormitories are NON_LODGING."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


#: slug -> the city the corridor sits in (display casing).
CITY_OF = {slug: city.title() for slug, _n, _a, _k, city, _z, _d in CORRIDORS}


def corridor_municipality():
    """slug -> the municipality the corridor sits in (name attachment only)."""
    return {slug: city for slug, _n, _a, _k, city, _z, _d in CORRIDORS}


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
    if corridor_slug == "virginia-beach-town-center":
        return coverage_area(lat, lng, ("Virginia Beach Town Center", "Pembroke / Newtown Road")) or \
            "Pembroke / Newtown Road"
    if corridor_slug == "norfolk-downtown":
        return coverage_area(lat, lng, ("Norfolk Downtown / Waterside", "Ghent / ODU")) or "Norfolk Downtown / Waterside"
    if corridor_slug == "norfolk-airport-military-highway":
        if re.search(r"\b(norview|azalea garden|airport)\b", st, re.I):
            return "ORF Airport"
        return coverage_area(lat, lng, ("ORF Airport", "Military Circle / Military Highway")) or \
            "Military Circle / Military Highway"
    if corridor_slug == "chesapeake-greenbrier":
        if re.search(r"\bbattlefield\b", st, re.I):
            return "Chesapeake Battlefield Blvd North"
        return "Chesapeake Greenbrier"
    if corridor_slug == "hampton-coliseum-central":
        if re.search(r"\b(hampton roads center|mercury|big bethel|magruder|executive)\b", st, re.I):
            return "Hampton Roads Center / Mercury Blvd"
        return "Hampton Coliseum / Convention Center"
    if corridor_slug == "newport-news-city-center":
        if re.search(r"\b(town center|city center|thimble shoals|canon)\b", st, re.I):
            return "Newport News City Center"
        if re.search(r"\b(oyster point|jefferson|j\.? clyde morris|victory)\b", st, re.I):
            return "Oyster Point"
        return coverage_area(lat, lng, ("Newport News City Center", "Oyster Point")) or "Newport News (Midtown / Hilton Village)"
    if corridor_slug == "newport-news-i-64-denbigh":
        return coverage_area(lat, lng, ("PHF Airport", "Denbigh / Jefferson Ave I-64")) or "Denbigh / Jefferson Ave I-64"
    return {"virginia-beach-oceanfront": "Virginia Beach Oceanfront",
            "virginia-beach-central-bayside": "Virginia Beach Central & Bayside",
            "norfolk-ocean-view": "Norfolk Ocean View",
            "chesapeake-great-bridge-south": "Chesapeake Great Bridge / Battlefield South",
            "chesapeake-western-branch": "Chesapeake Western Branch", "portsmouth": "Portsmouth",
            "hampton-mercury-downtown": "Hampton Downtown / Mercury Blvd East", "suffolk": "Suffolk",
            "smithfield": "Smithfield", "yorktown-route-17": "Yorktown US-17"}.get(corridor_slug)


def normalize_municipality(city):
    muni = " ".join((city or "").lower().replace(".", " ").replace(",", " ").split())
    return MUNICIPALITY_SPELLINGS.get(muni, muni)


def municipality_area(city):
    """The named city a property's own stated municipality reports under, or None."""
    muni = normalize_municipality(city)
    return {c: c.title() for cities in CITY_OF_CORRIDOR.values() for c in cities}.get(muni)


def is_future_submarket(postal, municipality=None):
    """True when a property belongs to the preserved Williamsburg / Historic Triangle market."""
    z = (postal or "").strip()[:5]
    return z in OUTSIDE[0][2] or normalize_municipality(municipality) in ("williamsburg", "toano", "lightfoot")


def is_military_postal(postal):
    return (postal or "").strip()[:5] in OUTSIDE[1][2]


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
