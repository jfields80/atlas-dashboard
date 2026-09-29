"""PTF-PHOENIX-AZ-FOUNDER-LAUNCH-AUTHORIZATION-004 -- build the global deployment manifest for the
founder-authorized whole-site candidate, then build and persist a NEW PREPARED->AUTHORIZED deployment
authorization binding that exact bundle to the founder's explicit statement.

Deploys nothing; the authorization is inert until a deployer consumes it.

THE FIRST AUTHORIZATION THIS MARKET HAS EVER HAD
------------------------------------------------
Phoenix has never been authorized and never deployed, so there is nothing to supersede and nothing to carry
forward. The earlier Phoenix packages (the superseded 63-no-pets pkg-phoenix-az-85ad9b66 and the source-ready shadow
pkg-phoenix-az-865822f4) were never authorized, and the founder refused every earlier package explicitly; this
module refuses unless the candidate it binds was assembled from the tree whose readiness packet binds
pkg-phoenix-az-07f7e75699af6a8c. No authorization naming this market may already be deployable, and the new id may
not collide with an existing record.

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

WORK_ORDER = "PTF-PHOENIX-AZ-FOUNDER-LAUNCH-AUTHORIZATION-004"
MARKET = "phoenix-az"
AUTHORIZED_PACKAGE_ID = "pkg-phoenix-az-07f7e75699af6a8c"
REFUSED_PACKAGE_PREFIXES = ("pkg-phoenix-az-85ad9b66", "pkg-phoenix-az-865822f4")
READINESS_PATH = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                              "phoenix_az_registration_authorization_readiness.json")
BUNDLE_MANIFEST_PATH = os.path.join("C:\\", "t", "phx4a", "global_bundle_manifest.json")
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_phoenix_004.json")
#: what production serves today (the DENVER deployment), and therefore what a Phoenix deployment would roll back
#: to. Resolved mechanically at the start of this order (release_index live-source --verify-host), not inherited.
ROLLBACK_TARGET = "6aba7587ddcc33a192bdf694"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'The founder, in work order PTF-PHOENIX-AZ-FOUNDER-LAUNCH-AUTHORIZATION-004, after '
    'PTF-PHOENIX-AZ-PREAUTH-VACATION-OWNERSHIP-CORRECTION-003 reported Phoenix AUTHORIZATION_READY: "Authorize '
    'ONLY the corrected Phoenix package: pkg-phoenix-az-07f7e75699af6a8c. Do NOT authorize any earlier Phoenix '
    'package." -- bound to parent deployment 6aba7587ddcc33a192bdf694, parent release-index digest '
    'sha256:fb99d3b6930954979aeac269668ba5c0cd554299bb74939bae6ba8887062fe62, registered package digest '
    'sha256:07f7e75699af6a8cefe5f083b688f647c55190f04aae0cd0617292968ab0fccf, market bundle '
    'ea2a8d31aadf5dcb5a20aa4872e5f761596fc5fe348f409c23c72952fcfa8d69, expected Phoenix delta +1 market / '
    '+256 profiles / +275 release-index routes / +276 served routes. The founder-approved cohort (coverage '
    'decision 003) publishes 256 pet-friendly profiles and 59 verified-no-pets exclusions; the 48 Places-gated rows, '
    'the 30 founder-decision rows, the 88 router-exhausted / evidence / source-silent rows and the three '
    'not-yet-open hotels stay unpublished, and the four Wyndham vacation-ownership resorts stay outside hotel '
    'inventory. This is the FIRST authorization this market has ever had: nothing is superseded and nothing is '
    'carried forward. This authorization permits the existing release lifecycle to deploy that exact staged '
    'artifact only if every gate passes; the founder authorized, and did not order a deployment, so it is written '
    'AUTHORIZED and left unconsumed.'
)

NOTE = (
    "Phoenix / Scottsdale / Valley of the Sun, Arizona joins as the THIRTY-SEVENTH market and the first Arizona "
    "market: 256 published pet-friendly profiles over 18 publishing corridors (downtown-phoenix, "
    "biltmore-camelback-arcadia, phx-sky-harbor, tempe, old-town-scottsdale, central-scottsdale, paradise-valley, "
    "mesa, chandler, glendale, scottsdale-airpark-kierland, north-scottsdale, north-phoenix-deer-valley, "
    "west-phoenix, gilbert, goodyear-avondale-litchfield, surprise-sun-city, buckeye), 59 verified-no-pets "
    "published only as exclusions, and 169 unresolved identities staying unpublished -- 48 with no first-party "
    "route in any free lane, 30 founder-decision rows (fourteen dual-brand buildings, two route-domain rulings), "
    "88 router-exhausted / evidence / source-silent and three hotels whose own pages say they are not open yet. "
    "Four Wyndham vacation-ownership resorts are TIMESHARE, outside hotel inventory. Registered as "
    "COMPOSITE_FRESH_MARKET_DATA_ONLY (FAST 15/15, 0 broad regression runs). No identity_resolutions.json ruling "
    "was written; no replacement identity, route or domain was invented; no paid Places usage occurred; no tiered "
    "or multi-part fee is flattened. The other 8 corridors stay below their own publication minimum and were not "
    "forced. Membership is decided by the property's own postal code: Sedona, Flagstaff, the Grand Canyon, "
    "Prescott and Tucson are refused and preserved as future markets; Scottsdale publishes inside Phoenix as its "
    "own corridors."
)


def _market_ids(markets):
    """``participating_markets`` holds one record per market, not bare ids; read the ids out of it. (Testing a
    bare id against the records can never match, so a 'still deployable' refusal written that way could never
    fire -- the defect Denver's writer found and fixed.)"""
    return {m.get("market_id") if isinstance(m, dict) else m for m in (markets or ())}


def _refuse_if_unsafe(authorization_id):
    """No authorization naming the market may still be deployable, the new id must not collide with any
    record, and the readiness packet must bind the founder's package and no other."""
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
    authorization_id = "ptf-auth-phoenix-004-%s" % bundle_prefix
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
                         note="The founder authorized %s only (and refused every earlier Phoenix package); this is "
                              "that exact candidate, and only %s. No deployment was ordered: this authorization is "
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
