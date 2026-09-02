"""PTF-FACTORY-THROUGHPUT-HARDENING-001 A1 -- inventory the suite's pins.

    python scripts/pettripfinder/regression_inventory.py \
        --out launch_packages/pettripfinder/reports/factory_throughput_001_test_inventory.json

Walks ``tests/pettripfinder`` and records every assertion site that pins a
count, a total, a hash or a historical founder output, then classifies each
site by what the assertion MEANS -- which is not the same as what it says.
``assert len(facts["hotels"]) == 47`` says "the package has 47 records"; in a
Pass C suite it MEANS "the 47 records Pass C applied are all still here",
and in an authority suite it means "the market currently publishes 47".

Classes
-------
    CURRENT_STATE_INVARIANT       the market / bundle as it stands NOW; must
                                  move with every legitimate growth -> read the
                                  pin (pettripfinder.market_state)
    HISTORICAL_COHORT_INVARIANT   what a closed order created; must NOT move
                                  when the package grows -> scope to the cohort
                                  (pettripfinder.epochs)
    HISTORICAL_ARTIFACT_INVARIANT a committed report / ledger / packet of a
                                  closed order; immutable by construction
    DEPLOYMENT_EPOCH_INVARIANT    a bundle sha, a route count, an authorization
                                  pin -- live, source, or consumed-historical
    GENERIC_SCHEMA_INVARIANT      a contract about record shape, independent of
                                  any market's size
    CROSS_MARKET_INVARIANT        isolation between markets

The classifier is a committed, reviewable set of rules: the module's lane and
name decide the DEFAULT class; the shape of the assertion (what it reads and
what it compares) refines it. It does not rewrite anything. Its output is the
inventory report the order asks for, and the list of modules the pin refactor
touched is asserted against it by tests/pettripfinder/test_factory_throughput_001.py.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import regression_lanes as LANES  # noqa: E402

SCHEMA = "ptf-test-pin-inventory/1.0"

CURRENT_STATE = "CURRENT_STATE_INVARIANT"
HISTORICAL_COHORT = "HISTORICAL_COHORT_INVARIANT"
HISTORICAL_ARTIFACT = "HISTORICAL_ARTIFACT_INVARIANT"
DEPLOYMENT_EPOCH = "DEPLOYMENT_EPOCH_INVARIANT"
GENERIC_SCHEMA = "GENERIC_SCHEMA_INVARIANT"
CROSS_MARKET = "CROSS_MARKET_INVARIANT"
CLASSES = (CURRENT_STATE, HISTORICAL_COHORT, HISTORICAL_ARTIFACT,
           DEPLOYMENT_EPOCH, GENERIC_SCHEMA, CROSS_MARKET)

#: Modules whose name carries a work-order number describe a CLOSED order.
_HISTORICAL_NAME = re.compile(r"_(\d{3}[a-z]?|pass_?[0-9a-z]+|recovery|"
                              r"work_browser|founder_[a-z_]+|capture_[a-z0-9_]+)"
                              r"(_[a-z0-9_]+)?\.py$")

#: Names of variables that hold a live package / registry / census.
_PACKAGE_NAMES = ("facts", "package", "pkg", "policy", "hotels", "records",
                  "census", "registry", "exclusions", "shard", "rows",
                  "partition", "part", "manifest", "doc", "counts", "items")
_HASH_LITERAL = re.compile(r"^[0-9a-f]{64}$")
_DEPLOY_WORDS = ("bundle", "sitemap", "route", "deploy", "manifest",
                 "authorization", "profile", "html_pages", "files")
_CROSS_WORDS = ("other_market", "no_other", "isolation", "untouched",
                "another_market", "leak", "cross")
_SCHEMA_WORDS = ("schema", "validate", "contract", "vocabulary", "enum",
                 "field", "shape")


def _source_of(node: ast.AST, source: str) -> str:
    try:
        return ast.get_source_segment(source, node) or ""
    except Exception:  # pragma: no cover
        return ""


def _numeric_literal(node: ast.AST) -> Optional[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) \
            and not isinstance(node.value, bool):
        return node.value
    return None


def _hash_literal(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) \
            and _HASH_LITERAL.match(node.value):
        return node.value
    return None


def _reads_package(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in _PACKAGE_NAMES:
            return True
        if isinstance(sub, ast.Attribute) and sub.attr in _PACKAGE_NAMES:
            return True
    return False


def _is_len_call(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ("len", "sum"))


def _pin_sites(path: Path) -> Iterator[Dict]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover
        return
    module_consts: Dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            value = node.value
            if _numeric_literal(value) is not None:
                module_consts[node.targets[0].id] = _numeric_literal(value)
            elif _hash_literal(value) is not None:
                module_consts[node.targets[0].id] = _hash_literal(value)
            elif isinstance(value, ast.Tuple) and len(value.elts) == 1 \
                    and _hash_literal(value.elts[0]) is not None:
                module_consts[node.targets[0].id] = _hash_literal(value.elts[0])
    enclosing: List[Tuple[str, ast.AST]] = []

    def walk(node: ast.AST, func: str) -> Iterator[Dict]:
        for child in ast.iter_child_nodes(node):
            child_func = func
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                child_func = child.name
            if isinstance(child, ast.Assert) and isinstance(child.test, ast.Compare):
                site = _classify_compare(child.test, source, child.lineno,
                                         func, module_consts)
                if site:
                    yield site
            yield from walk(child, child_func)

    yield from walk(tree, "<module>")


def _classify_compare(test: ast.Compare, source: str, lineno: int, func: str,
                      consts: Dict[str, object]) -> Optional[Dict]:
    operands = [test.left] + list(test.comparators)
    literal: Optional[object] = None
    kind = ""
    reads_package = any(_reads_package(o) for o in operands)
    has_len = any(_is_len_call(o) for o in operands)
    for o in operands:
        if _numeric_literal(o) is not None:
            literal = _numeric_literal(o); kind = "count"
        elif _hash_literal(o) is not None:
            literal = _hash_literal(o); kind = "hash"
        elif isinstance(o, ast.Name) and o.id in consts:
            literal = consts[o.id]
            kind = "hash" if isinstance(literal, str) else "count"
        elif isinstance(o, ast.Attribute) and o.attr in consts:
            literal = consts[o.attr]
            kind = "hash" if isinstance(literal, str) else "count"
    if literal is None:
        return None
    if kind == "count" and not (has_len or reads_package):
        # ``assert x == 3`` over a local scalar is not a pin.
        segment = _source_of(test, source)
        if not any(w in segment for w in ("count", "total", "expected", "EXPECTED",
                                          "published", "profiles", "routes")):
            return None
    if kind == "count" and isinstance(literal, int) and literal < 2:
        return None
    return OrderedDict((
        ("line", lineno), ("test", func), ("kind", kind),
        ("literal", literal), ("reads_package", reads_package),
        ("has_len", has_len), ("source", _source_of(test, source)[:160]),
    ))


def _module_default(rel: str, lanes: Sequence[str]) -> Tuple[str, str]:
    name = Path(rel).name
    if LANES.DEPLOYMENT_ARCHITECTURE in lanes:
        return DEPLOYMENT_EPOCH, "deployment-architecture lane"
    if rel in ("contracts/test_market_authorities.py",
               "contracts/test_market_state_pins.py",
               "test_per_market_release_contracts.py",
               "test_policy_schema_migration.py"):
        return CURRENT_STATE, "per-market contract module"
    if name.endswith("_authority.py") or name in ("test_market_isolation.py",
                                                  "test_market_ownership.py"):
        return CURRENT_STATE, "market authority module"
    if _HISTORICAL_NAME.search(name):
        return HISTORICAL_COHORT, "work-order-numbered module"
    if LANES.market_for(rel):
        return HISTORICAL_COHORT, "market-named module"
    if LANES.POLICY_SCHEMA in lanes or rel.startswith("contracts/"):
        return GENERIC_SCHEMA, "policy-schema lane"
    if LANES.ASSEMBLY in lanes:
        return CURRENT_STATE, "assembly lane"
    if rel.startswith("acquisition/") or rel.startswith("brightdata/"):
        return HISTORICAL_ARTIFACT, "acquisition order module"
    return GENERIC_SCHEMA, "unlisted module"


def _refine(site: Dict, default: str, test_name: str, rel: str) -> Tuple[str, str]:
    segment = site["source"].lower()
    name = test_name.lower()
    if any(w in name or w in segment for w in _CROSS_WORDS):
        return CROSS_MARKET, "names another market or isolation"
    if site["kind"] == "hash":
        if any(w in segment or w in name for w in _DEPLOY_WORDS):
            return DEPLOYMENT_EPOCH, "hash of a bundle / sitemap / authorization"
        if default == HISTORICAL_COHORT:
            return HISTORICAL_ARTIFACT, "hash pinned by a closed order"
        return default, "hash"
    if any(w in segment for w in ("bundle", "sitemap", "route_count", "total_profiles",
                                  "html_pages", "total_files", "deploy")):
        return DEPLOYMENT_EPOCH, "bundle / sitemap / route total"
    if default == HISTORICAL_COHORT:
        if site["reads_package"] and site["has_len"]:
            return HISTORICAL_COHORT, "whole-package count in a closed order's suite"
        if any(w in segment for w in ("report", "ledger", "packet", "manifest",
                                      "doc[", "audit", "application[", "promo",
                                      "inv[", "attended", "shadow", "run")):
            return HISTORICAL_ARTIFACT, "count read from a committed artifact"
        return HISTORICAL_COHORT, "count in a closed order's suite"
    if default == GENERIC_SCHEMA and site["reads_package"] and site["has_len"]:
        return CURRENT_STATE, "whole-package count in a generic module"
    return default, "module default"


def build(paths: Optional[Sequence[Path]] = None) -> Dict:
    paths = list(paths) if paths else sorted(LANES.PTF_TESTS.rglob("test_*.py"))
    modules: List[Dict] = []
    totals: Counter = Counter()
    for path in paths:
        rel = LANES._relpath(path)
        lanes = LANES.lanes_for(rel)
        default, why = _module_default(rel, lanes)
        sites = []
        for site in _pin_sites(path):
            cls, reason = _refine(site, default, site["test"], rel)
            site["class"] = cls
            site["reason"] = reason
            sites.append(site)
            totals[cls] += 1
        if not sites:
            continue
        by_class = Counter(s["class"] for s in sites)
        modules.append(OrderedDict((
            ("module", "tests/pettripfinder/" + rel),
            ("market", LANES.market_for(rel)),
            ("lanes", list(lanes)),
            ("default_class", default), ("default_reason", why),
            ("site_count", len(sites)),
            ("by_class", OrderedDict(sorted(by_class.items()))),
            ("sites", sites),
        )))
    whole_package = [m["module"] for m in modules
                     if any(s["reads_package"] and s["has_len"]
                            and s["class"] in (CURRENT_STATE, HISTORICAL_COHORT)
                            for s in m["sites"])]
    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is", "Every count / total / hash assertion site in "
                         "tests/pettripfinder, classified by what it means."),
        ("classes", list(CLASSES)),
        ("modules_scanned", len(paths)),
        ("modules_with_pins", len(modules)),
        ("sites", sum(totals.values())),
        ("by_class", OrderedDict((c, totals.get(c, 0)) for c in CLASSES)),
        ("modules_asserting_whole_package_counts", whole_package),
        ("modules", modules),
    ))


def markdown(doc: Dict) -> str:
    lines = ["# PetTripFinder test pin inventory (A1)", "",
             "Schema `%s`. %d modules scanned, %d carry pins, %d sites."
             % (doc["schema"], doc["modules_scanned"], doc["modules_with_pins"],
                doc["sites"]), "", "| class | sites |", "|---|---|"]
    for c, n in doc["by_class"].items():
        lines.append("| %s | %d |" % (c, n))
    lines += ["", "## Modules asserting whole-package counts", ""]
    for m in doc["modules_asserting_whole_package_counts"]:
        lines.append("- `%s`" % m)
    lines += ["", "## Per module", "", "| module | market | default | sites | by class |",
              "|---|---|---|---|---|"]
    for m in doc["modules"]:
        lines.append("| `%s` | %s | %s | %d | %s |" % (
            m["module"].replace("tests/pettripfinder/", ""), m["market"] or "",
            m["default_class"], m["site_count"],
            ", ".join("%s %d" % (k.replace("_INVARIANT", ""), v)
                      for k, v in m["by_class"].items())))
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", required=True)
    p.add_argument("--markdown")
    args = p.parse_args(argv)
    doc = build()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    if args.markdown:
        Path(args.markdown).write_text(markdown(doc), encoding="utf-8")
    print(json.dumps({k: doc[k] for k in ("modules_scanned", "modules_with_pins",
                                          "sites", "by_class")}, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
