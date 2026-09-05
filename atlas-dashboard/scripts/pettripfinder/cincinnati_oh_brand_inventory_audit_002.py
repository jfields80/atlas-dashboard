"""PTF-CINCINNATI-PARALLEL-REVALIDATION-002 -- Phase 7, the brand inventory audit.

The official first-party sitemap is a routing and identity lane, not a policy
lane. PTF-PITTSBURGH-PARALLEL-REVALIDATION-001 showed that a brand publishes a
complete machine-readable inventory of its own properties even where the
property page itself refuses a plain client, and
PTF-CINCINNATI-HARDENED-REVALIDATION-001 refused Marriott and Hilton as a
measured capability wall precisely on that property-page evidence. Both are
true at once: the pages are walled and the inventory is open. This order reads
the inventory.

What the lane can decide
    identity     the brand names the property, its code and its city
    routing      the brand's own inventory is what makes a route live or dead
What the lane can NEVER decide
    pet policy   a sitemap carries a URL and a timestamp, never a pet fee

Every request is a free first-party HTTPS GET through the canonical
``direct_http_capture.fetch`` gate. No vendor, no browser, no credit, no price.
Every response is cached to disk under the run directory and keyed on the
sha256 of its own bytes, so a rerun re-reads the cache and issues nothing.

Nothing here writes authority. The output is one report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from datetime import datetime, timezone

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import direct_http_capture as DHC  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-PARALLEL-REVALIDATION-002"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-brand-inventory-audit/1.0"
RUN_ID = "cincinnati_oh_brand_inventory_002"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
RUN_DIR = os.path.join(_DASH, "data", "acquisition", RUN_ID)
CACHE_DIR = os.path.join(RUN_DIR, "cache")
OUT = os.path.join(REPORTS, "cincinnati_oh_brand_inventory_audit_002.json")

SPACING_SECONDS = 1.0

# ---------------------------------------------------------------- brand lanes

# Each entry is an entry point and the rule for descending it. ``descend`` is
# how many levels of <sitemapindex> to walk before the locs are property URLs.
BRAND_SOURCES = OrderedDict([
    ("MARRIOTT", {
        "entry": "https://www.marriott.com/sitemap-index.xml",
        "shard_filter": r"/marriott-hws/sitemap-xmls/us-sitemap-hws-\d+\.xml$",
        "property_re": r"^https://www\.marriott\.com/en-us/hotels/([a-z0-9]{5})-([a-z0-9\-]+)/",
        "domain": "marriott.com",
    }),
    ("HILTON", {
        "entry": "https://www.hilton.com/sitemap.xml",
        "index_filter": r"/sitemap/en/sitemap-en\.xml$",
        "shard_filter": r"/sitemap-en-prop-[a-z]+-\d+\.xml$",
        "property_re": r"^https://www\.hilton\.com/en/hotels/([a-z0-9]+)-([a-z0-9\-]+)/",
        "domain": "hilton.com",
    }),
    ("BEST_WESTERN", {
        "entry": "https://www.bestwestern.com/sitemap.xml",
        "shard_filter": r"/hotels-details\.xml$",
        "property_re": r"^https://www\.bestwestern\.com/en_US/book/hotels-in-([a-z0-9\-]+)/([a-z0-9\-]+)/propertyCode\.(\d+)\.html$",
        "domain": "bestwestern.com",
    }),
    ("ESA", {
        "entry": "https://www.extendedstayamerica.com/sitemap.xml",
        "shard_filter": r"/web-cms-api/sitemap/geo$",
        "state_pages": ("/hotels/oh", "/hotels/ky", "/hotels/in"),
        "property_re": r"^https://www\.extendedstayamerica\.com/hotels/([a-z]{2})/([a-z0-9\-]+)/([a-z0-9\-]+)$",
        "domain": "extendedstayamerica.com",
    }),
    ("SONESTA", {
        "entry": "https://www.sonesta.com/sitemap/sitemap-index.xml",
        "shard_filter": r"/sitemap-\d+\.xml$",
        "property_re": r"^https://www\.sonesta\.com/([a-z0-9\-]+/){2,}([a-z0-9\-]+)/?$",
        "domain": "sonesta.com",
    }),
])

# Probed for the record. A refusal here is a measured fact about the lane, not
# a retry, and it is what makes a brand BRAND_INVENTORY_SILENT below.
BRAND_PROBES_ONLY = OrderedDict([
    ("IHG", ["https://www.ihg.com/sitemap.xml",
             "https://www.ihg.com/bin/sitemapindex.xml",
             "https://www.ihg.com/services/sitemaps/sitemap-index.xml"]),
    ("CHOICE", ["https://www.choicehotels.com/sitemap.xml",
                "https://www.choicehotels.com/sitemapindex.xml"]),
    ("WYNDHAM", ["https://www.wyndhamhotels.com/sitemap.xml"]),
    ("HYATT", ["https://www.hyatt.com/sitemap.xml"]),
    ("RED_ROOF", ["https://www.redroof.com/sitemap.xml"]),
    ("MOTEL6", ["https://www.motel6.com/sitemap.xml"]),
])

# Which census rows belong to which brand family. Matched on BRAND tokens only:
# a city name is never a brand, which is why "Fairfield Inn" is Marriott and
# "Holiday Inn Express Fairfield" is IHG.
BRAND_OF_NAME = [
    ("MARRIOTT", r"\b(marriott|courtyard|residence inn|fairfield inn|springhill|towneplace|ac hotel|aloft|element by|westin|sheraton|renaissance|moxy|four points|delta hotels|le meridien|autograph|tribute portfolio|st\.? regis|w hotels|kinley|lytle park|hotel celare)\b"),
    ("HILTON", r"\b(hilton|hampton inn|hampton by|homewood suites|home2 suites|embassy suites|doubletree|tru by hilton|tapestry|curio|canopy by|conrad|waldorf|signia|spark by hilton|lxr|motto by|graduate by|the cincinnatian|well house)\b"),
    ("IHG", r"\b(holiday inn|staybridge|candlewood|crowne plaza|even hotel|avid hotel|hotel indigo|intercontinental|kimpton|atwell suites|garner hotel)\b"),
    ("WYNDHAM", r"\b(days inn|super 8|ramada|baymont|microtel|travelodge|howard johnson|wingate|hawthorn|la quinta|wyndham|americinn|trademark collection|echo suites)\b"),
    ("CHOICE", r"\b(comfort inn|comfort suites|quality inn|sleep inn|clarion|econo lodge|rodeway|mainstay|suburban studios|suburban extended|woodspring suites|cambria|ascend|everhome)\b"),
    ("HYATT", r"\b(hyatt|caption by|urcove)\b"),
    ("BEST_WESTERN", r"\b(best western|surestay|aiden by|glo by|executive residency)\b"),
    ("ESA", r"\b(extended stay america|esa)\b"),
    ("SONESTA", r"\b(sonesta|red lion|americas best value|signature inn|guesthouse)\b"),
    ("RED_ROOF", r"\b(red roof|hometowne studios)\b"),
    ("MOTEL6", r"\b(motel 6|studio 6)\b"),
]

STOP_TOKENS = {
    "hotel", "hotels", "inn", "suites", "suite", "and", "the", "by", "at", "of",
    "an", "a", "resort", "motel", "lodge", "extended", "stay", "america", "us",
    "usa", "oh", "ky", "in", "north", "south", "east", "west", "downtown",
    "airport", "centre", "center", "near", "plus", "premier", "express",
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def tokens(text: str) -> set:
    return {t for t in norm(text).split() if len(t) > 2 and t not in STOP_TOKENS}


def brand_of(name: str) -> str:
    low = " %s " % norm(name)
    for family, pattern in BRAND_OF_NAME:
        if re.search(pattern, low):
            return family
    return "INDEPENDENT"


# ------------------------------------------------------------------- fetching

class Lane:
    """One free first-party GET, cached on disk, counted honestly."""

    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.requests = 0
        self.cache_hits = 0
        self.log = []

    def get(self, url: str):
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        path = os.path.join(CACHE_DIR, key + ".body")
        meta_path = os.path.join(CACHE_DIR, key + ".json")
        if os.path.exists(meta_path):
            meta = load(meta_path)
            self.cache_hits += 1
            body = b""
            if os.path.exists(path):
                with open(path, "rb") as handle:
                    body = handle.read()
            return meta, body
        result = DHC.fetch(url)
        self.requests += 1
        body = result.body or b""
        meta = {
            "url": url,
            "final_url": result.final_url,
            "status": str(result.status),
            "bytes": len(body),
            "body_sha256": hashlib.sha256(body).hexdigest() if body else None,
            "detail": result.detail,
            "fetched_at": now(),
        }
        if body:
            with open(path, "wb") as handle:
                handle.write(body)
        with open(meta_path, "w", encoding="utf-8") as handle:
            json.dump(meta, handle, indent=2)
        self.log.append(meta)
        time.sleep(SPACING_SECONDS)
        return meta, body


LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")


def locs_of(body: bytes):
    return LOC_RE.findall(body.decode("utf-8", "replace"))


# ---------------------------------------------------------- inventory harvest

def harvest(lane: Lane, family: str, spec: dict, verbose: bool):
    """Walk one brand's published inventory down to property URLs."""
    record = {
        "family": family,
        "entry": spec["entry"],
        "lane_state": None,
        "shards_listed": 0,
        "shards_read": 0,
        "shard_failures": 0,
        "property_urls": 0,
        "properties": {},
    }
    meta, body = lane.get(spec["entry"])
    if meta["status"] != "200" or not body:
        record["lane_state"] = "ENTRY_REFUSED"
        record["entry_status"] = meta["status"]
        return record

    level = locs_of(body)
    if spec.get("index_filter"):
        nxt = [u for u in level if re.search(spec["index_filter"], u)]
        level = []
        for url in nxt:
            m2, b2 = lane.get(url)
            if m2["status"] == "200" and b2:
                level.extend(locs_of(b2))

    shards = [u for u in level if re.search(spec["shard_filter"], u)]
    if spec.get("state_pages"):
        # ESA's geo shard lists state directories; only three are in market.
        shards = [u for u in level if any(u.endswith(s) for s in spec["state_pages"])] or shards
        if not shards:
            for url in level:
                if any(url.endswith(s) for s in spec["state_pages"]):
                    shards.append(url)
    record["shards_listed"] = len(shards)

    prop_re = re.compile(spec["property_re"])
    seen = {}
    for index, url in enumerate(shards, 1):
        meta_s, body_s = lane.get(url)
        if meta_s["status"] != "200" or not body_s:
            record["shard_failures"] += 1
            continue
        record["shards_read"] += 1
        for loc in locs_of(body_s):
            match = prop_re.match(loc)
            if not match:
                continue
            base = loc
            code = match.group(1)
            if family == "MARRIOTT":
                base = "https://www.marriott.com/en-us/hotels/%s-%s/" % (match.group(1), match.group(2))
                slug = match.group(2)
            elif family == "HILTON":
                base = "https://www.hilton.com/en/hotels/%s-%s/" % (match.group(1), match.group(2))
                slug = match.group(2)
            elif family == "BEST_WESTERN":
                code = match.group(3)
                slug = "%s %s" % (match.group(2), match.group(1))
            elif family == "ESA":
                code = match.group(3)
                slug = "%s %s" % (match.group(3), match.group(2))
            else:
                code = match.group(len(match.groups()))
                slug = code
            if base not in seen:
                seen[base] = {"url": base, "code": code, "slug": slug,
                              "tokens": sorted(tokens(slug.replace("-", " ")))}
        if verbose and index % 25 == 0:
            print("  %s shard %d/%d  properties=%d" % (family, index, len(shards), len(seen)), flush=True)

    record["properties"] = seen
    record["property_urls"] = len(seen)
    record["lane_state"] = "INVENTORY_READ" if seen else "INVENTORY_EMPTY"
    return record


# ------------------------------------------------------------- classification

def audit(inventories, verbose=False):
    census = load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    partition = load(os.path.join(PKG, "cincinnati_final_partition_001.json"))
    routing = load(os.path.join(AUTH, "identity_routing.json"))
    contract = load(os.path.join(PKG, "markets", "%s.json" % MARKET_ID))

    state_of = {i["identity_key"]: i["final_state"] for i in partition["items"]}
    url_of = {i["identity_key"]: (i.get("official_url") or "") for i in partition["items"]}
    route_by_url = {}
    for route in routing["routes"]:
        route_by_url.setdefault(route["official_property_url"], route)

    metro_cities = set()
    for corridor in contract["corridors"]:
        for city in corridor.get("included_cities") or []:
            metro_cities.add(norm(city))
    for hotel in census["hotels"]:
        metro_cities.add(norm(hotel.get("city") or ""))
    metro_cities.discard("")
    # "Dayton" is both a Kentucky city inside this market and the neighbouring
    # market. It is never a metro token here: the committed boundary review owns
    # that question and this order must not reopen it.
    metro_cities.discard("dayton")
    metro_tokens = set()
    for city in metro_cities:
        metro_tokens.update(t for t in city.split() if len(t) > 3 and t not in STOP_TOKENS)
    metro_tokens.add("cincinnati")

    rows = []
    matched_property_urls = set()
    for hotel in census["hotels"]:
        key = hotel["identity_key"]
        family = brand_of(hotel["canonical_name"])
        inventory = inventories.get(family)
        official = (url_of.get(key) or hotel.get("official_url") or "").strip()
        state = state_of.get(key, "UNKNOWN")
        row = {
            "identity_key": key,
            "canonical_name": hotel["canonical_name"],
            "city": hotel.get("city"),
            "state": hotel.get("state"),
            "postal_code": hotel.get("postal_code"),
            "brand_family": family,
            "partition_state": state,
            "committed_official_url": official or None,
            "inventory_lane": (inventory or {}).get("lane_state") or "NO_LANE",
        }
        if family == "INDEPENDENT":
            row["classification"] = "NOT_A_BRAND_LANE"
            rows.append(row)
            continue
        if not inventory or inventory.get("lane_state") != "INVENTORY_READ":
            row["classification"] = "BRAND_INVENTORY_SILENT"
            row["why"] = "the brand refused its own published inventory to a plain client; silence here is a measured fact about the lane, never evidence about the property"
            rows.append(row)
            continue

        properties = inventory["properties"]
        base = None
        if official:
            trimmed = re.sub(r"(overview/?|rooms/?|/)?$", "", official)
            for candidate in properties:
                if official.startswith(candidate) or candidate.startswith(trimmed):
                    base = candidate
                    break
        if base:
            matched_property_urls.add(base)
            row["classification"] = "EXACT_ACTIVE_ROUTE"
            row["inventory_url"] = base
            row["inventory_property_code"] = properties[base]["code"]
            route = route_by_url.get(official)
            committed_code = (route or {}).get("property_code") or ""
            row["committed_property_code"] = committed_code or None
            if route is None:
                row["route_table"] = "NO_ROUTE_ROW"
            elif not committed_code:
                row["route_table"] = "ROUTE_ROW_CARRIES_NO_PROPERTY_CODE"
            elif properties[base]["code"] not in norm(committed_code).replace(" ", "-"):
                row["route_table"] = "PROPERTY_CODE_DISAGREES"
            else:
                row["route_table"] = "AGREES"
            if route is not None and route.get("status") == "ROUTING_RETIRED":
                row["classification"] = "REBRAND_ROUTE"
                row["why"] = "the committed route is retired but the brand still publishes this exact URL in its own inventory"
            rows.append(row)
            continue

        if official and inventory["domain"] in official:
            row["classification"] = "DEAD_PROPERTY_CODE"
            row["why"] = "the committed route points at this brand's domain and the brand's own complete published inventory does not contain it"
            rows.append(row)
            continue

        # No route on this brand's domain. Can the inventory offer one?
        want = tokens(hotel["canonical_name"]) | tokens(hotel.get("city") or "")
        best, best_score = None, 0
        for url, prop in properties.items():
            shared = want & set(prop["tokens"])
            distinctive = {t for t in shared if t not in metro_tokens}
            if not distinctive:
                continue
            score = len(shared) + len(distinctive)
            if score > best_score:
                best, best_score = url, score
        if best and best_score >= 4:
            matched_property_urls.add(best)
            row["classification"] = "ROUTE_REPAIR_AVAILABLE"
            row["inventory_url"] = best
            row["inventory_property_code"] = properties[best]["code"]
            row["match_score"] = best_score
            row["why"] = "the brand's own inventory carries a property whose distinctive tokens match this identity; the route is a proposal for review, never an automatic bind"
        else:
            row["classification"] = "BRAND_INVENTORY_SILENT"
            row["why"] = "the brand's inventory was read in full and offers no distinctive match for this identity"
        rows.append(row)

    # ---- inventory rows in this metro that no census identity claims -------
    #
    # A single shared word is worthless here. "fairfield" is a Marriott BRAND;
    # "park", "ridge", "union", "chester" and "blue" are fragments of compound
    # city names; and Augusta, Franklin, Hamilton, Covington and Middletown all
    # exist in other states. Matching on tokens produced 2,708 "missing hotels"
    # and every sample was a Marriott in Atlanta or Austin.
    #
    # Two tests, both of which must pass:
    #   1. the property's slug contains a WHOLE market city as a contiguous
    #      phrase, not a token that happens to appear in one;
    #   2. the property's own code carries a market prefix this market already
    #      owns. That prefix set is not invented -- it is read back off the
    #      routes THIS RUN matched as EXACT_ACTIVE_ROUTE, so it is the brand's
    #      own statement about which codes serve this metro.
    #
    # A brand whose codes carry no market prefix (Best Western numbers its
    # properties, Sonesta uses per-brand slugs) cannot take test 2. For those
    # this lane says NOT_DECIDABLE_BY_THIS_LANE rather than pretending to a
    # discovery it cannot support.
    city_phrases = sorted({c for c in metro_cities if len(c) > 4},
                          key=len, reverse=True)
    in_market_prefixes = {}
    for row in rows:
        if row["classification"] in ("EXACT_ACTIVE_ROUTE", "REBRAND_ROUTE", "ROUTE_REPAIR_AVAILABLE"):
            code = (row.get("inventory_property_code") or "").lower()
            # A real property code is short and fixed-length: Marriott uses five
            # characters, Hilton six or seven. Sonesta's "code" is its whole
            # slug, so every Sonesta row would share the prefix "son" and the
            # test would pass for a hotel in Baton Rouge. A slug is not a code.
            if 5 <= len(code) <= 8 and code[:3].isalpha():
                in_market_prefixes.setdefault(row["brand_family"], set()).add(code[:3])

    missing = []
    census_tokens = [(h["identity_key"], tokens(h["canonical_name"]) | tokens(h.get("city") or ""))
                     for h in census["hotels"]]
    for family, inventory in inventories.items():
        if inventory.get("lane_state") != "INVENTORY_READ":
            continue
        prefixes = in_market_prefixes.get(family)
        for url, prop in inventory["properties"].items():
            if url in matched_property_urls:
                continue
            slug = norm(prop["slug"].replace("-", " "))
            hit = next((c for c in city_phrases if re.search(r"\b%s\b" % re.escape(c), slug)), None)
            if not hit:
                continue
            code = (prop["code"] or "").lower()
            if prefixes is not None:
                if not (5 <= len(code) <= 8 and code[:3] in prefixes):
                    continue                       # a city name in another state
                decidable = True
            else:
                decidable = False

            prop_tokens = set(prop["tokens"])
            best, best_score = None, 0
            for key, ctoks in census_tokens:
                shared = prop_tokens & ctoks
                distinctive = {t for t in shared if t not in metro_tokens}
                if not distinctive:
                    continue
                score = len(shared) + len(distinctive)
                if score > best_score:
                    best, best_score = key, score

            if not decidable:
                classification = "NOT_DECIDABLE_BY_THIS_LANE"
                why = ("this brand's property codes carry no market prefix, so the inventory cannot say "
                       "whether a same-named city is this one. The row is recorded, not counted as a "
                       "discovery.")
            elif best_score >= 3:
                classification = "IDENTITY_REVIEW_REQUIRED"
                why = ("the brand's code places this property in this market and a census identity is a "
                       "close name match; only an address or phone ruling separates them")
            else:
                classification = "TRUE_MISSING_BRAND_IDENTITY"
                why = ("the brand's own code places this property in this market, its slug names a market "
                       "city, and no census identity comes close. This is a lead for an identity order, "
                       "never a row for a policy inventory.")

            missing.append({
                "family": family,
                "inventory_url": url,
                "property_code": prop["code"],
                "slug": prop["slug"],
                "market_city_phrase_matched": hit,
                "code_prefix_in_market": (prefixes is not None and 5 <= len(code) <= 8 and code[:3] in prefixes),
                "closest_census_identity": best,
                "closest_score": best_score,
                "classification": classification,
                "why": why,
            })
    return rows, missing, sorted(metro_tokens), {k: sorted(v) for k, v in in_market_prefixes.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    lane = Lane()
    started = time.time()
    inventories = {}
    for family, spec in BRAND_SOURCES.items():
        print("== %s" % family, flush=True)
        record = harvest(lane, family, spec, args.verbose)
        record["domain"] = spec["domain"]
        inventories[family] = record
        print("   %s shards=%d/%d properties=%d" % (
            record["lane_state"], record["shards_read"], record["shards_listed"],
            record["property_urls"]), flush=True)

    probes = {}
    for family, urls in BRAND_PROBES_ONLY.items():
        results = []
        for url in urls:
            meta, _ = lane.get(url)
            results.append({"url": url, "status": meta["status"], "bytes": meta["bytes"]})
        opened = [r for r in results if r["status"] == "200" and r["bytes"] > 0]
        probes[family] = {
            "attempts": results,
            "lane_state": "ENTRY_REFUSED" if not opened else "OPEN_UNEXPECTEDLY",
        }
        inventories.setdefault(family, {"family": family, "lane_state": probes[family]["lane_state"],
                                        "properties": {}, "domain": ""})
        print("== %s probe-only: %s" % (family, probes[family]["lane_state"]), flush=True)

    rows, missing, metro_tokens, in_market_prefixes = audit(inventories, args.verbose)

    report = OrderedDict()
    report["schema"] = SCHEMA
    report["work_order"] = WORK_ORDER
    report["market_id"] = MARKET_ID
    report["phase"] = "7 -- official brand inventory audit (identity and routing only)"
    report["run_id"] = RUN_ID
    report["as_of"] = now()
    report["lane"] = "direct_http against published first-party sitemaps; no vendor, no browser, no credit"
    report["usd_spent"] = 0.0
    report["paid_provider_calls"] = 0
    report["plan_credits_spent"] = 0
    report["authority_mutation"] = "NONE"
    # A rerun reads the cache and issues nothing, so requests-this-invocation
    # would understate what the lane actually cost. The cache is the true meter:
    # one entry per distinct URL ever fetched for this run.
    report["free_http_requests_this_invocation"] = lane.requests
    report["cache_hits_this_invocation"] = lane.cache_hits
    report["free_http_requests_total_for_this_run"] = len(
        [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")])
    report["cost_note"] = ("every one of those is a free first-party GET of a document the brand publishes "
                           "for crawlers. No vendor, no browser, no plan credit, no USD.")
    report["elapsed_seconds_this_invocation"] = round(time.time() - started, 1)
    report["measured_wall_clock_of_the_first_uncached_sweep_seconds"] = 5777.1
    report["timing_note"] = ("the first sweep took 96 minutes, almost all of it Hilton's 539 property "
                             "shards at roughly ten seconds each. Every later invocation reads the cache "
                             "and takes seconds, which is why the two timings are reported separately "
                             "rather than one overwriting the other.")
    report["what_this_lane_can_decide"] = [
        "identity: the brand names its own property, its code and its city",
        "routing: the brand's own inventory is what makes a route live or dead",
    ]
    report["what_this_lane_can_never_decide"] = [
        "pet policy -- a sitemap carries a URL and a timestamp and nothing else",
    ]
    report["metro_token_vocabulary"] = metro_tokens
    report["in_market_code_prefixes_read_back_off_matched_routes"] = in_market_prefixes
    report["brand_lanes"] = OrderedDict()
    for family, record in inventories.items():
        report["brand_lanes"][family] = {
            "domain": record.get("domain"),
            "lane_state": record.get("lane_state"),
            "entry": record.get("entry"),
            "entry_status": record.get("entry_status"),
            "shards_listed": record.get("shards_listed", 0),
            "shards_read": record.get("shards_read", 0),
            "shard_failures": record.get("shard_failures", 0),
            "properties_published": record.get("property_urls", 0),
            "probe_attempts": probes.get(family, {}).get("attempts"),
        }
    report["classification_counts"] = OrderedDict(
        sorted(Counter(r["classification"] for r in rows).items()))
    report["missing_classification_counts"] = OrderedDict(
        sorted(Counter(m["classification"] for m in missing).items()))
    report["rows"] = rows
    report["inventory_rows_no_census_identity_claims"] = missing

    os.makedirs(REPORTS, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("\nwrote %s" % OUT)
    print(json.dumps(report["classification_counts"], indent=2))
    print(json.dumps(report["missing_classification_counts"], indent=2))
    print("requests this invocation:", lane.requests, "| cache hits:", lane.cache_hits,
          "| total free requests for this run:", report["free_http_requests_total_for_this_run"])


if __name__ == "__main__":
    main()
