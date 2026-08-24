"""A refusal that names a PLACE restricts where, not whether.

Saint Kate's page opens "Yes, Saint Kate is a pet-friendly hotel" and later
says pets are not allowed in the Milwaukee Center Galleria. Read as a refusal
that produced a SOURCE_CONTRADICTORY the source never made, and a founder held
the row out of publication because the machine told them the page contradicted
itself. It does not.

The correction is narrow on purpose, and these controls are the boundary: a
hotel guest's own accommodation is NOT one of the places. "Pets are not allowed
in guest rooms" is a refusal, and an earlier draft of the pattern turned it
into silence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.brightdata import policy_reading as PR


def read(text: str):
    return PR.to_extraction(PR.parse(text, strategy="test"), location="test")


SHARED_SPACES = [
    "Dogs welcome. Pets are not allowed in the pool area.",
    "We are a pet-friendly hotel. Pets are not permitted in the restaurant.",
    "Pets are welcome. Pets are not allowed in the Milwaukee Center Galleria.",
    "Pets welcome. No pets in the fitness center.",
]

ACCOMMODATION = [
    "Pets are not allowed in guest rooms.",
    "Pets are not allowed in the guest rooms or suites.",
]

PLAIN = [
    "No pets allowed.",
    "Pets are not allowed on the property.",
    "Pets are not permitted at this hotel.",
]


@pytest.mark.parametrize("text", SHARED_SPACES)
def test_a_refusal_naming_a_shared_space_does_not_refuse_pets(text):
    result = read(text)
    assert result.extraction.get("pets_allowed") is True
    assert "pets_allowed" not in result.withheld


@pytest.mark.parametrize("text", ACCOMMODATION)
def test_a_refusal_naming_the_guest_room_is_still_a_refusal(text):
    """A hotel that will not take a pet into a guest room will not take the
    pet. This is the case the first draft of the pattern got wrong."""
    assert read(text).extraction.get("pets_allowed") is False


@pytest.mark.parametrize("text", PLAIN)
def test_an_unqualified_refusal_is_untouched(text):
    assert read(text).extraction.get("pets_allowed") is False


def test_a_place_restriction_does_not_hide_a_later_real_refusal():
    """Skipping the first refusal must not stop the walk: the next one still
    settles the question."""
    result = read("Pets are not permitted in the restaurant. "
                  "Pets are not allowed.")
    assert result.extraction.get("pets_allowed") is False


def test_the_skipped_sentence_is_recorded_rather_than_discarded():
    """A short list of amenity words was already handled by the house-rule
    lookahead an earlier work order added; what is new here is the general
    case, a place the reader has never heard of. Either way the sentence is
    kept as a note rather than thrown away."""
    reading = PR.parse("Yes, this is a pet-friendly hotel. Pets are not "
                       "allowed in the Milwaukee Center Galleria.",
                       strategy="test")
    assert any("names a place" in note for note in reading.parser_notes)


def test_a_place_named_a_sentence_later_is_not_a_qualifier():
    """"Pets are not allowed. Our pool area is open until ten" is a refusal
    followed by an unrelated fact, and the window must not reach across it."""
    result = read("Pets are not allowed. Our pool area is open until ten.")
    assert result.extraction.get("pets_allowed") is False
