"""AES-SITE-001 -- JSON-LD structured data tests. No network."""

from __future__ import annotations

import json

from scripts.pettripfinder.structured_data import (
    breadcrumb_ld,
    item_list_ld,
    lodging_business_ld,
    organization_ld,
    place_ld,
    restaurant_ld,
    to_script_tag,
    website_ld,
)

BASE = "https://pettripfinder.com"


def test_website_ld_minimal():
    ld = website_ld(BASE, "PetTripFinder")
    assert ld["@type"] == "WebSite"
    assert ld["url"] == BASE


def test_breadcrumb_ld_positions():
    ld = breadcrumb_ld(BASE, [("Home", "/"), ("Pet-Friendly Hotels", "/pet-friendly-hotels/"),
                              ("Drury Inn", "/pet-friendly-hotels/drury-inn/")])
    items = ld["itemListElement"]
    assert [i["position"] for i in items] == [1, 2, 3]
    assert items[2]["item"] == BASE + "/pet-friendly-hotels/drury-inn/"


def test_item_list_ld():
    ld = item_list_ld(BASE, "Pet-Friendly Hotels", [("A Hotel", "/pet-friendly-hotels/a/"),
                                                      ("B Hotel", "/pet-friendly-hotels/b/")])
    assert ld["@type"] == "ItemList"
    assert len(ld["itemListElement"]) == 2


def test_lodging_business_ld_omits_pets_allowed_when_not_verified():
    ld = lodging_business_ld(
        base_url=BASE, route="/pet-friendly-hotels/x/", name="X Hotel",
        street="1 A St", city="Columbus", state="OH", postal_code="43215",
        official_url="https://x.test/")
    assert "petsAllowed" not in ld


def test_lodging_business_ld_includes_pets_allowed_when_verified_true():
    ld = lodging_business_ld(
        base_url=BASE, route="/pet-friendly-hotels/x/", name="X Hotel",
        street="1 A St", city="Columbus", state="OH", postal_code="43215",
        official_url="https://x.test/", pets_allowed=True)
    assert ld["petsAllowed"] is True


def test_lodging_business_ld_includes_pets_allowed_false_for_no_pets():
    ld = lodging_business_ld(
        base_url=BASE, route="/pet-friendly-hotels/x/", name="X Hotel",
        street="", city="Columbus", state="OH", postal_code="",
        official_url="https://x.test/", pets_allowed=False)
    assert ld["petsAllowed"] is False


def test_lodging_business_ld_no_address_block_without_street_or_city():
    ld = lodging_business_ld(
        base_url=BASE, route="/pet-friendly-hotels/x/", name="X Hotel",
        street="", city="", state="", postal_code="", official_url="")
    assert "address" not in ld
    assert "sameAs" not in ld


def test_lodging_business_ld_never_emits_rating_or_price():
    ld = lodging_business_ld(
        base_url=BASE, route="/x/", name="X", street="1 A St", city="Columbus",
        state="OH", postal_code="43215", official_url="https://x.test/")
    assert "aggregateRating" not in ld
    assert "priceRange" not in ld
    assert "telephone" not in ld
    assert "openingHours" not in ld


def test_place_ld_park_type():
    ld = place_ld(base_url=BASE, route="/pet-friendly-parks/x/", name="X Park",
                  street="", city="Columbus", state="OH", postal_code="",
                  official_url="https://parks.test/x")
    assert ld["@type"] == "Park"


def test_restaurant_ld_type():
    ld = restaurant_ld(base_url=BASE, route="/pet-friendly-restaurants/x/", name="X",
                       street="1 A St", city="Columbus", state="OH", postal_code="43215",
                       official_url="https://x.test/")
    assert ld["@type"] == "Restaurant"


def test_to_script_tag_escapes_closing_script():
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "</script><script>bad"}
    tag = to_script_tag([ld])
    assert "</script><script>bad" not in tag
    assert "<\\/script>" in tag


def test_to_script_tag_empty_list_returns_empty_string():
    assert to_script_tag([]) == ""
    assert to_script_tag([{}]) == ""


def test_to_script_tag_valid_json_per_block():
    ld1 = website_ld(BASE, "PetTripFinder")
    ld2 = organization_ld(BASE, "PetTripFinder")
    tag = to_script_tag([ld1, ld2])
    assert tag.count('<script type="application/ld+json">') == 2
    # Each payload individually parses as JSON.
    import re
    payloads = re.findall(r'<script type="application/ld\+json">(.*?)</script>', tag)
    for p in payloads:
        json.loads(p.replace("<\\/", "</"))
