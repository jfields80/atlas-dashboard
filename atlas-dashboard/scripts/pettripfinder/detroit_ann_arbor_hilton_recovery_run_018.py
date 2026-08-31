# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-INFRA-RECOVERY-018, Phases 4 and 5.

Runs the recovery cohort with the per-attempt CLI balance query OFF -- which is
this order's declared material change, not merely a setting.

Every recovery attempt names its order-017 predecessor and carries
MATERIAL_CHANGE_INFRASTRUCTURE_RECOVERY, so the ledger shows a page paid for
twice and says exactly why.
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
    detroit_ann_arbor_hilton_recovery_018 as R18)

if __name__ == "__main__":
    P13.WORK_ORDER = R18.WORK_ORDER
    P13.RUN_ID = R18.RUN_ID
    P13.CAP_USD = R18.CAP_USD
    P13.USD_CEILING_PER_ATTEMPT = R18.USD_PER_ATTEMPT
    P13.ADMITTED_PATH = R18.ADMITTED_PATH
    P13.PLAN_PATH = R18.PLAN_PATH

    R13.WORK_ORDER = R18.WORK_ORDER
    R13.RUN_ID = R18.RUN_ID
    R13.CAP_USD = R18.CAP_USD
    R13.CEILING = R18.USD_PER_ATTEMPT
    # THE MATERIAL CHANGE. Order 016 added this guard; order 017 ran with it
    # and lost nine sessions. It is off here, and that is what licenses the
    # retry of pages this project has already paid for.
    R13.ENFORCE_CAP_AGAINST_BALANCE = False
    R13.RUN_PATH = R18.LP / "detroit_ann_arbor_hilton_recovery_run_018.json"
    R13.RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                   / "detroit-ann-arbor-hilton-018")
    R13.LOCK_PATH = R13.RUN_DIR / ".run-in-progress.lock"

    try:
        asyncio.run(R13.main())
    finally:
        R13.release_lock()
