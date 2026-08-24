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
