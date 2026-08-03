"""``BrowserSession`` over a real CDP connection.

The page-side JavaScript here reads exactly what the capture contract needs --
markup and visible text -- and mirrors ``extractPage`` in the extension's
``background.js`` deliberately, so both transports produce the same payload.
It reads no cookie, no storage and no form value; the connection exposes no
method that could.
"""

from __future__ import annotations

import json
import time
from typing import Optional, Tuple

from ..capture_automation.contracts import BoxModel, DomSnapshot
from ..capture_automation.doctrine import (
    NAVIGATION_TIMEOUT_SECONDS, NETWORK_QUIET_SECONDS,
    NETWORK_QUIET_TIMEOUT_SECONDS,
)
from .cdp_client import CdpConnection, CdpError, CdpTimeout
from .session import NavigationResult

# Mirrors extractPage() in the extension. Kept as one expression so a single
# Runtime.evaluate returns the whole snapshot.
_EXTRACT_JS = """
(() => {
  const canonicalEl = document.querySelector('link[rel="canonical"]');
  const jsonld = [];
  for (const node of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const parsed = JSON.parse(node.textContent);
      if (parsed && typeof parsed === 'object') jsonld.push(parsed);
    } catch (_) { /* malformed JSON-LD is skipped, never repaired */ }
  }
  return {
    final_url: document.location.href,
    title: document.title || '',
    canonical_url: canonicalEl ? canonicalEl.href : '',
    html: document.documentElement ? document.documentElement.outerHTML : '',
    text: document.body ? document.body.innerText : '',
    jsonld: jsonld,
    vw: window.innerWidth || 0,
    vh: window.innerHeight || 0
  };
})()
"""

# Shared element-picking rule, injected into both helpers below.
#
# "Deepest match" is the obvious rule and it is wrong. On a real Marriott
# property page the last element whose innerText contains "Pet Policy" is a
# display:none <script> measuring 0x0, so the box came back all zeros and every
# capture failed POLICY_OFF_SCREEN with visible_fraction 0.00 while the policy
# sat plainly on screen.
#
# The rule that works: among VISIBLE matches with a real rectangle, take the
# tightest box that is still tall enough to be a block rather than a bare
# heading. That is the container holding the heading and its terms together --
# which is what the screenshot needs to show.
_PICK_ELEMENT_JS = """
  const MIN_BLOCK_HEIGHT = 40;
  const SKIP = {SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEMPLATE: 1, HEAD: 1};
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  const found = [];
  while (walker.nextNode()) {
    const el = walker.currentNode;
    if (SKIP[el.tagName]) continue;
    if (!el.innerText || el.innerText.indexOf(needle) === -1) continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    found.push({el: el, area: r.width * r.height, h: r.height});
  }
  if (!found.length) return null;
  found.sort((a, b) => a.area - b.area);
  let chosen = found.find(c => c.h >= MIN_BLOCK_HEIGHT) || found[0];
"""

_BOX_FOR_TEXT_JS = """
(() => {
  const needle = %s;
""" + _PICK_ELEMENT_JS + """
  const r = chosen.el.getBoundingClientRect();
  return {x: r.left + window.scrollX, y: r.top + window.scrollY,
          width: r.width, height: r.height,
          scroll_x: window.scrollX, scroll_y: window.scrollY};
})()
"""

_SCROLL_TO_TEXT_JS = """
(() => {
  const needle = %s;
""" + _PICK_ELEMENT_JS + """
  chosen.el.scrollIntoView({block: 'center', inline: 'nearest'});
  return true;
})()
"""


class LiveBrowserSession:
    """One visible tab, driven over CDP."""

    def __init__(self, connection: CdpConnection):
        self._cdp = connection
        self._cdp.send("Page.enable")
        self._cdp.send("Runtime.enable")
        self._cdp.send("Network.enable")

    # -- navigation ------------------------------------------------------- #

    def navigate(self, url: str) -> NavigationResult:
        try:
            self._cdp.send("Page.navigate", {"url": url},
                           timeout=NAVIGATION_TIMEOUT_SECONDS)
        except CdpTimeout:
            return NavigationResult(False, reason="NAVIGATION_TIMEOUT",
                                    detail="Page.navigate timed out")
        except CdpError as exc:
            return NavigationResult(False, reason="NAVIGATION_FAILED", detail=str(exc))

        if not self._wait_for_load():
            return NavigationResult(False, reason="NAVIGATION_TIMEOUT",
                                    detail="load event never fired")
        self._wait_for_network_quiet()

        try:
            final = self._cdp.evaluate("document.location.href") or ""
        except CdpError as exc:
            return NavigationResult(False, reason="NAVIGATION_FAILED", detail=str(exc))
        return NavigationResult(True, final_url=str(final))

    def _wait_for_load(self) -> bool:
        deadline = time.monotonic() + NAVIGATION_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            for ev in self._cdp.pump(0.5):
                if ev.get("method") in ("Page.loadEventFired",
                                        "Page.domContentEventFired"):
                    return True
            try:
                state = self._cdp.evaluate("document.readyState")
            except CdpError:
                state = None
            if state == "complete":
                return True
        return False

    def _wait_for_network_quiet(self) -> None:
        """Quiet = no Network request/response events for a settling window."""
        deadline = time.monotonic() + NETWORK_QUIET_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            events = self._cdp.pump(NETWORK_QUIET_SECONDS)
            if not any(str(e.get("method", "")).startswith("Network.") for e in events):
                return

    # -- reading ---------------------------------------------------------- #

    def snapshot(self) -> DomSnapshot:
        raw = self._cdp.evaluate(_EXTRACT_JS, timeout=60.0) or {}
        blocks = raw.get("jsonld") or []
        return DomSnapshot(
            final_url=str(raw.get("final_url") or ""),
            title=str(raw.get("title") or ""),
            canonical_url=str(raw.get("canonical_url") or ""),
            html=str(raw.get("html") or ""),
            text=str(raw.get("text") or ""),
            jsonld=tuple(b for b in blocks if isinstance(b, dict)),
            viewport_width=int(raw.get("vw") or 0),
            viewport_height=int(raw.get("vh") or 0))

    def query_selector_exists(self, selector: str) -> bool:
        expr = "!!document.querySelector(%s)" % json.dumps(selector)
        try:
            return bool(self._cdp.evaluate(expr))
        except CdpError:
            return False

    def viewport(self) -> Tuple[int, int]:
        try:
            raw = self._cdp.evaluate(
                "({w: window.innerWidth||0, h: window.innerHeight||0})") or {}
            return (int(raw.get("w") or 0), int(raw.get("h") or 0))
        except CdpError:
            return (0, 0)

    def evaluate(self, expression: str, timeout: float = 60.0):
        """Run one expression in the page and return its JSON value.

        The identity-view sweep probes the DOM with a script of its own rather
        than through one of the fixed accessors above -- it hunts an arbitrary
        set of needles and needs each painter's geometry back. Delegating is
        all that is required; every other caller keeps using the named methods,
        which stay the readable way to ask the page a known question.
        """
        return self._cdp.evaluate(expression, timeout=timeout)

    # -- interaction ------------------------------------------------------ #

    def click(self, selector: str) -> bool:
        """Click a visible control by selector.

        Uses the element's own ``click()`` rather than synthesising input at
        coordinates: it is the same event a user's click produces, and it does
        not require moving a virtual mouse around, which would be closer to
        imitating a human than to driving a browser.
        """
        expr = ("(() => { const el = document.querySelector(%s); "
                "if (!el) return false; el.click(); return true; })()"
                % json.dumps(selector))
        try:
            return bool(self._cdp.evaluate(expr))
        except CdpError:
            return False

    def click_text(self, selector: str, text: str) -> bool:
        """Click the first VISIBLE control matching ``selector`` whose label
        contains ``text``. Visibility matters: a tab strip often carries a
        duplicate hidden copy for small screens, and clicking that one does
        nothing while reporting success."""
        expr = ("(() => { const t = %s; "
                "for (const el of document.querySelectorAll(%s)) { "
                "  const label = (el.innerText || el.getAttribute('aria-label') || '');"
                "  if (label.trim().indexOf(t) === -1) continue; "
                "  const r = el.getBoundingClientRect(); "
                "  if (r.width <= 0 || r.height <= 0) continue; "
                "  el.click(); return true; } return false; })()"
                % (json.dumps(text), json.dumps(selector)))
        try:
            return bool(self._cdp.evaluate(expr))
        except CdpError:
            return False

    def scroll_into_view(self, selector: str) -> bool:
        expr = ("(() => { const el = document.querySelector(%s); if (!el) return false; "
                "el.scrollIntoView({block:'center', inline:'nearest'}); return true; })()"
                % json.dumps(selector))
        try:
            return bool(self._cdp.evaluate(expr))
        except CdpError:
            return False

    def scroll_to_text(self, needle: str) -> bool:
        try:
            return bool(self._cdp.evaluate(_SCROLL_TO_TEXT_JS % json.dumps(needle)))
        except CdpError:
            return False

    # -- geometry --------------------------------------------------------- #

    def box_model(self, selector: str) -> Optional[BoxModel]:
        expr = ("(() => { const el = document.querySelector(%s); if (!el) return null; "
                "const r = el.getBoundingClientRect(); "
                "return {x: r.left + window.scrollX, y: r.top + window.scrollY, "
                "width: r.width, height: r.height, "
                "scroll_x: window.scrollX, scroll_y: window.scrollY}; })()"
                % json.dumps(selector))
        return self._box(expr)

    def box_for_text(self, needle: str) -> Optional[BoxModel]:
        return self._box(_BOX_FOR_TEXT_JS % json.dumps(needle))

    def _box(self, expression: str) -> Optional[BoxModel]:
        try:
            raw = self._cdp.evaluate(expression)
        except CdpError:
            return None
        if not isinstance(raw, dict):
            return None
        return BoxModel(
            x=float(raw.get("x") or 0.0), y=float(raw.get("y") or 0.0),
            width=float(raw.get("width") or 0.0),
            height=float(raw.get("height") or 0.0),
            scroll_x=float(raw.get("scroll_x") or 0.0),
            scroll_y=float(raw.get("scroll_y") or 0.0))

    # -- capture ---------------------------------------------------------- #

    def screenshot_png(self) -> bytes:
        from ..capture_automation.capture_writer import decode_screenshot
        try:
            result = self._cdp.send("Page.captureScreenshot",
                                    {"format": "png", "fromSurface": True},
                                    timeout=60.0)
        except CdpError:
            return b""
        return decode_screenshot(str(result.get("data") or ""))

    def close(self) -> None:
        try:
            self._cdp.close()
        except Exception:                             # noqa: BLE001 - teardown
            pass
