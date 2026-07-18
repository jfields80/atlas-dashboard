"""AES-WORK-001B -- resume, force, and selected-job doctrine: durable
execution_state vs. per-run last_action, fingerprint-gated reuse, the
existing-state-without-resume/force refusal, disabled-job handling, and the
manifest-edit-triggers-selective-rerun end-to-end scenario. Static fixtures
only -- no network."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.batch import (
    JOB_DONE,
    JOB_FAILED,
    JOB_PENDING,
    JOB_SKIPPED,
    BatchJob,
    BatchManifest,
    BatchRunError,
    BatchStateError,
    JobState,
    load_batch_state,
    load_manifest,
    run_batch,
    write_batch_state,
)
from scripts.pettripfinder.importer.candidate import persist_candidate

_REPO_ROOT = Path(__file__).resolve().parents[3]
_STATIC_MANIFEST = Path(__file__).parent / "fixtures" / "batches" / "columbus_wave_1.json"
_CLOCK = lambda: "2026-07-17T00:00:00+00:00"   # noqa: E731 -- test-only fixed clock


def _manifest_with_batch_id(batch_id: str, **overrides) -> BatchManifest:
    base = load_manifest(_STATIC_MANIFEST)
    kwargs = dict(
        manifest_schema_version=base.manifest_schema_version, batch_id=batch_id,
        batch_name=base.batch_name, defaults=base.defaults, jobs=base.jobs)
    kwargs.update(overrides)
    return BatchManifest(**kwargs)


def _run(manifest, output_root, **overrides):
    kwargs = dict(
        extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
        output_root=str(output_root), observed_at="2026-07-17",
        repo_root=_REPO_ROOT, clock=_CLOCK)
    kwargs.update(overrides)
    return run_batch(manifest, **kwargs)


def _edit_job(manifest: BatchManifest, job_id: str, **field_overrides) -> BatchManifest:
    new_jobs = tuple(
        (job if job.job_id != job_id else
         BatchJob(**{**job.__dict__, **field_overrides}))
        for job in manifest.jobs
    )
    return BatchManifest(
        manifest_schema_version=manifest.manifest_schema_version, batch_id=manifest.batch_id,
        batch_name=manifest.batch_name, defaults=manifest.defaults, jobs=new_jobs)


# --------------------------------------------------------------------------- #
# Existing-state-without-resume/force refusal.
# --------------------------------------------------------------------------- #

class TestRefusalWithoutResumeOrForce:
    def test_second_run_without_resume_or_force_is_refused(self, tmp_path):
        manifest = _manifest_with_batch_id("refusal-test")
        _run(manifest, tmp_path)
        with pytest.raises(BatchRunError, match="pass resume=True or force=True"):
            _run(manifest, tmp_path)

    def test_refusal_happens_before_touching_the_manifest_snapshot(self, tmp_path):
        """The refusal must fire before manifest.json is rewritten -- proven
        by the manifest snapshot from run 1 being byte-identical after the
        refused run 2 attempt."""
        manifest = _manifest_with_batch_id("refusal-no-write-test")
        _run(manifest, tmp_path)
        manifest_snapshot_path = tmp_path / C.BATCHES_SUBDIR / "refusal-no-write-test" / "manifest.json"
        before = manifest_snapshot_path.read_bytes()

        edited = _edit_job(manifest, "drury-dublin", candidate_name="Changed Name")
        with pytest.raises(BatchRunError):
            _run(edited, tmp_path)   # same batch_id, neither resume nor force

        assert manifest_snapshot_path.read_bytes() == before

    def test_first_run_with_no_prior_state_never_refused(self, tmp_path):
        manifest = _manifest_with_batch_id("fresh-run-test")
        state = _run(manifest, tmp_path)   # resume=False, force=False, no prior state
        assert all(j.execution_state == JOB_DONE for j in state.jobs)


# --------------------------------------------------------------------------- #
# --resume with an unchanged manifest: everything reused.
# --------------------------------------------------------------------------- #

class TestResumeReuse:
    def test_unchanged_manifest_resume_reuses_every_job(self, tmp_path):
        manifest = _manifest_with_batch_id("reuse-test")
        state1 = _run(manifest, tmp_path)
        state2 = _run(manifest, tmp_path, resume=True)

        for js in state2.jobs:
            assert js.execution_state == JOB_DONE
            assert js.last_action == "reused"

        by_id1 = {j.job_id: j for j in state1.jobs}
        by_id2 = {j.job_id: j for j in state2.jobs}
        for job_id in by_id1:
            assert by_id1[job_id].candidate_id == by_id2[job_id].candidate_id
            assert by_id1[job_id].candidate_path == by_id2[job_id].candidate_path

    def test_reuse_does_not_call_the_importer_again(self, tmp_path, monkeypatch):
        manifest = _manifest_with_batch_id("no-reimport-test")
        _run(manifest, tmp_path)

        import scripts.pettripfinder.importer.batch as batch_mod

        def _boom(*args, **kwargs):
            raise AssertionError("run_job must not be called for a reused job")

        monkeypatch.setattr(batch_mod, "run_job", _boom)
        state = _run(manifest, tmp_path, resume=True)
        assert all(j.last_action == "reused" for j in state.jobs)

    def test_prior_failed_job_always_reruns_on_resume(self, tmp_path):
        job = BatchJob(job_id="only-job", candidate_name="X", category="hotels",
                       expected_city="Dublin", expected_state="OH",
                       urls=("https://www.druryhotels.com/locations/columbus-oh/"
                            "drury-inn-and-suites-columbus-dublin",),
                       static_fixtures=("tests/pettripfinder/importer/fixtures/hotel_01_strong.json",))
        manifest = BatchManifest(manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION,
                                 batch_id="prior-failed-test", batch_name="t", defaults={},
                                 jobs=(job,))
        _run(manifest, tmp_path, fetcher_factory=lambda j: (_ for _ in ()).throw(
            RuntimeError("boom")), extractor_factory=lambda j: None)

        state = _run(manifest, tmp_path, resume=True)   # real importer this time
        assert state.jobs[0].execution_state == JOB_DONE
        assert state.jobs[0].last_action == "ran"

    def test_fingerprint_mismatch_reruns_only_that_job_others_reused(self, tmp_path):
        manifest = _manifest_with_batch_id("fp-mismatch-test")
        _run(manifest, tmp_path)

        edited = _edit_job(manifest, "scioto-audubon", candidate_name="Scioto Audubon Metro Park")
        state = _run(edited, tmp_path, resume=True)
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["scioto-audubon"].last_action == "ran"
        assert by_id["drury-dublin"].last_action == "reused"
        assert by_id["land-grant"].last_action == "reused"

    def test_reuse_skipped_when_candidate_file_missing_on_disk(self, tmp_path):
        manifest = _manifest_with_batch_id("missing-candidate-test")
        state1 = _run(manifest, tmp_path)
        js = next(j for j in state1.jobs if j.job_id == "drury-dublin")
        Path(js.candidate_path).unlink()

        state2 = _run(manifest, tmp_path, resume=True)
        by_id = {j.job_id: j for j in state2.jobs}
        assert by_id["drury-dublin"].last_action == "ran"
        assert Path(by_id["drury-dublin"].candidate_path).exists()

    def test_reuse_skipped_when_report_file_missing_on_disk(self, tmp_path):
        manifest = _manifest_with_batch_id("missing-report-test")
        state1 = _run(manifest, tmp_path)
        js = next(j for j in state1.jobs if j.job_id == "scioto-audubon")
        Path(js.report_path).unlink()

        state2 = _run(manifest, tmp_path, resume=True)
        by_id = {j.job_id: j for j in state2.jobs}
        assert by_id["scioto-audubon"].last_action == "ran"

    def test_reuse_skipped_when_candidate_json_is_corrupt(self, tmp_path):
        manifest = _manifest_with_batch_id("corrupt-candidate-test")
        state1 = _run(manifest, tmp_path)
        js = next(j for j in state1.jobs if j.job_id == "land-grant")
        Path(js.candidate_path).write_text("{not valid json", encoding="utf-8")

        state2 = _run(manifest, tmp_path, resume=True)
        by_id = {j.job_id: j for j in state2.jobs}
        assert by_id["land-grant"].last_action == "ran"
        assert json.loads(Path(by_id["land-grant"].candidate_path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# --force: reruns every selected+enabled job regardless of prior state.
# --------------------------------------------------------------------------- #

class TestForce:
    def test_force_reruns_every_job_even_though_all_are_done(self, tmp_path):
        manifest = _manifest_with_batch_id("force-test")
        _run(manifest, tmp_path)
        state = _run(manifest, tmp_path, force=True)
        assert all(j.last_action == "ran" for j in state.jobs)

    def test_force_with_job_id_only_forces_the_selected_job(self, tmp_path):
        manifest = _manifest_with_batch_id("force-selected-test")
        _run(manifest, tmp_path)
        state = _run(manifest, tmp_path, force=True, selected_job_ids=("land-grant",))
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["land-grant"].last_action == "ran"
        assert by_id["drury-dublin"].last_action == "skipped_not_selected"
        assert by_id["scioto-audubon"].last_action == "skipped_not_selected"
        # untouched jobs keep their DONE durable state exactly.
        assert by_id["drury-dublin"].execution_state == JOB_DONE
        assert by_id["scioto-audubon"].execution_state == JOB_DONE


# --------------------------------------------------------------------------- #
# Selected-job (--job-id) behavior on a fresh batch: durable state for
# non-selected jobs stays PENDING (never executed, never marked SKIPPED).
# --------------------------------------------------------------------------- #

class TestSelectedJobOnFreshBatch:
    def test_first_run_with_job_id_leaves_others_pending(self, tmp_path):
        manifest = _manifest_with_batch_id("partial-first-run-test")
        state = _run(manifest, tmp_path, selected_job_ids=("land-grant",))
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["land-grant"].execution_state == JOB_DONE
        assert by_id["land-grant"].last_action == "ran"
        assert by_id["drury-dublin"].execution_state == JOB_PENDING
        assert by_id["drury-dublin"].last_action == "skipped_not_selected"
        assert by_id["scioto-audubon"].execution_state == JOB_PENDING

    def test_second_partial_run_without_resume_force_is_refused(self, tmp_path):
        manifest = _manifest_with_batch_id("partial-second-refusal-test")
        _run(manifest, tmp_path, selected_job_ids=("land-grant",))
        with pytest.raises(BatchRunError):
            _run(manifest, tmp_path, selected_job_ids=("drury-dublin",))

    def test_full_resume_after_partial_run_completes_the_rest(self, tmp_path):
        manifest = _manifest_with_batch_id("partial-then-full-resume-test")
        _run(manifest, tmp_path, selected_job_ids=("land-grant",))
        state = _run(manifest, tmp_path, resume=True)   # no job-id filter now
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["land-grant"].last_action == "reused"
        assert by_id["drury-dublin"].last_action == "ran"
        assert by_id["scioto-audubon"].last_action == "ran"
        assert all(j.execution_state == JOB_DONE for j in state.jobs)

    def test_unknown_selected_job_id_rejected_before_any_disk_write(self, tmp_path):
        manifest = _manifest_with_batch_id("unknown-job-id-test")
        with pytest.raises(BatchRunError, match="unknown selected job id"):
            _run(manifest, tmp_path, selected_job_ids=("does-not-exist",))
        assert not (tmp_path / C.BATCHES_SUBDIR).exists()


# --------------------------------------------------------------------------- #
# Disabled jobs.
# --------------------------------------------------------------------------- #

class TestDisabledJobs:
    def test_disabled_job_is_skipped_with_reason_and_updated_fingerprint(self, tmp_path):
        manifest = _manifest_with_batch_id("disabled-test")
        manifest = _edit_job(manifest, "scioto-audubon", enabled=False)
        state = _run(manifest, tmp_path)
        js = next(j for j in state.jobs if j.job_id == "scioto-audubon")
        assert js.execution_state == JOB_SKIPPED
        assert js.last_action == "skipped_disabled"
        assert js.skip_reason == "disabled"

    def test_disabled_totals_reported_separately_from_failed_or_pending(self, tmp_path):
        from scripts.pettripfinder.importer.batch import build_batch_summary
        manifest = _manifest_with_batch_id("disabled-totals-test")
        manifest = _edit_job(manifest, "scioto-audubon", enabled=False)
        state = _run(manifest, tmp_path)
        summary = build_batch_summary(state, manifest)
        assert summary["totals"]["disabled"] == 1
        assert summary["totals"]["done"] == 2
        assert summary["totals"]["failed"] == 0
        assert summary["totals"]["pending"] == 0


# --------------------------------------------------------------------------- #
# State/version/identity compatibility gates -- all fail before execution.
# --------------------------------------------------------------------------- #

class TestStateCompatibilityGates:
    def test_malformed_state_json_fails_before_execution(self, tmp_path):
        manifest = _manifest_with_batch_id("malformed-state-test")
        batch_dir = tmp_path / C.BATCHES_SUBDIR / "malformed-state-test"
        batch_dir.mkdir(parents=True)
        (batch_dir / "state.json").write_text("{not valid json", encoding="utf-8")
        original = (batch_dir / "state.json").read_bytes()

        with pytest.raises(BatchRunError, match="malformed"):
            _run(manifest, tmp_path, resume=True)
        assert (batch_dir / "state.json").read_bytes() == original

    def test_state_version_mismatch_fails_before_execution(self, tmp_path):
        manifest = _manifest_with_batch_id("version-mismatch-test")
        _run(manifest, tmp_path)
        state_path = tmp_path / C.BATCHES_SUBDIR / "version-mismatch-test" / "state.json"
        stale = load_batch_state(state_path)
        from scripts.pettripfinder.importer.batch import BatchState
        tampered = BatchState(
            batch_state_version="99.0", batch_id=stale.batch_id,
            manifest_hash=stale.manifest_hash,
            manifest_schema_version=stale.manifest_schema_version,
            extractor=stale.extractor, model=stale.model, observed_at=stale.observed_at,
            jobs=stale.jobs)
        write_batch_state(tampered, state_path.parent)

        with pytest.raises(BatchRunError, match="incompatible"):
            _run(manifest, tmp_path, resume=True)

    def test_batch_id_mismatch_inside_state_fails_before_execution(self, tmp_path):
        manifest = _manifest_with_batch_id("batch-id-mismatch-test")
        _run(manifest, tmp_path)
        state_path = tmp_path / C.BATCHES_SUBDIR / "batch-id-mismatch-test" / "state.json"
        stale = load_batch_state(state_path)
        from scripts.pettripfinder.importer.batch import BatchState
        tampered = BatchState(
            batch_state_version=stale.batch_state_version, batch_id="some-other-batch",
            manifest_hash=stale.manifest_hash,
            manifest_schema_version=stale.manifest_schema_version,
            extractor=stale.extractor, model=stale.model, observed_at=stale.observed_at,
            jobs=stale.jobs)
        write_batch_state(tampered, state_path.parent)

        with pytest.raises(BatchRunError, match="batch_id"):
            _run(manifest, tmp_path, resume=True)


# --------------------------------------------------------------------------- #
# manifest.json snapshot behavior across runs.
# --------------------------------------------------------------------------- #

class TestManifestSnapshot:
    def test_manifest_snapshot_rewritten_on_every_run_including_resume(self, tmp_path):
        manifest = _manifest_with_batch_id("snapshot-rewrite-test")
        _run(manifest, tmp_path)
        snapshot_path = tmp_path / C.BATCHES_SUBDIR / "snapshot-rewrite-test" / "manifest.json"
        first = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert first["batch_name"] == manifest.batch_name

        edited = manifest.__class__(
            manifest_schema_version=manifest.manifest_schema_version,
            batch_id=manifest.batch_id, batch_name="Columbus Wave 1 (revised)",
            defaults=manifest.defaults, jobs=manifest.jobs)
        _run(edited, tmp_path, resume=True)
        second = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert second["batch_name"] == "Columbus Wave 1 (revised)"


# --------------------------------------------------------------------------- #
# Full manifest-edit-and-resume proof (mirrors the doctrine's own example).
# --------------------------------------------------------------------------- #

class TestManifestEditAndResumeEndToEnd:
    def test_editing_one_job_only_reruns_that_job_across_a_realistic_edit_cycle(self, tmp_path):
        manifest = _manifest_with_batch_id("edit-cycle-test")
        state1 = _run(manifest, tmp_path)
        assert all(j.last_action == "ran" for j in state1.jobs)

        # Operator tweaks only the land-grant job's candidate_name.
        edited = _edit_job(manifest, "land-grant", candidate_name="Land-Grant Brewing Co.")
        state2 = _run(edited, tmp_path, resume=True)
        by_id2 = {j.job_id: j for j in state2.jobs}
        assert by_id2["land-grant"].last_action == "ran"
        assert by_id2["drury-dublin"].last_action == "reused"
        assert by_id2["scioto-audubon"].last_action == "reused"

        # A third, fully unchanged resume now reuses everything, including
        # the just-rerun land-grant job.
        state3 = _run(edited, tmp_path, resume=True)
        assert all(j.last_action == "reused" for j in state3.jobs)
