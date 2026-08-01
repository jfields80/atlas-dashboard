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
        assert len(session.navigations) == 5


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


class TestPacing:
    def test_the_runner_waits_between_hotels(self, tmp_path):
        names = MARRIOTT[:3]
        session = FakeBrowserSession(pages_from(*names))
        runner, slept = make_runner(tmp_path, session)
        runner.run(build_queue(names))
        assert len(slept) == 2, "one pause between each pair, none after the last"
        assert all(s >= 20.0 for s in slept)

    def test_a_single_hotel_batch_never_pauses(self, tmp_path):
        session = FakeBrowserSession(pages_from("marriott-cmham.json"))
        runner, slept = make_runner(tmp_path, session)
        runner.run(build_queue(["marriott-cmham.json"]))
        assert slept == []

    def test_the_floor_cannot_be_configured_away(self, tmp_path):
        names = MARRIOTT[:2]
        session = FakeBrowserSession(pages_from(*names))
        runner, slept = make_runner(tmp_path, session, min_pace=0.0, max_pace=0.0)
        runner.run(build_queue(names))
        assert slept and all(s >= 20.0 for s in slept)


class TestResume:
    def test_a_second_run_skips_completed_hotels(self, tmp_path):
        names = MARRIOTT[:4]
        pages = pages_from(*names)

        # First run: the third hotel is unreachable, so it ends as an exception.
        broken = entry_for(names[2]).official_url
        first = FakeBrowserSession(pages, nav_failures={broken: "NAVIGATION_TIMEOUT"})
        runner, _ = make_runner(tmp_path, first)
        runner.run(build_queue(names))
        assert len(first.navigations) == 4

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
        assert len(partial.navigations) == 2

        rest = FakeBrowserSession(pages)
        runner2, _ = make_runner(tmp_path, rest)
        result = runner2.run(build_queue(names))
        assert len(rest.navigations) == 2, "only the unfinished two"
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
