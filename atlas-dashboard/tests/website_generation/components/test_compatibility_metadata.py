"""Compatibility / capability metadata tests (AES-WEB-002A).

Declarative slot, page-archetype, content, asset, accessibility, responsive,
analytics, and monetization metadata — plus the registry rejections the
authority requires (unknown compatibility axis, monetization family without
a monetization contract, complexity-budget overflow). 002A declares
compatibility facts; it never filters, scores, ranks, or selects.
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.components import (
    AccessibilityContract,
    AnalyticsContract,
    DirectoryContract,
    MonetizationContract,
    PropSpec,
    RenderingContract,
    ResponsiveContract,
    SEOContract,
    SlotSpec,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    AssetRole,
    CommercialPurpose,
    ComponentFamily,
    ListingKind,
    PageRole,
    PropType,
    RegionKind,
    SlotCardinality,
)
from engines.website_generation.contracts.errors import (
    InvalidCompatibilityDeclarationError,
    InvalidComponentDefinitionError,
)
from engines.website_generation.components.registry import ComponentRegistry

from . import make_definition


class TestSlotAndContentMetadata:
    def test_valid_slot_declarations(self):
        d = make_definition(
            required_content_slots={
                "heading": SlotSpec(block_type="RichTextBlock")
            },
            optional_content_slots={
                "items": SlotSpec(
                    block_type="ReviewBlock",
                    cardinality=SlotCardinality.ONE_TO_N,
                    max_count=10,
                )
            },
        )
        r = ComponentRegistry([d])
        got = r.get(d.component_id)
        assert got.required_content_slots["heading"].block_type == "RichTextBlock"
        assert (
            got.optional_content_slots["items"].cardinality
            is SlotCardinality.ONE_TO_N
        )

    def test_slot_requires_block_type(self):
        with pytest.raises(Exception):
            SlotSpec()  # block_type is mandatory

    def test_content_requirement_registers(self):
        d = make_definition(
            required_content_slots={"h1": SlotSpec(block_type="RichTextBlock")}
        )
        assert ComponentRegistry([d]).get(d.component_id).required_content_slots


class TestPageArchetypeMetadata:
    def test_page_role_declarations_index(self):
        home = make_definition(supported_page_roles=(PageRole.HOME,))
        category = make_definition(
            component_id="listing.card.standard",
            component_family=ComponentFamily.LISTING,
            commercial_purpose=CommercialPurpose.EXPOSE_INVENTORY,
            supported_page_roles=(PageRole.CATEGORY,),
            rendering_contract=RenderingContract(
                emitter_key="listing.card.standard@1", class_prefix="ac-listing"
            ),
            analytics_contract=AnalyticsContract(
                impression_id="listing-card-standard"
            ),
        )
        r = ComponentRegistry([home, category])
        home_ids = [d.component_id for d in r.candidates_for(PageRole.HOME)]
        assert home_ids == ["hero.split.value-proposition"]
        cat_ids = [d.component_id for d in r.candidates_for(PageRole.CATEGORY)]
        assert cat_ids == ["listing.card.standard"]

    def test_candidates_for_is_index_not_selection(self):
        # Returns declared supporters, deterministically ordered, unscored.
        r = ComponentRegistry([make_definition()])
        assert r.candidates_for(PageRole.SEARCH_RESULTS) == ()


class TestAssetAndPropMetadata:
    def test_asset_role_requirements(self):
        d = make_definition(
            supported_asset_roles=(AssetRole.HERO_IMAGE, AssetRole.ICON)
        )
        assert AssetRole.HERO_IMAGE in ComponentRegistry([d]).get(
            d.component_id
        ).supported_asset_roles

    def test_prop_and_variant_metadata(self):
        d = make_definition(
            optional_props={
                "align": PropSpec(
                    prop_type=PropType.STR_ENUM,
                    enum_values=("left", "right"),
                    default="left",
                )
            },
            supported_variants={"image-right": VariantSpec(display_name="Right")},
            default_variant="image-right",
        )
        r = ComponentRegistry([d])
        assert r.resolve_variant(d.component_id, "image-right").display_name == (
            "Right"
        )


class TestCapabilityContracts:
    def test_accessibility_metadata(self):
        d = make_definition(
            accessibility_contract=AccessibilityContract(
                state_machine="drawer",
                keyboard_operable=True,
                focus_management=True,
                required_labels=("close_label",),
            )
        )
        got = ComponentRegistry([d]).get(d.component_id)
        assert got.accessibility_contract.state_machine == "drawer"

    def test_responsive_metadata(self):
        d = make_definition(
            responsive_contract=ResponsiveContract(
                collapse_behavior="grid-to-stack",
                sticky="bottom",
                table_adaptation="stacked-rows",
            )
        )
        assert ComponentRegistry([d]).get(
            d.component_id
        ).responsive_contract.sticky == "bottom"

    def test_seo_metadata(self):
        d = make_definition(
            seo_contract=SEOContract(
                heading_levels=(1,),
                link_kinds=("internal",),
                schema_fragments=("WebSite",),
                content_visibility="always-visible",
            )
        )
        assert ComponentRegistry([d]).get(
            d.component_id
        ).seo_contract.heading_levels == (1,)

    def test_analytics_metadata_requires_impression_id(self):
        with pytest.raises(Exception):
            AnalyticsContract()  # impression_id mandatory
        d = make_definition(
            analytics_contract=AnalyticsContract(
                impression_id="hero-split-value-proposition",
                interaction_events=("cta_click",),
            )
        )
        assert ComponentRegistry([d]).get(
            d.component_id
        ).analytics_contract.interaction_events == ("cta_click",)

    def test_directory_metadata(self):
        d = make_definition(
            component_id="listing.card.sponsored",
            component_family=ComponentFamily.LISTING,
            commercial_purpose=CommercialPurpose.EXPOSE_INVENTORY,
            directory_contract=DirectoryContract(
                supported_listing_kinds=(ListingKind.SPONSORED,),
                requires_disclosure=True,
            ),
        )
        got = ComponentRegistry([d]).get(d.component_id)
        assert got.directory_contract.requires_disclosure is True


class TestMonetizationAndIncompatibility:
    def test_monetization_family_requires_contract(self):
        # A monetization-family component without a monetization_contract is
        # rejected (AES-WEB-002 §5.10 / §15.2).
        with pytest.raises(InvalidComponentDefinitionError):
            ComponentRegistry(
                [
                    make_definition(
                        component_id="monetization.sponsor.featured",
                        component_family=ComponentFamily.MONETIZATION,
                        commercial_purpose=CommercialPurpose.PREPARE_MONETIZATION,
                    )
                ]
            )

    def test_monetization_metadata_valid(self):
        d = make_definition(
            component_id="monetization.sponsor.featured",
            component_family=ComponentFamily.MONETIZATION,
            commercial_purpose=CommercialPurpose.PREPARE_MONETIZATION,
            monetization_contract=MonetizationContract(
                requires_visible_disclosure=True,
                disclosure_kind="sponsored",
                link_rel="sponsored",
            ),
        )
        assert ComponentRegistry([d]).get(
            d.component_id
        ).monetization_contract.link_rel == "sponsored"

    def test_unknown_compatibility_axis_rejected(self):
        with pytest.raises(InvalidCompatibilityDeclarationError):
            ComponentRegistry(
                [make_definition(compatibility_range={"not_an_axis": ">=1.0.0"})]
            )

    def test_valid_compatibility_axis_accepted(self):
        d = make_definition(compatibility_range={"renderer": ">=1.0.0"})
        assert ComponentRegistry([d]).get(
            d.component_id
        ).compatibility_range == {"renderer": ">=1.0.0"}

    def test_complexity_budget_enforced(self):
        too_many_variants = {
            "v%d" % i: VariantSpec() for i in range(7)  # > MAX_VARIANTS (6)
        }
        with pytest.raises(InvalidComponentDefinitionError):
            ComponentRegistry(
                [make_definition(supported_variants=too_many_variants)]
            )
