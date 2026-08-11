"""Generic inventory record contract tests (AES-SEO-001 §7.2, Phase B)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engines.demand_mapping.contracts.canonical import (
    ContractValidationError,
    canonical_contract_json,
    contract_sha256,
)
from engines.demand_mapping.contracts.dimensions import DimensionKind
from engines.demand_mapping.contracts.provenance import Provenance
from engines.demand_mapping.contracts.records import (
    FieldValue,
    GenericEntityRecord,
    GenericInventorySnapshot,
)


def text_value(path="attr.color", kind=DimensionKind.CATEGORICAL,
               text="blue", provenance=Provenance.UNKNOWN):
    return FieldValue(
        field_path=path, kind=kind, value_text=text, provenance=provenance
    )


def numeric_value(path="attr.size", value=100, scale=1,
                  provenance=Provenance.UNKNOWN):
    return FieldValue(
        field_path=path, kind=DimensionKind.NUMERIC, value_int=value,
        scale_denominator=scale, provenance=provenance,
    )


def bool_value(path="attr.flag", value=True,
               provenance=Provenance.UNKNOWN):
    return FieldValue(
        field_path=path, kind=DimensionKind.BOOLEAN, value_bool=value,
        provenance=provenance,
    )


class TestFieldValueKinds:
    def test_valid_shapes(self):
        assert text_value().value_text == "blue"
        assert numeric_value().scale_denominator == 1
        assert bool_value(value=False).value_bool is False

    def test_numeric_requires_int_and_scale(self):
        with pytest.raises(ContractValidationError):
            FieldValue(field_path="a", kind=DimensionKind.NUMERIC,
                       value_text="5", provenance=Provenance.UNKNOWN)
        with pytest.raises(ContractValidationError):
            FieldValue(field_path="a", kind=DimensionKind.NUMERIC,
                       value_int=5, provenance=Provenance.UNKNOWN)
        with pytest.raises(ContractValidationError):
            FieldValue(field_path="a", kind=DimensionKind.NUMERIC,
                       value_int=5, scale_denominator=0,
                       provenance=Provenance.UNKNOWN)

    def test_scale_forbidden_off_numeric(self):
        with pytest.raises(ContractValidationError):
            FieldValue(field_path="a", kind=DimensionKind.BOOLEAN,
                       value_bool=True, scale_denominator=1,
                       provenance=Provenance.UNKNOWN)

    def test_boolean_requires_bool_only(self):
        with pytest.raises(ContractValidationError):
            FieldValue(field_path="a", kind=DimensionKind.BOOLEAN,
                       value_text="true", provenance=Provenance.UNKNOWN)

    def test_text_kinds_require_non_empty_text(self):
        for kind in (DimensionKind.CATEGORICAL, DimensionKind.GEOGRAPHIC,
                     DimensionKind.ENTITY_REF, DimensionKind.TEXT):
            with pytest.raises(ContractValidationError):
                FieldValue(field_path="a", kind=kind, value_text="",
                           provenance=Provenance.UNKNOWN)
            with pytest.raises(ContractValidationError):
                FieldValue(field_path="a", kind=kind, value_int=1,
                           provenance=Provenance.UNKNOWN)

    def test_float_rejected_by_strict_typing(self):
        with pytest.raises(ValidationError):
            numeric_value(value=5.5)
        with pytest.raises(ValidationError):
            numeric_value(scale=10.0)

    def test_zero_and_false_are_present_values(self):
        assert numeric_value(value=0).value_int == 0
        assert bool_value(value=False).value_bool is False


class TestEntityRecord:
    def test_fields_sorted_and_single_valued(self):
        with pytest.raises(ContractValidationError):
            GenericEntityRecord(
                entity_id="e1", entity_kind="thing",
                fields=(text_value(path="b.x"), text_value(path="a.x")),
            )
        with pytest.raises(ContractValidationError):
            GenericEntityRecord(
                entity_id="e1", entity_kind="thing",
                fields=(text_value(path="a.x"),
                        text_value(path="a.x", text="red")),
            )

    def test_non_empty_identity(self):
        with pytest.raises(ContractValidationError):
            GenericEntityRecord(entity_id="", entity_kind="thing", fields=())
        with pytest.raises(ContractValidationError):
            GenericEntityRecord(entity_id="e1", entity_kind="", fields=())


class TestInventorySnapshot:
    def make_record(self, entity_id):
        return GenericEntityRecord(
            entity_id=entity_id, entity_kind="thing",
            fields=(text_value(),),
        )

    def test_build_sorts_and_hashes(self):
        snapshot = GenericInventorySnapshot.build(
            schema_version="1.0.0",
            records=(self.make_record("b"), self.make_record("a")),
        )
        assert [r.entity_id for r in snapshot.records] == ["a", "b"]
        assert len(snapshot.snapshot_id) == 64

    def test_input_order_does_not_change_identity(self):
        one = GenericInventorySnapshot.build(
            schema_version="1.0.0",
            records=(self.make_record("a"), self.make_record("b")),
        )
        two = GenericInventorySnapshot.build(
            schema_version="1.0.0",
            records=(self.make_record("b"), self.make_record("a")),
        )
        assert one.snapshot_id == two.snapshot_id
        assert canonical_contract_json(one) == canonical_contract_json(two)
        assert contract_sha256(one) == contract_sha256(two)

    def test_duplicate_entity_ids_rejected(self):
        with pytest.raises(ContractValidationError):
            GenericInventorySnapshot.build(
                schema_version="1.0.0",
                records=(self.make_record("a"), self.make_record("a")),
            )

    def test_tampered_snapshot_id_rejected(self):
        snapshot = GenericInventorySnapshot.build(
            schema_version="1.0.0", records=(),
        )
        with pytest.raises(ContractValidationError):
            GenericInventorySnapshot(
                schema_version=snapshot.schema_version,
                snapshot_id="0" * 64,
                records=snapshot.records,
            )
