"""PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 -- the focused battery.

Proves the NEW_MARKET_REGISTRATION_DATA_ONLY boundary REJECTS every dangerous
change the order names, and grants the class to exactly one thing: a
legitimate, complete, one-market registration proven by field.

The positive fixture is real: Charlotte's committed registration, read as the
diff between the pre-Charlotte commit ``11373275`` and this tree, with the
sealed package and FAST receipt the registration release lane committed under
``markets/{packages,receipts}/charlotte-nc/``. Every negative case starts from
that fixture and breaks exactly one thing.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import subprocess
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import ci_validation as CI
from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import registration_data_only as REG
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP

REPO = RD.REPO_ROOT
BASE = "11373275"
MARKET = "charlotte-nc"
PACKAGE_PATH = REPO / "launch_packages" / "pettripfinder" / "markets" / "packages" / MARKET
RECEIPTS_PATH = REPO / "launch_packages" / "pettripfinder" / "markets" / "receipts" / MARKET

#: The complete change set an ordinary Charlotte registration writes, plus the
#: package and receipt the release lane commits. Read from git and the tree.
REGISTRATION_PATHS = OrderedDict((
    ("deploy/netlify/launch_participation.json", "M"),
    ("deploy/netlify/release_contracts/charlotte-nc.json", "A"),
    ("launch_packages/pettripfinder/bundle_cache_closure.json", "M"),
    ("tests/pettripfinder/pins/market_state.json", "M"),
    ("launch_packages/pettripfinder/markets/charlotte-nc.json", "A"),
    ("launch_packages/pettripfinder/markets/authority/charlotte-nc/seed_businesses.csv", "A"),
    ("launch_packages/pettripfinder/markets/authority/charlotte-nc/hotel_exclusions.json", "A"),
    ("launch_packages/pettripfinder/markets/authority/charlotte-nc/identity_routing.json", "A"),
    ("launch_packages/pettripfinder/markets/authority/charlotte-nc/affiliate_destinations.json", "A"),
    ("launch_packages/pettripfinder/seed_businesses.csv", "M"),
    ("launch_packages/pettripfinder/hotel_exclusions.json", "M"),
    ("launch_packages/pettripfinder/ptf_global_authority_manifest.json", "M"),
    ("launch_packages/pettripfinder/markets/reports/charlotte_nc_participation_registration_010.json", "A"),
))


def _committed_package_and_receipt():
    packages = sorted(PACKAGE_PATH.glob("pkg-*.json"))
    receipts = sorted(RECEIPTS_PATH.glob("pkg-*.json"))
    assert packages and receipts, "the registration release lane's Charlotte package and receipt must be committed"
    return packages[-1], receipts[-1]


def _paths():
    package, receipt = _committed_package_and_receipt()
    out = OrderedDict(REGISTRATION_PATHS)
    out[package.relative_to(REPO).as_posix()] = "A"
    out[receipt.relative_to(REPO).as_posix()] = "A"
    return out


def _rows(paths=None):
    rows = []
    for rel, status in (paths or _paths()).items():
        classes, rule = RD.classify_path(rel)
        rows.append(OrderedDict((("path", rel), ("status", status), ("classes", list(classes)),
                                 ("rule", rule), ("why", ""), ("shared_test_state", False),
                                 ("markets", []), ("market_local_proof", None), ("renamed_from", None))))
    return rows


def _blockers(paths):
    return [p for p in paths if RD.is_narrowing_blocker(p)]


def _bytes(rev, rel):
    data = REG.bytes_at(rev, rel)
    assert data is not None, (rev, rel)
    return data


def _mutate_json(raw: bytes, fn) -> bytes:
    doc = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    fn(doc)
    return (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


@pytest.fixture(scope="module")
def live():
    idx, state, problems = RI.live_index()
    assert not problems, problems
    return idx, state, problems


@pytest.fixture(autouse=True)
def _fast_live(monkeypatch, live):
    """The live index costs seconds; the proof reads it through one seam."""
    monkeypatch.setattr(REG, "live_index", lambda: live)


@pytest.fixture(scope="module")
def package():
    path, _receipt = _committed_package_and_receipt()
    return SMP.read_sealed(path)


@pytest.fixture(scope="module")
def base_contracts():
    out = OrderedDict()
    for mid in REG.release_contract_ids_at(BASE):
        out[mid] = _bytes(BASE, "deploy/netlify/release_contracts/%s.json" % mid)
    return out


@pytest.fixture
def participation():
    return _bytes(BASE, REG.PARTICIPATION_PATH), _bytes(RD.WORKTREE, REG.PARTICIPATION_PATH)


@pytest.fixture
def closure():
    return _bytes(BASE, REG.CLOSURE_PATH), _bytes(RD.WORKTREE, REG.CLOSURE_PATH)


@pytest.fixture
def pin():
    return _bytes(BASE, REG.MARKET_STATE_PIN_PATH), _bytes(RD.WORKTREE, REG.MARKET_STATE_PIN_PATH)


@pytest.fixture
def contract():
    return _bytes(RD.WORKTREE, "deploy/netlify/release_contracts/%s.json" % MARKET)


def _classify_as_registration(monkeypatch, paths):
    """Run the REAL classifier over a change set, with git's file listing
    replaced by ``paths`` -- every byte is still read from git / the tree."""
    monkeypatch.setattr(RD, "changed_files", lambda base, head=RD.WORKTREE: OrderedDict(paths))
    RD.RENAMED_FROM.clear()
    return RD.classify_change(BASE, RD.WORKTREE)


# --------------------------------------------------------------------------- #
# The contract, the matrix and the path classes.
# --------------------------------------------------------------------------- #

class TestTheContract:
    def test_the_committed_contract_is_the_modules_contract(self):
        committed = json.loads(REG.CONTRACT_PATH.read_text(encoding="utf-8-sig"))
        assert committed == json.loads(json.dumps(REG.contract_document()))
        assert committed["change_class"] == RD.NEW_MARKET_REGISTRATION_DATA_ONLY
        assert committed["checks"] == list(REG.CHECKS)
        policies = {row["policy"] for row in committed["field_level_eligibility_matrix"]}
        assert policies == {REG.FIELD_DATA, REG.FIELD_DERIVED, REG.FIELD_BEHAVIOR, REG.FIELD_PROTECTED}

    def test_the_class_is_conditional_and_moves_neither_fixed_set(self):
        row = RD.VALIDATION_MATRIX[RD.NEW_MARKET_REGISTRATION_DATA_ONLY]
        assert row["full_regression"] == RD.CONDITIONAL and row["condition"]
        assert row["assembly"] == RD.NOT_REQUIRED and row["lanes"] == ()
        assert RD.NEW_MARKET_REGISTRATION_DATA_ONLY not in RD.MANDATORY_FULL_REGRESSION
        assert RD.NEW_MARKET_REGISTRATION_DATA_ONLY not in RD.SAFE_NARROW_CLASSES
        assert set(RD.MANDATORY_FULL_REGRESSION) == {RD.AUTHORITY_CHANGE, RD.GENERIC_RUNTIME_CHANGE, RD.SCHEMA_CHANGE,
                                                     RD.ROUTING_SEMANTIC_CHANGE, RD.DEPLOYMENT_CHANGE, RD.UNCLASSIFIED}
        doc = json.loads(RD.MATRIX_PATH.read_text(encoding="utf-8-sig"))
        assert RD.SURFACE_NEW_MARKET_REGISTRATION_DATA_ONLY in doc["release_surfaces"]
        rows = {r["release_surface"]: r for r in doc["release_surface_matrix"]}
        assert rows[RD.SURFACE_NEW_MARKET_REGISTRATION_DATA_ONLY]["FULL_REGRESSION_REQUIRED"] == "CONDITIONAL"
        assert doc["registration_data_only_contract"] == "launch_packages/pettripfinder/registration_data_only_contract.json"

    def test_the_path_classes_are_unchanged_and_the_proof_is_a_blocker(self):
        assert RD.classify_path(REG.PARTICIPATION_PATH)[0] == (RD.DEPLOYMENT_CHANGE,)
        assert RD.classify_path("deploy/netlify/release_contracts/charlotte-nc.json")[0] == (RD.DEPLOYMENT_CHANGE,)
        assert RD.classify_path(REG.CLOSURE_PATH)[0] == (RD.DEPLOYMENT_CHANGE,)
        assert RD.classify_path(REG.MARKET_STATE_PIN_PATH)[0] == (RD.TEST_EXPECTATION_CHANGE,)
        assert RD.is_narrowing_blocker(REG.CLOSURE_PATH) and RD.is_narrowing_blocker(REG.MARKET_STATE_PIN_PATH)
        assert RD.is_narrowing_blocker("scripts/pettripfinder/registration_data_only.py")
        assert RD.is_narrowing_blocker("launch_packages/pettripfinder/registration_data_only_contract.json")
        assert RD.classify_path("launch_packages/pettripfinder/registration_data_only_contract.json")[0] == (RD.GENERIC_RUNTIME_CHANGE,)

    def test_the_runbook_states_the_rule(self):
        text = (REPO / "docs" / "PTF_HARDENED_FACTORY_RUNBOOK.md").read_text(encoding="utf-8-sig")
        assert "NEW_MARKET_REGISTRATION_DATA_ONLY" in text and "registration_data_only" in text
        assert "AUTHORIZATION_READY" in text


# --------------------------------------------------------------------------- #
# Case 1 and case 26: the one legitimate registration.
# --------------------------------------------------------------------------- #

class TestTheLegitimateRegistration:
    def test_case_01_exactly_one_valid_new_market_is_eligible(self):
        paths = _paths()
        doc = REG.evaluate(_rows(paths), BASE, RD.WORKTREE, blockers=_blockers(paths))
        failed = {n: c["why"] for n, c in doc["checks"].items() if not c["pass"]}
        assert doc["ELIGIBLE"] == "YES", failed
        assert set(doc["checks"]) == set(REG.CHECKS)
        assert all(c["status"] == REG.PASS for c in doc["checks"].values())
        assert doc["market_id"] == MARKET and doc["FULL_REGRESSION_REQUIRED"] == "NO"
        assert doc["REMOTE_BROAD_JOBS_REQUIRED"] == 0 and doc["UNCHANGED_MARKETS_REBUILT"] == 0
        assert doc["REACHES"] == "AUTHORIZATION_READY" and doc["authorizes_deployment"] is False
        expected = doc["expected_release"]
        assert expected["actual_markets"] == 14
        assert (expected["unexpected_market_changes"], expected["unexpected_profile_changes"],
                expected["unexpected_route_changes"]) == (0, 0, 0)

    def test_case_26_legitimate_movement_classifies_as_the_class(self, monkeypatch):
        doc = _classify_as_registration(monkeypatch, _paths())
        assert doc["new_market_registration_data_only"]["ELIGIBLE"] == "YES"
        assert RD.NEW_MARKET_REGISTRATION_DATA_ONLY in doc["change_classes"]
        assert RD.DEPLOYMENT_CHANGE not in doc["change_classes"]
        assert RD.AUTHORITY_CHANGE not in doc["change_classes"]
        assert RD.SURFACE_NEW_MARKET_REGISTRATION_DATA_ONLY in doc["release_surfaces"]
        assert RD.SURFACE_CLASSIFIER_TEST_INFRA_CHANGE not in doc["release_surfaces"]
        assert RD.SURFACE_DEPLOYMENT_CHANGE not in doc["release_surfaces"]
        by_path = {r["path"]: r for r in doc["changed_files"]}
        proof = doc["new_market_registration_data_only"]
        assert set(proof["registration_paths"]) == {p for p in REGISTRATION_PATHS if "/reports/" not in p}
        for rel in proof["registration_paths"]:
            assert by_path[rel]["classes"] == [RD.NEW_MARKET_REGISTRATION_DATA_ONLY], rel
            assert MARKET in by_path[rel]["markets"]
            assert by_path[rel]["release_surface"] == RD.SURFACE_NEW_MARKET_REGISTRATION_DATA_ONLY
        for rel in proof["companion_paths"]:
            assert by_path[rel]["classes"] in ([RD.GENERATED_REPORT_ONLY], [RD.MARKET_DATA_PACKAGE]), rel
        plan = RD.plan_for(doc)
        assert plan["full_regression_required"] is False and plan["full_regression_decision"] == RD.NOT_REQUIRED
        assert plan["assembly_required"] is False and plan["lanes"] == []
        assert plan["NEW_MARKET_REGISTRATION_DATA_ONLY"] == "YES" and plan["REMOTE_BROAD_JOBS_REQUIRED"] == 0
        assert doc["market_authority_data_only"]["market_id"] is None
        # ci_validation, untouched, reads the verdict and requests zero remote jobs.
        required = CI.required_shards(doc, plan)
        assert required["FULL_REGRESSION_REQUIRED"] == "NO" and required["REMOTE_BROAD_JOBS"] == 0
        assert required["scope"] == CI.SCOPE_NONE and required["dispatch"] == "NONE"

    def test_the_class_is_never_selected_by_name_count_or_request(self, monkeypatch):
        head = REG.registered_market_ids_at(RD.WORKTREE)
        monkeypatch.setattr(REG, "registered_market_ids_at", lambda rev: head)
        paths = _paths()
        doc = REG.evaluate(_rows(paths), BASE, RD.WORKTREE, blockers=_blockers(paths))
        assert doc["ELIGIBLE"] == "NO" and "gained nothing" in doc["checks"]["change_set"]["why"]


# --------------------------------------------------------------------------- #
# Cases 2-5: membership.
# --------------------------------------------------------------------------- #

class TestMembership:
    def test_case_02_two_new_markets_in_one_operation_default_broad(self, monkeypatch):
        base = REG.registered_market_ids_at(BASE)
        monkeypatch.setattr(REG, "registered_market_ids_at",
                            lambda rev: base if rev == BASE else tuple(sorted(base + (MARKET, "raleigh-nc"))))
        paths = _paths()
        gate = REG.classify_change_set(_rows(paths), base=BASE, head=RD.WORKTREE, blockers=_blockers(paths))
        assert gate["market_id"] is None and "exactly one" in gate["result"]["why"]
        doc = _classify_as_registration(monkeypatch, paths)
        assert doc["new_market_registration_data_only"]["ELIGIBLE"] == "NO"
        assert RD.DEPLOYMENT_CHANGE in doc["change_classes"]
        assert RD.plan_for(doc)["full_regression_required"] is True

    def test_case_03_existing_market_silently_removed_fails(self, monkeypatch, package, live):
        base = REG.registered_market_ids_at(BASE)
        monkeypatch.setattr(REG, "registered_market_ids_at",
                            lambda rev: base if rev == BASE else tuple(m for m in base + (MARKET,) if m != "toledo-oh"))
        paths = _paths()
        gate = REG.classify_change_set(_rows(paths), base=BASE, head=RD.WORKTREE, blockers=_blockers(paths))
        assert gate["market_id"] is None and "removes" in gate["result"]["why"]
        # And at the release level: an actual candidate missing a live market.
        idx, state, _ = live
        expected, actual = REG.expected_and_actual(package, MARKET, idx, state)
        del actual.markets["toledo-oh"]
        report = REG.compare_complete(expected, actual)
        assert not report["passed"] and report["unexpected_market_changes"] >= 1

    def test_case_04_profile_removed_and_added_at_equal_count_fails(self, package, live):
        idx, state, _ = live
        expected, actual = REG.expected_and_actual(package, MARKET, idx, state)
        victim = actual.markets["nashville-tn"]
        key = next(iter(victim.profiles))
        swapped = OrderedDict(victim.profiles)
        entry = swapped.pop(key)
        swapped["a hotel nobody registered"] = dataclasses.replace(
            entry, identity_key="a hotel nobody registered", declared_identity_key="a hotel nobody registered",
            route="/pet-friendly-hotels/nashville-tn/a-hotel-nobody-registered/")
        actual.markets["nashville-tn"] = dataclasses.replace(victim, profiles=swapped)
        report = REG.compare_complete(expected, actual)
        assert report["expected_profiles"] == report["actual_profiles"], "the swap keeps the total unchanged"
        assert not report["passed"] and report["unexpected_profile_changes"] == 2
        result, _ = REG.check_expected_release(package, MARKET, idx, state)
        assert result["pass"], "the real tree is clean; only the mutated candidate fails"

    def test_case_05_route_removed_and_added_at_equal_count_fails(self, package, live):
        idx, state, _ = live
        expected, actual = REG.expected_and_actual(package, MARKET, idx, state)
        victim = actual.markets["toledo-oh"]
        key = next(iter(victim.profiles))
        moved = OrderedDict(victim.profiles)
        moved[key] = dataclasses.replace(moved[key], route=moved[key].route.rstrip("/") + "-moved/")
        actual.markets["toledo-oh"] = dataclasses.replace(victim, profiles=moved)
        report = REG.compare_complete(expected, actual)
        assert report["expected_routes"] == report["actual_routes"]
        assert not report["passed"] and report["unexpected_route_changes"] >= 1


# --------------------------------------------------------------------------- #
# Cases 6-9: the participation row.
# --------------------------------------------------------------------------- #

class TestParticipation:
    def test_the_real_reissue_passes(self, participation):
        base, head = participation
        result = REG.check_participation(base, head, MARKET)
        assert result["pass"], result["why"]
        assert result["detail"]["founder_authorized_unchanged"] is True
        assert result["detail"]["lineage_records"] == 9

    def test_case_06_participation_lineage_broken_fails(self, participation):
        base, head = participation
        def _truncate(doc):
            doc["decision"]["lineage"]["records"] = doc["decision"]["lineage"]["records"][1:]
        result = REG.check_participation(base, _mutate_json(head, _truncate), MARKET)
        assert not result["pass"] and "lineage" in result["why"]
        def _drop(doc):
            del doc["decision"]["lineage"]
        result = REG.check_participation(base, _mutate_json(head, _drop), MARKET)
        assert not result["pass"]

    def test_case_07_decision_by_position_or_wrong_identity_fails(self, participation):
        base, head = participation
        def _wrong_predecessor(doc):
            first = doc["decision"]["lineage"]["records"][0]
            doc["decision"]["supersedes"] = OrderedDict(first)
        result = REG.check_participation(base, _mutate_json(head, _wrong_predecessor), MARKET)
        assert not result["pass"] and "supersedes" in result["why"]

    def test_case_08_registration_writer_impersonates_founder_fails(self, participation):
        base, head = participation
        def _founder(doc):
            doc["decision"]["decided_by"] = "founder"
        result = REG.check_participation(base, _mutate_json(head, _founder), MARKET)
        assert not result["pass"] and "founder" in result["why"]
        def _someone_else(doc):
            doc["decision"]["decided_by"] = "PTF-SOME-OTHER-ORDER-001"
        result = REG.check_participation(base, _mutate_json(head, _someone_else), MARKET)
        assert not result["pass"] and "writing work order" in result["why"]

    def test_case_09_founder_authorization_fabricated_fails(self, participation):
        base, head = participation
        def _authorize_new(doc):
            for row in doc["markets"]:
                if row["market_id"] == MARKET:
                    row["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        result = REG.check_participation(base, _mutate_json(head, _authorize_new), MARKET)
        assert not result["pass"] and "authorized set moved" in result["why"]
        def _authorize_detroit(doc):
            for row in doc["markets"]:
                if row["market_id"] == "detroit-ann-arbor-mi":
                    row["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        result = REG.check_participation(base, _mutate_json(head, _authorize_detroit), MARKET)
        assert not result["pass"] and "existing row" in result["why"]
        def _founder_block(doc):
            for row in doc["markets"]:
                if row["market_id"] == MARKET:
                    row["founder_decision"] = {"decided_by": "founder"}
        result = REG.check_participation(base, _mutate_json(head, _founder_block), MARKET)
        assert not result["pass"] and "unknown key" in result["why"]


# --------------------------------------------------------------------------- #
# Cases 10, 11, 20: behavior-bearing and unknown fields.
# --------------------------------------------------------------------------- #

class TestBehaviorBearingFields:
    def test_the_real_contract_instance_passes(self, contract, base_contracts):
        result = REG.check_release_contract(contract, MARKET, base_contracts, verify=lambda m: [])
        assert result["pass"], result["why"]
        assert set(result["detail"]["shared_blocks_equal_base"]) == set(REG.CONTRACT_SHARED_BLOCKS)

    @pytest.mark.parametrize("label,mutate", [
        ("gate removed", lambda d: d["minimum_release_gates"].pop()),
        ("publish rule changed", lambda d: d["publish"]["forbidden_extensions"].remove(".py")),
        ("canonical host changed", lambda d: d["canonical"].__setitem__("canonical_host", "example.com")),
        ("token list changed", lambda d: d["forbidden_output_tokens"].append("extra")),
        ("grants deployment", lambda d: d["deployment_authorization"].__setitem__("grants_deployment", True)),
    ])
    def test_case_10_release_contract_behavior_setting_change_is_broad(self, contract, base_contracts, label, mutate):
        result = REG.check_release_contract(_mutate_json(contract, mutate), MARKET, base_contracts, verify=lambda m: [])
        assert not result["pass"], label

    def test_case_10_a_count_that_disagrees_with_the_derivation_fails(self, contract, base_contracts):
        result = REG.check_release_contract(contract, MARKET, base_contracts,
                                            verify=lambda m: ["reconciliation.published_pet_friendly: contract states 106, authority derives 105"])
        assert not result["pass"] and "derivation" in result["why"]

    def test_the_real_closure_passes(self, closure):
        base, head = closure
        result = REG.check_build_closure(base, head, MARKET, exists=lambda rel: (REPO / rel).is_file())
        assert result["pass"], result["why"]

    @pytest.mark.parametrize("label,mutate", [
        ("code module added", lambda d: d["code_modules"].append("scripts/pettripfinder/nobody.py")),
        ("per-market input changed", lambda d: d["per_market_data_inputs"].append("launch_packages/x/<market_id>.json")),
        ("a third path declared", lambda d: d["shared_data_inputs"].append("deploy/netlify/release_contracts/detroit-ann-arbor-mi.json")),
        ("what_this_is rewritten", lambda d: d.__setitem__("what_this_is", "something else")),
        ("note dropped", lambda d: d["remeasured_by"].pop()),
    ])
    def test_case_11_build_closure_execution_setting_change_is_broad(self, closure, label, mutate):
        base, head = closure
        result = REG.check_build_closure(base, _mutate_json(head, mutate), MARKET, exists=lambda rel: (REPO / rel).is_file())
        assert not result["pass"], label

    def test_case_20_unknown_changed_field_is_broad(self, contract, base_contracts, participation, closure, pin, package):
        result = REG.check_release_contract(_mutate_json(contract, lambda d: d.__setitem__("build_flags", {"x": 1})),
                                            MARKET, base_contracts, verify=lambda m: [])
        assert not result["pass"] and "not exactly the registration shape" in result["why"]
        base, head = participation
        result = REG.check_participation(base, _mutate_json(head, lambda d: d["decision"].__setitem__("activation", True)), MARKET)
        assert not result["pass"] and "unknown key" in result["why"]
        base, head = closure
        result = REG.check_build_closure(base, _mutate_json(head, lambda d: d.__setitem__("validation_policy", "relaxed")),
                                         MARKET, exists=lambda rel: (REPO / rel).is_file())
        assert not result["pass"] and "keys changed" in result["why"]
        base, head = pin
        result = REG.check_market_state_pin(base, _mutate_json(head, lambda d: d.__setitem__("tolerance", 3)), MARKET,
                                            package, _bytes(RD.WORKTREE, "deploy/netlify/release_contracts/%s.json" % MARKET))
        assert not result["pass"] and "keys changed" in result["why"]


# --------------------------------------------------------------------------- #
# Cases 12, 13: the current-state pin.
# --------------------------------------------------------------------------- #

class TestTheCurrentStatePin:
    def test_the_real_pin_block_passes(self, pin, package, contract):
        base, head = pin
        result = REG.check_market_state_pin(base, head, MARKET, package, contract)
        assert result["pass"], result["why"]
        assert result["detail"]["expected_from_package"]["pet_friendly"] == 106
        assert result["detail"]["blocks_head"] == result["detail"]["blocks_base"] + 1

    def test_case_12_current_state_derived_count_wrong_fails(self, pin, package, contract):
        base, head = pin
        def _off_by_one(doc):
            doc["markets"][MARKET]["pet_friendly"] = 105
            doc["markets"][MARKET]["profiles"] = 105
        result = REG.check_market_state_pin(base, _mutate_json(head, _off_by_one), MARKET, package, contract)
        assert not result["pass"] and "sealed package derives" in result["why"]
        def _another_block(doc):
            doc["markets"]["toledo-oh"]["pet_friendly"] += 1
        result = REG.check_market_state_pin(base, _mutate_json(head, _another_block), MARKET, package, contract)
        assert not result["pass"] and "existing pin block" in result["why"]

    def test_case_13_circular_expected_count_validation_fails(self, pin, package, contract, monkeypatch, tmp_path):
        """The pin agrees with the committed TREE (which is what a circular
        check would generate it from) but the sealed package derives one
        record fewer: the pin must fail, because the package is the
        independent side."""
        base, head = pin
        thinner = copy.deepcopy(package)
        thinner["pet_friendly_records"] = thinner["pet_friendly_records"][:-1]
        thinner["seed_rows"] = thinner["seed_rows"][:-1]
        result = REG.check_market_state_pin(base, head, MARKET, thinner, contract)
        assert not result["pass"] and "sealed package derives 105" in result["why"]
        # And the classifier would not even accept that package: it KEEPS the
        # declared head digests, but a fresh seal of the head authority does
        # not reproduce its digest, so it covers nothing.
        thinner = SMP.seal(SMP.body_of(thinner), sealed_at="2026-09-11T00:00:00Z")
        monkeypatch.setattr(SMP, "PACKAGES_DIR", tmp_path / "packages")
        SMP.write_sealed(thinner, tmp_path / "packages")
        found, lookup = REG.find_covering_package(MARKET, RD.WORKTREE)
        assert found is None and lookup["covering"] == 0
        assert any("fresh seal" in s for s in lookup["packages_seen"])

    def test_the_expected_block_is_derived_from_the_package_alone(self, package):
        block = REG.expected_pin_block(package)
        assert block["census"] == package["census"]["count"]
        assert block["pet_friendly"] == len(package["pet_friendly_records"])
        assert block["unresolved"] == len(package["unresolved_rows"])
        assert block["census"] == block["resolved"] + block["unresolved"]


# --------------------------------------------------------------------------- #
# Cases 14, 15: identity and route collisions.
# --------------------------------------------------------------------------- #

class TestCollisions:
    def _with_foreign_profile(self, package, live, *, route_only):
        idx, state, _ = live
        expected, actual = REG.expected_and_actual(package, MARKET, idx, state)
        donor = idx.markets["nashville-tn"]
        key, entry = next(iter(donor.profiles.items()))
        mine = OrderedDict(expected.markets[MARKET].profiles)
        if route_only:
            own_key = next(iter(mine))
            mine[own_key] = dataclasses.replace(mine[own_key], route=entry.route)
        else:
            mine[key] = dataclasses.replace(entry, market_id=MARKET)
        expected.markets[MARKET] = dataclasses.replace(expected.markets[MARKET], profiles=mine)
        return idx, (expected, actual)

    def test_case_14_cross_market_identity_collision_fails(self, package, live):
        idx, releases = self._with_foreign_profile(package, live, route_only=False)
        result = REG.check_identity_routes(package, MARKET, idx, releases)
        assert not result["pass"]
        assert RI.CROSS_MARKET_IDENTITY_COLLISION in result["detail"]["expected"]["finding_counts"] \
            or RI.OWNERSHIP_MOVEMENT in result["detail"]["expected"]["finding_counts"]

    def test_case_15_route_ownership_collision_fails(self, package, live):
        idx, releases = self._with_foreign_profile(package, live, route_only=True)
        result = REG.check_identity_routes(package, MARKET, idx, releases)
        assert not result["pass"]
        assert RI.DUPLICATE_ROUTE in result["detail"]["expected"]["finding_counts"]

    def test_the_real_releases_scan_clean(self, package, live):
        idx, state, _ = live
        _result, releases = REG.check_expected_release(package, MARKET, idx, state)
        result = REG.check_identity_routes(package, MARKET, idx, releases)
        assert result["pass"], result["why"]


# --------------------------------------------------------------------------- #
# Cases 16-19: parent, receipt, package and candidate binding.
# --------------------------------------------------------------------------- #

class TestBinding:
    def test_the_real_package_and_receipt_bind(self, package, live):
        idx, state, _ = live
        found, lookup = REG.find_covering_package(MARKET, RD.WORKTREE)
        assert found is not None and found["package_digest"] == package["package_digest"]
        assert REG.check_sealed_package(found, MARKET, state, idx, lookup)["pass"]
        receipt = REG.check_fast_receipt(found, MARKET, state, idx)
        assert receipt["pass"], receipt["why"]
        assert receipt["detail"]["rules_passed"] == 15 and receipt["detail"]["unknown"] == [] and receipt["detail"]["failed"] == []

    def test_case_16_stale_parent_fails(self, package, live):
        idx, state, _ = live
        stale = copy.deepcopy(package)
        stale["parent_live_state"]["live_deploy_id"] = "000000000000000000000000"
        result = REG.check_sealed_package(stale, MARKET, state, idx, OrderedDict())
        assert not result["pass"] and "parent_live_state.live_deploy_id" in result["why"]
        older = dataclasses.replace(state, deploy_id="000000000000000000000000")
        result = REG.check_fast_receipt(package, MARKET, older, idx)
        assert not result["pass"] and "stale or wrong parent" in result["why"]

    def _receipt_variant(self, monkeypatch, tmp_path, mutate):
        _package_path, receipt_path = _committed_package_and_receipt()
        doc = json.loads(receipt_path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
        mutate(doc)
        monkeypatch.setattr(SMP, "RECEIPTS_DIR", tmp_path / "receipts")
        FL.write_receipt(doc, tmp_path / "receipts")

    def test_case_17_stale_or_wrong_validation_receipt_fails(self, package, live, monkeypatch, tmp_path):
        idx, state, _ = live
        self._receipt_variant(monkeypatch, tmp_path, lambda d: d["PARENT_RELEASE"].__setitem__("live_index_digest", "sha256:" + "0" * 64))
        result = REG.check_fast_receipt(package, MARKET, state, idx)
        assert not result["pass"] and "stale" in result["why"]

    def test_case_17_a_corrupt_receipt_fails(self, package, live, monkeypatch, tmp_path):
        idx, state, _ = live
        def _corrupt(doc):
            doc["RESULTS"]["C"]["status"] = FL.PASS
            doc["INTENDED_DELTA_DIGEST"] = "sha256:" + "1" * 64
        self._receipt_variant(monkeypatch, tmp_path, _corrupt)
        result = REG.check_fast_receipt(package, MARKET, state, idx)
        assert not result["pass"] and "corrupt" in result["why"]

    def test_case_17_a_receipt_with_an_unknown_rule_is_not_eligible(self, package, live, monkeypatch, tmp_path):
        idx, state, _ = live
        def _unknown(doc):
            doc["UNKNOWN_RULES"] = ["K"]
        self._receipt_variant(monkeypatch, tmp_path, _unknown)
        result = REG.check_fast_receipt(package, MARKET, state, idx)
        assert not result["pass"] and "no committed receipt" in result["why"]

    def test_case_17_a_missing_receipt_fails(self, package, live, monkeypatch, tmp_path):
        idx, state, _ = live
        monkeypatch.setattr(SMP, "RECEIPTS_DIR", tmp_path / "empty")
        result = REG.check_fast_receipt(package, MARKET, state, idx)
        assert not result["pass"] and "no committed receipt" in result["why"]

    def test_case_18_package_mismatch_fails(self, package, live, monkeypatch, tmp_path):
        idx, state, _ = live
        other = copy.deepcopy(package)
        other["dependency_input_digests"]["seed"] = "sha256:" + "f" * 64
        other = SMP.seal(SMP.body_of(other), sealed_at="2026-09-11T00:00:00Z")
        monkeypatch.setattr(SMP, "PACKAGES_DIR", tmp_path / "packages")
        SMP.write_sealed(other, tmp_path / "packages")
        found, lookup = REG.find_covering_package(MARKET, RD.WORKTREE)
        assert found is None and lookup["covering"] == 0
        result = REG.check_sealed_package(found, MARKET, state, idx, lookup)
        assert not result["pass"] and "no committed sealed package" in result["why"]

    def test_case_19_candidate_mismatch_fails(self, package, live):
        idx, state, _ = live
        thinner = copy.deepcopy(package)
        thinner["pet_friendly_records"] = thinner["pet_friendly_records"][:-1]
        thinner["seed_rows"] = thinner["seed_rows"][:-1]
        result, _releases = REG.check_expected_release(thinner, MARKET, idx, state)
        assert not result["pass"] and result["detail"]["unexpected_profile_changes"] >= 1
        assert "profile count expected" in result["why"] or "differ" in result["why"]


# --------------------------------------------------------------------------- #
# Cases 21-25: anything that is not registration data widens.
# --------------------------------------------------------------------------- #

class TestEverythingElseIsBroad:
    @pytest.mark.parametrize("label,extra", [
        ("case 21 shared runtime", ("scripts/pettripfinder/site_data.py", "M")),
        ("case 22 schema", ("scripts/pettripfinder/contracts/policy_schema.py", "M")),
        ("case 23 assembler", ("scripts/pettripfinder/assemble_netlify_bundle.py", "M")),
        ("case 24 deployment implementation", ("scripts/pettripfinder/global_deployment.py", "M")),
        ("case 24 deployment record", ("deploy/netlify/deployment_records/ptf-deploy-999-000000000000000000000000.json", "A")),
        ("case 24 activation flag", ("launch_packages/pettripfinder/fast_release_activation.json", "M")),
        ("case 25 classifier", ("scripts/pettripfinder/regression_delta.py", "M")),
        ("case 25 the proof itself", ("scripts/pettripfinder/registration_data_only.py", "M")),
        ("case 25 conftest", ("tests/pettripfinder/conftest.py", "M")),
        ("case 25 a test expectation", ("tests/pettripfinder/test_launch_participation_046.py", "M")),
        ("another market's shard", ("launch_packages/pettripfinder/markets/authority/toledo-oh/seed_businesses.csv", "M")),
        ("another market's contract", ("deploy/netlify/release_contracts/toledo-oh.json", "M")),
        ("another market's package", ("launch_packages/pettripfinder/markets/packages/toledo-oh/pkg-toledo-oh-0000000000000000.json", "A")),
        ("the deployment pin", ("tests/pettripfinder/pins/deployment_state.json", "M")),
        ("an unclassified loose file", ("launch_packages/pettripfinder/charlotte_nc_something_099.json", "A")),
    ])
    def test_cases_21_to_25_are_not_eligible(self, monkeypatch, label, extra):
        paths = _paths()
        paths[extra[0]] = extra[1]
        gate = REG.classify_change_set(_rows(paths), base=BASE, head=RD.WORKTREE, blockers=_blockers(paths))
        assert not gate["result"]["pass"], label
        doc = _classify_as_registration(monkeypatch, paths)
        assert doc["new_market_registration_data_only"]["ELIGIBLE"] == "NO", label
        assert RD.NEW_MARKET_REGISTRATION_DATA_ONLY not in doc["change_classes"], label
        assert RD.plan_for(doc)["full_regression_required"] is True, label

    def test_a_registration_missing_a_required_output_is_not_a_registration(self, monkeypatch):
        paths = _paths()
        del paths[REG.CLOSURE_PATH]
        gate = REG.classify_change_set(_rows(paths), base=BASE, head=RD.WORKTREE, blockers=_blockers(paths))
        assert not gate["result"]["pass"] and "absent from the change set" in gate["result"]["why"]

    def test_an_unknown_check_is_a_failure_never_a_pass(self, monkeypatch):
        def _boom():
            raise RuntimeError("no live state today")
        monkeypatch.setattr(REG, "live_index", _boom)
        paths = _paths()
        doc = REG.evaluate(_rows(paths), BASE, RD.WORKTREE, blockers=_blockers(paths))
        assert doc["ELIGIBLE"] == "NO" and "sealed_package" in doc["unknown_checks"]
        assert doc["FULL_REGRESSION_REQUIRED"] == "YES"

    def test_this_work_orders_own_change_set_is_broad(self):
        """The order that adds the class cannot be narrowed by it."""
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True)
        assert out.returncode == 0
        classes, _rule = RD.classify_path("scripts/pettripfinder/registration_data_only.py")
        assert classes == (RD.GENERIC_RUNTIME_CHANGE,)
        row = {"path": "scripts/pettripfinder/registration_data_only.py", "classes": list(classes)}
        assert RD.release_surface_of(row) == RD.SURFACE_CLASSIFIER_TEST_INFRA_CHANGE
