# -*- coding: utf-8 -*-
"""PTF-...-PARSER-REPAIR-AND-RETRY-009, Phase 6.

Classifies the retry attempts, CALLING the Pass 008 classifier rather than
restating it. A second batch that reimplements the first's judgement is how two
passes in one market end up disagreeing about what "publication grade" means;
the only thing that differs here is which run directory the artifacts live in.

The founder exception carried out of Pass 008 -- Days Inn Madison Heights,
whose page reads "Sorry not other pets are allowed" where the reader's negative
pattern wants "no other pets" -- is NOT resolved here. That row is a Wyndham
identity and was never in this retry cohort, and the parser repair touched
property-code extraction, not the policy reader. It is re-asserted as an open
exception so a repair to one thing is not mistaken for a repair to the other.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_firecrawl_classification_008 as C8)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-PROPERTY-CODE-PARSER-REPAIR-AND-RETRY-009"
RUN_ID = "detroit-firecrawl-009-retry"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-retry-009")
OUT_PATH = LP / "detroit_ann_arbor_retry_classification_009.json"
PACKET_PATH = LP / "detroit_ann_arbor_retry_founder_exceptions_009.json"

#: A quota refusal is not a fact about the page. The adapter says so itself
#: when it raises: "this is a quota result and says nothing about whether the
#: page is reachable". These rows are unanswered, not walled.
RATE_LIMIT_MARKER = "RATE_LIMITED"


def persisted(slug: str) -> Optional[Dict]:
    """Pass 008's artifact reader, pointed at THIS run's directory."""
    original = C8.RUN_DIR
    try:
        C8.RUN_DIR = RUN_DIR
        return C8.persisted(slug)
    finally:
        C8.RUN_DIR = original


def run() -> None:
    ledger = C8.load(LEDGER_PATH)
    rows = [attempt for attempt in ledger["attempts"]
            if attempt.get("run_id") == RUN_ID]
    if not rows:
        raise SystemExit("no attempts for run %r in the ledger" % RUN_ID)

    census = {row["identity_key"]: row for row in
              C8.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    run_doc = C8.load(LP / "detroit_ann_arbor_retry_run_009.json")
    detail_by_key = {result["identity_key"]: (result.get("refusal_reason") or "")
                     for result in run_doc["results"]}

    results: List[Dict] = []
    for row in rows:
        key = row["identity_key"]
        crow = census.get(key) or {}
        art = persisted(crow.get("slug") or "")
        verdict = C8.classify(row, art)
        detail = detail_by_key.get(key, "")
        rate_limited = RATE_LIMIT_MARKER in detail
        if rate_limited:
            # ACQUISITION_FAILURE is the right class -- nothing was acquired --
            # but the REASON matters for what happens next, so it is carried
            # explicitly rather than left to be inferred from a bare class.
            verdict["why"] = (
                "the plan's own request limit was hit, so this attempt never "
                "reached the property. A quota refusal is not evidence about "
                "the page: the row is unanswered, not walled, and it billed "
                "nothing.")
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
            ("rate_limited", rate_limited),
            ("billed", not rate_limited),
            ("predecessor_attempt_id", row.get("predecessor_attempt_id") or ""),
            ("reading", verdict["reading"]),
        ]))

    counts = Counter(result["class"] for result in results)
    for cls in C8.CLASSES:
        counts.setdefault(cls, 0)
    if sum(counts[cls] for cls in C8.CLASSES) != len(results):
        raise SystemExit("every attempt must fall in exactly one class")

    rate_limited = [result for result in results if result["rate_limited"]]
    by_brand = OrderedDict()
    for brand in sorted({result["brand"] for result in results}):
        sub = [result for result in results if result["brand"] == brand]
        by_brand[brand] = OrderedDict(
            [("attempts", len(sub))]
            + [(cls, sum(1 for result in sub if result["class"] == cls))
               for cls in C8.CLASSES
               if any(result["class"] == cls for result in sub)])

    C8.write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-retry-classification/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", "firecrawl"),
        ("note",
         "The parser-defect retry cohort, classified by the Pass 008 "
         "classifier -- the same code, pointed at this run's artifacts. "
         "Nothing here publishes anything."),
        ("attempts", len(results)),
        ("counts", OrderedDict((cls, counts[cls]) for cls in C8.CLASSES)),
        ("by_brand", by_brand),
        ("rate_limited", OrderedDict([
            ("count", len(rate_limited)),
            ("billed_credits", 0),
            ("what_it_means",
             "these attempts hit the Firecrawl plan's request limit and never "
             "reached the property. They are UNANSWERED, not walled, and they "
             "cost nothing: 19 billed attempts consumed exactly 19 credits. "
             "They are re-runnable at a slower pace, and this order forbids a "
             "second retry of a row, so they are left for a future one."),
            ("identity_keys", [result["identity_key"]
                               for result in rate_limited]),
        ])),
        ("results", results),
    ]))

    exceptions = [result for result in results
                  if result["class"] in C8.EXCEPTION_CLASSES]
    C8.write_lf(PACKET_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-retry-founder-exceptions/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_REVIEW"),
        ("note",
         "EXCEPTIONS ONLY, from the retry cohort. Most are quota refusals "
         "rather than judgements about a page, and are labelled as such."),
        ("count", len(exceptions)),
        ("counts", OrderedDict(
            (cls, sum(1 for result in exceptions if result["class"] == cls))
            for cls in C8.EXCEPTION_CLASSES
            if any(result["class"] == cls for result in exceptions))),
        ("still_open_from_pass_008", OrderedDict([
            ("identity_key", "days inn and suites by wyndham madison heights mi"),
            ("class", "HOLD"),
            ("why_still_open",
             "the property's page reads 'Sorry not other pets are allowed' "
             "where the reader's negative pattern wants 'no other pets'. This "
             "order repaired PROPERTY-CODE EXTRACTION, not the policy reader, "
             "and the row is a Wyndham identity that was never in this retry "
             "cohort. It is not resolved, and it is not resolved "
             "automatically."),
        ])),
        ("exceptions", exceptions),
    ]))

    print("retry attempts classified :", len(results))
    for cls in C8.CLASSES:
        if counts[cls]:
            print("   %-20s %d" % (cls, counts[cls]))
    print("   of which rate-limited (unanswered, $0):", len(rate_limited))
    print("founder exceptions        :", len(exceptions))
    print("wrote", OUT_PATH.name, "and", PACKET_PATH.name)


if __name__ == "__main__":
    run()
