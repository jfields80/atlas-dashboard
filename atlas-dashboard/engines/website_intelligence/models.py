"""Website Intelligence models.

Immutable, deterministic contract models for AES-005A Part 1.

Supports both Pydantic v1 and v2 without relying on ConfigDict import
detection, because some Pydantic v1 releases expose ConfigDict as a shim.
"""

from __future__ import annotations

from typing import Any

import pydantic
from pydantic import BaseModel, Field, validator

PYDANTIC_V2 = pydantic.VERSION.startswith("2")


if PYDANTIC_V2:
    from pydantic import ConfigDict

    class ImmutableModel(BaseModel):
        """Immutable base model for Pydantic v2."""

        model_config = ConfigDict(
            frozen=True,
            extra="ignore",
            arbitrary_types_allowed=True,
        )

        def atlas_model_dump(self, **kwargs: Any) -> dict[str, Any]:
            return self.model_dump(**kwargs)

        def atlas_model_dump_json(self, **kwargs: Any) -> str:
            return self.model_dump_json(**kwargs)

else:

    class ImmutableModel(BaseModel):
        """Immutable base model for Pydantic v1."""

        class Config:
            allow_mutation = False
            extra = "ignore"
            arbitrary_types_allowed = True

        @property
        def model_fields_set(self) -> set[str]:
            return set(getattr(self, "__fields_set__", set()))

        def atlas_model_dump(self, **kwargs: Any) -> dict[str, Any]:
            return self.dict(**kwargs)

        def atlas_model_dump_json(self, **kwargs: Any) -> str:
            return self.json(**kwargs)


def _require_non_empty(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be a non-empty string")
    return value


class WebsiteAuditInput(ImmutableModel):
    """Wrapper for the artifacts that future audit logic will inspect.

    Part 1 intentionally treats these artifacts as opaque objects.
    Later audit engines will interpret the real ProjectAssembly,
    StaticSitePackage, and PreviewBuild schemas.
    """

    project_assembly: Any = Field(...)
    static_site_package: Any = Field(...)
    preview_build: Any = Field(...)


class WebsiteAuditFinding(ImmutableModel):
    finding_id: str
    category: str
    severity: str
    title: str
    description: str = ""
    evidence: str = ""
    path: str = ""
    score_impact: float = 0.0

    @validator("finding_id", "category", "severity", "title")
    def _required_strings(cls, value: str) -> str:
        return _require_non_empty(value)


class WebsiteAuditRecommendation(ImmutableModel):
    recommendation_id: str
    category: str
    priority: str
    title: str
    description: str = ""
    finding_ids: tuple[str, ...] = ()

    @validator("recommendation_id", "category", "priority", "title")
    def _required_strings(cls, value: str) -> str:
        return _require_non_empty(value)


class WebsiteWorkOrder(ImmutableModel):
    work_order_id: str
    recommendation_id: str
    category: str
    priority: str
    title: str
    instructions: str
    acceptance_criteria: tuple[str, ...] = ()
    status: str = "PENDING"

    @validator(
        "work_order_id",
        "recommendation_id",
        "category",
        "priority",
        "title",
        "instructions",
    )
    def _required_strings(cls, value: str) -> str:
        return _require_non_empty(value)


class WebsiteAuditReport(ImmutableModel):
    report_id: str
    engine_name: str
    engine_version: str

    seo_score: float = Field(..., ge=0.0, le=100.0)
    navigation_score: float = Field(..., ge=0.0, le=100.0)
    content_score: float = Field(..., ge=0.0, le=100.0)
    directory_score: float = Field(..., ge=0.0, le=100.0)
    commercial_score: float = Field(..., ge=0.0, le=100.0)
    monetization_score: float = Field(..., ge=0.0, le=100.0)
    ux_score: float = Field(..., ge=0.0, le=100.0)
    overall_score: float = Field(..., ge=0.0, le=100.0)

    grade: str
    launch_readiness: str

    findings: tuple[WebsiteAuditFinding, ...] = ()
    recommendations: tuple[WebsiteAuditRecommendation, ...] = ()
    work_orders: tuple[WebsiteWorkOrder, ...] = ()

    @validator("report_id", "engine_name", "engine_version", "grade", "launch_readiness")
    def _required_strings(cls, value: str) -> str:
        return _require_non_empty(value)