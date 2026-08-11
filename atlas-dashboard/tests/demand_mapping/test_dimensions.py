"""Dimension profile tests (AES-SEO-001 §7)."""

from __future__ import annotations

import pytest

from engines.demand_mapping.contracts.canonical import ContractValidationError
from engines.demand_mapping.contracts.dimensions import (
    CoOccurrence,
    DimensionKind,
    DimensionProfile,
    DimensionProfileSet,
    FrequencyEntry,
    NumericSummary,
    ProvenanceCoverage,
)


def coverage(covered: int, unknown: int = 0):
    return ProvenanceCoverage(
        verified_count=covered - unknown,
        estimated_count=0,
        derived_count=0,
        operator_count=0,
        unknown_count=unknown,
    )


def profile_fields(**overrides):
    fields = dict(
        schema_version="1.0.0",
        dimension_id="dim.alpha",
        source_field_path="records.alpha",
        kind=DimensionKind.CATEGORICAL,
        entity_count=10,
        coverage_count=8,
        missing_count=2,
        distinct_count=3,
        frequencies=(
            FrequencyEntry(value_label="a", entity_count=5),
            FrequencyEntry(value_label="b", entity_count=2),
            FrequencyEntry(value_label="c", entity_count=1),
        ),
        numeric_summary=None,
        provenance_coverage=coverage(8),
        co_occurrences=(),
    )
    fields.update(overrides)
    return fields


def make_profile(**overrides):
    return DimensionProfile(**profile_fields(**overrides))


class TestDimensionKind:
    def test_exactly_six_kinds(self):
        assert {member.value for member in DimensionKind} == {
            "CATEGORICAL", "NUMERIC", "BOOLEAN", "GEOGRAPHIC",
            "ENTITY_REF", "TEXT",
        }


class TestProfileArithmetic:
    def test_valid_profile(self):
        assert make_profile().distinct_count == 3

    def test_coverage_plus_missing_must_equal_entity_count(self):
        with pytest.raises(ContractValidationError):
            make_profile(missing_count=3)

    def test_negative_counts_rejected(self):
        with pytest.raises(ContractValidationError):
            make_profile(entity_count=-1, coverage_count=-3, missing_count=2)

    def test_distinct_cannot_exceed_coverage(self):
        with pytest.raises(ContractValidationError):
            make_profile(
                distinct_count=9,
                frequencies=(),
            )

    def test_frequency_ordering_enforced(self):
        with pytest.raises(ContractValidationError):
            make_profile(frequencies=(
                FrequencyEntry(value_label="b", entity_count=2),
                FrequencyEntry(value_label="a", entity_count=5),
            ))

    def test_frequency_counts_cannot_exceed_coverage(self):
        with pytest.raises(ContractValidationError):
            make_profile(frequencies=(
                FrequencyEntry(value_label="a", entity_count=9),
            ))

    def test_provenance_partition_must_be_exact(self):
        with pytest.raises(ContractValidationError):
            make_profile(provenance_coverage=coverage(7))

    def test_provenance_unknown_bucket_counts(self):
        profile = make_profile(provenance_coverage=coverage(8, unknown=3))
        assert profile.provenance_coverage.unknown_count == 3


class TestNumericSummary:
    def test_summary_only_on_numeric(self):
        with pytest.raises(ContractValidationError):
            make_profile(numeric_summary=NumericSummary(
                minimum_scaled=0, maximum_scaled=10, scale_denominator=1,
            ))

    def test_numeric_with_summary_is_legal(self):
        profile = make_profile(
            kind=DimensionKind.NUMERIC,
            frequencies=(),
            distinct_count=4,
            numeric_summary=NumericSummary(
                minimum_scaled=2500, maximum_scaled=15000,
                scale_denominator=100,
            ),
        )
        assert profile.numeric_summary.scale_denominator == 100

    def test_scale_denominator_must_be_positive(self):
        with pytest.raises(ContractValidationError):
            make_profile(
                kind=DimensionKind.NUMERIC,
                frequencies=(),
                numeric_summary=NumericSummary(
                    minimum_scaled=0, maximum_scaled=1, scale_denominator=0,
                ),
            )

    def test_min_cannot_exceed_max(self):
        with pytest.raises(ContractValidationError):
            make_profile(
                kind=DimensionKind.NUMERIC,
                frequencies=(),
                numeric_summary=NumericSummary(
                    minimum_scaled=5, maximum_scaled=1, scale_denominator=1,
                ),
            )


class TestCoOccurrences:
    def test_self_co_occurrence_rejected(self):
        with pytest.raises(ContractValidationError):
            make_profile(co_occurrences=(
                CoOccurrence(other_dimension_id="dim.alpha",
                             co_present_count=1),
            ))

    def test_must_be_sorted(self):
        with pytest.raises(ContractValidationError):
            make_profile(co_occurrences=(
                CoOccurrence(other_dimension_id="dim.z", co_present_count=1),
                CoOccurrence(other_dimension_id="dim.b", co_present_count=1),
            ))

    def test_count_bounded_by_entity_count(self):
        with pytest.raises(ContractValidationError):
            make_profile(co_occurrences=(
                CoOccurrence(other_dimension_id="dim.b",
                             co_present_count=11),
            ))


class TestProfileSet:
    def test_build_sorts_and_hashes(self):
        alpha = make_profile()
        beta = make_profile(dimension_id="dim.beta",
                            source_field_path="records.beta")
        profile_set = DimensionProfileSet.build(
            schema_version="1.0.0",
            inventory_ref="inventory-snapshot-ref",
            profiles=(beta, alpha),
        )
        assert [p.dimension_id for p in profile_set.profiles] == [
            "dim.alpha", "dim.beta"
        ]
        assert len(profile_set.set_id) == 64

    def test_identical_content_identical_id(self):
        def build():
            return DimensionProfileSet.build(
                schema_version="1.0.0",
                inventory_ref="inventory-snapshot-ref",
                profiles=(make_profile(),),
            )

        assert build().set_id == build().set_id

    def test_duplicate_dimension_ids_rejected(self):
        with pytest.raises(ContractValidationError):
            DimensionProfileSet.build(
                schema_version="1.0.0",
                inventory_ref="inventory-snapshot-ref",
                profiles=(make_profile(), make_profile()),
            )

    def test_tampered_set_id_rejected(self):
        profile_set = DimensionProfileSet.build(
            schema_version="1.0.0",
            inventory_ref="inventory-snapshot-ref",
            profiles=(),
        )
        with pytest.raises(ContractValidationError):
            DimensionProfileSet(
                schema_version=profile_set.schema_version,
                set_id="0" * 64,
                inventory_ref=profile_set.inventory_ref,
                profiles=profile_set.profiles,
            )
