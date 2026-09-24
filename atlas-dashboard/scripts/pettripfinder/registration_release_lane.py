"""PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 -- the generic registration
release lane: seal the registering market, prove it on the FAST lane, commit
the package and the receipt where Regression V2 reads them, and -- once the
classifier has answered -- prepare the UNSIGNED authorization-readiness packet.

    python -m scripts.pettripfinder.registration_release_lane register --market <id> --work-order <ORDER>
    python -m scripts.pettripfinder.registration_release_lane seal --market <id> --work-order <ORDER>
    python -m scripts.pettripfinder.registration_release_lane packet --market <id>
    python -m scripts.pettripfinder.registration_release_lane reregister --market <id> --work-order <ORDER>

PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001: ``reregister`` is the one step
for a market that was registered and FOUNDER-AUTHORIZED, never deployed, and
corrected before deployment. After the founder's order has SUPERSEDED every
deployment authorization of the old bytes and ``seal`` (no ``--work-order``)
has committed the corrected package, it reissues the participation record
from the authorizing decision with the market back at SOURCE_READY and one
package-bound ``founder_authorization_superseded`` entry, and re-derives the
market's own pin block. ``packet`` then classifies against the market's own
authorizing commit (:func:`derive_reregistration_base`) and the packet says
which authorization the corrected bytes do NOT inherit.

PTF-RELEASE-FACTORY-EFFICIENCY-BOUNDED-REPAIR-002: ``register`` and ``seal``
refuse a tree that does not contain CURRENT_LIVE_SOURCE_COMMIT
(``release_index.resolve_current_live_source``), and ``packet`` with no
``--classification`` derives the classification base itself
(:func:`derive_registration_base`) and runs ``regression_delta`` on the
committed registration -- an ordinary registration names no ``--base``. A
classification produced elsewhere may still be passed and is recorded as
SUPPLIED.

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
from typing import Any, Dict, List, Mapping, Optional, Sequence

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


def write_pin_block(market_id: str, block: Mapping, work_order: str, pin_path: Optional[Path] = None,
                    *, replace: bool = False) -> str:
    """Add ONE market block to the reviewed pin; refuse to move an existing one.
    ``replace`` (re-registration only) re-derives the market's OWN existing
    block and refuses when there is none."""
    path = pin_path or PIN_PATH
    doc = _read(path)
    pinned = market_id in (doc.get("markets") or {})
    if pinned and not replace:
        raise SystemExit("%s is already pinned; a registration adds a block and never moves one" % market_id)
    if replace and not pinned:
        raise SystemExit("%s is not pinned; a re-registration re-derives an existing block" % market_id)
    doc["reviewed_by"] = work_order
    markets: "OrderedDict[str, Any]" = OrderedDict()
    for key in sorted(set(doc["markets"]) | {market_id}):
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


def reregister(market_id: str, *, work_order: str, out: Path, decided_on: Optional[str] = None,
               live: Optional[Any] = None, participation_path: Optional[Path] = None,
               pin_path: Optional[Path] = None, package: Optional[Mapping] = None) -> Dict:
    """PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001: re-register a market that
    was registered and FOUNDER-AUTHORIZED, was never deployed, and whose
    corrected package is sealed and committed (``seal`` without
    ``--work-order``). Writes two things and nothing else:

      * the participation record, REISSUED from the market's authorizing
        decision: its row back to SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_
        LAUNCH, and one package-bound ``founder_authorization_superseded``
        entry naming the authorizing decision, both package digests and every
        deployment authorization of the old bytes;
      * the market's OWN market-state pin block, re-derived from the corrected
        sealed package and held to the release contract.

    Refuses -- writing nothing -- when the market is live or was ever
    deployed, when any authorization of it is not SUPERSEDED (still
    deployable, or consumed), when the current participation record is not the
    market's package-bound founder authorization, or when no committed package
    covers the corrected bytes. It never supersedes an authorization itself
    and never authorizes anything: the founder's decision for the corrected
    bytes is a separate write."""
    from scripts.pettripfinder import launch_participation as LP
    from scripts.pettripfinder import registration_data_only as REG
    from scripts.pettripfinder.market_authority import load_markets
    _require_work_order(work_order)
    if market_id not in {m.market_id for m in load_markets()}:
        raise SystemExit("%s is not registered; there is nothing to re-register" % market_id)
    live = live if live is not None else RI.live_index()
    _idx, state, live_problems = live
    if live_problems or state.problems:
        raise SystemExit("CURRENT_VERIFIED_LIVE could not be established: %s" % (live_problems or state.problems)[:3])
    veto = REG.check_live_veto(market_id, state, REG.WORKTREE)
    if not veto["pass"]:
        raise SystemExit("REFUSED (live veto): %s" % veto["why"])

    path = participation_path or LP.PARTICIPATION_PATH
    prior_bytes = path.read_bytes()
    prior = json.loads(prior_bytes.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    prior_sha = LP.participation_sha256(path)
    decision = prior.get("decision") or {}
    basis = decision.get("decision_basis") if isinstance(decision.get("decision_basis"), Mapping) else {}
    if LP.launch_status(market_id, prior) != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH:
        raise SystemExit("%s reads %s; only a FOUNDER_AUTHORIZED_FOR_LAUNCH market is re-registered this way"
                         % (market_id, LP.launch_status(market_id, prior)))
    if basis.get("market_id") != market_id or not basis.get("registered_package_digest") \
            or str(decision.get("decided_by") or "").strip().lower() != "founder":
        raise SystemExit("the current participation record is not %s's package-bound founder authorization "
                         "(decided_by %r, decision_basis.market_id %r); re-register from the authorizing decision"
                         % (market_id, decision.get("decided_by"), basis.get("market_id")))
    old_digest = basis["registered_package_digest"]

    auths = [doc for _rel, doc in REG.json_docs_at(REG.WORKTREE, REG.AUTHORIZATIONS_PREFIX).items()
             if REG._names_market(doc, market_id)]
    if not auths:
        raise SystemExit("no deployment authorization names %s; there is nothing to supersede" % market_id)
    live_auths = [(a.get("authorization_id"), a.get("authorization_status")) for a in auths
                  if a.get("authorization_status") != LP.SUPERSEDED_AUTHORIZATION_STATUS]
    if live_auths:
        raise SystemExit("REFUSED: authorization(s) of %s's old bytes are not SUPERSEDED: %s -- supersede them "
                         "(founder order) before re-registering; a consumed one can never be" % (market_id, live_auths))

    if package is None:
        package, lookup = REG.find_covering_package(market_id, REG.WORKTREE)
        if package is None:
            raise SystemExit("no committed sealed package covers %s's corrected bytes: %s"
                             % (market_id, lookup.get("packages_seen")))
    if package["package_digest"] == old_digest:
        raise SystemExit("the package covering the head is the one the founder authorized; nothing was corrected")

    entry = OrderedDict((
        ("market_id", market_id),
        ("authorizing_decision", OrderedDict((("work_order", decision["work_order"]), ("sha256", prior_sha)))),
        ("superseded_package_digest", old_digest),
        ("corrected_package_digest", package["package_digest"]),
        ("deployment_authorizations", [OrderedDict((("authorization_id", a["authorization_id"]),
                                                    ("bundle_sha256", a["bundle_sha256"]),
                                                    ("authorization_status", a["authorization_status"])))
                                       for a in sorted(auths, key=lambda a: str(a["authorization_id"]))]),
        ("market_live", False),
        ("reauthorization_required", True),
    ))
    doc = json.loads(json.dumps(prior), object_pairs_hook=OrderedDict)
    for row in doc["markets"]:
        if row["market_id"] == market_id:
            row["launch_status"] = LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
            row["note"] = ("Re-registered by %s after a pre-deploy correction: the founder authorization of %s "
                           "(%s, package %s) is SUPERSEDED together with every deployment authorization of those "
                           "bytes. Corrected package %s is source-ready and awaiting a NEW founder launch decision."
                           % (work_order, market_id, decision["work_order"], old_digest[:23],
                              package["package_digest"][:23]))
    doc["decision"] = LP.extend_decision(
        prior, prior_sha, work_order=work_order, decided_by=work_order,
        decided_on=decided_on or time.strftime("%Y-%m-%d", time.gmtime()),
        reason=("%s's founder authorization was bound to package %s, which a pre-deploy correction replaced with "
                "%s. Every deployment authorization of the old bytes is SUPERSEDED and none was consumed; the "
                "market was never live. This write records that the old authorization admits nothing and returns "
                "the market to SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH. The founder's decision for the "
                "corrected bytes, if it comes, is a separate write."
                % (market_id, old_digest[:23], package["package_digest"][:23])),
        path=path, **{LP.FOUNDER_AUTHORIZATION_SUPERSEDED: [entry]})
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    new_bytes = text.encode("utf-8")
    proof = REG.check_reregistration_participation(prior_bytes, new_bytes, market_id)
    if not proof["pass"]:
        raise SystemExit("the reissued participation record fails the re-registration proof: %s" % proof["why"])
    block = pin_block_from_package(package, market_id, work_order)
    path.write_bytes(new_bytes)
    pinned = write_pin_block(market_id, block, work_order, pin_path, replace=True)
    report = OrderedDict((
        ("schema", "ptf-reregistration-participation/1.0"),
        ("work_order", work_order), ("market_id", market_id), ("as_of", _now()),
        ("participation", OrderedDict((
            ("prior_sha256", prior_sha), ("new_sha256", LP.participation_sha256(path)),
            ("status_before", LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
            ("status_after", LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH),
            ("founder_authorization_superseded", entry),
            ("proof", proof["status"])))),
        ("market_state_pin", pinned),
        ("live_veto", veto["why"]),
        ("nothing_deployed", True), ("nothing_authorized", True),
        ("new_founder_authorization_required", True),
    ))
    _write(out, report)
    print("participation  :", market_id, LP.FOUNDER_AUTHORIZED_FOR_LAUNCH, "->",
          LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH, "| proof", proof["status"])
    print("superseded     :", old_digest[:23], "->", package["package_digest"][:23], "| authorizations",
          [a["authorization_id"] for a in entry["deployment_authorizations"]])
    print("market state   :", pinned)
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


# --------------------------------------------------------------------------- #
# PTF-RELEASE-FACTORY-EFFICIENCY-BOUNDED-REPAIR-002: the live base and the
# automatic classification. An ordinary registration names no --base.
# --------------------------------------------------------------------------- #

STALE_LIVE_BASE = "STALE_LIVE_BASE"
BASE_NOT_DERIVABLE = "BASE_NOT_DERIVABLE"
DIRTY_WORKTREE = "DIRTY_WORKTREE"
CLASSIFICATION_SOURCE_AUTOMATIC = "AUTOMATIC"
CLASSIFICATION_SOURCE_SUPPLIED = "SUPPLIED"
_BASE_WALK_LIMIT = 2000


class LaneRefusal(SystemExit):
    """A named, fail-closed refusal of the lane (exit status 2)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(2)
        self.code = code
        self.detail = detail

    def __str__(self) -> str:
        return "%s: %s" % (self.code, self.detail)


def _git_text(*args: str, git_root: Optional[Path] = None) -> str:
    import subprocess
    proc = subprocess.run(["git", *args], cwd=str(git_root or _DASH.parent), capture_output=True, text=True)
    if proc.returncode != 0:
        raise LaneRefusal(BASE_NOT_DERIVABLE, "git %s failed: %s" % (" ".join(args[:3]), proc.stderr.strip()[:200]))
    return proc.stdout


def require_current_live(resolution: Optional[Mapping] = None, *, git_root: Optional[Path] = None,
                         prefix: Optional[str] = None,
                         worktree_live: Optional[Any] = None) -> "OrderedDict[str, Any]":
    """CURRENT_LIVE_SOURCE_COMMIT, and this worktree built on it -- or refuse.

    Refuses when the resolver cannot name live (any refusal code), when HEAD
    does not descend from the live lineage commit, or when the live state
    this worktree's own committed records describe is not that live."""
    doc = OrderedDict(resolution) if resolution is not None else RI.resolve_current_live_source(
        git_root, prefix=prefix)
    if doc.get("RESOLVED") != "YES":
        raise LaneRefusal(STALE_LIVE_BASE, "CURRENT_LIVE_SOURCE_COMMIT is not resolvable: %s"
                          % "; ".join((doc.get("problems") or ["unresolved"])[:3]))
    if not doc.get("head_contains_live"):
        raise LaneRefusal(STALE_LIVE_BASE, "HEAD %s does not contain the live lineage commit %s (live deploy %s); "
                          "merge the live lineage before registering"
                          % (str(doc.get("head_commit"))[:12], str(doc["CURRENT_LIVE_SOURCE_COMMIT"])[:12],
                             doc.get("live_deploy_id")))
    state = worktree_live if worktree_live is not None else RI.current_verified_live()
    if state.deploy_id != doc.get("live_deploy_id") or state.problems:
        raise LaneRefusal(STALE_LIVE_BASE, "this worktree's committed live state is deploy %s (%d problem(s)), "
                          "live is %s" % (state.deploy_id, len(state.problems), doc.get("live_deploy_id")))
    return doc


def _paths_naming(commit: str, market_id: str, prefix: str, git_root: Optional[Path]) -> List[str]:
    us = market_id.replace("-", "_")
    listing = _git_text("ls-tree", "-r", "--name-only", commit, "--", prefix.rstrip("/"), git_root=git_root)
    return [line for line in listing.splitlines()
            if market_id in line.lower() or us in line.lower()]


def _truth_ids(commit: str, prefix: str, git_root: Optional[Path]) -> List[str]:
    import subprocess
    spec = "".join("%s:%s%s\n" % (commit, prefix, p) for p in RI._LIVE_TRUTH_PATHS)
    proc = subprocess.run(["git", "cat-file", "--batch-check"], cwd=str(git_root or _DASH.parent),
                          input=spec, capture_output=True, text=True)
    return [line.split()[0] if line.split() else "" for line in proc.stdout.splitlines()]


def derive_registration_base(market_id: str, live_commit: str, *, head: str = "HEAD",
                             git_root: Optional[Path] = None,
                             prefix: Optional[str] = None) -> "OrderedDict[str, Any]":
    """The classification base, mechanically: the newest commit on HEAD's
    first-parent chain that (a) descends from the live lineage commit, (b)
    carries no path naming the registering market, and (c) carries exactly
    the live lineage commit's live-truth files. Everything the market brings
    -- its acquisition helpers, its shadow data, its registration -- is then
    in the diff the classifier proves, and nothing else is.

    Refuses when the chain leaves the live lineage before reaching such a
    commit: the market's work predates live and must be re-registered on it.
    """
    prefix = prefix if prefix is not None else _DASH.name + "/"
    live_truth = _truth_ids(live_commit, prefix, git_root)
    chain = _git_text("rev-list", "--first-parent", "--max-count=%d" % _BASE_WALK_LIMIT, head,
                      git_root=git_root).split()
    walked: List["OrderedDict[str, Any]"] = []
    for commit in chain:
        if not RI._is_ancestor(git_root or _DASH.parent, live_commit, commit):
            raise LaneRefusal(BASE_NOT_DERIVABLE,
                              "%s's work reaches back past the live lineage commit %s (first-parent %s does not "
                              "contain it): merge live first, then register"
                              % (market_id, live_commit[:12], commit[:12]))
        naming = _paths_naming(commit, market_id, prefix, git_root)
        walked.append(OrderedDict((("commit", commit), ("market_paths", len(naming)))))
        if naming:
            continue
        if _truth_ids(commit, prefix, git_root) != live_truth:
            raise LaneRefusal(BASE_NOT_DERIVABLE,
                              "%s carries no %s path but its live-truth files differ from the live lineage "
                              "commit %s" % (commit[:12], market_id, live_commit[:12]))
        between = _git_text("log", "--format=%H %s", "%s..%s" % (live_commit, commit),
                            git_root=git_root).splitlines()
        return OrderedDict((
            ("base", commit), ("live_lineage_commit", live_commit),
            ("rule", "newest first-parent ancestor of HEAD that contains the live lineage commit, names no "
                     "path of the registering market, and carries the live lineage commit's live-truth files"),
            ("commits_walked", walked),
            ("factory_commits_since_live", [OrderedDict((("commit", line[:40]), ("subject", line[41:])))
                                            for line in between if line.strip()]),
        ))
    raise LaneRefusal(BASE_NOT_DERIVABLE, "no base within %d first-parent commits" % _BASE_WALK_LIMIT)


_PARTICIPATION_REL = "deploy/netlify/launch_participation.json"
_AUTHORIZATIONS_REL = "deploy/netlify/deployment_authorizations"


def _blob(commit: str, relpath: str, git_root: Optional[Path]) -> Optional[bytes]:
    import subprocess
    proc = subprocess.run(["git", "show", "%s:%s" % (commit, relpath)], cwd=str(git_root or _DASH.parent),
                          capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def _tree_listing(commit: str, relpath: str, git_root: Optional[Path]) -> "OrderedDict[str, str]":
    listing = _git_text("ls-tree", commit, "--", relpath, git_root=git_root)
    out: "OrderedDict[str, str]" = OrderedDict()
    for line in listing.splitlines():
        meta, _tab, name = line.partition("\t")
        if meta.split()[1:2] == ["blob"]:
            out[name.rsplit("/", 1)[-1]] = meta.split()[2]
    return out


def reregistration_market_at(commit: str, *, git_root: Optional[Path] = None,
                             prefix: Optional[str] = None) -> Optional[str]:
    """The one market whose founder authorization ``commit``'s participation
    decision supersedes, or None (an ordinary registration)."""
    from scripts.pettripfinder import launch_participation as LP
    prefix = prefix if prefix is not None else _DASH.name + "/"
    data = _blob(commit, prefix + _PARTICIPATION_REL, git_root)
    if data is None:
        return None
    markets = LP.superseded_market_ids(json.loads(data.decode("utf-8-sig")))
    return markets[0] if len(markets) == 1 else None


def derive_reregistration_base(market_id: str, live_commit: str, *, head: str = "HEAD",
                               git_root: Optional[Path] = None,
                               prefix: Optional[str] = None) -> "OrderedDict[str, Any]":
    """PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001: the classification base of
    a RE-registration is the market's OWN prior registered state -- the
    first-parent commit that WROTE the authorizing decision the head's
    ``founder_authorization_superseded`` entry names (the oldest commit of the
    contiguous run whose participation record hashes to it). Its tree holds
    the registered package, the contract and the pin the founder authorized,
    so the diff is exactly the correction, the supersession and the reissue;
    nothing already proven reappears as drift and nothing earlier escapes.

    Refuses unless the base (a) descends from the live lineage commit, (b)
    registers the market, and (c) carries live's deployment records, manifest
    and deployment pin byte-for-byte and every live authorization unchanged,
    its only extra authorizations naming this market and never DEPLOYED."""
    from scripts.pettripfinder import launch_participation as LP
    import hashlib
    prefix = prefix if prefix is not None else _DASH.name + "/"
    head_bytes = _blob(head, prefix + _PARTICIPATION_REL, git_root)
    if head_bytes is None:
        raise LaneRefusal(BASE_NOT_DERIVABLE, "no participation record at %s" % head)
    entries = [e for e in (json.loads(head_bytes.decode("utf-8-sig")).get("decision") or {}).get(
        LP.FOUNDER_AUTHORIZATION_SUPERSEDED) or () if isinstance(e, Mapping)]
    if len(entries) != 1 or entries[0].get("market_id") != market_id:
        raise LaneRefusal(BASE_NOT_DERIVABLE, "the head participation decision does not supersede exactly %s's "
                                              "founder authorization" % market_id)
    authorizing = entries[0].get("authorizing_decision") or {}
    target = str(authorizing.get("sha256") or "")
    chain = _git_text("rev-list", "--first-parent", "--max-count=%d" % _BASE_WALK_LIMIT, head,
                      git_root=git_root).split()
    walked: List["OrderedDict[str, Any]"] = []
    base: Optional[str] = None
    for commit in chain:
        data = _blob(commit, prefix + _PARTICIPATION_REL, git_root)
        digest = hashlib.sha256(data).hexdigest() if data is not None else None
        walked.append(OrderedDict((("commit", commit), ("participation_sha256", digest))))
        if digest == target:
            base = commit
        elif base is not None:
            break
    if base is None:
        raise LaneRefusal(BASE_NOT_DERIVABLE, "no first-parent commit carries the authorizing decision %s (%s)"
                                              % (authorizing.get("work_order"), target[:12]))
    if not RI._is_ancestor(git_root or _DASH.parent, live_commit, base):
        raise LaneRefusal(BASE_NOT_DERIVABLE, "the authorizing commit %s does not contain the live lineage commit "
                                              "%s: the authorization predates live" % (base[:12], live_commit[:12]))
    if _blob(base, prefix + "launch_packages/pettripfinder/markets/%s.json" % market_id, git_root) is None:
        raise LaneRefusal(BASE_NOT_DERIVABLE, "%s is not registered at its authorizing commit %s" % (market_id, base[:12]))
    live_truth, base_truth = _truth_ids(live_commit, prefix, git_root), _truth_ids(base, prefix, git_root)
    for i, rel in enumerate(RI._LIVE_TRUTH_PATHS):
        if rel == _AUTHORIZATIONS_REL:
            continue
        if live_truth[i] != base_truth[i]:
            raise LaneRefusal(BASE_NOT_DERIVABLE, "%s differs between the authorizing commit %s and live %s"
                                                  % (rel, base[:12], live_commit[:12]))
    live_auths = _tree_listing(live_commit, prefix + _AUTHORIZATIONS_REL + "/", git_root)
    base_auths = _tree_listing(base, prefix + _AUTHORIZATIONS_REL + "/", git_root)
    changed = [n for n, blob in live_auths.items() if base_auths.get(n) != blob]
    if changed:
        raise LaneRefusal(BASE_NOT_DERIVABLE, "live authorization(s) differ at the authorizing commit: %s" % changed[:3])
    extras = []
    for name in (n for n in base_auths if n not in live_auths):
        doc = json.loads((_blob(base, "%s%s/%s" % (prefix, _AUTHORIZATIONS_REL, name), git_root) or b"{}")
                         .decode("utf-8-sig"))
        names_market = market_id in (doc.get("participating_markets") or ()) or market_id in (
            doc.get("founder_authorized_markets") or ())
        if not names_market or doc.get("authorization_status") not in ("PREPARED", "AUTHORIZED"):
            raise LaneRefusal(BASE_NOT_DERIVABLE, "authorization %s at the authorizing commit is not an undeployed "
                                                  "authorization of %s (%s)" % (name, market_id,
                                                                                doc.get("authorization_status")))
        extras.append(name)
    between = _git_text("log", "--format=%H %s", "%s..%s" % (live_commit, base), git_root=git_root).splitlines()
    return OrderedDict((
        ("base", base), ("live_lineage_commit", live_commit), ("mode", "reregistration"),
        ("rule", "the first-parent commit that wrote the authorizing decision the head's "
                 "founder_authorization_superseded entry names: the market's own prior registered state, "
                 "containing the live lineage commit and live's deployment records, manifest, deployment pin and "
                 "authorizations, plus only the undeployed authorization(s) of this market"),
        ("authorizing_decision", OrderedDict((("work_order", authorizing.get("work_order")), ("sha256", target)))),
        ("authorizations_of_the_market_at_base", extras),
        ("commits_walked", walked),
        ("factory_commits_since_live", [OrderedDict((("commit", line[:40]), ("subject", line[41:])))
                                        for line in between if line.strip()]),
    ))


FACTORY_BASELINE_NOT_DERIVABLE = "FACTORY_BASELINE_NOT_DERIVABLE"
#: What a factory lineage may never carry: a market's data, a release's
#: deployment state, or any path naming a market. Those belong to a market's
#: own order, and a lineage that carries one is not a factory lineage.
_NOT_FACTORY_CLASSES = ("AUTHORITY_CHANGE", "MARKET_DATA_PACKAGE", "DEPLOYMENT_CHANGE")


def _rel_from_git_path(git_path: str, prefix: str) -> str:
    return git_path[len(prefix):] if git_path.startswith(prefix) else "../" + git_path


def _refuse_factory(detail: str) -> None:
    raise LaneRefusal(FACTORY_BASELINE_NOT_DERIVABLE, detail)


def prove_factory_lineage(candidate: str, market_id: str, base: str, live_commit: str, *,
                          head: str = "HEAD", git_root: Optional[Path] = None,
                          prefix: Optional[str] = None) -> "OrderedDict[str, Any]":
    """One merged lineage tip, proven a TRUSTED FACTORY lineage -- or refused.

    It must (a) be an ancestor of ``head`` and not contain the market's
    authorizing commit ``base``; (b) name no path of the market; (c) contain
    the live lineage commit and carry its live-truth files byte-for-byte;
    (d) be published independently -- some branch or remote ref contains it
    that does not contain ``base`` (the lineage exists on its own, not only
    inside this market's branch); and (e) change, since it left the market
    line, only factory paths: no market data, no deployment state, no path
    naming any market."""
    from scripts.pettripfinder import regression_delta as RD
    prefix = prefix if prefix is not None else _DASH.name + "/"
    root = git_root or _DASH.parent
    if not RI._is_ancestor(root, candidate, head):
        _refuse_factory("factory lineage %s is not an ancestor of %s" % (candidate[:12], head))
    if RI._is_ancestor(root, base, candidate):
        _refuse_factory("lineage %s contains the market's authorizing commit %s: it is the market's line, not a "
                        "factory lineage" % (candidate[:12], base[:12]))
    naming = _paths_naming(candidate, market_id, prefix, git_root)
    if naming:
        _refuse_factory("lineage %s carries %d path(s) naming %s: %s" % (candidate[:12], len(naming), market_id,
                                                                         naming[:3]))
    if not RI._is_ancestor(root, live_commit, candidate):
        _refuse_factory("lineage %s does not contain the live lineage commit %s" % (candidate[:12], live_commit[:12]))
    if _truth_ids(candidate, prefix, git_root) != _truth_ids(live_commit, prefix, git_root):
        _refuse_factory("lineage %s moved live-truth files the live lineage commit %s carries"
                        % (candidate[:12], live_commit[:12]))
    refs = [line.strip() for line in _git_text("for-each-ref", "--contains", candidate, "--format=%(refname)",
                                               "refs/heads", "refs/remotes", git_root=git_root).splitlines()
            if line.strip() and not line.strip().endswith("/HEAD")]
    independent = [ref for ref in refs if not RI._is_ancestor(root, base, ref)]
    if not independent:
        _refuse_factory("lineage %s is published by no ref of its own (every ref containing it is the market's "
                        "line): an unproven lineage is not a trusted factory baseline" % candidate[:12])
    merge_base = _git_text("merge-base", base, candidate, git_root=git_root).strip()
    changed = [_rel_from_git_path(line.strip(), prefix)
               for line in _git_text("diff", "--name-only", "%s..%s" % (merge_base, candidate), "--",
                                     git_root=git_root).splitlines() if line.strip()]
    foreign = []
    for rel in changed:
        classes, _rule = RD.classify_path(rel)
        if RD._markets_named(rel) or market_id in rel.lower() or market_id.replace("-", "_") in rel.lower() \
                or any(c in _NOT_FACTORY_CLASSES for c in classes):
            foreign.append("%s (%s)" % (rel, "/".join(classes)))
    if foreign:
        _refuse_factory("lineage %s changes %d non-factory path(s): %s" % (candidate[:12], len(foreign), foreign[:3]))
    return OrderedDict((("commit", candidate), ("merge_base", merge_base), ("independent_refs", independent),
                        ("factory_paths", changed)))


def derive_trusted_factory_baseline(market_id: str, base: str, live_commit: str, *, head: str = "HEAD",
                                    git_root: Optional[Path] = None,
                                    prefix: Optional[str] = None) -> Optional["OrderedDict[str, Any]"]:
    """PTF-REREGISTRATION-TRUSTED-FACTORY-BASELINE-CORRECTION-002: the second
    lineage of a re-registration, mechanically.

    A re-registration is classified against the market's OWN authorizing
    commit ``base``. Factory repairs proven in their own orders and merged
    into the market line AFTER ``base`` would otherwise reappear as shared
    drift. The trusted factory baseline is found, never named: every
    non-first parent of a first-parent merge between ``base`` and ``head``
    that ``base`` does not already contain is a merged lineage, and EVERY one
    must pass :func:`prove_factory_lineage` (one unproven merge refuses the
    whole baseline). The proven tips must be ordered by ancestry; the newest,
    which contains all the others, is the baseline. None when nothing was
    merged -- the classification is then exactly the old one."""
    root = git_root or _DASH.parent
    merges = _git_text("rev-list", "--first-parent", "--merges", "%s..%s" % (base, head),
                       git_root=git_root).split()
    tips: List[str] = []
    for merge in reversed(merges):
        parents = _git_text("rev-list", "--parents", "-n", "1", merge, git_root=git_root).split()[2:]
        for parent in parents:
            if not RI._is_ancestor(root, parent, base) and parent not in tips:
                tips.append(parent)
    if not tips:
        return None
    proven = [prove_factory_lineage(tip, market_id, base, live_commit, head=head, git_root=git_root,
                                    prefix=prefix) for tip in tips]
    newest = [p for p in proven if all(RI._is_ancestor(root, q["commit"], p["commit"]) for q in proven)]
    if len(newest) != 1:
        _refuse_factory("the merged factory lineages %s are not one line of descent: the trusted factory baseline "
                        "cannot be resolved uniquely" % [p["commit"][:12] for p in proven])
    baseline = newest[0]
    baseline["merges"] = merges
    baseline["lineage_tips"] = tips
    baseline["rule"] = ("the newest of the lineages merged into the market line after its authorizing commit, each "
                        "proven: an ancestor of the head not containing the authorizing commit, naming no market "
                        "path, containing live and its live-truth files, published by a ref of its own, and changing "
                        "only factory paths")
    return baseline


def classify_automatically(market_id: str, *, out: Path, git_root: Optional[Path] = None,
                           resolution: Optional[Mapping] = None) -> "OrderedDict[str, Any]":
    """Resolve live, derive the base, run the existing classifier on the
    working tree, and write the classification the packet consumes."""
    from scripts.pettripfinder import regression_delta as RD
    started = time.monotonic()
    live = require_current_live(resolution, git_root=git_root)
    dirty = _git_text("status", "--porcelain", "--untracked-files=all", "--", _DASH.name,
                      git_root=git_root).strip()
    if dirty:
        raise LaneRefusal(DIRTY_WORKTREE, "commit the registration first; the classifier proves committed "
                          "bytes: %s" % dirty.splitlines()[:3])
    # PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001: a head that supersedes
    # this market's founder authorization is a RE-registration, proven
    # against the market's own authorizing commit.
    factory = None
    if reregistration_market_at("HEAD", git_root=git_root) == market_id:
        base = derive_reregistration_base(market_id, live["CURRENT_LIVE_SOURCE_COMMIT"], git_root=git_root)
        # PTF-REREGISTRATION-TRUSTED-FACTORY-BASELINE-CORRECTION-002: factory
        # lineages merged after the authorizing commit are compared against
        # their own proven tip, by bytes; the market against its base.
        factory = derive_trusted_factory_baseline(market_id, base["base"], live["CURRENT_LIVE_SOURCE_COMMIT"],
                                                  git_root=git_root)
        base["trusted_factory_baseline"] = factory
    else:
        base = derive_registration_base(market_id, live["CURRENT_LIVE_SOURCE_COMMIT"], git_root=git_root)
    doc = RD.classify_document(base["base"], RD.WORKTREE, factory_baseline=factory)
    doc["classification_source"] = CLASSIFICATION_SOURCE_AUTOMATIC
    doc["live_resolution"] = OrderedDict((k, live.get(k)) for k in (
        "CURRENT_LIVE_SOURCE_COMMIT", "built_from_commit", "live_deploy_id", "deployment_record",
        "bundle_sha256", "sitemap_sha256", "total_profiles", "sitemap_route_count", "head_commit",
        "head_contains_live", "origin_main_contains_live", "origin_main_stale", "refs_scanned", "seconds"))
    doc["registration_base"] = base
    doc["automatic_classification_seconds"] = round(time.monotonic() - started, 2)
    _write(out, doc)
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
            ("classification_source", classification.get("classification_source") or CLASSIFICATION_SOURCE_SUPPLIED),
            ("current_live_source_commit", (classification.get("live_resolution") or {}).get("CURRENT_LIVE_SOURCE_COMMIT")),
            ("registration_base", (classification.get("registration_base") or {}).get("base")),
            ("trusted_factory_baseline", (classification.get("trusted_factory_baseline") or {}).get("commit")),
            ("inherited_factory_paths", len((classification.get("trusted_factory_baseline") or {}).get(
                "inherited_paths") or ())),
            ("SHARED_FACTORY_DELTA", (classification.get("trusted_factory_baseline") or {}).get(
                "SHARED_FACTORY_DELTA")),
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
    # PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001: a re-registration packet
    # states which authorization it does NOT inherit.
    participation = ((proof.get("checks") or {}).get("participation") or {}).get("detail") or {}
    if proof.get("CHANGE_CLASS") == "AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY" \
            or participation.get("mode") == "reregistration":
        doc["reregistration"] = OrderedDict((
            ("superseded_founder_decision", participation.get("authorizing_decision")),
            ("superseded_package_digest", participation.get("superseded_package_digest")),
            ("corrected_package_digest", participation.get("corrected_package_digest")),
            ("superseded_deployment_authorizations", participation.get("deployment_authorizations")),
            ("old_authorizations_authorize_the_corrected_package", False),
            ("new_founder_authorization_required", True),
        ))
        doc["what_is_not_claimed"].append(
            "The superseded founder decision and every deployment authorization of the old bytes authorize "
            "NOTHING for the corrected package; a new founder authorization of these exact bytes is owed.")
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
    s = sub.add_parser("reregister", help="re-register an authorized, never-deployed market after a correction "
                                          "(participation reissue + its own pin block)")
    s.add_argument("--market", required=True)
    s.add_argument("--work-order", required=True)
    s.add_argument("--decided-on", default=None)
    s.add_argument("--out", default=None)
    s = sub.add_parser("packet", help="write the UNSIGNED authorization-readiness packet")
    s.add_argument("--market", required=True)
    s.add_argument("--classification", default=None,
                   help="a classification JSON produced elsewhere (SUPPLIED); omitted, the lane resolves "
                        "CURRENT_LIVE_SOURCE_COMMIT, derives the base and classifies itself (AUTOMATIC)")
    s.add_argument("--lane-report", default=None)
    s.add_argument("--out", default=None)
    s.add_argument("--prepared-by", default="registration_release_lane")
    args = p.parse_args(argv)

    us = args.market.replace("-", "_")
    try:
        return _run(args, us)
    except LaneRefusal as refusal:
        print("REFUSED        :", refusal)
        return 2


def _run(args: Any, us: str) -> int:
    if args.command in ("register", "seal", "reregister"):
        # PTF-RELEASE-FACTORY-EFFICIENCY-BOUNDED-REPAIR-002: never register or
        # seal on a tree that is not built on current live.
        require_current_live()
    if args.command == "reregister":
        reregister(args.market, work_order=args.work_order, decided_on=args.decided_on,
                   out=Path(args.out) if args.out else REPORTS / ("%s_reregistration_participation.json" % us))
        return 0
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
    classification_path = Path(args.classification) if args.classification else None
    if classification_path is None:
        classification_path = REPORTS / ("%s_registration_classification.json" % us)
        doc = classify_automatically(args.market, out=classification_path)
        print("live source    :", doc["live_resolution"]["CURRENT_LIVE_SOURCE_COMMIT"][:12], "| deploy",
              doc["live_resolution"]["live_deploy_id"], "| base", doc["registration_base"]["base"][:12],
              "| %.1fs" % doc["automatic_classification_seconds"])
    packet(args.market, classification_path=classification_path,
           lane_report=Path(args.lane_report) if args.lane_report else REPORTS / ("%s_registration_release_lane.json" % us),
           out=Path(args.out) if args.out else REPORTS / ("%s_registration_authorization_readiness.json" % us),
           prepared_by=args.prepared_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
