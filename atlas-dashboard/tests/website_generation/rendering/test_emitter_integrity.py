"""Emitter-table integrity tests (AES-WEB-002J.8; AES-WEB-002 §20.1).

Covers: exactly the 32 J.8 keys resolve exactly once, the 40 J.9 keys are
explicitly expected-absent (never silently "just missing"), duplicate
registration fails deterministically, and every J.8 key's registered
emitter is a pure callable matching the emitter-key -> component_id
identity the registry itself enforces.
"""

from __future__ import annotations

import pytest

from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.contracts.enums import LifecycleStatus
from engines.website_generation.contracts.errors import RenderError
from engines.website_generation.rendering.emitters_discovery import DISCOVERY_EMITTERS
from engines.website_generation.rendering.emitters_layout_atoms import (
    LAYOUT_ATOMS_EMITTERS,
)
from engines.website_generation.rendering.emitters_navigation import NAVIGATION_EMITTERS
from engines.website_generation.rendering.renderer import (
    EMITTER_TABLE,
    J9_EXPECTED_ABSENT_EMITTER_KEYS,
    _build_emitter_table,
)

from . import J8_COMPONENT_IDS


class TestEmitterTableSize:
    def test_exactly_32_j8_keys_registered(self):
        assert len(EMITTER_TABLE) == 32

    def test_family_table_sizes(self):
        assert len(LAYOUT_ATOMS_EMITTERS) == 15
        assert len(NAVIGATION_EMITTERS) == 8
        assert len(DISCOVERY_EMITTERS) == 9

    def test_family_tables_partition_the_merged_table(self):
        merged = set(LAYOUT_ATOMS_EMITTERS) | set(NAVIGATION_EMITTERS) | set(DISCOVERY_EMITTERS)
        assert merged == set(EMITTER_TABLE)
        assert len(LAYOUT_ATOMS_EMITTERS) + len(NAVIGATION_EMITTERS) + len(
            DISCOVERY_EMITTERS
        ) == len(EMITTER_TABLE)


class TestEmitterKeysMatchCatalog:
    def test_every_j8_key_matches_a_registered_component(self):
        registry = build_default_registry()
        for key in EMITTER_TABLE:
            component_id = key.rsplit("@", 1)[0]
            definition = registry.get(component_id)
            assert definition.rendering_contract.emitter_key == key

    def test_every_j8_key_resolves_exactly_once(self):
        registry = build_default_registry()
        seen = set()
        for component_id in J8_COMPONENT_IDS:
            definition = registry.get(component_id)
            key = definition.rendering_contract.emitter_key
            assert key not in seen, "duplicate resolution for %r" % key
            seen.add(key)
            assert key in EMITTER_TABLE

    def test_no_j8_component_is_active_or_preferred(self):
        # D-3: every J.8 component stays PROPOSED -- no lifecycle promotion.
        registry = build_default_registry()
        for component_id in J8_COMPONENT_IDS:
            status = registry.lifecycle(component_id)
            assert status == LifecycleStatus.PROPOSED, (component_id, status)


class TestJ9ExpectedAbsent:
    def test_j9_set_has_exactly_40_keys(self):
        assert len(J9_EXPECTED_ABSENT_EMITTER_KEYS) == 40

    def test_j9_keys_are_not_registered(self):
        overlap = set(EMITTER_TABLE) & J9_EXPECTED_ABSENT_EMITTER_KEYS
        assert not overlap

    def test_j8_plus_j9_covers_the_full_72_component_catalog(self):
        registry = build_default_registry()
        all_keys = {
            d.rendering_contract.emitter_key for d in registry.all_definitions()
        }
        assert len(all_keys) == 72
        assert set(EMITTER_TABLE) | J9_EXPECTED_ABSENT_EMITTER_KEYS == all_keys

    def test_j9_keys_belong_to_deferred_families(self):
        registry = build_default_registry()
        deferred_families = {"listing", "profile", "content", "trust", "form", "cta",
                              "seo", "monetization", "commerce", "status", "legal"}
        for key in J9_EXPECTED_ABSENT_EMITTER_KEYS:
            component_id = key.rsplit("@", 1)[0]
            definition = registry.get(component_id)
            assert definition.component_family.value in deferred_families, component_id


class TestDuplicateRegistrationFails:
    def test_duplicate_key_across_family_tables_raises(self, monkeypatch):
        import engines.website_generation.rendering.renderer as renderer_module

        fake_navigation = dict(NAVIGATION_EMITTERS)
        # Steal a layout_atoms key into the navigation table to simulate a
        # copy-paste collision across families.
        collided_key = next(iter(LAYOUT_ATOMS_EMITTERS))
        fake_navigation[collided_key] = LAYOUT_ATOMS_EMITTERS[collided_key]
        monkeypatch.setattr(renderer_module, "NAVIGATION_EMITTERS", fake_navigation)

        with pytest.raises(RenderError) as exc_info:
            renderer_module._build_emitter_table()
        assert exc_info.value.diagnostics["emitter_key"] == collided_key


class TestMissingEmitterDiagnostic:
    def test_unregistered_component_id_has_no_table_entry(self):
        # listing.card.standard is a real, registered J.9 component with no
        # emitter -- proving "missing" is deliberate, not a KeyError trap.
        assert "listing.card.standard@1" not in EMITTER_TABLE
        assert EMITTER_TABLE.get("listing.card.standard@1") is None
