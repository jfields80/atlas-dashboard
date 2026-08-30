# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-INFRA-RECOVERY-018, Phases 6 to 8.

Classifies the recovery, closes Hilton, and rebuilds the final consolidated
Bright Data application inventory. NO AUTHORITY IS APPLIED.

THE RECOVERY SETTLED THE OPEN QUESTION FROM ORDER 017. Those nine rows all
failed with session signatures under the per-attempt CLI guard; re-run with the
guard removed and nothing else changed, eight returned publication-grade
evidence. Order 016 had already read ten properties on the same host at the same
cadence with no failures. Across the three runs:

    016  guard off   median cycle  72s   10/10
    017  guard ON    median cycle 127s    4/13
    018  guard off   median cycle  76s    8/9   (the identical 017 failures)

That is strong evidence, not proof -- time is confounded and vendor conditions
could have improved on their own -- but the re-run used the SAME ROWS, which is
as close to a controlled comparison as a paid lane allows. It is reported at
that strength and no higher.

HILTON CLOSES ON THE PAGE EVIDENCE, which is what these orders were ever
measuring: 34 of 37 identities now hold a reliable read.
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
    detroit_ann_arbor_hilton_close_017 as X17,
    detroit_ann_arbor_hilton_recovery_018 as R18)

MARKET = R18.MARKET
WORK_ORDER = R18.WORK_ORDER
LANE = R18.LANE
AS_OF = R18.AS_OF

LP = R18.LP
RUN_DIR_018 = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
               / "detroit-ann-arbor-hilton-018")
CLASS_018 = LP / "detroit_ann_arbor_hilton_recovery_classification_018.json"
CLOSURE = LP / "detroit_ann_arbor_hilton_closure_018.json"
INVENTORY = LP / "detroit_ann_arbor_brightdata_application_inventory_018.json"

SOURCES = (
    LP / "detroit_ann_arbor_brightdata_classification_013.json",
    LP / "detroit_ann_arbor_brightdata_classification_014.json",
    LP / "detroit_ann_arbor_marriott_classification_015.json",
    LP / "detroit_ann_arbor_hilton_classification_016.json",
    LP / "detroit_ann_arbor_hilton_classification_017.json",
)

BALANCE_SPENT_018 = round(9.30 - 8.34, 2)
BALANCE_SPENT_TOTAL = round(6.01 + BALANCE_SPENT_018, 2)
BILLED_TOTAL = 16 + 16 + 16 + 10 + 13 + 9

PACING = OrderedDict([
    ("016_guard_off", {"median_cycle_seconds": 72.3, "result": "10/10"}),
    ("017_guard_on", {"median_cycle_seconds": 127.1, "result": "4/13"}),
    ("018_guard_off", {"median_cycle_seconds": 75.6,
                       "result": "8/9 on the identical 017 failures"}),
])


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def classify_018() -> List[Dict]:
    original_run, original_dir = M13.RUN_ID, M13.RUN_DIR
    original_admitted = P13.ADMITTED_PATH
    try:
        M13.RUN_ID = R18.RUN_ID
        M13.RUN_DIR = RUN_DIR_018
        P13.ADMITTED_PATH = R18.ADMITTED_PATH
        return M13.classify()
    finally:
        M13.RUN_ID, M13.RUN_DIR = original_run, original_dir
        P13.ADMITTED_PATH = original_admitted


def run() -> None:
    results_018 = classify_018()
    counts_018 = Counter(row["class"] for row in results_018)
    C8.write_lf(CLASS_018, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-recovery-classification/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", R18.RUN_ID), ("lane", LANE), ("family", "HILTON"),
        ("note", "Classified by the same committed path as orders 013-017. No "
                 "shared reader widened."),
        ("attempts", len(results_018)),
        ("counts", OrderedDict(sorted(counts_018.items()))),
        ("results", results_018),
    ]))

    # One verdict per identity, the recovery superseding its 017 failure.
    everything: "OrderedDict[str, Dict]" = OrderedDict()
    for path in SOURCES:
        for row in load(path)["results"]:
            everything[row["identity_key"]] = row
    for row in results_018:
        everything[row["identity_key"]] = row

    hilton = [row for row in everything.values() if row["brand"] == "HILTON"]
    reached = [row for row in hilton
               if row["adapter_outcome"] not in X17.INFRASTRUCTURE_OUTCOMES]
    counts = Counter(row["class"] for row in hilton)
    acquired = sum(counts[cls] for cls in C8.ACQUIRED_CLASSES)
    still_infra = [row for row in hilton
                   if row["adapter_outcome"] in X17.INFRASTRUCTURE_OUTCOMES]

    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}

    per_attempt = BALANCE_SPENT_TOTAL / BILLED_TOTAL
    pub_rate = M13.rate(acquired, len(hilton),
                        "unique Hilton identities that yielded a "
                        "publication-grade answer")
    reached_rate = M13.rate(
        sum(1 for row in reached if row["class"] in C8.ACQUIRED_CLASSES),
        len(reached), "identities that delivered a page and were answered")

    C8.write_lf(CLOSURE, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-closure/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("basis", "orders 013, 014, 016, 017 and 018. One verdict per unique "
                  "identity; a recovery supersedes the 017 failure it "
                  "replaces. Order 013's duplicate billed attempts stay cost-"
                  "only."),
        ("total_unique_hilton_identities_attempted", len(hilton)),
        ("reliable_page_evidence", len(hilton) - len(still_infra)),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("publication_grade", pub_rate),
        ("pet_friendly", M13.rate(counts["PET_FRIENDLY"], len(hilton),
                                  "identities whose page accepts pets")),
        ("of_those_that_delivered_a_page", reached_rate),
        ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
        ("policy_not_found", counts["POLICY_NOT_FOUND"]),
        ("holds", counts["HOLD"]),
        ("true_acquisition_failures", OrderedDict([
            ("count", len(still_infra)),
            ("identity_keys", [row["identity_key"] for row in still_infra]),
            ("note", "still session-class, not page-class. Never answered, "
                     "and not re-bought by this order: one recovery attempt "
                     "per row was authorised and one was made."),
        ])),
        ("unresolved_hilton_remaining", OrderedDict([
            ("never_attempted", 0),
            ("attempted_but_unanswered", len(still_infra)),
        ])),
        ("infrastructure_finding", OrderedDict([
            ("conclusion",
             "the per-attempt Bright Data CLI balance query is the leading "
             "explanation for order 017's session failures."),
            ("evidence", PACING),
            ("strength",
             "STRONG, NOT CONCLUSIVE. Time is confounded and vendor conditions "
             "could have improved on their own. What raises it above a guess "
             "is that order 018 re-ran the IDENTICAL nine rows with the guard "
             "removed and nothing else changed, and eight came back."),
            ("action_taken",
             "the guard stays off by default and the runner now carries this "
             "comparison where the next operator will read it. A cap should be "
             "held on a PERIODIC balance read -- once before a cohort, once "
             "after -- not on a shell-out before every session."),
        ])),
        ("cost", OrderedDict([
            ("order_018_usd_by_balance", BALANCE_SPENT_018),
            ("all_brightdata_usd_by_balance", BALANCE_SPENT_TOTAL),
            ("billed_attempts", BILLED_TOTAL),
            ("usd_per_billed_attempt", round(per_attempt, 4)),
            ("cost_per_publication_grade_result",
             round(per_attempt / pub_rate["wilson_lower_95"], 3)
             if pub_rate["wilson_lower_95"] else None),
        ])),
        ("acquisition_status", "CLOSED. No further Hilton pilot or scale order "
                               "is recommended."),
    ]))

    # ---- Phase 8: the final inventory ----------------------------------- #
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

    seen = Counter(row["identity_key"] for rows in buckets.values()
                   for row in rows)
    duplicates = [key for key, n in seen.items() if n > 1]
    clean_keys = {row["identity_key"] for row in buckets["CLEAN_PET_FRIENDLY"]}
    clean_keys |= {row["identity_key"]
                   for row in buckets["CLEAN_VERIFIED_NO_PETS"]}
    exception_keys = {row["identity_key"]
                      for row in buckets["FOUNDER_EXCEPTION"]}
    already = clean_keys & (published | excluded)

    clean_pf = len(buckets["CLEAN_PET_FRIENDLY"])
    clean_np = len(buckets["CLEAN_VERIFIED_NO_PETS"])
    C8.write_lf(INVENTORY, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-inventory/1.2"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "HELD FOR APPLICATION -- NOT APPLIED"),
        ("covers", ["013", "014", "015", "016", "017", "018"]),
        ("integrity", OrderedDict([
            ("no_duplicate_identities", not duplicates),
            ("duplicates", duplicates),
            ("no_candidate_already_in_authority", not already),
            ("candidates_already_in_authority", sorted(already)),
            ("no_candidate_both_clean_and_exception",
             not (clean_keys & exception_keys)),
        ])),
        ("counts", OrderedDict((name, len(rows))
                               for name, rows in buckets.items())),
        ("by_family", OrderedDict(
            (name, dict(Counter(row["brand"] for row in rows)))
            for name, rows in buckets.items())),
        ("projected_detroit_if_all_clean_were_approved", OrderedDict([
            ("pet_friendly_now", len(published)),
            ("pet_friendly_projected", len(published) + clean_pf),
            ("verified_no_pets_now", len(excluded)),
            ("verified_no_pets_projected", len(excluded) + clean_np),
            ("total_resolved_now", len(published) + len(excluded)),
            ("total_resolved_projected",
             len(published) + len(excluded) + clean_pf + clean_np),
            ("note", "PROJECTION ONLY. Founder exceptions excluded, and every "
                     "candidate must still clear the publication gates -- "
                     "orders 011 and 012 each found rows that passed the "
                     "policy gates and were still unpublishable."),
        ])),
        ("candidates", buckets),
    ]))

    print("=== Phase 6: recovery classification ===")
    for cls, n in sorted(counts_018.items()):
        print("   %-20s %d" % (cls, n))
    print()
    print("=== Phase 7: HILTON CLOSED ===")
    print("  unique identities attempted :", len(hilton))
    print("  reliable page evidence      :", len(hilton) - len(still_infra))
    print("  publication-grade  %2d/%-2d point %.3f wilson [%.3f, %.3f]"
          % (pub_rate["successes"], pub_rate["denominator"], pub_rate["point"],
             pub_rate["wilson_lower_95"], pub_rate["wilson_upper_95"]))
    print("  pet-friendly %d | verified no-pets %d | policy-not-found %d | "
          "holds %d | true failures %d"
          % (counts["PET_FRIENDLY"], counts["VERIFIED_NO_PETS"],
             counts["POLICY_NOT_FOUND"], counts["HOLD"], len(still_infra)))
    print("  total BD spend by balance: $%.2f over %d billed = $%.4f/attempt"
          % (BALANCE_SPENT_TOTAL, BILLED_TOTAL, per_attempt))
    print()
    print("=== Phase 8: final inventory (NOT applied) ===")
    for name, rows in buckets.items():
        print("   %-24s %-3d %s" % (name, len(rows),
                                    dict(Counter(r["brand"] for r in rows))))
    print("   no duplicates: %s | none already authority: %s"
          % (not duplicates, not already))
    print("   projected Detroit: %d pet-friendly, %d no-pets, %d resolved"
          % (len(published) + clean_pf, len(excluded) + clean_np,
             len(published) + len(excluded) + clean_pf + clean_np))
    print("wrote", CLASS_018.name, CLOSURE.name, INVENTORY.name)


if __name__ == "__main__":
    run()
