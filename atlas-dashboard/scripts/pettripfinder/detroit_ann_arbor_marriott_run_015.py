# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-MARRIOTT-SCALE-015, Phase 5.

Acquires the admitted Marriott cohort. Drives order 013's runner, whose
guarantees this order needs unchanged: one sanctioned Bright Data attempt per
row, no retry, no fallback provider, every attempt written to the durable
ledger before anything can raise, and an exclusive lock taken before the first
paid call.
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
    detroit_ann_arbor_marriott_scale_015 as S15)

if __name__ == "__main__":
    P13.WORK_ORDER = S15.WORK_ORDER
    P13.RUN_ID = S15.RUN_ID
    P13.CAP_USD = S15.CAP_USD
    P13.USD_CEILING_PER_ATTEMPT = S15.USD_PER_ATTEMPT
    P13.ADMITTED_PATH = S15.ADMITTED_PATH
    P13.PLAN_PATH = S15.PLAN_PATH

    R13.WORK_ORDER = S15.WORK_ORDER
    R13.RUN_ID = S15.RUN_ID
    R13.CAP_USD = S15.CAP_USD
    R13.CEILING = S15.USD_PER_ATTEMPT
    R13.RUN_PATH = S15.LP / "detroit_ann_arbor_marriott_run_015.json"
    R13.RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                   / "detroit-ann-arbor-marriott-015")
    R13.LOCK_PATH = R13.RUN_DIR / ".run-in-progress.lock"

    try:
        asyncio.run(R13.main())
    finally:
        R13.release_lock()
