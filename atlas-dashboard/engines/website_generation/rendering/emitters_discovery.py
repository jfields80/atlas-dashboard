"""Pure HTML emitters for the ``hero.*``/``directory.*``/
``status.results.zero`` discovery components (AES-WEB-002 §27.4; catalog:
``components/catalog/discovery.py``).

Nine components, nine emitter functions, one explicit ``Dict[str,
EmitterFn]`` table (``DISCOVERY_EMITTERS``) -- see
``emitters_layout_atoms.py``'s module docstring for the shared conventions
this module also follows.

Prop-reference resolution convention (AES-WEB-002J.8, documented): a prop's
declared ``PropType`` determines how its string value is used, applied
uniformly across every emitter in this delivery --

* ``CONTENT_BLOCK_REF``: the value is a slot id resolved against
  ``ContentPackage`` (same mechanism as a declared content slot; see
  ``renderer.py``).
* ``ROUTE_REF`` / ``ASSET_REF``: the value is already the literal
  route/asset reference -- used directly, no further resolution.
* ``A11Y_LABEL``: the value is already the literal accessible-label text --
  used directly as an ``aria-label``, never resolved as content.

No-JS baseline (§20.3, CG-RND-006, D-5): ``directory.filters.panel``
declares ``collapse_behavior="drawer-below-md"`` on its
``ResponsiveContract`` regardless of which *variant* is selected (variant
and responsive collapse are independent axes, §7.1) -- so, mirroring
``nav.mobile.drawer``, it always renders through a native
``<details>``/``<summary>`` disclosure, never a script-driven toggle.
"""

from __future__ import annotations

from typing import Dict, Optional

from engines.website_generation.contracts.artifacts import ComponentInstance
from engines.website_generation.contracts.render_data import TileLinks
from engines.website_generation.rendering.html_emitter import (
    EmitterFn,
    HtmlFragment,
    LayoutContext,
    ResolvedContent,
    TokenMap,
    all_values,
    analytics_attrs,
    class_names,
    element,
    escape,
    first_value,
    link_list_html,
)

_HERO_PREFIX = "ac-hero"
_DIRECTORY_PREFIX = "ac-directory"
_STATUS_PREFIX = "ac-status"
_VERSION = "1.0.0"

# AES-WEB-002K.2: the home-page hero's real CTA -- a static, structural
# in-page link (``#main`` is a real, universal id every generated page's
# shell carries) styled through the shared CTA/button system
# (``emitters_listings_profiles._CTA_CLASS`` uses the identical class
# string; duplicated here rather than cross-imported per the "no
# sibling-family imports" convention this module's own docstring names).
# Generic, directory-neutral wording -- never PetTripFinder-specific copy
# baked into a shared engine component (operator decision: "PetTripFinder-
# specific visual hardcoding forbidden except the converter address fix").
_HERO_CTA_CLASS = "ac-cta ac-cta--action"
_HERO_CTA_LABEL = "Browse the directory"
_HERO_CTA_HREF = "#main"


def _link_items(hrefs: "tuple[str, ...]") -> str:
    """One ``<li><a>`` per resolved href -- mirrors
    ``emitters_navigation._link_items``; duplicated rather than imported
    across sibling emitter modules (each family module imports only
    ``html_emitter``, never a sibling family module, keeping the per-family
    dependency graph flat)."""
    return "".join(
        element("li", {}, element("a", {"href": href}, escape(href)))
        for href in hrefs
    )


def _emit_hero_search_directory(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Home-page search-first hero; H1 owner (§27.4). The "search embed"
    requirement is compositional nesting of ``directory.search.primary`` per
    the catalog's own documented resolution -- not representable without a
    nesting-capable artifact (see module docstring's "no nesting" note in
    ``emitters_layout_atoms``), so it renders as its own sibling instance in
    the same region, not nested inside this hero.

    AES-WEB-002K.2: gains a real, static, in-page CTA to ``#main`` (a
    universal id every page shell carries) styled through the shared CTA
    system -- a real button, never a bare text link, and never fake search
    or fabricated imagery."""
    h1 = first_value(resolved_content, "h1")
    subhead = first_value(resolved_content, "subhead")
    attrs = {
        "class": class_names(_HERO_PREFIX, "search-directory", "centered"),
        **analytics_attrs("hero-search-directory", _VERSION),
    }
    cta = element("a", {"class": _HERO_CTA_CLASS, "href": _HERO_CTA_HREF}, escape(_HERO_CTA_LABEL))
    return element(
        "section", attrs,
        element("h1", {}, escape(h1)) + element("p", {}, escape(subhead)) + cta,
    )


def _emit_hero_local_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Compact hero for category/city/city-category/service-area pages;
    ``context_role`` selects role-appropriate labeling (§27.4)."""
    h1 = first_value(resolved_content, "h1")
    intro = first_value(resolved_content, "intro")
    attrs = {
        "class": class_names(_HERO_PREFIX, "local-standard", "standard"),
        **analytics_attrs("hero-local-standard", _VERSION),
    }
    return element(
        "section", attrs, element("h1", {}, escape(h1)) + element("p", {}, escape(intro))
    )


def _emit_directory_search_primary(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Real GET search form (§5.3 -- MVP search is a crawlable link-based
    facet, never client-state-only)."""
    action_route = instance.props.get("action_route", "")
    input_label = instance.props.get("input_label", "Search")
    form_attrs = {
        "action": action_route,
        "class": class_names(_DIRECTORY_PREFIX, "search-primary", "standalone"),
        "method": "get",
        **analytics_attrs(
            "directory-search-primary", _VERSION, event="search_submit"
        ),
    }
    input_html = element(
        "input", {"aria-label": input_label, "name": "q", "type": "search"}
    )
    submit_html = element("button", {"type": "submit"}, "Search")
    return element("form", form_attrs, input_html + submit_html)


def _emit_directory_categories_grid(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Category discovery grid: the internal-link backbone from home/city
    pages into the category taxonomy (§27.4). Real, linked tiles
    (PILOT-PTF-1; ``layout_ctx.render_data.tiles``) -- one real ``<a>`` per
    launched category with its own human-readable label, never a raw route
    string. Degrades to the pre-K.1 unlinked href-as-label rendering when no
    render data is present (no ``ListingDataset`` supplied)."""
    tile_links: Optional[TileLinks] = layout_ctx.render_data.tiles if layout_ctx.render_data else None
    attrs = {
        "class": class_names(_DIRECTORY_PREFIX, "categories-grid", "tiles"),
        **analytics_attrs("directory-categories-grid", _VERSION),
    }
    if tile_links is not None:
        return element("section", attrs, element("ul", {}, link_list_html(tile_links.tiles)))
    tiles = all_values(resolved_content, "category_tiles")
    return element("section", attrs, element("ul", {}, _link_items(tiles)))


def _emit_directory_locations_grid(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Location discovery grid: the internal-link backbone into the city/
    region taxonomy (§27.4)."""
    tiles = all_values(resolved_content, "location_tiles")
    attrs = {
        "class": class_names(_DIRECTORY_PREFIX, "locations-grid", "tiles"),
        **analytics_attrs("directory-locations-grid", _VERSION),
    }
    return element("section", attrs, element("ul", {}, _link_items(tiles)))


def _emit_directory_filters_panel(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Link-based facet filters (§5.3); always renders through a native
    ``<details>`` disclosure regardless of variant, because
    ``collapse_behavior="drawer-below-md"`` applies independently of variant
    choice (see module docstring)."""
    facets = all_values(resolved_content, "facet_set_ref")
    details_attrs = {
        "class": class_names(_DIRECTORY_PREFIX, "filters-panel", "sidebar"),
        **analytics_attrs(
            "directory-filters-panel", _VERSION, event="filter_use"
        ),
    }
    return element(
        "aside",
        {},
        element(
            "details",
            details_attrs,
            element("summary", {}, "Filters") + element("ul", {}, _link_items(facets)),
        ),
    )


def _emit_directory_sort_control(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Link-based result sort control (§27.4); canonicalization is the SEO
    Engine's concern, never declared here (§13.3)."""
    options = all_values(resolved_content, "sort_options_ref")
    attrs = {
        "class": class_names(_DIRECTORY_PREFIX, "sort-control"),
        **analytics_attrs("directory-sort-control", _VERSION, event="sort_change"),
    }
    return element("div", attrs, element("ul", {}, _link_items(options)))


def _emit_directory_results_summary(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Result-count announcement text (§27.4/§6.2)."""
    summary_text = first_value(resolved_content, "summary_text")
    attrs = {
        "class": class_names(_DIRECTORY_PREFIX, "results-summary"),
        **analytics_attrs("directory-results-summary", _VERSION),
    }
    return element("div", attrs, escape(summary_text))


def _emit_status_results_zero(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Mandatory zero-results state (§6.2/CG-STR-006); recovery links are
    mandatory content, never an afterthought (§5.14)."""
    message = first_value(resolved_content, "message")
    recovery_links = all_values(resolved_content, "recovery_links")
    attrs = {
        "class": class_names(_STATUS_PREFIX, "results-zero"),
        "role": "status",
        **analytics_attrs("status-results-zero", _VERSION, event="zero_results_view"),
    }
    return element(
        "div", attrs, element("p", {}, escape(message)) + element("ul", {}, _link_items(recovery_links))
    )


DISCOVERY_EMITTERS: Dict[str, EmitterFn] = {
    "hero.search.directory@1": _emit_hero_search_directory,
    "hero.local.standard@1": _emit_hero_local_standard,
    "directory.search.primary@1": _emit_directory_search_primary,
    "directory.categories.grid@1": _emit_directory_categories_grid,
    "directory.locations.grid@1": _emit_directory_locations_grid,
    "directory.filters.panel@1": _emit_directory_filters_panel,
    "directory.sort.control@1": _emit_directory_sort_control,
    "directory.results.summary@1": _emit_directory_results_summary,
    "status.results.zero@1": _emit_status_results_zero,
}
