"""A minimal Chrome DevTools Protocol client.

The only module in PTF-CAPTURE-003 that opens a socket. Hand-written rather
than delegating to Playwright or Selenium for one reason above all: every
command this build can send to a browser is visible in one file, so "prove this
contains no evasion" is a five-minute read rather than an audit of a dependency
tree and its plugin ecosystem.

It speaks only what the capture flow needs -- Page, Runtime, DOM, Emulation --
and has no method for cookies, storage, request interception or header
manipulation.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

DEFAULT_TIMEOUT = 30.0


class CdpError(RuntimeError):
    """Raised when the browser refuses or fails to answer."""


class CdpTimeout(CdpError):
    """Raised when a command or a wait exceeds its budget."""


def http_get_json(url: str, *, timeout: float = 10.0) -> Any:
    """Read Chrome's HTTP endpoint (``/json/version``, ``/json/list``).

    This and the WebSocket below are the sprint's entire network surface.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:   # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise CdpError("cannot reach Chrome at %s: %s" % (url, exc))


class CdpConnection:
    """One WebSocket to one target, with synchronous request/response.

    Chrome multiplexes commands and events over a single socket; commands carry
    an id and events do not. Events we did not ask for are buffered rather than
    discarded, because ``Page.loadEventFired`` and the ``Network`` activity
    events arrive interleaved with command replies and both are needed.
    """

    def __init__(self, ws_url: str, *, timeout: float = DEFAULT_TIMEOUT):
        try:
            import websocket                          # type: ignore
        except ImportError:                           # pragma: no cover
            raise CdpError(
                "websocket-client is required for browser control; "
                "install it with: python -m pip install websocket-client")
        self._ws_url = ws_url
        self._timeout = timeout
        self._next_id = 0
        self._events: list = []
        try:
            self._ws = websocket.create_connection(
                ws_url, timeout=timeout, max_size=None,
                suppress_origin=True)
        except Exception as exc:                      # noqa: BLE001
            raise CdpError("cannot open CDP socket: %s" % exc)

    # -- lifecycle -------------------------------------------------------- #

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:                             # noqa: BLE001 - teardown
            pass

    def __enter__(self) -> "CdpConnection":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- protocol --------------------------------------------------------- #

    def send(self, method: str, params: Optional[Dict[str, Any]] = None,
             *, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Issue one command and return its result."""
        budget = self._timeout if timeout is None else timeout
        self._next_id += 1
        msg_id = self._next_id
        payload = {"id": msg_id, "method": method, "params": params or {}}
        try:
            self._ws.send(json.dumps(payload))
        except Exception as exc:                      # noqa: BLE001
            raise CdpError("CDP send failed for %s: %s" % (method, exc))

        deadline = time.monotonic() + budget
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CdpTimeout("timed out waiting for %s" % method)
            frame = self._recv(remaining)
            if frame.get("id") == msg_id:
                if "error" in frame:
                    raise CdpError("%s failed: %s" % (method, frame["error"]))
                return frame.get("result") or {}
            if "method" in frame:
                self._events.append(frame)

    def _recv(self, timeout: float) -> Dict[str, Any]:
        try:
            self._ws.settimeout(max(0.1, timeout))
            raw = self._ws.recv()
        except Exception as exc:                      # noqa: BLE001
            if "timed out" in str(exc).lower():
                raise CdpTimeout("CDP receive timed out")
            raise CdpError("CDP receive failed: %s" % exc)
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise CdpError("CDP sent malformed JSON: %s" % exc)

    def drain_events(self) -> list:
        """Take the buffered events and clear the buffer."""
        events, self._events = self._events, []
        return events

    def pump(self, seconds: float) -> list:
        """Collect events for a fixed window. Used to detect network quiet."""
        deadline = time.monotonic() + seconds
        collected: list = []
        while time.monotonic() < deadline:
            try:
                frame = self._recv(deadline - time.monotonic())
            except CdpTimeout:
                break
            if "method" in frame:
                collected.append(frame)
        collected.extend(self.drain_events())
        return collected

    def evaluate(self, expression: str, *, timeout: Optional[float] = None,
                 await_promise: bool = False) -> Any:
        """Run JavaScript in the page and return its JSON value.

        Read-only by convention and by use: every call site in this sprint
        reads document state or scrolls. Nothing here submits a form, follows a
        link or alters page data.
        """
        result = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        }, timeout=timeout)
        if result.get("exceptionDetails"):
            detail = result["exceptionDetails"]
            raise CdpError("page script raised: %s"
                           % (detail.get("text") or detail))
        return (result.get("result") or {}).get("value")
