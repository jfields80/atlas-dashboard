"""Pure HTML emitters for the ``listing.*``/``profile.*``/
``content.description.business`` components (AES-WEB-002 §27.5; catalog:
``components/catalog/listings_profiles.py``).

Twelve components, twelve emitter functions, one explicit ``Dict[str,
EmitterFn]`` table (``LISTINGS_PROFILES_EMITTERS``). Shares every convention
documented in ``emitters_layout_atoms.py``'s module docstring (static
per-component identity, exact ``(route, slot_id)`` content binding,
default-variant selection, no sibling-family imports, canonical escaping via
``html_emitter``).

Opaque-content reality (AES-WEB-002J.8 established, unchanged): ``ContentBlock
.text`` is a single opaque string (``content/content_engine.py``), so every
structured §8.4 block type these components declare -- ``ContactSpec``,
``HoursSpec``, ``RatingSummary``, ``GeoSpec``, ``CredentialBlock``,
``AssetRef``, ``DisclosureBlock``, and the ``LISTING_REF``-resolved listing
data -- reaches an emitter as plain text. Emitters therefore wrap that text
in the *correct semantic element* (``<article>``, ``<header>``, ``<address>``,
``<table>``, list markup) and never fabricate the sub-fields (rating numbers,
per-day hours, coordinates) the structured type would carry. Where a
component contract names a structured affordance the opaque text cannot
supply, that is recorded as a carried gap in the AES-WEB-002J.9
implementation report, never invented here.

Documented per-component gaps (carried, not silently resolved):
* ``listing.*`` cards/rows, ``profile.contact.panel``, and
  ``profile.hours.table`` now render real hyperlinks and structured
  enrichment via ``layout_ctx.render_data`` (AES-WEB-002K.1;
  ``contracts/render_data.py``) when the Component Engine's render-data
  producer ran (a ``ListingDataset`` was supplied) -- the pre-K.1 opaque
  single-string rendering is retained as the honest degrade path when it
  did not.
* ``profile.gallery.standard`` binds ``AssetRef`` images as opaque reference
  strings with no companion alt text, so each ``<img>`` carries ``alt=""``
  (the spec-legal decorative marker, WCAG H67) -- the same documented
  limitation ``atom.image.responsive`` carries in J.8. Out of Wave 1 scope
  (no asset store; K.1 explicitly ships no images).
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from engines.website_generation.contracts.artifacts import ComponentInstance
from engines.website_generation.contracts.render_data import ContactData, HoursData, ListingCardData
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
    link_html,
)

_LISTING_PREFIX = "ac-listing"
_PROFILE_PREFIX = "ac-profile"
_CONTENT_PREFIX = "ac-content"
_VERSION = "1.0.0"


def _text_items(tag: str, values: Tuple[str, ...]) -> str:
    """One ``<tag>`` per resolved value, escaped -- for opaque multi-value
    slots (credentials, premium blocks) with no richer structure to reflect."""
    return "".join(element(tag, {}, escape(value)) for value in values)


def _link_items(hrefs: Tuple[str, ...], *, rel: str = "") -> str:
    """One ``<li><a>`` per resolved href (href text doubles as the visible
    label -- the documented single-string LinkSpec limitation shared across
    every J.8/J.9 link binding). ``rel`` is applied when the component's SEO
    contract requires it (e.g. sponsored)."""
    attrs_rel = {"rel": rel} if rel else {}
    return "".join(
        element("li", {}, element("a", {"href": href, **attrs_rel}, escape(href)))
        for href in hrefs
    )


def _disclosure_block(prefix: str, text: str) -> str:
    """A visible, non-hidden disclosure paragraph (§17.1) -- always rendered
    as ordinary in-flow text, never visually suppressed."""
    return element(
        "p", {"class": class_names(prefix, "disclosure")}, escape(text)
    )


def _card_body(card: Optional[ListingCardData], fallback_text: str) -> str:
    """A real, linked, enriched card body (AES-WEB-002K.1) when render data
    is present; degrades to the pre-K.1 unlinked ``<h2>`` heading when it is
    absent (no ListingDataset supplied -- the render-data producer never
    ran). ``<h2>`` (not the pre-K.1 ``<h3>``) either way: the card is the
    first heading level under the page's own ``<h1>``, never a level skip
    (CG-CMP-005)."""
    if card is None:
        return element("h2", {}, escape(fallback_text))
    name_html = element("a", {"href": card.profile_href}, escape(card.name))
    parts = [element("h2", {}, name_html)]
    if card.area_label:
        parts.append(
            element("p", {"class": class_names(_LISTING_PREFIX, "area")}, escape(card.area_label))
        )
    if card.rating_text:
        rating_text = card.rating_text
        if card.review_count is not None:
            rating_text = "%s (%d review%s)" % (
                card.rating_text, card.review_count, "" if card.review_count == 1 else "s",
            )
        parts.append(
            element("p", {"class": class_names(_LISTING_PREFIX, "rating")}, escape(rating_text))
        )
    if card.badge_label:
        parts.append(
            element("span", {"class": class_names(_LISTING_PREFIX, "badge")}, escape(card.badge_label))
        )
    if card.cta is not None:
        parts.append(link_html(card.cta))
    return "".join(parts)


# ---------------------------------------------------------------------------
# listing.* (§27.5)
# ---------------------------------------------------------------------------


def _emit_listing_card_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Organic listing card (§6.3 ORGANIC). Real, linked, enriched card body
    (AES-WEB-002K.1; ``layout_ctx.render_data.card``)."""
    density = instance.props.get("density", "comfortable")
    listing_text = first_value(resolved_content, "listing_ref")
    card = layout_ctx.render_data.card if layout_ctx.render_data else None
    attrs = {
        "class": class_names(_LISTING_PREFIX, "card-standard", "standard", density),
        **analytics_attrs("listing-card-standard", _VERSION, event="listing_click"),
    }
    return element("article", attrs, _card_body(card, listing_text))


def _emit_listing_card_featured(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Featured (paid) listing card: mandatory visible disclosure (§17.1, E5)
    on a distinct surface (§6.3 non-confusion). Real, linked, enriched card
    body (AES-WEB-002K.1)."""
    listing_text = first_value(resolved_content, "listing_ref")
    disclosure = first_value(resolved_content, "disclosure")
    card = layout_ctx.render_data.card if layout_ctx.render_data else None
    attrs = {
        "class": class_names(_LISTING_PREFIX, "card-featured", "featured"),
        **analytics_attrs("listing-card-featured", _VERSION, event="listing_click"),
    }
    return element(
        "article",
        attrs,
        _disclosure_block(_LISTING_PREFIX, disclosure) + _card_body(card, listing_text),
    )


def _emit_listing_card_sponsored(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Sponsored (paid, interleaved) listing card: mandatory visible
    disclosure (§17.1, E5), distinct sponsored surface (§6.3). Real, linked,
    enriched card body (AES-WEB-002K.1)."""
    listing_text = first_value(resolved_content, "listing_ref")
    disclosure = first_value(resolved_content, "disclosure")
    card = layout_ctx.render_data.card if layout_ctx.render_data else None
    attrs = {
        "class": class_names(_LISTING_PREFIX, "card-sponsored", "sponsored"),
        **analytics_attrs(
            "listing-card-sponsored", _VERSION, event="sponsored_listing_click"
        ),
    }
    return element(
        "article",
        attrs,
        _disclosure_block(_LISTING_PREFIX, disclosure) + _card_body(card, listing_text),
    )


def _emit_listing_row_compact(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Compact organic listing row for search-results/comparison (§27.5).
    Real, linked, enriched card body (AES-WEB-002K.1) when render data is
    present; degrades to the pre-K.1 unlinked ``<span>`` when absent."""
    listing_text = first_value(resolved_content, "listing_ref")
    card = layout_ctx.render_data.card if layout_ctx.render_data else None
    attrs = {
        "class": class_names(_LISTING_PREFIX, "row-compact", "result"),
        **analytics_attrs("listing-row-compact", _VERSION, event="listing_click"),
    }
    if card is None:
        return element("div", attrs, element("span", {}, escape(listing_text)))
    return element("div", attrs, _card_body(card, listing_text))


# ---------------------------------------------------------------------------
# profile.* (§27.5)
# ---------------------------------------------------------------------------


def _emit_profile_header_business(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Business-profile H1 owner (§9.3), replacing the hero on this role.
    Optional rating summary renders as a text equivalent (stars would be
    decorative, §12.4) -- never fabricated when absent.

    AES-WEB-002K.1: root element is ``<section>``, not ``<header>`` -- the
    site shell's HEADER-region ``nav.header.standard`` now owns the page's
    single ``<header>`` landmark (CG-CMP-006); this component still owns
    the ``<h1>``, just inside a non-landmark container.

    PILOT-PTF-1 claimed-variant honesty fix: the modifier class used to be a
    hardcoded ``"claimed"`` regardless of any real claim-status data --
    ``ListingRecord`` carries no claim-status field at all (that is a future
    AES-WEB-005 concern), so no listing could honestly be marked claimed.
    Renders the neutral ``"standard"`` modifier (matching every other
    single-variant component's third class segment) until a real
    claim-status producer exists; never asserts "claimed" without evidence."""
    name = first_value(resolved_content, "name")
    rating = first_value(resolved_content, "rating_summary")
    attrs = {
        "class": class_names(_PROFILE_PREFIX, "header-business", "standard"),
        **analytics_attrs("profile-header-business", _VERSION),
    }
    children = element("h1", {}, escape(name))
    if rating:
        children += element(
            "p", {"class": class_names(_PROFILE_PREFIX, "rating")}, escape(rating)
        )
    return element("section", attrs, children)


def _emit_profile_contact_panel(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Contact panel: real, clickable tel:/mailto:/website links
    (AES-WEB-002K.1; ``layout_ctx.render_data.contact``) inside an
    ``<address>`` (§13.3). Degrades to the pre-K.1 opaque NAP text when
    render data is absent.

    PILOT-PTF-1 §15: a sponsored listing's own ``disclosure_text`` (when
    present) renders as a visible paragraph outside the ``<address>`` block
    (a disclosure is not itself a NAP fact) -- absent for every ORGANIC/
    non-sponsored listing, never a fabricated default."""
    contact_info = first_value(resolved_content, "contact_info")
    contact: Optional[ContactData] = layout_ctx.render_data.contact if layout_ctx.render_data else None
    attrs = {
        "class": class_names(_PROFILE_PREFIX, "contact-panel", "sidebar"),
        **analytics_attrs("profile-contact-panel", _VERSION, event="phone_click"),
    }
    if contact is None:
        return element("aside", attrs, element("address", {}, escape(contact_info)))
    parts = []
    if contact.address_text:
        parts.append(element("p", {}, escape(contact.address_text)))
    if contact.phone is not None:
        parts.append(element("p", {}, link_html(contact.phone)))
    if contact.email is not None:
        parts.append(element("p", {}, link_html(contact.email)))
    if contact.website is not None:
        parts.append(element("p", {}, link_html(contact.website)))
    address = element("address", {}, "".join(parts))
    if contact.disclosure_text:
        address += _disclosure_block(_PROFILE_PREFIX, contact.disclosure_text)
    return element("aside", attrs, address)


def _emit_profile_hours_table(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Business hours as a real accessible table with a caption and a scoped
    header (§12.4, CG-A11Y-007). Real per-day rows (AES-WEB-002K.1;
    ``layout_ctx.render_data.hours``) when render data is present; degrades
    to the pre-K.1 single opaque schedule cell when absent. "Business
    hours"/"Schedule"/"Day"/"Hours" are fixed structural table chrome (the
    J.8 precedent for fixed non-commercial chrome text), never invented
    business copy."""
    hours_text = first_value(resolved_content, "hours")
    hours: Optional[HoursData] = layout_ctx.render_data.hours if layout_ctx.render_data else None
    attrs = {
        "class": class_names(_PROFILE_PREFIX, "hours-table"),
        **analytics_attrs("profile-hours-table", _VERSION),
    }
    if hours is None or not hours.rows:
        table = element(
            "table",
            {},
            element("caption", {}, "Business hours")
            + element(
                "thead",
                {},
                element("tr", {}, element("th", {"scope": "col"}, "Schedule")),
            )
            + element(
                "tbody",
                {},
                element("tr", {}, element("td", {}, escape(hours_text))),
            ),
        )
        return element("div", attrs, table)
    body_rows = "".join(
        element(
            "tr", {},
            element("th", {"scope": "row"}, escape(row.day))
            + element("td", {}, "Closed" if row.closed else escape("%s-%s" % (row.opens, row.closes))),
        )
        for row in hours.rows
    )
    table = element(
        "table",
        {},
        element("caption", {}, "Business hours")
        + element(
            "thead",
            {},
            element(
                "tr", {},
                element("th", {"scope": "col"}, "Day") + element("th", {"scope": "col"}, "Hours"),
            ),
        )
        + element("tbody", {}, body_rows),
    )
    return element("div", attrs, table)


def _emit_profile_areas_served(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Service-area internal-link set (§13.2 areaServed)."""
    areas = all_values(resolved_content, "area_links")
    attrs = {
        "class": class_names(_PROFILE_PREFIX, "areas-served", "list"),
        **analytics_attrs("profile-areas-served", _VERSION),
    }
    return element("section", attrs, element("ul", {}, _link_items(areas)))


def _emit_profile_map_directions(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Static map + text directions; text directions are the primary
    accessible path (§12.4). No interactive/third-party embed (§25 P3):
    location renders as text, never an iframe."""
    location = first_value(resolved_content, "location")
    directions = first_value(resolved_content, "directions_text")
    attrs = {
        "class": class_names(_PROFILE_PREFIX, "map-directions", "static-image"),
        **analytics_attrs("profile-map-directions", _VERSION),
    }
    children = element(
        "p", {"class": class_names(_PROFILE_PREFIX, "location")}, escape(location)
    ) + element("p", {}, escape(directions))
    return element("section", attrs, children)


def _emit_profile_credentials_list(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Credentials list; each entry's issuer+evidence text renders as a list
    item (CG-COM-003 evidence gating is a gate concern, not emitter-fabricated)."""
    credentials = all_values(resolved_content, "credentials")
    attrs = {
        "class": class_names(_PROFILE_PREFIX, "credentials-list"),
        **analytics_attrs("profile-credentials-list", _VERSION),
    }
    return element("section", attrs, element("ul", {}, _text_items("li", credentials)))


def _emit_profile_gallery_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """CSS-only scroll-snap gallery with list semantics (§12.6 Gallery). Each
    image is an opaque AssetRef with no companion alt text, so ``alt=""`` --
    the documented gap shared with ``atom.image.responsive``."""
    images = all_values(resolved_content, "images")
    items = "".join(
        element("li", {}, element("img", {"alt": "", "src": ref}))
        for ref in images
    )
    attrs = {
        "class": class_names(_PROFILE_PREFIX, "gallery-standard", "scroll-snap"),
        **analytics_attrs("profile-gallery-standard", _VERSION),
    }
    return element("section", attrs, element("ul", {}, items))


# ---------------------------------------------------------------------------
# content.description.business (§27.5)
# ---------------------------------------------------------------------------


def _emit_content_description_business(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Business description copy (H3-scoped internal headings, §9.3)."""
    description = first_value(resolved_content, "description")
    attrs = {
        "class": class_names(_CONTENT_PREFIX, "description-business"),
        **analytics_attrs("content-description-business", _VERSION),
    }
    return element("section", attrs, element("p", {}, escape(description)))


LISTINGS_PROFILES_EMITTERS: Dict[str, EmitterFn] = {
    "listing.card.standard@1": _emit_listing_card_standard,
    "listing.card.featured@1": _emit_listing_card_featured,
    "listing.card.sponsored@1": _emit_listing_card_sponsored,
    "listing.row.compact@1": _emit_listing_row_compact,
    "profile.header.business@1": _emit_profile_header_business,
    "profile.contact.panel@1": _emit_profile_contact_panel,
    "profile.hours.table@1": _emit_profile_hours_table,
    "profile.areas.served@1": _emit_profile_areas_served,
    "profile.map.directions@1": _emit_profile_map_directions,
    "profile.credentials.list@1": _emit_profile_credentials_list,
    "profile.gallery.standard@1": _emit_profile_gallery_standard,
    "content.description.business@1": _emit_content_description_business,
}
