"""Token-driven commercial visual layer for the Renderer (AES-WEB-001 §8.3;
ADR-WEB-VISUAL-TOKEN-APPLICATION; AES-WEB-002J.15; AES-WEB-002K.2).

The *applied* CSS the diagnostic sprint (AES-WEB-002J.14) found missing: a
reusable, deterministic set of visual rules that consume the resolved
``BrandPackage`` design tokens (compiled to ``:root`` custom properties by
``css_emitter``) and turn them into real color / typography / spacing / grid /
surface / border / radius / shadow / responsive treatment for the component
catalog. Engine behavior, not demo styling -- any site rendered through the
Renderer receives it.

AES-WEB-002K.2 (Commercial Visual System V2) expands this considerably: full
applied styling for the real surfaces J.15 never reached (the K.1/PILOT-PTF-1
listing card, category-discovery cards, utility/disclosure bar, wordmark,
hover/focus states throughout, a second small-breakpoint responsive tier, an
editorial reading measure, and a materially reworked hero/footer/profile
presentation) -- see ``docs/architecture/decisions/ADR-WEB-VISUAL-TOKEN-APPLICATION.md``
for the unchanged token-application discipline this wave continues rather
than replaces.

Discipline (per the ADR, unchanged):

* Every applied value references a ``var(--token)`` custom property; the only
  bare literals are structural/standards-safe keywords with no token
  equivalent (``0``, ``1fr``, ``100%``, ``none``, ``auto``, ``center``,
  ``flex``, ``grid``, the ``-9999px`` skip-link idiom, etc.).
* **Token gating:** a declaration is emitted only when *every* token it
  references is present in the build's token map, preserving the "no ``var()``
  without a backing custom property" invariant.
* **Tree-shaking:** family/variant/responsive rules are emitted only for
  component families actually present in the build (element-level global base
  rules always emit). AES-WEB-002K.2 promotes the CTA/button recipe to the
  global tier (see ``_GLOBAL_RULES`` below) because it is now the *shared*
  action treatment for anchors emitted by multiple families (hero, listing,
  profile, cta, form) -- family-gating a rule two or more families' emitters
  both depend on would make its presence depend on which family happened to
  be tree-shaken in, which is not a coherent contract.
* **Determinism:** rules are authored as fixed ordered tuples and emitted in
  that order; output never depends on dict/set iteration order.
* Media-query breakpoints use the *resolved* token value (CSS forbids
  ``var()`` in a media condition), mirroring ``css_emitter.compile_responsive_rules``.
  AES-WEB-002K.2 adds a second, smaller breakpoint tier (``breakpoint.sm``)
  alongside the existing ``breakpoint.md`` tier -- two intentional responsive
  steps (desktop -> tablet -> mobile) instead of one.
"""

from __future__ import annotations

from typing import Iterable, Tuple

from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.rendering.css_emitter import token_var
from engines.website_generation.rendering.html_emitter import TokenMap

# A declaration: (property, "%s"-template, token_ids). The template's "%s"
# slots are filled, in order, with ``var(--token)`` references. A declaration
# with no token ids is a purely structural rule (always emitted).
Declaration = Tuple[str, str, Tuple[str, ...]]
# A global rule: (selector, declarations). Always emitted (subject to gating).
GlobalRule = Tuple[str, Tuple[Declaration, ...]]
# A component/responsive rule additionally carries the component family that
# must be present for the rule to emit.
FamilyRule = Tuple[str, str, Tuple[Declaration, ...]]

_BREAKPOINT_MD_TOKEN = "breakpoint.md"
_BREAKPOINT_SM_TOKEN = "breakpoint.sm"


def _d(prop: str, template: str, *token_ids: str) -> Declaration:
    return (prop, template, token_ids)


# --------------------------------------------------------------------------- #
# Global element base (element selectors permitted only in this tier).
# --------------------------------------------------------------------------- #

_GLOBAL_RULES: Tuple[GlobalRule, ...] = (
    ("*,*::before,*::after", (_d("box-sizing", "border-box"),)),
    (
        "body",
        (
            _d("margin", "0"),
            _d("background", "%s", "color.surface.page"),
            _d("color", "%s", "color.text.default"),
            _d("font", "%s", "typography.body.default"),
        ),
    ),
    (
        "main",
        (
            _d("display", "block"),
            _d("max-width", "%s", "container.width.default"),
            _d("margin", "0 auto"),
            # AES-WEB-002K.2 §4: re-mapped from section.medium to
            # section.small -- thin content no longer sits inside two
            # stacked large paddings (hero + main both at section.large/
            # section.medium previously).
            _d("padding", "%s %s", "spacing.section.small", "spacing.stack.default"),
        ),
    ),
    ("a", (_d("color", "%s", "color.text.link"),)),
    ("a:hover", (_d("color", "%s", "color.action.primary"),)),
    ("img", (_d("max-width", "100%"), _d("height", "auto"))),
    (
        "h1",
        (_d("font", "%s", "typography.heading.display"), _d("margin", "%s 0", "spacing.stack.default")),
    ),
    ("h2", (_d("font", "%s", "typography.heading.2"), _d("margin", "%s 0", "spacing.stack.default"))),
    ("h3", (_d("font", "%s", "typography.heading.3"), _d("margin", "%s 0", "spacing.stack.default"))),
    ("p", (_d("margin", "%s 0", "spacing.stack.default"),)),
    ("table", (_d("border-collapse", "collapse"), _d("width", "100%"))),
    (
        "th,td",
        (
            _d("border", "%s %s", "border.default", "color.border.default"),
            _d("padding", "%s", "spacing.inline.default"),
            _d("text-align", "left"),
        ),
    ),
    ("button,input,select,textarea", (_d("font", "inherit"),)),
    (
        ":focus-visible",
        (_d("outline", "%s %s", "focus.ring.default", "color.focus.ring"),),
    ),
    # -- CTA/button system (promoted to global -- see module docstring) --- #
    (
        ".ac-cta--action",
        (
            _d("display", "inline-flex"),
            _d("align-items", "center"),
            _d("justify-content", "center"),
            _d("background", "%s", "color.action.primary"),
            _d("color", "%s", "color.text.inverse"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("border-radius", "%s", "radius.control"),
            _d("text-decoration", "none"),
            _d("border", "0"),
            _d("cursor", "pointer"),
        ),
    ),
    (".ac-cta--action:hover", (_d("background", "%s", "color.action.primary.hover"),)),
    (
        ".ac-cta--action:focus-visible",
        (_d("outline", "%s %s", "focus.ring.default", "color.focus.ring"),),
    ),
    # -- editorial reading measure (used by any content-bearing section) -- #
    (
        ".ac-content--section-editorial,.ac-content--description-business",
        (
            _d("max-width", "70ch"),
            _d("margin-left", "auto"),
            _d("margin-right", "auto"),
        ),
    ),
)


# --------------------------------------------------------------------------- #
# Component family / variant rules (tree-shaken by family presence).
# --------------------------------------------------------------------------- #

_COMPONENT_RULES: Tuple[FamilyRule, ...] = (
    # -- navigation & skip link ------------------------------------------- #
    (
        "nav",
        ".ac-nav--skip-link",
        (
            _d("position", "absolute"),
            _d("left", "-9999px"),
            _d("top", "0"),
            _d("background", "%s", "color.surface.inverse"),
            _d("color", "%s", "color.text.inverse"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
        ),
    ),
    ("nav", ".ac-nav--skip-link:focus", (_d("left", "0"),)),
    # -- utility/disclosure bar (AES-WEB-002K.2) --------------------------- #
    (
        "nav",
        ".ac-nav--utility-bar",
        (
            _d("display", "block"),
            _d("background", "%s", "color.surface.sponsored"),
            _d("color", "%s", "color.text.muted"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("text-align", "center"),
        ),
    ),
    (
        "nav",
        ".ac-nav--utility-bar a",
        (_d("color", "%s", "color.text.muted"),),
    ),
    (
        "nav",
        ".ac-nav--header-standard",
        (
            _d("display", "flex"),
            _d("align-items", "center"),
            _d("flex-wrap", "wrap"),
            _d("gap", "%s", "spacing.stack.default"),
            _d("padding", "%s %s", "spacing.stack.default", "spacing.section.small"),
            _d("background", "%s", "color.surface.raised"),
            _d("border-bottom", "%s %s", "border.default", "color.border.default"),
        ),
    ),
    (
        "nav",
        ".ac-nav--header-standard ul",
        (
            _d("display", "flex"),
            _d("flex-wrap", "wrap"),
            _d("align-items", "center"),
            _d("gap", "%s", "spacing.section.small"),
            _d("list-style", "none"),
            _d("margin", "0"),
            _d("padding", "0"),
        ),
    ),
    (
        "nav",
        ".ac-nav--header-standard a",
        (
            _d("color", "%s", "color.text.default"),
            _d("text-decoration", "none"),
            _d("font", "%s", "typography.label.default"),
        ),
    ),
    (
        "nav",
        ".ac-nav--header-standard a:hover,.ac-nav--header-standard a:focus-visible",
        (_d("color", "%s", "color.action.primary"),),
    ),
    # -- wordmark: the header's first link (deterministic -- "/" always
    # sorts first in nav_routes, AES-WEB-002K.2) -------------------------- #
    (
        "nav",
        ".ac-nav--header-standard li:first-child a",
        (
            _d("font", "%s", "typography.wordmark"),
            _d("color", "%s", "color.text.default"),
        ),
    ),
    (
        "nav",
        ".ac-nav--header-standard li:first-child a:hover,.ac-nav--header-standard li:first-child a:focus-visible",
        (_d("color", "%s", "color.action.primary"),),
    ),
    # -- hero (AES-WEB-002K.2: rescaled, both variants share the base) ----- #
    (
        "hero",
        ".ac-hero",
        (
            _d("background", "%s", "color.surface.featured"),
            _d("padding", "%s %s", "spacing.section.medium", "spacing.section.small"),
            _d("text-align", "center"),
        ),
    ),
    ("hero", ".ac-hero h1", (_d("font", "%s", "typography.heading.hero"),)),
    (
        "hero",
        ".ac-hero p",
        (
            _d("font", "%s", "typography.body.large"),
            _d("max-width", "60ch"),
            _d("margin-left", "auto"),
            _d("margin-right", "auto"),
        ),
    ),
    # Compact variant (category/city/service-area/editorial-guide pages):
    # smaller footprint than the homepage hero -- authored after the base
    # ``.ac-hero``/``.ac-hero h1`` rules above so equal-specificity
    # selectors resolve by source order (deterministic; see module
    # docstring's fixed-tuple-order discipline).
    (
        "hero",
        ".ac-hero--local-standard",
        (_d("padding", "%s %s", "spacing.section.small", "spacing.section.small"),),
    ),
    ("hero", ".ac-hero--local-standard h1", (_d("font", "%s", "typography.heading.display"),)),
    # -- content sections -------------------------------------------------- #
    ("content", ".ac-content", (_d("margin", "%s 0", "spacing.section.xsmall"),)),
    (
        "content",
        ".ac-content--section-editorial,.ac-content--description-business",
        (_d("font", "%s", "typography.body.large"),),
    ),
    # -- directory: category grid + results summary ----------------------- #
    (
        "directory",
        ".ac-directory--categories-grid ul",
        (
            _d("display", "grid"),
            _d("grid-template-columns", "%s", "grid.columns.3"),
            _d("gap", "%s", "grid.gap.default"),
            _d("list-style", "none"),
            _d("margin", "0"),
            _d("padding", "0"),
        ),
    ),
    (
        "directory",
        ".ac-directory--categories-grid li",
        (
            _d("background", "%s", "color.surface.raised"),
            _d("border", "%s %s", "border.default", "color.border.default"),
            _d("border-radius", "%s", "radius.card"),
            _d("box-shadow", "%s", "shadow.raised"),
            _d("padding", "0"),
            _d("overflow", "hidden"),
            _d("transition", "border-color 0.15s ease, box-shadow 0.15s ease"),
        ),
    ),
    (
        "directory",
        ".ac-directory--categories-grid li:hover,.ac-directory--categories-grid li:focus-within",
        (_d("border-color", "%s", "color.action.primary"),),
    ),
    (
        "directory",
        ".ac-directory--categories-grid li a",
        (
            _d("display", "block"),
            _d("padding", "%s", "spacing.section.xsmall"),
            _d("font", "%s", "typography.heading.3"),
            _d("color", "%s", "color.text.default"),
            _d("text-decoration", "none"),
        ),
    ),
    (
        "directory",
        ".ac-directory--results-summary",
        (_d("color", "%s", "color.text.muted"), _d("font", "%s", "typography.label.default")),
    ),
    # -- listings (AES-WEB-002K.2: full card treatment) -------------------- #
    (
        "listing",
        (
            ".ac-listing--card-standard,.ac-listing--card-featured,"
            ".ac-listing--card-sponsored,.ac-listing--row-compact"
        ),
        (
            _d("display", "block"),
            _d("background", "%s", "color.surface.raised"),
            _d("border", "%s %s", "border.default", "color.border.default"),
            _d("border-radius", "%s", "radius.card"),
            _d("box-shadow", "%s", "shadow.raised"),
            _d("padding", "%s", "spacing.stack.default"),
            _d("margin", "0 0 %s", "spacing.stack.default"),
            _d("transition", "border-color 0.15s ease, box-shadow 0.15s ease"),
        ),
    ),
    (
        "listing",
        (
            ".ac-listing--card-standard:hover,.ac-listing--card-featured:hover,"
            ".ac-listing--card-sponsored:hover,.ac-listing--row-compact:hover"
        ),
        (_d("border-color", "%s", "color.action.primary"),),
    ),
    # AES-WEB-002M.2: the card's optional primary image (media activation
    # only -- not a card redesign). Full inner-card width with the card's
    # own radius; a fixed aspect ratio + object-fit:cover so mixed image
    # dimensions never distort the card grid. The 3/2 ratio is
    # constants/brand.py's aspect.card token value ("3:2") expressed in CSS
    # aspect-ratio syntax -- documented duplication of the ratio, since the
    # token's colon form is not valid CSS and re-tokenizing brand scales is
    # out of M.2 scope. width:100% + aspect-ratio is inherently responsive;
    # an image-less card emits no element at all (no empty frame).
    (
        "listing",
        ".ac-listing--card-image",
        (
            _d("display", "block"),
            _d("width", "100%"),
            _d("aspect-ratio", "3/2"),  # = aspect.card "3:2"
            _d("object-fit", "cover"),
            _d("border-radius", "%s", "radius.card"),
            _d("margin", "0 0 %s", "spacing.stack.default"),
        ),
    ),
    (
        "listing",
        (
            ".ac-listing--card-standard h2,.ac-listing--card-featured h2,"
            ".ac-listing--card-sponsored h2,.ac-listing--row-compact h2"
        ),
        (
            _d("font", "%s", "typography.heading.3"),
            _d("margin", "0 0 %s", "spacing.inline.default"),
        ),
    ),
    (
        "listing",
        (
            ".ac-listing--card-standard h2 a,.ac-listing--card-featured h2 a,"
            ".ac-listing--card-sponsored h2 a,.ac-listing--row-compact h2 a"
        ),
        (_d("color", "%s", "color.text.default"), _d("text-decoration", "none")),
    ),
    (
        "listing",
        (
            ".ac-listing--card-standard h2 a:hover,.ac-listing--card-featured h2 a:hover,"
            ".ac-listing--card-sponsored h2 a:hover,.ac-listing--row-compact h2 a:hover"
        ),
        (_d("color", "%s", "color.action.primary"), _d("text-decoration", "underline")),
    ),
    (
        "listing",
        ".ac-listing--area,.ac-listing--rating",
        (
            _d("color", "%s", "color.text.muted"),
            _d("font", "%s", "typography.label.default"),
            _d("margin", "%s 0", "spacing.inline.default"),
        ),
    ),
    (
        "listing",
        ".ac-listing--badge",
        (
            _d("display", "inline-block"),
            _d("background", "%s", "color.surface.sponsored"),
            _d("color", "%s", "color.text.default"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("border-radius", "%s", "radius.badge"),
            _d("margin", "0 0 %s", "spacing.inline.default"),
        ),
    ),
    (
        "listing",
        ".ac-listing--disclosure",
        (
            _d("background", "%s", "color.surface.sponsored"),
            _d("color", "%s", "color.text.muted"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("border-radius", "%s", "radius.control"),
            _d("margin", "0 0 %s", "spacing.stack.default"),
        ),
    ),
    (
        "listing",
        ".ac-listing--card-standard .ac-cta--action,.ac-listing--row-compact .ac-cta--action,"
        ".ac-listing--card-featured .ac-cta--action,.ac-listing--card-sponsored .ac-cta--action",
        (_d("margin-top", "%s", "spacing.inline.default"),),
    ),
    # -- monetization: disclosure + sponsor ribbon ------------------------ #
    (
        "monetization",
        ".ac-monetization--disclosure-advertising",
        (
            _d("background", "%s", "color.surface.sponsored"),
            _d("color", "%s", "color.text.muted"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("text-align", "center"),
        ),
    ),
    (
        "monetization",
        ".ac-monetization--ribbon-sponsor",
        (
            _d("display", "inline-block"),
            _d("background", "%s", "color.surface.sponsored"),
            _d("color", "%s", "color.text.default"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("border-radius", "%s", "radius.badge"),
        ),
    ),
    # -- trust ------------------------------------------------------------- #
    (
        "trust",
        ".ac-trust--statistics-strip ul",
        (
            _d("display", "flex"),
            _d("flex-wrap", "wrap"),
            _d("gap", "%s", "grid.gap.default"),
            _d("list-style", "none"),
            _d("margin", "0"),
            _d("padding", "0"),
        ),
    ),
    ("trust", ".ac-trust--statistics-strip li", (_d("font", "%s", "typography.price.default"),)),
    ("trust", ".ac-trust--reviews-summary", (_d("color", "%s", "color.text.muted"),)),
    # -- profile ------------------------------------------------------------ #
    (
        "profile",
        ".ac-profile--header-business",
        (
            _d("background", "%s", "color.surface.featured"),
            _d("padding", "%s %s", "spacing.section.small", "spacing.stack.default"),
            _d("text-align", "center"),
        ),
    ),
    # AES-WEB-002M.2: the profile's optional primary image -- visually
    # strong but bounded (max-width caps it inside the centered header;
    # margin auto centers it), fixed 16/9 ratio + object-fit:cover. The
    # ratio is constants/brand.py's aspect.hero token value ("16:9") in CSS
    # syntax -- same documented duplication as .ac-listing--card-image. An
    # image-less profile emits no element at all (no empty frame).
    (
        "profile",
        ".ac-profile--primary-image",
        (
            _d("display", "block"),
            _d("width", "100%"),
            _d("max-width", "56rem"),
            _d("aspect-ratio", "16/9"),  # = aspect.hero "16:9"
            _d("object-fit", "cover"),
            _d("border-radius", "%s", "radius.card"),
            _d("margin", "%s auto 0", "spacing.stack.default"),
        ),
    ),
    (
        "profile",
        ".ac-profile--contact-panel",
        (
            _d("display", "block"),
            _d("background", "%s", "color.surface.raised"),
            _d("border", "%s %s", "border.default", "color.border.default"),
            _d("border-radius", "%s", "radius.card"),
            _d("box-shadow", "%s", "shadow.raised"),
            _d("padding", "%s", "spacing.stack.default"),
        ),
    ),
    (
        "profile",
        ".ac-profile--disclosure",
        (
            _d("background", "%s", "color.surface.sponsored"),
            _d("color", "%s", "color.text.muted"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("border-radius", "%s", "radius.control"),
            _d("margin-top", "%s", "spacing.stack.default"),
        ),
    ),
    # -- profile hours table: softened row treatment ----------------------- #
    (
        "profile",
        ".ac-profile--hours-table",
        (
            _d("background", "%s", "color.surface.raised"),
            _d("border", "%s %s", "border.default", "color.border.default"),
            _d("border-radius", "%s", "radius.card"),
            _d("padding", "%s", "spacing.stack.default"),
        ),
    ),
    (
        "profile",
        ".ac-profile--hours-table th,.ac-profile--hours-table td",
        (
            _d("border", "0"),
            _d("border-bottom", "%s %s", "border.default", "color.border.default"),
            _d("padding", "%s 0", "spacing.inline.default"),
        ),
    ),
    (
        "profile",
        ".ac-profile--hours-table tbody th",
        (
            _d("color", "%s", "color.text.muted"),
            _d("font-weight", "400"),
        ),
    ),
    (
        "profile",
        ".ac-profile--hours-table tbody tr:last-child th,.ac-profile--hours-table tbody tr:last-child td",
        (_d("border-bottom", "0"),),
    ),
    # -- two-column profile layout (CSS-only, no markup/shell-class change:
    # ``:has()`` scopes to any <main> that hosts a contact panel, i.e. every
    # business-profile page and no other page role) ----------------------- #
    (
        "profile",
        "main:has(>.ac-profile--contact-panel)",
        (
            _d("display", "flex"),
            _d("flex-wrap", "wrap"),
            _d("align-items", "flex-start"),
            _d("gap", "%s", "grid.gap.default"),
        ),
    ),
    (
        "profile",
        "main:has(>.ac-profile--contact-panel) > *",
        (_d("flex", "1 1 480px"), _d("min-width", "0")),
    ),
    (
        "profile",
        "main:has(>.ac-profile--contact-panel) > .ac-profile--contact-panel",
        (_d("flex", "0 1 320px"), _d("order", "2")),
    ),
    # -- CTA button (form.* buttons share the same recipe -- global tier's
    # .ac-cta--action covers anchors; <button> needs its own rule) -------- #
    (
        "form",
        ".ac-form--lead-quote,.ac-form--capture-newsletter",
        (
            _d("background", "%s", "color.surface.raised"),
            _d("border", "%s %s", "border.default", "color.border.default"),
            _d("border-radius", "%s", "radius.card"),
            _d("padding", "%s", "spacing.stack.default"),
            _d("margin", "%s 0", "spacing.stack.default"),
        ),
    ),
    (
        "form",
        ".ac-form--disclosure",
        (_d("color", "%s", "color.text.muted"), _d("font", "%s", "typography.label.default")),
    ),
    (
        "form",
        ".ac-form button",
        (
            _d("display", "inline-flex"),
            _d("align-items", "center"),
            _d("background", "%s", "color.action.primary"),
            _d("color", "%s", "color.text.inverse"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("border", "none"),
            _d("border-radius", "%s", "radius.control"),
            _d("cursor", "pointer"),
        ),
    ),
    ("form", ".ac-form button:hover", (_d("background", "%s", "color.action.primary.hover"),)),
    # -- footer (legal.footer.directory; AES-WEB-002K.2 redesign) ---------- #
    (
        "legal",
        ".ac-legal--footer-directory",
        (
            _d("display", "block"),
            _d("background", "%s", "color.surface.inverse"),
            _d("color", "%s", "color.text.inverse"),
            _d("padding", "%s %s", "spacing.section.small", "spacing.section.small"),
        ),
    ),
    ("legal", ".ac-legal--footer-directory a", (_d("color", "%s", "color.text.inverse"),)),
    ("legal", ".ac-legal--footer-directory a:hover", (_d("text-decoration", "underline"),)),
    (
        "legal",
        ".ac-legal--footer-directory p",
        (
            _d("font", "%s", "typography.label.default"),
            _d("max-width", "70ch"),
            _d("margin", "0 0 %s", "spacing.inline.default"),
        ),
    ),
    (
        "legal",
        ".ac-legal--footer-directory ul",
        (
            _d("display", "flex"),
            _d("flex-wrap", "wrap"),
            _d("gap", "%s", "spacing.section.small"),
            _d("list-style", "none"),
            _d("margin", "%s 0 0", "spacing.section.xsmall"),
            _d("padding", "%s 0 0", "spacing.stack.default"),
            _d("border-top", "%s", "border.default"),
        ),
    ),
)


# --------------------------------------------------------------------------- #
# Responsive collapse -- two intentional tiers (AES-WEB-002K.2): tablet
# (<= breakpoint.md, 1024px) and mobile (<= breakpoint.sm, 640px).
# --------------------------------------------------------------------------- #

_RESPONSIVE_RULES_MD: Tuple[FamilyRule, ...] = (
    ("directory", ".ac-directory--categories-grid ul", (_d("grid-template-columns", "%s", "grid.columns.2"),)),
    (
        "nav",
        ".ac-nav--header-standard",
        (_d("flex-direction", "column"), _d("align-items", "flex-start")),
    ),
    (
        "profile",
        "main:has(>.ac-profile--contact-panel)",
        (_d("flex-direction", "column"),),
    ),
    ("trust", ".ac-trust--statistics-strip ul", (_d("flex-direction", "column"),)),
    ("legal", ".ac-legal--footer-directory ul", (_d("flex-direction", "column"),)),
)

_RESPONSIVE_RULES_SM: Tuple[FamilyRule, ...] = (
    ("directory", ".ac-directory--categories-grid ul", (_d("grid-template-columns", "1fr"),)),
    (
        "hero",
        ".ac-hero",
        (_d("padding", "%s %s", "spacing.section.small", "spacing.stack.default"),),
    ),
    ("hero", ".ac-hero h1", (_d("font", "%s", "typography.heading.display"),)),
    (
        "hero",
        ".ac-hero--local-standard",
        (_d("padding", "%s %s", "spacing.section.xsmall", "spacing.stack.default"),),
    ),
    (
        "listing",
        ".ac-listing--card-standard .ac-cta--action,.ac-listing--row-compact .ac-cta--action,"
        ".ac-listing--card-featured .ac-cta--action,.ac-listing--card-sponsored .ac-cta--action",
        (_d("display", "flex"), _d("width", "100%")),
    ),
)


# --------------------------------------------------------------------------- #
# Compilation.
# --------------------------------------------------------------------------- #

def _emit_declarations(declarations: Tuple[Declaration, ...], tokens: TokenMap) -> str:
    parts = []
    for prop, template, token_ids in declarations:
        if not all(token_id in tokens for token_id in token_ids):
            continue
        # Structural (no-token) declarations use the template verbatim -- it
        # may contain a literal ``%`` (e.g. ``100%``); only token-bearing
        # templates carry ``%s`` slots to fill.
        if token_ids:
            value = template % tuple(token_var(token_id) for token_id in token_ids)
        else:
            value = template
        parts.append("%s:%s" % (prop, value))
    return ";".join(parts)


def _emit_global_rules(rules: Tuple[GlobalRule, ...], tokens: TokenMap) -> str:
    out = []
    for selector, declarations in rules:
        body = _emit_declarations(declarations, tokens)
        if body:
            out.append("%s{%s}" % (selector, body))
    return "".join(out)


def _emit_family_rules(
    rules: Tuple[FamilyRule, ...], tokens: TokenMap, families: "frozenset[str]"
) -> str:
    out = []
    for family, selector, declarations in rules:
        if family not in families:
            continue
        body = _emit_declarations(declarations, tokens)
        if body:
            out.append("%s{%s}" % (selector, body))
    return "".join(out)


def _present_families(definitions: Iterable[ComponentDefinition]) -> "frozenset[str]":
    return frozenset(d.component_id.split(".", 1)[0] for d in definitions)


def compile_visual_styles(
    definitions: Iterable[ComponentDefinition], tokens: TokenMap
) -> str:
    """The applied-visual CSS for one build: global element base, then
    tree-shaken family/variant component rules, then two tree-shaken
    responsive ``@media`` blocks (tablet, then mobile -- AES-WEB-002K.2) --
    all token-gated and deterministically ordered
    (ADR-WEB-VISUAL-TOKEN-APPLICATION)."""
    families = _present_families(definitions)
    globals_css = _emit_global_rules(_GLOBAL_RULES, tokens)
    components_css = _emit_family_rules(_COMPONENT_RULES, tokens, families)

    responsive_css = ""
    md_value = tokens.get(_BREAKPOINT_MD_TOKEN)
    if md_value:
        inner = _emit_family_rules(_RESPONSIVE_RULES_MD, tokens, families)
        if inner:
            responsive_css += "@media (max-width: %s){%s}" % (md_value, inner)
    sm_value = tokens.get(_BREAKPOINT_SM_TOKEN)
    if sm_value:
        inner = _emit_family_rules(_RESPONSIVE_RULES_SM, tokens, families)
        if inner:
            responsive_css += "@media (max-width: %s){%s}" % (sm_value, inner)

    return "".join((globals_css, components_css, responsive_css))
