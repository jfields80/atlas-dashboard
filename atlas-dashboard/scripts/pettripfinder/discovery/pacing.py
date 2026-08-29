"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- gentle, bounded request pacing.

Public Overpass instances are shared infrastructure run by volunteers. The
default behaviour of anything that queries them from here is deliberately slow:

    concurrency        1 -- never more unless a registry documents why
    spacing            a minimum gap between consecutive queries, plus jitter
    backoff            exponential with jitter between retries of ONE query,
                       capped, and bounded in attempts
    no tight loops     a failure sleeps before it is tried again, always

Every wait is recorded, so a run can say how long it spent being polite.
"""

from __future__ import annotations

import random
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

DEFAULT_CONCURRENCY = 1
DEFAULT_MIN_SPACING_SECONDS = 2.0
DEFAULT_JITTER_SECONDS = 0.5
DEFAULT_BACKOFF_BASE_SECONDS = 2.0
DEFAULT_BACKOFF_MAX_SECONDS = 60.0
DEFAULT_MAX_ATTEMPTS_PER_ENDPOINT = 2


@dataclass
class PacingStats:
    requests: int = 0
    successes: int = 0
    timeouts: int = 0
    rate_limits: int = 0
    server_errors: int = 0
    other_failures: int = 0
    endpoint_switches: int = 0
    cache_hits: int = 0
    waited_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    requests_by_endpoint: Dict[str, int] = field(default_factory=OrderedDict)

    def to_dict(self) -> Dict:
        return OrderedDict((
            ("concurrency", DEFAULT_CONCURRENCY),
            ("requests", self.requests), ("successes", self.successes),
            ("timeouts", self.timeouts), ("rate_limits", self.rate_limits),
            ("server_errors", self.server_errors),
            ("other_failures", self.other_failures),
            ("endpoint_switches", self.endpoint_switches),
            ("cache_hits", self.cache_hits),
            ("waited_seconds", round(self.waited_seconds, 3)),
            ("elapsed_seconds", round(self.elapsed_seconds, 3)),
            ("requests_by_endpoint", OrderedDict(self.requests_by_endpoint)),
        ))


@dataclass
class Pacer:
    """Spacing and backoff with injectable sleep, clock and randomness."""

    min_spacing_seconds: float = DEFAULT_MIN_SPACING_SECONDS
    jitter_seconds: float = DEFAULT_JITTER_SECONDS
    backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS
    backoff_max_seconds: float = DEFAULT_BACKOFF_MAX_SECONDS
    max_attempts_per_endpoint: int = DEFAULT_MAX_ATTEMPTS_PER_ENDPOINT
    sleep_fn: Optional[Callable[[float], None]] = None
    monotonic: Optional[Callable[[], float]] = None
    rand: Callable[[], float] = random.random
    stats: PacingStats = field(default_factory=PacingStats)
    last_request_at: Optional[float] = None
    waits: List[Dict] = field(default_factory=list)

    def _now(self) -> float:
        if self.monotonic is not None:
            return self.monotonic()
        import time
        return time.monotonic()

    def _sleep(self, seconds: float, why: str) -> None:
        if seconds <= 0:
            return
        self.waits.append(OrderedDict((("seconds", round(seconds, 3)), ("why", why))))
        self.stats.waited_seconds += seconds
        if self.sleep_fn is not None:
            self.sleep_fn(seconds)
        else:
            import time
            time.sleep(seconds)

    def _jitter(self) -> float:
        return self.jitter_seconds * self.rand() if self.jitter_seconds > 0 else 0.0

    def before_request(self, *, min_spacing_seconds: Optional[float] = None) -> float:
        """Wait until at least the spacing has passed since the last request.
        Returns the seconds waited."""
        spacing = (self.min_spacing_seconds if min_spacing_seconds is None
                   else float(min_spacing_seconds))
        waited = 0.0
        if self.last_request_at is not None and spacing > 0:
            due = self.last_request_at + spacing + self._jitter()
            gap = due - self._now()
            if gap > 0:
                self._sleep(gap, "spacing between queries")
                waited = gap
        self.last_request_at = self._now()
        self.stats.requests += 1
        return waited

    def backoff_seconds(self, attempt: int) -> float:
        """Exponential: base * 2^(attempt-1), plus jitter, capped."""
        raw = self.backoff_base_seconds * (2 ** max(0, attempt - 1))
        return min(self.backoff_max_seconds, raw) + self._jitter()

    def backoff(self, attempt: int, why: str = "retry backoff") -> float:
        seconds = self.backoff_seconds(attempt)
        self._sleep(seconds, "%s (attempt %d)" % (why, attempt))
        return seconds

    def may_retry(self, attempt: int) -> bool:
        """``attempt`` is the number already made on this endpoint."""
        return attempt < self.max_attempts_per_endpoint


__all__ = [
    "DEFAULT_CONCURRENCY", "DEFAULT_MIN_SPACING_SECONDS", "DEFAULT_JITTER_SECONDS",
    "DEFAULT_BACKOFF_BASE_SECONDS", "DEFAULT_BACKOFF_MAX_SECONDS",
    "DEFAULT_MAX_ATTEMPTS_PER_ENDPOINT", "PacingStats", "Pacer",
]
