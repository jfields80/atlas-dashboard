"""Wave 4 catalog tests (AES-WEB-002E; AES-WEB-002 §27.5, §15.2, §30.1).

Catalog completeness (exact IDs, versions, families, roles, variants,
count), definition validity, determinism (hash stability across order and
process restarts), compatibility metadata, registry lookups, and
architecture boundaries — mirrors test_catalog_wave3.py's structure.

Field-level coverage specific to listing.card.standard (registered early
under amendment A4) lives in test_catalog_listing_provisional.py; this
module tests the full WAVE4_COMPONENTS tuple as a wave, exactly as
test_catalog_wave3.py does for WAVE3_COMPONENTS.
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
    ListingKind,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
)
from engines.website_generation.components.catalog.listings_profiles import (
    WAVE4_COMPONENTS,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)

APP_ROOT = Path(__file__).resolve().parents[3]

# The exact §27.5 Wave 4 inventory (lexicographic — §15.2 ordering law).
EXPECTED_IDS = [
    "content.description.business",
    "listing.card.featured",
    "listing.card.sponsored",
    "listing.card.standard",
    "listing.row.compact",
    "profile.areas.served",
    "profile.contact.panel",
    "profile.credentials.list",
    "profile.gallery.standard",
    "profile.header.business",
    "profile.hours.table",
    "profile.map.directions",
]

EXPECTED_VARIANTS = {
    "content.description.business": (),
    "listing.card.featured": (),
    "listing.card.sponsored": (),
    "listing.card.standard": ("minimal", "standard"),
    "listing.row.compact": ("comparison", "result"),
    "profile.areas.served": ("list", "map-adjacent"),
    "profile.contact.panel": ("inline", "sidebar"),
    "profile.credentials.list": (),
    "profile.gallery.standard": ("scroll-snap",),
    "profile.header.business": ("claimed", "unclaimed"),
    "profile.hours.table": (),
    "profile.map.directions": ("static-image",),
}

# §27.5 "Roles" column, mapped to PageRole membership counts.
EXPECTED_ROLE_COUNTS = {
    "content.description.business": 1,  # prof
    "listing.card.featured": 3,  # home, cat, city
    "listing.card.sponsored": 3,  # cat, cc, sr
    "listing.card.standard": 7,  # home, cat, city, cc, sr, prof, collection
    "listing.row.compact": 2,  # sr, cmp
    "profile.areas.served": 1,
    "profile.contact.panel": 1,
    "profile.credentials.list": 1,
    "profile.gallery.standard": 1,
    "profile.header.business": 1,
    "profile.hours.table": 1,
    "profile.map.directions": 1,
}

EXPECTED_FAMILY = {
    "content.description.business": ComponentFamily.CONTENT,
    "listing.card.featured": ComponentFamily.LISTING,
    "listing.card.sponsored": ComponentFamily.LISTING,
    "listing.card.standard": ComponentFamily.LISTING,
    "listing.row.compact": ComponentFamily.LISTING,
    "profile.areas.served": ComponentFamily.PROFILE,
    "profile.contact.panel": ComponentFamily.PROFILE,
    "profile.credentials.list": ComponentFamily.PROFILE,
    "profile.gallery.standard": ComponentFamily.PROFILE,
    "profile.header.business": ComponentFamily.PROFILE,
    "profile.hours.table": ComponentFamily.PROFILE,
    "profile.map.directions": ComponentFamily.PROFILE,
}

EXPECTED_CLASS_PREFIX = {
    "content.description.business": "ac-content",
    "listing.card.featured": "ac-listing",
    "listing.card.sponsored": "ac-listing",
    "listing.card.standard": "ac-listing",
    "listing.row.compact": "ac-listing",
    "profile.areas.served": "ac-profile",
    "profile.contact.panel": "ac-profile",
    "profile.credentials.list": "ac-profile",
    "profile.gallery.standard": "ac-profile",
    "profile.header.business": "ac-profile",
    "profile.hours.table": "ac-profile",
    "profile.map.directions": "ac-profile",
}

EXPECTED_GATES = {
    "content.description.business": ("CG-CMP-005",),
    "listing.card.featured": ("CG-COM-001",),
    "listing.card.sponsored": ("CG-COM-001", "CG-SEO-002"),
    "listing.card.standard": ("CG-CMP-008", "CG-COM-001"),
    "listing.row.compact": ("CG-RSP-004",),
    "profile.areas.served": ("CG-SEO-005",),
    "profile.contact.panel": ("CG-SEO-008",),
    "profile.credentials.list": ("CG-COM-003",),
    "profile.gallery.standard": ("CG-A11Y-010",),
    "profile.header.business": ("CG-CMP-005", "CG-COM-004"),
    "profile.hours.table": ("CG-A11Y-007",),
    "profile.map.directions": ("CG-A11Y-010",),
}


def _get(cid):
    return next(d for d in WAVE4_COMPONENTS if d.component_id == cid)


class TestCatalogCompleteness:
    def test_exact_component_ids(self):
        assert [d.component_id for d in WAVE4_COMPONENTS] == EXPECTED_IDS

    def test_exact_catalog_count(self):
        assert len(WAVE4_COMPONENTS) == 12  # §27.5 "Listings and profiles (12)"
        # Wave 1 (15) + Wave 2 (8) + Wave 3 (9) + Wave 4 (12) + Wave 5 (13)
        # + Wave 6 (7) + Wave 7 (8) = 72.
        assert len(REGISTERED_COMPONENTS) == 72

    def test_exact_versions(self):
        assert all(d.component_version == "1.0.0" for d in WAVE4_COMPONENTS)

    def test_exact_family_assignments(self):
        for d in WAVE4_COMPONENTS:
            assert d.component_family is EXPECTED_FAMILY[d.component_id], (
                d.component_id
            )

    def test_family_counts(self):
        listing = [d for d in WAVE4_COMPONENTS if d.component_family is ComponentFamily.LISTING]
        profile = [d for d in WAVE4_COMPONENTS if d.component_family is ComponentFamily.PROFILE]
        content = [d for d in WAVE4_COMPONENTS if d.component_family is ComponentFamily.CONTENT]
        assert len(listing) == 4 and len(profile) == 7 and len(content) == 1

    def test_exact_variant_names(self):
        for d in WAVE4_COMPONENTS:
            expected = EXPECTED_VARIANTS[d.component_id]
            assert tuple(sorted(d.supported_variants)) == expected, d.component_id

    def test_exact_role_counts_match_authority_table(self):
        for d in WAVE4_COMPONENTS:
            assert len(d.supported_page_roles) == EXPECTED_ROLE_COUNTS[
                d.component_id
            ], d.component_id

    def test_listing_card_featured_scoped_correctly(self):
        d = _get("listing.card.featured")
        assert set(d.supported_page_roles) == {
            PageRole.HOME, PageRole.CATEGORY, PageRole.CITY,
        }

    def test_listing_card_sponsored_scoped_correctly(self):
        d = _get("listing.card.sponsored")
        assert set(d.supported_page_roles) == {
            PageRole.CATEGORY, PageRole.CITY_CATEGORY, PageRole.SEARCH_RESULTS,
        }

    def test_listing_row_compact_scoped_correctly(self):
        d = _get("listing.row.compact")
        assert set(d.supported_page_roles) == {
            PageRole.SEARCH_RESULTS, PageRole.COMPARISON,
        }

    def test_profile_components_scoped_to_business_profile_only(self):
        for cid in EXPECTED_IDS:
            if cid.startswith("profile.") or cid == "content.description.business":
                d = _get(cid)
                assert set(d.supported_page_roles) == {PageRole.BUSINESS_PROFILE}, cid

    def test_no_duplicate_ids_or_versions(self):
        keys = [(d.component_id, d.component_version) for d in WAVE4_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_no_duplicate_ids_or_versions_across_full_catalog(self):
        keys = [(d.component_id, d.component_version) for d in REGISTERED_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_lexicographic_tuple_order(self):
        ids = [d.component_id for d in REGISTERED_COMPONENTS]
        assert ids == sorted(ids)  # §15.2 ordering law

    def test_no_placeholder_values(self):
        text = canonical_json(
            [model_to_dict(d) for d in WAVE4_COMPONENTS]
        ).lower()
        for marker in ("todo", "tbd", "lorem", "dummy", "fixme", "xxx"):
            assert marker not in text, marker


class TestDefinitionValidity:
    def test_every_definition_passes_validate_definition(self):
        for d in WAVE4_COMPONENTS:
            validate_definition(d)

    def test_every_default_variant_exists(self):
        for d in WAVE4_COMPONENTS:
            if d.supported_variants:
                assert d.default_variant in d.supported_variants, d.component_id
            else:
                assert d.default_variant == "", d.component_id

    def test_lifecycle_is_proposed_until_emitters_exist(self):
        # Operator decision (AES-WEB-002E kickoff): no renderer/gates package
        # is built this wave; no component is promoted to ACTIVE.
        for d in WAVE4_COMPONENTS:
            assert d.lifecycle_status is LifecycleStatus.PROPOSED

    def test_required_contract_fields_present(self):
        for d in WAVE4_COMPONENTS:
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
        for d in WAVE4_COMPONENTS:
            suffixes = {
                fid.replace("fx-%s-" % d.component_id, "")
                for fid in d.example_fixture_ids
            }
            assert suffixes == expected_suffixes, d.component_id

    def test_listing_cards_carry_60_dom_budget(self):
        for cid in (
            "listing.card.featured", "listing.card.sponsored",
            "listing.card.standard", "listing.row.compact",
        ):
            d = _get(cid)
            assert d.rendering_contract.dom_budget == 60, cid

    def test_featured_and_sponsored_require_disclosure(self):
        for cid in ("listing.card.featured", "listing.card.sponsored"):
            d = _get(cid)
            assert "disclosure" in d.required_content_slots, cid
            assert d.directory_contract.requires_disclosure is True, cid

    def test_featured_and_sponsored_listing_kinds(self):
        assert _get("listing.card.featured").directory_contract.supported_listing_kinds == (
            ListingKind.FEATURED,
        )
        assert _get("listing.card.sponsored").directory_contract.supported_listing_kinds == (
            ListingKind.SPONSORED,
        )

    def test_sponsored_outbound_links_marked_sponsored(self):
        assert _get("listing.card.sponsored").seo_contract.link_kinds == ("sponsored",)

    def test_listing_row_compact_scoped_to_organic(self):
        d = _get("listing.row.compact")
        assert d.directory_contract.supported_listing_kinds == (ListingKind.ORGANIC,)
        assert d.directory_contract.requires_disclosure is False

    def test_no_density_prop_on_featured_or_sponsored(self):
        # §27.5's RP column lists only LISTING_REF for these two rows,
        # unlike listing.card.standard's "LISTING_REF, density".
        for cid in ("listing.card.featured", "listing.card.sponsored"):
            d = _get(cid)
            assert "density" not in d.required_props, cid
            assert "density" not in d.optional_props, cid

    def test_profile_header_owns_h1_and_hero_region(self):
        d = _get("profile.header.business")
        assert d.seo_contract.heading_levels == (1,)
        assert "name" in d.required_content_slots
        assert RegionKind.HERO in d.allowed_parent_regions

    def test_profile_header_rating_summary_optional(self):
        d = _get("profile.header.business")
        assert "rating_summary" in d.optional_content_slots
        assert d.optional_content_slots["rating_summary"].block_type == "RatingSummary"
        assert (
            d.optional_content_slots["rating_summary"].cardinality
            is SlotCardinality.ZERO_OR_ONE
        )

    def test_profile_header_no_separate_badges_slot(self):
        d = _get("profile.header.business")
        assert "badges" not in d.required_content_slots
        assert "badges" not in d.optional_content_slots

    def test_profile_contact_panel_contact_spec(self):
        d = _get("profile.contact.panel")
        assert d.required_content_slots["contact_info"].block_type == "ContactSpec"

    def test_profile_hours_table_hours_spec(self):
        d = _get("profile.hours.table")
        assert d.required_content_slots["hours"].block_type == "HoursSpec"

    def test_profile_map_directions_slots_and_prop(self):
        d = _get("profile.map.directions")
        assert d.required_content_slots["location"].block_type == "GeoSpec"
        assert d.required_content_slots["directions_text"].block_type == "RichTextBlock"
        assert "address" not in d.required_content_slots
        assert d.required_props["listing_ref"].prop_type is PropType.LISTING_REF

    def test_profile_credentials_list_credential_block(self):
        d = _get("profile.credentials.list")
        assert d.required_content_slots["credentials"].block_type == "CredentialBlock"
        assert d.required_content_slots["credentials"].cardinality is SlotCardinality.ONE_TO_N

    def test_profile_gallery_standard_asset_role_and_cap(self):
        d = _get("profile.gallery.standard")
        assert AssetRole.GALLERY_IMAGE in d.supported_asset_roles
        images = d.required_content_slots["images"]
        assert images.cardinality is SlotCardinality.ONE_TO_N
        assert images.max_count == 10
        assert d.accessibility_contract.state_machine == "gallery"

    def test_content_description_business_h3_scoped(self):
        d = _get("content.description.business")
        assert d.seo_contract.heading_levels == (3,)
        assert "description" in d.required_content_slots

    def test_no_monetization_contract_in_wave4(self):
        # §5.10: only the MONETIZATION family requires monetization_contract;
        # Wave 4's disclosure needs are carried by directory_contract instead
        # (§17.3 — no component invents monetization state).
        for d in WAVE4_COMPONENTS:
            assert d.monetization_contract is None

    def test_no_free_form_string_props(self):
        for d in WAVE4_COMPONENTS:
            for props in (d.required_props, d.optional_props):
                for name, spec in props.items():
                    assert isinstance(spec.prop_type, PropType), (d.component_id, name)

    def test_definitions_are_frozen_and_reject_extras(self):
        for d in WAVE4_COMPONENTS:
            with pytest.raises(Exception):
                d.component_id = "x.y.z"
            assert d.component_id != "x.y.z"


class TestDeterminism:
    def test_identical_catalog_identical_hash(self):
        assert (
            ComponentRegistry(WAVE4_COMPONENTS).registry_hash()
            == ComponentRegistry(WAVE4_COMPONENTS).registry_hash()
        )

    def test_registration_order_does_not_alter_hash(self):
        forward = ComponentRegistry(WAVE4_COMPONENTS).registry_hash()
        backward = ComponentRegistry(tuple(reversed(WAVE4_COMPONENTS))).registry_hash()
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
        prints = [definition_fingerprint(d) for d in WAVE4_COMPONENTS]
        assert prints == [definition_fingerprint(d) for d in WAVE4_COMPONENTS]
        assert len(set(prints)) == 12

    def test_earlier_waves_fingerprints_unchanged_by_wave4_addition(self):
        from engines.website_generation.components.catalog.layout_atoms import (
            WAVE1_COMPONENTS,
        )
        from engines.website_generation.components.catalog.navigation import (
            WAVE2_COMPONENTS,
        )
        from engines.website_generation.components.catalog.discovery import (
            WAVE3_COMPONENTS,
        )
        earlier = {
            d.component_id: definition_fingerprint(d)
            for d in WAVE1_COMPONENTS + WAVE2_COMPONENTS + WAVE3_COMPONENTS
        }
        r = build_default_registry()
        for component_id, expected_fp in earlier.items():
            got = r.get(component_id)
            assert definition_fingerprint(got) == expected_fp, component_id


class TestCompatibilityMetadata:
    def test_compatibility_axes_pinned(self):
        for d in WAVE4_COMPONENTS:
            assert set(d.compatibility_range) == {
                "renderer", "token_schema", "registry_schema",
            }, d.component_id

    def test_gate_requirements_match_authority_table(self):
        for d in WAVE4_COMPONENTS:
            assert d.quality_gate_requirements == EXPECTED_GATES[d.component_id], (
                d.component_id
            )

    def test_page_roles_and_region_kinds_typed(self):
        for d in WAVE4_COMPONENTS:
            assert all(isinstance(r, PageRole) for r in d.supported_page_roles)
            assert all(isinstance(r, RegionKind) for r in d.allowed_parent_regions)


class TestRegistryLookups:
    def test_every_wave4_component_resolvable(self):
        r = build_default_registry()
        for d in WAVE4_COMPONENTS:
            got = r.get(d.component_id, "1.0.0")
            assert got.component_id == d.component_id

    def test_by_family_returns_wave4_sets(self):
        r = build_default_registry()
        assert len(r.by_family(ComponentFamily.LISTING)) == 4
        assert len(r.by_family(ComponentFamily.PROFILE)) == 7
        # content family = 1 Wave 4 (content.description.business) + 1
        # Wave 5 (content.faq.standard, §27.6) + 5 Wave 6 (§27.7) = 7.
        assert len(r.by_family(ComponentFamily.CONTENT)) == 7

    def test_candidates_for_business_profile_includes_wave4_components(self):
        r = build_default_registry()
        profile_ids = {d.component_id for d in r.candidates_for(PageRole.BUSINESS_PROFILE)}
        for cid in (
            "profile.header.business", "profile.contact.panel",
            "profile.hours.table", "profile.areas.served",
            "profile.map.directions", "profile.credentials.list",
            "profile.gallery.standard", "content.description.business",
            "listing.card.standard",
        ):
            assert cid in profile_ids, cid
        assert "listing.card.featured" not in profile_ids
        assert "listing.card.sponsored" not in profile_ids

    def test_candidates_for_home_includes_listing_card_featured(self):
        r = build_default_registry()
        home_ids = {d.component_id for d in r.candidates_for(PageRole.HOME)}
        assert "listing.card.featured" in home_ids
        assert "listing.card.sponsored" not in home_ids

    def test_candidates_for_search_results_includes_sponsored_and_row(self):
        r = build_default_registry()
        sr_ids = {d.component_id for d in r.candidates_for(PageRole.SEARCH_RESULTS)}
        assert "listing.card.sponsored" in sr_ids
        assert "listing.row.compact" in sr_ids
        assert "listing.card.featured" not in sr_ids

    def test_variant_resolution(self):
        r = build_default_registry()
        assert r.resolve_variant(
            "profile.header.business", "unclaimed"
        ).display_name == "Unclaimed"
