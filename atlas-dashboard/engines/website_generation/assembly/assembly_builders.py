"""Pure assembly primitives for the Assembly Engine (AES-WEB-001 §5.9;
AES-WEB-002 §13, §19).

Escaping, URL safety, deterministic route → output-file mapping, HTML
``<head>`` injection, and sitemap/robots serialization. Every function here
is pure: no I/O, no clock, no randomness, no AI, no mutation of its inputs.
The Assembly Engine performs **no file I/O** (§5.9) -- these helpers produce
in-memory text; the (future) site_bundle_repository (§9.3) materializes it.

Import matrix (§3.2/§29.2): ``assembly/`` may import only ``contracts/``,
``constants/``, and itself. It never imports ``rendering/`` (the sibling
engine that produced the input) -- so escaping/URL-safety are re-derived
here from stdlib rather than reused across the engine boundary, exactly as
``rendering/html_emitter`` re-derived them from ``html.escape`` rather than
importing another engine.
"""

from __future__ import annotations

import html as _stdlib_html
from typing import FrozenSet, List, Optional, Tuple

# Scheme whitelist for any URL Assembly emits into markup (canonical link,
# stylesheet link) -- the same policy the Renderer enforces (CG-RND-009),
# re-derived here (no cross-engine import). A URL with no scheme (relative
# path or bare fragment) is safe by construction; protocol-relative "//host"
# is rejected.
_SAFE_URL_SCHEMES: FrozenSet[str] = frozenset({"http", "https", "mailto", "tel"})

# Reserved Windows device names (case-insensitive, any extension) -- rejected
# as path segments so a bundle can never be materialized to a path the
# filesystem repository cannot create on Windows (§9 "reserved filenames",
# "Windows path safety"). Assembly itself writes nothing, but the bundle is
# a contract the repository must be able to honor on every platform.
_RESERVED_SEGMENTS: FrozenSet[str] = frozenset(
    {"con", "prn", "aux", "nul"}
    | {"com%d" % n for n in range(1, 10)}
    | {"lpt%d" % n for n in range(1, 10)}
)

SHARED_STYLESHEET_FILENAME = "styles.css"
SITEMAP_FILENAME = "sitemap.xml"
ROBOTS_FILENAME = "robots.txt"
_INDEX_FILENAME = "index.html"


def escape_text(text: str) -> str:
    """HTML-escape text-node content (title, etc.): ``&``, ``<``, ``>``."""
    return _stdlib_html.escape(text, quote=False)


def escape_attr(value: str) -> str:
    """HTML-escape an attribute value: ``&``, ``<``, ``>``, ``"``, ``'``."""
    return _stdlib_html.escape(value, quote=True)


def escape_xml(text: str) -> str:
    """XML-escape text content (sitemap ``<loc>``): ``&``, ``<``, ``>``."""
    return _stdlib_html.escape(text, quote=False)


def is_safe_url(url: str) -> bool:
    """True iff ``url`` is safe to emit in an ``href`` (canonical/stylesheet):
    a site-relative path, a bare fragment, or a whitelisted scheme. Rejects
    ``javascript:``/``data:``/``vbscript:``, protocol-relative ``//host``,
    and any other scheme (§19)."""
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


def _segment_is_safe(segment: str) -> bool:
    if not segment or segment in (".", ".."):
        return False
    if segment.strip() != segment or segment.endswith("."):
        # Leading/trailing whitespace or a trailing dot are unsafe on
        # Windows and ambiguous everywhere.
        return False
    if segment.split(".", 1)[0].lower() in _RESERVED_SEGMENTS:
        return False
    for ch in segment:
        # Reject path separators, drive/scheme colons, wildcard/reserved
        # filesystem characters, and any control character.
        if ch in '\\/:*?"<>|' or ord(ch) < 0x20:
            return False
    return True


def route_to_output_path(route: str) -> Tuple[Optional[str], Optional[str]]:
    """Map a page route to a deterministic bundle-root-relative output path,
    or return a rejection reason.

    Returns ``(path, None)`` on success or ``(None, reason)`` on rejection.
    Rules (documented, not guessed -- §9's examples are illustrative):

    * a route MUST be an absolute site path (start with ``/``);
    * ``/`` -> ``index.html``; ``/about`` and ``/about/`` -> ``about/index.html``
      (trailing slash normalized); ``/a/b`` -> ``a/b/index.html``;
    * every segment must be filesystem-safe on every platform (no ``..``,
      no ``.`` , no separators/wildcards/control chars/reserved device names,
      no leading/trailing whitespace or trailing dot);
    * the emitted path is always forward-slash, relative, and cannot escape
      the bundle root.
    """
    if not route or not route.startswith("/"):
        return None, "route_not_absolute"
    if "\\" in route:
        return None, "route_contains_backslash"
    # Split, dropping the leading-empty (from leading "/") and any trailing
    # empty (from a trailing "/"); an interior empty segment ("//") is unsafe.
    raw = route.split("/")
    interior = raw[1:]
    if interior and interior[-1] == "":
        interior = interior[:-1]  # normalize a single trailing slash
    if not interior:
        return _INDEX_FILENAME, None  # root route "/"
    for segment in interior:
        if not _segment_is_safe(segment):
            return None, "unsafe_route_segment"
    return "/".join(interior) + "/" + _INDEX_FILENAME, None


def stylesheet_href_for(output_path: str) -> str:
    """The site-relative href from ``output_path`` up to the shared
    stylesheet at the bundle root -- ``styles.css`` for a root-level page,
    ``../styles.css`` one level deep, etc. A relative href works both when
    the bundle is hosted from a domain root and when a page is opened
    directly (file://), so it needs no base URL (which no artifact
    supplies)."""
    depth = output_path.count("/")
    return "../" * depth + SHARED_STYLESHEET_FILENAME


def build_head_additions(
    *,
    title: str,
    meta_description: str,
    canonical_url: str,
    stylesheet_href: str,
) -> str:
    """The deterministic ``<head>`` fragment Assembly injects per page,
    always in a fixed element order (title, description, canonical,
    stylesheet). Every text/attribute value is escaped; a value is omitted
    only when empty (title/description), never emitted blank. Attribute
    order within each element is alphabetical, matching the Renderer's own
    serialization discipline (CG-RND-004)."""
    parts: List[str] = []
    if title:
        parts.append("<title>%s</title>" % escape_text(title))
    if meta_description:
        parts.append(
            '<meta content="%s" name="description">' % escape_attr(meta_description)
        )
    parts.append(
        '<link href="%s" rel="canonical">' % escape_attr(canonical_url)
    )
    parts.append(
        '<link href="%s" rel="stylesheet">' % escape_attr(stylesheet_href)
    )
    return "".join(parts)


_HEAD_CLOSE = "</head>"


def inject_head(document_html: str, head_additions: str) -> Tuple[Optional[str], Optional[str]]:
    """Insert ``head_additions`` immediately before the single ``</head>`` of
    ``document_html``, preserving every other byte (§8: never rebuild body
    markup). Returns ``(final_html, None)`` or ``(None, reason)`` when the
    insertion point is missing or duplicated -- a deterministic structural
    anchor, never a broad regex rewrite."""
    open_count = document_html.count("<head>")
    close_count = document_html.count(_HEAD_CLOSE)
    if open_count != 1 or close_count != 1:
        return None, "head_insertion_point_not_unique"
    index = document_html.index(_HEAD_CLOSE)
    return document_html[:index] + head_additions + document_html[index:], None


def build_sitemap(canonical_urls: Tuple[str, ...]) -> str:
    """A deterministic sitemap.xml from the SEO artifact's canonical URLs, in
    the given (pre-sorted) order. XML-escaped ``<loc>`` entries, no
    ``<lastmod>`` (no clock/timestamp input exists), UTF-8. The URLs are the
    SEO Engine's self-canonical route paths (Decision D3) -- Assembly emits
    exactly those, inventing no hostname (§12: no guessed deployment host)."""
    locs = "".join(
        "<url><loc>%s</loc></url>" % escape_xml(url) for url in canonical_urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + locs
        + "</urlset>"
    )


def build_robots(directives: Tuple[str, ...]) -> str:
    """robots.txt from the SEO artifact's site-level directives, one per
    line, trailing newline. No ``Sitemap:`` line: that directive requires an
    absolute URL, and no base host exists in any artifact (§12: no guessed
    hostname)."""
    return "\n".join(directives) + "\n"
