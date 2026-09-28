"""PTF-DENVER-CO-PRODUCTION-DEPLOYMENT-005 -- move the deployment pins to the
Denver deployment that is now serving production.

Both blocks move, and both are DERIVED from committed evidence, never typed:

  live    from the deployment record this order just wrote (what production serves)
  source  from the committed global deployment manifest (what a fresh assembly of
          the committed source produces)

They agree after this deploy -- the deployed artifact IS the committed source's
artifact -- so ``ahead_of_production`` is false and ``moved_by`` is null, which is
what the pin's own contract says that state means.
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-DENVER-CO-PRODUCTION-DEPLOYMENT-005"
DEPLOYMENT_ID = sys.argv[1] if len(sys.argv) > 1 else None   # the Netlify deploy id this order's deploy returned
RECORD = os.path.join(_DASH, "deploy", "netlify", "deployment_records",
                      "ptf-deploy-denver-005-%s.json" % DEPLOYMENT_ID)
MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json")
PIN = os.path.join(_DASH, "tests", "pettripfinder", "pins", "deployment_state.json")

NOTE = (
    "Denver / Boulder / Front Range, Colorado joined as the THIRTY-SIXTH market and the first Colorado market at "
    "288 published pet-friendly profiles over 16 publishing corridors (aurora, boulder, central-park-lowry-i70, "
    "cherry-creek-glendale, den-airport, denver-tech-center, downtown-lodo-union-station, golden-red-rocks, "
    "highlands-rino-north-denver, lakewood-wheat-ridge, littleton-englewood, longmont-erie, "
    "louisville-superior-lafayette, parker-southeast, thornton-northglenn-north-i25, westminster-broomfield), on "
    "package pkg-denver-co-07f10db29ab56d98. Built from zero on the San Diego-live lineage, registered as "
    "COMPOSITE_FRESH_MARKET_DATA_ONLY with 0 broad regression runs, corrected before authorization (the "
    "not-yet-open ECHO Suites Thornton held), and founder-authorized once "
    "(PTF-DENVER-CO-FOUNDER-LAUNCH-AUTHORIZATION-004; the superseded 289-profile package pkg-denver-co-91b2e0a2 "
    "was refused) -- this market's FIRST authorization and FIRST deployment, so nothing was superseded. The exact "
    "authorized artifact was deployed with no rebuild: the served sitemap hashes to the authorized candidate, the "
    "served route SET is identical to it, all 3037 parent routes refetched 200 with 0 lost, all 306 Denver routes "
    "are live, and every unpublished census row returns 404 -- 52 with no first-party website, 16 founder-decision "
    "rows (seven dual-brand buildings, no identity_resolutions.json ruling written; two ESA title collisions, no "
    "display name invented), 38 router-exhausted, the not-yet-open ECHO Suites Thornton and the 46 "
    "verified-no-pets rows, which publish only as exclusions. Colorado Springs, Fort Collins / Loveland, Estes "
    "Park and the ski resorts remain refused. The other 4 corridors stay below their own publication minimum and "
    "were not forced. Rollback is the deployment Denver replaced (San Diego-live, 35 markets)."
)


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh, object_pairs_hook=OrderedDict)


def main():
    if not DEPLOYMENT_ID:
        raise SystemExit("usage: denver_co_deployment_pin_005 <deployment id>")
    record = _load(RECORD)
    manifest = _load(MANIFEST)
    pin = _load(PIN)

    live = OrderedDict([
        ("deploy_id", record["deployment_id"]),
        ("deployed_by", WORK_ORDER),
        ("authorization_id", record["authorization_id"]),
        ("deployment_record_id", record["deployment_record_id"]),
        ("previous_deploy_id", record["previous_deployment_id"]),
        ("source_commit", record["source_commit"]),
        ("bundle_sha256", record["bundle_sha256"]),
        ("sitemap_sha256", record["sitemap_sha256"]),
        ("participating_markets", record["participating_markets"]),
        ("profile_counts", record["profile_counts"]),
        ("total_profiles", record["total_profiles"]),
        ("sitemap_route_count", record["sitemap_route_count"]),
        # the record does not restate the page/file counts; they belong to the artifact, and the
        # manifest this deploy was authorized against is where the artifact states them.
        ("total_html_pages", manifest["total_html_pages"]),
        ("total_files", manifest["total_files"]),
        ("rollback_target", record["previous_deployment_id"]),
        ("note", NOTE),
        ("rollback_record", "ptf-deploy-san-diego-004-%s.json" % record["previous_deployment_id"]),
    ])

    source = OrderedDict([
        ("ahead_of_production", False),
        ("moved_by", None),
        ("bundle_sha256", manifest["bundle_sha256"]),
        ("sitemap_sha256", manifest["sitemap_sha256"]),
        ("participating_markets", manifest["participating_markets"]),
        ("profile_counts", OrderedDict(sorted(record["profile_counts"].items()))),
        ("total_profiles", manifest["total_published_profiles"]),
        ("sitemap_route_count", manifest["sitemap_route_count"]),
        ("total_html_pages", manifest["total_html_pages"]),
        ("total_files", manifest["total_files"]),
    ])

    disagreements = [k for k in ("bundle_sha256", "sitemap_sha256", "total_profiles",
                                 "sitemap_route_count", "total_html_pages", "total_files")
                     if live[k] != source[k]]
    if disagreements:
        raise SystemExit("live and source disagree after a deploy of the source's own bytes: %r"
                         % disagreements)

    pin["reviewed_by"] = WORK_ORDER
    pin["live"] = live
    pin["source"] = source
    with open(PIN, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pin, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("pin moved to :", record["deployment_id"])
    print("markets      :", len(live["participating_markets"]))
    print("profiles     :", live["total_profiles"])
    print("routes       :", live["sitemap_route_count"])
    print("bundle       :", live["bundle_sha256"])
    print("rollback     :", live["rollback_target"])
    print("written      :", os.path.relpath(PIN, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
