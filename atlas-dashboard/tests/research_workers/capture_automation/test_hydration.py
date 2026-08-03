"""Bounded hydration readiness.

The failure this closes: Aloft Columbus University District returned
IDENTITY_UNVERIFIABLE / no_identity_signal after 7.2 seconds, then succeeded
unchanged on a later run. The runner took ONE snapshot at
domContentEventFired, so a page that was merely slow was indistinguishable
from a page with no identity at all.

The property under test throughout: waiting may only decide WHEN to look. It
must never admit a page that ``verify_identity`` would refuse.

Offline: no browser, no network, no wall clock.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from services.research_workers.capture_automation.contracts import DomSnapshot
from services.research_workers.capture_automation.hydration import (
    SIGNAL_ADAPTER_SELECTOR, SIGNAL_JSONLD_HOTEL, SIGNAL_OBSERVED_IDENTITY,
    SIGNAL_URL_CODE_AND_NAME, ReadinessResult, identity_signal,
    wait_for_identity,
)
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.capture_automation.queue import CaptureQueue

from .conftest import (
    FakeBrowserSession, entry_for, load_fixture, pages_from,
)

NAME = "marriott-cmham.json"


class Clock:
    """Deterministic monotonic clock advanced only by the injected sleep."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class ScriptedSession:
    """Returns a scripted list of snapshots, one per snapshot() call."""

    def __init__(self, snapshots, selectors=()):
        self._snapshots = list(snapshots)
        self.calls = 0
        self.selector_probes = []
        self._selectors = set(selectors)
        self.navigations = []

    def snapshot(self):
        self.calls += 1
        idx = min(self.calls - 1, len(self._snapshots) - 1)
        return self._snapshots[idx]

    def query_selector_exists(self, selector):
        self.selector_probes.append(selector)
        return selector in self._selectors

    # Anything else being called would mean the wait is doing more than look.
    def navigate(self, url):
        self.navigations.append(url)
        raise AssertionError("hydration must never navigate")

    def __getattr__(self, item):
        raise AssertionError("hydration must not call session.%s" % item)


def hydrated_dom():
    return DomSnapshot.from_capture_payload(load_fixture(NAME))


def blank_dom(text="Loading…"):
    payload = load_fixture(NAME)
    return DomSnapshot(final_url=payload["final_url"], title="",
                       canonical_url="", html="<html></html>", text=text,
                       jsonld=())


def name_only_dom():
    """Visible hotel identity rendered, JSON-LD not yet injected."""
    payload = load_fixture(NAME)
    return DomSnapshot(
        final_url=payload["final_url"], title="",
        canonical_url=payload["canonical_url"], html="<html></html>",
        text=("Columbus Airport Marriott\n1375 North Cassady Avenue\n"
              "Columbus, OH 43219\nCheck-in 3:00 pm"),
        jsonld=())


ENTRY = entry_for(NAME)


def run(snapshots, **kw):
    clock = Clock()
    session = ScriptedSession(snapshots, selectors=kw.pop("selectors", ()))
    result = wait_for_identity(session, ENTRY, clock=clock, sleep=clock.sleep, **kw)
    return result, session, clock


# --------------------------------------------------------------------------- #
# 1. The signals.
# --------------------------------------------------------------------------- #

class TestIdentitySignal:
    def test_jsonld_hotel_is_the_strongest(self):
        assert identity_signal(hydrated_dom(), ENTRY) == SIGNAL_JSONLD_HOTEL

    def test_visible_name_plus_url_code_qualifies(self):
        assert identity_signal(name_only_dom(), ENTRY) in (
            SIGNAL_URL_CODE_AND_NAME, SIGNAL_OBSERVED_IDENTITY)

    def test_an_empty_page_has_no_signal(self):
        assert identity_signal(blank_dom(), ENTRY) == ""

    def test_none_snapshot_has_no_signal(self):
        assert identity_signal(None, ENTRY) == ""

    def test_brand_words_alone_do_not_qualify(self):
        """A brand landing page names the chain, not the property."""
        dom = DomSnapshot(final_url="https://www.marriott.com/hotels/",
                          text="Marriott Hotels and Suites. Inn. The resort.")
        assert identity_signal(dom, ENTRY) == ""

    def test_adapter_selector_is_additive_only(self):
        class A:
            def identity_selectors(self):
                return ("[data-testid='property-header']",)
        session = ScriptedSession([blank_dom()],
                                  selectors=["[data-testid='property-header']"])
        assert identity_signal(blank_dom(), ENTRY, adapter=A(),
                               session=session) == SIGNAL_ADAPTER_SELECTOR

    def test_a_broken_adapter_selector_never_raises(self):
        class A:
            def identity_selectors(self):
                return ("::::bad",)

        class Boom:
            def query_selector_exists(self, sel):
                raise RuntimeError("bad selector")
        assert identity_signal(blank_dom(), ENTRY, adapter=A(), session=Boom()) == ""


# --------------------------------------------------------------------------- #
# 2. Waiting.
# --------------------------------------------------------------------------- #

class TestWaiting:
    def test_jsonld_present_immediately(self):
        result, session, clock = run([hydrated_dom()] * 2)
        assert result.ready
        assert result.signal == SIGNAL_JSONLD_HOTEL
        assert result.checks == 2          # stability still requires two looks
        assert not result.timed_out

    def test_jsonld_appears_after_several_polls(self):
        snaps = [blank_dom(), blank_dom(), blank_dom(),
                 hydrated_dom(), hydrated_dom()]
        result, session, clock = run(snaps)
        assert result.ready
        assert result.signal == SIGNAL_JSONLD_HOTEL
        assert result.checks == 5
        assert clock.t == pytest.approx(4.0)      # four 1s sleeps
        assert result.signal_history[:3] == ("-", "-", "-")

    def test_visible_identity_before_jsonld_is_accepted(self):
        result, _s, _c = run([name_only_dom()] * 2)
        assert result.ready
        assert result.signal in (SIGNAL_URL_CODE_AND_NAME, SIGNAL_OBSERVED_IDENTITY)

    def test_stable_signal_across_two_checks_passes(self):
        result, _s, _c = run([hydrated_dom(), hydrated_dom()])
        assert result.ready and result.checks == 2

    def test_one_sighting_is_not_enough(self):
        """Present once then gone is not a hydrated page."""
        snaps = [hydrated_dom(), blank_dom(), blank_dom()]
        result, _s, _c = run(snaps, timeout=2.0)
        assert not result.ready and result.timed_out

    def test_unstable_signal_does_not_pass(self):
        """Signal present both times, but the text is still growing fast."""
        big = load_fixture(NAME)
        half = dict(big, text=(big["text"] or "")[: len(big["text"]) // 2])
        snaps = [DomSnapshot.from_capture_payload(half),
                 DomSnapshot.from_capture_payload(big),
                 DomSnapshot.from_capture_payload(half)]
        result, _s, _c = run(snaps, timeout=2.0)
        assert not result.ready
        assert result.timed_out

    def test_timeout_is_bounded_and_fails_closed(self):
        result, session, clock = run([blank_dom()] * 50, timeout=5.0)
        assert not result.ready
        assert result.timed_out
        assert clock.t <= 6.0
        assert session.calls <= 7

    def test_timeout_still_reports_the_final_identity_fields(self):
        result, _s, _c = run([blank_dom()] * 10, timeout=3.0)
        assert result.identity is not None
        assert result.dom is not None

    def test_challenge_interrupts_waiting_immediately(self):
        challenge = blank_dom("Please verify you are a human. reCAPTCHA")
        result, session, clock = run([challenge] + [hydrated_dom()] * 5)
        assert not result.ready
        assert result.blocked_reason == "captcha_or_challenge_page"
        assert session.calls == 1, "must not keep polling a bot wall"
        assert clock.t == 0.0

    def test_access_denied_interrupts_immediately(self):
        denied = blank_dom("Access Denied. You don't have permission")
        result, session, _c = run([denied] * 3)
        assert result.blocked_reason == "access_denied_page"
        assert session.calls == 1

    def test_no_refresh_or_navigation_is_performed(self):
        """ScriptedSession raises on any call other than snapshot/selector."""
        result, session, _c = run([blank_dom()] * 5, timeout=2.0)
        assert session.navigations == []
        assert not result.ready

    def test_diagnostics_are_complete(self):
        result, _s, _c = run([blank_dom(), hydrated_dom(), hydrated_dom()])
        d = result.to_dict()
        for key in ("ready", "signal", "checks", "waited_seconds", "timed_out",
                    "blocked_reason", "signal_history", "identity"):
            assert key in d
        assert d["ready"] is True
        assert d["checks"] == 3
        assert d["signal_history"] == ["-", SIGNAL_JSONLD_HOTEL, SIGNAL_JSONLD_HOTEL]


# --------------------------------------------------------------------------- #
# 3. Through the runner.
# --------------------------------------------------------------------------- #

class RunnerClock:
    def __init__(self):
        self.t = 1_781_000_000.0

    def __call__(self):
        self.t += 0.5
        return self.t


def make_runner(tmp_path, session):
    slept = []
    return CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "batch"),
                         clock=RunnerClock(), sleep=slept.append,
                         jitter=lambda a, b: a), slept


class TestThroughTheRunner:
    def test_a_slow_page_is_captured_not_rejected(self, tmp_path):
        """The Aloft failure, reproduced and fixed: identity arrives late."""
        payload = load_fixture(NAME)
        empty = dict(payload, text="Loading…", jsonld=[])
        session = FakeBrowserSession(
            pages_from(NAME),
            snapshot_sequence={payload["final_url"]:
                               [empty, empty, payload, payload, payload, payload]})
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(CaptureQueue(batch_id="b", entries=(entry_for(NAME),)))
        assert result.manifest["counts"]["captured"] == 1

    def test_a_permanently_anonymous_page_still_fails_closed(self, tmp_path):
        payload = load_fixture(NAME)
        empty = dict(payload, text="Loading…", jsonld=[])
        session = FakeBrowserSession(
            pages_from(NAME),
            snapshot_sequence={payload["final_url"]: [empty]})
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(CaptureQueue(batch_id="b", entries=(entry_for(NAME),)))
        exc = result.manifest["exceptions"][0]
        assert exc["reason"] == "IDENTITY_UNVERIFIABLE"
        assert any("hydration_timeout" in d or "no_identity_signal" in d
                   for d in exc["detail"])

    def test_one_hydration_timeout_does_not_stop_the_next_hotel(self, tmp_path):
        slow, good = load_fixture(NAME), load_fixture("marriott-cmhaw.json")
        empty = dict(slow, text="Loading…", jsonld=[])
        session = FakeBrowserSession(
            pages_from(NAME, "marriott-cmhaw.json"),
            snapshot_sequence={slow["final_url"]: [empty]})
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(CaptureQueue(
            batch_id="b",
            entries=(entry_for(NAME), entry_for("marriott-cmhaw.json"))))
        assert result.manifest["counts"]["captured"] == 1
        assert result.manifest["counts"]["exceptions"] == 1
        # Distinct pages: a hotel that captures is requested again so its
        # identity can be photographed with the policy modal gone.
        assert len(set(session.navigations)) == 2, "the batch must continue"

    def test_hydration_diagnostics_land_in_the_capture(self, tmp_path):
        session = FakeBrowserSession(pages_from(NAME))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(CaptureQueue(batch_id="b", entries=(entry_for(NAME),)))
        payload = json.loads(pathlib.Path(
            result.manifest["successful_captures"][0]["json_path"]).read_text("utf-8"))
        hyd = payload["automation"]["hydration"]
        assert hyd["ready"] is True
        assert hyd["signal"] == SIGNAL_JSONLD_HOTEL
        assert hyd["checks"] >= 2
        assert hyd["timed_out"] is False

    def test_readiness_cannot_admit_a_page_identity_would_refuse(self, tmp_path):
        """A hydrated page for the WRONG hotel is still refused."""
        session = FakeBrowserSession(pages_from(NAME))
        runner, _ = make_runner(tmp_path, session)
        wrong = entry_for(NAME, expected_property_code="cmhzz")
        result = runner.run(CaptureQueue(batch_id="b", entries=(wrong,)))
        assert result.manifest["counts"]["captured"] == 0
        assert result.manifest["exceptions"][0]["reason"] == "PROPERTY_CODE_MISMATCH"

    def test_a_challenge_page_is_still_a_challenge_not_a_timeout(self, tmp_path):
        payload = load_fixture(NAME)
        pages = pages_from(NAME)
        pages[payload["final_url"]] = dict(
            payload, text="Please verify you are a human. reCAPTCHA")
        session = FakeBrowserSession(pages)
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(CaptureQueue(batch_id="b", entries=(entry_for(NAME),)))
        assert result.manifest["exceptions"][0]["reason"] == "CAPTCHA_OR_CHALLENGE"
