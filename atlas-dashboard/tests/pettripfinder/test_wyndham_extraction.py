"""PTF-CAPTURE-004B -- reading a Wyndham pet policy without flattening it.

Two properties, two policies that differ in ways a careless extractor erases:

  West-Hilliard: dogs only, 25 USD PER PET per night
  Dublin:        cats and dogs, 25 USD nightly FOR UP TO 2 PETS

Same number, different policy. Two dogs cost 50 a night at West-Hilliard and 25
at Dublin, so publishing both as "$25 per night" understates one of them by
half. That is the tier-flattening error in a new costume, and most of this file
exists to keep the two apart.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.promote_attested_candidates import extract_pet_facts
from scripts.pettripfinder.prose_facts import (
    extract_fee_cap, extract_fee_with_basis, extract_species,
)


#: PTF-RENDERER-FIDELITY-001 §9. An amount and a recurrence with no stated
#: scope is only half a rule; the profile says so rather than letting it read
#: as a complete answer. Omitted at a one-pet limit, where per-pet and
#: per-room are the same arithmetic.
DISCLOSURE = "; the source does not say whether this is charged per pet or per room"

WEST_HILLIARD = (
    "Pet & Service Animal Policy Service Animals - ADA-defined service animals "
    "are welcome free of charge. Dogs Allowed - 2 dogs max. 75lbs or less per "
    "pet. Fees - 25 USD per pet per night. Max 75 USD per stay. Other "
    "Information - Contact hotel for additional details and availability.")

DUBLIN = (
    "Pet & Service Animal Policy Service Animals - ADA-defined service animals "
    "are welcome free of charge. Pets Allowed - 2 pets max. Cats and dogs only. "
    "75lbs or less per pet. Fees - Non-refundable 25 USD nightly for up to 2 "
    "pets. Max 75 USD per stay. Other Information - Contact hotel for "
    "additional details and availability.")


# --------------------------------------------------------------------------- #
# The two hotels, end to end.
# --------------------------------------------------------------------------- #

def test_west_hilliard_extracts_the_stated_policy():
    facts, evidence, _ = extract_pet_facts(WEST_HILLIARD)
    assert facts["species_allowed"] == "dogs"
    assert facts["pet_count_limit"] == "2"
    assert facts["weight_limit"] == "75.0 pounds"
    assert "weight_limit_operator" not in facts        # "75lbs or LESS" includes 75
    assert facts["pet_fee"] == "$25.00"
    assert facts["fee_basis"] == "per pet per night"
    assert facts["fee_cap"]["amount"] == "75.00"
    assert facts["pets_allowed"] == "true"
    assert "fee_withheld" not in facts


def test_dublin_extracts_the_stated_policy():
    facts, evidence, _ = extract_pet_facts(DUBLIN)
    assert facts["species_allowed"] == "dogs, cats"
    assert facts["pet_count_limit"] == "2"
    assert facts["weight_limit"] == "75.0 pounds"
    assert facts["pet_fee"] == "$25.00"
    assert facts["fee_basis"] == "per night for up to 2 pets"
    assert facts["fee_cap"]["amount"] == "75.00"
    assert "fee_withheld" not in facts


def test_the_two_fee_bases_are_not_collapsed():
    """The single most important assertion in this file."""
    wh, _, _ = extract_pet_facts(WEST_HILLIARD)
    du, _, _ = extract_pet_facts(DUBLIN)
    assert wh["pet_fee"] == du["pet_fee"] == "$25.00"
    assert wh["fee_basis"] != du["fee_basis"]
    assert "per pet" in wh["fee_basis"]
    assert "per pet" not in du["fee_basis"]
    assert "up to 2 pets" in du["fee_basis"]


def test_every_published_fact_is_backed_by_a_quote():
    for text in (WEST_HILLIARD, DUBLIN):
        facts, evidence, _ = extract_pet_facts(text)
        quoted = {e["field"] for e in evidence}
        for field in ("pet_fee", "fee_basis", "weight_limit", "pet_count_limit",
                      "species_allowed"):
            assert field in quoted, field
        for e in evidence:
            assert e["quote"].strip(), e
            # the quote is really from the source, not paraphrased
            assert e["quote"].strip(" .") in " ".join(text.split())


def test_nothing_unstated_is_invented():
    """The source states no deposit, no breed rule and no unattended-pet rule.
    Absent must stay absent."""
    for text in (WEST_HILLIARD, DUBLIN):
        facts, _, _ = extract_pet_facts(text)
        for field in ("pet_deposit", "breed_restrictions", "unattended_policy",
                      "fee_tiers"):
            assert field not in facts, field


# --------------------------------------------------------------------------- #
# Species.
# --------------------------------------------------------------------------- #

def test_dogs_allowed_label_means_dogs_only():
    got = extract_species("Dogs Allowed - 2 dogs max.")
    assert got is not None and got.value == "dogs"


def test_cats_and_dogs_only_means_both():
    got = extract_species("Pets Allowed - 2 pets max. Cats and dogs only.")
    assert got is not None and got.value == "dogs, cats"


def test_a_generic_pets_allowed_label_names_no_species():
    """"Pets Allowed" says nothing about which animals. Reading a species out
    of it would publish a restriction the hotel never stated."""
    assert extract_species("Pets Allowed - 2 pets max.") is None


def test_a_service_animal_sentence_is_not_a_species_permission():
    """Every Wyndham block opens with "ADA-defined service animals are welcome".
    A hotel that takes guide dogs has told you nothing about pets, and the
    site treats service animals as a separate legal category everywhere else."""
    assert extract_species(
        "Service Animals - ADA-defined service animals are welcome free of "
        "charge.") is None
    assert extract_species("Service dogs are welcome free of charge.") is None


def test_service_animal_text_does_not_mask_a_real_permission():
    """The guard removes service sentences; it must not remove the policy."""
    got = extract_species(
        "Service Animals - ADA-defined service animals are welcome free of "
        "charge. Dogs Allowed - 2 dogs max.")
    assert got is not None and got.value == "dogs"


# --------------------------------------------------------------------------- #
# Money without a dollar sign.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text,amount", [
    ("Fees - 25 USD per pet per night.", "$25.00"),
    ("Fees - 25 usd per night.", "$25.00"),
    ("Fee - 30 dollars per stay.", "$30.00"),
    ("Fees - $40.00 per night.", "$40.00"),
    ("Fees - 1,250 USD per stay.", "$1250.00"),
])
def test_unsigned_currency_amounts_are_parsed(text, amount):
    got = extract_fee_with_basis(text)
    assert got is not None and got.value == amount


def test_a_cap_is_not_harvested_as_the_rate():
    """"Max 75 USD per stay" is a ceiling. Reading it as the fee would publish
    75 a night for a hotel charging 25."""
    got = extract_fee_with_basis("Fees - 25 USD per pet per night. Max 75 USD per stay.")
    assert got.value == "$25.00"
    cap = extract_fee_cap("Fees - 25 USD per pet per night. Max 75 USD per stay.")
    assert cap.value == "$75.00"


def test_a_fee_with_no_stated_basis_yields_no_basis():
    """An amount is a fact; a basis nobody stated is not."""
    got = extract_fee_with_basis("Fees - 25 USD.")
    assert got is not None and got.value == "$25.00"
    assert got.operator == ""


# --------------------------------------------------------------------------- #
# Regressions caught while building this. Both would have changed LIVE records.
# --------------------------------------------------------------------------- #

STAYBRIDGE = (
    "Can I bring my pet to Staybridge Suites Columbus-Dublin? Pets are welcome "
    "at Staybridge Suites Columbus-Dublin. Our Pet Policy: This is a dog only "
    "hotel. Up to two friendly pups under 80 lbs are welcome. Pet fee per pet "
    "is 75 to 150 dollars depending on length of stay of reservation.")

ALOFT = (
    "Pet Policy Pets Welcome 2 pets 50lbs max per room w/non refundable fee "
    "contact for details max $150/stay Non-Refundable Pet Fee Per Night: $50.00 "
    "Maximum Pet Weight: 50.0lbs Maximum Number of Pets in Room: 2")


def test_a_stated_range_still_outranks_a_prose_scalar():
    """Staybridge is live with its fee WITHHELD. Teaching the extractor to read
    "75 to 150 dollars" as money made it publish $150 -- the high end of a
    range, presented as the price. The range check has to run first."""
    facts, _, _ = extract_pet_facts(STAYBRIDGE)
    assert "pet_fee" not in facts
    assert facts["fee_withheld"]["reason"].startswith("unrepresentable_fee_range")
    assert facts["species_allowed"] == "dogs"
    assert facts["weight_limit"] == "80.0 pounds"
    assert facts["weight_limit_operator"] == "lt"


def test_a_labelled_fee_still_outranks_prose():
    """Aloft is live at $50.00 per night with a $150 cap. Prose fills gaps; it
    never overwrites a labelled value."""
    facts, _, _ = extract_pet_facts(ALOFT)
    assert facts["pet_fee"] == "$50.00"
    assert facts["fee_basis"] == "per night"
    assert facts["fee_cap"]["amount"] == "150.00"
    assert "species_allowed" not in facts       # the source names no species


# --------------------------------------------------------------------------- #
# Public wording for a room-scoped nightly fee.
# --------------------------------------------------------------------------- #

DUBLIN_FACTS = {"species_allowed": "dogs, cats", "pet_fee": "$25.00",
                "fee_basis": "per night for up to 2 pets", "pet_count_limit": "2",
                "weight_limit": "75.0 pounds", "pets_allowed": "true",
                "fee_cap": {"amount": "75.00", "currency": "USD"}}
WH_FACTS = {"species_allowed": "dogs", "pet_fee": "$25.00",
            "fee_basis": "per pet per night", "pet_count_limit": "2",
            "weight_limit": "75.0 pounds", "pets_allowed": "true",
            "fee_cap": {"amount": "75.00", "currency": "USD"}}


def test_a_room_scoped_nightly_fee_reads_naturally():
    """"applies per night for up to 2 pets, up to a maximum of $75" stacks two
    "up to" phrases for two different quantities. Say it directly instead."""
    from scripts.pettripfinder.hotel_profile import _verified_summary
    s = _verified_summary(DUBLIN_FACTS, "")
    assert "A $25 nightly fee covers up to 2 pets and is capped at $75 per stay." in s
    assert "up to a maximum of" not in s
    assert "per pet" not in s


def test_the_per_pet_basis_keeps_its_original_wording():
    from scripts.pettripfinder.hotel_profile import _verified_summary
    s = _verified_summary(WH_FACTS, "")
    assert "A $25 fee applies per pet per night, up to a maximum of $75." in s


def test_a_plain_per_night_fee_is_unaffected():
    """Aloft and every other published hotel keep the sentence they have."""
    from scripts.pettripfinder.hotel_profile import _verified_summary
    s = _verified_summary({"pets_allowed": "true", "pet_fee": "$50.00",
                           "fee_basis": "per night", "pet_count_limit": "2",
                           "weight_limit": "50.0 pounds",
                           "fee_cap": {"amount": "150.00", "currency": "USD"}}, "")
    assert "A $50 fee applies per night, up to a maximum of $150" in s


def test_the_structured_basis_is_untouched_by_the_wording_choice():
    """Prose is a rendering decision. The stored basis, the chip and the
    comparison cell still carry the exact structured string."""
    from scripts.pettripfinder.hotel_profile import _verified_details, _verified_facts
    chips = dict((lab, val) for lab, val, _ in _verified_facts(DUBLIN_FACTS))
    assert chips["Charge basis"] == "Per night for up to 2 pets"
    rows = dict((lab, val) for lab, val, _ in _verified_details(DUBLIN_FACTS)[0])
    assert rows["Charge basis"] == "Per night for up to 2 pets"
    assert DUBLIN_FACTS["fee_basis"] == "per night for up to 2 pets"


def test_the_wording_follows_the_basis_shape_not_the_hotel():
    """Any policy stating this basis reads the same way -- no hotel literal."""
    from scripts.pettripfinder.hotel_profile import _verified_summary
    other = dict(DUBLIN_FACTS, fee_basis="per night for up to 3 pets",
                 pet_count_limit="3")
    assert "covers up to 3 pets" in _verified_summary(other, "")
