"""PTF-WILMINGTON-NC-NORMAL-PRODUCTION-001 -- Phase 2: the Wilmington coastal travel market.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Wilmington, North Carolina traveler lodging market -- the city, the
ILM airport corridor and the three beach towns a Wilmington visitor actually
sleeps in -- stated as an explicit four-way rule (CORE / CORRIDOR / FRINGE /
OUTSIDE) before a single hotel is discovered, so no property is admitted or
refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

A COASTAL MARKET, NOT CITY LIMITS
---------------------------------
Wrightsville Beach (28480), Carolina Beach (28428) and Kure Beach (28449) are
separate municipalities, and each is a real Wilmington lodging submarket: the
beach hotels are 15-25 minutes from downtown and are sold as Wilmington-area
beach lodging. They are CORE. Carolina Beach and Kure Beach share Pleasure
Island and one corridor.

28405 carries both the ILM airport (1740 Airport Blvd) and the Mayfaire / Market
Street / Military Cutoff cluster that fronts Wrightsville Beach. A ZIP is not
split: the corridor is one, and the coverage report slices it by the property's
own coordinates.

THE FOUR CLASSES
----------------
CORE       Downtown / Historic District / Riverfront (28401), Midtown / UNCW /
           Oleander / Eastwood Road (28403), North Wilmington -- ILM airport,
           Market Street and Mayfaire (28405), Wrightsville Beach (28480),
           Carolina Beach and Kure Beach (28428, 28449).
CORRIDOR   Monkey Junction / South College Road (28409, 28412), Ogden / Porters
           Neck on Market Street north (28411), and Leland / Belville / Navassa
           across the Cape Fear River on US-17 / US-74 (28451).
FRINGE     Castle Hayne on I-40 / US-117 north (28429). Admitted in its own
           corridor so a fringe property never reports as a core.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight: Hampstead, Topsail Beach / Surf City, Holly Ridge,
           Southport, Oak Island, Bald Head Island, Boiling Spring Lakes,
           Bolivia / Winnabow, Holden Beach / Supply, Shallotte, Ocean Isle
           Beach, Sunset Beach, Carolina Shores / Calabash, Burgaw, Rocky Point.

WHY LELAND IS IN AND SOUTHPORT IS NOT
-------------------------------------
Leland sits 4-8 miles from downtown Wilmington over the Cape Fear Memorial and
Isabel Holmes bridges, inside the Wilmington metropolitan area, and its
interchange hotels on US-17 / US-74 / US-76 are the inventory a Wilmington
traveler books when downtown is full. It is admitted as CORRIDOR (not CORE),
and the census records whether its hotels brand themselves to Wilmington.

Southport, Oak Island and Bald Head Island are 25-35 miles away by road (Bald
Head only by ferry), sold as their own Brunswick Islands vacation destination,
and their lodging is overwhelmingly vacation rentals. Topsail Beach and Surf
City are the Topsail Island product in Pender / Onslow counties. Hampstead is a
US-17 residential community with no Wilmington-branded hotel inventory.
Carolina Shores and Calabash belong to the Grand Strand at the South Carolina
line. None is absorbed because it is coastal and nearby. A single legitimate
exception is admitted by identity through ``explicit_hotel_admissions`` --
never by widening a ZIP.

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the admitted ZIPs -- it covers Hampstead,
Topsail, Southport / Oak Island, Bolivia and Burgaw deliberately -- so this
order classifies those properties on evidence rather than being blind to them.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/wilmington_nc.json
  launch_packages/pettripfinder/markets/wilmington-nc.json
  launch_packages/pettripfinder/markets/reports/wilmington_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/wilmington_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-WILMINGTON-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "wilmington-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                          "wilmington_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "wilmington-nc.json")
REPORT_OUT = os.path.join(REPORTS, "wilmington_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "wilmington_nc_corridor_registry_001.json")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, postal codes, description)
CORRIDORS = [
    (
        "downtown-wilmington", "Downtown Wilmington / Historic District", "Downtown Wilmington",
        "CORE",
        ["28401"],
        "The Riverwalk, the Wilmington Convention Center, the Historic District, the "
        "Northside and the South 17th Street medical park.",
    ),
    (
        "midtown-uncw", "Midtown / UNCW / Oleander Drive", "Midtown Wilmington", "CORE",
        ["28403"],
        "Oleander Drive, Independence Mall, UNC Wilmington, College Road and the Eastwood "
        "Road approach to Wrightsville Beach.",
    ),
    (
        "ilm-airport-mayfaire", "ILM Airport / Market Street / Mayfaire", "North Wilmington",
        "CORE",
        ["28405"],
        "Wilmington International Airport (ILM), Market Street, Mayfaire Town Center, "
        "Military Cutoff Road and Landfall.",
    ),
    (
        "wrightsville-beach", "Wrightsville Beach", "Wrightsville Beach", "CORE",
        ["28480"],
        "Lumina Avenue, Waynick Boulevard and the Wrightsville Beach oceanfront and "
        "Banks Channel.",
    ),
    (
        "carolina-beach-kure-beach", "Carolina Beach / Kure Beach", "Pleasure Island", "CORE",
        ["28428", "28449"],
        "Pleasure Island: the Carolina Beach boardwalk and Lake Park Boulevard, Kure Beach "
        "pier and Fort Fisher.",
    ),
    (
        "monkey-junction", "Monkey Junction / South College Road", "Monkey Junction",
        "CORRIDOR",
        ["28409", "28412"],
        "South College Road and Carolina Beach Road at Monkey Junction, Masonboro and Pine "
        "Valley -- the approach to Pleasure Island.",
    ),
    (
        "ogden-porters-neck", "Ogden / Porters Neck", "Porters Neck", "CORRIDOR",
        ["28411"],
        "Market Street north of Mayfaire through Ogden and Porters Neck to the I-140 / US-17 "
        "interchange.",
    ),
    (
        "leland", "Leland / Belville", "Leland", "CORRIDOR",
        ["28451"],
        "Leland, Belville and Navassa across the Cape Fear River on US-17 / US-74 / US-76, "
        "four to eight miles from downtown Wilmington.",
    ),
    (
        "castle-hayne", "Castle Hayne / I-40 North", "Castle Hayne", "FRINGE",
        ["28429"],
        "Castle Hayne on I-40 and US-117 north of Wilmington.",
    ),
]

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Hampstead", "NC", ["28443"],
     "Pender County US-17 residential community ~20 mi north; no Wilmington-branded hotel inventory; evaluated and refused."),
    ("Topsail Beach / Surf City / Holly Ridge", "NC", ["28445"],
     "Topsail Island -- its own beach product in Pender / Onslow counties, ~30 mi; refused."),
    ("Sneads Ferry", "NC", ["28460"], "Onslow County."),
    ("Southport / Bald Head Island / Boiling Spring Lakes / Caswell Beach", "NC", ["28461"],
     "Brunswick Islands destination ~30 mi by road (Bald Head only by ferry); sold as its own vacation market; evaluated and refused."),
    ("Oak Island", "NC", ["28465"],
     "Brunswick Islands beach town ~35 mi; vacation-rental dominated; evaluated and refused."),
    ("Bolivia", "NC", ["28422"], "Brunswick County seat."),
    ("Winnabow", "NC", ["28479"], "Brunswick County on NC-133 / US-17 south of Leland."),
    ("Holden Beach / Supply", "NC", ["28462"], "Brunswick Islands."),
    ("Shallotte", "NC", ["28470"], "Brunswick County on US-17 ~35 mi."),
    ("Ocean Isle Beach", "NC", ["28469"], "Brunswick Islands."),
    ("Sunset Beach", "NC", ["28468"], "Brunswick Islands."),
    ("Carolina Shores / Calabash", "NC", ["28467"],
     "Grand Strand edge at the South Carolina line ~50 mi; evaluated and refused."),
    ("Burgaw", "NC", ["28425"], "Pender County seat ~25 mi north on I-40."),
    ("Rocky Point", "NC", ["28457"], "Pender County on I-40."),
    ("Wallace", "NC", ["28466"], "Duplin County on I-40."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the refused neighbours so this order classifies them on evidence.
CELLS = [
    ("downtown-wilmington", "Wilmington", "Downtown / Riverwalk / Convention Center", 34.236, -77.945, 2500, True),
    ("medical-park", "Wilmington", "South 17th Street / Novant NHRMC medical park", 34.205, -77.925, 2500, True),
    ("oleander-midtown", "Wilmington", "Oleander Drive / Independence Mall", 34.215, -77.890, 3000, True),
    ("uncw-college-road", "Wilmington", "UNCW / College Road", 34.225, -77.870, 3000, True),
    ("eastwood-road", "Wilmington", "Eastwood Road / Wrightsville Avenue", 34.225, -77.835, 2500, True),
    ("mayfaire", "Wilmington", "Mayfaire Town Center / Military Cutoff / Landfall", 34.245, -77.825, 3000, True),
    ("market-street", "Wilmington", "Market Street / Kerr Avenue", 34.255, -77.870, 3000, True),
    ("ilm-airport", "Wilmington", "ILM airport / Airport Blvd / North 23rd St", 34.270, -77.905, 3500, True),
    ("wrightsville-beach", "Wrightsville Beach", "Wrightsville Beach oceanfront", 34.215, -77.790, 3500, True),
    ("monkey-junction", "Wilmington", "Monkey Junction / South College Road / Carolina Beach Road", 34.145, -77.895, 4000, True),
    ("carolina-beach", "Carolina Beach", "Carolina Beach boardwalk / Lake Park Blvd", 34.035, -77.895, 3500, True),
    ("kure-beach", "Kure Beach", "Kure Beach / Fort Fisher", 33.995, -77.908, 3000, True),
    ("ogden-porters-neck", "Wilmington", "Ogden / Porters Neck / Market Street north", 34.300, -77.790, 5000, True),
    ("leland", "Leland", "Leland / Belville / US-17 / US-74", 34.230, -78.020, 6000, True),
    ("castle-hayne", "Castle Hayne", "Castle Hayne / I-40 north", 34.355, -77.900, 5000, True),
    # observation only -- refused neighbours, seen so they can be classified
    ("obs-hampstead", "Hampstead", "Hampstead, Pender County -- OBSERVATION ONLY", 34.370, -77.710, 6000, False),
    ("obs-topsail", "Surf City", "Topsail Island / Surf City -- OBSERVATION ONLY", 34.430, -77.550, 8000, False),
    ("obs-southport-oak-island", "Southport", "Southport / Oak Island / Bald Head -- OBSERVATION ONLY", 33.920, -78.080, 10000, False),
    ("obs-bolivia", "Bolivia", "Bolivia / Winnabow, Brunswick County -- OBSERVATION ONLY", 34.080, -78.110, 7000, False),
    ("obs-burgaw", "Burgaw", "Burgaw / Rocky Point, Pender County -- OBSERVATION ONLY", 34.520, -77.920, 7000, False),
]

BOUNDS = {
    "min_lat": 33.84,
    "max_lat": 34.58,
    "min_lng": -78.22,
    "max_lng": -77.48,
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Wilmington" % name),
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
        ("market_name", "Wilmington, NC coastal visitor market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 34.225, "lng": -77.900}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It covers New Hanover County in full "
             "and deliberately reaches beyond it -- north to Hampstead, Topsail Island and "
             "Burgaw, west and south to Leland, Bolivia, Southport and Oak Island -- so that "
             + WORK_ORDER + " classifies those properties on evidence instead of being blind "
             "to them. Admission is decided by the market contract's corridor registry over "
             "the property's OWN postal code, never by this box."),
            ("_no_overlap_proof",
             "No committed discovery box overlaps this one. Raleigh's box begins at 35.45 N, "
             "Charlotte's at 34.85 N and the Piedmont Triad's at 35.66 N; this box ends at "
             "34.58 N."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision (~3 decimal places) approximate "
         "reference points. They are seed points for bounded-radius queries only; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A coastal market: downtown, midtown, the ILM airport / Mayfaire "
         "north side, Wrightsville Beach and Carolina / Kure Beach are CORE; Monkey Junction, "
         "Ogden / Porters Neck and Leland are CORRIDOR; Castle Hayne is FRINGE. Hampstead, "
         "Topsail, Southport, Oak Island, Bald Head Island and Burgaw are OBSERVED and "
         "REFUSED."),
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
        ("market_name", "Wilmington, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Wilmington"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Wilmington & Wrightsville Beach, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Wilmington, Wrightsville Beach, Carolina Beach and "
         "Kure Beach, North Carolina, with real pet fees and policies read from each hotel's "
         "own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official "
         "website."),
        ("navigation_label", "Wilmington"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, "
         "joined to the corridor registry. A coastal market: downtown and midtown Wilmington, "
         "the ILM airport / Mayfaire north side, Wrightsville Beach and Carolina / Kure Beach "
         "are CORE. Nothing else admits a property: not a brand's name for it, not an ILM "
         "property-code prefix, not a marketing region, not a map pin, not a vacation-rental "
         "listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). "
         "Every admitted lodging ZIP is claimed by exactly one corridor."),
        ("_census_membership_note",
         "Hampstead, Topsail Beach, Surf City, Southport, Oak Island, Bald Head Island and "
         "Carolina Shores are not absorbed. A property whose own page states one of their "
         "postal codes is OUTSIDE, however it is named."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Wilmington coastal travel-market geography"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-12"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the "
         "corridor registry. Nothing else admits a property."),
        ("coastal_market",
         "Wilmington proper plus the ILM airport corridor and the three beach towns a "
         "Wilmington visitor sleeps in. Wrightsville Beach, Carolina Beach and Kure Beach are "
         "separate municipalities and CORE lodging submarkets."),
        ("classes", OrderedDict([
            ("CORE", "Downtown Wilmington (28401); Midtown / UNCW (28403); ILM airport / Market Street / Mayfaire (28405); Wrightsville Beach (28480); Carolina Beach / Kure Beach (28428, 28449)."),
            ("CORRIDOR", "Monkey Junction (28409, 28412); Ogden / Porters Neck (28411); Leland / Belville / Navassa (28451)."),
            ("FRINGE", "Castle Hayne (28429)."),
            ("OUTSIDE", "Everything else, refused by name with its postal codes."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Wrightsville Beach", "ADMITTED (CORE) -- oceanfront resort hotels sold as Wilmington beach lodging."),
            ("Carolina Beach", "ADMITTED (CORE, Pleasure Island) -- oceanfront and boardwalk hotels."),
            ("Kure Beach", "ADMITTED (CORE, Pleasure Island, with Carolina Beach)."),
            ("ILM airport", "ADMITTED (CORE, 28405)."),
            ("Mayfaire", "ADMITTED (CORE, 28405) -- the Military Cutoff hotel cluster at the Wrightsville Beach approach."),
            ("Monkey Junction", "ADMITTED (CORRIDOR) -- South College Road hotels on the route to Pleasure Island."),
            ("Ogden", "ADMITTED (CORRIDOR, with Porters Neck, 28411)."),
            ("Porters Neck", "ADMITTED (CORRIDOR, 28411)."),
            ("Leland", "ADMITTED (CORRIDOR) -- 4-8 mi over the Cape Fear bridges, Wilmington metro interchange hotels; branding recorded by the census."),
            ("Castle Hayne", "ADMITTED (FRINGE) -- I-40 north."),
            ("Hampstead", "OUTSIDE -- Pender County residential US-17, no Wilmington-branded hotels."),
            ("Topsail Beach / Surf City", "OUTSIDE -- Topsail Island is its own beach product."),
            ("Southport", "OUTSIDE -- Brunswick Islands destination, ~30 mi."),
            ("Oak Island", "OUTSIDE -- Brunswick Islands, vacation-rental dominated."),
            ("Bald Head Island", "OUTSIDE -- ferry-only island resort destination."),
            ("Carolina Shores", "OUTSIDE -- Grand Strand edge at the SC line."),
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
         "Five cells observe Hampstead, Topsail Island, Southport / Oak Island, Bolivia and "
         "Burgaw. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotel / motel / inn / resort establishments operated as lodging "
         "businesses. Individual vacation homes, condos, Airbnb-style units, property-"
         "management listings and timeshare units without normal hotel operation are "
         "recorded as NON_HOTEL_VACATION_RENTAL exclusions, never admitted."),
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
