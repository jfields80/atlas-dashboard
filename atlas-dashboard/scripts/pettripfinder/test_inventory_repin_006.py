"""PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006 -- re-pinning the suite inventory.

``test_factory_throughput_001::TestTheHarness::
test_the_committed_inventory_reproduces_from_the_suite`` holds a committed
report to what ``regression_inventory.build()`` produces from the suite as it
stands. This repair adds three modules and edits two, and it also finds the pin
already stale: the Nashville launch arc added a suite and moved four modules
without re-running it. Both are GENERATED_REPORT_ONLY -- the report describes
what the suite contains, and the suite legitimately contains something else.

WHY THIS IS NOT A LICENCE TO REWRITE A SHARED REPORT

The file is not this order's to rewrite on trust, and the parallel-safety gate
exists to catch an order that quietly does so. PTF-NASHVILLE-TN-NEW-MARKET-001
solved this by refusing unless every added module was Nashville-named. That
guard does not fit here, because this order deliberately EDITS shared modules --
which is the whole point of a harness repair -- so a guard that forbids any
alteration would refuse the legitimate case and teach nothing.

So the guard is named instead of shaped: every added and every altered module
must appear in a list here WITH the work order that moved it, and nothing may be
removed. Anything outside those lists writes nothing and stays a TRUE_NEW
failure for a human to look at. Inherited debt is therefore closed by naming the
order that incurred it, never by absorbing it silently.
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

WORK_ORDER = "PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
PINNED = os.path.join(PKG, "reports", "factory_throughput_001_test_inventory.json")
OUT = os.path.join(PKG, "markets", "reports", "test_inventory_repin_006.json")

#: Modules ADDED to the inventory since it was last pinned, each with the order
#: that created it. Three are this order's. The fourth is the Nashville launch's
#: own suite: the pin was never re-run after that launch, so this repair closes
#: inherited debt as well as its own -- named, not absorbed silently.
ADDED = {
    "test_release_composition_contract_006.py": WORK_ORDER,
    "test_participation_lineage_contract_006.py": WORK_ORDER,
    "test_assembly_scratch_isolation_006.py": WORK_ORDER,
    "test_nashville_tn_launch_005.py":
        "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005",
}

#: Modules ALTERED since the pin, each with the order that moved it and why.
ALTERED = {
    "test_global_deployment_architecture_045.py":
        WORK_ORDER + ": the reviewed market list moved to one shared constant and "
                     "the scratch root became process-private",
    "test_launch_participation_046.py":
        WORK_ORDER + ": the same two changes",
    "test_lexington_ky_launch_006.py":
        "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005: rewritten to "
        "read its own deployment record now that a later release is live",
    "test_toledo_oh_launch_003.py":
        "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005: the same",
    "test_global_assembler.py":
        "PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002: nashville-tn "
        "joined the per-market expectations",
    "test_per_market_release_contracts.py":
        "PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002: the same",
    "acquisition/test_store_integration_025.py":
        "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003: the recovery run joined "
        "OTHER_MARKET_RUNS",
}

def module_key(m):
    return m.get("module") or m.get("path") or json.dumps(m, sort_keys=True)


def owned(key, names):
    return any(key.endswith(n) or key == n for n in names)


def main():
    with open(PINNED, encoding="utf-8-sig") as fh:
        committed = json.load(fh)
    fresh = INV.build()

    cm = {module_key(m): m for m in committed["modules"]}
    fm = {module_key(m): m for m in fresh["modules"]}
    added = sorted(set(fm) - set(cm))
    removed = sorted(set(cm) - set(fm))
    altered = sorted(k for k in set(cm) & set(fm) if cm[k] != fm[k])
    foreign_added = [k for k in added if not owned(k, ADDED)]
    foreign_altered = [k for k in altered if not owned(k, ALTERED)]

    proof_holds = (not removed and not foreign_added and not foreign_altered
                   and bool(added or altered))
    report = OrderedDict((
        ("schema", "ptf-suite-inventory-repin/1.0"),
        ("work_order", WORK_ORDER),
        ("pinned_file", os.path.relpath(PINNED, _DASH).replace("\\", "/")),
        ("change_class", "GENERATED_REPORT_ONLY"),
        ("what_moved_it",
         "three modules added and two edited by this harness repair, plus the "
         "additions and alterations the Nashville launch arc left un-pinned; the "
         "report describes what the suite contains and the suite now contains "
         "something else"),
        ("proof", OrderedDict((
            ("modules_removed", removed),
            ("modules_added", added),
            ("modules_altered", altered),
            ("added_that_this_order_did_not_create", foreign_added),
            ("altered_that_this_order_is_not_declared_to_have_edited", foreign_altered),
            ("proof_holds", proof_holds),
            ("rule", "rewritten ONLY when nothing was removed, every added module is "
                     "one this order created, and every altered module is one it is "
                     "declared to have edited. Otherwise nothing is written and the "
                     "failure stays TRUE_NEW for a human."),
        ))),
        ("declared_additions", OrderedDict(sorted(ADDED.items()))),
        ("declared_alterations", OrderedDict(sorted(ALTERED.items()))),
        ("counts_before", OrderedDict((
            ("modules_scanned", committed["modules_scanned"]),
            ("sites", committed["sites"])))),
        ("counts_after", OrderedDict((
            ("modules_scanned", fresh["modules_scanned"]),
            ("sites", fresh["sites"])))),
    ))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("modules added   :", len(added), added[:4])
    print("modules removed :", removed)
    print("modules altered :", len(altered), altered[:6])
    print("foreign added   :", foreign_added)
    print("foreign altered :", foreign_altered)
    print("proof holds     :", proof_holds)
    if not proof_holds:
        print("REFUSING to rewrite the pin; nothing was written to", PINNED)
        return 1
    with open(PINNED, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fresh, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("re-pinned       :", os.path.relpath(PINNED, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
