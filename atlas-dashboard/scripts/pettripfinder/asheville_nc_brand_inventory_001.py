"""PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001 -- Phase 3 + Phase 4: the free
brand-inventory lanes.

WHAT THIS IS
------------
Rung 0 and rung 2 of the acquisition ladder, run together because they answer
the same question -- WHICH PROPERTIES EXIST, and at WHAT OFFICIAL ROUTE -- and
because rung 0 must be exhausted before a single new request is made.

  rung 0  OWNED.  The committed national brand directory harvest
          (``dayton_oh_brand_directory_harvest_001.json``, 17,928 routes,
          as of 2026-09-02) is a SHARED national inventory. Every Asheville-area
          route in it is already paid for and already durable. Read, never
          refetched.
  rung 2  THE BRAND'S OWN CITY PAGE, then its own sitemap. One HTTPS GET each,
          from a plain client, bounded by a per-family request cap.

A ROSTER ROW IS NOT A POLICY, AND NOT AN ADMISSION
--------------------------------------------------
Everything here is ROUTING and IDENTITY evidence. No route in this file carries
or implies a pet policy. No route in this file admits a property to the Asheville market:
the postal code the property's OWN page states does that, joined to the
corridor registry. A Marriott route coded ``avl*`` or named ``...hendersonville...``
is a LEAD and nothing more until an address is read.

EVERY REFUSAL IS MEASURED, NOT INHERITED
----------------------------------------
Charlotte measured IHG, Best Western, Red Roof, Extended Stay, Hyatt and
Motel 6 as refusing a plain client one day before this run. This order re-probes
each of them anyway and records what THIS client saw at THIS moment, because a
refusal goes stale in days and an inherited refusal is an assumption.

Outputs:
  launch_packages/pettripfinder/markets/reports/asheville_nc_brand_inventory_001.json
  data/acquisition/asheville_nc_brand_001/<sha256>.bin   (documents as returned)
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

WORK_ORDER = "PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "asheville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "asheville_nc_brand_001")
OWNED = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
OUT = os.path.join(REPORTS, "asheville_nc_brand_inventory_001.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: Asheville-market municipalities (and the refused neighbours, so they are
#: CLASSIFIED rather than invisible) as Hilton spells them in a city-page path.
HILTON_CITIES = [
    "asheville", "arden", "fletcher", "candler", "weaverville", "swannanoa",
    "black-mountain", "woodfin", "hendersonville", "mills-river", "waynesville", "canton",
    "maggie-valley", "mars-hill", "lake-lure",
]

#: Locality tokens that make a route an Asheville-area LEAD. Deliberately wide --
#: it includes Hendersonville, Waynesville, Canton, Maggie Valley and Lake Lure so
#: those properties are CLASSIFIED rather than invisible. Admission still belongs
#: to the postal code the property's own page states.
LEAD_TOKENS = (
    "asheville", "biltmore", "arden", "fletcher", "candler", "weaverville", "swannanoa",
    "black-mountain", "blackmountain", "woodfin", "hendersonville", "flat-rock",
    "mills-river", "waynesville", "canton", "maggie-valley", "mars-hill", "lake-lure",
    "chimney-rock", "fairview", "leicester",
)
#: A token is a false positive outside North Carolina: Canton OH / MI / GA / MA,
#: Arden Hills MN, Fairview TN / PA, Biltmore in Phoenix. A route must also carry
#: a North Carolina marker, an "asheville" token, OR an AVL Marriott property code.
NC_MARKERS = ("north-carolina", "-nc-", "-nc/", "_nc", "-nc.", "/nc/", "asheville")
NEGATIVE = ("canton-oh", "canton-ohio", "canton-mi", "canton-ga", "canton-ma", "arden-hills",
            "biltmore-phoenix", "arizona-biltmore", "fairview-heights")
CAP_PER_FAMILY = 60


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


_AVL_CODE = re.compile(r"/hotels/avl[a-z0-9]{2}-", re.I)


def is_lead(url):
    u = url.lower()
    if _AVL_CODE.search(u):
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
# rung 2 -- HILTON's own city pages
# --------------------------------------------------------------------------
_HILTON_CODE = re.compile(r"/en/hotels/([a-z0-9]{6,8})-([a-z0-9-]+)/", re.I)


def hilton_city_pages(stats, report):
    fam = OrderedDict([("lane", "BRAND_CITY_PAGE"), ("request_cap", CAP_PER_FAMILY),
                       ("city_pages", OrderedDict()), ("routes", [])])
    seen = set()
    for city in HILTON_CITIES:
        if fam["request_cap"] <= 0:
            break
        url = "https://www.hilton.com/en/locations/usa/north-carolina/%s/" % city
        row, body = fetch(url, stats)
        fam["request_cap"] -= 1
        text = body.decode("utf-8", "replace")
        codes = OrderedDict()
        for code, slug in _HILTON_CODE.findall(text):
            codes.setdefault(code.lower(), slug.lower())
        row["codes_found"] = len(codes)
        fam["city_pages"][city] = row
        for code, slug in codes.items():
            if code in seen:
                continue
            seen.add(code)
            fam["routes"].append(OrderedDict([
                ("family", "HILTON"),
                ("route", "https://www.hilton.com/en/hotels/%s-%s/" % (code, slug)),
                ("property_code", code),
                ("lane", "BRAND_CITY_PAGE"),
                ("found_in", url),
                ("found_in_sha256", row["sha256"]),
                ("city_page_city", city),
            ]))
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
    ("CHOICE", ("https://www.choicehotels.com/sitemapindex.xml", None)),
    ("IHG", ("https://www.ihg.com/services/sitemaps/sitemap-index.xml", None)),
    ("BEST_WESTERN", ("https://www.bestwestern.com/sitemap.xml", None)),
    ("RED_ROOF", ("https://www.redroof.com/sitemap.xml", None)),
    ("MOTEL6", ("https://www.motel6.com/sitemap.xml", None)),
    ("EXTENDED_STAY", ("https://www.extendedstayamerica.com/sitemap.xml", None)),
    ("HYATT", ("https://www.hyatt.com/sitemap.xml", None)),
    ("RADISSON", ("https://www.radissonhotels.com/sitemapindex.xml", None)),
    ("OMNI", ("https://www.omnihotels.com/sitemap.xml", None)),
    ("HILTON", ("https://www.hilton.com/sitemap.xml", None)),
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
            # requests on static and interior shards of brands with no Asheville
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
         "Asheville property, and never inherited from an earlier order."),
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
    with open(args.out, "w", encoding="utf-8") as fh:
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
