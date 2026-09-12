"""PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001 -- Phase 2: the Piedmont Triad travel market.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Greensboro - Winston-Salem - High Point traveler lodging market,
stated as an explicit four-way rule (CORE / CORRIDOR / FRINGE / OUTSIDE) before
a single hotel is discovered, so no property is admitted or refused after the
fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

A MULTI-CORE METRO
------------------
The Triad is not one downtown with suburbs. It is three independent city
centres -- Greensboro, Winston-Salem and High Point -- plus Kernersville between
them and Piedmont Triad International Airport (PTI / GSO) on the I-40 / I-73
spine west of Greensboro. Each core carries its own corridors; no property is
reported as "Greensboro" because it sits on I-40.

THE FOUR CLASSES
----------------
CORE       Greensboro (downtown / UNCG / Coliseum / Wendover-I-40 / Friendly and
           north-west Greensboro), Winston-Salem (downtown, Hanes Mall /
           Stratford, the Wake Forest University / University Parkway north
           side), High Point (with Jamestown), Kernersville, and the PTI
           airport corridor (27409 and Colfax 27235).
CORRIDOR   Guilford and Forsyth County approaches whose hotels are sold as
           Triad lodging: south and east Greensboro on I-85 / I-40 (27406,
           McLeansville 27301, Whitsett 27377), Clemmons and Lewisville on
           I-40 west of Winston-Salem, and Archdale / Trinity on I-85 / I-74
           south of High Point (27263 is shared by High Point and Archdale and
           is claimed once, here).
FRINGE     Oak Ridge / Summerfield (north-west Guilford) and northern Forsyth
           on US-52 (Rural Hall, Walkertown, Pfafftown, Tobaccoville).
           Admitted, each in its own corridor, so a fringe property never
           silently reports as a core.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight: Lexington and Thomasville (Davidson County, separate
           I-85 county-seat lodging clusters named for their own towns),
           Burlington / Graham / Mebane / Elon (Alamance County -- an I-40/I-85
           outlet and university cluster that is its own product), Asheboro
           (Randolph County seat, the NC Zoo product), Mocksville and Bermuda
           Run / Advance (Davie County), Reidsville, Eden, King and Yadkinville.

WHY NOT ABSORB LEXINGTON / THOMASVILLE / BURLINGTON / MEBANE
------------------------------------------------------------
Each lies on I-85 or I-40 and each is observed. None is absorbed because a
highway is not a market: their hotels are branded with their own town names
("Hampton Inn Burlington", "Holiday Inn Express Thomasville", "Comfort Inn
Lexington"), they sit 18-30 miles from the nearest Triad core, and the three
cores already carry the airport and interstate inventory a Triad traveler
books. A single legitimate exception is admitted by identity through
``explicit_hotel_admissions`` -- never by widening a ZIP.

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the admitted ZIPs -- it covers Lexington,
Thomasville, Burlington, Mebane, Asheboro and Mocksville deliberately -- so this
order classifies those properties on evidence rather than being blind to them.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/piedmont_triad_nc.json
  launch_packages/pettripfinder/markets/piedmont-triad-nc.json
  launch_packages/pettripfinder/markets/reports/piedmont_triad_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/piedmont_triad_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "piedmont-triad-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                          "piedmont_triad_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "piedmont-triad-nc.json")
REPORT_OUT = os.path.join(REPORTS, "piedmont_triad_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "piedmont_triad_nc_corridor_registry_001.json")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, postal codes, description)
CORRIDORS = [
    (
        "downtown-greensboro", "Downtown Greensboro / UNCG", "Downtown Greensboro", "CORE",
        ["27401", "27403", "27405"],
        "Elm Street, the Tanger Center, LeBauer Park, the Greensboro Science Center "
        "approach, UNC Greensboro and North Carolina A&T.",
    ),
    (
        "greensboro-coliseum-wendover", "Greensboro Coliseum / Wendover / I-40", "Coliseum",
        "CORE",
        ["27407"],
        "The Greensboro Coliseum Complex, High Point Road / Gate City Boulevard, "
        "Wendover Avenue, Big Tree Way and the I-40 / I-73 hotel cluster.",
    ),
    (
        "greensboro-friendly-northwest", "Friendly Center / Northwest Greensboro",
        "Northwest Greensboro", "CORE",
        ["27408", "27410", "27455"],
        "Friendly Center, Wendover and Battleground Avenues, Guilford College and the "
        "north-west Greensboro loop.",
    ),
    (
        "pti-airport", "PTI Airport / Airport Corridor", "PTI Airport", "CORE",
        ["27409", "27235"],
        "Piedmont Triad International Airport (PTI / GSO), Regional Road, Sandy Ridge "
        "Road, Chimney Rock Road, and the Colfax side of I-40 at the airport.",
    ),
    (
        "high-point", "High Point / Jamestown", "High Point", "CORE",
        ["27260", "27262", "27265", "27282"],
        "Downtown High Point and the International Home Furnishings Market district, "
        "North Main Street, the Palladium / Wendover Avenue cluster, High Point "
        "University and Jamestown.",
    ),
    (
        "downtown-winston-salem", "Downtown Winston-Salem", "Downtown Winston-Salem", "CORE",
        ["27101", "27107", "27127"],
        "Downtown Winston-Salem, the Benton Convention Center, Innovation Quarter, Old "
        "Salem, Winston-Salem State University and the US-52 / I-40 Business south side.",
    ),
    (
        "winston-salem-hanes-mall", "Hanes Mall / Stratford Road", "Hanes Mall", "CORE",
        ["27103", "27104"],
        "Hanes Mall Boulevard, Stratford Road, the Wake Forest Baptist / Atrium Health "
        "medical campus and the I-40 west side of Winston-Salem.",
    ),
    (
        "winston-salem-university-north", "University Parkway / North Winston-Salem",
        "North Winston-Salem", "CORE",
        ["27105", "27106"],
        "Wake Forest University, Truist Field, the LJVM Coliseum, University Parkway and "
        "the north side of Winston-Salem.",
    ),
    (
        "kernersville", "Kernersville", "Kernersville", "CORE",
        ["27284"],
        "Kernersville on the I-40 / Business 40 spine between Winston-Salem and "
        "Greensboro, and the Novant Health Kernersville campus.",
    ),
    (
        "greensboro-south-east-i85", "South and East Greensboro / I-85", "East Greensboro",
        "CORRIDOR",
        ["27406", "27301", "27377"],
        "South Elm-Eugene Street and Randleman Road on I-85, McLeansville and Whitsett on "
        "the I-40 / I-85 eastern approach.",
    ),
    (
        "clemmons-lewisville", "Clemmons / Lewisville / I-40 West", "Clemmons", "CORRIDOR",
        ["27012", "27023"],
        "Clemmons and Lewisville on I-40 west of Winston-Salem, the Tanglewood Park "
        "approach.",
    ),
    (
        "archdale-trinity", "Archdale / Trinity / I-85 South", "Archdale", "CORRIDOR",
        ["27263", "27370"],
        "Archdale and Trinity on I-85 / I-74 south of High Point.",
    ),
    (
        "oak-ridge-summerfield", "Oak Ridge / Summerfield", "Oak Ridge", "FRINGE",
        ["27310", "27358"],
        "Oak Ridge and Summerfield on NC-68 / US-220 north-west of Greensboro.",
    ),
    (
        "north-forsyth-us52", "Northern Forsyth / US-52", "Northern Forsyth", "FRINGE",
        ["27045", "27051", "27040", "27050"],
        "Rural Hall, Walkertown, Pfafftown and Tobaccoville on US-52 and NC-66 north of "
        "Winston-Salem.",
    ),
]

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Lexington", "NC", ["27292", "27293", "27295"],
     "Davidson County seat on I-85 -- its own lodging cluster, branded with its own name; evaluated and refused."),
    ("Thomasville", "NC", ["27360", "27361"],
     "Davidson County on I-85 / I-74 -- hotels branded 'Thomasville', 10+ miles past High Point; evaluated and refused."),
    ("Welcome", "NC", ["27374"], "Davidson County on US-52."),
    ("Burlington", "NC", ["27215", "27216", "27217"],
     "Alamance County -- an I-40/I-85 outlet cluster and its own product; not absorbed because it lies on the interstate."),
    ("Graham", "NC", ["27253"], "Alamance County."),
    ("Mebane", "NC", ["27302"], "Alamance / Orange County outlet cluster on I-40/I-85; refused."),
    ("Elon", "NC", ["27244"], "Alamance County university town."),
    ("Gibsonville", "NC", ["27249"], "Guilford / Alamance line; no Triad-branded lodging observed."),
    ("Asheboro", "NC", ["27203", "27204", "27205"],
     "Randolph County seat and the North Carolina Zoo product; its own market."),
    ("Randleman", "NC", ["27317"], "Randolph County."),
    ("Mocksville", "NC", ["27028"], "Davie County seat."),
    ("Bermuda Run / Advance", "NC", ["27006"],
     "Davie County at I-40 exit 180 -- outside Forsyth County; evaluated and refused, admissible only by identity exception."),
    ("Reidsville", "NC", ["27320"], "Rockingham County."),
    ("Eden", "NC", ["27288"], "Rockingham County."),
    ("King", "NC", ["27021"], "Stokes County."),
    ("Yadkinville", "NC", ["27055"], "Yadkin County."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the refused neighbours so this order classifies them on evidence.
CELLS = [
    ("downtown-greensboro", "Greensboro", "Downtown Greensboro / UNCG / A&T", 36.072, -79.791, 3000, True),
    ("greensboro-coliseum", "Greensboro", "Coliseum / Gate City Blvd / Wendover / Big Tree Way", 36.055, -79.840, 3500, True),
    ("greensboro-friendly", "Greensboro", "Friendly Center / Guilford College / north-west loop", 36.090, -79.870, 4000, True),
    ("greensboro-north", "Greensboro", "North Greensboro / Battleground / US-29", 36.130, -79.820, 4000, True),
    ("pti-airport", "Greensboro", "PTI airport / Regional Rd / Sandy Ridge Rd / Chimney Rock Rd", 36.100, -79.950, 4500, True),
    ("greensboro-south-i85", "Greensboro", "South Elm-Eugene / Randleman Rd / I-85", 36.010, -79.790, 4000, True),
    ("greensboro-east-i40", "Whitsett", "McLeansville / Whitsett / I-40-85 east", 36.060, -79.620, 5000, True),
    ("high-point-downtown", "High Point", "Downtown High Point / N Main St / HPU", 35.960, -80.005, 3500, True),
    ("high-point-palladium", "High Point", "Palladium / Wendover Ave / I-74", 36.020, -79.965, 3500, True),
    ("jamestown", "Jamestown", "Jamestown / Guilford Technical CC", 35.995, -79.935, 3000, True),
    ("archdale", "Archdale", "Archdale / Trinity / I-85 south", 35.905, -79.960, 4000, True),
    ("kernersville", "Kernersville", "Kernersville / I-40 / Business 40", 36.110, -80.080, 4000, True),
    ("downtown-winston-salem", "Winston-Salem", "Downtown Winston-Salem / Innovation Quarter / Old Salem", 36.096, -80.244, 3000, True),
    ("winston-salem-hanes-mall", "Winston-Salem", "Hanes Mall Blvd / Stratford Rd / I-40 west", 36.066, -80.310, 3500, True),
    ("winston-salem-university", "Winston-Salem", "University Parkway / Wake Forest University / LJVM", 36.140, -80.270, 4000, True),
    ("winston-salem-south", "Winston-Salem", "Peters Creek / Clemmonsville Rd / US-52 south", 36.050, -80.240, 3500, True),
    ("clemmons", "Clemmons", "Clemmons / Lewisville / I-40 west", 36.030, -80.390, 4500, True),
    ("oak-ridge", "Oak Ridge", "Oak Ridge / Summerfield", 36.170, -79.960, 5000, True),
    ("north-forsyth", "Rural Hall", "Rural Hall / Walkertown / US-52 north", 36.220, -80.240, 6000, True),
    # observation only -- refused neighbours, seen so they can be classified
    ("obs-lexington", "Lexington", "Lexington, Davidson County -- OBSERVATION ONLY", 35.824, -80.253, 5000, False),
    ("obs-thomasville", "Thomasville", "Thomasville, Davidson County -- OBSERVATION ONLY", 35.883, -80.082, 4000, False),
    ("obs-burlington", "Burlington", "Burlington / Graham / Elon, Alamance County -- OBSERVATION ONLY", 36.080, -79.450, 6000, False),
    ("obs-mebane", "Mebane", "Mebane outlets, I-40/I-85 -- OBSERVATION ONLY", 36.090, -79.280, 4000, False),
    ("obs-asheboro", "Asheboro", "Asheboro, Randolph County -- OBSERVATION ONLY", 35.707, -79.814, 5000, False),
    ("obs-mocksville", "Mocksville", "Mocksville / Bermuda Run, Davie County -- OBSERVATION ONLY", 35.940, -80.500, 7000, False),
]

BOUNDS = {
    "min_lat": 35.66,
    "max_lat": 36.35,
    "min_lng": -80.65,
    "max_lng": -79.20,
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Piedmont Triad" % name),
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

    cells = [OrderedDict([
        ("cell_id", "%s__%s" % (MARKET_ID, suffix)),
        ("municipality", muni), ("label", label),
        ("center_lat", lat), ("center_lng", lng), ("radius_meters", radius),
        ("state_code", "NC"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Piedmont Triad, NC visitor market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 36.072, "lng": -79.950}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It covers Guilford and Forsyth "
             "counties in full and deliberately reaches beyond them -- south to Lexington, "
             "Thomasville and Asheboro, east to Burlington and Mebane, west to Mocksville and "
             "Bermuda Run -- so that " + WORK_ORDER + " classifies those properties on "
             "evidence instead of being blind to them. Admission is decided by the market "
             "contract's corridor registry over the property's OWN postal code, never by this "
             "box."),
            ("_no_overlap_proof",
             "No committed discovery box overlaps this one. Raleigh's box begins at -79.15 W "
             "and this box ends at -79.20 W; Charlotte's box ends at 35.62 N and this box "
             "begins at 35.66 N."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision (~3 decimal places) approximate "
         "reference points. They are seed points for bounded-radius queries only; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A multi-core metro: Greensboro, Winston-Salem, High Point, "
         "Kernersville and the PTI airport corridor are CORE; the I-85 / I-40 approaches in "
         "Guilford and Forsyth counties plus Archdale / Trinity are CORRIDOR; Oak Ridge / "
         "Summerfield and northern Forsyth are FRINGE. Lexington, Thomasville, Burlington, "
         "Mebane, Asheboro, Mocksville and Bermuda Run are OBSERVED and REFUSED."),
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
        ("market_name", "Piedmont Triad (Greensboro - Winston-Salem - High Point), North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Greensboro"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Greensboro, Winston-Salem & High Point, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across the Piedmont Triad -- Greensboro, Winston-Salem "
         "and High Point, North Carolina -- with real pet fees and policies read from each "
         "hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official "
         "website."),
        ("navigation_label", "Piedmont Triad"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, "
         "joined to the corridor registry. A multi-core metro: Greensboro, Winston-Salem, High "
         "Point, Kernersville and the PTI airport corridor are CORE. Nothing else admits a "
         "property: not a brand's name for it, not a GSO / INT property-code prefix, not a "
         "marketing region, not a map pin, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). "
         "Every admitted lodging ZIP is claimed by exactly one corridor."),
        ("_census_membership_note",
         "Lexington, Thomasville, Burlington, Mebane, Asheboro, Mocksville and Bermuda Run are "
         "not absorbed. A property whose own page states one of their postal codes is OUTSIDE, "
         "however it is named."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Piedmont Triad travel-market geography"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-12"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the "
         "corridor registry. Nothing else admits a property."),
        ("multi_core",
         "Three independent city centres (Greensboro, Winston-Salem, High Point) plus "
         "Kernersville and the PTI airport corridor. Each core carries its own corridors."),
        ("classes", OrderedDict([
            ("CORE", "Greensboro, Winston-Salem, High Point / Jamestown, Kernersville, PTI airport corridor (27409, Colfax 27235)."),
            ("CORRIDOR", "South / east Greensboro on I-85 and I-40 (27406, McLeansville, Whitsett); Clemmons / Lewisville on I-40 west; Archdale / Trinity on I-85 / I-74 south."),
            ("FRINGE", "Oak Ridge / Summerfield; northern Forsyth on US-52 (Rural Hall, Walkertown, Pfafftown, Tobaccoville)."),
            ("OUTSIDE", "Everything else, refused by name with its postal codes."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Colfax", "ADMITTED (CORE, PTI airport corridor) -- its I-40 hotels are airport lodging."),
            ("Jamestown", "ADMITTED (CORE, with High Point)."),
            ("Archdale", "ADMITTED (CORRIDOR) -- I-85 / I-74 hotels sold as High Point lodging; 27263 is shared with High Point."),
            ("Clemmons", "ADMITTED (CORRIDOR) -- I-40 west of Winston-Salem."),
            ("Lewisville", "ADMITTED (CORRIDOR, with Clemmons)."),
            ("Oak Ridge", "ADMITTED (FRINGE)."),
            ("Lexington, NC", "OUTSIDE -- Davidson County seat, own-named cluster, ~20 mi from High Point."),
            ("Thomasville", "OUTSIDE -- hotels branded Thomasville; not absorbed on I-85 alone."),
            ("Burlington", "OUTSIDE -- Alamance County, its own I-40/I-85 product."),
            ("Mebane", "OUTSIDE -- outlet cluster ~30 mi east."),
            ("Asheboro", "OUTSIDE -- Randolph County seat / NC Zoo product."),
            ("Mocksville", "OUTSIDE -- Davie County seat."),
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
         "Six cells observe Lexington, Thomasville, Burlington, Mebane, Asheboro and "
         "Mocksville / Bermuda Run. They admit nothing."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    config, shard, report, corridors = build()
    if args.write:
        os.makedirs(os.path.dirname(CONFIG_OUT), exist_ok=True)
        with open(CONFIG_OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(config, fh, indent=1)
            fh.write("\n")
        with open(SHARD_OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(shard, fh, indent=1)
            fh.write("\n")
        with open(REPORT_OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1)
            fh.write("\n")
        with open(REGISTRY_OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(OrderedDict([
                ("schema", "ptf-corridor-registry/1.0"), ("work_order", WORK_ORDER),
                ("market_id", MARKET_ID), ("corridors", corridors)]), fh, indent=1)
            fh.write("\n")
        for p in (CONFIG_OUT, SHARD_OUT, REPORT_OUT, REGISTRY_OUT):
            print("WROTE", os.path.relpath(p, _DASH))
    print("corridors=%d  admitted_zips=%d  cells=%d (admitting %d, observation %d)" % (
        report["corridor_count"], report["admitted_postal_code_count"],
        report["cells_total"], report["cells_admitting"], report["cells_observation_only"]))
    print("by class:", json.dumps(report["corridor_count_by_class"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
