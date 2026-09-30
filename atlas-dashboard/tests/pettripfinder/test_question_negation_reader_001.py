"""PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001 -- a question is never acceptance; a refusal wins.

Pins the shared reader (``brightdata.policy_reading.parse``) and the first-party gate FAST rule C runs
(``first_party_binding.classify_quote``) on the order's cases A-H, the exact wording of the live and Austin quotes
that exposed the defect, and every counter-example the live-corpus scan found while the repair was measured (an
acceptance only the ANSWER states, and restrictions that are not refusals).
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as READER  # noqa: E402

ACCEPTANCE, REFUSAL, NEITHER = "ACCEPTANCE", "REFUSAL", "NEITHER"


def outcome(quote, context=""):
    if FPB.classify_quote(quote, kind=FPB.KIND_PET_FRIENDLY, context=context)[0] == FPB.ELIGIBLE:
        return ACCEPTANCE
    if FPB.classify_quote(quote, kind=FPB.KIND_NO_PETS, context=context)[0] == FPB.ELIGIBLE:
        return REFUSAL
    return NEITHER


ORDER_CASES = [
    ("A bare question", "Are pets allowed?", NEITHER),
    ("B explicit refusal", "Pets are not permitted.", REFUSAL),
    ("C refusal with ESA wording", "Pets, including emotional support animals, are not permitted.", REFUSAL),
    ("D explicit acceptance", "Pets are welcome.", ACCEPTANCE),
    ("E acceptance with fee", "Pets are welcome. A $50 per stay pet fee applies.", ACCEPTANCE),
    ("F question then yes", "Are pets allowed? Yes, dogs and cats are welcome.", ACCEPTANCE),
    ("G question then refusal", "Are pets allowed? No, pets are not permitted.", REFUSAL),
    ("H service animals only", "Pets are not allowed. Service animals are welcome.", REFUSAL),
]

#: The live and Austin first-party quotes, verbatim, that published the OPPOSITE of what they say.
LIVE_REFUSALS = [
    ("Kalahari Round Rock (Austin)", "Are pets allowed? | With the exception of service animals certified under the "
     "American Disabilities Act (ADA), pets (including ESAs) are not permitted at Kalahari Resorts & Conventions. "
     "Guests bringing animals that go against our pet policy will be asked to leave and will not be refunded."),
    ("Dolphin Hollywood", "You are welcome to smoke outdoors ​ Are Pets Allowed? Unfortunately, we do not accept "
     "pets at this time. besides pets with license as emotional support."),
    ("Honu Cove", "Is Honu Cove Pet Friendly? Pet Policy & ADA Service Animals Pets: Pets are strictly prohibited "
     "anywhere on property."),
    ("Mariner Motel", "Policies Are pets allowed? While we love animals, our properties are currently pet-free to "
     "ensure a hypoallergenic environment for all guests."),
    ("Bellweather Beach Resort", "Is the hotel pet friendly? Unfortunately, Bellwether Beach Resort is a pet-free "
     "facility. We accept service dogs and will require a signed pet agreement."),
    ("Bon Aire Motel Apts", "Are you pet friendly? No, we do not allow pets on the property."),
    ("Boutique Beach Retreat", "Is Boutique Beach Retreat pet friendly? Unfortunately, we can not allow pets at the "
     "hotel. Emotional support animals are considered pets, not service animals under the American Disabilities "
     "Act. We do not allow pets at this property."),
    ("Crystal Palms", "PETS: Pets and Emotional Support Animals are not allowed on property. Crystal Palms Beach "
     "Resort adheres to Federal ADA Law allowing ADA Compliant Services Animals. Is Crystal Palms Beach Resort "
     "pet-friendly?"),
    ("Sunset Vistas", "PETS: Pets and Emotional Support Animals are not allowed on property. Sunset Vistas Beachfront "
     "Suites adheres to Federal ADA Law allowing ADA Compliant Services Animals. Are pets allowed at Sunset Vistas "
     "Beachfront Suites? Unfortunately, pets aren’t allowed."),
    ("Hotel South Tampa", "Are pets allowed at the hotel? + To ensure the comfort of all our guests, we maintain a "
     "strict no-pet policy."),
    ("Island Palms", "Pets Are pets allowed at Island Palms Hotel? We are not a pet friendly hotel at Island Palms."),
    ("Pacific Terrace", "Pets Are pets allowed? Pacific Terrace Hotel is not a pet-friendly hotel."),
    ("Animals prohibited", "Animals are prohibited."),
    ("We do not allow pets", "We do not allow pets."),
]

#: Accepted ONLY through the question's words before the repair; the answer states no acceptance.
QUESTION_ONLY = [
    ("Clevelander South Beach", "Are you pet-friendly?"),
    ("Essex House", "Are pets allowed? Please contact the hotel directly for the most up-to-date pet policy."),
]

#: Acceptance the ANSWER states -- must survive the question rule.
ANSWER_ACCEPTANCES = [
    ("yes then welcome", "Is Halcyon pet friendly? Yes, we’d love to welcome your pet. Ten percent of every "
     "monthly pet fee is donated."),
    ("welcomes well-behaved", "‍ Is the hotel pet-friendly? Collins Court welcomes well-behaved dogs and cats."),
    ("yes!", "A pet friendly Savannah bed and breakfast? Yes! Just because you’re traveling doesn’t mean you "
     "have to leave your pets behind. Four-legged guests are always welcome at the Foley House Inn."),
    ("we only allow", "Is Roost pet friendly? We love pets! We only allow dogs and cats. We charge a cleaning fee up "
     "to $350 for all pets (depending on length of stay)."),
    ("always welcome", "Are Pets Allowed at AKA locations? Pets are always welcome at AKA locations."),
    ("four-legged companions", "Is Eau Resort & Spa dog-friendly? Eau Resort & Spa welcomes four-legged companions "
     "with no pet fee."),
    ("welcome up to N", "Is Cardozo Pet Friendly? We welcome up to 2 dogs, 50lbs max combined, at Cardozo South "
     "Beach! $150 per stay per pet fee will apply."),
]

#: Restrictions beside an acceptance -- never refusals.
NOT_REFUSALS = [
    ("room type", "Pets Allowed: Yes General: Pet Accommodation: 25.00 USD per night per pet. 2 Pets per room, we "
     "do not allow pets in our Kitchenette suite or our 2 room suite.. Service animals are permitted, without "
     "charge."),
    ("species", "DOG-FRIENDLY The Summit welcomes dogs under 50 pounds. Maximum (2) dogs per room. A non-refundable "
     "$50 fee applies. Please note we do not accept pets other than dogs."),
    ("rooms not pet friendly", "Do you allow pets? We only have 4 rooms that are pet friendly. Our oceanfront rooms "
     "are not pet friendly. Is there a pet fee? Yes, we have an additional $25 per night pet fee."),
    ("house rule", "Pets are welcome. Pets are not allowed to be left alone in room."),
    ("count limit", "Pets are welcome. We cannot accommodate more than 2 pets per room."),
]


@pytest.mark.parametrize("label,quote,want", ORDER_CASES, ids=[c[0] for c in ORDER_CASES])
def test_order_cases(label, quote, want):
    assert outcome(quote) == want


@pytest.mark.parametrize("label,quote", LIVE_REFUSALS, ids=[c[0] for c in LIVE_REFUSALS])
def test_live_refusals_read_as_refusals(label, quote):
    reading = READER.parse(quote)
    assert reading.pets_allowed is False, reading.pets_allowed_quote
    assert outcome(quote) == REFUSAL
    assert FPB.classify_quote(quote, kind=FPB.KIND_PET_FRIENDLY)[0] != FPB.ELIGIBLE


@pytest.mark.parametrize("label,quote", QUESTION_ONLY, ids=[c[0] for c in QUESTION_ONLY])
def test_question_only_is_never_acceptance_and_never_refusal(label, quote):
    assert READER.parse(quote).pets_allowed is None
    assert outcome(quote) == NEITHER


@pytest.mark.parametrize("label,quote", ANSWER_ACCEPTANCES, ids=[c[0] for c in ANSWER_ACCEPTANCES])
def test_an_answer_still_states_acceptance(label, quote):
    assert READER.parse(quote).pets_allowed is True
    assert outcome(quote) == ACCEPTANCE


@pytest.mark.parametrize("label,quote", NOT_REFUSALS, ids=[c[0] for c in NOT_REFUSALS])
def test_restrictions_are_not_refusals(label, quote):
    assert READER.parse(quote).pets_allowed is True


def test_a_chip_before_an_all_caps_question_is_not_inside_it():
    context = ("Weight limit of 50 lbs Limit of 2 Dogs No Cats ARE PETS ALLOWED AT WOODSPRING SUITES HOLLAND - GRAND "
               "RAPIDS? Service Animals are welcome at no additional charge, must be registered upon arrival.")
    assert FPB.classify_quote("PETS ALLOWED", kind=FPB.KIND_PET_FRIENDLY, context=context)[0] == FPB.ELIGIBLE


def test_species_named_in_a_question_is_not_accepted():
    assert READER.parse("Are dogs allowed?").pets_allowed is None
    assert READER.parse("Are dogs allowed? Yes, dogs are welcome.").pets_allowed is True


def test_yes_to_a_pet_free_room_question_is_not_acceptance():
    reading = READER.parse("Do you have pet-free rooms for those with allergies? Yes, we do.")
    assert reading.pets_allowed is not True


def test_we_allow_our_four_legged_friends_is_acceptance():
    quote = ("Do you have pet-free rooms for those with allergies? Yes, we allow our four legged friends to sleep "
             "in two buildings leaving the other three buildings pet-free.")
    assert READER.parse(quote).pets_allowed is True


def test_a_yes_limited_to_service_animals_is_not_acceptance():
    reading = READER.parse("Are pets allowed? Yes, service animals only.")
    assert reading.pets_allowed is not True
