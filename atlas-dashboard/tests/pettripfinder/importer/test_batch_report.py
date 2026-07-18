"""AES-WORK-001C -- consolidated batch HTML report: content, manifest-order
determinism, relative links, operator commands, HTML escaping, and atomic
persistence. Static fixtures only -- no network."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.batch import (
    JOB_DONE,
    JOB_FAILED,
    JOB_PENDING,
    JOB_RUNNING,
    JOB_SKIPPED,
    BatchJob,
    BatchManifest,
    BatchState,
    JobState,
    load_manifest,
    run_batch,
)
from scripts.pettripfinder.importer.batch_report import (
    _atomic_write_text,
    build_batch_report_html,
    write_batch_report,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_STATIC_MANIFEST = Path(__file__).parent / "fixtures" / "batches" / "columbus_wave_1.json"
_CLOCK = lambda: "2026-07-18T00:00:00+00:00"   # noqa: E731 -- test-only fixed clock


def _sample_manifest(batch_id="report-test") -> BatchManifest:
    base = load_manifest(_STATIC_MANIFEST)
    return BatchManifest(
        manifest_schema_version=base.manifest_schema_version, batch_id=batch_id,
        batch_name=base.batch_name, defaults=base.defaults, jobs=base.jobs)


def _sample_state(manifest: BatchManifest, jobs=None) -> BatchState:
    jobs = jobs if jobs is not None else tuple(
        JobState(job_id=j.job_id, fingerprint="fp-%s" % j.job_id, execution_state=JOB_PENDING)
        for j in manifest.jobs)
    return BatchState(
        batch_state_version=C.BATCH_STATE_VERSION, batch_id=manifest.batch_id,
        manifest_hash="deadbeef" * 8, manifest_schema_version=manifest.manifest_schema_version,
        extractor="static", model=C.DEFAULT_ANTHROPIC_MODEL, observed_at="2026-07-18",
        jobs=jobs)


def _run(manifest, output_root, **overrides):
    kwargs = dict(
        extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
        output_root=str(output_root), observed_at="2026-07-18",
        repo_root=_REPO_ROOT, clock=_CLOCK)
    kwargs.update(overrides)
    return run_batch(manifest, **kwargs)


# --------------------------------------------------------------------------- #
# Task 13: the full static three-job report, real execution.
# --------------------------------------------------------------------------- #

class TestThreeJobReportEndToEnd:
    def test_all_done_ready_report_manifest_order_links_commands_totals(self, tmp_path):
        manifest = _sample_manifest()
        state = _run(manifest, tmp_path, max_workers=3)
        assert all(j.execution_state == JOB_DONE for j in state.jobs)
        assert all(j.recommendation == C.RECOMMEND_READY for j in state.jobs)

        report_path = tmp_path / C.BATCHES_SUBDIR / "report-test" / "report.html"
        assert report_path.exists()
        html = report_path.read_text(encoding="utf-8")

        # Manifest order, always -- job_id headers appear in this exact order.
        positions = [html.index('%s &mdash;' % jid)
                    for jid in ("drury-dublin", "scioto-audubon", "land-grant")]
        assert positions == sorted(positions)

        by_id = {j.job_id: j for j in state.jobs}
        for jid, js in by_id.items():
            candidate_rel = os.path.relpath(js.candidate_path, start=str(report_path.parent))
            candidate_rel = candidate_rel.replace(os.sep, "/")
            assert 'href="%s"' % candidate_rel in html
            assert ("approve_import_candidate.py --candidate %s --decision approve"
                    % js.candidate_path) in html
            assert ("approve_import_candidate.py --candidate %s --decision reject"
                    % js.candidate_path) in html

        assert ">3<" in html or "3</td>" in html   # totals rendered somewhere
        assert "READY" in html

    def test_report_links_resolve_to_real_files_on_disk(self, tmp_path):
        manifest = _sample_manifest("report-links-test")
        _run(manifest, tmp_path, max_workers=1)
        report_path = tmp_path / C.BATCHES_SUBDIR / "report-links-test" / "report.html"
        report_dir = report_path.parent
        html = report_path.read_text(encoding="utf-8")
        import re
        hrefs = re.findall(r'href="([^"]+)"', html)
        assert len(hrefs) == 6   # 3 jobs x (candidate json + report html)
        for href in hrefs:
            assert (report_dir / href).resolve().exists()


# --------------------------------------------------------------------------- #
# Batch header + totals content.
# --------------------------------------------------------------------------- #

class TestReportContent:
    def test_header_fields_present(self, tmp_path):
        manifest = _sample_manifest()
        state = _sample_state(manifest)
        html = build_batch_report_html(state, manifest, tmp_path)
        assert manifest.batch_name in html
        assert state.manifest_hash in html
        assert state.extractor in html
        assert state.model in html
        assert state.observed_at in html
        assert C.IMPORTER_VERSION in html
        assert C.AGGREGATION_VERSION in html
        assert state.batch_id in html

    def test_totals_reflect_mixed_execution_states_and_recommendations(self, tmp_path):
        manifest = _sample_manifest()
        job_ids = [j.job_id for j in manifest.jobs]
        jobs = (
            JobState(job_id=job_ids[0], fingerprint="fp0", execution_state=JOB_DONE,
                     recommendation=C.RECOMMEND_READY),
            JobState(job_id=job_ids[1], fingerprint="fp1", execution_state=JOB_FAILED,
                     error_type="RuntimeError", error_message="boom"),
            JobState(job_id=job_ids[2], fingerprint="fp2", execution_state=JOB_SKIPPED,
                     skip_reason="disabled"),
        )
        state = _sample_state(manifest, jobs)
        html = build_batch_report_html(state, manifest, tmp_path)
        assert "<td>1</td>" in html   # each of done/failed/disabled = 1
        assert "boom" in html
        assert "RuntimeError" in html
        assert "disabled" in html

    def test_pending_and_running_jobs_render_without_candidate_links(self, tmp_path):
        manifest = _sample_manifest()
        job_ids = [j.job_id for j in manifest.jobs]
        jobs = (
            JobState(job_id=job_ids[0], fingerprint="fp0", execution_state=JOB_PENDING),
            JobState(job_id=job_ids[1], fingerprint="fp1", execution_state=JOB_RUNNING,
                     run_id="2026-07-18T00:00:00+00:00"),
            JobState(job_id=job_ids[2], fingerprint="fp2", execution_state=JOB_PENDING),
        )
        state = _sample_state(manifest, jobs)
        html = build_batch_report_html(state, manifest, tmp_path)
        assert "approve_import_candidate.py" not in html
        assert "PENDING" in html
        assert "RUNNING" in html


# --------------------------------------------------------------------------- #
# Usage fields in the report.
# --------------------------------------------------------------------------- #

class TestReportUsage:
    def test_job_with_usage_shows_token_and_request_counts(self, tmp_path):
        manifest = _sample_manifest()
        job_ids = [j.job_id for j in manifest.jobs]
        jobs = (
            JobState(job_id=job_ids[0], fingerprint="fp0", execution_state=JOB_DONE,
                     recommendation=C.RECOMMEND_READY, provider_request_count=2,
                     input_tokens=1500, output_tokens=300),
            JobState(job_id=job_ids[1], fingerprint="fp1", execution_state=JOB_PENDING),
            JobState(job_id=job_ids[2], fingerprint="fp2", execution_state=JOB_PENDING),
        )
        state = _sample_state(manifest, jobs)
        html = build_batch_report_html(state, manifest, tmp_path)
        assert "1500" in html
        assert "300" in html
        assert "2 provider request" in html


# --------------------------------------------------------------------------- #
# HTML escaping: candidate names/errors are untrusted (operator-authored or
# extracted-from-page-text) and must never break out of the markup.
# --------------------------------------------------------------------------- #

class TestHtmlEscaping:
    def test_candidate_name_with_html_special_chars_is_escaped(self, tmp_path):
        job = BatchJob(
            job_id="danger", candidate_name='<script>alert("x")</script> & Co',
            category="hotels", expected_city="Columbus", expected_state="OH",
            urls=("https://example.test",))
        manifest = BatchManifest(
            manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="escape-test",
            batch_name="<b>bold</b> batch", defaults={}, jobs=(job,))
        state = _sample_state(manifest)
        html = build_batch_report_html(state, manifest, tmp_path)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "<b>bold</b>" not in html
        assert "&lt;b&gt;bold&lt;/b&gt;" in html

    def test_error_message_with_html_special_chars_is_escaped(self, tmp_path):
        manifest = _sample_manifest()
        job_ids = [j.job_id for j in manifest.jobs]
        jobs = (
            JobState(job_id=job_ids[0], fingerprint="fp0", execution_state=JOB_FAILED,
                     error_type="ValueError", error_message='bad <input> & "quotes"'),
            JobState(job_id=job_ids[1], fingerprint="fp1", execution_state=JOB_PENDING),
            JobState(job_id=job_ids[2], fingerprint="fp2", execution_state=JOB_PENDING),
        )
        state = _sample_state(manifest, jobs)
        html = build_batch_report_html(state, manifest, tmp_path)
        assert "<input>" not in html
        assert "&lt;input&gt;" in html


# --------------------------------------------------------------------------- #
# No batch-level approval action: exactly one approve/reject pair PER job
# that has a candidate, never a single action covering the whole batch.
# --------------------------------------------------------------------------- #

class TestNoBatchLevelApproval:
    def test_exactly_one_approve_reject_pair_per_done_job(self, tmp_path):
        manifest = _sample_manifest()
        state = _run(manifest, tmp_path, max_workers=1)
        report_path = tmp_path / C.BATCHES_SUBDIR / "report-test" / "report.html"
        html = report_path.read_text(encoding="utf-8")
        assert html.count("--decision approve") == 3
        assert html.count("--decision reject") == 3
        assert "--batch" not in html
        assert "approve-all" not in html.lower()
        assert "<form" not in html.lower()


# --------------------------------------------------------------------------- #
# Determinism: identical inputs -> byte-identical output; job order is
# ALWAYS manifest order, regardless of the state tuple's own ordering.
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_identical_inputs_produce_byte_identical_html(self, tmp_path):
        manifest = _sample_manifest()
        state = _sample_state(manifest)
        html1 = build_batch_report_html(state, manifest, tmp_path)
        html2 = build_batch_report_html(state, manifest, tmp_path)
        assert html1 == html2

    def test_report_job_order_is_manifest_order_even_if_state_jobs_shuffled(self, tmp_path):
        manifest = _sample_manifest()
        job_ids = [j.job_id for j in manifest.jobs]
        in_order = tuple(
            JobState(job_id=jid, fingerprint="fp-%s" % jid, execution_state=JOB_PENDING)
            for jid in job_ids)
        shuffled = tuple(reversed(in_order))
        assert [j.job_id for j in shuffled] != [j.job_id for j in in_order]

        state_in_order = _sample_state(manifest, in_order)
        state_shuffled = _sample_state(manifest, shuffled)
        html_in_order = build_batch_report_html(state_in_order, manifest, tmp_path)
        html_shuffled = build_batch_report_html(state_shuffled, manifest, tmp_path)
        # Same manifest -> same rendered job order, regardless of how the
        # (functionally identical, PENDING/PENDING/PENDING) state tuple
        # itself was ordered.
        assert html_in_order == html_shuffled


# --------------------------------------------------------------------------- #
# Atomic persistence.
# --------------------------------------------------------------------------- #

class TestAtomicReportWrite:
    def test_write_batch_report_creates_file(self, tmp_path):
        path = write_batch_report("<html>hi</html>", tmp_path)
        assert path == tmp_path / "report.html"
        assert path.read_text(encoding="utf-8") == "<html>hi</html>"

    def test_no_leftover_temp_files_on_success(self, tmp_path):
        write_batch_report("<html>hi</html>", tmp_path)
        assert sorted(p.name for p in tmp_path.iterdir()) == ["report.html"]

    def test_atomic_write_failure_leaves_prior_report_intact(self, tmp_path, monkeypatch):
        target = tmp_path / "report.html"
        _atomic_write_text(target, "<html>original</html>")
        original_bytes = target.read_bytes()

        def _boom(*args, **kwargs):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(os, "replace", _boom)
        with pytest.raises(OSError, match="simulated replace failure"):
            _atomic_write_text(target, "<html>new</html>")

        assert target.read_bytes() == original_bytes
        leftover = [p for p in tmp_path.iterdir() if p.name != "report.html"]
        assert leftover == []


# --------------------------------------------------------------------------- #
# Dry-run never creates report.html.
# --------------------------------------------------------------------------- #

class TestDryRunNoReport:
    def test_dry_run_creates_no_output_root_at_all(self, tmp_path):
        from scripts.run_import_batch import main
        output_root = tmp_path / "out"
        code = main(["--manifest", str(_STATIC_MANIFEST), "--extractor", "static",
                    "--dry-run", "--output-root", str(output_root),
                    "--observed-at", "2026-07-18"])
        assert code == 0
        assert not output_root.exists()
        assert not (output_root / C.BATCHES_SUBDIR).exists()
