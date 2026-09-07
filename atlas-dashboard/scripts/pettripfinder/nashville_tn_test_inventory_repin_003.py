"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phase 21b, re-pinning the suite inventory.

WHAT BROKE, AND WHY IT IS NOT A DEFECT
--------------------------------------
``tests/pettripfinder/test_factory_throughput_001.py::TestTheHarness::
test_the_committed_inventory_reproduces_from_the_suite`` holds a committed
report to what ``regression_inventory.build()`` produces from the suite as it
stands. This order added ONE test module -- its own market gates -- so the
suite grew and the committed report stopped reproducing. The report is
GENERATED_REPORT_ONLY in the change-class table: it describes what the suite
contains, and the suite legitimately contains one more module.

WHY THIS IS NOT A LICENCE TO REWRITE A SHARED REPORT
----------------------------------------------------
The file is not Nashville-named, and a market order that quietly rewrote a
shared generated report would be doing exactly what the parallel-safety gate
exists to catch. So this does not rewrite it on trust. It computes the delta
first and REFUSES to write unless the delta is exactly this order's own
modules:

  * every module in the committed report is still in the fresh one -- nothing
    was removed;
  * no module present in both changed its content -- nothing was altered;
  * every module the fresh report ADDS is Nashville-named.

If any of those fails, this exits non-zero and writes nothing, and the failure
stays a TRUE_NEW_FAILURE for a human to look at. The proof is written into the
Nashville-owned report beside it, so the next order can check the claim rather
than take it.

Outputs:
  launch_packages/pettripfinder/reports/factory_throughput_001_test_inventory.json
  launch_packages/pettripfinder/markets/reports/nashville_tn_test_inventory_repin_003.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for _p in (_DASH, os.path.join(_DASH, "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.pettripfinder import regression_inventory as INV  # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
PINNED = os.path.join(PKG, "reports", "factory_throughput_001_test_inventory.json")
OUT = os.path.join(PKG, "markets", "reports",
                   "nashville_tn_test_inventory_repin_003.json")
#: A module this order owns. Anything else appearing in the delta is a stop.
OWNED = "nashville_tn"


def module_key(m):
    return m.get("module") or m.get("path") or json.dumps(m, sort_keys=True)


def main():
    committed = json.load(open(PINNED, encoding="utf-8"))
    fresh = INV.build()

    cm = {module_key(m): m for m in committed["modules"]}
    fm = {module_key(m): m for m in fresh["modules"]}
    added = sorted(set(fm) - set(cm))
    removed = sorted(set(cm) - set(fm))
    altered = sorted(k for k in set(cm) & set(fm) if cm[k] != fm[k])
    foreign = [k for k in added if OWNED not in k]

    proof_holds = not removed and not altered and bool(added) and not foreign
    report = OrderedDict([
        ("schema", "ptf-suite-inventory-repin/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "21b -- re-pinning the suite-derived test inventory"),
        ("pinned_file", os.path.relpath(PINNED, _DASH).replace("\\", "/")),
        ("change_class", "GENERATED_REPORT_ONLY"),
        ("what_moved_it",
         "this order added its own market gate module to the suite; the report "
         "describes what the suite contains and the suite now contains one more "
         "module"),
        ("proof", OrderedDict([
            ("modules_removed", removed),
            ("modules_altered", altered),
            ("modules_added", added),
            ("modules_added_that_this_order_does_not_own", foreign),
            ("proof_holds", proof_holds),
            ("rule", "the pin is rewritten ONLY when nothing was removed, nothing "
                     "that exists in both changed, and every added module is "
                     "Nashville-named. Otherwise this writes nothing and the "
                     "failure stays TRUE_NEW for a human."),
        ])),
        ("counts_before", OrderedDict([
            ("modules_scanned", committed["modules_scanned"]),
            ("sites", committed["sites"]),
            ("by_class", committed["by_class"])])),
        ("counts_after", OrderedDict([
            ("modules_scanned", fresh["modules_scanned"]),
            ("sites", fresh["sites"]),
            ("by_class", OrderedDict(sorted(fresh["by_class"].items())))])),
    ])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")

    print("modules added   :", added)
    print("modules removed :", removed)
    print("modules altered :", altered)
    print("proof holds     :", proof_holds)
    if not proof_holds:
        print("REFUSING to rewrite the pin; nothing was written to", PINNED)
        return 1
    with open(PINNED, "w", encoding="utf-8") as fh:
        json.dump(fresh, fh, indent=1)
        fh.write("\n")
    print("re-pinned       :", os.path.relpath(PINNED, _DASH))
    print("written         :", os.path.relpath(OUT, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
