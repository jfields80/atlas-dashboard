"""PTF-JACKSONVILLE-NC-PARALLEL-SOURCE-READY-001 -- Phase 2: the Jacksonville / Camp Lejeune travel market.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Jacksonville, North Carolina traveler lodging market -- the
Western Boulevard retail-hotel concentration, the Marine Boulevard / US-17
commercial corridor, the Lejeune Boulevard approach to Marine Corps Base Camp
Lejeune's main gate, the US-17 South approach to Marine Corps Air Station New
River, and the NC-24 Midway Park / Piney Green corridor -- stated as an explicit
four-way rule (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is
discovered, so no property is admitted or refused after the fact to make a
number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

Two admitted ZIPs are SHARED with a neighbouring tourism market whose
inventory this order must not absorb. For those two ZIPs, and only those, a
second, equally mechanical rule applies over the property's OWN stated
municipality (``municipality_refusals`` below):

* 28460 is Sneads Ferry AND North Topsail Beach. Sneads Ferry is the NC-172
  village at Camp Lejeune's Courthouse Bay / Stone Bay gate and is FRINGE; a
  property whose own address says North Topsail Beach is Topsail Island beach
  vacation inventory and is OUTSIDE.
* 28584 is Swansboro AND Cape Carteret / Cedar Point. Swansboro (Onslow County)
  is FRINGE; a property whose own address says Cape Carteret or Cedar Point is
  Carteret County Crystal Coast / Emerald Isle inventory and is OUTSIDE.

A TRAVEL MARKET, NOT CITY LIMITS
--------------------------------
Jacksonville's hotel inventory is driven by Marine Corps Base Camp Lejeune and
MCAS New River (PCS moves, boot-camp and school graduations, TDY, family
visits) and by US-17. The corridors therefore follow where those travelers
actually sleep:

* 28546 carries Western Boulevard, Jacksonville Mall, Gum Branch Road and the
  north side of Piney Green Road -- the city's largest hotel concentration.
* 28540 carries downtown Jacksonville, Marine Boulevard (US-17 Business), the
  US-17 bypass north, Lejeune Boulevard (NC-24) toward the Camp Lejeune main
  gate, the US-17 South approach to MCAS New River, Half Moon and Verona.
* 28544 Midway Park is the NC-24 strip at the Camp Lejeune main gate and the
  Piney Green Road junction; its hotels sell as "Camp Lejeune" / "Jacksonville".
* 28539 Hubert is NC-24 between Jacksonville and Swansboro, at the Bear Creek
  gate and the Camp Lejeune eastern training areas: CORRIDOR.
* 28460 Sneads Ferry, 28584 Swansboro and 28574 Richlands are small towns
  twelve to twenty-five miles out: FRINGE, each in its own corridor so a fringe
  property never reports as core.

THE FOUR CLASSES
----------------
CORE       Western Boulevard / Jacksonville Mall (28546); Downtown / Marine
           Boulevard / Lejeune Boulevard / US-17 / New River / Half Moon /
           Verona (28540); Midway Park / Camp Lejeune main gate (28544).
CORRIDOR   Hubert / NC-24 east (28539).
FRINGE     Sneads Ferry (28460, municipality Sneads Ferry only); Swansboro
           (28584, municipality Swansboro only); Richlands (28574).
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight -- including Camp Lejeune and MCAS New River on-base
           postal codes, North Topsail Beach / Topsail Island, Cape Carteret /
           Cedar Point / Emerald Isle, Wilmington's market and Hampstead.

THE MILITARY / GOVERNMENT LODGING RULE
--------------------------------------
Camp Lejeune's on-base postal codes (28542, 28547), MCAS New River (28545) and
Tarawa Terrace base housing (28543) are OUTSIDE. On-base lodging -- the Inns of
the Corps / Marine Corps lodging, transient and bachelor quarters, barracks,
Onslow Beach MWR cabins and campground -- requires installation access (a DoD
credential or a sponsored visitor pass) and is not bookable by the general
traveling public under normal conditions. Any such property the census meets
is recorded as an explicit MILITARY_GOVERNMENT_NONPUBLIC exclusion, never
admitted. A property whose NAME markets it to the military ("Camp Lejeune",
"New River", "Marine") but whose own address is an off-base commercial ZIP is
an ordinary public hotel and is admitted normally.

WHY WILMINGTON, TOPSAIL, THE CRYSTAL COAST AND NEW BERN ARE NOT
--------------------------------------------------------------
Wilmington is its own live PetTripFinder market and owns Hampstead-adjacent
Pender County only through its own registry; nothing here claims a Wilmington
ZIP. Topsail Island (Surf City, Topsail Beach, North Topsail Beach, Holly
Ridge's beach access) is a beach-vacation market dominated by rentals and
condos. Emerald Isle / Cape Carteret / Cedar Point is the Carteret County
Crystal Coast. Maysville (Jones County) and New Bern are their own stops. US-17
alone admits nothing. A single legitimate exception is admitted by identity
through ``explicit_hotel_admissions`` -- never by widening a ZIP.

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the admitted ZIPs -- it covers Camp Lejeune,
Topsail Island, Holly Ridge, Cape Carteret and Maysville deliberately -- so
this order classifies those properties on evidence rather than being blind to
them.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
Jacksonville is built while production deployment is unavailable and another
market (Fayetteville) must go live first. This order therefore writes the
market document to the zone's PROPOSED path, never to the registry's
``markets/<id>.json``: the registry does not see Jacksonville, and the later
registration order copies the reviewed document into place.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/jacksonville_nc.json
  launch_packages/pettripfinder/markets/proposed/jacksonville-nc.json
  launch_packages/pettripfinder/markets/reports/jacksonville_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/jacksonville_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-JACKSONVILLE-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "jacksonville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                          "jacksonville_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "jacksonville-nc.json")
REPORT_OUT = os.path.join(REPORTS, "jacksonville_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "jacksonville_nc_corridor_registry_001.json")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, postal codes, description)
CORRIDORS = [
    (
        "western-boulevard", "Western Boulevard / Jacksonville Mall", "Western Boulevard",
        "CORE",
        ["28546"],
        "Western Boulevard, Jacksonville Mall, Gum Branch Road and the north side of Piney "
        "Green Road -- Jacksonville's largest hotel concentration.",
    ),
    (
        "marine-boulevard-us-17", "Downtown / Marine Boulevard / US-17 / New River",
        "Marine Boulevard & US-17", "CORE",
        ["28540"],
        "Downtown Jacksonville, Marine Boulevard (US-17 Business), the US-17 bypass, Lejeune "
        "Boulevard toward the Camp Lejeune main gate, the US-17 South approach to MCAS New "
        "River, Half Moon and Verona.",
    ),
    (
        "midway-park-camp-lejeune", "Midway Park / Camp Lejeune Main Gate", "Midway Park",
        "CORE",
        ["28544"],
        "Midway Park and the NC-24 (Lejeune Boulevard) strip at Marine Corps Base Camp "
        "Lejeune's main gate and the Piney Green Road junction.",
    ),
    (
        "hubert-nc-24", "Hubert / NC-24 East", "Hubert", "CORRIDOR",
        ["28539"],
        "Hubert and NC-24 between Jacksonville and Swansboro, at Camp Lejeune's Bear Creek "
        "gate.",
    ),
    (
        "sneads-ferry", "Sneads Ferry", "Sneads Ferry", "FRINGE",
        ["28460"],
        "Sneads Ferry on NC-172 at Camp Lejeune's Courthouse Bay and Stone Bay gates. North "
        "Topsail Beach shares this postal code and is refused by municipality.",
    ),
    (
        "swansboro", "Swansboro", "Swansboro", "FRINGE",
        ["28584"],
        "Swansboro on NC-24 / US-17 Business at the White Oak River. Cape Carteret and Cedar "
        "Point share this postal code and are refused by municipality.",
    ),
    (
        "richlands", "Richlands", "Richlands", "FRINGE",
        ["28574"],
        "Richlands on US-258 / NC-24, twelve miles north-west of Jacksonville.",
    ),
]

#: Municipalities refused INSIDE an admitted, shared postal code. Matched on the
#: property's OWN stated address municipality (normalised, case-insensitive).
MUNICIPALITY_REFUSALS = [
    ("28460", "North Topsail Beach",
     "TOPSAIL_ISLAND_VACATION_MARKET: Topsail Island beach-vacation inventory (rentals, condos, "
     "oceanfront resorts) shares Sneads Ferry's postal code; not absorbed into the Jacksonville "
     "travel market."),
    ("28584", "Cape Carteret",
     "CRYSTAL_COAST_MARKET: Carteret County / Emerald Isle inventory shares Swansboro's postal code; "
     "not absorbed."),
    ("28584", "Cedar Point",
     "CRYSTAL_COAST_MARKET: Carteret County / Emerald Isle inventory shares Swansboro's postal code; "
     "not absorbed."),
]

#: Spellings of a refused municipality that sources actually print.
MUNICIPALITY_SPELLINGS = {
    "n topsail beach": "north topsail beach",
    "north topsail": "north topsail beach",
    "cape carteret nc": "cape carteret",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Marine Corps Base Camp Lejeune (on-base)", "NC", ["28542", "28547"],
     "MILITARY_GOVERNMENT_NONPUBLIC: on-base lodging (Inns of the Corps / Marine Corps lodging, transient and bachelor quarters, barracks, Onslow Beach MWR cabins and campground) requires installation access and is not bookable by the general traveling public under normal conditions; evaluated and refused."),
    ("Marine Corps Air Station New River (on-base)", "NC", ["28545"],
     "MILITARY_GOVERNMENT_NONPUBLIC: on-base; evaluated and refused."),
    ("Tarawa Terrace (base housing)", "NC", ["28543"],
     "MILITARY_GOVERNMENT_NONPUBLIC: Camp Lejeune family housing; no public lodging; evaluated and refused."),
    ("Topsail Island: Surf City / Topsail Beach / Holly Ridge", "NC", ["28445"],
     "TOPSAIL_ISLAND_VACATION_MARKET: beach-vacation inventory 20-30 mi south-west; the order forbids absorbing Topsail vacation inventory; evaluated and refused."),
    ("Hampstead / Rocky Point / Burgaw", "NC", ["28443", "28457", "28425"],
     "Pender County, the Wilmington side of US-17; not Jacksonville travel inventory; evaluated and refused."),
    ("Emerald Isle / Crystal Coast", "NC", ["28594", "28570", "28575", "28557", "28512"],
     "CRYSTAL_COAST_MARKET: Carteret County beach and Morehead City / Atlantic Beach / Newport inventory; evaluated and refused."),
    ("Stella / Peletier", "NC", ["28582"], "Carteret County west of the White Oak River; evaluated and refused."),
    ("Maysville / Pollocksville", "NC", ["28555", "28573"],
     "Jones County on US-17 north, its own small towns; US-17 alone admits nothing; evaluated and refused."),
    ("New Bern / Havelock", "NC", ["28560", "28562", "28532"],
     "Craven County, its own market (and MCAS Cherry Point's); evaluated and refused."),
    ("Beulaville / Chinquapin / Kenansville", "NC", ["28518", "28521", "28349"],
     "Duplin County north-west; evaluated and refused."),
    ("Wilmington (live PetTripFinder market)", "NC",
     ["28401", "28403", "28405", "28409", "28411", "28412", "28428", "28429", "28449", "28451", "28480"],
     "Owned by the registered wilmington-nc market; never claimed here."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the refused neighbours so this order classifies them on evidence.
CELLS = [
    ("western-blvd-mall", "Jacksonville", "Western Boulevard / Jacksonville Mall", 34.772, -77.395, 3500, True),
    ("western-blvd-north", "Jacksonville", "Western Boulevard north / Gum Branch Road", 34.795, -77.410, 3000, True),
    ("marine-blvd-downtown", "Jacksonville", "Downtown / Marine Boulevard", 34.752, -77.425, 3000, True),
    ("us-17-north", "Jacksonville", "US-17 bypass north / Half Moon", 34.815, -77.445, 4000, True),
    ("lejeune-blvd", "Jacksonville", "Lejeune Boulevard / NC-24 toward the main gate", 34.738, -77.385, 3000, True),
    ("new-river-us-17-south", "Jacksonville", "US-17 South / MCAS New River approach / Verona", 34.700, -77.455, 4500, True),
    ("piney-green", "Jacksonville", "Piney Green Road", 34.745, -77.335, 3500, True),
    ("midway-park", "Midway Park", "Midway Park / Camp Lejeune main gate", 34.720, -77.315, 3000, True),
    ("hubert", "Hubert", "Hubert / NC-24 east", 34.670, -77.225, 5000, True),
    ("swansboro", "Swansboro", "Swansboro", 34.690, -77.120, 4000, True),
    ("sneads-ferry", "Sneads Ferry", "Sneads Ferry / NC-172", 34.550, -77.395, 5000, True),
    ("richlands", "Richlands", "Richlands / US-258", 34.897, -77.545, 4000, True),
    # observation only -- refused neighbours, seen so they can be classified
    ("obs-camp-lejeune", "Camp Lejeune", "Camp Lejeune / MCAS New River on-base -- OBSERVATION ONLY", 34.640, -77.340, 9000, False),
    ("obs-topsail-island", "North Topsail Beach", "North Topsail Beach / Surf City / Holly Ridge -- OBSERVATION ONLY", 34.470, -77.500, 9000, False),
    ("obs-cape-carteret", "Cape Carteret", "Cape Carteret / Cedar Point / Emerald Isle west -- OBSERVATION ONLY", 34.690, -77.050, 6000, False),
    ("obs-maysville", "Maysville", "Maysville / US-17 north -- OBSERVATION ONLY", 34.905, -77.230, 6000, False),
]

BOUNDS = {
    "min_lat": 34.40,
    "max_lat": 35.02,
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Jacksonville" % name),
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
        ("market_name", "Jacksonville, NC / Camp Lejeune visitor market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 34.754, "lng": -77.430}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It covers Onslow County's lodging "
             "towns and deliberately reaches beyond them -- south-west to Topsail Island and Holly "
             "Ridge, east to Cape Carteret and north to Maysville -- so that " + WORK_ORDER +
             " classifies those properties on evidence instead of being blind to them. "
             "Admission is decided by the market contract's corridor registry over the "
             "property's OWN postal code (and, in the two shared ZIPs, its own municipality), "
             "never by this box."),
            ("_overlap_disclosure",
             "This box OVERLAPS Wilmington's committed observation box (33.84..34.58 N, "
             "-78.22..-77.48 W) in the rectangle 34.40..34.58 N x -77.72..-77.48 W, which holds "
             "Topsail Beach, Surf City and Holly Ridge. The overlap is deliberate and harmless: "
             "observation never admits, neither market's corridor registry claims 28445 or "
             "28443, and no Wilmington postal code is admitted here. A box that avoided the "
             "overlap would have to drop either Richlands or Sneads Ferry / North Topsail Beach "
             "from observation."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision (~3 decimal places) approximate "
         "reference points. They are seed points for bounded-radius queries only; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A military / US-17 travel market: Western Boulevard, downtown / Marine "
         "Boulevard / US-17 / New River and Midway Park are CORE; Hubert is CORRIDOR; Sneads "
         "Ferry, Swansboro and Richlands are FRINGE. Camp Lejeune and MCAS New River on-base, "
         "North Topsail Beach / Topsail Island, Cape Carteret / Cedar Point / Emerald Isle, "
         "Maysville and Wilmington are OBSERVED or named and REFUSED."),
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
        ("market_name", "Jacksonville, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Jacksonville"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Jacksonville & Camp Lejeune, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Jacksonville, Midway Park, the Camp Lejeune and New "
         "River area, Hubert, Swansboro, Sneads Ferry and Richlands, North Carolina, with real "
         "pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official "
         "website."),
        ("navigation_label", "Jacksonville NC"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, "
         "joined to the corridor registry. A military / US-17 travel market: Western Boulevard, "
         "downtown / Marine Boulevard / US-17 / New River and Midway Park are CORE. Nothing else "
         "admits a property: not a brand's name for it, not a 'Camp Lejeune' or 'New River' "
         "marketing name, not a map pin, not a vacation-rental listing, not a competitor "
         "directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). "
         "Every admitted lodging ZIP is claimed by exactly one corridor."),
        ("_census_membership_note",
         "Camp Lejeune and MCAS New River on-base lodging, North Topsail Beach and Topsail "
         "Island, Cape Carteret, Cedar Point, Emerald Isle, Maysville, Hampstead and Wilmington "
         "are not absorbed. A property whose own page states one of their postal codes -- or, in "
         "28460 / 28584, the municipality North Topsail Beach, Cape Carteret or Cedar Point -- "
         "is OUTSIDE, however it is named."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Jacksonville / Camp Lejeune travel-market geography"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-13"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to "
         "the registry's markets/<id>.json. Registration waits for the Fayetteville-live parent."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the "
         "corridor registry; in the two shared postal codes 28460 and 28584, also the property's "
         "own stated municipality. Nothing else admits a property."),
        ("travel_market",
         "Jacksonville proper plus Midway Park, Hubert and the small towns a Camp Lejeune / New "
         "River visitor sleeps at. It represents military travel (PCS moves, school and unit "
         "graduations, TDY, family visits), US-17 through traffic, the Western Boulevard retail "
         "cluster and downtown."),
        ("classes", OrderedDict([
            ("CORE", "Western Boulevard / Jacksonville Mall (28546); downtown / Marine Boulevard / Lejeune Boulevard / US-17 / New River / Half Moon / Verona (28540); Midway Park / Camp Lejeune main gate (28544)."),
            ("CORRIDOR", "Hubert / NC-24 east (28539)."),
            ("FRINGE", "Sneads Ferry (28460, municipality Sneads Ferry only); Swansboro (28584, municipality Swansboro only); Richlands (28574)."),
            ("OUTSIDE", "Everything else, refused by name with its postal codes, including Camp Lejeune / MCAS New River on-base (MILITARY_GOVERNMENT_NONPUBLIC), North Topsail Beach and Topsail Island, and Cape Carteret / Cedar Point / Emerald Isle."),
        ])),
        ("municipality_refusals_apply_in_every_admitted_postal_code",
         "A refused municipality is refused whatever admitted postal code a source prints beside it; "
         "the ZIP each is listed with below is the one it is KNOWN to share."),
        ("municipality_refusals_inside_shared_postal_codes", [OrderedDict([
            ("postal_code", z), ("municipality", m), ("why", w)]) for z, m, w in MUNICIPALITY_REFUSALS]),
        ("military_government_lodging_rule",
         "On-base lodging (Inns of the Corps / Marine Corps lodging, transient and bachelor "
         "quarters, barracks, Onslow Beach MWR cabins and campground) requires installation access "
         "and is not bookable by the general traveling public under normal conditions. Its postal "
         "codes (28542, 28543, 28545, 28547) are OUTSIDE, and any such property the census meets "
         "is an explicit MILITARY_GOVERNMENT_NONPUBLIC exclusion. Public commercial hotels whose "
         "names market them to Camp Lejeune or New River travelers are admitted normally by their "
         "own off-base postal code."),
        ("evaluated_inclusions", OrderedDict([
            ("Jacksonville", "ADMITTED (CORE) -- every Jacksonville lodging ZIP (28540, 28546) is claimed by one corridor."),
            ("Camp Lejeune commercial lodging corridors", "ADMITTED (CORE) -- Lejeune Boulevard in 28540 / 28546 and Midway Park 28544; on-base REFUSED as nonpublic."),
            ("MCAS New River commercial lodging corridor", "ADMITTED (CORE, 28540) -- US-17 South / Marine Boulevard; on-base 28545 REFUSED."),
            ("Western Boulevard / Jacksonville retail-hotel concentration", "ADMITTED (CORE, 28546)."),
            ("US-17 commercial lodging corridor", "ADMITTED (CORE, 28540) inside Jacksonville; US-17 north of Half Moon (Maysville, Jones County) and south of Verona (Holly Ridge / Hampstead) is OUTSIDE -- US-17 alone admits nothing."),
            ("Midway Park", "ADMITTED (CORE, 28544) -- the NC-24 strip at the Camp Lejeune main gate."),
            ("Piney Green", "ADMITTED (CORE) -- unincorporated; its lodging addresses carry 28546 or 28544, both CORE."),
            ("Half Moon", "ADMITTED (CORE) -- unincorporated north Jacksonville on US-17 / Gum Branch; 28540 / 28546."),
            ("Verona", "ADMITTED (CORE) -- unincorporated US-17 South at MCAS New River; 28540."),
            ("Hubert", "ADMITTED (CORRIDOR, 28539) -- NC-24 east at the Bear Creek gate."),
            ("Sneads Ferry", "ADMITTED (FRINGE, 28460) -- the Courthouse Bay / Stone Bay gate village; never CORE."),
            ("North Topsail Beach", "OUTSIDE -- Topsail Island beach-vacation inventory refused by municipality inside 28460."),
            ("Swansboro", "ADMITTED (FRINGE, 28584) -- Onslow County's White Oak River town; never CORE."),
            ("Cape Carteret / Cedar Point", "OUTSIDE -- Crystal Coast inventory refused by municipality inside 28584."),
            ("Richlands", "ADMITTED (FRINGE, 28574) -- US-258 twelve miles north-west; never CORE."),
            ("Holly Ridge / Surf City / Topsail Beach", "OUTSIDE (28445) -- Topsail Island vacation market."),
            ("Maysville", "OUTSIDE (28555) -- Jones County."),
            ("Emerald Isle", "OUTSIDE (28594) -- Crystal Coast."),
            ("Wilmington", "OUTSIDE -- a registered, live PetTripFinder market."),
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
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Four cells observe Camp Lejeune / MCAS New River on-base, Topsail Island, Cape Carteret "
         "and Maysville. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotel / motel / inn / resort establishments operated as lodging "
         "businesses. Individual vacation homes, cottages and condos without normal hotel "
         "operation, Airbnb-style units, property-management listings, corporate "
         "furnished-apartment operators, RV parks / campgrounds and timeshare units are recorded "
         "as NON_HOTEL_VACATION_RENTAL exclusions, never admitted. A bed and breakfast is admitted "
         "only when it operates as an inn with bookable rooms on its own premises and an official "
         "site."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


def classify_postal(postal, municipality):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and
    municipality. The one membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = " ".join((municipality or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    for slug, _name, _area, klass, zips, _desc in CORRIDORS:
        if z in zips:
            # A refused municipality is refused in EVERY admitted postal code, not
            # only the one it is known to share: the county tourism roster prints
            # a North Topsail Beach motel with Hubert's 28539.
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
