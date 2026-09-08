"""ATLAS-THROUGHPUT-004 -- the persistent content-addressed market-bundle cache.

    IF every declared build input is identical
    AND the exact output bytes were previously validated under a compatible
        validation policy
    THEN do not rebuild that market: reuse the validated bundle.

A cache hit is a PROOF of identity, never an assumption:

* the BUILD INPUT KEY is the sha256 of a canonical build-input manifest
  (:func:`build_input_manifest`) over the sealed package, its section
  digests, the staged render tree, every shared data file the build reads,
  every repository module the build loads, the builder and assembler sources,
  the toolchain (interpreter, platform, lockfiles, installed package
  versions), the build arguments and the PTF_* environment -- the closure
  MEASURED by tracing two real builds and committed as
  ``launch_packages/pettripfinder/bundle_cache_closure.json``;
* the artifact is stored under its own content digest (the deployer's
  ``bundle_digest`` formula) as an immutable zip that is never overwritten;
* a bundle validation receipt binds the input key, the output digest, the
  validation policy version and the dependency digests, and records the
  assembler gates, the determinism proof and the undeclared-read check;
* a lookup materialises the stored bytes, RE-HASHES them, re-reads the
  receipt and re-checks revocation and freshness before calling anything a
  hit. Anything less is a miss, and a questionable entry is quarantined.

What this cache is NOT: a release authorization. It proves that bytes are
the bytes a declared input set produces; ``fast_release_lane`` proves a
release is safe; ATLAS-THROUGHPUT-005 coordinates the two. Production
deployment does not consume this cache (``PRODUCTION_RELEASE_CONSUMPTION =
DISABLED`` in ``fast_release_activation.json``).
"""

from __future__ import annotations

import builtins
import hashlib
import io
import json
import locale
import os
import platform
import shutil
import sys
import threading
import time
import uuid
import zipfile
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Set, Tuple

from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import first_party_binding as FPB
from scripts.pettripfinder import package_staging as STAGING
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = SMP.REPO_ROOT
CLOSURE_PATH = SMP.LAUNCH_PACKAGE / "bundle_cache_closure.json"
DEFAULT_ROOT = REPO_ROOT / "data" / "bundle_cache"
ROOT_ENV = "PTF_BUNDLE_CACHE_ROOT"
FORBID_BUILD_ENV = "PTF_BUNDLE_CACHE_FORBID_BUILD"

MANIFEST_SCHEMA = "ptf-bundle-build-input-manifest/1.0"
ENTRY_SCHEMA = "ptf-bundle-cache-entry/1.0"
RECEIPT_SCHEMA = "ptf-bundle-validation-receipt/1.0"
CLOSURE_SCHEMA = "ptf-bundle-cache-closure/1.0"
#: The validation policy a receipt is issued under. Bump it when a rule
#: changes; a receipt under an older but COMPATIBLE policy is revalidated
#: cheaply (bytes reused, new receipt), an incompatible one forces a rebuild.
VALIDATION_POLICY = "ptf-bundle-validation/1.0"
COMPATIBLE_POLICIES: Tuple[str, ...] = (VALIDATION_POLICY,)

# Cache statuses (observability).
MISS = "MISS"
HIT = "HIT"
HIT_AFTER_WAIT = "HIT_AFTER_WAIT"
REVALIDATE = "REVALIDATE"
INVALID_CORRUPT = "INVALID_CORRUPT"
INVALID_REVOKED = "INVALID_REVOKED"
INVALID_POLICY_VERSION = "INVALID_POLICY_VERSION"
BYPASS_COLD_REQUIRED = "BYPASS_COLD_REQUIRED"
BUILD_FORBIDDEN = "BUILD_FORBIDDEN"

# Trust states.
TRUSTED = "TRUSTED"
UNTRUSTED = "UNTRUSTED"
QUARANTINED = "QUARANTINED"
REVOKED = "REVOKED"

EVENTS: List[Dict[str, Any]] = []

#: Repository modules that may be loaded around a build without being part
#: of it: the cache itself, the lane that calls it, the pilots and tests.
NON_BUILD_MODULES: Tuple[str, ...] = (
    "scripts/pettripfinder/bundle_cache.py",
    "scripts/pettripfinder/fast_release_lane.py",
    "scripts/pettripfinder/first_party_binding.py",
    "scripts/pettripfinder/release_index.py",
    "scripts/pettripfinder/market_package_writer.py",
    "scripts/pettripfinder/atlas_throughput_003_pilot.py",
    "scripts/pettripfinder/atlas_throughput_004_pilot.py",
    "scripts/pettripfinder/throughput_profile.py",
    "scripts/pettripfinder/regression_delta.py",
    "scripts/pettripfinder/regression_lanes.py",
)


class BundleCacheError(RuntimeError):
    """The cache refused (fail closed); a caller may still build cold."""


class BuildForbidden(BundleCacheError):
    """A build was requested where the caller declared none may happen."""


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _posix(relpath: str) -> str:
    return relpath.replace("\\", "/")


def load_closure(path: Optional[Path] = None) -> "OrderedDict[str, Any]":
    doc = json.loads((Path(path) if path else CLOSURE_PATH).read_text(encoding="utf-8-sig"),
                     object_pairs_hook=OrderedDict)
    if doc.get("schema") != CLOSURE_SCHEMA:
        raise BundleCacheError("closure schema %r is not %s" % (doc.get("schema"), CLOSURE_SCHEMA))
    for key in ("shared_data_inputs", "per_market_data_inputs", "code_modules"):
        if not isinstance(doc.get(key), list) or not doc[key]:
            raise BundleCacheError("closure %s is missing or empty" % key)
    return doc


def closure_digest(closure: Mapping) -> str:
    return SMP.sha256_text(SMP.canonical_json(closure))


# --------------------------------------------------------------------------- #
# The canonical build input manifest.
# --------------------------------------------------------------------------- #

def _requirement_names(path: Path) -> List[str]:
    names: List[str] = []
    if not path.is_file():
        return names
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        name = ""
        for ch in line:
            if ch.isalnum() or ch in "-_.":
                name += ch
            else:
                break
        if name:
            names.append(name)
    return names


def toolchain_identity(repo_root: Path = REPO_ROOT) -> "OrderedDict[str, Any]":
    """Interpreter, platform, lockfiles and the installed versions of every
    declared dependency. Node is not part of this build path."""
    from importlib import metadata
    lockfiles: "OrderedDict[str, Optional[str]]" = OrderedDict()
    packages: "OrderedDict[str, Optional[str]]" = OrderedDict()
    for name in ("requirements.txt", "requirements-dev.txt"):
        path = repo_root / name
        lockfiles[name] = _sha_file(path) if path.is_file() else None
        for req in _requirement_names(path):
            try:
                packages[req] = metadata.version(req)
            except metadata.PackageNotFoundError:
                packages[req] = None
    return OrderedDict((
        ("python_version", platform.python_version()),
        ("python_implementation", platform.python_implementation()),
        ("platform_system", platform.system()),
        ("platform_machine", platform.machine()),
        ("node_version", "not_applicable: static site, no Node toolchain on the build path"),
        ("lockfiles", lockfiles),
        ("packages", OrderedDict(sorted(packages.items()))),
    ))


def _section_digest(*sections: Any) -> str:
    return SMP.sha256_text(SMP.canonical_json(list(sections)))


def _hash_paths(relpaths: Sequence[str], repo_root: Path) -> "OrderedDict[str, Optional[str]]":
    out: "OrderedDict[str, Optional[str]]" = OrderedDict()
    for rel in sorted(set(_posix(p) for p in relpaths)):
        path = repo_root / rel
        out[rel] = _sha_file(path) if path.is_file() else None
    return out


def _env_inputs() -> "OrderedDict[str, str]":
    return OrderedDict(sorted((k, v) for k, v in os.environ.items()
                              if k.startswith("PTF_") and not k.startswith("PTF_BUNDLE_CACHE")))


def build_input_manifest(package: Mapping, staged_input_digest: str, *,
                         context: str = "production", closure: Optional[Mapping] = None,
                         repo_root: Path = REPO_ROOT) -> "OrderedDict[str, Any]":
    """Every declared input of one market-bundle build, canonically.

    The output digest is never an input. ``validation_policy_version`` is
    carried in the manifest for the record but sits OUTSIDE the byte key
    (see :func:`build_input_key`): a policy change never changes the bytes a
    build produces, it changes what a receipt must prove.
    """
    closure = closure if closure is not None else load_closure()
    market_id = str(package["market_id"])
    shared = _hash_paths(closure["shared_data_inputs"], repo_root)
    per_market = _hash_paths([p.replace("<market_id>", market_id) for p in closure["per_market_data_inputs"]], repo_root)
    code = _hash_paths(closure["code_modules"], repo_root)
    missing_code = [p for p, d in code.items() if d is None]
    if missing_code:
        raise BundleCacheError("declared code closure names %d missing module(s): %s"
                               % (len(missing_code), missing_code[:5]))
    templates = OrderedDict((p, d) for p, d in shared.items() if p.endswith((".css", ".html", ".txt")))
    assets = OrderedDict((p, d) for p, d in shared.items() if p.endswith((".jpg", ".jpeg", ".png", ".webp", ".svg")))
    data = OrderedDict((p, d) for p, d in shared.items() if p not in templates and p not in assets)
    builder_files = ("scripts/generate_pettripfinder_columbus_site.py", "scripts/generate_pettripfinder_pilot.py",
                     "scripts/pettripfinder/package_staging.py")
    assembler_files = ("scripts/pettripfinder/assemble_netlify_bundle.py",)
    index_routes = _public_routes(package)
    return OrderedDict((
        ("schema", MANIFEST_SCHEMA),
        ("kind", "market_bundle"),
        ("market_id", market_id),
        ("package_digest", package["package_digest"]),
        ("package_schema", package["schema"]),
        ("authority_digest", _section_digest(package["census"], package["verified_no_pets_records"],
                                             package["official_routes"], package["seed_rows"])),
        ("route_digest", _section_digest(index_routes)),
        ("policy_digest", _section_digest(package["pet_friendly_records"])),
        ("evidence_manifest_digest", _section_digest(package["evidence_references"], package["evidence_hashes"])),
        ("geography_identity_digest", _section_digest(package["market"], package["identity_records"])),
        ("market_config_digest", _section_digest(package["market"])),
        ("partition_digest", _section_digest(package["partition"])),
        ("render_input_digest", staged_input_digest),
        ("builder_digest", SMP.sha256_text(SMP.canonical_json(_hash_paths(builder_files, repo_root)))),
        ("assembler_digest", SMP.sha256_text(SMP.canonical_json(_hash_paths(assembler_files, repo_root)))),
        ("shared_runtime_dependency_digest", SMP.sha256_text(SMP.canonical_json(code))),
        ("shared_runtime_modules", len(code)),
        ("template_digest", SMP.sha256_text(SMP.canonical_json(templates))),
        ("asset_digest", SMP.sha256_text(SMP.canonical_json(assets))),
        ("shared_data_digest", SMP.sha256_text(SMP.canonical_json(data))),
        ("per_market_data_digest", SMP.sha256_text(SMP.canonical_json(per_market))),
        ("declared_closure_digest", closure_digest(closure)),
        ("toolchain", toolchain_identity(repo_root)),
        ("build_arguments", OrderedDict((("context", context), ("cold", True),
                                         ("builder", "package_staging.build_changed_market")))),
        ("locale", OrderedDict((("preferred_encoding", locale.getpreferredencoding(False)),
                                ("utf8_mode", int(sys.flags.utf8_mode))))),
        ("env_inputs", _env_inputs()),
        ("time_inputs", OrderedDict((("reference_date", "not in the bytes: date.today() feeds only the "
                                                         "launch-readiness gate; recorded on the receipt"),))),
        ("validation_policy_version", VALIDATION_POLICY),
        ("fast_lane_version", FL.LANE_VERSION),
        ("contract_versions", OrderedDict(package["contract_versions"])),
        ("builder_version", package["builder_version"]),
    ))


#: Manifest fields that identify the BYTES. Everything else (policy versions)
#: identifies what a receipt must prove.
KEY_FIELDS: Tuple[str, ...] = (
    "schema", "kind", "market_id", "package_digest", "package_schema", "authority_digest",
    "route_digest", "policy_digest", "evidence_manifest_digest", "geography_identity_digest",
    "market_config_digest", "partition_digest", "render_input_digest", "builder_digest",
    "assembler_digest", "shared_runtime_dependency_digest", "template_digest", "asset_digest",
    "shared_data_digest", "per_market_data_digest", "declared_closure_digest", "toolchain",
    "build_arguments", "locale", "env_inputs", "contract_versions", "builder_version",
)


def build_input_key(manifest: Mapping) -> str:
    body = OrderedDict((k, manifest[k]) for k in KEY_FIELDS)
    return SMP.sha256_text(SMP.canonical_json(body))


def _public_routes(package: Mapping) -> List[str]:
    from scripts.pettripfinder import release_index as RI
    index = RI.index_from_package(package, participating=True)
    return list(index.routes)


# --------------------------------------------------------------------------- #
# Deterministic archive.
# --------------------------------------------------------------------------- #

def write_archive(site_dir: Path, target: Path) -> "OrderedDict[str, Any]":
    """A deterministic zip of ``site_dir``: sorted entries, fixed timestamps."""
    from scripts.pettripfinder.assemble_production_site import bundle_digest, file_hashes
    hashes = file_hashes(site_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in sorted(hashes):
            data = (site_dir / rel).read_bytes()
            total += len(data)
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    return OrderedDict((("bundle_sha256", bundle_digest(hashes)), ("file_count", len(hashes)),
                        ("byte_size", total), ("archive_sha256", _sha_file(target)),
                        ("archive_bytes", target.stat().st_size)))


def extract_archive(archive: Path, target: Path) -> "OrderedDict[str, str]":
    from scripts.pettripfinder.assemble_production_site import file_hashes
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = info.filename
            if name.startswith("/") or ".." in name.split("/"):
                raise BundleCacheError("archive entry escapes the target: %r" % name)
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(info))
    return file_hashes(target)


# --------------------------------------------------------------------------- #
# Read tracing: the undeclared-dependency check.
# --------------------------------------------------------------------------- #

class _ReadTracer:
    """Records the repository files THIS thread reads (other threads may be
    staging or hashing their own requests meanwhile) and the modules that
    enter sys.modules during the build."""

    def __init__(self, repo_root: Path, ignore: Sequence[Path]):
        self.repo = repo_root.resolve()
        self.ignore = [Path(p).resolve() for p in ignore]
        self.reads: Set[str] = set()
        self._open = builtins.open
        self._io_open = io.open
        self._modules_before: Set[str] = set()
        self._thread = threading.get_ident()

    def _record(self, file, mode):
        try:
            if threading.get_ident() != self._thread:
                return
            mode = str(mode)
            if not isinstance(file, (str, bytes, os.PathLike)) or "w" in mode or "a" in mode or "+" in mode:
                return
            p = Path(os.fsdecode(file)).resolve()
            if self.repo not in p.parents or any(i == p or i in p.parents for i in self.ignore):
                return
            self.reads.add(p.relative_to(self.repo).as_posix())
        except Exception:
            pass

    def __enter__(self):
        tracer = self

        def traced(file, mode="r", *a, **k):
            tracer._record(file, mode)
            return tracer._open(file, mode, *a, **k)

        def traced_code(path):
            tracer._record(path, "rb")
            return tracer._open_code(path)
        self._open_code = io.open_code
        traced.__tracer__ = self
        builtins.open = traced
        io.open = traced
        io.open_code = traced_code          # module source / bytecode loads
        self._modules_before = set(sys.modules)
        return self

    def __exit__(self, *exc):
        # Only unwind our own patch; another thread's tracer may be above us.
        if builtins.open is not self._open and getattr(builtins.open, "__tracer__", None) is self:
            builtins.open = self._open
            io.open = self._io_open
            io.open_code = self._open_code
        elif getattr(builtins.open, "__tracer__", None) is self:
            builtins.open = self._open
            io.open = self._io_open
            io.open_code = self._open_code

    def repo_modules(self) -> List[str]:
        """Repository modules the build LOADED: every source or bytecode read
        the import system made during the build, plus every module that
        entered sys.modules meanwhile."""
        out = set(p for p in self.reads if p.endswith((".py", ".pyc")))
        for name in set(sys.modules) - self._modules_before:
            m = sys.modules.get(name)
            f = getattr(m, "__file__", None)
            if not f:
                continue
            try:
                p = Path(f).resolve()
            except Exception:
                continue
            if self.repo in p.parents:
                out.add(p.relative_to(self.repo).as_posix())
        return sorted(p[:-1] if p.endswith(".pyc") else p for p in out)


def undeclared_dependencies(tracer: _ReadTracer, closure: Mapping, market_id: str) -> "OrderedDict[str, List[str]]":
    declared_data = set(_posix(p) for p in closure["shared_data_inputs"])
    declared_data |= {p.replace("<market_id>", market_id) for p in closure["per_market_data_inputs"]}
    declared_code = set(_posix(p) for p in closure["code_modules"])
    data_reads = [p for p in sorted(tracer.reads) if not p.endswith((".py", ".pyc"))]
    undeclared_data = [p for p in data_reads if p not in declared_data and not p.startswith("data/")]
    undeclared_code = [p for p in tracer.repo_modules() if p not in declared_code
                       and not p.startswith(("tests/", "data/", "__pycache__/"))
                       and "/__pycache__/" not in p
                       and p not in NON_BUILD_MODULES]
    return OrderedDict((("data", undeclared_data), ("code", undeclared_code)))


# --------------------------------------------------------------------------- #
# The cache.
# --------------------------------------------------------------------------- #

class BundleCache:
    """Persistent, content-addressed, fail-closed."""

    def __init__(self, root: Optional[Path] = None, *, repo_root: Path = REPO_ROOT,
                 closure: Optional[Mapping] = None, run_id: Optional[str] = None):
        env_root = os.environ.get(ROOT_ENV, "").strip()
        self.root = Path(root) if root else (Path(env_root) if env_root else DEFAULT_ROOT)
        self.repo_root = Path(repo_root)
        self.closure = closure if closure is not None else load_closure()
        self.run_id = run_id or ("run-%s" % uuid.uuid4().hex[:12])
        self._thread_locks: Dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        for sub in ("objects", "index", "receipts", "locks", "quarantine", "tmp"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    # ---- paths ------------------------------------------------------------ #
    def object_path(self, bundle_sha256: str) -> Path:
        return self.root / "objects" / ("%s.zip" % bundle_sha256.split(":", 1)[-1])

    def index_path(self, key: str) -> Path:
        return self.root / "index" / ("%s.json" % key.split(":", 1)[-1])

    def receipt_path(self, receipt_digest: str) -> Path:
        return self.root / "receipts" / ("%s.json" % receipt_digest.split(":", 1)[-1])

    def lock_path(self, key: str) -> Path:
        return self.root / "locks" / ("%s.lock" % key.split(":", 1)[-1])

    # ---- telemetry -------------------------------------------------------- #
    def _event(self, status: str, market_id: str, key: str, **fields: Any) -> Dict[str, Any]:
        event: "OrderedDict[str, Any]" = OrderedDict((("run_id", self.run_id), ("market_id", market_id),
                                                       ("build_input_key", key), ("cache_status", status),
                                                       ("ts", round(time.time(), 3))))
        event.update(fields)
        EVENTS.append(event)
        try:
            with open(self.root / "telemetry.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
        except OSError:
            pass
        return event

    # ---- manifest ---------------------------------------------------------- #
    def manifest_for(self, package: Mapping, work_dir: Path, *, context: str = "production"
                     ) -> Tuple["OrderedDict[str, Any]", str, "OrderedDict[str, str]"]:
        """Stage the package (cheap) and derive the manifest and key."""
        staged = STAGING.stage_package(package, Path(work_dir) / "stage", repo_root=self.repo_root)
        staged_digest = SMP.sha256_text(SMP.canonical_json(staged))
        manifest = build_input_manifest(package, staged_digest, context=context, closure=self.closure,
                                        repo_root=self.repo_root)
        return manifest, build_input_key(manifest), staged

    # ---- lookup ------------------------------------------------------------ #
    def probe(self, package: Mapping, *, context: str = "production") -> "OrderedDict[str, Any]":
        """Is there a TRUSTED entry for this package's current input key?
        Cheap (stage + hash, no extraction): the classifier's question.
        A full :meth:`verify` still decides an actual reuse."""
        import tempfile
        work = Path(tempfile.mkdtemp(prefix="ptf-bc-probe-"))
        try:
            _manifest, key, _staged = self.manifest_for(package, work, context=context)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        entry = self.read_entry(key)
        out: "OrderedDict[str, Any]" = OrderedDict((("build_input_key", key), ("trusted", False),
                                                   ("package_id", package.get("package_id"))))
        if entry is None:
            out["why"] = "no entry for this input key"
            return out
        archive = self.object_path(str(entry.get("output_bundle_digest") or ""))
        out["trust_state"] = entry.get("trust_state")
        out["output_bundle_digest"] = entry.get("output_bundle_digest")
        out["receipt_digest"] = entry.get("validation_receipt_digest")
        out["trusted"] = (entry.get("trust_state") == TRUSTED and archive.is_file()
                          and archive.stat().st_size == entry.get("archive_bytes")
                          and entry.get("validation_policy_version") == VALIDATION_POLICY)
        out["why"] = "trusted entry, artifact present" if out["trusted"] else "entry not trusted or artifact missing"
        return out

    def read_entry(self, key: str) -> Optional["OrderedDict[str, Any]"]:
        path = self.index_path(key)
        if not path.is_file():
            return None
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
        except ValueError:
            self._quarantine(key, "index row is not JSON")
            return None
        if not isinstance(doc, Mapping) or doc.get("schema") != ENTRY_SCHEMA or doc.get("build_input_key") != key:
            self._quarantine(key, "index row is malformed or names another key")
            return None
        return doc

    def read_receipt(self, receipt_digest: str) -> Optional["OrderedDict[str, Any]"]:
        path = self.receipt_path(receipt_digest)
        if not path.is_file():
            return None
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
        except ValueError:
            return None
        if doc.get("schema") != RECEIPT_SCHEMA or receipt_digest_of(doc) != receipt_digest:
            return None
        return doc

    def verify(self, key: str, entry: Mapping, output_dir: Path, *,
               revocations: Optional[Mapping[str, Mapping]] = None,
               now: Optional[datetime] = None) -> Tuple[str, "OrderedDict[str, Any]"]:
        """Prove an entry: bytes, digest, receipt, binding, policy, revocation,
        freshness. Returns ``(status, detail)``; anything but HIT/REVALIDATE
        is a miss. The bundle is materialised into ``output_dir`` on success."""
        started = time.perf_counter()
        detail: "OrderedDict[str, Any]" = OrderedDict()
        if entry.get("trust_state") != TRUSTED:
            return MISS, OrderedDict((("why", "entry is %s" % entry.get("trust_state")),))
        bundle_sha = str(entry.get("output_bundle_digest") or "")
        archive = self.object_path(bundle_sha)
        if not archive.is_file():
            self._quarantine(key, "artifact missing: %s" % archive.name)
            return INVALID_CORRUPT, OrderedDict((("why", "artifact file missing"),))
        if archive.stat().st_size == 0 or archive.stat().st_size != entry.get("archive_bytes"):
            self._quarantine(key, "artifact size %d != recorded %r" % (archive.stat().st_size, entry.get("archive_bytes")))
            return INVALID_CORRUPT, OrderedDict((("why", "artifact size mismatch (partial or zero-byte write)"),))
        t = time.perf_counter()
        if _sha_file(archive) != entry.get("archive_sha256"):
            self._quarantine(key, "archive digest mismatch")
            return INVALID_CORRUPT, OrderedDict((("why", "archive digest mismatch"),))
        try:
            hashes = extract_archive(archive, Path(output_dir) / "site")
        except (zipfile.BadZipFile, BundleCacheError, OSError) as exc:
            self._quarantine(key, "archive unreadable: %s" % exc)
            return INVALID_CORRUPT, OrderedDict((("why", "archive unreadable: %s" % str(exc)[:120]),))
        from scripts.pettripfinder.assemble_production_site import bundle_digest
        actual = bundle_digest(hashes)
        detail["verify_seconds"] = round(time.perf_counter() - t, 3)
        if actual != bundle_sha.split(":", 1)[-1]:
            self._quarantine(key, "extracted bytes hash to %s, entry says %s" % (actual[:16], bundle_sha[:23]))
            return INVALID_CORRUPT, OrderedDict((("why", "extracted bytes do not hash to the recorded digest"),))
        receipt = self.read_receipt(str(entry.get("validation_receipt_digest") or ""))
        if receipt is None:
            self._quarantine(key, "receipt missing or its digest does not re-derive")
            return INVALID_CORRUPT, OrderedDict((("why", "receipt missing or corrupt"),))
        binding_problems = receipt_binding_problems(receipt, key=key, bundle_sha256=bundle_sha,
                                                    manifest_dependencies=entry.get("dependency") or {})
        if binding_problems:
            self._quarantine(key, "receipt does not bind this entry: %s" % binding_problems[:2])
            return INVALID_CORRUPT, OrderedDict((("why", binding_problems),))
        if receipt.get("validation_policy_version") != VALIDATION_POLICY:
            if receipt.get("validation_policy_version") in COMPATIBLE_POLICIES:
                detail["why"] = "receipt under compatible policy %s; revalidation required" % receipt.get("validation_policy_version")
                detail["receipt"] = receipt
                detail["hashes"] = hashes
                return REVALIDATE, detail
            return INVALID_POLICY_VERSION, OrderedDict((("why", "receipt policy %r is incompatible with %s"
                                                          % (receipt.get("validation_policy_version"), VALIDATION_POLICY)),))
        revoked = revocations if revocations is not None else FL.load_revocations()
        moment = now or _now()
        for ref in receipt.get("evidence") or ():
            if str(ref.get("artifact_sha256")) in revoked:
                return INVALID_REVOKED, OrderedDict((("why", "evidence artifact %s is revoked" % str(ref.get("artifact_sha256"))[:23]),))
        expiry = receipt.get("earliest_evidence_expiry")
        if expiry and FPB.parse_timestamp(expiry) and FPB.parse_timestamp(expiry).replace(tzinfo=timezone.utc) < moment:
            return INVALID_REVOKED, OrderedDict((("why", "evidence expired at %s" % expiry),))
        if entry.get("revocation_state") not in (None, "", "NONE"):
            return INVALID_REVOKED, OrderedDict((("why", "entry revoked: %s" % entry.get("revocation_state")),))
        detail["bundle_sha256"] = actual
        detail["file_count"] = len(hashes)
        detail["receipt_digest"] = entry.get("validation_receipt_digest")
        detail["lookup_seconds"] = round(time.perf_counter() - started, 3)
        return HIT, detail

    def _quarantine(self, key: str, why: str) -> None:
        path = self.index_path(key)
        target = self.root / "quarantine" / ("%s-%s.json" % (_now().strftime("%Y%m%dT%H%M%S"), key.split(":", 1)[-1][:16]))
        try:
            if path.is_file():
                doc = path.read_text(encoding="utf-8-sig")
                target.write_text(json.dumps(OrderedDict((("why", why), ("quarantined_at", _iso(_now())),
                                                          ("index_row", doc))), indent=1), encoding="utf-8")
                path.unlink()
            else:
                target.write_text(json.dumps(OrderedDict((("why", why), ("quarantined_at", _iso(_now()))))), encoding="utf-8")
        except OSError:
            pass

    # ---- locks ------------------------------------------------------------- #
    @contextmanager
    def _key_lock(self, key: str, *, timeout: float = 900.0) -> Iterator[bool]:
        """Per-key lock across threads and processes. Yields True when the
        caller had to wait for another holder."""
        with self._guard:
            tlock = self._thread_locks.setdefault(key, threading.Lock())
        waited = not tlock.acquire(blocking=False)
        if waited:
            tlock.acquire()
        path = self.lock_path(key)
        started = time.monotonic()
        fd = None
        try:
            while True:
                try:
                    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(fd, ("%s %s %s" % (os.getpid(), self.run_id, _iso(_now()))).encode("utf-8"))
                    break
                except FileExistsError:
                    waited = True
                    if path.is_file() and time.time() - path.stat().st_mtime > timeout:
                        try:
                            path.unlink()                    # a holder that died: break the lock
                        except OSError:
                            pass
                        continue
                    if time.monotonic() - started > timeout:
                        raise BundleCacheError("timed out waiting for the build lock on %s" % key[:23])
                    time.sleep(0.2)
            yield waited
        finally:
            if fd is not None:
                os.close(fd)
                try:
                    path.unlink()
                except OSError:
                    pass
            tlock.release()

    # ---- the request ------------------------------------------------------- #
    def build_or_reuse(self, package: Mapping, *, work_dir: Path, context: str = "production",
                       cold_required: bool = False, require_determinism: bool = True,
                       revocations: Optional[Mapping[str, Mapping]] = None,
                       now: Optional[datetime] = None,
                       builder: Optional[Callable[..., Mapping]] = None) -> "OrderedDict[str, Any]":
        """The ONE request path. Returns a result naming the status, the
        bundle digest, the output directory and every measured second."""
        started = time.perf_counter()
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        market_id = str(package["market_id"])
        t = time.perf_counter()
        manifest, key, staged = self.manifest_for(package, work, context=context)
        manifest_seconds = round(time.perf_counter() - t, 3)
        output = work / "out"
        result: "OrderedDict[str, Any]" = OrderedDict((
            ("market_id", market_id), ("package_id", package["package_id"]), ("build_input_key", key),
            ("manifest_seconds", manifest_seconds), ("output_dir", str(output)),
        ))
        if cold_required:
            self._event(BYPASS_COLD_REQUIRED, market_id, key)
            built = self._build_and_publish(package, manifest, key, work, output, context, require_determinism,
                                            revocations, now, builder)
            result.update(built)
            result["cache_status"] = BYPASS_COLD_REQUIRED
            result["total_seconds"] = round(time.perf_counter() - started, 3)
            return result

        t = time.perf_counter()
        entry = self.read_entry(key)
        status, detail = (MISS, OrderedDict()) if entry is None else self.verify(key, entry, output,
                                                                                 revocations=revocations, now=now)
        lookup_seconds = round(time.perf_counter() - t, 3)
        if status == HIT:
            self._event(HIT, market_id, key, lookup_seconds=lookup_seconds, verify_seconds=detail.get("verify_seconds"),
                        bytes=entry.get("byte_size"), output_digest=detail["bundle_sha256"])
            result.update(OrderedDict((("cache_status", HIT), ("bundle_sha256", detail["bundle_sha256"]),
                                       ("file_count", detail["file_count"]), ("receipt_digest", detail["receipt_digest"]),
                                       ("lookup_seconds", lookup_seconds), ("verify_seconds", detail.get("verify_seconds")),
                                       ("build_seconds", 0.0), ("builder_invocations", 0),
                                       ("bytes_reused", entry.get("byte_size")))))
            result["total_seconds"] = round(time.perf_counter() - started, 3)
            return result
        if status == REVALIDATE:
            revalidated = self._revalidate(package, manifest, key, entry, detail, output, revocations, now)
            result.update(revalidated)
            result["lookup_seconds"] = lookup_seconds
            result["total_seconds"] = round(time.perf_counter() - started, 3)
            return result
        if status != MISS:
            self._event(status, market_id, key, why=detail.get("why"))
        with self._key_lock(key) as waited:
            if waited:
                entry = self.read_entry(key)
                if entry is not None:
                    status2, detail2 = self.verify(key, entry, output, revocations=revocations, now=now)
                    if status2 == HIT:
                        self._event(HIT_AFTER_WAIT, market_id, key, lookup_seconds=lookup_seconds,
                                    output_digest=detail2["bundle_sha256"])
                        result.update(OrderedDict((("cache_status", HIT_AFTER_WAIT),
                                                   ("bundle_sha256", detail2["bundle_sha256"]),
                                                   ("file_count", detail2["file_count"]),
                                                   ("receipt_digest", detail2["receipt_digest"]),
                                                   ("build_seconds", 0.0), ("builder_invocations", 0),
                                                   ("bytes_reused", entry.get("byte_size")))))
                        result["total_seconds"] = round(time.perf_counter() - started, 3)
                        return result
            built = self._build_and_publish(package, manifest, key, work, output, context, require_determinism,
                                            revocations, now, builder)
        result.update(built)
        result["cache_status"] = MISS if status == MISS else status
        result["lookup_seconds"] = lookup_seconds
        result["total_seconds"] = round(time.perf_counter() - started, 3)
        return result

    # ---- build + publish --------------------------------------------------- #
    def _build_and_publish(self, package, manifest, key, work, output, context, require_determinism,
                           revocations, now, builder) -> "OrderedDict[str, Any]":
        if os.environ.get(FORBID_BUILD_ENV, "").strip() == "1":
            self._event(BUILD_FORBIDDEN, str(package["market_id"]), key)
            raise BuildForbidden("a build of %s was required but %s=1 forbids it" % (package["market_id"], FORBID_BUILD_ENV))
        build = builder or STAGING.build_changed_market
        market_id = str(package["market_id"])
        t = time.perf_counter()
        tracer = _ReadTracer(self.repo_root, ignore=[work, self.root])
        # The 002 session cache fingerprints the whole tree before every
        # decision; those reads are ITS closure, not the build's. Take the
        # fingerprint once, untraced, and hand the session cache that value
        # while the build is traced.
        from scripts.pettripfinder import assembly_session_cache as ASC
        original_fingerprint = ASC.input_fingerprint
        if builder is None:
            fingerprint = ASC.input_fingerprint()
            ASC.input_fingerprint = lambda: fingerprint
        try:
            with tracer:
                first = build(package, work / "sa", output, context=context, cold=True, repo_root=self.repo_root)
        finally:
            ASC.input_fingerprint = original_fingerprint
        build_seconds = round(time.perf_counter() - t, 3)
        undeclared = undeclared_dependencies(tracer, self.closure, market_id)
        determinism: "OrderedDict[str, Any]" = OrderedDict((("required", bool(require_determinism)),))
        builder_invocations = 1
        if require_determinism:
            t2 = time.perf_counter()
            second = build(package, work / "sb", work / "ob", context=context, cold=True, repo_root=self.repo_root)
            builder_invocations = 2
            determinism.update(OrderedDict((("output_digest_a", first["bundle_sha256"]),
                                            ("output_digest_b", second["bundle_sha256"]),
                                            ("result", "BYTE_IDENTICAL" if first["bundle_sha256"] == second["bundle_sha256"] else "DIFFERENT"),
                                            ("seconds", round(time.perf_counter() - t2, 3)))))
        t3 = time.perf_counter()
        published = self._publish(package, manifest, key, first, output, undeclared, determinism, revocations, now)
        publish_seconds = round(time.perf_counter() - t3, 3)
        self._event(MISS if published["trust_state"] == TRUSTED else UNTRUSTED, market_id, key,
                    build_seconds=build_seconds, validation_seconds=publish_seconds, bytes=published.get("byte_size"),
                    output_digest=first["bundle_sha256"], trust_state=published["trust_state"],
                    untrusted_because=published.get("untrusted_because"))
        return OrderedDict((("bundle_sha256", first["bundle_sha256"]), ("file_count", first["file_count"]),
                            ("build_seconds", build_seconds), ("builder_invocations", builder_invocations),
                            ("determinism", determinism), ("undeclared_dependencies", undeclared),
                            ("publish_seconds", publish_seconds), ("trust_state", published["trust_state"]),
                            ("untrusted_because", published.get("untrusted_because")),
                            ("receipt_digest", published.get("receipt_digest")),
                            ("gates_failing", list(first.get("gates_failing") or []))))

    def _validation(self, package, manifest, key, built, undeclared, determinism, revocations, now
                    ) -> Tuple["OrderedDict[str, Any]", List[str]]:
        problems: List[str] = []
        if built.get("gates_failing"):
            problems.append("assembler gates failing: %s" % list(built["gates_failing"])[:5])
        cold = [e for e in built.get("cache_events") or () if e.get("assembly_kind") == "market_bundle"]
        if cold and any(e.get("verdict") != "BUILD_EXECUTED" for e in cold):
            problems.append("the bundle was not built cold")
        if undeclared["data"] or undeclared["code"]:
            problems.append("undeclared dependencies read during the build: data %s code %s"
                            % (undeclared["data"][:5], undeclared["code"][:5]))
        if determinism.get("required") and determinism.get("result") != "BYTE_IDENTICAL":
            problems.append("determinism %s" % determinism.get("result", "UNKNOWN"))
        revoked = revocations if revocations is not None else FL.load_revocations()
        evidence = [OrderedDict((("evidence_ref", r["evidence_ref"]), ("artifact_sha256", r["artifact_sha256"]),
                                 ("captured_at", r.get("captured_at"))))
                    for r in package.get("evidence_references") or ()]
        for ref in evidence:
            if str(ref["artifact_sha256"]) in revoked:
                problems.append("evidence %s is revoked" % ref["evidence_ref"])
        moment = now or _now()
        earliest = None
        for ref in evidence:
            captured = FPB.parse_timestamp(str(ref.get("captured_at") or ""))
            if captured is None:
                problems.append("evidence %s has no parseable captured_at" % ref["evidence_ref"])
                continue
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=timezone.utc)
            expiry = captured + timedelta(days=FL.EVIDENCE_MAX_AGE_DAYS)
            if expiry < moment:
                problems.append("evidence %s expired %s" % (ref["evidence_ref"], _iso(expiry)))
            earliest = expiry if earliest is None or expiry < earliest else earliest
        commit = _git_head(self.repo_root)
        receipt: "OrderedDict[str, Any]" = OrderedDict((
            ("schema", RECEIPT_SCHEMA),
            ("build_input_key", key),
            ("market_id", str(package["market_id"])),
            ("package_id", package["package_id"]),
            ("package_digest", package["package_digest"]),
            ("output_bundle_digest", "sha256:" + built["bundle_sha256"]),
            ("output_file_count", built["file_count"]),
            ("validation_policy_version", VALIDATION_POLICY),
            ("fast_lane_version", FL.LANE_VERSION),
            ("dependency", _dependency_block(manifest)),
            ("results", OrderedDict((
                ("assembler_gates", "PASS" if not built.get("gates_failing") else "FAIL"),
                ("cold_build", "PASS" if cold and all(e.get("verdict") == "BUILD_EXECUTED" for e in cold) else "UNKNOWN"),
                ("undeclared_dependencies", undeclared),
                ("determinism", determinism),
                ("evidence_revocation", "PASS" if not any("revoked" in p for p in problems) else "FAIL"),
                ("evidence_freshness", "PASS" if not any("expired" in p or "captured_at" in p for p in problems) else "FAIL"),
            ))),
            ("evidence", evidence),
            ("earliest_evidence_expiry", _iso(earliest) if earliest else None),
            ("reference_date", moment.date().isoformat()),
            ("problems", problems),
            ("trust_state", TRUSTED if not problems else UNTRUSTED),
            ("created_at", _iso(moment)),
            ("created_by", OrderedDict((("run_id", self.run_id), ("commit", commit),
                                        ("publisher", "scripts.pettripfinder.bundle_cache.BundleCache")))),
        ))
        receipt["receipt_digest"] = receipt_digest_of(receipt)
        return receipt, problems

    def _publish(self, package, manifest, key, built, output, undeclared, determinism, revocations, now
                 ) -> "OrderedDict[str, Any]":
        """Atomic: archive to tmp, verify, receipt to tmp, then rename the
        archive, the receipt and LAST the index row."""
        site_dir = Path(output) / "site"
        tmp = self.root / "tmp" / ("%s-%s" % (uuid.uuid4().hex[:12], key.split(":", 1)[-1][:12]))
        tmp.mkdir(parents=True)
        archive_tmp = tmp / "bundle.zip"
        archive_meta = write_archive(site_dir, archive_tmp)
        if archive_meta["bundle_sha256"] != built["bundle_sha256"]:
            shutil.rmtree(tmp, ignore_errors=True)
            raise BundleCacheError("archived bytes hash to %s, the build reported %s"
                                   % (archive_meta["bundle_sha256"][:16], built["bundle_sha256"][:16]))
        # Prove the archive round-trips before anything becomes visible.
        check = extract_archive(archive_tmp, tmp / "check")
        from scripts.pettripfinder.assemble_production_site import bundle_digest
        if bundle_digest(check) != built["bundle_sha256"]:
            shutil.rmtree(tmp, ignore_errors=True)
            raise BundleCacheError("archive does not round-trip to the built bytes")
        shutil.rmtree(tmp / "check", ignore_errors=True)
        receipt, problems = self._validation(package, manifest, key, built, undeclared, determinism, revocations, now)
        receipt_tmp = tmp / "receipt.json"
        receipt_tmp.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
        entry: "OrderedDict[str, Any]" = OrderedDict((
            ("schema", ENTRY_SCHEMA),
            ("build_input_key", key),
            ("market_id", str(package["market_id"])),
            ("package_id", package["package_id"]),
            ("package_digest", package["package_digest"]),
            ("output_bundle_digest", "sha256:" + built["bundle_sha256"]),
            ("output_path", "objects/%s.zip" % built["bundle_sha256"]),
            ("archive_sha256", archive_meta["archive_sha256"]),
            ("archive_bytes", archive_meta["archive_bytes"]),
            ("byte_size", archive_meta["byte_size"]),
            ("file_count", archive_meta["file_count"]),
            ("validation_receipt_digest", receipt["receipt_digest"]),
            ("validation_policy_version", VALIDATION_POLICY),
            ("dependency", _dependency_block(manifest)),
            ("created_at", receipt["created_at"]),
            ("created_by", receipt["created_by"]),
            ("trust_state", receipt["trust_state"]),
            ("untrusted_because", problems),
            ("last_verified", receipt["created_at"]),
            ("revocation_state", "NONE"),
            ("expiry", receipt["earliest_evidence_expiry"]),
            ("manifest", manifest),
        ))
        entry_tmp = tmp / "entry.json"
        entry_tmp.write_text(json.dumps(entry, indent=1) + "\n", encoding="utf-8")
        # Publication order: bytes (never overwritten), receipt, index row.
        archive_final = self.object_path(built["bundle_sha256"])
        if not archive_final.exists():
            os.replace(str(archive_tmp), str(archive_final))
        elif _sha_file(archive_final) != archive_meta["archive_sha256"]:
            # Same content digest, different archive bytes. A deterministic
            # archive of identical files cannot differ, so the existing file is
            # damaged (a corrupted or partial object): move it aside and
            # publish the freshly verified one. Never overwrite in place.
            damaged = self.root / "quarantine" / ("%s-object-%s.zip" % (_now().strftime("%Y%m%dT%H%M%S"),
                                                                         built["bundle_sha256"][:16]))
            try:
                os.replace(str(archive_final), str(damaged))
            except OSError:
                pass
            os.replace(str(archive_tmp), str(archive_final))
        receipt_final = self.receipt_path(receipt["receipt_digest"])
        if not receipt_final.exists():
            os.replace(str(receipt_tmp), str(receipt_final))
        os.replace(str(entry_tmp), str(self.index_path(key)))
        shutil.rmtree(tmp, ignore_errors=True)
        return OrderedDict((("trust_state", entry["trust_state"]), ("untrusted_because", problems),
                            ("receipt_digest", receipt["receipt_digest"]), ("byte_size", entry["byte_size"])))

    def _revalidate(self, package, manifest, key, entry, detail, output, revocations, now) -> "OrderedDict[str, Any]":
        """Bytes proven identical and the old receipt under a compatible
        policy: issue a new receipt WITHOUT rebuilding. Determinism is
        inherited from the old receipt when it was proven there."""
        old = detail["receipt"]
        built = OrderedDict((("bundle_sha256", str(entry["output_bundle_digest"]).split(":", 1)[-1]),
                             ("file_count", entry["file_count"]), ("gates_failing", []),
                             ("cache_events", [OrderedDict((("verdict", "BUILD_EXECUTED"), ("assembly_kind", "market_bundle")))])))
        undeclared = (old.get("results") or {}).get("undeclared_dependencies") or OrderedDict((("data", []), ("code", [])))
        determinism = (old.get("results") or {}).get("determinism") or OrderedDict((("required", True), ("result", "UNKNOWN")))
        t = time.perf_counter()
        receipt, problems = self._validation(package, manifest, key, built, undeclared, determinism, revocations, now)
        receipt["revalidated_from"] = old.get("receipt_digest")
        receipt["receipt_digest"] = receipt_digest_of(receipt)
        receipt_final = self.receipt_path(receipt["receipt_digest"])
        receipt_final.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
        new_entry = OrderedDict(entry)
        new_entry["validation_receipt_digest"] = receipt["receipt_digest"]
        new_entry["validation_policy_version"] = VALIDATION_POLICY
        new_entry["trust_state"] = receipt["trust_state"]
        new_entry["untrusted_because"] = problems
        new_entry["last_verified"] = receipt["created_at"]
        tmp = self.root / "tmp" / ("reval-%s.json" % uuid.uuid4().hex[:12])
        tmp.write_text(json.dumps(new_entry, indent=1) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(self.index_path(key)))
        seconds = round(time.perf_counter() - t, 3)
        self._event(REVALIDATE, str(package["market_id"]), key, validation_seconds=seconds,
                    output_digest=built["bundle_sha256"], trust_state=receipt["trust_state"])
        return OrderedDict((("cache_status", REVALIDATE), ("bundle_sha256", built["bundle_sha256"]),
                            ("file_count", built["file_count"]), ("build_seconds", 0.0), ("builder_invocations", 0),
                            ("revalidation_seconds", seconds), ("receipt_digest", receipt["receipt_digest"]),
                            ("trust_state", receipt["trust_state"]), ("untrusted_because", problems),
                            ("bytes_reused", entry.get("byte_size"))))

    # ---- inventory / retention -------------------------------------------- #
    def entries(self) -> List["OrderedDict[str, Any]"]:
        out = []
        for path in sorted((self.root / "index").glob("*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
            except ValueError:
                continue
            if isinstance(doc, Mapping) and doc.get("schema") == ENTRY_SCHEMA:
                out.append(doc)
        return out

    def revoke(self, key: str, reason: str) -> bool:
        entry = self.read_entry(key)
        if entry is None:
            return False
        entry["revocation_state"] = reason
        entry["trust_state"] = REVOKED
        tmp = self.root / "tmp" / ("revoke-%s.json" % uuid.uuid4().hex[:12])
        tmp.write_text(json.dumps(entry, indent=1) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(self.index_path(key)))
        return True

    def gc_plan(self, *, max_age_days: int = 90, max_bytes: int = 20 << 30,
                protected_digests: Sequence[str] = (), now: Optional[datetime] = None) -> "OrderedDict[str, Any]":
        """Retention DRY RUN: what a collector would remove and why. Nothing
        is deleted here. A protected digest (the live or rollback release's
        bundles, anything a committed receipt names) is never a candidate;
        the build cache is never the only copy of a release."""
        moment = now or _now()
        protected = {d.split(":", 1)[-1] for d in protected_digests}
        rows = []
        total = 0
        for entry in self.entries():
            digest = str(entry.get("output_bundle_digest") or "").split(":", 1)[-1]
            created = FPB.parse_timestamp(str(entry.get("created_at") or ""))
            age_days = (moment - created.replace(tzinfo=timezone.utc)).days if created else None
            size = int(entry.get("archive_bytes") or 0)
            total += size
            reasons = []
            if digest in protected:
                reasons.append("PROTECTED")
            elif entry.get("trust_state") in (QUARANTINED, REVOKED, UNTRUSTED):
                reasons.append("UNTRUSTED_STATE:%s" % entry.get("trust_state"))
            elif age_days is not None and age_days > max_age_days:
                reasons.append("OLDER_THAN_%d_DAYS" % max_age_days)
            rows.append(OrderedDict((("build_input_key", entry.get("build_input_key")), ("market_id", entry.get("market_id")),
                                     ("digest", digest), ("archive_bytes", size), ("age_days", age_days),
                                     ("trust_state", entry.get("trust_state")),
                                     ("candidate", bool(reasons) and "PROTECTED" not in reasons), ("reasons", reasons))))
        over = max(0, total - max_bytes)
        if over:
            for row in sorted((r for r in rows if not r["candidate"] and "PROTECTED" not in r["reasons"]),
                              key=lambda r: (r["age_days"] or 0), reverse=True):
                if over <= 0:
                    break
                row["candidate"] = True
                row["reasons"].append("OVER_SIZE_BUDGET")
                over -= row["archive_bytes"]
        return OrderedDict((("dry_run", True), ("policy", OrderedDict((("max_age_days", max_age_days), ("max_bytes", max_bytes)))),
                            ("entries", len(rows)), ("total_archive_bytes", total),
                            ("candidates", [r for r in rows if r["candidate"]]), ("protected", [r for r in rows if "PROTECTED" in r["reasons"]]),
                            ("rows", rows)))


def _git_head(repo_root: Path) -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root), capture_output=True,
                              check=True).stdout.decode().strip()
    except Exception:
        return "unknown"


def _dependency_block(manifest: Mapping) -> "OrderedDict[str, Any]":
    return OrderedDict((k, manifest[k]) for k in (
        "builder_digest", "assembler_digest", "shared_runtime_dependency_digest", "template_digest",
        "asset_digest", "shared_data_digest", "declared_closure_digest", "render_input_digest",
        "contract_versions", "builder_version") if k in manifest) | OrderedDict((
            ("python_version", manifest["toolchain"]["python_version"]),
            ("lockfiles", manifest["toolchain"]["lockfiles"]),
        ))


def receipt_digest_of(receipt: Mapping) -> str:
    body = OrderedDict((k, v) for k, v in receipt.items() if k != "receipt_digest")
    return SMP.sha256_text(SMP.canonical_json(body))


def receipt_binding_problems(receipt: Mapping, *, key: str, bundle_sha256: str,
                             manifest_dependencies: Mapping) -> List[str]:
    problems = []
    if receipt.get("build_input_key") != key:
        problems.append("receipt binds input key %s, entry is %s" % (str(receipt.get("build_input_key"))[:23], key[:23]))
    if str(receipt.get("output_bundle_digest") or "") != bundle_sha256:
        problems.append("receipt binds bundle %s, entry is %s" % (str(receipt.get("output_bundle_digest"))[:23], bundle_sha256[:23]))
    if receipt.get("trust_state") != TRUSTED:
        problems.append("receipt is %s: %s" % (receipt.get("trust_state"), (receipt.get("problems") or [])[:2]))
    dep = receipt.get("dependency") or {}
    for field in ("builder_digest", "assembler_digest", "shared_runtime_dependency_digest", "render_input_digest",
                  "declared_closure_digest", "python_version"):
        if dep.get(field) != (manifest_dependencies or {}).get(field):
            problems.append("receipt dependency %s differs from the entry's" % field)
    return problems


def summary() -> "OrderedDict[str, Any]":
    counts: "OrderedDict[str, int]" = OrderedDict()
    for e in EVENTS:
        counts[e["cache_status"]] = counts.get(e["cache_status"], 0) + 1
    return OrderedDict((("events", len(EVENTS)), ("by_status", counts),
                        ("build_seconds", round(sum(float(e.get("build_seconds") or 0) for e in EVENTS), 3)),
                        ("bytes_reused", sum(int(e.get("bytes") or 0) for e in EVENTS
                                             if e["cache_status"] in (HIT, HIT_AFTER_WAIT)))))


__all__ = [
    "MANIFEST_SCHEMA", "ENTRY_SCHEMA", "RECEIPT_SCHEMA", "CLOSURE_SCHEMA", "VALIDATION_POLICY",
    "COMPATIBLE_POLICIES", "KEY_FIELDS", "MISS", "HIT", "HIT_AFTER_WAIT", "REVALIDATE", "INVALID_CORRUPT",
    "INVALID_REVOKED", "INVALID_POLICY_VERSION", "BYPASS_COLD_REQUIRED", "BUILD_FORBIDDEN", "TRUSTED",
    "UNTRUSTED", "QUARANTINED", "REVOKED", "EVENTS", "BundleCacheError", "BuildForbidden", "load_closure",
    "closure_digest", "toolchain_identity", "build_input_manifest", "build_input_key", "write_archive",
    "extract_archive", "undeclared_dependencies", "BundleCache", "receipt_digest_of",
    "receipt_binding_problems", "summary", "DEFAULT_ROOT", "ROOT_ENV", "FORBID_BUILD_ENV",
]
