"""ATLAS-THROUGHPUT-006 -- turn a sharded run's artifacts into a trusted receipt.

This is the job the remote workflow's final step runs, and the same code the
local shard simulation runs, so the two cannot drift. It does three things and
refuses to do any of them loosely:

1. **Account for every planned node id.** The shards' junit files are unioned
   and compared with the collection the run planned. A missing node, an
   unintended duplicate, a shard that never reported and a collection error are
   all run failures. A shard's own exit status is deliberately NOT the verdict:
   the f75aa95 baseline failures make every honest broad run exit non-zero, and
   a workflow that treated that as failure would teach everyone to ignore it.

2. **Classify failures by node id AND signature.** A node in the baseline that
   now fails for a materially different reason is TRUE_NEW. The baseline
   records that a test fails, not a licence for it to fail in new ways.

3. **Emit a receipt that can be verified rather than believed.** The release
   coordinator checks the receipt's own digest, the commit, the candidate, the
   dependency digest, the shards completed and the node accounting before it
   will treat a broad validation as satisfied.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import ci_validation as CI
from scripts.pettripfinder import regression_lanes as LANES
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = SMP.REPO_ROOT
BASELINE = SMP.LAUNCH_PACKAGE / "regression_baselines" / "f75aa95.json"


def read_shard(xml_path: Path) -> "OrderedDict[str, Any]":
    """One shard's junit: node ids, statuses and failure messages."""
    cases = LANES._junit_cases(Path(xml_path))
    messages: Dict[str, str] = {}
    counts = OrderedDict((("tests", 0), ("failures", 0), ("errors", 0), ("skipped", 0)))
    seconds = 0.0
    try:
        root = ET.parse(str(xml_path)).getroot()
    except Exception as exc:
        return OrderedDict((("shard", Path(xml_path).stem), ("readable", False),
                            ("detail", str(exc)[:200]), ("nodes", {}), ("messages", {}),
                            ("counts", counts), ("seconds", 0.0)))
    for suite in root.iter("testsuite"):
        for key in counts:
            counts[key] += int(suite.get(key, 0) or 0)
        seconds += float(suite.get("time", 0) or 0)
    for case in root.iter("testcase"):
        classname = case.get("classname") or ""
        name = case.get("name") or ""
        for child in case:
            if child.tag in ("failure", "error"):
                node = _node_id(classname, name, case.get("file"))
                messages[node] = ((child.get("message") or "") + "\n" + (child.text or ""))[:4000]
    return OrderedDict((
        ("shard", Path(xml_path).stem), ("readable", True), ("nodes", cases),
        ("messages", messages), ("counts", counts), ("seconds", round(seconds, 1)),
    ))


def _node_id(classname: str, name: str, file_attr: Optional[str]) -> str:
    if file_attr:
        node = file_attr.replace("\\", "/")
        parts = classname.split(".")
        stem = Path(file_attr).stem
        if stem in parts:
            cls = parts[parts.index(stem) + 1:]
            return node + "::" + "::".join(cls + [name]) if cls else node + "::" + name
        return node + "::" + name
    parts = classname.split(".")
    path_parts: List[str] = []
    cls_parts: List[str] = []
    for part in parts:
        if cls_parts or (path_parts and part[:1].isupper()):
            cls_parts.append(part)
        else:
            path_parts.append(part)
    node = "/".join(path_parts) + ".py"
    if cls_parts:
        node += "::" + "::".join(cls_parts)
    return node + "::" + name


def gather(artifacts_dir: Path) -> "OrderedDict[str, Any]":
    """Every shard artifact under a directory, whatever nesting CI used."""
    shards: "OrderedDict[str, Any]" = OrderedDict()
    for xml_path in sorted(Path(artifacts_dir).rglob("shard-*.xml")):
        shard = read_shard(xml_path)
        shards[shard["shard"]] = shard
    return shards


def build(*, planned: Sequence[str], shards: Mapping[str, Mapping],
          shards_required: Sequence[Any], source_commit: str, ci_run_id: str,
          candidate_digest: Optional[str] = None,
          parent_release_digest: Optional[str] = None,
          change_class: Sequence[str] = (), reason: str = "",
          baseline: Optional[Mapping] = None,
          exclusions: Optional[Mapping[str, str]] = None) -> "OrderedDict[str, Any]":
    baseline = baseline if baseline is not None else json.loads(
        BASELINE.read_text(encoding="utf-8-sig"))
    executed = OrderedDict((name, sorted(shard["nodes"])) for name, shard in shards.items())
    failing: Dict[str, str] = {}
    counts = OrderedDict((("tests", 0), ("failures", 0), ("errors", 0), ("skipped", 0)))
    seconds = 0.0
    for shard in shards.values():
        failing.update(shard.get("messages") or {})
        for key in counts:
            counts[key] += int((shard.get("counts") or {}).get(key, 0) or 0)
        seconds += float(shard.get("seconds") or 0.0)
    counts["shard_seconds_total"] = round(seconds, 1)
    counts["shard_seconds_slowest"] = round(
        max((float(s.get("seconds") or 0.0) for s in shards.values()), default=0.0), 1)

    completed = [name for name, shard in shards.items() if shard.get("readable")]
    completeness = CI.verify_completeness(
        planned, executed, excluded=exclusions,
        shards_required=[_shard_number(s) for s in shards_required],
        shards_completed=[_shard_number(s) for s in completed])
    classified = CI.classify_failures(failing, baseline)
    receipt = CI.build_receipt(
        ci_run_id=ci_run_id, source_commit=source_commit, change_class=change_class,
        shards_required=[_shard_number(s) for s in shards_required],
        shards_completed=[_shard_number(s) for s in completed],
        completeness=completeness, counts=counts,
        pre_existing=classified["PRE_EXISTING"], true_new=classified["TRUE_NEW"],
        candidate_digest=candidate_digest or None,
        parent_release_digest=parent_release_digest,
        artifact_digests=OrderedDict((name, SMP.sha256_text(SMP.canonical_json(shard["nodes"])))
                                     for name, shard in shards.items()))
    receipt["reason"] = reason
    receipt["baseline_source_sha"] = baseline.get("source_sha")
    receipt["changed_signature"] = classified["changed_signature"]
    receipt["receipt_digest"] = SMP.sha256_text(SMP.canonical_json(
        OrderedDict((k, v) for k, v in receipt.items() if k != "receipt_digest")))
    return receipt


def _shard_number(value: Any) -> int:
    text = str(value)
    digits = "".join(c for c in text if c.isdigit())
    return int(digits) if digits else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="ATLAS-THROUGHPUT-006 -- verify a sharded run and emit its receipt")
    parser.add_argument("--planned", help="JSON list of planned node ids; collected if absent")
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--shards-required", default="[1,2,3,4]")
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--ci-run-id", default="local")
    parser.add_argument("--candidate-digest", default="")
    parser.add_argument("--parent-release-digest", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--out", default="ci-receipt.json")
    args = parser.parse_args(argv)

    if args.planned:
        planned = json.loads(Path(args.planned).read_text(encoding="utf-8-sig"))
    else:
        planned, errors = CI.collect_node_ids()
        if errors:
            print("COLLECTION ERRORS: %s" % errors[:3])
            return 1
    try:
        required = json.loads(args.shards_required)
    except ValueError:
        required = [s.strip() for s in args.shards_required.split(",") if s.strip()]

    shards = gather(Path(args.artifacts))
    receipt = build(planned=planned, shards=shards, shards_required=required,
                    source_commit=args.source_commit or _head(),
                    ci_run_id=args.ci_run_id,
                    candidate_digest=args.candidate_digest or None,
                    parent_release_digest=args.parent_release_digest or None,
                    reason=args.reason)
    Path(args.out).write_text(SMP.canonical_json(receipt) + "\n", encoding="utf-8", newline="\n")
    print("shards completed: %s of %s" % (receipt["shards_completed"], receipt["shards_required"]))
    print("node ids: %d planned, %d executed, %d excluded"
          % (receipt["node_ids_expected"], receipt["node_ids_executed"], receipt["node_ids_excluded"]))
    print("PRE_EXISTING %d  TRUE_NEW %d"
          % (len(receipt["pre_existing_failures"]), len(receipt["true_new_failures"])))
    print("completeness: %s" % ("OK" if receipt["node_completeness"]["complete"] else
                                receipt["node_completeness"]["problems"][:3]))
    print("RESULT: %s" % receipt["result"])
    return 0 if receipt["result"] == "PASS" else 1


def _head() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
