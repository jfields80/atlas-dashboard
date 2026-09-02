"""PTF-FACTORY-THROUGHPUT-HARDENING-001 -- test lanes, the normal regression
flow, and the baseline-failure manifest.

    python scripts/pettripfinder/regression_lanes.py plan
    python scripts/pettripfinder/regression_lanes.py run --lane market_targeted --market dayton-oh --out data/regression/<run>
    python scripts/pettripfinder/regression_lanes.py run --lane policy_schema --lane identity_routing --out ...
    python scripts/pettripfinder/regression_lanes.py run --lane full_regression --out ...
    python scripts/pettripfinder/regression_lanes.py baseline --run data/regression/<run> --sha <commit> --out launch_packages/pettripfinder/regression_baselines/<commit>.json
    python scripts/pettripfinder/regression_lanes.py classify --baseline <baseline.json> --run data/regression/<run> [--expected-epoch-change <file>] [--rerun-flakes]

WHY LANES
---------
Dayton APPLICATION-002 spent roughly 45 minutes applying a market and roughly
290 minutes finding and re-pinning tests, because every discovered stale pin was
followed by another ~37-minute full regression. The full suite is the right
FINAL check; it is the wrong instrument for finding which pins a market-scoped
change moved. Lanes are the instrument: a named subset of the suite, chosen by
what the change could have touched, that runs in minutes.

THE LANES
---------
    market_targeted          every module whose name carries the market, plus
                             the per-market contract rows (contracts/,
                             release contracts, schema migration, renderer)
    policy_schema            the policy record contract and its readers/renderers
    identity_routing         identity keys, census partitions, geography,
                             routing, ledgers, duplicate scans
    release_contract         per-market release contracts and market authorities
    cross_market             isolation: one market's data never leaks into another
    assembly                 the site generator and the multi-market assembler
    deployment_architecture  manifests, participation, authorizations, records
    full_regression          everything under tests/

A module may belong to several lanes. Membership is a committed table, not a
heuristic: a module that is not listed belongs to full_regression only, and a
contract test asserts that every module a market-scoped change is known to
break sits in a lane that the normal flow runs.

THE NORMAL FLOW (market-scoped change, no shared-code change)
-------------------------------------------------------------
    1  market_targeted (--market <id>)
    2  policy_schema + identity_routing
    3  release_contract
    4  assemble the candidate (assemble_netlify_bundle / global assembly)
    5  fix the factual epoch pins the targeted lanes surfaced (pins/*.json and
       the market's own suites), re-run 1-3 until clean
    6  commit
    7  ONE full_regression, classified against the committed baseline manifest

Shared or generic code changed? Run the affected lanes at step 2 as well
(cross_market, assembly, deployment_architecture as the change warrants), and
expect the full regression to be the proof rather than the discovery.

THE BASELINE MANIFEST
---------------------
A run's failures are compared by NODE ID against the manifest committed for a
source sha, never by count. Every failing node is classified exactly once:

    PRE_EXISTING            failing in the baseline manifest for the prior sha
    EXPECTED_EPOCH_CHANGE   named in the order's expected-epoch-change list
    TEST_HARNESS_FLAKE      failed, then passed on an isolated re-run
    TRUE_NEW_FAILURE        none of the above -- the order is not clean

The order passes only with TRUE_NEW_FAILURE == 0.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"
PTF_TESTS = TESTS_DIR / "pettripfinder"
BASELINES_DIR = REPO_ROOT / "launch_packages" / "pettripfinder" / "regression_baselines"

SCHEMA_RUN = "ptf-regression-run/1.0"
SCHEMA_BASELINE = "ptf-regression-baseline/1.0"
SCHEMA_CLASSIFICATION = "ptf-regression-classification/1.0"

MARKET_TARGETED = "market_targeted"
POLICY_SCHEMA = "policy_schema"
IDENTITY_ROUTING = "identity_routing"
RELEASE_CONTRACT = "release_contract"
CROSS_MARKET = "cross_market"
ASSEMBLY = "assembly"
DEPLOYMENT_ARCHITECTURE = "deployment_architecture"
FULL_REGRESSION = "full_regression"

LANES: Tuple[str, ...] = (
    MARKET_TARGETED, POLICY_SCHEMA, IDENTITY_ROUTING, RELEASE_CONTRACT,
    CROSS_MARKET, ASSEMBLY, DEPLOYMENT_ARCHITECTURE, FULL_REGRESSION,
)

#: The sequence a market-scoped change runs, in order. ``assemble`` is not a
#: lane -- it is the production assembler -- and is listed so the plan prints
#: the whole flow rather than only its pytest half.
NORMAL_FLOW: Tuple[Tuple[str, str], ...] = (
    (MARKET_TARGETED, "run the market's own modules and its contract rows"),
    (POLICY_SCHEMA, "the policy record contract, readers and renderers"),
    (IDENTITY_ROUTING, "identity keys, partitions, geography, routing, ledgers"),
    (RELEASE_CONTRACT, "every market's release contract still verifies "
                       "(python -m scripts.pettripfinder.release_contracts first: seconds)"),
    ("assemble", "assemble the candidate bundle; the renderer is the last gate"),
    ("fix_pins", "move the factual epoch pins the lanes surfaced; re-run 1-4"),
    ("commit", "commit the market change with its pins"),
    (FULL_REGRESSION, "ONE broad regression, classified against the baseline"),
)

PRE_EXISTING = "PRE_EXISTING"
EXPECTED_EPOCH_CHANGE = "EXPECTED_EPOCH_CHANGE"
TEST_HARNESS_FLAKE = "TEST_HARNESS_FLAKE"
TRUE_NEW_FAILURE = "TRUE_NEW_FAILURE"
CLASSES: Tuple[str, ...] = (PRE_EXISTING, EXPECTED_EPOCH_CHANGE,
                            TEST_HARNESS_FLAKE, TRUE_NEW_FAILURE)

# --------------------------------------------------------------------------- #
# Market prefixes: which module names belong to which market.
# --------------------------------------------------------------------------- #

MARKET_PREFIXES: "OrderedDict[str, Tuple[str, ...]]" = OrderedDict((
    ("cincinnati-oh", ("test_cincinnati_",)),
    ("cleveland-akron-canton-oh", ("test_cleveland_",)),
    ("columbus-oh", ("test_columbus_", "test_generate_columbus_site")),
    ("dayton-oh", ("test_dayton_",)),
    ("detroit-ann-arbor-mi", ("test_detroit_",)),
    ("grand-rapids-holland-mi", ("test_grand_rapids_",)),
    ("indianapolis-in", ("test_indianapolis_",)),
    ("louisville-ky", ("test_louisville_",)),
    ("milwaukee-wi", ("test_milwaukee_",)),
    ("pittsburgh-pa", ("test_pittsburgh_",)),
    ("st-louis-mo", ("test_st_louis_",)),
))

#: Modules that carry a row for EVERY market (a per-market pin, a per-market
#: parametrised contract). A market-targeted run includes them because they are
#: exactly where a market's count change shows up outside its own suites.
#:
#: NOT listed, deliberately: test_global_deployment_architecture_045 and
#: test_launch_participation_046 assemble the whole nine-market site (914s and
#: 528s on the c854469 baseline -- 24 of the old chunk's 27 minutes). They read
#: their pins from pins/deployment_state.json, run once in the final broad
#: regression, and the flow's assembly step produces the same facts earlier.
PER_MARKET_CONTRACT_MODULES: Tuple[str, ...] = (
    "contracts/test_market_authorities.py",
    "contracts/test_market_state_pins.py",
    "contracts/test_census_partition.py",
    "contracts/test_market_geography.py",
    "contracts/test_compat_readers.py",
    "test_per_market_release_contracts.py",
    "test_policy_schema_migration.py",
    "test_renderer_real_records.py",
    "test_identity_routing.py",
    "test_market_isolation.py",
    "test_market_ownership.py",
    "test_market_authority_sharding.py",
    "test_deployment_authorization_047.py",
    "test_grand_rapids_launch_participation_032.py",
    "test_global_assembler.py",
    "test_factory_throughput_001.py",
)

#: Test classes every lane EXCEPT full_regression deselects. Each one assembles
#: whole bundles per market and costs minutes on the c854469 baseline; the
#: assembly step of the flow produces the same facts once, and the final broad
#: regression runs them once more. Node ids, so a rename fails loudly.
DEFERRED_TO_FULL_REGRESSION: Tuple[Tuple[str, str], ...] = (
    ("tests/pettripfinder/test_per_market_release_contracts.py::TestEveryMarketAssembles",
     "assembles every market's bundle: 638 s on the baseline"),
)

# --------------------------------------------------------------------------- #
# Lane membership: module path (relative to tests/pettripfinder) patterns.
# --------------------------------------------------------------------------- #

LANE_MEMBERSHIP: "OrderedDict[str, Tuple[str, ...]]" = OrderedDict((
    (POLICY_SCHEMA, (
        "contracts/test_validators.py", "contracts/test_service_animal.py",
        "contracts/test_fee_computation.py", "contracts/test_compat_readers.py",
        "contracts/test_closure.py", "policy/*.py",
        "test_policy_schema_migration.py", "test_structured_fact_rendering.py",
        "test_renderer_real_records.py", "test_prose_pet_facts.py",
        "test_prose_fee_ladder.py", "test_fee_tiers.py", "test_fee_forms.py",
        "test_profile_fee_dimensions.py",
        "test_promotion_preserves_structured_facts.py",
        "test_pet_evidence_vocabulary.py", "test_weight_exclusivity.py",
        "test_dual_weight_and_additive_fees.py",
        "test_combined_weight_and_restriction_rows.py",
        "test_refundability_binding.py", "test_policy_precision.py",
        "test_service_animal_correction_011.py",
        "test_service_animal_reattestation_012.py",
        "test_reader_tiered_fee_hardening_010.py",
        "test_generic_fee_reader_usd_suffix_010.py", "test_wyndham_extraction.py",
        "test_sonesta_identity_and_scope.py",
        "test_choice_refusal_contradiction_005.py", "test_hotel_exclusions.py",
        "test_hotel_exclusions_co_located_004.py", "test_publication_guard.py",
        "test_publication_schema_decisions_010.py", "test_export_authority_guard.py",
        "test_promotion_resolution.py", "test_promote_attested_candidates.py",
        "acquisition/test_vocabulary_normalization_043.py",
        "acquisition/test_normalization_041.py",
        "acquisition/test_parser_semantics_017.py",
    )),
    (IDENTITY_ROUTING, (
        "contracts/test_identity_key.py", "contracts/test_census_partition.py",
        "contracts/test_market_geography.py", "contracts/test_coverage.py",
        "test_identity_routing.py", "test_identity_evidence.py",
        "test_routing_property_code_scope.py", "test_census_location.py",
        "test_census_promotion.py", "test_seed_matches_official_source.py",
        "test_market_ownership.py", "test_market_isolation.py",
        "test_market_authority_sharding.py", "test_coverage_audit.py",
        "acquisition/test_market_routing.py", "acquisition/test_paid_attempt_ledger.py",
        "acquisition/test_discovery_attempt_ledger.py", "acquisition/test_retry_policy.py",
        "acquisition/test_double_buy_url_level_p4.py",
        "acquisition/test_identity_binding_027.py",
        "acquisition/test_paid_lane_provenance.py",
        "acquisition/test_lane_qualification.py",
        "acquisition/test_acquisition_ladder.py",
        "brightdata/test_property_code_patterns.py",
        "brightdata/test_street_agreement_006.py",
        "discovery/test_identity_*.py", "discovery/test_property_identity.py",
        "discovery/test_census_*.py", "discovery/test_lodging_*.py",
        "discovery/test_deduplicate.py", "discovery/test_duplicates.py",
        "discovery/test_market_membership.py", "discovery/test_property_code_seam.py",
        "discovery/test_shared_brand_url_repair.py",
    )),
    (RELEASE_CONTRACT, (
        "test_per_market_release_contracts.py",
        "contracts/test_market_authorities.py",
        "contracts/test_market_state_pins.py",
        "test_market_policy_package_009.py", "test_markets.py",
    )),
    (CROSS_MARKET, (
        "contracts/test_market_authorities.py",
        "contracts/test_market_state_pins.py",
        "test_market_isolation.py", "test_market_ownership.py",
        "test_market_authority_sharding.py", "test_two_market_compat.py",
        "test_homepage_market_awareness.py", "test_dayton_authority.py",
        "test_cleveland_authority.py", "test_louisville_authority.py",
        "test_identity_routing.py",
    )),
    (ASSEMBLY, (
        "test_global_assembler.py", "test_generate_columbus_site.py",
        "test_site_data.py", "test_site_pages.py", "test_site_shell_markup.py",
        "test_site_enrichment.py", "test_structured_data.py", "test_hotel_profile.py",
        "test_listing_dataset_builder.py", "test_listing_renderability_boundary.py",
        "test_prod002_integration.py", "test_prod003_*.py",
        "test_prod004_verified_only.py", "test_prod005_netlify_config.py",
        "test_commercial_actions.py", "test_affiliate_destinations.py",
        "test_measurement.py", "test_inventory_validation.py",
        "test_renderer_real_records.py", "test_structured_fact_rendering.py",
    )),
    (DEPLOYMENT_ARCHITECTURE, (
        "test_global_deployment_architecture_045.py",
        "test_launch_participation_046.py", "test_deployment_authorization_047.py",
        "test_grand_rapids_launch_participation_032.py", "test_deployment_012.py",
        "test_production_deploy_012.py", "test_register_publish_011.py",
        "test_louisville_publication_008.py", "test_publication_cleanup_008b.py",
        "test_st_louis_production_safety_001.py", "test_prod003_launch_safety.py",
        "contracts/test_market_state_pins.py",
        "test_factory_throughput_001.py",
    )),
))


def _relpath(module_path: Path) -> str:
    """``tests/pettripfinder/contracts/x.py`` -> ``contracts/x.py``."""
    p = Path(module_path)
    try:
        rel = p.resolve().relative_to(PTF_TESTS.resolve())
    except ValueError:
        return ""
    return rel.as_posix()


def market_for(relpath: str) -> Optional[str]:
    """The market a module is named for, or ``None``."""
    name = Path(relpath).name
    for market_id, prefixes in MARKET_PREFIXES.items():
        if any(name.startswith(p) for p in prefixes):
            return market_id
    return None


def lanes_for(relpath: str) -> Tuple[str, ...]:
    """Every lane a module belongs to, in :data:`LANES` order. Always
    includes ``full_regression``; includes ``market_targeted`` when the module
    is market-named or a per-market contract module."""
    found: List[str] = []
    if market_for(relpath) or relpath in PER_MARKET_CONTRACT_MODULES:
        found.append(MARKET_TARGETED)
    for lane, patterns in LANE_MEMBERSHIP.items():
        if any(fnmatch.fnmatch(relpath, pat) for pat in patterns):
            found.append(lane)
    found.append(FULL_REGRESSION)
    return tuple(found)


def modules_in_lane(lane: str, *, market: Optional[str] = None) -> List[str]:
    """Module paths (relative to the repo) a lane runs, sorted.

    ``market_targeted`` needs a market: it returns that market's own modules
    plus the per-market contract modules.
    """
    if lane not in LANES:
        raise ValueError("unknown lane %r; lanes are %s" % (lane, ", ".join(LANES)))
    if lane == FULL_REGRESSION:
        return ["tests"]
    out: List[str] = []
    for path in sorted(PTF_TESTS.rglob("test_*.py")):
        rel = _relpath(path)
        if lane == MARKET_TARGETED:
            if market is None:
                raise ValueError("market_targeted needs --market <id>")
            if market_for(rel) == market or rel in PER_MARKET_CONTRACT_MODULES:
                out.append("tests/pettripfinder/" + rel)
        elif lane in lanes_for(rel):
            out.append("tests/pettripfinder/" + rel)
    return out


def describe() -> Dict:
    """The lane table as a document, for the runbook and for tests."""
    table: "OrderedDict[str, List[str]]" = OrderedDict((lane, []) for lane in LANES)
    markets: "OrderedDict[str, List[str]]" = OrderedDict(
        (m, []) for m in MARKET_PREFIXES)
    for path in sorted(PTF_TESTS.rglob("test_*.py")):
        rel = _relpath(path)
        for lane in lanes_for(rel):
            table[lane].append(rel)
        market = market_for(rel)
        if market:
            markets[market].append(rel)
    return OrderedDict((
        ("schema", "ptf-test-lanes/1.0"),
        ("lanes", table),
        ("markets", markets),
        ("per_market_contract_modules", list(PER_MARKET_CONTRACT_MODULES)),
        ("deferred_to_full_regression", [OrderedDict((("node_id", n), ("why", w)))
                                         for n, w in DEFERRED_TO_FULL_REGRESSION]),
        ("normal_flow", [OrderedDict((("step", i + 1), ("lane", lane), ("what", what)))
                         for i, (lane, what) in enumerate(NORMAL_FLOW)]),
    ))


# --------------------------------------------------------------------------- #
# Running a lane and reading the result.
# --------------------------------------------------------------------------- #

def _junit_cases(xml_path: Path) -> Dict[str, str]:
    """``nodeid -> status`` for every testcase in a junit file.

    status is one of passed / failed / error / skipped. The node id is
    rebuilt from ``classname`` + ``name`` the way pytest's xunit2 family
    writes them.
    """
    out: Dict[str, str] = {}
    if not xml_path.is_file():
        return out
    root = ET.parse(str(xml_path)).getroot()
    for case in root.iter("testcase"):
        classname = case.get("classname") or ""
        name = case.get("name") or ""
        file_attr = case.get("file")
        if file_attr:
            nodeid = file_attr.replace("\\", "/")
            parts = classname.split(".")
            # classname is <module dotted path>[.<Class>]; keep the class part.
            module_stem = Path(file_attr).stem
            if module_stem in parts:
                cls = parts[parts.index(module_stem) + 1:]
                nodeid += "::" + "::".join(cls + [name]) if cls else "::" + name
            else:
                nodeid += "::" + name
        else:
            parts = classname.split(".")
            # tests.pettripfinder.test_x.TestY -> tests/pettripfinder/test_x.py::TestY
            path_parts: List[str] = []
            cls_parts: List[str] = []
            for part in parts:
                if cls_parts or (path_parts and part[:1].isupper()):
                    cls_parts.append(part)
                else:
                    path_parts.append(part)
            nodeid = "/".join(path_parts) + ".py"
            if cls_parts:
                nodeid += "::" + "::".join(cls_parts)
            nodeid += "::" + name
        status = "passed"
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                status = "failed" if child.tag == "failure" else child.tag
                break
        out[nodeid] = status
    return out


def read_run(run_dir: Path) -> Dict:
    """Every junit file under ``run_dir`` folded into one status map."""
    run_dir = Path(run_dir)
    cases: Dict[str, str] = {}
    files = sorted(run_dir.glob("*.xml"))
    for xml_path in files:
        cases.update(_junit_cases(xml_path))
    failing = sorted(n for n, s in cases.items() if s in ("failed", "error"))
    return OrderedDict((
        ("schema", SCHEMA_RUN),
        ("run_dir", str(run_dir)),
        ("junit_files", [f.name for f in files]),
        ("collected", len(cases)),
        ("passed", sum(1 for s in cases.values() if s == "passed")),
        ("skipped", sum(1 for s in cases.values() if s == "skipped")),
        ("failed", len(failing)),
        ("failing_node_ids", failing),
    ))


def run_lanes(lanes: Sequence[str], *, out: Path, market: Optional[str] = None,
              extra_args: Sequence[str] = (), python: str = sys.executable) -> Dict:
    """Run each lane into ``out/<lane>.xml`` and return the folded result."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    timing: List[Dict] = []
    for lane in lanes:
        modules = modules_in_lane(lane, market=market)
        if not modules:
            timing.append(OrderedDict((("lane", lane), ("modules", 0),
                                       ("seconds", 0.0), ("exit_code", 5))))
            continue
        xml_path = out / ("%s.xml" % lane)
        deselect: List[str] = []
        if lane != FULL_REGRESSION:
            for nodeid, _why in DEFERRED_TO_FULL_REGRESSION:
                deselect += ["--deselect", nodeid]
        argv = [python, "-m", "pytest", *modules, "-q", "-p", "no:cacheprovider",
                "-o", "junit_family=xunit2", "--junitxml=%s" % xml_path,
                *deselect, *extra_args]
        started = time.monotonic()
        with open(out / ("%s.log" % lane), "w", encoding="utf-8") as log:
            code = subprocess.call(argv, cwd=str(REPO_ROOT), stdout=log,
                                   stderr=subprocess.STDOUT)
        timing.append(OrderedDict((("lane", lane), ("modules", len(modules)),
                                   ("seconds", round(time.monotonic() - started, 1)),
                                   ("exit_code", code))))
    result = read_run(out)
    result["lanes"] = list(lanes)
    result["market"] = market
    result["timing"] = timing
    (out / "run.json").write_text(json.dumps(result, indent=1) + "\n",
                                  encoding="utf-8")
    return result


# --------------------------------------------------------------------------- #
# Baseline manifests and classification.
# --------------------------------------------------------------------------- #

def build_baseline(run: Mapping, *, source_sha: str, label: str = "",
                   note: str = "") -> Dict:
    return OrderedDict((
        ("schema", SCHEMA_BASELINE),
        ("source_sha", source_sha),
        ("label", label),
        ("note", note),
        ("collected", run["collected"]),
        ("passed", run["passed"]),
        ("skipped", run["skipped"]),
        ("failed", run["failed"]),
        ("failing_node_ids", list(run["failing_node_ids"])),
    ))


def _rerun(node_ids: Sequence[str], *, out: Path,
           python: str = sys.executable) -> Dict[str, str]:
    """Re-run the named nodes in one isolated pytest process."""
    if not node_ids:
        return {}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    xml_path = out / "rerun.xml"
    argv = [python, "-m", "pytest", *node_ids, "-q", "-p", "no:cacheprovider",
            "-o", "junit_family=xunit2", "--junitxml=%s" % xml_path]
    with open(out / "rerun.log", "w", encoding="utf-8") as log:
        subprocess.call(argv, cwd=str(REPO_ROOT), stdout=log,
                        stderr=subprocess.STDOUT)
    return _junit_cases(xml_path)


def classify(run: Mapping, baseline: Mapping, *,
             expected_epoch_change: Iterable[str] = (),
             rerun_results: Optional[Mapping[str, str]] = None) -> Dict:
    """Every failing node id in ``run`` gets exactly one class.

    ``rerun_results`` is ``nodeid -> status`` from an isolated re-run of the
    candidates; a node that passed there is a harness flake. Without a
    re-run, nothing is called a flake.
    """
    if baseline.get("schema") != SCHEMA_BASELINE:
        raise ValueError("baseline is not a %s document" % SCHEMA_BASELINE)
    pre = set(baseline["failing_node_ids"])
    expected = set(expected_epoch_change)
    rerun = dict(rerun_results or {})
    classes: "OrderedDict[str, List[str]]" = OrderedDict((c, []) for c in CLASSES)
    for nodeid in run["failing_node_ids"]:
        if nodeid in pre:
            classes[PRE_EXISTING].append(nodeid)
        elif nodeid in expected:
            classes[EXPECTED_EPOCH_CHANGE].append(nodeid)
        elif rerun.get(nodeid) == "passed":
            classes[TEST_HARNESS_FLAKE].append(nodeid)
        else:
            classes[TRUE_NEW_FAILURE].append(nodeid)
    resolved = sorted(pre - set(run["failing_node_ids"]))
    return OrderedDict((
        ("schema", SCHEMA_CLASSIFICATION),
        ("baseline_source_sha", baseline["source_sha"]),
        ("run_dir", run.get("run_dir")),
        ("collected", run["collected"]),
        ("failed", run["failed"]),
        ("counts", OrderedDict((c, len(v)) for c, v in classes.items())),
        ("classes", classes),
        ("baseline_failures_now_passing", resolved),
        ("clean", not classes[TRUE_NEW_FAILURE]),
    ))


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #

def _read_json(path: Path) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, doc: Mapping) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")


def _lines(path: Optional[str]) -> List[str]:
    if not path:
        return []
    return [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("plan", help="print the lane table and the normal flow")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("run", help="run one or more lanes into junit files")
    s.add_argument("--lane", action="append", required=True, choices=LANES)
    s.add_argument("--market")
    s.add_argument("--out", required=True)
    s.add_argument("pytest_args", nargs="*")

    s = sub.add_parser("baseline", help="write a baseline manifest from a run")
    s.add_argument("--run", required=True)
    s.add_argument("--sha", required=True)
    s.add_argument("--label", default="")
    s.add_argument("--note", default="")
    s.add_argument("--out", required=True)

    s = sub.add_parser("classify", help="classify a run against a baseline")
    s.add_argument("--baseline", required=True)
    s.add_argument("--run", required=True)
    s.add_argument("--expected-epoch-change",
                   help="file of node ids the order expected to move")
    s.add_argument("--rerun-flakes", action="store_true",
                   help="re-run unclassified failures once, in isolation")
    s.add_argument("--out")

    args = p.parse_args(argv)

    if args.command == "plan":
        doc = describe()
        if args.json:
            print(json.dumps(doc, indent=1))
            return 0
        for step in doc["normal_flow"]:
            print("%d. %-24s %s" % (step["step"], step["lane"], step["what"]))
        print()
        for lane, modules in doc["lanes"].items():
            print("%-24s %d modules" % (lane, len(modules)))
        return 0

    if args.command == "run":
        result = run_lanes(args.lane, out=Path(args.out), market=args.market,
                           extra_args=args.pytest_args)
        print(json.dumps({k: result[k] for k in
                          ("collected", "passed", "skipped", "failed", "timing")},
                         indent=1))
        return 0 if result["failed"] == 0 else 1

    if args.command == "baseline":
        run = read_run(Path(args.run))
        doc = build_baseline(run, source_sha=args.sha, label=args.label,
                             note=args.note)
        _write_json(Path(args.out), doc)
        print("%s: %d collected, %d failing" % (args.out, doc["collected"],
                                                doc["failed"]))
        return 0

    if args.command == "classify":
        run = read_run(Path(args.run))
        baseline = _read_json(Path(args.baseline))
        expected = _lines(args.expected_epoch_change)
        rerun: Dict[str, str] = {}
        if args.rerun_flakes:
            first = classify(run, baseline, expected_epoch_change=expected)
            rerun = _rerun(first["classes"][TRUE_NEW_FAILURE],
                           out=Path(args.run) / "rerun")
        doc = classify(run, baseline, expected_epoch_change=expected,
                       rerun_results=rerun)
        if args.out:
            _write_json(Path(args.out), doc)
        print(json.dumps(doc["counts"], indent=1))
        for nodeid in doc["classes"][TRUE_NEW_FAILURE]:
            print("TRUE_NEW_FAILURE", nodeid)
        return 0 if doc["clean"] else 1

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
