"""PTF-RELEASE-STORE-LIVE-CONTENT-KEY-CORRECTION-005 -- Phase 5 NO_DELTA store proof.

    python mig5_nodelta.py <dash> <out.json>

Run in the replay worktree AFTER Columbia's registration commit, so the live
release digest has moved away from the one the store was seeded under. Uses the
store seeded ONCE (C:/t/rs4, 004: one assembly of current live, bundle == live).
stage(NO_DELTA) under the COMMITTED participation; the candidate must be the live
bundle byte for byte. Nothing is written to the repository; no deployment.
"""
import hashlib
import json
import sys
import time
from collections import OrderedDict
from pathlib import Path

DASH, OUT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(DASH))
from scripts.pettripfinder import launch_participation as LP  # noqa: E402
from scripts.pettripfinder import release_coordinator as RC  # noqa: E402

STORE, CAND_ROOT, WORK, LIVE_SITE = (Path("C:/t/rs4"), Path("C:/t/cc5n"), Path("C:/t/cw5n"),
                                     Path("C:/t/seed4/site"))


def tree(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


out = OrderedDict((("mode", "NO_DELTA"),))
part_before = hashlib.sha256(LP.PARTICIPATION_PATH.read_bytes()).hexdigest()
live = RC.LiveTruth.read()
store = RC.ReleaseStore(STORE)
out["live_bundle_sha256"] = live.state.bundle_sha256
out["live_release_digest_now"] = live.digest()
out["stored_releases"] = store.releases()
out["digest_lookup_finds_parent"] = store.get_release(live.digest()) is not None
doc, found_by = store.resolve_deployed(release_digest=live.digest(), bundle_sha256=live.state.bundle_sha256)
out["parent_found_by"] = found_by
out["PARENT_LOOKUP"] = "PASS" if (doc is not None and doc["bundle_sha256"] == live.state.bundle_sha256
                                  and len(RC._fragments_of(doc)) == len(live.participating_markets)) else "FAIL"
t = time.monotonic()
candidate = RC.stage(package=None, delta_kind=RC.NO_DELTA, live=live, store=store, cache=None,
                     work_dir=WORK, candidates_root=CAND_ROOT, require_gates=False)
out["stage_seconds"] = round(time.monotonic() - t, 1)
out["candidate_root"] = str(candidate.root)
out["telemetry"] = candidate.telemetry
gates = json.loads((candidate.root / "gates.json").read_text(encoding="utf-8"))
out["gates_total"] = len(gates["gates"])
out["gates_failing"] = gates["failing"]
out["parent_routes_preserved"] = gates["gates"].get("release.parent_routes_preserved")
out["unchanged_bundles_reused"] = candidate.telemetry["bundles_reused"]
out["unchanged_markets_rebuilt"] = candidate.telemetry["bundles_rebuilt"]
out["unexpected_delta"] = candidate.diff["unexpected_changes"]
out["candidate_bundle_sha256"] = candidate.bundle_sha256
out["BUNDLE_BYTES_MATCH_CURRENT_LIVE"] = candidate.bundle_sha256 == live.state.bundle_sha256
live_tree, cand_tree = tree(LIVE_SITE), tree(candidate.root / "site")
out["files"] = OrderedDict((
    ("live", len(live_tree)), ("candidate", len(cand_tree)),
    ("removed", sorted(set(live_tree) - set(cand_tree))[:20]),
    ("added", sorted(set(cand_tree) - set(live_tree))[:20]),
    ("changed", sorted(p for p in set(live_tree) & set(cand_tree) if live_tree[p] != cand_tree[p])[:20]),
))
out["routes"] = OrderedDict((("live", sum(1 for p in live_tree if p.endswith("index.html"))),
                             ("candidate", sum(1 for p in cand_tree if p.endswith("index.html")))))
out["participation_sha256_unchanged"] = hashlib.sha256(LP.PARTICIPATION_PATH.read_bytes()).hexdigest() == part_before
OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "telemetry"}, indent=1, default=str))
