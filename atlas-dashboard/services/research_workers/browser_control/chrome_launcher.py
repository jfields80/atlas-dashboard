"""Launch a dedicated, visible Chrome for one batch.

Never the operator's normal profile. ``--remote-debugging-port`` grants any
local process full cookie and storage access to whatever profile it is pointed
at; aiming it at the everyday profile would hand out exactly the credentials
the capture extension proudly cannot reach. A fresh ``--user-data-dir`` has no
sessions to leak, which is the cheapest possible way to keep that guarantee
true.

Flags are an allowlist (``PERMITTED_CHROME_FLAGS``). A new flag has to be
argued for, not merely not-yet-banned.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

from ..capture_automation.doctrine import PERMITTED_CHROME_FLAGS
from .cdp_client import CdpError, http_get_json

_WINDOWS_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
)
_POSIX_CANDIDATES = (
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


class LauncherError(RuntimeError):
    """Raised when a compliant Chrome cannot be started."""


def find_chrome(explicit: str = "") -> str:
    if explicit:
        if not pathlib.Path(explicit).exists():
            raise LauncherError("chrome not found at %s" % explicit)
        return explicit
    for name in ("chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    for cand in (_WINDOWS_CANDIDATES if os.name == "nt" else _POSIX_CANDIDATES):
        expanded = os.path.expandvars(cand)
        if pathlib.Path(expanded).exists():
            return expanded
    raise LauncherError("could not locate a Chrome executable; pass --chrome-path")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def assert_flags_permitted(flags: Sequence[str]) -> None:
    """Every flag must be on the ADR's allowlist.

    This is the mechanical half of the doctrine: a stealth flag cannot be added
    by accident, because adding it means editing an allowlist a test reads.
    """
    for flag in flags:
        name = flag.split("=", 1)[0]
        if name not in PERMITTED_CHROME_FLAGS:
            raise LauncherError(
                "chrome flag not permitted by ADR-PTF-AUTOMATED-BROWSING: %s" % name)


@dataclass
class ChromeProcess:
    """A running Chrome plus the profile it owns."""

    process: subprocess.Popen
    port: int
    user_data_dir: pathlib.Path
    websocket_url: str

    def stop(self, *, timeout: float = 10.0) -> None:
        """Shut the browser down. Never raises.

        Asks over CDP first, because the process we spawned is often only a
        launcher: the browser that actually owns the window has a different PID
        and terminating our handle would leave it running with a debugging port
        open. ``Browser.close`` reaches the real one.
        """
        try:
            from .cdp_client import CdpConnection
            with CdpConnection(self.websocket_url, timeout=5.0) as conn:
                conn.send("Browser.close", timeout=5.0)
        except Exception:                             # noqa: BLE001 - teardown
            pass
        try:
            self.process.terminate()
            self.process.wait(timeout=timeout)
        except Exception:                             # noqa: BLE001 - teardown
            try:
                self.process.kill()
            except Exception:                         # noqa: BLE001
                pass


def page_websocket_url(port: int, *, timeout: float = 20.0) -> str:
    """The debugger URL of a real page target.

    Asked of Chrome rather than derived from the browser socket's address: a
    page target lives at ``/devtools/page/<id>``, not ``/devtools/browser/<id>``,
    and constructing one by string surgery produces a 404 handshake.
    """
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            targets = http_get_json("http://127.0.0.1:%d/json/list" % port, timeout=3.0)
        except CdpError as exc:
            last = str(exc)
            time.sleep(0.3)
            continue
        for target in targets or []:
            if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                return str(target["webSocketDebuggerUrl"])
        time.sleep(0.3)
    raise LauncherError("no page target appeared on port %d (%s)" % (port, last))


def build_flags(port: int, user_data_dir: pathlib.Path,
                *, window_size: str = "1440,1000") -> List[str]:
    """The exact flag set. Visible window; no headless, no UA override, no
    proxy, no automation-concealment flag."""
    return [
        "--remote-debugging-port=%d" % port,
        "--user-data-dir=%s" % user_data_dir,
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--window-size=%s" % window_size,
    ]


def launch(*, user_data_dir, chrome_path: str = "", port: int = 0,
           window_size: str = "1440,1000",
           startup_timeout: float = 30.0) -> ChromeProcess:
    """Start Chrome and wait until its DevTools endpoint answers."""
    exe = find_chrome(chrome_path)
    # Absolute, always. Chrome silently declines to bind the debugging port
    # when --user-data-dir is relative, which surfaces only as "did not expose
    # DevTools" thirty seconds later -- resolve it here so no caller can
    # reintroduce that.
    profile = pathlib.Path(user_data_dir).resolve()
    profile.mkdir(parents=True, exist_ok=True)

    chosen = port or free_port()
    flags = build_flags(chosen, profile, window_size=window_size)
    assert_flags_permitted(flags)

    proc = subprocess.Popen([exe] + flags,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Readiness is the DevTools endpoint answering, NOT the spawned process
    # staying alive. On Windows the process we start is frequently a launcher
    # that hands off to a browser with a different PID and exits 0 immediately;
    # treating that as failure made every launch fail while Chrome was in fact
    # coming up fine.
    deadline = time.monotonic() + startup_timeout
    last: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            info = http_get_json("http://127.0.0.1:%d/json/version" % chosen, timeout=2.0)
            ws = str(info.get("webSocketDebuggerUrl") or "")
            if ws:
                return ChromeProcess(process=proc, port=chosen,
                                     user_data_dir=profile, websocket_url=ws)
        except CdpError as exc:
            last = exc
        time.sleep(0.4)

    exited = proc.poll()
    try:
        proc.terminate()
    except Exception:                                 # noqa: BLE001
        pass
    raise LauncherError(
        "chrome did not expose DevTools on port %d in %.0fs "
        "(launcher exit=%s; last error: %s)"
        % (chosen, startup_timeout, exited, last))
