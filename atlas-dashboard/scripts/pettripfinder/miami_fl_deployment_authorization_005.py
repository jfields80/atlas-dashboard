"""PTF-MIAMI-FL-FOUNDER-LAUNCH-AUTHORIZATION-005 -- build the global deployment
manifest for the founder-authorized whole-site candidate, then build and persist
the PREPARED->AUTHORIZED deployment authorization binding that exact bundle to
the founder's explicit, already-issued authorization statement.

Deploys nothing. This only prepares the record a real ``netlify deploy`` will be
checked against, and the authorization is inert until a deployer consumes it.

WHY THE LIVE MANIFEST IS NOT OVERWRITTEN HERE
---------------------------------------------
Every recent launch wrote ``deploy/netlify/global_deployment_manifest.json`` and
deployed in the same order, so the manifest and the newest DEPLOYED record agreed
again within minutes. This order STOPS BEFORE DEPLOYMENT by founder instruction,
so writing the live manifest would leave the repository's own cross-check
(``release_coordinator inspect``: "disagreement with the record is a problem, not
a tiebreak") describing a bundle production does not serve. The candidate manifest
is therefore written to the CANDIDATE path -- the shape
``global_deployment_manifest_candidate_032.json`` already established for "the
next production deployment CANDIDATE ... not an authorization" -- and the live
manifest is left exactly as Augusta's deployment left it. The deploying order
writes the live manifest from these same bytes.
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

WORK_ORDER = "PTF-MIAMI-FL-FOUNDER-LAUNCH-AUTHORIZATION-005"
MARKET = "miami-fl"
BUNDLE_MANIFEST_PATH = os.path.join("C:\\", "t", "mia5a", "global_bundle_manifest.json")
CANDIDATE_MANIFEST_PATH = os.path.join(_DASH, "deploy", "netlify",
                                       "global_deployment_manifest_candidate_miami_005.json")
#: what production serves today, and therefore what a Miami deployment rolls back to
ROLLBACK_TARGET = "6aaeb3b7384e1bb712adb084"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'Founder work order PTF-MIAMI-FL-FOUNDER-LAUNCH-AUTHORIZATION-005: "Founder authorization is '
    'explicitly granted for: miami-fl. Proceed through the normal founder-launch-authorization path '
    'and build the exact AUTHORIZED production candidate. STOP BEFORE DEPLOYMENT." -- bound to parent '
    'deployment 6aaeb3b7384e1bb712adb084, parent release-index digest '
    'sha256:c7998b87f638354ec5db316487f77c089f4351966aad9b0d99b4add74f0dd023, registered package digest '
    'sha256:b586ad449e46d0572c8b3c9248d56a8dcec7a51c4bf938598e9f1428f0b73cb1, expected Miami delta '
    '+1 market / +125 profiles / +136 routes. This authorization permits the existing release lifecycle '
    'to deploy that exact staged artifact only if every gate passes; the same order forbids deployment, '
    'so it is written AUTHORIZED and left unconsumed.'
)

NOTE = (
    "Greater Miami joins as the THIRTY-FIRST market at 125 published pet-friendly profiles over 10 "
    "publishing corridors (downtown-brickell, south-beach, mid-beach, mia-airport-miami-springs, "
    "airport-west-blue-lagoon, doral, midtown-wynwood-edgewater, aventura, kendall-south-dade, "
    "homestead-florida-city), 57 verified-no-pets, 455 held identities staying unpublished. Built from "
    "zero on the repaired release-factory lineage, closed through the authorized attended-browser lane "
    "to 0 actionable unresolved rows, registered against the Augusta-live parent as "
    "COMPOSITE_FRESH_MARKET_DATA_ONLY with 15/15 registration checks and 0 broad regression runs. "
    "Coral Gables stays below its publication minimum at 4 verified pet-friendly and was not forced."
)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-manifest", default=BUNDLE_MANIFEST_PATH)
    ap.add_argument("--write", action="store_true", help="persist the candidate manifest and the authorization")
    args = ap.parse_args(argv)

    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_DASH, text=True).strip()
    with open(args.bundle_manifest, encoding="utf-8-sig") as fh:
        bundle_manifest = json.load(fh)

    manifest = GD.build_manifest(bundle_manifest)
    problems = GD.verify_manifest(manifest)
    print("global manifest problems:", problems)
    if problems:
        raise SystemExit("global manifest verification failed: %r" % problems)

    bundle_prefix = manifest["bundle_sha256"][:12]
    authorization_id = "ptf-auth-miami-005-%s" % bundle_prefix

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
