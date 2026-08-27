# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-BACKLOG-ACQUISITION-016 -- 22 rows bought, 12 signed, 50 reached.

The number that matters is 56, and the number that nearly went wrong is 23.

    THE LEDGER REBUILD PAID FOR ITSELF BEFORE A CENT MOVED. The ledger on disk
    predated run 012 and knew nothing about its 50 purchases. Rebuilt, it
    matched 'hampton inn indianapolis sw plainfield' BY PROPERTY CODE to
    'hampton inn indianapolis southwest plainfield', already bought in 012 and
    already signed pet-friendly. Two census keys, one building, code indpfhx.
    The exact-cohort allowlist could not have caught it -- the keys genuinely
    differ -- and buying it would have paid for an answer we already owned and
    counted a profile we already had.

    THE READER GAP WAS LEFT OPEN ON PURPOSE. Omni Severin's block says "is a
    pet friendly hotel for pets under 25 pounds", which is a permission, and
    013's _ALLOWS has no pattern for it. Widening the rule mid-review would
    have turned 12 into 13 in the same breath that justified the edit. It is
    recorded as our defect and left for its own work order.

    THE FINAL DOLLAR FIGURE IS THE SETTLED ONE. The meter read 398c in-run and
    418c afterwards. A run that quoted its in-run number would understate what
    it spent.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.pettripfinder import indianapolis_founder_review_013 as R13
from scripts.pettripfinder import indianapolis_founder_review_016 as M

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def run():
    return _load("indianapolis_in_market_acquisition_016.json")


@pytest.fixture(scope="module")
def analysis():
    return _load("indianapolis_in_founder_review_analysis_016.json")


@pytest.fixture(scope="module")
def signature():
    return _load("indianapolis_in_founder_signature_016.json")


@pytest.fixture(scope="module")
def settled():
    return _load("indianapolis_in_settled_spend_016.json")


class TestTheAuthorizationWasHonoured:

    def test_the_gate_ran_the_authorised_allowlist(self, run):
        gate = run["authorized_cohort"]
        assert gate["authorised"] == 23
        assert gate["runner_queue"] == 24
        assert gate["payable"] == 22
        assert gate["suppressed_by_paid_history"] == 1

    def test_every_attempted_row_was_authorised(self, run):
        allowed = set(_load("indianapolis_in_authorized_cohort_016.json")
                      ["identity_keys"])
        for result in run["results"]:
            assert result["identity_key"] in allowed, result["identity_key"]

    def test_the_forbidden_residence_inn_row_was_never_contacted(self, run):
        """015's ledger already suppressed it; this work order forbade it by
        name. It is eligible, unauthorised, and untouched."""
        forbidden = "residence inn by marriott indianapolis northwest"
        assert forbidden not in {r["identity_key"] for r in run["results"]}
        assert forbidden not in set(
            _load("indianapolis_in_authorized_cohort_016.json")["identity_keys"])
        assert run["authorized_cohort"]["unauthorized_backlog"] == 1

    def test_the_cohort_shrank_and_nothing_was_substituted(self, run):
        assert "SHRINKS" in run["authorized_cohort"]["no_substitution"]
        assert run["attempted"] == 22 == run["cohort_size"]
        assert run["deferred"] == []
        assert run["outcome"] == "BATCH_COMPLETE"

    def test_the_authorisation_refuses_a_larger_cap_or_any_credit(self):
        from scripts.pettripfinder.acquisition import authorized_cohort as AC
        doc = _load("indianapolis_in_authorized_cohort_016.json")
        assert AC.validate(doc, market_id="indianapolis-in",
                           cap_usd_minor=500, plan_credit_cap=0)["ok"] is True
        assert AC.validate(doc, market_id="indianapolis-in",
                           cap_usd_minor=501, plan_credit_cap=0)["ok"] is False
        assert AC.validate(doc, market_id="indianapolis-in",
                           cap_usd_minor=500, plan_credit_cap=1)["ok"] is False

    def test_the_cohort_fingerprint_is_the_one_015_priced(self):
        priced = _load("indianapolis_in_backlog_plan_a_cohort_015.json")
        authorised = _load("indianapolis_in_authorized_cohort_016.json")
        assert authorised["cohort_keys_sha256"] == priced["cohort_keys_sha256"]
        assert authorised["identity_keys"] == priced["identity_keys"]


class TestTheDuplicatePurchaseTheLedgerPrevented:

    def test_one_row_was_suppressed_as_reusable_evidence(self, run):
        row, = run["authorized_cohort"]["suppressed_rows"]
        assert row["identity_key"] == "hampton inn indianapolis sw plainfield"
        assert row["decision"] == "SUPPRESSED_EVIDENCE_REUSABLE"
        assert "property code" in row["reason"]
        assert "indianapolis-in-012" in row["reason"]

    def test_the_twin_was_already_bought_and_already_signed(self):
        """Same building, two census keys. It was already inside the 44, so
        buying it would have added cost and no profile."""
        twin = "hampton inn indianapolis southwest plainfield"
        prior = _load("indianapolis_in_market_acquisition_012.json")
        assert next(r["outcome"] for r in prior["results"]
                    if r["identity_key"] == twin) == "VALID"
        signed = {r["identity_key"]: r["proposes_authority"]
                  for r in _load("indianapolis_in_founder_signature_013.json")["signed"]}
        assert signed[twin] == "PUBLISHED_PET_FRIENDLY"

    def test_the_allowlist_alone_could_not_have_caught_it(self):
        """The two identity keys differ, so an exact-cohort guard passes it.
        Only the property-code rung of the ledger stops it."""
        allowed = set(_load("indianapolis_in_authorized_cohort_016.json")
                      ["identity_keys"])
        assert "hampton inn indianapolis sw plainfield" in allowed
        assert "hampton inn indianapolis southwest plainfield" not in allowed

    def test_they_share_a_hilton_property_code(self):
        census = {h["identity_key"]: h for h in
                  _load("identity_census/indianapolis-in.json")["hotels"]}
        a = census["hampton inn indianapolis sw plainfield"]
        b = census["hampton inn indianapolis southwest plainfield"]
        assert "indpfhx" in (a.get("official_url") or a.get("url") or "")
        assert a["postal_code"] == b["postal_code"] == "46168"


class TestBothCapsHeld:

    def test_the_settled_meter_is_the_reported_figure(self, settled, run):
        assert settled["in_run_measured_usd_minor"] == 398
        assert settled["settled_usd_minor"] == 418
        assert settled["settled_upward_by_usd_minor"] == 20
        assert settled["settled_usd_minor"] > run["spend"]["measured_usd_minor"]

    def test_the_dollar_cap_was_never_crossed(self, settled, run):
        assert settled["authorised_cap_usd_minor"] == 500
        assert settled["within_cap"] is True
        assert settled["cap_margin_usd_minor"] == 82
        assert run["cost_policy"]["hard_cap_usd_minor"] == 500

    def test_no_firecrawl_credit_was_spent_and_none_was_authorised(self, run, settled):
        assert run["cost_policy"]["plan_credit_cap"] == 0
        assert run["spend"]["estimated_plan_credits"] == 0.0
        assert settled["plan_credits_spent"] == 0
        assert settled["plan_credit_cap"] == 0

    def test_no_row_ran_on_firecrawl(self, run):
        for result in run["results"]:
            assert result["provider"] != "firecrawl", result["identity_key"]
            assert result["provider"].startswith("brightdata")

    def test_the_cost_plan_gate_passed(self, run):
        assert run["cost_plan_gate"]["ok"] is True


class TestWhatCameBack:

    def test_the_outcome_split(self, run):
        assert run["outcome_counts"] == {
            "VALID": 13, "POLICY_NOT_FOUND": 4,
            "IDENTITY_MISMATCH": 3, "NAVIGATION_FAILED": 2}
        assert sum(run["outcome_counts"].values()) == 22
        assert run["publication_grade"] == 13

    def test_hilton_delivered_exactly_what_its_history_predicted(self, run):
        """015 forecast HILTON on a 9-for-9 record with a 70% floor. It went
        12 for 12."""
        hilton = [r for r in run["results"]
                  if r["identity_key"] in {c["identity_key"] for c in run["cohort"]
                                           if c["family"] == "HILTON"}]
        assert len(hilton) == 12
        assert all(r["outcome"] == "VALID" for r in hilton)

    def test_every_valid_row_kept_an_artifact_and_a_hash(self, run):
        for result in run["results"]:
            if result["outcome"] == "VALID":
                assert result["artifact_dir"], result["identity_key"]
                assert result["content_hash"]


class TestTheReviewUsesTheCommittedRules:

    def test_the_rules_are_imported_not_redefined(self):
        """Same function objects. A rule that differs between two reviews of
        one market is two rules."""
        assert M.R is R13
        assert M.R.rule is R13.rule
        assert M.R.read_block is R13.read_block

    def test_the_analysis_says_so(self, analysis):
        assert "imported verbatim" in analysis["reading_rules"]
        assert "013" in analysis["reading_rules"]

    def test_every_candidate_is_ruled_on_exactly_once(self, analysis):
        accounting = analysis["accounting"]
        assert accounting["attempted"] == 22
        assert accounting["candidates"] == 13 == accounting["reviewed"]
        assert accounting["each_candidate_once"] is True

    def test_the_dispositions_sum_to_thirteen(self, analysis):
        assert analysis["dispositions"] == {"APPROVE_PET_FRIENDLY": 12, "HOLD": 1}


class TestTheReaderGapWasNotPaperedOver:

    def test_the_source_does_permit_pets(self, analysis):
        gap = analysis["the_reader_gap_we_did_not_paper_over"]
        assert gap["identity_key"] == "omni severin hotel indianapolis"
        assert "pet friendly hotel" in gap["what_the_source_says"]
        assert gap["this_is_our_defect_not_the_sources"] is True

    def test_the_committed_rules_genuinely_miss_it(self):
        """Not a story about the reader -- the reader is run and does miss it."""
        block = ("Yes, Omni Severin Hotel is a pet friendly hotel for pets "
                 "under 25 pounds. There is a one-time non-refundable fee of "
                 "$125 per reservation.")
        reading = R13.read_block(block)
        assert reading["allowing_language"] == []
        assert reading["denying_language"] == []
        assert R13.rule({"policy_block": block}, reading)[0] == R13.HOLD

    def test_the_rule_was_not_widened(self):
        """If a 'pet friendly' pattern had been slipped in, this passes and the
        review's own account of itself becomes false."""
        assert R13.read_block("This is a pet friendly hotel.")["allowing_language"] == []

    def test_it_is_held_and_not_counted(self, analysis, signature):
        key = "omni severin hotel indianapolis"
        assert [r["identity_key"] for r in analysis["exceptions"]] == [key]
        assert key not in {r["identity_key"] for r in signature["signed"]}
        assert key in {r["identity_key"] for r in signature["withheld"]}
        assert analysis["the_reader_gap_we_did_not_paper_over"][
            "not_counted_in_the_new_signed_total"] is True

    def test_resolving_it_costs_nothing(self, analysis):
        gap = analysis["the_reader_gap_we_did_not_paper_over"]
        assert gap["cost_to_resolve"].startswith("zero")


class TestTheSignature:

    def test_twelve_signed_one_withheld(self, signature):
        assert signature["signed_count"] == 12
        assert signature["withheld_count"] == 1
        assert signature["signed_by_authority"] == {"PUBLISHED_PET_FRIENDLY": 12}

    def test_every_row_is_signed_by_the_named_reviewer(self, signature):
        for row in signature["signed"] + signature["withheld"]:
            assert row["founder_reviewer_id"] == "PTF-FOUNDER-001"

    def test_every_signed_row_binds_its_own_evidence(self, signature):
        for row in signature["signed"]:
            assert row["bound_semantic_hash"].startswith("sha256:")
            assert row["bound_snapshot_hash"]
            assert row["bound_source_url"].startswith("http")
            assert row["true_capture_completed_at"]

    def test_the_semantic_hashes_are_all_distinct(self, signature):
        hashes = [r["bound_semantic_hash"] for r in signature["signed"]]
        assert len(set(hashes)) == len(hashes)

    def test_nothing_is_promoted_by_signing(self, signature):
        assert signature["status"] == "RECORDED"
        for row in signature["signed"]:
            assert row["promotion"] == ""
        assert "publishes no page" in signature["nothing_is_published_by_this_file"]


class TestTheRunningTotal:

    def test_forty_four_plus_twelve_is_fifty_six(self, analysis):
        total = analysis["running_total"]
        assert total["promoted_pet_friendly"] == 24
        assert total["signed_pet_friendly_013_014"] == 20
        assert total["current_signed_pet_friendly"] == 44
        assert total["new_signed_pet_friendly"] == 12
        assert total["projected_total_after_review"] == 56

    def test_the_gap_to_fifty_is_closed(self, analysis):
        total = analysis["running_total"]
        assert total["remaining_gap_to_50"] == 0
        assert total["target_met_in_signatures"] is True

    def test_the_fifty_is_claimed_in_signatures_not_on_the_site(self, analysis):
        caveat = analysis["running_total"]["caveat"]
        assert "signed evidence, not on the site" in caveat
        assert "Not one row is promoted" in caveat


class TestNothingWasPromoted:

    def test_the_package_is_still_twenty_four(self):
        assert len(_load("hotel_policy_facts_indianapolis-in.json")["hotels"]) == 24

    def test_the_exclusion_shard_is_still_twenty_four(self):
        assert _load(
            "markets/authority/indianapolis-in/hotel_exclusions.json")["count"] == 24

    def test_the_census_is_still_257(self):
        assert _load("identity_census/indianapolis-in.json")["count"] == 257

    def test_the_esa_hold_and_the_mismatch_rows_were_not_touched(self, run):
        """Both were forbidden by this work order."""
        attempted = {r["identity_key"] for r in run["results"]}
        assert "extended stay america indianapolis airport w southern ave" \
            not in attempted
        prior = _load("indianapolis_in_market_acquisition_012.json")
        mismatched = {r["identity_key"] for r in prior["results"]
                      if r["outcome"] == "IDENTITY_MISMATCH"}
        assert len(mismatched) == 14
        assert attempted & mismatched == set()


class TestTheLedgerGrewAndLostNothing:

    def test_it_now_knows_run_012(self):
        ledger = _load("ptf_paid_attempt_ledger_001.json")
        runs = {a.get("run_id") for a in ledger["attempts"]}
        assert "indianapolis-in-012" in runs

    def test_the_earlier_markets_survived_the_rebuild(self):
        """Milwaukee entered through a provenance adapter, not an acquisition
        document; a regenerate-from-documents rebuild would have dropped it."""
        ledger = _load("ptf_paid_attempt_ledger_001.json")
        runs = {a.get("run_id") for a in ledger["attempts"]}
        for expected in ("st-louis-paid-002", "milwaukee-router-001",
                         "marriott-milwaukee-020", "hilton-milwaukee-023",
                         "pittsburgh-pa-recensus_001-pass1",
                         "grand-rapids-holland-mi-001-pass1"):
            assert expected in runs, expected
        assert len(ledger["attempts"]) >= 715


class TestTheRunWasFedBackIntoTheLedger:
    """The closing step, and the one most easily forgotten.

    016 rebuilt the ledger BEFORE spending and was rewarded immediately. But a
    run that does not write its own purchases back leaves the next caller --
    including a re-sent copy of this very work order -- free to buy all 22
    pages a second time. Suppression only works if every run both reads the
    ledger and feeds it.
    """

    def test_the_ledger_now_knows_this_run(self):
        ledger = _load("ptf_paid_attempt_ledger_001.json")
        runs = Counter(a.get("run_id") for a in ledger["attempts"])
        assert runs["indianapolis-in-016"] == 24
        assert runs["indianapolis-in-012"] == 52
        assert len(ledger["attempts"]) == 739

    def test_the_earlier_markets_still_survive(self):
        ledger = _load("ptf_paid_attempt_ledger_001.json")
        runs = {a.get("run_id") for a in ledger["attempts"]}
        for expected in ("st-louis-paid-002", "milwaukee-router-001",
                         "marriott-milwaukee-020", "hilton-milwaukee-023",
                         "pittsburgh-pa-recensus_001-pass1",
                         "grand-rapids-holland-mi-001-pass1",
                         "indianapolis-in-002-pass1"):
            assert expected in runs, expected

    def test_re_running_this_work_order_would_buy_nothing(self, run):
        """Every page 016 paid for is refused on a second pass."""
        from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL
        index = PAL.LedgerIndex(_load("ptf_paid_attempt_ledger_001.json"))
        cohort = {c["identity_key"]: c for c in run["cohort"]}
        for result in run["results"]:
            row = dict(cohort[result["identity_key"]])
            verdict = PAL.decide(row, index,
                                 available_lanes=("brightdata_browser",
                                                  "brightdata_web_unlocker"))
            assert verdict["decision"] != PAL.FIRST_PAID_ATTEMPT, (
                result["identity_key"], verdict["decision"])

    def test_a_page_this_run_bought_is_matched_on_its_own_url(self, run):
        from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL
        index = PAL.LedgerIndex(_load("ptf_paid_attempt_ledger_001.json"))
        cohort = {c["identity_key"]: c for c in run["cohort"]}
        valid = next(r for r in run["results"] if r["outcome"] == "VALID")
        verdict = PAL.decide(dict(cohort[valid["identity_key"]]), index,
                             available_lanes=("brightdata_browser",))
        assert verdict["match_key"] in (PAL.MATCH_CANONICAL_URL,
                                        PAL.MATCH_PROPERTY_CODE)

    def test_the_merge_lost_nothing_and_repeats_cleanly(self):
        """Additive, not regenerated: a rebuild from acquisition documents
        alone would drop Milwaukee, which arrived via a provenance adapter."""
        from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL
        ledger = _load("ptf_paid_attempt_ledger_001.json")
        again = PAL.merge(ledger, PAL.ingest_run(
            _load("indianapolis_in_market_acquisition_016.json"),
            census=_load("identity_census/indianapolis-in.json")["hotels"]))
        assert len(again["attempts"]) == len(ledger["attempts"])


class TestTheTwoRowsThatRemainGenuinelyOpen:
    """A transport failure is not evidence. These two are not settled, and the
    retry policy still refuses them -- because both approved lanes were already
    tried, not because the question is answered."""

    OPEN = ("country inn and suites indianapolis south in",
            "keystone inn and suites")

    def test_both_ended_in_a_transport_failure(self, run):
        for key in self.OPEN:
            result = next(r for r in run["results"] if r["identity_key"] == key)
            assert result["outcome"] == "NAVIGATION_FAILED"

    def test_neither_is_counted_as_answered(self, run, analysis):
        """NAVIGATION_FAILED is not in the terminal set, so neither row is
        pretending to be settled evidence."""
        assert "NAVIGATION_FAILED" not in run["cohort_rule"]["terminal_prior_outcomes"]
        reviewed = {r["identity_key"] for r in analysis["reviewed"]}
        assert set(self.OPEN) & reviewed == set()

    def test_a_blind_same_lane_retry_is_refused(self):
        """The work order forbids one; the retry policy is what enforces it."""
        from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL
        index = PAL.LedgerIndex(_load("ptf_paid_attempt_ledger_001.json"))
        run = _load("indianapolis_in_market_acquisition_016.json")
        cohort = {c["identity_key"]: c for c in run["cohort"]}
        for key in self.OPEN:
            verdict = PAL.decide(dict(cohort[key]), index,
                                 available_lanes=("brightdata_browser",
                                                  "brightdata_web_unlocker"))
            assert verdict["decision"] != PAL.FIRST_PAID_ATTEMPT, key
