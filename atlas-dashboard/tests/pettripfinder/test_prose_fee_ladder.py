"""PTF-FEES-PROSE -- a pet fee with more than one dimension, stated in prose.

Two real Columbus properties publish a fee no reader could represent:

    "Nonrefundable pet fee of 25 dollars per night with a maximum of 75 dollars
     for stays 1 to 6 nights and 150 dollars for 7 or more nights."

    "Pets with a max weight of 40 lbs each are allowed for a non-refundable fee
     of 45 USD for the 1st night and 10 USD for each additional night to a
     maximum of 180USD per stay."

The first published no fee at all. The second published nothing at all -- its
policy card carried no labelled field, so it could not even be located. And the
second is the more dangerous of the two: the scalar prose reader looks at it and
answers "$45", which is the price of exactly one night.

These tests pin the grammar, and -- more importantly -- the refusals. A third
property states a $500 penalty for an UNREGISTERED pet and then says a pet fee
exists without ever giving its amount. Nothing here may turn that into a fee.

Offline: no network, no browser, no production write.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.promote_attested_candidates import (
    PromotionError, extract_pet_facts,
)
from scripts.pettripfinder.prose_fee_ladder import (
    has_prose_fee_schedule, parse_prose_fee_schedule,
)

# The three blocks below are the captured official text, whitespace-normalised.
CANDLEWOOD = (
    "Can I bring my pet to Candlewood Suites Columbus North - Polaris? Pets are "
    "welcome at Candlewood Suites Columbus North - Polaris. Pet policy "
    "description. Nonrefundable pet fee of 25 dollars per night with a maximum "
    "of 75 dollars for stays 1 to 6 nights and 150 dollars for 7 or more "
    "nights. Pet fee per night: 25 USD Pet weight limit: 80 2 pets allowed "
    "Pets allowed: Only dogs and cats allowed Pet policy")

HAWTHORN = (
    "Pets with a max weight of 40 lbs each are allowed for a non-refundable fee "
    "of 45 USD for the 1st night and 10 USD for each additional night to a "
    "maximum of 180USD per stay. Pet agreement must be signed at check-in. Call "
    "hotel for details. ADA defined service animals are welcome at this hotel "
    "SMOKING POLICY This is a non-smoking hotel. GENERAL INFORMATION Guests "
    "must be at least 21 years of age to check-in. A refundable deposit of up "
    "to 50.00 USD is required at check-in for incidentals.")

STAYBRIDGE = (
    "Can I bring my pet to Staybridge Suites Columbus OSU-Medical Center? Pets "
    "are welcome at Staybridge Suites Columbus OSU-Medical Center. Our Pet "
    "Policy: Any unregistered pet will result in a 500.00 penalty There is a "
    "pet fee for all registered pets")


# --------------------------------------------------------------------------- #
# 1. The two shapes this exists to read.
# --------------------------------------------------------------------------- #

def test_a_nightly_rate_under_a_stay_length_ceiling_keeps_both_apart():
    """$25 a night, capped at $75 for a short stay and $150 for a long one.

    The ceiling is NOT the fee. A single night at this property costs $25, so
    publishing the $75 six-night ceiling as the price would overstate it
    threefold -- which is exactly what reading the ladder as a fee ladder does.
    """
    s = parse_prose_fee_schedule(CANDLEWOOD)
    assert s is not None
    assert (s.rate.amount, s.rate.basis) == ("25.00", "per night")
    assert s.is_staged is False
    assert [(t.min_nights, t.max_nights, t.amount) for t in s.cap_tiers] == [
        (1, 6, "75.00"), (7, None, "150.00")]
    assert s.cap is None


def test_a_first_night_priced_apart_from_every_night_after_it():
    """$45 then $10, ceiling $180 per stay -- and no single "the fee"."""
    s = parse_prose_fee_schedule(HAWTHORN)
    assert s is not None
    assert (s.first_night.amount, s.additional_night.amount) == ("45.00", "10.00")
    assert (s.cap.amount, s.cap.basis) == ("180.00", "per stay")
    assert s.is_staged is True
    assert s.rate is None


def test_the_staged_fee_is_never_flattened_into_one_pet_fee():
    """The specific error: $45 is one night's price, not the stay's price."""
    facts, _evidence, _block = extract_pet_facts(HAWTHORN)
    assert "pet_fee" not in facts
    assert facts["fee_schedule"]["first_night"]["amount"] == "45.00"
    assert facts["fee_schedule"]["additional_night"]["amount"] == "10.00"


def test_the_tiered_ceiling_is_never_published_as_a_fee_ladder():
    """``fee_cap_tiers`` and ``fee_tiers`` are different claims about money."""
    facts, _evidence, _block = extract_pet_facts(CANDLEWOOD)
    assert facts["pet_fee"] == "$25.00"
    assert facts["fee_basis"] == "per night"
    assert "fee_tiers" not in facts
    assert [t["amount"] for t in facts["fee_cap_tiers"]] == ["75.00", "150.00"]
    assert [t["max_nights"] for t in facts["fee_cap_tiers"]] == [6, ""]


def test_a_property_priced_only_in_prose_becomes_locatable():
    """Hawthorn carries no labelled field at all and was previously refused."""
    facts, evidence, _block = extract_pet_facts(HAWTHORN)
    assert facts["pets_allowed"] == "true"
    assert facts["weight_limit"] == "40.0 pounds"
    assert facts["fee_cap"]["amount"] == "180.00"
    assert {e["field"] for e in evidence} >= {"fee_schedule", "fee_cap"}


def test_every_returned_amount_carries_its_own_source_words():
    for block in (CANDLEWOOD, HAWTHORN):
        s = parse_prose_fee_schedule(block)
        for value in (s.rate, s.first_night, s.additional_night, s.cap):
            if value is not None:
                assert value.quote and value.quote in " ".join(block.split())
        for tier in s.cap_tiers:
            assert tier.quote in " ".join(block.split())


def test_quotations_begin_and_end_on_whole_words():
    """A quotation is shown as the property's own words."""
    s = parse_prose_fee_schedule(HAWTHORN)
    assert s.first_night.quote.startswith("are allowed for a non-refundable fee")


# --------------------------------------------------------------------------- #
# 2. Normalisation.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("phrase, amount", [
    ("25 dollars", "25.00"),
    ("25 USD", "25.00"),
    ("$25", "25.00"),
    ("$25.00", "25.00"),
    ("25.5 dollars", "25.50"),
    ("1,250 dollars", "1250.00"),
    ("seven dollars", "7.00"),             # closed word list, one to ten
    ("ten USD", "10.00"),
])
def test_amounts_normalise_deterministically(phrase, amount):
    block = ("Pets are welcome for a non-refundable pet fee of %s for the first "
             "night and 10 USD for each additional night." % phrase)
    s = parse_prose_fee_schedule(block)
    assert s is not None and s.first_night.amount == amount


@pytest.mark.parametrize("phrase", [
    "twenty five dollars", "forty seven dollars", "one hundred dollars",
])
def test_a_compound_word_amount_is_refused_not_half_read(phrase):
    """The closed list runs one to ten, so "twenty five" matches only "five".

    Reading it would publish $5 for a $25 fee -- understated fivefold, with a
    quotation that appears to support it. Refusing is the only safe answer.
    """
    block = ("Pets are welcome for a pet fee of %s for the first night and 10 "
             "USD for each additional night." % phrase)
    assert parse_prose_fee_schedule(block) is None


def test_the_same_amount_written_two_ways_is_one_value():
    a = parse_prose_fee_schedule(
        "Pets welcome for a pet fee of $45 for the 1st night and $10 for each "
        "additional night.")
    b = parse_prose_fee_schedule(
        "Pets welcome for a pet fee of 45 USD for the 1st night and 10 dollars "
        "for each additional night.")
    assert (a.first_night.amount, a.additional_night.amount) == \
           (b.first_night.amount, b.additional_night.amount) == ("45.00", "10.00")


# --------------------------------------------------------------------------- #
# 3. Refusals. These matter more than the extractions.
# --------------------------------------------------------------------------- #

def test_an_unregistered_pet_penalty_is_never_a_pet_fee():
    """The $500 is a penalty for breaking the policy, not the price of a pet.

    It is refused twice over: "500.00" carries no currency marker, and its
    sentence names a penalty for an unregistered animal.
    """
    assert parse_prose_fee_schedule(STAYBRIDGE) is None
    with pytest.raises(PromotionError):
        extract_pet_facts(STAYBRIDGE)


def test_a_fee_asserted_with_no_amount_stays_refused():
    """"There is a pet fee" states that money is owed, not how much."""
    block = ("Pets are welcome at this property. There is a pet fee for all "
             "registered pets. Please ask at the front desk.")
    assert parse_prose_fee_schedule(block) is None


def test_a_refundable_deposit_is_not_a_fee():
    block = ("Pets are welcome. A refundable deposit of 150 USD is required at "
             "check-in and is returned at departure.")
    assert parse_prose_fee_schedule(block) is None


def test_a_damage_charge_is_not_a_fee():
    block = ("Pets are welcome. Guests are responsible for damages, billed at a "
             "minimum of 250 USD per stay after departure.")
    assert parse_prose_fee_schedule(block) is None


def test_the_incidentals_deposit_beside_a_real_pet_fee_is_not_harvested():
    """Hawthorn states both. Only the pet fee is read."""
    s = parse_prose_fee_schedule(HAWTHORN)
    amounts = {v.amount for v in (s.rate, s.first_night, s.additional_night, s.cap)
               if v is not None}
    assert "50.00" not in amounts


def test_an_unrelated_dollar_amount_is_invisible():
    block = ("Pets are welcome for a pet fee of 45 USD for the 1st night and 10 "
             "USD for each additional night. Our restaurant serves a 30 USD "
             "prix fixe menu nightly.")
    s = parse_prose_fee_schedule(block)
    assert s is not None
    assert {v.amount for v in (s.first_night, s.additional_night)} == {"45.00", "10.00"}
    assert s.cap is None and not s.cap_tiers


def test_ambiguous_two_fee_prose_is_refused_rather_than_picked():
    block = ("Pets are welcome. There is a pet fee of 50 USD and a pet fee of "
             "75 USD for the 1st night and 10 USD for each additional night.")
    assert parse_prose_fee_schedule(block) is None


def test_two_sentences_disagreeing_about_the_first_night_refuse():
    block = ("Pets welcome for a pet fee of 45 USD for the 1st night and 10 USD "
             "for each additional night. A pet fee of 65 USD for the first "
             "night and 10 USD for each additional night applies to suites.")
    assert parse_prose_fee_schedule(block) is None


def test_a_bare_number_without_currency_is_not_money():
    block = ("Pets are welcome for a pet fee of 45 for the 1st night and 10 for "
             "each additional night.")
    assert parse_prose_fee_schedule(block) is None


def test_a_number_without_fee_context_is_not_money():
    block = ("Pets under 40 lbs are welcome in rooms 100 to 150. Call 614 555 "
             "0100. Established 1997.")
    assert parse_prose_fee_schedule(block) is None


def test_a_weight_is_never_read_as_an_amount():
    s = parse_prose_fee_schedule(HAWTHORN)
    amounts = {v.amount for v in (s.rate, s.first_night, s.additional_night, s.cap)
               if v is not None}
    assert "40.00" not in amounts


def test_an_amount_outside_the_policy_sentences_never_enters_the_fee():
    """A charge for something other than the animal is a different obligation.

    The reader is given the policy excerpt and nothing else, so a page-wide
    amount cannot reach it at all. Within the excerpt, a sentence that never
    mentions an animal is passed over for the same reason.
    """
    inside = ("Pets are welcome for a pet fee of 45 USD for the 1st night and "
              "10 USD for each additional night.")
    outside = " Parking is 32 USD per night. Resort fee is 40 USD per stay."

    alone = parse_prose_fee_schedule(inside)
    together = parse_prose_fee_schedule(inside + outside)
    assert together == alone
    assert alone.cap is None and not alone.cap_tiers
    assert {alone.first_night.amount, alone.additional_night.amount} == \
           {"45.00", "10.00"}
    assert "32.00" not in str(together) and "40.00" not in str(together)


def test_half_a_staged_fee_is_not_a_staged_fee():
    """A first-night price with no follow-on price misstates every longer stay."""
    block = ("Pets are welcome for a non-refundable pet fee of 45 USD for the "
             "first night.")
    assert parse_prose_fee_schedule(block) is None


def test_a_partly_understood_sentence_is_refused_whole():
    block = ("Pets are welcome for a pet fee of 45 USD for the 1st night, 10 "
             "USD for each additional night, and 20 USD.")
    assert parse_prose_fee_schedule(block) is None


def test_a_stay_length_ladder_with_no_ceiling_word_is_left_alone():
    """That is a tiered FEE. This module cannot represent one, so it declines."""
    block = ("Pets are welcome. The pet fee is 75 dollars for stays 1 to 4 "
             "nights and 125 dollars for 5 or more nights.")
    assert parse_prose_fee_schedule(block) is None


# --------------------------------------------------------------------------- #
# 4. This reader never speaks over one that already answers.
# --------------------------------------------------------------------------- #

def test_a_plain_scalar_fee_is_left_to_the_existing_reader():
    """One amount and one basis is not a schedule. Answering for it would
    rewrite the evidence quotation of hotels that publish today."""
    assert parse_prose_fee_schedule(
        "Pets are welcome. Fees - 50USD per stay.") is None
    assert parse_prose_fee_schedule(
        "Pets welcome for a pet fee of 50 USD per night up to a maximum of "
        "150 USD.") is None


@pytest.mark.parametrize("block, expected", [
    # Marriott: labelled, basis in the label.
    ("Pets Welcome Non-Refundable Pet Fee Per Stay: $100.00 Maximum Pet "
     "Weight: 75.0lbs Maximum Number of Pets in Room: 2", "$100.00"),
    # Hilton: labelled inside the pet card.
    ("Pets allowed Yes Non-refundable fee: $75 Max weight 50 lbs", "$75"),
    # Wyndham: table layout, amount before the label.
    ("Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee Max pets 2",
     "$75.00"),
])
def test_labelled_fees_are_unchanged(block, expected):
    facts, _evidence, _b = extract_pet_facts(block)
    assert facts["pet_fee"] == expected
    assert "fee_schedule" not in facts and "fee_cap_tiers" not in facts


def test_a_labelled_tier_ladder_still_wins():
    block = ("Pets allowed Yes Other pet information 1-4 night stay $75; 5+ "
             "night stay $125; 2 pets max; dog or cat only Max weight 50 lbs")
    facts, _evidence, _b = extract_pet_facts(block)
    assert [t["amount"] for t in facts["fee_tiers"]] == ["75.00", "125.00"]
    assert "fee_schedule" not in facts and "fee_cap_tiers" not in facts


def test_block_selection_only_gains_blocks_that_state_a_price():
    assert has_prose_fee_schedule(HAWTHORN) is True
    assert has_prose_fee_schedule(STAYBRIDGE) is False
    assert has_prose_fee_schedule("Pets are welcome at this property.") is False
