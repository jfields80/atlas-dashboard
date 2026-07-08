"""
Tests for Website Generator v1.

The Website Generator consumes a ProjectAssembly and produces a
deterministic StaticSitePackage.

The generator:

- never mutates ProjectAssembly
- never touches the filesystem
- produces deterministic output
- always generates required pages
"""

from __future__ import annotations

import hashlib
import re

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
from engines.website_generator.constants import EXTERNAL_ASSET_PATTERNS
from engines.website_generator.models import (
    StaticAsset,
    StaticPage,
    StaticSiteManifest,
    StaticSitePackage,
    WebsiteQualityReport,
)
from engines.website_generator.quality_gate import WebsiteQualityGate
from engines.website_generator.static_site_generator import StaticSiteGenerator

EXTERNAL_ASSET_RES = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in EXTERNAL_ASSET_PATTERNS
)


def dump(model):
    """Version-agnostic model dump that works for any Pydantic model."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def build_assembly(import_package: ImportPackage) -> ProjectAssembly:
    return ProjectAssembly(
        project_slug="pettripfinder",
        structure=ProjectStructurePlan(
            project_slug="pettripfinder",
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
        content_package=ContentBuildPackage(
            items=(),
        ),
        image_package=ImagePackage(
            specs=(),
            naming_standard="",
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
            project_slug="pettripfinder",
            completion_percentage=100,
            launch_readiness="READY",
            remaining_tasks=(),
            critical_warnings=(),
            build_progress=(),
            operator_summary="Ready",
        ),
        ai_queue=AiBuildQueue(
            units=(),
        ),
        quality=QualityReport(
            seo_score=100,
            content_score=100,
            import_score=100,
            completeness_score=100,
            automation_readiness=100,
            launch_readiness_score=100,
            overall_score=100,
            grade="A",
            explanations=(),
        ),
    )


def sample_assembly() -> ProjectAssembly:
    """Empty ImportPackage: no businesses, categories, or locations."""
    return build_assembly(
        ImportPackage(
            businesses=(),
            categories=(),
            locations=(),
            relationships=(),
            tags=(),
            amenities=(),
            scaffold_tables=(),
        )
    )


def populated_assembly() -> ProjectAssembly:
    """ImportPackage with categories, locations, and businesses.

    One business intentionally carries a plain-text website URL to guard
    against quality-gate false positives on legitimate contact content.
    """
    return build_assembly(
        ImportPackage(
            businesses=(
                BusinessRecord(
                    business_id="b1",
                    slug="paws-inn",
                    name="Paws Inn",
                    description="Pet-friendly hotel near the park.",
                    phone="614-555-0100",
                    website="https://pawsinn.example.com",
                    category_id="c1",
                    location_id="l1",
                ),
                BusinessRecord(
                    business_id="b2",
                    slug="bark-park-cafe",
                    name="Bark Park Cafe",
                    description="",
                    phone="",
                    website="",
                    category_id="c2",
                    location_id="l2",
                ),
                BusinessRecord(
                    business_id="b3",
                    slug="orphan-listing",
                    name="Orphan Listing",
                    description="Business with unknown category/location.",
                    phone="",
                    website="",
                    category_id="missing",
                    location_id="missing",
                ),
            ),
            categories=(
                CategoryRecord(
                    category_id="c1",
                    slug="pet-hotels",
                    name="Pet Hotels",
                    description="Places to stay with your pet.",
                ),
                CategoryRecord(
                    category_id="c2",
                    slug="pet-cafes",
                    name="Pet Cafes",
                    description="",
                ),
            ),
            locations=(
                LocationRecord(
                    location_id="l1",
                    slug="columbus-oh",
                    city="Columbus",
                    state="OH",
                ),
                LocationRecord(
                    location_id="l2",
                    slug="dublin-oh",
                    city="Dublin",
                    state="OH",
                ),
            ),
            relationships=(),
            tags=(),
            amenities=(),
            scaffold_tables=(),
        )
    )


def make_package(pages: tuple[StaticPage, ...]) -> StaticSitePackage:
    """Hand-build a package for direct quality-gate unit tests."""
    css = StaticAsset(path="assets/css/site.css", content="body{}", asset_type="css")
    system_files = (
        StaticAsset(path="robots.txt", content="User-agent: *\n", asset_type="text"),
        StaticAsset(path="sitemap.xml", content="<urlset></urlset>", asset_type="xml"),
    )

    manifest = StaticSiteManifest(
        engine_name="website_generator",
        engine_version="1.0.0",
        template_name="clean_directory_v1",
        project_slug="test",
        site_id="0" * 16,
        build_fingerprint="0" * 64,
        page_count=len(pages),
        asset_count=3,
        files=(),
    )

    return StaticSitePackage(
        project_slug="test",
        template_name="clean_directory_v1",
        pages=pages,
        assets=(css,),
        system_files=system_files,
        manifest=manifest,
        quality_report=WebsiteQualityReport(
            passed=True, critical_count=0, warning_count=0, issues=()
        ),
    )


def valid_page(path: str = "/", title: str = "Home") -> StaticPage:
    return StaticPage(
        path=path,
        title=title,
        html=f"<html><body><h1>{title}</h1></body></html>",
        page_type="home",
        source_id="home",
    )


# ---------------------------------------------------------------------------
# Required page and file generation
# ---------------------------------------------------------------------------


def test_generates_homepage():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert any(page.path == "/" for page in package.pages)


def test_generates_about_page():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert any(page.path == "/about/" for page in package.pages)


def test_generates_contact_page():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert any(page.path == "/contact/" for page in package.pages)


def test_generates_robots_txt():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert any(asset.path == "robots.txt" for asset in package.system_files)


def test_generates_sitemap():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert any(asset.path == "sitemap.xml" for asset in package.system_files)


def test_generates_local_css_asset():
    package = StaticSiteGenerator().generate(sample_assembly())

    css = [asset for asset in package.assets if asset.path == "assets/css/site.css"]

    assert len(css) == 1
    assert css[0].asset_type == "css"
    assert css[0].content.strip()


def test_handles_empty_import_package_gracefully():
    package = StaticSiteGenerator().generate(sample_assembly())

    # Only the always-on pages exist.
    paths = sorted(page.path for page in package.pages)
    assert paths == ["/", "/about/", "/contact/"]

    homepage = next(page for page in package.pages if page.path == "/")
    assert "No categories available yet." in homepage.html
    assert "No locations available yet." in homepage.html
    assert "No listings available yet." in homepage.html


def test_generates_category_location_and_business_pages_when_records_exist():
    package = StaticSiteGenerator().generate(populated_assembly())

    paths = {page.path for page in package.pages}

    assert "/categories/pet-hotels/" in paths
    assert "/categories/pet-cafes/" in paths
    assert "/locations/columbus-oh/" in paths
    assert "/locations/dublin-oh/" in paths
    assert "/categories/pet-hotels/locations/columbus-oh/" in paths
    assert "/categories/pet-hotels/locations/dublin-oh/" in paths
    assert "/categories/pet-cafes/locations/columbus-oh/" in paths
    assert "/categories/pet-cafes/locations/dublin-oh/" in paths
    assert "/businesses/paws-inn/" in paths
    assert "/businesses/bark-park-cafe/" in paths
    assert "/businesses/orphan-listing/" in paths


def test_business_page_renders_contact_and_fallbacks():
    package = StaticSiteGenerator().generate(populated_assembly())

    paws = next(p for p in package.pages if p.path == "/businesses/paws-inn/")
    assert "614-555-0100" in paws.html
    assert "pawsinn.example.com" in paws.html

    orphan = next(p for p in package.pages if p.path == "/businesses/orphan-listing/")
    assert "Uncategorized" in orphan.html
    assert "Location unavailable" in orphan.html


# ---------------------------------------------------------------------------
# Manifest integrity
# ---------------------------------------------------------------------------


def test_manifest_matches_page_count():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert package.manifest.page_count == len(package.pages)


def test_manifest_asset_count_matches():
    package = StaticSiteGenerator().generate(populated_assembly())

    assert package.manifest.asset_count == (
        len(package.assets) + len(package.system_files)
    )


def test_manifest_hashes_match_generated_files():
    package = StaticSiteGenerator().generate(populated_assembly())

    contents: dict[str, str] = {}
    for page in package.pages:
        contents[page.path] = page.html
    for asset in package.assets:
        contents[asset.path] = asset.content
    for system_file in package.system_files:
        contents[system_file.path] = system_file.content

    manifest_paths = {entry.path for entry in package.manifest.files}
    assert manifest_paths == set(contents)

    for entry in package.manifest.files:
        encoded = contents[entry.path].encode("utf-8")
        assert entry.sha256 == hashlib.sha256(encoded).hexdigest()
        assert entry.size_bytes == len(encoded)


def test_manifest_files_sorted_by_path():
    package = StaticSiteGenerator().generate(populated_assembly())

    paths = [entry.path for entry in package.manifest.files]
    assert paths == sorted(paths)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_generation_is_deterministic():
    generator = StaticSiteGenerator()

    first = generator.generate(populated_assembly())
    second = generator.generate(populated_assembly())

    assert first.manifest.build_fingerprint == second.manifest.build_fingerprint
    assert dump(first) == dump(second)


def test_output_uses_lf_newlines_only():
    package = StaticSiteGenerator().generate(populated_assembly())

    for page in package.pages:
        assert "\r" not in page.html
    for asset in package.assets + package.system_files:
        assert "\r" not in asset.content


def test_does_not_mutate_project_assembly():
    assembly = populated_assembly()
    before = dump(assembly)

    StaticSiteGenerator().generate(assembly)

    assert dump(assembly) == before


# ---------------------------------------------------------------------------
# Quality gate: passing cases
# ---------------------------------------------------------------------------


def test_quality_gate_passes_on_empty_assembly():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert package.quality_report.passed
    assert package.quality_report.critical_count == 0


def test_quality_gate_passes_on_populated_assembly():
    # Regression guard: a business displaying its own website URL as plain
    # text must not be flagged as an external asset reference.
    package = StaticSiteGenerator().generate(populated_assembly())

    assert package.quality_report.passed, [
        (issue.check, issue.message, issue.path)
        for issue in package.quality_report.issues
    ]


# ---------------------------------------------------------------------------
# Quality gate: failure cases
# ---------------------------------------------------------------------------


def test_quality_gate_catches_missing_homepage():
    package = make_package(pages=(valid_page(path="/about/", title="About"),))

    report = WebsiteQualityGate().validate(package)

    assert not report.passed
    assert any(issue.check == "homepage" for issue in report.issues)


def test_quality_gate_catches_empty_title():
    package = make_package(pages=(valid_page(), valid_page(path="/x/", title="  ")))

    report = WebsiteQualityGate().validate(package)

    assert not report.passed
    assert any(issue.check == "title" for issue in report.issues)


def test_quality_gate_catches_empty_html():
    bad = StaticPage(path="/x/", title="X", html="   ", page_type="other", source_id="x")
    package = make_package(pages=(valid_page(), bad))

    report = WebsiteQualityGate().validate(package)

    assert not report.passed
    assert any(issue.check == "html" for issue in report.issues)


def test_quality_gate_catches_script_tags():
    bad = StaticPage(
        path="/x/",
        title="X",
        html='<html><body><SCRIPT src="/x.js"></SCRIPT></body></html>',
        page_type="other",
        source_id="x",
    )
    package = make_package(pages=(valid_page(), bad))

    report = WebsiteQualityGate().validate(package)

    assert not report.passed
    assert any(issue.check == "forbidden-pattern" for issue in report.issues)


def test_quality_gate_catches_unresolved_placeholders():
    bad = StaticPage(
        path="/x/",
        title="X",
        html="<html><body>{{ business.name }}</body></html>",
        page_type="other",
        source_id="x",
    )
    package = make_package(pages=(valid_page(), bad))

    report = WebsiteQualityGate().validate(package)

    assert not report.passed
    assert any(issue.check == "forbidden-pattern" for issue in report.issues)


def test_quality_gate_catches_external_asset_references():
    bad_stylesheet = StaticPage(
        path="/x/",
        title="X",
        html='<html><head><link rel="stylesheet" href="https://cdn.example.com/a.css"></head><body>x</body></html>',
        page_type="other",
        source_id="x",
    )
    bad_image = StaticPage(
        path="/y/",
        title="Y",
        html='<html><body><img src="//cdn.example.com/pic.png"></body></html>',
        page_type="other",
        source_id="y",
    )
    package = make_package(pages=(valid_page(), bad_stylesheet, bad_image))

    report = WebsiteQualityGate().validate(package)

    assert not report.passed
    flagged = {issue.path for issue in report.issues if issue.check == "external-asset"}
    assert flagged == {"/x/", "/y/"}


def test_quality_gate_allows_plain_text_urls():
    page = StaticPage(
        path="/x/",
        title="X",
        html="<html><body><p>Website: https://example.com</p></body></html>",
        page_type="other",
        source_id="x",
    )
    package = make_package(pages=(valid_page(), page))

    report = WebsiteQualityGate().validate(package)

    assert report.passed


def test_quality_gate_catches_missing_required_files():
    base = make_package(pages=(valid_page(),))

    stripped = StaticSitePackage(
        project_slug=base.project_slug,
        template_name=base.template_name,
        pages=base.pages,
        assets=(),
        system_files=(),
        manifest=base.manifest,
        quality_report=base.quality_report,
    )

    report = WebsiteQualityGate().validate(stripped)

    assert not report.passed
    checks = {issue.check for issue in report.issues}
    assert "required-asset" in checks
    assert "required-system-file" in checks


def test_quality_gate_catches_duplicate_page_paths():
    package = make_package(pages=(valid_page(), valid_page()))

    report = WebsiteQualityGate().validate(package)

    assert not report.passed
    assert any(issue.check == "duplicate-path" for issue in report.issues)


# ---------------------------------------------------------------------------
# Generated output hygiene
# ---------------------------------------------------------------------------


def test_generated_pages_have_no_script_tags():
    package = StaticSiteGenerator().generate(populated_assembly())

    for page in package.pages:
        assert "<script" not in page.html.lower()


def test_generated_pages_have_no_external_assets():
    package = StaticSiteGenerator().generate(populated_assembly())

    for page in package.pages:
        for pattern in EXTERNAL_ASSET_RES:
            assert not pattern.search(page.html), (page.path, pattern.pattern)

    for asset in package.assets + package.system_files:
        for pattern in EXTERNAL_ASSET_RES:
            assert not pattern.search(asset.content), (asset.path, pattern.pattern)


def test_html_escapes_untrusted_record_content():
    assembly = build_assembly(
        ImportPackage(
            businesses=(
                BusinessRecord(
                    business_id="b1",
                    slug="evil",
                    name='<script>alert("x")</script>',
                    description="a & b <i>c</i>",
                    category_id="c1",
                    location_id="l1",
                ),
            ),
            categories=(
                CategoryRecord(category_id="c1", slug="cat", name="Cat & Co"),
            ),
            locations=(
                LocationRecord(location_id="l1", slug="loc", city="X", state="Y"),
            ),
            relationships=(),
            tags=(),
            amenities=(),
            scaffold_tables=(),
        )
    )

    package = StaticSiteGenerator().generate(assembly)

    business_page = next(
        page for page in package.pages if page.path == "/businesses/evil/"
    )
    assert "<script" not in business_page.html.lower()
    assert "&lt;script&gt;" in business_page.html
    assert package.quality_report.passed


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_project_slug_preserved():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert package.project_slug == "pettripfinder"


def test_template_name():
    package = StaticSiteGenerator().generate(sample_assembly())

    assert package.template_name == "clean_directory_v1"
