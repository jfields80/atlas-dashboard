"""PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 -- the last check before the host call.

Two questions, asked immediately before deploying and not before that:

  1  IS THE PARENT STILL THE ONE THE FOUNDER AUTHORIZED?
     Read from the committed deployment records AND from production itself. An
     already-authorized candidate is never silently rebased: if a newer release
     became live, this stops with STALE_PARENT and deploys nothing.

  2  ARE THE STAGED BYTES STILL THE AUTHORIZED BYTES?
     The directory about to be uploaded is RE-HASHED -- not rebuilt. Rebuilding
     to check would defeat the point of Phase 7: what must be proved is that
     these exact bytes are the authorized ones, and a fresh build proves only
     that a build is reproducible.

WHY THE PARENT IS NOT READ FROM release_index HERE

By this point the global deployment manifest has deliberately been moved ahead
to describe the AUTHORIZED bundle, because a manifest that still describes the
previous bundle leaves deployability_problems non-empty forever
(PTF-DAYTON-OH-DEPLOYMENT-AUTHORIZATION-003). ``release_index.live_index``
reconciles the manifest against the deployment record and so reports that
staging as an inconsistency. It is not one: the record is the authority for what
is DEPLOYED, and this reads the record and the live site directly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from collections import OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
MARKET_ID = "nashville-tn"
DEPLOY = _DASH / "deploy" / "netlify"
RECORDS = DEPLOY / "deployment_records"
AUTH_DIR = DEPLOY / "deployment_authorizations"
LIVE_SITEMAP = "https://pettripfinder.com/sitemap.xml"


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def deployed_records():
    """Every committed deployment record that reached DEPLOYED, newest last."""
    out = []
    for path in sorted(RECORDS.glob("*.json")):
        doc = _load(path)
        if doc.get("final_status") == "DEPLOYED":
            out.append(doc)
    out.sort(key=lambda d: d.get("deployed_at") or "")
    return out


def live_sitemap():
    request = urllib.request.Request(
        LIVE_SITEMAP, headers={"User-Agent": "ptf-release-audit/1.0"})
    body = urllib.request.urlopen(request, timeout=60).read()
    routes = {re.sub(r"^https?://[^/]+", "", u)
              for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body.decode("utf-8"))}
    return hashlib.sha256(body).hexdigest(), sorted(routes)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--site-dir", required=True, help="the staged bundle's site/ directory")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    from scripts.pettripfinder import deployment_authorization as DA

    auth = _load(AUTH_DIR / ("%s.json" % args.authorization))
    expected_parent = auth["rollback_target"]

    records = deployed_records()
    newest = records[-1] if records else None
    if newest is None:
        raise SystemExit("STOP: no deployed record exists; there is no parent to launch onto")
    if newest["deployment_id"] != expected_parent:
        raise SystemExit(
            "STALE_PARENT = YES. The authorization binds parent %s; the newest deployed record "
            "is %s. An already-authorized candidate is never silently rebased -- a new candidate "
            "must be composed on the new parent." % (expected_parent, newest["deployment_id"]))

    sitemap_sha, live_routes = live_sitemap()
    if sitemap_sha != newest["sitemap_sha256"]:
        raise SystemExit(
            "STOP: production serves sitemap %s but the record for %s states %s. The record and "
            "the live site disagree, so there is no verified parent to launch onto."
            % (sitemap_sha, newest["deployment_id"], newest["sitemap_sha256"]))

    for required in ("lexington-ky", "toledo-oh"):
        if required not in newest["participating_markets"]:
            raise SystemExit("STOP: %s is not in the live parent" % required)
    if MARKET_ID in newest["participating_markets"]:
        raise SystemExit("STOP: %s is already live in the parent" % MARKET_ID)

    # PHASE 7: the staged bytes, re-hashed rather than rebuilt.
    site_dir = Path(args.site_dir)
    artifact_problems = DA.verify_bundle_directory(auth, site_dir)
    if artifact_problems:
        raise SystemExit(
            "STOP: the staged artifact is not the authorized artifact: %s. Compose a NEW "
            "candidate rather than reconciling this." % artifact_problems)

    from scripts.pettripfinder.assemble_production_site import bundle_digest, file_hashes
    hashes = file_hashes(site_dir)
    staged_digest = bundle_digest(hashes)

    doc = OrderedDict((
        ("schema", "ptf-predeploy-check/1.0"),
        ("work_order", WORK_ORDER),
        ("authorization_id", args.authorization),
        ("parent", OrderedDict((
            ("expected_deployment_id", expected_parent),
            ("newest_deployed_record", newest["deployment_id"]),
            ("still_the_authorized_parent", True),
            ("record_bundle_sha256", newest["bundle_sha256"]),
            ("record_sitemap_sha256", newest["sitemap_sha256"]),
            ("live_sitemap_sha256", sitemap_sha),
            ("live_agrees_with_record", sitemap_sha == newest["sitemap_sha256"]),
            ("live_route_count", len(live_routes)),
            ("markets", len(newest["participating_markets"])),
            ("profiles", newest["total_profiles"]),
            ("lexington_live", "lexington-ky" in newest["participating_markets"]),
            ("toledo_live", "toledo-oh" in newest["participating_markets"]),
            ("nashville_not_yet_live", MARKET_ID not in newest["participating_markets"]),
            ("STALE_PARENT", False),
        ))),
        ("artifact", OrderedDict((
            ("site_dir", str(site_dir)),
            ("files", len(hashes)),
            ("staged_bundle_sha256", staged_digest),
            ("authorized_bundle_sha256", auth["bundle_sha256"]),
            ("staged_equals_authorized", staged_digest == auth["bundle_sha256"]),
            ("verified_by", "deployment_authorization.verify_bundle_directory"),
            ("problems", artifact_problems),
            ("rebuilt_to_check", False),
            ("how", "the directory was RE-HASHED, never rebuilt: what has to be proved is that "
                    "these exact bytes are the authorized ones."),
        ))),
        ("live_routes_before_deploy", live_routes),
        ("CLEARED_TO_DEPLOY", True),
    ))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")

    print("parent            :", expected_parent, "STILL CURRENT")
    print("live sitemap      :", sitemap_sha, "(%d routes)" % len(live_routes))
    print("record sitemap    :", newest["sitemap_sha256"], "AGREES")
    print("lexington / toledo:", doc["parent"]["lexington_live"], "/", doc["parent"]["toledo_live"])
    print("staged artifact   :", staged_digest)
    print("authorized        :", auth["bundle_sha256"])
    print("IDENTICAL         :", staged_digest == auth["bundle_sha256"], "| files:", len(hashes))
    print("STALE_PARENT      : NO")
    print("CLEARED_TO_DEPLOY : YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
