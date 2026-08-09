"""PTF-COLUMBUS-HYATT-002 -- two weight limits at once, and an additional fee.

Both extensions exist because five Hyatt pages state something the schema could
not carry, and in both cases the unrepresentable half was the half that protects
the reader.

**Two weight limits.** Every Hyatt page in the manual-evidence batch states
"Individual pet weight limit: 50 Pounds" AND "Combined pets weight limit: 75
Pounds". Publishing only the 75 tells the owner of a 60 lb dog they are
welcome. Publishing only the 50 hides that two 40 lb dogs are refused. There
was no third option: one ``weight_limit`` field, one operator.

**An additional fee.** Two of those pages read "7-30 nights + additional
cleaning fee: $200 / STAY" and two read "7-30 nights (includes cleaning fee):
$200 / STAY". Identical number, opposite meaning. Rendered identically, the
first understates a two-week stay by the entire $100 base fee.

The tests that matter most here are the ones that try to break the
distinctions: a combined limit mislabelled as individual, an additional fee
shown as a total, a legacy record silently changing, one limit fabricating the
other.
"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

from scripts.pettripfinder.hotel_profile import (
    _verified_details, _verified_summary, combined_weight_display,
    combined_weight_phrase, has_combined_weight, tier_fee_range,
    weight_conflict_reason, weight_display,
)

_REPO = pathlib.Path(__file__).resolve().parents[2]


def facts(**over):
    base = {"pets_allowed": "true", "species_allowed": "dogs",
            "pet_count_limit": "2", "pet_count_scope": "room",
            "weight_limit": "50 pounds", "weight_limit_combined": "75 pounds"}
    base.update(over)
    return base


def rows(f):
    return {r[0]: r[1] for r in _verified_details(f)[0]}


def tier(amount, lo, hi, *, additive=False):
    t = {"amount": amount, "currency": "USD", "condition_type": "stay_length_range",
         "condition_min": lo, "condition_max": hi, "boundary_unit": "nights",
         "basis_stated": True, "stated_basis": "per stay", "role": "ONE_TIME_CHARGE"}
    if additive:
        t["additive"] = True
    return t


# --------------------------------------------------------------------------- #
# Dual weight
# --------------------------------------------------------------------------- #

class TestBothLimitsSurvive:

    def test_both_numbers_reach_the_summary(self):
        s = _verified_summary(facts())
        assert "50 pounds" in s and "75 pounds" in s

    def test_both_numbers_reach_the_detail_table(self):
        r = rows(facts())
        assert r["Individual weight limit"] == "50 pounds per pet"
        assert r["Combined weight limit"] == "75 pounds for all pets together"

    def test_neither_value_overwrites_the_other(self):
        r = rows(facts(weight_limit="50 pounds", weight_limit_combined="75 pounds"))
        assert "75" not in r["Individual weight limit"]
        assert "50" not in r["Combined weight limit"]

    def test_the_combined_limit_is_never_described_as_per_pet(self):
        """The whole point. A reader must not be able to read 75 as a per-animal
        ceiling anywhere on the page."""
        f = facts()
        text = _verified_summary(f) + " " + json.dumps(rows(f))
        assert "75 pounds for all pets together" in text
        for wrong in ("each pet may weigh up to 75", "Each pet must weigh under 75",
                      "75 pounds per pet", "Maximum pet weight is 75"):
            assert wrong.lower() not in text.lower()

    def test_the_individual_limit_is_marked_as_per_pet_when_a_combined_one_exists(self):
        assert rows(facts())["Individual weight limit"].endswith("per pet")


class TestOperatorsStayDistinct:

    def test_strict_individual_is_not_rendered_as_inclusive(self):
        """Hyatt Place Dublin's prose: each dog "less than 50 lbs"."""
        s = _verified_summary(facts(weight_limit_operator="lt"))
        assert "must weigh under 50 pounds" in s
        assert "up to 50 pounds" not in s
        assert rows(facts(weight_limit_operator="lt"))["Individual weight limit"] \
            == "Under 50 pounds"

    def test_inclusive_individual_is_not_rendered_as_strict(self):
        s = _verified_summary(facts())
        assert "may weigh up to 50 pounds" in s
        assert "under 50 pounds" not in s

    def test_strict_combined_is_available_and_distinct(self):
        f = facts(weight_limit_combined_operator="lt")
        assert combined_weight_phrase(f) == "under 75 pounds"
        assert combined_weight_display(f) == "Under 75 pounds for all pets together"
        assert "under 75 pounds" in _verified_summary(f)

    def test_inclusive_combined_never_says_under(self):
        assert "under" not in combined_weight_display(facts()).lower()

    @pytest.mark.parametrize("ind,comb", [("", ""), ("lt", ""), ("", "lt"), ("lt", "lt")])
    def test_every_operator_pairing_keeps_the_two_numbers_apart(self, ind, comb):
        f = facts(weight_limit_operator=ind, weight_limit_combined_operator=comb)
        r = rows(f)
        assert "50" in r["Individual weight limit"] and "75" not in r["Individual weight limit"]
        assert "75" in r["Combined weight limit"] and "50" not in r["Combined weight limit"]


class TestMissingHalvesAreNeverFabricated:

    def test_an_individual_only_record_invents_no_combined_limit(self):
        f = facts(); f.pop("weight_limit_combined")
        assert not has_combined_weight(f)
        assert "Combined weight limit" not in rows(f)
        assert "combined" not in _verified_summary(f).lower()

    def test_a_combined_only_record_invents_no_individual_limit(self):
        f = facts(); f.pop("weight_limit")
        s = _verified_summary(f)
        assert "75 pounds" in s
        assert "50" not in s
        assert rows(f)["Individual weight limit"].lower().startswith("not stated")

    def test_a_combined_only_record_is_not_treated_as_stating_nothing(self):
        """`_STATED_FIELDS` decides whether a record is 'sparse'. A combined
        limit is a stated fact, and calling it sparse printed 'weight limit:
        Not stated' on a page that carries one."""
        f = {"pets_allowed": "true", "weight_limit_combined": "75 pounds"}
        assert "did not state" not in _verified_summary(f)


class TestTheDoubleCombinedRecordIsRefused:
    """The one combination that could be read two ways."""

    def test_legacy_combined_operator_plus_new_field_is_a_conflict(self):
        reason = weight_conflict_reason(facts(weight_limit_operator="combined"))
        assert "two different combined limits" in reason

    def test_a_clean_record_reports_no_conflict(self):
        assert weight_conflict_reason(facts()) == ""
        assert weight_conflict_reason(facts(weight_limit_operator="lt")) == ""

    def test_an_unknown_combined_operator_is_refused(self):
        assert "unsupported" in weight_conflict_reason(
            facts(weight_limit_combined_operator="approximately"))

    def test_a_legacy_record_with_no_combined_field_is_never_flagged(self):
        assert weight_conflict_reason(
            {"weight_limit": "80 pounds", "weight_limit_operator": "combined"}) == ""


class TestLegacyRecordsDoNotMove:

    def test_the_old_combined_form_renders_exactly_as_before(self):
        """Drury Plaza, Candlewood Grove City and Hampton Canal Winchester all
        express a combined limit the only way that used to exist."""
        f = {"pets_allowed": "true", "species_allowed": "dogs and cats",
             "pet_count_limit": "2", "pet_count_scope": "room",
             "weight_limit": "80 pounds", "weight_limit_operator": "combined"}
        assert weight_display(f) == "80 pounds combined"
        assert rows(f)["Weight restriction"] == "80 pounds combined"
        assert "Combined weight limit" not in rows(f)
        assert "combined weight limit of 80 pounds" in _verified_summary(f)

    def test_a_plain_individual_record_renders_exactly_as_before(self):
        f = {"pets_allowed": "true", "pet_count_limit": "2", "weight_limit": "40.0 pounds"}
        assert rows(f)["Weight restriction"] == "40.0 pounds"
        assert "Individual weight limit" not in rows(f)

    def test_the_label_only_changes_where_a_combined_limit_exists(self):
        assert "Weight restriction" in rows({"weight_limit": "40.0 pounds"})
        assert "Weight restriction" not in rows(facts())


class TestEveryPublishedRecordIsUnaffected:
    """Run the real authority. A schema extension that moved a live page would
    show up here rather than in a screenshot."""

    def _pkg(self):
        return json.loads((_REPO / "launch_packages" / "pettripfinder"
                           / "hotel_policy_facts.json").read_text("utf-8"))["hotels"]

    def test_no_published_record_reports_a_weight_conflict(self):
        for h in self._pkg():
            assert weight_conflict_reason(h.get("facts") or {}) == "", h["key"]

    def test_no_published_record_silently_gains_a_combined_row(self):
        for h in self._pkg():
            f = h.get("facts") or {}
            if not has_combined_weight(f):
                assert "Combined weight limit" not in rows(f), h["key"]


# --------------------------------------------------------------------------- #
# Additive fees
# --------------------------------------------------------------------------- #

class TestAnAdditionalFeeIsNeverATotal:

    ADDITIVE = [tier("100.00", 1, 6), tier("200.00", 7, 30, additive=True)]
    INCLUSIVE = [tier("100.00", 1, 6), tier("200.00", 7, 30)]

    def test_the_sentence_says_additional(self):
        s = _verified_summary(facts(fee_tiers=self.ADDITIVE))
        assert "an additional $200 per stay applies for stays of 7–30 nights" in s

    def test_the_inclusive_ladder_does_not_say_additional(self):
        assert "additional" not in _verified_summary(facts(fee_tiers=self.INCLUSIVE))

    def test_the_range_chip_does_not_present_the_surcharge_as_a_ceiling(self):
        """"$100–$200" says the most you pay is $200. On an additive ladder a
        two-week stay pays both."""
        assert tier_fee_range(self.ADDITIVE) == "$100 + $200"
        assert tier_fee_range(self.INCLUSIVE) == "$100–$200"

    def test_no_total_is_ever_computed(self):
        """The pages state $100 and $200 and never their sum. Neither do we."""
        f = facts(fee_tiers=self.ADDITIVE)
        text = _verified_summary(f) + " " + tier_fee_range(self.ADDITIVE) + " " + json.dumps(rows(f))
        assert "300" not in text

    def test_the_detail_row_marks_the_surcharge_too(self):
        """A reader scanning only the table must not read $200 as the price of
        the 7-30 night band."""
        r = rows(facts(fee_tiers=self.ADDITIVE))
        assert r["Pet charge, 7–30 nights"] == "$200 additional"
        assert rows(facts(fee_tiers=self.INCLUSIVE))["Pet charge, 7–30 nights"] == "$200"

    def test_every_surface_agrees_the_surcharge_is_additional(self):
        f = facts(fee_tiers=self.ADDITIVE)
        assert "an additional" in _verified_summary(f)
        assert "+" in tier_fee_range(self.ADDITIVE)
        assert "additional" in rows(f)["Pet charge, 7–30 nights"]

    def test_the_two_ladders_never_render_identically(self):
        a = facts(fee_tiers=self.ADDITIVE)
        i = facts(fee_tiers=self.INCLUSIVE)
        assert _verified_summary(a) != _verified_summary(i)
        assert tier_fee_range(self.ADDITIVE) != tier_fee_range(self.INCLUSIVE)

    def test_both_amounts_survive_either_way(self):
        for tiers in (self.ADDITIVE, self.INCLUSIVE):
            s = _verified_summary(facts(fee_tiers=tiers))
            assert "$100" in s and "$200" in s

    def test_a_non_refundable_additive_tier_keeps_both_words(self):
        t = copy.deepcopy(self.ADDITIVE)
        s = _verified_summary(facts(fee_tiers=t),
                              evidence="Non-refundable pet fee: 1-6 nights : $100 / STAY")
        assert "non-refundable" in s and "an additional" in s


class TestExistingLaddersAreUntouched:

    def test_no_published_ladder_is_additive(self):
        pkg = json.loads((_REPO / "launch_packages" / "pettripfinder"
                          / "hotel_policy_facts.json").read_text("utf-8"))["hotels"]
        for h in pkg:
            for t in (h.get("facts") or {}).get("fee_tiers") or []:
                if t.get("additive"):
                    assert h["key"].startswith("hyatt"), h["key"]

    def test_a_ladder_with_no_flag_renders_as_a_range(self):
        assert tier_fee_range([tier("75.00", 1, 7), tier("150.00", 8, None)]) == "$75–$150"

    def test_equal_amounts_still_collapse_to_one(self):
        assert tier_fee_range([tier("50.00", 1, 6), tier("50.00", 7, 30)]) == "$50"
