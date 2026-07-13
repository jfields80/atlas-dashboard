"""Pure HTML emitters for the ``trust.*``/``content.faq.standard``/
``form.*``/``cta.*`` components (AES-WEB-002 §27.6; catalog:
``components/catalog/trust_conversion.py``).

Thirteen components, thirteen emitter functions, one explicit ``Dict[str,
EmitterFn]`` table (``TRUST_CONVERSION_EMITTERS``). Shares every convention
documented in ``emitters_layout_atoms.py`` and the opaque-content reality
documented in ``emitters_listings_profiles.py``.

Form emission (§5.13, §16.5, CG-A11Y-012, D-5 no-JS): every ``form.*``
component renders a native ``<form method="post" action="...">`` whose
action is the component's ``action_route`` ``ROUTE_REF`` prop -- a literal,
contract-grounded route, scheme-validated by the Renderer's page-level
URL-safety scan (CG-RND-009). A submit ``<button type="submit">`` is always
present so the form is fully usable with zero JavaScript. The actual input
fields are ``allowed_child_components`` (``atom.field.*``) -- component
nesting has no representation in ``ComponentManifest``/``LayoutPlan`` (the
J.8 finding), so the form renders its own disclosure/label/standards content
and submit control, and the field children render as their own sibling
instances; this is the honest carried limitation, not a fabricated field
set. No form fabricates an endpoint: a missing ``action_route`` is a missing
required prop and the Renderer raises a batched ``RenderError``.

CTA emission (§5.7, §16.2): a CTA is a navigation affordance -- rendered as
an ``<a href="target_route">label</a>`` inside the component's ``div`` root.
``cta.sticky.mobile`` declares no label content slot (only ``goal`` and
``target_route`` props), so its link takes the literal ``goal`` prop value
as an ``aria-label`` (a deterministic structural accessible name derived
from contract data, never fabricated marketing copy) -- a carried catalog
gap recorded in the AES-WEB-002J.9 report.
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

_TRUST_PREFIX = "ac-trust"
_CONTENT_PREFIX = "ac-content"
_FORM_PREFIX = "ac-form"
_CTA_PREFIX = "ac-cta"
_VERSION = "1.0.0"


def _disclosure_block(prefix: str, text: str) -> str:
    """A visible, never-suppressed disclosure paragraph (§17.1/§17.2)."""
    return element("p", {"class": class_names(prefix, "disclosure")}, escape(text))


def _submit_button() -> str:
    """The no-JS submit control every form carries (fixed structural chrome
    text, the J.8 precedent for non-commercial control labels)."""
    return element("button", {"type": "submit"}, "Submit")


# ---------------------------------------------------------------------------
# trust.* (§27.6)
# ---------------------------------------------------------------------------


def _emit_trust_reviews_summary(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Aggregate rating summary with a text equivalent (stars would be
    aria-hidden decoration, §12.4). Renders only the bound RatingSummary
    text -- never a fabricated score."""
    rating = first_value(resolved_content, "rating_summary")
    attrs = {
        "class": class_names(_TRUST_PREFIX, "reviews-summary", "inline"),
        **analytics_attrs("trust-reviews-summary", _VERSION, event="review_expand"),
    }
    return element("section", attrs, element("p", {}, escape(rating)))


def _emit_trust_reviews_list(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Individual reviews, one ``<article>`` each (§8.4 ReviewBlock). Density
    is the shared global axis (§7.1), applied as a class modifier."""
    density = instance.props.get("density", "comfortable")
    reviews = all_values(resolved_content, "reviews")
    items = "".join(
        element("li", {}, element("article", {}, escape(review)))
        for review in reviews
    )
    attrs = {
        "class": class_names(_TRUST_PREFIX, "reviews-list", density),
        **analytics_attrs("trust-reviews-list", _VERSION, event="review_expand"),
    }
    return element("section", attrs, element("ul", {}, items))


def _emit_trust_statistics_strip(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Evidenced statistics as a text list -- never color-only (§12.4)."""
    stats = all_values(resolved_content, "statistics")
    items = "".join(element("li", {}, escape(stat)) for stat in stats)
    attrs = {
        "class": class_names(_TRUST_PREFIX, "statistics-strip", "strip"),
        **analytics_attrs("trust-statistics-strip", _VERSION),
    }
    return element("section", attrs, element("ul", {}, items))


# ---------------------------------------------------------------------------
# content.faq.standard (§27.6)
# ---------------------------------------------------------------------------


def _emit_content_faq_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """FAQ as native ``<details>`` disclosures -- the no-JS accordion baseline
    (§12.6 Accordion, CG-A11Y-002, CG-RND-006). Each opaque QAPair renders as
    one disclosure; question/answer separation needs a structured QAPair
    block type the opaque text does not carry (documented gap)."""
    pairs = all_values(resolved_content, "qa_pairs")
    items = "".join(
        element(
            "details",
            {"class": class_names(_CONTENT_PREFIX, "faq-item")},
            element("summary", {}, escape(pair)),
        )
        for pair in pairs
    )
    attrs = {
        "class": class_names(_CONTENT_PREFIX, "faq-standard", "accordion"),
        **analytics_attrs("content-faq-standard", _VERSION),
    }
    return element("section", attrs, items)


# ---------------------------------------------------------------------------
# form.* (§27.6)
# ---------------------------------------------------------------------------


def _form_shell(
    *,
    impression_id: str,
    modifier: str,
    variant: str,
    action_route: str,
    inner: str,
) -> HtmlFragment:
    """The shared ``<form method="post">`` shell every form.* emitter builds,
    always ending in a no-JS submit control."""
    modifiers = [modifier, variant] if variant else [modifier]
    attrs = {
        "action": action_route,
        "class": class_names(_FORM_PREFIX, *modifiers),
        "method": "post",
        **analytics_attrs(
            impression_id, _VERSION, event="form_start"
        ),
    }
    return element("form", attrs, inner + _submit_button())


def _emit_form_lead_quote(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Lead/quote form with mandatory lead-handling disclosure (§17.2)."""
    disclosure = first_value(resolved_content, "disclosure")
    return _form_shell(
        impression_id="form-lead-quote",
        modifier="lead-quote",
        variant="",
        action_route=instance.props.get("action_route", ""),
        inner=_disclosure_block(_FORM_PREFIX, disclosure),
    )


def _emit_form_claim_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Listing-claim intake. Never renders a verification badge itself (E10
    stays owned by profile.header.business)."""
    return _form_shell(
        impression_id="form-claim-standard",
        modifier="claim-standard",
        variant="",
        action_route=instance.props.get("action_route", ""),
        inner="",
    )


def _emit_form_submission_listing(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """New-listing submission with an editorial-standards link (§27.6)."""
    standards = first_value(resolved_content, "standards_link")
    standards_html = (
        element(
            "p",
            {},
            element("a", {"href": standards}, escape(standards)),
        )
        if standards
        else ""
    )
    return _form_shell(
        impression_id="form-submission-listing",
        modifier="submission-listing",
        variant="",
        action_route=instance.props.get("action_route", ""),
        inner=standards_html,
    )


def _emit_form_correction_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Data-correction intake (no monetization on this role, §6.1)."""
    return _form_shell(
        impression_id="form-correction-standard",
        modifier="correction-standard",
        variant="",
        action_route=instance.props.get("action_route", ""),
        inner="",
    )


def _emit_form_capture_newsletter(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Newsletter capture with a signup prompt. Consent is an
    ``atom.field.choice`` child (never pre-checked, E8) rendered as its own
    sibling instance -- see module docstring."""
    label = first_value(resolved_content, "label")
    return _form_shell(
        impression_id="form-capture-newsletter",
        modifier="capture-newsletter",
        variant="inline",
        action_route=instance.props.get("action_route", ""),
        inner=element("p", {}, escape(label)),
    )


# ---------------------------------------------------------------------------
# cta.* (§27.6)
# ---------------------------------------------------------------------------


def _cta_link(
    *,
    impression_id: str,
    modifier: str,
    variant: str,
    target_route: str,
    label: str,
    aria_label: str = "",
) -> HtmlFragment:
    """The shared CTA affordance: a link to ``target_route`` inside the
    component's ``div`` root."""
    modifiers = [modifier, variant] if variant else [modifier]
    link_attrs: Dict[str, object] = {
        "class": class_names(_CTA_PREFIX, "action"),
        "href": target_route,
    }
    if aria_label:
        link_attrs["aria-label"] = aria_label
    root_attrs = {
        "class": class_names(_CTA_PREFIX, *modifiers),
        **analytics_attrs(impression_id, _VERSION, event="cta_click"),
    }
    return element("div", root_attrs, element("a", link_attrs, escape(label)))


def _emit_cta_claim_listing(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Claim-listing CTA (goal LISTING_CLAIM, §16.2 label class)."""
    return _cta_link(
        impression_id="cta-claim-listing",
        modifier="claim-listing",
        variant="inline",
        target_route=instance.props.get("target_route", ""),
        label=first_value(resolved_content, "label"),
    )


def _emit_cta_sticky_mobile(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Sticky mobile CTA (< md, single instance). No label slot exists on
    this contract, so the link's accessible name is the literal ``goal`` prop
    value (documented gap)."""
    goal = instance.props.get("goal", "")
    return _cta_link(
        impression_id="cta-sticky-mobile",
        modifier="sticky-mobile",
        variant="",
        target_route=instance.props.get("target_route", ""),
        label="",
        aria_label=goal,
    )


def _emit_cta_sponsor_inquiry(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Sponsor-inquiry CTA (goal SPONSORSHIP_INQUIRY, §6.1 sponsor-page)."""
    return _cta_link(
        impression_id="cta-sponsor-inquiry",
        modifier="sponsor-inquiry",
        variant="",
        target_route=instance.props.get("target_route", ""),
        label=first_value(resolved_content, "label"),
    )


def _emit_cta_submit_listing(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Submit-listing CTA (goal LISTING_SUBMISSION, §16.2 label class)."""
    return _cta_link(
        impression_id="cta-submit-listing",
        modifier="submit-listing",
        variant="",
        target_route=instance.props.get("target_route", ""),
        label=first_value(resolved_content, "label"),
    )


TRUST_CONVERSION_EMITTERS: Dict[str, EmitterFn] = {
    "trust.reviews.summary@1": _emit_trust_reviews_summary,
    "trust.reviews.list@1": _emit_trust_reviews_list,
    "trust.statistics.strip@1": _emit_trust_statistics_strip,
    "content.faq.standard@1": _emit_content_faq_standard,
    "form.lead.quote@1": _emit_form_lead_quote,
    "form.claim.standard@1": _emit_form_claim_standard,
    "form.submission.listing@1": _emit_form_submission_listing,
    "form.correction.standard@1": _emit_form_correction_standard,
    "form.capture.newsletter@1": _emit_form_capture_newsletter,
    "cta.claim.listing@1": _emit_cta_claim_listing,
    "cta.sticky.mobile@1": _emit_cta_sticky_mobile,
    "cta.sponsor.inquiry@1": _emit_cta_sponsor_inquiry,
    "cta.submit.listing@1": _emit_cta_submit_listing,
}
