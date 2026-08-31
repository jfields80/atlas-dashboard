# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019, Phases 4 and 5.

Applies the gated clean candidates through order 011's authority path.

011's builders are the sanctioned ones and they are driven, not restated: they
project facts from the committed reader rather than authoring them, re-verify
every artifact hash from disk, check every cited quote appears verbatim in the
persisted block, and refuse the whole run if any row fails a contract. Acquisition
provenance travels with each record -- which paid order acquired it, and on which
attempt.
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
    detroit_ann_arbor_authority_application_011 as A11,
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019"
LP = A11.LP
PRECHECK = LP / "detroit_ann_arbor_brightdata_precheck_019.json"
CANDIDATES = LP / "detroit_ann_arbor_clean_candidates_019.json"
DECISIONS = LP / "detroit_ann_arbor_founder_decisions_019.json"

CLAUSE = ("Apply every clean Bright Data candidate from orders 013-018 that "
          "passes the current publication gates. Do not loosen a gate to "
          "preserve a projected total.")

if __name__ == "__main__":
    precheck = R11.load(PRECHECK)
    rows = precheck["passed_rows"]
    R11.write_lf(CANDIDATES, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-reconciled-candidates/1.0"),
        ("work_order", WORK_ORDER), ("market_id", A11.MARKET),
        ("as_of", "2026-08-30"),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note", "the gated clean block from the 019 precheck, in the shape "
                 "order 011's authority application consumes."),
        ("gates", OrderedDict([
            ("clean", len(rows)),
            ("clean_counts", OrderedDict(
                (cls, sum(1 for r in rows if r["class"] == cls))
                for cls in ("PET_FRIENDLY", "VERIFIED_NO_PETS"))),
            ("rejected", len(precheck["rejected_rows"])),
        ])),
        ("clean_candidates", [
            OrderedDict([
                ("identity_key", r["identity_key"]),
                ("canonical_name", r["canonical_name"]),
                ("brand", r["brand"]),
                ("class", r["class"]),
                ("source_pass", r["acquired_by_order"]),
                ("attempt_id", r["attempt_id"]),
                ("canonical_url", r["canonical_url"]),
                ("reading", r["reading"]),
            ]) for r in rows]),
        ("rejected_candidates", precheck["rejected_rows"]),
        ("holds", []),
    ]))

    A11.CANDIDATES = CANDIDATES
    A11.DECISIONS_PATH = DECISIONS
    A11.WORK_ORDER = WORK_ORDER
    A11.AUTHORISATION_CLAUSE = CLAUSE
    A11.DECISION_DATE = "2026-08-30"
    A11.run()
