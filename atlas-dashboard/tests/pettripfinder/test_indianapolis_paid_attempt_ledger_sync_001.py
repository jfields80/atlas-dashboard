# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-CROSS-RUN-ATTEMPT-LEDGER-SYNC-001.

Indianapolis is the market that proved the leak: pass 1 bought the Hampton Inn
NE / Castleton page (Hilton property code INDNEHX) and answered it VALID, the
re-census renamed the identity key from ``hampton inn indianapolis ne
castleton`` to ``hampton inn indianapolis northeast castleton``, and pass 2 --
seeing a property with no history under that name -- bought the very same page
again for $19.50.

These tests pin the guard to that market's own saved history. They replay pass 2
against a ledger built from pass 1 ONLY, offline, and assert two things that
pull in opposite directions:

  1. the renamed duplicate IS suppressed, on the PAGE rather than the name, and
  2. nothing else is -- least of all the two founder-signed hotels that share
     601 W Washington (Courtyard ``indct`` and SpringHill ``indsd``).

The second is the one worth guarding. A guard that over-collapses costs
coverage rather than money, and a suppressed hotel is a hotel that never gets a
policy. Indianapolis is exactly the market where a street-keyed guard would
have been tempting and wrong.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")

MARKET_ID = "indianapolis-in"
PASS1_DOC = "indianapolis_in_market_acquisition_pass1_002.json"
PASS2_DRY_RUN = "indianapolis_in_acquisition_dry_run_pass2_002.json"
LEDGER_DOC = "ptf_paid_attempt_ledger_001.json"

#: The renamed key pass 2 offered, and the pass-1 key that already owned the page.
PASS2_RENAMED_KEY = "hampton inn indianapolis northeast castleton"
PASS1_ORIGINAL_KEY = "hampton inn indianapolis ne castleton"
INDNEHX_PAGE = "hilton.com/en/hotels/indnehx-hampton-indianapolis-ne-castleton"

#: Both pass-1 lane attempts on that page: the browser step that answered
#: nothing, then the unlocker escalation that returned VALID.
PASS1_INDNEHX_ATTEMPTS = {"134a7ba042894793", "8b8f5bcbfef6998d"}


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pass1_ledger():
    """The ledger exactly as it stood when pass 2 was planned."""
    return PAL.merge(PAL.new_ledger(),
                     PAL.ingest_run(_load(PASS1_DOC), market_id=MARKET_ID))


@pytest.fixture(scope="module")
def pass2_cohort():
    return _load(PASS2_DRY_RUN)["cohort"]


@pytest.fixture(scope="module")
def replay(pass1_ledger, pass2_cohort):
    return PAL.suppress(pass2_cohort, pass1_ledger)


class TestTheRenamedDuplicateIsSuppressed:

    def test_exactly_one_pass_two_row_is_suppressed(self, replay):
        _payable, suppressed = replay
        assert len(suppressed) == 1

    def test_the_other_twenty_seven_rows_stay_payable(self, replay, pass2_cohort):
        payable, _suppressed = replay
        assert len(pass2_cohort) == 28
        assert len(payable) == 27

    def test_every_other_row_is_a_first_paid_attempt(self, replay):
        payable, _suppressed = replay
        assert {r["paid_history"]["decision"] for r in payable} == {
            PAL.FIRST_PAID_ATTEMPT}

    def test_the_suppressed_row_is_the_indnehx_page(self, replay):
        _payable, suppressed = replay
        assert suppressed[0]["paid_history"]["canonical_url"] == INDNEHX_PAGE

    def test_it_was_offered_under_the_renamed_key(self, replay):
        """The rename is the whole point: every name-keyed guard saw a new
        property here."""
        _payable, suppressed = replay
        assert suppressed[0]["identity_key"] == PASS2_RENAMED_KEY

    def test_the_match_was_made_on_the_page_not_the_name(self, replay):
        _payable, suppressed = replay
        history = suppressed[0]["paid_history"]
        assert history["match_key"] == PAL.MATCH_CANONICAL_URL
        assert history["match_value"] == INDNEHX_PAGE

    def test_it_matched_the_pass_one_attempts_on_that_page(self, replay):
        _payable, suppressed = replay
        history = suppressed[0]["paid_history"]
        assert set(history["matched_attempts"]) == PASS1_INDNEHX_ATTEMPTS
        assert history["prior_run_id"] == "indianapolis-in-002-pass1"

    def test_the_prior_answer_is_reusable_so_nothing_need_be_bought(self, replay):
        _payable, suppressed = replay
        history = suppressed[0]["paid_history"]
        assert history["prior_outcome"] == "VALID"
        assert history["reusable_evidence"] is True
        assert history["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE
        assert history["prior_artifact_hash"]

    def test_the_partition_invents_and_drops_nothing(self, replay, pass2_cohort):
        payable, suppressed = replay
        assert len(payable) + len(suppressed) == len(pass2_cohort)


class TestCoLocatedHotelsAreNotOverSuppressed:
    """601 W Washington carries two founder-signed hotels. The census may hold
    a multi-hotel complex; a paid-attempt guard must not collapse one into the
    other on the strength of a shared street."""

    @staticmethod
    def _indy_attempts(code):
        ledger = _load(LEDGER_DOC)
        return [a for a in ledger["attempts"]
                if a["market_id"] == MARKET_ID and code in a["normalized_path"]]

    @staticmethod
    def _row(identity_key, canonical_name, code):
        # Street and postal deliberately identical on both rows, so the
        # premises signals are as tempting as they will ever be.
        return {
            "identity_key": identity_key,
            "canonical_name": canonical_name,
            "source_url": "https://www.marriott.com/%s" % code,
            "brand": "MARRIOTT",
            "provider": "brightdata_browser",
            "street": "601 W Washington St",
            "postal_code": "46204",
        }

    def test_the_history_really_does_hold_both_hotels(self):
        assert self._indy_attempts("/indct"), "Courtyard indct missing"
        assert self._indy_attempts("/indsd"), "SpringHill indsd missing"

    def test_the_courtyard_does_not_suppress_the_springhill(self):
        ledger = PAL.merge(PAL.new_ledger(), self._indy_attempts("/indct"))
        payable, suppressed = PAL.suppress([self._row(
            "springhill suites indianapolis downtown",
            "SpringHill Suites Indianapolis Downtown", "indsd")], ledger)
        assert not suppressed
        assert payable[0]["paid_history"]["decision"] == PAL.FIRST_PAID_ATTEMPT

    def test_the_springhill_does_not_suppress_the_courtyard(self):
        ledger = PAL.merge(PAL.new_ledger(), self._indy_attempts("/indsd"))
        payable, suppressed = PAL.suppress([self._row(
            "courtyard by marriott indianapolis downtown",
            "Courtyard by Marriott Indianapolis Downtown", "indct")], ledger)
        assert not suppressed
        assert payable[0]["paid_history"]["decision"] == PAL.FIRST_PAID_ATTEMPT

    def test_no_indianapolis_suppression_rests_on_premises_evidence_alone(
            self, replay):
        """Premises signals may CONFIRM a page match; they may never make one."""
        _payable, suppressed = replay
        assert all(r["paid_history"]["match_key"] != PAL.MATCH_PREMISES_EVIDENCE
                   for r in suppressed)


class TestTheLedgerCarriesIndianapolisHistory:

    def test_the_committed_ledger_holds_the_market(self):
        """105 when this work order wrote it, 181 now.

        PTF-INDIANAPOLIS-BACKLOG-ACQUISITION-016 merged run 012's 52 attempts
        in BEFORE spending -- a ledger that does not know a run cannot suppress
        its purchases -- and was repaid at once, matching 'hampton inn
        indianapolis sw plainfield' by property code to a page 012 had already
        bought. It then merged its own 24 attempts back afterwards, which is
        what stops the NEXT caller re-buying all 22.

        The count is asserted by SOURCE, never as a bare total. Growth here is
        the system working; a stale total would read as breakage and tempt
        someone to bump a number instead of naming where it came from.
        """
        ledger = _load(LEDGER_DOC)
        indy = [a for a in ledger["attempts"] if a["market_id"] == MARKET_ID]
        by_run = Counter(a["run_id"] for a in indy)
        assert by_run["indianapolis-in-002-pass1"] == 101
        assert by_run["indianapolis-in-002-pass2"] == 4
        assert by_run["indianapolis-in-012"] == 52
        assert by_run["indianapolis-in-016"] == 24
        assert sum(by_run.values()) == len(indy) == 181

    def test_the_indnehx_page_was_in_fact_bought_twice(self):
        """The defect this work order exists to prevent, kept visible."""
        ledger = _load(LEDGER_DOC)
        runs = {a["run_id"] for a in ledger["attempts"]
                if a["market_id"] == MARKET_ID
                and a["normalized_host"] + a["normalized_path"] == INDNEHX_PAGE}
        assert runs == {"indianapolis-in-002-pass1", "indianapolis-in-002-pass2"}

    def test_the_two_runs_used_different_identity_keys_for_it(self):
        ledger = _load(LEDGER_DOC)
        keys = {a["identity_key"] for a in ledger["attempts"]
                if a["market_id"] == MARKET_ID
                and a["normalized_host"] + a["normalized_path"] == INDNEHX_PAGE}
        assert keys == {PASS1_ORIGINAL_KEY, PASS2_RENAMED_KEY}
