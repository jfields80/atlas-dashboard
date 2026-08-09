"""PTF-RENDER-001 -- structured policy facts in the profile details table.

The defect this exists for: a dict fact reached ``html.escape`` and the whole
build died with ``'dict' object has no attribute 'replace'``. Three of the
approved facts are objects, not strings, and the table had no agreed way to show
any of them.

The fixtures below are the EXACT approved facts, copied unsimplified.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from scripts.pettripfinder.hotel_profile import (
    PolicyRenderError, _verified_details, format_fact_value,
)

# Exactly as approved for TownePlace Suites by Marriott Columbus Dublin.
TOWNEPLACE_DUBLIN_FACTS = {
    "pet_count_limit": "2",
    "pet_fee": "$150.00",
    "pets_allowed": "true",
    "species_allowed": "dogs, cats",
    "species_weight_limits": {
        "cats": {"evidence_quote": "ts Welcome Dogs and 20-lb. cats. $150 non-refundabl",
                 "value": "20 pounds"}},
}
# Exactly as approved for La Quinta Inn & Suites West-Hilliard.
LA_QUINTA_FACTS = {
    "fee_basis": "per pet per night",
    "fee_cap": {"amount": "75.00", "basis": "per stay", "currency": "USD",
                "evidence_quote": "Max 75 USD per stay"},
    "pet_count_limit": "2", "pet_fee": "$25.00", "pets_allowed": "true",
    "species_allowed": "dogs", "weight_limit": "75.0 pounds",
}
DAYS_INN_DEPOSIT = {"amount": "150.00", "currency": "USD",
                    "evidence_quote": "Pet deposit is 150 USD"}


def _row(facts, label):
    rows, _chip, _note = _verified_details(facts)
    return next((v for lbl, v, _cls in rows if lbl == label), None)


# -- scalars are untouched -------------------------------------------------- #

@pytest.mark.parametrize("value, expected", [
    ("Dogs, cats", "Dogs, cats"), ("$50.00", "$50.00"),
    (2, "2"), (20.5, "20.5"), (Decimal("75.00"), "75.00"),
])
def test_scalar_values_pass_through_unchanged(value, expected):
    assert format_fact_value("anything", value) == expected


@pytest.mark.parametrize("value", [None, ""])
def test_absent_values_render_as_empty_so_omission_rules_still_apply(value):
    assert format_fact_value("pet_deposit", value) == ""


@pytest.mark.parametrize("value, expected", [(True, "Yes"), (False, "No")])
def test_booleans_render_as_words_not_python_literals(value, expected):
    assert format_fact_value("pets_allowed", value) == expected


# -- species_weight_limits -------------------------------------------------- #

def test_a_single_species_limit_names_only_that_species():
    assert format_fact_value("species_weight_limits",
                             TOWNEPLACE_DUBLIN_FACTS["species_weight_limits"]) == \
        "Cats: maximum 20 pounds"


def test_the_details_table_shows_the_species_limit():
    assert _row(TOWNEPLACE_DUBLIN_FACTS,
                "Species-specific weight limits") == "Cats: maximum 20 pounds"


def test_no_dog_statement_is_created_when_no_dog_limit_exists():
    """"Dogs and 20-lb. cats" limits the cat. Saying anything about the dog here
    would publish a restriction the hotel never wrote."""
    out = format_fact_value("species_weight_limits",
                            TOWNEPLACE_DUBLIN_FACTS["species_weight_limits"])
    assert "Dog" not in out and "dog" not in out


def test_multiple_species_render_in_a_stable_order():
    value = {"cats": {"value": "20 pounds"}, "dogs": {"value": "80 pounds"}}
    assert format_fact_value("species_weight_limits", value) == \
        "Dogs: maximum 80 pounds; Cats: maximum 20 pounds"
    assert format_fact_value("species_weight_limits", dict(reversed(list(value.items())))) == \
        format_fact_value("species_weight_limits", value)


@pytest.mark.parametrize("value", [
    {"cats": "20 pounds"},                 # not the nested shape
    {"cats": {"evidence_quote": "x"}},     # no value
    {"lizards": {"value": "2 pounds"}},    # species outside the vocabulary
    {},                                    # nothing to say
])
def test_a_malformed_species_limit_fails_closed(value):
    with pytest.raises(PolicyRenderError):
        format_fact_value("species_weight_limits", value, hotel_key="h")


# -- fee_cap and pet_deposit ------------------------------------------------ #

def test_the_approved_fee_cap_renders_with_its_basis():
    assert format_fact_value("fee_cap", LA_QUINTA_FACTS["fee_cap"]) == "$75 per stay"


def test_the_fee_cap_row_survives_beside_a_distinct_per_pet_fee():
    """The cap is a different fact from the rate and must not collapse into it."""
    assert _row(LA_QUINTA_FACTS, "Maximum total") == "$75 per stay"
    assert _row(LA_QUINTA_FACTS, "Pet charge") == "$25.00"


def test_a_pet_deposit_object_renders_as_money_not_as_a_dict():
    assert format_fact_value("pet_deposit", DAYS_INN_DEPOSIT) == "$150"


@pytest.mark.parametrize("value", [
    {"currency": "USD"},                            # no amount
    {"amount": "150.00", "unexpected": "field"},    # shape drift
])
def test_a_malformed_money_object_fails_closed(value):
    with pytest.raises(PolicyRenderError):
        format_fact_value("pet_deposit", value, hotel_key="h")


# -- unknown shapes --------------------------------------------------------- #

def test_an_unknown_dict_field_fails_closed_rather_than_printing_python():
    with pytest.raises(PolicyRenderError) as err:
        format_fact_value("some_new_fact", {"a": 1}, hotel_key="discovery-x")
    assert "{'a': 1}" not in str(err.value)


def test_an_unknown_list_field_fails_closed():
    with pytest.raises(PolicyRenderError):
        format_fact_value("some_new_fact", [1, 2], hotel_key="discovery-x")


def test_the_error_names_the_hotel_and_the_field():
    with pytest.raises(PolicyRenderError) as err:
        format_fact_value("some_new_fact", {"a": 1}, hotel_key="discovery-x")
    assert "discovery-x" in str(err.value) and "some_new_fact" in str(err.value)


# -- HTML safety ------------------------------------------------------------ #

def test_structured_leaf_text_is_returned_unescaped_for_the_template_to_escape():
    """One escape, at the leaf. Escaping here too would double-encode."""
    value = {"cats": {"value": "20 pounds & up"}}
    assert format_fact_value("species_weight_limits", value) == "Cats: maximum 20 pounds & up"


def test_markup_in_a_leaf_cannot_reach_a_page_unescaped():
    from scripts.pettripfinder.approved_hotel_profile import _e
    rendered = format_fact_value("species_weight_limits",
                                 {"cats": {"value": "<script>alert(1)</script>"}})
    assert "<script>" not in _e(rendered)


# -- the existing corpus still renders -------------------------------------- #

def test_every_currently_published_hotel_still_renders():
    import json
    from pathlib import Path
    pkg = json.loads((Path(__file__).resolve().parents[2] / "launch_packages"
                      / "pettripfinder" / "hotel_policy_facts.json").read_text("utf-8"))
    assert len(pkg["hotels"]) == 80
    for hotel in pkg["hotels"]:
        rows, _chip, _note = _verified_details(hotel.get("facts") or {})
        assert all(isinstance(value, str) for _lbl, value, _cls in rows)
