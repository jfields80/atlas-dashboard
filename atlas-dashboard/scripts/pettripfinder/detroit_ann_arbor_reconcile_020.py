# -*- coding: utf-8 -*-
"""Reconciliation after the order-020 founder rulings.

Rebuilds the display seed inventory and withdraws the routes that publication
has now answered, reusing order 011's committed pipeline whole.

THE PER-ORDER PATHS ARE OVERRIDDEN BEFORE THE MODULE RUNS. ``WORK_ORDER`` and
``WITHDRAWALS_PATH`` are module-level constants in the 011 pipeline; calling it
unchanged would stamp this order's work with 011's name and overwrite 011's own
withdrawal report. The shared cumulative archive is merged by that module, but
the per-order report is not, so it has to be pointed somewhere new here.

ROBERTS RIVERWALK KEEPS ITS ROUTE. The founder retained the identity as
unresolved and required a NEW first-party route before any publication, so the
route is not withdrawn -- nothing published answered it. Withdrawal is for
routes publication has ANSWERED, and a hijacked domain answered nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_display_inventory_011 as D11)

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020-FOUNDER-RULINGS"
ROBERTS = "roberts riverwalk hotel"


def run() -> None:
    D11.WORK_ORDER = WORK_ORDER
    D11.WITHDRAWALS_PATH = (D11.LP
                            / "detroit_ann_arbor_route_withdrawals_020.json")
    D11.run()

    routing = D11.load(D11.MA.routing_shard_path(D11.MARKET))
    kept = [route for route in routing["routes"]
            if route["hotel_ref"]["identity_key"] == ROBERTS]
    print()
    print("Roberts Riverwalk route retained: %s"
          % ("yes -- %s" % kept[0]["status"] if kept else "NO -- INVESTIGATE"))
    if not kept:
        raise SystemExit("STOP: the founder retained this identity as "
                         "unresolved and routed; its route is gone")


if __name__ == "__main__":
    run()
