"""PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032 -- authorize, then record.

    python -m scripts.pettripfinder.detroit_ann_arbor_launch_authorization_032 authorize --candidate <dir>
    python -m scripts.pettripfinder.detroit_ann_arbor_launch_authorization_032 record --deploy-id <id> ...

TWO STEPS, DELIBERATELY SEPARATE
--------------------------------
``authorize`` rewrites the global deployment manifest to describe the candidate,
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

THIS LAUNCH BINDS THE PACKET DIGEST, AND THAT IS UNUSUAL
--------------------------------------------------------
Every launch before this one had to explain why the prepared packet's digest
could NOT be the deployed one: a promotion packet pins the PRE-FLIP bundle, in
which the joining market contributes nothing, so a launch necessarily produces a
different artifact. Detroit is the exception. PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031
wrote the participation row in its admitting state and assembled the POST-flip
candidate, so the packet already pins the bundle a launch deploys.

What the founder signature changed was the participation record's own bytes --
sha256 057ead0385db06bb -> 9c39ba4a089440e1 -- and the order was explicit that
the bundle must not be assumed to survive that. It was reassembled from the
signed, committed source in a clean worktree and matched the packet on both
digests, so PACKET == AUTHORIZED holds here on equality that was proved rather
than asserted. ``_assert_packet_equality`` below re-checks it at authorization
time and refuses on any difference.
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

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032"
PREP_ORDER = "PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031"
MARKET = "detroit-ann-arbor-mi"
AUTHORIZATION_ID = "ptf-auth-detroit-032-92b39c81c319"
TARGET_SITE = "pettripfinder-prod"
TARGET_DOMAIN = "https://pettripfinder.com"
AUTHORIZED_BY = "founder"
PINS = _DASH / "tests" / "pettripfinder" / "pins"
PACKET = (_DASH / "launch_packages" / "pettripfinder"
          / "detroit_ann_arbor_launch_authorization_packet_031.json")

#: The founder's governing source state, carried from the committed packet.
GOVERNING = {"census": 247, "pet_friendly": 121, "verified_no_pets": 81,
             "resolved": 202, "unresolved": 45}

#: Registered nowhere and deliberately absent from this launch.
MUST_NOT_LAUNCH = ("fort-wayne-in", "lexington-ky")

AUTHORIZATION_SOURCE = (
    "Founder work order %s: \"THIS WORK ORDER IS EXPLICIT FOUNDER AUTHORIZATION "
    "TO LAUNCH AND DEPLOY DETROIT / ANN ARBOR USING ONLY THE EXACT VERIFIED "
    "CANDIDATE PREPARED BY %s\" and \"YES -- authorize Detroit / Ann Arbor "
    "participation\". The order required the bundle and sitemap digests to equal "
    "the committed packet exactly after the participation record was signed, and "
    "forbade repinning if they moved. They did not move: the record's own sha256 "
    "changed from 057ead0385db06bb to 9c39ba4a089440e1 while the reassembled "
    "bundle reproduced 92b39c81c31988a1 and the sitemap ad71bdfaef134ccd, both "
    "byte-identical to the packet. The order named the packet at "
    "launch_packages/pettripfinder/markets/reports/, where no such file exists; "
    "the committed packet one directory up was read instead and every binding "
    "value below comes from it." % (WORK_ORDER, PREP_ORDER))

NOTE = (
    "Detroit / Ann Arbor joins as the TWELFTH market at 121 published profiles "
    "and 81 verified-no-pets exclusions over a 247-identity census. Every "
    "previously live market moves by exactly zero and no route is removed. "
    "Founder rulings carried in unchanged: the Troy EVEN Hotel and Hotel Indigo "
    "remain DISTINCT published identities on the shared 575 W Big Beaver campus, "
    "the only shared premise among the 121; DoubleTree Ann Arbor North stays "
    "published; Royal Park and The Siren keep their partial-policy publications; "
    "Westin Book Cadillac and Roberts Riverwalk remain HELD and publish nothing. "
    "This launch resolves none of those holds. Fort Wayne and Lexington are not "
    "registered for launch and are absent from this bundle.")


def _load(path) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _live() -> dict:
    return _load(PINS / "deployment_state.json")["live"]


def _is_ancestor(older: str, newer: str) -> bool:
    """True when ``older`` is reachable from ``newer``. Read from git, not typed."""
    import subprocess
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=str(_DASH), capture_output=True).returncode == 0


def _assert_packet_equality(bundle) -> OrderedDict:
    """PACKET == candidate, on full values. The order forbids prefix matches.

    ``source_commit`` is the one binding value that MUST differ, and requiring
    equality would be requiring the impossible: the order instructs that the
    signed participation state be committed before reassembly, so the authorized
    source is necessarily a commit the packet could not have named. What is
    checked instead is stronger than equality would be -- the authorized commit
    must be a DESCENDANT of the one the packet pinned, so the artifact is built
    from the packet's source plus the founder's signature and nothing else, and
    the ARTIFACT digests must be byte-identical across that advance. That the
    bundle is unchanged is the empirical proof that the signature touched no
    assembler input, which is the fact the order refused to let anyone assume.
    """
    packet = _load(PACKET)
    binding = packet["binding"]
    checks = OrderedDict([
        ("bundle_sha256", (binding["bundle_sha256"], bundle["bundle_sha256"])),
        ("sitemap_sha256", (binding["sitemap_sha256"], bundle["sitemap_sha256"])),
        ("sitemap_route_count", (binding["sitemap_route_count"],
                                 bundle["sitemap_route_count"])),
        ("total_html_pages", (binding["total_html_pages"],
                              bundle["total_html_pages"])),
        ("total_files", (binding["total_files"], bundle["total_files"])),
        ("total_profiles",
         (binding["total_profiles"],
          sum(m["published_profiles"] for m in bundle["participating_markets"]))),
    ])
    problems = ["%s: packet %r != candidate %r" % (name, want, got)
                for name, (want, got) in checks.items() if want != got]

    authorized_commit = bundle["generated_from_commit"]
    packet_commit = binding["source_commit"]
    if authorized_commit == packet_commit:
        problems.append(
            "the authorized source is the packet's own commit; the signed "
            "participation state was never committed")
    elif not _is_ancestor(packet_commit, authorized_commit):
        problems.append(
            "the authorized source %s does not descend from the packet's %s"
            % (authorized_commit, packet_commit))
    # The baseline the packet was prepared against must still be production.
    live = _live()
    baseline = packet["production_baseline"]
    for field, pinned in (("deployment_id", live["deploy_id"]),
                          ("bundle_sha256", live["bundle_sha256"]),
                          ("sitemap_sha256", live["sitemap_sha256"]),
                          ("published_profiles", live["total_profiles"]),
                          ("sitemap_routes", live["sitemap_route_count"])):
        if baseline[field] != pinned:
            problems.append("production moved: packet baseline %s %r != live %r"
                            % (field, baseline[field], pinned))
    if packet["rollback_target"]["deployment_id"] != live["deploy_id"]:
        problems.append("rollback target is not the live deployment")
    if problems:
        raise SystemExit("%s: PACKET equality FAILED\n  %s"
                         % (WORK_ORDER, "\n  ".join(problems)))
    matched = OrderedDict((name, want) for name, (want, _got) in checks.items())
    matched["source_commit_advanced"] = "%s -> %s" % (packet_commit,
                                                      authorized_commit)
    return matched


def _assert_expected_delta(manifest) -> OrderedDict:
    """Detroit joins at 121; every previously live market moves by exactly zero."""
    live = _live()
    counts = {row["market_id"]: row["published_profiles"]
              for row in manifest["participating_markets"]}
    problems = []

    if counts.get(MARKET) != GOVERNING["pet_friendly"]:
        problems.append("detroit publishes %s, expected %d"
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
    for forbidden in MUST_NOT_LAUNCH:
        if forbidden in counts:
            problems.append("%s must not launch and is in the candidate" % forbidden)

    state = _load(PINS / "market_state.json")["markets"][MARKET]
    for key, want in (("census", GOVERNING["census"]),
                      ("profiles", GOVERNING["pet_friendly"]),
                      ("verified_no_pets", GOVERNING["verified_no_pets"]),
                      ("resolved", GOVERNING["resolved"]),
                      ("unresolved", GOVERNING["unresolved"])):
        if state[key] != want:
            problems.append("detroit source %s is %s, expected %d"
                            % (key, state[key], want))

    if LP.launch_status(MARKET) != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH:
        problems.append("the participation record does not authorize detroit")
    decision = LP.load_participation()["decision"]
    if decision["decided_by"] != AUTHORIZED_BY:
        problems.append("the participation decision is not the founder's")
    if decision["work_order"] != WORK_ORDER:
        problems.append("the participation decision names %s, expected %s"
                        % (decision["work_order"], WORK_ORDER))

    if problems:
        raise SystemExit("%s: expected-delta check FAILED\n  %s"
                         % (WORK_ORDER, "\n  ".join(problems)))
    return OrderedDict([
        ("markets", "%d -> %d" % (len(live["profile_counts"]), len(counts))),
        ("total_profiles", "%d -> %d" % (live["total_profiles"],
                                         sum(counts.values()))),
        ("sitemap_routes", "%d -> %d" % (live["sitemap_route_count"],
                                         manifest["sitemap_route_count"])),
        ("detroit", "0 -> %d" % counts[MARKET]),
        ("every_other_market_delta", deltas),
        ("fort_wayne_and_lexington_absent",
         all(m not in counts for m in MUST_NOT_LAUNCH)),
    ])


def authorize(candidate: Path) -> int:
    bundle = _load(candidate / "global_bundle_manifest.json")
    live = _live()

    if not bundle["all_gates_pass"]:
        raise SystemExit("%s: the candidate does not pass its own gates" % WORK_ORDER)

    packet_values = _assert_packet_equality(bundle)
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
        note=NOTE)

    problems = DA.verify_authorization(auth, manifest)
    if problems:
        raise SystemExit("%s: PREPARED authorization has %d problem(s)\n  %s"
                         % (WORK_ORDER, len(problems), "\n  ".join(problems)))

    auth = DA.transition(
        auth, DA.AUTHORIZED,
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
    print("PACKET == AUTHORIZED on:", ", ".join(packet_values))
    print("bundle_sha256    :", auth["bundle_sha256"])
    print("sitemap_sha256   :", auth["sitemap_sha256"])
    print("source_commit    :", auth["source_commit"])
    print("rollback_target  :", auth["rollback_target"])
    print("markets          :", delta["markets"])
    print("total_profiles   :", delta["total_profiles"])
    print("sitemap_routes   :", delta["sitemap_routes"])
    print("detroit          :", delta["detroit"])
    print("other deltas     :", set(delta["every_other_market_delta"].values()))
    print("fw/lex absent    :", delta["fort_wayne_and_lexington_absent"])
    print("superseded       :", superseded)
    print("verifier problems: 0")
    print("written          :", path.relative_to(_DASH).as_posix())
    return 0


def record(deploy_id: str, candidate: Path, live_results: Path,
           deployed_at: str, command: str, record_id: str) -> int:
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
        deployment_record_id=record_id,
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
    r.add_argument("--record-id", required=True)
    args = ap.parse_args(argv)
    if args.command == "authorize":
        return authorize(Path(args.candidate))
    return record(args.deploy_id, Path(args.candidate), Path(args.live_results),
                  args.deployed_at, args.command, args.record_id)


if __name__ == "__main__":
    raise SystemExit(main())
