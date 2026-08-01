"""PTF-CAPTURE-003 -- the browser seam.

Everything that touches a socket or a subprocess lives here and nowhere else in
the sprint. ``capture_automation`` depends on the ``BrowserSession`` protocol,
never on this package's implementations, which is why the whole pure core can be
exercised against saved DOMs with no Chrome and no network.

Permitted and forbidden techniques are fixed by ADR-PTF-AUTOMATED-BROWSING and
enforced mechanically by ``chrome_launcher``'s flag allowlist and the boundary
tests.
"""

from .session import BrowserSession, NavigationResult

__all__ = ["BrowserSession", "NavigationResult"]
