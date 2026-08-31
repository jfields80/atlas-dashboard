# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-SCALE-017, Phases 3 to 5.

Acquires the final Hilton cohort. Drives order 013's runner with the exclusive
lock and, as order 016 established, the cap enforced against ACTUAL PREPAID
BALANCE MOVEMENT re-read before every attempt.

The balance is the control because the vendor's month-to-date meter has now
restated in both directions across these orders -- downward during 015, upward
after 016. A cap held against a figure that moves on its own is not a cap.
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
    detroit_ann_arbor_hilton_scale_017 as S17)

if __name__ == "__main__":
    P13.WORK_ORDER = S17.WORK_ORDER
    P13.RUN_ID = S17.RUN_ID
    P13.CAP_USD = S17.CAP_USD
    P13.USD_CEILING_PER_ATTEMPT = S17.USD_PER_ATTEMPT
    P13.ADMITTED_PATH = S17.ADMITTED_PATH
    P13.PLAN_PATH = S17.PLAN_PATH

    R13.WORK_ORDER = S17.WORK_ORDER
    R13.RUN_ID = S17.RUN_ID
    R13.CAP_USD = S17.CAP_USD
    R13.CEILING = S17.USD_PER_ATTEMPT
    R13.ENFORCE_CAP_AGAINST_BALANCE = True
    R13.RUN_PATH = S17.LP / "detroit_ann_arbor_hilton_run_017.json"
    R13.RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                   / "detroit-ann-arbor-hilton-017")
    R13.LOCK_PATH = R13.RUN_DIR / ".run-in-progress.lock"

    try:
        asyncio.run(R13.main())
    finally:
        R13.release_lock()
