"""Direct unit tests for SEO Engine validator internals (AES-WEB-001 §5.8;
AES-WEB-002J.5 Decisions D1-D5).

Hand-built inputs exercising per-page lookup, title composition, meta
truncation, and structural/length validators in isolation, mirroring
``test_content_validators.py``'s direct-unit-test precedent for
``content_validators.py``.
"""

from __future__ import annotations

import pytest

from engines.website_generation.constants.seo import (
    CANONICAL_URL_MAX_LENGTH,
    META_DESCRIPTION_MAX_LENGTH,
    META_DESCRIPTION_MIN_LENGTH,
    TITLE_MAX_LENGTH,
)
from engines.website_generation.contracts.artifacts import ContentBlock, PagePlan
from engines.website_generation.seo.seo_validators import (
    canonical_length_violation,
    compose_title,
    duplicate_routes,
    index_content_blocks,
    meta_length_violation,
    missing_content_slots,
    role_source_slots,
    title_collisions,
    title_length_violation,
    truncate_meta_description,
    unknown_content_routes,
)


def _block(route: str, slot_id: str, text: str) -> ContentBlock:
    return ContentBlock(page_route=route, slot_id=slot_id, text=text)


# ---------------------------------------------------------------------------
# Per-page lookup
# ---------------------------------------------------------------------------


class TestIndexContentBlocks:
    def test_indexes_by_route_and_slot(self):
        a = _block("/", "hero_h1", "Hello")
        b = _block("/", "intro", "World")
        index = index_content_blocks((a, b))
        assert index[("/", "hero_h1")] is a
        assert index[("/", "intro")] is b

    def test_missing_key_is_absent(self):
        index = index_content_blocks((_block("/", "hero_h1", "Hello"),))
        assert ("/", "intro") not in index

    def test_independent_of_input_order(self):
        a = _block("/", "hero_h1", "Hello")
        b = _block("/hotels/", "hero_h1", "Hotels")
        forward = index_content_blocks((a, b))
        backward = index_content_blocks((b, a))
        assert forward == backward

    def test_duplicate_key_keeps_last_occurrence(self):
        first = _block("/", "hero_h1", "First")
        second = _block("/", "hero_h1", "Second")
        index = index_content_blocks((first, second))
        assert index[("/", "hero_h1")] is second


# ---------------------------------------------------------------------------
# Structural validators
# ---------------------------------------------------------------------------


class TestDuplicateRoutes:
    def test_no_duplicates_returns_empty(self):
        assert duplicate_routes(["/", "/hotels/", "/parks/"]) == ()

    def test_single_duplicate_reported(self):
        assert duplicate_routes(["/", "/hotels/", "/"]) == ("/",)

    def test_multiple_duplicates_sorted(self):
        assert duplicate_routes(["/parks/", "/", "/parks/", "/", "/"]) == ("/", "/parks/")

    def test_triplicate_reported_once(self):
        assert duplicate_routes(["/", "/", "/"]) == ("/",)

    def test_empty_input_returns_empty(self):
        assert duplicate_routes([]) == ()


class TestUnknownContentRoutes:
    def test_all_routes_known_returns_empty(self):
        blocks = (_block("/", "hero_h1", "x"),)
        assert unknown_content_routes(blocks, ["/"]) == ()

    def test_unknown_route_reported(self):
        blocks = (_block("/orphan/", "hero_h1", "x"),)
        assert unknown_content_routes(blocks, ["/"]) == ("/orphan/",)

    def test_distinct_unknown_routes_deduplicated_and_sorted(self):
        blocks = (
            _block("/b-orphan/", "hero_h1", "x"),
            _block("/b-orphan/", "intro", "y"),
            _block("/a-orphan/", "hero_h1", "z"),
        )
        assert unknown_content_routes(blocks, []) == ("/a-orphan/", "/b-orphan/")

    def test_no_blocks_returns_empty(self):
        assert unknown_content_routes((), ["/"]) == ()


# ---------------------------------------------------------------------------
# Role support (D1/D2 rule-table lookup)
# ---------------------------------------------------------------------------


class TestRoleSourceSlots:
    def test_home_resolves_to_hero_h1_and_intro(self):
        assert role_source_slots("home") == ("hero_h1", "intro")

    def test_category_resolves_to_hero_h1_and_intro(self):
        assert role_source_slots("category") == ("hero_h1", "intro")

    def test_unknown_role_returns_none(self):
        assert role_source_slots("mystery-role") is None

    def test_empty_role_returns_none(self):
        assert role_source_slots("") is None


class TestMissingContentSlots:
    def test_both_present_returns_empty(self):
        index = index_content_blocks(
            (_block("/", "hero_h1", "H"), _block("/", "intro", "I" * 60))
        )
        page = PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro"))
        assert missing_content_slots(page, "hero_h1", "intro", index) == ()

    def test_hero_missing_reported(self):
        index = index_content_blocks((_block("/", "intro", "I" * 60),))
        page = PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro"))
        assert missing_content_slots(page, "hero_h1", "intro", index) == ("hero_h1",)

    def test_intro_missing_reported(self):
        index = index_content_blocks((_block("/", "hero_h1", "H"),))
        page = PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro"))
        assert missing_content_slots(page, "hero_h1", "intro", index) == ("intro",)

    def test_both_missing_reported_sorted(self):
        index = index_content_blocks(())
        page = PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro"))
        assert missing_content_slots(page, "hero_h1", "intro", index) == ("hero_h1", "intro")

    def test_only_checks_this_pages_route(self):
        index = index_content_blocks(
            (_block("/other/", "hero_h1", "H"), _block("/other/", "intro", "I" * 60))
        )
        page = PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro"))
        assert missing_content_slots(page, "hero_h1", "intro", index) == ("hero_h1", "intro")


# ---------------------------------------------------------------------------
# Title composition and fallback ladder (Decision D2)
# ---------------------------------------------------------------------------


class TestComposeTitle:
    def test_full_form_when_within_limit(self):
        assert compose_title("Find Great Stays", "Pet Trip Finder") == (
            "Find Great Stays | Pet Trip Finder"
        )

    def test_separator_is_space_pipe_space(self):
        title = compose_title("Hero", "Biz")
        assert title == "Hero | Biz"

    def test_never_appends_ellipsis_or_punctuation(self):
        hero = "H" * 70
        title = compose_title(hero, "Biz")
        assert "..." not in title
        assert title == hero[:TITLE_MAX_LENGTH]


class TestScopeProtection:
    def test_truncation_only_removes_characters(self):
        # Every character of a hard-cut title is a prefix of the original
        # hero_h1 -- nothing is appended, substituted, or rewritten.
        hero = "H" * 90
        title = compose_title(hero, "Biz")
        assert hero.startswith(title)


class TestTruncation:
    """Meta description (D1) and title (D2) truncation, unit-level."""

    # --- Meta description (D1) ---

    def test_meta_verbatim_at_length_le_160(self):
        text = "A short, valid introduction that easily fits within the limit."
        assert len(text) <= META_DESCRIPTION_MAX_LENGTH
        assert truncate_meta_description(text) == text

    def test_meta_word_boundary_truncation_just_over_160(self):
        text = (
            "Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima "
            "mike november oscar papa quebec romeo sierra tango uniform victor whiskey "
            "yankee zulu extra words to push this well past one hundred and sixty."
        )
        assert len(text) > META_DESCRIPTION_MAX_LENGTH
        result = truncate_meta_description(text)
        expected = (
            "Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima "
            "mike november oscar papa quebec romeo sierra tango uniform victor whiskey "
            "yankee zulu"
        )
        assert result == expected
        assert len(result) == 158
        assert len(result) <= META_DESCRIPTION_MAX_LENGTH
        # The cut lands exactly at a word boundary -- the next original
        # character is whitespace, never a split word.
        assert text[len(result) : len(result) + 1] == " "

    def test_meta_no_whitespace_hard_cut_fallback(self):
        text = "A" * 170
        result = truncate_meta_description(text)
        assert result == "A" * META_DESCRIPTION_MAX_LENGTH
        assert len(result) == META_DESCRIPTION_MAX_LENGTH

    def test_meta_boundary_at_exactly_160(self):
        text = "B" * META_DESCRIPTION_MAX_LENGTH
        assert truncate_meta_description(text) == text

    def test_meta_boundary_at_161(self):
        padded_words = (
            "Pet Trip Finder helps travelers find verified pet friendly hotels parks "
            "and restaurants across the country with details checked before they go "
            "see zzzzzzzzzzzzzz"
        )
        assert len(padded_words) == 161
        result = truncate_meta_description(padded_words)
        assert len(result) < 161
        assert len(result) <= META_DESCRIPTION_MAX_LENGTH
        assert padded_words.startswith(result)
        assert padded_words[len(result) : len(result) + 1] == " "

    def test_meta_multibyte_character_counted_as_one_code_point(self):
        # "é" is multiple bytes in UTF-8 but one Unicode code point; a
        # byte-based truncation would cut at a different position.
        text = "é" * 170
        result = truncate_meta_description(text)
        assert result == "é" * META_DESCRIPTION_MAX_LENGTH
        assert len(result) == META_DESCRIPTION_MAX_LENGTH

    def test_meta_zero_width_character_is_not_a_whitespace_boundary(self):
        # U+200B is not str.isspace(); it must never be mistaken for a word
        # boundary, and it must not be silently dropped by rstrip() either.
        text = "Alpha bravo " + ("x" * 140) + "​" + ("y" * 20)
        assert len(text) > META_DESCRIPTION_MAX_LENGTH
        result = truncate_meta_description(text)
        assert result == "Alpha bravo"
        assert "​" not in result

    # --- Title (D2) ---

    def test_title_full_form_when_length_le_60(self):
        title = compose_title("Find Pet-Friendly Stays", "Pet Trip Finder")
        assert title == "Find Pet-Friendly Stays | Pet Trip Finder"
        assert len(title) <= TITLE_MAX_LENGTH

    def test_title_hero_h1_only_fallback(self):
        hero = "H" * 55
        business_name = "A Very Long Business Name That Pushes Combined Over Sixty"
        full_title = hero + " | " + business_name
        assert len(full_title) > TITLE_MAX_LENGTH
        assert len(hero) <= TITLE_MAX_LENGTH
        assert compose_title(hero, business_name) == hero

    def test_title_hard_cut_fallback(self):
        hero = "H" * 70
        assert len(hero) > TITLE_MAX_LENGTH
        result = compose_title(hero, "Biz")
        assert result == hero[:TITLE_MAX_LENGTH]
        assert len(result) == TITLE_MAX_LENGTH

    def test_title_boundary_at_exactly_60(self):
        hero = "H" * 54
        business_name = "Biz"
        full_title = hero + " | " + business_name
        assert len(full_title) == TITLE_MAX_LENGTH
        assert compose_title(hero, business_name) == full_title

    def test_title_boundary_at_61(self):
        hero = "H" * 55
        business_name = "Biz"
        full_title = hero + " | " + business_name
        assert len(full_title) == TITLE_MAX_LENGTH + 1
        # hero_h1 alone fits, so the fallback ladder uses it verbatim
        # rather than hard-cutting.
        assert compose_title(hero, business_name) == hero
        assert len(hero) <= TITLE_MAX_LENGTH

    def test_title_multibyte_character_counted_as_one_code_point(self):
        hero = "é" * 70
        result = compose_title(hero, "Biz")
        assert result == hero[:TITLE_MAX_LENGTH]
        assert len(result) == TITLE_MAX_LENGTH

    def test_title_zero_width_character_counts_toward_length(self):
        # The zero-width space is a real code point counted by len(), even
        # though it renders invisibly -- it is never stripped or ignored.
        hero = "Hero" + "​" + "Title"
        business_name = "B" * 60
        full_title = hero + " | " + business_name
        assert len(full_title) > TITLE_MAX_LENGTH
        assert len(hero) <= TITLE_MAX_LENGTH
        result = compose_title(hero, business_name)
        assert result == hero
        assert "​" in result


# ---------------------------------------------------------------------------
# Length validators over already-composed values (D1/D2/D3)
# ---------------------------------------------------------------------------


class TestMetaLengthViolation:
    def test_within_bounds_returns_none(self):
        assert meta_length_violation("/", "I" * 100) is None

    def test_exact_min_boundary_passes(self):
        assert meta_length_violation("/", "I" * META_DESCRIPTION_MIN_LENGTH) is None

    def test_under_min_fails(self):
        violation = meta_length_violation("/", "I" * (META_DESCRIPTION_MIN_LENGTH - 1))
        assert violation == {
            "route": "/",
            "length": META_DESCRIPTION_MIN_LENGTH - 1,
            "limit": META_DESCRIPTION_MIN_LENGTH,
        }

    def test_over_max_source_is_not_a_violation(self):
        # The floor is checked on the SOURCE intro; there is no ceiling
        # check here because truncation guarantees output <= the max.
        assert meta_length_violation("/", "I" * 600) is None


class TestTitleLengthViolation:
    def test_within_bounds_returns_none(self):
        assert title_length_violation("/", "A Fine Title | Biz") is None

    def test_exact_max_boundary_passes(self):
        assert title_length_violation("/", "T" * TITLE_MAX_LENGTH) is None

    def test_over_max_fails(self):
        title = "T" * (TITLE_MAX_LENGTH + 1)
        violation = title_length_violation("/", title)
        assert violation == {
            "route": "/",
            "length": TITLE_MAX_LENGTH + 1,
            "limit": TITLE_MAX_LENGTH,
        }


class TestCanonicalLengthViolation:
    def test_within_bounds_returns_none(self):
        assert canonical_length_violation("/hotels/") is None

    def test_exact_max_boundary_passes(self):
        route = "/" + "a" * (CANONICAL_URL_MAX_LENGTH - 2) + "/"
        assert len(route) == CANONICAL_URL_MAX_LENGTH
        assert canonical_length_violation(route) is None

    def test_over_max_fails(self):
        route = "/" + "a" * (CANONICAL_URL_MAX_LENGTH - 1) + "/"
        assert len(route) == CANONICAL_URL_MAX_LENGTH + 1
        violation = canonical_length_violation(route)
        assert violation == {
            "route": route,
            "length": CANONICAL_URL_MAX_LENGTH + 1,
            "limit": CANONICAL_URL_MAX_LENGTH,
        }


# ---------------------------------------------------------------------------
# Title uniqueness (Decision D2.b)
# ---------------------------------------------------------------------------


class TestTitleCollisions:
    def test_no_collision_returns_empty(self):
        titles = {"/": "Home | Biz", "/hotels/": "Hotels | Biz"}
        assert title_collisions(titles) == ()

    def test_one_collision_reported(self):
        titles = {"/": "Same | Biz", "/hotels/": "Same | Biz"}
        assert title_collisions(titles) == (
            {"title": "Same | Biz", "routes": ("/", "/hotels/")},
        )

    def test_routes_within_a_collision_are_sorted(self):
        titles = {"/parks/": "Same | Biz", "/hotels/": "Same | Biz"}
        result = title_collisions(titles)
        assert result[0]["routes"] == ("/hotels/", "/parks/")

    def test_multiple_collisions_sorted_by_title(self):
        titles = {
            "/a/": "Zebra | Biz",
            "/b/": "Zebra | Biz",
            "/c/": "Apple | Biz",
            "/d/": "Apple | Biz",
        }
        result = title_collisions(titles)
        assert [entry["title"] for entry in result] == ["Apple | Biz", "Zebra | Biz"]

    def test_three_way_collision_reported_once(self):
        titles = {"/a/": "X | Biz", "/b/": "X | Biz", "/c/": "X | Biz"}
        result = title_collisions(titles)
        assert result == ({"title": "X | Biz", "routes": ("/a/", "/b/", "/c/")},)

    def test_single_entry_is_never_a_collision(self):
        assert title_collisions({"/": "Only | Biz"}) == ()

    def test_empty_input_returns_empty(self):
        assert title_collisions({}) == ()
