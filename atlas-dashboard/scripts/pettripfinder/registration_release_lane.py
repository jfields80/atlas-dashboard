"""PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 -- the generic registration
release lane: seal the registering market, prove it on the FAST lane, commit
the package and the receipt where Regression V2 reads them, and -- once the
classifier has answered -- prepare the UNSIGNED authorization-readiness packet.

    python -m scripts.pettripfinder.registration_release_lane register --market <id> --work-order <ORDER>
    python -m scripts.pettripfinder.registration_release_lane seal --market <id> --work-order <ORDER>
    python -m scripts.pettripfinder.regression_delta classify --base <sha> --out <classify.json>
    python -m scripts.pettripfinder.registration_release_lane packet --market <id> \
        --classification <classify.json>

PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001 added ``register`` and
the market-state block to ``seal``, so that the whole registration transaction
-- shard, globals, contract, participation row, build closure, package,
receipt, PIN BLOCK -- is ordinary generic commands and no fresh market has to
write a participation helper that imports the assembler, or hand-edit a test
expectation to be classified. ``register`` reissues the participation record
with ONE row at SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH (the chain
extended, the writer named, the founder never), and declares the market's two
build-closure inputs. ``seal --work-order`` writes the market's block into
``tests/pettripfinder/pins/market_state.json`` from the SEALED PACKAGE, and
refuses unless the release contract states the same eight numbers; the
registration proof then holds that block to the package independently.

WHY THIS IS GENERIC
-------------------
Every market so far carried its own release-lane script (charlotte_nc_release_
lane_005, nashville_tn_release_lane_003, ...). Each sealed the package in
memory, ran rules A-O, and embedded the receipt in a report -- so nothing under
``markets/packages/<market>/`` or ``markets/receipts/<market>/`` existed for a
classifier to find, and the registration could not be proven data-only from
the change set alone. This lane writes both, in the market's own zone
(MARKET_DATA_PACKAGE, a narrow companion), so ``regression_delta classify``
can bind the registration to a sealed package and an eligible receipt without
being told anything.

WHAT ``seal`` PROVES
--------------------
    PACKAGE_REPRODUCIBLE      the package is sealed TWICE from the committed
                              authority; the two digests must be equal
    FAST rules A-O            15/15 PASS, 0 UNKNOWN, 0 FAILED, or the lane
                              reports NOT ELIGIBLE and exits non-zero
    CANDIDATE_REPRODUCIBLE    rule K's two COLD builds of the joining market
                              produced one bundle digest, and the composed
                              release index (live parent + package) is the same
                              digest when composed a second time
    UNCHANGED_MARKETS_REBUILT 0 -- the lane renders the joining market only

Nothing here deploys, nothing flips participation, nothing enables activation.

WHAT ``packet`` WRITES
----------------------
A prepared, UNSIGNED readiness document under ``markets/reports/`` -- never
under ``deploy/netlify/deployment_authorizations/``, because a file there IS
an authorization and only a founder creates one. It binds the parent release,
the package, the receipt, the intended delta and the expected candidate index,
and it records the classifier's verdict. ``authorized_by`` and
``authorized_at`` are null and stay null.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import fast_release_lane as FL         # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB      # noqa: E402
from scripts.pettripfinder import market_package_writer as W      # noqa: E402
from scripts.pettripfinder import release_index as RI             # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP    # noqa: E402
from scripts.pettripfinder.markets.contract import parse_market   # noqa: E402

LANE_SCHEMA = "ptf-registration-release-lane/1.0"
READINESS_SCHEMA = "ptf-registration-authorization-readiness/1.0"
REPORTS = SMP.LAUNCH_PACKAGE / "markets" / "reports"


def _write(path: Path, doc: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parent_from_live(live) -> "OrderedDict[str, Any]":
    idx, state, _problems = live
    doc = state.to_dict()
    parent = OrderedDict((k, doc[k]) for k in ("live_deploy_id", "rollback_target", "source_commit",
                                               "participating_markets", "profile_counts",
                                               "total_profiles", "sitemap_route_count"))
    parent["live_index_digest"] = idx.digest()
    return parent


def joining_delta(inputs: W.PackageInputs) -> "OrderedDict[str, Any]":
    """A market that JOINS, and nothing else moves. Property-level fields are
    empty and the profile delta is zero on purpose: ``release_index.compare``
    measures those WITHIN a market live on both sides, and a joining market is
    on neither. The join is declared by ``expected_market_count_delta`` and
    ``expected_participation_delta``; the surface it brings is declared route
    by route in ``add_routes``, derived by the same functions the release index
    uses, so the declaration and the measurement cannot drift apart."""
    market = parse_market(dict(inputs.market))
    profiles = RI._entries(market, inputs.pet_friendly_records, inputs.seed_rows)
    routes = sorted({p.route for p in profiles.values()}
                    | set(RI.published_corridor_routes(market, profiles, inputs.seed_rows))
                    | {RI.market_route(market)})
    return OrderedDict((
        ("market_id", inputs.market_id),
        ("add_property_ids", []),
        ("update_property_ids", []),
        ("remove_property_ids", []),
        ("add_routes", routes),
        ("change_routes", []),
        ("remove_routes", []),
        ("expected_profile_delta", 0),
        ("expected_verified_no_pets_delta", 0),
        ("expected_market_count_delta", 1),
        ("expected_participation_delta", [OrderedDict((
            ("market_id", inputs.market_id), ("from", False), ("to", True)))]),
        ("joining_market_profiles", len(inputs.pet_friendly_records)),
        ("joining_market_verified_no_pets", len(inputs.verified_no_pets_records)),
    ))


PIN_PATH = _DASH / "tests" / "pettripfinder" / "pins" / "market_state.json"
CLOSURE_PATH = SMP.LAUNCH_PACKAGE / "bundle_cache_closure.json"
_WORK_ORDER = re.compile(r"^PTF-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}[A-Z]?$")


def _require_work_order(work_order: str) -> str:
    if not _WORK_ORDER.match(work_order or ""):
        raise SystemExit("--work-order %r is not a work-order id (PTF-...-NNN)" % (work_order,))
    return work_order


def pin_block_from_package(package: Mapping, market_id: str, work_order: str) -> "OrderedDict[str, Any]":
    """The market-state block the sealed package derives, cross-held to the
    release contract's own reconciliation: the two must agree or nothing is
    written. Import is local so the lane never loads the classifier's proof
    unless it writes a pin."""
    from scripts.pettripfinder import registration_data_only as REG
    from scripts.pettripfinder import release_contracts as RC
    block = REG.expected_pin_block(package)
    contract = RC.load_contract(market_id)
    rec = contract.get("reconciliation") or {}
    stated = OrderedDict((
        ("census", (contract.get("identity_census") or {}).get("expected_count")),
        ("pet_friendly", rec.get("published_pet_friendly")),
        ("verified_no_pets", rec.get("verified_no_pets")),
        ("resolved", rec.get("resolved")), ("unresolved", rec.get("unresolved")),
        ("profiles", (contract.get("public_surface") or {}).get("public_hotel_profile_count")),
        ("corridor_routes", (contract.get("routes") or {}).get("published_corridor_route_count")),
    ))
    disagreements = [k for k, v in stated.items() if v != block.get(k)]
    if disagreements:
        raise SystemExit("the release contract and the sealed package disagree on %s: contract %s, package %s"
                         % (disagreements, {k: stated[k] for k in disagreements}, {k: block[k] for k in disagreements}))
    block["last_moved_by"] = work_order
    return block


def write_pin_block(market_id: str, block: Mapping, work_order: str, pin_path: Optional[Path] = None) -> str:
    """Add ONE market block to the reviewed pin; refuse to move an existing one."""
    path = pin_path or PIN_PATH
    doc = _read(path)
    if market_id in (doc.get("markets") or {}):
        raise SystemExit("%s is already pinned; a registration adds a block and never moves one" % market_id)
    doc["reviewed_by"] = work_order
    markets: "OrderedDict[str, Any]" = OrderedDict()
    for key in sorted(list(doc["markets"]) + [market_id]):
        markets[key] = OrderedDict(block) if key == market_id else doc["markets"][key]
    doc["markets"] = markets
    _write(path, doc)
    return "pinned %s: census %s / pet-friendly %s / verified-no-pets %s / corridor routes %s" % (
        market_id, block["census"], block["pet_friendly"], block["verified_no_pets"], block["corridor_routes"])


def register(market_id: str, *, work_order: str, out: Path, decided_on: Optional[str] = None) -> Dict:
    """Participation row + build closure for a registered, releasable, NOT
    authorized market. Refuses if the market has no shard or contract, if it
    already has a row, or if the reissued record fails the chain contract."""
    from scripts.pettripfinder import launch_participation as LP
    from scripts.pettripfinder import release_contracts as RC
    from scripts.pettripfinder.market_authority import load_markets, sharded_market_ids
    _require_work_order(work_order)
    if market_id not in {m.market_id for m in load_markets()}:
        raise SystemExit("%s is not registered (no launch_packages/pettripfinder/markets/%s.json)" % (market_id, market_id))
    if market_id not in sharded_market_ids():
        raise SystemExit("%s has no authority shard; run market_registration_cli --write first" % market_id)
    contract = RC.load_contract(market_id)
    rec = contract.get("reconciliation") or {}
    disagreements = RC.contract_disagreements(contract, RC.derive_authority(market_id))
    if disagreements:
        raise SystemExit("the release contract disagrees with the derived authority: %s" % disagreements[:3])
    # PTF-FINAL-ASSEMBLER-REGISTERED-MARKET-DISCOVERY-001: a registering
    # market's partition must be owned by its contract, or the whole-site
    # assembler cannot see it. The resolver is the assembler's own lookup;
    # refusing here is what keeps a new market off the frozen legacy table.
    from scripts.pettripfinder import market_partition_resolution as MPR
    try:
        partition = MPR.resolve_registered_market_partition(market_id)
    except MPR.PartitionResolutionError as exc:
        raise SystemExit("the market's partition is not owned by its registration: %s" % exc)
    if partition.source != MPR.SOURCE_CONTRACT and market_id not in MPR.LEGACY_MARKET_IDS:
        raise SystemExit("%s resolved its partition by %s; a registering market must reference it in its "
                         "release contract" % (market_id, partition.source))

    path = LP.PARTICIPATION_PATH
    prior = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
    prior_sha = LP.participation_sha256(path)
    before = sorted(LP.authorized_market_ids(prior))
    if any(m["market_id"] == market_id for m in prior["markets"]):
        raise SystemExit("%s already has a participation row; a registration adds one and never rewrites it" % market_id)
    row = OrderedDict((
        ("market_id", market_id),
        ("launch_status", LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH),
        ("note", "Registered by %s: %s registered identities, %s published pet-friendly, %s verified-no-pets. "
                 "Source-ready and awaiting a founder launch decision."
                 % (work_order, (contract.get("identity_census") or {}).get("expected_count"),
                    rec.get("published_pet_friendly"), rec.get("verified_no_pets"))),
    ))
    doc = json.loads(json.dumps(prior), object_pairs_hook=OrderedDict)
    doc["markets"] = sorted(list(doc["markets"]) + [row], key=lambda m: m["market_id"])
    doc["decision"] = LP.extend_decision(
        prior, prior_sha, work_order=work_order, decided_by=work_order,
        decided_on=decided_on or time.strftime("%Y-%m-%d", time.gmtime()),
        reason="%s is registered, releasable and NOT authorized. This write records that third fact explicitly so "
               "the market is not merely absent from the participation document, which the assembler and the "
               "composition contract both read as UNLISTED. The founder-authorized set is unchanged; the "
               "founder's %s decision, if it comes, is a separate write." % (market_id, market_id),
        path=path, markets_added=[market_id], founder_authorized_set_unchanged=True)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    # Validate the bytes this WOULD write (the record on disk is the
    # predecessor, which the new block names as its newest ancestor).
    scratch = path.with_name(path.name + ".candidate")
    try:
        scratch.write_text(text, encoding="utf-8", newline="\n")
        problems = LP.decision_problems(doc, path=scratch)
    finally:
        if scratch.exists():
            scratch.unlink()
    if problems:
        raise SystemExit("the reissued participation record fails its chain contract: %s" % problems[:3])
    path.write_text(text, encoding="utf-8", newline="\n")
    after = sorted(LP.authorized_market_ids(LP.load_participation()))
    if after != before:
        raise SystemExit("the founder-authorized set moved: %s -> %s" % (before, after))

    closure = _read(CLOSURE_PATH)
    inputs = ("deploy/netlify/release_contracts/%s.json" % market_id,
              "launch_packages/pettripfinder/markets/%s.json" % market_id)
    for rel in inputs:
        if not (_DASH / rel).is_file():
            raise SystemExit("declared input does not exist: %s" % rel)
    shared = list(closure["shared_data_inputs"])
    added = [rel for rel in inputs if rel not in shared]
    if added:
        closure["shared_data_inputs"] = sorted(shared + added)
        closure["remeasured_by"] = list(closure.get("remeasured_by") or []) + [
            "%s: the closure enumerates every REGISTERED market's market document and release contract by "
            "name, so registering %s extends it by exactly two paths. Until they are declared the bundle "
            "cache calls them undeclared reads and publishes every bundle UNTRUSTED. That is the guard "
            "working; an unlisted input is an input nobody proved constant." % (work_order, market_id)]
        _write(CLOSURE_PATH, closure)
    report = OrderedDict((
        ("schema", "ptf-registration-participation/1.0"),
        ("work_order", work_order), ("market_id", market_id), ("as_of", _now()),
        ("participation", OrderedDict((
            ("row", row), ("prior_sha256", prior_sha), ("new_sha256", LP.participation_sha256(path)),
            ("founder_authorized_before", before), ("founder_authorized_after", after),
            ("founder_authorized_set_unchanged", before == after),
            ("decision_chain_records", len((doc["decision"].get("lineage") or {}).get("records") or ())),
            ("decision_problems", problems)))),
        ("build_closure", OrderedDict((("inputs_declared", list(inputs)), ("inputs_added", added)))),
        ("partition_resolution", partition.as_row()),
        ("nothing_deployed", True), ("nothing_authorized", True),
    ))
    _write(out, report)
    print("participation  :", row["launch_status"], "| authorized set unchanged:", before == after)
    print("build closure  : added", added or "nothing (already declared)")
    print("written        :", out.relative_to(_DASH).as_posix() if str(out).startswith(str(_DASH)) else out)
    return report


def seal(market_id: str, *, sealed_at: str, work_dir: Path, out: Path,
         paid_reservations: Optional[Mapping[str, Mapping]] = None,
         packages_dir: Optional[Path] = None, receipts_dir: Optional[Path] = None,
         work_order: Optional[str] = None, pin_path: Optional[Path] = None) -> Dict:
    timings: "OrderedDict[str, float]" = OrderedDict()
    t0 = time.monotonic()

    t = time.monotonic()
    live = RI.live_index()
    idx, state, problems = live
    timings["live_parent_read_s"] = round(time.monotonic() - t, 2)
    if problems:
        raise SystemExit("CURRENT_VERIFIED_LIVE could not be established: %s" % problems[:3])
    if market_id in state.participating_markets:
        raise SystemExit("%s already participates in the live release; this lane registers a joining market" % market_id)
    parent = parent_from_live(live)

    t = time.monotonic()
    inputs = W.inputs_from_committed_market(
        market_id, execution_zone=SMP.ZONE_REGISTERED_LIVE,
        intended_delta=OrderedDict((("market_id", market_id),)), parent_live_state=parent)
    inputs.intended_delta = joining_delta(inputs)
    inputs.paid_reservations = dict(paid_reservations or {})
    timings["package_inputs_s"] = round(time.monotonic() - t, 2)

    t = time.monotonic()
    package = W.build_sealed_package(inputs, sealed_at=sealed_at)
    again = W.build_sealed_package(inputs, sealed_at=sealed_at)
    package_reproducible = package["package_digest"] == again["package_digest"]
    timings["package_seal_x2_s"] = round(time.monotonic() - t, 2)
    if not package_reproducible:
        raise SystemExit("PACKAGE_REPRODUCIBLE = NO: %s vs %s" % (package["package_digest"], again["package_digest"]))
    package_path = SMP.write_sealed(package, packages_dir)

    t = time.monotonic()
    gate = FPB.evaluate_package(package)
    timings["first_party_gate_s"] = round(time.monotonic() - t, 2)

    t = time.monotonic()
    receipt = FL.run_fast_lane(package, work_dir=work_dir, live=live, participates=True)
    timings["fast_lane_s"] = round(time.monotonic() - t, 2)
    receipt_path = FL.write_receipt(receipt, receipts_dir)

    t = time.monotonic()
    package_index = RI.index_from_package(package, participating=True)
    candidate = RI.compose(idx, package_index, participates=True)
    candidate_again = RI.compose(idx, RI.index_from_package(package, participating=True), participates=True)
    diff = RI.compare(idx, candidate, package_market=market_id, intended_delta=package["intended_delta"])
    timings["candidate_compose_x2_s"] = round(time.monotonic() - t, 2)
    artifacts = receipt.get("ARTIFACT_DIGESTS") or {}
    bundle_a, bundle_b = artifacts.get("changed_market_bundle_sha256_a"), artifacts.get("changed_market_bundle_sha256_b")
    candidate_reproducible = bool(bundle_a) and bundle_a == bundle_b and candidate.digest() == candidate_again.digest()
    timings["total_s"] = round(time.monotonic() - t0, 2)

    eligible = receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES
    rel = lambda p: Path(p).relative_to(_DASH).as_posix() if str(p).startswith(str(_DASH)) else str(p)  # noqa: E731

    # PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001: the market-state
    # block, written by the transaction from the sealed package and held to
    # the release contract. Only for an ELIGIBLE, reproducible seal.
    pin_written = None
    if work_order and eligible and candidate_reproducible:
        t = time.monotonic()
        block = pin_block_from_package(package, market_id, _require_work_order(work_order))
        pin_written = write_pin_block(market_id, block, work_order, pin_path)
        timings["market_state_pin_s"] = round(time.monotonic() - t, 2)
        timings["total_s"] = round(time.monotonic() - t0, 2)
    doc = OrderedDict((
        ("schema", LANE_SCHEMA),
        ("market_id", market_id),
        ("as_of", _now()),
        ("nothing_deployed", True),
        ("nothing_activated", True),
        ("participation_untouched", True),
        ("parent_live_state", parent),
        ("sealed_package", OrderedDict((
            ("package_id", package["package_id"]), ("package_digest", package["package_digest"]),
            ("path", rel(package_path)), ("sealed_at", package.get("sealed_at")),
            ("created_from_source_sha", package.get("created_from_source_sha")),
            ("pet_friendly_records", len(package.get("pet_friendly_records") or [])),
            ("verified_no_pets_records", len(package.get("verified_no_pets_records") or [])),
            ("census_count", (package.get("census") or {}).get("count")),
            ("unresolved_rows", len(package.get("unresolved_rows") or [])),
            ("declared_routes", len(package["intended_delta"].get("add_routes") or [])),
        ))),
        ("PACKAGE_REPRODUCIBLE", "YES" if package_reproducible else "NO"),
        ("first_party_gate", OrderedDict((("records_evaluated", gate["records_evaluated"]),
                                          ("eligible", gate["eligible"]), ("ineligible", gate["ineligible"]),
                                          ("passed", gate["passed"])))),
        ("fast_lane_receipt", OrderedDict((
            ("path", rel(receipt_path)), ("receipt_digest", receipt["RECEIPT_DIGEST"]),
            ("eligible", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
            ("rules", OrderedDict((r, res["status"]) for r, res in receipt["RESULTS"].items())),
            ("rules_passed", sum(1 for res in receipt["RESULTS"].values() if res["status"] == FL.PASS)),
            ("unknown_rules", receipt["UNKNOWN_RULES"]), ("failed_rules", receipt["FAILED_RULES"]),
            ("determinism_result", receipt["DETERMINISM_RESULT"]),
            ("changed_market_bundle_sha256", bundle_a),
            ("fast_lane_seconds", receipt["PERFORMANCE"]["total_seconds"]),
        ))),
        ("candidate", OrderedDict((
            ("candidate_index_digest", candidate.digest()),
            ("recomposed_index_digest", candidate_again.digest()),
            ("markets", len(candidate.participating)), ("profiles", candidate.total_profiles),
            ("routes", len({r for i in candidate.markets.values() if i.participating for r in i.routes})),
            ("release_diff_passed", diff["passed"]), ("finding_counts", diff["finding_counts"]),
        ))),
        ("CANDIDATE_REPRODUCIBLE", "YES" if candidate_reproducible else "NO"),
        ("UNCHANGED_MARKETS_REBUILT", 0),
        ("unchanged_markets", list(parent["participating_markets"])),
        ("market_state_pin", OrderedDict((("written", pin_written is not None), ("work_order", work_order),
                                          ("result", pin_written)))),
        ("timings", timings),
    ))
    _write(out, doc)
    if pin_written:
        print("market state   :", pin_written)
    print("package        :", package["package_id"], "reproducible", doc["PACKAGE_REPRODUCIBLE"])
    print("fast lane      :", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"], "| rules passed",
          doc["fast_lane_receipt"]["rules_passed"], "| unknown", receipt["UNKNOWN_RULES"],
          "| failed", receipt["FAILED_RULES"], "| %.1fs" % timings["fast_lane_s"])
    print("candidate      :", doc["candidate"]["markets"], "markets /", doc["candidate"]["profiles"],
          "profiles /", doc["candidate"]["routes"], "routes; reproducible", doc["CANDIDATE_REPRODUCIBLE"])
    print("receipt        :", rel(receipt_path))
    print("written        :", rel(out), "| total %.1fs" % timings["total_s"])
    if not eligible or not candidate_reproducible:
        raise SystemExit(1)
    return doc


def packet(market_id: str, *, classification_path: Path, lane_report: Path, out: Path,
           prepared_by: str) -> Dict:
    classification = _read(classification_path)
    plan = classification.get("plan") or {}
    proof = classification.get("new_market_registration_data_only") or {}
    lane = _read(lane_report) if lane_report.is_file() else {}
    ready = (proof.get("ELIGIBLE") == "YES" and plan.get("NEW_MARKET_REGISTRATION_DATA_ONLY") == "YES"
             and classification.get("FULL_REGRESSION_REQUIRED") == "NO"
             and proof.get("market_id") == market_id)
    checks = OrderedDict((name, c.get("status")) for name, c in (proof.get("checks") or {}).items())
    expected = proof.get("expected_release") or {}
    doc = OrderedDict((
        ("schema", READINESS_SCHEMA),
        ("status", "AUTHORIZATION_READY" if ready else "NOT_AUTHORIZATION_READY"),
        ("founder_status", "AWAITING_FOUNDER_AUTHORIZATION"),
        ("what_this_is", "A prepared, UNSIGNED readiness document for founder review, written by the "
                         "registration release lane after Regression V2 classified the registration. It "
                         "authorizes nothing: no launch-participation flag has moved, no activation flag is "
                         "enabled, nothing is deployed. The founder's decision, if it comes, is a separate "
                         "write into deploy/netlify/deployment_authorizations/ that this document never makes."),
        ("market_id", market_id),
        ("prepared_by", prepared_by),
        ("prepared_at", _now()),
        ("authorized_by", None),
        ("authorized_at", None),
        ("regression_v2", OrderedDict((
            ("base", classification.get("base_sha")), ("head", classification.get("head_sha")),
            ("change_classes", classification.get("change_classes")),
            ("release_surfaces", classification.get("release_surfaces")),
            ("CHANGE_CLASS", (proof.get("CHANGE_CLASS") or "NEW_MARKET_REGISTRATION_DATA_ONLY") if ready
             else "/".join(classification.get("change_classes") or [])),
            ("FULL_REGRESSION_REQUIRED", classification.get("FULL_REGRESSION_REQUIRED")),
            ("REMOTE_BROAD_JOBS_REQUIRED", plan.get("REMOTE_BROAD_JOBS_REQUIRED")),
            ("plan_modules", plan.get("module_count")), ("assembly_required", plan.get("assembly_required")),
            ("reason", classification.get("full_regression_reason")),
        ))),
        ("registration_proof", OrderedDict((
            ("proof_version", proof.get("proof_version")), ("ELIGIBLE", proof.get("ELIGIBLE")),
            ("checks", checks), ("seconds", proof.get("seconds")),
        ))),
        ("the_digests_this_readiness_binds", OrderedDict((
            ("parent_live_deploy_id", proof.get("live_deploy_id")),
            ("parent_release_digest", (lane.get("parent_live_state") or {}).get("live_index_digest")),
            ("sealed_package_id", proof.get("package_id")),
            ("sealed_package_digest", proof.get("package_digest")),
            ("fast_receipt", proof.get("receipt")),
            ("fast_receipt_digest", (lane.get("fast_lane_receipt") or {}).get("receipt_digest")),
            ("changed_market_bundle_sha256", (lane.get("fast_lane_receipt") or {}).get("changed_market_bundle_sha256")),
            ("expected_candidate_index_digest", expected.get("expected_digest")),
            ("actual_candidate_index_digest", expected.get("actual_digest")),
        ))),
        ("projected_live", OrderedDict((
            ("markets", expected.get("actual_markets")), ("profiles", expected.get("actual_profiles")),
            ("routes", expected.get("actual_routes")),
            ("unexpected_market_changes", expected.get("unexpected_market_changes")),
            ("unexpected_profile_changes", expected.get("unexpected_profile_changes")),
            ("unexpected_route_changes", expected.get("unexpected_route_changes")),
        ))),
        ("lane", OrderedDict((
            ("PACKAGE_REPRODUCIBLE", lane.get("PACKAGE_REPRODUCIBLE")),
            ("CANDIDATE_REPRODUCIBLE", lane.get("CANDIDATE_REPRODUCIBLE")),
            ("UNCHANGED_MARKETS_REBUILT", lane.get("UNCHANGED_MARKETS_REBUILT")),
            ("fast_rules_passed", (lane.get("fast_lane_receipt") or {}).get("rules_passed")),
        ))),
        ("what_is_not_claimed", [
            "This document authorizes nothing. Only a founder authorization in "
            "deploy/netlify/deployment_authorizations/ admits a market to production.",
            "The whole-site deployment artifact is built and hashed by the deployment order, under the "
            "current-parent guard, the exact-bytes rule and the rollback guard, none of which this lane touches.",
            "The registration's participation row reads SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH.",
        ]),
    ))
    _write(out, doc)
    print("status         :", doc["status"], "| founder:", doc["founder_status"])
    print("change class   :", doc["regression_v2"]["CHANGE_CLASS"], "| broad:", doc["regression_v2"]["FULL_REGRESSION_REQUIRED"],
          "| remote broad jobs:", doc["regression_v2"]["REMOTE_BROAD_JOBS_REQUIRED"])
    print("written        :", out.relative_to(_DASH).as_posix() if str(out).startswith(str(_DASH)) else out)
    if not ready:
        raise SystemExit(1)
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("seal", help="seal the market, run the FAST lane, write package + receipt")
    s.add_argument("--market", required=True)
    s.add_argument("--sealed-at", default=None, help="ISO timestamp; defaults to now (UTC)")
    s.add_argument("--work", default=None)
    s.add_argument("--out", default=None)
    s.add_argument("--paid-reservations", default=None,
                   help="JSON file: artifact sha256 -> reservation, for markets with paid captures")
    s.add_argument("--work-order", default=None,
                   help="the registering work order; when given, the market-state pin block is written from the "
                        "sealed package (and held to the release contract)")
    s = sub.add_parser("register", help="participation row (SOURCE_READY, unauthorized) + build-closure inputs")
    s.add_argument("--market", required=True)
    s.add_argument("--work-order", required=True)
    s.add_argument("--decided-on", default=None)
    s.add_argument("--out", default=None)
    s = sub.add_parser("packet", help="write the UNSIGNED authorization-readiness packet")
    s.add_argument("--market", required=True)
    s.add_argument("--classification", required=True)
    s.add_argument("--lane-report", default=None)
    s.add_argument("--out", default=None)
    s.add_argument("--prepared-by", default="registration_release_lane")
    args = p.parse_args(argv)

    us = args.market.replace("-", "_")
    if args.command == "register":
        register(args.market, work_order=args.work_order, decided_on=args.decided_on,
                 out=Path(args.out) if args.out else REPORTS / ("%s_registration_participation.json" % us))
        return 0
    if args.command == "seal":
        reservations = _read(Path(args.paid_reservations)) if args.paid_reservations else None
        seal(args.market,
             sealed_at=args.sealed_at or _now(),
             work_dir=Path(args.work) if args.work else _DASH / "data" / "registration_release_lane" / args.market,
             out=Path(args.out) if args.out else REPORTS / ("%s_registration_release_lane.json" % us),
             paid_reservations=reservations, work_order=args.work_order)
        return 0
    packet(args.market, classification_path=Path(args.classification),
           lane_report=Path(args.lane_report) if args.lane_report else REPORTS / ("%s_registration_release_lane.json" % us),
           out=Path(args.out) if args.out else REPORTS / ("%s_registration_authorization_readiness.json" % us),
           prepared_by=args.prepared_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
