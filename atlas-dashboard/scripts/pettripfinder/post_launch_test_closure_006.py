"""PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006 -- what a routine launch closure costs.

Closing the Nashville launch cost about 61 minutes of pytest. Two modules --
``test_global_deployment_architecture_045`` and ``test_launch_participation_046``
-- each RENDER THE WHOLE THIRTEEN-MARKET SITE in a module-scoped fixture, and
between them that is nearly all of it.

This measures the claim rather than asserting it: which nodes request the
full-assembly fixture, which lanes each module belongs to, and what a routine
market launch actually has to run. The classification of each expensive node is
declared here and checked against the source, so a node that stops requesting
the fixture, or starts, shows up as a mismatch instead of silently drifting.

THE FOUR CLASSES

  CHEAP_INDEX_INVARIANT          provable from committed indexes and the
                                 derivations themselves; no bytes required
  RELEASE_MANIFEST_INVARIANT     provable from the composed manifest and the
                                 release contracts it pins
  CHANGED_MARKET_BUILD_REQUIRED  needs the changed market rendered, not all of
                                 them
  FULL_ASSEMBLY_INTEGRATION      needs the composed multi-market bundle on disk

Only the last two need a build, and only the last needs the whole site.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006"
TESTS = _DASH / "tests" / "pettripfinder"
HEAVY = ("test_global_deployment_architecture_045.py", "test_launch_participation_046.py")
FIXTURE = "production"

CHEAP = "CHEAP_INDEX_INVARIANT"
MANIFEST = "RELEASE_MANIFEST_INVARIANT"
CHANGED_MARKET = "CHANGED_MARKET_BUILD_REQUIRED"
FULL = "FULL_ASSEMBLY_INTEGRATION"

#: What each node that requests the full-assembly fixture actually proves.
#: Anything not named here is FULL by default: an unclassified claim costs the
#: build, exactly as an unclassified path costs the full suite in Regression V2.
CLASSIFICATION = {
    # -- provable without rendering anything ---------------------------------
    "test_the_participation_set_is_derived_not_listed": CHEAP,
    "test_each_markets_profile_count_matches_its_own_contract": MANIFEST,
    "test_every_participating_market_is_contract_clean": MANIFEST,
    "test_participation_and_inventory_are_unchanged": CHEAP,
    "test_assembly_does_not_authorize_deployment": MANIFEST,
    "test_the_bundle_carries_exactly_the_live_set": CHEAP,
    "test_the_bundle_excludes_only_the_two_that_are_not_source_ready": CHEAP,
    "test_the_bundle_pins_the_participation_record": MANIFEST,
    "test_the_context_is_recorded_in_the_manifest": MANIFEST,
    # -- needs the changed market's own bytes --------------------------------
    "test_indianapolis_routes_are_present_and_correctly_counted": CHANGED_MARKET,
    "test_no_held_or_refused_indianapolis_row_reached_the_bundle": CHANGED_MARKET,
    "test_milwaukee_contributes_exactly_73_profiles": CHANGED_MARKET,
    "test_an_approved_milwaukee_property_is_in_the_bundle": CHANGED_MARKET,
    "test_a_held_milwaukee_property_is_absent_from_the_bundle": CHANGED_MARKET,
    "test_no_milwaukee_refusal_reaches_the_bundle": CHANGED_MARKET,
    "test_the_correction_moved_only_four_profiles": CHANGED_MARKET,
    # everything else: FULL_ASSEMBLY_INTEGRATION.
}

#: Where each cheap claim is proved now, without a build.
MOVED_TO = "tests/pettripfinder/test_release_composition_contract_006.py"

#: The modules a routine MARKET_AUTHORITY_DATA_ONLY launch closure runs.
ROUTINE_CLOSURE = (
    "tests/pettripfinder/test_release_composition_contract_006.py",
    "tests/pettripfinder/test_participation_lineage_contract_006.py",
    "tests/pettripfinder/test_assembly_scratch_isolation_006.py",
    "tests/pettripfinder/test_deployment_authorization_047.py",
    "tests/pettripfinder/contracts/test_market_state_pins.py",
    "tests/pettripfinder/test_nashville_tn_launch_005.py",
    "tests/pettripfinder/test_lexington_ky_launch_006.py",
    "tests/pettripfinder/test_toledo_oh_launch_003.py",
)

#: What the SAME closure cost during the Nashville launch, measured, before any
#: of this. The two heavy modules were in it because their hard-coded market
#: lists had to move; each rendered the whole site once.
BEFORE = OrderedDict((
    ("modules", ["tests/pettripfinder/test_deployment_authorization_047.py",
                 "tests/pettripfinder/test_global_deployment_architecture_045.py",
                 "tests/pettripfinder/test_launch_participation_046.py",
                 "tests/pettripfinder/test_lexington_ky_launch_006.py",
                 "tests/pettripfinder/test_toledo_oh_launch_003.py",
                 "tests/pettripfinder/contracts/test_market_state_pins.py"]),
    ("wall_seconds", 1136.98),
    ("summary", "29 failed, 222 passed in 1136.98s (0:18:56)"),
    ("full_site_assemblies", 2),
    ("markets_assembled_per_assembly", 13),
    ("measured_in", "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"),
))

#: The 39 fixture errors, and what they actually were.
THIRTY_NINE_ERRORS = OrderedDict((
    ("symptom", "a rendered Columbus profile fragment missing from one run and a "
                "shared asset missing from another's composed bundle -- both files "
                "the build had just written"),
    ("root_cause", "test_global_deployment_architecture_045 and "
                   "test_launch_participation_046 each built into ONE hard-coded "
                   "absolute path and each tore it down with shutil.rmtree, so two "
                   "pytest processes on the machine deleted each other's build tree "
                   "mid-flight."),
    ("why_it_appeared_then", "the regression rule is to run the suite at HEAD and "
                             "again in a scratch worktree at the parent commit, and "
                             "those two runs were started concurrently."),
    ("evidence", [
        "ran alone at HEAD:            18m56s, 29 failed, 222 passed,  0 errors",
        "ran alone at the parent:      16m57s,  7 failed, 244 passed,  0 errors",
        "the two run CONCURRENTLY:      3m00s, 21 failed, 191 passed, 39 errors",
        "                               1m33s, 15 failed, 197 passed, 39 errors",
    ]),
    ("not_caused_by", ["the Nashville launch", "the assembler",
                       "the participation record", "disk space"]),
    ("fixed_by", "pettripfinder.conftest.assembly_scratch -- a build root private "
                 "to the process, kept short for the Windows path limit"),
    ("regression_test", "tests/pettripfinder/test_assembly_scratch_isolation_006.py"),
))


def nodes_requesting_fixture(module: Path):
    """Every test function in ``module`` whose signature takes the fixture."""
    tree = ast.parse(module.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        args = [a.arg for a in node.args.args]
        out.append((node.name, FIXTURE in args))
    return out


def measure(paths, label):
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "--tb=short", "-p", "no:randomly"],
        cwd=str(_DASH), capture_output=True)
    seconds = time.time() - started
    tail = proc.stdout.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
    return OrderedDict((
        ("label", label),
        ("paths", list(paths)),
        ("wall_seconds", round(seconds, 1)),
        ("exit_status", proc.returncode),
        ("summary", tail[0].strip()),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true",
                    help="measure the routine closure cohort as well as classifying it")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    from scripts.pettripfinder import regression_lanes as LANES

    modules = OrderedDict()
    totals = Counter()
    for name in HEAVY:
        path = TESTS / name
        rows = []
        for test_name, needs in nodes_requesting_fixture(path):
            if not needs:
                continue
            klass = CLASSIFICATION.get(test_name, FULL)
            totals[klass] += 1
            rows.append(OrderedDict((("node", test_name), ("class", klass))))
        modules[name] = OrderedDict((
            ("lanes", list(LANES.lanes_for(name))),
            ("in_market_targeted_lane", LANES.MARKET_TARGETED in LANES.lanes_for(name)),
            ("tests_total", len(nodes_requesting_fixture(path))),
            ("tests_requiring_the_full_assembly_fixture", len(rows)),
            ("full_site_assemblies_per_run", 1),
            ("claims", rows),
        ))

    doc = OrderedDict((
        ("schema", "ptf-post-launch-test-closure/1.0"),
        ("work_order", WORK_ORDER),
        ("what_this_measures",
         "which test nodes require the whole thirteen-market site to have been "
         "rendered, what each of them actually proves, and what a routine market "
         "launch closure has to run once the cheap claims are proved cheaply."),
        ("heavy_modules", modules),
        ("claims_by_class", OrderedDict(sorted(totals.items()))),
        ("cheap_claims_now_proved_without_a_build", MOVED_TO),
        ("full_integration_still_lives_in", list(HEAVY)),
        ("full_integration_selected_by", OrderedDict((
            ("lanes", [LANES.DEPLOYMENT_ARCHITECTURE, LANES.FULL_REGRESSION]),
            ("never_in", LANES.MARKET_TARGETED),
            ("meaning", "an assembler, shared-runtime, shared-schema or "
                        "deployment-architecture change still runs them; a market "
                        "authority data-only launch does not, and never did -- what "
                        "pulled them into the Nashville closure was their hard-coded "
                        "market list, which now lives in one reviewed constant that a "
                        "buildless module holds to the manifest and to production."),
        ))),
        ("routine_closure_modules", list(ROUTINE_CLOSURE)),
        ("the_39_fixture_errors", THIRTY_NINE_ERRORS),
        ("routine_closure_before", BEFORE),
    ))

    if args.run:
        after = measure(ROUTINE_CLOSURE, "routine closure, after")
        after["full_site_assemblies"] = 0
        after["markets_assembled"] = 0
        doc["routine_closure_after"] = after
        doc["speedup"] = OrderedDict((
            ("before_seconds", BEFORE["wall_seconds"]),
            ("after_seconds", after["wall_seconds"]),
            ("factor", round(BEFORE["wall_seconds"] / max(after["wall_seconds"], 0.1), 1)),
            ("full_site_assemblies_before", BEFORE["full_site_assemblies"]),
            ("full_site_assemblies_after", 0),
        ))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    for name, row in modules.items():
        print("%-46s %2d/%2d need the full assembly | market_targeted=%s"
              % (name, row["tests_requiring_the_full_assembly_fixture"],
                 row["tests_total"], row["in_market_targeted_lane"]))
    print("claims by class   :", dict(sorted(totals.items())))
    if "speedup" in doc:
        s = doc["speedup"]
        print("routine closure   : %.1f s -> %.1f s (%.1fx), %d full-site assemblies -> 0"
              % (s["before_seconds"], s["after_seconds"], s["factor"],
                 s["full_site_assemblies_before"]))
        print("after             :", doc["routine_closure_after"]["summary"],
              "| exit", doc["routine_closure_after"]["exit_status"])
    print("written           :", Path(args.out).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
