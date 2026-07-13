"""HTML serialization primitives for the Renderer (AES-WEB-001 §5.7;
AES-WEB-002 §20.1).

Pure functions only: escaping, attribute/element serialization, analytics
data-attribute construction, and the shared per-emitter type aliases. No
markup knowledge for any specific component lives here -- that is exactly
what ``rendering/emitters_*.py`` hold (AES-WEB-001 §8.1: "the renderer
holds the (only) markup knowledge for each component ... as pure emission
functions"). This module owns none of it; it only gives every emitter the
same deterministic building blocks so two emitters never invent two
different escaping or attribute-ordering rules.

Escaping-boundary decision (AES-WEB-002J.8, documented -- not invented ad
hoc). AES-WEB-001 §5.7 describes the Renderer escaping "again" as
defense-in-depth, implying content arrives pre-escaped from the Content
Engine. Inspection of the actual Content Engine (``content/content_engine.py``
module docstring, Decision A1) shows this repository's Content Engine is a
*validation airlock*, not a copy transform: "every accepted
``ContentBlock.text`` is byte-identical to the ``ContentCandidate.body``
that produced it" -- no escaping happens anywhere upstream. ``ContentBlock
.text`` therefore arrives at the Renderer completely raw. Given that, this
module implements exactly ONE canonical HTML-escaping pass
(:func:`escape`), applied once at every text/attribute insertion point. This
is not "double escaping" (there is no upstream escaping to double) and it is
not "under escaping" (every interpolation site in every emitter routes
through this one function) -- it is the single, safe, deterministic boundary
CG-RND-003 requires, adapted to what the upstream artifact actually
contains rather than what §5.7's summary prose assumed. Because ``escape``
is idempotent-safe for the common case (it does not decode existing
entities first), text that already contains a literal ``&amp;`` becomes
``&amp;amp;`` -- correct, because that literal sequence in raw
``ContentCandidate.body`` was never intended as markup by anything upstream
(there is no upstream authoring path that emits pre-escaped entities); it is
ordinary text characters, escaped once, faithfully.
"""

from __future__ import annotations

import html as _stdlib_html
from typing import Callable, Dict, FrozenSet, Mapping, NamedTuple, Optional, Tuple, Union

from engines.website_generation.contracts.artifacts import (
    ComponentInstance,
    GridPlacement,
    ResponsiveSelection,
)
from engines.website_generation.contracts.enums import RegionKind

# A rendered HTML fragment: plain, already-serialized markup text. Not a
# frozen Pydantic contract model -- this is Renderer-internal plumbing
# (AES-WEB-001 §8.1's "pure emission functions"), never a persisted
# artifact; the persisted artifact is RenderedPageSet, assembled by
# renderer.py from many HtmlFragment values.
HtmlFragment = str

# Every content slot resolved for one component instance: slot_id -> an
# ordered tuple of raw (unescaped) ContentBlock.text values bound to that
# (route, slot_id) pair. A tuple, never a bare string, so EXACTLY_ONE slots
# (tuple of length 1) and ONE_TO_N slots (multiple ContentPackage blocks
# sharing one (route, slot_id)) share one uniform shape -- no join/split
# delimiter hack, no ambiguity about whether a slot is single- or
# multi-valued. Never partially escaped -- escaping is always applied at the
# point of interpolation, inside the emitter, via this module's helpers
# only.
ResolvedContent = Dict[str, Tuple[str, ...]]

# Every design token an emitter may reference, flattened from BrandPackage's
# five token-domain dicts (palette/type_scale/spacing_scale/radius_scale/
# extended_tokens) into one lookup keyed by the bare dotted token id (e.g.
# "color.text.link", "spacing.section.medium") -- the same id space
# ComponentDefinition.design_token_dependencies and GridPlacement
# .columns_token reference. Building this merge is renderer.py's job, not
# any individual emitter's.
TokenMap = Dict[str, str]


class LayoutContext(NamedTuple):
    """Per-instance placement context threaded into every emitter (§20.1's
    fourth parameter), read verbatim from the LayoutPlan -- an emitter never
    recomputes placement, only reflects it into markup (data attributes,
    responsive classes). ``component_index`` is the same original
    ``ComponentManifest`` page index ``ComponentPlacement.component_index``
    names (never renumbered) -- carried here so emitters needing a
    page-unique DOM id (form fields, aria-controls targets) never invent
    one (:func:`dom_id`, CG-RND-008)."""

    region_kind: RegionKind
    component_index: int
    grid: GridPlacement
    responsive: ResponsiveSelection


# The uniform pure-emission-function signature (§20.1): ``(instance,
# resolved_content, tokens, layout_ctx) -> HtmlFragment``. Every entry in
# every family's ``*_EMITTERS`` table, and the merged ``EMITTER_TABLE``
# ``renderer.py`` assembles from them, is one of these.
EmitterFn = Callable[
    [ComponentInstance, ResolvedContent, TokenMap, LayoutContext], HtmlFragment
]


_VOID_ELEMENTS: FrozenSet[str] = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)

# Scheme whitelist (CG-RND-009). A URL with no scheme at all (a relative
# path, a query string, or a bare fragment) is safe by construction -- it
# cannot smuggle an executable scheme. "//" (protocol-relative) is rejected:
# it resolves to an attacker-controlled host exactly like an absolute URL
# would, so it gets the same scheme-shaped scrutiny via the explicit "//"
# check below rather than falling through the no-colon fast path.
_SAFE_URL_SCHEMES: FrozenSet[str] = frozenset({"http", "https", "mailto", "tel"})


def escape(text: str) -> str:
    """The one canonical HTML-escaping function (see module docstring for
    the boundary decision). Safe for both text-node and attribute-value
    contexts: :func:`html.escape` with ``quote=True`` escapes ``&``, ``<``,
    ``>``, ``"``, and ``'`` -- a strict superset of what either context
    requires, so one function serves both without a context-detection bug
    class."""
    return _stdlib_html.escape(text, quote=True)


def is_safe_url(url: str) -> bool:
    """True iff ``url`` is safe to emit in an ``href``/``action``/``src``
    attribute (CG-RND-009): a same-origin-relative path, a bare fragment, or
    an explicitly whitelisted scheme. Rejects ``javascript:``, ``data:``,
    ``vbscript:``, protocol-relative ``//host/...``, and any other scheme."""
    stripped = url.strip()
    if not stripped:
        return False
    if stripped.startswith("//"):
        return False
    if stripped.startswith("#") or stripped.startswith("/"):
        return True
    if ":" not in stripped:
        return True
    scheme = stripped.split(":", 1)[0].strip().lower()
    return scheme in _SAFE_URL_SCHEMES


AttrValue = Union[str, bool, None]


def render_attrs(attrs: Mapping[str, AttrValue]) -> str:
    """Serialize an attribute mapping in deterministic alphabetical key
    order (§20.1/CG-RND-004). ``None``/``False`` values are omitted
    entirely; ``True`` renders as a bare boolean attribute; every string
    value is escaped via :func:`escape`."""
    parts = []
    for key in sorted(attrs):
        value = attrs[key]
        if value is None or value is False:
            continue
        if value is True:
            parts.append(key)
            continue
        parts.append('%s="%s"' % (key, escape(str(value))))
    return " ".join(parts)


def element(
    tag: str,
    attrs: Optional[Mapping[str, AttrValue]] = None,
    children: str = "",
) -> HtmlFragment:
    """Serialize one element deterministically: alphabetical attribute
    order, correct void-element handling (no closing tag, children
    ignored), UTF-8 text throughout. ``children`` must already be
    fully-serialized, escaped markup -- this function does not escape it
    (it is a fragment composed of other :func:`element`/:func:`escape`
    calls, not raw text)."""
    attr_str = render_attrs(attrs or {})
    open_tag = "<%s%s>" % (tag, (" " + attr_str) if attr_str else "")
    if tag in _VOID_ELEMENTS:
        return open_tag
    return "%s%s</%s>" % (open_tag, children, tag)


def class_names(class_prefix: str, *modifiers: str) -> str:
    """Deterministic, token-derived-in-spirit (never hashed-random) class
    list: the bare ``class_prefix`` plus one BEM-style modifier class per
    non-empty ``modifiers`` entry, in call order (callers pass modifiers in
    a fixed, documented order -- this function does not sort them, because
    modifier order is meaningful precedence in a few emitters, e.g.
    family-then-state)."""
    names = [class_prefix]
    for modifier in modifiers:
        if modifier:
            names.append("%s--%s" % (class_prefix, modifier))
    return " ".join(names)


def analytics_attrs(
    impression_id: str,
    component_version: str,
    *,
    variant: str = "",
    event: str = "",
    label: str = "",
) -> Dict[str, str]:
    """The §18.1 ``data-atlas-*`` attributes this component instance must
    carry: ``data-atlas-c``/``data-atlas-v`` always; ``data-atlas-var``/
    ``data-atlas-e``/``data-atlas-l`` only when the caller supplies a
    non-empty value (an inert component with no variant/event/label omits
    those keys rather than emitting an empty attribute)."""
    attrs: Dict[str, str] = {
        "data-atlas-c": impression_id,
        "data-atlas-v": component_version,
    }
    if variant:
        attrs["data-atlas-var"] = variant
    if event:
        attrs["data-atlas-e"] = event
    if label:
        attrs["data-atlas-l"] = label
    return attrs


def first_value(resolved_content: ResolvedContent, slot_id: str, default: str = "") -> str:
    """The first (or only) resolved value for ``slot_id`` -- the common case
    for an ``EXACTLY_ONE``/``ZERO_OR_ONE`` slot, where the tuple has at most
    one entry."""
    values = resolved_content.get(slot_id, ())
    return values[0] if values else default


def all_values(resolved_content: ResolvedContent, slot_id: str) -> Tuple[str, ...]:
    """Every resolved value for ``slot_id`` in bound order -- the
    ``ONE_TO_N`` case (e.g. a tile grid, a breadcrumb trail)."""
    return resolved_content.get(slot_id, ())


def dom_id(impression_id: str, component_index: int) -> str:
    """A deterministic, page-unique element id for components that need one
    (form field label association, aria-controls targets): the component's
    analytics slug plus its own manifest position -- never a random or
    clock-derived value, and never colliding with another instance's id on
    the same page because ``component_index`` is unique per page (§8.2 of
    the AES-WEB-002J.8 preflight; CG-RND-008)."""
    return "ac-%s-%d" % (impression_id, component_index)
