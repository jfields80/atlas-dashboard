# -*- coding: utf-8 -*-
"""PTF-...-BRIGHTDATA-AUTHORITY-APPLICATION-019 -- display and route withdrawal.

Drives order 011's display module with this order's identity, so the per-order
report and the cumulative withdrawals archive are both filed under 019 rather
than misattributed to 011.
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

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019"

if __name__ == "__main__":
    D11.WORK_ORDER = WORK_ORDER
    D5.WORK_ORDER = WORK_ORDER
    D11.WITHDRAWALS_PATH = (
        D11.LP / "detroit_ann_arbor_route_withdrawals_019.json")
    D11.run()
