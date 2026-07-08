"""Tests for the Preview Service (Phase 4).

Runs the real end-to-end pipeline:
    ProjectAssembly -> StaticSiteGenerator -> StaticSiteRepository
        -> PreviewEngine -> PreviewBuild
"""

from __future__ import annotations

from pathlib import Path

from engines.directory_builder.models import (
    AiBuildQueue,
    BusinessRecord,
    CategoryRecord,
    ContentBuildPackage,
    ImagePackage,
    ImportPackage,
    LocationRecord,
    ProjectAssembly,
    ProjectStatus,
    ProjectStructurePlan,
    QualityReport,
    SeoBuildPackage,
    ValidationReport,
)
from engines.preview.preview_models import PreviewBuild
from repositories.static_site_repository import (
    MANIFEST_FILENAME,
    StaticSiteRepository,
)
from services.preview_service import PreviewService


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _dump(model) -> dict:
    """Dump a model under Pydantic v1 or v2 (capability-detected)."""
    if hasattr(model, "model_dump"):
        return model.model_dump()

    return model.dict()


def build_assembly(project_slug: str = "pet-trip-finder") -> ProjectAssembly:
    import_package = ImportPackage(
        businesses=(
            BusinessRecord(
                business_id="biz-001",
                name="Barks and Rec",
                slug="barks-and-rec",
                category_id="cat-001",
                location_id="loc-001",
                website="https://example.com",
                phone="614-555-0100",
                description="Dog-friendly recreation and supplies.",
            ),
            BusinessRecord(
                business_id="biz-002",
                name="The Pampered Pup",
                slug="the-pampered-pup",
                category_id="cat-002",
                location_id="loc-001",
                description="Grooming and boutique treats.",
            ),
        ),
        categories=(
            CategoryRecord(
                category_id="cat-001",
                name="Pet Stores",
                slug="pet-stores",
                description="Retail stores for pet supplies.",
            ),
            CategoryRecord(
                category_id="cat-002",
                name="Groomers",
                slug="groomers",
            ),
        ),
        locations=(
            LocationRecord(
                location_id="loc-001",
                city="Columbus",
                state="OH",
                slug="columbus-oh",
            ),
        ),
        relationships=(),
        tags=(),
        amenities=(),
        scaffold_tables=(),
    )

    return ProjectAssembly(
        project_slug=project_slug,
        structure=ProjectStructurePlan(
            project_slug=project_slug,
            directories=(),
        ),
        import_package=import_package,
        seo_package=SeoBuildPackage(
            pages=(),
            internal_links=(),
            redirects=(),
            sitemap_plan=(),
            robots_recommendations=(),
        ),
        content_package=ContentBuildPackage(items=()),
        image_package=ImagePackage(
            specs=(),
            naming_standard="atlas-standard",
            dimension_standards=(),
        ),
        validation_report=ValidationReport(
            issues=(),
            critical_count=0,
            warning_count=0,
            info_count=0,
            passed=True,
        ),
        status=ProjectStatus(
            project_slug=project_slug,
            completion_percentage=100,
            launch_readiness="READY",
            remaining_tasks=(),
            critical_warnings=(),
            build_progress=(),
            operator_summary="Build complete.",
        ),
        ai_queue=AiBuildQueue(units=()),
        quality=QualityReport(
            seo_score=90,
            content_score=90,
            import_score=90,
            completeness_score=90,
            automation_readiness=90,
            launch_readiness_score=90,
            overall_score=90,
            grade="A",
            explanations=(),
        ),
    )


def _read_tree(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# ---------------------------------------------------------------------------
# Required coverage
# ---------------------------------------------------------------------------

def test_assembly_to_preview_build(tmp_path: Path) -> None:
    assembly = build_assembly()
    root = tmp_path / "preview"

    build = PreviewService().build_preview(assembly, preview_root=root)

    assert isinstance(build, PreviewBuild)
    assert build.preview_ready is True
    assert build.issues == ()
    assert build.preview_path == str(root)
    assert build.homepage_path == str(root / "index.html")
    assert build.manifest_path == str(root / MANIFEST_FILENAME)
    assert Path(build.homepage_path).is_file()
    assert Path(build.manifest_path).is_file()
    assert (root / "robots.txt").is_file()
    assert (root / "sitemap.xml").is_file()
    assert (root / "assets" / "css" / "site.css").is_file()

    # Directory structure covers categories, locations, and businesses.
    assert (root / "categories" / "pet-stores" / "index.html").is_file()
    assert (root / "locations" / "columbus-oh" / "index.html").is_file()
    assert (root / "businesses" / "barks-and-rec" / "index.html").is_file()
    assert (root / "about" / "index.html").is_file()
    assert (root / "contact" / "index.html").is_file()

    assert build.page_count > 0
    assert build.asset_count == 3  # site.css + robots.txt + sitemap.xml


def test_does_not_mutate_input(tmp_path: Path) -> None:
    assembly = build_assembly()
    snapshot = _dump(assembly)

    PreviewService().build_preview(assembly, preview_root=tmp_path / "preview")

    assert _dump(assembly) == snapshot


def test_deterministic(tmp_path: Path) -> None:
    service = PreviewService()

    build_a = service.build_preview(
        build_assembly(), preview_root=tmp_path / "a"
    )
    build_b = service.build_preview(
        build_assembly(), preview_root=tmp_path / "b"
    )

    assert build_a.page_count == build_b.page_count
    assert build_a.asset_count == build_b.asset_count
    assert build_a.preview_ready == build_b.preview_ready
    assert build_a.issues == build_b.issues
    assert _read_tree(tmp_path / "a") == _read_tree(tmp_path / "b")


def test_manifest_hashes_verify_on_disk(tmp_path: Path) -> None:
    assembly = build_assembly()
    root = tmp_path / "preview"

    from engines.website_generator.static_site_generator import (
        StaticSiteGenerator,
    )

    PreviewService().build_preview(assembly, preview_root=root)

    package = StaticSiteGenerator().generate(assembly)
    assert StaticSiteRepository().verify(package, root) == ()


def test_default_preview_root_uses_project_slug(tmp_path: Path) -> None:
    assembly = build_assembly()
    service = PreviewService(preview_root=tmp_path / "previews")

    build = service.build_preview(assembly)

    expected_root = tmp_path / "previews" / assembly.project_slug
    assert build.preview_path == str(expected_root)
    assert (expected_root / "index.html").is_file()


def test_rebuild_overwrites_previous_preview(tmp_path: Path) -> None:
    assembly = build_assembly()
    root = tmp_path / "preview"
    service = PreviewService()

    service.build_preview(assembly, preview_root=root)

    stale = root / "stale.html"
    stale.write_bytes(b"stale")

    build = service.build_preview(assembly, preview_root=root)

    assert not stale.exists()
    assert build.preview_ready is True
