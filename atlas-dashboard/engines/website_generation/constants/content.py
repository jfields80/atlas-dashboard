"""Content Engine validation-policy constants (AES-WEB-001 §5.4 / Part 2;
internal sequencing label AES-WEB-002J.4).

Supported content slots, per-slot length bounds, and placeholder/banned
content-marker policy for the Content Engine's validation airlock.
Constants only -- no computation, no imports beyond the standard library
(§3.2 constants-are-stdlib-only doctrine). ``engines/website_generation/
content/`` is the only consumer.

Slot-id namespace note: these are the same bare slot-id strings the
Information Architecture Engine declares on ``PagePlan.content_slots``
(``constants/ia.py``'s ``CONTENT_SLOT_HERO_H1`` / ``CONTENT_SLOT_INTRO``).
Per the constants-are-stdlib-only doctrine this module may not import
``constants/ia.py``, so the two slot-id strings are independently declared
here and must stay byte-identical to their ``constants/ia.py`` counterparts;
a cross-module consistency test enforces the equality.

Scope reminder (Decision A1): these constants describe what the Content
Engine *validates* -- supported slot vocabulary, length bounds, and
disallowed markers. They are never phrase libraries, sentence templates, or
anything that could be read as a copy-authoring source; the engine has no
copy-generation path.
"""

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Supported content slots (AES-WEB-001 §5.4 minimum viable slot set; the J.3
# SiteArchitecture fixture's two content_slots -- see constants/ia.py's
# CONTENT_SLOTS_BY_ROLE). An unsupported slot_id is always a deterministic
# validation error, never silently accepted or dropped.
# ---------------------------------------------------------------------------

SLOT_HERO_H1 = "hero_h1"
SLOT_INTRO = "intro"

SUPPORTED_SLOT_IDS: Tuple[str, ...] = (
    SLOT_HERO_H1,
    SLOT_INTRO,
)

# ---------------------------------------------------------------------------
# Slot length bounds (Decision A10). Character counting policy (deterministic
# and platform-independent): every bound below is checked against
# ``len(text)`` on the candidate body's Python ``str`` -- a count of Unicode
# code points as already decoded into the ``str``, never raw bytes, never a
# grapheme-cluster count, never re-encoded or locale-normalized first. The
# same input string therefore always yields the same length on any platform.
#
# hero_h1 asymmetry (documented, not an oversight): the floor is expressed as
# "at least one non-whitespace character" rather than a numeric minimum, so a
# whitespace-only hero is rejected even though it could otherwise satisfy a
# trivial numeric minimum of 1. "Non-whitespace" is deliberately stronger
# than ``str.isspace()``: zero-width/invisible Unicode format characters
# (category "Cf" -- zero-width space, joiners, BOM, soft hyphen) are not
# ``str.isspace()`` but are not visible content either, so they do not count
# toward the floor (content_validators.py's ``_visible_char_count``).
# ``intro`` has no such visible-content special case; its bounds are plain
# ``len(text)`` comparisons against the min/max below, per Decision A10's
# literal wording.
#
# The two dicts and the membership tuple below are the complete per-slot
# policy table content_validators.slot_length_violation() dispatches from --
# a new slot's length policy is a new entry in each, never a new branch
# (mirrors constants/brand.py's per-family dict-keyed tables: PALETTES,
# TYPE_SCALES, RADIUS_SCALES, VOICE_REGISTER_FRAGMENTS).
# ---------------------------------------------------------------------------

HERO_H1_MIN_NON_WHITESPACE_CHARS = 1
HERO_H1_MAX_CHARS = 80

INTRO_MIN_CHARS = 40
INTRO_MAX_CHARS = 600

SLOT_MIN_LENGTHS: Dict[str, int] = {
    SLOT_HERO_H1: HERO_H1_MIN_NON_WHITESPACE_CHARS,
    SLOT_INTRO: INTRO_MIN_CHARS,
}

SLOT_MAX_LENGTHS: Dict[str, int] = {
    SLOT_HERO_H1: HERO_H1_MAX_CHARS,
    SLOT_INTRO: INTRO_MAX_CHARS,
}

# Slots whose minimum is measured as "at least one visible character"
# (see hero_h1 asymmetry above) rather than a plain ``len(text)`` floor.
SLOTS_REQUIRING_VISIBLE_CONTENT: Tuple[str, ...] = (SLOT_HERO_H1,)

# ---------------------------------------------------------------------------
# Banned-phrase and placeholder-marker matching policy (documented,
# deterministic; AES-WEB-001 §10.2: "no placeholder tokens ({{, TODO,
# lorem)"). Both ``BANNED_VOICE_PHRASES`` (constants/brand.py) and the
# placeholder word markers below are matched by the same rule:
#
# * "{{" and "}}" are the sole exception -- matched as raw substrings. They
#   are template-delimiter symbols that never occur in finished prose, so no
#   letter-adjacency concept applies and a substring check carries no
#   false-positive risk.
# * Every other entry ("TODO", "lorem", and every ``BANNED_VOICE_PHRASES``
#   phrase) is matched case-insensitively wherever it is not directly
#   adjacent to another Unicode letter on either side (a custom
#   letter-adjacency boundary -- content_validators._contains_at_letter_
#   boundary -- deliberately not Python regex's default ``\\b``, which
#   treats digits/underscore as word characters, and not a plain ASCII
#   ``[A-Za-z]`` check, which would still miss non-ASCII letters). This
#   means:
#     - a real compound word that fuses the letters into a longer natural-
#       language word -- e.g. "photodocumentation" contains "todo", and
#       "unleashed"/"unleashing" contain "unleash" -- is never false-
#       flagged, because it is letter-adjacent on at least one side; and
#     - a marker joined to other text by an underscore, digit, brace,
#       colon, or other non-letter separator -- e.g. "TODO_HERO_COPY",
#       "{{TODO}}" -- or the banned marketing imperative itself (e.g.
#       "Unleash your...") is still flagged.
#   This is the "safer deterministic boundary check" the banned-content
#   policy calls for, precise in both directions rather than only avoiding
#   false positives.
# ---------------------------------------------------------------------------

PLACEHOLDER_MARKER_OPEN_BRACE = "{{"
PLACEHOLDER_MARKER_CLOSE_BRACE = "}}"

PLACEHOLDER_SUBSTRING_MARKERS: Tuple[str, ...] = (
    PLACEHOLDER_MARKER_OPEN_BRACE,
    PLACEHOLDER_MARKER_CLOSE_BRACE,
)

PLACEHOLDER_WORD_MARKERS: Tuple[str, ...] = (
    "TODO",
    "lorem",
)
