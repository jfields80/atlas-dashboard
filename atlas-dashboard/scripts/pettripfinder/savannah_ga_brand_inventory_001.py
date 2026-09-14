"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- Phase 4 + Phase 5C: the free
brand-inventory lanes (cloned from the Boone - Blowing Rock NC helper, itself from Atlanta GA; Savannah tokens).

WHAT THIS IS
------------
Rung 0 and rung 2 of the acquisition ladder, run together because they answer
the same question -- WHICH PROPERTIES EXIST, and at WHAT OFFICIAL ROUTE -- and
because rung 0 must be exhausted before a single new request is made.

  rung 0  OWNED.  The committed national brand directory harvest
          (``dayton_oh_brand_directory_harvest_001.json``, 17,928 routes,
          as of 2026-09-02) is a SHARED national inventory. Every Savannah-area
          route in it is already paid for and already durable. Read, never
          refetched.
  rung 2  THE BRAND'S OWN CITY PAGE, then its own sitemap. One HTTPS GET each,
          from a plain client, bounded by a per-family request cap.

A ROSTER ROW IS NOT A POLICY, AND NOT AN ADMISSION
--------------------------------------------------
Everything here is ROUTING and IDENTITY evidence. No route in this file carries
or implies a pet policy. No route in this file admits a property to the Savannah market:
the postal code the property's OWN page states does that, joined to the
corridor registry. A route or title naming "Savannah" is a LEAD and nothing more
until an address is read: Pooler, Port Wentworth, Richmond Hill and Hardeeville SC
properties carry the same word, and Tybee Island properties are OUTSIDE this market.

EVERY REFUSAL IS MEASURED, NOT INHERITED
----------------------------------------
Charlotte measured IHG, Best Western, Red Roof, Extended Stay, Hyatt and
Motel 6 as refusing a plain client one day before this run. This order re-probes
each of them anyway and records what THIS client saw at THIS moment, because a
refusal goes stale in days and an inherited refusal is an assumption.

Outputs:
  launch_packages/pettripfinder/markets/reports/savannah_ga_brand_inventory_001.json
  data/acquisition/savannah_ga_brand_001/<sha256>.bin   (documents as returned)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zlib
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "savannah-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "savannah_ga_brand_001")
OWNED = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
OUT = os.path.join(REPORTS, "savannah_ga_brand_inventory_001.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: Savannah-area municipalities -- and the Tybee Island market, Effingham and Liberty
#: County neighbours, so those properties are CLASSIFIED rather than invisible -- as
#: Hilton spells them in a city-page path (state / city).
HILTON_CITIES = [
    "georgia/savannah", "georgia/pooler", "georgia/garden-city", "georgia/port-wentworth",
    "georgia/richmond-hill", "georgia/tybee-island", "georgia/thunderbolt", "georgia/wilmington-island",
    "georgia/rincon", "georgia/bloomingdale", "georgia/hinesville", "georgia/midway",
    "south-carolina/hardeeville", "south-carolina/bluffton",
]

#: A Hilton city page lists only the twenty properties nearest its centre, and
#: Savannah holds more than twenty. The brand's own attraction and amenity views of
#: the same city are each centred or filtered differently, so their union reaches
#: the properties a single city page leaves out. A view that does not exist answers
#: 404 and is recorded.
HILTON_SUBPAGES = [
    "georgia/savannah/pet-friendly", "georgia/savannah/extended-stay", "georgia/savannah/boutique",
    "georgia/savannah/luxury", "georgia/savannah/outdoor-pool", "georgia/savannah/indoor-pool",
    "georgia/savannah/in-room-kitchen", "georgia/savannah/ev-charging", "georgia/savannah/spa",
    "georgia/savannah/hotel-residences", "georgia/savannah/golf", "georgia/savannah/beach",
    "georgia/savannah/river-street", "georgia/savannah/savannah-historic-district",
    "georgia/savannah/savannah-hilton-head-international-airport-sav", "georgia/savannah/forsyth-park",
    "georgia/pooler/extended-stay", "georgia/pooler/pet-friendly", "georgia/richmond-hill/pet-friendly",
]

#: Locality tokens that make a route a Savannah-area LEAD. Deliberately wide.
#: Admission still belongs to the postal code the property's own page states.
LEAD_TOKENS = tuple(c.split("/")[1] for c in HILTON_CITIES) + (
    "tybee", "skidaway", "hutchinson-island", "historic-district", "river-street", "riverfront",
    "gateway", "georgetown-ga", "crossroads", "hunter-army", "effingham", "springfield-ga", "guyton",
    "pembroke-ga", "ellabell",
)
#: A token is a false positive outside Georgia: Savannah TN / MO / NY, Garden City NY /
#: KS / MI / ID / SC, Richmond Hill NY / ON, Midway everywhere, Springfield... A route
#: must also carry a Georgia marker or a SAV-market Marriott property code.
NC_MARKERS = ("georgia", "-ga-", "-ga/", "_ga", "-ga.", "/ga/", "-ga_")
NEGATIVE = ("savannah-tn", "tennessee", "savannah-mo", "missouri", "new-york", "richmond-hill-ny",
            "ontario", "canada", "garden-city-ny", "kansas", "michigan", "idaho", "south-carolina",
            "/sc/", "-sc-", "texas", "utah", "illinois", "kentucky", "ohio", "florida")
CAP_PER_FAMILY = 120


class Stats(object):
    def __init__(self):
        self.requests = 0
        self.bytes = 0


def _decode(resp, raw):
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    try:
        if "gzip" in enc:
            return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        if "deflate" in enc:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:
        return raw
    return raw


def fetch(url, stats, timeout=25):
    """One plain HTTPS GET. Returns a row that always records what happened."""
    row = OrderedDict([("url", url), ("status", None), ("final_url", None),
                       ("bytes", 0), ("sha256", None), ("error", None),
                       ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))])
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    })
    stats.requests += 1
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            body = _decode(resp, raw)
            if url.endswith(".gz") or (body[:2] == b"\x1f\x8b"):
                try:
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                except Exception:
                    pass
            row["status"] = resp.getcode()
            row["final_url"] = resp.geturl()
            row["bytes"] = len(body)
            row["sha256"] = persist(body)
            stats.bytes += len(body)
            return row, body
    except urllib.error.HTTPError as exc:
        row["status"] = exc.code
        row["final_url"] = url
        try:
            body = _decode(exc, exc.read())
            row["bytes"] = len(body)
            if body:
                row["sha256"] = persist(body)
        except Exception:
            body = b""
        return row, body
    except Exception as exc:
        row["error"] = "%s: %s" % (type(exc).__name__, exc)
        return row, b""


def persist(body):
    """The document itself, on disk, addressed by its own hash. Nashville's
    evidence-recovery order exists because a capture kept only a byte length."""
    if not body:
        return None
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, digest + ".bin")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(body)
    return digest


#: Marriott files the Savannah market (downtown, airport, Pooler, Richmond Hill) under the SAV
#: airport code; a SAV-coded route is a LEAD, never an admission.
_PGV_CODE = re.compile(r"/hotels/sav[a-z0-9]{2}-", re.I)


def is_lead(url):
    u = url.lower()
    if _PGV_CODE.search(u):
        return True
    if any(n in u for n in NEGATIVE):
        return False
    return any(t in u for t in LEAD_TOKENS) and any(m in u for m in NC_MARKERS)


# --------------------------------------------------------------------------
# rung 0 -- the owned national harvest
# --------------------------------------------------------------------------
def owned_leads():
    if not os.path.exists(OWNED):
        return [], {"present": False}
    doc = json.load(open(OWNED, encoding="utf-8"))
    out, seen = [], set()
    for cand in doc.get("candidates", []):
        url = cand.get("url") or ""
        if not is_lead(url):
            continue
        # one property, not one locale: collapse marriott's /en-xx/ variants
        key = url.lower()
        m = re.search(r"/hotels/([a-z0-9]{5})-", key)
        code = (m.group(1) if m else (cand.get("property_code") or "")).lower()
        canon = re.sub(r"^https?://[^/]+/[a-z-]{2,5}/hotels/", "", key)
        canon = canon.split("/overview")[0]
        ident = (cand.get("family"), code or canon)
        if ident in seen:
            continue
        seen.add(ident)
        # prefer the en-us spelling of the route
        route = url
        if "/en-us/" not in route and "/hotels/" in route:
            route = re.sub(r"/[a-z]{2}(-[a-z]{2})?/hotels/", "/en-us/hotels/", route, count=1)
        out.append(OrderedDict([
            ("family", cand.get("family")),
            ("route", route),
            ("property_code", code),
            ("lane", "BRAND_INVENTORY_OWNED"),
            ("owned_source", "dayton_oh_brand_directory_harvest_001.json"),
            ("owned_as_of", doc.get("as_of")),
        ]))
    return out, {"present": True, "as_of": doc.get("as_of"),
                 "total_routes_in_corpus": len(doc.get("candidates", []))}


# --------------------------------------------------------------------------
# rung 2 -- HILTON's own city pages (Georgia + the two observed South Carolina towns)
# --------------------------------------------------------------------------
_HILTON_CODE = re.compile(r"/en/hotels/([a-z0-9]{6,8})-([a-z0-9-]+)/", re.I)


def _jstr(m):
    return json.loads('"%s"' % m.group(1)) if m else ""


def hilton_cards(text):
    """code -> the brand's own card fields for each hotel a city page lists."""
    out = {}
    for m in re.finditer(r'"ctyhocn":"([A-Z0-9]+)"', text):
        seg = text[m.start():m.start() + 2500]
        nxt = seg.find('"ctyhocn"', 10)
        if nxt > 0:
            seg = seg[:nxt]
        code = m.group(1).lower()
        if code in out:
            continue
        addr = OrderedDict([
            ("name", _jstr(re.search(r'"name":"((?:[^"\\]|\\.)*)"', seg))),
            ("street", _jstr(re.search(r'"addressLine1":"((?:[^"\\]|\\.)*)"', seg))),
            ("city", _jstr(re.search(r'"city":"((?:[^"\\]|\\.)*)"', seg))),
            ("state", _jstr(re.search(r'"state":"((?:[^"\\]|\\.)*)"', seg))),
            ("postal_code", _jstr(re.search(r'"postalCode":"((?:[^"\\]|\\.)*)"', seg))),
            ("phone", _jstr(re.search(r'"phoneNumber":"((?:[^"\\]|\\.)*)"', seg))),
        ])
        lat = re.search(r'"latitude":(-?[0-9.]+)', seg)
        lng = re.search(r'"longitude":(-?[0-9.]+)', seg)
        addr["lat"] = float(lat.group(1)) if lat else None
        addr["lng"] = float(lng.group(1)) if lng else None
        if addr["street"]:
            out[code] = addr
    return out


def hilton_city_pages(stats, report):
    fam = OrderedDict([("lane", "BRAND_CITY_PAGE"), ("request_cap", CAP_PER_FAMILY),
                       ("city_pages", OrderedDict()), ("routes", [])])
    seen = set()
    for city in HILTON_CITIES + HILTON_SUBPAGES:
        if fam["request_cap"] <= 0:
            break
        url = "https://www.hilton.com/en/locations/usa/%s/" % city
        row, body = fetch(url, stats)
        fam["request_cap"] -= 1
        text = body.decode("utf-8", "replace")
        codes = OrderedDict()
        for code, slug in _HILTON_CODE.findall(text):
            codes.setdefault(code.lower(), slug.lower())
        row["codes_found"] = len(codes)
        fam["city_pages"][city] = row
        cards = hilton_cards(text)
        for code, slug in codes.items():
            if code in seen:
                continue
            seen.add(code)
            route = OrderedDict([
                ("family", "HILTON"),
                ("route", "https://www.hilton.com/en/hotels/%s-%s/" % (code, slug)),
                ("property_code", code),
                ("lane", "BRAND_CITY_PAGE"),
                ("found_in", url),
                ("found_in_sha256", row["sha256"]),
                ("city_page_city", city),
            ])
            if code in cards:
                # The brand's OWN structured card for the property (name, address,
                # phone, pin) as the city page serves it. Identity only: the
                # amenity list beside it (``petsAllowed``) is never read.
                route["brand_card"] = cards[code]
            fam["routes"].append(route)
    return fam


# --------------------------------------------------------------------------
# rung 2 -- MARRIOTT's own Georgia hotel sitemap page
# --------------------------------------------------------------------------
MARRIOTT_STATE_SITEMAP = "https://www.marriott.com/en-us/hotel-sitemap/usa-georgia-hotel-sitemap"
_MARSHA = re.compile(r'\{"marsha":"([a-z0-9]{5})","title":"((?:[^"\\]|\\.)*)","url":"([^"]+)"\}', re.I)


def marriott_state_sitemap(stats):
    """Every Georgia property Marriott's own HTML hotel sitemap lists, with
    its MARSHA code and the brand's own title. A lead is any property whose title
    names a Savannah-area locality (or whose MARSHA code is SAV-prefixed) -- admission still belongs
    to the page's own postal code."""
    fam = OrderedDict([("lane", "BRAND_STATE_SITEMAP_PAGE"), ("url", MARRIOTT_STATE_SITEMAP),
                       ("document", None), ("properties_listed", 0), ("routes", [])])
    row, body = fetch(MARRIOTT_STATE_SITEMAP, stats, timeout=60)
    fam["document"] = row
    text = body.decode("utf-8", "replace")
    seen = set()
    for code, title, url in _MARSHA.findall(text):
        code = code.lower()
        if code in seen:
            continue
        seen.add(code)
        fam["properties_listed"] += 1
        title = json.loads('"%s"' % title)
        tl = re.sub(r"[^a-z0-9]+", "-", title.lower())
        if not (code.startswith("sav") or any(t in ("-%s-" % tl) for t in ["-%s-" % x for x in LEAD_TOKENS])):
            continue
        fam["routes"].append(OrderedDict([
            ("family", "MARRIOTT"), ("route", url), ("property_code", code),
            ("brand_title", title), ("lane", "BRAND_STATE_SITEMAP_PAGE"),
            ("found_in", MARRIOTT_STATE_SITEMAP), ("found_in_sha256", row["sha256"]),
        ]))
    fam["disposition"] = ("STATE_SITEMAP_ANSWERED_THIS_CLIENT" if fam["routes"]
                          else "STATE_SITEMAP_STATUS_%s" % row["status"])
    return fam


# --------------------------------------------------------------------------
# rung 2 -- the families whose own sitemap answered a plain client
# --------------------------------------------------------------------------
SITEMAP_FAMILIES = OrderedDict([
    ("WYNDHAM", ("https://www.wyndhamhotels.com/sitemap.xml",
                 None)),
    ("SONESTA", ("https://www.sonesta.com/sitemap/sitemap-index.xml", None)),
    ("DRURY", ("https://www.druryhotels.com/sitemap.xml", None)),
    ("WOODSPRING", ("https://www.woodspring.com/sitemap.xml", None)),
    ("INTOWN", ("https://www.intownsuites.com/sitemap.xml", None)),
    ("LOEWS", ("https://www.loewshotels.com/sitemap.xml", None)),
    ("CHOICE", ("https://www.choicehotels.com/sitemapindex.xml", None)),
    ("IHG", ("https://www.ihg.com/services/sitemaps/sitemap-index.xml", None)),
    ("BEST_WESTERN", ("https://www.bestwestern.com/sitemap.xml", None)),
    ("RED_ROOF", ("https://www.redroof.com/sitemap.xml", None)),
    ("MOTEL6", ("https://www.motel6.com/sitemap.xml", None)),
    ("EXTENDED_STAY", ("https://www.extendedstayamerica.com/sitemap.xml", None)),
    ("HYATT", ("https://www.hyatt.com/sitemap.xml", None)),
    ("RADISSON", ("https://www.radissonhotels.com/sitemapindex.xml", None)),
    ("OMNI", ("https://www.omnihotels.com/sitemap.xml", None)),
    ("FOUR_SEASONS", ("https://www.fourseasons.com/sitemap.xml", None)),
])

_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
#: A child sitemap is only walked when its own URL suggests it can hold US
#: property routes -- a bounded walk, never the whole index.
_CHILD_HINT = re.compile(r"hotel|propert|location|us|en[-_]us|america|north-america", re.I)
_CHILD_FIRST = re.compile(r"en[-_]us.*propert|propert.*en[-_]us", re.I)
_CHILD_SKIP = re.compile(r"_static|_interior|/(?!en-us)[a-z]{2}-[a-z]{2}/|sitemap_(?!en-us)[a-z]{2}-[a-z]{2}_", re.I)


def sitemap_family(name, entry, stats):
    fam = OrderedDict([("lane", "BRAND_SITEMAP"), ("entry_sitemap", entry),
                       ("request_cap", CAP_PER_FAMILY), ("requests_spent", 0),
                       ("cap_reached", False), ("documents", []), ("routes", []),
                       ("disposition", None)])
    queue, walked, seen = [entry], set(), set()
    while queue and fam["requests_spent"] < CAP_PER_FAMILY:
        url = queue.pop(0)
        if url in walked:
            continue
        walked.add(url)
        row, body = fetch(url, stats)
        fam["requests_spent"] += 1
        text = body.decode("utf-8", "replace")
        locs = _LOC.findall(text)
        hits = [u for u in locs if is_lead(u)]
        row["locs"] = len(locs)
        row["property_routes"] = len(hits)
        children = 0
        if "<sitemapindex" in text.lower():
            # A bounded walk spends its cap on PROPERTY shards first. Wyndham's
            # index lists ~700 children, and a walk in index order spent all 26
            # requests on static and interior shards of brands with no market
            # property before it reached Super 8, Baymont or Microtel.
            picked = [c for c in locs if _CHILD_HINT.search(c) and c not in walked
                      and not _CHILD_SKIP.search(c)]
            picked.sort(key=lambda c: (0 if _CHILD_FIRST.search(c) else 1))
            for child in picked:
                queue.append(child)
                children += 1
        row["children_selected"] = children
        fam["documents"].append(row)
        for u in hits:
            if u in seen:
                continue
            seen.add(u)
            fam["routes"].append(OrderedDict([
                ("family", name), ("route", u), ("property_code", ""),
                ("lane", "BRAND_SITEMAP"), ("found_in", url),
                ("found_in_sha256", row["sha256"]),
            ]))
    fam["cap_reached"] = bool(queue) and fam["requests_spent"] >= CAP_PER_FAMILY
    first = fam["documents"][0] if fam["documents"] else {}
    st = first.get("status")
    if st == 200 and fam["routes"]:
        fam["disposition"] = "SITEMAP_ANSWERED_THIS_CLIENT"
    elif st == 200:
        fam["disposition"] = "SITEMAP_ANSWERED_BUT_NO_MARKET_ROUTE_IN_THE_WALKED_SET"
    elif st in (403, 401, 429):
        fam["disposition"] = "SITEMAP_REFUSED_TO_THIS_CLIENT__STATUS_%s" % st
    elif st == 404:
        fam["disposition"] = "SITEMAP_NOT_AT_THIS_PATH__STATUS_404"
    elif first.get("error"):
        fam["disposition"] = "SITEMAP_UNREACHABLE__%s" % first["error"].split(":")[0]
    else:
        fam["disposition"] = "SITEMAP_STATUS_%s" % st
    return fam


def build(skip_network=False):
    stats = Stats()
    report = OrderedDict([
        ("schema", "ptf-brand-inventory/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "3 + 4 -- owned national inventory, then the brand's own city page and sitemap"),
        ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("a_roster_row_is_not_a_policy",
         "Everything here is ROUTING and IDENTITY evidence. No route carries or "
         "implies a pet policy, and no route admits a property to this market -- "
         "the postal code the property's OWN page states does that."),
        ("every_refusal_is_measured",
         "Each family was probed by THIS client at THIS moment. A refusal here "
         "is a fact about this request, never evidence that a family has no "
         "Savannah-area property, and never inherited from an earlier order."),
        ("every_walk_is_bounded",
         "Each family carries a request cap of %d and the walk stops at it, "
         "recording whether the cap was reached with work outstanding." % CAP_PER_FAMILY),
    ])

    owned, owned_meta = owned_leads()
    report["rung0_owned"] = OrderedDict([
        ("source", "launch_packages/pettripfinder/markets/reports/dayton_oh_brand_directory_harvest_001.json"),
        ("corpus", owned_meta),
        ("leads", len(owned)),
        ("by_family", dict(Counter(r["family"] for r in owned))),
        ("free_http_requests", 0),
        ("why_it_counts",
         "A shared national brand inventory already committed to this "
         "repository. The benchmark measures the modern factory, and the "
         "modern factory reads what it already owns before it asks anyone."),
    ])

    families = OrderedDict()
    if not skip_network:
        families["MARRIOTT_STATE_SITEMAP"] = marriott_state_sitemap(stats)
        families["HILTON_CITY_PAGES"] = hilton_city_pages(stats, report)
        for name, (entry, _pat) in SITEMAP_FAMILIES.items():
            families[name] = sitemap_family(name, entry, stats)

    routes = list(owned)
    for fam in families.values():
        routes.extend(fam.get("routes", []))

    # one row per (family, route)
    dedup, seen = [], set()
    for r in routes:
        key = (r["family"], r["route"].rstrip("/").lower())
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    report["families"] = families
    report["free_http_requests"] = stats.requests
    report["bytes_read"] = stats.bytes
    report["dispositions"] = {k: v.get("disposition") for k, v in families.items()
                              if v.get("disposition")}
    report["leads"] = dedup
    report["lead_count"] = len(dedup)
    report["leads_by_family"] = dict(Counter(r["family"] for r in dedup))
    report["leads_by_lane"] = dict(Counter(r["lane"] for r in dedup))
    report["documents_persisted_at"] = os.path.relpath(DOCS, _DASH).replace("\\", "/")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--owned-only", action="store_true")
    args = ap.parse_args(argv)
    rep = build(skip_network=args.owned_only)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    print("owned leads      :", rep["rung0_owned"]["leads"], rep["rung0_owned"]["by_family"])
    print("free requests    :", rep["free_http_requests"])
    for k, v in rep.get("dispositions", {}).items():
        print("  %-16s %s" % (k, v))
    print("TOTAL LEADS      :", rep["lead_count"], rep["leads_by_family"])
    print("WROTE", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
