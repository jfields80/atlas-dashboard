"""PTF-COLUMBUS-FINAL-CLOSURE-001 -- property-code extraction for Red Roof and
Choice URL shapes.

Both patterns come from real property URLs already sitting in the Columbus seed,
not from a brand's documentation:

    https://www.redroof.com/property/oh/dublin/rri127
    https://www.choicehotels.com/ohio/columbus/cambria-hotels/oh360

Why it matters beyond tidiness: a missing property code costs an identity key
group. With the code present, a hotel whose recorded phone is wrong can be
re-captured with the phone omitted -- the gate then confirms on address plus
property identifier and the page supplies the correct number. Without the code
there is only one group and the substitution correctly refuses. That is exactly
what was holding Cambria Columbus-Polaris.

The extractor fails closed and must keep doing so, which is what most of these
tests are about.
"""

from __future__ import annotations

import pytest

from services.research_workers.source_retrieval import (
    extract_property_code_from_url,
)


class TestRedRoof:

    @pytest.mark.parametrize("url,code", [
        ("https://www.redroof.com/property/oh/dublin/rri127", "rri127"),
        ("https://www.redroof.com/property/oh/columbus/rri262", "rri262"),
        ("https://www.redroof.com/property/oh/columbus/rri310", "rri310"),
        ("https://www.redroof.com/property/oh/columbus/rri009", "rri009"),
    ])
    def test_real_seed_urls(self, url, code):
        assert extract_property_code_from_url(url) == code

    def test_a_trailing_slash_or_query_does_not_matter(self):
        assert extract_property_code_from_url(
            "https://www.redroof.com/property/oh/dublin/rri127/?utm=x") == "rri127"

    def test_a_truncated_property_path_yields_nothing(self):
        assert extract_property_code_from_url(
            "https://www.redroof.com/property/oh/dublin") == ""

    def test_a_slug_in_the_code_position_is_refused(self):
        assert extract_property_code_from_url(
            "https://www.redroof.com/property/oh/dublin/red-roof-plus-dublin") == ""

    def test_the_brand_landing_page_yields_nothing(self):
        assert extract_property_code_from_url("https://www.redroof.com/") == ""


class TestChoice:

    @pytest.mark.parametrize("url,code", [
        ("https://www.choicehotels.com/ohio/columbus/cambria-hotels/oh360", "oh360"),
        ("https://www.choicehotels.com/ohio/grove-city/comfort-suites-hotels/oh675",
         "oh675"),
    ])
    def test_real_seed_urls(self, url, code):
        assert extract_property_code_from_url(url) == code

    def test_the_brand_segment_is_not_what_is_matched(self):
        """Any '<something>-hotels' segment works; the brand name is never
        hard-coded, and OH360 is never special-cased."""
        assert extract_property_code_from_url(
            "https://www.choicehotels.com/texas/austin/sleep-inn-hotels/tx123") == "tx123"

    def test_a_brand_landing_page_with_no_code_yields_nothing(self):
        assert extract_property_code_from_url(
            "https://www.choicehotels.com/ohio/columbus/cambria-hotels") == ""

    def test_a_slug_after_the_brand_segment_is_refused(self):
        assert extract_property_code_from_url(
            "https://www.choicehotels.com/ohio/columbus/cambria-hotels/"
            "cambria-hotel-columbus-polaris") == ""


class TestNothingElseMoved:
    """The three shapes that already worked must be untouched."""

    @pytest.mark.parametrize("url,code", [
        ("https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/",
         "cmhea"),
        ("https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/",
         "cmhchhf"),
        ("https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail",
         "cmhtc"),
    ])
    def test_existing_shapes(self, url, code):
        assert extract_property_code_from_url(url) == code

    def test_an_unknown_host_and_shape_still_yields_nothing(self):
        assert extract_property_code_from_url(
            "https://www.example-inn.com/rooms/deluxe") == ""

    def test_known_codes_still_win_on_a_segment_boundary(self):
        assert extract_property_code_from_url(
            "https://www.redroof.com/property/oh/dublin/rri127", ["rri127"]) == "rri127"

    def test_a_known_code_is_not_matched_as_a_bare_substring(self):
        """The PTF-CAPTURE-002A defect: 'cmhap' must not match inside
        'cmhaphx'."""
        assert extract_property_code_from_url(
            "https://www.hilton.com/en/hotels/cmhaphx-somewhere/", ["cmhap"]) != "cmhap"


class TestLiveSeedUrlsAllParse:

    def test_every_columbus_seed_url_with_a_known_shape_still_resolves(self):
        """Run it over the real seed. A regression here would silently cost
        identity keys across the whole market rather than in one test."""
        import csv
        import pathlib
        seed = (pathlib.Path(__file__).resolve().parents[2] / "launch_packages"
                / "pettripfinder" / "seed_businesses.csv")
        rows = [r for r in csv.DictReader(seed.open(encoding="utf-8-sig"))
                if r.get("category") == "pet-friendly-hotels"]
        hosts = ("marriott.com", "hilton.com", "ihg.com", "redroof.com",
                 "choicehotels.com")
        checked = 0
        for row in rows:
            url = (row.get("website_url") or "").lower()
            if not any(h in url for h in hosts):
                continue
            checked += 1
            assert extract_property_code_from_url(url), row["name"]
        assert checked >= 40, "expected the seed to carry many branded URLs"


class TestUrlShapeFollowsTheCode:
    """PTF-COLUMBUS-FINAL-CLOSURE-001 -- two shape classifications that were
    wrong for reasons that had nothing to do with the hotels."""

    def test_a_recognised_property_code_makes_it_a_property_page(self):
        from services.research_workers.source_retrieval import (
            URL_SHAPE_PROPERTY, classify_url_shape,
        )
        # Same brand, same shape. Before this, one was PROPERTY and the other
        # UNKNOWN, told apart only by "columbus" having eight letters and
        # "dublin" six.
        for url in ("https://www.redroof.com/property/oh/dublin/rri127",
                    "https://www.redroof.com/property/oh/columbus/rri262"):
            assert classify_url_shape(url) == URL_SHAPE_PROPERTY, url

    def test_a_geographic_index_above_a_property_slug_is_a_property_page(self):
        from services.research_workers.source_retrieval import (
            URL_SHAPE_PROPERTY, classify_url_shape,
        )
        assert classify_url_shape(
            "https://www.druryhotels.com/locations/columbus-oh/"
            "drury-plaza-hotel-columbus-downtown") == URL_SHAPE_PROPERTY

    def test_the_index_itself_is_still_a_brand_page(self):
        from services.research_workers.source_retrieval import (
            URL_SHAPE_BRAND, classify_url_shape,
        )
        for url in ("https://www.druryhotels.com/locations",
                    "https://www.druryhotels.com/locations/columbus-oh"):
            assert classify_url_shape(url) == URL_SHAPE_BRAND, url

    def test_a_non_geographic_brand_marker_never_becomes_a_property(self):
        """/pet-policy names no property however long the path grows."""
        from services.research_workers.source_retrieval import (
            URL_SHAPE_BRAND, classify_url_shape,
        )
        assert classify_url_shape(
            "https://www.example.com/pet-policy/dogs-are-allowed-here") == URL_SHAPE_BRAND

    def test_search_still_outranks_everything(self):
        from services.research_workers.source_retrieval import (
            URL_SHAPE_SEARCH, classify_url_shape,
        )
        assert classify_url_shape(
            "https://www.marriott.com/search/findHotels.mi?destination=Columbus"
        ) == URL_SHAPE_SEARCH
