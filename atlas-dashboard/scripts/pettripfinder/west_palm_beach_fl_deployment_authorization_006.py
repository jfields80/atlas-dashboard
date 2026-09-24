"""PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006 -- build the global
deployment manifest for the founder-authorized CORRECTED whole-site candidate, then
build and persist a NEW PREPARED->AUTHORIZED deployment authorization binding that
exact bundle to the founder's explicit statement in this order.

Deploys nothing; the authorization is inert until a deployer consumes it.

A NEW AUTHORIZATION, NEVER THE OLD ONE
--------------------------------------
``ptf-auth-west-palm-beach-003-217f87eeba72`` bound bundle 217f87ee (package 789c0187)
and is SUPERSEDED -- terminal, unconsumed. It is neither read for its bindings nor
transitioned here: SUPERSEDED has no outgoing edge, and this module refuses to run if
any authorization naming the market is still deployable or if the new id collides
with an existing record.

WHY THE LIVE MANIFEST IS NOT OVERWRITTEN HERE
---------------------------------------------
This order STOPS BEFORE DEPLOYMENT, so writing ``global_deployment_manifest.json``
would leave the repository's own cross-check describing a bundle production does not
serve. The candidate manifest goes to the CANDIDATE path; the deploying order writes
the live manifest from these same bytes.
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

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006"
MARKET = "west-palm-beach-fl"
BUNDLE_MANIFEST_PATH = os.path.join("C:\\", "t", "wpb6a", "global_bundle_manifest.json")
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_west_palm_beach_006.json")
#: what production serves today, and therefore what a West Palm Beach deployment rolls back to
ROLLBACK_TARGET = "6ab1a035c7ef3b14a23a4ec6"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'Founder work order PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006: "The founder '
    'explicitly grants a NEW launch authorization for the corrected West Palm Beach package. Create '
    'the canonical founder authorization for the corrected package and build the EXACT '
    'founder-authorized production candidate. STOP BEFORE PRODUCTION DEPLOYMENT." and "Authorize the '
    'corrected West Palm Beach publication cohort. The Hilton Garden Inn Boca Raton identity correction '
    'has been reviewed and accepted. The superseded package/authorization does not carry forward." -- '
    'bound to parent deployment 6ab1a035c7ef3b14a23a4ec6, parent release-index digest '
    'sha256:97ec0244d157683a50ddb57f9d55ce50ba15e61a96f6c42b9118bba1cf578c7f, corrected package digest '
    'sha256:94d6f4115daa9b88a8773d2b73b49593c5de4a4757125def52b7ba17c25ec086, corrected market bundle '
    '711760f09faddc8022b5d55a681c0ccd0937151a2d61be34d67cbdd0c934ef45, expected West Palm Beach delta +1 '
    'market / +49 profiles / +55 release-index routes / +56 served routes. The superseded authorization '
    'ptf-auth-west-palm-beach-003-217f87eeba72 (bundle 217f87ee, package 789c0187) authorizes nothing. '
    'This authorization permits the existing release lifecycle to deploy that exact staged artifact only '
    'if every gate passes; the same order forbids deployment, so it is written AUTHORIZED and left '
    'unconsumed.'
)

NOTE = (
    "West Palm Beach joins as the THIRTY-THIRD market on its CORRECTED package: 49 published "
    "pet-friendly profiles over 5 publishing corridors (downtown-west-palm-beach, palm-beach-gardens, "
    "palm-beach-international-airport, delray-beach, boca-raton), 25 verified-no-pets, 116 unresolved "
    "identities staying unpublished. The pre-deploy identity correction publishes Hilton Garden Inn Boca "
    "Raton (bctbrgi) where the superseded candidate published a DBPR licensee name. Re-registered as "
    "AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY (17/17, 0 broad regression runs). The other 10 "
    "corridors stay below their own publication minimum and were not forced."
)


def _refuse_if_unsafe(authorization_id):
    """No authorization naming the market may still be deployable, and the new id
    must not collide with any record: the old authorization is never reused."""
    existing = DA.list_authorizations()
    if any(a.get("authorization_id") == authorization_id for a in existing):
        raise SystemExit("authorization %s already exists; a new decision writes a new record" % authorization_id)
    live = [a["authorization_id"] for a in existing
            if MARKET in (a.get("participating_markets") or ()) and a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
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

    bundle_prefix = manifest["bundle_sha256"][:12]
    authorization_id = "ptf-auth-west-palm-beach-006-%s" % bundle_prefix
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
                         note="Founder work order %s authorizes this exact candidate, and only %s. "
                              "The same order forbids deployment: this authorization is written "
                              "AUTHORIZED and left UNCONSUMED." % (WORK_ORDER, MARKET))

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
