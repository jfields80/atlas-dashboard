# -*- coding: utf-8 -*-
"""PTF-...-PARSER-REPAIR-AND-RETRY-009, Phases 2 and 3.

Rebuilds the retry cohort OFFLINE, from the repaired parser and the committed
ledger, before a single credit is spent.

The authorisation is narrow on purpose: re-run the rows that were blocked BY
THIS DEFECT. So membership is not "everything that failed in Pass 008" -- it is
derived, per row, from three questions that each have a checkable answer:

  1. Did Pass 008 refuse it as UNEXPECTED_PAGE?
  2. Did the COMMITTED parser return no code (or the wrong one) for it, and
     does the REPAIRED parser now return the expected code? That is what makes
     the defect the cause rather than a coincidence.
  3. Is it still payable -- not already answered, not a duplicate page, not
     superseded by evidence another market already bought?

A row that fails 1 or 2 was blocked by something else and is NOT swept in. A
row that fails 3 is suppressed with its reason. ACCESS_DENIED rows are excluded
by construction: that gate fires before the code is ever consulted, so the
refusal was real and re-running it would be buying the same wall twice.

These 49 pages were already paid for once. The retry is legitimate only because
the parser defect is a declared MATERIAL CHANGE, and every retry row carries
that reason explicitly. The original attempts are not rewritten or removed --
the ledger records what this project paid, including for pages it then threw
away.
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

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-PROPERTY-CODE-PARSER-REPAIR-AND-RETRY-009"
PRIOR_RUN = "detroit-firecrawl-008"
AS_OF = "2026-08-29"

#: Named once, carried on every retry row and every ledger write.
MATERIAL_CHANGE = (
    "PROPERTY_CODE_PATTERNS could not read an IHG or Choice property code off "
    "those brands' canonical URL shapes, so page_health compared an empty "
    "string against the expected code and refused the page before it could be "
    "judged. The pattern is repaired under %s and proven on this market's own "
    "URLs. The page was never read on the first attempt, so this is a retry "
    "against a changed identity gate -- not a second look at the same result."
    % WORK_ORDER)

#: The committed patterns, as they stood when Pass 008 ran. Kept verbatim so
#: this replay can show what the parser DID, not merely what it does now.
COMMITTED_PATTERNS = {
    "IHG": r"/hotels/[a-z]{2}/[a-z]+/([a-z0-9]{5})/",
    "CHOICE": r"/[a-z]{2}/[a-z-]+/[a-z-]+-hotel/([a-z0-9]{4,8})",
}

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CLASSIFICATION = LP / "detroit_ann_arbor_firecrawl_classification_008.json"
QUALIFICATION = LP / "detroit_ann_arbor_firecrawl_lane_qualification_008.json"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
OUT_PATH = LP / "detroit_ann_arbor_retry_cohort_009.json"


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def committed_parse(url: str, brand: str) -> str:
    import re
    pattern = COMMITTED_PATTERNS.get(brand)
    if not pattern:
        return ""
    match = re.search(pattern, url or "", re.IGNORECASE)
    return match.group(1).lower() if match else ""


def run() -> None:
    classification = load(CLASSIFICATION)
    qualification = load(QUALIFICATION)
    ledger = load(LEDGER_PATH)

    row_by_key = {row["identity_key"]: row
                  for row in qualification["qualified_rows"]}

    candidates: List[Dict] = []
    not_this_defect: List[Dict] = []

    for result in classification["results"]:
        key = result["identity_key"]
        source = row_by_key.get(key) or {}
        expected = (source.get("property_code") or "").lower()
        url = result["canonical_url"]
        brand = result["brand"]
        before = committed_parse(url, brand)
        after = PS.property_code(url, brand).lower()

        # Question 1 and 2, together. Both must hold.
        blocked_here = result["class"] == "UNEXPECTED_PAGE"
        defect_caused = bool(expected) and before != expected
        repaired = bool(expected) and after == expected

        if blocked_here and defect_caused and repaired:
            candidates.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", result["canonical_name"]),
                ("brand", brand),
                ("canonical_url", url),
                ("property_code_expected", expected),
                ("property_code_committed_parser_returned", before or "(empty)"),
                ("property_code_repaired_parser_returns", after),
                ("pass_008_class", result["class"]),
                ("pass_008_attempt_id", result["attempt_id"]),
                ("material_change_reason", MATERIAL_CHANGE),
            ]))
        else:
            not_this_defect.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", result["canonical_name"]),
                ("brand", brand),
                ("pass_008_class", result["class"]),
                ("why_not_in_the_retry",
                 "Pass 008 did not refuse this row as UNEXPECTED_PAGE, so the "
                 "property-code defect is not what blocked it"
                 if not blocked_here else
                 "the committed parser already returned the expected code for "
                 "this row, so the defect is not what blocked it"
                 if not defect_caused else
                 "the repaired parser still does not return the expected code "
                 "for this row, so the repair does not unblock it"),
            ]))

    # ---- Phase 3: the paid ledger, before any provider call --------------- #
    index = PAL.LedgerIndex(ledger)
    attempt_by_id = {attempt.get("attempt_id"): attempt
                     for attempt in ledger["attempts"]}
    payable, suppressed = [], []
    reasons: Counter = Counter()
    seen_url, seen_identity = {}, {}

    # Every prior attempt on these pages, so a row that a LATER attempt already
    # answered is never bought again.
    acquired_keys = {row["identity_key"] for row in ledger["attempts"]
                     if row.get("market_id") == MARKET
                     and row.get("publication_grade")}

    for row in candidates:
        ledger_row = OrderedDict([
            ("identity_key", row["identity_key"]),
            ("canonical_url", row["canonical_url"]),
            ("market_id", MARKET),
            ("property_code", row["property_code_expected"]),
            ("brand", row["brand"]),
        ])
        if row["identity_key"] in acquired_keys:
            reasons["ALREADY_ACQUIRED_PUBLICATION_GRADE"] += 1
            suppressed.append(OrderedDict([
                ("identity_key", row["identity_key"]),
                ("reason", "ALREADY_ACQUIRED_PUBLICATION_GRADE"),
                ("why", "a later attempt on this identity already returned "
                        "publication-grade evidence; buying the page again "
                        "would pay for an answer this project holds"),
            ]))
            continue

        # The cross-run ledger decides whether the PAGE may be bought. A prior
        # attempt that this order declares materially changed must not be read
        # as "already paid, do not retry", so the verdict is consulted and then
        # the material change is applied on top of it -- explicitly, and only
        # for the specific prior attempts this defect caused.
        verdict = PAL.decide(ledger_row, index, available_lanes=("firecrawl",))
        # ``matched_attempts`` are attempt IDS. Resolve every one of them
        # against the ledger rather than trusting the summarised ``prior_*``
        # fields, which describe the latest match only: the override must hold
        # for EVERY prior payment on this page, not just the most recent.
        matched = [attempt_by_id[attempt_id]
                   for attempt_id in (verdict.get("matched_attempts") or [])
                   if attempt_id in attempt_by_id]
        prior_all_defect_blocked = bool(matched) and all(
            attempt.get("run_id") == PRIOR_RUN
            and attempt.get("outcome") == "UNEXPECTED_PAGE"
            for attempt in matched)
        if (verdict["decision"] in PAL.SUPPRESSED_DECISIONS
                and not prior_all_defect_blocked):
            reasons[verdict["decision"]] += 1
            suppressed.append(OrderedDict([
                ("identity_key", row["identity_key"]),
                ("reason", verdict["decision"]),
                ("why", verdict["reason"]),
                ("note", "not overridden by the material change: at least one "
                         "prior paid attempt on this page was something other "
                         "than a defect-blocked refusal"),
            ]))
            continue

        url = PAL.canonical_url(ledger_row)
        if url in seen_url:
            reasons["DUPLICATE_CANONICAL_URL_IN_COHORT"] += 1
            suppressed.append(OrderedDict([
                ("identity_key", row["identity_key"]),
                ("reason", "DUPLICATE_CANONICAL_URL_IN_COHORT"),
                ("why", "the same page is already in this retry cohort as %r"
                        % seen_url[url]),
            ]))
            continue
        identity = (PAL.property_identity(ledger_row)
                    if hasattr(PAL, "property_identity") else "")
        if identity and identity in seen_identity:
            reasons["DUPLICATE_PROPERTY_IDENTITY_IN_COHORT"] += 1
            suppressed.append(OrderedDict([
                ("identity_key", row["identity_key"]),
                ("reason", "DUPLICATE_PROPERTY_IDENTITY_IN_COHORT"),
                ("why", "the same building is already in this retry cohort as "
                        "%r" % seen_identity[identity]),
            ]))
            continue
        seen_url[url] = row["identity_key"]
        if identity:
            seen_identity[identity] = row["identity_key"]
        row["ledger_decision"] = verdict["decision"]
        row["ledger_reason"] = verdict["reason"]
        row["predecessor_attempt_id"] = verdict.get(
            "predecessor_attempt_id") or ""
        row["retry_permitted_by"] = (
            "the declared material change; every prior paid attempt on this "
            "page in the ledger is a Pass 008 defect-blocked refusal")
        payable.append(row)

    by_brand = Counter(row["brand"] for row in payable)
    write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-retry-cohort/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("lane", "firecrawl"),
        ("authorisation",
         "re-run ONLY the rows blocked by the property-code parser defect; no "
         "expansion beyond them"),
        ("material_change_reason", MATERIAL_CHANGE),
        ("derivation",
         "membership is derived per row, not inherited from 'failed in Pass "
         "008': the row must have been refused as UNEXPECTED_PAGE, the "
         "COMMITTED parser must have returned something other than its "
         "expected code, and the REPAIRED parser must now return that code. "
         "ACCESS_DENIED rows are excluded by construction -- that gate fires "
         "before the code is consulted, so the refusal was real."),
        ("pass_008_attempts_considered", len(classification["results"])),
        ("defect_blocked_candidates", len(candidates)),
        ("excluded_not_this_defect", len(not_this_defect)),
        ("suppressed", len(suppressed)),
        ("suppression_reasons", dict(reasons)),
        ("retry_cohort_size", len(payable)),
        ("retry_cohort_by_brand", dict(by_brand)),
        ("expected_property_code_parses",
         "%d/%d -- every row in the cohort parses to its expected code under "
         "the repaired parser, by construction of the membership test"
         % (len(payable), len(payable))),
        ("excluded_rows", not_this_defect),
        ("suppressed_rows", suppressed),
        ("retry_cohort", payable),
    ]))

    print("=== Phase 2: offline replay with the repaired parser ===")
    print("  Pass 008 attempts considered :", len(classification["results"]))
    print("  defect-blocked candidates    :", len(candidates))
    print("  excluded (a different cause) :", len(not_this_defect))
    print()
    print("=== Phase 3: paid-ledger check (no provider call yet) ===")
    print("  suppressed                   :", len(suppressed),
          dict(reasons) or "-")
    print("  RETRY COHORT                 :", len(payable), dict(by_brand))
    print("  every row names the material change:",
          all(row.get("material_change_reason") for row in payable))
    print("wrote", OUT_PATH.name)


if __name__ == "__main__":
    run()
