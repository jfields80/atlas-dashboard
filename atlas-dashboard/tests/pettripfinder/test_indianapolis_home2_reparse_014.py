# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-HOME2-KEYSTONE-REPARSE-014 -- one HOLD lifted, nothing bought.

013 held this row because its locator captured the FAQ heading and stopped: "Are
pets allowed at Home2 Suites by Hilton Indianapolis Keystone Crossing?" A
question is not a policy, so HOLD was right. The property's own answer was in the
same capture, in three encodings, and it says yes.

The tests that matter here are the ones that keep the correction honest rather
than the ones that confirm it:

    IT IS A RE-LOCATE AND IT SAYS SO. PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018
    re-parses the BLOCK and calls re-locating from rendered.html a
    re-ACQUISITION. This work order authorises that, and the module is required
    to label it accurately instead of borrowing 018's safer word.

    THE GUARD IS THE WHOLE ARTIFACT, NOT THE SENTENCE WE LIKED. A correction
    that reads one favourable sentence out of a page is worthless; the refusal
    scan runs over all of rendered.html and must find nothing.

    NOTHING IS BORROWED FROM THE SIBLINGS. Every other Home2/Homewood row in this
    market states "2 pets max, dogs and cats only". This property does not, so
    those fields stay empty. Absence is absence -- that is the same rule that
    made 013 hold this row in the first place.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder.indianapolis_promoted_state import (
    PROMOTED_BEFORE_017, PROMOTED_PET_FRIENDLY, PROMOTED_VERIFIED_NO_PETS)

from scripts.pettripfinder import indianapolis_home2_reparse_014 as M

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def correction():
    return _load("indianapolis_in_home2_reparse_014.json")


@pytest.fixture(scope="module")
def signature():
    return _load("indianapolis_in_founder_signature_014.json")


class TestNothingWasBoughtAndNothingWasAltered:

    def test_no_provider_was_called(self, correction):
        assert correction["provider_calls"] == 0
        assert correction["usd_spent"] == 0.0

    def test_the_raw_evidence_was_not_touched(self, correction):
        assert correction["correction"]["raw_evidence_altered"] is False

    def test_it_still_binds_the_original_captures_hashes(self, correction):
        """The snapshot hash and capture time come from the 012 run, not from
        any new fetch. If these drifted, something WAS re-acquired."""
        run = _load("indianapolis_in_market_acquisition_012.json")
        row = next(r for r in run["results"]
                   if r["identity_key"] == correction["identity_key"])
        assert correction["bound_snapshot_hash"] == row["content_hash"]
        assert correction["true_capture_completed_at"] == row["completed_at"]


class TestItIsCalledARelocateNotAReparse:
    """018's word is 're-parse' and it means something narrower than this."""

    def test_the_module_names_the_doctrine_it_is_departing_from(self, correction):
        note = correction["this_is_a_relocate_not_a_reparse"]
        assert "018" in note["doctrine"]
        assert "re-acquisition" in note["doctrine"]

    def test_it_states_why_the_018_harm_cannot_occur_here(self, correction):
        why = correction["this_is_a_relocate_not_a_reparse"]["why_it_is_safe_here"]
        assert "asserts nothing" in why
        assert "adds a finding where there was none" in why

    def test_the_held_block_really_did_assert_nothing(self, correction):
        """The whole justification rests on this. If the held block had carried
        a finding, moving off it would be silently changing the record."""
        block = correction["original_hold"]["held_block"]
        assert block.endswith("?")
        assert len(block.splitlines()) == 1
        from scripts.pettripfinder import indianapolis_founder_review_013 as R
        assert R.rule({"policy_block": block}, R.read_block(block))[0] == R.HOLD

    def test_the_authorisation_is_named(self, correction):
        note = correction["this_is_a_relocate_not_a_reparse"]
        assert note["authorised_by"] == M.WORK_ORDER


class TestTheGuardRanOverTheWholeArtifact:

    def test_no_refusal_appears_anywhere_in_the_rendered_capture(self):
        assert M.read_artifact()["contradictions"] == []

    def test_the_page_states_the_permission_exactly_once(self, correction):
        assert len(M.read_artifact()["statements"]) == 1
        assert correction["correction"]["occurrences_in_the_artifact"] == 3

    def test_the_refusal_scan_would_catch_a_refusal_if_one_were_there(self):
        """A guard nobody has seen fail is not a guard."""
        import re
        for pattern in M._REFUSALS:
            assert re.search(pattern, {
                r"pets?\s+(are\s+)?not\s+allowed": "Pets are not allowed here.",
                r"no\s+pets\s+allowed": "No Pets Allowed",
                r"pets\s+allowed\s*:\s*no": "Pets Allowed: No",
                r"no\s+other\s+pets": "Sorry, no other pets are permitted.",
                r'"petsAllowed"\s*:\s*false': '"petsAllowed": false',
            }[pattern], re.I), pattern

    def test_every_verification_check_passed(self, correction):
        assert correction["all_checks_pass"] is True
        assert all(correction["verification"].values())


class TestItIsThisBuildingAndNotTheBrand:
    """PTF-DAYTON-WORK-BROWSER-INTEGRATION-001: Best Western's JSON-LD
    petsAllowed:false is stamped on every property. Naming the building is what
    separates a statement from boilerplate."""

    def test_the_statement_names_the_property(self, correction):
        assert ("Home2 Suites by Hilton Indianapolis Keystone Crossing"
                in correction["correction"]["recovered_statement"])
        assert correction["verification"][
            "the_statement_names_this_building_not_the_brand"] is True

    def test_the_source_is_the_brands_own_site(self, correction):
        assert correction["correction"]["source_url"].startswith(
            "https://www.hilton.com/")


class TestOnlyWhatTheSentenceSays:

    def test_the_permission_is_quoted_not_inferred(self, correction):
        facts = correction["corrected_facts"]
        assert facts["pets_allowed"] is True
        assert facts["pets_allowed_evidence"] in \
            correction["correction"]["recovered_statement"]

    def test_the_weight_limit_is_read(self, correction):
        assert correction["corrected_facts"]["max_weight_lbs"] == 75

    def test_the_fee_is_two_tiers_not_three_charges(self, correction):
        """The sentence says "$75.00 non-refundable fee" and then "for stays of
        1-4 nights, the fee is $75". That is one tier said twice, not a $75
        base plus a $75 tier."""
        tiers = correction["corrected_facts"]["fee_tiers"]
        assert tiers == [
            {"amount_usd": 75.0, "min_nights": 1, "max_nights": 4},
            {"amount_usd": 125.0, "min_nights": 5, "max_nights": None}]

    def test_the_fee_basis_is_per_stay_and_non_refundable(self, correction):
        facts = correction["corrected_facts"]
        assert facts["fee_basis"] == "per stay"
        assert facts["fee_refundable"] is False

    @pytest.mark.parametrize("field", ["fee_scope", "max_pets", "species"])
    def test_what_the_source_never_states_stays_empty(self, correction, field):
        assert correction["corrected_facts"][field] is None

    def test_the_withholdings_say_why(self, correction):
        reasons = correction["corrected_facts"][
            "withheld_because_the_source_does_not_say"]
        assert len(reasons) == 3
        assert all(" -- " in r for r in reasons)

    def test_nothing_was_borrowed_from_the_sibling_properties(self, correction):
        note = correction["corrected_facts"]["not_borrowed_from_siblings"]
        assert "2 pets max" in note
        assert "absence on this property stays absence" in note


class TestTheHoldHistoryIsPreserved:

    def test_the_original_hold_is_carried_verbatim(self, correction):
        analysis = _load("indianapolis_in_founder_review_analysis_013.json")
        held = next(r for r in analysis["exceptions"]
                    if r["identity_key"] == correction["identity_key"])
        original = correction["original_hold"]
        assert original["disposition"] == "HOLD"
        assert original["reason"] == held["reason"]
        assert original["work_order"].endswith("FOUNDER-REVIEW-013")

    def test_the_correction_states_its_reason(self, correction):
        assert "the very question the locator stopped at" \
            in correction["correction"]["reason"]

    def test_the_013_ledger_is_left_standing_as_written(self, signature):
        """013 records what was decided then. It is amended, never rewritten."""
        assert signature["amends"] == "indianapolis_in_founder_signature_013.json"
        old = _load("indianapolis_in_founder_signature_013.json")
        assert old["signed_count"] == 29
        assert old["withheld_count"] == 2
        assert {r["identity_key"] for r in old["withheld"]} == {
            "extended stay america indianapolis airport w southern ave",
            "home2 suites by hilton indianapolis keystone crossing"}


class TestTheSignature:

    def test_one_row_signed_by_the_named_reviewer(self, signature):
        assert signature["signed_count"] == 1
        assert signature["withheld_count"] == 0
        row, = signature["signed"]
        assert row["founder_reviewer_id"] == "PTF-FOUNDER-001"
        assert row["proposes_authority"] == "PUBLISHED_PET_FRIENDLY"

    def test_the_row_records_what_it_supersedes(self, signature):
        """The decision is the CANONICAL publishing token; the fact that it
        followed a correction is a caveat beside it, not a new vocabulary word.

        An earlier draft of 014 wrote "APPROVED_AFTER_CORRECTION" here. That
        string is not in contracts.enums.APPROVAL_DECISIONS, so
        founder_approval.is_publishable refused it and the row silently failed
        to become authority in 017. A decision expressed in a word the contract
        does not know is not a decision the contract can act on."""
        from scripts.pettripfinder.contracts import enums
        from scripts.pettripfinder.contracts import founder_approval as FA
        row, = signature["signed"]
        assert row["founder_decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert FA.is_publishable(row["founder_decision"]) is True
        assert row["approved_after_correction"] is True
        assert row["supersedes_disposition"] == "HOLD"
        assert row["supersedes_work_order"].endswith("FOUNDER-REVIEW-013")

    def test_an_invented_approval_word_would_not_publish(self):
        """Why the line above is worth a test at all."""
        from scripts.pettripfinder.contracts import founder_approval as FA
        assert FA.is_publishable("APPROVED_AFTER_CORRECTION") is False

    def test_the_row_binds_its_evidence(self, signature, correction):
        row, = signature["signed"]
        assert row["bound_semantic_hash"] == correction["bound_semantic_hash"]
        assert row["bound_semantic_hash"].startswith("sha256:")
        assert row["bound_snapshot_hash"]
        assert row["bound_source_url"].startswith("http")

    def test_the_semantic_hash_is_bound_to_the_recovered_statement(self, correction):
        """It must move when the statement moves -- otherwise the signature is
        bound to the identity, not the evidence."""
        statement = correction["correction"]["recovered_statement"]
        url = correction["correction"]["source_url"]
        assert M.semantic_hash(M.IDENTITY, statement, url) \
            == correction["bound_semantic_hash"]
        assert M.semantic_hash(M.IDENTITY, "Pets are not allowed.", url) \
            != correction["bound_semantic_hash"]

    def test_the_row_is_not_promoted_by_signing_it(self, signature):
        row, = signature["signed"]
        assert row["promotion"] == ""
        assert signature["status"] == "RECORDED"
        assert "publishes no page" in signature["nothing_is_published_by_this_file"]


class TestTheRunningTotal:

    def test_twenty_signed_pet_friendly_across_013_and_014(self, signature):
        old = _load("indianapolis_in_founder_signature_013.json")
        assert old["signed_by_authority"]["PUBLISHED_PET_FRIENDLY"] == 19
        assert signature["signed_by_authority"]["PUBLISHED_PET_FRIENDLY"] == 1

    def test_the_projected_total_at_014_was_forty_four_and_the_gap_was_six(self):
        """What 014 could claim ON THE DAY, from the ledgers that existed then.

        This deliberately does NOT read the live package. The live count moves
        whenever a later work order promotes -- 016 signed twelve more and 017
        promoted the market to %d -- and a test that reads it would report an
        intended promotion as a regression in a work order that promoted
        nothing.""" % PROMOTED_PET_FRIENDLY
        signed = (_load("indianapolis_in_founder_signature_013.json")
                  ["signed_by_authority"]["PUBLISHED_PET_FRIENDLY"]
                  + _load("indianapolis_in_founder_signature_014.json")
                  ["signed_by_authority"]["PUBLISHED_PET_FRIENDLY"])
        assert signed == 20
        assert PROMOTED_BEFORE_017 + signed == 44
        assert 50 - (PROMOTED_BEFORE_017 + signed) == 6


class TestNothingWasPromoted:

    def test_the_package_is_still_twenty_four(self):
        assert len(_load("hotel_policy_facts_indianapolis-in.json")["hotels"]) == PROMOTED_PET_FRIENDLY

    def test_the_exclusion_shard_is_still_twenty_four(self):
        assert _load(
            "markets/authority/indianapolis-in/hotel_exclusions.json")["count"] == PROMOTED_VERIFIED_NO_PETS

    def test_the_census_is_still_257(self):
        assert _load("identity_census/indianapolis-in.json")["count"] == 257

    def test_the_unauthorized_backlog_was_not_touched(self):
        run = _load("indianapolis_in_market_acquisition_012.json")
        assert run["authorized_cohort"]["unauthorized_backlog"] == 24
        assert run["attempted"] == 50
