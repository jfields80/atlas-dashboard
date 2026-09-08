"""ATLAS-THROUGHPUT-002 -- session-local reuse of identical assembly work.

WHY
---
ATLAS-THROUGHPUT-001 measured, in one instrumented broad run, 56 assembly
calls over 19 unique input keys: the whole production site composed three
times from identical inputs (two of them byte-identical, the third a preview
whose ten market fragments were identical), Columbus generated fifteen times,
and 37 repeated builds costing about 710 seconds of PetTripFinder assembly
(and ~3,800 more inside the demo-media suite). Nothing was cached; a repeat
cost the full build.

WHAT THIS IS
------------
A cache that lives and dies with ONE Python process. A builder that is asked
for the same INPUT KEY a second time in the same process gets a verified copy
of the first build instead of rebuilding. It is not the persistent artifact
cache a later order will design: nothing is written outside a per-process
temp directory, nothing survives the process, and nothing here is consulted
by the production CLI (which runs one assembly per process and therefore
always builds cold).

THE KEY
-------
``session_key(kind, args)`` = sha256 over

    * ``kind`` -- which builder (generator / market bundle / production site)
    * ``args`` -- every build argument the caller names (context, base_url,
      market id AND the market config's own content, contract content,
      keep_fragments, ...)
    * the INPUT FINGERPRINT: the content hash of every file under the roots
      the builders read -- launch_packages/pettripfinder (all of it),
      deploy/netlify, scripts, engines, repositories, templates, static -- so
      authority, routes, policy, geography, identity, templates AND the
      builder's own code are all in the key; plus the registry directory the
      markets loader is currently pointed at (a test that patches
      ``MARKETS_DIR`` gets a different key), the census-directory override,
      every ``PTF_*`` environment variable, and the interpreter/platform.

An output sha is never part of its own key. Content hashes are memoised per
(path, size, mtime_ns) so a second fingerprint costs a directory walk, and a
file edited between two calls changes the key.

SAFETY
------
* a build that raises stores nothing;
* a hit re-hashes the stored copy and refuses it if the digest moved;
* each consumer gets its OWN copy (``shutil.copytree``), so no test can
  mutate another's artifact;
* one lock per key: a concurrent same-key request waits for the first build;
* ``cold()`` is an explicit context manager that bypasses lookups for a
  test whose claim IS a cold execution (determinism, atomic replace);
* ``PTF_ASSEMBLY_REUSE=0`` disables reuse process-wide;
* every decision is appended to :data:`EVENTS` as BUILD_EXECUTED or
  REUSE_HIT with the seconds spent and, for a hit, the seconds the original
  build cost -- the profiler reads these so a hit is never reported as free
  work without saying so.
"""

from __future__ import annotations

import atexit
import contextlib
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

BUILD_EXECUTED = "BUILD_EXECUTED"
REUSE_HIT = "REUSE_HIT"

#: Everything a site build reads, relative to the repo root. Over-inclusive on
#: purpose: a report nobody reads costs a hash, a missed input costs a wrong
#: reuse.
INPUT_ROOTS: Tuple[str, ...] = (
    "launch_packages/pettripfinder",
    "deploy/netlify",
    "scripts",
    "engines",
    "repositories",
    "templates",
    "static",
    "models",
    "core",
)
_SKIP_DIRS = {"__pycache__", ".pytest_cache", "node_modules"}

#: Events for the profiler: BUILD_EXECUTED / REUSE_HIT rows, in order.
EVENTS: List[Dict[str, Any]] = []


def enabled() -> bool:
    return os.environ.get("PTF_ASSEMBLY_REUSE", "1").strip() not in ("0", "false", "no", "off")


_cold_depth = threading.local()


@contextlib.contextmanager
def cold():
    """Force a real build inside the block. The result is still stored, so a
    later consumer may reuse a build that a cold test proved deterministic."""
    depth = getattr(_cold_depth, "value", 0)
    _cold_depth.value = depth + 1
    try:
        yield
    finally:
        _cold_depth.value = depth


def _is_cold() -> bool:
    return getattr(_cold_depth, "value", 0) > 0


# --------------------------------------------------------------------------- #
# Fingerprints.
# --------------------------------------------------------------------------- #

_HASH_MEMO: Dict[Tuple[str, int, int], str] = {}
_hash_lock = threading.Lock()


def _file_sha(path: Path) -> str:
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    with _hash_lock:
        cached = _HASH_MEMO.get(key)
    if cached is not None:
        return cached
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    digest = h.hexdigest()
    with _hash_lock:
        _HASH_MEMO[key] = digest
    return digest


def _walk(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith((".pyc", ".pyo")):
                continue
            yield Path(dirpath) / name


def tree_fingerprint(roots: Sequence[Path], base: Path = REPO_ROOT) -> Tuple[str, int]:
    """``(sha256, file count)`` over sorted (relpath, content sha) pairs."""
    h = hashlib.sha256()
    count = 0
    for root in roots:
        for path in _walk(Path(root)):
            try:
                rel = path.resolve().relative_to(base.resolve()).as_posix()
            except ValueError:
                rel = path.as_posix()
            try:
                digest = _file_sha(path)
            except OSError:
                continue
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(digest.encode("ascii"))
            h.update(b"\n")
            count += 1
    return h.hexdigest(), count


def _dynamic_inputs() -> Dict[str, Any]:
    """Module globals and environment that redirect what a build reads."""
    out: Dict[str, Any] = OrderedDict()
    try:
        from scripts.pettripfinder.markets import contract as MC
        markets_dir = Path(MC.MARKETS_DIR)
        out["markets_dir"] = markets_dir.resolve().as_posix()
        default = (REPO_ROOT / "launch_packages" / "pettripfinder" / "markets").resolve()
        if markets_dir.resolve() != default:
            out["markets_dir_fingerprint"] = tree_fingerprint([markets_dir], markets_dir)[0]
    except Exception:
        out["markets_dir"] = "unknown"
    try:
        from scripts.pettripfinder import market_reports as MR
        out["reports_markets_dir"] = Path(MR.MARKETS_DIR).resolve().as_posix()
    except Exception:
        out["reports_markets_dir"] = "unknown"
    try:
        from scripts.pettripfinder import census_location as CL
        census_dir = Path(CL.identity_census_dir())
        out["census_dir"] = census_dir.resolve().as_posix()
        if census_dir.resolve() != CL.COMMITTED_CENSUS_DIR.resolve():
            out["census_dir_fingerprint"] = tree_fingerprint([census_dir], census_dir)[0]
    except Exception:
        out["census_dir"] = "unknown"
    out["env"] = OrderedDict(sorted((k, v) for k, v in os.environ.items()
                                    if k.startswith("PTF_") and k != "PTF_ASSEMBLY_REUSE"))
    out["python"] = sys.version
    out["platform"] = platform.platform()
    out["module_state"] = module_state_signature()
    return out


#: The modules whose module-level state a build reads. A test that
#: monkeypatches a constant (a control-file path, the live route inventory) or
#: swaps a function (a fake inventory reader) changes this signature and
#: therefore the key, so a patched build can never be answered from an
#: unpatched one.
STATE_MODULES: Tuple[str, ...] = (
    "scripts.generate_pettripfinder_columbus_site",
    "scripts.generate_pettripfinder_pilot",
    "scripts.pettripfinder.assemble_production_site",
    "scripts.pettripfinder.assemble_netlify_bundle",
    "scripts.pettripfinder.site_data",
    "scripts.pettripfinder.site_pages",
    "scripts.pettripfinder.site_enrichment",
    "scripts.pettripfinder.hotel_profile",
    "scripts.pettripfinder.hotel_profile_page",
    "scripts.pettripfinder.approved_hotel_profile",
    "scripts.pettripfinder.commercial_actions",
    "scripts.pettripfinder.measurement",
    "scripts.pettripfinder.market_ownership",
    "scripts.pettripfinder.market_context",
    "scripts.pettripfinder.market_reports",
    "scripts.pettripfinder.markets.contract",
    "scripts.pettripfinder.release_contracts",
    "scripts.pettripfinder.launch_participation",
    "scripts.pettripfinder.build_market_manifest",
    "scripts.pettripfinder.hotel_exclusions",
    "scripts.pettripfinder.market_authority",
    "scripts.pettripfinder.affiliate_destinations",
    "scripts.pettripfinder.publication_guard",
    "scripts.pettripfinder.listing_dataset_builder",
    "scripts.pettripfinder.census_location",
    "scripts.pettripfinder.structured_data",
)

_SIMPLE = (str, int, float, bool, bytes, type(None), Path)


def _value_signature(value: Any, depth: int = 0) -> Optional[str]:
    """Immutable module state and callable identity only. Mutable containers
    (a module's memo dict, a display-context cache) fill up DURING a build
    and would make the second key differ from the first without any input
    having changed; they are deliberately left out. A monkeypatched constant
    is a str / Path / tuple, a monkeypatched function is a callable -- both
    are seen."""
    if isinstance(value, _SIMPLE):
        return repr(value)
    if isinstance(value, (tuple, frozenset)) and depth < 3:
        parts = [_value_signature(v, depth + 1) for v in (sorted(value, key=repr) if isinstance(value, frozenset) else value)]
        return "[" + ",".join(p if p is not None else "?" for p in parts) + "]"
    if callable(value) and not isinstance(value, type):
        return "callable:%s.%s" % (getattr(value, "__module__", "?"), getattr(value, "__qualname__", repr(value)))
    return None


#: Module globals the BUILD ITSELF sets through the one-call setters
#: (``set_published_categories`` and friends). They are outputs of a build's
#: market scoping, not inputs to it: the same market always sets the same
#: values, and including them made the first key of a process differ from
#: every later one. A test that wants a different value calls the setter,
#: which the generator re-applies on every call anyway.
BUILD_STATE_GLOBALS: Tuple[str, ...] = (
    "scripts.pettripfinder.site_pages.PUBLISHED_CATEGORIES",
    "scripts.pettripfinder.site_pages.COMPARISON_ROUTE",
    "scripts.pettripfinder.approved_hotel_profile.MARKET_LABEL",
    "scripts.pettripfinder.approved_hotel_profile.MARKET_STATE",
    "scripts.pettripfinder.approved_hotel_profile.MARKET_METRO_DEFAULT",
    "scripts.pettripfinder.approved_hotel_profile.PUBLISHED_CATEGORIES",
    # commercial_actions._GO_MARKET_PREFIX and measurement._CONFIG are
    # private and skipped by the underscore rule below.
)


def module_state_signature(modules: Sequence[str] = STATE_MODULES) -> str:
    """One sha256 over the simple module-level values and the identity of
    every module-level callable of :data:`STATE_MODULES`. Every module is
    imported first, so a module the first build pulls in lazily does not make
    the second key differ."""
    import importlib
    h = hashlib.sha256()
    for name in modules:
        mod = sys.modules.get(name)
        if mod is None:
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue
        for attr, value in sorted(vars(mod).items()):
            if attr.startswith("__") or attr.startswith("_"):
                continue
            if "%s.%s" % (name, attr) in BUILD_STATE_GLOBALS:
                continue
            if isinstance(value, type(sys)):          # a module reference
                continue
            sig = _value_signature(value)
            if sig is None:
                continue
            h.update(("%s.%s=%s\n" % (name, attr, sig[:2000])).encode("utf-8", "replace"))
    return h.hexdigest()


def input_fingerprint() -> Dict[str, Any]:
    roots = [REPO_ROOT / r for r in INPUT_ROOTS]
    sha, count = tree_fingerprint(roots)
    dyn = _dynamic_inputs()
    return OrderedDict((("repo_inputs_sha256", sha), ("repo_input_files", count),
                        ("dynamic", dyn)))


def session_key(kind: str, args: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """``(key, key_document)``. The document is kept with the entry so a
    profiler can say what the key covered."""
    fp = input_fingerprint()
    doc = OrderedDict((("kind", kind), ("args", args), ("inputs", fp)))
    key = hashlib.sha256(json.dumps(doc, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return key, doc


# --------------------------------------------------------------------------- #
# The store.
# --------------------------------------------------------------------------- #

class Entry:
    def __init__(self, key: str, kind: str, store: Path, digest: str, result: Any,
                 build_seconds: float, key_doc: Dict[str, Any]):
        self.key = key
        self.kind = kind
        self.store = store
        self.digest = digest
        self.result = result
        self.build_seconds = build_seconds
        self.key_doc = key_doc
        self.hits = 0


class SessionCache:
    def __init__(self):
        self._root: Optional[Path] = None
        self._entries: Dict[str, Entry] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    @property
    def root(self) -> Path:
        with self._guard:
            if self._root is None:
                self._root = Path(tempfile.mkdtemp(prefix="ptf-asm-session-"))
                atexit.register(self.close)
            return self._root

    def close(self) -> None:
        with self._guard:
            root, self._root = self._root, None
            self._entries.clear()
        if root is not None:
            shutil.rmtree(root, ignore_errors=True)

    def clear(self) -> None:
        """Forget every entry (tests use this between scenarios)."""
        self.close()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    def entries(self) -> List[Entry]:
        with self._guard:
            return list(self._entries.values())

    def reuse_or_build(self, kind: str, args: Dict[str, Any], output: Path,
                       build: Callable[[], Any]) -> Tuple[Any, Dict[str, Any]]:
        """Return ``(result, event)``.

        ``build`` must produce the artifact under ``output`` and return the
        result the caller would have returned. On a hit ``output`` receives a
        verified copy of the stored artifact and ``result`` is a deep copy of
        the stored result.
        """
        output = Path(output)
        key, key_doc = session_key(kind, args)
        lock = self._lock_for(key)
        with lock:
            entry = self._entries.get(key) if (enabled() and not _is_cold()) else None
            if entry is not None and self._verify(entry):
                started = time.monotonic()
                self._materialize(entry, output)
                seconds = time.monotonic() - started
                entry.hits += 1
                event = self._event(REUSE_HIT, kind, key, seconds, entry.build_seconds, key_doc, output)
                return json.loads(json.dumps(entry.result, default=str)) if isinstance(entry.result, (dict, list)) else entry.result, event
            started = time.monotonic()
            result = build()                       # any exception propagates; nothing stored
            seconds = time.monotonic() - started
            store = self.root / key[:24]
            if store.exists():
                shutil.rmtree(store, ignore_errors=True)
            shutil.copytree(output, store)
            digest = self.digest_of(store)
            with self._guard:
                self._entries[key] = Entry(key, kind, store, digest, result, seconds, key_doc)
            event = self._event(BUILD_EXECUTED, kind, key, seconds, None, key_doc, output)
            return result, event

    @staticmethod
    def digest_of(root: Path) -> str:
        h = hashlib.sha256()
        for path in _walk(root):
            rel = path.relative_to(root).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(_file_sha(path).encode("ascii"))
            h.update(b"\n")
        return h.hexdigest()

    def _verify(self, entry: Entry) -> bool:
        if not entry.store.is_dir():
            return False
        if self.digest_of(entry.store) != entry.digest:
            with self._guard:
                self._entries.pop(entry.key, None)
            shutil.rmtree(entry.store, ignore_errors=True)
            return False
        return True

    @staticmethod
    def _materialize(entry: Entry, output: Path) -> None:
        if output.exists():
            shutil.rmtree(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(entry.store, output)

    @staticmethod
    def _event(verdict: str, kind: str, key: str, seconds: float, avoided: Optional[float],
               key_doc: Dict[str, Any], output: Path) -> Dict[str, Any]:
        event = OrderedDict((
            ("verdict", verdict), ("assembly_kind", kind), ("input_key", key),
            ("seconds", round(seconds, 3)),
            ("reused_seconds_avoided", round(avoided - seconds, 3) if avoided is not None else None),
            ("output", str(output)), ("ts", round(time.time(), 3)),
            ("args", key_doc["args"]),
            ("repo_inputs_sha256", key_doc["inputs"]["repo_inputs_sha256"]),
            ("repo_input_files", key_doc["inputs"]["repo_input_files"]),
        ))
        EVENTS.append(event)
        return event


CACHE = SessionCache()


def summary() -> Dict[str, Any]:
    """BUILD_COUNT / REUSE_COUNT / BUILD_SECONDS / REUSED_SECONDS_AVOIDED per key."""
    per_key: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    for e in EVENTS:
        row = per_key.setdefault(e["input_key"], OrderedDict((
            ("input_key", e["input_key"]), ("assembly_kind", e["assembly_kind"]),
            ("args", e["args"]), ("build_count", 0), ("reuse_count", 0),
            ("build_seconds", 0.0), ("reuse_seconds", 0.0), ("reused_seconds_avoided", 0.0))))
        if e["verdict"] == BUILD_EXECUTED:
            row["build_count"] += 1
            row["build_seconds"] = round(row["build_seconds"] + e["seconds"], 3)
        else:
            row["reuse_count"] += 1
            row["reuse_seconds"] = round(row["reuse_seconds"] + e["seconds"], 3)
            row["reused_seconds_avoided"] = round(row["reused_seconds_avoided"] + (e["reused_seconds_avoided"] or 0.0), 3)
    return OrderedDict((
        ("enabled", enabled()),
        ("keys", len(per_key)),
        ("build_count", sum(r["build_count"] for r in per_key.values())),
        ("reuse_count", sum(r["reuse_count"] for r in per_key.values())),
        ("build_seconds", round(sum(r["build_seconds"] for r in per_key.values()), 3)),
        ("reused_seconds_avoided", round(sum(r["reused_seconds_avoided"] for r in per_key.values()), 3)),
        ("per_key", list(per_key.values())),
    ))
