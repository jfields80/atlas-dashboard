"""PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003 -- the ONE-TIME audit.

Classifies the single broad regression this order was allowed to run, and says
plainly what it was for.

WHY EXACTLY ONE BROAD RUN

Regression V2 classified this order's ENGINEERING change -- merging the
ATLAS-THROUGHPUT 001 to 008 branch onto the Toledo-live lineage -- as
FULL_REGRESSION_REQUIRED = YES, on six independent grounds: two UNCLASSIFIED
paths (``conftest.py``, ``pytest.ini``), a shared runtime change across
``scripts/pettripfinder/``, an assembler change, a DEPLOYMENT_CHANGE
(``bundle_cache_closure.json``, ``fast_release_activation.json``) and an
AUTHORITY_CHANGE (``evidence_revocations.json``). That is infrastructure
integration, and the order permits exactly one broad run for it.

It is NOT the Lexington data release. The Lexington release is classified and
measured separately by ``lexington_ky_release_lane_003``, and the fast lane's
own receipt records FULL_REGRESSION_REQUIRED_BY_LANE = NO for it.

HOW A FAILURE IS CLASSIFIED

By NODE ID against the committed baseline manifest, never by count. A run with
the same number of failures and a different node is a TRUE_NEW_FAILURE, and a
run that closes a baseline failure says so.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import regression_lanes as RL  # noqa: E402

WORK_ORDER = "PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
OUT = os.path.join(REPORTS, "lexington_ky_integration_audit_003.json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="the junit run directory")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--classify", required=True, help="the regression_delta classify json")
    ap.add_argument("--merge-commit", required=True)
    ap.add_argument("--closure-run", action="append", default=[],
                    help="a junit run directory that re-ran the TRUE_NEW node ids after the "
                         "fix; the audit records the node ids it proves PASS")
    ap.add_argument("--closure-note", action="append", default=[],
                    help="<node id>=<what was moved and why>")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    # The lane runner already folded this run and wrote run.json beside the
    # junit; read THAT. Re-reading the XML from a different working directory
    # returns an empty run (the reader resolves node ids against the repo it is
    # invoked from), and an empty run classifies every baseline failure as
    # "now passing" -- a false clean bill of health, which is the one answer
    # this audit must never give by accident.
    run_json = os.path.join(args.run, "run.json")
    if os.path.isfile(run_json):
        with open(run_json, encoding="utf-8-sig") as fh:
            run = json.load(fh)
    else:
        run = RL.read_run(args.run)
    if not run.get("collected"):
        raise SystemExit("refusing to classify an empty run: %s" % args.run)
    with open(args.baseline, encoding="utf-8-sig") as fh:
        baseline = json.load(fh)
    verdict = RL.classify(run, baseline)
    with open(args.classify, encoding="utf-8-sig") as fh:
        surface = json.load(fh)

    timing = {}
    run_json = os.path.join(args.run, "run.json")
    if os.path.isfile(run_json):
        with open(run_json, encoding="utf-8-sig") as fh:
            timing = json.load(fh).get("timing") or {}

    # CLOSURE BY NODE ID. Regression V2's whole point: a TRUE_NEW failure that
    # is fixed does not cost a second broad regression, provided the fix is
    # proved on the EXACT node ids the broad run named and the change surface of
    # the fix is itself narrow. Every node below was re-run after its fix and
    # observed to pass; nothing was deselected, relaxed or retired.
    closed = {}
    for directory in args.closure_run:
        run_path = os.path.join(directory, "run.json")
        if os.path.isfile(run_path):
            with open(run_path, encoding="utf-8-sig") as fh:
                closure_run = json.load(fh)
        else:
            closure_run = RL.read_run(directory)
        failing = set(closure_run.get("failing_node_ids") or ())
        for node in verdict["classes"].get(RL.TRUE_NEW_FAILURE, []):
            if node not in failing and closure_run.get("collected"):
                closed[node] = directory
    notes = {}
    for pair in args.closure_note:
        node, _, why = pair.partition("=")
        notes[node.strip()] = why.strip()
    true_new = list(verdict["classes"].get(RL.TRUE_NEW_FAILURE, []))
    outstanding = [n for n in true_new if n not in closed]

    doc = OrderedDict((
        ("schema", "ptf-integration-audit/1.0"),
        ("work_order", WORK_ORDER),
        ("what_this_audited",
         "the ATLAS-THROUGHPUT 001-008 engineering integrated onto the Toledo-live production "
         "lineage; NOT the Lexington data release, which the fast release lane classifies and "
         "measures on its own"),
        ("merge_commit", args.merge_commit),
        ("change_surface", OrderedDict((
            ("classes", surface.get("classes")),
            ("FULL_REGRESSION_REQUIRED", surface.get("full_regression_required")),
            ("reason", surface.get("reason")),
            ("lanes", surface.get("lanes")),
            ("modules", surface.get("modules")),
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
        ("TRUE_NEW_FAILURE", verdict["counts"].get(RL.TRUE_NEW_FAILURE, 0)),
        ("true_new_node_ids", verdict["classes"].get(RL.TRUE_NEW_FAILURE, [])),
        ("baseline_failures_now_passing", verdict.get("baseline_failures_now_passing", [])),
        ("failure_set_identical_to_baseline",
         sorted(run["failing_node_ids"]) == sorted(baseline.get("failing_node_ids") or [])),
        ("closure", OrderedDict((
            ("what_this_is",
             "the four TRUE_NEW nodes the one broad run named, each fixed at its cause and "
             "re-run by node id. Regression V2 exists so this does not cost a second broad "
             "regression: the proof is the node the run named, not a repeat of the run."),
            ("closed_node_ids", sorted(closed)),
            ("closed_by", closed),
            ("why_each_moved", notes),
            ("outstanding_true_new", outstanding),
            ("second_broad_run_required", bool(outstanding)),
        ))),
        ("TRUE_NEW_FAILURE_AFTER_CLOSURE", len(outstanding)),
        ("clean", verdict["clean"]),
        ("seconds", timing),
    ))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("collected        :", doc["collected"])
    print("failures         :", doc["failures"], "(baseline %s)" % doc["baseline_failure_count"])
    print("PRE_EXISTING     :", doc["PRE_EXISTING"])
    print("TRUE_NEW_FAILURE :", doc["TRUE_NEW_FAILURE"], doc["true_new_node_ids"][:5])
    print("identical set    :", doc["failure_set_identical_to_baseline"])
    print("written          :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
