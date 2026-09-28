"""PTF-DENVER-CO-FOUNDER-LAUNCH-AUTHORIZATION-004 -- build the global deployment manifest for the
founder-authorized whole-site candidate, then build and persist a NEW PREPARED->AUTHORIZED deployment
authorization binding that exact bundle to the founder's explicit statement.

Deploys nothing; the authorization is inert until a deployer consumes it.

THE FIRST AUTHORIZATION THIS MARKET HAS EVER HAD
------------------------------------------------
Denver has never been authorized and never deployed, so there is nothing to supersede and nothing to carry
forward. The superseded 289-profile package pkg-denver-co-91b2e0a2 was never authorized, and the founder refused
it explicitly; this module refuses unless the candidate it binds was assembled from the tree whose readiness
packet binds pkg-denver-co-07f10db29ab56d98. No authorization naming this market may already be deployable, and
the new id may not collide with an existing record.

WHY THE LIVE MANIFEST IS NOT OVERWRITTEN HERE
---------------------------------------------
The founder's decision authorizes, it does not deploy, so writing ``global_deployment_manifest.json`` would leave
the repository's own cross-check describing a bundle production does not serve. The candidate manifest goes to
the CANDIDATE path; the deploying order writes the live manifest from these same bytes.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402

WORK_ORDER = "PTF-DENVER-CO-FOUNDER-LAUNCH-AUTHORIZATION-004"
MARKET = "denver-co"
AUTHORIZED_PACKAGE_ID = "pkg-denver-co-07f10db29ab56d98"
READINESS_PATH = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                              "denver_co_registration_authorization_readiness.json")
BUNDLE_MANIFEST_PATH = os.path.join("C:\\", "t", "den4a", "global_bundle_manifest.json")
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_denver_004.json")
#: what production serves today (the SAN DIEGO deployment), and therefore what a Denver deployment would roll
#: back to. Resolved mechanically at the start of this order, not inherited from the parent module.
ROLLBACK_TARGET = "6ab859787d349f8397e1450a"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'The founder, in this conversation, after PTF-DENVER-CO-PREAUTH-PREOPENING-CORRECTION-003 reported Denver '
    'AUTHORIZATION_READY: "AUTHORIZE: pkg-denver-co-07f10db29ab56d98. DO NOT AUTHORIZE: pkg-denver-co-91b2e0a2." '
    'Recorded under work order PTF-DENVER-CO-FOUNDER-LAUNCH-AUTHORIZATION-004 -- bound to parent deployment '
    '6ab859787d349f8397e1450a, parent release-index digest '
    'sha256:4c702f05eca1588c92271a94f77303c0908f4f4972154a85c0b7979f321bdda1, registered package digest '
    'sha256:07f10db29ab56d982490df7341831d731c8015e198d9805572730113056c6707, market bundle '
    '475633a2d3c1553b19352927c29232d787da15e62eedc467341c103a2d278ce2, expected Denver delta +1 market / '
    '+288 profiles / +305 release-index routes / +306 served routes. The founder-approved cohort (coverage '
    'decision 003) publishes 288 pet-friendly profiles and 46 verified-no-pets exclusions; the 52 no-website rows, '
    'the 16 founder-decision rows, the 38 router-exhausted rows and the not-yet-open ECHO Suites Thornton stay '
    'unpublished. This is the FIRST authorization this market has ever had: nothing is superseded and nothing is '
    'carried forward. This authorization permits the existing release lifecycle to deploy that exact staged '
    'artifact only if every gate passes; the founder authorized, and did not order a deployment, so it is written '
    'AUTHORIZED and left unconsumed.'
)

NOTE = (
    "Denver / Boulder / Front Range, Colorado joins as the THIRTY-SIXTH market and the first Colorado market: 288 "
    "published pet-friendly profiles over 16 publishing corridors (downtown-lodo-union-station, "
    "highlands-rino-north-denver, cherry-creek-glendale, central-park-lowry-i70, denver-tech-center, den-airport, "
    "aurora, lakewood-wheat-ridge, golden-red-rocks, westminster-broomfield, thornton-northglenn-north-i25, "
    "littleton-englewood, boulder, louisville-superior-lafayette, longmont-erie, parker-southeast), 46 "
    "verified-no-pets published only as exclusions, and 107 unresolved identities staying unpublished -- 52 with "
    "no first-party website in any free lane, 16 founder-decision rows (seven dual-brand buildings, two ESA "
    "title collisions), 38 router-exhausted and one hotel whose own brand name says it is not open yet. "
    "Registered as COMPOSITE_FRESH_MARKET_DATA_ONLY (FAST 15/15, 0 broad regression runs). No "
    "identity_resolutions.json ruling was written; no ESA display name was invented; no paid Places usage "
    "occurred; no tiered or multi-part fee is flattened. The other 4 corridors stay below their own publication "
    "minimum and were not forced. Membership is decided by the property's own postal code: Colorado Springs, Fort "
    "Collins / Loveland, Estes Park and the ski resorts are refused and preserved as future markets; Boulder "
    "publishes as its own strong corridor."
)


def _market_ids(markets):
    """``participating_markets`` holds one record per market, not bare ids; read the ids out of it. (Testing a
    bare id against the records -- as the parent module did -- can never match, so its 'still deployable'
    refusal could never fire.)"""
    return {m.get("market_id") if isinstance(m, dict) else m for m in (markets or ())}


def _refuse_if_unsafe(authorization_id):
    """No authorization naming the market may still be deployable, the new id must not collide with any
    record, and the readiness packet must bind the founder's package and no other."""
    with open(READINESS_PATH, encoding="utf-8-sig") as fh:
        readiness = json.load(fh)
    bound = readiness["the_digests_this_readiness_binds"]["sealed_package_id"]
    if bound != AUTHORIZED_PACKAGE_ID or readiness.get("status") != "AUTHORIZATION_READY":
        raise SystemExit("the readiness packet binds %r (%s); the founder authorized %s only"
                         % (bound, readiness.get("status"), AUTHORIZED_PACKAGE_ID))
    existing = DA.list_authorizations()
    if any(a.get("authorization_id") == authorization_id for a in existing):
        raise SystemExit("authorization %s already exists; a new decision writes a new record" % authorization_id)
    live = [a["authorization_id"] for a in existing
            if MARKET in _market_ids(a.get("participating_markets")) and a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
    if live:
        raise SystemExit("authorization(s) naming %s are still deployable: %s" % (MARKET, live))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-manifest", default=BUNDLE_MANIFEST_PATH)
    ap.add_argument("--write", action="store_true",
                    help="persist the candidate manifest and the authorization")
    args = ap.parse_args(argv)

    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_DASH,
                                            text=True).strip()
    with open(args.bundle_manifest, encoding="utf-8-sig") as fh:
        bundle_manifest = json.load(fh)

    manifest = GD.build_manifest(bundle_manifest)
    problems = GD.verify_manifest(manifest)
    print("global manifest problems:", problems)
    if problems:
        raise SystemExit("global manifest verification failed: %r" % problems)
    if MARKET not in _market_ids(manifest["participating_markets"]):
        raise SystemExit("the candidate does not carry %s" % MARKET)

    bundle_prefix = manifest["bundle_sha256"][:12]
    authorization_id = "ptf-auth-denver-004-%s" % bundle_prefix
    _refuse_if_unsafe(authorization_id)

    auth = DA.build_authorization(
        manifest,
        authorization_id=authorization_id,
        work_order=WORK_ORDER,
        authorized_by="founder",
        source_commit=source_commit,
        rollback_target=ROLLBACK_TARGET,
        target_site=TARGET_SITE,
        target_domain=TARGET_DOMAIN,
        authorization_source=AUTHORIZATION_SOURCE,
        note=NOTE,
    )

    verify_problems = DA.verify_authorization(auth, manifest=manifest)
    print("authorization verify_authorization problems:", verify_problems)
    if verify_problems:
        raise SystemExit("authorization verification failed: %r" % verify_problems)

    auth = DA.transition(auth, DA.AUTHORIZED,
                         note="The founder authorized %s (and refused pkg-denver-co-91b2e0a2); this is that "
                              "exact candidate, and only %s. No deployment was ordered: this authorization is "
                              "written AUTHORIZED and left UNCONSUMED." % (AUTHORIZED_PACKAGE_ID, MARKET))

    print("authorization_id :", authorization_id)
    print("bundle_sha256    :", manifest["bundle_sha256"])
    print("sitemap_sha256   :", manifest["sitemap_sha256"])
    print("markets          :", len(manifest["participating_markets"]))
    print("profiles         :", manifest["total_published_profiles"])
    print("sitemap routes   :", manifest["sitemap_route_count"])
    print("rollback target  :", ROLLBACK_TARGET)
    print("status           :", auth["authorization_status"])
    if not args.write:
        print("nothing written (pass --write)")
        return 0

    with open(CANDIDATE_MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    path = DA.write_authorization(auth)
    print("candidate manifest:", os.path.relpath(CANDIDATE_MANIFEST_PATH, _DASH))
    print("authorization     :", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
