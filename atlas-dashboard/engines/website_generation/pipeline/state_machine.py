"""Pure state-machine core for the WGE build lifecycle (AES-WEB-001 §6).

This module is the *pure core* only: a transition function plus static
tables. No I/O, no clocks, no persistence, no logging, no retries
performed internally. The effectful shell (a future service) reads and
writes checkpoints and applies this law; it is deliberately absent from
Phase 1 (the AES-WEB-001 Phase 1 scope includes only the pure core).

Transition law:

* ``SUCCESS`` advances along the active sequence (§6.2).
* From ``GATED``: ``SUCCESS`` → ``CERTIFIED``; ``GATE_REJECT`` →
  ``GATE_REJECTED``.
* From ``GATE_REJECTED``: ``REWORK`` → ``CONTENT_DRAFTING`` (targeted
  rework); ``ESCALATE`` → ``ESCALATED_HUMAN``.
* From any active state: ``RETRYABLE_FAILURE`` → ``FAILED_RETRYABLE``;
  ``TERMINAL_FAILURE`` → ``FAILED_TERMINAL``; ``ESCALATE`` →
  ``ESCALATED_HUMAN``; ``CANCEL`` → ``CANCELLED``.
* From ``FAILED_RETRYABLE``: ``RETRY`` re-enters the prior active state,
  which the caller must supply as ``retry_target`` (attempt counters
  live in the build-state row, never here — §6.3).
* From ``ESCALATED_HUMAN``: ``REWORK`` → ``CONTENT_DRAFTING``;
  ``CANCEL`` → ``CANCELLED`` (§6.8 operator decisions; overrides are a
  service concern).
* Terminal states (``DEPLOY_READY``, ``FAILED_TERMINAL``, ``CANCELLED``)
  accept no transitions.

Any transition not present in the static tables raises
:class:`IllegalTransitionError` — a corrupted build never limps forward.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Tuple

from engines.website_generation.contracts.enums import (
    BuildState,
    StageOutcome,
)
from engines.website_generation.contracts.errors import (
    IllegalTransitionError,
)

STATE_MACHINE_VERSION = "1.0.0"

# Ordered active build sequence (§6.2). INITIALIZED is the entry state;
# DEPLOY_READY is the terminal success state.
ACTIVE_STATE_SEQUENCE: Tuple[BuildState, ...] = (
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

TERMINAL_STATES: FrozenSet[BuildState] = frozenset(
    {
        BuildState.DEPLOY_READY,
        BuildState.FAILED_TERMINAL,
        BuildState.CANCELLED,
    }
)

# Active states are the non-terminal members of the main sequence.
ACTIVE_STATES: FrozenSet[BuildState] = frozenset(
    state for state in ACTIVE_STATE_SEQUENCE if state not in TERMINAL_STATES
)


def _build_transition_table() -> Dict[
    Tuple[BuildState, StageOutcome], BuildState
]:
    table: Dict[Tuple[BuildState, StageOutcome], BuildState] = {}

    # SUCCESS advances along the sequence. GATED success routes through
    # the same table entry (GATED → CERTIFIED is the next sequence step).
    for index in range(len(ACTIVE_STATE_SEQUENCE) - 1):
        current = ACTIVE_STATE_SEQUENCE[index]
        table[(current, StageOutcome.SUCCESS)] = ACTIVE_STATE_SEQUENCE[
            index + 1
        ]

    # Failure and control routing from every active state (§6.2).
    for state in ACTIVE_STATES:
        table[(state, StageOutcome.RETRYABLE_FAILURE)] = (
            BuildState.FAILED_RETRYABLE
        )
        table[(state, StageOutcome.TERMINAL_FAILURE)] = (
            BuildState.FAILED_TERMINAL
        )
        table[(state, StageOutcome.ESCALATE)] = BuildState.ESCALATED_HUMAN
        table[(state, StageOutcome.CANCEL)] = BuildState.CANCELLED

    # Gate rejection (only from GATED).
    table[(BuildState.GATED, StageOutcome.GATE_REJECT)] = (
        BuildState.GATE_REJECTED
    )
    table[(BuildState.GATE_REJECTED, StageOutcome.REWORK)] = (
        BuildState.CONTENT_DRAFTING
    )
    table[(BuildState.GATE_REJECTED, StageOutcome.ESCALATE)] = (
        BuildState.ESCALATED_HUMAN
    )
    table[(BuildState.GATE_REJECTED, StageOutcome.CANCEL)] = (
        BuildState.CANCELLED
    )
    table[(BuildState.GATE_REJECTED, StageOutcome.TERMINAL_FAILURE)] = (
        BuildState.FAILED_TERMINAL
    )

    # Human escalation resolution (§6.8): rework or cancel.
    table[(BuildState.ESCALATED_HUMAN, StageOutcome.REWORK)] = (
        BuildState.CONTENT_DRAFTING
    )
    table[(BuildState.ESCALATED_HUMAN, StageOutcome.CANCEL)] = (
        BuildState.CANCELLED
    )
    table[(BuildState.ESCALATED_HUMAN, StageOutcome.TERMINAL_FAILURE)] = (
        BuildState.FAILED_TERMINAL
    )

    # Retryable failure: CANCEL / ESCALATE / TERMINAL_FAILURE are routed
    # here too; RETRY is handled by transition() with a retry_target.
    table[(BuildState.FAILED_RETRYABLE, StageOutcome.CANCEL)] = (
        BuildState.CANCELLED
    )
    table[(BuildState.FAILED_RETRYABLE, StageOutcome.ESCALATE)] = (
        BuildState.ESCALATED_HUMAN
    )
    table[(BuildState.FAILED_RETRYABLE, StageOutcome.TERMINAL_FAILURE)] = (
        BuildState.FAILED_TERMINAL
    )

    return table


# The static allowed-transition table (frozen at import; never mutated).
ALLOWED_TRANSITIONS: Dict[
    Tuple[BuildState, StageOutcome], BuildState
] = _build_transition_table()


def transition(
    current: BuildState,
    outcome: StageOutcome,
    retry_target: Optional[BuildState] = None,
) -> BuildState:
    """Pure transition function: ``(state, outcome) → state``.

    ``retry_target`` is required exactly when ``outcome`` is ``RETRY``
    from ``FAILED_RETRYABLE`` (§6.3: retry re-enters the prior state; the
    prior state lives in the build-state row, so the shell supplies it).
    """
    current = BuildState(current)
    outcome = StageOutcome(outcome)

    if current in TERMINAL_STATES:
        raise IllegalTransitionError(
            "no transitions are legal from terminal state %s"
            % current.value,
            from_state=current.value,
            outcome=outcome.value,
        )

    if outcome is StageOutcome.RETRY:
        if current is not BuildState.FAILED_RETRYABLE:
            raise IllegalTransitionError(
                "RETRY is only legal from FAILED_RETRYABLE",
                from_state=current.value,
                outcome=outcome.value,
            )
        if retry_target is None:
            raise IllegalTransitionError(
                "RETRY requires an explicit retry_target",
                from_state=current.value,
                outcome=outcome.value,
            )
        retry_target = BuildState(retry_target)
        if retry_target not in ACTIVE_STATES:
            raise IllegalTransitionError(
                "retry_target must be an active build state, got %s"
                % retry_target.value,
                from_state=current.value,
                outcome=outcome.value,
            )
        return retry_target

    if retry_target is not None:
        raise IllegalTransitionError(
            "retry_target is only legal with the RETRY outcome",
            from_state=current.value,
            outcome=outcome.value,
        )

    next_state = ALLOWED_TRANSITIONS.get((current, outcome))
    if next_state is None:
        raise IllegalTransitionError(
            "illegal transition: %s + %s" % (current.value, outcome.value),
            from_state=current.value,
            outcome=outcome.value,
        )
    return next_state
