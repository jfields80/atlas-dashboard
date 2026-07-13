"""Deterministic real-output fact extraction for the Quality Gate Engine
(AES-WEB-001 §5.10; AES-WEB-002 §21 preamble "rendered output").

Parses one assembled HTML document (a ``SiteBundle`` file) with the Python
standard library's :class:`html.parser.HTMLParser` into the exact subset of
:class:`~engines.website_generation.gates.checks.SyntheticRenderedPage` /
:class:`~engines.website_generation.gates.checks.SyntheticPage` fields the
gates this engine actually evaluates read -- and nothing else. It is a flat,
deterministic static analysis: no browser, no DOM engine, no CSS cascade, no
layout, no network, no rendering. The same input always yields the same
facts (no clock/UUID/randomness).

Honesty boundary (the AES-005A quality-gate lesson, §5.10): this module
populates only facts a static HTML scan can honestly derive. Facts a static
scan cannot derive -- colour contrast (needs the resolved CSS cascade + WCAG
maths), touch-target size / reflow / focus-ring visibility (need layout),
double-render determinism (needs two renders), content-escaping probes
(need injected markers) -- are deliberately NOT produced here, and the gates
depending on them are reported ``deferred`` by the engine rather than fed a
fabricated default. Callers therefore run only the gates whose every
read-field this module fills.

Import boundary (§3.2/§29.2): imports only stdlib + this package's fact
vocabulary (``gates/checks``). Never imports ``rendering/``/``assembly/``
(the engines that produced the input), the component registry,
repositories, services, or the pipeline.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Dict, FrozenSet, List, Optional, Tuple

from engines.website_generation.gates.checks import (
    SyntheticPage,
    SyntheticRenderedPage,
)

# Elements that are themselves focusable interactive controls -- a control
# nested inside another control is the CG-CMP-008 defect (§9, §12). Grouping
# containers (label, details, summary, fieldset) are intentionally excluded:
# an <input> inside a <label>, or a <summary> inside <details>, is correct
# markup, not a nested control.
_INTERACTIVE_TAGS: FrozenSet[str] = frozenset(
    {"a", "button", "input", "select", "textarea"}
)

# Tag -> the landmark-role name CG-CMP-006 counts. role="" attributes are
# also mapped (banner/main/contentinfo/navigation) so an author-set ARIA
# landmark is not missed.
_LANDMARK_TAGS: Dict[str, str] = {
    "header": "header",
    "main": "main",
    "footer": "footer",
    "nav": "nav",
}
_LANDMARK_ROLES: Dict[str, str] = {
    "banner": "header",
    "main": "main",
    "contentinfo": "footer",
    "navigation": "nav",
}

# Attributes whose values are URLs and must be scheme-safe (CG-RND-009).
_URL_ATTRS: FrozenSet[str] = frozenset({"href", "src", "action"})

# Internal build/selection markers that must never leak into emitted markup
# (CG-RND-008; AES-WEB-002 §18.3, §19). Scanned as substrings of the raw
# document.
_INTERNAL_METADATA_MARKERS: Tuple[str, ...] = (
    "selection_trace",
    "registry_version",
    "build_id",
    "__shell_body__",
)

_SAFE_URL_SCHEMES: FrozenSet[str] = frozenset({"http", "https", "mailto", "tel"})


def _is_safe_url(url: str) -> bool:
    """Re-derived from the Renderer/Assembly policy (no cross-engine import):
    relative paths and bare fragments are safe; protocol-relative ``//host``
    and any non-whitelisted scheme are not (CG-RND-009)."""
    stripped = url.strip()
    if not stripped:
        return True  # an empty href is a separate concern, not an unsafe scheme
    if stripped.startswith("//"):
        return False
    if stripped.startswith("#") or stripped.startswith("/"):
        return True
    if ":" not in stripped:
        return True
    scheme = stripped.split(":", 1)[0].strip().lower()
    return scheme in _SAFE_URL_SCHEMES


class _DocumentParser(HTMLParser):
    """Collects the flat facts the evaluated gates read, in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.dom_ids: List[str] = []
        self.heading_sequence: List[int] = []
        self.landmark_roles: List[str] = []
        self.unlabeled_nav_count: int = 0
        self.inline_script_count: int = 0
        self.external_script_count: int = 0
        self.inline_style_count: int = 0
        self.unsafe_urls: List[str] = []
        self.nested_interactive: List[str] = []
        self.tag_counts: Dict[str, int] = {}
        self._interactive_depth: int = 0
        self._malformed: bool = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_map = {name: (value or "") for name, value in attrs}
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1

        if "id" in attr_map:
            self.dom_ids.append(attr_map["id"])

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading_sequence.append(int(tag[1]))

        landmark = _LANDMARK_TAGS.get(tag)
        role = attr_map.get("role", "").strip().lower()
        if landmark is None and role in _LANDMARK_ROLES:
            landmark = _LANDMARK_ROLES[role]
        if landmark is not None:
            self.landmark_roles.append(landmark)
            if landmark == "nav" and not (
                attr_map.get("aria-label") or attr_map.get("aria-labelledby")
            ):
                self.unlabeled_nav_count += 1

        if tag == "script":
            # CG-RND-005 is about *inline* scripts (no src); an external
            # <script src> is not inline and is attributed to the no-JS
            # baseline (CG-RND-006) instead, via the total-script count below.
            if "src" in attr_map:
                self.external_script_count += 1
            else:
                self.inline_script_count += 1
        if tag == "style":
            self.inline_style_count += 1
        if "style" in attr_map:
            self.inline_style_count += 1

        for url_attr in _URL_ATTRS:
            if url_attr in attr_map:
                value = attr_map[url_attr]
                if value and not _is_safe_url(value):
                    self.unsafe_urls.append(value)

        if tag in _INTERACTIVE_TAGS:
            if self._interactive_depth > 0:
                self.nested_interactive.append(tag)
            # void interactive elements (input) never open a nesting scope
            if tag != "input":
                self._interactive_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _INTERACTIVE_TAGS and tag != "input" and self._interactive_depth > 0:
            self._interactive_depth -= 1

    def error(self, message: str) -> None:  # pragma: no cover - HTMLParser API
        self._malformed = True


def _conformance_errors(parser: _DocumentParser, html_text: str) -> Tuple[str, ...]:
    """Deterministic basic structural conformance (CG-RND-002, static
    subset). Not a full HTML5 validator -- checks the document-shell
    invariants the Renderer's ``layout.shell.page`` guarantees: a doctype and
    exactly one ``<html>``/``<head>``/``<body>``. Labeled honestly as a
    static structural check, never claimed as full conformance."""
    errors: List[str] = []
    if "<!doctype" not in html_text.lower():
        errors.append("missing doctype")
    for tag in ("html", "head", "body"):
        count = parser.tag_counts.get(tag, 0)
        if count != 1:
            errors.append("expected exactly one <%s>, found %d" % (tag, count))
    if parser._malformed:
        errors.append("unparseable markup")
    return tuple(errors)


def extract_rendered_page_facts(route: str, html_text: str) -> SyntheticRenderedPage:
    """Parse one assembled HTML document into the CG-RND-family read-fields
    (html_conformant/conformance_errors, inline_script_count,
    unapproved_inline_style_count, no_js_baseline_present, dom_ids,
    internal_metadata_markers, unsafe_urls). Every other
    ``SyntheticRenderedPage`` field is left at its default and MUST NOT be
    read by any gate this engine runs on real output."""
    parser = _DocumentParser()
    parser.feed(html_text)
    parser.close()
    errors = _conformance_errors(parser, html_text)
    markers = tuple(m for m in _INTERNAL_METADATA_MARKERS if m in html_text)
    return SyntheticRenderedPage(
        route=route,
        dom_ids=tuple(parser.dom_ids),
        html_conformant=not errors,
        conformance_errors=errors,
        inline_script_count=parser.inline_script_count,
        unapproved_inline_style_count=parser.inline_style_count,
        # The no-JS baseline holds only when the page ships zero scripts of
        # any kind -- inline or external (CG-RND-006). Atlas emits none.
        no_js_baseline_present=(
            parser.inline_script_count + parser.external_script_count
        )
        == 0,
        internal_metadata_markers=markers,
        unsafe_urls=tuple(parser.unsafe_urls),
    )


def extract_page_composition_facts(route: str, html_text: str) -> SyntheticPage:
    """Parse one assembled HTML document into the CG-CMP structural
    read-fields (heading_sequence, landmark_roles, unlabeled_nav_count,
    nested_interactive_controls). Every other ``SyntheticPage`` field is left
    at its default and MUST NOT be read by any gate this engine runs on real
    output."""
    parser = _DocumentParser()
    parser.feed(html_text)
    parser.close()
    return SyntheticPage(
        route=route,
        heading_sequence=tuple(parser.heading_sequence),
        landmark_roles=tuple(parser.landmark_roles),
        unlabeled_nav_count=parser.unlabeled_nav_count,
        nested_interactive_controls=tuple(parser.nested_interactive),
    )
