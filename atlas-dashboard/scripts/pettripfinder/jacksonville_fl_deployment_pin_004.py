"""PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004 -- move the deployment pins to the
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

WORK_ORDER = "PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004"
DEPLOYMENT_ID = "6ab6c8798bd9daf5038ae3e5"
RECORD = os.path.join(_DASH, "deploy", "netlify", "deployment_records",
                      "ptf-deploy-jacksonville-004-%s.json" % DEPLOYMENT_ID)
MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json")
PIN = os.path.join(_DASH, "tests", "pettripfinder", "pins", "deployment_state.json")

NOTE = (
    "Jacksonville / Northeast Florida joined as the THIRTY-FOURTH market at 95 published pet-friendly profiles "
    "over 10 publishing corridors (amelia-island-fernandina-beach, atlantic-neptune-beach-mayport, "
    "deerwood-baymeadows, jacksonville-beach, jax-airport-northside, mandarin-bartram-julington-creek, "
    "orange-park-fleming-island, southside-university-boulevard, st-johns-town-center-gate-parkway, "
    "westside-i10-i295), on package pkg-jacksonville-fl-60ba2edccd4882b3. Built from zero on the "
    "West-Palm-Beach-live lineage, registered as COMPOSITE_FRESH_MARKET_DATA_ONLY with 0 broad regression runs, "
    "and founder-authorized once (PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003) -- this market's FIRST "
    "authorization and FIRST deployment, so nothing was superseded. The exact authorized artifact was deployed "
    "with no rebuild: the served sitemap hashes to the authorized candidate, the served route SET is identical "
    "to it, all 2767 parent routes refetched 200 with 0 lost, all 107 Jacksonville routes are live, and every "
    "probed unpublished census row returns 404 -- including both halves of the 1201 Kings Avenue dual-brand "
    "Hilton building, which the founder deliberately withheld and for which no identity_resolutions.json ruling "
    "was written. Amelia Island is served as a CORRIDOR of this market and was not promoted to a standalone "
    "market; every St. Augustine postal code remains refused. The city name JACKSONVILLE decides nothing here: "
    "jacksonville-nc is a separate LIVE market in Onslow County, North Carolina, and its 19 served routes and 99 "
    "files are byte-identical across this deploy. The other 7 corridors stay below their own publication minimum "
    "and were not forced. Rollback is the deployment Jacksonville replaced (West-Palm-Beach-live, 33 markets)."
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
        ("rollback_record", "ptf-deploy-west-palm-beach-007-%s.json" % record["previous_deployment_id"]),
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
