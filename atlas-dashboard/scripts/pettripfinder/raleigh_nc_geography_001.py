"""PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001 -- Phase 2: the Raleigh travel market.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Raleigh traveler lodging market, stated as an explicit four-way
rule (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is discovered,
so that no property is admitted or refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is WAKE COUNTY, NORTH CAROLINA, by the property's OWN postal code as
its own official page states it. Wake County is the Raleigh lodging market: it
contains Raleigh, Cary, Morrisville, Apex, Garner, Wake Forest, Knightdale,
Holly Springs, Fuquay-Varina, Rolesville, Wendell and Zebulon, the RDU terminal
itself, and the Wake-side half of Research Triangle Park.

WHY NOT "RALEIGH-DURHAM"
-----------------------
Marketing, airport codes and brand property names all say "Raleigh-Durham".
None of them is a market. Durham County (Durham, the Durham side of RTP,
27701/27703/27709/27713) and Orange County (Chapel Hill, Carrboro,
27514/27516/27517) are separate county seats with their own lodging products and
their own visitor bureaus, and this order admits neither. A Marriott property
coded ``rdu*`` and named "...Raleigh-Durham... Research Triangle Park" is
admitted ONLY if the postal code on its own page is a Wake County code; the
brand's name for it decides nothing. That is the same ruling PTF-NASHVILLE
recorded as "an AIRPORT code prefix is not a market".

THE FOUR CLASSES
----------------
CORE       Raleigh proper -- downtown, Glenwood South, Midtown / North Hills,
           Crabtree Valley, west Raleigh / NCSU / PNC Arena, north Raleigh to
           I-540, east Raleigh / WakeMed, Brier Creek, and the RDU-facing
           Raleigh inventory. The product a visitor means by "a hotel in
           Raleigh".
CORRIDOR   Wake County municipalities on the I-40 / I-440 / I-540 / US-1 /
           US-64 ring whose hotels are sold, priced and travelled as Raleigh
           lodging: Cary, Morrisville (RDU and the Wake side of RTP), Apex,
           Garner, Wake Forest, Knightdale. Admitted.
FRINGE     Wake County's outer towns -- Holly Springs, Fuquay-Varina,
           Rolesville, Wendell, Zebulon. Inside the county and inside the rule,
           so admitted on the same basis, but each carries its own corridor so
           a fringe property never silently reports as Raleigh.
OUTSIDE    Everything outside Wake County. Named explicitly so the refusal is
           a decision and not an oversight: Durham County (Durham, RTP-Durham,
           Brier Creek's Durham side), Orange County (Chapel Hill, Carrboro,
           Hillsborough), Johnston County (Clayton, Smithfield, Selma),
           Franklin (Louisburg, Youngsville), Granville (Creedmoor, Butner),
           Harnett (Lillington), Chatham (Pittsboro, Siler City), Lee
           (Sanford), Nash/Edgecombe (Rocky Mount), Vance (Henderson).

THE OBSERVATION BOX IS NOT THE ADMISSION RULE
---------------------------------------------
Discovery SEES a box wider than the county -- it covers Durham, Chapel Hill and
Clayton deliberately -- so that this order classifies those properties on
evidence rather than being blind to them. Admission is the corridor registry
over the property's own postal code, never the box.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/raleigh_nc.json
  launch_packages/pettripfinder/markets/reports/raleigh_nc_geography_001.json
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

WORK_ORDER = "PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001"
MARKET_ID = "raleigh-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "raleigh_nc.json")
REPORT_OUT = os.path.join(REPORTS, "raleigh_nc_geography_001.json")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: Every admitted lodging postal code is claimed by exactly ONE corridor, so a
#: property's corridor is a lookup and never a judgement. (corridor_id suffix,
#: name, display_area, class, postal codes, description)
CORRIDORS = [
    (
        "downtown-raleigh", "Downtown Raleigh", "Downtown", "CORE",
        ["27601", "27603", "27605"],
        "Fayetteville Street, the Raleigh Convention Center, the Warehouse "
        "District, Moore Square, Glenwood South, the State Capitol and the "
        "Legislative complex.",
    ),
    (
        "north-hills-midtown", "Midtown / North Hills", "Midtown", "CORE",
        ["27609", "27608"],
        "North Hills, Six Forks Road, the Midtown district and the inner "
        "I-440 Beltline north of downtown.",
    ),
    (
        "crabtree-valley", "Crabtree Valley / Glenwood Avenue", "Crabtree Valley", "CORE",
        ["27612", "27607"],
        "Crabtree Valley Mall, Glenwood Avenue / US-70, Blue Ridge Road, the "
        "North Carolina Museum of Art and the Rex Hospital campus.",
    ),
    (
        "west-raleigh-ncsu", "West Raleigh / NC State", "West Raleigh", "CORE",
        ["27606"],
        "North Carolina State University, Hillsborough Street, the PNC Arena, "
        "Carter-Finley Stadium and the State Fairgrounds.",
    ),
    (
        "north-raleigh-540", "North Raleigh / I-540", "North Raleigh", "CORE",
        ["27613", "27614", "27615"],
        "Falls of Neuse Road, Leesville, Wakefield, Strickland Road and the "
        "I-540 northern arc.",
    ),
    (
        "brier-creek-rdu-raleigh", "Brier Creek / RDU (Raleigh side)", "Brier Creek", "CORE",
        ["27617"],
        "Brier Creek Parkway, Lumley Road, T.W. Alexander Drive on the Wake "
        "County side and the Raleigh-facing approach to Raleigh-Durham "
        "International Airport.",
    ),
    (
        "east-raleigh-wakemed", "East Raleigh / WakeMed / Capital Boulevard", "East Raleigh", "CORE",
        ["27604", "27610", "27616", "27620"],
        "WakeMed Raleigh Campus, New Bern Avenue, Capital Boulevard, Triangle "
        "Town Center, the I-440 eastern arc and the US-64 / I-87 approach.",
    ),
    (
        "cary", "Cary", "Cary", "CORRIDOR",
        ["27511", "27512", "27513", "27518", "27519"],
        "Downtown Cary, Weston Parkway, Harrison Avenue, Crossroads Plaza, "
        "Parkside Town Commons and the Cary side of I-40 and US-1/64.",
    ),
    (
        "morrisville-rdu-rtp", "Morrisville / RDU / RTP (Wake side)", "Morrisville", "CORRIDOR",
        ["27560"],
        "Raleigh-Durham International Airport, Airport Boulevard, Aviation "
        "Parkway, Perimeter Park and the Wake County side of Research "
        "Triangle Park.",
    ),
    (
        "apex", "Apex", "Apex", "CORRIDOR",
        ["27502", "27523", "27539"],
        "Apex, Beaver Creek Commons and the US-64 / NC-55 western approach.",
    ),
    (
        "garner", "Garner", "Garner", "CORRIDOR",
        ["27529", "27610-garner"],
        "Garner, Timber Drive, White Oak Crossing and the I-40 / US-70 "
        "southeastern approach.",
    ),
    (
        "wake-forest", "Wake Forest", "Wake Forest", "CORRIDOR",
        ["27587", "27588"],
        "Wake Forest, Capital Boulevard north and the US-1 northern approach.",
    ),
    (
        "knightdale", "Knightdale", "Knightdale", "CORRIDOR",
        ["27545"],
        "Knightdale, Knightdale Station and the US-64 / I-87 eastern approach.",
    ),
    (
        "holly-springs", "Holly Springs", "Holly Springs", "FRINGE",
        ["27540"],
        "Holly Springs, Holly Springs Towne Center and the NC-55 southwestern "
        "approach.",
    ),
    (
        "fuquay-varina", "Fuquay-Varina", "Fuquay-Varina", "FRINGE",
        ["27526"],
        "Fuquay-Varina and the US-401 southern approach.",
    ),
    (
        "rolesville-wendell-zebulon", "Rolesville / Wendell / Zebulon", "Eastern Wake", "FRINGE",
        ["27571", "27591", "27597"],
        "Rolesville, Wendell, Zebulon and the eastern Wake County US-64 "
        "corridor.",
    ),
]

#: Municipalities OUTSIDE the admitted market, each with the reason. Discovery
#: observes them; the corridor registry admits none of them.
OUTSIDE = [
    ("Durham", "NC", "Durham County -- a separate county seat, a separate visitor bureau and a separate lodging product. 'Raleigh-Durham' is an airport name, not a market."),
    ("Research Triangle Park (Durham side)", "NC", "Durham County. The Wake County side of RTP is admitted through Morrisville; the Durham side is not."),
    ("Chapel Hill", "NC", "Orange County -- a separate university town and lodging product."),
    ("Carrboro", "NC", "Orange County."),
    ("Hillsborough", "NC", "Orange County."),
    ("Clayton", "NC", "Johnston County -- outside Wake County; evaluated and refused."),
    ("Smithfield", "NC", "Johnston County -- an I-95 outlet-mall lodging cluster, a separate product."),
    ("Selma", "NC", "Johnston County -- I-95."),
    ("Youngsville", "NC", "Franklin County."),
    ("Louisburg", "NC", "Franklin County."),
    ("Creedmoor", "NC", "Granville County."),
    ("Butner", "NC", "Granville County."),
    ("Pittsboro", "NC", "Chatham County."),
    ("Sanford", "NC", "Lee County."),
    ("Lillington", "NC", "Harnett County."),
    ("Rocky Mount", "NC", "Nash / Edgecombe counties -- I-95."),
    ("Henderson", "NC", "Vance County -- I-85."),
    ("Benson", "NC", "Johnston County -- I-40 / I-95 junction."),
]

#: Bounded observation cells. ADMITTING cells sit inside Wake County;
#: OBSERVATION cells deliberately cover the refused neighbours so this order
#: classifies them on evidence.
CELLS = [
    # (cell_id suffix, municipality, label, lat, lng, radius_m, admitting)
    ("downtown", "Raleigh", "Downtown Raleigh / Fayetteville St / Convention Center / Glenwood South", 35.779, -78.639, 2500, True),
    ("midtown-north-hills", "Raleigh", "Midtown / North Hills / Six Forks", 35.837, -78.641, 2500, True),
    ("crabtree-valley", "Raleigh", "Crabtree Valley / Glenwood Ave / Blue Ridge Rd", 35.839, -78.683, 2500, True),
    ("west-raleigh-ncsu", "Raleigh", "NC State / Hillsborough St / PNC Arena / Fairgrounds", 35.787, -78.694, 3000, True),
    ("north-raleigh", "Raleigh", "North Raleigh / Falls of Neuse / Leesville / I-540", 35.885, -78.660, 4000, True),
    ("wakefield", "Raleigh", "Wakefield / Capital Blvd north / I-540 NE", 35.920, -78.560, 3500, True),
    ("east-raleigh-wakemed", "Raleigh", "WakeMed / New Bern Ave / I-440 east", 35.787, -78.590, 3000, True),
    ("capital-blvd-triangle-town", "Raleigh", "Capital Blvd / Triangle Town Center / I-440 north", 35.856, -78.585, 3000, True),
    ("brier-creek", "Raleigh", "Brier Creek / Lumley Rd / RDU east approach", 35.907, -78.783, 3000, True),
    ("southeast-raleigh", "Raleigh", "Tryon Rd / I-40 south / Garner border", 35.732, -78.640, 3000, True),
    ("cary-downtown", "Cary", "Downtown Cary / Harrison Ave / Chatham St", 35.791, -78.781, 2500, True),
    ("cary-weston", "Cary", "Weston Parkway / Cary Towne / I-40 west", 35.822, -78.800, 2500, True),
    ("cary-crossroads", "Cary", "Crossroads Plaza / US-1 / US-64 / Walnut St", 35.757, -78.762, 2500, True),
    ("cary-parkside", "Cary", "Parkside Town Commons / NC-55 / Green Level", 35.812, -78.878, 3000, True),
    ("morrisville-rdu", "Morrisville", "RDU Airport / Airport Blvd / Aviation Pkwy / Perimeter Park", 35.877, -78.813, 3500, True),
    ("morrisville-town", "Morrisville", "Morrisville / Chapel Hill Rd / Park West", 35.823, -78.826, 2500, True),
    ("apex", "Apex", "Apex / Beaver Creek / US-64", 35.733, -78.850, 3000, True),
    ("garner", "Garner", "Garner / Timber Dr / White Oak / US-70", 35.711, -78.614, 3000, True),
    ("wake-forest", "Wake Forest", "Wake Forest / US-1 north / Capital Blvd", 35.980, -78.510, 3500, True),
    ("knightdale", "Knightdale", "Knightdale / US-64 / I-87 east", 35.787, -78.481, 3000, True),
    ("holly-springs", "Holly Springs", "Holly Springs / NC-55 / Towne Center", 35.651, -78.833, 3000, True),
    ("fuquay-varina", "Fuquay-Varina", "Fuquay-Varina / US-401 south", 35.584, -78.800, 3000, True),
    ("eastern-wake", "Wendell", "Rolesville / Wendell / Zebulon / US-64 east", 35.790, -78.370, 5000, True),
    # observation only -- refused neighbours, seen so they can be classified
    ("obs-durham", "Durham", "Durham / downtown / I-85 / Duke -- OBSERVATION ONLY", 35.996, -78.899, 6000, False),
    ("obs-rtp-durham", "Durham", "Research Triangle Park, Durham side -- OBSERVATION ONLY", 35.898, -78.874, 4000, False),
    ("obs-chapel-hill", "Chapel Hill", "Chapel Hill / Carrboro -- OBSERVATION ONLY", 35.913, -79.055, 5000, False),
    ("obs-clayton", "Clayton", "Clayton, Johnston County -- OBSERVATION ONLY", 35.651, -78.456, 4000, False),
    ("obs-youngsville", "Youngsville", "Youngsville / Franklin County US-1 -- OBSERVATION ONLY", 36.026, -78.475, 4000, False),
]

BOUNDS = {
    "min_lat": 35.45,
    "max_lat": 36.10,
    "min_lng": -79.15,
    "max_lng": -78.30,
}


def build():
    corridors = []
    seen_zip = {}
    for order, (slug, name, area, klass, zips, desc) in enumerate(CORRIDORS, start=1):
        clean_zips = [z for z in zips if z.isdigit()]
        for z in clean_zips:
            if z in seen_zip:
                raise SystemExit(
                    "postal code %s claimed by both %s and %s -- the corridor "
                    "registry must be a partition" % (z, seen_zip[z], slug)
                )
            seen_zip[z] = slug
        corridors.append(OrderedDict([
            ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
            ("market_id", MARKET_ID),
            ("name", name),
            ("slug", slug),
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Raleigh" % name),
            ("meta_description",
             "Verified pet-friendly hotels in %s, with real pet fees and "
             "policies read from each hotel's own official website." % name),
            ("description", desc),
            ("included_cities", []),
            ("included_postal_codes", clean_zips),
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

    cells = []
    for suffix, muni, label, lat, lng, radius, admitting in CELLS:
        cells.append(OrderedDict([
            ("cell_id", "%s__%s" % (MARKET_ID, suffix)),
            ("municipality", muni),
            ("label", label),
            ("center_lat", lat),
            ("center_lng", lng),
            ("radius_meters", radius),
            ("state_code", "NC"),
            ("admitting", admitting),
        ]))

    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Raleigh, NC visitor market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 35.779, "lng": -78.639}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It covers Wake "
             "County, North Carolina in full and deliberately reaches beyond "
             "it -- west to Chapel Hill and Carrboro (Orange County), "
             "northwest to Durham and the Durham side of Research Triangle "
             "Park (Durham County), southeast to Clayton (Johnston County) and "
             "north to Youngsville (Franklin County) -- so that "
             + WORK_ORDER +
             " classifies those properties on evidence instead of being blind "
             "to them. Admission is decided by the market contract's corridor "
             "registry over the property's OWN postal code, never by this box. "
             "Deliberately excludes Smithfield and Selma (I-95, 35.5/-78.34 is "
             "outside the east edge), Sanford (35.48/-79.17), Rocky Mount "
             "(35.94/-77.79), Henderson (36.33) and Hillsborough (36.07/-79.10 "
             "sits in the box corner but carries no admitting corridor). Not "
             "an MSA boundary: the Raleigh-Cary MSA is Wake, Johnston and "
             "Franklin counties, and this file admits only Wake; the "
             "Raleigh-Durham-Cary CSA adds Durham, Orange, Chatham, Granville, "
             "Person, Vance and Harnett, and this file admits none of them."),
            ("_no_overlap_proof",
             "No committed discovery box overlaps this one. The nearest "
             "committed market is Charlotte, North Carolina "
             "(34.85..35.62 N, -81.30..-80.50 W): its north-east corner is "
             "35.62 N / -80.50 W and this box's south-west corner is "
             "35.45 N / -79.15 W, so the two are separated by more than one "
             "degree of longitude and share no point. Nashville, Tennessee "
             "(-87.10..-86.35 W) and Lexington, Kentucky (37.85..38.28 N) are "
             "further still."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision (~3 decimal "
         "places, roughly 100 m) approximate municipal-centre and corridor "
         "reference points from general public geographic knowledge, rounded "
         "deliberately to avoid a false impression of survey-grade precision. "
         "They are seed points for bounded-radius queries only, and nothing in "
         "this order decides a hotel's market membership from them: membership "
         "is decided by the corridor registry over the property's own postal "
         "code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". The admitting cells cover the practical Raleigh "
         "traveler lodging product: downtown Raleigh, Midtown / North Hills, "
         "Crabtree Valley, west Raleigh and the PNC Arena, north Raleigh to "
         "I-540, east Raleigh and WakeMed, Brier Creek, the RDU / Airport "
         "Boulevard cluster, Cary, Morrisville and the Wake side of Research "
         "Triangle Park, Apex, Garner, Wake Forest and Knightdale, plus Wake "
         "County's outer towns. Every one of them lies inside WAKE COUNTY, "
         "which is the admission rule. Durham, the Durham side of RTP and "
         "Chapel Hill are OBSERVED and REFUSED: 'Raleigh-Durham' is the name "
         "of an airport, not of a lodging market, and a brand property code "
         "beginning rdu admits nothing."),
        ("scope_disclosure",
         "28 bounded cells: 23 admitting cells inside Wake County and 5 "
         "observation-only cells (Durham, the Durham side of Research Triangle "
         "Park, Chapel Hill / Carrboro, Clayton and Youngsville). Conservative "
         "visitor-product seed plus a deliberately wider observation ring, not "
         "full-MSA and not full-CSA coverage."),
        ("explicit_hotel_admissions", OrderedDict([
            ("_what_this_is",
             "The explicit-hotel mechanism, so a single legitimate fringe "
             "property never becomes a reason to widen a municipality or a "
             "postal code. An entry admits ONE property by identity, with its "
             "own evidence, and does not admit its municipality. Empty at "
             "authoring time: this order admits no out-of-county property by "
             "exception, and routes every fringe candidate to the boundary "
             "report instead."),
            ("admissions", []),
        ])),
        ("cells", cells),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Raleigh travel-market geography"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-11"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("membership_rule",
         "WAKE COUNTY, NORTH CAROLINA, decided by the property's OWN postal "
         "code as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property: not a brand's name for it, "
         "not an rdu property-code prefix, not a marketing region, not a map "
         "pin, not a competitor directory's city label."),
        ("classes", OrderedDict([
            ("CORE", "Raleigh proper -- the product a visitor means by 'a hotel in Raleigh'."),
            ("CORRIDOR", "Wake County municipalities on the I-40 / I-440 / I-540 / US-1 / US-64 ring whose hotels are sold and travelled as Raleigh lodging: Cary, Morrisville, Apex, Garner, Wake Forest, Knightdale."),
            ("FRINGE", "Wake County's outer towns -- Holly Springs, Fuquay-Varina, Rolesville, Wendell, Zebulon. Admitted on the county rule, each in its own corridor so a fringe property never reports as Raleigh."),
            ("OUTSIDE", "Everything outside Wake County, refused by name."),
        ])),
        ("corridor_registry_is_a_partition", True),
        ("admitted_postal_codes", sorted(seen_zip)),
        ("admitted_postal_code_count", len(seen_zip)),
        ("corridors", [OrderedDict([
            ("corridor_id", c["corridor_id"]),
            ("name", c["name"]),
            ("geography_class", c["geography_class"]),
            ("included_postal_codes", c["included_postal_codes"]),
        ]) for c in corridors]),
        ("corridor_count", len(corridors)),
        ("corridor_count_by_class", {
            k: sum(1 for c in corridors if c["geography_class"] == k)
            for k in ("CORE", "CORRIDOR", "FRINGE")
        }),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("why", w)
        ]) for m, s, w in OUTSIDE]),
        ("the_raleigh_durham_ruling",
         "Durham and Chapel Hill are not absorbed. A property whose own page "
         "states a Durham County postal code (27701, 27703, 27707, 27709, "
         "27713) or an Orange County postal code (27514, 27516, 27517) is "
         "OUTSIDE, however it is named and whatever its property code begins "
         "with. The Wake County side of Research Triangle Park reaches this "
         "market through Morrisville (27560) and through Brier Creek (27617), "
         "which is where the Wake-side RTP lodging actually sits."),
        ("observation_is_not_admission",
         "Five cells observe Durham, RTP-Durham, Chapel Hill, Clayton and "
         "Youngsville. They admit nothing; they exist so a refusal is a "
         "recorded classification rather than a blind spot."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, report, corridors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    config, report, corridors = build()
    if args.write:
        os.makedirs(os.path.dirname(CONFIG_OUT), exist_ok=True)
        os.makedirs(REPORTS, exist_ok=True)
        with open(CONFIG_OUT, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=1)
            fh.write("\n")
        with open(REPORT_OUT, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
            fh.write("\n")
        # the corridor block the market shard will carry
        with open(os.path.join(REPORTS, "raleigh_nc_corridor_registry_001.json"), "w", encoding="utf-8") as fh:
            json.dump({"schema": "ptf-corridor-registry/1.0",
                       "work_order": WORK_ORDER,
                       "market_id": MARKET_ID,
                       "corridors": corridors}, fh, indent=1)
            fh.write("\n")
        print("WROTE", CONFIG_OUT)
        print("WROTE", REPORT_OUT)
    print("corridors=%d  admitted_zips=%d  cells=%d (admitting %d, observation %d)" % (
        report["corridor_count"], report["admitted_postal_code_count"],
        report["cells_total"], report["cells_admitting"], report["cells_observation_only"]))
    print("by class:", json.dumps(report["corridor_count_by_class"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
