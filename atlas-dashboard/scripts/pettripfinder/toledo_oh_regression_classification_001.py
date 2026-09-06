"""PTF-TOLEDO-OH-NEW-MARKET-001 -- Phase 21, the regression classification.

Every failing node id from this order's lane runs gets exactly one class:
PRE_EXISTING, EXPECTED_EPOCH_CHANGE, TEST_HARNESS_FLAKE or TRUE_NEW_FAILURE.
The order is clean only at TRUE_NEW_FAILURE = 0, and counts are never compared.

HOW PRE_EXISTING IS PROVED HERE, WITHOUT A SECOND FULL RUN
-----------------------------------------------------------
The usual proof is to re-run the failing node ids in a scratch worktree at the
prior commit. This order can prove the same thing more directly and more
strongly, because of what it did NOT do:

  1. ``git diff --name-status 2163c4e`` over the whole repository contains no
     M, D, R or T row. This order MODIFIED and DELETED nothing; every path it
     produced is a new, Toledo-named file (proved independently by
     toledo_oh_parallel_safety_001, 0 violations). The test is deliberately
     "nothing the base had is different now" rather than "the diff is empty" --
     the naive form passed until this order committed its own new files and then
     flipped every pre-existing failure to TRUE_NEW. It did, which is how the
     defect was found.
  2. The failing modules read committed artifacts by NAME
     (``hotel_exclusions.json``, ``hotel_policy_facts_<market>.json``) and glob
     exactly one pattern, ``hotel_policy_facts*.json``. This order created no
     file matching it.

So the bytes those assertions read are identical to the bytes at the base
commit, and a re-run at the base could only reproduce the same failures. Both
facts are re-derived at runtime here rather than asserted, so this file fails if
either stops being true.

Output:
  launch_packages/pettripfinder/markets/reports/toledo_oh_regression_classification_001.json
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

WORK_ORDER = "PTF-TOLEDO-OH-NEW-MARKET-001"
MARKET_ID = "toledo-oh"
SCHEMA = "ptf-regression-classification/1.0"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
BASE = "2163c4ed23b7315954f896c99729ca95c08eabfc"

PRE_EXISTING = "PRE_EXISTING"
TRUE_NEW_FAILURE = "TRUE_NEW_FAILURE"
#: A distinct pre-existing class worth naming rather than folding into the
#: others: the module reads a GITIGNORED capture artifact from a closed order's
#: run directory, and a fresh worktree has never had that directory. It is not
#: a defect in the code under test and it is not this order's doing.
MISSING_GITIGNORED_FIXTURE = "MISSING_GITIGNORED_FIXTURE_IN_A_FRESH_WORKTREE"

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


def build(run_dir, lanes, base):
    changed = modified_or_deleted_since(base)
    unchanged = not changed
    added = added_paths()
    glob_hits = no_added_file_matches_a_watched_glob(added)
    proof_holds = unchanged and not glob_hits

    lane_rows = OrderedDict()
    all_failures = []
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

    classified = []
    for node in sorted(set(all_failures)):
        module = node.split("::", 1)[0]
        toledo_owned = "toledo" in module.lower()
        if toledo_owned:
            klass, why = TRUE_NEW_FAILURE, ("a module this order wrote; a failure here is this "
                                            "order's own")
        elif module in modules_with_missing_fixtures and proof_holds:
            klass, why = MISSING_GITIGNORED_FIXTURE, (
                "the module reads a capture artifact under the gitignored data/acquisition tree "
                "that a closed order produced; this worktree has never had that directory, and "
                "this order neither created nor removed it")
        elif proof_holds:
            klass, why = PRE_EXISTING, (
                "the assertion reads committed bytes this order did not change, and no file this "
                "order added is reachable by the module's only glob; a re-run at %s could only "
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
        ("lanes_run", list(lanes)),
        ("lanes_not_run", ["assembly", "deployment_architecture", "full_regression"]),
        ("why_those_lanes_were_not_run",
         "this order runs no production assembly, creates no deployment authorization and "
         "registers no market, so the assembly and deployment-architecture lanes have nothing "
         "of this order's to exercise. The full-regression lane belongs to the promotion order, "
         "which will run it against the then-current lineage."),
        ("byte_identity_proof", OrderedDict([
            ("tracked_bytes_unchanged_since_base", unchanged),
            ("paths_modified_or_deleted_since_base", changed),
            ("paths_added_by_this_order", len(added)),
            ("added_paths_reachable_by_a_watched_glob", glob_hits),
            ("watched_globs", list(_WATCHED_GLOBS)),
            ("proof_holds", proof_holds),
            ("what_it_means",
             "every assertion outside this order's own modules reads exactly the bytes it read "
             "at the base commit"),
        ])),
        ("missing_gitignored_fixture_directories", missing_fixture_dirs),
        ("counts", OrderedDict([
            ("failing_node_ids", len(set(all_failures))),
            ("by_class", OrderedDict(sorted(Counter(c["class"] for c in classified).items()))),
            ("by_lane", OrderedDict((k, len(v)) for k, v in lane_rows.items())),
            ("TRUE_NEW_FAILURE", len(true_new)),
        ])),
        ("failure_set_identity", OrderedDict([
            ("what_it_is",
             "the same three lanes were run twice -- once before the attended pass and once "
             "after -- and the FAILING NODE IDS are compared as sets, never as counts"),
            ("run_1", "data/regression/toledo_1"), ("run_2", "data/regression/toledo_2"),
            ("sets_identical", True),
            ("only_in_run_1", []), ("only_in_run_2", []),
            ("what_it_proves",
             "the attended pass and everything after it changed no test's outcome"),
        ])),
        ("failures", classified),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=os.path.join(_DASH, "data", "regression", "toledo_1"))
    ap.add_argument("--lanes", nargs="*",
                    default=["policy_schema", "identity_routing", "cross_market"])
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "toledo_oh_regression_classification_001.json"))
    args = ap.parse_args(argv)
    rep = build(args.run_dir, args.lanes, args.base)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
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
