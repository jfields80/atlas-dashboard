"""PTF-RELEASE-FACTORY-BOUNDED-MIGRATION-DECISION-004 -- Columbia reuse-staging proof.

    python mig4_stage.py <dash> <out.json>

Run in the replay worktree after the registration reached AUTHORIZATION_READY.
Same shape as the 002 stage driver. Participation is projected IN MEMORY ONLY; nothing
is written to launch_participation.json and no authorization is made. The candidate
is PROJECTED / NON-DEPLOYABLE (deployment_bundle_manifest must refuse it). FAST is not
re-run: the committed seal receipt must bind the package to current live.

Additionally compares the candidate site byte for byte with the seeded live site
(C:/t/seed4/site) so the delta is proven on bytes, not only on counts.
"""
import copy
import hashlib
import json
import sys
import time
from collections import OrderedDict
from pathlib import Path

DASH = Path(sys.argv[1])
OUT = Path(sys.argv[2])
sys.path.insert(0, str(DASH))
from scripts.pettripfinder import launch_participation as LP  # noqa: E402
from scripts.pettripfinder import release_coordinator as RC  # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP  # noqa: E402

MARKET = "columbia-sc"
STORE = Path("C:/t/rs4")
CAND_ROOT = Path("C:/t/cc4")
WORK = Path("C:/t/cw4s")
LIVE_SITE = Path("C:/t/seed4/site")
PARTICIPATION = LP.PARTICIPATION_PATH
AUTH_DIR = DASH / "deploy" / "netlify" / "deployment_authorizations"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*") if p.is_file()}


out = OrderedDict((("market", MARKET),))
part_before = sha(PARTICIPATION)
auth_before = sorted(p.name for p in AUTH_DIR.glob("*.json"))
committed_doc = LP.load_participation()
committed_row = [r for r in committed_doc["markets"] if r["market_id"] == MARKET]
out["committed_participation_status"] = committed_row[0]["launch_status"] if committed_row else None
projection = copy.deepcopy(committed_doc)
for row in projection["markets"]:
    if row["market_id"] == MARKET:
        row["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
packages = sorted((SMP.LAUNCH_PACKAGE / "markets" / "packages" / MARKET).glob("pkg-*.json"))
out["packages_found"] = [p.name for p in packages]
package = SMP.read_sealed(packages[-1])
out["package_id"] = package["package_id"]

live = RC.LiveTruth.read()
store = RC.ReleaseStore(STORE)
parent = store.get_release(live.digest())
out["parent_release_digest"] = live.digest()
out["PARENT_RELEASE_LOOKUP"] = "PASS" if (
    parent is not None and RC.digest_of(RC.release_identity(parent)) == live.digest()
    and len(store.fragment_digests(live.digest())) == len(live.participating_markets)) else "FAIL"
parent_fragments = store.fragment_digests(live.digest())

t = time.monotonic()
candidate = RC.stage(package=package, delta_kind=RC.ADD, participation_doc=projection,
                     authority={"add": [MARKET]}, live=live, store=store, cache=None,
                     run_fast_lane=False, require_gates=False,
                     work_dir=WORK, candidates_root=CAND_ROOT)
out["stage_seconds"] = round(time.monotonic() - t, 1)
out["candidate_root"] = str(candidate.root)
out["telemetry"] = candidate.telemetry
gates = json.loads((candidate.root / "gates.json").read_text(encoding="utf-8"))
out["gates_total"] = len(gates["gates"])
out["gates_failing"] = gates["failing"]
out["gates_pass"] = sorted(g for g, r in gates["gates"].items() if r["pass"])
out["parent_routes_preserved"] = gates["gates"].get("release.parent_routes_preserved")
out["additions_are_declared"] = gates["gates"].get("release.additions_are_declared")
out["release_diff"] = candidate.diff

live_markets = list(live.participating_markets)
rows = {r["market_id"]: r for r in candidate.manifest["markets"]}
out["candidate_markets"] = len(rows)
out["candidate_market_set_is_live_plus_columbia"] = sorted(rows) == sorted(live_markets + [MARKET])
out["unchanged_bundles_reused"] = sum(1 for m in live_markets if rows[m]["fragment_source"] == RC.FROM_STORE)
out["unchanged_markets_rebuilt"] = sum(1 for m in live_markets if rows[m]["fragment_source"] != RC.FROM_STORE)
out["reused_fragment_is_parent_fragment"] = all(
    rows[m]["fragment_digest"] == parent_fragments.get(m) for m in live_markets)
out["columbia_fragment_source"] = rows[MARKET]["fragment_source"]
out["columbia_builder_invocations"] = candidate.telemetry.get("delta_market_builder_invocations")
out["columbia_profiles"] = rows[MARKET]["profile_count"]
out["columbia_routes"] = rows[MARKET]["route_count"]
out["live_profile_counts_preserved"] = all(
    rows[m]["profile_count"] == live.state.profile_counts[m] for m in live_markets)

# ---- byte-level delta against the seeded live site ------------------------ #
live_tree, cand_tree = tree(LIVE_SITE), tree(candidate.root / "site")
removed = sorted(set(live_tree) - set(cand_tree))
added = sorted(set(cand_tree) - set(live_tree))
changed = sorted(p for p in set(live_tree) & set(cand_tree) if live_tree[p] != cand_tree[p])
slug = MARKET
added_outside = [p for p in added if slug not in p and "columbia" not in p]
out["bytes"] = OrderedDict((
    ("live_files", len(live_tree)), ("candidate_files", len(cand_tree)),
    ("removed", len(removed)), ("removed_sample", removed[:20]),
    ("added", len(added)), ("added_not_naming_columbia", added_outside[:50]),
    ("added_not_naming_columbia_count", len(added_outside)),
    ("changed", len(changed)), ("changed_files", changed[:200]),
))

try:
    RC.deployment_bundle_manifest(candidate)
    out["projected_candidate_deployable"] = "UNEXPECTEDLY_YES"
except RC.CoordinatorError as exc:
    out["projected_candidate_deployable"] = "NO (%s)" % exc.code
out["CANDIDATE"] = "PROJECTED / NON-DEPLOYABLE" if out["projected_candidate_deployable"].startswith("NO") \
    else "DEPLOYABLE (unexpected)"

out["participation_sha256_unchanged"] = sha(PARTICIPATION) == part_before
out["participation_after"] = [r["launch_status"] for r in LP.load_participation()["markets"]
                              if r["market_id"] == MARKET]
out["authorizations_unchanged"] = sorted(p.name for p in AUTH_DIR.glob("*.json")) == auth_before
OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("telemetry", "release_diff", "gates_pass")},
                 indent=1, default=str)[:8000])
