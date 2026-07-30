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

import pytest

from scripts.pettripfinder.hotel_profile import (
    _tiered_fee_sentence, _verified_details, _verified_facts, _verified_summary,
    tier_fee_range,
)
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

    def test_only_the_genuinely_tiered_hotels_carry_tiers(self):
        """Exactly three published properties state a stay-length ladder. Every
        other record stays scalar -- a hotel gaining tiers without its source
        stating them would be the flattening bug in reverse."""
        pkg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
                          "pettripfinder" / "hotel_policy_facts.json")
                         .read_text(encoding="utf-8-sig"))
        assert len(pkg["hotels"]) == 33
        tiered = sorted(h["key"] for h in pkg["hotels"] if h.get("facts", {}).get("fee_tiers"))
        assert tiered == ["hampton inn columbus airport",
                          "hilton garden inn columbus airport",
                          "home2 suites new albany columbus"]
        for h in pkg["hotels"]:
            facts = h.get("facts", {})
            # A record may carry a ladder OR a scalar fee, never both.
            assert not (facts.get("fee_tiers") and facts.get("pet_fee")), h["key"]

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
            assert all(t["basis_stated"] is False for t in tiers), h["key"]

    def test_every_published_hotel_still_renders(self):
        pkg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
                          "pettripfinder" / "hotel_policy_facts.json")
                         .read_text(encoding="utf-8-sig"))
        for h in pkg["hotels"]:
            s = _verified_summary(h.get("facts", {}), h.get("evidence_quote", "") or "")
            assert s and "None" not in s, h["key"]
