"""PTF-FEES-FORMS -- fee wordings the labelled patterns could not reach.

Three shapes in the live corpus produced NO fee at all, silently, on properties
whose own pages state one plainly:

    "$50 USD pet fee will apply per pet per night"   -- amount before the label
    "$150 non-refundable fee."                       -- amount before the label
    "Pet fee per night: 30 USD"                      -- basis inside the label

Silence is the dangerous outcome. "Pet charge: Not stated" on a hotel that
charges $50 a night per pet does not read as a gap; it reads as a hotel that
does not charge for pets.

A fourth property publishes its whole policy under "Dogs Allowed -" and the word
"Pets" never appears, so no block was ever located.

A fifth states two incompatible fee terms at once. That one must NOT be fixed:
it must be refused, with both quotations kept.

Offline: no network, no browser, no production write.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.fee_forms import (
    amount_before_label, competing_recurrence, fee_contradiction,
    labelled_basis_amount, stated_fee,
)
from scripts.pettripfinder.promote_attested_candidates import (
    PromotionError, extract_pet_facts, find_pet_block,
)

# Captured official text, whitespace-normalised. Marketing tails trimmed; every
# policy sentence is verbatim.
FOUR_POINTS = (
    "Pet Policy Pets Welcome $50 USD pet fee will apply per pet per night. "
    "Maximum two pets allowed. Maximum Pet Weight: 50.0lbs Maximum Number of "
    "Pets in Room: 2")

IHE_REYNOLDSBURG = (
    "Can I bring my pet to Holiday Inn Express & Suites Columbus East - "
    "Reynoldsburg? Pets are welcome at Holiday Inn Express & Suites Columbus "
    "East - Reynoldsburg. Pet policy description. We gladly accept pet with a "
    "pet fee. Fee is per night. No more than one animal per room. Policy "
    "signed upon check in. Please ask front desk for any questions. Pet fee "
    "per night: 30 USD Pet weight limit: No weight limit per pet 1 pets "
    "allowed Pets allowed: Only dogs and cats allowed Pet policy")

TOWNEPLACE_DUBLIN = (
    "Pet Policy Pets Welcome Dogs and 20-lb. cats. $150 non-refundable fee. "
    "Maximum Pet Weight: 20.0lbs Maximum Number of Pets in Room: 2")

LA_QUINTA_WEST_HILLIARD = (
    "Service Animals - ADA-defined service animals are welcome free of charge. "
    "/ Dogs Allowed - 2 dogs max. 75lbs or less per pet. / Fees - 25 USD per "
    "pet per night. Max 75 USD per stay. / Other Information - Contact hotel "
    "for additional details and availability. SMOKING POLICY This is a "
    "non-smoking hotel.")

IHE_AIRPORT_EAST = (
    "Can I bring my pet to Holiday Inn Express & Suites Columbus Airport East? "
    "Pets are welcome at Holiday Inn Express & Suites Columbus Airport East. "
    "Pet policy description. Pets weighing 75 pounds or less are permitted. Up "
    "to 2 pets per room. Nonrefundable fee of 75USD for 1 to 4 nights and "
    "125USD for 5 nights or more. Pet fee per night: 50 USD Pet weight limit: "
    "75 2 pets allowed Pets allowed: Only dogs and cats allowed")

HIE_COLUMBUS_DUBLIN = (
    "Can I bring my pet to Holiday Inn Express Columbus - Dublin? Pets are "
    "welcome at Holiday Inn Express Columbus - Dublin. Pet policy description. "
    "There is a limit of 2 dogs per room, 75lb weight limit. We do not accept "
    "cats at our property. There is a 75 USD, one time pet fee. Pet Fee is Non "
    "Refundable. Pet fee per night: 75 USD Pet weight limit: 75 2 pets allowed "
    "Pets allowed: Only dogs allowed Pet policy")

STAYBRIDGE_OSU = (
    "Can I bring my pet to Staybridge Suites Columbus OSU-Medical Center? Pets "
    "are welcome at Staybridge Suites Columbus OSU-Medical Center. Our Pet "
    "Policy: Any unregistered pet will result in a 500.00 penalty There is a "
    "pet fee for all registered pets")

LE_MERIDIEN = (
    "Pet Policy Smoke-Free Policy Cash Free Community Fee Notice Our History "
    "Experience a mix of contemporary culture rooted in European heritage Our "
    "artistically inspired boutique hotels invite you to discover the "
    "destination and absorb the local culture of your surroundings.")


# --------------------------------------------------------------------------- #
# 1. Amount before the label.
# --------------------------------------------------------------------------- #

def test_amount_before_a_pet_fee_label_carries_its_basis():
    got = amount_before_label("Pets Welcome $50 USD pet fee will apply per pet per night.")
    assert (got.amount, got.basis) == ("50.00", "per pet per night")
    assert got.quote == "$50 USD pet fee will apply per pet per night"


def test_amount_before_a_nonrefundable_fee_label_invents_no_basis():
    got = amount_before_label("Pets Welcome Dogs and cats. $150 non-refundable fee.")
    assert (got.amount, got.basis) == ("150.00", "")


@pytest.mark.parametrize("text, amount, basis", [
    ("Pets welcome. $75 pet fee per stay.", "75.00", "per stay"),
    ("Pets welcome. 40 USD pet fee applies per night.", "40.00", "per night"),
    ("Pets welcome. $25 USD pet fee is charged per pet.", "25.00", "per pet"),
    ("Pets welcome. $60 nonrefundable pet fee.", "60.00", ""),
])
def test_amount_first_variants(text, amount, basis):
    got = amount_before_label(text)
    assert (got.amount, got.basis) == (amount, basis)


def test_a_sentence_boundary_stops_a_basis_being_borrowed():
    """"$150 non-refundable fee. Charged per night" is two statements."""
    got = amount_before_label("Pets welcome. $150 non-refundable fee. Rooms are "
                              "cleaned per night.")
    assert got.basis == ""


# --------------------------------------------------------------------------- #
# 2. Basis interposed in a labelled field.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text, amount, basis", [
    ("Pet fee per night: 30 USD", "30.00", "per night"),
    ("Pet fee per stay: 75 USD", "75.00", "per stay"),
    ("Pet fee per pet per night: 25 USD", "25.00", "per pet per night"),
    ("Pet fee per pet: $20", "20.00", "per pet"),
    ("Pet fee per night $45", "45.00", "per night"),
])
def test_labelled_field_with_interposed_basis(text, amount, basis):
    got = labelled_basis_amount("Pets are welcome. " + text)
    assert (got.amount, got.basis) == (amount, basis)


def test_each_basis_dimension_is_preserved_separately():
    """"per pet per night" and "per night" are different promises."""
    a = labelled_basis_amount("Pets welcome. Pet fee per pet per night: 25 USD")
    b = labelled_basis_amount("Pets welcome. Pet fee per night: 25 USD")
    assert a.amount == b.amount == "25.00"
    assert a.basis == "per pet per night" and b.basis == "per night"


def test_a_reversed_basis_normalises_to_one_form():
    got = labelled_basis_amount("Pets welcome. Pet fee per night per pet: 25 USD")
    assert got.basis == "per pet per night"


def test_the_interposed_form_is_preferred_over_the_amount_first_form():
    both = ("Pets welcome. $50 USD pet fee will apply per night. "
            "Pet fee per pet per night: 50 USD")
    assert stated_fee(both).basis == "per pet per night"


# --------------------------------------------------------------------------- #
# 3. Species-led block start.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("heading", [
    "Dogs Allowed - 2 dogs max.", "Cats Allowed - 1 cat max.",
    "Dogs and Cats Allowed - 2 pets max.", "Dogs Allowed: 2 dogs max.",
])
def test_a_species_led_row_opens_a_policy_block(heading):
    block, _off = find_pet_block(
        heading + " 75lbs or less per pet. / Fees - 25 USD per pet per night.")
    assert block.startswith(heading.split(" -")[0].split(":")[0])


def test_a_species_mention_in_prose_does_not_open_a_block():
    """"Only dogs and cats allowed" sits mid-sentence in other properties'
    blocks; treating it as a heading could change which block they select."""
    text = ("Pet Policy Pets Welcome Non-refundable fee: $75 Maximum Pet "
            "Weight: 50.0lbs Pets allowed: Only dogs and cats allowed")
    block, off = find_pet_block(text)
    assert off == 0 and block.startswith("Pet Policy")


def test_the_wyndham_species_led_table_now_extracts():
    facts, _evidence, _b = extract_pet_facts(LA_QUINTA_WEST_HILLIARD)
    assert facts["pet_fee"] == "$25.00"
    assert facts["fee_basis"] == "per pet per night"
    assert facts["fee_cap"]["amount"] == "75.00"


# --------------------------------------------------------------------------- #
# 4. The Front Desk heading versus the phrase.
# --------------------------------------------------------------------------- #

def test_front_desk_as_prose_no_longer_truncates_the_policy():
    """"Please ask front desk for any questions." sits INSIDE the card, and
    closing the block there cut the property off before its own fee line."""
    facts, _evidence, block = extract_pet_facts(IHE_REYNOLDSBURG)
    assert facts["pet_fee"] == "$30.00" and facts["fee_basis"] == "per night"
    assert "Pet fee per night: 30 USD" in block


def test_front_desk_as_a_heading_still_closes_the_block():
    text = ("Pet Policy Pets Welcome Non-refundable fee: $75 Maximum Pet "
            "Weight: 50.0lbs. Front Desk Open 24 hours. Non-refundable fee: $999")
    _facts, _evidence, block = extract_pet_facts(text)
    assert "$999" not in block


# --------------------------------------------------------------------------- #
# 5. Contradiction: two fee terms, neither chosen.
# --------------------------------------------------------------------------- #

def test_a_ladder_beside_a_flat_rate_is_surfaced_not_resolved():
    clash = fee_contradiction(IHE_AIRPORT_EAST)
    assert clash is not None
    assert clash.ladder_quote == ("Nonrefundable fee of 75USD for 1 to 4 nights "
                                  "and 125USD for 5 nights or more.")
    assert clash.rate_quote == "Pet fee per night: 50 USD"
    assert clash.detail == "stay_length_ladder_conflicts_with_flat_rate"


def test_the_contradiction_publishes_no_fee_and_keeps_both_quotes():
    facts, evidence, _b = extract_pet_facts(IHE_AIRPORT_EAST)
    assert "pet_fee" not in facts and "fee_basis" not in facts
    assert "fee_tiers" not in facts and "fee_schedule" not in facts
    conflict = facts["fee_conflict"]
    assert conflict["reason"] == "conflicting_fee_terms_in_official_source"
    assert conflict["quotes"] == [
        "Nonrefundable fee of 75USD for 1 to 4 nights and 125USD for 5 nights or more.",
        "Pet fee per night: 50 USD"]
    quotes = [e["quote"] for e in evidence if e["field"] == "fee_conflict"]
    assert len(quotes) == 2
    # The property is still pet-friendly; only the money is withheld.
    assert facts["pets_allowed"] == "true"


def test_a_one_time_fee_stated_beside_a_nightly_one_is_a_contradiction():
    """$75 once, or $75 a night? Five nights differ by $300.

    Superseded behaviour, changed under PTF-REVIEW-B2 on reviewer direction:
    this used to publish the amount with a silent basis. That let a reader
    assume the cheaper reading of two terms the source states with equal force,
    so the fee is now withheld and both quotations are kept.
    """
    assert competing_recurrence(HIE_COLUMBUS_DUBLIN) is True
    assert stated_fee(HIE_COLUMBUS_DUBLIN) is None
    facts, _evidence, _b = extract_pet_facts(HIE_COLUMBUS_DUBLIN)
    assert "pet_fee" not in facts and "fee_basis" not in facts
    assert facts["fee_conflict"]["detail"] == [
        "one_time_fee_conflicts_with_nightly_fee"]
    assert len(facts["fee_conflict"]["quotes"]) == 2


def test_a_cap_stated_per_stay_does_not_compete_with_a_nightly_rate():
    """"$25 per night up to a maximum of $75 per stay" is one coherent term."""
    assert competing_recurrence(
        "Pets welcome. Pet fee per night: 25 USD. Max 75 USD per stay.") is False


# --------------------------------------------------------------------------- #
# 6. Refusals that must survive.
# --------------------------------------------------------------------------- #

def test_the_unregistered_pet_penalty_is_still_never_a_fee():
    assert stated_fee(STAYBRIDGE_OSU) is None
    assert amount_before_label(STAYBRIDGE_OSU) is None
    with pytest.raises(PromotionError):
        extract_pet_facts(STAYBRIDGE_OSU)


def test_the_navigation_stub_is_still_refused_for_re_capture():
    assert stated_fee(LE_MERIDIEN) is None
    with pytest.raises(PromotionError):
        extract_pet_facts(LE_MERIDIEN)


@pytest.mark.parametrize("text", [
    "Pets welcome. 50 pet fee will apply per night.",          # no currency
    "Pets welcome. Pet fee per night: 30",                     # no currency
    "Pets welcome. Pet fee per night: 30 percent",             # not money
])
def test_a_bare_number_without_currency_is_ignored(text):
    assert stated_fee(text) is None


@pytest.mark.parametrize("text", [
    "Pets welcome. A $500 penalty applies for an unregistered pet fee.",
    "Pets welcome. $200 refundable deposit, non-refundable fee terms apply.",
    "Pets welcome. $250 damage fee will apply per night.",
    "Pets welcome. $95 cleaning fee will apply per stay.",
    "Pets welcome. A $75 fine, non-refundable fee, for smoking.",
])
def test_penalties_deposits_damage_and_cleaning_are_excluded(text):
    assert stated_fee(text) is None


def test_an_unrelated_amount_is_not_borrowed_as_a_pet_fee():
    """A non-refundable fee with no animal anywhere near it is someone else's."""
    assert amount_before_label(
        "Cancellation terms. $250 non-refundable fee applies to group bookings. "
        + "x" * 200) is None


def test_only_the_supplied_block_is_ever_read():
    inside = "Pets welcome. Pet fee per night: 30 USD"
    outside = " Parking is 32 USD nightly. Valet is 40 USD nightly."
    got = stated_fee(inside + outside)
    assert (got.amount, got.basis) == ("30.00", "per night")


def test_a_competing_recurrence_anywhere_in_the_block_withholds_the_fee():
    """Deliberately blunt, and deliberately conservative.

    This reader cannot tell which charge a stray "per stay" belongs to, so a
    block asserting both recurrences gets no answer from it at all and falls
    back to whatever the older readers already said. Declining costs coverage;
    guessing would publish a nightly rate as a one-time charge, or the reverse.
    """
    assert stated_fee("Pets welcome. Pet fee per night: 30 USD "
                      "Resort fee per stay: 40 USD") is None


# --------------------------------------------------------------------------- #
# 7. The live corpus outcomes these forms exist for.
# --------------------------------------------------------------------------- #

def test_four_points_extracts_fifty_per_pet_per_night():
    facts, _e, _b = extract_pet_facts(FOUR_POINTS)
    assert facts["pet_fee"] == "$50.00"
    assert facts["fee_basis"] == "per pet per night"
    assert facts["weight_limit"] == "50.0 pounds"


def test_towneplace_dublin_extracts_one_fifty_with_no_basis():
    facts, _e, _b = extract_pet_facts(TOWNEPLACE_DUBLIN)
    assert facts["pet_fee"] == "$150.00"
    assert "fee_basis" not in facts
    assert facts["weight_limit"] == "20.0 pounds"


# --------------------------------------------------------------------------- #
# 8. Nothing already understood may be disturbed.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("block, expected_fee, expected_basis", [
    ("Pets Welcome Non-Refundable Pet Fee Per Stay: $100.00 Maximum Pet "
     "Weight: 75.0lbs Maximum Number of Pets in Room: 2", "$100.00", "per stay"),
    ("Pets allowed Yes Non-refundable fee: $75 Max weight 50 lbs", "$75", None),
    ("Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee Max pets 2",
     "$75.00", None),
])
def test_labelled_fees_are_unchanged(block, expected_fee, expected_basis):
    facts, _e, _b = extract_pet_facts(block)
    assert facts["pet_fee"] == expected_fee
    if expected_basis:
        assert facts["fee_basis"] == expected_basis
    assert "fee_conflict" not in facts


def test_a_tier_ladder_still_wins_over_the_new_forms():
    block = ("Pets allowed Yes Other pet information 1-4 night stay $75; 5+ "
             "night stay $125; 2 pets max Max weight 50 lbs")
    facts, _e, _b = extract_pet_facts(block)
    assert [t["amount"] for t in facts["fee_tiers"]] == ["75.00", "125.00"]
    assert "pet_fee" not in facts and "fee_conflict" not in facts


def test_the_tiered_cap_property_is_unchanged():
    block = ("Pets are welcome. Nonrefundable pet fee of 25 dollars per night "
             "with a maximum of 75 dollars for stays 1 to 6 nights and 150 "
             "dollars for 7 or more nights. Pet fee per night: 25 USD 2 pets "
             "allowed")
    facts, _e, _b = extract_pet_facts(block)
    assert facts["pet_fee"] == "$25.00" and facts["fee_basis"] == "per night"
    assert [t["amount"] for t in facts["fee_cap_tiers"]] == ["75.00", "150.00"]


def test_the_staged_schedule_property_is_unchanged():
    block = ("Pets with a max weight of 40 lbs each are allowed for a "
             "non-refundable fee of 45 USD for the 1st night and 10 USD for "
             "each additional night to a maximum of 180USD per stay.")
    facts, _e, _b = extract_pet_facts(block)
    assert facts["fee_schedule"]["first_night"]["amount"] == "45.00"
    assert "pet_fee" not in facts


# --------------------------------------------------------------------------- #
# 9. PTF-FEES-LADDER -- notation variants, ordinal pet ladders, and one more
#    contradiction shape. All six came from Columbus Machine Review Batch 1,
#    where each would have published a fee wrong for a real booking.
# --------------------------------------------------------------------------- #

from services.research_workers.fee_terms import parse_fee_tiers   # noqa: E402
from scripts.pettripfinder.fee_forms import (                     # noqa: E402
    nightly_versus_per_stay_conflict, ordinal_pet_fees,
)

HILTON_ROW = ("Pets Smoking WiFi Pets allowed Yes Deposit Yes. $%s Non-refundable "
              "Fee Max weight 75 lbs Other pet information %s")


@pytest.mark.parametrize("ladder", [
    "1-4n $75, 5+ $125",                    # unit only on the first rung
    "1-4 days $75.00, 5 plus days $125.00",  # "days" unit, "plus" spelled out
    "$75(1-4nt), $125(5+n)",                 # compact "nt"
    "$75(1-4n)$125(5+n)",                    # the form that already worked
    "1-4 night stay $50; 5+ night stay $75",
])
def test_stay_length_ladder_notations_all_parse(ladder):
    terms, problems = parse_fee_tiers(ladder)
    assert problems == [], (ladder, problems)
    assert len(terms) == 2, ladder
    assert terms[0].condition_min == 1
    assert terms[1].condition_max is None       # open-ended upper rung


def test_a_days_ladder_reaches_the_extractor():
    facts, _e, _b = extract_pet_facts(HILTON_ROW % ("75.00", "1-4 days $75.00, 5 plus days $125.00"))
    assert [t["amount"] for t in facts["fee_tiers"]] == ["75.00", "125.00"]
    assert "pet_fee" not in facts               # the deposit row never wins


def test_a_unitless_open_rung_reaches_the_extractor():
    facts, _e, _b = extract_pet_facts(HILTON_ROW % ("75.00", "1-4n $75, 5+ $125, 2 pets max dog/cat"))
    assert [t["amount"] for t in facts["fee_tiers"]] == ["75.00", "125.00"]
    assert "pet_fee" not in facts


def test_a_lone_open_rung_is_not_a_ladder():
    """"5+ $125" with no sibling states no stay length at all."""
    terms, problems = parse_fee_tiers("Other pet information 5+ $125")
    assert terms == () and problems == ["tier_notation_unparseable"]


def test_a_malformed_range_boundary_refuses_rather_than_publishing_a_sibling():
    """"$75(1-na)" is unreadable. Publishing the surviving $125 as a flat fee
    would overcharge every short stay."""
    terms, problems = parse_fee_tiers("$75(1-na) $125(5+n)")
    assert terms == () and problems == ["tier_malformed_range_boundary"]
    with pytest.raises(PromotionError, match="tier_malformed_range_boundary"):
        extract_pet_facts(HILTON_ROW % ("125.00", "$75(1-na) $125(5+n) 2pets Max, dog only"))


# --------------------------------------------------------------------------- #
# Ordinal pet ladders.
# --------------------------------------------------------------------------- #

ORDINAL_BLOCK = ("Pets Smoking WiFi Pets allowed Yes Deposit Yes. $80.00 "
                 "Non-refundable Fee Max weight 50 lbs Other pet information "
                 "Max 2 cat(s) or 2 dog(s), Fee $80 for first pet and $50 for "
                 "second pet per stay.")


def test_a_per_animal_ladder_is_kept_apart():
    got = ordinal_pet_fees(ORDINAL_BLOCK)
    assert dict((n, (f.amount, f.basis)) for n, f in got.fees) == {
        "first_pet": ("80.00", "per stay"), "second_pet": ("50.00", "per stay")}


def test_the_per_animal_ladder_is_never_flattened_to_one_fee():
    """A two-pet stay here costs $130. No single number can say that."""
    facts, evidence, _b = extract_pet_facts(ORDINAL_BLOCK)
    assert "pet_fee" not in facts
    sched = facts["fee_pet_schedule"]
    assert sched["first_pet"]["amount"] == "80.00"
    assert sched["second_pet"]["amount"] == "50.00"
    assert sched["first_pet"]["basis"] == sched["second_pet"]["basis"] == "per stay"
    assert len([e for e in evidence if e["field"] == "fee_pet_schedule"]) == 2


def test_a_single_ordinal_mention_is_not_a_ladder():
    assert ordinal_pet_fees("Pets welcome. $80 for first pet per stay.") is None


def test_an_ordinal_basis_is_not_invented_when_the_clause_states_two():
    got = ordinal_pet_fees("Pets welcome. $80 for first pet per night and $50 "
                           "for second pet per stay.")
    assert all(f.basis == "" for _n, f in got.fees)


# --------------------------------------------------------------------------- #
# Nightly fee versus an unrelated per-stay fee.
# --------------------------------------------------------------------------- #

TOWNEPLACE = ("Pet Policy Pets Welcome $50 nonrefundable pet fee per night; max "
              "$300 per stay. 2 pets, 50 lbs max. Non-Refundable Pet Fee Per "
              "Stay: $100.00 Maximum Pet Weight: 50.0lbs Maximum Number of Pets "
              "in Room: 2")


def test_a_nightly_fee_beside_a_per_stay_fee_is_surfaced_not_resolved():
    clash = nightly_versus_per_stay_conflict(TOWNEPLACE)
    assert clash is not None
    assert clash.detail == "nightly_fee_conflicts_with_per_stay_fee"
    assert "$50 nonrefundable pet fee per night" in clash.ladder_quote
    assert "$100.00" in clash.rate_quote


def test_the_conflicting_scalar_is_never_paired_with_the_other_statement_s_cap():
    """The $300 ceiling belongs to the $50 nightly rate. Publishing "$100 per
    stay, max $300" would state a total neither sentence supports."""
    facts, evidence, _b = extract_pet_facts(TOWNEPLACE)
    assert "pet_fee" not in facts and "fee_basis" not in facts
    assert "fee_cap" not in facts
    conflict = facts["fee_conflict"]
    assert conflict["detail"] == ["nightly_fee_conflicts_with_per_stay_fee"]
    assert len(conflict["quotes"]) == 2
    assert len([e for e in evidence if e["field"] == "fee_conflict"]) == 2
    assert facts["pets_allowed"] == "true"      # only the money is withheld


def test_a_cap_is_not_a_competing_fee():
    """"$50 per night, max $300 per stay" is one coherent term, not two."""
    assert nightly_versus_per_stay_conflict(
        "Pets welcome. $50 pet fee per night, max $300 per stay.") is None


def test_the_same_amount_stated_twice_is_not_a_conflict():
    assert nightly_versus_per_stay_conflict(
        "Pets welcome. $100 pet fee per night. Pet Fee Per Stay: $100.00") is None


@pytest.mark.parametrize("text", [
    "Pets welcome. $50 pet fee per night. Refundable deposit $200 per stay.",
    "Pets welcome. $50 pet fee per night. Damage charge per stay: $250.",
    "Pets welcome. $50 pet fee per night. Cleaning fee per stay: $95.",
])
def test_deposits_damage_and_cleaning_never_form_a_conflict(text):
    assert nightly_versus_per_stay_conflict(text) is None


def test_an_incidentals_deposit_is_not_an_ordinal_pet_fee():
    assert ordinal_pet_fees("Pets welcome. A refundable deposit of $80 for first "
                            "pet and $50 for second pet is held at check-in.") is None
