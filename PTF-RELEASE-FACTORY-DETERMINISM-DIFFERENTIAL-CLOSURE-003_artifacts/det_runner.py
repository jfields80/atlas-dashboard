"""PTF-RELEASE-FACTORY-DETERMINISM-DIFFERENTIAL-CLOSURE-003 bounded A/B runner.

    python det_runner.py <out_dir>

Runs the SAME 2 node IDs in ONE pytest process per commit, A (repair) then B (parent),
never concurrently, identical argv/env/order/cap. Per run:
  * refuses if the worktree HEAD is wrong, the tree is dirty, or any other pytest runs
  * baseline: free RAM, commit limit / free commit, CPU, load, python version, start time
  * hard wall-clock cap CAP_S: the process TREE is killed -> outcome TIMEOUT
  * machine guard: system free commit < GUARD_GB -> killed -> outcome ABORTED_COMMIT_GUARD
  * memory sampled every SAMPLE_S (private, working set, system free RAM / commit)
  * peak working set / peak commit read from the process handle at exit
  * faulthandler_timeout dumps every thread's stack shortly before the cap, so a
    TIMEOUT still carries a traceback signature
No retry. Writes <out>/<name>.{log,xml,probe.jsonl,mem.jsonl,result.json}, status.jsonl.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

IDS = [
    "tests/website_generation/integration/test_pettripfinder_demo_media_determinism.py::TestDeterminism::test_repeated_real_build_identical",
    "tests/website_generation/integration/test_pettripfinder_demo_media_determinism.py::TestDeterminism::test_the_two_builds_were_genuinely_independent",
]
RUNS = [
    ("A_repair", r"C:\t\rfd3a\atlas-dashboard", "cf73a06d1b6f3fe83dcdb8363da047735d14d82f"),
    ("B_parent", r"C:\t\rfd3b\atlas-dashboard", "9656419918229db7a0eb5ca5a1b4fb514e0e9c34"),
]
CAP_S = 3600
FAULTHANDLER_S = 3300
GUARD_GB = 3.0
SAMPLE_S = 15
HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
STATUS = OUT / "status.jsonl"
k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD)] + [
        (n, ctypes.c_size_t) for n in (
            "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
            "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage",
            "PeakPagefileUsage", "PrivateUsage")]


class MSX(ctypes.Structure):
    _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD)] + [
        (n, ctypes.c_ulonglong) for n in (
            "ullTotalPhys", "ullAvailPhys", "ullTotalPageFile", "ullAvailPageFile",
            "ullTotalVirtual", "ullAvailVirtual", "ullAvailExtendedVirtual")]


def gb(n):
    return round(n / 2**30, 3)


def proc_mem(handle):
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    return c if k32.K32GetProcessMemoryInfo(wt.HANDLE(handle), ctypes.byref(c), c.cb) else None


def sysmem():
    m = MSX()
    m.dwLength = ctypes.sizeof(MSX)
    k32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m


def ps(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


def other_pytests():
    out = ps("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
             "Where-Object { $_.CommandLine -match '-m pytest' } | ForEach-Object { $_.ProcessId }")
    return [int(p) for p in out.split() if p.strip().isdigit()]


def status(**row):
    row["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(STATUS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def baseline():
    m = sysmem()
    cpu = ps("$c=Get-CimInstance Win32_Processor; \"$($c.Name.Trim())|$($c.NumberOfLogicalProcessors)|$($c.LoadPercentage)\"")
    name, logical, load = (cpu.split("|") + ["", "", ""])[:3]
    return {
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "free_ram_gb": gb(m.ullAvailPhys), "total_ram_gb": gb(m.ullTotalPhys),
        "commit_limit_gb": gb(m.ullTotalPageFile), "free_commit_gb": gb(m.ullAvailPageFile),
        "memory_load_pct": m.dwMemoryLoad,
        "cpu": name, "cpu_logical": logical, "cpu_load_pct": load,
        "python": sys.version.split()[0], "python_exe": sys.executable,
        "pytest": subprocess.run([sys.executable, "-m", "pytest", "--version"], capture_output=True,
                                 text=True).stdout.strip() or "?",
        "platform": platform.platform(),
    }


status(event="PLAN_START", runs=[r[0] for r in RUNS], ids=IDS, cap_s=CAP_S)
for name, cwd, expect in RUNS:
    head = subprocess.run(["git", "-C", cwd, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", cwd, "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    if head != expect or dirty:
        status(event="REFUSED", name=name, head=head, expected=expect, dirty=bool(dirty))
        sys.exit(2)
    others = other_pytests()
    if others:
        status(event="REFUSED_OTHER_PYTEST", name=name, pids=others)
        sys.exit(3)
    base = baseline()
    status(event="BASELINE", name=name, **base)
    xml, probe, memf = OUT / (name + ".xml"), OUT / (name + ".probe.jsonl"), OUT / (name + ".mem.jsonl")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(HERE) + os.pathsep + env.get("PYTHONPATH", "")
    env["DET_PROBE_OUT"] = str(probe)
    env["PYTHONUNBUFFERED"] = "1"
    argv = [sys.executable, "-u", "-m", "pytest", *IDS, "-vv", "-rA", "-p", "no:cacheprovider",
            "-p", "det_probe", "-o", "faulthandler_timeout=%d" % FAULTHANDLER_S,
            "-o", "junit_family=xunit2", "--junitxml=%s" % xml, "--durations=0"]
    t0 = time.monotonic()
    min_free_commit = sysmem().ullAvailPageFile
    killed = None
    with open(OUT / (name + ".log"), "w", encoding="utf-8", buffering=1) as log:
        p = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        status(event="RUN_START", name=name, pid=p.pid, commit=head, argv=argv[1:])
        last_sample = 0.0
        while p.poll() is None:
            time.sleep(1)
            el = time.monotonic() - t0
            sm = sysmem()
            min_free_commit = min(min_free_commit, sm.ullAvailPageFile)
            if el - last_sample >= SAMPLE_S:
                last_sample = el
                pm = proc_mem(p._handle)
                with open(memf, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"s": round(el), "private_gb": gb(pm.PrivateUsage) if pm else None,
                                        "ws_gb": gb(pm.WorkingSetSize) if pm else None,
                                        "sys_free_ram_gb": gb(sm.ullAvailPhys),
                                        "sys_free_commit_gb": gb(sm.ullAvailPageFile)}) + "\n")
            reason = None
            if el >= CAP_S:
                reason = "TIMEOUT"
            elif sm.ullAvailPageFile / 2**30 < GUARD_GB:
                reason = "ABORTED_COMMIT_GUARD"
            if reason and p.poll() is None:
                killed = reason
                pm = proc_mem(p._handle)
                status(event="KILL", name=name, reason=reason, elapsed_s=round(el, 1),
                       private_gb=gb(pm.PrivateUsage) if pm else None)
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                p.wait()
    secs = round(time.monotonic() - t0, 1)
    pm = proc_mem(p._handle)
    result = {
        "name": name, "cwd": cwd, "commit": head, "node_ids": IDS, "exit_code": p.returncode,
        "seconds": secs, "cap_s": CAP_S,
        "outcome": killed or ("PASSED" if p.returncode == 0 else "HAS_FAILURES"),
        "peak_working_set_gb": gb(pm.PeakWorkingSetSize) if pm else None,
        "peak_commit_gb": gb(pm.PeakPagefileUsage) if pm else None,
        "min_system_free_commit_gb": gb(min_free_commit),
        "junit": str(xml) if xml.exists() else None,
        "baseline": base,
    }
    (OUT / (name + ".result.json")).write_text(json.dumps(result, indent=1), encoding="utf-8")
    status(event="RUN_END", **{k: v for k, v in result.items() if k != "baseline"})
status(event="PLAN_END")
