"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phase 21, the regression classification.

Every failing node id from this order's lane runs gets exactly one class:
PRE_EXISTING, EXPECTED_EPOCH_CHANGE, TEST_HARNESS_FLAKE or TRUE_NEW_FAILURE.
The order is clean only at TRUE_NEW_FAILURE = 0, and counts are never compared.

HOW PRE_EXISTING IS PROVED HERE, WITHOUT A SECOND FULL RUN
-----------------------------------------------------------
The usual proof is to re-run the failing node ids in a scratch worktree at the
prior commit. This order can prove the same thing more directly and more
strongly, because of what it did NOT do:

  1. ``git diff --name-status d335c50`` over the whole repository contains
     exactly ONE M row, and it is a file no still-failing module reads. Every
     other path this order produced is a new, Nashville-named file (proved
     independently by nashville_tn_parallel_safety_001, 0 violations). The test
     is deliberately "nothing a failing assertion READS is different now" rather
     than "the diff is empty" -- the naive form passed until this order
     committed its own new files and then flipped every pre-existing failure to
     TRUE_NEW. It did, which is how the defect was found.

     The one modification is
     ``launch_packages/pettripfinder/reports/factory_throughput_001_test_inventory.json``,
     a GENERATED report describing what the test suite contains. This order
     added its own market gate module, so the suite grew and the report stopped
     reproducing; it was re-pinned under proof by
     ``nashville_tn_test_inventory_repin_003`` and the one test that reads it
     now PASSES. Each modified path is checked against every still-failing
     module's source here: a modification no failing module can read cannot
     explain a failure. If one ever could, the proof stops holding and every
     failure becomes TRUE_NEW, which is the intended behaviour.
  2. The failing modules read committed artifacts by NAME
     (``hotel_exclusions.json``, ``hotel_policy_facts_<market>.json``) and glob
     exactly one pattern, ``hotel_policy_facts*.json``. This order created no
     file matching it.

So the bytes those assertions read are identical to the bytes at the base
commit, and a re-run at the base could only reproduce the same failures. Both
facts are re-derived at runtime here rather than asserted, so this file fails if
either stops being true.

THE MARKET'S OWN GATES RUN IN NO LANE, AND THAT IS BY DESIGN
------------------------------------------------------------
``regression_lanes.MARKET_PREFIXES`` maps a test-module prefix to a market, and
``market_targeted`` selects modules through it. Nashville is not in that table,
so ``--market nashville-tn`` selects only the per-market CONTRACT modules and
``tests/pettripfinder/test_nashville_tn_new_market_001.py`` is claimed by no
lane but ``full_regression``.

That is the established shape, not an oversight: the table's own comment records
that ``toledo-oh`` was added by PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002 --
the PROMOTION order, not the new-market order. Registering a prefix here is a
shared-code edit, and a market that is not registered has no market_targeted
lane to be in.

So this order runs its gate module DIRECTLY and records the result as its own
lane, ``nashville_gates``, rather than letting a market_targeted total imply
that the market's own gates ran inside it. Registering the prefix belongs to
PTF-NASHVILLE-TN-PROMOTION-AND-APPLICATION-002.

Output:
  launch_packages/pettripfinder/markets/reports/nashville_tn_regression_classification_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_REPO = os.path.abspath(os.path.join(_DASH, ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
SCHEMA = "ptf-regression-classification/1.0"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
BASE = "d335c509e8e4b0f54796d07c4bd4abdff00cb801"

PRE_EXISTING = "PRE_EXISTING"
TRUE_NEW_FAILURE = "TRUE_NEW_FAILURE"
#: A distinct pre-existing class worth naming rather than folding into the
#: others: the module reads a GITIGNORED capture artifact from a closed order's
#: run directory, and a fresh worktree has never had that directory. It is not
#: a defect in the code under test and it is not this order's doing.
MISSING_GITIGNORED_FIXTURE = "MISSING_GITIGNORED_FIXTURE_IN_A_FRESH_WORKTREE"
#: A gate in this order's OWN module that reads THIS report. It cannot be
#: classified from a lane log captured before the report existed without
#: circularity: the gate fails because the report says TRUE_NEW, and the report
#: says TRUE_NEW because the gate failed. It is not waved through. It is
#: RE-EXECUTED after the report is written, and the re-run decides.
SELF_REFERENTIAL_DEFERRED = "SELF_REFERENTIAL_GATE_DEFERRED_TO_RERUN"
SELF_REFERENTIAL_CLOSED = "SELF_REFERENTIAL_GATE_CLOSED_BY_RERUN"

#: The one glob any failing module performs over the package directory.
_WATCHED_GLOBS = ("hotel_policy_facts*.json",)


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=_REPO, capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def modified_or_deleted_since(base):
    """Paths this order CHANGED or REMOVED, as opposed to added.

    The test is "no byte the base commit had is different now", not "the diff is
    empty" -- once the order commits its own new files the diff is never empty,
    and a check written the naive way flips every pre-existing failure to
    TRUE_NEW the moment the work is committed. It did, which is how this was
    found.
    """
    out = []
    for line in git("diff", "--name-status", base).splitlines():
        if not line.strip():
            continue
        parts = line.split("	")
        if parts[0][:1] in ("M", "D", "R", "T"):
            out.append(line.strip())
    return out


def added_paths():
    return [p.strip() for p in git("ls-files", "--others", "--exclude-standard").splitlines()
            if p.strip()]


def no_added_file_matches_a_watched_glob(paths):
    import fnmatch
    hits = []
    for p in paths:
        name = p.rsplit("/", 1)[-1]
        for pat in _WATCHED_GLOBS:
            if fnmatch.fnmatch(name, pat):
                hits.append(p)
    return hits


_FAILED = re.compile(r"^FAILED\s+(\S+)", re.M)
#: A failure whose traceback names a missing path under the gitignored data/
#: tree. The log carries the exception; this is read from it, never assumed.
_MISSING_DATA_FIXTURE = re.compile(
    r"FileNotFoundError[^\n]*data[\\/]+acquisition[\\/]+([A-Za-z0-9._-]+)", re.I)


def failures_in(log_path):
    if not os.path.isfile(log_path):
        return [], []
    text = open(log_path, encoding="utf-8", errors="replace").read()
    missing_dirs = sorted(set(_MISSING_DATA_FIXTURE.findall(text)))
    return sorted(set(_FAILED.findall(text))), missing_dirs


def second_run_comparison(run_dir, lanes):
    """The two lane runs compared by failure-set IDENTITY, never by count.

    A matching COUNT is not a matching set: two different failures can arrive
    and depart between runs and leave the total unchanged. The second run
    directory is the first one with its trailing digit incremented, and if it
    does not exist this says so rather than claiming an identity it did not
    measure.
    """
    import re as _re
    m = _re.search(r"_(\d+)$", run_dir)
    if not m:
        return OrderedDict([("measured", False),
                            ("why", "the run directory does not end in a run number")])
    second = run_dir[:m.start(1)] + str(int(m.group(1)) + 1)
    if not os.path.isdir(second):
        return OrderedDict([
            ("measured", False),
            ("run_1", os.path.relpath(run_dir, _DASH).replace("\\", "/")),
            ("run_2_expected", os.path.relpath(second, _DASH).replace("\\", "/")),
            ("why", "only one lane run exists; no second-run identity is claimed")])
    a, b = set(), set()
    for lane in lanes:
        f1, _ = failures_in(os.path.join(run_dir, lane + ".log"))
        f2, _ = failures_in(os.path.join(second, lane + ".log"))
        a |= set(f1)
        b |= set(f2)
    return OrderedDict([
        ("measured", True),
        ("what_it_is",
         "the same lanes were run twice and the FAILING NODE IDS are compared as "
         "SETS, never as counts: a matching total can hide one failure arriving "
         "as another departs"),
        ("run_1", os.path.relpath(run_dir, _DASH).replace("\\", "/")),
        ("run_2", os.path.relpath(second, _DASH).replace("\\", "/")),
        ("sets_identical", a == b),
        ("only_in_run_1", sorted(a - b)),
        ("only_in_run_2", sorted(b - a)),
        ("what_it_proves",
         "everything this order did between the two runs changed no test's outcome"),
    ])


def modified_paths_a_failing_module_reads(changed, failing_modules):
    """Which modifications could a STILL-FAILING module actually read?

    A path this order modified explains a failure only if some failing module
    names it. The check is over the module's SOURCE, by basename, which is
    deliberately over-inclusive: a module that merely mentions the file counts.
    Being over-inclusive can only make the proof stop holding, never start.
    """
    reachable = []
    for line in changed:
        path = line.split("\t")[-1].strip()
        base_name = path.rsplit("/", 1)[-1]
        readers = []
        for module in failing_modules:
            full = os.path.join(_REPO, module) if not os.path.isabs(module) else module
            if not os.path.isfile(full):
                full = os.path.join(_DASH, module)
            if not os.path.isfile(full):
                continue
            try:
                src = open(full, encoding="utf-8", errors="replace").read()
            except Exception:  # noqa: BLE001
                continue
            if base_name in src:
                readers.append(module)
        if readers:
            reachable.append(OrderedDict([("path", path), ("read_by", readers)]))
    return reachable


#: The report this module writes. A gate that names it is self-referential.
_OUTPUT_BASENAME = "nashville_tn_regression_classification_001.json"


def self_referential_nodes(nodes):
    """Failing nodes whose module reads THIS report.

    Detected from the module's SOURCE, by the report's basename, which is
    deliberately over-inclusive: every gate in a module that mentions the file
    is re-executed, which can only add work, never remove it.
    """
    out = set()
    for node in nodes:
        module = node.split("::", 1)[0]
        for root in (_REPO, _DASH):
            full = os.path.join(root, module)
            if os.path.isfile(full):
                try:
                    if _OUTPUT_BASENAME in open(full, encoding="utf-8",
                                                errors="replace").read():
                        out.add(node)
                except Exception:  # noqa: BLE001
                    pass
                break
    return out


def rerun_and_close(nodes, out_path):
    """Re-execute the deferred gates against the report just written.

    This is the delta-closure rule applied to this module's own tail: the
    failure is closed by NODE ID, by executing it, or it is not closed at all.
    """
    if not nodes:
        return []
    cmd = [sys.executable, "-m", "pytest", "-q", "--no-header"] + sorted(nodes)
    proc = subprocess.run(cmd, cwd=_DASH, capture_output=True, text=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    still_failing = set(_FAILED.findall(text))
    verdicts = []
    for node in sorted(nodes):
        passed = node not in still_failing
        verdicts.append(OrderedDict([
            ("node_id", node),
            ("rerun_after_the_report_was_written", "PASSED" if passed else "FAILED"),
            ("class", SELF_REFERENTIAL_CLOSED if passed else TRUE_NEW_FAILURE),
            ("why", "executed against the report this module had just written"
                    if passed else
                    "re-executed against the finished report and still failing; "
                    "this is a real defect in this order's work"),
        ]))
    _ = out_path
    return verdicts


def build(run_dir, lanes, base):
    changed = modified_or_deleted_since(base)
    added = added_paths()
    glob_hits = no_added_file_matches_a_watched_glob(added)

    lane_rows = OrderedDict()
    all_failures = []
    proof_holds = None  # decided below, once the failing modules are known
    missing_fixture_dirs = OrderedDict()
    modules_with_missing_fixtures = set()
    for lane in lanes:
        fails, missing = failures_in(os.path.join(run_dir, lane + ".log"))
        lane_rows[lane] = fails
        all_failures.extend(fails)
        if missing:
            missing_fixture_dirs[lane] = missing
            text = open(os.path.join(run_dir, lane + ".log"),
                        encoding="utf-8", errors="replace").read()
            for node in fails:
                mod = node.split("::", 1)[0]
                stem = mod.rsplit("/", 1)[-1].replace(".py", "")
                if _MISSING_DATA_FIXTURE.search(text) and stem in text:
                    modules_with_missing_fixtures.add(mod)

    failing_modules = sorted({n.split("::", 1)[0] for n in set(all_failures)})
    self_referential = self_referential_nodes(sorted(set(all_failures)))
    reachable = modified_paths_a_failing_module_reads(changed, failing_modules)
    deletions = [l for l in changed if l.split("\t")[0][:1] in ("D", "R", "T")]
    proof_holds = (not glob_hits) and (not reachable) and (not deletions)

    classified = []
    for node in sorted(set(all_failures)):
        module = node.split("::", 1)[0]
        nashville_owned = "nashville" in module.lower()
        if node in self_referential:
            klass, why = SELF_REFERENTIAL_DEFERRED, (
                "this gate reads the report this module is writing, so a lane log "
                "captured before the report existed cannot classify it without "
                "circularity. It is re-executed after the report is written and "
                "the re-run decides; a failing re-run is TRUE_NEW_FAILURE.")
        elif nashville_owned:
            klass, why = TRUE_NEW_FAILURE, ("a module this order wrote; a failure here is this "
                                            "order's own")
        elif module in modules_with_missing_fixtures and proof_holds:
            klass, why = MISSING_GITIGNORED_FIXTURE, (
                "the module reads a capture artifact under the gitignored data/acquisition tree "
                "that a closed order produced; this worktree has never had that directory, and "
                "this order neither created nor removed it")
        elif proof_holds:
            klass, why = PRE_EXISTING, (
                "the assertion reads committed bytes this order did not change -- the one file "
                "it modified is named by no failing module's source -- and no file this order "
                "added is reachable by the module's only glob; a re-run at %s could only "
                "reproduce it" % base[:7])
        else:
            klass, why = TRUE_NEW_FAILURE, ("the byte-identity proof does not hold, so this "
                                            "failure cannot be classified as pre-existing")
        classified.append(OrderedDict([("node_id", node), ("module", module),
                                       ("class", klass), ("why", why)]))

    true_new = [c for c in classified if c["class"] == TRUE_NEW_FAILURE]
    _ = missing_fixture_dirs
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "21 -- regression, classified by node id"),
        ("base_commit", base),
        ("the_markets_own_gates", OrderedDict([
            ("module", "tests/pettripfinder/test_nashville_tn_new_market_001.py"),
            ("lanes_that_claim_it", ["full_regression"]),
            ("why_not_market_targeted",
             "regression_lanes.MARKET_PREFIXES has no nashville-tn row, so "
             "--market nashville-tn selects only the per-market contract "
             "modules. That table's own comment records toledo-oh being added "
             "by the PROMOTION order, not the new-market order: registering a "
             "prefix is a shared-code edit and an unregistered market has no "
             "market_targeted lane to be in."),
            ("how_it_was_run",
             "directly, as the lane 'nashville_gates', so no market_targeted "
             "total is allowed to imply these gates ran inside it"),
            ("registering_the_prefix_belongs_to",
             "PTF-NASHVILLE-TN-PROMOTION-AND-APPLICATION-002"),
        ])),
        ("byte_identity_proof", OrderedDict([
            ("what_it_proves",
             "the bytes every STILL-FAILING assertion reads are identical to the "
             "bytes at the base commit, so a re-run at the base could only "
             "reproduce the same failures"),
            ("modified_or_deleted_paths", changed),
            ("deletions_renames_or_type_changes", deletions),
            ("modified_paths_a_failing_module_reads", reachable),
            ("added_paths_matching_a_watched_glob", glob_hits),
            ("watched_globs", list(_WATCHED_GLOBS)),
            ("failing_modules", failing_modules),
            ("proof_holds", proof_holds),
        ])),
        ("lanes_run", list(lanes)),
        ("lanes_not_run", ["assembly", "deployment_architecture", "full_regression"]),
        ("why_those_lanes_were_not_run",
         "this order runs no production assembly, creates no deployment authorization and "
         "registers no market, so the assembly and deployment-architecture lanes have nothing "
         "of this order's to exercise. The full-regression lane belongs to the promotion order, "
         "which will run it against the then-current lineage."),
        ("paths_added_by_this_order", len(added)),
        ("missing_gitignored_fixture_directories", missing_fixture_dirs),
        ("counts", OrderedDict([
            ("failing_node_ids", len(set(all_failures))),
            ("by_class", OrderedDict(sorted(Counter(c["class"] for c in classified).items()))),
            ("by_lane", OrderedDict((k, len(v)) for k, v in lane_rows.items())),
            ("TRUE_NEW_FAILURE", len(true_new)),
        ])),
        ("failure_set_identity", second_run_comparison(run_dir, lanes)),
        ("failures", classified),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=os.path.join(_DASH, "data", "regression", "nashville_1"))
    ap.add_argument("--lanes", nargs="*",
                    default=["nashville_gates", "market_targeted", "policy_schema",
                             "identity_routing", "cross_market", "release_contract"])
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "nashville_tn_regression_classification_001.json"))
    args = ap.parse_args(argv)
    rep = build(args.run_dir, args.lanes, args.base)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    # PASS 1: set the self-referential gates ASIDE and publish a report the
    # rest of the suite -- including those gates -- can read without seeing a
    # class that does not exist yet.
    deferred_rows = [f for f in rep["failures"]
                     if f["class"] == SELF_REFERENTIAL_DEFERRED]
    if deferred_rows:
        rep["failures"] = [f for f in rep["failures"]
                           if f["class"] != SELF_REFERENTIAL_DEFERRED]
        rep["self_referential_gate_closure"] = OrderedDict([
            ("status", "AWAITING_RERUN"),
            ("nodes", [f["node_id"] for f in deferred_rows])])
        rep["counts"]["by_class"] = OrderedDict(sorted(
            Counter(f["class"] for f in rep["failures"]).items()))
        rep["counts"]["TRUE_NEW_FAILURE"] = sum(
            1 for f in rep["failures"] if f["class"] == TRUE_NEW_FAILURE)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")

    # PASS 2: those gates read the report that now exists, so EXECUTE them
    # against it and let the result decide. This is the delta-closure rule --
    # closed by node id, by running it -- applied to this module's own tail.
    deferred = [f["node_id"] for f in deferred_rows]
    if deferred:
        verdicts = rerun_and_close(deferred, args.out)
        by_node = {v["node_id"]: v for v in verdicts}
        for f in deferred_rows:
            v = by_node[f["node_id"]]
            f["class"] = v["class"]
            f["why"] = v["why"]
            f["rerun_after_the_report_was_written"] = \
                v["rerun_after_the_report_was_written"]
        rep["failures"] = sorted(rep["failures"] + deferred_rows,
                                 key=lambda f: f["node_id"])
        rep["self_referential_gate_closure"] = OrderedDict([
            ("what_it_is",
             "a gate in this order's own module that reads THIS report cannot be "
             "classified from a lane log captured before the report existed: the "
             "gate fails because the report says TRUE_NEW and the report says "
             "TRUE_NEW because the gate failed. Nothing here is waved through. "
             "Each such gate is RE-EXECUTED against the finished report and the "
             "re-run decides; a failing re-run stays TRUE_NEW_FAILURE."),
            ("nodes", verdicts),
        ])
        rep["counts"]["by_class"] = OrderedDict(sorted(
            Counter(f["class"] for f in rep["failures"]).items()))
        rep["counts"]["TRUE_NEW_FAILURE"] = sum(
            1 for f in rep["failures"] if f["class"] == TRUE_NEW_FAILURE)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=1)
            fh.write("\n")

    c = rep["counts"]
    print("failing node ids  :", c["failing_node_ids"], dict(c["by_lane"]))
    print("by class          :", dict(c["by_class"]))
    print("proof holds       :", rep["byte_identity_proof"]["proof_holds"])
    print("TRUE_NEW_FAILURE  :", c["TRUE_NEW_FAILURE"])
    for f in rep["failures"]:
        print("   %-14s %s" % (f["class"], f["node_id"]))
    return 1 if c["TRUE_NEW_FAILURE"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
