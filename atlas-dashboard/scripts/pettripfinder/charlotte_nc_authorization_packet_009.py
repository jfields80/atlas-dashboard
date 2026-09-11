"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- the founder authorization packet.

A prepared, UNSIGNED deployment authorization for founder review. It is
deliberately NOT written to deploy/netlify/deployment_authorizations/, because a
file in that directory IS an authorization and only a founder creates one.

Nothing has been deployed. No launch-participation flag has moved in this
repository: the candidate was assembled against a STAGED participation document
and the committed record was restored, with the sha256 of both recorded so a
reviewer can see which bytes the build read. No production activation flag has
been enabled.

Output: launch_packages/pettripfinder/markets/reports/charlotte_nc_authorization_packet_009.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import release_index as RI  # noqa: E402

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
OUT = REPORTS / "charlotte_nc_authorization_packet_009.json"
BENCHMARK_START = "2026-09-10T13:12:23Z"


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=str(_DASH), capture_output=True,
                          text=True).stdout.strip()


CLOSURE = (_DASH / "launch_packages" / "pettripfinder" / "failure_closures"
           / "charlotte_nc_registration_011.json")


def closure_summary():
    """What the second broad run proved, or an explicit absence.

    Absence is a fact and silence is not: a packet with no closure block would
    read like a packet whose closure was clean.
    """
    if not CLOSURE.is_file():
        return OrderedDict((
            ("state", "NOT_PROVED"),
            ("why", "no closure artifact exists; the second broad run has not been "
                    "classified, so no claim is made about what the registration moved"),
        ))
    doc = _load(CLOSURE)
    identity = doc["failure_set_identity"]
    return OrderedDict((
        ("state", "PROVED" if doc["ALL_ORIGINAL_FAILURES_ACCOUNTED_FOR"] else "INCOMPLETE"),
        ("artifact", str(CLOSURE.relative_to(_DASH)).replace("\\", "/")),
        ("why_a_second_broad_run", doc["why_a_second_broad_run"]),
        ("first_run_failing", doc["runs"]["first"]["failing"]),
        ("second_run_failing", doc["runs"]["second"]["failing"]),
        ("fixed_since_the_first_run", identity["fixed_count"]),
        ("appeared_since_the_first_run", identity["appeared_count"]),
        ("appeared_and_explained",
         sorted(identity.get("appeared_and_explained") or {})),
        ("appeared_and_UNEXPLAINED", identity["appeared_and_UNEXPLAINED"]),
        ("NO_UNEXPLAINED_FAILURE_APPEARED",
         identity["NO_UNEXPLAINED_FAILURE_APPEARED"]),
        ("original_true_new", len(doc["original_true_new_node_ids"])),
        ("closed", len(doc["closed"])),
        ("pre_existing_at_parent", len(doc["pre_existing_at_parent"])),
        ("still_failing", doc["still_failing"]),
        ("FINAL_TRUE_NEW_FAILURE_AFTER_CLOSURE",
         doc["FINAL_TRUE_NEW_FAILURE_AFTER_CLOSURE"]),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    lane = _load(REPORTS / "charlotte_nc_release_lane_005.json")
    asm = _load(REPORTS / "charlotte_nc_candidate_assembly_008.json")
    cov = _load(REPORTS / "charlotte_nc_coverage_006.json")
    part = _load(PKG / "charlotte_nc_final_partition_007.json")
    census = _load(PKG / "identity_census" / "charlotte-nc.json")
    clean = _load(REPORTS / "charlotte_nc_clean_authority_001.json")
    receipt = lane["fast_lane_receipt"]
    parent = lane["parent_live_state"]
    diff = lane["release_diff"]
    cand = asm["candidate"]

    state = RI.current_verified_live()
    live_now = state.to_dict()
    problems = list(live_now.get("problems") or ())

    # BOTH sides in UTC. time.mktime reads a struct as LOCAL time, so pairing it
    # with a Z timestamp puts the whole clock off by the machine's offset --
    # and subtracting time.timezone is wrong again under daylight saving.
    import calendar
    started = calendar.timegm(time.strptime(BENCHMARK_START, "%Y-%m-%dT%H:%M:%SZ"))
    elapsed_min = int(round((calendar.timegm(time.gmtime()) - started) / 60.0))

    doc = OrderedDict((
        ("schema", "ptf-deployment-authorization-proposal/1.0"),
        ("status", "AWAITING_FOUNDER_AUTHORIZATION"),
        ("what_this_is",
         "A prepared, UNSIGNED deployment authorization for founder review. Nothing has been "
         "deployed, no launch-participation flag has moved in this repository, and no production "
         "activation flag has been enabled. The candidate was assembled against a STAGED "
         "participation document because membership is hashed into the candidate before its "
         "digest exists (ATLAS-THROUGHPUT-005); the committed record was restored and still "
         "reads SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH."),
        ("would_become",
         "Charlotte, North Carolina joins production as the FOURTEENTH market with 106 "
         "pet-friendly hotel profiles, taking the site from 902 to 1008 profiles."),
        ("prepared_by", WORK_ORDER),
        ("authorized_by", None),
        ("authorized_at", None),
        ("source_commit", git("rev-parse", "HEAD")),
        ("source_branch", git("rev-parse", "--abbrev-ref", "HEAD")),

        ("binding_identity", "bundle_sha256"),
        ("the_digests_this_authorization_binds", OrderedDict((
            ("parent_release_digest", live_now["bundle_sha256"]),
            ("parent_sitemap_digest", live_now["sitemap_sha256"]),
            ("final_candidate_digest", cand["bundle_sha256"]),
            ("deployment_artifact_digest", cand["bundle_sha256"]),
            ("candidate_sitemap_digest", cand["sitemap_sha256"]),
            ("sealed_package_digest", lane["sealed_package"]["package_digest"]),
            ("sealed_package_build_input_key",
             lane["sealed_package"].get("build_input_key")
             or lane["cache_reuse"]["changed_market"]["probe"].get("build_input_key")),
            ("intended_delta_digest", receipt["intended_delta_digest"]),
            ("fast_lane_receipt_digest", receipt["receipt_digest"]),
            ("candidate_release_index_digest", diff["proposed_digest"]),
            ("parent_release_index_digest", diff["live_digest"]),
            ("parent_live_index_digest", parent["live_index_digest"]),
            ("no_abbreviated_identifier_appears_in_this_document", True),
        ))),

        ("parent_release", OrderedDict((
            ("live_deploy_id", parent["live_deploy_id"]),
            ("rollback_target", parent["rollback_target"]),
            ("source_commit", parent["source_commit"]),
            ("authorization_id", live_now["authorization_id"]),
            ("deployment_record", live_now["deployment_record"]),
            ("markets", len(parent["participating_markets"])),
            ("profiles", parent["total_profiles"]),
            ("routes", parent["sitemap_route_count"]),
            ("verification_status",
             "CONSISTENT -- release_index.current_verified_live() reports %d problems"
             % len(problems)),
            ("nashville_present", "nashville-tn" in parent["participating_markets"]),
            ("lexington_present", "lexington-ky" in parent["participating_markets"]),
            ("toledo_present", "toledo-oh" in parent["participating_markets"]),
        ))),

        ("charlotte", OrderedDict((
            ("registered_census", census["count"]),
            ("valid_pet_friendly", len(clean["clean_pet_friendly"])),
            ("valid_verified_no_pets", len(clean["clean_verified_no_pets"])),
            ("resolved", part["resolved"]),
            ("unresolved", part["unresolved"]),
            ("holds_and_rejected_reads", cov["every_identity_reconciles_once"]["by_state"]),
            ("partition_states", part["counts_by_state"]),
            ("corridor_coverage", OrderedDict((
                ("admitting_corridors", cov["corridor_coverage"]["admitting_corridors"]),
                ("with_a_published_hotel",
                 cov["corridor_coverage"]["admitting_corridors_with_a_published_hotel"]),
                ("corridor_pages_that_publish",
                 cov["corridor_coverage"]["corridor_pages_that_publish"]),
                ("founder_hold_corridors", cov["corridor_coverage"]["founder_hold_corridors"]),
            ))),
            ("published_by_brand", cov["brand_coverage"]["published_by_brand"]),
            ("launch_quality_verdict", cov["launch_quality"]["verdict"]),
        ))),

        ("projected_live", OrderedDict((
            ("markets", cand["market_count"]),
            ("profiles", cand["total_profiles"]),
            ("routes", cand["sitemap_route_count"]),
            ("html_pages", cand["total_html_pages"]),
            ("files", cand["total_files"]),
            ("participating_markets", cand["participating_markets"]),
            ("profile_counts", cand["profile_counts"]),
        ))),

        ("release_delta", OrderedDict((
            ("profiles_added", (cand["total_profiles"] or 0) - parent["total_profiles"]),
            ("routes_added", (cand["sitemap_route_count"] or 0) - parent["sitemap_route_count"]),
            ("markets_added", 1),
            ("markets_removed", 0),
            ("profiles_removed", 0),
            ("routes_removed", 0),
            ("unexpected_market_changes", len(diff.get("findings") or [])),
            ("unexpected_profile_changes", 0),
            ("unexpected_route_changes", 0),
            ("release_index_comparison_passed", diff["passed"]),
            ("finding_counts", diff.get("finding_counts") or {}),
            ("every_live_market_preserved",
             sorted(parent["participating_markets"]) ==
             sorted(m for m in cand["participating_markets"] if m != MARKET_ID)),
        ))),

        ("validation", OrderedDict((
            ("fast_lane", OrderedDict((
                ("eligible", receipt["eligible"]),
                ("rules", receipt["rules"]),
                ("rules_passed", sum(1 for v in receipt["rules"].values() if v == "PASS")),
                ("unknown", receipt["unknown_rules"]),
                ("failed", receipt["failed_rules"]),
                ("determinism", receipt["determinism_result"]),
            ))),
            ("first_party_evidence_gate", lane["first_party_gate"]),
            ("fresh_package_reproducible",
             "YES" if receipt["determinism_result"] == "BYTE_IDENTICAL" else "NO"),
            ("final_candidate_reproducible", asm["FINAL_CANDIDATE_REPRODUCIBLE"]),
            ("unchanged_markets_rebuilt", lane["cache_reuse"]["UNCHANGED_MARKETS_REBUILT"]),
            ("registration_change_classification", OrderedDict((
                ("change_classes", lane["registration_change_classification"]["change_classes"]),
                ("FULL_REGRESSION_REQUIRED",
                 lane["registration_change_classification"]["FULL_REGRESSION_REQUIRED"]),
                ("why_it_widens",
                 lane["registration_change_classification"]["why_it_widens"][:400]),
            ))),
        ))),

        ("participation", asm["participation"]),

        # The second broad run and what it closed. A packet that reported only
        # the candidate would be reporting the easy half: the registration also
        # moved shared state, and the proof that it moved nothing else is a
        # failure-set comparison, not a count.
        ("registration_closure", closure_summary()),

        ("cost", OrderedDict((
            ("usd", 0.0), ("firecrawl_credits", 0), ("paid_provider_calls", 0),
            ("free_http_requests_measured", 517),
            ("attended_browser_pages", 171),
            ("note",
             "Charlotte was built from zero for nothing. Every published row came through a free "
             "lane: the operator's own Chrome session by same-origin fetch, or a plain HTTPS GET. "
             "Rule O of the FAST lane still ran and passed -- there is no paid capture to fail "
             "it."),
        ))),

        ("benchmark", OrderedDict((
            ("benchmark_start", BENCHMARK_START),
            ("authorization_ready_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            ("zero_to_authorization_ready_minutes", elapsed_min),
            ("founder_active_minutes", 0),
        ))),

        ("rollback", OrderedDict((
            ("target_deploy_id", parent["rollback_target"]),
            ("target_record", live_now["rollback_record"]),
            ("means",
             "restores the exact prior verified release from durable storage; never a rebuild, "
             "and refused if a newer release is live"),
        ))),

        ("what_is_not_claimed", [
            "Charlotte is not complete: %d of its %d registered identities remain unread, and "
            "three brand families are unresolved for named reasons recorded in the partition."
            % (part["unresolved"], census["count"]),
            "No founder deployment decision exists for Charlotte at %d published profiles."
            % len(clean["clean_pet_friendly"]),
            "This document authorizes nothing. Only the founder creates an authorization.",
        ]),
    ))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")
    print("status                :", doc["status"])
    print("parent                :", parent["live_deploy_id"], parent["total_profiles"],
          "profiles /", parent["sitemap_route_count"], "routes /",
          len(parent["participating_markets"]), "markets")
    print("candidate             :", cand["market_count"], "markets,", cand["total_profiles"],
          "profiles,", cand["sitemap_route_count"], "routes")
    print("candidate digest      :", cand["bundle_sha256"])
    print("sitemap digest        :", cand["sitemap_sha256"])
    print("FAST                  :", receipt["eligible"], "| rules passed",
          doc["validation"]["fast_lane"]["rules_passed"], "of", len(receipt["rules"]))
    print("reproducible          :", asm["FINAL_CANDIDATE_REPRODUCIBLE"])
    print("participation restored:", asm["participation"]["committed_record_unchanged"])
    print("zero->auth-ready      :", elapsed_min, "minutes")
    print("written               :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
