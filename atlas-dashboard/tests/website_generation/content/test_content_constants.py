"""Content Engine constants sanity checks (AES-WEB-001 §5.4; Decision A10).

Cross-module slot-id consistency and length/marker sanity, kept separate
from behavioral engine tests (test_content_engine.py) and validator-internal
tests (test_content_validators.py).
"""

from __future__ import annotations

from engines.website_generation.constants.content import (
    HERO_H1_MAX_CHARS,
    HERO_H1_MIN_NON_WHITESPACE_CHARS,
    INTRO_MAX_CHARS,
    INTRO_MIN_CHARS,
    PLACEHOLDER_MARKER_CLOSE_BRACE,
    PLACEHOLDER_MARKER_OPEN_BRACE,
    PLACEHOLDER_SUBSTRING_MARKERS,
    PLACEHOLDER_WORD_MARKERS,
    SLOT_HERO_H1,
    SLOT_INTRO,
    SLOT_MAX_LENGTHS,
    SLOT_MIN_LENGTHS,
    SLOTS_REQUIRING_VISIBLE_CONTENT,
    SUPPORTED_SLOT_IDS,
)
from engines.website_generation.constants.ia import (
    CONTENT_SLOT_HERO_H1,
    CONTENT_SLOT_INTRO,
)


class TestSlotIdCrossModuleConsistency:
    """constants/content.py may not import constants/ia.py (constants are
    stdlib-only, §3.2), so the two slot-id namespaces are independently
    declared and must be kept byte-identical by hand -- this is the
    enforcing test constants/content.py's module docstring promises."""

    def test_hero_h1_matches_ia_constant(self):
        assert SLOT_HERO_H1 == CONTENT_SLOT_HERO_H1

    def test_intro_matches_ia_constant(self):
        assert SLOT_INTRO == CONTENT_SLOT_INTRO

    def test_supported_slot_ids_cover_exactly_the_j3_fixture_slots(self):
        assert set(SUPPORTED_SLOT_IDS) == {CONTENT_SLOT_HERO_H1, CONTENT_SLOT_INTRO}

    def test_supported_slot_ids_has_no_duplicates(self):
        assert len(SUPPORTED_SLOT_IDS) == len(set(SUPPORTED_SLOT_IDS))


class TestLengthBounds:
    def test_hero_h1_bounds_match_decision_a10(self):
        assert HERO_H1_MIN_NON_WHITESPACE_CHARS == 1
        assert HERO_H1_MAX_CHARS == 80

    def test_intro_bounds_match_decision_a10(self):
        assert INTRO_MIN_CHARS == 40
        assert INTRO_MAX_CHARS == 600

    def test_intro_min_is_below_max(self):
        assert INTRO_MIN_CHARS < INTRO_MAX_CHARS


class TestSlotLengthPolicyTable:
    """The per-slot length policy table content_validators.slot_length_
    violation() dispatches from -- a new slot is a new entry in each of
    these, never a new branch (mirrors constants/brand.py's per-family
    dict-keyed tables)."""

    def test_every_supported_slot_has_min_and_max_entries(self):
        assert set(SLOT_MIN_LENGTHS) == set(SUPPORTED_SLOT_IDS)
        assert set(SLOT_MAX_LENGTHS) == set(SUPPORTED_SLOT_IDS)

    def test_min_lengths_match_named_constants(self):
        assert SLOT_MIN_LENGTHS[SLOT_HERO_H1] == HERO_H1_MIN_NON_WHITESPACE_CHARS
        assert SLOT_MIN_LENGTHS[SLOT_INTRO] == INTRO_MIN_CHARS

    def test_max_lengths_match_named_constants(self):
        assert SLOT_MAX_LENGTHS[SLOT_HERO_H1] == HERO_H1_MAX_CHARS
        assert SLOT_MAX_LENGTHS[SLOT_INTRO] == INTRO_MAX_CHARS

    def test_every_min_is_below_its_max(self):
        for slot_id in SUPPORTED_SLOT_IDS:
            assert SLOT_MIN_LENGTHS[slot_id] < SLOT_MAX_LENGTHS[slot_id]

    def test_only_hero_h1_requires_visible_content(self):
        assert SLOTS_REQUIRING_VISIBLE_CONTENT == (SLOT_HERO_H1,)
        assert SLOT_INTRO not in SLOTS_REQUIRING_VISIBLE_CONTENT

    def test_visible_content_slots_are_a_subset_of_supported_slots(self):
        assert set(SLOTS_REQUIRING_VISIBLE_CONTENT) <= set(SUPPORTED_SLOT_IDS)


class TestPlaceholderMarkerConstants:
    def test_substring_markers_are_the_brace_pair(self):
        assert PLACEHOLDER_SUBSTRING_MARKERS == (
            PLACEHOLDER_MARKER_OPEN_BRACE,
            PLACEHOLDER_MARKER_CLOSE_BRACE,
        )
        assert PLACEHOLDER_MARKER_OPEN_BRACE == "{{"
        assert PLACEHOLDER_MARKER_CLOSE_BRACE == "}}"

    def test_word_markers_include_todo_and_lorem(self):
        assert PLACEHOLDER_WORD_MARKERS == ("TODO", "lorem")
