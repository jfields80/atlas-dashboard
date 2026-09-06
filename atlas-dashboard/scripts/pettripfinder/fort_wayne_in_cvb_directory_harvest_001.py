"""PTF-FORT-WAYNE-IN-NEW-MARKET-001 -- Phase 4D (official tourism directory lane).

Zero-cost harvest of the Visit Fort Wayne (Allen County CVB) lodging directory.

The CVB is an OFFICIAL local tourism authority, so its directory is a strong
IDENTITY lead: it names properties the OpenStreetMap sweep does not carry at all
(avid hotel Fort Wayne North, Spark by Hilton, Tru by Hilton, Best Western
Luxbury Inn, Fairbridge Inn & Suites, Hallmark Inn, Hoosier Inn, Regency Inn,
Three Rivers Motel and others). It is still ONLY a lead: nothing here is policy
evidence, and a CVB listing does not by itself admit a property to the census.

How the candidate set is chosen. The directory's own /hotels/ index renders its
listings client-side, so it enumerates nothing to a plain client. The site's
robots.txt (Allow: /, Crawl-delay: 2) publishes a sitemap of 848 /listing/ URLs
instead, and that is walked. A generous lodging-keyword filter over the listing
slug SELECTS what to fetch; it deliberately over-selects, because a slug is a
name and a name only PROPOSES an identity. What a row actually is gets decided
from the listing page's own structured data -- and the filter's false positives
(a restaurant inside the Hilton, a Starbucks, the war memorial coliseum, a park)
are exactly what the LODGING / NON_LODGING classification below is for.

Crawl-delay 2 is honoured.

Outputs:
  launch_packages/pettripfinder/markets/reports/fort_wayne_in_cvb_directory_harvest_001.json
  data/discovery/fort_wayne_in_cvb_harvest_001/pages/<sha>.html   (gitignored cache)
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
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-FORT-WAYNE-IN-NEW-MARKET-001"
MARKET_ID = "fort-wayne-in"
SCHEMA = "ptf-cvb-directory-harvest/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "fort_wayne_in_cvb_harvest_001", "pages")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
SITEMAP = "https://www.visitfortwayne.com/sitemap.xml"
ROBOTS = "https://www.visitfortwayne.com/robots.txt"
#: The directory's own published Crawl-delay.
CRAWL_DELAY_SECONDS = 2.0

#: Over-selects on purpose; the page's structured data decides what a row is.
LODGING_SLUG_KEYWORDS = (
    "hotel", "motel", "inn", "suites", "lodge", "hostel", "extended-stay", "home2",
    "candlewood", "woodspring", "staybridge", "hyatt", "hilton", "marriott",
    "courtyard", "residence", "springhill", "towneplace", "fairfield", "hampton",
    "homewood", "doubletree", "holiday", "wyndham", "baymont", "days-inn", "super-8",
    "ramada", "la-quinta", "best-western", "comfort", "quality", "sleep", "econo",
    "rodeway", "clarion", "avid", "tru-by", "red-roof", "motel-6", "drury", "sonesta",
    "magnuson", "bradley", "klopfenstein", "luxbury", "hoosier", "studios", "suburban",
    "travelodge", "americinn", "country-hearth", "coliseum", "mckinnie",
    "bed-and-breakfast", "guest-house", "cabin", "campground", "rv-park",
)

#: schema.org types that ARE ordinary hotel lodging for this product.
#: ``accommodation`` is on this list because it is the type THIS directory
#: actually files its lodging under -- 25 of its listings carry it, including
#: every hotel it lists -- and reading it as anything else would throw the
#: lane's whole yield away.
_LODGING_TYPES = {"hotel", "motel", "inn", "resort", "lodgingbusiness",
                  "extendedstaylodgingbusiness", "bedandbreakfast", "hostel",
                  "accommodation"}
#: Lodging, but not the hotel category this product publishes.
_OUT_OF_CATEGORY_TYPES = {"campground", "rvpark", "vacationrental", "apartment",
                          "houseboat", "campingpitch"}
#: Types that genuinely settle "this is not lodging". ``localbusiness`` is
#: deliberately NOT here. It is this directory's catch-all -- 55 of its listings
#: carry it, and they include a concert arena, a dinner theatre and a log cabin
#: retreat alike -- so reading it as a refusal would encode the directory's
#: SILENCE about a category as a decision about one. A generic type leaves the
#: row UNDETERMINED, which another lane can corroborate and a human can review.
_NON_LODGING_TYPES = {"restaurant", "cafe", "bar", "foodestablishment", "store",
                      "pharmacy", "park", "civicstructure", "touristattraction",
                      "event", "theater", "performingartstheater", "museum",
                      "stadiumorarena", "sportsactivitylocation", "meetingroom",
                      "golfcourse", "movietheater", "nightclub", "winery"}


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


def _jsonld_nodes(html):
    """Every JSON-LD node on the page, flattened through @graph."""
    out = []
    for block in re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.I | re.S):
        try:
            data = json.loads(block.strip())
        except Exception:  # noqa: BLE001
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                if "@graph" in node:
                    stack.append(node["@graph"])
                out.append(node)
    return out


def _types(node):
    t = node.get("@type")
    if isinstance(t, str):
        return [t.lower()]
    if isinstance(t, list):
        return [str(x).lower() for x in t]
    return []


def classify(nodes, slug):
    """LODGING / OUT_OF_CURRENT_CATEGORY / NON_LODGING / UNDETERMINED, on the
    page's OWN structured data. A slug never decides this."""
    seen = []
    for node in nodes:
        for t in _types(node):
            seen.append(t)
            if t in _LODGING_TYPES:
                return "LODGING", t
            if t in _OUT_OF_CATEGORY_TYPES:
                return "OUT_OF_CURRENT_CATEGORY", t
    for t in seen:
        if t in _NON_LODGING_TYPES:
            return "NON_LODGING", t
    return "UNDETERMINED", (seen[0] if seen else "")


def _addr(node):
    a = node.get("address")
    if isinstance(a, list):
        a = a[0] if a else {}
    if not isinstance(a, dict):
        return {}
    return a


def read_listing(url, stats):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    path = os.path.join(CACHE, key + ".html")
    meta_path = os.path.join(CACHE, key + ".json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
    else:
        time.sleep(CRAWL_DELAY_SECONDS)
        st, final, body, dt = get(url)
        stats["requests"] += 1
        meta = {"url": url, "status": st, "final_url": final, "bytes": len(body),
                "seconds": dt,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if body:
            with open(path, "wb") as fh:
                fh.write(body)
        json.dump(meta, open(meta_path, "w", encoding="utf-8"))

    slug = urllib.parse.unquote(url.split("/listing/")[-1].rstrip("/"))
    rec = OrderedDict([
        ("cvb_url", url), ("cvb_slug", slug), ("status", meta["status"]),
        ("page_sha256", None), ("classification", "CAPTURE_FAILED"),
        ("schema_type", ""), ("name", ""), ("street", ""), ("city", ""),
        ("region", ""), ("postal_code", ""), ("telephone", ""),
        ("official_website", ""), ("latitude", None), ("longitude", None),
    ])
    if meta["status"] != 200 or not os.path.exists(path):
        return rec
    html_b = open(path, "rb").read()
    rec["page_sha256"] = hashlib.sha256(html_b).hexdigest()
    html = html_b.decode("utf-8", "replace")
    nodes = _jsonld_nodes(html)
    kind, t = classify(nodes, slug)
    rec["classification"] = kind
    rec["schema_type"] = t
    best = None
    for node in nodes:
        types = _types(node)
        if any(x in _LODGING_TYPES or x in _OUT_OF_CATEGORY_TYPES for x in types):
            best = node
            break
    if best is None:
        for node in nodes:
            if node.get("address") or node.get("telephone"):
                best = node
                break
    if best is not None:
        a = _addr(best)
        geo = best.get("geo") if isinstance(best.get("geo"), dict) else {}
        rec["name"] = str(best.get("name") or "").strip()
        rec["street"] = str(a.get("streetAddress") or "").strip()
        rec["city"] = str(a.get("addressLocality") or "").strip()
        rec["region"] = str(a.get("addressRegion") or "").strip()
        rec["postal_code"] = str(a.get("postalCode") or "").strip()[:5]
        rec["telephone"] = str(best.get("telephone") or "").strip()
        url_field = best.get("url")
        rec["official_website"] = str(url_field or "").strip()
        try:
            if geo.get("latitude") not in (None, ""):
                rec["latitude"] = float(geo["latitude"])
                rec["longitude"] = float(geo["longitude"])
        except Exception:  # noqa: BLE001
            pass
    if not rec["name"]:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            rec["name_from_title"] = " ".join(m.group(1).split())[:160]
    return rec


def build(args):
    stats = {"requests": 0}
    st, _, body, _ = get(ROBOTS)
    stats["requests"] += 1
    robots_txt = body.decode("utf-8", "replace") if body else ""
    time.sleep(CRAWL_DELAY_SECONDS)
    st_sm, _, sm_body, _ = get(SITEMAP)
    stats["requests"] += 1
    if st_sm != 200:
        raise SystemExit("CVB sitemap refused: %s" % st_sm)
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm_body.decode("utf-8", "replace"))
    listing_urls = sorted({u for u in locs if "/listing/" in u})
    selected = [u for u in listing_urls
                if any(k in urllib.parse.unquote(u).lower() for k in LODGING_SLUG_KEYWORDS)]
    if args.max_pages:
        selected = selected[: args.max_pages]
    print("sitemap urls", len(locs), "listings", len(listing_urls),
          "selected", len(selected), flush=True)

    rows = []
    for i, u in enumerate(selected):
        rows.append(read_listing(u, stats))
        if (i + 1) % 10 == 0:
            print("  fetched", i + 1, "of", len(selected),
                  "requests", stats["requests"], flush=True)

    lodging = [r for r in rows if r["classification"] == "LODGING"]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4D -- new-market shadow census, official tourism directory lane"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "Visit Fort Wayne / Allen County CVB (visitfortwayne.com)"),
        ("what_this_is",
         "The official Allen County CVB lodging directory, walked from its published "
         "sitemap because its /hotels/ index renders client-side. A lodging-keyword "
         "filter over the listing slug selects what to fetch; the listing page's OWN "
         "structured data decides whether the row is LODGING, OUT_OF_CURRENT_CATEGORY, "
         "NON_LODGING or UNDETERMINED. IDENTITY LEADS ONLY -- a CVB listing is not "
         "policy evidence and does not by itself admit a property to the census."),
        ("robots_allows", "Allow: /" in robots_txt),
        ("crawl_delay_honoured_seconds", CRAWL_DELAY_SECONDS),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("counts", OrderedDict([
            ("sitemap_urls", len(locs)),
            ("listing_urls", len(listing_urls)),
            ("selected_for_fetch", len(selected)),
            ("by_classification",
             OrderedDict(sorted(Counter(r["classification"] for r in rows).items()))),
            ("lodging_rows", len(lodging)),
            ("lodging_with_street",
             sum(1 for r in lodging if r["street"])),
            ("lodging_with_postal",
             sum(1 for r in lodging if r["postal_code"])),
        ])),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "fort_wayne_in_cvb_directory_harvest_001.json"))
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
