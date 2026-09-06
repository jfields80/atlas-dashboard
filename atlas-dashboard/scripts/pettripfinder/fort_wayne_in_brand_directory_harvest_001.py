"""PTF-FORT-WAYNE-IN-NEW-MARKET-001 -- Phase 4C/7 (official brand inventory lane).

Zero-cost FIRST-PARTY brand inventory for the Fort Wayne shadow census, taken
from the CHEAPEST rung of the ladder that each family actually answers.

WHY THIS IS NOT A SITEMAP WALK

The Dayton/Cleveland harness walks robots.txt -> sitemap index -> children for
every family. That harness was pointed at Fort Wayne first and measured, and the
measurement is the reason this module exists:

  MARRIOTT  75 sitemaps, 117,189 URLs, 17,556 property URLs -- about 4 minutes,
            to select NINE Fort Wayne properties.
  HILTON    sitemap-en.xml is an index of 984 brand-sharded children answering
            in ~10 s each. The harness caps at 200, so a full walk is neither
            affordable NOR complete: 75 minutes bought roughly a fifth of the
            inventory before the run was stopped.

Both families publish the same facts far more cheaply:

  RUNG 0  OWNED EVIDENCE. The committed Dayton harvest already contains
          Marriott's whole property-URL inventory (17,928 URLs across families).
          Fort Wayne's nine Marriott properties are a grep over a file this
          repository already owns, at zero requests. Re-walking Marriott to
          learn what we already committed is the definition of paying twice.
  RUNG 1  THE BRAND'S OWN LOCATION PAGE. Hilton publishes every Fort Wayne
          property on one city page: twelve FWA-coded properties in ONE request,
          against 984 sitemap children for the same answer.
  RUNG 2  SITEMAP, but only for a family with no cheaper rung and a small index.

A family that refuses a plain client is recorded with the status it actually
returned, probed on this run rather than inherited from Dayton's 2026-09-01
list. A refusal is a fact about a moment.

A PROPERTY CODE SELECTS, IT NEVER ADMITS. Marriott issues the FWA-prefixed code
``fwafw`` to the Fairfield Inn & Suites in WARSAW, Indiana, forty miles outside
this market, and Hilton's Indiana page carries IND-prefixed Indianapolis codes.
Every selected row is fetched and judged on the address its own page states.

Nothing here is policy evidence. ``pets_allowed_structured`` is captured where a
page publishes it, as a TARGETING HINT ONLY.

Outputs:
  launch_packages/pettripfinder/markets/reports/fort_wayne_in_brand_directory_harvest_001.json
  data/discovery/fort_wayne_in_brand_harvest_001/pages/<sha>.html   (gitignored cache)
"""
from __future__ import annotations

import argparse
import dataclasses
import glob
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
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402

WORK_ORDER = "PTF-FORT-WAYNE-IN-NEW-MARKET-001"
MARKET_ID = "fort-wayne-in"
SCHEMA = "ptf-brand-inventory-audit/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "fort_wayne_in_brand_harvest_001", "pages")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
SPACING_SECONDS = 1.5

#: This market's locality tokens as they appear in a URL slug.
CORE_LOCALITY_TOKENS = ("fort-wayne", "fortwayne", "ft-wayne", "ftwayne",
                        "fort_wayne", "new-haven", "newhaven")
#: Marriott and Hilton both key Fort Wayne off the FWA airport code.
CODE_PREFIX = "fwa"

# --------------------------------------------------------------------------- #
# RUNG 0 -- owned evidence
# --------------------------------------------------------------------------- #

#: Committed brand-directory harvests this repository already owns. Their
#: property-URL inventories are re-read rather than re-fetched.
OWNED_HARVESTS = (
    "dayton_oh_brand_directory_harvest_001.json",
    "cleveland_akron_canton_oh_brand_directory_harvest_003.json",
)

#: How a family's property code is read out of its URL. Scoped per family: a
#: raw code is never compared across families.
CODE_PATTERNS = {
    "MARRIOTT": r"marriott\.com/(?:[a-z-]+/)?hotels/([a-z0-9]{5,7})-",
    "HILTON": r"hilton\.com/en/hotels/([a-z0-9]{4,10})-",
}

# --------------------------------------------------------------------------- #
# RUNG 1 -- the brand's own location page
# --------------------------------------------------------------------------- #

LOCATION_PAGES = OrderedDict([
    ("HILTON", {"url": "https://www.hilton.com/en/locations/usa/indiana/fort-wayne/",
                "property_re": r"/en/hotels/([a-z0-9]{4,10})-[a-z0-9-]+/",
                "to_url": lambda code, html: _hilton_url(code, html)}),
])


def _hilton_url(code, html):
    m = re.search(r"(/en/hotels/%s-[a-z0-9-]+/)" % re.escape(code), html, re.I)
    return "https://www.hilton.com" + m.group(1) if m else ""


# --------------------------------------------------------------------------- #
# RUNG 2 -- sitemap, only where there is no cheaper rung
# --------------------------------------------------------------------------- #

SITEMAP_FAMILIES = OrderedDict([
    ("WYNDHAM", {"robots": "https://www.wyndhamhotels.com/robots.txt",
                 "property_re": r"wyndhamhotels\.com/[a-z0-9-]+/[a-z-]+-indiana/[^/]+/overview",
                 "child_filter": r"."}),
    ("DRURY", {"robots": "https://www.druryhotels.com/robots.txt",
               "property_re": r"druryhotels\.com/locations/[a-z-]+-in/[^/]+/?$",
               "child_filter": r"."}),
    ("SONESTA", {"robots": "https://www.sonesta.com/robots.txt",
                 "property_re": r"sonesta\.com/[a-z0-9-]+/in/[a-z-]+/[^/]+/?$",
                 "child_filter": r"."}),
    ("WOODSPRING", {"robots": "https://www.woodspring.com/robots.txt",
                    "property_re": r"woodspring\.com/[^\s]*(?:/indiana/|-in/)[^\s]*",
                    "child_filter": r"."}),
    ("MY_PLACE", {"robots": "https://www.myplacehotels.com/robots.txt",
                  "property_re": r"myplacehotels\.com/[^\s]*(?:/in/|indiana)[^\s]*",
                  "child_filter": r"."}),
    ("INTOWN", {"robots": "https://www.intownsuites.com/robots.txt",
                "property_re": r"intownsuites\.com/[^\s]*(?:indiana|/in/|-in-)[^\s]*",
                "child_filter": r"."}),
    ("MAGNUSON", {"robots": "https://www.magnusonhotels.com/robots.txt",
                  "property_re": r"magnusonhotels\.com/[a-z0-9-]+/?$",
                  "child_filter": r"."}),
])

#: Probed for a refusal status only, so the report states what each family
#: actually answered on this run instead of inheriting another market's list.
REFUSAL_PROBES = OrderedDict([
    ("IHG", "https://www.ihg.com/robots.txt"),
    ("CHOICE", "https://www.choicehotels.com/robots.txt"),
    ("BEST_WESTERN", "https://www.bestwestern.com/robots.txt"),
    ("ESA", "https://www.extendedstayamerica.com/robots.txt"),
    ("RED_ROOF", "https://www.redroof.com/robots.txt"),
    ("HYATT", "https://www.hyatt.com/robots.txt"),
    ("MOTEL6", "https://www.motel6.com/robots.txt"),
])

#: Sitemap children to fetch per family before giving up. Deliberately small:
#: a family whose index needs more than this has no affordable sitemap rung,
#: and the report says so rather than burning an hour proving it again.
MAX_SITEMAP_CHILDREN = 25


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip",
        "Accept-Language": "en-US,en;q=0.9"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                try:
                    data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
                except Exception:  # noqa: BLE001
                    pass
            return r.status, r.geturl(), data, round(time.time() - t0, 2)
    except urllib.error.HTTPError as e:
        return e.code, url, b"", round(time.time() - t0, 2)
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b"", round(time.time() - t0, 2)


def locality_hit(url):
    u = (url or "").lower()
    for tok in CORE_LOCALITY_TOKENS:
        if tok in u:
            return tok
    return ""


def code_hit(url, family):
    pattern = CODE_PATTERNS.get(family)
    if not pattern:
        return ""
    m = re.search(pattern, url or "", re.I)
    if not m:
        return ""
    code = m.group(1).lower()
    return code if code.startswith(CODE_PREFIX) else ""


def owned_rung(stats):
    """RUNG 0 -- Fort Wayne rows out of harvests this repository already owns."""
    found, scanned = [], []
    for name in OWNED_HARVESTS:
        path = os.path.join(REPORTS, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
        total = 0
        for family, harvest in (doc.get("families") or {}).items():
            for url in harvest.get("property_urls") or []:
                total += 1
                code = code_hit(url, family)
                token = locality_hit(url)
                if not code and not token:
                    continue
                found.append(OrderedDict([
                    ("family", family), ("url", url), ("property_code", code),
                    ("locality_token", token), ("rung", "OWNED_EVIDENCE"),
                    ("owned_from", name),
                ]))
        scanned.append(OrderedDict([("report", name), ("property_urls_scanned", total)]))
    return found, scanned


def location_rung(stats):
    """RUNG 1 -- the brand's own city page."""
    found, pages = [], OrderedDict()
    for family, spec in LOCATION_PAGES.items():
        time.sleep(SPACING_SECONDS)
        status, final, body, seconds = get(spec["url"])
        stats["requests"] += 1
        html = body.decode("utf-8", "replace") if body else ""
        codes = sorted({c.lower() for c in re.findall(spec["property_re"], html, re.I)})
        keep = [c for c in codes if c.startswith(CODE_PREFIX)]
        rejected = [c for c in codes if not c.startswith(CODE_PREFIX)]
        for code in keep:
            url = spec["to_url"](code, html)
            if url:
                found.append(OrderedDict([
                    ("family", family), ("url", url), ("property_code", code),
                    ("locality_token", locality_hit(url)),
                    ("rung", "BRAND_LOCATION_PAGE"), ("owned_from", ""),
                ]))
        pages[family] = OrderedDict([
            ("url", spec["url"]), ("status", status), ("seconds", seconds),
            ("codes_on_page", len(codes)),
            ("codes_selected_by_prefix", keep),
            ("codes_rejected_wrong_prefix", rejected),
        ])
        print("  location %s %s -> %d selected" % (family, status, len(keep)), flush=True)
    return found, pages


def _locs(xml):
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def sitemap_rung(stats):
    """RUNG 2 -- a bounded sitemap walk, for families with no cheaper rung."""
    found, families = [], OrderedDict()
    for family, spec in SITEMAP_FAMILIES.items():
        entry = OrderedDict([("robots", None), ("sitemaps_fetched", 0),
                             ("urls_seen", 0), ("property_urls", 0),
                             ("truncated_at_child_cap", False), ("notes", [])])
        time.sleep(SPACING_SECONDS)
        status, _, body, _ = get(spec["robots"])
        stats["requests"] += 1
        entry["robots"] = status
        if status != 200:
            entry["notes"].append("robots.txt refused a plain client; family not walked")
            families[family] = entry
            print("  sitemap %s robots %s -- refused" % (family, status), flush=True)
            continue
        text = body.decode("utf-8", "replace")
        sitemaps = re.findall(r"(?im)^sitemap:\s*(\S+)", text)
        base = spec["robots"].rsplit("/robots.txt", 1)[0]
        if not sitemaps:
            sitemaps = [base + "/sitemap.xml"]
        prop_re = re.compile(spec["property_re"], re.I)
        child_re = re.compile(spec["child_filter"], re.I)
        seen, queue, urls = set(), [(s, 0) for s in sitemaps[:5]], set()
        while queue and entry["sitemaps_fetched"] < MAX_SITEMAP_CHILDREN:
            sm, depth = queue.pop(0)
            if sm in seen:
                continue
            seen.add(sm)
            time.sleep(SPACING_SECONDS)
            st2, _, body2, _ = get(sm)
            stats["requests"] += 1
            entry["sitemaps_fetched"] += 1
            if st2 != 200 or not body2:
                entry["notes"].append("%s: %s" % (sm, st2))
                continue
            xml = body2.decode("utf-8", "replace")
            entries = _locs(xml)
            entry["urls_seen"] += len(entries)
            if "<sitemapindex" in xml:
                children = [c for c in entries
                            if (depth > 0 or child_re.search(c))
                            and not re.search(r"blog|news|offer|deal|image|video|press|career",
                                              c, re.I)]
                queue.extend((c, depth + 1) for c in children)
                continue
            for u in entries:
                if prop_re.search(u):
                    urls.add(u)
        if queue:
            entry["truncated_at_child_cap"] = True
            entry["notes"].append(
                "stopped at the %d-child cap with %d children still queued; this "
                "family has no affordable sitemap rung" % (MAX_SITEMAP_CHILDREN, len(queue)))
        for u in sorted(urls):
            token = locality_hit(u)
            if not token:
                continue
            found.append(OrderedDict([
                ("family", family), ("url", u), ("property_code", ""),
                ("locality_token", token), ("rung", "BRAND_SITEMAP"), ("owned_from", ""),
            ]))
        entry["property_urls"] = len(urls)
        families[family] = entry
        print("  sitemap %s robots %s sitemaps %d urls %d" % (
            family, status, entry["sitemaps_fetched"], entry["urls_seen"]), flush=True)
    return found, families


def refusal_rung(stats):
    out = OrderedDict()
    for family, url in REFUSAL_PROBES.items():
        time.sleep(SPACING_SECONDS)
        status, _, _, seconds = get(url, timeout=20)
        stats["requests"] += 1
        out[family] = OrderedDict([
            ("robots_url", url), ("status", status), ("seconds", seconds),
            ("probed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            ("note", "measured on this run, not inherited"),
        ])
        print("  refusal probe %s -> %s" % (family, status), flush=True)
    return out


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


_IDENTITY_FIELDS = ("name_on_page", "address_on_page", "postal_code",
                    "phone_on_page", "property_code_on_page", "canonical_url",
                    "pets_allowed_structured", "jsonld_present", "phones_on_page")


def read_page_identity(url, family, stats):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    path = os.path.join(CACHE, key + ".html")
    meta_path = os.path.join(CACHE, key + ".json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
    else:
        time.sleep(SPACING_SECONDS)
        status, final, body, seconds = get(url)
        stats["requests"] += 1
        meta = {"url": url, "status": status, "final_url": final,
                "bytes": len(body), "seconds": seconds,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if body:
            with open(path, "wb") as fh:
                fh.write(body)
        json.dump(meta, open(meta_path, "w", encoding="utf-8"))
    rec = OrderedDict([("url", url), ("family", family), ("status", meta["status"]),
                       ("final_url", meta.get("final_url")), ("bytes", meta.get("bytes")),
                       ("page_sha256", None)])
    if meta["status"] == 200 and os.path.exists(path):
        html_b = open(path, "rb").read()
        rec["page_sha256"] = hashlib.sha256(html_b).hexdigest()
        html = html_b.decode("utf-8", "replace")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = " ".join(m.group(1).split()) if m else ""
        rec["title"] = title[:160]
        try:
            sig = as_plain(PS.read_identity(html, final_url=meta.get("final_url") or url,
                                            title=title, brand=family))
            rec["identity"] = OrderedDict(
                [(k, sig.get(k)) for k in _IDENTITY_FIELDS if k in sig])
        except Exception as exc:  # noqa: BLE001
            rec["identity_error"] = repr(exc)
        rec["soft_404_suspected"] = bool(re.search(
            r"<title[^>]*>\s*(search results|hotels? in|find hotels)", html, re.I))
    return rec


def build(args):
    stats = {"requests": 0}
    print("rung 0: owned evidence", flush=True)
    owned, owned_scanned = owned_rung(stats)
    print("   owned Fort Wayne rows:", len(owned), flush=True)
    print("rung 1: brand location pages", flush=True)
    located, location_pages = location_rung(stats)
    print("rung 2: bounded sitemaps", flush=True)
    mapped, sitemap_families = sitemap_rung(stats)
    print("refusal probes", flush=True)
    refusals = refusal_rung(stats)

    # One candidate per URL; the cheapest rung that found it wins.
    candidates = OrderedDict()
    for row in owned + located + mapped:
        candidates.setdefault(row["url"], row)
    candidates = list(candidates.values())
    if args.max_pages:
        candidates = candidates[: args.max_pages]
    print("candidates", len(candidates), "-- fetching each once", flush=True)

    pages = []
    for i, c in enumerate(candidates):
        c["page"] = read_page_identity(c["url"], c["family"], stats)
        pages.append(c["page"])
        if (i + 1) % 10 == 0:
            print("  fetched", i + 1, "of", len(candidates),
                  "requests", stats["requests"], flush=True)

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4C/7 -- new-market shadow census, official brand inventory lane"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("what_this_is",
         "Official brand inventory for Fort Wayne, taken from the cheapest rung each "
         "family answers: owned committed harvests first (zero requests), then the "
         "brand's own city page, then a bounded sitemap walk. A property code SELECTS "
         "but never ADMITS -- Marriott issues fwafw to Warsaw, Indiana, outside this "
         "market -- so every selected row is fetched and judged on the address its own "
         "page states. Identity and routing evidence only; never policy evidence."),
        ("why_not_a_full_sitemap_walk",
         "Measured on this order: Marriott's walk cost 75 sitemaps and 117,189 URLs to "
         "select 9 properties this repository already owned, and Hilton's sitemap-en "
         "index has 984 brand-sharded children answering in ~10 s each -- 75 minutes "
         "bought about a fifth of it before the walk was stopped. Hilton's own Fort "
         "Wayne city page returns all 12 of its properties in ONE request."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("owned_reports_scanned", owned_scanned),
        ("location_pages", location_pages),
        ("sitemap_families", sitemap_families),
        ("refused_families", refusals),
        ("candidate_counts", OrderedDict([
            ("total", len(candidates)),
            ("by_family", OrderedDict(sorted(Counter(c["family"] for c in candidates).items()))),
            ("by_rung", OrderedDict(sorted(Counter(c["rung"] for c in candidates).items()))),
            ("pages_fetched", len(pages)),
            ("page_status", OrderedDict(sorted(Counter(str(p["status"]) for p in pages).items()))),
            ("with_identity_name",
             sum(1 for p in pages if (p.get("identity") or {}).get("name_on_page"))),
        ])),
        ("candidates", candidates),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "fort_wayne_in_brand_directory_harvest_001.json"))
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["candidate_counts"]))
    print("free requests", rep["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
