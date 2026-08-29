# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012 -- display.

Seeds the hotels this order published and withdraws the routes that answers.

It DRIVES order 011's display module rather than restating it, but it must
override two of its constants first. Both are the same lesson: a module that
writes a per-order report under its own name will file this order's work under
that order's name, and a shared archive it stamps will credit the wrong order.
So ``WORK_ORDER`` and ``WITHDRAWALS_PATH`` are pointed at this order before its
``run`` is called, and order 011's own report is left as the record of what
011 did.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_display_inventory_005 as D5,
    detroit_ann_arbor_display_inventory_011 as D11)

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012"

if __name__ == "__main__":
    D11.WORK_ORDER = WORK_ORDER
    D5.WORK_ORDER = WORK_ORDER
    D11.WITHDRAWALS_PATH = (
        D11.LP / "detroit_ann_arbor_route_withdrawals_012.json")
    D11.run()
