"""PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001 -- Phase 8D: the destination-organisation roster
(Visit Lauderdale, the Greater Fort Lauderdale Convention & Visitors Bureau, visitlauderdale.com).

Visit Lauderdale is Broward County's official destination marketing organisation -- it markets all 31 Broward
municipalities together, which is one of the reasons this market is drawn at the county. Its own site is a
Simpleview CMS whose public listings service (``/includes/rest_v2/plugins_listings_listings/find/``) is the
same service the site's own "Places to Stay" pages call from the browser, with the same public page token the
site embeds in that page. robots.txt allows every user agent with ``Crawl-delay: 2``; this helper honours that
delay and reads the lodging category (``catid 49``) in pages of ten, halving the page whenever the
bureau's CDN refuses an oversized response.

A listing row carries the bureau's own record of the premises: name, street, city, ZIP, phone, latitude,
longitude, its "visit website" URL and the lodging subcategories the bureau assigned it (Airport Hotels, Beach
Hotels, Cruise Hotels, Downtown Hotels, Hotels/Motels, Luxury, Resorts, Boutique Properties, Waterfront Hotels,
Alternative Lodging, Vacation Rentals, Pet-Friendly, LGBT+, Florida Green Lodging).

WHAT A ROSTER ROW IS, AND WHAT IT IS NOT
-----------------------------------------
Tier-2 discovery and IDENTITY evidence. A bureau ZIP can be a mailing ZIP; a bureau phone can be a central
reservations line; a bureau website can be a brand home page. None of them keys a building on its own and none
admits one -- the property's own postal code joined to the corridor registry does that.

**The bureau's "Pet-Friendly" subcategory (value 307) is NEVER a pet policy and is never published.** It is
read here only so that the reconciliation can say how many of the bureau's own pet-friendly picks this market
independently verified on the property's own page, and so that a bureau pet-friendly listing that the census
never saw becomes a GAP CHALLENGE lead. The same is true of "Vacation Rentals" (848) and "Alternative Lodging"
(847): those subcategories are recorded as the bureau's own classification and are used as refusal EVIDENCE,
never as a refusal on their own.

Outputs:
  launch_packages/pettripfinder/markets/reports/fort_lauderdale_fl_destination_roster_001.json
  data/acquisition/fort_lauderdale_fl_roster_001/<sha256>.bin
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import fort_lauderdale_fl_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "fort-lauderdale-fl"
DOCS = os.path.join(_DASH, "data", "acquisition", "fort_lauderdale_fl_roster_001")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "fort_lauderdale_fl_destination_roster_001.json")

HOST = "https://www.visitlauderdale.com"
ENDPOINT = HOST + "/includes/rest_v2/plugins_listings_listings/find/"
REFERER = HOST + "/places-to-stay/hotels/"
ROBOTS = HOST + "/robots.txt"
#: The public page token the bureau's own "Places to Stay" page embeds and its own browser code sends.
PAGE_TOKEN = "47f351fe4c527f6394d792976c1400da"
LODGING_CATID = 49
CRAWL_DELAY_SECONDS = 2.5
#: The bureau's edge refuses a response over roughly 300 KB with HTTP 403 (measured: limit 10 = 292 KB OK,
#: limit 20 = 403). Ten listings per page is the largest page the service will actually serve.
PAGE_SIZE = 10
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

#: The bureau's own lodging subcategories, read from its own filter widget. Classification evidence only.
SUBCATEGORIES = OrderedDict([
    (257, "Airport Hotels"), (847, "Alternative Lodging"), (256, "Beach Hotels"), (822, "Boutique Properties"),
    (316, "Cruise Hotels"), (832, "Downtown Hotels"), (794, "Florida Green Lodging"), (290, "Hotels/Motels"),
    (260, "LGBT+"), (255, "Luxury"), (307, "Pet-Friendly"), (258, "Resorts"), (848, "Vacation Rentals"),
    (291, "Waterfront Hotels"),
])
#: Subcategories that are the bureau's own statement that a listing is NOT a hotel operation.
NON_HOTEL_SUBCATS = (848, 847)
#: The bureau's own pet-friendly pick. Identity / gap-challenge use ONLY -- never a policy, never published.
PET_FRIENDLY_SUBCAT = 307


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def persist(body):
    if not body:
        return None
    digest = _sha(body)
    os.makedirs(DOCS, exist_ok=True)
    p = os.path.join(DOCS, digest + ".bin")
    if not os.path.exists(p):
        with open(p, "wb") as fh:
            fh.write(body)
    return digest


def _get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            return resp.status, resp.read(), resp.geturl(), ""
    except urllib.error.HTTPError as exc:
        return exc.code, b"", url, "HTTP %s" % exc.code
    except Exception as exc:                                     # noqa: BLE001
        return "TRANSPORT", b"", url, "%s: %s" % (type(exc).__name__, exc)


def fetch_page(skip, limit):
    query = {"filter": {"categories.catid": {"$in": [LODGING_CATID]}},
             "options": {"limit": limit, "skip": skip, "count": True,
                         "sort": {"recid": 1}}}
    url = ENDPOINT + "?" + urllib.parse.urlencode(
        [("json", json.dumps(query, separators=(",", ":"))), ("token", PAGE_TOKEN)])
    status, body, final, detail = _get(url, {
        "User-Agent": USER_AGENT, "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9", "Referer": REFERER,
    })
    return url, status, body, final, detail


def _s(v):
    return " ".join(str(v or "").split())


def _zip5(v):
    digits = "".join(ch for ch in _s(v) if ch.isdigit())
    return digits[:5]


def _subcats(doc):
    """The lodging subcategory ids the bureau assigned this listing. The service returns categories as a flat
    list of {catid, subcatid, subcatname, catname, primary}."""
    out = []
    for cat in doc.get("categories") or []:
        if isinstance(cat, dict) and cat.get("catid") == LODGING_CATID and cat.get("subcatid") is not None:
            out.append(int(cat["subcatid"]))
    return sorted(set(out))


def _primary_subcat(doc):
    for cat in doc.get("categories") or []:
        if isinstance(cat, dict) and cat.get("catid") == LODGING_CATID and cat.get("primary"):
            return _s(cat.get("subcatname"))
    return ""


def build(limit_pages=None):
    """Read the whole lodging category, adapting the page size DOWN whenever the bureau's edge refuses a page.

    The refusal is a RESPONSE-SIZE refusal, not a rate limit: a listing document carries its whole media array
    (~25 KB each), so a ten-listing window that happens to hold image-rich listings crosses the edge's ~300 KB
    ceiling and comes back 403 while its neighbours at the same page size succeed. The answer is to halve the
    window for that offset and keep going -- never to retry the same request harder.
    """
    requests_made = 0
    pages, listings = [], []
    seen = set()
    total = None
    skip = 0
    while True:
        if limit_pages is not None and len(pages) >= limit_pages:
            break
        got = 0
        window = PAGE_SIZE
        status = None
        while True:
            if requests_made:
                time.sleep(CRAWL_DELAY_SECONDS)
            url, status, body, final, detail = fetch_page(skip, window)
            requests_made += 1
            digest = persist(body)
            page = OrderedDict([
                ("skip", skip), ("limit", window), ("status", status), ("returned", 0),
                ("bytes", len(body)), ("sha256", digest), ("detail", detail), ("request_url", url),
            ])
            if status == 200 and body:
                try:
                    payload = json.loads(body.decode("utf-8", "replace"))
                except ValueError:
                    payload = None
                if isinstance(payload, dict):
                    docs = (payload.get("docs") or {})
                    total = docs.get("count", total)
                    for doc in docs.get("docs") or []:
                        got += 1
                        recid = doc.get("recid")
                        if recid in seen:
                            continue
                        seen.add(recid)
                        zip5 = _zip5(doc.get("zip"))
                        city = _s(doc.get("city"))
                        klass, slug, why = GEO.classify_postal(zip5, city)
                        subs = _subcats(doc)
                        listings.append(OrderedDict([
                            ("lane", "DESTINATION_ROSTER_VISIT_LAUDERDALE"),
                            ("recid", recid),
                            ("name", _s(doc.get("title"))),
                            ("street", _s(doc.get("address1"))),
                            ("street2", _s(doc.get("address2"))),
                            ("city", city),
                            ("state", _s(doc.get("state"))),
                            ("postal_code", zip5),
                            ("postal_code_raw", _s(doc.get("zip"))),
                            ("phone", _s(doc.get("phone"))),
                            ("website", _s(doc.get("weburl"))),
                            ("latitude", doc.get("latitude")),
                            ("longitude", doc.get("longitude")),
                            ("bureau_region", _s(doc.get("regionname") or doc.get("region"))),
                            ("bureau_subcategory_ids", subs),
                            ("bureau_subcategories", [SUBCATEGORIES.get(s, "subcat_%d" % s) for s in subs]),
                            ("bureau_primary_subcategory", _primary_subcat(doc)),
                            ("bureau_calls_it_non_hotel", any(s in NON_HOTEL_SUBCATS for s in subs)),
                            ("bureau_pet_friendly_pick", PET_FRIENDLY_SUBCAT in subs),
                            ("geography_class", klass),
                            ("corridor_slug", slug),
                            ("membership_reason", why),
                            ("listing_url", (HOST + _s(doc.get("url"))) if doc.get("url") else ""),
                            ("snapshot_sha256", digest),
                            # --- the field spellings the census reader consumes (same values, roster vocabulary)
                            ("region", _s(doc.get("state"))),
                            ("stated_postal_code", zip5),
                            ("stated_phone", _s(doc.get("phone"))),
                            ("document_sha256", digest),
                            ("bureau_subcategory", _primary_subcat(doc)),
                            ("bureau_all_subcategories", [SUBCATEGORIES.get(s, "subcat_%d" % s) for s in subs]),
                            ("lat", doc.get("latitude")),
                            ("lng", doc.get("longitude")),
                        ]))
                page["returned"] = got
                pages.append(page)
                break
            pages.append(page)
            if status == 403 and window > 1:
                window = max(1, window // 2)      # a size refusal: halve the window, never retry it harder
                continue
            break
        skip += window
        if total is not None and skip >= total:
            break
        if got == 0 and status != 403:
            break
    listings.sort(key=lambda r: (r["postal_code"], r["street"].upper(), r["name"].upper()))
    admitted = [r for r in listings if r["geography_class"] != "OUTSIDE"]
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "8D -- Visit Lauderdale (Greater Fort Lauderdale CVB) lodging roster"),
        ("source", HOST),
        ("endpoint", ENDPOINT),
        ("robots_txt", ROBOTS),
        ("robots_rule", "User-agent: * / Allow: / / Crawl-delay: 2 -- honoured (%.1f s between requests)."
                        % CRAWL_DELAY_SECONDS),
        ("terms", "The bureau's own public listings service, called with the bureau's own public page token as its "
                  "own Places to Stay page calls it, at the crawl delay its robots.txt asks for. No crawl of the "
                  "listing pages was needed."),
        ("edge_behaviour",
         "The bureau's CDN refuses any response over roughly 300 KB with HTTP 403. This is a RESPONSE-SIZE "
         "refusal, not a rate limit: at the same page size some offsets succeed and their image-rich neighbours "
         "do not. This lane halves its page size for the offending offset and continues; it never retries a "
         "refused request unchanged and never attempts to defeat the control."),
        ("category", OrderedDict([("catid", LODGING_CATID), ("label", "Places to Stay"),
                                  ("subcategories", OrderedDict((str(k), v) for k, v in SUBCATEGORIES.items()))])),
        ("a_roster_row_is_not_a_policy",
         "Tier-2 discovery and identity evidence only. The bureau's 'Pet-Friendly' subcategory (307) is NEVER a pet "
         "policy, is never published, and is used only to challenge this market's own coverage. 'Vacation Rentals' "
         "(848) and 'Alternative Lodging' (847) are the bureau's own classification and are refusal EVIDENCE, "
         "never a refusal on their own."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", requests_made),
        ("pages", pages),
        ("pages_refused_by_size", sum(1 for p in pages if p["status"] == 403)),
        ("total_reported_by_bureau", total),
        ("listing_count", len(listings)),
        ("roster_complete", bool(total is not None and len(listings) >= total)),
        ("listing_count_admitted_postal_codes", len(admitted)),
        ("listing_count_outside", len(listings) - len(admitted)),
        ("by_corridor", OrderedDict(sorted(Counter(r["corridor_slug"] for r in admitted).items()))),
        ("by_geography_class", OrderedDict(sorted(Counter(r["geography_class"] for r in listings).items()))),
        ("by_bureau_subcategory", OrderedDict(sorted(
            ((SUBCATEGORIES.get(s, "subcat_%d" % s), sum(1 for r in listings if s in r["bureau_subcategory_ids"]))
             for s in SUBCATEGORIES), key=lambda kv: -kv[1]))),
        ("bureau_pet_friendly_picks", sum(1 for r in listings if r["bureau_pet_friendly_pick"])),
        ("bureau_pet_friendly_picks_admitted", sum(1 for r in admitted if r["bureau_pet_friendly_pick"])),
        ("bureau_non_hotel_listings", sum(1 for r in listings if r["bureau_calls_it_non_hotel"])),
        ("listings_with_website", sum(1 for r in listings if r["website"])),
        ("bureaus", OrderedDict([
            ("visit_lauderdale", OrderedDict([
                ("name", "Visit Lauderdale (Greater Fort Lauderdale Convention & Visitors Bureau)"),
                ("host", HOST),
                ("endpoint", ENDPOINT),
                ("listing_count", len(listings)),
                ("listings", listings),
            ])),
        ])),
        ("listings", listings),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit-pages", type=int, default=None)
    args = ap.parse_args(argv)
    rep = build(limit_pages=args.limit_pages)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", rep["listing_count"], "admitted:", rep["listing_count_admitted_postal_codes"],
          "outside:", rep["listing_count_outside"], "requests:", rep["free_http_requests"])
    print("by corridor:", json.dumps(rep["by_corridor"]))
    print("bureau pet-friendly picks:", rep["bureau_pet_friendly_picks"],
          "non-hotel:", rep["bureau_non_hotel_listings"], "with website:", rep["listings_with_website"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
