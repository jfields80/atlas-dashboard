"""Amendment-A4 provenance tests for listing.card.standard (AES-WEB-002
§27.5, §34.3-A4) plus its enduring definition-validity/determinism coverage.

listing.card.standard was registered early, in AES-WEB-002D, as the sole
provisional component authorized ahead of schedule by amendment A4.
AES-WEB-002E has since completed Wave 4 around it (see
catalog/listings_profiles.py's module docstring): the "exactly one
listing.* component" / "no profile family yet" scope-discipline this file
used to enforce was the *pre*-002E precondition, superseded by design once
002E landed — it is not a regression. What this file protects now is
narrower and permanent: that A4's authorized contract shape survived 002E
unaltered (§22.2 — completing lifecycle artifacts is not a semantic
change).
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.artifacts import (
    canonical_json,
    model_to_dict,
)
from engines.website_generation.contracts.enums import (
    ComponentFamily,
    LifecycleStatus,
    ListingKind,
    PageRole,
    PropType,
    SemanticElement,
)
from engines.website_generation.components.catalog.listings_profiles import (
    LISTING_CARD_STANDARD,
    WAVE4_COMPONENTS,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)


class TestAmendmentA4Provenance:
    def test_listing_card_standard_is_part_of_wave4(self):
        assert LISTING_CARD_STANDARD in WAVE4_COMPONENTS

    def test_wave4_carries_the_full_twelve_component_inventory(self):
        assert len(WAVE4_COMPONENTS) == 12  # §27.5 "Listings and profiles (12)"

    def test_component_id_is_exactly_the_authorized_one(self):
        assert LISTING_CARD_STANDARD.component_id == "listing.card.standard"

    def test_a4_contract_shape_unchanged_by_002e(self):
        # §34.3-A4 authorized this exact contract ahead of schedule; 002E
        # completes its lifecycle artifacts without altering the contract.
        assert LISTING_CARD_STANDARD.component_version == "1.0.0"
        assert LISTING_CARD_STANDARD.directory_contract.supported_listing_kinds == (
            ListingKind.ORGANIC,
        )
        assert LISTING_CARD_STANDARD.monetization_contract is None
        assert LISTING_CARD_STANDARD.required_content_slots == {}
        assert LISTING_CARD_STANDARD.optional_content_slots == {}


class TestDefinitionValidity:
    def test_passes_validate_definition(self):
        validate_definition(LISTING_CARD_STANDARD)

    def test_lifecycle_is_proposed(self):
        assert LISTING_CARD_STANDARD.lifecycle_status is LifecycleStatus.PROPOSED

    def test_family_and_version(self):
        assert LISTING_CARD_STANDARD.component_family is ComponentFamily.LISTING
        assert LISTING_CARD_STANDARD.component_version == "1.0.0"

    def test_roles_match_authority_table(self):
        # §27.5 "home, cat, city, cc, sr, prof, collection".
        assert set(LISTING_CARD_STANDARD.supported_page_roles) == {
            PageRole.HOME, PageRole.CATEGORY, PageRole.CITY,
            PageRole.CITY_CATEGORY, PageRole.SEARCH_RESULTS,
            PageRole.BUSINESS_PROFILE, PageRole.COLLECTION,
        }

    def test_organic_kind_only(self):
        assert LISTING_CARD_STANDARD.directory_contract is not None
        assert LISTING_CARD_STANDARD.directory_contract.supported_listing_kinds == (
            ListingKind.ORGANIC,
        )

    def test_no_monetization_contract(self):
        assert LISTING_CARD_STANDARD.monetization_contract is None

    def test_listing_ref_and_density_props(self):
        assert (
            LISTING_CARD_STANDARD.required_props["listing_ref"].prop_type
            is PropType.LISTING_REF
        )
        density = LISTING_CARD_STANDARD.required_props["density"]
        assert density.prop_type is PropType.STR_ENUM
        assert set(density.enum_values) == {"comfortable", "compact"}

    def test_no_invented_content_slot_for_listing_data(self):
        # Module docstring: "via listing block" resolves through LISTING_REF,
        # not an invented content-slot/block-type contract.
        assert LISTING_CARD_STANDARD.required_content_slots == {}
        assert LISTING_CARD_STANDARD.optional_content_slots == {}

    def test_variants_standard_and_minimal(self):
        assert set(LISTING_CARD_STANDARD.supported_variants) == {"standard", "minimal"}
        assert LISTING_CARD_STANDARD.default_variant == "standard"

    def test_dom_budget_matches_25_listing_card_ceiling(self):
        assert LISTING_CARD_STANDARD.rendering_contract.dom_budget == 60

    def test_semantic_element_is_article(self):
        assert LISTING_CARD_STANDARD.semantic_element is SemanticElement.ARTICLE

    def test_gate_requirements(self):
        assert LISTING_CARD_STANDARD.quality_gate_requirements == (
            "CG-CMP-008", "CG-COM-001",
        )

    def test_fixture_ids_follow_grammar(self):
        expected_suffixes = {
            "min", "full", "bad-prop", "bad-slot", "mobile", "long", "a11y",
        }
        suffixes = {
            fid.replace("fx-listing.card.standard-", "")
            for fid in LISTING_CARD_STANDARD.example_fixture_ids
        }
        assert suffixes == expected_suffixes

    def test_no_placeholder_values(self):
        text = canonical_json(model_to_dict(LISTING_CARD_STANDARD)).lower()
        for marker in ("todo", "tbd", "lorem", "dummy", "fixme", "xxx"):
            assert marker not in text, marker

    def test_definition_is_frozen(self):
        with pytest.raises(Exception):
            LISTING_CARD_STANDARD.component_id = "listing.card.sponsored"


class TestDeterminism:
    def test_fingerprint_stable(self):
        assert (
            definition_fingerprint(LISTING_CARD_STANDARD)
            == definition_fingerprint(LISTING_CARD_STANDARD)
        )

    def test_registered_and_resolvable(self):
        r = build_default_registry()
        got = r.get("listing.card.standard")
        assert got.component_id == "listing.card.standard"

    def test_no_collision_with_registry(self):
        # A regression guard: registering the provisional component alongside
        # the full catalog must not raise (emitter_key/impression_id/family
        # uniqueness all hold).
        assert len(ComponentRegistry(REGISTERED_COMPONENTS)) == len(REGISTERED_COMPONENTS)
