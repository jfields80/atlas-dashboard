"""Website Generator models.

Immutable, framework-independent models for deterministic static website
generation from a Directory Builder ProjectAssembly.

The frozen base class is version-gated because Pydantic v2 raises
PydanticUserError when both ``model_config`` and a nested ``Config`` class
are defined on the same model. Exactly one configuration style is applied,
selected at import time.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

try:  # Pydantic v2
    from pydantic import ConfigDict

    _PYDANTIC_V2 = True
except ImportError:  # Pydantic v1
    _PYDANTIC_V2 = False


if _PYDANTIC_V2:

    class _Frozen(BaseModel):
        """Frozen base model (Pydantic v2)."""

        model_config = ConfigDict(frozen=True, extra="ignore")

        def atlas_model_dump(self, **kwargs: Any) -> dict[str, Any]:
            return self.model_dump(**kwargs)

        def atlas_model_dump_json(self, **kwargs: Any) -> str:
            return self.model_dump_json(**kwargs)

else:

    class _Frozen(BaseModel):  # type: ignore[no-redef]
        """Frozen base model (Pydantic v1)."""

        class Config:
            frozen = True
            extra = "ignore"

        @property
        def model_fields_set(self) -> set[str]:
            return set(getattr(self, "__fields_set__", set()))

        def atlas_model_dump(self, **kwargs: Any) -> dict[str, Any]:
            return self.dict(**kwargs)

        def atlas_model_dump_json(self, **kwargs: Any) -> str:
            return self.json(**kwargs)


class StaticPage(_Frozen):
    path: str
    title: str
    html: str
    page_type: str
    source_id: str = ""


class StaticAsset(_Frozen):
    path: str
    content: str
    asset_type: str


class StaticFileHash(_Frozen):
    path: str
    sha256: str
    size_bytes: int


class StaticSiteManifest(_Frozen):
    engine_name: str
    engine_version: str
    template_name: str
    project_slug: str
    site_id: str
    build_fingerprint: str
    page_count: int
    asset_count: int
    files: tuple[StaticFileHash, ...]


class WebsiteQualityIssue(_Frozen):
    issue_id: str
    severity: str
    check: str
    message: str
    path: str = ""


class WebsiteQualityReport(_Frozen):
    passed: bool
    critical_count: int
    warning_count: int
    issues: tuple[WebsiteQualityIssue, ...] = ()


class StaticSitePackage(_Frozen):
    project_slug: str
    template_name: str
    pages: tuple[StaticPage, ...]
    assets: tuple[StaticAsset, ...]
    manifest: StaticSiteManifest
    quality_report: WebsiteQualityReport
    system_files: tuple[StaticAsset, ...] = ()
