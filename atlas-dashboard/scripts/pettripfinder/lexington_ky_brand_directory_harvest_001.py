"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phase 4C/7, the first-party brand lane.

Zero-cost FIRST-PARTY brand-directory harvest for the Lexington shadow census.
For every hotel family whose public sitemap answers a plain client, walk
robots.txt -> sitemap index -> children, keep the property URLs whose path names
this market, then fetch each candidate property page ONCE to read the
property's OWN name / street / postal / telephone from its structured data.

Two things differ from the Cleveland/Dayton harvests this is adapted from.

1. MARRIOTT IS NOT RE-WALKED. Rank 0 of the ladder is owned evidence, and
   `dayton_oh_brand_directory_harvest_001.json` already holds Marriott's FULL
   GLOBAL property sitemap (17,567 URLs / 10,228 distinct property codes,
   walked 2026-09-02). Re-fetching 75 sitemaps to rediscover a list this
   repository owns would be the double-buy the ladder exists to prevent, so
   the owned file is read from disk and its `lex*` slice is used directly.

2. THE `lex` PREFIX IS A REGION, NOT A CITY. Marriott's `lex*` codes include
   Corbin, Frankfort, Georgetown and Richmond -- separate destinations 15 to
   80 miles apart. This is the same trap Louisville hit with `lou*`/`ckv*`.
   So the prefix SELECTS a candidate and never admits one: admission is
   decided later, on the address the property's own page states.

Directory names and URLs are DISCOVERY LEADS ONLY -- never policy evidence.
Families that refuse a plain client (403 / timeout) are recorded as refusals.
No paid provider is called.
"""
from __future__ import annotations

import argparse
import dataclasses
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
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
MARKET_ID = "lexington-ky"
SCHEMA = "ptf-brand-directory-harvest/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "lexington_ky_brand_harvest_001", "pages")
OWNED_MARRIOTT = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
SPACING_SECONDS = 1.5

# Fayette-county-proper tokens plus the three fringe county seats this order
# MEASURES rather than assumes, plus the near-miss destinations that must be
# recognised in order to be thrown out rather than silently swept in.
CORE_LOCALITY_TOKENS = [
    "lexington", "fayette", "hamburg", "keeneland", "griffin-gate", "fritz-farm",
    "nicholasville-road", "man-o-war", "newtown", "winchester-road", "richmond-road",
]
FRINGE_LOCALITY_TOKENS = ["georgetown", "nicholasville", "versailles", "wilmore", "midway"]
NEAR_MISS_TOKENS = ["frankfort", "richmond", "winchester", "paris", "corbin", "berea", "mount-sterling"]

# Families whose URLs carry a brand property code with an airport-code prefix.
# LEX is Blue Grass Airport; the prefix spans the whole central-Kentucky region.
CODE_PREFIXES = ("lex",)

FAMILIES = OrderedDict([
    ("HILTON", {"robots": "https://www.hilton.com/robots.txt",
                "property_re": r"hilton\.com/en/hotels/(%s)[a-z0-9]{1,6}-[^/]+/" % "|".join(CODE_PREFIXES),
                "child_filter": r"/sitemap/en/sitemap-en\.xml|sitemap-en-hotels|/en/.*hotel"}),
    ("WYNDHAM", {"robots": "https://www.wyndhamhotels.com/robots.txt",
                 "property_re": r"wyndhamhotels\.com/[a-z0-9-]+/([a-z-]+)-kentucky/[^/]+/overview",
                 "child_filter": r"."}),
    ("DRURY", {"robots": "https://www.druryhotels.com/robots.txt",
               "property_re": r"druryhotels\.com/locations/([a-z-]+)-ky/[^/]+/?$", "child_filter": r"."}),
    ("SONESTA", {"robots": "https://www.sonesta.com/robots.txt",
                 "property_re": r"sonesta\.com/[a-z0-9-]+/ky/([a-z-]+)/[^/]+/?$", "child_filter": r"."}),
    ("MY_PLACE", {"robots": "https://www.myplacehotels.com/robots.txt",
                  "property_re": r"myplacehotels\.com/[^\s]*(?:/ky/|kentucky)[^\s]*", "child_filter": r"."}),
    ("MAGNUSON", {"robots": "https://www.magnusonhotels.com/robots.txt",
                  "property_re": r"magnusonhotels\.com/([a-z0-9-]+)/?$", "child_filter": r"."}),
    ("INTOWN", {"robots": "https://www.intownsuites.com/robots.txt",
                "property_re": r"intownsuites\.com/[^\s]*(?:kentucky|/ky/|-ky-)[^\s]*", "child_filter": r"."}),
    ("WOODSPRING", {"robots": "https://www.woodspring.com/robots.txt",
                    "property_re": r"woodspring\.com/[^\s]*(?:/kentucky/|-ky/)[^\s]*", "child_filter": r"."}),
])

# Probed fresh by this order, not inherited. Anything that answers moves out.
REFUSED_FAMILIES: "OrderedDict[str, str]" = OrderedDict()
PROBE_FAMILIES = OrderedDict([
    ("IHG", "https://www.ihg.com/robots.txt"),
    ("HYATT", "https://www.hyatt.com/robots.txt"),
    ("BEST_WESTERN", "https://www.bestwestern.com/robots.txt"),
    ("ESA", "https://www.extendedstayamerica.com/robots.txt"),
    ("RED_ROOF", "https://www.redroof.com/robots.txt"),
    ("CHOICE", "https://www.choicehotels.com/robots.txt"),
    ("MOTEL6", "https://www.motel6.com/robots.txt"),
    ("RADISSON", "https://www.radissonhotels.com/robots.txt"),
])


def get(url, timeout=25):
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


def locs(xml: str):
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def harvest_family(fam, spec, stats, max_children=200):
    out = OrderedDict([("family", fam), ("robots", None), ("sitemaps_fetched", 0),
                       ("children_fetched", 0), ("urls_seen", 0), ("property_urls", []), ("notes", [])])
    st, _, body, _ = get(spec["robots"])
    stats["requests"] += 1
    out["robots"] = st
    txt = body.decode("utf-8", "replace") if body else ""
    sms = re.findall(r"(?im)^sitemap:\s*(\S+)", txt)
    base = spec["robots"].rsplit("/robots.txt", 1)[0]
    if not sms:
        sms = [base + "/sitemap.xml", base + "/sitemap-index.xml", base + "/sitemap_index.xml"]
    prop_re = re.compile(spec["property_re"], re.I)
    child_re = re.compile(spec["child_filter"], re.I)
    seen = set()
    queue = [(sm, 0) for sm in sms[:10]]
    fetched = 0
    while queue and fetched < max_children:
        sm, depth = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        time.sleep(SPACING_SECONDS)
        st2, _, body2, _ = get(sm)
        stats["requests"] += 1
        fetched += 1
        out["sitemaps_fetched"] += 1
        if st2 != 200 or not body2:
            out["notes"].append(f"{sm}: {st2}")
            continue
        xml = body2.decode("utf-8", "replace")
        entries = locs(xml)
        out["urls_seen"] += len(entries)
        if "<sitemapindex" in xml:
            children = [c for c in entries if (depth > 0 or child_re.search(c))
                        and not re.search(r"blog|news|offer|deal|image|video|press|career|magazine", c, re.I)]
            out["children_fetched"] += len(children)
            queue.extend((c, depth + 1) for c in children[:max_children])
            continue
        for u in entries:
            if prop_re.search(u):
                out["property_urls"].append(u)
    out["property_urls"] = sorted(set(out["property_urls"]))
    return out


def owned_marriott_slice():
    """Rank-0 owned evidence: Marriott's global sitemap, already in this repo."""
    d = json.load(open(OWNED_MARRIOTT, encoding="utf-8"))
    urls = d["families"]["MARRIOTT"]["property_urls"]
    best = {}
    for u in urls:
        m = re.search(r"/hotels/([a-z0-9]{5})-([a-z0-9\-]+)/overview", u)
        if not m:
            continue
        code = m.group(1)
        if code not in best or "/en-us/" in u:
            best[code] = u
    keep = sorted(u for c, u in best.items() if c.startswith(CODE_PREFIXES))
    return OrderedDict([
        ("family", "MARRIOTT"),
        ("robots", "OWNED_EVIDENCE"),
        ("sitemaps_fetched", 0), ("children_fetched", 0),
        ("urls_seen", len(urls)),
        ("property_urls", keep),
        ("notes", [
            "NOT RE-WALKED. Read from launch_packages/pettripfinder/markets/reports/"
            "dayton_oh_brand_directory_harvest_001.json (PTF-DAYTON-OH-HARDENED-REVALIDATION-001, "
            "walked 2026-09-02): Marriott's FULL GLOBAL property sitemap, 17,567 URLs over 10,228 "
            "distinct property codes. Rank 0 of the acquisition ladder is owned evidence; re-fetching "
            "75 sitemaps to rediscover a list the repository already owns is a double buy. "
            "0 HTTP requests were spent on this family.",
            "The lex* slice is a SELECTION, not an admission: it demonstrably spans Corbin, "
            "Frankfort, Georgetown and Richmond as well as Lexington-Fayette.",
        ]),
    ])


def locality_hit(url: str):
    u = url.lower()
    for tok in CORE_LOCALITY_TOKENS:
        if tok in u:
            return tok, "CORE"
    for tok in FRINGE_LOCALITY_TOKENS:
        if tok in u:
            return tok, "FRINGE"
    for tok in NEAR_MISS_TOKENS:
        if tok in u:
            return tok, "NEAR_MISS"
    return "", ""


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


def read_page_identity(url, fam, stats):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    path = os.path.join(CACHE, key + ".html")
    meta_path = os.path.join(CACHE, key + ".json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
    else:
        time.sleep(SPACING_SECONDS)
        st, final, body, dt = get(url)
        stats["requests"] += 1
        meta = {"url": url, "status": st, "final_url": final, "bytes": len(body),
                "seconds": dt, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if body:
            with open(path, "wb") as fh:
                fh.write(body)
        json.dump(meta, open(meta_path, "w", encoding="utf-8"))
    rec = OrderedDict([("url", url), ("family", fam), ("status", meta["status"]),
                       ("final_url", meta.get("final_url")), ("bytes", meta.get("bytes")),
                       ("page_sha256", None)])
    if meta["status"] == 200 and os.path.exists(path):
        html_b = open(path, "rb").read()
        rec["page_sha256"] = hashlib.sha256(html_b).hexdigest()
        html = html_b.decode("utf-8", "replace")
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = " ".join(title_m.group(1).split()) if title_m else ""
        rec["title"] = title[:160]
        try:
            sig = as_plain(PS.read_identity(html, final_url=meta.get("final_url") or url,
                                            title=title, brand=fam))
            rec["identity"] = OrderedDict([
                (k, sig.get(k)) for k in
                ("name", "street", "street_address", "locality", "city", "region",
                 "postal_code", "telephone", "phone", "property_code", "jsonld_present")
                if k in sig])
        except Exception as exc:  # noqa: BLE001
            rec["identity_error"] = repr(exc)
        rec["soft_404_suspected"] = bool(
            re.search(r"<title[^>]*>\s*(search results|hotels? in|find hotels)", html, re.I))
    return rec


def build(args) -> OrderedDict:
    stats = {"requests": 0}
    families = OrderedDict()

    families["MARRIOTT"] = owned_marriott_slice()
    print("MARRIOTT (owned evidence, 0 requests): property urls",
          len(families["MARRIOTT"]["property_urls"]), flush=True)

    for fam, url in PROBE_FAMILIES.items():
        if args.families and fam not in args.families:
            continue
        st, _, _, _ = get(url)
        stats["requests"] += 1
        time.sleep(SPACING_SECONDS)
        if st != 200:
            REFUSED_FAMILIES[fam] = f"robots.txt {st} to a plain client (probe {args.as_of})"
            print("  probe", fam, "->", st, "REFUSED", flush=True)
        else:
            REFUSED_FAMILIES[fam] = f"robots.txt 200 on probe {args.as_of} -- NOT walked by this order"
            print("  probe", fam, "->", st, "answers (recorded, not walked)", flush=True)

    for fam, spec in FAMILIES.items():
        if args.families and fam not in args.families:
            continue
        print("harvesting", fam, flush=True)
        families[fam] = harvest_family(fam, spec, stats)
        h = families[fam]
        print("  ", fam, "robots", h["robots"], "sitemaps", h["sitemaps_fetched"],
              "urls", h["urls_seen"], "property urls", len(h["property_urls"]), flush=True)

    candidates = []
    for fam, h in families.items():
        for u in h["property_urls"]:
            tok, band = locality_hit(u)
            coded = fam in ("MARRIOTT", "HILTON")
            candidates.append(OrderedDict([
                ("family", fam), ("url", u), ("locality_token", tok), ("locality_band", band),
                ("selected_by", "PROPERTY_CODE_PREFIX" if coded
                 else ("LOCALITY_TOKEN" if tok else "STATE_TOKEN_ONLY")),
            ]))

    to_fetch = [c for c in candidates
                if c["selected_by"] in ("PROPERTY_CODE_PREFIX", "LOCALITY_TOKEN")]
    if args.max_pages:
        to_fetch = to_fetch[: args.max_pages]
    print("candidates", len(candidates), "fetching", len(to_fetch), flush=True)
    pages = []
    for i, c in enumerate(to_fetch):
        rec = read_page_identity(c["url"], c["family"], stats)
        c["page"] = rec
        pages.append(rec)
        if (i + 1) % 20 == 0:
            print("  fetched", i + 1, "requests", stats["requests"], flush=True)

    status_counts: "OrderedDict[str,int]" = OrderedDict()
    for p in pages:
        k = str(p["status"])
        status_counts[k] = status_counts.get(k, 0) + 1
    by_family: "OrderedDict[str,int]" = OrderedDict()
    by_selection: "OrderedDict[str,int]" = OrderedDict()
    for c in candidates:
        by_family[c["family"]] = by_family.get(c["family"], 0) + 1
        by_selection[c["selected_by"]] = by_selection.get(c["selected_by"], 0) + 1

    return OrderedDict([
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("phase", "4C/7 -- new-market shadow census, first-party brand-directory lane"),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("what_this_is",
         "First-party sitemap walk per hotel family, filtered to this market by brand "
         "property-code prefix (Marriott/Hilton: LEX) or by a Kentucky state token plus a "
         "market locality token; each selected property page fetched once to read the "
         "property's own name/street/postal/telephone. Leads only; never policy evidence. "
         "MARRIOTT was NOT re-walked: its global sitemap is owned evidence already in this "
         "repository and was read from disk for 0 requests."),
        ("marriott_lane", "OWNED_EVIDENCE -- dayton_oh_brand_directory_harvest_001.json"),
        ("prefix_is_not_an_admission",
         "The LEX property-code prefix is Blue Grass Airport's, and Marriott applies it across "
         "central Kentucky: the lex* slice provably contains Corbin, Frankfort, Georgetown and "
         "Richmond properties. A prefix SELECTS a candidate here and never admits one. Admission "
         "is decided downstream on the address the property's own page states."),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("refused_families", REFUSED_FAMILIES),
        ("families", families),
        ("candidate_counts", OrderedDict([
            ("total", len(candidates)),
            ("by_family", by_family),
            ("by_selection", by_selection),
            ("pages_fetched", len(pages)),
            ("page_status", status_counts),
        ])),
        ("candidates", candidates),
    ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--families", nargs="*", default=None)
    ap.add_argument("--max-pages", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    report = build(args)
    os.makedirs(REPORTS, exist_ok=True)
    out = args.out or os.path.join(REPORTS, "lexington_ky_brand_directory_harvest_001.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print("wrote", out, flush=True)
    print("free_http_requests", report["free_http_requests"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
