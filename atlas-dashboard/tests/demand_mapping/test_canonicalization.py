"""Canonical serialization, float rejection, hash identity (AES-SEO-001 §4)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engines.demand_mapping.contracts.canonical import (
    ContractCanonicalizationError,
    canonical_contract_json,
    canonical_json,
    contract_sha256,
    sha256_of_text,
)
from engines.demand_mapping.contracts.provenance import Provenance, TaggedValue


def make_tagged():
    return TaggedValue(
        value=1200,
        provenance=Provenance.ESTIMATED,
        provider_id="test-provider",
        provider_version="1.0.0",
        rationale="deterministic model output for testing",
        confidence_bp=4000,
        observed_at="2026-08-09T00:00:00Z",
    )


class TestFloatRejection:
    def test_top_level_float_rejected(self):
        with pytest.raises(ContractCanonicalizationError):
            canonical_json(1.5)

    def test_nested_float_rejected(self):
        with pytest.raises(ContractCanonicalizationError):
            canonical_json({"a": {"b": [1, 2, 3.5]}})

    def test_float_in_tuple_rejected(self):
        with pytest.raises(ContractCanonicalizationError):
            canonical_json((1, 2.0))


class TestCanonicalForm:
    def test_sorted_keys_compact_separators(self):
        assert canonical_json({"b": 1, "a": None}) == '{"a":null,"b":1}'

    def test_enum_collapses_to_value(self):
        assert canonical_json(Provenance.VERIFIED) == '"VERIFIED"'

    def test_non_string_keys_rejected(self):
        with pytest.raises(ContractCanonicalizationError):
            canonical_json({1: "a"})

    def test_unsupported_types_rejected(self):
        with pytest.raises(ContractCanonicalizationError):
            canonical_json({"a": object()})

    def test_none_preserved_never_dropped(self):
        text = canonical_contract_json(
            TaggedValue(
                value=1,
                provenance=Provenance.UNKNOWN,
                provider_id="p",
                provider_version="1",
                rationale="no basis",
                confidence_bp=None,
                observed_at="2026-08-09T00:00:00Z",
            )
        )
        assert '"confidence_bp":null' in text


class TestDeterministicIdentity:
    def test_double_construction_is_byte_identical(self):
        first, second = make_tagged(), make_tagged()
        assert canonical_contract_json(first) == canonical_contract_json(second)
        assert contract_sha256(first) == contract_sha256(second)

    def test_hash_is_sha256_of_canonical_text(self):
        tagged = make_tagged()
        assert contract_sha256(tagged) == sha256_of_text(
            canonical_contract_json(tagged)
        )

    def test_different_content_different_hash(self):
        base = make_tagged()
        other = TaggedValue(
            value=1201,
            provenance=base.provenance,
            provider_id=base.provider_id,
            provider_version=base.provider_version,
            rationale=base.rationale,
            confidence_bp=base.confidence_bp,
            observed_at=base.observed_at,
        )
        assert contract_sha256(base) != contract_sha256(other)


class TestImmutability:
    def test_frozen_models_reject_mutation(self):
        tagged = make_tagged()
        with pytest.raises(Exception):
            tagged.value = 9

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            TaggedValue(
                value=1,
                provenance=Provenance.ESTIMATED,
                provider_id="p",
                provider_version="1",
                rationale="r",
                confidence_bp=1,
                observed_at="2026-08-09T00:00:00Z",
                unexpected_field="x",
            )
