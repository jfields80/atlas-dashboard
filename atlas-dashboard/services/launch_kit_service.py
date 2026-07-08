"""Launch Kit Service.

Thin orchestration layer between raw inputs and the Launch Kit Engine.

Responsibilities:
    * Adapt whatever the caller has — plain dicts today, typed Blueprint
      / SeedPackage objects later — into the engine's dict-based
      ``LaunchKitInput`` contract.
    * Call the deterministic engine.
    * Optionally hand the result to the exporter.

Non-responsibilities (by design):
    * No SQL. No repositories yet. When Phase 3A/3B repository loading is
      wired in later, that code adapts loaded objects through
      ``coerce_to_dict`` and nothing in the engine changes.
    * No Flask, no filesystem access outside the injected exporter.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from engines.launch_kit.launch_kit_engine import build_launch_kit
from engines.launch_kit.models import (
    LaunchKit,
    LaunchKitInput,
    LaunchKitInputError,
)
from services.launch_kit_exporter import LaunchKitExporter


def coerce_to_dict(value: Any, field_name: str) -> Dict[str, Any]:
    """Tolerantly convert an input into a plain dict.

    Accepts, in priority order:
        1. Mapping (dict) — used as-is (shallow copy).
        2. JSON string — parsed; must decode to an object.
        3. Pydantic v2 models — via ``model_dump()``.
        4. Pydantic v1 models — via ``dict()``.
        5. Dataclasses — via ``dataclasses.asdict()``.
        6. Objects exposing ``to_dict()``.

    Raises:
        LaunchKitInputError: If the value cannot be converted.
    """
    if isinstance(value, Mapping):
        return dict(value)

    if isinstance(value, (str, bytes)):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise LaunchKitInputError(
                f"{field_name} was a string but is not valid JSON: {exc}"
            ) from exc
        if not isinstance(parsed, Mapping):
            raise LaunchKitInputError(
                f"{field_name} JSON must decode to an object, got "
                f"{type(parsed).__name__}"
            )
        return dict(parsed)

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dict(dumped)

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        converted = to_dict()
        if isinstance(converted, Mapping):
            return dict(converted)

    as_dict = getattr(value, "dict", None)
    if callable(as_dict):
        converted = as_dict()
        if isinstance(converted, Mapping):
            return dict(converted)

    raise LaunchKitInputError(
        f"{field_name} must be a dict, JSON string, dataclass, or an object "
        f"with model_dump()/to_dict()/dict(); got {type(value).__name__}"
    )


class LaunchKitService:
    """Generates launch packages from tolerant, loosely typed inputs."""

    def __init__(self, exporter: Optional[LaunchKitExporter] = None) -> None:
        self._exporter = exporter or LaunchKitExporter()

    def build_input(
        self,
        project_slug: str,
        blueprint: Any,
        seed_package: Any,
        project_name: Optional[str] = None,
        generated_at: Optional[str] = None,
    ) -> LaunchKitInput:
        """Adapt loose inputs into the engine's LaunchKitInput contract."""
        return LaunchKitInput(
            project_slug=project_slug,
            blueprint=coerce_to_dict(blueprint, "blueprint"),
            seed_package=coerce_to_dict(seed_package, "seed_package"),
            project_name=project_name,
            generated_at=generated_at,
        )

    def generate(
        self,
        project_slug: str,
        blueprint: Any,
        seed_package: Any,
        project_name: Optional[str] = None,
        generated_at: Optional[str] = None,
    ) -> LaunchKit:
        """Generate an in-memory launch kit (no filesystem access)."""
        kit_input = self.build_input(
            project_slug=project_slug,
            blueprint=blueprint,
            seed_package=seed_package,
            project_name=project_name,
            generated_at=generated_at,
        )
        return build_launch_kit(kit_input)

    def generate_and_export(
        self,
        project_slug: str,
        blueprint: Any,
        seed_package: Any,
        project_name: Optional[str] = None,
        generated_at: Optional[str] = None,
        output_root: Optional[str] = None,
    ) -> Tuple[LaunchKit, Path]:
        """Generate a launch kit and write it to disk.

        Returns:
            (kit, package_dir) where package_dir is
            ``{output_root}/{project_slug}/``.
        """
        kit = self.generate(
            project_slug=project_slug,
            blueprint=blueprint,
            seed_package=seed_package,
            project_name=project_name,
            generated_at=generated_at,
        )
        package_dir = self._exporter.export(kit, output_root=output_root)
        return kit, package_dir
