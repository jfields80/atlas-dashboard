"""The locator, against sixteen real pages.

The claim under test is narrow and checkable: for every page a brand actually
served us, the located block contains that hotel's real pet terms, and does not
run on into the next section.
"""

from __future__ import annotations

import pytest

from services.research_workers.capture_automation.contracts import (
    CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_MEDIUM, DomSnapshot,
)
from services.research_workers.capture_automation.policy_locator import (
    BLOCK_TERMINATORS, MAX_EXCERPT_CHARS, extract_block, find_anchor_hits,
    locate_policy, score_block,
)

from .conftest import fixture_names, snapshot_for


class TestEveryRealPageIsLocated:
    @pytest.mark.parametrize("name", fixture_names())
    def test_policy_is_found(self, name):
        loc = locate_policy(snapshot_for(name))
        assert loc is not None, "no policy located in %s" % name
        assert loc.text_excerpt.strip()

    @pytest.mark.parametrize("name", fixture_names())
    def test_excerpt_is_verbatim_from_the_page(self, name):
        dom = snapshot_for(name)
        loc = locate_policy(dom)
        assert loc.text_excerpt in dom.text

    @pytest.mark.parametrize("name", fixture_names())
    def test_excerpt_is_bounded(self, name):
        """A block that swallows the rest of the page is not a located block."""
        loc = locate_policy(snapshot_for(name))
        assert len(loc.text_excerpt) <= MAX_EXCERPT_CHARS

    @pytest.mark.parametrize("name", fixture_names())
    def test_offsets_agree_with_the_excerpt(self, name):
        dom = snapshot_for(name)
        loc = locate_policy(dom)
        assert dom.text[loc.text_start:loc.text_end].strip() == loc.text_excerpt


class TestTheRightNumbersAreInTheBlock:
    """Verbatim expectations, one per hotel, taken from the real captures."""

    @pytest.mark.parametrize("name,needles", [
        ("marriott-cmham.json", ("Non-Refundable Pet Fee Per Stay: $75.00",
                                 "Maximum Number of Pets in Room: 2")),
        ("marriott-cmhaw.json", ("Maximum Pet Weight: 40.0lbs",
                                 "$50 pet fee/per pet 40lbs or over")),
        ("marriott-cmhsi.json", ("Non-Refundable Pet Fee Per Stay: $75.00",
                                 "Maximum Pet Weight: 50.0lbs")),
        ("marriott-cmhsu.json", ("$45 Non-Refundable Pet Fee Every 3 Nights",)),
        ("marriott-cmhrn.json", ("Non-Refundable Pet Fee Per Stay: $100.00",)),
        # Hilton's compressed tier notation carries the whole policy and
        # contains no anchor phrase of its own.
        ("hilton-cmhaphx.json", ("$75(1-4n)$125(5+n)2pet Max dog/cat only",)),
        ("hilton-cmhncht.json", ("1-4 night stay $50; 5+ night stay $75",)),
        ("hilton-cmhcsht.json", ("Yes. $75.00 Non-refundable Fee", "50 lbs")),
        ("hilton-cmhchhf.json", ("Non-refundable fee: $100.00", "Max weight: 75 lbs")),
    ])
    def test_block_carries_the_real_terms(self, name, needles):
        loc = locate_policy(snapshot_for(name))
        for needle in needles:
            assert needle in loc.text_excerpt, (
                "%s: %r missing from located block %r"
                % (name, needle, loc.text_excerpt))

    def test_tiered_hilton_block_is_not_flattened_to_one_number(self):
        """The whole reason PTF-FEES exists: both tier amounts must survive."""
        loc = locate_policy(snapshot_for("hilton-cmhaphx.json"))
        assert "$75" in loc.text_excerpt and "$125" in loc.text_excerpt


class TestBlockBoundaries:
    def test_stops_at_a_terminator(self):
        text = "Pet Policy\nPets Welcome\n$50 fee\nParking\nDaily: $15.00"
        block, start, end = extract_block(text, text.index("Pet Policy"))
        assert "Parking" not in block
        assert "$15.00" not in block

    def test_marriott_block_does_not_contain_parking(self):
        loc = locate_policy(snapshot_for("marriott-cmham.json"))
        assert "Parking" not in loc.text_excerpt

    def test_hilton_block_does_not_contain_all_policies(self):
        loc = locate_policy(snapshot_for("hilton-cmhncht.json"))
        assert "All Policies" not in loc.text_excerpt

    def test_every_terminator_is_honoured(self):
        for term in BLOCK_TERMINATORS:
            text = "Pet Policy\nPets Welcome\n$50 fee\n%s\nlater content" % term
            block, _s, _e = extract_block(text, 0)
            assert term not in block, term


class TestRefusesNonPolicies:
    def test_bare_nav_word_is_not_a_policy(self):
        """'Pets' in a navigation list, with nothing corroborating it, must not
        become evidence."""
        dom = DomSnapshot(final_url="https://example.com/x",
                          text="Home\nRooms\nPets\nContact\nAbout us\n")
        assert locate_policy(dom) is None

    def test_empty_page_locates_nothing(self):
        assert locate_policy(DomSnapshot(final_url="https://example.com/x",
                                         text="")) is None

    def test_page_without_any_anchor_locates_nothing(self):
        dom = DomSnapshot(final_url="https://example.com/x",
                          text="Parking is complimentary. Breakfast is served daily.")
        assert locate_policy(dom) is None


class TestScoringAndConfidence:
    def test_strong_anchor_outscores_weak(self):
        strong = score_block("Pet Policy stuff", ["Pet Policy"])
        weak = score_block("Pets stuff", ["Pets"])
        assert strong > weak

    def test_money_and_weight_raise_the_score(self):
        bare = score_block("Pets Welcome", ["Pets Welcome"])
        rich = score_block("Pets Welcome $50 fee, 40 lbs max, 2 pets",
                           ["Pets Welcome"])
        assert rich > bare

    @pytest.mark.parametrize("name", fixture_names())
    def test_every_real_page_is_at_least_medium_confidence(self, name):
        loc = locate_policy(snapshot_for(name))
        assert loc.confidence in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM)

    def test_marriott_pages_are_high_confidence(self):
        for name in fixture_names("marriott"):
            assert locate_policy(snapshot_for(name)).confidence == CONFIDENCE_HIGH


class TestAnchorScan:
    def test_finds_every_occurrence_in_order(self):
        text = "Pets here. Pet Policy there. Pets again."
        hits = find_anchor_hits(text)
        assert hits == sorted(hits, key=lambda h: h[1])
        assert any(a == "Pet Policy" for a, _ in hits)

    def test_extra_anchors_are_honoured(self):
        text = "Some page. Snorkel Policy: $10."
        assert not find_anchor_hits(text)
        assert find_anchor_hits(text, ("Snorkel Policy",))
