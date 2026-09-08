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
MARKET_LOCAL_TOOLING = "MARKET_LOCAL_TOOLING"
#: ATLAS-THROUGHPUT-003: a sealed market package, a staging tree or a
#: validation receipt under a market's own packages/staging/receipts
#: directories -- inert data no production module reads.
MARKET_DATA_PACKAGE = "MARKET_DATA_PACKAGE"
#: ATLAS-THROUGHPUT-003: a change set that is ONE registered market's
#: authority data and nothing else. Granted to a whole change set, never to a
#: path: every AUTHORITY_CHANGE row must be that market's own authority file
#: (or a derived global whose diff names only that market) and no other class
#: may be present. Its full regression is CONDITIONAL on a committed
#: FAST_DATA_ONLY_RELEASE receipt for a sealed package covering exactly these
#: bytes AND production activation for the market -- otherwise it is exactly
#: AUTHORITY_CHANGE.
MARKET_AUTHORITY_DATA_ONLY = "MARKET_AUTHORITY_DATA_ONLY"
UNCLASSIFIED = "UNCLASSIFIED"

CHANGE_CLASSES: Tuple[str, ...] = (
    AUTHORITY_CHANGE, GENERIC_RUNTIME_CHANGE, SCHEMA_CHANGE,
    ROUTING_SEMANTIC_CHANGE, DEPLOYMENT_CHANGE, TEST_EXPECTATION_CHANGE,
    BOOKKEEPING_REGISTRATION_CHANGE, DOCUMENTATION_ONLY,
    GENERATED_REPORT_ONLY, BASELINE_MANIFEST_ONLY, MARKET_LOCAL_TOOLING,
    MARKET_DATA_PACKAGE, MARKET_AUTHORITY_DATA_ONLY,
    UNCLASSIFIED,
)

#: ATLAS-THROUGHPUT-003: the release surfaces a plan distinguishes. Every
#: change class maps to exactly one surface (``release_surface_of``); the
#: surfaces are what the FAST_DATA_ONLY_RELEASE decision is stated over.
SURFACE_MARKET_LOCAL_TOOLING = "MARKET_LOCAL_TOOLING"
SURFACE_MARKET_DATA_PACKAGE = "MARKET_DATA_PACKAGE"
SURFACE_MARKET_AUTHORITY_DATA_ONLY = "MARKET_AUTHORITY_DATA_ONLY"
SURFACE_SHARED_SCHEMA_CHANGE = "SHARED_SCHEMA_CHANGE"
SURFACE_SHARED_RUNTIME_CHANGE = "SHARED_RUNTIME_CHANGE"
SURFACE_ASSEMBLER_CHANGE = "ASSEMBLER_CHANGE"
SURFACE_DEPLOYMENT_CHANGE = "DEPLOYMENT_CHANGE"
SURFACE_CLASSIFIER_TEST_INFRA_CHANGE = "CLASSIFIER_TEST_INFRA_CHANGE"
SURFACE_UNKNOWN_MIXED = "UNKNOWN_MIXED"
SURFACE_NARROW_NON_RELEASE = "NARROW_NON_RELEASE"
RELEASE_SURFACES: Tuple[str, ...] = (
    SURFACE_MARKET_LOCAL_TOOLING, SURFACE_MARKET_DATA_PACKAGE,
    SURFACE_MARKET_AUTHORITY_DATA_ONLY, SURFACE_SHARED_SCHEMA_CHANGE,
    SURFACE_SHARED_RUNTIME_CHANGE, SURFACE_ASSEMBLER_CHANGE, SURFACE_DEPLOYMENT_CHANGE,
    SURFACE_CLASSIFIER_TEST_INFRA_CHANGE, SURFACE_UNKNOWN_MIXED, SURFACE_NARROW_NON_RELEASE,
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
    (MARKET_LOCAL_TOOLING, OrderedDict((
        ("surface", "a shadow market's own tooling and proposed artifacts, "
                    "inside ONE declared execution zone "
                    "(launch_packages/pettripfinder/market_local_ownership.json) "
                    "and proven isolated on all five conditions of "
                    "market_local_isolation: namespace, imports, write roots, "
                    "reverse reachability, registration"),
        ("lanes", ()),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", True),
        ("assembly", NOT_REQUIRED),
        ("full_regression", NOT_REQUIRED),
        ("condition", ""),
        ("why", "ATLAS-THROUGHPUT-001 measured that a helper no production "
                "module imports, that writes only its own market's proposed "
                "and report paths, and that describes a market the assembler "
                "cannot select, cost a 2-hour broad regression by path prefix "
                "alone; the proof replaces the prefix with the five facts, and "
                "any fact that cannot be established leaves the path in its "
                "prefix class"),
    ))),
    (MARKET_DATA_PACKAGE, OrderedDict((
        ("surface", "a sealed market package, a staging tree or a validation "
                    "receipt under launch_packages/pettripfinder/markets/"
                    "{packages,staging,receipts}/<market>/ -- immutable data "
                    "named by digest that no production module reads"),
        ("lanes", ()),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", True),
        ("assembly", NOT_REQUIRED),
        ("full_regression", NOT_REQUIRED),
        ("condition", ""),
        ("why", "ATLAS-THROUGHPUT-003: a package is the INPUT to the fast "
                "release lane, never to a build -- the assembler, the "
                "generator and the deployer read committed authority only; "
                "the reverse-dependent scan finds every test that pins one, "
                "and a package that is not a package fails the lane's rule A"),
    ))),
    (MARKET_AUTHORITY_DATA_ONLY, OrderedDict((
        ("surface", "a change set that is ONE registered market's own "
                    "authority data and nothing else: its registry entry, "
                    "census, policy package, partition, shard and release "
                    "contract, plus the derived globals where the diff names "
                    "only that market"),
        ("lanes", (LANES_MODULE.POLICY_SCHEMA, LANES_MODULE.IDENTITY_ROUTING,
                   LANES_MODULE.RELEASE_CONTRACT, LANES_MODULE.CROSS_MARKET)),
        ("owning_modules", True),
        ("owning_directory", False),
        ("reverse_dependents", True),
        ("market_targeted", True),
        ("assembly", REQUIRED),
        ("full_regression", CONDITIONAL),
        ("condition", "not required ONLY when a committed FAST_DATA_ONLY_RELEASE "
                      "receipt says FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES for a "
                      "sealed package whose dependency digests cover the exact "
                      "bytes of every changed authority file, that receipt has "
                      "no UNKNOWN rule, and fast_release_activation.json "
                      "ENABLES the market; required otherwise, exactly as "
                      "AUTHORITY_CHANGE"),
        ("why", "ATLAS-THROUGHPUT-003: the fifteen rules of the fast lane "
                "prove the release hazards a data-only change can cause "
                "(identity, first-party binding, policy semantics, routes, "
                "partition, whole-release collisions, preservation, intended "
                "delta, build, determinism, hashes, freshness, live state, "
                "paid provenance) directly and in minutes; the broad suite "
                "proves them indirectly in hours. Until the receipt exists and "
                "activation is granted the row is AUTHORITY_CHANGE by another "
                "name"),
    ))),
    (UNCLASSIFIED, OrderedDict((
        ("surface", "unknown -- no rule claims this path"),
        ("lanes", tuple(l for l in LANES_MODULE.LANES
                        if l != LANES_MODULE.FULL_REGRESSION
                        and l != LANES_MODULE.MARKET_TARGETED
                        # the broad-audit lane is carried by full_regression,
                        # which this row already requires (ATLAS-THROUGHPUT-002
                        # kept this row byte-identical to V2-001's)
                        and l != LANES_MODULE.WEBSITE_GENERATION_INTEGRATION)),
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
    # ATLAS-THROUGHPUT-002: a PROPOSED census is not authority -- nothing in
    # the publication path reads identity_census_proposed/ -- but it is not
    # known either, so it stays a full regression unless the market-local
    # proof claims it. Listed BEFORE the identity_census prefix, which used to
    # swallow it.
    ("prefix", "launch_packages/pettripfinder/identity_census_proposed/",
     (UNCLASSIFIED,)),
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
    # -- ATLAS-THROUGHPUT-003: sealed packages, staging trees and receipts live
    #    inside a market's own zone; the two policy files are release policy.
    ("prefix", "launch_packages/pettripfinder/markets/packages/", (MARKET_DATA_PACKAGE,)),
    ("prefix", "launch_packages/pettripfinder/markets/staging/", (MARKET_DATA_PACKAGE,)),
    ("prefix", "launch_packages/pettripfinder/markets/receipts/", (MARKET_DATA_PACKAGE,)),
    ("glob", "launch_packages/pettripfinder/fast_release_activation.json", (DEPLOYMENT_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/bundle_cache_closure.json", (DEPLOYMENT_CHANGE,)),
    ("glob", "launch_packages/pettripfinder/evidence_revocations.json", (AUTHORITY_CHANGE,)),
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

#: ATLAS-THROUGHPUT-002: the ONLY path rules whose verdict the market-local
#: proof may replace. Every one of them is a prefix or a filename glob -- a
#: class assigned by WHERE a file sits or WHAT it is called, never by what it
#: contains -- which is exactly the over-breadth 001 measured. An authority
#: rule, a deployment rule, the contracts / acquisition / brightdata prefixes
#: and the classifier's own files are not here and can never be narrowed.
MARKET_LOCAL_REFINABLE_RULES: Tuple[str, ...] = (
    "prefix:scripts/pettripfinder/",
    "prefix:scripts/pettripfinder/discovery/",
    "glob:scripts/pettripfinder/*polic*.py",
    "glob:scripts/pettripfinder/*reader*.py",
    "glob:scripts/pettripfinder/*render*.py",
    "glob:scripts/pettripfinder/*identity*.py",
    "glob:scripts/pettripfinder/*routing*.py",
    "glob:scripts/pettripfinder/census_*.py",
    "glob:scripts/pettripfinder/*corridor*.py",
    "glob:scripts/pettripfinder/*deploy*.py",
    "prefix:launch_packages/pettripfinder/identity_census_proposed/",
    "prefix:launch_packages/pettripfinder/markets/reports/",
    "prefix:docs/",
    "no rule",
)

#: ATLAS-THROUGHPUT-002: a change set that touches any of these carries a
#: change to the thing that DECIDES scope -- the classifier, the lanes, the
#: ownership registry, the proof, or shared test infrastructure. No path in
#: such a change set may be narrowed to MARKET_LOCAL_TOOLING: the selector
#: cannot authorize its own narrowing.
NARROWING_BLOCKERS: Tuple[Tuple[str, str], ...] = (
    ("glob", "scripts/pettripfinder/regression_delta.py"),
    ("glob", "scripts/pettripfinder/regression_lanes.py"),
    ("glob", "scripts/pettripfinder/regression_inventory.py"),
    ("glob", "scripts/pettripfinder/market_local_ownership.py"),
    ("glob", "scripts/pettripfinder/market_local_isolation.py"),
    ("glob", "scripts/pettripfinder/assembly_session_cache.py"),
    ("glob", "scripts/pettripfinder/throughput_profile.py"),
    ("glob", "launch_packages/pettripfinder/market_local_ownership.json"),
    ("glob", "launch_packages/pettripfinder/regression_validation_matrix.json"),
    ("glob", "conftest.py"),
    ("glob", "pytest.ini"),
    ("glob", "requirements*.txt"),
    # ATLAS-THROUGHPUT-003: the fast lane and everything it decides with.
    ("glob", "scripts/pettripfinder/sealed_market_package.py"),
    ("glob", "scripts/pettripfinder/market_package_writer.py"),
    ("glob", "scripts/pettripfinder/package_staging.py"),
    ("glob", "scripts/pettripfinder/release_index.py"),
    ("glob", "scripts/pettripfinder/first_party_binding.py"),
    ("glob", "scripts/pettripfinder/fast_release_lane.py"),
    ("glob", "launch_packages/pettripfinder/fast_release_activation.json"),
    # ATLAS-THROUGHPUT-004: the persistent bundle cache and its declared closure.
    ("glob", "scripts/pettripfinder/bundle_cache.py"),
    ("glob", "launch_packages/pettripfinder/bundle_cache_closure.json"),
    # ATLAS-THROUGHPUT-005: the release coordinator decides what a release IS.
    # A change here can never be narrowed by a market-local proof.
    ("glob", "scripts/pettripfinder/release_coordinator.py"),
    # ATLAS-THROUGHPUT-006: these decide WHAT RUNS and WHAT MAY DEPLOY. A change
    # here can never be narrowed by the very selection it controls.
    ("glob", "scripts/pettripfinder/ci_validation.py"),
    ("glob", "scripts/pettripfinder/ci_report.py"),
    ("glob", "scripts/pettripfinder/artifact_handoff.py"),
    ("glob", "scripts/pettripfinder/release_queue.py"),
    ("glob", "scripts/pettripfinder/live_verification.py"),
    ("glob", "launch_packages/pettripfinder/release_production_gate.json"),
    ("glob", "launch_packages/pettripfinder/reports/atlas_throughput_006_shard_manifest.json"),
    ("glob", ".github/workflows/*.yml"),
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


def is_narrowing_blocker(relpath: str) -> bool:
    """Does a change to this path forbid MARKET_LOCAL_TOOLING for the whole
    change set it travels in? Shared test state counts too."""
    rel = _posix(relpath)
    if any(_matches(kind, pattern, rel) for kind, pattern in NARROWING_BLOCKERS):
        return True
    return is_shared_test_state(rel)


def is_market_local_refinable(rule: str) -> bool:
    """May the market-local proof replace the verdict of ``rule``?"""
    return rule in MARKET_LOCAL_REFINABLE_RULES


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


#: ATLAS-THROUGHPUT-002: the old path of every rename in the last
#: :func:`changed_files` call, ``new path -> old path``. A rename is classified
#: on BOTH paths; this is how the second one reaches the classifier without
#: changing the ``path -> status`` shape every caller reads.
RENAMED_FROM: Dict[str, str] = {}


def changed_files(base: str, head: str = WORKTREE) -> "OrderedDict[str, str]":
    """``repo-relative path -> git status letter`` between two revisions.

    ``head`` may be :data:`WORKTREE`, which compares the working tree -- staged,
    unstaged and untracked-but-not-ignored -- against ``base``. Paths are
    returned relative to :data:`REPO_ROOT`; anything outside it is skipped,
    because nothing outside it is part of the factory.
    """
    prefix = _repo_prefix()
    out: "OrderedDict[str, str]" = OrderedDict()
    RENAMED_FROM.clear()

    def _strip(git_path: str) -> str:
        path = git_path.replace("\\", "/")
        return path[len(prefix):] if path.startswith(prefix) else "../" + path

    def _add(status: str, git_path: str, old_git_path: Optional[str] = None) -> None:
        path = git_path.replace("\\", "/")
        if path.startswith(prefix):
            out.setdefault(path[len(prefix):], status)
        else:
            # The git root holds the work-order reports, one level above the
            # package. They are still part of the change and are classified
            # rather than dropped -- a file this module cannot see is a file
            # it cannot require a full regression for.
            out.setdefault("../" + path, status)
        if old_git_path is not None:
            RENAMED_FROM[_strip(git_path)] = _strip(old_git_path)

    if head == WORKTREE:
        raw = _git("diff", "--name-status", "-M", base, "--")
        untracked = _git("ls-files", "--others", "--exclude-standard")
        for line in untracked.splitlines():
            if line.strip():
                _add("A", line.strip())
    else:
        raw = _git("diff", "--name-status", "-M", "%s..%s" % (base, head), "--")
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][:1]
        if status in ("R", "C") and len(parts) >= 3:
            _add(status, parts[2], parts[1])
        else:
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


def _market_local_refinement(relpath: str, status: str, rule: str, base: str,
                             head: str, renamed_from: Optional[str]) -> Tuple[bool, Dict]:
    """ATLAS-THROUGHPUT-002: ``(narrowed, proof)``. The proof is the full
    five-condition document from :mod:`market_local_isolation`; ``narrowed``
    is True only when it passed for the path AND, for a rename, for the old
    path too. Never called when the change set carries a narrowing blocker."""
    from scripts.pettripfinder import market_local_isolation as ISO
    proof = ISO.prove(relpath, base, head, status=status, old_path=renamed_from)
    if not proof["passed"]:
        return False, proof
    if renamed_from and _posix(renamed_from) != _posix(relpath):
        # K: shared -> local is evaluated on BOTH paths; the old path must
        # have been local too, or the rename is a widening in disguise.
        old_classes, old_rule = classify_path(renamed_from)
        if not is_market_local_refinable(old_rule):
            proof["failed_conditions"] = ["namespace"]
            proof["conditions"]["namespace"] = OrderedDict((
                ("pass", False),
                ("why", "renamed from %s, whose rule %s is not refinable" % (renamed_from, old_rule))))
            proof["passed"] = False
            return False, proof
        old_proof = ISO.prove(renamed_from, base, base, status="M")
        if not old_proof["passed"]:
            proof["passed"] = False
            proof["failed_conditions"] = ["namespace"]
            proof["conditions"]["namespace"] = OrderedDict((
                ("pass", False),
                ("why", "renamed from %s, which fails the proof at %s on %s"
                        % (renamed_from, base, ", ".join(old_proof["failed_conditions"])))))
            return False, proof
    return True, proof


# --------------------------------------------------------------------------- #
# ATLAS-THROUGHPUT-003: MARKET_AUTHORITY_DATA_ONLY, release surfaces and the
# FAST_DATA_ONLY_RELEASE requirement.
# --------------------------------------------------------------------------- #

#: The authority files ONE market owns, with <id> / <us> substituted.
MARKET_AUTHORITY_DATA_PATTERNS: Tuple[str, ...] = (
    "launch_packages/pettripfinder/markets/<id>.json",
    "launch_packages/pettripfinder/identity_census/<id>.json",
    "launch_packages/pettripfinder/hotel_policy_facts_<id>.json",
    "launch_packages/pettripfinder/markets/authority/<id>/*",
    "launch_packages/pettripfinder/<us>_final_partition_*.json",
    "deploy/netlify/release_contracts/<id>.json",
)

#: Files DERIVED from every market's shard by build_global_authority; a
#: data-only change regenerates them, and the diff may name only the market.
DERIVED_AUTHORITY_GLOBALS: Tuple[str, ...] = (
    "launch_packages/pettripfinder/identity_routing.json",
    "launch_packages/pettripfinder/hotel_exclusions.json",
    "launch_packages/pettripfinder/seed_businesses.csv",
    "launch_packages/pettripfinder/ptf_global_authority_manifest.json",
)

#: Classes a data-only change set may carry beside its authority rows.
_DATA_ONLY_COMPANIONS = frozenset({GENERATED_REPORT_ONLY, DOCUMENTATION_ONLY,
                                   BASELINE_MANIFEST_ONLY, MARKET_DATA_PACKAGE})

_DERIVED_LINE_OK = re.compile(r"sha256|build_marker|generated|\"count\"|_hash\"|\"as_of\"|^[+-]\s*[\[\]{},]*\s*$")


def _registered_market_ids_at(head: str) -> Tuple[str, ...]:
    """Every market id the registry carries at ``head`` (worktree or git)."""
    if head == WORKTREE:
        directory = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
        return tuple(sorted(p.stem for p in directory.glob("*.json")))
    listing = _git("ls-tree", "--name-only", head, "%slaunch_packages/pettripfinder/markets/" % _repo_prefix())
    return tuple(sorted(Path(line.strip()).stem for line in listing.splitlines()
                        if line.strip().endswith(".json")))


def market_authority_owner(relpath: str, markets: Sequence[str]) -> Optional[str]:
    """Which registered market's own authority file ``relpath`` is, if any."""
    rel = _posix(relpath)
    for market_id in markets:
        us = market_id.replace("-", "_")
        for pattern in MARKET_AUTHORITY_DATA_PATTERNS:
            candidate = pattern.replace("<id>", market_id).replace("<us>", us)
            if _matches("glob", candidate, rel):
                return market_id
        if market_id == "columbus-oh" and rel == "launch_packages/pettripfinder/hotel_policy_facts.json":
            return market_id
    # Partition tables name files whose stem is not the market's underscore form.
    try:
        from scripts.pettripfinder.build_market_manifest import _PARTITION_FILES
        from scripts.pettripfinder.assemble_production_site import _partition_path
        for market_id in markets:
            name = _PARTITION_FILES.get(market_id)
            if name and rel == "launch_packages/pettripfinder/" + name:
                return market_id
            path = _partition_path(market_id)
            if path is not None and rel == "launch_packages/pettripfinder/" + Path(path).name:
                return market_id
    except Exception:                                    # pragma: no cover
        pass
    return None


def _derived_global_names_only(relpath: str, base: str, head: str, market_id: str,
                               markets: Sequence[str]) -> Tuple[bool, str]:
    """A derived global's diff may name only ``market_id``."""
    prefix = _repo_prefix()
    if head == WORKTREE:
        raw = _git("diff", base, "--", prefix + relpath)
    else:
        raw = _git("diff", base, head, "--", prefix + relpath)
    others = [m for m in markets if m != market_id]
    us = market_id.replace("-", "_")
    for line in raw.splitlines():
        if not line or line[0] not in "+-" or line.startswith(("+++", "---")):
            continue
        if market_id in line or us in line:
            continue
        if any(o in line for o in others):
            return False, "diff of %s names another market: %s" % (relpath, line.strip()[:80])
        if _DERIVED_LINE_OK.search(line):
            continue
        return False, "diff of %s carries a line that names no market: %s" % (relpath, line.strip()[:80])
    return True, "diff names only %s" % market_id


def _market_authority_data_only(rows: Sequence[Mapping], base: str, head: str,
                                blockers: Sequence[str]) -> Tuple[Optional[str], str]:
    """``(market_id, why)`` when the WHOLE change set is one market's data."""
    if blockers:
        return None, "narrowing blocked by %s" % list(blockers)[:3]
    authority_rows = [r for r in rows if AUTHORITY_CHANGE in r["classes"]]
    if not authority_rows:
        return None, "no authority change"
    for row in rows:
        if AUTHORITY_CHANGE in row["classes"]:
            extra = set(row["classes"]) - {AUTHORITY_CHANGE, ROUTING_SEMANTIC_CHANGE}
            if extra:
                return None, "%s is also %s" % (row["path"], sorted(extra))
        elif not set(row["classes"]) <= _DATA_ONLY_COMPANIONS:
            return None, "%s is %s, not market data" % (row["path"], row["classes"])
    try:
        markets = _registered_market_ids_at(head)
    except Exception as exc:
        return None, "registry unreadable at %s: %s" % (head, str(exc)[:80])
    owners: Dict[str, str] = {}
    derived: List[str] = []
    for row in authority_rows:
        owner = market_authority_owner(row["path"], markets)
        if owner is not None:
            owners[row["path"]] = owner
        elif _posix(row["path"]) in DERIVED_AUTHORITY_GLOBALS:
            derived.append(row["path"])
        else:
            return None, "%s is shared authority, not one market's" % row["path"]
    if len(set(owners.values())) != 1:
        return None, ("authority rows belong to %s markets: %s"
                      % (len(set(owners.values())), sorted(set(owners.values()))))
    market_id = next(iter(owners.values()))
    for path in derived:
        ok, why = _derived_global_names_only(path, base, head, market_id, markets)
        if not ok:
            return None, why
    return market_id, ("every authority row is %s's own data (%d file(s), %d derived global(s))"
                       % (market_id, len(owners), len(derived)))


def _bytes_at(rev: str, relpath: str) -> Optional[bytes]:
    if rev == WORKTREE:
        path = REPO_ROOT / relpath
        return path.read_bytes() if path.is_file() else None
    try:
        return subprocess.run(["git", "show", "%s:%s%s" % (rev, _repo_prefix(), _posix(relpath))],
                              cwd=str(REPO_ROOT), capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None


def fast_data_only_release(market_id: str, rows: Sequence[Mapping], head: str) -> Dict:
    """The FAST_DATA_ONLY_RELEASE requirement for a data-only change set, and
    whether a committed proof satisfies it. Fail closed on every gap."""
    import hashlib
    from scripts.pettripfinder import fast_release_lane as FL
    from scripts.pettripfinder import sealed_market_package as SMP

    data_paths = [r["path"] for r in rows if AUTHORITY_CHANGE in r["classes"]
                  and market_authority_owner(r["path"], (market_id,)) == market_id
                  and not _posix(r["path"]).startswith("deploy/netlify/release_contracts/")]
    derived_paths = [r["path"] for r in rows if AUTHORITY_CHANGE in r["classes"] and r["path"] not in data_paths]
    head_digests: "OrderedDict[str, Optional[str]]" = OrderedDict()
    for path in data_paths:
        data = _bytes_at(head, path)
        head_digests[path] = "sha256:" + hashlib.sha256(data).hexdigest() if data is not None else None
    activation = FL.load_activation()
    block: "OrderedDict[str, object]" = OrderedDict((
        ("market_id", market_id),
        ("FAST_DATA_ONLY_RELEASE_REQUIRED", "YES"),
        ("data_only_paths", data_paths),
        ("derived_paths", derived_paths),
        ("head_digests", head_digests),
        ("package_id", None), ("package_digest", None), ("receipt", None),
        ("receipt_eligible", False),
        ("activation", activation.get("FAST_PATH_PRODUCTION_ACTIVATION")),
        ("activation_allowed", FL.production_activation_allowed(market_id, activation)),
        ("FULL_REGRESSION_REQUIRED", "YES"),
        ("MARKET_BUILD_REQUIRED", "YES"),
        ("bundle_cache", None),
        ("CANDIDATE_STAGING_AVAILABLE", "UNKNOWN"),
        ("release_coordinator", None),
        ("why", ""),
    ))
    # ATLAS-THROUGHPUT-005: can this change even reach a staged candidate? A
    # verified live parent and a seeded release store are what let the
    # coordinator inherit the unchanged markets instead of rebuilding them.
    # Reported, never decisive: staging availability is not release safety.
    try:
        from scripts.pettripfinder import release_coordinator as RC
        live = RC.LiveTruth.read()
        store = RC.ReleaseStore()
        fragments = store.fragment_digests(live.digest())
        block["release_coordinator"] = OrderedDict((
            ("coordinator_version", RC.COORDINATOR_VERSION),
            ("live_verified", live.verified),
            ("parent_release_digest", live.digest()),
            ("participating_markets", len(live.participating_markets)),
            ("fragments_in_release_store", len(fragments)),
            ("REAL_PRODUCTION_ACTIVATION", RC.REAL_PRODUCTION_ACTIVATION),
        ))
        block["CANDIDATE_STAGING_AVAILABLE"] = (
            "YES" if live.verified and len(fragments) >= len(live.participating_markets) else "NO")
    except Exception as exc:                             # the coordinator is optional here
        block["release_coordinator"] = OrderedDict((("available", False), ("why", str(exc)[:160])))
        block["CANDIDATE_STAGING_AVAILABLE"] = "NO"
    covering = []
    for package_path in SMP.list_packages(market_id):
        try:
            package = SMP.read_sealed(package_path)
        except SMP.PackageContractError:
            continue
        digests = set(package["dependency_input_digests"].values())
        if data_paths and all(d is not None and d in digests for d in head_digests.values()):
            covering.append(package)
    if not covering:
        block["why"] = ("no sealed package under markets/packages/%s covers the head bytes of %s; "
                        "the broad regression stays required" % (market_id, data_paths or "the change"))
        return block
    # ATLAS-THROUGHPUT-004: a TRUSTED persistent bundle for the covering
    # package means MARKET_BUILD_REQUIRED = NO. Artifact identity only -- the
    # FAST lane's release-safety rules still decide the release.
    try:
        from scripts.pettripfinder import bundle_cache as BC
        cache = BC.BundleCache()
        for package in covering:
            probe = cache.probe(package)
            if probe.get("trusted"):
                block["MARKET_BUILD_REQUIRED"] = "NO"
                block["bundle_cache"] = probe
                break
        else:
            block["bundle_cache"] = cache.probe(covering[-1])
    except Exception as exc:                            # the cache is optional here
        block["bundle_cache"] = OrderedDict((("trusted", False), ("why", str(exc)[:160])))
    for package in covering:
        receipts = FL.eligible_receipts(market_id, package["package_digest"])
        if receipts:
            block["package_id"] = package["package_id"]
            block["package_digest"] = package["package_digest"]
            receipt_path = receipts[-1]
            try:
                block["receipt"] = receipt_path.relative_to(REPO_ROOT).as_posix()
            except ValueError:                           # a receipts dir outside the tree (tests)
                block["receipt"] = receipt_path.as_posix()
            block["receipt_eligible"] = True
            break
    else:
        block["package_id"] = covering[-1]["package_id"]
        block["package_digest"] = covering[-1]["package_digest"]
        block["why"] = ("sealed package %s covers the change but no committed receipt says "
                        "FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES for it" % covering[-1]["package_id"])
        return block
    if not block["activation_allowed"]:
        block["why"] = ("receipt %s is ELIGIBLE for %s, but FAST_PATH_PRODUCTION_ACTIVATION is %s "
                        "and %s is not in the pilot allowlist; the broad regression stays required"
                        % (block["receipt"], block["package_id"], block["activation"], market_id))
        return block
    block["FULL_REGRESSION_REQUIRED"] = "NO"
    block["why"] = ("receipt %s proves %s FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES and activation "
                    "is granted for %s" % (block["receipt"], block["package_id"], market_id))
    return block


_ASSEMBLER_GLOBS = ("scripts/pettripfinder/assemble_*.py", "scripts/pettripfinder/build_market_manifest.py",
                    "scripts/pettripfinder/release_contracts.py", "scripts/generate_pettripfinder_*.py",
                    "scripts/pettripfinder/market_package.py", "scripts/pettripfinder/global_deployment.py")


def release_surface_of(row: Mapping) -> str:
    """The release surface one classified row belongs to."""
    classes = set(row["classes"])
    path = _posix(row["path"])
    if is_narrowing_blocker(path) or is_shared_test_state(path):
        return SURFACE_CLASSIFIER_TEST_INFRA_CHANGE
    if MARKET_LOCAL_TOOLING in classes:
        return SURFACE_MARKET_LOCAL_TOOLING
    if MARKET_DATA_PACKAGE in classes:
        return SURFACE_MARKET_DATA_PACKAGE
    if MARKET_AUTHORITY_DATA_ONLY in classes:
        return SURFACE_MARKET_AUTHORITY_DATA_ONLY
    if UNCLASSIFIED in classes or AUTHORITY_CHANGE in classes:
        return SURFACE_UNKNOWN_MIXED
    if any(_matches("glob", g, path) for g in _ASSEMBLER_GLOBS):
        return SURFACE_ASSEMBLER_CHANGE
    if SCHEMA_CHANGE in classes:
        return SURFACE_SHARED_SCHEMA_CHANGE
    if DEPLOYMENT_CHANGE in classes:
        return SURFACE_DEPLOYMENT_CHANGE
    if GENERIC_RUNTIME_CHANGE in classes or ROUTING_SEMANTIC_CHANGE in classes:
        return SURFACE_SHARED_RUNTIME_CHANGE
    return SURFACE_NARROW_NON_RELEASE


def classify_change(base: str, head: str = WORKTREE,
                    paths: Optional[Mapping[str, str]] = None) -> Dict:
    """Classify every changed path, refining test files by syntax tree and
    market-local paths by the five-condition isolation proof."""
    files = OrderedDict(paths) if paths is not None else changed_files(base, head)
    renamed = dict(RENAMED_FROM) if paths is None else {}
    blockers = [p for p in files if is_narrowing_blocker(p)]
    rows: List[Dict] = []
    for relpath, status in files.items():
        classes, rule = classify_path(relpath)
        why = "matched %s" % rule
        shared = False
        proof: Optional[Dict] = None
        if classes == (TEST_EXPECTATION_CHANGE,) and relpath.endswith(".py"):
            refined, refined_why = refine_test_change(
                relpath, read_at(base, relpath), read_at(head, relpath))
            classes = (refined,)
            why = refined_why
        if TEST_EXPECTATION_CHANGE in classes:
            shared = is_shared_test_state(relpath)
        old_path = renamed.get(relpath)
        already_narrow = classes in ((GENERATED_REPORT_ONLY,), (DOCUMENTATION_ONLY,),
                                     (BASELINE_MANIFEST_ONLY,), (BOOKKEEPING_REGISTRATION_CHANGE,))
        if is_market_local_refinable(rule) and paths is None and not already_narrow:
            if blockers:
                why += "; market-local narrowing blocked: the change set touches %s" % ", ".join(blockers[:3])
            elif all(c in (GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE, SCHEMA_CHANGE,
                           DEPLOYMENT_CHANGE, UNCLASSIFIED) for c in classes):
                narrowed, proof = _market_local_refinement(relpath, status, rule, base, head, old_path)
                if narrowed:
                    classes = (MARKET_LOCAL_TOOLING,)
                    why = ("isolation proof passed for zone %s on all five conditions"
                           % proof["zone"])
                elif proof is not None and proof.get("zone"):
                    why += "; market-local proof FAILED on %s: %s" % (
                        ", ".join(proof["failed_conditions"]),
                        "; ".join(proof["conditions"][c]["why"][:120]
                                  for c in proof["failed_conditions"]))
                elif proof is not None:
                    why += "; not market-local: %s" % proof["conditions"]["namespace"]["why"]
        markets = _markets_named(relpath)
        if proof is not None and proof.get("zone"):
            markets = tuple(dict.fromkeys(list(markets) + [proof["zone"]]))
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
            ("renamed_from", old_path),
            ("classes", list(classes)),
            ("rule", rule),
            ("why", why),
            ("shared_test_state", shared),
            ("markets", list(markets)),
            ("market_local_proof", (OrderedDict((
                ("zone", proof["zone"]), ("passed", proof["passed"]),
                ("failed_conditions", proof["failed_conditions"]),
                ("conditions", OrderedDict((k, OrderedDict((("pass", v["pass"]), ("why", v["why"]))))
                                           for k, v in proof["conditions"].items())),
            )) if proof is not None else None)),
        )))
    # ATLAS-THROUGHPUT-003: a change set that is ONE market's authority data
    # and nothing else is MARKET_AUTHORITY_DATA_ONLY -- a whole-set verdict.
    data_only_market: Optional[str] = None
    data_only_why = "not evaluated (explicit path list)"
    fast_block: Optional[Dict] = None
    if paths is None:
        data_only_market, data_only_why = _market_authority_data_only(rows, base, head, blockers)
        if data_only_market is not None:
            fast_block = fast_data_only_release(data_only_market, rows, head)
            for row in rows:
                if AUTHORITY_CHANGE in row["classes"]:
                    row["classes"] = [MARKET_AUTHORITY_DATA_ONLY]
                    row["why"] += "; MARKET_AUTHORITY_DATA_ONLY: %s" % data_only_why
                    if data_only_market not in row["markets"]:
                        row["markets"] = list(row["markets"]) + [data_only_market]
    for row in rows:
        row["release_surface"] = release_surface_of(row)
    classes_seen: List[str] = []
    for row in rows:
        for cls in row["classes"]:
            if cls not in classes_seen:
                classes_seen.append(cls)
    ordered = [c for c in CHANGE_CLASSES if c in classes_seen]
    surfaces = [s for s in RELEASE_SURFACES if any(r["release_surface"] == s for r in rows)]
    return OrderedDict((
        ("schema", SCHEMA_CLASSIFICATION),
        ("base", base),
        ("base_sha", resolve_sha(base)),
        ("head", head),
        ("head_sha", resolve_sha(head)),
        ("changed_file_count", len(rows)),
        ("narrowing_blockers", blockers),
        ("changed_files", rows),
        ("change_classes", ordered),
        ("release_surfaces", surfaces),
        ("market_authority_data_only", OrderedDict((("market_id", data_only_market), ("why", data_only_why)))),
        ("fast_data_only_release", fast_block),
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
            if decision == CONDITIONAL and cls == MARKET_AUTHORITY_DATA_ONLY:
                # ATLAS-THROUGHPUT-003: conditional on a committed ELIGIBLE
                # receipt for a sealed package covering these bytes AND
                # production activation. Anything less is AUTHORITY_CHANGE.
                block = classification.get("fast_data_only_release") or {}
                decision = NOT_REQUIRED if block.get("FULL_REGRESSION_REQUIRED") == "NO" else REQUIRED
                detail = block.get("why") or ("no FAST_DATA_ONLY_RELEASE proof recorded for %s"
                                              % row["path"])
            elif decision == CONDITIONAL:
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
        # ATLAS-THROUGHPUT-002: a zone's own test modules are the market's
        # targeted suite even when regression_lanes.MARKET_PREFIXES has no row
        # for it (an unregistered market has none by design).
        try:
            from scripts.pettripfinder import market_local_ownership as OWN
            zone = OWN.load_registry().zone_for(market)
        except Exception:                                    # malformed: no extra modules
            zone = None
        if zone is not None:
            for path in sorted(PTF_TESTS.rglob("test_*.py")):
                rel = "tests/pettripfinder/" + LANES_MODULE._relpath(path)
                if any(OWN._glob_match(p, rel) for p in zone.owned_tests) and rel not in modules:
                    modules.append(rel)
    for lane in lanes:
        for module in LANES_MODULE.modules_in_lane(lane):
            if module not in modules:
                modules.append(module)

    # A directory target subsumes the modules under it.
    directories = [m for m in modules if not m.endswith(".py")]
    modules = [m for m in modules
               if not any(m != d and m.startswith(d + "/") for d in directories)]

    fast_block = classification.get("fast_data_only_release")
    return OrderedDict((
        ("lanes", lanes),
        ("markets", markets),
        ("modules", sorted(modules)),
        ("module_count", len(modules)),
        ("assembly_required", assembly == REQUIRED),
        ("full_regression_required", full == REQUIRED),
        ("full_regression_decision", full),
        ("release_surfaces", list(classification.get("release_surfaces") or ())),
        ("FAST_DATA_ONLY_RELEASE_REQUIRED",
         "YES" if fast_block and fast_block.get("FAST_DATA_ONLY_RELEASE_REQUIRED") == "YES" else "NO"),
        ("fast_data_only_release", fast_block),
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


LANE_SOURCE = "lane"


def _status_verdict(status: Optional[str]) -> str:
    if status is None or status == "skipped":
        return NOT_EXERCISED
    return CLOSED if status == "passed" else STILL_FAILING


def prove_closure(required_closed: Sequence[str],
                  statuses: Mapping[str, str],
                  exercised: Optional[Mapping[str, Mapping[str, str]]] = None) -> Dict:
    """Account for every node id the broad regression called TRUE_NEW.

    ``exercised`` maps a run label (the junit path of a run the caller made
    at the fix commit, e.g. an ordered one-process replay) to that run's
    statuses. It fills ONLY a node id the lanes left NOT_EXERCISED -- the
    classes ``regression_lanes.DEFERRED_TO_FULL_REGRESSION`` keeps out of
    every lane -- and never overrides a lane result. ``sources`` records
    which run proved each node id."""
    results: "OrderedDict[str, str]" = OrderedDict()
    sources: "OrderedDict[str, str]" = OrderedDict()
    for nodeid in required_closed:
        verdict = _status_verdict(statuses.get(nodeid))
        source = LANE_SOURCE
        if verdict == NOT_EXERCISED:
            for label, run_statuses in (exercised or {}).items():
                candidate = _status_verdict(run_statuses.get(nodeid))
                if candidate != NOT_EXERCISED:
                    verdict, source = candidate, label
                    break
        results[nodeid] = verdict
        sources[nodeid] = source if verdict != NOT_EXERCISED else ""
    return OrderedDict((
        ("required_closed", list(required_closed)),
        ("results", results),
        ("sources", sources),
        ("closed", [n for n, v in results.items() if v == CLOSED]),
        ("still_failing", [n for n, v in results.items() if v == STILL_FAILING]),
        ("not_exercised", [n for n, v in results.items() if v == NOT_EXERCISED]),
        ("all_accounted_for", bool(required_closed) and
         all(v == CLOSED for v in results.values())),
    ))


def classify_against_baseline(failing: Sequence[str],
                              baseline: Mapping,
                              messages: Optional[Mapping[str, str]] = None) -> Dict:
    """PRE_EXISTING / RESOLVED / TRUE_NEW for a delta run.

    RESOLVED is scoped to what the delta run actually EXERCISED, because a
    narrow run cannot claim a node it never collected started passing.

    ATLAS-THROUGHPUT-007: when the baseline carries ``failure_signatures`` and
    the caller supplies this run's failure ``messages``, a baselined node whose
    failure has a DIFFERENT normalized signature is TRUE_NEW. The baseline
    records that a test fails, not a licence for it to fail in new ways. With
    no messages the classification is by node id alone, exactly as before.
    """
    from scripts.pettripfinder import ci_validation as CI

    pre = set(baseline["failing_node_ids"])
    signatures = dict(baseline.get("failure_signatures") or {})
    failing_set = set(failing)
    pre_existing: List[str] = []
    true_new: List[str] = []
    changed: List["OrderedDict[str, Any]"] = []
    for node in sorted(failing_set):
        if node not in pre:
            true_new.append(node)
            continue
        expected = signatures.get(node)
        actual = CI.failure_signature((messages or {}).get(node, "")) if messages else None
        if expected and actual and actual != expected:
            true_new.append(node)
            changed.append(OrderedDict((("node_id", node),
                                        ("why", "same node, different failure signature"),
                                        ("baseline_signature", expected),
                                        ("actual_signature", actual))))
        else:
            pre_existing.append(node)
    return OrderedDict((
        ("baseline_source_sha", baseline["source_sha"]),
        ("PRE_EXISTING", pre_existing),
        ("TRUE_NEW", true_new),
        ("CHANGED_SIGNATURE", changed),
        ("signature_checked", bool(messages and signatures)),
        ("counts", OrderedDict((("PRE_EXISTING", len(pre_existing)),
                                ("TRUE_NEW", len(true_new)),
                                ("CHANGED_SIGNATURE", len(changed))))),
    ))


def baseline_now_passing(failing: Sequence[str], baseline: Mapping,
                         collected: Optional[Sequence[str]] = None) -> List[str]:
    """Baselined nodes that did NOT fail in this run.

    Reported, never erased: a legacy failure that starts passing is a fact about
    the tree worth knowing, and quietly dropping it from the baseline is how a
    baseline stops describing anything. Scoped to what was collected when the
    caller knows it, since an unexercised node has not started passing.
    """
    pre = set(baseline["failing_node_ids"])
    if collected is not None:
        pre &= set(collected)
    return sorted(pre - set(failing))


def resolved_against_baseline(statuses: Mapping[str, str],
                              baseline: Mapping) -> List[str]:
    pre = set(baseline["failing_node_ids"])
    return sorted(n for n, s in statuses.items()
                  if n in pre and s == "passed")


def validate(base: str, head: str = WORKTREE, *, baseline: Optional[Mapping] = None,
             out: Optional[Path] = None, require_closed: Sequence[str] = (),
             plan_only: bool = False, exercised_junit: Sequence[Path] = (),
             exercised_at: str = "") -> Dict:
    """Classify, plan, run and prove -- the whole delta-scoped validation.

    ``exercised_junit``: junit files of runs the caller made at the fix
    commit; their statuses prove only the required node ids the lanes defer
    (see ``prove_closure``). ``exercised_at`` names the commit they ran at."""
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
    exercised: "OrderedDict[str, Dict[str, str]]" = OrderedDict()
    exercised_runs = []
    for xml_path in exercised_junit:
        cases = LANES_MODULE._junit_cases(Path(xml_path))
        label = Path(xml_path).as_posix()
        exercised[label] = cases
        exercised_runs.append(OrderedDict((
            ("junit", label), ("at", exercised_at), ("cases", len(cases)),
            ("passed", sum(1 for v in cases.values() if v == "passed")),
            ("failed", sum(1 for v in cases.values() if v not in ("passed", "skipped"))),
        )))
    doc["exercised_runs"] = exercised_runs
    if require_closed:
        closure = prove_closure(require_closed, statuses, exercised)
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
        ("market_local_refinable_rules", list(MARKET_LOCAL_REFINABLE_RULES)),
        ("narrowing_blockers", [OrderedDict((("kind", k), ("pattern", p)))
                                for k, p in NARROWING_BLOCKERS]),
        ("market_local_ownership_registry",
         "launch_packages/pettripfinder/market_local_ownership.json"),
        # ATLAS-THROUGHPUT-003.
        ("release_surfaces", list(RELEASE_SURFACES)),
        ("release_surface_matrix", [
            OrderedDict((("release_surface", s),
                         ("FAST_DATA_ONLY_RELEASE_REQUIRED", "YES" if s == SURFACE_MARKET_AUTHORITY_DATA_ONLY else "NO"),
                         ("FULL_REGRESSION_REQUIRED", fr),
                         ("why", why)))
            for s, fr, why in (
                (SURFACE_MARKET_LOCAL_TOOLING, "NO", "five-condition isolation proof (ATLAS-THROUGHPUT-002)"),
                (SURFACE_MARKET_DATA_PACKAGE, "NO", "inert data named by digest; the fast lane's input, never a build's"),
                (SURFACE_MARKET_AUTHORITY_DATA_ONLY, "CONDITIONAL",
                 "NO only with a committed ELIGIBLE receipt covering the exact bytes and production activation; YES otherwise"),
                (SURFACE_SHARED_SCHEMA_CHANGE, "YES", "a contract change moves what every market derives"),
                (SURFACE_SHARED_RUNTIME_CHANGE, "YES", "shared runtime every market executes"),
                (SURFACE_ASSEMBLER_CHANGE, "YES", "the assembler is the proof the fast lane's rule J relies on"),
                (SURFACE_DEPLOYMENT_CHANGE, "YES", "deployment doctrine is proven by a fresh assembly"),
                (SURFACE_CLASSIFIER_TEST_INFRA_CHANGE, "YES", "the selector cannot authorize its own narrowing"),
                (SURFACE_UNKNOWN_MIXED, "YES", "an unclaimed path or a mixed set is the broad suite by definition"),
                (SURFACE_NARROW_NON_RELEASE, "NO", "prose, reports, baselines, bookkeeping and owned test expectations"),
            )]),
        ("market_authority_data_patterns", list(MARKET_AUTHORITY_DATA_PATTERNS)),
        ("derived_authority_globals", list(DERIVED_AUTHORITY_GLOBALS)),
        ("fast_release_activation", "launch_packages/pettripfinder/fast_release_activation.json"),
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
        ("node_id_sources", closure.get("sources", OrderedDict())),
        ("exercised_runs", list(delta.get("exercised_runs") or [])),
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
    s.add_argument("--exercised-junit", action="append", default=[],
                   help="junit of a run made at the fix commit; proves only the "
                        "required node ids the lanes defer to the full regression")
    s.add_argument("--exercised-at", default="", help="the commit that run was made at")

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
                       plan_only=args.plan_only,
                       exercised_junit=[Path(p) for p in args.exercised_junit],
                       exercised_at=args.exercised_at)
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
