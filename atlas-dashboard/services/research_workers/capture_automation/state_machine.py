"""The per-hotel state machine, as a pure transition table.

No I/O, no browser, no clock. The runner asks "given where I am and what just
happened, where do I go?" and this answers. Keeping it pure is what makes the
awkward paths -- kill switch, resume, one-hotel-fails-batch-continues -- testable
without a browser or a network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .reasons import CHALLENGE_REASONS, EXCEPTION_REASONS, retry_for

# States, in the order a healthy hotel passes through them.
QUEUED = "QUEUED"
NAVIGATING = "NAVIGATING"
URL_SHAPE = "URL_SHAPE"
IDENTITY = "IDENTITY"
POLICY_SCAN = "POLICY_SCAN"
INTERACTING = "INTERACTING"
CAPTURING = "CAPTURING"
VALIDATING = "VALIDATING"

# Terminal.
CAPTURED = "CAPTURED"
EXCEPTION = "EXCEPTION"

ORDERED_STATES = (QUEUED, NAVIGATING, URL_SHAPE, IDENTITY, POLICY_SCAN,
                  INTERACTING, CAPTURING, VALIDATING, CAPTURED)
TERMINAL_STATES = frozenset({CAPTURED, EXCEPTION})

_NEXT = {
    QUEUED: NAVIGATING,
    NAVIGATING: URL_SHAPE,
    URL_SHAPE: IDENTITY,
    IDENTITY: POLICY_SCAN,
    POLICY_SCAN: INTERACTING,
    INTERACTING: CAPTURING,
    CAPTURING: VALIDATING,
    VALIDATING: CAPTURED,
}


class StateError(ValueError):
    """Raised on an impossible transition -- a programming error, not a hotel
    outcome."""


def next_state(state: str) -> str:
    """The state that follows ``state`` when the current step succeeds."""
    if state in TERMINAL_STATES:
        raise StateError("no transition out of terminal state %s" % state)
    try:
        return _NEXT[state]
    except KeyError:
        raise StateError("unknown state: %s" % state)


def fail(state: str, reason: str) -> str:
    """Every failure goes to EXCEPTION. There is no in-batch retry: retrying
    inside a batch is how one bot-detection trip becomes twenty-five."""
    if state in TERMINAL_STATES:
        raise StateError("cannot fail out of terminal state %s" % state)
    if reason not in EXCEPTION_REASONS:
        raise StateError("undeclared reason: %s" % reason)
    return EXCEPTION


@dataclass(frozen=True)
class HotelOutcome:
    """What happened to one hotel. This is the journal record's payload."""

    hotel_id: str
    state: str
    reason: str = ""
    detail: Tuple[str, ...] = ()
    attempt: int = 1
    artifacts: Optional[dict] = None
    duplicate_of: str = ""
    elapsed_seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.state == CAPTURED

    @property
    def retry(self) -> str:
        return "" if self.succeeded else retry_for(self.reason)

    @property
    def is_challenge(self) -> bool:
        return self.reason in CHALLENGE_REASONS

    def to_dict(self) -> dict:
        d = {
            "hotel_id": self.hotel_id, "state": self.state,
            "reason": self.reason, "detail": list(self.detail),
            "attempt": self.attempt,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
        }
        if self.artifacts:
            d["artifacts"] = self.artifacts
        if self.duplicate_of:
            d["duplicate_of"] = self.duplicate_of
        if not self.succeeded:
            d["retry"] = self.retry
        return d


@dataclass(frozen=True)
class KillSwitch:
    """Consecutive-challenge counter.

    Immutable so the runner threads it explicitly rather than mutating shared
    state -- which also means a test can assert the exact count at which the
    batch aborts.
    """

    limit: int
    consecutive: int = 0

    def observe(self, outcome: HotelOutcome) -> "KillSwitch":
        if outcome.is_challenge:
            return KillSwitch(self.limit, self.consecutive + 1)
        return KillSwitch(self.limit, 0)

    @property
    def tripped(self) -> bool:
        return self.consecutive >= self.limit
