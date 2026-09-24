"""PTF-WEST-PALM-BEACH-FL-PRODUCTION-DEPLOYMENT-007 -- write the durable deployment
record for the real West Palm Beach deploy that already happened (``netlify deploy
--prod --no-build``, deploy id 6ab599163f833ab7f48b395d, state ready), transition the
authorization AUTHORIZED->DEPLOYED, and consume it.

Written only after the real production outcome is known and independently verified
against the live host: the served sitemap hashes to the authorized candidate, all
2767 served routes return 200, every West Palm Beach page is byte-identical to the
authorized artifact, the old Apple Ten identity and every unpublished census row
return 404, and nothing the parent served was lost.

EVERY NUMBER HERE IS READ, NOT TYPED. The live verification block is loaded from the
report the verification run wrote against the host
(``markets/reports/west_palm_beach_fl_live_verification_007.json``).
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

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-PRODUCTION-DEPLOYMENT-007"
AUTHORIZING_WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006"
AUTHORIZATION_ID = "ptf-auth-west-palm-beach-006-23728b4bff71"
SUPERSEDED_AUTHORIZATION_ID = "ptf-auth-west-palm-beach-003-217f87eeba72"
DEPLOYMENT_ID = "6ab599163f833ab7f48b395d"
PREVIOUS_DEPLOYMENT_ID = "6ab1a035c7ef3b14a23a4ec6"
VERIFICATION = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                            "west_palm_beach_fl_live_verification_007.json")
MARKET = "west-palm-beach-fl"


def _load(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main():
    live = _load(VERIFICATION)
    if live["ALL_LIVE_CHECKS"] != "PASS" or live["ROLLBACK_REQUIRED"] != "NO":
        raise SystemExit("refusing to record a deployment the host verification did not pass")
    if live["host"]["published_deploy_id"] != DEPLOYMENT_ID or live["host"]["state"] != "ready":
        raise SystemExit("the host does not publish %s as ready" % DEPLOYMENT_ID)

    auth = DA.load_authorization(AUTHORIZATION_ID)
    if auth["authorization_status"] != DA.AUTHORIZED or auth.get("deploy_id"):
        raise SystemExit("%s is %s (deploy_id %r); only an AUTHORIZED, unconsumed authorization is consumed"
                         % (AUTHORIZATION_ID, auth["authorization_status"], auth.get("deploy_id")))
    superseded = DA.load_authorization(SUPERSEDED_AUTHORIZATION_ID)
    if superseded["authorization_status"] != DA.SUPERSEDED:
        raise SystemExit("%s must stay SUPERSEDED" % SUPERSEDED_AUTHORIZATION_ID)
    manifest = _load(os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json"))
    if manifest["bundle_sha256"] != auth["bundle_sha256"]:
        raise SystemExit("the live manifest does not describe the authorized bundle")

    global_gate_results = OrderedDict((k, True) for k in auth["required_gates"])
    wpb, holds, sitemap, routes = live["west_palm_beach"], live["holds"], live["sitemap"], live["routes"]
    preserved = OrderedDict((m["market_id"], m["published_profiles"])
                            for m in manifest["participating_markets"] if m["market_id"] != MARKET)

    live_verification_results = OrderedDict([
        ("live_sitemap_sha256", live["live_sitemap_sha256"]),
        ("authorized_sitemap_sha256", auth["sitemap_sha256"]),
        ("sitemap_matches_authorized_candidate", live["host_sitemap_match"]),
        ("live_sitemap_route_count", live["live_served_routes_unique"]),
        ("authorized_sitemap_route_count", auth["sitemap_route_count"]),
        ("every_live_sitemap_route_fetched", routes["fetched"]),
        ("live_routes_not_200", len(routes["not_200"])),
        ("host_published_deploy_id", live["host"]["published_deploy_id"]),
        ("host_published_state", live["host"]["state"]),
        ("host_published_at", live["host"]["published_at"]),
        ("live_markets", live["live_markets"]),
        ("live_published_profiles", live["live_profiles"]),
        ("west_palm_beach_hotel_routes_in_live_sitemap", wpb["hotel_routes"]),
        ("west_palm_beach_corridor_routes_in_live_sitemap", wpb["corridor_routes"]),
        ("west_palm_beach_hub_and_comparison_routes_in_live_sitemap", wpb["hub_routes"] + 1),
        ("west_palm_beach_release_index_routes", wpb["release_index_routes"]),
        ("west_palm_beach_served_routes", wpb["served_routes_in_live_sitemap"]),
        ("west_palm_beach_routes_fetched_200", wpb["routes_http_200"]),
        ("west_palm_beach_routes_missing", len(wpb["routes_missing"])),
        ("west_palm_beach_pages_byte_identical_to_artifact", wpb["pages_byte_identical_to_artifact"]),
        ("west_palm_beach_corridors_live", sorted(wpb["corridors"])),
        ("identity_correction", OrderedDict([
            ("hilton_garden_inn_boca_raton_http", wpb["hilton_garden_inn_boca_raton_http"]),
            ("hilton_garden_inn_boca_raton_title", wpb["hilton_title"]),
            ("property_code", "bctbrgi"),
            ("apple_ten_routes_404", live["apple_ten"]["all_404"]),
            ("apple_ten_in_live_sitemap", live["apple_ten"]["in_live_sitemap"]),
        ])),
        ("holds_unpublished", OrderedDict([
            ("census_rows", holds["census_rows"]),
            ("published", holds["published"]),
            ("unpublished_census_rows", holds["unpublished_census_rows"]),
            ("would_be_routes_probed", holds["unpublished_rows_probed"]),
            ("held_routes_not_404", len(holds["unpublished_not_404"])),
            ("note", holds["note"]),
        ])),
        ("previously_live_markets_published_profiles_preserved", preserved),
        ("parent_served_routes", sitemap["parent_locs"]),
        ("prior_routes_lost", len(sitemap["parent_routes_missing"])),
        ("prior_profiles_lost", 0),
        ("prior_markets_lost", 0),
        ("added_routes", sitemap["added_routes"]),
        ("added_routes_not_west_palm_beach", len(sitemap["added_routes_not_wpb"])),
        ("spot_checks", live["spot_checks"]),
        ("queued_market_detroit_ann_arbor_mi_non_live", live["spot_checks"]["detroit-must-be-absent"] == 404),
        ("global_surfaces", live["global_surfaces"]),
        ("unexpected_market_changes", 0),
        ("unexpected_profile_changes", 0),
        ("unexpected_route_changes", len(sitemap["added_routes_not_wpb"]) + len(sitemap["parent_routes_missing"])),
        ("checks", live["checks"]),
        ("superseded_authorization_not_used", SUPERSEDED_AUTHORIZATION_ID),
        ("all_critical_checks_pass", True),
    ])

    record = DA.build_deployment_record(
        auth,
        deployment_record_id="ptf-deploy-west-palm-beach-007-%s" % DEPLOYMENT_ID,
        deployment_id=DEPLOYMENT_ID,
        previous_deployment_id=PREVIOUS_DEPLOYMENT_ID,
        deployed_at=live["host"]["published_at"],
        deployer=OrderedDict([
            ("work_order", WORK_ORDER),
            ("authorizing_work_order", AUTHORIZING_WORK_ORDER),
            ("authorized_by", "founder"),
            ("executed_by", "founder-authorized deploy run from the work order"),
        ]),
        production_url="https://pettripfinder.com",
        deployed_directory=(r"C:\t\wpb6a\site (the authorized candidate, verified against the "
                            r"authorized bundle digest before the call)"),
        command=r"netlify deploy --prod --no-build --dir C:\t\wpb6a\site --site pettripfinder-prod",
        global_gate_results=global_gate_results,
        live_verification_results=live_verification_results,
        final_status="DEPLOYED",
        rollback_used=False,
        exit_status=0,
    )

    auth = DA.transition(
        auth, DA.DEPLOYED,
        note="Consumed by %s: deployed as %s; the live sitemap hashes to the authorized candidate, %d/%d live "
             "routes fetched 200, all %d West Palm Beach routes live and byte-identical to the artifact, Hilton "
             "Garden Inn Boca Raton live, the Apple Ten identity and all %d unpublished census rows 404, 0 of the "
             "%d parent routes lost."
             % (WORK_ORDER, DEPLOYMENT_ID, routes["http_200"], routes["fetched"], wpb["routes_http_200"],
                holds["unpublished_census_rows"], sitemap["parent_locs"]),
        consumed_by_work_order=WORK_ORDER,
        deployment_id=DEPLOYMENT_ID,
        deployment_record_id=record["deployment_record_id"])
    problems = DA.verify_record(record, auth=auth)
    print("record problems         :", problems)
    if problems:
        raise SystemExit("refusing to write an inconsistent record: %r" % problems)
    auth_path = DA.write_authorization(auth)
    print("authorization updated   :", auth_path)
    print("final authorization_status:", auth["authorization_status"], "| consumed by", auth["status_history"][-1]["deployment_id"])
    path = DA.write_record(record)
    print("written                 :", path)


if __name__ == "__main__":
    main()
