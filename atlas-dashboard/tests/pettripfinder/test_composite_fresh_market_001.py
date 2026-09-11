# -*- coding: utf-8 -*-
"""PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001 -- the composite
fresh-market class: the partition, the registration-mode isolation proof, the
three typed-input field checks, the frozen Raleigh change set as a fixture,
and the negative matrix.

Every test here reads committed bytes through git (the frozen Raleigh branch
``worker/ptf-raleigh-new-market-001`` at ``b613d72d`` / ``13809c36``, and the
base it was measured against, ``e3c27772``) or builds a scratch git
repository. Nothing here writes to the real tree.
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import market_local_isolation as ISO
from scripts.pettripfinder import market_local_ownership as OWN
from scripts.pettripfinder import registration_data_only as REG
from scripts.pettripfinder import regression_delta as RD

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"

MARKET = "raleigh-nc"
RALEIGH_BASE = "e3c27772"
RALEIGH_FROZEN = "b613d72d"        # the 42-file first-market change set
RALEIGH_FORENSIC = "13809c36"      # + the three forensic reports (45)
COMPOSITE = RD.COMPOSITE_FRESH_MARKET_DATA_ONLY

INPUT_PATH = "launch_packages/pettripfinder/raleigh_nc_proposed_authority_002.json"
OSM_PATH = REG.OSM_EXTRACTS_PATH
CONFIG_PATH = "scripts/pettripfinder/discovery/config/raleigh_nc.json"
RULINGS_PATH = REG.IDENTITY_RESOLUTIONS_PATH

#: The three frozen helpers the isolation proof REJECTS, and the condition
#: each fails. These are real dependencies, not names.
REJECTED = OrderedDict((
    ("scripts/pettripfinder/raleigh_nc_candidate_assembly_008.py", ("reachability", "assemble_production_site")),
    ("scripts/pettripfinder/raleigh_nc_participation_registration_010.py", ("imports", "assemble_production_site")),
    ("scripts/pettripfinder/raleigh_nc_release_lane_005.py", ("writes", "cannot be resolved statically")),
))


def _commit_exists(rev: str) -> bool:
    proc = subprocess.run(["git", "cat-file", "-e", rev + "^{commit}"], cwd=str(REPO_ROOT.parent), capture_output=True)
    return proc.returncode == 0


needs_raleigh = pytest.mark.skipif(not (_commit_exists(RALEIGH_BASE) and _commit_exists(RALEIGH_FROZEN)
                                        and _commit_exists(RALEIGH_FORENSIC)),
                                   reason="the frozen Raleigh branch is not in this repository")


def _rows(base: str, head: str):
    files = RD.changed_files(base, head)
    rows = []
    for rel, status in files.items():
        classes, rule = RD.classify_path(rel)
        rows.append(OrderedDict((("path", rel), ("status", status), ("classes", list(classes)), ("rule", rule))))
    blockers = [rel for rel in files if RD.is_narrowing_blocker(rel)]
    return rows, blockers


@pytest.fixture(scope="module")
def frozen():
    rows, blockers = _rows(RALEIGH_BASE, RALEIGH_FROZEN)
    gate = REG.classify_change_set(rows, base=RALEIGH_BASE, head=RALEIGH_FROZEN, blockers=blockers)
    return rows, blockers, gate


def _bytes(rev: str, rel: str) -> bytes:
    data = REG.bytes_at(rev, rel)
    assert data is not None, (rev, rel)
    return data


def _patched_bytes(monkeypatch, overrides):
    """``REG.bytes_at`` answering ``overrides[(rev, rel)]`` first, git otherwise."""
    real = REG.bytes_at

    def fake(rev, rel):
        key = (rev, REG._posix(rel))
        if key in overrides:
            return overrides[key]
        return real(rev, rel)

    monkeypatch.setattr(REG, "bytes_at", fake)


# --------------------------------------------------------------------------- #
# The contract: what changed, what did not.
# --------------------------------------------------------------------------- #

class TestTheContract:
    def test_the_composite_class_is_conditional_and_moves_neither_fixed_set(self):
        assert COMPOSITE in RD.CHANGE_CLASSES
        row = RD.VALIDATION_MATRIX[COMPOSITE]
        assert row["full_regression"] == RD.CONDITIONAL
        assert row["assembly"] == RD.NOT_REQUIRED
        assert row["lanes"] == () and row["reverse_dependents"] is False
        assert COMPOSITE not in RD.MANDATORY_FULL_REGRESSION
        assert COMPOSITE not in RD.SAFE_NARROW_CLASSES
        assert set(RD.MANDATORY_FULL_REGRESSION) == {
            RD.AUTHORITY_CHANGE, RD.GENERIC_RUNTIME_CHANGE, RD.SCHEMA_CHANGE,
            RD.ROUTING_SEMANTIC_CHANGE, RD.DEPLOYMENT_CHANGE, RD.UNCLASSIFIED}

    def test_the_committed_matrix_and_contract_carry_the_class(self):
        matrix = json.loads(RD.MATRIX_PATH.read_text(encoding="utf-8-sig"))
        assert COMPOSITE in matrix["change_classes"]
        assert any(r["release_surface"] == COMPOSITE for r in matrix["release_surface_matrix"])
        contract = json.loads(REG.CONTRACT_PATH.read_text(encoding="utf-8-sig"))
        assert contract["composite_change_class"] == COMPOSITE
        assert contract["composite_buckets"] == list(REG.BUCKETS)
        assert contract["original_checks_unchanged"] == list(REG.ORIGINAL_CHECKS)
        assert contract == json.loads(json.dumps(REG.contract_document()))

    def test_none_of_the_original_checks_was_removed_and_four_were_added(self):
        assert set(REG.ORIGINAL_CHECKS) <= set(REG.CHECKS)
        assert set(REG.CHECKS) - set(REG.ORIGINAL_CHECKS) == {
            "market_local_zone", "discovery_config", "registration_input", "identity_resolutions"}
        assert list(REG.CHECKS)[0] == "change_set"

    def test_the_registry_admits_the_transaction_and_never_the_site_runtime(self):
        registry = OWN.load_registry()
        assert registry.transaction_imports
        for module in registry.transaction_imports + registry.transaction_python_modules:
            assert module not in registry.never_transaction_imports
            leaf = module.split(".")[-1]
            assert not leaf.startswith(("assemble_", "generate_")), module
            assert "render" not in leaf and "reader" not in leaf and "polic" not in leaf, module
        assert "scripts.pettripfinder.assemble_production_site" in registry.never_transaction_imports
        assert "tests/pettripfinder/test_composite_fresh_market_001.py" in registry.reachability_scan_exclusions

    def test_a_registry_that_admits_the_assembler_is_malformed(self):
        doc = json.loads(OWN.REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        doc["fresh_market_registration"]["transaction_imports"].append("scripts.pettripfinder.assemble_production_site")
        with pytest.raises(OWN.OwnershipError):
            OWN.parse_registry(doc)
        doc = json.loads(OWN.REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        doc["fresh_market_registration"]["transaction_imports"].append("scripts.pettripfinder.hotel_policy_reader")
        with pytest.raises(OWN.OwnershipError):
            OWN.parse_registry(doc)

    def test_the_registration_zone_is_the_template_instance_and_the_registry_is_not_edited(self):
        registry = OWN.load_registry()
        zone = OWN.registration_zone(MARKET, registry)
        assert zone.execution_zone == OWN.FRESH_MARKET_REGISTRATION
        assert zone.production_runtime_included is False
        assert registry.zone_for(MARKET) is None
        assert "scripts/pettripfinder/raleigh_nc_*.py" in zone.owned_paths
        with pytest.raises(OWN.OwnershipError):
            OWN.registration_zone("Raleigh", registry)
        # a committed SHADOW_UNTIL_REGISTERED zone is used as committed
        assert OWN.registration_zone("toledo-oh", registry).execution_zone == OWN.SHADOW_UNTIL_REGISTERED

    def test_the_runbook_states_the_rule(self):
        text = (REPO_ROOT / "docs" / "PTF_HARDENED_FACTORY_RUNBOOK.md").read_text(encoding="utf-8")
        assert COMPOSITE in text and "MARKET_LOCAL_ACQUISITION" in text and "registration mode" in text


# --------------------------------------------------------------------------- #
# The frozen Raleigh change set (PHASE 12): every path explained.
# --------------------------------------------------------------------------- #

@needs_raleigh
class TestTheFrozenRaleighChangeSet:
    def test_every_one_of_the_42_paths_is_in_exactly_one_bucket(self, frozen):
        rows, blockers, gate = frozen
        detail = gate["result"]["detail"]
        acc = detail["accounting"]
        assert acc["TOTAL_CHANGED_PATHS"] == 42 == len(rows)
        assert acc["sum_equals_total"] is True and acc["sum_of_buckets"] == 42
        assert acc["UNKNOWN_PATHS"] == 0
        assert set(detail["buckets"]) == {r["path"] for r in rows}
        assert sum(len(v) for v in detail["partition"].values()) == 42

    def test_the_forensic_head_adds_three_reports_and_nothing_else_moves(self):
        rows, blockers = _rows(RALEIGH_BASE, RALEIGH_FORENSIC)
        gate = REG.classify_change_set(rows, base=RALEIGH_BASE, head=RALEIGH_FORENSIC, blockers=blockers)
        acc = gate["result"]["detail"]["accounting"]
        assert acc["TOTAL_CHANGED_PATHS"] == 45 and acc["sum_equals_total"] and acc["UNKNOWN_PATHS"] == 0
        assert acc["DERIVED_PATHS"] == 16 and acc["SHARED_BEHAVIOR_PATHS"] == 3

    def test_the_partition_is_the_expected_one(self, frozen):
        rows, blockers, gate = frozen
        part = gate["result"]["detail"]["partition"]
        assert gate["market_id"] == MARKET
        assert blockers == ["launch_packages/pettripfinder/bundle_cache_closure.json"]
        assert sorted(part[REG.BUCKET_SHARED]) == sorted(REJECTED)
        assert part[REG.BUCKET_MARKET_LOCAL] == sorted([
            CONFIG_PATH,
            "scripts/pettripfinder/raleigh_nc_attended_capture_001.py",
            "scripts/pettripfinder/raleigh_nc_authorization_packet_009.py",
            "scripts/pettripfinder/raleigh_nc_brand_inventory_001.py",
            "scripts/pettripfinder/raleigh_nc_census_reconciliation_001.py",
            "scripts/pettripfinder/raleigh_nc_clean_authority_001.py",
            "scripts/pettripfinder/raleigh_nc_co_location_resolutions_003.py",
            "scripts/pettripfinder/raleigh_nc_coverage_reconciliation_006.py",
            "scripts/pettripfinder/raleigh_nc_final_partition_007.py",
            "scripts/pettripfinder/raleigh_nc_geography_001.py",
            "scripts/pettripfinder/raleigh_nc_registration_002.py",
            "scripts/pettripfinder/raleigh_nc_release_contract_004.py",
        ])
        registration = part[REG.BUCKET_REGISTRATION]
        assert INPUT_PATH in registration and RULINGS_PATH in registration and OSM_PATH in registration
        assert "launch_packages/pettripfinder/markets/raleigh-nc.json" in registration
        assert "deploy/netlify/release_contracts/raleigh-nc.json" in registration
        assert len(registration) == 14
        derived = part[REG.BUCKET_DERIVED]
        assert "launch_packages/pettripfinder/hotel_exclusions.json" in derived
        assert all(p.startswith("launch_packages/pettripfinder/markets/reports/raleigh_nc_") for p in derived
                   if p not in ("launch_packages/pettripfinder/hotel_exclusions.json",
                                "launch_packages/pettripfinder/seed_businesses.csv",
                                "launch_packages/pettripfinder/ptf_global_authority_manifest.json"))
        assert len(derived) == 13

    def test_every_rejection_names_a_real_dependency_not_a_name(self, frozen):
        rows, blockers, gate = frozen
        proofs = gate["result"]["detail"]["market_local_proofs"]
        for path, (condition, needle) in REJECTED.items():
            proof = proofs[path]
            assert not proof["passed"] and proof["mode"] == "registration"
            assert condition in proof["failed_conditions"], (path, proof["failed_conditions"])
            assert needle in proof["conditions"][condition]["why"], (path, proof["conditions"][condition]["why"])
        # and every accepted helper passed ALL FIVE conditions, in registration mode
        for path, proof in proofs.items():
            if path not in REJECTED:
                assert proof["passed"] and set(proof["conditions"]) == set(ISO.CONDITIONS), path
                assert all(c["pass"] for c in proof["conditions"].values()), path
                assert proof["mode"] == "registration" and proof["zone"] == MARKET

    def test_the_frozen_set_does_not_narrow_and_says_why(self, frozen):
        rows, blockers, gate = frozen
        assert gate["result"]["pass"] is False
        problems = gate["result"]["detail"]["problems"]
        assert any("market_state_pin" in p for p in problems)          # the block was never stated
        assert sum(1 for p in problems if "is not market-local" in p) == 3
        assert gate["result"]["detail"]["change_class"] == COMPOSITE   # the candidate class, had every proof passed

    def test_the_discovery_config_is_field_validated(self, frozen):
        rows, blockers, gate = frozen
        result = REG.check_discovery_config(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is True, result["why"]
        assert result["detail"]["market_config"]["market_id"] == MARKET
        assert result["detail"]["registry_row"]["markets"] == [MARKET]
        assert result["detail"]["registry_row"]["existing_rows_identical"] == 6

    def test_the_registration_input_is_typed(self, frozen):
        rows, blockers, gate = frozen
        result = REG.check_registration_input(rows, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is True, result["why"]
        assert result["detail"]["schema"] == "ptf-market-proposed-authority/1.0"
        assert result["detail"]["pet_friendly"] == 63 and result["detail"]["verified_no_pets"] == 23
        assert result["detail"]["in_change_set"] is True

    def test_the_identity_ruling_is_field_validated(self, frozen):
        rows, blockers, gate = frozen
        result = REG.check_identity_resolutions(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is True, result["why"]
        assert result["detail"]["head_rulings"] == result["detail"]["base_rulings"] + 1
        assert len(result["detail"]["added"]) == 1 and len(result["detail"]["added"][0]["identities"]) == 2

    def test_the_registration_artifacts_pass_their_existing_proof(self):
        participation = REG.check_participation(_bytes(RALEIGH_BASE, REG.PARTICIPATION_PATH),
                                                _bytes(RALEIGH_FROZEN, REG.PARTICIPATION_PATH), MARKET)
        assert participation["pass"] is True, participation["why"]
        closure = REG.check_build_closure(_bytes(RALEIGH_BASE, REG.CLOSURE_PATH), _bytes(RALEIGH_FROZEN, REG.CLOSURE_PATH),
                                          MARKET, exists=lambda rel: REG.bytes_at(RALEIGH_FROZEN, rel) is not None)
        assert closure["pass"] is True, closure["why"]

    def test_the_forensic_classification_is_reproduced_and_explained(self):
        """The forensic report's four disqualifying categories now each have a bucket."""
        rows, blockers = _rows(RALEIGH_BASE, RALEIGH_FORENSIC)
        gate = REG.classify_change_set(rows, base=RALEIGH_BASE, head=RALEIGH_FORENSIC, blockers=blockers)
        buckets = gate["result"]["detail"]["buckets"]
        assert buckets[INPUT_PATH] == REG.BUCKET_REGISTRATION
        assert buckets[RULINGS_PATH] == REG.BUCKET_REGISTRATION
        assert buckets[OSM_PATH] == REG.BUCKET_REGISTRATION
        assert buckets[CONFIG_PATH] == REG.BUCKET_MARKET_LOCAL
        assert buckets["scripts/pettripfinder/raleigh_nc_geography_001.py"] == REG.BUCKET_MARKET_LOCAL
        assert REG.BUCKET_UNKNOWN not in buckets.values()


# --------------------------------------------------------------------------- #
# The isolation proof in registration mode, on a scratch repository.
# --------------------------------------------------------------------------- #

HELPER = '''
    import argparse
    import json
    import os
    from scripts.pettripfinder.site_data import normalize_name
    _DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
    OUT = os.path.join(REPORTS, "zed_zz_geography_001.json")

    def main(argv=None):
        p = argparse.ArgumentParser()
        p.add_argument("--out", default=OUT)
        args = p.parse_args(argv)
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"name": normalize_name("x")}, fh)
        return 0
'''


@pytest.fixture()
def scratch(tmp_path, monkeypatch):
    """A git repository laid out like the package; zed-zz is ABSENT at the
    base commit and registered in the worktree unless a test says otherwise."""
    git_root = tmp_path / "root"
    pkg = git_root / "atlas-dashboard"
    (pkg / "scripts" / "pettripfinder" / "discovery" / "config").mkdir(parents=True)
    (pkg / "launch_packages" / "pettripfinder" / "markets" / "reports").mkdir(parents=True)
    (pkg / "launch_packages" / "pettripfinder" / "identity_census").mkdir(parents=True)
    (pkg / "tests" / "pettripfinder").mkdir(parents=True)
    (pkg / "deploy" / "netlify" / "release_contracts").mkdir(parents=True)
    (pkg / "deploy" / "netlify" / "launch_participation.json").write_text('{"markets": []}')
    (pkg / "scripts" / "pettripfinder" / "site_data.py").write_text("def normalize_name(x):\n    return x\n")
    subprocess.run(["git", "init", "-q"], cwd=str(git_root), check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=str(git_root), check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(git_root), check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(git_root), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=str(git_root), check=True)
    (pkg / "launch_packages" / "pettripfinder" / "markets" / "zed-zz.json").write_text("{}")
    monkeypatch.setattr(ISO, "REPO_ROOT", pkg)
    monkeypatch.setattr(OWN, "REPO_ROOT", pkg)
    ISO.clear_memo()
    return git_root, pkg, OWN.load_registry()


def _write(root: Path, rel: str, source: str) -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    ISO.clear_memo()
    return rel


def _ctx(*proven):
    return {"market_id": "zed-zz", "proven_paths": list(proven)}


class TestRegistrationModeIsolation:
    def test_case_01_a_fresh_market_helper_passes_in_registration_mode_and_only_there(self, scratch):
        root, pkg, registry = scratch
        rel = _write(pkg, "scripts/pettripfinder/zed_zz_geography_001.py", HELPER)
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert proof["passed"], proof["conditions"]
        assert proof["mode"] == "registration" and proof["zone"] == "zed-zz"
        assert proof["execution_zone"] == OWN.FRESH_MARKET_REGISTRATION
        shadow = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not shadow["passed"] and shadow["zone"] is None                       # no zone row: unowned
        assert shadow["conditions"]["namespace"]["why"] == "no zone owns this path"

    def test_case_02_a_helper_that_imports_the_assembler_is_rejected(self, scratch):
        root, pkg, registry = scratch
        rel = _write(pkg, "scripts/pettripfinder/zed_zz_participation_001.py", HELPER + '''
    def verify():
        from scripts.pettripfinder.assemble_production_site import market_eligibility
        return market_eligibility
''')
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert not proof["passed"] and proof["failed_conditions"] == ["imports"]
        assert "assemble_production_site" in proof["conditions"]["imports"]["why"]

    def test_case_02b_a_transaction_import_is_admitted_only_in_registration_mode(self, scratch):
        root, pkg, registry = scratch
        rel = _write(pkg, "scripts/pettripfinder/zed_zz_release_contract_001.py", HELPER + '''
    from scripts.pettripfinder import release_contracts as RC
''')
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert proof["passed"], proof["conditions"]
        assert any("registration-transaction module" in i for i in proof["conditions"]["imports"]["imports"])
        doc = json.loads(OWN.REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        doc["zones"].append({"market_id": "zed-zz", "execution_zone": "SHADOW",
                             "production_runtime_included": "NO", "use_template": True})
        shadow_registry = OWN.parse_registry(doc)
        (pkg / "launch_packages" / "pettripfinder" / "markets" / "zed-zz.json").unlink()
        ISO.clear_memo()
        shadow = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=shadow_registry)
        assert not shadow["passed"] and "imports" in shadow["failed_conditions"]

    def test_case_03_a_helper_reverse_imported_by_shared_runtime_is_rejected(self, scratch):
        root, pkg, registry = scratch
        rel = _write(pkg, "scripts/pettripfinder/zed_zz_geography_001.py", HELPER)
        _write(pkg, "scripts/pettripfinder/site_data.py",
               "from scripts.pettripfinder.zed_zz_geography_001 import main\ndef normalize_name(x):\n    return x\n")
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert not proof["passed"] and proof["failed_conditions"] == ["reachability"]
        assert "site_data.py" in proof["conditions"]["reachability"]["why"]

    def test_case_04_a_write_to_another_market_is_rejected_and_a_proven_registration_write_is_not(self, scratch):
        root, pkg, registry = scratch
        bad = _write(pkg, "scripts/pettripfinder/zed_zz_census_001.py", HELPER + '''
    def promote():
        target = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "authority", "other-xx", "seed_businesses.csv")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("")
''')
        ctx = _ctx("launch_packages/pettripfinder/identity_census/zed-zz.json")
        proof = ISO.prove(bad, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=ctx)
        assert not proof["passed"] and proof["failed_conditions"] == ["writes"]
        assert "other-xx" in proof["conditions"]["writes"]["why"]
        good = _write(pkg, "scripts/pettripfinder/zed_zz_census_002.py", HELPER + '''
    def census():
        target = os.path.join(_DASH, "launch_packages", "pettripfinder", "identity_census", "zed-zz.json")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("{}")
''')
        proof = ISO.prove(good, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=ctx)
        assert proof["passed"], proof["conditions"]["writes"]
        # the same write without the path in the proven set is outside the zone
        proof = ISO.prove(good, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert not proof["passed"] and proof["failed_conditions"] == ["writes"]

    def test_a_bare_root_with_a_dynamic_tail_is_never_a_proven_write(self, scratch):
        root, pkg, registry = scratch
        rel = _write(pkg, "scripts/pettripfinder/zed_zz_dyn_001.py", HELPER + '''
    def write(name):
        target = os.path.join(_DASH, "launch_packages", "pettripfinder", name)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("{}")
''')
        ctx = _ctx("launch_packages/pettripfinder/zed_zz_proposed_authority_001.json")
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=ctx)
        assert not proof["passed"] and proof["failed_conditions"] == ["writes"]

    def test_a_market_registered_at_the_base_fails_condition_five_in_registration_mode(self, scratch, tmp_path):
        root, pkg, registry = scratch
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "zed-zz registered"], cwd=str(root), check=True)
        ISO.clear_memo()
        rel = _write(pkg, "scripts/pettripfinder/zed_zz_geography_001.py", HELPER)
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert not proof["passed"] and proof["failed_conditions"] == ["registration"]
        assert "already registered at the base" in proof["conditions"]["registration"]["why"]

    def test_a_helper_of_another_market_fails_namespace(self, scratch):
        root, pkg, registry = scratch
        rel = _write(pkg, "scripts/pettripfinder/other_xx_geography_001.py", HELPER)
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert not proof["passed"] and "namespace" in proof["failed_conditions"]
        assert "not owned by the registering market" in proof["conditions"]["namespace"]["why"]

    def test_the_never_local_fence_still_stands_in_registration_mode(self, scratch):
        root, pkg, registry = scratch
        rel = _write(pkg, "scripts/pettripfinder/discovery/config/osm_extracts.json", "{}")
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="M", registry=registry, registration=_ctx())
        assert not proof["passed"] and proof["conditions"]["namespace"]["why"] == "inside the never_local fence"
        rel = _write(pkg, "scripts/pettripfinder/zed_zz_identity_routing.py", "x = 1\n")
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert proof["conditions"]["namespace"]["pass"]   # a zone name, not the fence

    def test_a_subprocess_of_the_assembler_is_rejected_and_of_the_registration_cli_is_not(self, scratch):
        root, pkg, registry = scratch
        bad = _write(pkg, "scripts/pettripfinder/zed_zz_candidate_001.py", HELPER + '''
    import subprocess, sys
    def build():
        subprocess.run([sys.executable, "-m", "scripts.pettripfinder.assemble_production_site"])
''')
        proof = ISO.prove(bad, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert not proof["passed"] and proof["failed_conditions"] == ["reachability"]
        good = _write(pkg, "scripts/pettripfinder/zed_zz_register_001.py", HELPER + '''
    import subprocess, sys
    def register():
        subprocess.run([sys.executable, "-m", "scripts.pettripfinder.market_registration_cli", "--market", "zed-zz"])
''')
        proof = ISO.prove(good, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration=_ctx())
        assert proof["passed"], proof["conditions"]["reachability"]

    def test_a_registration_context_without_a_market_fails_every_condition(self, scratch):
        root, pkg, registry = scratch
        rel = _write(pkg, "scripts/pettripfinder/zed_zz_geography_001.py", HELPER)
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry, registration={"proven_paths": []})
        assert not proof["passed"] and set(proof["failed_conditions"]) == set(ISO.CONDITIONS)


# --------------------------------------------------------------------------- #
# The partition on the real repository: shared, unknown, blockers.
# --------------------------------------------------------------------------- #

@needs_raleigh
class TestThePartition:
    def _gate(self, rows, blockers):
        return REG.classify_change_set(rows, base=RALEIGH_BASE, head=RALEIGH_FROZEN, blockers=blockers)

    def test_case_17_an_assembler_change_lands_in_shared_and_ends_the_narrowing(self, frozen):
        rows, blockers, _ = frozen
        extra = OrderedDict((("path", "scripts/pettripfinder/assemble_production_site.py"), ("status", "M"),
                             ("classes", ["GENERIC_RUNTIME_CHANGE", "DEPLOYMENT_CHANGE"]), ("rule", "glob")))
        gate = self._gate(rows + [extra], blockers)
        detail = gate["result"]["detail"]
        assert detail["buckets"]["scripts/pettripfinder/assemble_production_site.py"] == REG.BUCKET_SHARED
        assert detail["accounting"]["TOTAL_CHANGED_PATHS"] == 43 and detail["accounting"]["sum_equals_total"]
        assert gate["result"]["pass"] is False

    def test_case_16_a_build_module_change_is_shared(self, frozen):
        rows, blockers, _ = frozen
        extra = OrderedDict((("path", "scripts/pettripfinder/build_global_authority.py"), ("status", "M"),
                             ("classes", ["GENERIC_RUNTIME_CHANGE"]), ("rule", "prefix")))
        gate = self._gate(rows + [extra], blockers)
        assert gate["result"]["detail"]["buckets"]["scripts/pettripfinder/build_global_authority.py"] == REG.BUCKET_SHARED

    @pytest.mark.parametrize("blocker", [
        "scripts/pettripfinder/regression_delta.py",            # case 18: the classifier
        "scripts/pettripfinder/registration_data_only.py",      # case 18: the proof
        "conftest.py",                                          # case 19: test infrastructure
        "launch_packages/pettripfinder/market_local_ownership.json",  # the registry
    ])
    def test_cases_18_19_a_foreign_blocker_ends_the_narrowing_before_any_proof(self, frozen, blocker):
        rows, blockers, _ = frozen
        extra = OrderedDict((("path", blocker), ("status", "M"), ("classes", ["GENERIC_RUNTIME_CHANGE"]), ("rule", "glob")))
        gate = self._gate(rows + [extra], blockers + [blocker])
        assert gate["result"]["pass"] is False
        assert "does not own" in gate["result"]["why"]
        assert gate["roles"] == OrderedDict()

    def test_case_20_one_unknown_path_is_unknown_and_ends_the_narrowing(self, frozen):
        rows, blockers, _ = frozen
        extra = OrderedDict((("path", "launch_packages/pettripfinder/raleigh_nc_mystery_ledger.json"), ("status", "A"),
                             ("classes", ["UNCLASSIFIED"]), ("rule", "no rule")))
        gate = self._gate(rows + [extra], blockers)
        detail = gate["result"]["detail"]
        assert detail["accounting"]["UNKNOWN_PATHS"] == 1
        assert detail["buckets"]["launch_packages/pettripfinder/raleigh_nc_mystery_ledger.json"] == REG.BUCKET_UNKNOWN
        assert gate["result"]["pass"] is False

    def test_case_21_a_required_output_missing_from_the_accounting_fails(self, frozen):
        rows, blockers, _ = frozen
        without = [r for r in rows if r["path"] != "deploy/netlify/release_contracts/raleigh-nc.json"]
        gate = self._gate(without, blockers)
        assert any("release_contract" in p for p in gate["result"]["detail"]["problems"])
        assert gate["result"]["detail"]["accounting"]["TOTAL_CHANGED_PATHS"] == 41

    def test_a_second_market_or_another_markets_shard_is_never_composite(self, frozen):
        rows, blockers, _ = frozen
        extra = OrderedDict((("path", "launch_packages/pettripfinder/markets/authority/charlotte-nc/seed_businesses.csv"),
                             ("status", "M"), ("classes", ["AUTHORITY_CHANGE"]), ("rule", "prefix")))
        gate = self._gate(rows + [extra], blockers)
        assert gate["result"]["detail"]["buckets"][extra["path"]] == REG.BUCKET_UNKNOWN
        assert gate["result"]["pass"] is False

    def test_another_markets_helper_in_the_set_is_shared(self, frozen):
        rows, blockers, _ = frozen
        extra = OrderedDict((("path", "scripts/pettripfinder/charlotte_nc_registration_002.py"), ("status", "M"),
                             ("classes", ["GENERIC_RUNTIME_CHANGE"]), ("rule", "prefix")))
        gate = self._gate(rows + [extra], blockers)
        assert gate["result"]["detail"]["buckets"][extra["path"]] == REG.BUCKET_SHARED

    def test_a_bare_re_registration_keeps_the_original_class(self):
        """The Charlotte replay shape: no helper, no typed input -> NEW_MARKET_REGISTRATION_DATA_ONLY."""
        rows = []
        for rel, status in (("deploy/netlify/launch_participation.json", "M"),
                            ("deploy/netlify/release_contracts/charlotte-nc.json", "A"),
                            ("launch_packages/pettripfinder/bundle_cache_closure.json", "M"),
                            ("launch_packages/pettripfinder/markets/charlotte-nc.json", "A"),
                            ("tests/pettripfinder/pins/market_state.json", "M"),
                            ("launch_packages/pettripfinder/markets/authority/charlotte-nc/seed_businesses.csv", "A")):
            classes, rule = RD.classify_path(rel)
            rows.append(OrderedDict((("path", rel), ("status", status), ("classes", list(classes)), ("rule", rule))))
        gate = REG.classify_change_set(rows, base="11373275", head=RD.WORKTREE,
                                       blockers=["launch_packages/pettripfinder/bundle_cache_closure.json",
                                                 "tests/pettripfinder/pins/market_state.json"])
        detail = gate["result"]["detail"]
        assert detail["change_class"] == REG.CLASS_REGISTRATION
        assert detail["accounting"]["MARKET_LOCAL_ACQUISITION_PATHS"] == 0


# --------------------------------------------------------------------------- #
# Discovery config (cases 5, 6, 7).
# --------------------------------------------------------------------------- #

@needs_raleigh
class TestDiscoveryConfig:
    @pytest.fixture()
    def rows(self, frozen):
        return frozen[0]

    def _head_registry(self, mutate):
        doc = json.loads(_bytes(RALEIGH_FROZEN, OSM_PATH).decode("utf-8-sig"), object_pairs_hook=OrderedDict)
        mutate(doc)
        return json.dumps(doc, indent=1, ensure_ascii=False).encode("utf-8")

    def test_case_06_one_additive_row_for_the_new_market_is_narrow(self, rows):
        assert REG.check_discovery_config(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)["pass"] is True

    def test_case_05_a_changed_existing_row_is_broad(self, rows, monkeypatch):
        def mutate(doc):
            doc["extracts"][0]["url"] = doc["extracts"][0]["url"].replace("latest", "250101")
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, OSM_PATH): self._head_registry(mutate)})
        result = REG.check_discovery_config(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "existing registry row" in result["why"]

    def test_case_05b_a_removed_or_second_row_is_broad(self, rows, monkeypatch):
        def mutate(doc):
            doc["extracts"].append(dict(doc["extracts"][-1], extract_id="geofabrik-x-second", markets=[MARKET],
                                        index_path="data/osm_extracts/x.second.index.json"))
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, OSM_PATH): self._head_registry(mutate)})
        result = REG.check_discovery_config(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "exactly one row" in result["why"]

    def test_a_row_for_another_market_or_a_reused_index_is_broad(self, rows, monkeypatch):
        def other(doc):
            doc["extracts"][-1]["markets"] = ["charlotte-nc"]
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, OSM_PATH): self._head_registry(other)})
        result = REG.check_discovery_config(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "not exactly" in result["why"]

        def reuse(doc):
            doc["extracts"][-1]["index_path"] = doc["extracts"][0]["index_path"]
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, OSM_PATH): self._head_registry(reuse)})
        result = REG.check_discovery_config(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "index_path" in result["why"]

    def test_an_unknown_top_level_field_or_a_semantics_change_is_broad(self, rows, monkeypatch):
        def mutate(doc):
            doc["fallback_policy"] = "answer from any extract"
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, OSM_PATH): self._head_registry(mutate)})
        result = REG.check_discovery_config(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "registry.fallback_policy changed" in result["why"]

    def test_case_07_a_discovery_algorithm_change_is_broad(self, rows):
        extra = OrderedDict((("path", "scripts/pettripfinder/discovery/runner.py"), ("status", "M"),
                             ("classes", ["GENERIC_RUNTIME_CHANGE", "ROUTING_SEMANTIC_CHANGE"]), ("rule", "prefix")))
        result = REG.check_discovery_config(rows + [extra], RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "discovery code or provider configuration changed" in result["why"]
        extra["path"] = "scripts/pettripfinder/discovery/config/provider_terms.json"
        result = REG.check_discovery_config(rows + [extra], RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False

    def test_a_market_config_for_another_market_id_is_broad(self, rows, monkeypatch):
        doc = json.loads(_bytes(RALEIGH_FROZEN, CONFIG_PATH).decode("utf-8-sig"), object_pairs_hook=OrderedDict)
        doc["market_id"] = "charlotte-nc"
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, CONFIG_PATH): json.dumps(doc).encode("utf-8")})
        result = REG.check_discovery_config(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "market_id" in result["why"]


# --------------------------------------------------------------------------- #
# The registration input (cases 8, 9).
# --------------------------------------------------------------------------- #

@needs_raleigh
class TestRegistrationInput:
    @pytest.fixture()
    def rows(self, frozen):
        return frozen[0]

    def _head_input(self, mutate):
        doc = json.loads(_bytes(RALEIGH_FROZEN, INPUT_PATH).decode("utf-8-sig"), object_pairs_hook=OrderedDict)
        mutate(doc)
        return json.dumps(doc, indent=1, ensure_ascii=False).encode("utf-8")

    def test_the_frozen_input_is_typed_and_bound(self, rows):
        assert REG.check_registration_input(rows, RALEIGH_FROZEN, MARKET)["pass"] is True

    def test_case_08_a_schema_change_is_refused_by_the_clis_own_loader(self, rows, monkeypatch):
        def mutate(doc):
            doc["schema"] = "ptf-market-proposed-authority/2.0"
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, INPUT_PATH): self._head_input(mutate)})
        result = REG.check_registration_input(rows, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "loader refuses" in result["why"]

    def test_case_08b_the_readers_own_change_is_broad(self, rows):
        extra = OrderedDict((("path", "scripts/pettripfinder/market_registration_cli.py"), ("status", "M"),
                             ("classes", ["GENERIC_RUNTIME_CHANGE"]), ("rule", "prefix")))
        result = REG.check_registration_input(rows + [extra], RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "reader/writer changed" in result["why"]

    def test_case_09_an_input_that_alters_existing_authority_fails(self, rows, monkeypatch):
        def mutate(doc):
            doc["market_id"] = "charlotte-nc"
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, INPUT_PATH): self._head_input(mutate)})
        result = REG.check_registration_input(rows, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "market_id" in result["why"]
        extra = OrderedDict((("path", "launch_packages/pettripfinder/charlotte_nc_proposed_authority_002.json"),
                             ("status", "M"), ("classes", ["UNCLASSIFIED"]), ("rule", "no rule")))
        result = REG.check_registration_input(rows + [extra], RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "another market's registration input" in result["why"]

    def test_counts_that_do_not_reconcile_or_an_identity_outside_the_census_fail(self, rows, monkeypatch):
        def counts(doc):
            doc["pet_friendly_count"] = doc["pet_friendly_count"] + 1
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, INPUT_PATH): self._head_input(counts)})
        result = REG.check_registration_input(rows, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "pet_friendly_count" in result["why"]

        def stranger(doc):
            doc["pet_friendly"][0]["identity_key"] = "nowhere|inn|00000"
            doc["pet_friendly"][0]["canonical_name"] = "Nowhere Inn"
            doc["pet_friendly"][0]["normalized_name"] = "nowhere inn"
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, INPUT_PATH): self._head_input(stranger)})
        result = REG.check_registration_input(rows, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and ("not in the census" in result["why"] or "disagrees" in result["why"])

    def test_an_edited_rather_than_created_input_is_not_a_registration_write(self, rows):
        edited = [dict(r, status="M") if r["path"] == INPUT_PATH else r for r in rows]
        result = REG.check_registration_input(edited, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "created, never edited" in result["why"]

    def test_a_missing_input_is_a_failure_never_a_pass(self, monkeypatch):
        rows = []
        monkeypatch.setattr(REG, "_newest_input_at", lambda head, market_id: None)
        result = REG.check_registration_input(rows, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "no registration input" in result["why"]


# --------------------------------------------------------------------------- #
# Identity resolutions (cases 10, 11, 12).
# --------------------------------------------------------------------------- #

@needs_raleigh
class TestIdentityResolutions:
    @pytest.fixture()
    def rows(self, frozen):
        return frozen[0]

    def _head_rulings(self, mutate):
        doc = json.loads(_bytes(RALEIGH_FROZEN, RULINGS_PATH).decode("utf-8-sig"), object_pairs_hook=OrderedDict)
        mutate(doc)
        return json.dumps(doc, indent=1, ensure_ascii=False).encode("utf-8")

    def test_case_10_the_frozen_additive_ruling_is_narrow(self, rows):
        assert REG.check_identity_resolutions(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)["pass"] is True

    def test_no_ruling_in_the_set_is_a_pass(self):
        result = REG.check_identity_resolutions([], RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is True and result["detail"]["in_change_set"] is False

    def test_case_11_an_edited_existing_ruling_is_broad(self, rows, monkeypatch):
        def mutate(doc):
            doc["resolutions"][0]["evidence"] = doc["resolutions"][0]["evidence"] + " (edited)"
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, RULINGS_PATH): self._head_rulings(mutate)})
        result = REG.check_identity_resolutions(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "pre-existing ruling changed" in result["why"]

    def test_a_ruling_for_another_market_or_a_tampered_hash_fails(self, rows, monkeypatch):
        def other(doc):
            doc["resolutions"][-1]["market_id"] = "charlotte-nc"
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, RULINGS_PATH): self._head_rulings(other)})
        result = REG.check_identity_resolutions(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "belongs to" in result["why"]

        def tamper(doc):
            doc["resolutions"][-1]["reviewed_at"] = "2020-01-01"
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, RULINGS_PATH): self._head_rulings(tamper)})
        result = REG.check_identity_resolutions(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "resolution_hash" in result["why"]

    def test_case_12_a_ruling_that_creates_a_collision_fails(self, rows, monkeypatch):
        from scripts.pettripfinder import publication_guard as PG

        def duplicate_url(doc):
            row = doc["resolutions"][-1]
            row["identities"][1]["official_url"] = row["identities"][0]["official_url"]
            row["resolution_hash"] = PG.resolution_hash(row)
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, RULINGS_PATH): self._head_rulings(duplicate_url)})
        result = REG.check_identity_resolutions(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and ("DUPLICATE" in result["why"] or "different official URL" in result["why"])

        def stranger(doc):
            row = doc["resolutions"][-1]
            row["identities"][1]["canonical_name"] = "Nowhere Inn Brier Creek"
            row["resolution_hash"] = PG.resolution_hash(row)
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, RULINGS_PATH): self._head_rulings(stranger)})
        result = REG.check_identity_resolutions(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "not an identity of" in result["why"]

        def slug_collision(doc):
            row = doc["resolutions"][-1]
            row["identities"][0]["slug"] = doc["resolutions"][0]["identities"][0]["slug"]
            row["resolution_hash"] = PG.resolution_hash(row)
        _patched_bytes(monkeypatch, {(RALEIGH_FROZEN, RULINGS_PATH): self._head_rulings(slug_collision)})
        result = REG.check_identity_resolutions(rows, RALEIGH_BASE, RALEIGH_FROZEN, MARKET)
        assert result["pass"] is False and "claimed by two different identities" in result["why"]


# --------------------------------------------------------------------------- #
# The replay receipts (PHASES 14 and 16): documentary, machine-checked.
# --------------------------------------------------------------------------- #

RECEIPTS = {
    "focused_benchmark": REPORTS / "raleigh_nc_true_first_registration_replay_001_focused_benchmark.json",
    "true_first_replay": REPORTS / "raleigh_nc_true_first_registration_replay_001.json",
}


class TestTheReplayReceipts:
    @pytest.mark.parametrize("label", sorted(RECEIPTS))
    def test_a_committed_replay_receipt_passes_every_criterion(self, label):
        path = RECEIPTS[label]
        if not path.is_file():
            pytest.skip("%s not committed yet" % path.name)
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        assert doc["schema"] == "ptf-true-first-registration-replay/1.0"
        assert doc["label"] == label
        assert doc["TRUE_FIRST_REGISTRATION_REPLAY"] == "PASS", doc["failed_criteria"]
        assert all(doc["criteria"].values())
        assert doc["composite_proof"]["CHANGE_CLASS"] == COMPOSITE
        acc = doc["composite_proof"]["accounting"]
        assert acc["sum_equals_total"] and acc["UNKNOWN_PATHS"] == 0 and acc["SHARED_BEHAVIOR_PATHS"] == 0
        assert acc["TOTAL_CHANGED_PATHS"] == doc["regression_v2"]["changed_file_count"]
        assert doc["timings"]["REGISTRATION_TO_AUTHORIZATION_READY_SECONDS"] <= 300
        assert doc["shared_code_freeze"]["SHARED_CODE_CHANGED"] == "NO"
        assert doc["regression_v2"]["FULL_REGRESSION_REQUIRED"] == "NO"
        assert doc["regression_v2"]["REMOTE_BROAD_JOBS_REQUIRED"] == 0
        assert doc["lane"]["UNCHANGED_MARKETS_REBUILT"] == 0
        assert doc["lane"]["fast_lane_receipt"]["rules_passed"] == 15
        assert doc["authorization_readiness_packet"]["status"] == "AUTHORIZATION_READY"
        assert doc["authorization_readiness_packet"]["authorized_by"] is None
