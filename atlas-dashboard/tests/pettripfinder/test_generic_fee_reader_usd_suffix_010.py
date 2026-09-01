# -*- coding: utf-8 -*-
"""PTF-GENERIC-FEE-READER-USD-SUFFIX-FIX-010 -- the shared fee reader on the
USD-suffix money forms Wyndham renders.

WHAT THIS ORDER FOUND. Indianapolis orders 007-009 carried a "known 50 USD
reader defect" and blocked eight Wyndham rows on it: the rendered policies write
money as "15 USD", "20.00 USD" and "25USD" with no space. Probed on the
canonical lineage before any change, ``policy_reading.parse`` already reads all
three forms -- the ``(?P<usd>...)\\s*USD\\b`` branch entered the labelled,
prose, band, cap and cleaning patterns across 76d3ca0, 1537625 and a80b2b4,
and ``test_fee_forms`` already exercises "75USD" and "50 USD". The premise was
stale; the reader was not changed here. What was missing was a permanent
fixture set that says so in the reader's own vocabulary, so the next order that
inherits the rumour can run one file instead of an attended pass.

FIXTURES. The Wyndham blocks are the exact rendered quotes captured by
PTF-INDIANAPOLIS-ATTENDED-POLICY-PASS-009 (worker commit 2de700e,
``indianapolis_in_shadow_policy_evidence_009.json``), embedded verbatim rather
than merged: this order builds fixtures from that evidence and publishes
nothing from it. Nothing here touches Indianapolis authority.

TWO THINGS DELIBERATELY NOT PINNED, because pinning them would freeze a gap as
a rule: the USD-PREFIX form ("USD 25") is unread today and marked xfail; and a
"Sanitation Fee" is read as a plain fee, not a cleaning-labelled one, because
the cleaning vocabulary is ``clean(ing)`` -- both reported, neither decided by
a fixture file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _minor(x):
    return x.amount_minor if hasattr(x, "amount_minor") else x["amount_minor"]


def charges(text):
    return list(PR.parse(text).charges)


def charge_amounts(text):
    return sorted(c.amount_minor for c in charges(text))


def excluded_amounts(text):
    return sorted(_minor(x) for x in PR.parse(text).excluded_amounts)


def the_only_charge(text):
    found = charges(text)
    assert len(found) == 1, [(c.amount_minor, c.quote) for c in found]
    return found[0]


# --------------------------------------------------------------------------- #
# Phase 3 -- the three Wyndham shapes, minimal
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text, minor, form", [
    ("Non-refundable 15 USD nightly per pet.", 1500, "15 USD"),
    ("20.00 USD per pet per night.", 2000, "20.00 USD"),
    ("25USD per pet per night.", 2500, "25USD"),
])
def test_usd_suffix_forms_read_as_a_nightly_per_pet_charge(text, minor, form):
    charge = the_only_charge(text)
    assert charge.amount_minor == minor
    assert charge.basis == "per_night"
    assert charge.scope == "per_pet"
    assert form in charge.quote


def test_the_non_refundable_qualifier_travels_with_the_suffix_form():
    charge = the_only_charge("Non-refundable 15 USD nightly per pet.")
    assert charge.refundable is False


@pytest.mark.parametrize("spelling", ["25 USD", "25  USD", "25USD", "25 usd", "25usd"])
def test_whitespace_before_usd_is_optional_and_case_is_ignored(spelling):
    charge = the_only_charge("%s per pet per night." % spelling)
    assert charge.amount_minor == 2500


@pytest.mark.parametrize("text, minor", [
    ("20.00 USD per pet per night.", 2000),
    ("20.50 USD per pet per night.", 2050),
    ("100.00 USD per pet per stay.", 10000),
    ("1,250.00 USD per pet per stay.", 125000),
])
def test_decimal_and_grouped_amounts_keep_their_minor_units(text, minor):
    assert charge_amounts(text) == [minor]


# --------------------------------------------------------------------------- #
# Leading-dollar controls -- the behaviour that must not regress
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text, minor", [
    ("Pet fee $15 per night.", 1500),
    ("Pet fee $20.00 per night.", 2000),
    ("A non-refundable pet fee of $25 per night applies.", 2500),
    ("Pet deposit of $50.00 per stay.", 5000),
])
def test_leading_dollar_forms_in_pet_context_still_read(text, minor):
    # Set semantics on purpose: the prose path can state the same amount twice
    # ("$25.00 per night" and "25.00 per night"); that is pre-existing and not
    # this order's to decide. What is pinned is the amount and that it is one
    # amount.
    assert set(charge_amounts(text)) == {minor}


@pytest.mark.parametrize("text, minor", [
    ("$25 per night", 2500),
    ("$50.00 per stay", 5000),
])
def test_a_bare_leading_dollar_amount_is_recognised_but_not_a_pet_charge(text, minor):
    """The reader has always refused to call an amount a pet charge when the
    surface names no pet -- the non-pet-purpose rule the reader freeze pins.
    The money is still SEEN: it lands in ``excluded_amounts`` with its value,
    which is how a later order can tell "not read" from "read and refused"."""
    assert charge_amounts(text) == []
    assert excluded_amounts(text) == [minor]


# --------------------------------------------------------------------------- #
# Not money -- explicit currency context is required
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text", [
    "Pets must not weigh more than 25 lbs each.",
    "50lbs or less per pet.",
    "2 pets max.",
    "Up to 2 pets are welcome.",
    "Room 250 is pet friendly.",
    "Call 317-555-1212 for details.",
    "A 10% surcharge applies.",
    "Effective 12 May 2026.",
    "Pets allowed on floors 2 and 3.",
])
def test_numbers_without_currency_context_are_not_money(text):
    reading = PR.parse(text)
    assert list(reading.charges) == []
    assert list(reading.excluded_amounts) == []


def test_a_weight_next_to_a_suffix_fee_is_not_read_as_a_second_fee():
    text = ("A maximum of 2 pets allowed for a non-refundable charge of 20.00 USD "
            "per pet per night plus tax. Pets must not weigh more than 25 lbs each.")
    reading = PR.parse(text)
    assert [c.amount_minor for c in reading.charges] == [2000]
    assert 2500 not in [_minor(x) for x in reading.excluded_amounts]
    # The weight itself ("must not weigh more than 25 lbs") is not read by the
    # weight vocabulary today -- a separate gap, reported and not pinned here.


# --------------------------------------------------------------------------- #
# Phase 5 -- the captured Indianapolis Order-009 Wyndham blocks, verbatim
# --------------------------------------------------------------------------- #

WYNDHAM_BLOCKS = {
    "baymont-indianapolis": (
        "Service Animals - ADA-defined service animals are welcome free of charge. "
        "Pets Allowed - 2 pets max. Fees - Non-refundable 15 USD nightly per pet. "
        "Pet Sanitation Fee is 50 USD if applicable. Other Information - Pets "
        "cannot be left unattended in room."),
    "baymont-indianapolis-west": (
        "A maximum of 2 pets allowed for a non-refundable charge of 20.00 USD per "
        "pet per night plus tax. Pets must not weigh more than 25 lbs each. A "
        "100.00 USD refundable damage deposit is required at check-in. ADA defined "
        "service animals are welcomed at this hotel."),
    "days-inn-south": (
        "Service Animals - ADA-defined service animals welcome. / Pets Allowed - 2 "
        "pets max. 50lbs or less per pet. / Fees - 25USD per pet per night. Pet "
        "Sanitation Fee 250USD if required. / Other information - Contact hotel "
        "for additional details and availability."),
    "super-8-emerson": (
        "Up to 2 pets are welcome for a non-refundable charge of 25USD per pet per "
        "night. Pet Sanitation Fee is 100 USD if applicable. Sorry no cats allowed. "
        "ADA defined service animals are also welcome at this hotel."),
    "travelodge-speedway": (
        "Service Animals - ADA-defined service animals welcome. / Dogs Allowed - 2 "
        "pets max. Dogs only. 40lbs or less per pet. / Fees - 25USD per pet per "
        "night. / Other Information - Contact hotel for additional details and "
        "availability."),
}

WYNDHAM_REFUSALS = {
    "baymont-northeast": ("ADA-defined service animals are welcome at this hotel. "
                          "Sorry no other pets are allowed."),
    "days-inn-northwest": ("ADA defined service animals are welcome at this hotel. "
                           "Sorry no other pets are allowed."),
    "days-inn-castleton": ("ADA defined service animals are welcome at this hotel. "
                           "Sorry no other pets are allowed."),
}


@pytest.mark.parametrize("slug, nightly, other", [
    ("baymont-indianapolis", 1500, [5000]),
    ("baymont-indianapolis-west", 2000, []),
    ("days-inn-south", 2500, [25000]),
    ("super-8-emerson", 2500, [10000]),
    ("travelodge-speedway", 2500, []),
])
def test_each_wyndham_block_recovers_its_nightly_fee_and_stated_sanitation_fee(
        slug, nightly, other):
    reading = PR.parse(WYNDHAM_BLOCKS[slug])
    nightly_charges = [c for c in reading.charges if c.basis == "per_night"]
    assert [c.amount_minor for c in nightly_charges] == [nightly]
    assert nightly_charges[0].scope == "per_pet"
    others = sorted(c.amount_minor for c in reading.charges if c.basis != "per_night")
    assert others == other


def test_sanitation_fees_are_read_with_no_basis_because_the_surface_states_none():
    for slug, minor in (("baymont-indianapolis", 5000), ("days-inn-south", 25000),
                        ("super-8-emerson", 10000)):
        reading = PR.parse(WYNDHAM_BLOCKS[slug])
        sanitation = [c for c in reading.charges if c.amount_minor == minor]
        assert len(sanitation) == 1, slug
        assert sanitation[0].basis == ""
        assert "Sanitation Fee" in sanitation[0].quote


def test_baymont_west_damage_deposit_is_seen_and_refused_by_the_frozen_purpose_rule():
    """The 100.00 USD deposit is NOT a USD-suffix miss: the amount is parsed.
    It is excluded because "damage deposit" is a frozen non-pet purpose
    (``reader_freeze.FROZEN_NON_PET_PURPOSES``) and the sentence names no pet.
    Whether Wyndham's damage deposit is a pet charge is a founder question this
    order does not answer; the fixture records exactly where the reader put it."""
    reading = PR.parse(WYNDHAM_BLOCKS["baymont-indianapolis-west"])
    assert [c.amount_minor for c in reading.charges] == [2000]
    assert 10000 in [_minor(x) for x in reading.excluded_amounts]


@pytest.mark.parametrize("slug", sorted(WYNDHAM_REFUSALS))
def test_the_three_refusal_blocks_state_no_charge(slug):
    reading = PR.parse(WYNDHAM_REFUSALS[slug])
    assert list(reading.charges) == []
    assert list(reading.excluded_amounts) == []


def test_super_8_species_refusal_and_travelodge_dogs_only_survive_beside_the_fee():
    assert PR.parse(WYNDHAM_BLOCKS["super-8-emerson"]).cats_refused_quote
    assert PR.parse(WYNDHAM_BLOCKS["travelodge-speedway"]).dogs_only_quote


# --------------------------------------------------------------------------- #
# Recorded gaps -- documented, not decided here
# --------------------------------------------------------------------------- #

@pytest.mark.xfail(strict=True,
                   reason="USD-PREFIX form ('USD 25') is not read today; not a form "
                          "any captured surface uses and not in scope for 010")
def test_usd_prefix_form_is_not_yet_supported():
    assert charge_amounts("Pet fee USD 25 per night.") == [2500]
