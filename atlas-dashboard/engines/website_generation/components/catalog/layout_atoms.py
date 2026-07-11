"""Wave 1 — Foundation primitives catalog (AES-WEB-002B; AES-WEB-002 §27.2).

The fifteen ``layout.*`` / ``atom.*`` foundation components (§5.16), authored
exactly from the §27.2 Wave 1 inventory table: IDs, required props/slots,
variants, notes, and major-gate requirements. Declarative frozen data only —
no markup, no emitters, no selection, no behavior (§2.2).

Import matrix (§29.2): catalog modules import only ``contracts/`` and
``constants/``.

Lifecycle: registered as ``PROPOSED``. §23 promotion to ACTIVE requires a
complete emitter, full §30.2 fixture set, and verified contracts — the
emitter/snapshot portion of the 002B wave is delivered separately, and per
the Atlas never-report-unbuilt-work-as-complete doctrine these definitions
do not claim ACTIVE until those exist and the operator approves promotion.

Token dependencies are semantic token IDs from the §10.2 taxonomy. Gate IDs
in ``quality_gate_requirements`` come verbatim from the §27.2 "Major gates"
column; the gates themselves are registered in AES-WEB-002I. Fixture IDs
follow the §30.2 grammar (``fx-<id>-min`` …); fixture artifacts accumulate
through waves B–H per §31.
"""

from __future__ import annotations

from typing import Tuple

from engines.website_generation.contracts.components import (
    AccessibilityContract,
    AnalyticsContract,
    ComponentDefinition,
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
    LifecycleStatus,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
)

# Every page role (§27.2 "ALL"), in PageRole declaration order (stable).
_ALL_ROLES: Tuple[PageRole, ...] = tuple(PageRole)

# Form-hosting roles (§5.13): profile, lead-gen landing, claim, submission,
# correction, sponsor pages — the §27.2 "forms" abbreviation.
_FORM_ROLES: Tuple[PageRole, ...] = (
    PageRole.BUSINESS_PROFILE,
    PageRole.LEAD_GEN_LANDING,
    PageRole.CLAIM_LISTING,
    PageRole.SPONSOR_PAGE,
    PageRole.SUBMISSION,
    PageRole.CORRECTION,
)

# All composition regions — foundation primitives are the composition
# substrate (§5.16) and may appear in any region; composition-law policing
# is gate work (§21.2), not catalog data.
_ALL_REGIONS: Tuple[RegionKind, ...] = tuple(RegionKind)

# Compatibility pins (§22.1): Wave 1 targets the 1.x renderer, token schema,
# and registry schema.
_COMPAT = {
    "renderer": ">=1.0.0,<2.0.0",
    "token_schema": ">=1.0.0,<2.0.0",
    "registry_schema": ">=1.0.0,<2.0.0",
}


def _fixtures(component_id: str) -> Tuple[str, ...]:
    """The §30.2 registration-minimum fixture IDs for one component."""
    return (
        "fx-%s-min" % component_id,
        "fx-%s-full" % component_id,
        "fx-%s-bad-prop" % component_id,
        "fx-%s-bad-slot" % component_id,
        "fx-%s-mobile" % component_id,
        "fx-%s-long" % component_id,
        "fx-%s-a11y" % component_id,
    )


def _analytics(component_id: str, *events: str) -> AnalyticsContract:
    """AnalyticsContract with the §18.1 slug rule (dots → dashes)."""
    return AnalyticsContract(
        impression_id=component_id.replace(".", "-"),
        interaction_events=tuple(events),
    )


# ---------------------------------------------------------------------------
# layout.* — structural primitives (§27.2 rows 1–6)
# ---------------------------------------------------------------------------

LAYOUT_SHELL_PAGE = ComponentDefinition(
    component_id="layout.shell.page",
    component_family=ComponentFamily.LAYOUT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Page Shell",
    description=(
        "Root page shell: owns the landmark skeleton (header/main/footer), "
        "H1 delegation, and the head/JSON-LD injection points (§9.1, §9.3)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "page_role": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=tuple(role.value for role in PageRole),
            description="The SiteArchitecture-assigned role of the page.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(),  # the shell is the composition root
    allowed_child_components=("*",),
    design_token_dependencies=(
        "container.width.default",
        "color.surface.page",
        "color.text.default",
    ),
    responsive_contract=ResponsiveContract(
        collapse_behavior="none",
        touch_target="44px-token",
    ),
    accessibility_contract=AccessibilityContract(
        state_machine="",
        keyboard_operable=False,
        focus_management=False,
    ),
    seo_contract=SEOContract(
        heading_levels=(1,),  # H1 delegation owner (§9.3)
        content_visibility="always-visible",
    ),
    analytics_contract=_analytics("layout.shell.page"),
    rendering_contract=RenderingContract(
        emitter_key="layout.shell.page@1", class_prefix="ac-layout"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-005", "CG-CMP-006"),
    example_fixture_ids=_fixtures("layout.shell.page"),
)

LAYOUT_SECTION_CONTAINER = ComponentDefinition(
    component_id="layout.section.container",
    component_family=ComponentFamily.LAYOUT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Section Container",
    description=(
        "Body section container: owns the section H2 and parental section "
        "spacing (§9.3 — spacing is parental, never child-declared)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "width": PropSpec(
            prop_type=PropType.TOKEN_REF,
            default="container.width.default",
            description="Container width token.",
        ),
        "section_spacing": PropSpec(
            prop_type=PropType.TOKEN_REF,
            default="spacing.section.medium",
            description="Parental section spacing token.",
        ),
    },
    optional_content_slots={
        "heading": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.ZERO_OR_ONE,
            description="Optional section heading (H2, §9.3).",
        ),
    },
    supported_variants={
        "standard": VariantSpec(display_name="Standard"),
        "band": VariantSpec(display_name="Full-bleed surface band"),
    },
    default_variant="standard",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=("*",),
    design_token_dependencies=(
        "container.width.default",
        "spacing.section.small",
        "spacing.section.medium",
        "spacing.section.large",
        "color.surface.page",
        "color.surface.raised",
    ),
    responsive_contract=ResponsiveContract(collapse_behavior="none"),
    seo_contract=SEOContract(heading_levels=(2,)),
    analytics_contract=_analytics("layout.section.container"),
    rendering_contract=RenderingContract(
        emitter_key="layout.section.container@1", class_prefix="ac-layout"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-005",),
    example_fixture_ids=_fixtures("layout.section.container"),
)

LAYOUT_GRID_STANDARD = ComponentDefinition(
    component_id="layout.grid.standard",
    component_family=ComponentFamily.LAYOUT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Grid",
    description=(
        "Column grid (2–4 columns) with token gap; collapses per the §11 "
        "responsive law and owns its children's grid spacing."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "columns": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("2", "3", "4"),
            description="Desktop column count (§9.2: max 4).",
        ),
        "gap": PropSpec(
            prop_type=PropType.TOKEN_REF,
            default="grid.gap.default",
            description="Grid gap token.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY, RegionKind.HERO, RegionKind.FOOTER),
    allowed_child_components=("*",),
    design_token_dependencies=(
        "grid.columns.2",
        "grid.columns.3",
        "grid.columns.4",
        "grid.gap.default",
        "breakpoint.sm",
        "breakpoint.md",
        "breakpoint.lg",
    ),
    responsive_contract=ResponsiveContract(
        collapse_behavior="grid-to-stack",
        mobile_order="dom-order",
    ),
    analytics_contract=_analytics("layout.grid.standard"),
    rendering_contract=RenderingContract(
        emitter_key="layout.grid.standard@1", class_prefix="ac-layout"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-RSP-002",),
    example_fixture_ids=_fixtures("layout.grid.standard"),
)

LAYOUT_STACK_STANDARD = ComponentDefinition(
    component_id="layout.stack.standard",
    component_family=ComponentFamily.LAYOUT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Stack",
    description="Vertical rhythm owner: stacks children at a token gap.",
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "gap": PropSpec(
            prop_type=PropType.TOKEN_REF,
            default="spacing.stack.default",
            description="Vertical stack gap token.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY, RegionKind.HERO, RegionKind.FOOTER),
    allowed_child_components=("*",),
    design_token_dependencies=("spacing.stack.default",),
    responsive_contract=ResponsiveContract(collapse_behavior="none"),
    analytics_contract=_analytics("layout.stack.standard"),
    rendering_contract=RenderingContract(
        emitter_key="layout.stack.standard@1", class_prefix="ac-layout"
    ),
    compatibility_range=_COMPAT,
    example_fixture_ids=_fixtures("layout.stack.standard"),
)

LAYOUT_SPLIT_STANDARD = ComponentDefinition(
    component_id="layout.split.standard",
    component_family=ComponentFamily.LAYOUT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Split",
    description=(
        "Two-region split at a declared ratio; stacks below the md "
        "breakpoint (§11.5) with an explicit mobile order."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "ratio": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("50-50", "60-40", "40-60", "66-33", "33-66"),
            description="Desktop split ratio.",
        ),
        "mobile_order": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("dom-order", "media-first", "content-first"),
            default="dom-order",
            description="Stacking order below md (§11.3 mobile_order).",
        ),
    },
    supported_variants={
        "media-left": VariantSpec(display_name="Media left"),
        "media-right": VariantSpec(display_name="Media right"),
    },
    default_variant="media-left",
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY, RegionKind.HERO),
    allowed_child_components=("*",),
    design_token_dependencies=(
        "grid.gap.default",
        "breakpoint.md",
    ),
    responsive_contract=ResponsiveContract(
        collapse_behavior="stack-below-md",
        mobile_order="dom-order",
    ),
    analytics_contract=_analytics("layout.split.standard"),
    rendering_contract=RenderingContract(
        emitter_key="layout.split.standard@1", class_prefix="ac-layout"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-RSP-003",),
    example_fixture_ids=_fixtures("layout.split.standard"),
)

LAYOUT_CARD_SHELL = ComponentDefinition(
    component_id="layout.card.shell",
    component_family=ComponentFamily.LAYOUT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Card Shell",
    description=(
        "Pure surface card shell; the flagged card-in-card exception holder "
        "(§9.4 — the only permitted outer card, as pure surface)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "surface": PropSpec(
            prop_type=PropType.TOKEN_REF,
            default="color.surface.raised",
            description="Surface color token.",
        ),
        "radius": PropSpec(
            prop_type=PropType.TOKEN_REF,
            default="radius.card",
            description="Corner radius token.",
        ),
    },
    supported_variants={
        "raised": VariantSpec(display_name="Raised"),
        "flat": VariantSpec(display_name="Flat"),
    },
    default_variant="raised",
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY, RegionKind.HERO, RegionKind.FOOTER),
    allowed_child_components=("*",),
    design_token_dependencies=(
        "color.surface.raised",
        "radius.card",
        "shadow.raised",
        "border.default",
    ),
    responsive_contract=ResponsiveContract(collapse_behavior="none"),
    analytics_contract=_analytics("layout.card.shell"),
    rendering_contract=RenderingContract(
        emitter_key="layout.card.shell@1", class_prefix="ac-layout"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-004",),
    example_fixture_ids=_fixtures("layout.card.shell"),
)

# ---------------------------------------------------------------------------
# atom.* — atomic primitives (§27.2 rows 7–15)
# ---------------------------------------------------------------------------

ATOM_BUTTON_ACTION = ComponentDefinition(
    component_id="atom.button.action",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Action Button",
    description=(
        "Action button primitive with weight hierarchy; 44px touch target "
        "and mandatory focus ring (§12.2)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "weight": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("primary", "secondary", "ghost"),
            description="Visual weight (§16.3 CTA hierarchy substrate).",
        ),
    },
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Button label text.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=_ALL_REGIONS,
    allowed_child_components=(),
    design_token_dependencies=(
        "color.action.primary",
        "color.action.secondary",
        "color.action.primary.hover",
        "color.action.primary.active",
        "color.action.primary.disabled",
        "color.focus.ring",
        "focus.ring.default",
        "radius.control",
    ),
    responsive_contract=ResponsiveContract(touch_target="44px-token"),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
        focus_management=True,
    ),
    analytics_contract=_analytics(
        "atom.button.action", "component_interaction"
    ),
    rendering_contract=RenderingContract(
        emitter_key="atom.button.action@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-003", "CG-A11Y-005"),
    example_fixture_ids=_fixtures("atom.button.action"),
)

ATOM_LINK_STANDARD = ComponentDefinition(
    component_id="atom.link.standard",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Link",
    description=(
        "Link primitive bound to a LinkSpec; rel attributes derive from the "
        "LinkSpec link kind (§8.4, §13.3)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "link": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="LinkSpec content block reference.",
        ),
    },
    supported_variants={
        "inline": VariantSpec(display_name="Inline"),
        "standalone": VariantSpec(display_name="Standalone"),
    },
    default_variant="inline",
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=_ALL_REGIONS,
    allowed_child_components=(),
    design_token_dependencies=(
        "color.text.link",
        "color.focus.ring",
        "focus.ring.default",
    ),
    responsive_contract=ResponsiveContract(touch_target="44px-token"),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
        focus_management=True,
    ),
    seo_contract=SEOContract(
        link_kinds=("internal", "outbound", "sponsored", "nofollow"),
    ),
    analytics_contract=_analytics(
        "atom.link.standard", "component_interaction", "outbound_click"
    ),
    rendering_contract=RenderingContract(
        emitter_key="atom.link.standard@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-002", "CG-SEO-003"),
    example_fixture_ids=_fixtures("atom.link.standard"),
)

ATOM_IMAGE_RESPONSIVE = ComponentDefinition(
    component_id="atom.image.responsive",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Responsive Image",
    description=(
        "Responsive image primitive: CAS asset by hash, explicit "
        "width/height (CLS-safe), srcset from renditions, alt from content "
        "(§12.4, §25)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "asset": PropSpec(
            prop_type=PropType.ASSET_REF,
            description="CAS image asset reference.",
        ),
        "aspect": PropSpec(
            prop_type=PropType.TOKEN_REF,
            default="aspect.card",
            description="Aspect-ratio token.",
        ),
        "loading": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("eager", "lazy"),
            default="lazy",
            description="Loading policy; LCP/hero images are eager (§25).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=_ALL_REGIONS,
    allowed_child_components=(),
    supported_asset_roles=(AssetRole.HERO_IMAGE, AssetRole.GALLERY_IMAGE),
    design_token_dependencies=(
        "aspect.card",
        "aspect.hero",
        "aspect.gallery",
        "image.treatment.default",
    ),
    responsive_contract=ResponsiveContract(
        image_behavior="srcset-from-renditions",
    ),
    analytics_contract=_analytics("atom.image.responsive"),
    rendering_contract=RenderingContract(
        emitter_key="atom.image.responsive@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-010", "CG-RSP-005"),
    example_fixture_ids=_fixtures("atom.image.responsive"),
)

ATOM_ICON_STANDARD = ComponentDefinition(
    component_id="atom.icon.standard",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Icon",
    description=(
        "Icon primitive: registered SVG asset by hash; labeled via "
        "A11Y_LABEL or declared decorative (aria-hidden) — §12.4."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    secondary_purposes=(CommercialPurpose.IMPROVE_ACCESSIBILITY,),
    supported_page_roles=_ALL_ROLES,
    required_props={
        "asset": PropSpec(
            prop_type=PropType.ASSET_REF,
            description="CAS icon asset reference (AssetRole.ICON).",
        ),
        "size": PropSpec(
            prop_type=PropType.TOKEN_REF,
            default="icon.size.md",
            description="Icon size token.",
        ),
    },
    optional_props={
        "icon_label": PropSpec(
            prop_type=PropType.A11Y_LABEL,
            default="",
            description="Accessible label; required unless decorative.",
        ),
        "decorative": PropSpec(
            prop_type=PropType.BOOL,
            default="false",
            description="Decorative icons render aria-hidden (§12.4).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=_ALL_REGIONS,
    allowed_child_components=(),
    supported_asset_roles=(AssetRole.ICON,),
    design_token_dependencies=(
        "icon.size.sm",
        "icon.size.md",
        "icon.size.lg",
    ),
    responsive_contract=ResponsiveContract(),
    accessibility_contract=AccessibilityContract(
        required_labels=("icon_label",),
    ),
    analytics_contract=_analytics("atom.icon.standard"),
    rendering_contract=RenderingContract(
        emitter_key="atom.icon.standard@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-001",),
    example_fixture_ids=_fixtures("atom.icon.standard"),
)

ATOM_BADGE_STATUS = ComponentDefinition(
    component_id="atom.badge.status",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Status Badge",
    description=(
        "Status badge primitive; kind maps to a surface token and never "
        "fakes verification/paid states (E10, §6.3 non-confusion rule)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_ALL_ROLES,
    required_props={
        "kind": PropSpec(
            prop_type=PropType.STR_ENUM,
            # Lowercase-kebab projections of the §6.3 badge-bearing
            # ListingKind states.
            enum_values=(
                "verified",
                "featured",
                "sponsored",
                "editorial-pick",
                "ranked",
                "curated",
                "recently-added",
                "incomplete",
            ),
            description="Badge kind; drives the surface token.",
        ),
    },
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Visible badge label.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=_ALL_REGIONS,
    allowed_child_components=(),
    design_token_dependencies=(
        "color.surface.sponsored",
        "color.surface.featured",
        "radius.badge",
        "typography.label.default",
    ),
    responsive_contract=ResponsiveContract(),
    analytics_contract=_analytics("atom.badge.status"),
    rendering_contract=RenderingContract(
        emitter_key="atom.badge.status@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-004",),
    example_fixture_ids=_fixtures("atom.badge.status"),
)

ATOM_ALERT_NOTICE = ComponentDefinition(
    component_id="atom.alert.notice",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Alert Notice",
    description=(
        "Notice primitive; severity selects role=status vs role=alert "
        "(§12.5) and the surface treatment."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    secondary_purposes=(CommercialPurpose.IMPROVE_ACCESSIBILITY,),
    supported_page_roles=_ALL_ROLES,
    required_props={
        "severity": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("info", "success", "warning", "error"),
            description="Notice severity.",
        ),
    },
    required_content_slots={
        "body": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Notice body content.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=_ALL_REGIONS,
    allowed_child_components=(),
    design_token_dependencies=(
        "color.text.error",
        "color.text.success",
        "color.border.default",
        "radius.control",
    ),
    responsive_contract=ResponsiveContract(),
    accessibility_contract=AccessibilityContract(
        live_region_role="status",
    ),
    analytics_contract=_analytics("atom.alert.notice"),
    rendering_contract=RenderingContract(
        emitter_key="atom.alert.notice@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-008",),
    example_fixture_ids=_fixtures("atom.alert.notice"),
)

ATOM_FIELD_TEXT = ComponentDefinition(
    component_id="atom.field.text",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Text Field",
    description=(
        "Text input primitive: programmatic label association, "
        "described-by instruction linkage, autocomplete on identity fields "
        "(§12.3)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    secondary_purposes=(CommercialPurpose.IMPROVE_ACCESSIBILITY,),
    supported_page_roles=_FORM_ROLES,
    required_props={
        "input_kind": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("text", "email", "tel", "url", "number"),
            description="Input kind.",
        ),
        "autocomplete": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=(
                "name",
                "email",
                "tel",
                "street-address",
                "postal-code",
                "organization",
                "off",
            ),
            default="off",
            description="HTML autocomplete token (§12.3 identity fields).",
        ),
        "required": PropSpec(
            prop_type=PropType.BOOL,
            default="false",
            description="Whether the field is required.",
        ),
    },
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Programmatic field label.",
        ),
        "error": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Inline error message content (associated).",
        ),
    },
    optional_content_slots={
        "instructions": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.ZERO_OR_ONE,
            description="Instructions preceding the field (described-by).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.border.default",
        "color.border.strong",
        "color.text.error",
        "color.focus.ring",
        "focus.ring.default",
        "radius.control",
        "typography.label.default",
    ),
    responsive_contract=ResponsiveContract(touch_target="44px-token"),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
        focus_management=True,
    ),
    analytics_contract=_analytics(
        "atom.field.text", "component_interaction"
    ),
    rendering_contract=RenderingContract(
        emitter_key="atom.field.text@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-001", "CG-A11Y-012"),
    example_fixture_ids=_fixtures("atom.field.text"),
)

ATOM_FIELD_SELECT = ComponentDefinition(
    component_id="atom.field.select",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Select Field",
    description=(
        "Native select primitive with programmatic label; options bound "
        "from a typed content block (never free-typed)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    secondary_purposes=(CommercialPurpose.IMPROVE_ACCESSIBILITY,),
    supported_page_roles=_FORM_ROLES,
    required_props={
        "options": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="Typed option-set content block reference.",
        ),
        "required": PropSpec(
            prop_type=PropType.BOOL,
            default="false",
            description="Whether the field is required.",
        ),
    },
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Programmatic field label.",
        ),
        "error": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Inline error message content (associated).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.border.default",
        "color.focus.ring",
        "focus.ring.default",
        "radius.control",
        "typography.label.default",
    ),
    responsive_contract=ResponsiveContract(touch_target="44px-token"),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
        focus_management=True,
    ),
    analytics_contract=_analytics(
        "atom.field.select", "component_interaction"
    ),
    rendering_contract=RenderingContract(
        emitter_key="atom.field.select@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-001",),
    example_fixture_ids=_fixtures("atom.field.select"),
)

ATOM_FIELD_CHOICE = ComponentDefinition(
    component_id="atom.field.choice",
    component_family=ComponentFamily.ATOM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Choice Field",
    description=(
        "Radio/checkbox group primitive: fieldset/legend grouping; consent "
        "controls present equal-weight actions and are never pre-checked "
        "(E8, §12.3)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    secondary_purposes=(CommercialPurpose.IMPROVE_ACCESSIBILITY,),
    supported_page_roles=_FORM_ROLES,
    required_props={
        "mode": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("radio", "checkbox"),
            description="Choice mode.",
        ),
        "options": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="Typed option-set content block reference.",
        ),
    },
    required_content_slots={
        "legend": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Fieldset legend (§12.3).",
        ),
        "error": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Inline error message content (associated).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.border.default",
        "color.focus.ring",
        "focus.ring.default",
        "typography.label.default",
    ),
    responsive_contract=ResponsiveContract(touch_target="44px-token"),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
        focus_management=True,
    ),
    analytics_contract=_analytics(
        "atom.field.choice", "component_interaction"
    ),
    rendering_contract=RenderingContract(
        emitter_key="atom.field.choice@1", class_prefix="ac-atom"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-007",),
    example_fixture_ids=_fixtures("atom.field.choice"),
)

# ---------------------------------------------------------------------------
# Wave 1 export — lexicographic by component_id (§15.2 ordering law)
# ---------------------------------------------------------------------------

WAVE1_COMPONENTS: Tuple[ComponentDefinition, ...] = (
    ATOM_ALERT_NOTICE,
    ATOM_BADGE_STATUS,
    ATOM_BUTTON_ACTION,
    ATOM_FIELD_CHOICE,
    ATOM_FIELD_SELECT,
    ATOM_FIELD_TEXT,
    ATOM_ICON_STANDARD,
    ATOM_IMAGE_RESPONSIVE,
    ATOM_LINK_STANDARD,
    LAYOUT_CARD_SHELL,
    LAYOUT_GRID_STANDARD,
    LAYOUT_SECTION_CONTAINER,
    LAYOUT_SHELL_PAGE,
    LAYOUT_SPLIT_STANDARD,
    LAYOUT_STACK_STANDARD,
)
