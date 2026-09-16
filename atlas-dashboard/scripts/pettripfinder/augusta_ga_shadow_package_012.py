"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 26: the SHADOW sealed
package (cloned from the Savannah GA helper; Augusta tokens). Mission: Do not
register, do not touch launch_participation.json, do not create a
production candidate, do not deploy.

Stages a repository-shaped launch-package tree under
``markets/staging/augusta-ga/``, seals it TWICE through
``market_package_writer.inputs_from_committed_market`` with
``execution_zone = SHADOW_UNTIL_REGISTERED`` against the CURRENT live
parent, refuses unless both digests agree, then runs the FAST lane (rules
A-O) over it. Writes the package, the receipt and a report ONLY under
``markets/staging/augusta-ga/``.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as REG_PAL  # noqa: E402
from scripts.pettripfinder import fast_release_lane as FL             # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB          # noqa: E402
from scripts.pettripfinder import market_authority as MA              # noqa: E402
from scripts.pettripfinder import market_package_writer as W          # noqa: E402
from scripts.pettripfinder import market_registration_cli as REG      # noqa: E402
from scripts.pettripfinder import registration_release_lane as LANE   # noqa: E402
from scripts.pettripfinder import release_index as RI                 # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP        # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = _DASH / "launch_packages" / "pettripfinder"
STAGING = PKG / "markets" / "staging" / MARKET_ID
LP = STAGING / "launch_package"
REPORT = PKG / "markets" / "reports" / "augusta_ga_shadow_package_012.json"
PROPOSED_MARKET = PKG / "markets" / "proposed" / ("%s.json" % MARKET_ID)
PROPOSED_CENSUS = PKG / "identity_census_proposed" / ("%s.json" % MARKET_ID)
AUTHORITY = STAGING / "augusta_ga_proposed_authority_011.json"
SEALED_AT = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def stage_tree():
    (LP / "markets").mkdir(parents=True, exist_ok=True)
    (LP / "identity_census").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROPOSED_MARKET, LP / "markets" / ("%s.json" % MARKET_ID))
    shutil.copyfile(PROPOSED_CENSUS, LP / "identity_census" / ("%s.json" % MARKET_ID))

    authority = REG.load_authority(AUTHORITY)
    census = REG.census_by_key(PROPOSED_CENSUS)
    policy = _read(LP / ("hotel_policy_facts_%s.json" % MARKET_ID))
    package_records = {h.get("identity_key") or h["key"]: h for h in policy.get("hotels") or ()}
    rows = REG.seed_rows(authority, census, MARKET_ID, package_records)
    exclusions = REG.exclusion_records(authority, census, MARKET_ID)
    if len(rows) != authority["pet_friendly_count"] or len(exclusions) != authority["verified_no_pets_count"]:
        raise SystemExit("the staged shard does not state the authority's counts")
    shard = LP / "markets" / "authority" / MARKET_ID
    shard.mkdir(parents=True, exist_ok=True)
    written = OrderedDict()
    for name, text in (
            (getattr(MA, "SEED_SHARD_NAME", "seed_businesses.csv"), MA.render_seed_csv(rows)),
            ("hotel_exclusions.json", MA.render_json(MA.build_exclusions_shard(MARKET_ID, exclusions))),
            ("identity_routing.json", MA.render_json(MA.build_routing_shard(MARKET_ID, []))),
            ("affiliate_destinations.json", MA.render_json(REG.affiliate_shard(MARKET_ID)))):
        (shard / name).write_text(text, encoding="utf-8", newline="\n")
        written[name] = len(text)
    return written


def shadow_joining_delta(inputs):
    from scripts.pettripfinder.markets.contract import parse_market
    delta = LANE.joining_delta(inputs)
    market = parse_market(dict(inputs.market))
    profiles = RI._entries(market, inputs.pet_friendly_records, inputs.seed_rows)
    delta["add_property_ids"] = sorted(profiles)
    delta["expected_profile_delta"] = len(profiles)
    delta["expected_verified_no_pets_delta"] = len(inputs.verified_no_pets_records)
    delta["shadow_until_registered"] = (
        "declared against a live release that carries no index for this market; a future registration "
        "order's re-seal restates the delta through registration_release_lane.joining_delta")
    return delta


#: PTF-GENERIC-CROSS-RUN-PAID-ATTEMPT-LEDGER-001 reservations for the four
#: publication-grade evidence artifacts this market's pet_friendly records
#: depend on that were captured through the Firecrawl paid lane
#: (augusta_ga_firecrawl_acquisition_005), keyed by the artifact's own
#: content sha256 -- exactly what market_package_writer._reference looks up.
#: augusta_ga_firecrawl_ledger_reconciliation_013.py recorded these same
#: attempts in the shared ptf_paid_attempt_ledger_001.json.
_PAID_RESERVATIONS = {
    "bd09d92e60e67f4f9bc72e5a6932999d6a28699013d3d10252c2891b1a7f7c47": {
        "provider": "Firecrawl", "run_id": "augusta_ga_firecrawl_acquisition_005", "lane": "firecrawl",
        "attempt_id": REG_PAL.attempt_id(MARKET_ID, "augusta_ga_firecrawl_acquisition_005",
                                         "candlewood suites", "firecrawl"),
        "request_envelope_sha256": "2595d9c19993d48dd12eddfa90925b3a407dc6893cdf9b123657fb5f49482199",
    },
    "f7b3f96a0dad3dd08aaf4f3a29f4cdf369ef300428618aa50af22c8cd7916654": {
        "provider": "Firecrawl", "run_id": "augusta_ga_firecrawl_acquisition_005", "lane": "firecrawl",
        "attempt_id": REG_PAL.attempt_id(MARKET_ID, "augusta_ga_firecrawl_acquisition_005",
                                         "holiday inn express", "firecrawl"),
        "request_envelope_sha256": "aaaab35bd3247562492a3fb1a6e68341876f5a2d900612ebe4bb2ef65b383c3e",
    },
    "b7092df9857ddeace653589e3cf2b9e10676ebd3ae558e3b157cc8c04ae7125d": {
        "provider": "Firecrawl", "run_id": "augusta_ga_firecrawl_acquisition_005", "lane": "firecrawl",
        "attempt_id": REG_PAL.attempt_id(MARKET_ID, "augusta_ga_firecrawl_acquisition_005",
                                         "staybridge suites augusta", "firecrawl"),
        "request_envelope_sha256": "7b8010515a7c1659f535392c265946993899b8884a1b4bac88899aa4aebb22a7",
    },
    "d464382a255a0c2a853579b061833aa91d386c421a2fedbd8329bcd4496bf368": {
        "provider": "Firecrawl", "run_id": "augusta_ga_firecrawl_acquisition_005", "lane": "firecrawl",
        "attempt_id": REG_PAL.attempt_id(MARKET_ID, "augusta_ga_firecrawl_acquisition_005",
                                         "rodeway inn", "firecrawl"),
        "request_envelope_sha256": "bbc30a67eb9e8fd1cf3913d135228635d0e8edfacee0d7f421c98d732e3fbd5d",
    },
}


def _package(parent, source_sha):
    inputs = W.inputs_from_committed_market(
        MARKET_ID, execution_zone=SMP.ZONE_SHADOW_UNTIL_REGISTERED,
        intended_delta=OrderedDict((("market_id", MARKET_ID),)), parent_live_state=parent,
        launch_package=LP, source_sha=source_sha)
    inputs.intended_delta = shadow_joining_delta(inputs)
    inputs.paid_reservations = _PAID_RESERVATIONS
    return inputs, W.build_sealed_package(inputs, sealed_at=SEALED_AT)


def seal(source_sha, work_dir, write=True):
    t0 = time.monotonic()
    live = RI.live_index()
    idx, state, problems = live
    if problems:
        raise SystemExit("CURRENT_VERIFIED_LIVE could not be established: %s" % problems[:3])
    if MARKET_ID in state.participating_markets:
        raise SystemExit("%s already participates in the live release" % MARKET_ID)
    parent = LANE.parent_from_live(live)
    inputs, package = _package(parent, source_sha)
    _inputs2, again = _package(parent, source_sha)
    reproducible = package["package_digest"] == again["package_digest"]
    if not reproducible:
        raise SystemExit("PACKAGE_REPRODUCIBLE = NO: %s vs %s" % (package["package_digest"], again["package_digest"]))
    out = OrderedDict([("package_digest", package["package_digest"]), ("package_id", package["package_id"]),
                       ("PACKAGE_REPRODUCIBLE_IN_PROCESS", "YES"),
                       ("dependency_input_digests", inputs.dependency_input_digests)])
    if not write:
        return out, package
    package_path = SMP.write_sealed(package, STAGING / "shadow_packages")
    gate = FPB.evaluate_package(package)
    receipt = FL.run_fast_lane(package, work_dir=Path(work_dir), live=live, participates=True)
    receipt_path = FL.write_receipt(receipt, STAGING / "shadow_receipts")
    rel = lambda p: Path(p).relative_to(_DASH).as_posix()  # noqa: E731
    results = receipt["RESULTS"]
    j = OrderedDict(results.get("J", {}).get("detail") or {})
    census = package["census"]
    partition = package["partition"]
    holds = OrderedDict()
    for row in census.get("non_admitted") or ():
        holds.setdefault(row.get("classification", "UNKNOWN"), []).append(OrderedDict([
            ("identity_key", row.get("identity_key")), ("canonical_name", row.get("canonical_name")),
            ("reason", (row.get("classification_reason") or "")[:300])]))
    out.update(OrderedDict([
        ("schema", "ptf-shadow-sealed-package-report/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("execution_zone", package["execution_zone"]),
        ("created_from_source_sha", package["created_from_source_sha"]),
        ("sealed_at", package["sealed_at"]),
        ("package_path", rel(package_path)), ("receipt_path", rel(receipt_path)),
        ("receipt_digest", receipt["RECEIPT_DIGEST"]),
        ("FAST_DATA_ONLY_RELEASE_ELIGIBLE", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
        ("fast_rules", OrderedDict((r, res["status"]) for r, res in results.items())),
        ("fast_rule_problems", OrderedDict((r, res.get("problems")) for r, res in results.items() if res.get("problems"))),
        ("unknown_rules", receipt["UNKNOWN_RULES"]), ("failed_rules", receipt["FAILED_RULES"]),
        ("determinism_result", receipt["DETERMINISM_RESULT"]),
        ("first_party_gate", OrderedDict((k, gate[k]) for k in ("records_evaluated", "eligible", "ineligible", "passed"))),
        ("build_input_key", OrderedDict([
            ("staged_input_digest", j.get("staged_input_digest")),
            ("changed_market_bundle_sha256", j.get("bundle_sha256")),
            ("contract_sha256", j.get("contract_sha256")),
            ("dependency_input_digests", inputs.dependency_input_digests)])),
        ("intended_delta", package["intended_delta"]),
        ("parent_live_state", package["parent_live_state"]),
        ("coverage_scorecard", package.get("coverage_scorecard")),
        ("unresolved_set", package.get("unresolved_rows")),
        ("partition_counts_by_state", OrderedDict(sorted(Counter(i["final_state"] for i in partition["items"]).items()))),
        ("hold_set_non_admitted_census_rows", holds),
        ("counts", OrderedDict([
            ("census", census.get("count")), ("pet_friendly_records", len(package["pet_friendly_records"])),
            ("verified_no_pets_records", len(package["verified_no_pets_records"])),
            ("unresolved_rows", len(package.get("unresolved_rows") or [])),
            ("declared_routes", len(package["intended_delta"].get("add_routes") or []))])),
        ("parent_binding",
         "parent_live_state names the CURRENT live release. Once any later market lands live, FAST rule N "
         "fails this package BY DESIGN; a future registration order re-seals the same committed inputs "
         "against that parent as a NEW package id. Nothing here is a production candidate, and no "
         "whole-site build was assembled."),
        ("nothing_registered", True), ("nothing_authorized", True), ("participation_untouched", True),
        ("pin_untouched", True), ("nothing_deployed", True),
        ("seconds", round(time.monotonic() - t0, 1)),
    ]))
    REPORT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out, package


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-sha", required=True)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("--digest-only", action="store_true")
    args = ap.parse_args(argv)
    if args.stage:
        print("staged:", dict(stage_tree()))
    out, package = seal(args.source_sha, args.work_dir, write=not args.digest_only)
    print("package :", out["package_id"], out["package_digest"], "reproducible-in-process",
          out["PACKAGE_REPRODUCIBLE_IN_PROCESS"])
    if not args.digest_only:
        print("fast    :", out["FAST_DATA_ONLY_RELEASE_ELIGIBLE"], dict(out["fast_rules"]))
        print("unknown :", out["unknown_rules"], "failed:", out["failed_rules"])
        for r, p in out["fast_rule_problems"].items():
            print("  %s: %s" % (r, str(p)[:400]))
        print("receipt :", out["receipt_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
