"""AES-WORK-001B -- the sequential batch runner: execution routing (1 url ->
import_url, 2-4 urls -> import_urls), candidate/report persistence parity
with the existing single/multi-source CLIs, mixed READY/REVIEW/REJECT
outcomes, failure isolation, and KeyboardInterrupt handling. Static
fixtures only -- no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.import_official_url import _build_static, import_url
from scripts.import_official_urls import _build_static_multi, import_urls
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.batch import (
    JOB_DONE,
    JOB_FAILED,
    JOB_PENDING,
    JOB_RUNNING,
    BatchJob,
    BatchManifest,
    build_batch_summary,
    load_manifest,
    run_batch,
    run_job,
)
from scripts.pettripfinder.importer.candidate import candidate_from_dict
from scripts.pettripfinder.importer.models import ImportContext

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = Path(__file__).parent / "fixtures"
_BATCH_FIXTURES = _FIXTURES / "batches"
_STATIC_MANIFEST = _BATCH_FIXTURES / "columbus_wave_1.json"

_DRURY_URL = ("https://www.druryhotels.com/locations/columbus-oh/"
             "drury-inn-and-suites-columbus-dublin")
_DRURY_FIXTURE = "tests/pettripfinder/importer/fixtures/hotel_01_strong.json"
_FAQ_URL = "https://landgrantbrewing.com/faq/"
_CONTACT_URL = "https://landgrantbrewing.com/taproom/"
_FAQ_FIXTURE = "tests/pettripfinder/importer/fixtures/aggregate_landgrant_faq.json"
_CONTACT_FIXTURE = "tests/pettripfinder/importer/fixtures/aggregate_landgrant_contact.json"

_CLOCK = lambda: "2026-07-17T00:00:00+00:00"   # noqa: E731 -- test-only fixed clock


def _manifest_with_batch_id(batch_id: str) -> BatchManifest:
    """The checked-in three-job manifest, retargeted to a fresh batch_id so
    each test gets its own state directory under a shared tmp_path."""
    base = load_manifest(_STATIC_MANIFEST)
    return BatchManifest(
        manifest_schema_version=base.manifest_schema_version, batch_id=batch_id,
        batch_name=base.batch_name, defaults=base.defaults, jobs=base.jobs)


def _one_job_manifest(batch_id: str, job: BatchJob) -> BatchManifest:
    return BatchManifest(
        manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id=batch_id,
        batch_name="single job", defaults={}, jobs=(job,))


def _run(manifest, output_root, **overrides):
    kwargs = dict(
        extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
        output_root=str(output_root), observed_at="2026-07-17",
        repo_root=_REPO_ROOT, clock=_CLOCK)
    kwargs.update(overrides)
    return run_batch(manifest, **kwargs)


# --------------------------------------------------------------------------- #
# Execution routing: strictly by URL count, never a second extraction path.
# --------------------------------------------------------------------------- #

class TestExecutionRouting:
    def test_single_url_job_routes_through_import_url_shape(self, tmp_path):
        job = BatchJob(
            job_id="drury", candidate_name="Drury Inn", category="hotels",
            expected_city="Dublin", expected_state="OH", urls=(_DRURY_URL,),
            static_fixtures=(_DRURY_FIXTURE,))
        candidate, json_path, report_path = run_job(
            job, extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
            observed_at="2026-07-17", created_at="2026-07-17T00:00:00+00:00",
            output_root=str(tmp_path), repo_root=_REPO_ROOT)
        assert candidate.sources == ()
        assert candidate.aggregation_version == ""

    def test_multi_url_job_routes_through_import_urls_shape(self, tmp_path):
        job = BatchJob(
            job_id="land-grant", candidate_name="Land-Grant Brewing Columbus",
            category="restaurants", expected_city="Columbus", expected_state="OH",
            urls=(_FAQ_URL, _CONTACT_URL),
            static_fixtures=(_FAQ_FIXTURE, _CONTACT_FIXTURE))
        candidate, json_path, report_path = run_job(
            job, extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
            observed_at="2026-07-17", created_at="2026-07-17T00:00:00+00:00",
            output_root=str(tmp_path), repo_root=_REPO_ROOT)
        assert len(candidate.sources) == 2
        assert candidate.aggregation_version == C.AGGREGATION_VERSION

    def test_fetcher_and_extractor_factory_must_be_supplied_together(self, tmp_path):
        job = BatchJob(
            job_id="drury", candidate_name="Drury Inn", category="hotels",
            expected_city="Dublin", expected_state="OH", urls=(_DRURY_URL,),
            static_fixtures=(_DRURY_FIXTURE,))
        with pytest.raises(ValueError, match="must be supplied together"):
            run_job(
                job, extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
                observed_at="2026-07-17", created_at="2026-07-17T00:00:00+00:00",
                output_root=str(tmp_path), repo_root=_REPO_ROOT,
                fetcher_factory=lambda j: None)


# --------------------------------------------------------------------------- #
# Parity: a batch job's persisted candidate must be byte-identical in shape
# to calling the existing CLI entry points directly with the same inputs.
# --------------------------------------------------------------------------- #

class TestParityWithExistingCli:
    def test_single_source_batch_job_matches_direct_import_url_call(self, tmp_path):
        ctx = ImportContext(category="hotels", candidate_name="Drury Inn & Suites Columbus Dublin",
                            expected_city="Dublin", expected_state="OH",
                            source_relationship_hint="EXACT_ENTITY_DOMAIN")
        fetcher, extractor = _build_static(_DRURY_URL, _DRURY_FIXTURE)
        direct, direct_json, direct_report = import_url(
            _DRURY_URL, ctx, fetcher=fetcher, extractor=extractor,
            output_root=str(tmp_path / "direct"), observed_at="2026-07-17",
            created_at="2026-07-17T00:00:00+00:00")

        manifest = _manifest_with_batch_id("parity-single")
        state = _run(manifest, tmp_path / "batch", selected_job_ids=("drury-dublin",))
        js = next(j for j in state.jobs if j.job_id == "drury-dublin")
        via_batch = candidate_from_dict(json.loads(Path(js.candidate_path).read_text(encoding="utf-8")))

        assert via_batch.proposed_fields == direct.proposed_fields
        assert via_batch.pet_facts == direct.pet_facts
        assert via_batch.recommendation == direct.recommendation
        assert via_batch.sources == () == direct.sources
        assert via_batch.aggregation_version == "" == direct.aggregation_version

    def test_multi_source_batch_job_matches_direct_import_urls_call(self, tmp_path):
        ctx = ImportContext(category="restaurants", candidate_name="Land-Grant Brewing Columbus",
                            expected_city="Columbus", expected_state="OH",
                            source_relationship_hint="EXACT_ENTITY_DOMAIN")
        fetcher, extractor = _build_static_multi(
            [_FAQ_URL, _CONTACT_URL], [_FAQ_FIXTURE, _CONTACT_FIXTURE])
        direct, direct_json, direct_report = import_urls(
            [_FAQ_URL, _CONTACT_URL], ctx, fetcher=fetcher, extractor=extractor,
            output_root=str(tmp_path / "direct"), observed_at="2026-07-17",
            created_at="2026-07-17T00:00:00+00:00")

        manifest = _manifest_with_batch_id("parity-multi")
        state = _run(manifest, tmp_path / "batch", selected_job_ids=("land-grant",))
        js = next(j for j in state.jobs if j.job_id == "land-grant")
        via_batch = candidate_from_dict(json.loads(Path(js.candidate_path).read_text(encoding="utf-8")))

        assert via_batch.proposed_fields == direct.proposed_fields
        assert via_batch.recommendation == direct.recommendation
        assert [s.source_id for s in via_batch.sources] == [s.source_id for s in direct.sources]
        assert via_batch.aggregation_version == direct.aggregation_version == C.AGGREGATION_VERSION

    def test_candidate_and_report_persist_at_existing_paths_not_under_batches(self, tmp_path):
        manifest = _manifest_with_batch_id("parity-paths")
        state = _run(manifest, tmp_path)
        js = next(j for j in state.jobs if j.job_id == "drury-dublin")
        candidate_path = Path(js.candidate_path)
        report_path = Path(js.report_path)
        assert candidate_path.parent == tmp_path / C.CANDIDATES_SUBDIR
        assert report_path.parent == tmp_path / C.REPORTS_SUBDIR
        assert candidate_path.exists()
        assert report_path.exists()


# --------------------------------------------------------------------------- #
# Batch directory layout and manifest-order persistence.
# --------------------------------------------------------------------------- #

class TestBatchDirectoryLayout:
    def test_state_summary_manifest_written_under_batches_batch_id(self, tmp_path):
        manifest = _manifest_with_batch_id("layout-test")
        _run(manifest, tmp_path)
        batch_dir = tmp_path / C.BATCHES_SUBDIR / "layout-test"
        assert (batch_dir / "manifest.json").exists()
        assert (batch_dir / "state.json").exists()
        assert (batch_dir / "summary.json").exists()

    def test_state_and_summary_job_order_matches_manifest_order(self, tmp_path):
        manifest = _manifest_with_batch_id("order-test")
        state = _run(manifest, tmp_path)
        assert [j.job_id for j in state.jobs] == [
            "drury-dublin", "scioto-audubon", "land-grant"]
        summary = build_batch_summary(state, manifest)
        assert [j["job_id"] for j in summary["jobs"]] == [
            "drury-dublin", "scioto-audubon", "land-grant"]


# --------------------------------------------------------------------------- #
# Mixed READY/REVIEW/REJECT outcomes in one batch.
# --------------------------------------------------------------------------- #

class TestMixedOutcomes:
    def test_ready_review_reject_all_persist_correctly_in_one_batch(self, tmp_path):
        jobs = (
            BatchJob(job_id="ready-job", candidate_name="Ready Hotel", category="hotels",
                    expected_city="Columbus", expected_state="OH",
                    urls=("https://www.druryhotels.test/polaris",),
                    source_relationship_hint="EXACT_ENTITY_DOMAIN",
                    static_fixtures=("tests/pettripfinder/importer/fixtures/hotel_01_strong.json",)),
            BatchJob(job_id="review-job", candidate_name="Review Hotel", category="hotels",
                    expected_city="Columbus", expected_state="OH",
                    urls=("https://www.conflicthotel.test/pets",),
                    source_relationship_hint="EXACT_ENTITY_DOMAIN",
                    static_fixtures=("tests/pettripfinder/importer/fixtures/hotel_04_conflict.json",)),
            BatchJob(job_id="reject-job", candidate_name="Reject Hotel", category="hotels",
                    expected_city="Columbus", expected_state="OH",
                    urls=("https://www.nopetshotel.test/policy",),
                    source_relationship_hint="EXACT_ENTITY_DOMAIN",
                    static_fixtures=("tests/pettripfinder/importer/fixtures/hotel_03_no_pets.json",)),
        )
        manifest = BatchManifest(
            manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="mixed-outcomes",
            batch_name="mixed", defaults={}, jobs=jobs)
        state = _run(manifest, tmp_path)
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["ready-job"].recommendation == C.RECOMMEND_READY
        assert by_id["review-job"].recommendation == C.RECOMMEND_REVIEW
        assert by_id["reject-job"].recommendation == C.RECOMMEND_REJECT
        assert all(j.execution_state == JOB_DONE for j in state.jobs)

        summary = build_batch_summary(state, manifest)
        assert summary["totals"] == {
            "jobs": 3, "done": 3, "failed": 0, "pending": 0, "running": 0,
            "disabled": 0, "ready": 1, "review": 1, "reject": 1,
        }


# --------------------------------------------------------------------------- #
# source_outcomes / snapshot_hashes correctness.
# --------------------------------------------------------------------------- #

class TestSourceOutcomesAndSnapshotHashes:
    def test_single_source_job_has_empty_source_outcomes_one_snapshot_hash(self, tmp_path):
        manifest = _manifest_with_batch_id("outcomes-single")
        state = _run(manifest, tmp_path, selected_job_ids=("drury-dublin",))
        js = next(j for j in state.jobs if j.job_id == "drury-dublin")
        assert js.source_outcomes == ()
        assert len(js.snapshot_hashes) == 1

    def test_multi_source_job_has_two_included_source_outcomes(self, tmp_path):
        manifest = _manifest_with_batch_id("outcomes-multi")
        state = _run(manifest, tmp_path, selected_job_ids=("land-grant",))
        js = next(j for j in state.jobs if j.job_id == "land-grant")
        assert len(js.source_outcomes) == 2
        assert [o[2] for o in js.source_outcomes] == ["included", "included"]
        assert [o[0] for o in js.source_outcomes] == ["S1", "S2"]
        assert len(js.snapshot_hashes) == 2


# --------------------------------------------------------------------------- #
# Failure isolation: one job's exception never stops the batch.
# --------------------------------------------------------------------------- #

class TestFailureIsolation:
    def test_one_job_exception_does_not_stop_the_batch(self, tmp_path):
        def fetcher_factory(job):
            if job.job_id == "scioto-audubon":
                raise RuntimeError("simulated fetch failure")
            fetcher, _ = _build_static(job.urls[0],
                                       str(_REPO_ROOT / job.static_fixtures[0]))
            return fetcher

        def extractor_factory(job):
            _, extractor = _build_static(job.urls[0],
                                         str(_REPO_ROOT / job.static_fixtures[0]))
            return extractor

        manifest = _manifest_with_batch_id("failure-isolation")
        state = _run(manifest, tmp_path, fetcher_factory=fetcher_factory,
                    extractor_factory=extractor_factory)
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["drury-dublin"].execution_state == JOB_DONE
        assert by_id["scioto-audubon"].execution_state == JOB_FAILED
        assert by_id["scioto-audubon"].error_type == "RuntimeError"
        assert "simulated fetch failure" in by_id["scioto-audubon"].error_message
        assert by_id["land-grant"].execution_state == JOB_DONE

    def test_failed_job_summary_totals_reflect_failure(self, tmp_path):
        def fetcher_factory(job):
            raise RuntimeError("always fails")

        job = BatchJob(job_id="only-job", candidate_name="X", category="hotels",
                       expected_city="Columbus", expected_state="OH",
                       urls=(_DRURY_URL,), static_fixtures=(_DRURY_FIXTURE,))
        manifest = _one_job_manifest("failure-totals", job)
        state = _run(manifest, tmp_path, fetcher_factory=fetcher_factory,
                    extractor_factory=lambda j: None)
        summary = build_batch_summary(state, manifest)
        assert summary["totals"]["failed"] == 1
        assert summary["totals"]["done"] == 0

    def test_run_batch_never_raises_a_plain_job_exception(self, tmp_path):
        """A RuntimeError from inside one job's execution must be caught and
        recorded as FAILED -- never propagated out of run_batch itself
        (only KeyboardInterrupt/BatchRunError propagate)."""
        job = BatchJob(job_id="only-job", candidate_name="X", category="hotels",
                       expected_city="Columbus", expected_state="OH",
                       urls=(_DRURY_URL,), static_fixtures=(_DRURY_FIXTURE,))
        manifest = _one_job_manifest("no-raise-test", job)
        state = _run(manifest, tmp_path, fetcher_factory=lambda j: (_ for _ in ()).throw(
            ValueError("boom")), extractor_factory=lambda j: None)
        assert state.jobs[0].execution_state == JOB_FAILED
        assert state.jobs[0].error_type == "ValueError"


# --------------------------------------------------------------------------- #
# KeyboardInterrupt: never swallowed; interrupted job never left/marked DONE.
# --------------------------------------------------------------------------- #

class TestKeyboardInterrupt:
    def test_interrupt_during_job_converts_running_to_failed_and_reraises(self, tmp_path):
        def fetcher_factory(job):
            if job.job_id == "scioto-audubon":
                raise KeyboardInterrupt()
            fetcher, _ = _build_static(job.urls[0],
                                       str(_REPO_ROOT / job.static_fixtures[0]))
            return fetcher

        def extractor_factory(job):
            _, extractor = _build_static(job.urls[0],
                                         str(_REPO_ROOT / job.static_fixtures[0]))
            return extractor

        manifest = _manifest_with_batch_id("interrupt-test")
        with pytest.raises(KeyboardInterrupt):
            _run(manifest, tmp_path, fetcher_factory=fetcher_factory,
                extractor_factory=extractor_factory)

        from scripts.pettripfinder.importer.batch import load_batch_state
        state = load_batch_state(
            tmp_path / C.BATCHES_SUBDIR / "interrupt-test" / "state.json")
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["drury-dublin"].execution_state == JOB_DONE
        assert by_id["scioto-audubon"].execution_state == JOB_FAILED
        assert by_id["scioto-audubon"].error_type == "KeyboardInterrupt"
        assert by_id["scioto-audubon"].last_action == "failed"
        # never attempted -- manifest-order jobs after the interrupt point
        # must not have been touched.
        assert by_id["land-grant"].execution_state == JOB_PENDING

    def test_interrupt_before_any_job_running_reraises_without_marking_anything_failed(
        self, tmp_path,
    ):
        def fetcher_factory(job):
            raise KeyboardInterrupt()

        job = BatchJob(job_id="only-job", candidate_name="X", category="hotels",
                       expected_city="Columbus", expected_state="OH",
                       urls=(_DRURY_URL,), static_fixtures=(_DRURY_FIXTURE,))
        manifest = _one_job_manifest("interrupt-first-job", job)
        with pytest.raises(KeyboardInterrupt):
            _run(manifest, tmp_path, fetcher_factory=fetcher_factory,
                extractor_factory=lambda j: None)

        from scripts.pettripfinder.importer.batch import load_batch_state
        state = load_batch_state(
            tmp_path / C.BATCHES_SUBDIR / "interrupt-first-job" / "state.json")
        assert state.jobs[0].execution_state == JOB_FAILED
        assert state.jobs[0].error_type == "KeyboardInterrupt"


# --------------------------------------------------------------------------- #
# No production mutation: batch execution never writes outside output_root.
# --------------------------------------------------------------------------- #

class TestNoProductionMutation:
    def test_production_seed_csv_untouched_by_batch_execution(self, tmp_path):
        seed_csv = _REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
        before = seed_csv.read_bytes()
        manifest = _manifest_with_batch_id("no-prod-mutation")
        _run(manifest, tmp_path)
        after = seed_csv.read_bytes()
        assert before == after
