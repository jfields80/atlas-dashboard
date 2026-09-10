"""PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 -- the founder's decision.

Records the founder's launch decision for nashville-tn and writes the real
deployment authorization bound to the exact digests the current committed
artifacts state. Every digest is READ from an artifact; none is typed, and none
comes from terminal prose.

WHAT THIS WRITES

  deploy/netlify/launch_participation.json          the nashville-tn row flips
  deploy/netlify/global_deployment_manifest.json    the manifest of the AUTHORIZED bundle
  deploy/netlify/deployment_authorizations/<id>.json  the authorization itself

THE ORDER MATTERS AND IS NOT ARBITRARY

The participation record is part of the bundle: the assembler hashes it into the
manifest, and ``verify_authorization`` re-checks the committed file against the
hash the authorization binds. So the flip is written FIRST, then the manifest
that was built from a tree carrying that flip, then the authorization built from
that manifest. Writing them in any other order produces an authorization that
refuses its own repository.

The manifest is written BEFORE the deploy for the same reason
PTF-DAYTON-OH-DEPLOYMENT-AUTHORIZATION-003 learned it: a manifest that still
describes the previous bundle leaves ``deployability_problems`` non-empty
forever, and no amount of deploying fixes it.

WHAT IT REFUSES

A bundle whose digest is not the one the founder authorized. A participation
hash that does not match what the bundle was built with. Any market other than
nashville-tn moving from its recorded status. It raises rather than writing a
partial authorization.

NOTHING HERE DEPLOYS. It writes the authorization a deploy will later consume.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
_REPO = _DASH.parent
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
MARKET_ID = "nashville-tn"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
DEPLOY = _DASH / "deploy" / "netlify"
PARTICIPATION = DEPLOY / "launch_participation.json"
PACKET = REPORTS / "nashville_deployment_authorization_004_PROPOSED.json"

TARGET_SITE = "pettripfinder-prod"
#: The base URL the manifest itself states, not the bare host.
#: verify_authorization compares this against the artifact and refuses a mismatch.
TARGET_DOMAIN = "https://pettripfinder.com"

AUTHORIZATION_SOURCE = (
    "Founder work order " + WORK_ORDER + ': "I explicitly AUTHORIZE the CURRENT committed and '
    'reproducible Nashville production candidate produced by the completed Nashville recovery '
    'and final regression-closure orders", with the instruction that the authorization applies '
    "ONLY to nashville-tn, that no older Nashville candidate, package, packet or abbreviated "
    "digest from terminal prose may be used, and that every full digest be read mechanically "
    "from the current committed artifacts. Every digest in this record was read that way.")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _write(path, doc):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=str(_REPO),
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def _flip(participation, bound, before):
    """Move exactly this market to FOUNDER_AUTHORIZED_FOR_LAUNCH, and no other.

    The `before` snapshot is what makes "and no other" checkable rather than
    intended: every market's status is compared afterwards, so a decision that
    quietly admitted a second market would raise here instead of shipping.
    """
    from scripts.pettripfinder import launch_participation as LP
    moved = []
    for row in participation["markets"]:
        if row["market_id"] != MARKET_ID:
            continue
        if row["launch_status"] != LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH:
            raise SystemExit("REFUSING: %s is %r, not the source-ready state a founder decision "
                             "moves from" % (MARKET_ID, row["launch_status"]))
        row["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        row["founder_decision"] = OrderedDict((
            ("work_order", WORK_ORDER),
            ("decided_by", "founder"),
            ("authorized_candidate_digest", bound["final_candidate_digest"]),
            ("authorized_package_digest", bound["sealed_package_digest"]),
        ))
        moved.append(MARKET_ID)
    if moved != [MARKET_ID]:
        raise SystemExit("REFUSING: expected to move exactly %s, moved %s" % (MARKET_ID, moved))
    after = {r["market_id"]: r["launch_status"] for r in participation["markets"]}
    changed = sorted(m for m in after if before.get(m) != after[m])
    if changed != [MARKET_ID]:
        raise SystemExit("REFUSING: %d market(s) changed status, expected only %s: %s"
                         % (len(changed), MARKET_ID, changed))
    return changed


def participation_decision(bundle):
    """The founder's decision block, stating what moved and what did not."""
    counts = OrderedDict((row["market_id"], row["published_profiles"])
                         for row in bundle["participating_markets"])
    withheld = [row["market_id"] for row in bundle["markets_registered_but_excluded"]]
    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("decided_by", "founder"),
        ("decided_on", datetime.now(timezone.utc).date().isoformat()),
        ("reason",
         "Founder authorizes Nashville to participate in the next production assembly, joining "
         "as the THIRTEENTH market with %d pet-friendly profiles and %d verified-no-pets "
         "refusals over a 180-identity registered census. Every other market's decision is "
         "unchanged: %s remains NOT authorized, and chattanooga-tn and fort-wayne-in are not "
         "registered markets and are admitted by no lever here. Nashville reaches this decision "
         "having been registered at EIGHT published profiles and recovered to %d: "
         "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 re-fetched and re-hashed the 84 first-party "
         "pages whose legacy capture recorded a byte length and no document hash, and every one "
         "of the current reads agreed with the shadow's classification, so no policy changed -- "
         "only the proof. Four rows remain held and none is promoted by this launch. The founder "
         "was shown the current digests and this decision is bound to them: package "
         "%s and candidate %s at %d markets / %d profiles / %d routes."
         % (counts.get(MARKET_ID, 0),
            _load(PKG / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json")["count"],
            ", ".join(withheld) or "no registered market",
            counts.get(MARKET_ID, 0),
            _load(PACKET)["the_four_digests_this_authorization_binds"]["sealed_package_digest"],
            bundle["bundle_sha256"], len(counts), sum(counts.values()),
            bundle["sitemap_route_count"])),
        ("markets_moved", [MARKET_ID]),
        ("markets_unchanged", sorted(m for m in counts if m != MARKET_ID)),
        ("registered_but_still_withheld", withheld),
        ("held_rows_not_promoted",
         _load(PKG / "nashville_tn_identity_holds_002.json")["count"]),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True,
                    help="the assembled candidate directory whose bytes are authorized")
    ap.add_argument("--check", action="store_true")
    # TWO PHASES, and the split is not cosmetic. The founder's participation
    # record is part of the bundle: the assembler hashes it into the manifest.
    # So the decision is written and COMMITTED first, the candidate is assembled
    # from that committed state, and only then is the authorization built --
    # which means the one build this launch performs happens BEFORE any
    # authorization exists, never after it.
    ap.add_argument("--write-participation", action="store_true",
                    help="phase 1: record the founder's decision and stop")
    ap.add_argument("--authorize", action="store_true",
                    help="phase 2: manifest and authorization, from an already "
                         "assembled candidate whose participation is committed")
    args = ap.parse_args(argv)
    if not (args.check or args.write_participation or args.authorize):
        raise SystemExit("choose --write-participation, --authorize or --check")

    from scripts.pettripfinder import deployment_authorization as DA
    from scripts.pettripfinder import global_deployment as GD
    from scripts.pettripfinder import launch_participation as LP
    from scripts.pettripfinder import release_index as RI

    bundle = _load(Path(args.candidate) / "global_bundle_manifest.json")
    packet = _load(PACKET)
    bound = packet["the_four_digests_this_authorization_binds"]

    # THE FOUNDER AUTHORIZED A DIGEST, NOT A DIRECTORY.
    if bundle["bundle_sha256"] != bound["final_candidate_digest"]:
        raise SystemExit(
            "REFUSING: the assembled bundle is %s, the founder authorized %s. A different "
            "bundle is a different release, and reconciling it silently is the failure this "
            "check exists to prevent."
            % (bundle["bundle_sha256"], bound["final_candidate_digest"]))
    if bundle["sitemap_sha256"] != bound["candidate_sitemap_sha256"]:
        raise SystemExit("REFUSING: sitemap digest disagrees with the authorized packet")
    if not bundle["all_gates_pass"]:
        raise SystemExit("REFUSING: the bundle's own gates do not all pass")
    if bundle["deployment_authorized"] is not False:
        raise SystemExit("REFUSING: the bundle already claims to be authorized")

    # PARENT. Read live, not the branch base.
    idx, state, problems = RI.live_index()
    if problems:
        raise SystemExit("REFUSING: current verified live is inconsistent: %s" % problems)
    live = state.to_dict()
    if live["live_deploy_id"] != packet["parent_release"]["live_deploy_id"]:
        raise SystemExit(
            "STALE_PARENT: the packet was authorized against %s and live is now %s. An "
            "already-authorized candidate is never silently rebased."
            % (packet["parent_release"]["live_deploy_id"], live["live_deploy_id"]))
    for required in ("lexington-ky", "toledo-oh"):
        if required not in live["participating_markets"]:
            raise SystemExit("REFUSING: %s is not live" % required)

    # 1. PARTICIPATION -- the founder's decision, written first because the
    #    bundle hashes it and the authorization re-checks it.
    participation = _load(PARTICIPATION)

    if args.authorize:
        # Phase 2 does NOT re-make the decision. It checks that the decision
        # already committed is the one being authorized, and that it moved only
        # this market. Re-flipping here would rewrite the very bytes the
        # candidate was assembled against.
        row = next((r for r in participation["markets"] if r["market_id"] == MARKET_ID), None)
        if row is None:
            raise SystemExit("REFUSING: %s has no participation row" % MARKET_ID)
        if row["launch_status"] != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH:
            raise SystemExit(
                "REFUSING: %s is %r. Run --write-participation and commit it before "
                "authorizing." % (MARKET_ID, row["launch_status"]))
        decision = row.get("founder_decision") or {}
        if decision.get("authorized_candidate_digest") != bound["final_candidate_digest"]:
            raise SystemExit(
                "REFUSING: the committed founder decision names candidate %r, the packet binds "
                "%r" % (decision.get("authorized_candidate_digest"),
                        bound["final_candidate_digest"]))
        if participation["decision"].get("work_order") != WORK_ORDER:
            raise SystemExit("REFUSING: the committed decision block is not this work order's")
        authorized_now = sorted(r["market_id"] for r in participation["markets"]
                                if r["launch_status"] == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
        expected = sorted(r["market_id"] for r in bundle["participating_markets"])
        if authorized_now != expected:
            raise SystemExit(
                "REFUSING: the committed participation authorizes %s but the candidate "
                "participates %s" % (authorized_now, expected))
        changed = [MARKET_ID]
    else:
        before = {r["market_id"]: r["launch_status"] for r in participation["markets"]}
        changed = _flip(participation, bound, before)
        participation["decision"] = participation_decision(bundle)

    if args.check:
        print("would move  :", changed)
        print("bundle      :", bundle["bundle_sha256"], "MATCHES the authorized digest")
        print("parent      :", live["live_deploy_id"], "unchanged")
        print("nothing written (--check)")
        return 0

    if args.write_participation:
        _write(PARTICIPATION, participation)
        print("participation moved :", changed, "->", LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
        print("participation sha   :", LP.participation_sha256())
        print("NEXT: commit this, assemble the candidate from the committed state, then "
              "re-run with --authorize")
        return 0

    participation_sha = LP.participation_sha256()
    if participation_sha != bundle["launch_participation"]["sha256"]:
        raise SystemExit(
            "REFUSING: the committed participation hashes to %s but the candidate was built "
            "against %s. The authorization would refuse its own repository. Assemble the "
            "candidate from the COMMITTED participation record rather than reconciling this."
            % (participation_sha, bundle["launch_participation"]["sha256"]))

    # 2. THE MANIFEST of the bundle being authorized, written before the deploy.
    manifest = GD.write_manifest(bundle)
    manifest_problems = GD.verify_manifest(manifest)
    if manifest_problems:
        raise SystemExit("REFUSING: manifest does not verify: %s" % manifest_problems)

    # 3. THE AUTHORIZATION, built by the contract that owns it.
    authorization_id = "ptf-auth-nashville-005-%s" % bundle["bundle_sha256"][:12]
    authorized_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    auth = DA.build_authorization(
        manifest,
        authorization_id=authorization_id,
        work_order=WORK_ORDER,
        authorized_by="founder",
        source_commit=git("rev-parse", "HEAD"),
        rollback_target=live["live_deploy_id"],
        target_site=TARGET_SITE,
        target_domain=TARGET_DOMAIN,
        authorized_at=authorized_at,
        authorization_source=AUTHORIZATION_SOURCE,
        note=("Nashville joins as the THIRTEENTH market at %d published profiles and %d "
              "verified-no-pets over a 180-identity registered census. Every previously live "
              "market moves by exactly zero. The rollback target is %s, the CURRENT live "
              "deployment -- not that deployment's own rollback_target %s, which is the Toledo "
              "deploy Lexington replaced and would un-deploy Lexington. Four Nashville rows "
              "remain held by the modern gates and none is promoted by this launch."
              % (manifest["participating_markets"][
                     [r["market_id"] for r in manifest["participating_markets"]].index(MARKET_ID)
                 ]["published_profiles"],
                 _load(PKG / "markets" / "authority" / MARKET_ID
                       / "hotel_exclusions.json")["count"],
                 live["live_deploy_id"], live["rollback_target"])))

    path = DEPLOY / "deployment_authorizations" / ("%s.json" % authorization_id)
    if path.exists():
        raise SystemExit("REFUSING: %s already exists" % path.name)
    _write(path, auth)

    verify_problems = DA.verify_authorization(auth, manifest)
    if verify_problems:
        raise SystemExit("REFUSING: the authorization does not verify against the repository: %s"
                         % verify_problems)

    print("participation moved :", changed, "->", LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
    print("participation sha   :", participation_sha, "(matches the authorized bundle)")
    print("manifest written    :", manifest["bundle_sha256"])
    print("authorization       :", authorization_id)
    print("authorized_at       :", authorized_at)
    print("bundle_sha256       :", auth["bundle_sha256"])
    print("rollback_target     :", auth["rollback_target"])
    print("markets/profiles    :", len(auth["participating_markets"]), auth["total_profiles"])
    print("verify_authorization:", "CLEAN" if not verify_problems else verify_problems)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
