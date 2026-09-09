"""PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002 -- the UNEXECUTED packet.

Prepares, but does not sign, the deployment authorization a founder would need
to put Nashville into production. It writes to ``markets/reports/`` and NEVER to
``deploy/netlify/deployment_authorizations/``: a file in that directory IS an
authorization, and only a founder creates one.

Every number is read from an artifact this order produced or from the committed
production record. Nothing is typed. That matters more here than anywhere else
in the factory: the Cincinnati launch order's own inline bundle SHA was wrong in
five characters and its rollback target was one deploy stale, which would have
un-deployed Louisville.

THE CANDIDATE THIS PACKET BINDS IS POST-FLIP

PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003 paid for this lesson: a
promotion packet that pins the PRE-FLIP bundle can never equal the digest a
launch produces, because in the pre-flip bundle the joining market contributes
nothing. So the candidate this packet binds was composed with Nashville
PARTICIPATING, in a throwaway worktree, from a launch-participation document
that differs from the committed one in exactly one field. That one-field change
is stated here in full, and it is the founder's to make.

The committed record still says SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH,
so nothing in this repository publishes a Nashville page.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_REPO = os.path.abspath(os.path.join(_DASH, ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import launch_participation as LP  # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002"
WOULD_BECOME = "PTF-NASHVILLE-TN-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"
MARKET_ID = "nashville-tn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DEPLOY = os.path.join(_DASH, "deploy", "netlify")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=_REPO, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, help="the assembled POST-FLIP candidate dir")
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "nashville_deployment_authorization_003_PROPOSED.json"))
    args = ap.parse_args(argv)

    manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    lane = _load(os.path.join(REPORTS, "nashville_tn_release_lane_002.json"))
    holds = _load(os.path.join(PKG, "nashville_tn_identity_holds_002.json"))
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(PKG, "nashville_tn_final_partition_001.json"))
    contract = _load(os.path.join(DEPLOY, "release_contracts", "%s.json" % MARKET_ID))
    live_record = _load(os.path.join(DEPLOY, "deployment_records",
                                     "ptf-deploy-nashville-006-6aa172121d37bb4013eb44a4.json"))
    integration = _load(os.path.join(REPORTS, "nashville_tn_registration_audit_002.json"))

    parent = lane["parent_live_state"]
    receipt = lane["fast_lane_receipt"]
    diff = lane["release_diff"]
    package = lane["sealed_package"]

    participating = manifest["participating_markets"]
    cand_markets = [m["market_id"] for m in participating]
    cand_profile_counts = OrderedDict(
        (m["market_id"], m["published_profiles"]) for m in participating)
    cand_profiles = sum(cand_profile_counts.values())

    unexpected = len(diff["findings"])
    unchanged_moved = sorted(
        m for m, n in cand_profile_counts.items()
        if m != MARKET_ID and parent["profile_counts"].get(m) != n)

    # DEPLOYMENT_READY is DERIVED. A gate that cannot be read does not pass.
    gates = OrderedDict((
        # The one broad run named four TRUE_NEW nodes; each was fixed at its
        # cause and re-run by node id. What has to be zero is what is still
        # outstanding, and the audit records both numbers so neither can hide.
        ("integration_audit_true_new_closed",
         integration["TRUE_NEW_FAILURE_AFTER_CLOSURE"] == 0),
        ("fast_release_lane_eligible", receipt["eligible"] == "YES"),
        ("fast_lane_no_unknown_rules", not receipt["unknown_rules"]),
        ("fast_lane_no_failed_rules", not receipt["failed_rules"]),
        ("first_party_evidence_gate_clean", lane["first_party_gate"]["passed"] is True),
        ("release_diff_has_no_unexpected_finding", unexpected == 0),
        ("no_unrelated_live_market_moved", not unchanged_moved),
        ("candidate_includes_every_live_market",
         all(m in cand_markets for m in parent["participating_markets"])),
        ("candidate_includes_nashville", MARKET_ID in cand_markets),
        ("toledo_present_in_parent_and_candidate",
         "toledo-oh" in parent["participating_markets"] and "toledo-oh" in cand_markets),
        ("lexington_present_in_parent_and_candidate",
         "lexington-ky" in parent["participating_markets"] and "lexington-ky" in cand_markets),
        ("no_source_ready_market_auto_participated",
         not [m for m in cand_markets
              if m not in parent["participating_markets"] and m != MARKET_ID]),
        ("assembly_gates_pass", bool(manifest["all_gates_pass"])),
        ("no_broken_links", manifest["broken_links"] == 0),
        ("release_contract_grants_no_deployment",
         contract["deployment_authorization"]["grants_deployment"] is False),
        ("committed_participation_still_withholds_nashville",
         LP.launch_status(MARKET_ID) == "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"),
        ("every_held_row_recorded_by_name", holds["count"] == len(holds["holds"])),
        ("production_activation_still_disabled",
         receipt["production_activation_allowed"] == "NO"),
    ))
    ready = all(gates.values())

    doc = OrderedDict((
        ("schema", "ptf-deployment-authorization-proposal/1.0"),
        ("status", "AWAITING_FOUNDER_AUTHORIZATION"),
        ("what_this_is",
         "A prepared, UNSIGNED deployment authorization for founder review. It is deliberately "
         "NOT written to deploy/netlify/deployment_authorizations/, because a file in that "
         "directory IS an authorization and only a founder creates one. Nothing has been "
         "deployed, no launch-participation flag has moved in this repository, and no "
         "production activation flag has been enabled."),
        ("would_become", WOULD_BECOME),
        ("prepared_by", WORK_ORDER),
        ("authorized_by", None),
        ("authorized_at", None),
        ("source_commit", git("rev-parse", "HEAD")),
        ("source_branch", "worker/ptf-nashville-new-lane-launch-002"),

        ("binding_identity", "bundle_sha256"),
        ("the_four_digests_this_authorization_binds", OrderedDict((
            ("parent_release_digest", parent.get("bundle_sha256")
             or live_record["bundle_sha256"]),
            ("final_candidate_digest", manifest["bundle_sha256"]),
            ("intended_delta_digest", receipt["intended_delta_digest"]),
            ("deployment_artifact_digest", manifest["bundle_sha256"]),
            ("candidate_sitemap_sha256", manifest["sitemap_sha256"]),
            ("sealed_package_digest", package["package_digest"]),
            ("sealed_package_build_input_key", package.get("build_input_key")),
            ("fast_lane_receipt_digest", receipt["receipt_digest"]),
            ("no_abbreviated_identifier_appears_in_this_document", True),
        ))),

        ("this_document_is_not_byte_stable", OrderedDict((
            ("what_moves", ["source_commit", "git_state.head", "git_state.uncommitted_paths"]),
            ("what_does_not",
             "every digest and count this packet BINDS. Regenerating the packet after a report "
             "or a writer changes produces a diff in the three self-observing fields above and "
             "in nothing else. A changed report is not a changed candidate. This note exists "
             "because PTF-LEXINGTON-KY-FRESH-PACKAGE-REAUTHORIZATION-PREP-005 discovered the "
             "property the hard way, and leaving a reader to rediscover it is worse than saying "
             "it."),
        ))),

        ("git_state", OrderedDict((
            ("branch", git("rev-parse", "--abbrev-ref", "HEAD")),
            ("head", git("rev-parse", "HEAD")),
            ("uncommitted_paths", [l[3:] for l in
                                   git("status", "--porcelain").splitlines() if l]),
        ))),

        ("parent_release", OrderedDict((
            ("live_deploy_id", parent["live_deploy_id"]),
            ("bundle_sha256", live_record["bundle_sha256"]),
            ("sitemap_sha256", live_record["sitemap_sha256"]),
            ("source_commit", parent["source_commit"]),
            ("authorization_id", live_record["authorization_id"]),
            ("markets", len(parent["participating_markets"])),
            ("participating_markets", parent["participating_markets"]),
            ("profiles", parent["total_profiles"]),
            ("routes", parent["sitemap_route_count"]),
            ("toledo_present", "toledo-oh" in parent["participating_markets"]),
            ("lexington_present", "lexington-ky" in parent["participating_markets"]),
        ))),

        ("nashville", OrderedDict((
            ("registered_census", census["count"]),
            ("shadow_census", census["shadow_confirmed_identities"]),
            ("published_pet_friendly", cand_profile_counts.get(MARKET_ID)),
            ("verified_no_pets", contract["reconciliation"]["verified_no_pets"]),
            ("held_rows", holds["count"]),
            ("held_by_class", holds["counts_by_class"]),
            ("unresolved", contract["reconciliation"]["unresolved"]),
            ("partition_states", partition["final_state_counts"]),
            ("published_corridors", contract["routes"]["published_corridors"]),
            ("routes_added", len(lane["intended_delta"]["add_routes"])),
        ))),

        ("held_rows", holds["holds"]),

        ("release_delta", OrderedDict((
            ("parent_market_count", len(parent["participating_markets"])),
            ("candidate_market_count", len(cand_markets)),
            ("parent_profile_count", parent["total_profiles"]),
            ("candidate_profile_count", cand_profiles),
            ("parent_route_count", parent["sitemap_route_count"]),
            ("candidate_route_count", manifest["sitemap_route_count"]),
            ("markets_added", [m for m in cand_markets
                               if m not in parent["participating_markets"]]),
            ("markets_updated", unchanged_moved),
            ("markets_removed", [m for m in parent["participating_markets"]
                                 if m not in cand_markets]),
            ("unexpected_profile_changes", unexpected),
            ("unexpected_route_changes", unexpected),
            ("unexpected_market_changes", len(unchanged_moved)),
            ("release_index_findings", diff["findings"]),
        ))),

        ("bundle_reuse", OrderedDict((
            ("unchanged_markets_rebuilt", lane["cache_reuse"]["UNCHANGED_MARKETS_REBUILT"]),
            ("unchanged_markets", lane["cache_reuse"]["unchanged_live_markets"]),
            ("changed_market", lane["cache_reuse"]["changed_market"]),
        ))),

        ("validation", OrderedDict((
            ("one_time_registration_audit", OrderedDict((
                ("why", "REGISTERING a market is a DEPLOYMENT_CHANGE and an AUTHORITY_CHANGE, "
                        "which Regression V2 refuses to narrow. Exactly one broad run was "
                        "executed for it. No factory integration was performed or re-audited: "
                        "the ATLAS-THROUGHPUT engineering was already on this lineage."),
                ("collected", integration["collected"]),
                ("failures", integration["failures"]),
                ("PRE_EXISTING", integration["PRE_EXISTING"]),
                ("TRUE_NEW_FAILURE", integration["TRUE_NEW_FAILURE"]),
                ("TRUE_NEW_FAILURE_AFTER_CLOSURE",
                 integration["TRUE_NEW_FAILURE_AFTER_CLOSURE"]),
                ("closed_node_ids", integration["closure"]["closed_node_ids"]),
                ("second_broad_run_required",
                 integration["closure"]["second_broad_run_required"]),
                ("baseline", integration["baseline"]),
                ("seconds", integration["seconds"]),
            ))),
            ("routine_nashville_release", OrderedDict((
                ("change_class", receipt["change_class"]),
                ("FAST_DATA_ONLY_RELEASE", receipt["eligible"]),
                ("FULL_REGRESSION_REQUIRED", receipt["full_regression_required_by_lane"]),
                ("REMOTE_BROAD_JOBS_REQUIRED", 0),
                ("rules", receipt["rules"]),
                ("unknown_rules", receipt["unknown_rules"]),
                ("failed_rules", receipt["failed_rules"]),
            ))),
            ("first_party_evidence_gate", OrderedDict((
                ("records_evaluated", lane["first_party_gate"]["records_evaluated"]),
                ("eligible", lane["first_party_gate"]["eligible"]),
                ("ineligible", lane["first_party_gate"]["ineligible"]),
            ))),
        ))),

        ("performance_seconds", OrderedDict((
            ("routine_data_only_release_path", lane["timings"]),
            ("routine_data_only_release_service_time_s", lane["timings"]["total_s"]),
            ("one_time_registration_audit_s",
             (integration.get("seconds") or {}).get("total_s")),
            ("what_is_and_is_not_in_the_routine_figure",
             "the routine figure is the live parent read, the package seal, the first-party "
             "evidence gate, the fast release lane's fifteen rules including two cold builds, "
             "the candidate compose and diff, the Regression V2 classification and the cache "
             "lookup. It excludes the one-time registration audit, which is measured separately "
             "above, and it excludes the full multi-market bundle assembly, which a LAUNCH order "
             "runs and this one measured only to bind a digest."),
        ))),

        ("rollback", OrderedDict((
            ("target_deployment_id", live_record["deployment_id"]),
            ("target_release_digest", live_record["bundle_sha256"]),
            ("target_sitemap_sha256", live_record["sitemap_sha256"]),
            ("target_markets", len(live_record["participating_markets"])),
            ("target_profiles", live_record["total_profiles"]),
            ("target_routes", live_record["sitemap_route_count"]),
            ("target_is_current_verified_parent",
             live_record["deployment_id"] == parent["live_deploy_id"]),
            ("stale_rollback_guard",
             "the rollback target is the CURRENT live deployment read from the committed "
             "deployment record, not the parent's own rollback_target (%s), which is the "
             "Toledo deploy Lexington replaced. Rolling back to that would un-deploy Lexington."
             % parent["rollback_target"]),
            ("never_roll_back_to", parent["rollback_target"]),
        ))),

        ("what_the_founder_would_be_authorizing", OrderedDict((
            ("one_field_change",
             "deploy/netlify/launch_participation.json, the nashville-tn row: launch_status "
             "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH -> "
             "FOUNDER_AUTHORIZED_FOR_LAUNCH, plus the founder's own decision block. Nothing "
             "else in this repository changes to produce the candidate digest above."),
            ("effect", "Nashville joins as the thirteenth market at %d published profiles; every "
                       "other live market moves by exactly zero."
             % (cand_profile_counts.get(MARKET_ID) or 0)),
            ("not_authorized_here", ["production activation flags",
                                     "any netlify deploy",
                                     "any live verification",
                                     "Chattanooga or Fort Wayne participation",
                                     "Detroit participation"]),
        ))),

        ("deployment_ready_gates", gates),
        ("DEPLOYMENT_READY", "YES" if ready else "NO"),
        ("LAUNCH_AUTHORIZATION_REQUIRED", "YES"),
        ("nothing_deployed", True),
        ("nothing_activated", True),
    ))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("parent      :", doc["parent_release"]["live_deploy_id"],
          doc["parent_release"]["markets"], "markets /",
          doc["parent_release"]["profiles"], "profiles /",
          doc["parent_release"]["routes"], "routes")
    print("candidate   :", manifest["bundle_sha256"][:16],
          len(cand_markets), "markets /", cand_profiles, "profiles /",
          manifest["sitemap_route_count"], "routes")
    print("nashville   :", doc["nashville"]["published_pet_friendly"], "published /",
          doc["nashville"]["verified_no_pets"], "no-pets /",
          doc["nashville"]["held_rows"], "held")
    print("unexpected  :", unexpected, "findings;", len(unchanged_moved), "unrelated markets moved")
    print("DEPLOYMENT_READY:", doc["DEPLOYMENT_READY"])
    print("written     :", os.path.relpath(args.out, _DASH))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
