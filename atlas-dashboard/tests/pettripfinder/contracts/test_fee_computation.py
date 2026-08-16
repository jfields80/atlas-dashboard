"""PTF-CONTRACT-FOUNDATION-001 -- when a fee may safely become a number.

The five lettered cases are the ones the contract freeze named. They are the
boundary of the whole idea: A and E may be totalled, B and D may be totalled
for one animal only, and C may not be totalled at all. Getting any of them
wrong shows a guest a price the hotel never quoted.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.fee_computation import (
    classification_disagreements, classify,
)
from scripts.pettripfinder.contracts.policy_schema import money

SAFE_ANY = enums.COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT
SAFE_ONE = enums.COMPUTATION_SAFE_ONE_PET_ONLY
CONDITIONAL = enums.CONDITIONALLY_SAFE
NOT_COMPUTABLE = enums.NOT_COMPUTABLE


def fee(cents=5000, **kw):
    return dict(money(cents), **kw)


def tier(cents, lo, hi, *, role=enums.ROLE_REPLACEMENT_PRICE,
         basis_stated=True, **kw):
    return dict(money(cents), role=role, condition_type=enums.CONDITION_STAY_LENGTH_RANGE,
                boundary_unit=enums.BOUNDARY_NIGHTS, condition_min=lo,
                condition_max=hi, basis_stated=basis_stated, **kw)


class TestNamedCases:
    """The five cases the freeze resolved by hand."""

    def test_case_a_room_scoped_nightly(self):
        """$50 per room per night, 2 pets -> any allowed count is safe."""
        got = classify({"pet_fee": fee(basis="per_night", scope="per_room"),
                        "pet_count_limit": 2})
        assert got.computation_class == SAFE_ANY

    def test_case_b_scope_not_stated_with_multiple_pets(self):
        """$50 per night, 2 pets, no scope -> one pet only.

        Per pet the stay costs $100; per room it costs $50. Nothing in the
        record chooses, so nothing may.
        """
        got = classify({"pet_fee": fee(basis="per_night"), "pet_count_limit": 2})
        assert got.computation_class == SAFE_ONE

    def test_case_c_tier_basis_unstated(self):
        """$50 for 1-4 nights, $75 for 5+, never said nightly or total."""
        got = classify({"fee_tiers": [tier(5000, 1, 4, basis_stated=False),
                                      tier(7500, 5, None, basis_stated=False)]})
        assert got.computation_class == CONDITIONAL

    def test_case_d_cap_without_scope(self):
        """A $150 cap of unknown scope cannot bound two animals."""
        got = classify({
            "pet_fee": fee(basis="per_night", scope="per_pet"),
            "pet_count_limit": 2,
            "fee_cap": dict(money(15000), basis="per_stay", qualifier_stated=True),
        })
        assert got.computation_class == SAFE_ONE

    def test_case_e_single_pet_makes_scope_irrelevant(self):
        """At exactly one pet, per-pet and per-room are the same arithmetic.

        This is the ONLY place an unstated scope is safe, and it is safe
        because no answer a guest sees can differ.
        """
        got = classify({"pet_fee": fee(basis="per_night"), "pet_count_limit": 1})
        assert got.computation_class == SAFE_ANY


class TestNothingToCompute:

    def test_no_charge_at_all(self):
        """Silence about a fee is not a fee of zero."""
        assert classify({"pets_allowed": True}).computation_class == NOT_COMPUTABLE

    def test_empty_facts(self):
        assert classify({}).computation_class == NOT_COMPUTABLE

    def test_withheld_fee_is_never_computable(self):
        """Deriving a total would republish a withheld amount as arithmetic."""
        got = classify({"pet_fee": fee(basis="per_night", scope="per_room"),
                        "pet_count_limit": 2,
                        "_withheld_fee_paths": ("pet_fee",)})
        assert got.computation_class == NOT_COMPUTABLE

    def test_withheld_subfield_also_blocks(self):
        got = classify({"pet_fee": fee(basis="per_night"),
                        "_withheld_fee_paths": ("pet_fee.scope",)})
        assert got.computation_class == NOT_COMPUTABLE


class TestTiers:

    def test_missing_role_is_not_computable(self):
        """Without a role, a replacement price and an extra charge look alike."""
        broken = tier(5000, 1, 4)
        del broken["role"]
        assert classify({"fee_tiers": [broken]}).computation_class == NOT_COMPUTABLE

    def test_gap_between_bands_is_not_computable(self):
        """Nights 5 and 6 have no price, so no total is derivable."""
        got = classify({"fee_tiers": [tier(5000, 1, 4), tier(7500, 7, None)],
                        "pet_count_limit": 1})
        assert got.computation_class == NOT_COMPUTABLE

    def test_overlapping_bands_are_not_computable(self):
        got = classify({"fee_tiers": [tier(5000, 1, 5), tier(7500, 4, None)],
                        "pet_count_limit": 1})
        assert got.computation_class == NOT_COMPUTABLE

    def test_contiguous_stated_bands_resolve_by_scope(self):
        got = classify({"fee_tiers": [tier(5000, 1, 4, scope="per_room"),
                                      tier(7500, 5, None, scope="per_room")],
                        "pet_count_limit": 2})
        assert got.computation_class == SAFE_ANY

    def test_additional_charge_does_not_need_to_tile(self):
        """Only replacement tiers must tile; an extra charge is additive."""
        got = classify({
            "fee_tiers": [tier(5000, 1, None, scope="per_room"),
                          tier(2000, 1, None, role=enums.ROLE_ADDITIONAL_CHARGE,
                               scope="per_room")],
            "pet_count_limit": 2})
        assert got.computation_class == SAFE_ANY


class TestCaps:

    def test_cap_scope_is_never_inherited(self):
        """The fee being room-scoped says nothing about the cap's scope."""
        got = classify({
            "pet_fee": fee(basis="per_night", scope="per_room"),
            "pet_count_limit": 2,
            "fee_cap": dict(money(15000), basis="per_stay", qualifier_stated=True)})
        assert got.computation_class == SAFE_ONE

    def test_unstated_qualifier_downgrades(self):
        got = classify({
            "pet_fee": fee(basis="per_night", scope="per_room"),
            "pet_count_limit": 2,
            "fee_cap": dict(money(15000), basis="per_stay", scope="per_room",
                            qualifier_stated=False)})
        assert got.computation_class == SAFE_ONE

    def test_fully_qualified_cap_is_safe(self):
        got = classify({
            "pet_fee": fee(basis="per_night", scope="per_room"),
            "pet_count_limit": 2,
            "fee_cap": dict(money(15000), basis="per_stay", scope="per_room",
                            applies_to_pet_count=2, qualifier_stated=True)})
        assert got.computation_class == SAFE_ANY

    def test_nested_schedule_cap_is_checked_too(self):
        """A cap on a rung bounds real money and obeys the same rules.

        Checking only the fact-level cap is how a second-pet ceiling ends up
        applied to a first pet that stays free.
        """
        got = classify({
            "pet_count_limit": 2,
            "fee_pet_schedule": {"entries": [
                dict(money(0), pet_ordinal=1, basis="per_stay", additive=False),
                dict(money(1500), pet_ordinal=2, basis="per_night", additive=True,
                     cap=dict(money(10500), basis="per_stay", qualifier_stated=True)),
            ]}})
        assert got.computation_class == SAFE_ONE


class TestScope:

    def test_per_pet_without_a_limit_is_unbounded(self):
        got = classify({"pet_fee": fee(basis="per_night", scope="per_pet")})
        assert got.computation_class == SAFE_ONE

    def test_room_allowance_below_the_pet_limit(self):
        """"Covers up to 2 pets" on a property allowing 3 leaves one unpriced."""
        got = classify({
            "pet_fee": fee(basis="per_night", scope="per_room",
                           scope_pet_allowance=2),
            "pet_count_limit": 3})
        assert got.computation_class == CONDITIONAL

    def test_room_allowance_matching_the_limit_is_safe(self):
        got = classify({
            "pet_fee": fee(basis="per_night", scope="per_room",
                           scope_pet_allowance=2),
            "pet_count_limit": 2})
        assert got.computation_class == SAFE_ANY

    def test_scalar_without_basis_is_conditional(self):
        """$100 could be the night or the whole stay."""
        got = classify({"pet_fee": fee(scope="per_room"), "pet_count_limit": 2})
        assert got.computation_class == CONDITIONAL


class TestPetSchedules:

    def test_every_ordinal_priced_is_safe(self):
        got = classify({
            "pet_count_limit": 2,
            "fee_pet_schedule": {"entries": [
                dict(money(8000), pet_ordinal=1, basis="per_stay", additive=False),
                dict(money(5000), pet_ordinal=2, basis="per_stay", additive=True),
            ]}})
        assert got.computation_class == SAFE_ANY

    def test_missing_additive_flag_is_not_computable(self):
        """Without it, rungs can neither be summed nor made to replace."""
        got = classify({
            "pet_count_limit": 2,
            "fee_pet_schedule": {"entries": [
                dict(money(8000), pet_ordinal=1, basis="per_stay"),
                dict(money(5000), pet_ordinal=2, basis="per_stay", additive=True),
            ]}})
        assert got.computation_class == NOT_COMPUTABLE

    def test_incomplete_ladder_is_one_pet_only(self):
        got = classify({
            "pet_count_limit": 3,
            "fee_pet_schedule": {"entries": [
                dict(money(8000), pet_ordinal=1, basis="per_stay", additive=False),
                dict(money(5000), pet_ordinal=2, basis="per_stay", additive=True),
            ]}})
        assert got.computation_class == SAFE_ONE


class TestFilterCapabilities:

    @pytest.mark.parametrize("cls,one,many", [
        (SAFE_ANY, True, True),
        (SAFE_ONE, True, False),
        (CONDITIONAL, False, False),
        (NOT_COMPUTABLE, False, False),
    ])
    def test_filter_matrix(self, cls, one, many):
        assert (cls in enums.COMPUTABLE_FOR_ONE_PET) is one
        assert (cls in enums.COMPUTABLE_FOR_MANY_PETS) is many


class TestStoredVersusDerived:
    """The persist-and-derive design: a gate must be able to catch drift."""

    def test_agreement_is_silent(self):
        record = {"facts": {"pet_fee": fee(basis="per_night", scope="per_room"),
                            "pet_count_limit": 2},
                  "computation_class": SAFE_ANY}
        assert classification_disagreements(record) == ()

    def test_drift_is_reported(self):
        record = {"facts": {"pet_fee": fee(basis="per_night"),
                            "pet_count_limit": 2},
                  "computation_class": SAFE_ANY}
        found = classification_disagreements(record)
        assert len(found) == 1
        assert SAFE_ONE in found[0]

    def test_unmigrated_record_is_not_a_disagreement(self):
        record = {"facts": {"pet_fee": fee(basis="per_night", scope="per_room")}}
        assert classification_disagreements(record) == ()


def test_every_result_names_its_rule():
    """A reviewer needs to know WHICH rule excluded a hotel, not just that one did."""
    for facts in ({}, {"pet_fee": fee(basis="per_night"), "pet_count_limit": 2},
                  {"pet_fee": fee(scope="per_room")}):
        got = classify(facts)
        assert got.rule and got.reason
        assert got.computation_class in enums.COMPUTATION_CLASSES
