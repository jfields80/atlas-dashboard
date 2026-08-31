# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-PILOT-013, Phases 4, 5 and 6.

Classifies the pilot, measures Marriott and Hilton SEPARATELY, and sizes what
is left from those results alone.

CLASSIFICATION CALLS THE PASS-008 CLASSIFIER, as orders 009 and 010 did. Five
passes in one market must not hold five opinions about what "publication grade"
means, and the lane a page came down does not change what its policy says.

THE FAMILIES ARE NOT POOLED UNTIL AFTER THEY ARE REPORTED APART. Marriott and
Hilton are two walls, reached through one provider; a combined rate can hide one
family failing completely behind the other succeeding. The combined figure is
reported too, but second and labelled.

FIRECRAWL'S RATES DO NOT ENTER THIS FILE. Detroit's Firecrawl measurement was
taken on IHG, Choice and Wyndham through a different provider; carrying it here
would be exactly the extrapolation this order forbids. Every number below comes
from these twelve attempts.

SILENCE IS NOT NO-PETS, and no shared reader is widened here. A row whose page
states nothing about pets is POLICY_NOT_FOUND; a row whose wording the reader
declines to resolve is a HOLD and goes to the founder.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_firecrawl_classification_008 as C8)
from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_brightdata_pilot_013 as P13)

MARKET = P13.MARKET
WORK_ORDER = P13.WORK_ORDER
RUN_ID = P13.RUN_ID
LANE = P13.LANE
AS_OF = P13.AS_OF

LP = P13.LP
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-brightdata-013")
OUT_PATH = LP / "detroit_ann_arbor_brightdata_classification_013.json"
SIZING_PATH = LP / "detroit_ann_arbor_brightdata_sizing_013.json"
PACKET_PATH = LP / "detroit_ann_arbor_brightdata_founder_packet_013.json"

Z = 1.959963984540054

#: The pool as it stood before this pilot, from order 012's status.
POOL_BEFORE = {"MARRIOTT": 32, "HILTON": 37, "OTHER_DEFERRED": 43}

#: Measured across this pilot: zone cost $72.63 -> $75.27. That delta covers
#: SIXTEEN paid attempts, not twelve: a concurrency defect re-bought four pages
#: (see the overspend incident artifact). The per-attempt cost is therefore
#: computed over 16, because that is what was paid for -- while the YIELD below
#: is computed over the 12 distinct rows, because that is what was measured.
#: Conflating the two would either flatter the cost or double-count a hotel.
MEASURED_ZONE_DELTA_USD = 2.64
PAID_ATTEMPTS = 16
ATTEMPTS = 12

#: Outcomes that mean the managed browser REACHED the property's page. Access
#: is the pilot's first question and it is not the same as reading a policy.
REACHED = ("VALID", "POLICY_NOT_FOUND", "IDENTITY_MISMATCH")


def wilson(successes: int, trials: int) -> Tuple[float, float, float]:
    if trials <= 0:
        return (0.0, 0.0, 0.0)
    point = successes / trials
    denominator = 1.0 + (Z * Z) / trials
    centre = (point + (Z * Z) / (2 * trials)) / denominator
    margin = (Z * math.sqrt(point * (1 - point) / trials
                            + (Z * Z) / (4 * trials * trials))) / denominator
    return (point, max(0.0, centre - margin), min(1.0, centre + margin))


def rate(successes: int, trials: int, what: str) -> Dict:
    point, low, high = wilson(successes, trials)
    return OrderedDict([
        ("measures", what), ("successes", successes), ("denominator", trials),
        ("point", round(point, 4)),
        ("wilson_lower_95", round(low, 4)),
        ("wilson_upper_95", round(high, 4)),
    ])


def _question_only(text: str) -> bool:
    """True when the located block asks something and answers nothing.

    Deliberately narrow: every sentence in the block must end in a question
    mark. A block that asks and then answers is a normal FAQ answer and is left
    alone.
    """
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text or "")
                 if part.strip()]
    return bool(sentences) and all(part.endswith("?") for part in sentences)


def persisted(slug: str) -> Optional[Dict]:
    original = C8.RUN_DIR
    try:
        C8.RUN_DIR = RUN_DIR
        return C8.persisted(slug)
    finally:
        C8.RUN_DIR = original


def classify() -> Dict:
    ledger = P13.load(P13.LEDGER_PATH)
    rows = [attempt for attempt in ledger["attempts"]
            if attempt.get("run_id") == RUN_ID]
    if not rows:
        raise SystemExit("no attempts for run %r" % RUN_ID)
    census = {row["identity_key"]: row for row in
              P13.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    admitted = {row["identity_key"]: row for row in
                P13.load(P13.ADMITTED_PATH)["admitted_rows"]}

    results: List[Dict] = []
    for row in rows:
        key = row["identity_key"]
        crow = census.get(key) or {}
        meta = admitted.get(key) or {}
        art = persisted(crow.get("slug") or "")
        outcome = row["outcome"]
        if outcome in ("ACCESS_DENIED", "NAVIGATION_FAILED", "BLANK_PAGE",
                       "UNHYDRATED", "TIMEOUT", "CAPTURE_FAILED",
                       "PROVIDER_UNAVAILABLE"):
            # The adapter's own vocabulary is wider than this order's. Anything
            # that never became a document is an ACQUISITION_FAILURE here,
            # except a refusal, which the order names separately.
            cls = ("ACCESS_DENIED" if outcome == "ACCESS_DENIED"
                   else "ACQUISITION_FAILURE")
            verdict = {"class": cls,
                       "why": "the adapter returned %s; no property document "
                              "was obtained" % outcome,
                       "reading": None}
        else:
            verdict = C8.classify(row, art)
            interrogative = _question_only((verdict.get("reading") or {})
                                           .get("block_text") or "")
            if interrogative and verdict["class"] in C8.ACQUIRED_CLASSES:
                # A QUESTION IS NOT AN ANSWER. Hilton's FAQ heading "Are pets
                # allowed at <hotel>?" contains the words "pets allowed", so
                # both the shared reader and order 011's publication gate read
                # it as affirmative -- off a page that never states the policy.
                # Reclassified as a founder exception, which is this order's
                # instruction for new wording that needs interpretation. The
                # shared reader is NOT widened: declining a reading is the
                # conservative direction and changes nothing for any other
                # market.
                verdict = {
                    "class": "HOLD",
                    "why": ("the located block is a QUESTION and nothing else "
                            "(%r). It contains the words 'pets allowed', which "
                            "is why the reader resolved it affirmatively, but "
                            "the page states no answer here. A pet-friendly "
                            "claim cannot rest on an FAQ heading."
                            % ((verdict.get("reading") or {})
                               .get("block_text") or "")[:120]),
                    "reading": verdict.get("reading"),
                }
        results.append(OrderedDict([
            ("attempt_id", row["attempt_id"]),
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("brand", row["brand"]),
            ("sub_brand", meta.get("sub_brand") or ""),
            ("city", meta.get("city") or crow.get("city") or ""),
            ("canonical_url", row["canonical_url"]),
            ("lane", LANE),
            ("reader", meta.get("reader") or row.get("reader") or ""),
            ("adapter_outcome", outcome),
            ("reached_the_property_page", outcome in REACHED),
            ("class", verdict["class"]),
            ("why", verdict["why"]),
            ("artifact_path", row.get("artifact_path") or ""),
            ("artifact_hash", row.get("artifact_hash") or ""),
            ("reading", verdict["reading"]),
        ]))
    return results


def family_block(rows: List[Dict], label: str) -> Dict:
    counts = Counter(row["class"] for row in rows)
    acquired = sum(counts[cls] for cls in C8.ACQUIRED_CLASSES)
    reached = sum(1 for row in rows if row["reached_the_property_page"])
    return OrderedDict([
        ("family", label),
        ("attempts", len(rows)),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("access", rate(reached, len(rows),
                        "attempts where the managed browser reached the "
                        "property's own page")),
        ("publication_grade", rate(
            acquired, len(rows),
            "attempts that yielded a publication-grade answer either way")),
        ("pet_friendly", rate(counts["PET_FRIENDLY"], len(rows),
                              "attempts whose page states pets are accepted")),
        ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
        ("policy_not_found", counts["POLICY_NOT_FOUND"]),
        ("holds", counts["HOLD"]),
        ("failures", counts["ACQUISITION_FAILURE"] + counts["ACCESS_DENIED"]
         + counts["UNEXPECTED_PAGE"] + counts["IDENTITY_MISMATCH"]),
        ("actual_cost_usd", round(MEASURED_ZONE_DELTA_USD
                                  * len(rows) / PAID_ATTEMPTS, 2)),
        ("cost_note", "the zone meter is per ZONE, not per row; this is the "
                      "run's measured delta apportioned by attempt count, and "
                      "the meter settles upward"),
    ])


def run() -> None:
    results = classify()
    marriott = [row for row in results if row["brand"] == "MARRIOTT"]
    hilton = [row for row in results if row["brand"] == "HILTON"]

    per_family = OrderedDict([
        ("MARRIOTT", family_block(marriott, "MARRIOTT")),
        ("HILTON", family_block(hilton, "HILTON")),
    ])
    combined = family_block(results, "COMBINED")
    combined["note"] = ("reported SECOND and on purpose. Two brand walls "
                        "reached through one provider are two measurements; a "
                        "pooled rate can hide one family failing behind the "
                        "other succeeding.")

    counts = Counter(row["class"] for row in results)
    C8.write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-classification/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", LANE),
        ("note",
         "The Bright Data pilot, classified by the Pass 008 classifier -- the "
         "same code every Detroit pass has used. The lane a page came down "
         "does not change what its policy says. Nothing here is applied to "
         "authority."),
        ("attempts", len(results)),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("per_family", per_family),
        ("combined", combined),
        ("results", results),
    ]))

    # ---- Phase 6: size what is left, from this pilot only --------------- #
    left = OrderedDict()
    for family, block in per_family.items():
        attempted = block["attempts"]
        remaining = POOL_BEFORE[family] - attempted
        pub_low = block["publication_grade"]["wilson_lower_95"]
        pet_low = block["pet_friendly"]["wilson_lower_95"]
        per_attempt = MEASURED_ZONE_DELTA_USD / PAID_ATTEMPTS
        left[family] = OrderedDict([
            ("pool_before_pilot", POOL_BEFORE[family]),
            ("attempted_in_pilot", attempted),
            ("remaining", remaining),
            ("expected_publication_grade_at_wilson_lower",
             round(remaining * pub_low, 1)),
            ("expected_pet_friendly_at_wilson_lower",
             round(remaining * pet_low, 1)),
            ("projected_spend_usd", round(remaining * per_attempt, 2)),
            ("spend_basis", "the measured $%.3f per attempt from this pilot, "
                            "not a vendor list price" % per_attempt),
        ])
    left["OTHER_DEFERRED"] = OrderedDict([
        ("pool_before_pilot", POOL_BEFORE["OTHER_DEFERRED"]),
        ("attempted_in_pilot", 0),
        ("remaining", POOL_BEFORE["OTHER_DEFERRED"]),
        ("expected_publication_grade_at_wilson_lower", None),
        ("why_not_sized",
         "these are the registry-deferred families, not Marriott or Hilton. "
         "This pilot measured two brand walls and says nothing about them; "
         "sizing them from it would be the same extrapolation this order "
         "forbids in the other direction."),
    ])

    m_pub = per_family["MARRIOTT"]["publication_grade"]
    h_pub = per_family["HILTON"]["publication_grade"]
    weakest = min(m_pub["wilson_lower_95"], h_pub["wilson_lower_95"])
    if weakest >= 0.5:
        recommendation = "SCALE"
    elif weakest >= 0.25:
        recommendation = "SECOND PILOT"
    else:
        recommendation = "STOP / CHANGE LANE"

    remaining_total = (left["MARRIOTT"]["remaining"]
                       + left["HILTON"]["remaining"])
    next_cap = round((remaining_total * MEASURED_ZONE_DELTA_USD / PAID_ATTEMPTS)
                     * 1.25, 2)

    C8.write_lf(SIZING_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-sizing/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("basis",
         "THIS PILOT ONLY. Detroit's Firecrawl rates were measured on IHG, "
         "Choice and Wyndham through a different provider and are not carried "
         "here in any form."),
        ("measured_cost", OrderedDict([
            ("zone_delta_usd", MEASURED_ZONE_DELTA_USD),
            ("attempts_billed", PAID_ATTEMPTS),
            ("usd_per_attempt", round(MEASURED_ZONE_DELTA_USD / PAID_ATTEMPTS, 4)),
            ("paid_attempts", PAID_ATTEMPTS),
            ("distinct_rows_measured", ATTEMPTS),
            ("authorised_ceiling_usd_per_attempt",
             P13.USD_CEILING_PER_ATTEMPT),
            ("caveat", "the zone meter is month-to-date and settles upward; "
                       "this is a floor at the time it was read"),
        ])),
        ("remaining", left),
        ("recommendation", recommendation),
        ("recommended_next_hard_cap_usd", next_cap),
        ("sizing_rule", "Wilson LOWER bound, never the point estimate"),
        ("not_executed", "no larger cohort was run"),
    ]))

    exceptions = [row for row in results
                  if row["class"] not in C8.ACQUIRED_CLASSES]
    C8.write_lf(PACKET_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-founder-packet/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_REVIEW"),
        ("note", "Exceptions only. Nothing from this pilot is applied to "
                 "authority by this order."),
        ("count", len(exceptions)),
        ("counts", OrderedDict(
            (cls, sum(1 for row in exceptions if row["class"] == cls))
            for cls in sorted({row["class"] for row in exceptions}))),
        ("exceptions", exceptions),
    ]))

    print("=== Phase 4: classification ===")
    for cls, n in sorted(counts.items()):
        print("   %-20s %d" % (cls, n))
    print()
    print("=== Phase 5: families measured SEPARATELY ===")
    for family, block in per_family.items():
        print("  %s (n=%d, ~$%.2f)" % (family, block["attempts"],
                                       block["actual_cost_usd"]))
        for field in ("access", "publication_grade", "pet_friendly"):
            r = block[field]
            print("     %-18s %d/%-2d point %.3f  wilson [%.3f, %.3f]"
                  % (field, r["successes"], r["denominator"], r["point"],
                     r["wilson_lower_95"], r["wilson_upper_95"]))
    print("  COMBINED (reported second)")
    for field in ("access", "publication_grade", "pet_friendly"):
        r = combined[field]
        print("     %-18s %d/%-2d point %.3f  wilson [%.3f, %.3f]"
              % (field, r["successes"], r["denominator"], r["point"],
                 r["wilson_lower_95"], r["wilson_upper_95"]))
    print()
    print("=== Phase 6: sizing the remainder ===")
    for family, block in left.items():
        if block.get("remaining"):
            print("  %-16s remaining %-3d expected pub-grade %s at wilson lower"
                  % (family, block["remaining"],
                     block["expected_publication_grade_at_wilson_lower"]))
    print("  RECOMMENDATION:", recommendation)
    print("  next hard cap : $%.2f" % next_cap)
    print("wrote", OUT_PATH.name, SIZING_PATH.name, PACKET_PATH.name)


if __name__ == "__main__":
    run()
