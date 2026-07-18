"""AES-WORK-001A -- batch import queue contracts: manifest parsing,
fail-closed validation, stable batch identity, deterministic per-job
fingerprints, and the validate-only --dry-run CLI. No execution path
exists yet in this phase -- no fetch, no extraction, no provider call, no
candidate/state persistence. No network."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.batch import (
    BatchJob,
    BatchManifestError,
    compute_job_fingerprint,
    compute_manifest_hash,
    get_batch_id,
    load_manifest,
    validate_manifest,
)
from scripts.run_import_batch import main

_REPO_ROOT = Path(__file__).resolve().parents[3]
_STATIC_MANIFEST = Path(__file__).parent / "fixtures" / "batches" / "columbus_wave_1.json"

_DRURY_FIXTURE = "tests/pettripfinder/importer/fixtures/hotel_01_strong.json"
_SCIOTO_FIXTURE = "tests/pettripfinder/importer/fixtures/park_01_offleash.json"
_LANDGRANT_FAQ_FIXTURE = "tests/pettripfinder/importer/fixtures/aggregate_landgrant_faq.json"
_LANDGRANT_CONTACT_FIXTURE = "tests/pettripfinder/importer/fixtures/aggregate_landgrant_contact.json"


def _base_manifest_dict() -> dict:
    """The mission's exact three-job example: Drury (1 url), Scioto (1
    url), Land-Grant (2 urls) -- deep-copied by every caller so tests can
    freely mutate their own copy."""
    return {
        "manifest_schema_version": "1.0",
        "batch_id": "columbus-wave-1",
        "batch_name": "Columbus Wave 1",
        "defaults": {
            "expected_state": "OH",
            "source_relationship_hint": "EXACT_ENTITY_DOMAIN",
        },
        "jobs": [
            {
                "job_id": "drury-dublin",
                "candidate_name": "Drury Inn & Suites Columbus Dublin",
                "category": "hotels",
                "expected_city": "Dublin",
                "urls": ["https://www.druryhotels.com/locations/columbus-oh/"
                        "drury-inn-and-suites-columbus-dublin"],
                "static_fixtures": [_DRURY_FIXTURE],
            },
            {
                "job_id": "scioto-audubon",
                "candidate_name": "Scioto Audubon",
                "category": "parks",
                "expected_city": "Columbus",
                "urls": ["https://www.metroparks.net/parks-and-trails/scioto-audubon"],
                "static_fixtures": [_SCIOTO_FIXTURE],
            },
            {
                "job_id": "land-grant",
                "candidate_name": "Land-Grant Brewing Columbus",
                "category": "restaurants",
                "expected_city": "Columbus",
                "urls": [
                    "https://landgrantbrewing.com/faq/",
                    "https://landgrantbrewing.com/taproom/",
                ],
                "static_fixtures": [_LANDGRANT_FAQ_FIXTURE, _LANDGRANT_CONTACT_FIXTURE],
            },
        ],
    }


def _write_manifest(tmp_path: Path, data: dict, name: str = "manifest.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _job_kwargs(**overrides) -> dict:
    kwargs = dict(extractor="static", model=C.DEFAULT_ANTHROPIC_MODEL,
                  observed_at="2026-07-17", repo_root=_REPO_ROOT)
    kwargs.update(overrides)
    return kwargs


# --------------------------------------------------------------------------- #
# 1. Valid three-job manifest.
# --------------------------------------------------------------------------- #

class TestValidManifest:
    def test_three_job_manifest_validates_clean(self):
        """Uses the checked-in static fixture directly (not a tmp_path
        copy) -- the canonical example manifest."""
        manifest = load_manifest(_STATIC_MANIFEST)
        assert [j.job_id for j in manifest.jobs] == [
            "drury-dublin", "scioto-audubon", "land-grant"]
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert errors == ()

    def test_static_fixture_matches_base_manifest_dict(self, tmp_path):
        """Guards the two representations (checked-in file vs the dynamic
        dict used by every mutation test) against drifting apart."""
        from_static = load_manifest(_STATIC_MANIFEST)
        from_dict = load_manifest(_write_manifest(tmp_path, _base_manifest_dict()))
        assert compute_manifest_hash(from_static) == compute_manifest_hash(from_dict)


# --------------------------------------------------------------------------- #
# 2/3/28. Stable batch_id, manifest_hash, and selective-fingerprint identity.
# --------------------------------------------------------------------------- #

class TestIdentity:
    def test_stable_batch_id_unaffected_by_job_edit(self, tmp_path):
        data = _base_manifest_dict()
        m1 = load_manifest(_write_manifest(tmp_path, data, "m1.json"))
        edited = copy.deepcopy(data)
        edited["jobs"][2]["urls"][1] = "https://landgrantbrewing.com/location/"
        m2 = load_manifest(_write_manifest(tmp_path, edited, "m2.json"))
        assert get_batch_id(m1) == get_batch_id(m2) == "columbus-wave-1"

    def test_manifest_hash_changes_on_job_edit(self, tmp_path):
        data = _base_manifest_dict()
        m1 = load_manifest(_write_manifest(tmp_path, data, "m1.json"))
        edited = copy.deepcopy(data)
        edited["jobs"][2]["candidate_name"] = "Land-Grant Brewing Company"
        m2 = load_manifest(_write_manifest(tmp_path, edited, "m2.json"))
        assert compute_manifest_hash(m1) != compute_manifest_hash(m2)

    def test_manifest_hash_deterministic_across_loads(self, tmp_path):
        data = _base_manifest_dict()
        m1 = load_manifest(_write_manifest(tmp_path, data, "m1.json"))
        m2 = load_manifest(_write_manifest(tmp_path, copy.deepcopy(data), "m2.json"))
        assert compute_manifest_hash(m1) == compute_manifest_hash(m2)

    def test_editing_one_job_changes_only_that_jobs_fingerprint(self, tmp_path):
        data = _base_manifest_dict()
        m1 = load_manifest(_write_manifest(tmp_path, data, "m1.json"))
        edited = copy.deepcopy(data)
        edited["jobs"][2]["candidate_name"] = "Land-Grant Brewing Company"
        m2 = load_manifest(_write_manifest(tmp_path, edited, "m2.json"))

        fps1 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs()) for j in m1.jobs}
        fps2 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs()) for j in m2.jobs}

        assert fps1["drury-dublin"] == fps2["drury-dublin"]
        assert fps1["scioto-audubon"] == fps2["scioto-audubon"]
        assert fps1["land-grant"] != fps2["land-grant"]

    def test_28_unchanged_fingerprints_remain_resume_eligible_across_manifest_edit(
        self, tmp_path,
    ):
        """Same property as above, framed as the resume doctrine: batch_id
        is stable AND untouched jobs' fingerprints are unchanged, so a
        future resume can reuse them under the SAME batch state directory."""
        data = _base_manifest_dict()
        m1 = load_manifest(_write_manifest(tmp_path, data, "m1.json"))
        edited = copy.deepcopy(data)
        edited["batch_name"] = "Columbus Wave 1 (revised)"
        edited["jobs"][0]["expected_city"] = "Dublin, OH"   # only Drury touched
        m2 = load_manifest(_write_manifest(tmp_path, edited, "m2.json"))

        assert get_batch_id(m1) == get_batch_id(m2)
        assert compute_manifest_hash(m1) != compute_manifest_hash(m2)

        fps1 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs()) for j in m1.jobs}
        fps2 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs()) for j in m2.jobs}
        assert fps1["scioto-audubon"] == fps2["scioto-audubon"]
        assert fps1["land-grant"] == fps2["land-grant"]
        assert fps1["drury-dublin"] != fps2["drury-dublin"]


# --------------------------------------------------------------------------- #
# 5. Defaults merge.
# --------------------------------------------------------------------------- #

class TestDefaultsMerge:
    def test_job_value_overrides_default(self, tmp_path):
        data = _base_manifest_dict()
        data["defaults"]["expected_state"] = "OH"
        data["jobs"][0]["expected_state"] = "IN"   # explicit override
        manifest = load_manifest(_write_manifest(tmp_path, data))
        drury = next(j for j in manifest.jobs if j.job_id == "drury-dublin")
        assert drury.expected_state == "IN"

    def test_missing_job_value_inherits_default(self, tmp_path):
        data = _base_manifest_dict()
        manifest = load_manifest(_write_manifest(tmp_path, data))
        drury = next(j for j in manifest.jobs if j.job_id == "drury-dublin")
        assert drury.expected_state == "OH"                      # from defaults
        assert drury.source_relationship_hint == "EXACT_ENTITY_DOMAIN"

    def test_load_manifest_does_not_mutate_input_dict(self, tmp_path):
        data = _base_manifest_dict()
        original = copy.deepcopy(data)
        path = _write_manifest(tmp_path, data)
        load_manifest(path)
        assert json.loads(path.read_text(encoding="utf-8")) == original


# --------------------------------------------------------------------------- #
# 6/7/8/9/10/11/12. Structural + business-rule rejections.
# --------------------------------------------------------------------------- #

class TestValidationRejections:
    def test_6_duplicate_job_id_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][1]["job_id"] = "drury-dublin"
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("duplicate job_id" in e for e in errors)

    def test_7_invalid_batch_id_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["batch_id"] = "Columbus Wave 1!"
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("invalid batch_id" in e for e in errors)
        with pytest.raises(ValueError):
            get_batch_id(manifest)

    def test_8_invalid_job_id_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][0]["job_id"] = "Drury Dublin!"
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("invalid job_id" in e for e in errors)

    def test_9_unknown_top_level_key_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["operator_notes"] = "hi"
        path = _write_manifest(tmp_path, data)
        with pytest.raises(BatchManifestError, match="unknown top-level key"):
            load_manifest(path)

    def test_9_unknown_defaults_key_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["defaults"]["model"] = "claude-opus-4-8"
        path = _write_manifest(tmp_path, data)
        with pytest.raises(BatchManifestError, match="unknown defaults key"):
            load_manifest(path)

    def test_9_unknown_job_key_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][0]["retry"] = True
        path = _write_manifest(tmp_path, data)
        with pytest.raises(BatchManifestError, match="unknown job key"):
            load_manifest(path)

    def test_10_bad_category_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][0]["category"] = "spas"
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("category must be one of" in e for e in errors)

    def test_11_zero_urls_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][0]["urls"] = []
        data["jobs"][0]["static_fixtures"] = []
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("urls must contain 1 to" in e for e in errors)

    def test_12_five_urls_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][0]["urls"] = ["https://a.test/%d" % i for i in range(5)]
        data["jobs"][0]["static_fixtures"] = [_DRURY_FIXTURE] * 5
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("urls must contain 1 to" in e for e in errors)


# --------------------------------------------------------------------------- #
# 13/14/15/16/17. Static-fixture rules.
# --------------------------------------------------------------------------- #

class TestFixtureRules:
    def test_13_fixture_count_mismatch_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][2]["static_fixtures"] = [_LANDGRANT_FAQ_FIXTURE]  # 2 urls, 1 fixture
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("requires exactly one static_fixtures entry per url" in e for e in errors)

    def test_14_anthropic_mode_rejects_static_fixtures(self, tmp_path):
        data = _base_manifest_dict()
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="anthropic", repo_root=_REPO_ROOT)
        assert all("does not accept static_fixtures" in e for e in errors)
        assert len(errors) == 3   # all three jobs carry fixtures

    def test_15_absolute_fixture_path_rejected(self, tmp_path):
        data = _base_manifest_dict()
        abs_path = str((_REPO_ROOT / _DRURY_FIXTURE).resolve())
        data["jobs"][0]["static_fixtures"] = [abs_path]
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("must not be absolute" in e for e in errors)

    def test_16_traversal_path_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][0]["static_fixtures"] = ["../../../../etc/passwd"]
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("escapes the repository root" in e for e in errors)

    def test_17_missing_fixture_rejected(self, tmp_path):
        data = _base_manifest_dict()
        data["jobs"][0]["static_fixtures"] = [
            "tests/pettripfinder/importer/fixtures/does_not_exist_12345.json"]
        manifest = load_manifest(_write_manifest(tmp_path, data))
        errors = validate_manifest(manifest, extractor="static", repo_root=_REPO_ROOT)
        assert any("does not exist or is not a regular file" in e for e in errors)


# --------------------------------------------------------------------------- #
# 18. Fixture-content-drives-fingerprint isolation.
# --------------------------------------------------------------------------- #

class TestFixtureContentFingerprint:
    def test_fixture_content_change_affects_only_that_job(self, tmp_path):
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        fixture_a = fixtures_dir / "a.json"
        fixture_a.write_text('{"html": "original-a"}', encoding="utf-8")
        fixture_b = fixtures_dir / "b.json"
        fixture_b.write_text('{"html": "original-b"}', encoding="utf-8")

        job_a = BatchJob(job_id="a", candidate_name="A", category="hotels",
                         expected_city="X", expected_state="OH",
                         urls=("https://a.test/",), static_fixtures=("fixtures/a.json",))
        job_b = BatchJob(job_id="b", candidate_name="B", category="hotels",
                         expected_city="X", expected_state="OH",
                         urls=("https://b.test/",), static_fixtures=("fixtures/b.json",))
        kwargs = _job_kwargs(repo_root=tmp_path)

        fp_a1 = compute_job_fingerprint(job_a, **kwargs)
        fp_b1 = compute_job_fingerprint(job_b, **kwargs)

        fixture_a.write_text('{"html": "changed-a"}', encoding="utf-8")

        fp_a2 = compute_job_fingerprint(job_a, **kwargs)
        fp_b2 = compute_job_fingerprint(job_b, **kwargs)

        assert fp_a1 != fp_a2
        assert fp_b1 == fp_b2


# --------------------------------------------------------------------------- #
# 19/20/21. Shared-context changes affect every fingerprint.
# --------------------------------------------------------------------------- #

class TestSharedContextFingerprint:
    def test_19_model_change_changes_all_fingerprints(self, tmp_path):
        manifest = load_manifest(_write_manifest(tmp_path, _base_manifest_dict()))
        fps1 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs(model="claude-sonnet-5"))
               for j in manifest.jobs}
        fps2 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs(model="claude-opus-4-8"))
               for j in manifest.jobs}
        for job_id in fps1:
            assert fps1[job_id] != fps2[job_id]

    def test_20_extractor_change_changes_all_fingerprints(self, tmp_path):
        manifest = load_manifest(_write_manifest(tmp_path, _base_manifest_dict()))
        fps1 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs(extractor="static"))
               for j in manifest.jobs}
        fps2 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs(extractor="anthropic"))
               for j in manifest.jobs}
        for job_id in fps1:
            assert fps1[job_id] != fps2[job_id]

    def test_21_observed_at_change_changes_all_fingerprints(self, tmp_path):
        manifest = load_manifest(_write_manifest(tmp_path, _base_manifest_dict()))
        fps1 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs(observed_at="2026-07-17"))
               for j in manifest.jobs}
        fps2 = {j.job_id: compute_job_fingerprint(j, **_job_kwargs(observed_at="2026-07-18"))
               for j in manifest.jobs}
        for job_id in fps1:
            assert fps1[job_id] != fps2[job_id]


# --------------------------------------------------------------------------- #
# 22/23/24/25/26/27. Dry-run CLI.
# --------------------------------------------------------------------------- #

class TestDryRunCli:
    def test_22_valid_dry_run_exit_zero_deterministic_no_files(self, tmp_path, capsys):
        manifest_path = _write_manifest(tmp_path, _base_manifest_dict())
        output_root = tmp_path / "out"

        code1 = main(["--manifest", str(manifest_path), "--extractor", "static",
                     "--dry-run", "--output-root", str(output_root),
                     "--observed-at", "2026-07-17"])
        out1 = capsys.readouterr().out
        assert code1 == 0
        assert not output_root.exists()   # no output-root created

        code2 = main(["--manifest", str(manifest_path), "--extractor", "static",
                     "--dry-run", "--output-root", str(output_root),
                     "--observed-at", "2026-07-17"])
        out2 = capsys.readouterr().out
        assert code2 == 0
        assert out1 == out2               # deterministic across repeated runs
        assert not output_root.exists()

        plan = json.loads(out1)
        assert plan["batch_id"] == "columbus-wave-1"
        assert set(plan["selected_job_ids"]) == {"drury-dublin", "scioto-audubon", "land-grant"}
        assert len(plan["jobs"]) == 3

    def test_23_invalid_dry_run_exit_two_writes_nothing(self, tmp_path, capsys):
        data = _base_manifest_dict()
        data["jobs"][0]["urls"] = []
        data["jobs"][0]["static_fixtures"] = []
        manifest_path = _write_manifest(tmp_path, data)
        output_root = tmp_path / "out"

        code = main(["--manifest", str(manifest_path), "--extractor", "static",
                    "--dry-run", "--output-root", str(output_root)])
        assert code == 2
        assert not output_root.exists()
        out = capsys.readouterr().out
        assert "ERROR" in out

    def test_24_resume_and_force_rejected(self, tmp_path):
        manifest_path = _write_manifest(tmp_path, _base_manifest_dict())
        code = main(["--manifest", str(manifest_path), "--extractor", "static",
                    "--dry-run", "--resume", "--force"])
        assert code == 2

    def test_25_unknown_job_id_rejected(self, tmp_path):
        manifest_path = _write_manifest(tmp_path, _base_manifest_dict())
        code = main(["--manifest", str(manifest_path), "--extractor", "static",
                    "--dry-run", "--job-id", "does-not-exist"])
        assert code == 2

    def test_26_single_url_reports_route_single(self, tmp_path, capsys):
        manifest_path = _write_manifest(tmp_path, _base_manifest_dict())
        main(["--manifest", str(manifest_path), "--extractor", "static", "--dry-run"])
        plan = json.loads(capsys.readouterr().out)
        by_id = {j["job_id"]: j for j in plan["jobs"]}
        assert by_id["drury-dublin"]["route"] == "single"
        assert by_id["drury-dublin"]["url_count"] == 1
        assert by_id["scioto-audubon"]["route"] == "single"

    def test_27_multi_url_reports_route_multi(self, tmp_path, capsys):
        manifest_path = _write_manifest(tmp_path, _base_manifest_dict())
        main(["--manifest", str(manifest_path), "--extractor", "static", "--dry-run"])
        plan = json.loads(capsys.readouterr().out)
        by_id = {j["job_id"]: j for j in plan["jobs"]}
        assert by_id["land-grant"]["route"] == "multi"
        assert by_id["land-grant"]["url_count"] == 2

    def test_no_dry_run_flag_now_executes_for_real(self, tmp_path, capsys):
        """AES-WORK-001B lifts the AES-WORK-001A "--dry-run only" gate:
        omitting --dry-run now runs the batch for real through the existing
        importers instead of erroring. Full behavioral coverage of real
        execution lives in test_batch_runner.py/test_batch_resume.py; this
        just guards the CLI wiring itself against regressing back to the
        old always-reject gate."""
        manifest_path = _write_manifest(tmp_path, _base_manifest_dict())
        output_root = tmp_path / "out"
        code = main(["--manifest", str(manifest_path), "--extractor", "static",
                    "--output-root", str(output_root), "--observed-at", "2026-07-17"])
        assert code == 0
        summary = json.loads(capsys.readouterr().out)
        assert summary["totals"]["done"] == 3
        assert (output_root / "batches" / "columbus-wave-1" / "state.json").exists()

    def test_max_workers_out_of_range_rejected(self, tmp_path):
        manifest_path = _write_manifest(tmp_path, _base_manifest_dict())
        code = main(["--manifest", str(manifest_path), "--extractor", "static",
                    "--dry-run", "--max-workers", "99"])
        assert code == 2

    def test_disabled_job_reports_disabled_even_if_selected(self, tmp_path, capsys):
        data = _base_manifest_dict()
        data["jobs"][0]["enabled"] = False
        manifest_path = _write_manifest(tmp_path, data)
        main(["--manifest", str(manifest_path), "--extractor", "static", "--dry-run",
             "--job-id", "drury-dublin"])
        plan = json.loads(capsys.readouterr().out)
        by_id = {j["job_id"]: j for j in plan["jobs"]}
        assert by_id["drury-dublin"]["planned_action"] == "disabled"

    def test_job_id_selection_marks_others_not_selected(self, tmp_path, capsys):
        manifest_path = _write_manifest(tmp_path, _base_manifest_dict())
        main(["--manifest", str(manifest_path), "--extractor", "static", "--dry-run",
             "--job-id", "land-grant"])
        plan = json.loads(capsys.readouterr().out)
        by_id = {j["job_id"]: j for j in plan["jobs"]}
        assert by_id["land-grant"]["planned_action"] == "would_run"
        assert by_id["drury-dublin"]["planned_action"] == "not_selected"
        assert by_id["scioto-audubon"]["planned_action"] == "not_selected"
