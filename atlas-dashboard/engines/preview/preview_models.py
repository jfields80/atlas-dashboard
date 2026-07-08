"""Preview Engine models.

Immutable models describing a fully browsable local preview build of a
Website Generator StaticSitePackage.

Subsystem-specific models live with the subsystem per the Atlas contract:
core/ stays small and shared.

The frozen base class is version-gated because Pydantic v2 raises
PydanticUserError when both ``model_config`` and a nested ``Config`` class
are defined on the same model. Exactly one configuration style is applied,
selected at import time by capability detection (``BaseModel.model_dump``),
which remains correct on Pydantic 1.10.17+ where a ConfigDict
forward-compatibility shim makes import-based gating unreliable.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# Detect the real major version by capability, not by the ConfigDict
# import: Pydantic 1.10.17+ ships a ConfigDict forward-compatibility shim,
# so an import-based gate misidentifies late v1 releases as v2.
_PYDANTIC_V2 = hasattr(BaseModel, "model_dump")

if _PYDANTIC_V2:
    from pydantic import ConfigDict


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


class PreviewBuild(_Frozen):
    """The result of writing a StaticSitePackage as a local preview.

    ``preview_ready`` is True only when every quality check passed:
    homepage, manifest, robots, and sitemap all exist; every page and
    asset was written; manifest hashes verify against the files on disk;
    and no duplicate output paths were produced. Any failed check is
    recorded in ``issues``.
    """

    preview_path: str
    page_count: int
    asset_count: int
    manifest_path: str
    homepage_path: str
    preview_ready: bool
    issues: tuple[str, ...] = ()
