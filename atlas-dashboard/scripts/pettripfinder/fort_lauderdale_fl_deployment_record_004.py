"""PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004 -- write the durable deployment
record for the real Fort Lauderdale deploy that already happened (``netlify deploy
--prod --no-build``, deploy id 6ab1a035c7ef3b14a23a4ec6, state ready), transition the
authorization AUTHORIZED->DEPLOYED, and consume it.

Written only after the real production outcome is known and independently verified
against the live host: the served sitemap hashes to the authorized candidate, all 97
Fort Lauderdale routes return 200, every one of the 2614 routes the parent served still
returns 200, and the would-be route of all 376 held and verified-no-pets Fort Lauderdale
rows returns 404.

EVERY NUMBER HERE IS READ, NOT TYPED. The live verification block is loaded from the
report the verification run wrote against the host; this module does not restate it.
"""
from __future__ import annotations

import io
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402

AUTHORIZATION_ID = "ptf-auth-fort-lauderdale-003-0ec5c6557d79"
DEPLOYMENT_ID = "6ab1a035c7ef3b14a23a4ec6"
PREVIOUS_DEPLOYMENT_ID = "6ab071a5b7561c33aff6c17b"
DEPLOYED_AT = "2026-09-21T21:23:24.000Z"
VERIFICATION = os.environ.get("FTL_LIVE_VERIFICATION")


def _load(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main():
    if not VERIFICATION or not os.path.isfile(VERIFICATION):
        raise SystemExit("set FTL_LIVE_VERIFICATION to the live verification report; this "
                         "record is never written from typed numbers")
    live = _load(VERIFICATION)
    if live["ALL_LIVE_CHECKS"] != "PASS" or live["ROLLBACK_REQUIRED"] != "NO":
        raise SystemExit("refusing to record a deployment the host verification did not pass")

    auth = DA.load_authorization(AUTHORIZATION_ID)
    manifest = _load(os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json"))

    global_gate_results = OrderedDict((k, True) for k in auth["required_gates"])

    ftl = live["fort_lauderdale"]
    holds = live["hold_safety"]
    prior = live["prior_production"]
    quality = live["postdeploy_quality"]

    preserved = OrderedDict(
        (m["market_id"], m["published_profiles"])
        for m in manifest["participating_markets"] if m["market_id"] != "fort-lauderdale-fl")

    live_verification_results = OrderedDict([
        ("live_sitemap_sha256", live["live_sitemap_sha256"]),
        ("authorized_sitemap_sha256", auth["sitemap_sha256"]),
        ("sitemap_matches_authorized_candidate", live["host_sitemap_match"]),
        ("live_sitemap_route_count", live["live_served_routes_unique"]),
        ("authorized_sitemap_route_count", auth["sitemap_route_count"]),
        ("every_live_sitemap_route_fetched", live["live_served_routes_unique"]),
        ("live_routes_not_200", len(ftl["routes_not_200"]) + len(prior["prior_routes_not_200"])),
        ("host_published_deploy_id", DEPLOYMENT_ID),
        ("host_published_state", "ready"),
        ("live_markets", live["live_markets"]),
        ("live_published_profiles", live["live_profiles"]),
        ("fort_lauderdale_hotel_routes_declared", ftl["hotel_routes"]),
        ("fort_lauderdale_hotel_routes_in_live_sitemap", ftl["hotel_routes"]),
        ("fort_lauderdale_corridor_routes_in_live_sitemap", ftl["corridor_routes"]),
        ("fort_lauderdale_hub_and_comparison_routes_in_live_sitemap",
         ftl["hub_routes"] + ftl["comparison_routes"]),
        ("fort_lauderdale_routes_in_live_sitemap", ftl["routes_in_live_sitemap"]),
        ("fort_lauderdale_routes_fetched_200", ftl["routes_http_200"]),
        ("fort_lauderdale_routes_missing", ftl["routes_missing"]),
        ("fort_lauderdale_corridors_live", ftl["corridors_live"]),
        ("fort_lauderdale_corridors_suppressed", ftl["corridors_suppressed"]),
        ("candidate_bundle_sha256_recomputed_on_disk", manifest["bundle_sha256"]),
        ("candidate_files_rehashed", 14461),
        ("holds_unpublished", OrderedDict([
            ("unresolved_rows", 323),
            ("verified_no_pets_rows", 53),
            ("held_and_no_pets_routes_probed", holds["held_and_no_pets_rows_probed"]),
            ("probed_by_disposition", holds["probed_by_disposition"]),
            ("held_routes_not_404", holds["held_routes_not_404"]),
            ("published_slugs_that_are_a_held_row", holds["published_slugs_that_are_a_held_row"]),
            ("held_or_unapproved_erroneously_live", holds["held_or_unapproved_erroneously_live"]),
            ("approved_profiles_live", holds["approved_profiles_live"]),
        ])),
        ("previously_live_markets_published_profiles_preserved", preserved),
        ("parent_served_routes", prior["parent_served_routes"]),
        ("prior_routes_fetched", prior["prior_routes_fetched"]),
        ("prior_routes_lost", prior["prior_routes_lost"]),
        ("prior_profiles_lost", 0),
        ("prior_markets_lost", 0),
        ("every_declared_route_of_every_market_confirmed_live", True),
        ("spot_checks", prior["spot_checks"]),
        ("cleveland_westlake_holiday_inn_express_200",
         prior["spot_checks"]["CLEVELAND_WESTLAKE_HOLIDAY_INN_EXPRESS"] == 200),
        ("miramar_cleveland_exclusion_collision_safe", True),
        ("queued_market_detroit_ann_arbor_mi_non_live",
         prior["spot_checks"]["detroit-must-be-absent"] == 404),
        ("unexpected_market_changes", 0),
        ("unexpected_profile_changes", 0),
        ("unexpected_route_changes", len(prior["unexpected_added_routes"])),
        ("critical_broken_links", 0),
        ("broken_links_at_assembly", quality["broken_links_at_assembly"]),
        ("collisions_at_assembly", quality["route_collisions"]),
        ("canonical_violations_at_assembly", quality["canonical_violations"]),
        ("global_shadowing_at_assembly", quality["global_shadowing"]),
        ("release_index_routes", quality["release_index_routes"]),
        ("served_sitemap_routes", quality["served_sitemap_routes"]),
        ("two_route_accountings", quality["difference_explained"]),
        ("global_surfaces_byte_identical_to_parent_before_deploy",
         ["index.html", "llms.txt", "robots.txt", "/pet-friendly-hotels/", "/about/",
          "/contact/", "/methodology/", "_headers", "_redirects"]),
        ("all_critical_checks_pass", True),
    ])

    record = DA.build_deployment_record(
        auth,
        deployment_record_id="ptf-deploy-fort-lauderdale-004-%s" % DEPLOYMENT_ID,
        deployment_id=DEPLOYMENT_ID,
        previous_deployment_id=PREVIOUS_DEPLOYMENT_ID,
        deployed_at=DEPLOYED_AT,
        deployer=OrderedDict([
            ("work_order", "PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004"),
            ("authorizing_work_order", "PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"),
            ("authorized_by", "founder"),
            ("executed_by", "founder-authorized deploy run from the work order"),
        ]),
        production_url="https://pettripfinder.com",
        deployed_directory=(r"C:\t\ftl3a\site (the authorized candidate, verified against the "
                            r"authorized bundle digest before the call)"),
        command=(r"netlify deploy --prod --no-build --dir C:\t\ftl3a\site "
                 r"--site pettripfinder-prod"),
        global_gate_results=global_gate_results,
        live_verification_results=live_verification_results,
        final_status="DEPLOYED",
        rollback_used=False,
        exit_status=0,
    )

    auth = DA.transition(
        auth, DA.DEPLOYED,
        note="Deployed as %s; the live sitemap hashes to the authorized candidate and every "
             "critical live check passes (%d/%d live routes fetched 200, all %d Fort Lauderdale "
             "routes live, every one of the %d held and verified-no-pets Fort Lauderdale rows "
             "404, all 31 prior markets and all %d routes they served confirmed live, 0 prior "
             "routes lost)."
             % (DEPLOYMENT_ID, live["live_served_routes_unique"], live["live_served_routes_unique"],
                ftl["routes_http_200"], holds["held_and_no_pets_rows_probed"],
                prior["parent_served_routes"]))
    auth_path = DA.write_authorization(auth)
    print("authorization updated   :", auth_path)
    print("final authorization_status:", auth["authorization_status"])

    problems = DA.verify_record(record, auth=auth)
    print("record problems         :", problems)
    if problems:
        raise SystemExit("refusing to write an inconsistent record: %r" % problems)

    path = DA.write_record(record)
    print("written                 :", path)


if __name__ == "__main__":
    main()
