"""PTF-SAN-DIEGO-CA-FOUNDER-LAUNCH-AUTHORIZATION-003 -- build the global deployment manifest for the
founder-authorized whole-site candidate, then build and persist a NEW PREPARED->AUTHORIZED deployment
authorization binding that exact bundle to the founder's explicit statement in this order.

Deploys nothing; the authorization is inert until a deployer consumes it.

THE FIRST AUTHORIZATION THIS MARKET HAS EVER HAD
------------------------------------------------
San Diego has never been authorized and never deployed, so there is nothing to supersede and nothing to carry
forward. The safety check is still run: no authorization naming this market may already be deployable, and the
new id may not collide with an existing record.

WHY THE LIVE MANIFEST IS NOT OVERWRITTEN HERE
---------------------------------------------
This order STOPS BEFORE DEPLOYMENT, so writing ``global_deployment_manifest.json`` would leave the repository's
own cross-check describing a bundle production does not serve. The candidate manifest goes to the CANDIDATE
path; the deploying order writes the live manifest from these same bytes.
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

WORK_ORDER = "PTF-SAN-DIEGO-CA-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "san-diego-ca"
BUNDLE_MANIFEST_PATH = os.path.join("C:\\", "t", "sd3a", "global_bundle_manifest.json")
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_san_diego_003.json")
#: what production serves today (the JACKSONVILLE deployment), and therefore what a San Diego deployment would
#: roll back to. Resolved mechanically in Phase 1, not inherited from the parent module.
ROLLBACK_TARGET = "6ab6c8798bd9daf5038ae3e5"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'Founder work order PTF-SAN-DIEGO-CA-FOUNDER-LAUNCH-AUTHORIZATION-003: "Create the canonical founder launch '
    'authorization for San Diego and build the exact authorized production candidate. STOP BEFORE DEPLOYMENT." '
    'The founder explicitly decided: "The founder explicitly grants launch authorization for: san-diego-ca. The '
    'founder accepts the current sealed SAFE publication cohort: 147 approved pet-friendly profiles. The following '
    'remain deliberately unpublished: 130 no-website rows, 10 dual-brand rows, 52 additional safely held rows, 92 '
    'verified-no-pets except their canonical exclusion representation. This decision does NOT authorize: paid '
    'Google Places usage, weakening evidence rules, self-signing identity_resolutions.json, publishing held rows, '
    'flattening tiered/multi-part fees into misleading single numbers." -- bound to parent deployment '
    '6ab6c8798bd9daf5038ae3e5, parent release-index digest '
    'sha256:3bd26696cc3c8db69a6f54098cfcfa6deb7d74ff1d1b5fd408661b8dd120e44b, registered package digest '
    'sha256:5d5ffd65bf1262a17273100a2dc97ecfe80e54d61033441530dd05ab19914b7e, market bundle '
    '9d07caac8daaea5f17a348baab548e12a62ca8e66a2cd68dd69e4edb9acd6ffb, expected San Diego delta +1 market / '
    '+147 profiles / +162 release-index routes / +163 served routes. This is the FIRST authorization this market '
    'has ever had: nothing is superseded and nothing is carried forward. This authorization permits the existing '
    'release lifecycle to deploy that exact staged artifact only if every gate passes; the same order forbids '
    'deployment, so it is written AUTHORIZED and left unconsumed.'
)

NOTE = (
    "San Diego / Coastal San Diego County joins as the THIRTY-FIFTH market: 147 published pet-friendly profiles "
    "over 14 publishing corridors (downtown-gaslamp-waterfront, point-loma-shelter-island-airport, "
    "old-town-midway, mission-valley-hotel-circle, mission-pacific-beach, la-jolla, "
    "utc-golden-triangle-sorrento, del-mar-solana-beach, carlsbad, oceanside, south-bay-chula-vista, "
    "rancho-bernardo-poway-i15, east-county-i8, escondido-san-marcos-vista), 92 verified-no-pets published only "
    "as exclusions, and 192 unresolved identities staying unpublished -- 130 with no first-party website in any "
    "free lane, 10 in five dual-brand buildings, 52 held with their committed reasons. Registered as "
    "COMPOSITE_FRESH_MARKET_DATA_ONLY (FAST 15/15, 0 broad regression runs). No identity_resolutions.json ruling "
    "was written; no paid Places usage occurred; no tiered or multi-part fee is flattened. The other 6 corridors "
    "stay below their own publication minimum and were not forced. Membership is decided by the property's own "
    "postal code: Orange County, Riverside / Temecula, Palm Springs and Mexico are refused and preserved as "
    "future markets."
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
    authorization_id = "ptf-auth-san-diego-003-%s" % bundle_prefix
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
