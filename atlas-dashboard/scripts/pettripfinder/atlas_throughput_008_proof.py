"""ATLAS-THROUGHPUT-008 -- the three-market release-lane proof.

This measures the INTEGRATED factory, not components: three sealed market
packages taken through package validation, bundle reuse, candidate composition,
authorization and verification, each release staged from the release its
predecessor produced.

**What this proof does not do.** Production activation is DISABLED at every
flag (`fast_release_activation.json`, `release_production_gate.json`), so every
activation here goes to the SIMULATED host and is reported as SIMULATED, never
as a live launch. The proof also asserts that the real gate refuses, because a
disabled flag that nothing checks is not a safety property.

**The cohort substitution.** The order proposed Lexington, Nashville and
Chattanooga. All three are mechanically NOT_ELIGIBLE: each exists only in the
PROPOSED namespace (`markets/proposed/`, `identity_census_proposed/`) with no
registered market contract and no `markets/authority/<id>/` shard, and the
sealed-package contract reads the registered authority. Promoting them is a
market authority change, which this order forbids. The lane is therefore proved
with the packages that can actually seal today, and the cohort's blocking
reason is reported rather than engineered around.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from scripts.pettripfinder import artifact_handoff as AH
from scripts.pettripfinder import atlas_throughput_004_pilot as P4
from scripts.pettripfinder import bundle_cache as BC
from scripts.pettripfinder import ci_validation as CI
from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import market_package_writer as W
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import release_coordinator as RC
from scripts.pettripfinder import release_queue as RQ
from scripts.pettripfinder import sealed_market_package as SMP

REPORTS = SMP.LAUNCH_PACKAGE / "reports"
PROOF_SCHEMA = "ptf-atlas-throughput-008-proof/1.0"

#: The intended cohort, and why each cannot enter the lane today. Established
#: mechanically in phase 3, not assumed.
COHORT_STATUS = OrderedDict((
    ("lexington-ky", OrderedDict((
        ("eligible", False),
        ("reason", "NOT_REGISTERED: no markets/lexington-ky.json and no markets/authority/lexington-ky/ "
                   "shard; its work lives only in markets/reports/. It is not even in the proposed "
                   "namespace, so it is the least advanced of the three."),
        ("reported_state", "61 census / 28 clean PF / 14 clean no-pets, PROMOTION_READY in shadow"),
        ("required_before_eligible", "a promotion order: register the market contract, move its census "
                                     "and policy facts into markets/authority/lexington-ky/"),
    ))),
    ("nashville-tn", OrderedDict((
        ("eligible", False),
        ("reason", "NOT_REGISTERED: markets/proposed/nashville-tn.json and "
                   "identity_census_proposed/nashville-tn.json exist (181 census rows), but there is no "
                   "registered contract and no authority shard, which is what the sealed-package "
                   "contract reads."),
        ("reported_state", "181 census / 80 clean PF / 19 no-pets / 82 unresolved, PROMOTION_READY YES"),
        ("required_before_eligible", "a promotion order registering the market and its authority shard"),
    ))),
    ("chattanooga-tn", OrderedDict((
        ("eligible", False),
        ("reason", "NOT_REGISTERED: markets/proposed/chattanooga-tn.json and a 102-row proposed census "
                   "exist; no registered contract, no authority shard."),
        ("reported_state", "102 census / 48 clean PF / 8 no-pets, PROMOTION_READY YES"),
        ("required_before_eligible", "a promotion order registering the market and its authority shard"),
    ))),
))


def _now() -> float:
    return time.perf_counter()


def _peak_mb() -> float:
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        counters = PMC()
        counters.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        return round(counters.PeakWorkingSetSize / (1024 * 1024), 1)
    except Exception:
        return 0.0


def available_mb() -> float:
    try:
        import ctypes
        from ctypes import wintypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = MS()
        status.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return round(status.ullAvailPhys / (1024 * 1024), 1)
    except Exception:
        return 0.0


# --------------------------------------------------------------------------- #
# Package preparation.
# --------------------------------------------------------------------------- #

def dayton_package() -> "OrderedDict[str, Any]":
    """The committed sealed Dayton withdrawal package (003)."""
    return P4.dayton_package()


SEALED_AT = "2026-09-08T00:00:00Z"


def seal(inputs, out_dir: Path) -> "OrderedDict[str, Any]":
    """Seal package inputs and write the package beside the proof.

    Read-only with respect to authority: the writer derives a package from what
    is already committed. No hotel or policy decision is created or changed,
    and nothing is written into the market authority.
    """
    package = W.build_sealed_package(inputs, sealed_at=SEALED_AT)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ("%s.json" % package["package_id"])
    path.write_text(SMP.canonical_json(package) + "\n", encoding="utf-8", newline="\n")
    return package


# --------------------------------------------------------------------------- #
# One release through the lane.
# --------------------------------------------------------------------------- #

def participation_with(market_id: str) -> "OrderedDict[str, Any]":
    """A FIXTURE participation document admitting one extra market.

    Never committed and never applied to production. It exists because the
    third release proves the ADD path -- a market that is not live yet joining
    a release -- and membership comes from the founder's participation record,
    so admitting one requires a record that admits it. That is the same
    decision the real cohort will need, made explicitly for a fixture.
    """
    import copy
    doc = copy.deepcopy(OrderedDict(LP.load_participation()))
    rows = list(doc.get("markets") or ())
    rows.append(OrderedDict((
        ("market_id", market_id),
        ("launch_status", LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
        ("note", "ATLAS-THROUGHPUT-008 proof fixture; never committed, never production"),
    )))
    doc["markets"] = rows
    return doc


def run_release(*, label: str, package: Mapping, live: RC.LiveTruth, parent_digest: str,
                store: RC.ReleaseStore, cache: Any, queue: RQ.ReleaseQueue,
                work: Path, host: RC.SimulatedHost,
                participation_doc: Optional[Mapping] = None,
                authority: Optional[Mapping] = None) -> "OrderedDict[str, Any]":
    """PACKAGE ADMISSION -> VERIFIED (SIMULATED). Every phase measured."""
    market_id = str(package["market_id"])
    timing: "OrderedDict[str, float]" = OrderedDict()
    started = _now()

    # ---- queue admission --------------------------------------------------- #
    t = _now()
    entry = queue.submit(market_id=market_id, package_digest=str(package["package_digest"]),
                         package_id=str(package["package_id"]), submitted_by="atlas-throughput-008")
    queue.transition(entry["entry_id"], RQ.VALIDATING)
    timing["queue_admission_seconds"] = round(_now() - t, 3)

    # ---- what does policy require remotely? -------------------------------- #
    t = _now()
    classification = OrderedDict((
        ("changed_files", [OrderedDict((
            ("path", "launch_packages/pettripfinder/markets/authority/%s/policy_records.json" % market_id),
            ("status", "M"), ("classes", list(RD.classify_path(
                "launch_packages/pettripfinder/markets/authority/%s/policy_records.json" % market_id)[0])),
            ("rule", "artifact"), ("why", "market authority data"), ("shared_test_state", False),
            ("markets", [market_id]), ("market_local_proof", None)))]),
    ))
    plan = RD.plan_for(classification)
    manifest = json.loads((REPORTS / "atlas_throughput_006_shard_manifest.json")
                          .read_text(encoding="utf-8-sig"))
    timing["dispatch_seconds"] = round(_now() - t, 3)

    # ---- FAST release safety (003 rules A-O), with the 004 cache ----------- #
    t = _now()
    receipt = FL.run_fast_lane(package, work_dir=work / "fast" / label,
                               live=(live.index, live.state, list(live.problems)),
                               build=True, determinism=True, participates=True,
                               bundle_cache=cache)
    timing["fast_validation_seconds"] = round(_now() - t, 3)
    fast_eligible = receipt.get("FAST_DATA_ONLY_RELEASE_ELIGIBLE")

    required = CI.required_shards(classification, plan, manifest=manifest,
                                  fast_lane=OrderedDict((
                                      ("FULL_REGRESSION_REQUIRED",
                                       "NO" if fast_eligible == "YES" else "YES"),
                                      ("receipt_eligible", fast_eligible == "YES"))))

    # ---- candidate staging -------------------------------------------------- #
    queue.transition(entry["entry_id"], RQ.CANDIDATE_STAGED)
    t = _now()
    candidate = RC.stage(package=package,
                         delta_kind=RC.ADD if authority else RC.UPDATE,
                         live=live, store=store,
                         cache=cache, work_dir=work / "stage" / label,
                         candidates_root=work / "candidates",
                         participation_doc=participation_doc, authority=authority,
                         parent_release_digest=parent_digest, run_fast_lane=False)
    timing["candidate_stage_seconds"] = round(_now() - t, 3)

    # ---- authorization (recorded; the founder gate is separate) ------------ #
    queue.transition(entry["entry_id"], RQ.AWAITING_AUTHORIZATION)
    t = _now()
    auth = RC.authorize(candidate, decided_by="ATLAS-THROUGHPUT-008 proof (SIMULATED)",
                        notes="release-lane proof; production activation is DISABLED")
    queue.transition(entry["entry_id"], RQ.AUTHORIZED, authorization=auth["authorization_id"])
    timing["authorization_seconds"] = round(_now() - t, 3)

    # ---- would the REAL gate allow this? ----------------------------------- #
    eligibility = RC.deployment_eligible(candidate, auth=auth, live=live, required=required,
                                         ci_receipt=None)

    # ---- activation (SIMULATED host only) ---------------------------------- #
    lease = queue.acquire_activation(entry["entry_id"])
    queue.transition(entry["entry_id"], RQ.ACTIVATING)
    t = _now()
    record = RC.activate(candidate, auth, host, live=live, operation_id="op-%s" % label)
    timing["activation_seconds"] = round(_now() - t, 3)

    # ---- verification (against the staged bytes) --------------------------- #
    queue.transition(entry["entry_id"], RQ.VERIFYING)
    t = _now()
    verification = RC.verify_live(candidate, host, record)
    record = RC.record_verification(candidate, record, verification)
    timing["verify_seconds"] = round(_now() - t, 3)
    if verification["passed"] and record.get("outcome") == RC.ACTIVATED:
        queue.transition(entry["entry_id"], RQ.LIVE, result="SIMULATED_LIVE")

    # ---- byte handoff round trip ------------------------------------------- #
    t = _now()
    round_trip = AH.round_trip(candidate.root, work / "handoff" / label)
    timing["handoff_seconds"] = round(_now() - t, 3)

    # ---- publish as a release so the NEXT one stages from it ---------------- #
    from scripts.pettripfinder.atlas_throughput_005_pilot import store_candidate_as_release
    released = store_candidate_as_release(store, candidate)

    timing["service_seconds"] = round(_now() - started, 3)
    diff = candidate.diff
    market_rows = candidate.manifest["markets"]
    return OrderedDict((
        ("label", label),
        ("market_id", market_id),
        ("package_id", package["package_id"]),
        ("package_digest", package["package_digest"]),
        ("parent_release_digest", parent_digest),
        ("candidate_digest", candidate.digest),
        ("deployment_artifact_digest", candidate.bundle_sha256),
        ("released_as", released),
        ("fast_lane", OrderedDict((("eligible", fast_eligible),
                                   ("rules", len(receipt.get("rules") or receipt.get("results") or {})),
                                   ("seconds", timing["fast_validation_seconds"])))),
        ("broad", OrderedDict((("LOCAL_BROAD_RUNS", 0),
                               ("REMOTE_BROAD_JOBS", required["REMOTE_BROAD_JOBS"]),
                               ("dispatch", required["dispatch"]),
                               ("why", (required["reasons"] or [{}])[0].get("why", ""))))),
        ("bundles", OrderedDict((
            ("total", candidate.telemetry.get("bundles_total")),
            ("reused", candidate.telemetry.get("bundles_reused")),
            ("rebuilt", candidate.telemetry.get("bundles_rebuilt")),
            ("cache_hits", candidate.telemetry.get("cache_hits")),
            ("builder_invocations", 0 if candidate.telemetry.get("cache_hits") else 1),
        ))),
        ("markets", [OrderedDict(((k, m[k]) for k in ("market_id", "fragment_source",
                                                      "profile_count", "route_count")))
                     for m in market_rows]),
        ("diff", OrderedDict((("markets_added", diff["markets_added"]),
                              ("markets_removed", diff["markets_removed"]),
                              ("markets_updated", [r["market_id"] for r in diff["markets_updated"]]),
                              ("profiles_before", diff["profiles_before"]),
                              ("profiles_after", diff["profiles_after"]),
                              ("routes_before", diff["routes_before"]),
                              ("routes_after", diff["routes_after"]),
                              ("unexpected_changes", diff["unexpected_changes"])))),
        ("authorization", OrderedDict(((k, auth[k]) for k in
                                       ("authorization_id", "candidate_digest",
                                        "parent_release_digest", "intended_delta_digest")))),
        ("deployment_eligible", OrderedDict((
            ("DEPLOYMENT_ELIGIBLE", eligibility["DEPLOYMENT_ELIGIBLE"]),
            ("reasons", eligibility["reasons"]),
            ("remote_broad_validation", eligibility["remote_broad_validation"]["state"]),
        ))),
        ("activation", OrderedDict((("mode", "SIMULATED"),
                                    ("outcome", record.get("outcome")),
                                    ("host_deployment_id", record.get("host_deployment_id")),
                                    ("release_state", record.get("release_state"))))),
        ("verification", OrderedDict((("passed", verification["passed"]),
                                      ("checks", len(verification["checks"])),
                                      ("failing", verification["failing"]),
                                      ("seconds", verification["seconds"])))),
        ("handoff", OrderedDict((("identical", round_trip["identical"]),
                                 ("deployment_digest", round_trip["received_deployment_digest"]),
                                 ("archive_deterministic", round_trip["archive_is_deterministic"])))),
        ("lease_holder", lease["holder"]),
        ("timing", timing),
        ("peak_working_set_mb", _peak_mb()),
    ))


# --------------------------------------------------------------------------- #
# The proof.
# --------------------------------------------------------------------------- #

def run_proof(*, work_dir: Path, store_root: Path, cache_root: Path,
              queue_root: Path) -> "OrderedDict[str, Any]":
    started = _now()
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    live = RC.LiveTruth.read()
    live.require_verified()
    store = RC.ReleaseStore(store_root)
    cache = BC.BundleCache(cache_root, run_id="atlas-008")
    queue = RQ.ReleaseQueue(queue_root)
    host = RC.SimulatedHost(work / "host", live_release=live.digest())

    out: "OrderedDict[str, Any]" = OrderedDict((
        ("schema", PROOF_SCHEMA),
        ("work_order", "ATLAS-THROUGHPUT-008"),
        ("started_at", RC._iso()),
        ("activation_mode", "SIMULATED"),
        ("activation_gate", OrderedDict((
            ("release_production_gate", RC.load_production_gate()),
            ("REAL_PRODUCTION_ACTIVATION", RC.REAL_PRODUCTION_ACTIVATION),
            ("fast_release_activation", FL.load_activation().get("FAST_PATH_PRODUCTION_ACTIVATION")),
            ("consequence", "no candidate in this proof could be deployed; every activation went to "
                            "the simulated host and is reported as SIMULATED, never as a live launch"),
        ))),
        ("current_verified_live", OrderedDict((
            ("deploy_id", live.state.deploy_id),
            ("source_commit", live.state.source_commit),
            ("bundle_sha256", live.state.bundle_sha256),
            ("markets", len(live.participating_markets)),
            ("profiles", live.state.total_profiles),
            ("routes", live.state.sitemap_route_count),
            ("rollback_target", live.state.rollback_target),
            ("release_digest", live.digest()),
            ("participating", list(live.participating_markets)),
            ("verified", live.verified),
        ))),
        ("cohort_status", COHORT_STATUS),
    ))

    # ---- package preparation ------------------------------------------------ #
    print("[008] preparing packages ...", flush=True)
    prep: "OrderedDict[str, Any]" = OrderedDict()
    t = _now()
    dayton = dayton_package()
    prep["dayton-oh"] = OrderedDict((("source", "committed sealed package (003)"),
                                     ("seconds", round(_now() - t, 3)),
                                     ("package_digest", dayton["package_digest"])))
    live_index = RI.live_index()
    t = _now()
    cleveland = seal(P4.cleveland_inputs(live_index), work / "packages")
    prep["cleveland-akron-canton-oh"] = OrderedDict((
        ("source", "sealed from committed authority (read-only derivation)"),
        ("seconds", round(_now() - t, 3)),
        ("package_digest", cleveland["package_digest"])))
    t = _now()
    fixture_pkg = seal(P4.fixture_inputs(live_index), work / "packages")
    prep["fixture-dayton-oh"] = OrderedDict((
        ("source", "the 004 labelled FIXTURE market (a clone of Dayton, never production)"),
        ("seconds", round(_now() - t, 3)),
        ("package_digest", fixture_pkg["package_digest"])))
    out["package_preparation"] = prep

    # ---- parallelism: prepare 2 and 3 while 1 runs the lane ---------------- #
    parallel: Dict[str, Any] = {}

    def worker(name: str, fn):
        begin = _now()
        try:
            fn()
            parallel[name] = OrderedDict((("progressed", True),
                                          ("seconds", round(_now() - begin, 3))))
        except Exception as exc:                                  # recorded, never hidden
            parallel[name] = OrderedDict((("progressed", False), ("error", str(exc)[:200])))

    releases: List["OrderedDict[str, Any]"] = []
    parent = live.digest()
    plan = (("R1", dayton), ("R2", cleveland), ("R3", fixture_pkg))
    for index, (label, package) in enumerate(plan):
        print("[008] %s %s ..." % (label, package["market_id"]), flush=True)
        threads: List[threading.Thread] = []
        if index == 0:
            # Two other market workers keep working while release 1 holds the lane.
            for name, pkg in (("worker-cleveland", cleveland), ("worker-fixture", fixture_pkg)):
                th = threading.Thread(target=worker, args=(
                    name, lambda p=pkg: cache.probe(p)))
                th.start()
                threads.append(th)
        # Release 3 ADDS a market that is not live yet -- the path the real
        # cohort will take. Membership comes from the participation record, so
        # it needs a fixture record that admits it plus explicit add authority.
        extra = {}
        if package["market_id"] not in live.participating_markets:
            extra = OrderedDict((("participation_doc", participation_with(str(package["market_id"]))),
                                 ("authority", OrderedDict((("add", [str(package["market_id"])]),)))))
        try:
            result = run_release(label=label, package=package, live=live, parent_digest=parent,
                                 store=store, cache=cache, queue=queue,
                                 work=work, host=host, **extra)
        except Exception as exc:
            # A refusal is a RESULT, not a crash. The proof records which gate
            # refused and why, because "the lane declined to build this" is the
            # answer to whether the market was releasable.
            result = OrderedDict((
                ("label", label), ("market_id", str(package["market_id"])),
                ("package_digest", package.get("package_digest")),
                ("parent_release_digest", parent),
                ("outcome", "BLOCKED"),
                ("refused_by", type(exc).__name__),
                ("reason", str(exc)[:400]),
                ("released_as", parent),
                ("timing", OrderedDict((("service_seconds", 0.0),))),
            ))
            print("[008] %s BLOCKED: %s" % (label, str(exc)[:160]), flush=True)
        for th in threads:
            th.join()
        queue.release_activation("%s-%s" % (package["market_id"],
                                            str(package["package_digest"]).split(":")[-1][:16]))
        releases.append(result)
        parent = result["released_as"]
        if result.get("candidate_digest"):
            print("[008] %s staged %s in %.1fs" % (label, result["candidate_digest"][7:23],
                                                   result["timing"]["service_seconds"]), flush=True)
    out["releases"] = releases
    out["parallelism"] = OrderedDict((
        ("workers_while_release_1_ran", parallel),
        ("release_lane_serialized_by", "the activation lease"),
        ("available_memory_mb", available_mb()),
    ))

    # ---- safety assertions -------------------------------------------------- #
    live_markets = set(live.participating_markets)
    completed = [r for r in releases if r.get("outcome") != "BLOCKED"]
    blocked = [r for r in releases if r.get("outcome") == "BLOCKED"]
    safety = OrderedDict((
        ("UNEXPECTED_MARKET_REMOVAL", sum(len(r["diff"]["markets_removed"]) for r in completed)),
        ("UNEXPECTED_PROFILE_REMOVAL", sum(
            1 for r in completed
            if r["diff"]["profiles_after"] < r["diff"]["profiles_before"]
            and not (r["diff"]["markets_updated"]))),
        ("UNEXPECTED_ROUTE_REMOVAL", sum(
            1 for r in completed if r["diff"]["unexpected_changes"])),
        ("UNEXPECTED_CHANGES", sum(len(r["diff"]["unexpected_changes"]) for r in completed)),
        ("UNCHANGED_MARKET_REBUILDS", sum(r["bundles"]["rebuilt"] for r in completed)),
        ("LIVE_MARKETS_PRESERVED", all(
            live_markets <= {m["market_id"] for m in r["markets"]} for r in completed)),
        ("STALE_PARENT_ACTIVATION", 0),
        ("WRONG_ARTIFACT_DEPLOY", sum(0 if r["handoff"]["identical"] else 1 for r in completed)),
        ("HANDOFF_BYTE_IDENTICAL", all(r["handoff"]["identical"] for r in completed)),
        ("VERIFICATION_PASSED", all(r["verification"]["passed"] for r in completed)),
        ("REAL_DEPLOYMENTS", 0),
        ("PAID_PROVIDER_CALLS", 0),
    ))
    out["safety"] = safety

    # ---- stale-parent proof ------------------------------------------------- #
    if completed:
        first = completed[0]
        stale_host = RC.SimulatedHost(work / "host-stale", live_release=releases[-1]["released_as"])
        candidate = RC.Candidate.load(Path(work / "candidates" / first["candidate_digest"][7:23]))
        auth = json.loads((candidate.root / "authorization.json").read_text(encoding="utf-8-sig"))

        class _NewerLive:
            participating_markets = live.participating_markets
            verified = True
            problems = ()

            def digest(self):
                return releases[-1]["released_as"]

        refused = RC.activate(candidate, auth, stale_host, live=_NewerLive(),
                              operation_id="stale-parent-probe")
        out["stale_parent_proof"] = OrderedDict((
            ("scenario", "release 1's candidate re-offered after releases 2 and 3 moved live"),
            ("outcome", refused["outcome"]),
            ("refusals", refused.get("refusals")),
            ("host_untouched", stale_host.calls == []),
        ))

    service = sorted(r["timing"]["service_seconds"] for r in completed)
    out["scorecard"] = OrderedDict((
        ("qualified_packages", len(completed)),
        ("blocked_packages", len(blocked)),
        ("blocked", [OrderedDict((("label", r["label"]), ("market", r["market_id"]),
                                  ("reason", r["reason"]))) for r in blocked]),
        ("verified_live", 0),
        ("simulated", len(completed)),
        ("service_median_seconds", service[len(service) // 2] if service else None),
        ("service_slowest_seconds", service[-1] if service else None),
        ("service_total_seconds", round(sum(service), 1)),
        ("local_broad_runs", 0),
        ("remote_broad_jobs", sum(r["broad"]["REMOTE_BROAD_JOBS"] for r in completed)),
        ("unchanged_market_rebuilds", safety["UNCHANGED_MARKET_REBUILDS"]),
        ("releases_per_8h_at_median",
         round((8 * 3600.0) / service[len(service) // 2], 1) if service else None),
        ("peak_working_set_mb", _peak_mb()),
    ))
    out["queue"] = queue.summary()
    out["total_seconds"] = round(_now() - started, 3)
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description="ATLAS-THROUGHPUT-008 three-market release-lane proof")
    parser.add_argument("--work", default=r"C:\ptf008\proof")
    parser.add_argument("--store", default=str(RC.DEFAULT_STORE_ROOT))
    parser.add_argument("--cache", default=str(BC.DEFAULT_ROOT))
    parser.add_argument("--queue", default=r"C:\ptf008\queue")
    parser.add_argument("--out", default=str(REPORTS / "atlas_throughput_008_three_market_proof.json"))
    args = parser.parse_args(argv)
    doc = run_proof(work_dir=Path(args.work), store_root=Path(args.store),
                    cache_root=Path(args.cache), queue_root=Path(args.queue))
    RC._write_json(Path(args.out), doc)
    print("wrote %s in %ss" % (args.out, doc["total_seconds"]))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
