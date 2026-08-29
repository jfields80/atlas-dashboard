# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-TARGETED-POLICY-ACQUISITION-012 -- the pre-flight that stopped.

The authorisation named 51 identities, a $7.00 cap and 20 Firecrawl credits.
The pre-flight passed on every check it was given: the paid ledger rebuilds
byte-identically from its source documents, and suppression over the 51 leaves
all 51 payable with the exact 20/31 lane split that was costed.

Then the committed acquisition runner derived its own cohort and it was 74.
Not because the ledger suppressed anything -- because the runner asks a wider
question than this authorisation did. It routes every unsettled identity the
census can reach, and 24 of those already carried a URL and had simply never
been attempted.

Those 24 are real work. They are not THIS work, and their cost does not fit
this cap: 1113c worst case against a 700c ceiling. Running anyway would have
spent the whole authorisation on a set nobody costed and left ten rows deferred
by queue order. So nothing was spent, and these tests pin why.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


@pytest.fixture(scope="module")
def preflight():
    return json.loads(
        (PACKAGE_DIR / "indianapolis_in_acquisition_preflight_012.json")
        .read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def overlay():
    return json.loads(
        (PACKAGE_DIR / "indianapolis_in_url_overlay_012.json")
        .read_text(encoding="utf-8"))


class TestNothingWasSpent:

    def test_the_run_stopped_before_any_purchase(self, preflight):
        assert preflight["outcome"] == "STOPPED_BEFORE_SPEND"
        assert preflight["usd_spent"] == 0.0
        assert preflight["provider_calls"] == 0

    def test_the_paid_ledger_did_not_move(self, preflight):
        assert preflight["nothing_changed"]["paid_attempt_ledger_attempts"] == 663

    def test_the_policy_journals_did_not_move(self, preflight):
        assert preflight["nothing_changed"]["policy_journals"] == {
            "pass1": 79, "pass2": 2}

    def test_no_authority_was_touched(self, preflight):
        changed = preflight["nothing_changed"]
        assert changed["authority_touched"] is False
        assert changed["published"] is False and changed["deployed"] is False


class TestThePreflightChecksThatPassed:

    def test_the_ledger_rebuilds_from_its_source_documents(self, preflight):
        checks = preflight["preflight_checks"]
        assert checks["paid_ledger_rebuilt_from_source_documents"] is True
        assert checks["indianapolis_rows_rebuilt"] == 105
        assert checks["indianapolis_rows_in_committed_ledger"] == 105
        assert checks["attempt_id_sets_identical"] is True

    def test_the_other_markets_were_preserved(self, preflight):
        assert preflight["preflight_checks"]["other_markets_preserved"] == 558

    def test_suppression_over_the_51_left_all_51_payable(self, preflight):
        gate = preflight["preflight_checks"]["suppression_over_the_authorised_51"]
        assert gate["payable"] == 51
        assert gate["suppressed"] == 0
        assert gate["partition_holds"] is True
        assert gate["lane_split"] == {"firecrawl": 20, "brightdata_browser": 31}


class TestWhyItStopped:

    def test_the_runner_derives_a_wider_cohort_than_was_authorised(self, preflight):
        divergence = preflight["cohort_divergence"]
        assert divergence["authorised"] == 51
        assert divergence["runner_derived"] == 74
        assert len(divergence["derived_but_not_authorised"]) == 24

    def test_the_extras_are_the_pre_existing_routed_backlog(self, preflight):
        why = preflight["cohort_divergence"]["why_the_extras_exist"]
        assert "already had a first-party URL" in why
        assert "never attempted" in why

    def test_the_authorised_51_fits_the_cap(self, preflight):
        costed = preflight["cost_if_run_as_authorised_51"]
        assert costed["cohort_size"] == 51
        assert costed["projection"]["worst_case_usd_minor"] == 651.0
        assert costed["fits_the_700c_cap"] is True

    def test_the_runners_cohort_does_not(self, preflight):
        costed = preflight["cost_if_run_as_the_runner_derives_it"]
        assert costed["projection"]["worst_case_usd_minor"] == 1113.0
        assert costed["fits_the_700c_cap"] is False

    def test_running_anyway_would_have_deferred_rows_by_queue_order(self, preflight):
        under = preflight["cost_if_run_as_the_runner_derives_it"]["under_the_cap"]
        assert under["completes_cohort"] is False
        assert under["deferred"] == 10
        assert under["stops_on"] == "dollar balance"

    def test_the_cost_plan_gate_cannot_narrow_a_queue(self, preflight):
        """It proves a plan and a purchase agree. It is not a filter."""
        why = preflight["why_the_gate_cannot_narrow_it"]
        assert "not a filter" in why
        assert "cohort_keys_sha256" in why


class TestTheRoutingOverlayIsReadyForWhicheverScopeIsChosen:

    def test_it_carries_every_recovered_url(self, overlay):
        assert overlay["schema"] == "ptf-census-url-recovery/1.0"
        assert overlay["recovered"] == 52
        assert len(overlay["recoveries"]) == 52

    def test_every_recovery_is_a_routable_property_page(self, overlay):
        for row in overlay["recoveries"]:
            assert row["url_shape"] == "PROPERTY_PAGE", row["identity_key"]
            assert row["routable"] is True
            assert row["recovered_url"].startswith("http")

    def test_every_recovery_names_the_binding_that_produced_it(self, overlay):
        for row in overlay["recoveries"]:
            assert row["binding"] in ("PHONE", "NAME_AND_POSTAL_CODE")
            assert row["evidence"]["provider"] == "GOOGLE_PLACES"

    def test_it_does_not_edit_the_census(self, overlay):
        assert "ROUTING ONLY" in overlay["what_this_is"]
        assert "never edited" in overlay["what_this_is"]


class TestTheMeterAnchorIsUsableByALaterRun:

    def test_it_was_written_once_and_records_the_vendor_baseline(self, preflight):
        anchor = preflight["meter_anchor"]
        assert anchor["written"] is True
        assert anchor["vendor_balance_usd_minor"] == 1160
        assert "never rewritten" in anchor["note"]
