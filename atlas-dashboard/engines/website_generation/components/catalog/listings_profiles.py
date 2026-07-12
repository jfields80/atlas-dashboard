"""Wave 4 catalog module — PROVISIONAL EXCEPTION ONLY (amendment A4).

This file is *not* the AES-WEB-002E Wave 4 delivery. AES-WEB-002 §34.3-A4
("Part 13 Phase 2 scope note") authorizes exactly one provisional component
ahead of Wave 4 proper: ``listing.card.standard``, the minimum real
registered component necessary for the AES-WEB-001 Phase 2 deliverable
proof (fixture spec composition) and for the home/category recipes (§26.1,
§26.2) to resolve a listing slot at all. Per the amendment: "AES-WEB-001
Phase 2's deliverable proof ... is achieved at AES-WEB-002D exit using
Waves 1–3 plus a provisional listing card, and completed through 002J."

Constraints this module honors (binding, not advisory):

* exactly one component — no other ``listing.*`` id may be added here
  before AES-WEB-002E is explicitly authorized;
* registry-backed and deterministic, like every other catalog entry;
* no Wave 4 functionality beyond this single card (no
  ``listing.card.featured``, ``listing.card.sponsored``,
  ``listing.row.compact``, no profile.* family, no content.description);
* no new ``ArtifactKind``, no new contracts. §27.5's "RS: via listing block"
  column names no block type defined in §8.4's typed content models — the
  authority defines no "listing content block" contract yet. Rather than
  invent one (forbidden by this amendment), the listing's content is
  resolved entirely through the existing ``LISTING_REF`` prop type (§8.1),
  which exists precisely to reference listing data; this definition
  declares no ``required_content_slots``.
* declared ``kind=ORGANIC`` only (§27.5 note) — the sponsored/featured
  variants are separate Wave 4 components (``listing.card.sponsored``,
  ``listing.card.featured``), not variants of this one, and are explicitly
  out of scope here (§7.1 "Commercial-intent variant" governance: a
  sponsored card is a different contract, never a variant).

Lifecycle: registered as ``PROPOSED`` — §23 promotion to ACTIVE requires a
complete emitter and full §30.2 fixture set, which arrive with the real
Wave 4 delivery (AES-WEB-002E), not here.
"""

from __future__ import annotations

from typing import Tuple

from engines.website_generation.contracts.components import (
    AccessibilityContract,
    ComponentDefinition,
    DirectoryContract,
    PropSpec,
    RenderingContract,
    SEOContract,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
    ListingKind,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
)
from engines.website_generation.components.catalog.layout_atoms import (
    _COMPAT,
    _analytics,
    _fixtures,
)

# listing.card.standard: "home, cat, city, cc, sr, prof, collection" (§27.5).
_LISTING_CARD_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.CITY_CATEGORY,
    PageRole.SEARCH_RESULTS,
    PageRole.BUSINESS_PROFILE,
    PageRole.COLLECTION,
)


LISTING_CARD_STANDARD = ComponentDefinition(
    component_id="listing.card.standard",
    component_family=ComponentFamily.LISTING,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Standard Listing Card",
    description=(
        "PROVISIONAL (amendment A4): the sole listing.* component "
        "authorized ahead of the AES-WEB-002E Wave 4 delivery, registered "
        "only as the minimum real component the AES-WEB-001 Phase 2 proof "
        "and the home/category recipes (§26.1, §26.2) need to resolve a "
        "listing slot. ORGANIC kind only — sponsored/featured rendering is "
        "a different contract (separate Wave 4 components), never a "
        "variant of this one (§7.1)."
    ),
    commercial_purpose=CommercialPurpose.EXPOSE_INVENTORY,
    secondary_purposes=(CommercialPurpose.SUPPORT_COMPARISON,),
    supported_page_roles=_LISTING_CARD_ROLES,
    required_props={
        "listing_ref": PropSpec(
            prop_type=PropType.LISTING_REF,
            description=(
                "Reference to the bound listing's ContentPackage data; "
                "resolves the §27.5 'via listing block' content — no "
                "separate content slot is declared (see module docstring)."
            ),
        ),
        "density": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("comfortable", "compact"),
            description="The shared global density axis (§7.1) — not a variant.",
        ),
    },
    supported_variants={
        "standard": VariantSpec(display_name="Standard"),
        "minimal": VariantSpec(display_name="Minimal"),
    },
    default_variant="standard",
    semantic_element=SemanticElement.ARTICLE,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.raised",
        "radius.card",
        "typography.heading.3",
        "color.text.link",
        "color.text.default",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    seo_contract=SEOContract(link_kinds=("internal",)),
    directory_contract=DirectoryContract(
        supported_listing_kinds=(ListingKind.ORGANIC,),
        requires_disclosure=False,
    ),
    analytics_contract=_analytics("listing.card.standard", "listing_click"),
    rendering_contract=RenderingContract(
        emitter_key="listing.card.standard@1",
        class_prefix="ac-listing",
        dom_budget=60,  # §25: listing cards carry a lower DOM ceiling (60).
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-008", "CG-COM-001"),
    example_fixture_ids=_fixtures("listing.card.standard"),
)


# Provisional export — deliberately named to signal it is NOT the Wave 4
# catalog (WAVE4_COMPONENTS is reserved for AES-WEB-002E). Exactly one
# component; the registry-integrity tests assert this stays true.
PROVISIONAL_WAVE4_COMPONENTS: Tuple[ComponentDefinition, ...] = (
    LISTING_CARD_STANDARD,
)
