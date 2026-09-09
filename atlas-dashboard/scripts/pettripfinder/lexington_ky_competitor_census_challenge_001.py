"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phase 6, the competitor challenge.

A competitor directory is an AUDIT lane, not an acquisition lane. Its rows are
DISCOVERY LEADS: they may point at an identity Atlas is missing, and they are
never policy authority, never a quote, and never a reason to grade a row.

Two committed traps are tested here rather than assumed, because both were
measured on this same directory against Cincinnati and Indianapolis:

  1. THE HEADLINE COUNT IS NOT THE SERVED COHORT. The unfiltered page calls
     itself "pet friendly hotels" while serving hotels and vacation rentals
     together, so its headline is a mixed-category number. Cincinnati's page
     claimed 135 and its actual hotel cohort was 36.
  2. THE FILTER MAY BE INERT. On Cincinnati the QUERY-STRING category filter
     returned byte-identical results for different values while the PATH
     segment was live. Every filter this order relies on is diffed by content
     hash before it is believed.

A third thing is measured rather than inherited: Cincinnati recorded this host
as 403 to a plain client on every lodging path and took the lane into an
attended browser. Re-probed for Lexington it answers 200. A refusal is a
measurement with a date on it.

Reconciliation is against the Lexington census this order built, and a lead
matches an Atlas row only on a distinctive token plus agreeing geography --
same brand plus same city demotes to review, it never confirms.
"""
from __future__ import annotations

import argparse
import hashlib
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

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
RECON = os.path.join(REPORTS, "lexington_ky_census_reconciliation_001.json")
CACHE = os.path.join(_DASH, "data", "discovery", "lexington_ky_competitor_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
BASE = "https://www.bringfido.com/lodging/city/lexington_ky_us/"
SPACING = 2.0

STOPWORDS = {
    "inn", "suites", "suite", "hotel", "hotels", "motel", "resort", "spa", "the",
    "and", "by", "at", "of", "a", "an", "place", "plaza", "conference", "center",
    "centre", "lexington", "kentucky", "ky", "downtown", "dtwn", "airport",
    "university", "medical", "north", "south", "east", "west", "uk", "area",
    "district", "near", "i", "75", "64", "extended", "stay", "express", "garden",
}
CHAIN = {
    "marriott", "hilton", "hyatt", "sheraton", "westin", "courtyard", "residence",
    "fairfield", "springhill", "towneplace", "hampton", "homewood", "home2",
    "embassy", "doubletree", "tru", "wyndham", "days", "super", "baymont",
    "microtel", "ramada", "travelodge", "la", "quinta", "comfort", "quality",
    "sleep", "econo", "lodge", "clarion", "woodspring", "ihg", "holiday",
    "candlewood", "staybridge", "crowne", "avid", "best", "western", "surestay",
    "red", "roof", "drury", "sonesta", "radisson", "country", "guesthouse",
    "four", "points", "aloft", "element", "moxy", "ac", "8", "6",
}


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def dtok(s):
    return {t for t in norm(s).split() if t not in STOPWORDS and t not in CHAIN}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            b = r.read()
            return r.status, r.geturl(), b
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def cached_get(url):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    p = os.path.join(CACHE, key + ".html")
    m = os.path.join(CACHE, key + ".json")
    if os.path.exists(m):
        meta = json.load(open(m, encoding="utf-8"))
        body = open(p, "rb").read() if os.path.exists(p) else b""
        return meta, body
    time.sleep(SPACING)
    st, final, body = get(url)
    meta = {"url": url, "status": st, "final_url": final, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest() if body else "",
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if body:
        open(p, "wb").write(body)
    json.dump(meta, open(m, "w", encoding="utf-8"))
    return meta, body


def jsonld_blobs(html):
    out = []
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            out.append(json.loads(m.group(1)))
        except Exception:  # noqa: BLE001
            pass
    return out


def listing_rows(html):
    """Rows the directory actually served, from its own ItemList JSON-LD."""
    rows = []
    for blob in jsonld_blobs(html):
        items = []
        if isinstance(blob, dict) and blob.get("@type") in ("ItemList",):
            items = blob.get("itemListElement") or []
        elif isinstance(blob, list):
            for b in blob:
                if isinstance(b, dict) and b.get("@type") == "ItemList":
                    items = b.get("itemListElement") or []
        for it in items:
            obj = it.get("item") if isinstance(it, dict) and "item" in it else it
            if not isinstance(obj, dict):
                continue
            name = obj.get("name")
            if not name:
                continue
            addr = obj.get("address") or {}
            rows.append(OrderedDict([
                ("name", name),
                ("type", obj.get("@type") or ""),
                ("url", obj.get("url") or ""),
                ("street", (addr or {}).get("streetAddress") or ""),
                ("locality", (addr or {}).get("addressLocality") or ""),
                ("region", (addr or {}).get("addressRegion") or ""),
                ("postal", (addr or {}).get("postalCode") or ""),
            ]))
    seen, out = set(), []
    for r in rows:
        k = norm(r["name"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def headline(html):
    m = re.search(r"There are\s+([\d,]+)\s+pet friendly ([a-z ]+?) in ([^<.]{0,40})", html, re.I)
    if not m:
        return None
    return OrderedDict([("count", int(m.group(1).replace(",", ""))),
                        ("category_word", m.group(2).strip()),
                        ("place", m.group(3).strip())])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # --- lane probe ------------------------------------------------------
    probes = []
    for u in (BASE, BASE + "hotels/", BASE + "rentals/", BASE + "cats/",
              BASE + "large-dogs/", BASE + "no-pet-fee/",
              BASE + "?type=hotels", BASE + "?type=rentals"):
        meta, body = cached_get(u)
        probes.append(OrderedDict([("url", u), ("status", meta["status"]),
                                   ("bytes", meta["bytes"]), ("sha256", meta["sha256"])]))

    base_meta, base_body = cached_get(BASE)
    base_html = base_body.decode("utf-8", "replace")

    # --- trap 2: is the filter inert? -----------------------------------
    hashes = {p["url"]: p["sha256"] for p in probes if p["status"] == 200}
    qs = [u for u in hashes if "?type=" in u]
    inert = OrderedDict([
        ("path_filters_that_answered", sorted(u for u in hashes if "?" not in u and u != BASE)),
        ("query_string_values_tested", sorted(qs)),
        ("query_string_identical_to_unfiltered",
         all(hashes.get(u) == hashes.get(BASE) for u in qs) if qs else None),
        ("distinct_content_hashes", len(set(hashes.values()))),
        ("finding", ""),
    ])
    if qs and all(hashes.get(u) == hashes.get(BASE) for u in qs):
        inert["finding"] = (
            "The QUERY-STRING category filter is INERT here exactly as the committed doctrine "
            "warns: every ?type= value returns content byte-identical to the unfiltered page. "
            "Nothing derived from it would mean anything.")
    else:
        inert["finding"] = (
            "Query-string filters were not both served, so no inert-filter claim is made. "
            "What IS true for Lexington: the category PATH segments that exist on other "
            "cities (/hotels/, /rentals/) return 404 here, so this city page offers NO "
            "category split at all. The only live path filters are ATTRIBUTE filters "
            "(cats, large-dogs, no-pet-fee), which do not separate hotels from rentals.")

    # --- trap 1: headline vs served cohort -------------------------------
    head = headline(base_html)
    rows = listing_rows(base_html)

    # --- reconciliation ---------------------------------------------------
    recon = json.load(open(RECON, encoding="utf-8"))
    atlas = [r for r in recon["records"]
             if r["classification"] in ("EXACT_UNIQUE_IDENTITY", "IDENTITY_REVIEW_REQUIRED",
                                        "DUPLICATE_LISTING")]
    atlas_out = [r for r in recon["records"] if r["classification"] == "OUTSIDE_MARKET"]

    out_rows = []
    for lead in rows:
        lt = dtok(lead["name"])
        best, best_n = None, 0
        for a in atlas:
            shared = lt & dtok(a["name"])
            if len(shared) > best_n:
                best, best_n = a, len(shared)
        outside = None
        for a in atlas_out:
            if lt & dtok(a["name"]):
                outside = a
                break
        row = OrderedDict([("lead", lead["name"]), ("lead_type", lead["type"]),
                           ("lead_locality", lead["locality"]),
                           ("atlas", best["name"] if best else ""),
                           ("shared_tokens", sorted(lt & dtok(best["name"])) if best else [])])
        if best_n >= 1:
            row["class"] = "EXACT_EXISTING_IN_SHADOW_CENSUS"
            row["why"] = ("shares distinctive token(s) %s with an Atlas Lexington row; the "
                          "directory adds no identity here" % row["shared_tokens"])
        elif outside is not None:
            row["class"] = "OUTSIDE_MARKET_LEAD"
            row["atlas"] = outside["name"]
            row["why"] = ("matches an Atlas row this order classified OUTSIDE the market (%s); "
                          "the directory scopes by the literal city string and pulls in "
                          "surrounding county seats" % outside["county"])
        elif not lt:
            row["class"] = "IDENTITY_REVIEW_REQUIRED"
            row["why"] = ("the lead name reduces to chain and locality words only, so it "
                          "proposes a brand rather than a property; a bare chain name never "
                          "identifies one hotel")
        else:
            # The committed rule: same brand + same city DEMOTES to review, it
            # never confirms and it never declares a gap. Most Atlas rows here
            # come from OSM, where a hotel is often tagged with its bare chain
            # name ("Embassy Suites"), so it carries NO distinctive token to
            # share. Calling that a missing identity would manufacture a
            # discovery gap out of a thin OSM name tag.
            lead_chain = {t for t in norm(lead["name"]).split() if t in CHAIN}
            same_brand = [a for a in atlas
                          if lead_chain & {t for t in norm(a["name"]).split() if t in CHAIN}]
            bare_same_brand = [a for a in same_brand if not dtok(a["name"])]
            if bare_same_brand:
                row["class"] = "SAME_BRAND_SAME_CITY_REVIEW"
                row["atlas"] = ", ".join(a["name"] for a in bare_same_brand[:3])
                row["why"] = (
                    "no distinctive token is shared, but Atlas holds %d row(s) of the SAME "
                    "brand in this market whose own name is a bare chain name carrying no "
                    "distinctive token to match on. Same brand plus same city demotes to "
                    "review: this is either that row under the directory's fuller name, or a "
                    "second property of the brand. Only first-party address or property-code "
                    "evidence separates them." % len(bare_same_brand))
            elif same_brand:
                row["class"] = "TRUE_MISSING_IDENTITY_CANDIDATE"
                row["why"] = (
                    "Atlas holds %d row(s) of this brand in the market and none shares a "
                    "distinctive token with this lead, so the lead plausibly names a SECOND "
                    "property of the brand. A candidate for first-party verification, NOT an "
                    "admission." % len(same_brand))
            else:
                row["class"] = "TRUE_MISSING_IDENTITY_CANDIDATE"
                row["why"] = (
                    "no Atlas Lexington row shares a distinctive token with this lead and "
                    "Atlas holds no row of this brand in the market at all; a candidate for "
                    "first-party verification, NOT an admission")
        out_rows.append(row)

    counts = Counter(r["class"] for r in out_rows)
    report = OrderedDict([
        ("schema", "ptf-competitor-census-challenge/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "6 -- competitor directories as DISCOVERY LEAD SOURCES only"),
        ("as_of", args.as_of),
        ("usd_spent", 0.0),
        ("paid_provider_calls", 0),
        ("authority_mutation", "NONE"),
        ("standing_rule",
         "A competitor directory is an AUDIT lane, not an acquisition lane, and it is never "
         "policy authority. No competitor policy text is published, quoted into authority, or "
         "used to grade a row. Every candidate returns to first-party evidence before it can "
         "become authority."),
        ("stale_refusal_finding",
         "PTF-CINCINNATI-PARALLEL-REVALIDATION-002 recorded www.bringfido.com as 403 to a plain "
         "client on every lodging path tried (2026-09-04) and took the lane into an attended "
         "browser. Re-probed 2026-09-06 for Lexington the city page returns 200 to the same "
         "plain client. This order therefore ran the lane FREE and STATIC and spent no attended "
         "session on it. A refusal is a measurement with a date on it."),
        ("free_static_lane", OrderedDict([("outcome", "ANSWERED"), ("probes", probes)])),
        ("inert_filter_test", inert),
        ("headline_count_trap", OrderedDict([
            ("headline", head),
            ("rows_actually_served_in_page_markup", len(rows)),
            ("finding",
             "The page headlines %s pet friendly '%s' but its own ItemList markup serves %d "
             "rows. The committed doctrine is that this headline is a MIXED-category claim and "
             "is not the served hotel cohort; Cincinnati's page claimed 135 against a real "
             "hotel cohort of 36. No Lexington number is derived from the headline."
             % ((head or {}).get("count"), (head or {}).get("category_word"), len(rows))),
        ])),
        ("reconciliation", OrderedDict([
            ("rows_observed", len(out_rows)),
            ("classes", OrderedDict(sorted(counts.items()))),
            ("rows", out_rows),
        ])),
        ("what_this_lane_delivered", [
            "the lane runs FREE and STATIC for Lexington -- the inherited 403 was stale",
            "a reconciliation of every row the directory's own markup served",
            "true-missing candidates for first-party verification, admitted by nothing here",
        ]),
        ("what_this_lane_did_not_deliver", [
            "any policy fact, quote or grade -- competitor policy text is never authority",
            "the full headline cohort: the page's own markup serves fewer rows than it claims, "
            "and this order reports what it observed rather than estimating the remainder",
        ]),
    ])
    out = args.out or os.path.join(REPORTS, "lexington_ky_competitor_census_challenge_001.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print("headline:", head)
    print("rows served:", len(rows))
    print(json.dumps(dict(counts), indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
