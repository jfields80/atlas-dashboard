"""Directory Builder models — inputs (Launch Package) and outputs (Project Assembly).

Subsystem-specific models live with the subsystem per the Atlas contract:
core/ stays small and shared. All models are immutable (frozen).

Input models:  Launch Package, produced by the (frozen) Launch Kit Generator.
Output models: Project Assembly, the file-artifact contract consumed by any
future Website Generator. The Builder never mutates a Launch Package.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    """Frozen Directory Builder base model with Pydantic v1/v2 compatibility."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    class Config:
        frozen = True
        extra = "ignore"

    @property
    def model_fields_set(self) -> set[str]:
        """Pydantic v2-compatible field-set accessor for Pydantic v1 runtimes."""
        return set(getattr(self, "__fields_set__", set()))

    def atlas_model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Return model data under both Pydantic v1 and v2."""
        if hasattr(super(), "model_dump"):
            return super().model_dump(**kwargs)  # type: ignore[attr-defined]

        return self.dict(**kwargs)

    def atlas_model_dump_json(self, **kwargs: Any) -> str:
        """Return model JSON under both Pydantic v1 and v2."""
        if hasattr(super(), "model_dump_json"):
            return super().model_dump_json(**kwargs)  # type: ignore[attr-defined]

        return self.json(**kwargs)


# ---------------------------------------------------------------------------
# Input models: Launch Package
# ---------------------------------------------------------------------------

class Blueprint(_Frozen):
    project_name: str
    project_slug: str
    niche: str = ""
    domain: str = ""
    description: str = ""
    target_audience: str = ""


class SeedBusiness(_Frozen):
    name: str
    category: str
    city: str
    state: str
    website: str = ""
    phone: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    amenities: tuple[str, ...] = ()


class CategoryDef(_Frozen):
    name: str
    slug: str
    description: str = ""


class LocationDef(_Frozen):
    city: str
    state: str
    slug: str


class UrlMapEntry(_Frozen):
    path: str
    page_type: str
    title: str = ""


class SeoPageEntry(_Frozen):
    page_type: str
    slug: str
    title: str = ""
    meta_description: str = ""


class ContentPlanEntry(_Frozen):
    content_type: str
    title: str
    target_keyword: str = ""
    priority: int = 2


class MonetizationModel(_Frozen):
    name: str
    model_type: str = ""
    notes: str = ""


class MonetizationPlan(_Frozen):
    models: tuple[MonetizationModel, ...] = ()


class AiTaskEntry(_Frozen):
    task_type: str
    description: str
    priority: int = 2


class LaunchPackage(_Frozen):
    """The complete, validated input consumed by the Directory Builder."""

    blueprint: Blueprint
    seed_businesses: tuple[SeedBusiness, ...] = ()
    categories: tuple[CategoryDef, ...] = ()
    locations: tuple[LocationDef, ...] = ()
    url_map: tuple[UrlMapEntry, ...] = ()
    seo_pages: tuple[SeoPageEntry, ...] = ()
    content_plan: tuple[ContentPlanEntry, ...] = ()
    monetization_plan: MonetizationPlan = Field(default_factory=MonetizationPlan)
    ai_task_queue: tuple[AiTaskEntry, ...] = ()
    launch_checklist_md: str = ""
    operator_notes_md: str = ""
    missing_files: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Output models: Project Assembly
# ---------------------------------------------------------------------------

class ProjectStructurePlan(_Frozen):
    project_slug: str
    directories: tuple[str, ...]


# ---------------------------------------------------------------------------
# 2. Import package
# ---------------------------------------------------------------------------

class BusinessRecord(_Frozen):
    business_id: str
    name: str
    slug: str
    category_id: str
    location_id: str
    website: str = ""
    phone: str = ""
    description: str = ""


class CategoryRecord(_Frozen):
    category_id: str
    name: str
    slug: str
    description: str = ""


class LocationRecord(_Frozen):
    location_id: str
    city: str
    state: str
    slug: str


class RelationshipRecord(_Frozen):
    relationship_id: str
    business_id: str
    category_id: str
    location_id: str


class TagRecord(_Frozen):
    tag_id: str
    business_id: str
    tag: str


class AmenityRecord(_Frozen):
    amenity_id: str
    business_id: str
    amenity: str


class ImportPackage(_Frozen):
    businesses: tuple[BusinessRecord, ...]
    categories: tuple[CategoryRecord, ...]
    locations: tuple[LocationRecord, ...]
    relationships: tuple[RelationshipRecord, ...]
    tags: tuple[TagRecord, ...]
    amenities: tuple[AmenityRecord, ...]
    scaffold_tables: tuple[str, ...]
    duplicates_removed: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# 3. SEO build package
# ---------------------------------------------------------------------------

class SeoPage(_Frozen):
    page_id: str
    page_type: str
    url_path: str
    title: str
    meta_description: str
    canonical_url: str
    breadcrumbs: tuple[str, ...]
    category_id: str = ""
    location_id: str = ""


class InternalLink(_Frozen):
    from_path: str
    to_path: str
    anchor_text: str


class RedirectEntry(_Frozen):
    from_path: str
    to_path: str
    status_code: int


class SitemapSection(_Frozen):
    name: str
    paths: tuple[str, ...]


class SeoBuildPackage(_Frozen):
    pages: tuple[SeoPage, ...]
    internal_links: tuple[InternalLink, ...]
    redirects: tuple[RedirectEntry, ...]
    sitemap_plan: tuple[SitemapSection, ...]
    robots_recommendations: tuple[str, ...]


# ---------------------------------------------------------------------------
# 4. Content build package
# ---------------------------------------------------------------------------

class ContentWorkItem(_Frozen):
    item_id: str
    work_type: str
    title: str
    target_keyword: str = ""
    target_path: str = ""
    priority: int = 2
    instructions: str = ""


class ContentBuildPackage(_Frozen):
    items: tuple[ContentWorkItem, ...]


# ---------------------------------------------------------------------------
# 5. Image package — specifications only, never generated images
# ---------------------------------------------------------------------------

class ImageSpec(_Frozen):
    spec_id: str
    image_type: str
    subject: str
    subject_slug: str
    width: int
    height: int
    file_name: str
    image_format: str
    notes: str = ""


class ImagePackage(_Frozen):
    specs: tuple[ImageSpec, ...]
    naming_standard: str
    dimension_standards: tuple[tuple[str, int, int], ...]


# ---------------------------------------------------------------------------
# 6. Validation
# ---------------------------------------------------------------------------

class ValidationIssue(_Frozen):
    issue_id: str
    severity: str
    check: str
    message: str
    subject: str = ""


class ValidationReport(_Frozen):
    issues: tuple[ValidationIssue, ...]
    critical_count: int
    warning_count: int
    info_count: int
    passed: bool


# ---------------------------------------------------------------------------
# 7. Project status
# ---------------------------------------------------------------------------

class ProjectStatus(_Frozen):
    project_slug: str
    completion_percentage: int
    launch_readiness: str
    remaining_tasks: tuple[str, ...]
    critical_warnings: tuple[str, ...]
    build_progress: tuple[tuple[str, int], ...]
    operator_summary: str


# ---------------------------------------------------------------------------
# 8. AI build queue
# ---------------------------------------------------------------------------

class AiWorkUnit(_Frozen):
    unit_id: str
    unit_type: str
    title: str
    instructions: str
    priority: int
    depends_on: tuple[str, ...] = ()


class AiBuildQueue(_Frozen):
    units: tuple[AiWorkUnit, ...]


# ---------------------------------------------------------------------------
# 9. Quality report
# ---------------------------------------------------------------------------

class QualityReport(_Frozen):
    seo_score: int
    content_score: int
    import_score: int
    completeness_score: int
    automation_readiness: int
    launch_readiness_score: int
    overall_score: int
    grade: str
    explanations: tuple[str, ...]


# ---------------------------------------------------------------------------
# 10. Manifest and final assembly
# ---------------------------------------------------------------------------

class ManifestFile(_Frozen):
    path: str
    sha256: str
    size_bytes: int


class BuildManifest(_Frozen):
    engine_name: str
    engine_version: str
    project_slug: str
    build_id: str
    built_at: str
    input_fingerprint: str
    files: tuple[ManifestFile, ...]


class ProjectAssembly(_Frozen):
    """The full in-memory result of a Directory Builder run."""

    project_slug: str
    structure: ProjectStructurePlan
    import_package: ImportPackage
    seo_package: SeoBuildPackage
    content_package: ContentBuildPackage
    image_package: ImagePackage
    validation_report: ValidationReport
    status: ProjectStatus
    ai_queue: AiBuildQueue
    quality: QualityReport


class BuildResult(_Frozen):
    """Returned by DirectoryBuilderService after artifacts are persisted."""

    project_slug: str
    project_path: str
    assembly: ProjectAssembly
    manifest: BuildManifest
    files_written: tuple[str, ...] = Field(default=())