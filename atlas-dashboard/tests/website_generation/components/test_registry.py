"""ComponentRegistry tests (AES-WEB-002A; AES-WEB-002 §15).

Empty registry, registration, exact and version-aware lookup, duplicate and
conflicting registration, malformed rejection, deterministic inventory and
fingerprint, insertion-order independence, immutability of returned
collections, and instance isolation (no global state).
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
)
from engines.website_generation.contracts.errors import (
    ComponentNotFoundError,
    ConflictingComponentError,
    DuplicateComponentError,
    InvalidComponentDefinitionError,
    UnsupportedComponentVersionError,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
)

from . import make_definition


def _listing_def(**over):
    base = dict(
        component_id="listing.card.standard",
        component_family=ComponentFamily.LISTING,
        commercial_purpose=CommercialPurpose.EXPOSE_INVENTORY,
    )
    base.update(over)
    return make_definition(**base)


class TestEmptyRegistry:
    def test_empty_registry_is_valid(self):
        r = ComponentRegistry()
        assert len(r) == 0
        assert r.all_definitions() == ()
        assert r.inventory() == ()

    def test_registered_components_is_empty_in_002a(self):
        assert REGISTERED_COMPONENTS == ()
        assert len(build_default_registry()) == 0

    def test_empty_registry_has_stable_fingerprint(self):
        assert ComponentRegistry().registry_hash() == (
            ComponentRegistry().registry_hash()
        )

    def test_lookup_on_empty_raises_not_found(self):
        with pytest.raises(ComponentNotFoundError):
            ComponentRegistry().get("hero.split.value-proposition")


class TestRegistration:
    def test_valid_registration_and_exact_lookup(self):
        d = make_definition()
        r = ComponentRegistry([d])
        assert len(r) == 1
        assert r.get("hero.split.value-proposition").component_id == d.component_id
        assert "hero.split.value-proposition" in r

    def test_version_aware_lookup(self):
        v1 = make_definition(component_version="1.0.0")
        v11 = make_definition(component_version="1.1.0")
        r = ComponentRegistry([v1, v11])
        # No version_req -> latest.
        assert r.get("hero.split.value-proposition").component_version == "1.1.0"
        # Exact version.
        assert (
            r.get("hero.split.value-proposition", "1.0.0").component_version
            == "1.0.0"
        )

    def test_component_not_found(self):
        r = ComponentRegistry([make_definition()])
        with pytest.raises(ComponentNotFoundError):
            r.get("listing.card.standard")

    def test_unsupported_version_rejected(self):
        r = ComponentRegistry([make_definition(component_version="1.0.0")])
        with pytest.raises(UnsupportedComponentVersionError):
            r.get("hero.split.value-proposition", "9.9.9")

    def test_duplicate_registration_rejected(self):
        d = make_definition()
        with pytest.raises(DuplicateComponentError):
            ComponentRegistry([d, d])

    def test_conflicting_registration_rejected(self):
        # id family segment (listing) conflicts with declared family (hero).
        bad = make_definition(
            component_id="listing.card.standard",
            component_family=ComponentFamily.HERO,
        )
        with pytest.raises(ConflictingComponentError):
            ComponentRegistry([bad])

    def test_malformed_definition_rejected(self):
        with pytest.raises(InvalidComponentDefinitionError):
            ComponentRegistry([make_definition(component_id="not_valid")])
        with pytest.raises(InvalidComponentDefinitionError):
            ComponentRegistry([make_definition(component_version="1.0")])

    def test_deprecated_without_replacement_rejected(self):
        with pytest.raises(InvalidComponentDefinitionError):
            ComponentRegistry(
                [make_definition(lifecycle_status=LifecycleStatus.DEPRECATED)]
            )


class TestDeterminism:
    def test_inventory_is_deterministic_and_sorted(self):
        r = ComponentRegistry([_listing_def(), make_definition()])
        ids = [e.component_id for e in r.inventory()]
        assert ids == sorted(ids)
        assert ids == ["hero.split.value-proposition", "listing.card.standard"]

    def test_fingerprint_independent_of_insertion_order(self):
        a = make_definition()
        b = _listing_def()
        assert (
            ComponentRegistry([a, b]).registry_hash()
            == ComponentRegistry([b, a]).registry_hash()
        )

    def test_changed_definition_changes_fingerprint(self):
        base = ComponentRegistry([make_definition()]).registry_hash()
        changed = ComponentRegistry(
            [make_definition(display_name="Changed")]
        ).registry_hash()
        assert base != changed

    def test_returned_collections_are_immutable_tuples(self):
        r = ComponentRegistry([make_definition(), _listing_def()])
        assert isinstance(r.all_definitions(), tuple)
        assert isinstance(r.inventory(), tuple)
        assert isinstance(r.by_family(ComponentFamily.HERO), tuple)
        # Using a returned collection cannot change registry length.
        _ = list(r.all_definitions())
        assert len(r) == 2


class TestIsolation:
    def test_instances_are_isolated(self):
        empty = ComponentRegistry()
        populated = ComponentRegistry([make_definition()])
        assert len(empty) == 0
        assert len(populated) == 1
        assert empty.registry_hash() != populated.registry_hash()

    def test_no_global_state_leakage(self):
        # Building a populated registry must not mutate a later empty one.
        ComponentRegistry([make_definition(), _listing_def()])
        assert len(ComponentRegistry()) == 0
        assert build_default_registry() is not build_default_registry()
