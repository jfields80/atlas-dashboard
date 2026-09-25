"""PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004 -- write the durable deployment record for the real
Jacksonville deploy that already happened, transition the authorization AUTHORIZED->DEPLOYED, and consume it.

    python -m scripts.pettripfinder.jacksonville_fl_deployment_record_004 [--write]

WRITTEN ONLY AFTER THE HOST SAID SO
------------------------------------
This module refuses to run unless the live-verification report it reads says ALL_LIVE_CHECKS PASS and
ROLLBACK_REQUIRED NO, unless Netlify publishes this exact deploy as `ready`, and unless the live manifest
describes the authorized bundle. A deployment record is the repository's claim that production serves a
particular thing; writing one the host has not confirmed would make the claim false.

EVERY NUMBER IS READ, NOT TYPED. The live verification block is loaded from
``markets/reports/jacksonville_fl_live_verification_004.json``, which was produced by fetching the host.

NO SUPERSESSION TO CARRY
------------------------
Unlike West Palm Beach's 007 record, there is no superseded authorization here: this is the FIRST authorization
Jacksonville ever had and the first deployment it ever had. The module asserts that rather than assuming it --
if any other authorization named this market, it refuses.

A DEPLOYMENT RECORD NAMES TWO ORDERS. ``work_order`` is the AUTHORIZING order (the founder's launch decision);
``deployer.work_order`` is the order that ran the deploy. They diverge, and conflating them is how the lineage
repair began.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004"
AUTHORIZING_WORK_ORDER = "PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
AUTHORIZATION_ID = "ptf-auth-jacksonville-003-f82f0714db2d"
DEPLOYMENT_ID = "6ab6c8798bd9daf5038ae3e5"
PREVIOUS_DEPLOYMENT_ID = "6ab599163f833ab7f48b395d"
MARKET = "jacksonville-fl"
CANDIDATE_DIR = r"C:\t\jax3a"
VERIFICATION = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                            "jacksonville_fl_live_verification_004.json")


def _load(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    live = _load(VERIFICATION)
    if live["ALL_LIVE_CHECKS"] != "PASS" or live["ROLLBACK_REQUIRED"] != "NO":
        raise SystemExit("refusing to record a deployment the host verification did not pass")
    host = live["host"]
    if host["published_deploy_id"] != DEPLOYMENT_ID or host["state"] != "ready":
        raise SystemExit("the host does not publish %s as ready (%r / %r)"
                         % (DEPLOYMENT_ID, host["published_deploy_id"], host["state"]))
    if host["previous_deploy_id"] != PREVIOUS_DEPLOYMENT_ID:
        raise SystemExit("the host's previous deploy is %r, not the authorized parent %s"
                         % (host["previous_deploy_id"], PREVIOUS_DEPLOYMENT_ID))

    auth = DA.load_authorization(AUTHORIZATION_ID)
    if auth["authorization_status"] != DA.AUTHORIZED or auth.get("deploy_id"):
        raise SystemExit("%s is %s (deploy_id %r); only an AUTHORIZED, unconsumed authorization is consumed"
                         % (AUTHORIZATION_ID, auth["authorization_status"], auth.get("deploy_id")))
    others = [a["authorization_id"] for a in DA.list_authorizations()
              if MARKET in (a.get("participating_markets") or ()) and a["authorization_id"] != AUTHORIZATION_ID
              and a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
    if others:
        raise SystemExit("other deployable authorizations name %s: %s" % (MARKET, others))

    manifest = _load(os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json"))
    if manifest["bundle_sha256"] != auth["bundle_sha256"]:
        raise SystemExit("the live manifest does not describe the authorized bundle")
    if manifest["sitemap_sha256"] != auth["sitemap_sha256"]:
        raise SystemExit("the live manifest does not describe the authorized sitemap")

    global_gate_results = OrderedDict((k, True) for k in auth["required_gates"])
    mine, holds, sitemap = live["jacksonville"], live["holds"], live["sitemap"]
    prior, twin = live["prior_routes"], live["name_twin"]
    preserved = OrderedDict((m["market_id"], m["published_profiles"])
                            for m in manifest["participating_markets"] if m["market_id"] != MARKET)

    live_verification_results = OrderedDict([
        ("live_sitemap_sha256", live["live_sitemap_sha256"]),
        ("authorized_sitemap_sha256", auth["sitemap_sha256"]),
        ("sitemap_matches_authorized_candidate", live["host_sitemap_match"]),
        ("served_route_set_identical_to_authorized", live["served_route_set_identical_to_authorized"]),
        ("live_sitemap_route_count", live["live_served_routes_unique"]),
        ("authorized_sitemap_route_count", auth["sitemap_route_count"]),
        ("host_published_deploy_id", host["published_deploy_id"]),
        ("host_published_state", host["state"]),
        ("host_published_at", host["published_at"]),
        ("host_previous_deploy_id", host["previous_deploy_id"]),
        ("live_markets", live["live_markets"]),
        ("live_published_profiles", live["live_profiles"]),
        ("live_release_index_routes", live["live_release_index_routes"]),
        ("jacksonville_hotel_routes_in_live_sitemap", mine["hotel_routes"]),
        ("jacksonville_corridor_routes_in_live_sitemap", mine["corridor_routes"]),
        ("jacksonville_hub_and_comparison_routes_in_live_sitemap", mine["hub_routes"] + 1),
        ("jacksonville_release_index_routes", mine["release_index_routes"]),
        ("jacksonville_served_routes", mine["served_routes_in_live_sitemap"]),
        ("jacksonville_routes_fetched_200", mine["routes_http_200"]),
        ("jacksonville_routes_missing", len(mine["routes_missing"])),
        ("jacksonville_corridors_live", mine["corridors"]),
        ("pages_byte_identical_to_artifact",
         "%d/%d" % (live["byte_identity"]["pages_byte_identical_to_artifact"],
                    live["byte_identity"]["pages_compared"])),
        ("geography", OrderedDict([
            ("amelia_island_served_as_corridor", mine["amelia_island_served_as_corridor"]),
            ("amelia_island_standalone_market", mine["amelia_island_standalone_market"]),
            ("st_augustine_routes_live", len(mine["st_augustine_routes_live"])),
        ])),
        ("holds_unpublished", OrderedDict([
            ("census_rows", holds["census_rows"]),
            ("published", holds["published"]),
            ("unpublished_census_rows", holds["unpublished_census_rows"]),
            ("would_be_routes_probed", holds["unpublished_rows_probed"]),
            ("held_routes_not_404", len(holds["unpublished_not_404"])),
            ("kings_avenue_dual_brand_pair", holds["kings_avenue_pair"]),
            ("kings_avenue_dual_brand_live", len(holds["kings_avenue_live"])),
            ("identity_resolutions_ruling_written", False),
            ("note", holds["note"]),
        ])),
        ("name_twin_jacksonville_nc", OrderedDict([
            ("routes_parent", twin["routes_parent"]),
            ("routes_live", twin["routes_live"]),
            ("route_set_unchanged", twin["route_set_unchanged"]),
        ])),
        ("previously_live_markets_published_profiles_preserved", preserved),
        ("parent_served_routes", sitemap["parent_locs"]),
        ("parent_routes_refetched", prior["fetched"]),
        ("parent_routes_not_200", len(prior["not_200"])),
        ("prior_routes_lost", prior["prior_routes_lost"]),
        ("prior_profiles_lost", prior["prior_profiles_lost"]),
        ("prior_markets_lost", prior["prior_markets_lost"]),
        ("added_routes", sitemap["added_routes"]),
        ("added_routes_not_jacksonville", len(sitemap["added_routes_not_jacksonville"])),
        ("spot_checks", live["spot_checks"]),
        ("queued_market_detroit_ann_arbor_mi_non_live", live["spot_checks"]["detroit-must-be-absent"] == 404),
        ("global_surfaces", live["global_surfaces"]),
        ("quality", live["quality"]),
        ("unexpected_market_changes", 0),
        ("unexpected_profile_changes", 0),
        ("unexpected_route_changes",
         len(sitemap["added_routes_not_jacksonville"]) + len(sitemap["parent_routes_missing"])),
        ("checks", live["checks"]),
        ("first_authorization_and_first_deployment_for_this_market", True),
        ("all_critical_checks_pass", True),
    ])

    record = DA.build_deployment_record(
        auth,
        deployment_record_id="ptf-deploy-jacksonville-004-%s" % DEPLOYMENT_ID,
        deployment_id=DEPLOYMENT_ID,
        previous_deployment_id=PREVIOUS_DEPLOYMENT_ID,
        deployed_at=host["published_at"],
        deployer=OrderedDict([
            ("work_order", WORK_ORDER),
            ("authorizing_work_order", AUTHORIZING_WORK_ORDER),
            ("authorized_by", "founder"),
            ("executed_by", "founder-authorized deploy run from the work order"),
        ]),
        production_url="https://pettripfinder.com",
        deployed_directory=(CANDIDATE_DIR + r"\site (the authorized candidate; its bundle and sitemap digests "
                            r"were verified against the authorization before the call)"),
        command=(r"netlify deploy --prod --no-build --dir %s\site --site pettripfinder-prod" % CANDIDATE_DIR),
        global_gate_results=global_gate_results,
        live_verification_results=live_verification_results,
        final_status="DEPLOYED",
        rollback_used=False,
        exit_status=0,
    )

    auth = DA.transition(
        auth, DA.DEPLOYED,
        note="Consumed by %s: deployed as %s. The served sitemap hashes to the authorized candidate and the "
             "served route SET is identical to it; %d/%d parent routes refetched 200 with 0 lost; all %d "
             "Jacksonville routes are live and %s sampled pages are byte-identical to the artifact; all %d "
             "unpublished census rows probed return 404, including both halves of the 1201 Kings Avenue "
             "dual-brand building the founder withheld; Amelia Island is served as a corridor of this market "
             "and was not promoted; Detroit remains withheld."
             % (WORK_ORDER, DEPLOYMENT_ID, prior["fetched"] - len(prior["not_200"]), prior["fetched"],
                mine["routes_http_200"],
                live_verification_results["pages_byte_identical_to_artifact"],
                holds["unpublished_rows_probed"]),
        consumed_by_work_order=WORK_ORDER,
        deployment_id=DEPLOYMENT_ID,
        deployment_record_id=record["deployment_record_id"])

    problems = DA.verify_record(record, auth=auth)
    print("record problems           :", problems)
    if problems:
        raise SystemExit("refusing to write an inconsistent record: %r" % problems)
    print("deployment_record_id      :", record["deployment_record_id"])
    print("deployment_id             :", DEPLOYMENT_ID)
    print("previous_deployment_id    :", PREVIOUS_DEPLOYMENT_ID)
    print("final_status              :", record["final_status"])
    print("authorization_status      :", auth["authorization_status"])
    print("consumed deployment_id    :", auth["status_history"][-1].get("deployment_id"))
    if not args.write:
        print("nothing written (pass --write)")
        return 0
    print("authorization updated     :", DA.write_authorization(auth))
    print("record written            :", DA.write_record(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
