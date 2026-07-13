"""Pure validation and composition internals for the SEO Engine (AES-WEB-001
§5.8; AES-WEB-002J.5 Decisions D1-D5).

Per-page content-block lookup, title composition, meta-description
truncation, and the structural/content/length/uniqueness validators the
engine batches into a single :class:`SEOCompilationError`. Every function
here is pure: no I/O, no clock, no randomness, no AI, and no mutation of its
inputs (``PagePlan``/``ContentBlock`` are frozen). Nothing here is exported
as part of the package's public API -- ``seo_engine.py`` is the sole caller.

Character counting policy (Decision D1/D2, the J.4 counting policy): every
length compared against a named limit is ``len(text)`` on the Python
``str`` -- a count of Unicode code points as already decoded, never raw
bytes, never a grapheme-cluster count. The same input string therefore
always yields the same length on any platform.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from engines.website_generation.constants.seo import (
    CANONICAL_URL_MAX_LENGTH,
    META_DESCRIPTION_MAX_LENGTH,
    META_DESCRIPTION_MIN_LENGTH,
    META_SOURCE_SLOT_BY_ROLE,
    TITLE_MAX_LENGTH,
    TITLE_SEPARATOR,
    TITLE_SOURCE_SLOT_BY_ROLE,
)
from engines.website_generation.contracts.artifacts import ContentBlock, PagePlan

# ---------------------------------------------------------------------------
# Per-page content-block lookup (D1/D2: content blocks are looked up by
# (page_route, slot_id), never by positional order -- determinism
# requirement, AES-WEB-001 §1.1).
# ---------------------------------------------------------------------------


def index_content_blocks(
    blocks: Sequence[ContentBlock],
) -> Dict[Tuple[str, str], ContentBlock]:
    """``(page_route, slot_id) -> ContentBlock``.

    ``ContentPackage`` is trusted, already-validated upstream input; a
    duplicate ``(page_route, slot_id)`` pair silently keeps its last
    occurrence rather than being repaired or re-validated here, mirroring
    the Content Engine's own last-occurrence-wins precedent for trusted
    input (``content_validators.page_slot_map``). No diagnostic bucket is
    defined for this case because a correctly produced ``ContentPackage``
    cannot contain one.
    """
    return {(block.page_route, block.slot_id): block for block in blocks}


# ---------------------------------------------------------------------------
# Structural validators (§4.4 semantic ring; D2 structural uniqueness)
# ---------------------------------------------------------------------------


def duplicate_routes(routes: Sequence[str]) -> Tuple[str, ...]:
    """Every route occurring more than once in ``routes``, sorted.

    Structural violation (D2.a: "exactly one SEOEntry per SiteArchitecture
    page") -- a ``SiteArchitecture`` with a duplicate route cannot satisfy
    that invariant and is always a batched validation error, never silently
    deduplicated.
    """
    seen: set = set()
    dupes: set = set()
    for route in routes:
        if route in seen:
            dupes.add(route)
        seen.add(route)
    return tuple(sorted(dupes))


def unknown_content_routes(
    blocks: Sequence[ContentBlock], known_routes: Sequence[str]
) -> Tuple[str, ...]:
    """Every distinct ``ContentBlock.page_route`` absent from
    ``known_routes``, sorted (§4.4: cross-artifact route consistency,
    mirroring content_engine's own ``unknown_route_candidates`` check).
    """
    known = set(known_routes)
    return tuple(sorted({block.page_route for block in blocks if block.page_route not in known}))


# ---------------------------------------------------------------------------
# Title composition and truncation (Decision D2)
# ---------------------------------------------------------------------------


def compose_title(hero_h1: str, business_name: str) -> str:
    """``f"{hero_h1} | {business_name}"`` with the deterministic fallback
    ladder against ``TITLE_MAX_LENGTH`` (Decision D2):

    1. The full composed title, if its length is <= the limit.
    2. ``hero_h1`` alone, if *its* length is <= the limit.
    3. ``hero_h1`` hard-cut to exactly the limit's code points.

    Truncation may only remove characters -- no ellipsis, punctuation, or
    replacement character is ever appended.
    """
    full_title = hero_h1 + TITLE_SEPARATOR + business_name
    if len(full_title) <= TITLE_MAX_LENGTH:
        return full_title
    if len(hero_h1) <= TITLE_MAX_LENGTH:
        return hero_h1
    return hero_h1[:TITLE_MAX_LENGTH]


# ---------------------------------------------------------------------------
# Meta-description truncation (Decision D1)
# ---------------------------------------------------------------------------


def _last_whitespace_index(text: str) -> Optional[int]:
    """Index of the last whitespace code point in ``text``, or ``None``."""
    for index in range(len(text) - 1, -1, -1):
        if text[index].isspace():
            return index
    return None


def truncate_meta_description(intro: str) -> str:
    """Deterministic word-boundary truncation to ``META_DESCRIPTION_MAX_LENGTH``
    (Decision D1):

    1. ``intro`` verbatim, if its length is <= the limit.
    2. Otherwise, the longest prefix of the first ``META_DESCRIPTION_MAX_LENGTH``
       code points that ends at a whitespace boundary, with trailing
       whitespace then stripped via ``str.rstrip()``.
    3. Edge fallback: if no whitespace occurs within the first
       ``META_DESCRIPTION_MAX_LENGTH`` code points, hard-cut to exactly that
       many code points.

    Truncation may only remove characters -- no ellipsis, punctuation, or
    replacement character is ever appended. Zero-width/invisible Unicode
    format characters (category "Cf") are not ``str.isspace()`` and are
    therefore never treated as a whitespace boundary, consistent with
    ``str.rstrip()``'s own definition of whitespace.
    """
    if len(intro) <= META_DESCRIPTION_MAX_LENGTH:
        return intro
    window = intro[:META_DESCRIPTION_MAX_LENGTH]
    boundary = _last_whitespace_index(window)
    if boundary is None:
        return window
    return window[: boundary + 1].rstrip()


# ---------------------------------------------------------------------------
# Title uniqueness (Decision D2.b)
# ---------------------------------------------------------------------------


def title_collisions(titles_by_route: Dict[str, str]) -> Tuple[Dict[str, Any], ...]:
    """Every title text shared by more than one route, sorted by title text.

    Each entry is ``{"title": <text>, "routes": (<route>, ...)}`` with
    ``routes`` sorted -- a pure function of ``titles_by_route`` only, never
    of insertion order (determinism requirement, AES-WEB-001 §1.1).
    """
    routes_by_title: Dict[str, List[str]] = {}
    for route, title in titles_by_route.items():
        routes_by_title.setdefault(title, []).append(route)
    violations = [
        {"title": title, "routes": tuple(sorted(routes))}
        for title, routes in routes_by_title.items()
        if len(routes) > 1
    ]
    return tuple(sorted(violations, key=lambda entry: entry["title"]))


# ---------------------------------------------------------------------------
# Length validators over already-composed values (D1/D2/D3)
# ---------------------------------------------------------------------------


def meta_length_violation(route: str, intro: str) -> Optional[Dict[str, Any]]:
    """``meta_length_violations`` entry if the SOURCE ``intro`` is shorter
    than ``META_DESCRIPTION_MIN_LENGTH``, else ``None`` (Decision D1: the
    floor is measured on the source intro, never on the truncated output --
    truncation only ever shortens, so it requires no post-truncation
    maximum check).
    """
    length = len(intro)
    if length < META_DESCRIPTION_MIN_LENGTH:
        return {"route": route, "length": length, "limit": META_DESCRIPTION_MIN_LENGTH}
    return None


def title_length_violation(route: str, title: str) -> Optional[Dict[str, Any]]:
    """``title_length_violations`` entry if the final (post-fallback-ladder)
    ``title`` exceeds ``TITLE_MAX_LENGTH``, else ``None``. Unreachable under
    the fallback ladder in :func:`compose_title`, but validated anyway
    (defense in depth, per the sprint's explicit requirement).
    """
    length = len(title)
    if length > TITLE_MAX_LENGTH:
        return {"route": route, "length": length, "limit": TITLE_MAX_LENGTH}
    return None


def canonical_length_violation(route: str) -> Optional[Dict[str, Any]]:
    """``canonical_length_violations`` entry if ``route`` exceeds
    ``CANONICAL_URL_MAX_LENGTH``, else ``None`` (Decision D3: the canonical
    URL equals the route byte-verbatim, so the check is on the route
    itself)."""
    length = len(route)
    if length > CANONICAL_URL_MAX_LENGTH:
        return {"route": route, "length": length, "limit": CANONICAL_URL_MAX_LENGTH}
    return None


# ---------------------------------------------------------------------------
# Role support (D1/D2 rule-table lookup; unsupported_page_types)
# ---------------------------------------------------------------------------


def role_source_slots(page_type: str) -> Optional[Tuple[str, str]]:
    """``(title_slot, meta_slot)`` for ``page_type``, or ``None`` if
    ``page_type`` has no rule-table entry (an ``unsupported_page_types``
    validation error -- unknown page types are never silently defaulted).

    Table-driven from ``constants/seo.py``'s ``TITLE_SOURCE_SLOT_BY_ROLE`` /
    ``META_SOURCE_SLOT_BY_ROLE`` -- a new role's source slots are a new
    table entry, never a new branch here (mirrors
    ``content_validators.slot_length_violation``'s table-driven dispatch).
    """
    if page_type not in TITLE_SOURCE_SLOT_BY_ROLE or page_type not in META_SOURCE_SLOT_BY_ROLE:
        return None
    return TITLE_SOURCE_SLOT_BY_ROLE[page_type], META_SOURCE_SLOT_BY_ROLE[page_type]


def missing_content_slots(
    page: PagePlan,
    title_slot: str,
    meta_slot: str,
    block_index: Dict[Tuple[str, str], ContentBlock],
) -> Tuple[str, ...]:
    """Every one of ``(title_slot, meta_slot)`` absent from ``block_index``
    for ``page.route``, sorted (``missing_content``: "a page lacks
    hero_h1 or a page lacks intro")."""
    missing: List[str] = []
    if (page.route, title_slot) not in block_index:
        missing.append(title_slot)
    if (page.route, meta_slot) not in block_index:
        missing.append(meta_slot)
    return tuple(sorted(missing))
