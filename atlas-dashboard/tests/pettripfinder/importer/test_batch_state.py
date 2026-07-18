"""AES-WORK-001B -- batch execution state: JobState/BatchState contracts,
their serialization, and the atomic JSON writer. No fetch, no extraction,
no provider call -- pure contracts and filesystem behavior. No network."""

from __future__ import annotations

import json
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
    BatchState,
    BatchStateError,
    JobState,
    _atomic_write_json,
    batch_state_from_dict,
    batch_state_to_dict,
    dump_batch_state,
    load_batch_state,
    write_batch_state,
    write_batch_summary,
    write_manifest_snapshot,
)


def _sample_job_state(**overrides) -> JobState:
    kwargs = dict(
        job_id="drury-dublin", fingerprint="abc123", execution_state=JOB_DONE,
        last_action="ran", recommendation=C.RECOMMEND_READY,
        recommendation_reasons=(), candidate_id="cand-1",
        candidate_path="/out/candidates/cand-1.json",
        report_path="/out/reports/cand-1.html", run_id="2026-07-17T00:00:00+00:00",
        source_outcomes=(("S1", "PRIMARY", "included"),),
        snapshot_hashes=("deadbeef",), provider="static", model="static-fixture",
        prompt_version="1.0.0",
    )
    kwargs.update(overrides)
    return JobState(**kwargs)


def _sample_batch_state(**overrides) -> BatchState:
    kwargs = dict(
        batch_state_version=C.BATCH_STATE_VERSION, batch_id="columbus-wave-1",
        manifest_hash="deadbeef" * 8, manifest_schema_version="1.0",
        extractor="static", model=C.DEFAULT_ANTHROPIC_MODEL, observed_at="2026-07-17",
        jobs=(_sample_job_state(),),
    )
    kwargs.update(overrides)
    return BatchState(**kwargs)


# --------------------------------------------------------------------------- #
# JobState / BatchState round-trip serialization.
# --------------------------------------------------------------------------- #

class TestSerializationRoundTrip:
    def test_job_state_round_trips_through_batch_state_dict(self):
        state = _sample_batch_state()
        d = batch_state_to_dict(state)
        restored = batch_state_from_dict(d)
        assert restored == state

    def test_tuples_round_trip_as_lists_in_json_and_back_to_tuples(self):
        state = _sample_batch_state()
        d = batch_state_to_dict(state)
        assert isinstance(d["jobs"][0]["source_outcomes"], list)
        assert isinstance(d["jobs"][0]["source_outcomes"][0], list)
        restored = batch_state_from_dict(d)
        assert restored.jobs[0].source_outcomes == (("S1", "PRIMARY", "included"),)
        assert isinstance(restored.jobs[0].source_outcomes, tuple)
        assert restored.jobs[0].snapshot_hashes == ("deadbeef",)

    def test_optional_fields_default_when_absent_from_stored_dict(self):
        minimal = {
            "job_id": "j1", "fingerprint": "fp1", "execution_state": JOB_PENDING,
        }
        d = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "b1",
            "manifest_hash": "h1", "manifest_schema_version": "1.0",
            "extractor": "static", "model": "m1", "observed_at": "2026-07-17",
            "jobs": [minimal],
        }
        state = batch_state_from_dict(d)
        js = state.jobs[0]
        assert js.last_action == ""
        assert js.recommendation == ""
        assert js.recommendation_reasons == ()
        assert js.candidate_path == ""
        assert js.source_outcomes == ()
        assert js.snapshot_hashes == ()

    def test_batch_state_to_dict_key_set_is_exact(self):
        """Guards the persisted schema against silent drift."""
        d = batch_state_to_dict(_sample_batch_state())
        assert set(d.keys()) == {
            "batch_state_version", "batch_id", "manifest_hash",
            "manifest_schema_version", "extractor", "model", "observed_at", "jobs",
        }
        job_d = d["jobs"][0]
        assert set(job_d.keys()) == {
            "job_id", "fingerprint", "execution_state", "last_action",
            "recommendation", "recommendation_reasons", "candidate_id",
            "candidate_path", "report_path", "run_id", "skip_reason",
            "error_type", "error_message", "source_outcomes", "snapshot_hashes",
            "provider", "model", "prompt_version",
        }

    def test_dump_batch_state_is_sorted_key_deterministic_json(self):
        state = _sample_batch_state()
        text1 = dump_batch_state(state)
        text2 = dump_batch_state(state)
        assert text1 == text2
        parsed = json.loads(text1)
        assert list(parsed.keys()) == sorted(parsed.keys())


# --------------------------------------------------------------------------- #
# Rejection of malformed / unrecognized persisted state.
# --------------------------------------------------------------------------- #

class TestMalformedStateRejected:
    def test_unrecognized_execution_state_rejected(self):
        d = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "b1",
            "manifest_hash": "h1", "manifest_schema_version": "1.0",
            "extractor": "static", "model": "m1", "observed_at": "2026-07-17",
            "jobs": [{"job_id": "j1", "fingerprint": "fp1", "execution_state": "BOGUS"}],
        }
        with pytest.raises(BatchStateError, match="unrecognized execution_state"):
            batch_state_from_dict(d)

    def test_missing_required_job_key_rejected(self):
        d = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "b1",
            "manifest_hash": "h1", "manifest_schema_version": "1.0",
            "extractor": "static", "model": "m1", "observed_at": "2026-07-17",
            "jobs": [{"job_id": "j1", "fingerprint": "fp1"}],   # missing execution_state
        }
        with pytest.raises(BatchStateError, match="missing required key"):
            batch_state_from_dict(d)

    def test_missing_required_batch_key_rejected(self):
        d = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "b1",
            "manifest_hash": "h1", "manifest_schema_version": "1.0",
            "extractor": "static", "jobs": [],
            # missing "model" and "observed_at"
        }
        with pytest.raises(BatchStateError, match="missing required key"):
            batch_state_from_dict(d)

    def test_jobs_not_a_list_rejected(self):
        d = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "b1",
            "manifest_hash": "h1", "manifest_schema_version": "1.0",
            "extractor": "static", "model": "m1", "observed_at": "2026-07-17",
            "jobs": "not-a-list",
        }
        with pytest.raises(BatchStateError, match="'jobs' must be a list"):
            batch_state_from_dict(d)

    def test_non_dict_top_level_rejected(self):
        with pytest.raises(BatchStateError, match="must be a JSON object"):
            batch_state_from_dict(["not", "a", "dict"])

    def test_non_dict_job_entry_rejected(self):
        d = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "b1",
            "manifest_hash": "h1", "manifest_schema_version": "1.0",
            "extractor": "static", "model": "m1", "observed_at": "2026-07-17",
            "jobs": ["not-a-dict"],
        }
        with pytest.raises(BatchStateError, match="must be a JSON object"):
            batch_state_from_dict(d)

    def test_malformed_json_on_disk_rejected(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(BatchStateError, match="not valid JSON"):
            load_batch_state(path)


# --------------------------------------------------------------------------- #
# load_batch_state / write_batch_state real-file round-trip.
# --------------------------------------------------------------------------- #

class TestFileRoundTrip:
    def test_write_then_load_batch_state_round_trips(self, tmp_path):
        state = _sample_batch_state()
        path = write_batch_state(state, tmp_path)
        assert path == tmp_path / "state.json"
        assert path.exists()
        reloaded = load_batch_state(path)
        assert reloaded == state

    def test_write_batch_summary_produces_valid_json_at_expected_path(self, tmp_path):
        summary = {"batch_id": "columbus-wave-1", "totals": {"done": 1}}
        path = write_batch_summary(summary, tmp_path)
        assert path == tmp_path / "summary.json"
        assert json.loads(path.read_text(encoding="utf-8")) == summary

    def test_write_manifest_snapshot_includes_inline_manifest_hash(self, tmp_path):
        from scripts.pettripfinder.importer.batch import load_manifest, compute_manifest_hash
        fixture = (Path(__file__).parent / "fixtures" / "batches"
                  / "columbus_wave_1.json")
        manifest = load_manifest(fixture)
        path = write_manifest_snapshot(manifest, tmp_path)
        assert path == tmp_path / "manifest.json"
        d = json.loads(path.read_text(encoding="utf-8"))
        assert d["manifest_hash"] == compute_manifest_hash(manifest)
        assert d["batch_id"] == "columbus-wave-1"
        assert [j["job_id"] for j in d["jobs"]] == [
            "drury-dublin", "scioto-audubon", "land-grant"]


# --------------------------------------------------------------------------- #
# Atomic JSON writer: same-directory tempfile + os.replace; never leaves a
# partial/corrupt target; never leaks an abandoned temp file on failure.
# --------------------------------------------------------------------------- #

class TestAtomicWriter:
    def test_creates_parent_directory(self, tmp_path):
        target = tmp_path / "nested" / "dir" / "state.json"
        _atomic_write_json(target, {"a": 1})
        assert target.exists()
        assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}

    def test_no_leftover_temp_files_on_success(self, tmp_path):
        _atomic_write_json(tmp_path / "state.json", {"a": 1})
        names = sorted(p.name for p in tmp_path.iterdir())
        assert names == ["state.json"]

    def test_prior_file_untouched_when_replace_fails(self, tmp_path, monkeypatch):
        target = tmp_path / "state.json"
        _atomic_write_json(target, {"version": 1})
        original_bytes = target.read_bytes()

        def _boom(*args, **kwargs):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(os, "replace", _boom)
        with pytest.raises(OSError, match="simulated replace failure"):
            _atomic_write_json(target, {"version": 2})

        assert target.read_bytes() == original_bytes   # untouched
        leftover = [p for p in tmp_path.iterdir() if p.name != "state.json"]
        assert leftover == []   # abandoned temp file cleaned up

    def test_write_is_sorted_key_indented_json_with_trailing_newline(self, tmp_path):
        target = tmp_path / "state.json"
        _atomic_write_json(target, {"b": 2, "a": 1})
        text = target.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.index('"a"') < text.index('"b"')

    def test_repeated_writes_produce_byte_identical_output(self, tmp_path):
        target = tmp_path / "state.json"
        payload = {"jobs": [{"id": "x"}], "totals": {"done": 1}}
        _atomic_write_json(target, payload)
        bytes1 = target.read_bytes()
        _atomic_write_json(target, payload)
        bytes2 = target.read_bytes()
        assert bytes1 == bytes2
