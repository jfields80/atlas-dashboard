"""PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 -- Phase 2: the Hickory - Newton - Conover traveller
lodging market.

Cloned from the Pinehurst - Southern Pines NC geography helper (7-tuple corridor registry).

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Hickory, North Carolina traveller lodging market -- the City of
Hickory (the I-40 hotel concentration at exits 123 / 125 / 126, the US-321
south-west strip, downtown Union Square and the Lenoir-Rhyne / Catawba Valley
Boulevard business district, with Long View and Mountain View, which share
Hickory's postal codes), the City of Conover (its I-40 exits 128 / 130 / 131)
and the City of Newton (the Catawba County seat) -- stated as an explicit
four-way rule (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single hotel is
discovered, so no property is admitted or refused after the fact to make a
number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement. Hickory's
PO-box ZIP (28603) is claimed by the Hickory corridor.

THE CORRIDORS AND WHY
---------------------
CORE       Hickory (28601, 28602, 28603): downtown, the I-40 exits, US-321 south-west,
           and the towns of Long View and Mountain View, which carry Hickory ZIPs.
           Conover (28613): the I-40 exits 128-131 and US-70.
           Newton (28658): the county seat, NC-16 and US-321 Business.
CORRIDOR   Claremont (28610) -- I-40 exit 135, eight minutes east of Conover on the same
           interstate hotel run.
           Granite Falls / Sawmills (28630) -- US-321 north of Hickory across the
           Catawba River, ten minutes from exit 123; the same US-321 strip.
FRINGE     Hildebran / Icard (28637, 28666) -- I-40 exits 118-119 west of Long View,
           Burke County's Hickory side. Maiden (28650) -- US-321 south, Catawba County.
           Catawba (28609) -- I-40 exit 138 toward Statesville. Hudson (28638) --
           US-321 between Granite Falls and Lenoir.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not an
           oversight. Lenoir (28645, PO 28633) is evaluated and preserved as a FUTURE
           SUBMARKET: the Caldwell County seat is 20-25 minutes up US-321 with its own
           hotel cluster around US-321 / Blowing Rock Boulevard and NC-18 that serves
           Lenoir itself (furniture industry, CCC&TI, the Blue Ridge gateway), not
           the Hickory I-40 stay. Morganton / Valdese (Burke, I-40 west), Statesville
           (Iredell, I-40 / I-77), Taylorsville (Alexander), Lincolnton (Lincoln),
           Denver / Sherrills Ford / Mooresville (Lake Norman and the Charlotte exurbs)
           and Boone / Blowing Rock (registered separately) are their own markets.

The accounting's route overlay (Hickory downtown / central, I-40 Hickory, US-321
Hickory, Long View / Mountain View, Conover, Newton) is REPORTING ONLY and decides
nothing about membership.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
Hickory is built while the production release queue is drained separately
(Greenville is live; Jacksonville, Atlanta, Outer Banks, Boone - Blowing Rock and
Pinehurst - Southern Pines wait ahead). This order writes the market document to
the zone's PROPOSED path, never to the registry's ``markets/<id>.json``.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/hickory_nc.json
  launch_packages/pettripfinder/markets/proposed/hickory-nc.json
  launch_packages/pettripfinder/markets/reports/hickory_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/hickory_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hickory-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "hickory_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "hickory-nc.json")
REPORT_OUT = os.path.join(REPORTS, "hickory_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "hickory_nc_corridor_registry_001.json")

#: Lenoir is preserved as a future submarket (its own US-321 / Caldwell County cluster).
FUTURE_SUBMARKET = "lenoir-nc"
FUTURE_SUBMARKET_ZIPS = ("28645", "28633")

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("hickory", "Hickory", "Hickory", "CORE", "hickory",
     ["28601", "28602", "28603"],
     "The City of Hickory: downtown Union Square, the I-40 hotel concentration at exits 123 (US-321), "
     "125 (Lenoir-Rhyne Boulevard) and 126 (McDonald Parkway), Catawba Valley Boulevard, the US-321 "
     "south-west strip, and the towns of Long View and Mountain View, which share Hickory's postal codes."),
    ("conover", "Conover", "Conover", "CORE", "conover",
     ["28613"],
     "The City of Conover: I-40 exits 128, 130 and 131, US-70 and the Conover Station district."),
    ("newton", "Newton", "Newton", "CORE", "newton",
     ["28658"],
     "The City of Newton, the Catawba County seat: NC-16, US-321 Business and the downtown courthouse "
     "square."),
    ("claremont", "Claremont", "Claremont", "CORRIDOR", "claremont",
     ["28610"],
     "The City of Claremont at I-40 exit 135, eight minutes east of Conover on the same interstate run."),
    ("granite-falls-sawmills", "Granite Falls / Sawmills", "Granite Falls & Sawmills", "CORRIDOR",
     "granite falls",
     ["28630"],
     "US-321 north of Hickory across the Catawba River: Granite Falls and Sawmills, ten minutes from "
     "I-40 exit 123."),
    ("hildebran-icard", "Hildebran / Icard", "Hildebran & Icard", "FRINGE", "hildebran",
     ["28637", "28666"],
     "I-40 exits 118-119 west of Long View: Hildebran and Icard, the Hickory side of Burke County."),
    ("maiden", "Maiden", "Maiden", "FRINGE", "maiden",
     ["28650"],
     "The Town of Maiden on US-321 south, Catawba County."),
    ("catawba", "Catawba", "Catawba", "FRINGE", "catawba",
     ["28609"],
     "The Town of Catawba at I-40 exit 138 toward Statesville."),
    ("hudson", "Hudson", "Hudson", "FRINGE", "hudson",
     ["28638"],
     "The Town of Hudson on US-321 between Granite Falls and Lenoir."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. Empty at authoring time; a later
#: ruling adds a row, never a ZIP.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "longview": "long view", "long view nc": "long view", "mtn view": "mountain view",
    "granite fls": "granite falls", "saw mills": "sawmills", "st stephens": "hickory",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
OUTSIDE = [
    ("Lenoir (Caldwell County) -- FUTURE SUBMARKET lenoir-nc", "NC", ["28645", "28633"],
     "the Caldwell County seat, 20-25 minutes up US-321 from I-40 exit 123 past Granite Falls and Hudson; "
     "its hotels cluster on US-321 / Blowing Rock Boulevard and NC-18 and serve Lenoir itself and the Blue "
     "Ridge gateway rather than the Hickory I-40 stay; evaluated and preserved as a future submarket."),
    ("Morganton / Valdese / Drexel / Connelly Springs / Rutherford College (Burke County)", "NC",
     ["28655", "28680", "28690", "28619", "28612", "28671"],
     "Burke County on I-40 west, 20-30 minutes from Hickory; the Morganton market; refused by name."),
    ("Statesville / Troutman (Iredell County)", "NC", ["28625", "28677", "28687", "28166"],
     "Iredell County at I-40 / I-77, 30 minutes east; its own market; refused by name."),
    ("Taylorsville / Stony Point / Hiddenite (Alexander County)", "NC", ["28681", "28678", "28636"],
     "Alexander County on NC-16 / NC-90, 25 minutes north-east; a separate small county-seat cluster; "
     "evaluated and refused."),
    ("Lincolnton / Iron Station / Vale / Cherryville (Lincoln and Gaston)", "NC",
     ["28092", "28093", "28080", "28168", "28021"],
     "Lincoln County on US-321 south past Maiden; its own market; refused by name."),
    ("Denver / Sherrills Ford / Terrell / Mooresville (Lake Norman)", "NC",
     ["28037", "28673", "28682", "28115", "28117"],
     "the Lake Norman shore and the Charlotte exurbs; refused by name."),
    ("Boone / Blowing Rock (Watauga County)", "NC", ["28607", "28608", "28605"],
     "the Boone - Blowing Rock market (built separately); refused by name."),
    ("Collettsville / Patterson (Caldwell County)", "NC", ["28611", "28661"],
     "rural Caldwell County north-west of Lenoir; refused by name."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the refused neighbours so this order classifies those properties
#: on evidence.
CELLS = [
    ("hickory-downtown", "Hickory", "Hickory downtown / Union Square", 35.7334, -81.3413, 2000, True),
    ("hickory-i40-123", "Hickory", "Hickory I-40 exit 123 / US-321", 35.7128, -81.3690, 2500, True),
    ("hickory-i40-125-126", "Hickory", "Hickory I-40 exits 125-126 / Catawba Valley Blvd", 35.7130, -81.3120, 2500, True),
    ("hickory-us321-sw", "Hickory", "Hickory US-321 south-west / Mountain View", 35.6900, -81.3750, 3500, True),
    ("long-view", "Long View", "Long View", 35.7223, -81.3854, 2000, True),
    ("conover", "Conover", "Conover I-40 exits 128-131", 35.7070, -81.2450, 3500, True),
    ("newton", "Newton", "Newton", 35.6699, -81.2215, 4000, True),
    ("claremont", "Claremont", "Claremont I-40 exit 135", 35.7143, -81.1462, 3000, True),
    ("granite-falls", "Granite Falls", "Granite Falls / Sawmills US-321", 35.7960, -81.4309, 4000, True),
    ("hildebran-icard", "Hildebran", "Hildebran / Icard I-40", 35.7184, -81.4190, 4000, True),
    ("maiden", "Maiden", "Maiden US-321", 35.5757, -81.2118, 3500, True),
    ("catawba", "Catawba", "Catawba I-40 exit 138", 35.7082, -81.0770, 3000, True),
    ("hudson", "Hudson", "Hudson US-321", 35.8479, -81.4960, 3000, True),
    # observation only -- refused neighbours
    ("obs-lenoir", "Lenoir", "Lenoir -- OBSERVATION ONLY (future submarket)", 35.9140, -81.5390, 5000, False),
    ("obs-morganton-valdese", "Morganton", "Morganton / Valdese -- OBSERVATION ONLY", 35.7454, -81.6300, 9000, False),
    ("obs-statesville", "Statesville", "Statesville -- OBSERVATION ONLY", 35.7826, -80.8873, 6000, False),
    ("obs-taylorsville", "Taylorsville", "Taylorsville -- OBSERVATION ONLY", 35.9215, -81.1765, 4000, False),
    ("obs-lincolnton", "Lincolnton", "Lincolnton -- OBSERVATION ONLY", 35.4737, -81.2545, 4000, False),
    ("obs-denver", "Denver", "Denver / Lake Norman west -- OBSERVATION ONLY", 35.5310, -81.0300, 5000, False),
]

BOUNDS = {
    "min_lat": 35.45,
    "max_lat": 35.98,
    "min_lng": -81.72,
    "max_lng": -80.85,
}

#: Reporting overlay only (never membership). (area, anchor_lat, anchor_lng, radius_km)
COVERAGE_AREAS = [
    ("Hickory downtown / central", 35.7334, -81.3413, 1.6),
    ("I-40 Hickory", 35.7128, -81.3690, 1.3),
    ("I-40 Hickory", 35.7133, -81.3222, 1.4),
    ("I-40 Hickory", 35.7130, -81.3030, 1.3),
    ("US-321 Hickory", 35.6990, -81.3790, 2.0),
    ("US-321 Hickory", 35.7600, -81.3740, 1.8),
    ("Long View / Mountain View", 35.7223, -81.3854, 1.0),
    ("Long View / Mountain View", 35.6832, -81.3690, 2.2),
]

#: Street wording on the property's OWN address that names a road corridor (Hickory only).
STREET_OVERLAY = [
    (re.compile(r"lenoir[- ]?rhyne|catawba valley|mcdonald p(ar)?kwy|13th av(e|enue) dr|10th av(e|enue) dr"
                r"|conover blvd|\bus[- ]?(hwy |highway )?70\b|\bhwy\.? 70\b|highway 70\b", re.I), "I-40 Hickory"),
    (re.compile(r"hickory blvd|\bus[- ]?(hwy |highway )?321\b|\bhwy\.? 321\b|highway 321\b", re.I), "US-321 Hickory"),
    (re.compile(r"union sq|\bmain av|\b(1st|2nd|3rd) av(e|enue)? n|\bcenter st", re.I), "Hickory downtown / central"),
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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Hickory" % name),
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
        ("market_name", "Hickory - Newton - Conover, NC lodging market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 35.720, "lng": -81.300}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- north to "
             "Lenoir and Taylorsville, west to Morganton, east to Statesville and south to Lincolnton and "
             "Denver -- so that " + WORK_ORDER +
             " classifies those properties on evidence instead of being blind to them. Admission is decided by "
             "the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". An I-40 / US-321 business-travel market: Hickory (with Long View and Mountain View), "
         "Conover and Newton are CORE; Claremont and Granite Falls / Sawmills are CORRIDOR; Hildebran / Icard, "
         "Maiden, Catawba and Hudson are FRINGE. Lenoir is a future submarket. Morganton, Statesville, "
         "Taylorsville, Lincolnton, Denver and Boone are OBSERVED or named, and REFUSED."),
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
        ("market_name", "Hickory – Newton – Conover, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Hickory"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Hickory, Newton & Conover, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Hickory, Newton and Conover, North Carolina -- the I-40 and US-321 "
         "hotel corridors and Catawba County -- with real pet fees and policies read from each hotel's own "
         "official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Hickory – Newton – Conover"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A Catawba Valley market -- Hickory, Conover, Newton and the I-40 / US-321 "
         "towns that book as Hickory stays -- not the whole Unifour region. Nothing else admits a property: "
         "not a 'Hickory' marketing name, not a map pin, not an apartment or corporate-housing listing, not "
         "a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor; Hickory's PO-box ZIP (28603) with Hickory. "
         "Long View and Mountain View carry Hickory ZIPs and are part of the Hickory corridor."),
        ("_census_membership_note",
         "Lenoir, Morganton, Statesville, Taylorsville, Lincolnton and Denver are not absorbed. A property "
         "whose own page states one of their postal codes is OUTSIDE, however it is named. Apartment "
         "communities, corporate housing, individual short-term rentals, campgrounds, assisted-living and "
         "student housing are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Hickory - Newton - Conover geography and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-14"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for the release queue (Greenville is live)."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "The lodging a visitor means by 'Hickory', 'Conover' or 'Newton': the Hickory I-40 hotel "
         "concentration, the US-321 south-west strip, downtown Hickory and Lenoir-Rhyne, Long View and Mountain "
         "View, the Conover I-40 exits and Newton; Claremont (I-40 east) and Granite Falls / Sawmills (US-321 "
         "north) as CORRIDOR; Hildebran / Icard, Maiden, Catawba and Hudson as FRINGE."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("rules", OrderedDict([
            ("CORE", "A property whose own page states 28601 / 28602 / 28603 (Hickory, Long View, Mountain "
                     "View), 28613 (Conover) or 28658 (Newton)."),
            ("CORRIDOR", "A property whose own page states 28610 (Claremont, I-40 exit 135) or 28630 (Granite "
                         "Falls / Sawmills, US-321 north): contiguous interstate / US-321 towns whose lodging "
                         "books as a Hickory stay; never CORE."),
            ("FRINGE", "A property whose own page states 28637 / 28666 (Hildebran, Icard), 28650 (Maiden), "
                       "28609 (Catawba) or 28638 (Hudson): admitted only as a hotel establishment under the "
                       "lodging contract."),
            ("OUTSIDE", "Every other postal code, and the named refusals below with their reasons."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Hickory", "ADMITTED (CORE, hickory, 28601 / 28602 / 28603)."),
            ("Hickory I-40 hotel corridor", "ADMITTED (CORE, hickory) -- exits 123 / 125 / 126; reported as an "
                                            "overlay."),
            ("US-321 / southwest Hickory", "ADMITTED (CORE, hickory) -- reported as an overlay."),
            ("Downtown / central Hickory", "ADMITTED (CORE, hickory) -- reported as an overlay."),
            ("Conover I-40", "ADMITTED (CORE, conover, 28613)."),
            ("Newton commercial lodging", "ADMITTED (CORE, newton, 28658)."),
            ("Long View", "ADMITTED with Hickory -- the town carries Hickory postal codes 28601 / 28602 and sits "
                          "at I-40 exit 123 / 121."),
            ("Mountain View", "ADMITTED with Hickory -- the community carries Hickory postal code 28602."),
            ("Claremont", "ADMITTED (CORRIDOR, claremont, 28610) -- I-40 exit 135."),
            ("Granite Falls", "ADMITTED (CORRIDOR, granite-falls-sawmills, 28630) -- US-321, ten minutes north."),
            ("Sawmills", "ADMITTED with Granite Falls (28630)."),
            ("Maiden", "ADMITTED (FRINGE, maiden, 28650) -- US-321 south, Catawba County."),
            ("Hildebran / Icard", "ADMITTED (FRINGE, hildebran-icard, 28637 / 28666) -- I-40 exits 118-119."),
            ("Catawba", "ADMITTED (FRINGE, catawba, 28609) -- I-40 exit 138."),
            ("Hudson", "ADMITTED (FRINGE, hudson, 28638) -- US-321 toward Lenoir."),
            ("Lenoir", "OUTSIDE -- FUTURE SUBMARKET lenoir-nc. Evaluated explicitly: 20-25 minutes up US-321 past "
                       "two towns, its own county seat with a hotel cluster that serves Lenoir and the Blue Ridge "
                       "gateway; a separate lodging cluster, preserved for a future market."),
            ("Denver", "OUTSIDE -- Lake Norman west shore, Lincoln County; a Charlotte exurb."),
            ("Taylorsville", "OUTSIDE -- Alexander County seat, 25 minutes north-east, its own small cluster."),
            ("Morganton", "OUTSIDE -- Burke County, its own I-40 market."),
            ("Statesville", "OUTSIDE -- Iredell County, its own I-40 / I-77 market."),
            ("Boone", "OUTSIDE -- the Boone - Blowing Rock market."),
            ("Lincolnton", "OUTSIDE -- Lincoln County, its own market."),
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
         "A corridor page publishes only when the existing publication threshold (minimum_hotel_count = "
         "5 verified pet-friendly hotels) is met. No thin corridor page is invented for SEO; every "
         "corridor is show_in_navigation/show_in_sitemap false until a registration order publishes it."),
        ("coverage_areas_are_a_reporting_overlay",
         "The accounting reports a Hickory row under I-40 Hickory, US-321 Hickory or Hickory downtown / central "
         "when its own street names those roads, else by its pin's nearest overlay anchor (Long View / "
         "Mountain View included), else as Hickory (other). Conover and Newton rows report under their towns. "
         "The overlay decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("future_submarket", OrderedDict([("market_id", FUTURE_SUBMARKET),
                                          ("postal_codes", list(FUTURE_SUBMARKET_ZIPS))])),
        ("observation_is_not_admission",
         "Six cells observe Lenoir, Morganton / Valdese, Statesville, Taylorsville, Lincolnton and Denver. "
         "They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, qualifying resorts and qualifying lodging establishments "
         "operated as lodging businesses: bookable nightly rooms or suites sold to the public under one "
         "establishment name, with an official property page and a front desk / on-site hotel operation. "
         "It NEVER admits: apartment communities; corporate housing; individual short-term rentals or "
         "vacation homes; Airbnb / Vrbo-style listings; campgrounds and RV parks; assisted-living or senior "
         "housing; student housing; ordinary residential inventory. Every such row is recorded NON_LODGING "
         "with its reason. A bed and breakfast is admitted only when it operates as an inn with bookable "
         "rooms on its own premises and an official site."),
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
    if corridor_slug == "hickory":
        for rx, name in STREET_OVERLAY:
            if rx.search(street):
                return name
        return coverage_area(lat, lng) or "Hickory (other)"
    return {"conover": "Conover", "newton": "Newton", "claremont": "Claremont",
            "granite-falls-sawmills": "Granite Falls / Sawmills", "hildebran-icard": "Hildebran / Icard",
            "maiden": "Maiden", "catawba": "Catawba", "hudson": "Hudson"}.get(corridor_slug)


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    muni = " ".join((city or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    return {"hickory": "Hickory", "conover": "Conover", "newton": "Newton", "long view": "Long View",
            "mountain view": "Mountain View", "claremont": "Claremont", "granite falls": "Granite Falls",
            "sawmills": "Sawmills", "hildebran": "Hildebran", "icard": "Icard", "maiden": "Maiden",
            "catawba": "Catawba", "hudson": "Hudson"}.get(muni)


def is_future_submarket(postal):
    """True when the property's own postal code is Lenoir's."""
    return (postal or "").strip()[:5] in FUTURE_SUBMARKET_ZIPS


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
