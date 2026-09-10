"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- Phases 4D/4E and 5: identity
LEADS from a competitor directory and from the official destination
organisations.

WHAT A LEAD IS AND IS NOT
-------------------------
Everything this module produces is an IDENTITY LEAD: a name, sometimes an
address, and a directory URL. Nothing here is authority. A competitor's
``petsAllowed`` flag is captured because it is a TARGETING HINT -- it tells the
factory which rows are worth a first-party read first -- and it is never
published, never parsed into a fact, and never allowed to settle a row. The
first-party binding contract states this outright: competitor evidence is LEAD
ONLY.

TWO MEASUREMENTS NASHVILLE MADE THAT THIS ORDER REPEATS RATHER THAN INHERITS
---------------------------------------------------------------------------
1. **The /hotels/ path filter may or may not be live.** In Nashville the
   unfiltered ``/lodging/city/`` path returned 399 rows and the filtered
   ``/lodging/hotels/city/`` path 245, and the 250 rows only the unfiltered path
   carried were short-term rentals. In an earlier market the same filter was
   INERT. So this run measures it on Charlotte's own city page and records which
   it found, then supplies leads from the filtered path.
2. **A "city" page serves a RADIUS, not a city.** Antioch's Nashville page
   stated 5 results and served the same 399 rows as Belle Meade's, which stated
   0. So Charlotte is walked in full, and every other city is asked for its
   FIRST page only; a city whose first page is a subset of the Charlotte cohort
   is recorded as such and not walked again.

TWO STATES
----------
Charlotte's admitted corridors reach into South Carolina, and the held Rock Hill
corridor is there too. Out-of-market city slugs are those in neither Carolina;
a South Carolina slug is CARRIED and judged later on the postal code the
property's own page states.

No paid provider is called. Output is Charlotte-local.

Output:
  launch_packages/pettripfinder/markets/reports/charlotte_nc_lead_sources_001.json
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
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
SCHEMA = "ptf-market-lead-sources/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "charlotte_nc_lead_sources_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 0.6

BF = "https://www.bringfido.com"
#: Seeds. The real list is read from the Charlotte hub page's OWN links and
#: unioned with these, because BringFido's city slugs mix hyphens and
#: underscores with no rule worth guessing.
BF_SEED_CITIES = ["charlotte_nc_us", "pineville_nc_us", "matthews_nc_us",
                  "huntersville_nc_us", "concord_nc_us", "gastonia_nc_us",
                  "fort-mill_sc_us", "rock-hill_sc_us"]
_CITY_HREF = re.compile(r'href="/lodging/city/([a-z0-9_-]+)/"', re.I)
_REL_NEXT = re.compile(r'rel="next"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*rel="next"', re.I)
#: The JSON-LD ``Hotel`` block BringFido emits for each result. ``petsAllowed``
#: is captured because it is the TARGETING HINT; it is never authority.
_LD_ITEM = re.compile(
    r'"petsAllowed":\s*(true|false),\s*"name":\s*"([^"]+)",\s*"url":\s*'
    r'"(https://www\.bringfido\.com/lodging/(\d+))"', re.I)
_HEADLINE = re.compile(r'([0-9][0-9,]*)\s+(?:pet[- ]friendly\s+)?(?:hotels|places|results)', re.I)
#: A slug for a city in neither Carolina. BringFido's "nearby" rail links them.
_NON_CAROLINA = re.compile(r"[-_](?![ns]c[-_])[a-z]{2}[-_]us$", re.I)
MAX_PAGES = 30

#: The official destination organisations for this market. Probed on several
#: hosts and paths so a refusal is a measurement rather than one unlucky URL.
DESTINATION = OrderedDict([
    ("CHARLOTTES_GOT_A_LOT", [
        "https://www.charlottesgotalot.com/robots.txt",
        "https://charlottesgotalot.com/robots.txt",
        "https://www.charlottesgotalot.com/sitemap.xml",
        "https://www.charlottesgotalot.com/hotels",
    ]),
    ("NC_STATE_TOURISM", [
        "https://www.visitnc.com/robots.txt",
        "https://www.visitnc.com/sitemap.xml",
    ]),
    ("CHARLOTTE_CENTER_CITY", [
        "https://www.charlottecentercity.org/robots.txt",
        "https://www.charlottecentercity.org/sitemap.xml",
    ]),
    ("VISIT_CABARRUS", [
        "https://www.visitcabarrus.com/robots.txt",
        "https://www.visitcabarrus.com/sitemap.xml",
    ]),
    ("VISIT_LAKE_NORMAN", [
        "https://www.visitlakenorman.org/robots.txt",
        "https://www.visitlakenorman.org/sitemap.xml",
    ]),
    ("VISIT_GASTON", [
        "https://www.visitgastoncounty.org/robots.txt",
        "https://www.visitgastoncounty.org/sitemap.xml",
    ]),
    ("VISIT_YORK_COUNTY_SC", [
        "https://www.visityorkcounty.com/robots.txt",
        "https://www.visityorkcounty.com/sitemap.xml",
    ]),
])
#: A partner/lodging slug. Generous on purpose: every hit is confirmed against
#: the page's own address before it becomes a lead.
_LODGING_SLUG = re.compile(
    r"(hotel|motel|-inn|inn-|suites|lodge|resort|hostel|bed-and-breakfast"
    r"|extended-stay|homewood|hampton|marriott|hilton|hyatt|sheraton|westin|renaissance"
    r"|courtyard|residence|towneplace|springhill|fairfield|doubletree|embassy|candlewood"
    r"|staybridge|holiday|crowne|radisson|ramada|baymont|wyndham|super-8|days-|quality"
    r"|comfort|sleep-|clarion|econo|travelodge|howard-johnson|red-roof|motel-6|studio"
    r"|woodspring|sonesta|drury|best-western|la-quinta|home2|tru-|element-|aloft|omni"
    r"|loews|graduate|kimpton|moxy|ac-hotel|jw-marriott|le-meridien|grand-bohemian"
    r"|ballantyne|ivey|duke-mansion|mecklen)", re.I)
_NOT_LODGING_SLUG = re.compile(
    r"(property-management|management-company|chamber|convention-and-visitors|realty"
    r"|construction|supply|laundry|linen|staffing|insurance|marketing|design-group"
    r"|rv-resort|campground|golf-course|brewing|restaurant|pub|cafe|catering"
    r"|records|museum|theater|theatre|speedway-club|raceway)", re.I)


def get(url, timeout=25):
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


def _walk_bf(base, stats):
    """Every page of one BringFido listing URL. Returns (rows, pages, headline)."""
    rows, pages, headline = OrderedDict(), [], None
    url = base
    for _ in range(MAX_PAGES):
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        found = _LD_ITEM.findall(html)
        if headline is None:
            m = _HEADLINE.search(html)
            headline = int(m.group(1).replace(",", "")) if m else None
        for pets, name, purl, pid in found:
            rows.setdefault(pid, OrderedDict([
                ("bringfido_id", pid), ("name", name), ("directory_url", purl),
                ("competitor_pets_allowed_claim", pets.lower() == "true")]))
        pages.append(OrderedDict([
            ("url", url), ("status", meta["status"]), ("bytes", meta["bytes"]),
            ("sha256", meta["sha256"]), ("rows_parsed", len(found))]))
        if meta["status"] != 200 or not found:
            break
        nxt = _REL_NEXT.search(html)
        nxt_url = (nxt.group(1) or nxt.group(2)) if nxt else ""
        if not nxt_url or nxt_url == url:
            break
        url = nxt_url if nxt_url.startswith("http") else BF + nxt_url
    return rows, pages, headline


def harvest_bringfido(stats):
    hub_meta, hub_body = cached_get("%s/lodging/city/charlotte_nc_us/" % BF, stats)
    hub_html = hub_body.decode("utf-8", "replace") if hub_body else ""
    linked = sorted(set(_CITY_HREF.findall(hub_html)))
    cities = sorted(set(BF_SEED_CITIES) | set(linked))
    out_of_state = [c for c in cities if _NON_CAROLINA.search(c)]
    cities = [c for c in cities if not _NON_CAROLINA.search(c)]

    unfiltered_rows, _u_pages, u_head = _walk_bf(
        "%s/lodging/city/charlotte_nc_us/" % BF, stats)
    filtered_rows, f_pages, f_head = _walk_bf(
        "%s/lodging/hotels/city/charlotte_nc_us/" % BF, stats)
    only_unfiltered = sorted(set(unfiltered_rows) - set(filtered_rows))
    only_filtered = sorted(set(filtered_rows) - set(unfiltered_rows))
    live = bool(only_unfiltered or only_filtered)
    filter_test = OrderedDict([("charlotte_nc_us", OrderedDict([
        ("unfiltered_url", "%s/lodging/city/charlotte_nc_us/" % BF),
        ("filtered_url", "%s/lodging/hotels/city/charlotte_nc_us/" % BF),
        ("unfiltered_rows", len(unfiltered_rows)),
        ("filtered_rows", len(filtered_rows)),
        ("only_in_unfiltered", len(only_unfiltered)),
        ("only_in_filtered", len(only_filtered)),
        ("verdict", "PATH_FILTER_IS_LIVE" if live
                    else "PATH_FILTER_IS_INERT_SAME_COHORT_BOTH_WAYS"),
        ("why", "measured on this market's own city page by this run, never inherited. "
                "The FILTERED path supplies the leads either way; when the filter is "
                "live the rows only the unfiltered path carries are short-term "
                "rentals and are NOT imported as hotels."),
        ("sample_only_in_unfiltered",
         [unfiltered_rows[i]["name"] for i in only_unfiltered[:12]]),
        ("headline_unfiltered", u_head), ("headline_filtered", f_head),
    ]))])

    per_city, leads = OrderedDict(), OrderedDict()
    per_city["charlotte_nc_us"] = OrderedDict([
        ("url", "%s/lodging/hotels/city/charlotte_nc_us/" % BF),
        ("pages_fetched", len(f_pages)),
        ("headline_result_count_the_page_states", f_head),
        ("rows_actually_parsed", len(filtered_rows)),
        ("headline_equals_parsed", f_head == len(filtered_rows)),
        ("cohort_verdict", "WALKED_IN_FULL"), ("pages", f_pages)])
    for pid, row in filtered_rows.items():
        row = OrderedDict(row)
        row["seen_on_city"] = "charlotte_nc_us"
        leads.setdefault(pid, row)

    reference = set(filtered_rows)
    for city in cities:
        if city == "charlotte_nc_us":
            continue
        url = "%s/lodging/hotels/city/%s/" % (BF, city)
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        page_one = OrderedDict((pid, OrderedDict([
            ("bringfido_id", pid), ("name", name), ("directory_url", purl),
            ("competitor_pets_allowed_claim", pets.lower() == "true")]))
            for pets, name, purl, pid in _LD_ITEM.findall(html))
        m = _HEADLINE.search(html)
        head = int(m.group(1).replace(",", "")) if m else None
        if page_one and set(page_one) <= reference:
            per_city[city] = OrderedDict([
                ("url", url), ("pages_fetched", 1),
                ("headline_result_count_the_page_states", head),
                ("rows_actually_parsed", len(page_one)),
                ("headline_equals_parsed", head == len(page_one)),
                ("cohort_verdict", "COHORT_IS_A_SUBSET_OF_THE_CHARLOTTE_WALK"),
                ("why", "every row this city's first page serves is already in the "
                        "Charlotte cohort, so the city slug picks a centre and the "
                        "list is a radius; walking it again is not more evidence"),
                ("pages", [OrderedDict([("url", url), ("status", meta["status"]),
                                        ("bytes", meta["bytes"]),
                                        ("sha256", meta["sha256"]),
                                        ("rows_parsed", len(page_one))])])])
            continue
        rows, pages, head = _walk_bf(url, stats)
        per_city[city] = OrderedDict([
            ("url", url), ("pages_fetched", len(pages)),
            ("headline_result_count_the_page_states", head),
            ("rows_actually_parsed", len(rows)),
            ("headline_equals_parsed", head == len(rows)),
            ("cohort_verdict", "WALKED_IN_FULL_BECAUSE_ITS_FIRST_PAGE_CARRIED_NEW_ROWS"),
            ("pages", pages)])
        for pid, row in rows.items():
            row = OrderedDict(row)
            row["seen_on_city"] = city
            leads.setdefault(pid, row)

    return OrderedDict([
        ("hub_url", "%s/lodging/city/charlotte_nc_us/" % BF),
        ("hub_status", hub_meta["status"]), ("hub_sha256", hub_meta["sha256"]),
        ("cities_linked_by_the_hub", linked),
        ("cities_dropped_out_of_the_carolinas", out_of_state),
        ("cities_walked", per_city),
        ("category_filter_test", filter_test),
        ("distinct_leads", len(leads)),
        ("leads", list(leads.values())),
    ])


def probe_destinations(stats):
    out = OrderedDict()
    for org, urls in DESTINATION.items():
        attempts, slugs = [], OrderedDict()
        for u in urls:
            meta, body = cached_get(u, stats)
            html = body.decode("utf-8", "replace") if body else ""
            hits = []
            if meta["status"] == 200 and body:
                for href in re.findall(r'(?:href=|<loc>)\s*"?([^"<>\s]+)', html):
                    low = href.lower()
                    if _LODGING_SLUG.search(low) and not _NOT_LODGING_SLUG.search(low):
                        hits.append(href)
            for h in hits:
                slugs.setdefault(h, org)
            attempts.append(OrderedDict([
                ("url", u), ("status", meta["status"]), ("bytes", meta["bytes"]),
                ("sha256", meta["sha256"]), ("lodging_links", len(hits))]))
        served = [a for a in attempts if a["status"] == 200]
        out[org] = OrderedDict([
            ("attempts", attempts), ("any_url_served", bool(served)),
            ("distinct_lodging_links", len(slugs)),
            ("lodging_links", sorted(slugs)[:400]),
            ("verdict", "SERVED" if served else "REFUSED_OR_ABSENT_ON_EVERY_URL"),
            ("why", "an official destination organisation that refuses a plain client "
                    "is a fact about this client at this moment; it is never evidence "
                    "that the destination has no lodging")])
    return out


def build(args):
    stats = {"requests": 0}
    bf = harvest_bringfido(stats)
    dest = probe_destinations(stats)
    hinted = sum(1 for r in bf["leads"] if r["competitor_pets_allowed_claim"])
    dest_links = sum(v["distinct_lodging_links"] for v in dest.values())
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4D/4E/5 -- identity leads (competitor directory, destination organisations)"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "LOCAL_FREE_DISCOVERY (leads only)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("competitor_evidence_is_lead_only",
         "Every row here is an IDENTITY LEAD. A competitor's petsAllowed flag is a "
         "TARGETING HINT that decides read ORDER and nothing else. It is never "
         "published, never parsed into a policy fact, and never settles a row. The "
         "first-party binding contract refuses competitor evidence as authority."),
        ("a_directory_url_is_never_a_route",
         "A bringfido.com/lodging/<id> URL is a lead's address at the COMPETITOR. It "
         "is not the property's official URL and is never routed or captured as one."),
        ("bringfido", bf),
        ("destination_organisations", dest),
        ("counts", OrderedDict([
            ("bringfido_cities_walked", len(bf["cities_walked"])),
            ("bringfido_distinct_leads", bf["distinct_leads"]),
            ("bringfido_rows_claiming_pets_allowed", hinted),
            ("bringfido_cities_walked_in_full",
             sum(1 for v in bf["cities_walked"].values()
                 if v["cohort_verdict"].startswith("WALKED_IN_FULL"))),
            ("destination_orgs_probed", len(dest)),
            ("destination_orgs_served", sum(1 for v in dest.values() if v["any_url_served"])),
            ("destination_lodging_links", dest_links),
        ])),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "charlotte_nc_lead_sources_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    print("bringfido cities    :", c["bringfido_cities_walked"],
          "walked in full:", c["bringfido_cities_walked_in_full"])
    print("bringfido leads     :", c["bringfido_distinct_leads"],
          "(pets-allowed hint on %d)" % c["bringfido_rows_claiming_pets_allowed"])
    for city, t in rep["bringfido"]["category_filter_test"].items():
        print("filter test %-16s %s (%d unfiltered / %d filtered)"
              % (city, t["verdict"], t["unfiltered_rows"], t["filtered_rows"]))
    print("destination orgs    :", c["destination_orgs_served"], "of",
          c["destination_orgs_probed"], "served;", c["destination_lodging_links"], "links")
    print("free http requests  :", rep["free_http_requests"])
    print("written             :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
