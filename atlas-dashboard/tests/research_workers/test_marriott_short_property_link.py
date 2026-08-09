"""PTF-CLEVELAND-MARKET-FACTORY-001 -- Marriott's short property link.

``https://www.marriott.com/cleac`` is a real property URL: the whole path is
the property code and it redirects to the full
``/en-us/hotels/<code>-<slug>/overview/`` page. Cleveland's visitors bureau
stores this form for a third of its Marriott properties, so without it five
confirmed hotels carried a genuine official URL that classified as UNKNOWN and
never reached the capture queue.

The awkward part, and the reason most of this module is about refusals: a
five-letter site section is shaped exactly like a five-letter property code.
``/deals`` and ``/cleac`` cannot be told apart by form. The extractor's
contract is to fail closed, so the site's own section words are excluded by
name -- a denylist, with a denylist's cost, and the tests below pin both what
it catches and what it is allowed to miss.
"""

from __future__ import annotations

import pytest

from services.research_workers.source_retrieval import (
    URL_SHAPE_BRAND, URL_SHAPE_PROPERTY, URL_SHAPE_SEARCH, classify_url_shape,
    extract_property_code_from_url,
)

#: The five real Cleveland URLs that were being dropped.
REAL = {
    "https://www.marriott.com/cleac": "cleac",   # AC Hotel Cleveland Beachwood
    "https://www.marriott.com/clebw": "clebw",   # Courtyard Beachwood
    "https://www.marriott.com/clein": "clein",   # Residence Inn Independence
    "https://www.marriott.com/cleip": "cleip",   # SpringHill Independence
    "https://www.marriott.com/clest": "clest",   # Fairfield Streetsboro
}


class TestTheShortLinkIsAPropertyUrl:

    @pytest.mark.parametrize("url,code", sorted(REAL.items()))
    def test_the_code_is_extracted(self, url, code):
        assert extract_property_code_from_url(url) == code

    @pytest.mark.parametrize("url", sorted(REAL))
    def test_the_shape_is_property(self, url):
        assert classify_url_shape(url) == URL_SHAPE_PROPERTY

    def test_a_trailing_slash_does_not_matter(self):
        assert extract_property_code_from_url("https://www.marriott.com/cleac/") == "cleac"

    def test_a_query_string_does_not_matter(self):
        assert extract_property_code_from_url(
            "https://www.marriott.com/cleac?utm_source=cvb") == "cleac"


class TestItFailsClosed:
    """The refusals matter more than the acceptances: a wrong code sends a
    capture at the wrong hotel."""

    @pytest.mark.parametrize("path", ["deals", "offers", "hotels", "brands",
                                      "about", "search", "en-us", "help"])
    def test_a_site_section_is_not_a_property_code(self, path):
        url = "https://www.marriott.com/%s" % path
        assert extract_property_code_from_url(url) == ""
        assert classify_url_shape(url) != URL_SHAPE_PROPERTY

    def test_a_two_segment_path_is_not_a_short_link(self):
        """Only the ONE-segment form is a short link. /brands/... is a brand
        page and stays one."""
        url = "https://www.marriott.com/brands/towneplace-suites.mi"
        assert extract_property_code_from_url(url) == ""
        assert classify_url_shape(url) == URL_SHAPE_BRAND

    def test_no_other_brand_gets_the_short_link_reading(self):
        """The shape is Marriott's. hilton.com/cleac is not a Hilton property."""
        for host in ("www.hilton.com", "www.ihg.com", "www.hyatt.com",
                     "www.choicehotels.com", "www.example.com"):
            url = "https://%s/cleac" % host
            assert extract_property_code_from_url(url) == "", host

    def test_a_word_too_long_or_short_is_refused(self):
        for seg in ("cle", "clevelandairport", "a"):
            assert extract_property_code_from_url(
                "https://www.marriott.com/%s" % seg) == ""

    def test_the_search_surface_still_outranks_everything(self):
        assert classify_url_shape(
            "https://www.marriott.com/search/findHotels.mi?destination=Cleveland"
        ) == URL_SHAPE_SEARCH


class TestNothingElseMoved:
    """The four shapes that already worked, unchanged."""

    @pytest.mark.parametrize("url,code", [
        ("https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/", "cmhea"),
        ("https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/", "cmhchhf"),
        ("https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail", "cmhtc"),
        ("https://www.redroof.com/property/oh/dublin/rri127", "rri127"),
        ("https://www.choicehotels.com/ohio/columbus/cambria-hotels/oh360", "oh360"),
    ])
    def test_existing_shapes_are_untouched(self, url, code):
        assert extract_property_code_from_url(url) == code
        assert classify_url_shape(url) == URL_SHAPE_PROPERTY

    def test_an_unknown_host_and_shape_still_yields_nothing(self):
        assert extract_property_code_from_url(
            "https://www.example-inn.com/rooms/deluxe") == ""

    def test_the_columbus_seed_still_parses_end_to_end(self):
        """The whole live seed, so a regression here shows up as a market-wide
        loss of identity keys rather than one failing case."""
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
        assert checked >= 40
