"""Tests for the Preview Engine (Phase 4)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from engines.preview.preview_engine import PreviewEngine
from engines.preview.preview_models import PreviewBuild
from engines.website_generator.models import (
    StaticAsset,
    StaticFileHash,
    StaticPage,
    StaticSiteManifest,
    StaticSitePackage,
    WebsiteQualityReport,
)
from repositories.static_site_repository import MANIFEST_FILENAME


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _dump(model) -> dict:
    """Dump a model under Pydantic v1 or v2 (capability-detected)."""
    if hasattr(model, "model_dump"):
        return model.model_dump()

    return model.dict()


def _file_hash(path: str, content: str) -> StaticFileHash:
    encoded = content.encode("utf-8")

    return StaticFileHash(
        path=path,
        sha256=hashlib.sha256(encoded).hexdigest(),
        size_bytes=len(encoded),
    )


def _html(title: str) -> str:
    return f"<!DOCTYPE html>\n<html><head><title>{title}</title></head><body><h1>{title}</h1></body></html>\n"


def build_package(
    project_slug: str = "pet-trip-finder",
    corrupt_hash: bool = False,
) -> StaticSitePackage:
    pages = sorted(
        [
            StaticPage(
                path="/",
                title="Home",
                html=_html("Pet Trip Finder Directory"),
                page_type="home",
                source_id="home",
            ),
            StaticPage(
                path="/about/",
                title="About",
                html=_html("About"),
                page_type="about",
                source_id="about",
            ),
            StaticPage(
                path="/contact/",
                title="Contact",
                html=_html("Contact"),
                page_type="contact",
                source_id="contact",
            ),
            StaticPage(
                path="/categories/pet-stores/",
                title="Pet Stores",
                html=_html("Pet Stores"),
                page_type="category",
                source_id="cat-001",
            ),
            StaticPage(
                path="/businesses/barks-and-rec/",
                title="Barks and Rec",
                html=_html("Barks and Rec"),
                page_type="business",
                source_id="biz-001",
            ),
        ],
        key=lambda p: p.path,
    )

    assets = (
        StaticAsset(
            path="assets/css/site.css",
            content="body { margin: 0; }\n",
            asset_type="css",
        ),
    )

    system_files = (
        StaticAsset(
            path="robots.txt",
            content="User-agent: *\nAllow: /\n",
            asset_type="text",
        ),
        StaticAsset(
            path="sitemap.xml",
            content='<?xml version="1.0" encoding="UTF-8"?>\n<urlset></urlset>\n',
            asset_type="xml",
        ),
    )

    files = sorted(
        [_file_hash(page.path, page.html) for page in pages]
        + [_file_hash(asset.path, asset.content) for asset in assets]
        + [_file_hash(sf.path, sf.content) for sf in system_files],
        key=lambda f: f.path,
    )

    if corrupt_hash:
        first = files[0]
        files[0] = StaticFileHash(
            path=first.path,
            sha256="0" * 64,
            size_bytes=first.size_bytes,
        )

    fingerprint_source = "\n".join(
        f"{f.path}:{f.sha256}:{f.size_bytes}" for f in files
    )
    build_fingerprint = hashlib.sha256(
        fingerprint_source.encode("utf-8")
    ).hexdigest()

    manifest = StaticSiteManifest(
        engine_name="website_generator",
        engine_version="1.0.0",
        template_name="atlas-directory-default",
        project_slug=project_slug,
        site_id=build_fingerprint[:16],
        build_fingerprint=build_fingerprint,
        page_count=len(pages),
        asset_count=len(assets) + len(system_files),
        files=tuple(files),
    )

    return StaticSitePackage(
        project_slug=project_slug,
        template_name="atlas-directory-default",
        pages=tuple(pages),
        assets=assets,
        system_files=system_files,
        manifest=manifest,
        quality_report=WebsiteQualityReport(
            passed=True,
            critical_count=0,
            warning_count=0,
            issues=(),
        ),
    )


# ---------------------------------------------------------------------------
# Required coverage
# ---------------------------------------------------------------------------

def test_preview_folder_created(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "preview"

    build = PreviewEngine().build_preview(package, root)

    assert isinstance(build, PreviewBuild)
    assert root.is_dir()
    assert build.preview_path == str(root)


def test_homepage_exists(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "preview"

    build = PreviewEngine().build_preview(package, root)

    assert build.homepage_path == str(root / "index.html")
    assert Path(build.homepage_path).is_file()


def test_preview_ready_true(tmp_path: Path) -> None:
    package = build_package()

    build = PreviewEngine().build_preview(package, tmp_path / "preview")

    assert build.preview_ready is True
    assert build.issues == ()


def test_manifest_path_correct(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "preview"

    build = PreviewEngine().build_preview(package, root)

    assert build.manifest_path == str(root / MANIFEST_FILENAME)
    assert Path(build.manifest_path).is_file()


def test_page_counts_correct(tmp_path: Path) -> None:
    package = build_package()

    build = PreviewEngine().build_preview(package, tmp_path / "preview")

    assert build.page_count == len(package.pages)
    assert build.asset_count == (
        len(package.assets) + len(package.system_files)
    )
    assert build.page_count == package.manifest.page_count
    assert build.asset_count == package.manifest.asset_count


# ---------------------------------------------------------------------------
# Additional Phase 4 guarantees
# ---------------------------------------------------------------------------

def test_preview_not_ready_when_manifest_hash_mismatch(tmp_path: Path) -> None:
    package = build_package(corrupt_hash=True)

    build = PreviewEngine().build_preview(package, tmp_path / "preview")

    assert build.preview_ready is False
    assert any("manifest verification failed" in issue for issue in build.issues)


def test_all_pages_and_assets_written(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "preview"

    PreviewEngine().build_preview(package, root)

    assert (root / "about" / "index.html").is_file()
    assert (root / "contact" / "index.html").is_file()
    assert (root / "categories" / "pet-stores" / "index.html").is_file()
    assert (root / "businesses" / "barks-and-rec" / "index.html").is_file()
    assert (root / "assets" / "css" / "site.css").is_file()
    assert (root / "robots.txt").is_file()
    assert (root / "sitemap.xml").is_file()


def test_deterministic_preview(tmp_path: Path) -> None:
    package = build_package()
    engine = PreviewEngine()

    build_a = engine.build_preview(package, tmp_path / "a")
    build_b = engine.build_preview(package, tmp_path / "b")

    assert build_a.page_count == build_b.page_count
    assert build_a.asset_count == build_b.asset_count
    assert build_a.preview_ready == build_b.preview_ready
    assert build_a.issues == build_b.issues

    tree_a = {
        str(p.relative_to(tmp_path / "a")).replace("\\", "/"): p.read_bytes()
        for p in sorted((tmp_path / "a").rglob("*"))
        if p.is_file()
    }
    tree_b = {
        str(p.relative_to(tmp_path / "b")).replace("\\", "/"): p.read_bytes()
        for p in sorted((tmp_path / "b").rglob("*"))
        if p.is_file()
    }
    assert tree_a == tree_b


def test_does_not_mutate_package(tmp_path: Path) -> None:
    package = build_package()
    snapshot = _dump(package)

    PreviewEngine().build_preview(package, tmp_path / "preview")

    assert _dump(package) == snapshot
