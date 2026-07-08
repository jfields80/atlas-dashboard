"""
Tests for scripts/generate_launch_kit.py (Directory #1 Operator Runner).

These tests do NOT depend on the real LaunchKitService implementation.
They use fake/stub services injected via the `service_factory` parameter
(for unit-level tests) or by monkeypatching the import hook (for the
end-to-end `run()` test), so they will pass regardless of the exact
signature of the real service. This keeps the test suite decoupled from
services/launch_kit_service.py, which was not available at the time this
script was authored.

Run with:
    python -m pytest tests/test_operator_runner.py -v
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the script under test as a module, regardless of where pytest is
# invoked from.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_launch_kit.py"

spec = importlib.util.spec_from_file_location("generate_launch_kit", SCRIPT_PATH)
generate_launch_kit = importlib.util.module_from_spec(spec)
sys.modules["generate_launch_kit"] = generate_launch_kit
spec.loader.exec_module(generate_launch_kit)  # type: ignore


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------

class FakeLaunchKitService:
    """Stand-in for the real LaunchKitService, matching the primary
    expected call signature: generate_launch_kit(blueprint=, seed_package=,
    project_slug=)."""

    def generate_launch_kit(self, blueprint, seed_package, project_slug):
        return {
            "json_export": {"blueprint_echo": blueprint, "project_slug": project_slug},
            "csv_export": seed_package.get("listings", []),
            "url_map": {"/pet-friendly-hotels/oh/columbus": "listing-1"},
            "seo_export": {"title": f"{project_slug} SEO"},
            "content_plan_export": {"cadence": "weekly"},
            "ai_task_queue_export": [{"task_id": "seo_meta_generation"}],
            "launch_checklist": ["Set up hosting", "Import listings", "Activate affiliate links"],
            "operator_notes": ["Verify affiliate program approval before launch."],
        }


class AltSignatureLaunchKitService:
    """A service whose method only accepts positional args, to exercise
    the adapter's fallback logic in build_launch_kit()."""

    def generate_launch_kit(self, blueprint, seed_package, project_slug):
        # Deliberately does NOT accept keyword args the way the primary
        # candidate call uses them, by raising TypeError on kwargs.
        raise TypeError("keyword arguments not supported by this fake")

    def generate(self, blueprint, seed_package, project_slug):
        raise TypeError("no kwargs here either")

    def build_launch_kit(self, blueprint, seed_package, project_slug):
        return {"json_export": {"ok": True, "project_slug": project_slug}}


@pytest.fixture
def sample_blueprint():
    return json.loads(
        (REPO_ROOT / "examples" / "pettripfinder" / "blueprint_input.json").read_text()
    )


@pytest.fixture
def sample_seed():
    return json.loads(
        (REPO_ROOT / "examples" / "pettripfinder" / "seed_package_input.json").read_text()
    )


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert generate_launch_kit.slugify("PetTripFinder") == "pettripfinder"


def test_slugify_handles_spaces_and_punctuation():
    assert generate_launch_kit.slugify("Pet Trip Finder!!") == "pet-trip-finder"


# ---------------------------------------------------------------------------
# load_json
# ---------------------------------------------------------------------------

def test_load_json_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        generate_launch_kit.load_json(missing)


def test_load_json_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json")
    with pytest.raises(ValueError):
        generate_launch_kit.load_json(bad_file)


def test_load_json_valid(sample_blueprint):
    assert sample_blueprint["project_profile"]["project_slug"] == "pettripfinder"


# ---------------------------------------------------------------------------
# build_launch_kit (adapter)
# ---------------------------------------------------------------------------

def test_build_launch_kit_primary_signature(sample_blueprint, sample_seed):
    result = generate_launch_kit.build_launch_kit(
        sample_blueprint,
        sample_seed,
        "pettripfinder",
        service_factory=FakeLaunchKitService,
    )
    assert result["json_export"]["project_slug"] == "pettripfinder"
    assert isinstance(result["csv_export"], list)
    assert "launch_checklist" in result


def test_build_launch_kit_falls_back_to_alt_signature(sample_blueprint, sample_seed):
    result = generate_launch_kit.build_launch_kit(
        sample_blueprint,
        sample_seed,
        "pettripfinder",
        service_factory=AltSignatureLaunchKitService,
    )
    assert result["json_export"]["ok"] is True


def test_build_launch_kit_raises_if_no_signature_matches(sample_blueprint, sample_seed):
    class NoMatchService:
        def generate_launch_kit(self, *args, **kwargs):
            raise TypeError("nope")

        def generate(self, *args, **kwargs):
            raise TypeError("nope")

        def build_launch_kit(self, *args, **kwargs):
            raise TypeError("nope")

        def create_launch_kit(self, *args, **kwargs):
            raise TypeError("nope")

    with pytest.raises(TypeError):
        generate_launch_kit.build_launch_kit(
            sample_blueprint, sample_seed, "pettripfinder", service_factory=NoMatchService
        )


# ---------------------------------------------------------------------------
# write_launch_package
# ---------------------------------------------------------------------------

def test_write_launch_package_creates_expected_files(tmp_path):
    launch_kit = {
        "json_export": {"foo": "bar"},
        "csv_export": [{"name": "Listing A", "city": "Columbus"}],
        "url_map": {"/a": "b"},
        "seo_export": {"title": "Test"},
        "content_plan_export": {"cadence": "weekly"},
        "ai_task_queue_export": [{"task_id": "t1"}],
        "launch_checklist": ["Do the thing"],
        "operator_notes": ["Note one"],
    }

    package_dir = generate_launch_kit.write_launch_package(
        tmp_path, "pettripfinder", launch_kit
    )

    assert package_dir == tmp_path / "pettripfinder"
    assert (package_dir / "launch_package.json").exists()
    assert (package_dir / "json_export.json").exists()
    assert (package_dir / "listings.csv").exists()
    assert (package_dir / "url_map.json").exists()
    assert (package_dir / "seo_export.json").exists()
    assert (package_dir / "content_plan_export.json").exists()
    assert (package_dir / "ai_task_queue_export.json").exists()
    assert (package_dir / "launch_checklist.md").exists()
    assert (package_dir / "operator_notes.md").exists()

    checklist_text = (package_dir / "launch_checklist.md").read_text()
    assert "Do the thing" in checklist_text

    csv_text = (package_dir / "listings.csv").read_text()
    assert "Listing A" in csv_text


def test_write_launch_package_only_writes_present_fields(tmp_path):
    launch_kit = {"json_export": {"foo": "bar"}}
    package_dir = generate_launch_kit.write_launch_package(
        tmp_path, "minimalproject", launch_kit
    )
    assert (package_dir / "launch_package.json").exists()
    assert (package_dir / "json_export.json").exists()
    assert not (package_dir / "listings.csv").exists()
    assert not (package_dir / "launch_checklist.md").exists()


def test_write_launch_package_refuses_to_overwrite_by_default(tmp_path):
    launch_kit = {"json_export": {"foo": "bar"}}
    generate_launch_kit.write_launch_package(tmp_path, "pettripfinder", launch_kit)

    with pytest.raises(FileExistsError):
        generate_launch_kit.write_launch_package(tmp_path, "pettripfinder", launch_kit)


def test_write_launch_package_overwrite_flag_allows_regeneration(tmp_path):
    launch_kit_v1 = {"json_export": {"version": 1}}
    launch_kit_v2 = {"json_export": {"version": 2}}

    generate_launch_kit.write_launch_package(tmp_path, "pettripfinder", launch_kit_v1)
    package_dir = generate_launch_kit.write_launch_package(
        tmp_path, "pettripfinder", launch_kit_v2, overwrite=True
    )

    data = json.loads((package_dir / "json_export.json").read_text())
    assert data["version"] == 2


# ---------------------------------------------------------------------------
# End-to-end run() with a monkeypatched service import
# ---------------------------------------------------------------------------

def test_run_end_to_end(tmp_path, monkeypatch, sample_blueprint, sample_seed):
    blueprint_path = tmp_path / "blueprint.json"
    seed_path = tmp_path / "seed.json"
    blueprint_path.write_text(json.dumps(sample_blueprint))
    seed_path.write_text(json.dumps(sample_seed))

    output_dir = tmp_path / "launch_packages"

    monkeypatch.setattr(
        generate_launch_kit,
        "_import_launch_kit_service",
        lambda: FakeLaunchKitService,
    )

    exit_code = generate_launch_kit.run(
        [
            "--project",
            "PetTripFinder",
            "--blueprint",
            str(blueprint_path),
            "--seed",
            str(seed_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    package_dir = output_dir / "pettripfinder"
    assert package_dir.exists()
    assert (package_dir / "launch_package.json").exists()
    assert (package_dir / "listings.csv").exists()


def test_run_returns_nonzero_on_missing_blueprint(tmp_path, monkeypatch, sample_seed):
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(json.dumps(sample_seed))

    monkeypatch.setattr(
        generate_launch_kit,
        "_import_launch_kit_service",
        lambda: FakeLaunchKitService,
    )

    exit_code = generate_launch_kit.run(
        [
            "--project",
            "pettripfinder",
            "--blueprint",
            str(tmp_path / "missing_blueprint.json"),
            "--seed",
            str(seed_path),
            "--output-dir",
            str(tmp_path / "launch_packages"),
        ]
    )

    assert exit_code == 1


def test_run_returns_error_code_when_import_fails(tmp_path, monkeypatch, sample_blueprint, sample_seed):
    blueprint_path = tmp_path / "blueprint.json"
    seed_path = tmp_path / "seed.json"
    blueprint_path.write_text(json.dumps(sample_blueprint))
    seed_path.write_text(json.dumps(sample_seed))

    def _raise_import_error():
        raise ImportError("services.launch_kit_service not found")

    monkeypatch.setattr(
        generate_launch_kit, "_import_launch_kit_service", _raise_import_error
    )

    exit_code = generate_launch_kit.run(
        [
            "--project",
            "pettripfinder",
            "--blueprint",
            str(blueprint_path),
            "--seed",
            str(seed_path),
            "--output-dir",
            str(tmp_path / "launch_packages"),
        ]
    )

    assert exit_code == 2
