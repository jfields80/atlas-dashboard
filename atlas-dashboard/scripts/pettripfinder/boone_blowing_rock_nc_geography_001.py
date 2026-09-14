"""PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 -- Phase 2: the Boone - Blowing Rock
High Country traveller lodging market.

Cloned from the Outer Banks NC geography helper (7-tuple corridor registry).

WHAT THIS DECIDES, AND ON WHAT
------------------------------
The practical Boone - Blowing Rock, North Carolina traveller lodging market --
the Town of Boone (Appalachian State University, downtown King Street, the
US-321 Blowing Rock Road strip, the US-421 corridor and NC-105 toward Foscoe),
the Town of Blowing Rock (the village and its Blue Ridge Parkway resort
corridor) and the Watauga County valleys that book as Boone stays -- stated as
an explicit four-way rule (CORE / CORRIDOR / FRINGE / OUTSIDE) before a single
hotel is discovered, so no property is admitted or refused after the fact to
make a number.

THE GOVERNING RULE
------------------
Membership is decided by the property's OWN postal code, as its own official
page states it, joined to the corridor registry below. The registry is a
POSTAL-CODE PARTITION: every admitted lodging ZIP is claimed by exactly one
corridor, so a property's corridor is a lookup and never a judgement.

BANNER ELK / SUGAR MOUNTAIN / BEECH MOUNTAIN IS A SEPARATE CLUSTER
------------------------------------------------------------------
"The High Country" names three counties. The lodging a visitor books when they
say "Boone" or "Blowing Rock" is concentrated in Watauga County: the university
town and its highway strips, and the resort village eight miles south on US-321.
The Avery County ski towns behave as their own lodging market:

* Banner Elk (ZIP 28604) is ~17 road miles and 30+ minutes from downtown Boone
  over NC-105 and NC-184, in Avery County. Its lodging is a ski-and-golf resort
  cluster around Sugar Mountain Resort, Beech Mountain Resort and Lees-McRae
  College, and the same ZIP carries the Village of Sugar Mountain, the Town of
  Seven Devils and much of Beech Mountain. Beech Mountain (the highest town in
  eastern America) is a further 20 minutes of switchbacks above Banner Elk.
* Linville, Newland, Elk Park, Crossnore and Pineola (Grandfather Mountain,
  Linville Falls, Eseeola) are Avery County and route through the Banner Elk
  / US-221 side, not through Boone.

That cluster is therefore OUTSIDE this build and PRESERVED for a future
``banner-elk-sugar-beech-nc`` submarket: every such property any lane sees is
classified OUTSIDE_MARKET with that reason, not forced into this market and not
silently dropped. Seven Devils and the Foscoe community are split by the postal
service: a property whose own page states Boone 28607 (NC-105 / Foscoe) is
admitted as Boone; one that states Banner Elk 28604 is preserved for the future
submarket. The ZIP decides, never the resort's marketing name.

THE CORRIDORS AND WHY
---------------------
CORE       Boone (28607, and the Appalachian State University 28608 ZIP); Blowing
           Rock (28605).
CORRIDOR   Valle Crucis (28691) and Vilas (28692) -- NC-194 / US-421 / US-321
           west of Boone, ten to fifteen minutes out, whose inns book as Boone
           stays; Deep Gap (28618) -- US-421 east of Boone and the Parkway
           crossing at Deep Gap.
FRINGE     Sugar Grove / Zionville / Todd (28679, 28698, 28684) -- rural Watauga
           County on US-421 / US-321 toward Tennessee and the New River at Todd.
OUTSIDE    Everything else, refused BY NAME so the refusal is a decision and not
           an oversight: Banner Elk / Sugar Mountain / Seven Devils / Beech
           Mountain and the rest of Avery County (future submarket); West
           Jefferson and Jefferson (Ashe County, its own New River cluster);
           Lenoir, Wilkesboro / North Wilkesboro; Mountain City and Elizabethton
           in Tennessee.

The accounting's route overlay (Downtown / App State, US-321, US-421, NC-105,
Blowing Rock village, Blue Ridge Parkway / resort corridor) is REPORTING ONLY
and decides nothing about membership.

WHERE THIS WRITES (SHADOW UNTIL REGISTERED)
-------------------------------------------
Boone - Blowing Rock is built while production deployment is unavailable and
five other markets (Fayetteville, Jacksonville, Greenville, Atlanta, Outer
Banks) must go live first. This order writes the market document to the zone's
PROPOSED path, never to the registry's ``markets/<id>.json``.

Nothing here fetches, spends or deploys.

Outputs:
  scripts/pettripfinder/discovery/config/boone_blowing_rock_nc.json
  launch_packages/pettripfinder/markets/proposed/boone-blowing-rock-nc.json
  launch_packages/pettripfinder/markets/reports/boone_blowing_rock_nc_geography_001.json
  launch_packages/pettripfinder/markets/reports/boone_blowing_rock_nc_corridor_registry_001.json
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

WORK_ORDER = "PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "boone-blowing-rock-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONFIG_OUT = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "boone_blowing_rock_nc.json")
SHARD_OUT = os.path.join(PKG, "markets", "proposed", "boone-blowing-rock-nc.json")
REPORT_OUT = os.path.join(REPORTS, "boone_blowing_rock_nc_geography_001.json")
REGISTRY_OUT = os.path.join(REPORTS, "boone_blowing_rock_nc_corridor_registry_001.json")

#: The future submarket every Banner Elk / Sugar / Beech / Avery property is preserved for.
FUTURE_SUBMARKET = "banner-elk-sugar-beech-nc"

#: The corridor registry: a POSTAL-CODE PARTITION of the admitted market.
#: (slug, name, display_area, class, municipality, postal codes, description)
CORRIDORS = [
    ("boone", "Boone / Appalachian State", "Boone", "CORE", "boone",
     ["28607", "28608"],
     "The Town of Boone: downtown King Street and Appalachian State University, the US-321 Blowing "
     "Rock Road strip, the US-421 corridor and NC-105 toward Foscoe."),
    ("blowing-rock", "Blowing Rock", "Blowing Rock", "CORE", "blowing rock",
     ["28605"],
     "The Town of Blowing Rock: the Main Street village, US-321 and the Blue Ridge Parkway resort "
     "corridor (Moses Cone and Price parks)."),
    ("valle-crucis-vilas", "Valle Crucis / Vilas", "Valle Crucis & Vilas", "CORRIDOR", "valle crucis",
     ["28691", "28692"],
     "Valle Crucis on NC-194 and Vilas on US-421 / US-321, the Watauga valleys ten to fifteen minutes "
     "west of downtown Boone."),
    ("deep-gap", "Deep Gap / US-421 East", "Deep Gap", "CORRIDOR", "deep gap",
     ["28618"],
     "Deep Gap on US-421 east of Boone, where the highway crosses the Blue Ridge Parkway."),
    ("watauga-fringe", "Sugar Grove / Zionville / Todd", "Sugar Grove, Zionville & Todd", "FRINGE",
     "sugar grove",
     ["28679", "28698", "28684"],
     "Rural Watauga County: Sugar Grove and Zionville on US-421 / US-321 toward Tennessee, and Todd on "
     "the South Fork New River."),
]

#: Municipalities refused INSIDE an admitted postal code, matched on the
#: property's OWN stated address municipality. Empty at authoring time; a later
#: ruling adds a row, never a ZIP.
MUNICIPALITY_REFUSALS = []
MUNICIPALITY_SPELLINGS = {
    "blowingrock": "blowing rock", "valle crusis": "valle crucis", "boone nc": "boone",
}

#: Municipalities OUTSIDE the admitted market, each with the reason.
AVERY_WHY = ("Banner Elk / Sugar Mountain / Seven Devils / Beech Mountain, Avery County: a separate ski-and-"
             "golf resort lodging cluster ~30 minutes from Boone; PRESERVED for the future %s submarket, "
             "evaluated and refused here." % FUTURE_SUBMARKET)
AVERY_OTHER_WHY = ("Avery County on the US-221 / Grandfather Mountain side, routed through Banner Elk and "
                   "Linville rather than Boone; carried with the future %s submarket, evaluated and refused "
                   "here." % FUTURE_SUBMARKET)
OUTSIDE = [
    ("Banner Elk / Sugar Mountain / Seven Devils / Beech Mountain", "NC", ["28604"], AVERY_WHY),
    ("Linville / Grandfather Mountain", "NC", ["28646"], AVERY_OTHER_WHY),
    ("Newland / Minneapolis / Montezuma", "NC", ["28657", "28652", "28653"], AVERY_OTHER_WHY),
    ("Elk Park / Crossnore / Pineola / Plumtree", "NC", ["28622", "28616", "28662", "28664"], AVERY_OTHER_WHY),
    ("West Jefferson / Jefferson / Ashe County", "NC",
     ["28694", "28640", "28617", "28626", "28631", "28615", "28643", "28693"],
     "Ashe County on US-221 / NC-194 and the New River, 30-40 minutes from Boone; its own small "
     "lodging cluster; evaluated and refused."),
    ("Lenoir / Patterson / Collettsville", "NC", ["28645", "28638", "28611"],
     "Caldwell County below the Blue Ridge escarpment on US-321, 25 miles south; its own market; refused."),
    ("Wilkesboro / North Wilkesboro / Ferguson", "NC", ["28697", "28659", "28624"],
     "Wilkes County on US-421 east of the Parkway, 35 miles; its own market; refused by name."),
    ("Spruce Pine / Little Switzerland", "NC", ["28777", "28749"],
     "Mitchell / McDowell County on the Parkway south of Linville; refused by name."),
    ("Mountain City / Elizabethton / Roan Mountain", "TN", ["37683", "37643", "37687"],
     "Tennessee; another state and its own markets; refused by name."),
]

#: Bounded observation cells. ADMITTING cells sit on admitted ZIPs; OBSERVATION
#: cells cover the Avery submarket and Ashe County so this order classifies
#: those properties on evidence.
CELLS = [
    ("boone-downtown", "Boone", "Downtown Boone / Appalachian State", 36.2155, -81.6780, 2000, True),
    ("boone-us-321", "Boone", "Boone US-321 Blowing Rock Road strip", 36.1960, -81.6590, 2500, True),
    ("boone-nc-105", "Boone", "Boone NC-105 / Foscoe", 36.1900, -81.7150, 4500, True),
    ("boone-us-421-east", "Boone", "Boone US-421 East King Street", 36.2230, -81.6450, 2500, True),
    ("blowing-rock", "Blowing Rock", "Blowing Rock village", 36.1350, -81.6780, 2500, True),
    ("blowing-rock-parkway", "Blowing Rock", "Blowing Rock Parkway / resort corridor", 36.1500, -81.6600, 3500, True),
    ("valle-crucis", "Valle Crucis", "Valle Crucis / NC-194", 36.2100, -81.7800, 3500, True),
    ("vilas", "Vilas", "Vilas / US-421 west", 36.2600, -81.7700, 4000, True),
    ("deep-gap", "Deep Gap", "Deep Gap / US-421 east", 36.2250, -81.5300, 5000, True),
    ("sugar-grove-zionville", "Sugar Grove", "Sugar Grove / Zionville", 36.2600, -81.8400, 6000, True),
    ("todd", "Todd", "Todd / South Fork New River", 36.3150, -81.6050, 4000, True),
    # observation only -- the Banner Elk / Sugar / Beech submarket and refused neighbours
    ("obs-banner-elk", "Banner Elk", "Banner Elk -- OBSERVATION ONLY", 36.1630, -81.8720, 4000, False),
    ("obs-sugar-mountain", "Sugar Mountain", "Sugar Mountain -- OBSERVATION ONLY", 36.1270, -81.8660, 3000, False),
    ("obs-beech-mountain", "Beech Mountain", "Beech Mountain -- OBSERVATION ONLY", 36.2040, -81.8820, 3500, False),
    ("obs-seven-devils", "Seven Devils", "Seven Devils -- OBSERVATION ONLY", 36.1480, -81.8150, 3000, False),
    ("obs-linville-newland", "Linville", "Linville / Newland -- OBSERVATION ONLY", 36.0700, -81.8900, 7000, False),
    ("obs-west-jefferson", "West Jefferson", "West Jefferson / Jefferson -- OBSERVATION ONLY", 36.4050, -81.4850, 5000, False),
]

BOUNDS = {
    "min_lat": 35.88,
    "max_lat": 36.50,
    "min_lng": -82.05,
    "max_lng": -81.35,
}

#: Reporting overlay only (never membership). The order names the Boone road
#: corridors, which all sit inside ONE postal code, so the accounting reports a
#: property's route from its OWN stated street first and its pin second.
#: (area, anchor_lat, anchor_lng, radius_km)
COVERAGE_AREAS = [
    ("Boone Downtown / App State", 36.2155, -81.6780, 1.6),
    ("Boone US-321", 36.1960, -81.6590, 2.5),
    ("Boone US-421", 36.2230, -81.6450, 3.0),
    ("Boone NC-105 / Foscoe", 36.1900, -81.7150, 5.0),
    ("Blowing Rock village", 36.1350, -81.6780, 1.4),
    ("Blue Ridge Parkway / resort corridor", 36.1500, -81.6600, 5.0),
    ("Valle Crucis / Vilas", 36.2300, -81.7750, 5.0),
    ("Deep Gap", 36.2250, -81.5300, 6.0),
]

#: Street wording on the property's OWN address that names a Boone road corridor.
STREET_OVERLAY = [
    (re.compile(r"blowing rock r(oa)?d|\bus[- ]?(hwy |highway )?321\b|\bhwy\.? 321\b|highway 321", re.I),
     "Boone US-321"),
    (re.compile(r"\bking st|\bus[- ]?(hwy |highway )?421\b|\bhwy\.? 421\b|highway 421", re.I), "Boone US-421"),
    (re.compile(r"\b(nc|hwy\.?|highway)[- ]?105\b", re.I), "Boone NC-105 / Foscoe"),
]

#: The Blowing Rock town limits' village core, by own stated street.
BLOWING_ROCK_VILLAGE_STREETS = re.compile(
    r"\bmain st|\bsunset dr|\bpark ave|\bwallingford|\byonahlossee|\bmorris st|\bmaple st|\bwonderland",
    re.I)


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
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Boone - Blowing Rock" % name),
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
        ("market_name", "Boone - Blowing Rock, NC High Country lodging market (PetTripFinder discovery scope)"),
        ("state", "NC"),
        ("states", ["NC"]),
        ("country", "US"),
        ("market_center", {"lat": 36.185, "lng": -81.675}),
        ("geographic_bounds", OrderedDict(list(BOUNDS.items()) + [
            ("_disclosure",
             "OBSERVATION box, not an admission boundary. It reaches beyond the admitted corridors -- west "
             "over Banner Elk, Sugar Mountain, Beech Mountain and Linville, north-east to West Jefferson and "
             "south to Lenoir -- so that " + WORK_ORDER + " classifies those properties on evidence instead "
             "of being blind to them. Admission is decided by the corridor registry over the property's OWN "
             "postal code."),
        ])),
        ("coordinate_precision_disclosure",
         "All lat/lng values in this file are low-precision approximate reference points; membership "
         "is decided by the corridor registry over the property's own postal code."),
        ("included_municipalities", admitting_munis),
        ("_boundary_note",
         WORK_ORDER + ". A High Country market: Boone and Blowing Rock are CORE; Valle Crucis / Vilas and "
         "Deep Gap are CORRIDOR; rural Watauga (Sugar Grove, Zionville, Todd) is FRINGE. Banner Elk, Sugar "
         "Mountain, Seven Devils, Beech Mountain and the rest of Avery County are OBSERVED and REFUSED, "
         "preserved for a future " + FUTURE_SUBMARKET + " submarket; West Jefferson, Lenoir and Wilkesboro "
         "are named and REFUSED."),
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
        ("market_name", "Boone – Blowing Rock, North Carolina"),
        ("market_slug", MARKET_ID),
        ("state_name", "North Carolina"),
        ("state_code", "NC"),
        ("primary_state_code", "NC"),
        ("states", ["NC"]),
        ("primary_city", "Boone"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Boone & Blowing Rock, North Carolina | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels in Boone and Blowing Rock, North Carolina -- Appalachian State, "
         "the Blue Ridge Parkway, Valle Crucis and Deep Gap -- with real pet fees and policies read from "
         "each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official website."),
        ("navigation_label", "Boone – Blowing Rock"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note",
         "Membership is the property's OWN postal code, as its own official page states it, joined to "
         "the corridor registry. A Watauga County market -- Boone, Blowing Rock and the valleys that book "
         "as Boone stays -- not the whole High Country. Nothing else admits a property: not a 'High "
         "Country' or 'Blue Ridge' marketing name, not a map pin, not a cabin or vacation-rental listing, "
         "not a competitor directory's city label."),
        ("_corridor_note",
         "Corridors are a postal-code partition (census_membership_basis CORRIDOR_REGISTRY). Every "
         "admitted lodging ZIP is claimed by exactly one corridor. The Boone road corridors (downtown, "
         "US-321, US-421, NC-105) share 28607 and are one corridor."),
        ("_census_membership_note",
         "Banner Elk, Sugar Mountain, Seven Devils, Beech Mountain and the rest of Avery County are a "
         "separate ski-resort lodging cluster preserved for a future submarket; West Jefferson, Lenoir and "
         "Wilkesboro are not absorbed. A property whose own page states one of their postal codes is "
         "OUTSIDE, however it is named. Individual cabins, vacation homes, condo units, rental-management "
         "portfolios and timeshare inventory are never admitted."),
        ("authored_by", WORK_ORDER),
        ("corridors", [OrderedDict((k, v) for k, v in c.items() if k != "geography_class")
                       for c in corridors]),
    ])

    report = OrderedDict([
        ("schema", "ptf-market-geography/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "2 -- Boone - Blowing Rock High Country geography and corridor model"),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-13"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", 0),
        ("registration_state",
         "SHADOW_UNTIL_REGISTERED: the market document is written to markets/proposed/, never to the "
         "registry's markets/<id>.json. Registration waits for Fayetteville, Jacksonville, Greenville, "
         "Atlanta and Outer Banks to go live."),
        ("membership_rule",
         "The property's OWN postal code, as its own official page states it, joined to the corridor "
         "registry. Nothing else admits a property."),
        ("travel_market",
         "The lodging a visitor means by 'Boone' or 'Blowing Rock': the university town and its highway "
         "strips, the resort village on US-321 and the Parkway, and the Watauga valleys (Valle Crucis, "
         "Vilas, Deep Gap) whose inns book as Boone stays; rural Watauga as FRINGE."),
        ("classes", OrderedDict((k, "; ".join(
            "%s (%s)" % (c[1], ", ".join(c[5])) for c in CORRIDORS if c[3] == k))
            for k in ("CORE", "CORRIDOR", "FRINGE"))),
        ("outside_class", "Everything else, refused by name with its postal codes."),
        ("banner_elk_sugar_beech_ruling", OrderedDict([
            ("decision", "OUTSIDE -- PRESERVED_FOR_FUTURE_SUBMARKET"),
            ("future_market_id", FUTURE_SUBMARKET),
            ("why",
             "Banner Elk is ~17 road miles and 30+ minutes from downtown Boone in Avery County; its lodging "
             "is a ski-and-golf resort cluster around Sugar Mountain, Beech Mountain and Lees-McRae, sharing "
             "ZIP 28604 with Sugar Mountain, Seven Devils and much of Beech Mountain. Linville, Newland and "
             "Elk Park route through the same Avery side. Forcing them into this market would publish hotels "
             "half an hour of mountain road from the towns it names, and would bury a cluster that can stand "
             "on its own."),
            ("how_preserved",
             "Discovery OBSERVES all of it (six observation cells, brand city pages for Banner Elk, Beech "
             "Mountain, Sugar Mountain, Linville and Newland). Every property seen there is carried in the "
             "census's non_admitted rows as OUTSIDE_MARKET with this reason, so the future submarket order "
             "starts from recorded identities rather than from zero."),
        ])),
        ("evaluated_inclusions", OrderedDict([
            ("Boone", "ADMITTED (CORE, boone, 28607 / 28608) -- downtown, App State, US-321, US-421, NC-105."),
            ("Blowing Rock", "ADMITTED (CORE, blowing-rock, 28605) -- village and Parkway resort corridor."),
            ("Appalachian State / Downtown Boone", "ADMITTED (CORE) -- reported as the Downtown / App State overlay."),
            ("US-321 Boone corridor", "ADMITTED (CORE) -- reported as the US-321 overlay."),
            ("US-421 Boone corridor", "ADMITTED (CORE) -- reported as the US-421 overlay."),
            ("Blue Ridge Parkway access lodging", "ADMITTED where the property's own ZIP is 28605, 28607 or 28618."),
            ("Valle Crucis", "ADMITTED (CORRIDOR, valle-crucis-vilas, 28691) -- its inns book as Boone stays; never CORE."),
            ("Vilas", "ADMITTED (CORRIDOR, valle-crucis-vilas, 28692)."),
            ("Deep Gap", "ADMITTED (CORRIDOR, deep-gap, 28618)."),
            ("Foscoe", "ADMITTED only where its own page states Boone 28607; a Banner Elk 28604 address is OUTSIDE."),
            ("Seven Devils", "OUTSIDE (28604) -- future submarket; a Boone 28607 address would be admitted."),
            ("Banner Elk", "OUTSIDE -- Avery County ski-resort cluster; future submarket."),
            ("Sugar Mountain", "OUTSIDE -- future submarket."),
            ("Beech Mountain", "OUTSIDE -- future submarket."),
            ("Linville / Grandfather Mountain area", "OUTSIDE -- Avery County; carried with the future submarket."),
            ("Newland", "OUTSIDE -- Avery County seat; carried with the future submarket."),
            ("West Jefferson / Jefferson", "OUTSIDE -- Ashe County, its own New River cluster."),
            ("Sugar Grove / Zionville / Todd", "ADMITTED (FRINGE, watauga-fringe)."),
            ("Lenoir / Wilkesboro", "OUTSIDE -- their own markets."),
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
         "Downtown / App State, US-321, US-421 and NC-105 all sit in 28607. The accounting reports each "
         "from the property's own stated street (STREET_OVERLAY), then a nearest-anchor overlay on its "
         "pin. Blowing Rock reports as the village when its own street is a village street, else as the "
         "Parkway / resort corridor. The overlay decides nothing about membership or corridor."),
        ("coverage_areas", [OrderedDict([("area", a), ("anchor_lat", la), ("anchor_lng", ln),
                                         ("radius_km", r)]) for a, la, ln, r in COVERAGE_AREAS]),
        ("outside_named_and_refused", [OrderedDict([
            ("municipality", m), ("state", s), ("postal_codes", zs), ("why", w)
        ]) for m, s, zs, w in OUTSIDE]),
        ("observation_is_not_admission",
         "Six cells observe Banner Elk, Sugar Mountain, Beech Mountain, Seven Devils, Linville / Newland "
         "and West Jefferson. They admit nothing."),
        ("vacation_rental_rule",
         "The census admits hotels, motels, inns, qualifying resorts and qualifying lodging establishments "
         "operated as lodging businesses: bookable nightly rooms or suites sold to the public under one "
         "establishment name, with an official property page and a front desk / on-site hotel operation. "
         "It NEVER admits: individual cabins, chalets or vacation homes; condominium units or condo "
         "complexes rented unit-by-unit through owners or agencies; property-management or realty rental "
         "portfolios (Blue Ridge Mountain Rentals, High Country Vacation Homes, Foscoe Rentals, Boone "
         "Cabin Rentals and the like); Airbnb / Vrbo-style listings; cabin collections not operated as one "
         "lodging establishment; and TIMESHARE / vacation-ownership inventory unless that property "
         "independently qualifies as a hotel -- public nightly rooms, its own reservation surface and a "
         "front desk. Every such row is recorded NON_LODGING with its reason. A bed and breakfast is "
         "admitted only when it operates as an inn with bookable rooms on its own premises and an official "
         "site. Campgrounds, RV parks and university housing are NON_LODGING."),
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
    """The order's named route area a census row reports under. Reporting only.

    Boone rows report by their OWN stated street first (US-321 / US-421 / NC-105),
    then by pin (downtown / App State within 1.6 km of King & Depot). Blowing Rock
    rows report as the village on a village street, else the Parkway / resort
    corridor. Other corridors report as themselves."""
    if corridor_slug == "boone":
        for rx, name in STREET_OVERLAY:
            if rx.search(street or ""):
                return name
        area = coverage_area(lat, lng)
        if area and area.startswith("Boone"):
            return area
        return "Boone Downtown / App State"
    if corridor_slug == "blowing-rock":
        if BLOWING_ROCK_VILLAGE_STREETS.search(street or ""):
            return "Blowing Rock village"
        return "Blue Ridge Parkway / resort corridor"
    if corridor_slug == "valle-crucis-vilas":
        return "Valle Crucis / Vilas"
    if corridor_slug == "deep-gap":
        return "Deep Gap"
    if corridor_slug == "watauga-fringe":
        return "Sugar Grove / Zionville / Todd"
    return None


def municipality_area(city):
    """The named town a property's own stated municipality reports under, or None."""
    muni = " ".join((city or "").lower().replace(".", " ").split())
    muni = MUNICIPALITY_SPELLINGS.get(muni, muni)
    return {"boone": "Boone", "blowing rock": "Blowing Rock", "valle crucis": "Valle Crucis",
            "vilas": "Vilas", "deep gap": "Deep Gap", "sugar grove": "Sugar Grove",
            "zionville": "Zionville", "todd": "Todd"}.get(muni)


def is_future_submarket(postal):
    """True when a postal code belongs to the preserved Banner Elk / Sugar / Beech submarket."""
    z = (postal or "").strip()[:5]
    return any(z in zs for name, _s, zs, why in OUTSIDE if FUTURE_SUBMARKET in why)


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
