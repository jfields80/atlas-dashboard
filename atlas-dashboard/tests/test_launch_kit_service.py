"""Tests for the Launch Kit Service (adaptation + orchestration)."""

from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict, List

import pytest

from engines.launch_kit import LAUNCH_KIT_FILENAMES, LaunchKitInputError
from services.launch_kit_exporter import LaunchKitExporter
from services.launch_kit_service import LaunchKitService, coerce_to_dict


# ---------------------------------------------------------------------------
# Stand-ins for future typed Blueprint / SeedPackage objects
# ---------------------------------------------------------------------------


class FakePydanticV2Model:
    """Mimics a Pydantic v2 model exposing model_dump()."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self) -> Dict[str, Any]:
        return dict(self._payload)


class FakeLegacyModel:
    """Mimics an object exposing to_dict()."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._payload)


@dataclasses.dataclass
class FakeDataclassSeedPackage:
    listings: List[Dict[str, Any]]


class TestCoerceToDict:
    def test_dict_passthrough(self):
        assert coerce_to_dict({"a": 1}, "blueprint") == {"a": 1}

    def test_json_string_parsed(self):
        assert coerce_to_dict('{"a": 1}', "blueprint") == {"a": 1}

    def test_invalid_json_string_rejected(self):
        with pytest.raises(LaunchKitInputError):
            coerce_to_dict("not json", "blueprint")

    def test_json_array_string_rejected(self):
        with pytest.raises(LaunchKitInputError):
            coerce_to_dict("[1, 2]", "blueprint")

    def test_pydantic_v2_style_model(self):
        model = FakePydanticV2Model({"monetization_plan": {"primary_model": "ads"}})
        assert coerce_to_dict(model, "blueprint")["monetization_plan"] == {
            "primary_model": "ads"
        }

    def test_dataclass_converted(self):
        package = FakeDataclassSeedPackage(listings=[{"name": "A"}])
        assert coerce_to_dict(package, "seed_package") == {
            "listings": [{"name": "A"}]
        }

    def test_to_dict_object_converted(self):
        model = FakeLegacyModel({"listings": []})
        assert coerce_to_dict(model, "seed_package") == {"listings": []}

    def test_unconvertible_object_rejected(self):
        with pytest.raises(LaunchKitInputError):
            coerce_to_dict(object(), "blueprint")


class TestServiceGenerate:
    def test_generate_from_dicts(self, full_blueprint, full_seed_package):
        service = LaunchKitService()
        kit = service.generate(
            "pet-trip-finder", full_blueprint, full_seed_package
        )
        assert tuple(f.filename for f in kit.files) == LAUNCH_KIT_FILENAMES
        assert kit.stats.listing_count == 3

    def test_generate_from_json_strings(self, full_blueprint, full_seed_package):
        service = LaunchKitService()
        kit = service.generate(
            "pet-trip-finder",
            json.dumps(full_blueprint),
            json.dumps(full_seed_package),
        )
        assert kit.stats.listing_count == 3

    def test_generate_from_mixed_object_types(self, full_blueprint):
        service = LaunchKitService()
        seed = FakeDataclassSeedPackage(
            listings=[{"name": "A", "category": "Hotels", "city": "Columbus"}]
        )
        kit = service.generate(
            "pet-trip-finder", FakePydanticV2Model(full_blueprint), seed
        )
        assert kit.stats.listing_count == 1
        assert kit.stats.category_count == 1

    def test_generate_passes_through_metadata(
        self, sparse_blueprint, sparse_seed_package
    ):
        service = LaunchKitService()
        kit = service.generate(
            "sparse-project",
            sparse_blueprint,
            sparse_seed_package,
            project_name="Sparse, Inc.",
            generated_at="2026-07-06",
        )
        assert kit.project_name == "Sparse, Inc."
        assert kit.generated_at == "2026-07-06"

    def test_generate_is_filesystem_free(
        self, full_blueprint, full_seed_package, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        service = LaunchKitService()
        service.generate("pet-trip-finder", full_blueprint, full_seed_package)
        assert list(tmp_path.iterdir()) == []


class TestServiceGenerateAndExport:
    def test_end_to_end_writes_package(
        self, full_blueprint, full_seed_package, tmp_path
    ):
        service = LaunchKitService(
            exporter=LaunchKitExporter(output_root=tmp_path)
        )
        kit, package_dir = service.generate_and_export(
            "pet-trip-finder", full_blueprint, full_seed_package
        )
        assert package_dir == tmp_path / "pet-trip-finder"
        assert sorted(p.name for p in package_dir.iterdir()) == sorted(
            LAUNCH_KIT_FILENAMES
        )
        on_disk = (package_dir / "operator_notes.md").read_text(encoding="utf-8")
        assert on_disk == kit.get_file("operator_notes.md").content

    def test_output_root_override_per_call(
        self, sparse_blueprint, sparse_seed_package, tmp_path
    ):
        service = LaunchKitService(
            exporter=LaunchKitExporter(output_root=tmp_path / "default")
        )
        _, package_dir = service.generate_and_export(
            "sparse-project",
            sparse_blueprint,
            sparse_seed_package,
            output_root=tmp_path / "custom",
        )
        assert package_dir == tmp_path / "custom" / "sparse-project"
