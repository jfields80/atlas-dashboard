"""PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001 -- the page shell's exact markup.

The nav and footer were hard-coded constants until a hotels-only market shipped
56 links to directory pages it never built. They became functions of the
published category list, defaulting to all three.

A refactor like that is only safe if the default output is byte-identical, and
"byte-identical" is a claim that needs a witness. The literals below ARE the
pre-refactor constants, copied verbatim from the commit that removed them
(f6f6f52:scripts/pettripfinder/site_pages.py). Keeping them here rather than in
the module means the guarantee is checked rather than duplicated: two copies of
the markup in production code would simply drift apart, and nothing would
notice.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.site_pages import (
    _category_items, _footer, _nav, comparison_href, is_published_category,
    set_published_categories,
)

#: Verbatim from before the refactor.
LEGACY_NAV = (
    '<header><nav aria-label="Main" class="ac-nav ac-nav--header-standard ac-nav--standard">'
    "<ul><li><a href=\"/\">PetTripFinder</a></li>"
    '<li><a href="/pet-friendly-hotels/">Pet-Friendly Hotels</a></li>'
    '<li><a href="/pet-friendly-parks/">Pet-Friendly Parks</a></li>'
    '<li><a href="/pet-friendly-restaurants/">Pet-Friendly Restaurants</a></li>'
    "</ul></nav></header>"
)

LEGACY_FOOTER = (
    "<footer><div class=\"ac-legal ac-legal--footer-directory ac-legal--standard\">"
    "<p>(c) 2026 PetTripFinder. All rights reserved.</p>"
    "<p>Some listings are sponsored placements or contain affiliate links, always clearly "
    "labeled. Pet policies may change; confirm directly with the business before you travel.</p>"
    "<ul><li><a href=\"/\">PetTripFinder</a></li><li><a href=\"/about/\">About PetTripFinder</a></li>"
    "<li><a href=\"/contact/\">Contact Us</a></li><li><a href=\"/methodology/\">Our Methodology</a></li>"
    "<li><a href=\"/pet-friendly-hotels/\">Pet-Friendly Hotels</a></li>"
    "<li><a href=\"/pet-friendly-parks/\">Pet-Friendly Parks</a></li>"
    "<li><a href=\"/pet-friendly-restaurants/\">Pet-Friendly Restaurants</a></li></ul>"
    "</div></footer>"
)

ALL_THREE = ("pet-friendly-hotels", "pet-friendly-parks", "pet-friendly-restaurants")


@pytest.fixture(autouse=True)
def _reset():
    """Build state is module-global. Leaving it set would leak a market's
    categories into whatever test ran next."""
    set_published_categories(None)
    yield
    set_published_categories(None)


class TestTheDefaultIsByteIdentical:

    def test_the_nav_is_unchanged(self):
        assert _nav(None) == LEGACY_NAV

    def test_the_footer_is_unchanged(self):
        assert _footer(None) == LEGACY_FOOTER

    def test_naming_all_three_is_the_same_as_naming_none(self):
        assert _nav(ALL_THREE) == LEGACY_NAV
        assert _footer(ALL_THREE) == LEGACY_FOOTER


class TestAMarketLinksOnlyToWhatItBuilds:

    def test_a_hotels_only_market_drops_the_other_two(self):
        nav = _nav(["pet-friendly-hotels"])
        assert "/pet-friendly-hotels/" in nav
        assert "/pet-friendly-parks/" not in nav
        assert "/pet-friendly-restaurants/" not in nav

    def test_the_footer_keeps_its_non_category_links(self):
        footer = _footer(["pet-friendly-hotels"])
        for kept in ("/about/", "/contact/", "/methodology/"):
            assert kept in footer
        assert "/pet-friendly-parks/" not in footer

    def test_an_empty_category_list_emits_no_category_links(self):
        assert _category_items([]) == ""

    def test_ordering_is_stable_and_not_caller_controlled(self):
        """Two markets carrying the same categories must render them in the
        same order regardless of how the caller sorted them."""
        assert _nav(["pet-friendly-restaurants", "pet-friendly-hotels"]) == _nav(
            ["pet-friendly-hotels", "pet-friendly-restaurants"])


class TestPerBuildState:

    def test_unset_state_publishes_everything(self):
        assert all(is_published_category(s) for s in ALL_THREE)

    def test_setting_categories_restricts_them(self):
        set_published_categories(["pet-friendly-hotels"])
        assert is_published_category("pet-friendly-hotels")
        assert not is_published_category("pet-friendly-parks")

    def test_the_comparison_route_defaults_to_the_columbus_path(self):
        assert comparison_href() == "/pet-friendly-hotels/policy-comparison/"

    def test_a_market_prefixed_route_is_honoured(self):
        set_published_categories(
            ["pet-friendly-hotels"],
            "/pet-friendly-hotels/cleveland-akron-canton/policy-comparison/")
        assert comparison_href().endswith(
            "/cleveland-akron-canton/policy-comparison/")

    def test_clearing_the_route_restores_the_default(self):
        set_published_categories(["pet-friendly-hotels"], "/x/")
        set_published_categories(None)
        assert comparison_href() == "/pet-friendly-hotels/policy-comparison/"
