"""AES-WORK-001C -- bounded concurrency: ThreadPoolExecutor-backed
max_workers>1 execution, per-registrable-domain locking, thread-safe state
coordination, interruption under concurrency, and failure isolation.
Static fixtures only -- no network.

Concurrency proofs use ``threading.Barrier`` rendezvous, never wall-clock
sleep+interval overlap detection: this environment's atomic state/summary/
report writes (same-directory tempfile + fsync) can take anywhere from
~0.1s to several seconds depending on machine load, which would make any
short sleep-based "did these two windows overlap" check flaky. A barrier
is immune to that -- it only ever releases once ALL parties have
genuinely arrived concurrently, and a bounded timeout turns "did NOT
overlap" into a fast, deterministic, non-hanging assertion too.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.batch import (
    JOB_DONE,
    JOB_FAILED,
    JOB_PENDING,
    JOB_RUNNING,
    BatchJob,
    BatchManifest,
    load_batch_state,
    run_batch,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CLOCK = lambda: "2026-07-18T00:00:00+00:00"   # noqa: E731 -- test-only fixed clock

_HOTEL_FIXTURE = "tests/pettripfinder/importer/fixtures/hotel_01_strong.json"
_PARK_A_FIXTURE = "tests/pettripfinder/importer/fixtures/park_01_offleash.json"
_PARK_B_FIXTURE = "tests/pettripfinder/importer/fixtures/park_02_onleash.json"
_RESTAURANT_FIXTURE = "tests/pettripfinder/importer/fixtures/restaurant_01_patio.json"
_FAQ_FIXTURE = "tests/pettripfinder/importer/fixtures/aggregate_landgrant_faq.json"
_CONTACT_FIXTURE = "tests/pettripfinder/importer/fixtures/aggregate_landgrant_contact.json"


def _job(job_id, category, url, fixture, **overrides) -> BatchJob:
    kwargs = dict(
        job_id=job_id, candidate_name=job_id, category=category,
        expected_city="Columbus", expected_state="OH", urls=(url,),
        static_fixtures=(fixture,))
    kwargs.update(overrides)
    return BatchJob(**kwargs)


def _manifest(batch_id: str, jobs) -> BatchManifest:
    return BatchManifest(
        manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id=batch_id,
        batch_name=batch_id, defaults={}, jobs=tuple(jobs))


def _build(job: BatchJob):
    from scripts.import_official_url import _build_static
    from scripts.import_official_urls import _build_static_multi
    if len(job.urls) == 1:
        return _build_static(job.urls[0], str(_REPO_ROOT / job.static_fixtures[0]))
    return _build_static_multi(
        list(job.urls), [str(_REPO_ROOT / f) for f in job.static_fixtures])


def _run(manifest, output_root, **overrides):
    kwargs = dict(
        extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
        output_root=str(output_root), observed_at="2026-07-18",
        repo_root=_REPO_ROOT, clock=_CLOCK)
    kwargs.update(overrides)
    return run_batch(manifest, **kwargs)


def _run_with_timeout(manifest, output_root, timeout=15.0, **overrides):
    """Runs run_batch on a background thread and asserts it actually
    returns within ``timeout`` -- converts a hypothetical deadlock into a
    clean test failure instead of hanging the whole suite."""
    result = {}

    def _target():
        try:
            result["state"] = _run(manifest, output_root, **overrides)
        except BaseException as exc:   # noqa: BLE001 -- captured, re-raised below
            result["exc"] = exc

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout)
    assert not t.is_alive(), "run_batch did not return within %.1fs -- possible deadlock" % timeout
    if "exc" in result:
        raise result["exc"]
    return result["state"]


# --------------------------------------------------------------------------- #
# max_workers=1 parity with WORK-001B; max_workers>1 equivalence.
# --------------------------------------------------------------------------- #

class TestParityWithSequential:
    def test_max_workers_1_still_runs_every_job_sequentially(self, tmp_path):
        jobs = [
            _job("a", "hotels", "https://a.test", _HOTEL_FIXTURE),
            _job("b", "parks", "https://b.test", _PARK_A_FIXTURE),
        ]
        state = _run(_manifest("parity-1", jobs), tmp_path, max_workers=1)
        assert [j.job_id for j in state.jobs] == ["a", "b"]
        assert all(j.execution_state == JOB_DONE for j in state.jobs)

    def test_max_workers_1_and_3_produce_equivalent_recommendations_and_order(self, tmp_path):
        jobs = [
            _job("a", "hotels", "https://a.test", _HOTEL_FIXTURE),
            _job("b", "parks", "https://b.test", _PARK_A_FIXTURE),
            _job("c", "restaurants", "https://c.test", _RESTAURANT_FIXTURE),
        ]
        state1 = _run(_manifest("parity-seq", jobs), tmp_path / "seq", max_workers=1)
        state3 = _run(_manifest("parity-conc", jobs), tmp_path / "conc", max_workers=3)

        assert [j.job_id for j in state1.jobs] == [j.job_id for j in state3.jobs] == ["a", "b", "c"]
        for j1, j3 in zip(state1.jobs, state3.jobs):
            assert j1.job_id == j3.job_id
            assert j1.execution_state == j3.execution_state == JOB_DONE
            assert j1.recommendation == j3.recommendation
            assert j1.recommendation_reasons == j3.recommendation_reasons

    def test_max_workers_out_of_range_rejected_before_any_disk_write(self, tmp_path):
        jobs = [_job("a", "hotels", "https://a.test", _HOTEL_FIXTURE)]
        from scripts.pettripfinder.importer.batch import BatchRunError
        with pytest.raises(BatchRunError, match="max_workers"):
            _run(_manifest("bad-workers", jobs), tmp_path, max_workers=99)
        assert not (tmp_path / C.BATCHES_SUBDIR).exists()


# --------------------------------------------------------------------------- #
# Real concurrency: a barrier proves N independent-domain jobs genuinely
# overlap; a lock-protected running-max counter proves the pool never
# exceeds max_workers.
# --------------------------------------------------------------------------- #

class TestConcurrencyHappens:
    def test_three_independent_domain_jobs_overlap_with_max_workers_3(self, tmp_path):
        jobs = [
            _job("a", "hotels", "https://www.druryhotels.test/x", _HOTEL_FIXTURE),
            _job("b", "parks", "https://www.metroparks.net/x", _PARK_A_FIXTURE),
            _job("c", "restaurants", "https://www.somerestaurant.test/x", _RESTAURANT_FIXTURE),
        ]
        barrier = threading.Barrier(3, timeout=10)

        def fetcher_factory(job):
            fetcher, _extractor = _build(job)
            orig_fetch = fetcher.fetch

            def _wrapped(url):
                barrier.wait()   # only satisfiable if all 3 are truly concurrent
                return orig_fetch(url)

            fetcher.fetch = _wrapped
            return fetcher

        def extractor_factory(job):
            _fetcher, extractor = _build(job)
            return extractor

        state = _run(
            _manifest("three-way-overlap", jobs), tmp_path, max_workers=3,
            fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
        assert all(j.execution_state == JOB_DONE for j in state.jobs)

    def test_max_observed_concurrency_never_exceeds_max_workers(self, tmp_path):
        jobs = [
            _job("a", "hotels", "https://www.druryhotels.test/x", _HOTEL_FIXTURE),
            _job("b", "parks", "https://www.metroparks.net/x", _PARK_A_FIXTURE),
            _job("c", "restaurants", "https://www.somerestaurant.test/x", _RESTAURANT_FIXTURE),
        ]
        current = {"n": 0, "max": 0}
        lock = threading.Lock()
        release = threading.Event()

        def fetcher_factory(job):
            fetcher, _extractor = _build(job)
            orig_fetch = fetcher.fetch

            def _wrapped(url):
                with lock:
                    current["n"] += 1
                    current["max"] = max(current["max"], current["n"])
                release.wait(timeout=5)   # hold briefly so overlap is observable
                with lock:
                    current["n"] -= 1
                return orig_fetch(url)

            fetcher.fetch = _wrapped
            return fetcher

        def extractor_factory(job):
            _fetcher, extractor = _build(job)
            return extractor

        def _release_soon():
            import time
            time.sleep(0.3)
            release.set()

        threading.Thread(target=_release_soon, daemon=True).start()
        state = _run(
            _manifest("bounded-concurrency", jobs), tmp_path, max_workers=2,
            fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
        assert all(j.execution_state == JOB_DONE for j in state.jobs)
        assert current["max"] <= 2
        assert current["max"] >= 2, "expected at least 2-way concurrency to be observed"


# --------------------------------------------------------------------------- #
# Domain locking: same-domain serializes, cross-domain overlaps, a
# multi-source job's own sources stay sequential, no deadlock with
# overlapping domain sets across jobs.
# --------------------------------------------------------------------------- #

class TestDomainLocking:
    def test_same_domain_jobs_never_run_concurrently(self, tmp_path):
        jobs = [
            _job("park-a", "parks", "https://www.metroparks.net/a", _PARK_A_FIXTURE),
            _job("park-b", "parks", "https://www.metroparks.net/b", _PARK_B_FIXTURE),
        ]
        barrier = threading.Barrier(2, timeout=1.5)
        satisfied = {"value": False}

        def fetcher_factory(job):
            fetcher, _extractor = _build(job)
            orig_fetch = fetcher.fetch

            def _wrapped(url):
                try:
                    barrier.wait()
                    satisfied["value"] = True   # would mean BOTH ran concurrently
                except threading.BrokenBarrierError:
                    pass   # expected: the domain lock kept them apart
                return orig_fetch(url)

            fetcher.fetch = _wrapped
            return fetcher

        def extractor_factory(job):
            _fetcher, extractor = _build(job)
            return extractor

        state = _run(
            _manifest("same-domain-serialize", jobs), tmp_path, max_workers=2,
            fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
        assert all(j.execution_state == JOB_DONE for j in state.jobs)
        assert not satisfied["value"], "same-registrable-domain jobs must never overlap"

    def test_cross_domain_jobs_may_overlap(self, tmp_path):
        jobs = [
            _job("hotel-a", "hotels", "https://www.druryhotels.test/a", _HOTEL_FIXTURE),
            _job("park-a", "parks", "https://www.metroparks.net/a", _PARK_A_FIXTURE),
        ]
        barrier = threading.Barrier(2, timeout=10)

        def fetcher_factory(job):
            fetcher, _extractor = _build(job)
            orig_fetch = fetcher.fetch

            def _wrapped(url):
                barrier.wait()   # only satisfiable if genuinely concurrent
                return orig_fetch(url)

            fetcher.fetch = _wrapped
            return fetcher

        def extractor_factory(job):
            _fetcher, extractor = _build(job)
            return extractor

        state = _run(
            _manifest("cross-domain-overlap", jobs), tmp_path, max_workers=2,
            fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
        assert all(j.execution_state == JOB_DONE for j in state.jobs)

    def test_multi_source_job_own_sources_stay_sequential(self, tmp_path):
        """Both URLs of ONE job are on the same domain -- Task 1's "never
        parallelize sources within a job" plus Task 2's dedup-before-lock
        both guarantee this; a self-deadlock (acquiring the same
        non-reentrant lock twice) would hang, which _run_with_timeout
        converts into a clean failure instead."""
        job = _job("land-grant", "restaurants", "https://landgrantbrewing.com/faq/",
                   _FAQ_FIXTURE, urls=("https://landgrantbrewing.com/faq/",
                                       "https://landgrantbrewing.com/taproom/"),
                   static_fixtures=(_FAQ_FIXTURE, _CONTACT_FIXTURE))
        order = []
        order_lock = threading.Lock()

        def fetcher_factory(j):
            fetcher, _extractor = _build(j)
            orig_fetch = fetcher.fetch

            def _wrapped(url):
                with order_lock:
                    order.append(("start", url))
                result = orig_fetch(url)
                with order_lock:
                    order.append(("end", url))
                return result

            fetcher.fetch = _wrapped
            return fetcher

        def extractor_factory(j):
            _fetcher, extractor = _build(j)
            return extractor

        state = _run_with_timeout(
            _manifest("multi-source-sequential", [job]), tmp_path, max_workers=3,
            fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
        assert state.jobs[0].execution_state == JOB_DONE
        # Strictly alternating start/end pairs -- never two starts in a row.
        assert order[0][0] == "start" and order[1][0] == "end"
        assert order[2][0] == "start" and order[3][0] == "end"

    def test_no_deadlock_with_overlapping_domain_sets(self, tmp_path):
        """job-xy touches domains {x, y}; job-yz touches {y, z} -- a naive
        unordered lock-acquisition scheme could deadlock (xy holds x, wants
        y; yz holds z, wants y -- no, the classic case is xy holds x then
        wants y while ANOTHER thread holds y then wants x). The sorted-
        acquisition-order design (Task 2) prevents this by construction;
        _run_with_timeout converts a regression back to that into a clean
        failure instead of hanging the test suite."""
        job_xy = _job(
            "job-xy", "restaurants", "https://x.test/1", _FAQ_FIXTURE,
            urls=("https://x.test/1", "https://y.test/1"),
            static_fixtures=(_FAQ_FIXTURE, _CONTACT_FIXTURE))
        job_yz = _job(
            "job-yz", "restaurants", "https://y.test/2", _FAQ_FIXTURE,
            urls=("https://y.test/2", "https://z.test/2"),
            static_fixtures=(_FAQ_FIXTURE, _CONTACT_FIXTURE))
        state = _run_with_timeout(
            _manifest("overlapping-domains", [job_xy, job_yz]), tmp_path, max_workers=2)
        assert all(j.execution_state == JOB_DONE for j in state.jobs)


# --------------------------------------------------------------------------- #
# Failure isolation under concurrency.
# --------------------------------------------------------------------------- #

class TestConcurrencyFailureIsolation:
    def test_one_worker_exception_does_not_stop_the_batch(self, tmp_path):
        jobs = [
            _job("ok-a", "hotels", "https://a.test", _HOTEL_FIXTURE),
            _job("bad-b", "parks", "https://b.test", _PARK_A_FIXTURE),
            _job("ok-c", "restaurants", "https://c.test", _RESTAURANT_FIXTURE),
        ]

        def fetcher_factory(job):
            if job.job_id == "bad-b":
                raise RuntimeError("simulated concurrent failure")
            fetcher, _extractor = _build(job)
            return fetcher

        def extractor_factory(job):
            _fetcher, extractor = _build(job)
            return extractor

        state = _run(
            _manifest("concurrent-failure-isolation", jobs), tmp_path, max_workers=3,
            fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["ok-a"].execution_state == JOB_DONE
        assert by_id["bad-b"].execution_state == JOB_FAILED
        assert by_id["bad-b"].error_type == "RuntimeError"
        assert by_id["ok-c"].execution_state == JOB_DONE

    def test_domain_lock_released_after_failure(self, tmp_path):
        """Two same-domain jobs; the first fails INSIDE the domain-locked
        region -- the second must still be able to acquire the lock and
        run (never left permanently held)."""
        jobs = [
            _job("bad-a", "parks", "https://www.metroparks.net/a", _PARK_A_FIXTURE),
            _job("ok-b", "parks", "https://www.metroparks.net/b", _PARK_B_FIXTURE),
        ]

        def fetcher_factory(job):
            if job.job_id == "bad-a":
                raise RuntimeError("fails while holding the domain lock")
            fetcher, _extractor = _build(job)
            return fetcher

        def extractor_factory(job):
            _fetcher, extractor = _build(job)
            return extractor

        state = _run_with_timeout(
            _manifest("domain-lock-release-on-failure", jobs), tmp_path, max_workers=2,
            fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["bad-a"].execution_state == JOB_FAILED
        assert by_id["ok-b"].execution_state == JOB_DONE


# --------------------------------------------------------------------------- #
# Interruption under concurrency.
# --------------------------------------------------------------------------- #

class TestConcurrencyInterruption:
    def test_interrupt_never_swallowed_no_job_left_running(self, tmp_path):
        jobs = [
            _job("ok-x", "hotels", "https://x.test", _HOTEL_FIXTURE),
            _job("interrupt-y", "parks", "https://y.test", _PARK_A_FIXTURE),
        ]

        def fetcher_factory(job):
            if job.job_id == "interrupt-y":
                raise KeyboardInterrupt()
            fetcher, _extractor = _build(job)
            return fetcher

        def extractor_factory(job):
            _fetcher, extractor = _build(job)
            return extractor

        with pytest.raises(KeyboardInterrupt):
            _run(
                _manifest("concurrent-interrupt", jobs), tmp_path, max_workers=2,
                fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)

        state = load_batch_state(
            tmp_path / C.BATCHES_SUBDIR / "concurrent-interrupt" / "state.json")
        by_id = {j.job_id: j for j in state.jobs}
        assert by_id["interrupt-y"].execution_state == JOB_FAILED
        assert by_id["interrupt-y"].error_type == "KeyboardInterrupt"
        # ok-x may have finished, been cancelled before starting, or been
        # swept from RUNNING -- all are correct; it must simply never be
        # left RUNNING, and if swept, must be tagged KeyboardInterrupt.
        assert by_id["ok-x"].execution_state in (JOB_DONE, JOB_PENDING, JOB_FAILED)
        if by_id["ok-x"].execution_state == JOB_FAILED:
            assert by_id["ok-x"].error_type == "KeyboardInterrupt"
        assert all(j.execution_state != JOB_RUNNING for j in state.jobs)

    def test_interrupted_batch_is_resumable(self, tmp_path):
        jobs = [
            _job("ok-x", "hotels", "https://x.test", _HOTEL_FIXTURE),
            _job("interrupt-y", "parks", "https://y.test", _PARK_A_FIXTURE),
        ]

        def fetcher_factory(job):
            if job.job_id == "interrupt-y":
                raise KeyboardInterrupt()
            fetcher, _extractor = _build(job)
            return fetcher

        def extractor_factory(job):
            _fetcher, extractor = _build(job)
            return extractor

        manifest = _manifest("concurrent-interrupt-resume", jobs)
        with pytest.raises(KeyboardInterrupt):
            _run(manifest, tmp_path, max_workers=2,
                fetcher_factory=fetcher_factory, extractor_factory=extractor_factory)

        # Resume for real (no more injected interrupt) -- every non-DONE
        # job must be retried, and the batch must complete cleanly.
        state = _run(manifest, tmp_path, max_workers=2, resume=True)
        assert all(j.execution_state == JOB_DONE for j in state.jobs)
