"""PTF-FACTORY-REGRESSION-V2-001 -- the change-surface classifier, the
validation matrix, and delta-scoped validation of a late fix.

    python -m scripts.pettripfinder.regression_delta matrix [--json]
    python -m scripts.pettripfinder.regression_delta classify --base <sha> [--head <sha>|WORKTREE]
    python -m scripts.pettripfinder.regression_delta validate \
        --base <sha> [--head WORKTREE] \
        --baseline launch_packages/pettripfinder/regression_baselines/<sha>.json \
        --require-closed <node id> [--require-closed ...] \
        --out data/regression/<run>/delta.json [--closure-out <artifact>]

WHY
---
:mod:`regression_lanes` answered "which subset finds the pins a market change
moved". It did not answer the question that costs the most wall-clock: after
the FIRST broad regression has already run and returned one TRUE_NEW failure,
does closing that failure cost another broad regression?

Cincinnati made the question concrete. The broad regression found exactly one
TRUE_NEW node:

    tests/pettripfinder/acquisition/test_store_integration_025.py::test_every_run_on_disk_is_classified

The fix added two run ids to ``OTHER_MARKET_RUNS`` -- a module-level literal
set in a test file that declares which directories under ``data/acquisition/``
belong to another market. No authority moved. No runtime module was touched.
No bundle changed. The candidate hash was the same before and after. And the
workflow still spent another 90-110 minutes proving it.

That is the cost this module removes, and it removes it WITHOUT weakening the
gate: a narrow class earns a narrow proof only when the change surface is
provably narrow, and everything else -- including anything the classifier
cannot name -- still costs a full regression.

THE THREE PARTS
---------------
1.  :data:`PATH_RULES` classifies a changed path by what it IS, never by what
    its commit message says. A path that matches no rule is
    :data:`UNCLASSIFIED`, which requires a full regression.

2.  :func:`refine_test_change` is the one place a path-level class may be
    NARROWED, and only downward from :data:`TEST_EXPECTATION_CHANGE` to
    :data:`BOOKKEEPING_REGISTRATION_CHANGE`. It compares the two versions of
    the file as syntax trees. The narrowing holds only when the ONLY
    difference is the elements of a module-level literal collection that is
    named in :data:`REGISTRATION_CONTAINERS` -- a committed list of the
    containers that declare WHAT EXISTS rather than what a computation should
    return. An expectation table that happens to be a literal set is not in
    that list and is not narrowed.

3.  :data:`VALIDATION_MATRIX` maps each class to the validations it owes and
    says whether assembly and a full regression are mandatory. The decision
    over a whole change is the STRICTEST row any changed file selects.

WHAT THIS MODULE MAY NEVER DO
-----------------------------
Skip a full regression it is not certain about. Three separate rules enforce
that, and :mod:`tests.pettripfinder.test_regression_delta_001` proves each one:

    * an unmatched path is UNCLASSIFIED and UNCLASSIFIED requires full
    * a test-file change is only narrowed on the syntax-tree proof above
    * the whole-change decision is the OR of every row, so one dangerous file
      among a hundred harmless ones still costs a full regression
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"
PTF_TESTS = TESTS_DIR / "pettripfinder"

if str(REPO_ROOT) not in sys.path:                       # pragma: no cover
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import regression_lanes as LANES_MODULE   # noqa: E402

SCHEMA_MATRIX = "ptf-validation-matrix/1.0"
SCHEMA_CLASSIFICATION = "ptf-change-classification/1.0"
SCHEMA_DELTA = "ptf-regression-delta/1.0"
SCHEMA_CLOSURE = "ptf-failure-closure/1.0"

#: Where the machine-readable matrix is committed. The human-readable half is
#: the POST-BROAD FIX RULE section of docs/PTF_HARDENED_FACTORY_RUNBOOK.md.
MATRIX_PATH = (REPO_ROOT / "launch_packages" / "pettripfinder" /
               "regression_validation_matrix.json")

#: Where a durable failure-closure artifact is written.
CLOSURES_DIR = REPO_ROOT / "launch_packages" / "pettripfinder" / "failure_closures"

WORKTREE = "WORKTREE"

# --------------------------------------------------------------------------- #
# Phase 2: the change classes.
# --------------------------------------------------------------------------- #

AUTHORITY_CHANGE = "AUTHORITY_CHANGE"
GENERIC_RUNTIME_CHANGE = "GENERIC_RUNTIME_CHANGE"
SCHEMA_CHANGE = "SCHEMA_CHANGE"
ROUTING_SEMANTIC_CHANGE = "ROUTING_SEMANTIC_CHANGE"
DEPLOYMENT_CHANGE = "DEPLOYMENT_CHANGE"
TEST_EXPECTATION_CHANGE = "TEST_EXPECTATION_CHANGE"
BOOKKEEPING_REGISTRATION_CHANGE = "BOOKKEEPING_REGISTRATION_CHANGE"
DOCUMENTATION_ONLY = "DOCUMENTATION_ONLY"
GENERATED_REPORT_ONLY = "GENERATED_REPORT_ONLY"
BASELINE_MANIFEST_ONLY = "BASELINE_MANIFEST_ONLY"
UNCLASSIFIED = "UNCLASSIFIED"

CHANGE_CLASSES: Tuple[str, ...] = (
    AUTHORITY_CHANGE, GENERIC_RUNTIME_CHANGE, SCHEMA_CHANGE,
    ROUTING_SEMANTIC_CHANGE, DEPLOYMENT_CHANGE, TEST_EXPECTATION_CHANGE,
    BOOKKEEPING_REGISTRATION_CHANGE, DOCUMENTATION_ONLY,
    GENERATED_REPORT_ONLY, BASELINE_MANIFEST_ONLY, UNCLASSIFIED,
)

REQUIRED = "required"
NOT_REQUIRED = "not_required"
CONDITIONAL = "conditional"

# --------------------------------------------------------------------------- #
# Phase 4: the validation matrix.
#
# Each row says what the class touches, what it owes, and whether assembly and
# a broad regression are mandatory. ``lanes`` are lanes of
# :mod:`regression_lanes`; the boolean selectors add targets that no lane
# table can know in advance.
# --------------------------------------------------------------------------- #

#: change_class -> row. Keys, in order:
#:   surface              what the class can reach
#:   lanes                regression_lanes lanes the class owes
#:   owning_modules       run the changed test modules themselves
#:   owning_directory     run the changed test module's directory
#:   reverse_dependents   run every test module that imports the changed module
#:   market_targeted      add the market_targeted lane for markets the change names
#:   assembly             required / not_required
#:   full_regression      required / not_required / conditional
#:   condition            when ``full_regression`` is conditional, the test
#:   why                  the reason the row is what it is
VALIDATION_MATRIX: "OrderedDict[str, OrderedDict]" = OrderedDict((
    (AUTHORITY_CHANGE, OrderedDict((
        ("surface", "a market's own authority: its shard, its census and "
                    "partition, its release contract, the three generated "
                    "globals, and every profile the assembler renders from them"),
        ("lanes", (LANES_MODULE.POLICY_SCHEMA, LANES_MODULE.IDENTITY_ROUTING,
                   LANES_MODULE.RELEASE_CONTRACT, LANES_MODULE.CROSS_MARKET)),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", True),
        ("assembly", REQUIRED),
        ("full_regression", REQUIRED),
        ("condition", ""),
        ("why", "authority is what the site publishes; a wrong row reaches a "
                "reader, and the per-market contract rows and cross-market "
                "isolation gates are the only proof it did not leak"),
    ))),
    (GENERIC_RUNTIME_CHANGE, OrderedDict((
        ("surface", "shared runtime every market executes: readers, "
                    "assemblers, builders, ledgers, the acquisition router"),
        ("lanes", (LANES_MODULE.POLICY_SCHEMA, LANES_MODULE.IDENTITY_ROUTING,
                   LANES_MODULE.RELEASE_CONTRACT, LANES_MODULE.CROSS_MARKET,
                   LANES_MODULE.ASSEMBLY,
                   LANES_MODULE.DEPLOYMENT_ARCHITECTURE)),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", False),
        ("assembly", REQUIRED),
        ("full_regression", REQUIRED),
        ("condition", ""),
        ("why", "one edit changes what ELEVEN markets derive; the blast "
                "radius is the suite by definition, so the broad regression "
                "is the proof rather than the discovery"),
    ))),
    (SCHEMA_CHANGE, OrderedDict((
        ("surface", "the policy record contract and everything that reads, "
                    "validates or renders it"),
        ("lanes", (LANES_MODULE.POLICY_SCHEMA, LANES_MODULE.RELEASE_CONTRACT,
                   LANES_MODULE.ASSEMBLY)),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", False),
        ("assembly", REQUIRED),
        ("full_regression", REQUIRED),
        ("condition", ""),
        ("why", "a shape the renderer cannot carry is fatal at assembly and "
                "silent everywhere else; service_animal_statement proved it"),
    ))),
    (ROUTING_SEMANTIC_CHANGE, OrderedDict((
        ("surface", "identity keys, census partitions, geography, corridor "
                    "assignment and route derivation"),
        ("lanes", (LANES_MODULE.IDENTITY_ROUTING, LANES_MODULE.CROSS_MARKET,
                   LANES_MODULE.RELEASE_CONTRACT)),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", True),
        ("assembly", REQUIRED),
        ("full_regression", REQUIRED),
        ("condition", ""),
        ("why", "a route is an identity's public address; moving one silently "
                "retires a live URL, and only the assembled sitemap shows it"),
    ))),
    (DEPLOYMENT_CHANGE, OrderedDict((
        ("surface", "deployment authorizations, deployment records, release "
                    "contracts, the production manifest and launch participation"),
        ("lanes", (LANES_MODULE.DEPLOYMENT_ARCHITECTURE,
                   LANES_MODULE.RELEASE_CONTRACT, LANES_MODULE.ASSEMBLY)),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", False),
        ("assembly", REQUIRED),
        ("full_regression", REQUIRED),
        ("condition", ""),
        ("why", "deployment doctrine: what the record claims is served must be "
                "what a fresh assembly builds, and nothing narrower proves it"),
    ))),
    (TEST_EXPECTATION_CHANGE, OrderedDict((
        ("surface", "what a suite asserts -- an epoch pin, a count, a hash, a "
                    "restated site"),
        ("lanes", ()),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", True),
        ("assembly", NOT_REQUIRED),
        ("full_regression", CONDITIONAL),
        ("condition", "required when the changed expectation is a SHARED "
                      "current-state fact -- anything under tests/pettripfinder/"
                      "pins/, conftest.py, or a helper module imported by other "
                      "suites; not required when the change is confined to the "
                      "modules it owns"),
        ("why", "growing a package broke 85 tests in 19 modules once already; "
                "a shared pin moves suites that never name it, and only the "
                "broad run finds them"),
    ))),
    (BOOKKEEPING_REGISTRATION_CHANGE, OrderedDict((
        ("surface", "a declaration of WHAT EXISTS -- run ids, excused "
                    "directories -- inside one module-level literal collection "
                    "in one test file, proven by syntax tree to have changed "
                    "nothing else"),
        ("lanes", ()),
        ("owning_modules", True),
        ("owning_directory", True),
        ("reverse_dependents", True),
        ("market_targeted", True),
        ("assembly", NOT_REQUIRED),
        ("full_regression", NOT_REQUIRED),
        ("condition", ""),
        ("why", "the declaration is read by the module that declares it and by "
                "nothing else; no runtime executes it, no authority derives "
                "from it, and the assembled bundle cannot observe it"),
    ))),
    (DOCUMENTATION_ONLY, OrderedDict((
        ("surface", "prose: runbooks, work-order reports, README text"),
        ("lanes", ()),
        ("owning_modules", False),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", False),
        ("assembly", NOT_REQUIRED),
        ("full_regression", NOT_REQUIRED),
        ("condition", ""),
        ("why", "no suite reads prose; the reverse-dependent scan is kept "
                "because a doc under docs/ is occasionally asserted verbatim"),
    ))),
    (GENERATED_REPORT_ONLY, OrderedDict((
        ("surface", "an artifact a script emitted: a run report, a founder "
                    "packet, an evidence manifest"),
        ("lanes", ()),
        ("owning_modules", False),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", True),
        ("assembly", NOT_REQUIRED),
        ("full_regression", NOT_REQUIRED),
        ("condition", ""),
        ("why", "a report is an output, never an input to authority; the "
                "modules that pin one are found by the reverse-dependent scan"),
    ))),
    (BASELINE_MANIFEST_ONLY, OrderedDict((
        ("surface", "a committed regression baseline manifest"),
        ("lanes", ()),
        ("owning_modules", False),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", False),
        ("assembly", NOT_REQUIRED),
        ("full_regression", NOT_REQUIRED),
        ("condition", ""),
        ("why", "a manifest records what a past run did; it cannot change what "
                "the next run does, and the classifier self-test is the only "
                "thing that reads it"),
    ))),
    (UNCLASSIFIED, OrderedDict((
        ("surface", "unknown -- no rule claims this path"),
        ("lanes", tuple(l for l in LANES_MODULE.LANES
                        if l != LANES_MODULE.FULL_REGRESSION
                        and l != LANES_MODULE.MARKET_TARGETED)),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", False),
        ("assembly", REQUIRED),
        ("full_regression", REQUIRED),
        ("condition", ""),
        ("why", "uncertainty is not a narrow class; a path nobody taught this "
                "module about costs the full suite until somebody does"),
    ))),
))

#: Classes whose full-regression answer is a hard yes. Kept as a set so a new
#: row cannot quietly become skippable by editing prose.
MANDATORY_FULL_REGRESSION: Tuple[str, ...] = tuple(
    c for c, row in VALIDATION_MATRIX.items()
    if row["full_regression"] == REQUIRED)

#: Classes that never require one on their own.
SAFE_NARROW_CLASSES: Tuple[str, ...] = tuple(
    c for c, row in VALIDATION_MATRIX.items()
    if row["full_regression"] == NOT_REQUIRED)


# --------------------------------------------------------------------------- #
# Phase 3: path rules.
#
# ("prefix"|"glob", pattern, classes). First match wins; a glob is matched
# against the whole repo-relative posix path with fnmatch, a prefix against
# the leading path segments. Ordered most specific first.
# --------------------------------------------------------------------------- #

PATH_RULES: Tuple[Tuple[str, str, Tuple[str, ...]], ...] = (
    # -- baseline manifests, before the launch_packages authority rules ------
    ("prefix", "launch_packages/pettripfinder/regression_baselines/",
     (BASELINE_MANIFEST_ONLY,)),
    ("prefix", "launch_packages/pettripfinder/failure_closures/",
     (GENERATED_REPORT_ONLY,)),
    ("glob", "launch_packages/pettripfinder/regression_validation_matrix.json",
     (GENERIC_RUNTIME_CHANGE,)),

    # -- deployment, before the generic launch_packages rules ----------------
    ("prefix", "deploy/", (DEPLOYMENT_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/launch_participation.json",
     (DEPLOYMENT_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/*deployment_packet*.json",
     (DEPLOYMENT_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/*deployment_manifest*.json",
     (DEPLOYMENT_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/ptf_market_manifest*.json",
     (DEPLOYMENT_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/markets/manifest*.json",
     (DEPLOYMENT_CHANGE,)),

    # -- authority ------------------------------------------------------------
    ("prefix", "launch_packages/pettripfinder/markets/authority/",
     (AUTHORITY_CHANGE,)),
    ("prefix", "launch_packages/pettripfinder/markets/name_corrections/",
     (AUTHORITY_CHANGE,)),
    ("prefix", "launch_packages/pettripfinder/markets/founder_overrides/",
     (AUTHORITY_CHANGE,)),
    ("prefix", "launch_packages/pettripfinder/markets/coverage/",
     (AUTHORITY_CHANGE,)),
    ("prefix", "launch_packages/pettripfinder/markets/discovered_policy_urls/",
     (AUTHORITY_CHANGE,)),
    ("prefix", "launch_packages/pettripfinder/identity_census",
     (AUTHORITY_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "launch_packages/pettripfinder/hotel_policy_facts*.json",
     (AUTHORITY_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/hotel_exclusions*.json",
     (AUTHORITY_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/identity_routing*.json",
     (AUTHORITY_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "launch_packages/pettripfinder/*seed_businesses*.csv",
     (AUTHORITY_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/ptf_global_authority_manifest.json",
     (AUTHORITY_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/*_final_partition_*.json",
     (AUTHORITY_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "launch_packages/pettripfinder/*_census_*.json",
     (AUTHORITY_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "launch_packages/pettripfinder/markets/*.json", (AUTHORITY_CHANGE,)),

    # -- generated artifacts, AFTER the authority rules ----------------------
    #
    #    These four rules are deliberately NARROW. The rest of
    #    launch_packages/pettripfinder/ -- five hundred capture results,
    #    founder packets, ledgers and snapshots -- stays UNCLASSIFIED, and
    #    UNCLASSIFIED costs a full regression. That is not an oversight to be
    #    tidied up with a blanket rule: a packet a founder ruled on and a
    #    census partition sit side by side in that directory under names that
    #    do not distinguish them, and the cheap way to tell them apart is the
    #    one this module refuses to use.
    ("prefix", "launch_packages/pettripfinder/markets/reports/",
     (GENERATED_REPORT_ONLY,)),
    ("prefix", "launch_packages/pettripfinder/reports/",
     (GENERATED_REPORT_ONLY,)),
    ("glob", "launch_packages/pettripfinder/*_report_*.json",
     (GENERATED_REPORT_ONLY,)),
    ("glob", "launch_packages/pettripfinder/*_packet_*.json",
     (GENERATED_REPORT_ONLY,)),
    ("glob", "launch_packages/pettripfinder/*_verification_*.json",
     (GENERATED_REPORT_ONLY,)),
    ("glob", "launch_packages/pettripfinder/*_queue*.json",
     (GENERATED_REPORT_ONLY,)),

    # -- tests ----------------------------------------------------------------
    #    pins are shared current state; conftest and non-test helpers are
    #    imported by suites that never name them. Both stay TEST_EXPECTATION
    #    and both are shared, which the conditional rule below reads.
    ("prefix", "tests/", (TEST_EXPECTATION_CHANGE,)),

    # -- runtime --------------------------------------------------------------
    ("prefix", "scripts/pettripfinder/contracts/",
     (GENERIC_RUNTIME_CHANGE, SCHEMA_CHANGE)),
    ("prefix", "scripts/pettripfinder/acquisition/",
     (GENERIC_RUNTIME_CHANGE,)),
    ("prefix", "scripts/pettripfinder/brightdata/", (GENERIC_RUNTIME_CHANGE,)),
    ("prefix", "scripts/pettripfinder/discovery/",
     (GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "scripts/pettripfinder/*polic*.py",
     (GENERIC_RUNTIME_CHANGE, SCHEMA_CHANGE)),
    ("glob", "scripts/pettripfinder/*reader*.py",
     (GENERIC_RUNTIME_CHANGE, SCHEMA_CHANGE)),
    ("glob", "scripts/pettripfinder/*render*.py",
     (GENERIC_RUNTIME_CHANGE, SCHEMA_CHANGE)),
    ("glob", "scripts/pettripfinder/approved_hotel_profile.py",
     (GENERIC_RUNTIME_CHANGE, SCHEMA_CHANGE)),
    ("glob", "scripts/pettripfinder/*identity*.py",
     (GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "scripts/pettripfinder/*routing*.py",
     (GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "scripts/pettripfinder/census_*.py",
     (GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "scripts/pettripfinder/*corridor*.py",
     (GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE)),
    ("glob", "scripts/pettripfinder/assemble_*.py",
     (GENERIC_RUNTIME_CHANGE, DEPLOYMENT_CHANGE)),
    ("glob", "scripts/pettripfinder/build_market_manifest.py",
     (GENERIC_RUNTIME_CHANGE, DEPLOYMENT_CHANGE)),
    ("glob", "scripts/pettripfinder/*deploy*.py",
     (GENERIC_RUNTIME_CHANGE, DEPLOYMENT_CHANGE)),
    ("glob", "scripts/pettripfinder/release_contracts.py",
     (GENERIC_RUNTIME_CHANGE, DEPLOYMENT_CHANGE)),
    ("prefix", "scripts/pettripfinder/", (GENERIC_RUNTIME_CHANGE,)),
    ("prefix", "scripts/", (GENERIC_RUNTIME_CHANGE,)),

    # -- prose ----------------------------------------------------------------
    ("prefix", "docs/", (DOCUMENTATION_ONLY,)),
    ("glob", "*.md", (DOCUMENTATION_ONLY,)),

    # -- outside the package: the git root, where work-order reports live -----
    ("glob", "../*.md", (DOCUMENTATION_ONLY,)),
    ("glob", "../.gitignore", (DOCUMENTATION_ONLY,)),
    ("prefix", "../", (UNCLASSIFIED,)),
)

#: Test paths whose expectations are SHARED current state. A change to one of
#: these makes TEST_EXPECTATION_CHANGE's conditional full regression a yes.
#: Everything else under tests/ is owned by the modules that name it.
SHARED_TEST_STATE: Tuple[Tuple[str, str], ...] = (
    ("prefix", "tests/pettripfinder/pins/"),
    ("prefix", "tests/pettripfinder/fixtures/"),
    ("glob", "tests/**/conftest.py"),
    ("glob", "tests/pettripfinder/epochs.py"),
    ("glob", "tests/pettripfinder/market_state.py"),
    ("glob", "tests/pettripfinder/**/authority_freeze.py"),
    ("glob", "tests/pettripfinder/**/locator_freeze.py"),
    ("glob", "tests/pettripfinder/**/reader_freeze.py"),
)


# --------------------------------------------------------------------------- #
# Phase 3: the registration containers a test change may be narrowed to.
# --------------------------------------------------------------------------- #

#: (module path relative to tests/, container name, what it declares).
#:
#: A container belongs here when its elements name THINGS THAT EXIST -- a run
#: directory on disk, a file, an id -- rather than a value a computation is
#: expected to produce. That distinction is the whole safety argument: adding
#: "cincinnati_oh_firecrawl_001" to a list of run directories another market
#: owns cannot change any assertion's answer except the one that reads the
#: directory listing. Adding a number to an expectations table can.
#:
#: Node ids, not patterns, so a rename fails loudly in
#: ``test_every_registration_container_exists``.
REGISTRATION_CONTAINERS: Tuple[Tuple[str, str, str], ...] = (
    ("pettripfinder/acquisition/test_store_integration_025.py",
     "OTHER_MARKET_RUNS",
     "directories under data/acquisition/ that belong to another market and "
     "must stay out of Milwaukee's projection; every new market drops one here"),
)


def registration_containers_for(test_relpath: str) -> Tuple[str, ...]:
    """Container names this test module may have narrowed, in order."""
    rel = test_relpath.replace("\\", "/")
    if rel.startswith("tests/"):
        rel = rel[len("tests/"):]
    return tuple(name for path, name, _why in REGISTRATION_CONTAINERS
                 if path == rel)


# --------------------------------------------------------------------------- #
# Path classification.
# --------------------------------------------------------------------------- #

def _posix(path: str) -> str:
    out = str(path).replace("\\", "/")
    while out.startswith("./"):
        out = out[2:]
    return out


_GLOB_CACHE: Dict[str, "re.Pattern"] = {}


def _glob_regex(pattern: str) -> "re.Pattern":
    """A glob where ``*`` stops at a directory boundary.

    ``fnmatch`` lets ``*`` swallow slashes, which silently made
    ``markets/*.json`` claim ``markets/reports/*.json`` -- an authority rule
    eating a generated artifact, in the direction that matters least, and it
    would have eaten the other direction just as happily. ``**/`` spans
    directories explicitly and nothing else does.
    """
    cached = _GLOB_CACHE.get(pattern)
    if cached is not None:
        return cached
    parts: List[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if pattern[index:index + 3] == "**/":
                parts.append("(?:[^/]+/)*")
                index += 3
                continue
            if pattern[index:index + 2] == "**":
                parts.append(".*")
                index += 2
                continue
            parts.append("[^/]*")
        elif char == "?":
            parts.append("[^/]")
        else:
            parts.append(re.escape(char))
        index += 1
    compiled = re.compile("^" + "".join(parts) + "$")
    _GLOB_CACHE[pattern] = compiled
    return compiled


def _matches(kind: str, pattern: str, relpath: str) -> bool:
    if kind == "prefix":
        return relpath.startswith(pattern)
    if kind == "glob":
        return _glob_regex(pattern).match(relpath) is not None
    raise ValueError("unknown rule kind %r" % kind)


def classify_path(relpath: str) -> Tuple[Tuple[str, ...], str]:
    """``(classes, matched rule)`` for one repo-relative path.

    Pure path, no diff. A path no rule claims is :data:`UNCLASSIFIED`.
    """
    rel = _posix(relpath)
    for kind, pattern, classes in PATH_RULES:
        if _matches(kind, pattern, rel):
            return classes, "%s:%s" % (kind, pattern)
    return (UNCLASSIFIED,), "no rule"


def is_shared_test_state(relpath: str) -> bool:
    """Does this test path hold expectations OTHER suites depend on?"""
    rel = _posix(relpath)
    return any(_matches(kind, pattern, rel) for kind, pattern in SHARED_TEST_STATE)


# --------------------------------------------------------------------------- #
# Semantic refinement: the ONE narrowing this module permits.
# --------------------------------------------------------------------------- #

def _strip_module_docstring(body: List[ast.stmt]) -> List[ast.stmt]:
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(getattr(body[0], "value", None), ast.Constant)
            and isinstance(body[0].value.value, str)):
        return body[1:]
    return list(body)


def _module_shape(source: str) -> "OrderedDict[str, str]":
    """Module-level statements as ``key -> dumped ast``.

    Assignments to a single plain name are keyed by that name so an edit to
    one container is visible as exactly one differing key. Everything else is
    keyed positionally, so inserting or removing any other statement changes
    the key set and cannot be narrowed.
    """
    tree = ast.parse(source)
    shape: "OrderedDict[str, str]" = OrderedDict()
    for index, node in enumerate(_strip_module_docstring(tree.body)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            key = "def:%s" % node.name
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            key = "assign:%s" % node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            key = "assign:%s" % node.target.id
        else:
            key = "stmt:%03d:%s" % (index, type(node).__name__)
        if key in shape:                       # two defs of one name: positional
            key = "%s#%03d" % (key, index)
        shape[key] = ast.dump(node)
    return shape


def _assigned_value(source: str, name: str) -> Optional[ast.AST]:
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id == name:
            return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == name:
            return node.value
    return None


def _constantish(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_constantish(e) for e in node.elts)
    return False


def literal_elements(node: Optional[ast.AST]) -> Optional[Tuple]:
    """The elements of a literal collection of constants, or ``None``.

    ``None`` means "not a literal collection I will vouch for" -- a call, a
    comprehension, a name, a nested non-constant. Conservative on purpose.
    """
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        if not all(_constantish(e) for e in node.elts):
            return None
        return tuple(ast.dump(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        pairs = []
        for key, value in zip(node.keys, node.values):
            if key is None or not isinstance(key, ast.Constant):
                return None
            if not _constantish(value):
                return None
            pairs.append((ast.dump(key), ast.dump(value)))
        return tuple(pairs)
    return None


def refine_test_change(relpath: str, base_source: Optional[str],
                       head_source: Optional[str]) -> Tuple[str, str]:
    """``(class, why)`` for a changed test file.

    Returns :data:`BOOKKEEPING_REGISTRATION_CHANGE` only when every one of
    these holds, and :data:`TEST_EXPECTATION_CHANGE` otherwise:

        * the file exists on both sides and both parse
        * the module-level shapes differ in at least one key and ONLY in
          ``assign:<NAME>`` keys -- no def, no class, no import, no other
          statement, and no key added or removed
        * every differing name is declared in :data:`REGISTRATION_CONTAINERS`
          for this module
        * both versions of every differing name are literal collections of
          constants, and they actually differ in their elements
    """
    if base_source is None or head_source is None:
        return TEST_EXPECTATION_CHANGE, ("added or deleted module: there is no "
                                         "prior shape to compare against")
    allowed = registration_containers_for(relpath)
    if not allowed:
        return TEST_EXPECTATION_CHANGE, ("no registration container is declared "
                                         "for this module")
    try:
        base_shape = _module_shape(base_source)
        head_shape = _module_shape(head_source)
    except SyntaxError as exc:
        return TEST_EXPECTATION_CHANGE, "could not parse both versions: %s" % exc

    if set(base_shape) != set(head_shape):
        added = sorted(set(head_shape) - set(base_shape))
        removed = sorted(set(base_shape) - set(head_shape))
        return TEST_EXPECTATION_CHANGE, (
            "module-level statements were added or removed (added=%s removed=%s)"
            % (added or "none", removed or "none"))

    differing = [k for k in head_shape if head_shape[k] != base_shape[k]]
    if not differing:
        return TEST_EXPECTATION_CHANGE, ("no syntax-tree difference: the change "
                                         "is comment or whitespace only, which "
                                         "this module does not vouch for")
    non_assign = [k for k in differing if not k.startswith("assign:")]
    if non_assign:
        return TEST_EXPECTATION_CHANGE, (
            "code changed outside a module-level assignment: %s"
            % ", ".join(sorted(non_assign)))

    names = [k[len("assign:"):] for k in differing]
    outside = [n for n in names if n not in allowed]
    if outside:
        return TEST_EXPECTATION_CHANGE, (
            "changed containers are not declared registrations: %s"
            % ", ".join(sorted(outside)))

    for name in names:
        before = literal_elements(_assigned_value(base_source, name))
        after = literal_elements(_assigned_value(head_source, name))
        if before is None or after is None:
            return TEST_EXPECTATION_CHANGE, (
                "%s is not a literal collection of constants on both sides"
                % name)
        if before == after:
            return TEST_EXPECTATION_CHANGE, (
                "%s dumped differently but its elements are identical" % name)
    return BOOKKEEPING_REGISTRATION_CHANGE, (
        "only the elements of declared registration container(s) %s changed; "
        "no def, class, import or other module-level statement differs"
        % ", ".join(sorted(names)))


# --------------------------------------------------------------------------- #
# git plumbing.
# --------------------------------------------------------------------------- #

def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(REPO_ROOT.parent),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args),
                                                  proc.stderr.strip()))
    return proc.stdout


def _repo_prefix() -> str:
    """``atlas-dashboard/`` -- paths in git are relative to the git root."""
    return REPO_ROOT.name + "/"


def resolve_sha(rev: str) -> str:
    if rev == WORKTREE:
        return WORKTREE
    return _git("rev-parse", rev).strip()


def changed_files(base: str, head: str = WORKTREE) -> "OrderedDict[str, str]":
    """``repo-relative path -> git status letter`` between two revisions.

    ``head`` may be :data:`WORKTREE`, which compares the working tree -- staged,
    unstaged and untracked-but-not-ignored -- against ``base``. Paths are
    returned relative to :data:`REPO_ROOT`; anything outside it is skipped,
    because nothing outside it is part of the factory.
    """
    prefix = _repo_prefix()
    out: "OrderedDict[str, str]" = OrderedDict()

    def _add(status: str, git_path: str) -> None:
        path = git_path.replace("\\", "/")
        if path.startswith(prefix):
            out.setdefault(path[len(prefix):], status)
        else:
            # The git root holds the work-order reports, one level above the
            # package. They are still part of the change and are classified
            # rather than dropped -- a file this module cannot see is a file
            # it cannot require a full regression for.
            out.setdefault("../" + path, status)

    if head == WORKTREE:
        raw = _git("diff", "--name-status", base, "--")
        untracked = _git("ls-files", "--others", "--exclude-standard")
        for line in untracked.splitlines():
            if line.strip():
                _add("A", line.strip())
    else:
        raw = _git("diff", "--name-status", "%s..%s" % (base, head), "--")
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][:1]
        _add(status, parts[-1])
    return OrderedDict(sorted(out.items()))


def read_at(rev: str, relpath: str) -> Optional[str]:
    """The text of ``relpath`` at ``rev``, or ``None`` when it is absent."""
    if rev == WORKTREE:
        path = REPO_ROOT / relpath
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    proc = subprocess.run(
        ["git", "show", "%s:%s%s" % (rev, _repo_prefix(), relpath)],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return proc.stdout


# --------------------------------------------------------------------------- #
# Whole-change classification.
# --------------------------------------------------------------------------- #

def _markets_named(text: str) -> Tuple[str, ...]:
    """Markets a path or a diff body names, by market id or underscore form."""
    lowered = text.lower().replace("\\", "/")
    found: List[str] = []
    for market in LANES_MODULE.MARKET_PREFIXES:
        if market in lowered or market.replace("-", "_") in lowered:
            found.append(market)
    return tuple(found)


def _market_for_test_path(relpath: str) -> Optional[str]:
    rel = _posix(relpath)
    if not rel.startswith("tests/pettripfinder/"):
        return None
    return LANES_MODULE.market_for(rel[len("tests/pettripfinder/"):])


def classify_change(base: str, head: str = WORKTREE,
                    paths: Optional[Mapping[str, str]] = None) -> Dict:
    """Classify every changed path, refining test files by syntax tree."""
    files = OrderedDict(paths) if paths is not None else changed_files(base, head)
    rows: List[Dict] = []
    for relpath, status in files.items():
        classes, rule = classify_path(relpath)
        why = "matched %s" % rule
        shared = False
        if classes == (TEST_EXPECTATION_CHANGE,) and relpath.endswith(".py"):
            refined, refined_why = refine_test_change(
                relpath, read_at(base, relpath), read_at(head, relpath))
            classes = (refined,)
            why = refined_why
        if TEST_EXPECTATION_CHANGE in classes:
            shared = is_shared_test_state(relpath)
        markets = _markets_named(relpath)
        if not markets and relpath.endswith(".py"):
            market = _market_for_test_path(relpath)
            if market:
                markets = (market,)
        if not markets and BOOKKEEPING_REGISTRATION_CHANGE in classes:
            # The registration's own elements name the market it registers.
            head_source = read_at(head, relpath) or ""
            base_source = read_at(base, relpath) or ""
            added = set(head_source.splitlines()) - set(base_source.splitlines())
            markets = _markets_named("\n".join(sorted(added)))
        rows.append(OrderedDict((
            ("path", relpath),
            ("status", status),
            ("classes", list(classes)),
            ("rule", rule),
            ("why", why),
            ("shared_test_state", shared),
            ("markets", list(markets)),
        )))
    classes_seen: List[str] = []
    for row in rows:
        for cls in row["classes"]:
            if cls not in classes_seen:
                classes_seen.append(cls)
    ordered = [c for c in CHANGE_CLASSES if c in classes_seen]
    return OrderedDict((
        ("schema", SCHEMA_CLASSIFICATION),
        ("base", base),
        ("base_sha", resolve_sha(base)),
        ("head", head),
        ("head_sha", resolve_sha(head)),
        ("changed_file_count", len(rows)),
        ("changed_files", rows),
        ("change_classes", ordered),
    ))


# --------------------------------------------------------------------------- #
# The plan a classification owes.
# --------------------------------------------------------------------------- #

def _test_modules() -> List[str]:
    return ["tests/pettripfinder/" + LANES_MODULE._relpath(p)
            for p in sorted(PTF_TESTS.rglob("test_*.py"))]


_TEST_SOURCES: Optional["OrderedDict[str, str]"] = None


def _test_sources() -> "OrderedDict[str, str]":
    """``module path -> source``, read once per process.

    A change with a hundred files would otherwise re-read six hundred test
    modules a hundred times.
    """
    global _TEST_SOURCES
    if _TEST_SOURCES is None:
        sources: "OrderedDict[str, str]" = OrderedDict()
        for module in _test_modules():
            try:
                sources[module] = (REPO_ROOT / module).read_text(
                    encoding="utf-8-sig", errors="replace")
            except OSError:                              # pragma: no cover
                continue
        _TEST_SOURCES = sources
    return _TEST_SOURCES


def reverse_dependents(relpath: str) -> List[str]:
    """Test modules whose source names the changed module's importable stem.

    A cheap, over-inclusive reverse-import scan: it finds ``from .x import``,
    ``import x`` and a bare mention in a path string alike. Over-inclusive is
    the safe direction -- it can only add tests to a narrow run.
    """
    stem = Path(_posix(relpath)).stem
    if not stem or stem in ("__init__", "conftest"):
        return []
    return [module for module, text in _test_sources().items()
            if _posix(module) != _posix(relpath) and stem in text]


def plan_for(classification: Mapping) -> Dict:
    """The validations a classification owes, and the two verdicts."""
    lanes: List[str] = []
    modules: List[str] = []
    markets: List[str] = []
    reasons: List[Dict] = []
    assembly = NOT_REQUIRED
    full = NOT_REQUIRED

    def _need(current: str, wanted: str) -> str:
        rank = {NOT_REQUIRED: 0, CONDITIONAL: 1, REQUIRED: 2}
        return current if rank[current] >= rank[wanted] else wanted

    for row in classification["changed_files"]:
        for cls in row["classes"]:
            matrix = VALIDATION_MATRIX[cls]
            for lane in matrix["lanes"]:
                if lane not in lanes:
                    lanes.append(lane)
            if matrix["owning_modules"] and row["path"].startswith("tests/") \
                    and row["path"].endswith(".py") \
                    and (REPO_ROOT / row["path"]).is_file():
                if row["path"] not in modules:
                    modules.append(row["path"])
            if matrix["owning_directory"] and row["path"].startswith("tests/"):
                parent = str(Path(row["path"]).parent).replace("\\", "/")
                if parent not in modules:
                    modules.append(parent)
            if matrix["reverse_dependents"]:
                for dependent in reverse_dependents(row["path"]):
                    if dependent not in modules:
                        modules.append(dependent)
            if matrix["market_targeted"]:
                for market in row["markets"]:
                    if market not in markets:
                        markets.append(market)
            assembly = _need(assembly, matrix["assembly"])
            decision = matrix["full_regression"]
            if decision == CONDITIONAL:
                decision = REQUIRED if row["shared_test_state"] else NOT_REQUIRED
                detail = ("%s is shared current state" % row["path"]
                          if row["shared_test_state"]
                          else "%s is owned by the modules that name it"
                               % row["path"])
            else:
                detail = matrix["why"]
            full = _need(full, decision)
            reasons.append(OrderedDict((
                ("path", row["path"]),
                ("change_class", cls),
                ("full_regression", decision),
                ("assembly", matrix["assembly"]),
                ("why", detail),
            )))

    for market in markets:
        for module in LANES_MODULE.modules_in_lane(
                LANES_MODULE.MARKET_TARGETED, market=market):
            if module not in modules:
                modules.append(module)
    for lane in lanes:
        for module in LANES_MODULE.modules_in_lane(lane):
            if module not in modules:
                modules.append(module)

    # A directory target subsumes the modules under it.
    directories = [m for m in modules if not m.endswith(".py")]
    modules = [m for m in modules
               if not any(m != d and m.startswith(d + "/") for d in directories)]

    return OrderedDict((
        ("lanes", lanes),
        ("markets", markets),
        ("modules", sorted(modules)),
        ("module_count", len(modules)),
        ("assembly_required", assembly == REQUIRED),
        ("full_regression_required", full == REQUIRED),
        ("full_regression_decision", full),
        ("reasons", reasons),
    ))


# --------------------------------------------------------------------------- #
# Running the plan and proving the closure.
# --------------------------------------------------------------------------- #

def run_statuses(run_dir: Path) -> Dict[str, str]:
    """``node id -> passed|failed|error|skipped`` over every junit in a dir."""
    cases: Dict[str, str] = {}
    for xml_path in sorted(Path(run_dir).glob("*.xml")):
        cases.update(LANES_MODULE._junit_cases(xml_path))
    return cases


def run_plan(plan: Mapping, *, out: Path,
             python: str = sys.executable) -> Dict:
    """Run the plan's modules in ONE pytest process into ``out/delta.xml``."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    targets = list(plan["modules"])
    if not targets:
        return OrderedDict((("collected", 0), ("passed", 0), ("skipped", 0),
                            ("failed", 0), ("seconds", 0.0), ("exit_code", 5),
                            ("failing_node_ids", []), ("targets", [])))
    deselect: List[str] = []
    for nodeid, _why in LANES_MODULE.DEFERRED_TO_FULL_REGRESSION:
        deselect += ["--deselect", nodeid]
    xml_path = out / "delta.xml"
    argv = [python, "-m", "pytest", *targets, "-q", "-p", "no:cacheprovider",
            "-o", "junit_family=xunit2", "--junitxml=%s" % xml_path, *deselect]
    started = time.monotonic()
    with open(out / "delta.log", "w", encoding="utf-8") as log:
        code = subprocess.call(argv, cwd=str(REPO_ROOT), stdout=log,
                               stderr=subprocess.STDOUT)
    seconds = round(time.monotonic() - started, 1)
    cases = run_statuses(out)
    failing = sorted(n for n, s in cases.items() if s in ("failed", "error"))
    return OrderedDict((
        ("collected", len(cases)),
        ("passed", sum(1 for s in cases.values() if s == "passed")),
        ("skipped", sum(1 for s in cases.values() if s == "skipped")),
        ("failed", len(failing)),
        ("seconds", seconds),
        ("exit_code", code),
        ("failing_node_ids", failing),
        ("targets", targets),
        ("statuses", cases),
    ))


#: A node id is proven closed only when the delta run EXECUTED it and it
#: passed. "Absent from the failure list" is not proof -- a node that was never
#: collected is absent too, which is exactly the count-based proof this order
#: forbids.
CLOSED = "CLOSED"
STILL_FAILING = "STILL_FAILING"
NOT_EXERCISED = "NOT_EXERCISED"


def prove_closure(required_closed: Sequence[str],
                  statuses: Mapping[str, str]) -> Dict:
    """Account for every node id the broad regression called TRUE_NEW."""
    results: "OrderedDict[str, str]" = OrderedDict()
    for nodeid in required_closed:
        status = statuses.get(nodeid)
        if status is None:
            results[nodeid] = NOT_EXERCISED
        elif status == "passed":
            results[nodeid] = CLOSED
        elif status == "skipped":
            results[nodeid] = NOT_EXERCISED
        else:
            results[nodeid] = STILL_FAILING
    return OrderedDict((
        ("required_closed", list(required_closed)),
        ("results", results),
        ("closed", [n for n, v in results.items() if v == CLOSED]),
        ("still_failing", [n for n, v in results.items() if v == STILL_FAILING]),
        ("not_exercised", [n for n, v in results.items() if v == NOT_EXERCISED]),
        ("all_accounted_for", bool(required_closed) and
         all(v == CLOSED for v in results.values())),
    ))


def classify_against_baseline(failing: Sequence[str],
                              baseline: Mapping) -> Dict:
    """PRE_EXISTING / RESOLVED / TRUE_NEW for a delta run.

    RESOLVED is scoped to what the delta run actually EXERCISED, because a
    narrow run cannot claim a node it never collected started passing.
    """
    pre = set(baseline["failing_node_ids"])
    failing_set = set(failing)
    pre_existing = sorted(failing_set & pre)
    true_new = sorted(failing_set - pre)
    return OrderedDict((
        ("baseline_source_sha", baseline["source_sha"]),
        ("PRE_EXISTING", pre_existing),
        ("TRUE_NEW", true_new),
        ("counts", OrderedDict((("PRE_EXISTING", len(pre_existing)),
                                ("TRUE_NEW", len(true_new))))),
    ))


def resolved_against_baseline(statuses: Mapping[str, str],
                              baseline: Mapping) -> List[str]:
    pre = set(baseline["failing_node_ids"])
    return sorted(n for n, s in statuses.items()
                  if n in pre and s == "passed")


def validate(base: str, head: str = WORKTREE, *, baseline: Optional[Mapping] = None,
             out: Optional[Path] = None, require_closed: Sequence[str] = (),
             plan_only: bool = False) -> Dict:
    """Classify, plan, run and prove -- the whole delta-scoped validation."""
    classification = classify_change(base, head)
    plan = plan_for(classification)
    doc: "OrderedDict[str, object]" = OrderedDict((
        ("schema", SCHEMA_DELTA),
        ("base", base),
        ("base_sha", classification["base_sha"]),
        ("head", head),
        ("head_sha", classification["head_sha"]),
        ("classification", classification),
        ("plan", plan),
        ("FULL_REGRESSION_REQUIRED", "YES" if plan["full_regression_required"]
         else "NO"),
        ("full_regression_reason", _full_reason(plan)),
    ))
    if plan_only or out is None:
        doc["run"] = None
        doc["clean"] = None
        return doc
    result = run_plan(plan, out=Path(out))
    statuses = dict(result.pop("statuses", {}))
    doc["run"] = result
    if baseline is not None:
        against = classify_against_baseline(result["failing_node_ids"], baseline)
        against["RESOLVED"] = resolved_against_baseline(statuses, baseline)
        against["counts"]["RESOLVED"] = len(against["RESOLVED"])
        doc["against_baseline"] = against
        true_new_ok = not against["TRUE_NEW"]
    else:
        doc["against_baseline"] = None
        true_new_ok = result["failed"] == 0
    if require_closed:
        closure = prove_closure(require_closed, statuses)
        doc["closure"] = closure
        closure_ok = closure["all_accounted_for"]
    else:
        doc["closure"] = None
        closure_ok = True
    doc["clean"] = bool(true_new_ok and closure_ok)
    return doc


def _full_reason(plan: Mapping) -> str:
    if not plan["full_regression_required"]:
        classes = sorted({r["change_class"] for r in plan["reasons"]})
        return ("every changed file classifies into a narrow class (%s); no row "
                "of the matrix makes a broad regression mandatory"
                % ", ".join(classes) if classes else
                "nothing changed")
    drivers = [r for r in plan["reasons"] if r["full_regression"] == REQUIRED]
    return "; ".join("%s (%s): %s" % (r["path"], r["change_class"], r["why"])
                     for r in drivers[:6]) or "unknown"


# --------------------------------------------------------------------------- #
# Documents.
# --------------------------------------------------------------------------- #

def matrix_document() -> Dict:
    """The committed, machine-readable matrix."""
    rows = []
    for change_class, row in VALIDATION_MATRIX.items():
        rows.append(OrderedDict((
            ("change_class", change_class),
            ("surface", row["surface"]),
            ("required_lanes", list(row["lanes"])),
            ("owning_modules", row["owning_modules"]),
            ("owning_directory", row["owning_directory"]),
            ("reverse_dependents", row["reverse_dependents"]),
            ("market_targeted", row["market_targeted"]),
            ("assembly", row["assembly"]),
            ("full_regression", row["full_regression"]),
            ("condition", row["condition"]),
            ("why", row["why"]),
        )))
    return OrderedDict((
        ("schema", SCHEMA_MATRIX),
        ("work_order", "PTF-FACTORY-REGRESSION-V2-001"),
        ("change_classes", list(CHANGE_CLASSES)),
        ("mandatory_full_regression", list(MANDATORY_FULL_REGRESSION)),
        ("safe_narrow_classes", list(SAFE_NARROW_CLASSES)),
        ("rows", rows),
        ("registration_containers", [
            OrderedDict((("module", m), ("container", c), ("declares", w)))
            for m, c, w in REGISTRATION_CONTAINERS]),
        ("path_rules", [OrderedDict((("kind", k), ("pattern", p),
                                     ("classes", list(c))))
                        for k, p, c in PATH_RULES]),
        ("shared_test_state", [OrderedDict((("kind", k), ("pattern", p)))
                               for k, p in SHARED_TEST_STATE]),
    ))


def closure_document(delta: Mapping, *, order: str, fix_commit: str,
                     rationale: str = "") -> Dict:
    """The durable artifact a post-broad fix leaves behind (Phase 7)."""
    classification = delta["classification"]
    plan = delta["plan"]
    closure = delta.get("closure") or {}
    run = delta.get("run") or {}
    return OrderedDict((
        ("schema", SCHEMA_CLOSURE),
        ("work_order", order),
        ("fix_commit_sha", fix_commit),
        ("base_sha", delta["base_sha"]),
        ("head", delta["head"]),
        ("head_sha", delta["head_sha"]),
        ("original_true_new_node_ids", list(closure.get("required_closed", []))),
        ("baseline_source_sha",
         (delta.get("against_baseline") or {}).get("baseline_source_sha")),
        ("changed_files", [OrderedDict((("path", r["path"]),
                                        ("status", r["status"]),
                                        ("classes", r["classes"]),
                                        ("why", r["why"])))
                           for r in classification["changed_files"]]),
        ("change_classes", list(classification["change_classes"])),
        ("required_validations", OrderedDict((
            ("lanes", list(plan["lanes"])),
            ("markets", list(plan["markets"])),
            ("modules", list(plan["modules"])),
            ("assembly_required", plan["assembly_required"]),
        ))),
        ("targeted_result", OrderedDict((
            ("collected", run.get("collected")),
            ("passed", run.get("passed")),
            ("skipped", run.get("skipped")),
            ("failed", run.get("failed")),
            ("seconds", run.get("seconds")),
        ))),
        ("node_id_results", closure.get("results", OrderedDict())),
        ("against_baseline", delta.get("against_baseline")),
        ("FULL_REGRESSION_REQUIRED", delta["FULL_REGRESSION_REQUIRED"]),
        ("full_regression_reason", delta["full_regression_reason"]),
        ("all_original_failures_accounted_for",
         bool(closure.get("all_accounted_for"))),
        ("rationale", rationale),
    ))


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #

def _read_json(path: Path) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write_json(path: Path, doc: Mapping) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")


def _print_matrix(doc: Mapping) -> None:
    print("%-32s %-9s %-9s %s" % ("CHANGE CLASS", "ASSEMBLY", "FULL", "LANES"))
    for row in doc["rows"]:
        print("%-32s %-9s %-9s %s" % (
            row["change_class"], row["assembly"], row["full_regression"],
            ", ".join(row["required_lanes"]) or "-"))
    print()
    print("mandatory full regression: %s"
          % ", ".join(doc["mandatory_full_regression"]))
    print("safe narrow classes:       %s"
          % ", ".join(doc["safe_narrow_classes"]))


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("matrix", help="print or export the validation matrix")
    s.add_argument("--json", action="store_true")
    s.add_argument("--out")

    s = sub.add_parser("classify", help="classify the changed paths only")
    s.add_argument("--base", required=True)
    s.add_argument("--head", default=WORKTREE)
    s.add_argument("--out")

    s = sub.add_parser("validate", help="classify, run the required lanes, "
                                        "and prove the closure by node id")
    s.add_argument("--base", required=True)
    s.add_argument("--head", default=WORKTREE)
    s.add_argument("--baseline")
    s.add_argument("--require-closed", action="append", default=[],
                   help="a node id the broad regression called TRUE_NEW; "
                        "repeatable, and every one must end CLOSED")
    s.add_argument("--out", help="directory for the junit + delta.json")
    s.add_argument("--plan-only", action="store_true")
    s.add_argument("--closure-out", help="write the durable closure artifact here")
    s.add_argument("--order", default="", help="work order id for the artifact")
    s.add_argument("--fix-commit", default="", help="the fix's commit sha")
    s.add_argument("--rationale", default="")

    args = p.parse_args(argv)

    if args.command == "matrix":
        doc = matrix_document()
        if args.out:
            _write_json(Path(args.out), doc)
            print("%s: %d rows" % (args.out, len(doc["rows"])))
            return 0
        if args.json:
            print(json.dumps(doc, indent=1))
        else:
            _print_matrix(doc)
        return 0

    if args.command == "classify":
        doc = classify_change(args.base, args.head)
        plan = plan_for(doc)
        doc["plan"] = plan
        doc["FULL_REGRESSION_REQUIRED"] = ("YES" if plan["full_regression_required"]
                                           else "NO")
        doc["full_regression_reason"] = _full_reason(plan)
        if args.out:
            _write_json(Path(args.out), doc)
        for row in doc["changed_files"]:
            print("%-12s %-60s %s" % ("/".join(row["classes"]), row["path"],
                                      row["why"][:70]))
        print()
        print("change classes:            %s" % ", ".join(doc["change_classes"]))
        print("lanes:                     %s" % (", ".join(plan["lanes"]) or "-"))
        print("modules:                   %d" % plan["module_count"])
        print("assembly required:         %s" % plan["assembly_required"])
        print("FULL_REGRESSION_REQUIRED:  %s" % doc["FULL_REGRESSION_REQUIRED"])
        print("reason: %s" % doc["full_regression_reason"])
        return 0

    if args.command == "validate":
        baseline = _read_json(Path(args.baseline)) if args.baseline else None
        out = Path(args.out) if args.out else None
        doc = validate(args.base, args.head, baseline=baseline, out=out,
                       require_closed=args.require_closed,
                       plan_only=args.plan_only)
        if out is not None:
            _write_json(out / "delta.json", doc)
        if args.closure_out:
            _write_json(Path(args.closure_out),
                        closure_document(doc, order=args.order,
                                         fix_commit=args.fix_commit,
                                         rationale=args.rationale))
        print("FULL_REGRESSION_REQUIRED: %s" % doc["FULL_REGRESSION_REQUIRED"])
        print("reason: %s" % doc["full_regression_reason"])
        if doc["run"]:
            print("targeted run: %(collected)d collected, %(failed)d failing, "
                  "%(seconds).1fs" % doc["run"])
        if doc.get("against_baseline"):
            print(json.dumps(doc["against_baseline"]["counts"], indent=1))
            for nodeid in doc["against_baseline"]["TRUE_NEW"]:
                print("TRUE_NEW", nodeid)
        if doc.get("closure"):
            for nodeid, verdict in doc["closure"]["results"].items():
                print("%-14s %s" % (verdict, nodeid))
        if doc["clean"] is None:
            return 0
        return 0 if doc["clean"] else 1

    return 2                                             # pragma: no cover


if __name__ == "__main__":                               # pragma: no cover
    sys.exit(main())
