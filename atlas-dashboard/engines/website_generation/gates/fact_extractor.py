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
repositories, services, or the pipeline. AES-WEB-002L.2 adds exactly one
narrow exception, mirroring ``gates/checks/commercial_checks.py``'s own
precedent of importing threshold *data* from ``constants/``:
``constants.commercial_strategy.PAGE_COMMERCIAL_DEFAULTS`` (stdlib-only
itself, zero engine/state coupling) is the single declarative authority
CG-CMP-010's real evaluation reads its commercial requirements from -- read
here, never copied into a second table (AES-WEB-002L.1 §15 same-declaration-
source invariant).

AES-WEB-002L.2 commercial-completeness facts (CG-CMP-010): a page's real
``<main>`` region, its rendered anchor hrefs, and its ``legal.footer.
directory`` disclosure content are the exact "rendered output" §21
preamble language calls for -- honestly derivable from a static scan
because Atlas's own emitters (``rendering/html_emitter.py``'s ``element``)
guarantee well-formed, deterministic markup for every component this
engine emits (never a general-purpose HTML5 region extractor; scoped to
this engine's own known-well-formed output only, matching CG-RND-002's own
"static subset" honesty framing). Component identity comes from the real
``data-atlas-c`` attribute every component instance already carries
(``rendering/html_emitter.py``'s ``analytics_attrs``), whose value is a
tested invariant of ``component_id.replace(".", "-")`` (every catalog wave
test asserts this) -- so a value's family (``"layout"``, ``"trust"``, ...)
is honestly recovered by splitting on the first hyphen, with no registry
lookup and no guessing.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Dict, FrozenSet, List, Optional, Tuple

from engines.website_generation.constants.commercial_strategy import (
    PAGE_COMMERCIAL_DEFAULTS,
)
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


# AES-WEB-002L.2: the component family every "empty structural layout
# container" fallback (e.g. layout.section.container) belongs to -- the
# same family name composition_checks.py's CG-CMP-004 already treats as
# structurally inert (_EXEMPT_RECURSIVE_FAMILIES = {"layout", "atom"}).
# Only "layout" is checked here: a recipe slot's declared fallback_
# component_id is always a layout.* atom in the current catalog (never
# atom.*), so this is the exact, narrow set CG-CMP-010 needs -- not a
# broader guess.
_SHELL_COMPONENT_FAMILY = "layout"


def _component_family(data_atlas_c: str) -> str:
    """The component family a real ``data-atlas-c`` value's owning
    instance belongs to -- ``component_id.replace(".", "-")``'s first
    hyphen segment, honestly reversible because family names never
    contain hyphens (``ComponentFamily`` enum values are single words) and
    ``impression_id == component_id.replace(".", "-")`` is a tested
    invariant across every registered component (every catalog wave test
    asserts it)."""
    return data_atlas_c.split("-", 1)[0]


class _CommercialFactParser(HTMLParser):
    """Flat (non-nesting-aware) collector for the facts CG-CMP-010's real
    evaluation needs -- every ``data-atlas-c`` value, every anchor
    ``href``, and the ``<p>`` count -- within whatever HTML fragment it is
    fed. Region scoping (main region / legal.footer.directory's own
    element) is done by the caller via simple substring boundaries before
    feeding a fragment here (see ``_main_region``/``_footer_directory_
    region``) rather than by tracking a live element stack in this class --
    Atlas's own well-formed, deterministic output makes boundary-substring
    extraction safe for this engine's own emitted markup (same honesty
    scope as ``_DocumentParser``)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.data_atlas_c_values: List[str] = []
        self.hrefs: List[str] = []
        self.p_count: int = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_map = {name: (value or "") for name, value in attrs}
        if "data-atlas-c" in attr_map:
            self.data_atlas_c_values.append(attr_map["data-atlas-c"])
        if tag == "a" and "href" in attr_map:
            self.hrefs.append(attr_map["href"])
        if tag == "p":
            self.p_count += 1


def _collect_commercial_facts(html_fragment: str) -> _CommercialFactParser:
    parser = _CommercialFactParser()
    parser.feed(html_fragment)
    parser.close()
    return parser


def _main_region(html_text: str) -> Optional[str]:
    """The substring inside ``<main>...</main>``, or ``None`` if no
    ``<main>`` tag is found at all. ``""`` is a real, distinct, meaningful
    result (a ``<main>`` tag exists but is genuinely empty) -- callers must
    not conflate "absent" with "present but empty" (an empty string is
    falsy in Python; check ``is None`` explicitly). ``layout.shell.page``
    guarantees exactly one ``<main>``/``</main>`` pair per page (the same
    invariant CG-RND-002's own conformance check relies on), so a simple,
    well-formed boundary search is safe and honest for this engine's own
    output -- never claimed as a general HTML5 ``<main>`` extractor."""
    start_tag = html_text.find("<main")
    if start_tag == -1:
        return None
    open_end = html_text.find(">", start_tag)
    close_start = html_text.find("</main>", open_end) if open_end != -1 else -1
    if open_end == -1 or close_start == -1:
        return None
    return html_text[open_end + 1 : close_start]


def _footer_directory_region(html_text: str) -> str:
    """The substring inside ``legal.footer.directory``'s own ``<div>``,
    identified by its real ``data-atlas-c="legal-footer-directory"``
    marker -- ``""`` if the component was not selected for this page.
    ``emitters_navigation._emit_legal_footer_directory`` never nests a
    ``<div>`` inside its own markup (legal_facts/disclosures are ``<p>``,
    nav links are a ``<ul>``), so the first ``</div>`` after the opening
    tag is always the matching close."""
    marker = 'data-atlas-c="legal-footer-directory"'
    marker_pos = html_text.find(marker)
    if marker_pos == -1:
        return ""
    open_start = html_text.rfind("<div", 0, marker_pos)
    open_end = html_text.find(">", marker_pos) if open_start != -1 else -1
    close_start = html_text.find("</div>", open_end) if open_end != -1 else -1
    if open_start == -1 or open_end == -1 or close_start == -1:
        return ""
    return html_text[open_end + 1 : close_start]


def _commercial_requirement_facts(
    html_text: str, page_role: str, commercial_strategy: str,
) -> Tuple[bool, Tuple[str, ...]]:
    """Honest, structural verification of ``PAGE_COMMERCIAL_DEFAULTS``'
    declared requirements against this page's real rendered output -- the
    exact same declarative authority the Component Engine already
    consumes to compose the page (AES-WEB-002L.1), read here, never
    copied into a second table (§15 same-declaration-source invariant). A
    ``(commercial_strategy, page_role)`` with no declared defaults has
    nothing to verify, so it passes trivially -- matching
    ``SyntheticPage.required_role_components_present``'s own honest
    ``True`` default. Every failure is named specifically (which
    requirement, never a generic "something is wrong"), per the §21
    preamble diagnostic requirement."""
    defaults = PAGE_COMMERCIAL_DEFAULTS.get((commercial_strategy, page_role))
    if defaults is None:
        return True, ()

    missing: List[str] = []
    whole_page = _collect_commercial_facts(html_text)

    # 1. Primary CTA (AES-WEB-002L.2 §5): an exact href match against the
    # declared target -- a structured fact, not fuzzy text search. No
    # href declared (e.g. LEAD_GENERATION/home, which names a label but no
    # safe render target -- see PAGE_COMMERCIAL_DEFAULTS's own docstring)
    # means no CTA requirement to verify, never a fabricated expectation.
    href = defaults.get("primary_cta_href")
    label = defaults.get("primary_cta_label")
    if href and label and href not in whole_page.hrefs:
        missing.append("primary CTA (href=%r) not found in rendered output" % href)

    # 2. Required trust surfaces (AES-WEB-002L.2 §6): one structural rule
    # per declared surface name, dispatched by name -- an unrecognized
    # surface name is itself a defect worth surfacing, never silently
    # treated as satisfied.
    for surface in defaults.get("required_trust_surfaces", ()):
        if surface == "disclosure":
            footer_facts = _collect_commercial_facts(_footer_directory_region(html_text))
            # legal_facts is always exactly one required <p>
            # (binding_rules.py: _FULL/EXACTLY_ONE); a real disclosure
            # block contributes at least one more <p> -- so a bare
            # single-paragraph footer (or no footer at all) honestly
            # means no disclosure content is present.
            if footer_facts.p_count < 2:
                missing.append(
                    "required trust surface 'disclosure' not found in rendered output"
                )
        elif surface == "trust_adjacent_to_form":
            families = {_component_family(v) for v in whole_page.data_atlas_c_values}
            if "trust" not in families:
                missing.append(
                    "required trust surface 'trust_adjacent_to_form' not found in "
                    "rendered output"
                )
        else:
            missing.append(
                "required trust surface %r has no known verification rule" % surface
            )

    # 3. Commercially non-empty main (AES-WEB-002L.2 §8): main must carry
    # at least one non-shell (non-"layout"-family) component when this
    # page role/strategy declares any commercial requirement at all.
    main_html = _main_region(html_text)
    if main_html is None:
        missing.append("no <main> region found in rendered output")
    else:
        main_families = {
            _component_family(v) for v in _collect_commercial_facts(main_html).data_atlas_c_values
        }
        if not main_families:
            missing.append("main region is empty")
        elif main_families <= {_SHELL_COMPONENT_FAMILY}:
            missing.append("main region has no non-shell commercial content")

    return (not missing), tuple(missing)


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


def extract_page_composition_facts(
    route: str,
    html_text: str,
    *,
    page_role: str = "",
    commercial_strategy: str = "",
) -> SyntheticPage:
    """Parse one assembled HTML document into the CG-CMP structural
    read-fields (heading_sequence, landmark_roles, unlabeled_nav_count,
    nested_interactive_controls). Every other ``SyntheticPage`` field is left
    at its default and MUST NOT be read by any gate this engine runs on real
    output -- except (AES-WEB-002L.2) ``required_role_components_present``/
    ``commercial_strategy``/``missing_commercial_requirements``, populated
    from real ``PAGE_COMMERCIAL_DEFAULTS``-declared facts (CG-CMP-010) only
    when the caller supplies both ``page_role`` and ``commercial_strategy``
    (both keyword-only, both empty by default): omitting either preserves
    ``required_role_components_present``'s honest ``True`` default -- this
    gate was never fed a real value before this delivery, so there is no
    prior real-evaluation behavior to preserve beyond that honest default."""
    parser = _DocumentParser()
    parser.feed(html_text)
    parser.close()
    if page_role and commercial_strategy:
        present, missing = _commercial_requirement_facts(
            html_text, page_role, commercial_strategy
        )
    else:
        present, missing = True, ()
    return SyntheticPage(
        route=route,
        page_role=page_role,
        heading_sequence=tuple(parser.heading_sequence),
        landmark_roles=tuple(parser.landmark_roles),
        unlabeled_nav_count=parser.unlabeled_nav_count,
        nested_interactive_controls=tuple(parser.nested_interactive),
        required_role_components_present=present,
        commercial_strategy=commercial_strategy,
        missing_commercial_requirements=missing,
    )
