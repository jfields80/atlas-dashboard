"""PetTripFinder adapter tests + committed-Columbus golden validation.

Fixture provenance: ``fixtures/columbus_seed_businesses.csv`` and
``fixtures/columbus_hotel_policy_facts.json`` are byte-exact extracts of
the committed HEAD versions of
``launch_packages/pettripfinder/{seed_businesses.csv,
hotel_policy_facts.json}`` at commit 4d28eca (verified by git blob hash at
extraction time). The working-tree copies were NOT used — they carry
uncommitted concurrent Dayton-session changes (Phase-B authority §10).
"""

from __future__ import annotations

from pathlib import Path

from engines.demand_mapping.contracts.dimensions import DimensionKind
from engines.demand_mapping.contracts.provenance import Provenance
from engines.demand_mapping.profiling import InventoryProfiler
from services.demand_research.adapters.pettripfinder import (
    build_generic_records,
    build_inventory_snapshot,
    load_policy_records,
    load_seed_rows,
    normalize_entity_key,
    parse_bool_word,
    parse_money_cents,
    parse_plain_int,
    parse_pounds_tenths,
    species_members,
)

FIXTURES = Path(__file__).parent / "fixtures"


def seed_row(**overrides):
    row = {
        "name": "Test Hotel & Suites Downtown",
        "category": "pet-friendly-hotels",
        "city": "Columbus",
        "state": "OH",
        "postal_code": "43215",
        "market_id": "columbus-oh",
    }
    row.update(overrides)
    return row


def policy_record(**overrides):
    record = {
        "key": "test hotel and suites downtown",
        "name": "Test Hotel & Suites Downtown",
        "facts": {
            "pets_allowed": "true",
            "pet_fee": "$50.00",
            "weight_limit": "40.0 pounds",
            "pet_count_limit": "2",
            "fee_basis": "per night",
            "species_allowed": "dogs, cats",
        },
        "evidence": [
            {"field": "pets_allowed", "quote": "q", "value": "true"},
            {"field": "pet_fee", "quote": "q", "value": "$50.00"},
        ],
    }
    record.update(overrides)
    return record


class TestParsers:
    def test_money(self):
        assert parse_money_cents("$50.00") == 5000
        assert parse_money_cents("$50") == 5000
        assert parse_money_cents("$25.5") == 2550
        assert parse_money_cents("50.00") is None
        assert parse_money_cents("$50 per night") is None  # never guess

    def test_pounds(self):
        assert parse_pounds_tenths("75 pounds") == 750
        assert parse_pounds_tenths("40.0 pounds") == 400
        assert parse_pounds_tenths("50 lbs") == 500
        assert parse_pounds_tenths("heavy") is None

    def test_plain_int_and_bool(self):
        assert parse_plain_int("2") == 2
        assert parse_plain_int("two") is None
        assert parse_bool_word("true") is True
        assert parse_bool_word("False") is False
        assert parse_bool_word("yes") is None

    def test_species_members(self):
        assert species_members("dogs, cats") == ("cats", "dogs")
        assert species_members("cats and dogs") == ("cats", "dogs")
        assert species_members("birds, fish, dogs, cats") == (
            "birds", "cats", "dogs", "fish"
        )
        assert species_members("dogs") == ("dogs",)

    def test_key_normalization_matches_ptf_convention(self):
        assert (normalize_entity_key("Drury Inn & Suites Columbus Polaris")
                == "drury inn and suites columbus polaris")
        assert (normalize_entity_key("Aloft Columbus Easton")
                == "aloft columbus easton")


class TestMapping:
    def test_join_and_field_shapes(self):
        records = build_generic_records([seed_row()], [policy_record()])
        assert len(records) == 1
        by_path = {f.field_path: f for f in records[0].fields}
        assert by_path["policy.pet_fee"].value_int == 5000
        assert by_path["policy.pet_fee"].scale_denominator == 100
        assert by_path["policy.weight_limit"].value_int == 400
        assert by_path["policy.pet_count_limit"].value_int == 2
        assert by_path["policy.pets_allowed"].value_bool is True
        assert by_path["identity.city"].kind is DimensionKind.GEOGRAPHIC

    def test_provenance_mapping(self):
        by_path = {
            f.field_path: f
            for f in build_generic_records(
                [seed_row()], [policy_record()]
            )[0].fields
        }
        # evidenced fields → VERIFIED; unevidenced facts → UNKNOWN;
        # seed identity fields → UNKNOWN.
        assert by_path["policy.pets_allowed"].provenance is Provenance.VERIFIED
        assert by_path["policy.pet_fee"].provenance is Provenance.VERIFIED
        assert by_path["policy.weight_limit"].provenance is Provenance.UNKNOWN
        assert by_path["identity.city"].provenance is Provenance.UNKNOWN

    def test_manual_evidence_maps_to_operator(self):
        record = policy_record(manual_evidence=True)
        by_path = {
            f.field_path: f
            for f in build_generic_records([seed_row()], [record])[0].fields
        }
        assert by_path["policy.pets_allowed"].provenance is Provenance.OPERATOR

    def test_membership_explosion_false_vs_missing(self):
        listed = policy_record()  # "dogs, cats" of vocab {cats, dogs}
        other = policy_record(key="other hotel")
        other["facts"] = dict(other["facts"], species_allowed="dogs")
        absent = policy_record(key="third hotel")
        absent["facts"] = {
            k: v for k, v in absent["facts"].items()
            if k != "species_allowed"
        }
        rows = [
            seed_row(),
            seed_row(name="Other Hotel"),
            seed_row(name="Third Hotel"),
        ]
        records = build_generic_records(rows, [listed, other, absent])
        by_entity = {r.entity_id: {f.field_path: f for f in r.fields}
                     for r in records}
        # "dogs" against vocabulary {cats, dogs} → cats explicitly False.
        other_fields = by_entity["other hotel"]
        assert other_fields["policy.species_allowed:cats"].value_bool is False
        assert other_fields["policy.species_allowed:dogs"].value_bool is True
        # record without the field → membership dimensions MISSING entirely.
        assert not any(
            path.startswith("policy.species_allowed")
            for path in by_entity["third hotel"]
        )

    def test_empty_values_are_missing(self):
        row = seed_row(postal_code="  ")
        record_fields = {
            f.field_path
            for f in build_generic_records([row], [])[0].fields
        }
        assert "identity.postal_code" not in record_fields

    def test_market_filter(self):
        rows = [seed_row(), seed_row(name="Elsewhere Inn",
                                     market_id="cleveland-akron-canton-oh")]
        records = build_generic_records(rows, [])
        assert len(records) == 1

    def test_unparseable_values_are_omitted_never_guessed(self):
        record = policy_record()
        record["facts"] = dict(
            record["facts"],
            pet_fee="$100 (1-4 nights), then $100 more",
            weight_limit="call the front desk",
        )
        by_path = {
            f.field_path: f
            for f in build_generic_records([seed_row()], [record])[0].fields
        }
        assert "policy.pet_fee" not in by_path
        assert "policy.weight_limit" not in by_path

    def test_input_order_determinism(self):
        rows = [seed_row(), seed_row(name="Other Hotel")]
        policies = [policy_record(),
                    policy_record(key="other hotel")]
        one = build_inventory_snapshot(rows, policies)
        two = build_inventory_snapshot(list(reversed(rows)),
                                       list(reversed(policies)))
        assert one.snapshot_id == two.snapshot_id


class TestColumbusGolden:
    """Golden validation against the committed Columbus data (fixture
    provenance in the module docstring). Numbers cross-check the known
    Columbus policy-store field counts: pets_allowed 88, pet_count 73,
    weight_limit 62, species 48, pet_fee 39 of 88 records."""

    def build(self):
        seed = load_seed_rows(FIXTURES / "columbus_seed_businesses.csv")
        policy = load_policy_records(
            FIXTURES / "columbus_hotel_policy_facts.json"
        )
        return seed, policy

    def test_snapshot_shape(self):
        seed, policy = self.build()
        snapshot = build_inventory_snapshot(seed, policy)
        assert len(snapshot.records) == 116
        kinds = {}
        for record in snapshot.records:
            kinds[record.entity_kind] = kinds.get(record.entity_kind, 0) + 1
        assert kinds == {"pet-friendly-hotels": 89,
                         "pet-friendly-parks": 14,
                         "pet-friendly-restaurants": 13}
        matched = sum(
            1 for record in snapshot.records
            if any(f.field_path.startswith("policy.")
                   for f in record.fields)
        )
        assert matched == 88  # every committed policy record joins

    def test_golden_profiles(self):
        seed, policy = self.build()
        snapshot = build_inventory_snapshot(seed, policy)
        result = InventoryProfiler().profile(snapshot)
        assert len(result.profiles) == 15
        profiles = {p.dimension_id: p for p in result.profiles}

        allowed = profiles["pet-friendly-hotels:policy.pets_allowed"]
        assert (allowed.entity_count, allowed.coverage_count,
                allowed.missing_count, allowed.distinct_count) == (89, 88, 1, 1)
        assert allowed.provenance_coverage.verified_count == 78
        assert allowed.provenance_coverage.operator_count == 5
        assert allowed.provenance_coverage.unknown_count == 5

        fee = profiles["pet-friendly-hotels:policy.pet_fee"]
        assert (fee.coverage_count, fee.distinct_count) == (39, 7)
        assert (fee.numeric_summary.minimum_scaled,
                fee.numeric_summary.maximum_scaled,
                fee.numeric_summary.scale_denominator) == (2500, 15000, 100)

        limit = profiles["pet-friendly-hotels:policy.weight_limit"]
        assert (limit.coverage_count, limit.distinct_count) == (62, 9)
        assert (limit.numeric_summary.minimum_scaled,
                limit.numeric_summary.maximum_scaled,
                limit.numeric_summary.scale_denominator) == (200, 1250, 10)

        count = profiles["pet-friendly-hotels:policy.pet_count_limit"]
        assert (count.coverage_count,
                count.numeric_summary.maximum_scaled) == (73, 2)

        # Multi-value explosion over the global vocabulary {birds, cats,
        # dogs, fish}; dogs is universal (distinct=1), cats genuinely
        # differentiates (true and false both present, distinct=2).
        dogs = profiles["pet-friendly-hotels:policy.species_allowed:dogs"]
        cats = profiles["pet-friendly-hotels:policy.species_allowed:cats"]
        assert (dogs.coverage_count, dogs.distinct_count) == (48, 1)
        assert (cats.coverage_count, cats.distinct_count) == (48, 2)

        city = profiles["pet-friendly-hotels:identity.city"]
        assert (city.kind, city.coverage_count, city.distinct_count) == (
            DimensionKind.GEOGRAPHIC, 89, 9
        )

    def test_golden_determinism_and_hashes(self):
        seed, policy = self.build()
        one = build_inventory_snapshot(seed, policy)
        two = build_inventory_snapshot(list(reversed(seed)), policy)
        assert one.snapshot_id == two.snapshot_id
        first = InventoryProfiler().profile(one)
        second = InventoryProfiler().profile(two)
        assert first.set_id == second.set_id
        # Byte-level golden anchors for the frozen fixture + adapter 1.0.0
        # + profiler 1.0.0. These change ONLY when fixture, adapter, or
        # engine versions deliberately change.
        assert one.snapshot_id == (
            "5e1817fba788f87aa7954649bab81a7977c87c0fdd6a71b97f64bf3d3dbeb3ed"
        )
        assert first.set_id == (
            "a0b7d183dee9344b8d186849b845f6353aa30bd36d536ae464c52b0d43c51cbc"
        )
