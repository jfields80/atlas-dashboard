# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-SCALE-017, Phases 1 and 2.

Rebuilds the final Hilton cohort from current state and clears it to spend.
NOTHING IS SPENT HERE.

THE COUNT IS REBUILT, NOT INHERITED. Order 016 reported 13 remaining; that is
re-derived here from the committed authority and the paid ledger. Order 016's
own cohort builder is driven rather than restated -- its membership rules are
the ones this order needs, and it already excludes anything Detroit has paid
for, which now includes 016's own ten rows.

WHAT "REMAINING" MEANS HERE. The 13 are rows Detroit has NEVER attempted. Four
Hilton properties were attempted and did not yield publication-grade evidence
(two transient navigation failures, one source-silent page, one ambiguous
block); none is re-bought by this order. A retry needs a declared material
change, and nothing about them has changed -- the transient pair would simply be
a second roll of the same dice at list price.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_hilton_diagnostic_016 as H16)

MARKET = H16.MARKET
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-HILTON-SCALE-017"
RUN_ID = "detroit-brightdata-017-hilton-scale"
AS_OF = "2026-08-30"
FAMILY = "HILTON"

LANE = H16.LANE
CAP_USD = 1.79
MAX_ROWS = 13
#: Balance-derived across orders 013-016: $5.32 over 58 billed attempts.
USD_PER_ATTEMPT = 0.0917

LP = H16.LP
ADMITTED_PATH = LP / "detroit_ann_arbor_hilton_admitted_017.json"
PLAN_PATH = LP / "detroit_ann_arbor_hilton_cost_plan_017.json"

if __name__ == "__main__":
    # Drive order 016's builder with this order's identity and limits. Its
    # eligibility rules are unchanged; only the scope and the caps differ.
    H16.WORK_ORDER = WORK_ORDER
    H16.RUN_ID = RUN_ID
    H16.AS_OF = AS_OF
    H16.CAP_USD = CAP_USD
    H16.MAX_ROWS = MAX_ROWS
    H16.USD_PER_ATTEMPT = USD_PER_ATTEMPT
    H16.ADMITTED_PATH = ADMITTED_PATH
    H16.PLAN_PATH = PLAN_PATH
    # 016's own results are already excluded by the ledger check, but naming
    # the file makes the intent explicit rather than incidental.
    H16.PRIOR_CLASSIFICATIONS = H16.PRIOR_CLASSIFICATIONS + (
        LP / "detroit_ann_arbor_hilton_classification_016.json",)
    H16.run()
