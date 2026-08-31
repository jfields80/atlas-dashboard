# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-025, Phases 10 to 12.

Rebuilds Detroit's acquisition readiness after routing repair and reprices the
paid remainder FROM THE LEDGER.

THE RATE IS DERIVED, AND THE LIFETIME MEAN IS THE WRONG NUMBER. Across all 80
Detroit Bright Data attempts the mean is $0.1381, but that average is dragged
up by the three early pilots (013-015 ran $0.165-$0.1825). Orders 016-018, once
the per-attempt CLI guard was removed and the runs stabilised, cost $0.0850,
$0.0917 and $0.0892 -- a recent mean of $0.0890 over 32 attempts. Planning a
future run on the lifetime average would overstate the bill by more than half,
and planning on the single cheapest order would understate it.

REPORT ONLY. Nothing is acquired and no authority is touched.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-025"
AS_OF = "2026-08-30"
RECENT_ORDERS = ("016", "017", "018")

LP = R11.LP
OUT = LP / "detroit_ann_arbor_readiness_025.json"


def run():
    classification = R11.load(
        LP / "detroit_ann_arbor_remaining_classification_020.json")
    results = R11.load(LP / "detroit_ann_arbor_routing_results_025.json")
    ledger = R11.load(LP / "ptf_paid_attempt_ledger_001.json")

    bd = [a for a in ledger["attempts"]
          if a.get("market_id") == MARKET
          and a.get("lane") == "brightdata_browser"]
    by_order = {}
    for attempt in bd:
        tag = attempt["work_order"].split("-")[-1]
        by_order.setdefault(tag, []).append(attempt["cost_usd_minor"])
    lifetime = sum(a["cost_usd_minor"] for a in bd) / 100.0
    lifetime_rate = lifetime / len(bd) if bd else 0.0
    recent = [c for tag in RECENT_ORDERS for c in by_order.get(tag, [])]
    recent_rate = (sum(recent) / 100.0 / len(recent)) if recent else 0.0

    rows = classification["rows"]
    counts = Counter(row["classification"] for row in rows)
    paid = [row for row in rows
            if row["classification"] == "BRIGHTDATA_QUALIFIED"]
    families = Counter(row["host"] for row in paid)

    attempted = {a["identity_key"] for a in ledger["attempts"]
                 if a.get("market_id") == MARKET}
    repriced = OrderedDict([
        ("rows", len(paid)),
        ("families", dict(families)),
        ("previously_attempted_on_a_paid_lane",
         sum(1 for row in paid if row["identity_key"] in attempted)),
        ("route_quality",
         "all %d hold a confirmed first-party property route; 3 of them are "
         "the Marriott rows whose legacy /hotels/travel/ template this order "
         "repaired at $0" % len(paid)),
        ("rate_lifetime_usd", round(lifetime_rate, 4)),
        ("rate_recent_usd", round(recent_rate, 4)),
        ("rate_used", "recent"),
        ("why_recent",
         "the lifetime mean is inflated by pilots 013-015 ($0.165-$0.1825) "
         "run before the per-attempt CLI guard was removed; 016-018 settled "
         "at $0.0890 over 32 attempts and describe how a run behaves now"),
        ("projected_cost_recent_usd", round(len(paid) * recent_rate, 2)),
        ("projected_cost_lifetime_usd", round(len(paid) * lifetime_rate, 2)),
        ("recommended_hard_cap_usd", 2.00),
        ("cap_reasoning",
         "16 rows at the recent $0.0890 is $1.42. A cap of $2.00 covers that "
         "with headroom for the observed per-attempt spread ($0.085-$0.19) "
         "without authorising the lifetime-mean worst case of $2.21. A cap is "
         "a limit, not a budget to spend."),
    ])

    newly_routed = [row for row in results["rows"]
                    if row.get("classification") == "ROUTING_CONFIRMED"]
    opportunities = []
    for row in newly_routed:
        host = (row.get("first_party_domain") or "").lower()
        if host == "marriott.com":
            lane, why = ("BRIGHT_DATA_REQUIRED",
                         "Marriott is one of the five families this market "
                         "PROVED refuses an anonymous fetch")
        elif host in ("extendedstayamerica.com", "redroof.com"):
            lane, why = ("FREE_ATTENDED_CHROME",
                         "attended Chrome already opened this host in this "
                         "market at $0 during the 45-row pass")
        else:
            lane, why = ("UNMEASURED", "never free-tested; probe free first")
        opportunities.append(OrderedDict([
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("host", host), ("cheapest_valid_lane", lane), ("why", why),
        ]))

    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-readiness/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("authority_mutated", False),
        ("unresolved_total", classification["unresolved_total"]),
        ("readiness", dict(counts)),
        ("paid_remainder", repriced),
        ("zero_cost_opportunities_after_routing", opportunities),
    ]))

    print("=== Phase 10: readiness after routing repair ===")
    for name, n in sorted(counts.items()):
        print("   %-28s %d" % (name, n))
    print()
    print("=== Phase 11: repriced from the ledger ===")
    print("   Detroit Bright Data attempts :", len(bd))
    for tag in sorted(by_order):
        costs = by_order[tag]
        print("      order %-4s n=%-3d $%.4f/attempt"
              % (tag, len(costs), sum(costs) / 100.0 / len(costs)))
    print("   lifetime rate : $%.4f  (inflated by the early pilots)"
          % lifetime_rate)
    print("   RECENT rate   : $%.4f  <- used" % recent_rate)
    print("   %d rows -> $%.2f projected, recommended hard cap $2.00"
          % (len(paid), len(paid) * recent_rate))
    print()
    print("=== Phase 12: lanes for the newly routed ===")
    for row in opportunities:
        print("   %-46s %s" % (row["canonical_name"][:46],
                               row["cheapest_valid_lane"]))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
