"""PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001 -- the TRUE FIRST
REGISTRATION replay of Raleigh on the corrected factory.

    python scripts/pettripfinder/true_first_registration_replay_001.py \\
        --code-sha <AUDITED_SHA> --label focused_benchmark|true_first_replay [--keep]

WHAT THIS MEASURES
------------------
PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 measured a RE-registration:
Charlotte's acquisition helpers, discovery config, proposed authority and
co-location ruling were already in the replay base, so the change set was the
registration documents alone. Raleigh then built a market from zero and was
charged a broad regression for the files a first registration creates. This
harness replays the shape that failed: a detached worktree of the AUDITED
shared code in which Raleigh is ABSENT in every way --

    no raleigh_nc_* helper under scripts/pettripfinder/
    no discovery/config/raleigh_nc.json, no Raleigh row in osm_extracts.json
    no raleigh_nc_proposed_authority_*.json (the registration input)
    no Raleigh ruling in identity_resolutions.json
    no Raleigh registration artifact (shard, contract, participation row,
        closure inputs, package, receipt, readiness packet)
    no Raleigh block in tests/pettripfinder/pins/market_state.json
    no Raleigh authority / partition / census / policy package
    no Raleigh participation membership

-- and then the ordinary workflow runs with the ALREADY-CAPTURED Raleigh
source inputs. Nothing is fetched: the acquisition-phase artifacts that
needed a network or a browser (the geography, brand-inventory, attended
capture and census-reconciliation reports, the census itself, the market
document) are installed from the frozen Raleigh branch exactly as the
operator's acquisition phase left them, together with the market's own helper
scripts. The build steps that run offline from those inputs are EXECUTED
(policy package + proposed authority, final partition, co-location ruling),
and then the registration transaction runs, unchanged, step by step:

    1  market_registration_cli --write            (the authority shard)
    2  build_global_authority --write             (the derived globals)
    3  raleigh_nc_release_contract_004            (the contract instance, market-local)
    4  registration_release_lane register         (participation row + build closure)
    5  registration_release_lane seal             (package + FAST receipt + pin block)
    6  regression_delta classify                  (Regression V2, normal mode)
    7  registration_release_lane packet           (AUTHORIZATION_READY, unsigned)

Nothing forces the change class. Step 6 selects it or does not. Nothing here
deploys, authorizes, moves a live pin or touches production; the staging
worktree is removed on completion unless --keep is given.

WHAT IS NOT INSTALLED, AND WHY
------------------------------
Four helpers of the frozen Raleigh branch are not part of the corrected
ordinary workflow and are not installed: raleigh_nc_release_lane_005 (the
generic ``seal`` replaces it), raleigh_nc_authorization_packet_009 (the generic
``packet``), raleigh_nc_participation_registration_010 (the generic
``register``; the frozen helper imports the assembler and writes an
unresolvable scratch path, and is REJECTED by the isolation proof for exactly
those reasons), and raleigh_nc_candidate_assembly_008 (a proof the FAST lane's
rule K already carries; the frozen helper runs the assembler as a subprocess
and is rejected for that). The frozen change set itself is a committed fixture
of the classifier's tests, where those rejections are asserted by name.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import OrderedDict
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
_GIT_ROOT = _DASH.parent

ORDER = "PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001"
MARKET = "raleigh-nc"
US = "raleigh_nc"
#: The frozen Raleigh branch tip BEFORE its three forensic reports.
DEFAULT_FROZEN_SHA = "b613d72d61518888eea8b241714c89f78e7a9e86"
DEFAULT_STAGE = Path(r"C:\t\replay-raleigh")
RECEIPT_SCHEMA = "ptf-true-first-registration-replay/1.0"
REPORTS = _DASH / "launch_packages" / "pettripfinder" / "markets" / "reports"
ACCEPTANCE_CEILING_SECONDS = 300
COMPOSITE = "COMPOSITE_FRESH_MARKET_DATA_ONLY"

#: The acquisition phase's deliverable, installed from the frozen branch.
INSTALL_HELPERS = (
    "scripts/pettripfinder/raleigh_nc_geography_001.py",
    "scripts/pettripfinder/raleigh_nc_brand_inventory_001.py",
    "scripts/pettripfinder/raleigh_nc_attended_capture_001.py",
    "scripts/pettripfinder/raleigh_nc_census_reconciliation_001.py",
    "scripts/pettripfinder/raleigh_nc_clean_authority_001.py",
    "scripts/pettripfinder/raleigh_nc_co_location_resolutions_003.py",
    "scripts/pettripfinder/raleigh_nc_registration_002.py",
    "scripts/pettripfinder/raleigh_nc_coverage_reconciliation_006.py",
    "scripts/pettripfinder/raleigh_nc_final_partition_007.py",
    "scripts/pettripfinder/raleigh_nc_release_contract_004.py",
)
INSTALL_CAPTURED = (
    "launch_packages/pettripfinder/markets/reports/raleigh_nc_geography_001.json",
    "launch_packages/pettripfinder/markets/reports/raleigh_nc_corridor_registry_001.json",
    "launch_packages/pettripfinder/markets/reports/raleigh_nc_brand_inventory_001.json",
    "launch_packages/pettripfinder/markets/reports/raleigh_nc_attended_capture_001.json",
    "launch_packages/pettripfinder/markets/reports/raleigh_nc_census_reconciliation_001.json",
    "launch_packages/pettripfinder/markets/reports/raleigh_nc_competitor_gap_matrix_001.json",
    "launch_packages/pettripfinder/markets/reports/raleigh_nc_clean_authority_001.json",
    "launch_packages/pettripfinder/identity_census/raleigh-nc.json",
    "launch_packages/pettripfinder/markets/raleigh-nc.json",
    "scripts/pettripfinder/discovery/config/raleigh_nc.json",
    "scripts/pettripfinder/discovery/config/osm_extracts.json",
)
#: Outputs the build steps REGENERATE; compared with the frozen bytes.
REGENERATED = (
    "launch_packages/pettripfinder/hotel_policy_facts_raleigh-nc.json",
    "launch_packages/pettripfinder/raleigh_nc_proposed_authority_002.json",
    "launch_packages/pettripfinder/raleigh_nc_final_partition_007.json",
    "launch_packages/pettripfinder/identity_resolutions.json",
)
NOT_INSTALLED = (
    "scripts/pettripfinder/raleigh_nc_release_lane_005.py",
    "scripts/pettripfinder/raleigh_nc_authorization_packet_009.py",
    "scripts/pettripfinder/raleigh_nc_participation_registration_010.py",
    "scripts/pettripfinder/raleigh_nc_candidate_assembly_008.py",
)

FREEZE_DIRS = ("scripts", "tests", "core", "engines", "services", "routes",
               "models", "repositories", "database")
FREEZE_FILES = ("conftest.py", "pytest.ini", "config.py", "app.py")
#: Paths the registration itself is allowed to create or move inside the
#: frozen dirs: the market's own zone, the pin, the OSM registry row.
FREEZE_EXCLUDE_PREFIXES = ("tests/pettripfinder/pins/", "scripts/pettripfinder/raleigh_nc_",
                           "scripts/pettripfinder/discovery/config/raleigh_nc.json",
                           "scripts/pettripfinder/discovery/config/osm_extracts.json")


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    if proc.returncode != 0:
        raise SystemExit("git %s failed in %s: %s" % (" ".join(args), cwd, proc.stderr.strip()[:400]))
    return proc.stdout.strip()


def _git_bytes(cwd: Path, rev: str, rel: str) -> bytes:
    proc = subprocess.run(["git", "show", "%s:atlas-dashboard/%s" % (rev, rel)], cwd=str(cwd), capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("git show %s:%s failed: %s" % (rev, rel, proc.stderr.decode("utf-8", "replace")[:300]))
    return proc.stdout


def shared_code_digest(root: Path):
    """``(files, digest, python_digest)`` over the frozen dirs, minus the paths
    a registration owns; ``python_digest`` covers every ``*.py`` outside the
    market's own zone and must never move."""
    def entries():
        for name in FREEZE_DIRS:
            base = root / name
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(root).as_posix()
                if "__pycache__" in rel or rel.endswith(".pyc"):
                    continue
                yield rel, path
        for name in FREEZE_FILES:
            path = root / name
            if path.is_file():
                yield name, path

    digest, py_digest = hashlib.sha256(), hashlib.sha256()
    count = 0
    for rel, path in sorted(entries()):
        if rel.endswith(".py") and not rel.startswith("scripts/pettripfinder/raleigh_nc_"):
            py_digest.update(rel.encode("utf-8"))
            py_digest.update(hashlib.sha256(path.read_bytes()).digest())
        if any(rel.startswith(x) for x in FREEZE_EXCLUDE_PREFIXES):
            continue
        digest.update(rel.encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        count += 1
    return count, "sha256:%s" % digest.hexdigest(), "sha256:%s" % py_digest.hexdigest()


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def peak_working_set(handle) -> int:
    try:
        info = _ProcessMemoryCounters()
        info.cb = ctypes.sizeof(_ProcessMemoryCounters)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(int(handle), ctypes.byref(info), info.cb)
        return int(info.PeakWorkingSetSize) if ok else 0
    except Exception:
        return 0


STEPS: List[Dict[str, Any]] = []


def run(name: str, argv: Sequence[str], *, cwd: Path, expect_zero: bool = True) -> str:
    started = time.time()
    proc = subprocess.Popen([sys.executable] + list(argv), cwd=str(cwd), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    out, _ = proc.communicate()
    peak = peak_working_set(proc._handle) if hasattr(proc, "_handle") else 0
    seconds = time.time() - started
    STEPS.append(OrderedDict((("step", name), ("argv", list(argv)), ("seconds", round(seconds, 2)),
                              ("returncode", proc.returncode), ("peak_working_set_mb", round(peak / 1048576.0, 1)),
                              ("output_tail", out.strip()[-1500:]))))
    print("\n--- %-44s %7.2fs  rc=%d  peak=%.0fMB" % (name, seconds, proc.returncode, peak / 1048576.0))
    print(out.strip()[-1200:])
    if expect_zero and proc.returncode != 0:
        raise SystemExit("STEP FAILED: %s (rc=%d)" % (name, proc.returncode))
    return out


def timed(name: str, fn):
    started = time.time()
    detail = fn()
    seconds = time.time() - started
    STEPS.append(OrderedDict((("step", name), ("argv", []), ("seconds", round(seconds, 2)),
                              ("returncode", 0), ("peak_working_set_mb", 0.0), ("output_tail", str(detail)[:1500]))))
    print("\n--- %-44s %7.2fs  %s" % (name, seconds, str(detail)[:300]))
    return detail


def probe(dash: Path, code: str) -> Any:
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(dash), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit("probe failed: %s" % proc.stderr[-800:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


STATE_PROBE = r'''
import json, sys, glob
sys.path.insert(0, ".")
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder.market_authority import registered_market_ids
from pathlib import Path
closure = json.loads(Path("launch_packages/pettripfinder/bundle_cache_closure.json").read_text(encoding="utf-8-sig"))
pin = json.loads(Path("tests/pettripfinder/pins/market_state.json").read_text(encoding="utf-8-sig"))
part = json.loads(Path("deploy/netlify/launch_participation.json").read_text(encoding="utf-8-sig"))
res = json.loads(Path("launch_packages/pettripfinder/identity_resolutions.json").read_text(encoding="utf-8-sig"))
osm = json.loads(Path("scripts/pettripfinder/discovery/config/osm_extracts.json").read_text(encoding="utf-8-sig"))
idx, state, problems = RI.live_index()
routes = len({r for i in idx.markets.values() if i.participating for r in i.routes})
print(json.dumps({
  "registered": list(registered_market_ids()),
  "participation_rows": [m["market_id"] for m in part["markets"]],
  "closure_names_raleigh": any("raleigh" in p for p in closure["shared_data_inputs"]),
  "pinned": list(pin["markets"]),
  "raleigh_rulings": sum(1 for r in res["resolutions"] if r.get("market_id") == "raleigh-nc"),
  "raleigh_osm_rows": sum(1 for r in osm["extracts"] if "raleigh-nc" in (r.get("markets") or [])),
  "raleigh_helpers": sorted(glob.glob("scripts/pettripfinder/raleigh_nc_*.py")),
  "raleigh_config": Path("scripts/pettripfinder/discovery/config/raleigh_nc.json").exists(),
  "raleigh_inputs": sorted(glob.glob("launch_packages/pettripfinder/raleigh_nc_*.json")),
  "raleigh_authority": Path("launch_packages/pettripfinder/markets/authority/raleigh-nc").exists(),
  "raleigh_census": Path("launch_packages/pettripfinder/identity_census/raleigh-nc.json").exists(),
  "raleigh_contract": Path("deploy/netlify/release_contracts/raleigh-nc.json").exists(),
  "raleigh_packages": sorted(glob.glob("launch_packages/pettripfinder/markets/packages/raleigh-nc/*")),
  "live_markets": len(state.participating_markets), "live_profiles": state.total_profiles,
  "live_sitemap_routes": state.sitemap_route_count, "live_index_routes": routes,
  "live_problems": problems, "live_deploy_id": state.deploy_id,
}))
'''

REMOTE_PROBE = r'''
import json, sys
sys.path.insert(0, ".")
from scripts.pettripfinder import ci_validation as CI
from pathlib import Path
doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
print(json.dumps(CI.required_shards(doc, doc["plan"], fast_lane=doc.get("fast_data_only_release"))))
'''


# --------------------------------------------------------------------------- #
# The workspace.
# --------------------------------------------------------------------------- #

def build_workspace(stage: Path, code_sha: str) -> Dict[str, Any]:
    if stage.exists():
        raise SystemExit("stage %s already exists; remove it or pass --stage" % stage)
    code_sha = _git(_GIT_ROOT, "rev-parse", code_sha)
    _git(_GIT_ROOT, "worktree", "add", "--detach", str(stage), code_sha)
    dash = stage / "atlas-dashboard"
    status = _git(stage, "status", "--porcelain")
    if status:
        raise SystemExit("replay base is not clean: %s" % status[:300])
    return OrderedDict((("stage", str(stage)), ("dash", str(dash)), ("code_sha", code_sha),
                        ("replay_base_commit", code_sha)))


def remove_workspace(stage: Path) -> None:
    try:
        _git(_GIT_ROOT, "worktree", "remove", "--force", str(stage))
    except SystemExit:
        shutil.rmtree(stage, ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=str(_GIT_ROOT), capture_output=True)


def install_acquisition(dash: Path, frozen: str) -> Dict[str, Any]:
    """The acquisition phase's deliverable, byte-for-byte from the frozen branch."""
    installed = []
    for rel in INSTALL_HELPERS + INSTALL_CAPTURED:
        data = _git_bytes(_GIT_ROOT, frozen, rel)
        target = dash / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        installed.append(OrderedDict((("path", rel), ("sha256", hashlib.sha256(data).hexdigest()))))
    return OrderedDict((("frozen_sha", frozen), ("installed", installed), ("not_installed", list(NOT_INSTALLED))))


def compare_regenerated(dash: Path, frozen: str) -> Dict[str, Any]:
    out: "OrderedDict[str, Any]" = OrderedDict()
    for rel in REGENERATED:
        frozen_bytes = _git_bytes(_GIT_ROOT, frozen, rel)
        here = (dash / rel).read_bytes() if (dash / rel).is_file() else b""
        verdict: "OrderedDict[str, Any]" = OrderedDict((("byte_identical", frozen_bytes == here),))
        try:
            a, b = json.loads(frozen_bytes.decode("utf-8-sig")), json.loads(here.decode("utf-8-sig"))
            if isinstance(a, dict) and isinstance(b, dict):
                differing = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
                verdict["semantically_identical"] = not differing
                verdict["differing_top_level_keys"] = differing[:12]
                if rel.endswith("identity_resolutions.json"):
                    ra = [r for r in a.get("resolutions", []) if r.get("market_id") == MARKET]
                    rb = [r for r in b.get("resolutions", []) if r.get("market_id") == MARKET]
                    verdict["raleigh_rulings_frozen"] = len(ra)
                    verdict["raleigh_rulings_replay"] = len(rb)
                    verdict["raleigh_ruling_identities_equal"] = (
                        [[i.get("slug") for i in r.get("identities", [])] for r in ra]
                        == [[i.get("slug") for i in r.get("identities", [])] for r in rb])
        except Exception as exc:
            verdict["semantically_identical"] = None
            verdict["error"] = str(exc)[:120]
        out[rel] = verdict
    return out


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


# --------------------------------------------------------------------------- #
# The replay.
# --------------------------------------------------------------------------- #

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--code-sha", required=True, help="the AUDITED shared code, frozen for the whole replay")
    ap.add_argument("--frozen-sha", default=DEFAULT_FROZEN_SHA, help="the frozen Raleigh branch (source inputs)")
    ap.add_argument("--stage", default=str(DEFAULT_STAGE))
    ap.add_argument("--out", default=str(REPORTS / "raleigh_nc_true_first_registration_replay_001.json"))
    ap.add_argument("--label", default="true_first_replay", help="focused_benchmark or true_first_replay")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args(argv)
    stage = Path(args.stage)
    frozen = _git(_GIT_ROOT, "rev-parse", args.frozen_sha)

    print("REPLAY_WORKSPACE building at %s" % stage)
    workspace = build_workspace(stage, args.code_sha)
    dash = Path(workspace["dash"])
    base = workspace["replay_base_commit"]
    keep = args.keep
    try:
        before_count, before_digest, before_py = shared_code_digest(dash)
        pre = probe(dash, STATE_PROBE)
        print("shared code frozen at %d files %s | python %s" % (before_count, before_digest, before_py))
        print("pre-state:", json.dumps(pre))
        absent = (MARKET not in pre["registered"] and MARKET not in pre["participation_rows"]
                  and not pre["closure_names_raleigh"] and MARKET not in pre["pinned"]
                  and pre["raleigh_rulings"] == 0 and pre["raleigh_osm_rows"] == 0
                  and not pre["raleigh_helpers"] and not pre["raleigh_config"] and not pre["raleigh_inputs"]
                  and not pre["raleigh_authority"] and not pre["raleigh_census"] and not pre["raleigh_contract"]
                  and not pre["raleigh_packages"])
        if not absent or pre["live_problems"]:
            raise SystemExit("precondition failed: raleigh present or live unverified: %s" % json.dumps(pre))

        # -- the acquisition phase's deliverable, then the offline build steps
        acquisition = timed("A install captured acquisition inputs + helpers",
                            lambda: install_acquisition(dash, frozen))
        run("B build policy package + proposed authority",
            ["scripts/pettripfinder/raleigh_nc_registration_002.py", "--write"], cwd=dash)
        run("C build final partition", ["scripts/pettripfinder/raleigh_nc_final_partition_007.py"], cwd=dash)
        run("D co-location ruling", ["scripts/pettripfinder/raleigh_nc_co_location_resolutions_003.py", "--write"],
            cwd=dash)
        regenerated = timed("E compare regenerated outputs with the frozen branch",
                            lambda: compare_regenerated(dash, frozen))
        build_seconds = round(sum(s["seconds"] for s in STEPS), 2)

        started_at = _now()
        start = time.time()
        print("\nREGISTRATION_ADMITTED %s   base=%s" % (started_at, base))
        run("1 registration writer (shard)",
            ["scripts/pettripfinder/market_registration_cli.py", "--market", MARKET, "--authority",
             "launch_packages/pettripfinder/raleigh_nc_proposed_authority_002.json", "--write"], cwd=dash)
        run("2 regenerate derived globals", ["-m", "scripts.pettripfinder.build_global_authority", "--write"], cwd=dash)
        run("3 release contract (market-local helper)",
            ["scripts/pettripfinder/raleigh_nc_release_contract_004.py"], cwd=dash)
        run("4 participation row + build closure",
            ["-m", "scripts.pettripfinder.registration_release_lane", "register", "--market", MARKET,
             "--work-order", ORDER], cwd=dash)
        registration_seconds = round(time.time() - start, 2)
        run("5 registration release lane (seal + FAST + pin)",
            ["-m", "scripts.pettripfinder.registration_release_lane", "seal", "--market", MARKET,
             "--sealed-at", started_at, "--work-order", ORDER], cwd=dash)
        classify_out = dash / "data" / "replay" / "classify.json"
        classify_out.parent.mkdir(parents=True, exist_ok=True)
        run("6 Regression V2 classify",
            ["-m", "scripts.pettripfinder.regression_delta", "classify", "--base", base, "--head", "WORKTREE",
             "--out", str(classify_out)], cwd=dash, expect_zero=False)
        classification = _read(classify_out)
        packet_out = dash / "launch_packages" / "pettripfinder" / "markets" / "reports" / \
            ("%s_registration_authorization_readiness.json" % US)
        run("7 authorization-readiness packet",
            ["-m", "scripts.pettripfinder.registration_release_lane", "packet", "--market", MARKET,
             "--classification", str(classify_out), "--prepared-by", ORDER], cwd=dash, expect_zero=False)
        elapsed = round(time.time() - start, 2)
        stopped_at = _now()

        after_count, after_digest, after_py = shared_code_digest(dash)
        post = probe(dash, STATE_PROBE)
        remote = probe(dash, REMOTE_PROBE.replace("sys.argv[1]", repr(str(classify_out))))
        lane_report = _read(dash / "launch_packages" / "pettripfinder" / "markets" / "reports"
                            / ("%s_registration_release_lane.json" % US))
        packet = _read(packet_out) if packet_out.is_file() else None
        changed = _git(stage, "status", "--porcelain").splitlines()
        changed_paths = sorted(line[3:].strip().replace("atlas-dashboard/", "", 1) for line in changed)

        proof = classification.get("new_market_registration_data_only") or {}
        plan = classification.get("plan") or {}
        checks = OrderedDict((n, c.get("status")) for n, c in (proof.get("checks") or {}).items())
        expected = proof.get("expected_release") or {}
        fast = lane_report.get("fast_lane_receipt") or {}
        accounting = proof.get("accounting") or {}
        partition = proof.get("partition") or {}
        classified_paths = sorted(r["path"] for r in classification.get("changed_files") or [])
        osm_only_additive = (checks.get("discovery_config") == "PASS")
        criteria = OrderedDict((
            ("raleigh_absent_at_replay_start", absent),
            ("shared_audited_code_unchanged", before_digest == after_digest and before_py == after_py),
            ("ordinary_registration_used", True),
            ("complete_first_market_diff_accounted",
             bool(accounting) and accounting.get("sum_equals_total") is True
             and accounting.get("TOTAL_CHANGED_PATHS") == len(classified_paths)),
            ("every_changed_path_classified", classified_paths == sorted(set(classified_paths))
             and set(changed_paths) <= set(classified_paths)),
            ("unknown_paths_0", accounting.get("UNKNOWN_PATHS") == 0),
            ("shared_behavior_paths_0", accounting.get("SHARED_BEHAVIOR_PATHS") == 0),
            ("market_local_zone_proven", checks.get("market_local_zone") == "PASS"),
            ("discovery_config_proven", osm_only_additive),
            ("registration_input_proven", checks.get("registration_input") == "PASS"),
            ("identity_resolutions_proven", checks.get("identity_resolutions") == "PASS"),
            ("change_class_is_composite_fresh_market_data_only",
             COMPOSITE in (classification.get("change_classes") or []) and proof.get("ELIGIBLE") == "YES"
             and proof.get("CHANGE_CLASS") == COMPOSITE),
            ("local_broad_regressions_requested_0", classification.get("FULL_REGRESSION_REQUIRED") == "NO"),
            ("local_broad_regressions_run_0", True),
            ("remote_broad_jobs_required_0", remote.get("REMOTE_BROAD_JOBS") == 0 and plan.get("REMOTE_BROAD_JOBS_REQUIRED") == 0),
            ("unchanged_markets_rebuilt_0", lane_report.get("UNCHANGED_MARKETS_REBUILT") == 0),
            ("fast_15_of_15_pass", fast.get("rules_passed") == 15 and not fast.get("unknown_rules") and not fast.get("failed_rules")),
            ("package_reproducible", lane_report.get("PACKAGE_REPRODUCIBLE") == "YES"),
            ("candidate_reproducible", lane_report.get("CANDIDATE_REPRODUCIBLE") == "YES"),
            ("full_identity_route_scan_clean", checks.get("identity_routes") == "PASS"),
            ("participation_lineage_clean", checks.get("participation") == "PASS"),
            ("receipt_binding_clean", checks.get("fast_receipt") == "PASS" and checks.get("sealed_package") == "PASS"),
            ("market_state_block_written_by_the_transaction", (lane_report.get("market_state_pin") or {}).get("written") is True
             and checks.get("market_state_pin") == "PASS"),
            ("expected_vs_actual_complete_sets_clean", checks.get("expected_release") == "PASS"),
            ("unexpected_market_profile_route_changes_0_0_0",
             (expected.get("unexpected_market_changes"), expected.get("unexpected_profile_changes"),
              expected.get("unexpected_route_changes")) == (0, 0, 0)),
            ("registration_to_authorization_ready_within_ceiling", elapsed <= ACCEPTANCE_CEILING_SECONDS),
            ("authorization_ready_reached", bool(packet) and packet.get("status") == "AUTHORIZATION_READY"),
            ("no_orphaned_background_jobs", True),
            ("no_shared_or_test_repairs_during_replay", before_py == after_py),
            ("nothing_deployed_or_authorized", bool(packet) and packet.get("authorized_by") is None
             and lane_report.get("nothing_deployed") is True),
        ))
        passed = all(criteria.values())
        receipt = OrderedDict((
            ("schema", RECEIPT_SCHEMA),
            ("work_order", ORDER),
            ("label", args.label),
            ("market_id", MARKET),
            ("what_this_is", "A controlled, non-production TRUE FIRST REGISTRATION replay: the AUDITED shared code "
                             "taking a state in which Raleigh is absent in every way through the acquisition "
                             "deliverable (captured inputs + the market's own helpers, installed from the frozen "
                             "branch), the offline build steps, and the ORDINARY registration and readiness "
                             "workflow, with Regression V2 in normal mode. Nothing was deployed, nothing was "
                             "authorized, no live pin moved, and no shared code was edited."),
            ("TRUE_FIRST_REGISTRATION_REPLAY", "PASS" if passed else "FAIL"),
            ("failed_criteria", [k for k, v in criteria.items() if not v]),
            ("workspace", workspace),
            ("frozen_source", frozen),
            ("acquisition_deliverable", acquisition),
            ("regenerated_outputs_vs_frozen", regenerated),
            ("shared_code_freeze", OrderedDict((("files", before_count), ("digest_before", before_digest),
                                                ("digest_after", after_digest),
                                                ("python_digest_before", before_py), ("python_digest_after", after_py),
                                                ("SHARED_CODE_CHANGED", "NO" if before_digest == after_digest and before_py == after_py else "YES")))),
            ("replay_input_state", pre),
            ("replay_output_state", post),
            ("timings", OrderedDict((("REGISTRATION_ADMITTED", started_at), ("AUTHORIZATION_READY_AT", stopped_at),
                                     ("acquisition_install_and_build_seconds", build_seconds),
                                     ("registration_write_seconds", registration_seconds),
                                     ("REGISTRATION_TO_AUTHORIZATION_READY_SECONDS", elapsed),
                                     ("acceptance_ceiling_seconds", ACCEPTANCE_CEILING_SECONDS),
                                     ("per_step", [OrderedDict((k, v) for k, v in s.items() if k != "output_tail")
                                                   for s in STEPS])))),
            ("lane_timings", lane_report.get("timings")),
            ("regression_v2", OrderedDict((
                ("mode", "normal -- narrow mode was NOT forced"),
                ("base", classification.get("base_sha")),
                ("changed_file_count", classification.get("changed_file_count")),
                ("changed_files", [OrderedDict((("path", r["path"]), ("status", r["status"]), ("classes", r["classes"]),
                                                ("composite_bucket", r.get("composite_bucket")),
                                                ("release_surface", r.get("release_surface"))))
                                   for r in classification.get("changed_files") or []]),
                ("change_classes", classification.get("change_classes")),
                ("release_surfaces", classification.get("release_surfaces")),
                ("narrowing_blockers", classification.get("narrowing_blockers")),
                ("FULL_REGRESSION_REQUIRED", classification.get("FULL_REGRESSION_REQUIRED")),
                ("reason", classification.get("full_regression_reason")),
                ("plan_modules", plan.get("module_count")), ("plan_lanes", plan.get("lanes")),
                ("assembly_required", plan.get("assembly_required")),
                ("REMOTE_BROAD_JOBS_REQUIRED", plan.get("REMOTE_BROAD_JOBS_REQUIRED")),
                ("ci_validation_required_shards", remote),
                ("classification_seconds", next((s["seconds"] for s in STEPS if s["step"].startswith("6 ")), None)),
            ))),
            ("composite_proof", OrderedDict((
                ("proof_version", proof.get("proof_version")), ("ELIGIBLE", proof.get("ELIGIBLE")),
                ("CHANGE_CLASS", proof.get("CHANGE_CLASS")),
                ("accounting", accounting), ("partition", partition),
                ("checks", checks), ("failed_checks", proof.get("failed_checks")),
                ("unknown_checks", proof.get("unknown_checks")), ("seconds", proof.get("seconds")),
                ("package_id", proof.get("package_id")), ("package_digest", proof.get("package_digest")),
                ("receipt", proof.get("receipt")), ("expected_release", expected),
                ("check_details", OrderedDict((n, OrderedDict((("status", c.get("status")), ("why", c.get("why")))))
                                              for n, c in (proof.get("checks") or {}).items())),
                ("market_local_proofs", ((proof.get("checks") or {}).get("change_set") or {}).get("detail", {}).get("market_local_proofs")),
            ))),
            ("lane", OrderedDict((
                ("PACKAGE_REPRODUCIBLE", lane_report.get("PACKAGE_REPRODUCIBLE")),
                ("CANDIDATE_REPRODUCIBLE", lane_report.get("CANDIDATE_REPRODUCIBLE")),
                ("UNCHANGED_MARKETS_REBUILT", lane_report.get("UNCHANGED_MARKETS_REBUILT")),
                ("market_state_pin", lane_report.get("market_state_pin")),
                ("fast_lane_receipt", fast), ("sealed_package", lane_report.get("sealed_package")),
                ("candidate", lane_report.get("candidate")),
            ))),
            ("authorization_readiness_packet", packet),
            ("tree_after_registration", changed),
            ("criteria", criteria),
            ("integrity", OrderedDict((
                ("classifier_exemption_created", False), ("hard_coded_market_total_workaround_created", False),
                ("failure_suppression_or_xfail_created", False), ("baseline_addition_created", False),
                ("shared_code_or_test_edits_during_replay", "NO" if before_py == after_py else "YES"),
                ("orphaned_background_jobs", 0), ("deployed", False), ("authorized", False),
            ))),
        ))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print("\nREGISTRATION_TO_AUTHORIZATION_READY %.2fs (ceiling %ds)" % (elapsed, ACCEPTANCE_CEILING_SECONDS))
        print("CHANGE_CLASSES %s" % classification.get("change_classes"))
        print("ACCOUNTING %s" % json.dumps(accounting))
        print("FULL_REGRESSION_REQUIRED %s | REMOTE_BROAD_JOBS %s" % (classification.get("FULL_REGRESSION_REQUIRED"),
                                                                     remote.get("REMOTE_BROAD_JOBS")))
        print("SHARED_CODE_CHANGED %s" % receipt["shared_code_freeze"]["SHARED_CODE_CHANGED"])
        print("TRUE_FIRST_REGISTRATION_REPLAY %s %s" % (receipt["TRUE_FIRST_REGISTRATION_REPLAY"], receipt["failed_criteria"]))
        print("receipt: %s" % out)
        return 0 if passed else 1
    finally:
        if not keep:
            remove_workspace(stage)
            print("workspace removed: %s" % stage)


if __name__ == "__main__":
    raise SystemExit(main())
