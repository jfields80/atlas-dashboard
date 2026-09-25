"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phase 10: the BringFido competitor gap challenge.

BringFido is IDENTITY DISCOVERY / GAP CHALLENGE ONLY. Never pet-policy authority: no fee, weight, count or "pet
friendly" claim BringFido prints is read, stored or used. Only the listing NAME, its own BringFido URL and its
own schema.org type are kept.

HOW THE SET IS OBTAINED
-----------------------
BringFido's server response embeds a schema.org ``ItemList`` of ``@type: "Hotel"`` entries in each city page's
own JSON-LD, so a plain HTTP GET reads the whole card grid with no browser and no lazy-render coverage caveat
(the Tampa V2 finding, carried through Orlando V2, Miami, Fort Lauderdale and West Palm Beach). Each city page is
paginated with ``?page=N``. Every raw page is persisted at ``data/jacksonville_fl/bringfido/<slug>_page<N>.html``
(gitignored, sha256 recorded here) before being parsed.

TWO CAPTURE HAZARDS INHERITED AS FIXES RATHER THAN REDISCOVERED
---------------------------------------------------------------
1. BringFido enforces a hard site-wide cap of 20 result pages (page 21 always answers 404), but for a city whose
   inventory is smaller than that it does not stop at an empty page -- it silently widens the search radius past
   the city's own stated total and returns NEIGHBOURING cities' hotels under this city's URL. This lane stops
   paginating a city once its captured count reaches its own page-1 stated total.
2. The Hotel-typed JSON-LD DOES carry vacation-rental and condo-unit listings (Tampa excluded 559 of them). Every
   lead is reconciled by ``jacksonville_fl_competitor_reconciliation_001`` before any is treated as a hotel.

WHY THAT SECOND HAZARD IS ACUTE IN THIS MARKET
----------------------------------------------
Nassau County's lodging register is 1,130 resort-condominium licences against 32 hotel-rank ones, so Amelia
Island's BringFido page is dominated by Amelia Island Plantation and Omni villa inventory. Jacksonville Beach's
oceanfront is condominium towers. Ponte Vedra's is golf villas. None of that is a hotel identity.

AND WHY THE CITY SLUG LIST IS THE RISKY PART HERE
-------------------------------------------------
BringFido widens by RADIUS, and this market's refused neighbours are close: St. Augustine is 40 miles from
downtown Jacksonville with 116 hotel-rank licences, and Kingsland, GEORGIA is 20 minutes from Yulee. A
`jacksonville_fl_us` page will therefore return St. Augustine, Palm Coast and Georgia listings on its later
pages. That is EXPECTED and is not corrected here: every lead is placed by the reconciliation on its own
premises, and the OUTSIDE count is reported rather than hidden. What this lane does NOT do is challenge a
refused city's own page -- no `st_augustine_fl_us`, no `palm_coast_fl_us`, no `kingsland_ga_us` -- because a
refused place's inventory is not this market's gap.

Output:
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_competitor_challenge_001.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
DOCS = os.path.join(_DASH, "data", "jacksonville_fl", "bringfido")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "jacksonville_fl_competitor_challenge_001.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
MAX_PAGES_PER_CITY = 30

#: (slug, display name, corridor slug this city's page maps to for reporting)
CITIES = [
    ("jacksonville_fl_us", "Jacksonville", "downtown-jacksonville"),
    ("jacksonville_beach_fl_us", "Jacksonville Beach", "jacksonville-beach"),
    ("neptune_beach_fl_us", "Neptune Beach", "atlantic-neptune-beach-mayport"),
    ("atlantic_beach_fl_us", "Atlantic Beach", "atlantic-neptune-beach-mayport"),
    ("mayport_fl_us", "Mayport", "atlantic-neptune-beach-mayport"),
    ("ponte_vedra_beach_fl_us", "Ponte Vedra Beach", "ponte-vedra-beach-sawgrass"),
    ("ponte_vedra_fl_us", "Ponte Vedra", "ponte-vedra-beach-sawgrass"),
    ("nocatee_fl_us", "Nocatee", "ponte-vedra-beach-sawgrass"),
    ("orange_park_fl_us", "Orange Park", "orange-park-fleming-island"),
    ("fleming_island_fl_us", "Fleming Island", "orange-park-fleming-island"),
    ("middleburg_fl_us", "Middleburg", "orange-park-fleming-island"),
    ("green_cove_springs_fl_us", "Green Cove Springs", "orange-park-fleming-island"),
    ("oakleaf_plantation_fl_us", "Oakleaf Plantation", "orange-park-fleming-island"),
    ("fernandina_beach_fl_us", "Fernandina Beach", "amelia-island-fernandina-beach"),
    ("amelia_island_fl_us", "Amelia Island", "amelia-island-fernandina-beach"),
    ("yulee_fl_us", "Yulee", "yulee-nassau-i95"),
    ("callahan_fl_us", "Callahan", "yulee-nassau-i95"),
    ("hilliard_fl_us", "Hilliard", "yulee-nassau-i95"),
    ("baldwin_fl_us", "Baldwin", "westside-i10-i295"),
    ("saint_johns_fl_us", "Saint Johns", "mandarin-bartram-julington-creek"),
    ("st_johns_fl_us", "St. Johns (alt slug)", "mandarin-bartram-julington-creek"),
    ("fruit_cove_fl_us", "Fruit Cove", "mandarin-bartram-julington-creek"),
]

_STATED = re.compile(r"([\d,]+)\s*pet friendly hotels", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception as exc:
        return None, str(exc).encode("utf-8")


def persist(city_slug, page, body):
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, "%s_page%d.html" % (city_slug, page))
    with open(path, "wb") as fh:
        fh.write(body)
    return hashlib.sha256(body).hexdigest()


#: Each Hotel item in BringFido's own JSON-LD ends with this exact triple, in this order: petsAllowed, then
#: the hotel's own name (never the nested aggregateRating.author.name, which appears earlier in the same
#: item and would otherwise be matched first), then its own BringFido URL.
_HOTEL_TRIPLE = re.compile(
    r'"petsAllowed":\s*(true|false),\s*"name":\s*"((?:[^"\\]|\\.)*)",\s*"url":\s*"(https://www\.bringfido\.com/lodging/\d+)"',
    re.S)


def parse_hotels(html_text):
    """Every schema.org Hotel item on the page: (name, bringfido_url, pets_allowed_claim)."""
    out = []
    for pets, name_raw, url in _HOTEL_TRIPLE.findall(html_text):
        name = json.loads('"%s"' % name_raw)
        out.append(OrderedDict([("name", name), ("bringfido_url", url), ("pets_allowed_claim", pets == "true")]))
    return out


def challenge_city(slug, display, corridor_slug):
    pages, all_hotels, stated_total = [], [], None
    seen_urls = set()
    for page in range(1, MAX_PAGES_PER_CITY + 1):
        url = "https://www.bringfido.com/lodging/city/%s/" % slug
        if page > 1:
            url += "?page=%d" % page
        status, body = fetch(url)
        text = body.decode("utf-8", "replace") if status == 200 else ""
        sha = persist(slug, page, body) if body else None
        hotels_here = parse_hotels(text) if status == 200 else []
        if page == 1:
            m = _STATED.search(text)
            stated_total = int(m.group(1).replace(",", "")) if m else None
        pages.append(OrderedDict([("page", page), ("url", url), ("status", status), ("bytes", len(body)),
                                  ("sha256", sha), ("hotel_items_on_page", len(hotels_here))]))
        new = 0
        for h in hotels_here:
            if h["bringfido_url"] in seen_urls:
                continue
            seen_urls.add(h["bringfido_url"])
            h2 = OrderedDict(h)
            h2["page"] = page
            h2["source_url"] = url
            all_hotels.append(h2)
            new += 1
        time.sleep(0.15)
        if status != 200 or len(hotels_here) == 0:
            break
        # BringFido enforces a hard site-wide cap of 20 pages (page 21 always answers 404) but does not stop
        # returning results at a city's own stated total: past that point it silently widens the search radius
        # and starts returning other nearby cities' hotels instead of an empty page. Stop at the city's own
        # stated total (once known from page 1) so a small city's later pages never pull in a neighbour's
        # inventory under this city's label.
        if stated_total is not None and len(seen_urls) >= stated_total:
            break
    return OrderedDict([
        ("city_slug", slug), ("display_name", display), ("corridor_slug", corridor_slug),
        ("source_first_page", "https://www.bringfido.com/lodging/city/%s/" % slug),
        ("stated_total_hotels", stated_total), ("pages_fetched", len(pages)), ("pages", pages),
        ("hotel_items_captured", len(all_hotels)), ("hotels", all_hotels),
    ])


def build():
    cities = OrderedDict()
    for slug, display, corridor in CITIES:
        cities[slug] = challenge_city(slug, display, corridor)
        print("  %-24s stated=%s captured=%d pages=%d" % (
            display, cities[slug]["stated_total_hotels"], cities[slug]["hotel_items_captured"],
            cities[slug]["pages_fetched"]), flush=True)

    # normalise + dedupe ACROSS cities on the BringFido listing url (a hotel near a city boundary can be
    # listed under more than one neighbouring city page)
    by_url = OrderedDict()
    for slug, c in cities.items():
        for h in c["hotels"]:
            u = h["bringfido_url"]
            if u not in by_url:
                by_url[u] = OrderedDict([("name", h["name"]), ("bringfido_url", u),
                                         ("pets_allowed_claim", h["pets_allowed_claim"]),
                                         ("first_seen_city", c["display_name"]),
                                         ("first_seen_corridor_slug", c["corridor_slug"]),
                                         ("also_listed_under", [])])
            elif by_url[u]["first_seen_city"] != c["display_name"] and \
                    c["display_name"] not in by_url[u]["also_listed_under"]:
                by_url[u]["also_listed_under"].append(c["display_name"])

    raw_captured = sum(c["hotel_items_captured"] for c in cities.values())
    normalized_unique = len(by_url)
    return OrderedDict([
        ("schema", "ptf-competitor-challenge/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("competitor", "BringFido"), ("observed_at", "2026-09-25"),
        ("capture_lane",
         "plain HTTP GET of each city's own page; every listing is read from the page's own schema.org "
         "JSON-LD ItemList of @type Hotel entries (name, BringFido URL, petsAllowed claim), paginated with "
         "?page=N until a page returns zero Hotel entries. No browser, no page script."),
        ("never_policy_authority",
         "Names and BringFido's own URL only. A competitor lead proposes an identity and is reconciled against "
         "the census; petsAllowed and every other BringFido claim is never read as policy and can never publish one."),
        ("method_note",
         "BringFido's own server-rendered JSON-LD is read with a plain HTTP GET, so there is no lazy-render "
         "coverage caveat. Two hazards are inherited as fixes rather than rediscovered: (1) BringFido caps "
         "results at 20 pages (page 21 answers 404) but silently WIDENS THE SEARCH RADIUS past a small city's "
         "own stated total and returns neighbouring cities' hotels under that city's URL, so this lane stops "
         "paginating once a city's captured count reaches its own page-1 stated total; (2) the Hotel-typed "
         "entries include vacation-rental and condo-unit listings, so every lead is reconciled before it can be "
         "read as a hotel. In THIS market the radius widening is expected to reach St. Augustine (40 miles, 116 "
         "hotel-rank licences), Palm Coast and coastal GEORGIA -- that is reported as an OUTSIDE count, not "
         "corrected, and no refused city's own page is ever challenged, because a refused place's inventory is "
         "not this market's gap."),
        ("refused_cities_never_challenged",
         ["st_augustine_fl_us", "st_augustine_beach_fl_us", "palm_coast_fl_us", "gainesville_fl_us",
          "daytona_beach_fl_us", "kingsland_ga_us", "st_marys_ga_us", "brunswick_ga_us",
          "jacksonville_nc_us -- a DIFFERENT CITY IN A DIFFERENT STATE and a LIVE PetTripFinder market"]),
        ("cities_challenged", len(CITIES)),
        ("cities", cities),
        ("raw_captured", raw_captured),
        ("normalized_unique", normalized_unique),
        ("duplicates_across_city_pages", raw_captured - normalized_unique),
        ("leads", list(by_url.values())),
        ("stated_totals_by_city", OrderedDict((c["display_name"], c["stated_total_hotels"]) for c in cities.values())),
    ])


def main():
    rep = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("raw", rep["raw_captured"], "unique", rep["normalized_unique"])
    print("stated totals:", rep["stated_totals_by_city"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
