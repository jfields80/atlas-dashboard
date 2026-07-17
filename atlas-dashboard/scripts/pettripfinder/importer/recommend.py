"""AES-DATA-001 importer -- deterministic READY / REVIEW / REJECT logic
(mission section 15). Candidate recommendation is NOT launch readiness; a
READY candidate still flows through the existing inventory validation on
promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

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
    if not inp.pet_policy_present and inp.pets_allowed_state != "true":
        return (C.RECOMMEND_REJECT, (C.REASON_NO_PET_EVIDENCE,))
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
    if inp.text_truncated and not inp.pet_policy_present:
        reasons.append("truncated_source_missing_policy")

    if reasons:
        return (C.RECOMMEND_REVIEW, tuple(reasons))

    # 4. READY.
    return (C.RECOMMEND_READY, ())
