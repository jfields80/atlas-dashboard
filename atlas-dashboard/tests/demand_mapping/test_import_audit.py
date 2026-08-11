"""AST-based import audit for the Demand Mapping core (AES-SEO-001 §3.3).

Walks the AST of every module under ``engines/demand_mapping/`` and asserts
the import law: stdlib (minus the banned modules) + pydantic + itself only.
Cloned from the WGE audit (``tests/website_generation/architecture/
test_import_audit.py``) per AES-SEO-001 Appendix A.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "engines" / "demand_mapping"

_STDLIB: Set[str] = set(getattr(sys, "stdlib_module_names", ())) | {
    "typing", "abc", "enum", "json", "hashlib", "re",
    "collections", "functools", "itertools", "__future__",
}

# Modules forbidden anywhere inside the deterministic core (§3.3): no
# Flask, no network, no AI clients, no UUIDs, no randomness, no clock,
# no logging side channels.
_FORBIDDEN: Set[str] = {
    "flask", "requests", "urllib", "urllib3", "http", "httpx", "socket",
    "anthropic", "openai", "uuid", "random", "secrets", "time",
    "datetime", "logging",
}

_ALLOWED_THIRD_PARTY: Set[str] = {"pydantic"}
_OWN_PACKAGE_PREFIX = "engines.demand_mapping"


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


def _all_imports() -> Dict[Path, List[str]]:
    modules = list(_iter_modules(PACKAGE_ROOT))
    assert modules, "engines/demand_mapping is missing or empty"
    return {path: _imports_of(path) for path in modules}


class TestFlatImportDoctrine:
    def test_no_relative_imports(self):
        for path, imports in _all_imports().items():
            assert "<relative>" not in imports, (
                "relative import found in %s" % path
            )


class TestForbiddenDependencies:
    def test_no_forbidden_modules(self):
        for path, imports in _all_imports().items():
            offenders = {_top(name) for name in imports} & _FORBIDDEN
            assert not offenders, "%s imports forbidden %s" % (
                path, sorted(offenders)
            )

    def test_never_imports_services_repositories_routes(self):
        for path, imports in _all_imports().items():
            tops = {_top(name) for name in imports}
            for layer in ("services", "repositories", "routes"):
                assert layer not in tops, "%s imports %s" % (path, layer)

    def test_never_imports_other_engine_packages(self):
        for path, imports in _all_imports().items():
            for name in imports:
                if _top(name) == "engines":
                    assert (
                        name == "engines"
                        or name.startswith(_OWN_PACKAGE_PREFIX)
                    ), (
                        "%s imports foreign engine package %s (§3.7 — the "
                        "WGE and every other engine are off-limits)"
                        % (path, name)
                    )


class TestImportMatrix:
    def test_only_stdlib_pydantic_and_self(self):
        for path, imports in _all_imports().items():
            for name in imports:
                top = _top(name)
                allowed = (
                    top in _STDLIB
                    or top in _ALLOWED_THIRD_PARTY
                    or name == "engines"
                    or name.startswith(_OWN_PACKAGE_PREFIX)
                )
                assert allowed, "%s imports %s outside the §3.3 matrix" % (
                    path, name
                )
