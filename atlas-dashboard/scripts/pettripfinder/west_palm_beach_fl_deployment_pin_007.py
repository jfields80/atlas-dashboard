"""PTF-WEST-PALM-BEACH-FL-PRODUCTION-DEPLOYMENT-007 -- move the deployment pins to the
West Palm Beach deployment that is now serving production.

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

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-PRODUCTION-DEPLOYMENT-007"
DEPLOYMENT_ID = "6ab599163f833ab7f48b395d"
RECORD = os.path.join(_DASH, "deploy", "netlify", "deployment_records",
                      "ptf-deploy-west-palm-beach-007-%s.json" % DEPLOYMENT_ID)
MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json")
PIN = os.path.join(_DASH, "tests", "pettripfinder", "pins", "deployment_state.json")

NOTE = (
    "The Palm Beaches joined as the THIRTY-THIRD market at 49 published pet-friendly profiles over 5 publishing "
    "corridors (boca-raton, delray-beach, downtown-west-palm-beach, palm-beach-gardens, "
    "palm-beach-international-airport), on the CORRECTED package pkg-west-palm-beach-fl-94d6f4115daa9b88. A "
    "pre-deploy identity correction publishes Hilton Garden Inn Boca Raton (bctbrgi) where the first authorized "
    "candidate carried a DBPR licensee name; that candidate and its authorization "
    "(ptf-auth-west-palm-beach-003-217f87eeba72) were SUPERSEDED before any deployment and never shipped. "
    "Re-registered as AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY with 0 broad regression runs and "
    "founder-authorized anew (PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006). The exact authorized "
    "artifact was deployed with no rebuild; the live sitemap hashes to the authorized candidate, all 2767 live "
    "routes return 200, every West Palm Beach page is byte-identical to the artifact, and the Apple Ten identity "
    "and all 141 unpublished census rows return 404. The other 10 corridors stay below their own publication "
    "minimum and were not forced. Rollback is the deployment West Palm Beach replaced (Fort-Lauderdale-live, 32 "
    "markets)."
)


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh, object_pairs_hook=OrderedDict)


def main():
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
        ("rollback_record", "ptf-deploy-fort-lauderdale-004-%s.json" % record["previous_deployment_id"]),
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
