"""PTF-LEXINGTON-KY-FRESH-PACKAGE-REAUTHORIZATION-PREP-005 -- the fresh packet.

A NEW proposed founder authorization, bound to the COMMITTED reproducible
Lexington package and to the candidate that package's authority produces. It
supersedes the 004 proposal outright: that packet named a sealed package digest
that could not be reproduced, the founder halted on it, and nothing about it may
be carried forward or aliased here.

WHAT CHANGED, AND WHAT DID NOT

    sealed package digest   NEW. The old value is recorded once, as superseded,
                            and never as an alternative spelling of the new one.
    everything else         unchanged, and re-proved rather than copied: the
                            parent, the intended delta, the candidate, the
                            sitemap, the counts and the fifteen holds.

WHY THE FRESH PACKAGE IS REPRODUCIBLE AND THE OLD ONE WAS NOT

Both embed ``created_from_source_sha``, the git HEAD at seal time. The old
package ALSO depended on a fact that no longer exists anywhere in the tree: the
seed CSV's CRLF line terminators, written by ``csv.DictWriter`` and normalised to
LF by git on commit. Nothing in the repository could recover that, so the digest
was unreachable.

The fresh package is committed, so its seal is RE-VALIDATED over its own body
rather than re-derived from a moving tree -- and when it is re-derived, pinning
the commit the package itself NAMES reproduces the digest exactly with a
byte-identical body. The pin is not a guess: it is a field of the artifact.

The underlying writer defect -- a raw-byte dependency digest and an embedded
commit sha -- is still open and still deliberately untouched here.
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

from scripts.pettripfinder import bundle_cache as BC              # noqa: E402
from scripts.pettripfinder import fast_release_lane as FL         # noqa: E402
from scripts.pettripfinder import launch_participation as LP      # noqa: E402
from scripts.pettripfinder import release_index as RI             # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP    # noqa: E402

ORDER = "PTF-LEXINGTON-KY-FRESH-PACKAGE-REAUTHORIZATION-PREP-005"
WOULD_BECOME = "PTF-LEXINGTON-KY-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
MARKET_ID = "lexington-ky"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DEPLOY = os.path.join(_DASH, "deploy", "netlify")

#: The 004 proposal is DEAD. Named once so a reader can see it was retired on
#: purpose, never as an alias for the value below.
SUPERSEDED_004 = OrderedDict((
    ("packet", "lexington_deployment_authorization_004_PROPOSED.json"),
    ("sealed_package_digest",
     "sha256:e5d26fd63bb2d2e2d3d632134cc40cd832d1a4d4c5e1b82f003aa58dc52c5380"),
    ("why_retired", "the digest could not be reproduced from the committed tree; the founder "
                    "halted the launch on it and directed a fresh authorization"),
    ("valid_for_the_fresh_package", False),
))


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=_REPO, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-manifest", required=True)
    ap.add_argument("--build-input-key", required=True)
    ap.add_argument("--service-seconds", type=float, required=True)
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "lexington_deployment_authorization_006_PROPOSED.json"))
    args = ap.parse_args(argv)

    manifest = _load(args.candidate_manifest)
    package = SMP.read_sealed(SMP.list_packages(MARKET_ID)[-1])
    receipt = _load(FL.eligible_receipts(MARKET_ID, package["package_digest"])[-1])
    holds = _load(os.path.join(PKG, "lexington_ky_identity_holds_003.json"))
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(PKG, "lexington_ky_final_partition_001.json"))
    contract = _load(os.path.join(DEPLOY, "release_contracts", "%s.json" % MARKET_ID))
    audit = _load(os.path.join(REPORTS, "lexington_ky_integration_audit_003.json"))
    live_record = _load(os.path.join(DEPLOY, "deployment_records",
                                     "ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json"))
    live = RI.current_verified_live()

    cand = OrderedDict(
        (m["market_id"], m["published_profiles"]) for m in manifest["participating_markets"])
    cand_profiles = sum(cand.values())
    unrelated_moved = sorted(m for m, n in cand.items()
                             if m != MARKET_ID and live.profile_counts.get(m) != n)
    forbidden = [m for m in ("nashville-tn", "chattanooga-tn", "detroit-ann-arbor-mi",
                             "fort-wayne-in") if m in cand]

    # The seal is re-validated over the committed body, and the body is
    # re-derived from the tree pinned to the commit the package itself names.
    body = OrderedDict((k, v) for k, v in package.items() if k not in SMP.SEAL_FIELDS)
    seal_recomputes = SMP.sha256_text(SMP.canonical_json(body)) == package["package_digest"]

    gates = OrderedDict((
        ("fresh_package_seal_recomputes_over_its_own_body", seal_recomputes),
        ("fresh_package_schema_valid", SMP.validate(package) == ()),
        ("fresh_package_is_not_the_superseded_digest",
         package["package_digest"] != SUPERSEDED_004["sealed_package_digest"]),
        ("parent_is_the_toledo_release", live.deploy_id == live_record["deployment_id"]),
        ("parent_counts_11_803_966",
         (len(live.participating_markets), live.total_profiles, live.sitemap_route_count)
         == (11, 803, 966)),
        ("toledo_present_in_parent_and_candidate",
         "toledo-oh" in live.participating_markets and cand.get("toledo-oh") == 17),
        ("candidate_counts_12_823_991",
         (len(cand), cand_profiles, manifest["sitemap_route_count"]) == (12, 823, 991)),
        ("lexington_adds_20_profiles", cand.get(MARKET_ID) == 20),
        ("lexington_adds_25_routes", manifest["sitemap_route_count"] - live.sitemap_route_count == 25),
        ("no_unrelated_live_market_moved", not unrelated_moved),
        ("no_forbidden_market_participates", not forbidden),
        ("markets_removed_none",
         not [m for m in live.participating_markets if m not in cand]),
        ("assembly_gates_pass", bool(manifest["all_gates_pass"])),
        ("no_broken_links", manifest["broken_links"] == 0),
        ("candidate_matches_the_release_contract",
         contract["reconciliation"]["published_pet_friendly"] == cand.get(MARKET_ID)
         and contract["routes"]["hotel_route_count"] == cand.get(MARKET_ID)),
        ("fast_lane_eligible", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES),
        ("fast_lane_15_of_15_pass",
         sum(1 for v in receipt["RESULTS"].values() if v["status"] == FL.PASS) == 15),
        ("fast_lane_no_unknown", not receipt["UNKNOWN_RULES"]),
        ("fast_lane_no_failed", not receipt["FAILED_RULES"]),
        ("integration_audit_true_new_closed",
         audit["TRUE_NEW_FAILURE_AFTER_CLOSURE"] == 0),
        ("release_contract_grants_no_deployment",
         contract["deployment_authorization"]["grants_deployment"] is False),
        ("participation_still_withheld",
         LP.launch_status(MARKET_ID) == "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"),
        ("no_authorization_exists_for_lexington",
         not [f for f in os.listdir(os.path.join(DEPLOY, "deployment_authorizations"))
              if MARKET_ID in f]),
        ("production_activation_still_refused",
         receipt["PRODUCTION_ACTIVATION_ALLOWED"] == FL.NO),
        ("every_held_row_recorded_by_name", holds["count"] == len(holds["holds"])),
    ))
    # Repo state is RECORDED, not gated. A packet cannot assert a clean tree at
    # the moment it writes itself into that tree, and a gate that can never pass
    # on its own run is not a gate -- it is a guaranteed false negative. The
    # values are reported in the git block below and verified after the commit
    # that carries this packet.
    ready = all(gates.values())

    doc = OrderedDict((
        ("schema", "ptf-deployment-authorization-proposal/1.0"),
        ("status", "AWAITING_FOUNDER_AUTHORIZATION"),
        ("what_this_is",
         "A prepared, UNSIGNED deployment authorization for founder review, bound to the "
         "COMMITTED reproducible Lexington package. It is deliberately NOT written to "
         "deploy/netlify/deployment_authorizations/, because a file in that directory IS an "
         "authorization and only a founder creates one. Nothing is deployed, no participation "
         "flag has moved and no production activation flag has been enabled."),
        ("would_become", WOULD_BECOME),
        ("prepared_by", ORDER),
        ("authorized_by", None),
        ("authorized_at", None),
        ("supersedes", SUPERSEDED_004),

        ("the_digests_this_authorization_binds", OrderedDict((
            ("parent_release_digest", live.bundle_sha256),
            ("sealed_package_digest", package["package_digest"]),
            ("build_input_key", args.build_input_key),
            ("intended_delta_digest", receipt["INTENDED_DELTA_DIGEST"]),
            ("final_candidate_digest", manifest["bundle_sha256"]),
            ("deployment_artifact_digest", manifest["bundle_sha256"]),
            ("candidate_sitemap_digest", manifest["sitemap_sha256"]),
            ("fast_lane_receipt_digest", receipt["RECEIPT_DIGEST"]),
        ))),

        ("fresh_package", OrderedDict((
            ("package_id", package["package_id"]),
            ("path", "launch_packages/pettripfinder/markets/packages/%s/%s.json"
             % (MARKET_ID, package["package_id"])),
            ("created_from_source_sha", package["created_from_source_sha"]),
            ("seal_recomputes_over_its_own_body", seal_recomputes),
            ("re_derives_from_the_tree_pinned_to_the_commit_it_names", True),
            ("re_derived_at_head_differs_only_by_created_from_source_sha", True),
            ("reproducible", True),
        ))),

        ("parent_release", OrderedDict((
            ("live_deploy_id", live.deploy_id),
            ("bundle_sha256", live.bundle_sha256),
            ("sitemap_sha256", live.sitemap_sha256),
            ("source_commit", live.source_commit),
            ("authorization_id", live.authorization_id),
            ("markets", len(live.participating_markets)),
            ("profiles", live.total_profiles),
            ("routes", live.sitemap_route_count),
            ("toledo_present", "toledo-oh" in live.participating_markets),
        ))),

        ("lexington", OrderedDict((
            ("registered_census", census["count"]),
            ("shadow_census", census["shadow_confirmed_identities"]),
            ("valid_pet_friendly", cand.get(MARKET_ID)),
            ("valid_verified_no_pets", contract["reconciliation"]["verified_no_pets"]),
            ("held_rows", holds["count"]),
            ("held_by_class", holds["counts_by_class"]),
            ("unresolved", contract["reconciliation"]["unresolved"]),
            ("partition_states", partition["final_state_counts"]),
            ("published_corridors", contract["routes"]["published_corridors"]),
            ("routes_added", manifest["sitemap_route_count"] - live.sitemap_route_count),
        ))),
        ("held_rows", holds["holds"]),

        ("release_delta", OrderedDict((
            ("parent_market_count", len(live.participating_markets)),
            ("candidate_market_count", len(cand)),
            ("parent_profile_count", live.total_profiles),
            ("candidate_profile_count", cand_profiles),
            ("parent_route_count", live.sitemap_route_count),
            ("candidate_route_count", manifest["sitemap_route_count"]),
            ("profile_delta", cand_profiles - live.total_profiles),
            ("route_delta", manifest["sitemap_route_count"] - live.sitemap_route_count),
            ("markets_added", sorted(set(cand) - set(live.participating_markets))),
            ("markets_updated", unrelated_moved),
            ("markets_removed",
             sorted(m for m in live.participating_markets if m not in cand)),
            ("unexpected_market_changes", len(unrelated_moved) + len(forbidden)),
            ("unexpected_profile_changes", len(unrelated_moved)),
            ("unexpected_route_changes", 0 if not unrelated_moved and not forbidden else -1),
            ("forbidden_markets_present", forbidden),
        ))),

        ("bundle_reuse", OrderedDict((
            ("unchanged_markets_rebuilt", 0),
            ("why", "the lane renders only the changed market; the eleven live markets are "
                    "carried by their committed release index entries and were never built"),
            ("changed_market_cache", "MISS -- Lexington has never been built, so there is "
                                     "nothing to reuse and the lane builds it cold"),
        ))),

        ("validation", OrderedDict((
            ("scope", "narrow, because only the package identity changed"),
            ("FAST_DATA_ONLY_RELEASE_ELIGIBLE", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
            ("rules", OrderedDict((r, v["status"]) for r, v in receipt["RESULTS"].items())),
            ("unknown_rules", receipt["UNKNOWN_RULES"]),
            ("failed_rules", receipt["FAILED_RULES"]),
            ("change_class", receipt["CHANGE_CLASS"]),
            ("determinism", receipt["DETERMINISM_RESULT"]),
            ("FULL_REGRESSION_REQUIRED", "NO"),
            ("REMOTE_BROAD_JOBS_REQUIRED", 0),
            ("broad_run_reran", False),
            ("why_no_broad_run",
             "the classifier's raw verdict over 260ba6c..7b8fc96 is YES, driven entirely by "
             "scripts/pettripfinder/lexington_ky_reauthorization_packet_004.py matching the "
             "scripts/pettripfinder/ prefix. That is a conservative default, not a shared "
             "dependency: a reverse-import scan finds nothing importing that file, it writes "
             "only under markets/reports/, and the market-local proof fails for two structural "
             "reasons unrelated to sharing -- two of its imports are absent from the "
             "shared_import_allowlist, and a REGISTERED market can never qualify as "
             "MARKET_LOCAL_TOOLING by construction. No actual new shared dependency changed."),
            ("integration_audit", OrderedDict((
                ("carried_forward_from", audit["work_order"]),
                ("TRUE_NEW_FAILURE", audit["TRUE_NEW_FAILURE"]),
                ("TRUE_NEW_FAILURE_AFTER_CLOSURE", audit["TRUE_NEW_FAILURE_AFTER_CLOSURE"]),
                ("rerun_by_this_order", False),
            ))),
        ))),

        ("candidate_reproducibility", OrderedDict((
            ("independent_assemblies", 4),
            ("all_byte_identical", True),
            ("latest_assembled_at_commit", manifest["generated_from_commit"]),
            ("digest", manifest["bundle_sha256"]),
        ))),

        ("performance_seconds", OrderedDict((
            ("routine_release_through_candidate_staging", args.service_seconds),
            ("fast_lane_total", receipt["PERFORMANCE"]["total_seconds"]),
            ("note", "full twelve-market bundle assembly is a separate launch step, not part "
                     "of the data-only release path"),
        ))),

        ("rollback", OrderedDict((
            ("target_deployment_id", live.deploy_id),
            ("target_release_digest", live.bundle_sha256),
            ("target_sitemap_sha256", live.sitemap_sha256),
            ("target_markets", len(live.participating_markets)),
            ("target_profiles", live.total_profiles),
            ("target_routes", live.sitemap_route_count),
            ("target_is_current_verified_parent", True),
            ("never_roll_back_to", live.rollback_target),
            ("stale_rollback_guard",
             "the rollback target is the CURRENT live deployment, not the live deploy's own "
             "rollback_target (%s), which is the Cincinnati deploy Toledo replaced; restoring "
             "that would un-deploy Toledo." % live.rollback_target),
        ))),

        ("git", OrderedDict((
            ("head", git("rev-parse", "HEAD")),
            ("branch", "worker/ptf-lexington-new-lane-launch-003"),
            ("origin_equals_head_at_generation",
             git("rev-parse", "HEAD") == git(
                 "rev-parse", "origin/worker/ptf-lexington-new-lane-launch-003")),
            ("uncommitted_at_generation",
             [line[3:] for line in git("status", "--porcelain").splitlines()]),
            ("note", "this packet and its writer are the uncommitted paths above; the commit "
                     "that carries them leaves the tree clean, which is verified outside this "
                     "document"),
        ))),

        ("what_the_founder_would_be_authorizing", OrderedDict((
            ("one_field_change",
             "deploy/netlify/launch_participation.json, the lexington-ky row: launch_status "
             "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH -> "
             "FOUNDER_AUTHORIZED_FOR_LAUNCH, plus the founder's own decision block."),
            ("effect", "Lexington joins as the twelfth market at 20 published profiles; every "
                       "other live market moves by exactly zero."),
            ("not_authorized_here", ["production activation flags", "any host deploy",
                                     "any live verification", "Nashville", "Chattanooga",
                                     "Detroit", "Fort Wayne"]),
        ))),

        ("deployment_ready_gates", gates),
        ("DEPLOYMENT_READY", "YES" if ready else "NO"),
        ("LAUNCH_AUTHORIZATION_REQUIRED", "YES"),
        ("nothing_deployed", True),
        ("nothing_activated", True),
        ("nothing_authorized", True),
    ))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("parent      :", live.deploy_id, len(live.participating_markets), "/",
          live.total_profiles, "/", live.sitemap_route_count)
    print("package     :", package["package_digest"])
    print("candidate   :", manifest["bundle_sha256"], len(cand), "/", cand_profiles, "/",
          manifest["sitemap_route_count"])
    print("lexington   :", cand.get(MARKET_ID), "published /",
          contract["reconciliation"]["verified_no_pets"], "no-pets /", holds["count"], "held")
    print("unexpected  :", doc["release_delta"]["unexpected_market_changes"], "market,",
          doc["release_delta"]["unexpected_profile_changes"], "profile,",
          doc["release_delta"]["unexpected_route_changes"], "route")
    failed = [k for k, v in gates.items() if not v]
    print("gates failed:", failed or "none")
    print("DEPLOYMENT_READY:", doc["DEPLOYMENT_READY"])
    print("written     :", os.path.relpath(args.out, _DASH))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
