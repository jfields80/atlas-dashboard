# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-TARGETED-FOUNDER-REVIEW-013 -- 31 ruled, 29 signed, 2 held.

The reading rules are the load-bearing part. Two of them exist because this
corpus produced the counterexample itself:

    A REFUSAL OUTRANKS A PERMISSION PATTERN, because every permission pattern
    fires inside a refusal -- "No Pets Allowed" contains "Pets Allowed", and
    "Pets Allowed: No" contains it twice. That substring is exactly how 012's
    first-pass reader reported five contradictions that did not exist.

    A FEE IS NOT A PERMISSION and AN AMENITY LABEL IS NOT A POLICY. Extended
    Stay America's block is a whole fee schedule that never says pets may come;
    Motel 6's "Pets Allowed" sits in a run beside "Elevator" and "Wi-Fi".

Nothing is promoted by any of this. The package is still 24 and the tests say so.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder.indianapolis_promoted_state import (
    PROMOTED_PET_FRIENDLY, PROMOTED_VERIFIED_NO_PETS, CENSUS)

from scripts.pettripfinder import indianapolis_founder_review_013 as R

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def analysis():
    return _load("indianapolis_in_founder_review_analysis_013.json")


@pytest.fixture(scope="module")
def signature():
    return _load("indianapolis_in_founder_signature_013.json")


def disposition(block):
    return R.rule({"policy_block": block}, R.read_block(block))[0]


class TestARefusalOutranksAPermissionPattern:
    """The substring trap that produced five false contradictions."""

    @pytest.mark.parametrize("block", [
        "No Pets Allowed Only service animals are permitted, free of charge.",
        "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        "ADA defined service animals are welcome at this hotel. Sorry no other pets are allowed.",
        "Pet Policy Pets Not Allowed",
        "Pet Policy Pets Not Allowed Service Animals Only",
        "No, pets are not allowed at Holiday Inn Express & Suites Indianapolis - East.",
    ])
    def test_it_reads_as_a_refusal(self, block):
        assert disposition(block) == R.APPROVE_NO_PETS

    def test_a_refusal_clears_every_allowing_pattern(self):
        reading = R.read_block("No Pets Allowed Only service animals are permitted.")
        assert reading["denying_language"]
        assert reading["allowing_language"] == []


class TestAPermissionMustBeStatedInTheSourcesOwnWords:

    @pytest.mark.parametrize("block", [
        "Pets Allowed: Yes General: Pet accommodations: 20.00 USD per night per pet.",
        "Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee Max weight 75 lbs",
        "Pet fee per night: 25 USD Pet damage deposit: 150 USD Pet weight limit: 80 2 pets allowed",
        "Pet Policy Pets Welcome Dog and cats, $75/stay",
        "Yes, pets are welcome at Indianapolis Marriott East. Up to 2 pets are allowed per room.",
    ])
    def test_it_reads_as_pet_friendly(self, block):
        assert disposition(block) == R.APPROVE_PET_FRIENDLY

    def test_a_fee_schedule_alone_is_held_not_approved(self):
        block = ("Pet fees: Not to exceed a $25.00 per day cleaning fee plus "
                 "tax, for the first six (6) nights, per pet.")
        assert disposition(block) == R.HOLD

    def test_an_amenity_run_is_held_not_approved(self):
        assert disposition(
            "Pets Allowed Elevator Restaurant Nearby Racing Wi-Fi") == R.HOLD

    def test_a_question_is_not_an_answer(self):
        assert disposition(
            "Are pets allowed at Home2 Suites by Hilton Indianapolis "
            "Keystone Crossing?") == R.HOLD

    def test_service_animal_language_alone_never_permits_pets(self):
        assert disposition(
            "ADA-defined service animals are welcome free of charge.") == R.HOLD

    def test_an_empty_block_is_held(self):
        assert disposition("") == R.HOLD


class TestServiceAnimalLanguageIsOrthogonal:

    def test_it_does_not_soften_a_refusal(self):
        block = "No Pets Allowed Only service animals are permitted, free of charge."
        assert disposition(block) == R.APPROVE_NO_PETS

    def test_it_does_not_carry_a_permission_on_its_own(self):
        block = ("Service Animals - ADA-defined service animals are welcome "
                 "free of charge. / Pets Allowed - 2 pets max. Cats and dogs "
                 "only. 75lbs or less per pet.")
        # Approved on the "Pets Allowed" clause, not on the service-animal one.
        assert disposition(block) == R.APPROVE_PET_FRIENDLY
        assert R.read_block(block)["allowing_language"]


class TestEveryCandidateIsAccountedForExactlyOnce:

    def test_thirty_one_reviewed(self, analysis):
        accounting = analysis["accounting"]
        assert accounting["candidates"] == 31
        assert accounting["reviewed"] == 31
        assert accounting["each_candidate_once"] is True

    def test_the_dispositions_sum_to_thirty_one(self, analysis):
        counts = analysis["dispositions"]
        assert counts == {"APPROVE_PET_FRIENDLY": 19,
                          "APPROVE_VERIFIED_NO_PETS": 10, "HOLD": 2}
        assert sum(counts.values()) == 31

    def test_no_reviewed_key_repeats(self, analysis):
        keys = [r["identity_key"] for r in analysis["reviewed"]]
        assert len(keys) == len(set(keys))

    def test_the_non_publication_grade_row_is_still_accounted_for(self, analysis):
        rows = analysis["valid_but_not_publication_grade"]
        assert len(rows) == 1
        assert rows[0]["identity_key"] == "motel 6 indianapolis airport"


class TestTheContradictionThatWasNotOne:

    def test_all_five_were_plain_refusals(self, analysis):
        finding = analysis["the_contradiction_that_was_not_one"]
        assert finding["count"] == 5
        assert finding["ruling"] == "all five approved as VERIFIED_NO_PETS"
        assert len(finding["identity_keys"]) == 5

    def test_each_of_the_five_was_signed_as_no_pets(self, analysis, signature):
        flagged = set(analysis["the_contradiction_that_was_not_one"]["identity_keys"])
        signed = {r["identity_key"]: r["proposes_authority"]
                  for r in signature["signed"]}
        for key in flagged:
            assert signed.get(key) == "VERIFIED_NO_PETS", key

    def test_the_cause_is_recorded_rather_than_quietly_fixed(self, analysis):
        cause = analysis["the_contradiction_that_was_not_one"]["cause"]
        assert "No Pets Allowed" in cause and "Pets Allowed: No" in cause

    def test_the_disagreement_count_is_not_conflated(self, analysis):
        """Seven rows disagreed with the first pass: the five plus the two
        holds. Reporting seven as "five contradictions" would be a lie."""
        gap = analysis["machine_vs_deeper_disagreements"]
        assert gap["count"] == 7
        assert len(gap["of_which_012_called_contradictory"]) == 5
        assert len(gap["of_which_are_the_two_holds"]) == 2


class TestTheTwoHolds:

    def test_they_are_the_fee_only_and_the_question_only_rows(self, analysis):
        keys = sorted(r["identity_key"] for r in analysis["exceptions"])
        assert keys == ["extended stay america indianapolis airport w southern ave",
                        "home2 suites by hilton indianapolis keystone crossing"]

    def test_each_states_its_evidence_and_its_reason(self, analysis):
        for row in analysis["exceptions"]:
            assert row["policy_block"].strip()
            assert row["reason"]
            assert row["source_url"]

    def test_neither_was_signed(self, analysis, signature):
        held = {r["identity_key"] for r in analysis["exceptions"]}
        signed = {r["identity_key"] for r in signature["signed"]}
        assert held & signed == set()
        assert {r["identity_key"] for r in signature["withheld"]} == held


class TestTheSignature:

    def test_it_signs_twenty_nine_under_the_right_authorities(self, signature):
        assert signature["signed_count"] == 29
        assert signature["withheld_count"] == 2
        assert signature["signed_by_authority"] == {
            "PUBLISHED_PET_FRIENDLY": 19, "VERIFIED_NO_PETS": 10}

    def test_every_row_is_signed_by_the_named_reviewer(self, signature):
        for row in signature["signed"]:
            assert row["founder_reviewer_id"] == "PTF-FOUNDER-001"

    def test_every_row_binds_its_evidence(self, signature):
        for row in signature["signed"]:
            assert row["bound_semantic_hash"].startswith("sha256:")
            assert row["bound_snapshot_hash"]
            assert row["bound_source_url"].startswith("http")
            assert row["true_capture_completed_at"]

    def test_the_semantic_hash_moves_with_the_evidence(self):
        base = {"identity_key": "k", "policy_block": "Pets allowed Yes",
                "source_url": "https://example.com/a"}
        changed = dict(base, policy_block="Pets Not Allowed")
        assert R._semantic_hash(base) != R._semantic_hash(changed)

    def test_it_publishes_nothing(self, signature):
        assert "publishes no page" in signature["nothing_is_published_by_this_file"]
        assert signature["status"] == "RECORDED"


class TestTheRunningTotalAndTheGap:

    def test_twenty_four_plus_nineteen(self, analysis):
        total = analysis["running_total"]
        assert total["current_promoted_pet_friendly"] == 24
        assert total["new_signed_pet_friendly"] == 19
        assert total["projected_total_after_review"] == 43
        assert total["new_verified_no_pets"] == 10
        assert total["holds"] == 2
        assert total["approve_with_change"] == 0

    def test_the_gap_to_fifty_is_seven(self, analysis):
        assert analysis["running_total"]["remaining_gap_to_50"] == 7


class TestNothingWasPromoted:

    def test_the_package_is_still_twenty_four(self):
        assert len(_load("hotel_policy_facts_indianapolis-in.json")["hotels"]) == PROMOTED_PET_FRIENDLY

    def test_the_exclusion_shard_is_still_twenty_four(self):
        shard = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
        assert shard["count"] == PROMOTED_VERIFIED_NO_PETS

    def test_the_census_is_still_257(self):
        assert _load("identity_census/indianapolis-in.json")["count"] == CENSUS  # 257 until PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 promoted the reviewed shadow
