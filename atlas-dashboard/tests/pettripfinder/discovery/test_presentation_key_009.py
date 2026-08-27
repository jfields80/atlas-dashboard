# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-NAME-NORMALIZATION-009 -- the three transformations, and the wall.

25 paid Google Places lookups showed that the NAME_AND_POSTAL_CODE rule was
refusing hotels it had actually found, because it compared PRESENTATION and
called it identity: "Candlewood Suites Indianapolis Northwest BY IHG" is the
same building as "Candlewood Suites Indianapolis Northwest".

``presentation_key`` closes exactly three of those gaps and nothing else. Half
of this file proves the transformations work; the other half proves the wall
they stop at, which is the half that matters. A rule that binds a Hampton Inn
to a Homewood Suites does not cost a request -- it publishes one hotel's pet
policy under another hotel's name.
"""
from __future__ import annotations

import pytest

from scripts.pettripfinder.discovery import census_url_recovery as URC


def key(name, state="IN"):
    return URC.presentation_key(name, state_code=state)


class TestOperatorPresentationTokens:
    """"by <operator>" says who runs the chain, never which building."""

    def test_by_ihg_is_dropped(self):
        assert key("Candlewood Suites Indianapolis Northwest by IHG") == \
            key("Candlewood Suites Indianapolis Northwest")

    def test_by_marriott_is_dropped(self):
        assert key("Fairfield by Marriott Inn & Suites Indianapolis Plainfield") == \
            key("Fairfield Inn & Suites Indianapolis Plainfield")

    def test_by_hilton_is_dropped(self):
        assert key("Homewood Suites by Hilton Indianapolis Carmel") == \
            key("Homewood Suites Indianapolis Carmel")

    def test_by_wyndham_and_by_radisson_are_dropped(self):
        assert key("AmericInn by Wyndham Fishers") == key("AmericInn Fishers")
        assert key("Country Inn & Suites by Radisson, Indianapolis") == \
            key("Country Inn & Suites Indianapolis")

    def test_a_two_word_operator_is_dropped_whole(self):
        assert key("Executive Residency by Best Western Indianapolis") == \
            key("Executive Residency Indianapolis")

    def test_by_is_kept_when_what_follows_is_a_place_not_an_operator(self):
        """"by the airport" is where the hotel is. Dropping any "by X" would
        delete it, which is why the operator list is closed."""
        assert "by" in key("Holiday Inn by the Airport").split()
        assert "airport" in key("Holiday Inn by the Airport").split()

    def test_an_unknown_operator_is_not_invented(self):
        assert "by" in key("Some Inn by Nobody Indianapolis").split()


class TestAmpersandAndPunctuation:

    def test_ampersand_and_the_word_and_are_the_same_name(self):
        assert key("Comfort Inn & Suites North") == \
            key("Comfort Inn and Suites North")

    def test_hyphens_slashes_and_dashes_collapse(self):
        assert key("Hampton Inn Indianapolis-SW/Plainfield") == \
            key("Hampton Inn Indianapolis SW Plainfield")

    def test_a_trailing_dash_on_a_chain_word_collapses(self):
        assert key("Extended Stay America Suites- Indianapolis - Castleton") == \
            key("Extended Stay America Indianapolis Castleton")

    def test_commas_and_case_do_not_matter(self):
        assert key("MOTEL 6 Indianapolis, Airport") == key("motel 6 indianapolis airport")

    def test_and_carries_no_identity_and_is_dropped(self):
        """It is folded away because "&" already is, not kept for looks."""
        assert key("Bed and Breakfast") == "bed breakfast"

    def test_a_short_name_is_never_emptied_by_the_fold(self):
        """The guard exists so a two-token name cannot be reduced to one."""
        assert key("Rest and") == "rest and"


class TestTheBareStateCode:

    def test_a_bare_state_code_is_dropped(self):
        assert key("Motel 6 Indianapolis, IN - Airport") == \
            key("Motel 6 Indianapolis Airport")

    def test_inn_is_not_a_state_code(self):
        """Three letters, and the most common word in this corpus."""
        assert "inn" in key("Comfort Inn Indianapolis").split()

    def test_a_different_state_code_is_not_dropped(self):
        assert "in" in key("Motel 6 Indianapolis IN Airport", state="OH").split()


class TestChainRePresentation:

    def test_extended_stay_america_suites_is_the_same_chain(self):
        assert key("Extended Stay America Suites Indianapolis Castleton") == \
            key("Extended Stay America Indianapolis Castleton")

    def test_it_only_applies_at_the_start_of_the_name(self):
        """A table of whole-chain renames, not a floating word swap."""
        assert key("Somewhere Extended Stay America Suites") != \
            key("Somewhere Extended Stay America")


class TestWhatMustNeverBeNormalised:
    """Every one of these distinguishes two real Indianapolis buildings."""

    @pytest.mark.parametrize("token", [
        "airport", "downtown", "north", "south", "east", "west",
        "northwest", "northeast", "southwest", "southeast",
        "plainfield", "carmel", "castleton", "fishers", "westfield",
        "greenwood", "noblesville", "brownsburg", "indianapolis",
    ])
    def test_the_token_survives(self, token):
        assert token in key("Some Hotel %s" % token).split()

    def test_airport_separates_two_real_courtyards(self):
        assert key("Courtyard by Marriott Indianapolis Airport Plainfield") != \
            key("Courtyard by Marriott Indianapolis Plainfield")

    def test_inn_and_suites_are_two_different_brands(self):
        assert key("Comfort Inn South") != key("Comfort Suites South")

    def test_a_compass_word_still_separates_hotels(self):
        assert key("Baymont Indianapolis East") != key("Baymont Indianapolis West")

    def test_a_landmark_still_separates_two_best_westerns(self):
        """Same brand, same city, same compass word, different building."""
        assert key("Best Western Plus Indianapolis North at Broad Ripple") != \
            key("Best Western Plus Indianapolis North at Pyramids")


class TestTheWrongHotelsPlacesActuallyOffered:
    """Measured, not hypothetical: Places returned each of these."""

    def test_a_cambria_is_not_a_hampton(self):
        assert key("Cambria Hotel Westfield Indianapolis North") != \
            key("Hampton Inn Westfield Indianapolis")

    def test_a_hampton_is_not_a_homewood_at_one_address(self):
        """The dual-brand confusion the ledger doctrine is written against."""
        assert key("Hampton Inn & Suites Indianapolis Carmel") != \
            key("Homewood Suites by Hilton Indianapolis Carmel")

    def test_a_bare_brand_word_is_not_a_building(self):
        """Places returned the real Aloft Indianapolis Downtown for "Aloft"."""
        assert key("Aloft") != key("Aloft by Marriott Indianapolis Downtown")

    def test_a_baymont_rename_still_does_not_bind_on_the_name_alone(self):
        assert key("Baymont Inn & Suites Indianapolis East") != \
            key("Baymont by Wyndham Indianapolis East")


class TestThereIsNoFuzzyMatching:

    def test_a_missing_locality_is_still_a_different_name(self):
        assert key("Clarion Inn & Suites Northwest") != \
            key("Clarion Inn & Suites Indianapolis Northwest")

    def test_one_extra_word_is_still_a_different_name(self):
        """The "Inn & Suites" pair that used to sit here became a deliberate
        rule in PTF-INDIANAPOLIS-PLACES-SAVED-PAYLOAD-REBIND-011, derived from
        three saved payloads where the brand's own URL confirms one hotel. The
        invariant it demonstrates is unchanged, so it is shown on a pair no
        rule touches."""
        assert key("Comfort Inn North") != key("Comfort Inn North Airport")
        assert key("Hampton Inn Carmel") != key("Hampton Inn Carmel West")

    def test_the_key_is_stable_and_idempotent(self):
        once = key("Fairfield by Marriott Inn & Suites Indianapolis, IN")
        assert key(once) == once

    def test_an_empty_name_stays_empty(self):
        assert key("") == "" and key("   ") == ""


class TestTheRuleIsOptIn:
    """Every market that recovered its URLs under the old rule recovers exactly
    the same ones today."""

    def _row(self):
        return {"identity_key": "candlewood suites indianapolis northwest",
                "canonical_name": "Candlewood Suites Indianapolis Northwest",
                "postal_code": "46278", "phone": "", "state": "IN"}

    def _observation(self):
        return URC.Observation(
            provider=URC.GOOGLE_PLACES, source="test",
            name="Candlewood Suites Indianapolis Northwest by IHG", phone="",
            postal="46278",
            url="https://www.ihg.com/candlewood/hotels/us/en/indianapolis/"
                "indnw/hoteldetail", street="")

    def test_off_by_default_the_operator_token_still_blocks_the_bind(self):
        found, binding = URC.bind(self._row(), [self._observation()])
        assert found is None and binding == ""

    def test_on_request_it_binds(self):
        found, binding = URC.bind(self._row(), [self._observation()],
                                  presentation_variants=True)
        assert found is not None
        assert binding == URC.BIND_NAME_POSTAL

    def test_the_phone_key_is_untouched_either_way(self):
        row = dict(self._row(), phone="3175551212")
        observation = URC.Observation(
            provider=URC.GOOGLE_PLACES, source="test", name="Totally Different",
            phone="(317) 555-1212", postal="46278",
            url="https://www.ihg.com/candlewood/hotels/us/en/indianapolis/"
                "indnw/hoteldetail", street="")
        for variants in (False, True):
            _found, binding = URC.bind(row, [observation],
                                       presentation_variants=variants)
            assert binding == URC.BIND_PHONE
