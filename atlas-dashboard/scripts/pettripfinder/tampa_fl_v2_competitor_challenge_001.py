"""PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 9/10: the BringFido competitor challenge set.

BringFido is IDENTITY DISCOVERY / GAP CHALLENGE ONLY. Never pet-policy authority: no fee, weight, count or "pet
friendly" claim BringFido prints is read, stored or used. Only the listing NAME, its own BringFido URL and its
own schema.org type are kept.

HOW THE SET WAS OBTAINED -- A METHOD IMPROVEMENT OVER THE ORLANDO V2 PRECEDENT
--------------------------------------------------------------------------------
Orlando V2 read BringFido's city page through the supported attended browser (navigate + accessibility-tree
reads of lazily rendered cards), because the visible card grid mixed hotels and vacation-rental listings and
needed a name-regex classifier, with a recorded coverage caveat (a few cards on rental-heavy tail pages were
missed by the 20-card accessibility read). Reading Tampa's own city page here found that BringFido's server
response ALREADY embeds a schema.org ``ItemList`` of ``@type: "Hotel"`` entries in the page's own JSON-LD --
plain HTTP GET, no browser needed, and no vacation-rental card is embedded in this markup at all (BringFido
files vacation rentals under a separate "Vacation Rentals" tab this order does not fetch, since a rental could
never be a hotel identity regardless of how it is discovered). This is a more complete and more reliable
capture than a 20-card accessibility-tree read: no coverage caveat, and no name-regex guesswork for the
hotel/rental split, because BringFido's own markup already types each entry.

Each city page is paginated with ``?page=N`` until a page returns zero ``Hotel`` entries. Every raw page is
persisted (durable evidence) at ``data/tampa_fl_v2/bringfido/<city_slug>_page<N>.html`` (gitignored, sha256
recorded here) before being parsed.

Cities challenged (every BringFido city slug that resolved 200 across the Tampa Bay corridor set): Tampa,
St. Petersburg, Clearwater, Clearwater Beach, St. Pete Beach, Treasure Island, Madeira Beach, Largo, Brandon.
Ybor City has no separate BringFido city page (404); it is inside the Tampa page.

Output:
  launch_packages/pettripfinder/markets/reports/tampa_fl_v2_competitor_challenge_001.json
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

WORK_ORDER = "PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "tampa-fl"
DOCS = os.path.join(_DASH, "data", "tampa_fl_v2", "bringfido")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "tampa_fl_v2_competitor_challenge_001.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
MAX_PAGES_PER_CITY = 30

#: (slug, display name, corridor slug this city's page maps to for reporting)
CITIES = [
    ("tampa_fl_us", "Tampa", "downtown-riverwalk"),
    ("saint_petersburg_fl_us", "St. Petersburg", "st-petersburg-downtown"),
    ("clearwater_fl_us", "Clearwater", "clearwater-downtown"),
    ("clearwater_beach_fl_us", "Clearwater Beach", "clearwater-beach"),
    ("saint_pete_beach_fl_us", "St. Pete Beach", "st-pete-beach-treasure-island"),
    ("treasure_island_fl_us", "Treasure Island", "st-pete-beach-treasure-island"),
    ("madeira_beach_fl_us", "Madeira Beach", "madeira-redington-indian-rocks"),
    ("largo_fl_us", "Largo", "largo"),
    ("brandon_fl_us", "Brandon", "brandon"),
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
        ("competitor", "BringFido"), ("observed_at", "2026-09-15"),
        ("capture_lane",
         "plain HTTP GET of each city's own page; every listing is read from the page's own schema.org "
         "JSON-LD ItemList of @type Hotel entries (name, BringFido URL, petsAllowed claim), paginated with "
         "?page=N until a page returns zero Hotel entries. No browser, no page script."),
        ("never_policy_authority",
         "Names and BringFido's own URL only. A competitor lead proposes an identity and is reconciled against "
         "the census; petsAllowed and every other BringFido claim is never read as policy and can never publish one."),
        ("method_note",
         "An improvement over the Orlando V2 precedent's supported-browser accessibility-tree read: BringFido's "
         "own server-rendered JSON-LD already separates Hotel-typed entries from its Vacation Rentals tab, so "
         "no name-regex hotel/rental classifier and no lazy-render coverage caveat are needed here. One capture "
         "hazard was found and corrected: BringFido enforces a hard site-wide cap of 20 result pages (page 21 "
         "always answers 404, matching the Orlando V2 finding), but for a city whose own inventory is smaller "
         "than 20 pages it does not stop at an empty page -- it silently widens the search radius past the "
         "city's own stated total and starts returning neighbouring cities' hotels under this city's URL. This "
         "lane stops paginating a city once its own captured count reaches its own page-1 stated total, so a "
         "small city's later pages never mislabel a neighbour's inventory as its own."),
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
