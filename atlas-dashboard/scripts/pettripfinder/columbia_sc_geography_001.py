"""PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001 -- Phase 2 + 3 + 4: the Columbia travel market and its corridors.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Columbia, South Carolina traveller lodging market -- a MULTI-CORE state-capital
market: the State House / Main Street / Vista convention core, the University of South Carolina,
Prisma Health's two hospital campuses, Fort Jackson (the Army's largest basic-training post, whose
graduations fill every hotel in the east of the city weekly), Columbia Metropolitan Airport (CAE)
in West Columbia, and the I-20 / I-26 / I-77 / I-126 interstate ring with its suburban business
districts (Harbison, St. Andrews, Northeast / Two Notch, Sandhills / Clemson Road, Lexington). It is
NOT Columbia city limits and NOT the Columbia MSA / Midlands. The rule is stated as an explicit
four-way class (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is admitted, so no
property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official page states it,
joined to the corridor registry below. The registry is a POSTAL-CODE PARTITION: every admitted
lodging ZIP is claimed by exactly one corridor, and every corridor names the mailing
municipalities its ZIPs are addressed as, so a property's corridor is a lookup and never a
judgement. A brand's marketing name ("Columbia Airport", "Columbia / Fort Jackson", "Columbia
West / Lexington", "Columbia Northeast") never admits and never places a property.

MUNICIPALITY SAFETY
-------------------
West Columbia, Cayce, Irmo, Lexington, Forest Acres, Blythewood, Chapin and Elgin are distinct
municipalities (or postal towns) whose hotels are routinely marketed as "Columbia". The ZIP decides
the corridor, and the municipality the property's OWN page states is then checked against the
mailing municipalities of that corridor's ZIPs (CITY_OF_CORRIDOR, applied in the census helper). A
stated municipality that contradicts the ZIP's mailing town -- "Columbia, SC 29169" for a West
Columbia postal code -- is a GEOGRAPHY_HOLD: one of the two first-party facts is wrong, and the
ZIP alone never decides which. The city is preserved on every row, never flattened.

THE FOUR CLASSES
----------------
CORE       Downtown / The Vista / USC / Five Points; North Columbia (Prisma Health Richland,
           North Main, I-20 exits 70-73); Fort Jackson / Forest Acres / Garners Ferry;
           Northeast / Two Notch / Dentsville; Sandhills / Clemson Road / Killian Road;
           St. Andrews / Bush River / Seven Oaks / Greystone (I-20 / I-26 / I-126);
           Harbison / Irmo; West Columbia / Cayce (Knox Abbott, US-1, I-26 exit 111 / I-77 exit 1);
           CAE Airport / Airport Boulevard (I-26 exit 113); Lexington.
CORRIDOR   Blythewood (I-77 exit 27).
FRINGE     Chapin (I-26 exit 91); Elgin (I-20 exit 82 / 87).
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision.

FORT JACKSON / MILITARY LODGING
-------------------------------
Fort Jackson's installation postal code (29207) is OUTSIDE with the MILITARY_NONPUBLIC reason:
on-post lodging (the IHG Army Hotel, transient and distinguished-visitor quarters, barracks) requires
installation access or DoD eligibility and is not ordinary public lodging. The commercial hotels
outside the gates that serve graduation families and PCS travellers (Forest Drive, Garners Ferry
Road, Two Notch Road, Clemson Road) are ordinary public hotels and are admitted on their own ZIP.
A named military lodging row inside a mixed ZIP is refused by name in the census helper.
McEntire Joint National Guard Base (Eastover) is outside for the same reason and for distance.

Outputs:
  scripts/pettripfinder/discovery/config/columbia_sc.json
  launch_packages/pettripfinder/markets/proposed/columbia-sc.json
  launch_packages/pettripfinder/markets/reports/columbia_sc_geography_001.json
  launch_packages/pettripfinder/markets/reports/columbia_sc_corridor_registry_001.json
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

WORK_ORDER = "PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "columbia-sc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "columbia_sc.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "columbia-sc.json")
REPORT_OUT = os.path.join(REPORTS, "columbia_sc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "columbia_sc_corridor_registry_001.json")

#: No future standalone submarket is preserved by this order (Camden, Sumter, Orangeburg, Newberry and
#: Aiken are separate traveller markets refused by name, not sub-markets of Columbia).
FUTURE_SUBMARKET = ""

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, city, postal codes, description)
CORRIDORS = [
    ("downtown-vista-usc", "Downtown Columbia / The Vista / USC / Five Points", "Downtown & The Vista", "CORE", "columbia",
     ["29201", "29208", "29205"],
     "The State House and Main Street, The Vista and the Columbia Metropolitan Convention Center, the University of "
     "South Carolina campus and Williams-Brice / Colonial Life Arena, Prisma Health Baptist, Five Points, Devine "
     "Street and Shandon."),
    ("north-columbia-medical", "North Columbia / Prisma Health Richland / North Main / I-20", "North Columbia & Medical",
     "CORE", "columbia",
     ["29203", "29204"],
     "Prisma Health Richland and the Harden Street / Farrow Road medical district, North Main Street and Monticello "
     "Road, the I-20 interchanges at exits 70-73 and I-77 at Farrow Road, and Two Notch Road inside the Beltline."),
    ("fort-jackson-forest-acres", "Fort Jackson / Forest Acres / Garners Ferry Road", "Fort Jackson", "CORE", "columbia",
     ["29206", "29209"],
     "The commercial lodging outside Fort Jackson's gates: Forest Drive at I-77 exit 12 and Forest Acres / Trenholm "
     "Road, Garners Ferry Road and Fort Jackson Boulevard, Shop Road and Bluff Road toward the Dorn VA Medical Center "
     "and the I-77 southeast interchanges."),
    ("northeast-two-notch", "Northeast Columbia / Two Notch Road / Dentsville / Parklane", "Northeast Columbia",
     "CORE", "columbia",
     ["29223"],
     "Two Notch Road at I-77 exit 17 and I-20 exit 74, Parklane Road, Fashion Drive and Columbia Place, Dentsville "
     "and Decker Boulevard."),
    ("sandhills-clemson-road", "Sandhills / Clemson Road / Killian Road", "Sandhills & Clemson Road", "CORE", "columbia",
     ["29229"],
     "Clemson Road at I-20 exit 80, the Village at Sandhill, Sparkleberry Crossing, Killian Road and Farrow Road at "
     "I-77 exit 22 and the Spears Creek Church Road approach."),
    ("st-andrews-bush-river", "St. Andrews / Bush River Road / Seven Oaks / Greystone", "St. Andrews & Bush River",
     "CORE", "columbia",
     ["29210"],
     "The I-20 / I-26 / I-126 interchange cluster: Bush River Road and Dutch Square, Greystone Boulevard and "
     "Riverbanks Zoo, St. Andrews Road, Broad River Road at I-20 exit 65, Seven Oaks and Morninghill Drive."),
    ("harbison-irmo", "Harbison / Irmo / Lake Murray Boulevard", "Harbison & Irmo", "CORE", "columbia",
     ["29212", "29063", "29002", "29221"],
     "Harbison Boulevard and Columbiana Centre at I-26 exits 102-103, Piney Grove Road at exit 104, Lake Murray "
     "Boulevard, Irmo, Ballentine and Dutch Fork Road."),
    ("west-columbia-cayce", "West Columbia / Cayce / Knox Abbott Drive / I-26 US-1", "West Columbia & Cayce", "CORE",
     "west columbia",
     ["29169", "29033"],
     "The Congaree riverfront towns across from downtown: Meeting Street and State Street, Knox Abbott Drive, the "
     "Augusta Road (US-1) interchange at I-26 exit 111 and I-77's southern terminus at Charleston Highway in Cayce."),
    ("cae-airport", "Columbia Metropolitan Airport (CAE) / Airport Boulevard / Platt Springs Road", "CAE Airport",
     "CORE", "west columbia",
     ["29170", "29172", "29171"],
     "Columbia Metropolitan Airport and the Airport Boulevard (SC-302) interchange at I-26 exit 113, Platt Springs "
     "Road, Edmund Highway and Pine Ridge."),
    ("lexington", "Lexington / Sunset Boulevard / US-378 / I-20 exits 55-61", "Lexington", "CORE", "lexington",
     ["29072", "29073", "29071"],
     "The Town of Lexington: Sunset Boulevard (US-378) and West Main Street, Columbia Avenue (US-1) at I-20 exit 58, "
     "Lexington Medical Center, Red Bank and the Lake Murray south shore."),
    ("blythewood", "Blythewood / I-77 exit 27", "Blythewood", "CORRIDOR", "blythewood",
     ["29016"],
     "The Town of Blythewood at I-77 exit 27 (Blythewood Road), north of Killian Road on the Charlotte approach."),
    ("chapin", "Chapin / I-26 exit 91 / Lake Murray north shore", "Chapin", "FRINGE", "chapin",
     ["29036"],
     "The Town of Chapin at I-26 exit 91 (Columbia Avenue) and the north shore of Lake Murray."),
    ("elgin", "Elgin / I-20 exits 82-87", "Elgin", "FRINGE", "elgin",
     ["29045"],
     "Elgin and the I-20 interchanges at Spears Creek Church Road (exit 82) and White Pond Road (exit 87) on the "
     "Camden approach."),
]

#: The mailing municipalities each corridor's postal codes are addressed as. A property whose OWN stated
#: municipality is a known place OUTSIDE this set is a GEOGRAPHY_HOLD (read by the census helper).
CITY_OF_CORRIDOR = {
    "downtown-vista-usc": {"columbia"},
    "north-columbia-medical": {"columbia"},
    "fort-jackson-forest-acres": {"columbia", "forest acres", "arcadia lakes"},
    "northeast-two-notch": {"columbia"},
    "sandhills-clemson-road": {"columbia"},
    "st-andrews-bush-river": {"columbia"},
    "harbison-irmo": {"columbia", "irmo", "ballentine"},
    "west-columbia-cayce": {"west columbia", "cayce", "springdale"},
    "cae-airport": {"west columbia", "cayce", "pine ridge", "springdale"},
    "lexington": {"lexington", "pine ridge", "red bank", "south congaree", "oak grove"},
    "blythewood": {"blythewood"},
    "chapin": {"chapin"},
    "elgin": {"elgin"},
}

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. None in this market.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "columbia sc": "columbia", "w columbia": "west columbia", "west columbia sc": "west columbia",
    "westcolumbia": "west columbia", "w columbia sc": "west columbia", "cayce sc": "cayce",
    "lexington sc": "lexington", "irmo sc": "irmo", "blythewood sc": "blythewood", "chapin sc": "chapin",
    "elgin sc": "elgin", "forest acres sc": "forest acres",
}

MILITARY_WHY = ("MILITARY_NONPUBLIC -- an installation-only postal code: lodging there (the Fort Jackson IHG Army "
                "Hotel, transient and distinguished-visitor quarters, barracks, McEntire JNGB billeting) requires "
                "installation access or military / DoD eligibility and is not ordinary public lodging; evaluated and "
                "refused under the order's Fort Jackson / military lodging rule.")

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Military installations (Fort Jackson; McEntire Joint National Guard Base / Eastover)", "SC",
     ["29207"],
     MILITARY_WHY),
    ("Gaston / Swansea / Pelion / Gilbert (southern and western Lexington County)", "SC",
     ["29053", "29160", "29123", "29054"],
     "Rural southern and western Lexington County on US-321, SC-6 and US-1 beyond the Lexington and Cayce "
     "corridors: evaluated carefully; no public lodging core of its own (a single legitimate property there would "
     "be an explicit-hotel admission, never a widened postal code)."),
    ("Eastover / Hopkins / Gadsden (lower Richland County)", "SC", ["29044", "29061", "29052"],
     "Lower Richland County toward Congaree National Park and McEntire JNGB: rural, no hotel core; refused."),
    ("Camden / Lugoff (Kershaw County)", "SC", ["29020", "29078"],
     "Camden and Lugoff on I-20 exits 92-98: Kershaw County's own historic-town lodging market (steeplechase, "
     "Revolutionary War sites); refused by name (order: do not automatically absorb Camden)."),
    ("Sumter / Shaw AFB / Dalzell", "SC", ["29150", "29153", "29154", "29152", "29040"],
     "Sumter and Shaw Air Force Base, 45 miles east on US-378: a separate traveller market; refused by name (order)."),
    ("Orangeburg / Santee / St. Matthews", "SC", ["29115", "29118", "29142", "29135"],
     "Orangeburg (SC State, Claflin), Santee on I-95 and St. Matthews: separate markets down I-26; refused by name "
     "(order)."),
    ("Newberry / Prosperity / Little Mountain / Pomaria", "SC", ["29108", "29127", "29075", "29122"],
     "Newberry County up I-26 beyond Chapin: its own college-town lodging; refused by name (order)."),
    ("Winnsboro / Ridgeway (Fairfield County)", "SC", ["29180", "29130"],
     "Fairfield County up I-77 beyond Blythewood; refused."),
    ("Batesburg-Leesville / Leesville / Summit", "SC", ["29006", "29070"],
     "Western Lexington and Saluda counties on US-1 / I-20 exit 39: no Columbia lodging core; refused."),
    ("Aiken / North Augusta / Augusta GA", "SC", ["29801", "29803", "29841", "29860", "30901", "30907", "30909"],
     "Aiken and the Augusta, Georgia metro: a separate traveller market 60 miles west on I-20; refused by name "
     "(order)."),
    ("Florence / Rock Hill / Charlotte region", "SC", ["29501", "29505", "29730", "29732", "29715"],
     "Florence (I-95 / I-20), Rock Hill and the Charlotte region: separate markets (charlotte-nc is its own "
     "registered market); refused by name (order)."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover refused neighbours so this order classifies them on evidence.
CELLS = [
    ("downtown-vista", "Columbia", "Downtown / The Vista / USC / Five Points", 33.9950, -81.0350, 3500, True),
    ("north-columbia", "Columbia", "North Main / Prisma Health Richland / Farrow Road", 34.0400, -81.0250, 4500, True),
    ("fort-jackson", "Columbia", "Forest Drive / Garners Ferry / Fort Jackson Blvd", 34.0000, -80.9500, 6000, True),
    ("northeast-two-notch", "Columbia", "Two Notch Road / Parklane / Dentsville", 34.0800, -80.9550, 4500, True),
    ("sandhills", "Columbia", "Clemson Road / Killian Road", 34.1350, -80.8850, 6000, True),
    ("st-andrews", "Columbia", "Bush River / Greystone / St. Andrews", 34.0250, -81.1050, 4500, True),
    ("harbison-irmo", "Irmo", "Harbison / Irmo / Piney Grove", 34.0800, -81.1800, 6000, True),
    ("west-columbia-cayce", "West Columbia", "West Columbia / Cayce / Knox Abbott", 33.9750, -81.0800, 5000, True),
    ("cae-airport", "West Columbia", "CAE Airport / Airport Blvd", 33.9500, -81.1300, 5000, True),
    ("lexington", "Lexington", "Lexington / Sunset Blvd / US-1", 33.9800, -81.2300, 7000, True),
    ("blythewood", "Blythewood", "Blythewood / I-77 exit 27", 34.2050, -80.9750, 5000, True),
    ("chapin", "Chapin", "Chapin / I-26 exit 91", 34.1650, -81.3450, 5000, True),
    ("elgin", "Elgin", "Elgin / I-20 exits 82-87", 34.1700, -80.8000, 6000, True),
    # observation only -- refused neighbours
    ("obs-fort-jackson-post", "Fort Jackson", "Fort Jackson installation -- OBSERVATION ONLY", 34.0300, -80.8900, 5000, False),
    ("obs-camden-lugoff", "Lugoff", "Lugoff / Camden -- OBSERVATION ONLY", 34.2250, -80.6900, 7000, False),
    ("obs-gaston-swansea", "Gaston", "Gaston / Swansea / Pelion -- OBSERVATION ONLY", 33.8200, -81.1500, 9000, False),
    ("obs-eastover", "Eastover", "Eastover / Hopkins -- OBSERVATION ONLY", 33.9000, -80.8000, 8000, False),
    ("obs-winnsboro", "Winnsboro", "Ridgeway / Winnsboro approach -- OBSERVATION ONLY", 34.2800, -81.0500, 6000, False),
    ("obs-little-mountain", "Little Mountain", "Little Mountain / Prosperity approach -- OBSERVATION ONLY", 34.2000, -81.4300, 6000, False),
]

BOUNDS = {
    "min_lat": 33.72,
    "max_lat": 34.32,
    "min_lng": -81.50,
    "max_lng": -80.58,
}

#: Reporting overlay only (never membership): the areas the order names that share a postal code with another.
COVERAGE_AREAS = [
    ("The Vista / Convention Center", 33.9960, -81.0450, 0.9),
    ("Main Street / State House", 34.0020, -81.0340, 0.9),
    ("University of South Carolina", 33.9950, -81.0250, 1.0),
    ("Five Points / Devine Street", 33.9990, -81.0120, 1.2),
    ("Prisma Health Richland", 34.0310, -81.0310, 1.5),
    ("I-20 / North Main", 34.0650, -81.0300, 3.0),
    ("Forest Drive / I-77 (Fort Jackson gate)", 34.0200, -80.9550, 2.5),
    ("Garners Ferry / Fort Jackson Blvd", 33.9800, -80.9600, 3.0),
    ("Two Notch / I-77 exit 17", 34.0750, -80.9450, 2.0),
    ("Dentsville / Decker Blvd", 34.0600, -80.9750, 2.5),
    ("Clemson Road / I-20 exit 80", 34.1400, -80.8750, 2.5),
    ("Killian Road / I-77 exit 22", 34.1400, -80.9350, 2.5),
    ("Bush River Road / I-20 / I-26", 34.0300, -81.1150, 2.5),
    ("Greystone / Riverbanks", 34.0150, -81.0700, 1.5),
    ("St. Andrews Road", 34.0550, -81.1100, 2.5),
    ("Harbison Blvd / I-26", 34.0800, -81.1550, 2.5),
    ("Piney Grove Road / I-26", 34.0650, -81.1300, 1.5),
    ("Irmo", 34.0900, -81.1850, 3.0),
    ("Knox Abbott / Cayce", 33.9650, -81.0600, 2.5),
    ("I-26 / US-1 (exit 111)", 33.9900, -81.1050, 2.0),
    ("CAE Airport / Airport Blvd (exit 113)", 33.9600, -81.1150, 2.5),
    ("Lexington Sunset Blvd", 33.9900, -81.2150, 3.5),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Columbia" % name),
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
            ("state_code", "SC"),
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
        ("state_code", "SC"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Columbia, SC multi-core state-capital lodging market -- downtown / Vista / USC, Fort Jackson, "
                        "Northeast and Sandhills, St. Andrews and Harbison / Irmo, West Columbia / Cayce and CAE, "
                        "Lexington (PetTripFinder discovery scope)"),
        ("state", "SC"),
        ("states", ["SC"]),
        ("country", "US"),
        ("market_center", {"lat": 34.000, "lng": -81.035}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- east over "
             "Fort Jackson, Lugoff and the Camden approach, south over Gaston, Swansea and Eastover, north over "
             "Ridgeway and west over Little Mountain -- so that " + WORK_ORDER + " classifies those properties on "
             "evidence instead of being blind to them. Admission is decided by the corridor registry over the "
             "property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A multi-core state-capital market: ten CORE corridors (downtown / Vista / USC, north Columbia "
         "medical, Fort Jackson, Northeast, Sandhills, St. Andrews, Harbison / Irmo, West Columbia / Cayce, CAE airport, "
         "Lexington), one CORRIDOR (Blythewood) and two FRINGE corridors (Chapin, Elgin). The Fort Jackson "
         "installation, Camden / Lugoff, Sumter, Orangeburg, Newberry, Winnsboro, Aiken / Augusta, Florence, Rock Hill "
         "and the rural Lexington / lower Richland towns are named and REFUSED."),
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
        ("market_name", "Columbia, South Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "South Carolina"),
        ("state_code", "SC"),
        ("primary_state_code", "SC"),
        ("states", ["SC"]),
        ("primary_city", "Columbia"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Columbia, South Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Columbia, SC -- downtown and The Vista, USC, Fort Jackson, Northeast "
         "Columbia and Sandhills, Harbison and Irmo, West Columbia, Cayce and the CAE airport, and Lexington -- with "
         "real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Columbia, SC"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A multi-core state-capital market -- not Columbia city limits and not the Columbia "
         "MSA / Midlands. Every corridor names the mailing municipalities of its postal codes, so a West Columbia, "
         "Cayce, Irmo or Lexington hotel is never flattened into 'Columbia'. Nothing else admits a property: not a "
         "brand's 'Columbia Airport' or 'Columbia / Fort Jackson' marketing name, not a map pin, not a short-term-"
         "rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every admitted lodging "
         "ZIP is claimed by exactly one corridor. The Vista, Main Street, USC and Five Points share the downtown "
         "corridor; Forest Drive and Garners Ferry share the Fort Jackson corridor; Clemson Road and Killian Road "
         "share Sandhills; Bush River, Greystone and St. Andrews Road share 29210; Harbison and Piney Grove share "
         "29212: each is reported as an overlay, never a separate page. The I-20, I-26 and I-77 corridors cross "
         "several postal corridors and are reported as overlays across them."),
        ("_census_membership_note",
         "The Fort Jackson installation (29207) and other military lodging closed to the public, Camden / Lugoff, "
         "Sumter, Orangeburg, Newberry, Winnsboro, Aiken / Augusta, Florence, Rock Hill, and rural Gaston / Swansea "
         "/ Pelion / Eastover are not absorbed. A property whose own page states one of their postal codes is OUTSIDE, "
         "however it is named. Apartment communities, student housing, corporate housing, individual vacation "
         "rentals, Airbnb / Vrbo inventory, assisted living and private residences are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    adjudications = OrderedDict([
        ("West Columbia / Cayce / CAE", OrderedDict([
            ("decision", "CORE -- two corridors: west-columbia-cayce (29169 / 29033) and cae-airport (29170 / 29172)"),
            ("why",
             "The river towns across the Gervais Street and Blossom Street bridges are a ten-minute drive from the "
             "Vista and host the I-26 / US-1 and Knox Abbott hotel clusters; Columbia Metropolitan Airport and its "
             "Airport Boulevard hotels sit in West Columbia 29170. Both are admitted, each under its own mailing "
             "municipalities, never relabelled 'Columbia'."),
        ])),
        ("Lexington", OrderedDict([
            ("decision", "CORE (lexington: 29072 / 29073 / 29071)"),
            ("why", "The Town of Lexington's Sunset Boulevard and US-1 / I-20 exit 58 hotels serve Lake Murray, "
                    "Lexington Medical Center and west-side business travel; admitted as its own corridor."),
        ])),
        ("Blythewood", OrderedDict([
            ("decision", "CORRIDOR (blythewood: 29016)"),
            ("why", "The I-77 exit 27 cluster serves north-side business (Scout Motors, Blythewood industrial parks) and "
                    "the Charlotte approach, fifteen minutes from Killian Road."),
        ])),
        ("Chapin", OrderedDict([
            ("decision", "FRINGE (chapin: 29036)"),
            ("why", "The I-26 exit 91 town on Lake Murray's north shore sits twenty minutes from Harbison; its lodging "
                    "is small and town-scale, admitted as fringe."),
        ])),
        ("Elgin", OrderedDict([
            ("decision", "FRINGE (elgin: 29045)"),
            ("why", "Spears Creek Church Road (I-20 exit 82) is the next exit past Clemson Road and its hotels serve "
                    "Fort Jackson and Sandhills travellers; admitted as fringe. Lugoff and Camden beyond are refused."),
        ])),
        ("Gaston / Swansea / Pelion", OrderedDict([
            ("decision", "OUTSIDE -- evaluated carefully"),
            ("why", "Rural southern Lexington County with no hotel core; a traveller to Columbia sleeps in Cayce, West "
                    "Columbia or Lexington. A single legitimate property would be an explicit-hotel admission."),
        ])),
        ("Fort Jackson", OrderedDict([
            ("decision", "Installation ZIP 29207 OUTSIDE (MILITARY_NONPUBLIC); the commercial gate corridors admitted "
                         "(fort-jackson-forest-acres 29206 / 29209, northeast-two-notch 29223, sandhills 29229)"),
            ("why", MILITARY_WHY),
        ])),
        ("Dentsville / St. Andrews / Seven Oaks", OrderedDict([
            ("decision", "Inside the admitted CORE corridors (Dentsville: northeast-two-notch 29223; St. Andrews and "
                         "Seven Oaks: st-andrews-bush-river 29210)"),
            ("why", "Unincorporated Richland and Lexington county communities mailed as Columbia; reported as overlays."),
        ])),
        ("Camden / Sumter / Orangeburg / Newberry / Aiken / Augusta / Florence / Rock Hill", OrderedDict([
            ("decision", "OUTSIDE by name (order: do not automatically absorb)"),
            ("why", "Each is a materially separate traveller market 30-70 miles away with its own lodging core."),
        ])),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 + 3 + 4 -- Columbia multi-core geography, fringe adjudications, corridor model and Fort Jackson rule"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-15"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Columbia's turn in the serialized release "
         "queue against the then-current live parent."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("city_model",
         "Every corridor names the mailing municipalities its postal codes carry (CITY_OF_CORRIDOR), so every "
         "admitted hotel keeps its own town: Columbia, Forest Acres, Irmo, West Columbia, Cayce, Lexington, "
         "Blythewood, Chapin or Elgin."),
        ("travel_market",
         "Columbia's lodging cores (downtown / Vista / USC / Five Points, north Columbia's medical district, the Fort "
         "Jackson gate corridors, Northeast / Two Notch, Sandhills / Clemson Road, St. Andrews / Bush River, Harbison / "
         "Irmo, West Columbia / Cayce, the CAE airport and Lexington), Blythewood on I-77 and the fringe interchange "
         "towns a Columbia traveller sleeps in by choice (Chapin, Elgin)."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("fringe_adjudications", adjudications),
        ("corridor_page_evaluations", OrderedDict([
            ("Downtown / Vista", "SEPARATE CORRIDOR (downtown-vista-usc: 29201 / 29208 / 29205), with The Vista, Main "
                                 "Street, USC and Five Points as overlays."),
            ("USC / Five Points", "OVERLAY inside downtown-vista-usc -- the campus (29208) and Five Points (29205) "
                                  "border the Vista and carry too few hotels of their own for a page."),
            ("Prisma Health / medical", "SEPARATE CORRIDOR (north-columbia-medical: 29203 / 29204) for Prisma Health "
                                        "Richland and north Columbia; Prisma Health Baptist sits downtown (overlay)."),
            ("Fort Jackson", "SEPARATE CORRIDOR (fort-jackson-forest-acres: 29206 / 29209); the installation itself "
                             "is OUTSIDE (29207)."),
            ("Northeast / Two Notch", "SEPARATE CORRIDOR (29223)."),
            ("Sandhills / Clemson Road", "SEPARATE CORRIDOR (29229), Killian Road as an overlay."),
            ("Harbison / Irmo", "SEPARATE CORRIDOR (29212 / 29063 / 29002)."),
            ("West Columbia / Cayce", "SEPARATE CORRIDOR (29169 / 29033)."),
            ("CAE Airport", "SEPARATE CORRIDOR (29170 / 29172, and West Columbia's PO-box ZIP 29171 where a property's own page prints it)."),
            ("Lexington", "SEPARATE CORRIDOR (29072 / 29073)."),
            ("I-20", "OVERLAY across lexington, st-andrews-bush-river, north-columbia-medical, northeast-two-notch, "
                     "sandhills-clemson-road and elgin -- an interstate crosses the postal partition, so it is reported, "
                     "never a page of its own."),
            ("I-26", "OVERLAY across chapin, harbison-irmo, st-andrews-bush-river, west-columbia-cayce and cae-airport."),
            ("I-77", "OVERLAY across blythewood, sandhills-clemson-road, northeast-two-notch, fort-jackson-forest-acres "
                     "and west-columbia-cayce (Cayce terminus)."),
        ])),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]), ("name", c["name"]),
            ("geography_class", c["geography_class"]),
            ("city", CITY_OF[c["slug"]]),
            ("mailing_municipalities", sorted(CITY_OF_CORRIDOR[c["slug"]])),
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
         "Six cells observe the Fort Jackson installation, Lugoff / Camden, Gaston / Swansea, Eastover, the Ridgeway "
         "approach and Little Mountain. They admit nothing."),
        ("military_lodging_rule", MILITARY_WHY + " Ordinary publicly bookable commercial hotels serving Fort Jackson "
                                                "travellers are admitted on their own postal code."),
        ("non_hotel_rule",
         "The census admits hotels, motels, inns, boutique and historic hotels, extended-stay hotels and qualifying "
         "public lodging establishments operated as lodging businesses: bookable nightly rooms or suites sold to the "
         "public under one establishment name, with an official property page and an on-site hotel operation. It "
         "NEVER admits: ordinary apartment communities or individual apartments; student apartments and university "
         "dormitories; corporate-housing and furnished-apartment portfolios; individual houses rented whole; Airbnb / "
         "Vrbo-style listings; assisted-living properties; private residences; and military lodging closed to the "
         "public. Campgrounds, RV parks and state-park cabins are NON_LODGING."),
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
    if corridor_slug == "downtown-vista-usc":
        return coverage_area(lat, lng, ("The Vista / Convention Center", "Main Street / State House",
                                        "University of South Carolina", "Five Points / Devine Street")) or \
            "Downtown Columbia"
    if corridor_slug == "north-columbia-medical":
        return coverage_area(lat, lng, ("Prisma Health Richland", "I-20 / North Main")) or "North Columbia"
    if corridor_slug == "fort-jackson-forest-acres":
        if re.search(r"\b(garners ferry|fort jackson|shop|bluff|atlas)\b", st, re.I):
            return "Garners Ferry / Fort Jackson Blvd"
        return coverage_area(lat, lng, ("Forest Drive / I-77 (Fort Jackson gate)", "Garners Ferry / Fort Jackson Blvd")) \
            or "Forest Drive / I-77 (Fort Jackson gate)"
    if corridor_slug == "northeast-two-notch":
        return coverage_area(lat, lng, ("Two Notch / I-77 exit 17", "Dentsville / Decker Blvd")) or \
            "Two Notch / I-77 exit 17"
    if corridor_slug == "sandhills-clemson-road":
        if re.search(r"\bkillian\b|\bfarrow\b", st, re.I):
            return "Killian Road / I-77 exit 22"
        return "Clemson Road / I-20 exit 80"
    if corridor_slug == "st-andrews-bush-river":
        if re.search(r"\bgreystone|stoneridge|riverbanks\b", st, re.I):
            return "Greystone / Riverbanks"
        if re.search(r"\bst\.? andrews\b", st, re.I):
            return "St. Andrews Road"
        return coverage_area(lat, lng, ("Bush River Road / I-20 / I-26", "Greystone / Riverbanks", "St. Andrews Road")) \
            or "Bush River Road / I-20 / I-26"
    if corridor_slug == "harbison-irmo":
        if re.search(r"\bpiney grove\b", st, re.I):
            return "Piney Grove Road / I-26"
        return coverage_area(lat, lng, ("Harbison Blvd / I-26", "Piney Grove Road / I-26", "Irmo")) or "Harbison Blvd / I-26"
    if corridor_slug == "west-columbia-cayce":
        return coverage_area(lat, lng, ("Knox Abbott / Cayce", "I-26 / US-1 (exit 111)")) or "West Columbia / Cayce"
    if corridor_slug == "cae-airport":
        return "CAE Airport / Airport Blvd (exit 113)"
    return {"lexington": "Lexington Sunset Blvd", "blythewood": "Blythewood", "chapin": "Chapin",
            "elgin": "Elgin"}.get(corridor_slug)


def normalize_municipality(city):
    muni = " ".join((city or "").lower().replace(".", " ").replace(",", " ").split())
    return MUNICIPALITY_SPELLINGS.get(muni, muni)


def municipality_area(city):
    """The named city a property's own stated municipality reports under, or None."""
    muni = normalize_municipality(city)
    return {c: c.title() for cities in CITY_OF_CORRIDOR.values() for c in cities}.get(muni)


def is_future_submarket(postal, municipality=None):
    """No future submarket is preserved by this order."""
    return False


def is_military_postal(postal):
    return (postal or "").strip()[:5] in OUTSIDE[0][2]


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
