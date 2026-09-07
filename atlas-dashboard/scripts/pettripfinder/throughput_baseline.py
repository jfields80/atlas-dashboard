"""ATLAS-THROUGHPUT-001 -- read-only analysis of factory throughput evidence.

    python -m scripts.pettripfinder.throughput_baseline junit  --out <json> LABEL=<junit.xml> [...]
    python -m scripts.pettripfinder.throughput_baseline run    --profile <profile.jsonl> --out <json>
    python -m scripts.pettripfinder.throughput_baseline sampler --csv <samples.csv> --root-pid <pid> --out <json>
    python -m scripts.pettripfinder.throughput_baseline classify --out <json> [--branch LABEL=BASE..HEAD ...]
    python -m scripts.pettripfinder.throughput_baseline failures --baseline <baseline.json> --junit <junit.xml> --out <json>

Every subcommand READS: junit files a past run left behind, a profile the
:mod:`throughput_profile` plugin wrote, a process sampler CSV, git history
(``git diff`` / ``git show``), or a committed baseline manifest. None writes
anything but the ``--out`` document. None runs pytest. None touches authority.

WHY THIS EXISTS
---------------
The broad regression is measured as ONE number ("about 100 minutes") and the
work orders have been reasoning from a percentage on a progress bar. The
questions that decide what to cache are per-node: which tests carry the cost,
which fixture paid for it, how many times the same inputs were assembled, and
what the process peaked at. The junit files already answer the first
question for every broad run ever kept; the plugin answers the rest.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import regression_lanes as LANES  # noqa: E402

SCHEMA_JUNIT = "ptf-throughput-junit-profile/1.0"
SCHEMA_RUN = "ptf-throughput-run-profile/1.0"
SCHEMA_SAMPLER = "ptf-throughput-sampler-summary/1.0"
SCHEMA_CLASSIFY = "ptf-throughput-classifier-audit/1.0"
SCHEMA_FAILURES = "ptf-throughput-failure-baseline-audit/1.0"

# --------------------------------------------------------------------------- #
# Analytical categories (Phase 4). ANALYSIS ONLY -- nothing selects tests by
# these. A module's lane membership decides; the closed-order name pattern
# separates history from shared runtime inside the sub-packages.
# --------------------------------------------------------------------------- #

FAST_CONTRACT = "FAST_CONTRACT"
MARKET_LOCAL = "MARKET_LOCAL"
CORE_SHARED = "CORE_SHARED"
ASSEMBLY = "ASSEMBLY"
DEPLOYMENT = "DEPLOYMENT"
HISTORY = "HISTORY"
OTHER = "OTHER"
OTHER_NON_PTF = "OTHER_NON_PTF"
UNKNOWN = "UNKNOWN"
CATEGORIES = (FAST_CONTRACT, MARKET_LOCAL, CORE_SHARED, ASSEMBLY, DEPLOYMENT,
              HISTORY, OTHER, OTHER_NON_PTF, UNKNOWN)

_CLOSED_ORDER = re.compile(r"_(\d{3}[a-z]?|pass_?[0-9a-z]+|p\d)\.py$")


def category_of(module: str) -> str:
    """The analytical group a test module falls in."""
    module = module.replace("\\", "/")
    if not module.startswith("tests/"):
        return UNKNOWN
    if not module.startswith("tests/pettripfinder/"):
        return OTHER_NON_PTF
    rel = module[len("tests/pettripfinder/"):]
    lanes = LANES.lanes_for(rel)
    market = LANES.market_for(rel)
    if rel.startswith("contracts/"):
        return FAST_CONTRACT
    if LANES.DEPLOYMENT_ARCHITECTURE in lanes:
        return DEPLOYMENT
    if LANES.ASSEMBLY in lanes or rel == "test_per_market_release_contracts.py":
        return ASSEMBLY
    if market:
        return MARKET_LOCAL
    if rel.startswith(("acquisition/", "brightdata/", "discovery/", "importer/", "policy/")):
        return HISTORY if _CLOSED_ORDER.search(rel) else CORE_SHARED
    if len(lanes) > 1:
        return CORE_SHARED
    return HISTORY if _CLOSED_ORDER.search(rel) else OTHER


# --------------------------------------------------------------------------- #
# junit profiles.
# --------------------------------------------------------------------------- #

def junit_node_id(case) -> Tuple[str, str, str]:
    """``(node id, module path, class)`` rebuilt the way regression_lanes does."""
    classname = case.get("classname") or ""
    name = case.get("name") or ""
    parts = classname.split(".")
    path_parts: List[str] = []
    cls_parts: List[str] = []
    for part in parts:
        if cls_parts or (path_parts and part[:1].isupper()):
            cls_parts.append(part)
        else:
            path_parts.append(part)
    module = "/".join(path_parts) + ".py"
    nid = module
    if cls_parts:
        nid += "::" + "::".join(cls_parts)
    return nid + "::" + name, module, (cls_parts[0] if cls_parts else "")


def read_junit(path: Path) -> Dict[str, Any]:
    root = ET.parse(str(path)).getroot()
    suite = root.find("testsuite") if root.tag == "testsuites" else root
    cases = []
    for case in root.iter("testcase"):
        nid, module, cls = junit_node_id(case)
        seconds = float(case.get("time") or 0.0)
        status, message = "passed", ""
        for child in case:
            if child.tag in ("failure", "error"):
                status = child.tag
                message = (child.get("message") or (child.text or ""))[:300]
                break
            if child.tag == "skipped":
                status = "skipped"
                break
        cases.append(OrderedDict((("node", nid), ("module", module), ("class", cls),
                                  ("seconds", seconds), ("status", status),
                                  ("message", message))))
    return OrderedDict((
        ("suite_time_s", float(suite.get("time") or 0.0) if suite is not None else 0.0),
        ("suite_timestamp", suite.get("timestamp") if suite is not None else None),
        ("cases", cases),
    ))


def profile_junit(label: str, path: Path, top: int = 40) -> Dict[str, Any]:
    doc = read_junit(path)
    cases = doc["cases"]
    case_time = sum(c["seconds"] for c in cases)
    by_module: Counter = Counter()
    n_module: Counter = Counter()
    by_class: Counter = Counter()
    by_cat: Counter = Counter()
    n_cat: Counter = Counter()
    by_market: Counter = Counter()
    for c in cases:
        by_module[c["module"]] += c["seconds"]
        n_module[c["module"]] += 1
        by_class[c["module"] + ("::" + c["class"] if c["class"] else "")] += c["seconds"]
        cat = category_of(c["module"])
        by_cat[cat] += c["seconds"]
        n_cat[cat] += 1
        rel = c["module"][len("tests/pettripfinder/"):] \
            if c["module"].startswith("tests/pettripfinder/") else ""
        by_market[(LANES.market_for(rel) if rel else None) or "(none)"] += c["seconds"]
    ranked = sorted(cases, key=lambda c: -c["seconds"])
    return OrderedDict((
        ("label", label),
        ("path", str(path)),
        ("suite_timestamp", doc["suite_timestamp"]),
        ("suite_time_s", round(doc["suite_time_s"], 1)),
        ("sum_case_time_s", round(case_time, 1)),
        ("collection_and_session_overhead_s", round(doc["suite_time_s"] - case_time, 1)),
        ("collected", len(cases)),
        ("status_counts", dict(Counter(c["status"] for c in cases))),
        ("by_category", OrderedDict(
            (k, OrderedDict((("seconds", round(v, 1)), ("tests", n_cat[k]),
                             ("share", round(v / case_time, 4) if case_time else 0.0))))
            for k, v in by_cat.most_common())),
        ("by_market", OrderedDict((k, round(v, 1)) for k, v in by_market.most_common())),
        ("top_modules", [OrderedDict((("module", m), ("seconds", round(t, 1)),
                                      ("tests", n_module[m])))
                         for m, t in by_module.most_common(30)]),
        ("top_classes", [OrderedDict((("class", m), ("seconds", round(t, 1))))
                         for m, t in by_class.most_common(20)]),
        ("top_nodes", [OrderedDict((("node", c["node"]), ("seconds", round(c["seconds"], 1)),
                                    ("status", c["status"])))
                       for c in ranked[:top]]),
        ("failing", [OrderedDict((("node", c["node"]), ("message", c["message"])))
                     for c in cases if c["status"] in ("failure", "error")]),
    ))


def cross_run_table(profiles: Sequence[Mapping]) -> Dict[str, Any]:
    """The same node across runs, ranked by its worst run."""
    nodes: Dict[str, Dict[str, float]] = defaultdict(dict)
    for p in profiles:
        for n in p["top_nodes"]:
            nodes[n["node"]][p["label"]] = n["seconds"]
    rows = sorted(nodes.items(), key=lambda kv: -max(kv[1].values()))
    return OrderedDict((
        ("labels", [p["label"] for p in profiles]),
        ("nodes", [OrderedDict((("node", n), ("seconds_by_run", v),
                                ("max", max(v.values())), ("min", min(v.values()))))
                   for n, v in rows]),
    ))


# --------------------------------------------------------------------------- #
# plugin profiles (JSONL).
# --------------------------------------------------------------------------- #

def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def profile_run(rows: Sequence[Mapping], top: int = 25) -> Dict[str, Any]:
    """Phase 9 over a plugin JSONL: phases, top nodes/fixtures, assembly
    duplication by input hash, cold vs repeated build time."""
    starts = [r for r in rows if r["kind"] == "session_start"]
    finishes = [r for r in rows if r["kind"] == "session_finish"]
    collections = [r for r in rows if r["kind"] == "collection"]
    tests = [r for r in rows if r["kind"] == "test"]
    fixtures = [r for r in rows if r["kind"] == "fixture_setup"]
    assemblies = [r for r in rows if r["kind"] == "assembly"]

    def _sum(key: str) -> float:
        return round(sum(float(t.get(key) or 0.0) for t in tests), 1)

    fixture_by_name: Counter = Counter()
    fixture_count: Counter = Counter()
    for f in fixtures:
        fixture_by_name[(f["fixture"], f["scope"])] += float(f["seconds"])
        fixture_count[(f["fixture"], f["scope"])] += 1

    # Assembly duplication: group by (kind, dependency_input_hash, market, context).
    # Only OUTER calls that did real work (>= 1 s) count as a build; the wrap
    # also sees sub-second nested engine calls and synthetic-fixture calls,
    # which are reported separately under ``insignificant_calls``.
    groups: Dict[Tuple, List[Mapping]] = defaultdict(list)
    insignificant = 0
    for a in assemblies:
        if a.get("nesting_depth", 0) != 0:
            continue                       # count the outer call once
        if float(a.get("elapsed_seconds") or 0.0) < 1.0:
            insignificant += 1
            continue
        key = (a.get("assembly_kind"), a.get("dependency_input_hash"),
               a.get("market"), a.get("context"))
        groups[key].append(a)
    dup_rows = []
    identical_builds = 0
    identical_seconds = 0.0
    cold_vs_repeat = []
    for key, calls in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        calls_sorted = sorted(calls, key=lambda c: c["start_ts"])
        repeats = calls_sorted[1:]
        identical_builds += len(repeats)
        identical_seconds += sum(float(c["elapsed_seconds"]) for c in repeats)
        if repeats:
            cold_vs_repeat.append(OrderedDict((
                ("key", "%s|%s|%s|%s" % key),
                ("cold_seconds", round(float(calls_sorted[0]["elapsed_seconds"]), 1)),
                ("repeat_seconds_mean", round(sum(float(c["elapsed_seconds"]) for c in repeats) / len(repeats), 1)),
            )))
        dup_rows.append(OrderedDict((
            ("assembly_kind", key[0]), ("dependency_input_hash", key[1]),
            ("market", key[2]), ("context", key[3]),
            ("builds", len(calls)), ("repeated_builds", len(repeats)),
            ("seconds_total", round(sum(float(c["elapsed_seconds"]) for c in calls), 1)),
            ("seconds_repeated", round(sum(float(c["elapsed_seconds"]) for c in repeats), 1)),
            ("output_hashes", sorted({str(c.get("output_hash")) for c in calls})),
            ("callers", [c.get("test_node_id") for c in calls_sorted]),
        )))
    outer = [a for a in assemblies if a.get("nesting_depth", 0) == 0
             and float(a.get("elapsed_seconds") or 0.0) >= 1.0]
    by_market_calls: Counter = Counter()
    for a in outer:
        by_market_calls[a.get("market") or "(all-market/none)"] += 1
    peak = max([float(r.get("peak_working_set_mb") or 0) for r in rows] or [0.0])
    finish = finishes[-1] if finishes else {}
    cpu = finish.get("cpu") or {}
    cpu0 = finish.get("cpu_at_start") or {}
    return OrderedDict((
        ("schema", SCHEMA_RUN),
        ("run_id", rows[0]["run_id"] if rows else None),
        ("git_head", starts[0].get("git_head") if starts else None),
        ("wrapped", starts[0].get("wrapped") if starts else None),
        ("wrap_skipped", starts[0].get("wrap_skipped") if starts else None),
        ("total_wall_s", finish.get("seconds")),
        ("collection_s", finish.get("collection_seconds") or (collections[0]["seconds"] if collections else None)),
        ("execution_s", finish.get("execution_seconds")),
        ("collected", collections[0]["collected"] if collections else len(tests)),
        ("counts", finish.get("counts") or dict(Counter(t["outcome"] for t in tests))),
        ("exit_status", finish.get("exit_status")),
        ("phase_seconds", OrderedDict((
            ("test_setup", _sum("setup_seconds")),
            ("test_call", _sum("call_seconds")),
            ("test_teardown", _sum("teardown_seconds")),
            ("fixture_setup_recorded", round(sum(fixture_by_name.values()), 1)),
            ("assembly_outer_calls", round(sum(float(a["elapsed_seconds"]) for a in outer), 1)),
            ("assembly_by_kind", OrderedDict(sorted(
                ((k, round(v, 1)) for k, v in Counter(
                    {}).items()), key=lambda kv: -kv[1]))),
        ))),
        ("cpu_seconds", OrderedDict((
            ("user", round(float(cpu.get("user", 0)) - float(cpu0.get("user", 0)), 1)),
            ("system", round(float(cpu.get("system", 0)) - float(cpu0.get("system", 0)), 1)),
            ("children_user", round(float(cpu.get("children_user", 0)) - float(cpu0.get("children_user", 0)), 1)),
            ("children_system", round(float(cpu.get("children_system", 0)) - float(cpu0.get("children_system", 0)), 1)),
        ))),
        ("peak_working_set_mb", finish.get("peak_working_set_mb") or peak),
        ("io_bytes", finish.get("io_bytes")),
        ("recorder_errors", finish.get("recorder_errors")),
        ("top_nodes", [OrderedDict((("node", t["node_id"]), ("seconds", round(float(t["total_seconds"]), 1)),
                                    ("setup", t.get("setup_seconds")), ("call", t.get("call_seconds")),
                                    ("outcome", t.get("outcome"))))
                       for t in sorted(tests, key=lambda t: -float(t["total_seconds"]))[:top]]),
        ("top_fixtures", [OrderedDict((("fixture", k[0]), ("scope", k[1]),
                                       ("seconds", round(v, 1)), ("setups", fixture_count[k])))
                          for k, v in fixture_by_name.most_common(20)]),
        ("assembly", OrderedDict((
            ("total_invocations_outer", len(outer)),
            ("insignificant_calls_under_1s", insignificant),
            ("total_invocations_including_nested", len(assemblies)),
            ("unique_inputs", len(groups)),
            ("repeated_identical_builds", identical_builds),
            ("seconds_spent_on_repeated_identical_builds", round(identical_seconds, 1)),
            ("by_market", OrderedDict(by_market_calls.most_common())),
            ("by_kind", OrderedDict(Counter(a.get("assembly_kind") for a in outer).most_common())),
            ("seconds_by_kind", OrderedDict(sorted(
                ((k, round(sum(float(a["elapsed_seconds"]) for a in outer if a.get("assembly_kind") == k), 1))
                 for k in {a.get("assembly_kind") for a in outer}), key=lambda kv: -kv[1]))),
            ("top_input_keys_by_build_count", dup_rows[:20]),
            ("cold_vs_repeat", cold_vs_repeat[:20]),
        ))),
    ))


# --------------------------------------------------------------------------- #
# process sampler CSV (ts,pid,ppid,name,ws_mb,private_mb,cpu_s,cmd).
# --------------------------------------------------------------------------- #

def summarize_sampler(rows: Iterable[Mapping[str, str]], root_pid: int) -> Dict[str, Any]:
    by_ts: Dict[str, List[Mapping[str, str]]] = defaultdict(list)
    free_by_ts: Dict[str, float] = {}
    for r in rows:
        if r.get("name") == "SYSTEM_FREE_MB":
            try:
                free_by_ts[r["ts"]] = float(r["ws_mb"])
            except (KeyError, ValueError):
                pass
            continue
        by_ts[r["ts"]].append(r)
    peak_tree = 0.0
    peak_root = 0.0
    peak_ts = None
    samples = 0
    cpu_last = None
    first_ts = None
    last_ts = None
    for ts in sorted(by_ts):
        procs = by_ts[ts]
        pids = {int(p["pid"]): p for p in procs if p.get("pid", "").isdigit()}
        if root_pid not in pids:
            continue
        samples += 1
        first_ts = first_ts or ts
        last_ts = ts
        tree = {root_pid}
        changed = True
        while changed:
            changed = False
            for pid, p in pids.items():
                try:
                    ppid = int(p["ppid"])
                except (KeyError, ValueError):
                    continue
                if ppid in tree and pid not in tree:
                    tree.add(pid)
                    changed = True
        total = 0.0
        for pid in tree:
            try:
                total += float(pids[pid]["ws_mb"] or 0)
            except ValueError:
                pass
        try:
            root_ws = float(pids[root_pid]["ws_mb"] or 0)
            cpu_last = pids[root_pid].get("cpu_s") or cpu_last
        except ValueError:
            root_ws = 0.0
        if total > peak_tree:
            peak_tree, peak_ts = total, ts
        peak_root = max(peak_root, root_ws)
    return OrderedDict((
        ("schema", SCHEMA_SAMPLER),
        ("root_pid", root_pid),
        ("samples_with_root", samples),
        ("first_ts", first_ts), ("last_ts", last_ts),
        ("peak_process_tree_working_set_mb", round(peak_tree, 1)),
        ("peak_process_tree_at", peak_ts),
        ("peak_root_working_set_mb", round(peak_root, 1)),
        ("root_cpu_seconds_last_sample", cpu_last),
        ("system_free_mb_min", round(min(free_by_ts.values()), 1) if free_by_ts else None),
        ("system_free_mb_max", round(max(free_by_ts.values()), 1) if free_by_ts else None),
    ))


# --------------------------------------------------------------------------- #
# classifier audit (Phase 3 / 11): classification ONLY, never a run.
# --------------------------------------------------------------------------- #

def classifier_audit(paths: Sequence[str], branches: Sequence[Tuple[str, str, str]]) -> Dict[str, Any]:
    from scripts.pettripfinder import regression_delta as RD
    rep = []
    for p in paths:
        classes, rule = RD.classify_path(p)
        rep.append(OrderedDict((
            ("path", p), ("classes", list(classes)), ("rule", rule),
            ("shared_test_state", RD.is_shared_test_state(p)),
            ("full_required_on_its_own", any(
                RD.VALIDATION_MATRIX[c]["full_regression"] == RD.REQUIRED for c in classes)),
        )))
    out = []
    for label, base, head in branches:
        cls = RD.classify_change(base, head)
        plan = RD.plan_for(cls)
        drivers = [r for r in plan["reasons"] if r["full_regression"] == RD.REQUIRED]
        by_class: Counter = Counter()
        for row in cls["changed_files"]:
            for c in row["classes"]:
                by_class[c] += 1
        driver_paths = sorted({d["path"] for d in drivers})
        market_local = [p for p in driver_paths
                        if re.search(r"(^|/)(scripts/pettripfinder/)?[a-z_]+_(tn|oh|ky|in|mi|pa|mo|wi)_[a-z0-9_]+\.(py|json)$", p)
                        and "/discovery/config/" not in p and "/contracts/" not in p]
        out.append(OrderedDict((
            ("label", label), ("base", base), ("head", head),
            ("base_sha", cls["base_sha"]), ("head_sha", cls["head_sha"]),
            ("changed_file_count", cls["changed_file_count"]),
            ("change_classes", cls["change_classes"]),
            ("files_by_class", dict(by_class)),
            ("files_by_rule", dict(Counter(r["rule"] for r in cls["changed_files"]).most_common())),
            ("FULL_REGRESSION_REQUIRED", "YES" if plan["full_regression_required"] else "NO"),
            ("assembly_required", plan["assembly_required"]),
            ("lanes", plan["lanes"]), ("markets", plan["markets"]),
            ("module_count", plan["module_count"]),
            ("driver_paths", driver_paths),
            ("driver_count", len(driver_paths)),
            ("drivers_that_are_market_named_helpers", market_local),
            ("changed_files", cls["changed_files"]),
        )))
    return OrderedDict((("schema", SCHEMA_CLASSIFY), ("representative_paths", rep),
                        ("branches", out)))


# --------------------------------------------------------------------------- #
# failure baseline audit (Phase 10).
# --------------------------------------------------------------------------- #

IDENTITY_CRITICAL = "IDENTITY_CRITICAL"
POLICY_CRITICAL = "POLICY_CRITICAL"
ARTIFACT_INTEGRITY_CRITICAL = "ARTIFACT_INTEGRITY_CRITICAL"
RELEASE_CRITICAL = "RELEASE_CRITICAL"
HISTORICAL_COUNT_PIN = "HISTORICAL_COUNT/PIN"
LEGACY_EXPECTATION = "LEGACY_EXPECTATION"
ENVIRONMENT = "ENVIRONMENT"
FLAKE = "FLAKE"
FAILURE_GROUPS = (IDENTITY_CRITICAL, POLICY_CRITICAL, ARTIFACT_INTEGRITY_CRITICAL,
                  RELEASE_CRITICAL, HISTORICAL_COUNT_PIN, LEGACY_EXPECTATION,
                  ENVIRONMENT, FLAKE, UNKNOWN)

_ENV_MESSAGE = re.compile(
    r"FileNotFoundError|No such file or directory|is_file\(\)|no persisted|"
    r"missing|is missing|not on disk|ABORT: expected", re.I)


def _module_reads_gitignored_data(module: str) -> bool:
    try:
        src = (REPO_ROOT / module).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if re.search(r"[\"']data/|\"data\"\s*/|'data'\s*/|DATA_DIR|data_dir|"
                 r"observation_store|acquisition_store|operator_evidence|market_research", src):
        return True
    # closed-order acquisition suites read the store through the module they test
    for m in re.findall(r"from scripts\.pettripfinder(?:\.[a-z_]+)? import ([a-z_0-9]+)", src):
        for candidate in (REPO_ROOT / "scripts" / "pettripfinder" / ("%s.py" % m),
                          REPO_ROOT / "scripts" / "pettripfinder" / "acquisition" / ("%s.py" % m)):
            if candidate.is_file():
                try:
                    if re.search(r"[\"']data[\"'/]|DATA_DIR|\"data\"", candidate.read_text(encoding="utf-8", errors="replace")):
                        return True
                except OSError:
                    pass
    return False


def failure_baseline_audit(baseline: Mapping, junit: Optional[Path]) -> Dict[str, Any]:
    """Group a baseline's failing node ids with evidence from a junit run."""
    messages: Dict[str, str] = {}
    run_failing: set = set()
    if junit is not None:
        doc = read_junit(junit)
        for c in doc["cases"]:
            if c["status"] in ("failure", "error"):
                run_failing.add(c["node"])
                messages[c["node"]] = c["message"]
    groups: Dict[str, List[Dict[str, Any]]] = OrderedDict((g, []) for g in FAILURE_GROUPS)
    per_module: Dict[str, Dict[str, Any]] = OrderedDict()
    for nodeid in baseline["failing_node_ids"]:
        module = nodeid.split("::", 1)[0]
        msg = messages.get(nodeid, "")
        reads_data = _module_reads_gitignored_data(module)
        rel = module[len("tests/pettripfinder/"):] if module.startswith("tests/pettripfinder/") else module
        market = LANES.market_for(rel)
        closed_order = bool(_CLOSED_ORDER.search(rel)) or rel.startswith("acquisition/")
        if _ENV_MESSAGE.search(msg) or reads_data:
            group = ENVIRONMENT
            why = ("reads a gitignored data/ corpus a closed order produced; absent in a "
                   "fresh worktree" if reads_data else "environmental message")
        elif closed_order:
            group = HISTORICAL_COUNT_PIN
            why = "closed-order suite asserting a derived count over inputs not present here"
        else:
            group = UNKNOWN
            why = "no rule"
        groups[group].append(OrderedDict((("node", nodeid), ("module", module),
                                          ("market", market), ("message", msg[:160]),
                                          ("reads_gitignored_data", reads_data),
                                          ("why", why))))
        pm = per_module.setdefault(module, OrderedDict((
            ("module", module), ("market", market), ("count", 0),
            ("reads_gitignored_data", reads_data), ("closed_order", closed_order),
            ("groups", Counter()), ("sample_message", msg[:160]))))
        pm["count"] += 1
        pm["groups"][group] += 1
    for pm in per_module.values():
        pm["groups"] = dict(pm["groups"])
    return OrderedDict((
        ("schema", SCHEMA_FAILURES),
        ("baseline_source_sha", baseline.get("source_sha")),
        ("baseline_failing", len(baseline["failing_node_ids"])),
        ("junit", str(junit) if junit else None),
        ("junit_failing", len(run_failing) if junit else None),
        ("junit_failure_set_identical_to_baseline",
         (run_failing == set(baseline["failing_node_ids"])) if junit else None),
        ("counts", OrderedDict((g, len(v)) for g, v in groups.items())),
        ("by_module", list(per_module.values())),
        ("groups", groups),
    ))


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #

def _write(path: Path, doc: Mapping) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, default=str) + "\n", encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("junit", help="profile one or more junit files")
    s.add_argument("--out", required=True)
    s.add_argument("--top", type=int, default=40)
    s.add_argument("inputs", nargs="+", help="LABEL=path.xml")

    s = sub.add_parser("run", help="profile a throughput_profile JSONL")
    s.add_argument("--profile", required=True)
    s.add_argument("--out", required=True)

    s = sub.add_parser("sampler", help="summarize a process sampler CSV")
    s.add_argument("--csv", required=True)
    s.add_argument("--root-pid", type=int, required=True)
    s.add_argument("--out", required=True)

    s = sub.add_parser("classify", help="classification-only audit (no run)")
    s.add_argument("--out", required=True)
    s.add_argument("--path", action="append", default=[])
    s.add_argument("--branch", action="append", default=[], help="LABEL=BASE..HEAD")

    s = sub.add_parser("failures", help="group a baseline's failures")
    s.add_argument("--baseline", required=True)
    s.add_argument("--junit")
    s.add_argument("--out", required=True)

    args = p.parse_args(argv)

    if args.command == "junit":
        profiles = []
        for item in args.inputs:
            label, path = item.split("=", 1)
            profiles.append(profile_junit(label, Path(path), top=args.top))
        doc = OrderedDict((("schema", SCHEMA_JUNIT), ("runs", profiles),
                           ("cross_run", cross_run_table(profiles))))
        _write(Path(args.out), doc)
        for pr in profiles:
            print("%-28s suite %7.0fs cases %7.0fs overhead %5.0fs collected %d %s" % (
                pr["label"], pr["suite_time_s"], pr["sum_case_time_s"],
                pr["collection_and_session_overhead_s"], pr["collected"], pr["status_counts"]))
        return 0

    if args.command == "run":
        doc = profile_run(read_jsonl(Path(args.profile)))
        _write(Path(args.out), doc)
        print(json.dumps({k: doc[k] for k in ("total_wall_s", "collection_s", "execution_s",
                                              "collected", "counts", "peak_working_set_mb")}, indent=1))
        print(json.dumps({k: doc["assembly"][k] for k in (
            "total_invocations_outer", "unique_inputs", "repeated_identical_builds",
            "seconds_spent_on_repeated_identical_builds")}, indent=1))
        return 0

    if args.command == "sampler":
        with open(args.csv, encoding="utf-8-sig") as fh:
            doc = summarize_sampler(list(csv.DictReader(fh)), args.root_pid)
        _write(Path(args.out), doc)
        print(json.dumps(doc, indent=1))
        return 0

    if args.command == "classify":
        branches = []
        for item in args.branch:
            label, rng = item.split("=", 1)
            base, head = rng.split("..", 1)
            branches.append((label, base, head))
        doc = classifier_audit(args.path, branches)
        _write(Path(args.out), doc)
        for b in doc["branches"]:
            print("%s: %d files, FULL=%s, drivers=%d (market-named helpers: %d)" % (
                b["label"], b["changed_file_count"], b["FULL_REGRESSION_REQUIRED"],
                b["driver_count"], len(b["drivers_that_are_market_named_helpers"])))
        return 0

    if args.command == "failures":
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8-sig"))
        doc = failure_baseline_audit(baseline, Path(args.junit) if args.junit else None)
        _write(Path(args.out), doc)
        print(json.dumps(doc["counts"], indent=1))
        return 0

    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
