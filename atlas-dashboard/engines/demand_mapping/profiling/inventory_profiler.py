"""InventoryProfiler — generic records in, DimensionProfileSet out.

AES-SEO-001 §7.4/§7.5: the profiler reasons ONLY from normalized record
structure and the kinds DECLARED by the adapter. It never inspects field
names for meaning; every identifier is opaque.

Dimension identity: one dimension per ``(entity_kind, field_path)`` pair,
``dimension_id = entity_kind + ":" + field_path``, and every count is
scoped to the entities of that kind — coverage of a field is measured
against the population that could plausibly carry it, not against the
whole snapshot.

Determinism (§4): output depends only on snapshot content. All iteration
runs over sorted views; identical snapshots produce byte-identical
``DimensionProfileSet`` canonical JSON and equal set hashes regardless of
the order records or fields were supplied to the snapshot builder (the
snapshot itself already sorts, and this engine re-sorts defensively).

Missingness (§ Phase-B 6): a field absent from a record is the only form
of "missing". Zero, ``False``, and UNKNOWN-provenance values are present
values and count as coverage.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from engines.demand_mapping.contracts.canonical import (
    DemandMappingContractError,
)
from engines.demand_mapping.contracts.dimensions import (
    CoOccurrence,
    DimensionKind,
    DimensionProfile,
    DimensionProfileSet,
    FrequencyEntry,
    NumericSummary,
    ProvenanceCoverage,
)
from engines.demand_mapping.contracts.provenance import Provenance
from engines.demand_mapping.contracts.records import (
    FieldValue,
    GenericEntityRecord,
    GenericInventorySnapshot,
)
from engines.demand_mapping.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)

_LABEL_KINDS = (
    DimensionKind.CATEGORICAL,
    DimensionKind.GEOGRAPHIC,
    DimensionKind.ENTITY_REF,
    DimensionKind.BOOLEAN,
)

_BOOL_LABELS = {True: "true", False: "false"}


class ProfilingError(DemandMappingContractError):
    """The snapshot is internally inconsistent for profiling purposes."""


def _value_label(value: FieldValue) -> str:
    if value.kind is DimensionKind.BOOLEAN:
        return _BOOL_LABELS[bool(value.value_bool)]
    return str(value.value_text)


def _distinct_key(value: FieldValue) -> str:
    if value.kind is DimensionKind.NUMERIC:
        return str(value.value_int)
    return _value_label(value)


class InventoryProfiler:
    """Deterministic profiler (engine verb: ``profile``)."""

    version = ENGINE_VERSIONS["inventory_profiler"]

    def profile(
        self, snapshot: GenericInventorySnapshot
    ) -> DimensionProfileSet:
        """Profile every ``(entity_kind, field_path)`` dimension."""
        by_kind: Dict[str, List[GenericEntityRecord]] = {}
        for record in snapshot.records:
            by_kind.setdefault(record.entity_kind, []).append(record)

        profiles: List[DimensionProfile] = []
        for entity_kind in sorted(by_kind):
            records = by_kind[entity_kind]
            profiles.extend(self._profile_entity_kind(entity_kind, records))

        return DimensionProfileSet.build(
            schema_version=SCHEMA_VERSIONS["DimensionProfileSet"],
            inventory_ref=snapshot.snapshot_id,
            profiles=tuple(profiles),
        )

    def _profile_entity_kind(
        self, entity_kind: str, records: List[GenericEntityRecord]
    ) -> List[DimensionProfile]:
        entity_count = len(records)
        values_by_path: Dict[str, List[FieldValue]] = {}
        carriers_by_path: Dict[str, set] = {}
        for record in records:
            for value in record.fields:
                values_by_path.setdefault(value.field_path, []).append(value)
                carriers_by_path.setdefault(value.field_path, set()).add(
                    record.entity_id
                )

        profiles: List[DimensionProfile] = []
        for field_path in sorted(values_by_path):
            values = values_by_path[field_path]
            profiles.append(
                self._profile_dimension(
                    entity_kind,
                    field_path,
                    values,
                    entity_count,
                    carriers_by_path,
                )
            )
        return profiles

    def _profile_dimension(
        self,
        entity_kind: str,
        field_path: str,
        values: List[FieldValue],
        entity_count: int,
        carriers_by_path: Dict[str, set],
    ) -> DimensionProfile:
        dimension_id = "%s:%s" % (entity_kind, field_path)

        kinds = {value.kind for value in values}
        if len(kinds) != 1:
            raise ProfilingError(
                "conflicting declared kinds for %s: %s"
                % (dimension_id, sorted(kind.value for kind in kinds))
            )
        kind = values[0].kind

        coverage_count = len(values)
        missing_count = entity_count - coverage_count
        distinct_count = len({_distinct_key(value) for value in values})

        frequencies: Tuple[FrequencyEntry, ...] = ()
        if kind in _LABEL_KINDS:
            counts: Dict[str, int] = {}
            for value in values:
                label = _value_label(value)
                counts[label] = counts.get(label, 0) + 1
            frequencies = tuple(
                FrequencyEntry(value_label=label, entity_count=count)
                for count, label in sorted(
                    ((count, label) for label, count in counts.items()),
                    key=lambda item: (-item[0], item[1]),
                )
            )

        numeric_summary = None
        if kind is DimensionKind.NUMERIC:
            scales = {value.scale_denominator for value in values}
            if len(scales) != 1:
                raise ProfilingError(
                    "conflicting scale_denominator for %s: %s"
                    % (dimension_id, sorted(scales))
                )
            ints = [value.value_int for value in values]
            numeric_summary = NumericSummary(
                minimum_scaled=min(ints),
                maximum_scaled=max(ints),
                scale_denominator=values[0].scale_denominator,
            )

        tallies = {state: 0 for state in Provenance}
        for value in values:
            tallies[value.provenance] += 1
        provenance_coverage = ProvenanceCoverage(
            verified_count=tallies[Provenance.VERIFIED],
            estimated_count=tallies[Provenance.ESTIMATED],
            derived_count=tallies[Provenance.DERIVED],
            operator_count=tallies[Provenance.OPERATOR],
            unknown_count=tallies[Provenance.UNKNOWN],
        )

        own_carriers = carriers_by_path[field_path]
        co_occurrences = []
        for other_path in sorted(carriers_by_path):
            if other_path == field_path:
                continue
            shared = len(own_carriers & carriers_by_path[other_path])
            if shared >= 1:
                co_occurrences.append(
                    CoOccurrence(
                        other_dimension_id="%s:%s" % (entity_kind, other_path),
                        co_present_count=shared,
                    )
                )

        return DimensionProfile(
            schema_version=SCHEMA_VERSIONS["DimensionProfile"],
            dimension_id=dimension_id,
            source_field_path=field_path,
            kind=kind,
            entity_count=entity_count,
            coverage_count=coverage_count,
            missing_count=missing_count,
            distinct_count=distinct_count,
            frequencies=frequencies,
            numeric_summary=numeric_summary,
            provenance_coverage=provenance_coverage,
            co_occurrences=tuple(co_occurrences),
        )
