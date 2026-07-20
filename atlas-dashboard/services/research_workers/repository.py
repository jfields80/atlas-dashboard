"""ATLAS-WORKERS-001 -- research inbox (Stage 4).

A deterministic, safe result store confined to ONE gitignored runtime root
(data/worker_runs/pettripfinder/). Atomic writes (same-directory tempfile +
os.replace, the repository's established idiom), UTF-8, LF, sorted keys,
deterministic filenames, and hard path-traversal rejection. The repository can
only write under its own root -- never launch_packages, never production
inventory, never anywhere else.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, WorkerResult, pretty_json,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKER_ROOT = _REPO_ROOT / "data" / "worker_runs" / "pettripfinder"

# Never writable by this repository, defensively (the worker owns none of these).
_FORBIDDEN_ANCESTORS = (_REPO_ROOT / "launch_packages", _REPO_ROOT / "scripts",
                        _REPO_ROOT / "engines", _REPO_ROOT / "services")

ASSIGNMENTS = "assignments"
RESULTS = "results"
REJECTED = "rejected"
BENCHMARK_REPORTS = "benchmark_reports"
_SUBDIRS = (ASSIGNMENTS, RESULTS, REJECTED, BENCHMARK_REPORTS)

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")

# A worker result goes to rejected/ when it produced nothing usable.
_REJECTED_STATUSES = frozenset({V.STATUS_FAILED, V.STATUS_NO_OFFICIAL_SOURCE})


class RepositoryError(RuntimeError):
    pass


class WorkerRepository:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root).resolve() if root else DEFAULT_WORKER_ROOT.resolve()
        for anc in _FORBIDDEN_ANCESTORS:
            try:
                if self.root == anc.resolve() or anc.resolve() in self.root.parents:
                    raise RepositoryError("worker root may not live under %s" % anc)
            except FileNotFoundError:
                pass

    # -- path safety ------------------------------------------------------- #
    def _safe_file(self, subdir: str, filename: str) -> Path:
        if subdir not in _SUBDIRS:
            raise RepositoryError("unknown subdir: %r" % subdir)
        if not _SAFE_NAME.match(filename or "") or ".." in filename or "/" in filename or "\\" in filename:
            raise RepositoryError("unsafe filename: %r" % filename)
        target = (self.root / subdir / filename).resolve()
        base = (self.root / subdir).resolve()
        if base != target.parent:
            raise RepositoryError("path escapes worker root: %r" % filename)
        if base != self.root / subdir:
            raise RepositoryError("subdir escapes worker root")
        # Final belt-and-braces: target must be inside the worker root.
        if self.root != target.parents[1] and self.root not in target.parents:
            raise RepositoryError("resolved path escapes worker root: %s" % target)
        return target

    def _atomic_write(self, path: Path, payload: Dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = pretty_json(payload)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return path

    # -- writes ------------------------------------------------------------ #
    def write_assignment(self, assignment: Assignment) -> Path:
        assignment.validate()
        return self._atomic_write(
            self._safe_file(ASSIGNMENTS, assignment.assignment_id + ".json"),
            assignment.to_dict())

    def write_result(self, result: WorkerResult) -> Path:
        subdir = REJECTED if result.status in _REJECTED_STATUSES else RESULTS
        return self._atomic_write(
            self._safe_file(subdir, result.assignment_id + ".json"),
            result.to_dict())

    def write_benchmark_report(self, name: str, payload: Dict) -> Path:
        return self._atomic_write(self._safe_file(BENCHMARK_REPORTS, name + ".json"), payload)

    # -- reads ------------------------------------------------------------- #
    def read_result(self, path: Path) -> WorkerResult:
        return WorkerResult.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
