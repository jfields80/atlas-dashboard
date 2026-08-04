"""Drift needs two measurements, because each one alone fails the other's case.

Two real captures were refused for movement that never happened:

    Le Meridien   content moved 31px in page coords, camera moved 30px the same
                  way, so the block sat still under the camera (424.5px from the
                  viewport top before, 423.8px after)  -> "geometry_drift_px:31"
    IHG           content sat rock-still at page-y 6233 while captureScreenshot
                  nudged window.scrollY by 106px       -> "geometry_drift_px:106"
                  (three runs in a row, under a viewport-relative test)

They are opposites. Page-coordinate drift alone refuses the first;
viewport-relative drift alone refuses the second. Neither single metric can
accept both, so the predicate keeps BOTH and rejects only when both agree the
policy moved.

The case the check exists for is untouched: a capture describing a section
470px from the one in the image moves in both frames of reference at once.
"""

from __future__ import annotations

import pytest

from services.research_workers.capture_automation.contracts import BoxModel
from services.research_workers.capture_automation.validators import (
    check_policy_framing, visible_fraction,
)

VIEWPORT_H = 905.0


def box(y: float, scroll_y: float, *, height: float = 56.0) -> BoxModel:
    return BoxModel(x=324.5, y=y, width=760.0, height=height,
                    scroll_x=0.0, scroll_y=scroll_y)


def drifts(before: BoxModel, after: BoxModel):
    page = abs(after.y - before.y)
    viewport = abs((after.y - after.scroll_y) - (before.y - before.scroll_y))
    return (page, viewport)


class TestBothMustAgreeBeforeRejecting:
    def test_page_and_camera_move_together_is_accepted(self):
        """Le Meridien, from the real diagnostic geometry."""
        before, after = box(10895.546875, 10471.0), box(10864.8125, 10441.0)
        page, viewport = drifts(before, after)
        assert page > 20 and viewport < 2, (page, viewport)
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        assert ok, why

    def test_the_camera_moving_alone_is_accepted(self):
        """IHG: content still at page-y 6233, scrollY nudged 106px."""
        before, after = box(6233.0, 5500.0), box(6233.0, 5606.0)
        page, viewport = drifts(before, after)
        assert page == 0 and viewport == 106
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        assert ok, why

    def test_both_materially_large_is_rejected(self):
        """The Marriott failure the check exists for: a capture describing a
        section 470px from the one in the image."""
        before, after = box(1200.0, 900.0), box(1670.0, 900.0)
        page, viewport = drifts(before, after)
        assert page == 470 and viewport == 470
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        assert not ok
        assert "geometry_drift_px:470" in why
        assert "viewport_drift_px:470" in why

    def test_a_still_capture_is_accepted(self):
        ok, why = check_policy_framing(box(1200.0, 900.0), box(1200.0, 900.0),
                                       VIEWPORT_H)
        assert ok, why

    @pytest.mark.parametrize("page_move,scroll_move", [
        (30.0, 30.0), (120.0, 120.0), (500.0, 500.0), (-45.0, -45.0),
    ])
    def test_any_pure_scroll_compensation_is_accepted(self, page_move, scroll_move):
        """However far the page reflows, if the camera followed exactly, the
        image shows the same thing."""
        before = box(5000.0, 4600.0)
        after = box(5000.0 + page_move, 4600.0 + scroll_move)
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        assert ok, why


class TestMaterialCameraMovementIsStillRefused:
    """A camera move large enough to matter is caught BEFORE the drift check.

    This is what reconciles "reject when the viewport-relative position moves
    materially" with "IHG's 106px stays accepted": the in-frame gate runs first
    and is the accurate predicate for it. 106px leaves the policy fully visible;
    900px does not, and the earlier check says so by name.
    """

    def test_a_camera_move_that_pushes_the_policy_out_of_frame_is_rejected(self):
        before, after = box(6233.0, 5500.0), box(6233.0, 6400.0)
        assert visible_fraction(after, VIEWPORT_H) == 0.0
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        assert not ok
        assert why.startswith("off_screen_after_screenshot")

    def test_it_is_refused_before_drift_is_ever_consulted(self):
        """The reason names the frame, not the drift -- so an operator reading
        it is told the real problem."""
        before, after = box(6233.0, 5500.0), box(6233.0, 6900.0)
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        assert not ok and "drift" not in why

    def test_an_out_of_frame_before_reading_is_still_rejected(self):
        before, after = box(6233.0, 4000.0), box(6233.0, 5606.0)
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        assert not ok
        assert why.startswith("off_screen_before_screenshot")


class TestUnchangedGuarantees:
    def test_a_height_change_is_still_rejected_independently(self):
        """Drift and height are separate failures; the dual rule touches only
        drift."""
        before, after = box(1200.0, 900.0), box(1200.0, 900.0, height=400.0)
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        assert not ok
        assert "geometry_height_changed_px" in why

    def test_a_missing_reading_is_still_rejected(self):
        assert not check_policy_framing(None, box(1200.0, 900.0), VIEWPORT_H)[0]
        assert not check_policy_framing(box(1200.0, 900.0), None, VIEWPORT_H)[0]

    def test_the_rejection_reason_reports_both_numbers(self):
        """An operator should not have to guess which measurement fired."""
        # Both readings stay in frame, so the drift rule is what fires.
        before, after = box(1000.0, 500.0), box(1600.0, 1000.0)
        ok, why = check_policy_framing(before, after, VIEWPORT_H)
        page, viewport = drifts(before, after)
        assert (page, viewport) == (600.0, 100.0)
        assert not ok
        assert ("geometry_drift_px:%.0f" % page) in why
        assert ("viewport_drift_px:%.0f" % viewport) in why
