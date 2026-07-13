"""Pure HTML emitters for the ``seo.local-links.*``/``content.*`` editorial
and local-SEO components (AES-WEB-002 §27.7; catalog:
``components/catalog/seo_editorial.py``).

Seven components, seven emitter functions, one explicit ``Dict[str,
EmitterFn]`` table (``SEO_EDITORIAL_EMITTERS``). Shares every convention
documented in ``emitters_layout_atoms.py`` and the opaque-content reality
documented in ``emitters_listings_profiles.py``.

Scope boundary (AES-WEB-001 §5.9/§8.4, prompt §10): these emit **content-body
markup only**. They never emit ``<title>``/meta/canonical tags, robots
directives, sitemaps, or ``<head>`` JSON-LD -- those are SEO Engine and
Assembly responsibilities, out of the Renderer's boundary. ``seo.local-links.*``
surface internal links that arrive already resolved from ``SiteArchitecture``
topology (§5.9 "components never invent URLs"); the emitter renders the bound
link set and never synthesizes a URL.
"""

from __future__ import annotations

from typing import Dict, Tuple

from engines.website_generation.contracts.artifacts import ComponentInstance
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
)

_SEO_PREFIX = "ac-seo"
_CONTENT_PREFIX = "ac-content"
_VERSION = "1.0.0"


def _link_items(hrefs: Tuple[str, ...]) -> str:
    """One ``<li><a>`` per resolved href (href text doubles as the visible
    label -- the documented single-string LinkSpec limitation)."""
    return "".join(
        element("li", {}, element("a", {"href": href}, escape(href)))
        for href in hrefs
    )


# ---------------------------------------------------------------------------
# seo.local-links.* (§27.7)
# ---------------------------------------------------------------------------


def _emit_seo_local_links_cities(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Nearby-city internal-link block from SiteArchitecture topology (§5.9)."""
    links = all_values(resolved_content, "city_links")
    attrs = {
        "class": class_names(_SEO_PREFIX, "local-links-cities", "grid"),
        **analytics_attrs("seo-local-links-cities", _VERSION),
    }
    return element("section", attrs, element("ul", {}, _link_items(links)))


def _emit_seo_local_links_categories(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Related-category internal-link block from SiteArchitecture topology
    (§5.9)."""
    links = all_values(resolved_content, "category_links")
    attrs = {
        "class": class_names(_SEO_PREFIX, "local-links-categories", "grid"),
        **analytics_attrs("seo-local-links-categories", _VERSION),
    }
    return element("section", attrs, element("ul", {}, _link_items(links)))


# ---------------------------------------------------------------------------
# content.* (§27.7)
# ---------------------------------------------------------------------------


def _emit_content_intro_contextual(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Programmatic contextual intro copy (the CG-SEO-007 thin-content
    watchdog surface). Renders only the bound intro text -- variation is a
    content-layer concern, never invented here."""
    intro = first_value(resolved_content, "intro")
    attrs = {
        "class": class_names(_CONTENT_PREFIX, "intro-contextual", "above-listings"),
        **analytics_attrs("content-intro-contextual", _VERSION),
    }
    return element("section", attrs, element("p", {}, escape(intro)))


def _emit_content_section_editorial(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """General-purpose editorial rich-text section (H2/H3 discipline, §9.3)."""
    body = first_value(resolved_content, "body")
    attrs = {
        "class": class_names(_CONTENT_PREFIX, "section-editorial", "standard"),
        **analytics_attrs("content-section-editorial", _VERSION),
    }
    return element("section", attrs, element("p", {}, escape(body)))


def _emit_content_toc_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """In-page table of contents as a labeled ``<nav>`` landmark. Jump links
    arrive resolved via the ``heading_refs`` reference; the ``aria-label``
    "Table of contents" disambiguates this second ``<nav>`` from the shell's
    header nav (§9.3), fixed structural chrome, not invented copy."""
    links = all_values(resolved_content, "heading_refs")
    attrs = {
        "aria-label": "Table of contents",
        "class": class_names(_CONTENT_PREFIX, "toc-standard", "sidebar"),
        **analytics_attrs("content-toc-standard", _VERSION),
    }
    return element("nav", attrs, element("ol", {}, _link_items(links)))


def _emit_content_table_comparison(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Comparison table with a caption and a scoped header (§8.4 mandatory
    header declarations; CG-RSP-004 scroll-x adaptation is CSS-owned). The
    opaque ComparisonTableBlock text renders as the table body -- typed
    row/cell structure needs a structured block the opaque text does not
    carry (documented gap). "Comparison" is fixed structural table chrome."""
    table_text = first_value(resolved_content, "table")
    attrs = {
        "class": class_names(_CONTENT_PREFIX, "table-comparison"),
        **analytics_attrs("content-table-comparison", _VERSION),
    }
    table = element(
        "table",
        {},
        element("caption", {}, "Comparison")
        + element(
            "thead",
            {},
            element("tr", {}, element("th", {"scope": "col"}, "Details")),
        )
        + element(
            "tbody",
            {},
            element("tr", {}, element("td", {}, escape(table_text))),
        ),
    )
    return element("section", attrs, table)


def _emit_content_resources_grid(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Internal-link resource grid (resource cards modeled as LinkSpec)."""
    resources = all_values(resolved_content, "resources")
    attrs = {
        "class": class_names(_CONTENT_PREFIX, "resources-grid"),
        **analytics_attrs("content-resources-grid", _VERSION),
    }
    return element("section", attrs, element("ul", {}, _link_items(resources)))


SEO_EDITORIAL_EMITTERS: Dict[str, EmitterFn] = {
    "seo.local-links.cities@1": _emit_seo_local_links_cities,
    "seo.local-links.categories@1": _emit_seo_local_links_categories,
    "content.intro.contextual@1": _emit_content_intro_contextual,
    "content.section.editorial@1": _emit_content_section_editorial,
    "content.toc.standard@1": _emit_content_toc_standard,
    "content.table.comparison@1": _emit_content_table_comparison,
    "content.resources.grid@1": _emit_content_resources_grid,
}
