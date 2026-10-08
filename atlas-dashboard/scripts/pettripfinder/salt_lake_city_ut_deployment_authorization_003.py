"""PTF-SALT-LAKE-CITY-UT-FOUNDER-LAUNCH-AUTHORIZATION-003 -- build the global deployment manifest for the
founder-authorized whole-site candidate, then build and persist a NEW PREPARED->AUTHORIZED deployment authorization
binding that exact bundle to the founder's explicit statement (cloned in shape from New Orleans' 003 writer). NOTHING
IS DEPLOYED AND THE AUTHORIZATION IS NOT CONSUMED: this order stops before production deployment.

    python -m scripts.pettripfinder.salt_lake_city_ut_deployment_authorization_003 [--bundle-manifest ...] [--write]

THE FIRST AUTHORIZATION THIS MARKET HAS EVER HAD. Salt Lake City has never been authorized or deployed, so there is
nothing to supersede. The module refuses unless the candidate it binds carries salt-lake-city-ut, the readiness packet
binds pkg-salt-lake-city-ut-6d474d2906ae01e0 and no other package, the participation record reads
FOUNDER_AUTHORIZED_FOR_LAUNCH, no authorization is already deployable, and the new id does not collide with an
existing record.

SOURCE COMMIT = THE BUILD COMMIT. ``source_commit`` is the commit the candidate was assembled from (its manifest's own
``source_commit``), never HEAD: the live pin's source commit must equal the committed manifest's, and a metadata
commit after the build moves HEAD and no site byte.

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

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402
from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import launch_participation as LP       # noqa: E402

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "salt-lake-city-ut"
AUTHORIZED_PACKAGE_ID = "pkg-salt-lake-city-ut-6d474d2906ae01e0"
REGISTRATION_COMMIT = "2822639c"
FOUNDER_DECISION_COMMIT = "6959e985"
REFUSED_PACKAGE_PREFIXES = ("pkg-salt-lake-city-ut-f084558e", "pkg-salt-lake-city-ut-cb60864b")
READINESS_PATH = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                              "salt_lake_city_ut_authorization_readiness_002.json")
CHECKS_PATH = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "salt_lake_city_ut_registration_checks_002.json")
BUNDLE_MANIFEST_PATH = "C:/t/slc4a/global_bundle_manifest.json"
CANDIDATE_MANIFEST_PATH = os.path.join(
    _DASH, "deploy", "netlify", "global_deployment_manifest_candidate_salt_lake_city_003.json")
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"

FOUNDER_WORDS = ("The founder explicitly authorizes launch of: salt-lake-city-ut ONLY for the exact CURRENT registered "
                 "Salt Lake City package created by PTF-SALT-LAKE-CITY-UT-REGISTRATION-AND-STAGING-002 and bound to: "
                 "2822639c. The founder approves the current safe publication cohort: 133 pet-friendly profiles. "
                 "Keep ALL unresolved / held rows unpublished.")


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
    if LP.launch_status(MARKET) != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH:
        raise SystemExit("%s reads %s, not FOUNDER_AUTHORIZED_FOR_LAUNCH" % (MARKET, LP.launch_status(MARKET)))
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
    if not str(manifest["source_commit"]).startswith(FOUNDER_DECISION_COMMIT):
        raise SystemExit("the candidate was assembled from %s, not the founder-decision commit %s"
                         % (manifest["source_commit"], FOUNDER_DECISION_COMMIT))

    authorization_id = "ptf-auth-salt-lake-city-003-%s" % manifest["bundle_sha256"][:12]
    readiness = _refuse_if_unsafe(authorization_id)
    rollback_target = _live_deploy_id()
    if readiness["the_digests_this_readiness_binds"]["parent_live_deploy_id"] != rollback_target:
        raise SystemExit("the readiness packet's parent is not the live deploy %s" % rollback_target)
    binds = readiness["the_digests_this_readiness_binds"]
    with open(CHECKS_PATH, encoding="utf-8-sig") as fh:
        projected = json.load(fh)["projected_accounting"]

    authorization_source = (
        'The founder, in work order %s: "%s" -- the package id read mechanically from the registration commit and '
        'the readiness packet (the founder\'s console recap was truncated and is not used): registered package %s '
        '(%s), bound to registration commit %s, founder decision commit %s, parent deployment %s, parent '
        'release-index digest %s, market bundle %s, expected Salt Lake City delta +1 market / +%d profiles / +%d '
        'release-index routes / +%d served routes. The approved cohort publishes 133 pet-friendly profiles and 29 '
        'verified-no-pets exclusions (never as hotel profiles); all 47 unresolved rows stay unpublished -- Hyatt Place '
        'Salt Lake City / Cottonwood (a first-party page that welcomes pets and states "No pets are allowed in '
        '4th-floor rooms"; the shared reader is not weakened and no disposition is forced), Hyatt Place Salt Lake '
        'City / Lehi (first-party ZIP 84048 against 84043 elsewhere; no ZIP is invented), the three Vail Canyons '
        'Village rows, the preopening Ascent and the router-exhausted rest -- the timeshare / vacation-ownership, '
        'private condo / residence / rental and military-restricted identities stay outside hotel inventory, every '
        'Park City premises publishes as Park City, UT, and no identity_resolutions.json ruling is written. The '
        'source-ready shadow id pkg-salt-lake-city-ut-f084558e8d8acabe and the superseded cb60864b seal are not '
        'authorized. This is the FIRST authorization this market has had: nothing is superseded. This order stops '
        'before deployment; the authorization is created AUTHORIZED and is not consumed here.'
        % (WORK_ORDER, FOUNDER_WORDS, binds["sealed_package_id"], binds["sealed_package_digest"],
           REGISTRATION_COMMIT, FOUNDER_DECISION_COMMIT, rollback_target, binds["parent_release_digest"],
           binds["changed_market_bundle_sha256"], projected["SALT_LAKE_CITY_PROJECTED_PROFILES"],
           projected["SALT_LAKE_CITY_RELEASE_INDEX_ROUTES"], projected["SALT_LAKE_CITY_SERVED_ROUTES"]))
    note = (
        "Salt Lake City / Park City / Wasatch Front joins as the FORTY-FIFTH market and the first Utah market: 133 "
        "published pet-friendly profiles over 10 publishing corridors, 29 verified-no-pets published only as "
        "exclusions, and 47 unresolved identities staying unpublished. Every row publishes the municipality its own "
        "postal code carries (Salt Lake 159, Summit 32, Utah 13, Davis 5 qualifying rows; 0 Park City premises "
        "labelled Salt Lake City). Registered as COMPOSITE_FRESH_MARKET_DATA_ONLY with automatic base derivation and "
        "classification (FAST 15/15, 0 broad regression runs). No identity_resolutions.json ruling was written; the "
        "shared reader was not weakened; no paid spend occurred; no tiered, capped, conditional or multi-amount fee "
        "is flattened. The other 9 corridors stay below their own publication minimum.")

    auth = DA.build_authorization(
        manifest, authorization_id=authorization_id, work_order=WORK_ORDER, authorized_by="founder",
        source_commit=manifest["source_commit"], rollback_target=rollback_target, target_site=TARGET_SITE,
        target_domain=TARGET_DOMAIN, authorization_source=authorization_source, note=note)
    verify_problems = DA.verify_authorization(auth, manifest=manifest)
    print("authorization verify_authorization problems:", verify_problems)
    if verify_problems:
        raise SystemExit("authorization verification failed: %r" % verify_problems)
    auth = DA.transition(auth, DA.AUTHORIZED,
                         note="The founder authorized %s for launch, bound to registration commit %s. This is that "
                              "exact candidate (built twice, byte-identical), and only %s. Not deployed, not consumed."
                              % (AUTHORIZED_PACKAGE_ID, REGISTRATION_COMMIT, MARKET))
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
