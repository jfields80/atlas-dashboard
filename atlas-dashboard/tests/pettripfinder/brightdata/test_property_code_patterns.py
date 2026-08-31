# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-PROPERTY-CODE-PARSER-REPAIR-AND-RETRY-009.

Pins the repaired IHG and Choice property-code patterns, and -- far more
importantly -- pins what they must still REFUSE.

A property-code pattern is an identity control. Widening one to make a stuck
cohort parse is exactly how a brand landing page starts satisfying a specific
property's expected code, and the failure is silent: the gate says the page is
the right hotel and the reader dutifully reads a policy off it. So most of this
module is negative. The positive cases only prove the repair works; the
negative ones prove it did not buy that by loosening identity.

The equality requirement in ``page_health`` is NOT touched by this repair and
is pinned here too: extracting a code correctly and ACCEPTING a page are
different things, and only the first changed.
"""
from __future__ import annotations

import pytest

from scripts.pettripfinder.brightdata import outcomes as O
from scripts.pettripfinder.brightdata import policy_surface as PS

# --------------------------------------------------------------------------- #
# The real canonical shapes, from the committed routing shards.
# --------------------------------------------------------------------------- #

IHG_REAL = [
    ("https://www.ihg.com/holidayinnexpress/hotels/us/en/wixom/dttal/hoteldetail",
     "dttal"),
    ("https://www.ihg.com/crowneplaza/hotels/us/en/auburn-hills/dttah/hoteldetail",
     "dttah"),
    ("https://www.ihg.com/evenhotels/hotels/us/en/ann-arbor/arbmi/hoteldetail",
     "arbmi"),
    ("https://www.ihg.com/candlewood/hotels/us/en/mason/cvgsn/hoteldetail",
     "cvgsn"),
    ("https://www.ihg.com/staybridge/hotels/us/en/detroit/dttsb/hoteldetail",
     "dttsb"),
]

CHOICE_REAL = [
    ("https://www.choicehotels.com/michigan/romulus/clarion-hotels/mi190",
     "mi190"),
    ("https://www.choicehotels.com/michigan/dearborn/comfort-inn-hotels/mi385",
     "mi385"),
    ("https://www.choicehotels.com/ohio/cincinnati/comfort-inn-hotels/oh186",
     "oh186"),
    ("https://www.choicehotels.com/kentucky/wilder/comfort-inn-hotels/ky295",
     "ky295"),
    ("https://www.choicehotels.com/michigan/ann-arbor/quality-inn-hotels/mi223",
     "mi223"),
]


@pytest.mark.parametrize("url,code", IHG_REAL)
def test_ihg_canonical_urls_yield_their_code(url, code):
    assert PS.property_code(url, "IHG") == code


@pytest.mark.parametrize("url,code", CHOICE_REAL)
def test_choice_canonical_urls_yield_their_code(url, code):
    assert PS.property_code(url, "CHOICE") == code


def test_ihg_no_longer_captures_the_city_as_the_code():
    """The defect that made the old pattern worse than useless.

    ``/hotels/us/en/wixom/dttal/`` has a five-character city sitting exactly
    where the old pattern looked for a five-character code, so it returned
    "wixom" -- a confident, wrong answer rather than an empty one.
    """
    url = ("https://www.ihg.com/holidayinnexpress/hotels/us/en/wixom/dttal/"
           "hoteldetail")
    assert PS.property_code(url, "IHG") != "wixom"
    assert PS.property_code(url, "IHG") == "dttal"


# --------------------------------------------------------------------------- #
# Negative: brand and index pages must not parse as a property.
# --------------------------------------------------------------------------- #

BRAND_INDEX_URLS = [
    ("IHG", "https://www.ihg.com/"),
    ("IHG", "https://www.ihg.com/holidayinnexpress/hotels/us/en/reservation"),
    ("IHG", "https://www.ihg.com/holidayinnexpress/hotels/us/en/explore"),
    ("IHG", "https://www.ihg.com/hotels/us/en/find-hotels"),
    ("IHG", "https://www.ihg.com/holidayinnexpress/content/us/en/deals"),
    ("CHOICE", "https://www.choicehotels.com/"),
    ("CHOICE", "https://www.choicehotels.com/michigan"),
    ("CHOICE", "https://www.choicehotels.com/michigan/detroit"),
    ("CHOICE", "https://www.choicehotels.com/comfort-inn"),
    ("CHOICE", "https://www.choicehotels.com/reservations/lookup"),
]


@pytest.mark.parametrize("brand,url", BRAND_INDEX_URLS)
def test_brand_and_index_urls_do_not_parse_as_a_property(brand, url):
    assert PS.property_code(url, brand) == ""


MALFORMED_URLS = [
    ("IHG", ""),
    ("IHG", "not a url at all"),
    ("IHG", "https://www.ihg.com/holidayinnexpress/hotels/us/en/wixom/"),
    ("IHG", "https://www.ihg.com/holidayinnexpress/hotels/us/wixom/dttal/"),
    ("IHG", "https://www.ihg.com/holidayinnexpress/hotels/us/en/wixom/dt/"),
    ("IHG", "https://www.ihg.com/holidayinnexpress/hotels/us/en/wixom/dttalxx/"),
    ("CHOICE", ""),
    ("CHOICE", "https://www.choicehotels.com/michigan/romulus/clarion-hotels/"),
    ("CHOICE", "https://www.choicehotels.com/clarion-hotels/mi190"),
    ("CHOICE", "https://www.choicehotels.com/michigan/romulus/clarion/mi190"),
]


@pytest.mark.parametrize("brand,url", MALFORMED_URLS)
def test_malformed_urls_do_not_parse(brand, url):
    assert PS.property_code(url, brand) == ""


def test_an_unknown_brand_never_parses():
    """No pattern, no code. A family absent from the table must not fall
    through to another family's pattern."""
    url = "https://www.ihg.com/holidayinnexpress/hotels/us/en/wixom/dttal/x"
    assert PS.property_code(url, "NOT_A_BRAND") == ""
    assert PS.property_code(url, "") == ""


def test_the_repair_did_not_touch_the_other_families():
    """The four patterns this order did not authorise are unchanged."""
    assert PS.property_code(
        "https://www.marriott.com/hotels/dtwsf-courtyard/", "MARRIOTT") == "dtwsf"
    assert PS.property_code(
        "https://www.hilton.com/en/hotels/dtwabhf-hampton/", "HILTON") == "dtwabhf"
    assert PS.property_code(
        "https://www.hyatt.com/hyatt-place/en-US/mkeza-hyatt-place", "HYATT") == "mkeza"
    assert PS.property_code(
        "https://www.bestwestern.com/book/x/propertyCode.50056.html",
        "BEST_WESTERN") == "50056"


# --------------------------------------------------------------------------- #
# Negative: page_health still refuses a page whose code is not the expected one.
# The repair changed EXTRACTION only. Acceptance is unchanged.
# --------------------------------------------------------------------------- #

def _healthy_body() -> str:
    return ("Welcome to the hotel. " * 400)


def _health(final_url: str, expected_url: str, expected_code: str,
            brand: str) -> str:
    return PS.page_health(title="A Hotel", body_text=_healthy_body(),
                          final_url=final_url, expected_url=expected_url,
                          expected_property_code=expected_code, brand=brand)


def test_page_health_accepts_the_property_it_asked_for():
    url = ("https://www.ihg.com/crowneplaza/hotels/us/en/auburn-hills/dttah/"
           "hoteldetail")
    assert _health(url, url, "dttah", "IHG") is None


def test_page_health_refuses_a_different_property_of_the_same_brand():
    """A sibling property cannot satisfy another property's expected code --
    the case the repair could most easily have broken, because both URLs now
    parse successfully where neither did before."""
    asked = ("https://www.ihg.com/crowneplaza/hotels/us/en/auburn-hills/dttah/"
             "hoteldetail")
    served = ("https://www.ihg.com/crowneplaza/hotels/us/en/detroit/dttnd/"
              "hoteldetail")
    assert _health(served, asked, "dttah", "IHG") == O.UNEXPECTED_PAGE


def test_page_health_refuses_a_sibling_brand_page_of_the_same_family():
    """Choice runs many brands off one domain. A Comfort Inn page must not
    satisfy a Clarion's expected code."""
    asked = "https://www.choicehotels.com/michigan/romulus/clarion-hotels/mi190"
    served = ("https://www.choicehotels.com/michigan/dearborn/"
              "comfort-inn-hotels/mi385")
    assert _health(served, asked, "mi190", "CHOICE") == O.UNEXPECTED_PAGE


def test_page_health_refuses_a_brand_landing_page():
    """The redirect that costs a market a property: the brand answers, but
    about itself. With no code in the final URL the comparison must fail."""
    asked = ("https://www.ihg.com/crowneplaza/hotels/us/en/auburn-hills/dttah/"
             "hoteldetail")
    assert _health("https://www.ihg.com/crowneplaza/hotels/us/en/reservation",
                   asked, "dttah", "IHG") == O.UNEXPECTED_PAGE
    asked_choice = ("https://www.choicehotels.com/michigan/romulus/"
                    "clarion-hotels/mi190")
    assert _health("https://www.choicehotels.com/michigan", asked_choice,
                   "mi190", "CHOICE") == O.UNEXPECTED_PAGE


def test_page_health_refuses_another_partys_domain():
    """An OTA carrying the right code in its path is still not first party."""
    asked = ("https://www.ihg.com/crowneplaza/hotels/us/en/auburn-hills/dttah/"
             "hoteldetail")
    served = ("https://www.example-ota.com/crowneplaza/hotels/us/en/"
              "auburn-hills/dttah/hoteldetail")
    assert _health(served, asked, "dttah", "IHG") == O.UNEXPECTED_PAGE


def test_page_health_still_refuses_an_access_interstitial():
    """The repair must not let an identity success outrank a denial: the
    denial gate runs first and keeps running first."""
    body = "Access Denied. You don't have permission to access this resource."
    url = ("https://www.ihg.com/crowneplaza/hotels/us/en/auburn-hills/dttah/"
           "hoteldetail")
    assert PS.page_health(title="Access Denied", body_text=body,
                          final_url=url, expected_url=url,
                          expected_property_code="dttah",
                          brand="IHG") == O.ACCESS_DENIED
