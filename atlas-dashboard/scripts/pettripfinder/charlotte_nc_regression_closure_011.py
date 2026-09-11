"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- the second broad run's closure.

Proves the registration closure by NODE ID and by failure-set IDENTITY, and
writes the durable artifact under
``launch_packages/pettripfinder/failure_closures/``.

WHY A SECOND BROAD RUN AT ALL
-----------------------------
Not by preference. ``regression_delta classify`` reads the change surface and
answers FULL_REGRESSION_REQUIRED: YES, naming the participation record,
Charlotte's release contract and the bundle-cache closure as DEPLOYMENT_CHANGE
under the rule that what a record claims is served must be what a fresh assembly
builds. The closure file is additionally a narrowing blocker. Nothing narrower
proves this change surface, so the machine's verdict is recorded here beside the
result rather than argued with.

THE THREE QUESTIONS THIS ANSWERS
--------------------------------
1. FAILURE-SET IDENTITY. Which node ids failed in the first broad run
   (``charlotte-full``) and not the second, which in the second and not the
   first? A closure that merely matched the COUNT would prove nothing -- the
   house rule is identity, never arithmetic.
2. NODE-ID CLOSURE. Every one of the 28 node ids the first run called TRUE_NEW
   is accounted for as CLOSED, STILL_FAILING, PRE_EXISTING (proved at the parent
   commit) or MOVED (renamed, with the new id named and required to pass).
3. FINAL_TRUE_NEW_FAILURE_AFTER_CLOSURE. Classified against the committed
   baseline, and reported with the baseline's own staleness stated rather than
   hidden: ``f75aa95`` predates Lexington and Nashville, so a node those markets
   left red is not Charlotte's and is proved so at the parent commit.

Output:
  launch_packages/pettripfinder/failure_closures/charlotte_nc_registration_011.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import regression_lanes as RL  # noqa: E402

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
BASE_SHA = "11373275"
FIRST_RUN = _DASH / "data" / "regression" / "charlotte-full"
SECOND_RUN = _DASH / "data" / "regression" / "charlotte-close"
BASELINES = _DASH / "launch_packages" / "pettripfinder" / "regression_baselines"
CLOSURES = _DASH / "launch_packages" / "pettripfinder" / "failure_closures"
OUT = CLOSURES / "charlotte_nc_registration_011.json"

#: The node ids the first broad run called TRUE_NEW, read from its own
#: classification rather than retyped.
FIRST_CLASSIFICATION = FIRST_RUN / "classification.json"

#: Proved PRE_EXISTING by running them in a worktree at BASE_SHA. Each fails
#: there too, so it is not Charlotte's and this order does not fix it.
PRE_EXISTING_AT_PARENT = {
    "tests/pettripfinder/acquisition/test_store_integration_025.py::test_every_run_on_disk_is_classified":
        "fails at %s: a run on disk predating the classifier" % BASE_SHA,
    "tests/pettripfinder/test_atlas_throughput_003.py::TestReleaseIndex::test_the_index_is_o_data_and_fast_at_a_hundred_markets":
        "fails at %s: a timing bound this machine does not meet" % BASE_SHA,
    "tests/pettripfinder/test_atlas_throughput_004.py::TestBoundaries::test_the_fast_lane_reports_market_build_required_no_on_a_trusted_bundle":
        "fails at %s" % BASE_SHA,
    "tests/pettripfinder/test_indianapolis_authority_promotion_017.py::TestTheCrossMarketCollision::test_the_other_bare_names_are_clean":
        "fails at %s: bare names Lexington and Nashville brought" % BASE_SHA,
    "tests/pettripfinder/test_indianapolis_authority_promotion_017.py::TestTheCrossMarketCollision::test_the_scan_finds_nothing_else":
        "fails at %s: same scan, same rows" % BASE_SHA,
    "tests/research_workers/test_marriott_short_property_link.py::TestNothingElseMoved::test_the_columbus_seed_still_parses_end_to_end":
        "fails at %s: its ten failing rows are all Lexington's" % BASE_SHA,
    "tests/research_workers/test_property_code_redroof_choice.py::TestLiveSeedUrlsAllParse::test_every_columbus_seed_url_with_a_known_shape_still_resolves":
        "fails at %s: same ten rows" % BASE_SHA,
}

#: Renamed by this order, old id -> new id. A rename moves a node id and the
#: closure is proved BY node id, so every move is declared here and the new id
#: must pass. Exactly one test was renamed, and only because its NAME asserted
#: the opposite of what it now checks.
MOVED = {
    "tests/pettripfinder/test_participation_lineage_contract_006.py::TestTheCommittedRecordAndItsOneDocumentedException::test_it_is_the_repair_record_carrying_it_and_that_is_recorded":
        "tests/pettripfinder/test_participation_lineage_contract_006.py::TestTheCommittedRecordAndItsOneDocumentedException::test_the_record_carries_its_own_chain_again",
}

#: Node ids that failed in the second broad run and NOT the first, together with
#: the re-run that settles each. The factory calls nothing a flake on a story --
#: only on an isolated re-run result -- so each entry names the re-run and what
#: it returned.
APPEARED_AND_EXPLAINED = {
    "tests/pettripfinder/acquisition/test_normalization_041.py::test_the_simulation_wrote_nothing_to_the_repository":
        OrderedDict((
            ("verdict", "TEST_HARNESS_FLAKE"),
            ("rerun", "passes alone at HEAD, 1 passed in 9.78s"),
            ("cause", (
                "It runs `git status --porcelain` before and after a simulation and "
                "requires the two to be identical. That is a statement about the whole "
                "working tree, so ANY write to the repository during those few seconds "
                "fails it. The writer was me: this closure module and a patch to the "
                "authorization packet were created and byte-compiled while the broad "
                "run was in flight. The test is right and the operator was wrong.")),
            ("rule", (
                "Do not touch the working tree while a broad regression is running. "
                "Commit first, then run, then wait.")),
        )),
}

#: Not a Charlotte regression: it passes ALONE at both commits and failed only
#: when something earlier in the same pytest process assembled from the
#: committed census. Corrected in place by scoping its last assertion to the
#: entries the build added, which is what its other assertions already read.
ORDER_DEPENDENT = {
    "tests/pettripfinder/test_atlas_throughput_004.py::TestSessionCacheIsolation::test_a_staged_build_is_remembered_under_its_overlay_key_not_the_committed_one":
        "order-dependent; passes alone at %s and at HEAD" % BASE_SHA,
}


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=str(_DASH),
                          capture_output=True, text=True).stdout.strip()


def load_baseline(tag):
    return json.loads((BASELINES / ("%s.json" % tag)).read_text(encoding="utf-8-sig"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="f75aa95")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    first = RL.read_run(FIRST_RUN)
    second = RL.read_run(SECOND_RUN)
    # `read_run` folds every junit in the directory into counts and a failing
    # list; the per-node status map is what the accounting below needs, and it
    # is read from the same parser rather than re-derived.
    second_status = {}
    for xml in sorted(SECOND_RUN.glob("*.xml")):
        second_status.update(RL._junit_cases(xml))
    if not second_status:
        raise SystemExit("the second run produced no junit; nothing to classify")

    first_fail = set(first["failing_node_ids"])
    second_fail = set(second["failing_node_ids"])

    required = json.loads(FIRST_CLASSIFICATION.read_text(encoding="utf-8-sig"))
    required_closed = list(required["classes"]["TRUE_NEW_FAILURE"])

    # -- question 2: account for every original node id --------------------- #
    accounting = OrderedDict()
    for node in required_closed:
        moved_to = MOVED.get(node)
        target = moved_to or node
        status = second_status.get(target)
        if node in PRE_EXISTING_AT_PARENT:
            verdict = "PRE_EXISTING_AT_PARENT" if target in second_fail else "CLOSED"
            why = PRE_EXISTING_AT_PARENT[node]
        elif status is None:
            verdict, why = "NOT_COLLECTED", "the second run never collected it"
        elif target in second_fail:
            verdict, why = "STILL_FAILING", "failed again in the second broad run"
        else:
            verdict = "CLOSED"
            why = ("renamed to %s, which passes" % moved_to) if moved_to else "passes"
            if node in ORDER_DEPENDENT:
                why = ORDER_DEPENDENT[node]
        accounting[node] = OrderedDict((("verdict", verdict), ("why", why),
                                        ("moved_to", moved_to or "")))

    still = [n for n, r in accounting.items() if r["verdict"] == "STILL_FAILING"]
    uncollected = [n for n, r in accounting.items() if r["verdict"] == "NOT_COLLECTED"]
    pre_existing = [n for n, r in accounting.items()
                    if r["verdict"] == "PRE_EXISTING_AT_PARENT"]
    closed = [n for n, r in accounting.items() if r["verdict"] == "CLOSED"]

    # -- question 1: failure-set identity ----------------------------------- #
    fixed = sorted(first_fail - second_fail)
    appeared = sorted(second_fail - first_fail)

    # -- question 3: classify against the committed baseline ---------------- #
    baseline = load_baseline(args.baseline)
    classification = RL.classify(second, baseline)
    true_new = list(classification["classes"]["TRUE_NEW_FAILURE"])
    # A TRUE_NEW node proved PRE_EXISTING at the parent commit is not this
    # order's, and saying so is the whole reason the parent-commit proof exists.
    # A node settled by an isolated re-run is not this order's either, and the
    # re-run result is recorded beside it rather than asserted.
    charlotte_true_new = [n for n in true_new
                          if n not in PRE_EXISTING_AT_PARENT
                          and n not in APPEARED_AND_EXPLAINED]

    doc = OrderedDict((
        ("schema", "ptf-failure-closure/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("base_sha", BASE_SHA),
        ("head_sha", git("rev-parse", "HEAD")),
        ("why_a_second_broad_run", (
            "regression_delta classify answers FULL_REGRESSION_REQUIRED: YES. The "
            "participation record, Charlotte's release contract and the bundle-cache "
            "closure are DEPLOYMENT_CHANGE, and the closure file is a narrowing "
            "blocker. Nothing narrower proves this change surface.")),
        ("runs", OrderedDict((
            ("first", OrderedDict((("dir", FIRST_RUN.name),
                                   ("failing", len(first_fail))))),
            ("second", OrderedDict((("dir", SECOND_RUN.name),
                                    ("collected", second["collected"]),
                                    ("passed", second["passed"]),
                                    ("skipped", second["skipped"]),
                                    ("failing", len(second_fail))))),
        ))),
        ("failure_set_identity", OrderedDict((
            ("proved_by", "node id, never count"),
            ("fixed_since_the_first_run", fixed),
            ("fixed_count", len(fixed)),
            ("appeared_since_the_first_run", appeared),
            ("appeared_count", len(appeared)),
            ("appeared_and_explained",
             OrderedDict((n, APPEARED_AND_EXPLAINED[n]) for n in appeared
                         if n in APPEARED_AND_EXPLAINED)),
            ("appeared_and_UNEXPLAINED",
             [n for n in appeared if n not in APPEARED_AND_EXPLAINED]),
            ("NO_UNEXPLAINED_FAILURE_APPEARED",
             not [n for n in appeared if n not in APPEARED_AND_EXPLAINED]),
        ))),
        ("original_true_new_node_ids", required_closed),
        ("node_id_accounting", accounting),
        ("closed", closed),
        ("still_failing", still),
        ("not_collected", uncollected),
        ("pre_existing_at_parent", pre_existing),
        ("renamed_node_ids", MOVED),
        ("against_baseline", OrderedDict((
            ("baseline_source_sha", classification.get("baseline_source_sha")),
            ("baseline_is_stale", (
                "f75aa95 predates Lexington and Nashville, so nodes those markets "
                "left red classify as TRUE_NEW against it. Each is proved PRE_EXISTING "
                "by running it in a worktree at %s." % BASE_SHA)),
            ("PRE_EXISTING", classification["counts"]["PRE_EXISTING"]),
            ("TRUE_NEW_against_the_stale_baseline", true_new),
        ))),
        ("FINAL_TRUE_NEW_FAILURE_AFTER_CLOSURE", len(charlotte_true_new)),
        ("final_true_new_node_ids", charlotte_true_new),
        ("ALL_ORIGINAL_FAILURES_ACCOUNTED_FOR",
         not still and not uncollected),
    ))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")
    print("first run failing              :", len(first_fail))
    print("second run failing             :", len(second_fail))
    print("fixed since the first run      :", len(fixed))
    print("appeared since the first run   :", len(appeared))
    for node in appeared:
        known = APPEARED_AND_EXPLAINED.get(node)
        print("   APPEARED", node, "->", known["verdict"] if known else "UNEXPLAINED")
    print("original TRUE_NEW accounted    : %d closed / %d pre-existing / %d still failing / %d uncollected"
          % (len(closed), len(pre_existing), len(still), len(uncollected)))
    for node in still + uncollected:
        print("   OPEN", node, accounting[node]["verdict"])
    print("FINAL_TRUE_NEW_FAILURE_AFTER_CLOSURE:", len(charlotte_true_new))
    for node in charlotte_true_new:
        print("   TRUE_NEW", node)
    print("written                        :", args.out)
    unexplained = [n for n in appeared if n not in APPEARED_AND_EXPLAINED]
    return 0 if (not still and not uncollected and not charlotte_true_new
                 and not unexplained) else 1


if __name__ == "__main__":
    raise SystemExit(main())
