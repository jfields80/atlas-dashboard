"""PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002 -- classify the broad regression.

A registration re-tests every project-wide assumption about which markets exist,
so this order runs the FULL suite rather than a lane. The result is classified by
NODE ID against the committed baseline, never by count. 160 failures matching a
160-failure baseline proves nothing on its own; the same number can hide a fixed
failure and a fresh one. What this report asserts is SET IDENTITY.

Two runs are recorded. Run 1 carried nine failures the baseline does not have,
every one of them this order's own defect, and all nine were fixed at cause
rather than scoped away. Run 2 is the clean rerun.
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

WORK_ORDER = "PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
BASELINE = os.path.join(PKG, "regression_baselines", "f75aa95.json")
OUT = os.path.join(PKG, "markets", "reports", "toledo_oh_regression_classification_002.json")

#: Why each of run 1's nine node ids failed, and how it was closed. Every one is
#: this order's own bookkeeping or its own applier -- none is a relaxed gate.
RUN1_CAUSES = OrderedDict([
    ("tests/pettripfinder/test_service_animal_correction_011.py::"
     "test_no_committed_record_newly_fails_schema_validation",
     "APPLIER DEFECT. service_animal_statement was written inside facts, where policy_schema "
     "flags it as a MISPLACED_FIELD by name. Fixed at cause: the statement is a record-level "
     "structured field, not a fact."),
    ("tests/pettripfinder/test_affiliate_destinations.py::TestCommittedState::"
     "test_the_committed_shards_are_what_empty_document_renders",
     "APPLIER DEFECT. Toledo's policy records were written without the record envelope the "
     "contract requires. Fixed at cause by validating every record through "
     "policy_schema.validate_record INSIDE the applier, which now refuses to write instead of "
     "leaving a broken shard for a test to find."),
    ("tests/pettripfinder/test_global_assembler.py::"
     "test_current_live_inventory_preserves_all_assemblable_market_profiles",
     "APPLIER DEFECT. Flat pet fees were published as fee_tiers with invalid enum values "
     "(role PRICE, condition_type none). A tier requires a real condition; a flat fee has none "
     "and belongs in pet_fee. Fixed at cause in fee_from(), then the expected Toledo count was "
     "added to the assembler suite."),
    ("tests/pettripfinder/test_factory_throughput_001.py::TestCrossMarketIsolationIsProtected::"
     "test_identity_keys_are_unique_within_every_market",
     "REGISTRY COUNT. The suite enumerates registered markets; Toledo is the twelfth."),
    ("tests/pettripfinder/test_factory_throughput_001.py::TestTheHarness::"
     "test_the_committed_inventory_reproduces_from_the_suite",
     "REGISTRY COUNT. The committed test inventory was regenerated to include this order's "
     "two suites."),
    ("tests/pettripfinder/test_markets.py::"
     "test_production_markets_dir_loads_and_is_single_market_columbus",
     "REGISTRY COUNT. The expected market id list grew by toledo-oh."),
    ("tests/pettripfinder/test_st_louis_production_safety_001.py::TestStLouisIsNowRegistered::"
     "test_the_registry_grew_by_exactly_one",
     "REGISTRY COUNT. len(load_markets()) moved from 11 to 12."),
    ("tests/pettripfinder/test_launch_participation_046.py::"
     "test_the_bundle_excludes_only_the_two_that_are_not_source_ready",
     "REGISTRY COUNT. Toledo joins Detroit as a registered market that does not participate."),
    ("tests/pettripfinder/test_two_market_compat.py::"
     "test_an_unknown_market_id_fails_closed_rather_than_falling_back",
     "TEST USED toledo-oh AS ITS EXAMPLE of an unregistered id, so it silently stopped "
     "asserting anything the moment Toledo registered. Repointed at not-a-market-zz, an id no "
     "market can hold. The same latent defect was fixed in test_per_market_release_contracts "
     "and test_market_authority_sharding."),
])


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run1", default=os.path.join(_DASH, "data", "regression", "toledo_full"))
    ap.add_argument("--run2", default=os.path.join(_DASH, "data", "regression", "toledo_full2"))
    ap.add_argument("--baseline", default=BASELINE)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    base_doc = _load(args.baseline)
    base = set(base_doc["failing_node_ids"])
    r1 = _load(os.path.join(args.run1, "run.json"))
    r2 = _load(os.path.join(args.run2, "run.json"))
    s1, s2 = set(r1["failing_node_ids"]), set(r2["failing_node_ids"])

    new = sorted(s2 - base)
    gone = sorted(base - s2)
    identical = not new and not gone

    r1_new = sorted(s1 - base)
    unexplained = [n for n in r1_new if n not in RUN1_CAUSES]

    doc = OrderedDict([
        ("schema", "ptf-regression-classification/2.0"),
        ("work_order", WORK_ORDER),
        ("classified_at", "2026-09-06"),
        ("lane", "full_regression"),
        ("why_the_full_suite",
         "This order REGISTERS a market. A registration is the one change class that re-tests "
         "every project-wide assumption about which markets exist, so no narrow lane is "
         "admissible and the broad run is mandatory."),
        ("baseline", OrderedDict([
            ("path", os.path.relpath(args.baseline, _DASH).replace("\\", "/")),
            ("source_sha", base_doc.get("source_sha")),
            ("failing_node_ids", len(base)),
        ])),
        ("proof_method",
         "SET IDENTITY by node id, never counts. A matching failure COUNT is not a proof: it is "
         "equally consistent with one baseline failure being fixed and one new failure appearing. "
         "The assertion below is that the run's failing node-id set and the baseline's are the "
         "same set."),
        ("run_1", OrderedDict([
            ("run_dir", r1["run_dir"].replace("\\", "/")),
            ("collected", r1["collected"]),
            ("passed", r1["passed"]),
            ("failed", r1["failed"]),
            ("seconds", r1["timing"][0]["seconds"]),
            ("true_new_failures", len(r1_new)),
            ("every_new_failure_was_this_orders_own",
             OrderedDict((n, RUN1_CAUSES[n]) for n in r1_new if n in RUN1_CAUSES)),
            ("unexplained_new_failures", unexplained),
            ("disposition",
             "All %d were fixed AT CAUSE. Three were real applier defects that would have "
             "shipped a package the record contract rejects; five were registry counts that a "
             "twelfth market legitimately moves; one was a project test that had used toledo-oh "
             "as its example of an unregistered id. No gate was weakened or scoped away."
             % len(r1_new)),
        ])),
        ("run_2", OrderedDict([
            ("run_dir", r2["run_dir"].replace("\\", "/")),
            ("collected", r2["collected"]),
            ("passed", r2["passed"]),
            ("skipped", r2["skipped"]),
            ("failed", r2["failed"]),
            ("seconds", r2["timing"][0]["seconds"]),
            ("failing_node_ids", len(s2)),
            ("in_run_not_in_baseline", new),
            ("in_baseline_not_in_run", gone),
            ("failure_set_identical_to_baseline", identical),
        ])),
        ("classification", OrderedDict([
            ("PRE_EXISTING", len(s2 & base)),
            ("EXPECTED_EPOCH_CHANGE", 0),
            ("TEST_HARNESS_FLAKE", 0),
            ("TRUE_NEW_FAILURE", len(new)),
        ])),
        ("verdict",
         "CLEAN -- the broad run reproduces the f75aa95 baseline failure set EXACTLY by node id, "
         "0 TRUE_NEW_FAILURE" if identical else
         "NOT CLEAN -- the failure set differs from the baseline; do not proceed"),
    ])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("baseline node ids :", len(base))
    print("run 1             :", r1["failed"], "failed |", len(r1_new), "TRUE_NEW, all fixed")
    print("run 2             :", r2["failed"], "failed |", len(s2), "node ids")
    print("new vs baseline   :", len(new), "| missing vs baseline:", len(gone))
    print("SET IDENTICAL     :", identical)
    print("TRUE_NEW_FAILURE  :", len(new))
    print("written           :", os.path.relpath(args.out, _DASH).replace("\\", "/"))
    return 0 if identical and not unexplained else 1


if __name__ == "__main__":
    raise SystemExit(main())
