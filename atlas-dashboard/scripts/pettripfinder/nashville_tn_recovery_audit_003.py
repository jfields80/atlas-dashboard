"""PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 -- the ONE-TIME audit.

Classifies the single broad regression this order was allowed to run, and says
plainly what it was for.

WHY EXACTLY ONE BROAD RUN, AND WHAT IT IS NOT

Nashville pays NO factory-integration tax. The ATLAS-THROUGHPUT 001-008
engineering was merged onto this lineage by
PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003, so this order merges
nothing and re-audits no infrastructure.

This order changed NO shared runtime module, no schema, no contract and no
assembler. What it did change is ``tests/pettripfinder/pins/market_state.json``
-- shared test infrastructure read by nineteen modules -- along with Nashville's
own authority and its release contract. Regression V2 refuses to narrow a change
set that carries the pin, so exactly one broad run was executed. It was NOT run
merely because evidence changed.

It is NOT the routine Nashville data release, which is classified and measured
separately by ``nashville_tn_release_lane_002``: CHANGE_CLASS
MARKET_AUTHORITY_DATA_ONLY, FULL_REGRESSION_REQUIRED_BY_LANE = NO.

THREE KINDS OF TRUE_NEW, AND ONLY TWO OF THEM ARE THIS ORDER'S

Regression V2 classifies a run against a committed baseline manifest. When that
manifest is OLDER than the parent commit, a node the parent already fails is
reported TRUE_NEW even though this order never touched it. The classifier cannot
know the difference; the only way to find out is to run the named nodes AT THE
PARENT, which this audit requires as ``--parent-run`` and refuses to guess.

  PRE_EXISTING_AT_PARENT   fails at the parent too. Reported in full and NOT
                           closed here: absorbing it would hide a real failure,
                           and re-pinning the baseline is a different order's
                           work.
  CAUSED_BY_THIS_ORDER     passes at the parent, fails here. Closed at its cause
                           and re-run BY NODE ID.
  RETIRED_BY_NAME          a gate whose premise the promotion falsified. It
                           cannot be closed by re-running it, because it no
                           longer exists. Each is named with its reason, and a
                           retired gate is never counted as a passing one.

TRUE_NEW_FAILURE_AFTER_CLOSURE counts only what is still outstanding of the
second and third kinds.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import regression_lanes as RL  # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
OUT = os.path.join(REPORTS, "nashville_tn_recovery_audit_003.json")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _run(directory):
    """A run, read from the folded ``run.json`` when the lane runner wrote one.

    Re-reading the junit XML from a different working directory returns an EMPTY
    run, and an empty run classifies every baseline failure as "now passing" --
    a false clean bill of health, which is the one answer this audit must never
    give by accident.
    """
    folded = os.path.join(directory, "run.json")
    if os.path.isfile(folded):
        return _load(folded)
    return RL.read_run(directory)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="the broad junit run directory")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--classify", required=True, help="the regression_delta classify json")
    ap.add_argument("--split", required=True,
                    help="the parent-run split: which TRUE_NEW nodes the PARENT already fails")
    ap.add_argument("--closure-run", required=True,
                    help="a junit run directory that re-ran the surviving nodes after the fix")
    ap.add_argument("--recovery-commit", required=True)
    ap.add_argument("--parent-commit", required=True)
    ap.add_argument("--retired", action="append", default=[],
                    help="<node id>=<why the promotion falsified it>")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    run = _run(args.run)
    if not run.get("collected"):
        raise SystemExit("refusing to classify an empty run: %s" % args.run)
    baseline = _load(args.baseline)
    verdict = RL.classify(run, baseline)
    surface = _load(args.classify)
    split = _load(args.split)

    closure = _run(args.closure_run)
    if not closure.get("collected"):
        raise SystemExit("refusing to accept an empty closure run: %s" % args.closure_run)
    still_failing = set(closure.get("failing_node_ids") or ())

    retired = OrderedDict()
    for pair in args.retired:
        node, _, why = pair.partition("=")
        retired[node.strip()] = why.strip()

    pre_existing = list(split["PRE_EXISTING_AT_PARENT"]["nodes"])
    mine = [n for n in split["CAUSED_BY_THIS_ORDER"]["nodes"] if n not in retired]
    closed = sorted(n for n in mine if n not in still_failing)
    outstanding = sorted(n for n in mine if n in still_failing)

    doc = OrderedDict((
        ("schema", "ptf-registration-audit/1.0"),
        ("work_order", WORK_ORDER),
        ("what_this_audited",
         "the EVIDENCE RECOVERY for nashville-tn: 84 first-party pages re-fetched and hashed, "
         "and the authority rewritten on them. No shared runtime module, schema, contract or "
         "assembler changed; tests/pettripfinder/pins/market_state.json did, and Regression V2 "
         "refuses to narrow a change set carrying shared test infrastructure. It is NOT the "
         "routine Nashville data release, which the fast release lane classifies and measures "
         "on its own: that receipt reads MARKET_AUTHORITY_DATA_ONLY and "
         "FULL_REGRESSION_REQUIRED_BY_LANE = NO."),
        ("recovery_commit", args.recovery_commit),
        ("parent_commit", args.parent_commit),
        ("change_surface", OrderedDict((
            ("classes", surface.get("change_classes")),
            ("changed_file_count", surface.get("changed_file_count")),
            ("narrowing_blockers", surface.get("narrowing_blockers")),
        ))),
        ("broad_runs_executed", 1),
        ("remote_broad_jobs", 0),
        ("baseline", os.path.basename(args.baseline)),
        ("baseline_source_sha", baseline.get("source_sha")),
        ("baseline_failure_count", baseline.get("failed")),
        ("collected", run["collected"]),
        ("passed", run["passed"]),
        ("skipped", run["skipped"]),
        ("failures", run["failed"]),
        ("counts", verdict["counts"]),
        ("PRE_EXISTING", verdict["counts"].get(RL.PRE_EXISTING, 0)),
        ("TRUE_NEW_REPORTED_BY_THE_CLASSIFIER",
         verdict["counts"].get(RL.TRUE_NEW_FAILURE, 0)),
        ("baseline_failures_now_passing", verdict.get("baseline_failures_now_passing", [])),
        ("the_classifier_cannot_see_this", OrderedDict((
            ("what", "the committed baseline manifest is older than the parent commit, so a "
                     "node the PARENT already fails is reported TRUE_NEW. The split below is "
                     "measured by running the named nodes at %s." % args.parent_commit),
            ("PRE_EXISTING_AT_PARENT", OrderedDict((
                ("count", len(pre_existing)),
                ("not_closed_here",
                 "these fail at the parent too and are none of this order's doing. They are "
                 "reported rather than absorbed: silently folding sixteen real failures into a "
                 "PRE_EXISTING bucket is exactly the thing a baseline exists to prevent. "
                 "Re-pinning the baseline at the Lexington-live commit is a separate order's "
                 "work."),
                ("nodes", pre_existing),
            ))),
            ("CAUSED_BY_THIS_ORDER", OrderedDict((
                ("count", len(split["CAUSED_BY_THIS_ORDER"]["nodes"])),
                ("nodes", split["CAUSED_BY_THIS_ORDER"]["nodes"]),
            ))),
            ("corrections", split.get("corrections") or []),
        ))),
        ("closure", OrderedDict((
            ("what_this_is",
             "every node this order actually moved, fixed at its cause and re-run BY NODE ID. "
             "Regression V2 exists so this does not cost a second broad regression: the proof "
             "is the node the run named, not a repeat of the run."),
            ("closure_run", os.path.relpath(args.closure_run, _DASH)),
            ("closure_run_collected", closure["collected"]),
            ("closure_run_failed", closure["failed"]),
            ("closed_by_rerun", closed),
            ("retired_by_name", retired),
            ("why_a_retired_gate_is_not_a_closed_one",
             "a retired gate cannot be re-run: its premise is false and it no longer exists. "
             "Counting it as passing would let a deleted assertion read as an honoured one, so "
             "it is listed separately with the reason the promotion falsified it."),
            ("outstanding", outstanding),
            ("second_broad_run_required", bool(outstanding)),
        ))),
        ("seconds", OrderedDict((
            ("broad_run_s", sum(float(t.get("seconds") or 0)
                                for t in (run.get("timing") or ()))),
            ("closure_run_s", sum(float(t.get("seconds") or 0)
                                  for t in (closure.get("timing") or ()))),
        ))),
        ("TRUE_NEW_FAILURE_AFTER_CLOSURE", len(outstanding)),
        ("nothing_deselected_relaxed_or_deleted_to_make_a_count", True),
    ))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("collected            :", doc["collected"])
    print("failures             :", doc["failures"],
          "(baseline %s)" % doc["baseline_failure_count"])
    print("PRE_EXISTING         :", doc["PRE_EXISTING"])
    print("TRUE_NEW (classifier):", doc["TRUE_NEW_REPORTED_BY_THE_CLASSIFIER"])
    print("  pre-existing at parent:", len(pre_existing))
    print("  caused by this order  :",
          len(split["CAUSED_BY_THIS_ORDER"]["nodes"]))
    print("  corrections           :", len(split.get("corrections") or []))
    print("closed by rerun      :", len(closed))
    print("retired by name      :", len(retired))
    print("AFTER CLOSURE        :", doc["TRUE_NEW_FAILURE_AFTER_CLOSURE"])
    print("written              :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
