"""Ceilings, so escalation stops before the money does.

A ladder without a ceiling is a way to spend a market's budget on one
unreachable hotel. Choice proved the shape of the risk: fifteen attempts across
five properties returning nothing. The registry now refuses that lane outright,
but the general case -- a property that fails everywhere -- still needs an
answer, and the answer is a number agreed in advance.

Every ceiling is checked BEFORE an attempt is spent, never after. A budget that
notices it was exceeded has already been exceeded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Budget:
    """Per-property ceilings.

    Defaults are drawn from the pilots rather than chosen: three attempts per
    provider is the contract every run so far has used, two providers is the
    length of the longest real ladder, and 50 cents is roughly three times the
    measured $0.16 per property -- generous enough that a normal property never
    meets it and tight enough that a pathological one cannot run away.
    """

    max_attempts_per_provider: int = 3
    max_total_attempts: int = 6
    max_property_cost_usd_minor: Optional[float] = 50.0
    max_elapsed_seconds: Optional[float] = 600.0

    def to_dict(self) -> Dict:
        return {"max_attempts_per_provider": self.max_attempts_per_provider,
                "max_total_attempts": self.max_total_attempts,
                "max_property_cost_usd_minor": self.max_property_cost_usd_minor,
                "max_elapsed_seconds": self.max_elapsed_seconds}


@dataclass
class BudgetLedger:
    """What one property has spent so far, and whether it may spend more."""

    budget: Budget
    attempts: int = 0
    elapsed_seconds: float = 0.0
    estimated_usd_minor: float = 0.0

    def record(self, *, attempts: int, elapsed_seconds: float,
               estimated_usd_minor: float = 0.0) -> None:
        self.attempts += attempts
        self.elapsed_seconds += elapsed_seconds
        self.estimated_usd_minor += estimated_usd_minor

    def exhausted(self) -> str:
        """Which ceiling has been reached, or "".

        Checked before committing to another provider, so the reason names the
        limit rather than the symptom.
        """
        if self.attempts >= self.budget.max_total_attempts:
            return ("total attempts: %d of %d"
                    % (self.attempts, self.budget.max_total_attempts))
        if (self.budget.max_property_cost_usd_minor is not None
                and self.estimated_usd_minor
                >= self.budget.max_property_cost_usd_minor):
            return ("estimated cost: %.1f of %.1f cents"
                    % (self.estimated_usd_minor,
                       self.budget.max_property_cost_usd_minor))
        if (self.budget.max_elapsed_seconds is not None
                and self.elapsed_seconds >= self.budget.max_elapsed_seconds):
            return ("elapsed: %.0f of %.0f seconds"
                    % (self.elapsed_seconds, self.budget.max_elapsed_seconds))
        return ""

    def attempts_remaining(self) -> int:
        return max(0, self.budget.max_total_attempts - self.attempts)

    def attempts_for_next_provider(self) -> int:
        """How many attempts the next provider may have.

        The per-provider cap and whatever the total leaves, whichever is
        smaller -- so the last provider on a ladder cannot overrun the total by
        taking its full allowance.
        """
        return max(0, min(self.budget.max_attempts_per_provider,
                          self.attempts_remaining()))

    def to_dict(self) -> Dict:
        return {"budget": self.budget.to_dict(), "attempts": self.attempts,
                "elapsed_seconds": round(self.elapsed_seconds, 3),
                "estimated_usd_minor": round(self.estimated_usd_minor, 2),
                "attempts_remaining": self.attempts_remaining(),
                "exhausted": self.exhausted()}


__all__ = ["Budget", "BudgetLedger"]
