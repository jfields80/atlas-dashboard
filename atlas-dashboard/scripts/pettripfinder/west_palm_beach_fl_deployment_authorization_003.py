"""PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- build the global
deployment manifest for the founder-authorized whole-site candidate, then build
and persist the PREPARED->AUTHORIZED deployment authorization binding that exact
bundle to the founder's explicit, already-issued authorization statement.

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
is therefore written to the CANDIDATE path, and the live manifest is left exactly
as Fort Lauderdale's deployment left it. The deploying order writes the live
manifest from these same bytes.
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

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "west-palm-beach-fl"
BUNDLE_MANIFEST_PATH = os.path.join("C:\\", "t", "wpb3a", "global_bundle_manifest.json")
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_west_palm_beach_003.json")
#: what production serves today, and therefore what a West Palm Beach deployment rolls back to
ROLLBACK_TARGET = "6ab1a035c7ef3b14a23a4ec6"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'Founder work order PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003: "The founder '
    'explicitly grants launch authorization for west-palm-beach-fl. Build and gate the EXACT '
    'founder-authorized production candidate. STOP BEFORE DEPLOYMENT." -- bound to parent '
    'deployment 6ab1a035c7ef3b14a23a4ec6, parent release-index digest '
    'sha256:0ec19aa98462858d02a0770eb29e2cc124cfd7f7b82084ee34b2cc022062f94c, registered package '
    'digest sha256:789c0187e366abe8c199feb799ec691241d83ae81c3178e9cd4de41dde2c7bf8, expected '
    'West Palm Beach delta +1 market / +49 profiles / +55 release-index routes / +56 served '
    'routes. The same order states the limits of the grant: "Do not weaken evidence or identity '
    'standards. Do not publish held rows." This authorization permits the existing release '
    'lifecycle to deploy that exact staged artifact only if every gate passes; the same order '
    'forbids deployment, so it is written AUTHORIZED and left unconsumed.'
)

NOTE = (
    "The Palm Beaches join as the THIRTY-THIRD market at 49 published pet-friendly profiles over "
    "5 publishing corridors (downtown-west-palm-beach, palm-beach-gardens, "
    "palm-beach-international-airport, delray-beach, boca-raton), 25 verified-no-pets, 116 "
    "unresolved identities staying unpublished along with the four duplicate-premises halves "
    "held on identity. Built from zero on the Fort-Lauderdale-live release-factory lineage, "
    "closed through the supported attended-browser lane to 0 actionable unresolved rows, "
    "registered against the Fort-Lauderdale-live parent as COMPOSITE_FRESH_MARKET_DATA_ONLY with "
    "15/15 registration checks and 0 broad regression runs. The other 10 corridors stay below "
    "their own publication minimum and were not forced. Broward remains the LIVE "
    "fort-lauderdale-fl market's inventory and Miami-Dade the LIVE miami-fl market's; neither "
    "contributes one row here."
)


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
    authorization_id = "ptf-auth-west-palm-beach-003-%s" % bundle_prefix

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
