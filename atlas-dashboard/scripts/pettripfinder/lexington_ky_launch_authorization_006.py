"""PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 -- authorize, then record.

    python -m scripts.pettripfinder.lexington_ky_launch_authorization_006 authorize --candidate <dir>
    python -m scripts.pettripfinder.lexington_ky_launch_authorization_006 record --deploy-id <id> ...

TWO STEPS, DELIBERATELY SEPARATE

``authorize`` rewrites the global deployment manifest to describe the candidate,
binds a PREPARED authorization to it, moves it to AUTHORIZED and refuses if any
verifier reports a problem. ``record`` runs only AFTER a successful deploy and
moves AUTHORIZED -> DEPLOYED. Nothing here deploys; the deploy is a separate,
explicit command.

The manifest is rewritten BEFORE the authorization is built, because
``deployability_problems`` compares the authorization against the COMMITTED
manifest and never reaches zero while that manifest still describes the previous
bundle. Dayton learned that the expensive way.

WHAT THIS LAUNCH INHERITS FROM A HALT

PTF-LEXINGTON-KY-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-004 was stopped by the
founder because the sealed package digest it named could not be reproduced from
the committed tree. PTF-LEXINGTON-KY-FRESH-PACKAGE-REAUTHORIZATION-PREP-005
sealed a reproducible package, committed it under the market so its seal is
re-validated rather than re-derived, and re-proved the candidate. This order
binds the FRESH digests and never the retired ones, which is why
``ASSERT_FRESH`` below names both: the value that must appear and the value that
must not.

EVERY VALUE IS DERIVED

The bundle digest, sitemap digest, counts, control-file hashes and per-market
release-contract hashes all come from the assembled candidate's own manifest.
The rollback target and production baseline come from the committed deployment
pin. Nothing is typed. The Cincinnati launch order's own inline bundle SHA was
wrong in five characters and its rollback target was one deploy stale, which
would have un-deployed Louisville.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

_DASH = Path(__file__).resolve().parents[2]
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402
from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import launch_participation as LP       # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP     # noqa: E402

WORK_ORDER = "PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
MARKET = "lexington-ky"
AUTHORIZATION_ID = "ptf-auth-lexington-006-67fe8617b79f"
RECORD_ID_PREFIX = "ptf-deploy-lexington-006"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"
AUTHORIZED_BY = "founder"
PINS = _DASH / "tests" / "pettripfinder" / "pins"

#: The founder's governing source state, carried from the fresh packet.
GOVERNING = {"census": 57, "pet_friendly": 20, "verified_no_pets": 10, "held_rows": 15}

#: The digests the founder named. FRESH is what must appear; RETIRED is the 004
#: package digest that must never be bound again, and is checked for by name so
#: a copy-paste from the dead packet cannot pass silently.
ASSERT_FRESH = OrderedDict((
    ("sealed_package_digest",
     "sha256:a29e4a966e1b68b918c1b0f34db21ff5525691fc5e7581fb58190cc1031310b0"),
    ("final_candidate_digest",
     "67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78"),
    ("candidate_sitemap_digest",
     "dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611"),
    ("intended_delta_digest",
     "sha256:82e57491638b8fc471e691ba6ddbc376e11d371b1599740361af10c7fd6a76db"),
    ("parent_release_digest",
     "895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0"),
))
RETIRED_PACKAGE_DIGEST = \
    "sha256:e5d26fd63bb2d2e2d3d632134cc40cd832d1a4d4c5e1b82f003aa58dc52c5380"

AUTHORIZATION_SOURCE = (
    "Founder work order %s: \"I explicitly AUTHORIZE the CURRENT FRESH REPRODUCIBLE Lexington "
    "candidate produced by PTF-LEXINGTON-KY-FRESH-PACKAGE-REAUTHORIZATION-PREP-005\", with the "
    "instruction to read every full digest mechanically from the CURRENT committed fresh packet "
    "and to use no digest from an older Lexington authorization packet. This authorization "
    "applies to lexington-ky alone. It follows the founder's own HALT of "
    "PTF-LEXINGTON-KY-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-004, which named a sealed package "
    "digest that could not be reproduced; that digest is recorded here as RETIRED and is "
    "asserted absent rather than merely unused." % WORK_ORDER)


def _load(path) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _live() -> dict:
    return _load(PINS / "deployment_state.json")["live"]


def _packet() -> dict:
    return _load(_DASH / "launch_packages" / "pettripfinder" / "markets" / "reports"
                 / "lexington_deployment_authorization_006_PROPOSED.json")


def _assert_fresh_digests(bundle) -> OrderedDict:
    """The founder said: read the FRESH packet, never the old one. Checked."""
    packet = _packet()
    bound = packet["the_digests_this_authorization_binds"]
    package = SMP.read_sealed(SMP.list_packages(MARKET)[-1])
    problems = []

    for key, want in ASSERT_FRESH.items():
        got = bound.get(key)
        if got != want:
            problems.append("packet %s is %s, the founder named %s" % (key, got, want))
    if package["package_digest"] != ASSERT_FRESH["sealed_package_digest"]:
        problems.append("the committed package is %s, not the authorized %s"
                        % (package["package_digest"], ASSERT_FRESH["sealed_package_digest"]))
    if RETIRED_PACKAGE_DIGEST in bound.values():
        problems.append("the RETIRED 004 package digest appears in the bound digests")
    if bundle["bundle_sha256"] != ASSERT_FRESH["final_candidate_digest"]:
        problems.append("the candidate is %s, not the authorized %s"
                        % (bundle["bundle_sha256"], ASSERT_FRESH["final_candidate_digest"]))
    if bundle["sitemap_sha256"] != ASSERT_FRESH["candidate_sitemap_digest"]:
        problems.append("the candidate sitemap is %s, not the authorized %s"
                        % (bundle["sitemap_sha256"], ASSERT_FRESH["candidate_sitemap_digest"]))
    if problems:
        raise SystemExit("%s: FRESH-DIGEST check FAILED\n  %s"
                         % (WORK_ORDER, "\n  ".join(problems)))
    return OrderedDict((
        ("sealed_package_digest", package["package_digest"]),
        ("sealed_package_id", package["package_id"]),
        ("retired_004_digest_absent", True),
        ("intended_delta_digest", bound["intended_delta_digest"]),
        ("build_input_key", bound["build_input_key"]),
    ))


def _assert_expected_delta(manifest) -> OrderedDict:
    """Lexington joins at 20; every previously live market moves by exactly zero."""
    live = _live()
    counts = {row["market_id"]: row["published_profiles"]
              for row in manifest["participating_markets"]}
    problems = []

    if counts.get(MARKET) != GOVERNING["pet_friendly"]:
        problems.append("lexington publishes %s, expected %d"
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
    for other in ("nashville-tn", "chattanooga-tn", "fort-wayne-in", "detroit-ann-arbor-mi"):
        if other in counts:
            problems.append("%s must not participate" % other)

    state = _load(PINS / "market_state.json")["markets"][MARKET]
    for key, want in (("census", GOVERNING["census"]),
                      ("profiles", GOVERNING["pet_friendly"]),
                      ("verified_no_pets", GOVERNING["verified_no_pets"])):
        if state[key] != want:
            problems.append("lexington source %s is %s, expected %d"
                            % (key, state[key], want))

    holds = _load(_DASH / "launch_packages" / "pettripfinder"
                  / "lexington_ky_identity_holds_003.json")
    if holds["count"] != GOVERNING["held_rows"]:
        problems.append("held rows moved: %d, expected %d"
                        % (holds["count"], GOVERNING["held_rows"]))

    if problems:
        raise SystemExit("%s: expected-delta check FAILED\n  %s"
                         % (WORK_ORDER, "\n  ".join(problems)))
    return OrderedDict((
        ("markets", "%d -> %d" % (len(live["profile_counts"]), len(counts))),
        ("total_profiles", "%d -> %d" % (live["total_profiles"], sum(counts.values()))),
        ("sitemap_routes", "%d -> %d" % (live["sitemap_route_count"],
                                         manifest["sitemap_route_count"])),
        ("lexington", "0 -> %d" % counts[MARKET]),
        ("every_other_market_delta", deltas),
        ("held_rows_unchanged", holds["count"]),
        ("detroit_still_excluded",
         LP.launch_status("detroit-ann-arbor-mi") != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
    ))


def authorize(candidate: Path) -> int:
    bundle = _load(candidate / "global_bundle_manifest.json")
    live = _live()

    if not bundle["all_gates_pass"]:
        raise SystemExit("%s: the candidate does not pass its own gates" % WORK_ORDER)

    fresh = _assert_fresh_digests(bundle)
    delta = _assert_expected_delta(bundle)

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
        note=("Lexington joins as the TWELFTH market at %d published profiles over a "
              "57-identity registered census. Every previously live market moves by exactly "
              "zero. This is the first market to cross from the pre-redesign factory into the "
              "ATLAS-THROUGHPUT release lane, and it launches on the FRESH reproducible package "
              "%s -- not the 004 digest the founder halted on, which is asserted absent. The "
              "fifteen rows the modern gates hold are unresolved by this launch and none is "
              "promoted." % (GOVERNING["pet_friendly"], fresh["sealed_package_digest"])))

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
    print("sealed package   :", fresh["sealed_package_digest"])
    print("retired absent   :", fresh["retired_004_digest_absent"])
    print("intended delta   :", fresh["intended_delta_digest"])
    print("source_commit    :", auth["source_commit"])
    print("rollback_target  :", auth["rollback_target"])
    print("markets          :", delta["markets"])
    print("total_profiles   :", delta["total_profiles"])
    print("sitemap_routes   :", delta["sitemap_routes"])
    print("lexington        :", delta["lexington"])
    print("other deltas     :", set(delta["every_other_market_delta"].values()))
    print("held rows        :", delta["held_rows_unchanged"], "(unchanged)")
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
    bundle = _load(candidate / "global_bundle_manifest.json")

    auth = DA.transition(
        auth, DA.DEPLOYED,
        note="deployed to %s as %s by %s" % (TARGET_DOMAIN, deploy_id, WORK_ORDER))
    DA.write_authorization(auth)

    verification = _load(live_results)
    rec = DA.build_deployment_record(
        auth,
        deployment_record_id="%s-%s" % (RECORD_ID_PREFIX, deploy_id),
        deployment_id=deploy_id,
        previous_deployment_id=live["deploy_id"],
        deployed_at=deployed_at,
        deployer=OrderedDict((("work_order", WORK_ORDER),
                              ("authorized_by", AUTHORIZED_BY),
                              ("executed_by", "claude-code"))),
        production_url=TARGET_DOMAIN,
        deployed_directory=str(candidate / "site"),
        command=command,
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
