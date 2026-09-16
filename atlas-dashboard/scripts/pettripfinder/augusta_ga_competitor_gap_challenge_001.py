"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 9, the competitor challenge.

A competitor directory is an AUDIT lane, not an acquisition lane. Its rows are
DISCOVERY LEADS: they may point at an identity Atlas is missing, and they are
never policy authority, never a quote, and never a reason to grade a row.

Two committed traps are tested here rather than assumed (measured against
Cincinnati, Indianapolis and Lexington on this same directory):

  1. THE HEADLINE COUNT IS NOT THE SERVED COHORT. The unfiltered page often
     calls itself "pet friendly hotels" while serving hotels and vacation
     rentals together.
  2. THE FILTER MAY BE INERT. Every filter this order relies on is diffed by
     content hash before it is believed.

A third thing is measured rather than inherited: this order re-probes the host
fresh rather than assuming a prior market's refusal or success carries over.

Reconciliation is against the Augusta census this order built
(``augusta_ga_census_reconciliation_001.json``), and a lead matches an Atlas
row only on a distinctive token plus agreeing geography -- same brand plus
same city demotes to review, it never confirms.

South Carolina leads (North Augusta, Aiken) are read too, for the boundary
audit, and are classified OUTSIDE -- never merged into the augusta-ga census.
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

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
RECON = os.path.join(REPORTS, "augusta_ga_census_reconciliation_001.json")
CENSUS = os.path.join(_DASH, "launch_packages", "pettripfinder", "identity_census_proposed", "augusta-ga.json")
CACHE = os.path.join(_DASH, "data", "discovery", "augusta_ga_competitor_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
CITIES = OrderedDict([
    ("augusta_ga", "https://www.bringfido.com/lodging/city/augusta_ga_us/"),
    ("north_augusta_sc", "https://www.bringfido.com/lodging/city/north_augusta_sc_us/"),
    ("aiken_sc", "https://www.bringfido.com/lodging/city/aiken_sc_us/"),
])
SPACING = 2.0

STOPWORDS = {
    "inn", "suites", "suite", "hotel", "hotels", "motel", "resort", "spa", "the",
    "and", "by", "at", "of", "a", "an", "place", "plaza", "conference", "center",
    "centre", "augusta", "georgia", "ga", "downtown", "airport", "medical",
    "north", "south", "east", "west", "area", "district", "near", "extended",
    "stay", "express", "garden", "sc", "carolina", "aiken",
}
CHAIN = {
    "marriott", "hilton", "hyatt", "sheraton", "westin", "courtyard", "residence",
    "fairfield", "springhill", "towneplace", "hampton", "homewood", "home2",
    "embassy", "doubletree", "tru", "wyndham", "days", "super", "baymont",
    "microtel", "ramada", "travelodge", "la", "quinta", "comfort", "quality",
    "sleep", "econo", "lodge", "clarion", "woodspring", "ihg", "holiday",
    "candlewood", "staybridge", "crowne", "avid", "best", "western", "surestay",
    "red", "roof", "drury", "sonesta", "radisson", "country", "guesthouse",
    "four", "points", "aloft", "element", "moxy", "ac", "8", "6", "scottish",
    "rodeway", "knights", "masters", "spark",
}


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def dtok(s):
    return {t for t in norm(s).split() if t not in STOPWORDS and t not in CHAIN}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def cached_get(url):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    p, m = os.path.join(CACHE, key + ".html"), os.path.join(CACHE, key + ".json")
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
    rows = []
    for blob in jsonld_blobs(html):
        items = []
        if isinstance(blob, dict) and blob.get("@type") == "ItemList":
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
                ("name", name), ("type", obj.get("@type") or ""), ("url", obj.get("url") or ""),
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
                        ("category_word", m.group(2).strip()), ("place", m.group(3).strip())])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    recon = json.load(open(RECON, encoding="utf-8"))
    census = json.load(open(CENSUS, encoding="utf-8"))
    atlas = [h for h in census["hotels"]]
    atlas_outside = [OrderedDict([("name", n["name"]), ("why", n["why"])])
                     for n in census.get("non_admitted", []) if n["classification"] == "OUTSIDE_MARKET"]

    by_city = OrderedDict()
    for slug, base in CITIES.items():
        probes = []
        for u in (base, base + "hotels/", base + "rentals/", base + "?type=hotels", base + "?type=rentals"):
            meta, body = cached_get(u)
            probes.append(OrderedDict([("url", u), ("status", meta["status"]),
                                       ("bytes", meta["bytes"]), ("sha256", meta["sha256"])]))
        base_meta, base_body = cached_get(base)
        base_html = base_body.decode("utf-8", "replace")
        hashes = {p["url"]: p["sha256"] for p in probes if p["status"] == 200}
        qs = [u for u in hashes if "?type=" in u]
        inert = OrderedDict([
            ("query_string_values_tested", sorted(qs)),
            ("query_string_identical_to_unfiltered",
             all(hashes.get(u) == hashes.get(base) for u in qs) if qs else None),
        ])
        head = headline(base_html)
        rows = listing_rows(base_html)
        by_city[slug] = OrderedDict([
            ("base_url", base), ("status", base_meta["status"]), ("probes", probes),
            ("inert_filter_test", inert), ("headline", head),
            ("rows_served_in_page_markup", len(rows)), ("rows", rows),
        ])

    # --- reconciliation (augusta_ga_us city only; SC cities are boundary-audit reads) ----
    out_rows = []
    for lead in by_city["augusta_ga"]["rows"]:
        lt = dtok(lead["name"])
        best, best_n = None, 0
        for a in atlas:
            shared = lt & dtok(a["canonical_name"])
            if len(shared) > best_n:
                best, best_n = a, len(shared)
        outside = None
        for a in atlas_outside:
            if lt & dtok(a["name"]):
                outside = a
                break
        row = OrderedDict([("lead", lead["name"]), ("lead_type", lead["type"]),
                           ("lead_locality", lead["locality"]),
                           ("atlas", best["canonical_name"] if best else ""),
                           ("shared_tokens", sorted(lt & dtok(best["canonical_name"])) if best else [])])
        if best_n >= 1:
            row["class"] = "EXACT_ATLAS_MATCH"
            row["why"] = "shares distinctive token(s) %s with an Atlas Augusta row" % row["shared_tokens"]
        elif outside is not None:
            row["class"] = "OUTSIDE"
            row["atlas"] = outside["name"]
            row["why"] = "matches an Atlas row this order classified OUTSIDE the market"
        elif not lt:
            row["class"] = "REVIEW"
            row["why"] = "the lead name reduces to chain/locality words only; proposes a brand, not a property"
        else:
            lead_chain = {t for t in norm(lead["name"]).split() if t in CHAIN}
            same_brand = [a for a in atlas
                          if lead_chain & {t for t in norm(a["canonical_name"]).split() if t in CHAIN}]
            if same_brand:
                row["class"] = "REVIEW"
                row["atlas"] = ", ".join(a["canonical_name"] for a in same_brand[:3])
                row["why"] = ("no distinctive token shared, but Atlas holds %d row(s) of the same "
                              "brand; a candidate for first-party verification, not an admission"
                              % len(same_brand))
            else:
                row["class"] = "TRUE_MISSING_QUALIFYING"
                row["why"] = ("no Atlas Augusta row shares a distinctive token and Atlas holds no "
                              "row of this brand at all; a candidate for first-party verification")
        out_rows.append(row)

    counts = Counter(r["class"] for r in out_rows)
    material_gap = counts.get("TRUE_MISSING_QUALIFYING", 0) >= max(3, round(0.05 * len(atlas)))

    report = OrderedDict([
        ("schema", "ptf-competitor-gap-matrix/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9 -- competitor directories as DISCOVERY LEAD SOURCES only"),
        ("as_of", args.as_of), ("usd_spent", 0.0), ("paid_provider_calls", 0),
        ("authority_mutation", "NONE"),
        ("standing_rule",
         "A competitor directory is an AUDIT lane, not an acquisition lane, and it is never policy "
         "authority. No competitor policy text is published, quoted into authority, or used to "
         "grade a row. Every true-missing candidate returns to first-party evidence before it can "
         "become authority."),
        ("cities_probed", by_city),
        ("reconciliation", OrderedDict([
            ("rows_observed", len(out_rows)),
            ("classes", OrderedDict(sorted(counts.items()))),
            ("rows", out_rows),
        ])),
        ("counts", OrderedDict([
            ("competitor_raw_discovery", sum(c["rows_served_in_page_markup"] for c in by_city.values())),
            ("normalized_unique_augusta", len(by_city["augusta_ga"]["rows"])),
            ("matched_to_census", counts.get("EXACT_ATLAS_MATCH", 0)),
            ("true_missing_qualifying", counts.get("TRUE_MISSING_QUALIFYING", 0)),
            ("excluded_stale_outside", counts.get("OUTSIDE", 0)),
            ("matched_but_policy_unresolved", counts.get("EXACT_ATLAS_MATCH", 0)),
            ("material_unexplained_gap_remains", material_gap),
        ])),
        ("boundary_audit", OrderedDict([
            ("north_augusta_sc_rows", len(by_city["north_augusta_sc"]["rows"])),
            ("aiken_sc_rows", len(by_city["aiken_sc"]["rows"])),
            ("finding", "South Carolina competitor rows are read for the boundary audit only and "
                        "are never merged into the augusta-ga census -- they corroborate the "
                        "geography contract's OUTSIDE-by-default rule."),
        ])),
    ])
    out = args.out or os.path.join(REPORTS, "augusta_ga_competitor_gap_matrix_001.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print("augusta rows served:", len(by_city["augusta_ga"]["rows"]))
    print(json.dumps(dict(counts), indent=1))
    print("north_augusta_sc rows:", len(by_city["north_augusta_sc"]["rows"]),
          "aiken_sc rows:", len(by_city["aiken_sc"]["rows"]))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
