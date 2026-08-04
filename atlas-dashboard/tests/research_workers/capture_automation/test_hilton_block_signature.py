"""A refusal page that carries words is still a refusal.

Eleven Hilton candidates in one batch were reported IDENTITY_UNVERIFIABLE with
``hydration_timeout``. Every one was titled exactly "Hilton Page Reference
Code", every one a static 1206px document with no hotel content, and the same
URL captured cleanly one attempt earlier in the same run. They were not slow
pages and not anonymous pages -- they were refusals, waited out for the full
20-second budget and then filed as if the property page had merely lagged.

Two detectors both missed it, for opposite reasons:

  * ``looks_like_challenge_shell`` requires a TEXTLESS shell, and this page has
    words;
  * ``_page_block_reason`` reads the body, and this page states what it is in
    its TITLE and says nothing incriminating below it.

So the title is now read too, and the exact phrase is a denial marker. What must
not change: the hydration budget (a genuinely slow page still gets its full 20
seconds), the identity rules, and the consecutive-challenge kill switch -- which
this change feeds rather than bypasses, because a brand that starts refusing us
is precisely what that counter exists to notice.
"""

from __future__ import annotations

import json

import pytest

from services.research_workers.capture_automation.contracts import DomSnapshot
from services.research_workers.capture_automation.hydration import (
    ReadinessResult, wait_for_identity,
)
from services.research_workers.capture_automation.queue import CaptureQueue
from services.research_workers.capture_automation.reasons import (
    CHALLENGE_REASONS, retry_for,
)
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.capture_automation.state_machine import EXCEPTION
from services.research_workers.operator_capture import _page_block_reason

from .conftest import FakeBrowserSession, entry_for, load_fixture, pages_from

GOOD = "marriott-cmham.json"
HILTON_TITLE = "Hilton Page Reference Code"


class Clock:
    def __init__(self):
        self.t = 1_781_000_000.0

    def __call__(self):
        self.t += 0.5
        return self.t


def run_batch(tmp_path, session, fixture=GOOD):
    runner = CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "batch"),
                           clock=Clock(), sleep=lambda *_: None,
                           jitter=lambda a, b: a)
    return runner.run(CaptureQueue(batch_id="block", entries=(entry_for(fixture),)))


def journal(tmp_path):
    p = tmp_path / "batch" / "journal.jsonl"
    return [json.loads(x) for x in p.read_text("utf-8").splitlines() if x.strip()]


# --------------------------------------------------------------------------- #
# 1-4. Detection.
# --------------------------------------------------------------------------- #

class TestSignatureDetection:
    def test_1_hilton_reference_code_is_access_denied(self):
        assert _page_block_reason(HILTON_TITLE) == "access_denied_page"

    def test_1b_it_is_matched_case_insensitively_and_within_a_sentence(self):
        assert _page_block_reason("  HILTON PAGE REFERENCE CODE  ") == "access_denied_page"
        assert _page_block_reason(
            "Hilton Page Reference Code: 0.a1b2c3") == "access_denied_page"

    def test_2_an_ordinary_hilton_page_is_not_blocked(self):
        """The real corpus, not a hand-written string."""
        for name in ("hilton-cmhaphx.json", "hilton-cmhcagi.json",
                     "hilton-cmhcsht.json", "hilton-cmhncht.json"):
            payload = load_fixture(name)
            assert _page_block_reason(payload.get("text") or "") == "", name
            assert _page_block_reason(payload.get("title") or "") == "", name

    def test_3_marriott_access_denied_is_unchanged(self):
        assert _page_block_reason("Access Denied") == "access_denied_page"
        assert _page_block_reason("You don't have permission") == "access_denied_page"
        assert _page_block_reason("403 Forbidden") == "access_denied_page"

    def test_3b_other_block_classes_are_unchanged(self):
        assert _page_block_reason("Please enable JavaScript and cookies") \
            == "captcha_or_challenge_page"
        assert _page_block_reason("please sign in") == "login_required_page"
        assert _page_block_reason("a perfectly ordinary page") == ""

    def test_4_a_text_bearing_block_page_is_detected(self):
        """The whole point: this page has words, so the empty-shell check --
        which requires a textless shell -- can never see it."""
        from services.research_workers.capture_automation.hydration import (
            looks_like_challenge_shell,
        )

        dom = DomSnapshot(final_url="https://www.hilton.com/en/hotels/cmhlahw-x/",
                          title=HILTON_TITLE,
                          text="Hilton Page Reference Code\nReference: 0.a1b2c3",
                          html="<html><body><p>Hilton Page Reference Code</p></body></html>")
        assert looks_like_challenge_shell(dom) == "", "precondition: not an empty shell"
        assert _page_block_reason(dom.text) == "access_denied_page"

    def test_4b_a_title_only_refusal_is_detected(self):
        """Detected even when the body says nothing incriminating at all."""
        blocked = []

        class TitleOnly(FakeBrowserSession):
            def snapshot(self):
                return DomSnapshot(final_url="https://www.hilton.com/en/hotels/x/",
                                   title=HILTON_TITLE, text="Reference: 0.a1b2c3",
                                   html="<html></html>")

        r = wait_for_identity(TitleOnly({}), entry_for(GOOD), timeout=5.0,
                              interval=0.1, clock=Clock(), sleep=lambda *_: None)
        assert r.blocked_reason == "access_denied_page"
        assert not r.ready and not r.timed_out, "it stops at once, it does not wait"


# --------------------------------------------------------------------------- #
# 5. The hydration budget is untouched.
# --------------------------------------------------------------------------- #

class TestHydrationBudgetIsUnchanged:
    def test_5_a_genuine_slow_page_still_gets_its_full_budget(self):
        """No block markers anywhere: the wait runs to the timeout as before."""
        class Anonymous(FakeBrowserSession):
            def snapshot(self):
                return DomSnapshot(final_url="https://www.example.com/x",
                                   title="Loading", text="please wait", html="<html/>")

        r = wait_for_identity(Anonymous({}), entry_for(GOOD), timeout=3.0,
                              interval=1.0, clock=Clock(), sleep=lambda *_: None)
        assert r.timed_out and not r.blocked_reason
        assert r.checks >= 2, "it actually polled rather than bailing out"

    def test_5b_a_real_page_still_confirms_immediately(self):
        payload = load_fixture("hilton-cmhaphx.json")

        class Real(FakeBrowserSession):
            def snapshot(self):
                return DomSnapshot.from_capture_payload(payload)

        r = wait_for_identity(Real({}), entry_for("hilton-cmhaphx.json"), timeout=20.0,
                              interval=1.0, clock=Clock(), sleep=lambda *_: None)
        assert r.ready and not r.blocked_reason


# --------------------------------------------------------------------------- #
# 6-7. Kill switch and retry disposition.
# --------------------------------------------------------------------------- #

def _blocked_pages():
    pages = dict(pages_from(GOOD))
    for url in list(pages):
        p = dict(pages[url])
        p["title"] = HILTON_TITLE
        p["text"] = "Reference: 0.a1b2c3"
        pages[url] = p
    return pages


class TestKillSwitchAndDisposition:
    def test_6_the_outcome_reaches_the_consecutive_block_counter(self, tmp_path):
        result = run_batch(tmp_path, FakeBrowserSession(_blocked_pages()))
        rec = journal(tmp_path)[0]
        assert rec["state"] == EXCEPTION
        assert rec["reason"] == "ACCESS_DENIED"
        assert rec["detail"] == ["access_denied_page"]
        # The counter keys off CHALLENGE_REASONS; membership is what makes a
        # run of these halt the batch.
        assert rec["reason"] in CHALLENGE_REASONS

    def test_6b_a_run_of_them_aborts_the_batch(self, tmp_path):
        """The property that matters operationally: a brand that starts
        refusing us stops the batch instead of being ground through."""
        from services.research_workers.capture_automation.doctrine import (
            CONSECUTIVE_CHALLENGE_LIMIT,
        )

        entries = tuple(entry_for(GOOD).__class__(
            **{**entry_for(GOOD).to_dict(), "hotel_id": "h%d" % i,
               "alternate_urls": (), "required_fields": (), "priority_reasons": (),
               "discovery_provenance_refs": ()})
            for i in range(CONSECUTIVE_CHALLENGE_LIMIT + 2))
        runner = CaptureRunner(FakeBrowserSession(_blocked_pages()),
                               RunnerConfig(batch_dir=tmp_path / "batch"),
                               clock=Clock(), sleep=lambda *_: None,
                               jitter=lambda a, b: a)
        result = runner.run(CaptureQueue(batch_id="killswitch", entries=entries))
        assert result.aborted_reason, "the batch must stop, not continue"
        assert len(result.outcomes) <= CONSECUTIVE_CHALLENGE_LIMIT + 1

    def test_7_retry_disposition_is_the_existing_access_denied_one(self, tmp_path):
        run_batch(tmp_path, FakeBrowserSession(_blocked_pages()))
        rec = journal(tmp_path)[0]
        assert rec["retry"] == retry_for("ACCESS_DENIED")
        assert rec["retry"] != "now", "a refusal is never retried on the spot"

    def test_7b_it_is_no_longer_reported_as_a_hydration_timeout(self, tmp_path):
        """The misdiagnosis this change exists to end."""
        run_batch(tmp_path, FakeBrowserSession(_blocked_pages()))
        rec = journal(tmp_path)[0]
        assert rec["reason"] != "IDENTITY_UNVERIFIABLE"
        assert "hydration_timeout" not in rec["detail"]


class TestNoEvasion:
    def test_the_module_gains_no_bypass_path(self):
        """Detecting a refusal must never become working around one."""
        import inspect

        from services.research_workers.capture_automation import hydration

        src = inspect.getsource(hydration)
        for banned in ("user-agent", "user_agent", "proxy", "rotate", "stealth",
                       "undetected", "solve_captcha", "bypass"):
            assert banned not in src.lower(), banned
