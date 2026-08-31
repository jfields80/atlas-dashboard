# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-MARRIOTT-SCALE-015, Phases 6 to 9.

Classifies the scale run, closes Marriott's measurement across all three runs,
prepares authority candidates WITHOUT applying them, and restates Hilton.

THE VENDOR'S COST METER RESTATED DOWNWARD DURING THIS ORDER. Bright Data's
month-to-date zone cost read $77.70 before the run and $75.58 after, while
bandwidth rose 8.3 -> 8.4 GB. A month-to-date figure that falls while usage
rises is a vendor-side restatement, not a refund, and it cannot be used as this
run's spend. The PREPAID BALANCE is the direct measure of money leaving the
account, so it is what this order reports -- and because that disagrees with
the figure orders 013 and 014 published, both readings are shown rather than
quietly reconciled.

CLASSIFICATION IS THE PILOTS', UNCHANGED -- including the rule that a block
containing only a question is not affirmative evidence. No shared reader is
widened.

NOTHING IS APPLIED TO AUTHORITY. Phase 8 sorts candidates and stops.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_firecrawl_classification_008 as C8,
    detroit_ann_arbor_brightdata_measure_013 as M13,
    detroit_ann_arbor_brightdata_pilot_013 as P13,
    detroit_ann_arbor_brightdata_pilot_014 as P14,
    detroit_ann_arbor_marriott_scale_015 as S15)

MARKET = S15.MARKET
WORK_ORDER = S15.WORK_ORDER
LANE = S15.LANE
AS_OF = S15.AS_OF

LP = S15.LP
RUN_DIR_015 = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
               / "detroit-ann-arbor-marriott-015")
CLASS_015 = LP / "detroit_ann_arbor_marriott_classification_015.json"
FINAL = LP / "detroit_ann_arbor_marriott_final_measurement_015.json"
CANDIDATES = LP / "detroit_ann_arbor_brightdata_authority_candidates_015.json"
HILTON = LP / "detroit_ann_arbor_hilton_state_015.json"
SPEND = LP / "detroit_ann_arbor_brightdata_spend_reconciliation_015.json"

PILOTS = (
    ("013", LP / "detroit_ann_arbor_brightdata_classification_013.json"),
    ("014", LP / "detroit_ann_arbor_brightdata_classification_014.json"),
)

#: Prepaid balance, read at each boundary. The direct measure of money leaving.
BALANCE = OrderedDict([("pre_013", 5.42), ("post_013", 4.00),
                       ("post_014", 2.80), ("pre_015", 2.69),
                       ("post_015", 1.14)])
#: What the month-to-date zone meter said at the same moments.
ZONE_MTD = OrderedDict([("pre_013", 72.63), ("post_013", 75.27),
                        ("post_014", 77.50), ("pre_015", 77.70),
                        ("post_015", 75.58)])
BILLED = OrderedDict([("013", 16), ("014", 16), ("015", 16)])


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def classify_015() -> List[Dict]:
    original_run, original_dir = M13.RUN_ID, M13.RUN_DIR
    original_admitted = P13.ADMITTED_PATH
    try:
        M13.RUN_ID = S15.RUN_ID
        M13.RUN_DIR = RUN_DIR_015
        P13.ADMITTED_PATH = S15.ADMITTED_PATH
        return M13.classify()
    finally:
        M13.RUN_ID, M13.RUN_DIR = original_run, original_dir
        P13.ADMITTED_PATH = original_admitted


def run() -> None:
    results_015 = classify_015()
    counts_015 = Counter(row["class"] for row in results_015)
    C8.write_lf(CLASS_015, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-marriott-classification/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", S15.RUN_ID), ("lane", LANE), ("family", "MARRIOTT"),
        ("note", "Classified by the pilots' own path, question-only rule "
                 "included. No shared reader widened."),
        ("attempts", len(results_015)),
        ("counts", OrderedDict(sorted(counts_015.items()))),
        ("results", results_015),
    ]))

    # ---- Phase 7: Marriott across all three runs, UNIQUE properties ---- #
    everything: "OrderedDict[str, Dict]" = OrderedDict()
    for _label, path in PILOTS:
        for row in load(path)["results"]:
            everything[row["identity_key"]] = row
    for row in results_015:
        everything[row["identity_key"]] = row

    marriott = [row for row in everything.values() if row["brand"] == "MARRIOTT"]
    hilton = [row for row in everything.values() if row["brand"] == "HILTON"]

    def block(rows: List[Dict], label: str) -> Dict:
        counts = Counter(row["class"] for row in rows)
        acquired = sum(counts[cls] for cls in C8.ACQUIRED_CLASSES)
        reached = sum(1 for row in rows if row["reached_the_property_page"])
        return OrderedDict([
            ("family", label),
            ("unique_properties_measured", len(rows)),
            ("counts", OrderedDict(sorted(counts.items()))),
            ("access", M13.rate(reached, len(rows),
                                "unique properties reached")),
            ("publication_grade", M13.rate(acquired, len(rows),
                                           "unique properties answered")),
            ("pet_friendly", M13.rate(counts["PET_FRIENDLY"], len(rows),
                                      "unique properties stating pets are "
                                      "accepted")),
            ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
            ("policy_not_found", counts["POLICY_NOT_FOUND"]),
            ("holds", counts["HOLD"]),
            ("failures", counts["ACQUISITION_FAILURE"] + counts["ACCESS_DENIED"]
             + counts["UNEXPECTED_PAGE"] + counts["IDENTITY_MISMATCH"]),
        ])

    marriott_block = block(marriott, "MARRIOTT")
    hilton_block = block(hilton, "HILTON")

    balance_spent = round(BALANCE["pre_013"] - BALANCE["post_015"], 2)
    billed_total = sum(BILLED.values())
    per_attempt = balance_spent / billed_total
    pub_low = marriott_block["publication_grade"]["wilson_lower_95"]

    C8.write_lf(SPEND, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-spend-reconciliation/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("problem",
         "Bright Data's month-to-date zone cost FELL during order 015 -- "
         "$77.70 before the run, $75.58 after -- while bandwidth rose from 8.3 "
         "to 8.4 GB. A month-to-date figure that falls while usage rises is a "
         "vendor-side restatement, not a refund, so it cannot be this run's "
         "spend."),
        ("what_this_order_uses",
         "the PREPAID BALANCE, which decrements as money leaves the account "
         "and is the most direct signal available."),
        ("balance_readings", BALANCE),
        ("zone_month_to_date_readings", ZONE_MTD),
        ("billed_attempts", BILLED),
        ("spend_by_balance", OrderedDict([
            ("order_013_usd", round(BALANCE["pre_013"] - BALANCE["post_013"], 2)),
            ("order_014_usd", round(BALANCE["post_013"] - BALANCE["post_014"], 2)),
            ("order_015_usd", round(BALANCE["pre_015"] - BALANCE["post_015"], 2)),
            ("total_usd", balance_spent),
            ("usd_per_billed_attempt", round(per_attempt, 4)),
        ])),
        ("disagreement_with_earlier_orders",
         "orders 013 and 014 reported $2.64 and $2.23 from the month-to-date "
         "meter; the balance says $1.42 and $1.20 for the same runs. Both "
         "readings are published here rather than silently reconciled. The "
         "conclusion those orders drew is unaffected -- every figure is well "
         "inside every cap -- but the per-attempt cost this project plans "
         "against should be the balance-derived one."),
        ("caps_held_under_either_reading", True),
    ]))

    C8.write_lf(FINAL, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-marriott-final/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("basis", "pilots 013 and 014 plus scale 015. UNIQUE properties in "
                  "every denominator; the four pages order 013 bought twice "
                  "are cost only."),
        ("marriott", marriott_block),
        ("cost", OrderedDict([
            ("total_brightdata_usd_by_balance", balance_spent),
            ("billed_attempts", billed_total),
            ("usd_per_billed_attempt", round(per_attempt, 4)),
            ("marriott_share_usd",
             round(per_attempt * (14 + len(results_015)), 2)),
            ("cost_per_publication_grade_result",
             round(per_attempt / pub_low, 3) if pub_low else None),
            ("cost_note", "at the Wilson LOWER bound, so the conservative "
                          "figure rather than the flattering one"),
        ])),
        ("marriott_experimentation", "CLOSED. No new systemic defect appeared: "
                                     "the legacy-template failure diagnosed in "
                                     "014 did not recur, because the one row "
                                     "still on that template was excluded "
                                     "rather than bought."),
    ]))

    # ---- Phase 8: candidates, NOT applied ------------------------------ #
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    buckets = OrderedDict([("CLEAN_PET_FRIENDLY", []),
                           ("CLEAN_VERIFIED_NO_PETS", []),
                           ("FOUNDER_EXCEPTION", []),
                           ("NO_AUTHORITY_ACTION", [])])
    for row in everything.values():
        key = row["identity_key"]
        if key in published or key in excluded:
            buckets["NO_AUTHORITY_ACTION"].append(row)
        elif row["class"] == "PET_FRIENDLY":
            buckets["CLEAN_PET_FRIENDLY"].append(row)
        elif row["class"] == "VERIFIED_NO_PETS":
            buckets["CLEAN_VERIFIED_NO_PETS"].append(row)
        elif row["class"] == "HOLD":
            buckets["FOUNDER_EXCEPTION"].append(row)
        else:
            buckets["NO_AUTHORITY_ACTION"].append(row)

    C8.write_lf(CANDIDATES, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-candidates/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "HELD FOR APPLICATION -- NOT APPLIED"),
        ("note",
         "Every Bright Data candidate from 013, 014 and 015, sorted and left "
         "alone. This order mutates no authority; these still have to clear "
         "the publication gates when a later order applies them."),
        ("counts", OrderedDict((name, len(rows))
                               for name, rows in buckets.items())),
        ("by_family", OrderedDict(
            (name, dict(Counter(row["brand"] for row in rows)))
            for name, rows in buckets.items())),
        ("candidates", buckets),
    ]))

    # ---- Phase 9: Hilton, reported only -------------------------------- #
    routing = load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
    hilton_unresolved = [route for route in routing
                         if route["status"] == "ROUTING_CONFIRMED"
                         and P14.registrable(
                             route.get("official_property_url") or "")
                         == "hilton.com"
                         and route["hotel_ref"]["identity_key"] not in published
                         and route["hotel_ref"]["identity_key"] not in excluded
                         and route["hotel_ref"]["identity_key"]
                         not in {row["identity_key"] for row in hilton}]
    C8.write_lf(HILTON, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-state/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "REPORT ONLY -- NOT ACQUIRED IN THIS ORDER"),
        ("unresolved_remaining", len(hilton_unresolved)),
        ("measured_in_pilots_013_014", hilton_block),
        ("why_second_diagnostic_needed",
         "access is strong and equal to Marriott's -- the managed browser "
         "reaches Hilton. What is unresolved is what the pages YIELD: "
         "publication-grade lower bound %.3f on %d properties, and the four "
         "non-acquisitions share no pattern (two NAVIGATION_FAILED, one "
         "POLICY_NOT_FOUND, one HOLD). Nothing says the lane is wrong; nothing "
         "yet justifies buying the rest."
         % (hilton_block["publication_grade"]["wilson_lower_95"],
            hilton_block["unique_properties_measured"])),
        ("recommended_diagnostic", OrderedDict([
            ("rows", 10),
            ("why", "ten more takes Hilton to 24 measured, which roughly halves "
                    "the publication-grade interval -- enough to separate "
                    "'reliable' from 'not' without buying the family"),
            ("stratify_on", ["sub-brand", "city", "URL shape",
                             "per-brand hosts such as hamptoninn3.hilton.com, "
                             "where one of the two NAVIGATION_FAILED rows sat"]),
            ("recommended_hard_cap_usd", 1.50),
            ("cap_basis", "10 attempts at the balance-derived $%.3f, with "
                          "margin" % per_attempt),
            ("run", False),
        ])),
    ]))

    print("=== Phase 6: scale 015 classification ===")
    for cls, n in sorted(counts_015.items()):
        print("   %-20s %d" % (cls, n))
    print()
    print("=== Phase 7: FINAL Marriott, 013 + 014 + 015 ===")
    print("  unique properties :", marriott_block["unique_properties_measured"])
    for field in ("access", "publication_grade", "pet_friendly"):
        r = marriott_block[field]
        print("     %-18s %2d/%-2d point %.3f  wilson [%.3f, %.3f]"
              % (field, r["successes"], r["denominator"], r["point"],
                 r["wilson_lower_95"], r["wilson_upper_95"]))
    print("  verified no-pets %d | policy-not-found %d | holds %d | failures %d"
          % (marriott_block["verified_no_pets"],
             marriott_block["policy_not_found"], marriott_block["holds"],
             marriott_block["failures"]))
    print("  total BD spend by balance: $%.2f over %d billed = $%.4f/attempt"
          % (balance_spent, billed_total, per_attempt))
    print()
    print("=== Phase 8: candidates HELD, not applied ===")
    for name, rows in buckets.items():
        print("   %-24s %d %s" % (name, len(rows),
                                  dict(Counter(r["brand"] for r in rows))))
    print()
    print("=== Phase 9: Hilton, report only ===")
    print("  unresolved remaining :", len(hilton_unresolved))
    print("  recommended diagnostic: 10 rows, cap $1.50 -- NOT RUN")
    print("wrote", CLASS_015.name, FINAL.name, CANDIDATES.name, HILTON.name,
          SPEND.name)


if __name__ == "__main__":
    run()
