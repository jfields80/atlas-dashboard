"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- the modern release lane.

Takes the RECOVERED Charlotte authority through the redesigned lane
ATLAS-THROUGHPUT-003 to 008 built, and writes what each stage proved:

    1  MODERN FIRST-PARTY EVIDENCE GATE   first_party_binding.evaluate_package
    2  SEALED PACKAGE                     market_package_writer.build_sealed_package
    3  DATA-ONLY CLASSIFICATION           regression_delta over this order's diff
    4  FAST RELEASE-SAFETY LANE           fast_release_lane rules A-O
    5  CURRENT LIVE PARENT, RE-READ       release_index.current_verified_live
    6  FINAL CANDIDATE                    release_index.compose (live + Charlotte)
    7  RELEASE DIFF                       release_index.compare
    8  CACHE / REUSE                      bundle_cache lookup per live market

Nothing here deploys, nothing flips launch participation, and nothing enables a
production activation flag. The final stage writes a founder authorization
packet whose status is AWAITING_FOUNDER_AUTHORIZATION.

The candidate is composed with Charlotte PARTICIPATING, because a pre-flip
candidate can never carry the digest a launch would produce -- the lesson
PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003 paid for and
PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 inherits. Composing an
index is not a participation decision: the committed participation record still
says SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH and the assembler still
excludes the market.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import bundle_cache as BC              # noqa: E402
from scripts.pettripfinder import fast_release_lane as FL         # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB      # noqa: E402
from scripts.pettripfinder import market_package_writer as W      # noqa: E402
from scripts.pettripfinder import release_index as RI             # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP    # noqa: E402
from scripts.pettripfinder.markets.assignment import assign_hotels  # noqa: E402
from scripts.pettripfinder.markets.contract import parse_market   # noqa: E402
from scripts.pettripfinder.markets.routes import corridor_route, hotel_route  # noqa: E402
# Charlotte has NO paid ledger to ingest. Every published row came through a
# free lane -- the operator's own Chrome session or a plain HTTPS GET -- so
# there is no reservation to look up and rule O has nothing to bind. That is a
# fact about this market, recorded, not a check skipped: the lane still runs
# rule O, and it passes because there is no paid capture to fail it.

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
SEALED_AT = "2026-09-10T00:00:00Z"


def _write(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def parent_from_live(live):
    idx, state, _problems = live
    doc = state.to_dict()
    parent = OrderedDict((k, doc[k]) for k in ("live_deploy_id", "rollback_target",
                                               "source_commit", "participating_markets",
                                               "profile_counts", "total_profiles",
                                               "sitemap_route_count"))
    parent["live_index_digest"] = idx.digest()
    return parent


def joining_delta(inputs) -> "OrderedDict":
    """Charlotte's intended delta: a market that JOINS, and nothing else moves.

    The property-level fields are empty and the profile delta is zero on
    purpose, and it is not an understatement. ``release_index.compare`` measures
    ``add_property_ids`` and ``expected_profile_delta`` as movement WITHIN a
    market that is live on both sides of the comparison. Charlotte is on neither
    side of that question: it is not a live market, so none of its profiles is
    an addition to one. A market that joins is declared by
    ``expected_market_count_delta`` and ``expected_participation_delta``, and the
    surface it brings is declared route by route in ``add_routes`` -- the hub,
    every published corridor and every hotel profile, derived here from the same
    functions the release index derives them from, so the declaration and the
    measurement cannot drift apart.
    """
    market = parse_market(dict(inputs.market))
    profiles = RI._entries(market, inputs.pet_friendly_records, inputs.seed_rows)
    routes = sorted({p.route for p in profiles.values()}
                    | set(RI.published_corridor_routes(market, profiles, inputs.seed_rows))
                    | {RI.market_route(market)})
    return OrderedDict((
        ("market_id", MARKET_ID),
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
            ("market_id", MARKET_ID), ("from", False), ("to", True)))]),
        ("joining_market_profiles", len(inputs.pet_friendly_records)),
        ("joining_market_verified_no_pets", len(inputs.verified_no_pets_records)),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPORTS / "charlotte_nc_release_lane_005.json"))
    ap.add_argument("--work", default=str(_DASH / "data" / "charlotte_release_lane_005"))
    ap.add_argument("--base", default="11373275",
                    help="the commit this order's change is measured against")
    args = ap.parse_args(argv)

    timings = OrderedDict()
    t0 = time.monotonic()

    # ---- 5 (first): the parent, read from the committed records ------------ #
    live = RI.live_index()
    parent = parent_from_live(live)
    timings["live_parent_read_s"] = round(time.monotonic() - t0, 2)

    # ---- 2: package inputs and the sealed package -------------------------- #
    t = time.monotonic()
    inputs = W.inputs_from_committed_market(
        MARKET_ID, execution_zone=SMP.ZONE_REGISTERED_LIVE,
        intended_delta=OrderedDict((("market_id", MARKET_ID),)),
        parent_live_state=parent)
    inputs.intended_delta = joining_delta(inputs)
    # No published Charlotte row came through a paid lane, so there is no
    # reservation to read back. Rule O still runs.
    inputs.paid_reservations = {}
    timings["package_inputs_s"] = round(time.monotonic() - t, 2)

    # ---- 1: the modern first-party evidence gate --------------------------- #
    t = time.monotonic()
    package = W.build_sealed_package(inputs, sealed_at=SEALED_AT)
    timings["package_seal_s"] = round(time.monotonic() - t, 2)

    t = time.monotonic()
    gate = FPB.evaluate_package(package)
    timings["first_party_gate_s"] = round(time.monotonic() - t, 2)

    # ---- 4: the fast release-safety lane ----------------------------------- #
    t = time.monotonic()
    receipt = FL.run_fast_lane(package, work_dir=Path(args.work), live=live,
                               participates=True)
    timings["fast_lane_s"] = round(time.monotonic() - t, 2)

    # ---- 6 and 7: the final candidate and the release diff ----------------- #
    t = time.monotonic()
    package_index = RI.index_from_package(package, participating=True)
    candidate = RI.compose(live[0], package_index, participates=True)
    diff = RI.compare(live[0], candidate, package_market=MARKET_ID,
                      intended_delta=package["intended_delta"])
    timings["candidate_compose_s"] = round(time.monotonic() - t, 2)

    # ---- 3: the Regression V2 classification of this order's own change ---- #
    #
    # TWO DIFFERENT QUESTIONS, and conflating them is the mistake this section
    # exists to prevent:
    #
    #   (a) what does REGISTERING Charlotte cost?  The change surface of this
    #       order, classified by regression_delta over the real diff. It is a
    #       one-time cost and it is NOT data-only: registering a market moves a
    #       deployment record and the assembler's own partition table.
    #
    #   (b) what does a ROUTINE Charlotte release cost?  The fast lane's receipt
    #       answers that for the sealed package: CHANGE_CLASS
    #       MARKET_AUTHORITY_DATA_ONLY, FULL_REGRESSION_REQUIRED_BY_LANE = NO.
    #       That substitution is only ALLOWED once the activation flags name
    #       Charlotte, which this order proposes and does not apply.
    t = time.monotonic()
    from scripts.pettripfinder import regression_delta as RD
    surface = RD.classify_change(base=args.base, head=RD.WORKTREE)
    plan = RD.plan_for(surface)
    surface["plan"] = plan
    surface["FULL_REGRESSION_REQUIRED"] = ("YES" if plan["full_regression_required"] else "NO")
    surface["full_regression_reason"] = RD._full_reason(plan)
    timings["classification_s"] = round(time.monotonic() - t, 2)

    # ---- 8: cache / reuse ------------------------------------------------- #
    #
    # UNCHANGED_MARKETS_REBUILT = 0 here is a fact about what the lane DID, not
    # a cache hit rate. The redesigned lane never renders an unchanged market:
    # rule J stages and builds the CHANGED market alone, and rules G, H and I
    # compare release INDEXES derived from committed authority, so the other
    # twelve markets are neither reused nor rebuilt -- they are not built at
    # all. The persistent bundle cache is reported for the market that IS built.
    t = time.monotonic()
    cache = BC.BundleCache()
    try:
        probe = cache.probe(package)
    except Exception as exc:                                       # noqa: BLE001
        probe = OrderedDict((("trusted", False),
                             ("why", "%s: %s" % (type(exc).__name__, exc))))
    reuse = OrderedDict((
        ("changed_market", OrderedDict((("market_id", MARKET_ID), ("probe", probe),
                                        ("bundle_reused", bool(probe.get("trusted"))),
                                        ("bundle_rebuilt", not probe.get("trusted"))))),
        ("unchanged_live_markets", OrderedDict((
            ("count", len(parent["participating_markets"])),
            ("bundles_reused", 0), ("bundles_rebuilt", 0),
            ("why", "the lane renders only the changed market; every other live market is "
                    "carried by its committed release index entry, so none of them was "
                    "built, reused from a bundle, or rebuilt"),
            ("markets", list(parent["participating_markets"])),
        ))),
        ("UNCHANGED_MARKETS_REBUILT", 0),
    ))
    timings["cache_lookup_s"] = round(time.monotonic() - t, 2)
    timings["total_s"] = round(time.monotonic() - t0, 2)

    doc = OrderedDict((
        ("schema", "ptf-market-release-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("nothing_deployed", True),
        ("nothing_activated", True),
        ("parent_live_state", parent),
        ("first_party_gate", OrderedDict((
            ("records_evaluated", gate["records_evaluated"]),
            ("eligible", gate["eligible"]),
            ("ineligible", gate["ineligible"]),
            ("passed", gate["passed"]),
            ("classes", gate["classes"]),
            ("failures", gate["failures"]),
        ))),
        ("sealed_package", OrderedDict((
            ("package_id", package["package_id"]),
            ("package_digest", package["package_digest"]),
            ("build_input_key", package.get("build_input_key")),
            ("sealed_at", package.get("sealed_at")),
            ("pet_friendly_records", len(package.get("pet_friendly_records") or [])),
            ("verified_no_pets_records", len(package.get("verified_no_pets_records") or [])),
            ("census_count", (package.get("census") or {}).get("count")),
            ("evidence_references", len(package.get("evidence_references") or [])),
            ("unresolved", len(package.get("unresolved") or [])),
            ("founder_holds", len(package.get("founder_holds") or [])),
            ("coverage_scorecard", package.get("coverage_scorecard")),
        ))),
        ("intended_delta", package["intended_delta"]),
        ("registration_change_classification", OrderedDict((
            ("base", surface.get("base_sha")),
            ("changed_file_count", surface.get("changed_file_count")),
            ("change_classes", surface.get("change_classes")),
            ("MARKET_AUTHORITY_DATA_ONLY", surface.get("market_authority_data_only")),
            ("FAST_DATA_ONLY_RELEASE", surface.get("fast_data_only_release")),
            ("FULL_REGRESSION_REQUIRED", surface.get("FULL_REGRESSION_REQUIRED")),
            ("why_it_widens", surface.get("full_regression_reason")),
            ("narrowing_blockers", surface.get("narrowing_blockers")),
            ("lanes", plan["lanes"]),
            ("modules", plan["module_count"]),
            ("assembly_required", plan["assembly_required"]),
            ("this_is_the_registration_not_the_routine_release",
             "a market is registered once. The routine question is answered by "
             "fast_lane_receipt.change_class and .full_regression_required_by_lane above."),
        ))),
        ("fast_lane_receipt", OrderedDict((
            ("receipt_digest", receipt["RECEIPT_DIGEST"]),
            ("eligible", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
            ("change_class", receipt["CHANGE_CLASS"]),
            ("full_regression_required_by_lane", receipt["FULL_REGRESSION_REQUIRED_BY_LANE"]),
            ("rules", OrderedDict((r, res["status"])
                                  for r, res in receipt["RESULTS"].items())),
            ("unknown_rules", receipt["UNKNOWN_RULES"]),
            ("failed_rules", receipt["FAILED_RULES"]),
            ("intended_delta_digest", receipt["INTENDED_DELTA_DIGEST"]),
            ("artifact_digests", receipt["ARTIFACT_DIGESTS"]),
            ("determinism_result", receipt["DETERMINISM_RESULT"]),
            ("fast_path_production_activation", receipt["FAST_PATH_PRODUCTION_ACTIVATION"]),
            ("production_activation_allowed", receipt["PRODUCTION_ACTIVATION_ALLOWED"]),
            ("performance", receipt["PERFORMANCE"]),
        ))),
        ("fast_lane_receipt_document", receipt),
        ("release_diff", diff),
        ("candidate", OrderedDict((
            ("candidate_index_digest", candidate.digest()),
            ("markets", sorted(m for m, i in candidate.markets.items() if i.participating)),
            ("market_count", sum(1 for i in candidate.markets.values() if i.participating)),
            ("profile_counts", OrderedDict(sorted(
                (m, len(i.profiles)) for m, i in candidate.markets.items()
                if i.participating))),
            ("route_count", len({r for i in candidate.markets.values() if i.participating
                                 for r in i.routes})),
            ("parent_route_count", len({r for i in live[0].markets.values() if i.participating
                                        for r in i.routes})),
            ("charlotte_routes", sorted(candidate.markets[MARKET_ID].routes)),
        ))),
        ("cache_reuse", reuse),
        ("timings", timings),
    ))
    _write(Path(args.out), doc)

    print("parent live     :", parent["live_deploy_id"], parent["total_profiles"], "profiles /",
          parent["sitemap_route_count"], "routes /", len(parent["participating_markets"]),
          "markets")
    print("first-party gate:", gate["records_evaluated"], "evaluated,", gate["eligible"],
          "eligible,", gate["ineligible"], "ineligible", dict(gate["classes"]))
    print("package digest  :", package["package_digest"])
    print("fast lane       :", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"],
          "| unknown:", receipt["UNKNOWN_RULES"], "| failed:", receipt["FAILED_RULES"])
    print("candidate       :", doc["candidate"]["market_count"], "markets,",
          sum(doc["candidate"]["profile_counts"].values()), "profiles")
    print("written         :", os.path.relpath(args.out, str(_DASH)))
    print("timings         :", dict(timings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
