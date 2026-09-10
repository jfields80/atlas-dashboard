"""PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 -- rollback determination and the record.

Runs only after the deploy and only after targeted live verification. It decides
the rollback question first, and writes the durable record only if the answer is
"no rollback".

THE ROLLBACK QUESTION, ASKED IN THE ORDER'S OWN TERMS

A rollback happens if and only if BOTH are true: a critical live check failed,
AND the failed release is still what production is serving. If a newer valid
release became live in the meantime, rolling back would un-deploy someone else's
work, so this REFUSES the rollback rather than performing a stale one. The
rollback target is read from the authorization -- never from an older deployment
record, and never a single-market restore, neither of which exists as a thing
this host can do.

THE STATUS TRANSITION IS RECORDED LATE, AND SAYS SO

``nashville_tn_launch_authorization_005.py`` wrote the authorization and left it
PREPARED: it never called ``transition``. The deploy therefore ran against a
PREPARED authorization, which ``deployability_problems`` would have refused had
it been asked. What that gate protects -- the exact bundle digest, the exact
sitemap digest, the participation hash, the parent deployment -- was each checked
directly and held, and live verification then proved production serves those
exact bytes. But the state machine step was skipped, and this records it as what
it was, with its real timestamp, rather than backdating a decision.

WHAT THE PIN MEANS

``tests/pettripfinder/pins/deployment_state.json`` carries two different facts.
``live`` is what production serves and moves only here. ``source`` is what a
fresh assembly of the committed source produces. This launch shipped exactly the
committed source, so the two agree and ``moved_by`` returns to null.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
MARKET_ID = "nashville-tn"
AUTHORIZATION_ID = "ptf-auth-nashville-005-c12b410ec833"
RECORD_ID_PREFIX = "ptf-deploy-nashville-005"
PINS = _DASH / "tests" / "pettripfinder" / "pins" / "deployment_state.json"
DEPLOY = _DASH / "deploy" / "netlify"


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh, object_pairs_hook=OrderedDict)


def _write(path, doc):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def rollback_determination(verification, auth):
    """Phase 10. Returns the determination; raises if a rollback is actually due."""
    failed = verification["failed_critical_checks"]
    still_current = verification["live_sitemap_sha256"] == auth["sitemap_sha256"]
    determination = OrderedDict((
        ("work_order", WORK_ORDER),
        ("critical_checks", len(verification["critical_checks"])),
        ("critical_checks_failed", failed),
        ("failed_release_is_still_current", still_current),
        ("rollback_required", bool(failed)),
        ("rollback_performed", False),
        ("rollback_target_if_it_had_been", auth["rollback_target"]),
        ("rollback_target_source", "the authorization's own rollback_target, which is the "
                                   "pre-Nashville verified live parent"),
        ("stale_rollback_refused", False),
        ("why", "no critical check failed, so there is nothing to undo. Had one failed, the "
                "target would be %s -- never a single-market restore, never an older "
                "deployment record's rollback_target." % auth["rollback_target"]),
    ))
    if failed:
        if not still_current:
            determination["stale_rollback_refused"] = True
            raise SystemExit(
                "STOP: %d critical check(s) failed but production no longer serves this "
                "release. REFUSING a stale rollback: %s" % (len(failed), failed))
        raise SystemExit(
            "STOP: %d critical check(s) failed and this release is still current. A rollback "
            "to %s is due and must be performed deliberately, not by this recorder: %s"
            % (len(failed), auth["rollback_target"], failed))
    return determination


def live_results_block(verification):
    """The verification, reshaped so ``verify_record`` can actually police it.

    Each critical check becomes a mapping with a ``pass`` key, because that is
    the shape ``verify_record`` scans for when it refuses to call a record
    DEPLOYED. A flat boolean would be recorded and never checked.
    """
    block = OrderedDict((
        ("live_sitemap_sha256", verification["live_sitemap_sha256"]),
        ("authorized_sitemap_sha256", verification["authorized_sitemap_sha256"]),
        ("live_route_count", verification["live"]["routes"]),
        ("authorized_route_count", verification["live"]["authorized_routes"]),
        ("routes_http_200", verification["live"]["http_200"]),
        ("routes_byte_identical_to_authorized_bundle", verification["live"]["byte_identical"]),
        ("routes_non_200", verification["live"]["non_200"]),
        ("routes_mismatched", verification["live"]["byte_mismatched"]),
        ("previous_deploy_route_count",
         verification["versus_previous_deploy"]["previous_route_count"]),
        ("routes_added_vs_previous_deploy", verification["versus_previous_deploy"]["added"]),
        ("routes_removed_vs_previous_deploy", verification["versus_previous_deploy"]["removed"]),
        ("removed_routes", verification["versus_previous_deploy"]["removed_routes"]),
        ("added_by_market", verification["versus_previous_deploy"]["added_by_market"]),
        ("nashville", verification["nashville"]),
        ("published_profiles_by_market", verification["live_profiles_by_market"]),
        ("total_profiles", verification["live"]["profiles"]),
        ("unrelated_markets_whose_route_count_changed",
         verification["unrelated_markets_whose_route_count_changed"]),
        ("broken_links", len(verification["critical_broken_links"])),
        ("held_identities_reaching_production",
         verification["nashville"]["held_rows_reaching_production"]),
    ))
    block["critical_checks"] = OrderedDict(
        (name, OrderedDict((("pass", bool(ok)),)))
        for name, ok in verification["critical_checks"].items())
    block["ALL_CRITICAL_CHECKS_PASS"] = verification["ALL_CRITICAL_CHECKS_PASS"]
    return block


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy-id", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--live-results", required=True)
    ap.add_argument("--deployed-at", required=True)
    ap.add_argument("--command", required=True)
    ap.add_argument("--deployed-directory", required=True)
    ap.add_argument("--out", required=True, help="where the rollback determination is written")
    args = ap.parse_args(argv)

    from scripts.pettripfinder import deployment_authorization as DA
    from scripts.pettripfinder import global_deployment as GD

    auth = DA.load_authorization(AUTHORIZATION_ID)
    verification = _load(args.live_results)
    candidate = Path(args.candidate)
    bundle = _load(candidate / "global_bundle_manifest.json")

    if verification["authorization_id"] != AUTHORIZATION_ID:
        raise SystemExit("REFUSING: the verification report is for %s"
                         % verification["authorization_id"])
    if verification["host_deployment_id"] != args.deploy_id:
        raise SystemExit("REFUSING: the verification report is for deploy %s, not %s"
                         % (verification["host_deployment_id"], args.deploy_id))

    # PHASE 10 -- decided before anything is written.
    determination = rollback_determination(verification, auth)

    # PHASE 11a -- the transition the authorize step never performed.
    if auth["authorization_status"] == DA.PREPARED:
        auth = DA.transition(
            auth, DA.AUTHORIZED,
            note=("founder authorized nashville-tn for launch in %s. Recorded LATE: the "
                  "authorize step wrote this authorization and left it PREPARED, so the "
                  "deploy ran without deployability_problems having been asked. Every "
                  "substantive binding that gate enforces was checked directly and held -- "
                  "bundle digest, sitemap digest, participation hash and parent deployment -- "
                  "and live verification then proved production serves exactly these bytes."
                  % WORK_ORDER))
        problems = (DA.verify_authorization(auth, _load(GD.MANIFEST_PATH))
                    + DA.deployability_problems(auth)
                    + DA.verify_bundle_directory(auth, candidate / "site"))
        if problems:
            raise SystemExit("REFUSING: AUTHORIZED verification failed: %s" % problems)
        DA.write_authorization(auth)
        superseded = DA.supersede_earlier(auth)
        manifest_doc = DA.authorize_manifest(auth)
        _write(GD.MANIFEST_PATH, manifest_doc)
        manifest_problems = DA.manifest_authorization_problems(manifest_doc)
        if manifest_problems:
            raise SystemExit("REFUSING: manifest authorization problems: %s" % manifest_problems)
    else:
        superseded = []

    # PHASE 11b -- AUTHORIZED consumed, and the durable record.
    auth = DA.transition(auth, DA.DEPLOYED,
                         note="deployed to %s as %s by %s"
                              % (auth["target_domain"], args.deploy_id, WORK_ORDER))
    DA.write_authorization(auth)

    record = DA.build_deployment_record(
        auth,
        deployment_record_id="%s-%s" % (RECORD_ID_PREFIX, args.deploy_id),
        deployment_id=args.deploy_id,
        previous_deployment_id=auth["rollback_target"],
        deployed_at=args.deployed_at,
        deployer=OrderedDict((("work_order", WORK_ORDER),
                              ("authorized_by", "founder"),
                              ("executed_by", "claude-code"))),
        production_url=auth["target_domain"],
        deployed_directory=args.deployed_directory,
        command=args.command,
        global_gate_results=OrderedDict(
            (gid, bool(res.get("pass"))) for gid, res in sorted((bundle.get("gates") or {}).items())),
        live_verification_results=live_results_block(verification),
        final_status=DA.DEPLOYED,
        rollback_used=False,
        exit_status=0)
    record_problems = DA.verify_record(record, auth)
    if record_problems:
        raise SystemExit("REFUSING: the deployment record has problems: %s" % record_problems)
    record_path = DA.write_record(record)

    # PHASE 11c -- the current-live pin. `live` moves only here; `source` returns
    # to sync because this launch shipped exactly the committed source.
    pins = _load(PINS)
    shape = OrderedDict((
        ("bundle_sha256", auth["bundle_sha256"]),
        ("sitemap_sha256", auth["sitemap_sha256"]),
        ("participating_markets", list(auth["participating_markets"])),
        ("profile_counts", OrderedDict(auth["profile_counts"])),
        ("total_profiles", auth["total_profiles"]),
        ("sitemap_route_count", auth["sitemap_route_count"]),
        ("total_html_pages", auth["total_html_pages"]),
        ("total_files", auth["total_files"]),
    ))
    nashville_profiles = auth["profile_counts"][MARKET_ID]
    pins["reviewed_by"] = WORK_ORDER
    pins["live"] = OrderedDict((
        ("deploy_id", args.deploy_id),
        ("deployed_by", WORK_ORDER),
        ("authorization_id", AUTHORIZATION_ID),
        ("deployment_record_id", record["deployment_record_id"]),
        ("previous_deploy_id", auth["rollback_target"]),
        ("source_commit", auth["source_commit"]),
    ))
    pins["live"].update(shape)
    pins["live"]["rollback_target"] = auth["rollback_target"]
    pins["live"]["note"] = (
        "NASHVILLE IS LIVE AT %d. Deploy %s published the THIRTEENTH market by %s, on the "
        "candidate the founder authorized by digest. All %d live routes returned 200 and are "
        "byte-identical to the authorized bundle; %d routes were added and 0 removed against "
        "the Lexington deploy read from its own address, and every unrelated market kept its "
        "exact route and profile count. Rollback is the exact prior Lexington release %s. "
        "Nashville's four held rows publish nothing: all %d live Nashville profiles are in the "
        "published authority set, so no held identity reached production under any slug."
        % (nashville_profiles, args.deploy_id, WORK_ORDER,
           verification["live"]["routes"], verification["versus_previous_deploy"]["added"],
           auth["rollback_target"], nashville_profiles))
    pins["live"]["rollback_record"] = "ptf-deploy-lexington-006-%s.json" % auth["rollback_target"]
    pins["source"] = OrderedDict((("ahead_of_production", False), ("moved_by", None)))
    pins["source"].update(shape)
    pins["source"]["note"] = (
        "IN SYNC with production. %s shipped exactly this source as deploy %s, so moved_by is "
        "null and ahead_of_production is false. The next application order that moves any "
        "market's authority moves this block and not the live one."
        % (WORK_ORDER, args.deploy_id))
    _write(PINS, pins)

    determination["deployment_record_id"] = record["deployment_record_id"]
    _write(Path(args.out), determination)

    print("rollback required :", determination["rollback_required"])
    print("authorization     :", auth["authorization_status"])
    print("superseded        :", superseded)
    print("record            :", record_path.relative_to(_DASH).as_posix())
    print("record problems   : 0")
    print("deploy            :", args.deploy_id, "| previous:", auth["rollback_target"])
    print("markets/profiles  :", len(auth["participating_markets"]), "/", auth["total_profiles"])
    print("pin live deploy   :", pins["live"]["deploy_id"])
    print("pin source        : ahead_of_production", pins["source"]["ahead_of_production"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
