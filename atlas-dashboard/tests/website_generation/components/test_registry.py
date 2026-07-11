"""ComponentRegistry tests (AES-WEB-002A; AES-WEB-002 §15).

Empty registry, registration, exact and version-aware lookup, duplicate and
conflicting registration, malformed rejection, deterministic inventory and
fingerprint, insertion-order independence, immutability of returned
collections, and instance isolation (no global state).
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.components import (
    AnalyticsContract,
    RenderingContract,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    PageRole,
    LifecycleStatus,
)
from engines.website_generation.contracts.errors import (
    ComponentNotFoundError,
    ConflictingComponentError,
    DuplicateComponentError,
    InvalidComponentDefinitionError,
    UnsupportedComponentVersionError,
)
from engines.website_generation.components.catalog.layout_atoms import (
    WAVE1_COMPONENTS,
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
        # make_definition()'s defaults are keyed to its own component_id;
        # without overriding these, this fixture would silently collide
        # with make_definition()'s emitter_key/impression_id whenever both
        # are registered together (AES-REVIEW-001A #2 caught this).
        rendering_contract=RenderingContract(
            emitter_key="listing.card.standard@1", class_prefix="ac-listing"
        ),
        analytics_contract=AnalyticsContract(
            impression_id="listing-card-standard"
        ),
    )
    base.update(over)
    return make_definition(**base)


class TestEmptyRegistry:
    def test_empty_registry_is_valid(self):
        r = ComponentRegistry()
        assert len(r) == 0
        assert r.all_definitions() == ()
        assert r.inventory() == ()

    def test_registered_components_holds_wave1(self):
        # 002A shipped the tuple empty; 002B populated Wave 1 (§27.2: 15
        # foundation primitives) and 002C appended Wave 2 (§27.3: 8 more).
        # Wave 1 must remain a subset of whatever the full registry holds
        # today; exact per-wave inventory is asserted in each wave's own
        # test_catalog_waveN.py.
        assert len(REGISTERED_COMPONENTS) >= len(WAVE1_COMPONENTS)
        assert set(d.component_id for d in WAVE1_COMPONENTS) <= set(
            d.component_id for d in REGISTERED_COMPONENTS
        )
        assert len(build_default_registry()) == len(REGISTERED_COMPONENTS)

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


class TestCrossDefinitionUniqueness:
    """AES-REVIEW-001A #2: distinct component_ids must never share an
    emitter_key or impression_id (§20.1: the emitter table is keyed by
    (component_id, major_version), so a collision across different ids
    means two components would render through the same emitter)."""

    def test_distinct_ids_sharing_emitter_key_rejected(self):
        a = make_definition(component_id="hero.split.value-proposition")
        b = make_definition(
            component_id="hero.centered.standard",
            display_name="Different",
            rendering_contract=a.rendering_contract,  # copy-paste collision
        )
        with pytest.raises(ConflictingComponentError):
            ComponentRegistry([a, b])

    def test_distinct_ids_sharing_impression_id_rejected(self):
        a = make_definition(component_id="hero.split.value-proposition")
        b = make_definition(
            component_id="hero.centered.standard",
            display_name="Different",
            rendering_contract=RenderingContract(
                emitter_key="hero.centered.standard@1", class_prefix="ac-hero"
            ),
            analytics_contract=a.analytics_contract,  # copy-paste collision
        )
        with pytest.raises(ConflictingComponentError):
            ComponentRegistry([a, b])

    def test_same_id_different_versions_may_share_emitter_key(self):
        # Legal per §20.1: the emitter table is keyed by (id, major
        # version), so patch/minor versions of the SAME id sharing an
        # emitter_key/impression_id is expected, not a conflict.
        v1 = make_definition(component_version="1.0.0")
        v2 = make_definition(component_version="1.0.1")
        r = ComponentRegistry([v1, v2])
        assert len(r) == 2

    def test_valid_wave1_catalog_has_no_collisions(self):
        # The real registered catalog must pass the new uniqueness check —
        # regression guard against a future copy-paste collision shipping.
        assert len(build_default_registry()) == len(REGISTERED_COMPONENTS)


class TestSecondaryIndexes:
    """AES-REVIEW-001A #3: candidates_for()/by_family() must return results
    identical to the pre-optimization O(n) scan, via indexes built once,
    deterministically, at construction — no behavior change, no new API."""

    def test_candidates_for_matches_linear_scan(self):
        defs = [make_definition(), _listing_def()]
        r = ComponentRegistry(defs)
        expected = tuple(
            d for d in r.all_definitions() if PageRole.HOME in d.supported_page_roles
        )
        assert r.candidates_for(PageRole.HOME) == expected

    def test_by_family_matches_linear_scan(self):
        defs = [make_definition(), _listing_def()]
        r = ComponentRegistry(defs)
        expected = tuple(
            d for d in r.all_definitions() if d.component_family is ComponentFamily.HERO
        )
        assert r.by_family(ComponentFamily.HERO) == expected

    def test_unindexed_page_role_returns_empty_tuple(self):
        r = ComponentRegistry([make_definition()])
        assert r.candidates_for(PageRole.SPONSOR_PAGE) == ()

    def test_unindexed_family_returns_empty_tuple(self):
        r = ComponentRegistry([make_definition()])
        assert r.by_family(ComponentFamily.MONETIZATION) == ()

    def test_index_results_are_immutable_tuples(self):
        r = ComponentRegistry([make_definition()])
        result = r.candidates_for(PageRole.HOME)
        assert isinstance(result, tuple)
        # Mutating a fetched result cannot affect a second fetch (the index
        # itself stores the tuple, not a mutable list).
        _ = list(result)
        assert r.candidates_for(PageRole.HOME) == result

    def test_indexes_independent_of_insertion_order(self):
        a = make_definition()
        b = _listing_def()
        forward = ComponentRegistry([a, b])
        backward = ComponentRegistry([b, a])
        assert forward.candidates_for(PageRole.HOME) == backward.candidates_for(
            PageRole.HOME
        )
        assert forward.by_family(ComponentFamily.HERO) == backward.by_family(
            ComponentFamily.HERO
        )

    def test_wave1_registry_indexes_match_wave1_expectations(self):
        # End-to-end equivalence proof against the real Wave 1 catalog: the
        # documented HOME candidate count (12 of 15; three atoms are
        # form-scoped) must hold through the index path. Scoped to a
        # Wave-1-only registry (not build_default_registry(), which now
        # spans every registered wave) so this fact stays isolated.
        r = ComponentRegistry(WAVE1_COMPONENTS)
        assert len(r.candidates_for(PageRole.HOME)) == 12
        assert len(r.by_family(ComponentFamily.LAYOUT)) == 6
        assert len(r.by_family(ComponentFamily.ATOM)) == 9


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

    def test_secondary_indexes_are_isolated_per_instance(self):
        empty = ComponentRegistry()
        populated = ComponentRegistry([make_definition()])
        assert empty.candidates_for(PageRole.HOME) == ()
        assert len(populated.candidates_for(PageRole.HOME)) == 1
        assert empty.by_family(ComponentFamily.HERO) == ()
        assert len(populated.by_family(ComponentFamily.HERO)) == 1

    def test_no_global_state_leakage(self):
        # Building a populated registry must not mutate a later empty one.
        ComponentRegistry([make_definition(), _listing_def()])
        assert len(ComponentRegistry()) == 0
        assert build_default_registry() is not build_default_registry()
