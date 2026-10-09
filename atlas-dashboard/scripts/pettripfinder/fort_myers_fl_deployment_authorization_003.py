"""PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- build the global deployment manifest for the founder-authorized
whole-site candidate, then build and persist a NEW PREPARED->AUTHORIZED deployment authorization binding that exact
bundle to the founder's explicit statement (cloned in shape from the previous market's 003 writer). NOTHING IS DEPLOYED
AND THE AUTHORIZATION IS NOT CONSUMED: this order stops before production deployment.

    python -m scripts.pettripfinder.fort_myers_fl_deployment_authorization_003 [--bundle-manifest ...] [--write]

THE FIRST AUTHORIZATION THIS MARKET HAS EVER HAD. Fort Myers has never been authorized or deployed, so there is nothing
to supersede. The module refuses unless the candidate it binds carries fort-myers-fl and was assembled from the
founder-decision commit, the readiness packet binds pkg-fort-myers-fl-919f61116936bf5e and no other package, the
participation record reads FOUNDER_AUTHORIZED_FOR_LAUNCH, no authorization is already deployable, the live pin is the
parent the readiness packet binds, and the new id does not collide with an existing record.

SOURCE COMMIT = THE BUILD COMMIT. ``source_commit`` is the commit the candidate was assembled from (its manifest's own
``source_commit``), never HEAD: a metadata commit after the build moves HEAD and no site byte.

WHY THE LIVE MANIFEST IS NOT WRITTEN HERE. The deploying step writes the live ``global_deployment_manifest.json`` from
these same bytes immediately before the deploy; the candidate manifest goes to the CANDIDATE path.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402
from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import launch_participation as LP       # noqa: E402

WORK_ORDER = "PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "fort-myers-fl"
AUTHORIZED_PACKAGE_ID = "pkg-fort-myers-fl-919f61116936bf5e"
REGISTRATION_COMMIT = "19c47422"
FOUNDER_BINDING_COMMIT = "6a425592"
FOUNDER_DECISION_COMMIT = "ab616e2e"
REFUSED_PACKAGE_PREFIXES = ("pkg-fort-myers-fl-68b3cfa8",)
READINESS_PATH = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                              "fort_myers_fl_registration_authorization_readiness.json")
CHECKS_PATH = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "fort_myers_fl_registration_checks_002.json")
BUNDLE_MANIFEST_PATH = "C:/t/fm4a/global_bundle_manifest.json"
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_fort_myers_003.json")
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

FOUNDER_WORDS = ("The founder explicitly authorizes launch of: fort-myers-fl using ONLY the exact registered Fort Myers "
                 "package mechanically resolved from the completed staging order. Bind this decision to: 6a425592. "
                 "The founder approves the existing safe publication cohort: 57 pet-friendly profiles. No publication "
                 "expansion is authorized. Keep ALL held / unresolved rows unpublished.")


def _market_ids(markets):
    return {m.get("market_id") if isinstance(m, dict) else m for m in (markets or ())}


def _live_deploy_id():
    with open(os.path.join(_DASH, "tests", "pettripfinder", "pins", "deployment_state.json"), encoding="utf-8-sig") as fh:
        return json.load(fh)["live"]["deploy_id"]


def _refuse_if_unsafe(authorization_id):
    with open(READINESS_PATH, encoding="utf-8-sig") as fh:
        readiness = json.load(fh)
    bound = readiness["the_digests_this_readiness_binds"]["sealed_package_id"]
    if bound != AUTHORIZED_PACKAGE_ID or bound.startswith(REFUSED_PACKAGE_PREFIXES) \
            or readiness.get("status") != "AUTHORIZATION_READY":
        raise SystemExit("the readiness packet binds %r (%s); the founder authorized %s only"
                         % (bound, readiness.get("status"), AUTHORIZED_PACKAGE_ID))
    if LP.launch_status(MARKET) != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH:
        raise SystemExit("%s reads %s, not FOUNDER_AUTHORIZED_FOR_LAUNCH" % (MARKET, LP.launch_status(MARKET)))
    existing = DA.list_authorizations()
    if any(a.get("authorization_id") == authorization_id for a in existing):
        raise SystemExit("authorization %s already exists; a new decision writes a new record" % authorization_id)
    live = [a["authorization_id"] for a in existing
            if MARKET in _market_ids(a.get("participating_markets"))
            and a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
    if live:
        raise SystemExit("authorization(s) naming %s are still deployable: %s" % (MARKET, live))
    deployable = [a["authorization_id"] for a in existing if a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
    if deployable:
        raise SystemExit("other authorizations are still deployable: %s" % deployable)
    return readiness


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-manifest", default=BUNDLE_MANIFEST_PATH)
    ap.add_argument("--write", action="store_true", help="persist the candidate manifest and the authorization")
    args = ap.parse_args(argv)

    with open(args.bundle_manifest, encoding="utf-8-sig") as fh:
        bundle_manifest = json.load(fh)
    manifest = GD.build_manifest(bundle_manifest)
    problems = GD.verify_manifest(manifest)
    print("global manifest problems:", problems)
    if problems:
        raise SystemExit("global manifest verification failed: %r" % problems)
    if MARKET not in _market_ids(manifest["participating_markets"]):
        raise SystemExit("the candidate does not carry %s" % MARKET)
    if not str(manifest["source_commit"]).startswith(FOUNDER_DECISION_COMMIT):
        raise SystemExit("the candidate was assembled from %s, not the founder-decision commit %s"
                         % (manifest["source_commit"], FOUNDER_DECISION_COMMIT))

    authorization_id = "ptf-auth-fort-myers-003-%s" % manifest["bundle_sha256"][:12]
    readiness = _refuse_if_unsafe(authorization_id)
    rollback_target = _live_deploy_id()
    if readiness["the_digests_this_readiness_binds"]["parent_live_deploy_id"] != rollback_target:
        raise SystemExit("the readiness packet's parent is not the live deploy %s" % rollback_target)
    binds = readiness["the_digests_this_readiness_binds"]
    with open(CHECKS_PATH, encoding="utf-8-sig") as fh:
        projected = json.load(fh)["projected_accounting"]

    authorization_source = (
        'The founder, in work order %s: "%s" -- the package id read mechanically from the founder-binding commit and '
        'the readiness packet: registered package %s (%s), bound to commit %s (NOT the first registration commit %s, '
        'which added the package file), founder decision commit %s, parent deployment %s, parent release-index digest '
        '%s, market bundle %s, expected Fort Myers delta +1 market / +%d profiles / +%d release-index routes / +%d '
        'served routes. The approved cohort publishes 57 pet-friendly profiles and 34 verified-no-pets exclusions '
        '(never as hotel profiles); no publication expansion; all 51 unresolved rows stay unpublished -- Comfort Suites '
        'and MainStay Suites at 9455 Old Luckett (the shared-building identity is not resolved), the Quality Inn at '
        '4760 S Cleveland (the current identity candidate, held and not promoted; Travelodge is retired rebrand '
        'history and none of its evidence migrates; the published Travelodge at 13353 N Cleveland is a different '
        'building), Latitude 26 Waterfront Inn & Suites (no new county ruling), Pink Shell Beach Resort & Marina and '
        'Edison Beach House (the shared reader is not modified and no disposition is forced) and the router-exhausted '
        'rest -- timeshare / vacation-ownership, vacation rental and private condo / residence identities stay '
        'outside hotel inventory, no nonoperating identity publishes, every premises publishes as its own '
        'municipality with no Naples / Collier premises, and no identity_resolutions.json ruling is written. The '
        'source-ready shadow id pkg-fort-myers-fl-68b3cfa8bc4758c5 and the source-ready order\'s failed first seal '
        'are not authorized. This is the FIRST authorization this market has had: nothing is superseded. This order '
        'stops before deployment; the authorization is created AUTHORIZED and is not consumed here.'
        % (WORK_ORDER, FOUNDER_WORDS, binds["sealed_package_id"], binds["sealed_package_digest"],
           FOUNDER_BINDING_COMMIT, REGISTRATION_COMMIT, FOUNDER_DECISION_COMMIT, rollback_target,
           binds["parent_release_digest"], binds["changed_market_bundle_sha256"],
           projected["FORT_MYERS_PROJECTED_PROFILES"], projected["FORT_MYERS_RELEASE_INDEX_ROUTES"],
           projected["FORT_MYERS_SERVED_ROUTES"]))
    note = (
        "Fort Myers / Cape Coral / Sanibel joins as the FORTY-SIXTH market: 57 published pet-friendly profiles over 4 "
        "publishing corridors, 34 verified-no-pets published only as exclusions, and 51 unresolved identities staying "
        "unpublished. Every row publishes the municipality its own postal code carries (all 142 qualifying rows in Lee "
        "County; Cape Coral, Fort Myers Beach, Sanibel, Captiva, Estero, Bonita Springs and North Fort Myers never "
        "flattened to Fort Myers; 0 Naples / Collier premises). Registered as COMPOSITE_FRESH_MARKET_DATA_ONLY with "
        "automatic base derivation and classification (FAST 15/15, 0 broad regression runs). No identity_resolutions."
        "json ruling was written; the shared reader was not modified; no paid spend occurred; no tiered, capped, "
        "conditional or multi-amount fee is flattened.")

    auth = DA.build_authorization(
        manifest, authorization_id=authorization_id, work_order=WORK_ORDER, authorized_by="founder",
        source_commit=manifest["source_commit"], rollback_target=rollback_target, target_site=TARGET_SITE,
        target_domain=TARGET_DOMAIN, authorization_source=authorization_source, note=note)
    verify_problems = DA.verify_authorization(auth, manifest=manifest)
    print("authorization verify_authorization problems:", verify_problems)
    if verify_problems:
        raise SystemExit("authorization verification failed: %r" % verify_problems)
    auth = DA.transition(auth, DA.AUTHORIZED,
                         note="The founder authorized %s for launch, bound to commit %s. This is that exact candidate "
                              "(built twice, byte-identical), and only %s. Not deployed, not consumed."
                              % (AUTHORIZED_PACKAGE_ID, FOUNDER_BINDING_COMMIT, MARKET))
    for k in ("authorization_id", "bundle_sha256", "sitemap_sha256", "total_profiles", "sitemap_route_count",
              "source_commit", "rollback_target", "authorization_status", "deploy_id"):
        print("%-22s %s" % (k, auth.get(k)))
    print("%-22s %s" % ("markets", len(auth["participating_markets"])))
    if not args.write:
        print("nothing written (pass --write)")
        return 0
    with open(CANDIDATE_MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("candidate manifest:", os.path.relpath(CANDIDATE_MANIFEST_PATH, _DASH))
    print("authorization     :", DA.write_authorization(auth))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
