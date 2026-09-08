"""ATLAS-THROUGHPUT-004 -- persistent bundle cache pilot: cold -> warm across
processes, targeted invalidation, concurrency, multi-market reuse, benchmark.

Pilot inputs (frozen, non-production):
  A  dayton-oh              the committed 003 sealed package (ELIGIBLE = YES)
  B  cleveland-akron-canton-oh  the live authority sealed as a frozen copy
                             (edge cases: dash-spelled artifact hashes, four
                             ROUTING_RETIRED rows outside the census, two
                             committed partitions, 120 profiles)
  C  fixture-dayton-oh      a FIXTURE: Dayton's frozen authority under a
                             fictitious market id with every identity renamed,
                             so three markets exist for the multi-market proof
                             while only two live markets seal today

Nothing here touches committed authority; every build goes to short scratch
paths (Windows limits a path to 260 characters and a profile route is ~90).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from scripts.pettripfinder import atlas_throughput_003_pilot as P3
from scripts.pettripfinder import bundle_cache as BC
from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import market_package_writer as W
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.markets.contract import slugify
from scripts.pettripfinder.site_data import normalize_name

REPO_ROOT = SMP.REPO_ROOT
REPORTS = SMP.LAUNCH_PACKAGE / "reports"
FIXTURE_ID = "fixture-dayton-oh"
FIXTURE_SUFFIX = " Fixture"


# --------------------------------------------------------------------------- #
# Inputs.
# --------------------------------------------------------------------------- #

def dayton_package() -> "OrderedDict[str, Any]":
    return SMP.read_sealed(SMP.list_packages("dayton-oh")[-1])


def cleveland_inputs(live) -> W.PackageInputs:
    return P3.frozen_inputs("cleveland-akron-canton-oh", live)


def fixture_inputs(live, *, market_id: str = FIXTURE_ID, suffix: str = FIXTURE_SUFFIX) -> W.PackageInputs:
    """Dayton's frozen authority as a fictitious market: every identity,
    corridor and route renamed consistently; evidence untouched."""
    inp = P3.frozen_inputs("dayton-oh", live)
    old_id = "dayton-oh"

    def rename(name: str) -> str:
        return name + suffix

    market = json.loads(json.dumps(inp.market), object_pairs_hook=OrderedDict)
    market["market_id"] = market_id
    market["market_slug"] = market_id
    market["market_name"] = market["market_name"] + suffix
    market["title"] = market["title"].replace("Dayton", "Dayton" + suffix, 1)
    for corridor in market["corridors"]:
        corridor["corridor_id"] = corridor["corridor_id"].replace(old_id + "__", market_id + "__", 1)
        corridor["market_id"] = market_id
        for key in ("explicit_hotel_ids",):
            if corridor.get(key):
                corridor[key] = [normalize_name(rename(n)) if False else n for n in corridor[key]]
    census = json.loads(json.dumps(inp.census), object_pairs_hook=OrderedDict)
    census["market_id"] = market_id
    for row in census["hotels"]:
        name = rename(str(row["canonical_name"]))
        row["canonical_name"] = name
        row["display_name"] = name
        row["identity_key"] = ptf_identity_key(name)
        row["normalized_name"] = normalize_name(name)
        row["slug"] = slugify(name)
        row["market_id"] = market_id
        if row.get("corridor"):
            row["corridor"] = row["corridor"].replace(old_id + "__", market_id + "__", 1)
    records = []
    for r in inp.pet_friendly_records:
        rec = json.loads(json.dumps(r), object_pairs_hook=OrderedDict)
        name = rename(str(rec["name"]))
        rec["name"] = name
        rec["key"] = normalize_name(name)
        rec["identity_key"] = ptf_identity_key(name)
        rec["market_id"] = market_id
        if rec.get("corridor"):
            rec["corridor"] = rec["corridor"].replace(old_id + "__", market_id + "__", 1)
        records.append(rec)
    exclusions = []
    for e in inp.verified_no_pets_records:
        ex = json.loads(json.dumps(e), object_pairs_hook=OrderedDict)
        name = rename(str(ex["canonical_name"]))
        ex["canonical_name"] = name
        ex["normalized_name"] = normalize_name(name)
        ex["exclusion_id"] = ex["exclusion_id"] + "-fixture"
        ex["market_id"] = market_id
        ex["record_hash"] = HE.record_hash(ex)
        ex["approval_hash"] = HE.approval_hash(ex)
        exclusions.append(ex)
    routes = []
    for r in inp.official_routes:
        route = json.loads(json.dumps(r), object_pairs_hook=OrderedDict)
        ref = route["hotel_ref"]
        name = rename(str(ref["canonical_name"]))
        ref["canonical_name"] = name
        ref["normalized_name"] = normalize_name(name)
        if "identity_key" in ref:
            ref["identity_key"] = ptf_identity_key(name)
        ref["market_id"] = market_id
        route["market_id"] = market_id
        route["routing_id"] = route["routing_id"] + "-fixture"
        routes.append(route)
    seed = []
    for s in inp.seed_rows:
        row = OrderedDict(s)
        row["name"] = rename(str(row["name"]))
        row["market_id"] = market_id
        seed.append(row)
    partition = json.loads(json.dumps(inp.partition), object_pairs_hook=OrderedDict)
    partition["market_id"] = market_id
    for item in partition["items"]:
        name = rename(str(item["canonical_name"]))
        item["canonical_name"] = name
        item["identity_key"] = ptf_identity_key(name)
        item["slug"] = slugify(name)
    delta = P3.zero_delta(market_id)
    delta["add_property_ids"] = sorted(r["identity_key"] for r in records)
    delta["expected_profile_delta"] = len(records)
    delta["expected_market_count_delta"] = 1
    delta["expected_participation_delta"] = [OrderedDict((("market_id", market_id), ("from", False), ("to", True)))]
    delta["expected_verified_no_pets_delta"] = len(exclusions)
    return W.PackageInputs(
        market_id=market_id, execution_zone=SMP.ZONE_FROZEN_COPY, created_from_source_sha=inp.created_from_source_sha,
        market=market, census=census, pet_friendly_records=records, verified_no_pets_records=exclusions,
        official_routes=routes, seed_rows=seed, partition=partition, intended_delta=delta,
        parent_live_state=inp.parent_live_state,
        dependency_input_digests=OrderedDict(inp.dependency_input_digests, fixture_of="sha256:" + "0" * 64),
        founder_holds=[OrderedDict((("hold_id", "fixture"), ("reason", "a FIXTURE market cloned from dayton-oh for the "
                                                                          "ATLAS-THROUGHPUT-004 multi-market proof; never a "
                                                                          "real market"), ("blocks_promotion", True)))],
    )


def mutate_policy(inputs: W.PackageInputs) -> W.PackageInputs:
    """One record's pet fee moves by a dollar (a policy change)."""
    out = copy.deepcopy(inputs)
    for r in out.pet_friendly_records:
        fee = (r.get("facts") or {}).get("pet_fee")
        if isinstance(fee, Mapping) and isinstance(fee.get("amount_cents"), int):
            fee["amount_cents"] = int(fee["amount_cents"]) + 100
            break
    return out


def mutate_route(inputs: W.PackageInputs) -> W.PackageInputs:
    """A corridor's public slug changes (a route change)."""
    out = copy.deepcopy(inputs)
    market = json.loads(json.dumps(out.market), object_pairs_hook=OrderedDict)
    market["corridors"][0]["slug"] = market["corridors"][0]["slug"] + "-x"
    out.market = market
    return out


def mutate_geography(inputs: W.PackageInputs) -> W.PackageInputs:
    """A corridor's display name changes (geography / identity)."""
    out = copy.deepcopy(inputs)
    market = json.loads(json.dumps(out.market), object_pairs_hook=OrderedDict)
    market["corridors"][0]["name"] = market["corridors"][0]["name"] + " Extended"
    out.market = market
    return out


# --------------------------------------------------------------------------- #
# A shadow repository root for closure mutations.
# --------------------------------------------------------------------------- #

def shadow_repo(target: Path, closure: Mapping, market_ids: Sequence[str]) -> Path:
    """A copy of exactly the declared closure (plus the staging inputs), so a
    template / builder / tooling mutation can be made without touching the
    real tree. Code still imports from the real tree; only the KEY changes."""
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    rels = list(closure["shared_data_inputs"]) + list(closure["code_modules"])
    rels += ["requirements.txt", "requirements-dev.txt", "launch_packages/pettripfinder/identity_resolutions.json"]
    rels += ["launch_packages/pettripfinder/markets/authority/%s/affiliate_destinations.json" % m for m in market_ids]
    rels += [p.relative_to(REPO_ROOT).as_posix() for p in (REPO_ROOT / "deploy" / "netlify" / "release_contracts").glob("*.json")]
    rels += [p.relative_to(REPO_ROOT).as_posix() for p in (REPO_ROOT / "launch_packages" / "pettripfinder" / "markets").glob("*.json")]
    for rel in sorted(set(rels)):
        src = REPO_ROOT / rel
        if src.is_file():
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    # A market-local tooling helper that is NOT in the closure.
    tooling = target / "scripts" / "pettripfinder" / "dayton_oh_revalidation_999.py"
    tooling.write_text("# offline acquisition helper; not on the build path\n", encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# Runs.
# --------------------------------------------------------------------------- #

WARM_CHILD = r'''
import json, os, sys, time
sys.path.insert(0, %(repo)r)
from pathlib import Path
from scripts.pettripfinder import bundle_cache as BC, sealed_market_package as SMP
os.environ["PTF_BUNDLE_CACHE_FORBID_BUILD"] = "1"
pkg = SMP.read_sealed(Path(%(package)r))
cache = BC.BundleCache(Path(%(root)r), run_id=%(run)r, repo_root=Path(%(repo_root)r))
started = time.perf_counter()
try:
    r = cache.build_or_reuse(pkg, work_dir=Path(%(work)r))
    r["child_total_seconds"] = round(time.perf_counter() - started, 3)
    print(json.dumps({k: v for k, v in r.items() if k != "determinism"}, default=str))
except BC.BuildForbidden as exc:
    print(json.dumps({"cache_status": "MISS", "build_forbidden": True, "why": str(exc),
                      "child_total_seconds": round(time.perf_counter() - started, 3)}))
'''


def warm_in_new_process(package_path: Path, root: Path, work: Path, run_id: str,
                        repo_root: Path = REPO_ROOT) -> "OrderedDict[str, Any]":
    code = WARM_CHILD % {"repo": str(REPO_ROOT), "package": str(package_path), "root": str(root),
                         "run": run_id, "work": str(work), "repo_root": str(repo_root)}
    started = time.perf_counter()
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(REPO_ROOT))
    seconds = round(time.perf_counter() - started, 3)
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    try:
        doc = json.loads(line, object_pairs_hook=OrderedDict)
    except ValueError:
        doc = OrderedDict((("cache_status", "ERROR"), ("stderr", proc.stderr[-600:]), ("stdout", proc.stdout[-300:])))
    doc["process_seconds"] = seconds
    doc["separate_process"] = True
    return doc


def _seal_to(inputs: W.PackageInputs, directory: Path) -> Path:
    package = W.build_sealed_package(inputs, sealed_at="2026-09-08T00:00:00Z")
    return SMP.write_sealed(package, directory)


def stub_builder(sleep: float = 0.5):
    """A fake builder for the concurrency proof: writes a tiny site and
    returns the same shape the real one does."""
    from scripts.pettripfinder.assemble_production_site import bundle_digest, file_hashes
    calls: List[float] = []
    spans: List[List[float]] = []
    lock = threading.Lock()

    def build(package, stage_root, output_root, *, context="production", cold=True, repo_root=None):
        with lock:
            calls.append(time.time())
            span = [time.time(), None]
            spans.append(span)
        time.sleep(sleep)
        span[1] = time.time()
        site = Path(output_root) / "site"
        if site.exists():
            shutil.rmtree(site)
        site.mkdir(parents=True)
        (site / "index.html").write_text("<html>%s</html>" % package["package_id"], encoding="utf-8")
        (site / "sitemap.xml").write_text("<urlset/>", encoding="utf-8")
        hashes = file_hashes(site)
        return OrderedDict((("market_id", package["market_id"]), ("package_id", package["package_id"]),
                            ("context", context), ("cold", cold), ("staged_files", {}),
                            ("staged_input_digest", "sha256:" + "1" * 64), ("contract_sha256", "sha256:" + "2" * 64),
                            ("bundle_sha256", bundle_digest(hashes)), ("file_count", len(hashes)),
                            ("html_count", 1), ("release_name", "stub"), ("gates_failing", []),
                            ("cache_events", [OrderedDict((("verdict", "BUILD_EXECUTED"), ("assembly_kind", "market_bundle"),
                                                           ("input_key", "stub"), ("seconds", sleep)))]),
                            ("seconds", sleep)))
    build.calls = calls
    build.spans = spans
    return build


def concurrency_proof(root: Path, work: Path, packages: Sequence[Mapping]) -> "OrderedDict[str, Any]":
    """Two same-key requests: one build, one hit after waiting. Different
    keys: both build."""
    if root.exists():
        shutil.rmtree(root)
    cache = BC.BundleCache(root, run_id="concurrency")
    builder = stub_builder(sleep=1.0)
    results: Dict[str, Any] = {}

    def request(label, package):
        results[label] = cache.build_or_reuse(package, work_dir=work / label, require_determinism=False, builder=builder)

    a1 = threading.Thread(target=request, args=("same-1", packages[0]))
    a2 = threading.Thread(target=request, args=("same-2", packages[0]))
    a1.start(); time.sleep(0.05); a2.start(); a1.join(); a2.join()
    same_statuses = sorted(results[k]["cache_status"] for k in ("same-1", "same-2"))
    same_builds = len(builder.calls)
    builder2 = stub_builder(sleep=1.0)
    started = time.perf_counter()
    b1 = threading.Thread(target=lambda: results.__setitem__("diff-1", cache.build_or_reuse(
        packages[1], work_dir=work / "diff-1", require_determinism=False, builder=builder2)))
    b2 = threading.Thread(target=lambda: results.__setitem__("diff-2", cache.build_or_reuse(
        packages[2], work_dir=work / "diff-2", require_determinism=False, builder=builder2)))
    b1.start(); b2.start(); b1.join(); b2.join()
    diff_seconds = round(time.perf_counter() - started, 3)
    spans = sorted(builder2.spans)
    overlapped = len(spans) == 2 and spans[1][0] < spans[0][1]      # the second build began before the first ended
    return OrderedDict((
        ("same_key", OrderedDict((("statuses", same_statuses), ("BUILD_EXECUTED", same_builds),
                                  ("REUSE_AFTER_WAIT", same_statuses.count(BC.HIT_AFTER_WAIT)),
                                  ("digests_equal", results["same-1"]["bundle_sha256"] == results["same-2"]["bundle_sha256"])))),
        ("different_keys", OrderedDict((("statuses", [results["diff-1"]["cache_status"], results["diff-2"]["cache_status"]]),
                                        ("BUILD_EXECUTED", len(builder2.calls)),
                                        ("wall_seconds_for_two_1s_builds", diff_seconds),
                                        ("concurrent", overlapped)))),
    ))


def run_pilot(*, work_dir: Path, cache_root: Path) -> "OrderedDict[str, Any]":
    from scripts.pettripfinder.throughput_profile import peak_working_set_mb
    started = time.perf_counter()
    work = Path(work_dir)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if Path(cache_root).exists():
        shutil.rmtree(cache_root)
    report: "OrderedDict[str, Any]" = OrderedDict((("schema", "ptf-atlas-throughput-004-pilot/1.0"),
                                                   ("cache_root", str(cache_root)), ("packages", OrderedDict())))
    live = RI.live_index()
    packages_dir = work / "packages"
    a_path = SMP.write_sealed(dayton_package(), packages_dir)
    b_path = _seal_to(cleveland_inputs(live), packages_dir)
    c_path = _seal_to(fixture_inputs(live), packages_dir)
    for label, path in (("A_dayton", a_path), ("B_cleveland", b_path), ("C_fixture", c_path)):
        pkg = SMP.read_sealed(path)
        report["packages"][label] = OrderedDict((("package_id", pkg["package_id"]), ("market_id", pkg["market_id"]),
                                                 ("path", str(path)), ("published", pkg["coverage_scorecard"]["published_pet_friendly"])))
    cache = BC.BundleCache(cache_root, run_id="pilot-cold")
    closure = cache.closure

    # ---- Phase 18: cold in this process, warm in a NEW process ------------ #
    cold_warm: "OrderedDict[str, Any]" = OrderedDict()
    for label, path in (("A_dayton", a_path), ("B_cleveland", b_path), ("C_fixture", c_path)):
        pkg = SMP.read_sealed(path)
        cold = cache.build_or_reuse(pkg, work_dir=work / ("cold_" + label[0]))
        warm = warm_in_new_process(path, cache_root, work / ("warm_" + label[0]), "pilot-warm")
        same = (warm.get("bundle_sha256") == cold["bundle_sha256"])
        cold_warm[label] = OrderedDict((
            ("build_input_key", cold["build_input_key"]),
            ("RUN_1_COLD", OrderedDict((("cache_status", cold["cache_status"]), ("BUILD_EXECUTED", cold["builder_invocations"]),
                                        ("TRUSTED_CACHE_PUBLISHED", 1 if cold["trust_state"] == BC.TRUSTED else 0),
                                        ("bundle_sha256", cold["bundle_sha256"]), ("file_count", cold["file_count"]),
                                        ("build_seconds", cold["build_seconds"]), ("determinism", cold["determinism"]),
                                        ("publish_seconds", cold["publish_seconds"]), ("total_seconds", cold["total_seconds"]),
                                        ("undeclared_dependencies", cold["undeclared_dependencies"])))),
            ("RUN_2_WARM_SEPARATE_PROCESS", OrderedDict((("cache_status", warm.get("cache_status")),
                                                         ("BUILD_EXECUTED", warm.get("builder_invocations", "n/a")),
                                                         ("PERSISTENT_CACHE_HIT", 1 if warm.get("cache_status") == BC.HIT else 0),
                                                         ("bundle_sha256", warm.get("bundle_sha256")),
                                                         ("output_identical", same), ("receipt_digest", warm.get("receipt_digest")),
                                                         ("lookup_seconds", warm.get("lookup_seconds")),
                                                         ("verify_seconds", warm.get("verify_seconds")),
                                                         ("manifest_seconds", warm.get("manifest_seconds")),
                                                         ("total_seconds_in_child", warm.get("total_seconds")),
                                                         ("process_wall_seconds", warm.get("process_seconds")),
                                                         ("bytes_reused", warm.get("bytes_reused"))))),
        ))
    report["cold_warm"] = cold_warm

    # ---- Phase 19: targeted invalidation (builds forbidden) ---------------- #
    shadow = shadow_repo(work / "shadow", closure, ["dayton-oh", "cleveland-akron-canton-oh", FIXTURE_ID])
    matrix: List["OrderedDict[str, Any]"] = []

    def probe(label, expected, package_path, repo_root=REPO_ROOT, mutate_shadow=None, cache_root_override=None, **kw):
        if mutate_shadow:
            mutate_shadow(shadow)
        outcome = warm_in_new_process(package_path, cache_root_override or cache_root, work / ("inv_" + label), "inv-" + label,
                                      repo_root=repo_root)
        actual = outcome.get("cache_status")
        row = OrderedDict((("case", label), ("expected", expected), ("actual", actual),
                           ("match", actual == expected), ("seconds", outcome.get("process_seconds")),
                           ("why", outcome.get("why") or outcome.get("stderr") or "")))
        matrix.append(row)
        return row

    dayton_inputs = P3.frozen_inputs("dayton-oh", live)
    probe("baseline_unchanged", BC.HIT, a_path)
    probe("policy_mutation", BC.MISS, _seal_to(P3.withdrawal_inputs(live, withdraw_pf=P3.DAYTON_WITHDRAW_PET_FRIENDLY[:3],
                                                                    withdraw_np=()), work / "pk_policy"))
    probe("route_mutation", BC.MISS, _seal_to(mutate_route(dayton_inputs), work / "pk_route"))
    probe("geography_mutation", BC.MISS, _seal_to(mutate_geography(dayton_inputs), work / "pk_geo"))
    probe("shadow_repo_unchanged", BC.HIT, a_path, repo_root=shadow)

    def touch_css(root):
        p = root / "scripts" / "pettripfinder" / "approved_hotel_profile.css"
        p.write_text(p.read_text(encoding="utf-8") + "\n/* template mutation */\n", encoding="utf-8")
    probe("template_mutation", BC.MISS, a_path, repo_root=shadow, mutate_shadow=touch_css)
    shadow_repo(work / "shadow", closure, ["dayton-oh", "cleveland-akron-canton-oh", FIXTURE_ID])

    def touch_builder(root):
        p = root / "scripts" / "generate_pettripfinder_columbus_site.py"
        p.write_text(p.read_text(encoding="utf-8") + "\n# builder mutation\n", encoding="utf-8")
    probe("builder_mutation", BC.MISS, a_path, repo_root=shadow, mutate_shadow=touch_builder)
    shadow_repo(work / "shadow", closure, ["dayton-oh", "cleveland-akron-canton-oh", FIXTURE_ID])

    def touch_runtime(root):
        p = root / "scripts" / "pettripfinder" / "site_pages.py"
        p.write_text(p.read_text(encoding="utf-8") + "\n# shared runtime mutation\n", encoding="utf-8")
    probe("shared_runtime_mutation", BC.MISS, a_path, repo_root=shadow, mutate_shadow=touch_runtime)
    shadow_repo(work / "shadow", closure, ["dayton-oh", "cleveland-akron-canton-oh", FIXTURE_ID])

    def touch_tooling(root):
        p = root / "scripts" / "pettripfinder" / "dayton_oh_revalidation_999.py"
        p.write_text(p.read_text(encoding="utf-8") + "\n# market-local tooling mutation\n", encoding="utf-8")
    probe("market_tooling_only_mutation", BC.HIT, a_path, repo_root=shadow, mutate_shadow=touch_tooling)

    def touch_lockfile(root):
        p = root / "requirements.txt"
        p.write_text(p.read_text(encoding="utf-8") + "\n# lockfile mutation\n", encoding="utf-8")
    probe("lockfile_mutation", BC.MISS, a_path, repo_root=shadow, mutate_shadow=touch_lockfile)
    shadow_repo(work / "shadow", closure, ["dayton-oh", "cleveland-akron-canton-oh", FIXTURE_ID])

    # validation-policy change: compatible => REVALIDATE (bytes reused). On a
    # COPY of the cache: the probe legitimately rewrites the entry's receipt
    # under the bumped policy, which would then read as incompatible to the
    # rest of this pilot (the pilot runs under the current policy).
    reval_root = work / "reval_cache"
    if reval_root.exists():
        shutil.rmtree(reval_root)
    shutil.copytree(cache_root, reval_root)
    reval = _revalidation_probe(a_path, reval_root, work / "inv_policy_version")
    matrix.append(reval)
    # corruption family, on a copy of the cache
    corrupt_root = work / "corrupt_cache"
    for label, expected, damage in (
            ("corrupt_artifact", BC.MISS, "flip"), ("missing_artifact", BC.MISS, "delete"),
            ("zero_byte_artifact", BC.MISS, "zero"), ("missing_receipt", BC.MISS, "receipt"),
            ("wrong_receipt", BC.MISS, "receipt_other"), ("malformed_metadata", BC.MISS, "index")):
        if corrupt_root.exists():
            shutil.rmtree(corrupt_root)
        shutil.copytree(cache_root, corrupt_root)
        _damage(corrupt_root, cold_warm["A_dayton"]["build_input_key"], damage)
        probe(label, expected, a_path, cache_root_override=corrupt_root)
    # revoked entry and revoked evidence
    if corrupt_root.exists():
        shutil.rmtree(corrupt_root)
    shutil.copytree(cache_root, corrupt_root)
    BC.BundleCache(corrupt_root, run_id="rev").revoke(cold_warm["A_dayton"]["build_input_key"], "pilot revocation")
    probe("revoked_entry", BC.MISS, a_path, cache_root_override=corrupt_root)
    report["invalidation_matrix"] = matrix

    # ---- Phase 10: concurrency ------------------------------------------- #
    report["concurrency"] = concurrency_proof(work / "conc_cache", work / "conc_work",
                                              [SMP.read_sealed(a_path), SMP.read_sealed(b_path), SMP.read_sealed(c_path)])

    # ---- Phase 20: multi-market reuse ------------------------------------ #
    changed_b = _seal_to(mutate_policy(cleveland_inputs(live)), work / "pk_b_changed")
    multi = OrderedDict()
    t = time.perf_counter()
    cache2 = BC.BundleCache(cache_root, run_id="pilot-multi")
    for label, path in (("A_cleveland_changed", changed_b), ("B_dayton_unchanged", a_path), ("C_fixture_unchanged", c_path)):
        pkg = SMP.read_sealed(path)
        r = cache2.build_or_reuse(pkg, work_dir=work / ("multi_" + label[0]))
        multi[label] = OrderedDict((("cache_status", r["cache_status"]), ("builder_invocations", r["builder_invocations"]),
                                    ("bundle_sha256", r["bundle_sha256"]), ("total_seconds", r["total_seconds"]),
                                    ("trust_state", r.get("trust_state", BC.TRUSTED))))
    multi["total_seconds"] = round(time.perf_counter() - t, 3)
    # then a shared template change: every bundle misses (builds forbidden => proven without building)
    touch_css(shadow)
    after = OrderedDict()
    for label, path in (("A", changed_b), ("B", a_path), ("C", c_path)):
        o = warm_in_new_process(path, cache_root, work / ("multi_tpl_" + label), "tpl-" + label, repo_root=shadow)
        after[label] = o.get("cache_status")
    multi["after_shared_template_change"] = after
    report["multi_market"] = multi

    # ---- retention dry run ------------------------------------------------ #
    live_digests = [m.package_id for m in live[0].markets.values()]  # placeholders: no committed bundle digests yet
    report["gc_dry_run"] = cache2.gc_plan(max_age_days=90, protected_digests=[cold_warm["A_dayton"]["RUN_1_COLD"]["bundle_sha256"]])
    report["gc_dry_run"].pop("rows", None)

    # ---- benchmark --------------------------------------------------------- #
    a = cold_warm["A_dayton"]
    b = cold_warm["B_cleveland"]
    disk = sum(p.stat().st_size for p in Path(cache_root).rglob("*") if p.is_file())
    report["benchmark"] = OrderedDict((
        ("COLD_BUILD_TIME_s", OrderedDict((("dayton", a["RUN_1_COLD"]["build_seconds"]), ("cleveland", b["RUN_1_COLD"]["build_seconds"])))),
        ("DETERMINISM_SECOND_BUILD_s", OrderedDict((("dayton", a["RUN_1_COLD"]["determinism"].get("seconds")),
                                                    ("cleveland", b["RUN_1_COLD"]["determinism"].get("seconds"))))),
        ("WARM_CACHE_LOOKUP_TIME_s", OrderedDict((("dayton", a["RUN_2_WARM_SEPARATE_PROCESS"]["lookup_seconds"]),
                                                  ("cleveland", b["RUN_2_WARM_SEPARATE_PROCESS"]["lookup_seconds"])))),
        ("ARTIFACT_HASH_VERIFICATION_TIME_s", OrderedDict((("dayton", a["RUN_2_WARM_SEPARATE_PROCESS"]["verify_seconds"]),
                                                           ("cleveland", b["RUN_2_WARM_SEPARATE_PROCESS"]["verify_seconds"])))),
        ("CACHE_INDEX_LOOKUP_TIME_s", "included in lookup (one JSON read)"),
        ("MANIFEST_TIME_s", OrderedDict((("dayton", a["RUN_2_WARM_SEPARATE_PROCESS"]["manifest_seconds"]),
                                         ("cleveland", b["RUN_2_WARM_SEPARATE_PROCESS"]["manifest_seconds"])))),
        ("WARM_TOTAL_IN_PROCESS_s", OrderedDict((("dayton", a["RUN_2_WARM_SEPARATE_PROCESS"]["total_seconds_in_child"]),
                                                 ("cleveland", b["RUN_2_WARM_SEPARATE_PROCESS"]["total_seconds_in_child"])))),
        ("WARM_PROCESS_WALL_s", OrderedDict((("dayton", a["RUN_2_WARM_SEPARATE_PROCESS"]["process_wall_seconds"]),
                                             ("cleveland", b["RUN_2_WARM_SEPARATE_PROCESS"]["process_wall_seconds"])))),
        ("REVALIDATION_ONLY_TIME_s", reval.get("seconds")),
        ("CACHE_PUBLICATION_TIME_s", OrderedDict((("dayton", a["RUN_1_COLD"]["publish_seconds"]), ("cleveland", b["RUN_1_COLD"]["publish_seconds"])))),
        ("BYTES_REUSED", OrderedDict((("dayton", a["RUN_2_WARM_SEPARATE_PROCESS"]["bytes_reused"]),
                                      ("cleveland", b["RUN_2_WARM_SEPARATE_PROCESS"]["bytes_reused"])))),
        ("DISK_SPACE_BYTES", disk),
        ("PEAK_MEMORY_MB_pilot_process", peak_working_set_mb()),
        ("BUILD_EXECUTIONS_AVOIDED", sum(1 for e in BC.EVENTS if e["cache_status"] in (BC.HIT, BC.HIT_AFTER_WAIT))),
        ("multi_market_release", OrderedDict((("MARKETS", 3), ("COLD_BUILDS", sum(1 for k, v in multi.items() if isinstance(v, Mapping) and v.get("cache_status") == BC.MISS)),
                                              ("CACHE_HITS", sum(1 for k, v in multi.items() if isinstance(v, Mapping) and v.get("cache_status") == BC.HIT)),
                                              ("REVALIDATIONS", 0), ("GLOBAL_REBUILDS", "not in scope (005): the whole-site compose"),
                                              ("TOTAL_TIME_s", multi["total_seconds"])))),
    ))
    report["telemetry"] = BC.summary()
    report["total_seconds"] = round(time.perf_counter() - started, 3)
    return report


def _revalidation_probe(package_path: Path, cache_root: Path, work: Path) -> "OrderedDict[str, Any]":
    """A validation-policy bump under a compatible policy: bytes reused, a new
    receipt, no build."""
    code = r'''
import json, os, sys, time
sys.path.insert(0, %(repo)r)
from pathlib import Path
from scripts.pettripfinder import bundle_cache as BC, sealed_market_package as SMP
os.environ["PTF_BUNDLE_CACHE_FORBID_BUILD"] = "1"
BC.COMPATIBLE_POLICIES = (BC.VALIDATION_POLICY, "ptf-bundle-validation/1.1")
BC.VALIDATION_POLICY = "ptf-bundle-validation/1.1"
pkg = SMP.read_sealed(Path(%(package)r))
cache = BC.BundleCache(Path(%(root)r), run_id="reval")
t = time.perf_counter()
r = cache.build_or_reuse(pkg, work_dir=Path(%(work)r))
print(json.dumps({"cache_status": r["cache_status"], "seconds": round(time.perf_counter() - t, 3),
                  "builder_invocations": r.get("builder_invocations"), "trust_state": r.get("trust_state"),
                  "receipt_digest": r.get("receipt_digest")}))
r2 = cache.build_or_reuse(pkg, work_dir=Path(%(work)r) / "again")
print(json.dumps({"cache_status": r2["cache_status"]}))
'''
    proc = subprocess.run([sys.executable, "-c", code % {"repo": str(REPO_ROOT), "package": str(package_path),
                                                          "root": str(cache_root), "work": str(work)}],
                          capture_output=True, text=True, cwd=str(REPO_ROOT))
    lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    first = json.loads(lines[0]) if lines else {"cache_status": "ERROR", "why": proc.stderr[-400:]}
    second = json.loads(lines[1]) if len(lines) > 1 else {}
    return OrderedDict((("case", "validation_policy_version_change_compatible"), ("expected", BC.REVALIDATE),
                        ("actual", first.get("cache_status")), ("match", first.get("cache_status") == BC.REVALIDATE),
                        ("seconds", first.get("seconds")), ("builder_invocations", first.get("builder_invocations")),
                        ("then_hit_under_new_policy", second.get("cache_status")),
                        ("why", first.get("why", ""))))


def _damage(root: Path, key: str, kind: str) -> None:
    cache = BC.BundleCache(root, run_id="damage")
    entry = cache.read_entry(key)
    archive = cache.object_path(entry["output_bundle_digest"])
    if kind == "flip":
        data = bytearray(archive.read_bytes())
        data[len(data) // 2] ^= 0xFF
        archive.write_bytes(bytes(data))
    elif kind == "delete":
        archive.unlink()
    elif kind == "zero":
        archive.write_bytes(b"")
    elif kind == "receipt":
        cache.receipt_path(entry["validation_receipt_digest"]).unlink()
    elif kind == "receipt_other":
        # A receipt for another bundle, planted under this entry's digest.
        receipt = cache.read_receipt(entry["validation_receipt_digest"])
        receipt["output_bundle_digest"] = "sha256:" + "f" * 64
        cache.receipt_path(entry["validation_receipt_digest"]).write_text(json.dumps(receipt), encoding="utf-8")
    elif kind == "index":
        cache.index_path(key).write_text("{not json", encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report = run_pilot(work_dir=Path(args.work_dir), cache_root=Path(args.cache_root))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
    for label, cw in report["cold_warm"].items():
        print(label, "cold", cw["RUN_1_COLD"]["cache_status"], cw["RUN_1_COLD"]["BUILD_EXECUTED"], cw["RUN_1_COLD"]["TRUSTED_CACHE_PUBLISHED"],
              "| warm", cw["RUN_2_WARM_SEPARATE_PROCESS"]["cache_status"], cw["RUN_2_WARM_SEPARATE_PROCESS"]["BUILD_EXECUTED"],
              cw["RUN_2_WARM_SEPARATE_PROCESS"]["output_identical"], cw["RUN_2_WARM_SEPARATE_PROCESS"]["total_seconds_in_child"])
    for row in report["invalidation_matrix"]:
        print("inv", row["case"], row["expected"], row["actual"], "OK" if row["match"] else "MISMATCH")
    print("concurrency", json.dumps(report["concurrency"]))
    print("multi", json.dumps({k: (v["cache_status"] if isinstance(v, dict) and "cache_status" in v else v) for k, v in report["multi_market"].items()}))
    print("total", report["total_seconds"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
