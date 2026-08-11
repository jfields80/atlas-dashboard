"""Version registry tests (AES-SEO-001 §19)."""

from __future__ import annotations

import pytest

from engines.demand_mapping.contracts.canonical import SchemaRegistrationError
from engines.demand_mapping.contracts.provenance import TaggedValue
from engines.demand_mapping.contracts.versions import (
    CONTRACTS_VERSION,
    EVIDENCE_MODEL_VERSION,
    SCHEMA_VERSIONS,
    register_schema,
    registered_schema,
    registered_schema_versions,
)

_SEMVER_KINDS = (
    "TaggedValue", "EvidenceObservation", "EvidenceSnapshot",
    "DimensionProfile", "DimensionProfileSet", "GateResult",
    "PageOpportunity", "PageOpportunitySet",
    # Phase B additive minor (contracts 1.1.0):
    "FieldValue", "GenericEntityRecord", "GenericInventorySnapshot",
)


class TestVersionAxes:
    def test_package_versions_declared(self):
        assert CONTRACTS_VERSION == "1.1.0"
        assert EVIDENCE_MODEL_VERSION == "1.0.0"

    def test_every_contract_kind_has_a_schema_version(self):
        assert set(SCHEMA_VERSIONS) == set(_SEMVER_KINDS)
        for kind in _SEMVER_KINDS:
            major, minor, patch = SCHEMA_VERSIONS[kind].split(".")
            assert major.isdigit() and minor.isdigit() and patch.isdigit()


class TestSchemaRegistry:
    def test_all_kinds_registered_at_import(self):
        registered = registered_schema_versions()
        for kind in _SEMVER_KINDS:
            assert SCHEMA_VERSIONS[kind] in registered[kind]

    def test_lookup_returns_model_class(self):
        assert registered_schema(
            "TaggedValue", SCHEMA_VERSIONS["TaggedValue"]
        ) is TaggedValue

    def test_unknown_lookup_fails_loudly(self):
        with pytest.raises(SchemaRegistrationError):
            registered_schema("TaggedValue", "9.9.9")

    def test_reregistering_identical_class_is_idempotent(self):
        register_schema(
            "TaggedValue", SCHEMA_VERSIONS["TaggedValue"], TaggedValue
        )

    def test_duplicate_registration_with_different_class_fails(self):
        class Impostor(TaggedValue):
            pass

        with pytest.raises(SchemaRegistrationError):
            register_schema(
                "TaggedValue", SCHEMA_VERSIONS["TaggedValue"], Impostor
            )
