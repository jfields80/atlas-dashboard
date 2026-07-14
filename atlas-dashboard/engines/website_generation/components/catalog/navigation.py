"""Wave 2 — Navigation and shell catalog (AES-WEB-002C; AES-WEB-002 §27.3).

The eight ``nav.*`` / ``legal.footer.*`` / ``status.*`` components authored
exactly from the §27.3 Wave 2 inventory table (IDs, page roles, required
props/slots, variants, notes, major-gate requirements), the §5.1 ``nav``
family rules, the §5.14 ``status`` family rules, the §5.15 ``legal`` family
rules, and the §12.6 interactive state-machine table. Declarative frozen
data only — no markup, no emitters, no selection, no behavior (§2.2).

Landmark ownership (§12.1 — "landmark set exactly one main, one page
header/footer, labeled navs"): ``layout.shell.page`` (Wave 1) already owns
the page's single ``<header>``/``<footer>`` landmarks (§9.1/§9.3). Wave 2's
``nav.header.standard``, ``nav.mobile.drawer``, ``nav.breadcrumbs.standard``,
and ``nav.pagination.standard`` each contribute their own ``<nav>`` landmark
nested within/alongside the shell's header/body regions (hence §5.1's "aria-
label disambiguation required when >1 <nav>" rule); ``legal.footer.directory``
renders as plain content nested *inside* the shell's single ``<footer>``
landmark, not as a second ``<footer>`` element.

Deferred, not invented: nav.header.standard's optional "MAY host exactly one
cta.* slot" capability (§5.1) is not declared here, because ``cta.*``
components do not exist yet (Wave 5, AES-WEB-002F) — this scope boundary is
intentional, not an oversight; the capability will be added as a minor
version bump once cta.* lands. Likewise, status.banner.notification's "MUST
bind at least one recovery action" rule (§5.14) is a gate-enforced instance
requirement (matching the §6.2 CG-STR-006 pattern: contracts declare, gates
enforce on bound manifests), not a contract-schema requirement — the
authority's own Wave 2 table marks the action slot optional.

Reuses the Wave 1 helpers (``_analytics``, ``_fixtures``, ``_COMPAT``,
``_ALL_ROLES``) via the intra-catalog import path the architecture tests
already authorize (§29.2), rather than re-declaring them.

Lifecycle: registered as ``PROPOSED`` — §23 promotion to ACTIVE requires a
complete emitter and full §30.2 fixture set, delivered in a later wave.
"""

from __future__ import annotations

from typing import Tuple

from engines.website_generation.contracts.components import (
    AccessibilityContract,
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
from engines.website_generation.components.catalog.layout_atoms import (
    _ALL_ROLES,
    _COMPAT,
    _analytics,
    _fixtures,
)

# nav.breadcrumbs.standard: "all except home, lg" (§27.3) — every page role
# except home and lead-gen-landing.
_BREADCRUMB_ROLES: Tuple[PageRole, ...] = tuple(
    role
    for role in PageRole
    if role not in (PageRole.HOME, PageRole.LEAD_GEN_LANDING)
)

# nav.utility.bar: "home, cat, city" (§27.3).
_UTILITY_BAR_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CATEGORY,
    PageRole.CITY,
)

# nav.pagination.standard: "cat, city, cc, sr" (§27.3).
_PAGINATION_ROLES: Tuple[PageRole, ...] = (
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.CITY_CATEGORY,
    PageRole.SEARCH_RESULTS,
)


# ---------------------------------------------------------------------------
# nav.* (§5.1, §27.3)
# ---------------------------------------------------------------------------

NAV_SKIP_LINK = ComponentDefinition(
    component_id="nav.skip.link",
    component_family=ComponentFamily.NAV,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Skip Link",
    description=(
        "Skip-to-main-content link; mandatory as the first focusable "
        "element on every page (§5.1, §12.1)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    secondary_purposes=(CommercialPurpose.IMPROVE_ACCESSIBILITY,),
    supported_page_roles=_ALL_ROLES,
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.SKIP,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.focus.ring",
        "focus.ring.default",
        "color.text.link",
    ),
    responsive_contract=ResponsiveContract(touch_target="44px-token"),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
        focus_management=True,
    ),
    analytics_contract=_analytics("nav.skip.link"),
    rendering_contract=RenderingContract(
        emitter_key="nav.skip.link@1", class_prefix="ac-nav"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-011",),
    example_fixture_ids=_fixtures("nav.skip.link"),
)

NAV_HEADER_STANDARD = ComponentDefinition(
    component_id="nav.header.standard",
    component_family=ComponentFamily.NAV,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Standard Header",
    description=(
        "Main site header: nav tree from SiteArchitecture (never hand-"
        "authored per page); no more than one nav.header.* per page (§5.1). "
        "Renders a <nav> landmark nested within the shell's single <header> "
        "landmark region. Logo is optional (AES-WEB-002K.1, D4): no asset "
        "store exists yet, so the emitter degrades to a text wordmark/site "
        "label rather than fabricating an image URL."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    secondary_purposes=(CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,),
    supported_page_roles=_ALL_ROLES,
    required_props={
        "nav_tree": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="SiteArchitecture nav topology reference.",
        ),
    },
    optional_props={
        "logo": PropSpec(
            prop_type=PropType.ASSET_REF,
            description="Logo asset (AssetRole.LOGO); absent renders a text wordmark instead.",
            default="",
        ),
    },
    supported_variants={
        "standard": VariantSpec(display_name="Standard"),
        "condensed": VariantSpec(display_name="Condensed (lg)"),
    },
    default_variant="standard",
    semantic_element=SemanticElement.NAV,
    allowed_parent_regions=(RegionKind.HEADER,),
    allowed_child_components=(),
    supported_asset_roles=(AssetRole.LOGO,),
    design_token_dependencies=(
        "color.surface.page",
        "color.text.default",
        "color.text.link",
        "color.focus.ring",
        "focus.ring.default",
        "breakpoint.md",
    ),
    responsive_contract=ResponsiveContract(
        collapse_behavior="drawer-below-md",
        sticky="none",
    ),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics(
        "nav.header.standard", "component_interaction"
    ),
    rendering_contract=RenderingContract(
        emitter_key="nav.header.standard@1", class_prefix="ac-nav"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-006",),
    example_fixture_ids=_fixtures("nav.header.standard"),
)

NAV_MOBILE_DRAWER = ComponentDefinition(
    component_id="nav.mobile.drawer",
    component_family=ComponentFamily.NAV,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Mobile Nav Drawer",
    description=(
        "Mobile navigation drawer, triggered from nav.header.standard "
        "below md; focus-trap state machine per §12.6; always has a no-JS "
        "baseline (CSS/<details>-driven or minimal budgeted JS, "
        "CG-RND-006)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    secondary_purposes=(CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,),
    supported_page_roles=_ALL_ROLES,
    required_props={
        "nav_tree": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="SiteArchitecture nav topology reference.",
        ),
    },
    semantic_element=SemanticElement.NAV,
    # Overlays/drawers are projected regions owned by their triggering
    # component's contract (§9.1) — triggered from the header region.
    allowed_parent_regions=(RegionKind.HEADER,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.surface.raised",
        "color.overlay.scrim",
        "color.focus.ring",
        "focus.ring.default",
        "breakpoint.md",
    ),
    responsive_contract=ResponsiveContract(
        collapse_behavior="none",
        touch_target="44px-token",
    ),
    accessibility_contract=AccessibilityContract(
        # §12.6 Drawer row: closed->open focus moves in, trap active,
        # aria-expanded on trigger, aria-modal on drawer; Escape/close ->
        # trigger refocused.
        state_machine="drawer",
        keyboard_operable=True,
        focus_management=True,
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics(
        "nav.mobile.drawer", "component_interaction"
    ),
    rendering_contract=RenderingContract(
        emitter_key="nav.mobile.drawer@1", class_prefix="ac-nav"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=(
        "CG-A11Y-002",
        "CG-A11Y-009",
        "CG-RND-006",
    ),
    example_fixture_ids=_fixtures("nav.mobile.drawer"),
)

NAV_BREADCRUMBS_STANDARD = ComponentDefinition(
    component_id="nav.breadcrumbs.standard",
    component_family=ComponentFamily.NAV,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Breadcrumbs",
    description=(
        "Breadcrumb trail; required on every page role except home and "
        "lead-gen-landing (§6.2). Declares BreadcrumbList schema capability "
        "(§13.2); no promotional CTAs permitted inside breadcrumbs (§5.1)."
    ),
    commercial_purpose=CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,
    secondary_purposes=(CommercialPurpose.ORIENT,),
    supported_page_roles=_BREADCRUMB_ROLES,
    required_props={
        "trail": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="Breadcrumb trail reference.",
        ),
    },
    semantic_element=SemanticElement.NAV,
    allowed_parent_regions=(RegionKind.BREADCRUMB,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.text.muted",
        "color.text.link",
        "color.focus.ring",
        "focus.ring.default",
    ),
    responsive_contract=ResponsiveContract(touch_target="44px-token"),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
    ),
    seo_contract=SEOContract(
        link_kinds=("internal",),
        schema_fragments=("BreadcrumbList",),
    ),
    analytics_contract=_analytics("nav.breadcrumbs.standard"),
    rendering_contract=RenderingContract(
        emitter_key="nav.breadcrumbs.standard@1", class_prefix="ac-nav"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-009",),
    example_fixture_ids=_fixtures("nav.breadcrumbs.standard"),
)

NAV_UTILITY_BAR = ComponentDefinition(
    component_id="nav.utility.bar",
    component_family=ComponentFamily.NAV,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Utility Bar",
    description=(
        "Announcement/utility strip for home, category, and city pages "
        "(§27.3); dismissal is P3 (requires state) and is not implemented "
        "in this MVP definition."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_UTILITY_BAR_ROLES,
    required_content_slots={
        "message": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Announcement message content.",
        ),
    },
    optional_content_slots={
        "link": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ZERO_OR_ONE,
            description="Optional accompanying link.",
        ),
    },
    supported_variants={
        "announce": VariantSpec(display_name="Announcement"),
        "disclosure": VariantSpec(display_name="Disclosure"),
    },
    default_variant="announce",
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.ANNOUNCEMENT,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.surface.raised",
        "color.text.default",
        "color.text.link",
    ),
    responsive_contract=ResponsiveContract(),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("nav.utility.bar"),
    rendering_contract=RenderingContract(
        emitter_key="nav.utility.bar@1", class_prefix="ac-nav"
    ),
    compatibility_range=_COMPAT,
    example_fixture_ids=_fixtures("nav.utility.bar"),
)

NAV_PAGINATION_STANDARD = ComponentDefinition(
    component_id="nav.pagination.standard",
    component_family=ComponentFamily.NAV,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Pagination",
    description=(
        "Crawl-safe numbered pagination for category/city/city-category/"
        "search-results pages (§27.3); labeled 'Pagination' with "
        "aria-current='page' on the current page (§12.6)."
    ),
    commercial_purpose=CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,
    secondary_purposes=(CommercialPurpose.ORIENT,),
    supported_page_roles=_PAGINATION_ROLES,
    required_props={
        "page_context": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="Pagination context (current/total pages) reference.",
        ),
    },
    semantic_element=SemanticElement.NAV,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.text.link",
        "color.text.default",
        "color.focus.ring",
        "focus.ring.default",
    ),
    responsive_contract=ResponsiveContract(touch_target="44px-token"),
    accessibility_contract=AccessibilityContract(
        # §12.6 Pagination row: nav labeled "Pagination", aria-current on
        # current.
        state_machine="pagination",
        keyboard_operable=True,
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics(
        "nav.pagination.standard", "pagination_click"
    ),
    rendering_contract=RenderingContract(
        emitter_key="nav.pagination.standard@1", class_prefix="ac-nav"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-009",),
    example_fixture_ids=_fixtures("nav.pagination.standard"),
)


# ---------------------------------------------------------------------------
# legal.footer.* (§5.15, §27.3)
# ---------------------------------------------------------------------------

LEGAL_FOOTER_DIRECTORY = ComponentDefinition(
    component_id="legal.footer.directory",
    component_family=ComponentFamily.LEGAL,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Directory Footer",
    description=(
        "Footer mandatory on every page (§5.15). Legal facts sourced from "
        "BusinessSpec legal footer fields; disclosures must never be "
        "hidden below fold-only visibility tricks. Renders as content "
        "inside the shell's single <footer> landmark, not a second one."
    ),
    commercial_purpose=CommercialPurpose.SATISFY_LEGAL,
    secondary_purposes=(
        CommercialPurpose.ESTABLISH_TRUST,
        CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,
    ),
    supported_page_roles=_ALL_ROLES,
    required_props={
        "nav_tree": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="Footer nav topology reference.",
        ),
    },
    required_content_slots={
        "legal_facts": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Legal facts from BusinessSpec legal footer fields.",
        ),
        "disclosures": SlotSpec(
            block_type="DisclosureBlock",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Mandatory, always-visible disclosure blocks.",
        ),
    },
    supported_variants={
        "standard": VariantSpec(display_name="Standard"),
        "minimal": VariantSpec(display_name="Minimal (lg)"),
    },
    default_variant="standard",
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.FOOTER,),
    allowed_child_components=(),
    design_token_dependencies=(
        "color.surface.inverse",
        "color.text.inverse",
        "color.text.link",
        "color.focus.ring",
        "focus.ring.default",
    ),
    responsive_contract=ResponsiveContract(),
    accessibility_contract=AccessibilityContract(
        keyboard_operable=True,
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("legal.footer.directory"),
    rendering_contract=RenderingContract(
        emitter_key="legal.footer.directory@1", class_prefix="ac-legal"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-006",),
    example_fixture_ids=_fixtures("legal.footer.directory"),
)


# ---------------------------------------------------------------------------
# status.* (§5.14, §27.3)
# ---------------------------------------------------------------------------

STATUS_BANNER_NOTIFICATION = ComponentDefinition(
    component_id="status.banner.notification",
    component_family=ComponentFamily.STATUS,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Notification Banner",
    description=(
        "System/status notification banner (§5.14). The 'MUST bind at "
        "least one recovery action' rule is gate-enforced on bound "
        "instances (matching the §6.2 CG-STR-006 pattern) — the Wave 2 "
        "table itself marks the action slot optional at the contract "
        "level. Severity-to-ARIA-role mapping (role=status vs role=alert, "
        "§12.5) is an emitter-time concern, deferred to the rendering "
        "wave; this definition declares the general-case status role."
    ),
    commercial_purpose=CommercialPurpose.SYSTEM_STATUS,
    secondary_purposes=(CommercialPurpose.REDUCE_UNCERTAINTY,),
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
            description="Notification body content.",
        ),
    },
    optional_content_slots={
        "action": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ZERO_OR_ONE,
            description="Recovery-action link (gate-required in practice).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.ANNOUNCEMENT, RegionKind.BODY),
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
    analytics_contract=_analytics("status.banner.notification"),
    rendering_contract=RenderingContract(
        emitter_key="status.banner.notification@1", class_prefix="ac-status"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-008",),
    example_fixture_ids=_fixtures("status.banner.notification"),
)


# ---------------------------------------------------------------------------
# Wave 2 export — lexicographic by component_id (§15.2 ordering law)
# ---------------------------------------------------------------------------

WAVE2_COMPONENTS: Tuple[ComponentDefinition, ...] = (
    LEGAL_FOOTER_DIRECTORY,
    NAV_BREADCRUMBS_STANDARD,
    NAV_HEADER_STANDARD,
    NAV_MOBILE_DRAWER,
    NAV_PAGINATION_STANDARD,
    NAV_SKIP_LINK,
    NAV_UTILITY_BAR,
    STATUS_BANNER_NOTIFICATION,
)
