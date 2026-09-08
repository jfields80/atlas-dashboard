"""ATLAS-THROUGHPUT-002 -- the five-condition market-local isolation proof.

    python -m scripts.pettripfinder.market_local_isolation --base <sha> --head <sha|WORKTREE> <path> [...]

A changed path earns MARKET_LOCAL_TOOLING only when EVERY condition below
holds, each proven from the file's own bytes at the revision being classified
and from the repository around it -- never from its name alone.

    1  NAMESPACE      exactly one declared zone owns the path (old AND new path
                      of a rename); the path is outside the never_local fence
    2  IMPORTS        every import is stdlib, an allow-listed shared module, an
                      allow-listed third-party package, or the zone's own
                      module; no importlib / __import__ / exec / runpy
    3  WRITES         every write target resolves statically to the zone's
                      write roots or the shared generated-report / data roots;
                      an unresolvable target FAILS
    4  REACHABILITY   nothing outside the zone names the module (git grep at
                      the head revision over scripts/, engines/, tests/,
                      conftest, deploy/, pytest.ini, netlify.toml); no shared
                      module enumerates the directory a data file sits in; a
                      subprocess must resolve to an allow-listed read-only
                      command; a deleted file has no remaining consumers
    5  REGISTRATION   the market is not registered (no markets/<id>.json, no
                      launch-participation row) at the head revision and the
                      zone declares production_runtime_included = NO

UNKNOWN is a failure. A path whose write target cannot be resolved, whose
subprocess argv is dynamic, or whose registry entry is malformed is NOT local.
"""

from __future__ import annotations

import argparse
import ast
import json
import posixpath
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import market_local_ownership as OWN  # noqa: E402

WORKTREE = "WORKTREE"
SCHEMA = "ptf-market-local-isolation-proof/1.0"

CONDITIONS = ("namespace", "imports", "writes", "reachability", "registration")

#: Where a reverse-mention makes a helper reachable: runtime, engines, tests,
#: harness config and deployment. Reports and markdown are not consumers.
REACHABILITY_SCAN_ROOTS = ("scripts", "engines", "repositories", "tests", "conftest.py",
                           "deploy", "pytest.ini", "netlify.toml", "core", "services", "routes")

_WRITE_MODES = ("w", "a", "x", "+")
_DYNAMIC_NAMES = {"importlib", "__import__", "runpy", "exec", "eval", "compile"}
_STDLIB = set(sys.stdlib_module_names) | {"__future__"}


# --------------------------------------------------------------------------- #
# Static path evaluation.
#
# A value is a set of candidate strings, each a (prefix, exact) pair: ``exact``
# says the whole path is known; a False marks a known DIRECTORY prefix with an
# unknown tail (``os.path.join(REPORTS, name)`` where ``name`` is dynamic).
# ``None`` means "cannot say", which every consumer treats as a failure.
# --------------------------------------------------------------------------- #

Cand = Tuple[str, bool]


class _Evaluator:
    def __init__(self, tree: ast.Module, module_relpath: str, rev: Optional[str] = None,
                 own_prefix: Optional[str] = None):
        self.tree = tree
        self.module_relpath = module_relpath
        self.file_abs = "/REPO/" + module_relpath
        self.rev = rev
        self.own_prefix = own_prefix
        self.module_consts: Dict[str, ast.AST] = {}
        self.argparse_defaults: Dict[str, ast.AST] = {}
        self._sibling: Dict[str, "_Evaluator"] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                self.module_consts[node.targets[0].id] = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                    and node.value is not None:
                self.module_consts[node.target.id] = node.value
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level \
                    and own_prefix and node.module.startswith(own_prefix) and rev is not None:
                # ``from <own zone module> import REPORTS``: a constant defined
                # in a sibling helper of the same zone, resolved from that
                # module's own bytes at the same revision.
                sibling_rel = node.module.replace(".", "/") + ".py"
                for alias in node.names:
                    self.module_consts[alias.asname or alias.name] = ast.Subscript(
                        value=ast.Name(id="__sibling__", ctx=ast.Load()),
                        slice=ast.Constant("%s::%s" % (sibling_rel, alias.name)), ctx=ast.Load())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "add_argument" and node.args \
                    and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                name = node.args[0].value.lstrip("-").replace("-", "_")
                for kw in node.keywords:
                    if kw.arg == "default":
                        self.argparse_defaults[name] = kw.value
                    if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                        name = kw.value.value
                        for kw2 in node.keywords:
                            if kw2.arg == "default":
                                self.argparse_defaults[name] = kw2.value

    def _sibling_value(self, spec: str) -> Optional[Set[Cand]]:
        sibling_rel, name = spec.split("::", 1)
        if sibling_rel not in self._sibling:
            text = read_at(self.rev, sibling_rel) if self.rev else None
            if text is None:
                return None
            try:
                self._sibling[sibling_rel] = _Evaluator(ast.parse(text), sibling_rel, self.rev, self.own_prefix)
            except SyntaxError:
                return None
        sib = self._sibling[sibling_rel]
        if name not in sib.module_consts:
            return None
        return sib.eval(sib.module_consts[name], {}, 1)

    # -- helpers --------------------------------------------------------------
    def _norm(self, value: str) -> str:
        value = value.replace("\\", "/")
        if value.startswith("/REPO/"):
            value = posixpath.normpath(value)
            if value.startswith("/REPO/"):
                return value[len("/REPO/"):]
            return value
        return posixpath.normpath(value) if value not in ("", ".") else value

    def eval(self, node: Optional[ast.AST], scope: Dict[str, List[ast.AST]],
             depth: int = 0) -> Optional[Set[Cand]]:
        if node is None or depth > 48:
            return None
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return {(node.value, True)}
            if node.value is None:
                return set()            # "no path": an argparse default of None
            return None
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            # ``args.out or DEFAULT`` -- every operand that can be a path must
            # resolve; an operand that is literally None contributes nothing.
            out: Set[Cand] = set()
            for value in node.values:
                got = self.eval(value, scope, depth + 1)
                if got is None:
                    return None
                out |= got
            return out
        if isinstance(node, ast.JoinedStr):
            out = ""
            exact = True
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    if exact:
                        out += part.value
                else:
                    exact = False
                    break
            return {(out, exact)} if out else None
        if isinstance(node, ast.Name):
            if node.id == "__file__":
                return {(self.file_abs, True)}
            if node.id in scope:
                cands: Set[Cand] = set()
                for value in scope[node.id]:
                    got = self.eval(value, scope, depth + 1)
                    if got is None:
                        return None
                    cands |= got
                return cands or None
            if node.id in self.module_consts:
                return self.eval(self.module_consts[node.id], {}, depth + 1)
            return None
        if isinstance(node, ast.Attribute):
            # args.<name> -> the argparse default
            if isinstance(node.value, ast.Name) and node.value.id == "args" \
                    and node.attr in self.argparse_defaults:
                return self.eval(self.argparse_defaults[node.attr], scope, depth + 1)
            if node.attr in ("parent",):
                base = self.eval(node.value, scope, depth + 1)
                if base is None:
                    return None
                return {(posixpath.dirname(p), exact) for p, exact in base}
            if node.attr == "executable" and isinstance(node.value, ast.Name) \
                    and node.value.id == "sys":
                return {("<python>", True)}
            return None
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "__sibling__" \
                    and isinstance(node.slice, ast.Constant):
                return self._sibling_value(node.slice.value)
            # Path(...).parents[n]
            if isinstance(node.value, ast.Attribute) and node.value.attr == "parents" \
                    and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                base = self.eval(node.value.value, scope, depth + 1)
                if base is None:
                    return None
                out = set()
                for p, exact in base:
                    for _ in range(node.slice.value + 1):
                        p = posixpath.dirname(p)
                    out.add((p, exact))
                return out
            return None
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Div):
                left = self.eval(node.left, scope, depth + 1)
                right = self.eval(node.right, scope, depth + 1)
                return self._join(left, right)
            if isinstance(node.op, ast.Add):
                left = self.eval(node.left, scope, depth + 1)
                right = self.eval(node.right, scope, depth + 1)
                if left is None:
                    return None
                if right is None:
                    return {(p, False) for p, _ in left}
                return {(a + b, ea and eb) for a, ea in left for b, eb in right}
            if isinstance(node.op, ast.Mod):
                left = self.eval(node.left, scope, depth + 1)
                if left is None:
                    return None
                out = set()
                for p, _ in left:
                    head = p.split("%", 1)[0]
                    out.add((head, False))
                return out
            return None
        if isinstance(node, ast.Call):
            fn = node.func
            name = _dotted(fn)
            if name in ("os.path.join", "posixpath.join", "ntpath.join"):
                acc = self.eval(node.args[0], scope, depth + 1) if node.args else None
                for arg in node.args[1:]:
                    acc = self._join(acc, self.eval(arg, scope, depth + 1))
                    if acc is None:
                        return None
                return acc
            if name in ("Path", "pathlib.Path", "PurePath", "PurePosixPath"):
                if not node.args:
                    return None
                acc = self.eval(node.args[0], scope, depth + 1)
                for arg in node.args[1:]:
                    acc = self._join(acc, self.eval(arg, scope, depth + 1))
                return acc
            if name in ("os.path.dirname",):
                base = self.eval(node.args[0], scope, depth + 1) if node.args else None
                if base is None:
                    return None
                return {(posixpath.dirname(p), exact) for p, exact in base}
            if name in ("os.path.abspath", "os.path.normpath", "os.path.realpath", "str"):
                return self.eval(node.args[0], scope, depth + 1) if node.args else None
            if isinstance(fn, ast.Attribute) and fn.attr in ("resolve", "absolute", "expanduser"):
                return self.eval(fn.value, scope, depth + 1)
            if isinstance(fn, ast.Attribute) and fn.attr in ("with_suffix", "with_name", "format",
                                                             "replace", "lower", "strip", "rstrip"):
                base = self.eval(fn.value, scope, depth + 1)
                if base is None:
                    return None
                if fn.attr in ("with_name", "with_suffix", "format"):
                    return {(posixpath.dirname(p) if fn.attr == "with_name" else p.split("{", 1)[0], False)
                            for p, _ in base}
                return base
            if isinstance(fn, ast.Attribute) and fn.attr == "joinpath":
                acc = self.eval(fn.value, scope, depth + 1)
                for arg in node.args:
                    acc = self._join(acc, self.eval(arg, scope, depth + 1))
                return acc
            return None
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            out: Set[Cand] = set()
            for elt in node.elts:
                got = self.eval(elt, scope, depth + 1)
                if got is None:
                    return None
                out |= got
            return out or None
        if isinstance(node, ast.IfExp):
            a = self.eval(node.body, scope, depth + 1)
            b = self.eval(node.orelse, scope, depth + 1)
            if a is None or b is None:
                return None
            return a | b
        return None

    def _join(self, left: Optional[Set[Cand]], right: Optional[Set[Cand]]) -> Optional[Set[Cand]]:
        if left is None:
            return None
        if right is None:
            return {(p, False) for p, _ in left}
        out: Set[Cand] = set()
        for lp, le in left:
            if not le:
                out.add((lp, False))
                continue
            for rp, re_ in right:
                if rp.startswith("/") or (len(rp) > 1 and rp[1] == ":"):
                    out.add((rp, re_))          # absolute right-hand side wins
                else:
                    out.add((posixpath.join(lp, rp) if lp else rp, re_))
        return out

    def resolve(self, node: Optional[ast.AST], scope: Dict[str, List[ast.AST]]) -> Optional[Set[Cand]]:
        got = self.eval(node, scope)
        if got is None:
            return None
        return {(self._norm(p), exact) for p, exact in got}


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return base + "." + node.attr if base else node.attr
    return ""


def _function_scope(func: ast.AST) -> Dict[str, List[ast.AST]]:
    """name -> every value expression assigned to it inside ``func``; a for-
    target over a literal collection contributes that collection's elements."""
    scope: Dict[str, List[ast.AST]] = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    scope.setdefault(target.id, []).append(node.value)
                elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(node.value, (ast.Tuple, ast.List)) \
                        and len(target.elts) == len(node.value.elts):
                    for t, v in zip(target.elts, node.value.elts):
                        if isinstance(t, ast.Name):
                            scope.setdefault(t.id, []).append(v)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            scope.setdefault(node.target.id, []).append(node.value)
        elif isinstance(node, ast.For):
            targets = node.target.elts if isinstance(node.target, (ast.Tuple, ast.List)) else [node.target]
            iterable = node.iter
            if isinstance(iterable, (ast.List, ast.Tuple, ast.Set)):
                for elt in iterable.elts:
                    if len(targets) == 1 and isinstance(targets[0], ast.Name):
                        scope.setdefault(targets[0].id, []).append(elt)
                    elif isinstance(elt, (ast.Tuple, ast.List)) and len(elt.elts) == len(targets):
                        for t, v in zip(targets, elt.elts):
                            if isinstance(t, ast.Name):
                                scope.setdefault(t.id, []).append(v)
            elif isinstance(iterable, ast.Name):
                # ``for rel in PATHS`` where PATHS is a module constant list
                for t in targets:
                    if isinstance(t, ast.Name):
                        scope.setdefault(t.id, []).append(ast.Subscript(
                            value=iterable, slice=ast.Constant(0), ctx=ast.Load()))
        elif isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.optional_vars, ast.Name):
                    scope.setdefault(item.optional_vars.id, []).append(item.context_expr)
    return scope


# --------------------------------------------------------------------------- #
# Write-call and subprocess detection.
# --------------------------------------------------------------------------- #

_WRITE_ATTRS = {"write_text", "write_bytes", "mkdir", "unlink", "rmdir", "touch", "rename", "replace"}
_WRITE_FUNCS = {"os.makedirs", "os.mkdir", "os.rename", "os.replace", "os.remove", "os.unlink",
                "os.rmdir", "os.removedirs", "shutil.rmtree", "shutil.copy", "shutil.copy2",
                "shutil.copyfile", "shutil.copytree", "shutil.move"}
_DEST_ARG_INDEX = {"shutil.copy": 1, "shutil.copy2": 1, "shutil.copyfile": 1,
                   "shutil.copytree": 1, "shutil.move": 1, "os.rename": 1, "os.replace": 1}


def _open_mode(call: ast.Call) -> str:
    if len(call.args) > 1 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
        return call.args[1].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    return "r"


def write_targets(tree: ast.Module) -> List[Tuple[ast.AST, ast.AST, str, int]]:
    """``(target expr, enclosing function, kind, lineno)`` for every write."""
    out = []

    def visit(node: ast.AST, func: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            child_func = child if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else func
            if isinstance(child, ast.Call):
                name = _dotted(child.func)
                if name == "open" or name.endswith(".open"):
                    mode = _open_mode(child)
                    if any(m in mode for m in _WRITE_MODES):
                        target = child.func.value if name.endswith(".open") and not child.args else (child.args[0] if child.args else None)
                        out.append((target, child_func, "open:%s" % mode, child.lineno))
                elif isinstance(child.func, ast.Attribute) and child.func.attr in _WRITE_ATTRS \
                        and name not in _WRITE_FUNCS:
                    # Path methods: the receiver is the target. ``str.replace``
                    # takes two arguments and ``Path.replace`` one, which is
                    # how the two are told apart here.
                    if child.func.attr == "replace" and len(child.args) != 1:
                        pass  # str.replace(old, new)
                    else:
                        target = child.func.value
                        if child.func.attr in ("rename", "replace") and child.args:
                            target = child.args[0]
                        out.append((target, child_func, "path." + child.func.attr, child.lineno))
                elif name in _WRITE_FUNCS:
                    index = _DEST_ARG_INDEX.get(name, 0)
                    target = child.args[index] if len(child.args) > index else None
                    out.append((target, child_func, name, child.lineno))
            visit(child, child_func)

    visit(tree, tree)
    return out


def subprocess_calls(tree: ast.Module) -> List[Tuple[ast.AST, ast.AST, int]]:
    out = []

    def visit(node: ast.AST, func: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            child_func = child if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else func
            if isinstance(child, ast.Call):
                name = _dotted(child.func)
                if name.startswith("subprocess.") or name in ("os.system", "os.popen", "os.exec", "os.spawn"):
                    argv = child.args[0] if child.args else None
                    for kw in child.keywords:
                        if kw.arg == "args":
                            argv = kw.value
                    out.append((argv, child_func, child.lineno))
            visit(child, child_func)

    visit(tree, tree)
    return out


def _wrapper_call_site_heads(tree: ast.Module, func_name: str) -> List[Optional[str]]:
    """The first positional argument of every call to ``func_name`` in the
    module, as a literal string; a non-literal call site yields ``None`` so the
    caller fails closed."""
    heads: List[Optional[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == func_name:
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                heads.append(node.args[0].value)
            else:
                heads.append(None)
    return heads


def _argv_head(evaluator: _Evaluator, argv: Optional[ast.AST], scope: Dict) -> Optional[List[str]]:
    """The literal leading elements of a subprocess argv, or ``None``."""
    node = argv
    # ["git"] + list(args)  -> the literal left operand
    while isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        node = node.left
    if isinstance(node, ast.Name):
        # cmd = [...] assigned in scope
        values = scope.get(node.id) or ([evaluator.module_consts[node.id]] if node.id in evaluator.module_consts else [])
        if len(values) != 1:
            return None
        return _argv_head(evaluator, values[0], scope)
    if isinstance(node, (ast.List, ast.Tuple)):
        head: List[str] = []
        for elt in node.elts:
            got = evaluator.eval(elt, scope)
            if got is None or len(got) != 1:
                break
            (value, exact), = got
            if not exact:
                break
            head.append(value)
        return head
    return None


# --------------------------------------------------------------------------- #
# git plumbing (read-only).
# --------------------------------------------------------------------------- #

_GIT_MEMO: Dict[Tuple, object] = {}


def clear_memo() -> None:
    """Forget every git read (a test that rewrites the worktree calls this)."""
    _GIT_MEMO.clear()


def _git(*args: str, cwd: Path = REPO_ROOT) -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.stdout if proc.returncode == 0 else ""


def read_at(rev: str, relpath: str) -> Optional[str]:
    if rev == WORKTREE:
        path = REPO_ROOT / relpath
        return path.read_text(encoding="utf-8-sig", errors="replace") if path.is_file() else None
    key = ("read", rev, relpath)
    if key not in _GIT_MEMO:
        proc = subprocess.run(["git", "show", "%s:%s/%s" % (rev, REPO_ROOT.name, relpath)],
                              cwd=str(REPO_ROOT.parent), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        _GIT_MEMO[key] = proc.stdout if proc.returncode == 0 else None
    return _GIT_MEMO[key]  # type: ignore[return-value]


def exists_at(rev: str, relpath: str) -> bool:
    if rev == WORKTREE:
        return (REPO_ROOT / relpath).exists()
    return bool(_git("cat-file", "-e", "%s:%s/%s" % (rev, REPO_ROOT.name, relpath), cwd=REPO_ROOT.parent)
                or subprocess.run(["git", "cat-file", "-e", "%s:%s/%s" % (rev, REPO_ROOT.name, relpath)],
                                  cwd=str(REPO_ROOT.parent), capture_output=True).returncode == 0)


def list_at(rev: str, directory: str) -> List[str]:
    """Repo-relative paths under ``directory`` at ``rev``."""
    if rev == WORKTREE:
        root = REPO_ROOT / directory
        if not root.exists():
            return []
        return sorted(p.relative_to(REPO_ROOT).as_posix() for p in root.rglob("*") if p.is_file())
    key = ("list", rev, directory)
    if key not in _GIT_MEMO:
        out = _git("ls-tree", "-r", "--name-only", rev, "--", directory)
        _GIT_MEMO[key] = sorted(line.strip() for line in out.splitlines() if line.strip())
    return list(_GIT_MEMO[key])  # type: ignore[arg-type]


_WORKTREE_SUFFIXES = (".py", ".ini", ".toml", ".cfg", ".json", ".txt", ".yaml", ".yml",
                      ".ps1", ".sh", ".cmd", ".bat", "")


def _worktree_candidates(roots: Sequence[str]) -> List[Path]:
    key = ("wt-files", tuple(roots))
    if key not in _GIT_MEMO:
        candidates: List[Path] = []
        for root in roots:
            base = REPO_ROOT / root
            if base.is_file():
                candidates.append(base)
            elif base.is_dir():
                candidates.extend(p for p in base.rglob("*") if p.is_file()
                                  and "__pycache__" not in p.parts
                                  and p.suffix in _WORKTREE_SUFFIXES)
        _GIT_MEMO[key] = candidates
    return list(_GIT_MEMO[key])  # type: ignore[arg-type]


def mentions_at(rev: str, needle: str, roots: Sequence[str] = REACHABILITY_SCAN_ROOTS) -> List[str]:
    """Files under ``roots`` at ``rev`` whose text contains ``needle`` (fixed string)."""
    key = ("mentions", rev, needle, tuple(roots))
    if key in _GIT_MEMO:
        return list(_GIT_MEMO[key])  # type: ignore[arg-type]
    if rev == WORKTREE:
        hits = []
        for path in _worktree_candidates(roots):
            try:
                if needle in path.read_text(encoding="utf-8", errors="replace"):
                    hits.append(path.relative_to(REPO_ROOT).as_posix())
            except OSError:
                continue
        _GIT_MEMO[key] = sorted(hits)
        return sorted(hits)
    out = _git("grep", "-l", "-F", "--", needle, rev, "--", *roots)
    hits = []
    for line in out.splitlines():
        if ":" in line:
            hits.append(line.split(":", 1)[1].strip())
    _GIT_MEMO[key] = sorted(hits)
    return sorted(hits)


def enumerating_lines_at(rev: str, directory: str, roots: Sequence[str]) -> List[Tuple[str, str]]:
    """``(path, line)`` for every line under ``roots`` at ``rev`` that names
    ``directory`` (its leaf AND its parent, or the leaf from a module that
    lives beside it) as path segments AND calls a directory enumerator.

    ``(out_root / "reports").glob(...)`` in an importer test names a tmp
    directory, not ``markets/reports``; requiring the parent segment too is
    what keeps that from counting as a consumer."""
    leaf = posixpath.basename(directory)
    parent_leaf = posixpath.basename(posixpath.dirname(directory))
    key = ("enum", rev, directory, tuple(roots))
    if key in _GIT_MEMO:
        return list(_GIT_MEMO[key])  # type: ignore[arg-type]

    def _tokens(segment: str) -> Tuple[str, ...]:
        return ('"%s"' % segment, "'%s'" % segment, "/%s/" % segment,
                "/%s\"" % segment, "/%s'" % segment, "%s/" % segment)

    tokens = _tokens(leaf)
    parent_tokens = _tokens(parent_leaf) if parent_leaf else ()
    enumerators = ("glob(", "iterdir(", "listdir(", "rglob(", "scandir(")

    def _counts(hit_path: str, body: str) -> bool:
        if not (any(t in body for t in tokens) and any(e in body for e in enumerators)):
            return False
        if any(t in body for t in parent_tokens):
            return True
        beside = posixpath.dirname(directory)
        return bool(beside) and hit_path.startswith(beside + "/")

    out: List[Tuple[str, str]] = []
    if rev == WORKTREE:
        for path in _worktree_candidates(roots):
            if path.suffix != ".py":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if leaf not in text:
                continue
            rel_hit = path.relative_to(REPO_ROOT).as_posix()
            for line in text.splitlines():
                if _counts(rel_hit, line):
                    out.append((rel_hit, line.strip()[:80]))
    else:
        raw = _git("grep", "-n", "-F", "--", leaf, rev, "--", *roots)
        for line in raw.splitlines():
            parts = line.split(":", 3)
            if len(parts) < 4 or not parts[1].endswith(".py"):
                continue
            body = parts[3]
            if _counts(parts[1], body):
                out.append((parts[1], body.strip()[:80]))
    _GIT_MEMO[key] = out
    return list(out)


def registered_market_ids_at(rev: str) -> Set[str]:
    key = ("registered", rev)
    if key in _GIT_MEMO and rev != WORKTREE:
        return set(_GIT_MEMO[key])  # type: ignore[arg-type]
    ids = _registered_market_ids_uncached(rev)
    _GIT_MEMO[key] = set(ids)
    return ids


def _registered_market_ids_uncached(rev: str) -> Set[str]:
    ids = set()
    for path in list_at(rev, "launch_packages/pettripfinder/markets"):
        if path.count("/") == 3 and path.endswith(".json"):
            ids.add(Path(path).stem)
    text = read_at(rev, "deploy/netlify/launch_participation.json")
    if text:
        try:
            doc = json.loads(text)
            for row in doc.get("markets", []):
                if isinstance(row, dict) and row.get("market_id"):
                    ids.add(row["market_id"])
        except ValueError:
            pass
    return ids


# --------------------------------------------------------------------------- #
# The proof.
# --------------------------------------------------------------------------- #

def _in_roots(rel: str, roots: Iterable[str]) -> bool:
    return any(OWN.under_root(rel, r) for r in roots)


def _dir_allowed(dirpath: str, roots: Iterable[str]) -> bool:
    """A directory operation (mkdir / makedirs) is harmless when the directory
    is one that a declared write root's files live in -- creating the
    ``markets/reports`` directory a report glob points into -- or lies inside
    a directory root."""
    dirpath = dirpath.rstrip("/")
    for root in roots:
        if root.endswith("/"):
            if dirpath == root.rstrip("/") or dirpath.startswith(root):
                return True
            continue
        if posixpath.dirname(root) == dirpath:
            return True
    return False


def _module_of_import(node: ast.AST) -> List[str]:
    """Every dotted module an import statement may bind. ``from a.b import c``
    yields ``a.b.c`` (c may be a submodule) and ``a.b`` (c may be a name); the
    allow-list check passes when EITHER form is allowed."""
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level:
            return ["<relative>"]
        base = node.module or ""
        return ["%s.%s|%s" % (base, a.name, base) for a in node.names]
    return []


def _import_allowed(module: str, zone: OWN.Zone, registry: OWN.Registry) -> Tuple[bool, str]:
    candidates = module.split("|")
    verdicts = []
    for cand in candidates:
        root = cand.split(".", 1)[0]
        if cand.startswith(zone.local_module_prefix):
            return True, "own module"
        if root in _STDLIB:
            return True, "stdlib"
        if cand in registry.shared_import_allowlist:
            return True, "allow-listed shared module"
        if root in registry.third_party_allowlist:
            return True, "allow-listed third-party package"
        if cand == "<relative>":
            verdicts.append("relative import")
        else:
            verdicts.append("not allow-listed")
    return False, verdicts[0] if verdicts else "not allow-listed"


def prove(relpath: str, base: str, head: str, status: str = "M",
          old_path: Optional[str] = None, registry: Optional[OWN.Registry] = None) -> Dict:
    """The proof document for one changed path. ``passed`` is True only when
    all five conditions hold; every failure carries its reason."""
    rel = OWN._posix(relpath)
    conditions: "OrderedDict[str, Dict]" = OrderedDict()
    try:
        registry = registry or OWN.load_registry()
    except OWN.OwnershipError as exc:
        for name in CONDITIONS:
            conditions[name] = _fail("registry malformed: %s" % exc)
        return _doc(rel, base, head, status, old_path, None, conditions)

    # 1 -- namespace (old and new path of a rename must agree)
    zone, why = OWN.owner_of(rel, registry)
    if zone is None:
        conditions["namespace"] = _fail(why)
    elif old_path and OWN._posix(old_path) != rel:
        old_zone, old_why = OWN.owner_of(old_path, registry)
        if old_zone is None or old_zone.market_id != zone.market_id:
            conditions["namespace"] = _fail("renamed from %s (%s)" % (old_path, old_why))
        else:
            conditions["namespace"] = _ok(why + "; renamed within the zone from %s" % old_path)
    else:
        conditions["namespace"] = _ok(why)
    if zone is None:
        for name in CONDITIONS[1:]:
            conditions[name] = _fail("not evaluated: no single owner")
        return _doc(rel, base, head, status, old_path, None, conditions)

    head_text = read_at(head, rel) if status != "D" else None
    base_text = read_at(base, old_path or rel) if status != "A" else None
    is_python = rel.endswith(".py")

    # 2 -- imports and dynamic dependencies
    tree: Optional[ast.Module] = None
    if status == "D":
        conditions["imports"] = _ok("deleted file imports nothing")
    elif not is_python:
        conditions["imports"] = _ok("not a Python module")
    elif head_text is None:
        conditions["imports"] = _fail("file absent at %s" % head)
    else:
        try:
            tree = ast.parse(head_text)
        except SyntaxError as exc:
            conditions["imports"] = _fail("does not parse: %s" % exc)
        else:
            bad: List[str] = []
            seen: List[str] = []
            for node in ast.walk(tree):
                for module in _module_of_import(node):
                    ok, reason = _import_allowed(module, zone, registry)
                    shown = module.split("|")[0]
                    seen.append("%s (%s)" % (shown, reason))
                    if not ok:
                        bad.append("%s: %s" % (shown, reason))
                if isinstance(node, ast.Name) and node.id in _DYNAMIC_NAMES:
                    bad.append("dynamic dependency: %s" % node.id)
                if isinstance(node, ast.Attribute) and node.attr in ("import_module",):
                    bad.append("dynamic dependency: importlib.import_module")
            if bad:
                conditions["imports"] = _fail("; ".join(sorted(set(bad))), imports=sorted(set(seen)))
            else:
                conditions["imports"] = _ok("every import is stdlib, allow-listed or the zone's own",
                                            imports=sorted(set(seen)))

    # 3 -- writes
    allowed_writes = tuple(zone.allowed_write_roots) + tuple(registry.shared_write_allowlist)
    if status == "D" or not is_python:
        conditions["writes"] = _ok("no code, no writes" if not is_python else "deleted file writes nothing")
    elif tree is None:
        conditions["writes"] = _fail("not evaluated: module did not parse")
    else:
        evaluator = _Evaluator(tree, rel, head, zone.local_module_prefix)
        problems: List[str] = []
        resolved_targets: List[str] = []
        for target, func, kind, lineno in write_targets(tree):
            scope = _function_scope(func) if func is not tree else {}
            cands = evaluator.resolve(target, scope)
            if not cands:
                problems.append("line %d %s: write target cannot be resolved statically" % (lineno, kind))
                continue
            for path, exact in cands:
                if path.startswith("<python>"):
                    problems.append("line %d %s: nonsense target %s" % (lineno, kind, path))
                    continue
                if path.startswith("/") or (len(path) > 1 and path[1] == ":") or path.startswith(".."):
                    problems.append("line %d %s: target outside the repository: %s" % (lineno, kind, path))
                    continue
                if ".." in path.split("/"):
                    problems.append("line %d %s: traversal in target: %s" % (lineno, kind, path))
                    continue
                if not exact and ".." in _dotted(target):
                    problems.append("line %d %s: dynamic tail" % (lineno, kind))
                probe = path if exact else path + "/<dynamic>"
                is_dir_op = kind in ("os.makedirs", "os.mkdir", "path.mkdir")
                if _in_roots(path if exact else path.rstrip("/") + "/x", allowed_writes) \
                        or (not exact and any(OWN.under_root(path, r) or path == r.rstrip("/")
                                              for r in allowed_writes if r.endswith("/"))) \
                        or (is_dir_op and _dir_allowed(path, allowed_writes)):
                    resolved_targets.append(probe)
                else:
                    problems.append("line %d %s: %s is outside the zone's write roots" % (lineno, kind, probe))
        if problems:
            conditions["writes"] = _fail("; ".join(problems[:6]), targets=resolved_targets)
        else:
            conditions["writes"] = _ok("every write target resolves inside the zone's roots",
                                       targets=resolved_targets)

    # 4 -- reverse imports / runtime reachability / subprocess
    problems = []
    stem = Path(rel).stem
    scan_rev = base if status == "D" else head
    # A module is reachable by its importable stem; a data file only by its
    # path (the bare basename "toledo-oh.json" is also a release contract's
    # name, which is a different file).
    needles = [stem] if is_python else [rel, "/".join(rel.split("/")[-2:])]
    for needle in needles:
        hits = [h for h in mentions_at(scan_rev, needle)
                if h != rel and not any(OWN._glob_match(p, h) for p in zone.owned_paths)
                and h not in registry.reachability_scan_exclusions]
        if hits:
            problems.append("%s is named by %s" % (needle, ", ".join(hits[:6])))
    if not is_python and status != "D":
        parent = posixpath.dirname(rel)
        leaf = posixpath.basename(parent)
        # The directory named as a path SEGMENT, not as a substring of another
        # name: "proposed" must not match identity_census_proposed.
        enumerators = ["%s: %s" % (hit, line)
                       for hit, line in enumerating_lines_at(
                           scan_rev, parent, ("scripts", "engines", "tests", "conftest.py"))
                       if not any(OWN._glob_match(p, hit) for p in zone.owned_paths)]
        if enumerators:
            problems.append("directory %s is enumerated by shared code: %s" % (parent, "; ".join(enumerators[:4])))
    if tree is not None:
        evaluator = _Evaluator(tree, rel, head, zone.local_module_prefix)
        for argv, func, lineno in subprocess_calls(tree):
            scope = _function_scope(func) if func is not tree else {}
            head_argv = _argv_head(evaluator, argv, scope)
            if not head_argv:
                problems.append("line %d: subprocess argv is not a literal" % lineno)
                continue
            if head_argv[0] == "git":
                subs: List[Optional[str]] = [head_argv[1]] if len(head_argv) > 1 else []
                if not subs and isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and func.args.vararg is not None:
                    # ``def git(*args): subprocess.run(["git"] + list(args))`` --
                    # the subcommand is the first literal every CALL SITE passes.
                    subs = _wrapper_call_site_heads(tree, func.name)
                if not subs or any(s not in registry.git_readonly_subcommands for s in subs):
                    problems.append("line %d: git subcommand %r is not read-only / not resolvable"
                                    % (lineno, subs or None))
            elif head_argv[0] == "<python>" and len(head_argv) >= 3 and head_argv[1] == "-m" \
                    and head_argv[2] in registry.python_modules:
                pass
            else:
                problems.append("line %d: subprocess %r is not allow-listed" % (lineno, head_argv[:3]))
    if status == "D" and base_text is None:
        problems.append("deleted file could not be read at %s" % base)
    conditions["reachability"] = _fail("; ".join(problems)) if problems else \
        _ok("nothing outside the zone names it; subprocesses are allow-listed")

    # 5 -- registration / production reachability
    if zone.production_runtime_included:
        conditions["registration"] = _fail("zone declares production_runtime_included = YES")
    else:
        registered = registered_market_ids_at(head if status != "D" else base)
        if zone.market_id in registered:
            conditions["registration"] = _fail("%s is registered at %s (markets/*.json or launch "
                                               "participation); production is reachable" % (zone.market_id, head))
        else:
            conditions["registration"] = _ok("%s is unregistered at %s" % (zone.market_id, head))

    return _doc(rel, base, head, status, old_path, zone, conditions)


def _ok(why: str, **extra) -> Dict:
    d = OrderedDict((("pass", True), ("why", why)))
    d.update(extra)
    return d


def _fail(why: str, **extra) -> Dict:
    d = OrderedDict((("pass", False), ("why", why)))
    d.update(extra)
    return d


def _doc(rel, base, head, status, old_path, zone, conditions) -> Dict:
    passed = bool(conditions) and all(c["pass"] for c in conditions.values()) \
        and set(conditions) == set(CONDITIONS)
    return OrderedDict((
        ("schema", SCHEMA),
        ("path", rel), ("status", status), ("old_path", old_path),
        ("base", base), ("head", head),
        ("zone", zone.market_id if zone else None),
        ("execution_zone", zone.execution_zone if zone else None),
        ("passed", passed),
        ("conditions", conditions),
        ("failed_conditions", [n for n, c in conditions.items() if not c["pass"]]),
    ))


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base", required=True)
    p.add_argument("--head", default=WORKTREE)
    p.add_argument("--status", default="M")
    p.add_argument("--json", action="store_true")
    p.add_argument("paths", nargs="+")
    args = p.parse_args(argv)
    docs = [prove(path, args.base, args.head, args.status) for path in args.paths]
    if args.json:
        print(json.dumps(docs, indent=1))
    else:
        for d in docs:
            print("%s %s  zone=%s" % ("LOCAL " if d["passed"] else "BROAD ", d["path"], d["zone"]))
            for name, c in d["conditions"].items():
                print("   %-13s %s  %s" % (name, "ok  " if c["pass"] else "FAIL", c["why"][:140]))
    return 0 if all(d["passed"] for d in docs) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
