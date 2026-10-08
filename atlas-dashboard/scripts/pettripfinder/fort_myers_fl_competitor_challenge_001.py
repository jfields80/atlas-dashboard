"""PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001 -- Phase 12: the BringFido competitor gap challenge.

BringFido is IDENTITY DISCOVERY / GAP CHALLENGE ONLY. Never pet-policy authority: no fee, weight, count or "pet
friendly" claim BringFido prints is read, stored or used. Only the listing NAME and the city BringFido prints under it
are kept.

HOW THE SET WAS OBTAINED
------------------------
The plain client is refused on every BringFido city page (Cloudflare's interstitial, HTTP 403). Firecrawl, the earlier
markets' lane for these pages, has NO usable capacity in this order: the shared plan stands at exactly its protected
60-credit reserve until the billing period renews on 2026-10-19 (live read 2026-10-08), and this order does not consume
below the reserve. So the same public pages were read in the SUPPORTED ATTENDED BROWSER (claude-in-chrome): navigate,
then the page's own text. Nothing was solved, clicked through, scripted or bypassed. Every card's name and listed city
was transcribed into ``markets/staging/fort-myers-fl/raw_captures/bringfido_attended_reads_001.json``; this module
turns that transcription into the challenge report the reconciliation reads.

THREE CAPTURE FACTS RECORDED RATHER THAN HIDDEN
----------------------------------------------
1. BringFido silently WIDENS ITS RADIUS past a city's own stated total (Fort Myers's page 7 lists Bonita Springs,
   Saint James City, Matlacha and the islands). Fort Myers was read to its own stated total (122) and one page beyond;
   the widening is reported as OUTSIDE or matched, not corrected.
2. Cape Coral's unfiltered list states 616 listings, and every card on its first two pages is a private home. The city
   (and Fort Myers Beach, Sanibel, Bonita Springs, Estero and North Fort Myers) was therefore read through BringFido's
   OWN "Hotels" property-type filter (``/lodging/hotels/city/<city>/``), whose list states the city's own hotels and
   then "N more nearby" -- a regional hotel list that the reconciliation places by name and the census by postal code.
3. BringFido publishes no Captiva and no Lehigh Acres page (HTTP 404, recorded).

The "hotel" cards still carry vacation-rental, condo-unit and Airbnb / VRBO aggregation listings; every lead is
reconciled by ``fort_myers_fl_competitor_reconciliation_001`` before any is treated as a hotel. Refused cities' own
pages (Naples, Marco Island, Punta Gorda, Port Charlotte) were never challenged: a refused place's inventory is not this
market's gap.

Output:
  launch_packages/pettripfinder/markets/reports/fort_myers_fl_competitor_challenge_001.json
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

WORK_ORDER = "PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "fort-myers-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
TRANSCRIPTION = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures", "bringfido_attended_reads_001.json")
OUT = os.path.join(PKG, "markets", "reports", "fort_myers_fl_competitor_challenge_001.json")

#: BringFido city page -> the corridor its own city maps to (reporting only).
CITY_CORRIDOR = {
    "fort_myers_fl_us": "downtown-fort-myers", "cape_coral_fl_us_hotels": "cape-coral",
    "fort_myers_beach_fl_us_hotels": "fort-myers-beach", "sanibel_fl_us_hotels": "sanibel",
    "bonita_springs_fl_us_hotels": "bonita-springs", "estero_fl_us_hotels": "estero",
    "north_fort_myers_fl_us_hotels": "north-fort-myers", "captiva_fl_us": "captiva",
    "lehigh_acres_fl_us_hotels": "lehigh-acres-alva",
}

def _page_url(slug, page):
    if slug.endswith("_hotels"):
        url = "https://www.bringfido.com/lodging/hotels/city/%s/" % slug[:-len("_hotels")]
    else:
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
        ("plain_client_measured", "HTTP 403 Cloudflare interstitial on BringFido city pages (measured by the "
                                  "parent order and unchanged: the attended browser was the only lane used)"),
        ("cape_coral_unfiltered_measurement", doc.get("cape_coral_unfiltered_measurement")),
        ("firecrawl_capacity", "NONE usable: 60 credits remaining = the protected reserve (live read 2026-10-08); "
                               "billing period ends 2026-10-19. No Firecrawl call was made by this lane."),
        ("refused_cities_never_challenged",
         ["naples_fl_us", "marco_island_fl_us", "punta_gorda_fl_us", "port_charlotte_fl_us", "englewood_fl_us",
          "boca_grande_fl_us", "sarasota_fl_us"]),
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
