"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phase 14: the BringFido competitor gap challenge.

BringFido is IDENTITY DISCOVERY / GAP CHALLENGE ONLY. Never pet-policy authority: no fee, weight, count or "pet
friendly" claim BringFido prints is read, stored or used. Only the listing NAME and the city BringFido prints under it
are kept.

HOW THE SET WAS OBTAINED
------------------------
The plain client is refused on BringFido city pages (Cloudflare's interstitial, HTTP 403, measured by earlier orders).
Firecrawl has NO usable capacity in this order: the shared plan stands at exactly its protected 60-credit reserve until
the billing period renews on 2026-10-19 (live read 2026-10-09), and this order does not consume below the reserve. So
the public pages were read in the SUPPORTED ATTENDED BROWSER (claude-in-chrome): navigate, then the page's own text.
Nothing was solved, clicked through, scripted or bypassed. Every card's name and listed city was transcribed into
``markets/staging/dallas-fort-worth-tx/raw_captures/bringfido_attended_reads_001.json``; this module turns that
transcription into the challenge report the reconciliation reads.

Every city was read through BringFido's OWN "Hotels" property-type filter (``/lodging/hotels/city/<city>/``), whose list
states the city's own hotels and then "N more nearby"; each city was read to its own stated total and at most one page
of the nearby widening. The "hotel" cards can still carry vacation-rental and aggregation listings; every lead is
reconciled by ``dallas_fort_worth_tx_competitor_reconciliation_001`` before any is treated as a hotel. Refused cities'
own pages (Denton, Rockwall, Waxahachie, Weatherford, Cleburne, Waco) were never challenged: a refused place's
inventory is not this market's gap.

Output:
  launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_competitor_challenge_001.json
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

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
TRANSCRIPTION = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures", "bringfido_attended_reads_001.json")
OUT = os.path.join(PKG, "markets", "reports", "dallas_fort_worth_tx_competitor_challenge_001.json")

#: BringFido city page -> the corridor its own city maps to (reporting only).
CITY_CORRIDOR = {
    "dallas_tx_us_hotels": "downtown-dallas", "fort_worth_tx_us_hotels": "downtown-fort-worth",
    "irving_tx_us_hotels": "irving-las-colinas", "arlington_tx_us_hotels": "arlington-entertainment",
    "grapevine_tx_us_hotels": "grapevine-coppell", "plano_tx_us_hotels": "plano", "frisco_tx_us_hotels": "frisco",
    "addison_tx_us_hotels": "addison", "richardson_tx_us_hotels": "richardson",
    "grand_prairie_tx_us_hotels": "grand-prairie", "lewisville_tx_us_hotels": "lewisville-the-colony",
    "carrollton_tx_us_hotels": "carrollton-farmers-branch", "euless_tx_us_hotels": "mid-cities",
    "bedford_tx_us_hotels": "mid-cities", "hurst_tx_us_hotels": "mid-cities",
    "north_richland_hills_tx_us_hotels": "mid-cities", "farmers_branch_tx_us_hotels": "carrollton-farmers-branch",
    "coppell_tx_us_hotels": "grapevine-coppell", "the_colony_tx_us_hotels": "lewisville-the-colony",
    "mckinney_tx_us_hotels": "allen-mckinney", "allen_tx_us_hotels": "allen-mckinney",
    "garland_tx_us_hotels": "garland-mesquite-rowlett", "mesquite_tx_us_hotels": "garland-mesquite-rowlett",
    "southlake_tx_us_hotels": "southlake-flower-mound", "flower_mound_tx_us_hotels": "southlake-flower-mound",
    "mansfield_tx_us_hotels": "mansfield", "duncanville_tx_us_hotels": "south-dallas-county",
    "desoto_tx_us_hotels": "south-dallas-county", "roanoke_tx_us_hotels": "alliance-north-fort-worth",
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
        ("plain_client_measured", "HTTP 403 Cloudflare interstitial on BringFido city pages (measured by earlier "
                                  "orders; the attended browser was the only lane used)"),
        ("firecrawl_capacity", "NONE usable: 60 credits remaining = the protected reserve (live read 2026-10-09); "
                               "billing period ends 2026-10-19. No Firecrawl call was made by this lane."),
        ("refused_cities_never_challenged",
         ["denton_tx_us", "rockwall_tx_us", "waxahachie_tx_us", "weatherford_tx_us", "cleburne_tx_us",
          "decatur_tx_us", "waco_tx_us", "sherman_tx_us"]),
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
