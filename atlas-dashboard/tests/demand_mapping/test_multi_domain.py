"""Multi-domain portability proof (AES-SEO-001 §22.4, Phase B §11).

The SAME generic engine, unchanged, profiles two synthetic domains that
share nothing with the first fixture's vocabulary: a martial-arts
directory and a farm / direct-food directory. Domain words appear here in
TEST DATA only — the engine never sees them as anything but opaque labels.
"""

from __future__ import annotations

from engines.demand_mapping.contracts.canonical import canonical_contract_json
from engines.demand_mapping.contracts.dimensions import DimensionKind
from engines.demand_mapping.contracts.provenance import Provenance
from engines.demand_mapping.contracts.records import (
    FieldValue,
    GenericEntityRecord,
    GenericInventorySnapshot,
)
from engines.demand_mapping.profiling import InventoryProfiler

PROFILER = InventoryProfiler()  # one shared instance across all domains


def fv(path, kind, *, text=None, number=None, scale=None, flag=None,
       provenance=Provenance.UNKNOWN):
    return FieldValue(
        field_path=path, kind=kind, value_text=text, value_int=number,
        scale_denominator=scale, value_bool=flag, provenance=provenance,
    )


def rec(entity_id, kind, *fields):
    return GenericEntityRecord(
        entity_id=entity_id, entity_kind=kind,
        fields=tuple(sorted(fields, key=lambda f: f.field_path)),
    )


def snap(*records):
    return GenericInventorySnapshot.build(
        schema_version="1.0.0", records=tuple(records),
    )


def build_martial_arts_snapshot():
    """Martial-arts directory: multi-value program membership normalized
    into boolean dimensions (the §8 adapter transformation shape)."""
    return snap(
        rec("iron dragon academy", "school",
            fv("program.discipline", DimensionKind.CATEGORICAL, text="bjj",
               provenance=Provenance.OPERATOR),
            fv("program.ages:adults", DimensionKind.BOOLEAN, flag=True,
               provenance=Provenance.OPERATOR),
            fv("program.ages:kids", DimensionKind.BOOLEAN, flag=True,
               provenance=Provenance.OPERATOR),
            fv("pricing.monthly", DimensionKind.NUMERIC, number=14900,
               scale=100, provenance=Provenance.ESTIMATED),
            fv("location.city", DimensionKind.GEOGRAPHIC, text="springfield")),
        rec("north side karate", "school",
            fv("program.discipline", DimensionKind.CATEGORICAL,
               text="karate", provenance=Provenance.OPERATOR),
            fv("program.ages:adults", DimensionKind.BOOLEAN, flag=False,
               provenance=Provenance.OPERATOR),
            fv("program.ages:kids", DimensionKind.BOOLEAN, flag=True,
               provenance=Provenance.OPERATOR),
            fv("location.city", DimensionKind.GEOGRAPHIC, text="riverton")),
        rec("summit judo club", "school",
            fv("program.discipline", DimensionKind.CATEGORICAL, text="judo",
               provenance=Provenance.OPERATOR),
            fv("location.city", DimensionKind.GEOGRAPHIC,
               text="springfield")),
    )


def build_farm_snapshot():
    """Farm / direct-food directory."""
    return snap(
        rec("green pasture ranch", "farm",
            fv("product.primary", DimensionKind.CATEGORICAL,
               text="grass-fed", provenance=Provenance.VERIFIED),
            fv("price.per_pound", DimensionKind.NUMERIC, number=1250,
               scale=100, provenance=Provenance.VERIFIED),
            fv("sales.ships_frozen", DimensionKind.BOOLEAN, flag=True,
               provenance=Provenance.DERIVED),
            fv("location.county", DimensionKind.GEOGRAPHIC, text="madison")),
        rec("hilltop homestead", "farm",
            fv("product.primary", DimensionKind.CATEGORICAL,
               text="pasture-raised", provenance=Provenance.VERIFIED),
            fv("sales.ships_frozen", DimensionKind.BOOLEAN, flag=False,
               provenance=Provenance.OPERATOR),
            fv("location.county", DimensionKind.GEOGRAPHIC, text="union"),
            fv("notes.description", DimensionKind.TEXT,
               text="small family operation")),
        rec("valley creek farm", "farm",
            fv("product.primary", DimensionKind.CATEGORICAL,
               text="grass-fed", provenance=Provenance.ESTIMATED),
            fv("location.county", DimensionKind.GEOGRAPHIC,
               text="madison")),
    )


class TestMartialArtsDomain:
    def test_full_profile(self):
        result = PROFILER.profile(build_martial_arts_snapshot())
        profiles = {p.dimension_id: p for p in result.profiles}

        discipline = profiles["school:program.discipline"]
        assert discipline.kind is DimensionKind.CATEGORICAL
        assert (discipline.coverage_count, discipline.distinct_count) == (3, 3)

        pricing = profiles["school:pricing.monthly"]
        assert (pricing.coverage_count, pricing.missing_count) == (1, 2)
        assert pricing.numeric_summary.scale_denominator == 100

        adults = profiles["school:program.ages:adults"]
        assert (adults.coverage_count, adults.missing_count) == (2, 1)
        assert {(f.value_label, f.entity_count)
                for f in adults.frequencies} == {("true", 1), ("false", 1)}

        city = profiles["school:location.city"]
        assert city.kind is DimensionKind.GEOGRAPHIC
        assert city.frequencies[0].value_label == "springfield"

        assert discipline.provenance_coverage.operator_count == 3


class TestFarmDomain:
    def test_full_profile(self):
        result = PROFILER.profile(build_farm_snapshot())
        profiles = {p.dimension_id: p for p in result.profiles}

        product = profiles["farm:product.primary"]
        assert [(f.value_label, f.entity_count)
                for f in product.frequencies] == [
            ("grass-fed", 2), ("pasture-raised", 1)
        ]
        coverage = product.provenance_coverage
        assert (coverage.verified_count, coverage.estimated_count) == (2, 1)

        ships = profiles["farm:sales.ships_frozen"]
        assert (ships.coverage_count, ships.missing_count) == (2, 1)
        assert ships.provenance_coverage.derived_count == 1
        assert ships.provenance_coverage.operator_count == 1

        price = profiles["farm:price.per_pound"]
        assert (price.numeric_summary.minimum_scaled,
                price.numeric_summary.maximum_scaled) == (1250, 1250)

        notes = profiles["farm:notes.description"]
        assert notes.kind is DimensionKind.TEXT
        assert notes.frequencies == ()


class TestPortability:
    def test_one_engine_instance_serves_unrelated_domains(self):
        martial = PROFILER.profile(build_martial_arts_snapshot())
        farm = PROFILER.profile(build_farm_snapshot())
        assert martial.set_id != farm.set_id
        # Deterministic across repeated runs, per domain.
        assert canonical_contract_json(martial) == canonical_contract_json(
            PROFILER.profile(build_martial_arts_snapshot())
        )
        assert canonical_contract_json(farm) == canonical_contract_json(
            PROFILER.profile(build_farm_snapshot())
        )
