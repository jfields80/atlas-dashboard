"""J.9 emitter-table integrity (AES-WEB-002J.9; AES-WEB-002 §20.1).

Covers: the four new family tables supply exactly the 40 remaining keys, the
merged table is now complete at 72, every one of the 72 registry keys
resolves exactly once, the expected-absent set is empty, all 40 J.9
components stay PROPOSED, and every J.9 key matches ``component_id@1``.
"""

from __future__ import annotations

from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.contracts.enums import LifecycleStatus
from engines.website_generation.rendering.emitters_listings_profiles import (
    LISTINGS_PROFILES_EMITTERS,
)
from engines.website_generation.rendering.emitters_monetization_status import (
    MONETIZATION_STATUS_EMITTERS,
)
from engines.website_generation.rendering.emitters_seo_editorial import (
    SEO_EDITORIAL_EMITTERS,
)
from engines.website_generation.rendering.emitters_trust_conversion import (
    TRUST_CONVERSION_EMITTERS,
)
from engines.website_generation.rendering.renderer import (
    EMITTER_TABLE,
    J9_EXPECTED_ABSENT_EMITTER_KEYS,
)

from . import ALL_COMPONENT_IDS, J8_COMPONENT_IDS, J9_COMPONENT_IDS


class TestJ9FamilyTableSizes:
    def test_family_table_sizes(self):
        assert len(LISTINGS_PROFILES_EMITTERS) == 12
        assert len(TRUST_CONVERSION_EMITTERS) == 13
        assert len(SEO_EDITORIAL_EMITTERS) == 7
        assert len(MONETIZATION_STATUS_EMITTERS) == 8

    def test_j9_families_sum_to_40(self):
        assert (
            len(LISTINGS_PROFILES_EMITTERS)
            + len(TRUST_CONVERSION_EMITTERS)
            + len(SEO_EDITORIAL_EMITTERS)
            + len(MONETIZATION_STATUS_EMITTERS)
        ) == 40

    def test_j9_component_id_count(self):
        assert len(J9_COMPONENT_IDS) == 40


class TestMergedTableComplete:
    def test_table_has_exactly_72_keys(self):
        assert len(EMITTER_TABLE) == 72

    def test_expected_absent_is_empty(self):
        assert len(J9_EXPECTED_ABSENT_EMITTER_KEYS) == 0

    def test_j8_and_j9_partition_the_table(self):
        j8 = set(J8_COMPONENT_IDS)
        j9 = set(J9_COMPONENT_IDS)
        assert len(j8) == 32
        assert len(j9) == 40
        assert not (j8 & j9)
        assert j8 | j9 == set(ALL_COMPONENT_IDS)
        assert len(ALL_COMPONENT_IDS) == 72

    def test_table_exactly_matches_full_registry(self):
        registry = build_default_registry()
        registry_keys = {
            d.rendering_contract.emitter_key for d in registry.all_definitions()
        }
        assert set(EMITTER_TABLE) == registry_keys
        assert len(registry_keys) == 72


class TestJ9KeysResolveExactlyOnce:
    def test_every_j9_key_matches_a_registered_component(self):
        registry = build_default_registry()
        for family_table in (
            LISTINGS_PROFILES_EMITTERS,
            TRUST_CONVERSION_EMITTERS,
            SEO_EDITORIAL_EMITTERS,
            MONETIZATION_STATUS_EMITTERS,
        ):
            for key in family_table:
                component_id = key.rsplit("@", 1)[0]
                definition = registry.get(component_id)
                assert definition.rendering_contract.emitter_key == key
                assert key == component_id + "@1"

    def test_every_registry_key_resolves_exactly_once(self):
        registry = build_default_registry()
        seen = set()
        for definition in registry.all_definitions():
            key = definition.rendering_contract.emitter_key
            assert key not in seen, "duplicate resolution for %r" % key
            seen.add(key)
            assert key in EMITTER_TABLE
        assert len(seen) == 72

    def test_no_j9_family_table_shares_a_key(self):
        tables = [
            LISTINGS_PROFILES_EMITTERS,
            TRUST_CONVERSION_EMITTERS,
            SEO_EDITORIAL_EMITTERS,
            MONETIZATION_STATUS_EMITTERS,
        ]
        seen = set()
        for table in tables:
            for key in table:
                assert key not in seen, key
                seen.add(key)
        assert len(seen) == 40


class TestLifecycleUnchanged:
    def test_all_j9_components_remain_proposed(self):
        registry = build_default_registry()
        for component_id in J9_COMPONENT_IDS:
            status = registry.lifecycle(component_id)
            assert status == LifecycleStatus.PROPOSED, (component_id, status)

    def test_all_72_components_remain_proposed(self):
        registry = build_default_registry()
        for definition in registry.all_definitions():
            assert definition.lifecycle_status == LifecycleStatus.PROPOSED, (
                definition.component_id
            )

    def test_registry_count_still_72(self):
        registry = build_default_registry()
        assert len(registry.all_definitions()) == 72
