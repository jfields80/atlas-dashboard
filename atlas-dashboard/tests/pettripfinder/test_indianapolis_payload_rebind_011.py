# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-SAVED-PAYLOAD-REBIND-011 -- three more rules, five more URLs.

Every Google Places response Indianapolis will ever have is on disk and paid
for. This pass re-read the 96 that refused and asked what they refused OVER.

The restraint is the finding. 77 of those refusals returned a place at the right
postal code, with a routable property page, whose URL named the property -- and
it would be easy to read that as 77 recoverable rows. Most are different hotels
sharing a postal code: a Clarion Pointe offered for a Comfort Inn, a Red Roof
for a Comfort, a Courtyard for a Comfort Suites. Three deterministic patterns
survived that reading and they are worth five rows.

Half of this file is the three new rules. The other half is the six cases that
must keep refusing, and one regression that matters as much as any of them: the
009 measurement must not move, because widening a rule that changes an already
published number is how a record stops meaning anything.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.discovery import census_url_recovery as URC

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def key(name, unordered=True):
    return URC.presentation_key(name, state_code="IN", unordered=unordered)


@pytest.fixture(scope="module")
def rebind():
    return json.loads((PACKAGE_DIR / "indianapolis_in_payload_rebind_011.json")
                      .read_text(encoding="utf-8"))


class TestTheThreeNewRules:

    def test_an_operator_hotel_is_the_same_courtesy_as_by_operator(self):
        assert key("Holiday Inn Express Indianapolis - Southeast, an IHG Hotel") \
            == key("Holiday Inn Express Indianapolis Southeast")

    def test_it_is_only_the_exact_three_token_run(self):
        """"an inn hotel" is not an operator suffix."""
        assert "an" in key("An Inn Hotel Indianapolis").split()

    def test_inn_and_suites_is_a_designation_not_a_second_hotel(self):
        assert key("Comfort Inn & Suites Fishers - Indianapolis") == \
            key("Comfort Inn Fishers Indianapolis")
        assert key("Quality Inn & Suites Brownsburg - Indianapolis West") == \
            key("Quality Inn Brownsburg Indianapolis West")

    def test_the_same_words_in_a_different_order_are_one_name(self):
        assert key("Drury Plaza Hotel Indianapolis Carmel") == \
            key("Drury Plaza Hotel Carmel Indianapolis")

    def test_order_insensitivity_is_multiset_equality_not_overlap(self):
        """One extra word is still two different hotels."""
        assert key("Hampton Inn Indianapolis") != \
            key("Hampton Inn Indianapolis Airport")
        assert key("Comfort Inn North") != key("Comfort Inn North South")


class TestTheDangerousCaseStaysDangerous:
    """The whole reason "suites" is dropped only after "inn"."""

    def test_comfort_inn_is_not_comfort_suites(self):
        assert key("Comfort Inn South") != key("Comfort Suites South")

    def test_suites_survives_when_it_does_not_follow_inn(self):
        assert "suites" in key("Comfort Suites South").split()
        assert "suites" in key("Homewood Suites Carmel").split()

    def test_inn_survives_everywhere(self):
        assert "inn" in key("Comfort Inn & Suites Fishers").split()

    def test_two_brands_sharing_a_locality_never_merge(self):
        assert key("Quality Inn Noblesville") != key("Comfort Inn Noblesville")


class TestEveryProtectedTokenSurvives:

    @pytest.mark.parametrize("token", [
        "airport", "downtown", "north", "south", "east", "west", "northwest",
        "northeast", "southwest", "southeast", "plainfield", "carmel",
        "castleton", "fishers", "westfield", "greenwood", "noblesville",
        "brownsburg", "avon", "indianapolis",
    ])
    def test_the_token_survives(self, token):
        assert token in key("Some Hotel %s" % token).split()

    def test_airport_still_separates_two_courtyards(self):
        assert key("Courtyard by Marriott Indianapolis Airport Plainfield") != \
            key("Courtyard by Marriott Indianapolis Plainfield")

    def test_a_landmark_still_separates_two_best_westerns(self):
        assert key("Best Western Plus Indianapolis North at Broad Ripple") != \
            key("Best Western Plus Indianapolis North at Pyramids")


class TestTheWrongHotelsStillRefuse:
    """Measured: Places offered each of these for the row on the left."""

    @pytest.mark.parametrize("census,offered", [
        ("Cambria Hotel Westfield Indianapolis North",
         "Hampton Inn Westfield Indianapolis"),
        ("Hampton Inn & Suites Indianapolis Carmel",
         "Homewood Suites by Hilton Indianapolis Carmel"),
        ("Aloft", "Aloft by Marriott Indianapolis Downtown"),
        ("Comfort Inn Castleton", "Clarion Pointe Indianapolis Northeast"),
        ("Comfort Inn Indianapolis South", "Quality Inn Southport"),
    ])
    def test_it_does_not_bind(self, census, offered):
        assert key(census) != key(offered)


class TestTheReplayResult:

    def test_it_reviewed_every_saved_payload_and_spent_nothing(self, rebind):
        assert rebind["saved_payloads_reviewed"] == 143
        assert rebind["provider_calls"] == 0
        assert rebind["usd_spent"] == 0.0

    def test_it_re_examined_only_the_still_unbound(self, rebind):
        assert rebind["identities_re_examined"] == 96

    def test_five_new_binds(self, rebind):
        results = rebind["results"]
        assert results["already_bound_before"] == 47
        assert results["new_binds"] == 5
        assert results["total_bound_after"] == 52
        assert results["still_unbound"] == 91

    def test_no_protected_row_bound_and_no_collision(self, rebind):
        assert rebind["controls"]["all_held"] is True
        assert rebind["results"]["false_or_ambiguous_binds"] == []
        assert rebind["results"]["place_id_collisions"] == {}

    def test_every_new_bind_agrees_on_postal_and_is_a_property_page(self, rebind):
        for entry in rebind["new_binds"]:
            assert entry["census_postal"] == entry["places_postal"], entry
            assert entry["new_census_key"] == entry["new_places_key"], entry
            shape = MR.classify_url_shape(
                MR.normalize_source_url(entry["website_uri"]))
            assert shape in MR.ROUTABLE_SHAPES, entry
            assert entry["rule"] and entry["why_safe"]

    def test_the_declared_rules_disclaim_fuzzy_matching(self, rebind):
        assert "no edit distance" in rebind["new_rules"]["no_fuzzy_matching"]


class TestTheRoutingAndTheGap:

    def test_routing_moved_by_exactly_the_new_binds(self, rebind):
        routing = rebind["routing"]
        assert routing["routing_before"] == 161
        assert routing["routing_after"] == 166
        assert routing["url_less_before"] == 96
        assert routing["url_less_after"] == 91

    def test_the_acquisition_cohort_grew_from_46_to_51(self, rebind):
        impact = rebind["acquisition_impact"]
        assert impact["prepared_cohort_before"] == 46
        assert impact["newly_added_rows"] == 5
        assert impact["total_acquisition_cohort"] == 51

    def test_the_combined_plan_authorises_nothing(self, rebind):
        plan = rebind["combined_cost_plan"]
        assert plan["this_is_not_an_authorization"] is True
        assert plan["cohort_size"] == 51
        assert plan["firecrawl_credits"] == 20.0
        assert plan["dollar_billed_properties"] == 31
        assert plan["projection"]["worst_case_usd_minor"] == 651.0

    def test_fifty_is_still_out_of_reach(self, rebind):
        target = rebind["target_50"]
        assert target["current_promoted_pet_friendly"] == 24
        assert target["expected_from_prepared_cohort"] == 14
        assert target["expected_from_newly_rebound"] == 2
        assert target["expected_total"] == 40
        assert target["remaining_gap"] == 10

    def test_the_projection_is_labelled_an_estimate(self, rebind):
        assert "no row here is approved" in \
            rebind["target_50"]["this_is_an_estimate_not_an_approval"]


class TestTheEarlierMeasurementDidNotMove:
    """Widening a rule that changes an already published number is how a record
    stops meaning anything."""

    def test_009_still_reports_nine_to_thirteen(self):
        nine = json.loads(
            (PACKAGE_DIR / "indianapolis_in_name_normalization_009.json")
            .read_text(encoding="utf-8"))
        assert nine["totals"]["overall"] == {"attempted": 25, "old": 9, "new": 13}
        assert nine["totals"]["NAME_AND_POSTAL_CODE"] == {
            "attempted": 18, "old": 4, "new": 8}

    def test_the_rule_is_still_opt_in(self):
        row = {"identity_key": "comfort inn fishers indianapolis",
               "canonical_name": "Comfort Inn Fishers Indianapolis",
               "postal_code": "46037", "phone": "", "state": "IN"}
        observation = URC.Observation(
            provider=URC.GOOGLE_PLACES, source="t",
            name="Comfort Inn & Suites Fishers - Indianapolis", phone="",
            postal="46037",
            url="https://www.choicehotels.com/indiana/fishers/"
                "comfort-inn-hotels/in358", street="")
        assert URC.bind(row, [observation])[0] is None
        assert URC.bind(row, [observation], presentation_variants=True)[0] is not None
