"""PTF-MIAMI-FL-MARRIOTT-TERMINAL-CLOSURE-003 -- the four SOURCE-READY-001 corrections, re-tested before sealing.

Each invariant below is a defect this market actually produced once and a rule that now prevents it. They are
re-run mechanically here over THIS pass's own committed adjudication, not asserted in prose:

  1. CROSS-PROPERTY EVIDENCE   no published row cites a page that another published row also cites, and every
                               browser read bound to exactly one census row on exact premises.
  2. WEIGHT READ AS COUNT      "up to 25 lbs" yields no pet-count limit.
  3. AMENITY FEE READ AS PET FEE  a resort/amenity/destination charge in the same quote is never the pet fee.
  4. ROUTE / HOST MISMATCH     a read on a domain the census does not route the identity to never publishes.

Output: launch_packages/pettripfinder/markets/reports/miami_fl_closure_invariants_003.json  (exit 1 on any failure)
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import miami_fl_clean_authority_001 as CA  # noqa: E402

WORK_ORDER = "PTF-MIAMI-FL-MARRIOTT-TERMINAL-CLOSURE-003"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", "miami-fl", "raw_captures")
CENSUS = os.path.join(PKG, "identity_census_proposed", "miami-fl.json")
OUT = os.path.join(REPORTS, "miami_fl_closure_invariants_003.json")
PUBLISHED = ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS")


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def check_cross_property(clean, census):
    """One page, one published identity -- and every browser read bound on exact premises."""
    by_source, problems = {}, []
    for r in clean["rows"]:
        if r["disposition"] not in PUBLISHED:
            continue
        ev = r.get("evidence") or {}
        src = (ev.get("source_url") or "").split("?")[0]
        if not src:
            continue
        by_source.setdefault(src, []).append(r["identity_key"])
    for src, keys in sorted(by_source.items()):
        if len(keys) > 1:
            problems.append("%s cited by %d published rows: %s" % (src, len(keys), ", ".join(sorted(keys))))
    bindings = Counter()
    for r in (_load(os.path.join(RAW, "browser_closure_rows.json"), {}) or {}).get("rows", []):
        if r.get("outcome") == "READ":
            bindings[r.get("binding") or "NONE"] += 1
            if (r.get("binding") or "NONE") == "NONE":
                problems.append("%s: a browser read with no exact-premises binding" % r["identity_key"])
    return problems, OrderedDict([("published_rows_with_a_cited_page", sum(len(v) for v in by_source.values())),
                                  ("distinct_cited_pages", len(by_source)),
                                  ("browser_read_bindings", OrderedDict(sorted(bindings.items())))])


def check_weight_not_count():
    cases = [("Only one dog is allowed per room (up to 25 lbs) at a charge of USD 50 per day", 1, 25.0),
             ("Pets welcome. Maximum of 2 pets per room, 50 lbs each.", 2, 50.0),
             ("Pets allowed: Yes. Max weight 75 lbs", None, 75.0)]
    problems, seen = [], []
    for quote, want_count, want_weight in cases:
        facts = CA.extract_facts(quote)
        seen.append(OrderedDict([("quote", quote), ("max_pet_count", facts["max_pet_count"]),
                                 ("max_pet_weight_lbs", facts["max_pet_weight_lbs"])]))
        if facts["max_pet_count"] != want_count:
            problems.append("count %r read from %r (expected %r)" % (facts["max_pet_count"], quote, want_count))
        if facts["max_pet_weight_lbs"] != want_weight:
            problems.append("weight %r read from %r (expected %r)" % (facts["max_pet_weight_lbs"], quote, want_weight))
    return problems, seen


def check_amenity_fee_not_pet_fee():
    cases = [("Yes, the hotel charges a $35 nightly plus tax amenity fee including Wireless Internet. Is it Pet "
              "Friendly? We welcome up to 2 dogs. A $150 non-refundable pet fee applies per stay.", 15000),
             ("A daily destination fee of $35.40 is applied. Your pet is welcome, too. PET FEES Up to six nights: "
              "$100 / STAY", 10000),
             ("Pets allowed: Yes. $125.00 non-refundable fee, max weight 30 lbs", 12500)]
    problems, seen = [], []
    for quote, want in cases:
        facts = CA.extract_facts(quote)
        seen.append(OrderedDict([("quote", quote[:90]), ("pet_fee_cents", facts["pet_fee_cents"]), ("expected", want)]))
        if facts["pet_fee_cents"] != want:
            problems.append("pet fee %r read from %r (expected %r)" % (facts["pet_fee_cents"], quote[:60], want))
    return problems, seen


def check_route_host(clean, census):
    problems, checked = [], 0
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    for r in clean["rows"]:
        if r["disposition"] not in PUBLISHED:
            continue
        ev = r.get("evidence") or {}
        conflict = CA.route_domain_conflict(by_key.get(r["identity_key"], {}), ev)
        checked += 1
        if conflict:
            problems.append("%s published on %r while the census routes it elsewhere" % (r["identity_key"],
                                                                                         ev.get("source_url")))
    synthetic = CA.route_domain_conflict({"official_url": "https://www.wyndhamhotels.com/ramada/x/overview",
                                          "brand": "WYNDHAM"},
                                         {"source_url": "https://marcopolobeachresort.com/"})
    if not synthetic:
        problems.append("the route-domain guard no longer refuses a read on an unrouted domain")
    return problems, OrderedDict([("published_rows_checked", checked), ("guard_still_refuses_a_foreign_domain",
                                                                       bool(synthetic))])


def main():
    clean = _load(os.path.join(REPORTS, "miami_fl_clean_authority_001.json"))
    census = _load(CENSUS)
    results = OrderedDict()
    failures = []
    for name, fn in (("1_cross_property_evidence", lambda: check_cross_property(clean, census)),
                     ("2_weight_not_read_as_count", check_weight_not_count),
                     ("3_amenity_fee_not_read_as_pet_fee", check_amenity_fee_not_pet_fee),
                     ("4_route_host_mismatch_never_publishes", lambda: check_route_host(clean, census))):
        problems, detail = fn()
        results[name] = OrderedDict([("status", "PASS" if not problems else "FAIL"), ("problems", problems),
                                     ("detail", detail)])
        failures.extend(problems)
    doc = OrderedDict([("schema", "ptf-closure-invariants/1.0"), ("work_order", WORK_ORDER), ("market_id", "miami-fl"),
                       ("what_this_is", "the four SOURCE-READY-001 corrections, re-tested mechanically over this "
                                        "pass's own committed adjudication before sealing"),
                       ("overall", "PASS" if not failures else "FAIL"), ("checks", results)])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for name, res in results.items():
        print("%-42s %s" % (name, res["status"]))
        for p in res["problems"][:5]:
            print("   !", p[:200])
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
