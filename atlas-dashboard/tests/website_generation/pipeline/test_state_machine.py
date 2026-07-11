"""Pure state-machine tests (AES-WEB-001 §6).

Covers: every legal transition in the static table, representative
illegal transitions, terminal-state protection, failure-state routing,
retry re-entry, and deterministic transition behavior.
"""

from __future__ import annotations

import pytest

from engines.website_generation import (
    BuildState,
    IllegalTransitionError,
    StageOutcome,
)
from engines.website_generation.pipeline.state_machine import (
    ACTIVE_STATE_SEQUENCE,
    ACTIVE_STATES,
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    transition,
)


class TestStateTables:
    def test_sequence_matches_aes_web_001(self):
        assert ACTIVE_STATE_SEQUENCE == (
            BuildState.INITIALIZED,
            BuildState.SPEC_COMPILED,
            BuildState.BRAND_RESOLVED,
            BuildState.IA_PLANNED,
            BuildState.CONTENT_DRAFTING,
            BuildState.CONTENT_VALIDATED,
            BuildState.COMPONENTS_RESOLVED,
            BuildState.LAYOUT_COMPOSED,
            BuildState.RENDERED,
            BuildState.SEO_COMPILED,
            BuildState.ASSEMBLED,
            BuildState.GATED,
            BuildState.CERTIFIED,
            BuildState.PACKAGED,
            BuildState.DEPLOY_READY,
        )

    def test_terminal_states(self):
        assert TERMINAL_STATES == {
            BuildState.DEPLOY_READY,
            BuildState.FAILED_TERMINAL,
            BuildState.CANCELLED,
        }

    def test_control_states_exist(self):
        for state in (
            BuildState.FAILED_RETRYABLE,
            BuildState.FAILED_TERMINAL,
            BuildState.ESCALATED_HUMAN,
            BuildState.CANCELLED,
            BuildState.GATE_REJECTED,
        ):
            assert isinstance(state, BuildState)


class TestEveryLegalTransition:
    def test_every_table_entry_transitions(self):
        # Exhaustive: every entry in the static table is honored.
        for (state, outcome), expected in ALLOWED_TRANSITIONS.items():
            assert transition(state, outcome) == expected

    def test_success_walks_the_full_sequence(self):
        state = BuildState.INITIALIZED
        for expected in ACTIVE_STATE_SEQUENCE[1:]:
            state = transition(state, StageOutcome.SUCCESS)
            assert state == expected
        assert state == BuildState.DEPLOY_READY

    def test_gate_rejection_routes(self):
        assert (
            transition(BuildState.GATED, StageOutcome.GATE_REJECT)
            == BuildState.GATE_REJECTED
        )
        assert (
            transition(BuildState.GATE_REJECTED, StageOutcome.REWORK)
            == BuildState.CONTENT_DRAFTING
        )
        assert (
            transition(BuildState.GATE_REJECTED, StageOutcome.ESCALATE)
            == BuildState.ESCALATED_HUMAN
        )

    def test_escalation_resolution_routes(self):
        assert (
            transition(BuildState.ESCALATED_HUMAN, StageOutcome.REWORK)
            == BuildState.CONTENT_DRAFTING
        )
        assert (
            transition(BuildState.ESCALATED_HUMAN, StageOutcome.CANCEL)
            == BuildState.CANCELLED
        )

    def test_retry_reenters_prior_active_state(self):
        assert (
            transition(
                BuildState.FAILED_RETRYABLE,
                StageOutcome.RETRY,
                retry_target=BuildState.CONTENT_DRAFTING,
            )
            == BuildState.CONTENT_DRAFTING
        )


class TestFailureRouting:
    def test_every_active_state_routes_failures(self):
        for state in ACTIVE_STATES:
            assert (
                transition(state, StageOutcome.RETRYABLE_FAILURE)
                == BuildState.FAILED_RETRYABLE
            )
            assert (
                transition(state, StageOutcome.TERMINAL_FAILURE)
                == BuildState.FAILED_TERMINAL
            )
            assert (
                transition(state, StageOutcome.ESCALATE)
                == BuildState.ESCALATED_HUMAN
            )
            assert (
                transition(state, StageOutcome.CANCEL)
                == BuildState.CANCELLED
            )


class TestTerminalProtection:
    @pytest.mark.parametrize("terminal", sorted(TERMINAL_STATES))
    @pytest.mark.parametrize("outcome", list(StageOutcome))
    def test_no_transition_leaves_a_terminal_state(self, terminal, outcome):
        with pytest.raises(IllegalTransitionError):
            transition(terminal, outcome)


class TestIllegalTransitions:
    def test_gate_reject_only_from_gated(self):
        with pytest.raises(IllegalTransitionError):
            transition(BuildState.RENDERED, StageOutcome.GATE_REJECT)

    def test_rework_illegal_from_active_states(self):
        with pytest.raises(IllegalTransitionError):
            transition(BuildState.SPEC_COMPILED, StageOutcome.REWORK)

    def test_retry_illegal_outside_failed_retryable(self):
        with pytest.raises(IllegalTransitionError):
            transition(
                BuildState.SPEC_COMPILED,
                StageOutcome.RETRY,
                retry_target=BuildState.SPEC_COMPILED,
            )

    def test_retry_without_target_is_illegal(self):
        with pytest.raises(IllegalTransitionError):
            transition(BuildState.FAILED_RETRYABLE, StageOutcome.RETRY)

    def test_retry_target_must_be_active(self):
        with pytest.raises(IllegalTransitionError):
            transition(
                BuildState.FAILED_RETRYABLE,
                StageOutcome.RETRY,
                retry_target=BuildState.CANCELLED,
            )

    def test_retry_target_illegal_with_other_outcomes(self):
        with pytest.raises(IllegalTransitionError):
            transition(
                BuildState.SPEC_COMPILED,
                StageOutcome.SUCCESS,
                retry_target=BuildState.SPEC_COMPILED,
            )

    def test_success_illegal_from_failed_retryable(self):
        with pytest.raises(IllegalTransitionError):
            transition(BuildState.FAILED_RETRYABLE, StageOutcome.SUCCESS)

    def test_error_carries_structured_diagnostics(self):
        with pytest.raises(IllegalTransitionError) as excinfo:
            transition(BuildState.CANCELLED, StageOutcome.SUCCESS)
        assert excinfo.value.from_state == "CANCELLED"
        assert excinfo.value.outcome == "SUCCESS"


class TestDeterminism:
    def test_repeated_transitions_are_identical(self):
        results = {
            transition(BuildState.INITIALIZED, StageOutcome.SUCCESS)
            for _ in range(10)
        }
        assert results == {BuildState.SPEC_COMPILED}

    def test_table_is_pure_data(self):
        # The transition table is static: two reads observe equal content.
        snapshot = dict(ALLOWED_TRANSITIONS)
        transition(BuildState.INITIALIZED, StageOutcome.SUCCESS)
        assert snapshot == ALLOWED_TRANSITIONS
