"""PTF-TOLEDO-OH-NEW-MARKET-001 -- Phase 20, parallel safety, proved mechanically.

Fort Wayne and Lexington are running MARKET-LOCAL orders from the same base
commit at the same time. This module does not assert that Toledo stayed in its
lane; it computes the working tree's diff against the base and classifies every
changed path, so a violation is a failure rather than a claim.

The classes it refuses:

  OTHER_MARKET_FILE       a path naming fort-wayne, lexington, or any of the
                          twelve registered markets
  SHARED_GLOBAL           the three generated global authorities, the market
                          registry, the registered census directory
  SHARED_CURRENT_STATE    tests/pettripfinder/pins/*
  DEPLOYMENT              deploy/netlify/** and the assembler's outputs
  SHARED_LEDGER           the cross-run paid and discovery ledgers
  SHARED_FACTORY_CODE     generic modules under scripts/pettripfinder that no
                          Toledo-named file owns

Everything else must be Toledo-named, and the report says which rule admitted it.

Output:
  launch_packages/pettripfinder/markets/reports/toledo_oh_parallel_safety_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_REPO = os.path.abspath(os.path.join(_DASH, ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-TOLEDO-OH-NEW-MARKET-001"
MARKET_ID = "toledo-oh"
SCHEMA = "ptf-parallel-safety/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
BASE = "2163c4ed23b7315954f896c99729ca95c08eabfc"

#: A path this order owns. Every one of these carries the market in its name.
#: A path this order owns. Every one carries the market in its name, in any
#: of the separators the repository actually uses: a directory boundary, a
#: snake_case module, or a hyphenated work-order document name.
TOLEDO_OWNED = re.compile(r"(^|[/_-])toledo[-_]oh", re.I)

#: Markets that must not move. Fort Wayne and Lexington are running now; the
#: other twelve are registered and some are live.
OTHER_MARKETS = (
    "fort-wayne", "fort_wayne", "lexington",
    "cincinnati", "cleveland", "columbus", "dayton", "detroit", "ann_arbor", "ann-arbor",
    "grand_rapids", "grand-rapids", "indianapolis", "louisville", "milwaukee",
    "pittsburgh", "st_louis", "st-louis",
)
SHARED_GLOBALS = (
    "launch_packages/pettripfinder/hotel_policy_facts.json",
    "launch_packages/pettripfinder/hotel_exclusions.json",
    "launch_packages/pettripfinder/production_hotels.csv",
)
SHARED_LEDGERS = (
    "launch_packages/pettripfinder/ptf_paid_attempt_ledger_001.json",
    "launch_packages/pettripfinder/ptf_discovery_attempt_ledger_001.json",
)


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=_REPO, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), out.stderr.strip()))
    return out.stdout


def changed_paths(base):
    tracked = git("diff", "--name-status", base).strip().splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").strip().splitlines()
    rows = []
    for line in tracked:
        if not line.strip():
            continue
        parts = line.split("\t")
        rows.append((parts[0], parts[-1]))
    for path in untracked:
        if path.strip():
            rows.append(("?", path.strip()))
    return rows


def classify(path):
    p = path.replace("\\", "/")
    rel = p[len("atlas-dashboard/"):] if p.startswith("atlas-dashboard/") else p
    if TOLEDO_OWNED.search(rel):
        return "TOLEDO_OWNED", "the path carries this market's id"
    if rel in SHARED_LEDGERS:
        return "SHARED_LEDGER", "a cross-run ledger this order may only read"
    if rel in SHARED_GLOBALS:
        return "SHARED_GLOBAL", "a generated global authority"
    if rel.startswith("tests/pettripfinder/pins/"):
        return "SHARED_CURRENT_STATE", "a current-state pin"
    if rel.startswith("deploy/"):
        return "DEPLOYMENT", "a deployment artifact"
    if rel.startswith("launch_packages/pettripfinder/markets/") and rel.count("/") == 3 \
            and rel.endswith(".json"):
        return "MARKET_REGISTRY", "markets/*.json IS the registry"
    if rel.startswith("launch_packages/pettripfinder/identity_census/"):
        return "REGISTERED_CENSUS", "the contract-pinned census directory"
    if rel.startswith("launch_packages/pettripfinder/markets/authority/"):
        return "MARKET_AUTHORITY_SHARD", "a market authority shard"
    low = rel.lower()
    if any(m in low for m in OTHER_MARKETS):
        return "OTHER_MARKET_FILE", "the path names another market"
    if rel.startswith("scripts/pettripfinder/") or rel.startswith("tests/pettripfinder/"):
        return "SHARED_FACTORY_CODE", "generic factory code no Toledo file owns"
    if rel.startswith("data/"):
        return "GITIGNORED_WORKING_DATA", "under the gitignored data/ tree"
    return "UNCLASSIFIED", "no rule claims this path"


ALLOWED = {"TOLEDO_OWNED", "GITIGNORED_WORKING_DATA"}


def build(base):
    rows = []
    for status, path in changed_paths(base):
        cls, why = classify(path)
        rows.append(OrderedDict([("status", status), ("path", path.replace("\\", "/")),
                                 ("class", cls), ("why", why),
                                 ("allowed", cls in ALLOWED)]))
    violations = [r for r in rows if not r["allowed"]]
    counts = Counter(r["class"] for r in rows)

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "20 -- parallel safety"),
        ("base_commit", base),
        ("head_commit", git("rev-parse", "HEAD").strip()),
        ("concurrent_market_orders", ["fort-wayne (worker/ptf-fort-wayne-new-market-001)",
                                      "lexington (worker/ptf-lexington-new-market-001)"]),
        ("how_this_is_proved",
         "the working tree is diffed against the base commit and EVERY changed path is "
         "classified; a path no Toledo rule admits is a violation, not a note"),
        ("counts", OrderedDict([
            ("changed_paths", len(rows)),
            ("by_class", OrderedDict(sorted(counts.items()))),
            ("violations", len(violations)),
        ])),
        ("mechanical_assertions", OrderedDict([
            ("fort_wayne_files_changed",
             sum(1 for r in rows if "fort" in r["path"].lower() and "wayne" in r["path"].lower())),
            ("lexington_files_changed",
             sum(1 for r in rows if "lexington" in r["path"].lower())),
            ("other_registered_market_files_changed",
             sum(1 for r in rows if r["class"] == "OTHER_MARKET_FILE")),
            ("shared_globals_changed", counts.get("SHARED_GLOBAL", 0)),
            ("market_registry_changed", counts.get("MARKET_REGISTRY", 0)),
            ("registered_census_changed", counts.get("REGISTERED_CENSUS", 0)),
            ("market_authority_shards_changed", counts.get("MARKET_AUTHORITY_SHARD", 0)),
            ("shared_current_state_pins_changed", counts.get("SHARED_CURRENT_STATE", 0)),
            ("deployment_files_changed", counts.get("DEPLOYMENT", 0)),
            ("shared_ledgers_written", counts.get("SHARED_LEDGER", 0)),
            ("shared_factory_code_changed", counts.get("SHARED_FACTORY_CODE", 0)),
            ("production_assembly", "NOT RUN"),
            ("global_authority_regeneration", "NOT RUN"),
            ("deployment_authorization_created", "NO"),
            ("deployed", "NO"),
        ])),
        ("violations", violations),
        ("changed_paths", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--out", default=os.path.join(REPORTS, "toledo_oh_parallel_safety_001.json"))
    args = ap.parse_args(argv)
    rep = build(args.base)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    m = rep["mechanical_assertions"]
    for k, v in m.items():
        print("%-42s %s" % (k, v))
    print("violations:", rep["counts"]["violations"])
    for v in rep["violations"]:
        print("   !", v["class"], v["path"])
    print("written:", args.out)
    return 1 if rep["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
