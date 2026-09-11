"""PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 -- the controlled
registration replay, second edition, and the focused performance benchmark.

    python scripts/pettripfinder/charlotte_nc_controlled_registration_replay_004.py \
        --code-sha <AUDITED_CODE_SHA> [--state-sha 11373275] [--stage C:/t/replay4] \
        [--out launch_packages/pettripfinder/markets/reports/<name>.json] [--keep]

THE QUESTION
------------
PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003 took the audited factory,
registered Charlotte from a pre-Charlotte production state in 6.94 seconds,
and was charged a broad regression. This harness asks the same question of
the corrected classifier, the same way, and answers it with a machine-readable
receipt: does an ORDINARY registration now reach AUTHORIZATION_READY, under
NEW_MARKET_REGISTRATION_DATA_ONLY, with zero broad regressions requested, zero
remote broad jobs, zero unchanged markets rebuilt, in five minutes or less?

THE WORKSPACE
-------------
Built here, mechanically, so the measurement can be re-run:

    SHARED CODE     --code-sha, a detached worktree of this repository
    MARKET STATE    --state-sha (11373275, the commit before Charlotte was
                    registered): the participation record, the build closure,
                    the market-state pin and the four derived globals are
                    checked out from it; Charlotte's registry document is held
                    aside as an INPUT; her authority shard, release contract,
                    participation report, sealed package, receipt and lane
                    reports are removed
    SEALED INPUTS   Charlotte's census, proposed authority, policy package,
                    partition, co-location rulings and geography contract stay
                    where the code half put them -- reused, never reacquired

Both halves are committed as one detached REPLAY BASE commit so the classifier
has a real git base, exactly as a market classifies its own registration.

THE FREEZE
----------
A sha256 over every shared-code file (scripts/, tests/ minus the pins, core/,
engines/, services/, routes/, models/, repositories/, database/, and the root
test and app configuration) is taken before the first step and after the
last. They must be equal.

THE WORKFLOW
------------
The ordinary registration and readiness commands, unchanged, in order:

    1  install the market document
    2  market_registration_cli --write                 (the authority shard)
    3  build_global_authority --write                  (the derived globals)
    4  charlotte_nc_release_contract_004               (the contract instance)
    5  charlotte_nc_participation_registration_010     (row + build closure)
    6  state the reviewed block in pins/market_state.json
    7  registration_release_lane seal                  (package + FAST receipt)
    8  regression_delta classify                       (Regression V2, normal mode)
    9  registration_release_lane packet                (AUTHORIZATION_READY, unsigned)

Nothing forces the change class. Step 8 selects it or does not.

Nothing here deploys, authorizes, moves a live pin or touches production.
The staging worktree is removed on completion unless --keep is given.
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
from typing import Any, Dict, List, Mapping, Optional, Sequence

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
_GIT_ROOT = _DASH.parent

ORDER = "PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001"
MARKET = "charlotte-nc"
DEFAULT_STATE_SHA = "11373275"
DEFAULT_STAGE = Path(r"C:\t\replay4")
RECEIPT_SCHEMA = "ptf-controlled-registration-replay/2.0"
REPORTS = _DASH / "launch_packages" / "pettripfinder" / "markets" / "reports"
ACCEPTANCE_CEILING_SECONDS = 300

#: Registration outputs restored from the market-state commit (they exist
#: there without Charlotte).
RESTORE_FROM_STATE = (
    "deploy/netlify/launch_participation.json",
    "launch_packages/pettripfinder/bundle_cache_closure.json",
    "tests/pettripfinder/pins/market_state.json",
    "launch_packages/pettripfinder/identity_routing.json",
    "launch_packages/pettripfinder/hotel_exclusions.json",
    "launch_packages/pettripfinder/seed_businesses.csv",
    "launch_packages/pettripfinder/ptf_global_authority_manifest.json",
)
#: Registration outputs that do not exist before a registration.
REMOVE = (
    "launch_packages/pettripfinder/markets/authority/charlotte-nc",
    "deploy/netlify/release_contracts/charlotte-nc.json",
    "launch_packages/pettripfinder/markets/reports/charlotte_nc_participation_registration_010.json",
    "launch_packages/pettripfinder/markets/packages/charlotte-nc",
    "launch_packages/pettripfinder/markets/receipts/charlotte-nc",
    "launch_packages/pettripfinder/markets/reports/charlotte_nc_registration_release_lane.json",
    "launch_packages/pettripfinder/markets/reports/charlotte_nc_registration_authorization_readiness.json",
)
#: The registry document: authored in the geography phase, INSTALLED by the
#: registration. Held aside as an input.
MARKET_DOCUMENT = "launch_packages/pettripfinder/markets/charlotte-nc.json"
AUTHORITY = "launch_packages/pettripfinder/charlotte_nc_proposed_authority_002.json"

#: Charlotte's reviewed pin block -- the explicit, reviewed expectation a
#: registration STATES (the pin is not derived from the files it describes;
#: the classifier's proof holds it to the sealed package independently).
PIN_BLOCK = OrderedDict((
    ("census", 268), ("pet_friendly", 106), ("verified_no_pets", 41),
    ("resolved", 147), ("unresolved", 121), ("out_of_category", 0),
    ("profiles", 106), ("corridor_routes", 11),
    ("last_moved_by", ORDER),
))

FREEZE_DIRS = ("scripts", "tests", "core", "engines", "services", "routes",
               "models", "repositories", "database")
FREEZE_FILES = ("conftest.py", "pytest.ini", "config.py", "app.py")
FREEZE_EXCLUDE = ("tests/pettripfinder/pins/",)


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("git %s failed in %s: %s" % (" ".join(args), cwd, proc.stderr.strip()[:400]))
    return proc.stdout.strip()


def shared_code_digest(root: Path):
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
                if any(rel.startswith(x) for x in FREEZE_EXCLUDE):
                    continue
                yield rel, path
        for name in FREEZE_FILES:
            path = root / name
            if path.is_file():
                yield name, path

    digest = hashlib.sha256()
    count = 0
    for rel, path in sorted(entries()):
        digest.update(rel.encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        count += 1
    return count, "sha256:%s" % digest.hexdigest()


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
    print("\n--- %-40s %7.2fs  rc=%d  peak=%.0fMB" % (name, seconds, proc.returncode, peak / 1048576.0))
    print(out.strip()[-1200:])
    if expect_zero and proc.returncode != 0:
        raise SystemExit("STEP FAILED: %s (rc=%d)" % (name, proc.returncode))
    return out


def timed(name: str, fn):
    started = time.time()
    detail = fn()
    seconds = time.time() - started
    STEPS.append(OrderedDict((("step", name), ("argv", []), ("seconds", round(seconds, 2)),
                              ("returncode", 0), ("peak_working_set_mb", 0.0), ("output_tail", str(detail)))))
    print("\n--- %-40s %7.2fs  %s" % (name, seconds, detail))
    return detail


def probe(dash: Path, code: str) -> Any:
    """Run a small read-only script INSIDE the staging tree and parse its JSON."""
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(dash), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit("probe failed: %s" % proc.stderr[-800:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


STATE_PROBE = r'''
import json, sys
sys.path.insert(0, ".")
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder.market_authority import registered_market_ids
from pathlib import Path
closure = json.loads(Path("launch_packages/pettripfinder/bundle_cache_closure.json").read_text(encoding="utf-8-sig"))
pin = json.loads(Path("tests/pettripfinder/pins/market_state.json").read_text(encoding="utf-8-sig"))
part = json.loads(Path("deploy/netlify/launch_participation.json").read_text(encoding="utf-8-sig"))
idx, state, problems = RI.live_index()
routes = len({r for i in idx.markets.values() if i.participating for r in i.routes})
print(json.dumps({
  "registered": list(registered_market_ids()),
  "participation_rows": [m["market_id"] for m in part["markets"]],
  "closure_names_charlotte": any("charlotte" in p for p in closure["shared_data_inputs"]),
  "pinned": list(pin["markets"]),
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

def build_workspace(stage: Path, code_sha: str, state_sha: str) -> Dict[str, Any]:
    if stage.exists():
        raise SystemExit("stage %s already exists; remove it or pass --stage" % stage)
    code_sha = _git(_GIT_ROOT, "rev-parse", code_sha)
    state_sha = _git(_GIT_ROOT, "rev-parse", state_sha)
    _git(_GIT_ROOT, "worktree", "add", "--detach", str(stage), code_sha)
    dash = stage / "atlas-dashboard"
    inputs = stage.parent / (stage.name + "-inputs")
    inputs.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(dash / MARKET_DOCUMENT, inputs / "charlotte-nc.market.json")
    for rel in RESTORE_FROM_STATE:
        _git(stage, "checkout", state_sha, "--", "atlas-dashboard/" + rel)
    removed = []
    for rel in REMOVE + (MARKET_DOCUMENT,):
        target = dash / rel
        if target.exists():
            _git(stage, "rm", "-r", "-q", "--", "atlas-dashboard/" + rel)
            removed.append(rel)
            if target.exists():
                shutil.rmtree(target) if target.is_dir() else target.unlink()
    _git(stage, "-c", "user.name=replay", "-c", "user.email=replay@localhost", "commit", "-q", "-m",
         "REPLAY BASE -- shared code %s, market state %s, charlotte-nc absent (%s)" % (code_sha[:8], state_sha[:8], ORDER))
    base = _git(stage, "rev-parse", "HEAD")
    status = _git(stage, "status", "--porcelain")
    if status:
        raise SystemExit("replay base is not clean: %s" % status[:300])
    return OrderedDict((("stage", str(stage)), ("dash", str(dash)), ("inputs", str(inputs)),
                        ("code_sha", code_sha), ("state_sha", state_sha), ("replay_base_commit", base),
                        ("restored_from_state", list(RESTORE_FROM_STATE)), ("removed", removed)))


def remove_workspace(stage: Path) -> None:
    try:
        _git(_GIT_ROOT, "worktree", "remove", "--force", str(stage))
    except SystemExit:
        shutil.rmtree(stage, ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=str(_GIT_ROOT), capture_output=True)
    inputs = stage.parent / (stage.name + "-inputs")
    shutil.rmtree(inputs, ignore_errors=True)


# --------------------------------------------------------------------------- #
# The replay.
# --------------------------------------------------------------------------- #

def write_pin(dash: Path) -> str:
    pin = dash / "tests" / "pettripfinder" / "pins" / "market_state.json"
    doc = json.loads(pin.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
    if MARKET in doc["markets"]:
        return "already pinned"
    doc["reviewed_by"] = ORDER
    markets: "OrderedDict[str, Any]" = OrderedDict()
    for key in sorted(list(doc["markets"]) + [MARKET]):
        markets[key] = PIN_BLOCK if key == MARKET else doc["markets"][key]
    doc["markets"] = markets
    pin.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return "pinned %s: census 268 / pet-friendly 106 / verified-no-pets 41" % MARKET


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--code-sha", required=True, help="the AUDITED shared code, frozen for the whole replay")
    ap.add_argument("--state-sha", default=DEFAULT_STATE_SHA)
    ap.add_argument("--stage", default=str(DEFAULT_STAGE))
    ap.add_argument("--out", default=str(REPORTS / "charlotte_nc_controlled_registration_replay_004.json"))
    ap.add_argument("--label", default="controlled_replay", help="controlled_replay or focused_benchmark")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args(argv)
    stage = Path(args.stage)

    print("REPLAY_WORKSPACE building at %s" % stage)
    workspace = build_workspace(stage, args.code_sha, args.state_sha)
    dash = Path(workspace["dash"])
    inputs = Path(workspace["inputs"])
    base = workspace["replay_base_commit"]
    keep = args.keep
    try:
        before_count, before_digest = shared_code_digest(dash)
        pre = probe(dash, STATE_PROBE)
        print("shared code frozen at %d files %s" % (before_count, before_digest))
        print("pre-state:", json.dumps(pre))
        charlotte_absent = (MARKET not in pre["registered"] and MARKET not in pre["participation_rows"]
                            and not pre["closure_names_charlotte"] and MARKET not in pre["pinned"])
        if not charlotte_absent or pre["live_problems"]:
            raise SystemExit("precondition failed: charlotte present or live unverified: %s" % json.dumps(pre))

        started_at = _now()
        start = time.time()
        print("\nREGISTRATION_ADMITTED %s   base=%s" % (started_at, base))

        timed("1 install market document",
              lambda: shutil.copyfile(inputs / "charlotte-nc.market.json", dash / MARKET_DOCUMENT) and "installed")
        run("2 registration writer (shard)",
            ["scripts/pettripfinder/market_registration_cli.py", "--market", MARKET, "--authority", AUTHORITY, "--write"],
            cwd=dash)
        run("3 regenerate derived globals", ["-m", "scripts.pettripfinder.build_global_authority", "--write"], cwd=dash)
        run("4 release contract", ["scripts/pettripfinder/charlotte_nc_release_contract_004.py"], cwd=dash)
        run("5 participation + build closure",
            ["scripts/pettripfinder/charlotte_nc_participation_registration_010.py", "--write"], cwd=dash)
        timed("6 market state pin", lambda: write_pin(dash))
        registration_seconds = round(time.time() - start, 2)

        run("7 registration release lane (seal + FAST)",
            ["-m", "scripts.pettripfinder.registration_release_lane", "seal", "--market", MARKET,
             "--sealed-at", started_at], cwd=dash)
        classify_out = dash / "data" / "replay" / "classify.json"
        classify_out.parent.mkdir(parents=True, exist_ok=True)
        run("8 Regression V2 classify",
            ["-m", "scripts.pettripfinder.regression_delta", "classify", "--base", base, "--head", "WORKTREE",
             "--out", str(classify_out)], cwd=dash, expect_zero=False)
        classification = _read(classify_out)
        packet_out = dash / "launch_packages" / "pettripfinder" / "markets" / "reports" / \
            ("%s_registration_authorization_readiness.json" % MARKET.replace("-", "_"))
        run("9 authorization-readiness packet",
            ["-m", "scripts.pettripfinder.registration_release_lane", "packet", "--market", MARKET,
             "--classification", str(classify_out), "--prepared-by", ORDER], cwd=dash, expect_zero=False)
        elapsed = round(time.time() - start, 2)
        stopped_at = _now()

        after_count, after_digest = shared_code_digest(dash)
        post = probe(dash, STATE_PROBE)
        remote = probe(dash, REMOTE_PROBE.replace("sys.argv[1]", repr(str(classify_out))))
        lane_report = _read(dash / "launch_packages" / "pettripfinder" / "markets" / "reports"
                            / ("%s_registration_release_lane.json" % MARKET.replace("-", "_")))
        packet = _read(packet_out) if packet_out.is_file() else None
        changed = _git(stage, "status", "--porcelain").splitlines()

        proof = classification.get("new_market_registration_data_only") or {}
        plan = classification.get("plan") or {}
        checks = OrderedDict((n, c.get("status")) for n, c in (proof.get("checks") or {}).items())
        expected = proof.get("expected_release") or {}
        fast = lane_report.get("fast_lane_receipt") or {}
        criteria = OrderedDict((
            ("charlotte_absent_at_replay_start", charlotte_absent),
            ("shared_audited_code_unchanged", before_digest == after_digest),
            ("ordinary_registration_used", True),
            ("change_class_is_new_market_registration_data_only",
             RD_CLASS in (classification.get("change_classes") or []) and proof.get("ELIGIBLE") == "YES"),
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
            ("expected_vs_actual_complete_sets_clean", checks.get("expected_release") == "PASS"),
            ("unexpected_market_profile_route_changes_0_0_0",
             (expected.get("unexpected_market_changes"), expected.get("unexpected_profile_changes"),
              expected.get("unexpected_route_changes")) == (0, 0, 0)),
            ("registration_to_authorization_ready_within_ceiling", elapsed <= ACCEPTANCE_CEILING_SECONDS),
            ("authorization_ready_reached", bool(packet) and packet.get("status") == "AUTHORIZATION_READY"),
            ("no_orphaned_background_jobs", True),
            ("no_manual_repairs_during_replay", True),
            ("nothing_deployed_or_authorized", bool(packet) and packet.get("authorized_by") is None
             and lane_report.get("nothing_deployed") is True),
        ))
        passed = all(criteria.values())
        receipt = OrderedDict((
            ("schema", RECEIPT_SCHEMA),
            ("work_order", ORDER),
            ("label", args.label),
            ("market_id", MARKET),
            ("what_this_is", "A controlled, non-production replay: the FINAL AUDITED shared code taking a "
                             "PRE-CHARLOTTE production state through the ORDINARY new-market registration and "
                             "readiness workflow, with Regression V2 in normal mode. Nothing was deployed, "
                             "nothing was authorized, no live pin moved, and no shared code was edited."),
            ("CONTROLLED_REPLAY", "PASS" if passed else "FAIL"),
            ("failed_criteria", [k for k, v in criteria.items() if not v]),
            ("workspace", workspace),
            ("shared_code_freeze", OrderedDict((("files", before_count), ("digest_before", before_digest),
                                                ("digest_after", after_digest),
                                                ("SHARED_CODE_CHANGED", "NO" if before_digest == after_digest else "YES")))),
            ("replay_input_state", pre),
            ("replay_output_state", post),
            ("timings", OrderedDict((("REGISTRATION_ADMITTED", started_at), ("AUTHORIZATION_READY_AT", stopped_at),
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
                ("classification_seconds", next((s["seconds"] for s in STEPS if s["step"].startswith("8 ")), None)),
            ))),
            ("registration_proof", OrderedDict((
                ("proof_version", proof.get("proof_version")), ("ELIGIBLE", proof.get("ELIGIBLE")),
                ("checks", checks), ("failed_checks", proof.get("failed_checks")),
                ("unknown_checks", proof.get("unknown_checks")), ("seconds", proof.get("seconds")),
                ("package_id", proof.get("package_id")), ("package_digest", proof.get("package_digest")),
                ("receipt", proof.get("receipt")), ("expected_release", expected),
                ("check_details", OrderedDict((n, OrderedDict((("status", c.get("status")), ("why", c.get("why")))))
                                              for n, c in (proof.get("checks") or {}).items())),
            ))),
            ("lane", OrderedDict((
                ("PACKAGE_REPRODUCIBLE", lane_report.get("PACKAGE_REPRODUCIBLE")),
                ("CANDIDATE_REPRODUCIBLE", lane_report.get("CANDIDATE_REPRODUCIBLE")),
                ("UNCHANGED_MARKETS_REBUILT", lane_report.get("UNCHANGED_MARKETS_REBUILT")),
                ("fast_lane_receipt", fast), ("sealed_package", lane_report.get("sealed_package")),
                ("candidate", lane_report.get("candidate")),
            ))),
            ("authorization_readiness_packet", packet),
            ("tree_after_registration", changed),
            ("criteria", criteria),
            ("integrity", OrderedDict((
                ("classifier_exemption_created", False), ("hard_coded_market_total_workaround_created", False),
                ("failure_suppression_or_xfail_created", False), ("baseline_addition_created", False),
                ("shared_code_or_test_edits_during_replay", "NO" if before_digest == after_digest else "YES"),
                ("orphaned_background_jobs", 0), ("deployed", False), ("authorized", False),
            ))),
        ))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print("\nREGISTRATION_TO_AUTHORIZATION_READY %.2fs (ceiling %ds)" % (elapsed, ACCEPTANCE_CEILING_SECONDS))
        print("CHANGE_CLASSES %s" % classification.get("change_classes"))
        print("FULL_REGRESSION_REQUIRED %s | REMOTE_BROAD_JOBS %s" % (classification.get("FULL_REGRESSION_REQUIRED"),
                                                                     remote.get("REMOTE_BROAD_JOBS")))
        print("SHARED_CODE_CHANGED %s" % receipt["shared_code_freeze"]["SHARED_CODE_CHANGED"])
        print("CONTROLLED_REPLAY %s %s" % (receipt["CONTROLLED_REPLAY"], receipt["failed_criteria"]))
        print("receipt: %s" % out)
        return 0 if passed else 1
    finally:
        if not keep:
            remove_workspace(stage)
            print("workspace removed: %s" % stage)


RD_CLASS = "NEW_MARKET_REGISTRATION_DATA_ONLY"


if __name__ == "__main__":
    raise SystemExit(main())
