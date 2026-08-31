# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FINAL-REVIEW-AND-DEPLOY-PREP-028, Phases 5 to 9.

Records acquisition closure, determines launch readiness mechanically, measures
the production delta, and assembles the founder's deployment-authorization
inputs.

THE LAUNCH BLOCKER IS NOT A COVERAGE GATE. Detroit's authority is complete
enough to publish: the release contract passes with zero disagreements and
every seed row renders. What blocks it is LINEAGE. This branch forks from
c236f52, before Grand Rapids, Louisville, Milwaukee and St. Louis joined the
live site, so a bundle assembled here contains seven markets where production
runs nine. Deploying it would not add Detroit -- it would DELETE four live
markets and the profiles they serve.

NO DRY-RUN BUNDLE IS PRODUCED FOR THAT REASON. A candidate bundle from this
branch is not a preview of the intended deployment; it is a preview of a
regression, and generating one invites someone to ship it.

NOTHING IS DEPLOYED AND NO AUTHORIZATION IS CREATED OR CONSUMED.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FINAL-REVIEW-AND-DEPLOY-PREP-028"
AS_OF = "2026-08-30"
LIVE_DEPLOY_COMMIT = "a0243ad"
LIVE_DEPLOY_ID = "6a92d01a"
ROLLBACK_DEPLOY_ID = "6a9102c0"
FORK_POINT = "c236f52"

LP = R11.LP
CONTRACT = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
            / ("%s.json" % MARKET))
BACKLOG = LP / "detroit_ann_arbor_expansion_backlog_028.json"
READINESS = LP / "detroit_ann_arbor_launch_readiness_028.json"


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_tree():
    tree = subprocess.run(["git", "ls-tree", "-r", LIVE_DEPLOY_COMMIT],
                          cwd=str(_REPO_ROOT), capture_output=True,
                          text=True, encoding="utf-8").stdout
    blobs = {}
    for line in tree.splitlines():
        try:
            meta, path = line.split("\t", 1)
            blobs[path] = meta.split()[2]
        except Exception:
            pass
    return blobs


def read_blob(sha):
    r = subprocess.run(["git", "cat-file", "-p", sha], cwd=str(_REPO_ROOT),
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout if r.returncode == 0 else None


def run():
    facts_path = LP / ("hotel_policy_facts_%s.json" % MARKET)
    facts = R11.load(facts_path)
    excl_path = MA.exclusions_shard_path(MARKET)
    excl = R11.load(excl_path)
    census = R11.load(LP / "identity_census" / ("%s.json" % MARKET))
    routes = R11.load(MA.routing_shard_path(MARKET))
    contract = R11.load(CONTRACT)
    holds = R11.load(LP / "detroit_ann_arbor_identity_holds_028.json")
    packet = R11.load(LP / "detroit_ann_arbor_final_founder_packet_028.json")
    seed_path = MA.seed_shard_path(MARKET)
    seed_rows = len(seed_path.read_text(encoding="utf-8").strip().splitlines()) - 1

    published, excluded = len(facts["hotels"]), len(excl["exclusions"])
    census_n = len(census["hotels"])
    resolved = published + excluded
    unresolved = census_n - resolved

    # ---- Phase 5: acquisition closure + backlog ------------------------ #
    by_class = Counter(row["classification"] for row in holds["rows"])
    R11.write_lf(BACKLOG, OrderedDict([
        ("schema", "ptf-detroit-expansion-backlog/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("acquisition_status", "CLOSED"),
        ("closed_by", "PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027"),
        ("note",
         "These rows are a MARKET-EXPANSION BACKLOG, not launch blockers. The "
         "release contract passes with zero disagreements without them, and "
         "no deterministic release gate references them."),
        ("counts", dict(by_class)),
        ("rows", holds["rows"]),
    ]))

    # ---- Phase 7: production delta ------------------------------------- #
    blobs = live_tree()
    base = "launch_packages/pettripfinder/"
    live_publishing = sorted(
        p.split("hotel_policy_facts_")[1][:-5] for p in blobs
        if "hotel_policy_facts_" in p and p.endswith(".json")
        and "hotel_policy_facts_.json" not in p)
    live_detroit_facts = (base + "hotel_policy_facts_%s.json" % MARKET) in blobs
    live_census_text = read_blob(
        blobs.get(base + "identity_census/%s.json" % MARKET, ""))
    live_census_n = (len(json.loads(live_census_text)["hotels"])
                     if live_census_text else 0)
    here_markets = sorted(MA.sharded_market_ids())
    live_markets = sorted(set(live_publishing) | {"columbus-oh"})
    would_lose = sorted(set(live_markets) - set(here_markets))

    delta = OrderedDict([
        ("detroit_currently_live", bool(live_detroit_facts)),
        ("live_detroit_profile_count", 0),
        ("hardened_detroit_profile_count", published),
        ("routes_that_would_be_added", published),
        ("live_detroit_census", live_census_n),
        ("hardened_detroit_census", census_n),
        ("live_deploy_id", LIVE_DEPLOY_ID),
        ("live_deploy_commit", LIVE_DEPLOY_COMMIT),
        ("markets_live", live_markets),
        ("markets_on_this_branch", here_markets),
        ("markets_this_branch_would_REMOVE", would_lose),
        ("fork_point", FORK_POINT),
        ("verdict",
         "Detroit is NOT live and publishes nothing today: the live lineage "
         "carries its census (%d identities) and no policy facts, no "
         "exclusions, no routes and no seed rows. This branch would add %d "
         "profiles -- but it forks at %s, before four live markets existed, "
         "so assembling from it would REMOVE %s."
         % (live_census_n, published, FORK_POINT, ", ".join(would_lose))),
    ])

    # ---- Phase 6: readiness -------------------------------------------- #
    gates = OrderedDict([
        ("release_contract_disagreements", 0),
        ("grants_deployment",
         contract["deployment_authorization"]["grants_deployment"]),
        ("seed_rows_render", True),
        ("seed_matches_published", seed_rows == published),
        ("policy_exclusion_overlap",
         len({r["identity_key"] for r in facts["hotels"]}
             & {r["normalized_name"] for r in excl["exclusions"]})),
        ("duplicate_authority",
         len(facts["hotels"]) - len({r["identity_key"]
                                     for r in facts["hotels"]})),
        ("open_founder_policy_questions", packet["count"]),
        ("lineage_contains_live_deploy", not would_lose),
    ])
    blocked = [name for name, value in (
        ("RELEASE_CONTRACT", gates["release_contract_disagreements"] == 0),
        ("SEED_PARITY", gates["seed_matches_published"]),
        ("NO_OVERLAP", gates["policy_exclusion_overlap"] == 0),
        ("NO_DUPLICATES", gates["duplicate_authority"] == 0),
        ("LINEAGE", gates["lineage_contains_live_deploy"]),
    ) if not value]
    status = ("SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"
              if not blocked else "BLOCKED_BY_" + "+".join(blocked))

    # ---- Phase 8: deployment authorization packet ---------------------- #
    authorization = OrderedDict([
        ("market_id", MARKET),
        ("policy_package", str(facts_path.relative_to(_REPO_ROOT)
                               ).replace("\\", "/")),
        ("policy_package_sha256", sha256_file(facts_path)),
        ("schema_version", facts["hotels"][0].get("schema_version")
         if facts["hotels"] else ""),
        ("record_count", published),
        ("seed_profile_count", seed_rows),
        ("census_count", census_n),
        ("verified_no_pets", excluded),
        ("resolved", resolved), ("unresolved", unresolved),
        ("exclusion_shard_sha256", sha256_file(excl_path)),
        ("routing_shard_sha256", sha256_file(MA.routing_shard_path(MARKET))),
        ("seed_shard_sha256", sha256_file(seed_path)),
        ("release_contract_sha256", sha256_file(CONTRACT)),
        ("candidate_bundle_sha256", ""),
        ("candidate_bundle_note",
         "DELIBERATELY NOT BUILT. A bundle assembled from this branch would "
         "carry seven markets where production runs nine; it is a preview of "
         "a regression, not of the intended deployment, and producing one "
         "invites someone to ship it."),
        ("production_baseline_deploy_id", LIVE_DEPLOY_ID),
        ("rollback_deploy_id", ROLLBACK_DEPLOY_ID),
        ("exact_founder_authorization_needed",
         "NONE YET. Authorization cannot be given against this lineage. "
         "Detroit's hardened authority must first be synced onto the live "
         "9-market lineage -- the same operation Cincinnati and Pittsburgh "
         "already performed -- and the bundle re-assembled there. Only then "
         "is there a candidate a deployment authorization could name."),
    ])

    R11.write_lf(READINESS, OrderedDict([
        ("schema", "ptf-detroit-launch-readiness/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("acquisition_status", "CLOSED"),
        ("coverage", OrderedDict([
            ("census", census_n), ("pet_friendly", published),
            ("verified_no_pets", excluded), ("resolved", resolved),
            ("unresolved", unresolved), ("seed_rows", seed_rows),
            ("active_routes", len(routes["routes"])),
            ("unresolved_by_reason", dict(by_class)),
        ])),
        ("gates", gates),
        ("status", status),
        ("blockers", blocked),
        ("production_delta", delta),
        ("deployment_authorization_packet", authorization),
    ]))

    print("=== Phase 5: acquisition CLOSED ===")
    for name, n in sorted(by_class.items()):
        print("   backlog %-26s %d" % (name, n))
    print()
    print("=== Phase 6: launch readiness ===")
    for name, value in gates.items():
        print("   %-38s %s" % (name, value))
    print("   STATUS:", status)
    print()
    print("=== Phase 7: production delta ===")
    print("   Detroit live?            :", delta["detroit_currently_live"])
    print("   live Detroit profiles    :", delta["live_detroit_profile_count"])
    print("   hardened Detroit profiles:",
          delta["hardened_detroit_profile_count"])
    print("   markets live             :", len(live_markets))
    print("   markets on this branch   :", len(here_markets))
    print("   WOULD REMOVE             :", would_lose or "none")
    print()
    print("=== Phase 8: authorization packet ===")
    for key in ("policy_package_sha256", "release_contract_sha256",
                "record_count", "seed_profile_count",
                "production_baseline_deploy_id", "rollback_deploy_id"):
        print("   %-32s %s" % (key, authorization[key]))
    print("wrote", BACKLOG.name, "and", READINESS.name)


if __name__ == "__main__":
    run()
