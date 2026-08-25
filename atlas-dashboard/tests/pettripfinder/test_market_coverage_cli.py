"""PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 -- the coverage artifact over real markets.

Older markets must remain compatible: the coverage builder is run over the
COMMITTED St. Louis and Louisville artifacts -- census, overlay, merged
acquisition, closure ledger, founder packet -- and must reconcile every census
identity, agree with the closure ledger's denominator, and reproduce the
figures those work orders reported.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import market_coverage_cli as MC
from scripts.pettripfinder.contracts import coverage as COV

PKG = Path("launch_packages/pettripfinder")


def _read(name):
    return json.loads((PKG / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def louisville():
    return MC.build_from_paths(
        market_id="louisville-ky",
        url_overlay=(PKG / "louisville_ky_url_recovery_003.json").as_posix(),
        acquisition=(PKG / "louisville_ky_acquisition_merged_closeout_005.json").as_posix(),
        last_pass=(PKG / "louisville_ky_market_acquisition_003.json").as_posix(),
        closure=(PKG / "louisville_ky_closure_ledger_006.json").as_posix(),
        packet=(PKG / "louisville_ky_founder_review_packet_006.json").as_posix(),
        url_recovery=(PKG / "louisville_ky_url_recovery_003.json").as_posix(),
        declined_recovery=(PKG / "louisville_ky_zero_cost_recovery_005.json").as_posix(),
        recovery_after_last_pass=False,
        stage=MC.STAGE_FOUNDER_REVIEW_PACKET,
        work_order="TEST", as_of="2026-08-25")


@pytest.fixture(scope="module")
def st_louis():
    return MC.build_from_paths(
        market_id="st-louis-mo",
        url_overlay=(PKG / "st_louis_mo_url_recovery_002.json").as_posix(),
        acquisition=(PKG / "st_louis_mo_acquisition_merged_002.json").as_posix(),
        last_pass=(PKG / "st_louis_mo_paid_acquisition_002.json").as_posix(),
        closure=(PKG / "st_louis_mo_closure_ledger_002.json").as_posix(),
        packet=(PKG / "st_louis_mo_founder_review_packet_002.json").as_posix(),
        url_recovery=(PKG / "st_louis_mo_url_recovery_002.json").as_posix(),
        declined_recovery=(PKG / "st_louis_mo_zero_cost_recovery_002.json").as_posix(),
        stage=MC.STAGE_FOUNDER_REVIEW_PACKET,
        work_order="TEST", as_of="2026-08-25")


class TestLouisvilleCompatibility:
    def test_it_reconciles_the_whole_census(self, louisville):
        assert louisville["schema"] == COV.SCHEMA
        assert louisville["counts"]["CENSUS"] == 166
        rec = louisville["reconciliation"]
        assert rec["missing"] == [] and rec["foreign"] == [] and rec["duplicate"] == []
        assert len(louisville["rows"]) == 166

    def test_it_routes_what_the_paid_pass_routed(self, louisville):
        # 84 -> 101 with the overlay, as PTF-LOUISVILLE-COVERAGE-EXPANSION-003 reported.
        assert louisville["counts"]["ROUTED"] == 101
        assert louisville["counts"]["UNROUTED"] == 65

    def test_the_eight_same_lane_retries_are_terminal_not_settled(self, louisville):
        assert louisville["counts"]["ALTERNATE_LANE_REQUIRED"] == 8
        rows = {r["identity_key"]: r for r in louisville["rows"]}
        assert rows["louisville marriott downtown"]["next_state"] == COV.NEXT_ALTERNATE_LANE
        assert rows["louisville marriott downtown"]["factory_can_proceed"] is False
        assert louisville["counts"]["SETTLED"] == 90   # 82 VALID + 1 PNF + 7 mismatch

    def test_the_five_cap_deferred_rows_need_a_budget_not_a_phase(self, louisville):
        assert louisville["counts"]["BUDGET_DEFERRED"] == 5
        rows = {r["identity_key"]: r for r in louisville["rows"]}
        assert rows["hotel genevieve"]["next_state"] == COV.NEXT_BUDGET_AUTHORIZATION

    def test_closure_reconciles_and_the_founder_packet_is_read(self, louisville):
        assert louisville["booleans"]["CLOSURE_RECONCILED"] is True
        assert louisville["counts"]["FOUNDER_CANDIDATES"] == 63
        assert louisville["booleans"]["SAME_LANE_RETRIES_SUPPRESSED"] is True

    def test_every_row_has_exactly_one_next_state(self, louisville):
        for r in louisville["rows"]:
            assert r["next_state"] in COV.NEXT_STATES
            assert r["coverage_state"] in COV.COVERAGE_STATES

    def test_the_benchmark_is_reported_as_a_share_of_the_census(self, louisville):
        bench = louisville["benchmark"]
        assert bench["routed_pct_of_census"] == round(100.0 * 101 / 166, 1)
        assert bench["founder_candidate_pct_of_census"] == round(100.0 * 63 / 166, 1)
        assert bench["unresolved_pct_of_census"] == round(100.0 * (166 - 90) / 166, 1)


class TestStLouisCompatibility:
    def test_it_reconciles_the_whole_census(self, st_louis):
        assert st_louis["counts"]["CENSUS"] == 357
        rec = st_louis["reconciliation"]
        assert rec["missing"] == [] and rec["foreign"] == [] and rec["duplicate"] == []

    def test_closure_and_candidates_match_the_committed_artifacts(self, st_louis):
        closure = _read("st_louis_mo_closure_ledger_002.json")
        packet = _read("st_louis_mo_founder_review_packet_002.json")
        assert st_louis["booleans"]["CLOSURE_RECONCILED"] is True
        assert st_louis["active_eligible"] == closure["active_denominator"]
        assert st_louis["counts"]["FOUNDER_CANDIDATES"] == packet["count"] == 122

    def test_a_report_rebuilt_from_the_journal_cannot_claim_a_budget_stop(self, st_louis):
        # The 002 pass was killed and its report rebuilt with --report-only,
        # whose outcome is REPORT_FROM_JOURNAL: it says WHAT is true and never
        # WHY. So the 81 rows it lists as deferred cannot be attributed to the
        # cap by this artifact, and the ones still routed and unattempted are
        # honestly the factory's to run -- not a human's to authorise.
        assert st_louis["counts"]["BUDGET_DEFERRED"] == 0
        assert st_louis["coverage_state_counts"][COV.ROUTED_NEVER_ATTEMPTED] == 47
        assert st_louis["booleans"]["APPROVED_ROUTES_EXHAUSTED"] is False

    def test_the_two_key_recovery_of_002_is_not_exhaustion(self, st_louis):
        # St. Louis's URL recovery ran before the street key, URL corroboration
        # and unroutable-census-URL handling existed. The hardened factory says
        # so: 59 unrouted identities are still owed a free look.
        basis = st_louis["boolean_basis"]["zero_cost_recovery"]
        assert basis["url_recovery_ran"] is True
        assert basis["url_recovery_full_strength"] is False
        assert st_louis["booleans"]["ZERO_COST_RECOVERY_EXHAUSTED"] is False
        assert st_louis["next_state_counts"][COV.NEXT_RUN_ZERO_COST_RECOVERY] == 59
        assert st_louis["booleans"]["READY_FOR_FOUNDER_REVIEW"] is False

    def test_the_same_lane_rule_applied_retroactively_names_52_terminal_rows(self, st_louis):
        assert st_louis["counts"]["ALTERNATE_LANE_REQUIRED"] == 52
        assert st_louis["counts"]["UNSETTLED"] == 52


class TestStages:
    def test_an_unknown_stage_is_refused(self):
        with pytest.raises(COV.CoverageError):
            MC.build_from_paths(market_id="st-louis-mo", stage="whenever",
                                work_order="w", as_of="d")

    def test_before_closure_valid_rows_are_pending_grade_not_candidates(self):
        document = MC.build_from_paths(
            market_id="st-louis-mo",
            acquisition=(PKG / "st_louis_mo_acquisition_merged_002.json").as_posix(),
            stage=MC.STAGE_COVERAGE_EXHAUSTION, work_order="w", as_of="d")
        states = document["coverage_state_counts"]
        assert states.get(COV.SETTLED_VALID_GRADE_PENDING, 0) > 0
        assert states.get(COV.SETTLED_FOUNDER_CANDIDATE, 0) == 0
        assert document["booleans"]["READY_FOR_FOUNDER_REVIEW"] is False
        assert document["booleans"]["CLOSURE_RECONCILED"] is False
