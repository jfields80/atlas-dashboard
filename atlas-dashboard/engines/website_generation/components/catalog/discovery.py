"""Wave 3 — Directory discovery catalog (AES-WEB-002D; AES-WEB-002 §27.4).

The nine ``hero.*`` / ``directory.*`` / ``status.results.zero`` components
authored exactly from the §27.4 Wave 3 inventory table (IDs, page roles,
required props/slots, variants, notes, major-gate requirements), the §5.2
``hero`` family rules, the §5.3 ``directory.discovery`` family rules, and the
§5.14 ``status`` family rules. Declarative frozen data only — no markup, no
emitters, no selection, no behavior (§2.2).

Documented interpretive resolutions (consistent with the Wave 1/2 precedent
of recording, not guessing):

* ``hero.search.directory``'s §27.4 "RS: h1, subhead, search embed" row lists
  three *required slots*, but a search form is a nested component, not a
  ContentPackage block type (§8.4 defines no "search embed" block). The h1
  and subhead are modeled as real ``required_content_slots``; the search
  embed requirement is satisfied compositionally via
  ``allowed_child_components=("directory.search.primary",)`` and enforced at
  composition/gate time (§9.4), matching the established Wave 2 precedent
  (``status.banner.notification``'s "MUST bind a recovery action" rule is
  likewise gate-enforced on instances, not a contract-schema field).
* ``directory.search.primary``'s §27.4 "RS: labels" row is modeled as a
  required prop using the existing ``A11Y_LABEL`` prop type (§8.1's
  accessible-label prop type — already used for icon-only controls per
  §12.4), not a content slot, because §8.4 defines no "label" block type.
* ``directory.locations.grid``'s §27.4 row lists "tiles, columns" under the
  *variants* column (unlike ``directory.categories.grid``, where "columns"
  is a *prop*) — honored literally, even though it reads as an inconsistency
  between the two sibling rows.

Lifecycle: registered as ``PROPOSED`` — §23 promotion to ACTIVE requires a
complete emitter and full §30.2 fixture set, delivered in a later wave.

Reuses the Wave 1 helpers (``_analytics``, ``_fixtures``, ``_COMPAT``) via
the intra-catalog import path the architecture tests already authorize
(§29.2), rather than re-declaring them.
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
    _COMPAT,
    _analytics,
    _fixtures,
)

# hero.local.standard: "cat, city, cc, service-area" (§27.4), amended
# (PILOT-PTF-1, documented, non-silent per CLAUDE.md's authority-precedence
# rule) to add PageRole.EDITORIAL_GUIDE -- the new PetTripFinder trust-page
# role needs the identical "compact titled hero" shape §27.4 already
# specified for these four roles, and no dedicated hero.* component exists
# for editorial-guide. component_version bumped 1.0.0 -> 1.1.0 below for
# this additive role-support change.
_HERO_LOCAL_ROLES: Tuple[PageRole, ...] = (
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.CITY_CATEGORY,
    PageRole.SERVICE_AREA,
    PageRole.EDITORIAL_GUIDE,
)

# directory.search.primary: "home, cat, city, sr" (§27.4).
_SEARCH_PRIMARY_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.SEARCH_RESULTS,
)

# directory.categories.grid: "home, city" (§27.4).
_CATEGORIES_GRID_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CITY,
)

# directory.locations.grid: "home, cat, regional-hub" (§27.4).
_LOCATIONS_GRID_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CATEGORY,
    PageRole.REGIONAL_HUB,
)

# directory.filters.panel / directory.sort.control / directory.results.summary:
# "cat, cc, sr" (§27.4) — note this excludes city, unlike status.results.zero.
_CAT_CC_SR_ROLES: Tuple[PageRole, ...] = (
    PageRole.CATEGORY,
    PageRole.CITY_CATEGORY,
    PageRole.SEARCH_RESULTS,
)

# status.results.zero: "cat, city, cc, sr" (§27.4) — includes city.
_ZERO_STATE_ROLES: Tuple[PageRole, ...] = (
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.CITY_CATEGORY,
    PageRole.SEARCH_RESULTS,
)


# ---------------------------------------------------------------------------
# hero.* (§5.2, §27.4)
# ---------------------------------------------------------------------------

HERO_SEARCH_DIRECTORY = ComponentDefinition(
    component_id="hero.search.directory",
    component_family=ComponentFamily.HERO,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Directory Search Hero",
    description=(
        "Home-page search-first hero; H1 owner and LCP-eager media (§27.4). "
        "The 'search embed' requirement is satisfied compositionally by "
        "nesting directory.search.primary (see module docstring) rather "
        "than a content slot."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
    secondary_purposes=(
        CommercialPurpose.COMMUNICATE_VALUE,
        CommercialPurpose.ORIENT,
    ),
    supported_page_roles=(PageRole.HOME,),
    required_content_slots={
        "h1": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="The page H1 (hero owns H1 delegation, §9.3).",
        ),
        "subhead": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Supporting subheading text.",
        ),
    },
    supported_variants={
        "centered": VariantSpec(display_name="Centered"),
        "split": VariantSpec(display_name="Split"),
    },
    default_variant="centered",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.HERO,),
    allowed_child_components=("directory.search.primary",),
    design_token_dependencies=(
        "aspect.hero",
        "color.overlay.scrim",
        "typography.heading.display",
        "typography.body.default",
        "color.text.inverse",
        "color.text.default",
    ),
    responsive_contract=ResponsiveContract(image_behavior="aspect.hero"),
    seo_contract=SEOContract(
        heading_levels=(1,),
        content_visibility="always-visible",
    ),
    analytics_contract=_analytics("hero.search.directory"),
    rendering_contract=RenderingContract(
        emitter_key="hero.search.directory@1", class_prefix="ac-hero"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-005",),
    example_fixture_ids=_fixtures("hero.search.directory"),
)

HERO_LOCAL_STANDARD = ComponentDefinition(
    component_id="hero.local.standard",
    component_family=ComponentFamily.HERO,
    component_version="1.1.0",  # PILOT-PTF-1: added PageRole.EDITORIAL_GUIDE support
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Local Hero",
    description=(
        "Compact hero for category/city/city-category/service-area pages; "
        "context_role selects role-appropriate labeling. Programmatic intro "
        "content varies at the content layer, not here (§27.4 note); the "
        "CG-SEO-007 gate watches for thin, duplicated intros across the "
        "programmatic page set."
    ),
    commercial_purpose=CommercialPurpose.COMMUNICATE_VALUE,
    secondary_purposes=(CommercialPurpose.ORIENT,),
    supported_page_roles=_HERO_LOCAL_ROLES,
    required_props={
        "context_role": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=tuple(role.value for role in _HERO_LOCAL_ROLES),
            description="Which of the four hosting page roles this instance labels for.",
        ),
    },
    required_content_slots={
        "h1": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="The page H1.",
        ),
        "intro": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Short programmatic intro (content-layer variation).",
        ),
    },
    supported_variants={
        "standard": VariantSpec(display_name="Standard"),
        "compact": VariantSpec(display_name="Compact"),
    },
    default_variant="standard",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.HERO,),
    design_token_dependencies=(
        "typography.heading.display",
        "typography.body.default",
        "color.text.default",
        "spacing.section.medium",
    ),
    seo_contract=SEOContract(
        heading_levels=(1,),
        content_visibility="always-visible",
    ),
    analytics_contract=_analytics("hero.local.standard"),
    rendering_contract=RenderingContract(
        emitter_key="hero.local.standard@1", class_prefix="ac-hero"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-007",),
    example_fixture_ids=_fixtures("hero.local.standard"),
)


# ---------------------------------------------------------------------------
# directory.* (§5.3, §27.4)
# ---------------------------------------------------------------------------

DIRECTORY_SEARCH_PRIMARY = ComponentDefinition(
    component_id="directory.search.primary",
    component_family=ComponentFamily.DIRECTORY,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Primary Directory Search",
    description=(
        "Real GET search form (§5.3 — MVP filters/search are crawlable "
        "link-based facets, never client-state-only); may nest inside "
        "hero.search.directory (hero-embedded variant) or stand alone."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
    secondary_purposes=(CommercialPurpose.EXPOSE_INVENTORY,),
    supported_page_roles=_SEARCH_PRIMARY_ROLES,
    required_props={
        "action_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="GET form action route (must exist in SiteArchitecture).",
        ),
        "scope": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=tuple(role.value for role in _SEARCH_PRIMARY_ROLES),
            description="Search scope, mirroring the hosting page's role.",
        ),
        "input_label": PropSpec(
            prop_type=PropType.A11Y_LABEL,
            description="Accessible label for the search input (§27.4 'labels').",
        ),
    },
    supported_variants={
        "hero-embedded": VariantSpec(display_name="Hero-embedded"),
        "standalone": VariantSpec(display_name="Standalone"),
        "condensed": VariantSpec(display_name="Condensed"),
    },
    default_variant="standalone",
    semantic_element=SemanticElement.FORM,
    allowed_parent_regions=(RegionKind.HERO, RegionKind.BODY),
    design_token_dependencies=(
        "color.surface.page",
        "color.border.default",
        "color.focus.ring",
        "focus.ring.default",
        "radius.control",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    analytics_contract=_analytics(
        "directory.search.primary", "search_submit"
    ),
    rendering_contract=RenderingContract(
        emitter_key="directory.search.primary@1", class_prefix="ac-directory"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-001",),
    example_fixture_ids=_fixtures("directory.search.primary"),
)

DIRECTORY_CATEGORIES_GRID = ComponentDefinition(
    component_id="directory.categories.grid",
    component_family=ComponentFamily.DIRECTORY,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Categories Discovery Grid",
    description=(
        "Category discovery grid: the internal-link backbone from home/city "
        "pages into the category taxonomy (§27.4). Nests layout.grid.standard "
        "(Wave 1) as its structural substrate."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
    secondary_purposes=(CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,),
    supported_page_roles=_CATEGORIES_GRID_ROLES,
    required_props={
        "category_source_ref": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="SiteArchitecture category-taxonomy topology reference.",
        ),
        "columns": PropSpec(
            prop_type=PropType.INT_BOUNDED,
            int_min=2,
            int_max=4,
            description="Grid column count (§9.2 max 4 desktop).",
        ),
    },
    required_content_slots={
        "category_tiles": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            description="One tile link per category.",
        ),
    },
    supported_variants={
        "tiles": VariantSpec(display_name="Tiles"),
        "chips": VariantSpec(display_name="Chips"),
    },
    default_variant="tiles",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=("layout.grid.standard",),
    design_token_dependencies=(
        "grid.columns.2",
        "grid.columns.3",
        "grid.columns.4",
        "grid.gap.default",
        "color.text.link",
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("directory.categories.grid"),
    rendering_contract=RenderingContract(
        emitter_key="directory.categories.grid@1", class_prefix="ac-directory"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-003", "CG-SEO-004"),
    example_fixture_ids=_fixtures("directory.categories.grid"),
)

DIRECTORY_LOCATIONS_GRID = ComponentDefinition(
    component_id="directory.locations.grid",
    component_family=ComponentFamily.DIRECTORY,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Locations Discovery Grid",
    description=(
        "Location discovery grid: the internal-link backbone into the city/"
        "region taxonomy (§27.4). Nests layout.grid.standard (Wave 1) as its "
        "structural substrate."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
    secondary_purposes=(CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,),
    supported_page_roles=_LOCATIONS_GRID_ROLES,
    required_props={
        "location_source_ref": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="SiteArchitecture location topology reference.",
        ),
    },
    required_content_slots={
        "location_tiles": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            description="One tile link per location.",
        ),
    },
    supported_variants={
        "tiles": VariantSpec(display_name="Tiles"),
        "columns": VariantSpec(display_name="Columns"),
    },
    default_variant="tiles",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=("layout.grid.standard",),
    design_token_dependencies=(
        "grid.columns.2",
        "grid.columns.3",
        "grid.gap.default",
        "color.text.link",
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("directory.locations.grid"),
    rendering_contract=RenderingContract(
        emitter_key="directory.locations.grid@1", class_prefix="ac-directory"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-004",),
    example_fixture_ids=_fixtures("directory.locations.grid"),
)

DIRECTORY_FILTERS_PANEL = ComponentDefinition(
    component_id="directory.filters.panel",
    component_family=ComponentFamily.DIRECTORY,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Filters Panel",
    description=(
        "Link-based facet filters (§5.3 — MVP facets are crawlable links, "
        "never client-state-only); indexable-facet whitelist and crawl-"
        "safety enforced by the SEO Engine/gates, not this contract. The "
        "'drawer' variant carries the §12.6 drawer state machine below md "
        "(§11.5 canonical transformation)."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
    secondary_purposes=(CommercialPurpose.EXPOSE_INVENTORY,),
    supported_page_roles=_CAT_CC_SR_ROLES,
    required_props={
        "facet_set_ref": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="Facet-set reference (indexable-facet whitelist scoped).",
        ),
    },
    supported_variants={
        "sidebar": VariantSpec(display_name="Sidebar"),
        "top-bar": VariantSpec(display_name="Top bar"),
        "drawer": VariantSpec(display_name="Drawer"),
        "chips": VariantSpec(display_name="Chips"),
    },
    default_variant="sidebar",
    semantic_element=SemanticElement.ASIDE,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.raised",
        "color.border.default",
        "color.focus.ring",
        "focus.ring.default",
        "breakpoint.md",
    ),
    responsive_contract=ResponsiveContract(collapse_behavior="drawer-below-md"),
    accessibility_contract=AccessibilityContract(
        # §12.6 Drawer row: closed->open focus moves in, trap active,
        # aria-expanded on trigger, aria-modal on drawer.
        state_machine="drawer",
        keyboard_operable=True,
        focus_management=True,
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics(
        "directory.filters.panel", "filter_apply"
    ),
    rendering_contract=RenderingContract(
        emitter_key="directory.filters.panel@1", class_prefix="ac-directory"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-002", "CG-SEO-006"),
    example_fixture_ids=_fixtures("directory.filters.panel"),
)

DIRECTORY_SORT_CONTROL = ComponentDefinition(
    component_id="directory.sort.control",
    component_family=ComponentFamily.DIRECTORY,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Sort Control",
    description=(
        "Link-based result sort control (§27.4); self-canonical handling "
        "(page=1 / sort-order canonicalization) is the SEO Engine's concern, "
        "never declared here (§13.3)."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
    supported_page_roles=_CAT_CC_SR_ROLES,
    required_props={
        "sort_options_ref": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="Available sort-option set reference.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.text.link",
        "color.text.default",
        "color.focus.ring",
        "focus.ring.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("directory.sort.control", "sort_change"),
    rendering_contract=RenderingContract(
        emitter_key="directory.sort.control@1", class_prefix="ac-directory"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-003",),
    example_fixture_ids=_fixtures("directory.sort.control"),
)

DIRECTORY_RESULTS_SUMMARY = ComponentDefinition(
    component_id="directory.results.summary",
    component_family=ComponentFamily.DIRECTORY,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Results Summary",
    description=(
        "Result-count announcement text (§27.4, §6.2 — search-results "
        "summary text MUST announce result count). Static text in MVP; a "
        "polite live region is a future dynamic-mode enhancement (§5.3), "
        "not declared here."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
    supported_page_roles=_CAT_CC_SR_ROLES,
    required_content_slots={
        "summary_text": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Result-count announcement text.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.muted",
    ),
    analytics_contract=_analytics("directory.results.summary"),
    rendering_contract=RenderingContract(
        emitter_key="directory.results.summary@1", class_prefix="ac-directory"
    ),
    compatibility_range=_COMPAT,
    example_fixture_ids=_fixtures("directory.results.summary"),
)


# ---------------------------------------------------------------------------
# status.results.zero (§5.14, §27.4)
# ---------------------------------------------------------------------------

STATUS_RESULTS_ZERO = ComponentDefinition(
    component_id="status.results.zero",
    component_family=ComponentFamily.STATUS,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Zero Results State",
    description=(
        "Mandatory zero-results state (§6.2 — an inventory-rendering role "
        "that would render zero listings and no state component fails "
        "CG-STR-006, BLOCKING). Recovery links are mandatory content, not "
        "an afterthought (§5.14 — every status component MUST bind at "
        "least one recovery action)."
    ),
    commercial_purpose=CommercialPurpose.SYSTEM_STATUS,
    secondary_purposes=(CommercialPurpose.REDUCE_UNCERTAINTY,),
    supported_page_roles=_ZERO_STATE_ROLES,
    required_content_slots={
        "message": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Zero-results explanation message.",
        ),
        "recovery_links": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Mandatory recovery links (parent category/city, etc.).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.muted",
        "color.text.link",
        "spacing.section.medium",
    ),
    accessibility_contract=AccessibilityContract(live_region_role="status"),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("status.results.zero"),
    rendering_contract=RenderingContract(
        emitter_key="status.results.zero@1", class_prefix="ac-status"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-STR-006",),
    example_fixture_ids=_fixtures("status.results.zero"),
)


# ---------------------------------------------------------------------------
# Wave 3 export — lexicographic by component_id (§15.2 ordering law)
# ---------------------------------------------------------------------------

WAVE3_COMPONENTS: Tuple[ComponentDefinition, ...] = (
    DIRECTORY_CATEGORIES_GRID,
    DIRECTORY_FILTERS_PANEL,
    DIRECTORY_LOCATIONS_GRID,
    DIRECTORY_RESULTS_SUMMARY,
    DIRECTORY_SEARCH_PRIMARY,
    DIRECTORY_SORT_CONTROL,
    HERO_LOCAL_STANDARD,
    HERO_SEARCH_DIRECTORY,
    STATUS_RESULTS_ZERO,
)
