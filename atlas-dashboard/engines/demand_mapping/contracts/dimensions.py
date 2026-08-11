"""Inventory dimension contracts (AES-SEO-001 §7).

A ``DimensionProfile`` is the deterministic profiler's description of one
discovered dimension of a project's inventory, expressed entirely in
generic, integer-only statistics. Field names from the source project are
carried as opaque identifiers; generic planning rules speak only in profile
terms, never in project value terms (§7.5 — enforced by the
domain-neutrality test).

All statistics are integers (AMB-4). Fractional quantities use declared
integer scales (``NumericSummary.scale_denominator``).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Tuple

from pydantic import Field, StrictInt, StrictStr

from engines.demand_mapping.contracts.canonical import (
    ContractValidationError,
    FrozenModel,
    canonical_json,
    sha256_of_text,
)


class DimensionKind(str, Enum):
    """Closed dimension-kind vocabulary (§7.3)."""

    CATEGORICAL = "CATEGORICAL"
    NUMERIC = "NUMERIC"
    BOOLEAN = "BOOLEAN"
    GEOGRAPHIC = "GEOGRAPHIC"
    ENTITY_REF = "ENTITY_REF"
    TEXT = "TEXT"


class FrequencyEntry(FrozenModel):
    """One value of a dimension and how many entities carry it."""

    value_label: StrictStr = Field(...)
    entity_count: StrictInt = Field(...)


class NumericSummary(FrozenModel):
    """Integer-scaled numeric range (§4.4 — no floats, declared scale)."""

    minimum_scaled: StrictInt = Field(...)
    maximum_scaled: StrictInt = Field(...)
    scale_denominator: StrictInt = Field(...)


class ProvenanceCoverage(FrozenModel):
    """How many present values carry each provenance state (§7.4).

    Untagged source values count as UNKNOWN; the five counts partition the
    covered values exactly.
    """

    verified_count: StrictInt = Field(...)
    estimated_count: StrictInt = Field(...)
    derived_count: StrictInt = Field(...)
    operator_count: StrictInt = Field(...)
    unknown_count: StrictInt = Field(...)


class CoOccurrence(FrozenModel):
    """Co-presence of this dimension with another (§7.4)."""

    other_dimension_id: StrictStr = Field(...)
    co_present_count: StrictInt = Field(...)


class DimensionProfile(FrozenModel):
    """Deterministic profile of one inventory dimension (§7.4)."""

    schema_version: StrictStr = Field(...)
    dimension_id: StrictStr = Field(...)
    source_field_path: StrictStr = Field(...)
    kind: DimensionKind = Field(...)
    entity_count: StrictInt = Field(...)
    coverage_count: StrictInt = Field(...)
    missing_count: StrictInt = Field(...)
    distinct_count: StrictInt = Field(...)
    frequencies: Tuple[FrequencyEntry, ...] = Field(...)
    numeric_summary: Optional[NumericSummary] = Field(None)
    provenance_coverage: ProvenanceCoverage = Field(...)
    co_occurrences: Tuple[CoOccurrence, ...] = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_dimension_profile(self)


def validate_dimension_profile(profile: DimensionProfile) -> None:
    """All semantic rules for a DimensionProfile."""
    for name in ("schema_version", "dimension_id", "source_field_path"):
        if not getattr(profile, name):
            raise ContractValidationError("%s must be non-empty" % name)
    for name in ("entity_count", "coverage_count", "missing_count",
                 "distinct_count"):
        if getattr(profile, name) < 0:
            raise ContractValidationError("%s must be >= 0" % name)
    if profile.coverage_count + profile.missing_count != profile.entity_count:
        raise ContractValidationError(
            "coverage_count + missing_count must equal entity_count (§7.4)"
        )
    if profile.distinct_count > profile.coverage_count:
        raise ContractValidationError(
            "distinct_count cannot exceed coverage_count"
        )

    ordering = [
        (-entry.entity_count, entry.value_label)
        for entry in profile.frequencies
    ]
    if ordering != sorted(ordering):
        raise ContractValidationError(
            "frequencies must be ordered by count descending, then "
            "value_label ascending (§7.4 deterministic ordering)"
        )
    labels = [entry.value_label for entry in profile.frequencies]
    if len(labels) != len(set(labels)):
        raise ContractValidationError("frequency value_labels must be unique")
    total = 0
    for entry in profile.frequencies:
        if entry.entity_count < 1:
            raise ContractValidationError(
                "frequency entries require entity_count >= 1"
            )
        total += entry.entity_count
    if total > profile.coverage_count:
        raise ContractValidationError(
            "frequency counts cannot exceed coverage_count"
        )

    if profile.numeric_summary is not None:
        if profile.kind is not DimensionKind.NUMERIC:
            raise ContractValidationError(
                "numeric_summary is only legal on NUMERIC dimensions (§7.4)"
            )
        summary = profile.numeric_summary
        if summary.scale_denominator < 1:
            raise ContractValidationError("scale_denominator must be >= 1")
        if summary.minimum_scaled > summary.maximum_scaled:
            raise ContractValidationError(
                "minimum_scaled cannot exceed maximum_scaled"
            )

    coverage = profile.provenance_coverage
    provenance_total = (
        coverage.verified_count + coverage.estimated_count
        + coverage.derived_count + coverage.operator_count
        + coverage.unknown_count
    )
    for name in ("verified_count", "estimated_count", "derived_count",
                 "operator_count", "unknown_count"):
        if getattr(coverage, name) < 0:
            raise ContractValidationError("%s must be >= 0" % name)
    if provenance_total != profile.coverage_count:
        raise ContractValidationError(
            "provenance coverage counts must partition coverage_count "
            "exactly (§7.4)"
        )

    other_ids = [entry.other_dimension_id for entry in profile.co_occurrences]
    if other_ids != sorted(other_ids):
        raise ContractValidationError(
            "co_occurrences must be sorted by other_dimension_id (§4.3)"
        )
    if len(other_ids) != len(set(other_ids)):
        raise ContractValidationError("co_occurrences must be unique")
    for entry in profile.co_occurrences:
        if entry.other_dimension_id == profile.dimension_id:
            raise ContractValidationError(
                "a dimension cannot co-occur with itself"
            )
        if not (0 <= entry.co_present_count <= profile.entity_count):
            raise ContractValidationError(
                "co_present_count must be within [0, entity_count]"
            )


class DimensionProfileSet(FrozenModel):
    """The profiler's run-level output: every discovered dimension (§7.4).

    ``inventory_ref`` is the content reference of the inventory snapshot the
    profiles were computed from; ``set_id`` is content-derived (§4.2).
    """

    schema_version: StrictStr = Field(...)
    set_id: StrictStr = Field(...)
    inventory_ref: StrictStr = Field(...)
    profiles: Tuple[DimensionProfile, ...] = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_dimension_profile_set(self)

    @classmethod
    def build(cls, **fields: Any) -> "DimensionProfileSet":
        """Construct with sorted profiles and a computed ``set_id``."""
        fields.pop("set_id", None)
        fields["profiles"] = tuple(
            sorted(fields.get("profiles", ()),
                   key=lambda item: item.dimension_id)
        )
        candidate = dict(fields)
        candidate["set_id"] = compute_profile_set_id(fields)
        return cls(**candidate)


def compute_profile_set_id(fields: Dict[str, Any]) -> str:
    """SHA-256 of the canonical form of every field except the id itself."""
    payload = dict(fields)
    payload.pop("set_id", None)
    return sha256_of_text(canonical_json(payload))


def validate_dimension_profile_set(profile_set: DimensionProfileSet) -> None:
    """All semantic rules for a DimensionProfileSet."""
    for name in ("schema_version", "inventory_ref"):
        if not getattr(profile_set, name):
            raise ContractValidationError("%s must be non-empty" % name)
    ids = [profile.dimension_id for profile in profile_set.profiles]
    if ids != sorted(ids):
        raise ContractValidationError(
            "profiles must be sorted by dimension_id (§4.3)"
        )
    if len(ids) != len(set(ids)):
        raise ContractValidationError("profiles must have unique dimension_ids")
    expected = compute_profile_set_id(
        {name: getattr(profile_set, name) for name in profile_set.__fields__}
    )
    if profile_set.set_id != expected:
        raise ContractValidationError(
            "set_id does not match content hash — identity is "
            "content-derived (§4.2); use DimensionProfileSet.build()"
        )
