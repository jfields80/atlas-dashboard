"""InventoryProfiler behavior tests (AES-SEO-001 §7.4, Phase B)."""

from __future__ import annotations

import pytest

from engines.demand_mapping.contracts.canonical import canonical_contract_json
from engines.demand_mapping.contracts.dimensions import DimensionKind
from engines.demand_mapping.contracts.provenance import Provenance
from engines.demand_mapping.contracts.records import (
    FieldValue,
    GenericEntityRecord,
    GenericInventorySnapshot,
)
from engines.demand_mapping.profiling import InventoryProfiler, ProfilingError


def fv_text(path, text, kind=DimensionKind.CATEGORICAL,
            provenance=Provenance.UNKNOWN):
    return FieldValue(field_path=path, kind=kind, value_text=text,
                      provenance=provenance)


def fv_num(path, value, scale=1, provenance=Provenance.UNKNOWN):
    return FieldValue(field_path=path, kind=DimensionKind.NUMERIC,
                      value_int=value, scale_denominator=scale,
                      provenance=provenance)


def fv_bool(path, value, provenance=Provenance.UNKNOWN):
    return FieldValue(field_path=path, kind=DimensionKind.BOOLEAN,
                      value_bool=value, provenance=provenance)


def record(entity_id, *fields, kind="thing"):
    return GenericEntityRecord(
        entity_id=entity_id, entity_kind=kind,
        fields=tuple(sorted(fields, key=lambda f: f.field_path)),
    )


def snapshot(*records_):
    return GenericInventorySnapshot.build(
        schema_version="1.0.0", records=tuple(records_),
    )


def profile_map(snap):
    result = InventoryProfiler().profile(snap)
    return {p.dimension_id: p for p in result.profiles}, result


class TestCategoricalStats:
    def test_counts_and_frequency_ordering(self):
        snap = snapshot(
            record("e1", fv_text("attr.color", "blue")),
            record("e2", fv_text("attr.color", "blue")),
            record("e3", fv_text("attr.color", "red")),
            record("e4"),
        )
        profiles, _ = profile_map(snap)
        p = profiles["thing:attr.color"]
        assert (p.entity_count, p.coverage_count, p.missing_count,
                p.distinct_count) == (4, 3, 1, 2)
        assert [(f.value_label, f.entity_count) for f in p.frequencies] == [
            ("blue", 2), ("red", 1)
        ]

    def test_frequency_tie_breaks_by_label(self):
        snap = snapshot(
            record("e1", fv_text("attr.color", "red")),
            record("e2", fv_text("attr.color", "blue")),
        )
        profiles, _ = profile_map(snap)
        labels = [f.value_label
                  for f in profiles["thing:attr.color"].frequencies]
        assert labels == ["blue", "red"]


class TestNumericStats:
    def test_range_and_scale(self):
        snap = snapshot(
            record("e1", fv_num("attr.price", 2500, scale=100)),
            record("e2", fv_num("attr.price", 15000, scale=100)),
        )
        profiles, _ = profile_map(snap)
        p = profiles["thing:attr.price"]
        summary = p.numeric_summary
        assert (summary.minimum_scaled, summary.maximum_scaled,
                summary.scale_denominator) == (2500, 15000, 100)
        assert p.frequencies == ()

    def test_zero_is_covered_not_missing(self):
        snap = snapshot(
            record("e1", fv_num("attr.price", 0)),
            record("e2"),
        )
        profiles, _ = profile_map(snap)
        p = profiles["thing:attr.price"]
        assert (p.coverage_count, p.missing_count) == (1, 1)
        assert p.numeric_summary.minimum_scaled == 0

    def test_conflicting_scales_fail_closed(self):
        snap = snapshot(
            record("e1", fv_num("attr.price", 100, scale=1)),
            record("e2", fv_num("attr.price", 100, scale=100)),
        )
        with pytest.raises(ProfilingError):
            InventoryProfiler().profile(snap)


class TestBooleanStats:
    def test_false_is_covered_not_missing(self):
        snap = snapshot(
            record("e1", fv_bool("attr.flag", True)),
            record("e2", fv_bool("attr.flag", False)),
            record("e3"),
        )
        profiles, _ = profile_map(snap)
        p = profiles["thing:attr.flag"]
        assert (p.coverage_count, p.missing_count, p.distinct_count) == (2, 1, 2)
        assert [(f.value_label, f.entity_count) for f in p.frequencies] == [
            ("false", 1), ("true", 1)
        ]


class TestGeographicAndText:
    def test_geographic_frequencies(self):
        snap = snapshot(
            record("e1", fv_text("loc.area", "north",
                                 kind=DimensionKind.GEOGRAPHIC)),
            record("e2", fv_text("loc.area", "north",
                                 kind=DimensionKind.GEOGRAPHIC)),
        )
        profiles, _ = profile_map(snap)
        p = profiles["thing:loc.area"]
        assert p.kind is DimensionKind.GEOGRAPHIC
        assert p.frequencies[0].entity_count == 2

    def test_text_has_distinct_but_no_frequencies(self):
        snap = snapshot(
            record("e1", fv_text("attr.blurb", "alpha prose",
                                 kind=DimensionKind.TEXT)),
            record("e2", fv_text("attr.blurb", "beta prose",
                                 kind=DimensionKind.TEXT)),
        )
        profiles, _ = profile_map(snap)
        p = profiles["thing:attr.blurb"]
        assert p.distinct_count == 2
        assert p.frequencies == ()


class TestProvenancePartition:
    def test_counts_partition_coverage(self):
        snap = snapshot(
            record("e1", fv_text("attr.color", "blue",
                                 provenance=Provenance.VERIFIED)),
            record("e2", fv_text("attr.color", "blue",
                                 provenance=Provenance.OPERATOR)),
            record("e3", fv_text("attr.color", "red",
                                 provenance=Provenance.ESTIMATED)),
            record("e4", fv_text("attr.color", "red",
                                 provenance=Provenance.DERIVED)),
            record("e5", fv_text("attr.color", "red")),
            record("e6"),
        )
        profiles, _ = profile_map(snap)
        coverage = profiles["thing:attr.color"].provenance_coverage
        assert (coverage.verified_count, coverage.operator_count,
                coverage.estimated_count, coverage.derived_count,
                coverage.unknown_count) == (1, 1, 1, 1, 1)

    def test_unknown_provenance_is_still_coverage(self):
        snap = snapshot(record("e1", fv_text("attr.color", "blue")))
        profiles, _ = profile_map(snap)
        p = profiles["thing:attr.color"]
        assert p.coverage_count == 1
        assert p.provenance_coverage.unknown_count == 1


class TestCoOccurrence:
    def test_shared_carriers_counted(self):
        snap = snapshot(
            record("e1", fv_text("attr.a", "x"), fv_text("attr.b", "y")),
            record("e2", fv_text("attr.a", "x")),
        )
        profiles, _ = profile_map(snap)
        a = profiles["thing:attr.a"]
        assert [(c.other_dimension_id, c.co_present_count)
                for c in a.co_occurrences] == [("thing:attr.b", 1)]
        b = profiles["thing:attr.b"]
        assert [(c.other_dimension_id, c.co_present_count)
                for c in b.co_occurrences] == [("thing:attr.a", 1)]

    def test_disjoint_dimensions_have_no_edge(self):
        snap = snapshot(
            record("e1", fv_text("attr.a", "x")),
            record("e2", fv_text("attr.b", "y")),
        )
        profiles, _ = profile_map(snap)
        assert profiles["thing:attr.a"].co_occurrences == ()


class TestEntityKindScoping:
    def test_dimensions_scoped_per_kind(self):
        snap = snapshot(
            record("e1", fv_text("attr.color", "blue"), kind="alpha"),
            record("e2", kind="beta"),
        )
        profiles, _ = profile_map(snap)
        p = profiles["alpha:attr.color"]
        assert (p.entity_count, p.coverage_count, p.missing_count) == (1, 1, 0)
        assert "beta:attr.color" not in profiles

    def test_conflicting_kind_declarations_fail_closed(self):
        snap = snapshot(
            record("e1", fv_text("attr.mixed", "x")),
            record("e2", fv_bool("attr.mixed", True)),
        )
        with pytest.raises(ProfilingError):
            InventoryProfiler().profile(snap)


class TestDeterminism:
    def build(self, order):
        records = [
            record("e1", fv_text("attr.color", "blue"),
                   fv_num("attr.price", 100)),
            record("e2", fv_text("attr.color", "red")),
            record("e3", fv_bool("attr.flag", False)),
        ]
        ordered = [records[i] for i in order]
        return InventoryProfiler().profile(snapshot(*ordered))

    def test_record_input_order_is_irrelevant(self):
        first = self.build([0, 1, 2])
        second = self.build([2, 0, 1])
        assert first.set_id == second.set_id
        assert (canonical_contract_json(first)
                == canonical_contract_json(second))

    def test_repeated_runs_byte_identical(self):
        assert (canonical_contract_json(self.build([0, 1, 2]))
                == canonical_contract_json(self.build([0, 1, 2])))

    def test_inventory_ref_binds_snapshot(self):
        snap = snapshot(record("e1", fv_text("attr.color", "blue")))
        result = InventoryProfiler().profile(snap)
        assert result.inventory_ref == snap.snapshot_id


class TestEmptySnapshot:
    def test_empty_snapshot_yields_empty_profile_set(self):
        result = InventoryProfiler().profile(snapshot())
        assert result.profiles == ()
