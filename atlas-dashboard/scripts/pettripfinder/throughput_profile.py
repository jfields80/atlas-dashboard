"""ATLAS-THROUGHPUT-001 -- an opt-in pytest profiling plugin for the factory.

    python -m pytest tests -p scripts.pettripfinder.throughput_profile \
        --ptf-profile-out data/regression/<run>/profile.jsonl

WHY
---
The broad regression's junit file records one number per test. It cannot say
how long collection took, which fixture paid for an assembly, how many times
the same market was assembled from byte-identical inputs, or what the process
peaked at. This plugin records exactly those facts and nothing else, as one
JSON object per line, so a later order can decide what to cache on measured
evidence rather than on a percentage read off a progress bar.

WHAT IT MUST NEVER DO
---------------------
Change what a test does. Every hook is wrapped so that a failure inside the
plugin is swallowed and recorded (when recording is possible) rather than
raised. It writes to the ONE path it is given and to nothing else. It is not
loaded by any conftest: it runs only when named with ``-p`` on the command
line, so the production test harness is untouched when it is absent. With no
``--ptf-profile-out`` and no ``PTF_PROFILE_OUT`` in the environment it is
inert.

ROWS
----
Every row carries ``schema``, ``run_id``, ``kind`` and ``ts``.

    session_start   pid, ppid, python, argv, cwd, git head, os.times()
    collection      collected count, seconds from session start to the end of
                    collection
    fixture_setup   fixture name, scope, requesting node id, seconds
                    (only setups slower than ``--ptf-profile-fixture-floor``)
    test            node id, module, market, lanes, setup/call/teardown
                    seconds, outcome, peak working set after the test
    assembly        one row per wrapped assembly call: invocation id, kind,
                    market, context, output, seconds, output hash (the
                    manifest's bundle_sha256 when the callee returns one),
                    MARKET_INPUT_HASH and DEPENDENCY_INPUT_HASH (content
                    fingerprints of the authority files the market and the
                    whole site are assembled from), cache verdict (there is no
                    cache today, so always NO_CACHE), peak working set
    session_finish  seconds, exit status, peak working set, os.times(), io
                    bytes where the platform exposes them, counts

The assembly wrap is a plain function wrapper installed at ``pytest_configure``
-- before any test module is imported, so a test module's ``from ... import
assemble`` binds the wrapped callable. The wrapper calls the original with the
same arguments and returns its result unchanged; it only measures.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "ptf-throughput-profile/1.0"
NO_CACHE = "NO_CACHE"

#: (module, attribute, assembly kind). Import failures are skipped: a wrap
#: target that does not exist on a branch is a fact to record, not an error.
#: ORDER MATTERS: a callable that another module binds by name at import
#: time (``from generate_pettripfinder_columbus_site import run as
#: generate_site`` in assemble_netlify_bundle) must be wrapped BEFORE that
#: module is first imported, so the binding IS the wrapper and identity
#: assertions such as ``asm.generate_site is generator_run`` still hold. The
#: generator therefore comes first; the assemblers that import it follow.
WRAP_TARGETS: Tuple[Tuple[str, str, str], ...] = (
    ("scripts.generate_pettripfinder_columbus_site", "run", "columbus_site"),
    ("scripts.pettripfinder.assemble_netlify_bundle", "assemble", "market_bundle"),
    ("scripts.pettripfinder.assemble_production_site", "assemble", "production_site"),
    ("scripts.generate_pettripfinder_pilot", "run_pilot", "columbus_pilot"),
    ("scripts.generate_pettripfinder_pilot", "load_launch_package", "pilot_load_launch_package"),
    ("scripts.pettripfinder.listing_dataset_builder", "build_listing_dataset", "listing_dataset"),
    ("engines.website_generation.assembly.assembly_engine.AssemblyEngine", "assemble", "wge_assembly_engine"),
)

#: Authority inputs a market's bundle is assembled from, relative to the repo.
#: Globs are matched with ``{market}`` substituted; the whole-site fingerprint
#: adds the shared files. This is a FINGERPRINT for duplicate detection, not a
#: dependency graph: over-inclusive is the safe direction.
MARKET_INPUT_GLOBS: Tuple[str, ...] = (
    "launch_packages/pettripfinder/markets/authority/{market}/**/*",
    "launch_packages/pettripfinder/markets/{market}.json",
    "launch_packages/pettripfinder/hotel_policy_facts_{market}.json",
    "launch_packages/pettripfinder/identity_census/{market}.json",
    "launch_packages/pettripfinder/markets/coverage/{market}*",
    "launch_packages/pettripfinder/markets/name_corrections/{market}*",
    "launch_packages/pettripfinder/markets/founder_overrides/{market}*",
    "launch_packages/pettripfinder/markets/discovered_policy_urls/{market}*",
    "launch_packages/pettripfinder/{market_us}_final_partition_*.json",
    "deploy/netlify/release_contracts/{market}.json",
)
SHARED_INPUT_GLOBS: Tuple[str, ...] = (
    "launch_packages/pettripfinder/hotel_policy_facts.json",
    "launch_packages/pettripfinder/hotel_exclusions.json",
    "launch_packages/pettripfinder/seed_businesses.csv",
    "launch_packages/pettripfinder/categories.json",
    "launch_packages/pettripfinder/blueprint.json",
    "launch_packages/pettripfinder/ptf_global_authority_manifest.json",
    "launch_packages/pettripfinder/demo_media.json",
    "deploy/netlify/launch_participation.json",
    "deploy/netlify/global_deployment_manifest.json",
    "deploy/netlify/_headers",
    "deploy/netlify/_redirects",
)


# --------------------------------------------------------------------------- #
# Process measurements (stdlib only; every reader fails to None).
# --------------------------------------------------------------------------- #

def peak_working_set_mb() -> Optional[float]:
    """This process's peak working set in MiB, or ``None`` off Windows."""
    if sys.platform != "win32":
        try:
            import resource  # noqa: WPS433
            kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return round(kb / 1024.0, 1)
        except Exception:
            return None
    try:
        import ctypes
        import ctypes.wintypes as w

        class PMC(ctypes.Structure):
            _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]

        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p
        fn = k.K32GetProcessMemoryInfo
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), w.DWORD]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        if not fn(k.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return round(pmc.PeakWorkingSetSize / float(2 ** 20), 1)
    except Exception:
        return None


def working_set_mb() -> Optional[float]:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        import ctypes.wintypes as w

        class PMC(ctypes.Structure):
            _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]

        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p
        fn = k.K32GetProcessMemoryInfo
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), w.DWORD]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        if not fn(k.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return round(pmc.WorkingSetSize / float(2 ** 20), 1)
    except Exception:
        return None


def io_bytes() -> Optional[Dict[str, int]]:
    """Bytes read / written by this process (Windows), else ``None``."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        import ctypes.wintypes as w

        class IOC(ctypes.Structure):
            _fields_ = [("ReadOperationCount", ctypes.c_ulonglong),
                        ("WriteOperationCount", ctypes.c_ulonglong),
                        ("OtherOperationCount", ctypes.c_ulonglong),
                        ("ReadTransferCount", ctypes.c_ulonglong),
                        ("WriteTransferCount", ctypes.c_ulonglong),
                        ("OtherTransferCount", ctypes.c_ulonglong)]

        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p
        fn = k.GetProcessIoCounters
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(IOC)]
        ioc = IOC()
        if not fn(k.GetCurrentProcess(), ctypes.byref(ioc)):
            return None
        return {"read": int(ioc.ReadTransferCount), "write": int(ioc.WriteTransferCount)}
    except Exception:
        return None


def cpu_times() -> Dict[str, float]:
    try:
        t = os.times()
        return {"user": round(t.user, 2), "system": round(t.system, 2),
                "children_user": round(t.children_user, 2),
                "children_system": round(t.children_system, 2)}
    except Exception:
        return {}


def git_head() -> Optional[str]:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                              capture_output=True, text=True, timeout=20)
        return proc.stdout.strip() or None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Input fingerprints.
# --------------------------------------------------------------------------- #

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint_paths(paths: List[Path], root: Path = REPO_ROOT) -> Dict[str, Any]:
    """``{"sha256", "files"}`` over the sorted (relpath, content sha) pairs."""
    rows = []
    for path in sorted(set(p for p in paths if p.is_file())):
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = path.as_posix()
        rows.append((rel, _sha256_file(path)))
    h = hashlib.sha256()
    for rel, digest in rows:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\n")
    return {"sha256": h.hexdigest(), "files": len(rows)}


def market_input_paths(market_id: str, root: Path = REPO_ROOT) -> List[Path]:
    out: List[Path] = []
    subs = {"market": market_id, "market_us": market_id.replace("-", "_")}
    for pattern in MARKET_INPUT_GLOBS:
        out.extend(p for p in root.glob(pattern.format(**subs)) if p.is_file())
    return out


def shared_input_paths(root: Path = REPO_ROOT) -> List[Path]:
    out: List[Path] = []
    for pattern in SHARED_INPUT_GLOBS:
        out.extend(p for p in root.glob(pattern) if p.is_file())
    return out


class Fingerprints:
    """Per-session memo: authority files do not change during a pytest run."""

    def __init__(self, root: Path = REPO_ROOT):
        self.root = root
        self._market: Dict[str, Dict[str, Any]] = {}
        self._shared: Optional[Dict[str, Any]] = None
        self._site: Optional[Dict[str, Any]] = None

    def market(self, market_id: str) -> Dict[str, Any]:
        if market_id not in self._market:
            self._market[market_id] = fingerprint_paths(
                market_input_paths(market_id, self.root), self.root)
        return self._market[market_id]

    def shared(self) -> Dict[str, Any]:
        if self._shared is None:
            self._shared = fingerprint_paths(shared_input_paths(self.root), self.root)
        return self._shared

    def whole_site(self) -> Dict[str, Any]:
        """Every market's inputs plus the shared files, in one digest."""
        if self._site is None:
            paths = list(shared_input_paths(self.root))
            authority = self.root / "launch_packages" / "pettripfinder" / "markets" / "authority"
            markets = sorted(p.name for p in authority.iterdir()) if authority.is_dir() else []
            for market_id in markets:
                paths.extend(market_input_paths(market_id, self.root))
            self._site = fingerprint_paths(paths, self.root)
            self._site["markets"] = len(markets)
        return self._site


# --------------------------------------------------------------------------- #
# The recorder.
# --------------------------------------------------------------------------- #

class Recorder:
    """Append-only JSONL writer. Every public method fails silently."""

    def __init__(self, out: Optional[Path], run_id: str):
        self.out = Path(out) if out else None
        self.run_id = run_id
        self._fh = None
        self.rows_written = 0
        self.errors = 0
        if self.out is not None:
            try:
                self.out.parent.mkdir(parents=True, exist_ok=True)
                self._fh = open(self.out, "a", encoding="utf-8")
            except Exception:
                self._fh = None

    @property
    def active(self) -> bool:
        return self._fh is not None

    def write(self, kind: str, **fields: Any) -> None:
        if self._fh is None:
            return
        try:
            row: "OrderedDict[str, Any]" = OrderedDict()
            row["schema"] = SCHEMA
            row["run_id"] = self.run_id
            row["kind"] = kind
            row["ts"] = round(time.time(), 3)
            row.update(fields)
            self._fh.write(json.dumps(row, default=str) + "\n")
            self._fh.flush()
            self.rows_written += 1
        except Exception:
            self.errors += 1

    def close(self) -> None:
        try:
            if self._fh is not None:
                self._fh.close()
        except Exception:
            pass
        self._fh = None


def read_profile(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# --------------------------------------------------------------------------- #
# The assembly wrap.
# --------------------------------------------------------------------------- #

def _market_id_of(args: Tuple, kwargs: Dict) -> Optional[str]:
    market = kwargs.get("market")
    if market is None and args:
        for a in args:
            if hasattr(a, "market_id"):
                market = a
                break
    if market is None:
        return None
    return getattr(market, "market_id", None) or (market if isinstance(market, str) else None)


def _output_of(args: Tuple, kwargs: Dict) -> Optional[str]:
    if "output" in kwargs:
        return str(kwargs["output"])
    for a in args:
        if isinstance(a, (str, Path)) and ("/" in str(a) or "\\" in str(a)):
            return str(a)
    return None


def _hash_of_result(result: Any) -> Optional[str]:
    try:
        if isinstance(result, dict):
            for key in ("bundle_sha256", "sha256", "bundle_hash"):
                if key in result:
                    return str(result[key])
        for attr in ("bundle_sha256", "sha256"):
            if hasattr(result, attr):
                return str(getattr(result, attr))
    except Exception:
        return None
    return None


class AssemblyWrap:
    """Installs measuring wrappers around :data:`WRAP_TARGETS`."""

    def __init__(self, recorder: Recorder, fingerprints: Fingerprints,
                 current_node: Callable[[], Optional[str]]):
        self.recorder = recorder
        self.fingerprints = fingerprints
        self.current_node = current_node
        self.invocations = 0
        self.installed: List[Dict[str, str]] = []
        self.skipped: List[Dict[str, str]] = []
        self.depth = 0

    def install(self, targets=WRAP_TARGETS) -> None:
        for module_name, attr, kind in targets:
            try:
                holder = self._resolve_holder(module_name)
                original = getattr(holder, attr)
                if getattr(original, "_ptf_throughput_wrapped", False):
                    self.installed.append({"module": module_name, "attr": attr,
                                           "kind": kind, "note": "already wrapped"})
                    continue
                setattr(holder, attr, self._wrap(original, kind, module_name, attr))
                self.installed.append({"module": module_name, "attr": attr, "kind": kind})
            except Exception as exc:  # a missing target is a fact, not a failure
                self.skipped.append({"module": module_name, "attr": attr, "kind": kind,
                                     "why": "%s: %s" % (type(exc).__name__, exc)})

    @staticmethod
    def _resolve_holder(dotted: str) -> Any:
        """A module, or a class inside a module (``pkg.mod.Class``)."""
        import importlib
        try:
            return importlib.import_module(dotted)
        except ImportError:
            head, _, tail = dotted.rpartition(".")
            module = importlib.import_module(head)
            return getattr(module, tail)

    def _wrap(self, original: Callable, kind: str, module_name: str, attr: str) -> Callable:
        wrapper_self = self

        @functools.wraps(original)
        def wrapper(*args, **kwargs):
            wrapper_self.invocations += 1
            invocation = wrapper_self.invocations
            depth = wrapper_self.depth
            wrapper_self.depth += 1
            started = time.monotonic()
            started_ts = time.time()
            error = None
            result = None
            try:
                from scripts.pettripfinder import assembly_session_cache as _ASC
                events_before = len(_ASC.EVENTS)
            except Exception:
                _ASC, events_before = None, 0
            try:
                result = original(*args, **kwargs)
                return result
            except BaseException as exc:
                error = "%s: %s" % (type(exc).__name__, str(exc)[:200])
                raise
            finally:
                wrapper_self.depth -= 1
                elapsed = round(time.monotonic() - started, 3)
                try:
                    market_id = _market_id_of(args, kwargs)
                    context = kwargs.get("context")
                    if context is None and args and isinstance(args[0], str) \
                            and args[0] in ("production", "preview", "staging"):
                        context = args[0]
                    row: Dict[str, Any] = OrderedDict((
                        ("invocation_id", "%s-%04d" % (wrapper_self.recorder.run_id, invocation)),
                        ("assembly_kind", kind),
                        ("callee", "%s.%s" % (module_name, attr)),
                        ("nesting_depth", depth),
                        ("test_node_id", wrapper_self.current_node()),
                        ("market", market_id),
                        ("context", context),
                        ("output", _output_of(args, kwargs)),
                        ("start_ts", round(started_ts, 3)),
                        ("elapsed_seconds", elapsed),
                        ("output_hash", _hash_of_result(result)),
                        ("cache", NO_CACHE),
                        ("exit_status", "ok" if error is None else "error"),
                        ("error", error),
                        ("peak_working_set_mb", peak_working_set_mb()),
                        ("working_set_mb", working_set_mb()),
                    ))
                    # ATLAS-THROUGHPUT-002: what the session cache decided
                    # during this call. A REUSE_HIT is reported as a hit with
                    # the seconds it took AND the seconds it avoided; it is
                    # never reported as free work.
                    if _ASC is not None:
                        new_events = _ASC.EVENTS[events_before:]
                        mine = [e for e in new_events if e["assembly_kind"] in (
                            kind, {"market_bundle": "market_bundle", "production_site": "production_site",
                                   "columbus_site": "generator_site"}.get(kind, kind))]
                        own = mine[0] if mine else (new_events[0] if new_events and depth == 0 else None)
                        if own is not None:
                            row["cache"] = own["verdict"]
                            row["input_key"] = own["input_key"]
                            row["reused_seconds_avoided"] = own["reused_seconds_avoided"]
                        row["cache_events"] = [OrderedDict((
                            ("verdict", e["verdict"]), ("assembly_kind", e["assembly_kind"]),
                            ("input_key", e["input_key"]), ("seconds", e["seconds"]),
                            ("reused_seconds_avoided", e["reused_seconds_avoided"]),
                            ("args", e["args"]))) for e in new_events]
                    if market_id:
                        fp = wrapper_self.fingerprints.market(market_id)
                        row["market_input_hash"] = fp["sha256"]
                        row["market_input_files"] = fp["files"]
                    shared = wrapper_self.fingerprints.shared()
                    row["shared_input_hash"] = shared["sha256"]
                    if kind in ("production_site", "columbus_pilot", "listing_dataset",
                                "wge_assembly_engine", "pilot_load_launch_package"):
                        site = wrapper_self.fingerprints.whole_site()
                        row["dependency_input_hash"] = site["sha256"]
                        row["dependency_input_files"] = site["files"]
                    elif market_id:
                        h = hashlib.sha256()
                        h.update(row["market_input_hash"].encode("ascii"))
                        h.update(shared["sha256"].encode("ascii"))
                        row["dependency_input_hash"] = h.hexdigest()
                    wrapper_self.recorder.write("assembly", **row)
                except Exception:
                    wrapper_self.recorder.errors += 1

        wrapper._ptf_throughput_wrapped = True  # type: ignore[attr-defined]
        wrapper._ptf_throughput_original = original  # type: ignore[attr-defined]
        return wrapper


# --------------------------------------------------------------------------- #
# pytest hooks.
# --------------------------------------------------------------------------- #

def pytest_addoption(parser):
    group = parser.getgroup("pettripfinder-throughput")
    group.addoption("--ptf-profile-out", action="store", default=None,
                    help="JSONL file for ATLAS-THROUGHPUT profiling rows "
                         "(or set PTF_PROFILE_OUT); absent = plugin inert")
    group.addoption("--ptf-profile-fixture-floor", action="store", default="0.05",
                    help="record fixture setups slower than this many seconds")
    group.addoption("--ptf-inventory-out", action="store", default=None,
                    help="write a machine-readable inventory of every collected "
                         "test (node id, file, class, markers, fixtures, "
                         "parametrization) to this JSON file; works with "
                         "--collect-only")


def _item_inventory(item) -> Dict[str, Any]:
    nodeid = item.nodeid
    path = nodeid.split("::", 1)[0].replace("\\", "/")
    parts = nodeid.split("::")
    cls = parts[1] if len(parts) > 2 else ""
    markers = sorted({m.name for m in item.iter_markers()})
    lanes, market = _lanes_and_market(nodeid)
    marked_market = None
    for m in item.iter_markers("ptf_market"):
        marked_market = m.args[0] if m.args else None
    try:
        fixtures = sorted(item.fixturenames)
    except Exception:
        fixtures = []
    callspec = getattr(item, "callspec", None)
    return OrderedDict((
        ("node_id", nodeid), ("file", path), ("class", cls),
        ("name", parts[-1]),
        ("markers", markers), ("fixtures", fixtures),
        ("parametrized", callspec is not None),
        ("param_id", callspec.id if callspec is not None else None),
        ("lanes", lanes), ("market", market or marked_market),
    ))


def write_inventory(items, out: Path) -> Dict[str, Any]:
    """The Phase 4 inventory: one row per collected item plus roll-ups."""
    rows = [_item_inventory(item) for item in items]
    by_file: Dict[str, int] = {}
    by_market: Dict[str, int] = {}
    by_fixture: Dict[str, int] = {}
    base_functions: Dict[str, int] = {}
    for row in rows:
        by_file[row["file"]] = by_file.get(row["file"], 0) + 1
        key = row["market"] or "(none)"
        by_market[key] = by_market.get(key, 0) + 1
        for fx in row["fixtures"]:
            by_fixture[fx] = by_fixture.get(fx, 0) + 1
        base = row["node_id"].split("[", 1)[0]
        base_functions[base] = base_functions.get(base, 0) + 1
    doc = OrderedDict((
        ("schema", "ptf-test-inventory/1.0"),
        ("collected", len(rows)),
        ("test_functions", len(base_functions)),
        ("parametrized_items", sum(1 for r in rows if r["parametrized"])),
        ("by_file", OrderedDict(sorted(by_file.items(), key=lambda kv: -kv[1]))),
        ("by_market", OrderedDict(sorted(by_market.items(), key=lambda kv: -kv[1]))),
        ("by_fixture", OrderedDict(sorted(by_fixture.items(), key=lambda kv: -kv[1]))),
        ("parametrization_count_by_function", OrderedDict(
            sorted(((k, v) for k, v in base_functions.items() if v > 1),
                   key=lambda kv: -kv[1]))),
        ("items", rows),
    ))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    return doc


class _State:
    recorder: Optional[Recorder] = None
    wrap: Optional[AssemblyWrap] = None
    fingerprints: Optional[Fingerprints] = None
    session_started: float = 0.0
    session_started_ts: float = 0.0
    collection_finished: Optional[float] = None
    current_node: Optional[str] = None
    durations: Dict[str, Dict[str, float]] = {}
    outcomes: Dict[str, str] = {}
    fixture_floor: float = 0.05
    counts: Dict[str, int] = {}
    cpu_at_start: Dict[str, float] = {}


def _lanes_and_market(nodeid: str) -> Tuple[List[str], Optional[str]]:
    try:
        from scripts.pettripfinder import regression_lanes as LANES
        path = nodeid.split("::", 1)[0].replace("\\", "/")
        prefix = "tests/pettripfinder/"
        if not path.startswith(prefix):
            return [], None
        rel = path[len(prefix):]
        return list(LANES.lanes_for(rel)), LANES.market_for(rel)
    except Exception:
        return [], None


def pytest_configure(config):
    try:
        out = config.getoption("--ptf-profile-out") or os.environ.get("PTF_PROFILE_OUT")
        if not out:
            return
        try:
            _State.fixture_floor = float(config.getoption("--ptf-profile-fixture-floor"))
        except Exception:
            _State.fixture_floor = 0.05
        run_id = time.strftime("%Y%m%dT%H%M%S") + "-%d" % os.getpid()
        _State.recorder = Recorder(Path(out), run_id)
        _State.fingerprints = Fingerprints()
        _State.wrap = AssemblyWrap(_State.recorder, _State.fingerprints,
                                   lambda: _State.current_node)
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        _State.wrap.install()
        _State.session_started = time.monotonic()
        _State.session_started_ts = time.time()
        _State.cpu_at_start = cpu_times()
        _State.recorder.write(
            "session_start", pid=os.getpid(), ppid=os.getppid(),
            python=sys.version.split()[0], argv=list(sys.argv), cwd=os.getcwd(),
            git_head=git_head(), cpu=_State.cpu_at_start,
            wrapped=_State.wrap.installed, wrap_skipped=_State.wrap.skipped,
            fixture_floor_seconds=_State.fixture_floor,
            peak_working_set_mb=peak_working_set_mb())
    except Exception:
        _State.recorder = None


def pytest_collection_finish(session):
    try:
        inventory_out = session.config.getoption("--ptf-inventory-out") \
            or os.environ.get("PTF_INVENTORY_OUT")
        if inventory_out:
            write_inventory(session.items, Path(inventory_out))
    except Exception:
        if _State.recorder is not None:
            _State.recorder.errors += 1
    rec = _State.recorder
    if rec is None:
        return
    try:
        _State.collection_finished = time.monotonic()
        rec.write("collection", collected=len(session.items),
                  seconds=round(_State.collection_finished - _State.session_started, 3),
                  peak_working_set_mb=peak_working_set_mb())
    except Exception:
        rec.errors += 1


def pytest_runtest_logstart(nodeid, location):
    if _State.recorder is None:
        return
    _State.current_node = nodeid
    _State.durations[nodeid] = {}


def pytest_runtest_logreport(report):
    rec = _State.recorder
    if rec is None:
        return
    try:
        d = _State.durations.setdefault(report.nodeid, {})
        d[report.when] = round(float(report.duration), 4)
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            _State.outcomes[report.nodeid] = report.outcome
        if report.when == "teardown":
            outcome = _State.outcomes.pop(report.nodeid, report.outcome)
            lanes, market = _lanes_and_market(report.nodeid)
            _State.counts[outcome] = _State.counts.get(outcome, 0) + 1
            rec.write("test", node_id=report.nodeid,
                      module=report.nodeid.split("::", 1)[0],
                      market=market, lanes=lanes,
                      setup_seconds=d.get("setup"), call_seconds=d.get("call"),
                      teardown_seconds=d.get("teardown"),
                      total_seconds=round(sum(v for v in d.values() if v), 4),
                      outcome=outcome,
                      peak_working_set_mb=peak_working_set_mb(),
                      working_set_mb=working_set_mb())
            _State.durations.pop(report.nodeid, None)
    except Exception:
        rec.errors += 1


def pytest_fixture_setup(fixturedef, request):
    """Hookwrapper-free timing: pytest calls this for every fixture setup and
    the return value of a non-wrapper hook is ignored unless it is not
    ``None``, so timing is taken around the *next* hook via a wrapper below."""
    return None


try:
    import pytest as _pytest

    @_pytest.hookimpl(hookwrapper=True)
    def pytest_fixture_setup(fixturedef, request):  # noqa: F811
        rec = _State.recorder
        if rec is None:
            yield
            return
        started = time.monotonic()
        outcome = yield
        try:
            elapsed = time.monotonic() - started
            if elapsed >= _State.fixture_floor:
                rec.write("fixture_setup", fixture=fixturedef.argname,
                          scope=fixturedef.scope,
                          baseid=getattr(fixturedef, "baseid", None),
                          node_id=getattr(request, "node", None) and request.node.nodeid,
                          seconds=round(elapsed, 4),
                          failed=outcome.excinfo is not None,
                          peak_working_set_mb=peak_working_set_mb())
        except Exception:
            rec.errors += 1
except Exception:  # pragma: no cover
    pass


def pytest_sessionfinish(session, exitstatus):
    rec = _State.recorder
    if rec is None:
        return
    try:
        now = time.monotonic()
        try:
            from scripts.pettripfinder import assembly_session_cache as _ASC
            rec.write("assembly_session_cache", **_ASC.summary())
        except Exception:
            rec.errors += 1
        try:
            # ATLAS-THROUGHPUT-004: the persistent bundle cache's request
            # telemetry (MISS / HIT / HIT_AFTER_WAIT / REVALIDATE / INVALID_* /
            # BYPASS_COLD_REQUIRED), when the session touched it.
            _BC = sys.modules.get("scripts.pettripfinder.bundle_cache")
            if _BC is not None and _BC.EVENTS:
                rec.write("bundle_cache", **_BC.summary())
                for event in _BC.EVENTS:
                    rec.write("bundle_cache_request", **event)
        except Exception:
            rec.errors += 1
        try:
            # ATLAS-THROUGHPUT-005: what this session did to releases -- staged
            # candidates, authorizations, activations, rollbacks, and every
            # stale-parent refusal.
            _RC = sys.modules.get("scripts.pettripfinder.release_coordinator")
            if _RC is not None and _RC.EVENTS:
                rec.write("release_coordinator", **_RC.summary())
                for event in _RC.EVENTS:
                    rec.write("release_operation", **event)
        except Exception:
            rec.errors += 1
        rec.write("session_finish",
                  seconds=round(now - _State.session_started, 3),
                  collection_seconds=(round(_State.collection_finished - _State.session_started, 3)
                                      if _State.collection_finished else None),
                  execution_seconds=(round(now - _State.collection_finished, 3)
                                     if _State.collection_finished else None),
                  exit_status=int(exitstatus),
                  counts=dict(_State.counts),
                  assembly_invocations=_State.wrap.invocations if _State.wrap else 0,
                  peak_working_set_mb=peak_working_set_mb(),
                  cpu=cpu_times(), cpu_at_start=_State.cpu_at_start,
                  io_bytes=io_bytes(),
                  recorder_errors=rec.errors,
                  rows_written=rec.rows_written + 1)
    except Exception:
        rec.errors += 1
    finally:
        rec.close()
        _State.recorder = None
