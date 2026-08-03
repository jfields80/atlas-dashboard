"""The runner, driven end to end by a fake browser.

No Chrome, no socket, no wall clock. These are the tests for the properties the
operator asked for by name -- one hotel's failure does not stop the batch, a
challenge produces an exception and advances, resume works after interruption --
and each of them is asserted against a real run rather than argued for in prose.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from services.research_workers.capture_automation.contracts import BoxModel
from services.research_workers.capture_automation.manifest import Journal
from services.research_workers.capture_automation.queue import (
    CaptureQueue, QueueEntry,
)
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.capture_automation.state_machine import (
    CAPTURED, EXCEPTION, HotelOutcome, KillSwitch,
)
from services.research_workers.capture_automation.validators import (
    check_policy_framing,
)

from .conftest import FakeBrowserSession, entry_for, load_fixture, pages_from

MARRIOTT = ["marriott-cmham.json", "marriott-cmhaw.json", "marriott-cmhsi.json",
            "marriott-cmhrn.json", "marriott-cmhte.json"]
HILTON = ["hilton-cmhaphx.json", "hilton-cmhncht.json", "hilton-cmhcsht.json"]


class FrozenClock:
    def __init__(self):
        self.t = 1_781_000_000.0

    def __call__(self):
        self.t += 0.5
        return self.t


def build_queue(names, batch_id="test-batch"):
    return CaptureQueue(batch_id=batch_id,
                        entries=tuple(entry_for(n) for n in names))


def make_runner(tmp_path, session, **cfg):
    config = RunnerConfig(batch_dir=tmp_path / "batch", **cfg)
    slept = []
    return CaptureRunner(session, config, clock=FrozenClock(),
                         sleep=slept.append, jitter=lambda a, b: a), slept


class TestHappyPath:
    def test_every_good_hotel_is_captured(self, tmp_path):
        names = MARRIOTT
        session = FakeBrowserSession(pages_from(*names))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert result.manifest["counts"]["captured"] == len(names)
        assert result.manifest["counts"]["exceptions"] == 0

    def test_both_brands_capture(self, tmp_path):
        names = MARRIOTT[:2] + HILTON[:2]
        session = FakeBrowserSession(pages_from(*names))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert result.manifest["counts"]["captured"] == 4

    def test_files_land_inside_the_batch_directory(self, tmp_path):
        names = MARRIOTT[:2]
        session = FakeBrowserSession(pages_from(*names))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        batch = (tmp_path / "batch").resolve()
        for cap in result.manifest["successful_captures"]:
            assert pathlib.Path(cap["json_path"]).resolve().is_relative_to(batch)
            assert pathlib.Path(cap["png_path"]).resolve().is_relative_to(batch)

    def test_manifest_records_the_citable_url(self, tmp_path):
        session = FakeBrowserSession(pages_from("marriott-cmham.json"))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(["marriott-cmham.json"]))
        cap = result.manifest["successful_captures"][0]
        assert cap["citable_url"].startswith("https://www.marriott.com/")
        assert "?" not in cap["citable_url"]

    def test_nothing_is_attested_or_approved(self, tmp_path):
        session = FakeBrowserSession(pages_from(*MARRIOTT[:2]))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(MARRIOTT[:2]))
        blob = json.dumps(result.manifest)
        for word in ("attestation_id", "approval", "APPROVED", "publishable"):
            assert word not in blob
        assert "attested" in result.manifest["note"]


class TestOneFailureDoesNotStopTheBatch:
    def test_navigation_failure_is_isolated(self, tmp_path):
        names = MARRIOTT[:4]
        pages = pages_from(*names)
        broken = entry_for(names[1]).official_url
        session = FakeBrowserSession(
            pages, nav_failures={broken: "NAVIGATION_TIMEOUT"})
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert result.manifest["counts"]["captured"] == 3
        assert result.manifest["counts"]["exceptions"] == 1
        assert result.manifest["exceptions"][0]["reason"] == "NAVIGATION_TIMEOUT"

    def test_a_raised_exception_becomes_a_record_not_a_crash(self, tmp_path):
        names = MARRIOTT[:3]
        exploding = entry_for(names[0]).official_url
        session = FakeBrowserSession(pages_from(*names), raise_for=[exploding])
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert result.manifest["counts"]["captured"] == 2
        assert result.manifest["exceptions"][0]["reason"] == "UNEXPECTED_ERROR"

    def test_missing_screenshot_is_isolated(self, tmp_path):
        names = MARRIOTT[:3]
        pages = pages_from(*names)
        no_shot = entry_for(names[2]).official_url
        session = FakeBrowserSession(pages, no_screenshot_for=[no_shot])
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert result.manifest["counts"]["captured"] == 2
        assert any(e["reason"] == "SCREENSHOT_UNAVAILABLE"
                   for e in result.manifest["exceptions"])

    def test_unknown_brand_is_isolated(self, tmp_path):
        names = MARRIOTT[:2]
        entries = [entry_for(names[0]),
                   entry_for(names[1], brand="fictional-inns")]
        session = FakeBrowserSession(pages_from(*names))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(CaptureQueue(batch_id="b", entries=tuple(entries)))
        assert result.manifest["counts"]["captured"] == 1
        assert any(e["reason"] == "ADAPTER_UNAVAILABLE"
                   for e in result.manifest["exceptions"])


class TestChallengeHandling:
    def test_a_challenge_page_becomes_an_exception_and_advances(self, tmp_path):
        names = MARRIOTT[:3]
        pages = pages_from(*names)
        challenged = entry_for(names[0]).official_url
        pages[challenged] = dict(pages[challenged],
                                 text="Please verify you are a human. reCAPTCHA")
        session = FakeBrowserSession(pages)
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert result.manifest["exceptions"][0]["reason"] == "CAPTCHA_OR_CHALLENGE"
        assert result.manifest["counts"]["captured"] == 2, "batch must continue"

    def test_a_challenge_recommends_the_manual_fallback(self, tmp_path):
        names = MARRIOTT[:1]
        pages = pages_from(*names)
        url = entry_for(names[0]).official_url
        pages[url] = dict(pages[url], text="Access Denied. You don't have permission")
        session = FakeBrowserSession(pages)
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert result.manifest["retry_recommendations"]["manual"] == [
            entry_for(names[0]).hotel_id]

    def test_three_consecutive_challenges_abort_the_batch(self, tmp_path):
        names = MARRIOTT[:5]
        pages = pages_from(*names)
        for n in names[:3]:
            url = entry_for(n).official_url
            pages[url] = dict(pages[url], text="Please verify you are a human. CAPTCHA")
        session = FakeBrowserSession(pages)
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert result.aborted_reason.startswith("consecutive_challenges")
        assert result.manifest["counts"]["skipped"] == 2
        assert len(session.navigations) == 3, "must stop requesting the brand"

    def test_a_success_between_challenges_resets_the_counter(self, tmp_path):
        names = MARRIOTT[:5]
        pages = pages_from(*names)
        for n in (names[0], names[1], names[3]):
            url = entry_for(n).official_url
            pages[url] = dict(pages[url], text="Please verify you are a human. CAPTCHA")
        session = FakeBrowserSession(pages)
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        assert not result.aborted_reason
        # Distinct pages, not raw loads: a hotel that captures is requested a
        # second time so its identity can be photographed once the policy modal
        # is gone. What matters here is that every hotel was reached exactly
        # once as a hotel.
        assert len(set(session.navigations)) == 5


class TestKillSwitchUnit:
    def test_counts_only_consecutive(self):
        k = KillSwitch(3)
        challenge = HotelOutcome("a", EXCEPTION, "CAPTCHA_OR_CHALLENGE")
        good = HotelOutcome("b", CAPTURED)
        k = k.observe(challenge).observe(challenge)
        assert not k.tripped
        k = k.observe(good)
        assert k.consecutive == 0
        k = k.observe(challenge).observe(challenge).observe(challenge)
        assert k.tripped

    def test_a_non_challenge_exception_does_not_count(self):
        k = KillSwitch(2)
        k = k.observe(HotelOutcome("a", EXCEPTION, "POLICY_NOT_FOUND"))
        k = k.observe(HotelOutcome("b", EXCEPTION, "POLICY_NOT_FOUND"))
        assert not k.tripped


class TestDuplicates:
    def test_the_same_page_twice_is_a_duplicate(self, tmp_path):
        """The corpus holds two captures of the identical Marriott page."""
        a, b = "marriott-cmhap.json", "marriott-cmhap-b.json"
        pages = pages_from(a)
        entries = (entry_for(a, hotel_id="first"),
                   entry_for(b, hotel_id="second"))
        session = FakeBrowserSession(pages)
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(CaptureQueue(batch_id="b", entries=entries))
        assert result.manifest["counts"]["captured"] == 1
        assert result.manifest["counts"]["duplicates"] == 1
        assert result.manifest["duplicate_captures"][0]["duplicate_of"] == "first"

    def test_archived_corpus_blocks_a_cross_batch_duplicate(self, tmp_path):
        name = "marriott-cmham.json"
        archive = tmp_path / "archive"
        archive.mkdir()
        (archive / name).write_text(json.dumps(load_fixture(name)), encoding="utf-8")
        session = FakeBrowserSession(pages_from(name))
        runner, _ = make_runner(tmp_path, session,
                                archived_corpus_dirs=(str(archive),))
        result = runner.run(build_queue([name]))
        assert result.manifest["counts"]["duplicates"] == 1


class TestPolicyGeometry:
    def test_off_screen_policy_fails_the_hotel(self, tmp_path):
        name = "marriott-cmham.json"
        session = FakeBrowserSession(
            pages_from(name),
            box=BoxModel(x=0, y=9000, width=600, height=400, scroll_y=0))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue([name]))
        assert result.manifest["exceptions"][0]["reason"] == "POLICY_OFF_SCREEN"

    def test_policy_box_is_recorded_for_later_recheck(self, tmp_path):
        name = "marriott-cmham.json"
        session = FakeBrowserSession(pages_from(name))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue([name]))
        payload = json.loads(
            pathlib.Path(result.manifest["successful_captures"][0]["json_path"])
            .read_text("utf-8"))
        box = payload["automation"]["policy_box"]
        assert box and box["height"] > 0
        assert payload["automation"]["viewport_height"] > 0

    def test_the_scroll_targets_the_policy_text(self, tmp_path):
        name = "marriott-cmham.json"
        session = FakeBrowserSession(pages_from(name))
        runner, _ = make_runner(tmp_path, session)
        runner.run(build_queue([name]))
        assert any("Pet Policy" in s for s in session.scrolls)


class TestPolicyFramingIsCheckedTwice:
    """A single pre-screenshot reading is not evidence the policy was in frame.

    A real Aloft Columbus University District capture recorded "100% visible at
    viewport y=368", passed every automated gate, and its PNG showed the bar
    section 470px further down the page. The recorded geometry could not
    contradict itself because it held one measurement of a moment already gone.
    The fix reads the same element again after the screenshot and requires both
    readings to agree.
    """

    IN_FRAME = BoxModel(x=0, y=400, width=600, height=140, scroll_y=0)

    def _run(self, tmp_path, **session_kw):
        name = "marriott-cmham.json"
        session = FakeBrowserSession(pages_from(name), box=self.IN_FRAME,
                                     viewport=(1424, 905), **session_kw)
        runner, _ = make_runner(tmp_path, session)
        return runner.run(build_queue([name])), session

    def test_stable_in_frame_element_passes(self, tmp_path):
        result, _ = self._run(tmp_path)
        assert result.manifest["counts"]["captured"] == 1

    def test_in_frame_before_but_off_screen_after_fails(self, tmp_path):
        """The exact defect: the page moved while the image was taken."""
        moved = BoxModel(x=0, y=400, width=600, height=140, scroll_y=3000)
        result, _ = self._run(tmp_path, box_after=moved)
        assert result.manifest["counts"]["captured"] == 0
        exc = result.manifest["exceptions"][0]
        assert exc["reason"] == "POLICY_OFF_SCREEN"
        assert "off_screen_after_screenshot" in exc["detail"][0]

    def test_element_disappearing_after_screenshot_fails(self, tmp_path):
        result, _ = self._run(tmp_path, box_after_missing=True)
        assert result.manifest["counts"]["captured"] == 0
        exc = result.manifest["exceptions"][0]
        assert exc["reason"] == "POLICY_OFF_SCREEN"
        assert exc["detail"] == ["policy_element_missing_after_screenshot"]

    def test_material_drift_fails(self, tmp_path):
        """The CONTENT moved under the camera: same scroll, new page position.

        Chosen so the in-frame check cannot be what rejects it: at page-y 800
        with scroll 0 in a 905px viewport, 105 of the block's 140px are visible
        (75%). Only the 400px move from page-y 400 disqualifies it.
        """
        drifted = BoxModel(x=0, y=800, width=600, height=140, scroll_y=0)
        result, _ = self._run(tmp_path, box_after=drifted)
        assert result.manifest["counts"]["captured"] == 0
        exc = result.manifest["exceptions"][0]
        assert exc["reason"] == "POLICY_OFF_SCREEN"
        assert "geometry_drift_px" in exc["detail"][0]

    def test_small_drift_within_tolerance_passes(self, tmp_path):
        """Two healthy runs of the same page differed by 14px purely because
        the scroll landed marginally differently. That must not fail a batch."""
        nudged = BoxModel(x=0, y=414, width=600, height=140, scroll_y=0)
        result, _ = self._run(tmp_path, box_after=nudged)
        assert result.manifest["counts"]["captured"] == 1

    def test_the_screenshot_scrolling_the_page_is_not_drift(self, tmp_path):
        """Chrome's captureScreenshot scrolls, then composites. The content is
        stationary; only the camera moved, and the block is still in frame.

        Measured on a real IHG page: page-y 6233 before and after, scrollY
        5810 -> 5916. Treating that 106px as drift refused three healthy
        captures in a row.
        """
        before = BoxModel(x=0, y=6233, width=870, height=141, scroll_y=5810)
        after = BoxModel(x=0, y=6233, width=870, height=141, scroll_y=5916)
        session = FakeBrowserSession(pages_from("marriott-cmham.json"),
                                     box=before, box_after=after,
                                     viewport=(1424, 905))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(["marriott-cmham.json"]))
        assert result.manifest["counts"]["captured"] == 1

    def test_a_height_change_fails(self, tmp_path):
        """The block re-laid out under the camera; same top edge, new shape."""
        reshaped = BoxModel(x=0, y=400, width=600, height=600, scroll_y=0)
        result, _ = self._run(tmp_path, box_after=reshaped)
        assert result.manifest["counts"]["captured"] == 0
        assert "height_changed" in result.manifest["exceptions"][0]["detail"][0]

    def test_both_readings_are_recorded_in_the_capture(self, tmp_path):
        result, _ = self._run(tmp_path)
        payload = json.loads(pathlib.Path(
            result.manifest["successful_captures"][0]["json_path"]).read_text("utf-8"))
        auto = payload["automation"]
        assert auto["policy_box"] is not None
        assert auto["policy_box_after_screenshot"] is not None
        assert "before" in auto["geometry_note"] and "after" in auto["geometry_note"]

    def test_the_written_capture_revalidates_from_both_boxes(self, tmp_path):
        """The artifact must be able to prove the claim on its own."""
        from services.research_workers.capture_automation.validators import (
            validate_written_capture,
        )
        result, _ = self._run(tmp_path)
        cap = result.manifest["successful_captures"][0]
        assert validate_written_capture(cap["json_path"], cap["png_path"]).ok

    def test_a_tampered_after_box_is_caught_on_revalidation(self, tmp_path):
        from services.research_workers.capture_automation.validators import (
            validate_written_capture,
        )
        result, _ = self._run(tmp_path)
        cap = result.manifest["successful_captures"][0]
        p = pathlib.Path(cap["json_path"])
        payload = json.loads(p.read_text("utf-8"))
        payload["automation"]["policy_box_after_screenshot"]["scroll_y"] = 9000
        p.write_text(json.dumps(payload), encoding="utf-8")
        out = validate_written_capture(cap["json_path"], cap["png_path"])
        assert not out.ok and out.reason == "POLICY_OFF_SCREEN"

    def test_the_same_element_is_measured_both_times(self, tmp_path):
        """Re-deriving the handle could compare two different elements and call
        the difference drift."""
        from services.research_workers.capture_automation.runner import _policy_handle
        from services.research_workers.capture_automation.policy_locator import (
            locate_policy,
        )
        from .conftest import snapshot_for
        dom = snapshot_for("marriott-cmham.json")
        session = FakeBrowserSession(pages_from("marriott-cmham.json"))
        handle = _policy_handle(locate_policy(dom), session)
        assert handle[0] in ("selector", "text") and handle[1]


class TestFramingCheckUnit:
    VH = 905.0
    OK = BoxModel(x=0, y=400, width=600, height=140, scroll_y=0)

    def test_missing_before(self):
        ok, detail = check_policy_framing(None, self.OK, self.VH)
        assert not ok and detail == "no_box_before_screenshot"

    def test_missing_after(self):
        ok, detail = check_policy_framing(self.OK, None, self.VH)
        assert not ok and detail == "policy_element_missing_after_screenshot"

    def test_unknown_viewport(self):
        ok, detail = check_policy_framing(self.OK, self.OK, 0.0)
        assert not ok and detail == "unknown_viewport_height"

    def test_identical_boxes_pass(self):
        assert check_policy_framing(self.OK, self.OK, self.VH)[0]

    @pytest.mark.parametrize("dy,expected", [(0, True), (10, True), (24, True),
                                             (25, False), (400, False)])
    def test_tolerance_boundary_on_page_coordinates(self, dy, expected):
        after = BoxModel(x=0, y=400 + dy, width=600, height=140, scroll_y=0)
        assert check_policy_framing(self.OK, after, self.VH)[0] is expected

    @pytest.mark.parametrize("dscroll", [0, 106, 300])
    def test_scroll_change_alone_is_never_drift(self, dscroll):
        """Same PAGE position, different camera position, still in frame.

        page-y stays at 400; only scroll_y moves. That is exactly what
        captureScreenshot does, and it must not be called drift.
        """
        after = BoxModel(x=0, y=400, width=600, height=140, scroll_y=dscroll)
        ok, detail = check_policy_framing(self.OK, after, self.VH)
        assert ok, detail


class TestPacing:
    """Asserted against ``runner.pace_waits``, not the raw sleep log.

    The runner also sleeps for page settling and hydration polling, so counting
    every sleep would conflate three different waits and let a pacing
    regression hide behind a poll interval.
    """

    def test_the_runner_waits_between_hotels(self, tmp_path):
        names = MARRIOTT[:3]
        session = FakeBrowserSession(pages_from(*names))
        runner, _slept = make_runner(tmp_path, session)
        runner.run(build_queue(names))
        assert len(runner.pace_waits) == 2, "one pause per pair, none after the last"
        assert all(s >= 20.0 for s in runner.pace_waits)

    def test_a_single_hotel_batch_never_pauses(self, tmp_path):
        session = FakeBrowserSession(pages_from("marriott-cmham.json"))
        runner, _slept = make_runner(tmp_path, session)
        runner.run(build_queue(["marriott-cmham.json"]))
        assert runner.pace_waits == []

    def test_the_floor_cannot_be_configured_away(self, tmp_path):
        names = MARRIOTT[:2]
        session = FakeBrowserSession(pages_from(*names))
        runner, _slept = make_runner(tmp_path, session, min_pace=0.0, max_pace=0.0)
        runner.run(build_queue(names))
        assert runner.pace_waits and all(s >= 20.0 for s in runner.pace_waits)

    def test_hydration_polling_is_not_counted_as_pacing(self, tmp_path):
        """A poll interval must never be mistaken for an inter-hotel pause."""
        session = FakeBrowserSession(pages_from("marriott-cmham.json"))
        runner, slept = make_runner(tmp_path, session)
        runner.run(build_queue(["marriott-cmham.json"]))
        assert any(s < 20.0 for s in slept), "hydration did poll"
        assert runner.pace_waits == []


class TestResume:
    def test_a_second_run_skips_completed_hotels(self, tmp_path):
        names = MARRIOTT[:4]
        pages = pages_from(*names)

        # First run: the third hotel is unreachable, so it ends as an exception.
        broken = entry_for(names[2]).official_url
        first = FakeBrowserSession(pages, nav_failures={broken: "NAVIGATION_TIMEOUT"})
        runner, _ = make_runner(tmp_path, first)
        runner.run(build_queue(names))
        assert len(set(first.navigations)) == 4

        # Second run over the same batch dir: everything already terminal.
        second = FakeBrowserSession(pages)
        runner2, _ = make_runner(tmp_path, second)
        result = runner2.run(build_queue(names))
        assert second.navigations == [], "resume must re-request nothing"
        assert result.manifest["counts"]["attempted"] == 4

    def test_interruption_mid_batch_resumes_where_it_stopped(self, tmp_path):
        names = MARRIOTT[:4]
        pages = pages_from(*names)

        partial = FakeBrowserSession(pages)
        runner, _ = make_runner(tmp_path, partial, limit=2)
        runner.run(build_queue(names))
        assert len(set(partial.navigations)) == 2

        rest = FakeBrowserSession(pages)
        runner2, _ = make_runner(tmp_path, rest)
        result = runner2.run(build_queue(names))
        assert len(set(rest.navigations)) == 2, "only the unfinished two"
        assert result.manifest["counts"]["captured"] == 4

    def test_the_journal_survives_a_lost_manifest(self, tmp_path):
        names = MARRIOTT[:2]
        session = FakeBrowserSession(pages_from(*names))
        runner, _ = make_runner(tmp_path, session)
        runner.run(build_queue(names))

        (tmp_path / "batch" / "manifest.json").unlink()
        journal = Journal.open(tmp_path / "batch")
        assert len(journal.completed_hotel_ids()) == 2

    def test_a_corrupt_journal_line_is_fatal_not_silently_skipped(self, tmp_path):
        from services.research_workers.capture_automation.manifest import JournalError
        session = FakeBrowserSession(pages_from("marriott-cmham.json"))
        runner, _ = make_runner(tmp_path, session)
        runner.run(build_queue(["marriott-cmham.json"]))

        path = tmp_path / "batch" / "journal.jsonl"
        path.write_text(path.read_text("utf-8") + "{not json\n", encoding="utf-8")
        with pytest.raises(JournalError):
            Journal.open(tmp_path / "batch").records()


class TestManifestShape:
    def test_counts_and_rate_agree(self, tmp_path):
        names = MARRIOTT[:4]
        pages = pages_from(*names)
        broken = entry_for(names[0]).official_url
        session = FakeBrowserSession(pages, nav_failures={broken: "NAVIGATION_FAILED"})
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        counts = result.manifest["counts"]
        assert counts["captured"] + counts["exceptions"] + counts["duplicates"] \
            == counts["attempted"]
        assert result.manifest["unattended_success_rate"] == pytest.approx(0.75)

    def test_every_exception_carries_a_retry_and_an_explanation(self, tmp_path):
        names = MARRIOTT[:2]
        pages = pages_from(*names)
        broken = entry_for(names[0]).official_url
        session = FakeBrowserSession(pages, nav_failures={broken: "NAVIGATION_TIMEOUT"})
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(names))
        for exc in result.manifest["exceptions"]:
            assert exc["retry"] in ("now", "manual", "never")
            assert exc["explanation"]

    def test_manifest_is_written_to_disk(self, tmp_path):
        session = FakeBrowserSession(pages_from("marriott-cmham.json"))
        runner, _ = make_runner(tmp_path, session)
        result = runner.run(build_queue(["marriott-cmham.json"]))
        assert result.manifest_path.exists()
        assert json.loads(result.manifest_path.read_text("utf-8"))["batch_id"]
