"""PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003 -- authorize, then record.

    python -m scripts.pettripfinder.toledo_oh_launch_authorization_003 authorize --candidate <dir>
    python -m scripts.pettripfinder.toledo_oh_launch_authorization_003 record --deploy-id <id>

TWO STEPS, DELIBERATELY SEPARATE
--------------------------------
``authorize`` updates the global deployment manifest to describe the candidate,
binds a PREPARED authorization to it, moves it to AUTHORIZED, and refuses if any
verifier reports a problem. ``record`` runs only AFTER a successful deploy and
moves AUTHORIZED -> DEPLOYED, writing the deployment record. Nothing here
deploys; the deploy is a separate, explicit command.

The manifest is rewritten BEFORE the authorization is built, because
``deployability_problems`` compares the authorization against the committed
manifest and never reaches zero if the manifest still describes the previous
bundle. Dayton learned that the expensive way.

EVERY VALUE IS DERIVED
----------------------
The bundle digest, sitemap digest, counts, control-file hashes and per-market
release-contract hashes all come from the assembled candidate's own manifest.
The rollback target and production baseline come from the committed deployment
pin. Nothing is typed. The Cincinnati launch order's own inline bundle SHA was
wrong in five characters and its rollback target was one deploy stale, which
would have un-deployed Louisville.

WHY THE PROMOTION PACKET'S DIGEST IS NOT BOUND HERE
---------------------------------------------------
The promotion packet pins the PRE-FLIP bundle, in which Toledo contributes
nothing. A launch cannot deploy it. The founder was shown both digests with the
full post-flip numbers and bound this authorization to the reassembled
candidate. What IS carried from the packet, and asserted below, is the source
state: 54 census, 17 published, 9 verified-no-pets, and every live market's
profile count unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

_DASH = Path(__file__).resolve().parents[2]
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402
from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import launch_participation as LP       # noqa: E402

WORK_ORDER = "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"
MARKET = "toledo-oh"
AUTHORIZATION_ID = "ptf-auth-toledo-003-895248738c79"
RECORD_ID = "ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"
AUTHORIZED_BY = "founder"
PINS = _DASH / "tests" / "pettripfinder" / "pins"

#: The founder's governing source state, carried from the promotion packet.
GOVERNING = {"census": 54, "pet_friendly": 17, "verified_no_pets": 9}

AUTHORIZATION_SOURCE = (
    "Founder work order %s: \"THIS WORK ORDER IS EXPLICIT FOUNDER AUTHORIZATION "
    "TO LAUNCH AND DEPLOY TOLEDO\" and \"YES -- authorize Toledo participation\". "
    "The order also required PACKET == AUTHORIZED on bundle_sha256, which cannot "
    "hold for a launch: the promotion packet pins the PRE-FLIP bundle in which "
    "Toledo contributes nothing. That conflict was surfaced rather than "
    "reconciled, both digests and the full post-flip numbers were put to the "
    "founder, and the founder bound this authorization to the reassembled "
    "candidate." % WORK_ORDER)


def _load(path) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _live() -> dict:
    return _load(PINS / "deployment_state.json")["live"]


def _assert_expected_delta(manifest) -> OrderedDict:
    """Toledo joins at 17; every previously live market moves by exactly zero."""
    live = _live()
    counts = {row["market_id"]: row["published_profiles"]
              for row in manifest["participating_markets"]}
    problems = []

    if counts.get(MARKET) != GOVERNING["pet_friendly"]:
        problems.append("toledo publishes %s, expected %d"
                        % (counts.get(MARKET), GOVERNING["pet_friendly"]))
    deltas = OrderedDict()
    for market, was in sorted(live["profile_counts"].items()):
        now = counts.get(market)
        if now is None:
            problems.append("live market %s vanished from the candidate" % market)
            continue
        deltas[market] = now - was
        if now != was:
            problems.append("live market %s moved %d -> %d" % (market, was, now))
    gained = sorted(set(counts) - set(live["profile_counts"]))
    if gained != [MARKET]:
        problems.append("exactly one market may join; gained %s" % gained)
    if len(counts) != len(live["profile_counts"]) + 1:
        problems.append("market count must grow by exactly one")

    state = _load(PINS / "market_state.json")["markets"][MARKET]
    for key, want in (("census", GOVERNING["census"]),
                      ("profiles", GOVERNING["pet_friendly"]),
                      ("verified_no_pets", GOVERNING["verified_no_pets"])):
        if state[key] != want:
            problems.append("toledo source %s is %s, expected %d"
                            % (key, state[key], want))

    if problems:
        raise SystemExit("%s: expected-delta check FAILED\n  %s"
                         % (WORK_ORDER, "\n  ".join(problems)))
    return OrderedDict([
        ("markets", "%d -> %d" % (len(live["profile_counts"]), len(counts))),
        ("total_profiles", "%d -> %d" % (live["total_profiles"],
                                         sum(counts.values()))),
        ("sitemap_routes", "%d -> %d" % (live["sitemap_route_count"],
                                         manifest["sitemap_route_count"])),
        ("toledo", "0 -> %d" % counts[MARKET]),
        ("every_other_market_delta", deltas),
        ("detroit_still_excluded",
         LP.launch_status("detroit-ann-arbor-mi")
         != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
    ])


def authorize(candidate: Path) -> int:
    bundle = _load(candidate / "global_bundle_manifest.json")
    live = _live()

    if not bundle["all_gates_pass"]:
        raise SystemExit("%s: the candidate does not pass its own gates" % WORK_ORDER)

    delta = _assert_expected_delta(bundle)

    # The manifest FIRST: deployability_problems reads the committed manifest.
    manifest = GD.write_manifest(bundle)
    if manifest["bundle_sha256"] != bundle["bundle_sha256"]:
        raise SystemExit("%s: the manifest does not describe the candidate" % WORK_ORDER)

    auth = DA.build_authorization(
        manifest,
        authorization_id=AUTHORIZATION_ID,
        work_order=WORK_ORDER,
        authorized_by=AUTHORIZED_BY,
        source_commit=bundle["generated_from_commit"],
        rollback_target=live["deploy_id"],
        target_site=TARGET_SITE,
        target_domain=TARGET_DOMAIN,
        authorization_source=AUTHORIZATION_SOURCE,
        note=("Toledo joins as the eleventh market at %d published profiles over a "
              "54-identity census built from zero. Every previously live market "
              "moves by exactly zero. Founder ruling TOLEDO-R3 keeps both reads at "
              "10667 / 10667B Fremont Pike held, and this launch does not resolve "
              "that split." % GOVERNING["pet_friendly"]))

    problems = DA.verify_authorization(auth, manifest)
    if problems:
        raise SystemExit("%s: PREPARED authorization has %d problem(s)\n  %s"
                         % (WORK_ORDER, len(problems), "\n  ".join(problems)))

    auth = DA.transition(auth, DA.AUTHORIZED,
                         note="founder authorized launch and deployment in %s" % WORK_ORDER)
    problems = DA.verify_authorization(auth, manifest)
    deployability = DA.deployability_problems(auth)
    bundle_problems = DA.verify_bundle_directory(auth, candidate / "site")
    if problems or deployability or bundle_problems:
        raise SystemExit(
            "%s: AUTHORIZED verification FAILED\n  verify: %s\n  deployability: %s"
            "\n  bundle: %s" % (WORK_ORDER, problems, deployability, bundle_problems))

    path = DA.write_authorization(auth)
    superseded = DA.supersede_earlier(auth)
    GD.write_manifest(bundle)
    manifest_doc = DA.authorize_manifest(auth)
    GD.MANIFEST_PATH.write_text(
        json.dumps(manifest_doc, indent=1, ensure_ascii=False) + chr(10),
        encoding="utf-8", newline="\n")
    manifest_problems = DA.manifest_authorization_problems(manifest_doc)
    if manifest_problems:
        raise SystemExit("%s: manifest authorization problems: %s"
                         % (WORK_ORDER, manifest_problems))

    print("authorization    :", AUTHORIZATION_ID)
    print("status           :", auth["authorization_status"])
    print("bundle_sha256    :", auth["bundle_sha256"])
    print("sitemap_sha256   :", auth["sitemap_sha256"])
    print("source_commit    :", auth["source_commit"])
    print("rollback_target  :", auth["rollback_target"])
    print("markets          :", delta["markets"])
    print("total_profiles   :", delta["total_profiles"])
    print("sitemap_routes   :", delta["sitemap_routes"])
    print("toledo           :", delta["toledo"])
    print("other deltas     :", set(delta["every_other_market_delta"].values()))
    print("detroit excluded :", delta["detroit_still_excluded"])
    print("superseded       :", superseded)
    print("verifier problems: 0")
    print("written          :", path.relative_to(_DASH).as_posix())
    return 0


def record(deploy_id: str, candidate: Path, live_results: Path,
           deployed_at: str, command: str) -> int:
    """AUTHORIZED -> DEPLOYED, then the durable record. Runs only after a deploy."""
    auth = DA.load_authorization(AUTHORIZATION_ID)
    if auth["authorization_status"] != DA.AUTHORIZED:
        raise SystemExit("%s: authorization is %s, expected AUTHORIZED"
                         % (WORK_ORDER, auth["authorization_status"]))
    live = _live()
    manifest = GD.load_manifest()
    bundle = _load(candidate / "global_bundle_manifest.json")

    auth = DA.transition(
        auth, DA.DEPLOYED,
        note="deployed to %s as %s by %s" % (TARGET_DOMAIN, deploy_id, WORK_ORDER))
    DA.write_authorization(auth)

    verification = _load(live_results)
    rec = DA.build_deployment_record(
        auth,
        deployment_record_id=RECORD_ID,
        deployment_id=deploy_id,
        previous_deployment_id=live["deploy_id"],
        deployed_at=deployed_at,
        deployer=OrderedDict([("work_order", WORK_ORDER),
                              ("authorized_by", AUTHORIZED_BY),
                              ("executed_by", "claude-code")]),
        production_url=TARGET_DOMAIN,
        deployed_directory=str(candidate / "site"),
        command=command,
        # The REAL gate outcomes from the candidate that was uploaded, not a
        # list of gate names assumed to have passed.
        global_gate_results=OrderedDict(
            (gid, bool(res.get("pass")))
            for gid, res in sorted((bundle.get("gates") or {}).items())),
        live_verification_results=OrderedDict(verification),
        final_status=DA.DEPLOYED,
        rollback_used=False,
        exit_status=0)

    problems = DA.verify_record(rec, auth)
    if problems:
        raise SystemExit("%s: deployment record has %d problem(s)\n  %s"
                         % (WORK_ORDER, len(problems), "\n  ".join(problems)))
    path = DA.write_record(rec)

    print("authorization    :", auth["authorization_status"])
    print("record           :", path.relative_to(_DASH).as_posix())
    print("final_status     :", rec["final_status"])
    print("new deploy       :", deploy_id)
    print("previous deploy  :", live["deploy_id"])
    print("rollback target  :", rec["rollback_target"])
    print("verifier problems: 0")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    a = sub.add_parser("authorize")
    a.add_argument("--candidate", required=True)
    r = sub.add_parser("record")
    r.add_argument("--deploy-id", required=True)
    r.add_argument("--candidate", required=True)
    r.add_argument("--live-results", required=True)
    r.add_argument("--deployed-at", required=True)
    r.add_argument("--command", required=True)
    args = ap.parse_args(argv)
    if args.command == "authorize":
        return authorize(Path(args.candidate))
    return record(args.deploy_id, Path(args.candidate), Path(args.live_results),
                  args.deployed_at, args.command)


if __name__ == "__main__":
    raise SystemExit(main())
