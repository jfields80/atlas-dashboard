"""PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 -- write the
global deployment manifest from the independently-reproduced whole-site
build, then build and persist the PREPARED->AUTHORIZED deployment
authorization binding this exact bundle to the founder's explicit,
already-issued authorization statement. Deploys nothing; this only prepares
the record a real `netlify deploy` will be checked against.
"""
from __future__ import annotations

import json
import os
import sys

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402

BUNDLE_MANIFEST_PATH = os.path.join(_DASH, "taug6a", "global_bundle_manifest.json")

WORK_ORDER = "PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
SOURCE_COMMIT = None  # filled in main() from the committed HEAD at run time
ROLLBACK_TARGET = "6aab379e0777c9ee96702a4f"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'Founder work order PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006: '
    '"I explicitly AUTHORIZE augusta-ga only under the exact committed founder packet: '
    'atlas-dashboard/launch_packages/pettripfinder/markets/reports/augusta_ga_founder_authorization_packet_005.json" '
    '-- bound to parent deployment 6aab379e0777c9ee96702a4f, parent release digest '
    'cf761795e3deb1380ffb8e25869bd6ceefe31d2a9dfbaddad30c550ff69d60d2, registered package digest '
    'sha256:14806eca154760a0a9dc59b200b4fa83e4f748b4ebc8eba197eab8d1e50c0df6, expected Augusta delta '
    '+1 market / +14 profiles. This authorization permits the existing release lifecycle to stage the '
    'real deployable candidate, compute its exact digests, independently verify/reproduce it, and deploy '
    'that exact staged artifact only if every gate passes.'
)


def main():
    import subprocess
    global SOURCE_COMMIT
    SOURCE_COMMIT = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=_DASH, text=True).strip()

    bundle_manifest = json.load(open(BUNDLE_MANIFEST_PATH, encoding="utf-8"))
    manifest = GD.write_manifest(bundle_manifest)
    problems = GD.verify_manifest(manifest)
    print("global manifest problems:", problems)
    if problems:
        raise SystemExit("global manifest verification failed: %r" % problems)

    bundle_prefix = manifest["bundle_sha256"][:12]
    authorization_id = "ptf-auth-augusta-006-%s" % bundle_prefix

    auth = DA.build_authorization(
        manifest,
        authorization_id=authorization_id,
        work_order=WORK_ORDER,
        authorized_by="founder",
        source_commit=SOURCE_COMMIT,
        rollback_target=ROLLBACK_TARGET,
        target_site=TARGET_SITE,
        target_domain=TARGET_DOMAIN,
        authorization_source=AUTHORIZATION_SOURCE,
        note=("Augusta, Georgia joins as the THIRTIETH market at 14 published pet-friendly "
              "profiles over 1 publishing corridor (Washington Road), 14 verified-no-pets, 63 held "
              "identities staying unpublished. Registered against the Savannah-live parent, "
              "resealed against Orlando-live then Tampa-live as each superseded the last. Automated "
              "narrow classifier NOT APPLICABLE for the live-lineage-merge reason recorded in "
              "founder packets 004/005; 0 broad regression run. Whole-site candidate independently "
              "reproduced byte-identical across two separate build processes."),
    )

    verify_problems = DA.verify_authorization(auth, manifest=manifest)
    print("authorization verify_authorization problems:", verify_problems)
    if verify_problems:
        raise SystemExit("authorization verification failed: %r" % verify_problems)

    auth = DA.transition(auth, DA.AUTHORIZED,
                          note="Founder work order PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 "
                               "authorizes this exact candidate, and only augusta-ga.")

    path = DA.write_authorization(auth)
    print("authorization_id:", authorization_id)
    print("bundle_sha256:", manifest["bundle_sha256"])
    print("sitemap_sha256:", manifest["sitemap_sha256"])
    print("written:", path)


if __name__ == "__main__":
    main()
