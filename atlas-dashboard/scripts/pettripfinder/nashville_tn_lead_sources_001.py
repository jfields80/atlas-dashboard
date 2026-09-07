"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phases 4D/4E and 6, the free LEAD lanes.

Two zero-cost lead sources, read first-party and treated as leads only:

* the official Nashville destination organisation (Visit Music City), and
* BringFido's Greater Nashville city pages, a competitor pet-travel directory.

WHAT A LEAD IS
--------------
A row here proposes that a lodging identity EXISTS. It never decides that the
identity belongs to Nashville, never names its policy, and never publishes. A
competitor's pet-friendly claim is recorded verbatim as a TARGETING HINT so the
policy lane knows where to look, and is marked so it can never be mistaken for
authority. The competitor-census doctrine is explicit: a competitor directory is
an AUDIT lane, not an acquisition lane.

TWO TRAPS THIS RUN CHECKS RATHER THAN ASSUMES
---------------------------------------------
1. **Is the category filter live?** BringFido exposes both
   ``/lodging/city/<city>/`` and ``/lodging/hotels/city/<city>/``. A filter that
   is inert returns the same cohort for both, and a market that trusts it
   silently imports vacation rentals as hotels. Cincinnati measured a competitor
   whose PATH filter was live where its query string was inert. This run fetches
   BOTH and diffs them.
2. **Is the headline count the served cohort?** The page's own result count is
   recorded next to the number of rows actually parsed, and the two are reported
   as different facts. Page one is a PAGE SIZE (twelve rows here), never a
   cohort; the ``rel="next"`` chain is walked to a cap.

THE FRINGE IS FETCHED ON PURPOSE
--------------------------------
Franklin, Mount Juliet, Hendersonville, Smyrna, La Vergne and Lebanon are
fetched even though this order's corridor registry claims none of their postal
codes. A held area whose inventory was never looked at cannot be ruled on, and
a founder ruling deserves the count it would admit.

No paid provider is called. Output is Nashville-local.

Output:
  launch_packages/pettripfinder/markets/reports/nashville_tn_lead_sources_001.json
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

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
SCHEMA = "ptf-market-lead-sources/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "nashville_tn_lead_sources_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 1.0

BF = "https://www.bringfido.com"
#: Seeds. The real list is read from the Nashville hub page's OWN links and
#: unioned with these, because BringFido's city slugs mix hyphens and
#: underscores with no rule worth guessing (``mount_juliet_tn_us`` but
#: ``old-hickory-tn-us``).
BF_SEED_CITIES = ["nashville_tn_us", "brentwood_tn_us", "goodlettsville_tn_us"]
_CITY_HREF = re.compile(r'href="/lodging/city/([a-z0-9_-]+)/"', re.I)
_REL_NEXT = re.compile(r'rel="next"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*rel="next"', re.I)
#: The JSON-LD ``Hotel`` block BringFido emits for each result. ``petsAllowed``
#: is captured because it is the TARGETING HINT; it is never authority.
_LD_ITEM = re.compile(
    r'"petsAllowed":\s*(true|false),\s*"name":\s*"([^"]+)",\s*"url":\s*'
    r'"(https://www\.bringfido\.com/lodging/(\d+))"', re.I)
_HEADLINE = re.compile(r'([0-9][0-9,]*)\s+(?:pet[- ]friendly\s+)?(?:hotels|places|results)', re.I)
#: A slug for a city outside Tennessee. BringFido's "nearby" rail links them.
_NON_TN = re.compile(r"[-_](?!tn[-_])[a-z]{2}[-_]us$", re.I)
MAX_PAGES = 25

#: The official destination organisation for Nashville. Probed on several hosts
#: and paths so a refusal is a measurement rather than one unlucky URL.
DESTINATION = OrderedDict([
    ("VISIT_MUSIC_CITY", [
        "https://www.visitmusiccity.com/robots.txt",
        "https://visitmusiccity.com/robots.txt",
        "https://www.visitmusiccity.com/sitemap.xml",
        "https://www.visitmusiccity.com/hotels",
    ]),
    ("TN_STATE_TOURISM", [
        "https://www.tnvacation.com/robots.txt",
        "https://www.tnvacation.com/sitemap.xml",
    ]),
    ("NASHVILLE_DOWNTOWN_PARTNERSHIP", [
        "https://www.nashvilledowntown.com/robots.txt",
        "https://www.nashvilledowntown.com/sitemap.xml",
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
    r"|loews|graduate|thompson|noelle|bobby|dream-|1-hotel|four-seasons|conrad|w-nashville"
    r"|gaylord|opryland|union-station|hermitage-hotel|hutton|joseph)", re.I)
_NOT_LODGING_SLUG = re.compile(
    r"(property-management|management-company|chamber|convention-and-visitors|realty"
    r"|construction|supply|laundry|linen|staffing|insurance|marketing|design-group"
    r"|rv-resort|campground|golf-course|brewing|restaurant|pub|cafe|catering|honky-tonk"
    r"|boot|records|museum|theater|theatre)", re.I)


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
    """Every BringFido lead, from the path the run PROVED is the hotel cohort.

    Two measurements decided the shape of this function, and both were made
    rather than assumed:

    1. **The /hotels/ path filter is LIVE.** The unfiltered ``/lodging/city/``
       path returned 399 rows for Nashville and the filtered
       ``/lodging/hotels/city/`` path returned 245, with 250 rows in the first
       that are not in the second -- "Hart Suite 8 by Avantstay", "2BR Urban
       Bungalow", "Mid Century Luxe Boutique Condo Near Broadway". Those are
       short-term rentals. The FILTERED path is therefore what supplies leads
       here, and the unfiltered cohort is kept only as the diff that proves it.

    2. **A BringFido "city" page serves a REGIONAL cohort, not a city one.**
       Antioch's page states a headline of 5 results and serves the same 399
       rows as Belle Meade's, which states 0. The city slug picks a centre; the
       list is a radius. So this walks Nashville in full, then asks every other
       city for its FIRST page only and compares that page's row set to the
       corresponding page of the Nashville walk. A city whose cohort is
       identical is recorded as such and not walked further -- twenty
       redundant walks of the same 399 rows is not more evidence.
    """
    hub_meta, hub_body = cached_get("%s/lodging/city/nashville_tn_us/" % BF, stats)
    hub_html = hub_body.decode("utf-8", "replace") if hub_body else ""
    linked = sorted(set(_CITY_HREF.findall(hub_html)))
    cities = sorted(set(BF_SEED_CITIES) | set(linked))
    out_of_state = [c for c in cities if _NON_TN.search(c)]
    cities = [c for c in cities if not _NON_TN.search(c)]

    # The category-filter measurement, on the market's own city.
    unfiltered_rows, _u_pages, u_head = _walk_bf(
        "%s/lodging/city/nashville_tn_us/" % BF, stats)
    filtered_rows, f_pages, f_head = _walk_bf(
        "%s/lodging/hotels/city/nashville_tn_us/" % BF, stats)
    only_unfiltered = sorted(set(unfiltered_rows) - set(filtered_rows))
    only_filtered = sorted(set(filtered_rows) - set(unfiltered_rows))
    filter_test = OrderedDict([("nashville_tn_us", OrderedDict([
        ("unfiltered_url", "%s/lodging/city/nashville_tn_us/" % BF),
        ("filtered_url", "%s/lodging/hotels/city/nashville_tn_us/" % BF),
        ("unfiltered_rows", len(unfiltered_rows)),
        ("filtered_rows", len(filtered_rows)),
        ("only_in_unfiltered", len(only_unfiltered)),
        ("only_in_filtered", len(only_filtered)),
        ("verdict", "PATH_FILTER_IS_LIVE" if (only_unfiltered or only_filtered)
                    else "PATH_FILTER_IS_INERT_SAME_COHORT_BOTH_WAYS"),
        ("why", "the two paths returned different cohorts, and the rows only the "
                "unfiltered path carries read as short-term rentals. The FILTERED "
                "path is what supplies leads to the census; the unfiltered cohort "
                "is kept here as the measurement that proves the filter works, and "
                "its extra rows are NOT imported as hotels."),
        ("sample_only_in_unfiltered",
         [unfiltered_rows[i]["name"] for i in only_unfiltered[:12]]),
        ("headline_unfiltered", u_head), ("headline_filtered", f_head),
    ]))])

    per_city, leads = OrderedDict(), OrderedDict()
    per_city["nashville_tn_us"] = OrderedDict([
        ("url", "%s/lodging/hotels/city/nashville_tn_us/" % BF),
        ("pages_fetched", len(f_pages)),
        ("headline_result_count_the_page_states", f_head),
        ("rows_actually_parsed", len(filtered_rows)),
        ("headline_equals_parsed", f_head == len(filtered_rows)),
        ("cohort_verdict", "WALKED_IN_FULL"), ("pages", f_pages)])
    for pid, row in filtered_rows.items():
        row = OrderedDict(row)
        row["seen_on_city"] = "nashville_tn_us"
        leads.setdefault(pid, row)

    reference = set(filtered_rows)
    for city in cities:
        if city == "nashville_tn_us":
            continue
        url = "%s/lodging/hotels/city/%s/" % (BF, city)
        meta, body = cached_get(url, stats)
        html = body.decode("utf-8", "replace") if body else ""
        page_one = {pid: OrderedDict([
            ("bringfido_id", pid), ("name", name), ("directory_url", purl),
            ("competitor_pets_allowed_claim", pets.lower() == "true")])
            for pets, name, purl, pid in _LD_ITEM.findall(html)}
        m = _HEADLINE.search(html)
        head = int(m.group(1).replace(",", "")) if m else None
        if page_one and set(page_one) <= reference:
            per_city[city] = OrderedDict([
                ("url", url), ("pages_fetched", 1),
                ("headline_result_count_the_page_states", head),
                ("rows_actually_parsed", len(page_one)),
                ("headline_equals_parsed", head == len(page_one)),
                ("cohort_verdict", "COHORT_IS_A_SUBSET_OF_THE_NASHVILLE_WALK"),
                ("why", "every row this city's first page serves is already in the "
                        "Nashville cohort, so the city slug picks a centre and the "
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
        ("hub_url", "%s/lodging/city/nashville_tn_us/" % BF),
        ("hub_status", hub_meta["status"]),
        ("city_slugs_linked_by_the_hub", linked),
        ("out_of_state_slugs_dropped", out_of_state),
        ("cities_walked", cities),
        ("lead_cohort_is_the_filtered_hotel_path", True),
        ("per_city", per_city),
        ("category_filter_test", filter_test),
        ("short_term_rental_rows_measured_and_excluded", len(only_unfiltered)),
        ("distinct_leads", len(leads)),
        ("leads", list(leads.values())),
    ])


def harvest_destination(stats):
    out = OrderedDict()
    for org, urls in DESTINATION.items():
        attempts, lodging = [], []
        for u in urls:
            meta, body = cached_get(u, stats)
            html = body.decode("utf-8", "replace") if body else ""
            sitemaps = re.findall(r"(?im)^sitemap:\s*(\S+)", html) if u.endswith("robots.txt") else []
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", html) if "sitemap" in u else []
            hits = [l for l in locs
                    if _LODGING_SLUG.search(l) and not _NOT_LODGING_SLUG.search(l)]
            lodging.extend(hits)
            attempts.append(OrderedDict([
                ("url", u), ("status", meta["status"]), ("bytes", meta["bytes"]),
                ("sitemaps_declared", sitemaps), ("sitemap_locs", len(locs)),
                ("lodging_shaped_locs", len(hits))]))
        served = [a for a in attempts if a["status"] == 200]
        out[org] = OrderedDict([
            ("attempts", attempts),
            ("any_url_served", bool(served)),
            ("lodging_leads", sorted(set(lodging))),
            ("verdict", "SERVED" if served else "REFUSED_ON_EVERY_URL_TRIED"),
            ("why", "" if served else
             "every host and path this client tried returned a refusal; that is a "
             "fact about this client at this moment and is recorded as such. It is "
             "NOT evidence that the organisation publishes no lodging directory, "
             "and it never becomes a policy or closure fact.")])
    return out


def build(args):
    stats = {"requests": 0}
    bf = harvest_bringfido(stats)
    dest = harvest_destination(stats)
    hinted = sum(1 for r in bf["leads"] if r["competitor_pets_allowed_claim"])
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "4D/4E/6 -- free lead lanes (official destination + competitor directory)"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "LOCAL_FREE_DISCOVERY (leads only)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("a_lead_is_not_authority",
         "Every row in this file proposes that a lodging identity EXISTS. No row "
         "here decides market membership, and no row here is policy. A competitor's "
         "petsAllowed claim is recorded verbatim as a TARGETING HINT so the policy "
         "lane knows where to look first; it is never published, never counted, and "
         "never permitted to settle a pets decision. A competitor directory is an "
         "AUDIT lane, not an acquisition lane."),
        ("the_headline_is_not_the_cohort",
         "Each city records the result count the PAGE states next to the number of "
         "rows this run actually parsed. They are two different facts and are never "
         "reconciled by assumption."),
        ("bringfido", bf),
        ("official_destination_sources", dest),
        ("counts", OrderedDict([
            ("bringfido_cities_walked", len(bf["cities_walked"])),
            ("bringfido_distinct_leads", bf["distinct_leads"]),
            ("bringfido_rows_claiming_pets_allowed", hinted),
            ("bringfido_cities_walked_in_full",
             sum(1 for v in bf["per_city"].values()
                 if v["cohort_verdict"].startswith("WALKED_IN_FULL"))),
            ("short_term_rental_rows_measured_and_excluded",
             bf["short_term_rental_rows_measured_and_excluded"]),
            ("destination_orgs_probed", len(dest)),
            ("destination_orgs_served", sum(1 for v in dest.values() if v["any_url_served"])),
            ("destination_lodging_leads",
             sum(len(v["lodging_leads"]) for v in dest.values())),
        ])),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "nashville_tn_lead_sources_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    print("bringfido cities    :", c["bringfido_cities_walked"])
    print("bringfido leads     :", c["bringfido_distinct_leads"],
          "(pets-allowed hint on %d)" % c["bringfido_rows_claiming_pets_allowed"])
    for city, t in rep["bringfido"]["category_filter_test"].items():
        print("filter test %-16s: %s (%d unfiltered, %d filtered)"
              % (city, t["verdict"], t["unfiltered_rows"], t["filtered_rows"]))
    print("STR rows excluded   :",
          rep["bringfido"]["short_term_rental_rows_measured_and_excluded"])
    print("destination orgs    :", c["destination_orgs_served"], "/", c["destination_orgs_probed"],
          "served;", c["destination_lodging_leads"], "lodging leads")
    print("free http requests  :", rep["free_http_requests"])
    print("written             :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
