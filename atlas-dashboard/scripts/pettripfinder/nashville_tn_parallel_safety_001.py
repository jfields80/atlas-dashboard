"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phase 20, parallel safety, proved mechanically.

Detroit owns the serialized launch lane and other market orders share this
repository. This module does not ASSERT that Nashville stayed in its lane; it
computes the working tree's diff against the base commit and classifies every
changed path, so a violation is a failure rather than a claim.

The classes it refuses:

  OTHER_MARKET_FILE       a path naming detroit, lexington, fort-wayne or any
                          of the eleven live markets
  SHARED_GLOBAL           the three generated global authorities, the market
                          registry, the registered census directory
  SHARED_CURRENT_STATE    tests/pettripfinder/pins/*
  DEPLOYMENT              deploy/netlify/** and the assembler's outputs
  SHARED_LEDGER           the cross-run paid and discovery ledgers
  SHARED_FACTORY_CODE     generic modules under scripts/pettripfinder that no
                          Nashville-named file owns
  SHARED_GENERATED_REPORT_REWRITTEN_WITHOUT_PROOF
                          the one suite-derived inventory pin, rewritten
                          without the delta proof that permits it

Everything else must be Nashville-named, and the report says which rule
admitted it.

Output:
  launch_packages/pettripfinder/markets/reports/nashville_tn_parallel_safety_001.json
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

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
SCHEMA = "ptf-parallel-safety/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
BASE = "d335c509e8e4b0f54796d07c4bd4abdff00cb801"

#: A path this order owns. Every one of these carries the market in its name.
#: A path this order owns. Every one carries the market in its name, in any
#: of the separators the repository actually uses: a directory boundary, a
#: snake_case module, or a hyphenated work-order document name.
NASHVILLE_OWNED = re.compile(r"(^|[/_-])nashville[-_]tn", re.I)

#: Markets that must not move. Detroit holds the serialized launch lane;
#: Lexington and Fort Wayne are shadow markets; the rest are registered and
#: eleven of them are live.
OTHER_MARKETS = (
    "fort-wayne", "fort_wayne", "lexington",
    "cincinnati", "cleveland", "columbus", "dayton", "detroit", "ann_arbor", "ann-arbor",
    "grand_rapids", "grand-rapids", "indianapolis", "louisville", "milwaukee",
    "pittsburgh", "st_louis", "st-louis", "toledo",
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

#: The ONE shared file this order is allowed to rewrite, and only under proof.
#: It is a GENERATED report that describes what the test suite contains, and a
#: test holds it to what the suite reproduces. Adding a market's own gate module
#: moves it by construction. The allowance is not a judgement call: the
#: companion report must say the delta was exactly this order's own modules --
#: nothing removed, nothing altered, every addition Nashville-named -- and if it
#: does not, this classifies as a violation like any other shared write.
SUITE_INVENTORY_PIN = "launch_packages/pettripfinder/reports/factory_throughput_001_test_inventory.json"
REPIN_PROOF = ("launch_packages/pettripfinder/markets/reports/"
               "nashville_tn_test_inventory_repin_003.json")


def repin_proof_holds():
    """Did the re-pin prove its delta was only this order's own modules?"""
    path = os.path.join(_DASH, REPIN_PROOF)
    if not os.path.exists(path):
        return False, "no re-pin proof report exists"
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return False, "the re-pin proof report is unreadable (%r)" % exc
    proof = doc.get("proof") or {}
    ok = (proof.get("proof_holds") is True
          and not proof.get("modules_removed")
          and not proof.get("modules_altered")
          and not proof.get("modules_added_that_this_order_does_not_own")
          and bool(proof.get("modules_added")))
    return ok, ("the re-pin proved its delta is exactly %s"
                % proof.get("modules_added") if ok
                else "the re-pin proof does not hold")


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
    if NASHVILLE_OWNED.search(rel):
        return "NASHVILLE_OWNED", "the path carries this market's id"
    if rel == SUITE_INVENTORY_PIN:
        ok, why = repin_proof_holds()
        return ("SUITE_INVENTORY_REPINNED_UNDER_PROOF" if ok
                else "SHARED_GENERATED_REPORT_REWRITTEN_WITHOUT_PROOF"), why
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
        return "SHARED_FACTORY_CODE", "generic factory code no Nashville file owns"
    if rel.startswith("data/"):
        return "GITIGNORED_WORKING_DATA", "under the gitignored data/ tree"
    return "UNCLASSIFIED", "no rule claims this path"


ALLOWED = {"NASHVILLE_OWNED", "GITIGNORED_WORKING_DATA",
           "SUITE_INVENTORY_REPINNED_UNDER_PROOF"}


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
        ("serialized_lane_owner", "detroit-ann-arbor-mi (worker/ptf-detroit-launch-001)"),
        ("other_shadow_markets", ["lexington-ky (worker/ptf-lexington-new-market-001)",
                                  "fort-wayne-in (worker/ptf-fort-wayne-new-market-001)"]),
        ("how_this_is_proved",
         "the working tree is diffed against the base commit and EVERY changed path is "
         "classified; a path no Nashville rule admits is a violation, not a note"),
        ("counts", OrderedDict([
            ("changed_paths", len(rows)),
            ("by_class", OrderedDict(sorted(counts.items()))),
            ("violations", len(violations)),
        ])),
        ("mechanical_assertions", OrderedDict([
            ("detroit_files_changed",
             sum(1 for r in rows if "detroit" in r["path"].lower()
                 or "ann_arbor" in r["path"].lower() or "ann-arbor" in r["path"].lower())),
            ("lexington_files_changed",
             sum(1 for r in rows if "lexington" in r["path"].lower())),
            ("fort_wayne_files_changed",
             sum(1 for r in rows if "fort" in r["path"].lower() and "wayne" in r["path"].lower())),
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
            ("shared_generated_reports_rewritten_without_proof",
             counts.get("SHARED_GENERATED_REPORT_REWRITTEN_WITHOUT_PROOF", 0)),
            ("suite_inventory_repinned_under_proof",
             counts.get("SUITE_INVENTORY_REPINNED_UNDER_PROOF", 0)),
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
    ap.add_argument("--out", default=os.path.join(REPORTS, "nashville_tn_parallel_safety_001.json"))
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
