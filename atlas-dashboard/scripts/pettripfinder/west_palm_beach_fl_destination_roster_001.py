"""PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 -- Phase 7C: the destination-organisation roster
(Discover The Palm Beaches, thepalmbeaches.com) -- a NAME-ONLY lane, and why.

Discover The Palm Beaches is Palm Beach County's official destination marketing organisation: it markets all
39 county municipalities together under one brand, which is one of the reasons this market is drawn at the
county line. Fort Lauderdale's equivalent lane (Visit Lauderdale, a Simpleview CMS with a public listings REST
service) returned 376 listings, 370 in admitted codes and 360 WITH A WEBSITE -- the single biggest routing win
of that build. This bureau is not that, and the difference was measured rather than assumed.

WHAT THIS LANE ACTUALLY GOT, AND WHAT IT DID NOT
--------------------------------------------------
  * robots.txt ALLOWS every agent except /wp-login.php, /search/*, /feed/*, /tag/*, /wp-admin/ and -- for every
    agent -- /*? (any query string). This lane honours that: it reads only path URLs the bureau's own sitemap
    publishes and never constructs a query string.
  * A PLAIN CLIENT IS REFUSED OUTRIGHT. Every path, including /sitemap_index.xml which robots.txt explicitly
    allows, returns HTTP 403 to urllib with full browser headers.
  * WordPress with its REST API DISABLED: /wp-json/wp/v2/types -> {"code":"rest_no_route"}. There is no
    listings service to call, and no lodging-only index reachable without a query string.
  * THROUGH THE AUTHORIZED FIRECRAWL RENDERER the three SITEMAPS read cleanly (3 credits): 3,125 listing URLs,
    of which 624 are the English listings and the rest their es / fr / de / pt translations.
  * THE INDIVIDUAL LISTING PAGES CARRY NO PREMISES DATA THIS LANE CAN READ. Measured on this market's own
    pages, not inherited:
      - profile ``rawHtml`` (the routed profile, waitFor 6000 / timeout 90000): HTTP 408 SCRAPE_TIMEOUT on
        every listing attempted -- 88 Palms, Aloft Delray Beach, Amrit Ocean Resort. The bureau's listing
        pages are ~205 KB behind a loader and do not settle.
      - profile ``rawHtml`` with waitFor 0 / timeout 60000: HTTP 408 SCRAPE_TIMEOUT.
      - profile ``markdown`` with onlyMainContent: returns HTTP 200 in ~6 s for 1 credit -- and the document
        contains the listing's NAME, its description, its amenity chips and its "related listings", and NO
        street address, NO postal code, NO telephone and NO outbound website link. The bureau renders all four
        client-side from its Simpleview CRM (its images are served from
        assets.simpleviewinc.com/.../crm/palmbeach/), which this order has no authorization to call.

    Reading all 624 listing pages would therefore cost 624 credits and return NOT ONE street, postal code,
    phone or website. That is not a bounded cost for a real gain, so it is not done. The bureau contributes
    what it actually has that this order can read: NAMES.

WHAT A ROSTER NAME IS, AND WHAT IT IS NOT
-------------------------------------------
Tier-3 discovery evidence, the same standing as a competitor lead: a NAME and the bureau's own listing URL.
A name proposes an identity and never decides one, never keys a building and never admits one -- the
property's own postal code joined to the corridor registry does that. Every name here must be confirmed by
this market's own lanes (the DBPR licensed premises, a brand's own inventory, a map row or a first-party
read) before it can become a census row, and a name this market never independently confirms stays a GAP
CHALLENGE lead, counted and explained, never published.

**A bureau amenity chip is NEVER a pet policy.** The bureau tags many listings "Pet-Friendly". That tag is
not read into any policy field, is not evidence, and is never published. It is recorded on the lane only so
the competitor/gap reconciliation can say how many of the bureau's own pet-friendly picks this market
independently verified on the property's own page.

Outputs:
  launch_packages/pettripfinder/markets/reports/west_palm_beach_fl_destination_roster_001.json
  data/acquisition/west_palm_beach_fl_roster_001/<sha256>.html   (sitemap cache, gitignored)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "west-palm-beach-fl"
HOST = "https://www.thepalmbeaches.com"
DOCS = os.path.join(_DASH, "data", "acquisition", "west_palm_beach_fl_roster_001")
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
OUT = os.path.join(REPORTS, "west_palm_beach_fl_destination_roster_001.json")
SITEMAPS = (HOST + "/sitemap_index.xml", HOST + "/listing-sitemap1.xml", HOST + "/listing-sitemap2.xml")

#: A listing slug that reads as lodging. A LEAD FILTER ONLY -- it never admits or types anything.
_LODGING_SLUG = re.compile(
    r"hotel|motel|inn\b|-inn|resort|suites|lodge|hostel|bed-and-breakfast|guesthouse|guest-house|"
    r"marriott|hilton|hyatt|hampton|courtyard|residence-inn|westin|sheraton|holiday|comfort|quality-|"
    r"wyndham|ramada|embassy|doubletree|homewood|springhill|towneplace|fairfield|aloft|kimpton|opal|"
    r"eau-|breakers|colony|seagate|tideline|singer|amrit|four-seasons|ritz|waldorf|canopy|tru-by|home2|"
    r"extended-stay|red-roof|la-quinta|best-western|sonesta|drift-|white-elephant|vineta|ben-west-palm|"
    r"bradley-park|brazilian-court|chesterfield|boca-raton-resort|pga-national|jupiter-beach|"
    r"wellington-national|hutchinson|casa-grandview|sailfish|pelican|aka-west-palm|hotel-aka")
#: Slugs that read as lodging but name a restaurant, spa, shop, club, museum or civic page inside or near one.
_NOT_A_PROPERTY = re.compile(
    r"^(city-of-|town-of-|village-of-|american-german-club|benzaiten|bissingers|boca-raton-museum|"
    r"celis-|bella-reina|beldi-|bennys-|boca-brasserie|cafe-|restaurant-|spa-at-|golf-at-)|"
    r"(-museum|-brasserie|-juice-bar|-chocolate|-golf-course|-country-club-course|-event-center-rental)$")

#: The measured refusals, recorded as the lane's own evidence. Each was run against THIS market's pages.
PROFILE_ATTEMPTS = [
    OrderedDict([("profile", "rawHtml, waitFor 6000, timeout 90000 (the committed ROUTED profile)"),
                 ("listings_attempted", 3),
                 ("outcome", "HTTP 408 SCRAPE_TIMEOUT on every attempt"),
                 ("credits_charged", 0),
                 ("note", "Firecrawl cost is bimodal: a refused scrape charges nothing.")]),
    OrderedDict([("profile", "rawHtml, waitFor 0, timeout 60000"),
                 ("listings_attempted", 1),
                 ("outcome", "HTTP 408 SCRAPE_TIMEOUT"),
                 ("credits_charged", 0),
                 ("note", "")]),
    OrderedDict([("profile", "markdown, waitFor 0, timeout 45000, onlyMainContent"),
                 ("listings_attempted", 2),
                 ("outcome", "HTTP 200 -- but the document carries NO street, NO postal code, NO telephone "
                             "and NO outbound website link; the bureau renders all four client-side from its "
                             "Simpleview CRM"),
                 ("credits_charged", 2),
                 ("note", "This is why the lane is name-only: 624 further credits would buy 0 premises data.")]),
]


def _s(v):
    return " ".join(str(v or "").split())


def _cache_path(url):
    return os.path.join(DOCS, hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html")


def _read_sitemap(url, allow_fetch):
    """Cached Firecrawl read of ONE sitemap. Returns (text, from_cache, credits_used).

    The cache path is joined INLINE from this module's own DOCS constant on the WRITE side rather than taken
    from ``_cache_path``, because the market-local isolation prover must resolve every write target
    STATICALLY. A path that arrives from a function call is "a bare root plus a dynamic tail", which it
    refuses -- and that single unresolvable write cost this registration its narrowing on the first packet
    run: the whole 94-path change set fell back to a broad classification over it. Reads are not proven, so
    the helper is still used above. ``west_palm_beach_fl_brand_inventory_001.persist`` already writes this
    way, which is why that module classified MARKET_LOCAL and this one did not.
    """
    p = _cache_path(url)
    if os.path.exists(p):
        return open(p, "r", encoding="utf-8", errors="replace").read(), True, 0
    if not allow_fetch:
        return "", False, 0
    from scripts.pettripfinder.acquisition import firecrawl_capture as FC
    os.makedirs(DOCS, exist_ok=True)
    r = FC.fetch(url)
    h = r.get("html") or ""
    out_path = os.path.join(DOCS, hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html")
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(h)
    return h, False, (r.get("credits_used") or 0)


def _display_name(slug):
    words = [w for w in slug.split("-") if w]
    small = {"by", "at", "of", "the", "on", "and", "in"}
    out = []
    for i, w in enumerate(words):
        out.append(w if (w in small and i) else (w.upper() if w in ("pga", "aka", "jw") else w.capitalize()))
    return " ".join(out)


def build(allow_fetch=True):
    listing_urls, credits, cached, fetched = [], 0, 0, 0
    for sm in SITEMAPS:
        h, from_cache, cu = _read_sitemap(sm, allow_fetch)
        credits += cu
        cached += 1 if from_cache else 0
        fetched += 0 if from_cache else 1
        if sm != SITEMAPS[0]:
            listing_urls.extend(re.findall(r"<loc>(.*?)</loc>", h))

    english = sorted({u for u in listing_urls
                      if "/listing/" in u and not re.match(r"https://[^/]+/(es|fr|de|pt)/", u)})
    leads = []
    for u in english:
        slug = u.rsplit("/", 1)[1]
        if _NOT_A_PROPERTY.search(slug):
            continue
        if not _LODGING_SLUG.search(slug):
            continue
        leads.append(OrderedDict([
            ("lane", "DESTINATION_ROSTER_NAME_ONLY"),
            ("name", _display_name(slug)),
            ("slug", slug),
            ("listing_url", u),
            ("evidence_tier", 3),
            ("what_this_is", "A NAME and the bureau's own listing URL. No street, no postal code, no phone, "
                             "no website -- the bureau publishes none of them in any document this lane can "
                             "read. A name proposes an identity and never decides one."),
        ]))
    leads.sort(key=lambda r: r["slug"])

    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "7C -- Discover The Palm Beaches, the county destination marketing organisation "
                  "(NAME-ONLY lane)"),
        ("host", HOST),
        ("lane_class", "NAME_ONLY_DISCOVERY"),
        ("platform", "WordPress with the REST API disabled (/wp-json/wp/v2/types -> rest_no_route), a "
                     "Simpleview CRM behind it (images served from assets.simpleviewinc.com/.../crm/palmbeach/) "
                     "that this order has no authorization to call, and a bot wall that refuses a plain client "
                     "with HTTP 403 on every path"),
        ("robots",
         "robots.txt allows every agent except /wp-login.php, /search/*, /feed/*, /tag/*, /wp-admin/ and "
         "/*? (any query string). This lane reads ONLY path URLs published in the bureau's own sitemap and "
         "never constructs a query string, so no disallowed path is requested."),
        ("plain_client_result", "HTTP 403 on every path, including /sitemap_index.xml which robots.txt allows"),
        ("access_lane", "FIRECRAWL (existing authorized capacity, existing plan credits; no new provider, no "
                        "new key, no new plan, USD 0.00)"),
        ("why_name_only", OrderedDict([
            ("finding", "The bureau's individual listing pages carry NO street address, NO postal code, NO "
                        "telephone and NO outbound website link in any document this lane can read. It "
                        "renders all four client-side from its Simpleview CRM."),
            ("profiles_attempted", PROFILE_ATTEMPTS),
            ("cost_of_reading_all_624_listing_pages", "624 credits for 0 streets, 0 postal codes, 0 phones "
                                                      "and 0 websites -- not a bounded cost for a real gain"),
            ("decision", "NOT DONE. The lane contributes NAMES, which is what the bureau actually publishes "
                         "that this order can read."),
            ("contrast_with_fort_lauderdale",
             "Visit Lauderdale (Simpleview CMS, public listings REST service) returned 376 listings with 360 "
             "websites and was that build's biggest routing win. The difference between the two bureaus was "
             "MEASURED here, not assumed, and the routing gap is covered instead by Google Places route "
             "discovery on the existing key."),
        ])),
        ("a_bureau_tag_is_not_a_policy",
         "The bureau tags many listings 'Pet-Friendly'. That amenity chip is not read into any policy field, "
         "is not evidence, and is never published. No bureau pet text is stored by this lane at all."),
        ("a_roster_name_is_not_an_admission",
         "Tier-3 discovery evidence, the same standing as a competitor lead. Every name must be confirmed by "
         "this market's own lanes -- the DBPR licensed premises, a brand's own inventory, a map row or a "
         "first-party read -- before it can become a census row."),
        ("paid_provider_calls", fetched), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("firecrawl_credits_used_this_run", credits),
        ("firecrawl_credits_used_total_for_this_lane", 5),
        ("cache_dir", "data/acquisition/west_palm_beach_fl_roster_001"),
        ("sitemaps_from_cache", cached),
        ("sitemaps_fetched", fetched),
        ("listing_urls_in_sitemaps", len(listing_urls)),
        ("english_listings", len(english)),
        ("lodging_named_leads", len(leads)),
        ("leads", leads),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--no-fetch", action="store_true", help="cache only; spend nothing")
    args = ap.parse_args(argv)
    rep = build(allow_fetch=not args.no_fetch)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("sitemap urls=%d  english listings=%d  lodging-named leads=%d  credits_this_run=%d (lane total 5)" % (
        rep["listing_urls_in_sitemaps"], rep["english_listings"], rep["lodging_named_leads"],
        rep["firecrawl_credits_used_this_run"]))
    print("lane class:", rep["lane_class"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
