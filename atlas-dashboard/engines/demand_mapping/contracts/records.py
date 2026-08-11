"""Generic inventory record contracts (AES-SEO-001 §7.2, Phase B).

The neutral entity-record form every project adapter targets: an entity is
an opaque id plus an opaque kind label plus a tuple of single-valued,
kind-declared, provenance-tagged field values. The engine treats every
identifier as opaque — semantic kinds are DECLARED by the service adapter,
never inferred from names (§5 of the Phase-B authority scope; §7.1).

Missingness doctrine (deterministic, tested):
* an absent field simply does not appear in ``fields`` — that is the one
  and only representation of "missing";
* a present value with ``UNKNOWN`` provenance is a value whose origin is
  unknown — it still counts as coverage, never as absence;
* zero and ``False`` are ordinary present values;
* empty text is not a legal value — adapters MUST omit empty source values
  (they are missing), so the engine never has to guess.

Multi-valued source fields are normalized by adapters (§7.1) — typically
into deterministic boolean membership fields — before reaching this form;
each record carries at most one value per field path.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pydantic import Field, StrictBool, StrictInt, StrictStr

from engines.demand_mapping.contracts.canonical import (
    ContractValidationError,
    FrozenModel,
    canonical_json,
    sha256_of_text,
)
from engines.demand_mapping.contracts.dimensions import DimensionKind
from engines.demand_mapping.contracts.provenance import Provenance

_TEXT_KINDS = (
    DimensionKind.CATEGORICAL,
    DimensionKind.GEOGRAPHIC,
    DimensionKind.ENTITY_REF,
    DimensionKind.TEXT,
)


class FieldValue(FrozenModel):
    """One single-valued, kind-declared field of one entity.

    Exactly one payload slot is populated, determined by ``kind``:
    NUMERIC → ``value_int`` + ``scale_denominator``; BOOLEAN →
    ``value_bool``; all text-carrying kinds → non-empty ``value_text``.
    """

    field_path: StrictStr = Field(...)
    kind: DimensionKind = Field(...)
    value_text: Optional[StrictStr] = Field(None)
    value_int: Optional[StrictInt] = Field(None)
    value_bool: Optional[StrictBool] = Field(None)
    scale_denominator: Optional[StrictInt] = Field(None)
    provenance: Provenance = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_field_value(self)


def validate_field_value(value: FieldValue) -> None:
    """Kind ↔ payload-slot rules for a FieldValue."""
    if not value.field_path:
        raise ContractValidationError("field_path must be non-empty")
    populated_text = value.value_text is not None
    populated_int = value.value_int is not None
    populated_bool = value.value_bool is not None

    if value.kind is DimensionKind.NUMERIC:
        if not populated_int or populated_text or populated_bool:
            raise ContractValidationError(
                "NUMERIC fields carry value_int only (%s)" % value.field_path
            )
        if value.scale_denominator is None or value.scale_denominator < 1:
            raise ContractValidationError(
                "NUMERIC fields require scale_denominator >= 1 (%s)"
                % value.field_path
            )
        return
    if value.scale_denominator is not None:
        raise ContractValidationError(
            "scale_denominator is only legal on NUMERIC fields (%s)"
            % value.field_path
        )
    if value.kind is DimensionKind.BOOLEAN:
        if not populated_bool or populated_text or populated_int:
            raise ContractValidationError(
                "BOOLEAN fields carry value_bool only (%s)" % value.field_path
            )
        return
    if value.kind in _TEXT_KINDS:
        if not populated_text or populated_int or populated_bool:
            raise ContractValidationError(
                "%s fields carry value_text only (%s)"
                % (value.kind.value, value.field_path)
            )
        if value.value_text == "":
            raise ContractValidationError(
                "empty text is not a value — adapters omit empty source "
                "values as missing (%s)" % value.field_path
            )
        return
    raise ContractValidationError(
        "unsupported kind %r on %s" % (value.kind, value.field_path)
    )


class GenericEntityRecord(FrozenModel):
    """One inventory entity in generic form (§7.2)."""

    entity_id: StrictStr = Field(...)
    entity_kind: StrictStr = Field(...)
    fields: Tuple[FieldValue, ...] = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_entity_record(self)


def validate_entity_record(record: GenericEntityRecord) -> None:
    """Structural rules for a GenericEntityRecord."""
    if not record.entity_id:
        raise ContractValidationError("entity_id must be non-empty")
    if not record.entity_kind:
        raise ContractValidationError("entity_kind must be non-empty")
    paths = [value.field_path for value in record.fields]
    if paths != sorted(paths):
        raise ContractValidationError(
            "fields must be sorted by field_path (§4.3)"
        )
    if len(paths) != len(set(paths)):
        raise ContractValidationError(
            "fields must be single-valued per field_path — multi-valued "
            "source data is normalized by the adapter (§7.1)"
        )


class GenericInventorySnapshot(FrozenModel):
    """An immutable, content-addressed inventory input (§4.6, §7.2).

    ``snapshot_id`` is the SHA-256 of the canonical form of the snapshot's
    own fields and serves as ``DimensionProfileSet.inventory_ref``.
    """

    schema_version: StrictStr = Field(...)
    snapshot_id: StrictStr = Field(...)
    records: Tuple[GenericEntityRecord, ...] = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_inventory_snapshot(self)

    @classmethod
    def build(cls, **fields: Any) -> "GenericInventorySnapshot":
        """Construct with sorted records and a computed ``snapshot_id``."""
        fields.pop("snapshot_id", None)
        fields["records"] = tuple(
            sorted(fields.get("records", ()),
                   key=lambda item: item.entity_id)
        )
        candidate = dict(fields)
        candidate["snapshot_id"] = compute_inventory_snapshot_id(fields)
        return cls(**candidate)


def compute_inventory_snapshot_id(fields: Dict[str, Any]) -> str:
    """SHA-256 of the canonical form of every field except the id itself."""
    payload = dict(fields)
    payload.pop("snapshot_id", None)
    return sha256_of_text(canonical_json(payload))


def validate_inventory_snapshot(snapshot: GenericInventorySnapshot) -> None:
    """Structural rules for a GenericInventorySnapshot."""
    if not snapshot.schema_version:
        raise ContractValidationError("schema_version must be non-empty")
    ids = [record.entity_id for record in snapshot.records]
    if ids != sorted(ids):
        raise ContractValidationError(
            "records must be sorted by entity_id (§4.3)"
        )
    if len(ids) != len(set(ids)):
        raise ContractValidationError("records must have unique entity_ids")
    expected = compute_inventory_snapshot_id(
        {name: getattr(snapshot, name) for name in snapshot.__fields__}
    )
    if snapshot.snapshot_id != expected:
        raise ContractValidationError(
            "snapshot_id does not match content hash (§4.2); use "
            "GenericInventorySnapshot.build()"
        )
