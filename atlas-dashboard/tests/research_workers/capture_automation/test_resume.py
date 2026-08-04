"""Resume behaviour: what a re-run may skip, and what it must not.

Two defects motivated these tests, both found by tracing the code rather than
by any test failing:

  1. ``--resume`` was declared on the CLI parser and never passed into
     ``RunnerConfig`` -- a silent no-op flag.
  2. Far worse, the runner resumed UNCONDITIONALLY off
     ``Journal.completed_hotel_ids()``, which counts EXCEPTION as terminal. A
     second run over the same batch directory therefore skipped every
     IDENTITY_FAILED, IDENTITY_UNVERIFIABLE, POLICY_NOT_FOUND and
     POLICY_OFF_SCREEN -- abandoning exactly the work a resume exists to
     finish, and reporting success while doing it.

The rule these tests pin down: **only a complete, verified capture may be
skipped.** Everything else is re-attempted, and anything unverifiable fails
closed into being re-attempted.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from services.research_workers.capture_automation.manifest import Journal
from services.research_workers.capture_automation.queue import CaptureQueue
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.capture_automation.state_machine import (
    CAPTURED, EXCEPTION, HotelOutcome,
)

from .conftest import FakeBrowserSession, entry_for, pages_from

GOOD = "marriott-cmham.json"
OTHER = "marriott-cmhaw.json"


class FrozenClock:
    def __init__(self):
        self.t = 1_781_000_000.0

    def __call__(self):
        self.t += 0.5
        return self.t


def make_runner(tmp_path, session, **cfg):
    return CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "batch", **cfg),
                         clock=FrozenClock(), sleep=lambda *_: None,
                         jitter=lambda a, b: a)


def queue_of(*names):
    return CaptureQueue(batch_id="resume-test",
                        entries=tuple(entry_for(n) for n in names))


def seed_journal(tmp_path, records):
    """Write a journal by hand so a prior run's exact shape can be modelled."""
    d = tmp_path / "batch"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "journal.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return p


def complete_capture_record(tmp_path, hotel_id):
    """A CAPTURED record whose artifacts genuinely exist on disk."""
    caps = tmp_path / "batch" / "captures"
    caps.mkdir(parents=True, exist_ok=True)
    jf, pf = caps / ("%s.json" % hotel_id), caps / ("%s.png" % hotel_id)
    jf.write_text("{}", encoding="utf-8")
    pf.write_bytes(b"\x89PNG\r\n\x1a\n")
    return {"hotel_id": hotel_id, "state": CAPTURED, "reason": "", "detail": [],
            "at": "2026-08-03T00:00:00.000Z", "attempt": 1, "elapsed_seconds": 1.0,
            "artifacts": {"json_path": str(jf), "png_path": str(pf),
                          "png_sha256": "a" * 64, "text_sha256": "b" * 64}}


def exception_record(hotel_id, reason):
    return {"hotel_id": hotel_id, "state": EXCEPTION, "reason": reason,
            "detail": [], "at": "2026-08-03T00:00:00.000Z", "attempt": 1,
            "elapsed_seconds": 1.0, "artifacts": None}


# --------------------------------------------------------------------------- #
# 1-2. Completed skips; incomplete re-runs.
# --------------------------------------------------------------------------- #

class TestCompletedVersusIncomplete:
    def test_1_a_completed_capture_is_skipped(self, tmp_path):
        seed_journal(tmp_path, [complete_capture_record(tmp_path, entry_for(GOOD).hotel_id)])
        session = FakeBrowserSession(pages_from(GOOD))
        result = make_runner(tmp_path, session, resume=True).run(queue_of(GOOD))
        assert session.navigations == [], "a complete capture must not be re-fetched"
        assert result.manifest["resume"]["counts"]["skipped_completed"] == 1

    def test_2_an_incomplete_capture_is_rerun(self, tmp_path):
        """CAPTURED, but the artifacts are not on disk. Fails closed."""
        hid = entry_for(GOOD).hotel_id
        rec = complete_capture_record(tmp_path, hid)
        pathlib.Path(rec["artifacts"]["png_path"]).unlink()
        seed_journal(tmp_path, [rec])
        session = FakeBrowserSession(pages_from(GOOD))
        result = make_runner(tmp_path, session, resume=True).run(queue_of(GOOD))
        assert session.navigations, "a capture with missing artifacts must be re-run"
        assert result.manifest["resume"]["counts"]["skipped_completed"] == 0

    def test_a_capture_without_a_hash_is_rerun(self, tmp_path):
        hid = entry_for(GOOD).hotel_id
        rec = complete_capture_record(tmp_path, hid)
        rec["artifacts"]["png_sha256"] = ""
        seed_journal(tmp_path, [rec])
        session = FakeBrowserSession(pages_from(GOOD))
        make_runner(tmp_path, session, resume=True).run(queue_of(GOOD))
        assert session.navigations

    def test_existing_completed_artifacts_are_not_overwritten(self, tmp_path):
        hid = entry_for(GOOD).hotel_id
        rec = complete_capture_record(tmp_path, hid)
        png = pathlib.Path(rec["artifacts"]["png_path"])
        before = png.read_bytes()
        seed_journal(tmp_path, [rec])
        make_runner(tmp_path, FakeBrowserSession(pages_from(GOOD)),
                    resume=True).run(queue_of(GOOD))
        assert png.read_bytes() == before


# --------------------------------------------------------------------------- #
# 3-6. Terminal non-captures are never treated as completed.
# --------------------------------------------------------------------------- #

class TestExceptionsAreNotCompletions:
    @pytest.mark.parametrize("reason", [
        "IDENTITY_FAILED",          # 3
        "IDENTITY_UNVERIFIABLE",    # 4
        "POLICY_NOT_FOUND",         # 5
        "POLICY_OFF_SCREEN",        # 6
    ])
    def test_terminal_exception_is_reattempted_not_skipped(self, tmp_path, reason):
        hid = entry_for(GOOD).hotel_id
        seed_journal(tmp_path, [exception_record(hid, reason)])
        session = FakeBrowserSession(pages_from(GOOD))
        result = make_runner(tmp_path, session, resume=True).run(queue_of(GOOD))
        assert session.navigations, "%s must be re-attempted, never skipped" % reason
        rs = result.manifest["resume"]
        assert rs["counts"]["skipped_completed"] == 0
        assert hid in rs["reattempted_incomplete"]

    def test_manual_review_outcomes_are_reported_as_such(self, tmp_path):
        """POLICY_NOT_FOUND is RETRY_MANUAL: re-attempted, and surfaced so an
        operator can see it needs a human rather than another loop."""
        hid = entry_for(GOOD).hotel_id
        seed_journal(tmp_path, [exception_record(hid, "POLICY_NOT_FOUND")])
        result = make_runner(tmp_path, FakeBrowserSession(pages_from(GOOD)),
                             resume=True).run(queue_of(GOOD))
        assert hid in result.manifest["resume"]["manual_review"]

    def test_a_retry_now_outcome_is_not_flagged_manual(self, tmp_path):
        hid = entry_for(GOOD).hotel_id
        seed_journal(tmp_path, [exception_record(hid, "POLICY_OFF_SCREEN")])
        result = make_runner(tmp_path, FakeBrowserSession(pages_from(GOOD)),
                             resume=True).run(queue_of(GOOD))
        assert hid not in result.manifest["resume"]["manual_review"]


# --------------------------------------------------------------------------- #
# 7. Malformed prior records fail closed.
# --------------------------------------------------------------------------- #

class TestMalformedRecordsFailClosed:
    def test_7_a_malformed_artifacts_block_is_rerun(self, tmp_path):
        hid = entry_for(GOOD).hotel_id
        bad = {"hotel_id": hid, "state": CAPTURED, "reason": "", "detail": [],
               "at": "2026-08-03T00:00:00.000Z", "attempt": 1,
               "artifacts": "not-a-mapping"}
        seed_journal(tmp_path, [bad])
        session = FakeBrowserSession(pages_from(GOOD))
        make_runner(tmp_path, session, resume=True).run(queue_of(GOOD))
        assert session.navigations, "a malformed record must not authorise a skip"

    def test_a_capture_with_no_artifacts_at_all_is_rerun(self, tmp_path):
        hid = entry_for(GOOD).hotel_id
        seed_journal(tmp_path, [{"hotel_id": hid, "state": CAPTURED, "reason": "",
                                 "detail": [], "at": "2026-08-03T00:00:00.000Z",
                                 "attempt": 1}])
        session = FakeBrowserSession(pages_from(GOOD))
        make_runner(tmp_path, session, resume=True).run(queue_of(GOOD))
        assert session.navigations

    def test_a_corrupt_journal_line_still_raises(self, tmp_path):
        """Unchanged behaviour: a journal that cannot be parsed is fatal, not
        silently truncated -- silently dropping lines would make resume lie."""
        from services.research_workers.capture_automation.manifest import JournalError

        d = tmp_path / "batch"
        d.mkdir(parents=True, exist_ok=True)
        (d / "journal.jsonl").write_text("{not json}\n", encoding="utf-8")
        with pytest.raises(JournalError):
            Journal.open(d).completed_capture_ids()


# --------------------------------------------------------------------------- #
# Summary shape and determinism.
# --------------------------------------------------------------------------- #

class TestResumeSummary:
    def test_the_summary_accounts_for_every_candidate(self, tmp_path):
        hid_done = entry_for(GOOD).hotel_id
        hid_todo = entry_for(OTHER).hotel_id
        seed_journal(tmp_path, [complete_capture_record(tmp_path, hid_done),
                                exception_record(hid_todo, "POLICY_OFF_SCREEN")])
        result = make_runner(tmp_path, FakeBrowserSession(pages_from(GOOD, OTHER)),
                             resume=True).run(queue_of(GOOD, OTHER))
        rs = result.manifest["resume"]
        assert rs["counts"]["total_candidates"] == 2
        assert rs["skipped_completed"] == [hid_done]
        assert rs["counts"]["attempted"] == 1
        assert rs["attempted"] == [hid_todo]

    def test_the_summary_is_deterministic(self, tmp_path):
        """Same journal state must yield the same decision, every time.

        Asserted by reading the journal repeatedly rather than by running the
        batch twice -- a second run legitimately CHANGES the state (it captures
        the outstanding hotel), so comparing two runs would be testing that the
        runner does nothing, which is the opposite of what resume is for.
        """
        seed_journal(tmp_path, [complete_capture_record(tmp_path, entry_for(GOOD).hotel_id),
                                exception_record(entry_for(OTHER).hotel_id, "POLICY_OFF_SCREEN")])
        journal = Journal.open(tmp_path / "batch")
        reads = [journal.completed_capture_ids() for _ in range(3)]
        assert reads[0] == reads[1] == reads[2]
        assert reads[0] == (entry_for(GOOD).hotel_id,)
        incomplete = [journal.incomplete_hotel_ids() for _ in range(3)]
        assert incomplete[0] == incomplete[1] == incomplete[2]
        assert incomplete[0] == (entry_for(OTHER).hotel_id,)

    def test_resume_flag_is_recorded(self, tmp_path):
        r = make_runner(tmp_path, FakeBrowserSession(pages_from(GOOD)),
                        resume=True).run(queue_of(GOOD))
        assert r.manifest["resume"]["resume_requested"] is True

    def test_the_cli_passes_the_flag_through(self):
        """The original defect: declared on the parser, never delivered."""
        import inspect

        from services.research_workers import cli

        src = inspect.getsource(cli._cmd_capture_batch)
        assert "resume=" in src, "--resume must reach RunnerConfig"


# --------------------------------------------------------------------------- #
# 8. Against the real consolidated run.
# --------------------------------------------------------------------------- #

CONSOLIDATED = pathlib.Path(
    r"C:\Atlas\atlas-dashboard\data\worker_runs\pettripfinder\consolidated_run_manifest.json")


@pytest.mark.skipif(not CONSOLIDATED.exists(), reason="run corpus is gitignored")
class TestAgainstTheConsolidatedRun:
    def test_8_resume_would_not_recapture_the_58_completed_hotels(self):
        """The 58 completed captures carry verified artifact paths and hashes,
        so a resumed run skips them; the 20 non-captures do not and would be
        re-attempted."""
        man = json.loads(CONSOLIDATED.read_text(encoding="utf-8"))
        captured = [c for c in man["candidates"] if c["disposition"] == "CAPTURED"]
        assert len(captured) == 58
        assert all(c["artifacts"] and c["artifacts"][0].get("png_sha256")
                   for c in captured), "every completed capture must be verifiable"

        non_capture = [c for c in man["candidates"] if c["disposition"] != "CAPTURED"]
        assert len(non_capture) == 20
        assert all(not c["artifacts"] for c in non_capture), (
            "non-captures must carry no artifact, so resume re-attempts them")
