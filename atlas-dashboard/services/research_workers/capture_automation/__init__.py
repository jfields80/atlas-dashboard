"""PTF-CAPTURE-003 Phase 1 -- exception-driven official capture.

Automates the *finding* of a hotel's pet policy on its official page and stops
dead at a validated ``ptf-official-capture/1.0`` file. Attesting to that file,
approving it and publishing it stay human, per ADR-PTF-AUTOMATED-BROWSING.

Everything in this package is pure except where it takes a ``BrowserSession``,
and the only implementation of that protocol which touches a socket lives in
``services.research_workers.browser_control``. That split is what lets the
adapters, locator, validators and runner be tested against real saved DOMs with
no browser and no network.
"""

from .doctrine import BANNED_AUTOMATION_MARKERS, MIN_SECONDS_BETWEEN_HOTELS
from .reasons import EXCEPTION_REASONS, RETRY_MANUAL, RETRY_NEVER, RETRY_NOW

__all__ = [
    "BANNED_AUTOMATION_MARKERS", "MIN_SECONDS_BETWEEN_HOTELS",
    "EXCEPTION_REASONS", "RETRY_NOW", "RETRY_MANUAL", "RETRY_NEVER",
]
