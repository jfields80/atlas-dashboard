"""AES-DATA-001 importer -- deterministic READY / REVIEW / REJECT logic
(mission section 15). Candidate recommendation is NOT launch readiness; a
READY candidate still flows through the existing inventory validation on
promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from scripts.pettripfinder.importer import constants as C


@dataclass(frozen=True)
class RecommendationInput:
    fetch_ok: bool
    fetch_reason: str                    # slug when fetch not ok
    source_relationship: str
    entity_identified: bool
    category_resolved: bool
    missing_required: Tuple[str, ...]
    pet_policy_present: bool
    pets_allowed_state: str              # "true" | "false" | "" (unknown)
    has_material_conflict: bool
    multi_entity: bool
    required_evidence_mismatch: bool     # a required policy fact failed span check
    ambiguous_present: bool
    extraction_ok: bool
    text_truncated: bool
    # AES-DATA-002B multi-source aggregation signals (defaulted: every
    # existing single-source constructor call remains valid and unaffected).
    sources_excluded: bool = False           # a supplemental was gated out or failed
    aggregate_identity_conflict: bool = False
    aggregate_geography_conflict: bool = False
    aggregate_policy_conflict: bool = False  # a pooled pet-fact conflict
    # AES-DATA-003B (additive; defaults preserve every existing call site's
    # exact behavior byte-for-byte). Generalizes "this category's positive
    # service evidence exists" beyond pet-friendliness: when a caller leaves
    # ``service_evidence_present`` at its default (None), the hard REJECT
    # gate below falls back to ``pet_policy_present`` exactly as before --
    # only the veterinary path (candidate.py/aggregate.py) explicitly
    # supplies both new fields.
    service_evidence_present: Optional[bool] = None
    no_service_evidence_reason: str = C.REASON_NO_PET_EVIDENCE
    # A conflicting HIGH-RISK capability (e.g. one source says 24/7
    # emergency, another says limited hours) -- veterinary-only today,
    # False for every existing caller.
    high_risk_capability_conflict: bool = False


def recommend(inp: RecommendationInput) -> Tuple[str, Tuple[str, ...]]:
    """Return ``(recommendation, reasons)``."""
    reasons = []

    # 1. Fetch-level outcomes short-circuit.
    if not inp.fetch_ok:
        if inp.fetch_reason in C.REJECT_FETCH_REASONS:
            return (C.RECOMMEND_REJECT, (inp.fetch_reason,))
        if inp.fetch_reason in C.REVIEW_FETCH_REASONS:
            return (C.RECOMMEND_REVIEW, (inp.fetch_reason,))
        # Unknown fetch failure -> reject conservatively.
        return (C.RECOMMEND_REJECT, (inp.fetch_reason or C.REASON_FETCH_FAILED,))

    # 2. Hard REJECTs.
    if inp.source_relationship == C.REL_THIRD_PARTY:
        return (C.RECOMMEND_REJECT, (C.REASON_UNCERTAIN_SOURCE_RELATIONSHIP,))
    if inp.pets_allowed_state == "false":
        return (C.RECOMMEND_REJECT, (C.REASON_NO_PETS,))
    if not inp.entity_identified:
        return (C.RECOMMEND_REJECT, (C.REASON_ENTITY_MISMATCH,))
    # AES-DATA-003B: "positive service evidence exists" generalized beyond
    # pet-friendliness. inp.service_evidence_present is None for every
    # existing (lodging/parks/dining) caller, so effective_evidence_present
    # is BYTE-IDENTICAL to the old ``inp.pet_policy_present`` check for
    # them; only the veterinary path passes an explicit bool.
    effective_evidence_present = (
        inp.pet_policy_present if inp.service_evidence_present is None
        else inp.service_evidence_present)
    # A pooled aggregate policy conflict (e.g. one source says pets_allowed
    # true, another says false) means genuine pet-related evidence DOES
    # exist -- it just disagrees. REVIEW is the correct outcome; the
    # no-evidence REJECT below would be actively misleading, so an
    # aggregate policy conflict withdraws it (AES-DATA-002B doctrine: "mixed
    # true/false -> policy_conflict REVIEW, never automatic REJECT").
    if (not effective_evidence_present and inp.pets_allowed_state != "true"
            and not inp.aggregate_policy_conflict):
        return (C.RECOMMEND_REJECT, (inp.no_service_evidence_reason,))
    if inp.required_evidence_mismatch:
        return (C.RECOMMEND_REJECT, (C.REASON_EVIDENCE_MISMATCH,))

    # 3. REVIEW conditions (accumulate).
    if inp.source_relationship == C.REL_UNKNOWN:
        reasons.append(C.REASON_UNCERTAIN_SOURCE_RELATIONSHIP)
    if inp.multi_entity:
        reasons.append(C.REASON_MULTI_ENTITY)
    if inp.has_material_conflict:
        reasons.append(C.REASON_CONFLICTING_EVIDENCE)
    if not inp.extraction_ok:
        reasons.append(C.REASON_EXTRACTION_UNPARSEABLE)
    if not inp.category_resolved:
        reasons.append(C.REASON_MISSING_REQUIRED_FIELD)
    for field in inp.missing_required:
        reasons.append("%s:%s" % (C.REASON_MISSING_REQUIRED_FIELD, field))
    if inp.ambiguous_present:
        reasons.append(C.REASON_CONFLICTING_EVIDENCE if False else "ambiguous_field")
    if inp.text_truncated and not effective_evidence_present:
        reasons.append("truncated_source_missing_policy")
    if inp.sources_excluded:
        reasons.append(C.REASON_INCOMPLETE_SOURCE_SET)
    if inp.aggregate_identity_conflict:
        reasons.append(C.REASON_IDENTITY_CONFLICT)
    if inp.aggregate_geography_conflict:
        reasons.append(C.REASON_GEOGRAPHY_CONFLICT)
    if inp.aggregate_policy_conflict:
        reasons.append(C.REASON_POLICY_CONFLICT)
    if inp.high_risk_capability_conflict:
        reasons.append(C.REASON_VETERINARY_CAPABILITY_CONFLICT)

    if reasons:
        return (C.RECOMMEND_REVIEW, tuple(reasons))

    # 4. READY.
    return (C.RECOMMEND_READY, ())
