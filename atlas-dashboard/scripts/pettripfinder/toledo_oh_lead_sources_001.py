"""PTF-TOLEDO-OH-NEW-MARKET-001 -- Phase 4D/4E/6, the free LEAD lanes.

Two zero-cost lead sources, read first-party and treated as leads only:

* the official Destination Toledo (visittoledo.org) lodging directory, and
* BringFido's Toledo city pages, a competitor pet-travel directory.

WHAT A LEAD IS
--------------
A row here proposes that a lodging identity EXISTS. It never decides that the
identity belongs to Toledo, never names its policy, and never publishes. A
competitor's pet-friendly claim is recorded verbatim as a TARGETING HINT so the
policy lane knows where to look, and is marked so it can never be mistaken for
authority. PTF-CINCINNATI-PARALLEL-REVALIDATION-002 and the competitor-census
doctrine are explicit: a competitor directory is an AUDIT lane, not an
acquisition lane.

TWO TRAPS THIS RUN CHECKS RATHER THAN ASSUMES
---------------------------------------------
1. **Is the category filter live?** BringFido exposes both
   ``/lodging/city/<city>/`` and ``/lodging/hotels/city/<city>/``. A filter that
   is inert returns the same cohort for both, and a market that trusts it silently
   imports vacation rentals as hotels. This run fetches BOTH and diffs them.
2. **Is the headline count the served cohort?** The page's own result count is
   recorded next to the number of rows actually parsed, and they are reported as
   two different facts.

Michigan cities adjacent to Toledo (Lambertville, Temperance, Ottawa Lake, Erie,
La Salle, Luna Pier) are fetched deliberately: this market's contract admits Ohio
only, so those rows are CLASSIFIED OUTSIDE_MARKET rather than silently missed.

No paid provider is called. Output is Toledo-local.

Output:
  launch_packages/pettripfinder/markets/reports/toledo_oh_lead_sources_001.json
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
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-TOLEDO-OH-NEW-MARKET-001"
MARKET_ID = "toledo-oh"
SCHEMA = "ptf-market-lead-sources/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "toledo_oh_lead_sources_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 1.2

BF = "https://www.bringfido.com"
#: Every city page BringFido itself links from the Toledo hub. The Michigan
#: entries are fetched on purpose -- see the module docstring.
#: Seeds only. BringFido's city slugs mix hyphens and underscores with no rule
#: worth guessing (``monclova-oh-us`` but ``maumee_oh_us``), so the real list is
#: read from the Toledo hub page's OWN links and unioned with these two, which
#: the hub does not link but which serve.
BF_CITIES = ["toledo_oh_us", "bowling_green_oh_us", "swanton_oh_us"]
_CITY_HREF = re.compile(r'href="/lodging/city/([a-z0-9_-]+)/"', re.I)
MI_SUFFIX = re.compile(r"[-_]mi[-_]us$", re.I)
#: BringFido paginates with ?page=N and advertises the next page with a
#: rel="next" link. Page one alone is a PAGE SIZE (19 rows), never the cohort;
#: a market that stops there under-counts every city it looks at.
_REL_NEXT = re.compile(r'rel="next"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*rel="next"', re.I)
MAX_PAGES = 12

TOURISM = [
    ("DESTINATION_TOLEDO",
     "https://visittoledo.org/meetings-groups/venues-hotels/hotels-lodging/"),
]
#: Destination Toledo's OWN partner sitemap. Its hotels-lodging page renders its
#: directory client-side and yields almost nothing to a plain client; the
#: partner sitemap is the same organisation's published index and yields the
#: whole roster. This is a TIER 2 official destination source under
#: ptf-identity-evidence/1.0 -- identity only, never policy.
CVB_PARTNER_SITEMAP = "https://visittoledo.org/partner-sitemap.xml"
#: A partner slug that reads like lodging. Deliberately generous: every hit is
#: confirmed against the partner page's own address before it becomes a lead,
#: and obvious non-lodging (a hotel MANAGEMENT company, an RV resort, a
#: chamber of commerce) is dropped by name below.
_LODGING_SLUG = re.compile(
    r"(hotel|motel|inn|-inn-|suites|lodge|resort|hostel|bed-and-breakfast|b-and-b"
    r"|extended-stay|homewood|hampton|marriott|hilton|hyatt|sheraton|westin|renaissance"
    r"|courtyard|residence|towneplace|springhill|fairfield|doubletree|embassy|candlewood"
    r"|staybridge|holiday|crowne|radisson|ramada|baymont|wyndham|super-8|days-|quality"
    r"|comfort|sleep-|clarion|econo|travelodge|howard-johnson|red-roof|motel-6|studio"
    r"|woodspring|sonesta|drury|best-western|la-quinta|home2|tru-|element-|aloft)", re.I)
#: Slugs the pattern above catches that are NOT a lodging property.
_NOT_LODGING_SLUG = re.compile(
    r"(property-management|management-company|chamber|convention-and-visitors|realty"
    r"|construction|supply|laundry|linen|staffing|insurance|marketing|design-group"
    r"|rv-resort|campground|golf-course|brewing|restaurant|pub|cafe|catering)", re.I)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Encoding": "gzip", "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                try:
                    data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
                except Exception:  # noqa: BLE001
                    pass
            return r.status, r.geturl(), data
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def cached_get(url, stats):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    meta_path = os.path.join(CACHE, key + ".json")
    body_path = os.path.join(CACHE, key + ".html")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
        body = open(body_path, "rb").read() if os.path.exists(body_path) else b""
        return meta, body
    time.sleep(SPACING)
    st, final, body = get(url)
    stats["requests"] += 1
    meta = {"url": url, "status": st, "final_url": final, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest() if body else "",
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if body:
        open(body_path, "wb").write(body)
    json.dump(meta, open(meta_path, "w", encoding="utf-8"))
    return meta, body


_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)


def itemlist_hotels(html: str):
    """Hotel rows from the page's own schema.org ItemList."""
    out = []
    for m in _LD.finditer(html):
        raw = m.group(1).strip()
        try:
            doc = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        docs = doc if isinstance(doc, list) else [doc]
        for d in docs:
            if not isinstance(d, dict) or d.get("@type") != "ItemList":
                continue
            for el in d.get("itemListElement") or []:
                item = (el or {}).get("item") if isinstance(el, dict) else None
                if not isinstance(item, dict):
                    continue
                addr = item.get("address") or {}
                if not isinstance(addr, dict):
                    addr = {}
                out.append(OrderedDict([
                    ("name", str(item.get("name") or "").strip()),
                    ("type", str(item.get("@type") or "")),
                    ("url", str(item.get("url") or "")),
                    ("street", str(addr.get("streetAddress") or "").strip()),
                    ("city", str(addr.get("addressLocality") or "").strip()),
                    ("region", str(addr.get("addressRegion") or "").strip()),
                    ("postal_code", str(addr.get("postalCode") or "").strip()),
                    ("telephone", str(item.get("telephone") or "").strip()),
                ]))
    return out


_COUNT = re.compile(r"([\d,]+)\s+(?:pet[- ]friendly\s+)?(?:hotels?|results?|places?|properties)",
                    re.I)


def headline_count(html: str):
    m = _COUNT.search(re.sub(r"<[^>]+>", " ", html))
    return m.group(1).replace(",", "") if m else ""


def walk_paginated(first_url, stats):
    """Every page of a BringFido listing, followed by its own rel=next link."""
    pages, rows, url, seen = [], [], first_url, set()
    while url and url not in seen and len(pages) < MAX_PAGES:
        seen.add(url)
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        page_rows = itemlist_hotels(html) if meta["status"] == 200 else []
        pages.append(OrderedDict([("url", url), ("status", meta["status"]),
                                  ("sha256", meta["sha256"]),
                                  ("fetched_at", meta["fetched_at"]),
                                  ("rows_parsed", len(page_rows))]))
        rows.extend(page_rows)
        m = _REL_NEXT.search(html) if html else None
        nxt = (m.group(1) or m.group(2)) if m else ""
        url = nxt if nxt and nxt.startswith("http") else ""
    # A listing row can repeat across pages; identity is name + street.
    uniq, out = set(), []
    for r in rows:
        k = (r["name"].lower().strip(), r["street"].lower().strip())
        if k in uniq:
            continue
        uniq.add(k)
        out.append(r)
    return pages, out


def discover_city_slugs(stats):
    """The neighbouring-city pages BringFido's own Toledo hub links to."""
    meta, body = cached_get("%s/lodging/city/toledo_oh_us/" % BF, stats)
    html = body.decode("utf-8", "replace") if body else ""
    found = [s for s in sorted(set(_CITY_HREF.findall(html)))]
    slugs = list(BF_CITIES)
    for s in found:
        if s not in slugs:
            slugs.append(s)
    return slugs, found


def harvest_bringfido(stats):
    cities = OrderedDict()
    filter_probe = OrderedDict()
    slugs, hub_linked = discover_city_slugs(stats)
    for slug in slugs:
        url = "%s/lodging/city/%s/" % (BF, slug)
        pages, rows = walk_paginated(url, stats)
        first = pages[0]
        html_first = ""
        cities[slug] = OrderedDict([
            ("url", url), ("status", first["status"]), ("sha256", first["sha256"]),
            ("fetched_at", first["fetched_at"]),
            ("pages_walked", len(pages)),
            ("page_trail", pages),
            ("headline_count_on_page", ""),
            ("rows_parsed", len(rows)),
            ("state", "MI" if MI_SUFFIX.search(slug) else "OH"),
            ("rows", rows),
        ])
    # Is the category PATH filter live, or inert? Diff the two Toledo cohorts.
    all_url = "%s/lodging/city/toledo_oh_us/" % BF
    hotels_url = "%s/lodging/hotels/city/toledo_oh_us/" % BF
    rentals_url = "%s/lodging/rentals/city/toledo_oh_us/" % BF
    probes = OrderedDict()
    for label, u in (("ALL_LODGING", all_url), ("HOTELS_ONLY", hotels_url),
                     ("RENTALS_ONLY", rentals_url)):
        pages, rows = walk_paginated(u, stats)
        probes[label] = OrderedDict([
            ("url", u), ("status", pages[0]["status"]), ("sha256", pages[0]["sha256"]),
            ("pages_walked", len(pages)),
            ("rows_parsed", len(rows)),
            ("names", sorted({r["name"] for r in rows if r["name"]})),
        ])
    a = set(probes["ALL_LODGING"]["names"])
    h = set(probes["HOTELS_ONLY"]["names"])
    r = set(probes["RENTALS_ONLY"]["names"])
    filter_probe = OrderedDict([
        ("question", "Is BringFido's lodging-category PATH filter live for this city, or inert?"),
        ("all_lodging_rows", len(a)), ("hotels_only_rows", len(h)), ("rentals_only_rows", len(r)),
        ("hotels_equals_all", sorted(a) == sorted(h)),
        ("in_all_not_in_hotels", sorted(a - h)),
        ("in_hotels_not_in_all", sorted(h - a)),
        ("verdict", "INERT_FILTER_TREAT_ALL_ROWS_AS_MIXED_LODGING" if sorted(a) == sorted(h)
                    else "LIVE_FILTER_HOTELS_COHORT_IS_A_REAL_SUBSET"),
        ("probes", probes),
    ])
    filter_probe["city_slugs_from_hub_links"] = hub_linked
    return cities, filter_probe


_HREF = re.compile(r'href="(https?://[^"#?]+)"', re.I)


def harvest_cvb_partners(stats):
    """Destination Toledo's own partner roster: a TIER 2 identity source."""
    meta, body = cached_get(CVB_PARTNER_SITEMAP, stats)
    xml = body.decode("utf-8", "replace") if body else ""
    all_urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    partner_urls = [u for u in all_urls if "/partner/" in u]
    lodging_urls, dropped = [], []
    for u in partner_urls:
        slug = u.rstrip("/").rsplit("/", 1)[-1]
        if not _LODGING_SLUG.search(slug):
            continue
        if _NOT_LODGING_SLUG.search(slug):
            dropped.append(OrderedDict([("url", u), ("slug", slug),
                                        ("why", "slug names a non-lodging business")]))
            continue
        lodging_urls.append(u)
    rows = []
    for u in sorted(set(lodging_urls)):
        meta2, body2 = cached_get(u, stats)
        html = body2.decode("utf-8", "replace") if body2 else ""
        rec = OrderedDict([("url", u), ("status", meta2["status"]),
                           ("sha256", meta2["sha256"]), ("fetched_at", meta2["fetched_at"])])
        if meta2["status"] == 200 and html:
            ld = itemlist_hotels(html)
            rec["structured_rows"] = ld
            t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
            rec["title"] = " ".join(t.group(1).split())[:160] if t else ""
            rec["name"] = re.sub(r"\s*[|\-]\s*(Destination Toledo|Visit Toledo).*$", "",
                                 rec.get("title", "")).strip()
            # The partner page prints the property's address under its own
            # "Address" heading, as a street block followed by a
            # city / state / postal block. Anchoring on that heading is what
            # keeps Destination Toledo's OWN office address (401 Jefferson
            # Avenue, Suite 210) out of every row.
            plain = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
            plain = re.sub(r"<[^>]+>", "\n", plain)
            lines = [" ".join(x.split()) for x in plain.splitlines()]
            lines = [x for x in lines if x]
            try:
                at = lines.index("Address")
            except ValueError:
                at = -1
            if at >= 0:
                block = lines[at + 1: at + 8]
                if block and re.match(r"^\d{1,6}\s+\S", block[0]):
                    rec["street"] = block[0].rstrip(",")
                for j, val in enumerate(block):
                    if re.fullmatch(r"\d{5}", val):
                        rec["postal_code"] = val
                        if j >= 2:
                            rec["city"] = block[j - 2]
                            rec["region"] = block[j - 1]
                        break
            # The partner page's own "Website" button. It carries the
            # property's OFFICIAL brand route -- including IHG and Choice
            # property codes for brands whose own sites refuse a plain client
            # -- which makes this tier-2 destination source a ROUTING lane and
            # not only an identity lane.
            site = re.search(
                r"website-first-instance.*?<a href=['\"](https?://[^'\"]+)['\"]",
                html, re.S | re.I)
            if site and "visittoledo.org" not in site.group(1):
                rec["official_url"] = site.group(1).replace("&#038;", "&").replace("&amp;", "&")
            tel = re.search(r"href=['\"]tel:([+0-9() .-]{7,20})['\"]", html, re.I)
            if tel:
                digits = re.sub(r"\D", "", tel.group(1))[-10:]
                if len(digits) == 10:
                    rec["telephone"] = "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])
        rows.append(rec)
    return OrderedDict([
        ("source", CVB_PARTNER_SITEMAP),
        ("tier", 2),
        ("tier_name", "official destination, tourism or government body"),
        ("sitemap_status", meta["status"]), ("sitemap_sha256", meta["sha256"]),
        ("partner_urls_total", len(partner_urls)),
        ("lodging_slug_matches", len(set(lodging_urls))),
        ("dropped_non_lodging_slug", dropped),
        ("rows", rows),
    ])


def harvest_tourism(stats):
    out = OrderedDict()
    for label, url in TOURISM:
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        rows = itemlist_hotels(html)
        text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", "\n", text)
        # Named lodging headings the CVB page prints, as leads.
        names = sorted({" ".join(line.split()) for line in text.splitlines()
                        if re.search(r"\b(hotel|inn|suites|motel|lodge|resort|house|place)\b",
                                     line, re.I)
                        and 6 <= len(" ".join(line.split())) <= 80})
        out[label] = OrderedDict([
            ("url", url), ("status", meta["status"]), ("sha256", meta["sha256"]),
            ("fetched_at", meta["fetched_at"]),
            ("structured_rows", rows),
            ("named_lodging_lines", names),
            ("outbound_hotel_links", sorted({u for u in _HREF.findall(html)
                                             if re.search(r"marriott|hilton|ihg|hyatt|wyndham|choice"
                                                          r"|hotel|inn|suites|stay", u, re.I)})[:200]),
        ])
    return out


def build(args) -> OrderedDict:
    stats = {"requests": 0}
    cities, filter_probe = harvest_bringfido(stats)
    tourism = harvest_tourism(stats)
    cvb = harvest_cvb_partners(stats)

    leads = OrderedDict()
    for slug, blk in cities.items():
        for row in blk["rows"]:
            key = (row["name"].lower().strip(), row["street"].lower().strip())
            if not key[0]:
                continue
            rec = leads.get(key)
            if rec is None:
                rec = OrderedDict([
                    ("name", row["name"]), ("street", row["street"]), ("city", row["city"]),
                    ("region", row["region"]), ("postal_code", row["postal_code"]),
                    ("telephone", row["telephone"]), ("competitor_url", row["url"]),
                    ("lead_type", row["type"]),
                    ("seen_on_city_pages", []),
                    ("in_market_state", blk["state"] == "OH"),
                ])
                leads[key] = rec
            rec["seen_on_city_pages"].append(slug)

    oh = [v for v in leads.values() if v["in_market_state"]]
    mi = [v for v in leads.values() if not v["in_market_state"]]

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4D/4E/6 -- official tourism directory + competitor directory, LEAD lanes"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "LOCAL_FREE_DISCOVERY"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats["requests"]),
        ("a_lead_is_not_authority",
         "Every row here proposes that a lodging identity EXISTS. It does not decide that the "
         "identity belongs to Toledo, does not name its policy, and cannot publish. A competitor's "
         "pet-friendly claim is a TARGETING HINT for the policy lane and is never quoted as "
         "evidence. First-party identity confirmation is required before any of this enters the "
         "Toledo census."),
        ("page_one_is_a_page_size_not_a_cohort",
         "BringFido serves 19 rows per page and advertises the next page with rel=next; the only "
         "number printed near the top of a city page is a SITE-WIDE listing total (150,000), not a "
         "count for that city. This run follows rel=next to exhaustion per city and reports pages "
         "walked next to rows parsed, so a page size can never be mistaken for a cohort."),
        ("michigan_rows_are_deliberate",
         "BringFido's Toledo hub links six Michigan city pages. They are fetched so that "
         "Lambertville, Temperance, Ottawa Lake, Erie, La Salle and Luna Pier lodging is FOUND and "
         "classified OUTSIDE_MARKET, rather than silently missed and later mistaken for a gap."),
        ("category_filter_probe", filter_probe),
        ("counts", OrderedDict([
            ("city_pages_fetched", len(cities)),
            ("city_pages_200", sum(1 for b in cities.values() if b["status"] == 200)),
            ("distinct_leads", len(leads)),
            ("in_market_state_oh", len(oh)),
            ("outside_market_state_mi", len(mi)),
            ("by_lead_type", OrderedDict(sorted(Counter(v["lead_type"] for v in leads.values()).items()))),
            ("cvb_partner_urls_total", cvb["partner_urls_total"]),
            ("cvb_lodging_rows", len(cvb["rows"])),
            ("cvb_rows_with_address", sum(1 for r in cvb["rows"] if r.get("street"))),
            ("cvb_rows_with_official_url", sum(1 for r in cvb["rows"] if r.get("official_url"))),
            ("pages_and_rows_per_city", OrderedDict(
                (s, OrderedDict([("status", b["status"]), ("pages_walked", b["pages_walked"]),
                                 ("rows_parsed", b["rows_parsed"])]))
                for s, b in cities.items())),
        ])),
        ("competitor_city_pages", cities),
        ("official_tourism", tourism),
        ("official_destination_partner_roster", cvb),
        ("leads_in_market_state", oh),
        ("leads_outside_market_state", mi),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "toledo_oh_lead_sources_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    print("city pages          :", c["city_pages_fetched"], "200:", c["city_pages_200"])
    print("distinct leads      :", c["distinct_leads"], "OH:", c["in_market_state_oh"],
          "MI:", c["outside_market_state_mi"])
    print("lead types          :", dict(c["by_lead_type"]))
    print("category filter     :", rep["category_filter_probe"]["verdict"])
    print("free http requests  :", rep["free_http_requests"])
    print("written             :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
