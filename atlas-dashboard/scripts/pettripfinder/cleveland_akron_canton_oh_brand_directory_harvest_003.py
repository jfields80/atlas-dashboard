"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phase 3 (brand lane).

Zero-cost FIRST-PARTY brand-directory harvest for the Cleveland-Akron-Canton
shadow recensus. For every hotel family whose public sitemap answers a plain
client, walk robots.txt -> sitemap index -> children, keep the property URLs
whose path names this market (Marriott/Hilton by the CLE/CAK property-code
prefix, everybody else by an Ohio state token plus a market locality token),
then fetch each candidate property page ONCE to read the property's OWN
name / street / postal / telephone from its structured data.

Directory names and URLs are DISCOVERY LEADS ONLY -- never policy evidence.
Families that refuse a plain client (403 / timeout) are recorded as refusals
and are not retried. No paid provider is called.

Outputs:
  launch_packages/pettripfinder/markets/reports/<market>_brand_directory_harvest_003.json
  data/discovery/<market>_brand_harvest_003/pages/<sha>.html   (gitignored cache)
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
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-brand-directory-harvest/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", f"{MARKET_ID.replace('-', '_')}_brand_harvest_003", "pages")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
SPACING_SECONDS = 1.5

CORE_LOCALITY_TOKENS = [
    "cleveland", "akron", "canton", "beachwood", "independence", "westlake", "mentor", "willoughby", "eastlake",
    "solon", "twinsburg", "macedonia", "northfield", "richfield", "brecksville", "hudson", "aurora", "streetsboro",
    "kent", "fairlawn", "copley", "cuyahoga", "stow", "uniontown", "barberton", "massillon", "alliance",
    "hartville", "middleburg", "brook-park", "brookpark", "lakewood", "rocky-river", "north-olmsted", "mayfield",
    "lyndhurst", "warrensville", "seven-hills", "parma", "orange-village", "highland-heights", "wickliffe",
    "painesville", "peninsula", "green", "montrose", "belden", "north-canton", "east-canton", "wadsworth",
    "medina", "brunswick", "strongsville", "avon", "elyria", "lorain", "oberlin", "geneva", "chardon",
    "north-ridgeville", "sheffield", "amherst", "sandusky",
]
# Families whose URLs carry a brand property code with an airport-code prefix.
CODE_PREFIXES = ("cle", "cak", "akr")

FAMILIES = OrderedDict([
    ("MARRIOTT", {"robots": "https://www.marriott.com/robots.txt", "property_re": r"marriott\.com/(?:[a-z-]+/)?hotels/(%s)[a-z0-9]{2}-[^/]+/overview" % "|".join(CODE_PREFIXES),
                  "child_filter": r"sitemap-hotel-sitemaps|sitemap-hws|hotel-sitemaps"}),
    ("HILTON", {"robots": "https://www.hilton.com/robots.txt", "property_re": r"hilton\.com/en/hotels/(%s)[a-z0-9]{1,6}-[^/]+/" % "|".join(CODE_PREFIXES),
                "child_filter": r"/sitemap/en/sitemap-en\.xml|sitemap-en-hotels|/en/.*hotel"}),
    ("WYNDHAM", {"robots": "https://www.wyndhamhotels.com/robots.txt", "property_re": r"wyndhamhotels\.com/[a-z0-9-]+/([a-z-]+)-ohio/[^/]+/overview",
                 "child_filter": r"."}),
    ("DRURY", {"robots": "https://www.druryhotels.com/robots.txt", "property_re": r"druryhotels\.com/locations/([a-z-]+)-oh/[^/]+/?$", "child_filter": r"."}),
    ("SONESTA", {"robots": "https://www.sonesta.com/robots.txt", "property_re": r"sonesta\.com/[a-z0-9-]+/oh/([a-z-]+)/[^/]+/?$", "child_filter": r"."}),
    ("MY_PLACE", {"robots": "https://www.myplacehotels.com/robots.txt", "property_re": r"myplacehotels\.com/[^\s]*(?:/oh/|ohio)[^\s]*", "child_filter": r"."}),
    ("MAGNUSON", {"robots": "https://www.magnusonhotels.com/robots.txt", "property_re": r"magnusonhotels\.com/([a-z0-9-]+)/?$", "child_filter": r"."}),
    ("INTOWN", {"robots": "https://www.intownsuites.com/robots.txt", "property_re": r"intownsuites\.com/[^\s]*(?:ohio|/oh/|-oh-)[^\s]*", "child_filter": r"."}),
    ("WOODSPRING", {"robots": "https://www.woodspring.com/robots.txt", "property_re": r"woodspring\.com/[^\s]*(?:/ohio/|-oh/)[^\s]*", "child_filter": r"."}),
])
REFUSED_FAMILIES = OrderedDict([
    ("IHG", "robots.txt 403 to a plain client (probe 2026-09-01)"), ("HYATT", "robots.txt 403 (Kasada) -- ADR forbids satisfying the interstitial"),
    ("BEST_WESTERN", "robots.txt 403"), ("ESA", "robots.txt 403"), ("RED_ROOF", "robots.txt 403"),
    ("CHOICE", "robots.txt connection timeout (20 s)"), ("MOTEL6", "robots.txt connection timeout"), ("RADISSON", "robots.txt connection timeout"),
])


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip", "Accept-Language": "en-US,en;q=0.9"})
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
    out = OrderedDict([("family", fam), ("robots", None), ("sitemaps_fetched", 0), ("children_fetched", 0), ("urls_seen", 0), ("property_urls", []), ("notes", [])])
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
            # The family-level child filter applies to the ROOT index only; a
            # nested index (e.g. Marriott's index of hotel sitemaps) is walked whole.
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


def locality_hit(url: str) -> str:
    u = url.lower()
    for tok in CORE_LOCALITY_TOKENS:
        if tok in u:
            return tok
    return ""


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
        meta = {"url": url, "status": st, "final_url": final, "bytes": len(body), "seconds": dt, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if body:
            with open(path, "wb") as fh:
                fh.write(body)
        json.dump(meta, open(meta_path, "w", encoding="utf-8"))
    rec = OrderedDict([("url", url), ("family", fam), ("status", meta["status"]), ("final_url", meta.get("final_url")), ("bytes", meta.get("bytes")), ("page_sha256", None)])
    if meta["status"] == 200 and os.path.exists(path):
        html_b = open(path, "rb").read()
        rec["page_sha256"] = hashlib.sha256(html_b).hexdigest()
        html = html_b.decode("utf-8", "replace")
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = " ".join(title_m.group(1).split()) if title_m else ""
        rec["title"] = title[:160]
        try:
            sig = as_plain(PS.read_identity(html, final_url=meta.get("final_url") or url, title=title, brand=fam))
            rec["identity"] = OrderedDict([(k, sig.get(k)) for k in ("name", "street", "street_address", "locality", "city", "region", "postal_code", "telephone", "phone", "property_code", "jsonld_present") if k in sig])
        except Exception as exc:  # noqa: BLE001
            rec["identity_error"] = repr(exc)
        soft = bool(re.search(r"<title[^>]*>\s*(search results|hotels? in|find hotels)", html, re.I))
        rec["soft_404_suspected"] = soft
    return rec


def build(args) -> OrderedDict:
    stats = {"requests": 0}
    families = OrderedDict()
    for fam, spec in FAMILIES.items():
        if args.families and fam not in args.families:
            continue
        print("harvesting", fam, flush=True)
        families[fam] = harvest_family(fam, spec, stats)
        print("  ", fam, "robots", families[fam]["robots"], "sitemaps", families[fam]["sitemaps_fetched"], "urls", families[fam]["urls_seen"], "property urls", len(families[fam]["property_urls"]), flush=True)

    candidates = []
    for fam, h in families.items():
        for u in h["property_urls"]:
            tok = locality_hit(u)
            coded = fam in ("MARRIOTT", "HILTON")
            candidates.append(OrderedDict([("family", fam), ("url", u), ("locality_token", tok), ("selected_by", "PROPERTY_CODE_PREFIX" if coded else ("LOCALITY_TOKEN" if tok else "STATE_TOKEN_ONLY"))]))
    to_fetch = [c for c in candidates if c["selected_by"] in ("PROPERTY_CODE_PREFIX", "LOCALITY_TOKEN")]
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

    status_counts = Counter(str(p["status"]) for p in pages)
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("phase", "3 -- hardened shadow recensus, first-party brand-directory lane"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("what_this_is", "First-party sitemap walk per hotel family, filtered to this market by property-code prefix (Marriott/Hilton: CLE/CAK/AKR) or by an Ohio state token plus a market locality token; each selected property page fetched once to read the property's own name/street/postal/telephone. Leads only; never policy evidence."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats["requests"]),
        ("refused_families", REFUSED_FAMILIES),
        ("families", families),
        ("candidate_counts", OrderedDict([("total", len(candidates)), ("by_family", OrderedDict(sorted(Counter(c["family"] for c in candidates).items()))),
                                          ("by_selection", OrderedDict(sorted(Counter(c["selected_by"] for c in candidates).items()))), ("pages_fetched", len(pages)),
                                          ("page_status", OrderedDict(sorted(status_counts.items())))])),
        ("candidates", candidates),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_brand_directory_harvest_003.json"))
    ap.add_argument("--families", nargs="*", default=None)
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args(argv)
    rep = build(args)
    if args.families and os.path.exists(args.out):
        # A family-scoped rerun MERGES into the standing report: the other
        # families' harvest and candidates are kept, this family's replaced.
        prior = json.load(open(args.out, encoding="utf-8"))
        fams = OrderedDict(prior.get("families", {}))
        fams.update(rep["families"])
        cands = [c for c in prior.get("candidates", []) if c["family"] not in args.families] + rep["candidates"]
        rep["families"] = fams
        rep["candidates"] = cands
        rep["free_http_requests"] = prior.get("free_http_requests", 0) + rep["free_http_requests"]
        pages = [c["page"] for c in cands if c.get("page")]
        rep["candidate_counts"] = OrderedDict([("total", len(cands)), ("by_family", OrderedDict(sorted(Counter(c["family"] for c in cands).items()))),
                                               ("by_selection", OrderedDict(sorted(Counter(c["selected_by"] for c in cands).items()))), ("pages_fetched", len(pages)),
                                               ("page_status", OrderedDict(sorted(Counter(str(p["status"]) for p in pages).items())))])
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["candidate_counts"]))
    print("free requests", rep["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
