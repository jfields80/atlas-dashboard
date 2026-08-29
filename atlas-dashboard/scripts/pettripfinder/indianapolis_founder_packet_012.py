# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-TARGETED-POLICY-ACQUISITION-012 -- the exception-only founder packet.

Fifty authorised properties were acquired. This turns what came back into
something a founder can rule on without reading fifty pages.

WHAT THE ``indicative_reading`` IS, AND WHAT IT IS NOT
------------------------------------------------------
It is a machine's first pass over a quoted policy block, kept so a reviewer can
sort. It is NOT a decision and it is NOT authority. This codebase has learned
both ways it goes wrong: a service-animal sentence is a legal access category
and never a pet permission, and a "fee" token says a fee was MENTIONED, never
that it APPLIES. Every row carries its block verbatim so the reading can be
argued with rather than trusted.

A row whose block reads BOTH ways, or neither, is surfaced as an exception --
those are the ones where a first pass is worth nothing and a person is worth
everything.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

LP = Path(__file__).resolve().parents[2] / "launch_packages" / "pettripfinder"

_REFUSES = re.compile(
    r"pets?\s*(are\s*)?not\s*allowed|pets\s*allowed\s*:\s*no|"
    r"no\s*pets\s*allowed|sorry\s*no\s*other\s*pets|only\s*service\s*animals",
    re.I)
_ALLOWS = re.compile(
    r"pets?\s*(are\s*)?allowed|pets\s*welcome|pet\s*fee|pet\s*policy\s*pets\s*welcome",
    re.I)


def _block(artifact_dir: str) -> str:
    path = os.path.join((artifact_dir or "").replace(chr(92), "/"),
                        "policy-block.txt")
    if not os.path.isfile(path):
        return ""
    return open(path, encoding="utf-8", errors="replace").read().strip()


def _reading(outcome: str, block: str) -> str:
    if outcome != "VALID":
        return "NO_EVIDENCE"
    refuses, allows = bool(_REFUSES.search(block)), bool(_ALLOWS.search(block))
    if refuses and allows:
        return "READS_BOTH_WAYS_NEEDS_A_RULING"
    if refuses:
        return "READS_AS_NO_PETS"
    if allows:
        return "READS_AS_PET_FRIENDLY"
    return "READS_NEITHER_WAY"


def build() -> Dict:
    run = json.loads((LP / "indianapolis_in_market_acquisition_012.json")
                     .read_text(encoding="utf-8"))
    auth = json.loads((LP / "indianapolis_in_authorized_cohort_012.json")
                      .read_text(encoding="utf-8"))

    rows: List[Dict] = []
    for result in run["results"]:
        block = _block(result.get("artifact_dir", ""))
        rows.append(OrderedDict((
            ("identity_key", result["identity_key"]),
            ("canonical_name", result.get("canonical_name", "")),
            ("brand", result.get("brand", "")),
            ("outcome", result.get("outcome")),
            ("final_state", result.get("final_state")),
            ("publication_grade", bool(result.get("publication_grade"))),
            ("provider", result.get("provider")),
            ("source_url", result.get("source_url", "")),
            ("policy_block", block),
            ("indicative_reading", _reading(result.get("outcome", ""), block)),
            ("artifact_dir", result.get("artifact_dir", "")),
            ("detail", (result.get("detail") or "")[:220]),
        )))

    review = [r for r in rows if r["publication_grade"]]
    exceptions = [r for r in rows
                  if r["indicative_reading"] in
                  ("READS_BOTH_WAYS_NEEDS_A_RULING", "READS_NEITHER_WAY")
                  or r["outcome"] != "VALID"]
    gate = run["authorized_cohort"]

    return OrderedDict((
        ("schema", "ptf-founder-review-packet/1.0"),
        ("market_id", "indianapolis-in"),
        ("work_order", "PTF-INDIANAPOLIS-TARGETED-POLICY-ACQUISITION-012"),
        ("status", "EXCEPTIONS_ONLY"),
        ("nothing_is_published_by_this_file",
         "This packet proposes. It signs no row, promotes no identity and "
         "publishes nothing. Every indicative_reading is a machine's first "
         "pass over a quoted block, never a decision: a service-animal "
         "sentence is a legal access category and not a pet permission, and a "
         "'fee' token says MENTIONED, not APPLIES."),
        ("authorized_cohort", OrderedDict((
            ("authorised", auth["cohort_count"]),
            ("attempted", run["attempted"]),
            ("authorised_but_not_payable",
             gate["authorised_but_not_eligible"]),
            ("unauthorized_backlog", gate["unauthorized_backlog"]),
            ("backlog_state", "NOT_AUTHORIZED_THIS_WORK_ORDER"),
            ("backlog_note", "eligible for acquisition and deliberately not "
                             "bought; it needs its own cost plan and its own "
                             "approval, and it is not a budget casualty"),
        ))),
        ("counts", OrderedDict((
            ("attempted", run["attempted"]),
            ("valid", run["outcome_counts"].get("VALID", 0)),
            ("publication_grade", run["publication_grade"]),
            ("by_outcome", run["outcome_counts"]),
            ("by_indicative_reading", OrderedDict(sorted(
                Counter(r["indicative_reading"] for r in rows).items()))),
            ("candidates_for_review", len(review)),
            ("exceptions_surfaced", len(exceptions)),
        ))),
        ("review_candidates", review),
        ("exceptions", exceptions),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    doc = build()
    if args.out:
        Path(args.out).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    counts = doc["counts"]
    print("attempted             %d" % counts["attempted"])
    print("publication-grade     %d" % counts["publication_grade"])
    print("by indicative reading %s" % dict(counts["by_indicative_reading"]))
    print("candidates for review %d" % counts["candidates_for_review"])
    print("exceptions surfaced   %d" % counts["exceptions_surfaced"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
