"""Wave 4 catalog — Listing and Profile (AES-WEB-002E; AES-WEB-002 §27.5).

``listing.card.standard`` was registered early, in AES-WEB-002D, as the
single provisional exception authorized by amendment A4 (§34.3-A4) — see
its own docstring/comment below, preserved unchanged. This module now
carries the complete twelve-component §27.5 Wave 4 inventory: the three
remaining ``listing.*`` components, the full ``profile.*`` family, and
``content.description.business``.

Scope decision recorded for this delivery (binding for this wave, not a
silent assumption): no ``rendering/`` package, HTML emitter, or CSS exists
anywhere in this repository yet — ``RenderingContract.emitter_key`` is
declared metadata only, resolved "when the renderer exists, in a later
wave" (its own docstring). AES-WEB-002B/C/D established the precedent of
registering ``PROPOSED`` components with declared-but-unvalidated
``emitter_key`` strings and no real markup; this delivery continues that
precedent exactly. No component in this module is promoted to ``ACTIVE``
— §23 promotion requires a complete emitter and full §30.2 fixture set,
neither of which this wave builds. Real rendering, ``gates/`` execution,
and lifecycle promotion remain deferred to later, explicitly-scoped work.

Documented interpretive resolutions (consistent with the Wave 1–3
precedent of recording, not guessing, when §27.5's table under-determines
a detail against §8.4's typed content models):

* ``profile.contact.panel``'s §27.5 "RS: ContactSpec, CTA cluster" names a
  CTA cluster alongside the typed ContactSpec. The ``cta.*`` family is
  Wave 5 (AES-WEB-002F) and does not exist yet, so no
  ``allowed_child_components`` reference to it is declared here (a
  forward reference to an unregistered family would be speculative, not
  authority-grounded). This wave declares only the ``contact_info``
  slot (the part CG-SEO-008 NAP parity actually gates); the CTA cluster
  composition is deferred until Wave 5 ships, at which point extending
  ``allowed_child_components`` is an additive, registry-minor change
  (§22.2).
* ``profile.map.directions``'s §27.5 "RS: GeoSpec, address, directions
  text" repeats "address", but §13.3 is explicit that NAP renders from
  "the single ContactSpec block" — address is not re-declared as a second
  slot here. Instead this definition takes a ``listing_ref`` prop
  (``LISTING_REF``, the same mechanism ``listing.card.standard`` uses) to
  reach the shared listing/contact data, and declares only the two
  slots genuinely new to this component: ``location`` (``GeoSpec``) and
  ``directions_text`` (``RichTextBlock``).
* ``profile.gallery.standard``'s §27.5 "RS: images (1..10)" is modeled as
  a ``required_content_slots`` entry (``block_type="AssetRef"``,
  ``ONE_TO_N``, ``max_count=10``) rather than a prop, because ``PropSpec``
  has no repeated/collection concept (§8.1) while ``SlotSpec`` carries
  exactly the cardinality/max-count fields this requirement needs;
  ``supported_asset_roles=(AssetRole.GALLERY_IMAGE,)`` is declared
  alongside it as the complementary §3 asset-role capability declaration.
* ``profile.gallery.standard``'s §27.5 gate column reads "CG-A11Y-010,
  CG-CMP (carousel cap)" — the second reference does not name a specific
  §21.2 gate ID (no enumerated ``CG-CMP-0XX`` is titled "carousel cap");
  only the concretely-named ``CG-A11Y-010`` is declared in
  ``quality_gate_requirements`` here, since inventing a gate ID absent
  from §21's enumerated table is exactly the "no new registry contracts
  unless explicitly required" guardrail this delivery holds to.
* ``profile.header.business``'s §27.5 "RS: name(h1), rating summary (O),
  badges" declares ``name`` and ``rating_summary`` (``RatingSummary``,
  §8.4) as slots. "badges" is not a third slot: per §6.3's E10 rule,
  verification/claim badges are computed from the listing's existing
  ``verification_state``/claim data (already reachable via the required
  ``listing_ref`` prop) — the same "resolve via the existing reference,
  do not invent a block type" discipline ``listing.card.standard``
  already established for its own "via listing block" row.

All twelve definitions are declarative frozen data only — no markup, no
emitters, no selection, no behavior (§2.2).
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
    SlotSpec,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    AssetRole,
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
    ListingKind,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
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


# listing.card.featured / listing.card.sponsored roles (§27.5).
_LISTING_CARD_FEATURED_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CATEGORY,
    PageRole.CITY,
)
_LISTING_CARD_SPONSORED_ROLES: Tuple[PageRole, ...] = (
    PageRole.CATEGORY,
    PageRole.CITY_CATEGORY,
    PageRole.SEARCH_RESULTS,
)
_LISTING_ROW_COMPACT_ROLES: Tuple[PageRole, ...] = (
    PageRole.SEARCH_RESULTS,
    PageRole.COMPARISON,
)
_PROFILE_ONLY_ROLES: Tuple[PageRole, ...] = (PageRole.BUSINESS_PROFILE,)


LISTING_CARD_FEATURED = ComponentDefinition(
    component_id="listing.card.featured",
    component_family=ComponentFamily.LISTING,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Featured Listing Card",
    description=(
        "Paid placement in a dedicated featured zone (§6.3 FEATURED); "
        "never interleaved into organic rank order. Mandatory disclosure "
        "(§17, E5) and a distinct surface token satisfy the non-confusion "
        "rule (§6.3). No 'density' prop (§27.5 lists only LISTING_REF for "
        "this row, unlike listing.card.standard)."
    ),
    commercial_purpose=CommercialPurpose.EXPOSE_INVENTORY,
    secondary_purposes=(CommercialPurpose.PREPARE_MONETIZATION,),
    supported_page_roles=_LISTING_CARD_FEATURED_ROLES,
    required_props={
        "listing_ref": PropSpec(
            prop_type=PropType.LISTING_REF,
            description="Reference to the bound listing's ContentPackage data.",
        ),
    },
    required_content_slots={
        "disclosure": SlotSpec(
            block_type="DisclosureBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Mandatory visible featured-placement disclosure (§17.1, E5).",
        ),
    },
    semantic_element=SemanticElement.ARTICLE,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.featured",
        "radius.card",
        "typography.heading.3",
        "color.text.link",
        "color.text.default",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    seo_contract=SEOContract(link_kinds=("internal",)),
    directory_contract=DirectoryContract(
        supported_listing_kinds=(ListingKind.FEATURED,),
        requires_disclosure=True,
    ),
    analytics_contract=_analytics("listing.card.featured", "listing_click"),
    rendering_contract=RenderingContract(
        emitter_key="listing.card.featured@1",
        class_prefix="ac-listing",
        dom_budget=60,
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-001",),
    example_fixture_ids=_fixtures("listing.card.featured"),
)

LISTING_CARD_SPONSORED = ComponentDefinition(
    component_id="listing.card.sponsored",
    component_family=ComponentFamily.LISTING,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Sponsored Listing Card",
    description=(
        "Paid placement interleaved with organic results, capped per page "
        "(§17.2) and disclosed (§17.1, E5); outbound links carry "
        "rel=\"sponsored\" (§13.3, CG-SEO-002)."
    ),
    commercial_purpose=CommercialPurpose.EXPOSE_INVENTORY,
    secondary_purposes=(CommercialPurpose.PREPARE_MONETIZATION,),
    supported_page_roles=_LISTING_CARD_SPONSORED_ROLES,
    required_props={
        "listing_ref": PropSpec(
            prop_type=PropType.LISTING_REF,
            description="Reference to the bound listing's ContentPackage data.",
        ),
    },
    required_content_slots={
        "disclosure": SlotSpec(
            block_type="DisclosureBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Mandatory visible sponsored-placement disclosure (§17.1, E5).",
        ),
    },
    semantic_element=SemanticElement.ARTICLE,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.sponsored",
        "radius.card",
        "typography.heading.3",
        "color.text.link",
        "color.text.default",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    seo_contract=SEOContract(link_kinds=("sponsored",)),
    directory_contract=DirectoryContract(
        supported_listing_kinds=(ListingKind.SPONSORED,),
        requires_disclosure=True,
    ),
    analytics_contract=_analytics(
        "listing.card.sponsored", "sponsored_listing_click"
    ),
    rendering_contract=RenderingContract(
        emitter_key="listing.card.sponsored@1",
        class_prefix="ac-listing",
        dom_budget=60,
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-001", "CG-SEO-002"),
    example_fixture_ids=_fixtures("listing.card.sponsored"),
)

LISTING_ROW_COMPACT = ComponentDefinition(
    component_id="listing.row.compact",
    component_family=ComponentFamily.LISTING,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Compact Listing Row",
    description=(
        "Table-adjacent compact row for search-results and comparison "
        "contexts (§27.5). §27.5 declares no listing-kind restriction for "
        "this row; per the §7.1 commercial-intent-variant rule (a sponsored "
        "card is a different contract, never a variant), this definition "
        "is scoped to ORGANIC only, matching listing.card.standard's own "
        "precedent — a sponsored row is out of scope here."
    ),
    commercial_purpose=CommercialPurpose.EXPOSE_INVENTORY,
    secondary_purposes=(CommercialPurpose.SUPPORT_COMPARISON,),
    supported_page_roles=_LISTING_ROW_COMPACT_ROLES,
    required_props={
        "listing_ref": PropSpec(
            prop_type=PropType.LISTING_REF,
            description="Reference to the bound listing's ContentPackage data.",
        ),
    },
    supported_variants={
        "result": VariantSpec(display_name="Result row"),
        "comparison": VariantSpec(display_name="Comparison row"),
    },
    default_variant="result",
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.text.link",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    seo_contract=SEOContract(link_kinds=("internal",)),
    directory_contract=DirectoryContract(
        supported_listing_kinds=(ListingKind.ORGANIC,),
        requires_disclosure=False,
    ),
    analytics_contract=_analytics("listing.row.compact", "listing_click"),
    rendering_contract=RenderingContract(
        emitter_key="listing.row.compact@1",
        class_prefix="ac-listing",
        dom_budget=60,
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-RSP-004",),
    example_fixture_ids=_fixtures("listing.row.compact"),
)


# ---------------------------------------------------------------------------
# profile.* (§5.5, §27.5)
# ---------------------------------------------------------------------------

PROFILE_HEADER_BUSINESS = ComponentDefinition(
    component_id="profile.header.business",
    component_family=ComponentFamily.PROFILE,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Business Profile Header",
    description=(
        "H1 owner on business-profile pages (§9.3) — the functional "
        "replacement for a hero on this page role (§6.1 Hero column: "
        "'F (profile header instead)'). 'badges' (§27.5 RS) are not a "
        "separate slot: verification/claim state renders from the bound "
        "listing_ref per E10 (§6.3), the same 'resolve via the existing "
        "reference' choice listing.card.standard already made."
    ),
    commercial_purpose=CommercialPurpose.ESTABLISH_TRUST,
    secondary_purposes=(CommercialPurpose.ORIENT,),
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_props={
        "listing_ref": PropSpec(
            prop_type=PropType.LISTING_REF,
            description=(
                "Reference to the bound listing's data, incl. "
                "verification_state and claim status (E10)."
            ),
        ),
    },
    required_content_slots={
        "name": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="The business name, rendered as the profile's H1.",
        ),
    },
    optional_content_slots={
        "rating_summary": SlotSpec(
            block_type="RatingSummary",
            cardinality=SlotCardinality.ZERO_OR_ONE,
            description="Aggregate rating summary, when genuine on-page reviews exist.",
        ),
    },
    supported_variants={
        "claimed": VariantSpec(display_name="Claimed"),
        "unclaimed": VariantSpec(display_name="Unclaimed"),
    },
    default_variant="claimed",
    semantic_element=SemanticElement.HEADER,
    allowed_parent_regions=(RegionKind.HERO,),
    design_token_dependencies=(
        "typography.heading.display",
        "color.text.default",
        "color.text.muted",
        "radius.badge",
        "spacing.section.medium",
    ),
    seo_contract=SEOContract(
        heading_levels=(1,),
        content_visibility="always-visible",
        schema_fragments=("LocalBusiness",),
    ),
    directory_contract=DirectoryContract(
        supported_listing_kinds=(
            ListingKind.ORGANIC,
            ListingKind.VERIFIED,
            ListingKind.INCOMPLETE,
        ),
        requires_disclosure=False,
    ),
    analytics_contract=_analytics("profile.header.business"),
    rendering_contract=RenderingContract(
        emitter_key="profile.header.business@1", class_prefix="ac-profile"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-005", "CG-COM-004"),
    example_fixture_ids=_fixtures("profile.header.business"),
)

PROFILE_CONTACT_PANEL = ComponentDefinition(
    component_id="profile.contact.panel",
    component_family=ComponentFamily.PROFILE,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Business Contact Panel",
    description=(
        "Real tel:/mailto: links from the single ContactSpec NAP source "
        "(§13.3, CG-SEO-008). The §27.5 'CTA cluster' RS is deferred: "
        "cta.* is Wave 5 and unregistered (see module docstring) — this "
        "definition declares only the contact_info slot."
    ),
    commercial_purpose=CommercialPurpose.DRIVE_CALL,
    secondary_purposes=(CommercialPurpose.COLLECT_LEAD,),
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_content_slots={
        "contact_info": SlotSpec(
            block_type="ContactSpec",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="E.164 phone, validated email, address struct (§8.4) — the single NAP source.",
        ),
    },
    supported_variants={
        "sidebar": VariantSpec(display_name="Sidebar"),
        "inline": VariantSpec(display_name="Inline"),
    },
    default_variant="sidebar",
    semantic_element=SemanticElement.ASIDE,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.raised",
        "color.text.link",
        "color.text.default",
        "spacing.stack.default",
        "radius.card",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    seo_contract=SEOContract(schema_fragments=("LocalBusiness",)),
    analytics_contract=_analytics("profile.contact.panel", "phone_click"),
    rendering_contract=RenderingContract(
        emitter_key="profile.contact.panel@1", class_prefix="ac-profile"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-008",),
    example_fixture_ids=_fixtures("profile.contact.panel"),
)

PROFILE_HOURS_TABLE = ComponentDefinition(
    component_id="profile.hours.table",
    component_family=ComponentFamily.PROFILE,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Business Hours Table",
    description=(
        "Per-day open/close/closed schedule (§8.4 HoursSpec), rendered as a "
        "real table with header scope (§12.4). 'Open now' computation is "
        "PROHIBITED (clock read, §8.4) — hours render as stated schedule "
        "only."
    ),
    commercial_purpose=CommercialPurpose.REDUCE_UNCERTAINTY,
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_content_slots={
        "hours": SlotSpec(
            block_type="HoursSpec",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Per-day open/close/closed structure; no clock reads.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
    ),
    seo_contract=SEOContract(schema_fragments=("LocalBusiness",)),
    analytics_contract=_analytics("profile.hours.table"),
    rendering_contract=RenderingContract(
        emitter_key="profile.hours.table@1", class_prefix="ac-profile"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-007",),
    example_fixture_ids=_fixtures("profile.hours.table"),
)

PROFILE_AREAS_SERVED = ComponentDefinition(
    component_id="profile.areas.served",
    component_family=ComponentFamily.PROFILE,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Service Areas",
    description=(
        "Service-area link set with areaServed schema capability (§13.2: "
        "'service-area via areaServed on LocalBusiness')."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_LOCAL_SEO,
    secondary_purposes=(CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,),
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_content_slots={
        "area_links": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Service-area link set.",
        ),
    },
    supported_variants={
        "list": VariantSpec(display_name="List"),
        "map-adjacent": VariantSpec(display_name="Map-adjacent"),
    },
    default_variant="list",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.text.link",
        "typography.body.default",
        "spacing.stack.default",
    ),
    seo_contract=SEOContract(
        link_kinds=("internal",), schema_fragments=("LocalBusiness",)
    ),
    analytics_contract=_analytics("profile.areas.served"),
    rendering_contract=RenderingContract(
        emitter_key="profile.areas.served@1", class_prefix="ac-profile"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-005",),
    example_fixture_ids=_fixtures("profile.areas.served"),
)

PROFILE_MAP_DIRECTIONS = ComponentDefinition(
    component_id="profile.map.directions",
    component_family=ComponentFamily.PROFILE,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Map and Directions",
    description=(
        "Static map image with text directions as the primary accessible "
        "path (§12.4); interactive maps are P3 (§25 'Map loading'). "
        "'Address' (§27.5 RS) is not re-declared here — §13.3 requires NAP "
        "from the single ContactSpec block, so this definition reaches "
        "shared listing data via listing_ref instead (see module "
        "docstring) and declares only the two slots genuinely new here."
    ),
    commercial_purpose=CommercialPurpose.REDUCE_UNCERTAINTY,
    secondary_purposes=(CommercialPurpose.ORIENT,),
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_props={
        "listing_ref": PropSpec(
            prop_type=PropType.LISTING_REF,
            description="Reference to the bound listing's ContactSpec (single NAP source, §13.3).",
        ),
    },
    required_content_slots={
        "location": SlotSpec(
            block_type="GeoSpec",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Lat/lng decimals-as-strings + service-area region refs.",
        ),
        "directions_text": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Text directions — the primary accessible path (§12.4).",
        ),
    },
    supported_variants={
        "static-image": VariantSpec(display_name="Static map image"),
    },
    default_variant="static-image",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "aspect.card",
        "color.surface.raised",
        "typography.body.default",
        "color.text.link",
    ),
    analytics_contract=_analytics("profile.map.directions"),
    rendering_contract=RenderingContract(
        emitter_key="profile.map.directions@1", class_prefix="ac-profile"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-010",),
    example_fixture_ids=_fixtures("profile.map.directions"),
)

PROFILE_CREDENTIALS_LIST = ComponentDefinition(
    component_id="profile.credentials.list",
    component_family=ComponentFamily.PROFILE,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Credentials List",
    description=(
        "Issuer + evidence_ref per credential (§8.4 CredentialBlock); "
        "CG-COM-003 requires an evidence_ref on every entry (E2 doctrine "
        "parity)."
    ),
    commercial_purpose=CommercialPurpose.ESTABLISH_TRUST,
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_content_slots={
        "credentials": SlotSpec(
            block_type="CredentialBlock",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Issuer + evidence_ref per credential.",
        ),
    },
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.default",
        "icon.size.sm",
    ),
    analytics_contract=_analytics("profile.credentials.list"),
    rendering_contract=RenderingContract(
        emitter_key="profile.credentials.list@1", class_prefix="ac-profile"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-003",),
    example_fixture_ids=_fixtures("profile.credentials.list"),
)

PROFILE_GALLERY_STANDARD = ComponentDefinition(
    component_id="profile.gallery.standard",
    component_family=ComponentFamily.PROFILE,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Business Photo Gallery",
    description=(
        "The only permitted 'carousel' (§9.2): CSS-only scroll-snap, max "
        "10 items, per-image alt (§12.4). See module docstring for the "
        "'images (1..10)' slot-modeling choice and the CG-CMP gate-ID note."
    ),
    commercial_purpose=CommercialPurpose.INCREASE_ENGAGEMENT,
    secondary_purposes=(CommercialPurpose.ESTABLISH_TRUST,),
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_content_slots={
        "images": SlotSpec(
            block_type="AssetRef",
            cardinality=SlotCardinality.ONE_TO_N,
            max_count=10,
            description="Gallery images, up to the §9.2 carousel cap; each carries per-image alt text.",
        ),
    },
    supported_asset_roles=(AssetRole.GALLERY_IMAGE,),
    supported_variants={
        "scroll-snap": VariantSpec(display_name="Scroll-snap gallery"),
    },
    default_variant="scroll-snap",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "aspect.gallery",
        "spacing.inline.default",
        "radius.card",
    ),
    accessibility_contract=AccessibilityContract(
        # §12.6 Gallery row: list semantics, each image alt-labeled,
        # visible next/prev links (not hover-only), no autoplay.
        state_machine="gallery",
        keyboard_operable=True,
    ),
    analytics_contract=_analytics("profile.gallery.standard"),
    rendering_contract=RenderingContract(
        emitter_key="profile.gallery.standard@1", class_prefix="ac-profile"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-010",),
    example_fixture_ids=_fixtures("profile.gallery.standard"),
)


# ---------------------------------------------------------------------------
# content.description.business (§5.8, §27.5)
# ---------------------------------------------------------------------------

CONTENT_DESCRIPTION_BUSINESS = ComponentDefinition(
    component_id="content.description.business",
    component_family=ComponentFamily.CONTENT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Business Description",
    description=(
        "Business description copy; internal heading structure is "
        "H3-scoped (§9.3 — section containers own H2, components own "
        "H3+)."
    ),
    commercial_purpose=CommercialPurpose.REDUCE_UNCERTAINTY,
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_content_slots={
        "description": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Business description copy.",
        ),
    },
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "typography.heading.3",
        "color.text.default",
        "spacing.stack.default",
    ),
    seo_contract=SEOContract(
        heading_levels=(3,), content_visibility="always-visible"
    ),
    analytics_contract=_analytics("content.description.business"),
    rendering_contract=RenderingContract(
        emitter_key="content.description.business@1", class_prefix="ac-content"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-005",),
    example_fixture_ids=_fixtures("content.description.business"),
)


# Wave 4 export — lexicographic by component_id (§15.2 ordering law). The
# full §27.5 twelve-component inventory: listing.card.standard (registered
# early under amendment A4, §34.3-A4) plus the eleven components delivered
# in this wave.
WAVE4_COMPONENTS: Tuple[ComponentDefinition, ...] = (
    CONTENT_DESCRIPTION_BUSINESS,
    LISTING_CARD_FEATURED,
    LISTING_CARD_SPONSORED,
    LISTING_CARD_STANDARD,
    LISTING_ROW_COMPACT,
    PROFILE_AREAS_SERVED,
    PROFILE_CONTACT_PANEL,
    PROFILE_CREDENTIALS_LIST,
    PROFILE_GALLERY_STANDARD,
    PROFILE_HEADER_BUSINESS,
    PROFILE_HOURS_TABLE,
    PROFILE_MAP_DIRECTIONS,
)
