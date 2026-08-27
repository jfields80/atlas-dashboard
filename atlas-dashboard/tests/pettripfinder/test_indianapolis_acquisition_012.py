# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-TARGETED-POLICY-ACQUISITION-012 -- what 50 authorised properties bought.

The run spent real money once and will not be repeated: the cross-run paid
ledger now settles every one of these pages. So this is the durable record of
the caps that held, the cohort that was honoured, and the two spend bugs the
run exposed.

The number to be careful with is the pet-friendly one. 22 blocks read as
pet-friendly on a first pass, and NOT ONE of them is a promoted profile. A
service-animal sentence is a legal access category and never a pet permission;
a "fee" token says MENTIONED, not APPLIES. The founder rules, and until then
Indianapolis still has 24.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder.indianapolis_promoted_state import (
    PROMOTED_PET_FRIENDLY, PROMOTED_VERIFIED_NO_PETS)

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def run():
    return _load("indianapolis_in_market_acquisition_012.json")


@pytest.fixture(scope="module")
def packet():
    return _load("indianapolis_in_founder_review_packet_012.json")


@pytest.fixture(scope="module")
def authorization():
    return _load("indianapolis_in_authorized_cohort_012.json")


class TestTheAuthorizationWasHonoured:

    def test_the_gate_restricted_74_to_50(self, run):
        gate = run["authorized_cohort"]
        assert gate["authorised"] == 51
        assert gate["runner_queue"] == 74
        assert gate["payable"] == 50
        assert gate["unauthorized_backlog"] == 24

    def test_the_one_unpayable_row_was_the_brand_excluded_hyatt(self, run):
        """An allowlist, not a quota: 51 became 50 and nothing replaced it."""
        assert run["authorized_cohort"]["authorised_but_not_eligible"] == [
            "hyatt place indianapolis carmel"]

    def test_every_attempted_row_was_authorised(self, run, authorization):
        allowed = set(authorization["identity_keys"])
        for result in run["results"]:
            assert result["identity_key"] in allowed, result["identity_key"]

    def test_the_run_completed_its_restricted_cohort(self, run):
        assert run["outcome"] == "BATCH_COMPLETE"
        assert run["attempted"] == 50
        assert run["cohort_size"] == 50
        assert run["deferred"] == []

    def test_the_cost_plan_gate_passed(self, run):
        assert run["cost_plan_gate"]["ok"] is True


class TestBothCapsHeld:

    def test_the_dollar_cap_was_never_crossed(self, run):
        spend = run["spend"]
        assert run["cost_policy"]["hard_cap_usd_minor"] == 700
        assert spend["binding_usd_minor"] <= 700
        assert spend["binding_usd_minor"] == 542.0

    def test_the_credit_cap_was_reached_exactly_and_not_exceeded(self, run):
        spend = run["spend"]
        assert run["cost_policy"]["plan_credit_cap"] == 20
        assert spend["estimated_plan_credits"] == 20.0

    def test_the_credit_meter_was_seeded_across_the_resume(self, run):
        """The first bug this run exposed: without seeding, a resumed session
        could have spent the whole credit cap a second time."""
        assert run["spend"]["seeded_plan_credits"] == 20.0

    def test_the_dollar_meter_was_seeded_too(self, run):
        assert run["spend"]["seeded_usd_minor"] > 0


class TestWhatCameBack:

    def test_fifty_attempts_produced_thirty_two_valid(self, run):
        assert run["outcome_counts"] == {
            "IDENTITY_MISMATCH": 14, "NAVIGATION_FAILED": 2,
            "POLICY_NOT_FOUND": 2, "VALID": 32}

    def test_thirty_one_are_publication_grade(self, run):
        assert run["publication_grade"] == 31

    def test_every_valid_row_kept_an_artifact(self, run):
        for result in run["results"]:
            if result["outcome"] == "VALID":
                assert result["artifact_dir"], result["identity_key"]
                assert result["content_hash"]


class TestThePacketProposesAndDecidesNothing:

    def test_it_is_exception_only_and_publishes_nothing(self, packet):
        assert packet["status"] == "EXCEPTIONS_ONLY"
        assert "publishes nothing" in packet["nothing_is_published_by_this_file"]

    def test_it_warns_that_a_reading_is_not_a_decision(self, packet):
        note = packet["nothing_is_published_by_this_file"]
        assert "never a decision" in note
        assert "service-animal" in note
        assert "MENTIONED, not APPLIES" in note

    def test_the_indicative_split_covers_every_valid_row(self, packet):
        readings = packet["counts"]["by_indicative_reading"]
        assert readings["READS_AS_PET_FRIENDLY"] == 22
        assert readings["READS_AS_NO_PETS"] == 5
        assert readings["READS_BOTH_WAYS_NEEDS_A_RULING"] == 5
        assert (readings["READS_AS_PET_FRIENDLY"]
                + readings["READS_AS_NO_PETS"]
                + readings["READS_BOTH_WAYS_NEEDS_A_RULING"]) == 32

    def test_contradictory_blocks_are_surfaced_not_guessed(self, packet):
        contradictory = [r for r in packet["exceptions"]
                         if r["indicative_reading"]
                         == "READS_BOTH_WAYS_NEEDS_A_RULING"]
        assert len(contradictory) == 5
        for row in contradictory:
            assert row["policy_block"], row["identity_key"]

    def test_every_review_candidate_quotes_its_own_evidence(self, packet):
        for row in packet["review_candidates"]:
            assert row["policy_block"].strip(), row["identity_key"]
            assert row["source_url"]

    def test_the_backlog_is_carried_as_a_decision_not_a_failure(self, packet):
        cohort = packet["authorized_cohort"]
        assert cohort["unauthorized_backlog"] == 24
        assert cohort["backlog_state"] == "NOT_AUTHORIZED_THIS_WORK_ORDER"
        assert "not a budget casualty" in cohort["backlog_note"]


class TestNothingWasPromoted:

    def test_the_promoted_package_is_untouched_at_24(self):
        package = _load("hotel_policy_facts_indianapolis-in.json")
        assert len(package["hotels"]) == PROMOTED_PET_FRIENDLY

    def test_the_exclusion_shard_is_untouched_at_24(self):
        shard = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
        assert shard["count"] == PROMOTED_VERIFIED_NO_PETS

    def test_the_census_is_untouched_at_257(self):
        census = _load("identity_census/indianapolis-in.json")
        assert census["count"] == 257
