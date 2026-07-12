"""Wave 3 catalog tests (AES-WEB-002D; AES-WEB-002 §27.4, §15.2, §30.1).

Catalog completeness (exact IDs, versions, families, roles, variants,
count), definition validity, determinism (hash stability across order and
process restarts), compatibility metadata, registry lookups, and
architecture boundaries — mirrors test_catalog_wave2.py's structure.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from engines.website_generation.contracts.artifacts import (
    canonical_json,
    model_to_dict,
)
from engines.website_generation.contracts.enums import (
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
)
from engines.website_generation.components.catalog.discovery import (
    WAVE3_COMPONENTS,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)

APP_ROOT = Path(__file__).resolve().parents[3]

# The exact §27.4 Wave 3 inventory (lexicographic — §15.2 ordering law).
EXPECTED_IDS = [
    "directory.categories.grid",
    "directory.filters.panel",
    "directory.locations.grid",
    "directory.results.summary",
    "directory.search.primary",
    "directory.sort.control",
    "hero.local.standard",
    "hero.search.directory",
    "status.results.zero",
]

EXPECTED_VARIANTS = {
    "hero.search.directory": ("centered", "split"),
    "hero.local.standard": ("compact", "standard"),
    "directory.search.primary": ("condensed", "hero-embedded", "standalone"),
    "directory.categories.grid": ("chips", "tiles"),
    "directory.locations.grid": ("columns", "tiles"),
    "directory.filters.panel": ("chips", "drawer", "sidebar", "top-bar"),
    "directory.sort.control": (),
    "directory.results.summary": (),
    "status.results.zero": (),
}

# §27.4 "Roles" column, mapped to PageRole membership counts.
EXPECTED_ROLE_COUNTS = {
    "hero.search.directory": 1,  # home
    "hero.local.standard": 4,  # cat, city, cc, service-area
    "directory.search.primary": 4,  # home, cat, city, sr
    "directory.categories.grid": 2,  # home, city
    "directory.locations.grid": 3,  # home, cat, regional-hub
    "directory.filters.panel": 3,  # cat, cc, sr
    "directory.sort.control": 3,  # cat, cc, sr
    "directory.results.summary": 3,  # cat, cc, sr
    "status.results.zero": 4,  # cat, city, cc, sr
}


class TestCatalogCompleteness:
    def test_exact_component_ids(self):
        assert [d.component_id for d in WAVE3_COMPONENTS] == EXPECTED_IDS

    def test_exact_catalog_count(self):
        assert len(WAVE3_COMPONENTS) == 9  # §27.4 "Directory discovery (9)"
        # Wave 1 (15) + Wave 2 (8) + Wave 3 (9) + Wave 4 (12) + Wave 5 (13)
        # + Wave 6 (7) = 64.
        assert len(REGISTERED_COMPONENTS) == 64

    def test_exact_versions(self):
        assert all(d.component_version == "1.0.0" for d in WAVE3_COMPONENTS)

    def test_exact_family_assignments(self):
        expected_family = {
            "hero.search.directory": ComponentFamily.HERO,
            "hero.local.standard": ComponentFamily.HERO,
            "directory.search.primary": ComponentFamily.DIRECTORY,
            "directory.categories.grid": ComponentFamily.DIRECTORY,
            "directory.locations.grid": ComponentFamily.DIRECTORY,
            "directory.filters.panel": ComponentFamily.DIRECTORY,
            "directory.sort.control": ComponentFamily.DIRECTORY,
            "directory.results.summary": ComponentFamily.DIRECTORY,
            "status.results.zero": ComponentFamily.STATUS,
        }
        for d in WAVE3_COMPONENTS:
            assert d.component_family is expected_family[d.component_id], (
                d.component_id
            )

    def test_family_counts(self):
        hero = [d for d in WAVE3_COMPONENTS if d.component_family is ComponentFamily.HERO]
        directory = [
            d for d in WAVE3_COMPONENTS if d.component_family is ComponentFamily.DIRECTORY
        ]
        status = [d for d in WAVE3_COMPONENTS if d.component_family is ComponentFamily.STATUS]
        assert len(hero) == 2 and len(directory) == 6 and len(status) == 1

    def test_exact_variant_names(self):
        for d in WAVE3_COMPONENTS:
            expected = EXPECTED_VARIANTS[d.component_id]
            assert tuple(sorted(d.supported_variants)) == expected, d.component_id

    def test_exact_role_counts_match_authority_table(self):
        for d in WAVE3_COMPONENTS:
            assert len(d.supported_page_roles) == EXPECTED_ROLE_COUNTS[
                d.component_id
            ], d.component_id

    def test_hero_search_directory_scoped_to_home_only(self):
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "hero.search.directory")
        assert set(d.supported_page_roles) == {PageRole.HOME}

    def test_hero_local_standard_scoped_correctly(self):
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "hero.local.standard")
        assert set(d.supported_page_roles) == {
            PageRole.CATEGORY, PageRole.CITY,
            PageRole.CITY_CATEGORY, PageRole.SERVICE_AREA,
        }

    def test_filters_sort_summary_exclude_city(self):
        # §27.4 "cat, cc, sr" (no city) for filters/sort/results-summary,
        # unlike status.results.zero's "cat, city, cc, sr".
        for cid in (
            "directory.filters.panel", "directory.sort.control",
            "directory.results.summary",
        ):
            d = next(x for x in WAVE3_COMPONENTS if x.component_id == cid)
            assert PageRole.CITY not in d.supported_page_roles, cid

    def test_zero_state_includes_city(self):
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "status.results.zero")
        assert PageRole.CITY in d.supported_page_roles

    def test_no_duplicate_ids_or_versions(self):
        keys = [(d.component_id, d.component_version) for d in WAVE3_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_no_duplicate_ids_or_versions_across_full_catalog(self):
        keys = [(d.component_id, d.component_version) for d in REGISTERED_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_lexicographic_tuple_order(self):
        ids = [d.component_id for d in REGISTERED_COMPONENTS]
        assert ids == sorted(ids)  # §15.2 ordering law

    def test_no_placeholder_values(self):
        text = canonical_json(
            [model_to_dict(d) for d in WAVE3_COMPONENTS]
        ).lower()
        for marker in ("todo", "tbd", "lorem", "dummy", "fixme", "xxx"):
            assert marker not in text, marker


class TestDefinitionValidity:
    def test_every_definition_passes_validate_definition(self):
        for d in WAVE3_COMPONENTS:
            validate_definition(d)

    def test_every_default_variant_exists(self):
        for d in WAVE3_COMPONENTS:
            if d.supported_variants:
                assert d.default_variant in d.supported_variants, d.component_id
            else:
                assert d.default_variant == "", d.component_id

    def test_lifecycle_is_proposed_until_emitters_exist(self):
        for d in WAVE3_COMPONENTS:
            assert d.lifecycle_status is LifecycleStatus.PROPOSED

    def test_required_contract_fields_present(self):
        expected_prefix = {
            "hero.search.directory": "ac-hero",
            "hero.local.standard": "ac-hero",
            "directory.search.primary": "ac-directory",
            "directory.categories.grid": "ac-directory",
            "directory.locations.grid": "ac-directory",
            "directory.filters.panel": "ac-directory",
            "directory.sort.control": "ac-directory",
            "directory.results.summary": "ac-directory",
            "status.results.zero": "ac-status",
        }
        for d in WAVE3_COMPONENTS:
            assert d.analytics_contract.impression_id == d.component_id.replace(".", "-")
            assert d.rendering_contract.emitter_key == d.component_id + "@1"
            assert d.rendering_contract.class_prefix == expected_prefix[d.component_id]
            assert d.description and d.display_name
            assert d.design_token_dependencies, d.component_id
            assert d.example_fixture_ids

    def test_fixture_ids_follow_grammar(self):
        for d in WAVE3_COMPONENTS:
            expected_suffixes = {
                "min", "full", "bad-prop", "bad-slot", "mobile", "long", "a11y",
            }
            suffixes = {
                fid.replace("fx-%s-" % d.component_id, "")
                for fid in d.example_fixture_ids
            }
            assert suffixes == expected_suffixes, d.component_id

    def test_hero_search_directory_owns_h1(self):
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "hero.search.directory")
        assert d.seo_contract.heading_levels == (1,)
        assert "h1" in d.required_content_slots
        assert "subhead" in d.required_content_slots

    def test_hero_search_directory_nests_search_primary(self):
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "hero.search.directory")
        assert "directory.search.primary" in d.allowed_child_components

    def test_hero_local_standard_owns_h1_and_context_role(self):
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "hero.local.standard")
        assert d.seo_contract.heading_levels == (1,)
        assert "context_role" in d.required_props
        assert d.required_props["context_role"].prop_type is PropType.STR_ENUM
        assert set(d.required_props["context_role"].enum_values) == {
            "category", "city", "city-category", "service-area",
        }

    def test_search_primary_is_a_real_form(self):
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "directory.search.primary")
        assert d.semantic_element is SemanticElement.FORM
        assert d.required_props["action_route"].prop_type is PropType.ROUTE_REF
        assert d.required_props["input_label"].prop_type is PropType.A11Y_LABEL

    def test_categories_and_locations_grid_have_distinct_signatures(self):
        # AES-REVIEW-style hardening: these two components must not share
        # prop/slot names, or the selection pipeline cannot disambiguate
        # them for two sibling recipe slots (§14.2 step 1).
        categories = next(
            x for x in WAVE3_COMPONENTS if x.component_id == "directory.categories.grid"
        )
        locations = next(
            x for x in WAVE3_COMPONENTS if x.component_id == "directory.locations.grid"
        )
        assert set(categories.required_props) & set(locations.required_props) == set()
        assert (
            set(categories.required_content_slots)
            & set(locations.required_content_slots)
            == set()
        )

    def test_filters_and_sort_have_distinct_prop_signatures(self):
        filters = next(
            x for x in WAVE3_COMPONENTS if x.component_id == "directory.filters.panel"
        )
        sort = next(x for x in WAVE3_COMPONENTS if x.component_id == "directory.sort.control")
        assert set(filters.required_props) & set(sort.required_props) == set()

    def test_filters_panel_declares_drawer_state_machine(self):
        # §12.6 / §27.4 note "drawer SM".
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "directory.filters.panel")
        assert d.accessibility_contract.state_machine == "drawer"
        assert d.accessibility_contract.focus_management is True

    def test_zero_state_requires_message_and_recovery_links(self):
        d = next(x for x in WAVE3_COMPONENTS if x.component_id == "status.results.zero")
        assert "message" in d.required_content_slots
        assert "recovery_links" in d.required_content_slots
        from engines.website_generation.contracts.enums import SlotCardinality
        assert (
            d.required_content_slots["recovery_links"].cardinality
            is SlotCardinality.ONE_TO_N
        )

    def test_no_monetization_contract_in_wave3(self):
        for d in WAVE3_COMPONENTS:
            assert d.monetization_contract is None

    def test_no_free_form_string_props(self):
        for d in WAVE3_COMPONENTS:
            for props in (d.required_props, d.optional_props):
                for name, spec in props.items():
                    assert isinstance(spec.prop_type, PropType), (d.component_id, name)

    def test_definitions_are_frozen_and_reject_extras(self):
        for d in WAVE3_COMPONENTS:
            with pytest.raises(Exception):
                d.component_id = "x.y.z"
            assert d.component_id != "x.y.z"


class TestDeterminism:
    def test_identical_catalog_identical_hash(self):
        assert (
            ComponentRegistry(WAVE3_COMPONENTS).registry_hash()
            == ComponentRegistry(WAVE3_COMPONENTS).registry_hash()
        )

    def test_registration_order_does_not_alter_hash(self):
        forward = ComponentRegistry(WAVE3_COMPONENTS).registry_hash()
        backward = ComponentRegistry(tuple(reversed(WAVE3_COMPONENTS))).registry_hash()
        assert forward == backward

    def test_full_catalog_hash_reproduces_across_process_restarts(self):
        code = (
            "from engines.website_generation.components import "
            "build_default_registry; print(build_default_registry().registry_hash())"
        )
        runs = {
            subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(APP_ROOT), capture_output=True, text=True, check=True,
            ).stdout.strip()
            for _ in range(2)
        }
        assert len(runs) == 1
        assert runs == {build_default_registry().registry_hash()}

    def test_definition_fingerprints_stable_and_unique(self):
        prints = [definition_fingerprint(d) for d in WAVE3_COMPONENTS]
        assert prints == [definition_fingerprint(d) for d in WAVE3_COMPONENTS]
        assert len(set(prints)) == 9

    def test_earlier_waves_fingerprints_unchanged_by_wave3_addition(self):
        from engines.website_generation.components.catalog.layout_atoms import (
            WAVE1_COMPONENTS,
        )
        from engines.website_generation.components.catalog.navigation import (
            WAVE2_COMPONENTS,
        )
        earlier = {
            d.component_id: definition_fingerprint(d)
            for d in WAVE1_COMPONENTS + WAVE2_COMPONENTS
        }
        r = build_default_registry()
        for component_id, expected_fp in earlier.items():
            got = r.get(component_id)
            assert definition_fingerprint(got) == expected_fp, component_id


class TestCompatibilityMetadata:
    def test_compatibility_axes_pinned(self):
        for d in WAVE3_COMPONENTS:
            assert set(d.compatibility_range) == {
                "renderer", "token_schema", "registry_schema",
            }, d.component_id

    def test_gate_requirements_match_authority_table(self):
        expected = {
            "hero.search.directory": ("CG-CMP-005",),
            "hero.local.standard": ("CG-SEO-007",),
            "directory.search.primary": ("CG-A11Y-001",),
            "directory.categories.grid": ("CG-SEO-003", "CG-SEO-004"),
            "directory.locations.grid": ("CG-SEO-004",),
            "directory.filters.panel": ("CG-A11Y-002", "CG-SEO-006"),
            "directory.sort.control": ("CG-SEO-003",),
            "directory.results.summary": (),
            "status.results.zero": ("CG-STR-006",),
        }
        for d in WAVE3_COMPONENTS:
            assert d.quality_gate_requirements == expected[d.component_id], (
                d.component_id
            )

    def test_page_roles_and_region_kinds_typed(self):
        for d in WAVE3_COMPONENTS:
            assert all(isinstance(r, PageRole) for r in d.supported_page_roles)
            assert all(isinstance(r, RegionKind) for r in d.allowed_parent_regions)


class TestRegistryLookups:
    def test_every_wave3_component_resolvable(self):
        r = build_default_registry()
        for d in WAVE3_COMPONENTS:
            got = r.get(d.component_id, "1.0.0")
            assert got.component_id == d.component_id

    def test_by_family_returns_wave3_sets(self):
        r = build_default_registry()
        assert len(r.by_family(ComponentFamily.HERO)) == 2
        # directory family = 6 Wave 3 + 0 elsewhere.
        assert len(r.by_family(ComponentFamily.DIRECTORY)) == 6

    def test_candidates_for_home_includes_wave3_components(self):
        r = build_default_registry()
        home_ids = {d.component_id for d in r.candidates_for(PageRole.HOME)}
        for cid in (
            "hero.search.directory", "directory.search.primary",
            "directory.categories.grid", "directory.locations.grid",
        ):
            assert cid in home_ids, cid
        assert "hero.local.standard" not in home_ids
        assert "directory.filters.panel" not in home_ids

    def test_candidates_for_category_includes_local_hero_and_filters(self):
        r = build_default_registry()
        category_ids = {d.component_id for d in r.candidates_for(PageRole.CATEGORY)}
        for cid in (
            "hero.local.standard", "directory.filters.panel",
            "directory.sort.control", "directory.results.summary",
            "status.results.zero",
        ):
            assert cid in category_ids, cid
        assert "hero.search.directory" not in category_ids

    def test_variant_resolution(self):
        r = build_default_registry()
        assert r.resolve_variant(
            "hero.search.directory", "split"
        ).display_name == "Split"
