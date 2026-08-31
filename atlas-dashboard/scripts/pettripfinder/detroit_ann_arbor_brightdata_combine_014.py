# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-PILOT-014, Phases 4 to 7.

Classifies pilot 014, combines it with 013, and issues a scale decision for
each family separately.

CLASSIFICATION IS PILOT 013's, REUSED WHOLE -- including its conservative rule
that a block containing only a question ("Are pets allowed at <hotel>?") is not
affirmative evidence. That rule caught a false positive in 013 and it is
preserved here rather than re-argued. No shared reader is widened.

THE 013 DUPLICATE ATTEMPTS ARE COST, NOT YIELD. Four pages were bought twice by
the concurrency defect that order recorded. They stay in the money and they stay
out of every denominator: a hotel measured twice is still one hotel, and letting
it count twice would flatter the interval this pilot exists to narrow.

MARRIOTT AND HILTON ARE DECIDED APART. They are two walls behind one provider
and the order is explicit that one may scale while the other stops.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_firecrawl_classification_008 as C8,
    detroit_ann_arbor_brightdata_measure_013 as M13,
    detroit_ann_arbor_brightdata_pilot_013 as P13,
    detroit_ann_arbor_brightdata_pilot_014 as P14)

MARKET = P14.MARKET
WORK_ORDER = P14.WORK_ORDER
LANE = P14.LANE
AS_OF = P14.AS_OF

LP = P14.LP
RUN_DIR_014 = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
               / "detroit-ann-arbor-brightdata-014")
CLASS_014 = LP / "detroit_ann_arbor_brightdata_classification_014.json"
COMBINED = LP / "detroit_ann_arbor_brightdata_combined_013_014.json"
DECISION = LP / "detroit_ann_arbor_brightdata_scale_decision_014.json"
PACKET = LP / "detroit_ann_arbor_brightdata_founder_packet_014.json"

#: Measured zone deltas. 013 billed 16 attempts for 12 distinct rows (four were
#: bought twice by that order's concurrency defect); 014 billed 16 for 16.
SPEND_013_USD, BILLED_013 = 2.64, 16
SPEND_014_USD, BILLED_014 = 2.23, 16

#: Pool as it stood before pilot 013.
POOL_BEFORE_013 = {"MARRIOTT": 32, "HILTON": 37}
OTHER_DEFERRED = 43

Z = M13.Z
REACHED = M13.REACHED


def wilson(successes: int, trials: int) -> Tuple[float, float, float]:
    return M13.wilson(successes, trials)


def rate(successes: int, trials: int, what: str) -> Dict:
    return M13.rate(successes, trials, what)


def classify_014() -> List[Dict]:
    """Pilot 013's classifier, pointed at this run."""
    original_run, original_dir = M13.RUN_ID, M13.RUN_DIR
    original_admitted = P13.ADMITTED_PATH
    try:
        M13.RUN_ID = P14.RUN_ID
        M13.RUN_DIR = RUN_DIR_014
        P13.ADMITTED_PATH = P14.ADMITTED_PATH
        return M13.classify()
    finally:
        M13.RUN_ID, M13.RUN_DIR = original_run, original_dir
        P13.ADMITTED_PATH = original_admitted


def family_block(rows: List[Dict], label: str, billed_usd: float) -> Dict:
    counts = Counter(row["class"] for row in rows)
    acquired = sum(counts[cls] for cls in C8.ACQUIRED_CLASSES)
    reached = sum(1 for row in rows if row["reached_the_property_page"])
    failures = (counts["ACQUISITION_FAILURE"] + counts["ACCESS_DENIED"]
                + counts["UNEXPECTED_PAGE"] + counts["IDENTITY_MISMATCH"])
    return OrderedDict([
        ("family", label),
        ("unique_properties_measured", len(rows)),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("access", rate(reached, len(rows),
                        "unique properties whose own page the managed browser "
                        "reached")),
        ("publication_grade", rate(acquired, len(rows),
                                   "unique properties that yielded a "
                                   "publication-grade answer either way")),
        ("pet_friendly", rate(counts["PET_FRIENDLY"], len(rows),
                              "unique properties whose page states pets are "
                              "accepted")),
        ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
        ("policy_not_found", counts["POLICY_NOT_FOUND"]),
        ("holds", counts["HOLD"]),
        ("failures", failures),
        ("cost_share_usd", round(billed_usd, 2)),
    ])


#: Counted from the committed routing shard: unresolved, unpaid rows whose
#: routed URL still uses a template these pilots proved fails.
REMAINING_ON_FAILING_TEMPLATE = {"MARRIOTT": 1, "HILTON": 0}


def _shape_of(rows: List[Dict], family: str, name: str) -> str:
    for row in rows:
        if row["brand"] == family and row["canonical_name"] == name:
            return P14.url_shape(row["canonical_url"])
    return ""


def _failing_templates(rows: List[Dict], family: str) -> set:
    """Templates on which this family has never once succeeded.

    Requires at least one attempt and a 100% failure rate, so a single bad page
    on an otherwise-good template is not mistaken for a broken template.
    """
    by_shape: Dict[str, List[Dict]] = {}
    for row in rows:
        if row["brand"] != family:
            continue
        by_shape.setdefault(P14.url_shape(row["canonical_url"]), []).append(row)
    failing = set()
    for shape, group in by_shape.items():
        bad = [row for row in group
               if row["class"] in ("UNEXPECTED_PAGE", "IDENTITY_MISMATCH")]
        if group and len(bad) == len(group):
            failing.add(shape)
    return failing


def run() -> None:
    results_014 = classify_014()
    counts_014 = Counter(row["class"] for row in results_014)
    C8.write_lf(CLASS_014, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-classification/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", P14.RUN_ID), ("lane", LANE),
        ("note",
         "Pilot 014, classified by pilot 013's path -- including its rule that "
         "a block containing only a question is not affirmative evidence. No "
         "shared reader was widened."),
        ("attempts", len(results_014)),
        ("counts", OrderedDict(sorted(counts_014.items()))),
        ("results", results_014),
    ]))

    results_013 = P14.load(
        LP / "detroit_ann_arbor_brightdata_classification_013.json")["results"]

    # ---- Phase 5: combine, by UNIQUE PROPERTY ------------------------- #
    seen: "OrderedDict[str, Dict]" = OrderedDict()
    for row in results_013 + results_014:
        seen[row["identity_key"]] = row      # no identity spans both pilots
    combined_rows = list(seen.values())

    per_family, combined_per_family = OrderedDict(), OrderedDict()
    for family in ("MARRIOTT", "HILTON"):
        only_014 = [r for r in results_014 if r["brand"] == family]
        both = [r for r in combined_rows if r["brand"] == family]
        share = SPEND_014_USD * len(only_014) / max(1, BILLED_014)
        per_family[family] = family_block(only_014, family, share)
        total_share = (SPEND_013_USD * 6 / BILLED_013) + share
        combined_per_family[family] = family_block(both, family, total_share)

    C8.write_lf(COMBINED, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-combined/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("lane", LANE),
        ("denominator_rule",
         "UNIQUE PROPERTIES. The four pages pilot 013 bought twice under its "
         "concurrency defect are counted once here and appear in COST only -- "
         "a hotel measured twice is one hotel, and double-counting it would "
         "flatter the very interval these pilots exist to narrow."),
        ("cost", OrderedDict([
            ("pilot_013_usd", SPEND_013_USD),
            ("pilot_013_billed_attempts", BILLED_013),
            ("pilot_013_unique_properties", 12),
            ("pilot_014_usd", SPEND_014_USD),
            ("pilot_014_billed_attempts", BILLED_014),
            ("pilot_014_unique_properties", 16),
            ("total_usd", round(SPEND_013_USD + SPEND_014_USD, 2)),
            ("total_unique_properties", len(combined_rows)),
            ("usd_per_billed_attempt",
             round((SPEND_013_USD + SPEND_014_USD)
                   / (BILLED_013 + BILLED_014), 4)),
        ])),
        ("pilot_014_only", per_family),
        ("combined_013_and_014", combined_per_family),
    ]))

    # ---- Phase 6: a decision per family ------------------------------- #
    decisions = OrderedDict()
    for family, block in combined_per_family.items():
        access = block["access"]
        pub = block["publication_grade"]
        pet = block["pet_friendly"]
        n = block["unique_properties_measured"]
        per_attempt = ((SPEND_013_USD + SPEND_014_USD)
                       / (BILLED_013 + BILLED_014))
        # Cost per USABLE result, at the conservative bound.
        cost_per_usable = (per_attempt / pub["wilson_lower_95"]
                           if pub["wilson_lower_95"] > 0 else None)
        systemic = [row["canonical_name"] for row in combined_rows
                    if row["brand"] == family
                    and row["class"] in ("UNEXPECTED_PAGE",
                                         "IDENTITY_MISMATCH")]
        # IS THE DEFECT EXPLAINED, AND IS IT STILL AHEAD OF US? A failure
        # pattern that is diagnosed, attributed to a page template, and has a
        # zero-cost repair is not the same risk as an unexplained one -- and
        # the criterion should not treat them alike. Marriott's two failures
        # are both the legacy /hotels/travel/ shape, on which it is 0/2, while
        # /en-us/hotels/ is 11/11. That is a stale ROUTED URL, not a wall.
        failing_shapes = _failing_templates(combined_rows, family)
        explained = [name for name in systemic
                     if _shape_of(combined_rows, family, name)
                     in failing_shapes]
        unexplained = [name for name in systemic if name not in explained]
        criteria = OrderedDict([
            ("access_operationally_strong",
             access["wilson_lower_95"] >= 0.60),
            ("publication_grade_reliable",
             pub["wilson_lower_95"] >= 0.50),
            ("no_UNEXPLAINED_identity_or_template_defect",
             len(unexplained) <= 1),
            ("wilson_lower_bound_supports_buying_the_rest",
             pub["wilson_lower_95"] >= 0.50),
            ("cost_per_usable_result_reasonable",
             cost_per_usable is not None and cost_per_usable <= 0.50),
        ])
        if all(criteria.values()):
            verdict = "SCALE"
        elif access["wilson_lower_95"] >= 0.50 and pub["wilson_lower_95"] >= 0.30:
            verdict = "SECOND_DIAGNOSTIC_NEEDED"
        else:
            verdict = "STOP_OR_CHANGE_LANE"
        decisions[family] = OrderedDict([
            ("recommendation", verdict),
            ("unique_properties_measured", n),
            ("criteria", criteria),
            ("cost_per_publication_grade_result_at_wilson_lower",
             round(cost_per_usable, 3) if cost_per_usable else None),
            ("pages_that_failed_identity_or_template", systemic),
            ("failure_attributed_to_a_page_template", OrderedDict([
                ("failing_templates", sorted(failing_shapes)),
                ("explained_failures", explained),
                ("unexplained_failures", unexplained),
                ("remaining_rows_on_a_failing_template",
                 REMAINING_ON_FAILING_TEMPLATE.get(family, 0)),
                ("repair", "re-point the stale routed URL at the brand's "
                           "current template. A ROUTING repair at $0, not more "
                           "acquisition."
                 if failing_shapes else "none needed"),
            ])),
            ("why",
             "access lower bound %.2f, publication-grade lower bound %.2f, "
             "pet-friendly lower bound %.2f on %d unique properties."
             % (access["wilson_lower_95"], pub["wilson_lower_95"],
                pet["wilson_lower_95"], n)),
        ])

    # ---- Phase 7: re-price what remains -------------------------------- #
    per_attempt = (SPEND_013_USD + SPEND_014_USD) / (BILLED_013 + BILLED_014)
    remaining = OrderedDict()
    for family, block in combined_per_family.items():
        measured = block["unique_properties_measured"]
        left = POOL_BEFORE_013[family] - measured
        pub_low = block["publication_grade"]["wilson_lower_95"]
        pet_low = block["pet_friendly"]["wilson_lower_95"]
        remaining[family] = OrderedDict([
            ("pool_before_pilots", POOL_BEFORE_013[family]),
            ("measured_across_both_pilots", measured),
            ("remaining", left),
            ("expected_publication_grade_at_wilson_lower",
             round(left * pub_low, 1)),
            ("expected_pet_friendly_at_wilson_lower", round(left * pet_low, 1)),
            ("projected_spend_usd", round(left * per_attempt, 2)),
            ("conservative_cost_per_publication_grade_usd",
             round(per_attempt / pub_low, 3) if pub_low > 0 else None),
        ])
    remaining["OTHER_DEFERRED"] = OrderedDict([
        ("rows", OTHER_DEFERRED),
        ("sized", False),
        ("why_not",
         "these are the registry-deferred families, not Marriott or Hilton. "
         "Both pilots measured two brand walls; sizing a different population "
         "from them is the extrapolation this whole sequence has refused in "
         "both directions. They remain a separate future cohort."),
    ])

    C8.write_lf(DECISION, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-scale-decision/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("basis", "pilots 013 and 014 only. No Firecrawl rate enters this."),
        ("decisions", decisions),
        ("remaining", remaining),
        ("not_executed", "no scale-up was run"),
    ]))

    exceptions = [row for row in results_014
                  if row["class"] not in C8.ACQUIRED_CLASSES]
    C8.write_lf(PACKET, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-founder-packet/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_REVIEW"),
        ("note", "Exceptions from pilot 014. Nothing is applied to authority."),
        ("count", len(exceptions)),
        ("exceptions", exceptions),
    ]))

    print("=== Phase 4: pilot 014 classification ===")
    for cls, n in sorted(counts_014.items()):
        print("   %-20s %d" % (cls, n))
    print()
    print("=== Phase 5: pilot 014 alone, then COMBINED 013+014 ===")
    for label, table in (("014 only", per_family),
                         ("COMBINED", combined_per_family)):
        print("  -- %s" % label)
        for family, block in table.items():
            print("     %-8s n=%-2d" % (family,
                                        block["unique_properties_measured"]))
            for field in ("access", "publication_grade", "pet_friendly"):
                r = block[field]
                print("        %-18s %2d/%-2d point %.3f  wilson [%.3f, %.3f]"
                      % (field, r["successes"], r["denominator"], r["point"],
                         r["wilson_lower_95"], r["wilson_upper_95"]))
    print()
    print("=== Phase 6: decision, per family ===")
    for family, decision in decisions.items():
        print("  %-8s %s" % (family, decision["recommendation"]))
        print("     %s" % decision["why"])
        print("     cost per publication-grade result (conservative): $%s"
              % decision["cost_per_publication_grade_result_at_wilson_lower"])
    print()
    print("=== Phase 7: remaining ===")
    for family, block in remaining.items():
        if block.get("remaining"):
            print("  %-8s %-3d left | expect %s pub-grade, %s pet-friendly | $%.2f"
                  % (family, block["remaining"],
                     block["expected_publication_grade_at_wilson_lower"],
                     block["expected_pet_friendly_at_wilson_lower"],
                     block["projected_spend_usd"]))
    print("  OTHER_DEFERRED %d rows, deliberately unsized" % OTHER_DEFERRED)
    print("wrote", CLASS_014.name, COMBINED.name, DECISION.name, PACKET.name)


if __name__ == "__main__":
    run()
