# -*- coding: utf-8 -*-
"""PTF-FACTORY-THROUGHPUT-HARDENING-001 A9 -- the regression refactor proves
itself.

Five things the order requires, each shown rather than asserted in prose:

1. a historical cohort suite still catches mutation of its original records;
2. a current-state suite detects an unauthorised change to a current count;
3. later legitimate growth does NOT produce stale count failures;
4. deployment authorization history stays protected;
5. cross-market isolation stays protected.

Plus the harness itself: the lane table covers every module Dayton
APPLICATION-002 broke, the baseline classifier compares node ids and not
counts, and the committed inventory report reproduces from the suite.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from pettripfinder import epochs
from pettripfinder import market_state as MS
from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import regression_inventory as INV
from scripts.pettripfinder import regression_lanes as RL
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash
from scripts.pettripfinder.site_data import published_facts_path

REPO_ROOT = Path(__file__).resolve().parents[2]
DAYTON = "dayton-oh"
CLEVELAND = "cleveland-akron-canton-oh"
INDIANAPOLIS = "indianapolis-in"
PASS_C_LEDGER = "dayton_passB_founder_decisions.json"
APPLICATION_002 = "PTF-DAYTON-OH-HARDENED-APPLICATION-002"
FUTURE_ORDER = "PTF-DAYTON-OH-HYPOTHETICAL-GROWTH-999"

#: The modules PTF-DAYTON-OH-HARDENED-APPLICATION-002 had to re-pin (from
#: ``git diff --stat 2030358..c854469 -- tests``), relative to tests/pettripfinder.
DAYTON_002_BROKE = (
    "contracts/test_compat_readers.py", "contracts/test_market_authorities.py",
    "test_dayton_authority.py", "test_dayton_hardened_revalidation_001.py",
    "test_dayton_pass_a_artifact_verification.py",
    "test_dayton_pass_b_founder_decisions.py",
    "test_dayton_pass_b_policy_corrections.py",
    "test_dayton_pass_c_decision_application.py", "test_dayton_recovery_002.py",
    "test_dayton_work_browser_001.py", "test_deployment_authorization_047.py",
    "test_global_assembler.py", "test_global_deployment_architecture_045.py",
    "test_grand_rapids_launch_participation_032.py",
    "test_launch_participation_046.py", "test_per_market_release_contracts.py",
    "test_policy_schema_migration.py", "test_renderer_real_records.py",
)


def _package(market_id):
    return json.loads(published_facts_path(market_id).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1. Historical cohort suites still catch mutation of their records.
# --------------------------------------------------------------------------- #

class TestHistoricalCohortStillCatchesMutation:

    def test_the_pass_c_cohort_is_the_forty_seven_the_ledger_approved(self):
        package = _package(DAYTON)
        cohort = epochs.cohort(package["hotels"], epochs.by_ledger(PASS_C_LEDGER))
        assert len(cohort) == 47
        assert len(package["hotels"]) == MS.current(DAYTON).pet_friendly > 47

    def test_a_mutated_cohort_record_fails_its_own_hash(self):
        package = copy.deepcopy(_package(DAYTON))
        cohort = epochs.cohort(package["hotels"], epochs.by_ledger(PASS_C_LEDGER))
        victim = cohort[0]
        assert victim["approval"]["record_hash"] == record_hash(victim)
        victim["facts"]["pet_count_limit"] = 99
        assert victim["approval"]["record_hash"] != record_hash(victim)

    def test_a_mutated_evidence_entry_fails_its_own_hash(self):
        package = copy.deepcopy(_package(DAYTON))
        cohort = epochs.cohort(package["hotels"], epochs.by_ledger(PASS_C_LEDGER))
        victim = cohort[1]
        assert victim["approval"]["evidence_hash"] == evidence_hash(victim["evidence"])
        # The evidence hash is over the SET of evidence references (which
        # artifact, which field), so swapping a reference is the mutation it
        # sees; a quote is bound separately by the artifact sha it names.
        victim["evidence"][0]["evidence_ref"] = "sha256:" + "0" * 64
        assert victim["approval"]["evidence_hash"] != evidence_hash(victim["evidence"])

    def test_a_silently_dropped_cohort_record_changes_the_cohort_size(self):
        package = copy.deepcopy(_package(DAYTON))
        selector = epochs.by_ledger(PASS_C_LEDGER)
        epoch = epochs.HistoricalEpoch("PTF-DAYTON-RECERTIFICATION-001", DAYTON,
                                       facts={"pet_friendly": 47})
        epochs.assert_cohort_size(package["hotels"], selector, 47, epoch=epoch)
        dropped = [h for h in package["hotels"] if not selector(h)] \
            + [h for h in package["hotels"] if selector(h)][1:]
        with pytest.raises(AssertionError, match="PTF-DAYTON-RECERTIFICATION-001"):
            epochs.assert_cohort_size(dropped, selector, 47, epoch=epoch)

    def test_a_cohort_record_re_approved_under_another_ledger_leaves_the_cohort(self):
        """Rewriting a record's provenance is a mutation the selector sees."""
        package = copy.deepcopy(_package(DAYTON))
        selector = epochs.by_ledger(PASS_C_LEDGER)
        victim = epochs.cohort(package["hotels"], selector)[0]
        victim["approval"]["decision_source"]["ledger"] = "somebody_else.json"
        assert len(epochs.cohort(package["hotels"], selector)) == 46

    @pytest.mark.parametrize("market_id,selector,expected", [
        (CLEVELAND, epochs.by_caveat("PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005"), 21),
        (INDIANAPOLIS, epochs.by_caveat("PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014"), 11),
    ])
    def test_cleveland_and_indianapolis_cohorts_are_selectable_the_same_way(
            self, market_id, selector, expected):
        cohort = epochs.cohort(_package(market_id)["hotels"], selector)
        assert len(cohort) == expected, market_id
        for record in cohort:
            assert record["approval"]["record_hash"] == record_hash(record)


# --------------------------------------------------------------------------- #
# 2. Current-state suites detect an unauthorised current change.
# --------------------------------------------------------------------------- #

class TestCurrentStateDetectsUnauthorisedChange:

    def test_the_pin_matches_the_package_and_a_moved_pin_does_not(self, monkeypatch):
        pin = MS.current(DAYTON)
        package = _package(DAYTON)
        assert len(package["hotels"]) == pin.pet_friendly
        moved = pin.__class__(**{**pin.as_dict(), "market_id": DAYTON,
                                 "pet_friendly": pin.pet_friendly + 1})
        assert len(package["hotels"]) != moved.pet_friendly

    def test_a_record_added_without_moving_the_pin_is_caught_by_the_contract(self):
        """The single cross-check the suites rely on: package length against
        the pin. Adding one record without editing the pin must fail it."""
        package = copy.deepcopy(_package(DAYTON))
        package["hotels"].append(copy.deepcopy(package["hotels"][0]))
        assert len(package["hotels"]) != MS.current(DAYTON).pet_friendly

    def test_a_swap_that_keeps_the_count_is_still_caught_by_the_hash_gates(self):
        package = copy.deepcopy(_package(DAYTON))
        a = package["hotels"][0]
        a["name"] = "Some Other Hotel"
        assert len(package["hotels"]) == MS.current(DAYTON).pet_friendly
        assert a["approval"]["record_hash"] != record_hash(a)

    def test_every_market_pin_is_held_to_its_release_contract(self):
        from scripts.pettripfinder.release_contracts import load_contract
        for market_id in MS.market_ids():
            pin = MS.current(market_id)
            rec = load_contract(market_id)["reconciliation"]
            assert (rec["published_pet_friendly"], rec["verified_no_pets"]) == (
                pin.pet_friendly, pin.verified_no_pets), market_id


# --------------------------------------------------------------------------- #
# 3. Later legitimate growth produces no stale count failures.
# --------------------------------------------------------------------------- #

def _grown_package(market_id, *, extra=3, order=FUTURE_ORDER):
    """The live package plus ``extra`` records a hypothetical later order
    published, marked the way every application order marks its records."""
    package = copy.deepcopy(_package(market_id))
    template = package["hotels"][-1]
    for i in range(extra):
        record = copy.deepcopy(template)
        record["key"] = "hypothetical hotel %d" % i
        record["identity_key"] = record["key"]
        record["name"] = "Hypothetical Hotel %d" % i
        record["approval"]["decision_source"] = None
        record["approval"]["caveats"] = [
            "FOUNDER AUTHORIZATION (%s): apply the hypothetical row" % order]
        package["hotels"].append(record)
    return package


class TestLegitimateGrowthDoesNotBreakHistoricalSuites:

    def test_the_pass_c_cohort_is_unchanged_under_growth(self):
        grown = _grown_package(DAYTON)
        assert len(grown["hotels"]) == MS.current(DAYTON).pet_friendly + 3
        cohort = epochs.cohort(grown["hotels"], epochs.by_ledger(PASS_C_LEDGER))
        assert len(cohort) == 47

    def test_the_application_002_cohort_is_unchanged_under_growth(self):
        grown = _grown_package(DAYTON)
        cohort = epochs.cohort(grown["hotels"], epochs.by_caveat(APPLICATION_002))
        assert len(cohort) == 7
        later = epochs.cohort(grown["hotels"], epochs.by_caveat(FUTURE_ORDER))
        assert len(later) == 3

    def test_split_keeps_the_wider_invariant_runnable_over_the_rest(self):
        grown = _grown_package(DAYTON)
        cohort, rest = epochs.split(grown["hotels"], epochs.by_ledger(PASS_C_LEDGER))
        assert len(cohort) == 47 and len(rest) == 10
        for record in rest:
            assert record["approval"]["operator"]

    def test_whole_market_counts_are_superseded_by_name_when_the_pin_moves(self):
        """The one obsolete assertion a closed order keeps -- its whole-market
        count -- retires by the NAME of the order that moved the market, read
        from the pin, and nothing else in the suite changes."""
        epoch = epochs.HistoricalEpoch(APPLICATION_002, DAYTON,
                                       facts={"pet_friendly": 54})
        now = MS.current(DAYTON)
        # Unmoved: exact.
        epochs.whole_market_counts_or_superseded(epoch, now, {"pet_friendly": "pet_friendly"})
        # Moved by a later order: superseded, naming it.
        moved = now.__class__(**{**now.as_dict(), "market_id": DAYTON,
                                 "pet_friendly": 57, "last_moved_by": FUTURE_ORDER})
        before = len(epochs.DECLARED_SUPERSESSIONS)
        with pytest.raises(pytest.skip.Exception) as info:
            epochs.whole_market_counts_or_superseded(epoch, moved, {"pet_friendly": "pet_friendly"})
        assert FUTURE_ORDER in str(info.value)
        assert epochs.DECLARED_SUPERSESSIONS[-1].superseded_by == FUTURE_ORDER
        assert len(epochs.DECLARED_SUPERSESSIONS) == before + 1

    def test_a_pin_that_moved_without_naming_a_new_order_is_an_error_not_a_skip(self):
        epoch = epochs.HistoricalEpoch(APPLICATION_002, DAYTON, facts={"pet_friendly": 54})
        now = MS.current(DAYTON)
        inconsistent = now.__class__(**{**now.as_dict(), "market_id": DAYTON,
                                        "pet_friendly": 57})
        with pytest.raises(AssertionError, match="still names this order"):
            epochs.whole_market_counts_or_superseded(epoch, inconsistent,
                                                     {"pet_friendly": "pet_friendly"})

    def test_a_supersession_must_name_a_work_order(self):
        with pytest.raises(ValueError):
            epochs.superseded(by="later", what="whole-package count")
        with pytest.raises(ValueError):
            epochs.superseded(by=FUTURE_ORDER, what="   ")

    def test_the_numbers_dayton_002_restated_live_in_one_place_now(self):
        """The count 54 appears in the pin and in the release contract; the
        suites that used to restate it read the pin. A grep-level proof."""
        restating = []
        for rel in DAYTON_002_BROKE:
            text = (RL.PTF_TESTS / rel).read_text(encoding="utf-8")
            for needle in ('"dayton-oh": 54', "== 54\n", "(129, 54, 24, 78, 51)"):
                if needle in text:
                    restating.append((rel, needle))
        assert restating == []


# --------------------------------------------------------------------------- #
# 4. Deployment authorization history stays protected.
# --------------------------------------------------------------------------- #

class TestDeploymentHistoryIsProtected:

    def _git_bytes(self, rel):
        out = subprocess.run(["git", "show", "HEAD:%s" % rel], cwd=str(REPO_ROOT),
                             capture_output=True)
        return out.stdout if out.returncode == 0 else None

    def test_no_consumed_authorization_or_record_was_rewritten_by_this_order(self):
        for sub in ("deployment_authorizations", "deployment_records"):
            for path in sorted((REPO_ROOT / "deploy" / "netlify" / sub).glob("*.json")):
                rel = path.relative_to(REPO_ROOT).as_posix()
                committed = self._git_bytes(rel)
                if committed is None:
                    pytest.skip("not a git checkout")
                assert hashlib.sha256(committed).hexdigest() == \
                    hashlib.sha256(path.read_bytes()).hexdigest(), rel

    def test_every_authorization_verifies_at_its_own_shape(self):
        for auth in DA.list_authorizations():
            assert DA._shape_problems(auth) == [], auth["authorization_id"]

    def test_a_moved_market_is_named_with_the_order_that_moved_it(self):
        for auth_id, entry in epochs.supersession_registry()["authorizations"].items():
            for market_id, order in entry["moved_by_later_work"].items():
                assert epochs.is_work_order(order), (auth_id, market_id)

    def test_the_live_authorization_binds_every_market_exactly(self):
        live = MS.live()
        auth = DA.load_authorization(live.authorization_id)
        for row in auth["release_contracts"]:
            assert row["sha256"] == DA._sha256_file(REPO_ROOT / row["path"]), row["market_id"]

    def test_the_lapsed_source_allowance_is_gone_now_that_production_caught_up(self):
        from pettripfinder import conftest as C
        assert not hasattr(C, "manifest_problems_other_than_the_lapsed_dayton_contract")
        assert MS.source_assembly().ahead_of_production is False


# --------------------------------------------------------------------------- #
# 5. Cross-market isolation stays protected.
# --------------------------------------------------------------------------- #

class TestCrossMarketIsolationIsProtected:

    def test_no_premises_is_published_in_two_markets(self):
        """Identity keys are market-scoped (a bare chain word such as 'tru'
        can be a key in two markets); a PREMISES cannot be. One street and
        postal code publishes in at most one market's authority."""
        from scripts.pettripfinder.site_data import read_production_rows
        seen = {}
        for row in read_production_rows():
            if not (row.get("address") or "").strip():
                continue
            premises = (" ".join(row["address"].lower().split()),
                        (row.get("postal_code") or "").strip())
            owner = row.get("market_id")
            assert seen.get(premises, owner) == owner, (premises, seen.get(premises), owner)
            seen[premises] = owner

    def test_identity_keys_are_unique_within_every_market(self):
        for market_id in MS.market_ids():
            keys = [h["identity_key"] for h in _package(market_id)["hotels"]]
            assert len(keys) == len(set(keys)), market_id

    def test_every_package_names_its_own_market_and_only_its_own(self):
        for market_id in MS.market_ids():
            package = _package(market_id)
            assert package["market_id"] == market_id
            for record in package["hotels"]:
                if "market_id" in record:
                    assert record["market_id"] == market_id, record["identity_key"]

    def test_the_cross_market_lane_carries_the_isolation_modules(self):
        modules = RL.modules_in_lane(RL.CROSS_MARKET)
        for needed in ("test_market_isolation.py", "test_market_ownership.py",
                       "contracts/test_market_authorities.py"):
            assert "tests/pettripfinder/" + needed in modules, needed


# --------------------------------------------------------------------------- #
# The harness: lanes, classifier, inventory.
# --------------------------------------------------------------------------- #

class TestTheHarness:

    def test_every_module_dayton_002_broke_is_in_a_lane_the_normal_flow_runs(self):
        """Every module Dayton 002 had to re-pin is reached by the targeted
        lanes -- except the two whole-site assembly suites, which cost 24 of
        the old chunk's 27 minutes and now read their pins from ONE file
        (pins/deployment_state.json). Those run once, in the final regression,
        and the assembly step of the flow produces the same facts earlier."""
        flow_lanes = {RL.MARKET_TARGETED, RL.POLICY_SCHEMA, RL.IDENTITY_ROUTING,
                      RL.RELEASE_CONTRACT}
        final_only = {"test_global_deployment_architecture_045.py",
                      "test_launch_participation_046.py"}
        targeted = set(RL.modules_in_lane(RL.MARKET_TARGETED, market=DAYTON))
        for rel in DAYTON_002_BROKE:
            lanes = set(RL.lanes_for(rel))
            in_targeted = "tests/pettripfinder/" + rel in targeted
            if rel in final_only:
                assert RL.DEPLOYMENT_ARCHITECTURE in lanes and not in_targeted, rel
                continue
            assert in_targeted or (lanes & flow_lanes), (rel, lanes)

    def test_market_targeted_needs_a_market_and_names_only_that_markets_modules(self):
        with pytest.raises(ValueError):
            RL.modules_in_lane(RL.MARKET_TARGETED)
        modules = RL.modules_in_lane(RL.MARKET_TARGETED, market=DAYTON)
        assert "tests/pettripfinder/test_dayton_authority.py" in modules
        assert "tests/pettripfinder/test_cleveland_authority.py" not in modules
        assert "tests/pettripfinder/contracts/test_market_state_pins.py" in modules

    def test_every_lane_has_members_and_full_regression_is_everything(self):
        for lane in RL.LANES:
            if lane == RL.MARKET_TARGETED:
                continue
            assert RL.modules_in_lane(lane), lane
        assert RL.modules_in_lane(RL.FULL_REGRESSION) == ["tests"]

    def test_the_classifier_compares_node_ids_not_counts(self):
        baseline = RL.build_baseline(
            {"collected": 3, "passed": 1, "skipped": 0, "failed": 2,
             "failing_node_ids": ["t/a.py::test_x", "t/a.py::test_y"]},
            source_sha="abc1234")
        run = {"collected": 3, "passed": 1, "skipped": 0, "failed": 2,
               "failing_node_ids": ["t/a.py::test_x", "t/b.py::test_new"]}
        doc = RL.classify(run, baseline, expected_epoch_change=[],
                          rerun_results={})
        assert doc["counts"] == {RL.PRE_EXISTING: 1, RL.EXPECTED_EPOCH_CHANGE: 0,
                                 RL.TEST_HARNESS_FLAKE: 0, RL.TRUE_NEW_FAILURE: 1}
        assert doc["classes"][RL.TRUE_NEW_FAILURE] == ["t/b.py::test_new"]
        assert doc["baseline_failures_now_passing"] == ["t/a.py::test_y"]
        assert doc["clean"] is False
        # The same count, a different node: still a TRUE_NEW_FAILURE.
        expected = RL.classify(run, baseline, expected_epoch_change=["t/b.py::test_new"])
        assert expected["clean"] is True
        flaky = RL.classify(run, baseline, rerun_results={"t/b.py::test_new": "passed"})
        assert flaky["counts"][RL.TEST_HARNESS_FLAKE] == 1 and flaky["clean"] is True

    def test_the_committed_baseline_manifest_names_its_sha_and_node_ids(self):
        manifests = sorted(RL.BASELINES_DIR.glob("*.json"))
        assert manifests, "no baseline manifest committed"
        for path in manifests:
            doc = json.loads(path.read_text(encoding="utf-8"))
            assert doc["schema"] == RL.SCHEMA_BASELINE
            assert path.stem.startswith(doc["source_sha"][:7])
            assert all("::" in n for n in doc["failing_node_ids"])

    def test_the_committed_inventory_reproduces_from_the_suite(self):
        path = (REPO_ROOT / "launch_packages" / "pettripfinder" / "reports"
                / "factory_throughput_001_test_inventory.json")
        committed = json.loads(path.read_text(encoding="utf-8"))
        fresh = INV.build()
        assert fresh["schema"] == committed["schema"] == INV.SCHEMA
        assert set(fresh["by_class"]) == set(INV.CLASSES)
        assert fresh["modules_asserting_whole_package_counts"] == \
            committed["modules_asserting_whole_package_counts"]
        assert fresh["by_class"] == committed["by_class"]

    def test_the_lane_plan_describes_the_normal_flow_in_order(self):
        plan = RL.describe()
        steps = [s["lane"] for s in plan["normal_flow"]]
        assert steps == [RL.MARKET_TARGETED, RL.POLICY_SCHEMA, RL.IDENTITY_ROUTING,
                         RL.RELEASE_CONTRACT, "assemble", "fix_pins", "commit",
                         RL.FULL_REGRESSION]
        assert steps.count(RL.FULL_REGRESSION) == 1
