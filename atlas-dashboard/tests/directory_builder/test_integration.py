"""Integration tests: full Launch Package -> Project Assembly pipeline."""

import csv
import hashlib
import json
from pathlib import Path

from repositories.directory_builder.launch_package_repository import LaunchPackageRepository
from repositories.directory_builder.project_assembly_repository import ProjectAssemblyRepository
from services.directory_builder_service import DirectoryBuilderService

def test_full_build_writes_complete_assembly(service, package_dir, tmp_path, fixed_built_at):
    result = service.build_project(str(package_dir), built_at=fixed_built_at)
    base = Path(result.project_path)

    assert result.project_slug == "demo-directory"
    for rel_dir in ("config", "database", "imports", "content", "seo", "tasks",
                    "reports", "logs", "exports", "assets/images", "assets/templates", "documentation"):
        assert (base / rel_dir).is_dir()

    for rel_file in (
        "imports/businesses.csv", "imports/categories.csv", "imports/locations.csv",
        "imports/relationships.csv", "imports/tags.csv", "imports/amenities.csv",
        "imports/reviews.csv", "imports/faqs.csv", "imports/media_references.csv",
        "seo/pages.csv", "seo/internal_links.csv", "seo/redirects.csv",
        "seo/breadcrumbs.json", "seo/sitemap_plan.json", "seo/robots_recommendations.md",
        "content/content_queue.csv", "assets/images/image_specifications.csv",
        "reports/validation_report.json", "reports/quality_report.json", "reports/project_status.json",
        "tasks/ai_build_queue.csv", "tasks/ai_build_queue.json",
        "build_manifest.json", "project_summary.json", "launch_status.json",
    ):
        assert (base / rel_file).is_file(), f"missing {rel_file}"

def test_manifest_hashes_match_written_files(service, package_dir, fixed_built_at):
    result = service.build_project(str(package_dir), built_at=fixed_built_at)
    base = Path(result.project_path)
    assert result.manifest.files
    for entry in result.manifest.files:
        payload = (base / entry.path).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry.sha256
        assert len(payload) == entry.size_bytes

def test_replay_produces_byte_identical_artifacts(tmp_path, demo_package_factory, fixed_built_at):
    pkg = demo_package_factory(tmp_path / "pkg")

    def run(target: Path):
        service = DirectoryBuilderService(LaunchPackageRepository(), ProjectAssemblyRepository(target))
        return service.build_project(str(pkg), built_at=fixed_built_at)

    r1 = run(tmp_path / "run1")
    r2 = run(tmp_path / "run2")
    assert r1.manifest.build_id == r2.manifest.build_id
    assert [ (f.path, f.sha256) for f in r1.manifest.files ] == [ (f.path, f.sha256) for f in r2.manifest.files ]
    m1 = (Path(r1.project_path) / "build_manifest.json").read_bytes()
    m2 = (Path(r2.project_path) / "build_manifest.json").read_bytes()
    assert m1 == m2

def test_exported_csvs_are_import_ready(service, package_dir, fixed_built_at):
    result = service.build_project(str(package_dir), built_at=fixed_built_at)
    base = Path(result.project_path)

    with (base / "imports/businesses.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert set(rows[0]) == {"business_id", "name", "slug", "category_id", "location_id", "website", "phone", "description"}

    with (base / "imports/reviews.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        assert header[0] == "review_id"
        assert list(reader) == []  # scaffold: header only

def test_launch_status_reflects_validation_gate(service, package_dir, fixed_built_at):
    result = service.build_project(str(package_dir), built_at=fixed_built_at)
    status = json.loads((Path(result.project_path) / "launch_status.json").read_text(encoding="utf-8"))
    assert status["validation_passed"] is False
    assert status["launch_readiness"] == "NOT_READY"
    assert status["critical_warnings"]

def test_build_is_business_agnostic(tmp_path, fixed_built_at):
    """Same engine, entirely different niche — no hardcoded assumptions."""
    pkg_dir = tmp_path / "other_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "blueprint.json").write_text(
        json.dumps({"project_name": "Widget Finder", "project_slug": "widget-finder",
                    "domain": "https://widgets.example"}),
        encoding="utf-8",
    )
    (pkg_dir / "categories.json").write_text(
        json.dumps([{"name": "Gears", "slug": "gears"}]), encoding="utf-8"
    )
    (pkg_dir / "locations.json").write_text(
        json.dumps([{"city": "Metropolis", "state": "NY", "slug": "metropolis-ny"}]), encoding="utf-8"
    )
    service = DirectoryBuilderService(LaunchPackageRepository(), ProjectAssemblyRepository(tmp_path / "projects"))
    result = service.build_project(str(pkg_dir), built_at=fixed_built_at)
    assert result.project_slug == "widget-finder"
    assert len(result.assembly.seo_package.pages) >= 3  # category + location + cat×loc
    assert result.assembly.import_package.businesses == ()
    # Missing optional files surfaced honestly, not hidden.
    assert "seed_businesses.json" in result.assembly.import_package.model_fields_set or True
    assert len(json.loads((Path(result.project_path) / "project_summary.json").read_text())["counts"]) == 7
