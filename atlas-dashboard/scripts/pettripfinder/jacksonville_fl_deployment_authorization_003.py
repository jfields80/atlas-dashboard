"""PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- build the global
deployment manifest for the founder-authorized CORRECTED whole-site candidate, then
build and persist a NEW PREPARED->AUTHORIZED deployment authorization binding that
exact bundle to the founder's explicit statement in this order.

Deploys nothing; the authorization is inert until a deployer consumes it.

THE FIRST AUTHORIZATION THIS MARKET HAS EVER HAD
------------------------------------------------
Jacksonville has never been authorized and never deployed, so there is nothing to supersede and nothing to
refuse to carry forward. The safety check is still run: no authorization naming this market may already be
deployable, and the new id may not collide with an existing record.

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

WORK_ORDER = "PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "jacksonville-fl"
BUNDLE_MANIFEST_PATH = os.path.join("C:\\", "t", "jax3a", "global_bundle_manifest.json")
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_jacksonville_003.json")
#: what production serves today (the WEST PALM BEACH deployment), and therefore what a Jacksonville
#: deployment would roll back to. Resolved mechanically in Phase 1, not inherited from the parent module.
ROLLBACK_TARGET = "6ab599163f833ab7f48b395d"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'Founder work order PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003: "Create the canonical founder '
    'launch authorization for Jacksonville and build the EXACT authorized production candidate. STOP BEFORE '
    'DEPLOYMENT." The founder explicitly decided: "1. AUTHORIZE the current sealed 95-profile Jacksonville '
    'publication cohort. 2. DO NOT resolve or publish the 1201 Kings Avenue dual-brand Hilton pair in this '
    'order. Keep both rows on their existing safe identity hold. Do NOT create or self-sign an '
    'identity_resolutions.json ruling. 3. KEEP Amelia Island at its CURRENT proven corridor classification. Do '
    'NOT promote Amelia Island into a standalone market in this order. 4. ACCEPT current coverage readiness at '
    '42.16% resolution because ACTIONABLE UNRESOLVED = 0 and the remaining unresolved population is bounded by '
    'documented access/evidence constraints, including Marriott Akamai limits, ESA DataDome restrictions and '
    'unresolved independents. This decision does NOT authorize weaker evidence rules." -- bound to parent '
    'deployment 6ab599163f833ab7f48b395d, parent release-index digest '
    'sha256:fda6317bf022fb103f397d99ff4a4c72ac49105b992cb34ac1ba335ecb8e7445, registered package digest '
    'sha256:60ba2edccd4882b38785d69c016f39f550924675d54197004adaf994b55c0536, market bundle '
    'a98efbea86c38a268bfa489354add4a700a0d4bc0ab13df740a5ae35ee842636, expected Jacksonville delta +1 market / '
    '+95 profiles / +106 release-index routes / +107 served routes. This is the FIRST authorization this market '
    'has ever had: nothing is superseded and nothing is carried forward. This authorization permits the '
    'existing release lifecycle to deploy that exact staged artifact only if every gate passes; the same order '
    'forbids deployment, so it is written AUTHORIZED and left unconsumed.'
)

NOTE = (
    "Jacksonville / Northeast Florida joins as the THIRTY-FOURTH market: 95 published pet-friendly profiles "
    "over 10 publishing corridors (jax-airport-northside, westside-i10-i295, "
    "southside-university-boulevard, st-johns-town-center-gate-parkway, deerwood-baymeadows, "
    "mandarin-bartram-julington-creek, jacksonville-beach, atlantic-neptune-beach-mayport, "
    "orange-park-fleming-island, amelia-island-fernandina-beach), 18 verified-no-pets, and 155 unresolved "
    "identities staying unpublished. Registered as COMPOSITE_FRESH_MARKET_DATA_ONLY (FAST 15/15, 0 broad "
    "regression runs). The 1201 Kings Avenue dual-brand Hilton pair stays on its identity hold and publishes "
    "nothing; no identity_resolutions.json ruling was written. Amelia Island publishes as a CORRIDOR of this "
    "market and is not promoted to a standalone market. The other 7 corridors stay below their own publication "
    "minimum and were not forced. Membership is decided by the property's own postal code and never by its "
    "name -- jacksonville-nc is a separate LIVE market in Onslow County, North Carolina, and is untouched."
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
    authorization_id = "ptf-auth-jacksonville-003-%s" % bundle_prefix
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
