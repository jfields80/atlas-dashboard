"""PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001 -- Phase 2: the Banner Elk - Sugar
Mountain - Beech Mountain High Country ski-and-resort lodging market.

Cloned from the Boone - Blowing Rock NC geography helper (7-tuple corridor registry).

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Avery County ski-resort traveller lodging cluster -- the Town of
Banner Elk (Lees-McRae College, NC-184 / NC-194), the Village of Sugar Mountain
(Sugar Mountain Resort, NC-184), the Town of Beech Mountain (Beech Mountain
Resort, the highest town in eastern America) and the Town of Seven Devils (NC-105)
-- with the Linville / Grandfather Mountain lodging that serves the same
travellers, stated as an explicit four-way rule (CORE / CORRIDOR / FRINGE /
OUTSIDE) before a single hotel is discovered, so no property is admitted or
refused after the fact to make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

WHY ONE CORE CORRIDOR
---------------------
Banner Elk, Sugar Mountain, Seven Devils and (almost all of) Beech Mountain
share ONE postal code, 28604. A postal partition cannot split them, and a
town page thinner than the publication minimum would be invented SEO. The four
towns are therefore one CORE corridor; the accounting reports each property
under the town its OWN page names (a reporting overlay that decides nothing).

THE CORRIDORS AND WHY
---------------------
CORE       Banner Elk / Sugar Mountain / Beech Mountain / Seven Devils (28604).
           28604 also reaches the NC-194 Valle Crucis side and the NC-105
           Foscoe side of the Watauga line; a property whose OWN page states
           Banner Elk 28604 there is admitted (the ZIP decides) and reported
           under its own stated town.
CORRIDOR   Linville / Grandfather Mountain (28646), with Montezuma (28653) and
           Pineola (28662) at the US-221 / NC-181 junctions -- ten to fifteen
           minutes south of Sugar Mountain; Grandfather Mountain and Linville
           Gorge lodging books with the ski towns.
FRINGE     Newland (28657), the Avery County seat eight miles south-west of
           Banner Elk; Elk Park (28622), on US-19E ten minutes north-west on
           the Beech Mountain back road toward Roan Mountain.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight: Boone / Blowing Rock / Valle Crucis / Vilas / Deep Gap
           and the rest of Watauga County (the separate LIVE
           boone-blowing-rock-nc market -- its postal codes are never absorbed,
           and a Foscoe or Seven Devils property whose own page states Boone
           28607 is Boone's); West Jefferson / Jefferson (Ashe County);
           Crossnore, Minneapolis and Plumtree (southern Avery on the Spruce Pine
           side); Spruce Pine / Little Switzerland; Lenoir; Roan Mountain,
           Elizabethton and Mountain City in Tennessee.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
This order builds the market while the release queue (Atlanta, Outer Banks,
Pinehurst and others) holds the live parent. It writes the market document to
the zone's PROPOSED path, never to the registry's ``markets/<id>.json``.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/banner_elk_sugar_beech_nc.json
  launch_packages/pettripfinder/markets/proposed/banner-elk-sugar-beech-nc.json
  launch_packages/pettripfinder/markets/reports/banner_elk_sugar_beech_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/banner_elk_sugar_beech_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "banner-elk-sugar-beech-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "banner_elk_sugar_beech_nc.json")
#: SHADOW UNTIL REGISTERED: the proposed path, never markets/<id>.json.
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "banner-elk-sugar-beech-nc.json")
REPORT_OUT = os.path.join(REPORTS, "banner_elk_sugar_beech_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "banner_elk_sugar_beech_nc_corridor_registry_001.json")

#: The LIVE neighbouring market whose postal codes this market never absorbs.
NEIGHBOUR_MARKET = "boone-blowing-rock-nc"
#: The market whose Boone build preserved this cluster's leads.
PRESERVED_BY = "PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("banner-elk-sugar-beech", "Banner Elk / Sugar Mountain / Beech Mountain", "Banner Elk, Sugar Mountain & Beech Mountain",
     "CORE", "banner elk",
     ["28604"],
     "The Avery County ski towns that share postal code 28604: the Town of Banner Elk and Lees-McRae College, "
     "the Village of Sugar Mountain and Sugar Mountain Resort on NC-184, the Town of Beech Mountain and Beech "
     "Mountain Resort, and the Town of Seven Devils on NC-105."),
    ("linville-grandfather", "Linville / Grandfather Mountain", "Linville & Grandfather Mountain", "CORRIDOR",
     "linville",
     ["28646", "28653", "28662"],
     "Linville and Grandfather Mountain on US-221 / NC-105, with Montezuma and Pineola at the US-221 / NC-181 "
     "junctions -- ten to fifteen minutes south of Sugar Mountain."),
    ("newland-elk-park", "Newland / Elk Park", "Newland & Elk Park", "FRINGE", "newland",
     ["28657", "28622"],
     "Newland, the Avery County seat eight miles south-west of Banner Elk, and Elk Park on US-19E on the Beech "
     "Mountain back road toward Roan Mountain."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. Empty at authoring time; a later
#: ruling adds a row, never a ZIP.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "bannerelk": "banner elk", "banner elk nc": "banner elk", "beech mtn": "beech mountain",
    "sugar mtn": "sugar mountain", "village of sugar mountain": "sugar mountain",
    "town of seven devils": "seven devils", "beech mountain nc": "beech mountain",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
BOONE_WHY = ("Watauga County: the separate LIVE %s market. Its postal codes are never absorbed; a Foscoe or "
             "Seven Devils property whose own page states Boone 28607 belongs to it; refused by name here."
             % NEIGHBOUR_MARKET)
OUTSIDE = [
    ("Boone / Foscoe (Boone 28607 mail)", "NC", ["28607", "28608"], BOONE_WHY),
    ("Blowing Rock", "NC", ["28605"], BOONE_WHY),
    ("Valle Crucis / Vilas", "NC", ["28691", "28692"], BOONE_WHY),
    ("Deep Gap / Sugar Grove / Zionville / Todd", "NC", ["28618", "28679", "28698", "28684"], BOONE_WHY),
    ("West Jefferson / Jefferson / Ashe County", "NC",
     ["28694", "28640", "28617", "28626", "28631", "28615", "28643", "28693"],
     "Ashe County on US-221 / NC-194 and the New River, an hour from Banner Elk; its own small lodging "
     "cluster; refused by name."),
    ("Crossnore / Minneapolis / Plumtree", "NC", ["28616", "28652", "28664"],
     "Southern Avery County on US-221 / US-19E toward Spruce Pine, 20-30 minutes from Banner Elk; they route "
     "through Spruce Pine and the Parkway rather than the ski towns; refused by name."),
    ("Spruce Pine / Little Switzerland", "NC", ["28777", "28749"],
     "Mitchell / McDowell County on the Parkway south of Linville; its own cluster; refused by name."),
    ("Lenoir / Collettsville", "NC", ["28645", "28611"],
     "Caldwell County below the Blue Ridge escarpment; its own market; refused by name."),
    ("Roan Mountain / Elizabethton / Mountain City", "TN", ["37687", "37643", "37683"],
     "Tennessee; another state and its own markets; refused by name."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the Boone side and southern Avery so this order classifies those
#: properties on evidence.
CELLS = [
    ("banner-elk", "Banner Elk", "Banner Elk town / Lees-McRae", 36.1630, -81.8720, 3000, True),
    ("sugar-mountain", "Sugar Mountain", "Sugar Mountain village / NC-184", 36.1270, -81.8660, 3000, True),
    ("beech-mountain", "Beech Mountain", "Beech Mountain town / resort", 36.2040, -81.8820, 3500, True),
    ("seven-devils", "Seven Devils", "Seven Devils / NC-105", 36.1480, -81.8150, 3000, True),
    ("nc-194-valle-side", "Banner Elk", "NC-194 toward Valle Crucis (28604 mail)", 36.1900, -81.8200, 3500, True),
    ("linville", "Linville", "Linville / Grandfather Mountain", 36.0650, -81.8720, 4000, True),
    ("pineola-montezuma", "Pineola", "Pineola / Montezuma / Linville Falls Hwy", 36.0300, -81.8950, 4500, True),
    ("newland", "Newland", "Newland / Avery County seat", 36.0870, -81.9270, 3500, True),
    ("elk-park", "Elk Park", "Elk Park / US-19E", 36.1580, -81.9800, 3500, True),
    # observation only -- the Boone side and refused neighbours
    ("obs-foscoe", "Foscoe", "Foscoe / NC-105 (Boone 28607) -- OBSERVATION ONLY", 36.1750, -81.7650, 3000, False),
    ("obs-valle-crucis", "Valle Crucis", "Valle Crucis (Boone's corridor) -- OBSERVATION ONLY", 36.2100, -81.7800, 2500, False),
    ("obs-crossnore", "Crossnore", "Crossnore / southern Avery -- OBSERVATION ONLY", 35.9800, -81.9300, 4000, False),
    ("obs-roan-mountain", "Roan Mountain", "Roan Mountain TN -- OBSERVATION ONLY", 36.1960, -82.0700, 4000, False),
]

BOUNDS = {
    "min_lat": 35.93,
    "max_lat": 36.30,
    "min_lng": -82.10,
    "max_lng": -81.72,
}

#: Reporting overlay only (never membership): the town a property's OWN stated
#: municipality names, falling back to the nearest town anchor for its pin.
#: (area, anchor_lat, anchor_lng, radius_km)
COVERAGE_AREAS = [
    ("Banner Elk", 36.1630, -81.8720, 3.5),
    ("Sugar Mountain", 36.1270, -81.8660, 2.5),
    ("Beech Mountain", 36.2040, -81.8820, 4.0),
    ("Seven Devils", 36.1480, -81.8150, 3.0),
    ("Linville / Grandfather", 36.0650, -81.8720, 6.0),
    ("Newland", 36.0870, -81.9270, 5.0),
    ("Elk Park", 36.1580, -81.9800, 4.0),
]

#: The stated municipality -> the overlay area it reports under.
_MUNICIPALITY_AREA = {
    "banner elk": "Banner Elk", "sugar mountain": "Sugar Mountain", "beech mountain": "Beech Mountain",
    "seven devils": "Seven Devils", "linville": "Linville / Grandfather", "montezuma": "Linville / Grandfather",
    "pineola": "Linville / Grandfather", "newland": "Newland", "elk park": "Elk Park",
}


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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Banner Elk - Sugar - Beech" % name),
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
        ("state_code", "NC" if not muni.startswith("Roan") else "TN"), ("admitting", admitting),
    ]) for suffix, muni, label, lat, lng, radius, admitting in CELLS]
    admitting_munis = sorted({c["municipality"] for c in cells if c["admitting"]})

    config = OrderedDict([
        ("market_id", MARKET_ID),
        ("market_name", "Banner Elk - Sugar Mountain - Beech Mountain, NC ski-resort lodging market "
                        "(PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 36.150, "lng": -81.870}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- east to "
             "Foscoe and Valle Crucis on the Boone side, south to Crossnore and west to Roan Mountain TN -- so "
             "that " + WORK_ORDER + " classifies those properties on evidence instead of being blind to them. "
             "Admission is decided by the corridor registry over the property's OWN postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". An Avery County ski-resort market: Banner Elk, Sugar Mountain, Beech Mountain and Seven "
         "Devils (28604) are CORE; Linville / Grandfather (with Montezuma and Pineola) is CORRIDOR; Newland and "
         "Elk Park are FRINGE. Boone, Blowing Rock, Valle Crucis and the rest of Watauga County (the live " +
         NEIGHBOUR_MARKET + " market), West Jefferson, southern Avery and Tennessee are OBSERVED and REFUSED."),
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
        ("market_name", "Banner Elk – Sugar Mountain – Beech Mountain, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Banner Elk"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Banner Elk, Sugar Mountain & Beech Mountain, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Banner Elk, Sugar Mountain, Beech Mountain and Seven Devils, North "
         "Carolina -- the High Country ski towns, Linville and Grandfather Mountain -- with real pet fees and "
         "policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Banner Elk – Sugar – Beech"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to the "
         "corridor registry. An Avery County ski-resort market -- Banner Elk, Sugar Mountain, Beech Mountain, "
         "Seven Devils, Linville / Grandfather, Newland and Elk Park -- not the whole High Country. Nothing else "
         "admits a property: not a 'High Country' or 'Grandfather' marketing name, not a map pin, not a condo, "
         "cabin or vacation-rental listing, not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every admitted "
         "lodging ZIP is claimed by exactly one corridor. Banner Elk, Sugar Mountain, Beech Mountain and Seven "
         "Devils share 28604 and are one corridor."),
        ("_census_membership_note",
         "Boone, Blowing Rock, Valle Crucis, Vilas and the rest of Watauga County are the separate live Boone - "
         "Blowing Rock market and are never absorbed; West Jefferson, southern Avery (Crossnore, Plumtree), "
         "Spruce Pine and Tennessee are refused. A property whose own page states one of their postal codes is "
         "OUTSIDE, however it is named. Individual condos, cabins, vacation homes, rental-management portfolios "
         "and timeshare inventory are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Banner Elk - Sugar Mountain - Beech Mountain geography and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-14"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/%s.json, never to the "
         "registry's markets/<id>.json; a later registration order copies it into place against the then-"
         "current live parent." % MARKET_ID),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "The lodging a visitor means by 'Banner Elk', 'Sugar Mountain' or 'Beech Mountain': the Avery County "
         "ski-and-golf resort towns, Seven Devils on NC-105, and the Linville / Grandfather Mountain lodging ten "
         "to fifteen minutes south that books with them; Newland and Elk Park as FRINGE."),
        ("separated_from", OrderedDict([
            ("market_id", NEIGHBOUR_MARKET),
            ("by", PRESERVED_BY),
            ("how",
             "The Boone build refused 28604 and the rest of Avery County as OUTSIDE and carried every property it "
             "saw there with a FUTURE_SUBMARKET banner-elk-sugar-beech-nc reason. This market admits exactly the "
             "postal codes Boone refused on that reason and never one Boone admits, so no building can belong to "
             "both markets."),
        ])),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("evaluated_inclusions", OrderedDict([
            ("Banner Elk", "ADMITTED (CORE, banner-elk-sugar-beech, 28604)."),
            ("Sugar Mountain", "ADMITTED (CORE, 28604) -- reported as Sugar Mountain when its own page says so."),
            ("Beech Mountain", "ADMITTED (CORE, 28604) -- reported as Beech Mountain."),
            ("Seven Devils", "ADMITTED (CORE) where its own page states Banner Elk / Seven Devils 28604; a Boone "
                             "28607 address on the NC-105 side belongs to the live Boone market and is OUTSIDE here."),
            ("Grandfather / Linville-adjacent lodging",
             "ADMITTED (CORRIDOR, linville-grandfather, 28646 / 28653 / 28662) -- Linville, Grandfather Mountain, "
             "Montezuma and Pineola, ten to fifteen minutes from Sugar Mountain."),
            ("Elk Park", "ADMITTED (FRINGE, newland-elk-park, 28622) -- the US-19E back road to Beech Mountain."),
            ("Linville", "ADMITTED (CORRIDOR, 28646)."),
            ("Newland", "ADMITTED (FRINGE, 28657) -- the county seat, eight miles from Banner Elk; never CORE."),
            ("Foscoe", "OUTSIDE when its own page states Boone 28607 (the live Boone market); a Banner Elk 28604 "
                       "address on the NC-105 side is admitted by its ZIP and reported under its stated town."),
            ("Valle Crucis", "OUTSIDE (28691 is the live Boone market's corridor); an inn whose own page states "
                             "Banner Elk 28604 on the NC-194 side is admitted by its ZIP."),
            ("Boone / Blowing Rock", "OUTSIDE -- the separate live boone-blowing-rock-nc market; never absorbed."),
            ("West Jefferson / Jefferson", "OUTSIDE -- Ashe County."),
            ("Crossnore / Plumtree / Minneapolis", "OUTSIDE -- southern Avery on the Spruce Pine side."),
        ])),
        ("banner_elk_mailing_address_caution",
         "28604 is a large rural postal code. It reaches over the Watauga line on NC-194 (the Valle Crucis side) "
         "and NC-105 (the Foscoe side). The ZIP decides membership; the accounting reports every such property "
         "under the town its OWN page names, and a property whose own page names a Watauga town beside 28604 "
         "(for example 'Boone 28604') is a GEOGRAPHY_HOLD, never admitted on the ZIP alone."),
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
         "Banner Elk, Sugar Mountain, Beech Mountain and Seven Devils all sit in 28604. The accounting reports "
         "each property under the town its own page states, then the nearest town anchor for its pin. The "
         "overlay decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Four cells observe Foscoe, Valle Crucis, Crossnore and Roan Mountain. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, qualifying resorts and qualifying lodging establishments "
         "operated as lodging businesses: bookable nightly rooms or suites sold to the public under one "
         "establishment name, with an official property page and a front desk / on-site hotel operation. "
         "It NEVER admits: individual condos, cabins, chalets or vacation homes; condominium complexes rented "
         "unit-by-unit through owners or agencies (the ski towns' slope-side condo towers among them); "
         "property-management or realty rental portfolios; Airbnb / Vrbo-style listings; private resort or "
         "club units sold only to members or owners; cabin collections not operated as one lodging "
         "establishment; and TIMESHARE / vacation-ownership inventory unless that property independently "
         "qualifies as a hotel -- public nightly rooms, its own reservation surface and a front desk. Every "
         "such row is recorded NON_LODGING with its reason. A bed and breakfast is admitted only when it "
         "operates as an inn with bookable rooms on its own premises and an official site. Campgrounds, RV "
         "parks, college housing and summer camps are NON_LODGING."),
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
        dy = (float(lat) - la) * 111.0
        dx = (float(lng) - ln) * 111.0 * math.cos(math.radians(la))
        d = math.hypot(dx, dy)
        if d <= r and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def _muni(city):
    m = " ".join((city or "").lower().replace(".", " ").split())
    return MUNICIPALITY_SPELLINGS.get(m, m)


def route_overlay(corridor_slug, street, lat, lng, city=None):
    """The named town a census row reports under. Reporting only.

    The town the property's OWN page states first; then the nearest town anchor
    for its pin; then the corridor's own name."""
    area = _MUNICIPALITY_AREA.get(_muni(city))
    if area:
        return area
    area = coverage_area(lat, lng)
    if area:
        return area
    return {"banner-elk-sugar-beech": "Banner Elk", "linville-grandfather": "Linville / Grandfather",
            "newland-elk-park": "Newland"}.get(corridor_slug)


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    return _MUNICIPALITY_AREA.get(_muni(city))


def is_neighbour_market(postal):
    """True when a postal code belongs to the live Boone - Blowing Rock market."""
    z = (postal or "").strip()[:5]
    return any(z in zs for _name, _s, zs, why in OUTSIDE if NEIGHBOUR_MARKET in why)


def classify_postal(postal, municipality):
    """(class, corridor_slug | None, reason) for a property's OWN postal code and
    municipality. The one membership function every later phase imports."""
    z = (postal or "").strip()[:5]
    muni = _muni(municipality)
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
