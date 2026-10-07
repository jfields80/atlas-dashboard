"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phase 12: the BringFido competitor gap challenge.

BringFido is IDENTITY DISCOVERY / GAP CHALLENGE ONLY. Never pet-policy authority: no fee, weight, count or "pet
friendly" claim BringFido prints is read, stored or used. Only the listing NAME and the city BringFido prints under it
are kept.

HOW THE SET WAS OBTAINED
------------------------
The plain client is refused on every BringFido city page (Cloudflare's "Just a moment" interstitial, HTTP 403 --
measured on salt_lake_city_ut_us and park_city_ut_us, 2026-10-07). Firecrawl, the earlier markets' lane for these
pages, has NO usable capacity in this order: the shared plan stands at exactly its protected 60-credit reserve until
the billing period renews on 2026-10-19, and this order does not consume below the reserve. So the same public pages
were read in the SUPPORTED ATTENDED BROWSER (claude-in-chrome): navigate, then the page's own text. The interstitial
cleared itself in that browser; nothing was solved, clicked, scripted or bypassed. Every card's name and listed city
was transcribed into ``markets/staging/salt-lake-city-ut/raw_captures/bringfido_attended_reads_001.json``; this
module turns that transcription into the challenge report the reconciliation reads.

TWO CAPTURE HAZARDS INHERITED AS FIXES RATHER THAN REDISCOVERED
---------------------------------------------------------------
1. BringFido silently WIDENS ITS RADIUS past a city's own stated total (Salt Lake City's page 10 lists Morgan,
   Farmington and the suburbs; Park City's page 9 lists Coalville, Heber City, Midway, Kamas and Pleasant Grove).
   Each city was read to its own stated total and not beyond; the widening is reported as OUTSIDE, not corrected.
2. The "hotel" cards carry vacation-rental, condo-unit, townhome, chalet and Airbnb / VRBO aggregation listings --
   in Park City the large majority. Every lead is reconciled by ``salt_lake_city_ut_competitor_reconciliation_001``
   before any is treated as a hotel.

Refused cities' own pages (Provo, Orem, Ogden, Heber City, Midway, Snowbird, Alta, Moab, St. George) were never
challenged: a refused place's inventory is not this market's gap.

Output:
  launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_competitor_challenge_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
MARKET_ID = "salt-lake-city-ut"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
TRANSCRIPTION = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures", "bringfido_attended_reads_001.json")
OUT = os.path.join(PKG, "markets", "reports", "salt_lake_city_ut_competitor_challenge_001.json")

#: BringFido city page -> the corridor its own city maps to (reporting only).
CITY_CORRIDOR = {
    "salt_lake_city_ut_us": "downtown-salt-lake-city", "park_city_ut_us": "park-city", "sandy_ut_us": "sandy",
    "draper_ut_us": "draper", "murray_ut_us": "murray", "lehi_ut_us": "lehi",
    "west_valley_city_ut_us": "west-valley-city", "midvale_ut_us": "midvale", "south_jordan_ut_us": "south-jordan",
    "west_jordan_ut_us": "west-jordan", "cottonwood_heights_ut_us": "cottonwood-heights-holladay",
}


def _page_url(slug, page):
    url = "https://www.bringfido.com/lodging/city/%s/" % slug
    return url + ("?page=%d" % page if page > 1 else "")


def build():
    doc = json.load(open(TRANSCRIPTION, encoding="utf-8"))
    display = {p["city_slug"]: p["display"] for p in doc["pages"]}
    cities = OrderedDict()
    for p in doc["pages"]:
        cards = [c for c in doc["cards"] if c[0] == p["city_slug"]]
        cities[p["city_slug"]] = OrderedDict([
            ("city_slug", p["city_slug"]), ("display_name", p["display"]),
            ("corridor_slug", CITY_CORRIDOR.get(p["city_slug"])),
            ("source_first_page", _page_url(p["city_slug"], 1)),
            ("stated_total_hotels", p.get("stated_total")), ("pages_fetched", p.get("pages_read")),
            ("note", p.get("note", "")), ("hotel_items_captured", len(cards)),
        ])
    by_key = OrderedDict()
    for slug, page, name, listed_city in doc["cards"]:
        key = (normalize_name(name), listed_city.lower())
        src = _page_url(slug, page)
        if key not in by_key:
            by_key[key] = OrderedDict([
                ("name", name),
                ("bringfido_url", "%s#%s" % (src, re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"))),
                ("listed_city", listed_city), ("first_seen_city", display[slug]),
                ("first_seen_corridor_slug", CITY_CORRIDOR.get(slug)), ("also_listed_under", [])])
        elif display[slug] != by_key[key]["first_seen_city"] and display[slug] not in by_key[key]["also_listed_under"]:
            by_key[key]["also_listed_under"].append(display[slug])
    raw = len(doc["cards"])
    leads = list(by_key.values())
    return OrderedDict([
        ("schema", "ptf-competitor-challenge/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("competitor", "BringFido"), ("observed_at", doc.get("read_on")),
        ("capture_lane", doc.get("capture_lane")),
        ("never_policy_authority",
         "Names and BringFido's listed city only. A competitor lead proposes an identity and is reconciled against "
         "the census; every BringFido pet claim is never read as policy and can never publish one."),
        ("plain_client_measured", "HTTP 403 Cloudflare interstitial on salt_lake_city_ut_us and park_city_ut_us "
                                  "(2026-10-07)"),
        ("firecrawl_capacity", "NONE usable: 60 credits remaining = the protected reserve; billing period ends "
                               "2026-10-19. No Firecrawl call was made by this lane."),
        ("refused_cities_never_challenged",
         ["provo_ut_us", "orem_ut_us", "ogden_ut_us", "heber_city_ut_us", "midway_ut_us", "snowbird_ut_us",
          "alta_ut_us", "moab_ut_us", "st_george_ut_us", "springdale_ut_us"]),
        ("cities_challenged", len(cities)),
        ("cities", cities),
        ("raw_captured", raw),
        ("normalized_unique", len(leads)),
        ("duplicates_across_city_pages", raw - len(leads)),
        ("leads_by_listed_city", OrderedDict(sorted(Counter(l["listed_city"] for l in leads).items()))),
        ("leads", leads),
        ("stated_totals_by_city", OrderedDict((c["display_name"], c["stated_total_hotels"]) for c in cities.values())),
        ("transport", OrderedDict([("name", "attended_browser"), ("credits_used", 0),
                                   ("page_reads", sum(p.get("pages_read") or 0 for p in doc["pages"]))])),
        ("credits_used_all_runs", 0),
    ])


def main(argv=None):
    rep = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("raw", rep["raw_captured"], "unique", rep["normalized_unique"])
    print("by listed city:", dict(rep["leads_by_listed_city"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
