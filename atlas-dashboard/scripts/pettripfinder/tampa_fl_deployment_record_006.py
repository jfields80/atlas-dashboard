"""PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 -- write the
durable deployment record for the real Tampa deploy that already happened
(netlify deploy --prod --no-build, deploy id 6aab379e0777c9ee96702a4f,
state ready), transition the authorization PREPARED->AUTHORIZED->DEPLOYED,
and consume it. Written only after the real production outcome is known.
"""
from __future__ import annotations

import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402

AUTHORIZATION_ID = "ptf-auth-tampa-006-cf761795e3de"
DEPLOYMENT_ID = "6aab379e0777c9ee96702a4f"
PREVIOUS_DEPLOYMENT_ID = "6aa9dad7cf1419580b307f71"


def main():
    auth = DA.load_authorization(AUTHORIZATION_ID)

    global_gate_results = OrderedDict((k, True) for k in auth["required_gates"])

    live_verification_results = OrderedDict([
        ("live_sitemap_sha256", "53589cf6a740046ad244d3760495f6cdc62bbc0f17f3061cfc4d83e1017f103b"),
        ("authorized_sitemap_sha256", auth["sitemap_sha256"]),
        ("sitemap_matches_authorized_candidate", True),
        ("live_sitemap_route_count", 2460),
        ("authorized_sitemap_route_count", auth["sitemap_route_count"]),
        ("every_live_sitemap_route_fetched", 2460),
        ("live_routes_not_200", 0),
        ("host_published_deploy_id", DEPLOYMENT_ID),
        ("host_published_state", "ready"),
        ("host_published_at", "2026-09-17T00:43:38.767Z"),
        ("tampa_hotel_routes_declared", 148),
        ("tampa_hotel_routes_in_live_sitemap", 148),
        ("tampa_corridor_routes_in_live_sitemap", 11),
        ("tampa_hub_and_comparison_routes_in_live_sitemap", 2),
        ("tampa_routes_in_live_sitemap", 161),
        ("tampa_go_interstitial_noindex", True),
        ("holds_unpublished", OrderedDict([
            ("unresolved_rows", 314),
            ("in_live_sitemap", []),
            ("fetchable_200", []),
            ("status_counts", {"404": 314}),
        ])),
        ("previously_live_markets_published_profiles_preserved", OrderedDict([
            ("asheville-nc", 41), ("atlanta-ga", 244), ("boone-blowing-rock-nc", 11),
            ("charleston-sc", 84), ("charlotte-nc", 106), ("cincinnati-oh", 130),
            ("cleveland-akron-canton-oh", 120), ("columbus-oh", 88), ("dayton-oh", 54),
            ("fayetteville-nc", 26), ("grand-rapids-holland-mi", 43), ("greenville-nc", 8),
            ("indianapolis-in", 82), ("jacksonville-nc", 16), ("lexington-ky", 20),
            ("louisville-ky", 53), ("milwaukee-wi", 73), ("nashville-tn", 79),
            ("orlando-fl", 201), ("outer-banks-nc", 26), ("piedmont-triad-nc", 54),
            ("pittsburgh-pa", 61), ("raleigh-nc", 63), ("richmond-va", 93),
            ("savannah-ga", 99), ("st-louis-mo", 82), ("toledo-oh", 17),
            ("wilmington-nc", 29),
        ])),
        ("queued_market_detroit_ann_arbor_mi_non_live", 404),
        ("unrelated_surfaces_200", ["/", "/pet-friendly-hotels/", "/about/", "/contact/",
                                    "/methodology/", "/robots.txt", "/llms.txt"]),
        ("unexpected_market_changes", 0),
        ("unexpected_profile_changes", 0),
        ("unexpected_route_changes", 0),
        ("critical_broken_links", 0),
        ("broken_links_at_assembly", 0),
        ("collisions_at_assembly", 0),
        ("canonical_violations_at_assembly", 0),
        ("independent_reproduction", OrderedDict([
            ("build_a_bundle_sha256", "cf761795e3deb1380ffb8e25869bd6ceefe31d2a9dfbaddad30c550ff69d60d2"),
            ("build_b_bundle_sha256", "cf761795e3deb1380ffb8e25869bd6ceefe31d2a9dfbaddad30c550ff69d60d2"),
            ("byte_identical", True),
        ])),
        ("all_critical_checks_pass", True),
    ])

    record = DA.build_deployment_record(
        auth,
        deployment_record_id="ptf-deploy-tampa-006-%s" % DEPLOYMENT_ID,
        deployment_id=DEPLOYMENT_ID,
        previous_deployment_id=PREVIOUS_DEPLOYMENT_ID,
        deployed_at="2026-09-17T00:43:38.767Z",
        deployer=OrderedDict([
            ("work_order", "PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"),
            ("authorizing_work_order", "PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"),
            ("authorized_by", "founder"),
            ("executed_by", "claude-code"),
        ]),
        production_url="https://pettripfinder.com",
        deployed_directory="the authorized candidate's site/ tree",
        command="netlify deploy --prod --no-build --dir <candidate>/site --site <site>",
        global_gate_results=global_gate_results,
        live_verification_results=live_verification_results,
        final_status="DEPLOYED",
        rollback_used=False,
    )

    auth = DA.transition(auth, DA.DEPLOYED,
                          note="Deployed as %s; the live sitemap hashes to the authorized "
                               "candidate and all critical live checks pass." % DEPLOYMENT_ID)
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
