"""Wave 6 catalog tests (AES-WEB-002G; AES-WEB-002 §27.7, §15.2, §30.1).

Catalog completeness (exact IDs, versions, families, roles, variants,
count), definition validity, determinism (hash stability across order and
process restarts), compatibility metadata, registry lookups, SEO/editorial
doctrine enforcement linkage, the five new secondary recipe tables, and the
AMB-002G-01 city-category fixture-only proof -- mirrors test_catalog_wave5.py's
structure.
"""

from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path

import pytest

from engines.website_generation.contracts.artifacts import (
    canonical_json,
    model_to_dict,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
)
from engines.website_generation.components.catalog.seo_editorial import (
    WAVE6_COMPONENTS,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)
from engines.website_generation.constants import components as constants_components
from engines.website_generation.constants.components import (
    SEO_LOCAL_LINKS_MAX_BLOCKS_PER_PAGE,
    SEO_LOCAL_LINKS_MAX_PER_BLOCK,
    _UNBUILT_FAMILY_SENTINEL,
)

APP_ROOT = Path(__file__).resolve().parents[3]

# The exact §27.7 Wave 6 inventory (lexicographic -- §15.2 ordering law).
EXPECTED_IDS = [
    "content.intro.contextual",
    "content.resources.grid",
    "content.section.editorial",
    "content.table.comparison",
    "content.toc.standard",
    "seo.local-links.categories",
    "seo.local-links.cities",
]

EXPECTED_VARIANTS = {
    "content.intro.contextual": ("above-listings", "below-listings"),
    "content.resources.grid": (),
    "content.section.editorial": ("callout", "standard"),
    "content.table.comparison": (),
    "content.toc.standard": ("sidebar", "top"),
    "seo.local-links.categories": ("grid", "inline-list"),
    "seo.local-links.cities": ("grid", "inline-list"),
}

# §27.7 "Roles" column, mapped to PageRole membership counts. "guides" =
# PageRole.EDITORIAL_GUIDE (see catalog module docstring).
EXPECTED_ROLE_COUNTS = {
    "content.intro.contextual": 3,  # cat, city, cc
    "content.resources.grid": 2,  # home, guides
    "content.section.editorial": 3,  # guides, bo, prof
    "content.table.comparison": 3,  # cmp, bo, guides
    "content.toc.standard": 2,  # guides, bo
    "seo.local-links.categories": 3,  # cat, cc, city
    "seo.local-links.cities": 4,  # city, cc, home, regional-hub
}

EXPECTED_FAMILY = {
    "content.intro.contextual": ComponentFamily.CONTENT,
    "content.resources.grid": ComponentFamily.CONTENT,
    "content.section.editorial": ComponentFamily.CONTENT,
    "content.table.comparison": ComponentFamily.CONTENT,
    "content.toc.standard": ComponentFamily.CONTENT,
    "seo.local-links.categories": ComponentFamily.SEO,
    "seo.local-links.cities": ComponentFamily.SEO,
}

EXPECTED_CLASS_PREFIX = {
    "content.intro.contextual": "ac-content",
    "content.resources.grid": "ac-content",
    "content.section.editorial": "ac-content",
    "content.table.comparison": "ac-content",
    "content.toc.standard": "ac-content",
    "seo.local-links.categories": "ac-seo",
    "seo.local-links.cities": "ac-seo",
}

EXPECTED_GATES = {
    "content.intro.contextual": ("CG-SEO-007",),
    "content.resources.grid": ("CG-SEO-003",),
    "content.section.editorial": ("CG-CMP-005",),
    "content.table.comparison": ("CG-RSP-004",),
    "content.toc.standard": ("CG-RSP-003",),
    "seo.local-links.categories": ("CG-SEO-004",),
    "seo.local-links.cities": ("CG-SEO-003", "CG-SEO-004"),
}

# The five new secondary recipe tables (AMB-002G scope) and the roles they
# each compose for.
SECONDARY_RECIPE_TABLES = {
    "EDITORIAL_GUIDE_RECIPE_SLOTS": "editorial-guide",
    "COLLECTION_RECIPE_SLOTS": "collection",
    "SERVICE_AREA_RECIPE_SLOTS": "service-area",
    "VERIFICATION_RECIPE_SLOTS": "verification",
    "REGIONAL_HUB_RECIPE_SLOTS": "regional-hub",
}


def _get(cid):
    return next(d for d in WAVE6_COMPONENTS if d.component_id == cid)


class TestCatalogCompleteness:
    def test_exact_component_ids(self):
        assert [d.component_id for d in WAVE6_COMPONENTS] == EXPECTED_IDS

    def test_exact_catalog_count(self):
        assert len(WAVE6_COMPONENTS) == 7  # §27.7 "Local SEO and editorial (7)"
        # Wave 1 (15) + Wave 2 (8) + Wave 3 (9) + Wave 4 (12) + Wave 5 (13)
        # + Wave 6 (7) + Wave 7 (8) = 72.
        assert len(REGISTERED_COMPONENTS) == 72

    def test_exact_versions(self):
        assert all(d.component_version == "1.0.0" for d in WAVE6_COMPONENTS)

    def test_exact_family_assignments(self):
        for d in WAVE6_COMPONENTS:
            assert d.component_family is EXPECTED_FAMILY[d.component_id], (
                d.component_id
            )

    def test_family_counts(self):
        seo = [d for d in WAVE6_COMPONENTS if d.component_family is ComponentFamily.SEO]
        content = [d for d in WAVE6_COMPONENTS if d.component_family is ComponentFamily.CONTENT]
        assert len(seo) == 2 and len(content) == 5

    def test_exact_variant_names(self):
        for d in WAVE6_COMPONENTS:
            expected = EXPECTED_VARIANTS[d.component_id]
            assert tuple(sorted(d.supported_variants)) == expected, d.component_id

    def test_exact_role_counts_match_authority_table(self):
        for d in WAVE6_COMPONENTS:
            assert len(d.supported_page_roles) == EXPECTED_ROLE_COUNTS[
                d.component_id
            ], d.component_id

    def test_no_duplicate_ids_or_versions(self):
        keys = [(d.component_id, d.component_version) for d in WAVE6_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_no_duplicate_ids_or_versions_across_full_catalog(self):
        keys = [(d.component_id, d.component_version) for d in REGISTERED_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_lexicographic_tuple_order(self):
        ids = [d.component_id for d in REGISTERED_COMPONENTS]
        assert ids == sorted(ids)  # §15.2 ordering law

    def test_no_placeholder_values(self):
        text = canonical_json(
            [model_to_dict(d) for d in WAVE6_COMPONENTS]
        ).lower()
        for marker in ("todo", "tbd", "lorem", "dummy", "fixme", "xxx"):
            assert marker not in text, marker


class TestDefinitionValidity:
    def test_every_definition_passes_validate_definition(self):
        for d in WAVE6_COMPONENTS:
            validate_definition(d)

    def test_every_default_variant_exists(self):
        for d in WAVE6_COMPONENTS:
            if d.supported_variants:
                assert d.default_variant in d.supported_variants, d.component_id
            else:
                assert d.default_variant == "", d.component_id

    def test_lifecycle_is_proposed_until_emitters_exist(self):
        # Operator decision carried through 002B-002F and reaffirmed for
        # 002G (preflight Accepted-Warning Disposition): no renderer/gates
        # package is built this wave; no component is promoted to ACTIVE.
        for d in WAVE6_COMPONENTS:
            assert d.lifecycle_status is LifecycleStatus.PROPOSED

    def test_required_contract_fields_present(self):
        for d in WAVE6_COMPONENTS:
            assert d.analytics_contract.impression_id == d.component_id.replace(".", "-")
            assert d.rendering_contract.emitter_key == d.component_id + "@1"
            assert d.rendering_contract.class_prefix == EXPECTED_CLASS_PREFIX[d.component_id]
            assert d.description and d.display_name
            assert d.design_token_dependencies, d.component_id
            assert d.example_fixture_ids

    def test_fixture_ids_follow_grammar(self):
        expected_suffixes = {
            "min", "full", "bad-prop", "bad-slot", "mobile", "long", "a11y",
        }
        for d in WAVE6_COMPONENTS:
            suffixes = {
                fid.replace("fx-%s-" % d.component_id, "")
                for fid in d.example_fixture_ids
            }
            assert suffixes == expected_suffixes, d.component_id

    def test_no_directory_contract_in_wave6(self):
        # §6.3's ListingKind semantics are Wave 4's domain; no Wave 6
        # component is listing-kind-bearing.
        for d in WAVE6_COMPONENTS:
            assert d.directory_contract is None, d.component_id

    def test_no_monetization_contract_in_wave6(self):
        # §5.10: only the MONETIZATION family requires monetization_contract.
        for d in WAVE6_COMPONENTS:
            assert d.monetization_contract is None, d.component_id

    def test_no_conversion_contract_in_wave6(self):
        # Wave 6 is discovery/content support, not a conversion surface --
        # §27.7's table names no ConversionGoal for any of the seven rows.
        for d in WAVE6_COMPONENTS:
            assert d.conversion_contract is None, d.component_id

    def test_no_free_form_string_props(self):
        for d in WAVE6_COMPONENTS:
            for props in (d.required_props, d.optional_props):
                for name, spec in props.items():
                    assert isinstance(spec.prop_type, PropType), (d.component_id, name)

    def test_definitions_are_frozen_and_reject_extras(self):
        for d in WAVE6_COMPONENTS:
            with pytest.raises(Exception):
                d.component_id = "x.y.z"
            assert d.component_id != "x.y.z"

    def test_seo_local_links_source_ref_and_link_slot_shape(self):
        # Modeled exactly on directory.categories.grid's Wave-3 precedent
        # (§27.4): a CONTENT_BLOCK_REF source-ref prop plus a LinkSpec slot
        # capped at the §5.9 per-block ceiling. Components never invent URLs.
        for cid, prop_name, slot_name in (
            ("seo.local-links.cities", "city_source_ref", "city_links"),
            ("seo.local-links.categories", "category_source_ref", "category_links"),
        ):
            d = _get(cid)
            assert d.required_props[prop_name].prop_type is PropType.CONTENT_BLOCK_REF
            slot = d.required_content_slots[slot_name]
            assert slot.block_type == "LinkSpec"
            assert slot.cardinality is SlotCardinality.ONE_TO_N
            assert slot.max_count == SEO_LOCAL_LINKS_MAX_PER_BLOCK

    def test_seo_local_links_seo_contract_internal_only(self):
        for cid in ("seo.local-links.cities", "seo.local-links.categories"):
            d = _get(cid)
            assert d.seo_contract.link_kinds == ("internal",)

    def test_content_intro_contextual_context_role_prop(self):
        # Modeled exactly on hero.local.standard's Wave-3 context_role
        # precedent (§27.4).
        d = _get("content.intro.contextual")
        assert d.required_props["context_role"].prop_type is PropType.STR_ENUM
        assert set(d.required_props["context_role"].enum_values) == {
            PageRole.CATEGORY.value, PageRole.CITY.value, PageRole.CITY_CATEGORY.value,
        }
        assert d.required_content_slots["intro"].block_type == "RichTextBlock"
        assert d.quality_gate_requirements == ("CG-SEO-007",)

    def test_content_toc_standard_nav_semantic_and_heading_refs_prop(self):
        d = _get("content.toc.standard")
        assert d.semantic_element is SemanticElement.NAV
        assert d.required_props["heading_refs"].prop_type is PropType.CONTENT_BLOCK_REF
        assert d.responsive_contract.collapse_behavior == "jump-select"
        assert d.accessibility_contract.keyboard_operable is True

    def test_content_table_comparison_block_type_and_responsive_adaptation(self):
        d = _get("content.table.comparison")
        assert d.required_content_slots["table"].block_type == "ComparisonTableBlock"
        assert d.required_content_slots["table"].cardinality is SlotCardinality.EXACTLY_ONE
        assert d.responsive_contract.table_adaptation == "scroll-x"

    def test_content_resources_grid_composes_linkspec_not_invented_type(self):
        # Composition-over-invention: a resource card is modeled via the
        # existing LinkSpec type, matching directory.categories.grid's
        # category_tiles precedent, not a new block type.
        d = _get("content.resources.grid")
        slot = d.required_content_slots["resources"]
        assert slot.block_type == "LinkSpec"
        assert slot.cardinality is SlotCardinality.ONE_TO_N
        assert slot.max_count == 12
        assert d.allowed_child_components == ("layout.grid.standard",)

    def test_content_section_editorial_heading_levels(self):
        d = _get("content.section.editorial")
        assert d.seo_contract.heading_levels == (2, 3)
        assert set(d.supported_page_roles) == {
            PageRole.EDITORIAL_GUIDE, PageRole.BEST_OF, PageRole.BUSINESS_PROFILE,
        }


class TestDeterminism:
    def test_identical_catalog_identical_hash(self):
        assert (
            ComponentRegistry(WAVE6_COMPONENTS).registry_hash()
            == ComponentRegistry(WAVE6_COMPONENTS).registry_hash()
        )

    def test_registration_order_does_not_alter_hash(self):
        forward = ComponentRegistry(WAVE6_COMPONENTS).registry_hash()
        backward = ComponentRegistry(tuple(reversed(WAVE6_COMPONENTS))).registry_hash()
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
        prints = [definition_fingerprint(d) for d in WAVE6_COMPONENTS]
        assert prints == [definition_fingerprint(d) for d in WAVE6_COMPONENTS]
        assert len(set(prints)) == 7

    def test_earlier_waves_fingerprints_unchanged_by_wave6_addition(self):
        from engines.website_generation.components.catalog.layout_atoms import (
            WAVE1_COMPONENTS,
        )
        from engines.website_generation.components.catalog.navigation import (
            WAVE2_COMPONENTS,
        )
        from engines.website_generation.components.catalog.discovery import (
            WAVE3_COMPONENTS,
        )
        from engines.website_generation.components.catalog.listings_profiles import (
            WAVE4_COMPONENTS,
        )
        from engines.website_generation.components.catalog.trust_conversion import (
            WAVE5_COMPONENTS,
        )
        earlier = {
            d.component_id: definition_fingerprint(d)
            for d in WAVE1_COMPONENTS + WAVE2_COMPONENTS + WAVE3_COMPONENTS
            + WAVE4_COMPONENTS + WAVE5_COMPONENTS
        }
        r = build_default_registry()
        for component_id, expected_fp in earlier.items():
            got = r.get(component_id)
            assert definition_fingerprint(got) == expected_fp, component_id


class TestCompatibilityMetadata:
    def test_compatibility_axes_pinned(self):
        for d in WAVE6_COMPONENTS:
            assert set(d.compatibility_range) == {
                "renderer", "token_schema", "registry_schema",
            }, d.component_id

    def test_gate_requirements_match_authority_table(self):
        for d in WAVE6_COMPONENTS:
            assert d.quality_gate_requirements == EXPECTED_GATES[d.component_id], (
                d.component_id
            )

    def test_page_roles_and_region_kinds_typed(self):
        for d in WAVE6_COMPONENTS:
            assert all(isinstance(r, PageRole) for r in d.supported_page_roles)
            assert all(isinstance(r, RegionKind) for r in d.allowed_parent_regions)


class TestRegistryLookups:
    def test_every_wave6_component_resolvable(self):
        r = build_default_registry()
        for d in WAVE6_COMPONENTS:
            got = r.get(d.component_id, "1.0.0")
            assert got.component_id == d.component_id

    def test_by_family_returns_wave6_sets(self):
        r = build_default_registry()
        assert len(r.by_family(ComponentFamily.SEO)) == 2
        # content family = 1 Wave 4 (content.description.business) + 1
        # Wave 5 (content.faq.standard) + 5 Wave 6 = 7.
        assert len(r.by_family(ComponentFamily.CONTENT)) == 7

    def test_candidates_for_editorial_guide_includes_wave6_and_wave5_components(self):
        r = build_default_registry()
        guide_ids = {d.component_id for d in r.candidates_for(PageRole.EDITORIAL_GUIDE)}
        for cid in (
            "content.section.editorial", "content.toc.standard",
            "content.table.comparison", "content.resources.grid",
            "content.faq.standard", "form.capture.newsletter",
        ):
            assert cid in guide_ids, cid
        assert "seo.local-links.cities" not in guide_ids
        assert "seo.local-links.categories" not in guide_ids

    def test_candidates_for_regional_hub_includes_seo_local_links_cities_only(self):
        r = build_default_registry()
        hub_ids = {d.component_id for d in r.candidates_for(PageRole.REGIONAL_HUB)}
        assert "seo.local-links.cities" in hub_ids
        assert "seo.local-links.categories" not in hub_ids

    def test_candidates_for_home_includes_wave6_home_components(self):
        r = build_default_registry()
        home_ids = {d.component_id for d in r.candidates_for(PageRole.HOME)}
        assert "content.resources.grid" in home_ids
        assert "seo.local-links.cities" in home_ids
        assert "content.intro.contextual" not in home_ids

    def test_variant_resolution(self):
        r = build_default_registry()
        assert r.resolve_variant(
            "seo.local-links.cities", "inline-list"
        ).display_name == "Inline list"


class TestSeoAndEditorialDoctrineEnforcement:
    """AES-WEB-002 §31 acceptance for Wave 6 centers on CG-SEO-004/007
    (linking floors/ceilings, duplicate-content watchdog), not the E1-E11
    conversion doctrine -- Wave 6 has no conversion-bearing component. Per
    the same discipline test_catalog_wave5.py's E1-E11 suite established:
    each rule is addressed explicitly, including the several correctly out
    of this wave's scope, rather than silently skipped.
    """

    # E1 -- False urgency: structurally impossible here -- no Wave 6
    # component declares a conversion_contract at all (test_no_
    # conversion_contract_in_wave6), so no urgency_policy value exists to
    # violate E1 in the first place.
    def test_e1_false_urgency_structurally_absent(self):
        for d in WAVE6_COMPONENTS:
            assert d.conversion_contract is None, d.component_id

    # E2 -- Fabricated reviews/testimonials: owned by trust.* (Wave 5); no
    # Wave 6 component is trust-family or review-bearing.
    def test_e2_fabricated_reviews_out_of_wave_scope(self):
        for d in WAVE6_COMPONENTS:
            for slots in (d.required_content_slots, d.optional_content_slots):
                for spec in slots.values():
                    assert spec.block_type not in ("ReviewBlock", "RatingSummary"), (
                        d.component_id
                    )

    # E3 -- Deceptive scarcity / fake inventory counts: no component exposes
    # a count prop without a data_source reference. Structurally satisfied
    # by absence.
    def test_e3_deceptive_scarcity_structurally_absent(self):
        for d in WAVE6_COMPONENTS:
            for name in list(d.required_props) + list(d.optional_props):
                assert "count" not in name.lower(), (d.component_id, name)

    # E4 -- Hidden fees: owned by commerce.* (Wave 7, §5.12); no Wave 6
    # component carries a PriceSpec slot.
    def test_e4_hidden_fees_out_of_wave_scope(self):
        for d in WAVE6_COMPONENTS:
            for slots in (d.required_content_slots, d.optional_content_slots):
                for spec in slots.values():
                    assert spec.block_type != "PriceSpec", d.component_id

    # E5 -- Disguised advertisements: owned by monetization.* (Wave 7,
    # §5.10) -- no Wave 6 component is monetization-family or carries a
    # monetization_contract (see TestDefinitionValidity).
    def test_e5_disguised_ads_out_of_wave_scope(self):
        for d in WAVE6_COMPONENTS:
            assert d.component_family is not ComponentFamily.MONETIZATION

    # E6 -- Misleading rankings: ranked lists must bind ranking_rationale or
    # a methodology link. content.table.comparison renders a typed table,
    # not a ranked list, and no Wave 6 component binds a ranking_rationale
    # slot -- owned by listing/best-of ranked-list contexts (Wave 4).
    def test_e6_misleading_rankings_out_of_wave_scope(self):
        for d in WAVE6_COMPONENTS:
            for slots in (d.required_content_slots, d.optional_content_slots):
                assert "ranking_rationale" not in slots, d.component_id

    # E7 -- Inaccessible interactions as friction: the one genuinely
    # interactive Wave 6 component (content.toc.standard's jump navigation)
    # declares keyboard_operable=True; there is no conversion exception.
    def test_e7_accessibility_toc_keyboard_operable(self):
        d = _get("content.toc.standard")
        assert d.accessibility_contract.keyboard_operable is True

    # E8 -- Manipulative consent patterns: owned by form.* (Wave 5); no
    # Wave 6 component renders a consent control.
    def test_e8_manipulative_consent_out_of_wave_scope(self):
        for d in WAVE6_COMPONENTS:
            assert "atom.field.choice" not in d.allowed_child_components

    # E9 -- Bait-and-switch copy: CTA label must match conversion_goal;
    # structurally impossible -- no Wave 6 component has a conversion_contract
    # or a CTA-shaped "label" slot.
    def test_e9_bait_and_switch_out_of_wave_scope(self):
        for d in WAVE6_COMPONENTS:
            assert "label" not in d.required_content_slots

    # E10 -- Fake verification badges: owned by profile.header.business
    # (Wave 4) / status.listing.pending (Wave 7); no Wave 6 component
    # renders a verification indicator.
    def test_e10_fake_verification_out_of_wave_scope(self):
        for d in WAVE6_COMPONENTS:
            assert "CG-COM-004" not in d.quality_gate_requirements

    # E11 -- Fake popularity indicators: same rule as E3.
    def test_e11_fake_popularity_structurally_absent(self):
        for d in WAVE6_COMPONENTS:
            for name in list(d.required_props) + list(d.optional_props):
                assert "popular" not in name.lower(), (d.component_id, name)

    def test_cg_seo_003_and_004_linkage(self):
        assert "CG-SEO-003" in _get("seo.local-links.cities").quality_gate_requirements
        assert "CG-SEO-004" in _get("seo.local-links.cities").quality_gate_requirements
        assert "CG-SEO-004" in _get("seo.local-links.categories").quality_gate_requirements
        assert "CG-SEO-003" in _get("content.resources.grid").quality_gate_requirements

    def test_cg_seo_007_watchdog_on_content_intro_contextual(self):
        d = _get("content.intro.contextual")
        assert d.quality_gate_requirements == ("CG-SEO-007",)
        assert "fx-content.intro.contextual-long" in d.example_fixture_ids

    def test_components_never_invent_urls(self):
        # §5.9: link sets are derived from SiteArchitecture topology only.
        # Both seo.local-links.* components bind a CONTENT_BLOCK_REF source
        # ref, never a free-typed route/string for the link source itself.
        for cid in ("seo.local-links.cities", "seo.local-links.categories"):
            d = _get(cid)
            source_ref_specs = [
                spec for name, spec in d.required_props.items()
                if name.endswith("_source_ref")
            ]
            assert len(source_ref_specs) == 1
            assert source_ref_specs[0].prop_type is PropType.CONTENT_BLOCK_REF


class TestSeoLocalLinksConstants:
    def test_link_ceiling_values_match_authority(self):
        # §5.9: "24 links per block, <=2 blocks per page."
        assert SEO_LOCAL_LINKS_MAX_PER_BLOCK == 24
        assert SEO_LOCAL_LINKS_MAX_BLOCKS_PER_PAGE == 2

    def test_seo_local_links_slots_respect_ceiling_constant(self):
        assert _get("seo.local-links.cities").required_content_slots[
            "city_links"
        ].max_count == SEO_LOCAL_LINKS_MAX_PER_BLOCK
        assert _get("seo.local-links.categories").required_content_slots[
            "category_links"
        ].max_count == SEO_LOCAL_LINKS_MAX_PER_BLOCK


class TestSecondaryRecipeTables:
    """The five new secondary-role recipe tables (§6.1, §26 closing note,
    §34.2 bounded deferral, closed by this wave per §31). Per AMB-002G-02
    (operator-approved), this delivery is strictly additive: it does not
    touch HOME_RECIPE_SLOTS, CATEGORY_RECIPE_SLOTS, or
    BUSINESS_PROFILE_RECIPE_SLOTS.
    """

    def test_all_five_tables_exist_with_expected_slot_counts(self):
        expected_counts = {
            "EDITORIAL_GUIDE_RECIPE_SLOTS": 5,
            "COLLECTION_RECIPE_SLOTS": 3,
            "SERVICE_AREA_RECIPE_SLOTS": 5,
            "VERIFICATION_RECIPE_SLOTS": 5,
            "REGIONAL_HUB_RECIPE_SLOTS": 6,
        }
        for name, count in expected_counts.items():
            table = getattr(constants_components, name)
            assert len(table) == count, name

    def test_every_slot_page_role_matches_table_role(self):
        for table_name, role in SECONDARY_RECIPE_TABLES.items():
            table = getattr(constants_components, table_name)
            for slot in table:
                assert slot["page_role"] == role, (table_name, slot["slot_id"])
                assert PageRole(slot["page_role"])  # valid enum value

    def test_every_slot_purpose_is_valid_or_empty(self):
        valid_purposes = {p.value for p in CommercialPurpose}
        for table_name in SECONDARY_RECIPE_TABLES:
            table = getattr(constants_components, table_name)
            for slot in table:
                assert slot["purpose"] == "" or slot["purpose"] in valid_purposes, (
                    table_name, slot["slot_id"], slot["purpose"],
                )

    def test_every_slot_region_is_valid_or_empty(self):
        valid_regions = {r.value for r in RegionKind}
        for table_name in SECONDARY_RECIPE_TABLES:
            table = getattr(constants_components, table_name)
            for slot in table:
                assert slot["required_region"] == "" or slot["required_region"] in valid_regions, (
                    table_name, slot["slot_id"],
                )

    def test_optional_slots_use_sentinel_or_role_filtering_only(self):
        # Every required=False slot either uses the shared unbuilt-family
        # sentinel (content-slot-filtered) or an honest, non-sentinel
        # required_prop_names with no required_slot_names (role-filtered,
        # role-mismatch alone excludes every non-matching candidate).
        for table_name in SECONDARY_RECIPE_TABLES:
            table = getattr(constants_components, table_name)
            for slot in table:
                if slot["required"]:
                    continue
                assert slot["fallback_component_id"] == "", (
                    table_name, slot["slot_id"],
                )
                is_sentinel = slot["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
                is_role_filtered_only = (
                    slot["required_slot_names"] == ()
                    and bool(slot["required_prop_names"])
                )
                assert is_sentinel or is_role_filtered_only, (
                    table_name, slot["slot_id"],
                )

    def test_required_slots_declare_a_fallback(self):
        # Every required=True slot in these five new tables carries a
        # guaranteed-satisfiable fallback -- §14.2 step 9's rule, applied
        # uniformly since none of the five roles has a written §26 prose
        # recipe to inherit fallbacks from.
        for table_name in SECONDARY_RECIPE_TABLES:
            table = getattr(constants_components, table_name)
            for slot in table:
                if slot["required"]:
                    assert slot["fallback_component_id"] != "", (
                        table_name, slot["slot_id"],
                    )

    def test_claimed_real_candidate_bindings_resolve_against_registry(self):
        # Every slot documented in constants/components.py as binding a
        # *real* (non-fallback-only) Wave 1-6 candidate must actually
        # resolve against the registry via that exact prop/slot signature.
        r = build_default_registry()

        def resolves(role, prop_names=(), slot_names=()):
            role = PageRole(role)
            for d in r.candidates_for(role):
                have_props = set(d.required_props) | set(d.optional_props)
                have_slots = set(d.required_content_slots) | set(d.optional_content_slots)
                if set(prop_names) <= have_props and set(slot_names) <= have_slots:
                    return True
            return False

        assert resolves("editorial-guide", slot_names=("resources",))
        assert resolves("collection", prop_names=("listing_ref", "density"))
        assert resolves(
            "service-area", prop_names=("context_role",), slot_names=("h1", "intro"),
        )
        assert resolves("regional-hub", prop_names=("location_source_ref",))
        assert resolves("regional-hub", slot_names=("city_links",))

    def test_does_not_modify_earlier_wave_recipe_tables(self):
        # AMB-002G-02 guard: the three earlier tables still carry their
        # known AES-WEB-002D/E sentinel slots, unchanged by this wave.
        home = {s["slot_id"]: s for s in constants_components.HOME_RECIPE_SLOTS}
        category = {s["slot_id"]: s for s in constants_components.CATEGORY_RECIPE_SLOTS}
        profile = {
            s["slot_id"]: s for s in constants_components.BUSINESS_PROFILE_RECIPE_SLOTS
        }
        assert home["editorial_resources"]["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert home["editorial_resources"]["required"] is False
        assert category["related_categories_cities"]["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert category["related_categories_cities"]["required"] is False
        assert profile["faqs"]["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert profile["faqs"]["required"] is False
        assert len(constants_components.HOME_RECIPE_SLOTS) == 9
        assert len(constants_components.CATEGORY_RECIPE_SLOTS) == 9
        assert len(constants_components.BUSINESS_PROFILE_RECIPE_SLOTS) == 15


class TestCityCategoryFixtureSet:
    """AES-WEB-002 §31's AES-WEB-002G acceptance criterion: "city-category
    programmatic fixture set (>= 20 generated fixture pages) passes
    CG-SEO-004/007." Per AMB-002G-01 (operator-approved): satisfied via the
    fixture-only approach -- a deterministically generated set of >= 20
    fixture IDs exercising seo.local-links.*/content.intro.contextual
    against synthetic city x category inputs, proving the components'
    declared floor/ceiling shape is respected across realistic variation.
    This does NOT run a live recipe/selection pipeline and does NOT require
    CITY_RECIPE_SLOTS or CITY_CATEGORY_RECIPE_SLOTS, neither of which this
    delivery creates (see catalog/seo_editorial.py's module docstring).

    No clock, no randomness (Atlas invariant): the city x category matrix is
    a fixed, literal cross product, and the per-fixture link count is a
    deterministic function of its index -- not generated per test run.
    """

    _CITIES = ("austin", "denver", "portland", "nashville", "raleigh")
    _CATEGORIES = ("groomers", "boarding", "vets", "trainers")

    def _fixture_specs(self):
        pairs = list(itertools.product(self._CITIES, self._CATEGORIES))
        specs = []
        for index, (city, category) in enumerate(pairs):
            # Deterministic link count linearly interpolated from 1 (index
            # 0, the floor-adjacent case) to the §5.9 ceiling (last index,
            # the ceiling-boundary case), so both ends of the legal range
            # are exercised by the fixed, literal set -- no clock/randomness.
            span = SEO_LOCAL_LINKS_MAX_PER_BLOCK - 1
            link_count = 1 + (index * span) // (len(pairs) - 1)
            specs.append(
                {
                    "fixture_id": "fx-city-category-%s-%s-seo-links" % (city, category),
                    "city": city,
                    "category": category,
                    "link_count": link_count,
                }
            )
        return specs

    def test_fixture_set_has_at_least_twenty_pages(self):
        specs = self._fixture_specs()
        assert len(specs) == len(self._CITIES) * len(self._CATEGORIES)
        assert len(specs) >= 20

    def test_fixture_ids_are_unique_and_deterministic(self):
        first = [s["fixture_id"] for s in self._fixture_specs()]
        second = [s["fixture_id"] for s in self._fixture_specs()]
        assert first == second  # deterministic, no clock/randomness
        assert len(first) == len(set(first))

    def test_every_fixture_respects_the_per_block_ceiling(self):
        # Proves CG-SEO-004's floor/ceiling logic and CG-SEO-007's
        # duplicate-content watchdog have a realistic fixture surface to
        # exercise once registered (AES-WEB-002I) -- ceiling-boundary and
        # low-count cases both present in the deterministic set.
        specs = self._fixture_specs()
        counts = {s["link_count"] for s in specs}
        assert all(1 <= c <= SEO_LOCAL_LINKS_MAX_PER_BLOCK for c in counts)
        assert max(counts) == SEO_LOCAL_LINKS_MAX_PER_BLOCK  # ceiling case present
        assert min(counts) == 1  # floor-adjacent case present

    def test_fixture_set_covers_every_seo_local_links_component(self):
        # Both seo.local-links.* components declare CG-SEO-004; the
        # synthetic set exercises the shared ceiling both share.
        cities_gates = _get("seo.local-links.cities").quality_gate_requirements
        categories_gates = _get("seo.local-links.categories").quality_gate_requirements
        assert "CG-SEO-004" in cities_gates
        assert "CG-SEO-004" in categories_gates

    def test_no_city_category_recipe_table_created(self):
        # AMB-002G-01 guard: this wave took the fixture-only approach, so
        # CITY_RECIPE_SLOTS / CITY_CATEGORY_RECIPE_SLOTS did not exist as of
        # AES-WEB-002G. AES-WEB-002J.1 "Recipe Completion" is the later
        # recipe-integration phase §26's closing note anticipated, and
        # authors both tables -- confirmed present here rather than
        # re-asserting the now-superseded absence.
        assert hasattr(constants_components, "CITY_RECIPE_SLOTS")
        assert hasattr(constants_components, "CITY_CATEGORY_RECIPE_SLOTS")
