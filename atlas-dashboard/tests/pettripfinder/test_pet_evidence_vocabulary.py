# -*- coding: utf-8 -*-
"""The shared ordinary-pet evidence vocabulary.

PTF-GENERIC-EVIDENCE-VOCABULARY-AND-GUARD-SCOPE-REPAIR-023 extended this
vocabulary because it had been tuned on brand pages that write "Pets Allowed"
and could not read how an independent hotel actually speaks -- "we are a
pet-friendly hotel", "dog-friendly accommodations", "we welcome pets". Seven
Detroit properties stating fees, weights and counts scored as no evidence at
all.

The danger in widening it is obvious and this file exists to hold the line on
all four ways it could go wrong:

  1. a REFUSAL read as an acceptance ("we are not a pet-friendly property"),
  2. MARKETING prose promoted to policy ("Four-Legged Friends Welcome"),
  3. a QUESTION read as an answer ("Are pets allowed?"),
  4. SILENCE read as a refusal.

Every case below is real captured text from this product, not invented.
"""
from __future__ import annotations

import pytest

from scripts.pettripfinder import (
    detroit_ann_arbor_candidate_reconciliation_011 as R)


# --------------------------------------------------------------------------- #
# 1. POSITIVE: real first-party acceptance that states operational terms.
# --------------------------------------------------------------------------- #

ACCEPTS_WITH_TERMS = [
    ("shinola",
     "For your furry family members, we offer dog-friendly accommodations for "
     "up to two dogs with no weight or breed restrictions for a $125 + tax "
     "pet fee."),
    ("inn on ferry street",
     "We are a pet-friendly hotel and welcome pets up to 75 lbs. for an "
     "additional fee of $50."),
    ("hyatt house royal oak",
     "We Are Pet Friendly. We are happy to welcome your traveling canine "
     "companions at our dog-friendly hotel. Your dog must be house trained "
     "and the weight limit is 25 pounds each. Pets are limited to two per "
     "room."),
    ("roost detroit",
     "Is Roost pet friendly? We love pets! In the interest of security and "
     "safety for all our guests, we do not allow pets over 40 lbs. We only "
     "allow dogs. We charge a cleaning fee up to $350 per pet (depending on "
     "length of stay)."),
    ("extended stay america",
     "Is Extended Stay America Detroit - Farmington Hills pet friendly? Yes. "
     "Extended Stay America Detroit - Farmington Hills offers pet-friendly "
     "rooms, so you can bring your furry companion along for your stay. | "
     "Pet fees: Not to exceed a $25.00 per day cleaning fee plus tax, for the "
     "first six (6) nights, per pet."),
]

#: Wording the ORIGINAL set already read correctly. These must keep working --
#: a repair that fixes new phrasings and breaks the old ones is not a repair.
ALREADY_WORKED = [
    ("brand plain", "Pets are welcome. Pet fee per stay: $75.00"),
    ("species specific", "Dogs Allowed Dogs only / 25USD pet per night"),
    ("count", "Maximum of 2 pets per room."),
]


@pytest.mark.parametrize("name,block", ACCEPTS_WITH_TERMS)
def test_first_party_acceptance_with_terms_is_readable(name, block):
    affirmative, grade = R.has_affirmative_pets(block)
    assert affirmative is True, name
    assert grade in ("STRONG", "SOFT_WITH_TERMS"), (name, grade)


@pytest.mark.parametrize("name,block", ALREADY_WORKED)
def test_previously_readable_wording_still_reads(name, block):
    affirmative, _grade = R.has_affirmative_pets(block)
    assert affirmative is True, name


# --------------------------------------------------------------------------- #
# 2. NEGATIVE: marketing prose is not a policy.
# --------------------------------------------------------------------------- #

MARKETING_ONLY = [
    ("royal park",
     "Pet-Friendly Hotel in Rochester Four-Legged Friends Welcome Royal Park "
     "Hotel invites you to bring along your canine companion for a playful "
     "dog day afternoon."),
    ("the siren",
     "Pet Friendly Hotel The Siren welcomes four-legged companions to stay "
     "alongside you in Downtown Detroit. Our pet-friendly hotel "
     "accommodations make it easy to explore the city with your dog."),
    ("kensington",
     "We offer accommodations for large groups, such as wedding parties and "
     "company events, and cater to a variety of travelers with our selection "
     "of guest rooms, suites and pet-friendly rooms."),
    ("bare slogan", "Pet friendly!"),
    ("amenity list", "Free WiFi, fitness center, pet-friendly rooms, parking"),
]


@pytest.mark.parametrize("name,block", MARKETING_ONLY)
def test_marketing_prose_is_not_publication_grade(name, block):
    """A welcoming sentence with no fee, weight, count, species or acceptance
    rule is a slogan. It may still be true; it is not a policy this product
    can publish terms from."""
    affirmative, grade = R.has_affirmative_pets(block)
    assert affirmative is False, name
    assert grade == "MARKETING_ONLY", (name, grade)


# --------------------------------------------------------------------------- #
# 3. NEGATIVE: a refusal beats an allowance, always.
# --------------------------------------------------------------------------- #

REFUSALS = [
    ("bare negation", "Not Pet Friendly"),
    ("negated property",
     "Is the hotel dog-friendly? No, we are not a pet-friendly property. "
     "However, service animals are always welcome in accordance with ADA "
     "regulations."),
    ("plain refusal", "Sorry, no pets allowed."),
    ("location refusal",
     "Pet Policy: This location does not accept pets. Service and emotional "
     "support animals are always welcome."),
    ("no pet zone",
     "While we love your pets... Sorry, this is a NO PET zone."),
    ("not accepted",
     "Q. Is the hotel Pet Friendly? Pets are not accepted. | Service animals "
     "are welcome."),
]


@pytest.mark.parametrize("name,block", REFUSALS)
def test_a_refusal_is_never_read_as_an_acceptance(name, block):
    """The whole point of the ordering. "We are not a pet-friendly property"
    contains the token "pet-friendly"; a vocabulary that matched on the token
    would publish a hotel that refuses pets as one that takes them."""
    affirmative, grade = R.has_affirmative_pets(block)
    assert affirmative is False, name
    assert grade == "REFUSED", (name, grade)
    assert R.has_refusal(block) is True, name


def test_negation_is_neutralised_before_affirmative_matching():
    text = "We are not a pet-friendly property."
    assert "pet-friendly" in text
    assert "pet-friendly" not in R.neutralize_negated_acceptance(text).lower()


def test_a_refusal_wins_even_beside_welcoming_words():
    block = ("We love your furry friends! Unfortunately, for the safety, "
             "health and hygiene of all guests, pets are not allowed.")
    affirmative, grade = R.has_affirmative_pets(block)
    assert affirmative is False
    assert grade == "REFUSED"


# --------------------------------------------------------------------------- #
# 4. NEGATIVE: a question is not an answer; silence is not a refusal.
# --------------------------------------------------------------------------- #

def test_a_question_is_not_an_answer():
    """A founder ruled on exactly this: the only evidence captured for Embassy
    Suites Livonia Novi was the FAQ heading, and "that is a question, not an
    answer". The old vocabulary read the substring "pets allowed" inside it as
    affirmative acceptance."""
    block = "Are pets allowed at Embassy Suites by Hilton Detroit Livonia Novi?"
    affirmative, grade = R.has_affirmative_pets(block)
    assert affirmative is False
    assert grade == "QUESTION_ONLY"
    assert R.has_refusal(block) is False


def test_a_question_followed_by_its_answer_reads_the_answer():
    block = ("Are pets allowed? Yes -- dogs and cats are welcome for a $50 "
             "pet fee per night.")
    affirmative, _grade = R.has_affirmative_pets(block)
    assert affirmative is True


SILENT = [
    ("amenities", "The hotel has a fitness center, free parking and WiFi."),
    ("empty", ""),
    ("unrelated", "Check-in is at 3pm. Check-out is at 11am."),
]


@pytest.mark.parametrize("name,block", SILENT)
def test_silence_is_never_a_refusal(name, block):
    """SOURCE SILENCE IS ABSENCE. A page that says nothing about pets has not
    refused them, and an exclusion built on that would turn away a guest with
    a dog on the strength of nothing at all."""
    assert R.has_refusal(block) is False, name
    affirmative, _grade = R.has_affirmative_pets(block)
    assert affirmative is False, name


# --------------------------------------------------------------------------- #
# 5. NEGATIVE: service-animal language is not converted automatically.
# --------------------------------------------------------------------------- #

def test_service_animal_only_language_is_not_auto_converted():
    """Service-animal access is a legal category, not a pet policy.

    The Bell Tower Hotel answers "Are pets allowed?" with "We only allow
    service animals". A founder ruled THAT ONE PROPERTY no-pets as an
    identity-specific semantic ruling, precisely because the shared classifier
    does not and must not make that conversion on its own. If this test starts
    failing, the shared reader has quietly taken over a decision a human was
    required to make.
    """
    block = "Are pets allowed? We only allow service animals, not emotional support animals."
    assert R.has_refusal(block) is False
    affirmative, _grade = R.has_affirmative_pets(block)
    assert affirmative is False


def test_an_ordinary_pet_claim_must_survive_without_service_animal_clauses():
    block = ("We welcome guests with disabilities traveling with their "
             "service animals. Service animals are not pets.")
    affirmative, _grade = R.has_affirmative_pets(block)
    assert affirmative is False
