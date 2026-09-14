"""PTF-FAYETTEVILLE-NC-NORMAL-PRODUCTION-001 -- Phase 2: the Fayetteville / Fort Liberty travel market.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Fayetteville, North Carolina traveler lodging market -- downtown,
the Cross Creek Mall / Skibo Road cluster, the Bragg Boulevard / Fort Liberty
military-travel corridor, Fayetteville Regional Airport (FAY), the I-95
Fayetteville exits, Hope Mills and Spring Lake -- stated as an explicit four-way
rule (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is discovered, so
no property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

A TRAVEL MARKET, NOT CITY LIMITS
--------------------------------
Fayetteville's hotel inventory is driven by Fort Liberty, the largest Army
installation in the country by population, and by I-95. The corridors therefore
follow where travelers actually sleep:

* 28303 / 28304 / 28314 carry Cross Creek Mall, Skibo Road, Raeford Road, Owen
  Drive and the inner Bragg Boulevard -- one CORE corridor; the coverage report
  slices it by the property's own coordinates.
* 28390 Spring Lake is the Bragg Boulevard / NC-87 / NC-24 approach to the
  installation's main gates. Its hotels sell themselves as "Fort Liberty" /
  "Fayetteville - Spring Lake": CORE.
* 28348 Hope Mills is continuous with south Fayetteville and I-95 exit 41;
  its hotels are Fayetteville inventory: CORE.
* 28306 carries Fayetteville Regional Airport (400 Airport Road), Gillespie
  Street and I-95 exits 44 / 46.
* 28312 carries the I-95 exits 49 / 52 / 55 / 56 lodging clusters east of the
  Cape Fear River, plus Eastover and Vander.

THE FOUR CLASSES
----------------
CORE       Downtown Fayetteville / Haymount / Eastern Boulevard (28301, 28305);
           Cross Creek Mall / Skibo Road / Raeford Road / Bragg Boulevard (28303,
           28304, 28314); Fayetteville Regional Airport / Gillespie Street / I-95
           south exits (28306); North Fayetteville / Ramsey Street / Methodist
           University (28311); I-95 Central exits / Eastover / Vander (28312);
           Spring Lake / Fort Liberty gates (28390); Hope Mills (28348).
CORRIDOR   Wade on I-95 north, exits 58 / 61 (28395).
FRINGE     Raeford (28376), the Hoke County seat on US-401 at the installation's
           western edge -- admitted in its own corridor so a fringe property never
           reports as core.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight.

THE MILITARY / GOVERNMENT LODGING RULE
--------------------------------------
Fort Liberty's on-post postal codes (28307, 28310) and Pope Army Airfield (28308)
are OUTSIDE. On-post lodging -- IHG Army Hotels, Army Lodging, transient
quarters, barracks -- requires installation access (a DoD credential or a
sponsored visitor pass) and is not bookable by the general traveling public
under normal conditions. Any such property the census meets is recorded as an
explicit MILITARY_GOVERNMENT_NONPUBLIC exclusion, never admitted. The public
commercial hotels that serve Fort Liberty travelers sit off-post in Spring Lake
and Fayetteville and are admitted normally.

WHY SOUTHERN PINES, SANFORD, LUMBERTON AND DUNN ARE NOT
-------------------------------------------------------
Southern Pines / Pinehurst / Aberdeen is the Sandhills golf-resort market -- a
materially separate tourism product with its own resort inventory; never
absorbed. Sanford (Lee County, US-421 / US-1) is its own small-city market 35
miles north. Lumberton (Robeson County, I-95 exits 17-22) and St. Pauls sit
25-30 miles south and are their own I-95 stop; Dunn / Erwin (Harnett County, I-95
exits 71-75) and Godwin / Falcon sit 20-25 miles north. Clinton (Sampson County)
is 30 miles east. I-95 alone admits nothing. A single legitimate exception is
admitted by identity through ``explicit_hotel_admissions`` -- never by widening a
ZIP.

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the admitted ZIPs -- it covers Southern Pines /
Pinehurst, Lumberton, Dunn and Clinton deliberately -- so this order classifies
those properties on evidence rather than being blind to them.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/fayetteville_nc.json
  launch_packages/pettripfinder/markets/fayetteville-nc.json
  launch_packages/pettripfinder/markets/reports/fayetteville_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/fayetteville_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-FAYETTEVILLE-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "fayetteville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                          "fayetteville_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "fayetteville-nc.json")
REPORT_OUT = os.path.join(REPORTS, "fayetteville_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "fayetteville_nc_corridor_registry_001.json")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, postal codes, description)
CORRIDORS = [
    (
        "downtown-fayetteville", "Downtown Fayetteville / Haymount", "Downtown Fayetteville",
        "CORE",
        ["28301", "28305"],
        "Hay Street, the Market House, Festival Park, Haymount Hill and the Eastern "
        "Boulevard (US-301 / I-95 Business) approach.",
    ),
    (
        "cross-creek-skibo", "Cross Creek Mall / Skibo Road / Bragg Boulevard",
        "Cross Creek & Skibo", "CORE",
        ["28303", "28304", "28314"],
        "Cross Creek Mall, Skibo Road, Raeford Road, Owen Drive, McPherson Church Road and "
        "the inner Bragg Boulevard toward Fort Liberty.",
    ),
    (
        "fay-airport-south", "Fayetteville Regional Airport / Gillespie Street / I-95 South",
        "FAY Airport", "CORE",
        ["28306"],
        "Fayetteville Regional Airport (FAY), Gillespie Street, Doc Bennett Road and I-95 "
        "exits 44 and 46.",
    ),
    (
        "north-fayetteville", "North Fayetteville / Ramsey Street", "North Fayetteville",
        "CORE",
        ["28311"],
        "Ramsey Street, Methodist University and the I-295 Fayetteville Outer Loop.",
    ),
    (
        "i-95-central-eastover", "I-95 Central Exits / Eastover", "I-95 Fayetteville",
        "CORE",
        ["28312"],
        "The I-95 exit 49, 52, 55 and 56 lodging clusters east of the Cape Fear River, "
        "Eastover and Vander.",
    ),
    (
        "spring-lake-fort-liberty", "Spring Lake / Fort Liberty", "Spring Lake",
        "CORE",
        ["28390"],
        "Spring Lake, Bragg Boulevard, NC-87 and NC-24 at the Fort Liberty main gates.",
    ),
    (
        "hope-mills", "Hope Mills", "Hope Mills", "CORE",
        ["28348"],
        "Hope Mills, Hope Mills Road and I-95 exit 41, continuous with south Fayetteville.",
    ),
    (
        "wade-i-95-north", "Wade / I-95 North", "Wade", "CORRIDOR",
        ["28395"],
        "Wade and the I-95 exit 58 / 61 interchanges twelve miles north of Fayetteville.",
    ),
    (
        "raeford", "Raeford", "Raeford", "FRINGE",
        ["28376"],
        "Raeford, the Hoke County seat on US-401 at Fort Liberty's western edge, twenty "
        "miles west of downtown Fayetteville.",
    ),
]

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Fort Liberty (on-post)", "NC", ["28307", "28310"],
     "MILITARY_GOVERNMENT_NONPUBLIC: on-post lodging (IHG Army Hotels, Army Lodging, transient quarters, barracks) requires installation access and is not bookable by the general traveling public under normal conditions; evaluated and refused."),
    ("Pope Army Airfield", "NC", ["28308"], "MILITARY_GOVERNMENT_NONPUBLIC: on-post; evaluated and refused."),
    ("Southern Pines", "NC", ["28387", "28388"],
     "Sandhills golf / resort market ~35 mi west; a materially separate tourism and lodging market; evaluated and refused."),
    ("Pinehurst", "NC", ["28370", "28374"], "Sandhills golf resort market; evaluated and refused."),
    ("Aberdeen / Whispering Pines / Vass", "NC", ["28315", "28327", "28394"], "Moore County Sandhills."),
    ("Sanford", "NC", ["27330", "27332"],
     "Lee County seat ~35 mi north on US-421 / US-1, its own small-city market; evaluated and refused."),
    ("Lumberton", "NC", ["28358", "28359", "28360"],
     "Robeson County seat ~30 mi south on I-95 exits 17-22, its own I-95 lodging stop; not absorbed merely because of I-95; evaluated and refused."),
    ("St. Pauls / Parkton / Red Springs", "NC", ["28384", "28371", "28377"], "Robeson County."),
    ("Dunn / Erwin", "NC", ["28334", "28335", "28339"],
     "Harnett County on I-95 exits 71-75 ~25 mi north, its own I-95 stop; not absorbed merely because of I-95; evaluated and refused."),
    ("Godwin / Falcon / Linden", "NC", ["28344", "28342", "28356"],
     "Rural north Cumberland / Harnett I-95 exits 65-70, contiguous with Dunn; evaluated and refused."),
    ("Stedman", "NC", ["28391"],
     "Rural eastern Cumberland County on NC-24 with no I-95 frontage and no qualifying hotel inventory; evaluated and refused."),
    ("Clinton / Roseboro / Autryville / Salemburg", "NC", ["28328", "28382", "28318", "28385"],
     "Sampson County ~30 mi east; evaluated and refused."),
    ("Lillington / Spout Springs / Cameron / Bunnlevel", "NC", ["27546", "28326", "28323"],
     "Harnett County north of Fort Liberty; evaluated and refused."),
    ("Elizabethtown / White Oak", "NC", ["28337", "28399"], "Bladen County."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the refused neighbours so this order classifies them on evidence.
CELLS = [
    ("downtown", "Fayetteville", "Downtown / Hay Street / Haymount", 35.053, -78.880, 2500, True),
    ("eastern-boulevard", "Fayetteville", "Eastern Boulevard / US-301 Business", 35.070, -78.855, 3000, True),
    ("cross-creek-skibo", "Fayetteville", "Cross Creek Mall / Skibo Road", 35.070, -78.960, 3000, True),
    ("raeford-road-owen", "Fayetteville", "Raeford Road / Owen Drive / McPherson Church", 35.030, -78.955, 3500, True),
    ("bragg-boulevard", "Fayetteville", "Bragg Boulevard / All American Freeway", 35.095, -78.945, 3500, True),
    ("fay-airport", "Fayetteville", "Fayetteville Regional Airport / Gillespie Street", 34.995, -78.885, 3500, True),
    ("north-ramsey", "Fayetteville", "Ramsey Street / Methodist University", 35.120, -78.880, 4000, True),
    ("i95-exit49-52", "Fayetteville", "I-95 exits 49 / 52", 35.085, -78.805, 4000, True),
    ("eastover-i95-exit56", "Eastover", "Eastover / I-95 exits 55 / 56", 35.110, -78.790, 4000, True),
    ("spring-lake", "Spring Lake", "Spring Lake / Fort Liberty gates", 35.170, -78.975, 4000, True),
    ("hope-mills", "Hope Mills", "Hope Mills / I-95 exit 41", 34.970, -78.945, 4000, True),
    ("i95-exit44-46", "Fayetteville", "I-95 exits 44 / 46", 35.010, -78.830, 4000, True),
    ("wade", "Wade", "Wade / I-95 exits 58 / 61", 35.160, -78.740, 5000, True),
    ("raeford", "Raeford", "Raeford / US-401", 34.980, -79.225, 5000, True),
    # observation only -- refused neighbours, seen so they can be classified
    ("obs-fort-liberty", "Fort Liberty", "Fort Liberty on-post -- OBSERVATION ONLY", 35.140, -79.010, 6000, False),
    ("obs-southern-pines", "Southern Pines", "Southern Pines / Pinehurst / Aberdeen -- OBSERVATION ONLY", 35.180, -79.420, 12000, False),
    ("obs-lumberton", "Lumberton", "Lumberton / St. Pauls -- OBSERVATION ONLY", 34.660, -79.030, 10000, False),
    ("obs-dunn", "Dunn", "Dunn / Erwin / Godwin -- OBSERVATION ONLY", 35.300, -78.620, 9000, False),
    ("obs-clinton", "Clinton", "Clinton -- OBSERVATION ONLY", 35.000, -78.330, 7000, False),
]

BOUNDS = {
    "min_lat": 34.59,
    "max_lat": 35.44,
    "min_lng": -79.55,
    "max_lng": -78.28,
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Fayetteville" % name),
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
        ("market_name", "Fayetteville, NC / Fort Liberty visitor market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 35.053, "lng": -78.878}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It covers Cumberland County in full "
             "and deliberately reaches beyond it -- west to Southern Pines / Pinehurst, south "
             "to Lumberton, north to Dunn and east to Clinton -- so that " + WORK_ORDER +
             " classifies those properties on evidence instead of being blind to them. "
             "Admission is decided by the market contract's corridor registry over the "
             "property's OWN postal code, never by this box."),
            ("_no_overlap_proof",
             "No committed discovery box overlaps this one. Raleigh's box starts at 35.45 N "
             "(this box ends at 35.44 N); Wilmington's box ends at 34.58 N (this box starts at "
             "34.59 N); Piedmont Triad starts at 35.66 N; Charlotte ends at -80.5 W (this box "
             "starts at -79.55 W)."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision (~3 decimal places) approximate "
         "reference points. They are seed points for bounded-radius queries only; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A military / I-95 travel market: downtown, Cross Creek / Skibo, the "
         "FAY airport / south, North Fayetteville, the I-95 central exits / Eastover, Spring "
         "Lake / Fort Liberty and Hope Mills are CORE; Wade is CORRIDOR; Raeford is FRINGE. "
         "Fort Liberty on-post, Southern Pines / Pinehurst, Sanford, Lumberton, Dunn and "
         "Clinton are OBSERVED or named and REFUSED."),
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
        ("market_name", "Fayetteville, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Fayetteville"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Fayetteville & Fort Liberty, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Fayetteville, Spring Lake, Hope Mills, the Fort "
         "Liberty area and the I-95 exits, North Carolina, with real pet fees and policies read "
         "from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official "
         "website."),
        ("navigation_label", "Fayetteville"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, "
         "joined to the corridor registry. A military / I-95 travel market: downtown, Cross "
         "Creek / Skibo, FAY airport, North Fayetteville, the I-95 central exits, Spring Lake / "
         "Fort Liberty and Hope Mills are CORE. Nothing else admits a property: not a brand's "
         "name for it, not a FAY property-code prefix, not a marketing region, not a map pin, "
         "not a vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). "
         "Every admitted lodging ZIP is claimed by exactly one corridor."),
        ("_census_membership_note",
         "Fort Liberty on-post lodging, Southern Pines, Pinehurst, Aberdeen, Sanford, Lumberton, "
         "St. Pauls, Dunn, Godwin, Stedman and Clinton are not absorbed. A property whose own "
         "page states one of their postal codes is OUTSIDE, however it is named."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Fayetteville / Fort Liberty travel-market geography"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-13"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the "
         "corridor registry. Nothing else admits a property."),
        ("travel_market",
         "Fayetteville proper plus Spring Lake, Hope Mills, Eastover and the I-95 exits a "
         "Fayetteville / Fort Liberty visitor sleeps at. It represents military travel (PCS "
         "moves, graduations, TDY, family visits), I-95 through traffic, FAY airport lodging, "
         "the Cross Creek retail cluster and downtown."),
        ("classes", OrderedDict([
            ("CORE", "Downtown / Haymount (28301, 28305); Cross Creek Mall / Skibo / Raeford Road / Bragg Boulevard (28303, 28304, 28314); FAY airport / Gillespie / I-95 south (28306); North Fayetteville (28311); I-95 central / Eastover / Vander (28312); Spring Lake / Fort Liberty (28390); Hope Mills (28348)."),
            ("CORRIDOR", "Wade / I-95 north (28395)."),
            ("FRINGE", "Raeford (28376)."),
            ("OUTSIDE", "Everything else, refused by name with its postal codes, including Fort Liberty on-post (MILITARY_GOVERNMENT_NONPUBLIC)."),
        ])),
        ("military_government_lodging_rule",
         "On-post lodging (IHG Army Hotels, Army Lodging, transient quarters, barracks, Pope Army "
         "Airfield) requires installation access and is not bookable by the general traveling "
         "public under normal conditions. Its postal codes (28307, 28308, 28310) are OUTSIDE, "
         "and any such property the census meets is an explicit MILITARY_GOVERNMENT_NONPUBLIC "
         "exclusion. Public commercial hotels serving Fort Liberty travelers are admitted "
         "normally by their own off-post postal code."),
        ("evaluated_inclusions", OrderedDict([
            ("Fayetteville", "ADMITTED (CORE) -- every Fayetteville lodging ZIP is claimed by one corridor."),
            ("Downtown Fayetteville", "ADMITTED (CORE, 28301 / 28305)."),
            ("Cross Creek Mall / Skibo Road", "ADMITTED (CORE, 28303 / 28304 / 28314)."),
            ("Fort Liberty gate / military-travel corridors", "ADMITTED (CORE) -- off-post Bragg Boulevard in 28303 and Spring Lake 28390; on-post REFUSED as nonpublic."),
            ("Fayetteville Regional Airport / FAY", "ADMITTED (CORE, 28306)."),
            ("I-95 Fayetteville exits", "ADMITTED (CORE) -- exits 44 / 46 in 28306, exit 41 in Hope Mills 28348, exits 49-56 in 28312."),
            ("Hope Mills", "ADMITTED (CORE, 28348) -- continuous with south Fayetteville, sells as Fayetteville inventory."),
            ("Spring Lake", "ADMITTED (CORE, 28390) -- the Fort Liberty gate lodging."),
            ("Eastover", "ADMITTED (CORE, shares 28312) -- the I-95 exit 55 / 56 cluster sold as Fayetteville I-95."),
            ("Vander", "ADMITTED (CORE, shares 28312) -- unincorporated east Fayetteville."),
            ("Wade", "ADMITTED (CORRIDOR, 28395) -- I-95 exits 58 / 61, twelve miles north; the northern I-95 overflow."),
            ("Stedman", "OUTSIDE -- rural NC-24, no I-95 frontage and no qualifying hotel inventory."),
            ("Raeford", "ADMITTED (FRINGE, 28376) -- Hoke County seat at Fort Liberty's western edge, twenty miles out; never CORE."),
            ("Sanford", "OUTSIDE -- Lee County, its own small-city market."),
            ("Southern Pines", "OUTSIDE -- the Sandhills golf / resort market; never absorbed."),
            ("Pinehurst", "OUTSIDE -- the Sandhills golf / resort market; never absorbed."),
            ("Lumberton", "OUTSIDE -- Robeson County's own I-95 stop; I-95 alone admits nothing."),
            ("Dunn", "OUTSIDE -- Harnett County's own I-95 stop; I-95 alone admits nothing."),
            ("Clinton", "OUTSIDE -- Sampson County."),
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
         "Five cells observe Fort Liberty on-post, Southern Pines / Pinehurst, Lumberton, Dunn "
         "and Clinton. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotel / motel / inn / resort establishments operated as lodging "
         "businesses. Individual vacation homes, cabins and cottages without normal hotel "
         "operation, condos, Airbnb-style units, property-management listings, corporate "
         "furnished-apartment operators and timeshare units are recorded as "
         "NON_HOTEL_VACATION_RENTAL exclusions, never admitted. A bed and breakfast is admitted "
         "only when it operates as an inn with bookable rooms on its own premises and an "
         "official site."),
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
