"""PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 -- the coverage-completion contract.

Three properties, none arithmetic: the document reconciles by SET over the
census; every required count and boolean is present or the document refuses to
exist; and READY_FOR_FOUNDER_REVIEW cannot be asserted while any identity has a
next-state the factory can reach on its own.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.contracts import coverage as COV


def row(key, state=COV.SETTLED_FOUNDER_CANDIDATE, nxt=COV.NEXT_FOUNDER_DECISION):
    return COV.row(identity_key=key, canonical_name=key.title(),
                   coverage_state=state, next_state=nxt, why="because")


def counts(**overrides):
    base = {name: 0 for name in COV.REQUIRED_COUNTS}
    base.update(overrides)
    return base


def booleans(**overrides):
    base = {name: False for name in COV.REQUIRED_BOOLEANS}
    base.update(overrides)
    return base


class TestVocabulary:
    def test_every_next_state_has_a_written_meaning(self):
        for name in COV.NEXT_STATES:
            assert COV.NEXT_STATE_MEANINGS.get(name), name

    def test_terminal_and_factory_next_states_are_disjoint_and_complete(self):
        assert not set(COV.TERMINAL_NEXT_STATES) & set(COV.FACTORY_NEXT_STATES)
        assert set(COV.TERMINAL_NEXT_STATES) | set(COV.FACTORY_NEXT_STATES) == \
            set(COV.NEXT_STATES)

    def test_the_work_orders_required_fields_are_all_named(self):
        for name in ("CENSUS", "ROUTED", "UNROUTED", "ATTEMPTED", "VALID",
                     "SETTLED", "UNSETTLED", "NEEDS_OFFICIAL_URL",
                     "NEEDS_PROPERTY_URL", "BRAND_EXCLUDED", "BUDGET_DEFERRED",
                     "ALTERNATE_LANE_REQUIRED", "FOUNDER_CANDIDATES"):
            assert name in COV.REQUIRED_COUNTS
        for name in ("ZERO_COST_RECOVERY_EXHAUSTED", "APPROVED_ROUTES_EXHAUSTED",
                     "NEWLY_ROUTABLE_COHORT_EXHAUSTED",
                     "SAME_LANE_RETRIES_SUPPRESSED", "CLOSURE_RECONCILED",
                     "READY_FOR_FOUNDER_REVIEW"):
            assert name in COV.REQUIRED_BOOLEANS

    def test_retry_requires_alternate_lane_is_terminal_and_not_settled(self):
        assert COV.is_terminal(COV.NEXT_ALTERNATE_LANE)
        assert "NOT settled" in COV.NEXT_STATE_MEANINGS[COV.NEXT_ALTERNATE_LANE]


class TestRow:
    def test_an_unknown_coverage_state_is_refused(self):
        with pytest.raises(COV.CoverageError):
            row("a", state="PROBABLY_FINE")

    def test_an_unknown_next_state_is_refused(self):
        with pytest.raises(COV.CoverageError):
            row("a", nxt="SOMEONE_WILL_LOOK")

    def test_a_factory_next_state_means_the_factory_can_proceed(self):
        r = row("a", COV.ROUTED_NEVER_ATTEMPTED, COV.NEXT_RUN_ACQUISITION)
        assert r["factory_can_proceed"] is True
        assert r["next_state_is_terminal"] is False

    def test_a_terminal_next_state_means_it_cannot(self):
        r = row("a", COV.ROUTED_ALTERNATE_LANE_REQUIRED, COV.NEXT_ALTERNATE_LANE)
        assert r["factory_can_proceed"] is False


class TestDocument:
    def _doc(self, rows, keys, *, ready=False, **more):
        return COV.document(
            "m", rows, work_order="w", as_of="d", census_keys=keys,
            stage="closure", counts=counts(CENSUS=len(keys), **more),
            booleans=booleans(READY_FOR_FOUNDER_REVIEW=ready), evidence={})

    def test_it_reconciles_the_entire_census_by_set(self):
        with pytest.raises(COV.CoverageError):
            self._doc([row("a")], ["a", "b"])
        with pytest.raises(COV.CoverageError):
            self._doc([row("a"), row("z")], ["a"])
        with pytest.raises(COV.CoverageError):
            self._doc([row("a"), row("a")], ["a"])

    def test_a_missing_required_count_is_refused(self):
        partial = counts()
        del partial["BUDGET_DEFERRED"]
        with pytest.raises(COV.CoverageError):
            COV.document("m", [row("a")], work_order="w", as_of="d",
                         census_keys=["a"], stage="closure", counts=partial,
                         booleans=booleans(), evidence={})

    def test_a_missing_required_boolean_is_refused(self):
        partial = booleans()
        del partial["CLOSURE_RECONCILED"]
        with pytest.raises(COV.CoverageError):
            COV.document("m", [row("a")], work_order="w", as_of="d",
                         census_keys=["a"], stage="closure", counts=counts(CENSUS=1),
                         booleans=partial, evidence={})

    def test_ready_cannot_be_asserted_while_the_factory_can_still_move_a_row(self):
        rows = [row("a"), row("b", COV.ROUTED_NEVER_ATTEMPTED,
                               COV.NEXT_RUN_ACQUISITION)]
        with pytest.raises(COV.CoverageError):
            self._doc(rows, ["a", "b"], ready=True)

    def test_ready_may_be_true_with_unresolved_identities_that_are_terminal(self):
        rows = [row("a"),
                row("b", COV.ROUTED_ALTERNATE_LANE_REQUIRED, COV.NEXT_ALTERNATE_LANE),
                row("c", COV.UNROUTED_NEEDS_OFFICIAL_URL, COV.NEXT_OFFICIAL_URL),
                row("d", COV.ROUTED_BUDGET_DEFERRED, COV.NEXT_BUDGET_AUTHORIZATION)]
        doc = self._doc(rows, ["a", "b", "c", "d"], ready=True)
        assert doc["factory_complete"] is True
        assert doc["identities_the_factory_can_still_move"] == []
        assert doc["next_state_counts"][COV.NEXT_ALTERNATE_LANE] == 1

    def test_the_benchmark_percentages_are_of_the_census(self):
        rows = [row("a"), row("b", COV.UNROUTED_NEEDS_OFFICIAL_URL,
                               COV.NEXT_OFFICIAL_URL)]
        doc = COV.document(
            "m", rows, work_order="w", as_of="d", census_keys=["a", "b"],
            stage="closure",
            counts=counts(CENSUS=2, ROUTED=1, ATTEMPTED=1, SETTLED=1, VALID=1,
                          FOUNDER_CANDIDATES=1),
            booleans=booleans(), evidence={})
        bench = doc["benchmark"]
        assert bench["routed_pct_of_census"] == 50.0
        assert bench["settled_pct_of_census"] == 50.0
        assert bench["founder_candidate_pct_of_census"] == 50.0
        assert bench["unresolved_pct_of_census"] == 50.0

    def test_factory_complete_is_ready_and_nothing_else(self):
        doc = self._doc([row("a")], ["a"], ready=False)
        assert doc["factory_complete"] is False
        assert "never merely because one paid pass ended" in doc["factory_complete_basis"]
