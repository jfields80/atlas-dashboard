"""Pure HTML emitters for the ``monetization.*``/``commerce.*``/``status.*``/
``legal.*`` components (AES-WEB-002 §27.8; catalog:
``components/catalog/monetization_status.py``).

Eight components, eight emitter functions, one explicit ``Dict[str,
EmitterFn]`` table (``MONETIZATION_STATUS_EMITTERS``). Shares every
convention documented in ``emitters_layout_atoms.py`` and the opaque-content
reality documented in ``emitters_listings_profiles.py``.

Disclosure and non-confusion (§17.1, §6.3, E5, prompt §11): every paid
surface renders its disclosure/marker as ordinary visible in-flow text --
never visually suppressed, never hidden. Sponsor markers, advertising
disclosures, premium-section disclosures, and upgrade-prompt disclosures all
carry a distinct ``--disclosure`` / sponsored class so the non-confusion
rule (paid content is distinguishable from organic at a glance) holds
structurally. No emitter fabricates prices, legal text, consent language,
guarantees, or sponsorship claims -- all such copy renders only from bound
content, escaped. No payment/checkout/external-ad request is emitted (§25,
§19); pricing renders as static bound text, and the E4 disclaimer slot
renders visibly alongside it.
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

_MONETIZATION_PREFIX = "ac-monetization"
_COMMERCE_PREFIX = "ac-commerce"
_STATUS_PREFIX = "ac-status"
_LEGAL_PREFIX = "ac-legal"
_VERSION = "1.0.0"


def _disclosure_block(prefix: str, text: str) -> str:
    """A visible, never-suppressed disclosure paragraph (§17.1)."""
    return element("p", {"class": class_names(prefix, "disclosure")}, escape(text))


def _link_items(hrefs: Tuple[str, ...]) -> str:
    return "".join(
        element("li", {}, element("a", {"href": href}, escape(href)))
        for href in hrefs
    )


# ---------------------------------------------------------------------------
# monetization.* (§27.8)
# ---------------------------------------------------------------------------


def _emit_monetization_disclosure_advertising(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Visible advertising/sponsorship disclosure (§17.1). Renders the bound
    registered disclosure text -- components never author disclosure copy
    inline. ``disclosure_kind`` is a machine marker (data attribute), not
    visible text."""
    kind = instance.props.get("disclosure_kind", "advertising")
    disclosure = first_value(resolved_content, "disclosure")
    attrs = {
        "class": class_names(_MONETIZATION_PREFIX, "disclosure-advertising", "page-level"),
        "data-atlas-k": kind,
        **analytics_attrs("monetization-disclosure-advertising", _VERSION),
    }
    return element("div", attrs, _disclosure_block(_MONETIZATION_PREFIX, disclosure))


def _emit_monetization_ribbon_sponsor(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """The visible paid marker for listing/zone contexts (§17.1, §6.3
    non-confusion). Distinct sponsored surface class, visible label text."""
    label = first_value(resolved_content, "label")
    attrs = {
        "class": class_names(_MONETIZATION_PREFIX, "ribbon-sponsor", "sponsored"),
        "data-atlas-k": "sponsored",
        **analytics_attrs("monetization-ribbon-sponsor", _VERSION),
    }
    return element("div", attrs, escape(label))


def _emit_monetization_section_premium_profile(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Premium profile content, extending -- never gating -- core facts
    (§17.2 'core facts never paywalled'). Premium blocks render as visible
    content; ordering/core-facts-precedence is a composition/gate concern
    (CG-COM-012)."""
    blocks = all_values(resolved_content, "premium_blocks")
    items = "".join(element("p", {}, escape(block)) for block in blocks)
    attrs = {
        "class": class_names(_MONETIZATION_PREFIX, "section-premium-profile"),
        "data-atlas-k": "premium",
        **analytics_attrs("monetization-section-premium-profile", _VERSION),
    }
    return element("section", attrs, items)


def _emit_monetization_prompt_upgrade(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Claim-flow upgrade prompt. Mandatory visible disclosure that the
    upgrade is optional (E10 adjacency, §17.2) -- never disguised as a
    requirement."""
    offer = first_value(resolved_content, "offer")
    disclosure = first_value(resolved_content, "disclosure")
    attrs = {
        "class": class_names(_MONETIZATION_PREFIX, "prompt-upgrade"),
        "data-atlas-k": "upgrade",
        **analytics_attrs("monetization-prompt-upgrade", _VERSION),
    }
    children = element("p", {}, escape(offer)) + _disclosure_block(
        _MONETIZATION_PREFIX, disclosure
    )
    return element("div", attrs, children)


# ---------------------------------------------------------------------------
# commerce.* (§27.8)
# ---------------------------------------------------------------------------


def _emit_commerce_pricing_sponsorship(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Sponsorship pricing tiers as static bound text plus the mandatory E4
    disclaimer (CG-COM-006) -- no payment/checkout, no invented amounts. The
    disclaimer always renders visibly alongside the pricing."""
    prices = all_values(resolved_content, "pricing")
    disclaimer = first_value(resolved_content, "disclaimer")
    items = "".join(element("li", {}, escape(price)) for price in prices)
    attrs = {
        "class": class_names(_COMMERCE_PREFIX, "pricing-sponsorship", "cards"),
        **analytics_attrs("commerce-pricing-sponsorship", _VERSION),
    }
    children = element("ul", {}, items) + _disclosure_block(
        _COMMERCE_PREFIX, disclaimer
    )
    return element("section", attrs, children)


# ---------------------------------------------------------------------------
# status.* (§27.8)
# ---------------------------------------------------------------------------


def _emit_status_listing_pending(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Pending-verification state (§6.3, E10). Never fakes VERIFIED -- renders
    only the honest interim message and expectation text in a status live
    region."""
    message = first_value(resolved_content, "message")
    expectation = first_value(resolved_content, "expectation_text")
    attrs = {
        "class": class_names(_STATUS_PREFIX, "listing-pending"),
        "role": "status",
        **analytics_attrs("status-listing-pending", _VERSION),
    }
    children = element("p", {}, escape(message)) + element(
        "p", {}, escape(expectation)
    )
    return element("div", attrs, children)


def _emit_status_listing_unavailable(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Unavailable listing state (§6.1, CG-STR-006). Recovery links are
    mandatory content (§5.14) -- rendered as a real internal-link list."""
    reason = instance.props.get("reason", "unavailable")
    message = first_value(resolved_content, "message")
    recovery = all_values(resolved_content, "recovery_links")
    attrs = {
        "class": class_names(_STATUS_PREFIX, "listing-unavailable", reason),
        "role": "status",
        **analytics_attrs("status-listing-unavailable", _VERSION),
    }
    children = element("p", {}, escape(message)) + element(
        "ul", {}, _link_items(recovery)
    )
    return element("div", attrs, children)


# ---------------------------------------------------------------------------
# legal.* (§27.8)
# ---------------------------------------------------------------------------


def _emit_legal_statement_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Kind-specific legal statement as a self-contained ``<article>`` (H3+
    internal headings, §9.3). Body renders escaped -- legal text is never
    passed through raw."""
    kind = instance.props.get("kind", "privacy")
    body = first_value(resolved_content, "body")
    attrs = {
        "class": class_names(_LEGAL_PREFIX, "statement-standard", kind),
        **analytics_attrs("legal-statement-standard", _VERSION),
    }
    return element("article", attrs, element("p", {}, escape(body)))


MONETIZATION_STATUS_EMITTERS: Dict[str, EmitterFn] = {
    "monetization.disclosure.advertising@1": _emit_monetization_disclosure_advertising,
    "monetization.ribbon.sponsor@1": _emit_monetization_ribbon_sponsor,
    "monetization.section.premium-profile@1": _emit_monetization_section_premium_profile,
    "monetization.prompt.upgrade@1": _emit_monetization_prompt_upgrade,
    "commerce.pricing.sponsorship@1": _emit_commerce_pricing_sponsorship,
    "status.listing.pending@1": _emit_status_listing_pending,
    "status.listing.unavailable@1": _emit_status_listing_unavailable,
    "legal.statement.standard@1": _emit_legal_statement_standard,
}
