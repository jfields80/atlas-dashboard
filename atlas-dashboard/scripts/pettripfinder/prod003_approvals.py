"""PETTRIPFINDER-PROD-003 Gate 2 (Stage A) -- worker-promotion approval contract:
parsing, deterministic validation, and serialization.

This module implements ONLY the approval contract. It records NO approval
decisions, promotes NO records, and writes NOTHING to the operational corpus,
the committed launch package, the renderer, or any site. It is pure and
deterministic: it reads no wall clock and copies no raw model output, credential,
or bulk runtime artifact -- an approval carries only the record's binding
identity (result_hash, source URL, verification date, Gate-1 route) plus the
human-supplied decision/operator/date.

An approval binds to a frozen Gate-1 ``result_hash``. Promotion (a later stage)
re-derives the current Gate-1 manifest and refuses any approval whose hash no
longer matches -- so a changed or stale record automatically invalidates its
approval, and a record with no approval is never promoted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

SCHEMA_ID = "ptf-prod003-approvals/1.0"
ROUTE_READY = "READY"

DECISION_APPROVED = "APPROVED_FOR_PROMOTION"
DECISION_HOLD = "HOLD_FOR_MANUAL_REVIEW"
DECISION_REJECTED = "REJECTED"
DECISION_SUPERSEDED = "SUPERSEDED"
ALLOWED_DECISIONS = (DECISION_APPROVED, DECISION_HOLD, DECISION_REJECTED, DECISION_SUPERSEDED)

# Every recorded approval entry requires these (note is optional).
APPROVAL_REQUIRED_FIELDS = (
    "listing_key", "listing_name", "result_hash", "source_url",
    "verification_date", "gate1_route", "decision", "operator", "approval_date")
APPROVAL_OPTIONAL_FIELDS = ("note",)
# A pending candidate carries only the binding identity -- never a decision,
# operator, or date (those are recorded by a human later, entry by entry).
PENDING_FIELDS = (
    "listing_key", "listing_name", "result_hash", "source_url",
    "verification_date", "gate1_route")
_PENDING_FORBIDDEN = ("decision", "operator", "approval_date", "note")


def serialize(manifest: Dict) -> str:
    """Deterministic canonical JSON: keys sorted, and the approvals/pending arrays
    sorted by (listing_key, result_hash). No wall clock is read."""
    m = dict(manifest)
    for arr in ("approvals", "pending_candidates"):
        if isinstance(m.get(arr), list):
            m[arr] = sorted(m[arr], key=lambda a: (str(a.get("listing_key", "")),
                                                   str(a.get("result_hash", ""))))
    return json.dumps(m, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def load_manifest(path: Path) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def gate1_index(gate1_manifest: Dict) -> Dict[str, Dict]:
    """Map listing_key -> {result_hash, launch_safe, gate1_route} from a Gate-1
    launch-safety manifest. The result_hash is the frozen candidate identity."""
    idx: Dict[str, Dict] = {}
    for r in gate1_manifest.get("launch_safe_candidates", []):
        idx[r["listing_key"]] = {"result_hash": r["candidate_identity"],
                                 "launch_safe": True, "gate1_route": r["final_route"]}
    for r in gate1_manifest.get("manual_review_candidates", []):
        idx[r["listing_key"]] = {"result_hash": r["candidate_identity"],
                                 "launch_safe": False, "gate1_route": r["final_route"]}
    return idx


def validate_manifest(manifest: Dict, *, gate1_idx: Optional[Dict[str, Dict]] = None) -> List[str]:
    """Deterministically validate an approval manifest. Returns a sorted list of
    error slugs (empty == valid). When ``gate1_idx`` is supplied, approvals are
    additionally checked against the current Gate-1 authority (stale-hash and
    manual-review exclusion)."""
    errors: List[str] = []
    if manifest.get("schema") != SCHEMA_ID:
        errors.append("schema:expected_%s" % SCHEMA_ID)
    if not str(manifest.get("market", "")).strip():
        errors.append("market:missing")

    pending = manifest.get("pending_candidates", [])
    if not isinstance(pending, list):
        errors.append("pending_candidates:not_a_list")
        pending = []
    for i, p in enumerate(pending):
        for f in PENDING_FIELDS:
            if not str(p.get(f, "")).strip():
                errors.append("pending[%d]:missing_%s" % (i, f))
        for f in _PENDING_FORBIDDEN:
            if f in p:
                errors.append("pending[%d]:must_not_carry_%s" % (i, f))  # no fabricated decisions

    approvals = manifest.get("approvals", [])
    if not isinstance(approvals, list):
        return sorted(errors + ["approvals:not_a_list"])
    seen_key, seen_hash = set(), set()
    for i, a in enumerate(approvals):
        for f in APPROVAL_REQUIRED_FIELDS:
            if not str(a.get(f, "")).strip():          # operator/approval_date must be human-supplied
                errors.append("approval[%d]:missing_%s" % (i, f))
        extra = set(a) - set(APPROVAL_REQUIRED_FIELDS) - set(APPROVAL_OPTIONAL_FIELDS)
        if extra:
            errors.append("approval[%d]:unexpected_fields:%s" % (i, ",".join(sorted(extra))))
        decision = a.get("decision")
        if decision not in ALLOWED_DECISIONS:
            errors.append("approval[%d]:invalid_decision" % i)
        if decision == DECISION_APPROVED and a.get("gate1_route") != ROUTE_READY:
            errors.append("approval[%d]:approved_requires_ready_route" % i)
        key, rhash = a.get("listing_key"), a.get("result_hash")
        if key in seen_key:
            errors.append("approval[%d]:duplicate_listing_key" % i)
        if rhash in seen_hash:
            errors.append("approval[%d]:duplicate_result_hash" % i)
        seen_key.add(key)
        seen_hash.add(rhash)
        if gate1_idx is not None:
            g = gate1_idx.get(key)
            if g is None:
                errors.append("approval[%d]:unknown_listing_key" % i)
            else:
                if rhash != g["result_hash"]:
                    errors.append("approval[%d]:stale_result_hash" % i)
                if decision == DECISION_APPROVED and not g["launch_safe"]:
                    errors.append("approval[%d]:manual_review_cannot_be_approved" % i)
    return sorted(errors)


def is_valid(manifest: Dict, *, gate1_idx: Optional[Dict[str, Dict]] = None) -> bool:
    return not validate_manifest(manifest, gate1_idx=gate1_idx)


def approved_for_promotion(manifest: Dict) -> List[Dict]:
    """The APPROVED_FOR_PROMOTION entries, deterministically ordered. (Used by a
    later promotion stage; here only so the contract is complete and testable.)"""
    return sorted((a for a in manifest.get("approvals", [])
                   if a.get("decision") == DECISION_APPROVED),
                  key=lambda a: (str(a.get("listing_key", "")), str(a.get("result_hash", ""))))


def build_pending_manifest(gate1_manifest: Dict, committed_keys, *, frozen_worker_commit: str,
                           gate1_commit: str, gate1_manifest_sha256: str,
                           market: str = "columbus-oh") -> Dict:
    """Build the INITIAL approval manifest: an empty approvals list plus one
    pending-candidate identity per launch-safe hotel that is NOT already in the
    committed launch package (the recommended 10-new-hotel launch path -- the 5
    overlaps are left untouched). No decision, operator, or date is invented."""
    committed = set(committed_keys)
    pending = [
        {"listing_key": r["listing_key"], "listing_name": r["listing_name"],
         "result_hash": r["candidate_identity"], "source_url": (r.get("source_urls") or [""])[0],
         "verification_date": r.get("verification_date", ""), "gate1_route": r["final_route"]}
        for r in gate1_manifest.get("launch_safe_candidates", [])
        if r["listing_key"] not in committed]
    return {
        "schema": SCHEMA_ID,
        "market": market,
        "bound_to": {
            "frozen_worker_commit": frozen_worker_commit,
            "gate1_commit": gate1_commit,
            "gate1_manifest_sha256": gate1_manifest_sha256,
        },
        "note": ("Stage-A initial manifest. approvals is intentionally empty: no "
                 "approval decisions have been recorded. pending_candidates lists the "
                 "10 launch-safe worker hotels not yet in the committed package, each "
                 "bound to its frozen Gate-1 result_hash, awaiting per-record human "
                 "review. The 5 overlapping hotels keep their committed importer facts."),
        "pending_candidates": pending,
        "approvals": [],
    }
