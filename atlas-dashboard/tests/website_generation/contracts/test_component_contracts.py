"""ComponentDefinition contract tests (AES-WEB-002A; AES-WEB-002 §3, §8).

Frozen behavior, required fields, extra-field rejection, enum validation,
container normalization, canonical serialization, and content identity.
Also re-asserts that no thirteenth artifact kind was added and that the
amendment-A1 ComponentManifest schemas remain supported.
"""

from __future__ import annotations

import json

import pytest

from engines.website_generation.contracts.artifacts import (
    ArtifactCanonicalizationError,
    canonical_json,
    model_to_dict,
)
from engines.website_generation.contracts.components import (
    AnalyticsContract,
    ComponentDefinition,
    PropSpec,
    RenderingContract,
    SlotSpec,
)
from engines.website_generation.contracts.enums import (
    ArtifactKind,
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
    PropType,
    SemanticElement,
    SlotCardinality,
)
from engines.website_generation.contracts.versions import (
    registered_artifact_model,
)
from engines.website_generation.components.registry import (
    definition_fingerprint,
)

from ..components import make_definition


class TestComponentDefinitionShape:
    def test_definition_is_frozen(self):
        d = make_definition()
        with pytest.raises(Exception):
            d.component_id = "other.id.here"

    def test_required_header_fields_are_mandatory(self):
        # analytics_contract and rendering_contract have no defaults.
        with pytest.raises(Exception):
            ComponentDefinition(
                component_id="hero.split.value-proposition",
                component_family=ComponentFamily.HERO,
                component_version="1.0.0",
                lifecycle_status=LifecycleStatus.ACTIVE,
                commercial_purpose=CommercialPurpose.COMMUNICATE_VALUE,
                semantic_element=SemanticElement.SECTION,
                # analytics_contract / rendering_contract omitted
            )

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            make_definition(not_a_real_field="x")

    def test_invalid_enum_value_rejected(self):
        with pytest.raises(Exception):
            make_definition(component_family="not-a-family")
        with pytest.raises(Exception):
            make_definition(lifecycle_status="NOPE")

    def test_sub_contracts_frozen(self):
        spec = PropSpec(prop_type=PropType.BOOL)
        with pytest.raises(Exception):
            spec.prop_type = PropType.STR_ENUM

    def test_lists_normalized_to_tuples(self):
        # Tuple fields accept a list at construction and normalize to tuple.
        d = make_definition(design_token_dependencies=["focus.ring.default"])
        assert isinstance(d.design_token_dependencies, tuple)

    def test_typed_slot_and_prop_maps(self):
        d = make_definition(
            required_content_slots={
                "heading": SlotSpec(
                    block_type="RichTextBlock",
                    cardinality=SlotCardinality.EXACTLY_ONE,
                )
            },
            optional_props={
                "columns": PropSpec(
                    prop_type=PropType.INT_BOUNDED,
                    int_min=1,
                    int_max=4,
                    default="2",
                )
            },
        )
        assert d.required_content_slots["heading"].block_type == "RichTextBlock"
        assert d.optional_props["columns"].prop_type is PropType.INT_BOUNDED


class TestCanonicalSerialization:
    def test_deterministic_across_construction_order(self):
        a = make_definition()
        b = make_definition()
        assert canonical_json(model_to_dict(a)) == canonical_json(
            model_to_dict(b)
        )

    def test_enum_values_serialize_as_strings(self):
        payload = json.loads(canonical_json(model_to_dict(make_definition())))
        assert payload["component_family"] == "hero"
        assert payload["lifecycle_status"] == "ACTIVE"

    def test_no_floats_present(self):
        # Scores/budgets are integer; a definition with no float fields
        # serializes cleanly (AES-REVIEW-001A #4: this half was previously
        # a no-op assertion — now a real value check).
        payload = model_to_dict(make_definition())
        text = canonical_json(payload)
        assert json.loads(text) == json.loads(
            canonical_json(model_to_dict(make_definition()))
        )

        # The canonical serializer actively rejects floats anywhere in the
        # payload (contracts/artifacts.py's _canonicalize), not merely
        # "happens not to contain one" — inject a float and assert the
        # typed rejection actually fires.
        payload["component_version"] = 1.0
        with pytest.raises(ArtifactCanonicalizationError):
            canonical_json(payload)


class TestContentIdentity:
    def test_identical_definition_identical_identity(self):
        assert definition_fingerprint(
            make_definition()
        ) == definition_fingerprint(make_definition())

    def test_changed_definition_changes_identity(self):
        base = definition_fingerprint(make_definition())
        changed = definition_fingerprint(
            make_definition(display_name="Different Name")
        )
        assert base != changed

    def test_fingerprint_is_sha256_hex(self):
        digest = definition_fingerprint(make_definition())
        assert len(digest) == 64
        int(digest, 16)


class TestNoArtifactKindAdded:
    def test_still_twelve_artifact_kinds(self):
        assert len(list(ArtifactKind)) == 12

    def test_component_manifest_1_0_0_and_1_1_0_supported(self):
        assert registered_artifact_model(
            ArtifactKind.COMPONENT_MANIFEST, "1.0.0"
        ) is not None
        assert registered_artifact_model(
            ArtifactKind.COMPONENT_MANIFEST, "1.1.0"
        ) is not None
