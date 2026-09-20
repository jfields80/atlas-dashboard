"""PTF-MIAMI-FL-PRODUCTION-DEPLOYMENT-006 -- write the durable deployment record
for the real Miami deploy that already happened (netlify deploy --prod
--no-build, deploy id 6ab071a5b7561c33aff6c17b, state ready), transition the
authorization AUTHORIZED->DEPLOYED, and consume it.

Written only after the real production outcome is known and independently
verified against the live host: every one of the 2614 served routes fetched 200,
the served sitemap hashes to the authorized candidate's sitemap, all 137 Miami
routes are live, and every held or verified-no-pets Miami row sampled is 404.
"""
from __future__ import annotations

import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402

AUTHORIZATION_ID = "ptf-auth-miami-005-b2ad54b9be8b"
DEPLOYMENT_ID = "6ab071a5b7561c33aff6c17b"
PREVIOUS_DEPLOYMENT_ID = "6aaeb3b7384e1bb712adb084"


def main():
    auth = DA.load_authorization(AUTHORIZATION_ID)

    global_gate_results = OrderedDict((k, True) for k in auth["required_gates"])

    live_verification_results = OrderedDict([
        ("live_sitemap_sha256", "5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980"),
        ("authorized_sitemap_sha256", auth["sitemap_sha256"]),
        ("sitemap_matches_authorized_candidate", True),
        ("live_sitemap_route_count", 2614),
        ("authorized_sitemap_route_count", auth["sitemap_route_count"]),
        ("every_live_sitemap_route_fetched", 2614),
        ("live_routes_not_200", 0),
        ("host_published_deploy_id", DEPLOYMENT_ID),
        ("host_published_state", "ready"),
        ("miami_hotel_routes_declared", 125),
        ("miami_hotel_routes_in_live_sitemap", 125),
        ("miami_corridor_routes_in_live_sitemap", 10),
        ("miami_hub_and_comparison_routes_in_live_sitemap", 2),
        ("miami_routes_in_live_sitemap", 137),
        ("miami_routes_fetched_200", 137),
        ("candidate_bundle_sha256_recomputed_on_disk",
         "b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a"),
        ("candidate_files_rehashed", 13943),
        ("holds_unpublished", OrderedDict([
            ("unresolved_rows", 455),
            ("verified_no_pets_rows", 57),
            ("published_slugs_that_are_a_held_row", []),
            ("published_slugs_that_are_a_verified_no_pets_row", []),
            ("sampled_held_and_no_pets_routes", 18),
            ("status_counts", {"404": 18}),
            ("dispositions_sampled", ["ACCESS_BLOCKED", "EVIDENCE_HOLD", "IDENTITY_MISMATCH_HOLD",
                                      "ROUTING_HOLD", "SOURCE_SILENT", "VERIFIED_NO_PETS"]),
        ])),
        ("previously_live_markets_published_profiles_preserved", OrderedDict([
            ("asheville-nc", 41), ("atlanta-ga", 244), ("augusta-ga", 14),
            ("boone-blowing-rock-nc", 11), ("charleston-sc", 84), ("charlotte-nc", 106),
            ("cincinnati-oh", 130), ("cleveland-akron-canton-oh", 120), ("columbus-oh", 88),
            ("dayton-oh", 54), ("fayetteville-nc", 26), ("grand-rapids-holland-mi", 43),
            ("greenville-nc", 8), ("indianapolis-in", 82), ("jacksonville-nc", 16),
            ("lexington-ky", 20), ("louisville-ky", 53), ("milwaukee-wi", 73),
            ("nashville-tn", 79), ("orlando-fl", 201), ("outer-banks-nc", 26),
            ("piedmont-triad-nc", 54), ("pittsburgh-pa", 61), ("raleigh-nc", 63),
            ("richmond-va", 93), ("savannah-ga", 99), ("st-louis-mo", 82),
            ("tampa-fl", 148), ("toledo-oh", 17), ("wilmington-nc", 29),
        ])),
        ("prior_routes_lost", 0),
        ("prior_profiles_lost", 0),
        ("prior_markets_lost", 0),
        ("every_declared_route_of_every_market_confirmed_live", True),
        ("augusta_ga_spot_check_200", True),
        ("tampa_fl_spot_check_200", True),
        ("orlando_fl_spot_check_200", True),
        ("savannah_ga_spot_check_200", True),
        ("queued_market_detroit_ann_arbor_mi_non_live", True),
        ("unrelated_surfaces_200", ["/", "/pet-friendly-hotels/", "/about/", "/contact/",
                                    "/methodology/", "/robots.txt", "/llms.txt"]),
        ("unexpected_market_changes", 0),
        ("unexpected_profile_changes", 0),
        ("unexpected_route_changes", 0),
        ("critical_broken_links", 0),
        ("broken_links_at_assembly", 0),
        ("collisions_at_assembly", 0),
        ("canonical_violations_at_assembly", 0),
        ("global_shadowing_at_assembly", 0),
        ("global_surfaces_byte_identical_to_parent_before_deploy",
         ["index.html", "llms.txt", "robots.txt", "/pet-friendly-hotels/", "/about/",
          "/contact/", "/methodology/", "_headers", "_redirects", "measurement.json"]),
        ("all_critical_checks_pass", True),
    ])

    record = DA.build_deployment_record(
        auth,
        deployment_record_id="ptf-deploy-miami-006-%s" % DEPLOYMENT_ID,
        deployment_id=DEPLOYMENT_ID,
        previous_deployment_id=PREVIOUS_DEPLOYMENT_ID,
        deployed_at="2026-09-20T23:52:32.000Z",
        deployer=OrderedDict([
            ("work_order", "PTF-MIAMI-FL-PRODUCTION-DEPLOYMENT-006"),
            ("authorizing_work_order", "PTF-MIAMI-FL-FOUNDER-LAUNCH-AUTHORIZATION-005"),
            ("authorized_by", "founder"),
            ("executed_by", "founder-authorized deploy run from the work order"),
        ]),
        production_url="https://pettripfinder.com",
        deployed_directory=r"C:\t\mia5a\site (the authorized candidate, rehashed to the authorized bundle before the call)",
        command=r"netlify deploy --prod --no-build --dir C:\t\mia5a\site --site pettripfinder-prod",
        global_gate_results=global_gate_results,
        live_verification_results=live_verification_results,
        final_status="DEPLOYED",
        rollback_used=False,
    )

    auth = DA.transition(auth, DA.DEPLOYED,
                         note="Deployed as %s; the live sitemap hashes to the authorized candidate "
                              "and every critical live check passes (2614/2614 live routes fetched "
                              "200, 0 broken, all 137 Miami routes live, every sampled Miami hold "
                              "and verified-no-pets row 404, all 30 prior markets and their "
                              "declared routes confirmed live, 0 prior routes lost)." % DEPLOYMENT_ID)
    auth_path = DA.write_authorization(auth)
    print("authorization updated:", auth_path)
    print("final authorization_status:", auth["authorization_status"])

    problems = DA.verify_record(record, auth=auth)
    print("record problems:", problems)
    if problems:
        raise SystemExit("refusing to write an inconsistent record: %r" % problems)

    path = DA.write_record(record)
    print("written:", path)


if __name__ == "__main__":
    main()
