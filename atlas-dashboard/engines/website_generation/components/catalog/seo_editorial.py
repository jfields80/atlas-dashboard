"""Wave 6 catalog — Local SEO and Editorial (AES-WEB-002G; AES-WEB-002 §27.7).

The full seven-component §27.7 Wave 6 inventory: the two ``seo.local-links.*``
components and the five ``content.*`` components (``content.intro.contextual``,
``content.section.editorial``, ``content.toc.standard``,
``content.table.comparison``, ``content.resources.grid``). All seven are
declarative frozen data only — no markup, no emitters, no selection, no
behavior (§2.2).

Scope boundary (operator-approved, per the AES-WEB-002G architectural
preflight's Ambiguity Register): this delivery is the Wave 6 component
catalog, registry updates, the five new secondary-role recipe tables,
fixtures, and tests *only*. It does **not**:

* author ``CITY_RECIPE_SLOTS`` or ``CITY_CATEGORY_RECIPE_SLOTS`` (AMB-002G-01
  — the city-category acceptance requirement is satisfied via the
  fixture-only approach: parameterized fixture IDs exercising
  ``seo.local-links.*``/``content.intro.contextual`` against synthetic
  city-category inputs, not a live recipe/selection pipeline run; see
  ``tests/website_generation/components/test_catalog_wave6.py``'s
  ``TestCityCategoryFixtureSet``);
* remove ``_UNBUILT_FAMILY_SENTINEL`` gating or otherwise modify
  ``HOME_RECIPE_SLOTS`` / ``CATEGORY_RECIPE_SLOTS`` /
  ``BUSINESS_PROFILE_RECIPE_SLOTS`` in ``constants/components.py`` (AMB-002G-02
  — recipe integration for already-shipped recipes, including the
  ``editorial_resources`` (home) and ``related_categories_cities`` (category)
  slots this wave's own components could now satisfy, remains deferred to
  the later recipe-integration phase);
* author ``LEAD_GEN_LANDING_RECIPE_SLOTS`` or ``CLAIM_LISTING_RECIPE_SLOTS``
  (unchanged AMB-002F-02 deferral — not this wave's concern either).

Continues the AES-WEB-002B/C/D/E/F precedent unchanged: no ``rendering/`` or
``gates/`` package exists anywhere in this repository yet —
``RenderingContract.emitter_key`` is declared metadata only. Every
definition in this module registers ``PROPOSED``; §23 promotion requires a
complete emitter and full §30.2 fixture set, neither of which this wave
builds.

Role-abbreviation resolution (documented, not guessed): §27.6/§27.7's
"Roles" column uses "guides", which does not appear in §27.1's abbreviation
legend and has no literal ``PageRole`` match. The only candidate is
``PageRole.EDITORIAL_GUIDE`` — already precedented in this repository:
``test_catalog_wave5.py``'s ``EXPECTED_ROLE_COUNTS`` comment for
``content.faq.standard`` ("prof, cat, city, guides" -> counted as 4) already
resolves it identically. Applied the same way here for
``content.section.editorial``, ``content.toc.standard``,
``content.table.comparison``, and ``content.resources.grid``.

Documented interpretive resolutions (consistent with the Wave 1-5 precedent
of recording, not guessing, when §27.7's table under-determines a detail):

* **"link set ref (<=24)"** (both ``seo.local-links.*``): modeled exactly on
  ``directory.categories.grid``'s Wave-3 precedent (§27.4) — a
  ``CONTENT_BLOCK_REF`` prop naming the ``SiteArchitecture`` topology source
  (``city_source_ref`` / ``category_source_ref``), plus a ``LinkSpec``
  content slot carrying the actual link set, capped at the new
  ``SEO_LOCAL_LINKS_MAX_PER_BLOCK`` constant (§5.9: "24 links per block, <=2
  blocks per page" — the per-block half; the per-page half is
  ``SEO_LOCAL_LINKS_MAX_BLOCKS_PER_PAGE``, a page-level/recipe-level
  concern with no single-component home, declared alongside it for the
  eventual gate/recipe consumer). Components never invent URLs (§5.9) — the
  source-ref prop is the binding to ``SiteArchitecture``, not a free value.
* **"RP: context_role"** (``content.intro.contextual``): modeled exactly on
  ``hero.local.standard``'s Wave-3 ``context_role`` precedent (§27.4) — a
  ``STR_ENUM`` over the component's own three hosting roles.
* **"RP: derived heading refs"** (``content.toc.standard``): the TOC derives
  from the *page's own* rendered heading structure, not from
  ``SiteArchitecture`` topology (unlike the ``seo.local-links.*`` source
  refs above). No ``PropType`` value names this concept precisely; modeled
  as ``CONTENT_BLOCK_REF`` by nearest analogy (a reference into
  ``ContentPackage``-derived structure) — a known, flagged limitation
  rather than a silent invention, matching the restraint
  ``cta.sticky.mobile``'s "target" prop showed in the AES-WEB-002F module
  docstring.
* **``semantic_element`` for ``content.toc.standard``**: modeled as ``NAV``
  (an in-page table of contents is a navigation landmark per common ARIA
  authoring practice, and ``SemanticElement`` supports it directly). This
  is a genuine second ``<nav>`` landmark on guide/best-of pages alongside
  ``nav.header.standard``; §9.3's "aria-label disambiguation required when
  >1 ``<nav>``" is rendering/gate work (CG-CMP-006) deferred to when a
  renderer exists, not a contract-level concern here.
* **"RS: typed table"** (``content.table.comparison``): §8.4 names no
  dedicated comparison-table block type (only the general "Lists/tables:
  typed row/cell structures with mandatory header declarations" rule).
  Modeled as ``block_type="ComparisonTableBlock"`` — a new string label
  chosen by the same analogy discipline ``trust.statistics.strip``'s
  ``StatBlock`` and ``content.faq.standard``'s ``QAPair`` used in
  AES-WEB-002F, pending a future Content Engine authority ruling.
  ``SlotSpec.block_type`` is an unconstrained ``str`` at the contract level,
  so this does not violate any frozen contract.
* **``table_adaptation`` for ``content.table.comparison``**: §11.5 requires
  *both* "scroll-x with sticky first column >= md" *and* "stacked label/value
  rows < md" — ``ResponsiveContract.table_adaptation`` is a single field
  (docstring: "∈ {scroll-x, stacked-rows}"), so it cannot express both
  breakpoint behaviors at once without a contract change, which is out of
  scope (frozen contract, §3 Frozen-Contract Register #1). Declared as
  ``"scroll-x"`` (the >= md / enhanced-viewport treatment named first in
  both §11.5 and this component's own §27.7 "Notes" column); the < md
  stacked-rows fallback is recorded here as a known, flagged limitation of
  the single-value field, not a silent invention.
* **"RS: resource cards (<=12)"** (``content.resources.grid``): §8.4 has no
  dedicated "resource card" type either. Modeled via the existing
  ``LinkSpec`` block type (a resource card is fundamentally a titled
  internal link, the same shape ``directory.categories.grid``'s
  ``category_tiles`` slot already uses) rather than inventing a new block
  type — composition over invention, matching the Wave 5 precedent set for
  ``form.*`` "fields". The "<=12" ceiling is inlined directly on the slot's
  ``max_count`` with a citing comment, mirroring ``content.faq.standard``'s
  identical treatment of its own "<=12" ceiling (a component-specific slot
  cardinality, not a cross-component policy constant like the SEO link
  ceilings above).

All seven definitions carry no ``directory_contract`` (none is
listing-kind-bearing) and no ``monetization_contract`` (none is
``ComponentFamily.MONETIZATION``) and no ``conversion_contract`` (none
declares a ``ConversionGoal`` — Wave 6 is discovery/content support, not a
conversion surface; §27.7's table names no goal for any of the seven rows).
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
from engines.website_generation.constants.components import (
    SEO_LOCAL_LINKS_MAX_PER_BLOCK,
)
from engines.website_generation.components.catalog.layout_atoms import (
    _COMPAT,
    _analytics,
    _fixtures,
)

# ---------------------------------------------------------------------------
# Shared role tuples (§27.7)
# ---------------------------------------------------------------------------

_SEO_LOCAL_LINKS_CITIES_ROLES: Tuple[PageRole, ...] = (
    PageRole.CITY,
    PageRole.CITY_CATEGORY,
    PageRole.HOME,
    PageRole.REGIONAL_HUB,
)
_SEO_LOCAL_LINKS_CATEGORIES_ROLES: Tuple[PageRole, ...] = (
    PageRole.CATEGORY,
    PageRole.CITY_CATEGORY,
    PageRole.CITY,
)
_CONTENT_INTRO_CONTEXTUAL_ROLES: Tuple[PageRole, ...] = (
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.CITY_CATEGORY,
)
# "guides" (§27.7) = PageRole.EDITORIAL_GUIDE — see module docstring.
_CONTENT_SECTION_EDITORIAL_ROLES: Tuple[PageRole, ...] = (
    PageRole.EDITORIAL_GUIDE,
    PageRole.BEST_OF,
    PageRole.BUSINESS_PROFILE,
)
_CONTENT_TOC_STANDARD_ROLES: Tuple[PageRole, ...] = (
    PageRole.EDITORIAL_GUIDE,
    PageRole.BEST_OF,
)
_CONTENT_TABLE_COMPARISON_ROLES: Tuple[PageRole, ...] = (
    PageRole.COMPARISON,
    PageRole.BEST_OF,
    PageRole.EDITORIAL_GUIDE,
)
_CONTENT_RESOURCES_GRID_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.EDITORIAL_GUIDE,
)


# ---------------------------------------------------------------------------
# seo.* (§5.9, §27.7)
# ---------------------------------------------------------------------------

SEO_LOCAL_LINKS_CITIES = ComponentDefinition(
    component_id="seo.local-links.cities",
    component_family=ComponentFamily.SEO,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Nearby Cities Links",
    description=(
        "Internal-link block surfacing nearby-city links from "
        "SiteArchitecture topology only (§5.9) — components never invent "
        "URLs. Capped at the §5.9 per-block ceiling."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_LOCAL_SEO,
    secondary_purposes=(CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,),
    supported_page_roles=_SEO_LOCAL_LINKS_CITIES_ROLES,
    required_props={
        "city_source_ref": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="SiteArchitecture nearby-city topology reference.",
        ),
    },
    required_content_slots={
        "city_links": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            max_count=SEO_LOCAL_LINKS_MAX_PER_BLOCK,
            description="Nearby-city link set, capped at the §5.9 ceiling.",
        ),
    },
    supported_variants={
        "grid": VariantSpec(display_name="Grid"),
        "inline-list": VariantSpec(display_name="Inline list"),
    },
    default_variant="grid",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=("layout.grid.standard",),
    design_token_dependencies=(
        "grid.columns.2",
        "grid.columns.3",
        "grid.columns.4",
        "grid.gap.default",
        "color.text.link",
        "typography.label.default",
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("seo.local-links.cities"),
    rendering_contract=RenderingContract(
        emitter_key="seo.local-links.cities@1", class_prefix="ac-seo"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-003", "CG-SEO-004"),
    example_fixture_ids=_fixtures("seo.local-links.cities"),
)

SEO_LOCAL_LINKS_CATEGORIES = ComponentDefinition(
    component_id="seo.local-links.categories",
    component_family=ComponentFamily.SEO,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Related Categories Links",
    description=(
        "Internal-link block surfacing related-category links from "
        "SiteArchitecture topology only (§5.9) — components never invent "
        "URLs. Capped at the §5.9 per-block ceiling."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_LOCAL_SEO,
    secondary_purposes=(CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,),
    supported_page_roles=_SEO_LOCAL_LINKS_CATEGORIES_ROLES,
    required_props={
        "category_source_ref": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="SiteArchitecture related-category topology reference.",
        ),
    },
    required_content_slots={
        "category_links": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            max_count=SEO_LOCAL_LINKS_MAX_PER_BLOCK,
            description="Related-category link set, capped at the §5.9 ceiling.",
        ),
    },
    supported_variants={
        "grid": VariantSpec(display_name="Grid"),
        "inline-list": VariantSpec(display_name="Inline list"),
    },
    default_variant="grid",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=("layout.grid.standard",),
    design_token_dependencies=(
        "grid.columns.2",
        "grid.columns.3",
        "grid.columns.4",
        "grid.gap.default",
        "color.text.link",
        "typography.label.default",
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("seo.local-links.categories"),
    rendering_contract=RenderingContract(
        emitter_key="seo.local-links.categories@1", class_prefix="ac-seo"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-004",),
    example_fixture_ids=_fixtures("seo.local-links.categories"),
)


# ---------------------------------------------------------------------------
# content.* (§5.8, §27.7)
# ---------------------------------------------------------------------------

CONTENT_INTRO_CONTEXTUAL = ComponentDefinition(
    component_id="content.intro.contextual",
    component_family=ComponentFamily.CONTENT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Contextual Intro",
    description=(
        "Programmatic intro copy for category/city/city-category pages; "
        "the primary CG-SEO-007 watchdog surface — thin, duplicated intros "
        "across the programmatic page set are exactly what that gate "
        "watches for. Content varies at the content layer, not here."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_LOCAL_SEO,
    secondary_purposes=(CommercialPurpose.REDUCE_UNCERTAINTY,),
    supported_page_roles=_CONTENT_INTRO_CONTEXTUAL_ROLES,
    required_props={
        "context_role": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=tuple(
                role.value for role in _CONTENT_INTRO_CONTEXTUAL_ROLES
            ),
            description="Which of the three hosting page roles this instance labels for.",
        ),
    },
    required_content_slots={
        "intro": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Programmatic intro copy (content-layer variation).",
        ),
    },
    supported_variants={
        "above-listings": VariantSpec(display_name="Above listings (short)"),
        "below-listings": VariantSpec(display_name="Below listings (long)"),
    },
    default_variant="above-listings",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.default",
        "spacing.stack.default",
    ),
    seo_contract=SEOContract(content_visibility="always-visible"),
    analytics_contract=_analytics("content.intro.contextual"),
    rendering_contract=RenderingContract(
        emitter_key="content.intro.contextual@1", class_prefix="ac-content"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-007",),
    example_fixture_ids=_fixtures("content.intro.contextual"),
)

CONTENT_SECTION_EDITORIAL = ComponentDefinition(
    component_id="content.section.editorial",
    component_family=ComponentFamily.CONTENT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Editorial Section",
    description=(
        "General-purpose editorial rich-text section for guide/best-of/"
        "profile pages; H2/H3 discipline per §9.3 (section containers own "
        "H2, this component owns H3+ internally)."
    ),
    commercial_purpose=CommercialPurpose.REDUCE_UNCERTAINTY,
    secondary_purposes=(CommercialPurpose.SUPPORT_LOCAL_SEO,),
    supported_page_roles=_CONTENT_SECTION_EDITORIAL_ROLES,
    required_content_slots={
        "body": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Editorial section copy.",
        ),
    },
    supported_variants={
        "standard": VariantSpec(display_name="Standard"),
        "callout": VariantSpec(display_name="Callout"),
    },
    default_variant="standard",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.heading.2",
        "typography.heading.3",
        "typography.body.default",
        "color.text.default",
        "spacing.stack.default",
    ),
    seo_contract=SEOContract(
        heading_levels=(2, 3), content_visibility="always-visible"
    ),
    analytics_contract=_analytics("content.section.editorial"),
    rendering_contract=RenderingContract(
        emitter_key="content.section.editorial@1", class_prefix="ac-content"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-005",),
    example_fixture_ids=_fixtures("content.section.editorial"),
)

CONTENT_TOC_STANDARD = ComponentDefinition(
    component_id="content.toc.standard",
    component_family=ComponentFamily.CONTENT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Table of Contents",
    description=(
        "Jump-navigation table of contents derived from the page's own "
        "heading structure (see module docstring re: heading_refs prop "
        "modeling); collapses to jump-select < md (§11.5)."
    ),
    commercial_purpose=CommercialPurpose.ORIENT,
    supported_page_roles=_CONTENT_TOC_STANDARD_ROLES,
    required_props={
        "heading_refs": PropSpec(
            prop_type=PropType.CONTENT_BLOCK_REF,
            description="Reference to the page's derived heading structure.",
        ),
    },
    supported_variants={
        "sidebar": VariantSpec(display_name="Sidebar"),
        "top": VariantSpec(display_name="Top"),
    },
    default_variant="sidebar",
    semantic_element=SemanticElement.NAV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.label.default",
        "color.text.link",
        "spacing.stack.default",
    ),
    responsive_contract=ResponsiveContract(collapse_behavior="jump-select"),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    analytics_contract=_analytics("content.toc.standard"),
    rendering_contract=RenderingContract(
        emitter_key="content.toc.standard@1", class_prefix="ac-content"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-RSP-003",),
    example_fixture_ids=_fixtures("content.toc.standard"),
)

CONTENT_TABLE_COMPARISON = ComponentDefinition(
    component_id="content.table.comparison",
    component_family=ComponentFamily.CONTENT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Comparison Table",
    description=(
        "Typed comparison table with mandatory header-row declarations "
        "(§8.4; see module docstring re: ComparisonTableBlock modeling). "
        "Sticky first column >= md, stacked rows < md (§11.5, §26.7)."
    ),
    commercial_purpose=CommercialPurpose.SUPPORT_COMPARISON,
    secondary_purposes=(CommercialPurpose.REDUCE_UNCERTAINTY,),
    supported_page_roles=_CONTENT_TABLE_COMPARISON_ROLES,
    required_content_slots={
        "table": SlotSpec(
            block_type="ComparisonTableBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Typed row/cell structure with mandatory header rows (§8.4).",
        ),
    },
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
    ),
    responsive_contract=ResponsiveContract(table_adaptation="scroll-x"),
    analytics_contract=_analytics("content.table.comparison"),
    rendering_contract=RenderingContract(
        emitter_key="content.table.comparison@1", class_prefix="ac-content"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-RSP-004",),
    example_fixture_ids=_fixtures("content.table.comparison"),
)

CONTENT_RESOURCES_GRID = ComponentDefinition(
    component_id="content.resources.grid",
    component_family=ComponentFamily.CONTENT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Resources Grid",
    description=(
        "Internal-link support grid of resource cards, modeled via the "
        "existing LinkSpec block type rather than an invented card type "
        "(see module docstring). Capped at the §27.7 ceiling of 12."
    ),
    commercial_purpose=CommercialPurpose.STRENGTHEN_INTERNAL_LINKING,
    secondary_purposes=(CommercialPurpose.SUPPORT_DISCOVERY,),
    supported_page_roles=_CONTENT_RESOURCES_GRID_ROLES,
    required_content_slots={
        "resources": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            max_count=12,  # §27.7 "resource cards (<=12)".
            description="Resource-link cards, up to the §27.7 ceiling of 12.",
        ),
    },
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    allowed_child_components=("layout.grid.standard",),
    design_token_dependencies=(
        "grid.columns.2",
        "grid.columns.3",
        "grid.columns.4",
        "grid.gap.default",
        "color.text.link",
        "typography.body.default",
    ),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("content.resources.grid"),
    rendering_contract=RenderingContract(
        emitter_key="content.resources.grid@1", class_prefix="ac-content"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-SEO-003",),
    example_fixture_ids=_fixtures("content.resources.grid"),
)


# Wave 6 export — lexicographic by component_id (§15.2 ordering law). The
# full §27.7 seven-component inventory.
WAVE6_COMPONENTS: Tuple[ComponentDefinition, ...] = (
    CONTENT_INTRO_CONTEXTUAL,
    CONTENT_RESOURCES_GRID,
    CONTENT_SECTION_EDITORIAL,
    CONTENT_TABLE_COMPARISON,
    CONTENT_TOC_STANDARD,
    SEO_LOCAL_LINKS_CATEGORIES,
    SEO_LOCAL_LINKS_CITIES,
)
