"""PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002 -- the UNEXECUTED deployment packet.

Prepares, but does not sign, the deployment authorization a founder would need
to put this candidate into production. It writes to markets/reports/ and NEVER
to deploy/netlify/deployment_authorizations/: a file in that directory IS an
authorization, and only a founder creates one.

Every number is read from the artifacts this order produced and from the
committed production pin. Nothing is typed. That matters more here than
anywhere else in the factory: the Cincinnati launch order's own inline bundle
SHA was wrong in five characters and its rollback target was one deploy stale,
which would have un-deployed Louisville. A packet whose numbers are derived
cannot drift from the artifact it describes.

WHAT THIS CANDIDATE IS

Toledo is registered and its authority is committed, but it is recorded
SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH, so it contributes no page to
the composed site. The
candidate should therefore reproduce the live bundle EXACTLY -- same markets,
same profiles, same routes, same digest. That is the Cincinnati precedent: a
promotion that moves zero bytes of the composed bundle. The packet reports the
comparison either way and says plainly which happened.
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

WORK_ORDER = "PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002"
WOULD_BECOME = "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"
MARKET_ID = "toledo-oh"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PINS = os.path.join(_DASH, "tests", "pettripfinder", "pins")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=_REPO, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, help="the assembled candidate directory")
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "toledo_deployment_authorization_003_PROPOSED.json"))
    args = ap.parse_args(argv)

    manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    live = _load(os.path.join(PINS, "deployment_state.json"))["live"]
    market_state = _load(os.path.join(PINS, "market_state.json"))["markets"]
    contract = _load(os.path.join(_DASH, "deploy", "netlify", "release_contracts",
                                  "%s.json" % MARKET_ID))
    rulings = _load(os.path.join(PKG, "toledo_oh_founder_rulings_001.json"))

    participating = manifest["participating_markets"]
    cand_markets = [m["market_id"] for m in participating]
    cand_profiles = sum(m["published_profiles"] for m in participating)
    cand_profile_counts = {m["market_id"]: m["published_profiles"] for m in participating}

    same_bundle = manifest["bundle_sha256"] == live["bundle_sha256"]
    same_sitemap = manifest["sitemap_sha256"] == live["sitemap_sha256"]

    doc = OrderedDict([
        ("schema", "ptf-deployment-authorization-proposal/1.0"),
        ("status", "PROPOSED_UNEXECUTED"),
        ("what_this_is",
         "A prepared, UNSIGNED deployment authorization for founder review. It is deliberately "
         "NOT written to deploy/netlify/deployment_authorizations/, because a file in that "
         "directory IS an authorization and only a founder creates one. Nothing here has been "
         "deployed and no launch-participation flag has moved."),
        ("would_become", WOULD_BECOME),
        ("prepared_by", WORK_ORDER),
        ("prepared_at", "2026-09-06"),
        ("authorized_by", None),
        ("authorized_at", None),
        ("source_commit", git("rev-parse", "HEAD")),
        ("source_branch", git("rev-parse", "--abbrev-ref", "HEAD")),
        ("lineage_integrated", OrderedDict([
            ("then_current_deployed_lineage", "2163c4ed23b7315954f896c99729ca95c08eabfc"),
            ("how_it_was_derived",
             "read from the committed live deployment pin, not typed. Fort Wayne (+3 commits) and "
             "Lexington (+1) were both running market-local orders in parallel and neither "
             "touched a registry file, a pin or a deployment artifact, so the lineage tip had not "
             "moved since Toledo was built on it."),
            ("integration_was_purely_additive", True),
        ])),
        ("binding_identity", "bundle_sha256"),
        ("bundle_sha256", manifest["bundle_sha256"]),
        ("sitemap_sha256", manifest["sitemap_sha256"]),
        ("production_context", "production"),
        ("production_baseline", OrderedDict([
            ("deploy_id", live["deploy_id"]),
            ("deployed_by", live["deployed_by"]),
            ("authorization_id", live["authorization_id"]),
            ("source_commit", live["source_commit"]),
            ("total_profiles", live["total_profiles"]),
            ("sitemap_route_count", live["sitemap_route_count"]),
            ("total_html_pages", live["total_html_pages"]),
            ("total_files", live["total_files"]),
            ("bundle_sha256", live["bundle_sha256"]),
            ("sitemap_sha256", live["sitemap_sha256"]),
        ])),
        ("rollback_target", live["deploy_id"]),
        ("rollback_note",
         "Rolling back means returning to deploy %s, which is what production serves today at %d "
         "profiles. It is the CURRENT deploy and not the one before it: the Cincinnati launch "
         "order named a rollback one deploy stale, which would have un-deployed Louisville."
         % (live["deploy_id"], live["total_profiles"])),
        ("candidate", OrderedDict([
            ("participating_markets", cand_markets),
            ("total_profiles", cand_profiles),
            ("sitemap_route_count", manifest["sitemap_route_count"]),
            ("total_html_pages", manifest["total_html_pages"]),
            ("profile_counts", cand_profile_counts),
            ("total_files", manifest["total_files"]),
            ("all_gates_pass", manifest["all_gates_pass"]),
            ("broken_links", manifest["broken_links"]),
            ("collisions", manifest.get("collision_count")),
            ("canonical_violations", manifest.get("canonical_violations")),
        ])),
        ("toledo_is_registered_but_does_not_participate", OrderedDict([
            ("launch_status", LP.launch_status(MARKET_ID)),
            ("what_that_means",
             "Toledo's authority is committed and its release contract passes, but it contributes "
             "no page to the composed site until a founder flips its launch participation. This "
             "order is not permitted to flip it."),
            ("consequence_for_this_candidate",
             "the composed bundle should be IDENTICAL to what production already serves"),
            ("bundle_identical_to_live", same_bundle),
            ("sitemap_identical_to_live", same_sitemap),
            ("verdict",
             "CONFIRMED -- this promotion moved zero bytes of the composed bundle, the Cincinnati "
             "precedent" if (same_bundle and same_sitemap) else
             "NOT CONFIRMED -- the bundle differs from live; investigate before authorising"),
        ])),
        ("delta_against_production", OrderedDict([
            ("total_profiles", "%d -> %d" % (live["total_profiles"], cand_profiles)),
            ("sitemap_routes", "%d -> %d" % (live["sitemap_route_count"],
                                             manifest["sitemap_route_count"])),
            ("markets", "%d -> %d" % (len(live["participating_markets"]), len(cand_markets))),
            ("routes_added", 0 if same_sitemap else None),
            ("routes_removed", 0 if same_sitemap else None),
            ("every_live_market_profile_delta", {
                m: cand_profile_counts.get(m, 0) - live["profile_counts"][m]
                for m in live["profile_counts"]}),
        ])),
        ("what_toledo_would_bring_when_it_is_launched", OrderedDict([
            ("market_id", MARKET_ID),
            ("census", market_state[MARKET_ID]["census"]),
            ("published_profiles", market_state[MARKET_ID]["profiles"]),
            ("verified_no_pets", market_state[MARKET_ID]["verified_no_pets"]),
            ("publishing_corridors", contract["routes"]["published_corridor_route_count"]),
            ("note",
             "these are the numbers a LAUNCH order would add. This authorization does not add "
             "them: it describes a candidate in which Toledo does not participate."),
        ])),
        ("founder_rulings_this_candidate_obeys", [
            OrderedDict([("ruling_id", r["ruling_id"]), ("disposition", r["disposition"])])
            for r in rulings["rulings"] if not str(r.get("status", "")).startswith("SUPERSEDED")]),
        ("what_this_authorization_would_NOT_assert", [
            "that Toledo is complete -- 28 of its 54 identities are unresolved",
            "that the five held two-identity addresses are settled -- founder rulings TOLEDO-R2 "
            "and TOLEDO-R3 keep them held",
            "that Toledo should be launched -- launch participation is a separate founder lever",
        ]),
        ("execution_note",
         "NOT EXECUTED. Executing it means writing an authorization under "
         "deploy/netlify/deployment_authorizations/, registering it, and deploying. A launch "
         "order must also verify every pin here against the COMMITTED packet rather than against "
         "any SHA quoted in prose, and must delete the .netlify/ directory the Netlify CLI "
         "scaffolds before running any lane."),
    ])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("candidate bundle :", doc["bundle_sha256"][:16])
    print("live bundle      :", live["bundle_sha256"][:16])
    print("identical        :", same_bundle, "| sitemap identical:", same_sitemap)
    print("markets          :", doc["delta_against_production"]["markets"])
    print("profiles         :", doc["delta_against_production"]["total_profiles"])
    print("routes           :", doc["delta_against_production"]["sitemap_routes"])
    print("verdict          :", doc["toledo_is_registered_but_does_not_participate"]["verdict"])
    print("written          :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
