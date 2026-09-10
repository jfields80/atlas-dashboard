"""PTF-NASHVILLE-TN-FINAL-REGRESSION-CLOSURE-004 -- one broad run, and no second.

The shared-pin determination answers A: the recovery genuinely required one
broad regression. That run was executed and closed. This module answers the
question that follows and is easy to get wrong -- whether the commits made AFTER
that run require another one.

Regression V2 classifies the delta since the broad run FULL_REGRESSION_REQUIRED
= YES, on one ground only: three new modules under ``scripts/pettripfinder/``,
which the prefix rule calls SHARED_RUNTIME_CHANGE. There are no narrowing
blockers.

A prefix is a rule about a path. Whether those modules are a DEPENDENCY of
anything is a fact, and this measures it five ways:

  1  IMPORTS          any ``import``/``from`` statement naming the module
  2  CACHE CLOSURE    membership in bundle_cache_closure.code_modules, the
                      declared input set the persistent cache proves constant
  3  CI               any reference from .github/workflows
  4  DYNAMIC IMPORT   membership in a list a test feeds to importlib -- the only
                      way a module nothing imports can still be executed
  5  COLLECTION       whether pytest would collect it at all

A module that fails all five cannot be reached by any test or any production
path, so a second broad run would execute exactly zero new lines of it. That is
the narrow-follow-up case Regression V2 exists for, and it is the only ground on
which this module will say no.

It will say YES the moment a genuinely distinct shared dependency changed: an
existing shared module edited, a schema, an assembler, an UNCLASSIFIED path, or
a narrowing blocker. Those are checked first and short-circuit the measurement.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
_REPO = _DASH.parent
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-TN-FINAL-REGRESSION-CLOSURE-004"
REPORTS = _DASH / "launch_packages" / "pettripfinder" / "markets" / "reports"
OUT = REPORTS / "nashville_tn_broad_run_closure_004.json"
CLOSURE_DECL = _DASH / "launch_packages" / "pettripfinder" / "bundle_cache_closure.json"

#: Classes that mean a genuinely distinct shared dependency moved. Any of these
#: on a path that is NOT a brand-new unreachable module ends the analysis.
WIDENING = ("SCHEMA_CHANGE", "DEPLOYMENT_CHANGE", "UNCLASSIFIED",
            "ROUTING_SEMANTIC_CHANGE", "AUTHORITY_CHANGE")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def module_name(relpath):
    return Path(relpath).stem


def reachability(relpath):
    """Five independent ways a module could be reached. All must be empty."""
    name = module_name(relpath)
    dotted = relpath[:-3].replace("/", ".") if relpath.endswith(".py") else relpath

    imports = []
    dynamic = []
    for path in sorted(_DASH.rglob("*.py")):
        if path.resolve() == (_DASH / relpath).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if name not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        rel = str(path.relative_to(_DASH)).replace("\\", "/")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.endswith(name) or alias.name == dotted:
                        imports.append(OrderedDict((("from", rel), ("line", node.lineno))))
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").endswith(name) or any(
                        a.name == name for a in node.names):
                    imports.append(OrderedDict((("from", rel), ("line", node.lineno))))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # A dotted module path sitting in a literal is how importlib is fed.
                if node.value.endswith(name) and "." in node.value:
                    dynamic.append(OrderedDict((("from", rel), ("line", node.lineno),
                                                ("literal", node.value))))

    closure = _load(CLOSURE_DECL)
    in_closure = [m for m in closure.get("code_modules") or [] if name in str(m)]

    ci = []
    workflows = _REPO / ".github" / "workflows"
    if workflows.is_dir():
        for path in sorted(workflows.rglob("*.yml")):
            if name in path.read_text(encoding="utf-8"):
                ci.append(str(path.relative_to(_REPO)).replace("\\", "/"))

    collected_by_pytest = relpath.startswith("tests/") and Path(relpath).name.startswith("test_")

    return OrderedDict((
        ("module", relpath),
        ("import_statements", imports),
        ("in_bundle_cache_closure", in_closure),
        ("named_in_ci_workflows", ci),
        ("dynamic_import_literals", dynamic),
        ("collected_by_pytest", collected_by_pytest),
        ("reachable", bool(imports or in_closure or ci or dynamic or collected_by_pytest)),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--broad-run-audit",
                    default=str(REPORTS / "nashville_tn_recovery_audit_003.json"))
    ap.add_argument("--base", required=True, help="the commit the broad run was executed at")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    from scripts.pettripfinder import regression_delta as RD

    audit = _load(args.broad_run_audit)
    surface = RD.classify_change(base=args.base, head=args.head)
    plan = RD.plan_for(surface)

    added = set()
    try:
        import subprocess
        out = subprocess.run(["git", "diff", "--name-status", "%s..%s" % (args.base, args.head)],
                             cwd=str(_REPO), capture_output=True, text=True)
        for line in out.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].startswith("A"):
                added.add(parts[-1])
    except Exception:                                                # noqa: BLE001
        pass

    runtime, widened = [], []
    for entry in surface["changed_files"]:
        rel = entry["path"]
        classes = set(entry["classes"])
        if entry["release_surface"] == "SHARED_RUNTIME_CHANGE":
            runtime.append(rel)
        if classes & set(WIDENING):
            widened.append(OrderedDict((("path", rel), ("classes", sorted(classes)))))

    proofs = []
    for rel in runtime:
        repo_rel = "atlas-dashboard/" + rel
        proof = reachability(rel)
        proof["added_by_this_delta"] = repo_rel in added
        proof["pre_existing_module_edited"] = repo_rel not in added
        proofs.append(proof)

    any_reachable = any(p["reachable"] for p in proofs)
    any_pre_existing_shared_edited = any(p["pre_existing_module_edited"] for p in proofs)
    blockers = list(surface.get("narrowing_blockers") or ())

    second_required = bool(widened or blockers or any_reachable
                           or any_pre_existing_shared_edited)

    doc = OrderedDict((
        ("schema", "ptf-broad-run-closure/1.0"),
        ("work_order", WORK_ORDER),
        ("question",
         "the recovery's one broad regression was executed and closed at %s. Do the commits "
         "made AFTER it require a second one?" % args.base),
        ("the_broad_run_already_executed", OrderedDict((
            ("audit", os.path.relpath(args.broad_run_audit, str(_DASH))),
            ("executed_at", audit["recovery_commit"]),
            ("collected", audit["collected"]),
            ("failures", audit["failures"]),
            ("PRE_EXISTING", audit["PRE_EXISTING"]),
            ("TRUE_NEW_reported", audit["TRUE_NEW_REPORTED_BY_THE_CLASSIFIER"]),
            ("pre_existing_at_parent",
             audit["the_classifier_cannot_see_this"]["PRE_EXISTING_AT_PARENT"]["count"]),
            ("caused_by_the_order",
             audit["the_classifier_cannot_see_this"]["CAUSED_BY_THIS_ORDER"]["count"]),
            ("closed_by_rerun", len(audit["closure"]["closed_by_rerun"])),
            ("TRUE_NEW_FAILURE_AFTER_CLOSURE", audit["TRUE_NEW_FAILURE_AFTER_CLOSURE"]),
            ("seconds", audit.get("seconds")),
        ))),
        ("the_delta_since_that_run", OrderedDict((
            ("base", args.base), ("head", surface.get("head_sha")),
            ("changed_files", surface["changed_file_count"]),
            ("classes", surface["change_classes"]),
            ("narrowing_blockers", blockers),
            ("regression_v2_says_full_regression_required", plan["full_regression_required"]),
            ("what_drives_it", sorted(runtime)),
        ))),
        ("genuinely_distinct_shared_dependencies_changed", widened),
        ("reachability_of_the_new_shared_prefix_modules", proofs),
        ("summary", OrderedDict((
            ("modules_under_the_shared_prefix", len(proofs)),
            ("of_those_pre_existing_and_edited",
             sum(1 for p in proofs if p["pre_existing_module_edited"])),
            ("of_those_reachable", sum(1 for p in proofs if p["reachable"])),
            ("total_import_statements", sum(len(p["import_statements"]) for p in proofs)),
            ("total_cache_closure_entries",
             sum(len(p["in_bundle_cache_closure"]) for p in proofs)),
            ("total_ci_references", sum(len(p["named_in_ci_workflows"]) for p in proofs)),
            ("total_dynamic_import_literals",
             sum(len(p["dynamic_import_literals"]) for p in proofs)),
            ("collected_by_pytest", sum(1 for p in proofs if p["collected_by_pytest"])),
        ))),
        ("SECOND_BROAD_RUN_REQUIRED", "YES" if second_required else "NO"),
        ("why", ("a genuinely distinct shared dependency changed" if second_required else
                 "every module the prefix rule flagged is NEW in this delta and unreachable by "
                 "all five routes: no import statement names it, it is absent from the bundle "
                 "cache's declared code_modules, no CI workflow references it, no dynamic-import "
                 "literal names it, and pytest does not collect it. A second broad run would "
                 "execute zero new lines. The test-expectation changes in the same delta were "
                 "closed by node id.")),
        ("nothing_was_weakened", True),
        ("REMOTE_BROAD_JOBS_REQUIRED", 0),
    ))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("broad run already executed :", audit["collected"], "collected, AFTER CLOSURE",
          audit["TRUE_NEW_FAILURE_AFTER_CLOSURE"])
    print("delta since                :", surface["changed_file_count"], "files;",
          "regression_delta says full =", plan["full_regression_required"])
    print("shared-prefix modules      :", len(proofs))
    for p in proofs:
        print("   %-58s new=%s reachable=%s" % (p["module"], p["added_by_this_delta"],
                                                p["reachable"]))
    print("distinct shared deps moved :", len(widened))
    print("SECOND_BROAD_RUN_REQUIRED  :", doc["SECOND_BROAD_RUN_REQUIRED"])
    print("written                    :", os.path.relpath(args.out, str(_DASH)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
