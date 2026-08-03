"""The capture-time identity gate, asserted against a real runner pass.

The property that matters operationally: a page whose identity does not clear
FD-5 must stop BEFORE the policy region is ever touched -- no policy scan, no
interaction, no capture, no evidence. Asserting that at module level would
prove only that a function returns the right string; these tests prove the
runner acts on it.
"""

from __future__ import annotations

import copy
import json

import pytest

from services.research_workers.capture_automation import identity_keys as IK
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


class CountingSession(FakeBrowserSession):
    """FakeBrowserSession that records how many screenshots were taken."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.screenshot_calls = 0

    def screenshot_png(self, *args, **kwargs):
        self.screenshot_calls += 1
        return super().screenshot_png(*args, **kwargs)


def make_runner(tmp_path, session, **cfg):
    return CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "batch", **cfg),
                         clock=FrozenClock(), sleep=lambda *_: None,
                         jitter=lambda a, b: a)


def _queue(name=GOOD):
    return CaptureQueue(batch_id="identity-gate", entries=(entry_for(name),))


def _pages_with(payload_mutator, name=GOOD):
    """The real fixture page, mutated to model a weaker identity."""
    pages = copy.deepcopy(pages_from(name))
    for url, payload in pages.items():
        payload_mutator(payload)
    return pages


class TestConfirmedIdentityStillCaptures:
    def test_a_real_capture_still_succeeds(self, tmp_path):
        """The gate must not break the corpus it was added to protect."""
        session = FakeBrowserSession(pages_from(GOOD))
        result = make_runner(tmp_path, session).run(_queue())
        assert result.manifest["counts"]["captured"] == 1
        assert result.manifest["counts"]["exceptions"] == 0

    def test_the_real_pages_confirm_on_at_least_two_independent_keys(self):
        from services.research_workers.capture_automation.contracts import DomSnapshot
        from services.research_workers.capture_automation.identity_check import (
            classify_identity,
        )

        dom = DomSnapshot.from_capture_payload(load_fixture(GOOD))
        out = classify_identity(dom, entry_for(GOOD), observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_CONFIRMED
        assert len(out.keys.independent_groups) >= 2
        assert out.keys.has_authoritative


class TestMissingIdentityEvidenceStopsBeforePolicyScan:
    def _strip_structured_identity(self, payload):
        """Leave the name, remove every stable key: no JSON-LD address or
        phone, and no labelled markup. Exactly the name-only page FD-5 exists
        to refuse."""
        payload["jsonld"] = [{"@type": "Hotel", "name": "Columbus Airport Marriott"}]
        payload["html"] = "<html><head><title>Columbus Airport Marriott</title></head></html>"
        payload["text"] = "Columbus Airport Marriott in Columbus. Welcome to our hotel."

    def test_it_becomes_an_exception_and_captures_nothing(self, tmp_path):
        session = FakeBrowserSession(_pages_with(self._strip_structured_identity))
        result = make_runner(tmp_path, session).run(_queue())
        assert result.manifest["counts"]["captured"] == 0
        assert result.manifest["counts"]["exceptions"] == 1

    def test_no_capture_file_is_written(self, tmp_path):
        session = FakeBrowserSession(_pages_with(self._strip_structured_identity))
        make_runner(tmp_path, session).run(_queue())
        captures = list((tmp_path / "batch").rglob("*.json"))
        assert not any("captures" in str(p) for p in captures)

    def test_no_screenshot_is_taken(self, tmp_path):
        """A screenshot is the first act of capture. If identity did not
        confirm, the page was never photographed.

        The counter is added here rather than read off the fake: the fake does
        not track calls, so a ``getattr(..., 0)`` assertion would pass whether
        or not a screenshot happened.
        """
        session = CountingSession(_pages_with(self._strip_structured_identity))
        make_runner(tmp_path, session).run(_queue())
        assert session.screenshot_calls == 0

    def test_the_counter_would_catch_a_screenshot(self, tmp_path):
        """Guards the guard: on a confirmed page the same counter is non-zero,
        so the assertion above is measuring something real."""
        session = CountingSession(pages_from(GOOD))
        make_runner(tmp_path, session).run(_queue())
        assert session.screenshot_calls > 0

    def test_the_outcome_is_recorded_in_the_journal(self, tmp_path):
        session = FakeBrowserSession(_pages_with(self._strip_structured_identity))
        result = make_runner(tmp_path, session).run(_queue())
        blob = str(result.manifest)
        assert ("IDENTITY_INCOMPLETE" in blob or "IDENTITY_UNVERIFIABLE" in blob), blob


class TestConfirmedCapturesRecordTheirIdentityBasis:
    """A completed capture must state WHY we believed it was the right
    property. Recording that only on refusals left the successful case -- the
    one an approver reads -- with no citation at all."""

    def _captured(self, tmp_path):
        session = FakeBrowserSession(pages_from(GOOD))
        result = make_runner(tmp_path, session).run(_queue())
        assert result.manifest["counts"]["captured"] == 1
        return result.outcomes[0]

    def test_the_outcome_records_the_identity_verdict_and_keys(self, tmp_path):
        detail = " ".join(self._captured(tmp_path).detail)
        assert "identity_outcome:IDENTITY_CONFIRMED" in detail
        assert "independent_keys:" in detail and "independent_keys:none" not in detail
        assert "authoritative_key:yes" in detail
        assert "authoritative_basis:" in detail
        assert "authoritative_basis:none" not in detail
        assert "agreeing_keys:" in detail and "agreeing_keys:none" not in detail

    def test_the_agreeing_keys_name_their_evidence_basis(self, tmp_path):
        line = next(d for d in self._captured(tmp_path).detail
                    if d.startswith("agreeing_keys:"))
        assert "@" in line, line
        for pair in line.split(":", 1)[1].split(","):
            key, basis = pair.split("@")
            assert key in IK.APPROVED_KEYS
            assert basis in (IK.AUTHORITATIVE_BASES | IK.WEAK_BASES)

    def test_the_capture_artifacts_carry_the_full_assessment(self, tmp_path):
        identity = self._captured(tmp_path).artifacts["identity"]
        assert identity["outcome"] == IK.IDENTITY_CONFIRMED
        assert identity["may_proceed"] is True
        assert len(identity["keys"]["independent_groups"]) >= 2
        assert identity["keys"]["has_authoritative_key"] is True
        assert identity["keys"]["keys"], "the individual key evidence is recorded"

    def test_it_survives_to_the_on_disk_journal(self, tmp_path):
        """The journal is the durable record a reviewer reads later."""
        session = FakeBrowserSession(pages_from(GOOD))
        make_runner(tmp_path, session).run(_queue())
        lines = [json.loads(x) for x in
                 (tmp_path / "batch" / "journal.jsonl").read_text("utf-8").splitlines()
                 if x.strip()]
        record = next(r for r in lines if r["state"] == CAPTURED)
        assert any(d.startswith("identity_outcome:IDENTITY_CONFIRMED")
                   for d in record["detail"])
        assert record["artifacts"]["identity"]["keys"]["has_authoritative_key"] is True

    def test_refusals_still_record_theirs(self, tmp_path):
        def strip(payload):
            payload["jsonld"] = [{"@type": "Hotel", "name": "Columbus Airport Marriott"}]
            payload["html"] = "<html><head><title>x</title></head></html>"
            payload["text"] = "Columbus Airport Marriott in Columbus. Welcome."

        session = FakeBrowserSession(_pages_with(strip))
        result = make_runner(tmp_path, session).run(_queue())
        detail = " ".join(result.outcomes[0].detail)
        assert "identity_outcome:" in detail
        assert result.outcomes[0].state == EXCEPTION


class TestPartialIdentityIsStillRefused:
    def test_address_only_does_not_capture(self, tmp_path):
        """One approved key. Under the old gate name+address was EXACT_MATCH
        and would have captured."""
        def mutate(payload):
            payload["jsonld"] = [{
                "@type": "Hotel", "name": "Columbus Airport Marriott",
                "address": {"@type": "PostalAddress",
                            "streetAddress": "1375 North Cassady Avenue"}}]
            payload["html"] = "<html><head><title>Columbus Airport Marriott</title></head></html>"
            payload["text"] = ("Columbus Airport Marriott, 1375 North Cassady Avenue, "
                               "Columbus OH.")

        entry = entry_for(GOOD)
        queue = CaptureQueue(batch_id="identity-gate", entries=(
            entry.__class__(**{**entry.to_dict(),
                               "expected_phone": "", "expected_property_code": "",
                               "alternate_urls": (), "required_fields": (),
                               "priority_reasons": (), "discovery_provenance_refs": ()}),))
        session = FakeBrowserSession(_pages_with(mutate))
        result = make_runner(tmp_path, session).run(queue)
        assert result.manifest["counts"]["captured"] == 0
        assert result.manifest["counts"]["exceptions"] == 1


class TestBatchResilience:
    def test_one_identity_failure_does_not_stop_the_batch(self, tmp_path):
        """Founder requirement: continue after individual candidate failures."""
        good, bad = "marriott-cmham.json", "marriott-cmhaw.json"
        pages = dict(pages_from(good))
        weak = copy.deepcopy(pages_from(bad))
        for url, payload in weak.items():
            payload["jsonld"] = [{"@type": "Hotel", "name": "Somewhere"}]
            payload["html"] = "<html><head><title>Somewhere</title></head></html>"
            payload["text"] = "Somewhere. Welcome."
        pages.update(weak)

        session = FakeBrowserSession(pages)
        queue = CaptureQueue(batch_id="identity-gate",
                             entries=(entry_for(good), entry_for(bad)))
        result = make_runner(tmp_path, session).run(queue)
        counts = result.manifest["counts"]
        assert counts["captured"] == 1
        assert counts["exceptions"] == 1
