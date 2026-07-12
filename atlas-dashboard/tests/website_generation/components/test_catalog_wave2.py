"""Wave 2 catalog tests (AES-WEB-002C; AES-WEB-002 §27.3, §15.2, §30.1).

Catalog completeness (exact IDs, versions, families, roles, variants,
count), definition validity, determinism (hash stability across order and
process restarts), compatibility metadata, registry lookups, and
architecture boundaries (no placeholders, landmark-uniqueness discipline,
no selection/rendering smuggled into catalog data).
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
    SemanticElement,
)
from engines.website_generation.components.catalog.navigation import (
    WAVE2_COMPONENTS,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)

APP_ROOT = Path(__file__).resolve().parents[3]

# The exact §27.3 Wave 2 inventory (lexicographic — §15.2 ordering law).
EXPECTED_IDS = [
    "legal.footer.directory",
    "nav.breadcrumbs.standard",
    "nav.header.standard",
    "nav.mobile.drawer",
    "nav.pagination.standard",
    "nav.skip.link",
    "nav.utility.bar",
    "status.banner.notification",
]

# Exact §27.3 variant declarations (empty tuple = "—" in the table).
EXPECTED_VARIANTS = {
    "nav.header.standard": ("condensed", "standard"),
    "nav.utility.bar": ("announce", "disclosure"),
    "legal.footer.directory": ("minimal", "standard"),
}

# §27.3 "Roles" column, mapped to PageRole membership.
EXPECTED_ROLE_COUNTS = {
    "nav.skip.link": 18,  # ALL
    "nav.header.standard": 18,  # ALL
    "nav.mobile.drawer": 18,  # ALL
    "nav.breadcrumbs.standard": 16,  # all except home, lead-gen-landing
    "nav.utility.bar": 3,  # home, cat, city
    "nav.pagination.standard": 4,  # cat, city, cc, sr
    "legal.footer.directory": 18,  # ALL
    "status.banner.notification": 18,  # ALL
}


class TestCatalogCompleteness:
    def test_exact_component_ids(self):
        assert [d.component_id for d in WAVE2_COMPONENTS] == EXPECTED_IDS

    def test_exact_catalog_count(self):
        assert len(WAVE2_COMPONENTS) == 8  # §27.3 "Navigation and shell (8)"
        # Wave 1 (15) + Wave 2 (8) + Wave 3 (9) + Wave 4 (12) + Wave 5 (13)
        # + Wave 6 (7) = 64; the exact Wave 3 / Wave 4 / Wave 5 / Wave 6
        # inventory is asserted in their own test_catalog_wave3.py /
        # test_catalog_wave4.py / test_catalog_wave5.py / test_catalog_wave6.py.
        assert len(REGISTERED_COMPONENTS) == 64

    def test_exact_versions(self):
        assert all(d.component_version == "1.0.0" for d in WAVE2_COMPONENTS)

    def test_exact_family_assignments(self):
        expected_family = {
            "legal.footer.directory": ComponentFamily.LEGAL,
            "nav.breadcrumbs.standard": ComponentFamily.NAV,
            "nav.header.standard": ComponentFamily.NAV,
            "nav.mobile.drawer": ComponentFamily.NAV,
            "nav.pagination.standard": ComponentFamily.NAV,
            "nav.skip.link": ComponentFamily.NAV,
            "nav.utility.bar": ComponentFamily.NAV,
            "status.banner.notification": ComponentFamily.STATUS,
        }
        for d in WAVE2_COMPONENTS:
            assert d.component_family is expected_family[d.component_id], (
                d.component_id
            )

    def test_family_counts(self):
        nav = [d for d in WAVE2_COMPONENTS if d.component_family is ComponentFamily.NAV]
        legal = [d for d in WAVE2_COMPONENTS if d.component_family is ComponentFamily.LEGAL]
        status = [d for d in WAVE2_COMPONENTS if d.component_family is ComponentFamily.STATUS]
        assert len(nav) == 6 and len(legal) == 1 and len(status) == 1

    def test_exact_variant_names(self):
        for d in WAVE2_COMPONENTS:
            expected = EXPECTED_VARIANTS.get(d.component_id, ())
            assert tuple(sorted(d.supported_variants)) == expected, d.component_id

    def test_exact_role_counts_match_authority_table(self):
        for d in WAVE2_COMPONENTS:
            assert len(d.supported_page_roles) == EXPECTED_ROLE_COUNTS[
                d.component_id
            ], d.component_id

    def test_breadcrumbs_excludes_home_and_lead_gen(self):
        d = next(x for x in WAVE2_COMPONENTS if x.component_id == "nav.breadcrumbs.standard")
        assert PageRole.HOME not in d.supported_page_roles
        assert PageRole.LEAD_GEN_LANDING not in d.supported_page_roles
        assert PageRole.CATEGORY in d.supported_page_roles

    def test_utility_bar_scoped_to_home_cat_city(self):
        d = next(x for x in WAVE2_COMPONENTS if x.component_id == "nav.utility.bar")
        assert set(d.supported_page_roles) == {
            PageRole.HOME, PageRole.CATEGORY, PageRole.CITY,
        }

    def test_pagination_scoped_to_inventory_roles(self):
        d = next(x for x in WAVE2_COMPONENTS if x.component_id == "nav.pagination.standard")
        assert set(d.supported_page_roles) == {
            PageRole.CATEGORY, PageRole.CITY,
            PageRole.CITY_CATEGORY, PageRole.SEARCH_RESULTS,
        }

    def test_no_duplicate_ids_or_versions(self):
        keys = [(d.component_id, d.component_version) for d in WAVE2_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_no_duplicate_ids_or_versions_across_full_catalog(self):
        keys = [(d.component_id, d.component_version) for d in REGISTERED_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_lexicographic_tuple_order(self):
        ids = [d.component_id for d in REGISTERED_COMPONENTS]
        assert ids == sorted(ids)  # §15.2 ordering law

    def test_no_placeholder_values(self):
        text = canonical_json(
            [model_to_dict(d) for d in WAVE2_COMPONENTS]
        ).lower()
        for marker in ("todo", "tbd", "lorem", "dummy", "fixme", "xxx"):
            assert marker not in text, marker


class TestDefinitionValidity:
    def test_every_definition_passes_validate_definition(self):
        for d in WAVE2_COMPONENTS:
            validate_definition(d)  # raises on any violation

    def test_every_default_variant_exists(self):
        for d in WAVE2_COMPONENTS:
            if d.supported_variants:
                assert d.default_variant in d.supported_variants, d.component_id
            else:
                assert d.default_variant == "", d.component_id

    def test_lifecycle_is_proposed_until_emitters_exist(self):
        # §23: ACTIVE requires a complete emitter + full fixtures; the
        # emitter portion of 002C is a separate delivery, so Wave 2 honestly
        # registers as PROPOSED (never report unbuilt work as complete).
        for d in WAVE2_COMPONENTS:
            assert d.lifecycle_status is LifecycleStatus.PROPOSED

    def test_required_contract_fields_present(self):
        expected_prefix = {
            "legal.footer.directory": "ac-legal",
            "status.banner.notification": "ac-status",
        }
        for d in WAVE2_COMPONENTS:
            assert d.analytics_contract.impression_id == d.component_id.replace(".", "-")
            assert d.rendering_contract.emitter_key == d.component_id + "@1"
            assert d.rendering_contract.class_prefix == expected_prefix.get(
                d.component_id, "ac-nav"
            )
            assert d.description and d.display_name
            assert d.design_token_dependencies, d.component_id
            assert d.example_fixture_ids  # §30.2 minimum set declared

    def test_fixture_ids_follow_grammar(self):
        for d in WAVE2_COMPONENTS:
            expected_suffixes = {
                "min", "full", "bad-prop", "bad-slot", "mobile", "long", "a11y",
            }
            suffixes = {
                fid.replace("fx-%s-" % d.component_id, "")
                for fid in d.example_fixture_ids
            }
            assert suffixes == expected_suffixes, d.component_id

    def test_drawer_and_pagination_declare_state_machines(self):
        # §12.6: registry-declared, test-enforced interactive state machines.
        drawer = next(x for x in WAVE2_COMPONENTS if x.component_id == "nav.mobile.drawer")
        assert drawer.accessibility_contract.state_machine == "drawer"
        assert drawer.accessibility_contract.focus_management is True
        pagination = next(
            x for x in WAVE2_COMPONENTS if x.component_id == "nav.pagination.standard"
        )
        assert pagination.accessibility_contract.state_machine == "pagination"

    def test_skip_link_is_first_focusable_and_accessible(self):
        d = next(x for x in WAVE2_COMPONENTS if x.component_id == "nav.skip.link")
        assert d.allowed_parent_regions == (RegionKind.SKIP,)
        assert d.accessibility_contract.keyboard_operable is True
        assert d.accessibility_contract.focus_management is True

    def test_breadcrumbs_declare_breadcrumb_list_schema(self):
        # §13.2: BreadcrumbList is a supported MVP structured-data type.
        d = next(x for x in WAVE2_COMPONENTS if x.component_id == "nav.breadcrumbs.standard")
        assert "BreadcrumbList" in d.seo_contract.schema_fragments

    def test_footer_and_header_do_not_redeclare_landmarks(self):
        # §12.1: exactly one page header/footer landmark, owned by
        # layout.shell.page (Wave 1) — Wave 2 must not re-declare either.
        header = next(x for x in WAVE2_COMPONENTS if x.component_id == "nav.header.standard")
        footer = next(x for x in WAVE2_COMPONENTS if x.component_id == "legal.footer.directory")
        assert header.semantic_element is not SemanticElement.HEADER
        assert footer.semantic_element is not SemanticElement.FOOTER

    def test_nav_landmark_components_use_nav_semantic_element(self):
        # §5.1 SEO rule ("aria-label disambiguation required when >1 <nav>")
        # implies these four components each contribute a <nav> landmark.
        for cid in (
            "nav.header.standard", "nav.mobile.drawer",
            "nav.breadcrumbs.standard", "nav.pagination.standard",
        ):
            d = next(x for x in WAVE2_COMPONENTS if x.component_id == cid)
            assert d.semantic_element is SemanticElement.NAV, cid

    def test_definitions_are_frozen_and_reject_extras(self):
        # AES-REVIEW hardening: the previous try/except form swallowed its
        # own AssertionError, passing even if mutation silently succeeded.
        # pytest.raises' failure signal is a BaseException subclass, so it
        # cannot be swallowed the same way.
        for d in WAVE2_COMPONENTS:
            with pytest.raises(Exception):
                d.component_id = "x.y.z"
            assert d.component_id != "x.y.z"


class TestDeterminism:
    def test_identical_catalog_identical_hash(self):
        assert (
            ComponentRegistry(WAVE2_COMPONENTS).registry_hash()
            == ComponentRegistry(WAVE2_COMPONENTS).registry_hash()
        )

    def test_registration_order_does_not_alter_hash(self):
        forward = ComponentRegistry(WAVE2_COMPONENTS).registry_hash()
        backward = ComponentRegistry(tuple(reversed(WAVE2_COMPONENTS))).registry_hash()
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
        prints = [definition_fingerprint(d) for d in WAVE2_COMPONENTS]
        assert prints == [definition_fingerprint(d) for d in WAVE2_COMPONENTS]
        assert len(set(prints)) == 8

    def test_wave1_fingerprints_unchanged_by_wave2_addition(self):
        # Adding Wave 2 must not silently modify any released Wave 1
        # component's identity.
        from engines.website_generation.components.catalog.layout_atoms import (
            WAVE1_COMPONENTS,
        )
        wave1_only = {
            d.component_id: definition_fingerprint(d) for d in WAVE1_COMPONENTS
        }
        r = build_default_registry()
        for component_id, expected_fp in wave1_only.items():
            got = r.get(component_id)
            assert definition_fingerprint(got) == expected_fp, component_id

    def test_inventory_immutable_and_instances_isolated(self):
        r1 = build_default_registry()
        r2 = build_default_registry()
        assert r1 is not r2
        assert isinstance(r1.inventory(), tuple)
        assert r1.registry_hash() == r2.registry_hash()


class TestCompatibilityMetadata:
    def test_page_roles_and_region_kinds_typed(self):
        for d in WAVE2_COMPONENTS:
            assert all(isinstance(r, PageRole) for r in d.supported_page_roles)
            assert all(isinstance(r, RegionKind) for r in d.allowed_parent_regions)
            assert all(isinstance(a, AssetRole) for a in d.supported_asset_roles)

    def test_header_declares_logo_asset_role(self):
        # §27.3 header row requires a logo asset; the definition must
        # declare the LOGO asset role it consumes (Wave 1 precedent:
        # every ASSET_REF-consuming component declares its roles).
        d = next(x for x in WAVE2_COMPONENTS if x.component_id == "nav.header.standard")
        assert d.supported_asset_roles == (AssetRole.LOGO,)
        assert d.required_props["logo"].prop_type is PropType.ASSET_REF

    def test_footer_link_ceiling_constant_declared(self):
        # §5.15: "footer SEO links capped at constants ceiling, default 40"
        # — the number must live in constants, not prose.
        from engines.website_generation.constants.components import (
            FOOTER_SEO_LINK_CEILING,
        )
        assert FOOTER_SEO_LINK_CEILING == 40
        assert isinstance(FOOTER_SEO_LINK_CEILING, int)

    def test_compatibility_axes_pinned(self):
        for d in WAVE2_COMPONENTS:
            assert set(d.compatibility_range) == {
                "renderer", "token_schema", "registry_schema",
            }, d.component_id

    def test_gate_requirements_match_authority_table(self):
        # §27.3 "Major gates" column, verbatim.
        expected = {
            "nav.skip.link": ("CG-A11Y-011",),
            "nav.header.standard": ("CG-CMP-006",),
            "nav.mobile.drawer": ("CG-A11Y-002", "CG-A11Y-009", "CG-RND-006"),
            "nav.breadcrumbs.standard": ("CG-SEO-009",),
            "nav.utility.bar": (),
            "nav.pagination.standard": ("CG-SEO-009",),
            "legal.footer.directory": ("CG-CMP-006",),
            "status.banner.notification": ("CG-A11Y-008",),
        }
        for d in WAVE2_COMPONENTS:
            assert d.quality_gate_requirements == expected[d.component_id], (
                d.component_id
            )

    def test_no_monetization_contract_in_wave2(self):
        # No monetization family component in Wave 2 (§5.10 is a later wave).
        for d in WAVE2_COMPONENTS:
            assert d.monetization_contract is None

    def test_footer_requires_disclosures_and_legal_facts(self):
        d = next(x for x in WAVE2_COMPONENTS if x.component_id == "legal.footer.directory")
        assert "legal_facts" in d.required_content_slots
        assert "disclosures" in d.required_content_slots

    def test_status_banner_severity_enum_matches_wave1_alert(self):
        # Consistency with atom.alert.notice's established severity
        # vocabulary (§5.14 doesn't enumerate values; reusing Wave 1's).
        d = next(x for x in WAVE2_COMPONENTS if x.component_id == "status.banner.notification")
        assert d.required_props["severity"].enum_values == (
            "info", "success", "warning", "error",
        )

    def test_no_free_form_string_props(self):
        for d in WAVE2_COMPONENTS:
            for props in (d.required_props, d.optional_props):
                for name, spec in props.items():
                    assert isinstance(spec.prop_type, PropType), (d.component_id, name)


class TestRegistryLookups:
    def test_every_wave2_component_resolvable(self):
        r = build_default_registry()
        for d in WAVE2_COMPONENTS:
            got = r.get(d.component_id, "1.0.0")
            assert got.component_id == d.component_id

    def test_by_family_returns_wave2_sets(self):
        r = build_default_registry()
        assert len(r.by_family(ComponentFamily.NAV)) == 6
        assert len(r.by_family(ComponentFamily.LEGAL)) == 1
        # STATUS now holds Wave 2's status.banner.notification plus Wave 3's
        # status.results.zero (§27.4) = 2.
        assert len(r.by_family(ComponentFamily.STATUS)) == 2

    def test_candidates_for_home_includes_wave2_universal_components(self):
        r = build_default_registry()
        home_ids = {d.component_id for d in r.candidates_for(PageRole.HOME)}
        for cid in (
            "nav.skip.link", "nav.header.standard", "nav.mobile.drawer",
            "legal.footer.directory", "status.banner.notification",
            "nav.utility.bar",
        ):
            assert cid in home_ids, cid
        # home excludes breadcrumbs and pagination.
        assert "nav.breadcrumbs.standard" not in home_ids
        assert "nav.pagination.standard" not in home_ids

    def test_candidates_for_category_includes_pagination_and_breadcrumbs(self):
        r = build_default_registry()
        category_ids = {d.component_id for d in r.candidates_for(PageRole.CATEGORY)}
        assert "nav.pagination.standard" in category_ids
        assert "nav.breadcrumbs.standard" in category_ids

    def test_full_catalog_candidates_for_home_count(self):
        # 12 Wave-1 HOME candidates + 6 Wave-2 HOME candidates (all but
        # breadcrumbs and pagination) + 4 Wave-3 HOME candidates
        # (hero.search.directory, directory.search.primary,
        # directory.categories.grid, directory.locations.grid) + 2 Wave-4
        # HOME candidates (listing.card.standard, listing.card.featured —
        # §27.5 "home, cat, city") + 5 Wave-5 HOME candidates
        # (cta.claim.listing, cta.submit.listing, form.capture.newsletter,
        # trust.reviews.summary, trust.statistics.strip — §27.6) + 2 Wave-6
        # HOME candidates (content.resources.grid, seo.local-links.cities —
        # §27.7) = 31.
        r = build_default_registry()
        assert len(r.candidates_for(PageRole.HOME)) == 31

    def test_variant_resolution(self):
        r = build_default_registry()
        assert r.resolve_variant(
            "nav.header.standard", "condensed"
        ).display_name == "Condensed (lg)"
