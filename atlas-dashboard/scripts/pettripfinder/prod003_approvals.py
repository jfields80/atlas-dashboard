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
import re
from pathlib import Path
from typing import Dict, List, Optional

SCHEMA_ID = "ptf-prod003-approvals/1.0"
ROUTE_READY = "READY"

DECISION_APPROVED = "APPROVED_FOR_PROMOTION"
DECISION_HOLD = "HOLD_FOR_MANUAL_REVIEW"
DECISION_REJECTED = "REJECTED"
DECISION_SUPERSEDED = "SUPERSEDED"
# PTF-INVENTORY-001. A NARROW, hotel-specific authorization to promote a record
# whose ONLY blocking Gate-1 reason is STRUCTURED_FEE_REQUIRED -- i.e. the
# property publishes a genuine tiered or capped pet fee that the single-scalar
# production schema cannot represent.
#
# Business policy: a valid tiered fee is not a contradiction, and the renderer's
# inability to show two numbers must not suppress otherwise-credible
# pet-friendly inventory. The fee STRUCTURE is preserved in provenance and the
# scalar field is OMITTED -- never flattened to one misleading number.
#
# This is deliberately not a bypass. It waives exactly one reason code, only for
# the named hotel, only against the exact frozen result_hash, and it cannot
# clear a contradiction, an incomplete extraction, an identity conflict, or
# source-authority ambiguity. Those still fail closed.
DECISION_TIERED_FEE_OMITTED = "APPROVED_TIERED_FEE_OMITTED"
# PTF-WORKERS-007. A NARROW authorization to promote a record whose policy text
# came from an official search surface bound to a separately captured property
# page. It waives ONLY PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW, and only when
# all four strong binding signals were recorded AND the approval is bound to
# both capture hashes plus the attestation hash. Alter any of the three and the
# approval goes stale -- which is the point: an approval must apply to exactly
# the evidence a human looked at, not to whatever later occupies its slot.
DECISION_PAIRED_OFFICIAL_SOURCE = "APPROVED_PAIRED_OFFICIAL_SOURCE"
# PTF-WORKERS. An approval for a record whose only remaining reason is an
# APPROVAL-ELIGIBLE DIAGNOSTIC -- a note about what the airlock DID, not a
# defect being tolerated.
#
# It is deliberately NOT called a waiver, and MODEL_OVERCLAIM is deliberately
# not in WAIVABLE_REASON_CODES, because nothing unsupported is being accepted:
# the model's invented claim was rejected, removed, and never published. What a
# waiver does is carry a known defect into production; what this does is record
# that a human saw the diagnostic and the record is sound without it.
#
# It cannot clear anything else. A record carrying a contradiction, a genuine
# incomplete extraction, an identity or source-authority failure, or any other
# never-waivable reason is refused exactly as before -- the diagnostic must be
# the ONLY reason present.
DECISION_DIAGNOSTIC_ACKNOWLEDGED = "APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT"
ALLOWED_DECISIONS = (DECISION_APPROVED, DECISION_HOLD, DECISION_REJECTED,
                     DECISION_SUPERSEDED, DECISION_TIERED_FEE_OMITTED,
                     DECISION_PAIRED_OFFICIAL_SOURCE,
                     DECISION_DIAGNOSTIC_ACKNOWLEDGED)

# The ONLY reason codes these decisions may waive, one frozenset per decision.
# Kept separate so a widening is a visible, reviewable edit rather than a
# passing thought, and so neither decision can ever clear the other's blocker.
WAIVABLE_REASON_CODES = frozenset({"STRUCTURED_FEE_REQUIRED"})
PAIRED_WAIVABLE_REASON_CODES = frozenset({"PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW"})
# Reasons that must NEVER be waivable, asserted by test. Listing them explicitly
# documents the intent to a future reader who is tempted to add "just one more".
NEVER_WAIVABLE_REASON_CODES = frozenset({
    "CONTRADICTORY_OFFICIAL_SOURCES", "INCOMPLETE_EXTRACTION",
    "SOURCE_AUTHORITY_AMBIGUITY", "MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE",
    "INHERITED_IDENTITY_REQUIRES_REVIEW", "UNSAFE_RESULT",
})
# PTF-WORKERS. A THIRD category, distinct from both of the above: reasons that
# record what the airlock DID rather than a defect it tolerated.
#
# MODEL_OVERCLAIM means an unsupported model claim was caught, rejected and
# removed. There is no bad fact in the record to waive -- the record is sound
# BECAUSE the claim is gone. Filing it under WAIVABLE would say the opposite,
# and filing it under NEVER_WAIVABLE would hold a clean record forever for a
# note about a claim that never reached it.
#
# Membership here does NOT make a record approvable on its own: it only means
# this reason, ALONE, does not block. Every other gate is unchanged, and a
# human must still acknowledge the diagnostic explicitly on the approval.
APPROVAL_ELIGIBLE_WARNING_CODES = frozenset({"MODEL_OVERCLAIM"})
# Extra fields REQUIRED on a tiered-fee approval and permitted on no other.
TIERED_FEE_FIELDS = ("waived_reason_codes", "preserved_fee_amounts")
# Extra fields REQUIRED on a paired-source approval and permitted on no other.
PAIRED_SOURCE_FIELDS = ("waived_reason_codes", "identity_capture_url",
                        "identity_text_hash", "policy_capture_url",
                        "policy_text_hash", "matched_signals",
                        "attestation_hash")
# Extra fields REQUIRED on a diagnostic-acknowledgement approval and permitted
# on no other. The acknowledgement is the point of the decision: the diagnostic
# must be named, and what the model claimed and why it was rejected must survive
# in the approval record, so an approved hotel never loses the fact that
# something was thrown away to make it clean.
DIAGNOSTIC_ACK_FIELDS = ("acknowledged_reason_codes", "acknowledged_warnings")
# All four must be recorded. A three-of-four pairing is not a weaker pairing;
# it is an unproven one.
REQUIRED_BINDING_SIGNALS = ("address_exact", "name_exact", "phone_exact",
                            "property_code")

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
        decision = a.get("decision")
        if decision == DECISION_TIERED_FEE_OMITTED:
            allowed_extra = set(TIERED_FEE_FIELDS)
        elif decision == DECISION_PAIRED_OFFICIAL_SOURCE:
            allowed_extra = set(PAIRED_SOURCE_FIELDS)
        elif decision == DECISION_DIAGNOSTIC_ACKNOWLEDGED:
            allowed_extra = set(DIAGNOSTIC_ACK_FIELDS)
        else:
            allowed_extra = set()
        extra = (set(a) - set(APPROVAL_REQUIRED_FIELDS) - set(APPROVAL_OPTIONAL_FIELDS)
                 - allowed_extra)
        if extra:
            errors.append("approval[%d]:unexpected_fields:%s" % (i, ",".join(sorted(extra))))
        if decision not in ALLOWED_DECISIONS:
            errors.append("approval[%d]:invalid_decision" % i)
        if decision == DECISION_APPROVED and a.get("gate1_route") != ROUTE_READY:
            errors.append("approval[%d]:approved_requires_ready_route" % i)
        if decision == DECISION_TIERED_FEE_OMITTED:
            errors.extend(_tiered_fee_errors(i, a))
        if decision == DECISION_PAIRED_OFFICIAL_SOURCE:
            errors.extend(_paired_source_errors(i, a))
        if decision == DECISION_DIAGNOSTIC_ACKNOWLEDGED:
            errors.extend(_diagnostic_ack_errors(i, a))
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
                # A tiered-fee approval exists precisely FOR a manual-review
                # record; applying one to a launch-safe record would be
                # meaningless and is refused so the decision cannot drift into
                # a general-purpose rubber stamp.
                if decision == DECISION_TIERED_FEE_OMITTED and g["launch_safe"]:
                    errors.append("approval[%d]:tiered_fee_requires_manual_review_record" % i)
                if decision == DECISION_PAIRED_OFFICIAL_SOURCE and g["launch_safe"]:
                    errors.append("approval[%d]:paired_source_requires_manual_review_record" % i)
    return sorted(errors)


_SHA256_HEX = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def _diagnostic_ack_errors(i: int, a: Dict) -> List[str]:
    """Extra structural rules for APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT.

    The decision exists to record that a human SAW a diagnostic, so an approval
    that names none is meaningless. The acknowledged codes must be exactly the
    approval-eligible ones -- this decision can never reach a waivable reason,
    let alone a never-waivable one -- and the underlying warnings must be
    carried verbatim, so the fact that a claim was rejected and removed survives
    into the approval record rather than disappearing with it.
    """
    errors: List[str] = []
    if a.get("gate1_route") == ROUTE_READY:
        # A READY record has no diagnostic to acknowledge; using this decision
        # there would turn it into a general-purpose rubber stamp.
        errors.append("approval[%d]:diagnostic_ack_requires_review_route" % i)

    codes = a.get("acknowledged_reason_codes")
    if not isinstance(codes, list) or not codes:
        errors.append("approval[%d]:diagnostic_ack_requires_reason_codes" % i)
    else:
        illegal = sorted(set(codes) - APPROVAL_ELIGIBLE_WARNING_CODES)
        if illegal:
            errors.append("approval[%d]:not_approval_eligible_reason_codes:%s"
                          % (i, ",".join(illegal)))

    warnings = a.get("acknowledged_warnings")
    if not isinstance(warnings, list) or not warnings:
        errors.append("approval[%d]:diagnostic_ack_requires_warnings" % i)
    elif not all(isinstance(w, str) and w.strip() for w in warnings):
        errors.append("approval[%d]:diagnostic_ack_warnings_must_be_text" % i)
    return errors


def _paired_source_errors(i: int, a: Dict) -> List[str]:
    """Extra structural rules for APPROVED_PAIRED_OFFICIAL_SOURCE.

    Three independent bindings must hold: to the identity capture, to the
    policy capture, and to the attestation that joined them. Any one of the
    three going stale invalidates the approval, because an approval that could
    outlive its evidence is not an approval, it is a standing permission.
    """
    errors: List[str] = []
    if a.get("gate1_route") == ROUTE_READY:
        errors.append("approval[%d]:paired_source_requires_review_route" % i)

    waived = a.get("waived_reason_codes")
    if not isinstance(waived, list) or not waived:
        errors.append("approval[%d]:paired_source_requires_waived_reason_codes" % i)
    else:
        illegal = sorted(set(waived) - PAIRED_WAIVABLE_REASON_CODES)
        if illegal:
            errors.append("approval[%d]:non_waivable_reason_codes:%s"
                          % (i, ",".join(illegal)))

    signals = a.get("matched_signals")
    if not isinstance(signals, list):
        errors.append("approval[%d]:paired_source_requires_matched_signals" % i)
    else:
        missing = sorted(set(REQUIRED_BINDING_SIGNALS) - set(signals))
        if missing:
            errors.append("approval[%d]:missing_binding_signals:%s"
                          % (i, ",".join(missing)))

    # Both captures must be hash-bound, and they must be different pages: the
    # same file cited twice would let one capture stand as its own corroboration.
    id_hash = str(a.get("identity_text_hash") or "")
    pol_hash = str(a.get("policy_text_hash") or "")
    for label, value in (("identity_text_hash", id_hash),
                         ("policy_text_hash", pol_hash),
                         ("attestation_hash", str(a.get("attestation_hash") or ""))):
        if not _SHA256_HEX.match(value):
            errors.append("approval[%d]:invalid_%s" % (i, label))
    if id_hash and id_hash == pol_hash:
        errors.append("approval[%d]:identity_and_policy_captures_identical" % i)

    # The cited source_url must be the property page, never the search surface.
    id_url = str(a.get("identity_capture_url") or "")
    pol_url = str(a.get("policy_capture_url") or "")
    if not id_url or not pol_url:
        errors.append("approval[%d]:paired_source_requires_both_capture_urls" % i)
    elif str(a.get("source_url") or "") != id_url:
        errors.append("approval[%d]:source_url_must_be_the_identity_capture" % i)
    return errors


def _tiered_fee_errors(i: int, a: Dict) -> List[str]:
    """Extra structural rules for APPROVED_TIERED_FEE_OMITTED."""
    errors: List[str] = []
    if a.get("gate1_route") == ROUTE_READY:
        # A READY record has nothing to waive.
        errors.append("approval[%d]:tiered_fee_requires_review_route" % i)

    waived = a.get("waived_reason_codes")
    if not isinstance(waived, list) or not waived:
        errors.append("approval[%d]:missing_waived_reason_codes" % i)
    else:
        illegal = sorted(set(waived) - WAIVABLE_REASON_CODES)
        if illegal:
            errors.append("approval[%d]:non_waivable_reason_codes:%s" % (i, ",".join(illegal)))

    amounts = a.get("preserved_fee_amounts")
    if not isinstance(amounts, list) or len(amounts) < 2:
        # Fewer than two amounts is not a tiered fee, so the decision does not
        # apply -- this is what stops it being used on an ordinary blocked record.
        errors.append("approval[%d]:tiered_fee_requires_two_or_more_amounts" % i)
    return errors


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
