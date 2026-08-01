"""PTF-DATA -- an exclusive weight ceiling must survive to the reader.

Staybridge Suites Columbus-Dublin states "under 80 lbs". Every published
surface rendered that as "Maximum pet weight is 80 pounds", which promises an
80-pound dog a room the hotel's own page turns away. The number was right and
the promise was wrong.

The fix is a recorded operator, not a display patch: ``weight_limit_operator``
is emitted only where the source EXCLUDES the figure, and every surface reads
the same field. Absence means inclusive -- the meaning every labelled "Maximum
Pet Weight: N" has always carried -- so no already-published hotel moves.
"""

import json
from pathlib import Path

from scripts.pettripfinder.hotel_profile import (
    _verified_details, _verified_facts, _verified_summary, weight_display,
    weight_phrase,
)
from scripts.pettripfinder.prose_facts import (
    WEIGHT_OP_LT, WEIGHT_OP_LTE, extract_weight_limit,
)
from scripts.pettripfinder.site_data import _POLICY_FIELDS
from scripts.pettripfinder.site_pages import build_comparison_page

REPO_ROOT = Path(__file__).resolve().parents[2]

# The exact Staybridge wording, as attested.
STAYBRIDGE_QUOTE = (
    "Can I bring my pet to Staybridge Suites Columbus-Dublin? Pets are welcome "
    "at Staybridge Suites Columbus-Dublin. Our Pet Policy: This is a dog only "
    "hotel. Up to two friendly pups under 80 lbs are welcome. Pet fee per pet "
    "is 75 to 150 dollars depending on length of stay of reservation.")
STAYBRIDGE_FACTS = {"pets_allowed": "true", "species_allowed": "dogs",
                    "pet_count_limit": "2", "weight_limit": "80.0 pounds",
                    "weight_limit_operator": "lt"}
# A labelled, inclusive hotel: Aloft Columbus Easton, published since PTF-SITE.
INCLUSIVE_FACTS = {"pets_allowed": "true", "pet_fee": "$50.00",
                   "fee_basis": "per night", "pet_count_limit": "2",
                   "weight_limit": "40.0 pounds"}
INCLUSIVE_QUOTE = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Night: "
                   "$50.00 Maximum Pet Weight: 40.0lbs")


# --------------------------------------------------------------------------- #
# 1. Extraction records which way the ceiling points.
# --------------------------------------------------------------------------- #

def test_exclusive_wording_records_a_strictly_under_operator():
    for phrase in ("pets under 80 lbs are welcome",
                   "dogs less than 80 pounds",
                   "pets below 80 lbs"):
        got = extract_weight_limit(phrase)
        assert got is not None, phrase
        assert got.value == "80.0 pounds"
        assert got.operator == WEIGHT_OP_LT, phrase


def test_inclusive_wording_is_not_relabelled_as_exclusive():
    """"Up to 80" and "80 maximum" ACCEPT the 80-pound dog. Reading them as
    exclusive would turn away a pet the hotel takes -- the same class of error
    in the opposite direction."""
    for phrase in ("pets up to 80 lbs are welcome",
                   "maximum weight of 80 pounds",
                   "no more than 80 lbs",
                   "80 lbs maximum"):
        got = extract_weight_limit(phrase)
        assert got is not None, phrase
        assert got.operator == WEIGHT_OP_LTE, phrase


# --------------------------------------------------------------------------- #
# 2. The promoter emits the operator only where the source is exclusive.
# --------------------------------------------------------------------------- #

def test_promoter_emits_the_operator_for_an_exclusive_source():
    from scripts.pettripfinder.promote_attested_candidates import extract_pet_facts
    facts, evidence, _ = extract_pet_facts(STAYBRIDGE_QUOTE)
    assert facts["weight_limit"] == "80.0 pounds"
    assert facts["weight_limit_operator"] == WEIGHT_OP_LT
    quoted = [e for e in evidence if e["field"] == "weight_limit_operator"]
    assert quoted and "under 80 lbs" in quoted[0]["quote"]


def test_promoter_omits_the_operator_for_a_labelled_inclusive_source():
    """Silence is the inclusive case. Emitting "lte" everywhere would rewrite
    all 33 published records for a distinction none of them draw."""
    from scripts.pettripfinder.promote_attested_candidates import extract_pet_facts
    facts, _, _ = extract_pet_facts(INCLUSIVE_QUOTE)
    assert facts["weight_limit"] == "40.0 pounds"
    assert "weight_limit_operator" not in facts


def test_operator_is_publishable_through_site_data():
    assert "weight_limit_operator" in _POLICY_FIELDS


# --------------------------------------------------------------------------- #
# 3. Every public surface preserves the exclusivity.
# --------------------------------------------------------------------------- #

def test_profile_prose_says_pets_must_weigh_under():
    summary = _verified_summary(STAYBRIDGE_FACTS, STAYBRIDGE_QUOTE)
    assert "Pets must weigh under 80 pounds" in summary
    assert "Maximum pet weight" not in summary


def test_profile_prose_never_states_an_inclusive_maximum_for_an_exclusive_source():
    """The specific published falsehood, pinned so it cannot return."""
    summary = _verified_summary(STAYBRIDGE_FACTS, STAYBRIDGE_QUOTE).lower()
    for banned in ("maximum pet weight is 80", "80 pounds maximum",
                   "up to 80 pounds"):
        assert banned not in summary


def test_chips_and_detail_table_show_under_80():
    chips = dict((label, value) for label, value, _ in
                 _verified_facts(STAYBRIDGE_FACTS))
    assert chips["Weight limit"] == "Under 80.0 pounds"
    rows, _, _ = _verified_details(STAYBRIDGE_FACTS)
    detail = dict((label, value) for label, value, _ in rows)
    assert detail["Weight restriction"] == "Under 80.0 pounds"


def test_comparison_table_cell_preserves_exclusivity():
    row = dict(STAYBRIDGE_FACTS,
               name="Staybridge Suites Columbus-Dublin",
               route="/pet-friendly-hotels/staybridge-suites-columbus-dublin/",
               area="Dublin, OH", verified_at="2026-08-01")
    page = build_comparison_page([row])
    assert "<td>Under 80.0 pounds</td>" in page
    assert "<td>80.0 pounds</td>" not in page


def test_structured_display_helpers_agree_with_each_other():
    """Prose and table read the same field, so they cannot drift apart."""
    assert weight_phrase(STAYBRIDGE_FACTS) == "under 80 pounds"
    assert weight_display(STAYBRIDGE_FACTS) == "Under 80.0 pounds"


# --------------------------------------------------------------------------- #
# 4. Nothing already published moves.
# --------------------------------------------------------------------------- #

def test_inclusive_hotels_read_exactly_as_before():
    summary = _verified_summary(INCLUSIVE_FACTS, INCLUSIVE_QUOTE)
    assert summary == ("Pets are welcome. A $50 non-refundable fee applies per "
                       "night. Maximum pet weight is 40 pounds, with up to 2 "
                       "pets permitted per room.")
    chips = dict((label, value) for label, value, _ in
                 _verified_facts(INCLUSIVE_FACTS))
    assert chips["Weight limit"] == "40.0 pounds"
    assert weight_display(INCLUSIVE_FACTS) == "40.0 pounds"


def test_only_exclusive_records_carry_the_operator_in_the_launch_package():
    """Guards the published corpus itself: an operator appearing on a hotel
    whose source never excluded its ceiling would be a silent claim."""
    pkg = json.loads((REPO_ROOT / "launch_packages/pettripfinder/"
                      "hotel_policy_facts.json").read_text("utf-8"))
    for hotel in pkg["hotels"]:
        op = (hotel.get("pet_policy") or hotel).get("weight_limit_operator", "")
        if op:
            assert op == WEIGHT_OP_LT, hotel.get("name")
            quotes = json.dumps(hotel).lower()
            assert any(w in quotes for w in ("under", "less than", "below")), \
                hotel.get("name")
