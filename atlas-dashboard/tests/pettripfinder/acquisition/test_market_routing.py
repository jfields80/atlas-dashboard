"""PTF-ST-LOUIS-MARKET-001 -- routing a whole census in one pass.

The load-bearing claim is the URL SHAPE. A market that counts brand-index and
third-party URLs as "routed" reports 97% routing coverage and then acquires
nothing, because a locator page is property-specific for nobody and an OTA
listing is not first-party at all.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.acquisition import market_routing as MR


class TestNormalisation:
    def test_referrer_tracking_is_dropped_and_the_hotel_code_is_not(self):
        url = ("https://www.ihg.com/redirect?path=hd&localeCode=en&brandCode=EX"
               "&regionCode=US&hotelCode=ALNAT&cm_mmc=GoogleMaps-_-EX-_-US")
        out = MR.normalize_source_url(url)
        assert "hotelCode=ALNAT" in out
        assert "cm_mmc" not in out

    def test_two_sightings_of_one_property_normalise_to_one_url(self):
        a = "https://x.com/p?id=7&utm_source=google&gclid=abc"
        b = "https://x.com/p?id=7&utm_campaign=maps"
        assert MR.normalize_source_url(a) == MR.normalize_source_url(b)

    def test_an_empty_url_normalises_to_empty(self):
        assert MR.normalize_source_url("") == ""
        assert MR.normalize_source_url(None) == ""


class TestShape:
    @pytest.mark.parametrize("url,expected", [
        ("", MR.NO_URL),
        ("https://www.booking.com/hotel/us/x.html", MR.THIRD_PARTY),
        ("https://www.facebook.com/somehotel", MR.THIRD_PARTY),
        ("https://www.ihg.com/redirect?hotelCode=ALNAT", MR.BRAND_REDIRECT),
        ("https://www.marriott.com/en-us/hotels/stlaw-ac-hotel/overview/",
         MR.PROPERTY_PAGE),
        ("https://www.choicehotels.com/", MR.BRAND_INDEX),
        ("https://www.choicehotels.com/hotels", MR.BRAND_INDEX),
        ("https://www.hilton.com/en/hotels/", MR.BRAND_INDEX),
        ("https://someindependent.com/rooms", MR.PROPERTY_PAGE),
    ])
    def test_shapes(self, url, expected):
        assert MR.classify_url_shape(url) == expected

    def test_a_brand_index_is_never_routable(self):
        assert MR.BRAND_INDEX not in MR.ROUTABLE_SHAPES
        assert MR.THIRD_PARTY not in MR.ROUTABLE_SHAPES
        assert MR.NO_URL not in MR.ROUTABLE_SHAPES


class TestCategoryIndex:
    """A path ENDING in a category of hotels lists many; it names none.

    PTF-ST-LOUIS-PAID-ACQUISITION-002 found this the way it is always found: a
    Choice city-search URL was carried by THREE St. Louis census identities --
    two Comfort Inns and a Sleep Inn -- and being shaped like a property page,
    it was routed, fetched, passed the capture's identity gate on city and
    brand family alone, and returned POLICY_NOT_FOUND. That is a claim about a
    hotel made from a page that is not that hotel's.
    """

    def test_a_city_and_brand_listing_is_an_index(self):
        assert MR.classify_url_shape(
            "https://www.choicehotels.com/missouri/saint-louis/quality-inn-hotels"
        ) == MR.BRAND_INDEX

    def test_the_same_path_with_a_property_code_after_it_is_a_property_page(self):
        assert MR.classify_url_shape(
            "https://www.choicehotels.com/illinois/alton/comfort-inn-hotels/il008"
        ) == MR.PROPERTY_PAGE

    @pytest.mark.parametrize("tail", ["hotels", "motels", "inns", "resorts",
                                      "properties", "econo-lodge-hotels"])
    def test_every_category_word_is_an_index_in_the_last_segment(self, tail):
        assert MR.classify_url_shape(
            "https://www.choicehotels.com/illinois/alton/%s" % tail
        ) == MR.BRAND_INDEX

    def test_a_trailing_slash_does_not_hide_the_category_segment(self):
        assert MR.classify_url_shape(
            "https://www.choicehotels.com/missouri/saint-louis/quality-inn-hotels/"
        ) == MR.BRAND_INDEX

    def test_a_property_slug_that_merely_contains_a_category_word_survives(self):
        # "hotels" inside a segment is not "hotels" as the segment's category
        # suffix -- refusing these would delete real property pages.
        assert MR.classify_url_shape(
            "https://www.marriott.com/en-us/hotels/stlaw-ac-hotel/overview/"
        ) == MR.PROPERTY_PAGE
        assert MR.classify_url_shape(
            "https://someindependent.com/hotelsuites"
        ) == MR.PROPERTY_PAGE


class TestSharedUrls:
    def test_two_identities_on_one_routed_url_are_reported(self):
        entries = [
            {"identity_key": "a", "source_url": "https://x/1",
             "routing_state": MR.ROUTED},
            {"identity_key": "b", "source_url": "https://x/1",
             "routing_state": MR.ROUTED},
            {"identity_key": "c", "source_url": "https://x/2",
             "routing_state": MR.ROUTED},
        ]
        shared = MR.urls_claimed_more_than_once(entries)
        assert list(shared) == ["https://x/1"]
        assert shared["https://x/1"] == ["a", "b"]

    def test_an_unrouted_row_cannot_raise_a_false_collision(self):
        entries = [
            {"identity_key": "a", "source_url": "https://x/1",
             "routing_state": MR.ROUTED},
            {"identity_key": "b", "source_url": "https://x/1",
             "routing_state": MR.ROUTE_BRAND_EXCLUDED},
        ]
        assert MR.urls_claimed_more_than_once(entries) == {}


class TestRouting:
    def _row(self, url):
        return {"identity_key": "k", "canonical_name": "K", "corridor": "c",
                "official_url": url}

    def test_no_url_asks_for_an_official_url(self):
        entry = MR.route_row(self._row(""))
        assert entry["routing_state"] == MR.ROUTE_NEEDS_OFFICIAL_URL

    def test_an_ota_listing_is_refused_as_a_source(self):
        entry = MR.route_row(self._row("https://www.expedia.com/h/1"))
        assert entry["routing_state"] == MR.ROUTE_NEEDS_FIRST_PARTY_URL

    def test_a_brand_index_asks_for_a_property_url(self):
        entry = MR.route_row(self._row("https://www.choicehotels.com/hotels"))
        assert entry["routing_state"] == MR.ROUTE_NEEDS_PROPERTY_URL

    def test_an_excluded_brand_is_not_silently_routed(self):
        entry = MR.route_row(self._row(
            "https://www.hyatt.com/en-US/hotel/missouri/hyatt-regency/stlrs"))
        assert entry["routing_state"] == MR.ROUTE_BRAND_EXCLUDED
        assert entry["brand"] == "HYATT"

    def test_a_property_page_resolves_a_measured_lane(self):
        entry = MR.route_row(self._row(
            "https://www.marriott.com/en-us/hotels/stlaw-ac-hotel/overview/"))
        assert entry["routing_state"] == MR.ROUTED
        assert entry["provider"]
        assert entry["reader"] == "marriott"
        assert entry["measured_by"], "a route with no measurement is an opinion"

    def test_the_summary_counts_only_actually_routed_rows(self):
        rows = [self._row("https://www.marriott.com/en-us/hotels/stlaw-x/overview/"),
                self._row(""),
                self._row("https://www.choicehotels.com/hotels")]
        for index, row in enumerate(rows):
            row["identity_key"] = "k%d" % index
        _entries, summary = MR.route_census(rows)
        assert summary["automatically_routed"] == 1
        assert summary["count"] == 3
