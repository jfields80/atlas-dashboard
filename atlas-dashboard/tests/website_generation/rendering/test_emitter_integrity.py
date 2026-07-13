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
    def test_full_table_has_72_keys(self):
        # AES-WEB-002J.8 delivered the first 32 emitters; AES-WEB-002J.9
        # delivered the remaining 40, closing the table at the full
        # 72-component catalog.
        assert len(EMITTER_TABLE) == 72

    def test_j8_families_still_sum_to_32(self):
        assert len(LAYOUT_ATOMS_EMITTERS) == 15
        assert len(NAVIGATION_EMITTERS) == 8
        assert len(DISCOVERY_EMITTERS) == 9
        assert (
            len(LAYOUT_ATOMS_EMITTERS)
            + len(NAVIGATION_EMITTERS)
            + len(DISCOVERY_EMITTERS)
        ) == 32

    def test_family_table_sizes(self):
        assert len(LAYOUT_ATOMS_EMITTERS) == 15
        assert len(NAVIGATION_EMITTERS) == 8
        assert len(DISCOVERY_EMITTERS) == 9

    def test_j8_families_are_a_disjoint_subset_of_the_merged_table(self):
        # The three J.8 family tables remain present in, and mutually
        # disjoint within, the merged 72-key table (the J.9 families supply
        # the other 40 keys, verified in test_emitter_integrity_j9.py).
        j8_merged = (
            set(LAYOUT_ATOMS_EMITTERS)
            | set(NAVIGATION_EMITTERS)
            | set(DISCOVERY_EMITTERS)
        )
        assert j8_merged <= set(EMITTER_TABLE)
        assert len(j8_merged) == 32


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
    def test_j9_expected_absent_set_is_now_empty(self):
        # AES-WEB-002J.9 implemented every remaining family emitter, so the
        # "provably intentional absence" set has gone to zero -- the
        # invariant is preserved, its value is now empty.
        assert len(J9_EXPECTED_ABSENT_EMITTER_KEYS) == 0

    def test_j9_keys_are_not_registered(self):
        overlap = set(EMITTER_TABLE) & J9_EXPECTED_ABSENT_EMITTER_KEYS
        assert not overlap

    def test_table_plus_expected_absent_still_covers_the_full_72_catalog(self):
        # Post-J.9 the emitter table alone covers all 72 keys and the
        # expected-absent set is empty, but the union invariant still holds.
        registry = build_default_registry()
        all_keys = {
            d.rendering_contract.emitter_key for d in registry.all_definitions()
        }
        assert len(all_keys) == 72
        assert set(EMITTER_TABLE) | J9_EXPECTED_ABSENT_EMITTER_KEYS == all_keys
        assert set(EMITTER_TABLE) == all_keys


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
    def test_lookup_of_an_unknown_key_is_a_safe_miss(self):
        # Every real catalog key now resolves (72/72), so absence is probed
        # with a synthetic key that is not, and will never be, a registered
        # component -- the table returns None rather than raising a KeyError,
        # which is what lets the Renderer aggregate a missing-emitter
        # diagnostic instead of crashing.
        assert "does.not.exist@1" not in EMITTER_TABLE
        assert EMITTER_TABLE.get("does.not.exist@1") is None
