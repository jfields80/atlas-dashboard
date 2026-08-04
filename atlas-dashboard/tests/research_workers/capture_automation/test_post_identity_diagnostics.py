"""Every terminal record reached after identity succeeded says so.

The diagnostic FILES already carried the identity outcome. The journal RECORD
did not, so a POLICY_OFF_SCREEN or POLICY_NOT_FOUND line could not prove
identity had passed -- and the 10-candidate pilot plan names exactly that as a
stop condition: "the identity outcome is missing from a journal record --
un-diagnosable is a stop condition." The pilot's two AC Hotel exceptions hit it.

At ten hotels a reviewer can open the diagnostics by hand. At eighty-five that
is the difference between a readable batch and a re-run.

What this must NOT do, and what these tests hold: it may not change an outcome,
a reason, a retry disposition, or the two records that already carried the
lines. It is additive annotation on records that had none.
"""

from __future__ import annotations

import json
import pathlib
from typing import Dict, List, Optional

import pytest

from services.research_workers.capture_automation import identity_keys as IK
from services.research_workers.capture_automation.queue import CaptureQueue
from services.research_workers.capture_automation.reasons import retry_for
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.capture_automation.state_machine import (
    CAPTURED, EXCEPTION,
)

from .conftest import FakeBrowserSession, entry_for, load_fixture

GOOD = "marriott-cmham.json"

IDENTITY_LINES = ("identity_outcome:", "independent_keys:", "authoritative_key:",
                  "authoritative_basis:", "agreeing_keys:")


class FrozenClock:
    def __init__(self):
        self.t = 1_781_000_000.0

    def __call__(self):
        self.t += 0.5
        return self.t


def run(tmp_path, session, entry=None) -> List:
    runner = CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "batch"),
                           clock=FrozenClock(), sleep=lambda *_: None,
                           jitter=lambda a, b: a)
    queue = CaptureQueue(batch_id="postid", entries=(entry or entry_for(GOOD),))
    return list(runner.run(queue).outcomes)


def journal(tmp_path) -> List[dict]:
    path = tmp_path / "batch" / "journal.jsonl"
    return [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]


def identity_outcome_of(detail) -> Optional[str]:
    for d in detail:
        if d.startswith("identity_outcome:"):
            return d.split(":", 1)[1]
    return None


# --------------------------------------------------------------------------- #
# Sessions that fail at a specific stage, all AFTER identity confirms.
# --------------------------------------------------------------------------- #

class OffScreenSession(FakeBrowserSession):
    """The policy is located, then measured outside the capture frame.

    This is the AC Hotel shape: off_screen_before_screenshot:0.00.
    """

    def box_model(self, selector: str):
        return None

    def box_for_text(self, text: str):
        from services.research_workers.capture_automation.contracts import BoxModel
        # Far below a 905px viewport, and it stays there.
        return BoxModel(x=0.0, y=9000.0, width=700.0, height=60.0,
                        scroll_x=0.0, scroll_y=0.0)

    def viewport(self):
        return (1424, 905)

    def evaluate(self, expression: str, timeout: float = 60.0):
        return 0 if "scrollTo" in expression else None


class NoPolicySession(FakeBrowserSession):
    """Identity is intact; the pet-policy block is gone from the rendered text."""

    def __init__(self):
        payload = json.loads(json.dumps(load_fixture(GOOD)))
        text = payload["text"]
        for marker in ("Pet Policy", "Pets Welcome", "Non-Refundable Pet Fee",
                       "Maximum Number of Pets"):
            text = text.replace(marker, "Amenity")
        payload["text"] = text
        super().__init__({payload["final_url"]: payload})


class ScreenshotFailureSession(FakeBrowserSession):
    """Identity confirms, the policy is framed, the camera fails."""

    def screenshot_png(self, *args, **kwargs):
        raise RuntimeError("screenshot transport failed")


# --------------------------------------------------------------------------- #
# The six required cases.
# --------------------------------------------------------------------------- #

class TestPostIdentityRecordsCarryTheirIdentity:
    def test_1_policy_off_screen_carries_outcome_and_evidence(self, tmp_path):
        from .conftest import pages_from

        outcomes = run(tmp_path, OffScreenSession(pages_from(GOOD)))
        rec = journal(tmp_path)[0]
        assert rec["state"] == EXCEPTION
        assert rec["reason"] == "POLICY_OFF_SCREEN"
        assert identity_outcome_of(rec["detail"]) == IK.IDENTITY_CONFIRMED
        # Evidence, not merely the verdict.
        for line in IDENTITY_LINES:
            assert any(d.startswith(line) for d in rec["detail"]), line
        assert not any(d.startswith("independent_keys:none") for d in rec["detail"])
        assert outcomes[0].state == EXCEPTION

    def test_2_policy_not_found_carries_outcome(self, tmp_path):
        run(tmp_path, NoPolicySession())
        rec = journal(tmp_path)[0]
        assert rec["state"] == EXCEPTION
        assert rec["reason"] in ("POLICY_NOT_FOUND", "POLICY_ABSENT_CONFIRMED")
        assert identity_outcome_of(rec["detail"]) == IK.IDENTITY_CONFIRMED

    def test_3_screenshot_failure_carries_outcome(self, tmp_path):
        from .conftest import pages_from

        run(tmp_path, ScreenshotFailureSession(pages_from(GOOD)))
        rec = journal(tmp_path)[0]
        assert rec["state"] == EXCEPTION
        assert identity_outcome_of(rec["detail"]) == IK.IDENTITY_CONFIRMED

    def test_4_identity_stage_failures_are_unchanged(self, tmp_path):
        """A page that fails AT the gate already carried these lines. It must
        keep exactly one copy, in the order it always had."""
        from services.research_workers.capture_automation.contracts import DomSnapshot

        payload = json.loads(json.dumps(load_fixture(GOOD)))
        payload["jsonld"] = [{"@type": "Hotel", "name": "Columbus Airport Marriott"}]
        payload["html"] = "<html><head><title>x</title></head></html>"
        payload["text"] = "Columbus Airport Marriott in Columbus. Welcome."
        run(tmp_path, FakeBrowserSession({payload["final_url"]: payload}))
        rec = journal(tmp_path)[0]
        assert rec["state"] == EXCEPTION
        outcomes = [d for d in rec["detail"] if d.startswith("identity_outcome:")]
        assert len(outcomes) == 1, "no duplicate annotation"
        assert outcomes[0] != "identity_outcome:%s" % IK.IDENTITY_CONFIRMED

    def test_5_captured_records_are_unchanged(self, tmp_path):
        from .conftest import pages_from

        run(tmp_path, FakeBrowserSession(pages_from(GOOD)))
        rec = journal(tmp_path)[0]
        assert rec["state"] == CAPTURED
        outcomes = [d for d in rec["detail"] if d.startswith("identity_outcome:")]
        assert len(outcomes) == 1, "the CAPTURED path already carried it; not doubled"
        assert outcomes[0] == "identity_outcome:%s" % IK.IDENTITY_CONFIRMED
        assert rec["artifacts"]["identity"]["outcome"] == IK.IDENTITY_CONFIRMED

    def test_6_retry_dispositions_are_unchanged(self, tmp_path):
        """Annotation may not move a hotel between retry classes."""
        from .conftest import pages_from

        cases = [
            (OffScreenSession(pages_from(GOOD)), "POLICY_OFF_SCREEN"),
            (NoPolicySession(), None),
            (FakeBrowserSession(pages_from(GOOD)), None),
        ]
        for i, (session, expected_reason) in enumerate(cases):
            d = tmp_path / ("c%d" % i)
            runner = CaptureRunner(session, RunnerConfig(batch_dir=d / "batch"),
                                   clock=FrozenClock(), sleep=lambda *_: None,
                                   jitter=lambda a, b: a)
            out = list(runner.run(CaptureQueue(batch_id="r%d" % i,
                                               entries=(entry_for(GOOD),))).outcomes)[0]
            if expected_reason:
                assert out.reason == expected_reason
            # The disposition is derived from the reason alone, and the reason
            # is untouched by annotation.
            assert out.retry == ("" if out.state == CAPTURED else retry_for(out.reason))


class TestAnnotationIsStrictlyAdditive:
    def test_pre_identity_failures_are_not_annotated(self, tmp_path):
        """Nothing true can be said about identity before the gate runs."""
        from .conftest import pages_from

        entry = entry_for(GOOD)
        entry = entry.__class__(**{**entry.to_dict(), "brand": "marriott",
                                   "alternate_urls": (), "required_fields": (),
                                   "priority_reasons": (),
                                   "discovery_provenance_refs": ()})

        class DeadNav(FakeBrowserSession):
            def navigate(self, url):
                from services.research_workers.browser_control.session import (
                    NavigationResult,
                )
                return NavigationResult(ok=False, reason="NAVIGATION_FAILED",
                                        final_url=url, detail="boom")

        run(tmp_path, DeadNav(pages_from(GOOD)), entry)
        rec = journal(tmp_path)[0]
        assert rec["state"] == EXCEPTION
        assert identity_outcome_of(rec["detail"]) is None

    def test_identity_lines_are_reused_never_recomputed(self):
        """The annotation reads the stored tuple; it never calls the gate."""
        import inspect

        from services.research_workers.capture_automation import runner as R

        src = inspect.getsource(R.CaptureRunner.capture_one)
        head = src.split("def done(")[1].split("return HotelOutcome")[0]
        assert 'diag["identity_detail"]' in head
        assert "classify_identity" not in head
        assert "_identity_detail(" not in head
