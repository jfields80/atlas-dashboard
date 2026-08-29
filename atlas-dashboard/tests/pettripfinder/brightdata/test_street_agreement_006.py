# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-OFFICIAL-URL-RECOVERY-006 -- one address written two ways.

Two Indianapolis properties were refused by the identity gate while being,
demonstrably, the right hotel. Both refusals cost a paid fetch that answered
nothing, and both were a spelling difference rather than a disagreement:

    page   "7226 Woodland Drive at 71st Street"   census "7226 Woodland Drive"
    page   "2245 East Perry Road"                 census "2245 Perry Road"

``streets_agree`` reconciles exactly those two shapes. The tests that matter
most here are the negative ones: this is an identity gate, and the cost of
widening it too far is publishing another building's pet policy under this
hotel's name. So a different house number, a different street and two
DIFFERENT directionals all still disagree.
"""
from __future__ import annotations

import pytest

from scripts.pettripfinder.brightdata import marriott_surface
from scripts.pettripfinder.brightdata.policy_surface import streets_agree


class TestTheTwoShapesThatCostAFetch:

    def test_a_cross_street_after_a_complete_address_is_the_same_building(self):
        agree, why = streets_agree("7226 Woodland Drive at 71st Street",
                                   "7226 Woodland Drive")
        assert agree
        assert "cross street" in why

    def test_it_reads_the_same_in_either_direction(self):
        assert streets_agree("7226 Woodland Drive",
                             "7226 Woodland Drive at 71st Street")[0]

    def test_a_directional_stated_on_one_side_only_is_the_same_road(self):
        agree, why = streets_agree("2245 East Perry Road", "2245 Perry Road")
        assert agree
        assert "one side" in why

    def test_that_one_reads_the_same_in_either_direction(self):
        assert streets_agree("2245 Perry Road", "2245 East Perry Road")[0]

    def test_an_identical_address_still_agrees_exactly(self):
        agree, why = streets_agree("601 West Washington Street",
                                   "601 West Washington Street")
        assert agree and why == "exact"

    def test_the_existing_abbreviation_folding_is_untouched(self):
        assert streets_agree("2245 E Perry Rd", "2245 East Perry Road")[0]


class TestWhatMustStillDisagree:
    """The half of this change that protects coverage."""

    def test_a_different_house_number_is_still_a_different_building(self):
        """Residence Inn Airport: the page says 5224 and the census says 5228.
        Which one is wrong is a founder's question about the census, and
        normalisation must not answer it."""
        assert not streets_agree("5224 West Southern Avenue",
                                 "5228 West Southern Avenue")[0]

    def test_two_different_directionals_are_two_different_roads(self):
        """The reason this is not written as 'drop all directionals'."""
        assert not streets_agree("2245 East Perry Road",
                                 "2245 West Perry Road")[0]
        assert not streets_agree("100 N Meridian Street",
                                 "100 S Meridian Street")[0]

    def test_a_different_street_name_never_agrees(self):
        assert not streets_agree("7226 Woodland Drive at 71st Street",
                                 "7226 Oak Drive")[0]

    def test_a_cross_street_word_cannot_join_two_different_numbers(self):
        assert not streets_agree("7226 Woodland Drive at 71st Street",
                                 "7228 Woodland Drive")[0]

    def test_a_longer_address_that_is_not_a_cross_street_does_not_agree(self):
        """Only a cross-street connective may be dropped, not any suffix."""
        assert not streets_agree("100 Main Street Suite 400", "100 Main Street")[0]

    def test_a_road_with_no_house_number_is_no_signal_not_a_match(self):
        agree, why = streets_agree("North Brookfield Road", "North Brookfield Road")
        assert agree is False and why == ""

    def test_an_empty_side_is_no_signal(self):
        assert streets_agree("", "7226 Woodland Drive") == (False, "")
        assert streets_agree("7226 Woodland Drive", "") == (False, "")


class TestBothLanesShareTheOneRule:
    """A hotel must not be the right building on one lane and the wrong one on
    another, so the Marriott surface and the generic surface ask the same
    function."""

    def test_the_marriott_surface_uses_the_shared_helper(self):
        assert marriott_surface.policy_surface.streets_agree is streets_agree

    @pytest.mark.parametrize("page,census", [
        ("7226 Woodland Drive at 71st Street", "7226 Woodland Drive"),
        ("2245 East Perry Road", "2245 Perry Road"),
    ])
    def test_the_two_real_cases_agree_on_the_shared_rule(self, page, census):
        assert streets_agree(page, census)[0]
