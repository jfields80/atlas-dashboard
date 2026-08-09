"""PTF-WORKERS-FEE-TERMS -- structured stay-length tiered pet fees.

A property charging "$75(1-4n)$125(5+n)" has no single pet fee. Publishing the
Deposit row's $75 alone understates a five-night stay by $50, and that is the
flattening this feature exists to prevent.

Brand-neutral by construction: the parser keys on NOTATION, never on a hotel,
chain or domain. Two properties printing the same numbers is a coincidence the
code cannot observe -- every capture is parsed on its own.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import json
import pathlib
from decimal import Decimal

import pytest

from scripts.pettripfinder.hotel_profile import (
    _tiered_fee_sentence, _verified_details, _verified_facts, _verified_summary,
    tier_fee_range,
)
from scripts.pettripfinder.promote_attested_candidates import build_candidate
from services.research_workers import vocabulary as V
from services.research_workers.fee_terms import (
    basis_is_stated, parse_fee_tiers, tier_facts,
)

# Verbatim from the real captures -- one chain, two notations.
HAMPTON = "$75(1-4n)$125(5+n)2pet Max dog/cat only"
NEW_ALBANY_PAYLOAD = "$50(1-4n),$75(5+n) 2petsMax,dog/cat only"
NEW_ALBANY_RENDERED = "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"
FLAT = "Pets allowed, $100.00 non-refundable fee, 75 lbs maximum"


def _tiers(text):
    terms, problems = parse_fee_tiers(text)
    assert problems == [], problems
    return tier_facts(terms, basis_stated=basis_is_stated(text))


# --------------------------------------------------------------------------- #
# 1. Valid ladders, in every notation the sources actually use.
# --------------------------------------------------------------------------- #

class TestValidTiers:
    def test_two_tier_fee(self):
        terms, problems = parse_fee_tiers(HAMPTON)
        assert problems == []
        assert len(terms) == 2
        a, b = terms
        assert (a.amount, a.condition_min, a.condition_max) == ("75.00", 1, 4)
        assert (b.amount, b.condition_min, b.condition_max) == ("125.00", 5, None)

    def test_open_ended_final_tier(self):
        """condition_max None IS the open-ended range -- the contract's own
        convention, not a sentinel invented here."""
        terms, _ = parse_fee_tiers(HAMPTON)
        assert terms[-1].condition_max is None
        assert terms[-1].condition_min == 5
        assert terms[-1].boundary_unit == V.BOUNDARY_UNIT_NIGHTS

    @pytest.mark.parametrize("text,expected", [
        (HAMPTON, [("75.00", 1, 4), ("125.00", 5, None)]),
        (NEW_ALBANY_PAYLOAD, [("50.00", 1, 4), ("75.00", 5, None)]),
        (NEW_ALBANY_RENDERED, [("50.00", 1, 4), ("75.00", 5, None)]),
        ("$75 (1-4 nights) $125 (5+ nights)", [("75.00", 1, 4), ("125.00", 5, None)]),
        ("$75 for 1–4 nights; $125 for 5 nights or more",
         [("75.00", 1, 4), ("125.00", 5, None)]),
        ("$75 for 1 to 4 nights and $125 for 5 nights or longer",
         [("75.00", 1, 4), ("125.00", 5, None)]),
        ("1 to 4 nights $50 and 5 nights or more $75",
         [("50.00", 1, 4), ("75.00", 5, None)]),
    ])
    def test_notation_variants(self, text, expected):
        terms, problems = parse_fee_tiers(text)
        assert problems == []
        assert [(t.amount, t.condition_min, t.condition_max) for t in terms] == expected

    def test_amounts_are_exact_decimals_never_floats(self):
        terms, _ = parse_fee_tiers(HAMPTON)
        assert all(isinstance(t.amount, str) for t in terms)
        assert [t.amount for t in terms] == ["75.00", "125.00"]

    def test_source_quote_preserved_per_tier(self):
        terms, _ = parse_fee_tiers(HAMPTON)
        assert [t.evidence_quote for t in terms] == ["$75(1-4n)", "$125(5+n)"]
        for t in terms:
            assert t.evidence_quote in HAMPTON

    def test_tiers_never_shared_across_properties(self):
        """Requirement 6: each property is parsed independently. Same shape,
        different numbers -- neither may leak into the other."""
        a = [(t.amount, t.condition_min, t.condition_max) for t in parse_fee_tiers(HAMPTON)[0]]
        b = [(t.amount, t.condition_min, t.condition_max)
             for t in parse_fee_tiers(NEW_ALBANY_PAYLOAD)[0]]
        assert a != b
        assert a[0][0] == "75.00" and b[0][0] == "50.00"


# --------------------------------------------------------------------------- #
# 1b. PTF-FEE-TIERS-005 -- the same ladder written in ordinary prose.
#
# Verbatim from the live Sonesta Simply Suites Dublin Columbus page. Neither
# tier uses the compressed notation: the first gives only a spoken upper bound
# and the second gives no number at all. Before this sprint the parser saw one
# priced range and returned tier_single_only, so the fee could not publish.
# --------------------------------------------------------------------------- #

SONESTA = ("pets, with no breed or weight restrictions. Up to two pets are permitted "
           "per suite. We apologize as cats are not permitted. $75 fee, per pet, "
           "applies for stays up to 7 nights; $150 for all longer stays. Learn more "
           "about our pet policy here .")


class TestProseLadder:
    def test_sonesta_ladder_parses(self):
        terms, problems = parse_fee_tiers(SONESTA)
        assert problems == []
        assert [(t.amount, t.condition_min, t.condition_max) for t in terms] == [
            ("75.00", 1, 7), ("150.00", 8, None)]

    def test_open_tier_lower_bound_is_derived_from_the_stated_boundary(self):
        """8 is not stated; 7 is. "Longer than 7 nights" is 8 or more, and the
        quote carried on the open tier contains the 7 that licenses it."""
        terms, _ = parse_fee_tiers(SONESTA)
        assert terms[1].condition_min == 8 and terms[1].condition_max is None
        assert "up to 7 nights" in terms[1].evidence_quote
        assert "$150 for all longer stays" in terms[1].evidence_quote

    def test_every_quote_is_verbatim_from_the_source(self):
        terms, _ = parse_fee_tiers(SONESTA)
        normalized = " ".join(SONESTA.split())
        for t in terms:
            assert t.evidence_quote in normalized

    def test_basis_is_not_stated_by_this_wording(self):
        """"per pet" is a SCOPE. It says nothing about per-night vs per-stay,
        so no basis may be asserted from it."""
        assert basis_is_stated(SONESTA) is False

    @pytest.mark.parametrize("text,expected", [
        ("$75 fee applies for stays up to 7 nights; $150 for all longer stays",
         [("75.00", 1, 7), ("150.00", 8, None)]),
        ("$75 for stays up to 7 nights, $150 for longer stays",
         [("75.00", 1, 7), ("150.00", 8, None)]),
        ("$75 applies up to 7 nights, thereafter $150",
         [("75.00", 1, 7), ("150.00", 8, None)]),
        ("$75 up to 7 nights; $150 for stays beyond that",
         [("75.00", 1, 7), ("150.00", 8, None)]),
        ("A fee of $40 applies for stays up to 3 days; $90 thereafter",
         [("40.00", 1, 3), ("90.00", 4, None)]),
    ])
    def test_spoken_variants(self, text, expected):
        terms, problems = parse_fee_tiers(text)
        assert problems == []
        assert [(t.amount, t.condition_min, t.condition_max) for t in terms] == expected

    @pytest.mark.parametrize("text,slug", [
        # An open tail with nothing bounding what precedes it cannot be placed.
        ("A pet fee of $150 applies thereafter.",
         "tier_open_tail_without_bounded_opener"),
        # The open tier must FOLLOW the bounded one.
        ("$150 thereafter; $75 fee applies for stays up to 7 nights",
         "tier_prose_ladder_ambiguous"),
    ])
    def test_prose_ladder_fails_closed(self, text, slug):
        terms, problems = parse_fee_tiers(text)
        assert terms == ()
        assert slug in problems

    def test_new_slugs_are_declared(self):
        from services.research_workers.fee_terms import TIER_PARSE_PROBLEMS
        assert "tier_open_tail_without_bounded_opener" in TIER_PARSE_PROBLEMS
        assert "tier_prose_ladder_ambiguous" in TIER_PARSE_PROBLEMS

    def test_the_prose_path_never_re_reads_a_source_that_already_parses(self):
        """Consulted only when the compressed notations formed no ladder, so
        every already-published tiered hotel reads exactly as before."""
        for text, expected in ((HAMPTON, [("75.00", 1, 4), ("125.00", 5, None)]),
                               (NEW_ALBANY_PAYLOAD, [("50.00", 1, 4), ("75.00", 5, None)]),
                               (NEW_ALBANY_RENDERED, [("50.00", 1, 4), ("75.00", 5, None)])):
            terms, problems = parse_fee_tiers(text)
            assert problems == []
            assert [(t.amount, t.condition_min, t.condition_max) for t in terms] == expected

    def test_a_single_spoken_tier_is_still_not_a_ladder(self):
        """A bounded opener with no open tail is one conditional fee. The prose
        path requires BOTH halves, so it declines and the caller keeps its
        ordinary scalar handling."""
        terms, problems = parse_fee_tiers("$75 fee applies for stays up to 7 nights.")
        assert terms == ()
        assert problems == ["tier_notation_unparseable"]

    def test_renders_as_a_faithful_sentence(self):
        """PTF-SONESTA: the source states "per pet" on the first tier and elides
        it on the second, so the sentence shows it exactly where it is stated."""
        tiers = _tiers(SONESTA)
        assert _tiered_fee_sentence(tiers, SONESTA) == (
            "A pet fee of $75 per pet applies for stays of 1–7 nights, and $150 "
            "applies for stays of 8 nights or more.")
        assert tier_fee_range(tiers) == "$75–$150"

    def test_detail_rows_and_basis_row(self):
        rows, _plain, _note = _verified_details(
            {"pets_allowed": "true", "fee_tiers": _tiers(SONESTA),
             "species_allowed": "dogs", "pet_count_limit": "2"})
        d = dict((label, value) for label, value, _c in rows)
        # The stated scope travels with the amount it qualifies; the elided one
        # is not invented for the second tier.
        assert d["Pet charge, 1–7 nights"] == "$75 per pet"
        assert d["Pet charge, 8 nights or more"] == "$150"
        assert "Tiered by stay length" in d["Charge basis"]
        assert "does not state" in d["Charge basis"]


# --------------------------------------------------------------------------- #
# 2. Fails closed.
# --------------------------------------------------------------------------- #

class TestFailsClosed:
    @pytest.mark.parametrize("text,slug", [
        ("$$7(5(1--4n)$$(5+n)", "tier_notation_unparseable"),
        (FLAT, "tier_notation_unparseable"),
        ("$75 for 1-4 nights", "tier_single_only"),
        ("$75 for 4 nights $125 for 9 nights", "tier_missing_range_boundary"),
        ("$75(1-4n)$125(1-4n)", "tier_duplicate_range"),
        ("$75(1-6n)$125(4-9n)", "tier_ranges_overlap"),
        ("$75(4-1n)$125(5+n)", "tier_invalid_range"),
    ])
    def test_problem_slugs(self, text, slug):
        terms, problems = parse_fee_tiers(text)
        assert terms == ()
        assert slug in problems

    def test_no_partial_ladder_is_ever_returned(self):
        """A half-understood ladder is not a fee. Either every tier parses or
        none is published."""
        terms, problems = parse_fee_tiers("$75(1-6n)$125(4-9n)")
        assert problems and terms == ()

    def test_every_problem_is_a_declared_slug(self):
        from services.research_workers.fee_terms import TIER_PARSE_PROBLEMS
        for text in ("$$7(5(1--4n)", FLAT, "$75 for 1-4 nights", "$75(1-4n)$125(1-4n)",
                     "$75(1-6n)$125(4-9n)", "$75(4-1n)$125(5+n)"):
            _t, problems = parse_fee_tiers(text)
            assert set(problems) <= set(TIER_PARSE_PROBLEMS), (text, problems)


# --------------------------------------------------------------------------- #
# 3. Basis is never asserted unless the source states it.
# --------------------------------------------------------------------------- #

class TestBasisNeverInvented:
    def test_compressed_notation_states_no_basis(self):
        assert basis_is_stated(HAMPTON) is False
        assert basis_is_stated(NEW_ALBANY_RENDERED) is False

    def test_explicit_basis_is_recognised(self):
        assert basis_is_stated("$75 per night for 1-4 nights") is True
        assert basis_is_stated("a $50 fee per stay") is True

    def test_summary_never_claims_per_night_or_per_stay(self):
        facts = {"pets_allowed": "true", "fee_tiers": _tiers(HAMPTON),
                 "pet_count_limit": "2", "weight_limit": "75 pounds"}
        summary = _verified_summary(facts, HAMPTON)
        assert "per night" not in summary.lower()
        assert "per stay" not in summary.lower()

    def test_details_say_the_basis_is_not_stated(self):
        rows, _plain, _note = _verified_details(
            {"pets_allowed": "true", "fee_tiers": _tiers(HAMPTON),
             "pet_count_limit": "2", "weight_limit": "75 pounds"})
        basis = dict((label, value) for label, value, _c in rows)["Charge basis"]
        assert "Tiered by stay length" in basis
        assert "does not state" in basis

    def test_facts_chip_says_tiered_not_a_basis(self):
        chips = dict((l, v) for l, v, _c in _verified_facts({"fee_tiers": _tiers(HAMPTON)}))
        assert chips["Charge basis"] == "Tiered by stay length"
        assert chips["Pet charge"] == "$75–$125"


# --------------------------------------------------------------------------- #
# 4. Rendering.
# --------------------------------------------------------------------------- #

class TestRendering:
    def test_preferred_summary_sentence(self):
        assert _tiered_fee_sentence(_tiers(HAMPTON), HAMPTON) == (
            "A pet fee of $75 applies for stays of 1–4 nights, and $125 "
            "applies for stays of 5 nights or more.")

    def test_non_refundable_stated_only_when_the_source_says_so(self):
        text = "Non-refundable Fee $75(1-4n)$125(5+n)"
        assert "non-refundable" in _tiered_fee_sentence(_tiers(text), text)
        assert "non-refundable" not in _tiered_fee_sentence(_tiers(HAMPTON), HAMPTON)

    def test_fee_range_for_the_comparison_table(self):
        assert tier_fee_range(_tiers(HAMPTON)) == "$75–$125"
        assert tier_fee_range(_tiers(NEW_ALBANY_PAYLOAD)) == "$50–$75"

    def test_details_show_one_row_per_tier(self):
        rows = dict((label, value) for label, value, _c in _verified_details(
            {"pets_allowed": "true", "fee_tiers": _tiers(HAMPTON),
             "pet_count_limit": "2", "weight_limit": "75 pounds"})[0])
        assert rows["Pet charge, 1–4 nights"] == "$75"
        assert rows["Pet charge, 5 nights or more"] == "$125"

    def test_full_profile_summary_reads_faithfully(self):
        facts = {"pets_allowed": "true", "fee_tiers": _tiers(HAMPTON),
                 "pet_count_limit": "2", "weight_limit": "75 pounds"}
        summary = _verified_summary(facts, "Non-refundable Fee " + HAMPTON)
        assert summary == (
            "Pets are welcome. A non-refundable pet fee of $75 applies for stays of "
            "1–4 nights, and $125 applies for stays of 5 nights or more. "
            "Maximum pet weight is 75 pounds, with up to 2 pets permitted per room.")


# --------------------------------------------------------------------------- #
# 4b. Source conflicts and capped fees (PTF-FEES-CONFLICT / PTF-FEES-CAP).
#
# Courtyard Columbus Easton published "$50.00 / Per stay" from a source whose
# very next clause reads "$50 dollar per night up to $150". A four-night stay
# is $150 under one sentence and $50 under the other. The attestation RECORDED
# the contradiction; nothing read it, so one reading shipped as fact.
# --------------------------------------------------------------------------- #

COURTYARD_EASTON = (
    "Pet Policy Pets Welcome Pets are allowed at this property. There is $50 dollar "
    "per night up to $150 fee Non-Refundable Pet Fee Per Stay: $50.00 "
    "Maximum Pet Weight: 100.0lbs Maximum Number of Pets in Room: 2 Parking")
RESIDENCE_EASTON = (
    "Pet Policy Pets Welcome Pets are allowed at this property. There is $50 dollar "
    "per night up to $150 fee Non-Refundable Pet Fee Per Night: $50.00 "
    "Maximum Pet Weight: 50.0lbs Maximum Number of Pets in Room: 2 Parking")
SHERATON_WORTHINGTON = (
    "Pet Policy Pets Welcome Small pets under 50 lbs are welcome. $75 nonrefundable "
    "fees charged per pet. Non-Refundable Pet Fee Per Stay: $75.00 "
    "Maximum Pet Weight: 50.0lbs Maximum Number of Pets in Room: 2 Parking")


def _attestation(contradictions):
    return {"attestation_id": "attest-test", "attestation_hash": "sha256:" + "a" * 64,
            "listing_key": "k", "listing_name": "Test Hotel",
            "official_url": "https://www.marriott.com/en-us/hotels/cmhce-x/overview/",
            "observed_at": "2026-07-29", "capture_method": "MANUAL_ATTESTATION",
            "source_type": "MANUAL_OFFICIAL_ATTESTATION",
            "affirmation": {"operator_id": "jfields80", "attested_at": "t"},
            "approval": {"state": "APPROVED", "approver_id": "j", "approved_at": "t",
                         "approval_record_id": "APR-x"},
            "publishable": True, "contradictions": contradictions, "fee_amounts": []}


class TestFeeCapDetection:
    @pytest.mark.parametrize("text,amount", [
        ("There is $50 dollar per night up to $150 fee", "150.00"),
        ("up to $150 fee", "150.00"),
        ("fee not to exceed $200 per stay", "200.00"),
        ("pet fee capped at $ 120", "120.00"),
        ("up to a maximum of $99.50", "99.50"),
    ])
    def test_cap_wording_variants(self, text, amount):
        from services.research_workers.fee_terms import detect_fee_cap
        assert detect_fee_cap(text)[0] == amount

    def test_a_bare_number_is_never_a_cap(self):
        """"Earn up to 150,000 Bonus Points" sits on the same page."""
        from services.research_workers.fee_terms import detect_fee_cap
        assert detect_fee_cap("Earn up to 150,000 Marriott Bonvoy Bonus Points") == (None, "")
        assert detect_fee_cap("Up to 2 pets are allowed per room") == (None, "")

    def test_cap_quote_is_verbatim(self):
        from services.research_workers.fee_terms import detect_fee_cap
        amount, quote = detect_fee_cap(RESIDENCE_EASTON)
        assert amount == "150.00"
        assert quote in " ".join(RESIDENCE_EASTON.split())


class TestSourceConflictWithholdsTheFee:
    def test_courtyard_easton_publishes_no_fee(self):
        c = build_candidate(
            _attestation(["conflicting_fee_basis_per_stay_vs_fee_basis_per_night"]),
            COURTYARD_EASTON)
        facts = dict(c["pet_facts"])
        assert "pet_fee" not in facts and "fee_basis" not in facts
        assert "fee_cap" not in facts          # a cap on a withheld fee is meaningless
        assert facts["fee_conflict"]["reason"] == "conflicting_fee_terms_in_official_source"

    def test_sheraton_worthington_publishes_no_fee(self):
        c = build_candidate(
            _attestation(["conflicting_fee_basis_per_pet_vs_fee_basis_per_stay"]),
            SHERATON_WORTHINGTON)
        facts = dict(c["pet_facts"])
        assert "pet_fee" not in facts and "fee_basis" not in facts
        assert "per_pet" in facts["fee_conflict"]["detail"][0]

    def test_both_quotations_are_preserved(self):
        c = build_candidate(
            _attestation(["conflicting_fee_basis_per_stay_vs_fee_basis_per_night"]),
            COURTYARD_EASTON)
        quote = dict((k, v) for k, v in
                     (tuple(p) for p in c["proposed_fields"]))["pet_policy"]
        assert "per night up to $150" in quote
        assert "Non-Refundable Pet Fee Per Stay: $50.00" in quote

    def test_the_rest_of_the_policy_still_publishes(self):
        """The hotel is not withdrawn -- only the fee is withheld."""
        facts = dict(build_candidate(
            _attestation(["conflicting_fee_basis_per_stay_vs_fee_basis_per_night"]),
            COURTYARD_EASTON)["pet_facts"])
        assert facts["pets_allowed"] == "true"
        assert facts["pet_count_limit"] == "2"
        assert facts["weight_limit"] == "100.0 pounds"

    def test_public_wording_states_the_conflict_and_no_amount(self):
        facts = dict(build_candidate(
            _attestation(["conflicting_fee_basis_per_stay_vs_fee_basis_per_night"]),
            COURTYARD_EASTON)["pet_facts"])
        summary = _verified_summary(facts, COURTYARD_EASTON)
        assert ("Official source contains conflicting pet-fee terms. See the exact "
                "recorded policy wording or confirm with the hotel.") in summary
        assert "$50" not in summary and "$150" not in summary
        assert "per stay" not in summary.lower() and "per night" not in summary.lower()

    def test_an_unrelated_contradiction_does_not_withhold_the_fee(self):
        """multiple_fee_amounts fires on parking and restaurant reviews too, so
        it must never gate a fee on its own."""
        facts = dict(build_candidate(
            _attestation(["multiple_fee_amounts:150,20,30.00,50,50.00"]),
            RESIDENCE_EASTON)["pet_facts"])
        assert facts["pet_fee"] == "$50.00"
        assert "fee_conflict" not in facts


class TestCappedFeePublishesBothNumbers:
    def test_residence_inn_easton_keeps_its_rate_and_its_ceiling(self):
        facts = dict(build_candidate(_attestation([]), RESIDENCE_EASTON)["pet_facts"])
        assert facts["pet_fee"] == "$50.00"
        assert facts["fee_basis"] == "per night"
        assert facts["fee_cap"]["amount"] == "150.00"
        assert facts["fee_cap"]["evidence_quote"] == "up to $150"

    def test_summary_states_the_ceiling_in_the_same_sentence_as_the_rate(self):
        facts = dict(build_candidate(_attestation([]), RESIDENCE_EASTON)["pet_facts"])
        assert _verified_summary(facts, RESIDENCE_EASTON) == (
            "Pets are welcome. A $50 non-refundable fee applies per night, up to a "
            "maximum of $150. Maximum pet weight is 50 pounds, with up to 2 pets "
            "permitted per room.")

    def test_chip_and_detail_row_show_the_ceiling(self):
        facts = dict(build_candidate(_attestation([]), RESIDENCE_EASTON)["pet_facts"])
        chips = dict((l, v) for l, v, _c in _verified_facts(facts))
        assert chips["Pet charge"] == "$50.00 (max $150)"
        rows = dict((l, v) for l, v, _c in _verified_details(facts)[0])
        assert rows["Maximum total"] == "$150"
        assert rows["Pet charge"] == "$50.00"

    def test_a_hotel_without_a_stated_cap_gains_none(self):
        facts = dict(build_candidate(_attestation([]), SHERATON_WORTHINGTON.replace(
            "$75 nonrefundable fees charged per pet. ", ""))["pet_facts"])
        assert "fee_cap" not in facts


# --------------------------------------------------------------------------- #
# 5. Scalar hotels are untouched.
# --------------------------------------------------------------------------- #

class TestScalarUnchanged:
    SCALAR = {"pets_allowed": "true", "pet_fee": "$50.00", "fee_basis": "per night",
              "pet_count_limit": "2", "weight_limit": "40.0 pounds"}

    def test_flat_scalar_summary_is_unchanged(self):
        quote = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Night: $50.00 "
                 "Maximum Pet Weight: 40.0lbs Maximum Number of Pets in Room: 2")
        assert _verified_summary(self.SCALAR, quote) == (
            "Pets are welcome. A $50 non-refundable fee applies per night. "
            "Maximum pet weight is 40 pounds, with up to 2 pets permitted per room.")

    def test_scalar_chips_and_rows_unchanged(self):
        chips = dict((l, v) for l, v, _c in _verified_facts(self.SCALAR))
        assert chips["Pet charge"] == "$50.00"
        assert chips["Charge basis"] == "Per night"
        rows = dict((l, v) for l, v, _c in _verified_details(self.SCALAR)[0])
        assert rows["Pet charge"] == "$50.00"
        assert rows["Charge basis"] == "Per night"

    # PTF-PROMOTION-002: the published stay-length ladders, listed explicitly so
    # a record gaining or losing one is a reviewable diff rather than a silently
    # moving number. A hotel acquiring tiers its source never stated is the
    # flattening bug in reverse, and that is what this fixture pins.
    TIERED_IDENTITIES = [
        # PTF-COLUMBUS-INTEGRATE-UNRESOLVED-001 promotion.
        "candlewood suites columbus grove city",
        # PTF-COLUMBUS-AUTHORITY-APPLY-002 promotions; each states a
        # stay-length ladder on its own official page.
        "doubletree by hilton columbus dublin",
        "embassy suites by hilton columbus dublin",
        # PTF-COLUMBUS-IDENTITY-CLEANUP-001 promotion.
        "embassy suites columbus airport corporate exchange",
        "hampton inn and suites columbus downtown",
        "hampton inn and suites columbus easton area",
        "hampton inn and suites columbus hilliard",
        "hampton inn and suites columbus polaris",
        "hampton inn columbus airport",
        "hilton garden inn columbus airport",
        "hilton garden inn columbus grove city",
        "hilton garden inn columbus polaris",
        "hilton garden inn columbus university area",
        "home2 suites by hilton columbus airport east broad",
        "home2 suites by hilton columbus downtown",
        "home2 suites by hilton columbus dublin",
        "home2 suites by hilton reynoldsburg columbus east",
        "home2 suites new albany columbus",
        "homewood suites by hilton columbus dublin",
        "homewood suites by hilton columbus hilliard",
        "homewood suites by hilton columbus osu oh",
        "homewood suites by hilton columbus polaris oh",
        "sonesta simply suites columbus airport gahanna",
        "sonesta simply suites dublin columbus",
        "tru by hilton columbus east broad",
    ]

    def test_only_the_genuinely_tiered_hotels_carry_tiers(self):
        """Exactly the published properties that state a stay-length ladder.
        Every other record stays scalar."""
        pkg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
                          "pettripfinder" / "hotel_policy_facts.json")
                         .read_text(encoding="utf-8-sig"))
        assert len(pkg["hotels"]) == 85
        tiered = sorted(h["key"] for h in pkg["hotels"] if h.get("facts", {}).get("fee_tiers"))
        assert tiered == self.TIERED_IDENTITIES
        for h in pkg["hotels"]:
            facts = h.get("facts", {})
            # A record may carry a ladder OR a scalar fee, never both. A tiered
            # CEILING over a scalar fee is a different shape and is allowed --
            # see test_a_capped_scalar_fee_is_not_a_ladder.
            assert not (facts.get("fee_tiers") and facts.get("pet_fee")), h["key"]

    def test_a_capped_scalar_fee_is_not_a_ladder(self):
        """fee_cap_tiers is a ceiling schedule over a scalar fee, never a ladder.

        Candlewood charges $25 per night under a ceiling that itself varies with
        stay length. Reading that ceiling as a fee ladder would treble a
        one-night stay, so the two shapes must stay distinct: a capped scalar
        keeps its fee and basis and must never acquire synthetic fee_tiers.
        """
        pkg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
                          "pettripfinder" / "hotel_policy_facts.json")
                         .read_text(encoding="utf-8-sig"))
        capped = [h for h in pkg["hotels"] if h.get("facts", {}).get("fee_cap_tiers")]
        assert capped, "expected at least one capped-scalar record"
        for h in capped:
            facts = h["facts"]
            assert not facts.get("fee_tiers"), h["key"]
            assert facts.get("pet_fee"), h["key"]
            assert facts.get("fee_basis"), h["key"]
            for cap in facts["fee_cap_tiers"]:
                assert cap.get("amount"), h["key"]

    def test_every_published_tier_ladder_is_contiguous_and_non_overlapping(self):
        pkg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
                          "pettripfinder" / "hotel_policy_facts.json")
                         .read_text(encoding="utf-8-sig"))
        for h in pkg["hotels"]:
            tiers = h.get("facts", {}).get("fee_tiers") or []
            if not tiers:
                continue
            ordered = sorted(tiers, key=lambda t: t["condition_min"])
            for a, b in zip(ordered, ordered[1:]):
                assert a["condition_max"] is not None, h["key"]
                assert b["condition_min"] == a["condition_max"] + 1, h["key"]
            assert ordered[-1]["condition_max"] is None, h["key"]
            for t in ordered:
                # Ranges and amounts must be usable, not merely present.
                assert isinstance(t["condition_min"], int) and t["condition_min"] >= 1, h["key"]
                if t["condition_max"] is not None:
                    assert t["condition_max"] >= t["condition_min"], h["key"]
                assert Decimal(str(t["amount"])) > 0, h["key"]
                # Basis metadata must be internally consistent. A source that
                # states the recurrence is carried through; one that does not
                # must not smuggle a recurrence in beside basis_stated=False,
                # because the sentence would then assert a per-stay or
                # per-night charge the official page never made.
                assert isinstance(t["basis_stated"], bool), h["key"]
                stated = (t.get("stated_basis") or "").strip()
                if t["basis_stated"]:
                    assert stated, "%s: basis_stated=True without a basis" % h["key"]
                else:
                    assert not stated, "%s: unstated basis carries %r" % (h["key"], stated)
            # All rungs must agree about whether a basis was stated -- a ladder
            # whose rungs disagree is not one the summary can describe.
            assert len({t["basis_stated"] for t in ordered}) == 1, h["key"]
            if ordered[0]["basis_stated"]:
                assert len({(t.get("stated_basis") or "").strip().lower()
                            for t in ordered}) == 1, h["key"]

    def test_every_published_hotel_still_renders(self):
        pkg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
                          "pettripfinder" / "hotel_policy_facts.json")
                         .read_text(encoding="utf-8-sig"))
        for h in pkg["hotels"]:
            s = _verified_summary(h.get("facts", {}), h.get("evidence_quote", "") or "")
            assert s and "None" not in s, h["key"]
