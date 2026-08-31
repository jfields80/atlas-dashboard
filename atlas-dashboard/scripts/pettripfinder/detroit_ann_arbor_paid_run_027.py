# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027, Phases 8 and 9.

Runs the final Bright Data cohort by CALLING the order-013 runner, not by
copying it. Every hardening that runner carries -- the exclusive lock, the
already-bought guard, the per-attempt ceiling, the before/after balance read,
the disabled per-attempt CLI guard -- applies here unchanged.

THE PER-ATTEMPT CEILING IS RE-BASED, THE HARD CAP IS NOT. The runner's
inherited ceiling is $0.19, the rate the very first pilot paid before this
market understood the lane. Orders 016-018 measured $0.0850, $0.0917 and
$0.0892. Holding 17 rows against $0.19 would halt the run at ten attempts on
arithmetic that no longer describes reality. The ceiling is set to $0.11 --
above every recent measurement with room to spare, and low enough that the
whole cohort fits under the founder's $2.00 cap at $1.87 worst case. THE $2.00
CAP ITSELF IS UNTOUCHED, and it is the control that matters.

ENFORCE_CAP_AGAINST_BALANCE STAYS OFF. Order 017 ran with it and lost 9 of 13
sessions; order 018 re-ran those same nine rows with it off and recovered
eight. A vendor CLI shell-out before every managed-browser session destabilises
the sessions. Balance is read before and after instead.

ONE RUNNER. If this call appears to hang, DO NOT RELAUNCH IT -- check the lock
file, the ledger and the process. Relaunching a paid run that was merely quiet
is how order 013 spent $2.64 against a $2.28 cap.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_brightdata_pilot_013 as P13,
    detroit_ann_arbor_brightdata_run_013 as RUN,
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027"
RUN_ID = "detroit-brightdata-027-close"
HARD_CAP_USD = 2.00
CEILING_USD = 0.11

LP = P13.LP
COHORT = LP / "detroit_ann_arbor_paid_cohort_027.json"
SCRATCH = LP / "_027_runner_input"


def prepare():
    """Point the 013 runner at THIS order's cohort, in the shape it expects."""
    cohort = R11.load(COHORT)
    rows = cohort["rows"]
    SCRATCH.mkdir(parents=True, exist_ok=True)

    # The 013 runner reads several fields off each row directly, not with
    # .get(): brand, sub_brand, city, canonical_url. The first launch of this
    # order died on the missing one AFTER paying for an attempt -- the crash
    # was in the result record, past the provider call. Every field the runner
    # indexes is supplied here so a missing key can never again cost money.
    for row in rows:
        row.setdefault("brand", row.get("brand") or row.get("family") or "")
        row.setdefault("sub_brand", "")
        row.setdefault("city", row.get("city") or "")
        row.setdefault("property_code", row.get("property_code") or "")
        row.setdefault("reader", "")
        row.setdefault("lane", "brightdata_browser")

    admitted_path = SCRATCH / "admitted_027.json"
    plan_path = SCRATCH / "plan_027.json"
    R11.write_lf(admitted_path, OrderedDict([
        ("schema", "ptf-detroit-brightdata-admitted/1.0"),
        ("work_order", WORK_ORDER),
        ("admitted_rows", rows),
    ]))
    R11.write_lf(plan_path, OrderedDict([
        ("schema", "ptf-detroit-brightdata-cost-plan/1.0"),
        ("work_order", WORK_ORDER),
        ("cohort", OrderedDict([
            ("rows_this_run", len(rows)),
            ("usd_ceiling_per_attempt", CEILING_USD),
            ("hard_cap_usd", HARD_CAP_USD),
            ("worst_case_usd", round(len(rows) * CEILING_USD, 2)),
        ])),
    ]))

    # Re-point the runner and the pilot module it reads from.
    P13.ADMITTED_PATH = admitted_path
    P13.PLAN_PATH = plan_path
    P13.RUN_ID = RUN_ID
    P13.WORK_ORDER = WORK_ORDER
    P13.CAP_USD = HARD_CAP_USD
    P13.USD_CEILING_PER_ATTEMPT = CEILING_USD

    RUN.RUN_ID = RUN_ID
    RUN.WORK_ORDER = WORK_ORDER
    RUN.CAP_USD = HARD_CAP_USD
    RUN.CEILING = CEILING_USD
    RUN.RUN_PATH = LP / "detroit_ann_arbor_paid_run_027.json"
    RUN.RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                   / "detroit-brightdata-027-close")
    RUN.LOCK_PATH = RUN.RUN_DIR / ".run-in-progress.lock"
    RUN.ENFORCE_CAP_AGAINST_BALANCE = False

    worst = round(len(rows) * CEILING_USD, 2)
    print("=== Phase 8: one runner, locked ===")
    print("   run_id       :", RUN_ID)
    print("   rows         :", len(rows))
    print("   ceiling/att  : $%.2f  (re-based from the obsolete $0.19 pilot "
          "constant; recent measured max $0.0917)" % CEILING_USD)
    print("   worst case   : $%.2f" % worst)
    print("   HARD CAP     : $%.2f  (unchanged)" % HARD_CAP_USD)
    print("   lock         :", RUN.LOCK_PATH)
    if worst > HARD_CAP_USD:
        raise SystemExit("STOP: worst case exceeds the cap")
    return len(rows)


def main():
    prepare()
    print()
    print("=== Phase 9: running the final paid cohort ===")
    try:
        asyncio.run(RUN.main())
    finally:
        RUN.release_lock()


if __name__ == "__main__":
    main()
