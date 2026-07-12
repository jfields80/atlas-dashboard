"""Direct unit tests for Content Engine validator internals (AES-WEB-001
§5.4).

Hand-built inputs exercising classification and policy-check edge cases
that ``ContentEngine.validate()``'s golden path cannot reach directly --
every page in the real IA-produced fixture declares both ``hero_h1`` and
``intro``, so undeclared-slot and empty-slot-page cases need hand-built
``PagePlan``/``slot_map`` inputs, mirroring how
``test_information_architecture_engine.py::TestStructuralInvariantsDirectly``
exercises ``_validate_site_graph`` directly.
"""

from __future__ import annotations

import pytest

from engines.website_generation.constants.content import (
    HERO_H1_MAX_CHARS,
    INTRO_MAX_CHARS,
    INTRO_MIN_CHARS,
    SLOT_HERO_H1,
    SLOT_INTRO,
)
from engines.website_generation.content.content_validators import (
    classify_candidates,
    find_banned_phrases,
    find_placeholder_markers,
    missing_required_bindings,
    page_slot_map,
    slot_length_violation,
)
from engines.website_generation.contracts.artifacts import (
    ArtifactKind,
    ContentCandidate,
    PagePlan,
)


def _candidate(route: str, slot_id: str, body: str) -> ContentCandidate:
    return ContentCandidate(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.CONTENT_CANDIDATE,
        source_hashes={},
        page_route=route,
        slot_id=slot_id,
        body=body,
    )


class TestPageSlotMap:
    def test_preserves_declared_slot_order_verbatim(self):
        pages = (
            PagePlan(
                route="/", page_type="home", content_slots=(SLOT_INTRO, SLOT_HERO_H1)
            ),
        )
        assert page_slot_map(pages) == {"/": (SLOT_INTRO, SLOT_HERO_H1)}

    def test_page_with_no_slots_maps_to_empty_tuple(self):
        pages = (PagePlan(route="/about/", page_type="legal", content_slots=()),)
        assert page_slot_map(pages) == {"/about/": ()}

    def test_multiple_pages_each_keep_their_own_slots(self):
        pages = (
            PagePlan(route="/", page_type="home", content_slots=(SLOT_HERO_H1,)),
            PagePlan(
                route="/hotels/",
                page_type="category",
                content_slots=(SLOT_HERO_H1, SLOT_INTRO),
            ),
        )
        assert page_slot_map(pages) == {
            "/": (SLOT_HERO_H1,),
            "/hotels/": (SLOT_HERO_H1, SLOT_INTRO),
        }


class TestClassifyCandidates:
    def test_valid_candidate_binds_uniquely(self):
        slot_map = {"/": (SLOT_HERO_H1,)}
        candidate = _candidate("/", SLOT_HERO_H1, "Body")
        result = classify_candidates((candidate,), slot_map)
        assert result.bindings == {("/", SLOT_HERO_H1): (candidate,)}
        assert result.unknown_route == ()
        assert result.unsupported_slot == ()
        assert result.undeclared_slot == ()

    def test_unknown_route_bucketed_separately(self):
        slot_map = {"/": (SLOT_HERO_H1,)}
        candidate = _candidate("/missing/", SLOT_HERO_H1, "Body")
        result = classify_candidates((candidate,), slot_map)
        assert result.unknown_route == (candidate,)
        assert result.bindings == {}

    def test_unsupported_slot_bucketed_separately(self):
        # A route that exists, but a slot_id the engine's vocabulary does
        # not recognize at all -- distinct from "undeclared for this page".
        slot_map = {"/": (SLOT_HERO_H1,)}
        candidate = _candidate("/", "not_a_real_slot", "Body")
        result = classify_candidates((candidate,), slot_map)
        assert result.unsupported_slot == (candidate,)
        assert result.bindings == {}

    def test_undeclared_slot_for_page_bucketed_separately(self):
        # "intro" is globally supported but not declared on this page.
        slot_map = {"/": (SLOT_HERO_H1,)}
        candidate = _candidate("/", SLOT_INTRO, "B" * 50)
        result = classify_candidates((candidate,), slot_map)
        assert result.undeclared_slot == (candidate,)
        assert result.bindings == {}

    def test_duplicate_candidates_grouped_under_one_key(self):
        slot_map = {"/": (SLOT_HERO_H1,)}
        a = _candidate("/", SLOT_HERO_H1, "First")
        b = _candidate("/", SLOT_HERO_H1, "Second")
        result = classify_candidates((a, b), slot_map)
        group = result.bindings[("/", SLOT_HERO_H1)]
        assert len(group) == 2
        assert {c.body for c in group} == {"First", "Second"}

    def test_malformed_empty_route_falls_into_unknown_route(self):
        slot_map = {"/": (SLOT_HERO_H1,)}
        candidate = _candidate("", SLOT_HERO_H1, "Body with no route")
        result = classify_candidates((candidate,), slot_map)
        assert result.unknown_route == (candidate,)

    def test_classification_is_independent_of_input_order(self):
        slot_map = {"/": (SLOT_HERO_H1,), "/other/": (SLOT_HERO_H1,)}
        a = _candidate("/missing/", SLOT_HERO_H1, "A")
        b = _candidate("/", "bad_slot", "B")
        c = _candidate("/other/", SLOT_HERO_H1, "C")
        forward = classify_candidates((a, b, c), slot_map)
        backward = classify_candidates((c, b, a), slot_map)
        assert forward.unknown_route == backward.unknown_route
        assert forward.unsupported_slot == backward.unsupported_slot
        assert forward.bindings == backward.bindings


class TestMissingRequiredBindings:
    def test_reports_every_uncovered_slot_sorted(self):
        slot_map = {"/": (SLOT_HERO_H1, SLOT_INTRO)}
        bindings = {("/", SLOT_HERO_H1): (_candidate("/", SLOT_HERO_H1, "x"),)}
        assert missing_required_bindings(slot_map, bindings) == (("/", SLOT_INTRO),)

    def test_page_with_no_slots_requires_nothing(self):
        slot_map = {"/about/": ()}
        assert missing_required_bindings(slot_map, {}) == ()

    def test_fully_covered_page_reports_nothing(self):
        slot_map = {"/": (SLOT_HERO_H1,)}
        bindings = {("/", SLOT_HERO_H1): (_candidate("/", SLOT_HERO_H1, "x"),)}
        assert missing_required_bindings(slot_map, bindings) == ()

    def test_duplicate_binding_still_counts_as_covered(self):
        # Coverage only asks "is at least one candidate present" -- the
        # ambiguity itself is a separate diagnostic (§8), not "missing".
        slot_map = {"/": (SLOT_HERO_H1,)}
        bindings = {
            ("/", SLOT_HERO_H1): (
                _candidate("/", SLOT_HERO_H1, "First"),
                _candidate("/", SLOT_HERO_H1, "Second"),
            )
        }
        assert missing_required_bindings(slot_map, bindings) == ()


class TestFindBannedPhrases:
    def test_case_insensitive_match(self):
        assert find_banned_phrases("This is PAWSOME news for pets.") == ("pawsome",)

    def test_no_match_returns_empty_tuple(self):
        assert find_banned_phrases("This is great news for pets.") == ()

    def test_multiple_phrases_all_reported(self):
        text = "Unleash your PawFect adventure with your trusted partner."
        found = find_banned_phrases(text)
        assert "unleash" in found
        assert "pawfect" in found
        assert "your trusted partner" in found

    def test_mixed_case_furbaby_detected(self):
        assert find_banned_phrases("Every FurBaby deserves a good trip.") == (
            "furbaby",
        )

    def test_discover_the_best_detected(self):
        assert "discover the best" in find_banned_phrases(
            "Discover The Best spots in town."
        )

    def test_unleash_marketing_imperative_detected(self):
        assert find_banned_phrases("Unleash your inner adventurer!") == ("unleash",)

    def test_unleashed_ordinary_inflection_not_flagged(self):
        # "unleash" is a real dictionary word; its ordinary inflections are
        # not the banned marketing imperative and must not be false-flagged
        # (letter-adjacency boundary, same policy as placeholder markers).
        text = "The ranger unleashed the falcon at dawn."
        assert find_banned_phrases(text) == ()

    def test_unleashing_ordinary_inflection_not_flagged(self):
        text = "Pets are allowed off-leash in this fenced field for unleashing."
        assert find_banned_phrases(text) == ()


class TestFindPlaceholderMarkers:
    def test_double_open_brace_detected(self):
        assert "{{" in find_placeholder_markers("Welcome to {{business_name}}.")

    def test_double_close_brace_detected(self):
        assert "}}" in find_placeholder_markers("Welcome to {{business_name}}.")

    def test_todo_word_detected_case_insensitively(self):
        assert find_placeholder_markers("todo: write real copy here.") == ("TODO",)

    def test_lorem_word_detected(self):
        assert find_placeholder_markers("Lorem ipsum dolor sit amet.") == ("lorem",)

    def test_todo_substring_inside_real_word_is_not_flagged(self):
        # "photodocumentation" contains "todo" as a raw substring; the
        # word-boundary regex must not flag it (§10 false-positive guard).
        text = "Completed the photodocumentation of every room."
        assert find_placeholder_markers(text) == ()

    def test_lorem_as_prefix_of_a_larger_token_is_not_flagged(self):
        # "loremish" contains "lorem" as a raw substring but is not the
        # standalone word "lorem".
        assert find_placeholder_markers("A loremish-sounding brand name.") == ()

    def test_clean_text_yields_no_markers(self):
        assert find_placeholder_markers("A completely ordinary sentence.") == ()

    def test_result_order_is_substrings_then_words(self):
        text = "{{todo}} lorem }}"
        found = find_placeholder_markers(text)
        assert found == ("{{", "}}", "TODO", "lorem")

    def test_underscore_joined_todo_placeholder_is_flagged(self):
        # Python regex's default \b treats "_" as a word character, so a
        # naive \bTODO\b would miss this common placeholder-naming style.
        # The letter-adjacency boundary must still catch it.
        text = "Please finalize TODO_HERO_COPY before launch."
        assert "TODO" in find_placeholder_markers(text)

    def test_underscore_joined_lorem_placeholder_is_flagged(self):
        text = "the lorem_ipsum_placeholder text needs replacing"
        assert "lorem" in find_placeholder_markers(text)

    def test_digit_joined_todo_placeholder_is_flagged(self):
        text = "See TODO123 for details."
        assert "TODO" in find_placeholder_markers(text)

    def test_brace_adjacent_todo_still_flagged(self):
        assert find_placeholder_markers("{{TODO}}") == ("{{", "}}", "TODO")

    def test_todo_fused_to_non_ascii_letter_is_not_flagged(self):
        # A plain [A-Za-z] boundary check would miss that "é" is a letter
        # and false-flag this fused word; the boundary must be Unicode-aware.
        assert find_placeholder_markers("todoésumé is not a real word") == ()

    def test_lorem_fused_to_non_ascii_letter_is_not_flagged(self):
        assert find_placeholder_markers("mycafélorem brand exists") == ()


class TestSlotLengthViolation:
    def test_hero_h1_within_bounds_passes(self):
        assert slot_length_violation(SLOT_HERO_H1, "A Fine Title") is None

    def test_hero_h1_exact_max_boundary_passes(self):
        assert slot_length_violation(SLOT_HERO_H1, "H" * HERO_H1_MAX_CHARS) is None

    def test_hero_h1_single_non_whitespace_char_boundary_passes(self):
        assert slot_length_violation(SLOT_HERO_H1, "H") is None

    def test_hero_h1_over_max_fails(self):
        violation = slot_length_violation(SLOT_HERO_H1, "H" * (HERO_H1_MAX_CHARS + 1))
        assert violation == {
            "reason": "too_long",
            "length": HERO_H1_MAX_CHARS + 1,
            "limit": HERO_H1_MAX_CHARS,
        }

    def test_hero_h1_empty_fails(self):
        violation = slot_length_violation(SLOT_HERO_H1, "")
        assert violation["reason"] == "empty_or_whitespace"

    def test_hero_h1_whitespace_only_fails(self):
        violation = slot_length_violation(SLOT_HERO_H1, "    ")
        assert violation["reason"] == "empty_or_whitespace"

    def test_hero_h1_zero_width_space_only_fails(self):
        # U+200B is not str.isspace(), so a naive strip()-based check would
        # accept this as "1 non-whitespace character" while it renders as a
        # blank, invisible heading.
        violation = slot_length_violation(SLOT_HERO_H1, "​")
        assert violation["reason"] == "empty_or_whitespace"

    def test_hero_h1_byte_order_mark_only_fails(self):
        violation = slot_length_violation(SLOT_HERO_H1, "﻿﻿")
        assert violation["reason"] == "empty_or_whitespace"

    def test_hero_h1_zero_width_joiner_mixed_with_whitespace_fails(self):
        violation = slot_length_violation(SLOT_HERO_H1, "  ‌‍  ")
        assert violation["reason"] == "empty_or_whitespace"

    def test_hero_h1_visible_character_after_zero_width_space_passes(self):
        # A zero-width space alongside real visible content is fine -- only
        # a hero with *zero* visible characters is rejected.
        assert slot_length_violation(SLOT_HERO_H1, "​Title") is None

    def test_intro_within_bounds_passes(self):
        assert slot_length_violation(SLOT_INTRO, "I" * 100) is None

    def test_intro_exact_min_boundary_passes(self):
        assert slot_length_violation(SLOT_INTRO, "I" * INTRO_MIN_CHARS) is None

    def test_intro_exact_max_boundary_passes(self):
        assert slot_length_violation(SLOT_INTRO, "I" * INTRO_MAX_CHARS) is None

    def test_intro_under_min_fails(self):
        violation = slot_length_violation(SLOT_INTRO, "I" * (INTRO_MIN_CHARS - 1))
        assert violation == {
            "reason": "too_short",
            "length": INTRO_MIN_CHARS - 1,
            "limit": INTRO_MIN_CHARS,
        }

    def test_intro_over_max_fails(self):
        violation = slot_length_violation(SLOT_INTRO, "I" * (INTRO_MAX_CHARS + 1))
        assert violation == {
            "reason": "too_long",
            "length": INTRO_MAX_CHARS + 1,
            "limit": INTRO_MAX_CHARS,
        }

    def test_unsupported_slot_id_raises(self):
        with pytest.raises(ValueError):
            slot_length_violation("not_a_real_slot", "text")
