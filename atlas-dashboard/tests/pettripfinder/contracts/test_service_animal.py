"""PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 -- exemption language wins.

The defect these tests exist to make un-repeatable
--------------------------------------------------
Four LIVE Milwaukee profiles published "service animals are welcome and that a
charge applies" from sources that said the opposite. The classifier's fallback
asked only whether the WORD "fee" or "charge" appeared anywhere in the
sentence -- and an exemption sentence always contains one, because it has to
name what it exempts you from.

So the first test below is the four published sentences themselves, asserted
by the exact strings that shipped. If the rule ever regresses to a token
match, those four fail before anything else does.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import service_animal as SA

#: The exact sentences behind the four wrong live profiles, and the two other
#: Milwaukee phrasings that were already right and must stay right.
LIVE_MILWAUKEE_SENTENCES = (
    ("We charge 50.00 per pet, per night, except ADA Service Animals.",
     "avid hotels oak creek"),
    ("Service animals will be exempt from this charge.",
     "extended stay america milwaukee waukesha"),
    ("Service animals will be exempt from this charge.",
     "extended stay america milwaukee wauwatosa"),
    ("Service animals are allowed, with no pet fee required for service "
     "animals.", "the pfister hotel"),
)

EXEMPTIONS = (
    # The four required positive cases, verbatim from the work order.
    "Service animals will be exempt from this charge.",
    "No pet fee required for service animals.",
    "Pet fee applies except ADA Service Animals.",
    "Service animals are permitted, without charge.",
    # The phrasings already live in other markets, which must not move.
    "Service Animals - ADA-defined service animals are welcome free of charge.",
    "Max 40 Pounds Service animals are permitted, without charge.",
    # Other ways a source says the same thing.
    "Service animals are exempt from the pet fee.",
    "The pet fee is waived for service animals.",
    "Service animals are not subject to the pet fee.",
    "Service animals stay at no additional charge.",
    "Service animals are never charged a pet fee.",
    "Service animals are welcome; there is no charge.",
    "ADA service animals are complimentary.",
    "A $75 pet fee applies to all pets. Service animals are exempt.",
    "Guide dogs are accommodated at no cost.",
    # Corpus phrasings that reach no other exemption pattern. All three were
    # live in the store when this work order ran, and all three used to
    # publish as "a charge applies".
    "Non refundable pet fee 75 USD, not applicable to service animals.",
    "Pet fee $20/day with $100/stay nonrefundable clean fee excludes Service "
    "Animals",
    "The pet fee does not apply to service animals.",
    "There is a non-refundable pet fee of $25 per day applies for the first 6 "
    "days, and $15 per day thereafter except for service animals.",
    "While all of our extended stay hotels welcome eligible service animals "
    "at no additional charge, we also offer pet-friendly hotel rooms.",
)

CHARGES = (
    "Service animals are subject to the same $50 per night pet fee as any "
    "other animal.",
    "Service animals are charged $75 per stay.",
    "A $50 pet fee applies to service animals.",
    "We charge a $100 cleaning fee for service animals.",
    "Service animals incur the standard pet fee.",
    "Service animals are subject to the nightly pet charge.",
)

ALLOWED_ONLY = (
    # The live phrasing that carries no fee claim at all.
    "Service Animals - ADA-defined service animals welcome.",
    "Pets allowed Service animals allowed Pet walking area onsite",
    "Service animals are welcome.",
    # "fee" and "charge" present, but never attached to the animal.
    "Service animals are welcome. A $50 nightly pet fee applies to all pets.",
    "A resort charge of $30 is added nightly; service animals are welcome.",
    "Pets are $25 per night. Service animals are always welcome.",
    # Two live corpus lines that carry a fee in an unrelated clause. Both used
    # to publish as "a charge applies".
    "Pets allowed Service animals allowed Pet walking area onsite Pet fee per "
    "night: 50 USD",
    "Smoking indoors will incur a $250 cleaning fee. Do you allow pets? Only "
    "ADA service animals are allowed.",
    # "exclude" that belongs to something other than the animal.
    "Rates exclude taxes. Service animals are welcome.",
)

SILENT = (
    "",
    "   ",
    None,
    # A fee sentence that never mentions the animal at all.
    "Pets are welcome for a $25 fee.",
    "A $30 nightly resort charge applies to every reservation.",
)


# --------------------------------------------------------------------------- #
# The regression that must never recur.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("sentence,identity", LIVE_MILWAUKEE_SENTENCES)
def test_the_four_live_milwaukee_sentences_are_never_a_charge(sentence, identity):
    reading = SA.classify(sentence)
    assert reading.interpretation == SA.EXEMPT_FROM_PET_CHARGE, identity
    assert reading.charges_stated == enums.SERVICE_ANIMAL_NO_CHARGE, identity
    assert reading.charges_stated != enums.SERVICE_ANIMAL_CHARGE_STATED


def test_the_old_token_fallback_would_have_failed_these():
    """The defect, reproduced, so the fix is measured against it and not a story.

    This is the exact rule that shipped: a check for an affirmative no-charge
    phrase, then a bare token match on "fee" or "charge". Every one of the
    four live sentences reaches the second branch, which is why four profiles
    published the opposite of what their source said.
    """
    import re

    def old_rule(text):
        lowered = text.lower()
        if re.search(r"without\s+charge|no\s+charge|free\s+of\s+charge", lowered):
            return enums.SERVICE_ANIMAL_NO_CHARGE
        if re.search(r"\bfee\b|\bcharge\b", lowered):
            return enums.SERVICE_ANIMAL_CHARGE_STATED
        return enums.SERVICE_ANIMAL_NOT_ADDRESSED

    for sentence, identity in LIVE_MILWAUKEE_SENTENCES:
        assert old_rule(sentence) == enums.SERVICE_ANIMAL_CHARGE_STATED, identity
        assert SA.charges_stated(sentence) == enums.SERVICE_ANIMAL_NO_CHARGE


# --------------------------------------------------------------------------- #
# The four categories.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("sentence", EXEMPTIONS)
def test_exemption_language_reads_as_an_exemption(sentence):
    reading = SA.classify(sentence)
    assert reading.interpretation == SA.EXEMPT_FROM_PET_CHARGE, reading.reason
    assert reading.charges_stated == enums.SERVICE_ANIMAL_NO_CHARGE


@pytest.mark.parametrize("sentence", CHARGES)
def test_a_charge_bound_to_the_animal_still_reads_as_a_charge(sentence):
    reading = SA.classify(sentence)
    assert reading.interpretation == SA.CHARGE_EXPLICITLY_APPLIES, reading.reason
    assert reading.charges_stated == enums.SERVICE_ANIMAL_CHARGE_STATED


@pytest.mark.parametrize("sentence", ALLOWED_ONLY)
def test_acceptance_without_a_fee_claim_never_becomes_a_fee_claim(sentence):
    reading = SA.classify(sentence)
    assert reading.interpretation == SA.ALLOWED, reading.reason
    assert reading.charges_stated == enums.SERVICE_ANIMAL_NOT_ADDRESSED


@pytest.mark.parametrize("sentence", SILENT)
def test_silence_is_never_interpreted(sentence):
    reading = SA.classify(sentence)
    assert reading.interpretation == SA.SOURCE_SILENT, reading.reason
    assert reading.charges_stated == enums.SERVICE_ANIMAL_NOT_ADDRESSED


# --------------------------------------------------------------------------- #
# The rule itself.
# --------------------------------------------------------------------------- #

def test_a_bare_fee_or_charge_token_can_never_conclude_a_charge():
    """The whole defect in one assertion.

    Restricted to the sentences that actually CONTAIN the trigger token, so
    the assertion is about the token and not about the sample.
    """
    tokens = ("fee", "charge", "cost")
    carrying = [s for s in EXEMPTIONS + ALLOWED_ONLY
                if any(t in s.lower() for t in tokens)]
    assert len(carrying) >= 10, "the sample must exercise the trigger token"
    for sentence in carrying:
        assert SA.charges_stated(sentence) != enums.SERVICE_ANIMAL_CHARGE_STATED


def test_exemption_wins_when_a_sentence_states_both():
    """A sentence naming a charge AND exempting the animal is an exemption."""
    both = ("Pets are charged a $50 per night pet fee; service animals are "
            "exempt from this charge.")
    assert SA.classify(both).interpretation == SA.EXEMPT_FROM_PET_CHARGE


def test_a_charge_in_a_neighbouring_sentence_does_not_attach_to_the_animal():
    assert SA.classify(
        "Service animals are welcome. A $50 pet fee applies to dogs."
    ).interpretation == SA.ALLOWED


def test_every_interpretation_maps_onto_the_published_enum():
    for interpretation in SA.INTERPRETATIONS:
        wire = SA.Reading(interpretation, "test").charges_stated
        assert wire in enums.SERVICE_ANIMAL_CHARGE_STATES


def test_the_reading_always_names_the_rule_that_produced_it():
    for sentence in EXEMPTIONS + CHARGES + ALLOWED_ONLY:
        assert SA.classify(sentence).reason.strip()


def test_classification_is_insensitive_to_case_and_whitespace():
    spaced = "  Service   animals\nwill be\tEXEMPT from this charge.  "
    assert SA.classify(spaced).interpretation == SA.EXEMPT_FROM_PET_CHARGE
    assert SA.classify("SERVICE ANIMALS ARE PERMITTED, WITHOUT CHARGE.") \
        .interpretation == SA.EXEMPT_FROM_PET_CHARGE
