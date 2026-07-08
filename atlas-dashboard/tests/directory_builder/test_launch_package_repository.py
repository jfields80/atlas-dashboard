"""Unit tests: LaunchPackageRepository."""

from pathlib import Path

import pytest

from repositories.directory_builder.launch_package_repository import (
    LaunchPackageNotFoundError,
    LaunchPackageRepository,
)

def test_loads_complete_package(launch_package):
    assert launch_package.blueprint.project_slug == "demo-directory"
    assert len(launch_package.seed_businesses) == 5
    assert len(launch_package.categories) == 2
    assert len(launch_package.locations) == 2
    assert launch_package.missing_files == ()

def test_missing_directory_raises(tmp_path: Path):
    with pytest.raises(LaunchPackageNotFoundError):
        LaunchPackageRepository().load(tmp_path / "does-not-exist")

def test_missing_blueprint_raises(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(LaunchPackageNotFoundError):
        LaunchPackageRepository().load(tmp_path / "empty")

def test_optional_files_recorded_as_missing(tmp_path: Path, demo_package_factory):
    root = demo_package_factory(tmp_path / "partial")
    (root / "content_plan.csv").unlink()
    (root / "operator_notes.md").unlink()
    package = LaunchPackageRepository().load(root)
    assert "content_plan.csv" in package.missing_files
    assert "operator_notes.md" in package.missing_files
    assert package.content_plan == ()
    assert package.operator_notes_md == ""

def test_csv_priority_coercion(launch_package):
    assert all(isinstance(e.priority, int) for e in launch_package.content_plan)
    assert launch_package.content_plan[0].priority == 1
