"""Tests for the Launch Kit Exporter (filesystem writer)."""

from __future__ import annotations

from pathlib import Path

import pytest

from engines.launch_kit import LAUNCH_KIT_FILENAMES, LaunchKitInput, build_launch_kit
from services.launch_kit_exporter import (
    DEFAULT_OUTPUT_ROOT,
    LaunchKitExporter,
    LaunchKitExportError,
)


@pytest.fixture
def kit(full_blueprint, full_seed_package):
    return build_launch_kit(
        LaunchKitInput("pet-trip-finder", full_blueprint, full_seed_package)
    )


class TestExport:
    def test_writes_all_files_to_slug_directory(self, kit, tmp_path):
        exporter = LaunchKitExporter(output_root=tmp_path)
        package_dir = exporter.export(kit)

        assert package_dir == tmp_path / "pet-trip-finder"
        written = sorted(p.name for p in package_dir.iterdir())
        assert written == sorted(LAUNCH_KIT_FILENAMES)

    def test_file_contents_match_kit_exactly(self, kit, tmp_path):
        exporter = LaunchKitExporter(output_root=tmp_path)
        package_dir = exporter.export(kit)
        for launch_file in kit.files:
            on_disk = (package_dir / launch_file.filename).read_text(
                encoding="utf-8"
            )
            assert on_disk == launch_file.content

    def test_reexport_is_byte_identical(self, kit, tmp_path):
        exporter = LaunchKitExporter(output_root=tmp_path)
        package_dir = exporter.export(kit)
        first = {
            p.name: p.read_bytes() for p in package_dir.iterdir()
        }
        exporter.export(kit)
        second = {
            p.name: p.read_bytes() for p in package_dir.iterdir()
        }
        assert first == second

    def test_no_carriage_returns_on_disk(self, kit, tmp_path):
        exporter = LaunchKitExporter(output_root=tmp_path)
        package_dir = exporter.export(kit)
        for path in package_dir.iterdir():
            assert b"\r" not in path.read_bytes()

    def test_per_call_output_root_override(self, kit, tmp_path):
        exporter = LaunchKitExporter(output_root=tmp_path / "default")
        override = tmp_path / "override"
        package_dir = exporter.export(kit, output_root=override)
        assert package_dir == override / "pet-trip-finder"
        assert not (tmp_path / "default").exists()

    def test_default_output_root_constant(self):
        exporter = LaunchKitExporter()
        assert exporter.output_root == Path(DEFAULT_OUTPUT_ROOT)

    def test_written_paths_predicts_layout_without_writing(self, kit, tmp_path):
        exporter = LaunchKitExporter(output_root=tmp_path)
        predicted = exporter.written_paths(kit)
        assert len(predicted) == len(LAUNCH_KIT_FILENAMES)
        assert all(not p.exists() for p in predicted)
        exporter.export(kit)
        assert all(p.exists() for p in predicted)

    def test_unwritable_root_raises_export_error(self, kit, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.write_text("i am a file, not a directory")
        exporter = LaunchKitExporter(output_root=blocker)
        with pytest.raises(LaunchKitExportError):
            exporter.export(kit)
