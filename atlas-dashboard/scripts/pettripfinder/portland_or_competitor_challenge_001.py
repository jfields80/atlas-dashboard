"""PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001 -- Phase 11: the BringFido competitor gap challenge.

BringFido is IDENTITY DISCOVERY / GAP CHALLENGE ONLY. Never pet-policy authority: no fee, weight, count or "pet
friendly" claim BringFido prints is read, stored or used. Only the listing NAME, its own BringFido URL and its
own schema.org type are kept.

HOW THE SET IS OBTAINED
-----------------------
BringFido's server response embeds a schema.org ``ItemList`` of ``@type: "Hotel"`` entries in each city page's
own JSON-LD, so a plain HTTP GET reads the whole card grid with no browser and no lazy-render coverage caveat
(the Tampa V2 finding, carried through Orlando V2, Miami, Fort Lauderdale and West Palm Beach). Each city page is
paginated with ``?page=N``. Every raw page is persisted at ``data/portland_or/bringfido/<slug>_page<N>.html``
(gitignored, sha256 recorded here) before being parsed.

TWO CAPTURE HAZARDS INHERITED AS FIXES RATHER THAN REDISCOVERED
---------------------------------------------------------------
1. BringFido enforces a hard site-wide cap of 20 result pages (page 21 always answers 404), but for a city whose
   inventory is smaller than that it does not stop at an empty page -- it silently widens the search radius past
   the city's own stated total and returns NEIGHBOURING cities' hotels under this city's URL. This lane stops
   paginating a city once its captured count reaches its own page-1 stated total.
2. The Hotel-typed JSON-LD DOES carry vacation-rental and condo-unit listings (Tampa excluded 559 of them). Every
   lead is reconciled by ``portland_or_competitor_reconciliation_001`` before any is treated as a hotel.

WHY THAT SECOND HAZARD MATTERS IN THIS MARKET
---------------------------------------------
Portland's furnished condo and apartment units in the Pearl, South Waterfront and the Lloyd District, the
serviced-apartment and aparthotel operators (Sonder, Kasa, Mint House, Placemakr, Blueground, Lark, Barsala), the
coast, Gorge and Mount Hood cabins and Portland's large Airbnb inventory are all listed by BringFido as "hotels".
None of that is a hotel identity.

AND WHY THE CITY SLUG LIST IS THE RISKY PART HERE
-------------------------------------------------
BringFido widens by RADIUS. Camas, Washougal, Newberg, Sandy, Canby, Oregon's wine country and the Gorge are close
enough that later pages of the Portland city page will return some of them. That is EXPECTED and is not corrected
here: every lead is placed by the reconciliation on its own premises, and the OUTSIDE count is reported rather than
hidden. What this lane does NOT do is challenge a refused city's own page -- no ``salem_or_us``, no
``hood_river_or_us``, no ``cannon_beach_or_us``, no ``newberg_or_us``, no ``camas_wa_us`` -- because a refused
place's inventory is not this market's gap. Vancouver, WA's own page IS challenged: Vancouver is an in-market
corridor.

THE PLAIN CLIENT IS REFUSED -- MEASURED
---------------------------------------
On 2026-10-03 the BringFido Portland city page (portland_or_us) returned HTTP 403 (5,769 bytes, Cloudflare's
interstitial) to the plain client, exactly as the Seattle, San Antonio and Austin city pages did. The challenge is not solved
or bypassed. The same public page is instead read through Firecrawl (``--transport firecrawl``), an EXISTING
authorized provider on existing plan credits, capped on ATTEMPTS (``--cap-attempts``) with the live credit balance
read before and after: one credit per page that renders, zero when every engine is refused. The page's own
server-rendered JSON-LD is parsed exactly as before.

Output:
  launch_packages/pettripfinder/markets/reports/portland_or_competitor_challenge_001.json
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

WORK_ORDER = "PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001"
MARKET_ID = "portland-or"
DOCS = os.path.join(_DASH, "data", "portland_or", "bringfido")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "portland_or_competitor_challenge_001.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
MAX_PAGES_PER_CITY = 30

#: (slug, display name, corridor slug this city's page maps to for reporting)
CITIES = [
    ("portland_or_us", "Portland", "downtown-portland"),
    ("beaverton_or_us", "Beaverton", "beaverton"),
    ("hillsboro_or_us", "Hillsboro", "hillsboro"),
    ("tigard_or_us", "Tigard", "tigard"),
    ("lake_oswego_or_us", "Lake Oswego", "lake-oswego"),
    ("gresham_or_us", "Gresham", "gresham"),
    ("tualatin_or_us", "Tualatin", "tualatin-wilsonville"),
    ("wilsonville_or_us", "Wilsonville", "tualatin-wilsonville"),
    ("clackamas_or_us", "Clackamas", "clackamas-happy-valley"),
    ("happy_valley_or_us", "Happy Valley", "clackamas-happy-valley"),
    ("troutdale_or_us", "Troutdale", "troutdale-fairview"),
    ("fairview_or_us", "Fairview", "troutdale-fairview"),
    ("milwaukie_or_us", "Milwaukie", "milwaukie"),
    ("oregon_city_or_us", "Oregon City", "oregon-city-west-linn"),
    ("west_linn_or_us", "West Linn", "oregon-city-west-linn"),
    ("sherwood_or_us", "Sherwood", "sherwood"),
    ("forest_grove_or_us", "Forest Grove", "forest-grove-cornelius"),
    ("vancouver_wa_us", "Vancouver, WA", "vancouver-wa"),
]

ALL_CITIES = list(CITIES)

_STATED = re.compile(r"([\d,]+)\s*pet friendly hotels", re.I)


TRANSPORT = {"name": "plain", "attempts": 0, "cap": 10 ** 6}


def fetch(url):
    if TRANSPORT["name"] == "firecrawl":
        from scripts.pettripfinder.acquisition import firecrawl_capture as FC
        if TRANSPORT["attempts"] >= TRANSPORT["cap"]:
            return None, b"ATTEMPT_CAP_REACHED"
        TRANSPORT["attempts"] += 1
        try:
            res = FC.fetch(url)
        except Exception as exc:  # noqa: BLE001
            return None, ("%s: %s" % (type(exc).__name__, exc)).encode("utf-8")
        body = (res.get("html") or "").encode("utf-8")
        return (res.get("status") or (200 if body else None)), body
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


def build(prior_cities=None):
    """``prior_cities``: city blocks KEPT from the report already on disk (a ``--only`` run re-walks only the named
    cities and never re-buys a page another run already read)."""
    cities = OrderedDict()
    run_slugs = {c[0] for c in CITIES}
    for slug, display, corridor in ALL_CITIES:
        if slug not in run_slugs:
            if prior_cities and slug in prior_cities:
                cities[slug] = prior_cities[slug]
            continue
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
        ("competitor", "BringFido"), ("observed_at", time.strftime("%Y-%m-%d", time.gmtime())),
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
         "read as a hotel. In THIS market the radius widening is expected to reach Camas, Newberg, Sandy, Canby "
         "and the Gorge -- that is reported as an OUTSIDE count, not "
         "corrected, and no refused city's own page is ever challenged, because a refused place's inventory is "
         "not this market's gap."),
        ("refused_cities_never_challenged",
         ["salem_or_us", "keizer_or_us", "woodburn_or_us", "eugene_or_us", "hood_river_or_us", "cascade_locks_or_us",
          "the_dalles_or_us", "stevenson_wa_us", "government_camp_or_us", "welches_or_us", "sandy_or_us",
          "seaside_or_us", "cannon_beach_or_us", "astoria_or_us", "lincoln_city_or_us", "bend_or_us",
          "newberg_or_us", "mcminnville_or_us", "canby_or_us", "st_helens_or_us", "scappoose_or_us",
          "camas_wa_us", "washougal_wa_us", "battle_ground_wa_us", "ridgefield_wa_us", "longview_wa_us",
          "kelso_wa_us"]),
        ("cities_challenged", len(cities)),
        ("cities", cities),
        ("raw_captured", raw_captured),
        ("normalized_unique", normalized_unique),
        ("duplicates_across_city_pages", raw_captured - normalized_unique),
        ("leads", list(by_url.values())),
        ("stated_totals_by_city", OrderedDict((c["display_name"], c["stated_total_hotels"]) for c in cities.values())),
    ])


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--transport", choices=("plain", "firecrawl"), default="plain")
    ap.add_argument("--cap-attempts", type=int, default=60)
    ap.add_argument("--only", default=None, help="comma list of city slugs")
    ap.add_argument("--max-pages", type=int, default=None,
                    help="per-city page cap: a suburb's later pages are BringFido's radius widening of the metro list")
    args = ap.parse_args(argv)
    TRANSPORT["name"], TRANSPORT["cap"] = args.transport, args.cap_attempts
    before = None
    if args.transport == "firecrawl":
        from scripts.pettripfinder.acquisition import firecrawl_capture as FC
        before = FC.credits_remaining()
    global CITIES, MAX_PAGES_PER_CITY
    if args.max_pages:
        MAX_PAGES_PER_CITY = args.max_pages
    prior = None
    if args.only:
        keep = set(args.only.split(","))
        CITIES = [c for c in CITIES if c[0] in keep]
        if os.path.exists(OUT):
            prior = json.load(open(OUT, encoding="utf-8"))
    rep = build(prior_cities=(prior or {}).get("cities"))
    rep["earlier_runs"] = list((prior or {}).get("earlier_runs") or []) + (
        [prior["transport"]] if prior and prior.get("transport") else [])
    rep["transport"] = OrderedDict([
        ("name", args.transport),
        ("why", "the plain client is refused by Cloudflare's interstitial on every BringFido page (measured "
                "by this order on its own first page); the challenge is never solved or bypassed" if args.transport == "firecrawl" else
         "plain HTTP GET"),
        ("attempts", TRANSPORT["attempts"]), ("cap_attempts", args.cap_attempts)])
    if args.transport == "firecrawl":
        after = FC.credits_remaining()
        rep["transport"]["credits_before"] = before
        rep["transport"]["credits_after"] = after
        rep["transport"]["credits_used"] = (before - after) if (before is not None and after is not None) else None
    rep["transport"]["max_pages_per_city"] = MAX_PAGES_PER_CITY
    rep["credits_used_all_runs"] = sum(int(r.get("credits_used") or 0)
                                       for r in rep["earlier_runs"] + [rep["transport"]])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("raw", rep["raw_captured"], "unique", rep["normalized_unique"])
    print("stated totals:", rep["stated_totals_by_city"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
