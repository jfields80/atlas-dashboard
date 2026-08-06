"""PTF-RENDER -- refundability binds to the fee tier the source actually named.

A stay-length ladder may have only ONE of its amounts described as
non-refundable. Qualifying the whole sentence claims something about the other
tier that no wording supports, so the amount the source names decides which
rung carries the word.

Every excerpt below is the verbatim approved ``policy_excerpt`` of the record
named above it, whitespace-normalised exactly as the promotion builder
normalises it. No excerpt is shared between hotels.
"""

from scripts.pettripfinder.hotel_profile import (
    REFUND_GENERIC,
    REFUND_NONE,
    REFUND_TIER,
    REFUND_UNRESOLVED,
    _tiered_fee_sentence,
    _verified_summary,
    refundability_amounts,
    refundability_binding,
)


def _tier(amount, lo, hi):
    """A stay-length tier as the approved records carry it."""
    return {"amount": amount, "currency": "USD", "basis": "one_time",
            "basis_stated": False, "boundary_unit": "nights",
            "condition_min": lo, "condition_max": hi,
            "condition_type": "stay_length_range"}


LADDER_75_125 = (_tier("75.00", 1, 4), _tier("125.00", 5, None))

# Hampton Inn Columbus Airport -- lower tier is the named non-refundable amount.
EXCERPT_LOWER_75 = (
    "Pets Smoking WiFi Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee "
    "Max weight 75 lbs Max size Medium Other pet information "
    "$75(1-4n)$125(5+n)2pet Max dog/cat only")

# Hilton Garden Inn Columbus/Polaris -- UPPER tier is the named amount.
EXCERPT_HGI_POLARIS_125 = (
    "Pets Smoking WiFi Pets allowed Yes Deposit Yes. $125.00 Non-refundable Fee "
    "Max weight 50 lbs Max size Medium Other pet information "
    "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only")

# Homewood Suites by Hilton Columbus/Polaris, OH -- UPPER tier is the named amount.
EXCERPT_HOMEWOOD_POLARIS_125 = (
    "Pets Smoking WiFi Pets allowed Yes Deposit Yes. $125.00 Non-refundable Fee "
    "Other pet information $75(1-4nt), $125(5+n) 2 pets Max, dog/cat only")


class TestLowerTierNamed:
    def test_binding_selects_the_lower_tier(self):
        assert refundability_binding(LADDER_75_125, EXCERPT_LOWER_75) == (
            REFUND_TIER, ("75.00",))

    def test_sentence_qualifies_only_the_lower_tier(self):
        assert _tiered_fee_sentence(LADDER_75_125, EXCERPT_LOWER_75) == (
            "A non-refundable pet fee of $75 applies for stays of 1–4 nights, "
            "and $125 applies for stays of 5 nights or more.")


class TestUpperTierNamed:
    def test_hgi_polaris_binds_to_125(self):
        assert refundability_binding(LADDER_75_125, EXCERPT_HGI_POLARIS_125) == (
            REFUND_TIER, ("125.00",))

    def test_hgi_polaris_sentence_qualifies_the_upper_tier(self):
        assert _tiered_fee_sentence(LADDER_75_125, EXCERPT_HGI_POLARIS_125) == (
            "A pet fee of $75 applies for stays of 1–4 nights, and a "
            "non-refundable pet fee of $125 applies for stays of 5 nights or more.")

    def test_homewood_polaris_binds_to_125(self):
        assert refundability_binding(
            LADDER_75_125, EXCERPT_HOMEWOOD_POLARIS_125) == (REFUND_TIER, ("125.00",))

    def test_homewood_polaris_sentence_qualifies_the_upper_tier(self):
        assert _tiered_fee_sentence(LADDER_75_125, EXCERPT_HOMEWOOD_POLARIS_125) == (
            "A pet fee of $75 applies for stays of 1–4 nights, and a "
            "non-refundable pet fee of $125 applies for stays of 5 nights or more.")

    def test_upper_tier_wording_never_claims_the_lower_tier(self):
        s = _tiered_fee_sentence(LADDER_75_125, EXCERPT_HGI_POLARIS_125)
        assert not s.startswith("A non-refundable")


class TestGenericQualifier:
    """No figure is named, so the words describe the schedule as a whole."""

    def test_binding_is_generic(self):
        evidence = "Pets allowed Yes. A non-refundable pet fee applies to every stay."
        assert refundability_binding(LADDER_75_125, evidence) == (REFUND_GENERIC, ())

    def test_generic_renders_on_the_leading_tier_as_before(self):
        evidence = "Pets allowed Yes. A non-refundable pet fee applies to every stay."
        assert _tiered_fee_sentence(LADDER_75_125, evidence) == (
            "A non-refundable pet fee of $75 applies for stays of 1–4 nights, "
            "and $125 applies for stays of 5 nights or more.")

    def test_a_distant_figure_is_not_claimed_by_the_words(self):
        evidence = ("A non-refundable pet fee applies. " + "x" * 80 + " $999.00")
        assert refundability_amounts(evidence) == ()


class TestFailClosed:
    def test_amount_absent_from_the_ladder_withholds_the_qualifier(self):
        evidence = "Deposit Yes. $200.00 Non-refundable Fee Other pet information $75 / $125"
        mode, amounts = refundability_binding(LADDER_75_125, evidence)
        assert mode == REFUND_UNRESOLVED
        assert amounts == ("200.00",)

    def test_amount_absent_from_the_ladder_renders_no_qualifier(self):
        evidence = "Deposit Yes. $200.00 Non-refundable Fee Other pet information $75 / $125"
        assert "non-refundable" not in _tiered_fee_sentence(LADDER_75_125, evidence)

    def test_contradictory_amounts_withhold_the_qualifier(self):
        evidence = ("Deposit Yes. $75.00 Non-refundable Fee. "
                    "Elsewhere: $125.00 non-refundable fee.")
        mode, amounts = refundability_binding(LADDER_75_125, evidence)
        assert mode == REFUND_UNRESOLVED
        # reported in numeric order so a diagnostic reads predictably
        assert amounts == ("75.00", "125.00")

    def test_contradictory_amounts_render_no_qualifier(self):
        evidence = ("Deposit Yes. $75.00 Non-refundable Fee. "
                    "Elsewhere: $125.00 non-refundable fee.")
        assert "non-refundable" not in _tiered_fee_sentence(LADDER_75_125, evidence)

    def test_amount_matching_several_tiers_withholds_the_qualifier(self):
        ladder = (_tier("75.00", 1, 4), _tier("75.00", 5, None))
        mode, _ = refundability_binding(ladder, EXCERPT_LOWER_75)
        assert mode == REFUND_UNRESOLVED
        assert "non-refundable" not in _tiered_fee_sentence(ladder, EXCERPT_LOWER_75)


class TestNoQualifier:
    def test_wording_without_the_word_is_unchanged(self):
        evidence = "Pets allowed Yes Other pet information $75(1-4n)$125(5+n)"
        assert refundability_binding(LADDER_75_125, evidence) == (REFUND_NONE, ())
        assert _tiered_fee_sentence(LADDER_75_125, evidence) == (
            "A pet fee of $75 applies for stays of 1–4 nights, "
            "and $125 applies for stays of 5 nights or more.")

    def test_empty_evidence_is_unchanged(self):
        assert refundability_binding(LADDER_75_125, "") == (REFUND_NONE, ())
        assert "non-refundable" not in _tiered_fee_sentence(LADDER_75_125, "")


class TestNoCrossRecordUse:
    """Only the evidence handed in decides; one hotel never reads another's."""

    def test_each_record_binds_from_its_own_wording_alone(self):
        lower = _tiered_fee_sentence(LADDER_75_125, EXCERPT_LOWER_75)
        upper = _tiered_fee_sentence(LADDER_75_125, EXCERPT_HGI_POLARIS_125)
        assert lower != upper
        assert lower.startswith("A non-refundable pet fee of $75")
        assert upper.startswith("A pet fee of $75")

    def test_binding_is_a_pure_function_of_its_arguments(self):
        first = refundability_binding(LADDER_75_125, EXCERPT_HOMEWOOD_POLARIS_125)
        refundability_binding(LADDER_75_125, EXCERPT_LOWER_75)
        assert refundability_binding(
            LADDER_75_125, EXCERPT_HOMEWOOD_POLARIS_125) == first


class TestFullSummary:
    """The bound qualifier survives into the consumer summary."""

    def test_upper_tier_summary(self):
        facts = {"pets_allowed": "true", "species_allowed": "dogs, cats",
                 "fee_tiers": [dict(t) for t in LADDER_75_125],
                 "pet_count_limit": "2", "weight_limit": "50.0 pounds"}
        assert _verified_summary(facts, EXCERPT_HGI_POLARIS_125) == (
            "Dogs and cats are accepted. A pet fee of $75 applies for stays of "
            "1–4 nights, and a non-refundable pet fee of $125 applies for "
            "stays of 5 nights or more. Maximum pet weight is 50 pounds, with "
            "up to 2 pets permitted per room.")

    def test_lower_tier_summary(self):
        facts = {"pets_allowed": "true", "species_allowed": "dogs, cats",
                 "fee_tiers": [dict(t) for t in LADDER_75_125],
                 "pet_count_limit": "2", "weight_limit": "75.0 pounds"}
        assert _verified_summary(facts, EXCERPT_LOWER_75) == (
            "Dogs and cats are accepted. A non-refundable pet fee of $75 applies "
            "for stays of 1–4 nights, and $125 applies for stays of 5 nights "
            "or more. Maximum pet weight is 75 pounds, with up to 2 pets "
            "permitted per room.")
