"""Token-driven commercial visual layer for the Renderer (AES-WEB-001 §8.3;
ADR-WEB-VISUAL-TOKEN-APPLICATION; AES-WEB-002J.15).

The *applied* CSS the diagnostic sprint (AES-WEB-002J.14) found missing: a
reusable, deterministic set of visual rules that consume the resolved
``BrandPackage`` design tokens (compiled to ``:root`` custom properties by
``css_emitter``) and turn them into real color / typography / spacing / grid /
surface / border / radius / shadow / responsive treatment for the component
catalog. Engine behavior, not demo styling -- any site rendered through the
Renderer receives it.

Discipline (per the ADR):

* Every applied value references a ``var(--token)`` custom property; the only
  bare literals are structural/standards-safe keywords with no token
  equivalent (``0``, ``1fr``, ``100%``, ``none``, ``auto``, ``center``,
  ``flex``, ``grid``, the ``-9999px`` skip-link idiom, etc.).
* **Token gating:** a declaration is emitted only when *every* token it
  references is present in the build's token map, preserving the "no ``var()``
  without a backing custom property" invariant.
* **Tree-shaking:** family/variant/responsive rules are emitted only for
  component families actually present in the build (element-level global base
  rules always emit).
* **Determinism:** rules are authored as fixed ordered tuples and emitted in
  that order; output never depends on dict/set iteration order.
* Media-query breakpoints use the *resolved* token value (CSS forbids
  ``var()`` in a media condition), mirroring ``css_emitter.compile_responsive_rules``.
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

_BREAKPOINT_TOKEN = "breakpoint.md"


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
            _d("padding", "%s %s", "spacing.section.medium", "spacing.stack.default"),
        ),
    ),
    ("a", (_d("color", "%s", "color.text.link"),)),
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
            _d("gap", "%s", "spacing.stack.default"),
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
    # -- hero -------------------------------------------------------------- #
    (
        "hero",
        ".ac-hero",
        (
            _d("background", "%s", "color.surface.featured"),
            _d("padding", "%s %s", "spacing.section.large", "spacing.section.small"),
            _d("text-align", "center"),
        ),
    ),
    # -- content sections -------------------------------------------------- #
    ("content", ".ac-content", (_d("margin", "%s 0", "spacing.section.small"),)),
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
            _d("padding", "%s", "spacing.stack.default"),
        ),
    ),
    (
        "directory",
        ".ac-directory--results-summary",
        (_d("color", "%s", "color.text.muted"), _d("font", "%s", "typography.label.default")),
    ),
    # -- listings ---------------------------------------------------------- #
    (
        "listing",
        ".ac-listing--row-compact",
        (
            _d("display", "block"),
            _d("background", "%s", "color.surface.raised"),
            _d("border", "%s %s", "border.default", "color.border.default"),
            _d("border-radius", "%s", "radius.card"),
            _d("box-shadow", "%s", "shadow.raised"),
            _d("padding", "%s", "spacing.stack.default"),
            _d("margin", "%s 0", "spacing.stack.default"),
        ),
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
    # -- profile: contact panel ------------------------------------------- #
    (
        "profile",
        ".ac-profile--contact-panel",
        (
            _d("display", "block"),
            _d("background", "%s", "color.surface.raised"),
            _d("border", "%s %s", "border.default", "color.border.default"),
            _d("border-radius", "%s", "radius.card"),
            _d("padding", "%s", "spacing.stack.default"),
        ),
    ),
    # -- CTA button -------------------------------------------------------- #
    (
        "cta",
        ".ac-cta--action",
        (
            _d("display", "inline-flex"),
            _d("align-items", "center"),
            _d("background", "%s", "color.action.primary"),
            _d("color", "%s", "color.text.inverse"),
            _d("font", "%s", "typography.label.default"),
            _d("padding", "%s %s", "spacing.inline.default", "spacing.stack.default"),
            _d("border-radius", "%s", "radius.control"),
            _d("text-decoration", "none"),
        ),
    ),
    ("cta", ".ac-cta--action:hover", (_d("background", "%s", "color.action.primary.hover"),)),
    (
        "cta",
        ".ac-cta--action:focus-visible",
        (_d("outline", "%s %s", "focus.ring.default", "color.focus.ring"),),
    ),
    # -- forms ------------------------------------------------------------- #
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
    # -- footer (legal.footer.directory) ---------------------------------- #
    (
        "legal",
        ".ac-legal--footer-directory",
        (
            _d("display", "block"),
            _d("background", "%s", "color.surface.inverse"),
            _d("color", "%s", "color.text.inverse"),
            _d("padding", "%s %s", "spacing.section.medium", "spacing.section.small"),
        ),
    ),
    ("legal", ".ac-legal--footer-directory a", (_d("color", "%s", "color.text.inverse"),)),
    (
        "legal",
        ".ac-legal--footer-directory ul",
        (
            _d("display", "flex"),
            _d("flex-wrap", "wrap"),
            _d("gap", "%s", "spacing.stack.default"),
            _d("list-style", "none"),
            _d("margin", "%s 0", "spacing.stack.default"),
            _d("padding", "0"),
        ),
    ),
)


# --------------------------------------------------------------------------- #
# Responsive collapse (inside one @media (max-width: breakpoint.md)).
# --------------------------------------------------------------------------- #

_RESPONSIVE_RULES: Tuple[FamilyRule, ...] = (
    ("directory", ".ac-directory--categories-grid ul", (_d("grid-template-columns", "1fr"),)),
    (
        "nav",
        ".ac-nav--header-standard",
        (_d("flex-direction", "column"), _d("align-items", "flex-start")),
    ),
    ("trust", ".ac-trust--statistics-strip ul", (_d("flex-direction", "column"),)),
    ("legal", ".ac-legal--footer-directory ul", (_d("flex-direction", "column"),)),
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
    tree-shaken family/variant component rules, then a single tree-shaken
    responsive ``@media`` block -- all token-gated and deterministically
    ordered (ADR-WEB-VISUAL-TOKEN-APPLICATION)."""
    families = _present_families(definitions)
    globals_css = _emit_global_rules(_GLOBAL_RULES, tokens)
    components_css = _emit_family_rules(_COMPONENT_RULES, tokens, families)

    responsive_css = ""
    breakpoint_value = tokens.get(_BREAKPOINT_TOKEN)
    if breakpoint_value:
        inner = _emit_family_rules(_RESPONSIVE_RULES, tokens, families)
        if inner:
            responsive_css = "@media (max-width: %s){%s}" % (breakpoint_value, inner)

    return "".join((globals_css, components_css, responsive_css))
