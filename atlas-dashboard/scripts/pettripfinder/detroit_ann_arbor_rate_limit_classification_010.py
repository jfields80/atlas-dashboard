# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FIRECRAWL-RATE-LIMIT-RECOVERY-010, Phases 4 and 5.

Classifies the recovery cohort and measures it, CALLING the Pass 008
classifier -- the same code Pass 009 called, pointed at this run's artifacts.
Three passes in one market must not hold three opinions about what
"publication grade" means.

RATE_LIMITED is an allowed outcome in this order's vocabulary and is reported
on its own line. It is not a judgement about a page, so it stays out of the
capability denominator: a rate that counted this run's own pacing as a lane
failure would measure the operator, not the lane.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_firecrawl_classification_008 as C8)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FIRECRAWL-RATE-LIMIT-RECOVERY-010"
RUN_ID = "detroit-firecrawl-010-ratelimit"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
RUN_PATH = LP / "detroit_ann_arbor_rate_limit_run_010.json"
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-ratelimit-010")
OUT_PATH = LP / "detroit_ann_arbor_rate_limit_classification_010.json"
PACKET_PATH = LP / "detroit_ann_arbor_rate_limit_founder_candidates_010.json"

RATE_LIMITED = "RATE_LIMITED"
Z = 1.959963984540054


def persisted(slug: str) -> Optional[Dict]:
    original = C8.RUN_DIR
    try:
        C8.RUN_DIR = RUN_DIR
        return C8.persisted(slug)
    finally:
        C8.RUN_DIR = original


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
        ("measures", what),
        ("successes", successes),
        ("denominator", trials),
        ("point", round(point, 4)),
        ("wilson_lower_95", round(low, 4)),
        ("wilson_upper_95", round(high, 4)),
    ])


def run() -> None:
    ledger = C8.load(LEDGER_PATH)
    rows = [attempt for attempt in ledger["attempts"]
            if attempt.get("run_id") == RUN_ID]
    if not rows:
        raise SystemExit("no attempts for run %r in the ledger" % RUN_ID)

    census = {row["identity_key"]: row for row in
              C8.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    run_doc = C8.load(RUN_PATH)
    limited = {result["identity_key"] for result in run_doc["results"]
               if result["rate_limited"]}

    results: List[Dict] = []
    for row in rows:
        key = row["identity_key"]
        crow = census.get(key) or {}
        art = persisted(crow.get("slug") or "")
        if key in limited:
            verdict = {"class": RATE_LIMITED,
                       "why": "the provider's request limit refused this call; "
                              "no property was reached and nothing was billed",
                       "reading": None}
        else:
            verdict = C8.classify(row, art)
        results.append(OrderedDict([
            ("attempt_id", row["attempt_id"]),
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("brand", row["brand"]),
            ("canonical_url", row["canonical_url"]),
            ("property_code", row.get("property_code") or ""),
            ("adapter_outcome", row["outcome"]),
            ("class", verdict["class"]),
            ("why", verdict["why"]),
            ("predecessor_attempt_id", row.get("predecessor_attempt_id") or ""),
            ("material_change_reason", row.get("material_change_reason") or ""),
            ("reading", verdict["reading"]),
        ]))

    classes = tuple(C8.CLASSES) + (RATE_LIMITED,)
    counts = Counter(result["class"] for result in results)
    for cls in classes:
        counts.setdefault(cls, 0)
    if sum(counts[cls] for cls in classes) != len(results):
        raise SystemExit("every attempt must fall in exactly one class")

    reached = [result for result in results if result["class"] != RATE_LIMITED]
    acquired = sum(counts[cls] for cls in C8.ACQUIRED_CLASSES)

    by_brand = OrderedDict()
    for brand in sorted({result["brand"] for result in results}):
        sub = [result for result in results if result["brand"] == brand]
        by_brand[brand] = OrderedDict(
            [("attempts", len(sub))]
            + [(cls, sum(1 for result in sub if result["class"] == cls))
               for cls in classes
               if any(result["class"] == cls for result in sub)])

    measurement = OrderedDict([
        ("attempts", len(results)),
        ("credits_spent", run_doc["spend"]["credits_spent"]),
        ("usd_spent", run_doc["spend"]["usd_spent"]),
        ("counts", OrderedDict((cls, counts[cls]) for cls in classes)),
        ("reached_the_corrected_identity_gate", len(reached)),
        ("publication_grade", rate(
            acquired, len(reached),
            "rows that actually reached the corrected identity gate and "
            "yielded a publication-grade answer either way. Rate-limit "
            "failures are excluded from this denominator: they are a fact "
            "about pacing, not about the lane.")),
        ("pet_friendly", rate(
            counts["PET_FRIENDLY"], len(reached),
            "rows that actually reached the corrected identity gate and whose "
            "own page states pets are accepted")),
    ])

    C8.write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-rate-limit-classification/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", "firecrawl"),
        ("note",
         "The rate-limit recovery cohort, classified by the Pass 008 "
         "classifier -- the same code Pass 009 called. Nothing here is applied "
         "to authority and nothing is published."),
        ("by_brand", by_brand),
        ("measurement", measurement),
        ("results", results),
    ]))

    candidates = [result for result in results
                  if result["class"] in C8.ACQUIRED_CLASSES]
    exceptions = [result for result in results
                  if result["class"] not in C8.ACQUIRED_CLASSES]
    C8.write_lf(PACKET_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-rate-limit-candidates/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_APPROVAL"),
        ("note",
         "Candidates only. NOT applied to authority: no policy fact, "
         "exclusion, seed row or partition state is touched by this order. "
         "Each row states what its own page said, with the byte hashes of the "
         "block and the document it was read from."),
        ("candidate_count", len(candidates)),
        ("exception_count", len(exceptions)),
        ("counts", OrderedDict(
            (cls, sum(1 for result in candidates if result["class"] == cls))
            for cls in C8.ACQUIRED_CLASSES
            if any(result["class"] == cls for result in candidates))),
        ("candidates", candidates),
        ("exceptions", exceptions),
    ]))

    print("=== Phase 4/5: recovery cohort ===")
    print("  attempts :", len(results))
    for cls in classes:
        if counts[cls]:
            print("     %-20s %d" % (cls, counts[cls]))
    print("  credits  : %s | $%s of $5.00"
          % (measurement["credits_spent"], measurement["usd_spent"]))
    print("  reached the corrected gate:", len(reached))
    for key in ("publication_grade", "pet_friendly"):
        block = measurement[key]
        print("     %-18s %2d/%-3d point %.3f  wilson [%.3f, %.3f]"
              % (key, block["successes"], block["denominator"], block["point"],
                 block["wilson_lower_95"], block["wilson_upper_95"]))
    print("wrote", OUT_PATH.name, "and", PACKET_PATH.name)


if __name__ == "__main__":
    run()
