"""Section 10 — Build Manifest Engine.

Computes the immutable build manifest: engine identity, a deterministic
build_id derived from the input fingerprint + engine version, and a
hash-verified inventory of every written artifact.

Pydantic v1/v2 compatible.
"""

from __future__ import annotations

import json
from typing import Any

from engines.directory_builder.models import BuildManifest, LaunchPackage, ManifestFile
from engines.directory_builder.constants import ENGINE_NAME, ENGINE_VERSION as BUILDER_VERSION
from engines.directory_builder.deterministic import fingerprint

ENGINE_VERSION = "1.0.0"


def _model_to_dict(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_model_to_dict(x) for x in obj]
    return obj


def _model_to_json(obj: Any) -> str:
    data = _model_to_dict(obj)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class BuildManifestEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def input_fingerprint(package: LaunchPackage) -> str:
        """Full-content fingerprint of the launch package."""
        canonical = _model_to_json(package)
        return fingerprint(canonical)

    @staticmethod
    def build(
        package: LaunchPackage,
        project_slug: str,
        built_at: str,
        files: tuple[ManifestFile, ...],
    ) -> BuildManifest:
        input_fp = BuildManifestEngine.input_fingerprint(package)
        build_id = fingerprint(
            f"{ENGINE_NAME}|{BUILDER_VERSION}|{project_slug}|{input_fp}"
        )[:16]

        return BuildManifest(
            engine_name=ENGINE_NAME,
            engine_version=BUILDER_VERSION,
            project_slug=project_slug,
            build_id=build_id,
            built_at=built_at,
            input_fingerprint=input_fp,
            files=tuple(sorted(files, key=lambda f: f.path)),
        )