"""Shared fixtures: the redacted real-capture corpus, and a fake browser.

The corpus is the reason this sprint is testable. Sixteen real Marriott and
Hilton property pages, with known-correct identities and known-correct pet
blocks, redacted to head-only HTML plus verbatim rendered text. Every adapter,
locator and validator assertion below runs against a page a brand actually
served -- not against a mock somebody wrote to agree with the code.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import zlib
from typing import Dict, List, Optional, Sequence, Tuple

import pytest

from services.research_workers.browser_control.session import NavigationResult
from services.research_workers.capture_automation.contracts import (
    BoxModel, DomSnapshot,
)
from services.research_workers.capture_automation.queue import QueueEntry

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text("utf-8"))


def fixture_names(brand: str = "") -> Tuple[str, ...]:
    return tuple(sorted(p.name for p in FIXTURE_DIR.glob("*.json")
                        if not brand or p.name.startswith(brand)))


def snapshot_for(name: str) -> DomSnapshot:
    return DomSnapshot.from_capture_payload(load_fixture(name))


def make_png(width: int = 1440, height: int = 1000) -> bytes:
    """A real, structurally valid PNG. The validators parse IHDR and require
    IEND, so a handful of fake bytes would not do."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = b"\x00" + b"\xff\xff\xff" * width
    idat = zlib.compress(row * height, 1)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


@pytest.fixture(scope="session")
def png_bytes() -> bytes:
    return make_png(320, 200)


def entry_for(name: str, **overrides) -> QueueEntry:
    """A queue entry that matches a fixture, so identity passes by default.

    Values come from the fixture's own JSON-LD, which is how a real queue would
    be built -- from the seed, agreeing with the page.
    """
    payload = load_fixture(name)
    blocks = [b for b in payload.get("jsonld") or [] if isinstance(b, dict)]
    hotel = next((b for b in blocks
                  if str(b.get("@type", "")).lower() in ("hotel", "lodgingbusiness")), {})
    addr = hotel.get("address") if isinstance(hotel.get("address"), dict) else {}
    url = payload["final_url"]
    # Use the real extractor rather than a hyphen heuristic: IHG puts the code
    # in its own bare path segment (/dublin/cmhtc/hoteldetail), which a
    # "<code>-<slug>" guess silently misses.
    from services.research_workers.source_retrieval import (
        extract_property_code_from_url,
    )
    code = extract_property_code_from_url(url)
    base = dict(
        hotel_id=name.replace(".json", ""),
        listing_key=name.replace(".json", "").replace("_", "-"),
        hotel_name=str(hotel.get("name") or payload.get("title") or ""),
        brand=("hilton" if "hilton.com" in url else
               "ihg" if "ihg.com" in url else "marriott"),
        official_url=url,
        expected_address=str(addr.get("streetAddress") or ""),
        expected_city=str(addr.get("addressLocality") or ""),
        expected_state=str(addr.get("addressRegion") or ""),
        expected_postal_code=str(addr.get("postalCode") or ""),
        expected_phone=str(hotel.get("telephone") or ""),
        expected_property_code=code,
    )
    base.update(overrides)
    return QueueEntry(**base)


class FakeBrowserSession:
    """A scripted BrowserSession. No Chrome, no socket, no clock.

    Drives the runner end to end so the awkward paths -- kill switch, resume,
    one-hotel-fails-batch-continues -- get real tests instead of hopeful ones.
    """

    def __init__(self, pages: Dict[str, dict], *,
                 nav_failures: Optional[Dict[str, str]] = None,
                 screenshot: Optional[bytes] = None,
                 viewport: Tuple[int, int] = (1440, 1000),
                 box: Optional[BoxModel] = None,
                 no_screenshot_for: Sequence[str] = (),
                 raise_for: Sequence[str] = (),
                 box_after: Optional[BoxModel] = None,
                 box_after_missing: bool = False,
                 snapshot_sequence: Optional[Dict[str, List[dict]]] = None):
        # url -> list of payloads returned by successive snapshot() calls, so a
        # test can model a page that hydrates over several polls. The final
        # entry repeats once exhausted.
        self.snapshot_sequence = snapshot_sequence or {}
        self.snapshot_calls = 0
        self.pages = pages
        self.nav_failures = nav_failures or {}
        self._screenshot = screenshot if screenshot is not None else make_png(320, 200)
        self._viewport = viewport
        self._box = box or BoxModel(x=0, y=200, width=600, height=300, scroll_y=100)
        # Geometry the page reports AFTER the screenshot. Defaults to the same
        # box (a page that held still); set it to model drift, and
        # ``box_after_missing`` to model the element vanishing.
        self._box_after = box_after
        self._box_after_missing = box_after_missing
        self.screenshot_taken = False
        self._no_shot = frozenset(no_screenshot_for)
        self._raise_for = frozenset(raise_for)
        self.current = ""
        self.navigations: List[str] = []
        self.clicks: List[str] = []
        self.scrolls: List[str] = []
        self.closed = False

    # -- protocol -------------------------------------------------------- #

    def navigate(self, url: str) -> NavigationResult:
        self.navigations.append(url)
        if url in self._raise_for:
            raise RuntimeError("simulated driver explosion")
        if url in self.nav_failures:
            return NavigationResult(False, reason=self.nav_failures[url],
                                    detail="scripted")
        if url not in self.pages:
            return NavigationResult(False, reason="NAVIGATION_FAILED",
                                    detail="no scripted page")
        self.current = url
        return NavigationResult(True, final_url=self.pages[url]["final_url"])

    def snapshot(self) -> DomSnapshot:
        self.snapshot_calls += 1
        seq = self.snapshot_sequence.get(self.current)
        if seq:
            idx = min(self.snapshot_calls - 1, len(seq) - 1)
            return DomSnapshot.from_capture_payload(seq[idx])
        return DomSnapshot.from_capture_payload(self.pages[self.current])

    def query_selector_exists(self, selector: str) -> bool:
        return False          # fixtures carry no brand selectors

    def click(self, selector: str) -> bool:
        self.clicks.append(selector)
        return True

    def click_text(self, selector: str, text: str) -> bool:
        self.clicks.append("%s[text=%s]" % (selector, text))
        return False        # fixtures are already-expanded snapshots

    def scroll_into_view(self, selector: str) -> bool:
        self.scrolls.append(selector)
        return True

    def scroll_to_text(self, needle: str) -> bool:
        self.scrolls.append(needle)
        return True

    def _current_box(self) -> Optional[BoxModel]:
        if not self.screenshot_taken:
            return self._box
        if self._box_after_missing:
            return None
        return self._box_after if self._box_after is not None else self._box

    def box_model(self, selector: str) -> Optional[BoxModel]:
        return self._current_box()

    def box_for_text(self, needle: str) -> Optional[BoxModel]:
        return self._current_box()

    def viewport(self) -> Tuple[int, int]:
        return self._viewport

    def screenshot_png(self) -> bytes:
        self.screenshot_taken = True
        if self.current in self._no_shot:
            return b""
        return self._screenshot

    def close(self) -> None:
        self.closed = True


def pages_from(*fixture_names_: str) -> Dict[str, dict]:
    """URL -> capture payload, for the FakeBrowserSession."""
    out: Dict[str, dict] = {}
    for name in fixture_names_:
        payload = load_fixture(name)
        out[payload["final_url"]] = payload
    return out
