"""PETTRIPFINDER-PROD-003 (Gate 1) -- offline launch-safety re-derivation of the
frozen AW-006 Columbus/Dublin hotel-research pilot.

READ-ONLY over the gitignored worker runtime artifacts. Writes review artifacts
ONLY to an isolated gitignored review directory. It NEVER writes to
``launch_packages/`` or the operational hotel-policy corpus, never generates
pages, never touches inventory, and never calls the network. It reads no wall
clock, so identical inputs yield byte-identical artifacts.

Method (operator decision 3 -- re-derive under the FROZEN AW-006 validator and
routing authority at commit cde9745, WITHOUT trusting the historical AW-005 v2
READY flags):

The frozen AW-006 authority is a strict SUPERSET of gates over the v2 validator:
it only ADDS the deterministic multi-amount fee backstop; every contradiction,
warning, and scalar-fact rule is byte-identical. Therefore:

  * A v2 record that already failed a gate (status != COMPLETED) can never become
    launch-safe under the frozen authority. The frozen validator reproduces its
    deterministic output identically, so the loaded result is routed through the
    ACTUAL frozen ``route_result`` and its reasons are preserved -- a gate is
    never upgraded.

  * Every v2 COMPLETED record (the historical READY set) is INDEPENDENTLY
    re-derived: its model proposal is reconstructed from the persisted supported
    facts and re-run through the ACTUAL frozen ``validate_proposal`` +
    ``route_result``, so the AW-006 multi-amount backstop is applied over the
    ORIGINAL source evidence and the route is computed from scratch. This is the
    only place a previously-READY record can be demoted; the v2 READY flag is
    never an input to the classification.

A candidate is launch-safe iff the frozen route is READY. The worker code under
``services/research_workers`` is used strictly as a read-only, frozen authority;
this tool imports it and never modifies it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Allow direct invocation (python scripts/pettripfinder/prod003_launch_safety_replay.py)
# by putting the application root (atlas-dashboard) on sys.path. When imported as a
# module under pytest the package path is already resolved, so this is a no-op.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.contracts import Assignment, WorkerResult
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.fee_terms import detect_multiple_fee_amounts
from services.research_workers.model_eval import VALIDATOR_VERSION
from services.research_workers.proposal import ModelProposal, RawFactClaim

# Repo layout: scripts/pettripfinder/<this>.py -> parents[2] == atlas-dashboard.
_APP_ROOT = Path(__file__).resolve().parents[2]
FROZEN_WORKER_COMMIT = "cde9745e6cc730a14bfafe05d0d896a0173b3ddd"

DEFAULT_PILOT_DIR = _APP_ROOT / "data" / "worker_runs" / "pettripfinder" / "columbus_hotel_pilot_v2"
# Isolated, gitignored review directory (all of data/worker_runs is gitignored).
DEFAULT_REVIEW_DIR = _APP_ROOT / "data" / "worker_runs" / "pettripfinder" / "prod003_gate1_review"

# Paths this tool must never write to (asserted by the Gate-1 tests).
COMMITTED_LAUNCH_PACKAGE = _APP_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"

MANIFEST_SCHEMA_VERSION = "prod003-gate1/1.0"


# --------------------------------------------------------------------------- #
# Deterministic re-derivation of one record under the frozen AW-006 authority.
# --------------------------------------------------------------------------- #

def _reconstruct_proposal(result: WorkerResult) -> ModelProposal:
    """Rebuild the model proposal from a COMPLETED result's SUPPORTED facts.

    A COMPLETED result has no contradictions and no blocking warnings, so its
    supported facts ARE the accepted model claims; re-validating them under the
    frozen validator reproduces COMPLETED unless the new multi-amount backstop
    fires. (This is applied ONLY to COMPLETED records -- see module docstring --
    because a non-COMPLETED result's contradictory/rejected claims are not
    recoverable from the supported-fact set, and such records are never
    upgraded.)"""
    claims = tuple(
        RawFactClaim(f.field_name, f.value, f.evidence_quote, f.source_url)
        for f in result.proposed_facts if f.state == V.SUPPORTED)
    return ModelProposal(claims=claims, ok=True, structured_output_valid=True,
                         provider=result.provider, model=result.model)


def _exclusion_reason(route: str, reason_codes: Tuple[str, ...], contradictions: Tuple[str, ...],
                      multi_amount: bool, amounts: List[str]) -> str:
    """A precise, human-readable explanation of why a record is not launch-safe."""
    parts: List[str] = []
    if RT.CONTRADICTORY_OFFICIAL_SOURCES in reason_codes:
        parts.append(
            "Official source states conflicting values (%s); requires manual "
            "reconciliation before any import." % "; ".join(contradictions))
    if RT.STRUCTURED_FEE_REQUIRED in reason_codes or (multi_amount and RT.CONTRADICTORY_OFFICIAL_SOURCES not in reason_codes):
        parts.append(
            "Evidence states multiple distinct pet-fee amounts (%s) -- a tiered/"
            "capped fee the single-value launch schema cannot represent without "
            "flattening; withheld under AW-006 and routed to manual tiered-fee "
            "handling (PROD-003 item 5)." % ", ".join(amounts))
    residual = [c for c in reason_codes
                if c not in (RT.CONTRADICTORY_OFFICIAL_SOURCES, RT.STRUCTURED_FEE_REQUIRED)]
    if residual:
        parts.append(
            "Validator/routing withheld the record for: %s; requires human review "
            "(not auto-importable)." % ", ".join(sorted(residual)))
    if not parts:
        parts.append("Route %s is not READY; requires human review." % route)
    return " ".join(parts)


def classify_record(assignment: Assignment, v2_result: WorkerResult, *,
                    extraction_prompt_version: str, extraction_validator_version: str,
                    verification_date: str, v2_result_hash: str,
                    assignment_hash: str) -> Dict:
    """Re-derive ONE record's launch-safety under the frozen AW-006 authority and
    return a fully self-describing candidate record. Pure/deterministic."""
    usable = [d for d in assignment.source_documents if d.is_usable_official]
    multi_amount, amounts = detect_multiple_fee_amounts(usable)

    if v2_result.status == V.STATUS_COMPLETED:
        proposal: Optional[ModelProposal] = _reconstruct_proposal(v2_result)
        frozen_result = validate_proposal(
            assignment, proposal, provider=v2_result.provider, model=v2_result.model)
        rederivation_method = "reconstructed_proposal_frozen_validate_and_route"
    else:
        # Already failed a gate; the frozen validator reproduces this identically.
        proposal = None
        frozen_result = v2_result
        rederivation_method = "preserved_v2_gate_frozen_route"

    envelope = RT.route_result(
        assignment, frozen_result, proposal,
        prompt_version=extraction_prompt_version, validator_version=VALIDATOR_VERSION)

    reasons = set(envelope.reason_codes)
    # Faithful backstop augmentation: a NEEDS_REVIEW record with multi-amount
    # evidence would, under a FULL frozen re-validation of its raw proposal, also
    # carry the multi_term_fee_unrepresented warning, which routing._warning_reasons
    # maps to STRUCTURED_FEE_REQUIRED. A CONTRADICTORY status short-circuits in
    # routing._decide (routing.py:446) to CONTRADICTORY_OFFICIAL_SOURCES only, so it
    # is never augmented; COMPLETED records run the real backstop via reconstruction.
    if v2_result.status == V.STATUS_NEEDS_REVIEW and multi_amount:
        reasons.add(RT.STRUCTURED_FEE_REQUIRED)
        rederivation_method += "+backstop_augmented"
    reason_codes = sorted(reasons)

    launch_safe = envelope.route == RT.ROUTE_READY
    supported = [
        {"field_name": f.field_name, "value": f.value,
         "evidence_quote": f.evidence_quote, "source_url": f.source_url,
         "source_type": f.source_type}
        for f in frozen_result.proposed_facts if f.state == V.SUPPORTED]
    source_urls = sorted({d.source_url for d in usable})

    record = {
        # Result-hash-bound candidate identity (the frozen re-derivation is the
        # authority a future approval binds to; the v2 hash is provenance).
        "candidate_identity": envelope.result_hash,
        "listing_name": assignment.listing_name,
        "listing_key": assignment.listing_key,
        "launch_safe": launch_safe,
        "final_route": envelope.route,
        "reason_codes": reason_codes,
        "publication_eligible": bool(envelope.publication_eligible),
        "supported_facts": supported,
        "evidence_quotes": [f["evidence_quote"] for f in supported],
        "source_urls": source_urls,
        "verification_date": verification_date,
        "model_id": v2_result.model,
        # Extraction provenance (what produced the facts) vs the frozen
        # re-derivation authority (what classified them). No new model call.
        "extraction_prompt_version": extraction_prompt_version,
        "extraction_validator_version": extraction_validator_version,
        "rederivation_validator_version": VALIDATOR_VERSION,
        "rederivation_routing_version": RT.ROUTING_VERSION,
        "frozen_worker_commit": FROZEN_WORKER_COMMIT,
        "rederivation_method": rederivation_method,
        "multi_amount_detected": multi_amount,
        "multi_amount_values": amounts,
        "v2_status": v2_result.status,
        "v2_contradictions": list(v2_result.contradictions),
        "v2_result_hash": v2_result_hash,
        "frozen_result_hash": envelope.result_hash,
        "assignment_hash": assignment_hash,
    }
    if not launch_safe:
        record["manual_review_reason"] = _exclusion_reason(
            envelope.route, tuple(reason_codes),
            tuple(v2_result.contradictions), multi_amount, amounts)
    return record


# --------------------------------------------------------------------------- #
# Load the persisted v2 pilot artifacts (read-only).
# --------------------------------------------------------------------------- #

def _load_json(path: Path) -> Dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _index_by_assignment_id(directory: Path) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for path in sorted(directory.glob("*.json")):
        d = _load_json(path)
        aid = d.get("assignment_id")
        if aid:
            out[aid] = d
    return out


def load_pilot_records(pilot_dir: Path) -> List[Dict]:
    """Join assignments <-> validated_results <-> routing_envelopes by
    assignment_id. Returns one raw bundle per hotel (read-only)."""
    assignments = _index_by_assignment_id(pilot_dir / "assignments")
    results = _index_by_assignment_id(pilot_dir / "validated_results")
    envelopes = _index_by_assignment_id(pilot_dir / "routing_envelopes")
    bundles: List[Dict] = []
    for aid in sorted(results):
        if aid not in assignments:
            continue
        bundles.append({
            "assignment": assignments[aid],
            "result": results[aid],
            "envelope": envelopes.get(aid, {}),
        })
    return bundles


def _verification_date(assignment: Assignment) -> str:
    dates = sorted({d.retrieved_at for d in assignment.source_documents
                    if d.is_usable_official and d.retrieved_at})
    return dates[0] if dates else ""


def rederive_pilot(pilot_dir: Path) -> List[Dict]:
    """Re-derive every persisted record; returns candidate records sorted by
    listing_key. Deterministic; no writes."""
    records: List[Dict] = []
    for bundle in load_pilot_records(pilot_dir):
        assignment = Assignment.from_dict(bundle["assignment"])
        v2_result = WorkerResult.from_dict(bundle["result"])
        env = bundle["envelope"]
        records.append(classify_record(
            assignment, v2_result,
            extraction_prompt_version=str(env.get("prompt_version", "")),
            extraction_validator_version=str(env.get("validator_version", "")),
            verification_date=_verification_date(assignment),
            v2_result_hash=str(bundle["result"].get("result_hash", "")),
            assignment_hash=str(bundle["assignment"].get("assignment_hash", "")
                               or _content_hash_hint(bundle["assignment"]))))
    return sorted(records, key=lambda r: r["listing_key"])


def _content_hash_hint(assignment_dict: Dict) -> str:
    # The persisted assignment file does not carry a separate assignment_hash
    # field; the candidate export does. Fall back to the assignment_id, which is
    # itself content-derived (…-<hash prefix>). Never fabricated.
    return str(assignment_dict.get("assignment_id", ""))


# --------------------------------------------------------------------------- #
# Deterministic artifact rendering (to the isolated gitignored review dir only).
# --------------------------------------------------------------------------- #

def build_manifest(records: List[Dict]) -> Dict:
    safe = [r for r in records if r["launch_safe"]]
    excluded = [r for r in records if not r["launch_safe"]]
    return {
        "schema": MANIFEST_SCHEMA_VERSION,
        "sprint": "PETTRIPFINDER-PROD-003",
        "gate": 1,
        "market": "columbus-oh",
        "frozen_worker_commit": FROZEN_WORKER_COMMIT,
        "rederivation_authority": {
            "validator_version": VALIDATOR_VERSION,
            "routing_version": RT.ROUTING_VERSION,
        },
        "source_pilot": "columbus_hotel_pilot_v2",
        "non_production": True,
        "auto_import": False,
        "counts": {
            "total": len(records),
            "launch_safe": len(safe),
            "manual_review": len(excluded),
        },
        "launch_safe_candidates": safe,
        "manual_review_candidates": excluded,
    }


def render_review_packet(records: List[Dict]) -> str:
    safe = [r for r in records if r["launch_safe"]]
    excluded = [r for r in records if not r["launch_safe"]]
    lines: List[str] = []
    lines.append("# PETTRIPFINDER-PROD-003 -- Gate 1 candidate review packet")
    lines.append("")
    lines.append("Offline re-derivation under the FROZEN AW-006 authority "
                 "(commit `%s`, validator %s, routing %s)."
                 % (FROZEN_WORKER_COMMIT, VALIDATOR_VERSION, RT.ROUTING_VERSION))
    lines.append("Source: `columbus_hotel_pilot_v2` (extraction under prompt 1.4.0). "
                 "No new model call; the v2 READY flags are NOT trusted.")
    lines.append("")
    lines.append("- Total records: **%d**" % len(records))
    lines.append("- Launch-safe: **%d**" % len(safe))
    lines.append("- Manual review: **%d**" % len(excluded))
    lines.append("")

    def _emit(r: Dict) -> None:
        lines.append("### %s" % r["listing_name"])
        lines.append("- candidate_identity (frozen result_hash): `%s`" % r["candidate_identity"])
        lines.append("- final route: **%s**  |  launch_safe: **%s**" % (r["final_route"], r["launch_safe"]))
        lines.append("- reason codes: %s" % (", ".join(r["reason_codes"]) or "(none)"))
        lines.append("- model: `%s`  |  extraction prompt: %s  |  extraction validator: %s"
                     % (r["model_id"], r["extraction_prompt_version"], r["extraction_validator_version"]))
        lines.append("- re-derivation: validator %s / routing %s (%s)"
                     % (r["rederivation_validator_version"], r["rederivation_routing_version"],
                        r["rederivation_method"]))
        lines.append("- verification date: %s" % (r["verification_date"] or "(unknown)"))
        lines.append("- source URL(s): %s" % ", ".join(r["source_urls"]))
        lines.append("- v2 result_hash: `%s`" % r["v2_result_hash"])
        lines.append("- multi-amount detected: %s %s"
                     % (r["multi_amount_detected"],
                        ("(%s)" % ", ".join(r["multi_amount_values"])) if r["multi_amount_values"] else ""))
        if r.get("manual_review_reason"):
            lines.append("- **manual-review reason:** %s" % r["manual_review_reason"])
        lines.append("- supported facts:")
        if r["supported_facts"]:
            for f in r["supported_facts"]:
                lines.append("    - `%s` = `%s`  <- \"%s\"  [%s]"
                             % (f["field_name"], f["value"], f["evidence_quote"], f["source_url"]))
        else:
            lines.append("    - (none)")
        lines.append("")

    lines.append("## Launch-safe candidates")
    lines.append("")
    for r in safe:
        _emit(r)
    lines.append("## Manual-review candidates (excluded)")
    lines.append("")
    for r in excluded:
        _emit(r)
    return "\n".join(lines) + "\n"


def build_exclusion_report(records: List[Dict]) -> Dict:
    excluded = [r for r in records if not r["launch_safe"]]
    return {
        "schema": MANIFEST_SCHEMA_VERSION,
        "sprint": "PETTRIPFINDER-PROD-003",
        "gate": 1,
        "frozen_worker_commit": FROZEN_WORKER_COMMIT,
        "count": len(excluded),
        "excluded": [
            {
                "listing_name": r["listing_name"],
                "candidate_identity": r["candidate_identity"],
                "final_route": r["final_route"],
                "reason_codes": r["reason_codes"],
                "multi_amount_detected": r["multi_amount_detected"],
                "multi_amount_values": r["multi_amount_values"],
                "v2_status": r["v2_status"],
                "v2_contradictions": r["v2_contradictions"],
                "manual_review_reason": r["manual_review_reason"],
            }
            for r in excluded
        ],
    }


def _write_json(path: Path, payload: Dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def run(pilot_dir: Path = DEFAULT_PILOT_DIR, review_dir: Path = DEFAULT_REVIEW_DIR) -> Dict:
    """Re-derive and write the three Gate-1 review artifacts to ``review_dir``
    (which MUST be an isolated, gitignored directory). Returns the manifest.
    Writes nothing outside ``review_dir``."""
    records = rederive_pilot(pilot_dir)
    manifest = build_manifest(records)
    review_dir.mkdir(parents=True, exist_ok=True)
    _write_json(review_dir / "launch_safe_manifest.json", manifest)
    _write_json(review_dir / "exclusion_report.json", build_exclusion_report(records))
    (review_dir / "review_packet.md").write_text(render_review_packet(records), encoding="utf-8")
    return manifest


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot-dir", default=str(DEFAULT_PILOT_DIR))
    ap.add_argument("--review-dir", default=str(DEFAULT_REVIEW_DIR))
    args = ap.parse_args(argv)
    pilot_dir = Path(args.pilot_dir)
    if not (pilot_dir / "validated_results").exists():
        raise SystemExit(
            "pilot dir %s has no validated_results/ -- the gitignored v2 runtime "
            "artifacts are required and must not be committed." % pilot_dir)
    manifest = run(pilot_dir, Path(args.review_dir))
    c = manifest["counts"]
    print("PROD-003 Gate 1: %d launch-safe / %d manual-review (of %d) under frozen %s"
          % (c["launch_safe"], c["manual_review"], c["total"], VALIDATOR_VERSION))
    print("Review artifacts written to: %s" % args.review_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
