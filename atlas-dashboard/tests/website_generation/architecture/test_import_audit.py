"""AST-based import audit for the WGE (AES-WEB-001 §3.2-§3.3).

Walks the AST of every module under ``engines/website_generation/`` and
the two new repositories, asserting the dependency matrix:

* contracts import only stdlib + pydantic (the embedded pydantic_compat
  isolation, documented in ``contracts/artifacts.py``) + intra-contracts;
* constants import stdlib only;
* engines never import repositories or services;
* repositories import contracts + storage drivers only;
* pipeline is the only engine-layer composition point;
* no Flask, AI clients, network libraries, UUID, randomness, or
  wall-clock modules anywhere in engine code;
* flat imports only, per Atlas doctrine;
* the new package never imports the legacy engines/website_generator or
  engines/website_intelligence packages.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "engines" / "website_generation"

_STDLIB: Set[str] = set(getattr(sys, "stdlib_module_names", ())) | {
    "typing", "abc", "enum", "json", "hashlib", "os", "pathlib",
    "sqlite3", "tempfile", "collections", "functools", "itertools",
}

# Modules forbidden anywhere inside engine code (§3.2 plus the Atlas
# purity invariants: no AI, no network, no UUIDs, no clock, no
# randomness, no Flask, no logging/printing side channels).
_FORBIDDEN_IN_ENGINES: Set[str] = {
    "flask", "requests", "urllib", "urllib3", "http", "httpx", "socket",
    "anthropic", "openai", "uuid", "random", "secrets", "time",
    "datetime", "logging",
}

_LEGACY_PACKAGES: Tuple[str, ...] = (
    "engines.website_generator",
    "engines.website_intelligence",
)


def _iter_modules(root: Path) -> Iterator[Path]:
    yield from sorted(root.rglob("*.py"))


def _imports_of(path: Path) -> List[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                names.append("<relative>")
            elif node.module:
                names.append(node.module)
    return names


def _top(name: str) -> str:
    return name.split(".")[0]


def _wge_subpackage(name: str) -> str:
    # engines.website_generation.<sub>... -> <sub>
    parts = name.split(".")
    if parts[:2] == ["engines", "website_generation"] and len(parts) > 2:
        return parts[2]
    return ""


def _all_engine_imports() -> Dict[Path, List[str]]:
    return {path: _imports_of(path) for path in _iter_modules(PACKAGE_ROOT)}


class TestFlatImportDoctrine:
    def test_no_relative_imports(self):
        for path, imports in _all_engine_imports().items():
            assert "<relative>" not in imports, (
                "relative import found in %s" % path
            )


class TestForbiddenDependencies:
    def test_no_forbidden_modules_in_engine_code(self):
        for path, imports in _all_engine_imports().items():
            tops = {_top(name) for name in imports}
            offenders = tops & _FORBIDDEN_IN_ENGINES
            assert not offenders, "%s imports forbidden %s" % (
                path,
                sorted(offenders),
            )

    def test_engines_never_import_repositories_or_services(self):
        for path, imports in _all_engine_imports().items():
            tops = {_top(name) for name in imports}
            assert "repositories" not in tops, str(path)
            assert "services" not in tops, str(path)
            assert "routes" not in tops, str(path)

    def test_new_package_never_imports_legacy_engines(self):
        for path, imports in _all_engine_imports().items():
            for name in imports:
                for legacy in _LEGACY_PACKAGES:
                    assert not name.startswith(legacy), (
                        "%s imports legacy package %s" % (path, legacy)
                    )


class TestPackageMatrix:
    def test_contracts_import_stdlib_and_pydantic_only(self):
        contracts_dir = PACKAGE_ROOT / "contracts"
        for path in _iter_modules(contracts_dir):
            for name in _imports_of(path):
                top = _top(name)
                if top in _STDLIB:
                    continue
                if top == "pydantic":
                    # Embedded pydantic_compat isolation (documented in
                    # contracts/artifacts.py per the §3.1 matrix).
                    continue
                if name.startswith("engines.website_generation.contracts"):
                    continue
                raise AssertionError(
                    "%s has out-of-matrix import %r" % (path, name)
                )

    def test_constants_import_stdlib_only(self):
        constants_dir = PACKAGE_ROOT / "constants"
        for path in _iter_modules(constants_dir):
            for name in _imports_of(path):
                top = _top(name)
                if top in _STDLIB:
                    continue
                if name.startswith("engines.website_generation.constants"):
                    continue
                raise AssertionError(
                    "%s has out-of-matrix import %r" % (path, name)
                )

    def test_speccompiler_imports_contracts_and_constants_only(self):
        spec_dir = PACKAGE_ROOT / "speccompiler"
        for path in _iter_modules(spec_dir):
            for name in _imports_of(path):
                top = _top(name)
                if top in _STDLIB:
                    continue
                sub = _wge_subpackage(name)
                assert sub in {"contracts", "constants", "speccompiler"}, (
                    "%s has out-of-matrix import %r" % (path, name)
                )

    def test_pipeline_is_the_only_engine_composition_point(self):
        # Only pipeline modules (and the package __init__, which exports
        # the public surface) may import sibling engine packages.
        engine_subpackages = {"speccompiler", "pipeline"}
        for path, imports in _all_engine_imports().items():
            relative = path.relative_to(PACKAGE_ROOT)
            in_pipeline = relative.parts[0] == "pipeline"
            is_public_init = relative.parts == ("__init__.py",)
            if in_pipeline or is_public_init:
                continue
            for name in imports:
                sub = _wge_subpackage(name)
                if sub in engine_subpackages and sub != relative.parts[0]:
                    raise AssertionError(
                        "%s imports sibling engine package %r — only "
                        "pipeline/ composes engines" % (path, name)
                    )


class TestRepositoryMatrix:
    REPOSITORY_FILES = (
        REPO_ROOT / "repositories" / "artifact_store_repository.py",
        REPO_ROOT / "repositories" / "build_state_repository.py",
    )

    def test_repositories_import_contracts_and_storage_only(self):
        for path in self.REPOSITORY_FILES:
            for name in _imports_of(path):
                top = _top(name)
                if top in _STDLIB:
                    continue
                if name.startswith("engines.website_generation.contracts"):
                    continue
                raise AssertionError(
                    "%s has out-of-matrix import %r" % (path, name)
                )

    def test_repositories_do_not_import_engine_implementations(self):
        for path in self.REPOSITORY_FILES:
            for name in _imports_of(path):
                sub = _wge_subpackage(name)
                assert sub in ("", "contracts"), (
                    "%s imports engine implementation %r" % (path, name)
                )
