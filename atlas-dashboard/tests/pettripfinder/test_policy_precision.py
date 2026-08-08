"""PTF-POLICY-PRECISION-001 -- three distinctions the renderer could not make.

Each of these was a real sentence a real property published that the profile
could not say back correctly:

  * "Up to two pets are permitted per SUITE" rendered as "per room". A suite is
    not a room, and for an all-suite property the difference is the promise.
  * "no breed or weight restrictions" rendered as the same dim "Not stated" that
    silence renders as, turning an affirmative answer into an apparent gap.
  * "Non-refundable Fee: $100", with no per-night or per-stay qualifier, rendered
    as "a $100 fee applies" -- which reads as a complete answer to a question
    the source never answered.

The tests also pin the other half: records that state a basis, use rooms, or say
nothing about weight must render exactly as they did before.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.hotel_profile import (
    UNRESTRICTED_BREED_DISPLAY,
    UNRESTRICTED_WEIGHT_DISPLAY,
    _verified_facts,
    _verified_summary,
    weight_display,
)
from scripts.pettripfinder.site_data import _POLICY_FIELDS

SONESTA_TIERS = [
    {"amount": "75.00", "basis": "one_time", "basis_stated": False, "boundary_unit": "nights",
     "condition_min": 1, "condition_max": 7, "condition_type": "stay_length_range",
     "currency": "USD", "evidence_quote": "$75 fee applies for stays up to 7 nights",
     "role": "ONE_TIME_CHARGE", "scope": "unstated"},
    {"amount": "150.00", "basis": "one_time", "basis_stated": False, "boundary_unit": "nights",
     "condition_min": 8, "condition_max": None, "condition_type": "stay_length_range",
     "currency": "USD", "evidence_quote": "$150 for all longer stays",
     "role": "ONE_TIME_CHARGE", "scope": "unstated"},
]
SONESTA_FACTS = {"pets_allowed": "true", "pet_count_limit": "2", "pet_count_scope": "suite",
                 "fee_tiers": SONESTA_TIERS, "weight_limit_stated_none": "true",
                 "breed_restrictions_stated_none": "true"}
SONESTA_QUOTE = ("Sonesta Simply Suites Columbus Airport Gahanna is pet-friendly and welcomes "
                 "well-mannered pets, with no breed or weight restrictions. Up to two pets are "
                 "permitted per suite. $75 fee applies for stays up to 7 nights; $150 for all "
                 "longer stays.")

LEVEQUE_FACTS = {"pets_allowed": "true", "pet_count_limit": "2", "pet_fee": "$100.00",
                 "weight_limit": "80.0 pounds", "weight_limit_operator": "lte"}
LEVEQUE_QUOTE = ("PET POLICY Pets Welcome! Maximum 2 Pets Per Room Non-refundable Fee: $100 "
                 "Size Restriction: 80 pounds")


def chips(facts):
    return dict((c[0], c[1]) for c in _verified_facts(facts))


# --------------------------------------------------------------------------- #
# 1. Pet count scope.
# --------------------------------------------------------------------------- #

class TestCountScope:

    def test_sonesta_says_per_suite_not_per_room(self):
        summary = _verified_summary(SONESTA_FACTS, SONESTA_QUOTE)
        assert "per suite" in summary
        assert "per room" not in summary

    def test_an_absent_scope_still_says_per_room(self):
        summary = _verified_summary({"pets_allowed": "true", "pet_count_limit": "2"}, "")
        assert "Up to 2 pets permitted per room." in summary

    def test_an_explicit_room_scope_reads_identically_to_an_absent_one(self):
        base = {"pets_allowed": "true", "pet_count_limit": "2"}
        assert _verified_summary(dict(base, pet_count_scope="room"), "") == \
            _verified_summary(base, "")

    def test_an_unknown_scope_falls_back_to_room_rather_than_echoing_it(self):
        """A junk value must never reach a consumer sentence."""
        summary = _verified_summary(
            {"pets_allowed": "true", "pet_count_limit": "2", "pet_count_scope": "villa"}, "")
        assert "per room" in summary and "villa" not in summary

    def test_the_verb_agrees_with_the_count(self):
        one = _verified_summary({"pets_allowed": "true", "pet_count_limit": "1",
                                 "weight_limit_stated_none": "true"}, "")
        many = _verified_summary({"pets_allowed": "true", "pet_count_limit": "2",
                                  "pet_count_scope": "suite",
                                  "weight_limit_stated_none": "true"}, "")
        assert "One pet is permitted" in one
        assert "2 pets are permitted" in many          # not "2 pets is permitted"


# --------------------------------------------------------------------------- #
# 2. Explicitly unrestricted.
# --------------------------------------------------------------------------- #

class TestExplicitlyUnrestricted:

    def test_sonesta_weight_chip_states_the_property_said_there_is_no_limit(self):
        assert chips(SONESTA_FACTS)["Weight limit"] == UNRESTRICTED_WEIGHT_DISPLAY
        assert UNRESTRICTED_WEIGHT_DISPLAY != "Not stated"

    def test_sonesta_breed_chip_states_the_property_said_there_are_none(self):
        assert chips(SONESTA_FACTS)["Breed restrictions"] == UNRESTRICTED_BREED_DISPLAY

    def test_silence_still_renders_as_not_stated(self):
        quiet = {"pets_allowed": "true", "pet_count_limit": "2", "pet_fee": "$50.00",
                 "fee_basis": "per stay"}
        assert chips(quiet)["Weight limit"] == "Not stated"
        assert "Breed restrictions" not in chips(quiet)

    def test_a_breed_chip_is_not_added_to_records_that_merely_list_restrictions(self):
        """Emitting it for every record would rewrite pages this change must not
        touch; the chip exists for the affirmative statement only."""
        listed = {"pets_allowed": "true", "breed_restrictions": "No aggressive breeds",
                  "pet_fee": "$50.00", "fee_basis": "per stay"}
        assert "Breed restrictions" not in chips(listed)

    def test_a_stated_numeric_limit_beats_the_unrestricted_flag(self):
        """A record carrying both is contradictory; the number wins because it is
        the more specific claim, and the contradiction is visible rather than
        hidden behind a reassuring phrase."""
        assert weight_display({"weight_limit": "50.0 pounds",
                               "weight_limit_stated_none": "true"}) == "50.0 pounds"

    def test_unrestricted_is_never_inferred_from_an_absent_weight(self):
        assert weight_display({"pets_allowed": "true"}) == ""


# --------------------------------------------------------------------------- #
# 3. Fee basis ambiguity.
# --------------------------------------------------------------------------- #

class TestFeeBasisAmbiguity:

    def test_leveque_renders_the_required_sentence(self):
        assert _verified_summary(LEVEQUE_FACTS, LEVEQUE_QUOTE) == (
            "Pets are welcome. A $100 non-refundable pet fee is stated; the fee basis is not "
            "specified. Maximum pet weight is 80 pounds, with up to 2 pets permitted per room.")

    def test_leveque_never_claims_a_basis(self):
        summary = _verified_summary(LEVEQUE_FACTS, LEVEQUE_QUOTE).lower()
        for invented in ("per stay", "per night", "per pet"):
            assert invented not in summary

    def test_a_stated_basis_renders_exactly_as_before(self):
        stated = {"pets_allowed": "true", "pet_fee": "$75.00", "fee_basis": "per stay"}
        summary = _verified_summary(stated, "")
        assert "A $75 fee applies per stay." in summary
        assert "not specified" not in summary

    def test_the_caveat_survives_a_cap_without_swallowing_it(self):
        with_cap = {"pets_allowed": "true", "pet_fee": "$50.00",
                    "fee_cap": {"amount": "150.00"}}
        summary = _verified_summary(with_cap, "")
        assert "up to a maximum of $150" in summary
        assert summary.rstrip().endswith("the fee basis is not specified.")

    def test_a_tiered_fee_is_not_given_the_scalar_caveat(self):
        summary = _verified_summary(SONESTA_FACTS, SONESTA_QUOTE)
        assert "the fee basis is not specified" not in summary


# --------------------------------------------------------------------------- #
# 4. Sonesta's ladder.
# --------------------------------------------------------------------------- #

class TestSonestaLadder:

    def test_both_rungs_render_with_their_stay_windows(self):
        summary = _verified_summary(SONESTA_FACTS, SONESTA_QUOTE)
        assert "$75 applies for stays of 1–7 nights" in summary
        assert "$150 applies for stays of 8 nights or more" in summary

    def test_no_none_placeholder_reaches_a_consumer_sentence(self):
        """The first attempt at this ladder rendered "for stays of None nights or
        more" -- a Python repr in consumer prose. The check is for a placeholder
        standing where a value belongs, NOT for the word: the breed chip legit-
        imately reads "None stated by the property"."""
        summary = _verified_summary(SONESTA_FACTS, SONESTA_QUOTE)
        assert "None" not in summary
        for _label, value, _tone in _verified_facts(SONESTA_FACTS):
            assert str(value).strip() != "None"
            assert "None nights" not in str(value)

    def test_no_scalar_fee_and_no_inferred_scope_or_refundability(self):
        summary = _verified_summary(SONESTA_FACTS, SONESTA_QUOTE)
        assert "non-refundable" not in summary          # the source never says it
        assert "per pet" not in summary and "for the room" not in summary
        assert chips(SONESTA_FACTS)["Pet charge"] == "$75–$150"
        assert chips(SONESTA_FACTS)["Charge basis"] == "Tiered by stay length"


# --------------------------------------------------------------------------- #
# 5. The vocabulary, and what did NOT change.
# --------------------------------------------------------------------------- #

class TestVocabularyAndBlastRadius:

    @pytest.mark.parametrize("field", ["pet_count_scope", "weight_limit_stated_none",
                                       "breed_restrictions_stated_none"])
    def test_each_new_name_is_promotable(self, field):
        assert field in _POLICY_FIELDS

    def test_the_only_summaries_that_change_are_fees_with_no_stated_basis(self):
        """Measured against the committed authority, not asserted from memory."""
        import json
        import pathlib

        from scripts.pettripfinder.site_data import normalize_name, read_production_rows

        root = pathlib.Path(__file__).resolve().parents[2]
        pkg = json.loads((root / "launch_packages/pettripfinder/hotel_policy_facts.json")
                         .read_text(encoding="utf-8"))
        rows = {normalize_name(r["name"]): r for r in read_production_rows()
                if r["category"] == "pet-friendly-hotels"}
        affected = [h["key"] for h in pkg["hotels"]
                    if h["facts"].get("pet_fee") and not h["facts"].get("fee_basis")]
        # 9 when PTF-POLICY-PRECISION-001 measured this; 10 since
        # PTF-COLUMBUS-PROMOTION-002 published Hotel LeVeque, whose source states
        # a $100 fee and no basis at all. The count is asserted rather than
        # ranged so a new no-basis record cannot arrive unnoticed.
        assert len(affected) == 10
        for h in pkg["hotels"]:
            summary = _verified_summary(dict(h["facts"]), h.get("evidence_quote") or "")
            if h["key"] in affected:
                assert "the fee basis is not specified" in summary, h["key"]
            else:
                assert "the fee basis is not specified" not in summary, h["key"]
            assert rows.get(h["key"]) is not None

    def test_south_wind_remains_unpublishable(self):
        """No room-designation support was added, so the fact still has no home."""
        import csv
        import json
        import pathlib

        from scripts.pettripfinder.site_data import normalize_name

        root = pathlib.Path(__file__).resolve().parents[2]
        seed = {normalize_name(r["name"]) for r in csv.DictReader(
            (root / "launch_packages/pettripfinder/seed_businesses.csv").open(encoding="utf-8"))}
        pkg = {h["key"] for h in json.loads(
            (root / "launch_packages/pettripfinder/hotel_policy_facts.json")
            .read_text(encoding="utf-8"))["hotels"]}
        assert normalize_name("South Wind Motel") not in seed
        assert normalize_name("South Wind Motel") not in pkg
        for unimplemented in ("pet_room_restriction", "eligible_room_types",
                              "reservation_requirement"):
            assert unimplemented not in _POLICY_FIELDS

    def test_both_promoted_hotels_carry_exactly_their_approved_facts(self):
        """PTF-COLUMBUS-PROMOTION-002 replaced this file's earlier "neither hotel
        reached a tracked authority" assertion, which was true until they were
        promoted. The successor is stronger: they are published, and they carry
        the approved facts and nothing else."""
        import json
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[2]
        pkg = json.loads((root / "launch_packages/pettripfinder/hotel_policy_facts.json")
                         .read_text(encoding="utf-8"))
        by_key = {h["key"]: h for h in pkg["hotels"]}
        assert len(pkg["hotels"]) == 77

        sonesta = by_key["sonesta simply suites columbus airport gahanna"]
        assert set(sonesta["facts"]) == {"pets_allowed", "pet_count_limit", "pet_count_scope",
                                         "weight_limit_stated_none",
                                         "breed_restrictions_stated_none", "fee_tiers"}
        assert sonesta["facts"]["pet_count_scope"] == "suite"
        assert [t["amount"] for t in sonesta["facts"]["fee_tiers"]] == ["75.00", "150.00"]

        leveque = by_key["hotel leveque autograph collection"]
        assert set(leveque["facts"]) == {"pets_allowed", "pet_count_limit", "pet_count_scope",
                                         "pet_fee", "weight_limit", "weight_limit_operator"}
        assert "fee_basis" not in leveque["facts"]

        for record in (sonesta, leveque):
            for never in ("species_allowed", "pet_deposit", "breed_restrictions"):
                assert never not in record["facts"], (record["key"], never)
