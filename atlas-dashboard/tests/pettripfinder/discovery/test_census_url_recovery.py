"""PTF-ST-LOUIS-PAID-ACQUISITION-002 -- recovering a URL without buying one.

The value of this module is entirely in what it REFUSES. A missing URL leaves an
identity honestly unrouted; a wrong one sends a paid lane to another hotel's
page and publishes that building's pet policy under this hotel's name. So the
tests are mostly about non-matches.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.discovery import census_url_recovery as UR


def observation(**kwargs):
    base = {"provider": UR.GOOGLE_PLACES, "source": "s", "name": "",
            "phone": "", "postal": "", "url": "https://found/"}
    base.update(kwargs)
    return UR.Observation(**base)


def census_row(**kwargs):
    base = {"identity_key": "k", "canonical_name": "", "official_url": "",
            "phone": "", "postal_code": "", "city": "", "corridor": ""}
    base.update(kwargs)
    return base


class TestNormalisation:
    @pytest.mark.parametrize("value", ["(314) 731-3800", "+1 314 731 3800",
                                       "3147313800", "1-314-731-3800"])
    def test_one_telephone_line_compares_equal_however_it_is_written(self, value):
        assert UR.digits(value) == "3147313800"

    @pytest.mark.parametrize("value", ["", "12345", "731-3800", "abc"])
    def test_anything_that_is_not_a_full_number_is_not_a_key(self, value):
        assert UR.digits(value) == ""

    def test_names_compare_on_letters_and_digits_only(self):
        assert UR.normalise("The Ritz-Carlton, St. Louis") == \
            "the ritz carlton st louis"
        assert UR.normalise("Comfort Inn & Suites") == "comfort inn suites"

    def test_an_ampersand_and_the_word_and_do_not_normalise_together(self):
        # Deliberate. "Inn & Suites" and "Inn and Suites" are two spellings of
        # one hotel, and collapsing them here would be a genuine improvement --
        # but only for the NAME key, which never binds on its own. Widening a
        # weak key to catch more is the wrong direction: the postal code it is
        # paired with is what makes it safe, and a looser name paired with a
        # postal code that holds a dozen hotels starts guessing.
        assert UR.normalise("Inn & Suites") != UR.normalise("Inn and Suites")


class TestBinding:
    def test_a_matching_telephone_binds(self):
        row = census_row(phone="(314) 731-3800")
        found, binding = UR.bind(row, [observation(phone="3147313800")])
        assert binding == UR.BIND_PHONE and found.url == "https://found/"

    def test_an_empty_field_never_matches_an_empty_field(self):
        # The bug this pins: bucketing candidates by digits(phone) puts every
        # phoneless row in one bucket keyed by "" and marries fifty hotels to
        # one unrelated bed-and-breakfast.
        row = census_row(phone="", canonical_name="", postal_code="")
        found, binding = UR.bind(row, [observation(phone="", name="",
                                                   postal="")])
        assert found is None and binding == ""

    def test_a_name_alone_is_not_enough(self):
        row = census_row(canonical_name="Comfort Inn", postal_code="63146")
        found, _ = UR.bind(row, [observation(name="comfort inn", postal="")])
        assert found is None

    def test_a_postal_code_alone_is_not_enough(self):
        row = census_row(canonical_name="Comfort Inn", postal_code="63146")
        found, _ = UR.bind(row, [observation(name="", postal="63146")])
        assert found is None

    def test_a_name_and_a_postal_code_together_bind(self):
        row = census_row(canonical_name="Comfort Inn", postal_code="63146")
        found, binding = UR.bind(row, [observation(name="comfort inn",
                                                   postal="63146")])
        assert binding == UR.BIND_NAME_POSTAL and found is not None

    def test_the_same_name_in_a_different_postal_code_is_a_different_hotel(self):
        row = census_row(canonical_name="Comfort Inn", postal_code="63146")
        found, _ = UR.bind(row, [observation(name="comfort inn",
                                             postal="63101")])
        assert found is None

    def test_a_telephone_match_wins_over_a_name_match_elsewhere_in_the_list(self):
        row = census_row(canonical_name="Comfort Inn", postal_code="63146",
                         phone="3147313800")
        weaker = observation(name="comfort inn", postal="63146",
                             url="https://weaker/")
        stronger = observation(phone="3147313800", url="https://stronger/")
        found, binding = UR.bind(row, [weaker, stronger])
        assert binding == UR.BIND_PHONE and found.url == "https://stronger/"


class TestRecover:
    def test_a_row_that_already_has_a_url_is_left_alone(self):
        rows = [census_row(official_url="https://known/", phone="3147313800")]
        recovered, unknown = UR.recover(rows, [observation(phone="3147313800")])
        assert recovered == [] and unknown == []

    def test_a_recovery_carries_the_payload_it_came_from(self):
        rows = [census_row(phone="3147313800")]
        recovered, _ = UR.recover(rows, [observation(phone="3147313800",
                                                     source="cache/p1.json")])
        assert recovered[0]["evidence"]["source"] == "cache/p1.json"
        assert recovered[0]["binding"] == UR.BIND_PHONE

    def test_a_recovered_brand_index_is_reported_as_not_routable(self):
        rows = [census_row(phone="3147313800")]
        recovered, _ = UR.recover(rows, [observation(
            phone="3147313800",
            url="https://www.choicehotels.com/missouri/st-louis/quality-inn-hotels")])
        assert recovered[0]["routable"] is False

    def test_an_unrecovered_row_says_why_rather_than_vanishing(self):
        recovered, unknown = UR.recover([census_row()], [])
        assert recovered == [] and len(unknown) == 1
        assert unknown[0]["why"]


class TestCache:
    def test_places_and_openstreetmap_payloads_are_both_read(self, tmp_path):
        (tmp_path / "GOOGLE_PLACES").mkdir()
        (tmp_path / "GOOGLE_PLACES" / "page_1.json").write_text(json.dumps({
            "provider": "GOOGLE_PLACES",
            "payload": {"places": [
                {"id": "p1", "websiteUri": "https://a/",
                 "displayName": {"text": "A"},
                 "nationalPhoneNumber": "(314) 111-2222",
                 "addressComponents": [{"types": ["postal_code"],
                                        "longText": "63101"}]},
                {"id": "p2", "displayName": {"text": "No URL"}}]}}),
            encoding="utf-8")
        (tmp_path / "OSM").mkdir()
        (tmp_path / "OSM" / "page_1.json").write_text(json.dumps({
            "provider": "OPENSTREETMAP",
            "payload": {"elements": [
                {"type": "node", "id": 1,
                 "tags": {"name": "B", "website": "https://b/",
                          "phone": "+1 314 333 4444", "addr:postcode": "63102"}},
                {"type": "node", "id": 2, "tags": {"name": "No URL"}}]}}),
            encoding="utf-8")

        observations = UR.read_cache(tmp_path)
        assert len(observations) == 2           # the two without a URL are skipped
        by_url = {o.url: o for o in observations}
        assert by_url["https://a/"].phone == "3141112222"
        assert by_url["https://b/"].postal == "63102"
        assert by_url["https://b/"].provider == UR.OPENSTREETMAP

    def test_one_place_seen_in_many_cached_queries_is_counted_once(self, tmp_path):
        for name in ("q1", "q2"):
            (tmp_path / name).mkdir()
            (tmp_path / name / "page_1.json").write_text(json.dumps({
                "provider": "GOOGLE_PLACES",
                "payload": {"places": [{"id": "same", "websiteUri": "https://a/",
                                        "displayName": {"text": "A"}}]}}),
                encoding="utf-8")
        assert len(UR.read_cache(tmp_path)) == 1

    def test_an_unreadable_cache_file_does_not_stop_the_pass(self, tmp_path):
        (tmp_path / "page_1.json").write_text("{not json", encoding="utf-8")
        assert UR.read_cache(tmp_path) == []


# --------------------------------------------------------------------------- #
# PTF-LOUISVILLE-COVERAGE-EXPANSION-003 -- the third key, the URL's own text,
# and the rows whose URL nothing can fetch.
# --------------------------------------------------------------------------- #

def prior_census(tmp_path, *hotels):
    path = tmp_path / "prior_census.json"
    path.write_text(json.dumps({"count": len(hotels), "hotels": list(hotels)}),
                    encoding="utf-8")
    return path


class TestStreetKey:
    def test_two_spellings_of_one_address_produce_one_key(self):
        assert (UR.street_key("700 W Main St", "40202")
                == UR.street_key("700 West Main Street", "40202"))

    def test_the_postal_code_is_part_of_the_key(self):
        assert UR.street_key("700 W Main St", "40202") != \
            UR.street_key("700 W Main St", "40203")

    @pytest.mark.parametrize("address, postal", [
        ("700 W Main St", ""),          # a street with no postal code
        ("", "40202"),                  # a postal code with no street
        ("Airport Road", "40202"),      # a place, not an address
    ])
    def test_half_an_address_is_not_a_key(self, address, postal):
        assert UR.street_key(address, postal) == ""


class TestStreetBinding:
    def test_street_and_postal_bind_when_the_caller_allows_it(self):
        row = census_row(address="700 West Main Street", postal_code="40202")
        seen = observation(street="700 W Main St", postal="40202")
        found, binding = UR.bind(row, [seen], unambiguous_streets=frozenset(
            {UR.street_key("700 W Main St", "40202")}))
        assert binding == UR.BIND_STREET_POSTAL and found is seen

    def test_the_third_key_is_off_unless_the_caller_asks_for_it(self):
        row = census_row(address="700 West Main Street", postal_code="40202")
        found, _ = UR.bind(row, [observation(street="700 W Main St",
                                             postal="40202")])
        assert found is None

    def test_two_towers_at_one_address_bind_to_nothing(self):
        # The Galt House is Rivue Tower and the Galt House at one street
        # address. One URL bound to both identities means at least one of them
        # publishes another building's policy.
        rows = [census_row(identity_key="rivue tower", address="140 N Fourth St",
                           postal_code="40202"),
                census_row(identity_key="galt house", address="140 N Fourth St",
                           postal_code="40202")]
        keys = UR.unambiguous_street_keys(
            rows, [observation(street="140 N Fourth St", postal="40202")])
        assert keys == frozenset()

    def test_several_sightings_of_one_building_do_not_disqualify_its_key(self):
        rows = [census_row(address="102 W Main St", postal_code="40202")]
        keys = UR.unambiguous_street_keys(rows, [
            observation(street="102 W Main St", postal="40202",
                        url="https://one/"),
            observation(street="102 W Main St", postal="40202",
                        url="https://two/")])
        assert keys == frozenset({UR.street_key("102 W Main St", "40202")})


class TestUrlCorroboration:
    def test_a_url_that_names_the_property_is_accepted(self):
        ok, why = UR.url_names_the_property(
            "Aloft Louisville Downtown",
            "https://www.marriott.com/en-us/hotels/sdfld-aloft-louisville-downtown/")
        assert ok and "aloft" in why

    def test_a_url_for_another_hotel_on_the_same_brand_is_refused(self):
        # OpenStreetMap carries this exact tag on a Louisville Comfort Inn.
        ok, _ = UR.url_names_the_property(
            "Comfort Inn And Suites Clarksville",
            "https://www.choicehotels.com/kentucky/shepherdsville/sleep-inn-hotels")
        assert ok is False

    def test_a_bare_property_code_is_refused_because_it_cannot_be_read(self):
        ok, _ = UR.url_names_the_property("TownePlace Suites Louisville North",
                                          "https://www.marriott.com/sdfvn")
        assert ok is False

    def test_a_name_made_only_of_generic_words_corroborates_nothing(self):
        ok, why = UR.url_names_the_property("The Hotel", "https://thehotel.com/")
        assert ok is False and "distinctive" in why


class TestFallThrough:
    def test_a_rejected_url_does_not_consume_the_row(self):
        """Louisville: a phone binds to a bulk-edited OSM tag for another
        city's hotel, and the same building's street binds to its real page."""
        row = census_row(canonical_name="Comfort Suites East",
                         phone="5022666509", address="1877 S Hurstbourne Pkwy",
                         postal_code="40220")
        wrong = observation(phone="5022666509", url="https://elsewhere.com/x")
        right = observation(street="1877 S Hurstbourne Pkwy", postal="40220",
                            url="https://www.choicehotels.com/kentucky/"
                                "louisville/comfort-suites-hotels/ky999")
        rejected = []
        found, binding = UR.bind(
            row, [wrong, right],
            unambiguous_streets=frozenset({UR.street_key(
                "1877 S Hurstbourne Pkwy", "40220")}),
            acceptable=lambda o: UR.url_names_the_property(
                row["canonical_name"], o.url),
            rejected=rejected)
        assert binding == UR.BIND_STREET_POSTAL and found is right
        assert [r["binding"] for r in rejected] == [UR.BIND_PHONE]

    def test_every_refusal_is_reported_beside_the_row_it_was_refused_for(self):
        rows = [census_row(canonical_name="Comfort Inn", phone="5029152029")]
        _, unknown = UR.recover(rows, [observation(
            phone="5029152029",
            url="https://www.choicehotels.com/kentucky/shepherdsville/"
                "sleep-inn-hotels")], corroborate=True)
        assert unknown[0]["refused"][0]["binding"] == UR.BIND_PHONE
        assert unknown[0]["refused_url"].endswith("sleep-inn-hotels")


class TestUnroutableRows:
    def test_a_row_whose_url_no_lane_can_fetch_is_reachable_by_a_proposal(self):
        rows = [census_row(canonical_name="The Seelbach Hilton Hotel",
                           phone="5025853200",
                           official_url="https://seelbachhilton.com")]
        seen = observation(
            phone="5025853200",
            url="https://www.hilton.com/en/hotels/sdfshhf-the-seelbach-hilton/")
        recovered, _ = UR.recover(rows, [seen], corroborate=True,
                                  include_unroutable=True)
        assert recovered[0]["displaces_unroutable_census_url"] is True
        assert recovered[0]["census_url_shape"] == "BRAND_INDEX"

    def test_a_row_whose_url_a_lane_can_fetch_is_never_touched(self):
        rows = [census_row(
            phone="5025853200",
            official_url="https://www.hilton.com/en/hotels/sdfshhf-seelbach/")]
        recovered, unknown = UR.recover(
            rows, [observation(phone="5025853200", url="https://other/page/x")],
            include_unroutable=True)
        assert recovered == [] and unknown == []

    def test_proposing_the_url_the_census_already_holds_is_not_a_recovery(self):
        url = ("https://www.choicehotels.com/kentucky/shepherdsville/"
               "sleep-inn-hotels")
        rows = [census_row(canonical_name="Sleep Inn Louisville",
                           phone="5029152029", official_url=url)]
        recovered, unknown = UR.recover(rows, [observation(phone="5029152029",
                                                           url=url)],
                                        corroborate=True,
                                        include_unroutable=True)
        assert recovered == []
        assert "already holds" in unknown[0]["refused"][0]["why"]


class TestPriorBuild:
    def test_an_earlier_census_is_read_as_sightings(self, tmp_path):
        path = prior_census(tmp_path, {
            "identity_key": "21c museum hotel louisville",
            "canonical_name": "21c Museum Hotel Louisville",
            "phone": "502-217-6300", "postal_code": "40202",
            "address": "700 W Main St",
            "official_url": "https://www.21cmuseumhotels.com/louisville/"})
        observations = UR.read_prior_census(path)
        assert len(observations) == 1
        assert observations[0].provider == UR.PRIOR_BUILD
        assert observations[0].phone == "5022176300"
        assert observations[0].street == UR.street_key("700 W Main St", "40202")

    def test_an_earlier_row_with_no_url_carries_nothing_forward(self, tmp_path):
        path = prior_census(tmp_path, {"identity_key": "k",
                                       "canonical_name": "K", "phone": "",
                                       "postal_code": "40202",
                                       "address": "1 A St",
                                       "official_url": ""})
        assert UR.read_prior_census(path) == []

    def test_artifact_urls_are_only_used_for_prior_rows_that_lack_one(self, tmp_path):
        path = prior_census(tmp_path,
                            {"identity_key": "has", "canonical_name": "Has",
                             "phone": "", "postal_code": "40202",
                             "address": "1 A St",
                             "official_url": "https://census/"},
                            {"identity_key": "lacks", "canonical_name": "Lacks",
                             "phone": "", "postal_code": "40203",
                             "address": "2 B St", "official_url": ""})
        report = tmp_path / "report.json"
        report.write_text(json.dumps({"rows": [
            {"identity_key": "has", "policy_url": "https://deeper/"},
            {"identity_key": "lacks", "final_url": "https://found/"},
            {"identity_key": "unknown-identity", "url": "https://stray/"}]}),
            encoding="utf-8")

        observations, coverage = UR.read_prior_artifacts(path, [report])
        assert [o.url for o in observations] == ["https://found/"]
        assert coverage["urls_for_prior_rows_whose_census_url_is_empty"] == 1
        assert coverage["keys_absent_from_the_prior_census"] == ["unknown-identity"]


class TestTheRoutingShardShape:
    """PTF-INDIANAPOLIS-HARDENED-RECENSUS-002. The identity routing shard keeps
    the key in ``hotel_ref.identity_key`` and the URL in
    ``official_property_url`` one level up. A walk that pairs a URL only with
    a key on the same node read every market's canonical routing authority and
    bound nothing from it."""

    def test_a_url_binds_to_the_key_of_its_enclosing_hotel_ref(self, tmp_path):
        shard = tmp_path / "identity_routing.json"
        shard.write_text(json.dumps({"routes": [{
            "routing_id": "route-x",
            "hotel_ref": {"identity_key": "candlewood suites medical district",
                          "market_id": "x"},
            "official_property_url": "https://www.ihg.com/candlewood/indwp",
            "status": "VERIFIED",
        }]}), encoding="utf-8")
        found = UR.urls_in_artifacts([shard])
        assert found == {"candlewood suites medical district": [
            {"url": "https://www.ihg.com/candlewood/indwp",
             "source": shard.as_posix(), "field": "official_property_url"}]}

    def test_a_nested_node_inherits_the_nearest_enclosing_key(self, tmp_path):
        report = tmp_path / "report.json"
        report.write_text(json.dumps({"rows": [
            {"identity_key": "outer", "evidence": {"final_url": "https://inner/"}},
            {"identity_key": "other", "url": "https://other/"}]}), encoding="utf-8")
        found = UR.urls_in_artifacts([report])
        assert found["outer"][0]["url"] == "https://inner/"
        assert found["other"][0]["url"] == "https://other/"

    def test_a_url_with_no_key_anywhere_above_it_is_not_invented(self, tmp_path):
        report = tmp_path / "report.json"
        report.write_text(json.dumps({"summary": {"url": "https://nobody/"}}),
                          encoding="utf-8")
        assert UR.urls_in_artifacts([report]) == {}
