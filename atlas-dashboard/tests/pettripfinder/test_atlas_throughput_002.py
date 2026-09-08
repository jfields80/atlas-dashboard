# -*- coding: utf-8 -*-
"""ATLAS-THROUGHPUT-002 -- market-local ownership, the five-condition
isolation proof, the MARKET_LOCAL_TOOLING class, the demo-media lane role,
session-local assembly reuse, and the production/promotion safety freeze.

Every classifier case below is decided from ACTUAL dependency evidence -- a
synthetic module's real imports and real write targets, or a real branch's
real bytes read through git -- never from a name. Nothing here builds a
market site or runs the broad suite; the one-time migration audit is the
broad validation of this order.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

from scripts.pettripfinder import assembly_session_cache as ASC
from scripts.pettripfinder import market_local_isolation as ISO
from scripts.pettripfinder import market_local_ownership as OWN
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import regression_lanes as RL

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "reports"

NASHVILLE_HELPER = "scripts/pettripfinder/nashville_tn_shadow_market_001.py"
NASHVILLE_ROUTING = "scripts/pettripfinder/nashville_tn_routing_001.py"
CHATTANOOGA_HELPER = "scripts/pettripfinder/chattanooga_tn_shadow_market_001.py"
LEXINGTON_HELPER = "scripts/pettripfinder/lexington_ky_identity_key_repair_002.py"

#: Real branch heads read through git (never checked out). Skipped when the
#: commit is not in this clone.
NASHVILLE = ("d335c50", "4f3dd7b")
CHATTANOOGA = ("d335c50", "4e058a3")
LEXINGTON = ("2163c4e", "f1e0435")
TOLEDO_001 = ("2163c4e", "133b937")
TOLEDO_002 = ("2163c4e", "d335c50")


def _has_commit(sha: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"],
                          cwd=str(REPO_ROOT), capture_output=True).returncode == 0


needs_branches = pytest.mark.skipif(
    not all(_has_commit(s) for pair in (NASHVILLE, CHATTANOOGA, LEXINGTON, TOLEDO_001, TOLEDO_002) for s in pair),
    reason="the market branches are not in this clone")


# --------------------------------------------------------------------------- #
# Ownership registry.
# --------------------------------------------------------------------------- #

class TestOwnershipRegistry:
    def test_the_committed_registry_parses_and_names_the_shadow_markets(self):
        reg = OWN.load_registry()
        ids = {z.market_id for z in reg.zones}
        assert {"nashville-tn", "chattanooga-tn", "lexington-ky", "toledo-oh"} <= ids
        for zone in reg.zones:
            assert not zone.production_runtime_included
            assert zone.owned_paths and zone.allowed_write_roots and zone.owned_tests

    def test_a_zone_owns_only_paths_that_carry_its_own_id(self):
        reg = OWN.load_registry()
        for zone in reg.zones:
            for pattern in zone.owned_paths + zone.allowed_write_roots:
                assert zone.market_id in pattern or zone.market_us in pattern \
                    or zone.market_id.upper() in pattern, (zone.market_id, pattern)

    def test_shared_runtime_and_authority_are_never_local(self):
        reg = OWN.load_registry()
        for path in ("scripts/pettripfinder/assemble_production_site.py",
                     "scripts/pettripfinder/contracts/policy_schema.py",
                     "scripts/pettripfinder/acquisition/ladder.py",
                     "scripts/pettripfinder/discovery/runner.py",
                     "scripts/pettripfinder/discovery/config/osm_extracts.json",
                     "scripts/pettripfinder/regression_delta.py",
                     "launch_packages/pettripfinder/markets/nashville-tn.json",
                     "launch_packages/pettripfinder/markets/authority/toledo-oh/hotel_exclusions.json",
                     "launch_packages/pettripfinder/hotel_policy_facts_toledo-oh.json",
                     "launch_packages/pettripfinder/toledo_oh_final_partition_001.json",
                     "launch_packages/pettripfinder/market_local_ownership.json",
                     "deploy/netlify/release_contracts/toledo-oh.json",
                     "tests/pettripfinder/pins/market_state.json", "conftest.py", "pytest.ini"):
            zone, why = OWN.owner_of(path, reg)
            assert zone is None, (path, why)

    def test_owner_of_names_exactly_one_zone_for_a_helper(self):
        zone, why = OWN.owner_of(NASHVILLE_HELPER)
        assert zone is not None and zone.market_id == "nashville-tn"
        zone, why = OWN.owner_of("launch_packages/pettripfinder/identity_census_proposed/chattanooga-tn.json")
        assert zone is not None and zone.market_id == "chattanooga-tn"
        assert OWN.owner_of("scripts/pettripfinder/site_data.py")[0] is None

    def test_a_malformed_registry_fails_closed(self):
        with pytest.raises(OWN.OwnershipError):
            OWN.load_registry(text=json.dumps({"schema": "wrong"}))
        doc = json.loads(OWN.REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        doc["zones"].append(dict(doc["zones"][0], market_id="nashville-tn"))   # declared twice
        with pytest.raises(OWN.OwnershipError):
            OWN.load_registry(text=json.dumps(doc))
        doc = json.loads(OWN.REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        doc["zones"][0] = dict(doc["zones"][0], use_template=False,
                               owned_paths=["scripts/pettripfinder/*.py"],   # no market id
                               allowed_write_roots=[], allowed_read_roots=[], owned_tests=[])
        with pytest.raises(OWN.OwnershipError):
            OWN.load_registry(text=json.dumps(doc))

    def test_two_zones_claiming_one_path_is_no_owner(self):
        doc = json.loads(OWN.REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        doc["zones"].append({"market_id": "nash-tn", "execution_zone": "SHADOW",
                             "production_runtime_included": "NO", "use_template": False,
                             "owned_paths": ["scripts/pettripfinder/nash*_tn_*.py", "scripts/pettripfinder/nashville_tn_*.py"],
                             "allowed_write_roots": ["data/nash-tn/"], "allowed_read_roots": [],
                             "owned_tests": ["tests/pettripfinder/test_nash_tn_*.py"]})
        # the second pattern names nashville, which is not this zone's id -> malformed
        with pytest.raises(OWN.OwnershipError):
            OWN.load_registry(text=json.dumps(doc))


# --------------------------------------------------------------------------- #
# The proof on synthetic modules: every condition can fail, and each failure
# names its reason.
# --------------------------------------------------------------------------- #

@pytest.fixture()
def scratch_zone(tmp_path, monkeypatch):
    """A registry with one zone 'zed-zz' whose helpers live in tmp_path, plus
    the isolation module pointed at that tree as the worktree."""
    doc = json.loads(OWN.REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    doc["zones"] = [{"market_id": "zed-zz", "execution_zone": "SHADOW",
                     "production_runtime_included": "NO", "use_template": True}]
    registry = OWN.parse_registry(doc)
    root = tmp_path / "repo"
    (root / "scripts" / "pettripfinder").mkdir(parents=True)
    (root / "launch_packages" / "pettripfinder" / "markets" / "reports").mkdir(parents=True)
    (root / "tests" / "pettripfinder").mkdir(parents=True)
    (root / "deploy" / "netlify").mkdir(parents=True)
    (root / "deploy" / "netlify" / "launch_participation.json").write_text('{"markets": []}')
    monkeypatch.setattr(ISO, "REPO_ROOT", root)
    monkeypatch.setattr(OWN, "REPO_ROOT", root)
    ISO.clear_memo()
    return root, registry


def _write(root: Path, rel: str, source: str) -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return rel


ISOLATED_HELPER = '''
    import argparse
    import json
    import os
    from scripts.pettripfinder.site_data import normalize_name
    _DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
    OUT = os.path.join(REPORTS, "zed_zz_routing_001.json")

    def main(argv=None):
        p = argparse.ArgumentParser()
        p.add_argument("--out", default=OUT)
        args = p.parse_args(argv)
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"name": normalize_name("x")}, fh)
        for name, doc in (("zed_zz_a_001.json", {}), ("zed_zz_b_001.json", {})):
            path = os.path.join(REPORTS, name)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh)
        return 0
'''


class TestIsolationProofConditions:
    def test_an_isolated_helper_passes_all_five_conditions(self, scratch_zone):
        root, registry = scratch_zone
        rel = _write(root, "scripts/pettripfinder/zed_zz_routing_001.py", ISOLATED_HELPER)
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert proof["passed"], proof["conditions"]
        assert list(proof["conditions"]) == list(ISO.CONDITIONS)
        assert "markets/reports/zed_zz_routing_001.json" in "".join(proof["conditions"]["writes"]["targets"])

    def test_case_f_an_undeclared_shared_write_fails_the_proof(self, scratch_zone):
        root, registry = scratch_zone
        rel = _write(root, "scripts/pettripfinder/zed_zz_promote_001.py", ISOLATED_HELPER + '''
    def promote():
        target = os.path.join(_DASH, "launch_packages", "pettripfinder", "hotel_policy_facts_zed-zz.json")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("{}")
''')
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not proof["passed"]
        assert proof["failed_conditions"] == ["writes"]
        assert "hotel_policy_facts_zed-zz.json" in proof["conditions"]["writes"]["why"]

    def test_an_unresolvable_write_target_fails_closed(self, scratch_zone):
        root, registry = scratch_zone
        rel = _write(root, "scripts/pettripfinder/zed_zz_dyn_001.py", '''
    import json, os, sys
    def main():
        with open(sys.argv[1], "w") as fh:
            json.dump({}, fh)
''')
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not proof["passed"] and proof["failed_conditions"] == ["writes"]
        assert "cannot be resolved" in proof["conditions"]["writes"]["why"]

    def test_a_disallowed_import_or_dynamic_import_fails(self, scratch_zone):
        root, registry = scratch_zone
        rel = _write(root, "scripts/pettripfinder/zed_zz_bad_import_001.py", '''
    import importlib
    from scripts.pettripfinder.assemble_production_site import assemble
    def main():
        return importlib.import_module("os")
''')
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not proof["passed"] and "imports" in proof["failed_conditions"]
        why = proof["conditions"]["imports"]["why"]
        assert "assemble_production_site" in why and "dynamic dependency" in why

    def test_case_g_a_helper_imported_by_shared_runtime_fails_reachability(self, scratch_zone):
        root, registry = scratch_zone
        rel = _write(root, "scripts/pettripfinder/zed_zz_routing_001.py", ISOLATED_HELPER)
        _write(root, "scripts/pettripfinder/site_data.py",
               "from scripts.pettripfinder.zed_zz_routing_001 import main\n")
        ISO.clear_memo()
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not proof["passed"] and proof["failed_conditions"] == ["reachability"]
        assert "site_data.py" in proof["conditions"]["reachability"]["why"]

    def test_a_dynamic_subprocess_fails_and_read_only_git_passes(self, scratch_zone):
        root, registry = scratch_zone
        good = _write(root, "scripts/pettripfinder/zed_zz_git_001.py", ISOLATED_HELPER + '''
    import subprocess
    def git(*args):
        return subprocess.run(["git"] + list(args), capture_output=True, text=True).stdout
    def status():
        return git("status", "--porcelain") + git("diff", "--name-only")
''')
        bad = _write(root, "scripts/pettripfinder/zed_zz_push_001.py", ISOLATED_HELPER + '''
    import subprocess
    def push():
        subprocess.run(["git", "push", "origin", "main"])
    def anything(cmd):
        subprocess.run(cmd)
''')
        ISO.clear_memo()
        assert ISO.prove(good, "HEAD", ISO.WORKTREE, status="A", registry=registry)["passed"]
        proof = ISO.prove(bad, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not proof["passed"] and proof["failed_conditions"] == ["reachability"]
        assert "push" in proof["conditions"]["reachability"]["why"]
        assert "not a literal" in proof["conditions"]["reachability"]["why"]

    def test_a_registered_market_fails_condition_five(self, scratch_zone):
        root, registry = scratch_zone
        rel = _write(root, "scripts/pettripfinder/zed_zz_routing_001.py", ISOLATED_HELPER)
        (root / "launch_packages" / "pettripfinder" / "markets").mkdir(exist_ok=True)
        (root / "launch_packages" / "pettripfinder" / "markets" / "zed-zz.json").write_text("{}")
        ISO.clear_memo()
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not proof["passed"] and proof["failed_conditions"] == ["registration"]

    def test_a_data_file_in_an_enumerated_shared_directory_fails(self, scratch_zone):
        root, registry = scratch_zone
        rel = _write(root, "launch_packages/pettripfinder/zed_zz_osm_extracts_001.json", "{}")
        _write(root, "tests/pettripfinder/test_x.py",
               'import pathlib\nbefore = sorted(p.name for p in pathlib.Path("launch_packages/pettripfinder").iterdir())\n')
        ISO.clear_memo()
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not proof["passed"] and proof["failed_conditions"] == ["reachability"]
        assert "enumerated" in proof["conditions"]["reachability"]["why"]

    def test_an_unowned_path_fails_namespace_and_nothing_else_is_evaluated(self, scratch_zone):
        root, registry = scratch_zone
        rel = _write(root, "scripts/pettripfinder/other_tool.py", "x = 1\n")
        proof = ISO.prove(rel, "HEAD", ISO.WORKTREE, status="A", registry=registry)
        assert not proof["passed"] and "namespace" in proof["failed_conditions"]
        assert proof["zone"] is None


# --------------------------------------------------------------------------- #
# The classifier matrix: cases A-N on real branches and synthetic changes.
# --------------------------------------------------------------------------- #

def _classify_branch(base, head):
    return RD.classify_change(base, head)


def _row(doc, path):
    return next(r for r in doc["changed_files"] if r["path"] == path)


@pytest.fixture(scope="module")
def nashville():
    return _classify_branch(*NASHVILLE)


@pytest.fixture(scope="module")
def chattanooga():
    return _classify_branch(*CHATTANOOGA)


@pytest.fixture(scope="module")
def lexington():
    return _classify_branch(*LEXINGTON)


@pytest.fixture(scope="module")
def toledo001():
    return _classify_branch(*TOLEDO_001)


@pytest.fixture(scope="module")
def toledo002():
    return _classify_branch(*TOLEDO_002)


@needs_branches
class TestClassifierMatrixOnRealBranches:
    def test_case_a_nashville_helpers_are_market_local(self, nashville):
        helpers = [r for r in nashville["changed_files"]
                   if r["path"].startswith("scripts/pettripfinder/nashville_tn_")]
        assert len(helpers) >= 15
        for r in helpers:
            assert r["classes"] == [RD.MARKET_LOCAL_TOOLING], (r["path"], r["why"])
            assert r["market_local_proof"]["passed"]
            assert r["markets"] == ["nashville-tn"]
        assert _row(nashville, "launch_packages/pettripfinder/identity_census_proposed/nashville-tn.json")["classes"] == [RD.MARKET_LOCAL_TOOLING]
        assert _row(nashville, "launch_packages/pettripfinder/markets/proposed/nashville-tn.json")["classes"] == [RD.MARKET_LOCAL_TOOLING]
        assert _row(nashville, "scripts/pettripfinder/discovery/config/nashville_tn.json")["classes"] == [RD.MARKET_LOCAL_TOOLING]

    def test_case_a_nashville_root_artifact_stays_broad_on_evidence(self, nashville):
        """launch_packages/pettripfinder is enumerated by a shared test
        (test_build_capture_queue iterdir), so a root-level artifact is
        reachable and stays UNCLASSIFIED -- the proof says why."""
        row = _row(nashville, "launch_packages/pettripfinder/nashville_tn_osm_extracts_001.json")
        assert row["classes"] == [RD.UNCLASSIFIED]
        assert row["market_local_proof"]["failed_conditions"] == ["reachability"]
        assert "enumerated" in row["why"]

    def test_case_b_chattanooga_helpers_are_market_local(self, chattanooga):
        helpers = [r for r in chattanooga["changed_files"]
                   if r["path"].startswith("scripts/pettripfinder/chattanooga_tn_")]
        assert len(helpers) >= 6
        assert all(r["classes"] == [RD.MARKET_LOCAL_TOOLING] for r in helpers), \
            [(r["path"], r["why"]) for r in helpers if r["classes"] != [RD.MARKET_LOCAL_TOOLING]]

    def test_case_c_lexington_helpers_are_market_local(self, lexington):
        helpers = [r for r in lexington["changed_files"]
                   if r["path"].startswith("scripts/pettripfinder/lexington_ky_")]
        assert len(helpers) >= 10
        assert all(r["classes"] == [RD.MARKET_LOCAL_TOOLING] for r in helpers), \
            [(r["path"], r["why"]) for r in helpers if r["classes"] != [RD.MARKET_LOCAL_TOOLING]]

    def test_case_d_a_routing_named_local_helper_is_not_broad_for_its_name(self, nashville):
        row = _row(nashville, NASHVILLE_ROUTING)
        assert row["rule"] == "glob:scripts/pettripfinder/*routing*.py"     # the old verdict's source
        assert row["classes"] == [RD.MARKET_LOCAL_TOOLING]
        assert RD.ROUTING_SEMANTIC_CHANGE not in row["classes"]

    def test_case_e_the_shared_osm_registry_stays_routing_semantic(self, lexington, chattanooga):
        for doc in (lexington, chattanooga):
            row = _row(doc, "scripts/pettripfinder/discovery/config/osm_extracts.json")
            assert RD.ROUTING_SEMANTIC_CHANGE in row["classes"] and RD.GENERIC_RUNTIME_CHANGE in row["classes"]
            assert row["market_local_proof"] is None or not row["market_local_proof"]["passed"]

    def test_case_n_toledo_promotion_and_launch_stays_broad_on_its_facts(self, toledo002):
        assert RD.MARKET_LOCAL_TOOLING not in toledo002["change_classes"]
        plan = RD.plan_for(toledo002)
        assert plan["full_regression_required"]
        helper = _row(toledo002, "scripts/pettripfinder/toledo_oh_release_contract_002.py")
        assert helper["classes"] == [RD.GENERIC_RUNTIME_CHANGE]
        # The change set edits regression_lanes.py and the shared pins, so the
        # narrowing is BLOCKED before any proof runs (case H/I/M in one real
        # branch) ...
        assert "scripts/pettripfinder/regression_lanes.py" in toledo002["narrowing_blockers"]
        assert "blocked" in helper["why"]
        # ... and the proof, asked directly, fails on the facts too: the helper
        # writes deploy/ and Toledo is registered at that head.
        proof = ISO.prove("scripts/pettripfinder/toledo_oh_release_contract_002.py", *TOLEDO_002, status="A")
        failed = set(proof["failed_conditions"])
        assert "registration" in failed and "writes" in failed
        shard = _row(toledo002, "launch_packages/pettripfinder/markets/authority/toledo-oh/hotel_exclusions.json")
        assert shard["classes"] == [RD.AUTHORITY_CHANGE] and shard["market_local_proof"] is None

    def test_toledo_001_helpers_were_local_before_registration(self, toledo001):
        helpers = [r for r in toledo001["changed_files"]
                   if r["path"].startswith("scripts/pettripfinder/toledo_oh_")]
        assert helpers and all(r["classes"] == [RD.MARKET_LOCAL_TOOLING] for r in helpers), \
            [(r["path"], r["why"]) for r in helpers if r["classes"] != [RD.MARKET_LOCAL_TOOLING]]

    def test_the_plans_before_and_after(self, nashville, chattanooga, lexington, toledo001):
        """The verdict a whole branch earns, on the same rules the report
        publishes: Nashville and Toledo 001 stay FULL only for a root-level
        artifact; Chattanooga and Lexington for the shared OSM registry."""
        for doc, driver in ((nashville, "launch_packages/pettripfinder/nashville_tn_osm_extracts_001.json"),
                            (toledo001, "launch_packages/pettripfinder/toledo_oh_osm_extracts_001.json"),
                            (chattanooga, "scripts/pettripfinder/discovery/config/osm_extracts.json"),
                            (lexington, "scripts/pettripfinder/discovery/config/osm_extracts.json")):
            plan = RD.plan_for(doc)
            drivers = {r["path"] for r in plan["reasons"] if r["full_regression"] == RD.REQUIRED}
            assert driver in drivers
            assert not any(d.startswith("scripts/pettripfinder/") and "_tn_" in d or "_ky_" in d
                           for d in drivers if d.endswith(".py")), drivers


class TestClassifierMatrixSynthetic:
    """Cases the real branches cannot show: renames, blockers, unknown files."""

    @pytest.fixture()
    def scratch_repo(self, tmp_path, monkeypatch):
        """A git repository laid out like the package (git root / atlas-dashboard),
        with the committed registry and a base commit; the isolation module and
        the classifier are pointed at it."""
        git_root = tmp_path / "root"
        pkg = git_root / "atlas-dashboard"
        (pkg / "scripts" / "pettripfinder" / "discovery" / "config").mkdir(parents=True)
        (pkg / "launch_packages" / "pettripfinder" / "markets" / "reports").mkdir(parents=True)
        (pkg / "launch_packages" / "pettripfinder" / "markets" / "proposed").mkdir(parents=True)
        (pkg / "tests" / "pettripfinder" / "pins").mkdir(parents=True)
        (pkg / "deploy" / "netlify").mkdir(parents=True)
        (pkg / "deploy" / "netlify" / "launch_participation.json").write_text('{"markets": []}')
        shutil.copy2(OWN.REGISTRY_PATH, pkg / "launch_packages" / "pettripfinder" / "market_local_ownership.json")
        (pkg / "scripts" / "pettripfinder" / "site_data.py").write_text("def normalize_name(x):\n    return x\n")
        (pkg / "scripts" / "pettripfinder" / "nashville_tn_routing_001.py").write_text(textwrap.dedent(ISOLATED_HELPER).replace("zed_zz", "nashville_tn"))
        (pkg / "tests" / "pettripfinder" / "pins" / "market_state.json").write_text("{}")
        subprocess.run(["git", "init", "-q"], cwd=str(git_root), check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=str(git_root), check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=str(git_root), check=True)
        subprocess.run(["git", "add", "-A"], cwd=str(git_root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=str(git_root), check=True)
        monkeypatch.setattr(RD, "REPO_ROOT", pkg)
        monkeypatch.setattr(RD, "TESTS_DIR", pkg / "tests")
        monkeypatch.setattr(RD, "PTF_TESTS", pkg / "tests" / "pettripfinder")
        monkeypatch.setattr(RD, "_TEST_SOURCES", None)
        monkeypatch.setattr(ISO, "REPO_ROOT", pkg)
        monkeypatch.setattr(OWN, "REPO_ROOT", pkg)
        monkeypatch.setattr(OWN, "REGISTRY_PATH", pkg / "launch_packages" / "pettripfinder" / "market_local_ownership.json")
        OWN._CACHE.clear()
        ISO.clear_memo()
        return git_root, pkg

    def _commit(self, git_root, message="change"):
        subprocess.run(["git", "add", "-A"], cwd=str(git_root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=str(git_root), check=True)
        ISO.clear_memo()

    def test_an_isolated_helper_edit_is_market_local_and_owes_no_broad_run(self, scratch_repo):
        git_root, pkg = scratch_repo
        helper = pkg / "scripts" / "pettripfinder" / "nashville_tn_routing_001.py"
        helper.write_text(helper.read_text() + "\nX = 1\n")
        doc = RD.classify_change("HEAD", RD.WORKTREE)
        row = _row(doc, "scripts/pettripfinder/nashville_tn_routing_001.py")
        assert row["classes"] == [RD.MARKET_LOCAL_TOOLING]
        plan = RD.plan_for(doc)
        assert not plan["full_regression_required"] and not plan["assembly_required"]
        assert plan["lanes"] == []

    def test_case_h_a_changed_ownership_registry_blocks_the_narrowing(self, scratch_repo):
        git_root, pkg = scratch_repo
        helper = pkg / "scripts" / "pettripfinder" / "nashville_tn_routing_001.py"
        helper.write_text(helper.read_text() + "\nX = 1\n")
        reg = pkg / "launch_packages" / "pettripfinder" / "market_local_ownership.json"
        reg.write_text(reg.read_text() + "\n")
        doc = RD.classify_change("HEAD", RD.WORKTREE)
        assert doc["narrowing_blockers"] == ["launch_packages/pettripfinder/market_local_ownership.json"]
        row = _row(doc, "scripts/pettripfinder/nashville_tn_routing_001.py")
        assert RD.MARKET_LOCAL_TOOLING not in row["classes"] and RD.GENERIC_RUNTIME_CHANGE in row["classes"]
        assert "blocked" in row["why"]
        assert RD.plan_for(doc)["full_regression_required"]

    def test_case_i_a_changed_classifier_blocks_the_narrowing(self, scratch_repo):
        git_root, pkg = scratch_repo
        (pkg / "scripts" / "pettripfinder" / "regression_delta.py").write_text("# classifier\n")
        helper = pkg / "scripts" / "pettripfinder" / "nashville_tn_routing_001.py"
        helper.write_text(helper.read_text() + "\nX = 1\n")
        doc = RD.classify_change("HEAD", RD.WORKTREE)
        assert "scripts/pettripfinder/regression_delta.py" in doc["narrowing_blockers"]
        assert RD.MARKET_LOCAL_TOOLING not in _row(doc, "scripts/pettripfinder/nashville_tn_routing_001.py")["classes"]
        assert RD.plan_for(doc)["full_regression_required"]

    def test_case_m_a_conftest_or_pin_change_blocks_the_narrowing(self, scratch_repo):
        git_root, pkg = scratch_repo
        (pkg / "tests" / "pettripfinder" / "pins" / "market_state.json").write_text('{"x": 1}')
        helper = pkg / "scripts" / "pettripfinder" / "nashville_tn_routing_001.py"
        helper.write_text(helper.read_text() + "\nX = 1\n")
        doc = RD.classify_change("HEAD", RD.WORKTREE)
        assert "tests/pettripfinder/pins/market_state.json" in doc["narrowing_blockers"]
        assert RD.MARKET_LOCAL_TOOLING not in _row(doc, "scripts/pettripfinder/nashville_tn_routing_001.py")["classes"]
        assert RD.plan_for(doc)["full_regression_required"]

    def test_case_j_a_rename_from_local_to_shared_is_broad(self, scratch_repo):
        git_root, pkg = scratch_repo
        src = pkg / "scripts" / "pettripfinder" / "nashville_tn_routing_001.py"
        dst = pkg / "scripts" / "pettripfinder" / "routing_repair_tool.py"
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=str(git_root), check=True)
        self._commit(git_root, "rename to shared")
        doc = RD.classify_change("HEAD~1", "HEAD")
        row = _row(doc, "scripts/pettripfinder/routing_repair_tool.py")
        assert row["renamed_from"] == "scripts/pettripfinder/nashville_tn_routing_001.py"
        assert RD.MARKET_LOCAL_TOOLING not in row["classes"]
        assert RD.GENERIC_RUNTIME_CHANGE in row["classes"]
        assert RD.plan_for(doc)["full_regression_required"]

    def test_case_k_a_rename_from_shared_to_local_evaluates_both_paths(self, scratch_repo):
        git_root, pkg = scratch_repo
        shared = pkg / "scripts" / "pettripfinder" / "routing_tool.py"
        shared.write_text(textwrap.dedent(ISOLATED_HELPER).replace("zed_zz", "nashville_tn"))
        self._commit(git_root, "add shared tool")
        subprocess.run(["git", "mv", str(shared), str(pkg / "scripts" / "pettripfinder" / "nashville_tn_tool_002.py")],
                       cwd=str(git_root), check=True)
        self._commit(git_root, "rename into the zone")
        doc = RD.classify_change("HEAD~1", "HEAD")
        row = _row(doc, "scripts/pettripfinder/nashville_tn_tool_002.py")
        assert row["renamed_from"] == "scripts/pettripfinder/routing_tool.py"
        assert row["classes"] == [RD.GENERIC_RUNTIME_CHANGE]          # no silent narrowing
        assert "renamed from" in row["why"]
        assert RD.plan_for(doc)["full_regression_required"]

    def test_case_l_an_unknown_new_file_is_broad(self, scratch_repo):
        git_root, pkg = scratch_repo
        (pkg / "launch_packages" / "pettripfinder" / "brand_new_thing.bin").write_bytes(b"x")
        doc = RD.classify_change("HEAD", RD.WORKTREE)
        row = _row(doc, "launch_packages/pettripfinder/brand_new_thing.bin")
        assert row["classes"] == [RD.UNCLASSIFIED]
        assert RD.plan_for(doc)["full_regression_required"]

    def test_a_deleted_local_helper_with_a_consumer_stays_broad(self, scratch_repo):
        git_root, pkg = scratch_repo
        (pkg / "scripts" / "pettripfinder" / "site_data.py").write_text(
            "from scripts.pettripfinder.nashville_tn_routing_001 import main\n")
        self._commit(git_root, "shared consumer")
        (pkg / "scripts" / "pettripfinder" / "nashville_tn_routing_001.py").unlink()
        doc = RD.classify_change("HEAD", RD.WORKTREE)
        row = _row(doc, "scripts/pettripfinder/nashville_tn_routing_001.py")
        assert row["status"] == "D" and RD.MARKET_LOCAL_TOOLING not in row["classes"]
        assert RD.GENERIC_RUNTIME_CHANGE in row["classes"]
        assert "reachability" in row["market_local_proof"]["failed_conditions"]


class TestMatrixShape:
    def test_market_local_is_a_safe_narrow_class_and_the_dangerous_ones_are_untouched(self):
        assert RD.MARKET_LOCAL_TOOLING in RD.SAFE_NARROW_CLASSES
        assert RD.VALIDATION_MATRIX[RD.MARKET_LOCAL_TOOLING]["assembly"] == RD.NOT_REQUIRED
        for c in (RD.AUTHORITY_CHANGE, RD.GENERIC_RUNTIME_CHANGE, RD.SCHEMA_CHANGE,
                  RD.ROUTING_SEMANTIC_CHANGE, RD.DEPLOYMENT_CHANGE, RD.UNCLASSIFIED):
            assert c in RD.MANDATORY_FULL_REGRESSION

    def test_no_authority_deployment_or_contract_rule_is_refinable(self):
        for kind, pattern, classes in RD.PATH_RULES:
            rule = "%s:%s" % (kind, pattern)
            if RD.is_market_local_refinable(rule):
                assert RD.AUTHORITY_CHANGE not in classes, rule
                assert not pattern.startswith("deploy/"), rule
                assert not pattern.startswith("scripts/pettripfinder/contracts/"), rule
                assert not pattern.startswith("scripts/pettripfinder/acquisition/"), rule
                assert not pattern.startswith("scripts/pettripfinder/brightdata/"), rule

    def test_classify_path_is_unchanged_for_the_runtime_tree(self):
        """The pure path verdict of every runtime file is still mandatory-full;
        only classify_change, with a proof, may narrow one."""
        assert RD.classify_path(NASHVILLE_HELPER)[0] == (RD.GENERIC_RUNTIME_CHANGE,)
        assert RD.classify_path(NASHVILLE_ROUTING)[0] == (RD.GENERIC_RUNTIME_CHANGE, RD.ROUTING_SEMANTIC_CHANGE)
        assert RD.classify_path("launch_packages/pettripfinder/identity_census_proposed/x.json")[0] == (RD.UNCLASSIFIED,)
        assert RD.classify_path("launch_packages/pettripfinder/identity_census/x.json")[0] == (RD.AUTHORITY_CHANGE, RD.ROUTING_SEMANTIC_CHANGE)

    def test_the_committed_matrix_export_carries_the_new_tables(self):
        doc = json.loads(RD.MATRIX_PATH.read_text(encoding="utf-8-sig"))
        assert RD.MARKET_LOCAL_TOOLING in doc["change_classes"]
        assert doc["market_local_refinable_rules"] == list(RD.MARKET_LOCAL_REFINABLE_RULES)
        assert [b["pattern"] for b in doc["narrowing_blockers"]] == [p for _, p in RD.NARROWING_BLOCKERS]


# --------------------------------------------------------------------------- #
# The demo-media lane role.
# --------------------------------------------------------------------------- #

class TestDemoMediaLane:
    DEMO = "tests/website_generation/integration/test_pettripfinder_demo_media.py"

    def test_the_lane_exists_and_holds_the_suite(self):
        assert RL.WEBSITE_GENERATION_INTEGRATION in RL.LANES
        assert self.DEMO in RL.modules_in_lane(RL.WEBSITE_GENERATION_INTEGRATION)
        assert RL.modules_in_lane(RL.FULL_REGRESSION) == ["tests"]   # broad still runs it

    def test_no_market_local_plan_selects_it(self, tmp_path):
        classification = {"changed_files": [{"path": NASHVILLE_HELPER, "status": "A",
                                             "classes": [RD.MARKET_LOCAL_TOOLING], "rule": "prefix:scripts/pettripfinder/",
                                             "why": "", "shared_test_state": False, "markets": ["nashville-tn"],
                                             "market_local_proof": None, "renamed_from": None}]}
        plan = RD.plan_for(classification)
        assert self.DEMO not in plan["modules"] and "tests" not in plan["modules"]
        assert not plan["full_regression_required"]
        assert all(m.startswith("tests/pettripfinder/") for m in plan["modules"])

    def test_every_mandatory_full_class_still_reaches_it(self):
        for change_class in RD.MANDATORY_FULL_REGRESSION:
            classification = {"changed_files": [{"path": "x", "status": "M", "classes": [change_class],
                                                 "rule": "r", "why": "", "shared_test_state": False,
                                                 "markets": [], "market_local_proof": None, "renamed_from": None}]}
            assert RD.plan_for(classification)["full_regression_required"], change_class

    def test_the_suite_separates_cold_claims_from_consumer_reuse(self):
        src = (REPO_ROOT / self.DEMO).read_text(encoding="utf-8")
        assert "def with_media_chain(tmp_path_factory)" in src
        assert src.count("_real_chain(tmp_path, with_media=True)") == 1      # the fixture only... plus the two cold builds below
        assert '_real_chain(tmp_path / "a", with_media=True)' in src and '_real_chain(tmp_path / "b", with_media=True)' in src
        assert "_real_chain(tmp_path, with_media=False)" in src

    def test_the_marker_is_applied_at_collection(self):
        proc = subprocess.run([sys.executable, "-m", "pytest", self.DEMO, "--collect-only", "-q",
                               "-m", RL.WEBSITE_GENERATION_INTEGRATION, "-p", "no:cacheprovider"],
                              cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
        assert "18 tests collected" in proc.stdout or "18/18 tests collected" in proc.stdout, proc.stdout[-500:]


# --------------------------------------------------------------------------- #
# Session-local assembly reuse (synthetic builders; no market is built here).
# --------------------------------------------------------------------------- #

@pytest.fixture()
def fresh_cache(monkeypatch):
    cache = ASC.SessionCache()
    monkeypatch.setattr(ASC, "CACHE", cache)
    events_before = len(ASC.EVENTS)
    yield cache
    cache.close()
    del ASC.EVENTS[events_before:]


def _builder(output: Path, payload: str, calls: list):
    def build():
        calls.append(payload)
        output.mkdir(parents=True, exist_ok=True)
        (output / "site").mkdir(exist_ok=True)
        (output / "site" / "index.html").write_text(payload)
        (output / "manifest.json").write_text(json.dumps({"bundle_sha256": payload}))
        return {"bundle_sha256": payload}
    return build


class TestSessionCache:
    def test_same_key_builds_once_and_the_copy_is_byte_identical(self, fresh_cache, tmp_path, monkeypatch):
        monkeypatch.setattr(ASC, "input_fingerprint", lambda: {"repo_inputs_sha256": "fp", "repo_input_files": 1, "dynamic": {}})
        calls = []
        out1, out2 = tmp_path / "one", tmp_path / "two"
        r1, e1 = fresh_cache.reuse_or_build("k", {"market": "x"}, out1, _builder(out1, "A", calls))
        r2, e2 = fresh_cache.reuse_or_build("k", {"market": "x"}, out2, _builder(out2, "B", calls))
        assert calls == ["A"]                                   # built once
        assert r1 == r2 == {"bundle_sha256": "A"}
        assert (out2 / "site" / "index.html").read_text() == "A"
        assert e1["verdict"] == ASC.BUILD_EXECUTED and e2["verdict"] == ASC.REUSE_HIT
        assert e2["reused_seconds_avoided"] is not None
        assert r2 is not r1                                     # a copy, never the stored object

    def test_a_different_argument_or_input_is_a_different_key(self, fresh_cache, tmp_path, monkeypatch):
        fp = {"v": "fp1"}
        monkeypatch.setattr(ASC, "input_fingerprint", lambda: {"repo_inputs_sha256": fp["v"], "repo_input_files": 1, "dynamic": {}})
        calls = []
        fresh_cache.reuse_or_build("k", {"market": "x"}, tmp_path / "a", _builder(tmp_path / "a", "A", calls))
        fresh_cache.reuse_or_build("k", {"market": "y"}, tmp_path / "b", _builder(tmp_path / "b", "B", calls))
        fp["v"] = "fp2"                                          # an input mutated
        fresh_cache.reuse_or_build("k", {"market": "x"}, tmp_path / "c", _builder(tmp_path / "c", "C", calls))
        assert calls == ["A", "B", "C"]

    def test_a_failed_build_stores_nothing(self, fresh_cache, tmp_path, monkeypatch):
        monkeypatch.setattr(ASC, "input_fingerprint", lambda: {"repo_inputs_sha256": "fp", "repo_input_files": 1, "dynamic": {}})

        def boom():
            raise RuntimeError("gate failed")
        with pytest.raises(RuntimeError):
            fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "a", boom)
        assert fresh_cache.entries() == []
        calls = []
        _, e = fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "b", _builder(tmp_path / "b", "B", calls))
        assert e["verdict"] == ASC.BUILD_EXECUTED and calls == ["B"]

    def test_a_corrupted_store_is_refused_and_rebuilt(self, fresh_cache, tmp_path, monkeypatch):
        monkeypatch.setattr(ASC, "input_fingerprint", lambda: {"repo_inputs_sha256": "fp", "repo_input_files": 1, "dynamic": {}})
        calls = []
        fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "a", _builder(tmp_path / "a", "A", calls))
        (entry,) = fresh_cache.entries()
        (entry.store / "site" / "index.html").write_text("tampered")
        _, e = fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "b", _builder(tmp_path / "b", "A2", calls))
        assert e["verdict"] == ASC.BUILD_EXECUTED and calls == ["A", "A2"]

    def test_cold_bypasses_the_lookup_and_the_env_switch_disables_reuse(self, fresh_cache, tmp_path, monkeypatch):
        monkeypatch.setattr(ASC, "input_fingerprint", lambda: {"repo_inputs_sha256": "fp", "repo_input_files": 1, "dynamic": {}})
        calls = []
        fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "a", _builder(tmp_path / "a", "A", calls))
        with ASC.cold():
            _, e = fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "b", _builder(tmp_path / "b", "A", calls))
        assert e["verdict"] == ASC.BUILD_EXECUTED
        monkeypatch.setenv("PTF_ASSEMBLY_REUSE", "0")
        _, e = fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "c", _builder(tmp_path / "c", "A", calls))
        assert e["verdict"] == ASC.BUILD_EXECUTED and len(calls) == 3

    def test_consumers_cannot_mutate_each_other(self, fresh_cache, tmp_path, monkeypatch):
        monkeypatch.setattr(ASC, "input_fingerprint", lambda: {"repo_inputs_sha256": "fp", "repo_input_files": 1, "dynamic": {}})
        calls = []
        fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "a", _builder(tmp_path / "a", "A", calls))
        (tmp_path / "a" / "site" / "index.html").write_text("consumer one scribbled")
        _, e = fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "b", _builder(tmp_path / "b", "A", calls))
        assert e["verdict"] == ASC.REUSE_HIT
        assert (tmp_path / "b" / "site" / "index.html").read_text() == "A"

    def test_concurrent_same_key_requests_build_once(self, fresh_cache, tmp_path, monkeypatch):
        monkeypatch.setattr(ASC, "input_fingerprint", lambda: {"repo_inputs_sha256": "fp", "repo_input_files": 1, "dynamic": {}})
        calls = []
        verdicts = []

        def slow_builder(output):
            def build():
                time.sleep(0.3)
                return _builder(output, "A", calls)()
            return build

        def worker(i):
            out = tmp_path / ("w%d" % i)
            _, e = fresh_cache.reuse_or_build("k", {"m": 1}, out, slow_builder(out))
            verdicts.append(e["verdict"])
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert calls == ["A"] and sorted(verdicts) == [ASC.BUILD_EXECUTED] + [ASC.REUSE_HIT] * 3

    def test_the_key_covers_the_inputs_the_order_names(self):
        assert {"launch_packages/pettripfinder", "deploy/netlify", "scripts", "engines", "templates"} <= set(ASC.INPUT_ROOTS)
        doc = ASC.input_fingerprint()
        assert doc["repo_input_files"] > 1500
        dyn = doc["dynamic"]
        assert set(dyn) >= {"markets_dir", "census_dir", "env", "python", "platform", "module_state"}

    def test_module_state_signature_sees_a_monkeypatched_constant_and_function(self, monkeypatch):
        from scripts.pettripfinder import site_data as SD
        before = ASC.module_state_signature()
        monkeypatch.setattr(SD, "PRODUCTION_CSV", Path("/somewhere/else.csv"))
        after_constant = ASC.module_state_signature()
        monkeypatch.setattr(SD, "normalize_name", lambda s: s)
        after_function = ASC.module_state_signature()
        assert before != after_constant != after_function

    def test_summary_reports_build_and_reuse_counts(self, fresh_cache, tmp_path, monkeypatch):
        monkeypatch.setattr(ASC, "input_fingerprint", lambda: {"repo_inputs_sha256": "fp", "repo_input_files": 1, "dynamic": {}})
        calls = []
        fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "a", _builder(tmp_path / "a", "A", calls))
        fresh_cache.reuse_or_build("k", {"m": 1}, tmp_path / "b", _builder(tmp_path / "b", "A", calls))
        s = ASC.summary()
        assert s["build_count"] >= 1 and s["reuse_count"] >= 1
        row = next(r for r in s["per_key"] if r["assembly_kind"] == "k")
        assert row["build_count"] == 1 and row["reuse_count"] == 1
        assert set(row) >= {"input_key", "build_count", "reuse_count", "build_seconds", "reused_seconds_avoided"}


class TestReuseHooksAreWired:
    """The three builders route through the cache and the cold tests bypass it;
    proved by source, because building a market here would cost minutes."""

    def test_generator_bundle_and_compose_call_the_cache(self):
        gen = (REPO_ROOT / "scripts" / "generate_pettripfinder_columbus_site.py").read_text(encoding="utf-8")
        nb = (REPO_ROOT / "scripts" / "pettripfinder" / "assemble_netlify_bundle.py").read_text(encoding="utf-8")
        ps = (REPO_ROOT / "scripts" / "pettripfinder" / "assemble_production_site.py").read_text(encoding="utf-8")
        assert 'CACHE.reuse_or_build(\n        "generator_site"' in gen
        assert 'CACHE.reuse_or_build(\n        "market_bundle"' in nb
        assert 'CACHE.reuse_or_build(\n        "production_site"' in ps
        assert "def _prepare_build" in gen and "def _generate" in gen

    def test_the_cold_claims_are_explicit(self):
        for rel, marker in (("tests/pettripfinder/test_prod005_netlify_config.py", "with cold():"),
                            ("tests/pettripfinder/test_prod004_verified_only.py", "with cold():"),
                            ("tests/pettripfinder/test_global_assembler.py", "with cold():")):
            assert marker in (REPO_ROOT / rel).read_text(encoding="utf-8"), rel

    def test_the_committed_parity_report_proves_byte_identity(self):
        doc = json.loads((REPORTS / "atlas_throughput_002_cold_reuse_parity.json").read_text(encoding="utf-8"))
        assert doc["schema"] == "atlas-throughput-cold-reuse-parity/1.0"
        for row in doc["paths"]:
            assert row["files_identical"] is True and row["manifest_identical"] is True, row


# --------------------------------------------------------------------------- #
# Safety freeze: the production/promotion rule did not move.
# --------------------------------------------------------------------------- #

class TestProductionSafetyFreeze:
    @pytest.mark.parametrize("path", [
        "launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json",
        "launch_packages/pettripfinder/markets/authority/dayton-oh/identity_routing.json",
        "launch_packages/pettripfinder/markets/toledo-oh.json",
        "launch_packages/pettripfinder/identity_census/toledo-oh.json",
        "launch_packages/pettripfinder/toledo_oh_final_partition_001.json",
        "deploy/netlify/release_contracts/toledo-oh.json",
        "deploy/netlify/launch_participation.json",
        "deploy/netlify/deployment_records/ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json",
        "scripts/pettripfinder/contracts/policy_schema.py",
        "scripts/pettripfinder/assemble_production_site.py",
        "scripts/pettripfinder/assemble_netlify_bundle.py",
        "scripts/pettripfinder/identity_routing.py",
        "scripts/pettripfinder/deployment_authorization.py",
        "scripts/pettripfinder/regression_delta.py",
        "scripts/pettripfinder/assembly_session_cache.py",
        "some/brand/new/surface.bin",
    ])
    def test_every_production_surface_still_requires_a_full_regression(self, path):
        classes, rule = RD.classify_path(path)
        assert any(c in RD.MANDATORY_FULL_REGRESSION for c in classes), (path, classes)
        classification = {"changed_files": [{"path": path, "status": "M", "classes": list(classes),
                                             "rule": rule, "why": "", "shared_test_state": False,
                                             "markets": [], "market_local_proof": None, "renamed_from": None}]}
        plan = RD.plan_for(classification)
        assert plan["full_regression_required"] and plan["assembly_required"]

    def test_the_matrix_rows_of_the_dangerous_classes_are_byte_for_byte_what_they_were(self):
        """The five mandatory-full rows and UNCLASSIFIED, compared with the
        matrix committed by FACTORY-REGRESSION-V2-001 (read from git)."""
        old = json.loads(subprocess.run(
            ["git", "show", "0a623a0:atlas-dashboard/launch_packages/pettripfinder/regression_validation_matrix.json"],
            cwd=str(REPO_ROOT.parent), capture_output=True, text=True, encoding="utf-8").stdout)
        new = json.loads(RD.MATRIX_PATH.read_text(encoding="utf-8-sig"))
        old_rows = {r["change_class"]: r for r in old["rows"]}
        new_rows = {r["change_class"]: r for r in new["rows"]}
        for change_class in (RD.AUTHORITY_CHANGE, RD.GENERIC_RUNTIME_CHANGE, RD.SCHEMA_CHANGE,
                             RD.ROUTING_SEMANTIC_CHANGE, RD.DEPLOYMENT_CHANGE, RD.UNCLASSIFIED,
                             RD.TEST_EXPECTATION_CHANGE, RD.BOOKKEEPING_REGISTRATION_CHANGE):
            assert old_rows[change_class] == new_rows[change_class], change_class
        assert old["mandatory_full_regression"] == new["mandatory_full_regression"]

    def test_a_mixed_change_is_decided_by_its_strictest_file(self):
        classification = {"changed_files": [
            {"path": NASHVILLE_HELPER, "status": "A", "classes": [RD.MARKET_LOCAL_TOOLING], "rule": "r", "why": "",
             "shared_test_state": False, "markets": ["nashville-tn"], "market_local_proof": None, "renamed_from": None},
            {"path": "launch_packages/pettripfinder/hotel_policy_facts_nashville-tn.json", "status": "A",
             "classes": [RD.AUTHORITY_CHANGE], "rule": "r", "why": "", "shared_test_state": False,
             "markets": ["nashville-tn"], "market_local_proof": None, "renamed_from": None}]}
        plan = RD.plan_for(classification)
        assert plan["full_regression_required"] and plan["assembly_required"]
