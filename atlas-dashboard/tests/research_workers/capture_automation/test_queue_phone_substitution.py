"""PTF-COLUMBUS-INTEGRATE-UNRESOLVED-001 -- the queue may drop expected_phone
ONLY in exchange for the two key groups the capture-time doctrine actually wants.

The change being defended is narrow and easy to over-read, so these tests are
written mostly as refusals. ``identity_keys`` confirms an identity on two
INDEPENDENT key groups (address, phone, property_identifier) with at least one
authoritative basis; phone is one of the three, not a floor. A queue entry that
carries a street address, a postal code and a property code therefore offers the
gate the same two-group standard, and refusing it was stricter than the doctrine
it was supposed to be protecting.

Everything else must still fail closed: a missing address, a missing postal code,
a missing property code, or any two of them together. And none of this touches
capture-time verification -- the gate still has to find and agree with two
independent keys on the rendered page.
"""

from __future__ import annotations

import pytest

from services.research_workers.capture_automation.identity_keys import (
    KEY_GROUPS, MINIMUM_INDEPENDENT_KEYS,
)
from services.research_workers.capture_automation.queue import validate_entry

BRANDS = ("marriott", "hilton", "ihg", "wyndham")


def entry(**overrides):
    row = {
        "hotel_id": "h-1", "listing_key": "test hotel", "hotel_name": "Test Hotel",
        "brand": "hilton",
        "official_url": "https://www.hilton.com/en/hotels/cmhclgu-graduate-columbus/",
        "expected_address": "750 N High St", "expected_city": "Columbus",
        "expected_state": "OH", "expected_postal_code": "43215",
        "expected_phone": "614-555-0100",
        "expected_property_code": "cmhclgu",
    }
    row.update(overrides)
    return {k: v for k, v in row.items() if v is not None}


def problems(**overrides):
    _, found = validate_entry(entry(**overrides), 0, known_brands=BRANDS)
    return found


def missing_phone(found):
    return [p for p in found if p.endswith("missing_field:expected_phone")]


class TestDoctrineItself:
    """The premise. If these change, the queue rule must be revisited."""

    def test_phone_is_one_group_of_three(self):
        assert set(KEY_GROUPS.values()) == {"address", "phone", "property_identifier"}

    def test_two_independent_groups_are_required(self):
        assert MINIMUM_INDEPENDENT_KEYS == 2

    def test_address_and_property_identifier_are_independent_of_phone(self):
        groups = {KEY_GROUPS[k] for k in KEY_GROUPS}
        assert {"address", "property_identifier"} <= groups
        # Two groups that are not phone: the substitution is possible at all.
        assert len({"address", "property_identifier"}) >= MINIMUM_INDEPENDENT_KEYS


class TestPhoneMayBeSubstituted:

    def test_full_entry_with_phone_is_accepted(self):
        assert problems() == []

    def test_phone_absent_but_address_postal_and_code_present_is_accepted(self):
        assert problems(expected_phone="") == []

    def test_phone_key_entirely_missing_is_also_accepted(self):
        assert problems(expected_phone=None) == []

    def test_the_accepted_entry_really_is_usable(self):
        parsed, found = validate_entry(entry(expected_phone=""), 0, known_brands=BRANDS)
        assert found == [] and parsed is not None
        assert parsed.expected_phone == ""
        assert parsed.expected_address and parsed.expected_postal_code


class TestWeakIdentitiesStillFailClosed:
    """Every one of these must refuse. The substitution is a trade, not a waiver."""

    def test_no_phone_and_no_postal_code_is_refused(self):
        assert missing_phone(problems(expected_phone="", expected_postal_code=""))

    def test_no_phone_and_no_property_code_is_refused(self):
        assert missing_phone(problems(expected_phone="", expected_property_code=""))

    def test_no_phone_and_no_address_is_refused(self):
        found = problems(expected_phone="", expected_address="")
        assert missing_phone(found)
        assert [p for p in found if p.endswith("missing_field:expected_address")]

    def test_no_phone_and_nothing_else_is_refused(self):
        assert missing_phone(problems(
            expected_phone="", expected_postal_code="", expected_property_code=""))

    def test_address_is_never_optional_even_with_phone(self):
        assert [p for p in problems(expected_address="")
                if p.endswith("missing_field:expected_address")]

    def test_city_and_state_remain_required(self):
        assert [p for p in problems(expected_city="")
                if p.endswith("missing_field:expected_city")]
        assert [p for p in problems(expected_state="")
                if p.endswith("missing_field:expected_state")]

    @pytest.mark.parametrize("blank", ["   ", "\t", "\n"])
    def test_whitespace_is_not_a_value(self, blank):
        assert missing_phone(problems(expected_phone="", expected_postal_code=blank))

    def test_substitution_does_not_bypass_any_other_gate(self):
        """A phone-less entry still has to pass every unrelated check."""
        found = problems(expected_phone="", brand="hyatt",
                         official_url="http://www.hilton.com/en/hotels/cmhclgu-x/")
        assert any("no_adapter_for_brand:hyatt" in p for p in found)
        assert any("url_not_https" in p for p in found)
