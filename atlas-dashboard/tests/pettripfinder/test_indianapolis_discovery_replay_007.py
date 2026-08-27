# -*- coding: utf-8 -*-
"""PTF-GENERIC-CROSS-RUN-DISCOVERY-ATTEMPT-LEDGER-001 -- the Indianapolis replay.

Pins the offline replay of the new discovery ledger over the 143 Indianapolis
identities that name no website, and the 25-row qualification sample built from
it. Nothing here calls a provider.

The sample's shape is the part worth protecting. It is an experiment, not a
cheap slice: every row that can bind on a telephone, a stratified set that must
bind on name and postal code, and two bare two-word names included precisely
because they SHOULD fail. A later edit that quietly drops the failure controls,
or lets one brand dominate the strata, would make the measured rate mean
something other than what it claims.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def replay():
    return _load("indianapolis_in_discovery_replay_007.json")


@pytest.fixture(scope="module")
def ledger():
    return _load("ptf_discovery_attempt_ledger_001.json")


class TestTheLedgerExistsBeforeTheFirstSpend:

    def test_it_is_committed_and_empty(self, ledger):
        assert ledger["schema"] == DAL.SCHEMA
        assert ledger["attempts"] == []

    def test_it_loads_through_the_module(self):
        loaded = DAL.load(PACKAGE_DIR / "ptf_discovery_attempt_ledger_001.json")
        assert loaded["schema"] == DAL.SCHEMA

    def test_the_replay_says_why_it_is_empty(self, replay):
        why = replay["ledger"]["why_it_is_empty"]
        assert "no paid discovery lookup has ever been made" in why


class TestNothingWasCalledOrSpent:

    def test_no_provider_was_called(self, replay):
        assert replay["nothing_was_fetched"] is True
        assert replay["provider_calls"] == 0
        assert replay["usd_spent"] == 0.0

    def test_the_sample_is_not_executed(self, replay):
        assert replay["qualification_sample"]["not_executed"] is True
        assert replay["this_is_not_an_authorization"] is True


class TestTheReplay:

    def test_every_one_of_the_143_is_a_genuinely_new_lookup(self, replay):
        r = replay["replay"]
        assert r["url_less_identities"] == 143
        assert r["already_covered_by_prior_discovery_history"] == 0
        assert r["genuinely_new_paid_lookups"] == 143

    def test_no_two_identities_collapse_onto_one_question(self, replay):
        r = replay["replay"]
        assert r["duplicates_that_would_be_suppressed"] == 0
        assert r["distinct_query_fingerprints"] == 143
        assert r["query_fingerprint_collisions"] == {}

    def test_the_partition_is_stated_not_assumed(self, replay):
        summary = replay["replay"]["history_summary"]
        assert summary["accounted_for"] == 143
        assert summary["payable"] + summary["suppressed"] == 143

    def test_renamed_rows_are_protected_by_premises_not_by_key(self, replay):
        protected = replay["replay"]["renamed_identities_protected_from_rebuy"]
        assert protected["rows_carrying_a_prior_census_alias"] == 4
        assert "never from the identity key" in protected["how"]


class TestTheQualificationSample:

    def test_it_is_twenty_five_rows(self, replay):
        sample = replay["qualification_sample"]
        assert sample["size"] == 25
        assert len(sample["rows"]) == 25
        assert sample["provider_requests_if_authorised"] == 25

    def test_it_covers_every_family_in_the_cohort(self, replay):
        sample = replay["qualification_sample"]
        assert len(sample["families_covered"]) == sample["families_in_the_cohort"]
        assert len(sample["families_covered"]) == 11

    def test_no_single_brand_dominates_the_strata(self, replay):
        """Choice holds 33 of the 143. A sample that was mostly Choice would
        measure what Google knows about Choice."""
        covered = replay["qualification_sample"]["families_covered"]
        assert max(covered.values()) <= 8

    def test_it_takes_every_row_that_can_bind_on_the_strong_key(self, replay):
        by_method = replay["qualification_sample"]["by_expected_binding_method"]
        assert by_method["PHONE"] == replay["binding_readiness"]["can_bind_on_telephone"]
        assert by_method["PHONE"] == 5

    def test_the_untested_key_is_the_majority_of_the_sample(self, replay):
        by_method = replay["qualification_sample"]["by_expected_binding_method"]
        assert by_method["NAME_AND_POSTAL_CODE"] == 18
        assert by_method["NAME_AND_POSTAL_CODE"] > by_method["PHONE"]

    def test_it_keeps_two_deliberate_failure_controls(self, replay):
        """If a bare two-word name binds, the rule is too loose and the other
        141 must not be bought."""
        by_method = replay["qualification_sample"]["by_expected_binding_method"]
        assert by_method["EXPECTED_TO_FAIL"] == 2
        controls = [r for r in replay["qualification_sample"]["rows"]
                    if r["expected_binding_method"] == "EXPECTED_TO_FAIL"]
        assert all(len(r["canonical_name"].split()) <= 2 for r in controls)
        assert all("failure control" in r["why_selected"] for r in controls)

    def test_every_row_carries_a_query_and_its_evidence_and_a_reason(self, replay):
        for row in replay["qualification_sample"]["rows"]:
            assert row["query"] and row["canonical_name"] in row["query"]
            assert row["why_selected"]
            assert row["query_fingerprint"]
            evidence = row["binding_evidence_available"]
            assert evidence["postal_code"] and evidence["street"]

    def test_a_phone_row_really_states_a_phone(self, replay):
        strong = [r for r in replay["qualification_sample"]["rows"]
                  if r["expected_binding_method"] == "PHONE"]
        assert strong
        assert all(r["binding_evidence_available"]["telephone"] for r in strong)

    def test_the_sample_fingerprints_match_the_module(self, replay):
        """The sample is reproducible from the module, not remembered."""
        mask = tuple(replay["field_mask"])
        for row in replay["qualification_sample"]["rows"][:5]:
            source = {"identity_key": row["identity_key"],
                      "canonical_name": row["canonical_name"],
                      "street": row["binding_evidence_available"]["street"],
                      "city": row["binding_evidence_available"]["city"],
                      "state": "IN",
                      "postal_code": row["binding_evidence_available"]["postal_code"],
                      "telephone": row["binding_evidence_available"]["telephone"]}
            assert DAL.query_fingerprint(
                source, provider=replay["provider"],
                method=replay["discovery_method"],
                field_mask=mask) == row["query_fingerprint"]
