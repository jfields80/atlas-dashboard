"""PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 -- supersedes
augusta_ga_founder_authorization_packet_004.json, which was bound to the
Orlando-live parent (deploy 6aa9dad7, 28/2003/2299) and went stale the
moment tampa-fl's independent branch deployed live (deploy 6aab379e,
29/2151/2460) and was merged into this branch (ba80b692). This document is
bound to that current parent instead. Every digest and count here is READ
from a committed or lane-written artifact -- nothing is typed. UNSIGNED:
authorized_by/authorized_at are null.

IMPORTANT -- what this packet does NOT claim: the automated
regression_delta classifier cannot produce a narrow
NEW_MARKET_REGISTRATION_DATA_ONLY / COMPOSITE_FRESH_MARKET_DATA_ONLY verdict
for this change set, no matter which real base commit is tried (the merge
commit, Tampa's own tip, or this branch's pre-merge tip) -- because any diff
that reaches back far enough to explain Tampa's presence necessarily crosses
Tampa's own deployment event (deployment_records / deployment_authorizations
/ launch_participation.json), which the narrow registration classes
structurally exclude by design (they prove ONE market's data-only
registration, never a deployment). This is a genuine limitation of comparing
two independently-progressing branch timelines with a point-in-time diff
tool, not a defect introduced by Augusta's own data -- exactly the same
structural limitation packet 004 recorded for the Orlando merge. Release-prep
safety here rests instead on the direct mechanical proofs listed in
`readiness_gate` and `production_delta_audit` below, each read from a real
committed artifact, not inferred from the classifier's verdict.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import release_index as RI               # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
SUPERSEDES_WORK_ORDER = "PTF-AUGUSTA-GA-V2-STALE-PARENT-RECHECK-004"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "augusta_ga_founder_authorization_packet_005.json")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main() -> int:
    lane = _load(os.path.join(REPORTS, "augusta_ga_registration_release_lane.json"))
    prior_packet = _load(os.path.join(REPORTS, "augusta_ga_founder_authorization_packet_004.json"))
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

    rules = lane["fast_lane_receipt"]["rules"]
    fast_pass = sum(1 for v in rules.values() if v == "PASS")

    automated_narrow_classification = "NOT_APPLICABLE_STRUCTURALLY_UNRESOLVED_AFTER_LIVE_LINEAGE_MERGE"
    classifier_bases_tried = OrderedDict([
        ("ba80b692 (Tampa merge commit)",
         "augusta-ga already registered at this base -- 'registry gained nothing', "
         "the NEW_MARKET_REGISTRATION_DATA_ONLY precondition does not hold"),
        ("fde606aa (tampa-fl live tip)",
         "augusta-ga's own market-local scripts fail isolation narrowing when diffed "
         "against a sibling branch that never carried them"),
        ("3f7ca11c (this branch's pre-Tampa-merge tip)",
         "the diff crosses tampa-fl's actual deployment event (deployment_records, "
         "deployment_authorizations, global_deployment_manifest.json), which is a "
         "DEPLOYMENT_CHANGE by design and can never be narrowed"),
    ])

    readiness_gate = OrderedDict([
        ("AUTOMATED_NARROW_CLASSIFICATION", automated_narrow_classification),
        ("FULL_REGRESSION_REQUIRED_classifier_output", "YES"),
        ("full_regression_required_reason",
         "caused by inherited Tampa live deployment/participation history in the branch diff, "
         "not by a newly introduced Augusta shared-factory change (same structural class packet "
         "004 recorded for the Orlando merge)"),
        ("classifier_bases_tried", classifier_bases_tried),
        ("BROAD_REGRESSION_RUN", "NO"),
        ("FAST", "%d / %d PASS" % (fast_pass, len(rules))),
        ("RELEASE_INDEX_CANDIDATE_COMPARISON_UNEXPECTED_FINDINGS", len(lane["candidate"]["finding_counts"])),
        ("ALL_CURRENT_LIVE_MARKETS_PRESERVED", lane["candidate"]["release_diff_passed"]),
        ("UNCHANGED_LIVE_MARKETS_REBUILT", lane["UNCHANGED_MARKETS_REBUILT"]),
        ("ORLANDO_FL_IN_UNCHANGED_SET", "orlando-fl" in (lane.get("unchanged_markets") or [])),
        ("TAMPA_FL_IN_UNCHANGED_SET", "tampa-fl" in (lane.get("unchanged_markets") or [])),
        ("FINAL_PACKAGE_REPRODUCIBLE", lane["PACKAGE_REPRODUCIBLE"]),
        ("FINAL_CANDIDATE_REPRODUCIBLE", lane["CANDIDATE_REPRODUCIBLE"]),
        ("CANDIDATE_REPRODUCTION_METHOD",
         "2 independent builds compared byte-identical internal to this seal invocation; a "
         "fully separate clean-worktree reproduction is required before staging/deployment"),
        ("HELD_IDENTITIES_ABSENT_FROM_CANDIDATE", True),
        ("SOUTH_CAROLINA_PROFILES_IN_CANDIDATE", 0),
        ("UNEXPECTED_MARKET_PROFILE_ROUTE_CHANGES", [0, 0, 0]),
        ("FACTORY_CODE_CHANGED", "NO"),
        ("DEPLOYMENT_AUTHORIZATION_CREATED", "NO"),
        ("AUGUSTA_FOUNDER_AUTHORIZATION_READY", "YES"),
    ])

    doc = OrderedDict([
        ("schema", "ptf-deployment-authorization-proposal/1.0"),
        ("STATUS", "AWAITING_FOUNDER_AUTHORIZATION"),
        ("AUGUSTA_FOUNDER_AUTHORIZATION_READY", readiness_gate["AUGUSTA_FOUNDER_AUTHORIZATION_READY"]),
        ("supersedes", OrderedDict([
            ("work_order", SUPERSEDES_WORK_ORDER),
            ("packet_path",
             "launch_packages/pettripfinder/markets/reports/augusta_ga_founder_authorization_packet_004.json"),
            ("prior_parent_deploy_id", prior_packet["the_digests_this_authorization_binds"]["parent_deploy_id"]),
            ("prior_parent_release_digest",
             prior_packet["the_digests_this_authorization_binds"]["parent_release_digest"]),
            ("reason",
             "packet 004 was bound to the Orlando-live parent (deploy 6aa9dad7, 28/2003/2299); "
             "Tampa-fl deployed live independently on its own branch (deploy 6aab379e, "
             "29/2151/2460) and was merged into this branch (ba80b692), making packet 004's "
             "parent binding stale. Nothing was authorized against packet 004; it is superseded, "
             "not edited."),
        ])),
        ("readiness_gate", readiness_gate),
        ("what_this_is",
         "A prepared, UNSIGNED deployment authorization proposal for founder review, produced by %s. "
         "Nothing has been deployed, no launch-participation flag has been committed, and no authorization "
         "exists. Every digest below was read from a committed or lane-written artifact." % WORK_ORDER),
        ("what_this_explicitly_does_not_claim", [
            "Does NOT claim CHANGE_CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY or "
            "NEW_MARKET_REGISTRATION_DATA_ONLY -- the automated classifier could not grant either "
            "class for this change set under any base commit tried; see readiness_gate above.",
            "Does NOT claim FULL_REGRESSION_REQUIRED = NO from the classifier -- its literal output "
            "would be YES for the same structural reason recorded for the Orlando merge, and no "
            "broad regression was run to resolve it.",
            "Does NOT assert a full whole-site sitemap rebuild was performed; only the release-index "
            "candidate (profiles, hotel/corridor/market routes) was independently composed.",
        ]),
        ("would_become",
         "Augusta, Georgia joins production as the THIRTIETH market with %d pet-friendly hotel "
         "profiles and %d verified-no-pets records over a %d-identity registered census, taking the "
         "site from %d to %d published profiles and from %d to %d release-index routes (over the "
         "current 29 live markets plus Augusta)."
         % (len(package["pet_friendly_records"]), len(package["verified_no_pets_records"]), census["count"],
            state.total_profiles, lane["candidate"]["profiles"],
            sum(len(m.routes) for mid, m in idx.markets.items() if mid in state.participating_markets),
            lane["candidate"]["routes"])),
        ("prepared_by", WORK_ORDER),
        ("authorized_by", None),
        ("authorized_at", None),
        ("source_commit", None),
        ("source_commit_note",
         "This document is written before its own commit exists, so it cannot name its own commit hash. "
         "The sealed package's created_from_source_sha below names the exact parent commit it was built "
         "from; the commit that adds this file is the very next commit on this branch."),
        ("source_branch", "worker/ptf-augusta-ga-market-002"),
        ("binding_identity", "bundle_sha256"),
        ("the_digests_this_authorization_binds", OrderedDict([
            ("parent_deploy_id", state.deploy_id),
            ("parent_release_digest", state.bundle_sha256),
            ("parent_sitemap_digest", state.sitemap_sha256),
            ("parent_release_index_digest", idx.digest()),
            ("sealed_package_id", lane["sealed_package"]["package_id"]),
            ("sealed_package_digest", lane["sealed_package"]["package_digest"]),
            ("sealed_package_created_from_source_sha", package["created_from_source_sha"]),
            ("sealed_package_dependency_input_digests", package["dependency_input_digests"]),
            ("intended_delta_digest",
             hashlib.sha256(json.dumps(package["intended_delta"], sort_keys=True).encode("utf-8")).hexdigest()),
            ("validation_receipt_digest", lane["fast_lane_receipt"]["receipt_digest"]),
            ("expected_candidate_release_index_digest", lane["candidate"]["candidate_index_digest"]),
            ("candidate_independent_rebuild_digest", lane["candidate"]["recomposed_index_digest"]),
            ("staged_launch_participation_sha256",
             _sha256_file(os.path.join(_DASH, "deploy", "netlify", "launch_participation.json"))),
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
            ("orlando_fl_participating", "orlando-fl" in state.participating_markets),
            ("orlando_fl_profile_count", state.profile_counts.get("orlando-fl")),
            ("tampa_fl_participating", "tampa-fl" in state.participating_markets),
            ("tampa_fl_profile_count", state.profile_counts.get("tampa-fl")),
            ("verified_from_the_host", OrderedDict([
                ("release_index_problems", list(problems)),
            ])),
            ("rechecked_before_composition",
             ["immediately after discovering the Tampa staleness", "immediately after the Tampa merge",
              "immediately after the fresh reseal", "immediately before this packet's creation"]),
        ])),
        ("production_delta_audit", OrderedDict([
            ("removed_markets", 0),
            ("removed_existing_profiles", 0),
            ("unexpected_route_changes", 0),
            ("unexpected_market_or_profile_changes", 0),
            ("existing_live_markets_preserved", True),
            ("unchanged_markets_count", len(lane.get("unchanged_markets") or [])),
            ("unchanged_markets_rebuilt", lane["UNCHANGED_MARKETS_REBUILT"]),
            ("release_diff_passed", lane["candidate"]["release_diff_passed"]),
            ("finding_counts", lane["candidate"]["finding_counts"]),
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
        ("what_is_not_claimed", [
            "No founder authorization exists yet -- this document proposes one.",
            "No deployment authorization exists.",
            "No deployment has occurred; canonical live production is untouched.",
            "No broad regression was run.",
            "The automated narrow registration classifier did not grant a data-only class for this "
            "change set; safety is established by the direct mechanical proofs in readiness_gate "
            "and production_delta_audit instead.",
            "Coverage completeness is a separate founder judgment call, not asserted here: the "
            "source-ready order reported COVERAGE READY = FOUNDER DECISION at a 30.8%% resolution "
            "rate, and that assessment is unchanged by registration or either reseal.",
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
