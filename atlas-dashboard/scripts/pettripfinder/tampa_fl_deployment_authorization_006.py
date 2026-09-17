"""PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 -- write the global
deployment manifest from the independently-reproduced whole-site build, then
build and persist the PREPARED->AUTHORIZED deployment authorization binding
this exact bundle to the founder's explicit, already-issued authorization
statement. Deploys nothing; this only prepares the record a real `netlify
deploy` will be checked against.
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

BUNDLE_MANIFEST_PATH = r"C:\t\tpa6b\global_bundle_manifest.json"

WORK_ORDER = "PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
SOURCE_COMMIT = "9c63dabdf269ae24715d1d72edb269109efc3d5a"
ROLLBACK_TARGET = "6aa9dad7cf1419580b307f71"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    'Founder work order PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006: '
    '"I explicitly AUTHORIZE tampa-fl only under the exact committed founder packet: '
    'atlas-dashboard/launch_packages/pettripfinder/markets/reports/tampa_fl_founder_authorization_packet_005.json '
    'committed at: 0f150b60a44e6fa462526b57a762d64dd8828da9" -- bound to parent deployment '
    '6aa9dad7cf1419580b307f71, parent release digest '
    '084ac16aba3293b1e9fa02d8e8d95700251cb001dba5a24d45b0df5b4d1eb380, registered package digest '
    'sha256:38f6e4b2dc1f6a111985288f334ca93d66472423ccac760c98f05f47afaa9c8d, expected Tampa delta '
    '+1 market / +148 profiles. This authorization permits the existing release lifecycle to stage the '
    'real deployable candidate, compute its exact digests, independently verify/reproduce it, and deploy '
    'that exact staged artifact only if every gate passes.'
)


def main():
    bundle_manifest = json.load(open(BUNDLE_MANIFEST_PATH, encoding="utf-8"))
    manifest = GD.write_manifest(bundle_manifest)
    problems = GD.verify_manifest(manifest)
    print("global manifest problems:", problems)
    if problems:
        raise SystemExit("global manifest verification failed: %r" % problems)

    bundle_prefix = manifest["bundle_sha256"][:12]
    authorization_id = "ptf-auth-tampa-006-%s" % bundle_prefix

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
        note=("Tampa Bay, Florida joins as the TWENTY-NINTH market at 148 published pet-friendly "
              "profiles over 11 publishing corridors, 45 verified-no-pets, 314 held identities staying "
              "unpublished. Registered against the Orlando-live parent as COMPOSITE_FRESH_MARKET_DATA_ONLY "
              "(ELIGIBLE=YES, 0 broad). Whole-site candidate independently reproduced byte-identical across "
              "two separate build processes."),
    )

    verify_problems = DA.verify_authorization(auth, manifest=manifest)
    print("authorization verify_authorization problems:", verify_problems)
    if verify_problems:
        raise SystemExit("authorization verification failed: %r" % verify_problems)

    auth = DA.transition(auth, DA.AUTHORIZED,
                          note="Founder work order PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 "
                               "authorizes this exact candidate, and only tampa-fl.")

    path = DA.write_authorization(auth)
    print("authorization_id:", authorization_id)
    print("bundle_sha256:", manifest["bundle_sha256"])
    print("sitemap_sha256:", manifest["sitemap_sha256"])
    print("written:", path)


if __name__ == "__main__":
    main()
