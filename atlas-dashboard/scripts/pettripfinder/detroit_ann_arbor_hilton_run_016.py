# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-DIAGNOSTIC-016, Phase 3.

Runs the Hilton diagnostic through order 013's runner, with the cap enforced
against ACTUAL PREPAID BALANCE MOVEMENT as well as the assumed rate.

That second guard is switched on here for a specific reason. Ten attempts cost
about $0.89 at the balance-derived rate order 015 established, comfortably
inside the $1.50 cap -- but at the month-to-date-derived rate orders 013 and 014
used ($0.152) the same ten would be $1.52, marginally OVER. The two readings
disagree, so this run does not pick a winner and hope: it re-reads the balance
before every attempt and stops on the measurement.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_brightdata_pilot_013 as P13,
    detroit_ann_arbor_brightdata_run_013 as R13,
    detroit_ann_arbor_hilton_diagnostic_016 as H16)

if __name__ == "__main__":
    P13.WORK_ORDER = H16.WORK_ORDER
    P13.RUN_ID = H16.RUN_ID
    P13.CAP_USD = H16.CAP_USD
    P13.USD_CEILING_PER_ATTEMPT = H16.USD_PER_ATTEMPT
    P13.ADMITTED_PATH = H16.ADMITTED_PATH
    P13.PLAN_PATH = H16.PLAN_PATH

    R13.WORK_ORDER = H16.WORK_ORDER
    R13.RUN_ID = H16.RUN_ID
    R13.CAP_USD = H16.CAP_USD
    R13.CEILING = H16.USD_PER_ATTEMPT
    R13.ENFORCE_CAP_AGAINST_BALANCE = True
    R13.RUN_PATH = H16.LP / "detroit_ann_arbor_hilton_run_016.json"
    R13.RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                   / "detroit-ann-arbor-hilton-016")
    R13.LOCK_PATH = R13.RUN_DIR / ".run-in-progress.lock"

    try:
        asyncio.run(R13.main())
    finally:
        R13.release_lock()
