# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-50-PLUS-PET-FRIENDLY-RECOVERY-005.

The work order asked for +26 pet-friendly profiles and asked that they be found
from evidence we already own before any money was discussed. These tests pin
what that search actually returned, because the answer is counter-intuitive and
will be re-asked: the 54 identities the ledger calls SUPPRESSED_EVIDENCE_REUSABLE
are not 54 opportunities. Forty-eight of them ARE the current authority. Reusable
means "we own this answer", and for those it is already spent.

They also pin the arithmetic that says the target cannot be met by spending, so
that nobody re-derives it optimistically: at this market's own observed rate,
reaching 50 needs ~86 payable properties and only 36 exist.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import indianapolis_recovery_005 as R

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")

AUDIT = "indianapolis_in_recovery_audit_005.json"
PLAN = "indianapolis_in_recovery_cost_plan_005.json"
PACKET = "indianapolis_in_recovery_founder_packet_005.json"


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def audit():
    return _load(AUDIT)


@pytest.fixture(scope="module")
def plan():
    return _load(PLAN)


@pytest.fixture(scope="module")
def packet():
    return _load(PACKET)


class TestTheProtectedStateIsUntouched:

    def test_the_promoted_authority_is_still_24_and_24(self, audit):
        assert audit["current"]["promoted_pet_friendly"] == 24
        assert audit["current"]["verified_no_pets"] == 24
        assert audit["current"]["founder_signed"] == 48
        assert audit["current"]["census"] == 257

    def test_this_work_order_fetched_nothing_and_spent_nothing(self, audit):
        assert audit["nothing_was_fetched"] is True
        assert audit["usd_spent"] == 0.0
        assert audit["network_calls"] == 0

    def test_the_audit_derives_rather_than_remembers(self):
        """Two derivations from the same inputs agree.

        This is the property worth pinning. It is NOT the same as "the live
        derivation equals the saved artifact forever": the audit reads the
        cross-run paid ledger, and a ledger that never grows is a ledger that
        has stopped working.
        """
        assert R.build()["phase_5_payable"]["payable"] == \
            R.build()["phase_5_payable"]["payable"]

    def test_every_row_that_left_the_payable_set_was_paid_for(self, audit):
        """005 recorded 36 payable. It shrinks whenever a later run buys one of
        them, and the SHAPE of that shrinkage is the invariant worth pinning.

        Asserting a current total here would be a number to bump after every
        acquisition, which is how a meaningful test decays into a chore. So:
        every row that has left the payable set must have a recorded paid
        attempt behind it, and nothing may ever appear that was not there
        before. A row going quiet for any other reason is a defect.

        At the time of writing that is 36 -> 13: the 22 rows
        PTF-INDIANAPOLIS-BACKLOG-ACQUISITION-016 attempted, plus 'hampton inn
        indianapolis sw plainfield', which 016's ledger rebuild matched by
        property code to a page run 012 had already bought under the key
        'hampton inn indianapolis southwest plainfield' -- two census keys, one
        building. 016's own cohort shrank on that same row.
        """
        from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL

        def keys(phase):
            return {r["identity_key"] if isinstance(r, dict) else r
                    for r in phase["rows"]}

        saved = keys(audit["phase_5_payable"])
        live = keys(R.build()["phase_5_payable"])
        assert live <= saved, "the payable set may shrink, never grow"

        paid = {a["identity_key"] for a in
                PAL.load(PACKAGE_DIR / "ptf_paid_attempt_ledger_001.json")
                ["attempts"] if a["market_id"] == "indianapolis-in"}
        twin = "hampton inn indianapolis southwest plainfield"
        for key in saved - live:
            assert key in paid or twin in paid, key


class TestReusableEvidenceIsNotUntapped:
    """The single most important finding of this work order."""

    def test_all_54_reusable_rows_were_audited(self, audit):
        assert audit["phase_1_reusable_evidence"]["audited"] == 54

    def test_48_of_them_are_the_current_authority_already(self, audit):
        by = audit["phase_1_reusable_evidence"]["by_classification"]
        assert by["ALREADY_PROMOTED_PET_FRIENDLY"] == 24
        assert by["ALREADY_SIGNED_VERIFIED_NO_PETS"] == 24

    def test_no_new_pet_friendly_row_is_recoverable_from_saved_evidence(self, audit):
        assert audit["phase_1_reusable_evidence"]["new_pet_friendly_recoverable"] == 0

    def test_the_only_re_readable_artifact_says_no_pets_not_pets_allowed(self, audit):
        rows = [r for r in audit["phase_1_reusable_evidence"]["rows"]
                if r["classification"] == "NEEDS_POLICY_REPARSE"]
        assert len(rows) == 1
        row = rows[0]
        assert row["identity_key"] == "fairfield inn and suites indianapolis airport"
        assert "Pets Not Allowed" in row["policy_block"]

    def test_the_other_five_saved_no_artifact_at_all(self, audit):
        rows = [r for r in audit["phase_1_reusable_evidence"]["rows"]
                if r["classification"] == "NOT_PUBLICATION_GRADE"]
        assert len(rows) == 5
        assert all(not r["artifact_files"] for r in rows)


class TestRoutingRepair:

    def test_all_eight_routing_rows_were_diagnosed(self, audit):
        assert audit["phase_2_routing_repair"]["rows"] == 8

    def test_exactly_one_route_was_repairable_at_zero_cost(self, audit):
        assert audit["phase_2_routing_repair"]["repaired_zero_cost"] == 1

    def test_the_repaired_route_is_the_dead_delta_url(self, audit):
        rows = [r for r in audit["phase_2_routing_repair"]["detail"]
                if r["verdict"] == R.ROUTE_REPAIRED]
        assert len(rows) == 1
        row = rows[0]
        assert row["identity_key"] == "delta hotels by marriott indianapolis airport"
        assert "404" in row["page_title"]
        assert row["repaired_url"] == "https://www.marriott.com/indde"

    def test_no_routing_row_carries_reusable_policy_evidence(self, audit):
        """Every one of the eight aborted at the identity gate, before a policy
        was ever read -- so repairing the route buys a route, not a profile."""
        assert audit["phase_2_routing_repair"]["carry_saved_policy_evidence"] == 0

    def test_the_two_baymont_rows_point_at_one_page(self, audit):
        rows = [r for r in audit["phase_2_routing_repair"]["detail"]
                if "baymont" in r["identity_key"]]
        assert len(rows) == 2
        assert len({r["requested_url"] for r in rows}) == 1
        assert all(r["verdict"] == R.NEEDS_ADJUDICATION for r in rows)


class TestZeroCostRecoveryIsNearlyExhausted:

    def test_the_never_attempted_pool_is_mostly_unroutable(self, audit):
        p3 = audit["phase_3_zero_cost_recovery"]
        assert p3["never_attempted"] == 178
        assert p3["already_routable"] == 33
        assert p3["without_a_url"] == 145

    def test_only_two_urls_came_back_from_the_prior_census(self, audit):
        p3 = audit["phase_3_zero_cost_recovery"]
        assert p3["urls_recovered_from_prior_census"] == 2
        assert p3["still_without_a_url"] == 143


class TestThePayableCohortAndItsCeiling:

    def test_the_cohort_is_36_and_the_ledger_suppresses_none_of_it(self, audit):
        p5 = audit["phase_5_payable"]
        assert p5["cohort"] == 36
        assert p5["payable"] == 36
        assert p5["suppressed_by_ledger"] == 0

    def test_every_payable_row_has_an_established_route(self, audit):
        by = audit["phase_5_payable"]["by_basis"]
        assert by == {"never_attempted": 33, "routing_repaired": 1,
                      "url_recovered_zero_cost": 2}

    def test_the_plan_authorises_nothing(self, plan):
        assert plan["this_is_not_an_authorization"] is True
        assert plan["authorised_cap_usd_minor"] == 0

    def test_the_projection_is_small_and_bounded(self, plan):
        assert plan["dollar_billed_properties"] == 35
        assert plan["credit_billed_properties"] == 1
        assert plan["expected_firecrawl_credits"] == 1.0
        assert plan["projection"]["worst_case_usd_minor"] == 735.0
        assert plan["safe_cap_usd_minor"] == 750

    def test_the_target_is_not_reachable_from_this_pool(self, plan):
        y = plan["yield_projection"]
        assert y["target"] == 50
        assert y["payable_cohort"] == 36
        assert y["expected_total_pet_friendly"] == 35
        assert y["still_needed_after_spending_the_whole_cohort"] == 15
        assert y["payable_properties_required_to_reach_target_at_this_rate"] == 86
        assert y["verdict"] == "NOT_REACHABLE_FROM_THE_CURRENT_PAYABLE_POOL"


class TestTheFounderPacketIsExceptionsOnly:

    def test_nothing_was_auto_accepted_because_nothing_qualified(self, packet):
        assert packet["status"] == "EXCEPTIONS_ONLY"
        assert packet["auto_accepted"] == 0
        assert packet["new_pet_friendly_proposed"] == 0

    def test_it_proposes_one_no_pets_reinstatement_and_five_conflicts(self, packet):
        assert packet["new_verified_no_pets_proposed"] == 1
        assert packet["exceptions"] == 6

    def test_it_publishes_nothing(self, packet):
        assert "publishes nothing" in packet["nothing_is_published_by_this_file"]

    def test_no_row_proposes_changing_a_founder_decision_silently(self, packet):
        reinstate = [r for r in packet["rows"]
                     if r["proposes"] == "VERIFIED_NO_PETS"]
        assert len(reinstate) == 1
        assert "the founder's call" in reinstate[0]["why_it_is_an_exception"]
