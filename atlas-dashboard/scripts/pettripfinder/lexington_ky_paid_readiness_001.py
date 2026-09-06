"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phases 11 and 17, READ ONLY.

Computes the exact Firecrawl-eligible cohort with the COMMITTED planner
(`acquisition.ladder.firecrawl_candidacy`) rather than an opinion, and reports
what the paid lanes would cost. It spends nothing: no vendor client is
constructed, no credit is consumed, no shared paid or discovery ledger is
written, and no Bright Data or Places call is made.

Standing cost doctrine this report obeys:

  * Firecrawl cost is BIMODAL -- 1 credit on success, 0 when the origin refuses
    every engine. The 0.54 blended average is NOT a ceiling. So the cap is on
    ATTEMPTS, and the worst case quoted is attempts x 1 credit.
  * Marriott and Hilton are a MEASURED capability wall (HARD-LANES-003), never
    a candidate, whatever their static outcome was.
  * A code-bound family whose property code will not parse from the URL needs a
    ROUTING REPAIR, not a credit (Detroit PASS-008 lost 49 of 65 attempts here).
  * Pay once per page ever, and once to FIND a page ever.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import ladder as L  # noqa: E402

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
ROUTING = os.path.join(REPORTS, "lexington_ky_routing_and_static_capture_001.json")
FIRECRAWL_LEDGER = os.path.join(_DASH, "data", "acquisition", "firecrawl_call_ledger.jsonl")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = json.load(open(ROUTING, encoding="utf-8"))["identities"]

    tried_urls = set()
    ledger_lines = 0
    if os.path.exists(FIRECRAWL_LEDGER):
        for line in open(FIRECRAWL_LEDGER, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            ledger_lines += 1
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            for k in ("requested_url", "url", "final_url"):
                if rec.get(k):
                    tried_urls.add(rec[k])

    assessed = []
    for r in rows:
        url = r.get("route") or ""
        static = (r.get("static") or {}).get("outcome") or ""
        if not url:
            assessed.append(OrderedDict([
                ("identity_key", r["identity_key"]), ("name", r["name"]),
                ("family", r["brand"]), ("url", ""), ("static_outcome", ""),
                ("firecrawl_candidate", False),
                ("reason", "NO_ROUTE_FREE_LANE_EXHAUSTED"),
                ("next_lane", "PAID_IDENTITY_DISCOVERY_OR_ATTENDED_ROUTING"),
            ]))
            continue
        c = L.firecrawl_candidacy(
            family=r["brand"], url=url, prior_static_outcome=static,
            firecrawl_already_tried=url in tried_urls)
        assessed.append(OrderedDict([
            ("identity_key", r["identity_key"]), ("name", r["name"]),
            ("family", r["brand"]), ("url", url), ("static_outcome", static),
            ("firecrawl_candidate", bool(c.candidate)),
            ("reason", c.reason),
            ("measured_by", getattr(c, "measured_by", "") or ""),
            ("probe_eligible", bool(getattr(c, "probe_eligible", False))),
        ]))

    cand = [a for a in assessed if a["firecrawl_candidate"]]
    probe = [a for a in assessed if a.get("probe_eligible")]
    reasons = Counter(a["reason"] for a in assessed)
    fam_cand = Counter(a["family"] for a in cand)

    report = OrderedDict([
        ("schema", "ptf-paid-readiness/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "11 and 17 -- Firecrawl cohort and paid readiness, READ ONLY"),
        ("as_of", args.as_of),
        ("authority_mutation", "NONE"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("credits_consumed", 0),
        ("shared_ledgers_written", 0),
        ("ledger_read", OrderedDict([
            ("firecrawl_call_ledger", os.path.relpath(FIRECRAWL_LEDGER, _DASH).replace("\\", "/")),
            ("exists", os.path.exists(FIRECRAWL_LEDGER)),
            ("lines", ledger_lines),
            ("distinct_urls_already_bought", len(tried_urls)),
            ("lexington_urls_already_bought", len(
                [a for a in assessed if a["url"] and a["url"] in tried_urls])),
        ])),
        ("method",
         "Every routed row was put through the COMMITTED planner "
         "`acquisition.ladder.firecrawl_candidacy`, which is evidence-aware: only an "
         "escalatable CHANNEL failure moves a row down the ladder, Marriott and Hilton are a "
         "measured wall, and a code-bound family whose code will not parse needs a routing "
         "repair rather than a credit."),
        ("cost_doctrine",
         "Firecrawl cost is BIMODAL: 1 credit on a success, 0 when the origin refuses every "
         "engine. The 0.54 blended average is not a ceiling and is not used here. The cap is on "
         "ATTEMPTS and the worst case is attempts x 1 credit."),
        ("totals", OrderedDict([
            ("rows_assessed", len(assessed)),
            ("firecrawl_candidates", len(cand)),
            ("firecrawl_candidates_by_family", OrderedDict(sorted(fam_cand.items()))),
            ("probe_eligible_unmeasured_families", len(probe)),
            ("reasons", OrderedDict(sorted(reasons.items()))),
        ])),
        ("firecrawl", OrderedDict([
            ("rows", len(cand)),
            ("worst_case_credits", len(cand)),
            ("hard_cap_recommended_attempts", len(cand)),
            ("required_for_promotion", False),
            ("why_not_required",
             "PROMOTION_READY does not depend on this cohort. Every row here is already in the "
             "shadow census with a bound route; Firecrawl would move rows from unresolved to "
             "resolved, which is COVERAGE EXPANSION, not a promotion blocker."),
            ("authorization_state", "NOT AUTHORIZED BY THIS ORDER -- nothing was spent"),
        ])),
        ("bright_data", OrderedDict([
            ("candidates", 0),
            ("expected_cost_usd", 0.0),
            ("hard_cap_usd", 0.0),
            ("note",
             "Not evaluated and not called. Bright Data sits BELOW the attended browser on the "
             "ladder, and the attended lane has not been run for Lexington at all, so no row "
             "has yet earned a paid fetch. Quoting a rate here would imply a measurement this "
             "order did not make."),
        ])),
        ("places", OrderedDict([
            ("candidates", len([a for a in assessed if not a["url"]])),
            ("prior_attempts_for_this_market", 0),
            ("expected_cost_usd", 0.0),
            ("hard_cap_usd", 0.0),
            ("note",
             "The 16 rows with no free route are the only identity-discovery candidates. None "
             "was bought: the repository holds no prior paid attempt for lexington-ky, and the "
             "standing rule is to pay once per page ever and once to FIND a page ever, so the "
             "ledger must be rebuilt BEFORE any spend. Not authorized by this order."),
        ])),
        ("required_for_promotion", []),
        ("optional_coverage_expansion", [
            "Firecrawl on the %d-row escalatable cohort (worst case %d credits)" % (len(cand), len(cand)),
            "an attended browser session for the IHG / Red Roof / G6 / ESA rows the free "
            "lanes could not route or read",
            "paid identity discovery for the %d rows with no free route"
            % len([a for a in assessed if not a["url"]]),
        ]),
        ("rows", assessed),
    ])
    out = args.out or os.path.join(REPORTS, "lexington_ky_paid_readiness_001.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print(json.dumps(report["totals"], indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
