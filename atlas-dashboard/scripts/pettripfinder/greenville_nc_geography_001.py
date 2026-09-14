"""PTF-GREENVILLE-NC-PARALLEL-SOURCE-READY-001 -- Phase 2: the Greenville / ECU / Pitt County travel market.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Greenville, North Carolina traveler lodging market -- downtown
Greenville and East Carolina University, the ECU Health Medical Center / Brody
School of Medicine district on Stantonsburg Road, the Greenville Convention
Center and the SW Greenville Boulevard / Memorial Drive (US-13 / NC-11)
commercial hotel concentration, and the Pitt-Greenville Airport (PGV) corridor
-- stated as an explicit four-way rule (CORE / CORRIDOR / FRINGE / OUTSIDE)
before a single hotel is discovered, so no property is admitted or refused
after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

A TRAVEL MARKET, NOT CITY LIMITS
--------------------------------
Greenville's hotel demand is East Carolina University (move-in, graduation,
athletics), ECU Health Medical Center (the region's tertiary hospital: patients'
families, clinical rotations, travelling clinicians), the convention centre and
US-264 / US-13 through traffic. Its lodging sits in two postal codes:

* 27834 carries the Greenville Convention Center and SW Greenville Boulevard,
  Memorial Drive (US-13) north and south, the ECU Health / Brody medical
  district on Stantonsburg Road and Arlington Boulevard, Pitt-Greenville
  Airport, north Greenville and unincorporated Pactolus.
* 27858 carries downtown Greenville, East Carolina University's main campus,
  Evans Street, Charles Boulevard, Fire Tower Road, Greenville Boulevard east
  and the south-east of the city.

Winterville (28590) is contiguous with south Greenville on Memorial Drive /
NC-11 and sells as "Greenville": CORRIDOR. Ayden (28513) is NC-11 ten miles
south and Simpson (27879) is the US-264 edge east of the city: FRINGE, each its
own corridor so a fringe property never reports as core.

THE FOUR CLASSES
----------------
CORE       Convention Center / Memorial Drive / Medical District / PGV Airport
           (27834); Downtown / ECU / Charles Boulevard / Fire Tower (27858).
CORRIDOR   Winterville / NC-11 (28590).
FRINGE     Ayden (28513); Simpson (27879).
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight -- Farmville, Grifton, Grimesland, Bethel, Fountain,
           Kinston, Washington, Tarboro, Williamston, Rocky Mount, Wilson, New
           Bern, and Greenville, South Carolina.

WHY WASHINGTON, KINSTON, ROCKY MOUNT, WILSON, TARBORO AND WILLIAMSTON ARE NOT
---------------------------------------------------------------------------
Each is its own town with its own hotel cluster, twenty to forty miles out, and
each is a plausible future market of its own: Washington (Beaufort County, the
Pamlico River), Kinston (Lenoir County, US-70), Rocky Mount and Wilson (I-95),
Tarboro and Williamston (US-64). A traveller to ECU or ECU Health does not sleep
there by choice. Farmville (US-264 west) and Grifton (NC-11 south, Lenoir /
Pitt line) are small separate towns whose few properties are not Greenville
inventory. US-264 or NC-11 alone admits nothing. A single legitimate exception
is admitted by identity through ``explicit_hotel_admissions`` -- never by
widening a ZIP.

GREENVILLE, SOUTH CAROLINA
--------------------------
A much larger Greenville exists in South Carolina (ZIPs 296xx). Every brand
roster names it "Greenville" too. A route or listing that does not carry a
North Carolina marker is not a lead, and a page stating a 296xx postal code or
the state SC is OUTSIDE however it is named.

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the admitted ZIPs -- it covers Farmville,
Grifton, Kinston, Washington, Tarboro and Williamston deliberately -- so this
order classifies those properties on evidence rather than being blind to them.
Rocky Mount and Wilson lie west of the box on I-95; they are refused by name.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
Greenville is built while production deployment is unavailable and two other
markets (Fayetteville, then Jacksonville) must go live first. This order
therefore writes the market document to the zone's PROPOSED path, never to the
registry's ``markets/<id>.json``: the registry does not see Greenville, and the
later registration order copies the reviewed document into place.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/greenville_nc.json
  launch_packages/pettripfinder/markets/proposed/greenville-nc.json
  launch_packages/pettripfinder/markets/reports/greenville_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/greenville_nc_corridor_registry_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-GREENVILLE-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "greenville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                          "greenville_nc.json")
#: REGISTERED by PTF-GREENVILLE-NC-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002 against the Fayetteville-live parent. The source-ready
#: order wrote markets/proposed/greenville-nc.json (kept as history).
SHARD_OUT = os.path.join(PKG, "markets", "greenville-nc.json")
REPORT_OUT = os.path.join(REPORTS, "greenville_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "greenville_nc_corridor_registry_001.json")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, postal codes, description)
CORRIDORS = [
    (
        "convention-center-medical-district", "Convention Center / Memorial Drive / Medical District / PGV Airport",
        "Convention Center & Medical District", "CORE",
        # 27833, 27835 and 27836 are Greenville's PO-box-only postal codes. They name no
        # street, but a property's own page sometimes prints one (Microtel's own Wyndham
        # page states 450 Moye Boulevard with 27835). They are Greenville and nothing
        # else, so they are claimed here rather than refusing a Greenville building for
        # its mailing ZIP; the corridor is the one that holds every building such a page
        # has been seen to describe.
        ["27834", "27833", "27835", "27836"],
        "The Greenville Convention Center and SW Greenville Boulevard, Memorial Drive (US-13), the "
        "ECU Health Medical Center / Brody School of Medicine district on Stantonsburg Road and "
        "Arlington Boulevard, Pitt-Greenville Airport (PGV), north Greenville and Pactolus (plus "
        "Greenville's PO-box postal codes 27833, 27835 and 27836).",
    ),
    (
        "downtown-ecu", "Downtown / ECU / Charles Boulevard / Fire Tower", "Downtown & ECU", "CORE",
        ["27858"],
        "Downtown Greenville, East Carolina University's main campus, Evans Street, Charles "
        "Boulevard, Fire Tower Road, Greenville Boulevard east and south-east Greenville.",
    ),
    (
        "winterville", "Winterville / NC-11", "Winterville", "CORRIDOR",
        ["28590"],
        "Winterville on Memorial Drive / NC-11, contiguous with south Greenville.",
    ),
    (
        "ayden", "Ayden", "Ayden", "FRINGE",
        ["28513"],
        "Ayden on NC-11 ten miles south of Greenville.",
    ),
    (
        "simpson", "Simpson", "Simpson", "FRINGE",
        ["27879"],
        "Simpson on the US-264 edge east of Greenville.",
    ),
]

#: Municipalities refused INSIDE an admitted postal code. Matched on the
#: property's OWN stated address municipality (normalised, case-insensitive).
#: Greenville's admitted postal codes are not shared with a refused town, so the
#: list is empty; the mechanism stays so a later ruling adds a row, never a ZIP.
MUNICIPALITY_REFUSALS = []

#: Spellings of a refused municipality that sources actually print.
MUNICIPALITY_SPELLINGS = {}

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Farmville", "NC", ["27828"],
     "US-264 west, its own small town fifteen miles out; not Greenville traveler inventory; evaluated and refused."),
    ("Grifton", "NC", ["28530"],
     "NC-11 south on the Pitt / Lenoir line; its own small town; evaluated and refused."),
    ("Grimesland / Chocowinity", "NC", ["27837", "27817"],
     "NC-33 east toward Washington; no Greenville hotel corridor; evaluated and refused."),
    ("Bethel / Fountain / Stokes / Robersonville", "NC", ["27812", "27829", "27884", "27871"],
     "Small Pitt / Martin County towns; evaluated and refused."),
    ("Kinston", "NC", ["28501", "28504"],
     "Lenoir County on US-70, twenty-five miles south; its own hotel cluster and a plausible future market; evaluated and refused."),
    ("Washington", "NC", ["27889"],
     "Beaufort County on the Pamlico River, twenty miles east; its own hotel cluster and a plausible future market; evaluated and refused."),
    ("Tarboro", "NC", ["27886"],
     "Edgecombe County on US-64, twenty-five miles north; evaluated and refused."),
    ("Williamston", "NC", ["27892"],
     "Martin County on US-17 / US-64, twenty-five miles north-east; evaluated and refused."),
    ("Rocky Mount", "NC", ["27801", "27803", "27804"],
     "I-95 / US-64, forty miles north-west; its own market; refused by name (west of the observation box)."),
    ("Wilson", "NC", ["27893", "27896"],
     "I-95 / US-264, forty miles west; its own market; refused by name (west of the observation box)."),
    ("Snow Hill / La Grange", "NC", ["28580", "28551"],
     "Greene / Lenoir County towns south-west; evaluated and refused."),
    ("New Bern", "NC", ["28560", "28562"],
     "Craven County, its own market; evaluated and refused."),
]

#: A 296xx postal code is Greenville, SOUTH CAROLINA.
SOUTH_CAROLINA_GREENVILLE_PREFIX = "296"

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the refused neighbours so this order classifies them on evidence.
CELLS = [
    ("downtown-ecu", "Greenville", "Downtown Greenville / East Carolina University", 35.607, -77.366, 2500, True),
    ("medical-district", "Greenville", "ECU Health Medical Center / Brody / Stantonsburg Road", 35.607, -77.405, 2500, True),
    ("convention-center", "Greenville", "Greenville Convention Center / SW Greenville Blvd / Memorial Drive", 35.580, -77.390, 3000, True),
    ("charles-fire-tower", "Greenville", "Charles Blvd / Fire Tower Road / Evans Street south", 35.565, -77.360, 3000, True),
    ("pgv-airport", "Greenville", "Pitt-Greenville Airport / north Memorial Drive", 35.635, -77.385, 3000, True),
    ("winterville", "Winterville", "Winterville / NC-11", 35.529, -77.401, 4000, True),
    ("ayden", "Ayden", "Ayden / NC-11", 35.473, -77.415, 4000, True),
    ("simpson", "Simpson", "Simpson / US-264 east", 35.575, -77.278, 3000, True),
    # observation only -- refused neighbours, seen so they can be classified
    ("obs-farmville", "Farmville", "Farmville / US-264 west -- OBSERVATION ONLY", 35.595, -77.585, 5000, False),
    ("obs-grifton", "Grifton", "Grifton -- OBSERVATION ONLY", 35.373, -77.437, 4000, False),
    ("obs-kinston", "Kinston", "Kinston / US-70 -- OBSERVATION ONLY", 35.262, -77.582, 7000, False),
    ("obs-washington", "Washington", "Washington / US-17 -- OBSERVATION ONLY", 35.547, -77.052, 6000, False),
    ("obs-tarboro", "Tarboro", "Tarboro / US-64 -- OBSERVATION ONLY", 35.897, -77.536, 6000, False),
    ("obs-williamston", "Williamston", "Williamston / US-17 -- OBSERVATION ONLY", 35.855, -77.056, 6000, False),
]

BOUNDS = {
    "min_lat": 35.20,
    "max_lat": 35.95,
    "min_lng": -77.72,
    "max_lng": -76.98,
}


def build():
    corridors = []
    seen_zip = {}
    for order, (slug, name, area, klass, zips, desc) in enumerate(CORRIDORS, start=1):
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Greenville" % name),
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
            ("state_code", "NC"),
            ("geography_class", klass),
        ]))
    outside_zips = {z for _m, _s, zs, _w in OUTSIDE for z in zs}
    overlap = outside_zips & set(seen_zip)
    if overlap:
        raise SystemExit("postal codes both admitted and refused: %s" % sorted(overlap))
    for z, _muni, _why in MUNICIPALITY_REFUSALS:
        if z not in seen_zip:
            raise SystemExit("a municipality refusal names %s, which no corridor admits" % z)

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)),
        ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
        ("state_code", "NC"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Greenville, NC / ECU / ECU Health visitor market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 35.598, "lng": -77.375}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It covers Pitt County's lodging towns "
             "and deliberately reaches beyond them -- west to Farmville, south to Grifton and "
             "Kinston, east to Washington and north to Tarboro and Williamston -- so that " +
             WORK_ORDER + " classifies those properties on evidence instead of being blind to "
             "them. Admission is decided by the market contract's corridor registry over the "
             "property's OWN postal code, never by this box."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision (~3 decimal places) approximate "
         "reference points. They are seed points for bounded-radius queries only; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A university / medical / convention travel market: the Convention "
         "Center / Memorial Drive / Medical District / PGV Airport postal code and the Downtown / "
         "ECU postal code are CORE; Winterville is CORRIDOR; Ayden and Simpson are FRINGE. "
         "Farmville, Grifton, Kinston, Washington, Tarboro and Williamston are OBSERVED and "
         "REFUSED; Rocky Mount, Wilson, New Bern and Greenville SC are named and REFUSED."),
        ("scope_disclosure",
         "%d bounded cells: %d admitting and %d observation-only." % (
             len(cells), sum(1 for c in cells if c["admitting"]),
             sum(1 for c in cells if not c["admitting"]))),
        ("explicit_hotel_admissions", OrderedDict([
            ("_what_this_is",
             "The explicit-hotel mechanism, so a single legitimate fringe property never "
             "becomes a reason to widen a municipality or a postal code. Empty at authoring "
             "time."),
            ("admissions", []),
        ])),
        ("cells", cells),
    ])

    shard = OrderedDict([
        ("schema", "ptf-market/1.1"),
        ("market_id", MARKET_ID),
        ("market_name", "Greenville, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Greenville"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Greenville, North Carolina (ECU & ECU Health) | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Greenville, North Carolina -- near East Carolina "
         "University, ECU Health Medical Center, the Greenville Convention Center and "
         "Pitt-Greenville Airport -- plus Winterville and Ayden, with real pet fees and policies "
         "read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official "
         "website."),
        ("navigation_label", "Greenville NC"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, "
         "joined to the corridor registry. A university / medical / convention travel market: "
         "the Convention Center / Medical District / PGV Airport postal code (27834) and the "
         "Downtown / ECU postal code (27858) are CORE. Nothing else admits a property: not a "
         "brand's name for it, not an 'ECU' or 'Medical Center' marketing name, not a map pin, "
         "not a vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). "
         "Every admitted lodging ZIP is claimed by exactly one corridor."),
        ("_census_membership_note",
         "Farmville, Grifton, Kinston, Washington, Tarboro, Williamston, Rocky Mount, Wilson and "
         "New Bern are not absorbed, and Greenville, South Carolina is a different city. A "
         "property whose own page states one of their postal codes is OUTSIDE, however it is "
         "named."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Greenville / ECU / ECU Health travel-market geography"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-13"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "REGISTERED: the market document is written to the registry's markets/<id>.json by "
         "PTF-GREENVILLE-NC-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002 against the Fayetteville-live parent (the founder moved "
         "Greenville ahead of Jacksonville). The source-ready order's markets/proposed/ copy is history."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the "
         "corridor registry. Nothing else admits a property."),
        ("travel_market",
         "Greenville proper plus contiguous Winterville and the NC-11 / US-264 edge towns a "
         "visitor to East Carolina University, ECU Health Medical Center or the Greenville "
         "Convention Center sleeps at. It represents university travel (move-in, graduation, "
         "athletics), medical travel (patients' families, rotations, travelling clinicians), "
         "convention and business travel, PGV air travel and US-264 / US-13 through traffic."),
        ("classes", OrderedDict([
            ("CORE", "Convention Center / Memorial Drive / ECU Health medical district / PGV Airport / Pactolus (27834, plus Greenville's PO-box postal codes 27833 / 27835 / 27836);Downtown / ECU / Charles Boulevard / Fire Tower (27858)."),
            ("CORRIDOR", "Winterville / NC-11 (28590)."),
            ("FRINGE", "Ayden (28513); Simpson (27879)."),
            ("OUTSIDE", "Everything else, refused by name with its postal codes, including Farmville, Grifton, Kinston, Washington, Tarboro, Williamston, Rocky Mount, Wilson, New Bern and Greenville, South Carolina (296xx)."),
        ])),
        ("municipality_refusals_inside_shared_postal_codes", [OrderedDict([
            ("postal_code", z), ("municipality", m), ("why", w)]) for z, m, w in MUNICIPALITY_REFUSALS]),
        ("greenville_south_carolina_rule",
         "A route, listing or page naming 'Greenville' without a North Carolina marker is not a "
         "lead. A page stating a 296xx postal code or the state SC is Greenville, South Carolina "
         "and is OUTSIDE."),
        ("evaluated_inclusions", OrderedDict([
            ("Greenville", "ADMITTED (CORE) -- every Greenville lodging ZIP (27834, 27858) is claimed by one corridor."),
            ("Downtown Greenville", "ADMITTED (CORE, 27858)."),
            ("East Carolina University / ECU", "ADMITTED (CORE, 27858) -- main campus; the ECU Health Sciences campus is in 27834, also CORE."),
            ("ECU Health / medical district", "ADMITTED (CORE, 27834) -- ECU Health Medical Center and the Brody School of Medicine on Stantonsburg Road."),
            ("Greenville Convention Center / commercial hotel concentration", "ADMITTED (CORE, 27834) -- SW Greenville Boulevard and Memorial Drive."),
            ("Pitt-Greenville Airport / PGV corridor", "ADMITTED (CORE, 27834) -- Airport Road and north Memorial Drive."),
            ("Winterville", "ADMITTED (CORRIDOR, 28590) -- contiguous with south Greenville on Memorial Drive / NC-11."),
            ("Ayden", "ADMITTED (FRINGE, 28513) -- NC-11 ten miles south; never CORE."),
            ("Simpson", "ADMITTED (FRINGE, 27879) -- the US-264 edge east of the city; never CORE."),
            ("Pactolus", "ADMITTED (CORE) -- unincorporated on US-264 east; its addresses carry Greenville's 27834. No separate lodging corridor."),
            ("Farmville", "OUTSIDE (27828) -- its own town on US-264 west."),
            ("Grifton", "OUTSIDE (28530) -- its own town on NC-11 south."),
            ("Kinston", "OUTSIDE (28501, 28504) -- Lenoir County; plausible future market."),
            ("Washington, NC", "OUTSIDE (27889) -- Beaufort County; plausible future market."),
            ("Tarboro", "OUTSIDE (27886) -- Edgecombe County."),
            ("Williamston", "OUTSIDE (27892) -- Martin County."),
            ("Rocky Mount", "OUTSIDE (27801, 27803, 27804) -- I-95; plausible future market."),
            ("Wilson", "OUTSIDE (27893, 27896) -- I-95; plausible future market."),
            ("Greenville, South Carolina", "OUTSIDE (296xx) -- a different city in another state."),
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
        ("coverage_areas_are_a_reporting_overlay",
         "The order asks for coverage by Downtown, ECU, ECU Health / medical district, the "
         "convention / commercial corridor, PGV Airport and Winterville. Four of those areas "
         "share postal code 27834 and two share 27858, so they cannot be membership corridors "
         "without inventing a boundary inside a ZIP. The accounting reports them as a "
         "NEAREST-ANCHOR overlay on each property's coordinates (COVERAGE_AREAS below); the "
         "overlay decides nothing about membership or corridor assignment."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Six cells observe Farmville, Grifton, Kinston, Washington, Tarboro and Williamston. "
         "They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotel / motel / inn / resort establishments operated as lodging "
         "businesses. Individual vacation homes, cottages and condos without normal hotel "
         "operation, Airbnb-style units, property-management listings, corporate "
         "furnished-apartment operators, student housing, RV parks / campgrounds and timeshare "
         "units are recorded as NON_LODGING exclusions, never admitted. A bed and breakfast is "
         "admitted only when it operates as an inn with bookable rooms on its own premises and an "
         "official site."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


#: Reporting overlay only (never membership): the areas the order asks coverage for,
#: each an anchor point and a radius. A property is reported in the NEAREST anchor
#: whose radius it falls inside, else in "elsewhere in its corridor".
COVERAGE_AREAS = [
    ("Downtown", 35.6125, -77.3715, 1.6),
    ("ECU", 35.6060, -77.3640, 1.6),
    ("ECU Health / medical district", 35.6080, -77.4040, 2.5),
    ("Convention / commercial corridor", 35.5840, -77.3860, 3.0),
    ("PGV Airport", 35.6350, -77.3850, 2.5),
    ("Winterville", 35.5290, -77.4010, 4.0),
]


def coverage_area(lat, lng):
    """The overlay area a coordinate reports under, or None. Reporting only."""
    import math
    if lat is None or lng is None:
        return None
    best = None
    for name, la, ln, r in COVERAGE_AREAS:
        dy = (lat - la) * 111.0
        dx = (lng - ln) * 111.0 * math.cos(math.radians(la))
        d = math.hypot(dx, dy)
        if d <= r and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def classify_postal(postal, municipality):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and
    municipality. The one membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = " ".join((municipality or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    if z.startswith(SOUTH_CAROLINA_GREENVILLE_PREFIX):
        return "OUTSIDE", None, "postal code %s is Greenville, SOUTH CAROLINA" % z
    for slug, _name, _area, klass, zips, _desc in CORRIDORS:
        if z in zips:
            for _rz, rmuni, why in MUNICIPALITY_REFUSALS:
                if rmuni.lower() == muni:
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
