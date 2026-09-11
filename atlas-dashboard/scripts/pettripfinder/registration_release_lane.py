"""PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 -- the generic registration
release lane: seal the registering market, prove it on the FAST lane, commit
the package and the receipt where Regression V2 reads them, and -- once the
classifier has answered -- prepare the UNSIGNED authorization-readiness packet.

    python -m scripts.pettripfinder.registration_release_lane seal --market <id>
    python -m scripts.pettripfinder.regression_delta classify --base <sha> --out <classify.json>
    python -m scripts.pettripfinder.registration_release_lane packet --market <id> \
        --classification <classify.json>

WHY THIS IS GENERIC
-------------------
Every market so far carried its own release-lane script (charlotte_nc_release_
lane_005, nashville_tn_release_lane_003, ...). Each sealed the package in
memory, ran rules A-O, and embedded the receipt in a report -- so nothing under
``markets/packages/<market>/`` or ``markets/receipts/<market>/`` existed for a
classifier to find, and the registration could not be proven data-only from
the change set alone. This lane writes both, in the market's own zone
(MARKET_DATA_PACKAGE, a narrow companion), so ``regression_delta classify``
can bind the registration to a sealed package and an eligible receipt without
being told anything.

WHAT ``seal`` PROVES
--------------------
    PACKAGE_REPRODUCIBLE      the package is sealed TWICE from the committed
                              authority; the two digests must be equal
    FAST rules A-O            15/15 PASS, 0 UNKNOWN, 0 FAILED, or the lane
                              reports NOT ELIGIBLE and exits non-zero
    CANDIDATE_REPRODUCIBLE    rule K's two COLD builds of the joining market
                              produced one bundle digest, and the composed
                              release index (live parent + package) is the same
                              digest when composed a second time
    UNCHANGED_MARKETS_REBUILT 0 -- the lane renders the joining market only

Nothing here deploys, nothing flips participation, nothing enables activation.

WHAT ``packet`` WRITES
----------------------
A prepared, UNSIGNED readiness document under ``markets/reports/`` -- never
under ``deploy/netlify/deployment_authorizations/``, because a file there IS
an authorization and only a founder creates one. It binds the parent release,
the package, the receipt, the intended delta and the expected candidate index,
and it records the classifier's verdict. ``authorized_by`` and
``authorized_at`` are null and stay null.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import fast_release_lane as FL         # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB      # noqa: E402
from scripts.pettripfinder import market_package_writer as W      # noqa: E402
from scripts.pettripfinder import release_index as RI             # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP    # noqa: E402
from scripts.pettripfinder.markets.contract import parse_market   # noqa: E402

LANE_SCHEMA = "ptf-registration-release-lane/1.0"
READINESS_SCHEMA = "ptf-registration-authorization-readiness/1.0"
REPORTS = SMP.LAUNCH_PACKAGE / "markets" / "reports"


def _write(path: Path, doc: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parent_from_live(live) -> "OrderedDict[str, Any]":
    idx, state, _problems = live
    doc = state.to_dict()
    parent = OrderedDict((k, doc[k]) for k in ("live_deploy_id", "rollback_target", "source_commit",
                                               "participating_markets", "profile_counts",
                                               "total_profiles", "sitemap_route_count"))
    parent["live_index_digest"] = idx.digest()
    return parent


def joining_delta(inputs: W.PackageInputs) -> "OrderedDict[str, Any]":
    """A market that JOINS, and nothing else moves. Property-level fields are
    empty and the profile delta is zero on purpose: ``release_index.compare``
    measures those WITHIN a market live on both sides, and a joining market is
    on neither. The join is declared by ``expected_market_count_delta`` and
    ``expected_participation_delta``; the surface it brings is declared route
    by route in ``add_routes``, derived by the same functions the release index
    uses, so the declaration and the measurement cannot drift apart."""
    market = parse_market(dict(inputs.market))
    profiles = RI._entries(market, inputs.pet_friendly_records, inputs.seed_rows)
    routes = sorted({p.route for p in profiles.values()}
                    | set(RI.published_corridor_routes(market, profiles, inputs.seed_rows))
                    | {RI.market_route(market)})
    return OrderedDict((
        ("market_id", inputs.market_id),
        ("add_property_ids", []),
        ("update_property_ids", []),
        ("remove_property_ids", []),
        ("add_routes", routes),
        ("change_routes", []),
        ("remove_routes", []),
        ("expected_profile_delta", 0),
        ("expected_verified_no_pets_delta", 0),
        ("expected_market_count_delta", 1),
        ("expected_participation_delta", [OrderedDict((
            ("market_id", inputs.market_id), ("from", False), ("to", True)))]),
        ("joining_market_profiles", len(inputs.pet_friendly_records)),
        ("joining_market_verified_no_pets", len(inputs.verified_no_pets_records)),
    ))


def seal(market_id: str, *, sealed_at: str, work_dir: Path, out: Path,
         paid_reservations: Optional[Mapping[str, Mapping]] = None,
         packages_dir: Optional[Path] = None, receipts_dir: Optional[Path] = None) -> Dict:
    timings: "OrderedDict[str, float]" = OrderedDict()
    t0 = time.monotonic()

    t = time.monotonic()
    live = RI.live_index()
    idx, state, problems = live
    timings["live_parent_read_s"] = round(time.monotonic() - t, 2)
    if problems:
        raise SystemExit("CURRENT_VERIFIED_LIVE could not be established: %s" % problems[:3])
    if market_id in state.participating_markets:
        raise SystemExit("%s already participates in the live release; this lane registers a joining market" % market_id)
    parent = parent_from_live(live)

    t = time.monotonic()
    inputs = W.inputs_from_committed_market(
        market_id, execution_zone=SMP.ZONE_REGISTERED_LIVE,
        intended_delta=OrderedDict((("market_id", market_id),)), parent_live_state=parent)
    inputs.intended_delta = joining_delta(inputs)
    inputs.paid_reservations = dict(paid_reservations or {})
    timings["package_inputs_s"] = round(time.monotonic() - t, 2)

    t = time.monotonic()
    package = W.build_sealed_package(inputs, sealed_at=sealed_at)
    again = W.build_sealed_package(inputs, sealed_at=sealed_at)
    package_reproducible = package["package_digest"] == again["package_digest"]
    timings["package_seal_x2_s"] = round(time.monotonic() - t, 2)
    if not package_reproducible:
        raise SystemExit("PACKAGE_REPRODUCIBLE = NO: %s vs %s" % (package["package_digest"], again["package_digest"]))
    package_path = SMP.write_sealed(package, packages_dir)

    t = time.monotonic()
    gate = FPB.evaluate_package(package)
    timings["first_party_gate_s"] = round(time.monotonic() - t, 2)

    t = time.monotonic()
    receipt = FL.run_fast_lane(package, work_dir=work_dir, live=live, participates=True)
    timings["fast_lane_s"] = round(time.monotonic() - t, 2)
    receipt_path = FL.write_receipt(receipt, receipts_dir)

    t = time.monotonic()
    package_index = RI.index_from_package(package, participating=True)
    candidate = RI.compose(idx, package_index, participates=True)
    candidate_again = RI.compose(idx, RI.index_from_package(package, participating=True), participates=True)
    diff = RI.compare(idx, candidate, package_market=market_id, intended_delta=package["intended_delta"])
    timings["candidate_compose_x2_s"] = round(time.monotonic() - t, 2)
    artifacts = receipt.get("ARTIFACT_DIGESTS") or {}
    bundle_a, bundle_b = artifacts.get("changed_market_bundle_sha256_a"), artifacts.get("changed_market_bundle_sha256_b")
    candidate_reproducible = bool(bundle_a) and bundle_a == bundle_b and candidate.digest() == candidate_again.digest()
    timings["total_s"] = round(time.monotonic() - t0, 2)

    eligible = receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES
    rel = lambda p: Path(p).relative_to(_DASH).as_posix() if str(p).startswith(str(_DASH)) else str(p)  # noqa: E731
    doc = OrderedDict((
        ("schema", LANE_SCHEMA),
        ("market_id", market_id),
        ("as_of", _now()),
        ("nothing_deployed", True),
        ("nothing_activated", True),
        ("participation_untouched", True),
        ("parent_live_state", parent),
        ("sealed_package", OrderedDict((
            ("package_id", package["package_id"]), ("package_digest", package["package_digest"]),
            ("path", rel(package_path)), ("sealed_at", package.get("sealed_at")),
            ("created_from_source_sha", package.get("created_from_source_sha")),
            ("pet_friendly_records", len(package.get("pet_friendly_records") or [])),
            ("verified_no_pets_records", len(package.get("verified_no_pets_records") or [])),
            ("census_count", (package.get("census") or {}).get("count")),
            ("unresolved_rows", len(package.get("unresolved_rows") or [])),
            ("declared_routes", len(package["intended_delta"].get("add_routes") or [])),
        ))),
        ("PACKAGE_REPRODUCIBLE", "YES" if package_reproducible else "NO"),
        ("first_party_gate", OrderedDict((("records_evaluated", gate["records_evaluated"]),
                                          ("eligible", gate["eligible"]), ("ineligible", gate["ineligible"]),
                                          ("passed", gate["passed"])))),
        ("fast_lane_receipt", OrderedDict((
            ("path", rel(receipt_path)), ("receipt_digest", receipt["RECEIPT_DIGEST"]),
            ("eligible", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
            ("rules", OrderedDict((r, res["status"]) for r, res in receipt["RESULTS"].items())),
            ("rules_passed", sum(1 for res in receipt["RESULTS"].values() if res["status"] == FL.PASS)),
            ("unknown_rules", receipt["UNKNOWN_RULES"]), ("failed_rules", receipt["FAILED_RULES"]),
            ("determinism_result", receipt["DETERMINISM_RESULT"]),
            ("changed_market_bundle_sha256", bundle_a),
            ("fast_lane_seconds", receipt["PERFORMANCE"]["total_seconds"]),
        ))),
        ("candidate", OrderedDict((
            ("candidate_index_digest", candidate.digest()),
            ("recomposed_index_digest", candidate_again.digest()),
            ("markets", len(candidate.participating)), ("profiles", candidate.total_profiles),
            ("routes", len({r for i in candidate.markets.values() if i.participating for r in i.routes})),
            ("release_diff_passed", diff["passed"]), ("finding_counts", diff["finding_counts"]),
        ))),
        ("CANDIDATE_REPRODUCIBLE", "YES" if candidate_reproducible else "NO"),
        ("UNCHANGED_MARKETS_REBUILT", 0),
        ("unchanged_markets", list(parent["participating_markets"])),
        ("timings", timings),
    ))
    _write(out, doc)
    print("package        :", package["package_id"], "reproducible", doc["PACKAGE_REPRODUCIBLE"])
    print("fast lane      :", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"], "| rules passed",
          doc["fast_lane_receipt"]["rules_passed"], "| unknown", receipt["UNKNOWN_RULES"],
          "| failed", receipt["FAILED_RULES"], "| %.1fs" % timings["fast_lane_s"])
    print("candidate      :", doc["candidate"]["markets"], "markets /", doc["candidate"]["profiles"],
          "profiles /", doc["candidate"]["routes"], "routes; reproducible", doc["CANDIDATE_REPRODUCIBLE"])
    print("receipt        :", rel(receipt_path))
    print("written        :", rel(out), "| total %.1fs" % timings["total_s"])
    if not eligible or not candidate_reproducible:
        raise SystemExit(1)
    return doc


def packet(market_id: str, *, classification_path: Path, lane_report: Path, out: Path,
           prepared_by: str) -> Dict:
    classification = _read(classification_path)
    plan = classification.get("plan") or {}
    proof = classification.get("new_market_registration_data_only") or {}
    lane = _read(lane_report) if lane_report.is_file() else {}
    ready = (proof.get("ELIGIBLE") == "YES" and plan.get("NEW_MARKET_REGISTRATION_DATA_ONLY") == "YES"
             and classification.get("FULL_REGRESSION_REQUIRED") == "NO"
             and proof.get("market_id") == market_id)
    checks = OrderedDict((name, c.get("status")) for name, c in (proof.get("checks") or {}).items())
    expected = proof.get("expected_release") or {}
    doc = OrderedDict((
        ("schema", READINESS_SCHEMA),
        ("status", "AUTHORIZATION_READY" if ready else "NOT_AUTHORIZATION_READY"),
        ("founder_status", "AWAITING_FOUNDER_AUTHORIZATION"),
        ("what_this_is", "A prepared, UNSIGNED readiness document for founder review, written by the "
                         "registration release lane after Regression V2 classified the registration. It "
                         "authorizes nothing: no launch-participation flag has moved, no activation flag is "
                         "enabled, nothing is deployed. The founder's decision, if it comes, is a separate "
                         "write into deploy/netlify/deployment_authorizations/ that this document never makes."),
        ("market_id", market_id),
        ("prepared_by", prepared_by),
        ("prepared_at", _now()),
        ("authorized_by", None),
        ("authorized_at", None),
        ("regression_v2", OrderedDict((
            ("base", classification.get("base_sha")), ("head", classification.get("head_sha")),
            ("change_classes", classification.get("change_classes")),
            ("release_surfaces", classification.get("release_surfaces")),
            ("CHANGE_CLASS", "NEW_MARKET_REGISTRATION_DATA_ONLY" if ready else "/".join(classification.get("change_classes") or [])),
            ("FULL_REGRESSION_REQUIRED", classification.get("FULL_REGRESSION_REQUIRED")),
            ("REMOTE_BROAD_JOBS_REQUIRED", plan.get("REMOTE_BROAD_JOBS_REQUIRED")),
            ("plan_modules", plan.get("module_count")), ("assembly_required", plan.get("assembly_required")),
            ("reason", classification.get("full_regression_reason")),
        ))),
        ("registration_proof", OrderedDict((
            ("proof_version", proof.get("proof_version")), ("ELIGIBLE", proof.get("ELIGIBLE")),
            ("checks", checks), ("seconds", proof.get("seconds")),
        ))),
        ("the_digests_this_readiness_binds", OrderedDict((
            ("parent_live_deploy_id", proof.get("live_deploy_id")),
            ("parent_release_digest", (lane.get("parent_live_state") or {}).get("live_index_digest")),
            ("sealed_package_id", proof.get("package_id")),
            ("sealed_package_digest", proof.get("package_digest")),
            ("fast_receipt", proof.get("receipt")),
            ("fast_receipt_digest", (lane.get("fast_lane_receipt") or {}).get("receipt_digest")),
            ("changed_market_bundle_sha256", (lane.get("fast_lane_receipt") or {}).get("changed_market_bundle_sha256")),
            ("expected_candidate_index_digest", expected.get("expected_digest")),
            ("actual_candidate_index_digest", expected.get("actual_digest")),
        ))),
        ("projected_live", OrderedDict((
            ("markets", expected.get("actual_markets")), ("profiles", expected.get("actual_profiles")),
            ("routes", expected.get("actual_routes")),
            ("unexpected_market_changes", expected.get("unexpected_market_changes")),
            ("unexpected_profile_changes", expected.get("unexpected_profile_changes")),
            ("unexpected_route_changes", expected.get("unexpected_route_changes")),
        ))),
        ("lane", OrderedDict((
            ("PACKAGE_REPRODUCIBLE", lane.get("PACKAGE_REPRODUCIBLE")),
            ("CANDIDATE_REPRODUCIBLE", lane.get("CANDIDATE_REPRODUCIBLE")),
            ("UNCHANGED_MARKETS_REBUILT", lane.get("UNCHANGED_MARKETS_REBUILT")),
            ("fast_rules_passed", (lane.get("fast_lane_receipt") or {}).get("rules_passed")),
        ))),
        ("what_is_not_claimed", [
            "This document authorizes nothing. Only a founder authorization in "
            "deploy/netlify/deployment_authorizations/ admits a market to production.",
            "The whole-site deployment artifact is built and hashed by the deployment order, under the "
            "current-parent guard, the exact-bytes rule and the rollback guard, none of which this lane touches.",
            "The registration's participation row reads SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH.",
        ]),
    ))
    _write(out, doc)
    print("status         :", doc["status"], "| founder:", doc["founder_status"])
    print("change class   :", doc["regression_v2"]["CHANGE_CLASS"], "| broad:", doc["regression_v2"]["FULL_REGRESSION_REQUIRED"],
          "| remote broad jobs:", doc["regression_v2"]["REMOTE_BROAD_JOBS_REQUIRED"])
    print("written        :", out.relative_to(_DASH).as_posix() if str(out).startswith(str(_DASH)) else out)
    if not ready:
        raise SystemExit(1)
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("seal", help="seal the market, run the FAST lane, write package + receipt")
    s.add_argument("--market", required=True)
    s.add_argument("--sealed-at", default=None, help="ISO timestamp; defaults to now (UTC)")
    s.add_argument("--work", default=None)
    s.add_argument("--out", default=None)
    s.add_argument("--paid-reservations", default=None,
                   help="JSON file: artifact sha256 -> reservation, for markets with paid captures")
    s = sub.add_parser("packet", help="write the UNSIGNED authorization-readiness packet")
    s.add_argument("--market", required=True)
    s.add_argument("--classification", required=True)
    s.add_argument("--lane-report", default=None)
    s.add_argument("--out", default=None)
    s.add_argument("--prepared-by", default="registration_release_lane")
    args = p.parse_args(argv)

    us = args.market.replace("-", "_")
    if args.command == "seal":
        reservations = _read(Path(args.paid_reservations)) if args.paid_reservations else None
        seal(args.market,
             sealed_at=args.sealed_at or _now(),
             work_dir=Path(args.work) if args.work else _DASH / "data" / "registration_release_lane" / args.market,
             out=Path(args.out) if args.out else REPORTS / ("%s_registration_release_lane.json" % us),
             paid_reservations=reservations)
        return 0
    packet(args.market, classification_path=Path(args.classification),
           lane_report=Path(args.lane_report) if args.lane_report else REPORTS / ("%s_registration_release_lane.json" % us),
           out=Path(args.out) if args.out else REPORTS / ("%s_registration_authorization_readiness.json" % us),
           prepared_by=args.prepared_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
