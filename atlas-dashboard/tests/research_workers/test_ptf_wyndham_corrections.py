"""PTF-WYNDHAM -- two narrow corrections, plus the fee-dimension audit.

Three defects, all found by running the real pipeline against five Columbus
Wyndham properties rather than by reading it:

  1. A page that returns 200 and names a pet-policy section was called
     ready_for_extraction even when its body carried no policy VALUES at all.
     Every Wyndham property page is that shape, and what they do carry is
     brochure copy, so a worker sent to extract would have published
     advertising as policy.

  2. The seed's "7474 N High St" was reported missing from a page printing
     "7474 North High St".

  3. "25 USD per pet per night" -- one value on each of two independent axes
     -- was reported as contradicting itself, and five hotels were held on it.

Offline: no network, no browser.
"""

from __future__ import annotations

import pytest

from services.research_workers.capture_automation.evidence_completeness import (
    street_variants,
)
from services.research_workers.rendered_capture import (
    collect_statements, detect_contradictions,
)
from services.research_workers.render_evidence import policy_value_signals


# --------------------------------------------------------------------------- #
# 1. Page retrieved is not policy retrieved.
# --------------------------------------------------------------------------- #

#: The measured Wyndham static shape: the section is announced, the values
#: are not there. Taken from the real bodies of all five Columbus properties.
HEADING_ONLY = (
    "Hotel Policies Check In Check Out Children Stay Free Policy "
    "Pet & Service Animal Policy Smoking Policy General Information"
)

MARKETING_ONLY = (
    "Relax in Columbus Comfort Each room at our pet-friendly hotel features a "
    "coffee and tea maker. Rates do not include amenities such as rollaway "
    "beds, parking, and pets (if allowed)."
)

RENDERED_VALUES = (
    "Service Animals - ADA-defined service animals welcome. "
    "Dogs Allowed. 2 dogs max. 50lbs or less per pet. "
    "Fees - 25USD per pet per night."
)

STATIC_WITH_VALUES = (
    "Hotel Policies Pet Policy: we welcome up to 2 pets per room, 50 lbs or "
    "less, for a fee of $25 per night."
)


class TestPolicyValuesAreNotAHeading:
    def test_a_static_heading_only_states_no_policy_value(self):
        assert policy_value_signals(HEADING_ONLY) == ()

    def test_b_generic_pet_friendly_marketing_states_no_policy_value(self):
        """'pet-friendly' and 'an extra fee' are advertising, not a policy.

        A fee with no AMOUNT cannot publish a record, so the word alone is
        not a value. A count is -- which is why the Worthington brochure line
        is the honest edge of this rule and is asserted separately below.
        """
        assert policy_value_signals(MARKETING_ONLY) == ()
        assert policy_value_signals(
            "Bring your pet along for an extra nightly fee.") == ()

    def test_b_a_brochure_that_states_a_real_quantity_does_count(self):
        """Worthington's prose names a count and a ceiling. Rejecting that as
        'marketing' would be judging the sentence's tone, not its content."""
        signals = policy_value_signals(
            "You can bring along up to two pets (60 pounds or less) for an "
            "extra nightly fee.")
        assert set(signals) >= {"pet_count", "weight_limit"}
        assert "money_amount" not in signals

    def test_c_values_absent_from_static_but_present_once_rendered(self):
        assert policy_value_signals(HEADING_ONLY) == ()
        assert set(policy_value_signals(RENDERED_VALUES)) >= {
            "pet_count", "weight_limit", "money_amount"}

    def test_d_actual_policy_values_in_the_static_body_are_recognised(self):
        assert set(policy_value_signals(STATIC_WITH_VALUES)) >= {
            "pet_count", "money_amount"}


class TestReadinessRequiresValues:
    """The gate itself, through the real RetrievalOutcome."""

    def _outcome(self, text):
        from services.research_workers.contracts import SourceDocument
        from services.research_workers import source_retrieval as SR
        doc = SourceDocument(
            source_url="https://www.wyndhamhotels.com/x/overview",
            source_type="official_site", retrieved_at="2026-08-02",
            title="t", content_text=text, content_hash="sha256:" + "0" * 64,
            retrieval_status="OK")
        url = "https://www.wyndhamhotels.com/x/overview"
        return SR.RetrievalOutcome(
            status=SR.RETRIEVED, source_role=SR.LODGING_SOURCE_ROLE_PROPERTY_POLICY,
            assignment_id="a", listing_key="k", listing_name="n",
            initial_url=url, final_url=url,
            policy_applicable=True, source_document=doc)

    def test_a_heading_only_is_not_ready_for_extraction(self):
        o = self._outcome(HEADING_ONLY)
        assert o.status == "RETRIEVED"          # the PAGE did arrive
        assert not o.static_policy_values_present
        assert not o.ready_for_extraction       # the POLICY did not

    def test_b_marketing_only_is_not_ready_for_extraction(self):
        assert not self._outcome(MARKETING_ONLY).ready_for_extraction

    def test_d_a_body_carrying_values_stays_ready(self):
        o = self._outcome(STATIC_WITH_VALUES)
        assert o.static_policy_values_present
        assert o.ready_for_extraction

    def test_e_identity_retrieval_is_untouched_and_separate(self):
        """Narrowing extraction must not narrow what was reached."""
        o = self._outcome(HEADING_ONLY)
        assert o.status == "RETRIEVED"
        assert o.source_document is not None
        assert o.policy_applicable
        assert o.to_dict()["static_policy_values_present"] is False

    def test_f_the_reason_is_recorded_on_the_artifact(self):
        d = self._outcome(STATIC_WITH_VALUES).to_dict()
        assert d["static_policy_values_present"] is True
        assert d["ready_for_extraction"] is True


# --------------------------------------------------------------------------- #
# 2. Leading directional abbreviations.
# --------------------------------------------------------------------------- #

class TestDirectionalNormalization:
    def test_n_high_st_matches_north_high_street(self):
        v = [x.lower() for x in street_variants("7474 N High St")]
        assert "7474 north high street" in v
        assert "7474 n high st" in v

    def test_w_broad_st_matches_west_broad_street(self):
        v = [x.lower() for x in street_variants("123 W Broad St")]
        assert "123 west broad street" in v

    def test_the_expansion_is_symmetric(self):
        v = [x.lower() for x in street_variants("7474 North High Street")]
        assert "7474 n high street" in v

    @pytest.mark.parametrize("short,long", [
        ("N", "North"), ("S", "South"), ("E", "East"), ("W", "West"),
        ("NE", "Northeast"), ("NW", "Northwest"),
        ("SE", "Southeast"), ("SW", "Southwest"),
    ])
    def test_every_directional_is_covered(self, short, long):
        v = [x.lower() for x in street_variants("100 %s Main St" % short)]
        assert ("100 %s main street" % long).lower() in v

    def test_words_containing_the_letters_are_untouched(self):
        """A blind substring swap turns Westerville into Wersterville."""
        for street in ("5000 Westerville Rd", "80 Northwoods Blvd",
                       "12 Southfield Ave", "9 Eastland Dr"):
            for v in street_variants(street):
                assert "Wersterville" not in v
                assert v.split()[1] == street.split()[1], v

    def test_a_directional_not_in_the_house_number_slot_is_untouched(self):
        """Only the token after the number is a leading directional."""
        for v in street_variants("100 Main St N"):
            assert not v.lower().startswith("100 north")

    def test_unit_numbers_and_postal_codes_are_unchanged(self):
        """Digits are never rewritten, and the street line stops at its suffix."""
        for v in street_variants("7474 N High St Columbus OH 43235"):
            assert "43235" not in v          # street_line drops city/state/ZIP
            assert v.split()[0] == "7474"    # the house number is untouched
        for v in street_variants("7474 N High St Suite 200"):
            assert "200" not in v.replace("7474", "")

    def test_a_street_line_with_no_directional_is_unchanged(self):
        assert street_variants("175 Hutchinson Ave") == (
            "175 Hutchinson Ave", "175 Hutchinson Avenue")


# --------------------------------------------------------------------------- #
# 3. Fee dimensions: scope and time basis are different questions.
# --------------------------------------------------------------------------- #

def _contradictions(text):
    return detect_contradictions(collect_statements(text))


class TestFeeDimensions:
    def test_per_pet_and_per_night_coexist(self):
        found = _contradictions("Fees - 25 USD per pet per night.")
        assert not [c for c in found if c.startswith("conflicting_fee")], found

    def test_per_pet_and_per_stay_coexist(self):
        found = _contradictions("Fees - 50 USD per pet per stay.")
        assert not [c for c in found if c.startswith("conflicting_fee")], found

    def test_per_night_conflicts_with_per_stay(self):
        found = _contradictions(
            "Fees - 25 USD per night. A fee of 75 USD per stay applies.")
        assert "conflicting_fee_basis_per_stay_vs_fee_basis_per_night" in found

    def test_per_pet_conflicts_with_per_party(self):
        found = _contradictions(
            "A fee of 25 USD per pet applies. One fee of 50 USD per room applies.")
        assert "conflicting_fee_basis_per_pet_vs_fee_scope_per_party" in found

    def test_multiple_amounts_are_still_reported(self):
        """The tiered-fee protection is untouched."""
        found = _contradictions(
            "$75 for 1-7 nights. $150 for 8 or more nights.")
        assert any(c.startswith("multiple_fee_amounts") for c in found), found

    def test_the_baymont_sentence_is_not_a_contradiction(self):
        found = _contradictions(RENDERED_VALUES)
        assert not [c for c in found if c.startswith("conflicting_fee")], found
