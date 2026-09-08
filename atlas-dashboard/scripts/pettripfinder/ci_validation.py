"""ATLAS-THROUGHPUT-006 -- remote validation: shards, node-id completeness,
change-class dispatch, and the trusted CI receipt.

005 made a release a composition rather than a rebuild. What it did not fix is
where the expensive proof runs: a broad audit still occupies the founder's
desktop for an hour while every market worker waits. This module moves that
proof off the desktop WITHOUT moving the waste with it.

Three ideas, in order of importance:

1. **Most releases must not need a broad run at all.** ``required_shards``
   consumes Regression V2's existing plan, so a proven data-only market
   authority change requests ZERO remote jobs and a shared-runtime change
   requests all four. A remote runner that runs 17,000 tests on every release
   is the old waste with a bigger bill.

2. **A sharded run is only a run if every planned node id is accounted for
   exactly once.** ``verify_completeness`` fails on a missing node, an
   unintended duplicate, a collection error, a missing shard or a shard that
   timed out. Partial green is not green.

3. **"CI passed" is a string, not evidence.** ``build_receipt`` emits a
   machine-verifiable document binding the commit, the candidate digest, the
   change class, the dependency digest, the shards required and completed, the
   node-id accounting and the failure classification; ``receipt_problems``
   is what the release coordinator calls before it will treat a broad
   validation as satisfied.

The shard split is measured, not guessed. See ``plan_shards``: the profiler's
per-test timings from a real broad run drive a longest-processing-time
partition at MODULE granularity, because a module's expensive session fixtures
are exactly what splitting it would duplicate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = SMP.REPO_ROOT
REPORTS = SMP.LAUNCH_PACKAGE / "reports"

CI_POLICY_VERSION = "ptf-ci-policy/1.0"
RECEIPT_SCHEMA = "ptf-ci-validation-receipt/1.0"
SHARD_MANIFEST_SCHEMA = "ptf-ci-shard-manifest/1.0"
COMPLETENESS_SCHEMA = "ptf-ci-node-completeness/1.0"

#: The four categories the order names. Which MODULES land in which shard is
#: decided by measurement (``plan_shards``); the categories are how a reader
#: understands the split, not how it is computed.
CONTRACTS_CORE = "CONTRACTS_CORE"
MARKET_GROUP_A = "MARKET_GROUP_A"
MARKET_GROUP_B = "MARKET_GROUP_B"
ASSEMBLER_DEPLOYMENT_HISTORY = "ASSEMBLER_DEPLOYMENT_HISTORY"
CATEGORIES = (CONTRACTS_CORE, MARKET_GROUP_A, MARKET_GROUP_B, ASSEMBLER_DEPLOYMENT_HISTORY)

#: Modules whose cost is dominated by the website-generation chain and the
#: multi-market assembly. Measured, not assumed: on the 005 audit these three
#: are 68% of the whole suite.
_ASSEMBLY_HEAVY = (
    "tests/website_generation/",
    "tests/pettripfinder/test_global_deployment_architecture_045.py",
    "tests/pettripfinder/test_per_market_release_contracts.py",
    "tests/pettripfinder/test_prod005_netlify_config.py",
    "tests/pettripfinder/test_prod004_verified_only.py",
    "tests/pettripfinder/test_two_market_compat.py",
    "tests/pettripfinder/test_global_assembler.py",
    "tests/pettripfinder/test_generate_columbus_site.py",
    "tests/pettripfinder/test_launch_participation_046.py",
    "tests/pettripfinder/test_deployment",
    "tests/pettripfinder/test_production_deploy",
)
_CORE = (
    "tests/pettripfinder/contracts/",
    "tests/pettripfinder/test_regression_delta_001.py",
    "tests/pettripfinder/test_factory_throughput_001.py",
    "tests/pettripfinder/test_atlas_throughput_",
    "tests/pettripfinder/test_identity_routing.py",
    "tests/pettripfinder/test_policy_",
    "tests/pettripfinder/importer/",
    "tests/pettripfinder/discovery/",
)

#: Shard failure modes. Every one of them fails the RUN, not just the shard.
SHARD_MISSING = "SHARD_MISSING"
SHARD_TIMEOUT = "SHARD_TIMEOUT"
SHARD_CANCELLED = "SHARD_CANCELLED"
COLLECTION_ERROR = "COLLECTION_ERROR"
NODE_MISSING = "NODE_MISSING"
NODE_DUPLICATED = "NODE_DUPLICATED"
NODE_UNPLANNED = "NODE_UNPLANNED"
ARTIFACT_MISSING = "ARTIFACT_MISSING"

#: Receipt refusals.
RECEIPT_INCOMPLETE = "RECEIPT_INCOMPLETE"
RECEIPT_WRONG_CANDIDATE = "RECEIPT_WRONG_CANDIDATE"
RECEIPT_WRONG_COMMIT = "RECEIPT_WRONG_COMMIT"
RECEIPT_WRONG_DEPENDENCY_DIGEST = "RECEIPT_WRONG_DEPENDENCY_DIGEST"
RECEIPT_STALE = "RECEIPT_STALE"
RECEIPT_SHARDS_INCOMPLETE = "RECEIPT_SHARDS_INCOMPLETE"
RECEIPT_NODES_INCOMPLETE = "RECEIPT_NODES_INCOMPLETE"
RECEIPT_TRUE_NEW = "RECEIPT_TRUE_NEW"
RECEIPT_POLICY_VERSION = "RECEIPT_POLICY_VERSION"
NOT_REQUIRED_BY_POLICY = "NOT_REQUIRED_BY_POLICY"

#: A receipt older than this cannot satisfy a release: the tree it validated is
#: no longer plausibly the tree being released.
RECEIPT_MAX_AGE_SECONDS = 7 * 24 * 3600


class CIValidationError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Phase 3: the measured test inventory.
# --------------------------------------------------------------------------- #

@dataclass
class MeasuredModule:
    module: str
    tests: int = 0
    seconds: float = 0.0
    peak_mb: float = 0.0
    lanes: Set[str] = field(default_factory=set)
    markets: Set[str] = field(default_factory=set)
    assembly: bool = False

    def to_dict(self) -> "OrderedDict[str, Any]":
        return OrderedDict((
            ("module", self.module), ("tests", self.tests),
            ("measured_seconds", round(self.seconds, 3)),
            ("peak_working_set_mb_observed", round(self.peak_mb, 1)),
            ("lanes", sorted(self.lanes)), ("markets", sorted(self.markets)),
            ("assembly_usage", self.assembly), ("category", categorize(self.module)),
        ))


def categorize(module: str) -> str:
    """Which of the order's four categories a module belongs to."""
    m = module.replace("\\", "/")
    if any(m.startswith(p) or m == p for p in _ASSEMBLY_HEAVY):
        return ASSEMBLER_DEPLOYMENT_HISTORY
    if any(m.startswith(p) for p in _CORE):
        return CONTRACTS_CORE
    if m.startswith("tests/pettripfinder/"):
        return MARKET_GROUP_A                       # split A/B by measurement below
    return CONTRACTS_CORE


def load_measurements(profile_jsonl: Path) -> "OrderedDict[str, MeasuredModule]":
    """Per-module measured cost from a real broad run's profiler output."""
    out: "OrderedDict[str, MeasuredModule]" = OrderedDict()
    path = Path(profile_jsonl)
    if not path.is_file():
        raise CIValidationError("no profiler output at %s; a shard plan is measured, never guessed" % path)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("kind") != "test":
            continue
        module = str(row.get("module") or "").replace("\\", "/")
        if not module:
            continue
        rec = out.get(module)
        if rec is None:
            rec = out[module] = MeasuredModule(module=module)
        rec.tests += 1
        rec.seconds += float(row.get("total_seconds") or 0.0)
        rec.peak_mb = max(rec.peak_mb, float(row.get("peak_working_set_mb") or 0.0))
        for lane in row.get("lanes") or ():
            rec.lanes.add(str(lane))
        if row.get("market"):
            rec.markets.add(str(row["market"]))
    for module, rec in out.items():
        rec.assembly = categorize(module) == ASSEMBLER_DEPLOYMENT_HISTORY
    return OrderedDict(sorted(out.items()))


# --------------------------------------------------------------------------- #
# Phase 4: the shards.
# --------------------------------------------------------------------------- #

def plan_shards(measurements: Mapping[str, MeasuredModule], *, shard_count: int = 4
                ) -> "OrderedDict[str, Any]":
    """Balance the suite across ``shard_count`` jobs by MEASURED duration.

    Two rules the measurements force:

    * **Module granularity.** A module's session and module fixtures are the
      expensive part (the website-generation chain peaks near 9 GB). Splitting
      a module across shards would run that fixture twice, which is the exact
      trap ``pytest -n auto`` falls into.
    * **The critical path is a single module.** On the 005 audit
      ``test_pettripfinder_demo_media.py`` alone is 1,375.7 s -- more than a
      perfect quarter of 3,621.7 s. No four-way split can be faster than its
      slowest indivisible unit, so the wall clock floor is that module and
      adding shards beyond four buys nothing until it is itself divisible.
      That is a finding, not a defect, and it is recorded in the manifest as
      ``critical_path``.

    Longest-processing-time first: sort modules by measured cost descending and
    put each on the currently-lightest shard. LPT is within 4/3 of optimal and
    is stable, which matters more here than optimality -- a shard plan that
    reshuffles on every run cannot be reviewed.
    """
    if shard_count < 1:
        raise CIValidationError("shard_count must be >= 1")
    ordered = sorted(measurements.values(), key=lambda m: (-m.seconds, m.module))
    shards: List[Dict[str, Any]] = [
        {"shard": i + 1, "modules": [], "seconds": 0.0, "tests": 0, "peak_mb": 0.0}
        for i in range(shard_count)
    ]
    for rec in ordered:
        target = min(shards, key=lambda s: (s["seconds"], s["shard"]))
        target["modules"].append(rec.module)
        target["seconds"] += rec.seconds
        target["tests"] += rec.tests
        target["peak_mb"] = max(target["peak_mb"], rec.peak_mb)
    total = sum(m.seconds for m in measurements.values())
    critical = ordered[0] if ordered else None
    for shard in shards:
        shard["modules"] = sorted(shard["modules"])
        shard["seconds"] = round(shard["seconds"], 1)
        shard["peak_mb"] = round(shard["peak_mb"], 1)
        heaviest = max(shard["modules"], key=lambda m: measurements[m].seconds) if shard["modules"] else None
        shard["heaviest_module"] = heaviest
        shard["heaviest_module_seconds"] = round(measurements[heaviest].seconds, 1) if heaviest else 0.0
        shard["category"] = categorize(heaviest) if heaviest else CONTRACTS_CORE
        shard["module_count"] = len(shard["modules"])
    slowest = max((s["seconds"] for s in shards), default=0.0)
    return OrderedDict((
        ("schema", SHARD_MANIFEST_SCHEMA),
        ("ci_policy_version", CI_POLICY_VERSION),
        ("shard_count", shard_count),
        ("modules", len(measurements)),
        ("tests", sum(m.tests for m in measurements.values())),
        ("measured_total_seconds", round(total, 1)),
        ("balanced_by", "measured wall-clock duration per module, longest-processing-time first"),
        ("not_balanced_by", "test count -- the suite's cost is concentrated in a few modules, so counting "
                            "tests would put 8,900 cheap tests opposite 18 expensive ones"),
        ("memory_note", "peak_working_set_mb is the PROCESS peak observed while a module ran, which for a "
                        "late module includes everything before it. It bounds a shard; it is not that "
                        "module's own footprint."),
        ("category_note", "shards are NOT grouped by category: the assembly-heavy category alone measures "
                          "about 2,800 s, so grouping it would roughly double the wall clock. Each shard is "
                          "labelled by its heaviest module's category."),
        ("granularity", "module -- a module's expensive session fixtures must not be duplicated"),
        ("critical_path", OrderedDict((
            ("module", critical.module if critical else None),
            ("seconds", round(critical.seconds, 1) if critical else 0.0),
            ("tests", critical.tests if critical else 0),
            ("peak_working_set_mb", round(critical.peak_mb, 1) if critical else 0.0),
            ("why", "no split into jobs can finish faster than its slowest indivisible module; "
                    "more shards buy nothing until this one is itself divisible"),
        ))),
        ("projected_wall_seconds", round(slowest, 1)),
        ("projected_aggregate_seconds", round(total, 1)),
        ("shards", [OrderedDict(sorted(s.items())) for s in shards]),
    ))


def _dominant_category(modules: Sequence[str], measurements: Mapping[str, MeasuredModule]) -> str:
    weight: Dict[str, float] = {}
    for module in modules:
        rec = measurements.get(module)
        weight[categorize(module)] = weight.get(categorize(module), 0.0) + (rec.seconds if rec else 0.0)
    return max(weight.items(), key=lambda kv: kv[1])[0] if weight else CONTRACTS_CORE


def shard_of(manifest: Mapping, module: str) -> Optional[int]:
    module = module.replace("\\", "/")
    for shard in manifest.get("shards") or ():
        if module in (shard.get("modules") or ()):
            return int(shard["shard"])
    return None


# --------------------------------------------------------------------------- #
# Phase 5: the node-id completeness contract.
# --------------------------------------------------------------------------- #

def collect_node_ids(targets: Sequence[str] = ("tests",), *,
                     python: Optional[str] = None,
                     cwd: Optional[Path] = None) -> Tuple[List[str], List[str]]:
    """``(node_ids, errors)`` from a real pytest collection.

    Collection is the planning input, so a collection ERROR is a run failure,
    never an empty shard.
    """
    argv = [python or sys.executable, "-m", "pytest", *targets, "--collect-only", "-q",
            "-p", "no:cacheprovider"]
    proc = subprocess.run(argv, cwd=str(cwd or REPO_ROOT), capture_output=True, text=True)
    nodes: List[str] = []
    errors: List[str] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if "::" in line and not line.startswith(("=", "<", "ERROR", "E ")):
            nodes.append(line.replace("\\", "/"))
        elif line.lower().startswith("error"):
            errors.append(line[:200])
    if proc.returncode not in (0, 5) and not errors:
        errors.append("pytest --collect-only exited %s" % proc.returncode)
    return nodes, errors


def module_of(node_id: str) -> str:
    return node_id.split("::", 1)[0].replace("\\", "/")


def assign_nodes(manifest: Mapping, node_ids: Sequence[str]
                 ) -> "OrderedDict[str, Any]":
    """Partition collected node ids across the planned shards."""
    by_shard: "OrderedDict[int, List[str]]" = OrderedDict(
        (int(s["shard"]), []) for s in manifest.get("shards") or ())
    unassigned: List[str] = []
    for node in node_ids:
        shard = shard_of(manifest, module_of(node))
        if shard is None:
            unassigned.append(node)
        else:
            by_shard[shard].append(node)
    return OrderedDict((
        ("by_shard", OrderedDict((str(k), sorted(v)) for k, v in by_shard.items())),
        ("unassigned", sorted(unassigned)),
    ))


def verify_completeness(planned: Sequence[str], executed: Mapping[str, Sequence[str]], *,
                        excluded: Optional[Mapping[str, str]] = None,
                        shards_required: Sequence[int] = (),
                        shards_completed: Sequence[int] = (),
                        collection_errors: Sequence[str] = (),
                        duplicates_allowed: Sequence[str] = ()) -> "OrderedDict[str, Any]":
    """EXECUTED ∪ EXPLICITLY_EXCLUDED == PLANNED, and shards must not overlap.

    ``executed`` maps a shard id to the node ids that shard actually ran.
    Anything less than a complete, disjoint account is a failed RUN -- a
    missing shard, a timed-out shard, a silent skip and a collection error all
    land here rather than being averaged away into "mostly passed".
    """
    excluded = OrderedDict(excluded or {})
    problems: List["OrderedDict[str, Any]"] = []
    planned_set = set(planned)

    missing_shards = sorted(set(int(s) for s in shards_required) - set(int(s) for s in shards_completed))
    for shard in missing_shards:
        problems.append(OrderedDict((("code", SHARD_MISSING), ("shard", shard),
                                     ("detail", "shard %s was required and did not complete" % shard))))
    for err in collection_errors:
        problems.append(OrderedDict((("code", COLLECTION_ERROR), ("detail", str(err)[:200]))))

    seen: Dict[str, List[str]] = {}
    for shard, nodes in (executed or {}).items():
        for node in nodes:
            seen.setdefault(node, []).append(str(shard))
    allowed_dupes = set(duplicates_allowed)
    for node, shards in sorted(seen.items()):
        if len(shards) > 1 and node not in allowed_dupes:
            problems.append(OrderedDict((("code", NODE_DUPLICATED), ("node_id", node),
                                         ("shards", shards))))
    executed_set = set(seen)
    unplanned = sorted(executed_set - planned_set)
    for node in unplanned[:50]:
        problems.append(OrderedDict((("code", NODE_UNPLANNED), ("node_id", node))))
    accounted = executed_set | set(excluded)
    missing = sorted(planned_set - accounted)
    for node in missing[:50]:
        problems.append(OrderedDict((("code", NODE_MISSING), ("node_id", node))))

    return OrderedDict((
        ("schema", COMPLETENESS_SCHEMA),
        ("planned", len(planned_set)),
        ("executed", len(executed_set)),
        ("excluded", len(excluded)),
        ("exclusions", OrderedDict(sorted(excluded.items()))),
        ("shards_required", sorted(int(s) for s in shards_required)),
        ("shards_completed", sorted(int(s) for s in shards_completed)),
        ("duplicates_allowed", sorted(allowed_dupes)),
        ("missing_count", len(missing)),
        ("unplanned_count", len(unplanned)),
        ("problems", problems),
        ("complete", not problems),
    ))


# --------------------------------------------------------------------------- #
# Phase 8: what a change class actually requires remotely.
# --------------------------------------------------------------------------- #

#: The release surfaces Regression V2 already computes, mapped to the remote
#: jobs they owe. This table is the whole point of 006: it is what stops a
#: remote runner becoming an expensive way to repeat the old waste.
SURFACE_JOBS: "OrderedDict[str, Tuple[str, str]]" = OrderedDict((
    (RD.SURFACE_SHARED_SCHEMA_CHANGE, ("ALL",
     "a schema is read by every market and every renderer")),
    (RD.SURFACE_SHARED_RUNTIME_CHANGE, ("ALL",
     "shared runtime is what eleven markets derive from")),
    (RD.SURFACE_ASSEMBLER_CHANGE, ("ALL",
     "the assembler composes every market's bytes, and the modules that prove per-market "
     "output are spread across every shard by the duration balance")),
    (RD.SURFACE_DEPLOYMENT_CHANGE, ("DEPLOYMENT",
     "manifests, participation, authorizations and records: only the shards holding "
     "deployment-architecture modules")),
    (RD.SURFACE_CLASSIFIER_TEST_INFRA_CHANGE, ("ALL",
     "the classifier decides what runs, so it cannot narrow its own validation")),
))


def shards_covering(manifest: Mapping, predicate: Callable[[str], bool]) -> List[int]:
    """The shard ids holding at least one module the predicate accepts."""
    out: Set[int] = set()
    for shard in manifest.get("shards") or ():
        if any(predicate(m) for m in shard.get("modules") or ()):
            out.add(int(shard["shard"]))
    return sorted(out)


def all_shards(manifest: Mapping) -> List[int]:
    return sorted(int(s["shard"]) for s in manifest.get("shards") or ())


#: Scopes a change can owe. With a duration-balanced split most broad
#: requirements resolve to every shard -- which is the honest answer, and the
#: reason the saving that matters is NOT running broad at all for a proven
#: data-only release.
SCOPE_NONE = "NONE"
SCOPE_DEPLOYMENT = "DEPLOYMENT"
SCOPE_ALL = "ALL"


def required_shards(classification: Mapping, plan: Mapping, *,
                    manifest: Optional[Mapping] = None,
                    fast_lane: Optional[Mapping] = None) -> "OrderedDict[str, Any]":
    """Which remote shards a change owes, from Regression V2's own verdict.

    The default for an unclassified or mixed change is every shard. The
    exception is a change V2 has already proven narrow: a proven data-only
    market authority change with an eligible FAST receipt owes ZERO remote
    jobs, so the ordinary release path reports REMOTE_BROAD_JOBS = 0.
    """
    surfaces = sorted({RD.release_surface_of(row) for row in classification.get("changed_files") or ()})
    full_required = bool(plan.get("full_regression_required"))
    fast = fast_lane or {}
    fast_satisfies = (str(fast.get("FULL_REGRESSION_REQUIRED", "YES")).upper() == "NO")

    scope = SCOPE_NONE
    reasons: List["OrderedDict[str, Any]"] = []
    for surface in surfaces:
        entry = SURFACE_JOBS.get(surface)
        if entry is None:
            continue
        want, why = entry
        scope = SCOPE_ALL if SCOPE_ALL in (want, scope) else want
        reasons.append(OrderedDict((("surface", surface), ("scope", want), ("why", why))))

    if fast_satisfies:
        scope = SCOPE_NONE
        reasons = [OrderedDict((
            ("surface", "MARKET_AUTHORITY_DATA_ONLY"), ("scope", SCOPE_NONE),
            ("why", "FAST_DATA_ONLY_RELEASE proved this package on its own evidence; "
                    "Regression V2 says FULL_REGRESSION_REQUIRED = NO"),
        ))]
    elif full_required and scope == SCOPE_NONE:
        scope = SCOPE_ALL
        reasons.append(OrderedDict((
            ("surface", "UNKNOWN_OR_MIXED"), ("scope", SCOPE_ALL),
            ("why", "V2 requires a broad regression and no narrower surface claims the change: "
                    "fall broad rather than guess"),
        )))

    if scope == SCOPE_NONE:
        shards: List[Any] = []
    elif manifest is None:
        shards = list(CATEGORIES)
    elif scope == SCOPE_ALL:
        shards = all_shards(manifest)
    else:
        shards = shards_covering(manifest, lambda m: categorize(m) == ASSEMBLER_DEPLOYMENT_HISTORY)
    return OrderedDict((
        ("ci_policy_version", CI_POLICY_VERSION),
        ("release_surfaces", surfaces),
        ("FULL_REGRESSION_REQUIRED", "YES" if full_required else "NO"),
        ("FAST_DATA_ONLY_RELEASE_SATISFIES", "YES" if fast_satisfies else "NO"),
        ("scope", scope),
        ("REMOTE_BROAD_JOBS", len(shards)),
        ("shards_required", shards),
        ("reasons", reasons),
        ("dispatch", "REMOTE_BROAD" if shards else "NONE"),
    ))


def plan_for_head(base: str, head: str = RD.WORKTREE, *,
                  market_id: Optional[str] = None) -> "OrderedDict[str, Any]":
    """Classify a change with V2 and say what it owes remotely."""
    classification = RD.classify_change(base, head)
    plan = RD.plan_for(classification)
    fast = classification.get("fast_data_only_release")
    return OrderedDict((
        ("base", base), ("head", head),
        ("change_classes", list(classification.get("change_classes") or ())),
        ("required", required_shards(classification, plan, fast_lane=fast)),
        ("full_regression_reason", RD._full_reason(plan)),
    ))


# --------------------------------------------------------------------------- #
# Phase 9-10: the trusted CI validation receipt.
# --------------------------------------------------------------------------- #

def dependency_digest(paths: Optional[Sequence[str]] = None) -> str:
    """A digest over the inputs a remote environment must match.

    Deliberately narrow: the lockfiles and the interpreter contract. The tree
    itself is bound by the source commit, and the deployable bytes by the
    candidate digest -- this is what would make a receipt from a DIFFERENT
    dependency set unusable.
    """
    paths = list(paths or ("requirements.txt", "requirements-dev.txt", "pytest.ini"))
    h = hashlib.sha256()
    for rel in sorted(paths):
        path = REPO_ROOT / rel
        h.update(rel.encode("utf-8"))
        h.update(path.read_bytes() if path.is_file() else b"<absent>")
    return "sha256:" + h.hexdigest()


def build_receipt(*, ci_run_id: str, source_commit: str, change_class: Sequence[str],
                  shards_required: Sequence[Any], shards_completed: Sequence[Any],
                  completeness: Mapping, counts: Mapping,
                  pre_existing: Sequence[str], true_new: Sequence[str],
                  candidate_digest: Optional[str] = None,
                  parent_release_digest: Optional[str] = None,
                  artifact_digests: Optional[Mapping[str, str]] = None,
                  environment: Optional[Mapping] = None,
                  started_at: Optional[str] = None, ended_at: Optional[str] = None,
                  dependency: Optional[str] = None) -> "OrderedDict[str, Any]":
    """The document the release coordinator will actually verify."""
    env = OrderedDict(environment or OrderedDict((
        ("environment_id", os.environ.get("PTF_CI_ENVIRONMENT", "local")),
        ("platform", sys.platform),
        ("python_version", sys.version.split()[0]),
        ("node_version", _node_version()),
    )))
    receipt = OrderedDict((
        ("schema", RECEIPT_SCHEMA),
        ("ci_policy_version", CI_POLICY_VERSION),
        ("validation_policy_version", RD.SCHEMA_MATRIX if hasattr(RD, "SCHEMA_MATRIX") else CI_POLICY_VERSION),
        ("ci_run_id", ci_run_id),
        ("source_commit", source_commit),
        ("candidate_digest", candidate_digest),
        ("parent_release_digest", parent_release_digest),
        ("change_class", list(change_class)),
        ("dependency_digest", dependency or dependency_digest()),
        ("shards_required", sorted(str(s) for s in shards_required)),
        ("shards_completed", sorted(str(s) for s in shards_completed)),
        ("node_ids_expected", int(completeness.get("planned") or 0)),
        ("node_ids_executed", int(completeness.get("executed") or 0)),
        ("node_ids_excluded", int(completeness.get("excluded") or 0)),
        ("node_completeness", OrderedDict((
            ("complete", bool(completeness.get("complete"))),
            ("missing_count", completeness.get("missing_count")),
            ("unplanned_count", completeness.get("unplanned_count")),
            ("problems", list(completeness.get("problems") or ())[:20]),
        ))),
        ("counts", OrderedDict(sorted((counts or {}).items()))),
        ("pre_existing_failures", sorted(pre_existing)),
        ("true_new_failures", sorted(true_new)),
        ("artifact_digests", OrderedDict(sorted((artifact_digests or {}).items()))),
        ("environment", env),
        ("started_at", started_at or _iso()),
        ("ended_at", ended_at or _iso()),
        ("result", "PASS" if (not true_new and completeness.get("complete")
                              and not set(map(str, shards_required)) - set(map(str, shards_completed)))
         else "FAIL"),
    ))
    receipt["receipt_digest"] = SMP.sha256_text(SMP.canonical_json(
        OrderedDict((k, v) for k, v in receipt.items() if k != "receipt_digest")))
    return receipt


def receipt_problems(receipt: Optional[Mapping], *, required: Mapping,
                     source_commit: Optional[str] = None,
                     candidate_digest: Optional[str] = None,
                     dependency: Optional[str] = None,
                     now: Optional[float] = None,
                     max_age_seconds: int = RECEIPT_MAX_AGE_SECONDS) -> List[str]:
    """Every reason this receipt does not satisfy this release.

    A release whose policy needs no broad run is not "missing" a receipt: it
    returns ``NOT_REQUIRED_BY_POLICY`` and no problems at all.
    """
    if not required.get("shards_required"):
        return []
    if receipt is None:
        return ["%s: policy requires shards %s and no CI receipt was supplied"
                % (RECEIPT_INCOMPLETE, required.get("shards_required"))]
    problems: List[str] = []
    if receipt.get("schema") != RECEIPT_SCHEMA:
        problems.append("%s: schema is %r" % (RECEIPT_INCOMPLETE, receipt.get("schema")))
    for field_name in ("ci_run_id", "source_commit", "shards_completed", "counts",
                       "node_completeness", "environment", "receipt_digest"):
        if receipt.get(field_name) in (None, "", [], {}):
            problems.append("%s: %s is empty" % (RECEIPT_INCOMPLETE, field_name))
    expected = SMP.sha256_text(SMP.canonical_json(
        OrderedDict((k, v) for k, v in receipt.items() if k != "receipt_digest")))
    if receipt.get("receipt_digest") != expected:
        problems.append("%s: the receipt does not hash to its own contents" % RECEIPT_INCOMPLETE)
    if source_commit and receipt.get("source_commit") != source_commit:
        problems.append("%s: receipt validated %s, this release is %s"
                        % (RECEIPT_WRONG_COMMIT, str(receipt.get("source_commit"))[:12],
                           source_commit[:12]))
    if candidate_digest and receipt.get("candidate_digest") not in (None, candidate_digest):
        problems.append("%s: receipt binds candidate %s, this candidate is %s"
                        % (RECEIPT_WRONG_CANDIDATE, str(receipt.get("candidate_digest"))[7:23],
                           candidate_digest[7:23]))
    if candidate_digest and receipt.get("candidate_digest") is None:
        problems.append("%s: receipt binds no candidate digest" % RECEIPT_INCOMPLETE)
    expected_dep = dependency or dependency_digest()
    if receipt.get("dependency_digest") != expected_dep:
        problems.append("%s: receipt ran against %s, this tree is %s"
                        % (RECEIPT_WRONG_DEPENDENCY_DIGEST,
                           str(receipt.get("dependency_digest"))[7:19], expected_dep[7:19]))
    missing_shards = sorted(set(str(s) for s in required.get("shards_required") or ())
                            - set(str(s) for s in receipt.get("shards_completed") or ()))
    if missing_shards:
        problems.append("%s: policy requires %s, receipt completed %s"
                        % (RECEIPT_SHARDS_INCOMPLETE, missing_shards,
                           list(receipt.get("shards_completed") or ())))
    if not (receipt.get("node_completeness") or {}).get("complete"):
        problems.append("%s: the run did not account for every planned node id"
                        % RECEIPT_NODES_INCOMPLETE)
    if receipt.get("true_new_failures"):
        problems.append("%s: %d true-new failures"
                        % (RECEIPT_TRUE_NEW, len(receipt["true_new_failures"])))
    ended = receipt.get("ended_at")
    if ended:
        try:
            age = (now if now is not None else time.time()) - _epoch(str(ended))
            if age > max_age_seconds:
                problems.append("%s: the receipt is %.1f days old" % (RECEIPT_STALE, age / 86400.0))
        except ValueError:
            problems.append("%s: ended_at %r is not a timestamp" % (RECEIPT_INCOMPLETE, ended))
    return problems


def broad_validation_state(required: Mapping, receipt: Optional[Mapping], **kwargs: Any
                           ) -> "OrderedDict[str, Any]":
    """What the release coordinator records about remote validation."""
    if not required.get("shards_required"):
        return OrderedDict((("state", NOT_REQUIRED_BY_POLICY),
                            ("REMOTE_BROAD_JOBS", 0),
                            ("why", (required.get("reasons") or [{}])[0].get("why", "")),
                            ("problems", [])))
    problems = receipt_problems(receipt, required=required, **kwargs)
    return OrderedDict((
        ("state", "SATISFIED" if not problems else "REFUSED"),
        ("REMOTE_BROAD_JOBS", len(required.get("shards_required") or ())),
        ("ci_run_id", (receipt or {}).get("ci_run_id")),
        ("receipt_digest", (receipt or {}).get("receipt_digest")),
        ("problems", problems),
    ))


# --------------------------------------------------------------------------- #
# Failure classification, reusing 001-005's node-id doctrine.
# --------------------------------------------------------------------------- #

_NORMALISE = re.compile(r"0x[0-9a-f]+|[A-Za-z]:\\\\[^\s'\"]+|/tmp/[^\s'\"]+|\d{4}-\d{2}-\d{2}T[\d:.]+Z?")


def failure_signature(message: str) -> str:
    """A failure's identity, with the parts that legitimately move removed."""
    return SMP.sha256_text(_NORMALISE.sub("<v>", (message or "").strip())[:2000])


def classify_failures(failing: Mapping[str, str], baseline: Mapping) -> "OrderedDict[str, Any]":
    """PRE_EXISTING vs TRUE_NEW by node id AND failure signature.

    A node in the baseline that now fails for a materially different reason is
    TRUE_NEW: the baseline records that a test fails, not a licence for it to
    fail in new ways.
    """
    baseline_nodes = set(baseline.get("failing_node_ids") or baseline.get("failures") or ())
    signatures = dict(baseline.get("failure_signatures") or {})
    pre_existing: List[str] = []
    true_new: List[str] = []
    changed: List["OrderedDict[str, Any]"] = []
    for node, message in sorted(failing.items()):
        if node not in baseline_nodes:
            true_new.append(node)
            continue
        expected = signatures.get(node)
        if expected and failure_signature(message) != expected:
            true_new.append(node)
            changed.append(OrderedDict((("node_id", node), ("why", "same node, different failure"))))
        else:
            pre_existing.append(node)
    now_passing = sorted(baseline_nodes - set(failing))
    return OrderedDict((
        ("PRE_EXISTING", pre_existing), ("TRUE_NEW", true_new),
        ("changed_signature", changed),
        ("BASELINE_NOW_PASSING", now_passing),
        ("signature_checked", bool(signatures)),
        ("counts", OrderedDict((("PRE_EXISTING", len(pre_existing)), ("TRUE_NEW", len(true_new)),
                                ("BASELINE_NOW_PASSING", len(now_passing))))),
    ))


# --------------------------------------------------------------------------- #
# Helpers and CLI.
# --------------------------------------------------------------------------- #

def _iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _epoch(stamp: str) -> float:
    return time.mktime(time.strptime(stamp.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")) - time.timezone


def _node_version() -> Optional[str]:
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=20)
        return (out.stdout or "").strip() or None
    except Exception:
        return None


def _write_json(path: Path, doc: Mapping) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SMP.canonical_json(doc) + "\n", encoding="utf-8", newline="\n")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover - CLI
    parser = argparse.ArgumentParser(
        description="ATLAS-THROUGHPUT-006 -- remote validation policy, shards and receipts.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inventory", help="measured per-module cost from a profiler run")
    p.add_argument("--profile", required=True)
    p.add_argument("--out")
    p = sub.add_parser("shards", help="plan the shards from measurements")
    p.add_argument("--profile", required=True)
    p.add_argument("--count", type=int, default=4)
    p.add_argument("--out")
    p = sub.add_parser("dispatch", help="what a change owes remotely")
    p.add_argument("--base", required=True)
    p.add_argument("--head", default=RD.WORKTREE)
    p = sub.add_parser("completeness", help="verify a sharded run accounted for every node")
    p.add_argument("--manifest", required=True)
    p.add_argument("--junit", action="append", default=[], help="one shard's junit; repeatable")
    args = parser.parse_args(argv)

    if args.command in ("inventory", "shards"):
        measurements = load_measurements(Path(args.profile))
        if args.command == "inventory":
            doc = OrderedDict((("schema", "ptf-ci-test-inventory/1.0"),
                               ("modules", [m.to_dict() for m in measurements.values()])))
        else:
            doc = plan_shards(measurements, shard_count=args.count)
        if args.out:
            _write_json(Path(args.out), doc)
            print("%s: %d modules" % (args.out, len(measurements)))
        else:
            print(SMP.canonical_json(doc)[:4000])
        return 0
    if args.command == "dispatch":
        print(SMP.canonical_json(plan_for_head(args.base, args.head)))
        return 0
    if args.command == "completeness":
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
        from scripts.pettripfinder import regression_lanes as LANES
        executed: Dict[str, List[str]] = {}
        for junit in args.junit:
            cases = LANES._junit_cases(Path(junit))
            executed[Path(junit).stem] = sorted(cases)
        planned, errors = collect_node_ids()
        doc = verify_completeness(planned, executed, collection_errors=errors,
                                  shards_required=[s["shard"] for s in manifest["shards"]],
                                  shards_completed=list(range(1, len(args.junit) + 1)))
        print(SMP.canonical_json(doc))
        return 0 if doc["complete"] else 1
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
