"""PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001 -- Phase 2: the Pinehurst - Southern
Pines - Aberdeen Sandhills traveller lodging market.

Cloned from the Boone - Blowing Rock NC geography helper (7-tuple corridor registry).

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Sandhills, North Carolina traveller lodging market -- the Village of
Pinehurst (the resort district around Pinehurst No. 2, the village centre and the
NC-5 / NC-211 / US-15-501 medical and business ring around FirstHealth Moore
Regional), the Town of Southern Pines (downtown Broad Street, the US-1 strip and
the Mid Pines / Pine Needles golf lodges), the Town of Aberdeen (its US-1 /
US-15-501 / NC-5 hotel concentration) and the Moore County towns that book as
Pinehurst stays -- stated as an explicit four-way rule (CORE / CORRIDOR / FRINGE /
OUTSIDE) before a single hotel is discovered, so no property is admitted or
refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. The PO-box
ZIPs of Pinehurst (28370) and Southern Pines (28388) are claimed by their towns'
corridors, so a property page that prints its box ZIP lands in its own town.

THE CORRIDORS AND WHY
---------------------
CORE       Pinehurst (28374, 28370): the village, the resort district and the
           Moore Regional ring; the Village of Taylortown shares 28374.
           Southern Pines (28387, 28388): downtown, US-1, Midland Road and the golf
           lodges. Aberdeen (28315): US-1 / US-15-501 / NC-5.
CORRIDOR   Pinebluff (28373) -- US-1 four miles south of Aberdeen, the same strip.
           Whispering Pines / Carthage (28327) -- NC-22 and US-15-501 north of
           Southern Pines, 15-20 minutes out; the two towns share one ZIP and the
           county seat's inns book as Pinehurst-area stays.
FRINGE     Vass / Cameron (28394, 28326) -- US-1 north toward Sanford, rural Moore.
           Seven Lakes / West End / Foxfire (27376, 27281) -- NC-211 / NC-73 west of
           Pinehurst, gated golf communities with little public lodging.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not an
           oversight: Robbins / Eagle Springs (northern Moore, 30 minutes up NC-24/27
           and NC-705, its own small cluster); Sanford (Lee County, US-1 north, its
           own market); Fayetteville / Spring Lake / Fort Liberty (Cumberland and the
           Fayetteville market); Raeford (Hoke); Rockingham / Hamlet / Hoffman /
           Ellerbe (Richmond); Laurinburg (Scotland); Candor / Biscoe / Troy
           (Montgomery).

The accounting's route overlay (Pinehurst resort district, the Moore Regional
medical / business ring, Southern Pines downtown, the US-1 corridor, Aberdeen
US-15-501 / NC-5) is REPORTING ONLY and decides nothing about membership.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
Pinehurst - Southern Pines is built while the production release queue is being
drained separately: Fayetteville is live, and five other markets (Jacksonville,
Greenville, Atlanta, Outer Banks, Boone - Blowing Rock) must go live first. This order writes
the market document to the zone's PROPOSED path, never to the registry's
``markets/<id>.json``.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/pinehurst_southern_pines_nc.json
  launch_packages/pettripfinder/markets/proposed/pinehurst-southern-pines-nc.json
  launch_packages/pettripfinder/markets/reports/pinehurst_southern_pines_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/pinehurst_southern_pines_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "pinehurst-southern-pines-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "pinehurst_southern_pines_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "pinehurst-southern-pines-nc.json")
REPORT_OUT = os.path.join(REPORTS, "pinehurst_southern_pines_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "pinehurst_southern_pines_nc_corridor_registry_001.json")

#: No neighbouring cluster is preserved as a future submarket by this order. The
#: constant is kept (empty) because the census helper imports it.
FUTURE_SUBMARKET = ""

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("pinehurst", "Pinehurst", "Pinehurst", "CORE", "pinehurst",
     ["28374", "28370"],
     "The Village of Pinehurst: the historic village centre and the Pinehurst Resort district around "
     "Pinehurst No. 2, the NC-5 / NC-211 / US-15-501 ring around FirstHealth Moore Regional Hospital, and "
     "Taylortown."),
    ("southern-pines", "Southern Pines", "Southern Pines", "CORE", "southern pines",
     ["28387", "28388"],
     "The Town of Southern Pines: downtown Broad Street, the US-1 Sandhills Boulevard strip, Midland Road "
     "and the Mid Pines / Pine Needles golf lodges."),
    ("aberdeen", "Aberdeen", "Aberdeen", "CORE", "aberdeen",
     ["28315"],
     "The Town of Aberdeen: the US-1 / US-15-501 / NC-5 hotel concentration and the historic downtown."),
    ("pinebluff", "Pinebluff", "Pinebluff", "CORRIDOR", "pinebluff",
     ["28373"],
     "The Town of Pinebluff on US-1, four miles south of Aberdeen on the same strip."),
    ("whispering-pines-carthage", "Whispering Pines / Carthage", "Whispering Pines & Carthage", "CORRIDOR",
     "carthage",
     ["28327"],
     "Whispering Pines on NC-22 and the county seat of Carthage on US-15-501, 15-20 minutes north of "
     "Southern Pines; the two towns share one postal code."),
    ("vass-cameron", "Vass / Cameron", "Vass & Cameron", "FRINGE", "vass",
     ["28394", "28326"],
     "Rural Moore County on US-1 north toward Sanford: Vass, Lakeview and Cameron."),
    ("seven-lakes-west-end", "Seven Lakes / West End / Foxfire", "Seven Lakes, West End & Foxfire", "FRINGE",
     "west end",
     ["27376", "27281"],
     "NC-211 and NC-73 west of Pinehurst: the gated golf communities of Seven Lakes and Foxfire, West End "
     "and Jackson Springs."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. Empty at authoring time; a later
#: ruling adds a row, never a ZIP.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "southernpines": "southern pines", "so pines": "southern pines", "s pines": "southern pines",
    "village of pinehurst": "pinehurst", "whispering pines nc": "whispering pines",
    "pine bluff": "pinebluff", "foxfire village": "foxfire", "village of foxfire": "foxfire",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Robbins / Eagle Springs (northern Moore County)", "NC", ["27325", "27242"],
     "northern Moore County on NC-24/27 and NC-705, 30 minutes from Pinehurst; a separate pottery-country "
     "cluster with its own small lodging; evaluated and refused."),
    ("Sanford / Broadway (Lee County)", "NC", ["27330", "27332", "27505"],
     "Lee County on US-1 north, 30 minutes from Southern Pines; its own traveller market; refused by name."),
    ("Fayetteville / Spring Lake / Fort Liberty / Hope Mills (Cumberland)", "NC",
     ["28301", "28303", "28304", "28305", "28306", "28307", "28308", "28310", "28311", "28312", "28314",
      "28390", "28348"],
     "Cumberland County and the Fayetteville market (registered separately); refused by name."),
    ("Raeford (Hoke County)", "NC", ["28376"],
     "Hoke County on US-401 / NC-211 south-east; its own market; refused by name."),
    ("Rockingham / Hamlet / Hoffman / Ellerbe (Richmond County)", "NC", ["28379", "28345", "28347", "28338"],
     "Richmond County on US-1 / US-74 south-west; its own markets; refused by name."),
    ("Laurinburg (Scotland County)", "NC", ["28352"],
     "Scotland County on US-74 / US-401; its own market; refused by name."),
    ("Candor / Biscoe / Troy / Star (Montgomery County)", "NC", ["27229", "27209", "27371", "27356"],
     "Montgomery County on NC-24/27 and I-73 to the north-west; refused by name."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the refused neighbours so this order classifies those properties
#: on evidence.
CELLS = [
    ("pinehurst-village", "Pinehurst", "Pinehurst village / resort district", 35.1954, -79.4695, 2500, True),
    ("pinehurst-moore-regional", "Pinehurst", "Pinehurst NC-5 / Moore Regional ring", 35.1880, -79.4500, 2500, True),
    ("southern-pines-downtown", "Southern Pines", "Southern Pines downtown / Broad Street", 35.1740, -79.3923, 2000, True),
    ("southern-pines-us-1", "Southern Pines", "Southern Pines US-1 Sandhills Boulevard", 35.1650, -79.4050, 3000, True),
    ("southern-pines-golf", "Southern Pines", "Mid Pines / Pine Needles / Midland Road", 35.1560, -79.4250, 2500, True),
    ("aberdeen", "Aberdeen", "Aberdeen US-1 / US-15-501 / NC-5", 35.1400, -79.4300, 3500, True),
    ("pinebluff", "Pinebluff", "Pinebluff US-1", 35.1090, -79.4722, 2500, True),
    ("whispering-pines", "Whispering Pines", "Whispering Pines NC-22", 35.2557, -79.3720, 3500, True),
    ("carthage", "Carthage", "Carthage US-15-501", 35.3460, -79.4170, 3500, True),
    ("vass-cameron", "Vass", "Vass / Lakeview / Cameron", 35.2900, -79.2700, 6000, True),
    ("seven-lakes-west-end", "West End", "Seven Lakes / West End / Foxfire", 35.2300, -79.5600, 7000, True),
    # observation only -- refused neighbours
    ("obs-robbins", "Robbins", "Robbins / Eagle Springs -- OBSERVATION ONLY", 35.4000, -79.5800, 6000, False),
    ("obs-sanford", "Sanford", "Sanford -- OBSERVATION ONLY", 35.4600, -79.1900, 5000, False),
    ("obs-raeford", "Raeford", "Raeford -- OBSERVATION ONLY", 34.9810, -79.2240, 4000, False),
    ("obs-rockingham", "Rockingham", "Rockingham / Hoffman -- OBSERVATION ONLY", 34.9900, -79.6800, 6000, False),
]

BOUNDS = {
    "min_lat": 34.95,
    "max_lat": 35.50,
    "min_lng": -79.75,
    "max_lng": -79.15,
}

#: Reporting overlay only (never membership). (area, anchor_lat, anchor_lng, radius_km)
COVERAGE_AREAS = [
    ("Pinehurst village / resort district", 35.1954, -79.4695, 1.8),
    ("Pinehurst Moore Regional medical / business ring", 35.1880, -79.4500, 2.5),
    ("Southern Pines downtown", 35.1740, -79.3923, 1.5),
    ("US-1 corridor", 35.1550, -79.4150, 3.5),
    ("Aberdeen US-15-501 / NC-5", 35.1400, -79.4300, 3.0),
]

#: Street wording on the property's OWN address that names a road corridor.
STREET_OVERLAY = [
    (re.compile(r"\bus[- ]?(hwy |highway )?1\b(?!\d|5)|\bhwy\.? 1\b(?!\d|5)|sandhills blvd|sandhills boulevard"
                r"|u\.?s\.? 1 (north|south|hwy)", re.I), "US-1 corridor"),
    (re.compile(r"15[- /]?501|\bnc[- ]?(hwy )?5\b|\bhwy\.? 5\b|highway 5\b", re.I), "Aberdeen US-15-501 / NC-5"),
]

#: The Pinehurst resort district, by own stated street.
PINEHURST_RESORT_STREETS = re.compile(
    r"carolina vista|cherokee r|community r|market sq|chinquapin|magnolia r|dogwood r|azalea r"
    r"|beulah hill|mcindoe|village green|mcCaskill|cameron r|pine crest|burning tree", re.I)


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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Pinehurst - Southern Pines" % name),
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
        ("market_name", "Pinehurst - Southern Pines - Aberdeen, NC Sandhills lodging market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 35.170, "lng": -79.430}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- north to "
             "Robbins and Sanford, south to Raeford and west toward Rockingham -- so that " + WORK_ORDER +
             " classifies those properties on evidence instead of being blind to them. Admission is decided by "
             "the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A Sandhills golf-and-resort market: Pinehurst, Southern Pines and Aberdeen are CORE; "
         "Pinebluff and Whispering Pines / Carthage are CORRIDOR; Vass / Cameron and Seven Lakes / West End / "
         "Foxfire are FRINGE. Robbins, Sanford, Fayetteville, Raeford, Rockingham, Laurinburg and Montgomery "
         "County are OBSERVED or named, and REFUSED."),
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
        ("market_name", "Pinehurst – Southern Pines – Aberdeen, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Pinehurst"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Pinehurst, Southern Pines & Aberdeen, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Pinehurst, Southern Pines and Aberdeen, North Carolina -- the "
         "Sandhills golf resorts, US-1 and Moore County -- with real pet fees and policies read from each "
         "hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Pinehurst – Southern Pines"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A Moore County Sandhills market -- Pinehurst, Southern Pines, Aberdeen and "
         "the towns that book as Pinehurst stays -- not the whole Sandhills region. Nothing else admits a "
         "property: not a 'Pinehurst' marketing name, not a map pin, not a golf villa or vacation-rental "
         "listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor, PO-box ZIPs (28370, 28388) with their "
         "towns. Whispering Pines and Carthage share 28327 and are one corridor."),
        ("_census_membership_note",
         "Robbins, Sanford, Fayetteville, Raeford, Rockingham and Laurinburg are not absorbed. A property "
         "whose own page states one of their postal codes is OUTSIDE, however it is named. Private club "
         "guest houses, member-only accommodations, golf villas and condos, individual golf-course homes, "
         "property-management portfolios and timeshare inventory are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Pinehurst - Southern Pines - Aberdeen Sandhills geography and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-14"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Jacksonville, Greenville, Atlanta, Outer "
         "Banks and Boone - Blowing Rock to go live (Fayetteville is live)."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "The lodging a visitor means by 'Pinehurst', 'Southern Pines' or 'Aberdeen': the resort village and "
         "its golf lodges, the Southern Pines downtown and US-1 strip, the Aberdeen highway hotels and the "
         "Moore Regional medical / business ring; Pinebluff and Whispering Pines / Carthage as CORRIDOR; "
         "rural Moore to the north and west as FRINGE."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("rules", OrderedDict([
            ("CORE", "A property whose own page states 28374 / 28370 (Pinehurst, Taylortown), 28387 / 28388 "
                     "(Southern Pines) or 28315 (Aberdeen)."),
            ("CORRIDOR", "A property whose own page states 28373 (Pinebluff) or 28327 (Whispering Pines / "
                         "Carthage): contiguous towns on US-1 and NC-22 / US-15-501 whose lodging books as a "
                         "Pinehurst-area stay; never CORE."),
            ("FRINGE", "A property whose own page states 28394 / 28326 (Vass, Lakeview, Cameron) or 27376 / "
                       "27281 (Seven Lakes, West End, Foxfire, Jackson Springs): rural Moore County, admitted "
                       "only as a hotel establishment under the lodging contract."),
            ("OUTSIDE", "Every other postal code, and the named refusals below with their reasons."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Pinehurst", "ADMITTED (CORE, pinehurst, 28374 / 28370)."),
            ("Village of Pinehurst / resort district", "ADMITTED (CORE) -- reported as the resort-district overlay."),
            ("Pinehurst No. 2 / golf resort lodging", "ADMITTED only as public hotel identities under the lodging "
                                                       "contract; resort villas, condos and member cottages are refused."),
            ("Southern Pines downtown / US-1 corridor", "ADMITTED (CORE, southern-pines, 28387 / 28388)."),
            ("Aberdeen US-1 / NC-5 hotel concentration", "ADMITTED (CORE, aberdeen, 28315)."),
            ("Moore County medical / business cluster", "ADMITTED where its ZIP is admitted; FirstHealth Moore "
                                                         "Regional sits in Pinehurst 28374, reported as an overlay "
                                                         "and never a separate corridor."),
            ("Taylortown", "ADMITTED with Pinehurst -- it shares 28374."),
            ("Whispering Pines", "ADMITTED (CORRIDOR, whispering-pines-carthage, 28327)."),
            ("Pinebluff", "ADMITTED (CORRIDOR, pinebluff, 28373) -- the US-1 strip continued south of Aberdeen."),
            ("Carthage", "ADMITTED (CORRIDOR, whispering-pines-carthage, 28327) -- the county seat, 20 minutes north."),
            ("Vass", "ADMITTED (FRINGE, vass-cameron, 28394)."),
            ("Cameron", "ADMITTED (FRINGE, vass-cameron, 28326)."),
            ("Seven Lakes", "ADMITTED (FRINGE, seven-lakes-west-end, 27376) -- a gated golf community; its "
                            "owner homes are never lodging."),
            ("West End", "ADMITTED (FRINGE, seven-lakes-west-end, 27376)."),
            ("Foxfire", "ADMITTED (FRINGE, seven-lakes-west-end, 27281 Jackson Springs)."),
            ("Robbins", "OUTSIDE -- northern Moore County, 30 minutes up NC-24/27; not a Pinehurst stay."),
            ("Sanford", "OUTSIDE -- Lee County, its own market."),
            ("Fayetteville", "OUTSIDE -- the Fayetteville market."),
            ("Rockingham", "OUTSIDE -- Richmond County, its own market."),
            ("Laurinburg", "OUTSIDE -- Scotland County, its own market."),
            ("Raeford", "OUTSIDE -- Hoke County, its own market."),
        ])),
        ("golf_resort_lodging_rule",
         "Qualifying public hotel / resort lodging is admitted under the existing lodging contract: bookable "
         "nightly rooms sold to the public under one establishment name with an official property page. "
         "A resort complex is decided by PREMISES: a separately named, separately addressed hotel building "
         "(the Carolina, the Holly Inn and the Manor at Pinehurst Resort) is its own identity; the resort's "
         "villas, condominiums and cottages are not hotel identities. Private club guest houses, member-only "
         "accommodations, rental villas, individual golf-course homes, property-management portfolios and "
         "timeshare units that do not independently qualify are refused with their reason."),
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
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = "
         "5 verified pet-friendly hotels) is met. No thin corridor page is invented for SEO; every "
         "corridor is show_in_navigation/show_in_sitemap false until a registration order publishes it."),
        ("coverage_areas_are_a_reporting_overlay",
         "The accounting reports a Pinehurst row as the resort district when its own street is a village "
         "street, else as the Moore Regional ring; a Southern Pines or Aberdeen row as the US-1 corridor when "
         "its own street is US-1 / Sandhills Boulevard, as Aberdeen US-15-501 / NC-5 when its street names "
         "those roads, else by its town. The overlay decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Four cells observe Robbins, Sanford, Raeford and Rockingham. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, qualifying resorts and qualifying lodging establishments "
         "operated as lodging businesses: bookable nightly rooms or suites sold to the public under one "
         "establishment name, with an official property page and a front desk / on-site hotel operation. "
         "It NEVER admits: private club guest houses or member-only accommodations; golf villas, condominium "
         "units or condo complexes rented unit-by-unit through owners or agencies; individual golf-course "
         "homes or cottages; property-management or realty rental portfolios; Airbnb / Vrbo-style listings; "
         "and TIMESHARE / vacation-ownership inventory unless that property independently qualifies as a "
         "hotel. Every such row is recorded NON_LODGING with its reason. A bed and breakfast is admitted only "
         "when it operates as an inn with bookable rooms on its own premises and an official site. "
         "Campgrounds, RV parks, equestrian barns and military lodging are NON_LODGING."),
        ("config_written", os.path.relpath(CONFIG_OUT, _DASH).replace("\\", "/")),
        ("market_document_written", os.path.relpath(SHARD_OUT, _DASH).replace("\\", "/")),
        ("cells_total", len(cells)),
        ("cells_admitting", sum(1 for c in cells if c["admitting"])),
        ("cells_observation_only", sum(1 for c in cells if not c["admitting"])),
    ])
    return config, shard, report, corridors


def corridor_municipality():
    """slug -> the municipality the corridor principally sits in (name attachment only)."""
    return {slug: muni for slug, _n, _a, _k, muni, _z, _d in CORRIDORS}


def coverage_area(lat, lng):
    """The overlay area a coordinate reports under, or None. Reporting only."""
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


def route_overlay(corridor_slug, street, lat, lng):
    """The order's named route area a census row reports under. Reporting only."""
    street = street or ""
    if corridor_slug == "pinehurst":
        if PINEHURST_RESORT_STREETS.search(street):
            return "Pinehurst village / resort district"
        area = coverage_area(lat, lng)
        if area == "Pinehurst village / resort district":
            return area
        return "Pinehurst Moore Regional medical / business ring"
    if corridor_slug in ("southern-pines", "aberdeen"):
        for rx, name in STREET_OVERLAY:
            if rx.search(street):
                return name
        if corridor_slug == "southern-pines":
            return "Southern Pines downtown"
        return "Aberdeen US-15-501 / NC-5"
    if corridor_slug == "pinebluff":
        return "US-1 corridor"
    if corridor_slug == "whispering-pines-carthage":
        return "Whispering Pines / Carthage"
    if corridor_slug == "vass-cameron":
        return "Vass / Cameron"
    if corridor_slug == "seven-lakes-west-end":
        return "Seven Lakes / West End / Foxfire"
    return None


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    muni = " ".join((city or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    return {"pinehurst": "Pinehurst", "southern pines": "Southern Pines", "aberdeen": "Aberdeen",
            "pinebluff": "Pinebluff", "whispering pines": "Whispering Pines", "carthage": "Carthage",
            "vass": "Vass", "cameron": "Cameron", "west end": "West End", "seven lakes": "Seven Lakes",
            "foxfire": "Foxfire", "jackson springs": "Jackson Springs", "taylortown": "Taylortown",
            "lakeview": "Lakeview"}.get(muni)


def is_future_submarket(postal):
    """No future submarket is preserved by this order."""
    return False


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
