"""Pure HTML emitters for the ``layout.*``/``atom.*`` foundation primitives
(AES-WEB-002 §27.2; catalog: ``components/catalog/layout_atoms.py``).

Fifteen components, fifteen emitter functions, one explicit ``Dict[str,
EmitterFn]`` table (``LAYOUT_ATOMS_EMITTERS``) -- no dynamic scanning, no
decorators (§20.1, ADR-06). Every function has the uniform signature
``(instance, resolved_content, tokens, layout_ctx) -> HtmlFragment`` and
reads only what it is passed (§20.1 "never read anything not passed in").

Per-component identity (``class_prefix``, the analytics ``impression_id``,
``default_variant``) is a static fact about each registered
``ComponentDefinition`` -- §20.1's four-argument signature carries no fifth
"definition" parameter, so each emitter closes over its own component's
already-known identity as module-level literals, exactly mirroring how the
catalog's own ``_analytics()`` helper computed the same ``impression_id``
(dots -> dashes) at registration time. Duplicating these constants here is
not a maintenance risk: an emitter is written once, specifically for the
one ``emitter_key`` it is registered under, and a mismatch would fail the
emitter-integrity test (every J.8 key must resolve exactly once) or a
snapshot test immediately.

Content-binding convention (AES-WEB-002J.8, documented decision -- see
``renderer.py`` module docstring for the full reasoning): a
``ContentBlock``-backed value -- whether it arrived via ``content_refs``
(a content slot) or via a ``CONTENT_BLOCK_REF``/``ROUTE_REF`` prop -- is
resolved by ``renderer.py`` into this module's ``resolved_content`` mapping
before any emitter runs; every URL-shaped value is scheme-validated
(CG-RND-009) before an emitter ever sees it. Emitters trust the values they
are given and never re-resolve or re-validate.

No nesting/composition: ``ComponentManifest``/``LayoutPlan`` carry no
parent-child relationship between component instances (§8.2 preflight
finding) -- every instance renders as a structurally complete but childless
element. Container primitives (section/grid/stack/split/card-shell) are
therefore empty shells in this delivery; composing real children into them
is a future capability gated on a nesting-capable artifact, not invented
here.

Variant selection: every emitter renders its component's registry
``default_variant`` (a static per-component fact, same reasoning as
``class_prefix`` above) -- ``selection_trace.chosen_variant`` is not read,
matching the established "ignored by downstream engines" doctrine
(AES-WEB-002 §14.3/ADR-14 states the Layout Engine ignores the trace; the
same reasoning applies here since the trace's slot-id keying does not
reliably map back to a ``ComponentPlacement.component_index``).
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
    dom_id,
    element,
    escape,
    first_value,
)

_LAYOUT_PREFIX = "ac-layout"
_ATOM_PREFIX = "ac-atom"
_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# layout.* (§27.2 rows 1-6)
# ---------------------------------------------------------------------------


def _emit_layout_shell_page(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """The document shell (§9.1/§9.3): doctype, ``<html>``/``<head>``/
    ``<body>``, and the already-assembled region body handed in via the
    reserved ``__shell_body__`` synthetic key (``renderer.py`` assembles
    every other region's markup first and passes the joined result here --
    see that module's page-orchestration docstring). No head/JSON-LD
    injection is emitted (Assembly's job, AES-WEB-001 §5.9/§8.4); this emits
    only the two structural meta tags every document needs."""
    body = first_value(resolved_content, "__shell_body__")
    head = "".join(
        (
            element("meta", {"charset": "utf-8"}),
            element(
                "meta",
                {
                    "name": "viewport",
                    "content": "width=device-width, initial-scale=1",
                },
            ),
        )
    )
    body_attrs = {
        "class": class_names(_LAYOUT_PREFIX, "shell-page"),
        **analytics_attrs("layout-shell-page", _VERSION),
    }
    html_doc = (
        "<!doctype html>"
        + element(
            "html",
            {"lang": "en"},
            element("head", {}, head) + element("body", body_attrs, body),
        )
    )
    return html_doc


def _emit_layout_section_container(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Body section container owning its own H2 (§9.3: heading ownership;
    parental spacing is a layout/CSS concern, never child-declared)."""
    heading_text = first_value(resolved_content, "heading")
    heading_html = element("h2", {}, escape(heading_text)) if heading_text else ""
    attrs = {
        "class": class_names(_LAYOUT_PREFIX, "section-container", "standard"),
        **analytics_attrs("layout-section-container", _VERSION),
    }
    return element("section", attrs, heading_html)


def _emit_layout_grid_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Column grid (§9.2: max 4 desktop columns); collapses per
    ``layout_ctx.responsive.collapse_behavior`` (CSS-owned, §11)."""
    columns = instance.props.get("columns", "2")
    attrs = {
        "class": class_names(_LAYOUT_PREFIX, "grid-standard", "cols-" + columns),
        **analytics_attrs("layout-grid-standard", _VERSION),
    }
    return element("div", attrs)


def _emit_layout_stack_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Vertical rhythm owner: stacks children at a token gap."""
    attrs = {
        "class": class_names(_LAYOUT_PREFIX, "stack-standard"),
        **analytics_attrs("layout-stack-standard", _VERSION),
    }
    return element("div", attrs)


def _emit_layout_split_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Two-region split at a declared desktop ratio, stacking below md with
    an explicit mobile order (§11.5)."""
    ratio = instance.props.get("ratio", "50-50")
    attrs = {
        "class": class_names(
            _LAYOUT_PREFIX, "split-standard", "media-left", "ratio-" + ratio
        ),
        **analytics_attrs("layout-split-standard", _VERSION),
    }
    return element("div", attrs)


def _emit_layout_card_shell(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Pure surface card shell (§9.4: the only permitted outer card)."""
    attrs = {
        "class": class_names(_LAYOUT_PREFIX, "card-shell", "raised"),
        **analytics_attrs("layout-card-shell", _VERSION),
    }
    return element("div", attrs)


# ---------------------------------------------------------------------------
# atom.* (§27.2 rows 7-15)
# ---------------------------------------------------------------------------


def _emit_atom_button_action(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Action button: real ``<button type="button">``, 44px touch target
    and mandatory focus ring are CSS/token concerns (§12.2)."""
    weight = instance.props.get("weight", "primary")
    label = first_value(resolved_content, "label")
    attrs = {
        "type": "button",
        "class": class_names(_ATOM_PREFIX, "button-action", weight),
        **analytics_attrs(
            "atom-button-action", _VERSION, event="component_interaction"
        ),
    }
    return element("button", attrs, escape(label))


def _emit_atom_link_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Link primitive bound to a LinkSpec content block (§8.4/§13.3). The
    single resolved string serves as both ``href`` and visible text -- this
    component declares no separate visible-label slot (a documented catalog
    gap; see the AES-WEB-002J.8 implementation report)."""
    href = first_value(resolved_content, "link")
    attrs = {
        "class": class_names(_ATOM_PREFIX, "link-standard", "inline"),
        "href": href,
        **analytics_attrs(
            "atom-link-standard", _VERSION, event="component_interaction"
        ),
    }
    return element("a", attrs, escape(href))


def _emit_atom_image_responsive(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Responsive image primitive. No CAS access exists in the Renderer
    (explicit AES-WEB-002J.8 exclusion), so the ``asset`` prop's opaque
    reference string is emitted as-is as ``src``; no accessible-label
    slot/prop is declared on this component (a documented catalog gap), so
    ``alt=""`` -- the spec-legal "decorative image" marker (WCAG technique
    H67) -- is emitted rather than inventing describing text."""
    asset = instance.props.get("asset", "")
    loading = instance.props.get("loading", "lazy")
    attrs = {
        "alt": "",
        "class": class_names(_ATOM_PREFIX, "image-responsive"),
        "loading": loading,
        "src": asset,
        **analytics_attrs("atom-image-responsive", _VERSION),
    }
    return element("img", attrs)


def _emit_atom_icon_standard(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Icon primitive: labeled via ``icon_label`` or declared decorative
    (§12.4). No CAS access, so the asset reference travels as an inert
    ``data-asset`` attribute rather than a resolved image source."""
    asset = instance.props.get("asset", "")
    icon_label = instance.props.get("icon_label", "")
    decorative = instance.props.get("decorative", "false") == "true"
    attrs: Dict[str, object] = {
        "class": class_names(_ATOM_PREFIX, "icon-standard"),
        "data-asset": asset,
        "role": "img",
        **analytics_attrs("atom-icon-standard", _VERSION),
    }
    if decorative or not icon_label:
        attrs["aria-hidden"] = "true"
        attrs.pop("role", None)
    else:
        attrs["aria-label"] = icon_label
    return element("span", attrs)


def _emit_atom_badge_status(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Status badge: kind maps to a surface token, never fakes verification/
    paid states (E10, §6.3 non-confusion rule)."""
    kind = instance.props.get("kind", "verified")
    label = first_value(resolved_content, "label")
    attrs = {
        "class": class_names(_ATOM_PREFIX, "badge-status", kind),
        **analytics_attrs("atom-badge-status", _VERSION),
    }
    return element("span", attrs, escape(label))


def _emit_atom_alert_notice(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Notice primitive: severity selects ``role=status`` vs ``role=alert``
    (§12.5)."""
    severity = instance.props.get("severity", "info")
    body = first_value(resolved_content, "body")
    role = "alert" if severity == "error" else "status"
    attrs = {
        "class": class_names(_ATOM_PREFIX, "alert-notice", severity),
        "role": role,
        **analytics_attrs("atom-alert-notice", _VERSION),
    }
    return element("div", attrs, escape(body))


def _emit_atom_field_text(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Text input primitive: programmatic label association, described-by
    instruction linkage, autocomplete on identity fields (§12.3)."""
    input_kind = instance.props.get("input_kind", "text")
    autocomplete = instance.props.get("autocomplete", "off")
    required = instance.props.get("required", "false") == "true"
    label = first_value(resolved_content, "label")
    error = first_value(resolved_content, "error")
    instructions = first_value(resolved_content, "instructions")
    field_id = dom_id("atom-field-text", layout_ctx.component_index)
    error_id = field_id + "-error"
    instructions_id = field_id + "-instructions"
    describedby_parts = [
        part for part in (instructions_id if instructions else "", error_id if error else "") if part
    ]
    input_attrs: Dict[str, object] = {
        "autocomplete": autocomplete,
        "class": class_names(_ATOM_PREFIX, "field-text"),
        "id": field_id,
        "required": required,
        "type": input_kind,
        **analytics_attrs(
            "atom-field-text", _VERSION, event="component_interaction"
        ),
    }
    if describedby_parts:
        input_attrs["aria-describedby"] = " ".join(describedby_parts)
    parts = [element("label", {"for": field_id}, escape(label))]
    if instructions:
        parts.append(element("div", {"id": instructions_id}, escape(instructions)))
    parts.append(element("input", input_attrs))
    if error:
        parts.append(
            element("div", {"id": error_id, "role": "alert"}, escape(error))
        )
    return "".join(parts)


def _emit_atom_field_select(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Native select primitive with programmatic label; options bound from
    a typed content block (never free-typed)."""
    required = instance.props.get("required", "false") == "true"
    label = first_value(resolved_content, "label")
    error = first_value(resolved_content, "error")
    option_values = all_values(resolved_content, "options")
    field_id = dom_id("atom-field-select", layout_ctx.component_index)
    error_id = field_id + "-error"
    select_attrs: Dict[str, object] = {
        "class": class_names(_ATOM_PREFIX, "field-select"),
        "id": field_id,
        "required": required,
        **analytics_attrs(
            "atom-field-select", _VERSION, event="component_interaction"
        ),
    }
    if error:
        select_attrs["aria-describedby"] = error_id
    options_html = "".join(
        element("option", {"value": escape(value)}, escape(value))
        for value in option_values
    )
    parts = [
        element("label", {"for": field_id}, escape(label)),
        element("select", select_attrs, options_html),
    ]
    if error:
        parts.append(
            element("div", {"id": error_id, "role": "alert"}, escape(error))
        )
    return "".join(parts)


def _emit_atom_field_choice(
    instance: ComponentInstance,
    resolved_content: ResolvedContent,
    tokens: TokenMap,
    layout_ctx: LayoutContext,
) -> HtmlFragment:
    """Radio/checkbox group primitive: fieldset/legend grouping; never
    pre-checked (E8, §12.3)."""
    mode = instance.props.get("mode", "radio")
    legend = first_value(resolved_content, "legend")
    error = first_value(resolved_content, "error")
    option_values = all_values(resolved_content, "options")
    group_name = dom_id("atom-field-choice", layout_ctx.component_index)
    options_html = "".join(
        element(
            "label",
            {},
            element(
                "input",
                {
                    "name": group_name,
                    "type": mode,
                    "value": escape(value),
                },
            )
            + escape(value),
        )
        for value in option_values
    )
    fieldset_attrs = {
        "class": class_names(_ATOM_PREFIX, "field-choice", mode),
        **analytics_attrs(
            "atom-field-choice", _VERSION, event="component_interaction"
        ),
    }
    parts = [
        element(
            "fieldset",
            fieldset_attrs,
            element("legend", {}, escape(legend)) + options_html,
        )
    ]
    if error:
        parts.append(element("div", {"role": "alert"}, escape(error)))
    return "".join(parts)


LAYOUT_ATOMS_EMITTERS: Dict[str, EmitterFn] = {
    "layout.shell.page@1": _emit_layout_shell_page,
    "layout.section.container@1": _emit_layout_section_container,
    "layout.grid.standard@1": _emit_layout_grid_standard,
    "layout.stack.standard@1": _emit_layout_stack_standard,
    "layout.split.standard@1": _emit_layout_split_standard,
    "layout.card.shell@1": _emit_layout_card_shell,
    "atom.button.action@1": _emit_atom_button_action,
    "atom.link.standard@1": _emit_atom_link_standard,
    "atom.image.responsive@1": _emit_atom_image_responsive,
    "atom.icon.standard@1": _emit_atom_icon_standard,
    "atom.badge.status@1": _emit_atom_badge_status,
    "atom.alert.notice@1": _emit_atom_alert_notice,
    "atom.field.text@1": _emit_atom_field_text,
    "atom.field.select@1": _emit_atom_field_select,
    "atom.field.choice@1": _emit_atom_field_choice,
}
