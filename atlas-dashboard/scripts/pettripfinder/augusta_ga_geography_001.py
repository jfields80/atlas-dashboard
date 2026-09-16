"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 3 + 4: the Augusta travel market and its corridors.

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Augusta, Georgia traveler lodging market -- an Augusta-Richmond
County / Columbia County CSA market, not city limits and not a two-state
metro -- stated as an explicit four-way rule (CORE / CORRIDOR / FRINGE /
OUTSIDE) before a single hotel is admitted, so no property is admitted or
refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. A
brand's marketing name ("Fort Gordon Area", "Washington Rd./I-20") never
admits and never places a property -- real OSM discovery evidence shows both
names attached to hotels in BOTH 30907 and 30909, so this order partitions by
the property's OWN postal code, not by which marketing phrase a brand chose.

THIS IS A REVISION FROM THE INITIALLY DRAFTED PLAN
---------------------------------------------------
The original ten-corridor draft (Downtown, Medical District, Washington Road,
West Augusta, Gordon Highway, Fort Eisenhower, Grovetown, Martinez, Evans,
AGS/South Augusta) was authored before discovery ran. PTF-AUGUSTA-GA-
HARDENED-V2-SOURCE-READY-001's own real Overpass + Georgia/South-Carolina
Geofabrik-extract discovery (44/44 cells exhausted, 94 candidates) showed:
  - 30907 and 30909 are each internally mixed by brand-marketing name
    (Washington Rd. and Fort Gordon Area names both appear in each), but
    cleanly split BY POSTAL CODE with 13 real hotels apiece. There is no
    third, distinct "West Augusta" postal cluster in the real data: every
    West Augusta candidate found carries 30907 or 30909. West Augusta is
    therefore RETIRED as a separate corridor and folded into whichever of
    Washington Road (30907) / Gordon Highway (30909) its own postal code
    names.
  - Medical District (Augusta University Health, 30912) returned zero
    discovered hotels of its own; it is reported as a DOWNTOWN OVERLAY
    (like Savannah's River Street / Eastern Wharf), never a separate
    postal-code corridor, unless a later official-site import proves a
    30912 hotel.
  - Martinez and Belair returned zero discovered hotels carrying their own
    distinct postal code (Martinez shares Augusta's 30907); both are
    reported as WASHINGTON ROAD OVERLAYS.
  - Harlem returned zero discovered hotels; reported as an EVANS OVERLAY
    (Harlem's 30814 is folded into the Evans corridor's postal set so a
    later-discovered Harlem hotel still classifies correctly).
  - Hephzibah returned one real discovered candidate at 30815, folded into
    AGS Airport / South Augusta exactly as originally planned.
  - Fort Eisenhower (30905) is kept SEPARATE from Gordon Highway (30909)
    despite marketing overlap: OSM's own address tag for the one candidate
    found there states city=Fort Eisenhower, a first-party geographic
    signal the postal partition honors.

A DATA-QUALITY FLAG CARRIED FORWARD TO CENSUS/IDENTITY (not resolved here)
---------------------------------------------------------------------------
Discovery returned an OSM node named "Holiday Inn Express North Agusta" [sic]
whose OWN address tags state city=Augusta, state=GA, postal_code=30907 --
i.e. a Georgia hotel using "North Augusta" as a marketing/typo phrase in its
OSM name, not a hotel in North Augusta, South Carolina. Its OWN postal code
places it in the Washington Road corridor. Census/identity work must bind it
to augusta-ga by its stated address, never by its OSM display name, and must
never treat it as evidence for a future north-augusta-sc market.

A TRAVEL MARKET, NOT CITY LIMITS, AND NOT A TWO-STATE METRO
-------------------------------------------------------------
Augusta's hotel demand sits in Richmond County lodging cores (Downtown /
Medical District overlay, the Washington Road / I-20 corridor including the
Martinez and Belair overlays, the Gordon Highway corridor, Fort Eisenhower's
public off-post gate corridor, and AGS Airport / South Augusta including the
Hephzibah overlay) plus Columbia County's own towns (Grovetown, Evans
including the Harlem overlay) as CORRIDOR-class edge markets, and a FRINGE of
distant county seats (Thomson, Wrens, Waynesboro, Lincolnton) admitted for
evidence but not expected to carry meaningful inventory. South Carolina
(North Augusta, Aiken, Edgefield, Graniteville, Clearwater) is OBSERVED and
REFUSED BY DEFAULT, preserved for possible future north-augusta-sc / aiken-sc
standalone markets -- 14 real South Carolina hotels were discovered there and
are carried in the census as OUTSIDE, not silently dropped.

FORT EISENHOWER / MILITARY SAFETY
----------------------------------
"Fort Eisenhower" is the current name of the installation historically named
"Fort Gordon"; OSM's own data already reflects the rename (city=Fort
Eisenhower on the one candidate found there). Only PUBLIC, off-post lodging
is ever admitted to this corridor. On-post lodging, government housing and
any restricted-access facility are NEVER census candidates -- not even as a
hold -- regardless of how they are discovered.

MASTERS / TEMPORARY-EVENT LODGING SAFETY
-------------------------------------------
Augusta hosts the Masters Tournament, which generates an unusually large
event-driven private-rental market. Private home rentals, Airbnb/Vrbo
listings, and property-management rental portfolios are NEVER admitted
regardless of how they are discovered, however many bedrooms or however
close to Augusta National they sit. Only public hotels, motels, inns and
extended-stay lodging operated as a single establishment with a front desk
qualify -- the same admission rule every other PTF market uses.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
--------------------------------------------
Augusta V2 is a SOURCE-READY build only. It must not register, participate
globally, or touch canonical live state. The market document goes to the
zone's PROPOSED path, never to the registry's markets/<id>.json.

Nothing here fetches, spends or deploys. (Real, free OSM/Overpass and
Geofabrik-extract discovery already ran, ahead of this script, at
data/discovery/augusta_ga/discovery_001/.)

Outputs:
  scripts/pettripfinder/discovery/config/augusta_ga.json (already written; this
    script does not overwrite the hand-authored cell list, only validates it)
  launch_packages/pettripfinder/markets/proposed/augusta-ga.json
  launch_packages/pettripfinder/markets/reports/augusta_ga_geography_001.json
  launch_packages/pettripfinder/markets/reports/augusta_ga_corridor_registry_001.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DISCOVERY_CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "augusta_ga.json")
#: SHADOW_UNTIL_REGISTERED: the proposed path, never the registry.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "augusta-ga.json")
REPORT_OUT = os.path.join(REPORTS, "augusta_ga_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "augusta_ga_corridor_registry_001.json")

#: Future standalone markets every South Carolina property is preserved for.
FUTURE_SUBMARKET_NORTH_AUGUSTA = "north-augusta-sc"
FUTURE_SUBMARKET_AIKEN = "aiken-sc"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market,
#: finalized against real discovery evidence (44/44 cells, 94 candidates).
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("downtown-medical-district", "Downtown Augusta / Medical District", "Downtown Augusta", "CORE",
     "augusta",
     ["30901", "30902", "30903", "30912"],
     "Downtown Augusta's Riverwalk and historic core (30901/30902/30903) and the Augusta University "
     "Health / Medical District campus (30912), reported as one corridor because the medical district "
     "returned no hotel of its own postal code in real discovery; a future 30912 hotel is reported as "
     "the Medical District overlay of this corridor, never a separate page."),
    ("washington-road", "Washington Road / I-20 / Martinez / Belair", "Washington Road", "CORE", "augusta",
     ["30907"],
     "The Washington Road / I-20 exit 199 hotel cluster (30907): thirteen real hotels discovered, "
     "including several branded 'Washington Rd./I-20' and one branded 'North Agusta' [sic OSM name] "
     "whose own address states Augusta GA 30907, not South Carolina. Martinez (unincorporated Columbia "
     "County, sharing 30907) and Belair are reported as overlays; no distinct 'West Augusta' postal "
     "cluster exists in the real data, so that originally drafted corridor is retired and folded here."),
    ("gordon-highway", "Gordon Highway", "Gordon Highway", "CORE", "augusta",
     ["30909"],
     "The Gordon Highway hotel cluster (30909): thirteen real hotels discovered, several branded "
     "'Fort Gordon Area' or 'Augusta/Fort Gordon' by the brand's own marketing choice -- a marketing "
     "name that never admits or places a property. Distinct from the Fort Eisenhower corridor's own "
     "postal code."),
    ("fort-eisenhower", "Fort Eisenhower", "Fort Eisenhower", "CORE", "fort eisenhower",
     ["30905"],
     "The Fort Eisenhower gate corridor (30905), kept separate from Gordon Highway despite marketing "
     "overlap because OSM's own address tag for the discovered candidate (Candlewood Suites) states "
     "city=Fort Eisenhower, the installation's current name (legacy alias: Fort Gordon). PUBLIC, "
     "off-post lodging only; on-post, government or restricted-access lodging is never a census "
     "candidate."),
    ("ags-south-augusta", "AGS Airport / South Augusta / Hephzibah", "AGS Airport", "CORE", "augusta",
     ["30906", "30815", "30805"],
     "Augusta Regional Airport (AGS) and South Augusta along Peach Orchard Road / Windsor Spring Road "
     "(30906), with Hephzibah (30815, one real candidate discovered) and Blythe (30805, evaluated, no "
     "discovered inventory) folded in as overlays."),
    ("grovetown", "Grovetown", "Grovetown", "CORRIDOR", "grovetown",
     ["30813"],
     "The City of Grovetown at I-20 exits 190-194 in Columbia County: two real hotels discovered "
     "(Avid Hotel, Home2 Suites by Hilton)."),
    ("evans", "Evans / Harlem", "Evans", "CORRIDOR", "evans",
     ["30809", "30814"],
     "Evans, the Columbia County seat area (30809), with Harlem (30814) folded in as an overlay; "
     "zero hotels discovered with either postal code as of this order -- kept as an admitted corridor "
     "so a later official-site-import resolution of an unresolved-ZIP candidate still classifies "
     "correctly, not reported as a page until the publication threshold is met."),
    ("fringe-thomson", "Thomson", "Thomson", "FRINGE", "thomson",
     ["30824"],
     "McDuffie County seat, 30 miles west on I-20: two real candidates discovered, careful fringe per "
     "the order's mandate to evaluate rather than assume inclusion or exclusion."),
    ("fringe-wrens", "Wrens", "Wrens", "FRINGE", "wrens",
     ["30833"],
     "Jefferson County town southwest of Augusta: zero hotels discovered as of this order; kept as an "
     "admitted fringe corridor, not reported until the publication threshold is met."),
    ("fringe-waynesboro", "Waynesboro", "Waynesboro", "FRINGE", "waynesboro",
     ["30830"],
     "Burke County seat south of Augusta: one real candidate discovered."),
    ("fringe-lincolnton", "Lincolnton", "Lincolnton", "FRINGE", "lincolnton",
     ["30817"],
     "Lincoln County seat north of Augusta: zero hotels discovered as of this order; kept as an "
     "admitted fringe corridor, not reported until the publication threshold is met."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. Empty at authoring time.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "augusta ga": "augusta", "fort eisenhower ga": "fort eisenhower", "fort gordon ga": "fort eisenhower",
    "fort gordon": "fort eisenhower", "grovetown ga": "grovetown", "evans ga": "evans",
    "martinez ga": "martinez", "hephzibah ga": "hephzibah", "harlem ga": "harlem",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
NORTH_AUGUSTA_WHY = ("North Augusta, South Carolina: across the Savannah River from downtown Augusta, its "
                     "own municipality and its own postal codes; PRESERVED for the future %s standalone "
                     "market, evaluated and refused here." % FUTURE_SUBMARKET_NORTH_AUGUSTA)
AIKEN_WHY = ("Aiken, South Carolina and its own lodging cluster (Days Inn, Clarion, Hilton Garden Inn, "
             "TownePlace Suites, Fairfield Inn, Econo Lodge, The Willcox, Quality Inn, Hampton Inn, "
             "Americas Best Value Inn -- ten real hotels discovered); PRESERVED for the future %s "
             "standalone market, evaluated and refused here." % FUTURE_SUBMARKET_AIKEN)
OUTSIDE = [
    ("North Augusta", "SC", ["29841", "29842", "29860"], NORTH_AUGUSTA_WHY),
    ("Aiken", "SC", ["29801", "29803"], AIKEN_WHY),
    ("Edgefield", "SC", ["29824"],
     "South Carolina, one real candidate discovered (Quality Inn & Suites); refused by default per the "
     "order's South Carolina boundary rule; preserved for a future South Carolina market."),
    ("Graniteville", "SC", ["29829"],
     "South Carolina; zero hotels discovered as of this order; refused by default; preserved for a "
     "future South Carolina market."),
    ("Clearwater", "SC", ["29822"],
     "South Carolina; zero hotels discovered as of this order; refused by default; preserved for a "
     "future South Carolina market."),
]

#: Bounded observation cells (mirrors scripts/pettripfinder/discovery/config/augusta_ga.json;
#: this list is validated against that file by main(), never regenerates it silently).
CELLS = [
    ("downtown", "Augusta", "Downtown Augusta / Riverwalk", 33.4735, -81.9748, 2500, True),
    ("medical-district", "Augusta", "Medical District / Augusta University Health", 33.4720, -82.0018, 2000, True),
    ("washington-road", "Augusta", "Washington Road / Augusta National / I-20 exit 199", 33.5075, -82.0230, 3000, True),
    ("west-augusta", "Augusta", "West Augusta / Bobby Jones Expressway / Wheeler Road", 33.4870, -82.0430, 3500, True),
    ("gordon-highway", "Augusta", "Gordon Highway", 33.4590, -81.9960, 3500, True),
    ("fort-eisenhower", "Augusta", "Fort Eisenhower gate corridor (public lodging only; legacy Fort Gordon)", 33.4170, -82.1200, 4500, True),
    ("grovetown", "Grovetown", "Grovetown / I-20 exit 190-194", 33.4487, -82.1943, 4000, True),
    ("martinez", "Martinez", "Martinez", 33.5257, -82.0821, 4000, True),
    ("evans", "Evans", "Evans / Columbia County", 33.5457, -82.1290, 4500, True),
    ("harlem", "Harlem", "Harlem (Columbia County, strong-evaluation)", 33.4979, -82.3143, 4000, True),
    ("ags-south-augusta", "Augusta", "AGS Airport / South Augusta / Peach Orchard Road", 33.4000, -81.9800, 4500, True),
    ("hephzibah", "Hephzibah", "Hephzibah (strong-evaluation)", 33.3057, -82.0888, 4000, True),
    ("belair", "Augusta", "Belair (strong-evaluation)", 33.5104, -82.0574, 3000, True),
    ("fringe-thomson", "Thomson", "Thomson (McDuffie County) -- careful fringe, admitting for evidence", 33.4707, -82.5057, 4000, True),
    ("fringe-wrens", "Wrens", "Wrens (Jefferson County) -- careful fringe, admitting for evidence", 33.2079, -82.3874, 3000, True),
    ("fringe-waynesboro", "Waynesboro", "Waynesboro (Burke County) -- careful fringe, admitting for evidence", 33.0904, -82.0146, 4000, True),
    ("fringe-lincolnton", "Lincolnton", "Lincolnton (Lincoln County) -- careful fringe, admitting for evidence", 33.7943, -82.4746, 3000, True),
    ("obs-north-augusta", "North Augusta", "North Augusta SC -- OBSERVATION ONLY", 33.5090, -81.9648, 5000, False),
    ("obs-aiken", "Aiken", "Aiken SC -- OBSERVATION ONLY", 33.5546, -81.7196, 6000, False),
    ("obs-edgefield", "Edgefield", "Edgefield SC -- OBSERVATION ONLY", 33.7871, -81.9265, 5000, False),
    ("obs-graniteville", "Graniteville", "Graniteville SC -- OBSERVATION ONLY", 33.5626, -81.8154, 5000, False),
    ("obs-clearwater", "Clearwater", "Clearwater SC -- OBSERVATION ONLY", 33.5107, -81.7787, 5000, False),
]

BOUNDS = {
    "min_lat": 33.05,
    "max_lat": 33.85,
    "min_lng": -82.55,
    "max_lng": -81.68,
}

#: Reporting overlay only (never membership): named areas that share a postal
#: code with another area. A property is reported in the NEAREST anchor whose
#: radius it falls inside, else "elsewhere".
COVERAGE_AREAS = [
    ("Downtown Augusta", 33.4735, -81.9748, 2.5),
    ("Medical District", 33.4720, -82.0018, 2.0),
    ("Washington Road", 33.5075, -82.0230, 3.5),
    ("Martinez", 33.5257, -82.0821, 3.5),
    ("Belair", 33.5104, -82.0574, 2.5),
    ("Gordon Highway", 33.4590, -81.9960, 3.5),
    ("Fort Eisenhower", 33.4170, -82.1200, 4.5),
    ("AGS Airport / South Augusta", 33.4000, -81.9800, 4.0),
    ("Hephzibah", 33.3057, -82.0888, 4.0),
    ("Grovetown", 33.4487, -82.1943, 4.0),
    ("Evans", 33.5457, -82.1290, 4.5),
    ("Harlem", 33.4979, -82.3143, 4.0),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Augusta" % name),
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
            ("state_code", "GA"),
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
        ("state_code", "SC" if suffix.startswith("obs-") and muni not in ("Rincon",) and
         muni in ("North Augusta", "Aiken", "Edgefield", "Graniteville", "Clearwater") else "GA"),
        ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Augusta, GA metro, medical-district, airport and Fort Eisenhower lodging market (PetTripFinder discovery scope)"),
        ("state", "GA"),
        ("states", ["GA"]),
        ("country", "US"),
        ("market_center", {"lat": 33.4735, "lng": -81.9748}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- "
             "east over North Augusta, Aiken, Graniteville and Clearwater SC, north over Lincolnton, "
             "south over Waynesboro, west over Thomson and Wrens -- so that " + WORK_ORDER + " "
             "classifies those properties on evidence instead of being blind to them. Admission is "
             "decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". An Augusta-Richmond County / Columbia County CSA market: five CORE corridors "
         "(Downtown / Medical District, Washington Road / Martinez / Belair, Gordon Highway, Fort "
         "Eisenhower, AGS Airport / South Augusta / Hephzibah), two Columbia County CORRIDOR-class edge "
         "markets (Grovetown, Evans / Harlem) and four FRINGE county-seat corridors (Thomson, Wrens, "
         "Waynesboro, Lincolnton). South Carolina (North Augusta, Aiken, Edgefield, Graniteville, "
         "Clearwater) is OBSERVED and REFUSED by default, preserved for possible future "
         "north-augusta-sc / aiken-sc standalone markets."),
        ("scope_disclosure",
         "%d bounded cells: %d admitting and %d observation-only." % (
             len(cells), sum(1 for c in cells if c["admitting"]),
             sum(1 for c in cells if not c["admitting"]))),
        ("explicit_hotel_admissions", OrderedDict([
            ("_what_this_is",
             "The explicit-hotel mechanism, so a single legitimate fringe property never becomes a "
             "reason to widen a municipality or a postal code. Empty at authoring time."),
            ("admissions", []),
        ])),
        ("cells", cells),
    ])

    shard = OrderedDict([
        ("schema", "ptf-market/1.1"),
        ("market_id", MARKET_ID),
        ("market_name", "Augusta, Georgia"),
        ("market_slug", MARKET_ID),
        ("state_name", "Georgia"),
        ("state_code", "GA"),
        ("primary_state_code", "GA"),
        ("states", ["GA"]),
        ("primary_city", "Augusta"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Augusta, Georgia | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Augusta -- Downtown and the Medical District, Washington "
         "Road, Gordon Highway, Fort Eisenhower, the Augusta Regional Airport area, Grovetown and Evans "
         "-- with real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Augusta"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. An Augusta-Richmond County / Columbia County CSA market -- not "
         "Augusta's city limits, not a two-state metro. Nothing else admits a property: not a brand's "
         "'Fort Gordon Area' or 'North Augusta' marketing name, not a map pin, not a vacation-rental "
         "listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor. Washington Road (30907) and Gordon "
         "Highway (30909) are each internally mixed by brand-marketing name but cleanly split by "
         "postal code; there is no separate 'West Augusta' postal cluster in the real discovery data."),
        ("_census_membership_note",
         "South Carolina (North Augusta, Aiken, Edgefield, Graniteville, Clearwater) is not absorbed. "
         "A property whose own page states one of their postal codes is OUTSIDE, however it is named -- "
         "including an OSM-discovered hotel named 'Holiday Inn Express North Agusta' [sic] whose own "
         "address states Augusta GA 30907: it binds to augusta-ga by its stated address, never to a "
         "future north-augusta-sc market by its display name. Individual vacation houses, condo units, "
         "rental-management portfolios, Airbnb/Vrbo listings and Masters-week private-home rentals are "
         "never admitted. On-post or restricted-access Fort Eisenhower lodging is never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "3 + 4 -- Augusta travel-market geography and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-15"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to the zone's proposed path only. "
         "No registration, no global participation, no production candidate."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "Augusta-Richmond County's lodging cores (Downtown / Medical District, Washington Road, "
         "Gordon Highway, Fort Eisenhower, AGS Airport / South Augusta) plus Columbia County's own "
         "towns (Grovetown, Evans) as CORRIDOR-class edge markets, and four distant county seats as "
         "FRINGE."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "South Carolina, refused by default with its postal codes."),
        ("revision_from_draft_plan", OrderedDict([
            ("west_augusta", "RETIRED -- no distinct postal cluster in real discovery data; folded "
                              "into Washington Road (30907) and Gordon Highway (30909)."),
            ("medical_district", "Folded into Downtown as an overlay (zero discovered hotels of its "
                                  "own postal code, 30912)."),
            ("martinez", "Folded into Washington Road as an overlay (shares 30907; zero discovered "
                         "hotels of its own)."),
            ("belair", "Folded into Washington Road as an overlay (zero discovered hotels)."),
            ("harlem", "Folded into Evans as an overlay (zero discovered hotels)."),
            ("hephzibah", "Folded into AGS Airport / South Augusta as planned; one real candidate "
                          "discovered at 30815."),
        ])),
        ("osm_data_quality_flag", OrderedDict([
            ("finding",
             "OSM discovery returned a node named 'Holiday Inn Express North Agusta' [sic, OSM's own "
             "typo] whose own address tags state addr:city=Augusta, addr:state=GA, "
             "addr:postcode=30907 -- i.e. a Georgia hotel, not a hotel in North Augusta, South "
             "Carolina."),
            ("disposition",
             "Binds to augusta-ga / Washington Road corridor (30907) by its own stated address. Must "
             "never be treated as evidence for, or merged into, a future north-augusta-sc market. "
             "Carried forward as an explicit flag for census/identity reconciliation."),
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
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count "
         "= 5 verified pet-friendly hotels) is met. No thin corridor page is invented for SEO; every "
         "corridor is show_in_navigation/show_in_sitemap false until a registration order publishes "
         "it. Medical District, Martinez, Belair and Harlem cannot be separate pages under a "
         "postal-code partition; they are reported as overlays."),
        ("coverage_areas_are_a_reporting_overlay",
         "Named areas sharing a postal code with another area (Medical District inside Downtown's "
         "30912-adjacent 30901 grouping; Martinez and Belair inside Washington Road's 30907; Harlem "
         "inside Evans's 30814) are reported from the property's own stated street/city first and a "
         "nearest-anchor overlay on its pin second. The overlay decides nothing about membership or "
         "corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Five cells observe North Augusta, Aiken, Edgefield, Graniteville and Clearwater SC. They "
         "admit nothing; fourteen real hotels were discovered there and are carried in the census as "
         "OUTSIDE with this reason, not silently dropped."),
        ("vacation_rental_and_masters_rule",
         "The census admits hotels, motels, inns, boutique hotels, qualifying resorts and qualifying "
         "lodging establishments operated as lodging businesses: bookable nightly rooms or suites sold "
         "to the public under one establishment name, with an official property page and a front desk "
         "/ on-site hotel operation. It NEVER admits: individual vacation houses; condominium units or "
         "condo complexes rented unit-by-unit; property-management or realty rental portfolios "
         "(including Masters-week private-home rental operations); Airbnb / Vrbo-style listings; "
         "app-only apartment-hotel units without a front desk; ordinary apartment communities; private "
         "residences; and timeshare / vacation-ownership inventory unless that property independently "
         "qualifies as a hotel. On-post, government or restricted-access Fort Eisenhower lodging is "
         "never admitted, not even as a hold. Campgrounds, RV parks, hostels-as-dormitories and "
         "university/military housing are NON_LODGING."),
        ("config_written", os.path.relpath(DISCOVERY_CONFIG, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
        ("discovery_evidence",
         "data/discovery/augusta_ga/discovery_001: 44/44 cells exhausted (36 via local Geofabrik "
         "Georgia + South Carolina extracts after live Overpass rate-limited/timed out at 8 cells; 8 "
         "via live overpass-api.de and overpass.kumi.systems), 94 raw candidates, 0 paid requests."),
    ])
    return config, shard, report, corridors


def coverage_area(lat, lng):
    """The overlay area a coordinate reports under, or None. Reporting only."""
    if lat is None or lng is None:
        return None
    best = None
    for name, la, ln, r in COVERAGE_AREAS:
        dy = (float(lat) - la) * 111.0
        dx = (float(lng) - ln) * 111.0 * math.cos(math.radians(la))
        d = math.hypot(dx, dy)
        if d <= r and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    muni = " ".join((city or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    return {"augusta": "Augusta", "fort eisenhower": "Fort Eisenhower", "grovetown": "Grovetown",
            "evans": "Evans", "martinez": "Martinez", "hephzibah": "Hephzibah",
            "harlem": "Harlem"}.get(muni)


def classify_postal(postal, municipality):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and
    municipality. The one membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = " ".join((municipality or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    for slug, _name, _area, klass, _m, zips, _desc in CORRIDORS:
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

    with open(DISCOVERY_CONFIG, "r", encoding="utf-8") as fh:
        committed_config = json.load(fh)
    committed_cell_ids = sorted(c["cell_id"] for c in committed_config["cells"])
    built_cell_ids = sorted(c["cell_id"] for c in config["cells"])
    if committed_cell_ids != built_cell_ids:
        raise SystemExit("this script's CELLS list has drifted from the committed discovery config -- "
                          "reconcile before writing")

    from scripts.pettripfinder.markets.contract import parse_market
    parse_market(json.loads(json.dumps(shard)))
    if args.write:
        for path, doc in ((SHARD_OUT, shard), (REPORT_OUT, report),
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
