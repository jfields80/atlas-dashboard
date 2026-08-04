"""Settling is not framing: verify after the page holds still, then re-scroll.

Three real hotels failed with the policy measured hundreds of pixels below the
fold AFTER the geometry had stopped moving:

    courtyard-columbus-downtown   box y 2959, scroll_y 1553, viewport 905
    le-meridien (attempt A)       box y 10895, scroll_y 9499, viewport 905

``_settle_policy`` waited for stillness and never asked whether the still
element was in frame, so the runner photographed a viewport the policy had
already left. The correction re-scrolls ONCE, from the geometry in hand.

What these tests defend against, in both directions:

  * the tolerance must not move -- ``policy_in_frame`` is the same predicate the
    final gate uses, so a re-scroll can only satisfy the rule, never relax it;
  * the correction must be computed, not remembered -- a hard-coded ~500px
    would be fitted to three samples and wrong on the fourth page;
  * one cycle only -- more would be a retry loop under another name;
  * a page that still will not frame must still fail POLICY_OFF_SCREEN.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from services.research_workers.capture_automation.contracts import BoxModel
from services.research_workers.capture_automation.queue import CaptureQueue
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.capture_automation.validators import (
    MIN_VISIBLE_FRACTION, policy_in_frame,
)

from .conftest import FakeBrowserSession, entry_for, pages_from

FIXTURE = "marriott-cmham.json"


class FrozenClock:
    def __init__(self):
        self.t = 1_781_000_000.0

    def __call__(self):
        self.t += 0.5
        return self.t


class ScrollableSession(FakeBrowserSession):
    """A page with a real scroll position and an element at a fixed page-y.

    ``box_model`` is derived from the current scroll rather than canned, which
    is what makes a corrective scroll observable at all: move the window and
    the element's viewport rect moves with it, exactly as in a browser.
    """

    def __init__(self, *, page_y: float, height: float, scroll_y: float,
                 viewport_h: int = 905, allow_scroll: bool = True,
                 evaluate_raises: bool = False):
        super().__init__(pages_from(FIXTURE), viewport=(1440, viewport_h))
        self.page_y, self.height = page_y, height
        self.scroll_y = scroll_y
        self._allow_scroll = allow_scroll
        self._evaluate_raises = evaluate_raises
        self.scroll_targets: List[int] = []

    def _current_box(self) -> Optional[BoxModel]:
        return BoxModel(x=0, y=self.page_y, width=600, height=self.height,
                        scroll_x=0.0, scroll_y=self.scroll_y)

    def evaluate(self, expression: str, timeout: float = 60.0):
        if self._evaluate_raises:
            raise RuntimeError("simulated CDP failure")
        if "aria-expanded" in expression:
            return None
        match = re.search(r"window\.scrollTo\(0,\s*(-?\d+)\)", expression)
        if match:
            target = int(match.group(1))
            self.scroll_targets.append(target)
            if self._allow_scroll:
                self.scroll_y = float(target)
            return self.scroll_y
        return None


def _runner(tmp_path, session):
    return CaptureRunner(
        session, RunnerConfig(batch_dir=tmp_path / "batch"),
        clock=FrozenClock(), sleep=lambda s: None, jitter=lambda a, b: a)


def _run(tmp_path, session) -> dict:
    result = _runner(tmp_path, session).run(
        CaptureQueue(batch_id="reframe", entries=(entry_for(FIXTURE),)))
    return result.manifest


def _handle_box(session) -> Tuple[Tuple[str, str], BoxModel]:
    return (("text", "Pet Policy"), session._current_box())


class TestCorrection:
    def test_below_fold_after_settle_is_rescrolled_into_frame(self, tmp_path):
        """The courtyard-columbus-downtown geometry, to the pixel."""
        session = ScrollableSession(page_y=2959, height=300, scroll_y=1553)
        assert not policy_in_frame(session._current_box(), 905), (
            "precondition: this geometry is the failure we are fixing")

        manifest = _run(tmp_path, session)

        assert session.scroll_targets, "no corrective scroll was attempted"
        assert policy_in_frame(session._current_box(), 905)
        assert manifest["counts"]["captured"] == 1

    def test_the_le_meridien_geometry_is_corrected_too(self, tmp_path):
        """A page ten thousand pixels tall, corrected by the same arithmetic."""
        session = ScrollableSession(page_y=10895, height=300, scroll_y=9499)
        manifest = _run(tmp_path, session)
        assert policy_in_frame(session._current_box(), 905)
        assert manifest["counts"]["captured"] == 1

    def test_the_correction_is_computed_not_a_remembered_constant(self, tmp_path):
        """Two pages, two different corrections.

        If the fix carried the observed ~490-501px offset as a constant, both
        pages would move by the same amount. They must not.
        """
        shallow = ScrollableSession(page_y=2000, height=300, scroll_y=1000)
        deep = ScrollableSession(page_y=8000, height=300, scroll_y=1000)
        _run(tmp_path / "a", shallow)
        _run(tmp_path / "b", deep)

        assert shallow.scroll_targets and deep.scroll_targets
        assert shallow.scroll_targets[0] != deep.scroll_targets[0]
        # Each lands the element's top near a third of the viewport down.
        for s in (shallow, deep):
            assert abs((s.page_y - s.scroll_y) - 905 / 3.0) < 2.0

    def test_correction_never_scrolls_above_the_top_of_the_document(self, tmp_path):
        """An element near the top must not produce a negative scroll."""
        session = ScrollableSession(page_y=10, height=300, scroll_y=900)
        _run(tmp_path, session)
        assert all(t >= 0 for t in session.scroll_targets)
        assert session.scroll_y >= 0


class TestBoundedness:
    def test_at_most_one_corrective_cycle(self, tmp_path):
        """A page that refuses to move is not scrolled repeatedly."""
        session = ScrollableSession(page_y=2959, height=300, scroll_y=1553,
                                    allow_scroll=False)
        _run(tmp_path, session)
        assert len(session.scroll_targets) == 1

    def test_a_page_that_still_will_not_frame_fails_off_screen(self, tmp_path):
        session = ScrollableSession(page_y=2959, height=300, scroll_y=1553,
                                    allow_scroll=False)
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 0
        assert [e["reason"] for e in manifest["exceptions"]] == ["POLICY_OFF_SCREEN"]

    def test_an_already_framed_policy_is_never_scrolled(self, tmp_path):
        """No speculative movement: a healthy capture stays byte-for-byte the
        page it already was."""
        session = ScrollableSession(page_y=1300, height=300, scroll_y=1000)
        assert policy_in_frame(session._current_box(), 905)
        manifest = _run(tmp_path, session)
        assert session.scroll_targets == []
        assert manifest["counts"]["captured"] == 1

    def test_a_partially_visible_policy_above_the_threshold_is_left_alone(self, tmp_path):
        """60% visible clears MIN_VISIBLE_FRACTION, so nothing moves."""
        session = ScrollableSession(page_y=1000 + 905 - 180, height=300,
                                    scroll_y=1000)
        box = session._current_box()
        assert 0.5 < (905 - (box.y - box.scroll_y)) / box.height < 0.7
        _run(tmp_path, session)
        assert session.scroll_targets == []


class TestFailsSafe:
    def test_no_box_means_no_scroll_attempt(self, tmp_path):
        session = ScrollableSession(page_y=2959, height=300, scroll_y=1553)
        session._current_box = lambda: None
        manifest = _run(tmp_path, session)
        assert session.scroll_targets == []
        assert [e["reason"] for e in manifest["exceptions"]] == ["POLICY_OFF_SCREEN"]

    def test_unknown_viewport_height_means_no_scroll_attempt(self, tmp_path):
        session = ScrollableSession(page_y=2959, height=300, scroll_y=1553,
                                    viewport_h=0)
        _run(tmp_path, session)
        assert session.scroll_targets == []

    def test_an_evaluate_failure_leaves_the_original_box(self, tmp_path):
        """A driver error must not take the batch down, and must not invent
        geometry -- the hotel fails the way it failed before."""
        session = ScrollableSession(page_y=2959, height=300, scroll_y=1553,
                                    evaluate_raises=True)
        manifest = _run(tmp_path, session)
        assert [e["reason"] for e in manifest["exceptions"]] == ["POLICY_OFF_SCREEN"]

    def test_a_session_without_evaluate_is_untouched(self, tmp_path):
        """Every offline fake lacks ``evaluate``; existing behaviour is exact."""
        session = FakeBrowserSession(pages_from(FIXTURE))
        assert not hasattr(session, "evaluate")
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 1


class TestToleranceUnchanged:
    def test_the_visibility_threshold_is_the_one_the_gate_already_used(self):
        """The fix moves the page, never the bar."""
        assert MIN_VISIBLE_FRACTION == 0.5

    def test_reframing_uses_the_gate_predicate_itself(self, tmp_path):
        """Whatever ``policy_in_frame`` accepts is exactly what stops the
        correction -- there is no second, looser notion of "close enough"."""
        session = ScrollableSession(page_y=2959, height=300, scroll_y=1553)
        runner = _runner(tmp_path, session)
        handle, box = _handle_box(session)
        assert not policy_in_frame(box, 905)
        corrected = runner._reframe_if_needed(handle, box)
        assert policy_in_frame(corrected, 905)
