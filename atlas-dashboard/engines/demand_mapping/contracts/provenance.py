"""Canonical provenance model (AES-SEO-001 §5, operator decision AMB-3).

Defined fresh for this subsystem — no legacy TaggedValue variant is imported
or retrofitted. This module is the single home of the provenance vocabulary,
the one provenance-priority order (§5.2a), and the tagged value carrier.

Binding rules encoded here:
* ESTIMATED can never be represented, upgraded, or merged into VERIFIED —
  merging selects between values; it never rewrites a provenance tag.
* UNKNOWN carries no confidence value (§5.3); every other state must.
* Observation timestamps are explicit input strings; nothing in this module
  reads a clock (§5.2f).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, StrictInt, StrictStr

from engines.demand_mapping.contracts.canonical import (
    ContractValidationError,
    FrozenModel,
)


class Provenance(str, Enum):
    """The five canonical epistemic states (AES-SEO-001 §5.1)."""

    VERIFIED = "VERIFIED"
    ESTIMATED = "ESTIMATED"
    DERIVED = "DERIVED"
    OPERATOR = "OPERATOR"
    UNKNOWN = "UNKNOWN"


# The single provenance-priority order (§5.2a). Higher wins in merges.
# VERIFIED outranks OPERATOR: a live external source returning the specific
# value is stronger than human attestation about it; both outrank anything
# computed or modeled. This table is versioned data — changing it is an
# evidence-model version bump (§19.1).
PROVENANCE_PRIORITY: Dict[Provenance, int] = {
    Provenance.VERIFIED: 5,
    Provenance.OPERATOR: 4,
    Provenance.DERIVED: 3,
    Provenance.ESTIMATED: 2,
    Provenance.UNKNOWN: 1,
}

# Confidence is integer basis points on a closed 0..10000 scale (§5.3).
CONFIDENCE_BP_MIN: int = 0
CONFIDENCE_BP_MAX: int = 10000


def stronger_provenance(first: Provenance, second: Provenance) -> Provenance:
    """The higher-priority of two provenance states (ties keep ``first``)."""
    if PROVENANCE_PRIORITY[second] > PROVENANCE_PRIORITY[first]:
        return second
    return first


class TaggedValue(FrozenModel):
    """An integer value that always carries its epistemic state (§5).

    ``observed_at`` is an ISO-8601 string supplied by the service layer as
    explicit input data — the deterministic core never creates timestamps.
    """

    value: StrictInt = Field(...)
    provenance: Provenance = Field(...)
    provider_id: StrictStr = Field(...)
    provider_version: StrictStr = Field(...)
    rationale: StrictStr = Field(...)
    confidence_bp: Optional[StrictInt] = Field(None)
    observed_at: StrictStr = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_tagged_value(self)


def validate_confidence_bp(
    provenance: Provenance, confidence_bp: Optional[int]
) -> None:
    """§5.3: UNKNOWN carries no confidence; every other state must, in range."""
    if provenance is Provenance.UNKNOWN:
        if confidence_bp is not None:
            raise ContractValidationError(
                "UNKNOWN provenance must not carry a confidence value (§5.3)"
            )
        return
    if confidence_bp is None:
        raise ContractValidationError(
            "provenance %s requires an integer confidence_bp (§5.3)"
            % provenance.value
        )
    if not (CONFIDENCE_BP_MIN <= confidence_bp <= CONFIDENCE_BP_MAX):
        raise ContractValidationError(
            "confidence_bp %d outside [%d, %d]"
            % (confidence_bp, CONFIDENCE_BP_MIN, CONFIDENCE_BP_MAX)
        )


def validate_tagged_value(tagged: TaggedValue) -> None:
    """All semantic rules for a TaggedValue instance."""
    if not tagged.provider_id:
        raise ContractValidationError("provider_id must be non-empty (§5.2e)")
    if not tagged.provider_version:
        raise ContractValidationError(
            "provider_version must be non-empty (§5.2e)"
        )
    if not tagged.rationale:
        raise ContractValidationError(
            "rationale must be non-empty — every value explains its origin"
        )
    if not tagged.observed_at:
        raise ContractValidationError(
            "observed_at must be a non-empty explicit timestamp string (§5.2f)"
        )
    validate_confidence_bp(tagged.provenance, tagged.confidence_bp)


def merge_tagged_values(first: TaggedValue, second: TaggedValue) -> TaggedValue:
    """Select the stronger of two tagged values (§5.2a).

    Selection only — the returned object is one of the two inputs, with its
    provenance tag untouched. ESTIMATED can therefore never become VERIFIED
    through merging. Priority: provenance order, then higher confidence,
    then ``first`` (deterministic tie-break).
    """
    first_priority = PROVENANCE_PRIORITY[first.provenance]
    second_priority = PROVENANCE_PRIORITY[second.provenance]
    if second_priority > first_priority:
        return second
    if second_priority < first_priority:
        return first
    first_confidence = first.confidence_bp or 0
    second_confidence = second.confidence_bp or 0
    if second_confidence > first_confidence:
        return second
    return first
