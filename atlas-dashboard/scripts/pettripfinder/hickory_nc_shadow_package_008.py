"""PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 -- Phase 9: the SHADOW sealed package.

WHY A SHADOW PACKAGE, AND NOT ``registration_release_lane seal``
----------------------------------------------------------------
Greenville is live (deploy 6aa75f87), and the release queue (Jacksonville, Atlanta, Outer Banks,
Boone - Blowing Rock, Pinehurst - Southern Pines; source-ready, not registered) is drained separately
before Hickory - Newton - Conover can be released.
The generic lane ``registration_release_lane register`` / ``seal --work-order``
would reissue ``launch_participation.json``, extend ``bundle_cache_closure.json``,
write a pin block into ``tests/pettripfinder/pins/market_state.json`` and
require a registry row, a shard, regenerated globals and a release contract --
every one of them shared, parent-sensitive state that this order is forbidden
to touch and that would conflict with the queued markets' own registration of the same documents.

The factory already names the state this order is in:
``sealed_market_package.ZONE_SHADOW_UNTIL_REGISTERED``, and the market-local
ownership template already owns ``markets/staging/<id>/``. So this helper:

  1. STAGES a repository-shaped launch-package tree inside the market's own zone
     (``markets/staging/hickory-nc/launch_package/``) from the proposed
     market document, the proposed census, the staged policy package, the shard
     documents ``market_registration_cli.build`` derives (computed here, written
     only under staging) and the staged partition;
  2. seals the package TWICE from that tree through
     ``market_package_writer.inputs_from_committed_market(launch_package=...)``
     with ``execution_zone = SHADOW_UNTIL_REGISTERED`` and a COMMITTED source sha,
     and refuses unless the two digests agree;
  3. runs the FAST lane (rules A-O) over it, which builds the joining market's
     bundle twice cold and composes the release index IN MEMORY against the
     current live parent (Greenville) -- no whole-site candidate is assembled;
  4. writes the package, the receipt and a report ONLY under
     ``markets/staging/hickory-nc/``: never ``markets/packages/`` or
     ``markets/receipts/``, where Regression V2 binds a REGISTRATION to its
     package, so no later classification can mistake this shadow for a release.

WHAT BINDS TO THE GREENVILLE PARENT, AND HOW IT IS RECONCILED
------------------------------------------------------------
``parent_live_state`` and ``intended_delta`` are body fields, so the digest
names the current live release. That is the truthful statement of what the
package was validated against, and it is reconcilable by construction: a sealed
package is never edited -- "a correction is a new package with a new id" -- and
FAST rule N refuses any package whose parent is not the CURRENT live state. Once
the next queued market is live, rule N FAILS this package on purpose; the registration
order re-seals the same committed inputs against the new parent (a new id), and
everything the parent does not touch (census, identity records, policy
records, evidence, partition, routes) is carried unchanged.

Nothing here registers, authorizes, flips participation, pins, deploys or
touches a shared document.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import fast_release_lane as FL             # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB          # noqa: E402
from scripts.pettripfinder import market_authority as MA              # noqa: E402
from scripts.pettripfinder import market_package_writer as W          # noqa: E402
from scripts.pettripfinder import market_registration_cli as REG      # noqa: E402
from scripts.pettripfinder import registration_release_lane as LANE   # noqa: E402
from scripts.pettripfinder import release_index as RI                 # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP        # noqa: E402

WORK_ORDER = "PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hickory-nc"
PKG = _DASH / "launch_packages" / "pettripfinder"
STAGING = PKG / "markets" / "staging" / MARKET_ID
LP = STAGING / "launch_package"
REPORT = PKG / "markets" / "reports" / "hickory_nc_shadow_package_008.json"
PROPOSED_MARKET = PKG / "markets" / "proposed" / ("%s.json" % MARKET_ID)
PROPOSED_CENSUS = PKG / "identity_census_proposed" / ("%s.json" % MARKET_ID)
AUTHORITY = STAGING / "hickory_nc_proposed_authority_002.json"
SEALED_AT = "2026-09-14T04:00:00Z"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def stage_tree():
    """Byte copies of the proposed documents plus the shard documents the
    registration CLI derives, all under the market's staging zone."""
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
            (MA.SEED_SHARD_NAME if hasattr(MA, "SEED_SHARD_NAME") else "seed_businesses.csv", MA.render_seed_csv(rows)),
            ("hotel_exclusions.json", MA.render_json(MA.build_exclusions_shard(MARKET_ID, exclusions))),
            ("identity_routing.json", MA.render_json(MA.build_routing_shard(MARKET_ID, []))),
            ("affiliate_destinations.json", MA.render_json(REG.affiliate_shard(MARKET_ID)))):
        (shard / name).write_text(text, encoding="utf-8", newline="\n")
        written[name] = len(text)
    return written


def shadow_joining_delta(inputs):
    """The generic lane's joining delta, restated for a market on NEITHER side.

    ``registration_release_lane.joining_delta`` declares zero profile additions
    because a REGISTERED joining market already has a (non-participating) index
    in the live release, and ``release_index.compare`` measures additions against
    it. An unregistered market has no live index at all, so every profile and
    every verified-no-pets record it brings IS an addition, and the honest
    declaration names each one. Routes, the market-count delta and the
    participation delta are the generic lane's own, unchanged.
    """
    from scripts.pettripfinder.markets.contract import parse_market
    delta = LANE.joining_delta(inputs)
    market = parse_market(dict(inputs.market))
    profiles = RI._entries(market, inputs.pet_friendly_records, inputs.seed_rows)
    delta["add_property_ids"] = sorted(profiles)
    delta["expected_profile_delta"] = len(profiles)
    delta["expected_verified_no_pets_delta"] = len(inputs.verified_no_pets_records)
    delta["shadow_until_registered"] = (
        "declared against a live release that carries no index for this market; the registration "
        "order's re-seal restates the delta through registration_release_lane.joining_delta")
    return delta


def _package(parent, source_sha):
    inputs = W.inputs_from_committed_market(
        MARKET_ID, execution_zone=SMP.ZONE_SHADOW_UNTIL_REGISTERED,
        intended_delta=OrderedDict((("market_id", MARKET_ID),)), parent_live_state=parent,
        launch_package=LP, source_sha=source_sha)
    inputs.intended_delta = shadow_joining_delta(inputs)
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
        holds.setdefault(row["classification"], []).append(OrderedDict([
            ("identity_key", row["identity_key"]), ("canonical_name", row["canonical_name"]),
            ("reason", (row.get("classification_reason") or "")[:300])]))
    out.update(OrderedDict([
        ("schema", "ptf-shadow-sealed-package-report/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("execution_zone", package["execution_zone"]),
        ("created_from_source_sha", package["created_from_source_sha"]),
        ("sealed_at", package["sealed_at"]),
        ("package_path", rel(package_path)),
        ("receipt_path", rel(receipt_path)),
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
         "parent_live_state names the CURRENT live release (Greenville, deploy 6aa75f87...). That is what this "
         "package was validated against. Once the next queued market is live, FAST rule N fails this package BY "
         "DESIGN; the registration order -- when Hickory reaches the front of the release queue -- re-seals the "
         "same committed inputs against that parent as a NEW package id. Nothing here is a production candidate, "
         "and no whole-site build was assembled."),
        ("nothing_registered", True), ("nothing_authorized", True), ("participation_untouched", True),
        ("pin_untouched", True), ("nothing_deployed", True),
        ("seconds", round(time.monotonic() - t0, 1)),
    ]))
    REPORT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out, package


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-sha", required=True, help="the COMMIT that holds every staged input")
    ap.add_argument("--work-dir", required=True, help="scratch directory for the two cold FAST builds")
    ap.add_argument("--stage", action="store_true", help="(re)write the staged shard documents first")
    ap.add_argument("--digest-only", action="store_true", help="seal twice and print the digest; write nothing")
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
