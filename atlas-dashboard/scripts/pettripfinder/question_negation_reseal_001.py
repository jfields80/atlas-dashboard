"""PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001 -- reseal ONLY the corrected live markets.

    python -m scripts.pettripfinder.question_negation_reseal_001 --live-tree C:/t/qn_base-wt --work C:/t/qnf [--write]

WHY NOT ``registration_release_lane seal``
------------------------------------------
The lane seals a JOINING market and refuses a live one ("already participates in the live release"). These seven
markets are live and stay live; what moved is sixteen rows inside them. So this module runs the lane's own steps --
``market_package_writer.inputs_from_committed_market`` (zone REGISTERED_LIVE), the package sealed TWICE and required
to agree, ``first_party_binding.evaluate_package``, ``fast_release_lane.run_fast_lane`` (rules A-O, J and K
executed) and ``release_index.compare`` -- with a CORRECTION delta instead of a joining one: the profiles, routes and
verified-no-pets the market loses or changes, derived by the release index from the live market and the resealed
package, never typed. Every other market is untouched.

WHICH "LIVE"
------------
``release_index.live_index`` derives the live index from the committed tree and checks it against the live record's
counts. After the correction the committed tree is AHEAD of production, so read here it would (rightly) report the
mismatch. The live index is therefore derived in a checkout whose launch-package, deploy and script trees are
byte-identical to the data the live bundle was BUILT FROM -- the live record's own ``source_commit`` --
(``--live-tree``, verified before use): that is exactly
production's authority, and ``live_index`` must return no problem there.

WHAT IT WRITES (``--write``)
----------------------------
  markets/packages/<m>/pkg-<m>-<digest16>.json         the resealed package (canonical directory)
  <receipts>/<m>/...                                   the FAST receipt (canonical directory)
  tests/pettripfinder/pins/market_state.json           each market's OWN block, re-derived from its package and
                                                       cross-held to its contract (``write_pin_block(replace=True)``)
  markets/reports/question_negation_reseal_001.json    the report
"""
from __future__ import annotations

import argparse
import json
import pickle
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

_DASH = Path(__file__).resolve().parents[2]
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import fast_release_lane as FL  # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
from scripts.pettripfinder import market_package_writer as W  # noqa: E402
from scripts.pettripfinder import registration_release_lane as LANE  # noqa: E402
from scripts.pettripfinder import release_index as RI  # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP  # noqa: E402

WORK_ORDER = "PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001"
PKG = _DASH / "launch_packages" / "pettripfinder"
LEDGER = PKG / "markets" / "reports" / "question_negation_live_correction_001.json"
REPORT = PKG / "markets" / "reports" / "question_negation_reseal_001.json"
#: the market data the live bundle was built from. The commit is the live record's own ``source_commit`` (its
#: built-from commit), read at run time -- never typed here. Reports are excluded: a deploy order adds reports and
#: records after the build, and neither is an input to it.
LIVE_DATA_PATHS = ("atlas-dashboard/launch_packages", ":(exclude)atlas-dashboard/launch_packages/pettripfinder/markets/reports",
                   "atlas-dashboard/deploy/netlify/release_contracts",
                   "atlas-dashboard/deploy/netlify/launch_participation.json")

_PICKLE_LIVE = r"""
import pickle, sys
sys.path.insert(0, '.')
from scripts.pettripfinder import release_index as RI
live = RI.live_index()
pickle.dump(live, open(sys.argv[1], 'wb'))
"""


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root)] + list(args), capture_output=True, text=True,
                          check=True).stdout.strip()


def live_from_tree(live_tree: Path, scratch: Path):
    """The CURRENT VERIFIED LIVE index, derived in a checkout whose market data is proven identical to the data
    the live bundle was built from."""
    live_tree = Path(live_tree)
    if _git(live_tree, "status", "--porcelain"):
        raise SystemExit("%s is not clean" % live_tree)
    scratch.mkdir(parents=True, exist_ok=True)
    out = scratch / "live_index.pkl"
    subprocess.run([sys.executable, "-c", _PICKLE_LIVE, str(out)], cwd=str(live_tree / "atlas-dashboard"),
                   check=True)
    live = pickle.loads(out.read_bytes())
    idx, state, problems = live
    if problems:
        raise SystemExit("CURRENT_VERIFIED_LIVE could not be established in %s: %s" % (live_tree, problems[:3]))
    diff = _git(live_tree, "diff", "--name-only", state.source_commit, "HEAD", "--", *LIVE_DATA_PATHS)
    if diff:
        raise SystemExit("%s's market data differs from the live build source %s in %s"
                         % (live_tree, state.source_commit, diff.splitlines()[:3]))
    return live, OrderedDict([("live_tree_head", _git(live_tree, "rev-parse", "HEAD")),
                              ("live_built_from_commit", state.source_commit),
                              ("market_data_identical_to_live_build_source", list(LIVE_DATA_PATHS)),
                              ("live_deploy_id", state.deploy_id), ("live_index_digest", idx.digest()),
                              ("markets", len(idx.participating)), ("profiles", idx.total_profiles)])


def correction_delta(market_id, live_market, package_market, ledger_rows):
    """What the market loses or changes, measured between the live index and the resealed package's index."""
    lp, pp = live_market.profiles, package_market.profiles
    live_routes, pkg_routes = set(live_market.routes), set(package_market.routes)
    refused = sum(1 for r in ledger_rows if r["action"] == "REFUSE")
    return OrderedDict((
        ("market_id", market_id),
        ("add_property_ids", sorted(set(pp) - set(lp))),
        ("update_property_ids", sorted(k for k in set(pp) & set(lp) if pp[k] != lp[k])),
        ("remove_property_ids", sorted(set(lp) - set(pp))),
        ("add_routes", sorted(pkg_routes - live_routes)),
        ("change_routes", []),
        ("remove_routes", sorted(live_routes - pkg_routes)),
        ("expected_profile_delta", len(pp) - len(lp)),
        ("expected_verified_no_pets_delta", refused),
        ("expected_market_count_delta", 0),
        ("expected_participation_delta", []),
        ("correction", OrderedDict((
            ("work_order", WORK_ORDER),
            ("ledger", LEDGER.relative_to(_DASH).as_posix()),
            ("rows", [OrderedDict((("identity_key", r["identity_key"]), ("action", r["action"])))
                      for r in ledger_rows]),
            ("why", "a live market stays live; the repaired first-party reader moved these rows out of "
                    "acceptance, and this delta states exactly what the market loses or changes"))),
         ),
    ))


def _seal(market_id, parent, source_sha, sealed_at, delta):
    inputs = W.inputs_from_committed_market(market_id, execution_zone=SMP.ZONE_REGISTERED_LIVE,
                                            intended_delta=delta or OrderedDict((("market_id", market_id),)),
                                            parent_live_state=parent, source_sha=source_sha)
    return inputs, W.build_sealed_package(inputs, sealed_at=sealed_at)


def reseal(market_id, live, rows, *, source_sha, sealed_at, work, write):
    idx, state, _p = live
    parent = LANE.parent_from_live(live)
    _i, provisional = _seal(market_id, parent, source_sha, sealed_at, None)
    delta = correction_delta(market_id, idx.markets[market_id],
                             RI.index_from_package(provisional, participating=True), rows)
    _i, package = _seal(market_id, parent, source_sha, sealed_at, delta)
    _i, again = _seal(market_id, parent, source_sha, sealed_at, delta)
    reproducible = package["package_digest"] == again["package_digest"]
    if not reproducible:
        raise SystemExit("%s: PACKAGE_REPRODUCIBLE = NO" % market_id)
    gate = FPB.evaluate_package(package)
    package_index = RI.index_from_package(package, participating=True)
    candidate = RI.compose(idx, package_index, participates=True)
    diff = RI.compare(idx, candidate, package_market=market_id, intended_delta=package["intended_delta"])
    out = OrderedDict((
        ("market_id", market_id), ("package_id", package["package_id"]),
        ("package_digest", package["package_digest"]), ("PACKAGE_REPRODUCIBLE", "YES"),
        ("intended_delta", OrderedDict((k, v) for k, v in delta.items() if k != "correction")),
        ("first_party_gate", OrderedDict((("records_evaluated", gate["records_evaluated"]),
                                          ("eligible", gate["eligible"]), ("ineligible", gate["ineligible"]),
                                          ("passed", gate["passed"])))),
        ("release_diff_passed", diff["passed"]), ("release_diff_findings", diff["findings"]),
        ("candidate_profiles", candidate.total_profiles),
    ))
    if not write:
        return out, package
    package_path = SMP.write_sealed(package)
    receipt = FL.run_fast_lane(package, work_dir=Path(work) / market_id, live=live, participates=True)
    receipt_path = FL.write_receipt(receipt)
    eligible = [Path(p).name for p in FL.eligible_receipts(market_id, package["package_digest"])]
    results = receipt["RESULTS"]
    artifacts = receipt.get("ARTIFACT_DIGESTS") or {}
    j = results.get("J", {}).get("detail") or {}
    rel = lambda p: Path(p).resolve().relative_to(_DASH).as_posix()  # noqa: E731
    out.update(OrderedDict((
        ("package_path", rel(package_path)),
        ("fast_receipt", rel(receipt_path)),
        ("FAST_DATA_ONLY_RELEASE_ELIGIBLE", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
        ("rules", OrderedDict((r, res["status"]) for r, res in results.items())),
        ("rules_passed", sum(1 for res in results.values() if res["status"] == FL.PASS)),
        ("rules_total", len(results)),
        ("failed_rules", receipt["FAILED_RULES"]), ("unknown_rules", receipt["UNKNOWN_RULES"]),
        ("determinism", receipt["DETERMINISM_RESULT"]),
        ("J", OrderedDict((("file_count", j.get("file_count")), ("html_count", j.get("html_count")),
                           ("bundle_sha256", j.get("bundle_sha256"))))),
        ("market_bundle_a", artifacts.get("changed_market_bundle_sha256_a")),
        ("market_bundle_b", artifacts.get("changed_market_bundle_sha256_b")),
        ("receipt_defects", FL.receipt_output_defects(receipt)),
        ("receipt_currently_eligible", Path(receipt_path).name in eligible),
    )))
    ok = (out["rules_passed"] == out["rules_total"] and not out["receipt_defects"]
          and out["receipt_currently_eligible"] and out["market_bundle_a"] == out["market_bundle_b"]
          and diff["passed"] and gate["passed"])
    out["RESEAL_PASS"] = ok
    if ok:
        block = LANE.pin_block_from_package(package, market_id, WORK_ORDER)
        out["market_state_pin"] = LANE.write_pin_block(market_id, block, WORK_ORDER, replace=True)
    return out, package


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-tree", required=True)
    ap.add_argument("--work", required=True, help="a SHORT ABSOLUTE forward-slash scratch dir (C:/t/x)")
    ap.add_argument("--market", action="append", help="limit to these markets (default: every ledger market)")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    if "\t" in args.work or not args.work.startswith(("C:/", "/")):
        raise SystemExit("--work must be a short absolute forward-slash path, got %r" % args.work)
    if _git(_DASH, "status", "--porcelain", "--", "launch_packages", "deploy"):
        raise SystemExit("the market data is not committed; a sealed package is sealed from a commit")
    source_sha = _git(_DASH, "rev-parse", "HEAD")
    live, live_doc = live_from_tree(Path(args.live_tree), Path(args.work))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    sealed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = OrderedDict((("schema", "ptf-live-correction-reseal/1.0"), ("work_order", WORK_ORDER),
                          ("created_from_source_sha", source_sha), ("sealed_at", sealed_at),
                          ("current_verified_live", live_doc), ("markets", OrderedDict())))
    if REPORT.is_file() and args.write:
        prior = json.loads(REPORT.read_text(encoding="utf-8"))
        report["markets"].update(prior.get("markets") or {})
    for market_id, entry in ledger["markets"].items():
        if args.market and market_id not in args.market:
            continue
        out, _pkg = reseal(market_id, live, entry["rows"], source_sha=source_sha, sealed_at=sealed_at,
                           work=args.work, write=args.write)
        report["markets"][market_id] = out
        print(market_id, json.dumps(OrderedDict((k, out.get(k)) for k in (
            "package_id", "PACKAGE_REPRODUCIBLE", "release_diff_passed", "rules_passed", "rules_total",
            "failed_rules", "unknown_rules", "determinism", "receipt_currently_eligible", "RESEAL_PASS"))))
        for f in out["release_diff_findings"][:5]:
            print("   finding", f)
    if args.write:
        REPORT.write_bytes((json.dumps(report, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("report", REPORT.relative_to(_DASH).as_posix())
    return 0 if all(m.get("RESEAL_PASS", not args.write) for m in report["markets"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
