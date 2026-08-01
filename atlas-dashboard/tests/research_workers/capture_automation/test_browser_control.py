"""The browser seam, tested without a browser.

Nothing here launches Chrome or opens a socket. What is testable offline is the
part that matters most for the doctrine: which flags may be passed, that the
session protocol is honoured, and that the CLI is wired without reaching the
network.
"""

from __future__ import annotations

import pathlib

import pytest

from services.research_workers.browser_control.chrome_launcher import (
    LauncherError, assert_flags_permitted, build_flags, find_chrome, free_port,
)
from services.research_workers.browser_control.session import (
    BrowserSession, NavigationResult,
)
from services.research_workers.capture_automation.doctrine import (
    PERMITTED_CHROME_FLAGS,
)

from .conftest import FakeBrowserSession, pages_from


class TestFlagAllowlist:
    def test_the_default_flag_set_is_permitted(self):
        assert_flags_permitted(build_flags(9222, pathlib.Path("/tmp/profile")))

    def test_every_default_flag_is_on_the_allowlist(self):
        for flag in build_flags(9222, pathlib.Path("/tmp/profile")):
            assert flag.split("=", 1)[0] in PERMITTED_CHROME_FLAGS

    @pytest.mark.parametrize("flag", [
        "--headless", "--headless=new",
        "--proxy-server=http://127.0.0.1:8080",
        "--user-agent=Mozilla/5.0",
        "--disable-blink-features=AutomationControlled",
        "--disable-web-security",
        "--load-extension=/tmp/stealth",
    ])
    def test_a_forbidden_flag_is_refused(self, flag):
        with pytest.raises(LauncherError, match="not permitted"):
            assert_flags_permitted([flag])

    def test_the_profile_is_always_explicit(self):
        flags = build_flags(9222, pathlib.Path("/tmp/batch/.chrome-profile"))
        profile = [f for f in flags if f.startswith("--user-data-dir=")]
        assert len(profile) == 1
        assert ".chrome-profile" in profile[0]

    def test_the_debug_port_is_bound_to_the_chosen_value(self):
        assert "--remote-debugging-port=9333" in build_flags(
            9333, pathlib.Path("/tmp/p"))


class TestLauncherHelpers:
    def test_free_port_returns_something_usable(self):
        port = free_port()
        assert 1024 < port < 65536

    def test_missing_explicit_chrome_is_reported(self):
        with pytest.raises(LauncherError, match="chrome not found"):
            find_chrome("/definitely/not/here/chrome.exe")


class TestSessionProtocol:
    def test_the_fake_satisfies_the_protocol(self):
        session = FakeBrowserSession(pages_from("marriott-cmham.json"))
        assert isinstance(session, BrowserSession)

    def test_the_live_session_satisfies_the_protocol(self):
        """Structural check only -- no Chrome is started."""
        from services.research_workers.browser_control.live_session import (
            LiveBrowserSession,
        )
        for method in ("navigate", "snapshot", "click", "scroll_into_view",
                       "scroll_to_text", "box_model", "box_for_text",
                       "viewport", "screenshot_png", "close"):
            assert callable(getattr(LiveBrowserSession, method))

    def test_the_session_exposes_no_cookie_or_storage_method(self):
        """Not merely unused -- unavailable."""
        from services.research_workers.browser_control.live_session import (
            LiveBrowserSession,
        )
        names = " ".join(dir(LiveBrowserSession)).lower()
        for forbidden in ("cookie", "storage", "credential", "header", "intercept"):
            assert forbidden not in names

    def test_navigation_result_carries_a_reason_when_it_fails(self):
        r = NavigationResult(False, reason="NAVIGATION_TIMEOUT")
        from services.research_workers.capture_automation.reasons import (
            EXCEPTION_REASONS,
        )
        assert r.reason in EXCEPTION_REASONS


class TestCliWiring:
    def test_capture_batch_is_registered(self):
        from services.research_workers.cli import build_parser
        args = build_parser().parse_args([
            "capture-batch", "--queue", "q.json", "--output", "out"])
        assert args.queue == "q.json" and args.output == "out"

    def test_preflight_only_never_launches_chrome(self, tmp_path, capsys):
        """The cheapest possible proof that a bad queue costs no browser."""
        import json

        from services.research_workers.capture_automation.queue import QUEUE_SCHEMA
        from services.research_workers.cli import main

        queue = tmp_path / "q.json"
        queue.write_text(json.dumps({
            "schema": QUEUE_SCHEMA, "batch_id": "preflight-test",
            "hotels": [{
                "hotel_id": "cmham", "listing_key": "columbus-airport-marriott",
                "hotel_name": "Columbus Airport Marriott", "brand": "marriott",
                "official_url": "https://www.marriott.com/en-us/hotels/"
                                "cmham-columbus-airport-marriott/overview/",
                "expected_address": "1375 North Cassady Avenue",
                "expected_city": "Columbus", "expected_state": "OH",
                "expected_phone": "614-475-7551",
                "expected_property_code": "cmham"}]}), encoding="utf-8")

        code = main(["capture-batch", "--queue", str(queue),
                     "--output", str(tmp_path / "batch"), "--preflight-only"])
        assert code == 0
        assert "queue OK" in capsys.readouterr().out
        assert not (tmp_path / "batch").exists(), "preflight must write nothing"

    def test_a_bad_queue_exits_non_zero_without_a_browser(self, tmp_path, capsys):
        import json

        from services.research_workers.capture_automation.queue import QUEUE_SCHEMA
        from services.research_workers.cli import main

        queue = tmp_path / "q.json"
        queue.write_text(json.dumps({
            "schema": QUEUE_SCHEMA, "batch_id": "bad",
            "hotels": [{"hotel_id": "x", "brand": "marriott"}]}), encoding="utf-8")
        code = main(["capture-batch", "--queue", str(queue),
                     "--output", str(tmp_path / "batch")])
        assert code == 2
        assert "preflight failed" in capsys.readouterr().err
