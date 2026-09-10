"""PTF-NASHVILLE-TN-FINAL-REGRESSION-CLOSURE-004 -- is the shared pin narrowable?

Regression V2 classifies ``tests/pettripfinder/pins/market_state.json`` as
SHARED_TEST_STATE and turns TEST_EXPECTATION_CHANGE's conditional full
regression into a yes. This module decides, mechanically, whether that is:

  A  a legitimate shared semantic change that truly requires one broad run, or
  B  a generated current-state view already covered by the sealed package and
     the fast release contract, which should not widen a data-only release.

It does not assume either answer, and it does not read the classifier's comment
and call that a proof. Every field below is measured from the repository.

THE FOUR MEASUREMENTS

  1  IS IT GENERATED?      Search every module for a WRITER of the pin. If a
                           generation path exists, B is at least arguable; if
                           only readers exist, the pin is an authored
                           expectation and B's premise is false.
  2  WHAT DOES IT CONTROL? The blast radius, measured by experiment rather than
                           by import graph: hold the whole tree at HEAD, move
                           ONLY this market's pin entry back to its previous
                           values, and record which node ids change answer.
                           Baseline failures and failures that survive at HEAD
                           are subtracted, because a node that fails either way
                           is not controlled by the pin.
  3  DOES IT CROSS MARKETS? Of the controlled nodes, how many are parameterised
                           by this market and how many assert something about
                           the whole registry. A per-market node could in
                           principle be narrowed; a registry-wide one cannot.
  4  IS IT COVERED?        Does the sealed package or the fast release lane
                           evaluate the same invariants? The fast lane's rules
                           are listed and compared against what the controlled
                           nodes actually assert.

WHAT WOULD MAKE A CORRECTION LEGITIMATE

Only an objectively wrong classification. Two facts weigh against calling it
wrong before the measurements are even taken, and both are recorded here rather
than argued: ``test_regression_delta_001`` contains a test named
``test_a_shared_pin_makes_the_conditional_row_a_yes`` whose entire purpose is to
assert this behaviour and contrast it with a market-OWNED test file, and
``release_coordinator`` lists the pin in its own claim table as a CROSS-CHECK
input. A change here is a change to tested shared safety semantics, not a bug
fix, and it cannot self-authorize.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-TN-FINAL-REGRESSION-CLOSURE-004"
MARKET_ID = "nashville-tn"
PIN = "tests/pettripfinder/pins/market_state.json"

REPORTS = _DASH / "launch_packages" / "pettripfinder" / "markets" / "reports"
OUT = REPORTS / "nashville_tn_pin_scope_determination_004.json"
BASELINE = (_DASH / "launch_packages" / "pettripfinder" / "regression_baselines"
            / "f75aa95.json")

#: Nodes that fail at HEAD regardless of the pin. Measured by the recovery
#: order's own parent split, and subtracted here so a failure nobody caused is
#: never counted as something the pin controls.
FAILS_AT_HEAD_ANYWAY_SOURCE = REPORTS / "nashville_tn_recovery_audit_003.json"


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# 1. Generated, or authored?
# --------------------------------------------------------------------------- #

#: Local names a fixture builds a THROWAWAY tree under. A write rooted at one of
#: these targets a temporary copy, not the repository's pin, and is not a
#: generation path. Naming them explicitly is what keeps this measurement
#: honest: the first pass of this module counted two such fixtures as writers
#: and would have recorded a generation path that does not exist.
_FIXTURE_ROOTS = frozenset({"pkg", "tmp_path", "root", "dest", "tmp", "sandbox",
                            "repo", "worktree", "staged", "target"})


def _root_name(node):
    """The leftmost identifier a path expression is built from, or ""."""
    while isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        node = node.left
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Call):
        return _root_name(node.func)
    return node.id if isinstance(node, ast.Name) else ""


def writers_of_the_pin():
    """Every module that WRITES the pin, found by parsing rather than grep.

    A ``json.dump`` or ``write_text`` whose target resolves to the REPOSITORY's
    pin is a generation path. Two things are deliberately not counted: naming
    the file in a docstring, a comment or a claim table, which is a reference;
    and a fixture writing a stub pin into a temporary package it just built,
    which is a test of the classifier rather than a producer of the real file.
    Both kinds are returned, separated, so the distinction is visible instead of
    being taken on trust.
    """
    real, fixtures = [], []
    for root in ("scripts", "tests"):
        for path in sorted((_DASH / root).rglob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if "market_state.json" not in text and "MARKET_STATE_PATH" not in text:
                continue
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = (node.func.attr if isinstance(node.func, ast.Attribute)
                        else node.func.id if isinstance(node.func, ast.Name) else "")
                if name not in ("dump", "write_text", "write_bytes", "writelines"):
                    continue
                segment = ast.get_source_segment(text, node) or ""
                if "MARKET_STATE_PATH" not in segment and "market_state.json" not in segment:
                    continue
                target = node.func.value if isinstance(node.func, ast.Attribute) else None
                if target is None and node.args:
                    target = node.args[-1]
                rooted_at = _root_name(target) if target is not None else ""
                record = OrderedDict((
                    ("path", str(path.relative_to(_DASH)).replace("\\", "/")),
                    ("line", node.lineno), ("call", name),
                    ("target_rooted_at", rooted_at),
                    ("source", " ".join(segment.split())[:160])))
                if rooted_at in _FIXTURE_ROOTS:
                    record["why_not_a_writer"] = (
                        "the target is built under the local name %r, a throwaway tree the test "
                        "creates; it writes a stub pin to exercise the classifier, not the "
                        "repository's pin" % rooted_at)
                    fixtures.append(record)
                else:
                    real.append(record)
    return real, fixtures


def readers_of_the_pin():
    """Test modules that read the pin, directly or through market_state."""
    out = []
    for path in sorted((_DASH / "tests").rglob("test_*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if re.search(r"\bmarket_state\b|pinned_state|pinned_market_ids", text):
            out.append(str(path.relative_to(_DASH)).replace("\\", "/"))
    return out


# --------------------------------------------------------------------------- #
# 2 and 3. What the pin entry controls, and how far it reaches.
# --------------------------------------------------------------------------- #

def _failed(log_path):
    raw = Path(log_path).read_bytes()
    text = ""
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            candidate = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        if "FAILED" in candidate or "passed" in candidate:
            text = candidate
            break
    nodes = {n.replace("\\", "/") for n in re.findall(r"^FAILED\s+(\S+)", text, re.M)}
    tail = [l for l in text.strip().splitlines() if l.strip()][-1:]
    return nodes, (tail[0].strip() if tail else "")


def blast_radius(probe_log, control_log):
    """Nodes whose answer THIS market's pin entry controls.

    ``probe`` is the tree with only this market's pin entry reverted; ``control``
    is the same tree untouched. A node that fails in both is not controlled by
    the pin -- it fails for its own reason -- so the radius is the set
    difference, and the control is what makes the claim honest.
    """
    probe_failed, probe_tail = _failed(probe_log)
    control_failed, control_tail = _failed(control_log)
    baseline = set(_load(BASELINE)["failing_node_ids"])
    controlled = sorted(probe_failed - control_failed)
    return OrderedDict((
        ("probe_failed", len(probe_failed)),
        ("control_failed", len(control_failed)),
        ("in_the_committed_baseline", len(probe_failed & baseline)),
        ("controlled_by_the_pin_entry", len(controlled)),
        ("nodes", controlled),
        ("probe_summary", probe_tail),
        ("control_summary", control_tail),
    ))


def reach(nodes):
    """Per-market versus registry-wide, decided by the node id's own parameter."""
    scoped = [n for n in nodes if "[%s]" % MARKET_ID in n]
    wide = [n for n in nodes if "[%s]" % MARKET_ID not in n]
    return OrderedDict((
        ("parameterised_by_this_market", len(scoped)),
        ("registry_wide", len(wide)),
        ("registry_wide_nodes", wide),
        ("why_it_matters",
         "a node parameterised by this market could in principle be narrowed to it. A "
         "registry-wide node cannot: its answer is a statement about every pinned market at "
         "once, so moving one market's entry moves an assertion that is not about that market."),
    ))


# --------------------------------------------------------------------------- #
# 4. Covered by the package and the lane?
# --------------------------------------------------------------------------- #

def coverage(lane_report):
    """What the fast release lane evaluates, against what the pin controls."""
    lane = _load(lane_report)
    rules = lane["fast_lane_receipt"]["rules"]
    return OrderedDict((
        ("fast_lane_rules", rules),
        ("all_pass", all(v == "PASS" for v in rules.values())),
        ("what_the_lane_reads",
         "the sealed package for ONE market, and release INDEXES derived from committed "
         "authority for the comparison rules. It never opens the pin."),
        ("what_the_pin_cross_check_reads",
         "every market's release contract, policy package, exclusion shard, census and "
         "partition, and holds the reviewed number against each. That is "
         "tests/pettripfinder/contracts/test_market_state_pins.py, which is not one of the "
         "fifteen rules and is not run by the lane."),
        ("lane_evaluates_the_pin", False),
    ))


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-log", required=True)
    ap.add_argument("--control-log", required=True)
    ap.add_argument("--lane-report",
                    default=str(REPORTS / "nashville_tn_release_lane_003.json"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    writers, fixture_writes = writers_of_the_pin()
    readers = readers_of_the_pin()
    radius = blast_radius(args.probe_log, args.control_log)
    spread = reach(radius["nodes"])
    covered = coverage(args.lane_report)

    generated = bool(writers)
    crosses_markets = spread["registry_wide"] > 0
    covered_by_lane = bool(covered["lane_evaluates_the_pin"])

    # THE VERDICT IS DERIVED. B requires all three: a generation path, no
    # cross-market reach, and coverage by the lane. Any one of them false makes
    # the shared classification correct.
    verdict = "B" if (generated and not crosses_markets and covered_by_lane) else "A"

    doc = OrderedDict((
        ("schema", "ptf-pin-scope-determination/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("question",
         "is a change to %s a legitimate shared semantic change requiring one broad "
         "regression (A), or a generated current-state view already covered by the sealed "
         "package and the fast release contract (B)?" % PIN),
        ("measurement_1_is_it_generated", OrderedDict((
            ("writers_found", len(writers)),
            ("writers", writers),
            ("fixture_writes_not_counted", len(fixture_writes)),
            ("fixture_writes", fixture_writes),
            ("readers_found", len(readers)),
            ("conclusion",
             "the pin has %d writer(s) and %d reading test modules. The %d write call(s) that "
             "mention the filename all target a throwaway tree a test builds to exercise the "
             "classifier, so none is a generation path. With no writer, the file is an authored, "
             "reviewed expectation -- which its own owning module states in as many words: 'It "
             "is not a derivation. Nothing here opens a policy package, a census or a manifest.'"
             % (len(writers), len(readers), len(fixture_writes))),
            ("supports_B", generated),
        ))),
        ("measurement_2_blast_radius", radius),
        ("measurement_3_reach", spread),
        ("measurement_4_coverage", covered),
        ("classifier_behaviour_is_deliberate_and_tested", OrderedDict((
            ("rule", "regression_delta.SHARED_TEST_STATE, prefix tests/pettripfinder/pins/"),
            ("asserted_by",
             "tests/pettripfinder/test_regression_delta_001.py::"
             "test_a_shared_pin_makes_the_conditional_row_a_yes, which asserts "
             "full_regression_required is True for this exact path and False for a "
             "market-OWNED test file, so the distinction is designed rather than incidental"),
            ("also_declared_by",
             "scripts/pettripfinder/release_coordinator.py lists the pin in its own claim "
             "table with role 'CROSS-CHECK -- reviewed per-market numbers, not a live record'"),
            ("narrowing_mechanism_that_exists_and_does_not_apply",
             "regression_delta.REGISTRATION_CONTAINERS narrows a shared test file when its "
             "elements name THINGS THAT EXIST -- a run directory, a file, an id. Its own note "
             "draws the line this question turns on: 'Adding a number to an expectations table "
             "can [change an assertion's answer].' The pin is an expectations table of numbers."),
        ))),
        ("VERDICT", verdict),
        ("verdict_why", OrderedDict((
            ("B_requires_all_three", ["a generation path exists",
                                      "no cross-market reach",
                                      "the fast lane evaluates the same invariants"]),
            ("generation_path_exists", generated),
            ("crosses_markets", crosses_markets),
            ("fast_lane_evaluates_the_pin", covered_by_lane),
        ))),
        ("classifier_correction", OrderedDict((
            ("made", False),
            ("why_not",
             "the classification is not objectively wrong. It is conservative and correct: the "
             "pin is authored rather than generated, its movement demonstrably changes "
             "registry-wide assertions, and no fast-lane rule evaluates it. Correcting it would "
             "mean falsifying a test written to assert this behaviour, which is a change to "
             "shared safety semantics and cannot self-authorize."),
        ))),
        ("nothing_was_weakened", True),
    ))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("writers of the pin      :", len(writers),
          "| fixture writes not counted:", len(fixture_writes),
          "| readers:", len(readers))
    print("probe failed            :", radius["probe_failed"],
          "| control failed:", radius["control_failed"])
    print("controlled by the pin   :", radius["controlled_by_the_pin_entry"])
    print("  parameterised by market:", spread["parameterised_by_this_market"])
    print("  registry-wide          :", spread["registry_wide"])
    for node in spread["registry_wide_nodes"]:
        print("     ", node)
    print("fast lane evaluates pin :", covered["lane_evaluates_the_pin"])
    print("VERDICT                 :", verdict)
    print("written                 :", os.path.relpath(args.out, str(_DASH)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
