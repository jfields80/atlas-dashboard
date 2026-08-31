# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012 -- status.

Detroit's position after the exceptions, and the Bright Data pilot re-derived
against current authority.

It drives order 011's status module with its inputs pointed at this order: the
holds packet must read THIS order's candidate set, or it reports two holds that
this order's founder dispositions have already answered.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_holds_and_status_011 as S11)

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012"

if __name__ == "__main__":
    S11.WORK_ORDER = WORK_ORDER
    S11.CANDIDATES = S11.LP / "detroit_ann_arbor_reconciled_candidates_012.json"
    S11.HOLDS_PATH = S11.LP / "detroit_ann_arbor_hold_exceptions_012.json"
    S11.STATUS_PATH = S11.LP / "detroit_ann_arbor_status_012.json"
    S11.PILOT_PATH = S11.LP / "detroit_ann_arbor_brightdata_pilot_cohort_012.json"
    S11.run()
