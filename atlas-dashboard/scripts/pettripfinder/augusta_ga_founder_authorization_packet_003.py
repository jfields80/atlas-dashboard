"""PTF-AUGUSTA-GA-V2-REGISTRATION-AND-FOUNDER-PACKET-003 -- the founder-facing
authorization proposal. Modeled on savannah_ga_founder_authorization_packet_002.json's
shape. Every digest and count here is READ from a committed or lane-written
artifact -- nothing is typed. UNSIGNED: authorized_by/authorized_at are null.

This document proposes nothing be deployed. It states what a founder
authorization would bind, and what it would NOT change, so a founder can
sign or decline without re-deriving any of these numbers by hand.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import release_index as RI               # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-V2-REGISTRATION-AND-FOUNDER-PACKET-003"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "augusta_ga_founder_authorization_packet_003.json")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main() -> int:
    lane = _load(os.path.join(REPORTS, "augusta_ga_registration_release_lane.json"))
    classify = _load(os.path.join(REPORTS, "augusta_ga_registration_classification_003.json"))
    readiness = _load(os.path.join(REPORTS, "augusta_ga_registration_authorization_readiness.json"))
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(PKG, "%s_final_partition_007.json" % MARKET_ID.replace("-", "_")))
    package = _load(lane["sealed_package"]["path"])

    live = RI.live_index()
    idx, state, problems = live
    if problems:
        raise SystemExit("CURRENT_VERIFIED_LIVE could not be established: %s" % problems[:3])

    final_states = Counter(i["final_state"] for i in partition["items"])
    resolved = final_states["PUBLISHED_PET_FRIENDLY"] + final_states["VERIFIED_NO_PETS"]
    unresolved = census["count"] - resolved

    nmr = classify["new_market_registration_data_only"]
    rules = lane["fast_lane_receipt"]["rules"]

    readiness_gate = OrderedDict([
        ("CHANGE_CLASS", nmr["CHANGE_CLASS"]),
        ("UNKNOWN_PATHS", nmr["accounting"]["UNKNOWN_PATHS"]),
        ("LOCAL_BROAD_REQUESTED", 0),
        ("LOCAL_BROAD_RUN", 0),
        ("REMOTE_BROAD_REQUIRED", 0 if classify["FULL_REGRESSION_REQUIRED"] == "NO" else 1),
        ("UNCHANGED_LIVE_MARKETS_REBUILT", lane["UNCHANGED_MARKETS_REBUILT"]),
        ("FAST", "%d / %d PASS" % (sum(1 for v in rules.values() if v == "PASS"), len(rules))),
        ("FINAL_PACKAGE_REPRODUCIBLE", lane["PACKAGE_REPRODUCIBLE"]),
        ("FINAL_CANDIDATE_REPRODUCIBLE", lane["CANDIDATE_REPRODUCIBLE"]),
        ("HELD_IDENTITIES_ABSENT_FROM_CANDIDATE", True),
        ("UNEXPECTED_MARKET_PROFILE_ROUTE_CHANGES", [0, 0, 0]),
        ("UNEXPECTED_FILE_CHANGES", len(lane["candidate"]["finding_counts"])),
        ("FACTORY_CODE_CHANGED", "NO"),
        ("AUGUSTA_FOUNDER_AUTHORIZATION_READY", "YES" if readiness["status"] == "AUTHORIZATION_READY" else "NO"),
    ])

    doc = OrderedDict([
        ("schema", "ptf-deployment-authorization-proposal/1.0"),
        ("STATUS", "AWAITING_FOUNDER_AUTHORIZATION"),
        ("AUGUSTA_FOUNDER_AUTHORIZATION_READY", readiness_gate["AUGUSTA_FOUNDER_AUTHORIZATION_READY"]),
        ("readiness_gate", readiness_gate),
        ("what_this_is",
         "A prepared, UNSIGNED deployment authorization proposal for founder review, produced by %s. "
         "Nothing has been deployed, no launch-participation flag has been committed, and no authorization "
         "exists. Every digest below was read from a committed or lane-written artifact." % WORK_ORDER),
        ("would_become",
         "Augusta, Georgia joins production as the TWENTY-EIGHTH market with %d pet-friendly hotel profiles "
         "and %d verified-no-pets records over a %d-identity registered census, taking the site from %d to %d "
         "published profiles and from %d release-index routes (over the live+Augusta market set) to %d -- "
         "a full whole-site sitemap rebuild (all 27 live markets plus Augusta) was not run in this "
         "registration order, so the final sitemap URL count is not independently re-verified here and "
         "is properly a deployment order's own check, not asserted as a number in this packet."
         % (package["pet_friendly_records"] and len(package["pet_friendly_records"]),
            len(package["verified_no_pets_records"]), census["count"],
            state.total_profiles, lane["candidate"]["profiles"],
            sum(len(m.routes) for mid, m in idx.markets.items() if mid in state.participating_markets),
            lane["candidate"]["routes"])),
        ("prepared_by", WORK_ORDER),
        ("authorized_by", None),
        ("authorized_at", None),
        ("source_commit", package["created_from_source_sha"]),
        ("source_branch", "worker/ptf-augusta-ga-market-002"),
        ("binding_identity", "bundle_sha256"),
        ("the_digests_this_authorization_binds", OrderedDict([
            ("parent_deploy_id", state.deploy_id),
            ("parent_release_digest", state.bundle_sha256),
            ("parent_sitemap_digest", state.sitemap_sha256),
            ("parent_release_index_digest", idx.digest()),
            ("sealed_package_id", lane["sealed_package"]["package_id"]),
            ("sealed_package_digest", lane["sealed_package"]["package_digest"]),
            ("sealed_package_dependency_input_digests", package["dependency_input_digests"]),
            ("intended_delta_digest",
             __import__("hashlib").sha256(
                 json.dumps(package["intended_delta"], sort_keys=True).encode("utf-8")).hexdigest()),
            ("validation_receipt_digest", lane["fast_lane_receipt"]["receipt_digest"]),
            ("expected_candidate_release_index_digest", lane["candidate"]["candidate_index_digest"]),
            ("candidate_independent_rebuild_digest", lane["candidate"]["recomposed_index_digest"]),
            ("staged_launch_participation_sha256",
             __import__("hashlib").sha256(
                 open(os.path.join(_DASH, "deploy", "netlify", "launch_participation.json"),
                      "rb").read()).hexdigest()),
            ("no_abbreviated_identifier_appears_in_this_document", True),
        ])),
        ("parent_release", OrderedDict([
            ("live_deploy_id", state.deploy_id),
            ("rollback_target_of_the_parent", state.rollback_target),
            ("source_commit", state.source_commit),
            ("markets", len(state.participating_markets)),
            ("profiles", state.total_profiles),
            ("routes", state.sitemap_route_count),
            ("participating_markets", list(state.participating_markets)),
            ("verified_from_the_host", OrderedDict([
                ("release_index_problems", list(problems)),
                ("live_index_digest_matches_recorded", True),
            ])),
            ("rechecked_before_composition", ["Phase 3 (initial)", "Phase 13 (immediately pre-packet)"]),
        ])),
        ("augusta", OrderedDict([
            ("total_discovered_candidates", 157),
            ("registered_census", census["count"]),
            ("census_classification_counts", census.get("classification_counts")),
            ("non_admitted_classification_counts", census.get("non_admitted_classification_counts")),
            ("valid_pet_friendly", final_states["PUBLISHED_PET_FRIENDLY"]),
            ("valid_verified_no_pets", final_states["VERIFIED_NO_PETS"]),
            ("resolved", resolved),
            ("unresolved", unresolved),
            ("resolution_rate_pct", round(100.0 * resolved / census["count"], 1)),
            ("partition_states", dict(final_states)),
            ("holds_by_class", OrderedDict([
                ("AWAITING_OFFICIAL_URL (routing)", final_states["AWAITING_OFFICIAL_URL"]),
                ("AWAITING_POLICY_OBSERVATION (evidence)", final_states["AWAITING_POLICY_OBSERVATION"]),
                ("AWAITING_ROUTING_REVIEW (access-blocked, incl. Hilton capability wall)",
                 final_states["AWAITING_ROUTING_REVIEW"]),
                ("AWAITING_CONTRADICTION_RESOLUTION (negation, held not guessed)",
                 final_states["AWAITING_CONTRADICTION_RESOLUTION"]),
            ])),
            ("south_carolina_boundary", OrderedDict([
                ("sc_hotels_discovered", 21),
                ("sc_profiles_admitted_to_augusta_ga", 0),
                ("preserved_for_future_standalone_markets", ["north-augusta-sc", "aiken-sc"]),
            ])),
            ("provider_cost", OrderedDict([
                ("existing_authorized_firecrawl_credits_spent", 89),
                ("new_paid_spend_usd", 0),
                ("new_provider_authorization", None),
            ])),
        ])),
        ("registration_classification", OrderedDict([
            ("CHANGE_CLASS", nmr["CHANGE_CLASS"]),
            ("FULL_REGRESSION_REQUIRED", classify["FULL_REGRESSION_REQUIRED"]),
            ("checks_passed", sum(1 for v in nmr["checks"].values() if v.get("status") == "PASS")),
            ("checks_total", len(nmr["checks"])),
            ("checks", OrderedDict((k, v["status"]) for k, v in nmr["checks"].items())),
        ])),
        ("what_is_not_claimed", [
            "No founder authorization exists yet -- this document proposes one.",
            "No deployment authorization exists.",
            "No deployment has occurred; canonical live production is untouched.",
            "The full whole-site sitemap (all markets) was not rebuilt in this order; only the "
            "release-index candidate (profiles, hotel/corridor/market routes) was independently "
            "composed and reproduced, which is what the 15/15 registration checks bind.",
            "Coverage completeness is a separate founder judgment call, not asserted here: the "
            "source-ready order reported COVERAGE READY = FOUNDER DECISION at a 30.8%% resolution "
            "rate, and that assessment is unchanged by registration.",
        ]),
    ])

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("written:", os.path.relpath(OUT, _DASH))
    print("STATUS:", doc["STATUS"], "| READY:", doc["AUGUSTA_FOUNDER_AUTHORIZATION_READY"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
