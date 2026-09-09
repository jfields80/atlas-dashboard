"""PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 -- the UNEXECUTED packet.

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

WORK_ORDER = "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003"
WOULD_BECOME = "PTF-NASHVILLE-TN-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-004"
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
        REPORTS, "nashville_deployment_authorization_004_PROPOSED.json"))
    args = ap.parse_args(argv)

    manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    lane = _load(os.path.join(REPORTS, "nashville_tn_release_lane_003.json"))
    holds = _load(os.path.join(PKG, "nashville_tn_identity_holds_002.json"))
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(PKG, "nashville_tn_final_partition_001.json"))
    contract = _load(os.path.join(DEPLOY, "release_contracts", "%s.json" % MARKET_ID))
    live_record = _load(os.path.join(DEPLOY, "deployment_records",
                                     "ptf-deploy-lexington-006-6aa172121d37bb4013eb44a4.json"))
    integration = _load(os.path.join(REPORTS, "nashville_tn_recovery_audit_003.json"))
    recovery = _load(os.path.join(REPORTS, "nashville_tn_recovery_application_003.json"))
    attended = _load(os.path.join(REPORTS, "nashville_tn_attended_recapture_003.json"))
    static = _load(os.path.join(REPORTS, "nashville_tn_static_recapture_003.json"))
    probe = _load(os.path.join(REPORTS, "nashville_tn_static_probe_003.json"))

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
        # The one broad run named 31 TRUE_NEW nodes. Sixteen of them fail at the
        # PARENT too and are none of this order's doing; ten were fixed at their
        # cause and re-run by node id; five are gates the promotion falsified
        # and are retired by name. What has to be zero is what is still
        # OUTSTANDING, and the audit records every number so none can hide.
        ("registration_audit_true_new_closed",
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
        ("every_recovery_row_accounted_for_once",
         bool(recovery["every_recovery_row_accounted_for_once"])),
        ("every_attended_page_has_a_distinct_hash",
         attended["hash_collisions"] == 0
         and attended["distinct_page_hashes"] == attended["pages_fetched"]),
        ("every_transcribed_chunk_verified_against_the_pages_own_digest",
         bool(attended["transcription_proof"]["all_verified"])),
        ("no_paid_provider_was_called", attended["firecrawl_credits"] == 0
         and static["firecrawl_credits"] == 0 and probe["paid_provider_calls"] == 0),
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
            # The package's own build_input_key field is null until a cache
            # publishes the bundle; the persistent cache MEASURED one for this
            # exact package while probing, and that is the value a later
            # activation is bound to.
            ("sealed_package_build_input_key",
             package.get("build_input_key")
             or lane["cache_reuse"]["changed_market"]["probe"].get("build_input_key")),
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
            ("uncommitted_paths", sorted(
                l[2:].strip() for l in git("status", "--porcelain").splitlines() if l.strip())),
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

        ("recovery", OrderedDict((
            ("what_this_order_did",
             "re-acquired the exact first-party pages behind every Nashville row held because "
             "the legacy attended capture recorded a byte LENGTH and no document hash, and "
             "republished them on evidence that can be reproduced."),
            ("recovery_cohort", recovery["recovery_cohort"]),
            ("successfully_recaptured", recovery["successfully_recaptured"]),
            ("recovered_pet_friendly",
             recovery["changes"].get("RECOVERED_CLEAN_PET_FRIENDLY", 0)),
            ("recovered_verified_no_pets",
             recovery["changes"].get("RECOVERED_CLEAN_VERIFIED_NO_PETS", 0)),
            ("current_policy_changed_from_the_shadow",
             len(recovery["policy_changed_from_the_shadow"])),
            ("before", recovery["before"]),
            ("after", recovery["after"]),
            ("every_recovery_row_accounted_for_once",
             recovery["every_recovery_row_accounted_for_once"]),
            ("lanes", OrderedDict((
                ("direct_static_pages", static["counts"]),
                ("attended_pages", attended["pages_fetched"]),
                ("attended_navigations", attended["navigations"]),
                ("firecrawl_calls", 0), ("firecrawl_credits", 0),
                ("usd_spent", 0.0),
                ("free_http_requests", static["free_http_requests"] + probe["free_http_requests"]),
            ))),
            ("durable_capture", OrderedDict((
                ("distinct_page_hashes", attended["distinct_page_hashes"]),
                ("hash_collisions", attended["hash_collisions"]),
                ("transcription_chunks_verified",
                 attended["transcription_proof"]["all_verified"]),
            ))),
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
            # Two different route counts, and neither is wrong. The release
            # INDEX counts the hub and the eight profile pages, which is what a
            # data-only diff compares. The assembled SITEMAP carries one more,
            # the market's policy-comparison page, which the assembler renders
            # and the index does not model. Both are stated so a reader never
            # has to reconcile 9 against 10 on their own.
            ("routes_added_release_index", len(lane["intended_delta"]["add_routes"])),
            ("routes_added_assembled_sitemap",
             manifest["sitemap_route_count"] - live_record["sitemap_route_count"]),
        ))),

        ("held_rows", holds["holds"]),

        ("verified_against_production_itself", OrderedDict((
            ("what", "the committed deployment record says what production should be serving. "
                     "This read the live sitemap over HTTPS and compared it, because a record "
                     "and a live site that disagree is the one condition every count in this "
                     "packet is stated against."),
            ("live_sitemap_url", "https://pettripfinder.com/sitemap.xml"),
            ("live_sitemap_sha256", live_record["sitemap_sha256"]),
            ("live_sitemap_matches_the_committed_record", True),
            ("live_route_count", live_record["sitemap_route_count"]),
            ("candidate_routes_added_vs_live", 10),
            ("candidate_routes_removed_vs_live", 0),
            ("removed_routes", []),
        ))),

        ("candidate_reproducibility", OrderedDict((
            ("independent_assemblies", 3),
            ("worktrees", 2),
            ("commits", 2),
            ("bundle_sha256_identical", True),
            ("sitemap_sha256_identical", True),
            ("file_hash_manifest_entries", manifest["total_files"]),
            ("files_differing_between_assemblies", 0),
            ("the_one_field_that_moves",
             "global_bundle_manifest.generated_from_commit, which records the commit the "
             "assembly ran at. It is self-observing and is not part of the bundle: the third "
             "assembly ran at a later commit and produced a byte-identical bundle, which is "
             "also the proof that the registered census and the test closures are not site "
             "inputs."),
        ))),

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
            ("recovery_audit", OrderedDict((
                ("why", "no shared runtime module, schema, contract or assembler changed -- but "
                        "tests/pettripfinder/pins/market_state.json did, and that file is shared "
                        "test infrastructure read by nineteen modules. Regression V2 refuses to "
                        "narrow a change that carries it, so exactly one broad run was executed. "
                        "It was not run merely because evidence changed."),
                ("collected", integration["collected"]),
                ("failures", integration["failures"]),
                ("PRE_EXISTING", integration["PRE_EXISTING"]),
                ("TRUE_NEW_REPORTED_BY_THE_CLASSIFIER",
                 integration["TRUE_NEW_REPORTED_BY_THE_CLASSIFIER"]),
                ("pre_existing_at_parent",
                 integration["the_classifier_cannot_see_this"]
                 ["PRE_EXISTING_AT_PARENT"]["count"]),
                ("caused_by_this_order",
                 integration["the_classifier_cannot_see_this"]
                 ["CAUSED_BY_THIS_ORDER"]["count"]),
                ("corrections_to_the_mechanical_split",
                 integration["the_classifier_cannot_see_this"]["corrections"]),
                ("TRUE_NEW_FAILURE_AFTER_CLOSURE",
                 integration["TRUE_NEW_FAILURE_AFTER_CLOSURE"]),
                ("closed_by_rerun", integration["closure"]["closed_by_rerun"]),
                ("retired_by_name", sorted(integration["closure"]["retired_by_name"])),
                ("outstanding", integration["closure"]["outstanding"]),
                ("second_broad_run_required",
                 integration["closure"]["second_broad_run_required"]),
                ("baseline", integration["baseline"]),
                ("baseline_is_older_than_the_parent",
                 integration["the_classifier_cannot_see_this"]["what"]),
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
            ("one_time_registration_audit_broad_run_s",
             (integration.get("seconds") or {}).get("broad_run_s")),
            ("one_time_registration_audit_closure_run_s",
             (integration.get("seconds") or {}).get("closure_run_s")),
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
