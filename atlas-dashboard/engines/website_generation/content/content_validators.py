"""Pure validation internals for the Content Engine (AES-WEB-001 §5.4).

Structural classification of candidates against a SiteArchitecture's routes
and declared slots, and policy checks (banned phrases, placeholder markers,
slot length bounds) over a single candidate body. Every function here is
pure: no I/O, no clock, no randomness, no AI, and no mutation of its inputs
(``ContentCandidate``/``PagePlan`` are frozen). Nothing here authors,
rewrites, or varies candidate text -- these functions only classify and
measure it (Decision A1).
"""

from __future__ import annotations

import unicodedata
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from engines.website_generation.constants.brand import BANNED_VOICE_PHRASES
from engines.website_generation.constants.content import (
    PLACEHOLDER_SUBSTRING_MARKERS,
    PLACEHOLDER_WORD_MARKERS,
    SLOT_MAX_LENGTHS,
    SLOT_MIN_LENGTHS,
    SLOTS_REQUIRING_VISIBLE_CONTENT,
    SUPPORTED_SLOT_IDS,
)
from engines.website_generation.contracts.artifacts import ContentCandidate, PagePlan

# ---------------------------------------------------------------------------
# Structural classification (route/slot membership; §8)
# ---------------------------------------------------------------------------


class CandidateClassification(NamedTuple):
    """Result of sorting raw candidates into structural buckets.

    ``bindings`` maps every ``(page_route, slot_id)`` pair that at least one
    candidate structurally targets (known route, supported slot, slot
    declared on that page) to every candidate that targeted it -- more than
    one entry for a key means an ambiguous duplicate binding (§8). The three
    remaining fields hold structurally invalid candidates, each sorted
    deterministically by ``(page_route, slot_id)`` so classification never
    depends on the input candidate order.
    """

    bindings: Dict[Tuple[str, str], Tuple[ContentCandidate, ...]]
    unknown_route: Tuple[ContentCandidate, ...]
    unsupported_slot: Tuple[ContentCandidate, ...]
    undeclared_slot: Tuple[ContentCandidate, ...]


def page_slot_map(pages: Sequence[PagePlan]) -> Dict[str, Tuple[str, ...]]:
    """Route -> declared ``content_slots``, preserving each page's given
    slot order verbatim.

    ``SiteArchitecture`` is trusted, already-validated upstream input (§5.3
    enforces its own structural invariants at construction). A duplicate
    route silently keeps its last occurrence rather than being repaired or
    re-validated here -- that is IA's contract to enforce, not the Content
    Engine's (§13: "follow the existing architectural contract
    expectations. Do not silently repair it").
    """
    return {page.route: page.content_slots for page in pages}


def classify_candidates(
    candidates: Sequence[ContentCandidate],
    slot_map: Dict[str, Tuple[str, ...]],
) -> CandidateClassification:
    """Sort candidates by structural validity against ``slot_map``.

    Pure and order-independent: every bucket is sorted by ``(page_route,
    slot_id)`` so the result does not depend on ``candidates``' input order
    (determinism requirement, AES-WEB-001 §1.1).
    """
    unknown_route: List[ContentCandidate] = []
    unsupported_slot: List[ContentCandidate] = []
    undeclared_slot: List[ContentCandidate] = []
    grouped: Dict[Tuple[str, str], List[ContentCandidate]] = {}

    for candidate in candidates:
        route = candidate.page_route
        slot_id = candidate.slot_id
        if route not in slot_map:
            unknown_route.append(candidate)
            continue
        if slot_id not in SUPPORTED_SLOT_IDS:
            unsupported_slot.append(candidate)
            continue
        if slot_id not in slot_map[route]:
            undeclared_slot.append(candidate)
            continue
        grouped.setdefault((route, slot_id), []).append(candidate)

    def _sorted(bucket: List[ContentCandidate]) -> Tuple[ContentCandidate, ...]:
        return tuple(sorted(bucket, key=lambda c: (c.page_route, c.slot_id)))

    bindings = {key: tuple(value) for key, value in grouped.items()}

    return CandidateClassification(
        bindings=bindings,
        unknown_route=_sorted(unknown_route),
        unsupported_slot=_sorted(unsupported_slot),
        undeclared_slot=_sorted(undeclared_slot),
    )


def missing_required_bindings(
    slot_map: Dict[str, Tuple[str, ...]],
    bindings: Dict[Tuple[str, str], Tuple[ContentCandidate, ...]],
) -> Tuple[Tuple[str, str], ...]:
    """Every ``(route, slot)`` declared in ``slot_map`` with zero candidates.

    Coverage requires only that at least one structurally valid candidate
    targeted the slot -- content-quality failures (banned phrases, length)
    on that candidate are reported separately (§8/§10), never folded into
    "missing", and a page declaring no slots requires nothing here (§13).
    """
    missing = [
        (route, slot_id)
        for route, slots in slot_map.items()
        for slot_id in slots
        if (route, slot_id) not in bindings
    ]
    return tuple(sorted(missing))


def unique_bindings_only(
    bindings: Dict[Tuple[str, str], Tuple[ContentCandidate, ...]]
) -> Dict[Tuple[str, str], ContentCandidate]:
    """Every ``(route, slot)`` binding with exactly one candidate -- the only
    bindings safe to treat as resolved.

    Ambiguous (duplicate) bindings are intentionally excluded here; they
    surface only via the duplicate-binding diagnostic, never as resolved
    content (§8). Every downstream consumer that needs "the accepted
    candidate for this slot" reads this single derived view rather than
    each re-deriving its own length check over ``bindings``.
    """
    return {key: group[0] for key, group in bindings.items() if len(group) == 1}


def duplicate_binding_keys(
    bindings: Dict[Tuple[str, str], Tuple[ContentCandidate, ...]]
) -> Tuple[Tuple[str, str], ...]:
    """Every ``(route, slot)`` binding with more than one candidate, sorted."""
    return tuple(sorted(key for key, group in bindings.items() if len(group) > 1))


# ---------------------------------------------------------------------------
# Policy checks over a single candidate body (§10)
# ---------------------------------------------------------------------------


def _is_letter(ch: str) -> bool:
    """True iff ``ch`` is a Unicode letter (general category starting with
    "L"): ASCII and non-ASCII alike (accented, non-Latin, etc.)."""
    return unicodedata.category(ch).startswith("L")


def _contains_at_letter_boundary(text: str, marker: str) -> bool:
    """True iff ``marker`` occurs in ``text``, case-insensitively, at a
    position not immediately adjacent to another letter on either side.

    A Unicode-aware letter-adjacency boundary -- deliberately not Python
    regex's default ``\\b`` (which treats digits and "_" as word characters,
    so "TODO_HERO_COPY" would have no boundary between "TODO" and "_" and
    would never match) and not a plain ASCII ``[A-Za-z]`` check (which would
    still misfire on a marker fused to a non-ASCII letter). A marker fused
    into a longer natural-language word -- a letter immediately before or
    after it, e.g. "photodocumentation" contains "todo" and "unleashed"
    contains "unleash" -- is excluded; a marker separated by an underscore,
    digit, brace, colon, whitespace, or other non-letter character -- e.g.
    "TODO_HERO_COPY", "Unleash your..." -- is still matched. Shared by both
    :func:`find_banned_phrases` and :func:`find_placeholder_markers` so the
    two apply one, consistently-reasoned matching policy rather than two.
    """
    lowered = text.lower()
    needle = marker.lower()
    start = 0
    while True:
        idx = lowered.find(needle, start)
        if idx == -1:
            return False
        before_is_letter = idx > 0 and _is_letter(text[idx - 1])
        after_index = idx + len(needle)
        after_is_letter = after_index < len(text) and _is_letter(text[after_index])
        if not before_is_letter and not after_is_letter:
            return True
        start = idx + 1


def find_banned_phrases(text: str) -> Tuple[str, ...]:
    """Banned voice phrases present in ``text``, case-insensitively, at a
    letter-adjacency boundary (see :func:`_contains_at_letter_boundary`).

    Every entry in ``BANNED_VOICE_PHRASES`` is checked at the same boundary
    ``find_placeholder_markers`` uses -- required for single-word entries
    like "unleash", whose ordinary inflections ("unleashed", "unleashing")
    are ordinary descriptive usage, not the banned marketing imperative
    ("Unleash your..."), and raw substring matching cannot tell them apart.
    Result order follows ``BANNED_VOICE_PHRASES``' fixed declared order, so
    it is deterministic regardless of where in ``text`` each phrase occurs.
    """
    return tuple(
        phrase
        for phrase in BANNED_VOICE_PHRASES
        if _contains_at_letter_boundary(text, phrase)
    )


def find_placeholder_markers(text: str) -> Tuple[str, ...]:
    """Placeholder/unfinished-content markers present in ``text`` (§10).

    ``{{``/``}}`` are matched as raw substrings (template-delimiter symbols
    never occur in finished prose). ``TODO``/``lorem`` are matched
    case-insensitively at a letter-adjacency boundary (see
    ``_contains_at_letter_boundary``) so a real compound word that fuses the
    letters into a longer word (e.g. "photodocumentation" contains "todo")
    is never false-flagged, while a placeholder joined to other text by an
    underscore, digit, or punctuation (e.g. "TODO_HERO_COPY") is still
    caught. Result order is deterministic: substring markers first
    (declared order), then word markers (declared order).
    """
    found: List[str] = [
        marker for marker in PLACEHOLDER_SUBSTRING_MARKERS if marker in text
    ]
    for marker in PLACEHOLDER_WORD_MARKERS:
        if _contains_at_letter_boundary(text, marker):
            found.append(marker)
    return tuple(found)


def _visible_char_count(text: str) -> int:
    """Count of characters in ``text`` that are neither whitespace nor a
    zero-width/invisible Unicode format character.

    ``str.strip()``/``str.isspace()`` alone do not catch Unicode general
    category "Cf" (Format) characters -- zero-width space, zero-width
    joiners, byte-order mark, soft hyphen, word joiner -- so a string made
    solely of such characters would otherwise satisfy a naive
    "non-whitespace" check while rendering as a blank, invisible heading.
    """
    return sum(
        1 for ch in text if not ch.isspace() and unicodedata.category(ch) != "Cf"
    )


def slot_length_violation(slot_id: str, text: str) -> Optional[Dict[str, object]]:
    """Length-policy violation for ``text`` in ``slot_id``, or ``None`` (§10 A10).

    Table-driven from constants/content.py's ``SLOT_MIN_LENGTHS`` /
    ``SLOT_MAX_LENGTHS`` / ``SLOTS_REQUIRING_VISIBLE_CONTENT`` -- a new
    slot's length policy is a new entry in those tables, never a new branch
    here. Character counting is ``len(text)`` over the Python ``str`` -- a
    count of Unicode code points as already decoded, never raw bytes, never
    a grapheme-cluster count -- so identical input text always yields an
    identical count on any platform.

    A slot in ``SLOTS_REQUIRING_VISIBLE_CONTENT`` (``hero_h1``) has its
    floor measured as "at least one visible character"
    (:func:`_visible_char_count`), not a plain numeric minimum, so a
    whitespace-only or invisible-character-only hero is rejected. Every
    other slot (``intro``) has no such visible-content special case: both
    of its bounds are plain ``len(text)`` comparisons. Only called for
    ``slot_id in SUPPORTED_SLOT_IDS`` -- every other ``slot_id`` was
    already rejected during structural classification.
    """
    if slot_id not in SLOT_MIN_LENGTHS:
        raise ValueError("no length policy declared for slot_id %r" % slot_id)

    min_chars = SLOT_MIN_LENGTHS[slot_id]
    max_chars = SLOT_MAX_LENGTHS[slot_id]

    if slot_id in SLOTS_REQUIRING_VISIBLE_CONTENT:
        if _visible_char_count(text) < min_chars:
            return {
                "reason": "empty_or_whitespace",
                "length": len(text),
                "limit": min_chars,
            }
    elif len(text) < min_chars:
        return {"reason": "too_short", "length": len(text), "limit": min_chars}

    if len(text) > max_chars:
        return {"reason": "too_long", "length": len(text), "limit": max_chars}

    return None
