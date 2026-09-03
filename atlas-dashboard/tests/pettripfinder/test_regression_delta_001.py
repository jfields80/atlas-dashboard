"""PTF-FACTORY-REGRESSION-V2-001 -- the delta-scoped validation gate.

WHAT THESE TESTS GUARD
----------------------
That a late fix earns a narrow proof only when its change surface is provably
narrow. Three separate things have to hold and each is tested here.

The classifier is honest about what it does not know. A path no rule claims is
UNCLASSIFIED, and UNCLASSIFIED costs a full regression -- so teaching the
factory a new directory can only ever make it slower, never quieter.

The one narrowing is proven by syntax tree, not by diff shape. A test module
drops from TEST_EXPECTATION_CHANGE to BOOKKEEPING_REGISTRATION_CHANGE only
when the ONLY difference between the two versions is the elements of a
module-level literal collection that is named in REGISTRATION_CONTAINERS. An
assertion, an import, a helper, a count table, a container nobody declared --
each of them blocks the narrowing, and each has a test.

And the whole-change verdict is the strictest row, not the commonest one. The
Cincinnati replay proves the safe direction end to end; the negative battery
proves the dangerous one, file by file, against the real paths in this repo.
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import regression_delta as D          # noqa: E402
from scripts.pettripfinder import regression_lanes as L          # noqa: E402


# --------------------------------------------------------------------------- #
# 1. The matrix is committed, and the committed copy is the module's.
# --------------------------------------------------------------------------- #

def test_the_committed_matrix_is_the_modules_matrix():
    """A drifting export would let the runbook and the gate disagree."""
    committed = json.loads(D.MATRIX_PATH.read_text(encoding="utf-8-sig"))
    assert committed == json.loads(json.dumps(D.matrix_document()))


def test_every_change_class_has_exactly_one_matrix_row():
    assert tuple(D.VALIDATION_MATRIX) == D.CHANGE_CLASSES
    for change_class, row in D.VALIDATION_MATRIX.items():
        assert row["assembly"] in (D.REQUIRED, D.NOT_REQUIRED), change_class
        assert row["full_regression"] in (D.REQUIRED, D.NOT_REQUIRED,
                                          D.CONDITIONAL), change_class
        assert row["surface"] and row["why"], change_class
        if row["full_regression"] == D.CONDITIONAL:
            assert row["condition"], change_class
        for lane in row["lanes"]:
            assert lane in L.LANES, (change_class, lane)


def test_the_dangerous_classes_are_all_mandatory_full():
    """The safety property stated as a set, so a prose edit cannot move it."""
    for change_class in (D.AUTHORITY_CHANGE, D.GENERIC_RUNTIME_CHANGE,
                         D.SCHEMA_CHANGE, D.ROUTING_SEMANTIC_CHANGE,
                         D.DEPLOYMENT_CHANGE, D.UNCLASSIFIED):
        assert change_class in D.MANDATORY_FULL_REGRESSION, change_class
    assert D.BOOKKEEPING_REGISTRATION_CHANGE in D.SAFE_NARROW_CLASSES
    assert set(D.MANDATORY_FULL_REGRESSION).isdisjoint(D.SAFE_NARROW_CLASSES)


def test_assembly_is_required_wherever_a_full_regression_is():
    """Nothing may demand the broad suite yet skip the renderer.

    The Dayton appliers proved the ordering: only the production ASSEMBLY
    caught the renderer-fatal defect, and it caught it before the suite did.
    """
    for change_class, row in D.VALIDATION_MATRIX.items():
        if row["full_regression"] == D.REQUIRED:
            assert row["assembly"] == D.REQUIRED, change_class


# --------------------------------------------------------------------------- #
# 2. Path classification.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("relpath,expected", [
    # the order's own worked examples
    ("tests/pettripfinder/acquisition/test_store_integration_025.py",
     D.TEST_EXPECTATION_CHANGE),
    ("scripts/pettripfinder/contracts/policy_reading.py", D.GENERIC_RUNTIME_CHANGE),
    ("launch_packages/pettripfinder/hotel_policy_facts_cincinnati-oh.json",
     D.AUTHORITY_CHANGE),
    ("deploy/netlify/deployment_records/ptf-deploy-003-6a982a1fc32c2911d0d65d04.json",
     D.DEPLOYMENT_CHANGE),
    # the rest of the surface
    ("launch_packages/pettripfinder/markets/authority/dayton-oh/identity_routing.json",
     D.AUTHORITY_CHANGE),
    ("launch_packages/pettripfinder/markets/dayton-oh.json", D.AUTHORITY_CHANGE),
    ("deploy/netlify/release_contracts/dayton-oh.json", D.DEPLOYMENT_CHANGE),
    ("launch_packages/pettripfinder/regression_baselines/f75aa95.json",
     D.BASELINE_MANIFEST_ONLY),
    ("launch_packages/pettripfinder/markets/reports/ptf_marriott_supersession_022.json",
     D.GENERATED_REPORT_ONLY),
    ("docs/PTF_HARDENED_FACTORY_RUNBOOK.md", D.DOCUMENTATION_ONLY),
    ("PTF-ST-LOUIS-MARKET-001_FINAL.md", D.DOCUMENTATION_ONLY),
    ("tests/pettripfinder/pins/market_state.json", D.TEST_EXPECTATION_CHANGE),
    ("scripts/pettripfinder/assemble_netlify_bundle.py", D.GENERIC_RUNTIME_CHANGE),
])
def test_a_path_lands_in_the_class_it_belongs_to(relpath, expected):
    classes, rule = D.classify_path(relpath)
    assert expected in classes, (relpath, classes, rule)


@pytest.mark.parametrize("relpath,also", [
    ("scripts/pettripfinder/contracts/policy_schema.py", D.SCHEMA_CHANGE),
    ("scripts/pettripfinder/contracts/policy_reading.py", D.SCHEMA_CHANGE),
    ("scripts/pettripfinder/census_location.py", D.ROUTING_SEMANTIC_CHANGE),
    ("scripts/pettripfinder/assemble_production_site.py", D.DEPLOYMENT_CHANGE),
    ("launch_packages/pettripfinder/identity_routing.json",
     D.ROUTING_SEMANTIC_CHANGE),
])
def test_a_runtime_path_carries_every_semantic_it_can_reach(relpath, also):
    """One file may be several classes; the plan is the union of all of them."""
    classes, _rule = D.classify_path(relpath)
    assert D.GENERIC_RUNTIME_CHANGE in classes or D.AUTHORITY_CHANGE in classes
    assert also in classes, (relpath, classes)


def test_an_unknown_path_is_unclassified_and_that_costs_the_full_suite():
    classes, rule = D.classify_path("some/directory/nobody/taught/us/about.bin")
    assert classes == (D.UNCLASSIFIED,)
    assert rule == "no rule"
    assert D.VALIDATION_MATRIX[D.UNCLASSIFIED]["full_regression"] == D.REQUIRED


def test_the_baseline_directory_beats_the_authority_rules():
    """Rule ORDER is load-bearing: a baseline manifest lives under
    launch_packages/pettripfinder/ like authority does, and would be swept
    into AUTHORITY_CHANGE by a later rule if it were not claimed first."""
    classes, _ = D.classify_path(
        "launch_packages/pettripfinder/regression_baselines/c854469.json")
    assert classes == (D.BASELINE_MANIFEST_ONLY,)


def test_the_two_generated_report_directories_are_claimed():
    for relpath in ("launch_packages/pettripfinder/reports/"
                    "factory_regression_v2_001_benchmark.json",
                    "launch_packages/pettripfinder/markets/reports/"
                    "ptf_marriott_supersession_022.json"):
        assert (REPO / relpath).is_file(), relpath
        assert D.classify_path(relpath)[0] == (D.GENERATED_REPORT_ONLY,), relpath


def test_the_bulk_of_launch_packages_is_deliberately_unclassified():
    """A guard against a future tidy-up.

    Five hundred files sit directly under launch_packages/pettripfinder/:
    capture results, founder packets, ledgers, snapshots -- and census
    partitions and candidate ledgers, under names that do not distinguish
    them. They classify UNCLASSIFIED, which costs a full regression, and that
    is the intended answer. If someone adds a blanket rule to quieten them,
    this test says so before the gate does.
    """
    out = subprocess.run(["git", "ls-files",
                          "launch_packages/pettripfinder/*.json"],
                         cwd=str(REPO), capture_output=True, text=True)
    direct = [p for p in out.stdout.splitlines() if p.count("/") == 2]
    assert len(direct) > 100, "expected the populated directory, got %d" % len(
        direct)
    unclassified = [p for p in direct
                    if D.classify_path(p)[0] == (D.UNCLASSIFIED,)]
    assert len(unclassified) > 100, (
        "a blanket rule now claims %d of %d files that used to be treated "
        "conservatively" % (len(direct) - len(unclassified), len(direct)))


def test_a_report_never_outranks_the_authority_it_reports_on():
    """The generated-artifact rules sit AFTER the authority rules, so a file
    that is both an authority and named like a report stays an authority."""
    classes, _ = D.classify_path(
        "launch_packages/pettripfinder/cincinnati_final_partition_001.json")
    assert D.AUTHORITY_CHANGE in classes


# --------------------------------------------------------------------------- #
# 3. The one narrowing, proven by syntax tree.
# --------------------------------------------------------------------------- #

STORE_MODULE = "tests/pettripfinder/acquisition/test_store_integration_025.py"

BASE_REGISTRATION = '''"""A module docstring."""

import json

OTHER_MARKET_RUNS = {
    "st_louis_direct_http_001",
    "dayton_oh_free_static_001",
}


def test_every_run_on_disk_is_classified():
    assert OTHER_MARKET_RUNS
'''


def _refine(head_source, base_source=BASE_REGISTRATION, module=STORE_MODULE):
    return D.refine_test_change(module, base_source, head_source)


def test_adding_a_run_id_to_a_declared_registration_is_bookkeeping():
    head = BASE_REGISTRATION.replace(
        '    "dayton_oh_free_static_001",\n',
        '    "dayton_oh_free_static_001",\n'
        '    # PTF-CINCINNATI-HARDENED-REVALIDATION-001, zero-cost lane.\n'
        '    "cincinnati_oh_free_static_001",\n'
        '    "cincinnati_oh_firecrawl_001",\n')
    verdict, why = _refine(head)
    assert verdict == D.BOOKKEEPING_REGISTRATION_CHANGE, why
    assert "OTHER_MARKET_RUNS" in why


def test_removing_a_run_id_is_bookkeeping_too():
    head = BASE_REGISTRATION.replace('    "st_louis_direct_http_001",\n', "")
    verdict, _why = _refine(head)
    assert verdict == D.BOOKKEEPING_REGISTRATION_CHANGE


def test_changing_an_assertion_in_the_same_file_is_not_bookkeeping():
    head = BASE_REGISTRATION.replace("assert OTHER_MARKET_RUNS",
                                     "assert len(OTHER_MARKET_RUNS) == 2")
    verdict, why = _refine(head)
    assert verdict == D.TEST_EXPECTATION_CHANGE
    assert "outside a module-level assignment" in why


def test_adding_an_import_is_not_bookkeeping():
    head = BASE_REGISTRATION.replace("import json", "import json\nimport os")
    verdict, why = _refine(head)
    assert verdict == D.TEST_EXPECTATION_CHANGE
    assert "added or removed" in why


def test_adding_a_test_function_is_not_bookkeeping():
    head = BASE_REGISTRATION + "\n\ndef test_new_thing():\n    assert True\n"
    verdict, why = _refine(head)
    assert verdict == D.TEST_EXPECTATION_CHANGE
    assert "added or removed" in why


def test_an_undeclared_container_is_not_bookkeeping_however_it_looks():
    """The whole safety argument. EXPECTED_PROFILES is a literal set in a test
    file, edited exactly the way a registration is edited -- and it is an
    EXPECTATION, so it is not narrowed."""
    base = BASE_REGISTRATION.replace(
        "OTHER_MARKET_RUNS = {", "EXPECTED_PROFILES = {")
    head = base.replace('    "dayton_oh_free_static_001",\n',
                        '    "dayton_oh_free_static_001",\n    "extra",\n')
    verdict, why = D.refine_test_change(STORE_MODULE, base, head)
    assert verdict == D.TEST_EXPECTATION_CHANGE
    assert "not declared registrations" in why


def test_a_module_with_no_declared_container_is_never_narrowed():
    head = BASE_REGISTRATION.replace('    "dayton_oh_free_static_001",\n',
                                     '    "dayton_oh_free_static_001",\n    "x",\n')
    verdict, why = D.refine_test_change(
        "tests/pettripfinder/test_markets.py", BASE_REGISTRATION, head)
    assert verdict == D.TEST_EXPECTATION_CHANGE
    assert "no registration container is declared" in why


def test_turning_the_container_into_a_computation_is_not_bookkeeping():
    """A comprehension is not a declaration of what exists."""
    head = BASE_REGISTRATION.replace(
        'OTHER_MARKET_RUNS = {\n    "st_louis_direct_http_001",\n'
        '    "dayton_oh_free_static_001",\n}',
        'OTHER_MARKET_RUNS = {p.name for p in []}')
    verdict, why = _refine(head)
    assert verdict == D.TEST_EXPECTATION_CHANGE
    assert "literal collection" in why


def test_a_comment_only_edit_is_not_vouched_for():
    head = BASE_REGISTRATION.replace(
        "import json", "import json  # noqa")
    verdict, why = _refine(head)
    assert verdict == D.TEST_EXPECTATION_CHANGE
    assert "comment or whitespace only" in why


def test_a_new_or_deleted_module_is_never_bookkeeping():
    assert D.refine_test_change(STORE_MODULE, None, BASE_REGISTRATION)[0] \
        == D.TEST_EXPECTATION_CHANGE
    assert D.refine_test_change(STORE_MODULE, BASE_REGISTRATION, None)[0] \
        == D.TEST_EXPECTATION_CHANGE


def test_every_registration_container_exists_where_it_is_declared():
    """A rename must fail loudly rather than silently stop narrowing."""
    for module, container, why in D.REGISTRATION_CONTAINERS:
        path = REPO / "tests" / module
        assert path.is_file(), module
        assert why.strip(), (module, container)
        value = D._assigned_value(
            path.read_text(encoding="utf-8-sig"), container)
        assert value is not None, "%s has no %s" % (module, container)
        assert D.literal_elements(value) is not None, \
            "%s.%s is not a literal collection of constants" % (module, container)


def test_the_declared_container_is_the_one_the_cincinnati_failure_reads():
    """The registry is not a guess: OTHER_MARKET_RUNS is read by the very node
    the Cincinnati broad regression returned as TRUE_NEW."""
    source = (REPO / "tests" / D.REGISTRATION_CONTAINERS[0][0]).read_text(
        encoding="utf-8-sig")
    tree = ast.parse(source)
    target = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "test_every_run_on_disk_is_classified")
    names = {n.id for n in ast.walk(target) if isinstance(n, ast.Name)}
    assert "OTHER_MARKET_RUNS" in names


# --------------------------------------------------------------------------- #
# 4. The plan a classification owes.
# --------------------------------------------------------------------------- #

def _classification(rows):
    """A hand-built classification document, so a plan can be tested without
    inventing commits."""
    built = []
    for path, classes, shared, markets in rows:
        built.append({"path": path, "status": "M", "classes": list(classes),
                      "rule": "test", "why": "test", "shared_test_state": shared,
                      "markets": list(markets)})
    return {"schema": D.SCHEMA_CLASSIFICATION, "base": "x", "base_sha": "x",
            "head": "y", "head_sha": "y", "changed_file_count": len(built),
            "changed_files": built, "change_classes": []}


def test_a_bookkeeping_plan_runs_the_module_and_its_directory_and_no_lane():
    plan = D.plan_for(_classification([
        (STORE_MODULE, (D.BOOKKEEPING_REGISTRATION_CHANGE,), False,
         ("cincinnati-oh",)),
    ]))
    assert plan["full_regression_required"] is False
    assert plan["assembly_required"] is False
    assert plan["lanes"] == []
    assert "tests/pettripfinder/acquisition" in plan["modules"]
    # the directory subsumes the module itself
    assert STORE_MODULE not in plan["modules"]
    # and the market it registers pulls its own targeted modules in
    assert any(m.startswith("tests/pettripfinder/test_cincinnati_")
               for m in plan["modules"])


def test_one_dangerous_file_among_many_harmless_ones_still_costs_the_suite():
    plan = D.plan_for(_classification([
        ("docs/PTF_HARDENED_FACTORY_RUNBOOK.md", (D.DOCUMENTATION_ONLY,),
         False, ()),
        ("launch_packages/pettripfinder/regression_baselines/f75aa95.json",
         (D.BASELINE_MANIFEST_ONLY,), False, ()),
        (STORE_MODULE, (D.BOOKKEEPING_REGISTRATION_CHANGE,), False, ()),
        ("scripts/pettripfinder/contracts/policy_schema.py",
         (D.GENERIC_RUNTIME_CHANGE, D.SCHEMA_CHANGE), False, ()),
    ]))
    assert plan["full_regression_required"] is True
    assert plan["assembly_required"] is True


def test_a_shared_pin_makes_the_conditional_row_a_yes():
    shared = D.plan_for(_classification([
        ("tests/pettripfinder/pins/market_state.json",
         (D.TEST_EXPECTATION_CHANGE,), True, ()),
    ]))
    assert shared["full_regression_required"] is True
    owned = D.plan_for(_classification([
        ("tests/pettripfinder/test_dayton_authority.py",
         (D.TEST_EXPECTATION_CHANGE,), False, ("dayton-oh",)),
    ]))
    assert owned["full_regression_required"] is False


def test_the_shared_state_table_names_files_that_exist():
    for kind, pattern in D.SHARED_TEST_STATE:
        if kind == "prefix":
            assert (REPO / pattern).is_dir(), pattern
        else:
            assert list(REPO.glob(pattern)), pattern


def test_the_pins_directory_is_shared_state():
    assert D.is_shared_test_state("tests/pettripfinder/pins/deployment_state.json")
    assert D.is_shared_test_state("tests/pettripfinder/conftest.py")
    assert not D.is_shared_test_state(
        "tests/pettripfinder/test_dayton_authority.py")


# --------------------------------------------------------------------------- #
# 5. Phase 9 -- the negative battery, on real paths in this repo.
# --------------------------------------------------------------------------- #

NEGATIVE_CASES = (
    ("policy parser / schema contract",
     "scripts/pettripfinder/contracts/policy_schema.py"),
    ("market authority JSON",
     "launch_packages/pettripfinder/markets/authority/dayton-oh/identity_routing.json"),
    ("routing contract",
     "launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json"),
    ("deployment manifest / record",
     "deploy/netlify/deployment_records/ptf-deploy-003-6a982a1fc32c2911d0d65d04.json"),
    ("generic assembler",
     "scripts/pettripfinder/assemble_netlify_bundle.py"),
    ("release contract",
     "deploy/netlify/release_contracts/cincinnati-oh.json"),
    ("identity routing runtime",
     "scripts/pettripfinder/census_location.py"),
)


@pytest.mark.parametrize("label,relpath",
                         NEGATIVE_CASES, ids=[c[0] for c in NEGATIVE_CASES])
def test_a_dangerous_change_always_requires_a_full_regression(label, relpath):
    assert (REPO / relpath).exists(), "%s: %s is not in this checkout" % (label,
                                                                         relpath)
    classes, rule = D.classify_path(relpath)
    assert D.UNCLASSIFIED not in classes, (label, rule)
    plan = D.plan_for(_classification([(relpath, classes, False, ())]))
    assert plan["full_regression_required"] is True, (label, classes)
    assert plan["assembly_required"] is True, (label, classes)


def test_no_safe_classification_can_be_reached_from_a_runtime_or_authority_path():
    """Swept over the real tree rather than a sample: every tracked runtime and
    authority file must land in a mandatory-full class."""
    out = subprocess.run(
        ["git", "ls-files", "scripts/pettripfinder", "deploy",
         "launch_packages/pettripfinder/markets/authority"],
        cwd=str(REPO), capture_output=True, text=True)
    paths = [p for p in out.stdout.splitlines() if p.strip()]
    assert len(paths) > 100, "expected a populated tree, got %d" % len(paths)
    offenders = []
    for path in paths:
        classes, _rule = D.classify_path(path)
        if not any(c in D.MANDATORY_FULL_REGRESSION for c in classes):
            offenders.append((path, classes))
    assert not offenders, offenders[:10]


def test_this_work_orders_own_change_requires_a_full_regression():
    """The module that decides is itself generic runtime, and says so."""
    classes, _rule = D.classify_path(
        "scripts/pettripfinder/regression_delta.py")
    assert classes == (D.GENERIC_RUNTIME_CHANGE,)
    classes, _rule = D.classify_path(
        "launch_packages/pettripfinder/regression_validation_matrix.json")
    assert classes == (D.GENERIC_RUNTIME_CHANGE,)


# --------------------------------------------------------------------------- #
# 6. Closure proof: node ids, never counts.
# --------------------------------------------------------------------------- #

NODE = ("tests/pettripfinder/acquisition/test_store_integration_025.py"
        "::test_every_run_on_disk_is_classified")


def test_a_node_that_passed_in_the_delta_run_is_closed():
    proof = D.prove_closure([NODE], {NODE: "passed"})
    assert proof["results"][NODE] == D.CLOSED
    assert proof["all_accounted_for"] is True


def test_a_node_the_delta_run_never_collected_is_not_closed():
    """The count-based proof this order forbids, stated as a test: a node that
    was never exercised is absent from the failure list, and absence is not
    evidence."""
    proof = D.prove_closure([NODE], {"tests/other.py::test_x": "passed"})
    assert proof["results"][NODE] == D.NOT_EXERCISED
    assert proof["all_accounted_for"] is False
    assert proof["not_exercised"] == [NODE]


def test_a_skipped_node_is_not_closed_either():
    proof = D.prove_closure([NODE], {NODE: "skipped"})
    assert proof["results"][NODE] == D.NOT_EXERCISED
    assert proof["all_accounted_for"] is False


def test_a_still_failing_node_is_reported_as_such():
    proof = D.prove_closure([NODE], {NODE: "failed"})
    assert proof["results"][NODE] == D.STILL_FAILING
    assert proof["all_accounted_for"] is False


def test_every_original_failure_must_be_accounted_for():
    other = "tests/pettripfinder/test_markets.py::test_x"
    proof = D.prove_closure([NODE, other], {NODE: "passed"})
    assert proof["all_accounted_for"] is False
    assert proof["closed"] == [NODE]
    assert proof["not_exercised"] == [other]


def test_resolved_is_scoped_to_what_the_run_actually_exercised():
    baseline = {"schema": L.SCHEMA_BASELINE, "source_sha": "f75aa95",
                "failing_node_ids": ["a::t1", "b::t2"]}
    resolved = D.resolved_against_baseline({"a::t1": "passed"}, baseline)
    assert resolved == ["a::t1"]          # b::t2 was never run, so no claim


def test_a_failure_outside_the_baseline_is_true_new():
    baseline = {"schema": L.SCHEMA_BASELINE, "source_sha": "f75aa95",
                "failing_node_ids": ["a::t1"]}
    doc = D.classify_against_baseline(["a::t1", "c::t3"], baseline)
    assert doc["PRE_EXISTING"] == ["a::t1"]
    assert doc["TRUE_NEW"] == ["c::t3"]


# --------------------------------------------------------------------------- #
# 7. Phase 8 -- the Cincinnati replay, end to end over real git objects.
# --------------------------------------------------------------------------- #

CINCINNATI_RUNS = ("cincinnati_oh_free_static_001", "cincinnati_oh_firecrawl_001")


@pytest.fixture
def replay_repo(tmp_path):
    """A throwaway git repo shaped like this one, holding the real module.

    The replay must not touch this checkout's Cincinnati authority -- it does
    not touch any authority at all. What it needs is the exact BEFORE and AFTER
    of the registration file under two commits, which a scratch repo gives for
    free and which no market can observe.
    """
    root = tmp_path / "repo"
    inner = root / REPO.name
    target = inner / "tests" / "pettripfinder" / "acquisition"
    target.mkdir(parents=True)
    source = (REPO / "tests" / "pettripfinder" / "acquisition"
              / "test_store_integration_025.py").read_text(encoding="utf-8-sig")
    module = target / "test_store_integration_025.py"
    module.write_text(source, encoding="utf-8")

    def git(*args):
        return subprocess.run(["git", *args], cwd=str(root),
                              capture_output=True, text=True, check=True)

    git("init", "-q")
    git("config", "user.email", "replay@example.com")
    git("config", "user.name", "replay")
    git("add", "-A")
    git("commit", "-q", "-m", "before the registration fix")
    base = git("rev-parse", "HEAD").stdout.strip()

    # THE FIX, and nothing else: two run ids and their comment.
    anchor = '    "dayton_oh_live_audit_001",\n'
    assert anchor in source
    fixed = source.replace(anchor, anchor + (
        "    # PTF-CINCINNATI-HARDENED-REVALIDATION-001: the zero-cost static\n"
        "    # lane and the Firecrawl rung, both cincinnati-oh.\n"
        '    "%s",\n    "%s",\n' % CINCINNATI_RUNS))
    module.write_text(fixed, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "register the two Cincinnati runs")
    head = git("rev-parse", "HEAD").stdout.strip()
    return root, inner, base, head, source, fixed


def test_the_cincinnati_registration_fix_classifies_as_bookkeeping(replay_repo):
    """The headline. The real file, the real edit, the real classifier."""
    _root, _inner, _base, _head, before, after = replay_repo
    verdict, why = D.refine_test_change(
        "tests/pettripfinder/acquisition/test_store_integration_025.py",
        before, after)
    assert verdict == D.BOOKKEEPING_REGISTRATION_CHANGE, why
    assert "OTHER_MARKET_RUNS" in why


def test_the_replay_edit_really_is_the_two_run_ids_and_nothing_else(replay_repo):
    _root, _inner, _base, _head, before, after = replay_repo
    added = [l.strip() for l in after.splitlines() if l not in before.splitlines()]
    quoted = [l for l in added if l.startswith('"')]
    assert quoted == ['"%s",' % CINCINNATI_RUNS[0], '"%s",' % CINCINNATI_RUNS[1]]
    assert D._module_shape(before).keys() == D._module_shape(after).keys()


def test_the_replay_plan_skips_assembly_and_the_broad_regression(replay_repo):
    """FULL_REGRESSION_REQUIRED = NO, from the classification alone."""
    _root, _inner, _base, _head, before, after = replay_repo
    relpath = "tests/pettripfinder/acquisition/test_store_integration_025.py"
    verdict, _why = D.refine_test_change(relpath, before, after)
    plan = D.plan_for(_classification([(relpath, (verdict,), False,
                                        ("cincinnati-oh",))]))
    assert plan["full_regression_required"] is False
    assert plan["assembly_required"] is False
    assert "tests/pettripfinder/acquisition" in plan["modules"]


def test_the_replay_classifies_through_git_not_through_a_string(replay_repo,
                                                                monkeypatch):
    """Same verdict when the two versions come from real commits."""
    root, inner, base, head, _before, _after = replay_repo
    monkeypatch.setattr(D, "REPO_ROOT", inner)
    files = D.changed_files(base, head)
    assert list(files) == [
        "tests/pettripfinder/acquisition/test_store_integration_025.py"]
    doc = D.classify_change(base, head)
    assert doc["change_classes"] == [D.BOOKKEEPING_REGISTRATION_CHANGE]
    row = doc["changed_files"][0]
    assert row["markets"] == ["cincinnati-oh"], row["markets"]
    assert row["shared_test_state"] is False


def test_a_second_edit_in_the_same_commit_loses_the_narrowing(replay_repo):
    """The replay's safety twin: bundle a real assertion change with the
    registration and the whole file leaves the safe class."""
    _root, _inner, _base, _head, before, after = replay_repo
    also_changed = after.replace("assert not unclassified, unclassified",
                                 "assert not unclassified")
    assert also_changed != after
    verdict, why = D.refine_test_change(
        "tests/pettripfinder/acquisition/test_store_integration_025.py",
        before, also_changed)
    assert verdict == D.TEST_EXPECTATION_CHANGE, why


# --------------------------------------------------------------------------- #
# 8. The artifacts a closure leaves behind.
# --------------------------------------------------------------------------- #

def _delta_doc():
    return {
        "schema": D.SCHEMA_DELTA, "base": "aaa", "base_sha": "aaa",
        "head": "bbb", "head_sha": "bbb",
        "classification": _classification([
            (STORE_MODULE, (D.BOOKKEEPING_REGISTRATION_CHANGE,), False,
             ("cincinnati-oh",))]),
        "plan": D.plan_for(_classification([
            (STORE_MODULE, (D.BOOKKEEPING_REGISTRATION_CHANGE,), False,
             ("cincinnati-oh",))])),
        "FULL_REGRESSION_REQUIRED": "NO",
        "full_regression_reason": "bookkeeping only",
        "run": {"collected": 10, "passed": 10, "skipped": 0, "failed": 0,
                "seconds": 42.0},
        "against_baseline": {"baseline_source_sha": "f75aa95",
                             "PRE_EXISTING": [], "TRUE_NEW": [],
                             "RESOLVED": [NODE]},
        "closure": D.prove_closure([NODE], {NODE: "passed"}),
        "clean": True,
    }


def test_a_closure_artifact_carries_every_field_the_order_requires():
    doc = D.closure_document(_delta_doc(), order="PTF-CINCINNATI-EXAMPLE",
                             fix_commit="deadbee", rationale="because")
    for field in ("schema", "work_order", "fix_commit_sha", "base_sha",
                  "original_true_new_node_ids", "baseline_source_sha",
                  "changed_files", "change_classes", "required_validations",
                  "targeted_result", "node_id_results",
                  "FULL_REGRESSION_REQUIRED", "rationale",
                  "all_original_failures_accounted_for"):
        assert field in doc, field
    assert doc["schema"] == D.SCHEMA_CLOSURE
    assert doc["original_true_new_node_ids"] == [NODE]
    assert doc["node_id_results"][NODE] == D.CLOSED
    assert doc["all_original_failures_accounted_for"] is True
    assert doc["FULL_REGRESSION_REQUIRED"] == "NO"


def test_a_closure_artifact_is_not_accounted_for_when_a_node_was_not_run():
    delta = _delta_doc()
    delta["closure"] = D.prove_closure([NODE], {})
    doc = D.closure_document(delta, order="x", fix_commit="y")
    assert doc["all_original_failures_accounted_for"] is False


def test_the_committed_closures_all_verify():
    """Every durable artifact under failure_closures/ still states a closed
    account: every original node id present, and every one of them CLOSED."""
    if not D.CLOSURES_DIR.is_dir():
        pytest.skip("no closures recorded yet")
    found = sorted(D.CLOSURES_DIR.glob("*.json"))
    assert found, "the directory exists, so it must hold artifacts"
    for path in found:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        assert doc["schema"] == D.SCHEMA_CLOSURE, path.name
        originals = doc["original_true_new_node_ids"]
        assert originals, path.name
        for nodeid in originals:
            assert doc["node_id_results"].get(nodeid) == D.CLOSED, \
                (path.name, nodeid)
        assert doc["all_original_failures_accounted_for"] is True, path.name
        assert doc["FULL_REGRESSION_REQUIRED"] in ("YES", "NO"), path.name


# --------------------------------------------------------------------------- #
# 9. The runbook states the rule the module enforces.
# --------------------------------------------------------------------------- #

def test_the_runbook_carries_the_post_broad_fix_rule():
    text = (REPO / "docs" / "PTF_HARDENED_FACTORY_RUNBOOK.md").read_text(
        encoding="utf-8-sig")
    assert "POST-BROAD FIX RULE" in text
    assert "regression_delta" in text
    for change_class in D.CHANGE_CLASSES:
        assert change_class in text, change_class
    assert "SAFE DELTA" in text and "UNSAFE DELTA" in text
