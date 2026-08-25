"""PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005 -- the final Milwaukee Choice matrix.

Three artifacts have to agree before anyone touches the router, and until now
they have lived apart:

    ptf_firecrawl_choice_validation_004.json   the fifteen-property sample
    ptf_choice_failure_retry_005.json          the two failures, retried
    ptf_choice_reader_rederive_005.json        the held record, re-read offline

This module folds them into one matrix, in that order, so each property appears
exactly once and carries its most recent honest state. Nothing is re-fetched:
every number here already exists somewhere on disk, and the only work is making
the three agree.

Where the counts deliberately do not flatter the result
-------------------------------------------------------
The re-derivation REMOVED a complete policy. Country Inn Milwaukee Airport was
counted complete in 004 on the strength of being a refusal; it is now
SOURCE_CONTRADICTORY and is complete no longer. Folding the retries in without
folding that out would have produced 15/15 complete, which is not true and would
have been the flattering direction.

The Web Unlocker's fallback value is reported as UNTESTED rather than as zero.
It was never invoked because Firecrawl succeeded on all fifteen, and "not
needed on this sample" is a different claim from "adds nothing".
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_choice_validation_004 as CV  # noqa: E402

WORK_ORDER = "PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005"
MARKET = "milwaukee-wi"
BRAND = "CHOICE"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"

VALIDATION = REPORTS / "ptf_firecrawl_choice_validation_004.json"
RETRY = REPORTS / "ptf_choice_failure_retry_005.json"
REDERIVE = REPORTS / "ptf_choice_reader_rederive_005.json"

#: Bright Data's own result over the same fifteen, from the production run.
UNLOCKER_PUBLICATION_GRADE = 7


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _slugify(name: str) -> str:
    import re
    s = name.lower().replace("&", "").replace(",", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def fold() -> List[Dict]:
    """One row per property, newest honest state wins."""
    rows = {r["identity_key"]: dict(r) for r in _load(VALIDATION)["items"]}

    # 1. The retried failures replace their 004 rows outright.
    for row in _load(RETRY)["items"]:
        rows[row["identity_key"]] = dict(row)

    # 2. The offline re-derivation replaces only the EXTRACTION and its
    #    classification. It re-read a persisted artifact, so it says nothing
    #    about acquisition, timing or cost and must not overwrite them.
    if REDERIVE.is_file():
        rederived = {r["slug"]: r for r in _load(REDERIVE)["rederived"]}
        for key, row in rows.items():
            entry = rederived.get(_slugify(row["canonical_name"]))
            if not entry or entry.get("state") != "REDERIVED":
                continue
            if entry["extraction"] == (row.get("firecrawl_extraction") or {}):
                continue
            row["firecrawl_extraction_before_reader_fix"] = dict(
                row.get("firecrawl_extraction") or {})
            row["firecrawl_extraction"] = dict(entry["extraction"])
            row["firecrawl_field_count"] = len(entry["extraction"])
            row["reader_state"] = entry["state_class"]
            row["reader_notes"] = entry.get("parser_notes") or []
            if entry["state_class"] == "SOURCE_CONTRADICTORY":
                # A record the source contradicts is not a complete policy and
                # is not publishable, whatever its evidence package looks like.
                row["policy_completeness"] = {
                    "basis": "SOURCE_CONTRADICTORY",
                    "complete": False,
                    "why": ("the property's own page states pet terms and also "
                            "states that it does not allow pets; neither side "
                            "is published")}
    return sorted(rows.values(), key=lambda r: r["identity_key"])


def build(write: bool = False) -> Dict:
    rows = fold()
    acquired = [r for r in rows
                if str(r.get("firecrawl_state", "")).startswith("ACQUIRED")]
    pub = [r for r in rows
           if r.get("firecrawl_state") == "ACQUIRED_PUBLICATION_GRADE"]
    # CV._is_complete, not a fresh predicate: the three rows PTF-FIRECRAWL-
    # HARD-LANES-003 contributed carry a bare ``complete`` flag and no
    # ``policy_completeness`` block, and a stricter reading here would score
    # them incomplete and quietly understate the result by three.
    complete = [r for r in rows if CV._is_complete(r)]
    contradictory = [r for r in rows
                     if r.get("reader_state") == "SOURCE_CONTRADICTORY"]

    compared = [r for r in rows if r.get("comparable") and r.get("comparison")]
    verdicts: Counter = Counter()
    structured = 0
    for r in compared:
        verdicts.update(r["comparison"]["counts"])
        structured += len(r["comparison"].get("structured_mismatches") or {})

    wrong: Counter = Counter()
    for r in rows:
        for name, flag in (r.get("false_facts") or {}).items():
            if flag:
                wrong[name] += 1

    # A refusal must never arrive carrying ordinary-pet terms. Re-checked on
    # the FINAL extractions, not trusted from an earlier stage.
    residual = {r["identity_key"]: CV.refusal_carrying_pet_terms(
        r.get("firecrawl_extraction") or {})
        for r in rows
        if CV.refusal_carrying_pet_terms(r.get("firecrawl_extraction") or {})}

    times = [r["firecrawl_elapsed_seconds"] for r in rows
             if r.get("firecrawl_elapsed_seconds")]
    retry_doc = _load(RETRY)
    credits = (_load(VALIDATION)["cost"]["combined_15_credits"]
               + (retry_doc["cost"]["measured_credits"] or 0))

    unlocker_probes = [r for r in rows if r.get("unlocker_fallback")]
    unlocker_recoveries = [
        r for r in unlocker_probes
        if str((r["unlocker_fallback"] or {}).get("state", "")).startswith("ACQUIRED")]

    doc = {
        "schema": "ptf-choice-coverage-matrix/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "note": ("Folds the 004 fifteen-property sample, the 005 retry of its "
                 "two failures, and the 005 offline re-derivation of its held "
                 "record into one matrix. No property is counted twice and "
                 "nothing was re-fetched to produce it."),
        "sources": [str(p.relative_to(REPO)) for p in (VALIDATION, RETRY, REDERIVE)
                    if p.is_file()],
        "total": len(rows),
        "firecrawl_acquired": len(acquired),
        "web_unlocker_unique_recoveries": len(unlocker_recoveries),
        "web_unlocker_fallback_value": (
            "UNTESTED_ON_THIS_SAMPLE: the fallback was never invoked because "
            "Firecrawl acquired all fifteen. That is not evidence the fallback "
            "adds nothing -- it is evidence it was not needed here. The Web "
            "Unlocker independently holds %d of these fifteen at publication "
            "grade, which is why it stays in the lane."
            % UNLOCKER_PUBLICATION_GRADE),
        "combined_firecrawl_then_unlocker": len(acquired) + len(unlocker_recoveries),
        "publication_grade": len(pub),
        "intrinsically_complete": len(complete),
        "structured_mismatch": structured,
        "internal_contradiction": len(contradictory),
        "internal_contradiction_keys": [r["identity_key"] for r in contradictory],
        "residual_refusals_carrying_pet_terms": residual,
        "false_pets_allowed": wrong.get("false_pets_allowed", 0),
        "false_no_pets": wrong.get("false_no_pets", 0),
        "false_fee": wrong.get("false_fee", 0),
        "false_weight": wrong.get("false_weight", 0),
        "false_species": wrong.get("false_species", 0),
        "compared_against_bright_data": len(compared),
        "match": verdicts.get("MATCH", 0),
        "extra": verdicts.get("EXTRA", 0),
        "missing": verdicts.get("MISSING", 0),
        "avg_firecrawl_seconds": round(statistics.mean(times), 1) if times else None,
        "median_firecrawl_seconds": round(statistics.median(times), 1) if times else None,
        "firecrawl_credits": credits,
        "bright_data_reference": {
            "publication_grade_over_the_same_fifteen": UNLOCKER_PUBLICATION_GRADE,
            "access_denied": 4,
            "never_attempted_budget_stopped": 4,
            "avg_seconds": 130.0,
            "usd_per_attempted_property": 0.197,
        },
        "known_remaining_defects": [
            {"defect": "weight_limit not extracted from 'A size limit of 40 "
                       "pounds' (Sleep Inn & Suites Milwaukee Airport)",
             "class": "PRE_EXISTING_PATTERN_GAP",
             "caused_by_this_work_order": False,
             "evidence": ("no pattern in policy_reading._WEIGHT_RES matches "
                          "that wording, and no drop note fired, so the miss "
                          "predates the reader change made here"),
             "action": ("NOT FIXED. Outside the three items this work order was "
                        "opened for. A weight pattern change re-reads every "
                        "brand's corpus and deserves its own measurement.")},
        ],
        "authority_written": False,
        "routes_changed": False,
        "items": rows,
    }
    if write:
        out = REPORTS / "ptf_choice_coverage_matrix_005.json"
        out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                        .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    d = build(write=args.write)
    print("FIRECRAWL_ACQUIRED:               %d/%d" % (d["firecrawl_acquired"], d["total"]))
    print("WEB_UNLOCKER_UNIQUE_RECOVERIES:   %d" % d["web_unlocker_unique_recoveries"])
    print("COMBINED_FIRECRAWL_THEN_UNLOCKER: %d/%d"
          % (d["combined_firecrawl_then_unlocker"], d["total"]))
    print("PUBLICATION_GRADE:                %d" % d["publication_grade"])
    print("INTRINSICALLY_COMPLETE:           %d" % d["intrinsically_complete"])
    print("STRUCTURED_MISMATCH:              %d" % d["structured_mismatch"])
    print("INTERNAL_CONTRADICTION:           %d" % d["internal_contradiction"])
    print("FALSE_PETS_ALLOWED:               %d" % d["false_pets_allowed"])
    print("FALSE_NO_PETS:                    %d" % d["false_no_pets"])
    print("AVG_FIRECRAWL_SECONDS:            %s" % d["avg_firecrawl_seconds"])
    print("FIRECRAWL_CREDITS:                %d" % d["firecrawl_credits"])
    print()
    print("compared against bright data: %d | MATCH %d | MISSING %d | EXTRA %d"
          % (d["compared_against_bright_data"], d["match"], d["missing"], d["extra"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
