"""PTF-LOUISVILLE-FOUNDER-REMEDIATION-005 -- eleven things a reader read wrongly,
each caught by asking a persisted block what it says.

Every block below is verbatim from a Louisville capture. Each repair is paired
with the control that must not move: a reader that reads MORE is not
automatically safer, and every one of these rules had a way to be too generous.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.contracts import enums


def read(text, strategy="static_html_walk"):
    return PR.to_extraction(PR.parse(text, strategy=strategy), location="b")


def facts(text, **kwargs):
    return dict(read(text, **kwargs).extraction)


def withheld(text, **kwargs):
    return dict(read(text, **kwargs).withheld)


def flag_codes(text, **kwargs):
    return {f["code"] for f in read(text, **kwargs).flags}


# --------------------------------------------------------------------------- #
# A fee and a deposit that are the same number
# --------------------------------------------------------------------------- #

class TestFeeAndDepositShareAnAmount:
    BLOCK = "Pet fee per night: 40 USD Pet damage deposit: 40 USD"

    def test_both_charges_are_read(self):
        """IHG Louisville East/Hurstbourne. A guest pays both, and the record
        carried one: the pass that reads labelled amounts skipped any amount
        already explained, and forty dollars had been explained once."""
        result = facts(self.BLOCK)
        assert result["pet_fee"] == 4000
        assert result["pet_deposit"] == 4000

    def test_one_charge_stated_twice_is_still_one_charge(self):
        result = facts("Pet fee per night: 40 USD. The pet fee is 40 USD.")
        assert result["pet_fee"] == 4000
        assert "pet_deposit" not in result


# --------------------------------------------------------------------------- #
# Weights and counts the patterns did not have
# --------------------------------------------------------------------------- #

class TestStatedLimits:
    def test_a_weight_limit_with_no_connector_is_read(self):
        assert facts("Weight limit 50 lbs, limit of two dogs in room.")[
            "weight_limit"] == {"value": 50.0, "unit": "lb"}

    def test_a_word_number_and_a_species_are_a_count(self):
        assert facts("Weight limit 50 lbs, limit of two dogs in room.")[
            "pet_count_limit"] == 2

    def test_a_count_stated_as_an_allowance_is_read(self):
        result = facts("One pet is allowed per room, with a maximum weight of "
                       "25.0 lbs.")
        assert result["pet_count_limit"] == 1
        assert result["pet_count_scope"] == "per_room"

    def test_a_bare_allowance_count_is_read(self):
        assert facts("Pet weight limit: 80 lbs 2 pets allowed")[
            "pet_count_limit"] == 2

    def test_a_compressed_cell_states_a_count(self):
        assert facts("$75(1-4n),$125(5+n)2petsMax total 75lb")[
            "pet_count_limit"] == 2

    def test_a_room_occupancy_is_not_a_pet_count(self):
        assert "pet_count_limit" not in facts(
            "Maximum occupancy 4 guests. Pets are welcome.")


class TestWeightsThatMustNotBePublished:
    def test_a_weight_no_pet_has_is_withheld_and_quoted(self):
        """Marriott's own page for Residence Inn Louisville Airport."""
        block = ("Yes, pets are welcome. Up to 3 pets are allowed per room. "
                 "Each pet may weigh up to 900.0 lbs.")
        assert "weight_limit" not in facts(block)
        assert withheld(block)["weight_limit"] == enums.SOURCE_AMBIGUOUS
        detail = next(f["detail"] for f in read(block).flags
                      if f["code"] == "FLAG_WEIGHT_IMPLAUSIBLE")
        assert "900" in detail

    def test_a_large_but_real_weight_still_publishes(self):
        assert facts("Pets are welcome. Maximum weight of 150 lbs.")[
            "weight_limit"] == {"value": 150.0, "unit": "lb"}

    def test_a_weight_with_no_unit_is_withheld_rather_than_dropped(self):
        block = "Pet fee per night: 150 USD Pet weight limit: 80 2 pets allowed"
        assert "weight_limit" not in facts(block)
        assert withheld(block)["weight_limit"] == enums.SOURCE_AMBIGUOUS
        assert "FLAG_WEIGHT_NOT_USABLE" in flag_codes(block)

    def test_a_combined_weight_is_withheld_rather_than_dropped(self):
        block = "Pets allowed Yes. $75(1-4n),$125(5+n)2petsMax total 75lb"
        assert "weight_limit" not in facts(block, strategy="generic_signal_walk")
        assert withheld(block, strategy="generic_signal_walk")["weight_limit"] \
            == enums.SOURCE_AMBIGUOUS

    def test_an_individual_weight_beside_a_combined_one_still_publishes(self):
        block = ("Individual pet weight limit : 50 lbs. Maximum combined "
                 "weight 100 lbs.")
        assert facts(block)["weight_limit"] == {"value": 50.0, "unit": "lb"}


# --------------------------------------------------------------------------- #
# A price the record said was not stated
# --------------------------------------------------------------------------- #

class TestPricesTheReaderMissed:
    def test_a_label_with_two_qualifier_words_is_still_a_label(self):
        """Hilton's Seelbach: "There is a $100.00 non-refundable pet fee"."""
        assert facts("Yes, pets are allowed. There is a $100.00 non-refundable "
                     "pet fee, and the maximum weight limit is 75 lbs.",
                     strategy="generic_signal_walk")["pet_fee"] == 10000

    def test_an_unbound_pet_amount_is_ambiguous_and_not_silence(self):
        """Staybridge Louisville Expo prices a bounded stay and no ladder can
        carry one rung, so nothing is published -- but the source is not
        silent, and the record used to say it was."""
        block = ("Pets are welcome at Staybridge Suites. Our Pet Policy: "
                 "1 to 6 nights: 75 USD")
        assert "pet_fee" not in facts(block)
        assert withheld(block)["pet_fee"] == enums.SOURCE_AMBIGUOUS
        assert "FLAG_PET_AMOUNT_NOT_BOUND" in flag_codes(block)

    def test_a_page_that_prices_nothing_is_still_silent(self):
        block = "Pets are welcome at this hotel. Up to 2 pets are allowed."
        assert withheld(block)["pet_fee"] == enums.SOURCE_SILENT

    def test_a_parking_fee_is_not_a_pet_amount(self):
        block = ("Yes, pets are welcome. Up to 2 pets are allowed per room. "
                 "The daily valet fee is $50.00 per day.")
        assert withheld(block)["pet_fee"] == enums.SOURCE_SILENT


# --------------------------------------------------------------------------- #
# One charge, two bases
# --------------------------------------------------------------------------- #

class TestContradictedBasis:
    BLOCK = ("Pets are welcome. Subject to a 75 USD pet fee per stay. "
             "Pet fee per night: 75 USD")

    def test_the_amount_stands_and_the_basis_is_withheld(self):
        assert facts(self.BLOCK)["pet_fee"] == 7500
        assert "fee_basis" not in facts(self.BLOCK)
        assert withheld(self.BLOCK)["fee_basis"] == enums.SOURCE_CONTRADICTORY

    def test_a_nightly_fee_with_a_per_stay_ceiling_is_not_a_contradiction(self):
        block = ("Service Animals - ADA-defined service animals are welcome "
                 "free of charge. / Dogs Allowed - 2 dogs max. 75lbs or less "
                 "per pet. / Fees - 25 USD per pet per night. Max 75 USD per "
                 "stay.")
        result = facts(block)
        assert result["fee_basis"] == enums.BASIS_PER_NIGHT
        assert result["fee_cap"]["amount_minor"] == 7500

    def test_two_statements_of_one_basis_are_not_a_contradiction(self):
        block = ("A non refundable fee is required in the amount of 40 dollars "
                 "per night per pet. Pet fee per night: 40 USD")
        assert facts(block)["fee_basis"] == enums.BASIS_PER_NIGHT


# --------------------------------------------------------------------------- #
# A species acceptance is an acceptance
# --------------------------------------------------------------------------- #

class TestSpeciesAcceptance:
    SELLERSBURG = ("A maximum of 2 dogs up to 15 lbs each are allowed for a "
                   "non-refundable charge of 20.00 USD per pet per night. "
                   "Sorry no other pets are allowed. ADA-defined service "
                   "animals are also welcome at this hotel.")

    def test_a_counted_species_allowance_reads_completely(self):
        """Days Inn Sellersburg stated the species, the count, the weight and
        the price, and the record carried none of them: the acceptance was not
        adjacent to the word "dogs", so the following "no other pets" clause
        made the surface look self-contradictory."""
        result = facts(self.SELLERSBURG)
        assert result["pets_allowed"] is True
        assert result["species_allowed"] == ["dog"]
        assert result["pet_count_limit"] == 2
        assert result["weight_limit"] == {"value": 15.0, "unit": "lb"}
        assert result["pet_fee"] == 2000

    def test_a_service_animal_sentence_is_never_a_species_acceptance(self):
        """The near-miss this corpus already has: reading it the other way
        publishes a no-pets hotel as pet-friendly."""
        assert facts("Service animals are welcome. No other pets are "
                     "allowed.")["pets_allowed"] is False

    @pytest.mark.parametrize("block", [
        "Dogs are not allowed at this property.",
        "No dogs allowed.",
        "Sorry, no pets are allowed at this hotel.",
    ])
    def test_a_refusal_never_becomes_an_acceptance(self, block):
        assert facts(block).get("pets_allowed") is not True

    def test_a_refused_species_is_not_an_affirmed_one(self):
        """"No dogs allowed" contains "dogs allowed", and that was enough to
        list dog among the species this property accepts."""
        assert "species_allowed" not in facts("No dogs allowed.")
