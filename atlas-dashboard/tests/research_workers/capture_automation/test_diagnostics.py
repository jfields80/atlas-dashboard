"""Failure diagnostics: evidence about why a capture failed.

Fourteen POLICY_NOT_FOUND and four POLICY_OFF_SCREEN outcomes were
undiagnosable because the exception path preserved nothing. These tests hold
the collector to the two rules that make it safe to add at all:

  * it can never change an outcome -- not the terminal reason, not the retry
    class, not what counts as a completed capture;
  * everything it writes is bounded, redacted, hashed, and labelled
    NON_AUTHORITATIVE / FAILURE_DIAGNOSTIC / NOT_FOR_EXTRACTION.

Fixtures and a fake browser only. No live page is needed to prove correctness.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from services.research_workers.capture_automation import diagnostics as D
from services.research_workers.capture_automation.contracts import BoxModel, DomSnapshot
from services.research_workers.capture_automation.manifest import Journal
from services.research_workers.capture_automation.queue import CaptureQueue
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.capture_automation.state_machine import (
    CAPTURED, EXCEPTION,
)

from .conftest import FakeBrowserSession, entry_for, load_fixture, pages_from

GOOD = "marriott-cmham.json"


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
    return CaptureQueue(batch_id="diag-test",
                        entries=tuple(entry_for(n) for n in names))


class StubSession:
    """Minimal session exposing only what the collector reads."""

    def __init__(self, *, geometry=None, png=b"\x89PNG\r\n\x1a\n", raises=False):
        self._geometry = geometry if geometry is not None else {
            "collected": True, "url": "https://example.test/x", "title": "T",
            "viewport": {"width": 1440, "height": 1000, "deviceScaleFactor": 1},
            "document": {"width": 1440, "height": 8000},
            "scroll": {"x": 0, "y": 1200, "maxY": 7000, "maxX": 0},
            "activeElement": "BODY", "fixedOverlays": [], "scrollContainers": [],
            "openDetails": 0, "dialogsOpen": 0,
            "ariaExpandedTrue": 2, "ariaExpandedFalse": 9}
        self._png = png
        self._raises = raises

    def evaluate(self, expression, timeout=60.0):
        if self._raises:
            raise RuntimeError("evaluate refused")
        return self._geometry

    def screenshot_png(self):
        if self._raises:
            raise RuntimeError("screenshot refused")
        return self._png


def ctx(**kw):
    base = dict(hotel_id="test-hotel", reason="POLICY_NOT_FOUND",
                official_url="https://example.test/hotel", brand="marriott",
                session=StubSession(),
                dom=DomSnapshot(final_url="https://example.test/hotel", title="Test Hotel",
                                html="<html><body>hello</body></html>", text="hello",
                                jsonld=({"@type": "Hotel", "name": "Test"},)))
    base.update(kw)
    return D.DiagnosticContext(**base)


# --------------------------------------------------------------------------- #
# 1-3. Records are written, with the right content, before cleanup.
# --------------------------------------------------------------------------- #

class TestRecordsAreWritten:
    def test_1_policy_not_found_writes_a_diagnostic_record(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(ctx(reason="POLICY_NOT_FOUND"))
        assert rec is not None
        assert rec["schema"] == D.DIAGNOSTIC_SCHEMA
        assert rec["terminal_reason"] == "POLICY_NOT_FOUND"
        assert (tmp_path / rec["relative_dir"] / "diagnostic.json").exists()

    def test_2_policy_off_screen_writes_geometry_and_target(self, tmp_path):
        box = BoxModel(x=0, y=6000, width=600, height=300, scroll_y=0)
        after = BoxModel(x=0, y=6400, width=600, height=300, scroll_y=0)
        rec = D.DiagnosticCollector(tmp_path).collect(ctx(
            reason="POLICY_OFF_SCREEN", policy_box=box, policy_box_after=after,
            viewport=(1440, 1000)))
        geo_path = tmp_path / rec["relative_dir"] / "geometry.json"
        assert geo_path.exists()
        geo = json.loads(geo_path.read_text(encoding="utf-8"))
        assert geo["policy_box"]["y"] == 6000
        assert geo["policy_box_after_screenshot"]["y"] == 6400
        assert geo["viewport"] == {"width": 1440, "height": 1000}
        assert geo["scroll"]["y"] == 1200 and geo["document"]["height"] == 8000

    def test_3_rendered_dom_is_captured(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(ctx())
        dom_path = tmp_path / rec["relative_dir"] / "rendered_dom.html"
        assert dom_path.exists()
        assert "hello" in dom_path.read_text(encoding="utf-8")

    def test_the_expansion_trace_records_what_was_attempted(self, tmp_path):
        from services.research_workers.capture_automation.adapters.ihg import IhgAdapter

        rec = D.DiagnosticCollector(tmp_path).collect(ctx(
            adapter=IhgAdapter(),
            interaction_log=({"action": "click_text", "selector": "a.cmp-faq__action",
                              "text": "FAQ", "performed": True},)))
        trace = json.loads((tmp_path / rec["relative_dir"] / "expansion_trace.json")
                           .read_text(encoding="utf-8"))
        assert "Can I bring my pet" in trace["anchor_terms_attempted"]
        assert trace["expansion_controls_declared"]
        assert trace["expansion_controls_performed"][0]["performed"] is True


# --------------------------------------------------------------------------- #
# 4-5. Diagnostics are not captures.
# --------------------------------------------------------------------------- #

class TestDiagnosticsAreNotCaptures:
    def test_4_diagnostics_do_not_count_as_completed_captures(self, tmp_path):
        d = tmp_path / "batch"
        d.mkdir(parents=True, exist_ok=True)
        rec = D.DiagnosticCollector(d).collect(ctx())
        (d / "journal.jsonl").write_text(json.dumps({
            "hotel_id": "test-hotel", "state": EXCEPTION, "reason": "POLICY_NOT_FOUND",
            "detail": [], "at": "2026-08-03T00:00:00.000Z", "attempt": 1,
            "artifacts": rec}) + "\n", encoding="utf-8")
        journal = Journal.open(d)
        assert journal.completed_capture_ids() == ()
        assert "test-hotel" in journal.incomplete_hotel_ids()

    def test_5_resume_reattempts_a_hotel_with_only_diagnostics(self, tmp_path):
        hid = entry_for(GOOD).hotel_id
        d = tmp_path / "batch"
        d.mkdir(parents=True, exist_ok=True)
        rec = D.DiagnosticCollector(d).collect(ctx(hotel_id=hid))
        (d / "journal.jsonl").write_text(json.dumps({
            "hotel_id": hid, "state": EXCEPTION, "reason": "POLICY_NOT_FOUND",
            "detail": [], "at": "2026-08-03T00:00:00.000Z", "attempt": 1,
            "artifacts": rec}) + "\n", encoding="utf-8")
        session = FakeBrowserSession(pages_from(GOOD))
        result = make_runner(tmp_path, session, resume=True).run(queue_of(GOOD))
        assert session.navigations, "a hotel with only diagnostics must be re-attempted"
        assert result.manifest["resume"]["counts"]["skipped_completed"] == 0

    def test_11_diagnostics_are_labelled_against_extraction(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(ctx())
        for label in D.DIAGNOSTIC_LABELS:
            assert label in rec["labels"]
        assert rec["non_authoritative"] is True
        assert rec["not_for_extraction"] is True
        assert D.is_diagnostic_artifact(rec) is True

    def test_diagnostics_are_written_outside_the_captures_directory(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(ctx())
        assert rec["relative_dir"].startswith("diagnostics/")
        assert "captures" not in rec["relative_dir"]


# --------------------------------------------------------------------------- #
# 6-7. Collection failures never mask the real outcome.
# --------------------------------------------------------------------------- #

class TestCollectionFailuresAreContained:
    def test_6_the_original_reason_survives_a_collection_error(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(
            ctx(reason="POLICY_OFF_SCREEN", session=StubSession(raises=True)))
        assert rec["terminal_reason"] == "POLICY_OFF_SCREEN"

    def test_7_partial_collection_is_recorded_without_crashing(self, tmp_path):
        """No DOM available, but geometry still collects."""
        rec = D.DiagnosticCollector(tmp_path).collect(ctx(dom=None))
        types = {a["artifact_type"]: a for a in rec["artifacts"]}
        assert types["rendered_dom"]["status"] == D.STATUS_SKIPPED
        assert types["geometry"]["status"] == D.STATUS_OK

    def test_a_failing_artifact_is_recorded_with_its_error(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(
            ctx(session=StubSession(raises=True)))
        vp = next(a for a in rec["artifacts"] if a["artifact_type"] == "viewport_png")
        assert vp["status"] == D.STATUS_FAILED
        assert vp["error"]

    def test_a_collector_explosion_still_returns_the_reason(self, tmp_path):
        class Exploding(D.DiagnosticCollector):
            def _collect(self, ctx):
                raise RuntimeError("boom")

        rec = Exploding(tmp_path).collect(ctx(reason="POLICY_NOT_FOUND"))
        assert rec["terminal_reason"] == "POLICY_NOT_FOUND"
        assert rec["collection_status"] == D.STATUS_FAILED


# --------------------------------------------------------------------------- #
# 8-9. Hashes, sizes, and never overwriting.
# --------------------------------------------------------------------------- #

class TestArtifactIntegrity:
    def test_8_hashes_and_sizes_match_the_files_on_disk(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(ctx())
        base = tmp_path / rec["relative_dir"]
        checked = 0
        for a in rec["artifacts"]:
            if a["status"] not in (D.STATUS_OK, D.STATUS_TRUNCATED):
                continue
            raw = (base / a["relative_path"]).read_bytes()
            assert len(raw) == a["bytes"]
            assert hashlib.sha256(raw).hexdigest() == a["sha256"]
            checked += 1
        assert checked >= 3

    def test_9_a_second_attempt_never_overwrites_the_first(self, tmp_path):
        c = D.DiagnosticCollector(tmp_path)
        first = c.collect(ctx())
        second = c.collect(ctx())
        assert first["relative_dir"] != second["relative_dir"]
        assert first["attempt_dir"] == "attempt-1"
        assert second["attempt_dir"] == "attempt-2"
        assert (tmp_path / first["relative_dir"] / "diagnostic.json").exists()

    def test_every_artifact_record_has_the_required_fields(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(ctx())
        for a in rec["artifacts"]:
            for key in ("artifact_type", "relative_path", "bytes", "sha256",
                        "status", "error", "truncated"):
                assert key in a


# --------------------------------------------------------------------------- #
# 12-14. Security, bounds, fail-closed metadata.
# --------------------------------------------------------------------------- #

class TestSecurityAndBounds:
    def test_12_secrets_and_cookies_are_absent_from_the_schema(self, tmp_path):
        rec = D.DiagnosticCollector(tmp_path).collect(ctx())
        blob = json.dumps(rec).lower()
        for forbidden in ("cookie", "authorization", "set-cookie", "api_key",
                          "access_token", "localstorage", "sessionstorage"):
            assert forbidden not in blob

    def test_secret_shaped_content_is_redacted_from_the_dom(self, tmp_path):
        html = ('<html><script>var cfg={"api_key":"AIzaSyREDACTMEREDACTME1234"};'
                '</script><p>Authorization: Bearer abcdefghijklmnopqrst</p></html>')
        rec = D.DiagnosticCollector(tmp_path).collect(ctx(
            dom=DomSnapshot(final_url="u", title="t", html=html, text="x")))
        body = (tmp_path / rec["relative_dir"] / "rendered_dom.html").read_text(encoding="utf-8")
        assert "AIzaSyREDACTMEREDACTME1234" not in body
        assert "abcdefghijklmnopqrst" not in body
        assert "REDACTED" in body

    def test_13_text_size_limits_are_enforced(self, tmp_path):
        huge = "<html>" + ("x" * (D.MAX_DOM_BYTES + 5000)) + "</html>"
        rec = D.DiagnosticCollector(tmp_path).collect(ctx(
            dom=DomSnapshot(final_url="u", title="t", html=huge, text="")))
        dom_rec = next(a for a in rec["artifacts"] if a["artifact_type"] == "rendered_dom")
        assert dom_rec["bytes"] <= D.MAX_DOM_BYTES
        assert dom_rec["truncated"] is True
        assert dom_rec["status"] == D.STATUS_TRUNCATED

    def test_14_malformed_diagnostic_metadata_fails_closed(self):
        with pytest.raises(D.DiagnosticError):
            D.assert_no_forbidden_fields({"hotel_id": "x", "cookies": "abc=1"})
        with pytest.raises(D.DiagnosticError):
            D.assert_no_forbidden_fields({"nested": [{"authorization": "Bearer x"}]})

    def test_a_clean_record_passes_the_forbidden_field_check(self):
        D.assert_no_forbidden_fields({"hotel_id": "x", "artifacts": [{"bytes": 1}]})


# --------------------------------------------------------------------------- #
# 15-17. Nothing else changes.
# --------------------------------------------------------------------------- #

class TestExistingBehaviourUnchanged:
    def test_10_successful_captures_are_unchanged(self, tmp_path):
        session = FakeBrowserSession(pages_from(GOOD))
        result = make_runner(tmp_path, session).run(queue_of(GOOD))
        assert result.manifest["counts"]["captured"] == 1
        assert result.manifest["counts"]["exceptions"] == 0
        rec = json.loads((tmp_path / "batch" / "journal.jsonl")
                         .read_text(encoding="utf-8").splitlines()[0])
        assert rec["state"] == CAPTURED
        assert not D.is_diagnostic_artifact(rec.get("artifacts"))
        assert rec["artifacts"].get("png_sha256")

    def test_a_success_writes_no_diagnostics_directory(self, tmp_path):
        make_runner(tmp_path, FakeBrowserSession(pages_from(GOOD))).run(queue_of(GOOD))
        assert not (tmp_path / "batch" / D.DIAGNOSTICS_DIRNAME).exists()

    def test_15_identity_refusal_behaviour_is_unchanged(self, tmp_path):
        """A name-only page still refuses, and diagnostics do not rescue it."""
        import copy

        pages = copy.deepcopy(pages_from(GOOD))
        for payload in pages.values():
            payload["jsonld"] = [{"@type": "Hotel", "name": "Columbus Airport Marriott"}]
            payload["html"] = "<html><head><title>Columbus Airport Marriott</title></head></html>"
            payload["text"] = "Columbus Airport Marriott in Columbus. Welcome."
        result = make_runner(tmp_path, FakeBrowserSession(pages)).run(queue_of(GOOD))
        assert result.manifest["counts"]["captured"] == 0
        assert result.manifest["counts"]["exceptions"] == 1

    def test_16_terminal_classifications_are_unchanged(self):
        """The collector reads reasons; it must not define or alter them."""
        src = pathlib.Path(D.__file__).read_text(encoding="utf-8")
        for forbidden in ("retry_for(", "RETRY_NOW", "EXCEPTION_REASONS",
                          "check_policy_framing", "locate_policy"):
            assert forbidden not in src, "diagnostics must not touch %s" % forbidden

    def test_17_cleanup_still_occurs_after_collection(self, tmp_path):
        """Diagnostics are gathered inside capture_one, so the batch still
        finishes and writes its manifest -- collection cannot strand a run."""
        session = FakeBrowserSession(pages_from(GOOD))
        result = make_runner(tmp_path, session).run(queue_of(GOOD))
        assert result.manifest_path is not None and result.manifest_path.exists()

    def test_diagnostics_never_apply_to_a_captured_outcome(self, tmp_path):
        assert D.diagnostic_level("POLICY_NOT_FOUND") == "full"
        assert D.diagnostic_level("POLICY_OFF_SCREEN") == "full"
        assert D.diagnostic_level("IDENTITY_FAILED") == "bounded"
        assert D.diagnostic_level("") == "none"


# --------------------------------------------------------------------------- #
# 4/18. Scope discipline.
# --------------------------------------------------------------------------- #

class TestScopeDiscipline:
    def test_identity_refusals_get_bounded_diagnostics_not_a_page_dump(self, tmp_path):
        """A page already judged to be the WRONG hotel is not retained."""
        rec = D.DiagnosticCollector(tmp_path).collect(ctx(reason="IDENTITY_FAILED"))
        assert rec["diagnostic_level"] == "bounded"
        types = {a["artifact_type"] for a in rec["artifacts"]}
        assert "rendered_dom" not in types

    def test_18_the_three_unrelated_files_remain_untouched(self):
        """Guards the standing instruction across this work order."""
        import subprocess

        out = subprocess.run(["git", "status", "--short", "--",
                              "services/research_workers/research_escalation.py",
                              "services/research_workers/web_research.py",
                              "tests/research_workers/test_research_provenance.py"],
                             capture_output=True, text=True,
                             cwd=r"C:\Atlas\atlas-dashboard").stdout
        # They were already modified/untracked before this work order and must
        # stay exactly that way -- never staged, never reverted.
        assert " M services/research_workers/research_escalation.py" in out
        assert " M services/research_workers/web_research.py" in out
        assert "?? tests/research_workers/test_research_provenance.py" in out
