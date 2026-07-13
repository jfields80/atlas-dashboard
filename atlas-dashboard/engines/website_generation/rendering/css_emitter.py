"""CSS serialization primitives for the Renderer (AES-WEB-001 §5.7/§8.3;
AES-WEB-002 §20.2).

Pure functions only, mirroring ``html_emitter.py``'s discipline: no
per-component visual authoring lives here beyond what the authorities
themselves specify (token-driven custom properties, deterministic
selectors, manifest-scoped tree-shaking, and the collapse-behavior media
queries the ResponsiveContract/ResponsiveSelection grammar already names).
No pixel value, spacing rhythm, or layout formula is invented here that
does not already exist as a resolved BrandPackage token or an authority-named
responsive keyword (§9.2, §11.3) -- detailed component-by-component visual
design is out of AES-WEB-002J.8's foundation scope and no authority document
specifies it.

Determinism (§5.7, §20.2, CG-RND-004): custom properties are emitted in
sorted token-id order; component rules are emitted in sorted class-name
order; media-query blocks are emitted in sorted collapse-behavior-keyword
order. Class names are never hashed-random -- always ``class_prefix`` plus
a dotted-to-dashed id fragment (mirroring ``html_emitter.class_names``).
"""

from __future__ import annotations

from typing import Iterable, Tuple

from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.rendering.html_emitter import TokenMap, class_names


def custom_property_name(token_id: str) -> str:
    """``"color.text.link"`` -> ``"--color-text-link"`` (dots to dashes,
    ``--`` custom-property prefix per §8.3's "tokens compile to custom
    properties")."""
    return "--" + token_id.replace(".", "-")


def token_var(token_id: str) -> str:
    """``"color.text.link"`` -> ``"var(--color-text-link)"`` -- the only way
    an emitted rule may reference a token value (§10, ADR-04: semantic
    tokens only, never a raw value)."""
    return "var(%s)" % custom_property_name(token_id)


def compile_custom_properties(tokens: TokenMap) -> str:
    """The ``:root`` custom-properties block compiled once per build from
    every resolved BrandPackage token (§8.3), sorted by token id for
    deterministic output regardless of the input dict's iteration order."""
    if not tokens:
        return ":root{}"
    declarations = ";".join(
        "%s:%s" % (custom_property_name(token_id), tokens[token_id])
        for token_id in sorted(tokens)
    )
    return ":root{%s}" % declarations


def component_class(definition: ComponentDefinition) -> str:
    """The deterministic, unique CSS class for every instance of this
    component: ``class_prefix`` plus the id's non-family segments
    (dots -> dashes), mirroring ``html_emitter.class_names`` so the same
    class appears in both the emitted markup and the emitted CSS selector.
    E.g. ``atom.button.action`` (class_prefix ``ac-atom``) ->
    ``ac-atom--button-action``."""
    prefix = definition.rendering_contract.class_prefix
    family_segment = definition.component_id.split(".", 1)[0]
    remainder = definition.component_id[len(family_segment) + 1:]
    modifier = remainder.replace(".", "-")
    return class_names(prefix, modifier).split(" ", 1)[-1]


def compile_component_rules(
    definitions: Iterable[ComponentDefinition], tokens: TokenMap
) -> str:
    """One deterministic token-driven rule per present component (§20.2's
    "emitting only for components present in the build's manifests"),
    sorted by the resulting class name. A component with no declared
    ``design_token_dependencies`` contributes no rule (nothing to
    tree-shake in, and nothing to invent)."""
    rules = []
    for definition in sorted(
        definitions,
        key=lambda d: component_class(d),
    ):
        deps = definition.design_token_dependencies
        if not deps:
            continue
        declarations = ";".join(
            "%s:%s" % (custom_property_name(token_id), token_var(token_id))
            for token_id in deps
            if token_id in tokens
        )
        if not declarations:
            continue
        rules.append(".%s{%s}" % (component_class(definition), declarations))
    return "".join(rules)


# The single breakpoint token every collapse-behavior media query keys off
# (§11.1's "single breakpoint authority"). "breakpoint.md" is the only
# breakpoint token any J.8 component's ResponsiveContract actually
# references (verified against the three J.8 catalog modules).
_RESPONSIVE_BREAKPOINT_TOKEN = "breakpoint.md"


def compile_responsive_rules(
    definitions: Iterable[ComponentDefinition], tokens: TokenMap
) -> str:
    """One deterministic ``@media (max-width: ...)`` block per distinct
    non-empty/non-"none" ``collapse_behavior`` actually declared among the
    present components (§11.2/§20.2), sorted by the collapse-behavior
    keyword. Every affected component's class is stacked-to-block inside
    that behavior's query -- the only responsive transformation any J.8
    component's contract names (``grid-to-stack``, ``stack-below-md``,
    ``drawer-below-md``); no other breakpoint or transformation is
    invented."""
    breakpoint_value = tokens.get(_RESPONSIVE_BREAKPOINT_TOKEN)
    if not breakpoint_value:
        return ""
    by_behavior = {}
    for definition in definitions:
        behavior = definition.responsive_contract.collapse_behavior
        if not behavior or behavior == "none":
            continue
        by_behavior.setdefault(behavior, []).append(definition)
    if not by_behavior:
        return ""
    blocks = []
    for behavior in sorted(by_behavior):
        selectors = ",".join(
            ".%s" % component_class(d)
            for d in sorted(by_behavior[behavior], key=component_class)
        )
        blocks.append(
            "@media (max-width: %s){%s{display:block}}"
            % (breakpoint_value, selectors)
        )
    return "".join(blocks)


def compile_shared_css(
    definitions: Iterable[ComponentDefinition], tokens: TokenMap
) -> str:
    """The complete deterministic shared CSS payload for one build: custom
    properties, then tree-shaken component rules, then tree-shaken
    responsive rules -- always in this fixed order so output is stable
    regardless of any input collection's iteration order."""
    ordered_definitions: Tuple[ComponentDefinition, ...] = tuple(definitions)
    return "".join(
        (
            compile_custom_properties(tokens),
            compile_component_rules(ordered_definitions, tokens),
            compile_responsive_rules(ordered_definitions, tokens),
        )
    )
