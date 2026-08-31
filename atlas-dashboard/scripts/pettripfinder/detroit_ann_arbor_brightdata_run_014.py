# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-PILOT-014, Phase 3.

Runs the second pilot. It DRIVES ORDER 013's runner rather than restating it,
with its cohort, cap, run id and lock pointed at this order.

013's runner already carries the two things that matter: one sanctioned attempt
per row with no retry and no fallback provider, and an exclusive lock taken
before the first paid call. The lock is why this order can be run without
repeating 013's overspend -- it makes a second concurrent runner impossible
rather than merely discouraged.
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
    detroit_ann_arbor_brightdata_pilot_014 as P14,
    detroit_ann_arbor_brightdata_run_013 as R13)

if __name__ == "__main__":
    # 013's runner reads its inputs from P13; point every one at this order.
    P13.WORK_ORDER = P14.WORK_ORDER
    P13.RUN_ID = P14.RUN_ID
    P13.CAP_USD = P14.CAP_USD
    P13.USD_CEILING_PER_ATTEMPT = P14.USD_PER_ATTEMPT
    P13.ADMITTED_PATH = P14.ADMITTED_PATH
    P13.PLAN_PATH = P14.PLAN_PATH

    R13.WORK_ORDER = P14.WORK_ORDER
    R13.RUN_ID = P14.RUN_ID
    R13.CAP_USD = P14.CAP_USD
    R13.CEILING = P14.USD_PER_ATTEMPT
    R13.RUN_PATH = P14.LP / "detroit_ann_arbor_brightdata_run_014.json"
    R13.RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                   / "detroit-ann-arbor-brightdata-014")
    R13.LOCK_PATH = R13.RUN_DIR / ".run-in-progress.lock"

    try:
        asyncio.run(R13.main())
    finally:
        R13.release_lock()
