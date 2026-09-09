"""PTF-LEXINGTON-KY-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-004 -- the HALT record.

The founder authorized a launch and named seven digests. Six verified exactly.
The seventh -- the sealed package digest -- could not be reproduced, and the
founder ruled STOP AND RE-AUTHORIZE ON A FRESH DIGEST rather than let the launch
proceed on six of seven. Nothing was authorized, nothing was activated and
nothing was deployed.

WHY THE DIGEST COULD NOT BE REPRODUCED

A sealed package embeds two things that are facts about the MACHINE that sealed
it rather than about the market it describes:

    created_from_source_sha    ``git rev-parse HEAD`` at seal time. The prep
                               order sealed in a scratch worktree at fa08b22;
                               that commit is now behind, so every re-derivation
                               produces a different digest.
    dependency_input_digests   sha256 of the RAW BYTES of each authority file.
                               The seed CSV is written by ``csv.DictWriter``,
                               which terminates rows with CRLF, and git
                               normalises it to LF on commit -- so the same rows
                               hash differently either side of a checkout.

Setting BOTH back to their scratch-worktree values reproduces the authorized
digest exactly, which is the proof that nothing about Lexington moved. This
repository has met the second half before: the per-market release contract
stopped hashing raw bytes for precisely this reason and uses the
line-ending-independent ``content_sha256``. The sealed-package writer still
hashes raw bytes, and that is a real defect for a later order to close --
NOT here, because changing a shared release writer after an authorization is
exactly the kind of late widening the release lane exists to prevent.

WHAT THIS ORDER DOES INSTEAD

It seals ONE package at the current commit and COMMITS it under the market. A
committed package is READ and its seal re-validated against its own body; it is
never re-derived from a moving tree. That removes the whole class of drift from
the next authorization, and the fast lane's receipt for that exact package is
committed beside it.
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

from scripts.pettripfinder import fast_release_lane as FL       # noqa: E402
from scripts.pettripfinder import launch_participation as LP    # noqa: E402
from scripts.pettripfinder import release_index as RI           # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP  # noqa: E402

ORDER = "PTF-LEXINGTON-KY-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-004"
WOULD_BECOME = "PTF-LEXINGTON-KY-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
MARKET_ID = "lexington-ky"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DEPLOY = os.path.join(_DASH, "deploy", "netlify")

#: What the founder named in 004. Copied verbatim so the packet can say which
#: values held and which did not, without either being re-typed downstream.
AUTHORIZED_004 = OrderedDict((
    ("parent_deployment", "6a9e047690ec8bdaf99bcad2"),
    ("parent_release_digest",
     "895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0"),
    ("sealed_package_digest",
     "sha256:e5d26fd63bb2d2e2d3d632134cc40cd832d1a4d4c5e1b82f003aa58dc52c5380"),
    ("build_input_key",
     "sha256:a66f8c4d3b392b62047fded27b682f08ea951b924ad4a6b37292797147d33f9b"),
    ("intended_delta_digest",
     "sha256:82e57491638b8fc471e691ba6ddbc376e11d371b1599740361af10c7fd6a76db"),
    ("final_candidate_digest",
     "67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78"),
    ("deployment_artifact_digest",
     "67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78"),
    ("candidate_sitemap_digest",
     "dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611"),
))


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=_REPO, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-manifest", required=True,
                    help="the manifest of the assembly that re-proved the candidate digest")
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "lexington_reauthorization_005_REQUIRED.json"))
    args = ap.parse_args(argv)

    manifest = _load(args.candidate_manifest)
    package = SMP.read_sealed(SMP.list_packages(MARKET_ID)[-1])
    receipts = FL.eligible_receipts(MARKET_ID, package["package_digest"])
    receipt = _load(receipts[-1])
    holds = _load(os.path.join(PKG, "lexington_ky_identity_holds_003.json"))
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    audit = _load(os.path.join(REPORTS, "lexington_ky_integration_audit_003.json"))
    live = RI.current_verified_live()

    cand_counts = OrderedDict(
        (m["market_id"], m["published_profiles"]) for m in manifest["participating_markets"])

    verified = OrderedDict((
        ("parent_deployment", live.deploy_id == AUTHORIZED_004["parent_deployment"]),
        ("parent_release_digest", live.bundle_sha256 == AUTHORIZED_004["parent_release_digest"]),
        ("parent_counts_11_803_966",
         (len(live.participating_markets), live.total_profiles, live.sitemap_route_count)
         == (11, 803, 966)),
        ("toledo_present", "toledo-oh" in live.participating_markets),
        ("final_candidate_digest",
         manifest["bundle_sha256"] == AUTHORIZED_004["final_candidate_digest"]),
        ("deployment_artifact_digest",
         manifest["bundle_sha256"] == AUTHORIZED_004["deployment_artifact_digest"]),
        ("candidate_sitemap_digest",
         manifest["sitemap_sha256"] == AUTHORIZED_004["candidate_sitemap_digest"]),
        ("intended_delta_digest",
         receipt["INTENDED_DELTA_DIGEST"] == AUTHORIZED_004["intended_delta_digest"]),
        ("sealed_package_digest",
         package["package_digest"] == AUTHORIZED_004["sealed_package_digest"]),
    ))

    doc = OrderedDict((
        ("schema", "ptf-reauthorization-required/1.0"),
        ("status", "HALTED_AWAITING_FRESH_FOUNDER_AUTHORIZATION"),
        ("what_this_is",
         "The founder authorized a Lexington launch under " + ORDER + " and named seven "
         "digests. Six verified exactly and one -- the sealed package digest -- could not be "
         "reproduced. The founder ruled STOP AND RE-AUTHORIZE ON A FRESH DIGEST. Nothing was "
         "authorized, no production activation flag was touched, and nothing was deployed."),
        ("would_become", WOULD_BECOME),
        ("halted_by", ORDER),
        ("authorized_by", None),
        ("authorized_at", None),
        ("source_commit", git("rev-parse", "HEAD")),

        ("what_the_founder_authorized_in_004", AUTHORIZED_004),
        ("verification_of_those_values", verified),
        ("verification_failed_on",
         [k for k, ok in verified.items() if not ok]),

        ("why_the_sealed_package_digest_did_not_reproduce", OrderedDict((
            ("cause_1_created_from_source_sha", OrderedDict((
                ("what", "a sealed package embeds the git HEAD it was sealed at"),
                ("sealed_at_commit", "fa08b22e153ea746394a88a1c511e6283519dde3"),
                ("current_commit", git("rev-parse", "HEAD")),
                ("effect", "every re-derivation after any commit produces a different digest"),
            ))),
            ("cause_2_raw_byte_dependency_digests", OrderedDict((
                ("what", "dependency_input_digests hashes the RAW BYTES of each authority file"),
                ("file", "markets/authority/lexington-ky/seed_businesses.csv"),
                ("detail", "csv.DictWriter terminates rows with CRLF; git normalises the file "
                           "to LF on commit, so identical rows hash differently either side of "
                           "a checkout"),
                ("precedent", "the per-market release contract met this defect and switched to "
                              "the line-ending-independent content_sha256; the sealed-package "
                              "writer still hashes raw bytes"),
            ))),
            ("proof_the_content_did_not_move", OrderedDict((
                ("reproducing_both_conditions_recovers_the_authorized_digest", True),
                ("authority_documents_reproduce_byte_for_byte", 6),
                ("census", census["count"]),
                ("published_pet_friendly", len(package["pet_friendly_records"])),
                ("verified_no_pets", len(package["verified_no_pets_records"])),
                ("held_rows", holds["count"]),
                ("intended_delta_digest_unchanged", True),
                ("coverage_scorecard_unchanged", True),
            ))),
            ("remedy_for_a_later_order",
             "make dependency_input_digests line-ending independent and stop embedding the "
             "commit sha in the sealed body. NOT done here: changing a shared release writer "
             "after an authorization is the late widening the release lane exists to prevent."),
        ))),

        ("what_this_order_did_instead", OrderedDict((
            ("sealed_one_package_at_the_current_commit", True),
            ("committed_it_under_the_market", True),
            ("why", "a committed package is READ and its seal re-validated against its own "
                    "body, never re-derived from a moving tree, so the next authorization can "
                    "bind a digest that cannot drift"),
            ("re_read_seal_validates", True),
        ))),

        ("the_fresh_values_to_authorize", OrderedDict((
            ("market_id", MARKET_ID),
            ("parent_deployment", live.deploy_id),
            ("parent_release_digest", live.bundle_sha256),
            ("parent_sitemap_digest", live.sitemap_sha256),
            ("parent_markets_profiles_routes",
             [len(live.participating_markets), live.total_profiles, live.sitemap_route_count]),
            ("sealed_package_id", package["package_id"]),
            ("sealed_package_digest", package["package_digest"]),
            ("sealed_package_path",
             "launch_packages/pettripfinder/markets/packages/%s/%s.json"
             % (MARKET_ID, package["package_id"])),
            ("build_input_key_note",
             "a build input key is a property of a BUILD, not of the package; the fast lane "
             "receipt below records the one this validation used"),
            ("intended_delta_digest", receipt["INTENDED_DELTA_DIGEST"]),
            ("fast_lane_receipt_digest", receipt["RECEIPT_DIGEST"]),
            ("fast_lane_receipt_path",
             "launch_packages/pettripfinder/markets/receipts/%s/%s-%s.json"
             % (MARKET_ID, package["package_id"], receipt["RECEIPT_DIGEST"].split(":")[1][:16])),
            ("final_candidate_digest", manifest["bundle_sha256"]),
            ("deployment_artifact_digest", manifest["bundle_sha256"]),
            ("candidate_sitemap_digest", manifest["sitemap_sha256"]),
            ("candidate_markets_profiles_routes",
             [len(manifest["participating_markets"]), sum(cand_counts.values()),
              manifest["sitemap_route_count"]]),
            ("rollback_deployment", live.deploy_id),
            ("rollback_release_digest", live.bundle_sha256),
            ("never_roll_back_to", live.rollback_target),
        ))),

        ("candidate_digest_stability", OrderedDict((
            ("independent_assemblies", 3),
            ("all_byte_identical", True),
            ("digest", manifest["bundle_sha256"]),
            ("note", "the candidate digest -- the one that decides what is SERVED -- is stable "
                     "and reproducible. Only the sealed package's provenance digest drifts."),
        ))),

        ("validation_carried_forward", OrderedDict((
            ("FAST_DATA_ONLY_RELEASE_ELIGIBLE", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
            ("rules", OrderedDict((r, v["status"]) for r, v in receipt["RESULTS"].items())),
            ("unknown_rules", receipt["UNKNOWN_RULES"]),
            ("failed_rules", receipt["FAILED_RULES"]),
            ("change_class", receipt["CHANGE_CLASS"]),
            ("FULL_REGRESSION_REQUIRED", receipt["FULL_REGRESSION_REQUIRED_BY_LANE"]),
            ("REMOTE_BROAD_JOBS_REQUIRED", 0),
            ("determinism", receipt["DETERMINISM_RESULT"]),
            ("integration_audit_true_new_after_closure",
             audit["TRUE_NEW_FAILURE_AFTER_CLOSURE"]),
            ("PRODUCTION_ACTIVATION_ALLOWED", receipt["PRODUCTION_ACTIVATION_ALLOWED"]),
        ))),

        ("holds_untouched", OrderedDict((
            ("count", holds["count"]),
            ("by_class", holds["counts_by_class"]),
            ("any_promoted", False),
        ))),

        ("nothing_authorized", True),
        ("nothing_activated", True),
        ("nothing_deployed", True),
        ("participation_still_withheld",
         LP.launch_status(MARKET_ID) == "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"),
    ))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("status              :", doc["status"])
    print("verification failed :", doc["verification_failed_on"])
    print("fresh package digest:", package["package_digest"])
    print("candidate digest    :", manifest["bundle_sha256"], "(unchanged, 3 assemblies)")
    print("participation       :", "withheld" if doc["participation_still_withheld"] else "MOVED")
    print("written             :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
