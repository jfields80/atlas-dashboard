"""PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003 -- the replay harness.

The final controlled proof of one question: can the audited factory take a
PRE-CHARLOTTE production state, register Charlotte as a previously absent
market through the ORDINARY registration workflow, and reach authorization-ready
in five minutes without a broad validation?

WHY THIS FILE WAS RUN FROM OUTSIDE THE REPOSITORY
-------------------------------------------------
Acceptance criterion 3 forbids the replay to add, edit or touch one byte of
shared code WHILE IT RUNS. So the harness executed from ``C:/t/replay-tools``
against a detached staging worktree at ``C:/t/replay``, and is committed here
only afterwards, so that the shared-code digest taken before the replay and the
one taken after it are the same 1988 files and the same sha256. It is committed
because a measurement nobody can re-run is not a measurement.

WHAT THE REPLAY WORKSPACE WAS
-----------------------------
    SHARED CODE     42cb937f -- the final Charlotte-audited implementation,
                    frozen for the whole replay
    MARKET STATE    11373275 -- the commit before Charlotte was registered:
                    13 live markets, 902 profiles, 1078 routes, and no
                    charlotte-nc in the registry, the participation record,
                    the build closure, the derived globals or the pins
    SEALED INPUTS   Charlotte's already-validated census (268), proposed
                    authority (106 pet-friendly / 41 verified-no-pets), policy
                    package, partition, co-location rulings and geography
                    contract -- reused, never reacquired and never altered

The two halves were committed as one detached REPLAY BASE commit so that
``regression_delta classify`` had a real git base to compare the registration
against, which is exactly how a market classifies its own registration.

WHAT IT MEASURED
----------------
The ordinary workflow wrote Charlotte in 6.94 seconds and Regression V2
classified it in 2.09 more. The classification is the finding:

    FULL_REGRESSION_REQUIRED = YES

Four paths force it, and a registration cannot avoid any of them --
the participation row, the release contract and the build closure are all
DEPLOYMENT_CHANGE, and the market-state pin is a shared current-state fact that
blocks narrowing. There is no NEW_MARKET_REGISTRATION_DATA_ONLY class to fall
into: the nearest narrow class, MARKET_AUTHORITY_DATA_ONLY, requires the WHOLE
change set to be one market's authority data and additionally requires
``fast_release_activation.json`` to enable the market, which it does not.

The broad regression was NOT run. A request for one is the failure, not a step.

Output:
    launch_packages/pettripfinder/markets/reports/charlotte_nc_controlled_registration_replay_003.json
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import shutil
import subprocess
import sys
import time
from collections import OrderedDict
from ctypes import wintypes
from pathlib import Path

#: Where the replay actually ran. Short paths on purpose: a checkout of this
#: repository under the session scratchpad exceeds the Windows path limit and
#: git refuses three fixture files by name.
STAGE = Path(r"C:\t\replay")
DASH = STAGE / "atlas-dashboard"
INPUTS = Path(r"C:\t\replay-inputs")
TOOLS = Path(r"C:\t\replay-tools")

MARKET = "charlotte-nc"
PKG = DASH / "launch_packages" / "pettripfinder"
AUTHORITY = PKG / "charlotte_nc_proposed_authority_002.json"
MARKET_DOC = PKG / "markets" / ("%s.json" % MARKET)
PIN = DASH / "tests" / "pettripfinder" / "pins" / "market_state.json"

#: Charlotte's reviewed pin block. The pin is deliberately NOT derived from the
#: files it describes -- it is an explicit reviewed expectation, and the one
#: cross-check that holds it to the release contract is a separate suite. So a
#: registration STATES these numbers. They are the already-validated counts the
#: second Charlotte audit closed on, not numbers computed here.
PIN_BLOCK = OrderedDict((
    ("census", 268), ("pet_friendly", 106), ("verified_no_pets", 41),
    ("resolved", 147), ("unresolved", 121), ("out_of_category", 0),
    ("profiles", 106), ("corridor_routes", 11),
    ("last_moved_by", "PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003"),
))

#: The shared code the replay froze: every executable and every test module.
#: tests/pettripfinder/pins/ is excluded because a pin is committed market
#: STATE that a registration is expected to move, not test machinery.
FREEZE_DIRS = ("scripts", "tests", "core", "engines", "services", "routes",
               "models", "repositories", "database")
FREEZE_FILES = ("conftest.py", "pytest.ini", "config.py", "app.py")
FREEZE_EXCLUDE = ("tests/pettripfinder/pins/",)


# --------------------------------------------------------------------------- #
# The freeze proof.
# --------------------------------------------------------------------------- #

def shared_code_digest(root: Path):
    """``(file count, sha256)`` over every shared-code file under ``root``."""
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


# --------------------------------------------------------------------------- #
# Peak working set, per step. No psutil on this machine, so ask Windows.
# --------------------------------------------------------------------------- #

class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


def peak_working_set(handle) -> int:
    info = _ProcessMemoryCounters()
    info.cb = ctypes.sizeof(_ProcessMemoryCounters)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(
        int(handle), ctypes.byref(info), info.cb)
    return int(info.PeakWorkingSetSize) if ok else 0


# --------------------------------------------------------------------------- #
# The workflow.
# --------------------------------------------------------------------------- #

STEPS = []


def run(name, argv, *, expect_zero=True):
    """One blocking workflow step, timed and measured."""
    started = time.time()
    proc = subprocess.Popen([sys.executable] + argv, cwd=str(DASH),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    out, _ = proc.communicate()
    peak = peak_working_set(proc._handle)
    seconds = time.time() - started
    STEPS.append(OrderedDict((
        ("step", name), ("argv", argv), ("seconds", round(seconds, 2)),
        ("returncode", proc.returncode),
        ("peak_working_set_mb", round(peak / 1048576.0, 1)),
        ("output", out.strip()))))
    print("\n--- %-34s %7.2fs  rc=%d  peak=%.0fMB"
          % (name, seconds, proc.returncode, peak / 1048576.0))
    print(out.strip())
    if expect_zero and proc.returncode != 0:
        raise SystemExit("STEP FAILED: %s (rc=%d)" % (name, proc.returncode))
    return out


def timed(name, fn):
    """One in-process workflow step."""
    started = time.time()
    detail = fn()
    seconds = time.time() - started
    STEPS.append(OrderedDict((
        ("step", name), ("argv", []), ("seconds", round(seconds, 2)),
        ("returncode", 0), ("peak_working_set_mb", 0.0),
        ("output", str(detail)))))
    print("\n--- %-34s %7.2fs  %s" % (name, seconds, detail))


def install_market_document():
    """A market document is AUTHORED in the geography phase and INSTALLED here.

    It is the registry entry: ``load_markets()`` globs this directory, so
    placing the file is what makes the market registered.
    """
    shutil.copyfile(INPUTS / "charlotte-nc.market.json", MARKET_DOC)
    return "installed %s" % MARKET_DOC.name


def write_pin():
    doc = json.loads(PIN.read_text(encoding="utf-8-sig"),
                     object_pairs_hook=OrderedDict)
    if MARKET in doc["markets"]:
        return "already pinned"
    doc["reviewed_by"] = "PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003"
    markets = OrderedDict()
    for key in sorted(list(doc["markets"]) + [MARKET]):
        markets[key] = PIN_BLOCK if key == MARKET else doc["markets"][key]
    doc["markets"] = markets
    PIN.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    return "pinned %s: census 268 / pet-friendly 106 / verified-no-pets 41" % MARKET


def main(argv=None) -> int:
    base = (TOOLS / "replay_base.txt").read_text(encoding="utf-8").strip()
    before_count, before_digest = shared_code_digest(DASH)

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    start = time.time()
    print("REGISTRATION_REPLAY_START %s   base=%s" % (started_at, base))
    print("shared code frozen at %d files %s" % (before_count, before_digest))

    timed("1 install market document", install_market_document)
    run("2 registration writer (shard)",
        ["scripts/pettripfinder/market_registration_cli.py",
         "--market", MARKET, "--authority", str(AUTHORITY), "--write"])
    run("3 regenerate derived globals",
        ["-m", "scripts.pettripfinder.build_global_authority", "--write"])
    run("4 release contract",
        ["scripts/pettripfinder/charlotte_nc_release_contract_004.py"])
    run("5 participation + build closure",
        ["scripts/pettripfinder/charlotte_nc_participation_registration_010.py",
         "--write"])
    timed("6 market state pin", write_pin)
    run("7 Regression V2 classify",
        ["-m", "scripts.pettripfinder.regression_delta", "classify",
         "--base", base, "--head", "WORKTREE",
         "--out", str(TOOLS / "classify.json")],
        expect_zero=False)

    elapsed = time.time() - start
    after_count, after_digest = shared_code_digest(DASH)

    receipt = OrderedDict((
        ("schema", "ptf-controlled-registration-replay-steps/1.0"),
        ("work_order", "PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003"),
        ("market_id", MARKET),
        ("replay_base_commit", base),
        ("REGISTRATION_REPLAY_START", started_at),
        ("stopped_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("elapsed_seconds", round(elapsed, 2)),
        ("shared_code_files", before_count),
        ("shared_code_digest_before", before_digest),
        ("shared_code_digest_after", after_digest),
        ("SHARED_CODE_CHANGED", "NO" if before_digest == after_digest else "YES"),
        ("steps", STEPS),
    ))
    (TOOLS / "replay_steps.json").write_text(
        json.dumps(receipt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\nELAPSED_THROUGH_CLASSIFICATION %.2fs" % elapsed)
    print("SHARED_CODE_CHANGED %s" % receipt["SHARED_CODE_CHANGED"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
