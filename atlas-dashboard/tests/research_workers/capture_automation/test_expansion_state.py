"""A click that REPORTS success has not necessarily opened anything.

Expo Center is the page that forced this. Both accordion clicks came back
``performed: True`` and every one of its eleven panels stayed shut -- the count
of ``aria-expanded="true"`` controls was 0, while every IHG page that captured
cleanly showed exactly 1. The pet text was in the HTML the whole time, sealed
inside a ``display:none`` panel.

The fix verifies the control's own ``aria-expanded`` and allows exactly one
re-click. What it must NOT do is read the sealed text: a capture whose
screenshot cannot show what its text claims is worse than no capture, so a page
that will not open stays POLICY_NOT_FOUND.
"""

from __future__ import annotations

import copy
import json
import pathlib
from typing import Dict, List, Optional

from services.research_workers.capture_automation.queue import CaptureQueue
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)

from .conftest import FakeBrowserSession, entry_for, load_fixture

IHG = "ihg-cmhtc.json"


def _pet_answer() -> str:
    """The FAQ answer IHG hides behind its accordion button, verbatim.

    Sliced out of the real fixture rather than retyped, so the collapsed page
    below is the actual page minus exactly the panel that was sealed.
    """
    text = load_fixture(IHG)["text"]
    start = text.index("Can I bring my pet")
    return text[start:text.index("READ FEWER FAQS", start)]


PET_ANSWER = _pet_answer()


def _payloads():
    """(collapsed, expanded) versions of one real IHG page.

    Collapsed is the honest model of the failure: the pet answer is present in
    ``html`` -- it really is in the DOM -- and absent from ``text``, because
    ``document.body.innerText`` does not report a ``display:none`` panel.
    """
    expanded = load_fixture(IHG)
    collapsed = copy.deepcopy(expanded)
    collapsed["text"] = expanded["text"].replace(PET_ANSWER, "")
    assert "bring my pet" not in collapsed["text"]
    # The control is on the page in both states -- that is what makes the
    # adapter propose the click at all.
    marker = '<div class="cmp-accordion"><button class="cmp-accordion__button" '
    marker += 'aria-expanded="false">Can I bring my pet to this hotel?</button>'
    marker += '<div hidden>%s</div></div>' % PET_ANSWER
    collapsed["html"] = expanded["html"] + marker
    expanded = copy.deepcopy(expanded)
    expanded["html"] = collapsed["html"].replace('aria-expanded="false"',
                                                 'aria-expanded="true"')
    return collapsed, expanded


class AccordionSession(FakeBrowserSession):
    """A page whose panel opens on the Nth click -- or never.

    ``click_text`` always returns True, exactly as the real driver did on Expo
    Center: it found the element and dispatched the click. Whether the panel
    opened is a separate question, and answering it is the point of the fix.
    """

    def __init__(self, collapsed: dict, expanded: dict, *, opens_on_click: int):
        super().__init__({collapsed["final_url"]: collapsed})
        self._collapsed, self._expanded = collapsed, expanded
        self._opens_on = opens_on_click
        self.click_text_calls: List[str] = []
        self.is_expanded = False
        self.evaluations: List[str] = []

    def click_text(self, selector: str, text: str) -> bool:
        self.click_text_calls.append(text)
        if self._opens_on and len(self.click_text_calls) >= self._opens_on:
            self.is_expanded = True
            self.pages[self._collapsed["final_url"]] = self._expanded
        return True

    def evaluate(self, expression: str, timeout: float = 60.0):
        self.evaluations.append(expression)
        if "aria-expanded" in expression:
            return self.is_expanded
        if "scrollTo" in expression:
            return 0
        return None


def _run(tmp_path, session) -> dict:
    class Clock:
        t = 1_781_000_000.0

        def __call__(self):
            Clock.t += 0.5
            return Clock.t

    runner = CaptureRunner(
        session, RunnerConfig(batch_dir=tmp_path / "batch"),
        clock=Clock(), sleep=lambda s: None, jitter=lambda a, b: a)
    entry = entry_for(IHG)
    result = runner.run(CaptureQueue(batch_id="expansion", entries=(entry,)))
    return result.manifest


def _interaction_log(batch_dir: pathlib.Path) -> List[dict]:
    """The written capture's own record of what was done to the page."""
    for path in sorted((batch_dir / "captures").glob("*.json")):
        if path.name.endswith(".view.json"):
            continue
        payload = json.loads(path.read_text("utf-8"))
        return (payload.get("automation") or {}).get("interaction_log") or []
    return []


class TestExpansionVerification:
    def test_first_click_opens_and_the_capture_succeeds(self, tmp_path):
        collapsed, expanded = _payloads()
        session = AccordionSession(collapsed, expanded, opens_on_click=1)
        manifest = _run(tmp_path, session)

        assert manifest["counts"]["captured"] == 1
        assert session.click_text_calls == ["bring my pet"], (
            "a control that opened first time must never be clicked twice")
        log = _interaction_log(tmp_path / "batch")
        pet = [s for s in log if s.get("text") == "bring my pet"]
        assert pet and pet[0]["expanded"] is True
        assert "reclicked" not in pet[0]

    def test_first_click_reports_success_but_panel_stays_shut_second_opens(self, tmp_path):
        """The Expo Center shape, with a page that yields on the retry."""
        collapsed, expanded = _payloads()
        session = AccordionSession(collapsed, expanded, opens_on_click=2)
        manifest = _run(tmp_path, session)

        assert session.click_text_calls == ["bring my pet", "bring my pet"]
        assert manifest["counts"]["captured"] == 1
        pet = [s for s in _interaction_log(tmp_path / "batch")
               if s.get("text") == "bring my pet"]
        assert pet and pet[0]["reclicked"] is True
        assert pet[0]["expanded"] is True

    def test_two_failed_clicks_leave_policy_not_found_unchanged(self, tmp_path):
        collapsed, expanded = _payloads()
        session = AccordionSession(collapsed, expanded, opens_on_click=0)
        manifest = _run(tmp_path, session)

        assert manifest["counts"]["captured"] == 0
        reasons = [e["reason"] for e in manifest["exceptions"]]
        assert reasons == ["POLICY_NOT_FOUND"]

    def test_never_more_than_one_re_click(self, tmp_path):
        """Bounded means bounded: a page that refuses is not hammered."""
        collapsed, expanded = _payloads()
        session = AccordionSession(collapsed, expanded, opens_on_click=0)
        _run(tmp_path, session)
        assert len(session.click_text_calls) == 2

    def test_hidden_text_is_never_accepted_as_evidence(self, tmp_path):
        """The pet answer is in the DOM the whole time. It must not be read.

        This is the guarantee the whole fix exists to protect: text a
        screenshot cannot show never becomes a capture.
        """
        collapsed, expanded = _payloads()
        assert PET_ANSWER in collapsed["html"], "fixture must model the sealed panel"
        assert "bring my pet" not in collapsed["text"]

        session = AccordionSession(collapsed, expanded, opens_on_click=0)
        manifest = _run(tmp_path, session)

        assert manifest["successful_captures"] == []
        assert not list((tmp_path / "batch" / "captures").glob("*.json")) \
            if (tmp_path / "batch" / "captures").exists() else True


class TestExistingCapturesUnchanged:
    def test_a_session_without_evaluate_behaves_exactly_as_before(self, tmp_path):
        """Every offline fake lacks ``evaluate``; none of them may change.

        Verification is unavailable rather than failed when the page cannot be
        asked, and unavailable must never be read as "did not expand".
        """
        from .conftest import pages_from
        names = ["marriott-cmham.json", "marriott-cmhaw.json", "hilton-cmhaphx.json"]
        session = FakeBrowserSession(pages_from(*names))
        assert not hasattr(session, "evaluate")

        class Clock:
            t = 1_781_000_000.0

            def __call__(self):
                Clock.t += 0.5
                return Clock.t

        runner = CaptureRunner(
            session, RunnerConfig(batch_dir=tmp_path / "batch"),
            clock=Clock(), sleep=lambda s: None, jitter=lambda a, b: a)
        result = runner.run(CaptureQueue(
            batch_id="unchanged", entries=tuple(entry_for(n) for n in names)))
        assert result.manifest["counts"]["captured"] == 3
        assert result.manifest["counts"]["exceptions"] == 0

    def test_a_control_without_aria_expanded_is_unknown_not_failed(self, tmp_path):
        collapsed, expanded = _payloads()

        class NoAria(AccordionSession):
            def evaluate(self, expression, timeout: float = 60.0):
                if "aria-expanded" in expression:
                    return None     # the control exposes no such attribute
                return super().evaluate(expression, timeout)

        session = NoAria(collapsed, expanded, opens_on_click=1)
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 1
        assert len(session.click_text_calls) == 1, (
            "an unobservable control must not trigger a speculative re-click")
