# -*- coding: utf-8 -*-
"""ATLAS-THROUGHPUT-001 -- the instrumentation proves itself.

The order adds two read-only tools: a pytest profiling plugin
(:mod:`scripts.pettripfinder.throughput_profile`) and an analysis CLI
(:mod:`scripts.pettripfinder.throughput_baseline`). Neither may change what a
test does, write anywhere but its ``--out``, or touch authority. These tests
show that, and that the analysis reads the evidence it claims to read.

Nothing here assembles a market or runs the broad suite: the one authorized
instrumented baseline is the plugin's broad validation, and its artifacts are
what the committed report cites.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from scripts.pettripfinder import throughput_baseline as TB
from scripts.pettripfinder import throughput_profile as TP

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "reports"
PLUGIN = "scripts.pettripfinder.throughput_profile"


# --------------------------------------------------------------------------- #
# The recorder and the process readers fail safe.
# --------------------------------------------------------------------------- #

class TestRecorder:
    def test_writes_one_json_object_per_line_with_the_schema(self, tmp_path):
        rec = TP.Recorder(tmp_path / "p.jsonl", "run-1")
        rec.write("test", node_id="a::b", total_seconds=1.5)
        rec.write("assembly", market="dayton-oh")
        rec.close()
        rows = TP.read_profile(tmp_path / "p.jsonl")
        assert [r["kind"] for r in rows] == ["test", "assembly"]
        assert all(r["schema"] == TP.SCHEMA and r["run_id"] == "run-1" for r in rows)
        assert rows[0]["node_id"] == "a::b" and rows[1]["market"] == "dayton-oh"

    def test_an_inert_recorder_writes_nothing_and_never_raises(self, tmp_path):
        rec = TP.Recorder(None, "run-2")
        assert not rec.active
        rec.write("test", node_id="x")
        rec.close()
        assert list(tmp_path.iterdir()) == []

    def test_an_unwritable_path_is_swallowed_not_raised(self, tmp_path):
        blocker = tmp_path / "file"
        blocker.write_text("not a directory")
        rec = TP.Recorder(blocker / "p.jsonl", "run-3")
        assert not rec.active
        rec.write("test")
        rec.close()

    def test_process_readers_return_numbers_or_none(self):
        peak = TP.peak_working_set_mb()
        assert peak is None or peak > 0
        ws = TP.working_set_mb()
        assert ws is None or ws > 0
        io = TP.io_bytes()
        assert io is None or set(io) == {"read", "write"}
        assert set(TP.cpu_times()) >= {"user", "system"}


# --------------------------------------------------------------------------- #
# Fingerprints: deterministic, content-sensitive, market-scoped.
# --------------------------------------------------------------------------- #

class TestFingerprints:
    def _tree(self, root: Path) -> None:
        (root / "launch_packages/pettripfinder/markets/authority/x-oh").mkdir(parents=True)
        (root / "launch_packages/pettripfinder/markets/authority/x-oh/hotel_exclusions.json").write_text("{}")
        (root / "launch_packages/pettripfinder/hotel_policy_facts_x-oh.json").write_text('{"hotels": []}')
        (root / "launch_packages/pettripfinder/markets/authority/y-oh").mkdir(parents=True)
        (root / "launch_packages/pettripfinder/markets/authority/y-oh/hotel_exclusions.json").write_text("{}")
        (root / "launch_packages/pettripfinder/seed_businesses.csv").write_text("a,b\n")
        (root / "deploy/netlify").mkdir(parents=True)
        (root / "deploy/netlify/launch_participation.json").write_text("{}")

    def test_same_bytes_same_digest_and_a_changed_byte_moves_it(self, tmp_path):
        self._tree(tmp_path)
        fp = TP.Fingerprints(tmp_path)
        first = fp.market("x-oh")
        assert first["files"] == 2
        assert TP.Fingerprints(tmp_path).market("x-oh") == first
        (tmp_path / "launch_packages/pettripfinder/hotel_policy_facts_x-oh.json").write_text('{"hotels": [1]}')
        assert TP.Fingerprints(tmp_path).market("x-oh")["sha256"] != first["sha256"]

    def test_a_market_fingerprint_ignores_another_markets_files(self, tmp_path):
        self._tree(tmp_path)
        before = TP.Fingerprints(tmp_path).market("x-oh")
        (tmp_path / "launch_packages/pettripfinder/markets/authority/y-oh/hotel_exclusions.json").write_text('{"changed": 1}')
        assert TP.Fingerprints(tmp_path).market("x-oh") == before
        site = TP.Fingerprints(tmp_path).whole_site()
        assert site["markets"] == 2 and site["files"] >= 4

    def test_the_real_authority_fingerprints_cover_every_registered_market(self):
        from scripts.pettripfinder.markets import load_markets
        fp = TP.Fingerprints()
        for market in load_markets():
            assert fp.market(market.market_id)["files"] >= 1, market.market_id
        assert fp.whole_site()["markets"] == len(load_markets())


# --------------------------------------------------------------------------- #
# The assembly wrap measures and returns the original result unchanged.
# --------------------------------------------------------------------------- #

class TestAssemblyWrap:
    def test_the_wrapper_records_market_hashes_and_passes_the_result_through(self, tmp_path):
        import types

        class Market:
            market_id = "dayton-oh"

        mod = types.ModuleType("fake_assembler")
        calls = []

        def assemble(context, output, contract=None, market=None):
            calls.append((context, output, market))
            return {"bundle_sha256": "abc123"}

        mod.assemble = assemble
        sys.modules["fake_assembler"] = mod
        try:
            rec = TP.Recorder(tmp_path / "p.jsonl", "run-w")
            wrap = TP.AssemblyWrap(rec, TP.Fingerprints(), lambda: "tests/x.py::test_y")
            wrap.install([("fake_assembler", "assemble", "market_bundle")])
            assert wrap.installed and not wrap.skipped
            result = mod.assemble("production", str(tmp_path / "out"), market=Market())
            assert result == {"bundle_sha256": "abc123"}
            assert calls == [("production", str(tmp_path / "out"), calls[0][2])]
            rec.close()
            rows = TP.read_profile(tmp_path / "p.jsonl")
            assert len(rows) == 1 and rows[0]["kind"] == "assembly"
            row = rows[0]
            assert row["assembly_kind"] == "market_bundle"
            assert row["market"] == "dayton-oh" and row["context"] == "production"
            assert row["test_node_id"] == "tests/x.py::test_y"
            assert row["output_hash"] == "abc123"
            assert row["cache"] == TP.NO_CACHE and row["exit_status"] == "ok"
            assert row["market_input_hash"] == TP.Fingerprints().market("dayton-oh")["sha256"]
            assert len(row["dependency_input_hash"]) == 64
            assert row["elapsed_seconds"] >= 0
        finally:
            sys.modules.pop("fake_assembler", None)

    def test_an_exception_is_recorded_and_re_raised(self, tmp_path):
        import types
        mod = types.ModuleType("fake_assembler_2")

        def assemble(*a, **k):
            raise RuntimeError("gate failed")

        mod.assemble = assemble
        sys.modules["fake_assembler_2"] = mod
        try:
            rec = TP.Recorder(tmp_path / "p.jsonl", "run-e")
            wrap = TP.AssemblyWrap(rec, TP.Fingerprints(), lambda: None)
            wrap.install([("fake_assembler_2", "assemble", "market_bundle")])
            with pytest.raises(RuntimeError):
                mod.assemble("production", "out")
            rec.close()
            row = TP.read_profile(tmp_path / "p.jsonl")[0]
            assert row["exit_status"] == "error" and "gate failed" in row["error"]
        finally:
            sys.modules.pop("fake_assembler_2", None)

    def test_a_missing_target_is_skipped_not_fatal(self, tmp_path):
        wrap = TP.AssemblyWrap(TP.Recorder(None, "r"), TP.Fingerprints(), lambda: None)
        wrap.install([("no.such.module", "assemble", "x")])
        assert not wrap.installed and wrap.skipped[0]["module"] == "no.such.module"

    def test_every_committed_wrap_target_resolves_on_this_tree(self):
        wrap = TP.AssemblyWrap(TP.Recorder(None, "r"), TP.Fingerprints(), lambda: None)
        # Resolve only -- never install on the live modules from inside the suite.
        for module_name, attr, _kind in TP.WRAP_TARGETS:
            holder = wrap._resolve_holder(module_name)
            assert callable(getattr(holder, attr)), (module_name, attr)


# --------------------------------------------------------------------------- #
# The plugin end to end, in a child pytest over a scratch suite.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def child_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("child")
    suite = root / "test_scratch.py"
    suite.write_text(textwrap.dedent("""
        import time
        import pytest

        @pytest.fixture(scope="module")
        def slow():
            time.sleep(0.12)
            return 1

        def test_fast(slow):
            assert slow == 1

        @pytest.mark.parametrize("n", [1, 2])
        def test_param(n):
            assert n

        def test_fails():
            assert False
    """))
    profile = root / "profile.jsonl"
    inventory = root / "inventory.json"
    argv = [sys.executable, "-m", "pytest", str(suite), "-q", "-p", "no:cacheprovider",
            "-p", PLUGIN, "--ptf-profile-out", str(profile),
            "--ptf-inventory-out", str(inventory), "--ptf-profile-fixture-floor", "0.05",
            "--rootdir", str(root), "-c", str(REPO_ROOT / "pytest.ini")]
    proc = subprocess.run(argv, cwd=str(REPO_ROOT), capture_output=True, text=True,
                          timeout=300)
    return proc, profile, inventory


class TestPluginEndToEnd:
    def test_the_child_run_reports_its_own_outcomes_unchanged(self, child_run):
        proc, _, _ = child_run
        assert proc.returncode == 1, proc.stdout[-2000:] + proc.stderr[-2000:]
        assert "1 failed, 3 passed" in proc.stdout

    def test_every_row_kind_is_present_with_phases(self, child_run):
        _, profile, _ = child_run
        rows = TP.read_profile(profile)
        kinds = [r["kind"] for r in rows]
        assert kinds[0] == "session_start" and kinds[-1] == "session_finish"
        assert kinds.count("collection") == 1 and kinds.count("test") == 4
        tests = {r["node_id"].split("::")[-1]: r for r in rows if r["kind"] == "test"}
        assert tests["test_fails"]["outcome"] == "failed"
        assert tests["test_fast"]["outcome"] == "passed"
        assert tests["test_fast"]["setup_seconds"] >= 0.1   # the fixture is charged to setup
        assert all(r["total_seconds"] >= 0 for r in tests.values())
        # Installed third-party plugins may contribute their own session
        # fixtures (a Faker session fixture does on this box); the scratch
        # suite's own slow fixture must be there with its scope.
        fixtures = {r["fixture"]: r for r in rows if r["kind"] == "fixture_setup"}
        assert "slow" in fixtures and fixtures["slow"]["scope"] == "module"
        assert fixtures["slow"]["seconds"] >= 0.1
        finish = rows[-1]
        assert finish["counts"] == {"passed": 3, "failed": 1}
        assert finish["recorder_errors"] == 0
        assert finish["collection_seconds"] > 0 and finish["execution_seconds"] > 0
        assert finish["rows_written"] == len(rows)

    def test_the_inventory_names_every_item_with_fixtures_and_params(self, child_run):
        _, _, inventory = child_run
        doc = json.loads(inventory.read_text(encoding="utf-8"))
        assert doc["collected"] == 4 and doc["test_functions"] == 3
        assert doc["parametrized_items"] == 2
        by_name = {i["name"]: i for i in doc["items"]}
        assert "slow" in by_name["test_fast"]["fixtures"]
        assert by_name["test_param[1]"]["parametrized"] and by_name["test_param[1]"]["param_id"] == "1"
        assert doc["parametrization_count_by_function"] == {
            str(Path("test_scratch.py")) + "::test_param": 2} or \
            list(doc["parametrization_count_by_function"].values()) == [2]

    def test_without_an_output_path_the_plugin_is_inert(self, tmp_path):
        suite = tmp_path / "test_one.py"
        suite.write_text("def test_one():\n    assert True\n")
        proc = subprocess.run([sys.executable, "-m", "pytest", str(suite), "-q",
                               "-p", "no:cacheprovider", "-p", PLUGIN,
                               "--rootdir", str(tmp_path), "-c", str(REPO_ROOT / "pytest.ini")],
                              cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert list(tmp_path.glob("*.jsonl")) == []


# --------------------------------------------------------------------------- #
# The analysis CLI reads what it claims to read.
# --------------------------------------------------------------------------- #

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="4" time="100.0" timestamp="2026-09-07T00:00:00">
<testcase classname="tests.pettripfinder.contracts.test_identity_key" name="test_a" time="0.5"/>
<testcase classname="tests.pettripfinder.test_global_deployment_architecture_045" name="test_b" time="60.0"/>
<testcase classname="tests.pettripfinder.test_dayton_authority.TestX" name="test_c" time="1.0"><failure message="boom"/></testcase>
<testcase classname="tests.website_generation.integration.test_demo" name="test_d" time="30.0"><skipped/></testcase>
</testsuite></testsuites>
"""


class TestJunitProfile:
    def test_overhead_is_suite_time_minus_case_time_and_categories_roll_up(self, tmp_path):
        xml = tmp_path / "r.xml"
        xml.write_text(JUNIT)
        doc = TB.profile_junit("r", xml)
        assert doc["collected"] == 4
        assert doc["sum_case_time_s"] == 91.5 and doc["collection_and_session_overhead_s"] == 8.5
        assert doc["status_counts"] == {"passed": 2, "failure": 1, "skipped": 1}
        cats = doc["by_category"]
        assert cats["DEPLOYMENT"]["seconds"] == 60.0
        assert cats["FAST_CONTRACT"]["seconds"] == 0.5
        assert cats["MARKET_LOCAL"]["seconds"] == 1.0
        assert cats["OTHER_NON_PTF"]["seconds"] == 30.0
        assert doc["top_nodes"][0]["node"].endswith("test_global_deployment_architecture_045.py::test_b")
        assert doc["by_market"]["dayton-oh"] == 1.0
        assert doc["failing"][0]["node"].endswith("test_dayton_authority.py::TestX::test_c")

    def test_the_node_id_matches_the_lane_runners_reconstruction(self, tmp_path):
        from scripts.pettripfinder import regression_lanes as RL
        xml = tmp_path / "r.xml"
        xml.write_text(JUNIT)
        ours = {c["node"] for c in TB.read_junit(xml)["cases"]}
        assert ours == set(RL._junit_cases(xml))

    def test_category_of_every_ptf_module_is_a_declared_category(self):
        from scripts.pettripfinder import regression_lanes as RL
        for path in RL.PTF_TESTS.rglob("test_*.py"):
            rel = "tests/pettripfinder/" + RL._relpath(path)
            assert TB.category_of(rel) in TB.CATEGORIES
        assert TB.category_of("tests/pettripfinder/contracts/test_identity_key.py") == TB.FAST_CONTRACT
        assert TB.category_of("tests/pettripfinder/test_per_market_release_contracts.py") == TB.ASSEMBLY
        assert TB.category_of("tests/pettripfinder/acquisition/test_paid_attempt_ledger.py") == TB.CORE_SHARED
        assert TB.category_of("tests/pettripfinder/acquisition/test_marriott_template_021.py") == TB.HISTORY
        assert TB.category_of("not/a/test.py") == TB.UNKNOWN


class TestRunProfile:
    def _rows(self):
        base = {"schema": TP.SCHEMA, "run_id": "r"}

        def row(kind, **f):
            d = dict(base)
            d.update(kind=kind, ts=0)
            d.update(f)
            return d

        return [
            row("session_start", git_head="abc", cpu={"user": 1.0, "system": 0.5}, wrapped=[], wrap_skipped=[]),
            row("collection", collected=3, seconds=2.0),
            row("assembly", invocation_id="r-1", assembly_kind="market_bundle", nesting_depth=0,
                dependency_input_hash="h1", market="dayton-oh", context="production",
                start_ts=1, elapsed_seconds=10.0, output_hash="o", test_node_id="t1", peak_working_set_mb=100),
            row("assembly", invocation_id="r-2", assembly_kind="market_bundle", nesting_depth=0,
                dependency_input_hash="h1", market="dayton-oh", context="production",
                start_ts=2, elapsed_seconds=8.0, output_hash="o", test_node_id="t2", peak_working_set_mb=120),
            row("assembly", invocation_id="r-3", assembly_kind="wge_assembly_engine", nesting_depth=1,
                dependency_input_hash="h9", market=None, context=None,
                start_ts=2, elapsed_seconds=1.0, output_hash=None, test_node_id="t2", peak_working_set_mb=120),
            row("assembly", invocation_id="r-4", assembly_kind="production_site", nesting_depth=0,
                dependency_input_hash="h2", market=None, context="production",
                start_ts=3, elapsed_seconds=30.0, output_hash="p", test_node_id="t3", peak_working_set_mb=300),
            row("fixture_setup", fixture="production", scope="module", seconds=30.5, node_id="t3"),
            row("test", node_id="t1", total_seconds=10.5, setup_seconds=0.1, call_seconds=10.4, teardown_seconds=0.0, outcome="passed"),
            row("test", node_id="t2", total_seconds=9.0, setup_seconds=0.0, call_seconds=9.0, teardown_seconds=0.0, outcome="passed"),
            row("test", node_id="t3", total_seconds=31.0, setup_seconds=30.5, call_seconds=0.5, teardown_seconds=0.0, outcome="failed"),
            row("session_finish", seconds=60.0, collection_seconds=2.0, execution_seconds=58.0, exit_status=1,
                counts={"passed": 2, "failed": 1}, peak_working_set_mb=300,
                cpu={"user": 41.0, "system": 2.5}, cpu_at_start={"user": 1.0, "system": 0.5},
                io_bytes={"read": 1, "write": 2}, recorder_errors=0, rows_written=11),
        ]

    def test_repeated_identical_inputs_are_counted_and_costed(self):
        doc = TB.profile_run(self._rows())
        a = doc["assembly"]
        assert a["total_invocations_outer"] == 3
        assert a["total_invocations_including_nested"] == 4
        assert a["unique_inputs"] == 2
        assert a["repeated_identical_builds"] == 1
        assert a["seconds_spent_on_repeated_identical_builds"] == 8.0
        assert a["by_market"] == {"dayton-oh": 2, "(all-market/none)": 1}
        assert a["top_input_keys_by_build_count"][0]["builds"] == 2
        assert a["cold_vs_repeat"][0]["cold_seconds"] == 10.0
        assert a["cold_vs_repeat"][0]["repeat_seconds_mean"] == 8.0

    def test_phases_and_cpu_are_derived_not_typed(self):
        doc = TB.profile_run(self._rows())
        assert doc["total_wall_s"] == 60.0 and doc["collection_s"] == 2.0 and doc["execution_s"] == 58.0
        assert doc["phase_seconds"]["test_call"] == 19.9
        assert doc["phase_seconds"]["test_setup"] == 30.6
        assert doc["phase_seconds"]["assembly_outer_calls"] == 48.0
        assert doc["cpu_seconds"] == {"user": 40.0, "system": 2.0, "children_user": 0.0, "children_system": 0.0}
        assert doc["peak_working_set_mb"] == 300
        assert doc["top_nodes"][0]["node"] == "t3"
        assert doc["top_fixtures"][0]["fixture"] == "production"


class TestSamplerSummary:
    def test_the_process_tree_peak_walks_parent_ids(self):
        rows = [
            {"ts": "t1", "pid": "1", "ppid": "0", "name": "python.exe", "ws_mb": "100", "cpu_s": "5"},
            {"ts": "t1", "pid": "2", "ppid": "1", "name": "python.exe", "ws_mb": "50", "cpu_s": ""},
            {"ts": "t1", "pid": "9", "ppid": "0", "name": "python.exe", "ws_mb": "999", "cpu_s": ""},
            {"ts": "t1", "pid": "0", "ppid": "0", "name": "SYSTEM_FREE_MB", "ws_mb": "1000"},
            {"ts": "t2", "pid": "1", "ppid": "0", "name": "python.exe", "ws_mb": "120", "cpu_s": "9"},
            {"ts": "t2", "pid": "3", "ppid": "2", "name": "python.exe", "ws_mb": "0", "cpu_s": ""},
            {"ts": "t2", "pid": "2", "ppid": "1", "name": "python.exe", "ws_mb": "40", "cpu_s": ""},
            {"ts": "t2", "pid": "0", "ppid": "0", "name": "SYSTEM_FREE_MB", "ws_mb": "800"},
        ]
        doc = TB.summarize_sampler(rows, 1)
        assert doc["samples_with_root"] == 2
        assert doc["peak_process_tree_working_set_mb"] == 160.0 and doc["peak_process_tree_at"] == "t2"
        assert doc["peak_root_working_set_mb"] == 120.0
        assert doc["root_cpu_seconds_last_sample"] == "9"
        assert doc["system_free_mb_min"] == 800.0


class TestClassifierAudit:
    def test_a_market_named_helper_under_scripts_is_a_full_regression_on_its_own(self):
        doc = TB.classifier_audit(["scripts/pettripfinder/nashville_tn_shadow_market_001.py",
                                   "launch_packages/pettripfinder/markets/reports/nashville_tn_routing_001.json",
                                   "launch_packages/pettripfinder/markets/proposed/nashville-tn.json"], [])
        rows = {r["path"]: r for r in doc["representative_paths"]}
        assert rows["scripts/pettripfinder/nashville_tn_shadow_market_001.py"]["classes"] == ["GENERIC_RUNTIME_CHANGE"]
        assert rows["scripts/pettripfinder/nashville_tn_shadow_market_001.py"]["full_required_on_its_own"]
        assert rows["launch_packages/pettripfinder/markets/reports/nashville_tn_routing_001.json"]["classes"] == ["GENERATED_REPORT_ONLY"]
        assert rows["launch_packages/pettripfinder/markets/proposed/nashville-tn.json"]["classes"] == ["UNCLASSIFIED"]

    def test_this_orders_own_change_surface_requires_a_full_regression(self):
        """The two new modules live under scripts/pettripfinder/, so the
        classifier owes them a broad run; the one solitary instrumented
        baseline is that run."""
        doc = TB.classifier_audit(["scripts/pettripfinder/throughput_profile.py",
                                   "scripts/pettripfinder/throughput_baseline.py",
                                   "tests/pettripfinder/test_atlas_throughput_001.py"], [])
        rows = {r["path"]: r for r in doc["representative_paths"]}
        assert rows["scripts/pettripfinder/throughput_profile.py"]["full_required_on_its_own"]
        assert rows["scripts/pettripfinder/throughput_baseline.py"]["full_required_on_its_own"]
        assert not rows["tests/pettripfinder/test_atlas_throughput_001.py"]["full_required_on_its_own"]


class TestFailureBaselineAudit:
    def test_every_baseline_failure_is_grouped_exactly_once(self):
        baseline = json.loads((REPO_ROOT / "launch_packages/pettripfinder/regression_baselines/f75aa95.json")
                              .read_text(encoding="utf-8-sig"))
        doc = TB.failure_baseline_audit(baseline, None)
        assert sum(doc["counts"].values()) == len(baseline["failing_node_ids"]) == 160
        assert doc["counts"]["UNKNOWN"] == 0
        grouped = {n["node"] for g in doc["groups"].values() for n in g}
        assert grouped == set(baseline["failing_node_ids"])

    def test_an_environmental_message_lands_in_environment(self, tmp_path):
        xml = tmp_path / "r.xml"
        xml.write_text("""<?xml version="1.0"?><testsuites><testsuite tests="1" time="1">
<testcase classname="tests.pettripfinder.acquisition.test_marriott_template_021" name="test_z" time="1">
<failure message="FileNotFoundError: no such file"/></testcase></testsuite></testsuites>""")
        baseline = {"source_sha": "x", "failing_node_ids": [
            "tests/pettripfinder/acquisition/test_marriott_template_021.py::test_z"]}
        doc = TB.failure_baseline_audit(baseline, xml)
        assert doc["counts"]["ENVIRONMENT"] == 1 and doc["junit_failure_set_identical_to_baseline"]


# --------------------------------------------------------------------------- #
# The committed artifacts are the tools' own output, not typed numbers.
# --------------------------------------------------------------------------- #

class TestCommittedArtifacts:
    def test_the_frozen_success_criteria_carry_the_orders_targets_unclaimed(self):
        doc = json.loads((REPORTS / "atlas_throughput_001_success_criteria.json").read_text(encoding="utf-8"))
        assert doc["schema"] == "atlas-throughput-success-criteria/1.0"
        targets = {t["id"]: t for t in doc["targets"]}
        assert targets["LARGE_NEW_MARKET_SOURCE_READY_MINUTES"]["target"] == 180
        assert targets["RELEASE_LANE_ADMISSION_TO_VERIFIED_LIVE_MINUTES"]["target"] == 60
        assert targets["FOUNDER_ACTIVE_MINUTES_PER_LAUNCH"]["target"] == 30
        assert targets["FACTORY_PROOF_LAUNCHES_PER_8H_DAY"]["target"] == 3
        assert all(t["status"] == "TARGET_NOT_CLAIMED" for t in doc["targets"])

    def test_the_junit_profile_report_was_produced_by_this_module(self):
        doc = json.loads((REPORTS / "atlas_throughput_001_broad_run_profiles.json").read_text(encoding="utf-8"))
        assert doc["schema"] == TB.SCHEMA_JUNIT
        assert len(doc["runs"]) >= 10
        for run in doc["runs"]:
            assert run["collected"] > 17000
            assert abs(run["suite_time_s"] - run["sum_case_time_s"] - run["collection_and_session_overhead_s"]) < 0.2

    def test_the_classifier_audit_report_names_real_branches(self):
        doc = json.loads((REPORTS / "atlas_throughput_001_classifier_audit.json").read_text(encoding="utf-8"))
        assert doc["schema"] == TB.SCHEMA_CLASSIFY
        labels = {b["label"] for b in doc["branches"]}
        assert {"nashville-new-market-001", "toledo-new-market-001"} <= labels
        for b in doc["branches"]:
            assert b["FULL_REGRESSION_REQUIRED"] == "YES"
            assert b["driver_count"] >= 1
