"""The BrowserSession protocol, and the results it returns.

Deliberately small. Every method here is something the capture flow genuinely
needs; anything broader would be capability the sprint does not require and the
ADR would have to justify. In particular there is no cookie access, no storage
access, no request interception and no header manipulation -- not because they
are unused, but because they are unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Tuple, runtime_checkable

from ..capture_automation.contracts import BoxModel, DomSnapshot


@dataclass(frozen=True)
class NavigationResult:
    """What happened when we asked for a URL."""

    ok: bool
    final_url: str = ""
    reason: str = ""          # an EXCEPTION_REASONS key when not ok
    detail: str = ""
    http_status: int = 0


@runtime_checkable
class BrowserSession(Protocol):
    """A visible browser tab, seen through the narrowest useful keyhole."""

    def navigate(self, url: str) -> NavigationResult:
        """Open ``url`` and wait for render plus network quiet."""

    def snapshot(self) -> DomSnapshot:
        """Read the current page: URL, title, canonical, HTML, text, JSON-LD."""

    def query_selector_exists(self, selector: str) -> bool:
        """Is there an element matching ``selector``?"""

    def click(self, selector: str) -> bool:
        """Click the first match. Returns False when nothing matched."""

    def click_text(self, selector: str, text: str) -> bool:
        """Click the first element matching ``selector`` whose visible label
        contains ``text``. For tab and accordion controls a brand identifies by
        wording rather than by a stable id."""

    def scroll_into_view(self, selector: str) -> bool:
        """Scroll the first match to the middle of the viewport."""

    def scroll_to_text(self, needle: str) -> bool:
        """Scroll to the first element whose text contains ``needle``.

        The fallback when a brand offers no stable selector -- which is the
        common case, since the locator works on rendered text.
        """

    def box_model(self, selector: str) -> Optional[BoxModel]:
        """The element's page-coordinate box plus current scroll offset."""

    def box_for_text(self, needle: str) -> Optional[BoxModel]:
        """Box of the first element containing ``needle``."""

    def viewport(self) -> Tuple[int, int]:
        """(width, height) of the visible area, in CSS pixels."""

    def screenshot_png(self) -> bytes:
        """PNG bytes of the visible tab."""

    def close(self) -> None:
        """Release the tab. Never raises."""
