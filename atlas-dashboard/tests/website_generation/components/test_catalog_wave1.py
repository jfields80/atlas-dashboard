"""Wave 1 catalog tests (AES-WEB-002B; AES-WEB-002 §27.2, §15.2, §30.1).

Catalog completeness (exact IDs, versions, families, variants, count),
definition validity, determinism (hash stability across order and process
restarts), compatibility metadata, and architecture boundaries (no
placeholders, no selection/rendering smuggled into catalog data).
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
    AssetRole,
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
    RegionKind,
)
from engines.website_generation.components.catalog.layout_atoms import (
    WAVE1_COMPONENTS,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)

APP_ROOT = Path(__file__).resolve().parents[3]

# The exact §27.2 Wave 1 inventory.
EXPECTED_IDS = [
    "atom.alert.notice",
    "atom.badge.status",
    "atom.button.action",
    "atom.field.choice",
    "atom.field.select",
    "atom.field.text",
    "atom.icon.standard",
    "atom.image.responsive",
    "atom.link.standard",
    "layout.card.shell",
    "layout.grid.standard",
    "layout.section.container",
    "layout.shell.page",
    "layout.split.standard",
    "layout.stack.standard",
]

# Exact §27.2 variant declarations (empty tuple = "—" in the table).
EXPECTED_VARIANTS = {
    "layout.section.container": ("band", "standard"),
    "layout.split.standard": ("media-left", "media-right"),
    "layout.card.shell": ("flat", "raised"),
    "atom.link.standard": ("inline", "standalone"),
}


class TestCatalogCompleteness:
    def test_exact_component_ids(self):
        assert [d.component_id for d in WAVE1_COMPONENTS] == EXPECTED_IDS

    def test_exact_catalog_count(self):
        assert len(WAVE1_COMPONENTS) == 15  # §27.2 "Foundation primitives (15)"
        # REGISTERED_COMPONENTS now spans every registered wave (AES-WEB-002C
        # appended Wave 2); Wave 1 must remain a subset. The exact full-
        # catalog count is asserted in test_catalog_wave2.py, next to the
        # wave that most recently changed it.
        assert set(d.component_id for d in WAVE1_COMPONENTS) <= set(
            d.component_id for d in REGISTERED_COMPONENTS
        )

    def test_exact_versions(self):
        assert all(d.component_version == "1.0.0" for d in WAVE1_COMPONENTS)

    def test_exact_family_assignments(self):
        for d in WAVE1_COMPONENTS:
            expected = (
                ComponentFamily.LAYOUT
                if d.component_id.startswith("layout.")
                else ComponentFamily.ATOM
            )
            assert d.component_family is expected, d.component_id
        families = {d.component_family for d in WAVE1_COMPONENTS}
        assert families == {ComponentFamily.LAYOUT, ComponentFamily.ATOM}

    def test_family_counts(self):
        layout = [d for d in WAVE1_COMPONENTS if d.component_family is ComponentFamily.LAYOUT]
        atoms = [d for d in WAVE1_COMPONENTS if d.component_family is ComponentFamily.ATOM]
        assert len(layout) == 6 and len(atoms) == 9

    def test_exact_variant_names(self):
        for d in WAVE1_COMPONENTS:
            expected = EXPECTED_VARIANTS.get(d.component_id, ())
            assert tuple(sorted(d.supported_variants)) == expected, d.component_id

    def test_no_duplicate_ids_or_versions(self):
        keys = [(d.component_id, d.component_version) for d in WAVE1_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_lexicographic_tuple_order(self):
        ids = [d.component_id for d in REGISTERED_COMPONENTS]
        assert ids == sorted(ids)  # §15.2 ordering law

    def test_no_placeholder_values(self):
        text = canonical_json(
            [model_to_dict(d) for d in WAVE1_COMPONENTS]
        ).lower()
        for marker in ("todo", "tbd", "lorem", "dummy", "fixme", "xxx"):
            assert marker not in text, marker


class TestDefinitionValidity:
    def test_every_definition_passes_validate_definition(self):
        for d in WAVE1_COMPONENTS:
            validate_definition(d)  # raises on any violation

    def test_every_default_variant_exists(self):
        for d in WAVE1_COMPONENTS:
            if d.supported_variants:
                assert d.default_variant in d.supported_variants, d.component_id
            else:
                assert d.default_variant == "", d.component_id

    def test_lifecycle_is_proposed_until_emitters_exist(self):
        # §23: ACTIVE requires a complete emitter + full fixtures; the
        # emitter portion of 002B is a separate delivery, so Wave 1 honestly
        # registers as PROPOSED (never report unbuilt work as complete).
        for d in WAVE1_COMPONENTS:
            assert d.lifecycle_status is LifecycleStatus.PROPOSED

    def test_required_contract_fields_present(self):
        for d in WAVE1_COMPONENTS:
            assert d.analytics_contract.impression_id == d.component_id.replace(".", "-")
            assert d.rendering_contract.emitter_key == d.component_id + "@1"
            assert d.rendering_contract.class_prefix in ("ac-layout", "ac-atom")
            assert d.description and d.display_name
            assert d.design_token_dependencies, d.component_id
            assert d.example_fixture_ids  # §30.2 minimum set declared

    def test_fixture_ids_follow_grammar(self):
        for d in WAVE1_COMPONENTS:
            expected_suffixes = {
                "min", "full", "bad-prop", "bad-slot", "mobile", "long", "a11y",
            }
            suffixes = {
                fid.replace("fx-%s-" % d.component_id, "")
                for fid in d.example_fixture_ids
            }
            assert suffixes == expected_suffixes, d.component_id

    def test_interactive_atoms_declare_focus_ring_dependency(self):
        # §12.2: focus.ring.default is mandatory for interactive components.
        for cid in (
            "atom.button.action", "atom.link.standard", "atom.field.text",
            "atom.field.select", "atom.field.choice",
        ):
            d = next(x for x in WAVE1_COMPONENTS if x.component_id == cid)
            assert "focus.ring.default" in d.design_token_dependencies, cid
            assert d.accessibility_contract.keyboard_operable, cid

    def test_form_atoms_scoped_to_form_roles(self):
        for cid in ("atom.field.text", "atom.field.select", "atom.field.choice"):
            d = next(x for x in WAVE1_COMPONENTS if x.component_id == cid)
            assert PageRole.LEAD_GEN_LANDING in d.supported_page_roles
            assert PageRole.HOME not in d.supported_page_roles

    def test_definitions_are_frozen_and_reject_extras(self):
        # AES-REVIEW hardening: the previous try/except form swallowed its
        # own AssertionError, passing even if mutation silently succeeded.
        # pytest.raises' failure signal is a BaseException subclass, so it
        # cannot be swallowed the same way.
        for d in WAVE1_COMPONENTS:
            with pytest.raises(Exception):
                d.component_id = "x.y.z"
            assert d.component_id != "x.y.z"


class TestDeterminism:
    def test_identical_catalog_identical_hash(self):
        assert (
            ComponentRegistry(WAVE1_COMPONENTS).registry_hash()
            == ComponentRegistry(WAVE1_COMPONENTS).registry_hash()
        )

    def test_registration_order_does_not_alter_hash(self):
        forward = ComponentRegistry(WAVE1_COMPONENTS).registry_hash()
        backward = ComponentRegistry(tuple(reversed(WAVE1_COMPONENTS))).registry_hash()
        assert forward == backward

    def test_hash_reproduces_across_process_restarts(self):
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
        prints = [definition_fingerprint(d) for d in WAVE1_COMPONENTS]
        assert prints == [definition_fingerprint(d) for d in WAVE1_COMPONENTS]
        assert len(set(prints)) == 15

    def test_inventory_immutable_and_instances_isolated(self):
        r1 = build_default_registry()
        r2 = build_default_registry()
        assert r1 is not r2
        assert isinstance(r1.inventory(), tuple)
        assert r1.registry_hash() == r2.registry_hash()


class TestCompatibilityMetadata:
    def test_page_roles_region_kinds_asset_roles_typed(self):
        for d in WAVE1_COMPONENTS:
            assert all(isinstance(r, PageRole) for r in d.supported_page_roles)
            assert all(isinstance(r, RegionKind) for r in d.allowed_parent_regions)
            assert all(isinstance(a, AssetRole) for a in d.supported_asset_roles)

    def test_compatibility_axes_pinned(self):
        for d in WAVE1_COMPONENTS:
            assert set(d.compatibility_range) == {
                "renderer", "token_schema", "registry_schema",
            }, d.component_id

    def test_image_and_icon_asset_roles(self):
        image = next(d for d in WAVE1_COMPONENTS if d.component_id == "atom.image.responsive")
        assert set(image.supported_asset_roles) == {
            AssetRole.HERO_IMAGE, AssetRole.GALLERY_IMAGE,
        }
        icon = next(d for d in WAVE1_COMPONENTS if d.component_id == "atom.icon.standard")
        assert icon.supported_asset_roles == (AssetRole.ICON,)

    def test_gate_requirements_match_authority_table(self):
        # §27.2 "Major gates" column, verbatim.
        expected = {
            "layout.shell.page": ("CG-CMP-005", "CG-CMP-006"),
            "layout.section.container": ("CG-CMP-005",),
            "layout.grid.standard": ("CG-RSP-002",),
            "layout.stack.standard": (),
            "layout.split.standard": ("CG-RSP-003",),
            "layout.card.shell": ("CG-CMP-004",),
            "atom.button.action": ("CG-A11Y-003", "CG-A11Y-005"),
            "atom.link.standard": ("CG-SEO-002", "CG-SEO-003"),
            "atom.image.responsive": ("CG-A11Y-010", "CG-RSP-005"),
            "atom.icon.standard": ("CG-A11Y-001",),
            "atom.badge.status": ("CG-COM-004",),
            "atom.alert.notice": ("CG-A11Y-008",),
            "atom.field.text": ("CG-A11Y-001", "CG-A11Y-012"),
            "atom.field.select": ("CG-A11Y-001",),
            "atom.field.choice": ("CG-COM-007",),
        }
        for d in WAVE1_COMPONENTS:
            assert d.quality_gate_requirements == expected[d.component_id], (
                d.component_id
            )

    def test_no_conversion_directory_monetization_contracts_in_wave1(self):
        # Foundation primitives carry no commercial contracts (§5.16).
        for d in WAVE1_COMPONENTS:
            assert d.conversion_contract is None
            assert d.directory_contract is None
            assert d.monetization_contract is None

    def test_no_free_form_string_props(self):
        for d in WAVE1_COMPONENTS:
            for props in (d.required_props, d.optional_props):
                for name, spec in props.items():
                    assert isinstance(spec.prop_type, PropType), (d.component_id, name)


class TestRegistryLookups:
    def test_every_wave1_component_resolvable(self):
        r = build_default_registry()
        for d in WAVE1_COMPONENTS:
            got = r.get(d.component_id, "1.0.0")
            assert got.component_id == d.component_id

    def test_by_family_returns_wave1_sets(self):
        r = build_default_registry()
        assert len(r.by_family(ComponentFamily.LAYOUT)) == 6
        assert len(r.by_family(ComponentFamily.ATOM)) == 9

    def test_candidates_for_home_excludes_form_atoms(self):
        # Scoped to a Wave-1-only registry (not build_default_registry(),
        # which now spans every registered wave) so this fact about Wave 1
        # stays true and isolated regardless of what later waves add.
        r = ComponentRegistry(WAVE1_COMPONENTS)
        home_ids = {d.component_id for d in r.candidates_for(PageRole.HOME)}
        assert "atom.field.text" not in home_ids
        assert "layout.shell.page" in home_ids
        assert len(home_ids) == 12  # 15 minus the three form-scoped atoms

    def test_variant_resolution(self):
        r = build_default_registry()
        assert r.resolve_variant("layout.card.shell", "flat").display_name == "Flat"
