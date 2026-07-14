"""Pure HTML emitters for the ``nav.*``/``legal.footer.*``/``status.*``
navigation and shell components (AES-WEB-002 §27.3; catalog:
``components/catalog/navigation.py``).

Eight components, eight emitter functions, one explicit ``Dict[str,
EmitterFn]`` table (``NAVIGATION_EMITTERS``) -- see
``emitters_layout_atoms.py``'s module docstring for the shared conventions
(static per-component identity, content-binding, default-variant selection)
this module also follows.

Landmark labeling (§5.1 "aria-label disambiguation required when >1
``<nav>``"): every ``<nav>`` this module emits carries a fixed, structural
``aria-label`` distinguishing it from the page's other navs -- "Main",
"Mobile", "Breadcrumb", "Pagination". These are not invented marketing copy;
they mirror the same fixed-structural-label precedent the catalog itself
already uses for ``nav.pagination.standard`` ("labeled 'Pagination'", §12.6).

No-JS baseline (§20.3, CG-RND-006, D-5): ``nav.mobile.drawer`` uses the
native ``<details>``/``<summary>`` disclosure pattern -- zero script, fully
keyboard- and screen-reader-operable without any JavaScript. No
``aria-expanded``/``aria-modal`` are emitted, because those states would go
stale without JS keeping them synchronized with ``<details>``'s native
``open`` state; a native disclosure widget needs no redundant ARIA.
"""

from __future__ import annotations

from typing import Dict

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
    link_list_html,
)

_NAV_PREFIX = "ac-nav"
_LEGAL_PREFIX = "ac-legal"
_STATUS_PREFIX = "ac-status"
_VERSION = "1.0.0"


def _link_items(hrefs: "tuple[str, ...]") -> str:
    """One ``<li><a>`` per resolved href, using the href text as both the
    link target and visible label (the documented LinkSpec-single-string
    limitation shared by every link-shaped binding in this delivery -- see
    ``emitters_layout_atoms._emit_atom_link_standard``)."""
    return "".join(
        element("li", {}, element("a", {"href": href}, escape(href)))
        for href in hrefs
    )


def _emit_nav_skip_link(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Skip-to-main-content link (§5.1/§12.1): mandatory first focusable
    element, targeting the shell's ``<main id="main">``. "Skip to main
    content" is fixed structural chrome text, not commercial copy -- the
    same category as ``nav.pagination.standard``'s fixed "Pagination"
    label."""
    attrs = {
        "class": class_names(_NAV_PREFIX, "skip-link"),
        "href": "#main",
        **analytics_attrs("nav-skip-link", _VERSION),
    }
    return element("a", attrs, "Skip to main content")


def _emit_nav_header_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Main site header: real nav links from render data (AES-WEB-002K.1;
    layout_ctx.render_data.nav -- SiteArchitecture-derived, never
    hand-authored per page). No separate logo/wordmark markup: logo is
    optional (D4) and, with no asset store to source a real image from,
    the header's first (Home) nav link already carries the site identity --
    fabricating a text duplicate of it would add noise, not information."""
    nav_data = layout_ctx.render_data.nav if layout_ctx.render_data else None
    links = nav_data.links if nav_data is not None else ()
    nav_attrs = {
        "aria-label": "Main",
        "class": class_names(_NAV_PREFIX, "header-standard", "standard"),
        **analytics_attrs(
            "nav-header-standard", _VERSION, event="component_interaction"
        ),
    }
    return element("nav", nav_attrs, element("ul", {}, link_list_html(links)))


def _emit_nav_mobile_drawer(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Mobile navigation drawer: CSS/``<details>``-driven no-JS baseline
    (CG-RND-006) -- see module docstring."""
    links = all_values(resolved_content, "nav_tree")
    nav_html = element(
        "nav", {"aria-label": "Mobile"}, element("ul", {}, _link_items(links))
    )
    details_attrs = {
        "class": class_names(_NAV_PREFIX, "mobile-drawer"),
        **analytics_attrs(
            "nav-mobile-drawer", _VERSION, event="component_interaction"
        ),
    }
    return element(
        "details", details_attrs, element("summary", {}, "Menu") + nav_html
    )


def _emit_nav_breadcrumbs_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Breadcrumb trail (§6.2 required on every page role except home/lead-
    gen-landing). Structured-data (BreadcrumbList) compilation is SEO
    Engine/Assembly's job (§13.2), never emitted here."""
    trail = all_values(resolved_content, "trail")
    attrs = {
        "aria-label": "Breadcrumb",
        "class": class_names(_NAV_PREFIX, "breadcrumbs-standard"),
        **analytics_attrs("nav-breadcrumbs-standard", _VERSION),
    }
    return element("nav", attrs, element("ol", {}, _link_items(trail)))


def _emit_nav_utility_bar(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Announcement/utility strip (§27.3); dismissal is a deferred P3
    capability, not implemented here."""
    message = first_value(resolved_content, "message")
    link = first_value(resolved_content, "link")
    link_anchor_html = element("a", {"href": link}, escape(link)) if link else ""
    attrs = {
        "class": class_names(_NAV_PREFIX, "utility-bar", "announce"),
        **analytics_attrs("nav-utility-bar", _VERSION),
    }
    return element("div", attrs, escape(message) + link_anchor_html)


def _emit_nav_pagination_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Crawl-safe numbered pagination (§27.3), labeled "Pagination" (§12.6).
    ``aria-current="page"`` requires knowing which page is current -- no
    structured current/total data reaches the Renderer (only an opaque
    resolved reference string per page link), so it is deliberately omitted
    rather than guessed (documented gap; see the implementation report)."""
    pages = all_values(resolved_content, "page_context")
    attrs = {
        "aria-label": "Pagination",
        "class": class_names(_NAV_PREFIX, "pagination-standard"),
        **analytics_attrs("nav-pagination-standard", _VERSION, event="pagination_click"),
    }
    return element("nav", attrs, element("ul", {}, _link_items(pages)))


def _emit_legal_footer_directory(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Footer content, mandatory on every page (§5.15). Renders as content
    inside the shell's single ``<footer>`` landmark, not a second one -- this
    component's own semantic element is ``div``, matching the catalog
    contract. Nav links come from render data (AES-WEB-002K.1;
    ``layout_ctx.render_data.nav`` -- Wave 1 shares the exact same link set
    as the site header, no trust/editorial routes exist yet to
    differentiate them)."""
    legal_facts = first_value(resolved_content, "legal_facts")
    disclosures = all_values(resolved_content, "disclosures")
    nav_data = layout_ctx.render_data.nav if layout_ctx.render_data else None
    links = nav_data.links if nav_data is not None else ()
    disclosures_html = "".join(
        element("p", {}, escape(text)) for text in disclosures
    )
    attrs = {
        "class": class_names(_LEGAL_PREFIX, "footer-directory", "standard"),
        **analytics_attrs("legal-footer-directory", _VERSION),
    }
    return element(
        "div",
        attrs,
        element("p", {}, escape(legal_facts))
        + disclosures_html
        + element("ul", {}, link_list_html(links)),
    )


def _emit_status_banner_notification(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """System/status notification banner (§5.14); severity selects
    ``role=status`` vs ``role=alert`` at emitter time (§12.5, per the
    catalog's own deferral note)."""
    severity = instance.props.get("severity", "info")
    body = first_value(resolved_content, "body")
    action = first_value(resolved_content, "action")
    role = "alert" if severity == "error" else "status"
    action_html = element("a", {"href": action}, escape(action)) if action else ""
    attrs = {
        "class": class_names(_STATUS_PREFIX, "banner-notification", severity),
        "role": role,
        **analytics_attrs("status-banner-notification", _VERSION),
    }
    return element("div", attrs, escape(body) + action_html)


NAVIGATION_EMITTERS: Dict[str, EmitterFn] = {
    "nav.skip.link@1": _emit_nav_skip_link,
    "nav.header.standard@1": _emit_nav_header_standard,
    "nav.mobile.drawer@1": _emit_nav_mobile_drawer,
    "nav.breadcrumbs.standard@1": _emit_nav_breadcrumbs_standard,
    "nav.utility.bar@1": _emit_nav_utility_bar,
    "nav.pagination.standard@1": _emit_nav_pagination_standard,
    "legal.footer.directory@1": _emit_legal_footer_directory,
    "status.banner.notification@1": _emit_status_banner_notification,
}
