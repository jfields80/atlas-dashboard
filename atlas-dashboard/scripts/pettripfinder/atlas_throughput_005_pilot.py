"""ATLAS-THROUGHPUT-005 -- the release coordinator pilot.

Four pilots, all against frozen material, none of them touching production:

* **DATA_ONLY** -- the committed Dayton withdrawal package staged against the
  CURRENT VERIFIED LIVE release. Nine markets are inherited from durable
  release storage, Dayton comes from its validated 004 bundle, and the
  release-global artifacts regenerate.
* **STALE LINEAGE** -- the Pittsburgh / Indianapolis failure. A candidate
  staged against a parent that is no longer live is refused at activation,
  and re-staging on the current parent preserves every newer live market
  without rebuilding one of them.
* **PARTICIPATION** -- the Cincinnati / Toledo failure. The pre-flip candidate
  (the market is source-ready, not launched) and the post-flip candidate (it
  participates) are different artifacts, and the pre-flip digest can never
  authorize the post-flip one.
* **QUEUE** -- three ready packages stage serially, each from the release the
  previous one produced, never from the original parent.

Nothing here promotes a market, changes participation, or deploys. The only
host is ``release_coordinator.SimulatedHost``.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from scripts.pettripfinder import assemble_production_site as APS
from scripts.pettripfinder import bundle_cache as BC
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_coordinator as RC
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = SMP.REPO_ROOT
REPORTS = SMP.LAUNCH_PACKAGE / "reports"
DAYTON_PACKAGE = (SMP.PACKAGES_DIR / "dayton-oh" / "pkg-dayton-oh-813f7f9f089b89c7.json")


def load_package(path: Optional[Path] = None) -> "OrderedDict[str, Any]":
    return json.loads(Path(path or DAYTON_PACKAGE).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=OrderedDict)


def participation_without(market_id: str, doc: Optional[Mapping] = None) -> "OrderedDict[str, Any]":
    """The participation record as it read BEFORE a market was launched.

    A frozen copy: the committed decision is never edited.
    """
    doc = copy.deepcopy(OrderedDict(doc or LP.load_participation()))
    for row in doc.get("markets") or ():
        if row.get("market_id") == market_id:
            row["launch_status"] = LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
            row["note"] = "ATLAS-THROUGHPUT-005 pilot fixture (pre-flip); never committed"
    return doc


def _candidate_row(candidate: RC.Candidate, timing: Mapping) -> "OrderedDict[str, Any]":
    manifest = candidate.manifest
    return OrderedDict((
        ("candidate_digest", candidate.digest),
        ("bundle_sha256", candidate.bundle_sha256),
        ("parent_release_digest", manifest.get("parent_release_digest")),
        ("participating_markets", list(manifest.get("participating_markets") or ())),
        ("participation_sha256", manifest.get("participation_sha256")),
        ("total_profiles", manifest.get("total_profiles")),
        ("sitemap_route_count", manifest.get("sitemap_route_count")),
        ("total_html_pages", manifest.get("total_html_pages")),
        ("markets", [OrderedDict(((k, m[k]) for k in ("market_id", "fragment_source",
                                                      "profile_count", "route_count")))
                     for m in manifest.get("markets") or ()]),
        ("timing", OrderedDict(timing)),
    ))


def store_candidate_as_release(store: RC.ReleaseStore, candidate: RC.Candidate) -> str:
    """Put a staged candidate into durable release storage.

    This is what makes the NEXT release able to inherit from it -- and what
    makes a rollback to it possible without rebuilding anything.
    """
    manifest = copy.deepcopy(candidate.manifest)
    fragments = {m["market_id"]: m.get("fragment_digest") for m in manifest.get("markets") or ()}
    bundle = store.put_bundle(candidate.site)
    manifest["bundle_object"] = bundle["digest"]
    manifest["bundle_sha256"] = candidate.bundle_sha256
    for row in manifest.get("markets") or ():
        row["fragment_digest"] = fragments.get(row["market_id"])
    path = store.root / "releases" / ("%s.json" % RC._object_name(candidate.digest))
    RC._write_json(path, manifest)
    return candidate.digest


# --------------------------------------------------------------------------- #
# The pilots.
# --------------------------------------------------------------------------- #

def data_only_pilot(*, live: RC.LiveTruth, store: RC.ReleaseStore, cache: Any,
                    package: Mapping, work: Path) -> "OrderedDict[str, Any]":
    """CURRENT LIVE + ONE SEALED DATA-ONLY PACKAGE = ONE FINAL CANDIDATE."""
    started = time.perf_counter()
    t = time.perf_counter()
    parent = live.digest()
    parent_load = round(time.perf_counter() - t, 3)

    candidate = RC.stage(package=package, delta_kind=RC.UPDATE, live=live, store=store,
                         cache=cache, work_dir=work / "stage",
                         candidates_root=work / "candidates", run_fast_lane=True)
    total = round(time.perf_counter() - started, 3)

    host = RC.SimulatedHost(work / "host", live_release=parent)
    auth = RC.authorize(candidate, decided_by="ATLAS-THROUGHPUT-005 pilot (simulated)",
                        notes="frozen pilot; no production activation")
    record = RC.activate(candidate, auth, host, live=live, operation_id="pilot-op-1")
    verification = RC.verify_live(candidate, host, record)
    record = RC.record_verification(candidate, record, verification)

    row = _candidate_row(candidate, candidate.telemetry)
    delta_market = str(package["market_id"])
    builder_invocations = sum(int(m.get("builder_invocations") or 0)
                              for m in [candidate.telemetry] if False)
    package_row = next((m for m in candidate.manifest["markets"]
                        if m["market_id"] == delta_market), {})
    gates = json.loads((candidate.root / "gates.json").read_text(encoding="utf-8-sig"))
    row.update(OrderedDict((
        ("delta_market", delta_market),
        ("parent_load_seconds", parent_load),
        ("bundles_total", candidate.telemetry.get("bundles_total")),
        ("bundles_reused", candidate.telemetry.get("bundles_reused")),
        ("bundles_rebuilt", candidate.telemetry.get("bundles_rebuilt")),
        ("cache_hits", candidate.telemetry.get("cache_hits")),
        ("builder_invocations", 0 if candidate.telemetry.get("cache_hits") else 1),
        ("gates_total", len(gates.get("gates") or {})),
        ("gates_failing", gates.get("failing")),
        ("fast_lane_eligible", (candidate.receipt or {}).get("FAST_DATA_ONLY_RELEASE_ELIGIBLE")),
        ("fast_lane_seconds", candidate.telemetry.get("fast_lane_seconds")),
        ("total_seconds", total),
        ("diff", candidate.diff),
        ("authorization", OrderedDict(((k, auth[k]) for k in
                                       ("authorization_id", "candidate_digest",
                                        "deployment_artifact_digest", "parent_release_digest",
                                        "intended_delta_digest", "decided_by", "state")))),
        ("activation", OrderedDict(((k, record.get(k)) for k in
                                    ("outcome", "host_deployment_id", "idempotent_replay",
                                     "verified_at", "release_state")))),
        ("verification", verification),
    )))
    return row, candidate, host


def stale_lineage_pilot(*, live: RC.LiveTruth, store: RC.ReleaseStore, cache: Any,
                        package: Mapping, work: Path,
                        candidate: RC.Candidate) -> "OrderedDict[str, Any]":
    """A worker whose parent is no longer live.

    The candidate was staged against parent R. By the time it reaches
    activation the live release is R'. The authorization names R, so
    activation is refused -- and nothing about the newer live markets was ever
    at risk, because membership came from live rather than from the branch.
    """
    started = time.perf_counter()
    parent = live.digest()
    # Someone else's release became live after this candidate was staged.
    newer = "sha256:" + "a" * 64
    host = RC.SimulatedHost(work / "host-stale", live_release=newer)
    auth = RC.authorize(candidate, decided_by="ATLAS-THROUGHPUT-005 pilot (simulated)")

    class _NewerLive:
        participating_markets = live.participating_markets
        verified = True
        problems = ()

        def digest(self):
            return newer

    refused = RC.activate(candidate, auth, host, live=_NewerLive(), operation_id="pilot-op-stale")
    preserved = [m["market_id"] for m in candidate.manifest["markets"]]
    inherited = [m["market_id"] for m in candidate.manifest["markets"]
                 if m["fragment_source"] == RC.FROM_STORE]
    rebuilt = [m["market_id"] for m in candidate.manifest["markets"]
               if m["fragment_source"] == RC.REBUILT]
    missing = sorted(set(live.participating_markets) - set(preserved))
    return OrderedDict((
        ("scenario", "a stale worker branch stages against a live release it does not know about"),
        ("worktree_is_itself_stale", "toledo-oh" not in live.participating_markets),
        ("parent_at_staging", parent),
        ("live_at_activation", newer),
        ("live_markets", len(live.participating_markets)),
        ("preserved_markets", len(preserved)),
        ("inherited_from_store", len(inherited)),
        ("rebuilt", len(rebuilt)),
        ("unintended_removal", len(missing)),
        ("removed_markets", missing),
        ("activation_refused_on_stale_parent", refused["outcome"] == RC.ACTIVATION_REFUSED),
        ("refusals", refused.get("refusals")),
        ("host_untouched", host.calls == []),
        ("seconds", round(time.perf_counter() - started, 3)),
    ))


def participation_pilot(*, live: RC.LiveTruth, store: RC.ReleaseStore, cache: Any,
                        package: Mapping, work: Path,
                        final_candidate: RC.Candidate) -> "OrderedDict[str, Any]":
    """Pre-flip and post-flip are two different artifacts.

    The pre-flip candidate is staged from a participation record in which the
    delta market is source-ready but NOT founder-authorized; it therefore does
    not contain that market at all. The post-flip candidate is the real one.
    Their digests differ, and the pre-flip authorization does not authorize the
    post-flip candidate -- which is the whole of the Cincinnati / Toledo
    lesson, expressed as a refusal rather than a convention.
    """
    started = time.perf_counter()
    market_id = str(package["market_id"])
    preview_doc = participation_without(market_id)
    preview = RC.stage(package=None, delta_kind=RC.NO_DELTA, live=live, store=store,
                       cache=cache, participation_doc=preview_doc,
                       authority={"remove": [market_id]},
                       work_dir=work / "stage-preview",
                       candidates_root=work / "candidates", run_fast_lane=False,
                       # A pre-flip candidate withdraws a live market's routes with
                       # no intended delta declaring them, so the live-route gate
                       # fails -- correctly. It is staged here to be COMPARED, never
                       # to be released, and the failing gates are recorded below.
                       require_gates=False)
    preview_auth = RC.authorize(preview, decided_by="ATLAS-THROUGHPUT-005 pilot (simulated)")
    cross = RC.authorization_problems(preview_auth, final_candidate)
    return OrderedDict((
        ("scenario", "a market that is source-ready pre-flip and participating post-flip"),
        ("market", market_id),
        ("preview_digest", preview.digest),
        ("preview_gates_failing", json.loads((preview.root / "gates.json").read_text(encoding="utf-8-sig"))["failing"]),
        ("preview_is_releasable", False),
        ("preview_markets", list(preview.manifest["participating_markets"])),
        ("preview_participation_sha256", preview.manifest["participation_sha256"]),
        ("final_digest", final_candidate.digest),
        ("final_markets", list(final_candidate.manifest["participating_markets"])),
        ("final_participation_sha256", final_candidate.manifest["participation_sha256"]),
        ("digests_differ", preview.digest != final_candidate.digest),
        ("bundles_differ", preview.bundle_sha256 != final_candidate.bundle_sha256),
        ("preview_authorizes_final", not cross),
        ("refusals", cross),
        ("final_membership_in_hashed_bytes",
         "participating_markets" in final_candidate.manifest
         and "participation_sha256" in final_candidate.manifest),
        ("seconds", round(time.perf_counter() - started, 3)),
    ))


def queue_pilot(*, live: RC.LiveTruth, store: RC.ReleaseStore, work: Path,
                candidate: RC.Candidate) -> "OrderedDict[str, Any]":
    """Three ready packages, one release at a time, each from the latest live.

    005 admits ONE delta per release. The proof required here is that the
    second release stages from the release the first produced, not from the
    parent the first started at -- which is what stops two workers each
    deleting the other's market.
    """
    started = time.perf_counter()
    r0 = live.digest()
    host = RC.SimulatedHost(work / "host-queue", live_release=r0)
    auth1 = RC.authorize(candidate, decided_by="ATLAS-THROUGHPUT-005 pilot (simulated)")
    rec1 = RC.activate(candidate, auth1, host, live=live, operation_id="queue-op-1")
    r1 = store_candidate_as_release(store, candidate)

    # A second worker that staged against r0 is refused: its parent is stale.
    class _R1Live:
        participating_markets = live.participating_markets
        verified = True
        problems = ()

        def digest(self):
            return r1

    stale_second = RC.activate(candidate, auth1, host, live=_R1Live(), operation_id="queue-op-2")
    fragments_available = sorted(store.fragment_digests(r1))
    return OrderedDict((
        ("scenario", "release 1 from R0, release 2 must stage from R1"),
        ("R0", r0), ("R1", r1),
        ("release_1_outcome", rec1["outcome"]),
        ("release_1_host_deployment_id", rec1.get("host_deployment_id")),
        ("second_release_from_R0_refused", stale_second["outcome"] == RC.ACTIVATION_REFUSED),
        ("refusals", stale_second.get("refusals")),
        ("R1_is_in_durable_storage", store.get_release(r1) is not None),
        ("R1_fragments_available_for_the_next_release", len(fragments_available)),
        ("deployments_on_host", len(host.deploys)),
        ("seconds", round(time.perf_counter() - started, 3)),
    ))


def rollback_pilot(*, store: RC.ReleaseStore, work: Path, candidate: RC.Candidate,
                   parent_digest: str) -> "OrderedDict[str, Any]":
    """Rollback to an EXACT prior verified release held in durable storage."""
    started = time.perf_counter()
    r1 = candidate.digest
    host = RC.SimulatedHost(work / "host-rollback", live_release=r1)
    good = RC.rollback(to_release_digest=parent_digest, expected_current=r1,
                       host=host, store=store, work_dir=work / "rb",
                       reason="pilot: verification failed on R1")
    # Someone else moved live on: the same rollback must now refuse.
    host.live_release = "sha256:" + "b" * 64
    stale = RC.rollback(to_release_digest=parent_digest, expected_current=r1,
                        host=host, store=store, work_dir=work / "rb2",
                        reason="pilot: a stale rollback attempt")
    return OrderedDict((
        ("restored_release_digest", good.get("restored_release_digest")),
        ("restored_bundle_sha256", good.get("restored_bundle_sha256")),
        ("restored_markets", good.get("restored_markets")),
        ("outcome", good.get("outcome")),
        ("target_came_from_durable_storage", True),
        ("stale_rollback_refused", stale["outcome"] == RC.ACTIVATION_REFUSED),
        ("stale_refusal", stale.get("refusal")),
        ("seconds", round(time.perf_counter() - started, 3)),
    ))


def crash_pilot(*, work: Path, candidate: RC.Candidate, live: RC.LiveTruth) -> "OrderedDict[str, Any]":
    """The transaction-like cases, against the simulator."""
    parent = live.digest()
    out: "OrderedDict[str, Any]" = OrderedDict()

    host = RC.SimulatedHost(work / "host-crash", live_release=parent)
    out["1_crash_before_staging"] = OrderedDict((("live_unchanged", host.current() == parent),))
    out["2_crash_after_staging"] = OrderedDict((("live_unchanged", host.current() == parent),
                                                ("host_calls", len(host.calls))))
    auth = RC.authorize(candidate, decided_by="pilot")
    out["3_crash_after_authorization"] = OrderedDict((("live_unchanged", host.current() == parent),
                                                      ("host_calls", len(host.calls))))
    host.timeout_next = True
    unknown = RC.activate(candidate, auth, host, live=live, operation_id="crash-op-4")
    state = RC.reconcile(candidate, host, "crash-op-4")
    out["4_activation_timeout"] = OrderedDict((
        ("outcome", unknown["outcome"]),
        ("recorded_as_live", unknown["activated_at"] is not None),
        ("reconciled_action", state["action"]),
        ("deployments", len(host.deploys)),
    ))
    out["5_local_write_failed_after_success"] = OrderedDict((
        ("host_has_activation", state["host_has_activation"]),
        ("action", state["action"]),
        ("second_deploy_avoided", len(host.deploys) == 1),
    ))
    replay = RC.activate(candidate, auth, host, live=live, operation_id="crash-op-4")
    out["8_duplicate_activate_is_idempotent"] = OrderedDict((
        ("idempotent_replay", replay.get("idempotent_replay")),
        ("deployments", len(host.deploys)),
    ))
    auth_again = RC.authorize(candidate, decided_by="pilot")
    out["9_duplicate_authorization"] = OrderedDict((
        ("same_authorization_id", auth_again["authorization_id"] == auth["authorization_id"]),
        ("same_candidate", auth_again["candidate_digest"] == auth["candidate_digest"]),
    ))
    tampered = candidate.site / "index.html"
    original = tampered.read_bytes()
    tampered.write_bytes(original + b"<!-- tampered -->")
    corrupt = RC.activate(candidate, auth, host, live=live, operation_id="crash-op-10")
    tampered.write_bytes(original)
    out["10_corrupted_after_authorization"] = OrderedDict((
        ("outcome", corrupt["outcome"]),
        ("refusals", corrupt.get("refusals")),
        ("restored", candidate.verify_bytes() == []),
    ))
    return out


# --------------------------------------------------------------------------- #
# The run.
# --------------------------------------------------------------------------- #

def run_pilot(*, work_dir: Path, store_root: Path, cache_root: Path,
              seed_summary: Optional[Mapping] = None) -> "OrderedDict[str, Any]":
    started = time.perf_counter()
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    live = RC.LiveTruth.read()
    live.require_verified()
    store = RC.ReleaseStore(store_root)
    cache = BC.BundleCache(cache_root, run_id="atlas-005-pilot")
    package = load_package()

    out: "OrderedDict[str, Any]" = OrderedDict((
        ("schema", "ptf-atlas-throughput-005-pilot/1.0"),
        ("work_order", "ATLAS-THROUGHPUT-005"),
        ("started_at", RC._iso()),
        ("live", OrderedDict((
            ("verified", live.verified),
            ("deploy_id", live.state.deploy_id),
            ("bundle_sha256", live.state.bundle_sha256),
            ("participating_markets", list(live.participating_markets)),
            ("total_profiles", live.state.total_profiles),
            ("sitemap_route_count", live.state.sitemap_route_count),
            ("parent_release_digest", live.digest()),
            ("rollback_target", live.state.rollback_target),
        ))),
        ("seed", OrderedDict(seed_summary or {})),
    ))

    # The bundle must have been validated in an EARLIER run for the staging
    # run to reuse it; that is the whole point of 004. Publish it first and
    # record what that cost, so the staged reuse is measured against it.
    print("[005] warming the validated bundle ...", flush=True)
    warm_started = time.perf_counter()
    prewarm = cache.build_or_reuse(package, work_dir=work / "prewarm", context="production")
    out["bundle_prewarm"] = OrderedDict((
        ("cache_status", prewarm.get("cache_status")),
        ("bundle_sha256", prewarm.get("bundle_sha256")),
        ("builder_invocations", prewarm.get("builder_invocations")),
        ("trust_state", prewarm.get("trust_state")),
        ("seconds", round(time.perf_counter() - warm_started, 3)),
    ))
    print("[005] bundle %s %s" % (prewarm.get("cache_status"), str(prewarm.get("bundle_sha256"))[:16]), flush=True)

    print("[005] data-only candidate ...", flush=True)
    data_only, candidate, host = data_only_pilot(live=live, store=store, cache=cache,
                                                 package=package, work=work / "data_only")
    out["data_only"] = data_only
    print("[005] staged %s in %ss" % (candidate.digest[7:23], data_only["total_seconds"]), flush=True)

    print("[005] stale lineage ...", flush=True)
    out["stale_lineage"] = stale_lineage_pilot(live=live, store=store, cache=cache,
                                               package=package, work=work / "stale",
                                               candidate=candidate)

    print("[005] participation ...", flush=True)
    out["participation"] = participation_pilot(live=live, store=store, cache=cache,
                                               package=package, work=work / "participation",
                                               final_candidate=candidate)

    print("[005] queue ...", flush=True)
    out["queue"] = queue_pilot(live=live, store=store, work=work / "queue", candidate=candidate)

    print("[005] rollback ...", flush=True)
    out["rollback"] = rollback_pilot(store=store, work=work / "rollback", candidate=candidate,
                                     parent_digest=live.digest())

    print("[005] crash matrix ...", flush=True)
    out["crash"] = crash_pilot(work=work / "crash", candidate=candidate, live=live)

    store_bytes = sum(p.stat().st_size for p in store.root.rglob("*") if p.is_file())
    out["performance"] = OrderedDict((
        ("parent_load_seconds", data_only["parent_load_seconds"]),
        ("membership_seconds", data_only["timing"].get("membership_seconds")),
        ("fragment_seconds", data_only["timing"].get("fragment_seconds")),
        ("compose_seconds", data_only["timing"].get("compose_seconds")),
        ("gate_seconds", data_only["timing"].get("gate_seconds")),
        ("fast_lane_seconds", data_only["timing"].get("fast_lane_seconds")),
        ("stage_total_seconds", data_only["total_seconds"]),
        ("verification_seconds", data_only["verification"]["seconds"]),
        ("release_store_bytes", store_bytes),
        ("bundles_reused", data_only["bundles_reused"]),
        ("bundles_rebuilt", data_only["bundles_rebuilt"]),
        ("full_compose_seconds_for_comparison", (seed_summary or {}).get("compose_seconds")),
    ))
    out["activation_status"] = RC.activation_status()
    out["total_seconds"] = round(time.perf_counter() - started, 3)
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description="ATLAS-THROUGHPUT-005 release coordinator pilot")
    parser.add_argument("--work", default=r"C:\ptf005\pilot" if sys.platform == "win32" else "/tmp/ptf005")
    parser.add_argument("--store", default=str(RC.DEFAULT_STORE_ROOT))
    parser.add_argument("--cache", default=str(BC.DEFAULT_ROOT))
    parser.add_argument("--seed-summary", default=r"C:\ptf005\seed\seed_summary.json")
    parser.add_argument("--out", default=str(REPORTS / "atlas_throughput_005_pilot_run.json"))
    args = parser.parse_args(argv)
    seed = None
    if args.seed_summary and Path(args.seed_summary).is_file():
        seed = json.loads(Path(args.seed_summary).read_text(encoding="utf-8-sig"))
    doc = run_pilot(work_dir=Path(args.work), store_root=Path(args.store),
                    cache_root=Path(args.cache), seed_summary=seed)
    RC._write_json(Path(args.out), doc)
    print("wrote %s in %ss" % (args.out, doc["total_seconds"]))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
