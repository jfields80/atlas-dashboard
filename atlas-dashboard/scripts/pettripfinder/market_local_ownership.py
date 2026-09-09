"""ATLAS-THROUGHPUT-002 -- the market-local ownership registry.

    python -m scripts.pettripfinder.market_local_ownership [--json]
    python -m scripts.pettripfinder.market_local_ownership --owner <path> [...]

WHY
---
ATLAS-THROUGHPUT-001 measured that Regression V2 classifies every
``scripts/pettripfinder/<market>_*.py`` helper as GENERIC_RUNTIME_CHANGE by
path prefix, so a shadow market that touched nothing shared still owed a
~2-hour broad regression. The classifier had no notion of a market-local
NAMESPACE, of what a helper IMPORTS, of where it WRITES, of who imports IT,
or of whether the market can reach production at all.

This module is the first of those notions: ONE committed registry
(``launch_packages/pettripfinder/market_local_ownership.json``) that declares,
per market, an execution zone -- the paths it owns, the shared modules it may
import, the roots it may write, the tests it owns -- plus the repository-wide
allow-lists and the ``never_local`` fence no zone may cross.

WHAT THE REGISTRY GRANTS
------------------------
Nothing by itself. It only names the zone a path MAY belong to; whether a
change is MARKET_LOCAL_TOOLING is decided by the five-condition proof in
:mod:`scripts.pettripfinder.market_local_isolation`, and every failure of
that proof leaves the path in the Regression V2 prefix class it had before.
A malformed registry, a path two zones claim, or a path inside the
``never_local`` fence is a proof FAILURE, not a warning.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "launch_packages" / "pettripfinder" / "market_local_ownership.json"
SCHEMA = "ptf-market-local-ownership/1.0"

SHADOW = "SHADOW"
SHADOW_UNTIL_REGISTERED = "SHADOW_UNTIL_REGISTERED"
EXECUTION_ZONES = (SHADOW, SHADOW_UNTIL_REGISTERED)

_MARKET_ID = re.compile(r"^[a-z][a-z0-9]+(-[a-z0-9]+)*-[a-z]{2}$")


class OwnershipError(ValueError):
    """The registry is malformed. Fail closed: no zone is trusted."""


@dataclass(frozen=True)
class Zone:
    market_id: str
    execution_zone: str
    production_runtime_included: bool
    owned_paths: Tuple[str, ...]
    allowed_write_roots: Tuple[str, ...]
    allowed_read_roots: Tuple[str, ...]
    owned_tests: Tuple[str, ...]
    note: str = ""

    @property
    def market_us(self) -> str:
        return self.market_id.replace("-", "_")

    @property
    def local_module_prefix(self) -> str:
        """Dotted prefix of this zone's own Python modules."""
        return "scripts.pettripfinder.%s_" % self.market_us


@dataclass(frozen=True)
class Registry:
    schema: str
    shared_import_allowlist: Tuple[str, ...]
    third_party_allowlist: Tuple[str, ...]
    shared_write_allowlist: Tuple[str, ...]
    git_readonly_subcommands: Tuple[str, ...]
    python_modules: Tuple[str, ...]
    never_local_prefixes: Tuple[str, ...]
    never_local_globs: Tuple[str, ...]
    zones: Tuple[Zone, ...] = field(default_factory=tuple)
    #: Test modules whose purpose is to name market-local paths (the
    #: classifier's own self-tests); the reachability scan ignores them.
    reachability_scan_exclusions: Tuple[str, ...] = field(default_factory=tuple)

    def zone_for(self, market_id: str) -> Optional[Zone]:
        for zone in self.zones:
            if zone.market_id == market_id:
                return zone
        return None

    def owners_of(self, relpath: str) -> List[Zone]:
        """Every zone whose owned_paths claim ``relpath``."""
        rel = _posix(relpath)
        if self.is_never_local(rel):
            return []
        return [z for z in self.zones if any(_glob_match(p, rel) for p in z.owned_paths)]

    def is_never_local(self, relpath: str) -> bool:
        rel = _posix(relpath)
        if any(rel.startswith(p) for p in self.never_local_prefixes):
            return True
        return any(_glob_match(g, rel) for g in self.never_local_globs)


# --------------------------------------------------------------------------- #
# glob matching: ``*`` stops at ``/``; ``**/`` spans directories (the same
# semantics regression_delta uses, so a rule reads the same in both places).
# --------------------------------------------------------------------------- #

_GLOB_CACHE: Dict[str, "re.Pattern"] = {}


def _glob_regex(pattern: str) -> "re.Pattern":
    cached = _GLOB_CACHE.get(pattern)
    if cached is not None:
        return cached
    parts: List[str] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "*":
            if pattern[i:i + 3] == "**/":
                parts.append("(?:[^/]+/)*")
                i += 3
                continue
            if pattern[i:i + 2] == "**":
                parts.append(".*")
                i += 2
                continue
            parts.append("[^/]*")
        elif ch == "?":
            parts.append("[^/]")
        else:
            parts.append(re.escape(ch))
        i += 1
    compiled = re.compile("^" + "".join(parts) + "$")
    _GLOB_CACHE[pattern] = compiled
    return compiled


def _glob_match(pattern: str, relpath: str) -> bool:
    return _glob_regex(pattern).match(relpath) is not None


def _posix(path: str) -> str:
    out = str(path).replace("\\", "/")
    while out.startswith("./"):
        out = out[2:]
    return out


def under_root(relpath: str, root: str) -> bool:
    """Is ``relpath`` the root itself, inside the root directory, or matched by
    the root when the root is a glob?"""
    rel = _posix(relpath)
    root = _posix(root)
    if root.endswith("/"):
        return rel.startswith(root)
    if any(ch in root for ch in "*?"):
        return _glob_match(root, rel)
    return rel == root or rel.startswith(root + "/")


# --------------------------------------------------------------------------- #
# Loading and validation.
# --------------------------------------------------------------------------- #

def _substitute(patterns: Sequence[str], market_id: str) -> Tuple[str, ...]:
    us = market_id.replace("-", "_")
    upper = market_id.upper()
    return tuple(p.replace("<id>", market_id).replace("<us>", us).replace("<ID>", upper)
                 for p in patterns)


def _require(doc, key: str, kind, where: str):
    if key not in doc:
        raise OwnershipError("%s: missing %r" % (where, key))
    value = doc[key]
    if not isinstance(value, kind):
        raise OwnershipError("%s: %r must be %s" % (where, key, kind.__name__))
    return value


def _str_list(doc, key: str, where: str) -> Tuple[str, ...]:
    value = _require(doc, key, list, where)
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise OwnershipError("%s: %r holds a non-string or empty entry" % (where, key))
    return tuple(value)


def parse_registry(doc: Dict) -> Registry:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise OwnershipError("registry schema must be %r" % SCHEMA)
    imports = _require(doc, "shared_import_allowlist", dict, "registry")
    writes = _require(doc, "shared_write_allowlist", dict, "registry")
    sub = _require(doc, "allowed_subprocess", dict, "registry")
    never = _require(doc, "never_local", dict, "registry")
    template = _require(doc, "zone_template", dict, "registry")
    zones_doc = _require(doc, "zones", list, "registry")

    shared_write_roots = _str_list(writes, "roots", "shared_write_allowlist")
    for root in shared_write_roots:
        if not root.endswith("/"):
            raise OwnershipError("shared write root %r must be a directory (end with /)" % root)

    zones: List[Zone] = []
    seen = set()
    for entry in zones_doc:
        where = "zone %r" % entry.get("market_id")
        market_id = _require(entry, "market_id", str, where)
        if not _MARKET_ID.match(market_id):
            raise OwnershipError("%s: not a market id" % where)
        if market_id in seen:
            raise OwnershipError("%s: declared twice" % where)
        seen.add(market_id)
        execution_zone = _require(entry, "execution_zone", str, where)
        if execution_zone not in EXECUTION_ZONES:
            raise OwnershipError("%s: execution_zone must be one of %s" % (where, EXECUTION_ZONES))
        included = _require(entry, "production_runtime_included", str, where)
        if included not in ("YES", "NO"):
            raise OwnershipError("%s: production_runtime_included must be YES or NO" % where)
        if entry.get("use_template"):
            owned = _substitute(_str_list(template, "owned_paths", "zone_template"), market_id)
            write_roots = _substitute(_str_list(template, "allowed_write_roots", "zone_template"), market_id)
            read_roots = _substitute(_str_list(template, "allowed_read_roots", "zone_template"), market_id)
            tests = _substitute(_str_list(template, "owned_tests", "zone_template"), market_id)
        else:
            owned = _substitute(_str_list(entry, "owned_paths", where), market_id)
            write_roots = _substitute(_str_list(entry, "allowed_write_roots", where), market_id)
            read_roots = _substitute(_str_list(entry, "allowed_read_roots", where), market_id)
            tests = _substitute(_str_list(entry, "owned_tests", where), market_id)
        for pattern in owned + write_roots + tests:
            if "<" in pattern or ">" in pattern:
                raise OwnershipError("%s: unsubstituted placeholder in %r" % (where, pattern))
            if market_id not in pattern and market_id.replace("-", "_") not in pattern \
                    and market_id.upper() not in pattern:
                raise OwnershipError("%s: pattern %r does not name the market -- a zone may "
                                     "only own paths that carry its own id" % (where, pattern))
        zones.append(Zone(
            market_id=market_id, execution_zone=execution_zone,
            production_runtime_included=(included == "YES"),
            owned_paths=owned, allowed_write_roots=write_roots,
            allowed_read_roots=read_roots, owned_tests=tests,
            note=str(entry.get("note", "")),
        ))
    registry = Registry(
        schema=SCHEMA,
        shared_import_allowlist=_str_list(imports, "modules", "shared_import_allowlist"),
        third_party_allowlist=tuple(imports.get("third_party", ())),
        shared_write_allowlist=shared_write_roots,
        git_readonly_subcommands=_str_list(sub, "git_readonly_subcommands", "allowed_subprocess"),
        python_modules=_str_list(sub, "python_modules", "allowed_subprocess"),
        never_local_prefixes=_str_list(never, "prefixes", "never_local"),
        never_local_globs=_str_list(never, "globs", "never_local"),
        zones=tuple(zones),
        reachability_scan_exclusions=(
            _str_list(doc["reachability_scan_exclusions"], "paths", "reachability_scan_exclusions")
            if isinstance(doc.get("reachability_scan_exclusions"), dict) else ()),
    )
    for path in registry.reachability_scan_exclusions:
        if not path.startswith("tests/") or not path.endswith(".py"):
            raise OwnershipError("reachability_scan_exclusions may name test modules only, not %r" % path)
    # No zone may own a never-local path by construction: probe every owned
    # pattern's literal prefix against the fence.
    for zone in registry.zones:
        for pattern in zone.owned_paths:
            literal = pattern.split("*", 1)[0]
            if any(literal.startswith(p) for p in registry.never_local_prefixes):
                raise OwnershipError("zone %s owns %r inside the never_local fence"
                                     % (zone.market_id, pattern))
    return registry


_CACHE: Dict[str, Registry] = {}


def load_registry(path: Optional[Path] = None, text: Optional[str] = None) -> Registry:
    """Parse the committed registry (or ``text`` -- a registry read from git at
    another revision). Never cached across different texts."""
    if text is None:
        path = Path(path) if path else REGISTRY_PATH
        text = path.read_text(encoding="utf-8-sig")
    key = text
    if key not in _CACHE:
        try:
            doc = json.loads(text)
        except ValueError as exc:
            raise OwnershipError("registry is not JSON: %s" % exc)
        _CACHE[key] = parse_registry(doc)
    return _CACHE[key]


def owner_of(relpath: str, registry: Optional[Registry] = None) -> Tuple[Optional[Zone], str]:
    """``(zone, why)``: the ONE zone that owns the path, or ``None`` with the
    reason (unowned / never-local / claimed by several zones)."""
    registry = registry or load_registry()
    rel = _posix(relpath)
    if registry.is_never_local(rel):
        return None, "inside the never_local fence"
    owners = registry.owners_of(rel)
    if not owners:
        return None, "no zone owns this path"
    if len(owners) > 1:
        return None, "claimed by %d zones: %s" % (
            len(owners), ", ".join(z.market_id for z in owners))
    return owners[0], "owned by zone %s" % owners[0].market_id


def describe(registry: Optional[Registry] = None) -> Dict:
    registry = registry or load_registry()
    return OrderedDict((
        ("schema", registry.schema),
        ("zones", [OrderedDict((
            ("market_id", z.market_id), ("execution_zone", z.execution_zone),
            ("production_runtime_included", z.production_runtime_included),
            ("owned_paths", list(z.owned_paths)),
            ("allowed_write_roots", list(z.allowed_write_roots)),
            ("allowed_read_roots", list(z.allowed_read_roots)),
            ("owned_tests", list(z.owned_tests)),
        )) for z in registry.zones]),
        ("shared_import_allowlist", list(registry.shared_import_allowlist)),
        ("shared_write_allowlist", list(registry.shared_write_allowlist)),
        ("never_local_prefixes", list(registry.never_local_prefixes)),
        ("never_local_globs", list(registry.never_local_globs)),
    ))


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true")
    p.add_argument("--owner", action="append", default=[], help="report the owner of a path")
    args = p.parse_args(argv)
    registry = load_registry()
    if args.owner:
        for path in args.owner:
            zone, why = owner_of(path, registry)
            print("%-70s %s" % (path, why))
        return 0
    doc = describe(registry)
    if args.json:
        print(json.dumps(doc, indent=1))
    else:
        for z in doc["zones"]:
            print("%-16s %-24s owned=%d write_roots=%d tests=%d" % (
                z["market_id"], z["execution_zone"], len(z["owned_paths"]),
                len(z["allowed_write_roots"]), len(z["owned_tests"])))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
