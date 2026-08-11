"""Provenance model tests (AES-SEO-001 §5, AMB-3)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engines.demand_mapping.contracts.canonical import ContractValidationError
from engines.demand_mapping.contracts.provenance import (
    CONFIDENCE_BP_MAX,
    CONFIDENCE_BP_MIN,
    PROVENANCE_PRIORITY,
    Provenance,
    TaggedValue,
    merge_tagged_values,
    stronger_provenance,
)


def make_tagged(**overrides):
    fields = dict(
        value=1200,
        provenance=Provenance.ESTIMATED,
        provider_id="test-provider",
        provider_version="1.0.0",
        rationale="deterministic model output for testing",
        confidence_bp=4000,
        observed_at="2026-08-09T00:00:00Z",
    )
    fields.update(overrides)
    return TaggedValue(**fields)


class TestProvenanceEnum:
    def test_exactly_five_states(self):
        assert {member.value for member in Provenance} == {
            "VERIFIED", "ESTIMATED", "DERIVED", "OPERATOR", "UNKNOWN"
        }

    def test_priority_order_is_total_and_ranked(self):
        assert set(PROVENANCE_PRIORITY) == set(Provenance)
        assert (
            PROVENANCE_PRIORITY[Provenance.VERIFIED]
            > PROVENANCE_PRIORITY[Provenance.OPERATOR]
            > PROVENANCE_PRIORITY[Provenance.DERIVED]
            > PROVENANCE_PRIORITY[Provenance.ESTIMATED]
            > PROVENANCE_PRIORITY[Provenance.UNKNOWN]
        )

    def test_stronger_provenance_selects_and_tie_keeps_first(self):
        assert stronger_provenance(
            Provenance.ESTIMATED, Provenance.VERIFIED
        ) is Provenance.VERIFIED
        assert stronger_provenance(
            Provenance.OPERATOR, Provenance.ESTIMATED
        ) is Provenance.OPERATOR
        assert stronger_provenance(
            Provenance.DERIVED, Provenance.DERIVED
        ) is Provenance.DERIVED


class TestTaggedValueRules:
    def test_valid_construction(self):
        tagged = make_tagged()
        assert tagged.value == 1200
        assert tagged.provenance is Provenance.ESTIMATED

    def test_unknown_must_not_carry_confidence(self):
        with pytest.raises(ContractValidationError):
            make_tagged(provenance=Provenance.UNKNOWN, confidence_bp=100)

    def test_unknown_without_confidence_is_legal(self):
        tagged = make_tagged(provenance=Provenance.UNKNOWN, confidence_bp=None)
        assert tagged.confidence_bp is None

    def test_non_unknown_requires_confidence(self):
        with pytest.raises(ContractValidationError):
            make_tagged(confidence_bp=None)

    def test_confidence_bounds(self):
        with pytest.raises(ContractValidationError):
            make_tagged(confidence_bp=CONFIDENCE_BP_MAX + 1)
        with pytest.raises(ContractValidationError):
            make_tagged(confidence_bp=CONFIDENCE_BP_MIN - 1)
        assert make_tagged(confidence_bp=CONFIDENCE_BP_MAX).confidence_bp == 10000

    def test_float_value_rejected_by_strict_typing(self):
        with pytest.raises(ValidationError):
            make_tagged(value=12.5)

    def test_float_confidence_rejected_by_strict_typing(self):
        with pytest.raises(ValidationError):
            make_tagged(confidence_bp=40.5)

    def test_empty_provider_and_rationale_rejected(self):
        with pytest.raises(ContractValidationError):
            make_tagged(provider_id="")
        with pytest.raises(ContractValidationError):
            make_tagged(rationale="")
        with pytest.raises(ContractValidationError):
            make_tagged(observed_at="")


class TestMergeNeverUpgrades:
    def test_merge_returns_one_of_the_inputs_untouched(self):
        estimated = make_tagged()
        verified = make_tagged(
            provenance=Provenance.VERIFIED, confidence_bp=100
        )
        winner = merge_tagged_values(estimated, verified)
        assert winner is verified

    def test_estimated_can_never_become_verified(self):
        first = make_tagged(confidence_bp=9999)
        second = make_tagged(confidence_bp=1)
        winner = merge_tagged_values(first, second)
        assert winner.provenance is Provenance.ESTIMATED
        assert winner in (first, second)

    def test_merge_provenance_is_always_from_an_input(self):
        for state_a in Provenance:
            for state_b in Provenance:
                a = make_tagged(
                    provenance=state_a,
                    confidence_bp=None if state_a is Provenance.UNKNOWN else 500,
                )
                b = make_tagged(
                    provenance=state_b,
                    confidence_bp=None if state_b is Provenance.UNKNOWN else 700,
                )
                winner = merge_tagged_values(a, b)
                assert winner in (a, b)
                assert winner.provenance in (state_a, state_b)

    def test_tie_breaks_on_confidence_then_first(self):
        low = make_tagged(confidence_bp=100)
        high = make_tagged(confidence_bp=200)
        assert merge_tagged_values(low, high) is high
        assert merge_tagged_values(high, low) is high
        twin = make_tagged(confidence_bp=100)
        assert merge_tagged_values(low, twin) is low
