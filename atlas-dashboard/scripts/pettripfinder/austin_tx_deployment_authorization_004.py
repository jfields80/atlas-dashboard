"""PTF-AUSTIN-TX-FOUNDER-LAUNCH-AUTHORIZATION-AND-DEPLOYMENT-004 -- build the global deployment manifest for the
founder-authorized whole-site candidate, then build and persist a NEW PREPARED->AUTHORIZED deployment
authorization binding that exact bundle to the founder's explicit statement.

    python -m scripts.pettripfinder.austin_tx_deployment_authorization_004 [--bundle-manifest ...] [--write]

THE FIRST AUTHORIZATION THIS MARKET HAS EVER HAD. Austin has never been authorized or deployed, so there is nothing
to supersede. The module refuses unless the candidate it binds carries austin-tx, the readiness packet binds
pkg-austin-tx-ee3f5c9147638f51 and no other package, no authorization naming this market is already deployable, and
the new id does not collide with an existing record.

SOURCE COMMIT = THE BUILD COMMIT. ``source_commit`` is the commit the candidate was assembled from (its manifest's
own ``source_commit``), never HEAD: the live pin's source commit must equal the committed manifest's, and a
metadata commit after the build moves HEAD and no site byte (PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001
learned this after a deploy).

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

from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402

WORK_ORDER = "PTF-AUSTIN-TX-FOUNDER-LAUNCH-AUTHORIZATION-AND-DEPLOYMENT-004"
MARKET = "austin-tx"
AUTHORIZED_PACKAGE_ID = "pkg-austin-tx-ee3f5c9147638f51"
REFUSED_PACKAGE_PREFIXES = ("pkg-austin-tx-3030caf7", "pkg-austin-tx-024e6fb4")
READINESS_PATH = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                              "austin_tx_registration_authorization_readiness.json")
BUNDLE_MANIFEST_PATH = "C:/t/atx4a/global_bundle_manifest.json"
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_austin_004.json")
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

FOUNDER_WORDS = "Founder authorizes Austin pkg-austin-tx-ee3f5c9147638f51 for launch; deploy after gates."


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

    authorization_id = "ptf-auth-austin-004-%s" % manifest["bundle_sha256"][:12]
    readiness = _refuse_if_unsafe(authorization_id)
    rollback_target = _live_deploy_id()
    if readiness["the_digests_this_readiness_binds"]["parent_live_deploy_id"] != rollback_target:
        raise SystemExit("the readiness packet's parent is not the live deploy %s" % rollback_target)
    binds = readiness["the_digests_this_readiness_binds"]

    authorization_source = (
        'The founder, in work order %s: "%s" -- bound to parent deployment %s, parent release-index digest %s, '
        'registered package %s (%s), market bundle %s, expected Austin delta +1 market / +190 profiles / +203 '
        'release-index routes / +204 served routes. The approved cohort (coverage decision 003) publishes 190 '
        'pet-friendly profiles and 63 verified-no-pets exclusions; the 80 new-spend rows, the 25 founder-decision '
        'rows and the 49 router-exhausted / evidence / source-silent rows stay unpublished, and the three timeshare / '
        'vacation-ownership identities stay outside hotel inventory. The stale package pkg-austin-tx-3030caf7 and the '
        'shadow id pkg-austin-tx-024e6fb4 are not authorized. This is the FIRST authorization this market has had: '
        'nothing is superseded. The founder authorized deployment after the gates pass.'
        % (WORK_ORDER, FOUNDER_WORDS, rollback_target, binds["parent_release_digest"], binds["sealed_package_id"],
           binds["sealed_package_digest"], binds["changed_market_bundle_sha256"]))
    note = (
        "Austin / Central Texas joins as the THIRTY-EIGHTH market and the first Texas market: 190 published "
        "pet-friendly profiles over 12 publishing corridors, 63 verified-no-pets published only as exclusions, and "
        "154 unresolved identities staying unpublished -- 80 with no first-party route in any authorized lane, 25 "
        "founder-decision rows (nine dual-brand buildings, five operator-domain rows, Mountain Star and Strickland "
        "Arms) and 49 router-exhausted / evidence / source-silent. Three timeshare / vacation-ownership identities are "
        "outside hotel inventory. Refreshed under the repaired shared first-party reader and registered as "
        "COMPOSITE_FRESH_MARKET_DATA_ONLY (FAST 15/15, 0 broad regression runs). No identity_resolutions.json ruling "
        "was written; no replacement identity, route or domain was invented; no paid spend occurred; no tiered or "
        "multi-part fee is flattened. The other 8 corridors stay below their own publication minimum.")

    auth = DA.build_authorization(
        manifest, authorization_id=authorization_id, work_order=WORK_ORDER, authorized_by="founder",
        source_commit=manifest["source_commit"], rollback_target=rollback_target, target_site=TARGET_SITE,
        target_domain=TARGET_DOMAIN, authorization_source=authorization_source, note=note)
    verify_problems = DA.verify_authorization(auth, manifest=manifest)
    print("authorization verify_authorization problems:", verify_problems)
    if verify_problems:
        raise SystemExit("authorization verification failed: %r" % verify_problems)
    auth = DA.transition(auth, DA.AUTHORIZED,
                         note="The founder authorized %s for launch and authorized deployment after the gates. This "
                              "is that exact candidate (built twice, byte-identical), and only %s."
                              % (AUTHORIZED_PACKAGE_ID, MARKET))
    for k in ("authorization_id", "bundle_sha256", "sitemap_sha256", "total_profiles", "sitemap_route_count",
              "source_commit", "rollback_target", "authorization_status"):
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
