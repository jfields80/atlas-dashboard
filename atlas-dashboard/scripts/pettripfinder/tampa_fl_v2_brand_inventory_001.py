"""PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 -- Phases 8 + 9C: owned national inventory, then the brands' own
inventories (cloned in shape from the Orlando FL V2 helper, Tampa Bay localities and Florida surfaces).

WHAT THIS IS
------------
Rung 0 and rung 2 of the acquisition ladder, run together because they answer the same question -- WHICH
PROPERTIES EXIST, and at WHAT OFFICIAL ROUTE -- and because rung 0 must be exhausted before a new request.

  rung 0  OWNED.  The committed national brand directory harvest (``dayton_oh_brand_directory_harvest_001.json``)
          is a SHARED national inventory. Every TPA-coded or Tampa-Bay-area Marriott route in it is already durable.
  rung 2  THE BRAND'S OWN INVENTORY PAGE, then its own sitemap. One plain HTTPS GET each, bounded per family:
            MARRIOTT  the brand's own Florida hotel sitemap page (MARSHA code, title, route)
            HILTON    the brand's own Florida city pages and every in-market interlink they publish (each page
                      carries the twenty nearest properties with the brand's own structured address card)
            WYNDHAM / DRURY / LOEWS / ESA / SONESTA / INTOWN / WOODSPRING  the brand's own sitemap
            CHOICE / IHG / BEST WESTERN / RED ROOF / MOTEL 6 / HYATT / OMNI / FOUR SEASONS / RADISSON / STAYABLE
                      re-probed at their sitemap; what THIS client saw is recorded

A ROSTER ROW IS NOT A POLICY, AND NOT AN ADMISSION
--------------------------------------------------
Everything here is ROUTING and IDENTITY evidence. No route carries or implies a pet policy, and no route admits a
property: the postal code the property's OWN page (or its DBPR licence) states does that. A route naming "Tampa"
is a LEAD: Tampa Bay-marketed hotels sit in St. Petersburg, Clearwater and the Gulf beaches, and some sit outside
the market entirely.

Outputs:
  launch_packages/pettripfinder/markets/reports/tampa_fl_v2_brand_inventory_001.json
  data/acquisition/tampa_fl_v2_brand_001/<sha256>.bin   (documents as returned)
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

WORK_ORDER = "PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "tampa-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "tampa_fl_v2_brand_001")
OWNED = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
OUT = os.path.join(REPORTS, "tampa_fl_v2_brand_inventory_001.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: Tampa Bay municipalities and the careful-evaluation neighbours, as a brand spells them in a URL.
LOCALITIES = (
    "tampa", "st-petersburg", "saint-petersburg", "clearwater", "clearwater-beach", "brandon", "ybor-city",
    "ybor", "westshore", "largo", "madeira-beach", "treasure-island", "st-pete-beach", "st-pete",
    "indian-rocks-beach", "dunedin", "tarpon-springs", "palm-harbor", "oldsmar", "safety-harbor", "seminole",
    "pinellas-park", "gulfport", "wesley-chapel", "new-tampa", "riverview", "apollo-beach", "ruskin",
    "plant-city", "temple-terrace", "town-n-country", "rocky-point", "belleair",
)
#: Unambiguous Tampa Bay-area tokens that need no state marker.
UNIQUE_TOKENS = ("tampa", "st-petersburg", "saint-petersburg", "clearwater-beach", "ybor-city", "westshore-tampa",
                 "madeira-beach", "st-pete-beach", "indian-rocks-beach", "tarpon-springs", "safety-harbor",
                 "wesley-chapel", "temple-terrace", "rocky-point")
FL_MARKERS = ("florida", "-fl-", "-fl/", "_fl", "-fl.", "/fl/", "-fl_", "/florida/")
NEGATIVE = ("tampa-ok", "oklahoma", "iowa", "minnesota", "colorado", "north-carolina", "maine", "new-jersey",
            "-ia-", "-mn-", "-co-", "-nc-", "/ia/", "/mn/", "/co/", "/nc/", "texas", "kentucky", "tennessee",
            "clearwater-ks", "kansas", "brandon-ms", "mississippi", "brandon-canada", "manitoba")
CAP_PER_FAMILY = 150

HILTON_SEEDS = [
    "florida/tampa", "florida/st-petersburg", "florida/clearwater", "florida/clearwater-beach",
    "florida/brandon", "florida/largo", "florida/temple-terrace", "florida/oldsmar", "florida/palm-harbor",
    "florida/safety-harbor", "florida/dunedin", "florida/tarpon-springs", "florida/wesley-chapel",
    "florida/riverview", "florida/apollo-beach", "florida/plant-city", "florida/madeira-beach",
    "florida/treasure-island", "florida/st-pete-beach", "florida/indian-rocks-beach", "florida/seminole",
    "florida/pinellas-park",
]


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


def persist(body):
    if not body:
        return None
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, digest + ".bin")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(body)
    return digest


def fetch(url, stats, timeout=30):
    row = OrderedDict([("url", url), ("status", None), ("final_url", None), ("bytes", 0), ("sha256", None),
                       ("error", None), ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))])
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate"})
    stats.requests += 1
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = _decode(resp, resp.read())
            if body[:2] == b"\x1f\x8b":
                try:
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                except Exception:
                    pass
            row.update(status=resp.getcode(), final_url=resp.geturl(), bytes=len(body), sha256=persist(body))
            stats.bytes += len(body)
            return row, body
    except urllib.error.HTTPError as exc:
        row["status"], row["final_url"] = exc.code, url
        return row, b""
    except Exception as exc:
        row["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])
        return row, b""


_TPA_CODE = re.compile(r"/hotels/tpa[a-z0-9]{2}-", re.I)


def is_lead(url):
    u = url.lower()
    if _TPA_CODE.search(u):
        return True
    if any(n in u for n in NEGATIVE):
        return False
    if any(t in u for t in UNIQUE_TOKENS):
        return True
    return any(t in u for t in LOCALITIES) and any(m in u for m in FL_MARKERS)


# --------------------------------------------------------------------------- rung 0
def owned_leads():
    if not os.path.exists(OWNED):
        return [], {"present": False}
    doc = json.load(open(OWNED, encoding="utf-8"))
    out, seen = [], set()
    for cand in doc.get("candidates", []):
        url = cand.get("url") or ""
        if not is_lead(url):
            continue
        key = url.lower()
        m = re.search(r"/hotels/([a-z0-9]{5})-", key)
        code = (m.group(1) if m else (cand.get("property_code") or "")).lower()
        canon = re.sub(r"^https?://[^/]+/[a-z-]{2,5}/hotels/", "", key).split("/overview")[0]
        ident = (cand.get("family"), code or canon)
        if ident in seen:
            continue
        seen.add(ident)
        route = url
        if "/en-us/" not in route and "/hotels/" in route:
            route = re.sub(r"/[a-z]{2}(-[a-z]{2})?/hotels/", "/en-us/hotels/", route, count=1)
        route = re.sub(r"(/overview/?).*$", "/overview/", route)
        out.append(OrderedDict([("family", cand.get("family")), ("route", route), ("property_code", code),
                                ("lane", "BRAND_INVENTORY_OWNED"),
                                ("owned_source", "dayton_oh_brand_directory_harvest_001.json"),
                                ("owned_as_of", doc.get("as_of"))]))
    return out, {"present": True, "as_of": doc.get("as_of"), "total_routes_in_corpus": len(doc.get("candidates", []))}


# --------------------------------------------------------------------------- MARRIOTT state sitemap
MARRIOTT_STATE_SITEMAP = "https://www.marriott.com/en-us/hotel-sitemap/usa-florida-hotel-sitemap"
_MARSHA = re.compile(r'\{"marsha":"([a-z0-9]{5})","title":"((?:[^"\\]|\\.)*)","url":"([^"]+)"\}', re.I)
_TITLE_PLACES = re.compile(r"\b(tampa|st\.? petersburg|saint petersburg|clearwater|ybor city|brandon|largo|"
                           r"madeira beach|treasure island|st\.? pete beach|indian rocks beach|dunedin|"
                           r"tarpon springs|palm harbor|oldsmar|safety harbor|seminole|pinellas park|gulfport|"
                           r"wesley chapel|riverview|apollo beach|ruskin|plant city|temple terrace|"
                           r"rocky point|westshore)\b", re.I)


def marriott_state_sitemap(stats):
    fam = OrderedDict([("lane", "BRAND_STATE_SITEMAP_PAGE"), ("url", MARRIOTT_STATE_SITEMAP), ("document", None),
                       ("properties_listed", 0), ("routes", [])])
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
        if not (code.startswith("tpa") or _TITLE_PLACES.search(title)):
            continue
        fam["routes"].append(OrderedDict([("family", "MARRIOTT"), ("route", url), ("property_code", code),
                                          ("brand_title", title), ("lane", "BRAND_STATE_SITEMAP_PAGE"),
                                          ("found_in", MARRIOTT_STATE_SITEMAP), ("found_in_sha256", row["sha256"])]))
    fam["disposition"] = ("STATE_SITEMAP_ANSWERED_THIS_CLIENT" if fam["routes"] else "STATE_SITEMAP_STATUS_%s" % row["status"])
    return fam


# --------------------------------------------------------------------------- HILTON city pages + interlinks
def hilton_page_hotels(text):
    """(hotels, interlinks) from a Hilton locations page's own __NEXT_DATA__."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not m:
        return [], []
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return [], []
    hotels, links = [], []
    for q in (data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries") or []):
        gp = ((q.get("state") or {}).get("data") or {}).get("geocodePage") or {}
        for block in ((gp.get("location") or {}).get("pageInterlinks") or []):
            for link in block.get("links") or []:
                if link.get("uri"):
                    links.append(link["uri"])
        for h in ((gp.get("hotelSummaryOptions") or {}).get("hotels") or []):
            addr = h.get("address") or {}
            coord = ((h.get("localization") or {}).get("coordinate") or {})
            hotels.append(OrderedDict([
                ("ctyhocn", (h.get("ctyhocn") or "").lower()), ("name", h.get("name")),
                ("route", ((h.get("facilityOverview") or {}).get("homeUrlTemplate") or "")),
                ("brand_code", h.get("brandCode")), ("street", addr.get("addressLine1")), ("city", addr.get("city")),
                ("state", addr.get("state")), ("postal_code", addr.get("postalCode")),
                ("phone", (h.get("contactInfo") or {}).get("phoneNumber")),
                ("lat", coord.get("latitude")), ("lng", coord.get("longitude")),
                ("open", (h.get("display") or {}).get("open")),
                ("open_date", (h.get("display") or {}).get("openDate")),
            ]))
    return hotels, links


_HILTON_IN_MARKET_LINK = re.compile(r"^locations/usa/florida/(%s)(/[a-z0-9-]+)?/?$" % "|".join(
    re.escape(s.split("/")[1]) for s in HILTON_SEEDS))


def hilton_city_pages(stats):
    fam = OrderedDict([("lane", "BRAND_CITY_PAGE"), ("request_cap", CAP_PER_FAMILY), ("pages", OrderedDict()),
                       ("routes", [])])
    queue = ["locations/usa/%s/" % s for s in HILTON_SEEDS]
    walked, seen = set(), set()
    spent = 0
    while queue and spent < CAP_PER_FAMILY:
        uri = queue.pop(0).strip("/") + "/"
        if uri in walked:
            continue
        walked.add(uri)
        url = "https://www.hilton.com/en/%s" % uri
        row, body = fetch(url, stats)
        spent += 1
        hotels, links = hilton_page_hotels(body.decode("utf-8", "replace"))
        row["hotels_on_page"] = len(hotels)
        new = 0
        for h in hotels:
            if not h["ctyhocn"] or h["ctyhocn"] in seen:
                continue
            seen.add(h["ctyhocn"])
            new += 1
            fam["routes"].append(OrderedDict([
                ("family", "HILTON"), ("route", h["route"] or "https://www.hilton.com/en/hotels/%s/" % h["ctyhocn"]),
                ("property_code", h["ctyhocn"]), ("lane", "BRAND_CITY_PAGE"), ("found_in", url),
                ("found_in_sha256", row["sha256"]), ("brand_card", h)]))
        row["new_hotels"] = new
        fam["pages"][uri] = row
        for link in links:
            lk = link.strip("/")
            if _HILTON_IN_MARKET_LINK.match(lk) and (lk + "/") not in walked:
                queue.append(lk)
    fam["requests_spent"] = spent
    fam["cap_reached"] = bool(queue) and spent >= CAP_PER_FAMILY
    fam["disposition"] = "CITY_PAGES_ANSWERED_THIS_CLIENT" if fam["routes"] else "CITY_PAGES_YIELDED_NOTHING"
    return fam


# --------------------------------------------------------------------------- sitemaps
SITEMAP_FAMILIES = OrderedDict([
    ("WYNDHAM", "https://www.wyndhamhotels.com/sitemap.xml"),
    ("DRURY", "https://www.druryhotels.com/sitemap.xml"),
    ("LOEWS", "https://www.loewshotels.com/sitemap.xml"),
    ("ESA", "https://www.extendedstayamerica.com/sitemap.xml"),
    ("SONESTA", "https://www.sonesta.com/sitemap/sitemap-index.xml"),
    ("INTOWN", "https://www.intownsuites.com/sitemap.xml"),
    ("WOODSPRING", "https://www.woodspring.com/sitemap.xml"),
    ("CHOICE", "https://www.choicehotels.com/sitemapindex.xml"),
    ("IHG", "https://www.ihg.com/services/sitemaps/sitemap-index.xml"),
    ("BEST_WESTERN", "https://www.bestwestern.com/sitemap.xml"),
    ("RED_ROOF", "https://www.redroof.com/sitemap.xml"),
    ("MOTEL6", "https://www.motel6.com/sitemap.xml"),
    ("HYATT", "https://www.hyatt.com/sitemap.xml"),
    ("OMNI", "https://www.omnihotels.com/sitemap.xml"),
    ("FOUR_SEASONS", "https://www.fourseasons.com/sitemap.xml"),
    ("RADISSON", "https://www.radissonhotels.com/sitemapindex.xml"),
    ("STAYABLE", "https://www.stayable.com/sitemap.xml"),
    ("HOMETOWNE", "https://www.hometownestudios.com/sitemap.xml"),
])
_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_CHILD_HINT = re.compile(r"hotel|propert|location|geo|main|sitemap-0|en[-_]us|america|north-america", re.I)
_CHILD_FIRST = re.compile(r"en[-_]us.*propert|propert.*en[-_]us|property-sitemap|/geo$", re.I)
_CHILD_SKIP = re.compile(r"_static|_interior|/(?!en-us)[a-z]{2}-[a-z]{2}/|sitemap_(?!en-us)[a-z]{2}-[a-z]{2}_|blog|article|news|"
                         r"rate-sitemap|travel-idea|post-sitemap|pointsofinterest", re.I)
#: A route that names ONE property, per family; everything else a sitemap lists (city indexes, locale
#: duplicates, rooms / meetings / dining sub-pages) is not a property route.
_PROPERTY_ROUTE = OrderedDict([
    ("WYNDHAM", re.compile(r"wyndhamhotels\.com/(?![a-z]{2}-[a-z]{2}/)[a-z0-9-]+/[a-z-]+-florida/[a-z0-9-]+/overview$", re.I)),
    ("DRURY", re.compile(r"druryhotels\.com/locations/[a-z-]+-fl/[a-z0-9-]+$", re.I)),
    ("LOEWS", re.compile(r"loewshotels\.com/[a-z0-9-]+/?$", re.I)),
    ("ESA", re.compile(r"extendedstayamerica\.com/hotels/fl/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("SONESTA", re.compile(r"sonesta\.com/[a-z0-9-]+/fl/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("INTOWN", re.compile(r"intownsuites\.com/extended-stay-locations/florida/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("WOODSPRING", re.compile(r"woodspring\.com/extended-stay-hotels/locations/florida/[a-z-]+/[a-z0-9-]+/?$", re.I)),
])


def sitemap_family(name, entry, stats):
    fam = OrderedDict([("lane", "BRAND_SITEMAP"), ("entry_sitemap", entry), ("request_cap", CAP_PER_FAMILY),
                       ("requests_spent", 0), ("cap_reached", False), ("documents", []), ("routes", []),
                       ("disposition", None)])
    queue, walked, seen = [entry], set(), set()
    prop_rx = _PROPERTY_ROUTE.get(name)
    while queue and fam["requests_spent"] < CAP_PER_FAMILY:
        url = queue.pop(0)
        if url in walked:
            continue
        walked.add(url)
        row, body = fetch(url, stats, timeout=45)
        fam["requests_spent"] += 1
        text = body.decode("utf-8", "replace")
        locs = _LOC.findall(text)
        hits = [u for u in locs if is_lead(u) and (prop_rx is None or prop_rx.search(u.rstrip("/") if name == "WYNDHAM" else u))]
        row["locs"], row["property_routes"] = len(locs), len(hits)
        children = 0
        if "<sitemapindex" in text.lower() or (name == "ESA" and "sitemap" in url and not hits and locs):
            picked = [c for c in locs if _CHILD_HINT.search(c) and c not in walked and not _CHILD_SKIP.search(c)]
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
            fam["routes"].append(OrderedDict([("family", name), ("route", u), ("property_code", ""),
                                              ("lane", "BRAND_SITEMAP"), ("found_in", url),
                                              ("found_in_sha256", row["sha256"])]))
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
        ("schema", "ptf-brand-inventory/1.0"), ("work_order", WORK_ORDER),
        ("phase", "8 + 9C -- owned national inventory, then the brand's own inventory page and sitemap"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("a_roster_row_is_not_a_policy",
         "Everything here is ROUTING and IDENTITY evidence. No route carries or implies a pet policy, and no route "
         "admits a property to this market -- the postal code the property's OWN page or DBPR licence states does that."),
        ("every_refusal_is_measured",
         "Each family was probed by THIS client at THIS moment. A refusal here is a fact about this request, never "
         "evidence that a family has no Tampa Bay-area property, and never inherited from an earlier order."),
        ("every_walk_is_bounded", "Each family carries a request cap of %d." % CAP_PER_FAMILY),
    ])
    owned, owned_meta = owned_leads()
    report["rung0_owned"] = OrderedDict([
        ("source", "launch_packages/pettripfinder/markets/reports/dayton_oh_brand_directory_harvest_001.json"),
        ("corpus", owned_meta), ("leads", len(owned)), ("by_family", dict(Counter(r["family"] for r in owned))),
        ("free_http_requests", 0)])
    families = OrderedDict()
    if not skip_network:
        families["MARRIOTT_STATE_SITEMAP"] = marriott_state_sitemap(stats)
        families["HILTON_CITY_PAGES"] = hilton_city_pages(stats)
        for name, entry in SITEMAP_FAMILIES.items():
            families[name] = sitemap_family(name, entry, stats)
            print("  %-14s %s routes=%d requests=%d" % (name, families[name]["disposition"], len(families[name]["routes"]),
                                                      families[name]["requests_spent"]), flush=True)
    routes = list(owned)
    for fam in families.values():
        routes.extend(fam.get("routes", []))
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
    report["dispositions"] = {k: v.get("disposition") for k, v in families.items() if v.get("disposition")}
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
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("owned leads      :", rep["rung0_owned"]["leads"], rep["rung0_owned"]["by_family"])
    print("free requests    :", rep["free_http_requests"])
    for k, v in rep.get("dispositions", {}).items():
        print("  %-24s %s" % (k, v))
    print("TOTAL LEADS      :", rep["lead_count"], rep["leads_by_family"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
