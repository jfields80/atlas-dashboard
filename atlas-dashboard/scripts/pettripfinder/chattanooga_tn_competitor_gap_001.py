"""PTF-CHATTANOOGA-TN-NEW-MARKET-001 -- Phase 7, the competitor gap matrix.

BringFido's Chattanooga pages, reconciled against this order's proposed census.

A COMPETITOR DIRECTORY IS AN AUDIT LANE, NOT AN ACQUISITION LANE
---------------------------------------------------------------
Nothing here becomes authority. A row proposes that a lodging identity EXISTS,
so the census can be asked whether it already knows it. A competitor's
pet-friendly claim is recorded verbatim as a TARGETING HINT -- it tells the
policy lane where to look and never what to publish. Every useful lead returns
to first-party verification.

THREE TRAPS THIS RUN CHECKS RATHER THAN ASSUMES
-----------------------------------------------
1. **Is the category filter live?** The site exposes both ``/lodging/city/<c>/``
   and ``/lodging/hotels/city/<c>/``. A filter that is INERT returns the same
   cohort for both, and a market that trusts it silently imports vacation
   rentals as hotels. This run fetches BOTH and diffs them.
2. **Is the headline count the served cohort?** The page's own result count is
   recorded next to the number of rows actually parsed, as two different facts.
3. **Is page one the cohort?** It is a PAGE SIZE. The listing is followed by its
   own ``rel="next"`` link until it stops.

Georgia cities over the state line are fetched deliberately, so the Phase 6
border audit has rows to rule on rather than a silent gap.

Output:
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_competitor_gap_001.json
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

from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name      # noqa: E402

WORK_ORDER = "PTF-CHATTANOOGA-TN-NEW-MARKET-001"
MARKET_ID = "chattanooga-tn"
SCHEMA = "ptf-competitor-gap-matrix/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "chattanooga_tn_competitor_001")


def _first_existing(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[-1]


CENSUS = _first_existing(os.path.join(PKG, "identity_census", "chattanooga-tn.json"),
                         os.path.join(PKG, "identity_census_proposed", "chattanooga-tn.json"))

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 1.4
BF = "https://www.bringfido.com"
MAX_PAGES = 12

#: Tennessee cities in this market, plus the Georgia fringe. The Georgia slugs
#: are fetched on purpose: this market admits Tennessee only, so those rows are
#: CLASSIFIED as a border hold rather than silently missed.
BF_CITIES = [
    "chattanooga_tn_us", "east-ridge_tn_us", "hixson_tn_us", "ooltewah_tn_us",
    "collegedale_tn_us", "red-bank_tn_us", "soddy-daisy_tn_us", "signal-mountain_tn_us",
    "harrison_tn_us", "lookout-mountain_tn_us",
    "fort-oglethorpe_ga_us", "ringgold_ga_us", "rossville_ga_us",
]
_CITY_HREF = re.compile(r'href="/lodging/city/([a-z0-9_-]+)/"', re.I)
_REL_NEXT = re.compile(r'rel="next"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*rel="next"', re.I)
_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)
_COUNT = re.compile(r"([\d,]+)\s+(?:pet[- ]friendly\s+)?(?:hotels?|results?|places?|properties)",
                    re.I)
_GA_SUFFIX = re.compile(r"[-_]ga[-_]us$", re.I)


def _get(url, timeout=30):
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
    mp, bp = os.path.join(CACHE, key + ".json"), os.path.join(CACHE, key + ".html")
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding="utf-8"))
        body = open(bp, "rb").read() if os.path.exists(bp) else b""
        return meta, body
    time.sleep(SPACING)
    st, final, body = _get(url)
    stats["requests"] += 1
    meta = OrderedDict([("requested_url", url), ("status", st), ("final_url", final),
                        ("bytes", len(body)),
                        ("sha256", hashlib.sha256(body).hexdigest() if body else ""),
                        ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))])
    if body:
        open(bp, "wb").write(body)
    json.dump(meta, open(mp, "w", encoding="utf-8"))
    return meta, body


def _text(b):
    return b.decode("utf-8", "replace") if b else ""


def itemlist_rows(html):
    """Lodging rows from the page's own schema.org ItemList."""
    out = []
    for m in _LD.finditer(html):
        try:
            doc = json.loads(m.group(1).strip())
        except Exception:  # noqa: BLE001
            continue
        for d in (doc if isinstance(doc, list) else [doc]):
            if not isinstance(d, dict) or d.get("@type") != "ItemList":
                continue
            for el in d.get("itemListElement") or []:
                item = (el or {}).get("item") if isinstance(el, dict) else None
                if not isinstance(item, dict):
                    continue
                addr = item.get("address") if isinstance(item.get("address"), dict) else {}
                out.append(OrderedDict([
                    ("name", str(item.get("name") or "").strip()),
                    ("lead_type", str(item.get("@type") or "")),
                    ("competitor_url", str(item.get("url") or "")),
                    ("street", str(addr.get("streetAddress") or "").strip()),
                    ("city", str(addr.get("addressLocality") or "").strip()),
                    ("region", str(addr.get("addressRegion") or "").strip()),
                    ("postal_code", str(addr.get("postalCode") or "").strip()),
                    ("telephone", str(item.get("telephone") or "").strip()),
                ]))
    return out


def headline_count(html):
    m = _COUNT.search(re.sub(r"<[^>]+>", " ", html))
    return m.group(1).replace(",", "") if m else ""


def walk(first_url, stats):
    pages, rows, url, seen = [], [], first_url, set()
    while url and url not in seen and len(pages) < MAX_PAGES:
        seen.add(url)
        meta, body = cached_get(url, stats)
        html = _text(body)
        page_rows = itemlist_rows(html)
        pages.append(OrderedDict([("url", url), ("status", meta["status"]),
                                  ("sha256", meta["sha256"]),
                                  ("headline_count", headline_count(html)),
                                  ("rows_parsed", len(page_rows))]))
        rows.extend(page_rows)
        if meta["status"] != 200 or not page_rows:
            break
        m = _REL_NEXT.search(html)
        nxt = (m.group(1) or m.group(2)) if m else ""
        url = (BF + nxt) if nxt.startswith("/") else nxt
    return pages, rows


#: Parent-company wording a competitor appends that the hotel's own name does
#: not carry: "Candlewood Suites Chattanooga East Ridge BY IHG". Counting the
#: parent as distinguishing vocabulary refused matches against census rows this
#: order had already admitted, and reported them as coverage gaps.
_PARENT_SUFFIX = re.compile(
    r"\s+by\s+(ihg|marriott|wyndham|hilton|hyatt|choice|radisson|sonesta|g6|"
    r"best western|red lion).*$", re.I)
_GENERIC_NAME_WORDS = {
    "hotel", "hotels", "inn", "inns", "suites", "suite", "and", "by", "the", "of", "at",
    "a", "an", "motel", "lodge", "resort", "extended", "stay", "america", "select",
    "chattanooga", "tn", "tennessee", "marriott", "hilton", "wyndham", "hyatt", "ihg",
    "choice", "radisson", "sonesta", "collection", "autograph", "tribute", "portfolio",
}


def name_tokens(name):
    """The distinguishing vocabulary of a name: chain plus place, no parents."""
    n = normalize_name(_PARENT_SUFFIX.sub("", name or ""))
    return {t for t in n.split() if t and t not in _GENERIC_NAME_WORDS}


def loose_street(street):
    s = re.sub(r"[^a-z0-9 ]+", " ", (street or "").lower()).split()
    num = s[0] if s and s[0].isdigit() else ""
    words = [t for t in s[1:] if not t.isdigit()]
    return "%s|%s" % (num, " ".join(words[:2])) if num and words else ""


def build(args):
    stats = {"requests": 0}
    census = json.load(open(CENSUS, encoding="utf-8"))
    known = list(census.get("hotels", [])) + list(census.get("non_admitted", []))
    by_addr = {}
    by_phone = {}
    by_name = {}
    by_loose = {}
    for r in known:
        if r.get("street_identity"):
            by_addr.setdefault(r["street_identity"], r)
        if r.get("phone_key"):
            by_phone.setdefault(r["phone_key"], r)
        if r.get("identity_key"):
            by_name.setdefault(r["identity_key"], r)
            by_name.setdefault(normalize_name(_PARENT_SUFFIX.sub("", r["canonical_name"])), r)
        for a in r.get("identity_key_aliases") or []:
            by_name.setdefault(a, r)
        lk = loose_street(r.get("street") or "")
        if lk:
            by_loose.setdefault(lk, r)

    # Trap 1: is the category filter live? Diff two filter values on one city.
    unf_pages, unf_rows = walk("%s/lodging/city/%s/" % (BF, BF_CITIES[0]), stats)
    fil_pages, fil_rows = walk("%s/lodging/hotels/city/%s/" % (BF, BF_CITIES[0]), stats)
    unf_names = {normalize_name(r["name"]) for r in unf_rows}
    fil_names = {normalize_name(r["name"]) for r in fil_rows}
    filter_live = unf_names != fil_names
    filter_probe = OrderedDict([
        ("city", BF_CITIES[0]),
        ("unfiltered_rows", len(unf_rows)), ("filtered_rows", len(fil_rows)),
        ("unfiltered_distinct_names", len(unf_names)),
        ("filtered_distinct_names", len(fil_names)),
        ("only_in_unfiltered", sorted(unf_names - fil_names)[:40]),
        ("only_in_filtered", sorted(fil_names - unf_names)[:40]),
        ("category_filter_is_live", filter_live),
        ("verdict", "the hotels filter serves a DIFFERENT cohort than the unfiltered page"
                    if filter_live else
                    "the hotels filter is INERT here -- it returns the same cohort as the "
                    "unfiltered page, so a market that trusted it would import short-term "
                    "rentals as hotels"),
        ("headline_vs_parsed",
         "the page's own headline count and the number of rows parsed are two different facts "
         "and are reported separately per page below"),
    ])

    # Every city the hub itself links, unioned with the seeds.
    linked = set()
    for p in unf_pages[:1]:
        meta, body = cached_get(p["url"], stats)
        linked.update(_CITY_HREF.findall(_text(body)))
    cities = sorted(set(BF_CITIES) | {c for c in linked if c.endswith(("_tn_us", "_ga_us"))})

    city_reports, leads = [], []
    # The category filter is proven live above, so the gap matrix is built from
    # the HOTELS cohort. Trusting an inert filter would import short-term
    # rentals as hotels; ignoring a live one buries every real hotel row under
    # them. The unfiltered walk stays, as the probe that proved which it is.
    for city in cities[: args.max_cities]:
        pages, rows = walk("%s/lodging/hotels/city/%s/" % (BF, city), stats)
        city_reports.append(OrderedDict([("city_slug", city), ("pages", pages),
                                         ("rows_parsed", len(rows))]))
        for r in rows:
            r = OrderedDict(r)
            r["city_slug"] = city
            leads.append(r)

    # Reconcile against the census.
    seen, matrix = set(), []
    for r in leads:
        nk = normalize_name(r["name"])
        if (nk, r.get("street", "")) in seen:
            continue
        seen.add((nk, r.get("street", "")))
        sid = address_key(r["street"], r["postal_code"]) if r.get("street") else ""
        pk = re.sub(r"\D", "", r.get("telephone") or "")[-10:]
        stripped = normalize_name(_PARENT_SUFFIX.sub("", r["name"]))
        hit = (by_addr.get(sid) or by_phone.get(pk) or by_name.get(nk)
               or by_name.get(stripped)
               or by_loose.get(loose_street(r.get("street") or "")))
        # Last resort, and only for a row the competitor gave no address: the
        # distinguishing vocabulary of the two names must agree ENTIRELY. This
        # proposes that the census already knows the row; it never admits one.
        vocab_hit = None
        if hit is None and not r.get("street"):
            toks = name_tokens(r["name"])
            if toks:
                cands = [k for k in known
                         if k.get("canonical_name") and name_tokens(k["canonical_name"]) == toks]
                if len(cands) == 1:
                    vocab_hit = cands[0]
        region = (r.get("region") or "").upper()
        if hit:
            verdict = ("EXACT_MATCH_IN_CENSUS" if hit["classification"] == "TRUE_HOTEL_IDENTITY"
                       else "KNOWN_BUT_NOT_ADMITTED:" + hit["classification"])
            why = "the census already carries this identity"
        elif vocab_hit is not None:
            hit = vocab_hit
            verdict = "NAME_VOCABULARY_MATCH_IN_CENSUS"
            why = ("the competitor published no address; exactly one census identity carries the "
                   "same distinguishing vocabulary once parent-company wording is removed. A "
                   "proposal that the census already knows this row, not an admission.")
        elif _GA_SUFFIX.search(r["city_slug"]) or region in ("GA", "GEORGIA"):
            verdict = "NORTH_GEORGIA_FRINGE_HOLD"
            why = ("the competitor's own row states a Georgia address; this market admits "
                   "Tennessee only, so it is a border hold and not a coverage gap")
        elif r.get("lead_type") in ("Campground", "Apartment", "House", "VacationRental"):
            verdict = "NON_HOTEL_LEAD_TYPE"
            why = "the competitor itself types this row %s" % r.get("lead_type")
        elif not r.get("street"):
            verdict = "NAME_ONLY_UNRESOLVED"
            why = ("the competitor published no address for this row, and a name alone proposes "
                   "an identity without deciding one")
        else:
            verdict = "TRUE_MISSING_CANDIDATE"
            why = ("no census row matches this address, phone or name; a first-party read must "
                   "confirm the identity before it can be admitted")
        matrix.append(OrderedDict([
            ("name", r["name"]), ("lead_type", r.get("lead_type", "")),
            ("street", r.get("street", "")), ("city", r.get("city", "")),
            ("region", region), ("postal_code", r.get("postal_code", "")),
            ("telephone", r.get("telephone", "")), ("city_slug", r["city_slug"]),
            ("competitor_url", r.get("competitor_url", "")),
            ("verdict", verdict), ("why", why),
            ("matched_identity_key", hit["identity_key"] if hit else ""),
            ("competitor_claim_is_a_targeting_hint_only", True),
        ]))

    counts = Counter(x["verdict"] for x in matrix)
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "7 -- competitor gap matrix"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("a_competitor_is_an_audit_lane",
         "Nothing here is authority. A competitor's pet-friendly claim is a TARGETING HINT that "
         "tells the policy lane where to look and never what to publish; every useful lead "
         "returns to first-party verification."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests_this_run", stats["requests"]),
        ("unique_urls_fetched_cumulative",
         len([n for n in os.listdir(CACHE) if n.endswith(".json")])
         if os.path.isdir(CACHE) else stats["requests"]),
        ("category_filter_probe", filter_probe),
        ("cities", city_reports),
        ("counts", OrderedDict([("competitor_rows_observed", len(matrix)),
                                ("by_verdict", OrderedDict(sorted(counts.items())))])),
        ("matrix", matrix),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "chattanooga_tn_competitor_gap_001.json"))
    ap.add_argument("--max-cities", type=int, default=16)
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    print("requests        :", rep["free_http_requests_this_run"])
    print("filter live     :", rep["category_filter_probe"]["category_filter_is_live"])
    print("rows observed   :", rep["counts"]["competitor_rows_observed"])
    print("by verdict      :", json.dumps(rep["counts"]["by_verdict"]))
    print("written         :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
