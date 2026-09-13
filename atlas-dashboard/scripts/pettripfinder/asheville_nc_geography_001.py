"""PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001 -- Phase 2: the Asheville mountain travel market.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Asheville, North Carolina traveler lodging market -- downtown, the
Biltmore Village / Biltmore Estate corridor, the Tunnel Road and West Asheville
interstate clusters, South Asheville / Arden and the Asheville Regional Airport
(AVL) corridor, plus the I-40 / I-26 towns an Asheville visitor actually sleeps
in -- stated as an explicit four-way rule (CORE / CORRIDOR / FRINGE / OUTSIDE)
before a single hotel is discovered, so no property is admitted or refused after
the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

A TRAVEL MARKET, NOT CITY LIMITS
--------------------------------
28803 carries Biltmore Village, the Biltmore Estate lodging (The Inn and Village
Hotel on the estate) AND the Hendersonville Road / Biltmore Park hotels of South
Asheville. A ZIP is not split: the corridor is one, and the coverage report
slices it by the property's own coordinates.

Arden (28704) and Fletcher (28732) hold the Airport Road / I-26 hotel cluster and
Asheville Regional Airport itself (61 Terminal Drive, Fletcher). Those hotels sell
themselves as "Asheville Airport" / "Asheville South": they are CORE, one
corridor.

North Asheville (28804) carries the Omni Grove Park Inn, the UNC Asheville /
Merrimon Avenue inns and Woodfin (a separate municipality that shares 28804).

THE FOUR CLASSES
----------------
CORE       Downtown Asheville (28801); Biltmore Village / Biltmore Estate / South
           Asheville (28803); Tunnel Road / East Asheville (28805); West
           Asheville / Patton Avenue / Brevard Road (28806); North Asheville /
           Grove Park / Woodfin (28804); Arden / Fletcher / AVL airport (28704,
           28732).
CORRIDOR   Candler on I-40 west / Smoky Park Highway (28715); Weaverville on
           I-26 / US-19-23 north (28787); Swannanoa on I-40 east (28778).
FRINGE     Black Mountain (28711), admitted in its own corridor so a fringe
           property never reports as a core.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight: Hendersonville / Flat Rock / East Flat Rock, Mills River,
           Fairview, Leicester, Mars Hill / Marshall, Waynesville / Lake
           Junaluska / Maggie Valley, Canton / Clyde, Chimney Rock / Lake Lure /
           Bat Cave, Montreat / Ridgecrest / Old Fort, Brevard / Pisgah Forest.

WHY CANDLER, WEAVERVILLE, SWANNANOA AND BLACK MOUNTAIN ARE IN
-------------------------------------------------------------
Candler's Smoky Park Highway hotels sit at I-40 exits 37 / 44, 8-10 miles from
downtown, and brand themselves "Asheville West". Weaverville's I-26 exit 19
hotels are 10 miles north and brand "Asheville North / Weaverville". Swannanoa's
I-40 exit 55 motels are the eastern overflow. Black Mountain is 15 miles east on
I-40, a separate small-town destination whose handful of inns are nonetheless
routinely booked by Asheville visitors; it is FRINGE, never CORE.

WHY HENDERSONVILLE AND WAYNESVILLE ARE NOT
-----------------------------------------
Hendersonville is the Henderson County seat 22 miles south, with its own
downtown, its own apple-country tourism product and its own US-64 / I-26 hotel
cluster sold as "Hendersonville" / "Flat Rock": a materially separate lodging
market reserved for a future independent market. Mills River's only
airport-adjacent inventory brands as Mills River / Hendersonville. Waynesville,
Maggie Valley and Canton are the Haywood County Great Smoky Mountains gateway
product 25-35 miles west. Chimney Rock and Lake Lure are the Hickory Nut Gorge
resort product in Rutherford County. Fairview and Leicester are rural
cabin / vacation-rental country with no qualifying hotel inventory; Mars Hill is
the Madison County college town. None is absorbed because it is nearby. A single
legitimate exception is admitted by identity through
``explicit_hotel_admissions`` -- never by widening a ZIP.

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the admitted ZIPs -- it covers Hendersonville,
Mills River, Waynesville / Canton, Mars Hill and Chimney Rock / Lake Lure
deliberately -- so this order classifies those properties on evidence rather
than being blind to them.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/asheville_nc.json
  launch_packages/pettripfinder/markets/asheville-nc.json
  launch_packages/pettripfinder/markets/reports/asheville_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/asheville_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "asheville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                          "asheville_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "asheville-nc.json")
REPORT_OUT = os.path.join(REPORTS, "asheville_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "asheville_nc_corridor_registry_001.json")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, postal codes, description)
CORRIDORS = [
    (
        "downtown-asheville", "Downtown Asheville", "Downtown Asheville", "CORE",
        ["28801"],
        "Pack Square, the South Slope, Haywood Street, the Grove Arcade, Montford and the "
        "River Arts District edge.",
    ),
    (
        "biltmore-south-asheville", "Biltmore Village / Biltmore Estate / South Asheville",
        "Biltmore & South Asheville", "CORE",
        ["28803"],
        "Biltmore Village, the Biltmore Estate lodging, Biltmore Avenue, Hendersonville Road "
        "and Biltmore Park Town Square.",
    ),
    (
        "tunnel-road-east-asheville", "Tunnel Road / East Asheville", "East Asheville",
        "CORE",
        ["28805"],
        "Tunnel Road, the Asheville Mall, I-240 exits 7-9 and the Swannanoa River Road "
        "approach to I-40.",
    ),
    (
        "west-asheville", "West Asheville / Patton Avenue / Brevard Road", "West Asheville",
        "CORE",
        ["28806"],
        "Haywood Road, Patton Avenue, Smokey Park Highway at I-240 and the Brevard Road / "
        "I-26 exit 33 cluster.",
    ),
    (
        "north-asheville-grove-park", "North Asheville / Grove Park / Woodfin",
        "North Asheville", "CORE",
        ["28804"],
        "The Omni Grove Park Inn, Merrimon Avenue, UNC Asheville and Woodfin on US-19-23.",
    ),
    (
        "arden-avl-airport", "Arden / Fletcher / Asheville Regional Airport", "AVL Airport",
        "CORE",
        ["28704", "28732"],
        "Airport Road, Long Shoals Road and I-26 exits 37-40 in Arden, and Asheville "
        "Regional Airport (AVL) in Fletcher.",
    ),
    (
        "candler-asheville-west", "Candler / Asheville West", "Candler", "CORRIDOR",
        ["28715"],
        "Smoky Park Highway at I-40 exits 37 and 44, eight to ten miles west of downtown.",
    ),
    (
        "weaverville", "Weaverville / Asheville North", "Weaverville", "CORRIDOR",
        ["28787"],
        "Weaverville and I-26 exit 19 on US-19-23, ten miles north of downtown.",
    ),
    (
        "swannanoa", "Swannanoa / I-40 East", "Swannanoa", "CORRIDOR",
        ["28778"],
        "Swannanoa and the I-40 exit 55 interchange east of Asheville.",
    ),
    (
        "black-mountain", "Black Mountain", "Black Mountain", "FRINGE",
        ["28711"],
        "The town of Black Mountain on I-40, fifteen miles east of Asheville.",
    ),
]

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Hendersonville / Laurel Park", "NC", ["28739", "28791", "28792", "28793"],
     "Henderson County seat ~22 mi south with its own downtown, its own tourism product and its own US-64 / I-26 hotel cluster sold as Hendersonville; a materially separate lodging market reserved for a future market; evaluated and refused."),
    ("Flat Rock / East Flat Rock", "NC", ["28726", "28731"], "Henderson County, with Hendersonville."),
    ("Mills River", "NC", ["28759"],
     "Henderson County; airport-adjacent inventory brands as Mills River / Hendersonville; evaluated and refused."),
    ("Horse Shoe / Etowah", "NC", ["28742", "28729"], "Henderson County."),
    ("Fairview", "NC", ["28730"],
     "Rural Buncombe County US-74A cabin and vacation-rental country with no qualifying hotel inventory; evaluated and refused."),
    ("Leicester", "NC", ["28748"], "Rural Buncombe County; vacation rentals; evaluated and refused."),
    ("Alexander", "NC", ["28701"], "Rural Buncombe County."),
    ("Barnardsville", "NC", ["28709"], "Rural Buncombe County."),
    ("Mars Hill / Marshall / Hot Springs", "NC", ["28754", "28753", "28743"],
     "Madison County college town and river towns ~20-35 mi north; evaluated and refused."),
    ("Waynesville / Lake Junaluska", "NC", ["28785", "28786", "28745"],
     "Haywood County seat ~30 mi west, its own Smokies-gateway product; evaluated and refused."),
    ("Maggie Valley", "NC", ["28751"], "Haywood County Smokies-gateway resort town."),
    ("Canton / Clyde", "NC", ["28716", "28721"], "Haywood County on I-40 ~20 mi west; evaluated and refused."),
    ("Chimney Rock / Lake Lure / Bat Cave", "NC", ["28720", "28746", "28710"],
     "Hickory Nut Gorge resort product in Rutherford / Henderson counties ~25 mi; evaluated and refused."),
    ("Montreat / Ridgecrest", "NC", ["28757", "28770"], "Conference-center communities beyond Black Mountain."),
    ("Old Fort", "NC", ["28762"], "McDowell County on I-40 east."),
    ("Brevard / Pisgah Forest", "NC", ["28712", "28768"], "Transylvania County, its own destination."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the refused neighbours so this order classifies them on evidence.
CELLS = [
    ("downtown-asheville", "Asheville", "Downtown / Pack Square / South Slope", 35.595, -82.553, 2000, True),
    ("river-arts-montford", "Asheville", "River Arts District / Montford", 35.590, -82.570, 2000, True),
    ("biltmore-village", "Asheville", "Biltmore Village / Biltmore Estate entrance", 35.567, -82.543, 2500, True),
    ("biltmore-estate", "Asheville", "Biltmore Estate lodging", 35.545, -82.560, 3000, True),
    ("hendersonville-road", "Asheville", "Hendersonville Road / South Asheville", 35.520, -82.525, 3500, True),
    ("biltmore-park", "Asheville", "Biltmore Park Town Square / Long Shoals", 35.490, -82.545, 3000, True),
    ("tunnel-road", "Asheville", "Tunnel Road / Asheville Mall", 35.585, -82.515, 3000, True),
    ("east-asheville-i40", "Asheville", "Swannanoa River Road / I-40 exit 53", 35.570, -82.480, 3000, True),
    ("west-asheville", "Asheville", "West Asheville / Haywood Road / Patton Avenue", 35.580, -82.600, 3000, True),
    ("brevard-road", "Asheville", "Brevard Road / I-26 exit 33 / Farmers Market", 35.545, -82.600, 3000, True),
    ("north-asheville", "Asheville", "Grove Park / Merrimon Avenue / UNC Asheville", 35.625, -82.550, 3000, True),
    ("woodfin", "Woodfin", "Woodfin / US-19-23", 35.640, -82.585, 3000, True),
    ("arden-airport-road", "Arden", "Airport Road / I-26 exit 40", 35.450, -82.525, 3500, True),
    ("avl-airport", "Fletcher", "Asheville Regional Airport / Fletcher", 35.435, -82.540, 3500, True),
    ("candler", "Candler", "Candler / Smoky Park Highway / I-40 exit 44", 35.550, -82.690, 5000, True),
    ("weaverville", "Weaverville", "Weaverville / I-26 exit 19", 35.700, -82.560, 4000, True),
    ("swannanoa", "Swannanoa", "Swannanoa / I-40 exit 55", 35.600, -82.400, 4000, True),
    ("black-mountain", "Black Mountain", "Black Mountain", 35.617, -82.322, 4000, True),
    # observation only -- refused neighbours, seen so they can be classified
    ("obs-hendersonville", "Hendersonville", "Hendersonville / Flat Rock -- OBSERVATION ONLY", 35.320, -82.460, 9000, False),
    ("obs-mills-river", "Mills River", "Mills River -- OBSERVATION ONLY", 35.390, -82.570, 5000, False),
    ("obs-fairview", "Fairview", "Fairview -- OBSERVATION ONLY", 35.520, -82.400, 5000, False),
    ("obs-waynesville-canton", "Waynesville", "Waynesville / Canton / Maggie Valley -- OBSERVATION ONLY", 35.500, -82.920, 12000, False),
    ("obs-mars-hill", "Mars Hill", "Mars Hill / Marshall / Leicester -- OBSERVATION ONLY", 35.790, -82.620, 9000, False),
    ("obs-lake-lure", "Lake Lure", "Chimney Rock / Lake Lure -- OBSERVATION ONLY", 35.430, -82.220, 7000, False),
]

BOUNDS = {
    "min_lat": 35.20,
    "max_lat": 35.92,
    "min_lng": -83.05,
    "max_lng": -82.15,
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Asheville" % name),
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
        ("market_name", "Asheville, NC mountain visitor market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 35.595, "lng": -82.551}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It covers Buncombe County in full "
             "and deliberately reaches beyond it -- south to Hendersonville and Mills River, "
             "west to Waynesville and Canton, north to Mars Hill and east to Chimney Rock / "
             "Lake Lure -- so that " + WORK_ORDER + " classifies those properties on evidence "
             "instead of being blind to them. Admission is decided by the market contract's "
             "corridor registry over the property's OWN postal code, never by this box."),
            ("_no_overlap_proof",
             "No committed discovery box overlaps this one. Charlotte's box ends at -81.3 W "
             "(the easternmost western edge of any committed box); this box ends at -82.15 W."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision (~3 decimal places) approximate "
         "reference points. They are seed points for bounded-radius queries only; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A mountain travel market: downtown, Biltmore / South Asheville, "
         "Tunnel Road, West Asheville, North Asheville / Woodfin and Arden / Fletcher / AVL "
         "are CORE; Candler, Weaverville and Swannanoa are CORRIDOR; Black Mountain is "
         "FRINGE. Hendersonville, Mills River, Fairview, Waynesville, Canton, Mars Hill and "
         "Chimney Rock / Lake Lure are OBSERVED and REFUSED."),
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
        ("market_name", "Asheville, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Asheville"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Asheville & Biltmore, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Asheville, Biltmore Village, South Asheville, Arden "
         "and the Asheville airport area, North Carolina, with real pet fees and policies read "
         "from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official "
         "website."),
        ("navigation_label", "Asheville"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, "
         "joined to the corridor registry. A mountain travel market: downtown, Biltmore / South "
         "Asheville, Tunnel Road, West Asheville, North Asheville / Woodfin and Arden / "
         "Fletcher / AVL are CORE. Nothing else admits a property: not a brand's name for it, "
         "not an AVL property-code prefix, not a marketing region, not a map pin, not a "
         "vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). "
         "Every admitted lodging ZIP is claimed by exactly one corridor."),
        ("_census_membership_note",
         "Hendersonville, Flat Rock, Mills River, Fairview, Waynesville, Maggie Valley, Canton, "
         "Mars Hill, Chimney Rock and Lake Lure are not absorbed. A property whose own page "
         "states one of their postal codes is OUTSIDE, however it is named."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Asheville mountain travel-market geography"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-12"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the "
         "corridor registry. Nothing else admits a property."),
        ("travel_market",
         "Asheville proper plus Biltmore, the AVL airport corridor in Arden / Fletcher, Woodfin, "
         "and the I-40 / I-26 towns an Asheville visitor sleeps in. It represents downtown "
         "tourism, Biltmore tourism, I-40 / I-240 lodging, airport / South Asheville and the "
         "mountain resort / independent inventory (Grove Park, Biltmore Estate, downtown "
         "boutiques)."),
        ("classes", OrderedDict([
            ("CORE", "Downtown Asheville (28801); Biltmore Village / Biltmore Estate / South Asheville (28803); Tunnel Road / East Asheville (28805); West Asheville (28806); North Asheville / Grove Park / Woodfin (28804); Arden / Fletcher / AVL airport (28704, 28732)."),
            ("CORRIDOR", "Candler (28715); Weaverville (28787); Swannanoa (28778)."),
            ("FRINGE", "Black Mountain (28711)."),
            ("OUTSIDE", "Everything else, refused by name with its postal codes."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Downtown Asheville", "ADMITTED (CORE, 28801)."),
            ("Biltmore Village", "ADMITTED (CORE, 28803)."),
            ("Biltmore Estate lodging", "ADMITTED (CORE, 28803) -- The Inn and Village Hotel on the estate."),
            ("Tunnel Road / East Asheville", "ADMITTED (CORE, 28805)."),
            ("West Asheville", "ADMITTED (CORE, 28806)."),
            ("South Asheville", "ADMITTED (CORE, 28803 -- Hendersonville Road / Biltmore Park)."),
            ("Arden", "ADMITTED (CORE, 28704) -- Airport Road / I-26 hotels sold as Asheville Airport / Asheville South."),
            ("Asheville Regional Airport / Fletcher", "ADMITTED (CORE, 28732) -- the airport itself and its Fletcher hotels."),
            ("Woodfin", "ADMITTED (CORE, shares 28804 with North Asheville)."),
            ("Candler", "ADMITTED (CORRIDOR) -- I-40 exits 37 / 44, hotels brand Asheville West."),
            ("Weaverville", "ADMITTED (CORRIDOR) -- I-26 exit 19, 10 mi north."),
            ("Swannanoa", "ADMITTED (CORRIDOR) -- I-40 exit 55 overflow."),
            ("Black Mountain", "ADMITTED (FRINGE) -- 15 mi east, small-town inns booked by Asheville visitors; never CORE."),
            ("Hendersonville", "OUTSIDE -- materially separate Henderson County lodging market, reserved for a future market."),
            ("Mills River", "OUTSIDE -- Henderson County; inventory brands Hendersonville."),
            ("Fairview", "OUTSIDE -- cabin / vacation-rental country, no qualifying hotels."),
            ("Leicester", "OUTSIDE -- rural, vacation rentals."),
            ("Mars Hill", "OUTSIDE -- Madison County college town."),
            ("Waynesville", "OUTSIDE -- Haywood County Smokies gateway."),
            ("Canton", "OUTSIDE -- Haywood County."),
            ("Chimney Rock", "OUTSIDE -- Hickory Nut Gorge resort product."),
            ("Lake Lure", "OUTSIDE -- Hickory Nut Gorge resort product."),
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
         "Six cells observe Hendersonville, Mills River, Fairview, Waynesville / Canton, Mars "
         "Hill and Chimney Rock / Lake Lure. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotel / motel / inn / resort establishments operated as lodging "
         "businesses. Individual vacation homes, cabins and cottages without normal hotel "
         "operation, condos, Airbnb-style units, property-management listings and timeshare "
         "units are recorded as NON_HOTEL_VACATION_RENTAL exclusions, never admitted. A bed "
         "and breakfast is admitted only when it operates as an inn with bookable rooms on "
         "its own premises and an official site."),
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
